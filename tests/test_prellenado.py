"""Pruebas del prellenado. Ejecutar con:  python tests/test_prellenado.py

Los dictados son inventados. Nunca usar dictados reales en las pruebas ni en el repositorio.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prellenado import comparar, prellenar, validar_confirmacion  # noqa: E402


def campos(texto, **kw):
    p = prellenar(texto, **kw)
    return {k: v["valor"] for k, v in p["campos"].items()}, p


def test_ejemplo_completo():
    v, p = campos("Radiografía AP de pelvis. Fractura subcapital izquierda no desplazada, "
                  "Garden II. Osteopenia. Cambios degenerativos leves.")
    assert v["Proyección"] == "AP de pelvis"
    assert v["Fractura"] == "Presente"
    assert v["Lado del hallazgo"] == "Izquierdo"
    assert v["Grupo AO/OTA"] == "31B1 Subcapital"
    assert v["Desplazamiento"] == "No desplazada"
    assert v["Grado de Garden"] == "II"
    assert v["Osteopenia"] == "Sí"
    assert v["Cambios degenerativos coxofemorales"] == "Leves"
    # la AP de pelvis no lleva lado del estudio, aunque el hallazgo sea izquierdo
    assert p["lado_estudio"]["dictado"] == "Sin lado"


def test_lado_del_estudio_y_del_hallazgo_separados():
    v, p = campos("Proyección AP de cadera derecha. Fractura transcervical derecha desplazada.")
    assert v["Proyección"] == "AP de cadera"
    assert p["lado_estudio"]["dictado"] == "Derecho"
    assert v["Lado del hallazgo"] == "Derecho"
    assert p["campos"]["Lado del hallazgo"]["evidencia"][0]["inicio"] > 30   # no es el de la proyección


def test_negacion_y_duda():
    v, _ = campos("AP de cadera izquierda. Sin fractura. No se observa osteopenia.")
    assert v["Fractura"] == "Ausente" and v["Osteopenia"] == "No"
    v, _ = campos("AP de cadera izquierda. Probable fractura subcapital.")
    assert v["Fractura"] == "Dudosa"
    v, _ = campos("AP de pelvis. No se descarta fractura basicervical derecha.")
    assert v["Fractura"] == "Dudosa"
    # la negación no cruza la coma hacia el siguiente hallazgo
    v, _ = campos("AP de pelvis. Sin datos de osteopenia, fractura subcapital izquierda.")
    assert v["Osteopenia"] == "No" and v["Fractura"] == "Presente"


def test_conflicto_no_se_adivina():
    v, p = campos("AP de pelvis. Fractura subcapital izquierda, Garden II. Se reclasifica como Garden III.")
    assert v["Grado de Garden"] is None
    assert p["campos"]["Grado de Garden"]["conflicto"] == ["II", "III"]


def test_ap_sin_region_no_se_adivina():
    v, _ = campos("Proyección AP. Fractura subcapital derecha.")
    assert v["Proyección"] is None


def test_material_ambos_y_grado_requerido():
    v, _ = campos("AP de cadera derecha con prótesis y material de osteosíntesis. Coxartrosis.")
    assert v["Material de osteosíntesis o prótesis"] == "Ambos"
    assert v["Cambios degenerativos coxofemorales"] is None          # sin grado no se llena
    v, _ = campos("AP de cadera izquierda sin material de osteosíntesis. Coxartrosis severa.")
    assert v["Material de osteosíntesis o prótesis"] == "Ninguno"
    assert v["Cambios degenerativos coxofemorales"] == "Severos"


def test_dicom_contra_dictado():
    _, p = campos("AP de cadera derecha. Fractura subcapital derecha.", lado_dicom="R")
    le = p["lado_estudio"]
    assert le["estado"] == "coinciden" and le["propuesta"] == "Derecho" and not le["requiere_motivo"]
    _, p = campos("AP de cadera derecha. Fractura subcapital derecha.", lado_dicom="L")
    le = p["lado_estudio"]
    assert le["estado"] == "difieren" and le["propuesta"] is None and le["requiere_motivo"]
    _, p = campos("Fractura subcapital derecha.", lado_dicom="L")
    assert p["lado_estudio"]["estado"] == "solo_dicom"


def test_motivo_obligatorio_si_difieren():
    _, p = campos("AP de cadera derecha. Fractura subcapital derecha.", lado_dicom="L")
    try:
        validar_confirmacion({}, {"eleccion": "Derecho", "motivo": ""}, p)
        assert False, "debió pedir el motivo"
    except ValueError as e:
        assert "motivo" in str(e)
    validar_confirmacion({}, {"eleccion": "Derecho", "motivo": "Etiqueta DICOM equivocada"}, p)


def test_valor_no_permitido():
    _, p = campos("AP de pelvis.")
    try:
        validar_confirmacion({"Fractura": "Quizá"}, None, p)
        assert False
    except ValueError:
        pass


def test_comparar_cambio_y_falto():
    _, p = campos("AP de pelvis. Fractura subcapital izquierda, Garden II.")
    final = {k: v["valor"] for k, v in p["campos"].items()}
    final["Grado de Garden"] = "III"          # el radiólogo corrige
    final["Desplazamiento"] = "No desplazada" # la voz no lo había llenado
    final["Osteopenia"] = "Sí"
    d = comparar(p, final)
    assert d["Grado de Garden"] == "cambió"
    assert d["Desplazamiento"] == "faltó" and d["Osteopenia"] == "faltó"
    assert d["Fractura"] == "igual" and d["Conminución"] == "igual"   # ambos vacíos


if __name__ == "__main__":
    pruebas = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    fallas = 0
    for nombre, f in pruebas:
        try:
            f()
            print("ok  ", nombre)
        except AssertionError as e:
            fallas += 1
            print("FALLA", nombre, e)
    sys.exit(1 if fallas else 0)
