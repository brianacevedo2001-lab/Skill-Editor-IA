"""Corte palabra a palabra, seco, a 30 fps exactos y con la voz a −16 LUFS.

Uso:
  python pipeline/01_cut_silences.py <bruto> <corte.mp4> --words <palabras.json>
         [--aire 0.06] [--aire-punto 0.09] [--lufs -16] [--no-verificar]

Genera:
  <corte.mp4>              vídeo 1920x1080 CFR 30 fps (H.264 NVENC) + voz normalizada
  <corte>.cuts.json        mapa origen → corte (segmentos) para remap_times.py y los guiones
  <corte>.palabras_corte.json  las palabras que quedan, con tiempos YA en el corte (para anclar escenas)

Cómo decide qué se queda (ver «Reglas técnicas» en CLAUDE.md):
  - Umbral de voz relativo: voz (p90 dentro de palabras) − 24 dB. No un umbral fijo de ruido.
  - Cada grupo de palabras consecutivas conservadas es una «zona». Entre grupos (donde había una toma
    descartada) se corta todo, haya voz o no.
  - El inicio de cada zona retrocede hasta 250 ms mientras haya voz (las palabras cortas que abren frase
    salen tarde y con duración 0) y el final avanza hasta 250 ms mientras haya voz (colas de palabra).
  - Dentro de una zona, cualquier silencio más largo que el aire objetivo se reduce a ~60 ms
    (~90 ms tras coma o punto). También los silencios que Whisper mete DENTRO de una palabra.
  - Voz continua ≥ 0,2 s sin palabra transcrita NO se quita (Whisper coloca mal palabras enteras).
    Chasquidos < 0,2 s fuera de palabras sí se tratan como silencio.
  - Vídeo: redondeo acumulado. El audio se corta a muestra exacta; cada fotograma de salida se toma del
    fotograma de origen que le corresponde → vídeo y audio acaban con el MISMO número de fotogramas.
"""
from __future__ import annotations

import argparse
import sys
import json
import re
import subprocess
from pathlib import Path

import numpy as np

from comun import (FFMPEG, FPS, contar_fotogramas, escribir_json, ffmpeg, ffprobe_json, leer_json)

SR = 48000
HOP = SR // 100            # 10 ms
MUESTRAS_FOTOGRAMA = SR // FPS
RETROCESO = 0.25           # s máximos para retroceder el inicio / alargar el final mientras haya voz
VOZ_MIN_SIN_PALABRA = 0.20 # s de voz continua fuera de palabras que obligan a conservar
COLA_MAX = 15              # ×10 ms: lo más que se alarga una cola suave tras la voz clara (más = reverb)
FUNDIDO = int(0.005 * SR)  # 5 ms de entrada en cada empalme (evita clics)
FUNDIDO_SALIDA = int(0.020 * SR)  # 20 ms de salida: el final de frase decae, no se corta


# ───────────────────────── audio ─────────────────────────
def leer_audio(ruta: Path) -> tuple[np.ndarray, float]:
    """Audio mono 48 kHz float32 y el start_time de la pista (para alinear con el vídeo)."""
    info = ffprobe_json(ruta)
    a_st = next(s for s in info["streams"] if s["codec_type"] == "audio")
    inicio = float(a_st.get("start_time", 0) or 0)
    r = subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-i", str(ruta), "-map", "0:a:0",
                        "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], check=True, capture_output=True)
    return np.frombuffer(r.stdout, np.float32).copy(), inicio


def envolvente_db(a: np.ndarray) -> np.ndarray:
    n = len(a) // HOP
    pot = (a[:n * HOP].reshape(n, HOP) ** 2).mean(1)
    pot = np.convolve(pot, np.ones(3) / 3, mode="same")  # ventana efectiva de 30 ms: menos parpadeo
    return 10 * np.log10(pot + 1e-12)


def tramos(mask: np.ndarray) -> list[tuple[int, int]]:
    """Tramos [i, j) donde mask es True."""
    d = np.diff(np.concatenate([[0], mask.astype(np.int8), [0]]))
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))


