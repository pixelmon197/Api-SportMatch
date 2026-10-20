from datetime import datetime, timezone

from database import db

# `amistades.estado` NO tiene CHECK en Neon: este catálogo lo define la API.
ESTADOS_AMISTAD = ("pendiente", "aceptada", "rechazada")


class Amistad(db.Model):
    """Tabla `amistades`. Una amistad es simétrica: la fila puede estar
    como (usuario_id=A, amigo_id=B) o (B, A); `UNIQUE(usuario_id, amigo_id)`
    solo evita repetir el mismo sentido. `usuario_id` es quien envía la
    solicitud y `amigo_id` quien la recibe."""

    __tablename__ = "amistades"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    amigo_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="pendiente")
    creado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    respondida_en = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "amigo_id": self.amigo_id,
            "estado": self.estado,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "respondida_en": self.respondida_en.isoformat() if self.respondida_en else None,
        }


class Seguidor(db.Model):
    """Tabla `seguidores`: relación de un solo sentido (seguir no requiere
    aprobación, a diferencia de la amistad). PK real compuesta
    (seguidor_id, seguido_id), sin `id` propio; Neon impide seguirse a uno
    mismo (CHECK)."""

    __tablename__ = "seguidores"

    seguidor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), primary_key=True)
    seguido_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), primary_key=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class Bloqueo(db.Model):
    """Tabla `bloqueos`. PK real compuesta (bloqueador_id, bloqueado_id),
    sin `id` propio (la documentación del proyecto decía que lo tenía)."""

    __tablename__ = "bloqueos"

    bloqueador_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), primary_key=True)
    bloqueado_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), primary_key=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
