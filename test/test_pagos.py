import os, sys, sqlite3
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# Rutas relativas a este archivo: funciona sin importar desde dónde se
# ejecute ni en qué máquina, siempre que este script viva en test/ dentro
# del proyecto (Api-SportMatch/test/este_archivo.py).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, PROJECT_DIR)

DB_PATH = os.path.join(BASE_DIR, "test_pagos.sqlite3")
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "test"
os.environ["JWT_SECRET_KEY"] = "test"

DDL = """
CREATE TABLE ciudades (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'México', pais TEXT NOT NULL DEFAULT 'México', codigo_postal TEXT);
CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_completo TEXT NOT NULL, correo TEXT UNIQUE, contrasena TEXT,
    fecha_nacimiento DATE, sexo TEXT, rol TEXT NOT NULL DEFAULT 'usuario',
    estado_cuenta TEXT NOT NULL DEFAULT 'pendiente_verificacion',
    correo_verificado_en TIMESTAMP, ultimo_acceso TIMESTAMP,
    nombre_usuario TEXT UNIQUE, telefono TEXT, ciudad_id INTEGER,
    idioma TEXT DEFAULT 'es', zona_horaria TEXT DEFAULT 'America/Mexico_City',
    codigo_referido TEXT UNIQUE, registro_completo_en TIMESTAMP,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    eliminado_en TIMESTAMP
);
CREATE TABLE archivos (id INTEGER PRIMARY KEY AUTOINCREMENT, propietario_id INTEGER, tipo TEXT NOT NULL, url TEXT NOT NULL, nombre_original TEXT, tipo_mime TEXT, tamano_bytes BIGINT, ancho_px INTEGER, alto_px INTEGER, duracion_segundos INTEGER, subido_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, eliminado_en TIMESTAMP);
CREATE TABLE organizadores (
    id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER NOT NULL UNIQUE REFERENCES usuarios(id),
    nombre_comercial TEXT NOT NULL, descripcion TEXT, correo_contacto TEXT, telefono_contacto TEXT,
    ciudad_id INTEGER, logo_id INTEGER, estado_validacion TEXT NOT NULL DEFAULT 'sin_solicitud', validado_en TIMESTAMP,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, eliminado_en TIMESTAMP
);
CREATE TABLE organizador_miembros (
    organizador_id INTEGER NOT NULL, usuario_id INTEGER NOT NULL, rol TEXT NOT NULL DEFAULT 'colaborador',
    agregado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (organizador_id, usuario_id)
);
CREATE TABLE cuentas_cobro (
    id INTEGER PRIMARY KEY AUTOINCREMENT, organizador_id INTEGER NOT NULL, banco TEXT NOT NULL, titular TEXT NOT NULL,
    clabe TEXT NOT NULL, verificada BOOLEAN NOT NULL DEFAULT 0, es_principal BOOLEAN NOT NULL DEFAULT 0,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, eliminado_en TIMESTAMP
);
CREATE TABLE eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT, organizador_id INTEGER NOT NULL REFERENCES organizadores(id),
    tipo TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'borrador', dificultad TEXT, titulo TEXT NOT NULL, slug TEXT NOT NULL UNIQUE,
    descripcion TEXT, portada_id INTEGER, edad_minima INTEGER, es_publico BOOLEAN NOT NULL DEFAULT 1, publicado_en TIMESTAMP,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, eliminado_en TIMESTAMP
);
CREATE TABLE evento_categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT, evento_id INTEGER NOT NULL, nombre TEXT NOT NULL, distancia_km NUMERIC,
    edad_minima INTEGER, edad_maxima INTEGER, cupo_total INTEGER, permite_lista_espera BOOLEAN NOT NULL DEFAULT 0, UNIQUE (id, evento_id)
);
CREATE TABLE evento_boletos (
    id INTEGER PRIMARY KEY AUTOINCREMENT, categoria_id INTEGER NOT NULL, tipo TEXT NOT NULL, precio NUMERIC NOT NULL,
    moneda TEXT NOT NULL DEFAULT 'MXN', disponible_desde TIMESTAMP, disponible_hasta TIMESTAMP, cantidad_maxima INTEGER,
    activo BOOLEAN NOT NULL DEFAULT 1, UNIQUE (id, categoria_id)
);
CREATE TABLE evento_fechas (id INTEGER PRIMARY KEY AUTOINCREMENT, evento_id INTEGER NOT NULL, inicia_en TIMESTAMP NOT NULL, termina_en TIMESTAMP, cancelada_en TIMESTAMP, UNIQUE (id, evento_id));
CREATE TABLE paquetes_recuperacion (
    id INTEGER PRIMARY KEY AUTOINCREMENT, evento_id INTEGER NOT NULL, nivel TEXT NOT NULL, nombre TEXT NOT NULL, descripcion TEXT,
    precio NUMERIC NOT NULL, moneda TEXT NOT NULL DEFAULT 'MXN', activo BOOLEAN NOT NULL DEFAULT 1, UNIQUE (evento_id, nivel), UNIQUE (id, evento_id)
);
CREATE TABLE inscripciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER NOT NULL, evento_id INTEGER NOT NULL, fecha_id INTEGER NOT NULL,
    categoria_id INTEGER NOT NULL, boleto_id INTEGER, paquete_id INTEGER, estado TEXT NOT NULL DEFAULT 'pendiente_pago',
    numero_participante TEXT, inscrita_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, cancelada_en TIMESTAMP, asistio_en TIMESTAMP,
    asistencia_latitud NUMERIC, asistencia_longitud NUMERIC, tiempo_oficial TIME, posicion_general INTEGER, posicion_categoria INTEGER,
    CHECK (estado IN ('pendiente_pago','inscrito','activo','lista_espera','completado','cancelado','no_asistio'))
);
CREATE TABLE liquidaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT, organizador_id INTEGER NOT NULL, cuenta_cobro_id INTEGER NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente', periodo_desde DATE NOT NULL, periodo_hasta DATE NOT NULL,
    monto_bruto NUMERIC NOT NULL, monto_comision NUMERIC NOT NULL, monto_neto NUMERIC NOT NULL, moneda VARCHAR(3) NOT NULL DEFAULT 'MXN',
    referencia_pago VARCHAR(100), pagada_en TIMESTAMP, creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (periodo_hasta >= periodo_desde), CHECK (monto_neto = monto_bruto - monto_comision)
);
CREATE TABLE pagos (
    id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    metodo VARCHAR(20) NOT NULL, pasarela VARCHAR(20) NOT NULL, estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    monto_total NUMERIC NOT NULL, moneda VARCHAR(3) NOT NULL DEFAULT 'MXN', referencia_externa VARCHAR(100),
    pagado_en TIMESTAMP, creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, CHECK (monto_total >= 0)
);
CREATE TABLE pagos_inscripciones (
    inscripcion_id INTEGER PRIMARY KEY REFERENCES inscripciones(id), pago_id INTEGER NOT NULL REFERENCES pagos(id),
    liquidacion_id INTEGER REFERENCES liquidaciones(id),
    monto_bruto NUMERIC NOT NULL, comision_plataforma NUMERIC NOT NULL, monto_organizador NUMERIC NOT NULL,
    CHECK (monto_bruto >= 0), CHECK (comision_plataforma >= 0), CHECK (monto_organizador >= 0),
    CHECK (monto_organizador = monto_bruto - comision_plataforma)
);
CREATE TABLE reembolsos (
    id INTEGER PRIMARY KEY AUTOINCREMENT, pago_id INTEGER NOT NULL REFERENCES pagos(id), estado VARCHAR(20) NOT NULL DEFAULT 'solicitado',
    monto NUMERIC NOT NULL, motivo TEXT, solicitado_por INTEGER REFERENCES usuarios(id), aprobado_por INTEGER REFERENCES usuarios(id),
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, procesado_en TIMESTAMP, CHECK (monto > 0)
);
CREATE TABLE comisiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT, concepto VARCHAR(30) NOT NULL, porcentaje NUMERIC NOT NULL,
    vigente_desde DATE NOT NULL, vigente_hasta DATE, CHECK (porcentaje >= 0 AND porcentaje <= 100)
);
CREATE TABLE cupones (
    id INTEGER PRIMARY KEY AUTOINCREMENT, codigo VARCHAR(30) NOT NULL UNIQUE, descripcion VARCHAR(200),
    tipo_descuento VARCHAR(20) NOT NULL, concepto VARCHAR(30), organizador_id INTEGER REFERENCES organizadores(id),
    valor NUMERIC NOT NULL, vigente_desde TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, vigente_hasta TIMESTAMP,
    usos_maximos INTEGER, usos_por_usuario INTEGER NOT NULL DEFAULT 1, activo BOOLEAN NOT NULL DEFAULT 1, CHECK (valor > 0)
);
CREATE TABLE cupon_usos (
    id INTEGER PRIMARY KEY AUTOINCREMENT, cupon_id INTEGER NOT NULL REFERENCES cupones(id), usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    pago_id INTEGER NOT NULL REFERENCES pagos(id), usado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE (cupon_id, pago_id)
);
"""

