"""Lectura de una parte ANTES de diseñar sus escenas: ritmo, pausas, palabras con énfasis, cifras, marcas y bloques.

Uso:
  python pipeline/lectura.py <id> <parte>        (intro, datos, cierre, grueso, vertical…)  → videos/<id>/<parte>.lectura.md

Sale un informe para escribir el concepto (videos/_shared/plantillas/concepto.md) y el guion de escenas:
- Ritmo: palabras por minuto global y por tramos de 10 s (los tramos rápidos aguantan menos texto en pantalla).
- Énfasis: palabras dichas más fuerte o más estiradas que lo normal en esa frase → candidatas a *acento* o callout.
- Cifras y marcas: cada número (con su contexto) y cada marca de la librería de logos.
- Bloques de ~8–15 s cortados en fin de frase, con la pieza que sugiere el contenido (cifra → revealStat/bars,
  varias marcas → lineup, «primero… luego…» → pasos, «busca…» → buscador, «te escribe / mensaje» → notificacion,
  pregunta → callout) y un color de plano alterno para que los bloques seguidos no se vean iguales.
Usa las palabras alineadas (alinear.py) y la voz cortada. Idea de una skill de referencia («leer antes de editar»).
"""
from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

import numpy as np

from comun import FFMPEG, MARCA, VIDEOS, leer_json

SR = 16000


def normal(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    return re.sub(r"[^a-z0-9ñ%]", "", "".join(c for c in t if not unicodedata.combining(c)))


def energia(voz: Path) -> np.ndarray:
    import subprocess
    r = subprocess.run([FFMPEG, "-v", "error", "-i", str(voz), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True, check=True)
    x = np.frombuffer(r.stdout, np.float32)
    hop = SR // 100
    n = len(x) // hop
    return 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)


def frases(pal: list[dict]) -> list[list[int]]:
    res, act = [], []
    for k, w in enumerate(pal):
        act.append(k)
        siguiente_pausa = pal[k + 1]["inicio"] - w["fin"] if k + 1 < len(pal) else 9
        if re.search(r"[.?!…]$", w["w"]) or siguiente_pausa > 0.6:
            res.append(act)
            act = []
    if act:
        res.append(act)
    return res


SUGERENCIAS = [
    (r"\b(primero|segundo|tercero|luego|despues|después|paso|pasos|finalmente)\b", "pasos"),
    (r"\b(busca|buscas|buscar|googlea|google)\b", "buscador"),
    (r"\b(te escribe|te escribio|te escribió|mensaje|mensajes|notificacion|notificación|whatsapp)\b", "notificacion"),
    (r"\b(comentario|comentarios|me escribieron|me preguntan|preguntan)\b", "comentario"),
]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("id")
    p.add_argument("parte")
    a = p.parse_args()
    base = VIDEOS / a.id / a.parte
    pal = [w for w in leer_json(base.with_name(a.parte + ".palabras_corte.json")) if w["fin"] > w["inicio"]]
    db = energia(base.with_name(a.parte + ".voz.wav"))
    logos = leer_json(VIDEOS / "_shared" / "logos" / "index.json")
    bloqueados = set(logos.get("bloqueados", []))
    alias = {normal(al): m["nombre"] for m in logos["marcas"] for al in m["alias"] if al not in bloqueados}
    colores = leer_json(MARCA / "marca.json")["colores"]
    paleta = [colores["acento"], colores.get("acento2", colores["acento"]), colores.get("brillo", colores["texto"]),
              colores.get("etiqueta", colores["acento"])]

    dur = pal[-1]["fin"] - pal[0]["inicio"]
    wpm = len(pal) / dur * 60
    # energía media de cada palabra y énfasis relativo a su frase
    def nivel(w):
        s = db[int(w["inicio"] * 100):max(int(w["fin"] * 100), int(w["inicio"] * 100) + 1)]
        return float(np.percentile(s, 90)) if len(s) else -90.0
    niv = [nivel(w) for w in pal]
    fr = frases(pal)
    # Énfasis = más fuerte que la mediana de su frase y/o más estirada (s por letra) que lo normal en ella.
    # La voz está normalizada y comprimida: se ordena por puntuación y se toman las mejores, sin umbral fijo.
    VACIAS = {"porque", "cuando", "donde", "entonces", "tambien", "también", "esto", "esta", "este", "para", "pero",
              "como", "cómo", "solo", "sólo", "todo", "todos", "tiene", "están", "estan", "puede", "hace", "desde"}
    enfasis = []
    for ks in fr:
        if len(ks) < 4:
            continue
        med = np.median([niv[k] for k in ks])
        vel = np.median([(pal[k]["fin"] - pal[k]["inicio"]) / max(len(normal(pal[k]["w"])), 1) for k in ks])
        for k in ks:
            letras = max(len(normal(pal[k]["w"])), 1)
            if letras < 4 or normal(pal[k]["w"]) in VACIAS:
                continue
            estira = (pal[k]["fin"] - pal[k]["inicio"]) / letras / max(vel, 1e-3)
            puntos = (niv[k] - med) + 4 * max(0.0, estira - 1)
            if puntos > 1.5:
                enfasis.append((k, puntos, estira > 1.5))

    L = [f"# Lectura de {a.id}/{a.parte}", "",
         f"- Duración hablada: **{dur:.1f} s** · {len(pal)} palabras · **{wpm:.0f} palabras/min** "
         f"({'rápido: textos en pantalla muy cortos' if wpm > 170 else 'pausado: cabe algo más de texto' if wpm < 130 else 'ritmo normal'})"]
    tramos = []
    for t in np.arange(pal[0]["inicio"], pal[-1]["fin"], 10):
        n = sum(1 for w in pal if t <= w["inicio"] < t + 10)
        tramos.append(f"{t:.0f}–{t + 10:.0f} s: {n * 6}")
    L += [f"- Ritmo por tramos (pal/min): " + " · ".join(tramos)]
    pausas = [(pal[k]["fin"], pal[k + 1]["inicio"] - pal[k]["fin"]) for k in range(len(pal) - 1)
              if pal[k + 1]["inicio"] - pal[k]["fin"] >= 0.4]
    L += [f"- Pausas ≥ 0,4 s: " + (", ".join(f"{t:.1f} s ({d:.1f})" for t, d in pausas) if pausas else "ninguna")]

    L += ["", "## Palabras con énfasis (candidatas a *acento* o callout)", ""]
    for k, d, est in sorted(enfasis, key=lambda x: -x[1])[:20]:
        ctx = " ".join(w["w"] for w in pal[max(0, k - 3):k + 4])
        L.append(f"- **{pal[k]['w']}** ({pal[k]['inicio']:.2f} s, fuerza {d:.1f}{', estirada' if est else ''}) — «{ctx}»")

    L += ["", "## Cifras y marcas", ""]
    for k, w in enumerate(pal):
        n = normal(w["w"])
        marca = alias.get(n) or (alias.get(normal(w["w"] + pal[k + 1]["w"])) if k + 1 < len(pal) else None)
        if re.search(r"\d", w["w"]) or marca:
            ctx = " ".join(x["w"] for x in pal[max(0, k - 4):k + 6])
            L.append(f"- {w['inicio']:.2f} s · {'**' + marca + '**' if marca else 'cifra **' + w['w'] + '**'} — «{ctx}»")

    L += ["", "## Bloques (planos) y pieza sugerida", "",
          "| # | Tiempo | Empieza | Sugerencia | Color de plano |", "|---|---|---|---|---|"]
    bloques, act = [], []
    for ks in fr:
        act += ks
        if pal[act[-1]]["fin"] - pal[act[0]]["inicio"] >= 8:
            bloques.append(act)
            act = []
    if act:
        bloques.append(act)
    for b, ks in enumerate(bloques):
        texto = " ".join(pal[k]["w"] for k in ks)
        tn = normal(texto)
        sug = []
        if re.search(r"\d", texto):
            sug.append("revealStat/bars")
        marcas = {alias[normal(pal[k]["w"])] for k in ks if normal(pal[k]["w"]) in alias}
        if len(marcas) >= 2:
            sug.append(f"lineup ({', '.join(sorted(marcas))})")
        for patron, pieza in SUGERENCIAS:
            if re.search(patron, texto.lower()):
                sug.append(pieza)
        if "?" in texto:
            sug.append("callout (pregunta)")
        L.append(f"| {b + 1} | {pal[ks[0]]['inicio']:.1f}–{pal[ks[-1]]['fin']:.1f} s | "
                 f"{' '.join(pal[k]['w'] for k in ks[:7])}… | {', '.join(dict.fromkeys(sug)) or 'cámara'} | "
                 f"`{paleta[b % len(paleta)]}` |")
    salida = base.with_name(a.parte + ".lectura.md")
    salida.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{wpm:.0f} pal/min · {len(enfasis)} énfasis · {len(bloques)} bloques → {salida}")


if __name__ == "__main__":
    main()
