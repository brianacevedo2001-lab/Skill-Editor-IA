"""Zooms automáticos suaves (≤ 1,45×) hacia donde hay actividad en la pantalla; los escribe en grueso.json.

Uso:
  python pipeline/06_zooms.py videos/<id>/grueso_pantalla.mp4 videos/<id>/grueso.json
         [--max 1.45] [--min 1.15] [--duracion-min 2.5]

- Se analiza el vídeo a 256×144 y 5 fps: diferencia entre fotogramas → mapa de actividad.
- Por cada segundo: caja que envuelve la actividad (sin ruido suelto). Si cambia casi toda la pantalla
  (scroll, cambio de ventana), ese segundo NO admite zoom.
- Segundos consecutivos con la actividad en la misma zona (≥ 2,5 s) → un zoom: caja + margen, en 16:9,
  escala = lo que quepa (máx. 1,45×; si sale < 1,15× no merece la pena).
- Solo se reescribe la clave "zooms" de grueso.json (si no existe, se crea el guion base).
  Las transiciones (entrada/salida suaves) las hace Remotion.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import numpy as np

from comun import FFMPEG, escribir_json, ffprobe_json, leer_json

AN, AL, FPS_A = 256, 144, 5


def leer_fotogramas(video: Path) -> np.ndarray:
    r = subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-i", str(video),
                        "-vf", f"fps={FPS_A},scale={AN}:{AL}:flags=area,format=gray", "-f", "rawvideo", "-"],
                       check=True, capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, AL, AN).astype(np.int16)


def cajas_por_segundo(fr: np.ndarray) -> list[dict | None]:
    dif = np.abs(np.diff(fr, axis=0)) > 18                         # píxeles que cambian
    res: list[dict | None] = []
    for s in range(0, len(dif), FPS_A):
        m = dif[s:s + FPS_A].any(axis=0)
        # quitar ruido suelto: celdas de 8×8 con al menos 3 píxeles activos
        celdas = m.reshape(AL // 8, 8, AN // 8, 8).sum(axis=(1, 3)) >= 3
        area = celdas.mean()
        if area == 0:
            res.append(None)                                        # pantalla quieta
            continue
        if area > 0.30:
            res.append({"global": True})                            # scroll / cambio de ventana
            continue
        ys, xs = np.nonzero(celdas)
        res.append({"x0": xs.min() / (AN // 8), "x1": (xs.max() + 1) / (AN // 8),
                    "y0": ys.min() / (AL // 8), "y1": (ys.max() + 1) / (AL // 8), "area": float(area)})
    return res


def planificar(cajas: list[dict | None], esc_max: float, esc_min: float, dur_min: float) -> list[dict]:
    zooms, i, n = [], 0, len(cajas)
    while i < n:
        c = cajas[i]
        if not c or c.get("global"):
            i += 1
            continue
        caja = dict(c)
        centro = lambda b: ((b["x0"] + b["x1"]) / 2, (b["y0"] + b["y1"]) / 2)
        j, quietos, fin = i + 1, 0, i + 1
        while j < n:
            d = cajas[j]
            if d is None:                                           # quieto: el zoom aguanta ≤ 2 s
                quietos += 1
                if quietos > 2:
                    break
                j += 1
                continue
            if d.get("global"):
                break
            (cx0, cy0), (cx1, cy1) = centro(caja), centro(d)
            if abs(cx1 - cx0) > 0.2 or abs(cy1 - cy0) > 0.2:
                break                                               # la actividad se ha ido a otra zona
            caja = {"x0": min(caja["x0"], d["x0"]), "x1": max(caja["x1"], d["x1"]),
                    "y0": min(caja["y0"], d["y0"]), "y1": max(caja["y1"], d["y1"])}
            quietos = 0
            j += 1
            fin = j
        j = fin                                                     # no alargar el zoom con los quietos del final
        dur = j - i
        if dur >= dur_min:
            w = (caja["x1"] - caja["x0"]) * 1.35 + 0.04             # margen
            h = (caja["y1"] - caja["y0"]) * 1.35 + 0.04
            esc = min(esc_max, 1 / max(w, h * 1.0))
            if esc >= esc_min:
                cx = (caja["x0"] + caja["x1"]) / 2
                cy = (caja["y0"] + caja["y1"]) / 2
                # el encuadre ampliado no puede salirse de la pantalla
                m = 0.5 / esc
                cx, cy = min(max(cx, m), 1 - m), min(max(cy, m), 1 - m)
                zooms.append({"from": float(i), "to": float(j), "x": round(cx, 3), "y": round(cy, 3),
                              "escala": round(esc, 2)})
        i = j
    # separación mínima de 1 s entre zooms (si no, se funden en uno)
    res: list[dict] = []
    for z in zooms:
        if res and z["from"] - res[-1]["to"] < 1.0:
            if z["from"] - 1.0 - res[-1]["from"] < 1.5:
                continue                                            # no caben los dos: se queda el primero
            res[-1]["to"] = z["from"] - 1.0
        res.append(z)
    return res


def guion_base(video: Path) -> dict:
    id_ = video.parent.name
    return {"parte": "grueso", "pantalla": f"{id_}/grueso_pantalla.mp4", "camara": f"{id_}/grueso_camara.mp4",
            "cuts": f"{id_}/grueso.cuts.json", "palabras": f"{id_}/grueso.palabras_corte.json",
            "esquina": {"lado": "der", "ancho": 0.2}, "musica": {"src": "_shared/music/jazz_a_night_alone.m4a", "volumen": 0.13},
            "zooms": [], "escenas": []}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video", type=Path)
    p.add_argument("guion", type=Path)
    p.add_argument("--max", type=float, default=1.45)
    p.add_argument("--min", type=float, default=1.15)
    p.add_argument("--duracion-min", type=float, default=2.5)
    a = p.parse_args()

    fr = leer_fotogramas(a.video)
    cajas = cajas_por_segundo(fr)
    zooms = planificar(cajas, min(a.max, 1.45), a.min, a.duracion_min)
    dur = float(ffprobe_json(a.video)["format"]["duration"])
    for z in zooms:
        z["to"] = min(z["to"], round(dur, 2))
    g = leer_json(a.guion) if a.guion.exists() else guion_base(a.video)
    g["zooms"] = zooms
    escribir_json(a.guion, g)
    quietos = sum(c is None for c in cajas)
    globales = sum(bool(c and c.get("global")) for c in cajas)
    print(f"{len(cajas)} s analizados · {quietos} quietos · {globales} con cambio global · {len(zooms)} zooms")
    for z in zooms:
        print(f"  zoom {z['from']:6.1f}–{z['to']:6.1f} s  ×{z['escala']:.2f} hacia ({z['x']:.2f}, {z['y']:.2f})")
    print(f"→ {a.guion}")


if __name__ == "__main__":
    main()
