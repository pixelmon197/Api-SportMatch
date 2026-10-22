# Api-SportMatch — Resumen del proyecto y catálogo de endpoints

Última actualización: Fase 16 (pagos). Este documento resume
todo el trabajo de revisión/reparación hecho sobre la API contra el
esquema real de Neon (`Neon.sql`), y cataloga **todos los endpoints
disponibles hasta el momento**.

---

## 1. Resumen de las fases realizadas

| Fase | Módulo | Qué se encontró y corrigió |
|---|---|---|
| 1 | Análisis inicial | Comparación completa modelo-por-modelo contra `Neon.sql`: nombres de columna que no coinciden, tablas duplicadas (una vieja "fantasma" y una vigente), catálogos de valores (`CHECK`) distintos a los que usaba el código, y columnas `id` inventadas en tablas con llave primaria compuesta. |
| 2 | Login / Register / Recuperar contraseña | `contrasena_hash`/`fecha_de_nacimiento` no existían como tales en Neon; `actualizado_en` sin default rompía cada registro; `nombre_usuario` sin normalizar a minúsculas; `sexo` sin validar; tabla de tokens apuntando a la vieja `tockens_verificacion`; **no existían** los endpoints de olvidé/restablecer contraseña — se crearon. |
| 3 | Organizadores | `actualizado_en` sin default; rol de miembro `"editor"` inexistente (real: `colaborador`); `estado_validacion` con vocabulario incorrecto (`aprobado`→`aprobada`, faltaba `sin_solicitud`); `archivo_id`/`tipo_documento` de documentos de validación sin exigir/validar. |
| 4 | Eventos | `actualizado_en` sin default; `organizador_id` permitía `NULL` (Neon lo exige siempre); `EventoDeporte` con un `id` que no existe (PK real compuesta); tablas legacy de fechas/requisitos; **catálogos completamente distintos** de `tipo`, `dificultad`, tipo de sede y tipo de boleto. |
| 5 | Rutas | `EventoRuta` con `id` inventado y sin la columna `evento_id` (PK real compuesta + FK compuesta a categoría); catálogo de `tipo` de punto de ruta distinto; `dificultad` sin validar; `distancia_m`/`desnivel_positivo_m` son enteros en Neon, no decimales. |
| 6 | Cuestionarios | `OpcionRespuesta.codigo_id` no existe (la columna real es `codigo`); catálogo de `tipo` de pregunta incompleto; tabla legacy `respuesta_usuario`; preguntas de opción múltiple perdían respuestas por un bug de sobre-escritura. |
| 7 | Inscripciones | **Catálogo de `estado` completamente distinto** (`pendiente`→`pendiente_pago`, `confirmada`→`inscrito`, `cancelada`→`cancelado`, `completada`→`completado`); `tiempo_oficial` es tipo `time`, no texto; tabla legacy de paquetes de recuperación; `ValoracionEvento` con `id` inventado (la PK real es `inscripcion_id`). |
| 8 | Deportes | Tabla legacy `usuarios_deportes` (correcta: `usuario_deportes`); se actualizó también la documentación OpenAPI con ejemplos. |
| 9 | Soporte | `categoria` de ticket obligatoria en Neon pero no exigida; columnas más cortas de lo asumido (`motivo`, `tipo_entidad`, `accion_tomada`, `categoria` — Postgres rechaza en vez de truncar); tabla legacy `ticket_mensaje`. |
| 10 | Administradores | El código entero usaba `"admin"` para el rol; el `CHECK` real exige `"administrador"`. Corregido en el modelo, en `utils/auth.py` y en cada ruta que comparaba contra ese valor; `crear_admin` tenía además el mismo bug de `fecha_nacimiento`/`sexo` que ya se había corregido en `register()`. |

**Patrón que se repitió una y otra vez:** Neon tiene pares de tablas
donde una es un remanente de un rediseño (sin `CHECK`, sin
`ON DELETE CASCADE`) y la otra es la vigente. Varios modelos apuntaban a
la vieja: `tockens_verificacion`, `eventos_fechas`, `eventos_requisitos`,
`respuesta_usuario`, `paquete_recuperacion`, `usuarios_deportes`,
`ticket_mensaje`. Todos corregidos.

