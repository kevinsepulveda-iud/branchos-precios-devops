# Imagen para correr el pipeline igual en cualquier máquina (mi PC, Colab o un servidor).
#   docker build -t branchos-precios .
#   docker run --rm -v "$(pwd)/data:/app/data" branchos-precios
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY scripts/ scripts/

# Por defecto extrae el catálogo y genera el sitio en /app/site
CMD ["sh", "-c", "python scripts/extraer.py && python scripts/publicar.py --salida site"]
