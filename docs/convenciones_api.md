# Convenciones de la API

Reglas que se repiten en todos los endpoints de Api-SportMatch. Se
documentan una sola vez aquí para no repetirlas endpoint por endpoint en
cada `fase*.md` ni en el Swagger.

## 1. URL base y versionado

Todas las rutas parten de **`/api`** (prefijo definido por cada `Blueprint`
en `routes/`, ver `app.py`):

```
/api/auth/...
/api/usuarios/...
/api/deportes/...
/api/eventos/...
/api/rutas/...
/api/inscripciones/...
/api/organizadores/...
/api/reportes/...  /api/tickets/...  /api/admin/auditoria
```

> **Nota:** actualmente **no hay prefijo de versión** (`/api/v1`). Si en el
> futuro se necesita un cambio que rompa compatibilidad, la convención a
> seguir es crear `/api/v2/...` dejando `/api/...` (o `/api/v1/...`) como
> está, en vez de modificar las rutas existentes. Mientras eso no pase, no
> hay que escribir `/v1` en ningún lado: no existe en el código hoy.

## 2. Formato de request / response

- Todo el cuerpo de request y response es **JSON** (`Content-Type:
  application/json`). No se usa form-data ni query strings para el body de
  POST/PUT.
- Las respuestas exitosas regresan directamente el recurso (o una lista),
  nunca envuelto en un wrapper genérico tipo `{"data": ...}`.
- Las claves de los JSON van en **español y `snake_case`**
  (`nombre_completo`, `estado_cuenta`, `fecha_inicio`), igual que las
  columnas de la base de datos — así el `to_dict()` de cada modelo no
  necesita traducir nombres.

## 3. Autenticación

- JWT vía `Flask-JWT-Extended`. El token va en el header:
  ```
  Authorization: Bearer <token>
  ```
- Se obtiene en `POST /api/auth/login`. Expira a las 8 horas
  (`JWT_ACCESS_TOKEN_EXPIRES`, ver `config.py`).
- El JWT lleva el claim `rol` (`usuario` / `administrador`), usado por los
  decoradores de `utils/auth.py` (`@admin_required`, `@roles_required(...)`,
  `@usuario_autenticado_required`) para proteger cada ruta sin volver a
  consultar la base de datos solo para saber el rol.
- No existe refresh token todavía: al expirar, el cliente debe volver a
  hacer login. Ver sección 11 para el ciclo de vida completo del token.

## 4. Códigos de estado HTTP

| Código | Cuándo se usa |
|---|---|
| `200` | Lectura u operación exitosa que no crea un recurso nuevo |
| `201` | Creación exitosa (no todos los `POST` lo usan todavía de forma consistente — revisar caso a caso) |
| `400` | Validación fallida: campo faltante, formato inválido, valor fuera de catálogo |
| `401` | JWT faltante, inválido o expirado (lo maneja `Flask-JWT-Extended` automáticamente) |
| `403` | JWT válido pero sin permiso para esa acción (rol incorrecto, no es dueño del recurso) |
| `404` | El recurso no existe (o, en catálogos con borrado suave, no está visible para ese rol) |
| `409` | Conflicto: ya existe un recurso único (p. ej. nivel de paquete duplicado), o estado que no admite la operación (cupo lleno, ya cancelado) |
| `500` | Error interno no controlado (`app.py` define un handler genérico) |

## 5. Formato de errores

Todo error regresa siempre la misma forma, nunca texto plano ni HTML:

```json
{ "error": "Mensaje describiendo qué salió mal, en español" }
```

Las respuestas exitosas que no regresan un recurso (p. ej. tras un `DELETE`
o un cambio de estado) usan `"mensaje"` en vez de `"error"`:

```json
{ "mensaje": "Contraseña actualizada" }
```

## 6. Paginación

Los listados largos (`/api/usuarios`, `/api/eventos`, `/api/admin/auditoria`,
etc.) aceptan query params y regresan siempre la misma envoltura:

**Request:** `?page=1&per_page=20` (ambos opcionales; `per_page` tiene un
tope distinto por endpoint — 100 en catálogos normales, 200 en auditoría —
para evitar que un cliente pida de más).

**Response:**
```json
{
  "usuarios": [ ... ],
  "total": 134,
  "page": 1,
  "per_page": 20,
  "paginas": 7
}
```

La clave de la lista (`usuarios`, `eventos`, `registros`, ...) cambia según
el recurso; `total`, `page`, `per_page` y `paginas` son siempre iguales.

## 7. Fechas y horas

