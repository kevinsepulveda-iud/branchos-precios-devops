"""Paso 1 del pipeline: scraping + limpieza + control de calidad.

Uso:
    python scripts/extraer.py            # extrae y guarda en data/
    python scripts/extraer.py --paginas 2  # prueba rápida con 2 páginas

Guarda:
    data/historico/tenis_AAAA-MM-DD.csv   una foto por fecha (no se sobrescribe el pasado)
    data/tenis_branchos_actual.csv        la última extracción
    data/ultima_ejecucion.json            resumen para el control de calidad

Si la validación encuentra problemas el script termina con código 1 y el
workflow de GitHub Actions se detiene antes de publicar.
"""

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from branchos import limpieza, scraper  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--paginas", type=int, default=None, help="tope de páginas (para pruebas)")
    parser.add_argument("--salida", default=str(RAIZ / "data"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    salida = Path(args.salida)
    (salida / "historico").mkdir(parents=True, exist_ok=True)

    if not scraper.robots_permite():
        logging.error("El robots.txt no permite recorrer la categoría; no extraigo nada")
        return 1

    registros, resumen = scraper.extraer_catalogo(max_paginas=args.paginas)
    hoy = date.today().isoformat()
    df = limpieza.limpiar(registros, hoy)

    # En una prueba con pocas páginas no tiene sentido exigir el catálogo completo
    total = None if args.paginas else resumen["total_reportado"]
    problemas = limpieza.validar(df, total)
    resumen.update({"fecha": hoy, "registros_limpios": len(df), "problemas": problemas})

    df.to_csv(salida / "historico" / f"tenis_{hoy}.csv", index=False, sep=";", encoding="utf-8-sig")
    df.to_csv(salida / "tenis_branchos_actual.csv", index=False, sep=";", encoding="utf-8-sig")
    (salida / "ultima_ejecucion.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")

    logging.info("Resumen: %s", resumen)
    if problemas:
        for p in problemas:
            logging.error("Control de calidad: %s", p)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
