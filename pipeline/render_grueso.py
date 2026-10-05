"""Render híbrido del grueso: la base la compone ffmpeg (GPU) y Remotion solo dibuja los gráficos.

Uso:
  python pipeline/render_grueso.py videos/<id>/grueso.json [--salida out/<id>_grueso.mp4] [--sin-graficos]

Por qué: renderizar la composición Grueso entera en Remotion iba a 1/35 del tiempo real (prueba02: 60 s de
vídeo en 35 min), porque cada fotograma mueve una imagen de 2560×1440 (pantalla) y otra de la cámara.

  Base (ffmpeg):   pantalla con zooms suaves (zoompan, misma curva que Grueso.tsx: 18 fotogramas de entrada
                   y salida con smoothstep) + cámara en la esquina (bordes redondeados, borde de acento y
                   sombra; se oculta en los tramos sin cámara) + camFull (fundido y zoom lento 1 → 1,07)
                   + grano sutil.
  Gráficos:        composición GruesoGraficos de Remotion (lowerThird, showcase) en ProRes 4444 con
                   transparencia, SOLO en sus tramos; se superponen con sus efectos de sonido.
  Audio:           la voz del corte (+ música si grueso.json la tiene).
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from comun import FPS, MARCA, RAIZ, VIDEOS, contar_fotogramas, ffmpeg, ffprobe_json, leer_json

W, H = 1920, 1080
TRANS = 18 / FPS          # s: entrada/salida de cada zoom (igual que TRANS en Grueso.tsx)
MARGEN = 36


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def expr_zoom(zooms: list[dict]) -> tuple[str, str, str]:
    """Expresiones de zoompan (tiempo de entrada `it`): zoom, centro x, centro y."""
    if not zooms:
        return "1", "0.5", "0.5"
    z_terms, x_terms, y_terms = [], [], []
    for zz in zooms:
        a, b, s = zz["from"], zz["to"], zz["escala"]
        ci = f"clip((it-{a - TRANS / 2:.3f})/{TRANS:.3f},0,1)"
        co = f"clip((it-{b - TRANS / 2:.3f})/{TRANS:.3f},0,1)"
        k = f"min({ci}*{ci}*(3-2*{ci}),1-{co}*{co}*(3-2*{co}))"
        z_terms.append(f"{s - 1:.3f}*max(0,{k})")
        activo = f"between(it,{a - TRANS:.3f},{b + TRANS:.3f})"
        x_terms.append(f"{zz['x'] - 0.5:.3f}*{activo}")
        y_terms.append(f"{zz['y'] - 0.5:.3f}*{activo}")
    return "1+" + "+".join(z_terms), "0.5+" + "+".join(x_terms), "0.5+" + "+".join(y_terms)


def recursos_esquina(tmp: Path, ancho: int, alto: int, x: int, y: int, acento: str) -> tuple[Path, Path]:
    """Máscara redondeada de la cámara + capa de sombra y borde a pantalla completa (PNG)."""
    radio = 22
    mascara = Image.new("L", (ancho, alto), 0)
    ImageDraw.Draw(mascara).rounded_rectangle([0, 0, ancho - 1, alto - 1], radio, fill=255)
    ruta_m = tmp / "mascara.png"
    mascara.save(ruta_m)

    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rounded_rectangle([x, y + 18, x + ancho, y + alto + 18], radio, fill=(0, 0, 0, 150))
    capa = Image.alpha_composite(capa, sombra.filter(ImageFilter.GaussianBlur(26)))
    r, g, b = hex_rgb(acento)
    ImageDraw.Draw(capa).rounded_rectangle([x - 2, y - 2, x + ancho + 1, y + alto + 1], radio + 2,
                                           outline=(r, g, b, 150), width=2)
    ruta_c = tmp / "marco.png"
    capa.save(ruta_c)
    return ruta_m, ruta_c


def render_graficos(guion_rel: str, escenas: list[dict], tmp: Path) -> list[tuple[float, Path]]:
    """Renderiza con Remotion solo los tramos con gráficos (ProRes 4444 con alfa). Si ya existe el clip de
    ese tramo exacto, se reutiliza (el nombre incluye los fotogramas)."""
    res = []
    for k, e in enumerate(escenas):
        a, b = round(e["from"] * FPS), round(e["to"] * FPS) - 1
        salida = tmp / f"grafico_{e['type']}_{a}-{b}.mov"
        if salida.exists() and salida.stat().st_size > 0:
            print(f"  (reutilizo {salida.name})")
            res.append((a / FPS, salida))
            continue
        print(f"  Remotion: {e['type']} {e['from']:.1f}–{e['to']:.1f} s…", flush=True)
        subprocess.run(
            ["npx", "remotion", "render", "src/index.ts", "GruesoGraficos", str(salida),
             f"--props={{\"guion\":\"{guion_rel}\"}}", f"--frames={a}-{b}", "--codec=prores",
             "--prores-profile=4444", "--pixel-format=yuva444p10le", "--image-format=png",
             "--concurrency=4", "--timeout=120000", "--log=error"],
            cwd=RAIZ / "remotion", check=True, shell=True)
        res.append((a / FPS, salida))
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("guion", type=Path)
    ap.add_argument("--salida", type=Path)
    ap.add_argument("--sin-graficos", action="store_true")
    a = ap.parse_args()

    g = leer_json(a.guion)
    cuts = leer_json(VIDEOS / g["cuts"])
    colores = leer_json(MARCA / "marca.json")["colores"]
    pantalla, camara = VIDEOS / g["pantalla"], VIDEOS / g["camara"]
    n = contar_fotogramas(pantalla)
    dur = n / FPS
    iw = int(next(s for s in ffprobe_json(pantalla)["streams"] if s["codec_type"] == "video")["width"])
    ih = int(next(s for s in ffprobe_json(pantalla)["streams"] if s["codec_type"] == "video")["height"])
    id_ = a.guion.parent.name
    salida = a.salida or (RAIZ / "out" / f"{id_}_grueso.mp4")

    esq = g.get("esquina", {"lado": "der", "ancho": 0.2})
    cw = int(round(W * esq["ancho"] / 2)) * 2
    chh = int(round(cw * 9 / 16 / 2)) * 2
    cx = W - cw - MARGEN if esq["lado"] == "der" else MARGEN
    cy = H - chh - MARGEN
    camfull = next((e for e in g["escenas"] if e["type"] == "camFull"), None)
    f0 = camfull["from"] if camfull else dur + 1

    # La esquina se ve salvo en tramos sin cámara (± 4 fotogramas) y durante camFull.
    ocultar = [f"between(t,{x - 4 / FPS:.3f},{y + 4 / FPS:.3f})" for x, y in cuts.get("sin_camara", [])]
    ocultar.append(f"gte(t,{f0 + 0.4:.3f})")
    en_esquina = f"not({'+'.join(ocultar)})"

    tmp = RAIZ / "out" / "render_grueso" / id_          # se conserva: los gráficos se reutilizan
    tmp.mkdir(parents=True, exist_ok=True)
    if True:
        mascara, marco = recursos_esquina(tmp, cw, chh, cx, cy, colores["acento"])
        graficos = [] if a.sin_graficos else render_graficos(
            f"{id_}/grueso.json", [e for e in g["escenas"] if e["type"] in ("lowerThird", "showcase")], tmp)

        zexp, xexp, yexp = expr_zoom(g.get("zooms", []))
        entradas = ["-i", str(pantalla), "-i", str(camara),
                    "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", str(mascara),
                    "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", str(marco)]
        for t0, ruta in graficos:
            entradas += ["-itsoffset", f"{t0:.4f}", "-i", str(ruta)]
        musica = g.get("musica") or {}
        if musica.get("src"):
            entradas += ["-ss", str(musica.get("desde", 0)), "-stream_loop", "-1", "-i", str(VIDEOS / musica["src"])]

        lento = f"1+0.07*clip((it-{f0:.3f})/{max(dur - f0, 0.1):.3f},0,1)"
        grafo = [
            # pantalla con zooms (zoompan a 1920×1080)
            f"[0:v]zoompan=z='{zexp}':x='({xexp})*(iw-iw/zoom)':y='({yexp})*(ih-ih/zoom)'"
            f":d=1:s={W}x{H}:fps={FPS},setsar=1[pz]",
            # cámara en la esquina, redondeada
            f"[1:v]split=2[c1][c2]",
            f"[c1]scale={cw}:{chh},format=yuva420p[cs]",
            f"[2:v]format=gray,scale={cw}:{chh}[cm]",
            f"[cs][cm]alphamerge[cr]",
            f"[pz][3:v]overlay=0:0:enable='{en_esquina}'[b1]",
            f"[b1][cr]overlay={cx}:{cy}:enable='{en_esquina}'[b2]",
            # camFull: fundido y zoom lento
            # (solo el tramo final: zoompan reinicia las marcas de tiempo → se recolocan en f0)
            f"[c2]trim=start={min(f0, dur):.3f},zoompan=z='{lento}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2'"
            f":d=1:s={W}x{H}:fps={FPS},setpts=PTS+{min(f0, dur):.3f}/TB,"
            f"format=yuva420p,fade=in:st={f0:.3f}:d=0.4:alpha=1[cf]",
            f"[b2][cf]overlay=0:0:enable='gte(t,{f0:.3f})'[b3]",
        ]
        actual = "b3"
        for k in range(len(graficos)):
            idx = 4 + k
            grafo.append(f"[{actual}][{idx}:v]overlay=0:0:eof_action=pass:format=auto[g{k}]")
            actual = f"g{k}"
        grafo.append(f"[{actual}]noise=c0s=5:c0f=t,format=yuv420p[v]")
        # audio: voz + efectos de los gráficos (+ música)
        pistas = ["[0:a]"]
        for k, (t0, ruta) in enumerate(graficos):
            # Solo si el clip trae audio (el showcase, sin efecto, no lleva pista)
            if any(st["codec_type"] == "audio" for st in ffprobe_json(ruta)["streams"]):
                grafo.append(f"[{4 + k}:a]adelay={int(t0 * 1000)}:all=1[sfx{k}]")
                pistas.append(f"[sfx{k}]")
        if musica.get("src"):
            idx_m = 4 + len(graficos)
            # en bucle (-stream_loop): se recorta a la duración, entra suave y sale en los últimos 3 s
            grafo.append(f"[{idx_m}:a]atrim=0:{dur:.3f},volume={musica.get('volumen', 0.13)},"
                         f"afade=t=in:d=1.5,afade=t=out:st={max(dur - 3, 0):.3f}:d=3[mus]")
            pistas.append("[mus]")
        if len(pistas) > 1:
            grafo.append(f"{''.join(pistas)}amix=inputs={len(pistas)}:duration=first:normalize=0[a]")
            mapa_a = "[a]"
        else:
            mapa_a = "0:a"
        guion_f = tmp / "grafo.txt"
        guion_f.write_text(";".join(grafo), encoding="utf-8")

        print(f"Componiendo base con ffmpeg ({dur:.0f} s, {len(g.get('zooms', []))} zooms, "
              f"{len(graficos)} gráficos)…", flush=True)
        salida.parent.mkdir(parents=True, exist_ok=True)
        try:
            ffmpeg(*entradas, "-/filter_complex", str(guion_f), "-map", "[v]", "-map", mapa_a,
                   "-frames:v", str(n), "-r", str(FPS), "-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr",
                   "-cq", "19", "-b:v", "0", "-g", str(FPS * 2), "-c:a", "aac", "-b:a", "256k",
                   "-movflags", "+faststart", str(salida))
        except subprocess.CalledProcessError as e:
            raise SystemExit(f"ffmpeg falló:\n{e.stderr[-3000:]}")
    print(f"✔ {contar_fotogramas(salida)} fotogramas (esperados {n}) → {salida}")


if __name__ == "__main__":
    main()
