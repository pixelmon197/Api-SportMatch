import os
from datetime import timedelta

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    """Configuración base de Api-SportMatch."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "cambia-esta-clave-en-produccion")

    # Conexión a MySQL (esquema en sportmatch_schema.sql).
    # Se puede sobreescribir por completo con la variable de entorno DATABASE_URL,
    # o ajustar usuario/password/host/puerto/nombre de BD por separado.
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = os.environ.get("MYSQL_PORT", "3306")
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "sportmatch")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False

    # JWT (autenticación de usuarios)
    JWT_SECRET_KEY = os.environ.get(
        "JWT_SECRET_KEY", "cambia-esta-clave-jwt-en-produccion"
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
