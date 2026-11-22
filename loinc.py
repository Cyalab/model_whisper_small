"""Código LOINC del estudio a partir de la proyección y el lado de la plantilla v0.4.

Capa 2 de Aurora (códigos de estudio LOINC/RSNA Radiology Playbook), decisión de la líder del
proyecto del 19 nov 2026: Aurora Voz asigna el código LOINC del estudio.

Regla: el código se toma de dos campos que la persona ya confirma en la plantilla, la
«Proyección» y el «Lado del estudio». Igual que la plantilla de Excel v0.4, se acepta una
correspondencia exacta o aproximada, y siempre se dice cuál fue (decisión de la líder del
proyecto, 21 nov 2026). Si la combinación no tiene código, no se asigna ninguno y se explica por qué.

Fuente: LOINC 2.83, LOINC/RSNA Radiology Playbook. El subconjunto completo de cadera, pelvis
y fémur (230 códigos) está en el repositorio de análisis del proyecto
(capa2_loinc/estudios_cadera_pelvis_loinc_2_83.json). Aquí solo van los códigos que
corresponden a los valores de la plantilla.

Licencia de LOINC: el código se muestra siempre junto con su nombre LOINC y con el aviso
AVISO_LOINC, en pantalla y en el expediente.
"""
from __future__ import annotations

VERSION_LOINC = "2.83"
VERSION_REGLA = "0.2"

AVISO_LOINC = (
    "This material contains content from LOINC (http://loinc.org). LOINC is copyright © "
    "Regenstrief Institute, Inc. and the Logical Observation Identifiers Names and Codes (LOINC) "
    "Committee and is available at no cost under the license at http://loinc.org/license. "
    "LOINC® is a registered United States trademark of Regenstrief Institute, Inc."
)

# Códigos del Playbook (LOINC 2.83) para los valores de la plantilla v0.4.
# Clave -> (código, nombre LOINC, correspondencia, nota). Correspondencias como en la hoja
# «Códigos LOINC» de la plantilla de Excel v0.4.
CODIGOS = {
    "pelvis_ap": ("37622-8", "XR Pelvis AP", "exacta", None),
    "cadera_izq_ap": ("36582-5", "XR Hip - left AP", "exacta", None),
    "cadera_der_ap": ("37726-7", "XR Hip - right AP", "exacta", None),
    "cadera_ap_sin_lado": ("36581-7", "XR Hip AP", "exacta", "Lateralidad no especificada."),
    "cadera_bilateral": ("26400-2", "XR Hip - bilateral Single view", "aproximada",
                         "El Playbook no tiene AP bilateral de cadera; el código es de una vista "
                         "bilateral sin tipo de vista."),
}

# (Proyección, Lado del estudio) -> clave de CODIGOS. Lado None = cualquier lado.
TABLA = {
    ("AP de pelvis", None): "pelvis_ap",
    ("AP de cadera", "Izquierdo"): "cadera_izq_ap",
    ("AP de cadera", "Derecho"): "cadera_der_ap",
    ("AP de cadera", "Sin lado"): "cadera_ap_sin_lado",
    ("AP de cadera", "Bilateral"): "cadera_bilateral",
}

# Por qué no hay código, cuando no lo hay.
MOTIVOS = {
    ("AP de cadera", None): "Falta el lado del estudio.",
    ("Axial (lateral) de cadera", None): "Pendiente: los radiólogos deciden a qué vista del "
                                         "Playbook corresponde la axial.",
    ("Otra", None): "La proyección «Otra» no tiene código asignado.",
}


def codigo_estudio(proyeccion: str | None, lado: str | None) -> dict:
    """Código LOINC del estudio, o None con el motivo. Nunca lanza excepciones."""
    base = {"loinc": None, "nombre_loinc": None, "correspondencia": None, "nota": None,
            "motivo": None, "proyeccion": proyeccion or None,
            "lado": lado or None, "version_loinc": VERSION_LOINC, "version_regla": VERSION_REGLA}
    if not proyeccion:
        return {**base, "motivo": "Falta la proyección."}
    clave = TABLA.get((proyeccion, lado or None)) or TABLA.get((proyeccion, None))
    if clave:
        codigo, nombre, corresp, nota = CODIGOS[clave]
        return {**base, "loinc": codigo, "nombre_loinc": nombre, "correspondencia": corresp, "nota": nota}
    motivo = (MOTIVOS.get((proyeccion, lado or None)) or MOTIVOS.get((proyeccion, None))
              or "No hay código LOINC para esta combinación.")
    return {**base, "motivo": motivo}
