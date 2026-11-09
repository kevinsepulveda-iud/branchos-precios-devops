"""Extracción del catálogo de Tiendas Branchos.

Es el mismo método 1 de la EA1 (requests + BeautifulSoup), pero separado en
funciones pequeñas para poder probarlas una por una con pytest. Las funciones
que leen el HTML (productos_json_ld, precios_tarjetas, total_productos) no
hacen peticiones, así las pruebas corren sin internet usando una página guardada.
"""

import html as html_lib
import json
import logging
import math
import re
import time
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from branchos import config
from branchos.limpieza import a_pesos

log = logging.getLogger(__name__)


def limpiar_url(url):
    """URL absoluta y sin parámetros: la uso como identificador del producto."""
    if not url:
        return None
    return urljoin(config.DOMINIO, url).split("?")[0]


def url_pagina(n, categoria=None):
    """Branchos pagina con ?page=1, ?page=2, ..."""
    return f"{config.DOMINIO}{categoria or config.CATEGORIA}?page={n}"


def productos_json_ld(soup):
    """Lee los <script type="application/ld+json"> y devuelve {url: producto}.

    Solo me sirve el bloque de tipo ItemList, que es el que trae la lista de
    productos con SKU, nombre, marca, precio y las tallas (cada talla es una oferta).
    """
    productos = {}
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            datos = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        if not isinstance(datos, dict) or datos.get("@type") != "ItemList":
            continue
        for elemento in datos.get("itemListElement", []):
            p = elemento.get("item", {}) or {}
            oferta = p.get("offers", {}) or {}
            tallas = [
                o for o in oferta.get("offers", [])
                if "InStock" in str(o.get("availability", ""))
            ]
            url = limpiar_url(p.get("@id") or p.get("url"))
            if not url:
                continue
            productos[url] = {
                "sku": str(p.get("sku") or p.get("mpn") or ""),
                # algunos nombres traen entidades HTML (D&quot;lites), las convierto a texto
                "nombre": html_lib.unescape(p.get("name") or "").strip(),
                "marca": (p.get("brand") or {}).get("name"),
                "precio": a_pesos(oferta.get("lowPrice") or oferta.get("price")),
                "tallas_disponibles": len(tallas),
                "url": url,
            }
    return productos


def precios_tarjetas(soup):
    """De las tarjetas VTEX saco el precio tachado (antes del descuento).

    Ese dato no viene en el JSON-LD, por eso en la EA1 también leía el HTML.
    """
    precios = {}
    for card in soup.select("section.vtex-product-summary-2-x-container"):
        enlace = card.find("a", href=True)
        if not enlace:
            continue
        antes = card.select_one("[class*='listPriceValue']")
        actual = card.select_one("[class*='sellingPriceValue']")
        precios[limpiar_url(enlace["href"])] = {
            "precio_antes": a_pesos(antes.get_text()) if antes else None,
            "precio_tarjeta": a_pesos(actual.get_text()) if actual else None,
        }
    return precios


def total_productos(html):
    """Total de productos que reporta la tienda (campo recordsFiltered de VTEX)."""
    encontrado = re.search(r'"recordsFiltered":(\d+)', html)
    return int(encontrado.group(1)) if encontrado else None


def numero_paginas(total, por_pagina, maximo=None):
    """Cuántas páginas debo recorrer (división hacia arriba, con tope)."""
    if not total or not por_pagina:
        return 1
    return min(maximo or config.MAX_PAGINAS, math.ceil(total / por_pagina))


def parsear_pagina(html, pagina):
    """Une JSON-LD y tarjetas de una página ya descargada."""
    soup = BeautifulSoup(html, "html.parser")
    productos = productos_json_ld(soup)
    precios = precios_tarjetas(soup)
    registros = []
    for url, p in productos.items():
        p["precio_antes"] = precios.get(url, {}).get("precio_antes")
        p["pagina"] = pagina
        registros.append(p)
    return registros


def robots_permite(sesion=None):
    """Reviso el robots.txt antes de empezar, como en la EA1."""
    sesion = sesion or requests
    robots = RobotFileParser()
    try:
        texto = sesion.get(config.DOMINIO + "/robots.txt", headers=config.HEADERS,
                           timeout=config.TIMEOUT).text
        robots.parse(texto.splitlines())
        return robots.can_fetch(config.HEADERS["User-Agent"], url_pagina(2))
    except requests.RequestException as e:
        log.warning("No pude leer robots.txt: %s", e)
        return True


def descargar_pagina(pagina, sesion=None, intentos=None, espera=3):
    """Descarga una página; si llega vacía o falla, la vuelve a pedir."""
    sesion = sesion or requests
    intentos = intentos or config.INTENTOS
    for intento in range(1, intentos + 1):
        try:
            resp = sesion.get(url_pagina(pagina), headers=config.HEADERS, timeout=config.TIMEOUT)
            if resp.status_code == 200:
                registros = parsear_pagina(resp.text, pagina)
                if registros:
                    return resp.text, registros, intento
            log.info("Página %s vacía o con código %s (intento %s)", pagina,
                     resp.status_code, intento)
        except requests.RequestException as e:
            log.info("Página %s: error de red %s (intento %s)", pagina, e, intento)
        time.sleep(espera * intento)
    return None, [], intentos


def extraer_catalogo(sesion=None, pausa=None, max_paginas=None):
    """Recorre toda la categoría y devuelve (registros, resumen).

    El resumen guarda lo que necesito para el control de calidad: total que
    reporta la tienda, páginas recorridas, reintentos y páginas que no se leyeron.
    """
    sesion = sesion or requests.Session()
    pausa = config.PAUSA if pausa is None else pausa
    inicio = time.time()

    html, registros, intento = descargar_pagina(1, sesion)
    if not registros:
        raise RuntimeError("No se pudo leer la primera página del catálogo")

    total = total_productos(html)
    paginas = numero_paginas(total, len(registros), max_paginas)
    log.info("La categoría tiene %s productos en %s páginas", total, paginas)

    reintentos, fallidas = intento - 1, []
    for pagina in range(2, paginas + 1):
        time.sleep(pausa)
        _, nuevos, intento = descargar_pagina(pagina, sesion)
        reintentos += intento - 1
        if not nuevos:
            fallidas.append(pagina)
            continue
        registros.extend(nuevos)
        if pagina % 10 == 0:
            log.info("Página %s de %s (acumulado %s)", pagina, paginas, len(registros))

    # Segunda pasada: en la EA1 vi que las páginas que fallan suelen responder bien
    # unos segundos después. En vez de usar un segundo método (como hice con Scrapy),
    # vuelvo a pedir solo las que quedaron pendientes.
    recuperadas = []
    for pagina in list(fallidas):
        time.sleep(pausa * 4)
        _, nuevos, _ = descargar_pagina(pagina, sesion)
        if nuevos:
            registros.extend(nuevos)
            fallidas.remove(pagina)
            recuperadas.append(pagina)

    resumen = {
        "total_reportado": total,
        "paginas": paginas,
        "registros": len(registros),
        "reintentos": reintentos,
        "paginas_recuperadas": recuperadas,
        "paginas_fallidas": fallidas,
        "segundos": round(time.time() - inicio, 1),
    }
    return registros, resumen
