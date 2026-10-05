"""Hojas de fotogramas en cuadrícula para revisar un vídeo (pixelado de datos personales, zooms…).

Uso:
  python pipeline/hojas.py <vídeo> <prefijo salida> [--cada 3] [--cols 3] [--filas 3] [--ancho 800]
                           [--rejilla 160] [--desde 0] [--hasta fin]

Genera <prefijo>_01.jpg, _02.jpg… Cada miniatura lleva su tiempo (s) y una rejilla con coordenadas en
PÍXELES DEL VÍDEO ORIGINAL (cada `--rejilla` px), para anotar los rectángulos de `pixelar` en
grueso.prep.json: {"desde", "hasta", "rect": [x, y, ancho, alto]}.
Procedimiento: 1) hojas de la pantalla bruta → anotar; 2) 04_grueso.py; 3) hojas del corte → verificar.
"""
from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from comun import ffmpeg, ffprobe_json


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video", type=Path)
    p.add_argument("prefijo", type=Path)
    p.add_argument("--cada", type=float, default=3.0)
    p.add_argument("--cols", type=int, default=3)
    p.add_argument("--filas", type=int, default=3)
    p.add_argument("--ancho", type=int, default=800)
    p.add_argument("--rejilla", type=int, default=160)
    p.add_argument("--desde", type=float, default=0.0)
    p.add_argument("--hasta", type=float)
    p.add_argument("--cambios", type=float, default=0.0,
                   help="solo fotogramas que difieren del anterior guardado (diferencia media, 0–255; p. ej. 4)")
    a = p.parse_args()

    info = ffprobe_json(a.video)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    W, H = int(v["width"]), int(v["height"])
    dur = float(info["format"]["duration"])
    hasta = min(a.hasta or dur, dur)
    esc = a.ancho / W
    alto = int(round(H * esc))

    tmp = Path(tempfile.mkdtemp(prefix="hojas_"))
    try:
        ffmpeg("-ss", f"{a.desde:.3f}", "-to", f"{hasta:.3f}", "-i", str(a.video),
               "-vf", f"fps=1/{a.cada},scale={a.ancho}:{alto}", "-q:v", "3", str(tmp / "%05d.jpg"))
        cuadros = sorted(tmp.glob("*.jpg"))
        tiempos = [a.desde + k * a.cada for k in range(len(cuadros))]
        if a.cambios > 0:
            # Solo cuando cambia el contenido: en un tutorial la pantalla está quieta mucho rato.
            import numpy as np
            guardados, ultimo = [], None
            for c, t in zip(cuadros, tiempos):
                g = np.asarray(Image.open(c).convert("L").resize((160, 90)), dtype=np.int16)
                if ultimo is None or np.abs(g - ultimo).mean() > a.cambios:
                    guardados.append((c, t))
                    ultimo = g
            cuadros, tiempos = [c for c, _ in guardados], [t for _, t in guardados]
        try:
            fuente = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 16)
            grande = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 22)
        except Exception:
            fuente = grande = ImageFont.load_default()
        por_hoja = a.cols * a.filas
        a.prefijo.parent.mkdir(parents=True, exist_ok=True)
        hojas = 0
        for h0 in range(0, len(cuadros), por_hoja):
            grupo = cuadros[h0:h0 + por_hoja]
            hoja = Image.new("RGB", (a.cols * (a.ancho + 10) + 10, a.filas * (alto + 10) + 10), (20, 20, 20))
            for k, c in enumerate(grupo):
                im = Image.open(c).convert("RGB")
                d = ImageDraw.Draw(im, "RGBA")
                for x in range(a.rejilla, W, a.rejilla):
                    d.line([(x * esc, 0), (x * esc, alto)], fill=(255, 210, 31, 70))
                    d.text((x * esc + 2, 2), str(x), fill=(255, 210, 31, 230), font=fuente)
                for y in range(a.rejilla, H, a.rejilla):
                    d.line([(0, y * esc), (a.ancho, y * esc)], fill=(255, 210, 31, 70))
                    d.text((2, y * esc + 2), str(y), fill=(255, 210, 31, 230), font=fuente)
                t = tiempos[h0 + k]
                d.rectangle([a.ancho - 118, alto - 34, a.ancho, alto], fill=(0, 0, 0, 190))
                d.text((a.ancho - 112, alto - 30), f"{t:7.1f} s", fill=(255, 255, 255, 255), font=grande)
                hoja.paste(im, (10 + (k % a.cols) * (a.ancho + 10), 10 + (k // a.cols) * (alto + 10)))
            hojas += 1
            hoja.save(f"{a.prefijo}_{hojas:02d}.jpg", quality=86)
        print(f"{len(cuadros)} fotogramas ({W}×{H}, cada {a.cada} s) en {hojas} hojas → {a.prefijo}_NN.jpg")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
