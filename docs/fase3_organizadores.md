# Fase 3 — Módulo Organizadores

## Bugs corregidos (confirmados con pruebas contra un esquema que replica los CHECK/NOT NULL reales de Neon)

1. **`Organizador.actualizado_en` sin `default`** (mismo patrón que `Usuario`/`Evento`):
   en Neon es `NOT NULL DEFAULT CURRENT_TIMESTAMP`; el modelo no declaraba
   `default`, así que cada `POST /api/organizadores` rompía por `NOT NULL`.
   Se agregó `default=lambda: datetime.now(timezone.utc)`.

2. **Rol de miembro `"editor"` no existe en la BD**: el `CHECK` real de
   `organizador_miembros` solo permite `propietario` / `administrador` /
   `colaborador`. `ROLES_MIEMBRO_ORG` y el default de
   `OrganizadorMiembro.rol` usaban `"editor"` → `POST /<id>/miembros` sin
   especificar rol (el caso más común) siempre fallaba. Ahora usan
   `"colaborador"`.

3. **Valores de `estado_validacion` no coincidían con el `CHECK` real**:
   el modelo usaba `aprobado` / `rechazado` / `suspendido`; Neon exige
   `sin_solicitud` / `pendiente` / `en_revision` / `aprobada` / `rechazada`
   / `revocada`. Esto rompía:
   - `PUT /solicitudes/<id>/revisar` (aprobar o rechazar) — siempre fallaba.
   - `POST /api/organizadores` ponía `"pendiente"` a mano en vez de dejar
     que se use el default real de Neon, `"sin_solicitud"` (un organizador
     recién creado no tiene nada que revisar todavía).
   - `GET /api/organizadores` (listado público) filtraba por `"aprobado"`,
     así que nunca mostraba ningún organizador aunque sí estuvieran
     aprobados.
   - `routes/eventos.py` (creación de evento) comparaba contra
     `"aprobado"` para dejar publicar eventos a un organizador — con el
     valor real (`"aprobada"`) esa comparación nunca era cierta. Se
     corrigió también, aunque el resto del módulo de eventos tiene sus
     propios pendientes (ver el análisis general).

4. **`DocumentoValidacion.archivo_id` es `NOT NULL` en Neon** pero el
   modelo lo permitía `NULL` y las rutas lo mandaban tal cual viniera del
   cliente (`data.get("archivo_id")`, sin validar). Ahora `POST
   /solicitudes/<id>/documentos` y los documentos embebidos en `POST
   /<id>/solicitudes` **exigen `archivo_id`** (400 claro si falta, en vez
   de una excepción de base de datos).

5. **`tipo_documento` no se validaba**: Neon tiene un `CHECK` con un
   catálogo cerrado (`ine`, `curp`, `comprobante_domicilio`, `rfc`,
   `permiso_evento`). Se agregó `TIPOS_DOCUMENTO_VALIDACION` y se valida
   en ambos endpoints que crean `DocumentoValidacion` (400 en vez de
   error de base de datos).

6. **`CuentaCobro.banco`**: el modelo declaraba `String(100)`, Neon es
   `varchar(50)`. Se ajustó a 50 para evitar un error de longitud si
   algún banco tiene un nombre largo.

## Verificación

`test_organizadores.py` (adjunto) monta un esquema SQLite con las mismas
columnas/`NOT NULL`/`CHECK` reales de `organizadores`,
`organizador_miembros`, `solicitudes_validacion`, `documentos_validacion`
y `cuentas_cobro`, levanta la app con `create_app()` y prueba con el
cliente de Flask el flujo completo: crear organizador (queda
`sin_solicitud`), no aparece en el listado público, agregar miembro sin
rol explícito (debe quedar `colaborador`), agregar cuenta de cobro,
enviar solicitud con documento, verificar que el organizador pasa a
`en_revision`, rechazar documento con tipo inválido (400) y sin
`archivo_id` (400), admin lista solicitudes pendientes, aprobar (pasa a
`aprobada` y ya aparece en el listado público), verificar cuenta de
cobro, un usuario ajeno no puede editar el organizador (403), y un
segundo caso de rechazo. Todo pasa.

Como con la Fase 2, esto no sustituye correr contra el Neon real antes
de dar por cerrado el entregable.

## Pendiente relacionado (fuera de este módulo, ya documentado antes)

`usuarios.rol` sigue usando `"admin"` en el código
(`utils/auth.py`, `routes/usuarios.py`) mientras el `CHECK` real de
`usuarios` exige `"administrador"`. No lo toqué aquí porque es del
módulo de usuarios/roles, no de organizadores — pero conviene
resolverlo pronto porque `admin_required` seguirá funcionando
mientras el JWT lleve el claim `"admin"` (no depende de la columna),
así que no rompe organizadores, pero si algún día se crea un admin vía
`POST /api/usuarios/admins` (que sí escribe `rol="admin"` en la tabla
`usuarios`), esa inserción fallará por el `CHECK`.
