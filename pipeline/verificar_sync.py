"""Comprobación de sincronía DESPUÉS del render de una parte (intro, datos, cierre, grueso, vertical).

Uso:
  python pipeline/verificar_sync.py videos/<id>/<parte>.json out/<id>_<parte>.mp4 [--despues 0.4] [--tarde 0.12] [--pronto 0.45]

1. Audio y vídeo: misma duración que el corte (± 1 fotograma) y la voz del render alineada con la voz cortada
   (correlación de envolventes de los primeros 60 s; un desfase > 1 fotograma es un error de montaje).
2. Escenas contra sus anclas: cada escena con "ancla" se busca en las palabras alineadas (alinear.py) y se compara
   su "from" con el inicio de la frase. Llegar un poco ANTES es buen estilo (el gráfico se anticipa a la palabra):
   solo se marca si llega más de --tarde s después o más de --pronto s antes.
3. Hoja de contactos (out/qa/<id>_<parte>_sync.jpg): un fotograma por escena tomado --despues s después de su
   entrada, con el tipo, el tiempo, el desfase y la frase que se oye en ese instante. Mirarla SIEMPRE: es la forma
   rápida de ver que cada gráfico aparece cuando se dice lo que muestra.
Idea de una skill de referencia (comprobación de sincronía posterior al render), reimplementada aquí.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import unicodedata
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from comun import FFMPEG, FPS, RAIZ, VIDEOS, ffprobe_json, leer_json

SR = 8000


def normal(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]", " ", t)


def buscar_frase(palabras: list[dict], frase: str, cerca: float) -> float | None:
    """Inicio de la aparición de `frase` (≥ 2 palabras) más cercana a `cerca`."""
    objetivo = normal(frase).split()
    if len(objetivo) < 2:
        return None
    objetivo = objetivo[:6]
    toks = [normal(w["w"]).split() for w in palabras]
    planas = [(k, t) for k, ts in enumerate(toks) for t in ts]
    mejores = []
    for i in range(len(planas) - len(objetivo) + 1):
        if [t for _, t in planas[i:i + len(objetivo)]] == objetivo:
            mejores.append(palabras[planas[i][0]]["inicio"])
    return min(mejores, key=lambda t: abs(t - cerca)) if mejores else None


def frase_en(palabras: list[dict], t: float, n: int = 6) -> str:
    k = next((i for i, w in enumerate(palabras) if w["fin"] >= t), len(palabras) - 1)
    return " ".join(w["w"] for w in palabras[max(0, k - 1):k + n - 1])


def audio(ruta: Path, segundos: float = 60) -> np.ndarray:
    r = subprocess.run([FFMPEG, "-v", "error", "-t", str(segundos), "-i", str(ruta), "-vn", "-ac", "1", "-ar", str(SR),
                        "-f", "f32le", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32)


def envolvente(x: np.ndarray) -> np.ndarray:
    hop = SR // 200                                         # 5 ms
    n = len(x) // hop
    e = np.log1p(100 * np.abs(x[:n * hop]).reshape(n, hop).mean(1))
    return (e - e.mean()) / (e.std() + 1e-9)


def desfase_voz(render: Path, voz: Path) -> tuple[float, float]:
    a, b = envolvente(audio(render)), envolvente(audio(voz))
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    tam = 1 << int(np.ceil(np.log2(2 * n)))
    c = np.fft.irfft(np.fft.rfft(a, tam) * np.conj(np.fft.rfft(b, tam)), tam)
    c = np.concatenate([c[-n + 1:], c[:n]])
    lag = int(np.argmax(c)) - (n - 1)
    return lag / 200, float(c.max() / n)


def fotograma(video: Path, t: float, ancho: int = 560) -> Image.Image:
    r = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                        "-vf", f"scale={ancho}:-2", "-f", "image2pipe", "-vcodec", "png", "-"],
                       capture_output=True, check=True)
    from io import BytesIO
    return Image.open(BytesIO(r.stdout)).convert("RGB")


def fuente(tam: int) -> ImageFont.ImageFont:
    for f in ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"]:
        if Path(f).exists():
            return ImageFont.truetype(f, tam)
    return ImageFont.load_default()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("guion", type=Path)
    p.add_argument("render", type=Path)
    p.add_argument("--despues", type=float, default=0.4)
    p.add_argument("--tarde", type=float, default=0.12)
    p.add_argument("--pronto", type=float, default=0.45)
    a = p.parse_args()

    g = leer_json(a.guion)
    palabras = leer_json(VIDEOS / g["palabras"]) if g.get("palabras") else []
    cuts = leer_json(VIDEOS / g["cuts"]) if g.get("cuts") else None
    problemas = []

    # 1. duraciones y voz
    info = ffprobe_json(a.render)
    dv = float(next(s for s in info["streams"] if s["codec_type"] == "video")["duration"])
    da = float(next((s for s in info["streams"] if s["codec_type"] == "audio"), {"duration": 0})["duration"])
    linea = f"Render: vídeo {dv:.3f} s · audio {da:.3f} s"
    if abs(dv - da) > 1.5 / FPS:
        problemas.append(f"audio y vídeo del render difieren {abs(dv - da) * 1000:.0f} ms")
    if cuts:
        linea += f" · corte {cuts['duracion']:.3f} s"
        if dv + 1.5 / FPS < cuts["duracion"]:
            problemas.append(f"el render dura {cuts['duracion'] - dv:.2f} s menos que el corte")
    print(linea)
    voz = (VIDEOS / g["palabras"]).with_name(Path(g["palabras"]).name.replace(".palabras_corte.json", ".voz.wav")) \
        if g.get("palabras") else None
    if voz and voz.exists():
        lag, corr = desfase_voz(a.render, voz)
        print(f"Voz del render vs voz cortada: desfase {lag * 1000:+.0f} ms (correlación {corr:.2f})")
        if abs(lag) > 1 / FPS and corr > 0.3:
            nota = " (priming del AAC de Remotion: 07_final lo recorta solo)" if 0 < lag <= 0.2 else ""
            problemas.append(f"la voz del render va {lag * 1000:+.0f} ms respecto al corte{nota}")

    # 2. escenas contra anclas
    filas = []
    for n, e in enumerate(g.get("escenas", []), 1):
        desde = float(e.get("from", 0))
        ancla = e.get("ancla", "")
        t_ancla = buscar_frase(palabras, ancla.split("·")[0], desde) if ancla and palabras else None
        delta = None if t_ancla is None else desde - t_ancla
        marca = ""
        if delta is not None and (delta > a.tarde or -delta > a.pronto):
            marca = "TARDE" if delta > 0 else "PRONTO"
            problemas.append(f"#{n} {e['type']} en {desde:.2f} s: {marca.lower()} {abs(delta) * 1000:.0f} ms "
                             f"respecto a «{ancla.split('·')[0].strip()[:40]}» ({t_ancla:.2f} s)")
        filas.append((n, e, desde, delta, marca))

    # 3. hoja de contactos
    ancho, alto_txt, cols = 560, 64, 3
    teselas = []
    for n, e, desde, delta, marca in filas:
        t = min(desde + a.despues, dv - 0.05)
        img = fotograma(a.render, t, ancho)
        lienzo = Image.new("RGB", (ancho, img.height + alto_txt), (18, 18, 18))
        lienzo.paste(img, (0, 0))
        d = ImageDraw.Draw(lienzo)
        color = (255, 90, 90) if marca else (230, 230, 230)
        dtxt = "sin ancla" if delta is None else f"Δ {delta * 1000:+.0f} ms {marca}"
        d.text((8, img.height + 4), f"#{n} {e['type']} · {desde:.2f} s · {dtxt}", fill=color, font=fuente(17))
        d.text((8, img.height + 30), f"«{frase_en(palabras, t)}»"[:70] if palabras else "", fill=(160, 160, 160),
               font=fuente(15))
        teselas.append(lienzo)
    if teselas:
        h = max(t.height for t in teselas)
        filas_n = (len(teselas) + cols - 1) // cols
        hoja = Image.new("RGB", (cols * ancho, filas_n * h), (0, 0, 0))
        for i, t in enumerate(teselas):
            hoja.paste(t, ((i % cols) * ancho, (i // cols) * h))
        nombre = f"{Path(g.get('video', a.guion.stem)).parent.name or a.guion.parent.name}_{a.guion.stem}_sync.jpg"
        salida = RAIZ / "out" / "qa" / nombre
        salida.parent.mkdir(parents=True, exist_ok=True)
        hoja.save(salida, quality=85)
        print(f"→ {salida} ({len(teselas)} escenas)")

    if problemas:
        print("✘ revisar:")
        for x in problemas:
            print("  · " + x)
    else:
        print("✔ sincronía correcta (duraciones, voz y escenas dentro de tolerancia)")


if __name__ == "__main__":
    main()
