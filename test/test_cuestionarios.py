import os, sys, sqlite3

sys.path.insert(0, "/home/claude/work/api_sportmatch/Api-SportMatch")

DB_PATH = "/home/claude/work/test_cuestionarios.sqlite3"
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
    id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL UNIQUE,
    categoria TEXT, activo BOOLEAN NOT NULL DEFAULT 1
);
CREATE TABLE cuestionarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE, titulo TEXT NOT NULL, descripcion TEXT,
    activo BOOLEAN NOT NULL DEFAULT 1,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE preguntas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cuestionario_id INTEGER NOT NULL REFERENCES cuestionarios(id) ON DELETE CASCADE,
    codigo TEXT NOT NULL, texto TEXT NOT NULL, tipo TEXT NOT NULL,
    obligatoria BOOLEAN NOT NULL DEFAULT 1, orden INTEGER NOT NULL,
    activa BOOLEAN NOT NULL DEFAULT 1,
    UNIQUE (cuestionario_id, codigo),
    CHECK (tipo IN ('opcion_unica','opcion_multiple','escala','texto','numero','si_no'))
);
CREATE TABLE opciones_respuesta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pregunta_id INTEGER NOT NULL REFERENCES preguntas(id) ON DELETE CASCADE,
    deporte_id INTEGER REFERENCES deportes(id),
    codigo TEXT NOT NULL, texto TEXT NOT NULL, orden INTEGER NOT NULL,
    UNIQUE (id, pregunta_id),
    UNIQUE (pregunta_id, codigo)
);
CREATE TABLE respuestas_usuario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    pregunta_id INTEGER NOT NULL REFERENCES preguntas(id),
    opcion_id INTEGER, respuesta_texto TEXT,
    respondida_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (usuario_id, pregunta_id, opcion_id),
    FOREIGN KEY (opcion_id, pregunta_id) REFERENCES opciones_respuesta(id, pregunta_id),
    CHECK (opcion_id IS NOT NULL OR respuesta_texto IS NOT NULL)
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

# 1) Crear cuestionario
r = client.post("/api/cuestionarios", json={"codigo": "registro", "titulo": "Cuestionario de registro"}, headers=H_ADMIN)
show("CREAR CUESTIONARIO", r)
assert r.status_code == 201
cuestionario_id = r.get_json()["id"]

# 2) Crear pregunta de opcion_unica con opciones embebidas (usa 'codigo', no 'codigo_id')
r = client.post(f"/api/cuestionarios/{cuestionario_id}/preguntas", json={
    "codigo": "deporte_favorito", "texto": "¿Cuál es tu deporte favorito?", "tipo": "opcion_unica",
    "opciones": [
        {"codigo": "running", "texto": "Running", "orden": 1},
        {"codigo": "ciclismo", "texto": "Ciclismo", "orden": 2},
    ],
}, headers=H_ADMIN)
show("CREAR PREGUNTA (opcion_unica, con opciones)", r)
assert r.status_code == 201, r.get_json()
pregunta_unica = r.get_json()
pregunta_unica_id = pregunta_unica["id"]
opcion_running_id = pregunta_unica["opciones"][0]["id"]
opcion_ciclismo_id = pregunta_unica["opciones"][1]["id"]
assert pregunta_unica["opciones"][0]["codigo"] == "running"

# 3) Pregunta con tipo viejo 'texto_libre' ya no es valido; 'numero'/'si_no' si
r = client.post(f"/api/cuestionarios/{cuestionario_id}/preguntas", json={
    "codigo": "comentario", "texto": "Comentarios", "tipo": "texto_libre"}, headers=H_ADMIN)
show("CREAR PREGUNTA (tipo viejo invalido)", r)
assert r.status_code == 400

r = client.post(f"/api/cuestionarios/{cuestionario_id}/preguntas", json={
    "codigo": "edad_aprox", "texto": "¿Edad aproximada?", "tipo": "numero"}, headers=H_ADMIN)
show("CREAR PREGUNTA (tipo 'numero', nuevo valido)", r)
assert r.status_code == 201
pregunta_numero_id = r.get_json()["id"]

# 4) Pregunta opcion_multiple con opciones
r = client.post(f"/api/cuestionarios/{cuestionario_id}/preguntas", json={
    "codigo": "dias_semana", "texto": "¿Qué días entrenas?", "tipo": "opcion_multiple",
    "opciones": [
        {"codigo": "lunes", "texto": "Lunes", "orden": 1},
        {"codigo": "miercoles", "texto": "Miércoles", "orden": 2},
        {"codigo": "viernes", "texto": "Viernes", "orden": 3},
    ],
}, headers=H_ADMIN)
show("CREAR PREGUNTA (opcion_multiple)", r)
assert r.status_code == 201
pregunta_multi = r.get_json()
pregunta_multi_id = pregunta_multi["id"]
op_lunes_id = pregunta_multi["opciones"][0]["id"]
op_miercoles_id = pregunta_multi["opciones"][1]["id"]
op_viernes_id = pregunta_multi["opciones"][2]["id"]

