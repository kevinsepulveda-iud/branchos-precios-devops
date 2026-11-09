"""Preparación de los datos (fase 3 de CRISP-DM).

Son las mismas reglas de limpieza de la EA1, ahora en funciones con pruebas.
"""

import re

import pandas as pd

from branchos import config

# La categoría mezcla tenis, botas, guayos y sandalias; saco el tipo del nombre
TIPOS = {
    "tenis": "Tenis", "teniguayo": "Teniguayos", "teniguayos": "Teniguayos",
    "tenisguayos": "Teniguayos", "semibotas": "Botas",
    "bota": "Botas", "botas": "Botas", "guayo": "Guayos", "guayos": "Guayos",
    "sandalia": "Sandalias", "sandalias": "Sandalias",
    "chancla": "Chanclas", "chanclas": "Chanclas",
}
_PATRON_TIPO = re.compile(r"\b(" + "|".join(sorted(TIPOS, key=len, reverse=True)) + r")\b")


def a_pesos(valor):
    """Convierte '$ 191.200,00', '191200' o 191200.0 en el entero 191200.

    En Colombia el punto separa miles y la coma los decimales, entonces corto en la coma.
    """
    if valor is None:
        return None
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        if pd.isna(valor):
            return None
        return int(round(valor))
    texto = str(valor).split(",")[0]
    digitos = re.sub(r"[^\d]", "", texto)
    return int(digitos) if digitos else None


def tipo_calzado(nombre):
    """Tipo de calzado según el nombre.

    Algunos productos no dicen el tipo ("Nike Killshot 2 Leather"); como la
    categoría que recorro es /hombres/tenis, en ese caso los dejo como Tenis.
    """
    if not isinstance(nombre, str) or not nombre.strip():
        return "Otro"
    encontrado = _PATRON_TIPO.search(nombre.lower())
    return TIPOS[encontrado.group(1)] if encontrado else "Tenis"


def calcular_descuento(precio, precio_antes):
    """Porcentaje de rebaja frente al precio tachado (0 si no hay rebaja)."""
    if precio is None or precio_antes is None or pd.isna(precio) or pd.isna(precio_antes):
        return 0.0
    if precio_antes <= 0 or precio >= precio_antes:
        return 0.0
    return round((1 - precio / precio_antes) * 100, 1)


def limpiar(registros, fecha):
    """Convierte la lista de registros del scraper en el dataset limpio.

    - precios a número y sin registros sin nombre o sin precio
    - sin duplicados (misma URL)
    - marca en formato título, tipo de calzado y descuento calculado
    """
    df = pd.DataFrame(registros)
    if df.empty:
        return pd.DataFrame(columns=config.COLUMNAS)

    for col in ["precio", "precio_antes"]:
        df[col] = df[col].apply(a_pesos).astype("Int64") if col in df else pd.NA
    df["tallas_disponibles"] = pd.to_numeric(df.get("tallas_disponibles"), errors="coerce")

    df = df.dropna(subset=["nombre", "precio"])
    df = df[(df["nombre"].str.strip() != "") & (df["precio"] > 0)]
    df = df.drop_duplicates(subset="url").reset_index(drop=True)

    df["marca"] = df["marca"].fillna("Sin marca").str.strip().str.title()
    df["tipo"] = df["nombre"].apply(tipo_calzado)
    df["descuento_pct"] = [
        calcular_descuento(p, a) for p, a in zip(df["precio"], df["precio_antes"], strict=True)
    ]
    df["fecha_extraccion"] = str(fecha)
    return df.reindex(columns=config.COLUMNAS)


def validar(df, total_reportado=None, minimo_completitud=95.0):
    """Control de calidad del dataset. Devuelve la lista de problemas encontrados.

    Si la lista sale vacía el dataset se puede publicar; si no, el pipeline falla
    y GitHub Actions no despliega nada (así no se publica un dataset incompleto,
    que fue justo el error que casi entrego en la EA1).
    """
    problemas = []
    if df.empty:
        return ["El dataset está vacío"]
    clave = ["nombre", "marca", "precio", "url"]
    completitud = df[clave].notna().mean().mean() * 100
    if completitud < minimo_completitud:
        problemas.append(f"Completitud {completitud:.1f} % menor al {minimo_completitud} %")
    if df["url"].duplicated().any():
        problemas.append("Hay URLs duplicadas")
    if (df["precio"] <= 0).any():
        problemas.append("Hay precios en cero o negativos")
    if total_reportado:
        cobertura = len(df) / total_reportado * 100
        if cobertura < 95:
            problemas.append(
                f"Solo se extrajo el {cobertura:.1f} % de los {total_reportado} productos"
            )
    return problemas
