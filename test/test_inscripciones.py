import os, sys, sqlite3
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/home/claude/work/api_sportmatch/Api-SportMatch")

DB_PATH = "/home/claude/work/test_inscripciones.sqlite3"
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "test"
os.environ["JWT_SECRET_KEY"] = "test"

DDL = """
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
CREATE TABLE organizadores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL UNIQUE REFERENCES usuarios(id),
    nombre_comercial TEXT NOT NULL,
    estado_validacion TEXT NOT NULL DEFAULT 'sin_solicitud',
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE organizador_miembros (
    organizador_id INTEGER NOT NULL REFERENCES organizadores(id) ON DELETE CASCADE,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    rol TEXT NOT NULL DEFAULT 'colaborador',
    agregado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (organizador_id, usuario_id)
);
CREATE TABLE eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organizador_id INTEGER NOT NULL REFERENCES organizadores(id),
    tipo TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'borrador',
    dificultad TEXT, titulo TEXT NOT NULL, slug TEXT NOT NULL UNIQUE,
    descripcion TEXT, portada_id INTEGER, edad_minima INTEGER,
    es_publico BOOLEAN NOT NULL DEFAULT 1, publicado_en TIMESTAMP,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    eliminado_en TIMESTAMP
);
CREATE TABLE evento_categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL, distancia_km NUMERIC, edad_minima INTEGER,
    edad_maxima INTEGER, cupo_total INTEGER,
    permite_lista_espera BOOLEAN NOT NULL DEFAULT 0,
    UNIQUE (id, evento_id)
);
CREATE TABLE evento_boletos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria_id INTEGER NOT NULL REFERENCES evento_categorias(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL, precio NUMERIC NOT NULL,
    moneda TEXT NOT NULL DEFAULT 'MXN',
    disponible_desde TIMESTAMP, disponible_hasta TIMESTAMP,
    cantidad_maxima INTEGER, activo BOOLEAN NOT NULL DEFAULT 1,
    UNIQUE (id, categoria_id)
);
CREATE TABLE evento_fechas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
    inicia_en TIMESTAMP NOT NULL, termina_en TIMESTAMP, cancelada_en TIMESTAMP,
    UNIQUE (id, evento_id)
);
CREATE TABLE paquetes_recuperacion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
    nivel TEXT NOT NULL, nombre TEXT NOT NULL, descripcion TEXT,
    precio NUMERIC NOT NULL, moneda TEXT NOT NULL DEFAULT 'MXN',
    activo BOOLEAN NOT NULL DEFAULT 1,
    UNIQUE (evento_id, nivel), UNIQUE (id, evento_id),
    CHECK (nivel IN ('basico','medio','premium')),
    CHECK (precio >= 0)
);
CREATE TABLE inscripciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    evento_id INTEGER NOT NULL REFERENCES eventos(id),
    fecha_id INTEGER NOT NULL,
    categoria_id INTEGER NOT NULL,
    boleto_id INTEGER,
    paquete_id INTEGER,
    estado TEXT NOT NULL DEFAULT 'pendiente_pago',
    numero_participante TEXT,
    inscrita_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cancelada_en TIMESTAMP, asistio_en TIMESTAMP,
    asistencia_latitud NUMERIC, asistencia_longitud NUMERIC,
    tiempo_oficial TIME, posicion_general INTEGER, posicion_categoria INTEGER,
    FOREIGN KEY (categoria_id, evento_id) REFERENCES evento_categorias(id, evento_id),
    FOREIGN KEY (fecha_id, evento_id) REFERENCES evento_fechas(id, evento_id),
    FOREIGN KEY (boleto_id, categoria_id) REFERENCES evento_boletos(id, categoria_id),
    FOREIGN KEY (paquete_id, evento_id) REFERENCES paquetes_recuperacion(id, evento_id),
    CHECK (estado IN ('pendiente_pago','inscrito','activo','lista_espera','completado','cancelado','no_asistio')),
    CHECK (posicion_general IS NULL OR posicion_general > 0),
    CHECK (posicion_categoria IS NULL OR posicion_categoria > 0)
);
CREATE TABLE valoraciones_evento (
    inscripcion_id INTEGER PRIMARY KEY REFERENCES inscripciones(id) ON DELETE CASCADE,
    calificacion_evento INTEGER, calificacion_organizador INTEGER,
    comentario TEXT, respuesta_organizador TEXT, respondida_en TIMESTAMP,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (calificacion_evento IS NULL OR (calificacion_evento BETWEEN 1 AND 5)),
    CHECK (calificacion_organizador IS NULL OR (calificacion_organizador BETWEEN 1 AND 5))
);
CREATE TABLE calendario_usuario (
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    fecha_id INTEGER NOT NULL REFERENCES evento_fechas(id) ON DELETE CASCADE,
    agregado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usuario_id, fecha_id)
);
"""

