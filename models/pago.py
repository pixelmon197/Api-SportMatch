from datetime import datetime, timezone

from database import db

# --- Catálogos --------------------------------------------------------
# Neon NO tiene CHECK en ninguna de estas columnas: los valores válidos los
# define la API (y por eso hay que validarlos aquí).

# Métodos que puede elegir el usuario. Con total $0 el sistema usa
# "gratuito" por su cuenta (no es elegible).
METODOS_PAGO = ("tarjeta", "transferencia", "efectivo")
METODO_GRATUITO = "gratuito"

PASARELA_SIMULADA = "simulada"  # "tarjeta" mientras no haya una pasarela real
PASARELA_MANUAL = "manual"      # transferencia/efectivo: un admin confirma el depósito
PASARELA_NINGUNA = "ninguna"    # pagos de $0

ESTADOS_PAGO = ("pendiente", "pagado", "fallido", "cancelado", "reembolsado")
ESTADOS_REEMBOLSO = ("solicitado", "aprobado", "rechazado")
ESTADOS_LIQUIDACION = ("pendiente", "pagada")
TIPOS_DESCUENTO = ("porcentaje", "monto_fijo")
CONCEPTOS = ("inscripcion",)  # a qué se aplica una comisión o un cupón


class Pago(db.Model):
    """Tabla `pagos`: un cobro (puede cubrir varias inscripciones)."""

    __tablename__ = "pagos"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    metodo = db.Column(db.String(20), nullable=False)
    pasarela = db.Column(db.String(20), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="pendiente")
    monto_total = db.Column(db.Numeric(10, 2), nullable=False)
    moneda = db.Column(db.String(3), nullable=False, default="MXN")
    referencia_externa = db.Column(db.String(100), nullable=True)
    pagado_en = db.Column(db.DateTime, nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    usuario = db.relationship("Usuario")
    items = db.relationship("PagoInscripcion", back_populates="pago")
    cupon_usos = db.relationship("CuponUso", back_populates="pago")

    def to_dict(self, detalle=False, interno=False):
        data = {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "metodo": self.metodo,
            "pasarela": self.pasarela,
            "estado": self.estado,
            "monto_total": float(self.monto_total),
            "moneda": self.moneda,
            "referencia_externa": self.referencia_externa,
            "pagado_en": self.pagado_en.isoformat() if self.pagado_en else None,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }
        if detalle:
            data["inscripciones"] = [i.to_dict(interno=interno) for i in self.items]
            data["cupon"] = self.cupon_usos[0].cupon.codigo if self.cupon_usos else None
        return data


class PagoInscripcion(db.Model):
    """Tabla `pagos_inscripciones`: cuánto de un pago corresponde a cada
    inscripción y cómo se reparte entre la plataforma y el organizador. Su
    PK real es `inscripcion_id` (no tiene `id` propio, la documentación del
    proyecto decía que sí): una inscripción tiene a lo sumo UN registro de
    pago."""

    __tablename__ = "pagos_inscripciones"

    inscripcion_id = db.Column(db.Integer, db.ForeignKey("inscripciones.id"), primary_key=True)
    pago_id = db.Column(db.Integer, db.ForeignKey("pagos.id"), nullable=False)
    liquidacion_id = db.Column(db.Integer, db.ForeignKey("liquidaciones.id"), nullable=True)
    monto_bruto = db.Column(db.Numeric(10, 2), nullable=False)
    comision_plataforma = db.Column(db.Numeric(10, 2), nullable=False)
    monto_organizador = db.Column(db.Numeric(10, 2), nullable=False)

    pago = db.relationship("Pago", back_populates="items")
    inscripcion = db.relationship("Inscripcion")
    liquidacion = db.relationship("Liquidacion", back_populates="items")

    def to_dict(self, interno=False):
        ins = self.inscripcion
        data = {
            "inscripcion_id": self.inscripcion_id,
            "evento_id": ins.evento_id if ins else None,
            "evento_titulo": ins.evento.titulo if ins and ins.evento else None,
            "monto": float(self.monto_bruto),
        }
        if interno:
            data["comision_plataforma"] = float(self.comision_plataforma)
            data["monto_organizador"] = float(self.monto_organizador)
            data["liquidacion_id"] = self.liquidacion_id
        return data


class Reembolso(db.Model):
    """Tabla `reembolsos`."""

    __tablename__ = "reembolsos"

    id = db.Column(db.Integer, primary_key=True)
    pago_id = db.Column(db.Integer, db.ForeignKey("pagos.id"), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="solicitado")
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    motivo = db.Column(db.Text, nullable=True)
    solicitado_por = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    aprobado_por = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    procesado_en = db.Column(db.DateTime, nullable=True)

    pago = db.relationship("Pago")

    def to_dict(self):
        return {
            "id": self.id,
            "pago_id": self.pago_id,
            "estado": self.estado,
            "monto": float(self.monto),
            "motivo": self.motivo,
            "solicitado_por": self.solicitado_por,
            "aprobado_por": self.aprobado_por,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "procesado_en": self.procesado_en.isoformat() if self.procesado_en else None,
        }


class Comision(db.Model):
    """Tabla `comisiones`: el porcentaje que se queda la plataforma, con
    vigencia por fechas."""

    __tablename__ = "comisiones"

    id = db.Column(db.Integer, primary_key=True)
    concepto = db.Column(db.String(30), nullable=False)
    porcentaje = db.Column(db.Numeric(5, 2), nullable=False)
    vigente_desde = db.Column(db.Date, nullable=False)
    vigente_hasta = db.Column(db.Date, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "concepto": self.concepto,
            "porcentaje": float(self.porcentaje),
            "vigente_desde": self.vigente_desde.isoformat() if self.vigente_desde else None,
            "vigente_hasta": self.vigente_hasta.isoformat() if self.vigente_hasta else None,
        }


class Liquidacion(db.Model):
    """Tabla `liquidaciones`: lo que la plataforma le paga a un organizador
    por un periodo (suma de los `pagos_inscripciones` incluidos)."""

    __tablename__ = "liquidaciones"

    id = db.Column(db.Integer, primary_key=True)
    organizador_id = db.Column(db.Integer, db.ForeignKey("organizadores.id"), nullable=False)
    cuenta_cobro_id = db.Column(db.Integer, db.ForeignKey("cuentas_cobro.id"), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="pendiente")
    periodo_desde = db.Column(db.Date, nullable=False)
    periodo_hasta = db.Column(db.Date, nullable=False)
    monto_bruto = db.Column(db.Numeric(10, 2), nullable=False)
    monto_comision = db.Column(db.Numeric(10, 2), nullable=False)
    monto_neto = db.Column(db.Numeric(10, 2), nullable=False)
    moneda = db.Column(db.String(3), nullable=False, default="MXN")
    referencia_pago = db.Column(db.String(100), nullable=True)
    pagada_en = db.Column(db.DateTime, nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    organizador = db.relationship("Organizador")
    cuenta_cobro = db.relationship("CuentaCobro")
    items = db.relationship("PagoInscripcion", back_populates="liquidacion")

    def to_dict(self, detalle=False):
        data = {
            "id": self.id,
            "organizador_id": self.organizador_id,
            "cuenta_cobro_id": self.cuenta_cobro_id,
            "estado": self.estado,
            "periodo_desde": self.periodo_desde.isoformat(),
            "periodo_hasta": self.periodo_hasta.isoformat(),
            "monto_bruto": float(self.monto_bruto),
            "monto_comision": float(self.monto_comision),
            "monto_neto": float(self.monto_neto),
            "moneda": self.moneda,
            "referencia_pago": self.referencia_pago,
            "pagada_en": self.pagada_en.isoformat() if self.pagada_en else None,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }
        if detalle:
            data["pagos"] = [i.to_dict(interno=True) for i in self.items]
        return data


class Cupon(db.Model):
    """Tabla `cupones`. `organizador_id` NULL = cupón de la plataforma
    (aplica a cualquier evento); con valor, solo a eventos de ese
    organizador. `concepto` NULL = aplica a todo."""

    __tablename__ = "cupones"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(30), nullable=False, unique=True)
    descripcion = db.Column(db.String(200), nullable=True)
    tipo_descuento = db.Column(db.String(20), nullable=False)
    concepto = db.Column(db.String(30), nullable=True)
    organizador_id = db.Column(db.Integer, db.ForeignKey("organizadores.id"), nullable=True)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    vigente_desde = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    vigente_hasta = db.Column(db.DateTime, nullable=True)
    usos_maximos = db.Column(db.Integer, nullable=True)
    usos_por_usuario = db.Column(db.Integer, nullable=False, default=1)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,
            "descripcion": self.descripcion,
            "tipo_descuento": self.tipo_descuento,
            "concepto": self.concepto,
            "organizador_id": self.organizador_id,
            "valor": float(self.valor),
            "vigente_desde": self.vigente_desde.isoformat() if self.vigente_desde else None,
            "vigente_hasta": self.vigente_hasta.isoformat() if self.vigente_hasta else None,
            "usos_maximos": self.usos_maximos,
            "usos_por_usuario": self.usos_por_usuario,
            "activo": self.activo,
        }


class CuponUso(db.Model):
    """Tabla `cupon_usos`: una fila por pago que usó el cupón (UNIQUE
    cupon+pago)."""

    __tablename__ = "cupon_usos"

    id = db.Column(db.Integer, primary_key=True)
    cupon_id = db.Column(db.Integer, db.ForeignKey("cupones.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    pago_id = db.Column(db.Integer, db.ForeignKey("pagos.id"), nullable=False)
    usado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    cupon = db.relationship("Cupon")
    pago = db.relationship("Pago", back_populates="cupon_usos")
