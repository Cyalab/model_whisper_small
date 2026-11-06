"""Pruebas del marcado automático. Ejecutar con:  python -m pytest tests  (o  python tests/test_marcado.py)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from marcado import Marcador  # noqa: E402

M = Marcador()


def colores(texto):
    return {(m["texto"], m["color"]) for m in M.marcar(texto)}


def test_termino_oficial_en_verde():
    assert ("fractura subcapital", "verde") not in colores("x")  # sanity
    c = colores("Se observa fractura subcapital izquierda no desplazada.")
    assert ("subcapital", "verde") in c
    assert ("izquierda", "verde") in c
    assert ("no desplazada", "verde") in c
    assert ("fractura", "verde") in c


def test_frase_mas_larga_gana():
    c = colores("Fractura parcialmente desplazada.")
    assert ("parcialmente desplazada", "verde") in c
    assert ("desplazada", "verde") not in c


def test_sin_acento_en_amarillo():
    marcas = M.marcar("Fractura del femur con cabeza femoral integra.")
    m = next(x for x in marcas if x["texto"] == "femur")
    assert m["color"] == "amarillo" and m["sugerencia"] == "fémur"


def test_sinonimo_y_abreviatura_en_amarillo():
    marcas = {x["texto"]: x for x in M.marcar("Fx mediocervical derecha con coxartrosis.")}
    assert marcas["Fx"]["color"] == "amarillo" and marcas["Fx"]["sugerencia"] == "fractura"
    assert marcas["mediocervical"]["sugerencia"] == "transcervical"
    assert marcas["coxartrosis"]["sugerencia"] == "cambios degenerativos"


def test_genero_y_numero():
    c = colores("Trazos desplazados y fracturas conminutas.")
    assert ("desplazados", "verde") in c
    assert ("fracturas", "verde") in c
    assert ("conminutas", "verde") in c


def test_error_de_transcripcion_en_rojo():
    marcas = {x["texto"]: x for x in M.marcar("Datos de costeopenia difusa.")}
    assert marcas["costeopenia"]["color"] == "rojo"
    assert marcas["costeopenia"]["sugerencia"] == "osteopenia"


def test_texto_comun_sin_marcas():
    assert M.marcar("Hoy me desperté tarde y revisé el clima.") == []


def test_posiciones_coinciden_con_el_texto():
    texto = "Fractura basicervical del cuello del fémur, Garden III."
    for m in M.marcar(texto):
        assert texto[m["inicio"]:m["fin"]] == m["texto"]


if __name__ == "__main__":
    fallas = 0
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            try:
                fn(); print("ok  ", nombre)
            except AssertionError as e:
                fallas += 1; print("FALLA", nombre, e)
    sys.exit(1 if fallas else 0)
