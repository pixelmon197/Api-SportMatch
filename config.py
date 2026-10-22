import os
from datetime import timedelta

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    """Configuración base de Api-SportMatch."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "cambia-esta-clave-en-produccion")

    # Conexión a PostgreSQL (Neon). Ver docs/entidades_completas.md para el
    # catálogo completo de tablas del modelo entidad-relación.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False

    # JWT
    JWT_SECRET_KEY = os.environ.get(
        "JWT_SECRET_KEY", "cambia-esta-clave-jwt-en-produccion"
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)

    # Subida de archivos: tope global del request (el máximo real por tipo, p. ej.
    # 8 MB para imágenes, se valida en routes/archivos.py). Flask responde 413
    # solo si se supera este tope, antes de leer el archivo completo.
    MAX_CONTENT_LENGTH = 210 * 1024 * 1024

    # Pagos
    # Comisión de la plataforma (%) cuando no hay ninguna vigente en la tabla
    # `comisiones`. Un admin la define con POST /api/comisiones.
    COMISION_POR_DEFECTO = os.environ.get("COMISION_POR_DEFECTO", "10")
    # Pasarela de tarjeta SIMULADA (POST /api/pagos/{id}/simular-pago). Sirve
    # para probar el flujo sin una pasarela real. En producción poner
    # SIMULAR_PASARELA=false: así nadie puede marcar un pago como pagado sin pagar.
    SIMULAR_PASARELA = os.environ.get("SIMULAR_PASARELA", "true").strip().lower() in ("1", "true", "si", "sí", "yes")
