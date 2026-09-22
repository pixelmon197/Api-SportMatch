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