def sql(consulta, *params):
    c = sqlite3.connect(DB_PATH)
    try:
        filas = c.execute(consulta, params).fetchall(); c.commit(); return filas
    finally:
        c.close()

conn = sqlite3.connect(DB_PATH)
conn.executescript(DDL)
def usuario(nombre, correo, nick, rol="usuario"):
    conn.execute("INSERT INTO usuarios (nombre_completo, correo, contrasena, fecha_nacimiento, sexo, nombre_usuario, rol, estado_cuenta, registro_completo_en) VALUES (?,?,'x','2000-01-01','femenino',?,?,'activa',CURRENT_TIMESTAMP)", (nombre, correo, nick, rol))
usuario("Ana Perez", "ana@c.com", "ana")                    # 1 compradora
usuario("Luis Gomez", "luis@c.com", "luis")                 # 2 comprador (transferencia + reembolso)
usuario("Marta Diaz", "marta@c.com", "marta")               # 3 dueña del organizador 1
usuario("Admin Uno", "admin@c.com", "admin1", "administrador")  # 4
usuario("Carlos Ruiz", "carlos@c.com", "carlos")            # 5 paga 2 inscripciones juntas
usuario("Pablo Sol", "pablo@c.com", "pablo")                # 6 dueño del organizador 2
usuario("Diana Lopez", "diana@c.com", "diana")              # 7 lista de espera
conn.execute("INSERT INTO organizadores (usuario_id, nombre_comercial, estado_validacion) VALUES (3,'Carreras Marta','aprobada')")
conn.execute("INSERT INTO organizadores (usuario_id, nombre_comercial, estado_validacion) VALUES (6,'Eventos Pablo','aprobada')")
conn.execute("INSERT INTO organizador_miembros (organizador_id, usuario_id, rol) VALUES (1,3,'propietario')")
conn.execute("INSERT INTO organizador_miembros (organizador_id, usuario_id, rol) VALUES (2,6,'propietario')")
conn.execute("INSERT INTO cuentas_cobro (organizador_id, banco, titular, clabe, verificada) VALUES (1,'BBVA','Marta Diaz','012345678901234567',1)")   # 1 verificada
conn.execute("INSERT INTO cuentas_cobro (organizador_id, banco, titular, clabe, verificada) VALUES (1,'Banorte','Marta Diaz','072345678901234567',0)")  # 2 sin verificar
conn.execute("INSERT INTO cuentas_cobro (organizador_id, banco, titular, clabe, verificada) VALUES (2,'HSBC','Pablo Sol','021345678901234567',1)")      # 3 de otro organizador
# Evento 1 (org 1): cat 1 con cupo 3 y lista de espera; boleto $200; paquete $100
conn.execute("INSERT INTO eventos (organizador_id, tipo, estado, titulo, slug, publicado_en) VALUES (1,'carrera','publicado','5K Nocturna','5k',CURRENT_TIMESTAMP)")
conn.execute("INSERT INTO evento_categorias (evento_id, nombre, cupo_total, permite_lista_espera) VALUES (1,'5K',3,1)")
conn.execute("INSERT INTO evento_boletos (categoria_id, tipo, precio) VALUES (1,'general',200)")                  # boleto 1
conn.execute("INSERT INTO evento_fechas (evento_id, inicia_en) VALUES (1,'2026-12-01T19:00:00')")                # fecha 1
conn.execute("INSERT INTO paquetes_recuperacion (evento_id, nivel, nombre, precio) VALUES (1,'basico','Kit',100)")  # paquete 1
# Evento 2 (org 2): boleto $300
conn.execute("INSERT INTO eventos (organizador_id, tipo, estado, titulo, slug, publicado_en) VALUES (2,'carrera','publicado','10K Sol','10k',CURRENT_TIMESTAMP)")
conn.execute("INSERT INTO evento_categorias (evento_id, nombre) VALUES (2,'10K')")
conn.execute("INSERT INTO evento_boletos (categoria_id, tipo, precio) VALUES (2,'general',300)")                  # boleto 2
conn.execute("INSERT INTO evento_fechas (evento_id, inicia_en) VALUES (2,'2026-12-05T08:00:00')")                # fecha 2
# Evento 3 (org 1): gratis
conn.execute("INSERT INTO eventos (organizador_id, tipo, estado, titulo, slug, publicado_en) VALUES (1,'ruta','publicado','Rodada gratis','rodada',CURRENT_TIMESTAMP)")
conn.execute("INSERT INTO evento_categorias (evento_id, nombre) VALUES (3,'Libre')")
conn.execute("INSERT INTO evento_boletos (categoria_id, tipo, precio) VALUES (3,'general',0)")                    # boleto 3
conn.execute("INSERT INTO evento_fechas (evento_id, inicia_en) VALUES (3,'2026-12-10T08:00:00')")                # fecha 3
conn.commit(); conn.close()

