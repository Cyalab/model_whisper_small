"""Código LOINC del estudio a partir de la proyección y el lado de la plantilla v0.4.

Capa 2 de Aurora (códigos de estudio LOINC/RSNA Radiology Playbook), decisión de la líder del
proyecto del 19 nov 2026: Aurora Voz asigna el código LOINC del estudio.

Regla: el código se toma de dos campos que la persona ya confirma en la plantilla, la
«Proyección» y el «Lado del estudio». No se adivina: si la combinación no tiene un código
LOINC exacto, no se asigna ninguno y se explica por qué.

Fuente: LOINC 2.83, LOINC/RSNA Radiology Playbook. El subconjunto completo de cadera, pelvis
y fémur (230 códigos) está en el repositorio de análisis del proyecto
(capa2_loinc/estudios_cadera_pelvis_loinc_2_83.json). Aquí solo van los códigos que
corresponden a los valores de la plantilla.

Licencia de LOINC: el código se muestra siempre junto con su nombre LOINC y con el aviso
AVISO_LOINC, en pantalla y en el expediente.
"""
from __future__ import annotations

VERSION_LOINC = "2.83"
VERSION_REGLA = "0.1"

AVISO_LOINC = (
    "This material contains content from LOINC (http://loinc.org). LOINC is copyright © "
    "Regenstrief Institute, Inc. and the Logical Observation Identifiers Names and Codes (LOINC) "
    "Committee and is available at no cost under the license at http://loinc.org/license. "
    "LOINC® is a registered United States trademark of Regenstrief Institute, Inc."
)

# Códigos del Playbook (LOINC 2.83) para los valores de la plantilla v0.4.
CODIGOS = {
    "pelvis_ap": ("37622-8", "XR Pelvis AP"),
    "cadera_izq_ap": ("36582-5", "XR Hip - left AP"),
    "cadera_der_ap": ("37726-7", "XR Hip - right AP"),
}

# (Proyección, Lado del estudio) -> clave de CODIGOS. Lado None = cualquier lado.
TABLA = {
    ("AP de pelvis", None): "pelvis_ap",
    ("AP de cadera", "Izquierdo"): "cadera_izq_ap",
    ("AP de cadera", "Derecho"): "cadera_der_ap",
}

# Por qué no hay código, cuando no lo hay.
MOTIVOS = {
    ("AP de cadera", "Bilateral"): "El Playbook no tiene un código de AP bilateral de cadera; "
                                   "si el estudio es una AP de pelvis, elige esa proyección.",
    ("AP de cadera", "Sin lado"): "Una AP de cadera necesita lado (izquierdo o derecho).",
    ("AP de cadera", None): "Falta el lado del estudio.",
    ("Axial (lateral) de cadera", None): "Pendiente: los radiólogos deciden a qué vista del "
                                         "Playbook corresponde la axial.",
    ("Otra", None): "La proyección «Otra» no tiene código asignado.",
}


def codigo_estudio(proyeccion: str | None, lado: str | None) -> dict:
    """Código LOINC del estudio, o None con el motivo. Nunca lanza excepciones."""
    base = {"loinc": None, "nombre_loinc": None, "motivo": None, "proyeccion": proyeccion or None,
            "lado": lado or None, "version_loinc": VERSION_LOINC, "version_regla": VERSION_REGLA}
    if not proyeccion:
        return {**base, "motivo": "Falta la proyección."}
    clave = TABLA.get((proyeccion, lado)) or TABLA.get((proyeccion, None))
    if clave:
        codigo, nombre = CODIGOS[clave]
        return {**base, "loinc": codigo, "nombre_loinc": nombre}
    motivo = (MOTIVOS.get((proyeccion, lado or None)) or MOTIVOS.get((proyeccion, None))
              or "No hay código LOINC para esta combinación.")
    return {**base, "motivo": motivo}
