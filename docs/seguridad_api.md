# Seguridad de la API

Estado real de las medidas de seguridad de Api-SportMatch, revisado contra
el código (`app.py`, `config.py`, `utils/auth.py`, `models/`, `routes/`).
La API es Flask, así que cada medida se documenta con su equivalente en
Python (no `bcrypt`/`helmet`/`express-rate-limit`, que son de Node).

**Estados:** ✅ Implementado · ⚠️ Parcial · ❌ Pendiente

## Resumen

| Medida | Cómo se implementó | Estado |
|---|---|---|
| Contraseñas con hash | `werkzeug.security.generate_password_hash` / `check_password_hash` en `models/usuario.py` (hash con sal; scrypt por defecto en Werkzeug 3, no bcrypt). Nunca se guarda ni se regresa la contraseña en claro. | ✅ Implementado |
| Tokens firmados | JWT con `Flask-JWT-Extended`, firmados con `JWT_SECRET_KEY` y expiración de 8 horas (`JWT_ACCESS_TOKEN_EXPIRES` en `config.py`). El rol viaja como claim `rol`. | ✅ Implementado |
| Control de acceso por rol | Decoradores `roles_required`, `admin_required` y `usuario_autenticado_required` en `utils/auth.py`, más permisos por pertenencia (`puede_gestionar_organizador`, `puede_gestionar_evento`). | ✅ Implementado |
| Tokens de recuperación | `TokenVerificacion`: valor aleatorio con `secrets.token_urlsafe(32)`, en la base solo se guarda su SHA-256, de un solo uso y con 30 minutos de validez. | ⚠️ Parcial |
| Secretos fuera del código | `SECRET_KEY`, `JWT_SECRET_KEY` y `DATABASE_URL` se leen de `.env` (ignorado por git; existe `.env.example`). | ⚠️ Parcial |
| Validación y sanitización | Validación manual en cada ruta (campos requeridos, catálogos permitidos, teléfono, fechas, llaves foráneas). Consultas con el ORM de SQLAlchemy, que parametriza y evita inyección SQL. | ⚠️ Parcial |
| Auditoría | `registrar_auditoria` (`utils/auditoria.py`) guarda usuario, acción, datos antes/después e IP en `auditoria_log` para las acciones administrativas sensibles. | ✅ Implementado |
| CORS restringido | `CORS(app)` en `app.py` sin lista de orígenes: acepta peticiones de cualquier origen. | ❌ Pendiente |
| Límite de peticiones | No hay limitador (ni en login ni en recuperación de contraseña). | ❌ Pendiente |
| Cabeceras de seguridad | No se envían cabeceras como `Strict-Transport-Security`, `X-Content-Type-Options` o `X-Frame-Options`. | ❌ Pendiente |
| HTTPS | La API no fuerza HTTPS; depende del certificado del proveedor donde se despliegue. La conexión a Neon sí va cifrada (`sslmode=require` en `DATABASE_URL`). | ❌ Pendiente |

## Detalle de lo parcial y lo pendiente

| Medida | Qué falta | Cómo resolverlo |
|---|---|---|
| Tokens de recuperación | `POST /api/auth/olvide-contrasena` regresa `token_reseteo` en la respuesta (hay un `TODO` en `routes/auth.py`). Cualquiera que conozca un correo puede restablecer esa contraseña. | Enviar el token por correo y quitarlo de la respuesta antes de producción. |
| Secretos fuera del código | `config.py` tiene valores por defecto (`"cambia-esta-clave-en-produccion"`): si falta la variable de entorno, la API arranca con una clave conocida. | Fallar al arrancar si `SECRET_KEY` o `JWT_SECRET_KEY` no están definidas en producción. |
| Validación y sanitización | No hay esquemas declarativos; cada ruta valida a mano, así que la cobertura no es uniforme (por ejemplo, la longitud mínima de 8 caracteres solo se exige en `/restablecer-contrasena`, no en `/register`). | Adoptar esquemas (`marshmallow` o `pydantic`) y aplicar la misma política de contraseñas en todas las rutas. |
| Revocación de tokens | Un JWT sigue siendo válido hasta que expira (8 h): no hay logout del lado del servidor ni refresh tokens. | Lista de bloqueo con `token_in_blocklist_loader` de `Flask-JWT-Extended` y tokens de acceso más cortos con refresh. |
| CORS restringido | Cualquier origen puede llamar a la API. | `CORS(app, origins=[...])` con la lista de dominios del frontend, leída de una variable de entorno. |
| Límite de peticiones | Login y recuperación de contraseña quedan expuestos a fuerza bruta. | `Flask-Limiter`, con límites más estrictos en `/api/auth/*`. |
| Cabeceras de seguridad | Sin cabeceras de protección del navegador. | `Flask-Talisman` (equivalente a `helmet`). |
| HTTPS | No se redirige HTTP a HTTPS ni se envía HSTS. | Certificado en el proveedor de despliegue y `Flask-Talisman` con `force_https`. |
| Modo debug | `app.py` arranca con `debug=True` y `host="0.0.0.0"` al ejecutarse directamente. | En producción arrancar solo con `gunicorn` (ya está en `requirements.txt`), nunca con `python app.py`. |
