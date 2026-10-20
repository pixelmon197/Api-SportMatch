# Fase 14 — Módulo Perfiles

## Revisión de la tabla `perfiles` en Neon

- Su llave primaria real es **`usuario_id`**. No tiene columna `id` propia
  (la documentación del proyecto decía lo contrario: el mismo error del
  "id inventado" que ya se corrigió en otros módulos). `bloqueos` tiene el
  mismo detalle: PK compuesta `(bloqueador_id, bloqueado_id)`.
- `actualizado_en` es `NOT NULL DEFAULT CURRENT_TIMESTAMP`; el modelo lo
  declara con `default` para no mandar `NULL` (el bug de siempre).
- Los tres campos de visibilidad (`visibilidad_perfil`,
  `visibilidad_ubicacion`, `quien_puede_escribir`) tienen un `CHECK` con
  `publico` / `amigos` / `privado`. Los defaults reales son `publico`,
  `amigos` y `publico`.
- `amistades.estado` **no tiene `CHECK`** en Neon: el catálogo
  (`pendiente`, `aceptada`, `rechazada`) lo define la API.

## Endpoints

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/api/perfiles/me` | Autenticado | Mi usuario + mi perfil + mis deportes (con ubicación y ajustes) |
| PUT | `/api/perfiles/me` | Autenticado | Editar biografía, avatar, portada y privacidad |
| PUT | `/api/perfiles/me/ubicacion` | Autenticado | Guardar mi ubicación (latitud/longitud) |
| DELETE | `/api/perfiles/me/ubicacion` | Autenticado | Borrar mi ubicación |
| GET | `/api/perfiles/{usuario_id}` | Público* | Ver el perfil de otro usuario |
| GET | `/api/perfiles/usuario/{nombre_usuario}` | Público* | Lo mismo, buscando por nombre de usuario |

\* Se puede consultar sin iniciar sesión si el perfil es público; con token
además se reconoce a los amigos.

### Reglas de quién ve qué

- **Dueño y administradores**: ven todo.
- **Perfil `privado`** → 403 para todos los demás (incluso amigos).
- **Perfil `amigos`** → 403 salvo para quien tenga una amistad *aceptada*
  (en cualquiera de los dos sentidos; una solicitud pendiente no cuenta).
- **Bloqueo en cualquier sentido** → 404 (no se revela que el perfil existe).
- **Cuenta suspendida o eliminada** → 404 para los demás.
- **Ubicación**: aunque el perfil sea visible, la ubicación solo se muestra si
  `visibilidad_ubicacion` lo permite (`publico`, o `amigos` y son amigos).
- A terceros **nunca** se les muestra correo, teléfono, fecha de nacimiento,
  sexo ni rol, ni los ajustes de privacidad.

### Decisiones de diseño

- **El perfil se crea de forma perezosa**: no hay fila en `perfiles` hasta que
  el usuario consulta o edita el suyo (`GET/PUT /me`), con los valores por
  defecto de Neon. Así funciona para usuarios que ya existían, sin migración.
- **Un GET de otra persona nunca escribe en la base**: si no tiene fila, se
  arma una respuesta con los valores por defecto sin guardarla (la prueba lo
  verifica contando filas).
- `avatar_id` y `portada_id` deben ser imágenes ya subidas con
  `POST /api/archivos` (FK real a `archivos`, validado igual que en eventos).
- La biografía se limita a 500 caracteres (límite de la API; en Neon es `text`).
- Latitud entre -90 y 90, longitud entre -180 y 180, y deben ser números.
- `Amistad` y `Bloqueo` se agregaron como modelos mínimos de solo lectura,
  porque las reglas de visibilidad los necesitan. **Todavía no hay endpoints**
  para enviar/aceptar solicitudes de amistad ni para bloquear: son el
  siguiente módulo natural (junto con `seguidores`).

## Documentación (Swagger)

Nuevo grupo **Perfiles** con los 6 endpoints, y tres esquemas: `Perfil`,
`PerfilCompleto` (lo que ve el dueño) y `PerfilPublico` (lo que ve un
tercero). Los dos GET públicos usan seguridad opcional, así Swagger envía el
token si lo tienes puesto y se puede probar "como amigo".

## Verificación

`test/test_perfiles.py`: perfil creado con los defaults reales; edición y sus
validaciones (avatar que es un GPX, imagen inexistente, visibilidad inválida,
booleano inválido, biografía larga); borrar el avatar con `null`; sin token
(401); ubicación válida e inválida (fuera de rango, texto, `true`, faltante);
vista pública sin datos privados; ubicación visible para el amigo (amistad
guardada en sentido inverso), oculta para el desconocido y para quien solo tiene
solicitud pendiente; ubicación pública y privada; perfil `amigos`; perfil
`privado` (ni una amiga entra, el admin sí); bloqueo en ambos sentidos;
búsqueda por nombre de usuario con mayúsculas; usuario sin fila en `perfiles`
(un GET no crea filas); cuenta suspendida; borrar ubicación. Las 11 pruebas del
proyecto pasan juntas.
