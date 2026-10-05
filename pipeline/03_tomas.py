"""Limpia la transcripción: tomas repetidas, claquetas, «otra vez», frases a medias, muletillas y coletillas.

Uso:
  python pipeline/03_tomas.py <transcripcion.json> <palabras.json> [--mantener 12-15 …] [--quitar 40-44 …]
                              [--sin-coletilla]

Criterios (imprime TODO lo que quita, con índices, para revisarlo):
  1. Claqueta: frases cortas antes de la primera frase real («tres, dos, uno», «acción», «grabando»…).
  2. Aviso al editor: frase corta con «otra vez / repito / de nuevo / corta / perdón…» → se quita ella
     y la frase anterior (la que salió mal).
  3. Toma repetida: si una frase vuelve a empezar igual poco después, se queda la ÚLTIMA versión.
     Incluye la frase abandonada a medias («Compite…» → «Compite por quien contesta primero…»).
  4. Reinicios: «no por el producto, no porque el producto, no porque el producto fuera malo» → el último.
  5. Muletillas sueltas: «eh», «em», «mmm».
  6. Coletilla final: frase corta tras una pausa larga al final («listo», «vale», «gracias por ver…»).
Las correcciones manuales van con --mantener / --quitar (índices «i» de las palabras).
"""
from __future__ import annotations

import argparse
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from comun import escribir_json, leer_json

PAUSA_FRASE = 0.7          # s de silencio que separan frases aunque no haya punto
VENTANA_TOMA = 25.0        # s máximos entre una toma y su repetición
MULETILLAS = {"eh", "ehh", "ehm", "em", "emm", "mm", "mmm", "hmm", "am", "ah"}
AVISOS = [r"\botra vez\b", r"\brepito\b", r"\bde nuevo\b", r"\bvuelvo a empezar\b", r"\bdesde el principio\b",
          r"\bcorta(mos)?\b", r"\bcorto\b", r"\bperd[oó]n\b", r"\bme equivoqu[eé]\b", r"\brepetimos\b",
          r"\bespera\b", r"\botra\b$", r"\bde vuelta\b"]
# Instrucciones claras al editor: cuentan aunque la frase sea más larga (hasta 10 palabras).
AVISOS_FUERTES = [r"\brepetimos desde\b", r"\bvuelvo a empezar\b", r"\botra vez desde\b", r"\bcorta y repetimos\b",
                  r"\beso (lo )?(corto|cortas|quitamos|quitas)\b", r"\bdesde el principio\b", r"\bempiezo de nuevo\b",
                  r"\bempiezo nuevamente\b", r"\bvoy a corregir(lo)?\b", r"\bpara la correccion del video\b",
                  r"\bajustar nuevamente lo que dije\b", r"\bvoy a repetir(lo)?\b", r"\blo vuelvo a decir\b"]
# Hasta dónde llega la corrección hacia atrás: el párrafo (hasta una pausa ≥ 1 s), como mucho 40 s.
PAUSA_PARRAFO, MAX_CORRECCION = 1.0, 40.0
CLAQUETAS = [r"\btres,? dos,? uno\b", r"\b3,? 2,? 1\b", r"\bacci[oó]n\b", r"\bgrabando\b", r"\bprueba\b",
             r"\bprobando\b", r"\bya est[aá] grabando\b", r"\bempezamos\b", r"\bva\b$"]
COLETILLAS = [r"^(listo|vale|ok|okay|bueno|ya|ya est[aá]|y ya|eso es todo|corta|corto|fin)$",
              r"\bgracias por ver\b", r"\b(ya )?est[aá] grabado\b", r"\bse grab[oó]\b"]


def norm(w: str) -> str:
    w = unicodedata.normalize("NFD", w.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w]", "", w)


def texto(ws: list[dict]) -> str:
    return " ".join(w["w"] for w in ws)


def frases(ws: list[dict]) -> list[list[dict]]:
    res, act = [], []
    for k, w in enumerate(ws):
        act.append(w)
        sig = ws[k + 1] if k + 1 < len(ws) else None
        fin_puntuacion = w["w"].rstrip().endswith((".", "?", "!", "…"))
        if sig is None or fin_puntuacion or sig["inicio"] - w["fin"] > PAUSA_FRASE:
            res.append(act)
            act = []
    return res


