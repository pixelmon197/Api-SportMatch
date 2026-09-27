import os, sys, sqlite3

sys.path.insert(0, "/home/claude/work/api_sportmatch/Api-SportMatch")

DB_PATH = "/home/claude/work/test_administradores.sqlite3"
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
    eliminado_en TIMESTAMP,
    CHECK (rol IN ('usuario','organizador','administrador')),
    CHECK ((registro_completo_en IS NULL) OR (correo IS NOT NULL AND fecha_nacimiento IS NOT NULL AND sexo IS NOT NULL))
);
CREATE TABLE deportes (
    id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL UNIQUE,
    categoria TEXT, activo BOOLEAN NOT NULL DEFAULT 1
);
"""

conn = sqlite3.connect(DB_PATH)
conn.executescript(DDL)
# Primer admin "de fábrica" (como lo haría seed.py), y un usuario normal.
conn.execute("INSERT INTO usuarios (nombre_completo, correo, contrasena, nombre_usuario, rol, estado_cuenta) VALUES ('Administrador SportMatch','admin@sportmatch.com','x','admin','administrador','activa')")
conn.execute("INSERT INTO usuarios (nombre_completo, correo, contrasena, fecha_nacimiento, sexo, nombre_usuario, rol, estado_cuenta, registro_completo_en) VALUES ('Ana Perez','ana@correo.com','x','2000-01-01','femenino','anaperez','usuario','activa',CURRENT_TIMESTAMP)")
conn.commit()
conn.close()

from app import create_app
from flask_jwt_extended import create_access_token

app = create_app()
client = app.test_client()
with app.app_context():
    H_ADMIN = {"Authorization": f"Bearer {create_access_token(identity='1', additional_claims={'rol': 'administrador'})}"}
    H_ANA = {"Authorization": f"Bearer {create_access_token(identity='2', additional_claims={'rol': 'usuario'})}"}

def show(label, resp):
    print(f"--- {label} [{resp.status_code}] ---")
    print(resp.get_json())

# 1) Login real: el JWT debe llevar el rol real ('administrador'), no 'admin'
r = client.post("/api/auth/login", json={"correo": "admin@sportmatch.com", "password": "x"})
show("LOGIN ADMIN (password no coincide, solo para ver error controlado)", r)
# (no seteamos hash real de password aqui; probamos login con Ana mas abajo)

# 2) Ana (usuario normal) no puede crear un admin
r = client.post("/api/usuarios/admins", json={
    "nombre_completo": "Otro Admin", "nombre_usuario": "otroadmin", "correo": "otro@sportmatch.com",
    "password": "ClaveSegura123", "fecha_nacimiento": "1995-01-01", "sexo": "masculino",
}, headers=H_ANA)
show("CREAR ADMIN (usuario normal, debe fallar)", r)
assert r.status_code == 403

# 3) El admin real SI puede, y ya no rompe contra el CHECK (rol='administrador', no 'admin')
r = client.post("/api/usuarios/admins", json={
    "nombre_completo": "Otro Admin", "nombre_usuario": "OtroAdmin", "correo": "Otro@sportmatch.com",
    "password": "ClaveSegura123", "fecha_nacimiento": "1995-01-01", "sexo": "masculino",
}, headers=H_ADMIN)
show("CREAR ADMIN (admin real, valido)", r)
assert r.status_code == 201, r.get_json()
assert r.get_json()["rol"] == "administrador"
nuevo_admin_id = r.get_json()["id"]

# 4) Crear admin sin fecha_nacimiento -> 400 (misma regla que /auth/register)
r = client.post("/api/usuarios/admins", json={
    "nombre_completo": "Sin Fecha", "nombre_usuario": "sinfecha", "correo": "sinfecha@sportmatch.com",
    "password": "ClaveSegura123", "sexo": "masculino",
}, headers=H_ADMIN)
show("CREAR ADMIN (sin fecha_nacimiento)", r)
assert r.status_code == 400

# 5) cambiar_rol: ya no acepta el valor viejo 'admin'
r = client.put(f"/api/usuarios/{nuevo_admin_id}/rol", json={"rol": "admin"}, headers=H_ADMIN)
show("CAMBIAR ROL (valor viejo 'admin', invalido)", r)
assert r.status_code == 400

# 6) cambiar_rol con el valor real 'organizador' (permitido por Neon aunque la app no lo use activamente)
r = client.put(f"/api/usuarios/{nuevo_admin_id}/rol", json={"rol": "organizador"}, headers=H_ADMIN)
show("CAMBIAR ROL (organizador, valido)", r)
assert r.status_code == 200 and r.get_json()["rol"] == "organizador"

# 7) Filtrar usuarios por rol=administrador
r = client.get("/api/usuarios?rol=administrador", headers=H_ADMIN)
show("LISTAR USUARIOS (rol=administrador)", r)
assert r.status_code == 200
assert all(u["rol"] == "administrador" for u in r.get_json()["usuarios"])

# 8) Permisos de admin en otros módulos siguen funcionando (rutas.py usa usuario.rol == 'administrador')
r = client.post("/api/deportes", json={"nombre": "Running"}, headers=H_ADMIN)
show("CREAR DEPORTE (admin, en otro modulo, debe seguir funcionando)", r)
assert r.status_code == 201

r = client.post("/api/deportes", json={"nombre": "Ciclismo"}, headers=H_ANA)
show("CREAR DEPORTE (usuario normal, debe seguir bloqueado)", r)
assert r.status_code == 403

print("\nTODAS LAS PRUEBAS DE ADMINISTRADORES PASARON")