Cada fase se probó con un script Python que monta un esquema SQLite
replicando las columnas, `CHECK`, `UNIQUE` y llaves foráneas (incluidas
las compuestas) reales de Neon, y ejercita los endpoints de punta a
punta con el cliente de pruebas de Flask. Los 9 scripts
(`test_neon_like.py`, `test_organizadores.py`, `test_eventos.py`,
`test_rutas.py`, `test_cuestionarios.py`, `test_inscripciones.py`,
`test_deportes.py`, `test_soporte.py`, `test_administradores.py`) se
re-corren juntos en cada fase nueva para asegurar que no hay
regresiones.

| 11-12 | Revisión del Swagger | Teléfono solo números, `ciudad_id` validado, `organizador_id` obligatorio documentado, 23 endpoints de eventos documentados, `GET /api/organizadores/me`, cuerpo de `PUT /api/usuarios/me`. |
| 13 | Archivos | Nuevo módulo para subir imágenes, videos, PDF, GPX y audio (`/api/archivos`); `portada_id`, `logo_id`, `gpx_archivo_id` y `archivo_id` pasan a ser llaves foráneas reales. Ver `docs/fase13_archivos.md`. |
| 14 | Perfiles | Nuevo módulo `/api/perfiles`: ver/editar mi perfil, ubicación, y ver el de otros respetando visibilidad (público/amigos/privado), amistad y bloqueos. `perfiles` y `bloqueos` no tienen `id` propio. Ver `docs/fase14_perfiles.md`. |
| 15 | Seguidores, amistades y bloqueos | 17 endpoints nuevos (`/api/seguidores`, `/api/amistades`, `/api/bloqueos`). Bloquear borra seguimientos y amistad y oculta el perfil (404). Los perfiles ahora traen `contadores` y `relacion`. `seguidores` y `bloqueos` no tienen `id` propio. Ver `docs/fase15_seguidores_amistades_bloqueos.md`. |
| 16 | Pagos | 25 endpoints nuevos: pagos (tarjeta simulada, transferencia/efectivo confirmados por admin, eventos gratis), reembolsos (totales), comisiones con vigencia, cupones y liquidaciones a organizadores. Neon no tiene `CHECK` de catálogo aquí, así que la API los define. `pagos_inscripciones` no tiene `id` propio. Ver `docs/fase16_pagos.md`. |

### Pendiente conocido (no bloquea nada hoy)

- `usuarios.firebase_uid` (nuevo en Neon2.sql) todavía no se mapea: solo hará falta si se agrega inicio de sesión con Firebase.
- Módulos de Neon sin endpoints todavía: comunidades y tarjetas de conexión, créditos y puntos, notificaciones, marketplace, publicidad, gamificación y música/video (ver la respuesta de la Fase 13).
- `AceptacionLegal` y `Dispositivo` tienen modelo pero **ningún endpoint
  implementado todavía**; sus columnas no se han contrastado a fondo
  contra Neon porque no hay código que las use.

---

## 2. Catálogo completo de endpoints

Niveles de acceso: **Público** (sin token) · **Autenticado** (cualquier
usuario con sesión) · **Dueño/Gestión** (autenticado + dueño del
recurso o miembro con permisos) · **Admin** (`rol="administrador"`).

### Auth — `/api/auth`

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| POST | `/api/auth/register` | Público | Registro (exige `fecha_nacimiento` y `sexo`) |
| POST | `/api/auth/login` | Público | Inicia sesión, regresa JWT |
| POST | `/api/auth/olvide-contrasena` | Público | Genera token de recuperación (Fase 2) |
| POST | `/api/auth/restablecer-contrasena` | Público | Cambia la contraseña con el token (Fase 2) |
| GET | `/api/auth/me` | Autenticado | Datos del usuario en sesión |

### Usuarios — `/api/usuarios`

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| PUT | `/api/usuarios/me` | Autenticado | Editar mi propio perfil |
| PUT | `/api/usuarios/me/password` | Autenticado | Cambiar mi contraseña |
| GET | `/api/usuarios` | Admin | Listar usuarios (filtros `rol`, `estado_cuenta`, `q`) |
| GET | `/api/usuarios/{usuario_id}` | Admin | Ver un usuario |
| PUT | `/api/usuarios/{usuario_id}/rol` | Admin | Cambiar rol (`usuario`/`organizador`/`administrador`) |
| PUT | `/api/usuarios/{usuario_id}/estado` | Admin | Cambiar `estado_cuenta` |
| POST | `/api/usuarios/admins` | Admin | Crear otro administrador |

### Deportes — `/api/deportes`

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/api/deportes` | Público | Catálogo de deportes (`?incluir_inactivos=1` para admin) |
| GET | `/api/deportes/{deporte_id}` | Público | Ver un deporte |
| POST | `/api/deportes` | Admin | Crear deporte |
| PUT | `/api/deportes/{deporte_id}` | Admin | Editar deporte |
| DELETE | `/api/deportes/{deporte_id}` | Admin | Desactivar (borrado suave) |
| GET | `/api/deportes/me` | Autenticado | Mis deportes |
| POST | `/api/deportes/me` | Autenticado | Agregar un deporte a mi perfil |
| PUT | `/api/deportes/me/{deporte_id}` | Autenticado | Cambiar nivel / marcar principal |
| DELETE | `/api/deportes/me/{deporte_id}` | Autenticado | Quitar un deporte de mi perfil |

### Organizadores — `/api/organizadores`

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/api/organizadores` | Público | Listar organizadores aprobados (`?estado_validacion=` para admin) |
| GET | `/api/organizadores/{id}` | Público | Ver un organizador |
| POST | `/api/organizadores` | Autenticado | Crear mi perfil de organizador (queda `sin_solicitud`) |
| PUT | `/api/organizadores/{id}` | Dueño/Gestión | Editar organizador |
| DELETE | `/api/organizadores/{id}` | Dueño/Gestión | Eliminar (borrado suave) |
| POST | `/api/organizadores/{id}/miembros` | Dueño/Gestión | Agregar miembro al equipo |
| DELETE | `/api/organizadores/{id}/miembros/{usuario_id}` | Dueño/Gestión | Quitar miembro |
| GET | `/api/organizadores/{id}/cuentas-cobro` | Dueño/Gestión | Listar cuentas de cobro |
| POST | `/api/organizadores/{id}/cuentas-cobro` | Dueño/Gestión | Agregar cuenta de cobro |
| PUT | `/api/organizadores/cuentas-cobro/{cuenta_id}/verificar` | Admin | Verificar cuenta de cobro |
| DELETE | `/api/organizadores/cuentas-cobro/{cuenta_id}` | Dueño/Gestión | Eliminar cuenta de cobro |
| POST | `/api/organizadores/{id}/solicitudes` | Dueño/Gestión | Enviar a revisión (con documentos opcionales) |
| POST | `/api/organizadores/solicitudes/{solicitud_id}/documentos` | Dueño/Gestión | Agregar documento a una solicitud |
| GET | `/api/organizadores/solicitudes` | Admin | Bandeja de solicitudes pendientes |
| PUT | `/api/organizadores/solicitudes/{solicitud_id}/revisar` | Admin | Aprobar / rechazar |

### Eventos — `/api/eventos`

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/api/eventos` | Público | Listar eventos publicados (filtros varios) |
| GET | `/api/eventos/{id}` | Público | Ver un evento |
| GET | `/api/eventos/slug/{slug}` | Público | Ver un evento por slug |
| POST | `/api/eventos` | Autenticado | Crear evento (con deportes/requisitos/sedes/fechas/categorías/boletos embebidos) |
| PUT | `/api/eventos/{id}` | Dueño/Gestión | Editar evento |
| DELETE | `/api/eventos/{id}` | Dueño/Gestión | Cancelar (borrado suave) |
| POST | `/api/eventos/{id}/deportes` | Dueño/Gestión | Asociar un deporte |
| DELETE | `/api/eventos/{id}/deportes/{deporte_id}` | Dueño/Gestión | Quitar un deporte |
| POST | `/api/eventos/{id}/requisitos` | Dueño/Gestión | Agregar requisito |
| PUT | `/api/eventos/requisitos/{requisito_id}` | Dueño/Gestión | Editar requisito |
| DELETE | `/api/eventos/requisitos/{requisito_id}` | Dueño/Gestión | Eliminar requisito |
| POST | `/api/eventos/{id}/sedes` | Dueño/Gestión | Agregar sede |
| PUT | `/api/eventos/sedes/{sede_id}` | Dueño/Gestión | Editar sede |
| DELETE | `/api/eventos/sedes/{sede_id}` | Dueño/Gestión | Eliminar sede |
| POST | `/api/eventos/{id}/fechas` | Dueño/Gestión | Agregar fecha |
| PUT | `/api/eventos/fechas/{fecha_id}` | Dueño/Gestión | Editar fecha |
| DELETE | `/api/eventos/fechas/{fecha_id}` | Dueño/Gestión | Eliminar fecha |
| POST | `/api/eventos/{id}/categorias` | Dueño/Gestión | Agregar categoría |
| PUT | `/api/eventos/categorias/{categoria_id}` | Dueño/Gestión | Editar categoría |
| DELETE | `/api/eventos/categorias/{categoria_id}` | Dueño/Gestión | Eliminar categoría |
| POST | `/api/eventos/categorias/{categoria_id}/boletos` | Dueño/Gestión | Agregar tipo de boleto |
| PUT | `/api/eventos/boletos/{boleto_id}` | Dueño/Gestión | Editar boleto |
| DELETE | `/api/eventos/boletos/{boleto_id}` | Dueño/Gestión | Eliminar boleto |

### Rutas — `/api/rutas`

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/api/rutas` | Público | Listar rutas públicas |
| GET | `/api/rutas/{id}` | Público | Ver una ruta (con sus puntos) |
| POST | `/api/rutas` | Autenticado | Crear ruta (con puntos embebidos) |
| PUT | `/api/rutas/{id}` | Dueño/Gestión | Editar ruta |
| DELETE | `/api/rutas/{id}` | Dueño/Gestión | Eliminar ruta |
| POST | `/api/rutas/{id}/puntos` | Dueño/Gestión | Agregar punto a la ruta |
| DELETE | `/api/rutas/puntos/{punto_id}` | Dueño/Gestión | Eliminar punto |
| POST | `/api/rutas/categorias/{categoria_id}/rutas` | Dueño/Gestión | Ligar una ruta a una categoría de evento |
| GET | `/api/rutas/categorias/{categoria_id}/rutas` | Público | Listar rutas ligadas a una categoría |
| DELETE | `/api/rutas/eventos-rutas/{evento_id}/{ruta_id}` | Dueño/Gestión | Desligar ruta de evento |

### Cuestionarios — `/api/cuestionarios`

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/api/cuestionarios` | Público | Listar cuestionarios activos |
| GET | `/api/cuestionarios/{codigo}` | Público | Ver un cuestionario con sus preguntas |
| POST | `/api/cuestionarios` | Admin | Crear cuestionario |
| PUT | `/api/cuestionarios/{id}` | Admin | Editar cuestionario |
| POST | `/api/cuestionarios/{id}/preguntas` | Admin | Agregar pregunta (con opciones embebidas) |
| PUT | `/api/cuestionarios/preguntas/{pregunta_id}` | Admin | Editar pregunta |
| DELETE | `/api/cuestionarios/preguntas/{pregunta_id}` | Admin | Eliminar pregunta |
| POST | `/api/cuestionarios/preguntas/{pregunta_id}/opciones` | Admin | Agregar opción de respuesta |
| DELETE | `/api/cuestionarios/opciones/{opcion_id}` | Admin | Eliminar opción |
| POST | `/api/cuestionarios/{codigo}/responder` | Autenticado | Responder (soporta opción múltiple) |
| GET | `/api/cuestionarios/me/respuestas` | Autenticado | Ver mis respuestas |

### Inscripciones y calendario — prefijo `/api`

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/api/eventos/{id}/paquetes` | Público | Listar paquetes de recuperación de un evento |
| POST | `/api/eventos/{id}/paquetes` | Dueño/Gestión | Crear paquete (nivel básico/medio/premium) |
| PUT | `/api/paquetes/{paquete_id}` | Dueño/Gestión | Editar paquete |
| DELETE | `/api/paquetes/{paquete_id}` | Dueño/Gestión | Desactivar paquete |
| POST | `/api/inscripciones` | Autenticado | Inscribirse a una categoría (o entrar a lista de espera) |
| GET | `/api/inscripciones/me` | Autenticado | Mis inscripciones |
| GET | `/api/inscripciones/{id}` | Dueño/Admin | Ver una inscripción |
| PUT | `/api/inscripciones/{id}/cancelar` | Dueño/Admin | Cancelar (promueve a quien sigue en lista de espera) |
| PUT | `/api/inscripciones/{id}/estado` | Dueño/Gestión | Cambiar estado manualmente |
| PUT | `/api/inscripciones/{id}/resultado` | Dueño/Gestión | Registrar asistencia/tiempo/posición |
| GET | `/api/eventos/{id}/inscripciones` | Dueño/Gestión | Listar inscritos a un evento |
| POST | `/api/inscripciones/{id}/valoracion` | Dueño (de la inscripción) | Valorar el evento (requiere estado `completado`) |
| GET | `/api/eventos/{id}/valoraciones` | Público | Listar valoraciones de un evento |
| PUT | `/api/valoraciones/{inscripcion_id}/responder` | Dueño/Gestión | El organizador responde una reseña |
| GET | `/api/usuarios/me/calendario` | Autenticado | Mi calendario de fechas guardadas |
| POST | `/api/usuarios/me/calendario` | Autenticado | Agregar una fecha a mi calendario |
| DELETE | `/api/usuarios/me/calendario/{fecha_id}` | Autenticado | Quitar una fecha de mi calendario |

