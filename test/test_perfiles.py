import os, sys, sqlite3

# Rutas relativas a este archivo: funciona sin importar desde dónde se
# ejecute ni en qué máquina, siempre que este script viva en test/ dentro
# del proyecto (Api-SportMatch/test/este_archivo.py).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, PROJECT_DIR)

DB_PATH = os.path.join(BASE_DIR, "test_perfiles.sqlite3")
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
    nombre_usuario TEXT UNIQUE, telefono TEXT, ciudad_id INTEGER REFERENCES ciudades(id),
    idioma TEXT DEFAULT 'es', zona_horaria TEXT DEFAULT 'America/Mexico_City',
    codigo_referido TEXT UNIQUE, registro_completo_en TIMESTAMP,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    eliminado_en TIMESTAMP
);
CREATE TABLE archivos (
    id INTEGER PRIMARY KEY AUTOINCREMENT, propietario_id INTEGER REFERENCES usuarios(id),
    tipo VARCHAR(20) NOT NULL, url VARCHAR(500) NOT NULL, nombre_original VARCHAR(200), tipo_mime VARCHAR(100),
    tamano_bytes BIGINT, ancho_px INTEGER, alto_px INTEGER, duracion_segundos INTEGER,
    subido_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, eliminado_en TIMESTAMP,
    CHECK (tipo IN ('imagen','video','documento','gpx','audio'))
);
CREATE TABLE deportes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL UNIQUE, categoria TEXT, activo BOOLEAN NOT NULL DEFAULT 1);
CREATE TABLE usuario_deportes (
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    deporte_id INTEGER NOT NULL REFERENCES deportes(id),
    nivel TEXT, es_principal BOOLEAN NOT NULL DEFAULT 0, PRIMARY KEY (usuario_id, deporte_id)
);
CREATE TABLE perfiles (
    usuario_id INTEGER PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    biografia TEXT,
    avatar_id INTEGER REFERENCES archivos(id), portada_id INTEGER REFERENCES archivos(id),
    visibilidad_perfil VARCHAR(20) NOT NULL DEFAULT 'publico',
    visibilidad_ubicacion VARCHAR(20) NOT NULL DEFAULT 'amigos',
    quien_puede_escribir VARCHAR(20) NOT NULL DEFAULT 'publico',
    aparecer_en_cercanos BOOLEAN NOT NULL DEFAULT 1,
    latitud NUMERIC, longitud NUMERIC, ubicacion_actualizada_en TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (visibilidad_perfil IN ('publico','amigos','privado')),
    CHECK (visibilidad_ubicacion IN ('publico','amigos','privado')),
    CHECK (quien_puede_escribir IN ('publico','amigos','privado'))
);
CREATE TABLE amistades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    amigo_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, respondida_en TIMESTAMP,
    UNIQUE (usuario_id, amigo_id), CHECK (usuario_id <> amigo_id)
);
CREATE TABLE bloqueos (
    bloqueador_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    bloqueado_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (bloqueador_id, bloqueado_id), CHECK (bloqueador_id <> bloqueado_id)
);
"""

conn = sqlite3.connect(DB_PATH)
conn.executescript(DDL)
conn.execute("INSERT INTO ciudades (nombre) VALUES ('Toluca')")
def usuario(nombre, correo, nick, rol="usuario", estado="activa"):
    conn.execute("INSERT INTO usuarios (nombre_completo, correo, contrasena, telefono, fecha_nacimiento, sexo, nombre_usuario, rol, estado_cuenta, ciudad_id, registro_completo_en) VALUES (?,?,'x','5512345678','2000-01-01','femenino',?,?,?,1,CURRENT_TIMESTAMP)", (nombre, correo, nick, rol, estado))
usuario("Ana Perez", "ana@correo.com", "anaperez")        # 1  dueña del perfil
usuario("Luis Gomez", "luis@correo.com", "luisg")         # 2  desconocido
usuario("Marta Diaz", "marta@correo.com", "martad")       # 3  amiga (aceptada, en sentido inverso)
usuario("Pablo Ruiz", "pablo@correo.com", "pabloruiz")    # 4  solicitud pendiente
usuario("Admin Uno", "admin@correo.com", "admin1", "administrador")  # 5
usuario("Sin Perfil", "sinperfil@correo.com", "sinperfil")  # 6  nunca ha tocado su perfil
usuario("Suspendido", "susp@correo.com", "suspendido", estado="suspendida")  # 7
conn.execute("INSERT INTO amistades (usuario_id, amigo_id, estado) VALUES (3, 1, 'aceptada')")   # Marta->Ana (inverso)
conn.execute("INSERT INTO amistades (usuario_id, amigo_id, estado) VALUES (4, 1, 'pendiente')")
conn.execute("INSERT INTO deportes (nombre) VALUES ('Running')")
conn.execute("INSERT INTO usuario_deportes (usuario_id, deporte_id, nivel, es_principal) VALUES (1, 1, 'intermedio', 1)")
conn.execute("INSERT INTO archivos (id, propietario_id, tipo, url) VALUES (1, 1, 'imagen', '/static/uploads/imagen/avatar.png')")
conn.execute("INSERT INTO archivos (id, propietario_id, tipo, url) VALUES (2, 1, 'imagen', '/static/uploads/imagen/portada.png')")
conn.execute("INSERT INTO archivos (id, propietario_id, tipo, url) VALUES (3, 1, 'gpx', '/static/uploads/gpx/ruta.gpx')")
conn.commit(); conn.close()

from app import create_app
from flask_jwt_extended import create_access_token

app = create_app()
client = app.test_client()
with app.app_context():
    tok = lambda i, rol="usuario": {"Authorization": "Bearer " + create_access_token(identity=str(i), additional_claims={"rol": rol})}
    H_ANA, H_LUIS, H_MARTA, H_PABLO = tok(1), tok(2), tok(3), tok(4)
    H_ADMIN, H_SINPERFIL = tok(5, "administrador"), tok(6)

def show(label, resp):
    print(f"--- {label} [{resp.status_code}] ---")
    print(resp.get_json())

# ===== MI PERFIL =====
# 1) Primera vez: se crea con los defaults reales de Neon
r = client.get("/api/perfiles/me", headers=H_ANA)
show("MI PERFIL (primera vez)", r)
assert r.status_code == 200
p = r.get_json()
assert p["correo"] == "ana@correo.com" and p["deportes"][0]["deporte"]["nombre"] == "Running"
assert (p["perfil"]["visibilidad_perfil"], p["perfil"]["visibilidad_ubicacion"],
        p["perfil"]["quien_puede_escribir"], p["perfil"]["aparecer_en_cercanos"]) == ("publico", "amigos", "publico", True)

# 2) Editar: biografia + avatar + portada
r = client.put("/api/perfiles/me", json={"biografia": "Corro los fines de semana", "avatar_id": 1, "portada_id": 2}, headers=H_ANA)
show("EDITAR PERFIL", r)
assert r.status_code == 200
assert r.get_json()["perfil"]["avatar_url"] == "/static/uploads/imagen/avatar.png"
assert r.get_json()["perfil"]["portada_url"] == "/static/uploads/imagen/portada.png"

# 3) Validaciones de la edición
casos = [
    ({"avatar_id": 3}, "avatar es un GPX"),
    ({"portada_id": 999}, "portada inexistente"),
    ({"visibilidad_perfil": "todos"}, "visibilidad invalida"),
    ({"quien_puede_escribir": "nadie"}, "quien_puede_escribir invalido"),
    ({"aparecer_en_cercanos": "si"}, "bool invalido"),
    ({"biografia": "x" * 501}, "biografia muy larga"),
    ({"biografia": 123}, "biografia no es texto"),
]
for body, nombre in casos:
    r = client.put("/api/perfiles/me", json=body, headers=H_ANA)
    assert r.status_code == 400, (nombre, r.get_json())
print("--- validaciones de edicion OK ---")

# 4) Borrar avatar con null; body vacio no cambia nada
r = client.put("/api/perfiles/me", json={"avatar_id": None}, headers=H_ANA)
assert r.status_code == 200 and r.get_json()["perfil"]["avatar_url"] is None
r = client.put("/api/perfiles/me", json={}, headers=H_ANA)
assert r.status_code == 200 and r.get_json()["perfil"]["biografia"] == "Corro los fines de semana"

# 5) Sin token
assert client.get("/api/perfiles/me").status_code == 401
assert client.put("/api/perfiles/me", json={}).status_code == 401

# ===== UBICACION =====
r = client.put("/api/perfiles/me/ubicacion", json={"latitud": 19.2826, "longitud": -99.6557}, headers=H_ANA)
show("GUARDAR UBICACION", r)
assert r.status_code == 200
assert r.get_json()["perfil"]["latitud"] == 19.2826 and r.get_json()["perfil"]["ubicacion_actualizada_en"]
for body in ({}, {"latitud": 19}, {"latitud": "x", "longitud": 1}, {"latitud": 91, "longitud": 0},
             {"latitud": 0, "longitud": 181}, {"latitud": True, "longitud": 0}):
    assert client.put("/api/perfiles/me/ubicacion", json=body, headers=H_ANA).status_code == 400, body
print("--- validaciones de ubicacion OK ---")

# ===== VER PERFIL DE OTROS =====
# 6) Anonimo ve un perfil publico, SIN datos privados, y la ubicacion oculta (default 'amigos')
r = client.get("/api/perfiles/1")
show("VER PERFIL (anonimo, publico)", r)
v = r.get_json()
assert r.status_code == 200 and v["nombre_usuario"] == "anaperez"
for privado in ("correo", "telefono", "fecha_de_nacimiento", "rol", "sexo"):
    assert privado not in v, privado
assert "latitud" not in v["perfil"] and "visibilidad_perfil" not in v["perfil"]
assert v["perfil"]["biografia"] == "Corro los fines de semana" and v["deportes"][0]["nivel"] == "intermedio"

# 7) Un amigo (amistad aceptada en sentido inverso) si ve la ubicacion; el desconocido y el pendiente no
r = client.get("/api/perfiles/1", headers=H_MARTA)
assert r.status_code == 200 and r.get_json()["perfil"]["latitud"] == 19.2826
r = client.get("/api/perfiles/1", headers=H_LUIS)
assert r.status_code == 200 and "latitud" not in r.get_json()["perfil"]
r = client.get("/api/perfiles/1", headers=H_PABLO)
assert r.status_code == 200 and "latitud" not in r.get_json()["perfil"]  # solicitud pendiente != amigo
print("--- ubicacion segun amistad OK ---")

# 8) Ubicacion publica la ve cualquiera; privada no la ve nadie (salvo dueña/admin)
client.put("/api/perfiles/me", json={"visibilidad_ubicacion": "publico"}, headers=H_ANA)
assert client.get("/api/perfiles/1").get_json()["perfil"]["longitud"] == -99.6557
client.put("/api/perfiles/me", json={"visibilidad_ubicacion": "privado"}, headers=H_ANA)
assert "latitud" not in client.get("/api/perfiles/1", headers=H_MARTA).get_json()["perfil"]
assert client.get("/api/perfiles/1", headers=H_ADMIN).get_json()["perfil"]["latitud"] == 19.2826

# 9) Perfil solo para amigos
client.put("/api/perfiles/me", json={"visibilidad_perfil": "amigos"}, headers=H_ANA)
assert client.get("/api/perfiles/1").status_code == 403
assert client.get("/api/perfiles/1", headers=H_LUIS).status_code == 403
assert client.get("/api/perfiles/1", headers=H_PABLO).status_code == 403
assert client.get("/api/perfiles/1", headers=H_MARTA).status_code == 200
print("--- perfil 'amigos' OK ---")

# 10) Perfil privado: solo la dueña y el admin
client.put("/api/perfiles/me", json={"visibilidad_perfil": "privado"}, headers=H_ANA)
r = client.get("/api/perfiles/1", headers=H_MARTA)
show("VER PERFIL (privado, hasta una amiga)", r); assert r.status_code == 403
assert client.get("/api/perfiles/1").status_code == 403
assert client.get("/api/perfiles/1", headers=H_ANA).status_code == 200
assert client.get("/api/perfiles/1", headers=H_ADMIN).status_code == 200

# 11) Bloqueos: se oculta incluso que el perfil existe (404), en ambos sentidos
client.put("/api/perfiles/me", json={"visibilidad_perfil": "publico"}, headers=H_ANA)
conn = sqlite3.connect(DB_PATH)
conn.execute("INSERT INTO bloqueos (bloqueador_id, bloqueado_id) VALUES (1, 2)")  # Ana bloqueo a Luis
conn.execute("INSERT INTO bloqueos (bloqueador_id, bloqueado_id) VALUES (4, 1)")  # Pablo bloqueo a Ana
conn.commit(); conn.close()
assert client.get("/api/perfiles/1", headers=H_LUIS).status_code == 404
r = client.get("/api/perfiles/1", headers=H_PABLO)
show("VER PERFIL (el consultante bloqueo a la dueña)", r); assert r.status_code == 404
assert client.get("/api/perfiles/4", headers=H_ANA).status_code == 404       # y al reves
assert client.get("/api/perfiles/1", headers=H_MARTA).status_code == 200     # los demas no se ven afectados
print("--- bloqueos OK ---")

# 12) Por nombre de usuario (sin importar mayusculas) y casos 404
r = client.get("/api/perfiles/usuario/AnaPerez")
show("VER POR NOMBRE DE USUARIO", r); assert r.status_code == 200 and r.get_json()["id"] == 1
assert client.get("/api/perfiles/usuario/noexiste").status_code == 404
assert client.get("/api/perfiles/9999").status_code == 404

# 13) Usuario que nunca tocó su perfil: se ve con los defaults, sin escribir en la base
conn = sqlite3.connect(DB_PATH); antes = conn.execute("SELECT COUNT(*) FROM perfiles").fetchone()[0]; conn.close()
r = client.get("/api/perfiles/6", headers=H_LUIS)
show("VER PERFIL (sin fila en perfiles)", r)
assert r.status_code == 200 and r.get_json()["nombre_usuario"] == "sinperfil"
conn = sqlite3.connect(DB_PATH); despues = conn.execute("SELECT COUNT(*) FROM perfiles").fetchone()[0]; conn.close()
assert antes == despues, "un GET no debe crear filas"
r = client.get("/api/perfiles/me", headers=H_SINPERFIL)   # su propio GET si crea la fila
assert r.status_code == 200
conn = sqlite3.connect(DB_PATH); assert conn.execute("SELECT COUNT(*) FROM perfiles").fetchone()[0] == antes + 1; conn.close()

# 14) Cuenta suspendida: para los demas es como si no existiera; el admin si la ve
assert client.get("/api/perfiles/7", headers=H_LUIS).status_code == 404
assert client.get("/api/perfiles/7", headers=H_ADMIN).status_code == 200

# 15) Borrar ubicacion
r = client.delete("/api/perfiles/me/ubicacion", headers=H_ANA)
show("BORRAR UBICACION", r)
assert r.status_code == 200 and r.get_json()["perfil"]["latitud"] is None and r.get_json()["perfil"]["ubicacion_actualizada_en"] is None

print("\nTODAS LAS PRUEBAS DE PERFILES PASARON")
