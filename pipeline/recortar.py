"""Recorta la persona de un vídeo a cámara: capa con transparencia para poner gráficos DETRÁS de ella.

Uso:
  python pipeline/recortar.py videos/<id>/intro.mp4                 → videos/<id>/intro.persona.webm
  python pipeline/recortar.py videos/<id>/intro.mp4 --desde 20 --hasta 35    (solo un tramo: más rápido y ligero)

- Modelo: Robust Video Matting (PeterL1n/RobustVideoMatting, torch.hub, mobilenetv3) en la GPU. Es recurrente: usa
  los fotogramas anteriores, así que el borde (pelo, gafas) no parpadea como con un segmentador fotograma a fotograma.
  Licencia GPL-3.0: se usa como herramienta externa (se descarga en la caché de torch), no se copia su código aquí.
- Salida: WebM VP9 con alfa (yuva420p) del MISMO tamaño y número de fotogramas que el vídeo, para que Remotion lo
  ponga encima con los mismos punch-in. Con --desde/--hasta el resto del vídeo sale transparente (pesa casi nada).
- En el guion: "persona": "<id>/intro.persona.webm" y escenas con "capa": "detras" (ver CLAUDE.md › Capas).
Idea de una skill de referencia (capas con la persona recortada), reimplementada aquí.
"""
from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path

import numpy as np

from comun import FFMPEG, FPS, contar_fotogramas, ffprobe_json


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video", type=Path)
    p.add_argument("--salida", type=Path)
    p.add_argument("--desde", type=float, default=0.0)
    p.add_argument("--hasta", type=float)
    p.add_argument("--reduccion", type=float, help="downsample_ratio de RVM (por defecto según la resolución)")
    a = p.parse_args()

    salida = a.salida or a.video.with_name(a.video.stem + ".persona.webm")
    v = next(s for s in ffprobe_json(a.video)["streams"] if s["codec_type"] == "video")
    W, H = int(v["width"]), int(v["height"])
    total = contar_fotogramas(a.video)
    f0 = int(round(a.desde * FPS))
    f1 = min(total, int(round(a.hasta * FPS)) if a.hasta else total)
    reduccion = a.reduccion or (0.25 if max(W, H) <= 1920 else 0.125)

    import torch
    disp = "cuda" if torch.cuda.is_available() else "cpu"
    modelo = torch.hub.load("PeterL1n/RobustVideoMatting", "mobilenetv3", trust_repo=True).to(disp).eval()
    if disp == "cuda":
        modelo = modelo.half()

    lector = subprocess.Popen([FFMPEG, "-v", "error", "-i", str(a.video), "-vf", f"fps={FPS}", "-f", "rawvideo",
                               "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    salida.parent.mkdir(parents=True, exist_ok=True)
    escritor = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                                 "-r", str(FPS), "-i", "-", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
                                 "-b:v", "0", "-crf", "30", "-deadline", "realtime", "-cpu-used", "8", "-row-mt", "1",
                                 "-auto-alt-ref", "0", "-an", str(salida)], stdin=subprocess.PIPE)
    tam = W * H * 3
    vacio = np.zeros((H, W, 4), np.uint8).tobytes()
    rec = [None] * 4
    t0, i = time.time(), 0
    with torch.inference_mode():
        while True:
            buf = lector.stdout.read(tam)
            if len(buf) < tam:
                break
            if f0 <= i < f1:
                x = torch.frombuffer(bytearray(buf), dtype=torch.uint8).to(disp).view(H, W, 3)
                src = x.permute(2, 0, 1)[None].to(torch.float16 if disp == "cuda" else torch.float32) / 255
                _, pha, *rec = modelo(src, *rec, downsample_ratio=reduccion)
                # color ORIGINAL + alfa (no el `fgr` del modelo): la capa coincide píxel a píxel con la cámara y no
                # hay salto cuando aparece encima de ella
                a8 = pha[0, 0].clamp(0, 1).mul(255).byte()
                rgba = torch.cat([x, a8[..., None]], 2)
                escritor.stdin.write(rgba.contiguous().cpu().numpy().tobytes())
            else:
                escritor.stdin.write(vacio)
            i += 1
            if i % 300 == 0:
                print(f"  {i}/{total} fotogramas · {i / (time.time() - t0):.0f} fps", flush=True)
    escritor.stdin.close()
    escritor.wait()
    lector.wait()
    n = contar_fotogramas(salida)
    print(f"{'✔' if n == total else '✘'} {salida}: {n}/{total} fotogramas · {W}×{H} · "
          f"{salida.stat().st_size / 1e6:.1f} MB · {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
