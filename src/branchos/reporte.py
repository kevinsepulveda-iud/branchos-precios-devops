"""Genera el sitio estático que se publica en GitHub Pages (la parte de CD).

Uso matplotlib para los gráficos y los guardo como PNG dentro de la carpeta
site/. La página no necesita servidor: es HTML plano, por eso se puede
desplegar gratis en GitHub Pages cada vez que hay cambios en main.
"""

import html
import json
from datetime import datetime
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")  # sin ventana: en GitHub Actions no hay pantalla
import matplotlib.pyplot as plt  # noqa: E402

from branchos import analisis  # noqa: E402

AZUL, NARANJA = "#1f4e79", "#e07b39"
COLS_MARCA = ["marca", "referencias", "precio_promedio", "descuento_promedio", "tallas_promedio"]


def _pesos(valor):
    return "$ " + f"{int(valor):,}".replace(",", ".")


def grafico_rangos(df, ruta):
    rangos = analisis.rangos_precio(df)
    fig, ax = plt.subplots(figsize=(7, 3.6))
    barras = ax.bar(rangos.index, rangos.values, color=AZUL)
    ax.bar_label(barras, fmt="%.1f %%")
    ax.set_ylabel("% de referencias")
    ax.set_title("Distribución del precio actual")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(ruta, dpi=120)
    plt.close(fig)


def grafico_marcas(tabla, ruta):
    fig, ax1 = plt.subplots(figsize=(7, 3.8))
    ax1.bar(tabla["marca"], tabla["precio_promedio"] / 1000, color=AZUL, label="Precio promedio (miles)")
    ax1.set_ylabel("Precio promedio (miles de COP)")
    ax2 = ax1.twinx()
    ax2.plot(tabla["marca"], tabla["descuento_promedio"], color=NARANJA, marker="o", label="Descuento %")
    ax2.set_ylabel("Descuento promedio (%)")
    ax2.set_ylim(0, max(60, tabla["descuento_promedio"].max() + 5))
    ax1.set_title("Precio y descuento promedio por marca")
    ax1.spines[["top"]].set_visible(False)
    ax2.spines[["top"]].set_visible(False)
    # la leyenda va debajo del gráfico para que no tape ninguna barra
    fig.legend(loc="lower center", ncol=2, fontsize=8, frameon=False)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(ruta, dpi=120)
    plt.close(fig)


def grafico_historico(historico, ruta):
    """Evolución del número de referencias y del precio mediano entre extracciones."""
    fig, ax1 = plt.subplots(figsize=(7, 3.4))
    ax1.plot(historico["fecha"], historico["referencias"], color=AZUL, marker="o")
    ax1.set_ylabel("Referencias", color=AZUL)
    ax2 = ax1.twinx()
    ax2.plot(historico["fecha"], historico["precio_mediano"] / 1000, color=NARANJA, marker="s")
    ax2.set_ylabel("Precio mediano (miles)", color=NARANJA)
    ax1.set_title("Evolución del catálogo entre extracciones")
    fig.tight_layout()
    fig.savefig(ruta, dpi=120)
    plt.close(fig)


def _tabla_html(df, columnas):
    filas = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(fila[c]))}</td>" for c in columnas) + "</tr>"
        for _, fila in df.iterrows()
    )
    cabecera = "".join(f"<th>{html.escape(c)}</th>" for c in columnas)
    return f"<table><thead><tr>{cabecera}</tr></thead><tbody>{filas}</tbody></table>"


def generar_sitio(df, historico, salida, version="local"):
    """Escribe site/index.html, los gráficos, el CSV y un JSON con los indicadores."""
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)

    ind = analisis.indicadores(df)
    marcas = analisis.por_marca(df)
    grafico_rangos(df, salida / "rangos.png")
    grafico_marcas(marcas, salida / "marcas.png")
    if len(historico) > 1:
        grafico_historico(historico, salida / "historico.png")

    df.to_csv(salida / "tenis_branchos_actual.csv", index=False, sep=";", encoding="utf-8-sig")
    (salida / "indicadores.json").write_text(json.dumps(ind, indent=2, ensure_ascii=False), encoding="utf-8")

    top_desc = df.sort_values("descuento_pct", ascending=False).head(10).copy()
    top_desc["precio"] = top_desc["precio"].apply(_pesos)
    top_desc["precio_antes"] = top_desc["precio_antes"].apply(lambda v: _pesos(v) if pd.notna(v) else "—")
    marcas_html = marcas.copy()
    marcas_html["precio_promedio"] = marcas_html["precio_promedio"].apply(_pesos)

    tarjetas = [
        ("Referencias", ind["referencias"]),
        ("Precio mediano", _pesos(ind["precio_mediano"])),
        ("Con descuento", f"{ind['pct_con_descuento']} %"),
        ("Descuento promedio", f"{ind['descuento_promedio']} %"),
    ]
    tarjetas_html = "".join(f"<div class='kpi'><span>{t}</span><b>{v}</b></div>" for t, v in tarjetas)
    bloque_hist = "<img src='historico.png' alt='Evolución'>" if len(historico) > 1 else ""

    pagina = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Precios de tenis para hombre – Tiendas Branchos</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;max-width:960px;margin:auto;padding:24px;color:#222}}
h1{{color:{AZUL};margin-bottom:4px}} .sub{{color:#666;margin-top:0}}
.kpis{{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}}
.kpi{{flex:1;min-width:150px;border:1px solid #ddd;border-radius:8px;padding:12px}}
.kpi span{{display:block;color:#666;font-size:13px}} .kpi b{{font-size:22px;color:{AZUL}}}
table{{border-collapse:collapse;width:100%;font-size:13px;margin:8px 0 20px}}
th,td{{border-bottom:1px solid #e5e5e5;padding:6px;text-align:left}} th{{background:#f3f6fa}}
img{{max-width:100%}} footer{{color:#888;font-size:12px;margin-top:30px}}
</style></head><body>
<h1>Tenis para hombre – Tiendas Branchos</h1>
<p class="sub">Extracción del {html.escape(str(df['fecha_extraccion'].iloc[0]))} ·
Programación para Análisis de Datos – IU Digital ·
Kevin Daniel Sepúlveda Giraldo y Jessica Serna Vargas (Grupo 9)</p>
<div class="kpis">{tarjetas_html}</div>
<img src="rangos.png" alt="Rangos de precio">
<h2>Por marca</h2>
{_tabla_html(marcas_html, COLS_MARCA)}
<img src="marcas.png" alt="Marcas">
<h2>Los 10 descuentos más altos</h2>
{_tabla_html(top_desc, ["nombre", "marca", "precio", "precio_antes", "descuento_pct"])}
<h2>Histórico de extracciones</h2>
{_tabla_html(historico, list(historico.columns))}
{bloque_hist}
<p><a href="tenis_branchos_actual.csv">Descargar el dataset (CSV)</a> ·
<a href="indicadores.json">Indicadores (JSON)</a></p>
<footer>Versión {html.escape(version)} · generado {datetime.now():%Y-%m-%d %H:%M} por GitHub Actions</footer>
</body></html>"""
    (salida / "index.html").write_text(pagina, encoding="utf-8")
    return salida / "index.html"
