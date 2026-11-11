"""Prellenado de la plantilla de informe estructurado de cadera (v0.4) a partir del dictado.

Decisiones de la líder del proyecto (10 nov 2026):
  - Aurora Voz prellena los campos de la plantilla y el radiólogo confirma.
  - El lado del estudio se propone desde el DICOM y desde el dictado; decide el radiólogo,
    y se guarda su elección y el motivo.
  - Se miden por separado: DICOM contra dictado (lado del estudio) y lo que prellenó
    Aurora Voz contra lo que confirmó el radiólogo. Cada diferencia se registra como
    "cambió" o "faltó". El denominador es el total de casos registrados.

Las REGLAS de este archivo son PROVISIONALES (propuesta de Claude): las validan los
radiólogos antes de usar las métricas. Cada campo prellenado lleva la regla que lo
llenó y el texto que la disparó, para que el radiólogo vea por qué.

Un campo que el dictado no deja claro (dos valores distintos) no se llena: se marca
como conflicto y decide el radiólogo. Nunca se elige uno a ciegas.
"""
from __future__ import annotations

import re
import unicodedata

from marcado import marcar, plegar

VERSION_REGLAS = "0.1-provisional"
VERSION_PLANTILLA = "v0.4"

# Valores permitidos: los mismos de la hoja «Listas» de la plantilla v0.4.
VALORES = {
    "Proyección": ["AP de pelvis", "AP de cadera", "Axial (lateral) de cadera", "Otra"],
    "Lado del estudio": ["Izquierdo", "Derecho", "Bilateral", "Sin lado"],
    "Lado del hallazgo": ["Izquierdo", "Derecho", "Bilateral"],
    "Fractura": ["Presente", "Ausente", "Dudosa"],
    "Grupo AO/OTA": ["31A Trocantérica", "31B1 Subcapital", "31B2 Transcervical",
                     "31B3 Basicervical", "31C Cabeza femoral", "Otra", "No aplica"],
    "Grado de Garden": ["I", "II", "III", "IV", "No aplica"],
    "Desplazamiento": ["No desplazada", "Impactada en valgo", "Parcialmente desplazada",
                       "Desplazada", "No aplica"],
    "Conminución": ["Sí", "No", "No aplica"],
    "Material de osteosíntesis o prótesis": ["Ninguno", "Osteosíntesis", "Prótesis", "Ambos"],
    "Osteopenia": ["Sí", "No", "No valorable"],
    "Cambios degenerativos coxofemorales": ["Ausentes", "Leves", "Moderados", "Severos",
                                            "No valorable"],
}
# Campos que la voz intenta llenar y que entran a la medición. El lado del estudio se mide
# aparte (DICOM contra dictado). Calidad, sutileza, ancho, confianza, otros hallazgos e
# impresión no se prellenan.
CAMPOS_VOZ = [c for c in VALORES if c != "Lado del estudio"]

LADO = {"izquierda": "Izquierdo", "derecha": "Derecho", "bilateral": "Bilateral"}
LADO_DICOM = {"L": "Izquierdo", "R": "Derecho", "B": "Bilateral",
              "IZQUIERDO": "Izquierdo", "DERECHO": "Derecho", "BILATERAL": "Bilateral",
              "SIN LADO": "Sin lado"}
AO = {"subcapital": "31B1 Subcapital", "transcervical": "31B2 Transcervical",
      "basicervical": "31B3 Basicervical", "intertrocantérica": "31A Trocantérica",
      "subtrocantérica": "Otra"}
DESPLAZAMIENTO = {"no desplazada": "No desplazada", "parcialmente desplazada": "Parcialmente desplazada",
                  "desplazada": "Desplazada", "impactada en valgo": "Impactada en valgo"}
GARDEN = {"Garden I": "I", "Garden II": "II", "Garden III": "III", "Garden IV": "IV"}
MATERIAL = {"material de osteosíntesis": "Osteosíntesis", "prótesis": "Prótesis",
            "hemiartroplastia": "Prótesis"}
GRADO = [(r"\bleve(s)?\b", "Leves"), (r"\bmoderad[oa]s?\b", "Moderados"),
         (r"\b(sever[oa]s?|importantes?|avanzad[oa]s?)\b", "Severos")]

