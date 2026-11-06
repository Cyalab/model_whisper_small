"""Marcado automático de transcripciones con el diccionario de cadera.

Colores (los mismos del editor):
  verde    -> el término está en el diccionario y está bien escrito.
  amarillo -> el término está en el diccionario, pero sin acento, como sinónimo
              o como abreviatura. Se sugiere el término oficial.
  rojo     -> palabra desconocida muy parecida a un término del diccionario:
              probable error de transcripción. Se sugiere el término.

Las posiciones (inicio, fin) son índices sobre el texto plano en forma NFC,
igual que las marcas manuales del editor (fin exclusivo).
"""
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

RUTA_DICCIONARIO = Path(__file__).resolve().parent / "diccionario" / "diccionario_cadera.json"
LONGITUD_MINIMA_DIFUSA = 6     # solo palabras largas se comparan de forma aproximada
UMBRAL_DIFUSO = 0.85           # parecido mínimo para marcar en rojo
CATEGORIAS_SIN_DIFUSO = {"lado", "garden"}


def _plegar_caracter(c: str) -> str:
    """Minúsculas y sin acentos, conservando un carácter por carácter."""
    base = unicodedata.normalize("NFD", c)[0]
    return base.lower() if len(base.lower()) == 1 else c


def plegar(texto: str) -> str:
    return "".join(_plegar_caracter(c) for c in texto)


def _variantes(forma: str):
    """La forma y sus variantes de género y número en la última palabra."""
    palabras = forma.split()
    ultima = palabras[-1]
    if ultima.isupper() or len(ultima) < 3:      # abreviaturas y numerales romanos
        return [forma]
    salida = {forma}
    candidatas = {ultima}
    if ultima.endswith("a"):
        candidatas.add(ultima[:-1] + "o")
    elif ultima.endswith("o"):
        candidatas.add(ultima[:-1] + "a")
    for c in list(candidatas):
        candidatas.add(c + ("s" if c[-1] in "aeiouáéíóú" else "es"))
    for c in candidatas:
        salida.add(" ".join(palabras[:-1] + [c]))
    return sorted(salida)


class Marcador:
    def __init__(self, ruta=RUTA_DICCIONARIO):
        datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
        self.version = datos.get("version", "?")
        self.formas = []        # (forma_plegada, forma, tipo, entrada)
        self.palabras_difusas = {}  # palabra_plegada -> (forma, entrada)
        vistas = set()
        for e in datos["terminos"]:
            grupos = [("oficial", [e["termino"]]), ("sinonimo", e.get("sinonimos", [])),
                      ("abreviatura", e.get("abreviaturas", []))]
            for tipo, formas in grupos:
                for base in formas:
                    for forma in _variantes(base):
                        p = plegar(forma)
                        if p in vistas:
                            continue
                        vistas.add(p)
                        self.formas.append((p, forma, tipo, e))
                        if (" " not in p and len(p) >= LONGITUD_MINIMA_DIFUSA
                                and e["categoria"] not in CATEGORIAS_SIN_DIFUSO):
                            self.palabras_difusas[p] = (forma, e)
        # Primero las formas más largas, para que "fractura subcapital" gane a "fractura".
        self.formas.sort(key=lambda t: len(t[0]), reverse=True)
        self._patrones = [(re.compile(r"(?<!\w)" + re.escape(p) + r"(?!\w)"), forma, tipo, e)
                          for p, forma, tipo, e in self.formas]

    def marcar(self, texto: str):
        texto = unicodedata.normalize("NFC", texto)
        plegado = plegar(texto)
        ocupado = [False] * len(texto)
        marcas = []

        def libre(i, j):
            return not any(ocupado[i:j])

        def tomar(i, j, color, motivo, e, sugerencia=None):
            for k in range(i, j):
                ocupado[k] = True
            marcas.append({
                "texto": texto[i:j], "color": color, "inicio": i, "fin": j,
                "sugerencia": sugerencia, "motivo": motivo,
                "rid": e.get("rid"), "origen": "auto",
            })

        for patron, forma, tipo, e in self._patrones:
            for m in patron.finditer(plegado):
                i, j = m.span()
                if not libre(i, j):
                    continue
                if tipo == "oficial":
                    if texto[i:j].casefold() == forma.casefold():
                        tomar(i, j, "verde", "término del diccionario", e)
                    else:
                        tomar(i, j, "amarillo", "falta acento o letra", e, sugerencia=forma)
                elif tipo == "sinonimo":
                    tomar(i, j, "amarillo", "sinónimo; término oficial sugerido", e, sugerencia=e["termino"])
                else:
                    tomar(i, j, "amarillo", "abreviatura; término oficial sugerido", e, sugerencia=e["termino"])

        # Palabras no reconocidas que se parecen mucho a un término: probable error.
        for m in re.finditer(r"\w+", plegado):
            i, j = m.span()
            palabra = m.group()
            if len(palabra) < LONGITUD_MINIMA_DIFUSA or not libre(i, j):
                continue
            mejor, puntaje = None, 0.0
            for p, (forma, e) in self.palabras_difusas.items():
                s = SequenceMatcher(None, palabra, p).ratio()
                if s > puntaje:
                    mejor, puntaje = (forma, e), s
            if mejor is not None and puntaje >= UMBRAL_DIFUSO:
                forma, e = mejor
                tomar(i, j, "rojo", "posible error de transcripción", e, sugerencia=forma)

        marcas.sort(key=lambda x: x["inicio"])
        return marcas


_marcador = None


def marcar(texto: str):
    """Atajo con un marcador compartido (se carga una sola vez)."""
    global _marcador
    if _marcador is None:
        _marcador = Marcador()
    return _marcador.marcar(texto)


def version_diccionario():
    if _marcador is None:
        marcar("")
    return _marcador.version
