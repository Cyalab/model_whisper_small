# Código LOINC del estudio (capa 2)

Rama `loinc-estudio`, sobre `ocr-notas`. Pedido por la líder del proyecto el 19 nov 2026.

## Qué hace

Aurora Voz asigna a cada expediente el **código LOINC del estudio** (LOINC/RSNA Radiology Playbook, versión 2.83) a partir de dos campos que la persona ya confirma en la plantilla v0.4: la **Proyección** y el **Lado del estudio**.

| Proyección | Lado del estudio | Código LOINC | Nombre LOINC |
|---|---|---|---|
| AP de pelvis | cualquiera | 37622-8 | XR Pelvis AP |
| AP de cadera | Izquierdo | 36582-5 | XR Hip - left AP |
| AP de cadera | Derecho | 37726-7 | XR Hip - right AP |
| AP de cadera | Bilateral, Sin lado o vacío | sin código | El Playbook no tiene AP bilateral de cadera; una AP de cadera necesita lado |
| Axial (lateral) de cadera | cualquiera | sin código | **Pendiente**: los radiólogos deciden a qué vista del Playbook corresponde |
| Otra | cualquiera | sin código | — |

La regla no adivina: si la combinación no tiene un código exacto, no se asigna ninguno y se muestra el motivo.

## Dónde aparece

1. **En la pantalla**, debajo de la plantilla: el código, su nombre LOINC y de qué proyección y lado salió. Se recalcula cada vez que la persona cambia la proyección o el lado.
2. **En el prellenado** (`/api/transcribir`, `/api/ocr`, `/api/prellenar`): `estudio_loinc` con el código **propuesto** a partir de la proyección y el lado propuestos.
3. **En el expediente** (`/api/guardar`): `plantilla.estudio_loinc` con el código **definitivo**, calculado con lo que **confirmó** la persona, no con lo que propuso el sistema. Guarda la versión de LOINC (`2.83`) y de la regla (`0.1`).
4. `/api/loinc` (POST `{proyeccion, lado}`): el código y el aviso de licencia, para la pantalla.

## Licencia de LOINC

La licencia pide mostrar el código junto con su nombre LOINC y el aviso de Regenstrief. Las dos cosas aparecen en la pantalla (`loinc.AVISO_LOINC`).

## Fuente

Los tres códigos salen del subconjunto de cadera, pelvis y fémur (230 códigos) que extrajo la líder del proyecto de LOINC 2.83, en el repositorio de análisis (`capa2_loinc/estudios_cadera_pelvis_loinc_2_83.json`). La prueba `test_codigos_existen_en_el_subconjunto_del_playbook` comprueba, si ese archivo está disponible, que cada código existe, está activo y tiene el mismo nombre.

## Pendientes

- **Axial (lateral) de cadera**: los radiólogos dicen a qué vista corresponde (en el Playbook hay lateral, lateral en rana, lateral con rayo horizontal y lateral verdadera).
- **Lista corta**: los radiólogos marcan qué estudios se usan en sus hospitales; si aparece otra proyección, se agrega a la plantilla y a la tabla.
- **Integración con Aurora**: cuando Aurora envíe la proyección y la lateralidad del DICOM, el código podrá proponerse desde ahí.

## Pruebas

```bash
python tests/test_loinc.py
```

Solo usan textos inventados.