# ───────────────────────── decisión de cortes ─────────────────────────
def planificar(palabras: list[dict], todas: list[dict], db: np.ndarray, aire: float, aire_punto: float,
               ) -> tuple[list[tuple[float, float]], list[str], float]:
    n = len(db)
    f = lambda t: int(round(t * 100))  # s → índice de envolvente
    dentro = np.zeros(n, bool)
    for w in palabras:
        dentro[max(f(w["inicio"]), 0):min(f(w["fin"]) + 1, n)] = True
    voz_db = float(np.percentile(db[dentro], 90)) if dentro.any() else float(db.max())
    umbral = voz_db - 24
    voz = db > umbral
    avisos: list[str] = []

    # Ruido que roza el umbral: trocea los silencios en pedacitos < aire y ya no se recortan
    # (prueba01: «fuera» con 2,5 s de pausa dentro sobrevivía al corte).
    #  a) destellos de voz < 50 ms → silencio
    #  b) voz aislada < 120 ms con ≥ 250 ms de silencio a cada lado → silencio (chasquidos, ruido), salvo
    #     que una palabra corta encaje dentro («y», «a»). Una palabra estirada por Whisper por encima
    #     (prueba01: 105,5 s) no cuenta.
    for i, j in tramos(voz):
        if j - i < 5:
            voz[i:j] = False
    for i, j in tramos(voz):
        if j - i < 12 and not voz[max(i - 25, 0):i].any() and not voz[j:j + 25].any():
            encaja = any(i - 5 <= f((w["inicio"] + w["fin"]) / 2) <= j + 5 and w["fin"] - w["inicio"] <= 2 * (j - i) / 100 + 0.1
                         for w in todas)
            if not encaja:
                voz[i:j] = False

    # Grupos de palabras conservadas consecutivas (sin palabras quitadas entre medias).
    quitadas = {w["i"] for w in todas} - {w["i"] for w in palabras}
    por_i = {w["i"]: w for w in todas}
    grupos: list[list[dict]] = []
    for w in palabras:
        if grupos and w["i"] - 1 == grupos[-1][-1]["i"]:
            grupos[-1].append(w)
        else:
            grupos.append([w])

    # Umbral suave para las COLAS: la última sílaba de una frase se dice flojo («respuesta» perdía la
    # «a», «promete» la «-te»: quedaban a −38/−42 dB con el umbral en −37,6). Nunca a menos de 4 dB
    # del ruido de fondo.
    ruido = float(np.percentile(db, 10))
    voz_suave = db > max(umbral - 7, ruido + 4)

    def cola(i: int, limite: int) -> int:
        """Desde el final de la voz clara, alarga mientras haya voz suave (salva caídas ≤ 60 ms)."""
        fin, hueco, k = i, 0, i
        while k < min(limite, i + COLA_MAX):
            if voz_suave[k]:
                fin, hueco = k + 1, 0
            else:
                hueco += 1
                if hueco > 6:
                    break
            k += 1
        return fin

    keep = np.zeros(n, bool)
    for g in grupos:
        # Límites: no invadir palabras quitadas vecinas (tomas descartadas).
        lim_a = f(por_i[g[0]["i"] - 1]["fin"]) if g[0]["i"] - 1 in quitadas else 0
        lim_b = f(por_i[g[-1]["i"] + 1]["inicio"]) if g[-1]["i"] + 1 in quitadas else n
        # Zona de búsqueda: 250 ms antes de la primera palabra (las que abren frase salen tarde) y
        # 250 ms + cola después de la última.
        # Si limita con una toma descartada sin pausa entre medias, el corte va al valle de energía
        # más cercano (prueba01: el 3.er intento empezaba mordido en 103,22 s).
        if lim_a:
            lim_a = max(lim_a - 8, 0) + int(np.argmin(db[max(lim_a - 8, 0):lim_a + 9]))
        if lim_b < n:
            lim_b = max(lim_b - 8, 0) + int(np.argmin(db[max(lim_b - 8, 0):lim_b + 9]))
        a = max(f(g[0]["inicio"]) - int(RETROCESO * 100), lim_a, 0)
        b = min(f(g[-1]["fin"]) + int(RETROCESO * 100) + COLA_MAX, lim_b, n)
        if b <= a:
            continue

        cubierto = np.zeros(b - a, bool)
        for w in g:
            cubierto[max(f(w["inicio"]) - 4 - a, 0):max(f(w["fin"]) + 4 - a, 0)] = True
        c_ini, c_fin = np.flatnonzero(cubierto)[[0, -1]] if cubierto.any() else (0, b - a - 1)
        v = voz[a:b].copy()
        for i, j in tramos(v):  # voz que no toca ninguna palabra
            if cubierto[i:j].any():
                continue
            if j <= c_ini or i > c_fin or (j - i) / 100 < VOZ_MIN_SIN_PALABRA:
                v[i:j] = False  # antes/después de la frase (respiración, ruido) o chasquido
            else:
                avisos.append(f"voz sin palabra transcrita {(a + i) / 100:.2f}–{(a + j) / 100:.2f} s: se conserva")
        if not v.any():
            continue
        idx = np.flatnonzero(v)
        s, e = int(idx[0]), int(idx[-1]) + 1  # voz clara de la frase

        def aire_tras(i_rel: int) -> int:
            t = (a + i_rel) / 100
            previa = [w for w in g if w["fin"] <= t + 0.05]
            ult = previa[-1]["w"] if previa else ""
            return int(round((aire_punto if re.search(r"[.,;:?!…]$", ult) else aire) * 100 / 2))

        k_zona = np.zeros(b - a, bool)
        k_zona[s:e] = True
        for i, j in tramos(~v[s:e]):  # silencios internos → aire (respetando la cola suave)
            i, j = i + s, j + s
            mitad = aire_tras(i)
            desde = cola(a + i, a + j) - a + mitad
            hasta = j - mitad
            if hasta > desde:
                k_zona[desde:hasta] = False
        mitad = aire_tras(e)
        k_zona[e:min(cola(a + e, b) - a + mitad, b - a)] = True   # cola final + aire
        k_zona[max(s - aire_tras(s), 0):s] = True                  # aire antes de la frase
        keep[a:b] |= k_zona

    segs = [(i / 100, j / 100) for i, j in tramos(keep)]
    return segs, avisos, umbral


