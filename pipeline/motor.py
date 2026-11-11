"""Motor de render: un solo punto que despacha cada composición a Remotion o a HyperFrames.

Cómo se elige el motor (gana el primero que esté definido):
  1. --motor remotion|hyperframes en el script que renderiza (anuncio.py, 09_shorts.py, 10_linkedin.py, motor.py)
  2. "motor" en el guion de la pieza (videos/<id>/anuncio.json, shorts.json, linkedin.json, miniatura.json, escenas.json)
  3. "motor" en marca/proyecto.json
  4. "remotion" (por defecto: lo que ya funcionaba sigue igual)

Uso directo:
  python pipeline/motor.py cual [<id>/<guion>.json] [--motor m]          # qué motor se usaría y por qué
  python pipeline/motor.py video <Composición> <id>/<guion>.json <salida.mp4|.mov> [--motor m] [--portada seg]
  python pipeline/motor.py still <Composición> <id>/<guion>.json <salida.jpg|.png> [--motor m]
  python pipeline/motor.py proyecto <Composición> <id>/<guion>.json      # solo arma el proyecto de HyperFrames
Composiciones: Escenas (16:9) y EscenasVertical (9:16) — solo HyperFrames —, Short, Linkedin, Anuncio, AnuncioLinkedin,
Miniatura y Lamina. Las láminas del carrusel van por pipeline/10_linkedin.py.

HyperFrames (https://hyperframes.heygen.com): cada render copia la plantilla hyperframes/<plantilla>/ a
out/hyperframes/<trabajo>/ (un proyecto normal: `npx hyperframes check|preview|snapshot` funcionan ahí), escribe
assets/datos.js con la marca (marca/*.json) y el guion, copia fuentes, logos y medios a assets/ y renderiza con
`npx hyperframes render`. Todo MP4 de HyperFrames pasa por comun.portada() (el cuadro 0 nunca queda negro).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from comun import FPS, MARCA, OUT, RAIZ, VIDEOS, duracion as duracion_de, leer_json, portada

MOTORES = ("remotion", "hyperframes")
POR_DEFECTO = "remotion"
REMOTION = RAIZ / "remotion"
PLANTILLAS = RAIZ / "hyperframes"
TRABAJOS = OUT / "hyperframes"
CACHE_FUENTES = TRABAJOS / "_fuentes"

# Composición → (plantilla de hyperframes/, ancho, alto). Mismos nombres y tamaños que remotion/src/Root.tsx.
COMPOSICIONES = {
    "Escenas": ("escenas", 1920, 1080), "EscenasVertical": ("escenas", 1080, 1920),
    "Short": ("subtitulos", 1080, 1920), "Linkedin": ("subtitulos", 1080, 1350),
    "Anuncio": ("anuncio", 1080, 1920), "AnuncioLinkedin": ("anuncio", 1080, 1350),
    "Miniatura": ("miniatura", 1920, 1080), "Lamina": ("lamina", 1080, 1350),
}
SOLO_HYPERFRAMES = {"Escenas", "EscenasVertical"}

# Escenas con plantilla en hyperframes/comun/hf.js (con los nombres de Remotion como alias).
TIPOS_HF = {"titulo", "callout", "lowerThird", "tarjetas", "lineup", "dato", "revealStat", "barras", "bars",
            "apertura", "chat", "remate", "final", "outro", "pildoras"}


# ───────────────────────── elección ─────────────────────────
def elegir(guion: dict | None = None, forzado: str | None = None, explicar: bool = False):
    """Motor para una pieza: --motor > guion["motor"] > proyecto.json["motor"] > remotion."""
    proyecto = leer_json(MARCA / "proyecto.json")
    for origen, valor in (("--motor", forzado), ("guion", (guion or {}).get("motor")), ("marca/proyecto.json", proyecto.get("motor"))):
        if valor:
            v = str(valor).strip().lower()
            if v not in MOTORES:
                raise SystemExit(f"Motor desconocido «{valor}» ({origen}): usa {' | '.join(MOTORES)}")
            return (v, origen) if explicar else v
    return (POR_DEFECTO, "por defecto") if explicar else POR_DEFECTO


def argumento(p: argparse.ArgumentParser) -> None:
    p.add_argument("--motor", choices=MOTORES, help="fuerza el motor de render (si no: guion › proyecto.json › remotion)")


def _props(guion_rel: str) -> str:
    return f"--props={{\"guion\":\"{guion_rel}\"}}"


# ───────────────────────── Remotion (sin cambios de comportamiento) ─────────────────────────
def _remotion(args: list[str], intentos: int = 1, silencioso: bool = False, etiqueta: str | None = None) -> None:
    cmd = ["npx", "remotion", *args]
    r = None
    for intento in range(intentos):
        if etiqueta:
            print(f"  {etiqueta}…{f' (reintento {intento})' if intento else ''}", flush=True)
        r = subprocess.run(cmd, cwd=REMOTION, shell=sys.platform == "win32", capture_output=silencioso,
                           text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            return
    if silencioso:
        sys.exit(f"Remotion falló:\n{(r.stdout or '')[-2000:]}\n{(r.stderr or '')[-2000:]}")
    raise SystemExit(f"El render de {etiqueta or args[2]} falló {intentos} {'vez' if intentos == 1 else 'veces'}")


# ───────────────────────── API para el pipeline ─────────────────────────
def render_video(comp: str, guion_rel: str, salida: Path, motor: str | None = None, *, remotion_extra=(),
                 intentos: int = 1, silencioso: bool = False, portada_t: float | None = None,
                 portada_jpg: Path | None = None) -> Path:
    """Renderiza una composición a vídeo con el motor elegido."""
    salida = Path(salida).resolve()   # Remotion corre con cwd=remotion/: nada de rutas relativas
    salida.parent.mkdir(parents=True, exist_ok=True)
    m = motor or elegir(leer_json(VIDEOS / guion_rel))
    if m == "hyperframes":
        return hf_video(comp, guion_rel, salida, portada_t=portada_t, portada_jpg=portada_jpg)
    if comp in SOLO_HYPERFRAMES:
        raise SystemExit(f"{comp} solo existe en HyperFrames (en Remotion las escenas van dentro de Intro/Parte/Short)")
    _remotion(["render", "src/index.ts", comp, str(salida), _props(guion_rel), *remotion_extra], intentos, silencioso,
              comp if intentos > 1 else None)
    return salida


def render_still(comp: str, guion_rel: str, salida: Path, motor: str | None = None, *, remotion_extra=(),
                 silencioso: bool = False, escala: float = 1.0) -> Path:
    """Cuadro fijo (miniatura, lámina suelta…) con el motor elegido."""
    salida = Path(salida).resolve()   # Remotion corre con cwd=remotion/: nada de rutas relativas
    salida.parent.mkdir(parents=True, exist_ok=True)
    m = motor or elegir(leer_json(VIDEOS / guion_rel))
    if m == "hyperframes":
        proyecto = construir(comp, guion_rel)
        _snapshots(proyecto, [0.0], [salida], escala)
        return salida
    _remotion(["still", "src/index.ts", comp, str(salida), _props(guion_rel), *remotion_extra], 1, silencioso)
    return salida


def render_laminas(guion_rel: str, carpeta: Path, motor: str | None = None) -> None:
    """Láminas de LinkedIn: lamina_01.png… e imagen.png (la imagen suelta) en `carpeta`."""
    carpeta = Path(carpeta).resolve()
    carpeta.mkdir(parents=True, exist_ok=True)
    m = motor or elegir(leer_json(VIDEOS / guion_rel))
    if m == "hyperframes":
        proyecto = construir("Lamina", guion_rel)
        n = len(leer_json(VIDEOS / guion_rel)["carrusel"])
        nombres = [carpeta / f"lamina_{i + 1:02d}.png" for i in range(n)] + [carpeta / "imagen.png"]
        _snapshots(proyecto, [i + 0.5 for i in range(n + 1)], nombres)
        for x in nombres:
            print(f"✔ {x.name}")
        return
    r = subprocess.run(["node", "scripts/laminas.mjs", guion_rel, str(carpeta)], cwd=REMOTION, shell=True,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        sys.exit(f"Remotion falló:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")


# ───────────────────────── HyperFrames: CLI ─────────────────────────
def _hf(args: list[str], capturar: bool = False) -> subprocess.CompletedProcess:
    """npx hyperframes … (en Windows por la shell: npx es npx.cmd)."""
    env = {**os.environ, "HYPERFRAMES_NO_UPDATE_CHECK": "1"}
    r = subprocess.run(["npx", "hyperframes", *args], shell=sys.platform == "win32", env=env, capture_output=capturar,
                       text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        detalle = f"\n{(r.stdout or '')[-2500:]}\n{(r.stderr or '')[-2500:]}" if capturar else ""
        sys.exit(f"HyperFrames falló: npx hyperframes {' '.join(args[:2])}…{detalle}")
    return r


def hf_video(comp: str, guion_rel: str, salida: Path, portada_t: float | None = None,
             portada_jpg: Path | None = None) -> Path:
    proyecto = construir(comp, guion_rel)
    salida = Path(salida)
    args = ["render", str(proyecto), "-o", str(salida), "--fps", str(FPS)]
    if salida.suffix.lower() == ".mov":
        args += ["--format", "mov"]
    if os.environ.get("HF_WORKERS"):
        args += ["--workers", os.environ["HF_WORKERS"]]
    print(f"  HyperFrames: {comp} → {salida.name}", flush=True)
    _hf(args)
    if not salida.exists() or salida.stat().st_size == 0:
        sys.exit(f"HyperFrames no escribió {salida}")
    if salida.suffix.lower() == ".mp4":
        datos = leer_json(VIDEOS / guion_rel)
        t = portada_t if portada_t is not None else datos.get("portada", min(1.5, duracion_de(salida) / 2))
        portada(salida, float(t), portada_jpg)
    return salida


def _snapshots(proyecto: Path, tiempos: list[float], salidas: list[Path], escala: float = 1.0) -> None:
    """Un cuadro por tiempo con `hyperframes snapshot` → PNG del tamaño del lienzo → salida (jpg/png, con escala)."""
    from PIL import Image
    tmp = proyecto / ".hyperframes" / "cuadros"
    if tmp.exists():
        shutil.rmtree(tmp)
    r = _hf(["snapshot", str(proyecto), "--at", ",".join(f"{t:g}" for t in tiempos), "--no-end", "-o", str(tmp), "--json"],
            capturar=True)
    pngs = _rutas_snapshot(r.stdout, tmp)
    if len(pngs) != len(salidas):
        sys.exit(f"snapshot devolvió {len(pngs)} cuadros y se esperaban {len(salidas)}:\n{r.stdout[-1500:]}")
    for png, sal in zip(pngs, salidas):
        sal = Path(sal)
        sal.parent.mkdir(parents=True, exist_ok=True)
        img = Image.open(png).convert("RGB")
        if escala != 1.0:
            img = img.resize((round(img.width * escala), round(img.height * escala)), Image.LANCZOS)
        if sal.suffix.lower() in (".jpg", ".jpeg"):
            img.save(sal, quality=92)
        else:
            img.save(sal)


def _rutas_snapshot(stdout: str, carpeta: Path) -> list[Path]:
    """Rutas de los PNG en el orden de --at (del JSON de snapshot; si no se puede leer, por nombre)."""
    try:
        datos = json.loads(stdout[stdout.index("{"):stdout.rindex("}") + 1])
        rutas = [p for p in _buscar_png(datos)]
        if rutas:
            return [Path(p) if Path(p).is_absolute() else carpeta / Path(p).name for p in rutas]
    except ValueError:
        pass
    clave = lambda p: float(re.findall(r"[\d.]+", p.stem.replace("at-", ""))[0] or 0)
    return sorted(carpeta.glob("*.png"), key=clave)


def _buscar_png(x):
    if isinstance(x, dict):
        for k in ("frames", "snapshots", "stills", "paths", "files"):
            if k in x and isinstance(x[k], list):
                encontrados = [v if isinstance(v, str) else v.get("path") or v.get("file") for v in x[k]]
                return [p for p in encontrados if p and str(p).endswith(".png")]
        for v in x.values():
            r = _buscar_png(v)
            if r:
                return r
    return []


# ───────────────────────── HyperFrames: armar el proyecto ─────────────────────────
class Trabajo:
    """Carpeta out/hyperframes/<trabajo>/ con assets/ y medidas del lienzo."""

    def __init__(self, carpeta: Path, ancho: int, alto: int):
        self.dir, self.ancho, self.alto = carpeta, ancho, alto
        self.assets = carpeta / "assets"
        self.movil = alto / ancho > 1.6

    def medio(self, origen: Path, sub: str = "media") -> str:
        """Pone un archivo en assets/<sub>/ (enlace duro si se puede: los vídeos pesan) y devuelve su ruta relativa."""
        origen = Path(origen)
        if not origen.exists():
            raise SystemExit(f"No existe {origen}")
        dest = self.assets / sub / origen.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            try:
                os.link(origen, dest)
            except OSError:
                shutil.copy2(origen, dest)
        return f"assets/{sub}/{origen.name}"

    def seguras(self) -> dict:
        """Zona segura: en 9:16 las apps tapan arriba, abajo (descripción, música) y la derecha (botones)."""
        if self.movil:
            return {"arriba": 230, "abajo": 450, "izq": 70, "der": 170}
        if self.ancho < self.alto:      # 4:5
            return {"arriba": 80, "abajo": 90, "izq": 70, "der": 70}
        return {"arriba": 80, "abajo": 90, "izq": 110, "der": 110}


def construir(comp: str, guion_rel: str) -> Path:
    """Copia la plantilla de la composición a out/hyperframes/<trabajo>/ y la rellena con la marca y el guion."""
    if comp not in COMPOSICIONES:
        raise SystemExit(f"Composición desconocida para HyperFrames: {comp} ({', '.join(COMPOSICIONES)})")
    plantilla, ancho, alto = COMPOSICIONES[comp]
    g = leer_json(VIDEOS / guion_rel)
    carpeta = TRABAJOS / re.sub(r"[^\w.-]+", "_", f"{Path(guion_rel).with_suffix('').as_posix()}_{comp}")
    # Se rehace todo menos .hyperframes/ (caché y artefactos de check/snapshot). Se borran archivos, no carpetas: el
    # navegador «caliente» de `hyperframes check` (warmCheck, vive 5 min) deja las carpetas abiertas en Windows.
    for f in sorted((carpeta / "assets").rglob("*"), reverse=True) if (carpeta / "assets").exists() else []:
        try:
            f.unlink() if f.is_file() else f.rmdir()
        except OSError:
            pass
    shutil.copytree(PLANTILLAS / plantilla, carpeta, dirs_exist_ok=True)
    shutil.copytree(PLANTILLAS / "comun", carpeta / "assets" / "comun", dirs_exist_ok=True)
    t = Trabajo(carpeta, ancho, alto)

    marca, css = _marca(t)
    armar = {"escenas": _escenas, "anuncio": _anuncio, "subtitulos": _subtitulos, "miniatura": _miniatura,
             "lamina": _lamina}[plantilla]
    dur, clips, medios, datos = armar(t, g)
    datos.update(lienzo={"ancho": ancho, "alto": alto, "movil": t.movil, "u": min(ancho, alto) / 1080, "seg": t.seguras()},
                 marca=marca, duracion=round(dur, 3))
    (t.assets / "datos.js").write_text("// Escrito por pipeline/motor.py: marca + guion de la pieza.\nwindow.DATOS = "
                                       + json.dumps(datos, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    html = (carpeta / "index.html").read_text(encoding="utf-8")
    for k, v in {"__ANCHO__": str(ancho), "__ALTO__": str(alto), "__DURACION__": f"{dur:.3f}", "<!--MARCA-->": css,
                 "<!--CLIPS-->": "\n      ".join(clips), "<!--MEDIOS-->": "\n      ".join(medios)}.items():
        html = html.replace(k, v)
    (carpeta / "index.html").write_text(html, encoding="utf-8")
    (carpeta / "hyperframes.json").write_text(json.dumps({"_nota": "Generado por pipeline/motor.py desde "
                                                          f"videos/{guion_rel}; se rehace en cada render."}, ensure_ascii=False),
                                              encoding="utf-8")
    return carpeta


# ── marca: colores, tipografías y logos (marca blanca) ──
def _luminancia(hexa: str) -> float:
    h = hexa.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _marca(t: Trabajo) -> tuple[dict, str]:
    m, canal = leer_json(MARCA / "marca.json"), leer_json(MARCA / "canal.json")
    c = m["colores"]
    logos = {"soloTexto": m.get("logos", {}).get("soloTexto") or m.get("marca", "")}
    for clave, ruta in (("isotipo", m.get("logos", {}).get("isotipo")), ("logotipo", m.get("logos", {}).get("logotipo")),
                        ("avatar", canal.get("avatar"))):
        logos[clave] = None
        if ruta:
            for cand in (RAIZ / ruta, VIDEOS / "_shared" / "marca" / Path(ruta).name):
                if cand.exists():
                    logos[clave] = t.medio(cand, "marca")
                    break
    caras, familias = _fuentes(t, m.get("tipografias", {}))
    tip = m.get("tipografias", {})
    sobre = c["fondo"] if _luminancia(c["acento"]) > 0.62 else "#FFFFFF"   # texto sobre el acento: blanco salvo acentos muy claros
    seg = t.seguras()
    var = {"fondo": c["fondo"], "superficie": c["superficie"], "superficie2": c.get("superficie2", c["superficie"]),
           "borde": c["borde"], "texto": c["texto"], "texto-suave": c["textoSuave"], "acento": c["acento"],
           "acento2": c.get("acento2", c["acento"]), "brillo": c.get("brillo", c["texto"]), "etiqueta": c.get("etiqueta", c["acento"]),
           "sobre-acento": sobre, "f-titulares": familias["titulares"], "f-texto": familias["texto"], "f-mono": familias["etiquetas"],
           "estilo-titulares": tip.get("titulares", {}).get("estilo", "normal"),
           **{f"seg-{k}": f"{v}px" for k, v in seg.items()}}
    css = ("<style>\n" + caras + "\n:root {\n" + "\n".join(f"  --{k}: {v};" for k, v in var.items()) + "\n}\n</style>")
    datos = {"nombre": m.get("marca", ""), "persona": m.get("persona", {}), "colores": c, "logos": logos,
             "sitio": canal.get("sitio", ""), "handle": canal.get("handle", "")}
    return datos, css


UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def _google(familia: str, italica: bool, pesos: list[int]) -> str | None:
    """CSS de Google Fonts (woff2) para una familia; si un peso no existe, se reintenta con menos."""
    nombre = familia.replace(" ", "+")
    for ps in (pesos, pesos[:1], []):
        if italica:
            eje = f":ital,wght@{';'.join(f'1,{p}' for p in ps)}" if ps else ":ital@1"
        else:
            eje = f":wght@{';'.join(str(p) for p in ps)}" if ps else ""
        url = f"https://fonts.googleapis.com/css2?family={nombre}{eje}&display=swap"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                return r.read().decode("utf-8")
        except Exception:
            continue
    return None


def _fuentes(t: Trabajo, tip: dict) -> tuple[str, dict]:
    """@font-face de las tipografías de marca.json en assets/fonts/ (HyperFrames solo resuelve por nombre las que trae;
    el resto necesita su archivo). Google Fonts se descarga una vez a out/hyperframes/_fuentes/; "archivo" en marca.json
    sirve para una fuente propia (ruta a .woff2/.ttf/.otf)."""
    caras, familias = [], {}
    respaldo = {"titulares": "serif", "texto": "sans-serif", "etiquetas": "monospace"}
    for rol in ("titulares", "texto", "etiquetas"):
        f = tip.get(rol, {})
        familia = f.get("familia", "Inter")
        familias[rol] = f'"{familia}", {respaldo[rol]}'
        italica = f.get("estilo") == "italic"
        pesos = sorted(set(f.get("pesos") or [f.get("peso", 400)]) | ({700, 800} if rol == "texto" else set()))
        if f.get("archivo"):
            rel = t.medio(RAIZ / f["archivo"], "fonts")
            caras.append(f'@font-face {{ font-family: "{familia}"; src: url("{rel}"); font-style: {"italic" if italica else "normal"}; }}')
            continue
        if not f.get("googleFonts", True):
            continue
        slug = re.sub(r"\W+", "_", familia).lower() + ("_i" if italica else "") + "_" + "-".join(map(str, pesos))
        cache = CACHE_FUENTES / slug
        css_cache = cache / "fuentes.css"
        if not css_cache.exists():
            css = _google(familia, italica, pesos)
            if not css:
                print(f"  ⚠ no pude bajar «{familia}» de Google Fonts: se usará la fuente de respaldo")
                continue
            cache.mkdir(parents=True, exist_ok=True)
            bloques = re.findall(r"/\*\s*([\w-]+)\s*\*/\s*(@font-face\s*{[^}]*})", css)
            salida = []
            for subset, bloque in bloques:
                if subset not in ("latin", "latin-ext"):
                    continue
                url = re.search(r"url\((https://[^)]+)\)", bloque).group(1)
                estilo = re.search(r"font-style:\s*(\w+)", bloque).group(1)
                peso = re.search(r"font-weight:\s*(\d+)", bloque).group(1)
                nombre = f"{slug}_{estilo}_{peso}_{subset}.woff2"
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
                    (cache / nombre).write_bytes(r.read())
                salida.append(bloque.replace(url, nombre))
            css_cache.write_text("\n".join(salida), encoding="utf-8")
        css = css_cache.read_text(encoding="utf-8")
        for archivo in sorted(cache.glob("*.woff2")):
            t.medio(archivo, "fonts")
        caras.append(re.sub(r"url\(([^)/]+\.woff2)\)", r'url("assets/fonts/\1")', css))
    return "\n".join(caras), familias


# ── escenas comunes (escenas, anuncio y los rótulos del vertical) ──
def _normalizar(e: dict) -> dict:
    """Pasa claves de Remotion/promo a lo que entiende hf.js y avisa de lo que no tiene plantilla."""
    e = dict(e)
    tipo = e.get("tipo") or e.get("type")
    if tipo == "pildoras":                     # columnas de píldoras + frase → titular con sus tiempos
        e.update(tipo="titulo", lineas=e.get("texto", []), wordsAt=(e.get("at") or {}).get("palabras"))
    elif tipo == "listo":
        e.update(tipo="titulo", lineas=[e.get("texto", "¡Listo!")])
    elif tipo not in TIPOS_HF:
        texto = e.get("rotulo") or e.get("headline") or e.get("titulo")
        print(f"  ⚠ escena «{tipo}» ({e.get('from')}–{e.get('to')} s) sin plantilla en HyperFrames: "
              + (f"se muestra su rótulo «{texto}»" if texto else "queda vacía"))
        e.update(tipo="titulo", lineas=[texto] if texto else [])
    return e


def _logos_tarjetas(t: Trabajo, e: dict) -> None:
    indice = VIDEOS / "_shared" / "logos" / "index.json"
    if not e.get("items") or not indice.exists():
        return
    marcas = {x["slug"]: x for x in leer_json(indice).get("marcas", [])}
    for it in e["items"]:
        if it.get("logo") in marcas and (VIDEOS / marcas[it["logo"]]["archivo"]).exists():
            it["logoSrc"] = t.medio(VIDEOS / marcas[it["logo"]]["archivo"], "logos")


def _clips_escenas(t: Trabajo, escenas: list[dict], pista: int = 2) -> list[str]:
    clips = []
    for i, e in enumerate(escenas):
        _logos_tarjetas(t, e)
        a, b = float(e["from"]), float(e["to"])
        clips.append(f'<section id="e{i}" class="clip capa escena" data-escena="{i}" data-start="{a:.3f}" '
                     f'data-duration="{max(b - a, 0.05):.3f}" data-track-index="{pista}" style="z-index:{10 + i}"></section>')
        if e.get("transicion") in ("mancha", "barrido") and a > 0.3:
            clips.append(f'<div id="t{i}" class="clip capa barrido" data-transicion="{e["transicion"]}" data-start="{a - 0.3:.3f}" '
                         f'data-duration="0.6" data-x="{e.get("transicionX", 0.5)}" data-y="{e.get("transicionY", 0.5)}" '
                         f'data-color="{e.get("transicionColor", "acento")}" data-track-index="{pista + 4}" '
                         f'data-layout-ignore style="z-index:900"></div>')
    return clips


def _audio(t: Trabajo, ruta: Path, dur: float) -> str:
    """La voz como <audio> (HyperFrames mezcla el sonido aparte del vídeo); su hueco no pasa del largo del archivo."""
    d = min(dur, duracion_de(ruta))
    return (f'<audio id="voz" class="clip" src="{t.medio(ruta)}" data-start="0" data-duration="{d:.3f}" '
            f'data-track-index="20" data-volume="1"></audio>')


def _escenas(t: Trabajo, g: dict):
    escenas = [_normalizar(e) for e in g.get("escenas", [])]
    dur = float(g.get("duracion") or max((float(e["to"]) for e in escenas), default=3.0))
    medios = []
    if g.get("voz"):
        medios.append(_audio(t, VIDEOS / g["voz"], dur))
    clips = _clips_escenas(t, escenas) + medios
    return dur, clips, [], {"escenas": escenas, "transparente": g.get("fondo") == "transparente"}


def _anuncio(t: Trabajo, g: dict):
    escenas = [_normalizar(e) for e in g["escenas"]]
    dur = float(g["duracion"])
    medios = [_audio(t, VIDEOS / g["voz"], dur)]
    return dur, _clips_escenas(t, escenas), medios, {"escenas": escenas}


# ── vertical con subtítulos ──
def _limpiar(w: str) -> str:
    return re.sub(r'^[«"“(]+|[»"”),.;:…]+$', "", w.strip())


def _agrupar(palabras: list[dict]) -> list[list[dict]]:
    """Grupos de ≤ 3 palabras / ≤ 18 letras; corta en pausas ≥ 0,3 s y en fin de frase (como Short.tsx)."""
    grupos, g = [], []
    for i, p in enumerate(palabras):
        g.append(p)
        sig = palabras[i + 1] if i + 1 < len(palabras) else None
        letras = len(" ".join(_limpiar(x["w"]) for x in g))
        fin = bool(re.search(r"[.?!…,]$", p["w"].strip()))
        if not sig or len(g) >= 3 or letras >= 18 or fin or sig["inicio"] - p["fin"] >= 0.3:
            grupos.append(g)
            g = []
    return grupos


def _restar(a: float, b: float, tapados: list[tuple[float, float]]) -> list[tuple[float, float]]:
    trozos = [(a, b)]
    for x, y in tapados:
        nuevos = []
        for p, q in trozos:
            if y <= p or x >= q:
                nuevos.append((p, q))
                continue
            if x > p:
                nuevos.append((p, x))
            if y < q:
                nuevos.append((y, q))
        trozos = nuevos
    return [(p, q) for p, q in trozos if q - p >= 0.12]


def _subtitulos(t: Trabajo, g: dict):
    dur = g["fotogramas"] / FPS
    escenas_ok, ignoradas = [], []
    for e in g.get("escenas", []):
        (escenas_ok if (e.get("tipo") or e.get("type")) in TIPOS_HF else ignoradas).append(e)
    if ignoradas:
        print(f"  ⚠ HyperFrames no tiene aún estas escenas a pantalla completa del vertical (se omiten): "
              + ", ".join(sorted({e.get('type') or e.get('tipo') for e in ignoradas})) + " — usa --motor remotion si las necesitas")
    escenas = [_normalizar(e) for e in escenas_ok]
    pos = g.get("posicion") or [0.5, 0.5]
    cam = t.medio(VIDEOS / g["camara"])
    medios = []
    video = (lambda id_, src: f'<video id="{id_}" class="clip" src="{src}" muted playsinline data-start="0" '
                              f'data-duration="{dur:.3f}" data-track-index="{0 if id_ == "camara" else 1}" '
                              f'style="object-position:{pos[0] * 100:.1f}% {pos[1] * 100:.1f}%"></video>')
    if g.get("layout") == "dividido" and g.get("pantalla"):
        corte = round(t.alto * 0.52)
        medios += [f'<div id="marco-pantalla" class="marco" style="top:0;width:100%;height:{corte}px">'
                   + video("pantalla", t.medio(VIDEOS / g["pantalla"])) + "</div>",
                   f'<div id="marco-camara" class="marco" style="top:{corte}px;width:100%;height:{t.alto - corte}px">'
                   + video("camara", cam) + "</div>",
                   f'<div class="union" style="top:{corte - 2}px"></div>']
        y_sub = corte
    else:
        medios.append('<div id="marco-camara" class="marco" style="top:0;width:100%;height:100%">' + video("camara", cam) + "</div>")
        y_sub = 1420 if t.movil else t.alto - t.seguras()["abajo"] - 150
    medios.append(_audio(t, VIDEOS / g["voz"], dur))

    clips = _clips_escenas(t, escenas)
    # Sin subtítulos bajo el gancho, los rótulos ni el cierre (se pisaban abajo), como en Short.tsx.
    tapados = [(float(e["from"]) - 0.1, float(e["to"])) for e in escenas]
    if g.get("gancho"):
        tapados.append((0.0, float(g["gancho"]["hasta"])))
        clips.append(f'<div id="gancho" class="clip capa" data-start="0" data-duration="{g["gancho"]["hasta"]:.3f}" '
                     f'data-track-index="7" style="z-index:800"></div>')
    if g.get("cierre"):
        desde = float(g["cierre"]["desde"])
        tapados.append((desde - 0.1, dur + 1))
        clips.append(f'<div id="cierre" class="clip capa" data-start="{desde:.3f}" data-duration="{dur - desde:.3f}" '
                     f'data-track-index="8" style="z-index:800"></div>')
    if g.get("subtitulos", True) is not False:
        grupos = _agrupar([p for p in g.get("palabras", []) if _limpiar(p["w"])])
        sub = ['<div id="subtitulos" class="capa" data-layout-allow-overflow style="z-index:700">']
        n = 0
        for i, gr in enumerate(grupos):
            a = gr[0]["inicio"] - 0.05
            b = grupos[i + 1][0]["inicio"] - 0.05 if i + 1 < len(grupos) else gr[-1]["fin"] + 0.4
            b = min(b, dur)
            palabras = "".join(f'<span class="w" data-t="{p["inicio"]:.3f}">{_esc(_limpiar(p["w"]))}</span>' for p in gr)
            for x, y in _restar(a, b, tapados):
                sub.append(f'  <div id="g{n}" class="clip grupo" data-start="{x:.3f}" data-duration="{y - x:.3f}" '
                           f'data-track-index="5" style="top:{y_sub}px"><div class="grupo-in" style="font-size:86px">'
                           f'{palabras}</div></div>')
                n += 1
        sub.append("</div>")
        clips.append("\n".join(sub))
    datos = {"escenas": escenas, "layout": g.get("layout", "camara"), "punchIn": g.get("punchIn", 0.09),
             "foco": g.get("foco", [0.5, 0.4]), "cortes": g.get("cortes", []), "gancho": g.get("gancho"), "cierre": g.get("cierre")}
    return dur, clips, medios, datos


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ── cuadros fijos ──
def _miniatura(t: Trabajo, g: dict):
    medios = []
    if g.get("imagen"):
        medios.append(f'<img id="base" src="{t.medio(VIDEOS / g["imagen"])}" alt="">')
    return 1.0, [], medios, {"pieza": g}


def _lamina(t: Trabajo, g: dict):
    laminas = list(g["carrusel"]) + [{**(g.get("imagen") or g["carrusel"][0]), "_suelta": True}]
    clips = [f'<section id="l{i}" class="clip lamina" data-lamina="{i}" data-start="{i}" data-duration="1" '
             f'data-track-index="1"></section>' for i in range(len(laminas))]
    return float(len(laminas)), clips, [], {"laminas": laminas, "total": len(g["carrusel"])}


# ───────────────────────── línea de órdenes ─────────────────────────
def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("orden", choices=["cual", "video", "still", "proyecto"])
    p.add_argument("args", nargs="*")
    p.add_argument("--portada", type=float, help="segundo cuyo cuadro pasa a ser el cuadro 0 (HyperFrames)")
    argumento(p)
    a = p.parse_args()
    if a.orden == "cual":
        g = leer_json(VIDEOS / a.args[0]) if a.args else None
        m, origen = elegir(g, a.motor, explicar=True)
        print(f"{m}  ({origen})")
        return
    comp, guion = a.args[0], a.args[1]
    if a.orden == "proyecto":
        print(construir(comp, guion))
        return
    salida = Path(a.args[2])
    m = elegir(leer_json(VIDEOS / guion), a.motor)
    if a.orden == "video":
        render_video(comp, guion, salida, m, portada_t=a.portada,
                     remotion_extra=["--timeout=180000", "--hardware-acceleration=if-possible"])
    else:
        es_min = comp == "Miniatura"
        render_still(comp, guion, salida, m, escala=2 / 3 if es_min else 1.0,
                     remotion_extra=["--image-format=jpeg", "--jpeg-quality=92"] + (["--scale=0.6667"] if es_min else [])
                     if salida.suffix.lower() in (".jpg", ".jpeg") else (["--scale=0.6667"] if es_min else []))
    print(f"✔ {salida} ({m})")


if __name__ == "__main__":
    main()