def es_repeticion(a: list[str], b: list[str]) -> bool:
    """¿La frase a es una toma anterior de la frase b (b vuelve a empezar como a)?"""
    if not a or not b:
        return False
    if len(a) <= 3:
        return b[:len(a)] == a and len(b) >= len(a)
    pref = b[:len(a) + 2]
    r = SequenceMatcher(None, a, pref).ratio()
    return (a[:2] == b[:2] and r >= 0.55) or r >= 0.75


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("transcripcion", type=Path)
    p.add_argument("salida", type=Path)
    p.add_argument("--mantener", nargs="*", default=[], help="rangos de índices a conservar: 12-15 30")
    p.add_argument("--quitar", nargs="*", default=[], help="rangos de índices a quitar: 40-44")
    p.add_argument("--sin-coletilla", action="store_true", help="no quitar la coletilla final")
    a = p.parse_args()

    t = leer_json(a.transcripcion)
    ws = t["palabras"]
    quitar: dict[int, str] = {}  # índice → motivo

    def marcar(grupo: list[dict], motivo: str) -> None:
        for w in grupo:
            quitar.setdefault(w["i"], motivo)

    fr = frases(ws)
    toks = [[norm(w["w"]) for w in f] for f in fr]
    # Las muletillas no cuentan al comparar tomas: «Eh, esto es» ≈ «Esto es muy importante…».
    toks = [[x for x in f if x and x not in MULETILLAS] for f in toks]

    # 1. Claquetas al principio
    for k, f in enumerate(fr):
        tx = " ".join(toks[k])
        if len(toks[k]) <= 4 and any(re.search(pat, tx) for pat in CLAQUETAS):
            marcar(f, "claqueta")
        else:
            break

    # 2. Avisos al editor («otra vez», «repito»…)
    for k, f in enumerate(fr):
        tx = " ".join(toks[k])
        fuerte = any(re.search(pat, tx) for pat in AVISOS_FUERTES)   # «repetimos desde la parte de…»
        if fuerte and len(toks[k]) <= 25:
            # Orden clara al editor: fuera ella (y la frase siguiente si también es aviso) y TODO el párrafo
            # anterior, que es lo que se va a volver a decir (prueba02: «voy a corregirlo… esto es para la
            # corrección del video» anulaba 22 s de explicación, no solo la última frase).
            marcar(f, f"aviso «{texto(f)}»")
            j = k - 1
            while j >= 0 and f[0]["inicio"] - fr[j][0]["inicio"] <= MAX_CORRECCION:
                marcar(fr[j], f"corregido por «{texto(f)[:60]}»")
                if j == 0 or fr[j][0]["inicio"] - fr[j - 1][-1]["fin"] >= PAUSA_PARRAFO:
                    break
                j -= 1
        elif len(toks[k]) <= 5 and any(re.search(pat, tx) for pat in AVISOS):
            marcar(f, f"aviso «{texto(f)}»")
            if k > 0:
                marcar(fr[k - 1], f"frase anterior a «{texto(f)}»")

    # 3. Tomas repetidas entre frases: gana la última
    for k in range(len(fr)):
        for j in range(k + 1, min(k + 4, len(fr))):
            if fr[j][0]["inicio"] - fr[k][-1]["fin"] > VENTANA_TOMA:
                break
            if all(w["i"] in quitar for w in fr[j]):
                continue
            if es_repeticion(toks[k], toks[j]):
                marcar(fr[k], f"toma repetida (se queda la de {fr[j][0]['inicio']:.1f} s)")
                break

    # 4. Reinicios (aunque no haya pausa entre medias):
    #    «no por el producto, no porque el producto, no porque el producto fuera malo» → el último.
    #    «la venta se gana, la venta se gana o se pierde» → el último.
    #    Es reinicio SOLO si el intento es corto (≤ 6 palabras), no es una frase completa (no acaba en
    #    «.», «?», «!»), hay titubeo (acaba en «,» o «…», o hay pausa ≥ 0,3 s, o son ≤ 2 palabras) y los
    #    4 primeros tokens se parecen ≥ 70 % empezando por la misma palabra.
    #    Más laxo quitaba cosas con sentido en habla real (prueba02): «pero no voy a atender…» (invertía el
    #    sentido), «tu propio ChatGPT, tu propio Claude…» (enumeraciones), «¿qué hizo el bot? El bot…».
    n_all = [norm(w["w"]) for w in ws]
    k = 0
    while k < len(ws):
        if ws[k]["i"] in quitar or not n_all[k] or n_all[k] in MULETILLAS:
            k += 1
            continue
        salto = None
        for m in range(k + 1, min(k + 8, len(ws))):
            if n_all[m] != n_all[k]:
                continue
            intento = [x for x in n_all[k:m] if x and x not in MULETILLAS]
            ultima = ws[m - 1]["w"].rstrip()
            if not intento or len(intento) > 6 or ultima.endswith((".", "?", "!")):
                break
            titubeo = (ultima.endswith((",", "...", "…")) or ws[m]["inicio"] - ws[m - 1]["fin"] >= 0.3
                       or len(intento) <= 2)
            a_ = intento[:4]
            b_ = [x for x in n_all[m:m + 8] if x and x not in MULETILLAS][:len(a_)]
            if len(a_) >= 2 and titubeo and SequenceMatcher(None, a_, b_).ratio() >= 0.7:
                salto = m
            break
        if salto is not None:
            marcar(ws[k:salto], f"reinicio (sigue en {ws[salto]['inicio']:.1f} s)")
            k = salto
        else:
            k += 1

    # 5. Muletillas sueltas
    for w in ws:
        if norm(w["w"]) in MULETILLAS:
            quitar.setdefault(w["i"], "muletilla")

    # 6. Coletilla final
    if not a.sin_coletilla and len(fr) > 1:
        ult, penult = fr[-1], fr[-2]
        tx = " ".join(toks[-1])
        pausa = ult[0]["inicio"] - penult[-1]["fin"]
        if len(toks[-1]) <= 6 and pausa >= 1.5 and any(re.search(pat, tx) for pat in COLETILLAS):
            marcar(ult, f"coletilla final (tras {pausa:.1f} s de pausa)")

    # Correcciones manuales
    def rangos(lista: list[str]):
        for r in lista:
            i0, _, i1 = r.partition("-")
            yield from range(int(i0), int(i1 or i0) + 1)

    for i in rangos(a.quitar):
        quitar[i] = "manual"
    for i in rangos(a.mantener):
        quitar.pop(i, None)

    # Informe agrupado por tramos consecutivos con el mismo motivo
    print(f"Palabras: {len(ws)}  ·  quitadas: {len(quitar)}  ·  quedan: {len(ws) - len(quitar)}\n")
    quitadas, k = [], 0
    while k < len(ws):
        if ws[k]["i"] in quitar:
            motivo, j = quitar[ws[k]["i"]], k
            while j + 1 < len(ws) and quitar.get(ws[j + 1]["i"]) == motivo:
                j += 1
            tramo = ws[k:j + 1]
            quitadas.append({"motivo": motivo, "texto": texto(tramo), "i": [tramo[0]["i"], tramo[-1]["i"]],
                             "inicio": tramo[0]["inicio"], "fin": tramo[-1]["fin"]})
            print(f"  ✂ [{tramo[0]['i']}-{tramo[-1]['i']}] {tramo[0]['inicio']:7.2f}s  {motivo}\n"
                  f"      «{texto(tramo)}»")
            k = j + 1
        else:
            k += 1
    if not quitadas:
        print("  (nada que quitar)")

    quedan = [w for w in ws if w["i"] not in quitar]
    escribir_json(a.salida, {"fuente": t["fuente"], "transcripcion": str(a.transcripcion),
                             "palabras": quedan, "quitadas": quitadas})
    print(f"\nTexto final:\n  {texto(quedan)}\n→ {a.salida}")


if __name__ == "__main__":
    main()
