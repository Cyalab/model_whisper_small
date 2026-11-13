# OCR de notas manuscritas

Rama `ocr-notas`, sobre `prellenado-plantilla`. Pedido por la líder del proyecto el 13 nov 2026.

## Qué hace

1. En el editor, **Subir foto de nota** manda la imagen a `/api/ocr`.
2. `ocr.py` reduce la foto a 1600 px por lado y se la pide a un **modelo de visión-lenguaje local con Ollama**. Por omisión es **Qwen3-VL 2B** (`qwen3-vl:2b`, 1.9 GB), que cabe en la Quadro M1200 de 4 GB.
3. La instrucción pide transcribir **tal cual**: sin corregir, sin completar abreviaturas y sin interpretar. Lo que no se lee sale como `[ilegible]`.
4. El texto entra al **mismo camino que un dictado**: marcado con el diccionario de cadera, prellenado de la plantilla v0.4 (reglas R1–R11) y confirmación del radiólogo.
5. Al guardar, el expediente registra `origen: "nota"` y el `modelo_ocr` usado, para medir por separado el dictado y la nota.

## Privacidad

- **La imagen no sale del equipo**: Ollama corre en local. No se usa ningún servicio en la nube.
- **La imagen no se guarda**: vive en memoria mientras se lee. Solo se guarda el texto que confirma el radiólogo, igual que con el dictado.
- **La detección de datos identificables NO está implementada.** Una nota manuscrita puede traer el nombre, el expediente o fechas del paciente. Mientras no exista, el editor pide no subir notas con nombre del paciente. Es el siguiente pendiente.

## Configuración

| Variable | Por omisión | Para qué |
|---|---|---|
| `AURORA_VOZ_OCR_MODELO` | `qwen3-vl:2b` | Modelo de Ollama. En la RTX 3060 (6 GB) cabe `qwen2.5vl:3b`; en la RTX 5080 (16 GB), `qwen2.5vl:7b` |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Dirección de Ollama |

## Uso

```bash
ollama pull qwen3-vl:2b
python ocr.py nota.jpg                       # sin servidor ni Whisper: imprime texto, marcas y campos
python ocr.py nota.jpg --modelo qwen2.5vl:3b --lado-dicom Izquierdo
python servidor.py                           # editor completo en http://127.0.0.1:8000
python tests/test_ocr.py                     # 8 pruebas; no necesitan Ollama
```

`ocr.py` solo necesita Python y, de preferencia, Pillow (`pip install pillow`). Sin Pillow, la foto se envía sin reducir.

## Pruebas

`tests/test_ocr.py` levanta un Ollama falso en el mismo proceso y prueba:

- la petición: modelo, imagen y temperatura 0;
- que la foto se reduzca;
- la limpieza del texto y la normalización NFC;
- el conteo de `[ilegible]`;
- que la nota llegue al mismo prellenado que un dictado;
- los errores: modelo no descargado, Ollama apagado e imagen inválida.

Las notas de prueba son inventadas.

## Pendiente

- **Detección de datos identificables** en el texto de la nota (y en el dictado).
- **Probar con notas manuscritas inventadas** escritas a mano por el equipo. Todavía no se sabe qué tan bien lee un modelo de 2B la letra de un médico. Si no alcanza, probar `qwen2.5vl:3b` (RTX 3060) o `qwen2.5vl:7b` (RTX 5080).
- Confirmar que la versión de Ollama instalada usa la Quadro M1200 (capacidad de cómputo 5.0). Si no, corre en el procesador, más lento.
- En el servidor de `voz.aurora-cyalab.space` (sin tarjeta gráfica, según `DESPLIEGUE.md`), decidir dónde corre el OCR.
- La lectura de la nota no tiene medición propia todavía: hoy se mide igual que el dictado (prellenado contra confirmación), separado por `origen`.
