"""Transcribe un vídeo o audio con marcas de tiempo por palabra (faster-whisper en CUDA), en dos pasadas.

Uso:
  python pipeline/02_transcribe.py <vídeo|audio> <salida.json> [--modelo turbo|large-v3] [--pista 0]
                                   [--una-pasada]

Pasada 1 (completa): todo el audio de una vez. Mejor contexto → mejores palabras.
Pasada 2 (literal):  el audio se trocea en cada pausa (≥ 0,35 s) y cada trozo se transcribe por separado
                     (secuencial, con un prompt de titubeos). Whisper con el archivo entero SE SALTA LAS REPETICIONES («no por el
                     producto, no porque el producto, no porque el producto fuera malo» → solo la última),
                     y 03_tomas.py no puede quitar lo que no ve. Trozo a trozo sí las transcribe.
Por cada trozo se usa la pasada 2 si tiene más palabras que la 1, o si la 1 trae alguna palabra de más
de 1 s (Whisper metiendo pausas o tomas dentro de una palabra). Si no, se queda la pasada 1.

Salida:
  {"fuente", "duracion", "modelo", "idioma", "trozos_literales": [[ini, fin, antes, despues]…],
   "segmentos": [{"inicio", "fin", "texto"}],
   "palabras":  [{"i", "w", "inicio", "fin", "prob", "seg", "pasada"}]}
"""
from __future__ import annotations

import argparse
import re
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np

from comun import MARCA, audio_16k, escribir_json, leer_json, registrar_dll_cuda

SR = 16000
PAUSA_TROZO = 0.35     # s de silencio que separan trozos en la pasada literal
MAX_TROZO = 25.0       # s (Whisper trabaja en ventanas de 30 s)
PALABRA_LARGA = 1.0    # s: una palabra así de larga esconde pausas o tomas
# Ejemplo de habla con titubeos y repeticiones: le dice a Whisper «transcribe literal, no resumas».
# Genérico a propósito (sin palabras de ningún vídeo concreto); probado en prueba01: con él aparecen
# los tres intentos de «no porque el producto…» y el «Compite… Compite», de forma estable.
PROMPT_LITERAL = "Mmm, vale. Hoy, hoy te... hoy te enseño, eh... no. Hoy te enseño cómo, cómo lo hago. "


def _n(w: str) -> str:
    w = unicodedata.normalize("NFD", w.lower())
    return re.sub(r"[^\w]", "", "".join(c for c in w if unicodedata.category(c) != "Mn"))


def trozos_de_voz(audio: np.ndarray) -> list[tuple[float, float]]:
    hop = SR // 100
    n = len(audio) // hop
    pot = np.convolve((audio[:n * hop].reshape(n, hop) ** 2).mean(1), np.ones(3) / 3, "same")
    db = 10 * np.log10(pot + 1e-12)
    voz = db > np.percentile(db, 95) - 30
    res, i = [], 0
    while i < n:
        if not voz[i]:
            i += 1
            continue
        j = i
        while j < n:
            if voz[j]:
                j += 1
                continue
            k = j
            while k < n and not voz[k]:
                k += 1
            if (k - j) / 100 >= PAUSA_TROZO or k >= n or (k - i) / 100 > MAX_TROZO:
                break
            j = k
        if (j - i) >= 8:  # ≥ 80 ms
            a = max(i / 100 - 0.15, res[-1][1] if res else 0.0)  # sin solapes (faster-whisper los suma)
            res.append((round(a, 2), round(min(j / 100 + 0.2, n / 100), 2)))
        i = j
    return res


def a_palabras(segs, desplazamiento: float = 0.0, pasada: int = 1) -> list[dict]:
    res = []
    for s in segs:
        for w in s.words or []:
            res.append({"w": w.word.strip(), "inicio": round(w.start + desplazamiento, 3),
                        "fin": round(w.end + desplazamiento, 3), "prob": round(w.probability, 3),
                        "pasada": pasada})
    return [w for w in res if w["w"]]


