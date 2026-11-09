"""Indicadores del catálogo y comparación entre extracciones.

En la EA1 el análisis era de una sola foto (19 de octubre). Como ahora el
scraping corre cada semana con GitHub Actions, agrego la comparación entre
fechas: qué productos entraron, cuáles salieron y a cuáles les cambió el precio.
"""

import pandas as pd

RANGOS = [0, 150_000, 250_000, 350_000, float("inf")]
ETIQUETAS_RANGO = ["< $150 mil", "$150-250 mil", "$250-350 mil", "> $350 mil"]


def indicadores(df):
    """Indicadores generales (equivalentes a la Tabla 3 de la EA1)."""
    con_desc = df[df["descuento_pct"] > 0]
    return {
        "referencias": int(len(df)),
        "marcas": int(df["marca"].nunique()),
        "precio_promedio": int(round(df["precio"].mean())),
        "precio_mediano": int(round(df["precio"].median())),
        "precio_min": int(df["precio"].min()),
        "precio_max": int(df["precio"].max()),
        "pct_con_descuento": round(len(con_desc) / len(df) * 100, 1),
        "descuento_promedio": round(float(con_desc["descuento_pct"].mean()), 1) if len(con_desc) else 0.0,
        "pct_descuento_50_o_mas": round((df["descuento_pct"] >= 50).mean() * 100, 1),
        "tallas_promedio": round(float(df["tallas_disponibles"].mean()), 1),
    }


def por_marca(df):
    """Referencias, precio, descuento y tallas promedio por marca (Tabla 4 de la EA1)."""
    tabla = (
        df.groupby("marca")
        .agg(
            referencias=("url", "count"),
            precio_promedio=("precio", "mean"),
            descuento_promedio=("descuento_pct", lambda s: s[s > 0].mean() if (s > 0).any() else 0),
            tallas_promedio=("tallas_disponibles", "mean"),
        )
        .sort_values("referencias", ascending=False)
    )
    tabla["precio_promedio"] = tabla["precio_promedio"].round(0).astype(int)
    tabla["descuento_promedio"] = tabla["descuento_promedio"].astype(float).round(1)
    tabla["tallas_promedio"] = tabla["tallas_promedio"].round(1)
    return tabla.reset_index()


def rangos_precio(df):
    """Porcentaje de referencias en cada rango de precio."""
    rangos = pd.cut(df["precio"].astype(float), bins=RANGOS, labels=ETIQUETAS_RANGO, right=False)
    return (rangos.value_counts(normalize=True).reindex(ETIQUETAS_RANGO) * 100).round(1)


def comparar(actual, anterior):
    """Compara dos extracciones por URL.

    Devuelve un diccionario con los productos nuevos, los retirados y los que
    cambiaron de precio (con la variación en porcentaje).
    """
    urls_act, urls_ant = set(actual["url"]), set(anterior["url"])
    cruce = actual.merge(anterior[["url", "precio"]], on="url", suffixes=("", "_anterior"))
    cambios = cruce[cruce["precio"] != cruce["precio_anterior"]].copy()
    cambios["variacion_pct"] = (
        (cambios["precio"] / cambios["precio_anterior"] - 1) * 100
    ).astype(float).round(1)
    return {
        "nuevos": actual[actual["url"].isin(urls_act - urls_ant)],
        "retirados": anterior[anterior["url"].isin(urls_ant - urls_act)],
        "en_comun": len(urls_act & urls_ant),
        "cambios_precio": cambios.sort_values("variacion_pct"),
    }