# 5) codigo de opcion repetido dentro de la misma pregunta -> 400
r = client.post(f"/api/cuestionarios/{cuestionario_id}/preguntas", json={
    "codigo": "otra", "texto": "Otra pregunta", "tipo": "si_no",
    "opciones": [{"codigo": "si", "texto": "Sí"}, {"codigo": "si", "texto": "Si (dup)"}],
}, headers=H_ADMIN)
show("CREAR PREGUNTA (codigo de opcion repetido)", r)
assert r.status_code == 400

# 6) codigo de pregunta repetido en el mismo cuestionario -> 409
r = client.post(f"/api/cuestionarios/{cuestionario_id}/preguntas", json={
    "codigo": "deporte_favorito", "texto": "Duplicada", "tipo": "texto"}, headers=H_ADMIN)
show("CREAR PREGUNTA (codigo repetido en cuestionario)", r)
assert r.status_code == 409

# 7) Responder: opcion_id que no pertenece a la pregunta -> 400 (antes: 500 por FK)
r = client.post(f"/api/cuestionarios/registro/responder", json={
    "respuestas": [{"pregunta_id": pregunta_unica_id, "opcion_id": op_lunes_id}]}, headers=H_ANA)
show("RESPONDER (opcion de otra pregunta, invalido)", r)
assert r.status_code == 400

# 8) Responder: ni opcion_id ni respuesta_texto -> 400 (antes: violaba CHECK real)
r = client.post(f"/api/cuestionarios/registro/responder", json={
    "respuestas": [{"pregunta_id": pregunta_numero_id}]}, headers=H_ANA)
show("RESPONDER (sin opcion_id ni respuesta_texto)", r)
assert r.status_code == 400

# 9) Responder correctamente: opcion_unica + numero + multiple (2 opciones)
r = client.post(f"/api/cuestionarios/registro/responder", json={
    "respuestas": [
        {"pregunta_id": pregunta_unica_id, "opcion_id": opcion_running_id},
        {"pregunta_id": pregunta_numero_id, "respuesta_texto": "28"},
        {"pregunta_id": pregunta_multi_id, "opcion_id": op_lunes_id},
        {"pregunta_id": pregunta_multi_id, "opcion_id": op_miercoles_id},
    ]}, headers=H_ANA)
show("RESPONDER (correcto, incluye multiple)", r)
assert r.status_code == 201, r.get_json()
assert len(r.get_json()) == 4

# 10) Verificar que las 2 respuestas de opcion_multiple se guardaron ambas (no se pisaron)
r = client.get("/api/cuestionarios/me/respuestas", headers=H_ANA)
show("MIS RESPUESTAS", r)
respuestas_multi = [x for x in r.get_json() if x["pregunta_id"] == pregunta_multi_id]
assert len(respuestas_multi) == 2, respuestas_multi

# 11) Responder pregunta unica dos veces con opciones distintas -> 400 (no acepta multiples)
r = client.post(f"/api/cuestionarios/registro/responder", json={
    "respuestas": [
        {"pregunta_id": pregunta_unica_id, "opcion_id": opcion_running_id},
        {"pregunta_id": pregunta_unica_id, "opcion_id": opcion_ciclismo_id},
    ]}, headers=H_ANA)
show("RESPONDER (opcion_unica con 2 respuestas, invalido)", r)
assert r.status_code == 400

# 12) Re-responder la opcion_multiple con un subconjunto distinto -> reemplaza limpio
r = client.post(f"/api/cuestionarios/registro/responder", json={
    "respuestas": [{"pregunta_id": pregunta_multi_id, "opcion_id": op_viernes_id}]}, headers=H_ANA)
show("RE-RESPONDER (multiple, reemplazo)", r)
assert r.status_code == 201
r = client.get("/api/cuestionarios/me/respuestas", headers=H_ANA)
respuestas_multi = [x for x in r.get_json() if x["pregunta_id"] == pregunta_multi_id]
assert len(respuestas_multi) == 1 and respuestas_multi[0]["opcion"]["codigo"] == "viernes"

print("\nTODAS LAS PRUEBAS DE CUESTIONARIOS PASARON")
