from datetime import datetime, timezone

from werkzeug.security import generate_password_hash, check_password_hash

from database import db

# Valores válidos para `usuarios.rol` (ver docs/entidades_completas.md).
# "organizador" NO es un rol: es un perfil aparte (tabla `organizadores`)
# ligado a un usuario con estado_validacion propio (Fase 3).
ROLES_VALIDOS = ("usuario", "admin")

# Valores válidos para `usuarios.estado_cuenta`.
ESTADOS_CUENTA = ("activa", "suspendida", "eliminada")


class Usuario(db.Model):
    """Cuenta de la plataforma (tabla `usuarios` del modelo entidad-relación).

    Nombres de columna fieles al diagrama, salvo `contrasena_hash`
    (el diagrama la llama `constrasena`: aquí solo se guarda el hash,
    nunca la contraseña en claro).
    """

    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nombre_completo = db.Column(db.String(150), nullable=False)
    correo = db.Column(db.String(150), nullable=False, unique=True)
    contrasena_hash = db.Column(db.String(255), nullable=False)
    fecha_de_nacimiento = db.Column(db.Date, nullable=True)
    sexo = db.Column(db.String(20), nullable=True)
    rol = db.Column(db.String(20), nullable=False, default="usuario")
    estado_cuenta = db.Column(db.String(20), nullable=False, default="activa")
    correo_verificado_en = db.Column(db.DateTime, nullable=True)
    registro_completo_en = db.Column(db.DateTime, nullable=True)
    ultimo_acceso = db.Column(db.DateTime, nullable=True)
    nombre_usuario = db.Column(db.String(50), nullable=False, unique=True)
    telefono = db.Column(db.String(20), nullable=True)
    ciudad_id = db.Column(db.Integer, db.ForeignKey("ciudades.id"), nullable=True)
    idioma = db.Column(db.String(10), nullable=False, default="es")
    zona_horaria = db.Column(db.String(50), nullable=False, default="America/Mexico_City")
    codigo_referido = db.Column(db.String(20), nullable=True, unique=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    actualizado_en = db.Column(
        db.DateTime, nullable=True, onupdate=lambda: datetime.now(timezone.utc)
    )
    eliminado_en = db.Column(db.DateTime, nullable=True)  # borrado suave

    ciudad = db.relationship("Ciudad")
    deportes = db.relationship("UsuarioDeporte", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.contrasena_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.contrasena_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "nombre_completo": self.nombre_completo,
            "correo": self.correo,
            "nombre_usuario": self.nombre_usuario,
            "fecha_de_nacimiento": self.fecha_de_nacimiento.isoformat()
            if self.fecha_de_nacimiento
            else None,
            "sexo": self.sexo,
            "rol": self.rol,
            "estado_cuenta": self.estado_cuenta,
            "correo_verificado": self.correo_verificado_en is not None,
            "ultimo_acceso": self.ultimo_acceso.isoformat() if self.ultimo_acceso else None,
            "telefono": self.telefono,
            "ciudad": self.ciudad.to_dict() if self.ciudad else None,
            "idioma": self.idioma,
            "zona_horaria": self.zona_horaria,
            "codigo_referido": self.codigo_referido,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "actualizado_en": self.actualizado_en.isoformat() if self.actualizado_en else None,
        }
