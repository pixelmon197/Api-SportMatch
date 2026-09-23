# Importa aquí cada modelo para que SQLAlchemy lo registre en db.create_all().
# Catálogo completo de tablas del modelo entidad-relación: docs/entidades_completas.md
# (89 entidades en total; se irán incorporando por fases).

from models.ciudad import Ciudad
from models.usuario import Usuario, ROLES_VALIDOS, ESTADOS_CUENTA
from models.token_verificacion import TokenVerificacion, TIPOS_TOKEN
from models.dispositivo import Dispositivo
from models.aceptacion_legal import AceptacionLegal

# Fase 3 — Deportes
from models.deporte import Deporte, UsuarioDeporte, NIVELES_DEPORTE

# Fase 3 — Cuestionario de registro
from models.cuestionario import (
    Cuestionario,
    Pregunta,
    OpcionRespuesta,
    RespuestaUsuario,
    TIPOS_PREGUNTA,
)

# Fase 3 — Eventos
from models.evento import (
    Evento,
    EventoDeporte,
    EventoRequisito,
    EventoSede,
    EventoFecha,
    EventoCategoria,
    EventoBoleto,
    ESTADOS_EVENTO,
    DIFICULTADES_EVENTO,
    TIPOS_SEDE,
    TIPOS_BOLETO,
)

# Fase 3 — Rutas
from models.ruta import Ruta, RutaPunto, EventoRuta, TIPOS_PUNTO_RUTA

__all__ = [
    "Ciudad",
    "Usuario",
    "ROLES_VALIDOS",
    "ESTADOS_CUENTA",
    "TokenVerificacion",
    "TIPOS_TOKEN",
    "Dispositivo",
    "AceptacionLegal",
    "Deporte",
    "UsuarioDeporte",
    "NIVELES_DEPORTE",
    "Cuestionario",
    "Pregunta",
    "OpcionRespuesta",
    "RespuestaUsuario",
    "TIPOS_PREGUNTA",
    "Evento",
    "EventoDeporte",
    "EventoRequisito",
    "EventoSede",
    "EventoFecha",
    "EventoCategoria",
    "EventoBoleto",
    "ESTADOS_EVENTO",
    "DIFICULTADES_EVENTO",
    "TIPOS_SEDE",
    "TIPOS_BOLETO",
    "Ruta",
    "RutaPunto",
    "EventoRuta",
    "TIPOS_PUNTO_RUTA",
]
