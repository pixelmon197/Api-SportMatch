import os
import sys

sys.path.insert(0, "/home/claude/work/api_sportmatch/Api-SportMatch")

DB_PATH = "/home/claude/work/test_neon_like.sqlite3"
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "test"
os.environ["JWT_SECRET_KEY"] = "test"

import sqlite3

# DDL traducido de Neon.sql (mismos nombres/constraints reales de columnas
# y CHECKs, para las tablas que tocan Login/Register/Olvide/Restablecer).
DDL = """
CREATE TABLE ciudades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL
);

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
    ciudad_id INTEGER REFERENCES ciudades(id),
    idioma TEXT DEFAULT 'es',
    zona_horaria TEXT DEFAULT 'America/Mexico_City',
    codigo_referido TEXT UNIQUE,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    eliminado_en TIMESTAMP,
    CHECK ((registro_completo_en IS NULL) OR (correo IS NOT NULL AND fecha_nacimiento IS NOT NULL AND sexo IS NOT NULL)),
    CHECK (correo = lower(correo)),
    CHECK (estado_cuenta IN ('pendiente_verificacion','activa','suspendida','eliminada')),
    CHECK (rol IN ('usuario','organizador','administrador')),
    CHECK (nombre_usuario = lower(nombre_usuario)),
    CHECK (sexo IN ('masculino','femenino','otro','prefiero_no_decir'))
);

CREATE TABLE tokens_verificacion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    correo_nuevo TEXT,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expira_en TIMESTAMP NOT NULL,
    usado_en TIMESTAMP,
    CHECK (expira_en > creado_en),
    CHECK (tipo <> 'cambio_correo' OR correo_nuevo IS NOT NULL),
    CHECK (tipo IN ('verificacion_correo','restablecer_contrasena','cambio_correo')),
    CHECK (length(token_hash) <= 64)
);
"""

conn = sqlite3.connect(DB_PATH)
conn.executescript(DDL)
conn.commit()
conn.close()

from app import create_app

app = create_app()
client = app.test_client()

def show(label, resp):
    print(f"--- {label} [{resp.status_code}] ---")
    print(resp.get_json())

# 1) Registro con datos válidos
r = client.post("/api/auth/register", json={
    "nombre_completo": "Ana Perez",
    "nombre_usuario": "AnaPerez",  # con mayúsculas a propósito, debe normalizarse
    "correo": "Ana@Correo.com",
    "password": "ClaveSegura123",
    "fecha_nacimiento": "2000-05-10",
    "sexo": "femenino",
})
show("REGISTER", r)
assert r.status_code == 201, "Register debería responder 201"

# 2) Login con las credenciales recién creadas
r = client.post("/api/auth/login", json={"correo": "ana@correo.com", "password": "ClaveSegura123"})
show("LOGIN", r)
assert r.status_code == 200, "Login debería responder 200"

# 3) Olvidé mi contraseña
r = client.post("/api/auth/olvide-contrasena", json={"correo": "ana@correo.com"})
show("OLVIDE_CONTRASENA", r)
assert r.status_code == 200
token = r.get_json().get("token_reseteo")
assert token, "Debe regresar un token de prueba"

# 3b) Olvidé mi contraseña con correo inexistente (no debe filtrar existencia)
r = client.post("/api/auth/olvide-contrasena", json={"correo": "no-existe@correo.com"})
show("OLVIDE_CONTRASENA (correo inexistente)", r)
assert r.status_code == 200 and "token_reseteo" not in r.get_json()

# 4) Restablecer contraseña con el token
r = client.post("/api/auth/restablecer-contrasena", json={"token": token, "nueva_password": "OtraClave456"})
show("RESTABLECER_CONTRASENA", r)
assert r.status_code == 200

# 5) Login con la contraseña vieja debe fallar
r = client.post("/api/auth/login", json={"correo": "ana@correo.com", "password": "ClaveSegura123"})
show("LOGIN (password vieja, debe fallar)", r)
assert r.status_code == 401

# 6) Login con la contraseña nueva debe funcionar
r = client.post("/api/auth/login", json={"correo": "ana@correo.com", "password": "OtraClave456"})
show("LOGIN (password nueva)", r)
assert r.status_code == 200

# 7) Reusar el mismo token de reseteo debe fallar (ya usado)
r = client.post("/api/auth/restablecer-contrasena", json={"token": token, "nueva_password": "Otra789Clave"})
show("RESTABLECER_CONTRASENA (token reusado, debe fallar)", r)
assert r.status_code == 400

print("\nTODAS LAS PRUEBAS PASARON")

# 8) Registro duplicado (mismo correo)
r = client.post("/api/auth/register", json={
    "nombre_completo": "Otra Ana",
    "nombre_usuario": "otraana",
    "correo": "ana@correo.com",
    "password": "ClaveSegura123",
    "fecha_nacimiento": "1999-01-01",
    "sexo": "femenino",
})
show("REGISTER (correo duplicado)", r)
assert r.status_code == 409

# 9) Registro con sexo inválido
r = client.post("/api/auth/register", json={
    "nombre_completo": "Luis Gomez",
    "nombre_usuario": "luisg",
    "correo": "luis@correo.com",
    "password": "ClaveSegura123",
    "fecha_nacimiento": "1995-01-01",
    "sexo": "no-valido",
})
show("REGISTER (sexo inválido)", r)
assert r.status_code == 400

# 10) Registro sin fecha_nacimiento (antes ni se pedía)
r = client.post("/api/auth/register", json={
    "nombre_completo": "Luis Gomez",
    "nombre_usuario": "luisg",
    "correo": "luis@correo.com",
    "password": "ClaveSegura123",
    "sexo": "masculino",
})
show("REGISTER (sin fecha_nacimiento)", r)
assert r.status_code == 400

print("\nTODAS LAS PRUEBAS ADICIONALES PASARON")
