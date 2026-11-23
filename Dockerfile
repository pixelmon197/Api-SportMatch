
# Imagen de la API de SportMatch (Flask + Gunicorn).
#
# Construcción multietapa: la etapa "builder" instala las dependencias de
# Python en un entorno virtual y la etapa final solo copia ese entorno ya
# construido. Así la imagen final no arrastra los compiladores ni la caché de
# pip, y el proyecto sigue usando la misma versión de Python que runtime.txt
# (3.12), igual que el servicio desplegado en Render.

# ---------- Etapa 1: construcción de dependencias ----------
FROM python:3.12-slim AS builder

# Evita archivos .pyc y fuerza la salida sin búfer (los logs aparecen en
# `docker logs` en el momento, no al cerrar el contenedor).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# psycopg2-binary y Pillow traen ruedas precompiladas, pero build-essential y
# libpq-dev garantizan la compilación si alguna dependencia no la tiene.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Entorno virtual propio: se copia completo a la etapa final.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Se copia solo requirements.txt antes del código: mientras las dependencias
# no cambien, Docker reutiliza esta capa en caché y la construcción es rápida.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ---------- Etapa 2: imagen final de ejecución ----------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=5000

# libpq5 es la biblioteca cliente de PostgreSQL que psycopg2 necesita en
# tiempo de ejecución; curl se usa en la comprobación de salud (HEALTHCHECK).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Usuario sin privilegios: el contenedor no se ejecuta como root.
RUN useradd --create-home --shell /bin/bash sportmatch

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=sportmatch:sportmatch . .

# Carpeta de archivos subidos por los usuarios (fotos de perfil, evidencias de
# soporte). Se declara como volumen porque su contenido no debe vivir dentro
# de la imagen ni perderse al recrear el contenedor.
RUN mkdir -p /app/static/uploads \
    && chown -R sportmatch:sportmatch /app/static/uploads
VOLUME ["/app/static/uploads"]

USER sportmatch

EXPOSE 5000

# El endpoint /api/health de app.py responde {"status": "ok"}. Docker lo
# consulta periódicamente para marcar el contenedor como healthy o unhealthy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:5000/api/health || exit 1

# Gunicorn como servidor de producción (nunca `python app.py`, que arranca en
# modo debug). create_app() es la factoría de la aplicación Flask.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", \
     "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", \
     "app:create_app()"]
