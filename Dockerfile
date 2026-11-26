# Imagen de la aplicación web (EA3). El pipeline la construye, la prueba y la
# publica en GitHub Container Registry (ghcr.io).
#
#   docker build -t branchos-precios .
#   docker run --rm -p 8000:8000 branchos-precios            # app en http://localhost:8000
#
# La misma imagen sigue sirviendo para correr el pipeline de la EA2:
#   docker run --rm -v "$(pwd)/data:/app/data" branchos-precios python scripts/extraer.py
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn==23.0.0

COPY src/ src/
COPY scripts/ scripts/
COPY app/ app/
COPY data/ data/

# Configuración por variables de entorno (se pueden cambiar con docker run -e)
ARG VERSION=local
ENV PYTHONPATH=/app/src \
    BRANCHOS_DATOS=/app/data \
    BRANCHOS_VERSION=${VERSION} \
    PORT=8000

# No corro el servicio como root
RUN useradd --create-home app && chown -R app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://localhost:' + os.environ['PORT'] + '/salud', timeout=4)"

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 2 'branchos.web:create_app()'"]