from app import create_app
from flask_jwt_extended import create_access_token

app = create_app()
app.config["SIMULAR_PASARELA"] = True
client = app.test_client()
with app.app_context():
    tok = lambda i, rol="usuario": {"Authorization": "Bearer " + create_access_token(identity=str(i), additional_claims={"rol": rol})}
    ANA, LUIS, MARTA, ADMIN, CARLOS, PABLO, DIANA = tok(1), tok(2), tok(3), tok(4, "administrador"), tok(5), tok(6), tok(7)

def show(label, resp):
    print(f"--- {label} [{resp.status_code}] ---")
    print(resp.get_json())

def inscribir(headers, evento, fecha, categoria, boleto, paquete=None):
    body = {"evento_id": evento, "fecha_id": fecha, "categoria_id": categoria, "boleto_id": boleto}
    if paquete: body["paquete_id"] = paquete
    r = client.post("/api/inscripciones", json=body, headers=headers)
    assert r.status_code == 201, r.get_json()
    return r.get_json()

dec = lambda x: Decimal(str(x))
hoy = datetime.now(timezone.utc).date()

# ======================= COMISIONES =======================
r = client.get("/api/comisiones/vigente", headers=ANA)
show("COMISION VIGENTE (sin ninguna registrada)", r)
assert r.get_json() == {"concepto": "inscripcion", "porcentaje": 10.0, "por_defecto": True}
assert client.post("/api/comisiones", json={"concepto": "inscripcion", "porcentaje": 12.5}, headers=ANA).status_code == 403
for body in ({"concepto": "tienda", "porcentaje": 5}, {"concepto": "inscripcion", "porcentaje": 101},
             {"concepto": "inscripcion", "porcentaje": -1}, {"concepto": "inscripcion", "porcentaje": "10"},
             {"concepto": "inscripcion", "porcentaje": 5, "vigente_desde": "ayer"}):
    assert client.post("/api/comisiones", json=body, headers=ADMIN).status_code == 400, body
r = client.post("/api/comisiones", json={"concepto": "inscripcion", "porcentaje": 12.5, "vigente_desde": "2026-01-01"}, headers=ADMIN)
show("CREAR COMISION", r); assert r.status_code == 201
assert client.get("/api/comisiones/vigente", headers=ANA).get_json() == {"concepto": "inscripcion", "porcentaje": 12.5, "por_defecto": False}
assert client.post("/api/comisiones", json={"concepto": "inscripcion", "porcentaje": 9, "vigente_desde": "2025-06-01"}, headers=ADMIN).status_code == 409
r = client.post("/api/comisiones", json={"concepto": "inscripcion", "porcentaje": 20, "vigente_desde": "2099-01-01"}, headers=ADMIN)
assert r.status_code == 201
hist = client.get("/api/comisiones", headers=ADMIN).get_json()
assert [c["vigente_hasta"] for c in hist] == [None, "2098-12-31"], hist          # la anterior se cerro el dia antes
assert client.get("/api/comisiones/vigente", headers=ANA).get_json()["porcentaje"] == 12.5   # la de 2099 aun no rige
assert client.get("/api/comisiones", headers=ANA).status_code == 403
print("--- comisiones OK ---")

