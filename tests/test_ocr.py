"""Pruebas del OCR de notas. Ejecutar con:  python tests/test_ocr.py

No necesitan Ollama ni el modelo: un servidor falso en este mismo proceso responde como
Ollama. Las notas son inventadas. Nunca usar notas reales en las pruebas ni en el repositorio.
"""
import base64
import io
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ocr  # noqa: E402

NOTA = ("Rx AP de pelvis. Fractura subcapital izquierda desplazada, Garden IV. "
        "Osteopenia. Sin material de osteosintesis.")


class _FalsoOllama(BaseHTTPRequestHandler):
    respuesta = NOTA
    estado = 200
    recibido = {}

    def do_POST(self):  # noqa: N802
        largo = int(self.headers.get("Content-Length", 0))
        _FalsoOllama.recibido = {"ruta": self.path, "cuerpo": json.loads(self.rfile.read(largo))}
        self.send_response(_FalsoOllama.estado)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if _FalsoOllama.estado == 200:
            cuerpo = {"message": {"role": "assistant", "content": _FalsoOllama.respuesta}}
        else:
            cuerpo = {"error": "model not found"}
        self.wfile.write(json.dumps(cuerpo).encode("utf-8"))

    def log_message(self, *a):
        pass


def _servidor():
    srv = HTTPServer(("127.0.0.1", 0), _FalsoOllama)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def _png(ancho=2400, alto=1800):
    from PIL import Image
    salida = io.BytesIO()
    Image.new("RGB", (ancho, alto), "white").save(salida, format="PNG")
    return salida.getvalue()


def test_peticion_a_ollama():
    srv, url = _servidor()
    try:
        _FalsoOllama.respuesta, _FalsoOllama.estado = NOTA, 200
        r = ocr.leer_nota(_png(), modelo="qwen3-vl:2b-instruct", url=url)
        c = _FalsoOllama.recibido["cuerpo"]
        assert _FalsoOllama.recibido["ruta"] == "/api/chat"
        assert c["model"] == "qwen3-vl:2b-instruct" and c["stream"] is False
        assert c["options"]["temperature"] == 0
        assert c["think"] is False and c["options"]["num_predict"] == ocr.MAX_TOKENS
        assert len(c["messages"][0]["images"]) == 1
        assert r["texto"] == NOTA and r["modelo"] == "qwen3-vl:2b-instruct" and r["ilegibles"] == 0
    finally:
        srv.shutdown()


def test_reduce_fotos_grandes():
    from PIL import Image
    reducida = Image.open(io.BytesIO(ocr._reducir(_png(4000, 3000))))
    assert max(reducida.size) == ocr.LADO_MAXIMO_PX
    assert reducida.size == (ocr.LADO_MAXIMO_PX, ocr.LADO_MAXIMO_PX * 3 // 4)


def test_solo_procesador():
    srv, url = _servidor()
    try:
        _FalsoOllama.respuesta, _FalsoOllama.estado = NOTA, 200
        ocr.leer_nota(_png(), url=url)          # por omisión: solo procesador
        assert _FalsoOllama.recibido["cuerpo"]["options"]["num_gpu"] == 0
        ocr.leer_nota(_png(), url=url, capas_gpu="auto")   # la tarjeta la decide Ollama
        assert "num_gpu" not in _FalsoOllama.recibido["cuerpo"]["options"]
        ocr.leer_nota(_png(), url=url, capas_gpu=99)
        assert _FalsoOllama.recibido["cuerpo"]["options"]["num_gpu"] == 99
    finally:
        srv.shutdown()


def test_limpia_lo_que_agrega_el_modelo():
    assert ocr.limpiar("```\nFractura subcapital\n```") == "Fractura subcapital"
    assert ocr.limpiar("Transcripción: Fractura subcapital") == "Fractura subcapital"
    assert ocr.limpiar('"Garden III"') == "Garden III"
    # NFC: la «á» descompuesta (a + acento) queda como un solo carácter, igual que en el dictado
    assert ocr.limpiar("Radiográfia") == "Radiográfia"


def test_cuenta_ilegibles():
    srv, url = _servidor()
    try:
        _FalsoOllama.respuesta, _FalsoOllama.estado = "Fractura [ilegible] izquierda [ilegible]", 200
        assert ocr.leer_nota(_png(), url=url)["ilegibles"] == 2
    finally:
        srv.shutdown()


def test_nota_entra_al_mismo_prellenado():
    srv, url = _servidor()
    try:
        _FalsoOllama.respuesta, _FalsoOllama.estado = NOTA, 200
        r = ocr.procesar_nota(_png(), lado_dicom="Izquierdo", url=url)
        v = {k: c["valor"] for k, c in r["prellenado"]["campos"].items()}
        assert r["origen"] == "nota"
        assert v["Grupo AO/OTA"] == "31B1 Subcapital"
        assert v["Grado de Garden"] == "IV"
        assert v["Lado del hallazgo"] == "Izquierdo"
        assert v["Osteopenia"] == "Sí"
        assert any(m["color"] in ("verde", "amarillo") for m in r["marcas"])
    finally:
        srv.shutdown()


def test_modelo_no_descargado():
    srv, url = _servidor()
    try:
        _FalsoOllama.estado = 404
        try:
            ocr.leer_nota(_png(), modelo="qwen3-vl:2b", url=url)
            assert False, "debió fallar"
        except ocr.ErrorOCR as e:
            assert "ollama pull qwen3-vl:2b" in str(e)
    finally:
        _FalsoOllama.estado = 200
        srv.shutdown()


def test_ollama_apagado():
    try:
        ocr.leer_nota(_png(), url="http://127.0.0.1:9")
        assert False, "debió fallar"
    except ocr.ErrorOCR as e:
        assert "No se pudo conectar con Ollama" in str(e)


def test_imagen_vacia_o_invalida():
    for imagen in (b"", b"esto no es una imagen"):
        try:
            ocr.leer_nota(imagen, url="http://127.0.0.1:9")
            assert False, "debió fallar"
        except ocr.ErrorOCR:
            pass


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
