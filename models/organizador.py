from datetime import datetime, timezone

from database import db

# Valores válidos (deben coincidir con los CHECK reales de Neon).
# `sin_solicitud` es el default real en Neon: un organizador nuevo no tiene
# nada que revisar hasta que manda su primera solicitud.
ESTADOS_VALIDACION_ORG = ("sin_solicitud", "pendiente", "en_revision", "aprobada", "rechazada", "revocada")
ESTADOS_SOLICITUD = ("pendiente", "en_revision", "aprobada", "rechazada")
ROLES_MIEMBRO_ORG = ("propietario", "administrador", "colaborador")
TIPOS_DOCUMENTO_VALIDACION = ("ine", "curp", "comprobante_domicilio", "rfc", "permiso_evento")


class Organizador(db.Model):
    """Tabla `organizadores`: perfil de organizador de eventos, ligado a un
    usuario. Solo puede crear/publicar eventos si `estado_validacion` es
    'aprobado' (ver `SolicitudValidacion`).
    """

    __tablename__ = "organizadores"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, unique=True)
    nombre_comercial = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    correo_contacto = db.Column(db.String(150), nullable=True)
    telefono_contacto = db.Column(db.String(20), nullable=True)
    ciudad_id = db.Column(db.Integer, db.ForeignKey("ciudades.id"), nullable=True)
    logo_id = db.Column(db.Integer, nullable=True)  # futura FK a `archivos`
    estado_validacion = db.Column(db.String(20), nullable=False, default="sin_solicitud")
    validado_en = db.Column(db.DateTime, nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    # En Neon es NOT NULL DEFAULT CURRENT_TIMESTAMP; sin `default` aquí,
    # SQLAlchemy manda NULL explícito y la BD lo rechaza (mismo bug que ya
    # se corrigió en Usuario y Evento).
    actualizado_en = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    eliminado_en = db.Column(db.DateTime, nullable=True)

    ciudad = db.relationship("Ciudad")
    miembros = db.relationship("OrganizadorMiembro", cascade="all, delete-orphan")

    def to_dict(self, detalle=False):
        data = {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "nombre_comercial": self.nombre_comercial,
            "descripcion": self.descripcion,
            "correo_contacto": self.correo_contacto,
            "telefono_contacto": self.telefono_contacto,
            "ciudad": self.ciudad.to_dict() if self.ciudad else None,
            "estado_validacion": self.estado_validacion,
            "validado_en": self.validado_en.isoformat() if self.validado_en else None,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }
        if detalle:
            data["miembros"] = [m.to_dict() for m in self.miembros]
        return data


class OrganizadorMiembro(db.Model):
    """Tabla `organizador_miembros`: usuarios con acceso a administrar un
    organizador (PK compuesta)."""

    __tablename__ = "organizador_miembros"

    organizador_id = db.Column(db.Integer, db.ForeignKey("organizadores.id"), primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), primary_key=True)
    rol = db.Column(db.String(20), nullable=False, default="colaborador")
    agregado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    usuario = db.relationship("Usuario")

    def to_dict(self):
        return {
            "organizador_id": self.organizador_id,
            "usuario_id": self.usuario_id,
            "nombre_usuario": self.usuario.nombre_usuario if self.usuario else None,
            "rol": self.rol,
            "agregado_en": self.agregado_en.isoformat() if self.agregado_en else None,
        }


class SolicitudValidacion(db.Model):
    """Tabla `solicitudes_validacion`: pide que un admin revise y apruebe
    a un organizador (con documentos de soporte)."""

    __tablename__ = "solicitudes_validacion"

    id = db.Column(db.Integer, primary_key=True)
    organizador_id = db.Column(db.Integer, db.ForeignKey("organizadores.id"), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="pendiente")
    revisor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    comentarios = db.Column(db.Text, nullable=True)
    motivo_rechazo = db.Column(db.Text, nullable=True)
    enviada_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    resuelta_en = db.Column(db.DateTime, nullable=True)

    documentos = db.relationship("DocumentoValidacion", cascade="all, delete-orphan")

    def to_dict(self, con_documentos=False):
        data = {
            "id": self.id,
            "organizador_id": self.organizador_id,
            "estado": self.estado,
            "revisor_id": self.revisor_id,
            "comentarios": self.comentarios,
            "motivo_rechazo": self.motivo_rechazo,
            "enviada_en": self.enviada_en.isoformat() if self.enviada_en else None,
            "resuelta_en": self.resuelta_en.isoformat() if self.resuelta_en else None,
        }
        if con_documentos:
            data["documentos"] = [d.to_dict() for d in self.documentos]
        return data


class DocumentoValidacion(db.Model):
    __tablename__ = "documentos_validacion"

    id = db.Column(db.Integer, primary_key=True)
    solicitud_id = db.Column(db.Integer, db.ForeignKey("solicitudes_validacion.id"), nullable=False)
    tipo_documento = db.Column(db.String(50), nullable=False)  # ej. "ine", "constancia_fiscal"
    # NOT NULL en Neon: no hay todavía un módulo de subida de archivos, así
    # que las rutas deben exigir un archivo_id ya existente (ver validación
    # en routes/organizadores.py) en vez de dejarlo en None.
    archivo_id = db.Column(db.Integer, nullable=False)
    numero_documento = db.Column(db.String(50), nullable=True)
    verificado = db.Column(db.Boolean, nullable=False, default=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "tipo_documento": self.tipo_documento,
            "numero_documento": self.numero_documento,
            "verificado": self.verificado,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }


class CuentaCobro(db.Model):
    """Tabla `cuentas_cobro`: cuenta bancaria donde el organizador recibe
    sus liquidaciones (módulo de pagos, pendiente; el catálogo ya se puede
    ir armando)."""

    __tablename__ = "cuentas_cobro"

    id = db.Column(db.Integer, primary_key=True)
    organizador_id = db.Column(db.Integer, db.ForeignKey("organizadores.id"), nullable=False)
    banco = db.Column(db.String(50), nullable=False)
    titular = db.Column(db.String(150), nullable=False)
    clabe = db.Column(db.String(18), nullable=False)
    verificada = db.Column(db.Boolean, nullable=False, default=False)
    es_principal = db.Column(db.Boolean, nullable=False, default=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    eliminado_en = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "organizador_id": self.organizador_id,
            "banco": self.banco,
            "titular": self.titular,
            "clabe": f"******{self.clabe[-4:]}" if self.clabe else None,
            "verificada": self.verificada,
            "es_principal": self.es_principal,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }
