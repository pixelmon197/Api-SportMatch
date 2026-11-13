# Pasos de despliegue

Pasos para llevar Api-SportMatch a un servidor, ajustados a lo que el
proyecto tiene hoy. Todavía no hay un despliegue hecho (ver
`docs/despliegue_ambientes.md`), así que varios pasos están pendientes de
una decisión: proveedor, Docker y migraciones.

**Estados:** ✅ Listo para usarse · ⚠️ Parcial · ❌ Pendiente

## Resumen

| # | Paso | Cómo se hace en este proyecto | Estado |
|---|---|---|---|
| 1 | Compilar o empaquetar | Python no se compila: basta instalar dependencias con `pip install -r requirements.txt`. | ✅ Listo |
| 2 | Construir la imagen de Docker | No hay `Dockerfile` en el repositorio. Es opcional: muchos proveedores despliegan directo desde `requirements.txt`. | ❌ Pendiente |
| 3 | Publicar en el servidor o servicio de hosting | No hay proveedor elegido. El servidor de producción (`gunicorn`) ya está en `requirements.txt`. | ❌ Pendiente |
| 4 | Ejecutar migraciones | No hay herramienta de migraciones. Las tablas se crean solas con `db.create_all()` al arrancar; los datos iniciales, con `python seed.py`. | ⚠️ Parcial |
| 5 | Verificar `/health` | La ruta real es `GET /api/health` y responde `{"status": "ok", "proyecto": "SportMatch"}`. | ✅ Listo |

## Detalle de cada paso

### 1. Compilar o empaquetar

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

No se genera ningún artefacto: lo que se despliega es el código fuente más
sus dependencias. `gunicorn` solo funciona en Linux/Mac, que es lo que usan
los servidores; en Windows se sigue usando `python app.py` para desarrollo.

### 2. Construir la imagen de Docker (opcional, pendiente)

Solo hace falta si el proveedor elegido lo pide. Un `Dockerfile` de partida
(propuesta, todavía no existe ni se ha probado):

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:create_app()"]
```

```bash
docker build -t api-sportmatch .
docker run --env-file .env -p 8000:8000 api-sportmatch
```

Si se crea, agregar un `.dockerignore` con `venv/`, `.env`, `__pycache__/`
y `.git/` para que ni el entorno virtual ni los secretos entren a la imagen.

### 3. Publicar en el servidor o servicio de hosting (pendiente)

Sea cual sea el proveedor, se necesitan estos tres datos:

| Dato | Valor |
|---|---|
| Comando de instalación | `pip install -r requirements.txt` |
| Comando de arranque | `gunicorn "app:create_app()"` (nunca `python app.py`, que arranca en modo debug) |
| Variables de entorno | `SECRET_KEY`, `JWT_SECRET_KEY` y `DATABASE_URL`, configuradas en el panel del proveedor |

Las claves deben ser valores aleatorios nuevos, no los de `.env.example`:
si faltan, `config.py` usa un valor por defecto conocido.

### 4. Ejecutar migraciones (parcial)

Hoy no hay nada que ejecutar a mano en el primer despliegue:

- `db.create_all()` corre en cada arranque (`app.py`) y crea las tablas que
  falten en la base indicada por `DATABASE_URL`.
- `python seed.py` crea la ciudad demo y el usuario `admin@sportmatch.com`.
  Se puede repetir sin duplicar datos. La contraseña inicial es pública
  (está en el repositorio): hay que cambiarla en cuanto se inicie sesión.

La limitación es que `db.create_all()` **no modifica tablas que ya
existen**. Si un modelo cambia (columna nueva, tipo distinto), la base de
producción no se entera y el cambio hay que hacerlo a mano en Neon. Antes
de tener datos reales conviene adoptar `Flask-Migrate` (`flask db upgrade`).

### 5. Verificar `/health`

```bash
curl https://<dominio>/api/health
```

Respuesta esperada (código 200):

```json
{"status": "ok", "proyecto": "SportMatch"}
```

Esta ruta no consulta la base de datos, así que solo confirma que la API
arrancó. Para comprobar también la conexión a Neon y el JWT, iniciar sesión:

```bash
curl -X POST https://<dominio>/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"correo": "admin@sportmatch.com", "password": "<contraseña>"}'
```

Y abrir Swagger UI en `https://<dominio>/api/docs`.
