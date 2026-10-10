# Fase 12 — Editar perfil (Swagger vacío) y cómo conseguir el `organizador_id`

## 1. `PUT /api/usuarios/me` no mostraba nada que editar

En `static/openapi.yaml` ese endpoint no tenía `requestBody` en absoluto
(a diferencia de `register`, que sí llevaba su esquema completo) — por
eso Swagger no mostraba ningún campo editable, aunque la ruta en
`routes/usuarios.py` sí acepta varios. Se documentó el cuerpo real:

| Campo | Se puede editar aquí |
|---|---|
| `nombre_completo` | Sí |
| `telefono` | Sí (solo números, 7-15 dígitos) |
| `sexo` | Sí (`masculino`/`femenino`/`otro`/`prefiero_no_decir`) |
| `idioma` | Sí |
| `zona_horaria` | Sí |
| `ciudad_id` | Sí (debe ser una ciudad existente) |
| `correo`, `nombre_usuario`, `fecha_nacimiento` | **No** — son datos de identidad; cambiarlos necesitaría su propio flujo (verificación de correo, etc.), que todavía no existe |
| `rol`, `estado_cuenta` | **No** — eso solo lo cambia un admin (`PUT /usuarios/{id}/rol` y `/estado`) |

No era un bug de la API — la API ya rechazaba esos tres campos
correctamente si se mandaban (simplemente los ignora, no truena); el
problema era solo que la documentación no explicaba nada de esto.

## 2. `organizador_id` en `POST /api/eventos`: de dónde sale

Todo evento pertenece a un organizador (ver Fase 4). El flujo completo:

1. `POST /api/organizadores` — crea tu perfil de organizador. La
   respuesta trae el `id` que vas a necesitar.
2. (Si no eres admin) ese organizador nace en `sin_solicitud`: para
   poder crear eventos primero hay que enviarlo a revisión con
   `POST /api/organizadores/{id}/solicitudes` y que un admin lo apruebe
   con `PUT /api/organizadores/solicitudes/{solicitud_id}/revisar`.
3. Ya aprobado (o si quien crea el evento es admin, que no necesita
   aprobación), se manda ese `id` como `organizador_id` en
   `POST /api/eventos`.

El problema real que encontré: **no había ninguna forma de recuperar tu
propio `organizador_id` después** si no lo guardaste de la respuesta del
paso 1. `GET /api/organizadores` (el listado público) solo muestra los
`aprobada`, así que mientras el tuyo estuviera en `sin_solicitud` o
`en_revision` **no aparecía en ningún lado** — no había 404 ni error,
simplemente no estaba en la lista y no existía otra ruta para buscarlo.

### Se agregó `GET /api/organizadores/me`

Nuevo endpoint (autenticado) que regresa tu propio organizador —
cualquiera que sea su `estado_validacion` — o un 404 claro
("Todavía no tienes un perfil de organizador") si todavía no has creado
uno. Con esto ya hay una forma directa de resolver justo lo que se
preguntó: "no tengo cómo saber el `organizador_id`".

## Documentación (`static/openapi.yaml`)

- `PUT /api/usuarios/me`: `requestBody` completo + nota explicando qué
  no se puede cambiar ahí y por qué.
- Nuevo esquema reutilizable `Organizador` (mismo estilo que
  `Usuario`/`Deporte`), con su sub-objeto `miembros` para las respuestas
  de detalle.
- Conectado con `$ref` en `GET/POST /api/organizadores`,
  `GET/PUT /api/organizadores/{id}` y el nuevo `GET /api/organizadores/me`.
- Se corrigió el resumen de `POST /api/organizadores`, que todavía decía
  que el organizador "queda pendiente" (texto viejo de antes de la
  Fase 3; el valor real es `sin_solicitud`), y se agregó una nota en la
  respuesta 201 recordando guardar el `id` (o usar `GET .../me` después).

## Verificación

Nuevos casos en `test_organizadores.py`: Ana encuentra su propio
`organizador_id` por `GET /me` mientras todavía no está aprobado, un
usuario sin perfil de organizador recibe 404 (no 500), y cada quien ve
el suyo y no el de otro. Las 9 pruebas de todas las fases pasan.
