# Contenerización con Docker

Configuración de Docker de Api-SportMatch, verificada ejecutando la imagen
contra la base de datos PostgreSQL de Neon.

**Archivos:** `Dockerfile` · `.dockerignore` · `docker-compose.yml`

## Qué se contenariza y qué no

| Componente | Contenerizado | Motivo |
|---|---|---|
| API (Flask + Gunicorn) | ✅ Sí | `Dockerfile` en la raíz de este repositorio. |
| Aplicación web (React.js) | ⚠️ Propuesto | Vive en otro repositorio; ver "Dockerfile de la aplicación web". |
| PostgreSQL de producción | ❌ No | Servicio administrado por Neon: no se migra a contenedores. |
| PostgreSQL de pruebas | ✅ Sí | Servicio `db-pruebas` del compose, bajo el perfil `pruebas`. |
| Aplicación móvil (React Native / Expo) | ❌ No | Se distribuye como APK generado con Expo, no como servicio HTTP. |

## Imagen de la API

El `Dockerfile` usa **construcción multietapa**:

| Etapa | Qué hace |
|---|---|
| `builder` | Instala `build-essential` y `libpq-dev` y construye las dependencias de `requirements.txt` en un entorno virtual en `/opt/venv`. |
| final | Parte de `python:3.12-slim`, instala solo `libpq5` y `curl`, y copia `/opt/venv` ya construido. |

Decisiones de la imagen:

| Elemento | Valor | Motivo |
|---|---|---|
| Python | 3.12-slim | Misma versión que `runtime.txt` y que el servicio de Render. |
| Usuario | `sportmatch` (sin privilegios) | El contenedor no se ejecuta como root. |
| Servidor | `gunicorn "app:create_app()"` | Nunca `python app.py`, que arranca en modo debug. |
| Workers | 2 workers, 4 threads | Ajustable con `--workers` según los recursos del servidor. |
| Puerto | 5000 | `EXPOSE 5000`, publicado como `5000:5000`. |
| `HEALTHCHECK` | `curl /api/health` cada 30 s | Marca el contenedor `healthy` / `unhealthy`. |
| Volumen | `/app/static/uploads` | Los archivos que suben los usuarios no viven en la imagen. |

`.dockerignore` excluye `.env`, `.git`, `venv/`, `node_modules/`,
`__pycache__/`, los `*.sqlite3` de `test/` y `static/uploads/`. El `.env`
**nunca** entra en la imagen: la configuración se inyecta como variables de
entorno.

## Comandos

| Acción | Comando |
|---|---|
| Construir la imagen | `docker build -t sportmatch/api:1.7.1 .` |
| Levantar la API | `docker compose up -d --build` |
| API + PostgreSQL de pruebas | `docker compose --profile pruebas up -d` |
| Ver estado y salud | `docker compose ps` |
| Ver registros en vivo | `docker compose logs -f api` |
| Consumo de recursos | `docker stats sportmatch-api` |
| Pruebas dentro del contenedor | `docker compose exec -e DATABASE_URL=sqlite:///contenedor_pruebas.sqlite3 api python test/run_all.py` |
| Detener y eliminar | `docker compose down` |

## Variables de entorno

Se declaran en `docker-compose.yml` y se leen del archivo `.env` del equipo
(que está en `.gitignore`). Ver `.env.example`.

| Variable | Obligatoria | Notas |
|---|---|---|
| `DATABASE_URL` | Sí | Cadena de Neon con `?sslmode=require`. Si falta, el compose se detiene con un mensaje. |
| `SECRET_KEY` | Recomendada | Sin ella se usa el valor de desarrollo de `config.py`. |
| `JWT_SECRET_KEY` | Recomendada | Igual que la anterior. |
| `COMISION_POR_DEFECTO` | No | Por defecto `10`. |
| `SIMULAR_PASARELA` | No | En el compose queda en `false`: con `true` un pago puede marcarse como pagado sin pagarse. |
| `POSTGRES_PASSWORD` | Solo perfil `pruebas` | Contraseña del PostgreSQL local. |

## Red

Los servicios comparten la red bridge `sportmatch-net` y se localizan entre
sí por su nombre de servicio (`api`, `db-pruebas`), sin exponer puertos
adicionales al host. Solo la API publica un puerto (`5000`).

## Resultado de la verificación

| Comprobación | Resultado |
|---|---|
| Construcción de la imagen | ✅ Correcta (302 MB en disco) |
| Estado del contenedor | ✅ `Up (healthy)` |
| `GET /api/health` | ✅ `200` · `{"status":"ok","proyecto":"SportMatch"}` |
| `GET /api/deportes` (lectura de Neon) | ✅ `200` con el catálogo de deportes |
| `test/run_all.py` en el contenedor | ✅ 14 de 14 scripts en 30.9 s |

> Durante esta verificación se detectó que `requirements.txt` no fijaba la
> versión de SQLAlchemy. Una instalación limpia instalaba la 2.1, donde
> `postgresql://` usa psycopg v3 por defecto en lugar de psycopg2, y la API
> no arrancaba (`ModuleNotFoundError: No module named 'psycopg'`). Se fijó
> `SQLAlchemy>=2.0,<2.1`. El entorno local no lo mostraba porque ya tenía
> instalada la 2.0.54, y la integración continua tampoco, porque sus pruebas
> usan SQLite.

## Dockerfile de la aplicación web (propuesto)

La aplicación web de React.js está en otro repositorio y hoy se publica
manualmente en la instancia de Amazon EC2. Configuración propuesta, también
multietapa: Node construye los archivos de producción y Nginx los sirve.

```dockerfile
# Etapa 1: construcción de los archivos estáticos
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# La URL de la API se inyecta en tiempo de construcción
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# Etapa 2: servidor web
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Necesario para que las rutas del enrutador de React no devuelvan 404
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

La imagen final solo contiene los archivos compilados y Nginx: no incluye
Node, `node_modules` ni el código fuente.
