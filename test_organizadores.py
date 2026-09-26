import os, sys, sqlite3

sys.path.insert(0, "/home/claude/work/api_sportmatch/Api-SportMatch")

DB_PATH = "/home/claude/work/test_organizadores.sqlite3"
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "test"
os.environ["JWT_SECRET_KEY"] = "test"

DDL = """
CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_completo TEXT NOT NULL,
    correo TEXT UNIQUE,
    contrasena TEXT,
    fecha_nacimiento DATE,
    sexo TEXT,
    rol TEXT NOT NULL DEFAULT 'usuario',
    estado_cuenta TEXT NOT NULL DEFAULT 'pendiente_verificacion',
    correo_verificado_en TIMESTAMP,
    registro_completo_en TIMESTAMP,
    ultimo_acceso TIMESTAMP,
    nombre_usuario TEXT UNIQUE,
    telefono TEXT,
    ciudad_id INTEGER,
    idioma TEXT DEFAULT 'es',
    zona_horaria TEXT DEFAULT 'America/Mexico_City',
    codigo_referido TEXT UNIQUE,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    eliminado_en TIMESTAMP
);

CREATE TABLE organizadores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL UNIQUE REFERENCES usuarios(id),
    nombre_comercial TEXT NOT NULL,
    descripcion TEXT,
    correo_contacto TEXT,
    telefono_contacto TEXT,
    ciudad_id INTEGER,
    logo_id INTEGER,
    estado_validacion TEXT NOT NULL DEFAULT 'sin_solicitud',
    validado_en TIMESTAMP,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    eliminado_en TIMESTAMP,
    CHECK (estado_validacion IN ('sin_solicitud','pendiente','en_revision','aprobada','rechazada','revocada'))
);

CREATE TABLE organizador_miembros (
    organizador_id INTEGER NOT NULL REFERENCES organizadores(id) ON DELETE CASCADE,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    rol TEXT NOT NULL DEFAULT 'colaborador',
    agregado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (organizador_id, usuario_id),
    CHECK (rol IN ('propietario','administrador','colaborador'))
);

CREATE TABLE solicitudes_validacion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organizador_id INTEGER NOT NULL REFERENCES organizadores(id) ON DELETE CASCADE,
    estado TEXT NOT NULL DEFAULT 'pendiente',
    revisor_id INTEGER REFERENCES usuarios(id),
    comentarios TEXT,
    motivo_rechazo TEXT,
    enviada_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resuelta_en TIMESTAMP,
    CHECK (estado IN ('pendiente','en_revision','aprobada','rechazada'))
);

CREATE TABLE documentos_validacion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    solicitud_id INTEGER NOT NULL REFERENCES solicitudes_validacion(id) ON DELETE CASCADE,
    tipo_documento TEXT NOT NULL,
    archivo_id INTEGER NOT NULL,
    numero_documento TEXT,
    verificado BOOLEAN NOT NULL DEFAULT 0,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (tipo_documento IN ('ine','curp','comprobante_domicilio','rfc','permiso_evento'))
);

CREATE TABLE cuentas_cobro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organizador_id INTEGER NOT NULL REFERENCES organizadores(id) ON DELETE CASCADE,
    banco TEXT NOT NULL,
    titular TEXT NOT NULL,
    clabe TEXT NOT NULL,
    verificada BOOLEAN NOT NULL DEFAULT 0,
    es_principal BOOLEAN NOT NULL DEFAULT 0,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    eliminado_en TIMESTAMP
);
"""

conn = sqlite3.connect(DB_PATH)
conn.executescript(DDL)

# Usuarios de prueba: uno normal (futuro organizador) y un admin.
conn.execute(
    "INSERT INTO usuarios (nombre_completo, correo, contrasena, fecha_nacimiento, sexo, nombre_usuario, rol, estado_cuenta, registro_completo_en) "
    "VALUES ('Ana Perez', 'ana@correo.com', 'x', '2000-01-01', 'femenino', 'anaperez', 'usuario', 'activa', CURRENT_TIMESTAMP)"
)
conn.execute(
    "INSERT INTO usuarios (nombre_completo, correo, contrasena, fecha_nacimiento, sexo, nombre_usuario, rol, estado_cuenta, registro_completo_en) "
    "VALUES ('Admin Uno', 'admin@correo.com', 'x', '1990-01-01', 'masculino', 'admin1', 'admin', 'activa', CURRENT_TIMESTAMP)"
)
conn.execute(
    "INSERT INTO usuarios (nombre_completo, correo, contrasena, fecha_nacimiento, sexo, nombre_usuario, rol, estado_cuenta, registro_completo_en) "
    "VALUES ('Luis Gomez', 'luis@correo.com', 'x', '1998-01-01', 'masculino', 'luisg', 'usuario', 'activa', CURRENT_TIMESTAMP)"
)
conn.commit()
conn.close()

from app import create_app
from flask_jwt_extended import create_access_token

app = create_app()
client = app.test_client()

with app.app_context():
    token_ana = create_access_token(identity="1", additional_claims={"rol": "usuario"})
    token_admin = create_access_token(identity="2", additional_claims={"rol": "admin"})
    token_luis = create_access_token(identity="3", additional_claims={"rol": "usuario"})

H_ANA = {"Authorization": f"Bearer {token_ana}"}
H_ADMIN = {"Authorization": f"Bearer {token_admin}"}
H_LUIS = {"Authorization": f"Bearer {token_luis}"}

def show(label, resp):
    print(f"--- {label} [{resp.status_code}] ---")
    print(resp.get_json())

# 1) Ana crea su perfil de organizador -> debe quedar "sin_solicitud"
r = client.post("/api/organizadores", json={"nombre_comercial": "Carreras del Valle"}, headers=H_ANA)
show("CREAR ORGANIZADOR", r)
assert r.status_code == 201
org = r.get_json()
assert org["estado_validacion"] == "sin_solicitud", org["estado_validacion"]
organizador_id = org["id"]

# 2) Listar público (default solo aprobadas) -> no debe aparecer todavía
r = client.get("/api/organizadores")
show("LISTAR (publico)", r)
assert r.status_code == 200 and organizador_id not in [o["id"] for o in r.get_json()]

# 3) Agregar miembro sin especificar rol -> debe usar 'colaborador' (no 'editor')
r = client.post(f"/api/organizadores/{organizador_id}/miembros", json={"usuario_id": 3}, headers=H_ANA)
show("AGREGAR MIEMBRO (rol default)", r)
assert r.status_code == 201
assert r.get_json()["rol"] == "colaborador", r.get_json()["rol"]

# 4) Agregar cuenta de cobro
r = client.post(f"/api/organizadores/{organizador_id}/cuentas-cobro",
                json={"banco": "BBVA", "titular": "Ana Perez", "clabe": "012345678901234567"}, headers=H_ANA)
show("AGREGAR CUENTA COBRO", r)
assert r.status_code == 201
cuenta_id = r.get_json()["id"]

# 5) Enviar solicitud de validación con un documento (con archivo_id)
r = client.post(f"/api/organizadores/{organizador_id}/solicitudes",
                json={"documentos": [{"tipo_documento": "ine", "archivo_id": 101}]}, headers=H_ANA)
show("ENVIAR SOLICITUD", r)
assert r.status_code == 201
solicitud_id = r.get_json()["id"]

# 5b) organizador debe pasar a en_revision
r = client.get(f"/api/organizadores/{organizador_id}")
show("VER ORGANIZADOR (tras enviar solicitud)", r)
assert r.get_json()["estado_validacion"] == "en_revision"

# 6) Documento con tipo_documento inválido debe rechazarse (400), no explotar (500)
r = client.post(f"/api/organizadores/solicitudes/{solicitud_id}/documentos",
                json={"tipo_documento": "no-valido", "archivo_id": 5}, headers=H_ANA)
show("AGREGAR DOCUMENTO (tipo invalido)", r)
assert r.status_code == 400

# 7) Documento sin archivo_id debe rechazarse (400), no violar NOT NULL
r = client.post(f"/api/organizadores/solicitudes/{solicitud_id}/documentos",
                json={"tipo_documento": "rfc"}, headers=H_ANA)
show("AGREGAR DOCUMENTO (sin archivo_id)", r)
assert r.status_code == 400

# 8) Documento válido
r = client.post(f"/api/organizadores/solicitudes/{solicitud_id}/documentos",
                json={"tipo_documento": "rfc", "archivo_id": 102}, headers=H_ANA)
show("AGREGAR DOCUMENTO (valido)", r)
assert r.status_code == 201

# 9) Admin lista solicitudes pendientes
r = client.get("/api/organizadores/solicitudes", headers=H_ADMIN)
show("LISTAR SOLICITUDES (admin)", r)
assert r.status_code == 200 and len(r.get_json()) == 1

# 10) Admin aprueba
r = client.put(f"/api/organizadores/solicitudes/{solicitud_id}/revisar",
                json={"decision": "aprobar"}, headers=H_ADMIN)
show("APROBAR SOLICITUD", r)
assert r.status_code == 200
assert r.get_json()["organizador"]["estado_validacion"] == "aprobada"
assert r.get_json()["solicitud"]["estado"] == "aprobada"

# 11) Ahora sí debe aparecer en el listado público (aprobada)
r = client.get("/api/organizadores")
show("LISTAR (publico, tras aprobar)", r)
assert organizador_id in [o["id"] for o in r.get_json()]

# 12) Verificar cuenta de cobro (admin)
r = client.put(f"/api/organizadores/cuentas-cobro/{cuenta_id}/verificar", headers=H_ADMIN)
show("VERIFICAR CUENTA COBRO", r)
assert r.status_code == 200 and r.get_json()["verificada"] is True

# 13) Un usuario ajeno (Luis, sin ser miembro con permisos) no puede gestionar
r = client.put(f"/api/organizadores/{organizador_id}", json={"descripcion": "hackeo"}, headers=H_LUIS)
show("ACTUALIZAR (usuario ajeno, debe fallar)", r)
assert r.status_code == 403

# 14) Segundo organizador para probar rechazo
r = client.post("/api/organizadores", json={"nombre_comercial": "Otro Organizador"}, headers=H_LUIS)
org2_id = r.get_json()["id"]
r = client.post(f"/api/organizadores/{org2_id}/solicitudes", json={}, headers=H_LUIS)
solicitud2_id = r.get_json()["id"]
r = client.put(f"/api/organizadores/solicitudes/{solicitud2_id}/revisar",
                json={"decision": "rechazar", "motivo_rechazo": "Datos incompletos"}, headers=H_ADMIN)
show("RECHAZAR SOLICITUD", r)
assert r.status_code == 200
assert r.get_json()["organizador"]["estado_validacion"] == "rechazada"
assert r.get_json()["solicitud"]["estado"] == "rechazada"

print("\nTODAS LAS PRUEBAS DE ORGANIZADORES PASARON")
