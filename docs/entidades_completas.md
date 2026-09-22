
## Ciudades
  - id: INTEGER PK
  - nombre:
  - estado:
  - pais:
  - codigo_postal:

## Entity1

## Deportes
  - id: INTEGER PK
  - nombre:
  - categoria:
  - activo:

## usuarios
  - id: INTEGER PK
  - nombre_completo:
  - correo:
  - constrasena:
  - fecha_de_nacimiento:
  - sexo:
  - rol:
  - estado_cuenta:
  - correo_verificado_en:
  - registro_completo_en:
  - ultimo_acceso:
  - nombre_usuario:
  - telefono:
  - ciudad_id:  FK
  - idioma:
  - zona_horaria:
  - codigo_referido:
  - creado_en:
  - actualizado_en:
  - eliminado_en:

## cuentas_externas
  - id: INTEGER PK
  - usuario_id:  FK
  - proveedor:
  - id_externo:
  - correo_proveedor:
  - creado_en:

## Dispositivos
  - id: INTEGER PK
  - usuario_id:  FK
  - plataforma:
  - token_push:
  - modelo:
  - activio:
  - ultimo_uso_en:
  - creado_en:

## Tockens_verificacion
  - id: INTEGER PK
  - usuario_id:  FK
  - tipo:
  - token_hash:
  - correo_nuevo:
  - creado_en:
  - expira_en:
  - usado_en:

## aceptaciones_legales
  - id: INTEGER PK
  - usuario_id:  FK
  - documento:
  - version:
  - aceptado_en:
  - ip:

## archivos
  - id: INTEGER PK
  - propietario_id:  FK
  - tipo:
  - url:
  - nombre_original:
  - tipo_mime:
  - tamano_bytes:
  - ancho_px:
  - alto_px:
  - duracion_segundos:
  - subido_en:
  - eliminado_en:

## perfiles
  - id: INTEGER PK
  - usuario_id:  FK
  - biografia:
  - avatar_id:
  - portada_id:
  - visibilidad_perfil:
  - visibilidad_ubicacion:
  - quien_puede_escribir:
  - aparecer_en_cercanos:
  - latitud:
  - longitud:
  - ubicacion_actualizada_en:
  - actualizada_en:

## Seguidores
  - id: INTEGER PK
  - seguidor_id:  FK
  - seguido_id:  FK
  - creado_en:

## amistades
  - id: INTEGER PK
  - usuario_id:  FK
  - amigo_id:  FK
  - estado:
  - creado_en:
  - respondida_en:

## bloqueos
  - id:
  - bloqueador_id: INTEGER FK
  - bloqueado_id: INTEGER FK
  - creado_en:

## comunidades
  - id: INTEGER PK
  - nombre:
  - descripcion:
  - deporte_id:  FK
  - ciudad_id:  FK
  - logo_id:  FK
  - portada_id:  FK
  - creador_id:  FK
  - es_publica:
  - chat_acgtivo:
  - creado_en:
  - eliminado_en:

## comunidad_miembro
  - comunidad_miembro: INTEGER FK
  - usuario_id: INTEGER FK
  - rol:
  - unido_en:

## tarjetas_conexion
  - id: INTEGER PK
  - usuario_id:  FK
  - deporte_id:  FK
  - ciudad_id:  FK
  - imagen_id:  FK
  - titulo:
  - descripcion:
  - activa:
  - expira_en:
  - creado_en:

## tarjeta _solcitantes
  - id: INTEGER PK
  - tarjeta_id:  FK
  - solicitante_id:  FK
  - estado:
  - mensaje:
  - creado_en:
  - respondida_en:

## cuestionarios
  - id: INTEGER PK
  - codigo:
  - titulo:
  - descripcion:
  - activo:
  - creado_en:

## preguntas
  - id: INTEGER PK
  - cuestionario_id:
  - codigo:
  - texto:
  - tipo:
  - obligatoria:
  - orden:
  - activa:

