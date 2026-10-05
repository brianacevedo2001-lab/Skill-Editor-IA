"""Montaje final: une las partes, deja el audio a −14 LUFS y prepara la entrega para YouTube.

Uso:
  python pipeline/07_final.py "<carpeta de entrega>" "<nombre>.mp4" intro [disclaimer] grueso \\
         --id <id> --capitulos videos/<id>/capitulos_youtube.txt [--titulo "..."] [--miniatura ruta.jpg]

Cada parte es un nombre (→ out/<id>_<parte>.mp4) o la ruta de un .mp4 (p. ej. out/prueba01_intro.mp4).

1. Une las partes en orden. Si en una parte la imagen dura menos que el audio (p. ej. la animación final de
   Remotion se pasa del clip), se alarga congelando el último fotograma (tpad=stop_mode=clone); si es el audio
   el que se queda corto, se rellena con silencio (apad).
2. Audio a −14 LUFS en DOS pasadas: loudnorm mide y luego se aplica una ganancia LINEAL (no bombea la voz
   ni la música). Si esa ganancia llevara algún pico por encima de −1,5 dBTP, un limitador recorta solo
   esos picos (loudnorm linear=true se pasaría a modo dinámico y comprimiría todo).
3. Capítulos calculados sobre el montaje FINAL. capitulos_youtube.txt lleva una línea por capítulo con el
   tiempo RELATIVO a su parte (más cómodo: los tiempos salen del corte de cada parte):
       intro   00:00  Por qué la venta se gana en los primeros minutos
       grueso  01:04  Clientes esperando un humano
   Se comprueban las reglas de YouTube: el primero en 00:00, al menos 3 y cada uno de ≥ 10 s.
4. descripcion_youtube.txt a partir de la plantilla videos/_shared/descripciones/plantilla.txt
   ({titulo}, {resumen} ← videos/<id>/resumen.txt, {capitulos}, {canal}, {marca}, {persona}, {sitio},
   {redes} ← marca/canal.json).
5. En la carpeta de entrega quedan: el vídeo, la miniatura, capitulos_youtube.txt y descripcion_youtube.txt,
   y SIEMPRE se copia a la carpeta de Drive de entregas (final/<id>/; el usuario publica desde ahí con cualquier
   dispositivo). --sin-drive para no copiar. --solo-textos rehace capítulos/descripción/miniatura sin
   volver a codificar el vídeo.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from comun import (FPS, MARCA, OUT, RAIZ, VIDEOS, contar_fotogramas, copiar_reanudable, duracion, ffmpeg,
                   ffprobe_json, leer_json)

OBJETIVO = dict(I=-14.0, TP=-1.5, LRA=11.0)
PLANTILLA = VIDEOS / "_shared" / "descripciones" / "plantilla.txt"


def resolver(parte: str, id_: str | None) -> Path:
    p = Path(parte)
    if p.suffix.lower() == ".mp4":
        return p if p.is_absolute() else RAIZ / p
    if not id_:
        sys.exit(f"«{parte}» no es una ruta .mp4: pasa --id para buscar out/<id>_{parte}.mp4")
    return OUT / f"{id_}_{parte}.mp4"


def etiqueta(ruta: Path) -> str:
    """intro / disclaimer / grueso a partir del nombre (out/prueba01_intro.mp4 → intro)."""
    return ruta.stem.rsplit("_", 1)[-1].lower()


def medir(ruta: Path) -> dict:
    info = ffprobe_json(ruta)
    tiene_audio = any(s["codec_type"] == "audio" for s in info["streams"])
    v = contar_fotogramas(ruta) / FPS
    a = 0.0
    if tiene_audio:
        st = next(s for s in info["streams"] if s["codec_type"] == "audio")
        a = float(st.get("duration") or info["format"]["duration"])
    return {"video": v, "audio": a, "tiene_audio": tiene_audio, "dur": max(v, a)}


def cadenas(partes: list[dict], con_video: bool) -> list[str]:
    g = []
    for i, p in enumerate(partes):
        d = p["dur"]
        if con_video:
            relleno = max(0.0, d - p["video"])
            tp = f",tpad=stop_mode=clone:stop_duration={relleno:.3f}" if relleno > 1 / FPS / 2 else ""
            g.append(f"[{i}:v]fps={FPS},scale=1920:1080,setsar=1,format=yuv420p{tp},trim=duration={d:.3f}[v{i}]")
        if p["tiene_audio"]:
            ade = f"atrim=start={p['adelanto']:.3f},asetpts=PTS-STARTPTS," if p.get("adelanto") else ""
            g.append(f"[{i}:a]{ade}aresample=48000,aformat=channel_layouts=stereo,apad=whole_dur={d:.3f},"
                     f"atrim=duration={d:.3f}[a{i}]")
        else:
            g.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={d:.3f}[a{i}]")
    n = len(partes)
    if con_video:
        g.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a]")
    else:
        g.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[a]")
    return g


def fmt(t: float) -> str:
    t = int(round(t))
    h, m, s = t // 3600, t % 3600 // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def leer_tiempo(s: str) -> float:
    n = [float(x) for x in s.split(":")]
    return sum(v * 60 ** k for k, v in enumerate(reversed(n)))


def capitulos(ruta: Path, inicios: dict[str, float]) -> list[tuple[float, str]]:
    res = []
    for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        m = re.match(r"(\w+)\s+([\d:]+)\s*-?\s*(.+)", linea)
        if not m:
            sys.exit(f"{ruta}:{n}: formato «parte MM:SS Título»: {linea!r}")
        parte, t, titulo = m.group(1).lower(), leer_tiempo(m.group(2)), m.group(3).strip()
        if parte not in inicios:
            sys.exit(f"{ruta}:{n}: la parte «{parte}» no está en el montaje ({', '.join(inicios)})")
        res.append((inicios[parte] + t, titulo))
    res.sort()
    errores = []
    if not res or res[0][0] > 0.5:
        errores.append("el primer capítulo debe empezar en 00:00")
    if len(res) < 3:
        errores.append("YouTube pide al menos 3 capítulos")
    for (t0, a), (t1, b) in zip(res, res[1:]):
        if t1 - t0 < 10:
            errores.append(f"«{a}» dura {t1 - t0:.1f} s (mínimo 10 s)")
    if errores:
        sys.exit("Capítulos no válidos:\n  - " + "\n  - ".join(errores))
    return res


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("entrega", type=Path)
    p.add_argument("nombre")
    p.add_argument("partes", nargs="+")
    p.add_argument("--id")
    p.add_argument("--capitulos", type=Path)
    p.add_argument("--titulo", default="")
    p.add_argument("--miniatura", type=Path)
    p.add_argument("--solo-textos", action="store_true")
    p.add_argument("--sin-drive", action="store_true")
    a = p.parse_args()

    rutas = [resolver(x, a.id) for x in a.partes]
    for r in rutas:
        if not r.exists():
            sys.exit(f"No existe {r}")
    partes = [medir(r) for r in rutas]
    # Los mp4 de Remotion traen el «priming» del AAC como audio real: la voz va ~45 ms tarde respecto a la imagen
    # (proyecto01: intro, datos y cierre +45 ms; el grueso, montado con ffmpeg, 0). Se mide contra la voz cortada de
    # la parte y se recorta ese adelanto del audio.
    from verificar_sync import desfase_voz
    for r, m in zip(rutas, partes):
        voz = VIDEOS / (a.id or "") / f"{etiqueta(r)}.voz.wav"
        if a.id and m["tiene_audio"] and voz.exists():
            lag, corr = desfase_voz(r, voz)
            if 0 < lag <= 0.2 and corr > 0.3:
                m["adelanto"] = lag
                print(f"  {etiqueta(r)}: la voz llega {lag * 1000:.0f} ms tarde → se recorta del audio")
    inicios, t = {}, 0.0
    for r, m in zip(rutas, partes):
        inicios.setdefault(etiqueta(r), t)
        extra = ""
        if m["dur"] - m["video"] > 0.02:
            extra = f"  (imagen alargada {m['dur'] - m['video']:.2f} s congelando el último fotograma)"
        elif m["dur"] - m["audio"] > 0.02:
            extra = f"  (audio rellenado {m['dur'] - m['audio']:.2f} s)"
        print(f"  {etiqueta(r):10s} {fmt(t)}  {m['dur']:7.2f} s  {r.name}{extra}")
        t += m["dur"]
    total = t
    entradas = [x for r in rutas for x in ("-i", str(r))]
    a.entrega.mkdir(parents=True, exist_ok=True)
    salida = a.entrega / a.nombre
    if not (a.solo_textos and salida.exists()):
        codificar(entradas, partes, salida, total)
    textos(a, inicios)
    if not a.sin_drive:
        destino = Path(leer_json(MARCA / "proyecto.json")["entregas"]["carpetaLocalDrive"]) / (a.id or a.entrega.name)
        for f in sorted(x for x in a.entrega.iterdir() if x.is_file()):
            copiar_reanudable(f, destino / f.name)
        print(f"Copiado a {destino} — Google Drive lo subirá en segundo plano.")


def codificar(entradas: list[str], partes: list[dict], salida: Path, total: float) -> None:

    # 1.ª pasada: medir el audio del montaje
    print(f"Midiendo sonoridad ({fmt(total)})…")
    g = ";".join(cadenas(partes, False)) + f";[a]loudnorm=I={OBJETIVO['I']}:TP={OBJETIVO['TP']}:LRA={OBJETIVO['LRA']}:print_format=json[ao]"
    r = ffmpeg(*entradas, "-filter_complex", g, "-map", "[ao]", "-f", "null", "-", silencioso=False)
    medida = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    print(f"  entrada {medida['input_i']} LUFS · pico {medida['input_tp']} dBTP · LRA {medida['input_lra']}")

    # 2.ª pasada: aplicar (lineal) y codificar
    # loudnorm linear=true solo es lineal si la ganancia no empuja el pico por encima de TP; si no, cambia
    # a modo dinámico (comprime). Por eso: ganancia lineal exacta + limitador que solo toca los picos sueltos.
    ganancia = OBJETIVO["I"] - float(medida["input_i"])
    pico_tras = float(medida["input_tp"]) + ganancia
    limite = 10 ** ((OBJETIVO["TP"] - 0.5) / 20)          # margen: el limitador mide pico de muestra, no true peak
    ln = (f"volume={ganancia:.2f}dB,alimiter=limit={limite:.4f}:attack=5:release=80:level=false"
          if pico_tras > OBJETIVO["TP"] else f"volume={ganancia:.2f}dB")
    print(f"  ganancia {ganancia:+.2f} dB" + (f" · limitador (el pico subiría a {pico_tras:+.1f} dBTP)"
                                             if pico_tras > OBJETIVO["TP"] else ""))
    g = ";".join(cadenas(partes, True)) + f";[a]{ln},aresample=48000[ao]"
    print("Codificando montaje final…")
    r = ffmpeg(*entradas, "-filter_complex", g, "-map", "[v]", "-map", "[ao]",
               "-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "19", "-b:v", "0", "-g", str(FPS * 2),
               "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(salida), silencioso=False)

    # Verificación
    r = ffmpeg("-i", str(salida), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-", silencioso=False)
    i_final = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)[-1]
    pico = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r.stderr)
    fotos, esperadas = contar_fotogramas(salida), round(total * FPS)
    print(f"✔ {salida}\n  {fotos} fotogramas (esperados {esperadas}) · {duracion(salida):.2f} s · "
          f"{i_final} LUFS · pico {pico[-1] if pico else '?'} dBTP")
    if abs(fotos - esperadas) > 2:
        print("  ⚠ el número de fotogramas no cuadra")



def textos(a, inicios: dict[str, float]) -> None:
    caps = capitulos(a.capitulos, inicios) if a.capitulos else []
    texto_caps = "\n".join(f"{fmt(t)} - {titulo}" for t, titulo in caps)
    if caps:
        (a.entrega / "capitulos_youtube.txt").write_text(texto_caps + "\n", encoding="utf-8")
        print("Capítulos:\n  " + texto_caps.replace("\n", "\n  "))
    if PLANTILLA.exists():
        marca, canal = leer_json(MARCA / "marca.json"), leer_json(MARCA / "canal.json")
        resumen = VIDEOS / (a.id or "") / "resumen.txt"
        datos = {
            "titulo": a.titulo, "capitulos": texto_caps,
            "resumen": resumen.read_text(encoding="utf-8").strip() if a.id and resumen.exists() else "",
            "canal": canal.get("handle", ""), "marca": marca.get("marca", ""),
            "persona": marca.get("persona", {}).get("nombre", ""), "sitio": canal.get("sitio", ""),
            "redes": "\n".join(f"• {k}: {v}" for k, v in canal.get("redes", {}).items()),
        }
        desc = PLANTILLA.read_text(encoding="utf-8").format(**datos)
        desc = re.sub(r"\n{3,}", "\n\n", desc).strip() + "\n"
        (a.entrega / "descripcion_youtube.txt").write_text(desc, encoding="utf-8")
        print(f"Descripción → {a.entrega / 'descripcion_youtube.txt'} ({len(desc)} caracteres; YouTube admite 5000)")
    else:
        print(f"⚠ Falta la plantilla de descripción {PLANTILLA}: no se genera descripcion_youtube.txt")

    mini = a.miniatura or (OUT / "miniatura" / f"{a.id}_miniatura.jpg" if a.id else None)
    if mini and mini.exists():
        shutil.copy2(mini, a.entrega / f"miniatura{mini.suffix}")
        print(f"Miniatura → {a.entrega / ('miniatura' + mini.suffix)}")
    elif a.miniatura:
        print(f"⚠ No existe la miniatura {a.miniatura}")


if __name__ == "__main__":
    main()
