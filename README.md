# Aurora Voz: transcripción de dictados radiológicos

Módulo de voz de la plataforma **Aurora** (proyecto CBF-2025-I-3700). Hoy funciona de forma independiente; está pensado para integrarse a Aurora, que proveerá el acceso de usuarios y el ID del estudio.

## Qué hace

1. **Transcripción.** Recibe un dictado (grabado en el navegador o subido como archivo) y lo transcribe con **Whisper small** (`openai/whisper-small`) en español, en ventanas de 30 segundos con traslape.
2. **Marcado automático.** Compara la transcripción con el **diccionario de cadera** (`diccionario/diccionario_cadera.json`, basado en RadLex y AO/OTA) y marca cada término en verde, amarillo o rojo. Ver `CAMBIOS_MARCADO.md`.
3. **Corrección del radiólogo.** El radiólogo revisa y corrige los colores en el editor.
4. **Guardado.** Guarda la transcripción con las marcas finales y las automáticas, como pares para el aprendizaje activo.

## Relación con otros componentes de Aurora

- **Formato de descripción de cadera** (v0.3): mismo vocabulario y mismos códigos RadLex que el diccionario.
- **Ontología OCHM 31-B** (fracturas de cuello femoral, AO/OTA 2018): el diccionario usa sus grupos AO/OTA y su vocabulario de desplazamiento.
- **Editor-corrector de Aurora Voz** (artículo «Aurora Voz: captura multimodal asistida por IA»): este repositorio implementa la captura por voz y el marcado automático; el OCR de notas manuscritas aún no está implementado.

## Estructura

| Archivo | Función |
|---|---|
| `servidor.py` | Servidor FastAPI: `/api/transcribir`, `/api/guardar`, `/api/expedientes` |
| `marcado.py` | Marcado automático con el diccionario |
| `diccionario/diccionario_cadera.json` | Términos, sinónimos, abreviaturas y códigos RadLex |
| `static/index.html` | Editor web de transcripción y corrección |
| `tests/test_marcado.py` | Pruebas del marcado |

## Uso

```bash
pip install fastapi uvicorn python-multipart soundfile torch transformers
python servidor.py        # abre http://127.0.0.1:8000
python tests/test_marcado.py
```

Se necesita `ffmpeg` para audios que no sean WAV. Los dictados se guardan en `expedientes/`, que está excluido del repositorio: nunca deben subirse.