# ======================= CUPONES =======================
r = client.post("/api/cupones", json={"codigo": "marta20", "tipo_descuento": "porcentaje", "valor": 20, "organizador_id": 1}, headers=MARTA)
show("CUPON (organizador propio)", r)
assert r.status_code == 201 and r.get_json()["codigo"] == "MARTA20" and r.get_json()["usos"] == 0
r = client.post("/api/cupones", json={"codigo": "GLOBAL50", "tipo_descuento": "monto_fijo", "valor": 50}, headers=ADMIN)
assert r.status_code == 201 and r.get_json()["organizador_id"] is None
r = client.post("/api/cupones", json={"codigo": "PABLO10", "tipo_descuento": "porcentaje", "valor": 10, "organizador_id": 2}, headers=PABLO)
assert r.status_code == 201
r = client.post("/api/cupones", json={"codigo": "SOLOUNA", "tipo_descuento": "porcentaje", "valor": 50, "organizador_id": 1, "usos_maximos": 1}, headers=MARTA)
assert r.status_code == 201
for body, codigo, headers in (
    ({"codigo": "x", "tipo_descuento": "porcentaje", "valor": 5}, 400, ADMIN),                    # codigo corto
    ({"codigo": "MALO!", "tipo_descuento": "porcentaje", "valor": 5}, 400, ADMIN),                # simbolo
    ({"codigo": "OK1", "tipo_descuento": "descuento", "valor": 5}, 400, ADMIN),                   # tipo
    ({"codigo": "OK1", "tipo_descuento": "porcentaje", "valor": 0}, 400, ADMIN),                  # valor 0
    ({"codigo": "OK1", "tipo_descuento": "porcentaje", "valor": 150}, 400, ADMIN),                # >100%
    ({"codigo": "OK1", "tipo_descuento": "porcentaje", "valor": "5"}, 400, ADMIN),                # texto
    ({"codigo": "OK1", "tipo_descuento": "porcentaje", "valor": 5, "usos_maximos": 0}, 400, ADMIN),
    ({"codigo": "OK1", "tipo_descuento": "porcentaje", "valor": 5, "concepto": "tienda"}, 400, ADMIN),
    ({"codigo": "OK1", "tipo_descuento": "porcentaje", "valor": 5, "vigente_desde": "2026-12-02T00:00:00", "vigente_hasta": "2026-12-01T00:00:00"}, 400, ADMIN),
    ({"codigo": "OK1", "tipo_descuento": "porcentaje", "valor": 5}, 400, MARTA),                   # organizador sin organizador_id
    ({"codigo": "OK1", "tipo_descuento": "porcentaje", "valor": 5, "organizador_id": 2}, 403, MARTA),  # organizador ajeno
    ({"codigo": "OK1", "tipo_descuento": "porcentaje", "valor": 5, "organizador_id": 99}, 400, ADMIN),
    ({"codigo": "MARTA20", "tipo_descuento": "porcentaje", "valor": 5, "organizador_id": 1}, 409, MARTA),  # repetido
):
    assert client.post("/api/cupones", json=body, headers=headers).status_code == codigo, body
assert client.get("/api/cupones", headers=MARTA).status_code == 400                    # debe indicar organizador_id
assert client.get("/api/cupones?organizador_id=2", headers=MARTA).status_code == 403
r = client.get("/api/cupones?organizador_id=1", headers=MARTA)
assert sorted(c["codigo"] for c in r.get_json()["cupones"]) == ["MARTA20", "SOLOUNA"]
assert r.get_json()["total"] == 2
assert client.get("/api/cupones", headers=ADMIN).get_json()["total"] == 4
assert client.get("/api/cupones", headers=ANA).status_code == 400
print("--- cupones (alta y permisos) OK ---")

# ======================= COTIZAR =======================
ins_ana = inscribir(ANA, 1, 1, 1, 1, paquete=1)            # evento 1: $200 + paquete $100 = $300
ins_luis = inscribir(LUIS, 1, 1, 1, 1)                     # $200
ins_carlos_1 = inscribir(CARLOS, 1, 1, 1, 1)               # $200  (cupo 3 de 3 -> ya esta lleno)
ins_diana = inscribir(DIANA, 1, 1, 1, 1)
assert ins_diana["estado"] == "lista_espera"
ins_carlos_2 = inscribir(CARLOS, 2, 2, 2, 2)               # evento 2: $300
ins_ana_gratis = inscribir(ANA, 3, 3, 3, 3)                # evento gratis

r = client.post("/api/pagos/cotizar", json={"inscripcion_ids": [ins_ana["id"]]}, headers=ANA)
show("COTIZAR", r)
c = r.get_json()
assert c["total"] == 300 and c["subtotal"] == 300 and c["descuento_total"] == 0 and c["cupon"] is None
assert c["items"][0]["precio_boleto"] == 200 and c["items"][0]["precio_paquete"] == 100
assert "comision_plataforma" not in str(c) and "monto_organizador" not in str(c), "quien paga no ve la comision"
assert sql("SELECT COUNT(*) FROM pagos")[0][0] == 0, "cotizar no debe escribir"

for body, codigo, nombre in (
    ({}, 400, "sin ids"), ({"inscripcion_ids": []}, 400, "lista vacia"), ({"inscripcion_ids": "1"}, 400, "no es lista"),
    ({"inscripcion_ids": ["1"]}, 400, "id texto"), ({"inscripcion_ids": [True]}, 400, "id booleano"),
    ({"inscripcion_ids": [ins_ana["id"], ins_ana["id"]]}, 400, "repetidos"),
    ({"inscripcion_ids": [9999]}, 404, "no existe"),
    ({"inscripcion_ids": [ins_luis["id"]]}, 404, "es de otra persona"),
    ({"inscripcion_ids": [ins_diana["id"]]}, 404, "es de otra persona (Diana, vista por Ana)"),
):
    assert client.post("/api/pagos/cotizar", json=body, headers=ANA).status_code == codigo, nombre
r = client.post("/api/pagos/cotizar", json={"inscripcion_ids": [ins_diana["id"]]}, headers=DIANA)
assert r.status_code == 409 and "lista de espera" in r.get_json()["error"]
assert client.post("/api/pagos/cotizar", json={"inscripcion_ids": [1]}).status_code == 401

# Cupones al cotizar
r = client.post("/api/pagos/cotizar", json={"inscripcion_ids": [ins_ana["id"]], "cupon_codigo": "marta20"}, headers=ANA)
show("COTIZAR con MARTA20 (20% sobre $300)", r)
assert r.get_json()["descuento_total"] == 60 and r.get_json()["total"] == 240 and r.get_json()["cupon"]["codigo"] == "MARTA20"
assert client.post("/api/pagos/cotizar", json={"inscripcion_ids": [ins_ana["id"]], "cupon_codigo": "NOEXISTE"}, headers=ANA).status_code == 404
r = client.post("/api/pagos/cotizar", json={"inscripcion_ids": [ins_ana["id"]], "cupon_codigo": "PABLO10"}, headers=ANA)
show("COTIZAR con cupon de otro organizador", r); assert r.status_code == 409 and "no aplica" in r.get_json()["error"]
r = client.post("/api/pagos/cotizar", json={"inscripcion_ids": [ins_ana["id"]], "cupon_codigo": "GLOBAL50"}, headers=ANA)
assert r.get_json()["total"] == 250                       # cupon de la plataforma vale en cualquier evento
def cupon_id(codigo):
    lista = client.get("/api/cupones?organizador_id=1", headers=MARTA).get_json()["cupones"]
    return [c for c in lista if c["codigo"] == codigo][0]["id"]