## opciones_respuesta
  - id: INTEGER PK
  - pregunta_id:  FK
  - deporte_id:  FK
  - codigo_id:
  - texto:
  - orden:

## respuesta_usuario
  - id: INTEGER PK
  - usuario_id:  FK
  - pregunta_id:  FK
  - opcion_id:  FK
  - respuesta_texto:
  - responido_en:
  - Column4:
  - Column5:

## usuarios_deportes
  - usuario_id: INTEGER FK
  - deporte_id:  FK
  - nivel:
  - es_principal:

## organizadores
  - id: INTEGER PK
  - usuario_id:  FK
  - nombre_comercial:
  - descripcion:
  - correo_contacto:
  - telefono_contacto:
  - ciudad_id:  FK
  - logo_id:  FK
  - estado_validacion:
  - validado_en:
  - creado_en:
  - actualizado_en:
  - eliminado_en:

## organizador_miembros
  - organizador_id: INTEGER PK
  - usuario_id:
  - rol:
  - agregado_en:

## solicitudes_validacion
  - id: INTEGER PK
  - organizador_id:  FK
  - estado:
  - revisor_id:
  - comentarios:
  - motivo_rechazo:
  - enviada_en:
  - resuelta_en:
  - Column3:
  - Column4:

## documentos_validacion
  - id: INTEGER PK
  - solicitud_id:
  - tipo_documento:
  - archivo_id:
  - numero_documento:
  - verificado:
  - creado_en:

## cuentas_cobro
  - id: INTEGER PK
  - organizador_id:  FK
  - banco:
  - titular:
  - clabe:
  - verificada:
  - es_principal:
  - creado_en:
  - eliminado_en:
  - Column3:

## eventos
  - id: INTEGER PK
  - organizador_id:  FK
  - tipo:
  - estado:
  - dificultad:
  - titulo:
  - slug:
  - descripcion:
  - portada_id:
  - edad_minima:
  - es_publico:
  - Column12: INTEGER PK
  - publicado_en:
  - creado_en:
  - actualizado_en:
  - eliminado_en:
  - Column2:

## evento_deportes
  - id: INTEGER PK
  - evento_id:  FK
  - Column3: INTEGER PK
  - deporte_id:  FK

## eventos_requisitos
  - id: INTEGER PK
  - evento_id:  FK
  - descripcion:
  - orden:

## evento_sedes
  - id: INTEGER PK
  - evento_id:
  - tipo:
  - nombre:
  - direccion:
  - ciudad_id:
  - latitud:
  - longitud:

## eventos_fechas
  - id: INTEGER PK
  - evento_id:
  - inicia_en:
  - termina_en:
  - cancelada_en:
  - Column2:
  - Column3:
  - Column4:

## evento_categorias
  - id: INTEGER PK
  - evento_id:  FK
  - nombre:
  - distancia_km:
  - edad_minima:
  - edad_maxima:
  - cupo_total:
  - permite_lista_espera:

## evento_boletos
  - id: INTEGER PK
  - categoria_id:  FK
  - tipo:
  - precio:
  - moneda:
  - disponible_desde:
  - disponible_hasta:
  - cantidad_maxima:
  - activo:

## rutas
  - id: INTEGER PK
  - creador_id:  FK
  - deporte_id:  FK
  - gpx_archivo_id:
  - dificultad:
  - nombre:
  - descripcion:
  - distancia_m:
  - desnivel_positivo_m:
  - es_publica:
  - creado_en:
  - eliminado_en:

## ruta_puntos
  - id: INTEGER PK
  - ruta_id:  FK
  - tipo:
  - orden:
  - nombre:
  - latitud:
  - longitud:
  - altitud_m:

## evento_rutas
  - id: INTEGER PK
  - ruta_id:
  - categoria_id:

## paquete_recuperacion
  - id: INTEGER PK
  - evento_id:
  - nivel:
  - nombre:
  - descripcion:
  - precio:
  - moneda:
  - activo:

