import os
import json
import shutil
import uuid
import subprocess
import tempfile
import tracemalloc
import unicodedata
from pathlib import Path

import torch
import soundfile as sf
import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from transformers import pipeline
from datetime import datetime

from marcado import marcar, version_diccionario
from prellenado import comparar, prellenar, validar_confirmacion

# ── Configuración ────────────────────────────────────────────────
MODELO = "openai/whisper-small"
IDIOMA = "es"
VENTANA_S = 30
SOLAPE_S = 2          # avance de 28 s por ventana
SOLAPE_PALABRAS = 6   # para la fusión tolerante
UMBRAL_SIMILITUD = 0.6

BASE_DIR = Path(__file__).resolve().parent
CARPETA_EXPEDIENTES = BASE_DIR / "expedientes"
ARCHIVO_ESTADISTICAS = BASE_DIR / "estadisticas.json"
CARPETA_STATIC = BASE_DIR / "static"

CARPETA_EXPEDIENTES.mkdir(exist_ok=True)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Carga del modelo ─────────────────────────────────────────────
print("Cargando Whisper small...")
pipe = pipeline(
    "automatic-speech-recognition",
    model=MODELO,
    device=-1,  # CPU
    chunk_length_s=VENTANA_S,
    stride_length_s=SOLAPE_S,
)
print("Modelo listo.")


# ── Utilidades de fusión tolerante ───────────────────────────────
def _similitud(a: str, b: str) -> float:
    """Fracción de palabras en común entre dos textos."""
    pa, pb = a.split(), b.split()
    if not pa or not pb:
        return 0.0
    comunes = len(set(pa) & set(pb))
    return comunes / max(len(pa), len(pb))


def fusionar_textos(partes, solape_palabras=SOLAPE_PALABRAS):
    """Une ventanas eliminando el solape, tolerando diferencias menores."""
    if not partes:
        return ""
    resultado = partes[0]
    for siguiente in partes[1:]:
        palabras_res = resultado.split()
        palabras_sig = siguiente.split()
        mejor = 0
        mejor_sim = 0.0
        limite = min(len(palabras_res), len(palabras_sig), solape_palabras * 2)
        for n in range(3, limite + 1):
            fin_res = " ".join(palabras_res[-n:])
            ini_sig = " ".join(palabras_sig[:n])
            s = _similitud(fin_res, ini_sig)
            if s > mejor_sim:
                mejor_sim = s
                mejor = n
        if mejor and mejor_sim >= UMBRAL_SIMILITUD:
            resultado = resultado + " " + " ".join(palabras_sig[mejor:])
        else:
            resultado = resultado + " " + siguiente
    return resultado


def transcribir_audio(ruta_wav: str):
    """Divide en ventanas con solape usando soundfile y fusiona tolerando diferencias.

    Devuelve (texto, duracion_segundos, ram_mb).
    """
    tracemalloc.start()
    base_snapshot = tracemalloc.take_snapshot()

    datos, sr = sf.read(ruta_wav, dtype="float32")
    if datos.ndim == 2:
        datos = datos.mean(axis=1)  # mono
    onda = torch.from_numpy(datos).unsqueeze(0)  # (1, muestras)
    duracion = onda.shape[1] / sr
    avance = (VENTANA_S - SOLAPE_S) * sr

    partes = []
    inicio = 0
    while inicio < onda.shape[1]:
        fin = min(inicio + VENTANA_S * sr, onda.shape[1])
        segmento = onda[:, inicio:fin]
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            sf.write(tmp.name, segmento.squeeze(0).numpy(), sr)
            tmp_path = tmp.name
        try:
            res = pipe(tmp_path, generate_kwargs={"language": IDIOMA})
            partes.append(res["text"].strip())
        finally:
            os.unlink(tmp_path)
        if fin >= onda.shape[1]:
            break
        inicio += avance

    texto = fusionar_textos(partes)

    # ── Medición de RAM ─────────────────────────────
    final_snapshot = tracemalloc.take_snapshot()
    tracemalloc.stop()
    stats = final_snapshot.compare_to(base_snapshot, "filename")
    ram_bytes = sum(s.size_diff for s in stats)
    ram_mb = round(ram_bytes / (1024 * 1024), 2)
    # ────────────────────────────────────────────────

    return texto, round(duracion, 2), ram_mb


# ── Modelo de entrada para guardar ───────────────────────────────
class Marca(BaseModel):
    texto: str = ""
    color: str = "verde"
    inicio: int = 0
    fin: int = 0
    # Campos del marcado automático (opcionales en las marcas manuales)
    sugerencia: str | None = None
    motivo: str | None = None
    rid: str | None = None
    origen: str = "radiologo"   # "auto" si la puso el diccionario