assert client.put(f"/api/cupones/{cupon_id('SOLOUNA')}", json={"activo": False}, headers=MARTA).status_code == 200
print("--- cotizar OK ---")

# ======================= PAGO CON TARJETA (simulada) =======================
r = client.post("/api/pagos", json={"inscripcion_ids": [ins_ana["id"]], "metodo": "tarjeta", "cupon_codigo": "MARTA20"}, headers=ANA)
show("CREAR PAGO (tarjeta)", r)
assert r.status_code == 201, r.get_json()
p = r.get_json(); pago_ana = p["id"]
assert (p["estado"], p["pasarela"], p["monto_total"], p["moneda"], p["cupon"]) == ("pendiente", "simulada", 240.0, "MXN", "MARTA20")
assert "comision_plataforma" not in str(p["inscripciones"]), "el comprador no ve la comision"
assert "simular-pago" in p["instrucciones"]
assert sql("SELECT estado FROM inscripciones WHERE id=?", ins_ana["id"])[0][0] == "pendiente_pago"

r = client.post("/api/pagos", json={"inscripcion_ids": [ins_ana["id"]], "metodo": "tarjeta"}, headers=ANA)
show("CREAR PAGO otra vez para la misma inscripcion", r); assert r.status_code == 409 and r.get_json()["pago_id"] == pago_ana
r = client.put(f"/api/inscripciones/{ins_ana['id']}/cancelar", headers=ANA)
show("CANCELAR INSCRIPCION con pago pendiente", r); assert r.status_code == 409 and r.get_json()["pago_id"] == pago_ana
assert client.get(f"/api/pagos/{pago_ana}", headers=LUIS).status_code == 404       # ajeno: no se revela
assert client.get(f"/api/pagos/{pago_ana}").status_code == 401
assert client.post(f"/api/pagos/{pago_ana}/simular-pago", headers=LUIS).status_code == 404
assert client.post(f"/api/pagos/{pago_ana}/simular-pago", json={"resultado": "quiza"}, headers=ANA).status_code == 400
assert client.post("/api/pagos", json={"inscripcion_ids": [ins_luis["id"]], "metodo": "bitcoin"}, headers=LUIS).status_code == 400
assert client.post("/api/pagos", json={"inscripcion_ids": [ins_luis["id"]], "metodo": "gratuito"}, headers=LUIS).status_code == 400
assert client.post("/api/pagos", json={"inscripcion_ids": [ins_luis["id"]]}, headers=LUIS).status_code == 400

# El cupon queda apartado mientras el pago esta pendiente
cupon_marta = client.get("/api/cupones?organizador_id=1", headers=MARTA).get_json()["cupones"]
assert [c for c in cupon_marta if c["codigo"] == "MARTA20"][0]["usos"] == 1

# La pasarela rechaza: el pago falla, el cupon se libera y se puede reintentar
r = client.post(f"/api/pagos/{pago_ana}/simular-pago", json={"resultado": "rechazado"}, headers=ANA)
show("SIMULAR (rechazado)", r); assert r.status_code == 200 and r.get_json()["estado"] == "fallido"
assert sql("SELECT estado FROM inscripciones WHERE id=?", ins_ana["id"])[0][0] == "pendiente_pago"
assert [c for c in client.get("/api/cupones?organizador_id=1", headers=MARTA).get_json()["cupones"] if c["codigo"] == "MARTA20"][0]["usos"] == 0
assert client.post(f"/api/pagos/{pago_ana}/simular-pago", headers=ANA).status_code == 409     # ya no esta pendiente
r = client.post("/api/pagos", json={"inscripcion_ids": [ins_ana["id"]], "metodo": "tarjeta", "cupon_codigo": "MARTA20"}, headers=ANA)
show("REINTENTAR PAGO", r); assert r.status_code == 201
pago_ana = r.get_json()["id"]
assert sql("SELECT COUNT(*) FROM pagos_inscripciones WHERE inscripcion_id=?", ins_ana["id"])[0][0] == 1   # sin filas duplicadas

# Cancelar y volver a crear
r = client.put(f"/api/pagos/{pago_ana}/cancelar", headers=ANA); assert r.status_code == 200 and r.get_json()["estado"] == "cancelado"
assert client.put(f"/api/pagos/{pago_ana}/cancelar", headers=ANA).status_code == 409
r = client.post("/api/pagos", json={"inscripcion_ids": [ins_ana["id"]], "metodo": "tarjeta", "cupon_codigo": "MARTA20"}, headers=ANA)
assert r.status_code == 201; pago_ana = r.get_json()["id"]

# Aprobado
r = client.post(f"/api/pagos/{pago_ana}/simular-pago", headers=ANA)
show("SIMULAR (aprobado)", r)
assert r.status_code == 200 and r.get_json()["estado"] == "pagado" and r.get_json()["pagado_en"]
assert r.get_json()["referencia_externa"].startswith("SIM-")
assert sql("SELECT estado FROM inscripciones WHERE id=?", ins_ana["id"])[0][0] == "inscrito"

# Reparto de comision: 12.5 % de $240 = $30; el organizador recibe $210
fila = sql("SELECT monto_bruto, comision_plataforma, monto_organizador FROM pagos_inscripciones WHERE inscripcion_id=?", ins_ana["id"])[0]
assert tuple(round(x, 2) for x in fila) == (240.0, 30.0, 210.0), fila
r = client.get(f"/api/pagos/{pago_ana}", headers=ADMIN)
assert r.get_json()["inscripciones"][0]["comision_plataforma"] == 30.0 and r.get_json()["inscripciones"][0]["monto_organizador"] == 210.0
assert "comision_plataforma" not in str(client.get(f"/api/pagos/{pago_ana}", headers=ANA).get_json())

# MARTA20 no tiene limite global, pero cada persona solo la puede usar 1 vez
r = client.post("/api/pagos/cotizar", json={"inscripcion_ids": [ins_ana_gratis["id"]], "cupon_codigo": "MARTA20"}, headers=ANA)
assert r.status_code == 409 and "máximo de veces" in r.get_json()["error"]
print("--- pago con tarjeta OK ---")