# ───────────────────────── montaje ─────────────────────────
def cortar_audio(a: np.ndarray, segs: list[tuple[float, float]]) -> tuple[np.ndarray, list[dict]]:
    trozos, mapa, cursor = [], [], 0
    rampa = np.linspace(0, 1, FUNDIDO, dtype=np.float32)
    rampa_salida = np.linspace(1, 0, FUNDIDO_SALIDA, dtype=np.float32) ** 2
    for s0, s1 in segs:
        i, j = int(round(s0 * SR)), min(int(round(s1 * SR)), len(a))
        if j - i <= FUNDIDO + FUNDIDO_SALIDA:
            continue
        t = a[i:j].copy()
        t[:FUNDIDO] *= rampa
        t[-FUNDIDO_SALIDA:] *= rampa_salida
        trozos.append(t)
        mapa.append({"src": [round(i / SR, 5), round(j / SR, 5)],
                     "cut": [round(cursor / SR, 5), round((cursor + j - i) / SR, 5)]})
        cursor += j - i
    return np.concatenate(trozos), mapa


def fotogramas_origen(mapa: list[dict], n_salida: int, desfase_video: float) -> list[int]:
    """Redondeo acumulado: fotograma de origen (a 30 fps) para cada fotograma de salida."""
    res, prev, k = [], -1, 0
    for s in range(n_salida):
        t = (s + 0.5) / FPS
        while k + 1 < len(mapa) and t >= mapa[k]["cut"][1]:
            k += 1
        seg = mapa[k]
        t_src = seg["src"][0] + (t - seg["cut"][0]) + desfase_video
        idx = max(int(t_src * FPS), prev + 1)
        res.append(idx)
        prev = idx
    return res


def tramos_indices(indices: list[int]) -> list[tuple[int, int]]:
    runs, ini = [], indices[0]
    for p, q in zip(indices, indices[1:] + [None]):
        if q != p + 1:
            runs.append((ini, p))
            ini = q
    return runs


def expresion_select(indices: list[int]) -> str:
    return "+".join(f"between(n,{a},{b})" for a, b in tramos_indices(indices))


TRAMOS_POR_BLOQUE = 40


