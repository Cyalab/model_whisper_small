"""OCR de notas manuscritas para Aurora Voz.

Lee la foto de una nota escrita a mano con un modelo de visión-lenguaje que corre en local
con Ollama (por omisión, Qwen3-VL 2B, que cabe en una tarjeta de 4 GB). El texto leído
entra al mismo camino que un dictado: marcado con el diccionario de cadera, prellenado de
la plantilla v0.4 y confirmación del radiólogo.

Privacidad: la imagen nunca sale del equipo (Ollama corre en local) y este módulo no la
guarda. Una nota manuscrita puede traer nombre, expediente o fechas del paciente: la
detección de datos identificables todavía NO está implementada (ver CAMBIOS_OCR.md).

Uso desde la terminal, sin el servidor ni Whisper:
    python ocr.py nota.jpg
    python ocr.py nota.jpg --modelo qwen2.5vl:3b --lado-dicom Izquierdo
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request

from marcado import marcar, version_diccionario
from prellenado import prellenar

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODELO_OCR = os.environ.get("AURORA_VOZ_OCR_MODELO", "qwen3-vl:2b")
# Las fotos de celular se reducen: menos memoria y menos trabajo para la tarjeta gráfica.
LADO_MAXIMO_PX = int(os.environ.get("AURORA_VOZ_OCR_LADO_PX", "1280"))
# Capas del modelo en la tarjeta gráfica: vacío = las que decida Ollama; 0 = todo en el
# procesador. En tarjetas chicas que también dibujan la pantalla (p. ej. Quadro M1200),
# Windows corta las operaciones largas de la tarjeta ("CUDA error: the launch timed out"):
# con 0 se evita, a cambio de leer más lento.
CAPAS_GPU = os.environ.get("AURORA_VOZ_OCR_CAPAS_GPU", "")
TIEMPO_LIMITE_S = 600      # en CPU o en una tarjeta chica la primera lectura puede tardar
MARCA_ILEGIBLE = "[ilegible]"

INSTRUCCION = (
    "Esta imagen es una nota manuscrita de radiología, en español, sobre una radiografía "
    "de cadera o pelvis. Transcribe exactamente el texto escrito a mano, en el mismo orden "
    "y con los mismos renglones. No corrijas la ortografía, no completes abreviaturas, no "
    "interpretes ni agregues nada. Si una palabra no se puede leer, escribe "
    f"{MARCA_ILEGIBLE} en su lugar. Devuelve solo el texto transcrito."
)


class ErrorOCR(RuntimeError):
    """Falla al leer la nota (Ollama apagado, modelo no descargado, imagen inválida)."""


def _reducir(imagen: bytes) -> bytes:
    """Reduce la imagen a LADO_MAXIMO_PX por lado y la convierte a PNG. Requiere Pillow;
    sin Pillow se envía tal cual."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return imagen
    try:
        with Image.open(io.BytesIO(imagen)) as im:
            im = ImageOps.exif_transpose(im)          # respeta la orientación de la foto
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            im.thumbnail((LADO_MAXIMO_PX, LADO_MAXIMO_PX))
            salida = io.BytesIO()
            im.save(salida, format="PNG")
            return salida.getvalue()
    except Exception as e:  # noqa: BLE001
        raise ErrorOCR(f"No se pudo abrir la imagen: {e}") from e


def _opciones(capas_gpu: str | int | None = None) -> dict:
    opciones = {"temperature": 0}
    capas = CAPAS_GPU if capas_gpu is None else capas_gpu
    if str(capas).strip() != "":
        opciones["num_gpu"] = int(capas)
    return opciones


def _llamar_ollama(imagen_b64: str, modelo: str, url: str, capas_gpu=None) -> str:
    """Pide la transcripción a Ollama (/api/chat) y devuelve el texto de la respuesta."""
    cuerpo = json.dumps({
        "model": modelo,
        "stream": False,
        "messages": [{"role": "user", "content": INSTRUCCION, "images": [imagen_b64]}],
        "options": _opciones(capas_gpu),
    }).encode("utf-8")
    peticion = urllib.request.Request(
        url.rstrip("/") + "/api/chat", data=cuerpo,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(peticion, timeout=TIEMPO_LIMITE_S) as r:
            datos = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detalle = e.read().decode("utf-8", "replace")
        if e.code == 404:
            raise ErrorOCR(f"El modelo {modelo} no está en Ollama. Descárgalo con: "
                           f"ollama pull {modelo}") from e
        if "timed out" in detalle and "CUDA" in detalle:
            raise ErrorOCR("Windows cortó la tarjeta gráfica por tardar demasiado. Usa el "
                           "procesador (AURORA_VOZ_OCR_CAPAS_GPU=0 o --cpu) o un equipo con "
                           f"una tarjeta más grande. Detalle: {detalle}") from e
        raise ErrorOCR(f"Ollama respondió {e.code}: {detalle}") from e
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        raise ErrorOCR(f"No se pudo conectar con Ollama en {url}. ¿Está abierto? ({e})") from e
    return (datos.get("message") or {}).get("content", "")


def limpiar(texto: str) -> str:
    """Quita lo que agrega el modelo alrededor del texto (bloques de código, comillas,
    encabezados como «Transcripción:») y normaliza a NFC, igual que el dictado."""
    t = texto.strip()
    t = re.sub(r"^```[a-zA-Z]*\s*\n?", "", t)
    t = re.sub(r"\n?```\s*$", "", t)
    t = re.sub(r"^(texto\s+)?transcri(to|pción|pcion)\s*:\s*", "", t, flags=re.IGNORECASE)
    if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'«“":
        t = t[1:-1]
    t = re.sub(r"[ \t]+\n", "\n", t)
    return unicodedata.normalize("NFC", t.strip())


def leer_nota(imagen: bytes, modelo: str | None = None, url: str | None = None,
              capas_gpu=None) -> dict:
    """Transcribe la nota. Devuelve {texto, modelo, segundos, ilegibles}."""
    if not imagen:
        raise ErrorOCR("La imagen está vacía.")
    modelo = modelo or MODELO_OCR
    inicio = time.monotonic()
    crudo = _llamar_ollama(base64.b64encode(_reducir(imagen)).decode("ascii"),
                           modelo, url or OLLAMA_URL, capas_gpu)
    texto = limpiar(crudo)
    if not texto:
        raise ErrorOCR("El modelo no devolvió texto. Prueba con una foto más nítida.")
    return {
        "texto": texto,
        "modelo": modelo,
        "segundos": round(time.monotonic() - inicio, 2),
        "ilegibles": texto.count(MARCA_ILEGIBLE),
    }


def procesar_nota(imagen: bytes, lado_dicom: str | None = None,
                  modelo: str | None = None, url: str | None = None, capas_gpu=None) -> dict:
    """OCR + marcado + prellenado: la misma respuesta que /api/transcribir, con origen «nota»."""
    lectura = leer_nota(imagen, modelo, url, capas_gpu)
    marcas = marcar(lectura["texto"])
    return {
        "texto": lectura["texto"],
        "marcas": marcas,
        "origen": "nota",
        "modelo_ocr": lectura["modelo"],
        "segundos": lectura["segundos"],
        "ilegibles": lectura["ilegibles"],
        "idioma": "es",
        "version_diccionario": version_diccionario(),
        "prellenado": prellenar(lectura["texto"], marcas, lado_dicom),
    }


def _main() -> int:
    p = argparse.ArgumentParser(description="Lee una nota manuscrita y prellena la plantilla.")
    p.add_argument("imagen", help="foto de la nota (JPG o PNG)")
    p.add_argument("--modelo", default=None, help=f"modelo de Ollama (por omisión {MODELO_OCR})")
    p.add_argument("--lado-dicom", default=None, help="Izquierdo, Derecho, Bilateral o Sin lado")
    p.add_argument("--url", default=None, help=f"dirección de Ollama (por omisión {OLLAMA_URL})")
    p.add_argument("--cpu", action="store_true", help="leer solo con el procesador (sin tarjeta)")
    a = p.parse_args()
    try:
        with open(a.imagen, "rb") as f:
            r = procesar_nota(f.read(), a.lado_dicom, a.modelo, a.url, 0 if a.cpu else None)
    except (ErrorOCR, ValueError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    campos = {k: v.get("valor") for k, v in r["prellenado"]["campos"].items()}
    print(f"Modelo: {r['modelo_ocr']} · {r['segundos']} s · palabras ilegibles: {r['ilegibles']}\n")
    print("Texto leído:\n" + r["texto"] + "\n")
    print("Marcas: " + ", ".join(f"{m['texto']} ({m['color']})" for m in r["marcas"]) + "\n")
    print("Campos prellenados:")
    for k, v in campos.items():
        print(f"  {k}: {v if v else '—'}")
    print(f"  Lado del estudio (dictado/nota): {r['prellenado']['lado_estudio'].get('dictado')}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
