"""Transcribe el corte y lo compara (difflib) con las palabras que debían quedar.

Uso:  python pipeline/verificar_corte.py <corte.mp4> <palabras.json>

Avisa de las palabras que FALTAN (el corte se comió algo) y de las que SOBRAN (se coló una toma
descartada). Las diferencias de una sola palabra que suenan igual («3»/«tres») se ignoran.
"""
from __future__ import annotations

import argparse
import importlib
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from comun import escribir_json, leer_json

NUMEROS = {"1": "uno", "2": "dos", "3": "tres", "4": "cuatro", "5": "cinco", "6": "seis", "7": "siete",
           "8": "ocho", "9": "nueve", "10": "diez"}


def norm(w: str) -> str:
    w = unicodedata.normalize("NFD", w.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    w = re.sub(r"[^\w]", "", w)
    return NUMEROS.get(w, w)


def verificar(corte: Path, palabras_json: Path) -> bool:
    transcribir = importlib.import_module("02_transcribe").transcribir
    esperadas = [w for w in leer_json(palabras_json)["palabras"] if norm(w["w"])]
    t = transcribir(Path(corte))
    escribir_json(Path(corte).with_suffix(".verif.json"), t)
    obtenidas = [w for w in t["palabras"] if norm(w["w"])]
    a, b = [norm(w["w"]) for w in esperadas], [norm(w["w"]) for w in obtenidas]

    faltan, sobran = [], []
    for op, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        # Sustituciones 1↔1 casi iguales (grafía distinta, misma palabra): no cuentan.
        if op == "replace" and i2 - i1 == j2 - j1 and all(
                SequenceMatcher(None, x, y).ratio() >= 0.75 for x, y in zip(a[i1:i2], b[j1:j2])):
            continue
        if i2 > i1:
            faltan.append((esperadas[i1]["i"], " ".join(w["w"] for w in esperadas[i1:i2]),
                           obtenidas[j1]["inicio"] if j1 < len(obtenidas) else t["duracion"]))
        if j2 > j1:
            sobran.append((obtenidas[j1]["inicio"], " ".join(w["w"] for w in obtenidas[j1:j2])))

    parecido = SequenceMatcher(None, a, b, autojunk=False).ratio()
    print(f"\nVerificación: {len(a)} palabras esperadas · {len(b)} transcritas del corte · "
          f"coincidencia {parecido * 100:.1f} %")
    for i, tx, tc in faltan:
        print(f"  ✘ FALTA  (palabra {i}, hacia {tc:.2f} s del corte): «{tx}»")
    for tc, tx in sobran:
        print(f"  ＋ SOBRA  ({tc:.2f} s del corte): «{tx}»")
    if not faltan and not sobran:
        print("  ✔ Están todas las palabras y no sobra ninguna.")
    return not faltan


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("corte", type=Path)
    p.add_argument("palabras", type=Path)
    a = p.parse_args()
    verificar(a.corte, a.palabras)


if __name__ == "__main__":
    main()
