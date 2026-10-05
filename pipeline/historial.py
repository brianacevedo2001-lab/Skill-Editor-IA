"""Historial de decisiones visuales por vídeo, para que dos vídeos seguidos no se vean iguales.

Uso:
  python pipeline/historial.py registrar <id>       → guarda en videos/_shared/historial.json lo que usó el vídeo
  python pipeline/historial.py comparar <id> [--n 3]  → avisa de lo que repite respecto a los N vídeos anteriores
  python pipeline/historial.py ver

Se registra por vídeo: piezas usadas (y cuántas de cada), fondo, música (tema y desde), tintes, si hubo capas
(persona recortada), b-roll, miniatura y el concepto (primera línea de videos/<id>/concepto.md si existe).
`comparar` sugiere fondo, piezas y música que NO se usaron últimamente. Se llama al escribir el concepto (antes de
diseñar escenas) y se registra al entregar. Idea de una skill de referencia (concepto por vídeo + historial).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from collections import Counter
from pathlib import Path

from comun import VIDEOS, escribir_json, leer_json

HIST = VIDEOS / "_shared" / "historial.json"
FONDOS = ["profundidad", "puntos", "aurora"]
CATALOGO = ["orbOpen", "lineup", "revealStat", "bars", "rise", "orbChips", "dissolve", "outro", "broll", "callout",
            "notificacion", "buscador", "pasos", "comentario", "tituloDetras", "index", "subscribe", "lowerThird",
            "showcase", "camFull"]
PARTES = ["intro", "disclaimer", "datos", "grueso", "cierre", "vertical"]


def resumen(id_: str) -> dict:
    piezas, tintes, fondos, musica, capas, broll = Counter(), set(), set(), [], False, 0
    for parte in PARTES:
        ruta = VIDEOS / id_ / f"{parte}.json"
        if not ruta.exists():
            continue
        g = leer_json(ruta)
        fondos.add(g.get("fondo", "profundidad"))
        if g.get("persona"):
            capas = True
        m = g.get("musica") or {}
        if m.get("src"):
            musica.append({"parte": parte, "src": m["src"], "desde": m.get("desde", 0)})
        for e in g.get("escenas", []):
            piezas[e["type"]] += 1
            broll += e["type"] == "broll"
            if e.get("tint"):
                tintes.add(e["tint"])
            if e.get("capa") == "detras":
                capas = True
    concepto = VIDEOS / id_ / "concepto.md"
    idea = next((l.strip("# ").strip() for l in concepto.read_text(encoding="utf-8").splitlines() if l.strip()), "") \
        if concepto.exists() else ""
    return {"id": id_, "fecha": dt.date.today().isoformat(), "piezas": dict(piezas.most_common()),
            "fondos": sorted(fondos), "musica": musica, "tintes": sorted(tintes), "capas": capas, "broll": broll,
            "concepto": idea}


def leer() -> list[dict]:
    return leer_json(HIST) if HIST.exists() else []


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("orden", choices=["registrar", "comparar", "ver"])
    p.add_argument("id", nargs="?")
    p.add_argument("--n", type=int, default=3)
    a = p.parse_args()
    hist = leer()

    if a.orden == "ver":
        for h in hist:
            top = ", ".join(f"{k}×{v}" for k, v in list(h["piezas"].items())[:5])
            print(f"{h['id']} ({h['fecha']}): fondo {'/'.join(h['fondos'])} · música "
                  f"{', '.join(Path(m['src']).stem for m in h['musica']) or '—'} · {top}"
                  f"{' · capas' if h['capas'] else ''}")
        return
    if not a.id:
        raise SystemExit("Falta el <id>")

    if a.orden == "registrar":
        r = resumen(a.id)
        hist = [h for h in hist if h["id"] != a.id] + [r]
        escribir_json(HIST, hist)
        print(f"✔ {a.id} registrado en {HIST.relative_to(VIDEOS.parent)}: {r['piezas']}")
        return

    # comparar: el vídeo actual (si ya tiene guiones) contra los N anteriores
    previos = [h for h in hist if h["id"] != a.id][-a.n:]
    if not previos:
        print("No hay vídeos anteriores en el historial: libertad total.")
        return
    actual = resumen(a.id)
    usados_fondo = Counter(f for h in previos for f in h["fondos"])
    usados_musica = Counter(m["src"] for h in previos for m in h["musica"])
    usadas = Counter()
    for h in previos:
        usadas.update(h["piezas"])
    print(f"Comparando {a.id} con {', '.join(h['id'] for h in previos)}")
    avisos = []
    for f in actual["fondos"]:
        if f == previos[-1]["fondos"][0] if previos[-1]["fondos"] else False:
            avisos.append(f"mismo fondo que {previos[-1]['id']} («{f}»)")
    for m in actual["musica"]:
        if usados_musica[m["src"]]:
            avisos.append(f"la música {Path(m['src']).stem} ({m['parte']}) ya sonó en {usados_musica[m['src']]} de los últimos")
    top_prev = [k for k, _ in Counter(previos[-1]["piezas"]).most_common(3)]
    top_act = [k for k, _ in Counter(actual["piezas"]).most_common(3)]
    if top_act and top_prev and set(top_act) == set(top_prev):
        avisos.append(f"las 3 piezas protagonistas son las mismas que en {previos[-1]['id']}: {', '.join(top_act)}")
    for x in avisos:
        print("  ⚠ " + x)
    if not avisos:
        print("  ✔ nada repetido de forma llamativa")
    libres_fondo = [f for f in FONDOS if not usados_fondo[f]] or sorted(FONDOS, key=lambda f: usados_fondo[f])
    libres_piezas = [k for k in CATALOGO if not usadas[k]]
    print(f"  Fondo sugerido: {libres_fondo[0]} (menos usado: {', '.join(libres_fondo)})")
    print(f"  Piezas sin usar últimamente: {', '.join(libres_piezas) or '—'}")
    print(f"  Música ya usada (evitar): {', '.join(Path(s).stem for s in usados_musica) or '—'}")


if __name__ == "__main__":
    main()
