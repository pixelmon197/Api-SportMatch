import os, sys, sqlite3

sys.path.insert(0, "/home/claude/work/api_sportmatch/Api-SportMatch")

DB_PATH = "/home/claude/work/test_deportes.sqlite3"
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
CREATE TABLE deportes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE, categoria TEXT,
    activo BOOLEAN NOT NULL DEFAULT 1
);
CREATE TABLE usuario_deportes (
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    deporte_id INTEGER NOT NULL REFERENCES deportes(id),
    nivel TEXT, es_principal BOOLEAN NOT NULL DEFAULT 0,
    PRIMARY KEY (usuario_id, deporte_id),
    CHECK (nivel IN ('principiante','intermedio','avanzado','profesional') OR nivel IS NULL)
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

# 1) Admin crea deportes
r = client.post("/api/deportes", json={"nombre": "Running", "categoria": "resistencia"}, headers=H_ADMIN)
show("CREAR DEPORTE", r)
assert r.status_code == 201
running_id = r.get_json()["id"]

r = client.post("/api/deportes", json={"nombre": "Ciclismo"}, headers=H_ADMIN)
ciclismo_id = r.get_json()["id"]

# 2) Nombre duplicado -> 409
r = client.post("/api/deportes", json={"nombre": "Running"}, headers=H_ADMIN)
show("CREAR DEPORTE (nombre duplicado)", r)
assert r.status_code == 409

# 3) Listar publico (solo activos)
r = client.get("/api/deportes")
show("LISTAR DEPORTES", r)
assert r.status_code == 200 and len(r.get_json()) == 2

# 4) Ana agrega Running a sus deportes
r = client.post("/api/deportes/me", json={"deporte_id": running_id, "nivel": "intermedio", "es_principal": True}, headers=H_ANA)
show("AGREGAR MI DEPORTE (Running)", r)
assert r.status_code == 201
assert r.get_json()["es_principal"] is True

# 5) Ana agrega Ciclismo como principal -> Running deja de ser principal
r = client.post("/api/deportes/me", json={"deporte_id": ciclismo_id, "es_principal": True}, headers=H_ANA)
show("AGREGAR MI DEPORTE (Ciclismo, principal)", r)
assert r.status_code == 201

r = client.get("/api/deportes/me", headers=H_ANA)
show("MIS DEPORTES", r)
principales = [d for d in r.get_json() if d["es_principal"]]
assert len(principales) == 1 and principales[0]["deporte"]["nombre"] == "Ciclismo"

# 6) Agregar el mismo deporte otra vez -> 409 (PK compuesta)
r = client.post("/api/deportes/me", json={"deporte_id": running_id}, headers=H_ANA)
show("AGREGAR MI DEPORTE (duplicado)", r)
assert r.status_code == 409

# 7) nivel invalido
r = client.post("/api/deportes/me", json={"deporte_id": ciclismo_id, "nivel": "elite"}, headers=H_ANA)
show("AGREGAR MI DEPORTE (nivel invalido, ya existente de todos modos)", r)
assert r.status_code == 400

# 8) Actualizar nivel
r = client.put(f"/api/deportes/me/{running_id}", json={"nivel": "avanzado"}, headers=H_ANA)
show("ACTUALIZAR MI DEPORTE (nivel)", r)
assert r.status_code == 200 and r.get_json()["nivel"] == "avanzado"

# 9) Desactivar deporte (soft delete) y confirmar que ya no sale en listado publico
r = client.delete(f"/api/deportes/{running_id}", headers=H_ADMIN)
show("DESACTIVAR DEPORTE", r)
assert r.status_code == 200
r = client.get("/api/deportes")
assert running_id not in [d["id"] for d in r.get_json()]

# 10) Quitar mi deporte
r = client.delete(f"/api/deportes/me/{ciclismo_id}", headers=H_ANA)
show("QUITAR MI DEPORTE", r)
assert r.status_code == 204

print("\nTODAS LAS PRUEBAS DE DEPORTES PASARON")
