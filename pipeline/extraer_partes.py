"""Separa una sesión de cámara (todos los bloques grabados seguidos) en las partes del vídeo.

Uso:
  python pipeline/extraer_partes.py <sesion.mov> videos/<id>/partes.json

partes.json: {"intro": [[21.7, 59.7], [71.9, 193.8]], "datos": [[…]], …}  (segundos de la sesión; cada parte
une sus tramos en orden). Salida: videos/<id>/<parte>_bruto.mov (vídeo + audio sin pérdidas), que luego pasa por
02_transcribe → 03_tomas → 01_cut_silences como cualquier intro.

Los tramos se eligen con la transcripción de la sesión: empiezan ~0,3 s antes de la primera palabra del bloque
(después de la claqueta «Bloque X») y acaban ~0,4 s después de la última. Las claquetas, «Corte», «Fin» y
las tomas falladas quedan fuera; las repeticiones DENTRO de un bloque las resuelve 03_tomas.
"""
from __future__ import annotations

import sys
from pathlib import Path

from comun import FPS, contar_fotogramas, ffmpeg, leer_json


def main() -> None:
    sesion, cfg = Path(sys.argv[1]), Path(sys.argv[2])
    for parte, tramos in leer_json(cfg).items():
        g = []
        for k, (a, b) in enumerate(tramos):
            g.append(f"[0:v]trim=start={a}:end={b},setpts=PTS-STARTPTS[v{k}]")
            g.append(f"[0:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS[a{k}]")
        g.append("".join(f"[v{k}][a{k}]" for k in range(len(tramos))) + f"concat=n={len(tramos)}:v=1:a=1[v][a]")
        salida = cfg.parent / f"{parte}_bruto.mov"
        ffmpeg("-i", str(sesion), "-filter_complex", ";".join(g), "-map", "[v]", "-map", "[a]", "-r", str(FPS),
               "-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "17", "-b:v", "0",
               "-c:a", "pcm_s16le", "-ar", "48000", str(salida))
        print(f"✔ {salida}: {sum(b - a for a, b in tramos):.1f} s · {contar_fotogramas(salida)} fotogramas")


if __name__ == "__main__":
    main()