NEGACION = re.compile(r"\b(sin|no se (observan?|identifican?|aprecian?|evidencian?|ven?)|no hay|"
                      r"ausencia de|negativ[oa] para|descarta(n|mos)?)\b[^.;,]{0,25}$")
DUDA = re.compile(r"\b(probable|posible|sospecha( de)?|dudos[oa]|no se descarta|"
                  r"no se puede descartar|sugestiv[oa] de)\b[^.;,]{0,25}$")


# ---------------------------------------------------------------- utilidades

def _oraciones(texto: str) -> list[tuple[int, int]]:
    limites, inicio = [], 0
    for m in re.finditer(r"[.;\n]+", texto):
        limites.append((inicio, m.start()))
        inicio = m.end()
    limites.append((inicio, len(texto)))
    return [(a, b) for a, b in limites if b > a]


def _oracion_de(oraciones, pos):
    return next(((a, b) for a, b in oraciones if a <= pos < b), (pos, pos + 1))


def _antes(texto_plegado: str, m: dict, oraciones) -> str:
    a, _ = _oracion_de(oraciones, m["inicio"])
    return texto_plegado[a:m["inicio"]]


def _polaridad(texto_plegado, m, oraciones) -> str:
    """'neg', 'duda' o 'pos' según lo que se dice antes del término, en la misma oración."""
    previo = _antes(texto_plegado, m, oraciones)
    if DUDA.search(previo):          # primero la duda: «no se descarta» no es negación
        return "duda"
    if NEGACION.search(previo):
        return "neg"
    return "pos"


def _evid(m: dict) -> dict:
    return {"texto": m["texto"], "inicio": m["inicio"], "fin": m["fin"], "color": m["color"]}


class _Campos:
    def __init__(self):
        self.propuestas: dict[str, list[tuple[str, str, dict]]] = {c: [] for c in VALORES}

    def proponer(self, campo, valor, regla, marca):
        assert valor in VALORES[campo], (campo, valor)
        self.propuestas[campo].append((valor, regla, marca))

    def resultado(self) -> dict:
        salida = {}
        for campo, props in self.propuestas.items():
            valores = []
            for v, _, _ in props:
                if v not in valores:
                    valores.append(v)
            if not props:
                salida[campo] = {"valor": None, "regla": None, "evidencia": [], "conflicto": None}
            elif len(valores) == 1:
                salida[campo] = {"valor": valores[0], "regla": props[0][1],
                                 "evidencia": [_evid(m) for _, _, m in props if m],
                                 "conflicto": None}
            else:
                salida[campo] = {"valor": None, "regla": "conflicto",
                                 "evidencia": [_evid(m) for _, _, m in props if m],
                                 "conflicto": valores}
        return salida


# ---------------------------------------------------------------- prellenado

