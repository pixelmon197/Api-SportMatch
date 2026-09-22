from datetime import datetime, timezone

from database import db


class AceptacionLegal(db.Model):
    """Registro de aceptación de términos/privacidad (tabla `aceptaciones_legales`)."""

    __tablename__ = "aceptaciones_legales"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    documento = db.Column(db.String(50), nullable=False)  # terminos / privacidad
    version = db.Column(db.String(20), nullable=False)
    aceptado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    ip = db.Column(db.String(45), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "documento": self.documento,
            "version": self.version,
            "aceptado_en": self.aceptado_en.isoformat() if self.aceptado_en else None,
        }
