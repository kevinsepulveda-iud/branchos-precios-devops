import pandas as pd
import pytest

from branchos import config, limpieza, scraper


@pytest.mark.parametrize("entrada,esperado", [
    ("$ 191.200,00", 191200),
    ("$ 215.200", 215200),
    ("191200", 191200),
    (263200, 263200),
    (263200.0, 263200),
    ("", None),
    (None, None),
    (float("nan"), None),
])
def test_a_pesos(entrada, esperado):
    assert limpieza.a_pesos(entrada) == esperado


@pytest.mark.parametrize("nombre,tipo", [
    ("Nike Tenis Revolution 8 Hombre Negro", "Tenis"),
    ("Nike Teniguayo Total 90 Hombre Cafe", "Teniguayos"),
    ("Fila Botas Netball Classic Hombre Blanco", "Botas"),
    ("Adidas Guayos Predator Hombre", "Guayos"),
    ("Treme Sandalias Playa", "Sandalias"),
    ("Reebok Semibotas Press Hombre Blanco", "Botas"),
    ("Fila Tenisguayos Drad Tf Hombre Gris", "Teniguayos"),
    ("Nike Killshot 2 Leather Hombre Beige", "Tenis"),   # sin tipo en el nombre
    ("", "Otro"),
    (None, "Otro"),
])
def test_tipo_calzado(nombre, tipo):
    assert limpieza.tipo_calzado(nombre) == tipo


def test_calcular_descuento():
    assert limpieza.calcular_descuento(263200, 359000) == 26.7
    assert limpieza.calcular_descuento(100, 100) == 0.0
    assert limpieza.calcular_descuento(120, 100) == 0.0      # precio "antes" menor: no es rebaja
    assert limpieza.calcular_descuento(100, None) == 0.0


def test_limpiar_quita_duplicados_y_registros_invalidos(html_pagina):
    registros = scraper.parsear_pagina(html_pagina, 1)
    registros += [dict(registros[0])]                                       # duplicado
    registros += [{"nombre": "", "precio": 1000, "url": "x"}]              # sin nombre
    registros += [{"nombre": "Algo", "precio": None, "url": "y"}]          # sin precio
    df = limpieza.limpiar(registros, "2026-11-09")
    assert len(df) == 3
    assert list(df.columns) == config.COLUMNAS
    assert set(df["marca"]) == {"Nike", "Fila"}
    assert df.loc[df["sku"] == "154300", "descuento_pct"].item() == 26.7
    assert (df["fecha_extraccion"] == "2026-11-09").all()


def test_limpiar_lista_vacia():
    df = limpieza.limpiar([], "2026-11-09")
    assert df.empty and list(df.columns) == config.COLUMNAS


def test_validar_dataset_correcto(html_pagina):
    df = limpieza.limpiar(scraper.parsear_pagina(html_pagina, 1), "2026-11-09")
    assert limpieza.validar(df, total_reportado=3) == []


def test_validar_detecta_extraccion_incompleta(html_pagina):
    # Es el caso de la EA1: la primera ejecución se detuvo en la página 8
    df = limpieza.limpiar(scraper.parsear_pagina(html_pagina, 1), "2026-11-09")
    problemas = limpieza.validar(df, total_reportado=560)
    assert any("560" in p for p in problemas)


def test_validar_dataset_vacio():
    assert limpieza.validar(pd.DataFrame()) == ["El dataset está vacío"]
