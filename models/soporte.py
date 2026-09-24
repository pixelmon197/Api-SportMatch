from datetime import datetime, timezone

from database import db

ESTADOS_REPORTE = ("pendiente", "en_revision", "resuelto", "desestimado")
ESTADOS_TICKET = ("abierto", "en_progreso", "resuelto", "cerrado")
PRIORIDADES_TICKET = ("baja", "media", "alta", "urgente")


class AuditoriaLog(db.Model):
    """Tabla `auditoria_log`: registro de acciones administrativas
    sensibles (cambios de rol, validación de organizadores, moderación).
    No se audita cada request, solo las acciones que puede necesitar
    revisar un administrador después.
    """

    __tablename__ = "auditoria_log"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    accion = db.Column(db.String(100), nullable=False)  # ej. "usuario.cambiar_rol"
    tipo_entidad = db.Column(db.String(50), nullable=False)  # ej. "usuario", "organizador"
    entidad_id = db.Column(db.Integer, nullable=True)  # genérico: no lleva FK real (polimórfico)
    datos_anteriores = db.Column(db.Text, nullable=True)  # JSON serializado
    datos_nuevos = db.Column(db.Text, nullable=True)  # JSON serializado
    ip = db.Column(db.String(45), nullable=True)
    registrada_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "accion": self.accion,
            "tipo_entidad": self.tipo_entidad,
            "entidad_id": self.entidad_id,
            "datos_anteriores": self.datos_anteriores,
            "datos_nuevos": self.datos_nuevos,
            "ip": self.ip,
            "registrada_en": self.registrada_en.isoformat() if self.registrada_en else None,
        }


class Reporte(db.Model):
    """Tabla `reportes`: cualquier usuario puede reportar contenido o a
    otro usuario (`tipo_entidad` + `entidad_id` son genéricos/polimórficos,
    sin FK real, ya que pueden apuntar a distintas tablas)."""

    __tablename__ = "reportes"

    id = db.Column(db.Integer, primary_key=True)
    reportante_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    asignado_a = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    tipo_entidad = db.Column(db.String(50), nullable=False)  # ej. "usuario", "evento", "ruta"
    entidad_id = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    estado = db.Column(db.String(20), nullable=False, default="pendiente")
    accion_tomada = db.Column(db.Text, nullable=True)
    notas_moderador = db.Column(db.Text, nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    resuelto_en = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "reportante_id": self.reportante_id,
            "asignado_a": self.asignado_a,
            "tipo_entidad": self.tipo_entidad,
            "entidad_id": self.entidad_id,
            "motivo": self.motivo,
            "descripcion": self.descripcion,
            "estado": self.estado,
            "accion_tomada": self.accion_tomada,
            "notas_moderador": self.notas_moderador,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "resuelto_en": self.resuelto_en.isoformat() if self.resuelto_en else None,
        }


class TicketSoporte(db.Model):
    __tablename__ = "tickets_soporte"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    asignado_a = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    categoria = db.Column(db.String(50), nullable=True)  # ej. "pagos", "cuenta", "evento"
    prioridad = db.Column(db.String(10), nullable=False, default="media")
    estado = db.Column(db.String(20), nullable=False, default="abierto")
    asunto = db.Column(db.String(150), nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    cerrado_en = db.Column(db.DateTime, nullable=True)

    mensajes = db.relationship(
        "TicketMensaje", order_by="TicketMensaje.creado_en", cascade="all, delete-orphan"
    )

    def to_dict(self, con_mensajes=False, incluir_internos=False):
        data = {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "asignado_a": self.asignado_a,
            "categoria": self.categoria,
            "prioridad": self.prioridad,
            "estado": self.estado,
            "asunto": self.asunto,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "cerrado_en": self.cerrado_en.isoformat() if self.cerrado_en else None,
        }
        if con_mensajes:
            mensajes = self.mensajes if incluir_internos else [m for m in self.mensajes if not m.es_interno]
            data["mensajes"] = [m.to_dict() for m in mensajes]
        return data


class TicketMensaje(db.Model):
    """Tabla `ticket_mensaje`. El diagrama trae columnas duplicadas de
    `tickets_soporte` (categoria, prioridad, estado, asunto...), claro
    artefacto de la herramienta de diagramado; aquí solo se modelan los
    campos propios: ticket_id, autor_id, mensaje, es_interno, creado_en.
    """

    __tablename__ = "ticket_mensaje"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets_soporte.id"), nullable=False)
    autor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    es_interno = db.Column(db.Boolean, nullable=False, default=False)  # nota solo visible para staff
    creado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    autor = db.relationship("Usuario")

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "autor_id": self.autor_id,
            "autor_nombre": self.autor.nombre_completo if self.autor else None,
            "mensaje": self.mensaje,
            "es_interno": self.es_interno,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }
