import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from database import db

# Tipos válidos. OJO: en Neon existen DOS tablas por un rediseño a medias:
#   - `tockens_verificacion` (con el typo del diagrama original, sin CHECK
#     de tipo) -> ya NO se usa.
#   - `tokens_verificacion` (ortografía correcta, con CHECK real) -> es la
#     tabla vigente; sus valores de `tipo` son distintos a los del diagrama.
TIPOS_TOKEN = ("verificacion_correo", "restablecer_contrasena", "cambio_correo")


class TokenVerificacion(db.Model):
    __tablename__ = "tokens_verificacion"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    tipo = db.Column(db.String(30), nullable=False)
    # varchar(64) en Neon -> se guarda un hash SHA-256 (hexdigest de 64
    # caracteres), no el hash salteado de werkzeug (mucho más largo).
    # Como es determinista, permite buscar el registro directamente por
    # hash sin tener que probarlo contra todos los tokens activos.
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    correo_nuevo = db.Column(db.String(150), nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    expira_en = db.Column(db.DateTime, nullable=False)
    usado_en = db.Column(db.DateTime, nullable=True)

    usuario = db.relationship("Usuario")

    @staticmethod
    def _hash(valor_plano: str) -> str:
        return hashlib.sha256(valor_plano.encode("utf-8")).hexdigest()

    @staticmethod
    def generar(usuario_id, tipo, minutos_validez=30, correo_nuevo=None):
        """Crea un token, guarda su hash SHA-256 y regresa (token, valor_plano).

        `valor_plano` solo existe en este momento: es lo que se le manda al
        usuario (por correo, en producción); en la base solo queda el hash.
        """
        valor_plano = secrets.token_urlsafe(32)
        token = TokenVerificacion(
            usuario_id=usuario_id,
            tipo=tipo,
            token_hash=TokenVerificacion._hash(valor_plano),
            correo_nuevo=correo_nuevo,
            expira_en=datetime.now(timezone.utc) + timedelta(minutes=minutos_validez),
        )
        db.session.add(token)
        db.session.commit()
        return token, valor_plano

    @staticmethod
    def buscar_valido(tipo, valor_plano):
        """Busca el token por su hash y regresa el registro solo si es
        del tipo esperado, no ha sido usado y no ha expirado; si no,
        regresa None (token inválido/expirado/usado)."""
        token = TokenVerificacion.query.filter_by(
            token_hash=TokenVerificacion._hash(valor_plano), tipo=tipo
        ).first()
        if token is None or not token.es_valido():
            return None
        return token

    def es_valido(self) -> bool:
        if self.usado_en is not None:
            return False
        expira = self.expira_en
        if expira.tzinfo is None:
            expira = expira.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) <= expira

    def marcar_usado(self):
        self.usado_en = datetime.now(timezone.utc)
        db.session.commit()
