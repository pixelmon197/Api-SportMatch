import os, sys, sqlite3, io, tempfile

# Rutas relativas a este archivo: funciona sin importar desde dónde se
# ejecute ni en qué máquina, siempre que este script viva en test/ dentro
# del proyecto (Api-SportMatch/test/este_archivo.py).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, PROJECT_DIR)

DB_PATH = os.path.join(BASE_DIR, "test_foto_perfil.sqlite3")
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
def usuario(nombre, correo, nick):
    conn.execute("INSERT INTO usuarios (nombre_completo, correo, contrasena, fecha_nacimiento, sexo, nombre_usuario, rol, estado_cuenta, ciudad_id, registro_completo_en) VALUES (?,?,'x','2000-01-01','femenino',?,'usuario','activa',1,CURRENT_TIMESTAMP)", (nombre, correo, nick))
usuario("Ana Perez", "ana@correo.com", "anaperez")   # 1
usuario("Luis Gomez", "luis@correo.com", "luisg")    # 2
conn.commit(); conn.close()

from app import create_app
from flask_jwt_extended import create_access_token
from PIL import Image

app = create_app()
# Las subidas de la prueba van a una carpeta temporal, no a static/uploads del proyecto.
UPLOADS_TMP = tempfile.mkdtemp(prefix="sportmatch_uploads_")
app.static_folder = UPLOADS_TMP
client = app.test_client()
with app.app_context():
    tok = lambda i: {"Authorization": "Bearer " + create_access_token(identity=str(i), additional_claims={"rol": "usuario"})}
    H_ANA, H_LUIS = tok(1), tok(2)

def show(label, resp):
    print(f"--- {label} [{resp.status_code}] ---")
    print(resp.get_json())

def png(w, h, color="red"):
    buf = io.BytesIO(); Image.new("RGB", (w, h), color).save(buf, "PNG"); return buf.getvalue()

def enviar(metodo, headers, nombre, contenido, campo="foto"):
    data = {campo: (io.BytesIO(contenido), nombre)} if nombre else {}
    return getattr(client, metodo)("/api/perfiles/me/foto", data=data, headers=headers, content_type="multipart/form-data")

# 1) Sin token
r = enviar("post", {}, "a.png", png(10, 10))
show("POST (sin token)", r); assert r.status_code == 401
r = enviar("put", {}, "a.png", png(10, 10))
assert r.status_code == 401

# 2) Subir foto por primera vez
r = enviar("post", H_ANA, "yo.png", png(40, 30))
show("POST FOTO (primera vez)", r)
assert r.status_code == 201, r.get_json()
p = r.get_json()["perfil"]
assert p["avatar_id"] and p["avatar_url"].startswith("/static/uploads/imagen/") and p["avatar_url"].endswith(".png")
assert os.path.exists(os.path.join(UPLOADS_TMP, p["avatar_url"].replace("/static/", "", 1)))
avatar1 = p["avatar_id"]
a = client.get(f"/api/archivos/{avatar1}").get_json()
assert a["tipo"] == "imagen" and a["propietario_id"] == 1 and (a["ancho_px"], a["alto_px"]) == (40, 30)

# 3) Segundo POST -> 409 (hay que usar PUT)
r = enviar("post", H_ANA, "otra.png", png(10, 10))
show("POST FOTO (ya tenia foto)", r); assert r.status_code == 409

# 4) Actualizar con PUT: cambia el avatar y la anterior queda eliminada
r = enviar("put", H_ANA, "nueva.jpg", png(50, 50, "blue"))
show("PUT FOTO (reemplazar)", r)
assert r.status_code == 200, r.get_json()
p2 = r.get_json()["perfil"]
assert p2["avatar_id"] != avatar1 and p2["avatar_url"].endswith(".jpg")
assert client.get(f"/api/archivos/{avatar1}").status_code == 404   # la anterior ya no existe
assert client.get(f"/api/archivos/{p2['avatar_id']}").status_code == 200
assert client.get("/api/perfiles/me", headers=H_ANA).get_json()["perfil"]["avatar_id"] == p2["avatar_id"]
assert client.get("/api/perfiles/1").get_json()["perfil"]["avatar_url"] == p2["avatar_url"]  # visible en el perfil publico

# 5) PUT sin foto previa (Luis) crea la foto
r = enviar("put", H_LUIS, "luis.webp", png(20, 20, "green"))
show("PUT FOTO (sin foto previa)", r); assert r.status_code == 200 and r.get_json()["perfil"]["avatar_id"]
assert r.get_json()["perfil"]["avatar_id"] != p2["avatar_id"]
assert client.get("/api/perfiles/1").get_json()["perfil"]["avatar_id"] == p2["avatar_id"]  # la de Ana no se toca

# 6) Si la foto anterior tambien es la portada, no se elimina
r = client.put("/api/perfiles/me", json={"portada_id": p2["avatar_id"]}, headers=H_ANA)
assert r.status_code == 200
r = enviar("put", H_ANA, "otra.png", png(30, 30, "black"))
assert r.status_code == 200
assert client.get(f"/api/archivos/{p2['avatar_id']}").status_code == 200

# 7) Validaciones
r = enviar("put", H_ANA, None, None)
show("PUT (sin archivo)", r); assert r.status_code == 400
r = enviar("post", H_LUIS, None, None)
assert r.status_code == 409 or r.status_code == 400
r = enviar("put", H_ANA, "virus.exe", b"MZ....")
show("PUT (extension no permitida)", r); assert r.status_code == 400
r = enviar("put", H_ANA, "ruta.gpx", b"<gpx></gpx>")
show("PUT (no es imagen)", r); assert r.status_code == 400
r = enviar("put", H_ANA, "vacia.png", b"")
assert r.status_code == 400
r = enviar("put", H_ANA, "enorme.png", b"0" * (8 * 1024 * 1024 + 1))
show("PUT (mayor a 8 MB)", r); assert r.status_code == 400 and "8 MB" in r.get_json()["error"]
# Los intentos fallidos no cambian la foto actual
assert client.get("/api/perfiles/me", headers=H_ANA).get_json()["perfil"]["avatar_url"].endswith(".png")

# 8) Campo alterno 'archivo'
r = enviar("put", H_ANA, "x.png", png(12, 12), campo="archivo")
assert r.status_code == 200

print("\nTODAS LAS PRUEBAS DE FOTO DE PERFIL PASARON")
