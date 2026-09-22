from datetime import datetime, timezone

from database import db


class Dispositivo(db.Model):
    """Dispositivos del usuario para notificaciones push (tabla `Dispositivos`)."""

    __tablename__ = "dispositivos"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    plataforma = db.Column(db.String(20), nullable=False)  # ios / android / web
    token_push = db.Column(db.String(255), nullable=True)
    modelo = db.Column(db.String(100), nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    ultimo_uso_en = db.Column(db.DateTime, nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    usuario = db.relationship("Usuario")

    def to_dict(self):
        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "plataforma": self.plataforma,
            "modelo": self.modelo,
            "activo": self.activo,
            "ultimo_uso_en": self.ultimo_uso_en.isoformat() if self.ultimo_uso_en else None,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }
