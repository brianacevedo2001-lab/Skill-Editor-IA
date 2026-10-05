"""Pixelado automático de datos personales con OCR (RapidOCR, local, sin enviar nada fuera).

Uso:
  python pipeline/pixelar_auto.py videos/<id>/grueso.prep.json [--procesos 6] [--muestreo 4]

Lee la pantalla bruta indicada en el prep y escribe videos/<id>/grueso.pixelar_auto.json, que 04_grueso.py
suma a los rectángulos manuales de "pixelar".

1. Estados de pantalla: se muestrea a `--muestreo` fps y se abre un estado nuevo cada vez que la imagen cambia
   (también con scroll pequeño). Solo se hace OCR de un fotograma por estado.
2. OCR (un proceso: RapidOCR ya usa casi todos los núcleos; varios procesos a la vez se estorban
   —prueba02: 6 procesos gastaron 68 000 s de CPU sin terminar—). Solo dentro de "ocr_zona" del prep
   [x, y, ancho, alto] si existe (p. ej. sin la barra del navegador ni el menú lateral).
3. Se pixela cada caja de texto que contenga:
     correo · teléfono (+57…, 7+ dígitos) · cédula (CC …) · cuentas / números largos · fechas de nacimiento
     (17/septiembre/1969, 17/09/1969) · «a nombre de …» · cualquier palabra de "sensibles" del prep
     (nombres de clientes, apellidos…; sin tildes ni mayúsculas).
4. Cada caja vale desde que empieza su estado hasta que empieza el siguiente (± 0,3 s). Si el estado es muy
   corto (scroll en marcha), la caja se alarga en vertical para cubrir el desplazamiento.
El JSON guarda la CATEGORÍA de cada caja, nunca el texto leído.
Complementa, no sustituye, a las zonas manuales para listas de nombres (columnas enteras).
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import re
import subprocess
import time
import unicodedata
from pathlib import Path

import numpy as np

from comun import FFMPEG, RAIZ, escribir_json, ffprobe_json, leer_json

MESES = "enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre"
PATRONES = [
    ("correo", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")),
    ("telefono", re.compile(r"\+?\d[\d\s().-]{8,}\d")),
    ("cedula", re.compile(r"\b(cc|c\.c\.|cedula|dni|nit)\s*[:#]?\s*\d{5,}")),
    ("numero", re.compile(r"#?\d{7,}")),
    ("fecha", re.compile(rf"\b\d{{1,2}}\s*[/-]\s*({MESES}|\d{{1,2}})\s*[/-]\s*\d{{2,4}}\b")),
    ("fecha", re.compile(rf"\b\d{{1,2}}\s+de\s+({MESES})\s+de\s+\d{{4}}\b")),
    ("titular", re.compile(r"a\s*nombre\s*de")),
]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


ANIO = time.localtime().tm_year


def categoria(texto: str, sensibles: list[str]) -> str | None:
    t = norm(texto)
    for nombre, pat in PATRONES:
        m = pat.search(t)
        if not m:
            continue
        if nombre == "fecha":
            anio = re.search(r"(\d{4})\s*$", m.group(0))
            if anio and int(anio.group(1)) >= ANIO - 1:
                continue            # marca de tiempo reciente de la app («25/9/2026»), no un dato personal
        return nombre
    compacto = t.replace(" ", "")
    for s in sensibles:
        if s and (s in t or s.replace(" ", "") in compacto):
            return "nombre"
    return None


# ───────────── procesos de OCR ─────────────
_ocr = None


def _init():
    global _ocr
    from rapidocr_onnxruntime import RapidOCR
    _ocr = RapidOCR()


def _leer(args):
    ruta, t, ancho, alto, zona = args
    r = subprocess.run([FFMPEG, "-loglevel", "error", "-ss", f"{t:.3f}", "-i", ruta, "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    if len(r.stdout) != ancho * alto * 3:
        return t, []
    img = np.frombuffer(r.stdout, np.uint8).reshape(alto, ancho, 3)
    zx, zy, zw, zh = zona
    res, _ = _ocr(np.ascontiguousarray(img[zy:zy + zh, zx:zx + zw]))
    cajas = []
    for box, txt, conf in res or []:
        xs = [p[0] + zx for p in box]; ys = [p[1] + zy for p in box]
        cajas.append((txt, float(conf), int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))))
    return t, cajas


def estados(ruta: str, fps: float, umbral: float = 0.6) -> list[float]:
    r = subprocess.run([FFMPEG, "-loglevel", "error", "-i", ruta, "-vf", f"fps={fps},scale=320:180,format=gray",
                        "-f", "rawvideo", "-"], capture_output=True, check=True)
    fr = np.frombuffer(r.stdout, np.uint8).reshape(-1, 180, 320).astype(np.int16)
    res, ultimo = [], None
    for k, f in enumerate(fr):
        if ultimo is None or np.abs(f - ultimo).mean() > umbral:
            res.append(k / fps)
            ultimo = f
    return res


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("prep", type=Path)
    p.add_argument("--procesos", type=int, default=1)
    p.add_argument("--muestreo", type=float, default=4.0)
    p.add_argument("--reclasificar", action="store_true",
                   help="reutiliza grueso.ocr_cache.json: reaplica las reglas sin repetir el OCR")
    a = p.parse_args()

    prep = leer_json(a.prep)
    ruta = str(RAIZ / prep["pantalla"])
    v = next(s for s in ffprobe_json(ruta)["streams"] if s["codec_type"] == "video")
    W, H = int(v["width"]), int(v["height"])
    dur = float(ffprobe_json(ruta)["format"]["duration"])
    sensibles = [norm(s) for s in prep.get("sensibles", [])]

    t0 = time.time()
    # El OCR bruto (con texto) se guarda en local, fuera de git, para poder reclasificar sin repetirlo.
    cache = a.prep.with_name("grueso.ocr_cache.json")
    if a.reclasificar and cache.exists():
        guardado = leer_json(cache)
        ts = guardado["estados"]
        resultados = {float(k): v for k, v in guardado["ocr"].items()}
        print(f"Reclasificando {len(ts)} estados desde {cache.name}")
    else:
        ts = estados(ruta, a.muestreo)
        print(f"{len(ts)} estados de pantalla distintos en {dur:.0f} s (muestreo {a.muestreo} fps)")
        # OCR ligeramente después del cambio (evita el fotograma de transición)
        zona = prep.get("ocr_zona", [0, 0, W, H])
        tareas = [(ruta, min(t + 0.12, dur - 0.05), W, H, zona) for t in ts]
        resultados = {}
        with mp.Pool(a.procesos, initializer=_init) as pool:
            for k, (t, cajas) in enumerate(pool.imap(_leer, tareas, chunksize=2)):
                resultados[t] = cajas
                if (k + 1) % 10 == 0 or k + 1 == len(tareas):
                    print(f"  OCR {k + 1}/{len(tareas)} ({time.time() - t0:.0f} s)", flush=True)
        escribir_json(cache, {"estados": ts, "ocr": {str(k): v for k, v in resultados.items()}})

    rects, conteo = [], {}
    cajas_de = lambda k: resultados.get(min(ts[k] + 0.12, dur - 0.05), []) if 0 <= k < len(ts) else []
    for i, t in enumerate(ts):
        fin = ts[i + 1] if i + 1 < len(ts) else dur
        movimiento = (fin - t) < 0.6                              # scroll en marcha
        # En scroll, el OCR de ESTE estado puede no ver un dato que el vecino sí vio (prueba02: «a nombre de
        # María Fernanda calzada» legible en un fotograma en movimiento): se aplican también las detecciones
        # de los estados vecinos, con margen vertical amplio, solo mientras dura este estado.
        fuentes = [(cajas_de(i), 60 if movimiento else 8)]
        if movimiento:
            fuentes += [(cajas_de(i - 1), 260), (cajas_de(i + 1), 260)]
        for n, (cajas, pad_y) in enumerate(fuentes):
            for txt, conf, x0, y0, x1, y1 in cajas:
                cat = categoria(txt, sensibles)
                if not cat:
                    continue
                if n == 0:
                    conteo[cat] = conteo.get(cat, 0) + 1
                x0, y0 = max(0, x0 - 8), max(0, y0 - pad_y)
                x1, y1 = min(W, x1 + 8), min(H, y1 + pad_y)
                desde = t - 0.3 if n == 0 else t
                hasta = fin + 0.3 if n == 0 else fin
                rects.append({"desde": round(max(0.0, desde), 2), "hasta": round(min(dur, hasta), 2),
                              "rect": [x0, y0, x1 - x0, y1 - y0], "nota": f"auto:{cat}"})
    # Anclas: si aparece un rótulo (p. ej. «DATOS DE CONTACTO»), se pixela una zona fija entera durante ese
    # estado ± margen. Red de seguridad para el scroll: en los fotogramas en movimiento el OCR del estado
    # puede no ver aún el dato, pero el panel entero queda cubierto (prueba02: correo asomando por abajo).
    for ancla in prep.get("anclas", []):
        clave = norm(ancla["texto"])
        margen = float(ancla.get("margen", 1.5))
        for i, t in enumerate(ts):
            cajas = resultados.get(min(t + 0.12, dur - 0.05), [])
            if any(clave in norm(c[0]) for c in cajas):
                fin = ts[i + 1] if i + 1 < len(ts) else dur
                rects.append({"desde": round(max(0.0, t - margen), 2), "hasta": round(min(dur, fin + margen), 2),
                              "rect": list(ancla["zona"]), "nota": f"ancla:{clave}"})
                conteo["ancla"] = conteo.get("ancla", 0) + 1

    # Unir la misma caja en estados consecutivos
    rects.sort(key=lambda r: (r["rect"][0] // 6, r["rect"][1] // 6, r["desde"]))
    unidos: list[dict] = []
    for r in rects:
        u = unidos[-1] if unidos else None
        if (u and all(abs(u["rect"][k] - r["rect"][k]) <= 6 for k in range(4))
                and r["desde"] <= u["hasta"] + 0.05 and u["nota"] == r["nota"]):
            u["hasta"] = max(u["hasta"], r["hasta"])
        else:
            unidos.append(dict(r))
    unidos.sort(key=lambda r: r["desde"])
    salida = a.prep.with_name("grueso.pixelar_auto.json")
    escribir_json(salida, unidos)
    print(f"{len(unidos)} rectángulos ({', '.join(f'{k}: {v}' for k, v in sorted(conteo.items()))}) "
          f"en {time.time() - t0:.0f} s → {salida}")


if __name__ == "__main__":
    main()
