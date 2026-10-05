"""Corta el grueso: pantalla, cámara y voz en fotogramas exactos a 30 fps, con el MISMO número de fotogramas.

Uso:
  python pipeline/04_grueso.py videos/<id>/grueso.prep.json [--no-verificar]

grueso.prep.json (rutas relativas a la raíz del proyecto; tiempos en SEGUNDOS DE LA PANTALLA bruta):
  {
    "pantalla": "raw/<id>/pantalla.mp4",          grabación de OBS (la voz buena: micrófono micrófono USB)
    "camara":   "raw/<id>/camara.mp4",            grabación del móvil
    "sync":     "videos/<id>/grueso.sync.json",   de 05_sync.py
    "palabras": "videos/<id>/grueso.palabras.json",  de 03_tomas.py (sobre la transcripción de la PANTALLA)
    "recorte":  {"y": 0, "alto": 1440},           por defecto un monitor ultrapanorámico (ya 16:9). Portátil 16:10: {"y": 88, "alto": 1440}
                                                 sin pestañas/barra de tareas: {"y": 108, "alto": 1272, "rellenar": "0x0E1116"}
    "voltearCamara": true,                       cámara frontal del móvil (graba en espejo)
    "pixelar":  [{"desde": 12.0, "hasta": 40.5, "rect": [x, y, w, h], "nota": "Gmail"}],   px de la pantalla bruta
    "forzar":   [[a, b]],                          tramos que se quedan enteros (p. ej. el resultado funcionando)
    "quitar":   [[a, b]],                          tramos que se quitan aunque haya voz
    "aire": 0.06, "aire_punto": 0.09
  }

Genera en videos/<id>/:
  grueso_pantalla.mp4   2560×1440, 30 fps CFR, pixelado aplicado + la voz a −16 LUFS
  grueso_camara.mp4     1920×1080, 30 fps CFR, sin audio
  grueso.voz.wav        la voz cortada (normalizada)
  grueso.cuts.json      mapa pantalla → corte + tramos SIN cámara (en tiempo del corte)
  grueso.palabras_corte.json
"""
from __future__ import annotations

import argparse
import sys
import subprocess
import importlib
import wave
from pathlib import Path

import numpy as np

from comun import FPS, RAIZ, contar_fotogramas, escribir_json, ffmpeg, ffprobe_json, leer_json

corte = importlib.import_module("01_cut_silences")
SR, MUESTRAS_FOTOGRAMA = corte.SR, corte.MUESTRAS_FOTOGRAMA


# ───────────────────────── intervalos ─────────────────────────
def unir(segs: list[tuple[float, float]]) -> list[tuple[float, float]]:
    res: list[list[float]] = []
    for a, b in sorted(segs):
        if res and a <= res[-1][1] + 1e-3:
            res[-1][1] = max(res[-1][1], b)
        else:
            res.append([a, b])
    return [(a, b) for a, b in res]


def restar(segs, quitar):
    res = []
    for a, b in segs:
        trozos = [(a, b)]
        for qa, qb in quitar:
            nuevos = []
            for x, y in trozos:
                if qb <= x or qa >= y:
                    nuevos.append((x, y))
                else:
                    if qa > x:
                        nuevos.append((x, qa))
                    if qb < y:
                        nuevos.append((qb, y))
            trozos = nuevos
        res += trozos
    return [(a, b) for a, b in res if b - a > 0.02]


# ───────────────────────── sincronización ─────────────────────────
def a_camara(t: float, sync: dict) -> float | None:
    """Tiempo de pantalla → tiempo de cámara. None si en ese instante no hay cámara."""
    for tr in sync["tramos"]:
        if tr["desde"] <= t < tr["hasta"] or (t >= tr["hasta"] and tr is sync["tramos"][-1]):
            if tr.get("sin_camara"):
                return None
            return t + tr["desfase"] + tr["deriva"] * (t - tr["desde"])
    return None


BLOQUE = 22  # px: el texto queda ilegible pero se siguen viendo las formas (burbujas, filas)