def codificar_indices(entrada: Path, indices: list[int], salida: Path, pre="[base]null[pre]", post: str = "",
                      cq: int = 18, audio: Path | None = None, paralelo: int = 3) -> None:
    """Codifica exactamente los fotogramas `indices` (a 30 fps) de `entrada`, en orden.

    ffmpeg no aguanta una expresión `select` con cientos de tramos (prueba02: 330 → «Cannot allocate
    memory»), así que se codifica por bloques de ≤ 40 tramos: cada bloque salta con -ss a su zona del bruto
    (con -copyts para que `t` siga siendo el tiempo absoluto: el pixelado se activa por `t`), se comprueba
    su número de fotogramas y al final se unen con el demuxer concat sin recodificar.
      pre:  grafo en tiempo del bruto (tras fps=30): entra por [base] y sale por [pre] (pixelado, recorte).
            Puede ser una función (t0, t1) → grafo, para incluir solo lo que afecta a cada bloque.
      post: filtros tras la selección (escala, formato). Empieza por «,».
    """
    import concurrent.futures
    import tempfile
    runs = tramos_indices(indices)
    bloques = [runs[k:k + TRAMOS_POR_BLOQUE] for k in range(0, len(runs), TRAMOS_POR_BLOQUE)]
    tmp = Path(tempfile.mkdtemp(prefix="bloques_", dir=salida.parent))

    def uno(k: int, bloque: list[tuple[int, int]]) -> Path:
        n = sum(b - a + 1 for a, b in bloque)
        t0 = max(0.0, bloque[0][0] / FPS - 1.0)
        expr = "+".join(f"between(t,{(a - 0.25) / FPS:.4f},{(b + 0.25) / FPS:.4f})" for a, b in bloque)
        guion = tmp / f"f{k:03d}.txt"
        grafo = pre(bloque[0][0] / FPS - 1.0, bloque[-1][1] / FPS + 1.0) if callable(pre) else pre
        guion.write_text(f"[0:v]fps={FPS}[base];{grafo};[pre]select='{expr}',setpts=N/{FPS}/TB{post},format=yuv420p[v]",
                         encoding="utf-8")
        out = tmp / f"b{k:03d}.mp4"
        ffmpeg("-ss", f"{t0:.3f}", "-copyts", "-i", str(entrada), "-/filter_complex", str(guion), "-map", "[v]",
               "-frames:v", str(n), "-r", str(FPS), "-an", "-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr",
               "-cq", str(cq), "-b:v", "0", "-g", str(FPS), str(out))
        obtenidos = contar_fotogramas(out)
        if obtenidos != n:
            raise RuntimeError(f"bloque {k}: {obtenidos} fotogramas, esperados {n}")
        return out

    with concurrent.futures.ThreadPoolExecutor(paralelo) as ex:
        partes = list(ex.map(lambda kb: uno(*kb), enumerate(bloques)))
    lista = tmp / "lista.txt"
    lista.write_text("".join(f"file '{p.as_posix()}'\n" for p in partes), encoding="utf-8")
    args = ["-f", "concat", "-safe", "0", "-i", str(lista)]
    if audio:
        args += ["-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ac", "2"]
    else:
        args += ["-c", "copy"]
    ffmpeg(*args, "-movflags", "+faststart", str(salida))
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()