def prellenar(texto: str, marcas: list[dict] | None = None, lado_dicom: str | None = None) -> dict:
    """Devuelve los campos propuestos y la propuesta del lado del estudio.

    texto: transcripción. marcas: las del marcado automático (si no se dan, se calculan).
    lado_dicom: lateralidad del DICOM (L, R, B o el valor en español), si se conoce.
    """
    texto = unicodedata.normalize("NFC", texto or "")
    if marcas is None:
        marcas = marcar(texto)
    marcas = sorted((m for m in marcas if m.get("origen") == "auto" and m.get("categoria")),
                    key=lambda m: m["inicio"])
    pleg = plegar(texto)
    oraciones = _oraciones(texto)
    c = _Campos()

    def en_oracion(m, categoria=None, termino=None):
        a, b = _oracion_de(oraciones, m["inicio"])
        return [x for x in marcas if a <= x["inicio"] < b and x is not m
                and (categoria is None or x["categoria"] == categoria)
                and (termino is None or x["termino"] in termino)]

    # R1 Proyección: AP + la región que le sigue (pelvis o cadera); axial o lateral.
    lado_de_proyeccion = []
    for m in (x for x in marcas if x["categoria"] == "proyeccion"):
        # Lo que sigue a la proyección en la misma oración, hasta 30 caracteres y antes de
        # cualquier hallazgo («AP de cadera derecha», no «AP: fractura de cadera derecha»).
        a, b = _oracion_de(oraciones, m["inicio"])
        primer_hallazgo = min((h["inicio"] for h in marcas if h["categoria"] == "hallazgo"
                               and m["fin"] <= h["inicio"] < b), default=b)
        siguientes = [x for x in marcas if 0 <= x["inicio"] - m["fin"] <= 30
                      and x["inicio"] < primer_hallazgo]
        if m["termino"] == "proyección axial":
            c.proponer("Proyección", "Axial (lateral) de cadera", "R1 proyección", m)
        else:
            region = next((x for x in siguientes if x["categoria"] == "anatomia"
                           and x["termino"] in ("pelvis", "cadera", "articulación coxofemoral")), None)
            if region is None:
                continue                      # AP sin región: no se adivina
            valor = "AP de pelvis" if region["termino"] == "pelvis" else "AP de cadera"
            c.proponer("Proyección", valor, "R1 proyección", m)
        # R2 Lado del estudio (dictado): un lado justo después de la proyección y su región.
        lado = next((x for x in siguientes if x["categoria"] == "lado"), None)
        if lado:
            lado_de_proyeccion.append(lado)

    proy = c.resultado()["Proyección"]["valor"]
    lado_dictado, regla_dictado, evid_dictado = None, None, []
    valores_lado = sorted({LADO[x["termino"]] for x in lado_de_proyeccion})
    if len(valores_lado) == 1:
        lado_dictado, regla_dictado = valores_lado[0], "R2 lado junto a la proyección"
        evid_dictado = [_evid(x) for x in lado_de_proyeccion]
    elif not valores_lado and proy == "AP de pelvis":
        lado_dictado, regla_dictado = "Sin lado", "R2 la AP de pelvis no lleva lado"

    # R3 Fractura y R4 lado del hallazgo, R5 grupo AO/OTA (en la oración de la fractura).
    fracturas = [x for x in marcas if x["categoria"] == "hallazgo" and x["termino"].startswith("fractura")]
    for f in fracturas:
        pol = _polaridad(pleg, f, oraciones)
        c.proponer("Fractura", {"pos": "Presente", "neg": "Ausente", "duda": "Dudosa"}[pol], "R3 fractura", f)
        if pol == "neg":
            continue
        lados = [x for x in en_oracion(f, "lado") if x not in lado_de_proyeccion]
        if lados:
            cercano = min(lados, key=lambda x: abs(x["inicio"] - f["inicio"]))
            c.proponer("Lado del hallazgo", LADO[cercano["termino"]], "R4 lado en la oración de la fractura", cercano)
        for loc in en_oracion(f, "localizacion_ao"):
            c.proponer("Grupo AO/OTA", AO[loc["termino"]], "R5 localización en la oración de la fractura", loc)
        if not en_oracion(f, "localizacion_ao"):
            for an in en_oracion(f, "anatomia"):
                if an["termino"] == "cabeza femoral":
                    c.proponer("Grupo AO/OTA", "31C Cabeza femoral", "R5 cabeza femoral con fractura", an)
                elif an["termino"] in ("región trocantérica", "trocánter mayor", "trocánter menor"):
                    c.proponer("Grupo AO/OTA", "31A Trocantérica", "R5 región trocantérica con fractura", an)

    for m in marcas:
        cat, t = m["categoria"], m["termino"]
        if cat == "garden":                                             # R6
            c.proponer("Grado de Garden", GARDEN[t], "R6 Garden", m)
        elif cat == "desplazamiento":                                   # R7
            c.proponer("Desplazamiento", DESPLAZAMIENTO[t], "R7 desplazamiento", m)
        elif t == "conminuta":                                          # R8
            neg = _polaridad(pleg, m, oraciones) == "neg"
            c.proponer("Conminución", "No" if neg else "Sí", "R8 conminución", m)
        elif cat == "material":                                         # R9
            if _polaridad(pleg, m, oraciones) == "neg":
                c.proponer("Material de osteosíntesis o prótesis", "Ninguno", "R9 material negado", m)
            else:
                c.proponer("Material de osteosíntesis o prótesis", MATERIAL[t], "R9 material", m)
        elif t == "osteopenia":                                         # R10
            neg = _polaridad(pleg, m, oraciones) == "neg"
            c.proponer("Osteopenia", "No" if neg else "Sí", "R10 osteopenia", m)
        elif t == "cambios degenerativos":                              # R11
            if _polaridad(pleg, m, oraciones) == "neg":
                c.proponer("Cambios degenerativos coxofemorales", "Ausentes", "R11 degenerativos negados", m)
            else:
                a, b = _oracion_de(oraciones, m["inicio"])
                for patron, valor in GRADO:
                    if re.search(patron, pleg[a:b]):
                        c.proponer("Cambios degenerativos coxofemorales", valor, "R11 grado en la oración", m)
                        break                                           # sin grado: no se llena

    campos = c.resultado()
    # Dos materiales distintos no son conflicto: son «Ambos».
    mat = c.propuestas["Material de osteosíntesis o prótesis"]
    if {v for v, _, _ in mat} == {"Osteosíntesis", "Prótesis"}:
        campos["Material de osteosíntesis o prótesis"].update(
            valor="Ambos", regla="R9 osteosíntesis y prótesis", conflicto=None)
    # Si hay fractura con grupo AO/OTA distinto de 31B, Garden no aplica (no se fuerza nada más).

    return {
        "version_reglas": VERSION_REGLAS,
        "version_plantilla": VERSION_PLANTILLA,
        "campos": {k: v for k, v in campos.items() if k in CAMPOS_VOZ},
        "lado_estudio": lado_estudio(lado_dicom, lado_dictado, regla_dictado, evid_dictado),
        "valores": VALORES,
    }


