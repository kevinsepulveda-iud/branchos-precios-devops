"""Paso 2 del pipeline: construye el sitio estático a partir de data/.

Uso:
    python scripts/publicar.py --salida site --version <sha del commit>

Lee la última extracción y todo el histórico, y genera site/index.html con
los indicadores, gráficos y el CSV descargable. Desde la EA3 también copia la
aplicación web (app/) en site/app/ con su catálogo en JSON y un salud.json
que el pipeline revisa después de desplegar. GitHub Actions sube esa carpeta
a GitHub Pages.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from branchos import analisis, catalogo, reporte  # noqa: E402


def cargar_historico(carpeta):
    """Un renglón por extracción con los indicadores principales.

    La primera fila sale de referencia_ea1.json: en la EA1 trabajé en Colab y
    no guardé el CSV en un repositorio, así que de esa fecha solo quedan los
    indicadores del informe. Desde la EA2 cada extracción queda versionada.
    """
    filas = []
    referencia = Path(carpeta) / "referencia_ea1.json"
    if referencia.exists():
        filas.append(json.loads(referencia.read_text(encoding="utf-8")))
    for archivo in sorted(Path(carpeta).glob("tenis_*.csv")):
        df = pd.read_csv(archivo, sep=";", encoding="utf-8-sig")
        ind = analisis.indicadores(df)
        filas.append({
            "fecha": archivo.stem.replace("tenis_", ""),
            "referencias": ind["referencias"],
            "precio_mediano": ind["precio_mediano"],
            "pct_con_descuento": ind["pct_con_descuento"],
            "descuento_promedio": ind["descuento_promedio"],
        })
    return pd.DataFrame(filas)


def publicar_app(carpeta_datos, salida, version):
    """Copia app/ en site/app/ y escribe el catálogo y el estado de salud en JSON."""
    destino = Path(salida) / "app"
    shutil.copytree(RAIZ / "app", destino, dirs_exist_ok=True)
    extracciones = catalogo.cargar_extracciones(Path(carpeta_datos) / "historico")
    datos = catalogo.construir_catalogo(extracciones, version)
    (destino / "datos").mkdir(exist_ok=True)
    (destino / "datos" / "catalogo.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    salud = catalogo.estado_salud(datos)
    (destino / "salud.json").write_text(json.dumps(salud, indent=2, ensure_ascii=False), encoding="utf-8")
    return destino, catalogo.resumen_cambios(datos)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--datos", default=str(RAIZ / "data"))
    parser.add_argument("--salida", default=str(RAIZ / "site"))
    parser.add_argument("--version", default="local")
    args = parser.parse_args()

    actual = pd.read_csv(Path(args.datos) / "tenis_branchos_actual.csv", sep=";", encoding="utf-8-sig")
    historico = cargar_historico(Path(args.datos) / "historico")
    ruta = reporte.generar_sitio(actual, historico, args.salida, args.version)
    print(f"Sitio generado en {ruta}")
    carpeta_app, cambios = publicar_app(args.datos, args.salida, args.version)
    print(f"Aplicación web en {carpeta_app} · cambios contra la semana anterior: {cambios}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