def loudnorm(entrada: Path, salida: Path, lufs: float) -> dict:
    filtro = f"loudnorm=I={lufs}:TP=-1.5:LRA=11"
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", str(entrada), "-af", filtro + ":print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    ffmpeg("-i", str(entrada), "-af",
           f"{filtro}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
           f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true",
           "-ar", str(SR), "-c:a", "pcm_s16le", str(salida))
    return m


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("bruto", type=Path)
    p.add_argument("corte", type=Path)
    p.add_argument("--words", type=Path, required=True, help="palabras.json de 03_tomas.py")
    p.add_argument("--aire", type=float, default=0.06)
    p.add_argument("--aire-punto", type=float, default=0.09)
    p.add_argument("--lufs", type=float, default=-16)
    p.add_argument("--no-verificar", action="store_true")
    p.add_argument("--sin-alinear", action="store_true")
    a = p.parse_args()

    if a.corte.with_suffix("").name + ".palabras_corte.json" == a.words.name:
        raise SystemExit("--words no puede llamarse igual que la salida <corte>.palabras_corte.json")
    pal = leer_json(a.words)
    todas = leer_json(pal["transcripcion"])["palabras"]
    audio, a_inicio = leer_audio(a.bruto)
    info = ffprobe_json(a.bruto)
    v_st = next(s for s in info["streams"] if s["codec_type"] == "video")
    desfase_video = a_inicio - float(v_st.get("start_time", 0) or 0)  # tiempo audio → tiempo vídeo

    db = envolvente_db(audio)
    segs, avisos, umbral = planificar(pal["palabras"], todas, db, a.aire, a.aire_punto)
    for av in avisos:
        print("  ⚠", av)
    # Cortes con voz: si justo en el borde de un tramo hay voz clara, se está comiendo una sílaba.
    comidos = []
    for s0, s1 in segs:
        i0, i1 = int(round(s0 * 100)), int(round(s1 * 100))
        if i1 < len(db) and db[i1 - 1] > umbral:          # el fotograma exacto del corte
            comidos.append(f"final en {s1:.2f} s")
        if i0 > 0 and db[i0] > umbral:
            comidos.append(f"inicio en {s0:.2f} s")
    print(f"{'⚠ cortes con voz: ' + ', '.join(comidos) if comidos else '✔ ningún corte cae sobre voz clara'}")
    cortado, mapa = cortar_audio(audio, segs)
    n_fot = int(round(len(cortado) / MUESTRAS_FOTOGRAMA))
    cortado = np.pad(cortado, (0, max(0, n_fot * MUESTRAS_FOTOGRAMA - len(cortado))))[:n_fot * MUESTRAS_FOTOGRAMA]
    print(f"Umbral de voz {umbral:.1f} dB · {len(mapa)} tramos · {len(audio) / SR:.1f} s → {n_fot / FPS:.2f} s "
          f"({n_fot} fotogramas)")

    a.corte.parent.mkdir(parents=True, exist_ok=True)
    base = a.corte.with_suffix("")
    wav_crudo, wav_norm = base.with_name(base.name + ".voz_cruda.wav"), base.with_name(base.name + ".voz.wav")
    with open(wav_crudo, "wb") as fh:
        pcm = (np.clip(cortado, -1, 1) * 32767).astype("<i2")
        import wave
        with wave.open(fh, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    m = loudnorm(wav_crudo, wav_norm, a.lufs)
    print(f"Voz: {m['input_i']} LUFS → {a.lufs} LUFS")

    indices = fotogramas_origen(mapa, n_fot, desfase_video)
    # Respeta la orientación: un vertical (móvil en vertical) sale 1080×1920. Forzar siempre 1920×1080
    # recortaba el centro de un vertical y dejaba un primer plano de la boca (proyecto01).
    vb = next(s for s in ffprobe_json(a.bruto)["streams"] if s["codec_type"] == "video")
    rot = next((abs(int(sd.get("rotation", 0))) for sd in vb.get("side_data_list", []) if "rotation" in sd), 0)
    ancho, alto = (int(vb["height"]), int(vb["width"])) if rot in (90, 270) else (int(vb["width"]), int(vb["height"]))
    W, H = (1080, 1920) if alto > ancho else (1920, 1080)
    codificar_indices(a.bruto, indices, a.corte, cq=18, audio=wav_norm,
                      post=f",scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}")

    # Comprobación de fotogramas: vídeo y audio deben durar lo mismo.
    nv = contar_fotogramas(a.corte)
    dur_a = float(next(s for s in ffprobe_json(a.corte)["streams"] if s["codec_type"] == "audio")["duration"])
    ok = nv == n_fot and abs(dur_a - n_fot / FPS) < 0.03
    print(f"{'✔' if ok else '✘'} vídeo {nv} fotogramas · audio {dur_a:.3f} s ({dur_a * FPS:.1f} fotogramas)")

    # Pausas que se notan: la verificación por palabras no las ve (no falta ni sobra texto).
    db_c = envolvente_db(cortado)
    # `cortado` aún no está normalizado: mismo nivel que el bruto. Umbral suave: las colas no son pausa.
    sil = db_c < max(umbral - 7, float(np.percentile(db, 10)) + 4)
    largos = [(i / 100, (j - i) * 10) for i, j in tramos(sil) if (j - i) >= 25]
    if largos:
        for t, ms in largos:
            print(f"  ⚠ pausa de {ms} ms en {t:.2f} s del corte")
    else:
        print("✔ ninguna pausa de más de 250 ms")

    # Mapa y palabras en el tiempo del corte
    def a_corte(t: float) -> float:
        for s in mapa:
            if t <= s["src"][1]:
                return round(s["cut"][0] + max(t - s["src"][0], 0), 3)
        return round(mapa[-1]["cut"][1], 3)

    escribir_json(base.with_name(base.name + ".cuts.json"),
                  {"fuente": str(a.bruto), "corte": str(a.corte), "fps": FPS, "fotogramas": n_fot,
                   "duracion": round(n_fot / FPS, 3), "umbral_db": round(umbral, 1), "segmentos": mapa})
    escribir_json(base.with_name(base.name + ".palabras_corte.json"),
                  [{"i": w["i"], "w": w["w"], "inicio": a_corte(w["inicio"]), "fin": a_corte(w["fin"])}
                   for w in pal["palabras"]])
    wav_crudo.unlink(missing_ok=True)
    print(f"→ {a.corte}")

    if not a.sin_alinear:                      # tiempos de palabra exactos (alineación forzada sobre la voz cortada)
        r = subprocess.run([sys.executable, str(Path(__file__).with_name("alinear.py")), str(base)])
        if r.returncode:
            print("⚠ alinear.py falló: se quedan los tiempos de Whisper")

    if not a.no_verificar:
        from verificar_corte import verificar
        verificar(a.corte, a.words)


if __name__ == "__main__":
    main()