# ======================= TRANSFERENCIA (confirma un admin) =======================
r = client.post("/api/pagos", json={"inscripcion_ids": [ins_luis["id"]], "metodo": "transferencia"}, headers=LUIS)
show("CREAR PAGO (transferencia)", r)
pt = r.get_json(); pago_luis = pt["id"]
assert pt["pasarela"] == "manual" and pt["monto_total"] == 200.0 and pt["referencia_externa"] == f"SM-{pago_luis:08d}"
assert pt["referencia_externa"] in pt["instrucciones"]
assert client.post(f"/api/pagos/{pago_luis}/simular-pago", headers=LUIS).status_code == 409   # no es de la pasarela simulada
assert client.put(f"/api/pagos/{pago_luis}/confirmar", headers=LUIS).status_code == 403       # solo admin
r = client.put(f"/api/pagos/{pago_luis}/confirmar", json={"referencia_externa": "SPEI-998877"}, headers=ADMIN)
show("CONFIRMAR (admin)", r)
assert r.status_code == 200 and r.get_json()["estado"] == "pagado" and r.get_json()["referencia_externa"] == "SPEI-998877"
assert sql("SELECT estado FROM inscripciones WHERE id=?", ins_luis["id"])[0][0] == "inscrito"
assert client.put(f"/api/pagos/{pago_luis}/confirmar", headers=ADMIN).status_code == 409
assert client.put(f"/api/pagos/{pago_luis}/cancelar", headers=LUIS).status_code == 409        # ya pagado
assert client.put("/api/pagos/9999/confirmar", headers=ADMIN).status_code == 404
# sin cupon: 12.5 % de $200 = $25
fila = sql("SELECT monto_bruto, comision_plataforma, monto_organizador FROM pagos_inscripciones WHERE inscripcion_id=?", ins_luis["id"])[0]
assert tuple(round(x, 2) for x in fila) == (200.0, 25.0, 175.0), fila

# Una inscripcion cambio de estado entre crear y confirmar el pago -> no se confirma
r = client.post("/api/pagos", json={"inscripcion_ids": [ins_carlos_2["id"]], "metodo": "efectivo"}, headers=CARLOS)
pago_efectivo = r.get_json()["id"]
sql("UPDATE inscripciones SET estado='cancelado' WHERE id=?", ins_carlos_2["id"])
r = client.put(f"/api/pagos/{pago_efectivo}/confirmar", headers=ADMIN)
show("CONFIRMAR con inscripcion ya cancelada", r); assert r.status_code == 409 and "ya no está pendiente" in r.get_json()["error"]
assert sql("SELECT estado FROM pagos WHERE id=?", pago_efectivo)[0][0] == "pendiente"
client.put(f"/api/pagos/{pago_efectivo}/cancelar", headers=ADMIN)
sql("UPDATE inscripciones SET estado='pendiente_pago' WHERE id=?", ins_carlos_2["id"])
print("--- transferencia OK ---")

# ======================= EVENTO GRATIS =======================
r = client.post("/api/pagos", json={"inscripcion_ids": [ins_ana_gratis["id"]]}, headers=ANA)
show("PAGO GRATIS (sin metodo)", r)
g = r.get_json()
assert r.status_code == 201 and (g["estado"], g["metodo"], g["pasarela"], g["monto_total"]) == ("pagado", "gratuito", "ninguna", 0.0)
assert sql("SELECT estado FROM inscripciones WHERE id=?", ins_ana_gratis["id"])[0][0] == "inscrito"
r = client.post(f"/api/pagos/{g['id']}/reembolsos", json={"motivo": "x"}, headers=ANA)
assert r.status_code == 409 and "gratuito" in r.get_json()["error"]
print("--- evento gratis OK ---")

# ======================= VARIAS INSCRIPCIONES + CUPON GLOBAL (reparto) =======================
r = client.post("/api/pagos/cotizar", json={"inscripcion_ids": [ins_carlos_1["id"], ins_carlos_2["id"]], "cupon_codigo": "GLOBAL50"}, headers=CARLOS)
show("COTIZAR 2 inscripciones con GLOBAL50 ($50 fijos sobre $500)", r)
c = r.get_json()
assert (c["subtotal"], c["descuento_total"], c["total"]) == (500, 50, 450)
assert [i["descuento"] for i in c["items"]] == [20.0, 30.0] and [i["monto"] for i in c["items"]] == [180.0, 270.0]
# El cupon de Marta solo aplica a SU evento: descuenta solo en la inscripcion del evento 1
r = client.post("/api/pagos/cotizar", json={"inscripcion_ids": [ins_carlos_1["id"], ins_carlos_2["id"]], "cupon_codigo": "SOLOUNA"}, headers=CARLOS)
assert r.status_code == 409 and "no está activo" in r.get_json()["error"], "SOLOUNA se desactivo arriba"
r = client.put(f"/api/cupones/{[x for x in client.get('/api/cupones?organizador_id=1', headers=MARTA).get_json()['cupones'] if x['codigo']=='SOLOUNA'][0]['id']}", json={"activo": True}, headers=MARTA)
assert r.status_code == 200
r = client.post("/api/pagos/cotizar", json={"inscripcion_ids": [ins_carlos_1["id"], ins_carlos_2["id"]], "cupon_codigo": "SOLOUNA"}, headers=CARLOS)
c = r.get_json()
assert [i["descuento"] for i in c["items"]] == [100.0, 0.0] and c["total"] == 400, c      # 50 % de $200, y nada del evento 2