## inscripciones
  - id: INTEGER PK
  - usuario_id:
  - evento_id:
  - fecha_id:
  - categoria_id:
  - boleto_id:
  - paquete_id:
  - estado:
  - numero_particpante:
  - inscrita_en:
  - cancelada_en:
  - asistio_en:
  - asistencia_latitud:
  - asistencia_longitud:
  - tiempo_oficial:
  - posicion_general:
  - posicion_categoria:
  - Column4:

## valoraciones_evento
  - id: INTEGER PK
  - inscripciones_id: INTEGER FK
  - calificacion_evento:
  - calificacion_organizador:
  - comentario:
  - respuesta_organizador:
  - respondida_en:
  - creado_en:

## calendario_usuario
  - usuario_id: INTEGER FK
  - fecha_id:  FK
  - agregado_en:

## publicaciones
  - id: INTEGER PK
  - usuario_id:
  - comunidad_id:
  - evento_id:
  - archivo_id:
  - texto:
  - estado:
  - creado_en:
  - eliminado_en:

## comentarios
  - id: INTEGER PK
  - publicacion_id:  FK
  - usuario_id:  FK
  - comentario_padre_id:  FK
  - texto:
  - creado_en:
  - eliminado_en:

## reacciones
  - id: INTEGER PK
  - usuario_id:  FK
  - tipo:
  - creado_en:

## pagos
  - id: INTEGER PK
  - usuario_id:  FK
  - metodo:
  - pasarela:
  - estado:
  - monto_total:
  - moneda:
  - referencia_externa:
  - pagado_en:
  - creado_en:

## comisiones
  - id: INTEGER PK
  - concepto:
  - porcentaje:
  - vigente_desde:
  - vigente_hasta:
  - Column6:

## liquidaciones
  - id: INTEGER PK
  - organizador_id:  FK
  - cuenta_cobro_id:  FK
  - estado:
  - periodo_desde:
  - periodo_hasta:
  - monto_bruto:
  - monto_comision:
  - monto_neto:
  - moneda:
  - referencia_pago:
  - pagada_en:
  - creado_en:

## pagos_inscripciones
  - id: INTEGER PK
  - inscripcion_id: INTEGER PK
  - pago_id:  FK
  - liquidacion_id:  FK
  - monto_bruto:
  - comision_plataforma:
  - monto_organizador:

## reembolsos
  - id: INTEGER PK
  - pago_id:  FK
  - estado:
  - monto:
  - motivo:
  - solicitado_por:
  - aprobado_por:
  - creado_en:
  - procesado_en:

## cupones
  - id: INTEGER PK
  - codigo:
  - descripcion:
  - tipo_descuento:
  - concepto:
  - organizador_id:  FK
  - valor:
  - vigente_desde:
  - vigente_hasta:
  - usos_maximos:
  - usos_por_usuario:
  - activo:
  - Column3:

## cupones_usos
  - id: INTEGER PK
  - cupon_id:  FK
  - usuario_id:  FK
  - pago_id:  FK
  - usado_en:

## vendedores
  - id: INTEGER PK
  - usuario_id:  FK
  - nombre_tienda:
  - descripcion:
  - logo_id:  FK
  - es_plataforma:
  - verificado_en:
  - activo:
  - creado_en:

## cetegorias_producto
  - id: INTEGER PK
  - padre_id:  FK
  - nombre:
  - slug:

## productos
  - id: INTEGER PK
  - vendedor_id:  FK
  - categoria_id:  FK
  - imagen_id:  FK
  - marca:
  - nombre:
  - slug:
  - descripcion:
  - activo:
  - publicado_en:
  - creado_en:
  - eliminado_en:

## produCto_variantes
  - id:  PK
  - producto_id:  FK
  - sku:
  - talla:
  - color:
  - precio:
  - moneda:
  - peso_gramos:
  - stock_disponible:
  - stock_reservado:
  - umbral_stock_bajo:
  - activo:

