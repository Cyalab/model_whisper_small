# Marcado automático con el diccionario de cadera

## Qué hace

Al transcribir un dictado, el servidor compara el texto con el diccionario de cadera y devuelve las marcas de color ya puestas. El radiólogo solo corrige lo que el diccionario haya marcado mal, con los mismos botones de siempre.

| Color | Significado | Ejemplo |
|---|---|---|
| Verde | Término del diccionario, bien escrito | "subcapital", "no desplazada" |
| Amarillo | Término del diccionario sin acento, o un sinónimo o abreviatura; se sugiere el término oficial | "femur" → fémur; "Fx" → fractura; "coxartrosis" → cambios degenerativos |
| Rojo | Palabra desconocida muy parecida a un término: probable error de transcripción | "costeopenia" → osteopenia |

Al pasar el cursor sobre una marca automática se ve el motivo, el término sugerido y su código RadLex.

## Archivos

- `diccionario/diccionario_cadera.json`: términos, sinónimos, abreviaturas y códigos RadLex. Versión 0.1, alineada con el formato de descripción v0.3 y la ontología OCHM 31-B. Los sinónimos son una propuesta inicial que validan los radiólogos.
- `marcado.py`: el marcado. No depende de Whisper, así que se puede probar por separado.
- `tests/test_marcado.py`: pruebas. Se corren con `python tests/test_marcado.py`.
- `servidor.py`:
  - `/api/transcribir` devuelve las marcas automáticas y la versión del diccionario.
  - `/api/guardar` guarda las marcas finales del radiólogo junto con `marcas_automaticas`, las que propuso el diccionario. Esos pares sirven para medir qué tan bien marca el diccionario y para el aprendizaje activo.
- `static/index.html`:
  - conserva los datos de las marcas automáticas;
  - muestra la sugerencia al pasar el cursor;
  - etiqueta las marcas manuales como `origen: "radiologo"`;
  - explica los colores en la ayuda.
- `.gitignore`: excluye `expedientes/` y `estadisticas.json`, y se quitaron del repositorio los dos expedientes de prueba. Los dictados reales nunca deben subirse.

## Cómo funciona

- Las frases más largas ganan: en "parcialmente desplazada" no se marca "desplazada" por separado.
- Se reconocen variantes de género y número: desplazado, desplazadas, fracturas, conminutas.
- La comparación aproximada (rojo) solo se aplica a palabras de 6 letras o más, con un parecido de al menos 0.85. No se aplica a lateralidad ni a Garden.
- Las posiciones de las marcas son índices sobre el texto en forma NFC, el mismo formato que las marcas manuales.

## Pendiente

- Que los radiólogos validen los sinónimos y abreviaturas del diccionario.
- Ajustar el umbral del rojo con dictados reales: medir cuántas marcas automáticas corrigen los radiólogos.
- La ayuda de la página mencionaba sugerencias desde `estadisticas.json`, pero el servidor no lo implementa. Se reemplazó ese texto.
- Este módulo funciona hoy de forma independiente, pero se integrará a Aurora. El acceso de usuarios y el ID del estudio los proveerá la plataforma Aurora al integrarse; por eso no se agregaron aquí.
