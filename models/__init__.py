# Importa aquí cada modelo para que SQLAlchemy lo registre en db.create_all().
# Catálogo completo de tablas del modelo entidad-relación: docs/entidades_completas.md
# (89 entidades en total; se irán incorporando por fases).

from models.ciudad import Ciudad
from models.usuario import Usuario, ROLES_VALIDOS, ESTADOS_CUENTA, SEXOS_VALIDOS
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

# Fase 3 — Inscripciones y valoraciones
from models.inscripcion import (
    PaqueteRecuperacion,
    Inscripcion,
    ValoracionEvento,
    CalendarioUsuario,
    ESTADOS_INSCRIPCION,
)

# Fase 3 — Organizadores y validación
from models.organizador import (
    Organizador,
    OrganizadorMiembro,
    SolicitudValidacion,
    DocumentoValidacion,
    CuentaCobro,
    ESTADOS_VALIDACION_ORG,
    ESTADOS_SOLICITUD,
    ROLES_MIEMBRO_ORG,
)

# Fase 3 — Administración y soporte
from models.soporte import (
    AuditoriaLog,
    Reporte,
    TicketSoporte,
    TicketMensaje,
    ESTADOS_REPORTE,
    ESTADOS_TICKET,
    PRIORIDADES_TICKET,
)

__all__ = [
    "Ciudad",
    "Usuario",
    "ROLES_VALIDOS",
    "ESTADOS_CUENTA",
    "SEXOS_VALIDOS",
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
    "PaqueteRecuperacion",
    "Inscripcion",
    "ValoracionEvento",
    "CalendarioUsuario",
    "ESTADOS_INSCRIPCION",
    "Organizador",
    "OrganizadorMiembro",
    "SolicitudValidacion",
    "DocumentoValidacion",
    "CuentaCobro",
    "ESTADOS_VALIDACION_ORG",
    "ESTADOS_SOLICITUD",
    "ROLES_MIEMBRO_ORG",
    "AuditoriaLog",
    "Reporte",
    "TicketSoporte",
    "TicketMensaje",
    "ESTADOS_REPORTE",
    "ESTADOS_TICKET",
    "PRIORIDADES_TICKET",
]