def filtro_pixelado(pixelar: list[dict], entrada: str, ancho: int = 2560, alto: int = 1440) -> tuple[str, str]:
    """Pixela los rectángulos en su intervalo (t = tiempo de la pantalla bruta), con coste casi constante:
    se pixela el fotograma ENTERO una vez, se dibuja una máscara con todos los rectángulos (drawbox sobre gris,
    barato) y se mezcla con alphamerge + overlay. La versión anterior (split + crop + overlay por rectángulo)
    copiaba el fotograma de 2560×1440 por cada zona: con cientos de zonas (OCR) no terminaba (prueba02)."""
    if not pixelar:
        return "", entrada
    cajas = ",".join(
        f"drawbox={int(p['rect'][0])}:{int(p['rect'][1])}:{int(p['rect'][2])}:{int(p['rect'][3])}:white:t=fill"
        f":enable='between(t,{p['desde']:.3f},{p['hasta']:.3f})'"
        for p in pixelar)
    grafo = (f"[{entrada}]split=3[pxa][pxb][pxc];"
             f"[pxb]scale={ancho // BLOQUE}:{alto // BLOQUE}:flags=area,scale={ancho}:{alto}:flags=neighbor[pxp];"
             f"[pxc]extractplanes=y,drawbox=0:0:iw:ih:black:t=fill,{cajas}[pxm];"
             f"[pxp][pxm]alphamerge[pxpa];"
             f"[pxa][pxpa]overlay=0:0[pxo];")
    return grafo, "pxo"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prep", type=Path)
    ap.add_argument("--no-verificar", action="store_true")
    ap.add_argument("--sin-alinear", action="store_true")
    a = ap.parse_args()

    prep = leer_json(a.prep)
    ruta = lambda k: RAIZ / prep[k]
    salida = a.prep.parent
    pantalla, camara = ruta("pantalla"), ruta("camara")
    sync = leer_json(ruta("sync"))
    pal = leer_json(ruta("palabras"))
    todas = leer_json(RAIZ / pal["transcripcion"] if not Path(pal["transcripcion"]).is_absolute() else pal["transcripcion"])["palabras"]

    # 1) Qué se queda: mismo criterio que las partes a cámara + forzar / quitar.
    audio, a_inicio = corte.leer_audio(pantalla)
    info_p = ffprobe_json(pantalla)
    vp = next(s for s in info_p["streams"] if s["codec_type"] == "video")
    desfase_vp = a_inicio - float(vp.get("start_time", 0) or 0)
    db = corte.envolvente_db(audio)
    segs, avisos, umbral = corte.planificar(pal["palabras"], todas, db, prep.get("aire", 0.06), prep.get("aire_punto", 0.09))
    for av in avisos:
        print("  ⚠", av)
    segs = unir(segs + [tuple(x) for x in prep.get("forzar", [])])
    segs = restar(segs, [tuple(x) for x in prep.get("quitar", [])])

    cortado, mapa = corte.cortar_audio(audio, segs)
    n_fot = int(round(len(cortado) / MUESTRAS_FOTOGRAMA))
    cortado = np.pad(cortado, (0, max(0, n_fot * MUESTRAS_FOTOGRAMA - len(cortado))))[: n_fot * MUESTRAS_FOTOGRAMA]
    print(f"Umbral de voz {umbral:.1f} dB · {len(mapa)} tramos · {len(audio) / SR:.1f} s → {n_fot / FPS:.2f} s ({n_fot} fotogramas)")

    # 2) Voz normalizada
    crudo, voz = salida / "grueso.voz_cruda.wav", salida / "grueso.voz.wav"
    with wave.open(str(crudo), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(cortado, -1, 1) * 32767).astype("<i2").tobytes())
    m = corte.loudnorm(crudo, voz, -16)
    crudo.unlink(missing_ok=True)
    print(f"Voz: {m['input_i']} LUFS → −16 LUFS")

    # 3) Pantalla: pixelado (en tiempo bruto) → 16:9 → fotogramas del corte
    idx_p = corte.fotogramas_origen(mapa, n_fot, desfase_vp)
    rec = prep.get("recorte", {"y": 0, "alto": 1440})  # un monitor ultrapanorámico ya graba 16:9 (2560×1440)
    ancho = int(vp["width"])
    pixelar = list(prep.get("pixelar", []))
    auto = salida / "grueso.pixelar_auto.json"
    if auto.exists():
        pixelar += leer_json(auto)
        print(f"Pixelado: {len(prep.get('pixelar', []))} zonas manuales + {len(pixelar) - len(prep.get('pixelar', []))} automáticas (OCR)")

    def grafo_p(t0: float, t1: float) -> str:
        # Solo los rectángulos que tocan este bloque: el grafo no crece con la duración del vídeo.
        dentro = [r for r in pixelar if r["desde"] < t1 and r["hasta"] > t0]
        pix, ultima = filtro_pixelado(dentro, "base", ancho, int(vp["height"]))
        recorte = f"crop={ancho}:{rec['alto']}:0:{rec['y']}"
        if rec.get("rellenar"):
            # p. ej. sin pestañas ni barra de tareas: se rellena hasta 16:9 con el fondo de la marca (sin deformar)
            alto16 = ancho * 9 // 16
            recorte += f",pad={ancho}:{alto16}:0:{(alto16 - rec['alto']) // 2}:color={rec['rellenar']}"
        return f"{pix}[{ultima}]{recorte}[pre]"
    sal_p = salida / "grueso_pantalla.mp4"
    print(f"Codificando pantalla ({len(corte.tramos_indices(idx_p))} tramos)…")
    corte.codificar_indices(pantalla, idx_p, sal_p, pre=grafo_p, cq=17, audio=voz)

    # 4) Cámara: cada fotograma del corte → su instante en la cámara (sync con deriva)
    info_c = ffprobe_json(camara)
    vc = next(s for s in info_c["streams"] if s["codec_type"] == "video")
    ac = next((s for s in info_c["streams"] if s["codec_type"] == "audio"), vc)
    desfase_vc = float(ac.get("start_time", 0) or 0) - float(vc.get("start_time", 0) or 0)
    dur_c = float(info_c["format"]["duration"])
    idx_c, sin_cam, prev, k = [], [], -1, 0
    for s in range(n_fot):
        t = (s + 0.5) / FPS
        while k + 1 < len(mapa) and t >= mapa[k]["cut"][1]:
            k += 1
        t_src = mapa[k]["src"][0] + (t - mapa[k]["cut"][0])
        tc = a_camara(t_src, sync)
        falta = tc is None or tc < 0 or tc >= dur_c - 0.05
        sin_cam.append(falta)
        i = int(max(0.0, (tc or 0.0) + desfase_vc) * FPS)  # tiempo de audio de la cámara → su vídeo
        i = max(i, prev + 1)
        idx_c.append(i)
        prev = i
    sal_c = salida / "grueso_camara.mp4"
    print(f"Codificando cámara ({len(corte.tramos_indices(idx_c))} tramos)…")
    # Cámara frontal del móvil = imagen en espejo: "voltearCamara": true la corrige (proyecto01).
    volteo = ",hflip" if prep.get("voltearCamara") else ""
    corte.codificar_indices(camara, idx_c, sal_c, cq=19,
                            post=f"{volteo},scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080")
    # Si la cámara se acaba antes, ffmpeg da menos fotogramas: se alarga congelando el último.
    nc = contar_fotogramas(sal_c)
    if nc < n_fot:
        tmp = sal_c.with_name("grueso_camara_tmp.mp4")
        ffmpeg("-i", str(sal_c), "-vf", f"tpad=stop_mode=clone:stop={n_fot - nc}", "-frames:v", str(n_fot),
               "-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "19", "-b:v", "0", str(tmp))
        tmp.replace(sal_c)
        for s in range(nc, n_fot):
            sin_cam[s] = True

    # 5) Comprobación: los tres con el MISMO número de fotogramas
    npf, ncf = contar_fotogramas(sal_p), contar_fotogramas(sal_c)
    with wave.open(str(voz)) as w:
        nvoz = w.getnframes() / w.getframerate() * FPS
    ok = npf == ncf == n_fot and abs(nvoz - n_fot) < 1
    print(f"{'✔' if ok else '✘'} pantalla {npf} · cámara {ncf} · voz {nvoz:.1f} fotogramas (esperados {n_fot})")

    # Tramos sin cámara, en segundos del corte
    tramos_sin, i = [], 0
    while i < n_fot:
        if sin_cam[i]:
            j = i
            while j < n_fot and sin_cam[j]:
                j += 1
            tramos_sin.append([round(i / FPS, 3), round(j / FPS, 3)])
            i = j
        else:
            i += 1
    for x, y in tramos_sin:
        print(f"  · sin cámara en el corte {x:.2f}–{y:.2f} s (la esquina se oculta)")

    def a_corte(t: float) -> float:
        for s in mapa:
            if t <= s["src"][1]:
                return round(s["cut"][0] + max(t - s["src"][0], 0), 3)
        return round(mapa[-1]["cut"][1], 3)

    escribir_json(salida / "grueso.cuts.json", {
        "fuente": str(prep["pantalla"]), "fps": FPS, "fotogramas": n_fot, "duracion": round(n_fot / FPS, 3),
        "umbral_db": round(umbral, 1), "recorte": rec, "sin_camara": tramos_sin, "segmentos": mapa})
    escribir_json(salida / "grueso.palabras_corte.json",
                  [{"i": w["i"], "w": w["w"], "inicio": a_corte(w["inicio"]), "fin": a_corte(w["fin"])} for w in pal["palabras"]])
    print(f"→ {sal_p}\n→ {sal_c}")

    if not a.sin_alinear:                      # tiempos de palabra exactos (alineación forzada sobre la voz cortada)
        r = subprocess.run([sys.executable, str(Path(__file__).with_name("alinear.py")), str(salida / "grueso")])
        if r.returncode:
            print("⚠ alinear.py falló: se quedan los tiempos de Whisper")

    if not a.no_verificar:
        # Las palabras de los tramos quitados a mano no deben contar como «faltan».
        quitar = [tuple(x) for x in prep.get("quitar", [])]
        esperadas = [w for w in pal["palabras"]
                     if not any(qa <= (w["inicio"] + w["fin"]) / 2 <= qb for qa, qb in quitar)]
        ruta_esp = salida / "grueso.palabras_esperadas.json"
        escribir_json(ruta_esp, {**pal, "palabras": esperadas})
        from verificar_corte import verificar
        verificar(sal_p, ruta_esp)


if __name__ == "__main__":
    main()
