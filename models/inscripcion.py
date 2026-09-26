from datetime import datetime, timezone

from database import db

# Valores válidos (ver docs/entidades_completas.md).
ESTADOS_INSCRIPCION = ("pendiente", "confirmada", "lista_espera", "cancelada", "completada")


class PaqueteRecuperacion(db.Model):
    """Tabla `paquete_recuperacion`: paquete opcional que un usuario puede
    agregar a su inscripción (ej. "kit básico" / "kit premium" con playera,
    medalla, etc.). `paquete_items` (liga a variantes de producto de la
    tienda) queda pendiente hasta construir el módulo de tienda.
    """

    __tablename__ = "paquete_recuperacion"

    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("eventos.id"), nullable=False)
    nivel = db.Column(db.String(30), nullable=True)  # ej. "basico", "premium"
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    precio = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    moneda = db.Column(db.String(3), nullable=False, default="MXN")
    activo = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "evento_id": self.evento_id,
            "nivel": self.nivel,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "precio": float(self.precio) if self.precio is not None else None,
            "moneda": self.moneda,
            "activo": self.activo,
        }


class Inscripcion(db.Model):
    """Tabla `inscripciones`. `numero_particpante` del diagrama (con typo)
    se guarda como `numero_participante`, igual que se hizo con
    `contrasena_hash` en Fase 2. `pago_id` no existe todavía: el módulo de
    pagos es de una fase posterior; por ahora el estado se mueve a mano
    (pendiente -> confirmada) y ahí se conectará con el cobro real.
    """

    __tablename__ = "inscripciones"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey("eventos.id"), nullable=False)
    fecha_id = db.Column(db.Integer, db.ForeignKey("evento_fechas.id"), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey("evento_categorias.id"), nullable=False)
    boleto_id = db.Column(db.Integer, db.ForeignKey("evento_boletos.id"), nullable=False)
    paquete_id = db.Column(db.Integer, db.ForeignKey("paquete_recuperacion.id"), nullable=True)

    estado = db.Column(db.String(20), nullable=False, default="pendiente")
    numero_participante = db.Column(db.String(20), nullable=True)  # "número de corredor"/bib
    inscrita_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    cancelada_en = db.Column(db.DateTime, nullable=True)
    asistio_en = db.Column(db.DateTime, nullable=True)
    asistencia_latitud = db.Column(db.Numeric(9, 6), nullable=True)
    asistencia_longitud = db.Column(db.Numeric(9, 6), nullable=True)
    tiempo_oficial = db.Column(db.String(20), nullable=True)  # ej. "01:23:45"
    posicion_general = db.Column(db.Integer, nullable=True)
    posicion_categoria = db.Column(db.Integer, nullable=True)

    evento = db.relationship("Evento")
    categoria = db.relationship("EventoCategoria")
    boleto = db.relationship("EventoBoleto")
    paquete = db.relationship("PaqueteRecuperacion")
    fecha = db.relationship("EventoFecha")

    def to_dict(self, detalle=False):
        data = {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "evento_id": self.evento_id,
            "categoria_id": self.categoria_id,
            "boleto_id": self.boleto_id,
            "paquete_id": self.paquete_id,
            "estado": self.estado,
            "numero_participante": self.numero_participante,
            "inscrita_en": self.inscrita_en.isoformat() if self.inscrita_en else None,
            "cancelada_en": self.cancelada_en.isoformat() if self.cancelada_en else None,
            "asistio_en": self.asistio_en.isoformat() if self.asistio_en else None,
            "tiempo_oficial": self.tiempo_oficial,
            "posicion_general": self.posicion_general,
            "posicion_categoria": self.posicion_categoria,
        }
        if detalle:
            data["evento"] = self.evento.to_dict() if self.evento else None
            data["categoria"] = self.categoria.to_dict() if self.categoria else None
            data["boleto"] = self.boleto.to_dict() if self.boleto else None
            data["paquete"] = self.paquete.to_dict() if self.paquete else None
        return data


class ValoracionEvento(db.Model):
    """Tabla `valoraciones_evento`: reseña que deja el usuario tras asistir.
    Se limita a una valoración por inscripción a nivel de aplicación
    (si ya existe una, se actualiza en vez de duplicarse).
    """

    __tablename__ = "valoraciones_evento"

    id = db.Column(db.Integer, primary_key=True)
    inscripciones_id = db.Column(db.Integer, db.ForeignKey("inscripciones.id"), nullable=False)
    calificacion_evento = db.Column(db.Integer, nullable=False)  # 1-5
    calificacion_organizador = db.Column(db.Integer, nullable=True)  # 1-5
    comentario = db.Column(db.Text, nullable=True)
    respuesta_organizador = db.Column(db.Text, nullable=True)
    respondida_en = db.Column(db.DateTime, nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    inscripcion = db.relationship("Inscripcion")

    def to_dict(self):
        return {
            "id": self.id,
            "inscripciones_id": self.inscripciones_id,
            "usuario_id": self.inscripcion.usuario_id if self.inscripcion else None,
            "evento_id": self.inscripcion.evento_id if self.inscripcion else None,
            "calificacion_evento": self.calificacion_evento,
            "calificacion_organizador": self.calificacion_organizador,
            "comentario": self.comentario,
            "respuesta_organizador": self.respuesta_organizador,
            "respondida_en": self.respondida_en.isoformat() if self.respondida_en else None,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }


class CalendarioUsuario(db.Model):
    """Tabla `calendario_usuario`: fechas de eventos que un usuario guardó
    en su calendario personal (le interesen o no estar inscrito todavía).
    """

    __tablename__ = "calendario_usuario"

    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), primary_key=True)
    fecha_id = db.Column(db.Integer, db.ForeignKey("evento_fechas.id"), primary_key=True)
    agregado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    fecha = db.relationship("EventoFecha")

    def to_dict(self):
        evento = self.fecha.evento if self.fecha else None
        return {
            "fecha_id": self.fecha_id,
            "inicia_en": self.fecha.inicia_en.isoformat() if self.fecha and self.fecha.inicia_en else None,
            "evento": evento.to_dict() if evento else None,
            "agregado_en": self.agregado_en.isoformat() if self.agregado_en else None,
        }
