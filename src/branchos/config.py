"""Parámetros del proyecto.

Los dejo en un solo archivo para que el scraper, la limpieza y el reporte usen
los mismos valores. Si quiero cambiar de categoría o la pausa entre peticiones,
solo toco este archivo (o las variables de entorno, que es lo que usa GitHub Actions).
"""

import os

DOMINIO = "https://www.tiendasbranchos.com"
CATEGORIA = os.getenv("BRANCHOS_CATEGORIA", "/hombres/tenis")

# Tope de seguridad por si la categoría crece mucho
MAX_PAGINAS = int(os.getenv("BRANCHOS_MAX_PAGINAS", "60"))

# Segundos entre peticiones: misma pausa ética que usé en la EA1 y que vimos en clase
PAUSA = float(os.getenv("BRANCHOS_PAUSA", "1.5"))

# Reintentos cuando la tienda responde una página vacía (falla intermitente de su caché)
INTENTOS = 3
TIMEOUT = 30

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO,es;q=0.9",
}

# Columnas del dataset limpio (mismo orden en todos los CSV del histórico)
COLUMNAS = [
    "fecha_extraccion",
    "sku",
    "nombre",
    "marca",
    "tipo",
    "precio",
    "precio_antes",
    "descuento_pct",
    "tallas_disponibles",
    "url",
    "pagina",
]
