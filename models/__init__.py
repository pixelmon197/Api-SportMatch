# Importa aquí cada modelo para que SQLAlchemy lo registre en db.create_all().
# Catálogo completo de tablas del modelo entidad-relación: docs/entidades_completas.md
# (89 entidades en total; se irán incorporando por fases).

from models.ciudad import Ciudad
from models.usuario import Usuario, ROLES_VALIDOS, ESTADOS_CUENTA
from models.token_verificacion import TokenVerificacion, TIPOS_TOKEN
from models.dispositivo import Dispositivo
from models.aceptacion_legal import AceptacionLegal

__all__ = [
    "Ciudad",
    "Usuario",
    "ROLES_VALIDOS",
    "ESTADOS_CUENTA",
    "TokenVerificacion",
    "TIPOS_TOKEN",
    "Dispositivo",
    "AceptacionLegal",
]