def transcribir(ruta: Path, modelo: str | None = None, pista: int = 0, una_pasada: bool = False) -> dict:
    cfg = leer_json(MARCA / "proyecto.json")["equipo"]["transcripcion"]
    modelo = modelo or cfg["modelo"]
    idioma = leer_json(MARCA / "marca.json").get("idioma", "es").split("-")[0]
    hotwords = " ".join(cfg.get("vocabulario", [])) or None

    registrar_dll_cuda()
    from faster_whisper import WhisperModel

    audio = audio_16k(ruta, pista)
    dur = len(audio) / SR
    t0 = time.time()
    m = WhisperModel(modelo, device=cfg.get("dispositivo", "cuda"), compute_type="float16")
    comunes = dict(language=idioma, word_timestamps=True, beam_size=5, condition_on_previous_text=False,
                   vad_filter=False)

    # Pasada 1: con `hotwords` (vocabulario de marca bien escrito).
    segs1 = list(m.transcribe(audio, hotwords=hotwords, **comunes)[0])
    completa = a_palabras(segs1, pasada=1)
    segmentos = [{"inicio": round(s.start, 3), "fin": round(s.end, 3), "texto": s.text.strip()} for s in segs1]

    palabras, literales = completa, []
    if not una_pasada:
        # Pasada 2: trozo a trozo, SECUENCIAL (el modo por lotes vuelve a saltarse repeticiones) y con un
        # prompt lleno de titubeos: así Whisper transcribe literal. Sin `hotwords` (alucina «Telegram»,
        # «www»… en los silencios); el vocabulario va dentro del prompt.
        prompt = PROMPT_LITERAL + ", ".join(cfg.get("vocabulario", [])) + "."
        literal = []
        trozos = trozos_de_voz(audio)
        for a, b in trozos:
            segs = m.transcribe(audio[int(a * SR):int(b * SR)], initial_prompt=prompt, **comunes)[0]
            literal += a_palabras(segs, desplazamiento=a, pasada=2)
        palabras = []
        for a, b in trozos:
            en = lambda ws: [w for w in ws if a <= (w["inicio"] + w["fin"]) / 2 < b]
            p1, p2 = en(completa), en(literal)
            larga = any(w["fin"] - w["inicio"] > PALABRA_LARGA for w in p1)
            # Solo donde la pasada 1 ya oyó voz: en trozos sin voz Whisper se inventa «Gracias por ver
            # el video», «¡Suscríbete al canal!»…
            parecido = SequenceMatcher(None, [_n(w["w"]) for w in p1], [_n(w["w"]) for w in p2]).ratio()
            if p1 and parecido >= 0.5 and (len(p2) > len(p1) or (larga and len(p2) >= len(p1))):
                palabras += p2
                literales.append([a, b, " ".join(w["w"] for w in p1), " ".join(w["w"] for w in p2)])
            else:
                palabras += p1
        # Palabras de la pasada 1 que no cayeron en ningún trozo (voz muy débil): se conservan.
        vistas = {id(w) for w in palabras}
        for w in completa:
            c = (w["inicio"] + w["fin"]) / 2
            if id(w) not in vistas and not any(a <= c < b for a, b in trozos):
                palabras.append(w)
        palabras.sort(key=lambda w: w["inicio"])
        # Frontera entre trozos: la misma palabra puede venir de las dos pasadas («es» + «Es»).
        limpias: list[dict] = []
        for w in palabras:
            prev = limpias[-1] if limpias else None
            if prev and _n(prev["w"]) == _n(w["w"]) and w["inicio"] < prev["fin"] - 0.5 * min(
                    prev["fin"] - prev["inicio"], w["fin"] - w["inicio"]):
                continue
            limpias.append(w)
        palabras = limpias

    # Alucinaciones: palabras donde el audio NO tiene voz (prueba02: «Gracias por ver el video» sobre el
    # silencio final, con «ver» de 4,5 s). Se descartan si su pico está 30 dB por debajo de la voz.
    hop = SR // 100
    n = len(audio) // hop
    env = 20 * np.log10(np.sqrt((audio[: n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)
    picos = [env[int(w["inicio"] * 100):max(int(w["fin"] * 100), int(w["inicio"] * 100) + 1)].max(initial=-200)
             for w in palabras]
    voz = float(np.percentile(picos, 75)) if picos else 0.0
    fantasmas = [w for w, pk in zip(palabras, picos) if pk < voz - 30]
    if fantasmas:
        print(f"  ✂ {len(fantasmas)} palabras sin voz debajo (alucinación): "
              f"«{' '.join(w['w'] for w in fantasmas)[:120]}»")
    palabras = [w for w, pk in zip(palabras, picos) if pk >= voz - 30]

    for i, w in enumerate(palabras):
        w["i"] = i
        w["seg"] = next((k for k, s in enumerate(segmentos) if w["inicio"] < s["fin"]), len(segmentos) - 1)
    print(f"Transcrito {dur:.1f} s en {time.time() - t0:.1f} s con {modelo}: {len(palabras)} palabras"
          + (f" ({len(literales)} trozos con la pasada literal)" if literales else ""))
    for a, b, antes, despues in literales:
        print(f"  ↺ {a:7.2f}–{b:7.2f} s\n      completa: «{antes}»\n      literal:  «{despues}»")
    return {"fuente": str(ruta), "duracion": round(dur, 3), "modelo": modelo, "idioma": idioma,
            "trozos_literales": literales, "segmentos": segmentos,
            "palabras": [{k: w[k] for k in ("i", "w", "inicio", "fin", "prob", "seg", "pasada")} for w in palabras]}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("fuente", type=Path)
    p.add_argument("salida", type=Path)
    p.add_argument("--modelo")
    p.add_argument("--pista", type=int, default=0, help="índice de la pista de audio (0 = primera)")
    p.add_argument("--una-pasada", action="store_true", help="solo la pasada completa (más rápido)")
    a = p.parse_args()
    escribir_json(a.salida, transcribir(a.fuente, a.modelo, a.pista, a.una_pasada))
    print(f"→ {a.salida}")


if __name__ == "__main__":
    main()