## paquete_items
  - paquete_id:  FK
  - variante_id:  FK
  - cantidad:

## direcciones_usuario
  - id: INTEGER PK
  - usuario_id:
  - ciudad_id:
  - alias:
  - destinatario:
  - telefono:
  - calle:
  - numero_exterior:
  - numero_interior:
  - referencias:
  - es_priincipal:
  - aliminado_en:

## carrito_items
  - usuario_id: INTEGER FK
  - variante_id:  FK
  - cantidad:
  - agregado_en:

## ordenes
  - id: INTEGER PK
  - usuario_id:  FK
  - direccion_envio_id:  FK
  - pago_id:  FK
  - estado:
  - moneda:
  - trasnportista:
  - numero_guia:
  - costo_envio:
  - enviado_en:
  - entregado_en:
  - creado_en:

## ordenes_items
  - id: INTEGER PK
  - orden_id:
  - variante_id:
  - cantidad:
  - precio_unitario:
  - comision_porcentaje:

## valoraciones_producto
  - orden_item_id: INTEGER FK
  - calificado:
  - comentario:
  - creado_en:

## creadores
  - id: INTEGER PK
  - usuario_id:  FK
  - nombre_publico:
  - biografia:
  - verificado_en:
  - activo:
  - creado_en:

## videos
  - id: INTEGER PK
  - creador_id:  FK
  - deporte_id:  FK
  - video_id:  FK
  - miniatura_id:  FK
  - categoria:
  - formato:
  - estado:
  - titulo:
  - descripcion:
  - duracion_segundos:
  - publicado_en:
  - creado_en:
  - eliminado_en:

## articulos
  - id: INTEGER PK
  - creador_id:  FK
  - portada_id:  FK
  - categoria:
  - estado:
  - titulo:
  - slug:
  - resumen:
  - cuerpo:
  - publicado_en:
  - creado_en:
  - eliminado_en:

## video_reacciones
  - id: INTEGER FK
  - video_id: INTEGER FK
  - usuario_id:
  - tipo:
  - Column5:
  - creado_en:

## video_comentarios
  - id: INTEGER PK
  - video_id:
  - usuario_id:
  - comentario_padre_id:
  - texto:
  - creado_en:
  - eliminado_en:

## video_vistas
  - id: INTEGER PK
  - video_id:  FK
  - usuario_id:  FK
  - ssegundos_vistos:
  - vista_en:

## notificaciones
  - id: INTEGER PK
  - usuario_id:  FK
  - tipo:
  - canal:
  - titulo:
  - cuerpo:
  - tipo_entidad:
  - entidad_id:  FK
  - leida_en:
  - creado_en:

## mensajeria
  - id: INTEGER PK
  - tipo:
  - titulo:
  - evento_id:  FK
  - comunidad_id:  FK
  - creada_por:
  - creado_en:

## conversaciones_particIpantes
  - conversaciones_id:  FK
  - usuario_id:  FK
  - es_administrador:
  - silenciado:
  - ultimo_leido_en:
  - unido_en:
  - salido_en:

## mensajes
  - id: INTEGER PK
  - conversacion_id:  FK
  - remitente:
  - responde_a_id:
  - archivo_id:
  - tipo:
  - contenido:
  - creado_en:
  - editado_en:
  - eliminado_en:

## difusion_admin
  - id: INTEGER PK
  - creada_por:
  - imagen_id:  FK
  - formato:
  - estado:
  - canal:
  - titulo:
  - cuerpo:
  - texto_boton:
  - url_destino:
  - segmento_deporte_id:  FK
  - segmento_ciudad_id:  FK
  - segmento_nivel:
  - programada_para:
  - enviada_en:
  - creado_en:

## insignias
  - id: INTEGER PK
  - deporte_id:
  - icono_id:
  - nivel:
  - tipo:
  - codigo:
  - nombre:
  - descripcion:
  - criterio_tipo:
  - criterio_valor:
  - activa:

