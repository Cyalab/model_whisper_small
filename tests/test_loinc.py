"""Código LOINC del estudio (capa 2). Solo textos inventados, sin datos de pacientes."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loinc import AVISO_LOINC, CODIGOS, codigo_estudio  # noqa: E402
from prellenado import VALORES, prellenar  # noqa: E402


def test_ap_de_pelvis_no_depende_del_lado():
    for lado in (None, "Sin lado", "Izquierdo", "Bilateral"):
        r = codigo_estudio("AP de pelvis", lado)
        assert (r["loinc"], r["nombre_loinc"]) == ("37622-8", "XR Pelvis AP")


def test_ap_de_cadera_con_lado():
    assert codigo_estudio("AP de cadera", "Izquierdo")["loinc"] == "36582-5"
    assert codigo_estudio("AP de cadera", "Derecho")["loinc"] == "37726-7"
    assert codigo_estudio("AP de cadera", "Izquierdo")["correspondencia"] == "exacta"


def test_ap_de_cadera_sin_lado_y_bilateral_como_en_el_excel():
    r = codigo_estudio("AP de cadera", "Sin lado")
    assert (r["loinc"], r["correspondencia"]) == ("36581-7", "exacta")
    r = codigo_estudio("AP de cadera", "Bilateral")
    assert (r["loinc"], r["correspondencia"]) == ("26400-2", "aproximada")
    assert r["nota"]


def test_sin_codigo_explica_el_motivo():
    for proy, lado in [("AP de cadera", None), ("AP de cadera", ""),
                       ("Axial (lateral) de cadera", "Izquierdo"), ("Otra", None), (None, "Derecho")]:
        r = codigo_estudio(proy, lado)
        assert r["loinc"] is None and r["nombre_loinc"] is None
        assert r["motivo"]


def test_toda_combinacion_de_la_plantilla_responde_sin_error():
    for proy in VALORES["Proyección"] + [None, ""]:
        for lado in VALORES["Lado del estudio"] + [None, ""]:
            r = codigo_estudio(proy, lado)
            assert (r["loinc"] is None) == bool(r["motivo"])
            assert (r["loinc"] is None) == (r["correspondencia"] is None)
            assert r["version_loinc"] == "2.83"


def test_codigos_existen_en_el_subconjunto_del_playbook():
    """Si está disponible el subconjunto del repositorio de análisis, cada código y nombre coinciden."""
    ruta = Path(__file__).resolve().parents[2] / "aurora-analisis/capa2_loinc/estudios_cadera_pelvis_loinc_2_83.json"
    if not ruta.exists():
        return
    estudios = {e["loinc"]: e for e in json.loads(ruta.read_text(encoding="utf-8"))["estudios"]}
    for codigo, nombre, _corresp, _nota in CODIGOS.values():
        assert codigo in estudios and estudios[codigo]["nombre_loinc"] == nombre
        assert estudios[codigo]["estado"] == "ACTIVE"


def test_prellenado_propone_codigo_con_proyeccion_y_lado():
    p = prellenar("Proyección AP de cadera derecha. Fractura subcapital derecha.")
    assert p["campos"]["Proyección"]["valor"] == "AP de cadera"
    assert p["lado_estudio"]["propuesta"] == "Derecho"
    assert p["estudio_loinc"]["loinc"] == "37726-7"


def test_prellenado_sin_lado_no_propone_codigo_de_cadera():
    p = prellenar("Proyección AP de cadera. Sin fractura.")
    assert p["estudio_loinc"]["loinc"] is None


def test_aviso_de_licencia():
    assert "Regenstrief Institute" in AVISO_LOINC and "loinc.org/license" in AVISO_LOINC


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
