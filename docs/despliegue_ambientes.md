# Despliegue y ambientes

Estado real de los ambientes de Api-SportMatch, revisado contra el
repositorio (`app.py`, `config.py`, `.env.example`, `requirements.txt`,
`test/` y las ramas de git). Hoy solo existe el ambiente de desarrollo;
pruebas y producción todavía no están desplegados.

**Estados:** ✅ Disponible · ⚠️ Parcial · ❌ Pendiente

## Ambientes

| Ambiente | URL | Rama | Base de datos | Estado | Notas |
|---|---|---|---|---|---|
| Desarrollo | `http://localhost:5000` | `main` | PostgreSQL en Neon (la `DATABASE_URL` de tu `.env`) | ✅ Disponible | Se arranca con `python app.py` (modo debug). Swagger UI en `/api/docs`. |
| Pruebas | `http://localhost:5000` (contenedor) | Rama de trabajo del integrante | SQLite temporal, o el servicio `db-pruebas` del compose | ⚠️ Parcial | Sin servidor de pruebas dedicado: se valida con `docker compose --profile pruebas up -d` y con GitHub Actions en cada push. |
| Producción | Servicio de la API en Render | `main` | PostgreSQL en Neon | ✅ Disponible | Arranca con `gunicorn "app:create_app()"`. Falta dominio personalizado y una base de Neon separada de la de desarrollo. |

> El repositorio tiene las ramas `main`, `production`, `dev` y las ramas de
> trabajo por integrante (`dev-Michel`, `devOmar`). Las versiones
> (`Update vX.Y.Z`) se integran en `main`.

## Variables de entorno por ambiente

| Variable | Desarrollo | Producción |
|---|---|---|
| `SECRET_KEY` | Cualquier valor en `.env` | Valor aleatorio largo, distinto al de desarrollo |
| `JWT_SECRET_KEY` | Cualquier valor en `.env` | Valor aleatorio largo, distinto al de desarrollo |
| `DATABASE_URL` | Base de Neon de desarrollo (`?sslmode=require`) | Base de Neon de producción (`?sslmode=require`) |

Las tres se leen en `config.py`. El archivo `.env` está en `.gitignore`;
en producción se configuran en el panel del proveedor, no con un `.env`
subido al repositorio.

## Cómo se ejecuta en cada ambiente

| Ambiente | Comando | Notas |
|---|---|---|
| Desarrollo | `python app.py` | Puerto 5000, `debug=True`, recarga automática. |
| Desarrollo (contenedor) | `docker compose up -d --build` | Misma imagen que producción, Gunicorn en el puerto 5000. Ver `docs/docker.md`. |
| Desarrollo (datos iniciales) | `python seed.py` | Crea una ciudad demo y `admin@sportmatch.com`; cambiar esa contraseña al entrar. |
| Producción | `gunicorn "app:create_app()"` | Nunca `python app.py`: arranca en modo debug. En Windows `gunicorn` no funciona; se usa solo en el servidor (Linux). |

## Pendientes antes de desplegar

| Pendiente | Detalle |
|---|---|
| Dominio propio | Ya hay `Dockerfile` y `docker-compose.yml` (ver `docs/docker.md`), pero los servicios se acceden con las direcciones que asignan Render y EC2: falta un dominio personalizado. |
| Base de datos de producción | Crear una base (o rama de Neon) separada; hoy solo hay una `DATABASE_URL`. |
| Migraciones | Las tablas se crean con `db.create_all()` al arrancar, que no aplica cambios a tablas existentes. Conviene `Flask-Migrate` antes de tener datos reales. |
| Configuración por ambiente | `config.py` tiene una sola clase `Config`; falta separar desarrollo/producción (debug, CORS, claves obligatorias). |
| URL del servidor en Swagger | `static/openapi.yaml` solo declara `http://localhost:5000` en `servers`. |
| Pruebas automáticas | Resuelto: `test/run_all.py` ejecuta los 14 scripts y el workflow `.github/workflows/ci.yml` los corre en cada push y pull request. |
| Estrategia de ramas | Definir si se crean `develop` y `release` o se sigue desplegando desde `main`. |
| Seguridad | Ver `docs/seguridad_api.md` (CORS, límite de peticiones, HTTPS, token de reseteo en la respuesta). |
