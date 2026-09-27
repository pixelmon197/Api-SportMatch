import os, sys, sqlite3

sys.path.insert(0, "/home/claude/work/api_sportmatch/Api-SportMatch")

DB_PATH = "/home/claude/work/test_soporte.sqlite3"
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
CREATE TABLE reportes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reportante_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    asignado_a INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    tipo_entidad VARCHAR(30) NOT NULL,
    entidad_id INTEGER NOT NULL,
    motivo VARCHAR(30) NOT NULL,
    descripcion TEXT,
    estado VARCHAR(20) NOT NULL DEFAULT 'abierto',
    accion_tomada VARCHAR(30),
    notas_moderador TEXT,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resuelto_en TIMESTAMP
);
CREATE TABLE tickets_soporte (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    asignado_a INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    categoria VARCHAR(20) NOT NULL,
    prioridad VARCHAR(20) NOT NULL DEFAULT 'media',
    estado VARCHAR(30) NOT NULL DEFAULT 'abierto',
    asunto VARCHAR(200) NOT NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cerrado_en TIMESTAMP
);
CREATE TABLE ticket_mensajes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL REFERENCES tickets_soporte(id) ON DELETE CASCADE,
    autor_id INTEGER NOT NULL REFERENCES usuarios(id),
    mensaje TEXT NOT NULL,
    es_interno BOOLEAN NOT NULL DEFAULT 0,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE auditoria_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id),
    accion TEXT NOT NULL, tipo_entidad TEXT NOT NULL, entidad_id INTEGER,
    datos_anteriores TEXT, datos_nuevos TEXT, ip TEXT,
    registrada_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

conn = sqlite3.connect(DB_PATH)
conn.executescript(DDL)
conn.execute("INSERT INTO usuarios (nombre_completo, correo, contrasena, fecha_nacimiento, sexo, nombre_usuario, rol, estado_cuenta, registro_completo_en) VALUES ('Ana Perez','ana@correo.com','x','2000-01-01','femenino','anaperez','usuario','activa',CURRENT_TIMESTAMP)")
conn.execute("INSERT INTO usuarios (nombre_completo, correo, contrasena, fecha_nacimiento, sexo, nombre_usuario, rol, estado_cuenta, registro_completo_en) VALUES ('Admin Uno','admin@correo.com','x','1990-01-01','masculino','admin1','admin','activa',CURRENT_TIMESTAMP)")
conn.commit()
conn.close()

from app import create_app
from flask_jwt_extended import create_access_token

app = create_app()
client = app.test_client()
with app.app_context():
    H_ANA = {"Authorization": f"Bearer {create_access_token(identity='1', additional_claims={'rol': 'usuario'})}"}
    H_ADMIN = {"Authorization": f"Bearer {create_access_token(identity='2', additional_claims={'rol': 'admin'})}"}

def show(label, resp):
    print(f"--- {label} [{resp.status_code}] ---")
    print(resp.get_json())

# ===== TICKETS =====

# 1) Crear ticket sin categoria -> antes violaba NOT NULL en Neon real (500)
r = client.post("/api/tickets", json={"asunto": "No puedo pagar", "mensaje": "Me sale error al pagar"}, headers=H_ANA)
show("CREAR TICKET (sin categoria)", r)
assert r.status_code == 400

# 2) categoria demasiado larga (>20 chars)
r = client.post("/api/tickets", json={
    "asunto": "No puedo pagar", "mensaje": "Error", "categoria": "esta-categoria-es-demasiado-larga",
}, headers=H_ANA)
show("CREAR TICKET (categoria muy larga)", r)
assert r.status_code == 400

# 3) Crear ticket valido
r = client.post("/api/tickets", json={"asunto": "No puedo pagar", "mensaje": "Me sale error al pagar", "categoria": "pagos"}, headers=H_ANA)
show("CREAR TICKET (valido)", r)
assert r.status_code == 201, r.get_json()
ticket_id = r.get_json()["id"]
assert r.get_json()["mensajes"][0]["mensaje"] == "Me sale error al pagar"

# 4) Agregar mensaje interno (admin) y publico
r = client.post(f"/api/tickets/{ticket_id}/mensajes", json={"mensaje": "Nota interna", "es_interno": True}, headers=H_ADMIN)
show("AGREGAR MENSAJE (interno)", r)
assert r.status_code == 201 and r.get_json()["es_interno"] is True

r = client.post(f"/api/tickets/{ticket_id}/mensajes", json={"mensaje": "Ya lo revisamos"}, headers=H_ADMIN)
show("AGREGAR MENSAJE (admin, publico)", r)
assert r.status_code == 201

# 5) Ana no debe ver el mensaje interno
r = client.get(f"/api/tickets/{ticket_id}", headers=H_ANA)
show("VER TICKET (Ana, sin internos)", r)
mensajes = r.get_json()["mensajes"]
assert all("interna" not in m["mensaje"] for m in mensajes)

# 6) Intentar dejar categoria vacia al actualizar -> 400 (no NOT NULL crudo)
r = client.put(f"/api/tickets/{ticket_id}", json={"categoria": ""}, headers=H_ADMIN)
show("ACTUALIZAR TICKET (categoria vacia)", r)
assert r.status_code == 400

# 7) Actualizar categoria valida y cerrar
r = client.put(f"/api/tickets/{ticket_id}", json={"categoria": "cuenta", "estado": "cerrado"}, headers=H_ADMIN)
show("ACTUALIZAR TICKET (categoria + cerrar)", r)
assert r.status_code == 200 and r.get_json()["estado"] == "cerrado"

# ===== REPORTES =====

# 8) Reporte con tipo_entidad valido
r = client.post("/api/reportes", json={"tipo_entidad": "usuario", "entidad_id": 1, "motivo": "spam"}, headers=H_ANA)
show("CREAR REPORTE (valido)", r)
assert r.status_code == 201
reporte_id = r.get_json()["id"]

# 9) motivo demasiado largo (>30 chars) -> antes error crudo de Postgres
r = client.post("/api/reportes", json={
    "tipo_entidad": "usuario", "entidad_id": 1,
    "motivo": "este motivo tiene mas de treinta caracteres seguro",
}, headers=H_ANA)
show("CREAR REPORTE (motivo muy largo)", r)
assert r.status_code == 400

# 10) moderar reporte con accion_tomada muy larga
r = client.put(f"/api/reportes/{reporte_id}", json={
    "estado": "resuelto", "accion_tomada": "esta accion tomada es demasiado larga para la columna",
}, headers=H_ADMIN)
show("MODERAR REPORTE (accion_tomada muy larga)", r)
assert r.status_code == 400

# 11) moderar reporte correctamente
r = client.put(f"/api/reportes/{reporte_id}", json={"estado": "resuelto", "accion_tomada": "advertencia"}, headers=H_ADMIN)
show("MODERAR REPORTE (valido)", r)
assert r.status_code == 200 and r.get_json()["resuelto_en"] is not None

print("\nTODAS LAS PRUEBAS DE SOPORTE PASARON")