class DecisionLado(BaseModel):
    """Lado del estudio que eligió el radiólogo, con el motivo si DICOM y dictado no coinciden."""
    eleccion: str | None = None
    motivo: str | None = None
    lado_dicom: str | None = None   # capturado a mano hasta que Aurora lo envíe desde el DICOM


class GuardarRequest(BaseModel):
    texto: str
    marcas: list[Marca] = []
    # Plantilla v0.4: lo que confirmó el radiólogo después del prellenado.
    campos_confirmados: dict[str, str | None] = {}
    lado_estudio: DecisionLado | None = None


# ── Rutas ────────────────────────────────────────────────────────
@app.post("/api/transcribir")
async def api_transcribir(audio: UploadFile = File(...), lado_dicom: str | None = Form(None)):
    contenido = await audio.read()
    sufijo = Path(audio.filename or "audio.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=sufijo, delete=False) as tmp:
        tmp.write(contenido)
        tmp_path = tmp.name

    wav_path = tmp_path
    if sufijo.lower() != ".wav":
        wav_path = tmp_path.rsplit(".", 1)[0] + ".wav"
        subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_path, "-ar", "16000", "-ac", "1", wav_path],
            check=True, capture_output=True,
        )

    try:
        texto, duracion, ram_mb = transcribir_audio(wav_path)
    finally:
        os.unlink(tmp_path)
        if wav_path != tmp_path and os.path.exists(wav_path):
            os.unlink(wav_path)

    print(f"[RAM transcripción] {ram_mb} MB")
    texto = unicodedata.normalize("NFC", texto)
    marcas = marcar(texto)
    try:
        prellenado = prellenar(texto, marcas, lado_dicom)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"texto": texto, "marcas": marcas, "duracion": duracion, "idioma": IDIOMA,
            "version_diccionario": version_diccionario(), "prellenado": prellenado}


@app.post("/api/prellenar")
async def api_prellenar(datos: dict):
    """Recalcula el prellenado (por ejemplo, cuando el radiólogo captura el lado del DICOM)."""
    try:
        return prellenar(datos.get("texto", ""), None, datos.get("lado_dicom"))
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/api/guardar")
async def api_guardar(datos: GuardarRequest):
    # El prellenado se recalcula aquí, igual que las marcas automáticas: lo que se mide es
    # lo que propuso el sistema, no lo que mande el navegador.
    decision = datos.lado_estudio.model_dump() if datos.lado_estudio else None
    try:
        prellenado = prellenar(datos.texto, None, (decision or {}).get("lado_dicom"))
        validar_confirmacion(datos.campos_confirmados, decision, prellenado)
    except ValueError as e:
        raise HTTPException(422, str(e))
    plantilla = None
    if datos.campos_confirmados or decision:
        plantilla = {
            "campos_prellenados": prellenado,
            "campos_confirmados": datos.campos_confirmados,
            "diferencias": comparar(prellenado, datos.campos_confirmados),
            "lado_estudio": {**prellenado["lado_estudio"], "decision": decision},
        }
    exp_id = f"{uuid.uuid4().hex[:8]}"
    carpeta = CARPETA_EXPEDIENTES / exp_id
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "transcripcion.json").write_text(
        json.dumps(
            {
                "texto": datos.texto,
                # Marcas finales, después de la revisión del radiólogo
                "marcas": [m.model_dump() for m in datos.marcas],
                # Lo que propuso el diccionario, para comparar con la corrección
                # del radiólogo (pares para el aprendizaje activo)
                "marcas_automaticas": marcar(datos.texto),
                "version_diccionario": version_diccionario(),
                # Plantilla v0.4: prellenado, confirmación, diferencias y lado del estudio
                "plantilla": plantilla,
                "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return {"id": exp_id}


@app.get("/api/expedientes")
async def api_expedientes():
    lista = []
    for carpeta in sorted(CARPETA_EXPEDIENTES.iterdir(), reverse=True):
        archivo = carpeta / "transcripcion.json"
        if archivo.exists():
            datos = json.loads(archivo.read_text(encoding="utf-8"))
            lista.append({
                "id": carpeta.name,
                "texto": datos.get("texto", ""),
                "fecha": datos.get("fecha", ""),
            })
    return lista


@app.get("/api/expedientes/{exp_id}")
async def api_expediente(exp_id: str):
    archivo = CARPETA_EXPEDIENTES / exp_id / "transcripcion.json"
    if not archivo.exists():
        raise HTTPException(404, "Expediente no encontrado")
    return json.loads(archivo.read_text(encoding="utf-8"))


@app.delete("/api/expedientes/{exp_id}")
async def api_eliminar(exp_id: str):
    carpeta = CARPETA_EXPEDIENTES / exp_id
    if not carpeta.exists():
        raise HTTPException(404, "Expediente no encontrado")
    shutil.rmtree(carpeta)
    return {"ok": True}


app.mount("/", StaticFiles(directory=CARPETA_STATIC, html=True), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
