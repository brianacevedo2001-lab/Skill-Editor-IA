"""Brutos y entregas a través de la carpeta de Google Drive para escritorio (<DRIVE>).

Nunca se procesa vídeo dentro de <DRIVE>. Solo se COPIA (lectura/escritura lineal, reanudable):
  - brutos:   <DRIVE>/raw   → raw/<id>/
  - entregas: out/entregas/<id>/                  → <DRIVE>/final\\<id>\\

Uso:
  python pipeline/brutos.py listar
  python pipeline/brutos.py traer <id> [<archivo o subcarpeta de raw>...]
        sin archivos: si existe raw\\<id>\\ en Drive copia esa subcarpeta; si no, pregunta.
  python pipeline/brutos.py entregar <id> [archivos...]
        sin archivos: copia todo out/entregas/<id>/.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from comun import MARCA, OUT, RAW, copiar_reanudable, duracion, escribir_json, ffprobe_json, leer_json

VIDEO = (".mp4", ".mov", ".mkv", ".m4v")


def carpetas() -> tuple[Path, Path]:
    p = leer_json(MARCA / "proyecto.json")
    return Path(p["brutos"]["carpetaLocalDrive"]), Path(p["entregas"]["carpetaLocalDrive"])


def ficha(ruta: Path) -> str:
    try:
        info = ffprobe_json(ruta)
    except Exception:
        return "(sin datos: ¿aún sincronizando?)"
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), {})
    fps = v.get("avg_frame_rate", "0/1")
    n, d = (int(x) for x in fps.split("/")) if "/" in fps else (0, 1)
    return f"{float(info['format']['duration']):7.1f} s  {v.get('width', '?')}x{v.get('height', '?')}  {n / d if d else 0:5.2f} fps"


def cmd_listar(_a) -> None:
    raw_drive, _ = carpetas()
    if not raw_drive.exists():
        sys.exit(f"No encuentro {raw_drive}. ¿Está abierto Google Drive para escritorio?")
    vacio = True
    for ruta in sorted(raw_drive.rglob("*")):
        if ruta.is_file() and ruta.suffix.lower() in VIDEO:
            vacio = False
            rel = ruta.relative_to(raw_drive)
            print(f"🎞  {str(rel):<50} {ruta.stat().st_size / 1024**2:>9,.0f} MB  {ficha(ruta)}")
    if vacio:
        print(f"(no hay vídeos en {raw_drive})")


def cmd_traer(a) -> None:
    raw_drive, _ = carpetas()
    if a.archivos:
        origenes = []
        for x in a.archivos:
            r = raw_drive / x
            origenes += sorted(p for p in r.rglob("*") if p.suffix.lower() in VIDEO) if r.is_dir() else [r]
    elif (raw_drive / a.id).is_dir():
        origenes = sorted(p for p in (raw_drive / a.id).rglob("*") if p.suffix.lower() in VIDEO)
    else:
        sys.exit(f"Indica qué archivos traer (no existe la subcarpeta {raw_drive / a.id}). "
                 f"Mira `brutos.py listar`.")
    if not origenes:
        sys.exit("No hay vídeos que copiar.")

    destino = RAW / a.id
    manifiesto_ruta = destino / "origen.json"
    manifiesto = leer_json(manifiesto_ruta) if manifiesto_ruta.exists() else {}
    for src in origenes:
        if not src.exists():
            sys.exit(f"No existe {src}")
        dst = copiar_reanudable(src, destino / src.name)
        d_src, d_dst = duracion(src), duracion(dst)
        ok = abs(d_src - d_dst) < 0.05
        print(f"  {'✔' if ok else '⚠'} {dst.name}: {dst.stat().st_size / 1024**2:,.0f} MB, "
              f"{d_dst:.2f} s{'' if ok else f' (origen {d_src:.2f} s)'}")
        manifiesto[src.name] = {"origen": str(src), "bytes": dst.stat().st_size, "duracion": round(d_dst, 3)}
    escribir_json(manifiesto_ruta, manifiesto)
    print(f"Listo: {destino}")


def cmd_entregar(a) -> None:
    _, final_drive = carpetas()
    local = OUT / "entregas" / a.id
    archivos = [Path(x) for x in a.archivos] if a.archivos else sorted(p for p in local.iterdir() if p.is_file())
    if not archivos:
        sys.exit(f"No hay nada en {local}")
    for src in archivos:
        copiar_reanudable(src, final_drive / a.id / src.name)
    print(f"Copiado a {final_drive / a.id} — Google Drive lo subirá en segundo plano.")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("listar").set_defaults(fn=cmd_listar)
    s = sub.add_parser("traer"); s.add_argument("id"); s.add_argument("archivos", nargs="*"); s.set_defaults(fn=cmd_traer)
    s = sub.add_parser("entregar"); s.add_argument("id"); s.add_argument("archivos", nargs="*"); s.set_defaults(fn=cmd_entregar)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
