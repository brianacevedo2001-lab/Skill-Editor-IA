"""Anuncio de producto con locución (composiciones Anuncio 9:16 y AnuncioLinkedin 4:5) → entregas por red.

Uso:
  python pipeline/anuncio.py <id> [--sin-render] [--sin-drive] [--motor remotion|hyperframes]

Lee videos/<id>/anuncio.json ({voz, duracion, musica:{src, volumen, desde}, portada: seg, textos:{youtube, instagram,
tiktok, linkedin}, escenas, motor?}) y saca en out/entregas/<id>/:
  <id>_youtube.mp4 (CON música), <id>_instagram.mp4 y <id>_tiktok.mp4 (SIN música: se pone al publicar),
  <id>_linkedin.mp4 (4:5, sin música), <id>_portada.jpg y <id>_textos.txt; todo a −14 LUFS y con la voz en sincronía
  (09_shorts.exportar recorta el priming del AAC de Remotion). Copia SIEMPRE a Drive final/<id>/ salvo --sin-drive.
Ejemplo real: anuncio01 (réplica del estilo de un anuncio de SaaS con la app de la marca).
Motor (pipeline/motor.py): Remotion (remotion/src/promo/Anuncio.tsx, las 13 escenas de producto) o HyperFrames
(hyperframes/anuncio: apertura, chat, remate, final + titulo/tarjetas/dato/barras; el resto muestra su «rotulo»).
"""
from __future__ import annotations

import argparse
import importlib
import subprocess
from pathlib import Path

import motor
from comun import FFMPEG, MARCA, OUT, VIDEOS, contar_fotogramas, copiar_reanudable, leer_json

shorts = importlib.import_module("09_shorts")


def render(comp: str, guion: str, salida: Path, m: str, t_portada: float) -> None:
    """Anuncio (9:16) o AnuncioLinkedin (4:5) con el motor elegido (pipeline/motor.py).
    Remotion a veces falla al mezclar el audio («remotion-audio-mixing\\0.wav: No such file or directory», carpeta
    temporal que desaparece): es puntual, se reintenta hasta 3 veces. En HyperFrames el cuadro 0 pasa a ser el de la
    portada (regla de portada)."""
    if m == "hyperframes":
        motor.render_video(comp, guion, salida, m, portada_t=t_portada)
        return
    motor.render_video(comp, guion, salida, m, intentos=3,
                       remotion_extra=["--timeout=180000", "--hardware-acceleration=if-possible", "--concurrency=8"])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("id")
    p.add_argument("--sin-render", action="store_true")
    p.add_argument("--sin-drive", action="store_true")
    motor.argumento(p)
    a = p.parse_args()
    g = leer_json(VIDEOS / a.id / "anuncio.json")
    m = motor.elegir(g, a.motor)
    guion = f"{a.id}/anuncio.json"
    base9, base45 = OUT / "anuncio" / a.id / "base_9x16.mp4", OUT / "anuncio" / a.id / "base_4x5.mp4"
    if not a.sin_render:
        print(f"Motor: {m}")
        render("Anuncio", guion, base9, m, float(g.get("portada", 1.0)))
        render("AnuncioLinkedin", guion, base45, m, float(g.get("portada", 1.0)))
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