- Se envían y reciben como **string ISO 8601** (`"2026-11-15T07:00:00"` o
  con `Z`/offset). El backend las convierte con
  `utils/fechas.py` (`parse_datetime`, `parse_date`, `parse_time`).
- Columnas solo de hora (`HH:MM:SS`, p. ej. `tiempo_oficial`) no admiten 24h
  o más — limitación del tipo `TIME` de PostgreSQL, no del parser.

## 8. Borrado suave (soft delete)

Ningún `DELETE` borra la fila físicamente en los recursos que son
catálogo o historial (usuarios, deportes, etc.): se marca un campo de
estado (`estado_cuenta`, `activo`, etc.) y las consultas públicas filtran
por ese estado. Los endpoints de admin pueden pedir explícitamente los
registros inactivos/eliminados vía query param cuando aplica.

## 9. Filtros en listados

Los query params de filtro siguen el nombre exacto de la columna
(`?rol=admin&estado_cuenta=activo`), y `q` se reserva siempre para búsqueda
libre tipo `ILIKE` sobre los campos de texto relevantes del recurso
(nombre, correo, título...).

## 10. Permisos por rol

Regla general (válida para casi todo endpoint simple: deportes, cuestionarios,
auditoría...):

| Módulo / acción | Público | Usuario | Administrador |
|---|---|---|---|
| Registrarse / iniciar sesión | Sí | Sí | Sí |
| Ver recursos | No | Sí | Sí |
| Crear / editar recursos | No | Propios | Todos |
| Eliminar recursos | No | No | Sí |

Varios módulos tienen matices sobre esa regla general (dueño del recurso,
miembro de un organizador, etc.). Detalle por módulo, verificado contra los
decoradores reales en `routes/`:

### Autenticación (`/api/auth`)

| Acción | Público | Usuario | Administrador |
|---|---|---|---|
| Registrarse, iniciar sesión, recuperar contraseña | Sí | Sí | Sí |
| Ver mis datos de sesión (`/me`) | No | Sí | Sí |

### Usuarios (`/api/usuarios`)

| Acción | Público | Usuario | Administrador |
|---|---|---|---|
| Editar mi perfil / mi contraseña | No | Sí (propio) | Sí (propio) |
| Ver listado / detalle de usuarios | No | No | Sí |
| Cambiar rol o estado de un usuario | No | No | Sí |
| Dar de alta a otro administrador | No | No | Sí |

### Deportes (`/api/deportes`)

| Acción | Público | Usuario | Administrador |
|---|---|---|---|
| Ver catálogo | Sí | Sí | Sí |
| Crear / editar catálogo | No | No | Sí |
| Eliminar (desactivar) catálogo | No | No | Sí |
| Gestionar mis deportes practicados (`/me`) | No | Sí (propios) | Sí (propios) |

### Cuestionarios (`/api/cuestionarios`)

| Acción | Público | Usuario | Administrador |
|---|---|---|---|
| Ver cuestionario / preguntas | Sí | Sí | Sí |
| Responder cuestionario | No | Sí | Sí |
| Crear / editar preguntas y opciones | No | No | Sí |

### Eventos (`/api/eventos`)

| Acción | Público | Usuario | Administrador |
|---|---|---|---|
| Ver eventos publicados | Sí | Sí | Sí |
| Crear / editar / eliminar evento y sub-recursos (deportes, requisitos, sedes, fechas, categorías, boletos) | No | Solo si es miembro (propietario/administrador) del organizador dueño | Sí (todos) |

### Rutas GPS (`/api/rutas`)

| Acción | Público | Usuario | Administrador |
|---|---|---|---|
| Ver rutas públicas | Sí | Sí | Sí |
| Crear ruta (propia, con puntos) | No | Sí | Sí |
| Editar / eliminar ruta | No | Dueño de la ruta | Sí (todas) |
| Ligar ruta a categoría de evento | No | No | Sí |

### Inscripciones, paquetes y valoraciones (`/api/inscripciones`, `/api/paquetes`, `/api/valoraciones`)

| Acción | Público | Usuario | Administrador |
|---|---|---|---|
| Inscribirse a un evento | No | Sí | Sí |
| Ver mis inscripciones / cancelar | No | Dueño | Sí (todas) |
| Cambiar estado o registrar resultado de una inscripción | No | No | Sí |
| Ver inscripciones de un evento | No | No | Sí |
| Crear / editar / eliminar paquetes de recuperación | No | No | Sí |
| Dejar una valoración (si `estado=completada`) | No | Dueño | Sí (todas) |
| Responder una valoración | No | No | Sí |
| Gestionar mi calendario de eventos | No | Sí (propio) | Sí (propio) |

### Organizadores (`/api/organizadores`)

| Acción | Público | Usuario | Administrador |
|---|---|---|---|
| Ver organizadores aprobados | Sí | Sí | Sí |
| Crear mi perfil de organizador | No | Sí (uno propio) | Sí |
| Editar / eliminar organizador, gestionar miembros y cuentas de cobro | No | Miembro (propietario/administrador) | Sí (todos) |
| Verificar cuenta de cobro | No | No | Sí |
| Enviar solicitud de validación (con documentos) | No | Miembro del organizador | Sí |
| Revisar solicitudes (aprobar / rechazar) | No | No | Sí |

### Soporte: reportes y tickets (`/api/reportes`, `/api/tickets`)

| Acción | Público | Usuario | Administrador |
|---|---|---|---|
| Crear reporte o ticket | No | Sí | Sí |
| Ver mis reportes / tickets | No | Dueño | Sí (todos) |
| Ver listado completo de reportes / tickets | No | No | Sí |
| Moderar reporte / actualizar ticket (estado, prioridad, asignación) | No | No | Sí |
| Agregar mensaje a un ticket | No | Dueño (sin ver mensajes internos) | Sí (incluye mensajes internos) |

### Auditoría (`/api/admin/auditoria`)

| Acción | Público | Usuario | Administrador |
|---|---|---|---|
| Ver bitácora de auditoría | No | No | Sí |

## 11. Ciclo de vida del token

Verificado contra `routes/auth.py`, `utils/auth.py`, `config.py` y `app.py`
— no hay nada de esto implícito, es el comportamiento real del código hoy.

### Duración del access token

- Se emite con `create_access_token(identity=str(usuario.id),
  additional_claims={"rol": usuario.rol})` en dos endpoints:
  `POST /api/auth/register` (201) y `POST /api/auth/login` (200).
- Dura **8 horas** desde que se emite (`JWT_ACCESS_TOKEN_EXPIRES =
  timedelta(hours=8)` en `config.py`). Pasado ese tiempo, `Flask-JWT-Extended`
  responde automáticamente `401` en cualquier ruta protegida.
- Es un JWT firmado con `JWT_SECRET_KEY` (HS256 por default de la librería):
  **stateless**, no se guarda en la base de datos ni en ninguna tabla. El
  servidor no sabe qué tokens están "activos"; solo valida la firma y la
  fecha de expiración (`exp`) en cada request.
- El claim `rol` queda fijo en el token desde que se emite. Si un admin le
  cambia el rol a un usuario (`PUT /api/usuarios/<id>/rol`) mientras ese
  usuario tiene un token vigente, **el token viejo sigue con el rol
  anterior** hasta que expire o el usuario vuelva a hacer login.

### Cómo se renueva (refresh token) o se vuelve a iniciar sesión

- **No existe refresh token.** No hay `create_refresh_token`, ni endpoint
  `/refresh`, en ningún lugar del código.
- La única forma de obtener un token nuevo es volver a llamar
  `POST /api/auth/login` con correo/password. No hay renovación silenciosa:
  cuando el access token expira, el cliente debe mostrar login de nuevo.
- Si se necesita evitar que la sesión se corte a medio uso, la opción
  actual (manual) es que el cliente vuelva a loguear antes de que pasen las
  8 horas — no hay mecanismo del servidor que lo haga por él.

### Qué ocurre al cerrar sesión

- **No existe endpoint de logout** (`/api/auth/logout` no está implementado)
  ni un `token_in_blocklist_loader` configurado en `JWTManager(app)`
  (`app.py`). Por diseño de JWT stateless, "cerrar sesión" en esta API es
  **100% responsabilidad del cliente**: borrar el token guardado
  (localStorage, memoria, etc.) y dejar de enviarlo.
- Consecuencia importante: si alguien más obtuvo una copia del token (robo,
  log, etc.) antes de que el usuario "cerrara sesión" en su app, ese token
  **sigue siendo válido en el servidor** hasta su expiración natural (8h) —
  borrarlo del cliente no lo revoca.
- Si se necesita poder invalidar tokens de verdad (logout real, o forzar
  cierre de sesión al suspender una cuenta), hay que agregar una blocklist
  server-side (tabla de `jti` revocados + `token_in_blocklist_loader` de
  `Flask-JWT-Extended`) — hoy esa pieza no está construida.
