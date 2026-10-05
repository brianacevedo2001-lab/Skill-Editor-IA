"""Shorts verticales (1080×1920) a partir de las partes ya editadas: YouTube Shorts (con música),
Instagram Reels y TikTok (sin música; el usuario la añade al publicar).

Uso:
  python pipeline/09_shorts.py frases <id> <parte>          # frases con tiempos, para elegir fragmentos
  python pipeline/09_shorts.py <id> [nombre…] [--sin-render] [--sin-drive]

Lee videos/<id>/shorts.json:
  {
    "musica": {"src": "_shared/music/jazz_a_night_alone.m4a", "volumen": 0.13},   ← solo la versión de YouTube
    "cierre": "Video completo en YouTube",
    "shorts": [{
      "nombre": "3-minutos", "parte": "intro",            ← intro | disclaimer | grueso (del mismo <id> o "parte": "prueba01/intro")
      "tramos": [[0, 13.4], [17.2, 27.6]],                 ← segundos de la parte YA cortada; varios = salto de corte
      "gancho": ["3 MINUTOS", "y tu cliente se fue"],      ← texto grande de los primeros segundos
      "layout": "camara",                                  ← camara (defecto en intro) | dividido (defecto en grueso)
      "recorte": [x, y, ancho],                            ← opcional, zona de la pantalla (px de la grabación) en dividido
      "focoCamara": [0.46, 0.56],                          ← (también global) dónde está la cara en la cámara del grueso
      "escenas": [ … callouts con tiempos del short … ],   ← además se importan los callouts de la parte
      "titulo": "…", "descripcion": "…", "hashtags": ["#ventas", …],
      "textos": {"youtube": {"titulo": "…", "texto": "…"}, "instagram": {"texto": "…"},   ← un texto DISTINTO por red
                 "tiktok": {"texto": "…"}, "linkedin": {"texto": "…"}},
      "linkedin": true                                     ← también el vídeo 4:5 para LinkedIn (sin música)
    }]
  Un vertical grabado aparte: procésalo como la intro (02 → 03 → 01) en videos/<id>/vertical.mp4, escribe
  videos/<id>/vertical.json (misma forma que intro.json, con sus escenas) y usa "parte": "vertical" con un tramo
  que cubra todo el vídeo.
  }

Por cada short: recorta los tramos (cámara, pantalla y voz), traslada palabras/cortes/callouts al tiempo
del short, escribe videos/<id>/shorts/<nombre>/short.json, renderiza la composición Short de Remotion
(voz + efectos) y exporta tres versiones a −14 LUFS en out/entregas/<id>/shorts/ (+ portada y textos).
Siempre se copia a Drive (final/<id>/shorts/) salvo --sin-drive.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from comun import (FPS, MARCA, OUT, RAIZ, VIDEOS, contar_fotogramas, copiar_reanudable, duracion, escribir_json,
                   ffmpeg, ffprobe_json, leer_json)

OBJ_I, OBJ_TP = -14.0, -1.5
PLATAFORMAS = {"youtube": True, "instagram": False, "tiktok": False}   # ¿lleva música?
ANCHO_PANTALLA = 1150            # px de la grabación de pantalla que caben en el short (texto legible)


# ───────────────────────── fuentes ─────────────────────────
def cargar_parte(id_: str, parte: str) -> dict:
    """Devuelve rutas y datos de una parte editada. parte = "intro" o "<otro_id>/intro"."""
    if "/" in parte:
        id_, parte = parte.split("/", 1)
    g = leer_json(VIDEOS / id_ / f"{parte}.json")
    d = {"id": id_, "parte": parte, "guion": g,
         "palabras": leer_json(VIDEOS / g["palabras"]) if g.get("palabras") else [],
         "cuts": leer_json(VIDEOS / g["cuts"]) if g.get("cuts") else None}
    if isinstance(d["palabras"], dict):
        d["palabras"] = d["palabras"].get("palabras", [])
    if parte == "grueso":
        d.update(camara=VIDEOS / g["camara"], pantalla=VIDEOS / g["pantalla"], voz=VIDEOS / g["pantalla"])
    else:
        d.update(camara=VIDEOS / g["video"], pantalla=None, voz=VIDEOS / g["video"])
    return d


def frases(id_: str, parte: str) -> None:
    d = cargar_parte(id_, parte)
    linea, t0 = [], None
    for w in d["palabras"]:
        if t0 is None:
            t0 = w["inicio"]
        linea.append(w["w"].strip())
        if re.search(r"[.?!]$", w["w"].strip()) or w is d["palabras"][-1]:
            print(f"{t0:7.2f}–{w['fin']:7.2f}  {' '.join(linea)}")
            linea, t0 = [], None


# ───────────────────────── traslado al tiempo del short ─────────────────────────
def mapa(tramos: list[list[float]]):
    """t de la parte → t del short (None si cae fuera de los tramos)."""
    offs, acum = [], 0.0
    for a, b in tramos:
        offs.append((a, b, acum))
        acum += b - a

    def m(t: float, tol: float = 0.0):
        for a, b, o in offs:
            if a - tol <= t <= b + tol:
                return o + min(max(t, a), b) - a
        return None
    return m, acum, [o for _, _, o in offs[1:]]


IMPORTABLES = {"callout", "orbOpen", "lineup", "revealStat", "rise", "orbChips", "dissolve", "outro", "bars", "broll",
               "notificacion", "buscador", "pasos", "comentario"}


def trasladar(obj, m, defecto: float):
    """Copia una escena pasando al tiempo del short toda clave de tiempo: at, *At y listas *At."""
    if isinstance(obj, dict):
        res = {}
        for k, v in obj.items():
            if (k == "at" or k.endswith("At")) and isinstance(v, (int, float)):
                res[k] = round(m(v, 0.3) if m(v, 0.3) is not None else defecto, 3)
            elif k.endswith("At") and isinstance(v, list):
                res[k] = [round(m(x, 0.3) if m(x, 0.3) is not None else defecto, 3) for x in v]
            else:
                res[k] = trasladar(v, m, defecto)
        return res
    if isinstance(obj, list):
        return [trasladar(x, m, defecto) for x in obj]
    return obj


def reflujo(lineas: list[str], maximo: int = 17) -> list[str]:
    """Reparte las palabras de un callout en líneas cortas para el vertical (respeta *acentos*)."""
    palabras = " ".join(lineas).split()
    res, actual = [], ""
    for p in palabras:
        limpio = actual.replace("*", "")
        if actual and len(limpio) + 1 + len(p.replace("*", "")) > maximo:
            res.append(actual)
            actual = p
        else:
            actual = f"{actual} {p}".strip()
    if actual:
        res.append(actual)
    # Un *acento* partido entre líneas pierde los asteriscos: se cierran/abren en el salto.
    arreglo, abierto = [], False
    for l in res:
        if abierto:
            l = "*" + l
        abierto = l.count("*") % 2 == 1
        arreglo.append(l + ("*" if abierto else ""))
    return arreglo


# ───────────────────────── recorte de material ─────────────────────────
def filtro_tramos(tramos, etiqueta: str, tipo: str) -> tuple[str, str]:
    partes, nombres = [], []
    for k, (a, b) in enumerate(tramos):
        n = f"{etiqueta}{k}"
        if tipo == "v":
            partes.append(f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[{n}]")
        else:
            partes.append(f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[{n}]")
        nombres.append(f"[{n}]")
    v, a_ = (1, 0) if tipo == "v" else (0, 1)
    return ";".join(partes) + f";{''.join(nombres)}concat=n={len(tramos)}:v={v}:a={a_}", nombres


def recortar_video(src: Path, tramos, salida: Path, extra: str = "") -> None:
    g, _ = filtro_tramos(tramos, "v", "v")
    g += f"[c];[c]fps={FPS}{',' + extra if extra else ''},format=yuv420p[out]"
    ffmpeg("-i", str(src), "-filter_complex", g, "-map", "[out]", "-an", "-c:v", "h264_nvenc", "-preset", "p5",
           "-rc", "vbr", "-cq", "18", "-b:v", "0", str(salida))


def recortar_audio(src: Path, tramos, salida: Path, cola: float = 0.0) -> None:
    g, _ = filtro_tramos(tramos, "a", "a")
    g += f"[c];[c]apad=pad_dur={cola:.3f}[out]" if cola else "[out]"
    ffmpeg("-i", str(src), "-filter_complex", g, "-map", "[out]", "-ar", "48000", "-ac", "2", str(salida))


def zona_pantalla(d: dict, tramos, recorte) -> tuple[int, int, int, int]:
    v = next(s for s in ffprobe_json(d["pantalla"])["streams"] if s["codec_type"] == "video")
    W, H = int(v["width"]), int(v["height"])
    if recorte:
        x, y, w = recorte
    else:
        # centro: media de los zooms del grueso que caen en los tramos (ponderada por solape)
        suma, peso = [0.0, 0.0], 0.0
        for z in d["guion"].get("zooms", []):
            for a, b in tramos:
                s = max(0.0, min(b, z["to"]) - max(a, z["from"]))
                suma[0] += z["x"] * s; suma[1] += z["y"] * s; peso += s
        cx, cy = (suma[0] / peso, suma[1] / peso) if peso else (0.5, 0.45)
        w = ANCHO_PANTALLA
        x, y = cx * W - w / 2, cy * H - w * 1000 / 1080 / 2
    h = round(w * 1000 / 1080)
    x = int(min(max(x, 0), W - w)); y = int(min(max(y, 0), H - h))
    return x, y, int(w), int(h)


def preparar(id_: str, s: dict, cierre_defecto: str, foco_camara: list[float]) -> tuple[Path, float]:
    d = cargar_parte(id_, s["parte"])
    tramos = s["tramos"]
    m, dur, juntas = mapa(tramos)
    carpeta = VIDEOS / id_ / "shorts" / s["nombre"]
    carpeta.mkdir(parents=True, exist_ok=True)
    layout = s.get("layout") or ("dividido" if d["parte"] == "grueso" else "camara")

    # "cola": segundos extra al final (cámara congelada, sin voz) para un cierre de marca tras la última palabra
    cola = float(s.get("cola", 0))
    tpad = f"tpad=stop_mode=clone:stop_duration={cola:.3f}" if cola else ""
    print(f"  recortando {len(tramos)} tramo(s), {dur:.1f} s ({layout}){f' + cola {cola:.1f} s' if cola else ''}…")
    if layout == "dividido":
        # La franja de cámara (1080×920) cae en la zona que tapan las apps abajo: se recorta alrededor de la
        # cara y se deja la cara en el tercio superior de la franja (prueba02: si no, quedaba a la altura
        # de la descripción de TikTok).
        fx, fy = s.get("focoCamara", foco_camara)
        cw, ch = 800, round(800 * 920 / 1080)
        v = next(x for x in ffprobe_json(d["camara"])["streams"] if x["codec_type"] == "video")
        CW, CH = int(v["width"]), int(v["height"])
        cx = int(min(max(fx * CW - cw / 2, 0), CW - cw)); cy = int(min(max(fy * CH - 0.33 * ch, 0), CH - ch))
        recortar_video(d["camara"], tramos, carpeta / "camara.mp4",
                       f"crop={cw}:{ch}:{cx}:{cy},scale=1080:920:flags=lanczos" + (f",{tpad}" if tpad else ""))
    else:
        recortar_video(d["camara"], tramos, carpeta / "camara.mp4", tpad)
    recortar_audio(d["voz"], tramos, carpeta / "voz.wav", cola)
    if layout == "dividido":
        x, y, w, h = zona_pantalla(d, tramos, s.get("recorte"))
        recortar_video(d["pantalla"], tramos, carpeta / "pantalla.mp4",
                       f"crop={w}:{h}:{x}:{y},scale=1080:1000:flags=lanczos" + (f",{tpad}" if tpad else ""))
        print(f"  pantalla: zona {w}×{h} en ({x}, {y})")

    palabras = []
    for p in d["palabras"]:
        t0 = m(p["inicio"])
        if t0 is None:
            continue
        palabras.append({"w": p["w"], "inicio": round(t0, 3), "fin": round(m(p["fin"], 0.3) or t0 + 0.2, 3)})

    cortes = list(juntas)
    for seg in (d["cuts"] or {}).get("segmentos", [])[1:]:
        t = m(seg["cut"][0])
        if t is not None and 0.5 < t < dur - 0.5:
            cortes.append(round(t, 3))

    escenas = []
    if s.get("importarEscenas", s.get("importarCallouts", True)):
        for e in d["guion"].get("escenas", []):
            if e.get("type") not in IMPORTABLES:
                continue
            # tolerancia de 1 s: una escena que empieza/acaba un poco fuera del tramo se recorta al tramo
            a, b = m(e["from"], 1.0), m(e["to"], 1.0)
            if a is None or b is None or b - a < 0.8:
                continue
            nuevo = trasladar(e, m, a)
            nuevo["from"], nuevo["to"] = round(a, 3), round(b, 3)
            if e["type"] == "callout":
                nuevo["lines"] = reflujo(e["lines"])
            escenas.append(nuevo)
    escenas += s.get("escenas", [])
    gancho_hasta = float(s.get("gancho_hasta", 2.8))
    # El gancho no se pisa con un callout importado del principio.
    if s.get("gancho"):
        escenas = [e for e in escenas if e["from"] >= gancho_hasta - 0.2]

    foco = d["guion"].get("camara", {}).get("foco", [0.5, 0.4]) if d["parte"] != "grueso" else [0.5, 0.42]
    guion = {
        "layout": layout,
        "camara": (carpeta / "camara.mp4").relative_to(VIDEOS).as_posix(),
        "voz": (carpeta / "voz.wav").relative_to(VIDEOS).as_posix(),
        "fotogramas": contar_fotogramas(carpeta / "camara.mp4"),
        "posicion": [foco[0], 0.5] if layout == "camara" else [0.5, 0.5], "foco": foco, "punchIn": 0.09,
        "cortes": sorted(cortes), "palabras": palabras, "escenas": escenas,
        "autoLogos": s.get("autoLogos", True),
        "fondo": s.get("fondo", d["guion"].get("fondo", "profundidad")),
    }
    if layout == "dividido":
        guion["pantalla"] = (carpeta / "pantalla.mp4").relative_to(VIDEOS).as_posix()
    if s.get("gancho"):
        # En un vertical grabado la cara queda arriba: el gancho va a la altura del pecho para no tapar los ojos.
        guion["gancho"] = {"lineas": s["gancho"], "hasta": gancho_hasta,
                           "posicion": s.get("gancho_posicion", "abajo" if d["parte"] == "vertical" else "arriba")}
    dur += cola
    texto_cierre = s.get("cierre", cierre_defecto)
    if texto_cierre:
        guion["cierre"] = {"texto": texto_cierre, "desde": round(max(dur - 2.6, 0), 2)}
    escribir_json(carpeta / "short.json", guion)
    return carpeta, dur


# ───────────────────────── render y exportación ─────────────────────────
def render(carpeta: Path, salida: Path, composicion: str = "Short", portada: bool = True) -> None:
    """Short = 1080×1920; Linkedin = la misma edición en 4:5 (1080×1350)."""
    props = f"--props={{\"guion\":\"{(carpeta / 'short.json').relative_to(VIDEOS).as_posix()}\"}}"
    base = ["npx", "remotion"]
    cmds = [base + ["render", "src/index.ts", composicion, str(salida), props,
                    "--hardware-acceleration=if-possible", "--timeout=180000", "--log=error"]]
    if portada:
        cmds.append(base + ["still", "src/index.ts", composicion, str(salida.with_name("portada.jpg")), props, "--frame=40",
                            "--image-format=jpeg", "--jpeg-quality=92", "--timeout=180000", "--log=error"])
    for cmd in cmds:
        r = subprocess.run(cmd, cwd=RAIZ / "remotion", shell=True, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode:
            sys.exit(f"Remotion falló:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")


def exportar(base: Path, salida: Path, musica: dict | None, voz: Path | None = None) -> str:
    dur = duracion(base)
    entradas = ["-i", str(base)]
    # El mp4 de Remotion trae el priming del AAC como audio: la voz llega ~45 ms tarde. Se mide contra la voz del
    # short y se recorta (apad mantiene la duración).
    voz_a = "[0:a]"
    if voz and voz.exists():
        from verificar_sync import desfase_voz
        lag, corr = desfase_voz(base, voz)
        if 0 < lag <= 0.2 and corr > 0.3:
            voz_a = f"[0:a]atrim=start={lag:.3f},asetpts=PTS-STARTPTS,apad=whole_dur={dur:.3f}[v0];[v0]"
    if musica:
        entradas += ["-ss", str(musica.get("desde", 0)), "-stream_loop", "-1", "-i", str(VIDEOS / musica["src"])]
        mezcla = (f"[1:a]atrim=0:{dur:.3f},volume={musica.get('volumen', 0.13)},afade=t=in:d=1,"
                  f"afade=t=out:st={max(dur - 1.5, 0):.3f}:d=1.5[m];{voz_a}[m]amix=inputs=2:duration=first:normalize=0")
    else:
        mezcla = f"{voz_a}anull"
    r = ffmpeg(*entradas, "-filter_complex", f"{mezcla},loudnorm=I={OBJ_I}:TP={OBJ_TP}:print_format=json[a]",
               "-map", "[a]", "-f", "null", "-", silencioso=False)
    med = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    gan = OBJ_I - float(med["input_i"])
    lim = (f",alimiter=limit={10 ** ((OBJ_TP - 0.5) / 20):.4f}:attack=5:release=80:level=false"
           if float(med["input_tp"]) + gan > OBJ_TP else "")
    ffmpeg(*entradas, "-filter_complex", f"{mezcla},volume={gan:.2f}dB{lim},aresample=48000[a]",
           "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart",
           "-shortest", str(salida))
    r = ffmpeg("-i", str(salida), "-vn", "-af", "ebur128", "-f", "null", "-", silencioso=False)
    return re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)[-1]


def textos(s: dict, canal: dict) -> str:
    """Si el short trae "textos" por red ({youtube|instagram|tiktok|linkedin: {titulo?, texto}}), se usan tal cual
    (un texto distinto para cada red); si no, se arman desde titulo/descripcion/hashtags."""
    propios = s.get("textos")
    if propios:
        nombres = {"youtube": "YouTube Shorts (con música)", "instagram": "Instagram Reels (añade la música en la app)",
                   "tiktok": "TikTok (añade la música al publicar)", "linkedin": "LinkedIn (vídeo 4:5)"}
        bloques = []
        for red, t in propios.items():
            cab = f"══ {nombres.get(red, red)} ══"
            bloques.append(f"{cab}\n" + (f"Título: {t['titulo']}\n\n" if t.get("titulo") else "") + t.get("texto", "").strip())
        return "\n\n".join(bloques) + "\n"
    tags = " ".join(s.get("hashtags", []))
    desc = s.get("descripcion", "").strip()
    yt_canal = canal.get("redes", {}).get("YouTube", "")
    return (f"══ YouTube Shorts ══\nTítulo: {s.get('titulo', '')}\n\n{desc}\n\n▶ Video completo: {yt_canal}\n{tags} #Shorts\n\n"
            f"══ Instagram Reels ══ (añade la música en la app)\n{desc}\n\n🔗 Video completo en YouTube ({canal.get('handle', '')}) "
            f"· link en la bio\n{tags}\n\n"
            f"══ TikTok ══ (añade la música al publicar)\n{s.get('titulo', '')} {desc}\n{tags}\n")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "frases":
        return frases(sys.argv[2], sys.argv[3])
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("id")
    p.add_argument("nombres", nargs="*")
    p.add_argument("--sin-render", action="store_true", help="solo prepara material y short.json")
    p.add_argument("--sin-drive", action="store_true")
    a = p.parse_args()

    cfg = leer_json(VIDEOS / a.id / "shorts.json")
    canal = leer_json(MARCA / "canal.json")
    entrega = OUT / "entregas" / a.id / "shorts"
    entrega.mkdir(parents=True, exist_ok=True)
    hechos, li_hechos = [], []
    for s in cfg["shorts"]:
        if a.nombres and s["nombre"] not in a.nombres:
            continue
        print(f"▶ {s['nombre']}")
        carpeta, dur = preparar(a.id, s, cfg.get("cierre", ""), cfg.get("focoCamara", [0.46, 0.56]))
        if dur > 60:
            print(f"  ⚠ dura {dur:.0f} s: por encima de 60 s rinde peor en Shorts/Reels/TikTok")
        if a.sin_render:
            continue
        base = OUT / "shorts" / a.id / s["nombre"] / "base.mp4"
        base.parent.mkdir(parents=True, exist_ok=True)
        print("  render Remotion…")
        render(carpeta, base)
        for plat, con_musica in PLATAFORMAS.items():
            sal = entrega / f"{a.id}_{s['nombre']}_{plat}.mp4"
            lufs = exportar(base, sal, cfg.get("musica") if con_musica else None, carpeta / "voz.wav")
            print(f"  ✔ {sal.name}: {contar_fotogramas(sal)} fotogramas · {lufs} LUFS"
                  f"{' · con música' if con_musica else ' · sin música'}")
        if s.get("linkedin", True):
            print("  render LinkedIn 4:5…")
            base_li = base.with_name("base_linkedin.mp4")
            render(carpeta, base_li, "Linkedin", portada=False)
            dest_li = OUT / "entregas" / a.id / "linkedin"
            dest_li.mkdir(parents=True, exist_ok=True)
            sal = dest_li / f"{a.id}_{s['nombre']}_linkedin.mp4"
            lufs = exportar(base_li, sal, None, carpeta / "voz.wav")
            print(f"  ✔ {sal.name}: {contar_fotogramas(sal)} fotogramas · {lufs} LUFS · sin música")
            li_hechos.append(sal)
        portada = entrega / f"{a.id}_{s['nombre']}_portada.jpg"
        base.with_name("portada.jpg").replace(portada)
        (entrega / f"{a.id}_{s['nombre']}_textos.txt").write_text(textos(s, canal), encoding="utf-8")
        hechos.append(s["nombre"])

    if hechos and not a.sin_drive:
        destino = Path(leer_json(MARCA / "proyecto.json")["entregas"]["carpetaLocalDrive"]) / a.id / "shorts"
        for f in sorted(x for x in entrega.iterdir() if x.is_file()):
            copiar_reanudable(f, destino / f.name)
        for f in li_hechos:
            copiar_reanudable(f, destino.parent / "linkedin" / f.name)
        print(f"Copiado a {destino}" + (f" y {destino.parent / 'linkedin'}" if li_hechos else ""))


if __name__ == "__main__":
    main()
