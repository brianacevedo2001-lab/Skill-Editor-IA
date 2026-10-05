"""Anuncio de producto con locución (composiciones Anuncio 9:16 y AnuncioLinkedin 4:5) → entregas por red.

Uso:
  python pipeline/anuncio.py <id> [--sin-render] [--sin-drive]

Lee videos/<id>/anuncio.json ({voz, duracion, musica:{src, volumen, desde}, portada: seg, textos:{youtube, instagram,
tiktok, linkedin}, escenas}) y saca en out/entregas/<id>/:
  <id>_youtube.mp4 (CON música), <id>_instagram.mp4 y <id>_tiktok.mp4 (SIN música: se pone al publicar),
  <id>_linkedin.mp4 (4:5, sin música), <id>_portada.jpg y <id>_textos.txt; todo a −14 LUFS y con la voz en sincronía
  (09_shorts.exportar recorta el priming del AAC de Remotion). Copia SIEMPRE a Drive final/<id>/ salvo --sin-drive.
Ejemplo real: anuncio01 (réplica del estilo de un anuncio de SaaS con la app de la marca).
"""
from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
from pathlib import Path

from comun import FFMPEG, MARCA, OUT, RAIZ, VIDEOS, contar_fotogramas, copiar_reanudable, leer_json

shorts = importlib.import_module("09_shorts")
REMOTION = RAIZ / "remotion"


def render(comp: str, guion: str, salida: Path) -> None:
    salida.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["npx", "remotion", "render", "src/index.ts", comp, str(salida), f"--props={{\"guion\":\"{guion}\"}}",
           "--timeout=180000", "--hardware-acceleration=if-possible", "--concurrency=8"]
    # Remotion a veces falla al mezclar el audio («remotion-audio-mixing\0.wav: No such file or directory», carpeta
    # temporal que desaparece): es puntual, se reintenta.
    for intento in range(3):
        print(f"  {comp}…{f' (reintento {intento})' if intento else ''}", flush=True)
        if subprocess.run(cmd, cwd=REMOTION, shell=sys.platform == "win32").returncode == 0:
            return
    raise SystemExit(f"El render de {comp} falló 3 veces")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("id")
    p.add_argument("--sin-render", action="store_true")
    p.add_argument("--sin-drive", action="store_true")
    a = p.parse_args()
    g = leer_json(VIDEOS / a.id / "anuncio.json")
    guion = f"{a.id}/anuncio.json"
    base9, base45 = OUT / "anuncio" / a.id / "base_9x16.mp4", OUT / "anuncio" / a.id / "base_4x5.mp4"
    if not a.sin_render:
        render("Anuncio", guion, base9)
        render("AnuncioLinkedin", guion, base45)
    voz = VIDEOS / g["voz"]
    entrega = OUT / "entregas" / a.id
    entrega.mkdir(parents=True, exist_ok=True)
    hechos = []
    for red, base, musica in [("youtube", base9, g.get("musica")), ("instagram", base9, None), ("tiktok", base9, None),
                              ("linkedin", base45, None)]:
        sal = entrega / f"{a.id}_{red}.mp4"
        lufs = shorts.exportar(base, sal, musica, voz)
        print(f"  ✔ {sal.name}: {contar_fotogramas(sal)} fotogramas · {lufs} LUFS{' · con música' if musica else ''}")
        hechos.append(sal)
    portada = entrega / f"{a.id}_portada.jpg"
    subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", str(g.get("portada", 1.0)),
                    "-i", str(base9), "-frames:v", "1", "-q:v", "2", str(portada)], check=True)
    nombres = {"youtube": "YouTube Shorts (con música)", "instagram": "Instagram Reels (añade la música en la app)",
               "tiktok": "TikTok (añade la música al publicar)", "linkedin": "LinkedIn (vídeo 4:5)"}
    textos = "\n\n".join(f"══ {nombres[r]} ══\n" + (f"Título: {t['titulo']}\n\n" if t.get("titulo") else "") + t["texto"].strip()
                         for r, t in g.get("textos", {}).items())
    (entrega / f"{a.id}_textos.txt").write_text(textos + "\n", encoding="utf-8")
    hechos += [portada, entrega / f"{a.id}_textos.txt"]
    if not a.sin_drive:
        destino = Path(leer_json(MARCA / "proyecto.json")["entregas"]["carpetaLocalDrive"]) / a.id
        for h in hechos:
            copiar_reanudable(h, destino / h.name)
        print(f"Copiado a {destino}")


if __name__ == "__main__":
    main()