conn = sqlite3.connect(DB_PATH)
conn.executescript(DDL)
conn.execute("INSERT INTO usuarios (nombre_completo, correo, contrasena, fecha_nacimiento, sexo, nombre_usuario, rol, estado_cuenta, registro_completo_en) VALUES ('Ana Perez','ana@correo.com','x','2000-01-01','femenino','anaperez','usuario','activa',CURRENT_TIMESTAMP)")
conn.execute("INSERT INTO usuarios (nombre_completo, correo, contrasena, fecha_nacimiento, sexo, nombre_usuario, rol, estado_cuenta, registro_completo_en) VALUES ('Luis Gomez','luis@correo.com','x','1998-01-01','masculino','luisg','usuario','activa',CURRENT_TIMESTAMP)")
conn.execute("INSERT INTO usuarios (nombre_completo, correo, contrasena, fecha_nacimiento, sexo, nombre_usuario, rol, estado_cuenta, registro_completo_en) VALUES ('Admin Uno','admin@correo.com','x','1990-01-01','masculino','admin1','administrador','activa',CURRENT_TIMESTAMP)")
conn.execute("INSERT INTO organizadores (usuario_id, nombre_comercial, estado_validacion) VALUES (1,'Carreras del Valle','aprobada')")
conn.execute("INSERT INTO organizador_miembros (organizador_id, usuario_id, rol) VALUES (1,1,'propietario')")
conn.execute("INSERT INTO eventos (organizador_id, tipo, estado, titulo, slug, publicado_en) VALUES (1,'carrera','publicado','5K Nocturna','5k-nocturna',CURRENT_TIMESTAMP)")
conn.execute("INSERT INTO evento_categorias (evento_id, nombre, cupo_total, permite_lista_espera) VALUES (1,'5K Varonil',1,1)")
conn.execute("INSERT INTO evento_boletos (categoria_id, tipo, precio) VALUES (1,'general',250)")
conn.execute("INSERT INTO evento_fechas (evento_id, inicia_en) VALUES (1, '2026-11-15T19:00:00')")
conn.commit()
conn.close()

from app import create_app
from flask_jwt_extended import create_access_token

app = create_app()
client = app.test_client()
with app.app_context():
    H_ANA = {"Authorization": f"Bearer {create_access_token(identity='1', additional_claims={'rol': 'usuario'})}"}
    H_LUIS = {"Authorization": f"Bearer {create_access_token(identity='2', additional_claims={'rol': 'usuario'})}"}
    H_ADMIN = {"Authorization": f"Bearer {create_access_token(identity='3', additional_claims={'rol': 'administrador'})}"}

def show(label, resp):
    print(f"--- {label} [{resp.status_code}] ---")
    print(resp.get_json())

# 1) Crear paquete de recuperacion con nivel invalido
r = client.post("/api/eventos/1/paquetes", json={"nombre": "Kit", "nivel": "oro"}, headers=H_ANA)
show("CREAR PAQUETE (nivel invalido)", r)
assert r.status_code == 400

# 2) Crear paquete valido
r = client.post("/api/eventos/1/paquetes", json={"nombre": "Kit Basico", "nivel": "basico", "precio": 100}, headers=H_ANA)
show("CREAR PAQUETE (valido)", r)
assert r.status_code == 201
paquete_id = r.get_json()["id"]

# 3) Paquete duplicado (mismo evento+nivel)
r = client.post("/api/eventos/1/paquetes", json={"nombre": "Otro basico", "nivel": "basico", "precio": 50}, headers=H_ANA)
show("CREAR PAQUETE (nivel duplicado)", r)
assert r.status_code == 409

# 4) Inscripcion de Ana (cupo_total=1) -> pendiente_pago
r = client.post("/api/inscripciones", json={
    "evento_id": 1, "fecha_id": 1, "categoria_id": 1, "boleto_id": 1, "paquete_id": paquete_id,
}, headers=H_ANA)
show("CREAR INSCRIPCION (Ana)", r)
assert r.status_code == 201, r.get_json()
inscripcion_ana = r.get_json()
assert inscripcion_ana["estado"] == "pendiente_pago"
inscripcion_ana_id = inscripcion_ana["id"]

