# Fase 8 — Módulo Deportes + documentación OpenAPI

## Bug corregido (confirmado con pruebas contra un esquema que replica el CHECK/CASCADE real de Neon)

**Tabla legacy**: `UsuarioDeporte` apuntaba a `usuarios_deportes` (con
"s" de más) en vez de la vigente `usuario_deportes`. Mismo patrón que ya
vimos varias veces (tokens, fechas/requisitos de evento, respuestas de
cuestionario, paquetes de recuperación): la tabla vieja **sí existe** en
Neon y no truena, pero le faltan cosas importantes que sí tiene la
vigente:

- `ON DELETE CASCADE` en `usuario_id` (si se borra un usuario, en la
  tabla vieja la fila de `usuarios_deportes` quedaría huérfana en vez de
  borrarse sola).
- El `CHECK` real de `nivel` — que por cierto **sí coincidía** con
  `NIVELES_DEPORTE` en el código (`principiante/intermedio/avanzado/profesional`);
  aquí el catálogo de valores nunca estuvo mal, solo la tabla.

Se corrigió `__tablename__` a `usuario_deportes`. De paso se ajustó
`Deporte.nombre` de `String(80)` a `String(100)` para que coincida
exactamente con `varchar(100)` en Neon (antes era más corto, no
generaba error pero limitaba de más).

El resto del módulo (catálogo de deportes, agregar/quitar deportes del
perfil, marcar uno como principal, validación de `nivel`) ya estaba bien
armado — no encontré más incompatibilidades aquí.

## Verificación

`test_deportes.py` (adjunto) monta un esquema SQLite con las columnas,
`CHECK` y PK compuesta reales de `deportes` y `usuario_deportes`, y
prueba: crear deportes, nombre duplicado (409), listar solo activos,
agregar un deporte al perfil marcándolo principal, agregar otro como
principal (el anterior deja de serlo), agregar el mismo deporte dos
veces (409 por la PK compuesta), nivel inválido (400), actualizar nivel,
desactivar un deporte (borrado suave, ya no sale en el listado público),
y quitar un deporte del perfil. Todo pasa. Se re-corrieron las pruebas
de las Fases 2 a 7 — sin regresiones.

## Documentación (`static/openapi.yaml`)

Se actualizó siguiendo el mismo estilo que ya tenían los endpoints de
`/api/auth/register` (`type: ..., example: ...` en vez de solo
`type: string`/`type: integer`/`type: boolean` sin ejemplo):

- Se agregaron ejemplos a todos los campos de `/api/deportes/*` que no
  los tenían (`deporte_id`, `nivel`, `es_principal`, `activo`, y los
  `deporte_id` de path).
- Se completó el `requestBody` de `PUT /api/deportes/{deporte_id}`, que
  no estaba documentado (permite actualizar `nombre`/`categoria`/`activo`).
- Se agregó el campo `activo` al `POST /api/deportes`, que la ruta ya
  aceptaba pero no estaba documentado.
- Se agregaron dos esquemas reutilizables nuevos en
  `components.schemas`: `Deporte` y `UsuarioDeporte`, con el mismo
  formato con ejemplos que `Usuario`, y se conectaron con `$ref` en las
  respuestas de todos los endpoints de `/api/deportes/*` (antes esos
  endpoints no documentaban la forma de su respuesta, solo una
  descripción en texto).
- Se le agregaron también ejemplos al esquema `Usuario` existente (no
  tenía ninguno) y se corrigió su `enum` de `estado_cuenta`, al que le
  faltaba `pendiente_verificacion` (agregado en la Fase 2, pero no se
  había reflejado ahí todavía).

Se validó que el YAML resultante sigue siendo válido (se parseó con
`pyyaml` sin errores, 55 rutas y los 3 esquemas reutilizables
presentes).
