"""Aplicación web con Flask: el mismo buscador de GitHub Pages, pero como servicio.

Rutas:
    /                        la aplicación (app/index.html)
    /datos/catalogo.json     catálogo con historial (lo arma catalogo.py)
    /api/productos           búsqueda con filtros por parámetros (?q=&marca=&tipo=&max=&orden=)
    /api/productos/<sku>     un producto con su historial
    /salud                   estado del servicio (lo usan Docker y el pipeline)

Configuración por variables de entorno (así se cambia sin tocar código):
    BRANCHOS_DATOS    carpeta con historico/ (por defecto data/)
    BRANCHOS_VERSION  versión que se muestra en /salud (el pipeline pasa el SHA del commit)
"""

import os
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory

from branchos import catalogo as cat

RAIZ = Path(__file__).resolve().parents[2]
CARPETA_APP = RAIZ / "app"
ORDENES = {
    "precio": ("precio", False),
    "-precio": ("precio", True),
    "descuento": ("descuento_pct", True),
    "variacion": ("variacion_pct", False),
}


def filtrar(productos, q="", marca="", tipo="", precio_max=None, orden="descuento"):
    """Misma lógica de filtros que usa app/app.js en el navegador."""
    q = q.strip().lower()
    salida = [
        p for p in productos
        if (not q or q in p["nombre"].lower())
        and (not marca or p["marca"] == marca)
        and (not tipo or p["tipo"] == tipo)
        and (precio_max is None or p["precio"] <= precio_max)
    ]
    campo, descendente = ORDENES.get(orden, ORDENES["descuento"])
    # los productos sin variación (nuevos) van al final en cualquier orden
    con_valor = [p for p in salida if p[campo] is not None]
    sin_valor = [p for p in salida if p[campo] is None]
    return sorted(con_valor, key=lambda p: p[campo], reverse=descendente) + sin_valor


def create_app(carpeta_datos=None, version=None):
    carpeta_datos = Path(carpeta_datos or os.environ.get("BRANCHOS_DATOS", RAIZ / "data"))
    version = version or os.environ.get("BRANCHOS_VERSION", "local")

    app = Flask(__name__, static_folder=None)
    # el catálogo se arma una vez al iniciar; los datos cambian una vez por semana
    datos = cat.construir_catalogo(cat.cargar_extracciones(carpeta_datos / "historico"), version)
    app.config["CATALOGO"] = datos

    @app.get("/")
    def inicio():
        return send_from_directory(CARPETA_APP, "index.html")

    @app.get("/<path:archivo>")
    def estaticos(archivo):
        return send_from_directory(CARPETA_APP, archivo)

    @app.get("/datos/catalogo.json")
    def catalogo_json():
        return jsonify(datos)

    @app.get("/api/productos")
    def api_productos():
        precio_max = request.args.get("max", type=int)
        lista = filtrar(
            datos["productos"],
            q=request.args.get("q", ""),
            marca=request.args.get("marca", ""),
            tipo=request.args.get("tipo", ""),
            precio_max=precio_max,
            orden=request.args.get("orden", "descuento"),
        )
        return jsonify({"total": len(lista), "productos": lista})

    @app.get("/api/productos/<int:sku>")
    def api_producto(sku):
        for p in datos["productos"]:
            if p["sku"] == sku:
                return jsonify(p)
        abort(404)

    @app.get("/salud")
    def salud():
        # responde 200 mientras el servicio esté arriba; si los datos están viejos lo dice en
        # "estado" y el workflow de monitoreo es el que falla y avisa
        return jsonify(cat.estado_salud(datos))

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
