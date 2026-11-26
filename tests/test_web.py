"""Pruebas del catálogo con historial y de la aplicación web (EA3).

Uso extracciones pequeñas escritas en una carpeta temporal para no depender
del tamaño de data/ y poder probar casos puntuales: un producto que bajó, uno
que subió y uno que apareció esta semana.
"""

from datetime import date

import pandas as pd
import pytest

from branchos import catalogo as cat
from branchos.web import create_app, filtrar

COLUMNAS = ["fecha_extraccion", "sku", "nombre", "marca", "tipo", "precio", "precio_antes",
            "descuento_pct", "tallas_disponibles", "url", "pagina"]


def _fila(fecha, sku, nombre, marca, precio, antes):
    desc = round((1 - precio / antes) * 100, 1)
    return [fecha, sku, nombre, marca, "Tenis", precio, antes, desc, 5, f"https://x/{sku}/p", 1]


@pytest.fixture
def carpeta_datos(tmp_path):
    historico = tmp_path / "historico"
    historico.mkdir()
    semana1 = [
        _fila("2026-11-16", 1, "Nike Court Vision", "Nike", 300000, 500000),
        _fila("2026-11-16", 2, "Fila Netball", "Fila", 200000, 250000),
    ]
    semana2 = [
        _fila("2026-11-23", 1, "Nike Court Vision", "Nike", 240000, 500000),  # bajó 20 %
        _fila("2026-11-23", 2, "Fila Netball", "Fila", 210000, 250000),       # subió 5 %
        _fila("2026-11-23", 3, "Treme Urban", "Treme", 99000, 150000),        # nuevo
    ]
    for nombre, filas in [("tenis_2026-11-16.csv", semana1), ("tenis_2026-11-23.csv", semana2)]:
        pd.DataFrame(filas, columns=COLUMNAS).to_csv(historico / nombre, sep=";", index=False,
                                                     encoding="utf-8-sig")
    return tmp_path


@pytest.fixture
def datos(carpeta_datos):
    return cat.construir_catalogo(cat.cargar_extracciones(carpeta_datos / "historico"), "abc1234")


@pytest.fixture
def cliente(carpeta_datos):
    app = create_app(carpeta_datos, version="abc1234")
    app.config["TESTING"] = True
    return app.test_client()


def test_catalogo_une_historial_por_sku(datos):
    nike = next(p for p in datos["productos"] if p["sku"] == 1)
    assert [h["precio"] for h in nike["historial"]] == [300000, 240000]
    assert nike["variacion_pct"] == -20.0
    assert datos["ultima_extraccion"] == "2026-11-23"


def test_producto_nuevo_no_tiene_variacion_inventada(datos):
    nuevo = next(p for p in datos["productos"] if p["sku"] == 3)
    assert nuevo["variacion_pct"] is None
    assert len(nuevo["historial"]) == 1


def test_resumen_cambios(datos):
    esperado = {"comparables": 2, "bajaron": 1, "subieron": 1, "iguales": 0, "nuevos": 1}
    assert cat.resumen_cambios(datos) == esperado


def test_sin_extracciones_falla(tmp_path):
    with pytest.raises(ValueError):
        cat.construir_catalogo({})


def test_salud_detecta_datos_viejos(datos):
    assert cat.estado_salud(datos, hoy=date(2026, 11, 24))["estado"] == "ok"
    viejo = cat.estado_salud(datos, hoy=date(2026, 12, 10))
    assert viejo["estado"] == "datos_desactualizados"
    assert viejo["dias_desde_extraccion"] == 17


def test_filtrar_por_marca_y_precio(datos):
    assert [p["sku"] for p in filtrar(datos["productos"], marca="Nike")] == [1]
    assert {p["sku"] for p in filtrar(datos["productos"], precio_max=210000)} == {2, 3}


def test_filtrar_ordena_por_variacion_y_deja_nuevos_al_final(datos):
    orden = [p["sku"] for p in filtrar(datos["productos"], orden="variacion")]
    assert orden == [1, 2, 3]


def test_busqueda_no_distingue_mayusculas(datos):
    assert [p["sku"] for p in filtrar(datos["productos"], q="COURT")] == [1]


def test_ruta_salud(cliente):
    r = cliente.get("/salud")
    assert r.status_code == 200
    assert r.get_json()["version"] == "abc1234"
    assert r.get_json()["productos"] == 3


def test_ruta_api_productos_con_filtros(cliente):
    r = cliente.get("/api/productos?marca=Fila")
    assert r.get_json()["total"] == 1
    assert r.get_json()["productos"][0]["nombre"] == "Fila Netball"


def test_ruta_producto_inexistente_da_404(cliente):
    assert cliente.get("/api/productos/999").status_code == 404
    assert cliente.get("/api/productos/1").get_json()["sku"] == 1


def test_la_app_y_su_catalogo_se_sirven(cliente):
    assert b"Buscador de precios" in cliente.get("/").data
    assert cliente.get("/app.js").status_code == 200
    assert len(cliente.get("/datos/catalogo.json").get_json()["productos"]) == 3


def test_catalogo_real_del_repositorio():
    """Con los datos versionados: cada SKU de la última extracción tiene historial."""
    from branchos.web import RAIZ

    extracciones = cat.cargar_extracciones(RAIZ / "data" / "historico")
    datos = cat.construir_catalogo(extracciones)
    assert len(datos["productos"]) == len(extracciones[datos["ultima_extraccion"]])
    assert all(p["historial"][-1]["fecha"] == datos["ultima_extraccion"] for p in datos["productos"])
