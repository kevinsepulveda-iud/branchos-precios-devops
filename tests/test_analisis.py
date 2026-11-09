import pandas as pd
import pytest

from branchos import analisis, reporte


@pytest.fixture
def catalogo():
    return pd.DataFrame({
        "fecha_extraccion": ["2026-11-09"] * 4,
        "url": ["a", "b", "c", "d"],
        "nombre": ["Nike Tenis A", "Nike Tenis B", "Fila Botas C", "Treme Tenis D"],
        "marca": ["Nike", "Nike", "Fila", "Treme"],
        "tipo": ["Tenis", "Tenis", "Botas", "Tenis"],
        "precio": [300_000, 200_000, 100_000, 400_000],
        "precio_antes": [400_000, 200_000, 200_000, None],
        "descuento_pct": [25.0, 0.0, 50.0, 0.0],
        "tallas_disponibles": [4, 6, 2, 8],
        "sku": ["1", "2", "3", "4"],
        "pagina": [1, 1, 1, 1],
    })


def test_indicadores(catalogo):
    ind = analisis.indicadores(catalogo)
    assert ind["referencias"] == 4
    assert ind["marcas"] == 3
    assert ind["precio_mediano"] == 250_000
    assert ind["pct_con_descuento"] == 50.0
    assert ind["descuento_promedio"] == 37.5
    assert ind["pct_descuento_50_o_mas"] == 25.0


def test_por_marca_ordena_por_referencias(catalogo):
    tabla = analisis.por_marca(catalogo)
    assert tabla.iloc[0]["marca"] == "Nike"
    assert tabla.iloc[0]["referencias"] == 2
    assert tabla.set_index("marca").loc["Nike", "descuento_promedio"] == 25.0


def test_rangos_suman_100(catalogo):
    rangos = analisis.rangos_precio(catalogo)
    assert rangos.sum() == pytest.approx(100)
    assert rangos["> $350 mil"] == 25.0


def test_comparar_extracciones(catalogo):
    anterior = catalogo.copy()
    anterior.loc[0, "precio"] = 350_000                                # a: bajó de precio
    anterior = pd.concat([anterior[anterior["url"] != "d"],            # d: producto nuevo
                          anterior.iloc[[0]].assign(url="z")])          # z: retirado
    cmp = analisis.comparar(catalogo, anterior)
    assert list(cmp["nuevos"]["url"]) == ["d"]
    assert list(cmp["retirados"]["url"]) == ["z"]
    assert cmp["en_comun"] == 3
    assert cmp["cambios_precio"].iloc[0]["variacion_pct"] == pytest.approx(-14.3)


def test_generar_sitio(catalogo, tmp_path):
    historico = pd.DataFrame({"fecha": ["2026-10-19", "2026-11-09"], "referencias": [593, 4],
                              "precio_mediano": [210_000, 250_000]})
    ruta = reporte.generar_sitio(catalogo, historico, tmp_path, version="abc123")
    contenido = ruta.read_text(encoding="utf-8")
    assert "Tiendas Branchos" in contenido and "abc123" in contenido
    for archivo in ["rangos.png", "marcas.png", "historico.png", "tenis_branchos_actual.csv",
                    "indicadores.json"]:
        assert (tmp_path / archivo).exists()
