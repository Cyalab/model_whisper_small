# Despliegue de Aurora Voz en voz.aurora-cyalab.space

Para: Abel. De: María de los Ángeles Cosío León. 11 de noviembre de 2026.
Rama: `prellenado-plantilla` (repositorio `Cyalab/model_whisper_small`).

## Qué contiene esta versión

- Transcripción con Whisper small y marcado con el diccionario de cadera (`CAMBIOS_MARCADO.md`).
- Prellenado de la plantilla de informe estructurado v0.4 a partir del dictado; el radiólogo confirma
  (`CAMBIOS_PRELLENADO.md`). Las reglas de llenado son **provisionales** (versión 0.1) hasta que las
  validen los radiólogos.

## Antes de publicar: obligatorio

El servidor está hecho para uso local. **No se debe exponer a internet tal como está:**

1. **No tiene acceso con usuario.** Cualquiera con la dirección podría ver la lista de dictados
   (`GET /api/expedientes`), leer cualquiera (`GET /api/expedientes/{id}`) y **borrarlos**
   (`DELETE /api/expedientes/{id}`). Los dictados son descripciones clínicas y pueden incluir datos
   dichos en voz alta. Hace falta autenticación delante de **todas** las rutas, incluida la página.
2. **CORS abierto**: `allow_origins=["*"]` en `servidor.py`. Limitarlo al propio dominio.
3. **Borrado**: quitar `DELETE /api/expedientes/{id}` o restringirlo a administradores, con registro de
   quién borró y cuándo.
4. **HTTPS obligatorio.** Además de la seguridad, el navegador solo permite usar el micrófono
   («Grabar en tiempo real») en páginas con HTTPS.
5. **Escucha local**: `uvicorn` debe seguir en `127.0.0.1` y publicarse solo a través de Nginx.

## Operación

- **Recursos**: Whisper small corre en CPU y ocupa memoria. Si va en el mismo servidor que Aurora,
  compite con ella; confirmar que alcanza.
- **Datos**: los dictados se guardan en `expedientes/` en el disco del servidor. Necesitan respaldo y
  no deben entrar al repositorio (ya están en `.gitignore`).
- **Dependencias**: además de las de Whisper, `ffmpeg` en el sistema y `python-multipart` para recibir
  el audio.
- **Pruebas**: `python tests/test_marcado.py` y `python tests/test_prellenado.py`.
- **Métricas**: `python metricas_prellenado.py` (solo conteos; no imprime los dictados).

## Pendiente de decidir (María)

- En qué servidor corre.
- Quién controla el acceso: usuarios propios de Aurora Voz, Nginx o esperar a la integración con Aurora.
- Si se publica `prellenado-plantilla` o solo el marcado (`diccionario-marcado-automatico`).
- El DNS del subdominio depende de la cuenta del dominio (ver la lista de entrega).
