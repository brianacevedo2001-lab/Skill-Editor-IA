"""Cuadra la música con el vídeo: encuentra los golpes fuertes de un tema y propone desde qué segundo empezarlo para
que uno de ellos caiga en el momento clave (el revelado, el nombre del producto).

Uso:
  python pipeline/golpe_musica.py videos/<id>/intro.json --en 12.4 [--tambien 25.4 40.9] [--n 6] [--aplicar 1]
  python pipeline/golpe_musica.py videos/_shared/music/epica_inception.m4a --en 12.4      (solo analiza)

--en        segundo de la PARTE donde tiene que caer el golpe (p. ej. el inicio de la palabra «TuMarca» − 0,03)
--tambien   otros instantes donde conviene que la música marque algo: se cuenta cuántos coinciden (±80 ms) con un
            golpe del tema en cada propuesta
--aplicar   escribe la propuesta N (1 = la mejor) en musica.desde del guion
Cada golpe se puntúa por su fuerza (subida de energía grave y de banda ancha) y por el redoble que lo prepara (golpes
en el 1,2 s anterior: lo que lo hace épico). Idea de una skill de referencia (`anim.py golpe`), reimplementada aquí.
musica.desde lo usan Parte.tsx (Remotion), render_grueso.py y 09_shorts.py.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

from comun import FFMPEG, VIDEOS, escribir_json, leer_json

SR = 22050
HOP = 256                      # ~11,6 ms


def leer(ruta: Path) -> np.ndarray:
    r = subprocess.run([FFMPEG, "-v", "error", "-i", str(ruta), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32)


def golpes(x: np.ndarray, n_max: int = 400) -> list[dict]:
    """Golpes del tema: picos de la novedad espectral (sobre todo graves) con su fuerza y su «redoble» previo."""
    win = 1024
    marcos = np.lib.stride_tricks.sliding_window_view(np.pad(x, (win // 2, win // 2)), win)[::HOP]
    espec = np.abs(np.fft.rfft(marcos * np.hanning(win), axis=1))
    frec = np.fft.rfftfreq(win, 1 / SR)
    log = np.log1p(espec)
    flujo = np.maximum(np.diff(log, axis=0, prepend=log[:1]), 0)
    grave = flujo[:, (frec >= 30) & (frec <= 220)].sum(axis=1)
    ancho = flujo.sum(axis=1)
    fuerza = 0.6 * grave / (grave.max() + 1e-9) + 0.4 * ancho / (ancho.max() + 1e-9)
    t = np.arange(len(fuerza)) * HOP / SR
    # picos locales (±60 ms) por encima de la mediana móvil
    k = int(0.06 * SR / HOP)
    res = []
    umbral = np.median(fuerza) * 2.5
    for i in range(k, len(fuerza) - k):
        if fuerza[i] >= umbral and fuerza[i] == fuerza[i - k:i + k + 1].max():
            res.append({"t": float(t[i]), "fuerza": float(fuerza[i])})
    res.sort(key=lambda g: -g["fuerza"])
    res = res[:n_max]
    tiempos = np.array([g["t"] for g in res])
    for g in res:
        previos = [h["fuerza"] for h in res if g["t"] - 1.2 <= h["t"] < g["t"] - 0.05]
        g["redoble"] = float(sum(previos))
    return sorted(res, key=lambda g: g["t"])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("entrada", type=Path, help="guion de la parte (.json) o un archivo de música")
    p.add_argument("--en", type=float, required=True)
    p.add_argument("--tambien", type=float, nargs="*", default=[])
    p.add_argument("--n", type=int, default=6)
    p.add_argument("--aplicar", type=int)
    a = p.parse_args()

    guion = leer_json(a.entrada) if a.entrada.suffix == ".json" else None
    musica = VIDEOS / guion["musica"]["src"] if guion else a.entrada
    x = leer(musica)
    dur = len(x) / SR
    gs = golpes(x)
    if not gs:
        raise SystemExit("No encontré golpes claros en el tema.")
    fmax = max(g["fuerza"] for g in gs)
    rmax = max(g["redoble"] for g in gs) or 1
    props = []
    for g in gs:
        desde = g["t"] - a.en
        if desde < 0:
            continue                                           # el tema tendría que empezar antes del vídeo
        coinc = sum(any(abs((h["t"] - desde) - x_) <= 0.08 for h in gs) for x_ in a.tambien)
        nota = g["fuerza"] / fmax + 0.6 * g["redoble"] / rmax + 0.25 * coinc
        props.append({"desde": round(desde, 3), "golpe": round(g["t"], 3), "fuerza": round(g["fuerza"] / fmax, 2),
                      "redoble": round(g["redoble"] / rmax, 2), "coincidencias": coinc, "nota": round(nota, 3),
                      "queda": round(dur - desde, 1)})
    props.sort(key=lambda r: -r["nota"])
    print(f"{musica.name}: {dur:.1f} s · {len(gs)} golpes. El golpe tiene que caer en el segundo {a.en:.2f} de la parte.")
    print(" #   desde   golpe  fuerza  redoble  coinc.  música restante")
    for i, r in enumerate(props[:a.n], 1):
        print(f"{i:2d}  {r['desde']:6.2f}  {r['golpe']:6.2f}   {r['fuerza']:.2f}    {r['redoble']:.2f}     {r['coincidencias']}      {r['queda']:.0f} s")
    if a.aplicar and guion:
        r = props[a.aplicar - 1]
        guion["musica"]["desde"] = r["desde"]
        escribir_json(a.entrada, guion)
        print(f"→ musica.desde = {r['desde']} en {a.entrada}")


if __name__ == "__main__":
    main()