r = client.post("/api/pagos", json={"inscripcion_ids": [ins_carlos_1["id"], ins_carlos_2["id"]], "metodo": "tarjeta", "cupon_codigo": "GLOBAL50"}, headers=CARLOS)
show("CREAR PAGO de 2 inscripciones", r)
assert r.status_code == 201 and r.get_json()["monto_total"] == 450.0
pago_carlos = r.get_json()["id"]
assert client.post(f"/api/pagos/{pago_carlos}/simular-pago", headers=CARLOS).get_json()["estado"] == "pagado"
filas = sql("SELECT inscripcion_id, monto_bruto, comision_plataforma, monto_organizador FROM pagos_inscripciones WHERE pago_id=? ORDER BY inscripcion_id", pago_carlos)
assert [(round(a, 2), round(b, 2), round(c_, 2)) for _, a, b, c_ in filas] == [(180.0, 22.5, 157.5), (270.0, 33.75, 236.25)], filas
assert sum(f[1] for f in filas) == 450 and abs(sum(f[2] for f in filas) - 56.25) < 1e-9
assert client.get(f"/api/pagos/{pago_carlos}", headers=CARLOS).get_json()["cupon"] == "GLOBAL50"
print("--- varias inscripciones y reparto OK ---")

# ======================= LISTAS =======================
r = client.get("/api/pagos/me", headers=ANA)
assert r.get_json()["total"] == 4 and r.get_json()["pagos"][0]["id"] > r.get_json()["pagos"][-1]["id"]   # mas reciente primero
r = client.get("/api/pagos/me?estado=pagado&per_page=1", headers=ANA)
assert r.get_json()["total"] == 2 and len(r.get_json()["pagos"]) == 1 and r.get_json()["paginas"] == 2
assert client.get("/api/pagos/me?estado=cancelado", headers=ANA).get_json()["total"] == 1
assert client.get("/api/pagos", headers=ANA).status_code == 403
r = client.get("/api/pagos?metodo=transferencia", headers=ADMIN)
assert r.get_json()["total"] == 1 and "comision_plataforma" in str(r.get_json())
assert client.get("/api/pagos?usuario_id=5", headers=ADMIN).get_json()["total"] == 2   # efectivo cancelado + tarjeta pagada
print("--- listas OK ---")

# ======================= REEMBOLSO (+ lista de espera) =======================
assert sql("SELECT estado FROM inscripciones WHERE id=?", ins_diana["id"])[0][0] == "lista_espera"
assert client.post(f"/api/pagos/{pago_luis}/reembolsos", json={}, headers=LUIS).status_code == 400            # motivo obligatorio
assert client.post(f"/api/pagos/{pago_luis}/reembolsos", json={"motivo": "x" * 501}, headers=LUIS).status_code == 400
assert client.post(f"/api/pagos/{pago_luis}/reembolsos", json={"motivo": "No puedo ir"}, headers=ANA).status_code == 404   # pago ajeno
assert client.post(f"/api/pagos/{pago_efectivo}/reembolsos", json={"motivo": "x"}, headers=CARLOS).status_code == 409      # no esta pagado
r = client.post(f"/api/pagos/{pago_luis}/reembolsos", json={"motivo": "No puedo ir"}, headers=LUIS)
show("SOLICITAR REEMBOLSO", r)
assert r.status_code == 201 and r.get_json()["estado"] == "solicitado" and r.get_json()["monto"] == 200.0
reemb = r.get_json()["id"]
assert client.post(f"/api/pagos/{pago_luis}/reembolsos", json={"motivo": "otra vez"}, headers=LUIS).status_code == 409
assert client.get("/api/reembolsos/me", headers=LUIS).get_json()["total"] == 1
assert client.get("/api/reembolsos/me", headers=ANA).get_json()["total"] == 0
assert client.get("/api/reembolsos", headers=LUIS).status_code == 403
assert [x["id"] for x in client.get("/api/reembolsos", headers=ADMIN).get_json()["reembolsos"]] == [reemb]
assert client.get("/api/reembolsos?estado=raro", headers=ADMIN).status_code == 400
assert client.put(f"/api/reembolsos/{reemb}/aprobar", headers=LUIS).status_code == 403

r = client.put(f"/api/reembolsos/{reemb}/rechazar", headers=ADMIN)
show("RECHAZAR REEMBOLSO", r); assert r.status_code == 200 and r.get_json()["estado"] == "rechazado" and r.get_json()["aprobado_por"] == 4
assert sql("SELECT estado FROM pagos WHERE id=?", pago_luis)[0][0] == "pagado"          # sigue pagado
assert client.put(f"/api/reembolsos/{reemb}/aprobar", headers=ADMIN).status_code == 409   # ya resuelto
r = client.post(f"/api/pagos/{pago_luis}/reembolsos", json={"motivo": "Insisto"}, headers=LUIS)
assert r.status_code == 201; reemb = r.get_json()["id"]

r = client.put(f"/api/reembolsos/{reemb}/aprobar", headers=ADMIN)
show("APROBAR REEMBOLSO", r); assert r.status_code == 200 and r.get_json()["estado"] == "aprobado" and r.get_json()["procesado_en"]
assert sql("SELECT estado FROM pagos WHERE id=?", pago_luis)[0][0] == "reembolsado"
assert sql("SELECT estado FROM inscripciones WHERE id=?", ins_luis["id"])[0][0] == "cancelado"
assert sql("SELECT estado FROM inscripciones WHERE id=?", ins_diana["id"])[0][0] == "pendiente_pago", "Diana debe subir de la lista de espera"
assert client.post(f"/api/pagos/{pago_luis}/reembolsos", json={"motivo": "x"}, headers=LUIS).status_code == 409
print("--- reembolsos OK ---")

# ======================= INGRESOS DEL ORGANIZADOR =======================
assert client.get("/api/organizadores/1/pagos", headers=ANA).status_code == 403
assert client.get("/api/organizadores/1/pagos", headers=PABLO).status_code == 403
assert client.get("/api/organizadores/99/pagos", headers=MARTA).status_code == 404
r = client.get("/api/organizadores/1/pagos", headers=MARTA)
show("INGRESOS org 1", r)
b = r.get_json()
# Pagados del evento 1: Ana ($240) y Carlos ($180); Luis esta reembolsado y no cuenta; el evento gratis ($0) si aparece
assert sorted(x["inscripcion_id"] for x in b["pagos"] if x["monto"] > 0) == sorted([ins_ana["id"], ins_carlos_1["id"]])
assert b["resumen"] == {"monto_bruto": 420.0, "comision_plataforma": 52.5, "monto_organizador": 367.5, "por_liquidar": 367.5}, b["resumen"]
assert client.get("/api/organizadores/1/pagos", headers=ADMIN).status_code == 200
r = client.get("/api/organizadores/2/pagos", headers=PABLO)
assert r.get_json()["resumen"]["monto_bruto"] == 270.0

