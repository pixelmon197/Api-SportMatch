import secrets
from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash, check_password_hash

from database import db

# Tipos válidos (tabla `tockens_verificacion` en el diagrama).
TIPOS_TOKEN = ("verificar_correo", "recuperar_contrasena", "cambiar_correo")


class TokenVerificacion(db.Model):
    __tablename__ = "tockens_verificacion"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    tipo = db.Column(db.String(30), nullable=False)
    token_hash = db.Column(db.String(255), nullable=False)
    correo_nuevo = db.Column(db.String(150), nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    expira_en = db.Column(db.DateTime, nullable=False)
    usado_en = db.Column(db.DateTime, nullable=True)

    usuario = db.relationship("Usuario")

    @staticmethod
    def generar(usuario_id, tipo, minutos_validez=30, correo_nuevo=None):
        """Crea un token, lo guarda hasheado y regresa el valor en claro (una sola vez)."""
        valor_plano = secrets.token_urlsafe(32)
        token = TokenVerificacion(
            usuario_id=usuario_id,
            tipo=tipo,
            token_hash=generate_password_hash(valor_plano),
            correo_nuevo=correo_nuevo,
            expira_en=datetime.now(timezone.utc) + timedelta(minutes=minutos_validez),
        )
        db.session.add(token)
        db.session.commit()
        return token, valor_plano

    def es_valido(self, valor_plano):
        if self.usado_en is not None:
            return False
        if datetime.now(timezone.utc) > self.expira_en.replace(tzinfo=timezone.utc):
            return False
        return check_password_hash(self.token_hash, valor_plano)

    def marcar_usado(self):
        self.usado_en = datetime.now(timezone.utc)
        db.session.commit()
