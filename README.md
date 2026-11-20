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
- **Editor-corrector de Aurora Voz** (artículo «Aurora Voz: captura multimodal asistida por IA»): este repositorio implementa la captura por voz, el marcado automático, el prellenado de la plantilla, el OCR local de notas manuscritas (rama `ocr-notas`, ver `CAMBIOS_OCR.md`) y el código LOINC del estudio (rama `loinc-estudio`, ver `CAMBIOS_LOINC.md`).
- **Capa 2 de Aurora (códigos de estudio LOINC/RSNA Playbook)**: cada expediente lleva el código LOINC del estudio, calculado con la proyección y el lado que confirma la persona.

## Estructura

| Archivo | Función |
|---|---|
| `servidor.py` | Servidor FastAPI: `/api/transcribir`, `/api/guardar`, `/api/expedientes` |
| `marcado.py` | Marcado automático con el diccionario |
| `ocr.py` | OCR de notas manuscritas con un modelo local de Ollama (`CAMBIOS_OCR.md`) |
| `loinc.py` | Código LOINC del estudio a partir de la proyección y el lado (`CAMBIOS_LOINC.md`) |
| `diccionario/diccionario_cadera.json` | Términos, sinónimos, abreviaturas y códigos RadLex |
| `static/index.html` | Editor web de transcripción y corrección |
| `tests/test_marcado.py` | Pruebas del marcado |
| `tests/test_loinc.py` | Pruebas del código LOINC |

## Uso

```bash
pip install fastapi uvicorn python-multipart soundfile torch transformers
python servidor.py        # abre http://127.0.0.1:8000
python tests/test_marcado.py
python tests/test_loinc.py
```

Se necesita `ffmpeg` para audios que no sean WAV. Los dictados se guardan en `expedientes/`, que está excluido del repositorio: nunca deben subirse.

## Licencia de LOINC

This material contains content from LOINC (http://loinc.org). LOINC is copyright © Regenstrief Institute, Inc. and the Logical Observation Identifiers Names and Codes (LOINC) Committee and is available at no cost under the license at http://loinc.org/license. LOINC® is a registered United States trademark of Regenstrief Institute, Inc.