### Archivos — `/api/archivos`

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| POST | `/api/archivos` | Autenticado | Subir imagen, video, PDF, GPX o audio (`multipart/form-data`); regresa el `id` y la `url` |
| GET | `/api/archivos/{archivo_id}` | Público | Ver los datos de un archivo |
| DELETE | `/api/archivos/{archivo_id}` | Dueño/Admin | Eliminar (borrado suave) |

Además, en Organizadores: `GET /api/organizadores/me` (Autenticado) regresa mi propio perfil y su `organizador_id`.

### Perfiles — `/api/perfiles`

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/api/perfiles/me` | Autenticado | Mi usuario + perfil + deportes |
| PUT | `/api/perfiles/me` | Autenticado | Editar biografía, avatar, portada y privacidad |
| PUT | `/api/perfiles/me/ubicacion` | Autenticado | Guardar mi ubicación |
| DELETE | `/api/perfiles/me/ubicacion` | Autenticado | Borrar mi ubicación |
| GET | `/api/perfiles/{usuario_id}` | Público* | Ver el perfil de otro usuario |
| GET | `/api/perfiles/usuario/{nombre_usuario}` | Público* | Ver un perfil por nombre de usuario |

\* Sin token solo si el perfil es público; con token se reconoce a los amigos.

### Seguidores — `/api/seguidores`

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| POST | `/api/seguidores/{usuario_id}` | Autenticado | Seguir a un usuario |
| DELETE | `/api/seguidores/{usuario_id}` | Autenticado | Dejar de seguir |
| GET | `/api/seguidores/me/seguidores` | Autenticado | Quiénes me siguen |
| GET | `/api/seguidores/me/siguiendo` | Autenticado | A quiénes sigo |
| GET | `/api/seguidores/{usuario_id}/seguidores` | Público* | Seguidores de otro usuario |
| GET | `/api/seguidores/{usuario_id}/siguiendo` | Público* | A quiénes sigue otro usuario |

### Amistades — `/api/amistades`

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/api/amistades` | Autenticado | Mis amigos |
| POST | `/api/amistades/solicitudes` | Autenticado | Enviar solicitud de amistad |
| GET | `/api/amistades/solicitudes/recibidas` | Autenticado | Solicitudes que me enviaron |
| GET | `/api/amistades/solicitudes/enviadas` | Autenticado | Solicitudes que envié |
| PUT | `/api/amistades/solicitudes/{id}/aceptar` | Autenticado | Aceptar (solo quien la recibió) |
| PUT | `/api/amistades/solicitudes/{id}/rechazar` | Autenticado | Rechazar (solo quien la recibió) |
| DELETE | `/api/amistades/solicitudes/{id}` | Autenticado | Cancelar una que envié |
| DELETE | `/api/amistades/amigos/{usuario_id}` | Autenticado | Eliminar un amigo |

