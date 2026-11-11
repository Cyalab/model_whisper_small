# Prellenado de la plantilla de informe estructurado (v0.4)

Rama `prellenado-plantilla`, sobre `diccionario-marcado-automatico`.

## Decisiones de la líder del proyecto (10 nov 2026)

- Aurora Voz **prellena** los campos de la plantilla y el **radiólogo confirma**.
- El **lado del estudio** se propone desde el DICOM y desde el dictado. **Decide el radiólogo**, y se guarda su elección **y el motivo**.
- Se miden **por separado**: (1) DICOM contra dictado en el lado del estudio, y (2) lo que prellenó Aurora Voz contra lo que confirmó el radiólogo.
- Cada diferencia se registra como **«cambió»** o **«faltó»**.
- El denominador de cada campo es el **total de casos registrados**.

Flujo, en palabras de la líder: "El radiólogo dicta; Aurora Voz llena los campos; cuando el DICOM y el dictado no coinciden en el lado, el radiólogo lo hace; y lo que se guarda para medir son las diferencias que se tuvieron del total de casos registrados."

## Qué hace

1. Al transcribir, el servidor marca los términos (como antes) y además **propone los campos** de la plantilla v0.4.
2. Debajo de la transcripción aparece la plantilla prellenada. Bajo cada campo se ve la frase que lo llenó y la regla que se usó.
3. Si el dictado dice dos cosas distintas para un campo (por ejemplo, Garden II y Garden III), el campo **no se llena**: queda en amarillo y elige el radiólogo.
4. **Lado del estudio:** se captura a mano el lado del DICOM, hasta que Aurora lo envíe. Si el DICOM y el dictado coinciden, se propone ese lado. Si no coinciden, la lista queda **vacía** (no se empuja hacia ninguna fuente) y el motivo es obligatorio.
5. Al guardar, el servidor **recalcula** el prellenado (lo que se mide es lo que propuso el sistema, no lo que manda el navegador) y guarda, en `plantilla`:
   - `campos_prellenados`, con la versión de las reglas;
   - `campos_confirmados`;
   - `diferencias` por campo: `igual`, `cambió` o `faltó`;
   - `lado_estudio`: DICOM, dictado, estado y la decisión del radiólogo con su motivo.
6. `python metricas_prellenado.py` cuenta, sobre el total de casos, las dos mediciones por separado. No imprime el texto de los dictados.

Un dictado guardado sin plantilla se sigue guardando igual que antes (`plantilla: null`).

## Campos

| Se prellenan | No se prellenan |
|---|---|
| Proyección, lado del estudio (aparte), lado del hallazgo, fractura, grupo AO/OTA, Garden, desplazamiento, conminución, material, osteopenia, cambios degenerativos | Calidad de imagen, sutileza, ancho de la línea, confianza, otros hallazgos, impresión |

Los valores son los mismos de la hoja «Listas» de la plantilla v0.4.

## Reglas (versión 0.1-provisional, propuesta de Claude)

**Las validan los radiólogos antes de usar las métricas.** Cada propuesta guarda el número de regla.

| Regla | Qué hace |
|---|---|
| R1 | Proyección: «AP» seguido de pelvis → AP de pelvis; de cadera o coxofemoral → AP de cadera; «axial» o «lateral» → Axial (lateral). Un AP sin región no se llena. |
| R2 | Lado del estudio (dictado): un lado justo después de la proyección y su región, antes de cualquier hallazgo. La AP de pelvis sin lado dictado → «Sin lado». |
| R3 | Fractura: presente; «sin», «no se observa», «descarta»… antes, en la misma oración y sin cruzar una coma → ausente; «probable», «posible», «no se descarta»… → dudosa. |
| R4 | Lado del hallazgo: el lado más cercano a la fractura en su oración, sin contar el de la proyección. |
| R5 | Grupo AO/OTA: subcapital → 31B1; transcervical → 31B2; basicervical → 31B3; intertrocantérica → 31A; subtrocantérica → Otra; sin localización, cabeza femoral → 31C y región trocantérica → 31A. |
| R6–R8 | Garden, desplazamiento y conminución, por término del diccionario (con negación en la conminución). |
| R9 | Material: osteosíntesis, prótesis o ambos; negado → Ninguno. |
| R10 | Osteopenia: sí, o no si está negada. |
| R11 | Cambios degenerativos: el grado (leves, moderados, severos) en la misma oración; sin grado no se llena; negados → Ausentes. |

## Archivos

- `prellenado.py`: reglas, lado del estudio, validación y comparación.
- `metricas_prellenado.py`: las dos mediciones por separado.
- `marcado.py`: cada marca automática trae ahora `termino` y `categoria`.
- `servidor.py`: `/api/transcribir` devuelve `prellenado` y acepta `lado_dicom`; nueva ruta `/api/prellenar`; `/api/guardar` recibe `campos_confirmados` y `lado_estudio`, valida los valores y exige el motivo cuando hace falta.
- `static/index.html`: panel de la plantilla.
- `tests/test_prellenado.py`: 10 pruebas con dictados inventados.

## Pendiente

- Que los radiólogos validen las reglas R1–R11.
- El lado del DICOM llega a mano hasta que Aurora Voz se integre a Aurora.
- La vista axial sigue pendiente con la radióloga, igual que en la plantilla.
- El diccionario aún trata «proyección lateral» como sinónimo de «proyección axial».
