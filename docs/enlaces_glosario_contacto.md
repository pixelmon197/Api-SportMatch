# Enlaces útiles, glosario y contacto

## Enlaces útiles

| Recurso | Enlace |
|---|---|
| Documentación interactiva (Swagger UI) | `http://localhost:5000/api/docs` (con la API corriendo en local) |
| Especificación OpenAPI | [`static/openapi.yaml`](../static/openapi.yaml) |
| Repositorio | <https://github.com/pixelmon197/Api-SportMatch> |
| Colección de Postman | Pendiente: no existe. Mientras tanto, Postman puede importar `static/openapi.yaml` directamente. |
| Documento de base de datos | [`entidades_completas.md`](entidades_completas.md) (tablas) y [`relaciones_completas.md`](relaciones_completas.md) (relaciones) |
| Documento de pruebas | Pendiente: no existe. Las pruebas son los scripts de la carpeta [`test/`](../test), uno por módulo. |
| Convenciones de la API | [`convenciones_api.md`](convenciones_api.md) |
| Seguridad | [`seguridad_api.md`](seguridad_api.md) |
| Despliegue y ambientes | [`despliegue_ambientes.md`](despliegue_ambientes.md) y [`pasos_despliegue.md`](pasos_despliegue.md) |
| Versionado y registro de cambios | [`versionado_cambios.md`](versionado_cambios.md) |
| Documentación por módulo | `fase1_analisis.md` a `fase11_revision_swagger.md`, en esta misma carpeta |
| Panel de la base de datos (Neon) | <https://console.neon.tech> |

## Glosario

### Términos técnicos

| Término | Significado |
|---|---|
| API REST | Servicio al que el frontend le pide y le envía datos por HTTP, en formato JSON. |
| Endpoint | Una ruta concreta de la API con su método, por ejemplo `POST /api/auth/login`. |
| JWT | Token firmado que identifica al usuario. Se obtiene al iniciar sesión, dura 8 horas y se envía en la cabecera `Authorization: Bearer <token>`. |
| Claim | Dato que viaja dentro del JWT. Esta API guarda ahí el `rol` del usuario. |
| Hash | Resultado irreversible de transformar un dato. Las contraseñas y los tokens de recuperación se guardan así, nunca en claro. |
| Swagger / OpenAPI | OpenAPI es el archivo que describe la API (`static/openapi.yaml`); Swagger UI es la página que lo muestra y permite probar los endpoints. |
| Blueprint | Forma en que Flask agrupa las rutas de un módulo. Hay uno por archivo en `routes/`. |
| ORM (SQLAlchemy) | Biblioteca que permite trabajar con las tablas como clases de Python (`models/`) en vez de escribir SQL. |
| Neon | Servicio en la nube donde vive la base de datos PostgreSQL del proyecto. |
| `.env` | Archivo local con las claves y la conexión a la base (`DATABASE_URL`). No se sube al repositorio. |
| CORS | Regla del navegador que decide qué sitios web pueden llamar a la API. |
| Borrado suave (soft delete) | El registro no se elimina de la base: solo se marca como eliminado. |
| Paginación | Entregar los listados por páginas en vez de todos los registros de una vez. |
| Seed | Script (`seed.py`) que carga los datos iniciales: una ciudad demo y el primer administrador. |
| Gunicorn | Servidor que ejecuta la API en producción, en lugar de `python app.py`. |
| Migración | Cambio controlado en la estructura de la base de datos. El proyecto todavía no usa una herramienta para esto. |

### Términos del proyecto

| Término | Significado |
|---|---|
| Usuario | Persona registrada en SportMatch. Su rol es `usuario` o `administrador`. |
| Administrador | Usuario con rol `administrador`: gestiona usuarios, catálogos, soporte y auditoría. |
| Organizador | Entidad que publica eventos. Tiene miembros (usuarios), cuentas de cobro y un proceso de validación con documentos. |
| Miembro de organizador | Usuario que pertenece al equipo de un organizador, con un rol dentro de él (por ejemplo, `propietario`). |
| Evento | Actividad deportiva publicada, con deportes, sedes, fechas, categorías, boletos y requisitos. |
| Sede | Lugar donde se realiza un evento. |
| Ruta | Recorrido con sus puntos (salida, meta, puntos intermedios) que puede asociarse a un evento. |
| Inscripción | Registro de un usuario en un evento. |
| Paquete de recuperación | Paquete que el evento ofrece al participante, clasificado por nivel. |
| Valoración | Calificación que un participante da a un evento. |
| Cuestionario | Conjunto de preguntas y opciones que responde el usuario. |
| Reporte | Aviso que hace un usuario sobre un contenido o comportamiento, revisado por un administrador. |
| Ticket | Solicitud de soporte con prioridad, estado y un hilo de mensajes. |
| Auditoría | Registro de las acciones administrativas sensibles: quién, qué cambió, cuándo y desde qué IP. |

## Contacto del equipo

Nombres tomados de los autores del historial de git. Rol y correo quedan
por completar por el propio equipo.

| Nombre | Rol | Correo | GitHub |
|---|---|---|---|
| pixelmon197 | Por definir (autor principal del repositorio) | Por definir | [@pixelmon197](https://github.com/pixelmon197) |
| Omar Yova Aviles | Por definir | Por definir | [@Yoval128](https://github.com/Yoval128) |