# ======================= LIQUIDACIONES =======================
ayer, manana = (hoy - timedelta(days=1)).isoformat(), (hoy + timedelta(days=1)).isoformat()
base = {"organizador_id": 1, "cuenta_cobro_id": 1, "periodo_desde": ayer, "periodo_hasta": manana}
assert client.post("/api/liquidaciones", json=base, headers=MARTA).status_code == 403            # solo admin
for cambio, codigo, nombre in (
    ({"organizador_id": None}, 400, "falta organizador"), ({"organizador_id": 99}, 400, "organizador inexistente"),
    ({"cuenta_cobro_id": 3}, 400, "cuenta de otro organizador"), ({"cuenta_cobro_id": 99}, 400, "cuenta inexistente"),
    ({"cuenta_cobro_id": 2}, 409, "cuenta sin verificar"),
    ({"periodo_desde": "ayer"}, 400, "fecha mala"), ({"periodo_desde": manana, "periodo_hasta": ayer}, 400, "periodo invertido"),
    ({"moneda": "PESOS"}, 400, "moneda mala"),
    ({"periodo_desde": "2020-01-01", "periodo_hasta": "2020-01-31"}, 409, "periodo sin pagos"),
    ({"moneda": "USD"}, 409, "no hay pagos en esa moneda"),
):
    assert client.post("/api/liquidaciones", json={**base, **cambio}, headers=ADMIN).status_code == codigo, nombre

# Un reembolso solicitado ANTES de liquidar sigue siendo posible; despues de liquidar, no.
r = client.post("/api/liquidaciones", json=base, headers=ADMIN)
show("CREAR LIQUIDACION", r)
liq = r.get_json()
assert r.status_code == 201 and (liq["monto_bruto"], liq["monto_comision"], liq["monto_neto"]) == (420.0, 52.5, 367.5)
assert liq["estado"] == "pendiente" and len(liq["pagos"]) == 2
assert sql("SELECT COUNT(*) FROM pagos_inscripciones WHERE liquidacion_id=?", liq["id"])[0][0] == 2
assert client.post("/api/liquidaciones", json=base, headers=ADMIN).status_code == 409           # ya no queda nada por liquidar
assert client.get("/api/organizadores/1/pagos?por_liquidar=true", headers=MARTA).get_json()["total"] == 0
assert client.get("/api/organizadores/1/pagos", headers=MARTA).get_json()["resumen"]["por_liquidar"] == 0

# Ya liquidado: no se puede reembolsar el pago de Ana
r = client.post(f"/api/pagos/{pago_ana}/reembolsos", json={"motivo": "Quiero mi dinero"}, headers=ANA)
show("REEMBOLSO de un pago ya liquidado", r); assert r.status_code == 409 and "liquidación" in r.get_json()["error"]

# Consultas y permisos
assert client.get(f"/api/liquidaciones/{liq['id']}", headers=MARTA).status_code == 200
assert client.get(f"/api/liquidaciones/{liq['id']}", headers=ADMIN).status_code == 200
assert client.get(f"/api/liquidaciones/{liq['id']}", headers=PABLO).status_code == 404         # otro organizador
assert client.get(f"/api/liquidaciones/{liq['id']}", headers=ANA).status_code == 404
assert client.get("/api/liquidaciones", headers=MARTA).status_code == 403
assert client.get("/api/liquidaciones?estado=pendiente&organizador_id=1", headers=ADMIN).get_json()["total"] == 1
assert client.get("/api/liquidaciones?estado=raro", headers=ADMIN).status_code == 400
assert client.get("/api/organizadores/1/liquidaciones", headers=MARTA).get_json()["total"] == 1
assert client.get("/api/organizadores/1/liquidaciones", headers=PABLO).status_code == 403

# Pagarla
assert client.put(f"/api/liquidaciones/{liq['id']}/pagar", json={"referencia_pago": "SPEI-1"}, headers=MARTA).status_code == 403
assert client.put(f"/api/liquidaciones/{liq['id']}/pagar", json={}, headers=ADMIN).status_code == 400
r = client.put(f"/api/liquidaciones/{liq['id']}/pagar", json={"referencia_pago": "SPEI-445566"}, headers=ADMIN)
show("PAGAR LIQUIDACION", r)
assert r.status_code == 200 and r.get_json()["estado"] == "pagada" and r.get_json()["referencia_pago"] == "SPEI-445566" and r.get_json()["pagada_en"]
assert client.put(f"/api/liquidaciones/{liq['id']}/pagar", json={"referencia_pago": "otra"}, headers=ADMIN).status_code == 409
print("--- liquidaciones OK ---")

# ======================= PASARELA SIMULADA APAGADA (produccion) =======================
app.config["SIMULAR_PASARELA"] = False
ins_diana_pago = ins_diana["id"]
r = client.post("/api/pagos", json={"inscripcion_ids": [ins_diana_pago], "metodo": "tarjeta"}, headers=DIANA)
show("TARJETA con la pasarela simulada apagada", r); assert r.status_code == 501
r = client.post("/api/pagos", json={"inscripcion_ids": [ins_diana_pago], "metodo": "transferencia"}, headers=DIANA)
assert r.status_code == 201                                    # los metodos manuales siguen funcionando
assert client.post(f"/api/pagos/{r.get_json()['id']}/simular-pago", headers=DIANA).status_code == 403
app.config["SIMULAR_PASARELA"] = True

# ======================= CONTROL DE REDONDEO: nunca se pierde ni se inventa un centavo =======================
for (bruto, pct) in ((Decimal("33.33"), Decimal("12.5")), (Decimal("0.01"), Decimal("10")), (Decimal("199.99"), Decimal("7.35"))):
    from utils.pagos import q2
    com = q2(bruto * pct / 100)
    assert com + (bruto - com) == bruto
print("\nTODAS LAS PRUEBAS DE PAGOS PASARON")
