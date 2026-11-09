"""Pipeline de precios de Tiendas Branchos (continuación de la EA1).

Módulos:
- scraper:  extracción con requests + BeautifulSoup (JSON-LD y tarjetas VTEX)
- limpieza: conversión de precios, descuentos, tipo de calzado y duplicados
- analisis: indicadores del catálogo, resumen por marca y comparación entre fechas
- reporte:  página HTML estática que se publica en GitHub Pages
"""

__version__ = "1.0.0"
