"""Utilidades compartidas por los scripts del pipeline.

- Rutas del proyecto y lectura de marca/*.json.
- Localiza ffmpeg/ffprobe aunque el PATH de la terminal aún no los vea.
- Registra las DLL de CUDA (cuBLAS/cuDNN instaladas por pip) para faster-whisper en Windows.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MARCA = RAIZ / "marca"
VIDEOS = RAIZ / "videos"
RAW = RAIZ / "raw"
OUT = RAIZ / "out"
SECRETS = RAIZ / "secrets"
FPS = 30

# La consola de Windows usa cp1252 por defecto: forzamos UTF-8 para tildes y «».
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def leer_json(ruta: Path | str):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def escribir_json(ruta: Path | str, datos) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def _buscar_binario(nombre: str) -> str:
    en_path = shutil.which(nombre)
    if en_path:
        return en_path
    paquetes = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    for candidato in paquetes.glob(f"Gyan.FFmpeg*/*/bin/{nombre}.exe"):
        return str(candidato)
    raise FileNotFoundError(f"No encuentro {nombre}. Instálalo con: winget install Gyan.FFmpeg")


FFMPEG = _buscar_binario("ffmpeg")
FFPROBE = _buscar_binario("ffprobe")


def ffmpeg(*args: str, silencioso: bool = True) -> subprocess.CompletedProcess:
    cmd = [FFMPEG, "-hide_banner", "-y"]
    if silencioso:
        cmd += ["-loglevel", "error"]
    cmd += list(args)
    return subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")


def ffprobe_json(ruta: Path | str) -> dict:
    r = subprocess.run(
        [FFPROBE, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(ruta)],
        check=True, capture_output=True, text=True, encoding="utf-8",
    )
    return json.loads(r.stdout)


def duracion(ruta: Path | str) -> float:
    return float(ffprobe_json(ruta)["format"]["duration"])


def contar_fotogramas(ruta: Path | str) -> int:
    """Cuenta fotogramas reales del primer stream de vídeo (lento pero exacto)."""
    r = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "v:0", "-count_packets",
         "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(ruta)],
        check=True, capture_output=True, text=True,
    )
    return int(r.stdout.strip().split(",")[0])


def copiar_reanudable(origen: Path | str, destino: Path | str, trozo: int = 16 * 1024 * 1024) -> Path:
    """Copia secuencial por trozos a <destino>.part; si se corta, sigue donde lo dejó.

    Pensado para leer/escribir en <DRIVE> (Google Drive para escritorio): una lectura
    lineal de principio a fin es segura; lo que se cuelga es procesar el vídeo allí dentro.
    Si el destino ya existe con el mismo tamaño y no es más antiguo que el origen, no hace nada
    (si el origen se volvió a renderizar, se copia de nuevo aunque pese lo mismo).
    """
    import time
    origen, destino = Path(origen), Path(destino)
    total = origen.stat().st_size
    if (destino.exists() and destino.stat().st_size == total
            and destino.stat().st_mtime >= origen.stat().st_mtime):
        print(f"  ✔ ya estaba: {destino.name}")
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_name(destino.name + ".part")
    hecho = parcial.stat().st_size if parcial.exists() else 0
    if hecho > total:
        parcial.unlink()
        hecho = 0
    t0 = time.time()
    with open(origen, "rb") as src, open(parcial, "ab") as dst:
        src.seek(hecho)
        while hecho < total:
            bloque = src.read(min(trozo, total - hecho))
            if not bloque:
                raise IOError(f"Lectura interrumpida en {origen} ({hecho}/{total} bytes); vuelve a lanzarlo y seguirá.")
            dst.write(bloque)
            hecho += len(bloque)
            vel = hecho / max(time.time() - t0, 1e-3) / 1024 / 1024
            print(f"\r  → {destino.name}: {hecho * 100 / total:5.1f} %  "
                  f"{hecho / 1024**2:,.0f}/{total / 1024**2:,.0f} MB  {vel:5.1f} MB/s", end="", flush=True)
    print()
    if parcial.stat().st_size != total:
        raise IOError(f"Tamaño incorrecto en {parcial}")
    parcial.replace(destino)
    return destino


def audio_16k(ruta: Path | str, pista: int = 0):
    """Decodifica con ffmpeg a PCM mono 16 kHz float32 (lo que espera Whisper).

    No usamos el decodificador interno de faster-whisper (PyAV): faster-whisper 1.2.1
    llama a av.open(metadata_errors=…), que PyAV ≥ 15 ya no acepta.
    """
    import numpy as np
    r = subprocess.run(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-i", str(ruta), "-map", f"0:a:{pista}",
         "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
        check=True, capture_output=True,
    )
    return np.frombuffer(r.stdout, dtype=np.float32).copy()


def registrar_dll_cuda() -> None:
    """faster-whisper (CTranslate2) necesita cublas64_12.dll y cudnn*_9.dll en Windows."""
    if os.name != "nt":
        return
    import site
    bases = [Path(p) for p in site.getsitepackages()] + [Path(sys.prefix) / "Lib" / "site-packages"]
    for base in bases:
        for sub in ("nvidia/cublas/bin", "nvidia/cudnn/bin", "nvidia/cuda_nvrtc/bin"):
            d = base / sub
            if d.is_dir():
                os.add_dll_directory(str(d))
                os.environ["PATH"] = str(d) + os.pathsep + os.environ.get("PATH", "")
