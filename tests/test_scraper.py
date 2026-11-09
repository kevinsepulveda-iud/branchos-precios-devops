"""Pruebas del scraper con una página guardada (sin internet)."""

from bs4 import BeautifulSoup

from branchos import config, scraper


def test_json_ld_lee_los_tres_productos(html_pagina):
    productos = scraper.productos_json_ld(BeautifulSoup(html_pagina, "html.parser"))
    assert len(productos) == 3
    revolution = productos["https://www.tiendasbranchos.com/nike-tenis-revolution-8-hombre-negro-66091/p"]
    assert revolution["sku"] == "154300"
    assert revolution["marca"] == "NIKE"
    assert revolution["precio"] == 263200


def test_tallas_solo_cuenta_las_que_estan_en_stock(html_pagina):
    productos = scraper.productos_json_ld(BeautifulSoup(html_pagina, "html.parser"))
    tallas = {p["sku"]: p["tallas_disponibles"] for p in productos.values()}
    assert tallas == {"154300": 2, "161724": 3, "76224": 1}


def test_precio_tachado_sale_de_las_tarjetas(html_pagina):
    precios = scraper.precios_tarjetas(BeautifulSoup(html_pagina, "html.parser"))
    url = "https://www.tiendasbranchos.com/nike-tenis-revolution-8-hombre-negro-66091/p"
    # la URL de la tarjeta trae ?skuId=..., el scraper la limpia para poder unirla con el JSON-LD
    assert precios[url]["precio_antes"] == 359000
    assert precios[url]["precio_tarjeta"] == 263200


def test_parsear_pagina_une_json_ld_y_tarjetas(html_pagina):
    registros = scraper.parsear_pagina(html_pagina, pagina=1)
    assert len(registros) == 3
    assert all(r["precio_antes"] for r in registros)
    assert {r["pagina"] for r in registros} == {1}


def test_total_y_numero_de_paginas(html_pagina):
    assert scraper.total_productos(html_pagina) == 560
    assert scraper.numero_paginas(560, 12) == 47
    assert scraper.numero_paginas(5000, 12, maximo=60) == 60
    assert scraper.numero_paginas(None, 12) == 1


def test_limpiar_url():
    assert scraper.limpiar_url("/producto/p?skuId=1") == f"{config.DOMINIO}/producto/p"
    assert scraper.limpiar_url(None) is None


def test_reintenta_cuando_la_pagina_llega_vacia(html_pagina, html_vacio, sesion_falsa, respuesta):
    # Primero llega vacía, luego con error 503 y al tercer intento con productos
    sesion = sesion_falsa([respuesta(html_vacio), respuesta("", 503), respuesta(html_pagina)])
    _, registros, intento = scraper.descargar_pagina(5, sesion, espera=0)
    assert intento == 3
    assert len(registros) == 3
    assert sesion.urls[0].endswith("?page=5")


def test_se_rinde_despues_de_tres_intentos(html_vacio, sesion_falsa, respuesta):
    sesion = sesion_falsa([respuesta(html_vacio)] * 3)
    html, registros, intento = scraper.descargar_pagina(8, sesion, espera=0)
    assert html is None and registros == [] and intento == 3


def test_extraer_catalogo_recorre_todas_las_paginas(html_pagina, sesion_falsa, respuesta, monkeypatch):
    # recordsFiltered = 7 con 3 productos por página -> 3 páginas
    html = html_pagina.replace('"recordsFiltered":560', '"recordsFiltered":7')
    monkeypatch.setattr(scraper.time, "sleep", lambda s: None)
    sesion = sesion_falsa([respuesta(html)] * 3)
    registros, resumen = scraper.extraer_catalogo(sesion, pausa=0)
    assert resumen["paginas"] == 3
    assert resumen["paginas_fallidas"] == []
    assert len(sesion.urls) == 3
    assert len(registros) == 9  # las 3 páginas del fixture traen los mismos 3 productos


def test_segunda_pasada_recupera_paginas_fallidas(html_pagina, html_vacio, sesion_falsa, respuesta,
                                                  monkeypatch):
    # 2 páginas: la 2 falla 3 veces seguidas y se recupera en la segunda pasada
    html = html_pagina.replace('"recordsFiltered":560', '"recordsFiltered":6')
    monkeypatch.setattr(scraper.time, "sleep", lambda s: None)
    sesion = sesion_falsa([respuesta(html)] + [respuesta(html_vacio)] * 3 + [respuesta(html)])
    registros, resumen = scraper.extraer_catalogo(sesion, pausa=0)
    assert resumen["paginas_recuperadas"] == [2]
    assert resumen["paginas_fallidas"] == []
    assert len(registros) == 6


def test_nombres_con_entidades_html(html_pagina):
    # Caso real: "Skechers Tenis D&quot;lites Hiker" llega así en el JSON-LD
    html = html_pagina.replace("Fila Botas Netball Classic", "Skechers Tenis D&quot;lites")
    productos = scraper.productos_json_ld(BeautifulSoup(html, "html.parser"))
    assert any(p["nombre"].startswith('Skechers Tenis D"lites') for p in productos.values())
