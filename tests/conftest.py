import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def html_pagina():
    """Página real de Branchos recortada a 3 productos."""
    return (FIXTURES / "pagina_branchos.html").read_text(encoding="utf-8")


@pytest.fixture
def html_vacio():
    """Así responde la tienda cuando falla su caché: HTML sin productos."""
    return "<html><head></head><body><p>Sin resultados</p></body></html>"


class RespuestaFalsa:
    def __init__(self, texto, codigo=200):
        self.text = texto
        self.status_code = codigo


class SesionFalsa:
    """Reemplaza a requests en las pruebas: devuelve respuestas en el orden que le doy."""

    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        return self.respuestas.pop(0)


@pytest.fixture
def sesion_falsa():
    return SesionFalsa


@pytest.fixture
def respuesta():
    return RespuestaFalsa
