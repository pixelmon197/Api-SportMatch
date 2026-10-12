import os, sys, sqlite3, io, tempfile

# Rutas relativas a este archivo: funciona sin importar desde dónde se
# ejecute ni en qué máquina, siempre que este script viva en test/ dentro
# del proyecto (Api-SportMatch/test/este_archivo.py).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, PROJECT_DIR)

DB_PATH = os.path.join(BASE_DIR, "test_archivos.sqlite3")
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
CREATE TABLE archivos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    propietario_id INTEGER REFERENCES usuarios(id),
    tipo VARCHAR(20) NOT NULL, url VARCHAR(500) NOT NULL,
    nombre_original VARCHAR(200), tipo_mime VARCHAR(100),
    tamano_bytes BIGINT, ancho_px INTEGER, alto_px INTEGER, duracion_segundos INTEGER,
    subido_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, eliminado_en TIMESTAMP,
    CHECK (tipo IN ('imagen','video','documento','gpx','audio'))
);
CREATE TABLE organizadores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL UNIQUE REFERENCES usuarios(id),
    nombre_comercial TEXT NOT NULL, descripcion TEXT, correo_contacto TEXT,
    telefono_contacto TEXT, ciudad_id INTEGER,
    logo_id INTEGER REFERENCES archivos(id),
    estado_validacion TEXT NOT NULL DEFAULT 'sin_solicitud', validado_en TIMESTAMP,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    eliminado_en TIMESTAMP
);
CREATE TABLE organizador_miembros (
    organizador_id INTEGER NOT NULL REFERENCES organizadores(id) ON DELETE CASCADE,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    rol TEXT NOT NULL DEFAULT 'colaborador',
    agregado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (organizador_id, usuario_id)
);
CREATE TABLE deportes (
    id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL UNIQUE,
    categoria TEXT, activo BOOLEAN NOT NULL DEFAULT 1
);
CREATE TABLE eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organizador_id INTEGER NOT NULL REFERENCES organizadores(id),
    tipo TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'borrador',
    dificultad TEXT, titulo TEXT NOT NULL, slug TEXT NOT NULL UNIQUE,
    descripcion TEXT, portada_id INTEGER REFERENCES archivos(id), edad_minima INTEGER,
    es_publico BOOLEAN NOT NULL DEFAULT 1, publicado_en TIMESTAMP,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    eliminado_en TIMESTAMP
);
CREATE TABLE evento_deportes (evento_id INTEGER NOT NULL, deporte_id INTEGER NOT NULL, PRIMARY KEY (evento_id, deporte_id));
CREATE TABLE evento_requisitos (id INTEGER PRIMARY KEY AUTOINCREMENT, evento_id INTEGER NOT NULL, descripcion TEXT NOT NULL, orden INTEGER NOT NULL DEFAULT 0);
CREATE TABLE evento_sedes (id INTEGER PRIMARY KEY AUTOINCREMENT, evento_id INTEGER NOT NULL, tipo TEXT NOT NULL, nombre TEXT NOT NULL, direccion TEXT, ciudad_id INTEGER, latitud NUMERIC, longitud NUMERIC);
CREATE TABLE evento_fechas (id INTEGER PRIMARY KEY AUTOINCREMENT, evento_id INTEGER NOT NULL, inicia_en TIMESTAMP NOT NULL, termina_en TIMESTAMP, cancelada_en TIMESTAMP);
CREATE TABLE evento_categorias (id INTEGER PRIMARY KEY AUTOINCREMENT, evento_id INTEGER NOT NULL, nombre TEXT NOT NULL, distancia_km NUMERIC, edad_minima INTEGER, edad_maxima INTEGER, cupo_total INTEGER, permite_lista_espera BOOLEAN NOT NULL DEFAULT 0);
CREATE TABLE evento_boletos (id INTEGER PRIMARY KEY AUTOINCREMENT, categoria_id INTEGER NOT NULL, tipo TEXT NOT NULL, precio NUMERIC NOT NULL, moneda TEXT NOT NULL DEFAULT 'MXN', disponible_desde TIMESTAMP, disponible_hasta TIMESTAMP, cantidad_maxima INTEGER, activo BOOLEAN NOT NULL DEFAULT 1);
CREATE TABLE rutas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    creador_id INTEGER REFERENCES usuarios(id), deporte_id INTEGER REFERENCES deportes(id),
    gpx_archivo_id INTEGER REFERENCES archivos(id),
    dificultad TEXT, nombre TEXT NOT NULL, descripcion TEXT,
    distancia_m INTEGER, desnivel_positivo_m INTEGER,
    es_publica BOOLEAN NOT NULL DEFAULT 1,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, eliminado_en TIMESTAMP
);
CREATE TABLE ruta_puntos (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ruta_id INTEGER NOT NULL, tipo TEXT NOT NULL,
    orden INTEGER NOT NULL, nombre TEXT, latitud NUMERIC NOT NULL, longitud NUMERIC NOT NULL, altitud_m NUMERIC
);
"""

conn = sqlite3.connect(DB_PATH)
conn.executescript(DDL)
def usuario(nombre, correo, nick, rol="usuario"):
    conn.execute("INSERT INTO usuarios (nombre_completo, correo, contrasena, fecha_nacimiento, sexo, nombre_usuario, rol, estado_cuenta, registro_completo_en) VALUES (?,?,'x','2000-01-01','femenino',?,?,'activa',CURRENT_TIMESTAMP)", (nombre, correo, nick, rol))
usuario("Ana Perez", "ana@correo.com", "anaperez")
usuario("Luis Gomez", "luis@correo.com", "luisg")
usuario("Admin Uno", "admin@correo.com", "admin1", "administrador")
conn.execute("INSERT INTO organizadores (usuario_id, nombre_comercial, estado_validacion) VALUES (1,'Carreras del Valle','aprobada')")
conn.execute("INSERT INTO organizador_miembros (organizador_id, usuario_id, rol) VALUES (1,1,'propietario')")
conn.execute("INSERT INTO deportes (nombre) VALUES ('Running')")
conn.commit(); conn.close()

from app import create_app
from flask_jwt_extended import create_access_token

app = create_app()
# Las subidas de la prueba van a una carpeta temporal, no a static/uploads del proyecto.
UPLOADS_TMP = tempfile.mkdtemp(prefix="sportmatch_uploads_")
app.static_folder = UPLOADS_TMP
client = app.test_client()
with app.app_context():
    tok = lambda i, rol: {"Authorization": "Bearer " + create_access_token(identity=str(i), additional_claims={"rol": rol})}
    H_ANA, H_LUIS, H_ADMIN = tok(1, "usuario"), tok(2, "usuario"), tok(3, "administrador")

def show(label, resp):
    print(f"--- {label} [{resp.status_code}] ---")
    print(resp.get_json())

def subir(headers, nombre, contenido, **form):
    data = {"archivo": (io.BytesIO(contenido), nombre), **form}
    return client.post("/api/archivos", data=data, headers=headers, content_type="multipart/form-data")

from PIL import Image
buf = io.BytesIO(); Image.new("RGB", (40, 30), "red").save(buf, "PNG"); PNG = buf.getvalue()

# 1) Imagen: el tipo se adivina por la extension y se leen ancho/alto
r = subir(H_ANA, "portada.png", PNG)
show("SUBIR IMAGEN", r)
assert r.status_code == 201, r.get_json()
img = r.get_json()
assert img["tipo"] == "imagen" and img["ancho_px"] == 40 and img["alto_px"] == 30
assert img["propietario_id"] == 1 and img["tamano_bytes"] == len(PNG)
assert img["url"].startswith("/static/uploads/imagen/") and img["url"].endswith(".png")
assert os.path.exists(os.path.join(UPLOADS_TMP, img["url"].replace("/static/", "", 1)))

# 2) Video (con duracion opcional), GPX y PDF
r = subir(H_ANA, "carrera.mp4", b"\x00\x00\x00\x18ftypmp42" + b"0" * 2000, duracion_segundos="95")
show("SUBIR VIDEO", r)
assert r.status_code == 201 and r.get_json()["tipo"] == "video" and r.get_json()["duracion_segundos"] == 95
video = r.get_json()

r = subir(H_ANA, "ruta.gpx", b"<?xml version='1.0'?><gpx version='1.1'></gpx>")
show("SUBIR GPX", r); assert r.status_code == 201 and r.get_json()["tipo"] == "gpx"
gpx = r.get_json()

r = subir(H_ANA, "ine.pdf", b"%PDF-1.4 fake")
show("SUBIR PDF", r); assert r.status_code == 201 and r.get_json()["tipo"] == "documento"

# 3) Validaciones de la subida
r = client.post("/api/archivos", data={"archivo": (io.BytesIO(PNG), "x.png")}, content_type="multipart/form-data")
show("SUBIR (sin token)", r); assert r.status_code == 401

r = client.post("/api/archivos", data={}, headers=H_ANA, content_type="multipart/form-data")
show("SUBIR (sin archivo)", r); assert r.status_code == 400

r = subir(H_ANA, "vacio.png", b"")
show("SUBIR (archivo vacio)", r); assert r.status_code == 400

r = subir(H_ANA, "virus.exe", b"MZ....")
show("SUBIR (extension no permitida)", r); assert r.status_code == 400

r = subir(H_ANA, "foto.jpg", PNG, tipo="video")
show("SUBIR (tipo video con extension .jpg)", r); assert r.status_code == 400

r = subir(H_ANA, "foto.png", PNG, tipo="holograma")
show("SUBIR (tipo invalido)", r); assert r.status_code == 400

r = subir(H_ANA, "enorme.png", b"0" * (8 * 1024 * 1024 + 1))
show("SUBIR (imagen mayor a 8 MB)", r); assert r.status_code == 400 and "8 MB" in r.get_json()["error"]

# 4) Consultar y eliminar
r = client.get(f"/api/archivos/{img['id']}")
show("VER ARCHIVO (publico)", r); assert r.status_code == 200 and r.get_json()["id"] == img["id"]
assert client.get("/api/archivos/9999").status_code == 404

r = client.delete(f"/api/archivos/{video['id']}", headers=H_LUIS)
show("ELIMINAR (de otro usuario)", r); assert r.status_code == 403
r = client.delete(f"/api/archivos/{video['id']}", headers=H_ANA)
assert r.status_code == 204
assert client.get(f"/api/archivos/{video['id']}").status_code == 404
r = subir(H_LUIS, "otra.png", PNG); otra = r.get_json()
assert client.delete(f"/api/archivos/{otra['id']}", headers=H_ADMIN).status_code == 204  # admin si puede

# 5) Evento con portada
base_evento = {"titulo": "5K Nocturna", "tipo": "carrera", "organizador_id": 1}
r = client.post("/api/eventos", json={**base_evento, "portada_id": img["id"]}, headers=H_ANA)
show("CREAR EVENTO (con portada)", r)
assert r.status_code == 201, r.get_json()
assert r.get_json()["portada_id"] == img["id"] and r.get_json()["portada_url"] == img["url"]
evento_id = r.get_json()["id"]

r = client.post("/api/eventos", json={**base_evento, "titulo": "B", "portada_id": gpx["id"]}, headers=H_ANA)
show("CREAR EVENTO (portada es un GPX)", r); assert r.status_code == 400 and "imagen" in r.get_json()["error"]
r = client.post("/api/eventos", json={**base_evento, "titulo": "C", "portada_id": 9999}, headers=H_ANA)
show("CREAR EVENTO (portada inexistente)", r); assert r.status_code == 400
r = client.post("/api/eventos", json={**base_evento, "titulo": "D", "portada_id": video["id"]}, headers=H_ANA)
show("CREAR EVENTO (portada eliminada)", r); assert r.status_code == 400

r = subir(H_ANA, "nueva.jpg", PNG); nueva = r.get_json()
r = client.put(f"/api/eventos/{evento_id}", json={"portada_id": nueva["id"]}, headers=H_ANA)
show("CAMBIAR PORTADA", r); assert r.status_code == 200 and r.get_json()["portada_url"] == nueva["url"]

# 6) Logo de organizador
r = client.put("/api/organizadores/1", json={"logo_id": img["id"]}, headers=H_ANA)
show("LOGO DE ORGANIZADOR", r); assert r.status_code == 200 and r.get_json()["logo_url"] == img["url"]
r = client.put("/api/organizadores/1", json={"logo_id": gpx["id"]}, headers=H_ANA)
show("LOGO (es un GPX)", r); assert r.status_code == 400

# 7) GPX de ruta
r = client.post("/api/rutas", json={"nombre": "Sendero", "deporte_id": 1, "gpx_archivo_id": gpx["id"]}, headers=H_ANA)
show("CREAR RUTA (con GPX)", r)
assert r.status_code == 201 and r.get_json()["gpx_url"] == gpx["url"]
r = client.post("/api/rutas", json={"nombre": "Otra", "deporte_id": 1, "gpx_archivo_id": img["id"]}, headers=H_ANA)
show("CREAR RUTA (GPX es una imagen)", r); assert r.status_code == 400

print("\nTODAS LAS PRUEBAS DE ARCHIVOS PASARON")