### Bloqueos — `/api/bloqueos`

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/api/bloqueos` | Autenticado | Usuarios que he bloqueado |
| POST | `/api/bloqueos/{usuario_id}` | Autenticado | Bloquear (borra seguimientos y amistad) |
| DELETE | `/api/bloqueos/{usuario_id}` | Autenticado | Desbloquear |

\* Sin token solo si el perfil es público.

### Pagos — prefijo `/api`

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| POST | `/api/pagos/cotizar` | Autenticado | Cuánto costaría pagar esas inscripciones (con cupón) |
| POST | `/api/pagos` | Autenticado | Pagar una o varias inscripciones |
| GET | `/api/pagos/me` | Autenticado | Mis pagos |
| GET | `/api/pagos` | Admin | Todos los pagos |
| GET | `/api/pagos/{id}` | Dueño/Admin | Ver un pago |
| POST | `/api/pagos/{id}/simular-pago` | Dueño | Simular la pasarela de tarjeta (solo pruebas) |
| PUT | `/api/pagos/{id}/confirmar` | Admin | Confirmar un pago (p. ej. una transferencia) |
| PUT | `/api/pagos/{id}/cancelar` | Dueño/Admin | Cancelar un pago pendiente |
| GET | `/api/organizadores/{id}/pagos` | Gestión/Admin | Lo cobrado por un organizador, con resumen |

### Reembolsos

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| POST | `/api/pagos/{id}/reembolsos` | Dueño/Admin | Pedir un reembolso (total) |
| GET | `/api/reembolsos/me` | Autenticado | Mis reembolsos |
| GET | `/api/reembolsos` | Admin | Bandeja de reembolsos |
| PUT | `/api/reembolsos/{id}/aprobar` | Admin | Aprobar (cancela las inscripciones) |
| PUT | `/api/reembolsos/{id}/rechazar` | Admin | Rechazar |

### Liquidaciones, comisiones y cupones

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| POST | `/api/liquidaciones` | Admin | Armar la liquidación de un organizador |
| GET | `/api/liquidaciones` | Admin | Todas las liquidaciones |
| GET | `/api/liquidaciones/{id}` | Gestión/Admin | Detalle |
| PUT | `/api/liquidaciones/{id}/pagar` | Admin | Registrar el pago al organizador |
| GET | `/api/organizadores/{id}/liquidaciones` | Gestión/Admin | Liquidaciones de un organizador |
| GET | `/api/comisiones/vigente` | Autenticado | Comisión vigente de la plataforma |
| GET/POST | `/api/comisiones` | Admin | Historial / definir una comisión |
| POST | `/api/cupones` | Admin/Organizador | Crear un cupón |
| GET | `/api/cupones` | Admin/Organizador | Listar cupones |
| PUT | `/api/cupones/{id}` | Admin/Organizador | Editar un cupón |

### Soporte — prefijo `/api`

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| POST | `/api/reportes` | Autenticado | Reportar contenido o a un usuario |
| GET | `/api/reportes/me` | Autenticado | Mis reportes enviados |
| GET | `/api/reportes` | Admin | Bandeja de moderación |
| GET | `/api/reportes/{id}` | Dueño/Admin | Ver un reporte |
| PUT | `/api/reportes/{id}` | Admin | Moderar (cambia estado, registra en auditoría) |
| POST | `/api/tickets` | Autenticado | Abrir ticket de soporte |
| GET | `/api/tickets/me` | Autenticado | Mis tickets |
| GET | `/api/tickets` | Admin | Bandeja de tickets |
| GET | `/api/tickets/{id}` | Dueño/Admin | Ver ticket con mensajes (dueño no ve internos) |
| POST | `/api/tickets/{id}/mensajes` | Dueño/Admin | Agregar mensaje al ticket |
| PUT | `/api/tickets/{id}` | Admin | Asignar / priorizar / cerrar |
| GET | `/api/admin/auditoria` | Admin | Bitácora de auditoría del sistema |

---

## 3. Cómo verificar

Cada fase dejó su propio script de prueba (`test_*.py`) que no requiere
una base de datos real: monta un esquema SQLite con las mismas
restricciones de Neon y prueba los endpoints con el cliente de Flask.
Para correr todo junto:

```bash
python3 test_neon_like.py
python3 test_organizadores.py
python3 test_eventos.py
python3 test_rutas.py
python3 test_cuestionarios.py
python3 test_inscripciones.py
python3 test_deportes.py
python3 test_soporte.py
python3 test_administradores.py
```

Antes de dar por cerrado el entregable, se recomienda correr `flask run`
con el `DATABASE_URL` real de Neon y repetir manualmente al menos los
flujos principales (registro, login, crear organizador → evento →
inscripción) — estas pruebas replican los `CHECK`/llaves reales, pero no
sustituyen una corrida final contra la base de datos real.
