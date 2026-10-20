# Fase 15 — Seguidores, amistades y bloqueos

## Revisión de las tablas en Neon

- `seguidores` y `bloqueos` tienen **PK compuesta, sin `id` propio** (la
  documentación del proyecto decía que `bloqueos` tenía `id`: el error del
  "id inventado" de siempre). Las tres tablas tienen un `CHECK` que impide la
  relación con uno mismo, y todas hacen `ON DELETE CASCADE` hacia `usuarios`.
- `amistades` tiene `UNIQUE(usuario_id, amigo_id)` **por sentido**: dos filas
  A→B y B→A serían válidas para Neon aunque representen la misma amistad. La
  API siempre revisa ambos sentidos antes de crear una.
- `amistades.estado` no tiene `CHECK`: el catálogo (`pendiente`, `aceptada`,
  `rechazada`) lo define la API.

> Se incluyeron también las **amistades**, aunque se pidieron solo seguidores
> y bloqueos, porque la visibilidad "amigos" de los perfiles depende de ellas y
> bloquear a alguien tiene que deshacer también la amistad.

## Endpoints (17)

### Seguidores — `/api/seguidores`
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/{usuario_id}` | Seguir (sin aprobación) |
| DELETE | `/{usuario_id}` | Dejar de seguir |
| GET | `/me/seguidores` | Quiénes me siguen |
| GET | `/me/siguiendo` | A quiénes sigo |
| GET | `/{usuario_id}/seguidores` | Seguidores de otro (público*) |
| GET | `/{usuario_id}/siguiendo` | A quiénes sigue otro (público*) |

### Amistades — `/api/amistades`
| Método | Ruta | Descripción |
|---|---|---|
| GET | `` | Mis amigos |
| POST | `/solicitudes` | Enviar solicitud (`{"usuario_id": N}`) |
| GET | `/solicitudes/recibidas` | Solicitudes pendientes que me enviaron |
| GET | `/solicitudes/enviadas` | Solicitudes pendientes que envié |
| PUT | `/solicitudes/{id}/aceptar` | Aceptar (solo quien la recibió) |
| PUT | `/solicitudes/{id}/rechazar` | Rechazar (solo quien la recibió) |
| DELETE | `/solicitudes/{id}` | Cancelar una que envié |
| DELETE | `/amigos/{usuario_id}` | Eliminar un amigo (se borra para ambos) |

### Bloqueos — `/api/bloqueos`
| Método | Ruta | Descripción |
|---|---|---|
| GET | `` | Usuarios que bloqueé |
| POST | `/{usuario_id}` | Bloquear |
| DELETE | `/{usuario_id}` | Desbloquear |

\* Respetan la visibilidad del perfil: 403 si es privado o solo para amigos.
Las listas están paginadas con el mismo formato del resto de la API
(`page`, `per_page` hasta 100, y `total`/`paginas` en la respuesta).

## Reglas

- **Seguir**: no a uno mismo (400); no a cuentas suspendidas/eliminadas (404);
  repetir da 409.
- **Amistad**: una solicitud rechazada se puede volver a enviar (se reutiliza la
  misma fila, por el `UNIQUE` de Neon). Si la otra persona ya te envió una, la
  respuesta es 409 con su `solicitud_id` para que la aceptes. Solo quien recibe
  puede aceptar o rechazar (403 si no), y solo quien envía puede cancelar.
- **Bloquear** (lo más delicado):
  - Para la persona bloqueada, el bloqueador "no existe": su perfil, seguirlo y
    enviarle solicitudes dan **404**, para no revelar que lo bloquearon.
  - Para quien bloqueó, seguir o enviar solicitud a esa persona da 409
    ("desbloquéalo primero").
  - Se borran los seguimientos (en ambos sentidos) y la amistad o solicitudes
    pendientes entre los dos. **Desbloquear no los restaura.**
  - En los listados de seguidores, cada quien deja de ver a las personas con las
    que tiene un bloqueo (en cualquier sentido).
  - No toca relaciones con terceros.

## Cambios en perfiles

Ahora `GET /api/perfiles/...` agrega dos bloques, que son lo que permite armar la
pantalla (botón "Seguir", "Agregar amigo", "Aceptar"):

- `contadores`: `{seguidores, siguiendo, amigos}`.
- `relacion` (solo con sesión y en perfiles ajenos): `yo_sigo`, `me_sigue`,
  `amistad` (`ninguna` / `solicitud_enviada` / `solicitud_recibida` /
  `aceptada`) y `amistad_id`.

Además se movieron a `utils/social.py` las reglas de acceso que vivían dentro de
`routes/perfiles.py` (quién es amigo, quién bloqueó a quién, quién puede ver un
perfil), porque ahora las usan cuatro módulos.

**Ya se puede probar completa la visibilidad "amigos" desde Swagger**: se
envía y acepta una solicitud de amistad y el perfil pasa a ser visible.

## Documentación (Swagger)

Tres grupos nuevos (Seguidores, Amistades, Bloqueos) con las 17 operaciones, y
los esquemas `TarjetaUsuario`, `Amistad`, `Contadores` y `Relacion`; los
esquemas de perfil incluyen los dos bloques nuevos.

## Verificación

`test/test_social.py` (6 usuarios): seguir con todos sus errores; listas propias
con avatar y fecha; paginación; listas de otro respetando un perfil privado;
contadores y relación en el perfil; solicitud, solicitud cruzada, bandejas,
aceptar/rechazar por quien no debe (403) y por quien sí, doble respuesta (409),
efecto en la visibilidad "amigos"; rechazo y reenvío reutilizando la fila (se
verifica que no se duplica en la base); cancelar y eliminar amigo; bloquear
borrando seguimientos y amistad **sin tocar a terceros** (verificado con
consultas a la base); 404 para el bloqueado y 409 para el bloqueador; listas que
excluyen bloqueados; desbloquear sin restaurar. Las 12 pruebas del proyecto
pasan juntas.

## Pendiente

- No hay notificaciones: nadie se entera de una solicitud hasta que consulta su
  bandeja. Se resuelve con el módulo de notificaciones.
- Una solicitud rechazada se puede reenviar sin límite; si hace falta, se
  podría agregar un tiempo de espera.