## usuario_insignias
  - usuario_id: INTEGER FK
  - insignia_id:  FK
  - evento_id:  FK
  - otorgada_por:
  - otorgada_en:

## retos
  - id: INTEGER PK
  - insignia_id:
  - comunidad_id:
  - deporte_id:
  - nombre:
  - descripcion:
  - distancia_objetivo_km:
  - inicia_en:
  - termina_en:
  - creado_en:

## reto_particpantes
  - reto_id: INTEGER FK
  - usuario_id:  FK
  - inscrito_en:
  - completado_en:

## puntos_movimientos
  - id: INTEGER PK
  - usuario_id:
  - inscripcion_id:
  - insignia_id:
  - motivo:
  - puntos:
  - creado_en:

## referidos
  - id: INTEGER PK
  - referidor_id:  FK
  - referido_id:  FK
  - inscripcion_id:  FK
  - tipo_recompensa:
  - valor_recompensa:
  - recompensa_otorgada_en:
  - registrado_en:

## creditos_moviminetos
  - id: INTEGER PK
  - usuario_id:  FK
  - referido_id:  FK
  - pago_id:  FK
  - motivo:
  - monto:
  - creado_en:

## anunciantes
  - id: BOOLEAN PK
  - tipo:
  - nombre:
  - correo_electronico:
  - telefono_contacto:
  - activo:
  - creado_en:

## anuncios
  - id: INTEGER PK
  - anunciante_id:  FK
  - imagen_id:  FK
  - video_id:  FK
  - nombre_campana:
  - estado:
  - modelo_cobro:
  - presupuesto:
  - tarifa:
  - moneda:
  - inicia_en:
  - termina_en:
  - ubicacion:
  - titulo:
  - cuerpo:
  - url_destino:
  - segmento_deporte_id:  FK
  - segmento_ciudad_id:  FK
  - segmento_sexo:
  - segmento_edad_minima:
  - segmento_edad_maxima:
  - activo:
  - creado_en:

## anuncios_eventos
  - id: INTEGER PK
  - anuncio_id:  FK
  - usuario_id:  FK
  - tipo:
  - registrado_en:

## auditoria_log
  - id: INTEGER PK
  - usuario_id:  FK
  - accion:
  - tipo_entidad:
  - entidad_id:  FK
  - datos_anteriores:
  - datos_nuevos:
  - ip:
  - registrada_en:

## reportes
  - id: INTEGER PK
  - reportante_id:  FK
  - asignado_a:
  - tipo_entidad:
  - entidad_id:  FK
  - motivo:
  - descripcion:
  - estado:
  - accion_tomada:
  - notas_moderador:
  - creado_en:
  - resuelto_en:

## tickets_soporte
  - id: INTEGER PK
  - usuario_id:  FK
  - asignado_a:
  - categoria:
  - prioridad:
  - estado:
  - asunto:
  - creado_en:
  - cerrado_en:

## ticket_mensaje
  - id: INTEGER PK
  - usuario_id:  FK
  - asignado_a:
  - ctaegoria:
  - prioridad:
  - estado:
  - asunto:
  - creado_en:
  - cerrado_en:
  - ticket_id:  FK
  - autor_id:  FK
  - mensaje:
  - es_interno:
  - creado_en:

## home_bloques
  - id: INTEGER PK
  - imagen_id:  FK
  - tipo:
  - titulo:
  - subtitulo:
  - texto_boton_primario:
  - destino_boton_primario:
  - texto_boton_secundario:
  - destino_boton_secundario:
  - orden:
  - activo:
  - visible_desde:
  - visible_hasta:
  - creado_en:
  - Column3:

## ciudades

## CONVERSACIONES
  - id: INTEGER PK
  - tipo:
  - titulo:
  - evento_id:
  - comunidad_id:
  - creada_por:
  - creado_en: