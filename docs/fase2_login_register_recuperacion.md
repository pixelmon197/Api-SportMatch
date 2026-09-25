# Fase 1 y 2 — Login, Register, Olvidé/Restablecer contraseña

## Fase 1 — Análisis (API vs `Neon.sql`)

Se comparó `models/usuario.py` y `models/token_verificacion.py` contra las
tablas reales `usuarios` y `tokens_verificacion` del script `Neon.sql`.
Se confirmó cada hallazgo con una prueba automatizada end-to-end contra un
esquema que replica los `CHECK`/`NOT NULL` reales de Neon (ver
`test_neon_like.py` adjunto al entregable). Hallazgos:

### 1. Nombres de columna que no coinciden (rompían TODAS las consultas a `usuarios`, incluyendo login)

| Atributo del modelo      | Columna que el modelo esperaba | Columna real en Neon |
|---------------------------|-------------------------------|------------------------|
| `contrasena_hash`          | `contrasena_hash`             | `contrasena`            |
| `fecha_de_nacimiento`      | `fecha_de_nacimiento`         | `fecha_nacimiento`      |

Como SQLAlchemy arma el `SELECT`/`INSERT` con el nombre de columna que
declara el modelo, cualquier consulta a `Usuario` (incluida
`Usuario.query.filter_by(correo=...)` del login) fallaba con
`UndefinedColumn` contra la base real.

### 2. `usuarios.actualizado_en` es `NOT NULL DEFAULT CURRENT_TIMESTAMP` en Neon, pero el modelo no traía `default`

El modelo solo definía `onupdate`, no `default`. SQLAlchemy no conoce el
`DEFAULT` que vive del lado de Postgres, así que en cada `INSERT` mandaba
`NULL` explícito para esa columna → violación de `NOT NULL` en cada
registro nuevo. Se reprodujo el error exacto con la prueba automatizada.

### 3. `usuarios_check` (CHECK compuesto) rompía el registro

```
CHECK ((registro_completo_en IS NULL) OR
       (correo IS NOT NULL AND fecha_nacimiento IS NOT NULL AND sexo IS NOT NULL))
```

`register()` siempre fijaba `registro_completo_en = ahora()`, pero nunca
pedía `fecha_nacimiento` al cliente (ni tenía ese campo en el payload) y
`sexo` era opcional. Resultado: el `INSERT` violaba el CHECK en cuanto se
corrigieran los nombres de columna del punto 1.

### 4. `nombre_usuario` debe ir en minúsculas (CHECK) y el modelo no lo normalizaba

`CHECK (nombre_usuario = lower(nombre_usuario))` en Neon; `register()`
guardaba el valor tal cual lo mandara el cliente. Cualquier usuario con
una mayúscula en su nombre de usuario hacía fallar el `INSERT`.

### 5. `sexo` tiene un CHECK de valores permitidos y no se validaba

`CHECK (sexo IN ('masculino','femenino','otro','prefiero_no_decir'))`. La
API aceptaba cualquier string sin validar, lo que producía un error 500
sin control si el cliente mandaba un valor fuera de ese catálogo.

### 6. `nombre_usuario` es `varchar(30)` en Neon; el modelo declaraba `String(50)`

Un nombre de usuario de 31-50 caracteres pasaba la validación de la API
pero rompía al insertarse en Postgres.

### 7. Tabla de tokens duplicada: el modelo apuntaba a la tabla vieja

En Neon existen **dos** tablas de verificación (residuo de un rediseño a
medias):

- `tockens_verificacion` (con el typo del diagrama original, sin `CHECK`
  de `tipo`) — es la que usaba el modelo.
- `tokens_verificacion` (ortografía correcta, con `CHECK` real de `tipo`
  y `token_hash varchar(64) UNIQUE`) — es la tabla vigente, pensada para
  búsqueda directa por hash.

Los valores de `tipo` también difieren: el modelo usaba
`verificar_correo` / `recuperar_contrasena` / `cambiar_correo`, mientras
que el `CHECK` real exige `verificacion_correo` / `restablecer_contrasena`
/ `cambio_correo`.

Además, el modelo hasheaba el token con `werkzeug.generate_password_hash`
(salida variable, normalmente >80 caracteres) — no cabe en
`varchar(64)`, y al ser salteado tampoco permite buscar el registro
directamente por hash (habría que traer todos los tokens activos y
probarlos uno por uno).

### 8. Los endpoints de Olvidé/Restablecer contraseña no existían

`routes/auth.py` solo tenía `/register`, `/login` y `/me`. El modelo de
soporte (`TokenVerificacion`) ya estaba, pero nunca se usaba desde ninguna
ruta.

### Hallazgo adicional (fuera de prioridad, no se tocó en esta entrega)

`usuarios.rol` en Neon tiene `CHECK (rol IN ('usuario','organizador','administrador'))`,
pero el código usa `'admin'` en todo el proyecto (`ROLES_VALIDOS`,
`routes/usuarios.py` al crear administradores, `utils/auth.py`). Esto no
afecta a Login/Register/Olvidé/Restablecer (que siempre usan
`rol='usuario'`), pero **romperá la creación de administradores** en
cuanto se pruebe contra Neon real. Se deja documentado para una fase
dedicada a usuarios/roles.

## Fase 2 — Cambios aplicados

- `models/usuario.py`: mapeo explícito de columnas
  (`contrasena_hash`→`contrasena`, `fecha_de_nacimiento`→`fecha_nacimiento`),
  `nombre_usuario` a `String(30)`, `actualizado_en` con `default` +
  `onupdate`, `ESTADOS_CUENTA` incluye `pendiente_verificacion` (se deja
  el default de la app en `activa` porque todavía no hay flujo de
  verificación de correo), se agregó `SEXOS_VALIDOS`.
- `models/token_verificacion.py`: apunta a `tokens_verificacion` (tabla
  correcta), `TIPOS_TOKEN` actualizado a los valores reales, hash con
  SHA-256 (64 caracteres, determinista → permite `buscar_valido()` por
  hash directo), nuevo método `TokenVerificacion.buscar_valido(tipo, valor_plano)`.
- `routes/auth.py`:
  - `register()` ahora pide y valida `fecha_nacimiento` (formato
    `YYYY-MM-DD`) y `sexo` (catálogo cerrado), normaliza `nombre_usuario`
    a minúsculas y valida su longitud.
  - Nuevo `POST /api/auth/olvide-contrasena`: recibe `correo`, siempre
    responde 200 con mensaje genérico (no filtra si el correo existe); si
    existe, genera un token de un solo uso (30 min) y lo regresa en
    `token_reseteo` **solo como solución temporal de prueba**, ya que el
    proyecto no tiene todavía un servicio de envío de correo. Queda un
    `TODO` explícito en el código para cuando se integre uno.
  - Nuevo `POST /api/auth/restablecer-contrasena`: recibe `token` y
    `nueva_password` (mínimo 8 caracteres), valida el token
    (tipo/expiración/uso), actualiza la contraseña y marca el token como
    usado (no se puede reutilizar).
- `static/openapi.yaml`: documentados los dos endpoints nuevos y los
  campos nuevos de `/register`.

## Verificación

Se armó `test_neon_like.py` (raíz del entregable, no forma parte del
código de producción): crea una base SQLite con las mismas columnas,
`NOT NULL` y `CHECK` reales de `usuarios` y `tokens_verificacion` en
Neon, levanta la app con `create_app()` y prueba con el cliente de Flask:
registro válido, login, correo/usuario duplicado, `sexo` inválido, falta
de `fecha_nacimiento`, olvidé-contraseña (con y sin correo existente),
restablecer contraseña, login con la contraseña vieja (debe fallar), login
con la nueva (debe funcionar) y reintento del mismo token ya usado (debe
fallar). Todas las pruebas pasan.

Este script **no reemplaza probar contra el Neon real**: valida que la
lógica y los nombres/tipos de columna coinciden con el DDL de
`Neon.sql`, pero no puede replicar detalles específicos del motor
Postgres (por ejemplo, cómo maneja `serial4`, codificaciones, etc.).
Antes de dar por cerrado el entregable, se recomienda correr
`flask run` con el `DATABASE_URL` real de Neon y repetir manualmente las
mismas pruebas contra `/api/docs`.
