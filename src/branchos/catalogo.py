"""Catálogo con historial de precios para la aplicación web (EA3).

En la EA2 el reporte mostraba una sola foto del catálogo. Como el scraping
programado ya guarda una extracción por semana en data/historico/, aquí uno
todas las fotos por SKU para que la app pueda mostrar cómo cambió el precio
de cada producto.

Lo usan los dos despliegues:
- scripts/publicar.py lo escribe como JSON estático para GitHub Pages.
- branchos.web lo arma en vivo cuando la app corre como servicio (Docker).
"""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

CAMPOS = [
    "sku", "nombre", "marca", "tipo", "precio", "precio_antes", "descuento_pct", "tallas_disponibles", "url",
]


def cargar_extracciones(carpeta):
    """Lee data/historico/tenis_AAAA-MM-DD.csv y devuelve {fecha: DataFrame} en orden."""
    extracciones = {}
    for archivo in sorted(Path(carpeta).glob("tenis_*.csv")):
        fecha = archivo.stem.replace("tenis_", "")
        extracciones[fecha] = pd.read_csv(archivo, sep=";", encoding="utf-8-sig")
    return extracciones


def _entero(valor):
    return None if pd.isna(valor) else int(valor)


def construir_catalogo(extracciones, version="local"):
    """Une las extracciones por SKU.

    Cada producto de la última extracción lleva su historial de precios y la
    variación contra la extracción anterior. Si el producto no estaba la semana
    anterior, la variación queda en None (no la invento como 0).
    """
    if not extracciones:
        raise ValueError("No hay extracciones en data/historico")

    fechas = list(extracciones)
    ultima = extracciones[fechas[-1]]
    anterior = extracciones[fechas[-2]] if len(fechas) > 1 else None

    historial = {}
    for fecha, df in extracciones.items():
        for sku, precio in zip(df["sku"], df["precio"], strict=True):
            historial.setdefault(int(sku), []).append({"fecha": fecha, "precio": int(precio)})

    precio_anterior = {}
    if anterior is not None:
        precio_anterior = {int(s): int(p) for s, p in zip(anterior["sku"], anterior["precio"], strict=True)}

    productos = []
    for fila in ultima[CAMPOS].itertuples(index=False):
        sku = int(fila.sku)
        previo = precio_anterior.get(sku)
        variacion = None if previo is None else round((int(fila.precio) / previo - 1) * 100, 1)
        productos.append({
            "sku": sku,
            "nombre": fila.nombre,
            "marca": fila.marca,
            "tipo": fila.tipo,
            "precio": int(fila.precio),
            "precio_antes": _entero(fila.precio_antes),
            "descuento_pct": float(fila.descuento_pct),
            "tallas": _entero(fila.tallas_disponibles),
            "url": fila.url,
            "variacion_pct": variacion,
            "historial": historial[sku],
        })

    return {
        "version": version,
        "generado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fechas": fechas,
        "ultima_extraccion": fechas[-1],
        "productos": productos,
    }


def resumen_cambios(catalogo):
    """Cuántos productos subieron, bajaron o mantuvieron el precio contra la semana anterior."""
    variaciones = [p["variacion_pct"] for p in catalogo["productos"]]
    comparables = [v for v in variaciones if v is not None]
    return {
        "comparables": len(comparables),
        "bajaron": sum(v < 0 for v in comparables),
        "subieron": sum(v > 0 for v in comparables),
        "iguales": sum(v == 0 for v in comparables),
        "nuevos": len(variaciones) - len(comparables),
    }


def estado_salud(catalogo, hoy=None, max_dias=8):
    """Lo que responde /salud: si hay datos y si no están viejos.

    El scraping corre cada lunes, así que si la última extracción tiene más de
    8 días algo falló en el workflow programado y el monitoreo lo debe avisar.
    """
    hoy = hoy or datetime.now(timezone.utc).date()
    ultima = datetime.strptime(catalogo["ultima_extraccion"], "%Y-%m-%d").date()
    dias = (hoy - ultima).days
    return {
        "estado": "ok" if catalogo["productos"] and dias <= max_dias else "datos_desactualizados",
        "version": catalogo["version"],
        "ultima_extraccion": catalogo["ultima_extraccion"],
        "dias_desde_extraccion": dias,
        "productos": len(catalogo["productos"]),
        "extracciones": len(catalogo["fechas"]),
    }
