# Fase 9 — Módulo Soporte (reportes, tickets, auditoría)

## Bugs corregidos (confirmados con pruebas contra un esquema que replica las columnas/NOT NULL reales de Neon)

1. **`tickets_soporte.categoria` es `NOT NULL` en Neon**, pero el modelo
   la declaraba `nullable=True` y la ruta la mandaba tal cual viniera del
   cliente (`categoria=data.get("categoria")`, sin validar). Cualquier
   `POST /api/tickets` sin `categoria` habría roto contra la base real.
   Ahora es obligatoria (400 claro si falta), y `PUT /tickets/<id>`
   tampoco permite dejarla vacía si se manda explícitamente.

2. **Columnas más cortas en Neon de lo que el modelo asumía** — a
   diferencia de otros módulos, aquí no hay `CHECK` de catálogo (Neon no
   restringe los valores de `categoria`, `motivo`, `tipo_entidad`, etc.),
   pero sí hay un límite de longitud real que Postgres **no trunca como
   MySQL: rechaza el INSERT con un error crudo** si se excede:

   | Columna | Neon | Modelo (antes) |
   |---|---|---|
   | `tickets_soporte.categoria` | `varchar(20)` | `String(50)` |
   | `tickets_soporte.prioridad` | `varchar(20)` | `String(10)` |
   | `tickets_soporte.estado` | `varchar(30)` | `String(20)` |
   | `reportes.tipo_entidad` | `varchar(30)` | `String(50)` |
   | `reportes.motivo` | `varchar(30)` | `String(100)` |
   | `reportes.accion_tomada` | `varchar(30)` | `Text` (sin límite) |

   Se ajustaron los tamaños de columna al real, y se agregó una
   validación explícita (`_validar_longitud`) en las rutas que reciben
   `categoria`, `tipo_entidad`, `motivo` y `accion_tomada`, para
   responder 400 con un mensaje claro en vez de dejar que rompa contra
   la base — esto importa porque `motivo`/`tipo_entidad`/`accion_tomada`
   son el tipo de campo donde un cliente fácilmente manda más de 30
   caracteres sin darse cuenta.

3. **Tabla legacy `ticket_mensaje`**: el modelo apuntaba a la vieja (sin
   `ON DELETE CASCADE`, sin los defaults de `es_interno`/`creado_en`) en
   vez de la vigente `ticket_mensajes`. Mismo patrón que ya se corrigió
   varias veces en otros módulos. Se ajustó el `__tablename__`.

El resto del módulo (mensajes internos vs públicos, cambios de estado de
ticket al responder, moderación de reportes con bitácora de auditoría)
ya estaba bien encaminado — no encontré más incompatibilidades.

## Verificación

`test_soporte.py` (adjunto) monta un esquema SQLite con las columnas y
longitudes reales de `reportes`, `tickets_soporte` y `ticket_mensajes`,
y prueba: crear ticket sin categoría (400), categoría demasiado larga
(400), ticket válido con su primer mensaje, agregar mensaje interno y
público, confirmar que el dueño del ticket no ve los internos, intentar
vaciar la categoría al actualizar (400), actualizar categoría y cerrar
el ticket, crear reporte válido, motivo demasiado largo (400), moderar
un reporte con `accion_tomada` demasiado larga (400) y luego válida.
Todo pasa. Se re-corrieron las pruebas de las Fases 2 a 8 — sin
regresiones.

## Documentación (`static/openapi.yaml`)

Se actualizó la sección de `/api/reportes` y `/api/tickets` con el mismo
estilo con ejemplos usado en fases anteriores (`type: ..., example: ...`
en vez de solo `type: string`), se marcó `categoria` como obligatoria en
`POST /api/tickets`, se documentó el `requestBody` de
`PUT /api/tickets/{ticket_id}` (no existía), y se agregó `maxLength` a
los campos con límite real de Neon. Se validó que el YAML sigue siendo
válido.
