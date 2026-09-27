# Fase 10 — Administradores (rol `usuario.rol`)

## El bug: un mismatch de una sola palabra, pero regado por todo el proyecto

`usuarios.rol` en Neon tiene `CHECK (rol IN ('usuario','organizador','administrador'))`.
Todo el código, desde el primer día, usó la palabra **`"admin"`** para
referirse a un administrador — en el JWT, en las comparaciones de
permisos, y al crear uno nuevo. Como el registro normal siempre pone
`rol="usuario"` (que sí es válido), esto nunca se notó hasta ahora: el
único lugar que de verdad intenta escribir `rol="admin"` en la base es
`POST /api/usuarios/admins`, que habría fallado por el `CHECK` en cuanto
se probara contra Neon real.

Pero el problema no termina ahí: **todo el sistema de permisos de admin
en el resto de la app compara contra ese mismo string `"admin"`**, así
que si alguna vez se hubiera insertado un administrador a mano
directamente en Neon (con el valor correcto, `"administrador"`, porque
es lo único que el `CHECK` permite), ese administrador **no habría
podido usar ninguno de sus privilegios** — `admin_required`,
`puede_gestionar_organizador`, `puede_gestionar_evento`, y los checks de
"admin o dueño" en eventos, inscripciones, rutas y soporte, todos
comparaban contra `"admin"`, no contra `"administrador"`.

## Cambios

Se reemplazó `"admin"` por `"administrador"` en cada lugar donde
representa el **rol de usuario** (con cuidado de no tocar cosas que
comparten la palabra pero son otra cosa: el rol de miembro de
organizador ya usaba `"administrador"` correctamente desde la Fase 3, y
el decorador `admin_required` conserva su nombre en Python, solo cambió
lo que exige):

- `models/usuario.py`: `ROLES_VALIDOS` ahora es
  `("usuario", "organizador", "administrador")` — igual al `CHECK` real.
  Se agregó `"organizador"` aunque hoy la app no lo asigna solo (ser
  organizador se maneja con un perfil aparte en la tabla `organizadores`,
  no cambiando el rol base), porque la base sí lo permite y conviene que
  un admin pueda asignarlo manualmente vía `PUT /usuarios/<id>/rol` si
  hiciera falta.
- `utils/auth.py`: `admin_required`, `usuario_autenticado_required`,
  `puede_gestionar_organizador` y `puede_gestionar_evento` ahora exigen
  `"administrador"`.
- `routes/eventos.py`, `routes/inscripciones.py`, `routes/rutas.py`,
  `routes/soporte.py`: todas las comparaciones `usuario.rol == "admin"` /
  `!= "admin"` corregidas.
- `routes/usuarios.py` (`crear_admin`): además del rol, este endpoint
  tenía **el mismo bug que ya se había corregido en `/auth/register` en
  la Fase 2** y que nunca se replicó aquí — no pedía `fecha_nacimiento`
  ni `sexo`, que Neon exige en cuanto se fija `registro_completo_en`
  (como este endpoint sí lo fija, cada alta de administrador habría
  violado ese `CHECK` también). Se igualó a `register()`: ahora exige
  `fecha_nacimiento` y `sexo`, valida `sexo` contra el catálogo real, y
  normaliza/valida la longitud de `nombre_usuario`.
- `seed.py`: el admin de arranque también usaba `rol="admin"`.

## Verificación

`test_administradores.py` (adjunto) monta un esquema con el `CHECK` real
de `usuarios.rol` y prueba: un usuario normal no puede crear un admin
(403), un admin real sí puede y el registro queda con `rol="administrador"`
(ya no viola el `CHECK`), crear un admin sin `fecha_nacimiento` falla
(400, misma regla que `/auth/register`), `cambiar_rol` ya no acepta el
valor viejo `"admin"` pero sí acepta `"organizador"` (400/200), filtrar
usuarios por `rol=administrador`, y que los permisos de admin sigan
funcionando correctamente en otro módulo (deportes) tanto para permitir
como para bloquear. Todo pasa.

Como este cambio es transversal, también se **actualizaron y
re-corrieron** los arneses de prueba de las Fases 3, 4, 6, 7, 8 y 9
(`test_organizadores.py`, `test_eventos.py`, `test_cuestionarios.py`,
`test_inscripciones.py`, `test_deportes.py`, `test_soporte.py`), que
simulaban al admin con el rol viejo `"admin"` tanto en el JWT como en
una fila insertada directo por SQL — no era un bug del código, sino que
las pruebas mismas quedaron desactualizadas por este fix y había que
alinearlas. Las 9 pruebas de todas las fases pasan juntas sin
regresiones.

## Documentación (`static/openapi.yaml`)

Se corrigieron los tres lugares que documentaban `rol` con el catálogo
viejo (`[usuario, admin]` → `[usuario, organizador, administrador]`):
el schema reutilizable `Usuario`, el filtro de `GET /api/usuarios`, y el
body de `PUT /usuarios/<id>/rol`. También se completó el `requestBody`
de `POST /api/usuarios/admins` (le faltaban `fecha_nacimiento` y `sexo`,
ahora obligatorios), se corrigió un `enum` de `estado_cuenta` que
todavía no tenía `pendiente_verificacion` en el listado de usuarios, y
se corrigió el `rol` de miembro de organizador en
`POST /organizadores/<id>/miembros`, que documentaba `"editor"` (el
valor viejo de la Fase 3) en vez de `"colaborador"`.