# 5) Inscripcion de Luis -> cupo ya lleno (cupo_total=1, Ana ocupa el unico lugar) -> lista_espera
r = client.post("/api/inscripciones", json={
    "evento_id": 1, "fecha_id": 1, "categoria_id": 1, "boleto_id": 1,
}, headers=H_LUIS)
show("CREAR INSCRIPCION (Luis, cupo lleno -> lista_espera)", r)
assert r.status_code == 201
inscripcion_luis_id = r.get_json()["id"]
assert r.get_json()["estado"] == "lista_espera"

# 6) Cancelar la de Ana -> Luis debe subir de lista_espera a pendiente_pago
r = client.put(f"/api/inscripciones/{inscripcion_ana_id}/cancelar", headers=H_ANA)
show("CANCELAR INSCRIPCION (Ana)", r)
assert r.status_code == 200 and r.get_json()["estado"] == "cancelado"

r = client.get(f"/api/inscripciones/{inscripcion_luis_id}", headers=H_LUIS)
show("VER INSCRIPCION (Luis, tras cancelacion de Ana)", r)
assert r.get_json()["estado"] == "pendiente_pago"

# 7) cambiar_estado con valor invalido (vocabulario viejo 'confirmada')
r = client.put(f"/api/inscripciones/{inscripcion_luis_id}/estado", json={"estado": "confirmada"}, headers=H_ANA)
show("CAMBIAR ESTADO (valor viejo invalido)", r)
assert r.status_code == 400

# 8) cambiar_estado a 'inscrito' (valor real valido)
r = client.put(f"/api/inscripciones/{inscripcion_luis_id}/estado", json={"estado": "inscrito"}, headers=H_ANA)
show("CAMBIAR ESTADO (inscrito, valido)", r)
assert r.status_code == 200 and r.get_json()["estado"] == "inscrito"

# 9) Registrar resultado con tiempo_oficial (antes: string en columna time real -> fallaba)
r = client.put(f"/api/inscripciones/{inscripcion_luis_id}/resultado", json={
    "asistio": True, "tiempo_oficial": "00:25:30", "posicion_general": 1, "completada": True,
}, headers=H_ANA)
show("REGISTRAR RESULTADO", r)
assert r.status_code == 200, r.get_json()
assert r.get_json()["tiempo_oficial"] == "00:25:30"
assert r.get_json()["estado"] == "completado"

# 10) posicion_general invalida (0 o negativa)
r = client.put(f"/api/inscripciones/{inscripcion_luis_id}/resultado", json={"posicion_general": 0}, headers=H_ANA)
show("REGISTRAR RESULTADO (posicion invalida)", r)
assert r.status_code == 400

# 11) Valorar el evento (inscripcion completada)
r = client.post(f"/api/inscripciones/{inscripcion_luis_id}/valoracion", json={
    "calificacion_evento": 5, "calificacion_organizador": 4, "comentario": "Excelente"}, headers=H_LUIS)
show("VALORAR EVENTO", r)
assert r.status_code == 201, r.get_json()
assert r.get_json()["inscripcion_id"] == inscripcion_luis_id

# 12) Listar valoraciones del evento
r = client.get("/api/eventos/1/valoraciones")
show("LISTAR VALORACIONES", r)
assert r.status_code == 200 and len(r.get_json()) == 1

# 13) Responder la valoracion (usa inscripcion_id como identificador, ya no un 'id' propio)
r = client.put(f"/api/valoraciones/{inscripcion_luis_id}/responder",
                json={"respuesta_organizador": "Gracias por venir!"}, headers=H_ANA)
show("RESPONDER VALORACION", r)
assert r.status_code == 200

# 14) Calendario personal
r = client.post("/api/usuarios/me/calendario", json={"fecha_id": 1}, headers=H_LUIS)
show("AGREGAR A CALENDARIO", r)
assert r.status_code == 201
r = client.post("/api/usuarios/me/calendario", json={"fecha_id": 1}, headers=H_LUIS)
show("AGREGAR A CALENDARIO (duplicado)", r)
assert r.status_code == 409

print("\nTODAS LAS PRUEBAS DE INSCRIPCIONES PASARON")