def normalizar_lado_dicom(valor: str | None) -> str | None:
    if valor is None or not str(valor).strip():
        return None
    v = LADO_DICOM.get(str(valor).strip().upper())
    if v is None:
        raise ValueError(f"Lado del DICOM no reconocido: {valor!r} (use L, R, B o el valor en español)")
    return v


def lado_estudio(lado_dicom, lado_dictado, regla=None, evidencia=None) -> dict:
    dicom = normalizar_lado_dicom(lado_dicom)
    if dicom and lado_dictado:
        estado = "coinciden" if dicom == lado_dictado else "difieren"
    elif dicom:
        estado = "solo_dicom"
    elif lado_dictado:
        estado = "solo_dictado"
    else:
        estado = "ninguno"
    propuesta = None if estado in ("difieren", "ninguno") else (dicom or lado_dictado)
    return {"dicom": dicom, "dictado": lado_dictado, "regla_dictado": regla,
            "evidencia_dictado": evidencia or [], "estado": estado, "propuesta": propuesta,
            "requiere_motivo": estado == "difieren"}


# ---------------------------------------------------------------- confirmación y medición

def validar_confirmacion(confirmados: dict, decision_lado: dict | None, prellenado: dict) -> None:
    """Lanza ValueError si un valor no está permitido o falta el motivo del lado."""
    for campo, valor in (confirmados or {}).items():
        if campo not in CAMPOS_VOZ:
            raise ValueError(f"Campo desconocido: {campo}")
        if valor not in (None, "") and valor not in VALORES[campo]:
            raise ValueError(f"Valor no permitido en «{campo}»: {valor}")
    if decision_lado:
        eleccion = decision_lado.get("eleccion")
        if eleccion not in (None, "") and eleccion not in VALORES["Lado del estudio"]:
            raise ValueError(f"Valor no permitido en «Lado del estudio»: {eleccion}")
        if prellenado["lado_estudio"]["requiere_motivo"] and not (decision_lado.get("motivo") or "").strip():
            raise ValueError("El DICOM y el dictado no coinciden en el lado del estudio: "
                             "escribe el motivo de tu elección.")


def comparar(prellenado: dict, confirmados: dict) -> dict:
    """Por campo: 'igual', 'cambió' (la voz propuso y el radiólogo dejó otro valor, o lo vació)
    o 'faltó' (la voz no propuso y el radiólogo sí llenó). Un conflicto cuenta como no propuesto."""
    salida = {}
    for campo in CAMPOS_VOZ:
        prop = prellenado["campos"].get(campo, {}).get("valor")
        final = (confirmados or {}).get(campo) or None
        if prop == final:
            salida[campo] = "igual"
        elif prop is None:
            salida[campo] = "faltó"
        else:
            salida[campo] = "cambió"
    return salida
