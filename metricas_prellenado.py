"""Métricas del prellenado a partir de los expedientes guardados.

Decisiones de la líder del proyecto (10 nov 2026):
  - Se miden por separado (1) el lado del estudio, DICOM contra dictado, y (2) lo que
    prellenó Aurora Voz contra lo que confirmó el radiólogo.
  - Cada diferencia se registra como «cambió» o «faltó».
  - El denominador de cada campo es el total de casos registrados (expedientes con plantilla).

No imprime ni copia el texto de los dictados: solo conteos.

Uso:  python metricas_prellenado.py [carpeta_expedientes] [--csv salida.csv]
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from prellenado import CAMPOS_VOZ


def leer(carpeta: Path):
    for archivo in sorted(carpeta.glob("*/transcripcion.json")):
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        if datos.get("plantilla"):
            yield datos["plantilla"]


def calcular(carpeta: Path) -> dict:
    casos = list(leer(carpeta))
    n = len(casos)
    por_campo = defaultdict(Counter)
    lado = Counter()
    decision_contra = Counter()
    con_motivo = 0
    versiones = Counter()
    for p in casos:
        versiones[p["campos_prellenados"]["version_reglas"]] += 1
        for campo in CAMPOS_VOZ:
            por_campo[campo][p["diferencias"].get(campo, "igual")] += 1
        le = p["lado_estudio"]
        lado[le["estado"]] += 1
        dec = le.get("decision") or {}
        elec = dec.get("eleccion")
        if elec:
            if le["estado"] == "difieren":
                decision_contra["eligió el DICOM" if elec == le["dicom"] else
                                "eligió el dictado" if elec == le["dictado"] else "eligió otro"] += 1
            elif le["propuesta"] and elec != le["propuesta"]:
                decision_contra["cambió la propuesta"] += 1
        if (dec.get("motivo") or "").strip():
            con_motivo += 1
    return {"casos": n, "por_campo": por_campo, "lado": lado, "decision": decision_contra,
            "con_motivo": con_motivo, "versiones_reglas": versiones}


def tasa(k, n):
    return f"{k} ({100 * k / n:.1f} %)" if n else "—"


def main():
    args = sys.argv[1:]
    salida_csv = None
    if "--csv" in args:
        i = args.index("--csv")
        salida_csv = Path(args[i + 1])
        args = args[:i] + args[i + 2:]
    carpeta = Path(args[0]) if args else Path(__file__).resolve().parent / "expedientes"
    r = calcular(carpeta)
    n = r["casos"]
    print(f"Casos registrados con plantilla: {n}")
    print(f"Versiones de las reglas: {dict(r['versiones_reglas'])}")
    if not n:
        return

    print("\n1) Lado del estudio: DICOM contra dictado (denominador: total de casos)")
    for estado in ("coinciden", "difieren", "solo_dicom", "solo_dictado", "ninguno"):
        print(f"   {estado:<13} {tasa(r['lado'][estado], n)}")
    for k, v in r["decision"].items():
        print(f"   {k:<22} {v}")
    print(f"   decisiones con motivo  {r['con_motivo']}")

    print("\n2) Prellenado contra confirmación (denominador: total de casos)")
    print(f"   {'campo':<38} {'igual':>14} {'cambió':>14} {'faltó':>14}")
    filas = []
    for campo in CAMPOS_VOZ:
        c = r["por_campo"][campo]
        print(f"   {campo:<38} {tasa(c['igual'], n):>14} {tasa(c['cambió'], n):>14} {tasa(c['faltó'], n):>14}")
        filas.append({"campo": campo, "casos": n, "igual": c["igual"], "cambio": c["cambió"],
                      "falto": c["faltó"]})
    if salida_csv:
        with open(salida_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(filas[0]))
            w.writeheader()
            w.writerows(filas)
        print(f"\nCSV: {salida_csv}")


if __name__ == "__main__":
    main()
