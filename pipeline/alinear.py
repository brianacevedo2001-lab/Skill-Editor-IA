"""Alineación forzada: recoloca cada palabra de <parte>.palabras_corte.json sobre la voz YA CORTADA.

Uso:
  python pipeline/alinear.py videos/<id>/<parte>          (intro, grueso, vertical, datos…)
  python pipeline/alinear.py videos/<id>/<parte> --deshacer

Whisper da tiempos de palabra aproximados (a veces una palabra de 4 s o una corta a destiempo): las escenas ancladas
a palabras y los subtítulos de los shorts heredan ese error. Aquí el texto ya se sabe (lo que quedó tras 03_tomas y el
corte), así que solo hay que encontrar DÓNDE se dice cada palabra: modelo MMS_FA de torchaudio (wav2vec2 multilingüe,
CTC) + `forced_align`, por ventanas de ~25 s cortadas en las pausas más largas.

- Texto → caracteres del modelo: minúsculas sin tildes, ñ → n, números y símbolos a palabras en español
  (`PRONUNCIA` para siglas y nombres que se leen distinto de como se escriben).
- Una palabra que no se puede alinear (sin letras, o con puntuación del modelo muy baja) conserva el tiempo de Whisper
  ajustado entre sus vecinas.
- Guarda la versión de Whisper en <parte>.palabras_corte.whisper.json (con --deshacer se restaura) y escribe
  <parte>.alineacion.json con el desplazamiento y la confianza de cada palabra. Cada palabra lleva "al": 1/0
  (alineada o no); un palabras_corte.json sin "al" es uno recién salido del corte y se toma como el de Whisper.
- 01_cut_silences y 04_grueso lo llaman solos al terminar (--sin-alinear para no hacerlo).
Idea de una skill de referencia (alineación forzada con MMS_FA), reimplementada aquí.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

import numpy as np

from comun import FFMPEG, escribir_json, leer_json

SR = 16000
VENTANA = 25.0        # s de audio por pasada (cabe de sobra en 8 GB y no pierde precisión)
MARGEN = 0.6          # s de audio extra a cada lado de la ventana
CONF_MIN = 0.12       # puntuación media por debajo de la cual se desconfía de la alineación

# Siglas y nombres que se pronuncian distinto de como se escriben (minúsculas, sin tildes).
PRONUNCIA = {
    "ia": "ia", "ai": "ei ai", "crm": "ce erre eme", "erp": "e erre pe", "pdf": "pe de efe", "api": "api",
    "whatsapp": "guasap", "linkedin": "linquedin", "youtube": "iutub",
    "chatgpt": "chat ge pe te", "gpt": "ge pe te", "claude": "clod", "excel": "exel", "google": "gugel",
    "tiktok": "tictoc", "instagram": "instagram", "hubspot": "jabspot", "make": "meik", "zapier": "zapier",
    "n8n": "ene ocho ene", "saas": "sas", "kpi": "ka pe i", "roi": "roi", "b2b": "be tu be",
}

UNIDADES = ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once", "doce",
            "trece", "catorce", "quince", "dieciseis", "diecisiete", "dieciocho", "diecinueve", "veinte",
            "veintiuno", "veintidos", "veintitres", "veinticuatro", "veinticinco", "veintiseis", "veintisiete",
            "veintiocho", "veintinueve"]
DECENAS = ["", "", "", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"]
CENTENAS = ["", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos", "setecientos",
            "ochocientos", "novecientos"]


def numero(n: int) -> str:
    """Entero a palabras en español (sin tildes, que el modelo no las usa)."""
    if n < 30:
        return UNIDADES[n]
    if n < 100:
        d, u = divmod(n, 10)
        return DECENAS[d] + (f" y {UNIDADES[u]}" if u else "")
    if n < 1000:
        c, r = divmod(n, 100)
        return "cien" if n == 100 else CENTENAS[c] + (f" {numero(r)}" if r else "")
    if n < 1_000_000:
        m, r = divmod(n, 1000)
        return ("mil" if m == 1 else f"{numero(m)} mil") + (f" {numero(r)}" if r else "")
    m, r = divmod(n, 1_000_000)
    return ("un millon" if m == 1 else f"{numero(m)} millones") + (f" {numero(r)}" if r else "")


def a_letras(palabra: str) -> str:
    """Una palabra de la transcripción → texto que el modelo sabe alinear (a-z, apóstrofo, espacios)."""
    t = palabra.lower().strip()
    t = t.replace("%", " por ciento").replace("€", " euros").replace("$", " dolares").replace("&", " y ")
    t = t.replace("+", " mas ").replace("@", " arroba ")
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    limpio = re.sub(r"[^a-z0-9' ]", " ", t).strip()
    if limpio.replace(" ", "") in PRONUNCIA:
        return PRONUNCIA[limpio.replace(" ", "")]

    def num(m: re.Match) -> str:
        s = m.group(0)
        return numero(int(s)) if len(s) <= 9 else " ".join(numero(int(c)) for c in s)

    # 1.500 / 1,5 → «mil quinientos» / «uno coma cinco»
    t = re.sub(r"(\d)\.(\d{3})", r"\1\2", t)
    t = re.sub(r"(\d+),(\d+)", lambda m: f"{m.group(1)} coma {m.group(2)}", t)
    t = re.sub(r"\d+", num, t)
    t = re.sub(r"[^a-z' ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def leer_audio(ruta: Path) -> np.ndarray:
    r = subprocess.run([FFMPEG, "-v", "error", "-i", str(ruta), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).copy()


def fuera_del_corte(pal: list[dict]) -> set[int]:
    """Palabras que no están en el audio cortado: tramos quitados a mano o tomas descartadas que el mapa del corte
    aplasta en un instante (≥ 3 seguidas con el mismo inicio y fin)."""
    res, k = set(), 0
    while k < len(pal):
        j = k
        while (j + 1 < len(pal) and pal[j + 1]["inicio"] == pal[k]["inicio"]
               and pal[j + 1]["fin"] == pal[j + 1]["inicio"] and pal[k]["fin"] == pal[k]["inicio"]):
            j += 1
        if j - k + 1 >= 3:
            res.update(range(k, j + 1))
        k = j + 1
    return res


def ventanas(pal: list[dict], idx: list[int], dur: float) -> list[tuple[list[int], float, float]]:
    """Grupos de ~VENTANA s partidos en la pausa más larga cerca del límite. El audio de cada grupo llega hasta la
    mitad de la pausa con el grupo vecino (+ MARGEN): todo el audio se mira aunque Whisper dé tiempos malos."""
    grupos, i = [], 0
    while i < len(idx):
        j = i
        while j + 1 < len(idx) and pal[idx[j + 1]]["fin"] - pal[idx[i]]["inicio"] < VENTANA:
            j += 1
        if j + 1 < len(idx) and j > i:
            desde = i + max(1, (j - i) * 2 // 3)
            j = max(range(desde, j + 1), key=lambda q: pal[idx[q + 1]]["inicio"] - pal[idx[q]]["fin"])
        grupos.append(idx[i:j + 1])
        i = j + 1
    res = []
    for g, grupo in enumerate(grupos):
        a = 0.0 if g == 0 else (pal[grupos[g - 1][-1]]["fin"] + pal[grupo[0]]["inicio"]) / 2 - MARGEN
        b = dur if g == len(grupos) - 1 else (pal[grupo[-1]]["fin"] + pal[grupos[g + 1][0]]["inicio"]) / 2 + MARGEN
        res.append((grupo, max(0.0, a), min(dur, b)))
    return res


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("base", type=Path, help="videos/<id>/<parte> (sin extensión)")
    p.add_argument("--deshacer", action="store_true")
    a = p.parse_args()

    ruta = a.base.with_name(a.base.name + ".palabras_corte.json")
    copia = a.base.with_name(a.base.name + ".palabras_corte.whisper.json")
    if a.deshacer:
        shutil.copyfile(copia, ruta)
        print(f"→ restaurado {ruta} (tiempos de Whisper)")
        return
    if not copia.exists() or not any("al" in w for w in leer_json(ruta)):
        shutil.copyfile(ruta, copia)             # recién salido del corte: esos son los tiempos de Whisper
    pal = leer_json(copia)                       # siempre desde los tiempos de Whisper (repetible)
    voz = leer_audio(a.base.with_name(a.base.name + ".voz.wav"))
    dur = len(voz) / SR

    import torch
    import torchaudio
    import torchaudio.functional as F
    bundle = torchaudio.pipelines.MMS_FA
    disp = "cuda" if torch.cuda.is_available() else "cpu"
    modelo = bundle.get_model(with_star=False).to(disp).eval()
    dic = bundle.get_dict(star=None)
    ratio = bundle.sample_rate / SR

    letras = [a_letras(w["w"]) for w in pal]
    fuera = fuera_del_corte(pal)
    nuevo: list[tuple[float, float, float] | None] = [None] * len(pal)
    for idx, ta, tb in ventanas(pal, [k for k in range(len(pal)) if letras[k] and k not in fuera], dur):
        trozo = torch.from_numpy(voz[int(ta * SR):int(tb * SR)]).to(disp)[None]
        if ratio != 1:
            trozo = torchaudio.functional.resample(trozo, SR, bundle.sample_rate)
        with torch.inference_mode():
            emision, _ = modelo(trozo)
        # cada palabra puede ser varias «palabras» del modelo («por ciento»): se alinean juntas
        trozos = [letras[k].split() for k in idx]
        tokens = [dic[c] for t in trozos for sub in t for c in sub if c in dic]
        if len(tokens) == 0 or emision.shape[1] < len(tokens):
            continue
        alin, puntos = F.forced_align(emision, torch.tensor([tokens], dtype=torch.int32, device=disp), blank=0)
        spans = F.merge_tokens(alin[0], puntos[0].exp())
        seg = emision.shape[1] / (trozo.shape[1] / bundle.sample_rate)     # fotogramas del modelo por segundo
        pos = 0
        for k, t in zip(idx, trozos):
            n = sum(len([c for c in sub if c in dic]) for sub in t)
            sp = spans[pos:pos + n]
            pos += n
            if not sp:
                continue
            conf = float(np.mean([s.score for s in sp]))
            nuevo[k] = (ta + sp[0].start / seg, ta + sp[-1].end / seg, conf)

    # Montaje: confiar en la alineación salvo puntuación muy baja; las demás, Whisper encajado entre vecinas.
    fiable = [bool(n and n[2] >= CONF_MIN) for n in nuevo]
    k = 0
    while k < len(pal):
        if nuevo[k] and not fiable[k]:
            j = k
            while j + 1 < len(pal) and nuevo[j + 1] and not fiable[j + 1]:
                j += 1
            antes = k > 0 and nuevo[k - 1] and nuevo[k - 1][2] >= 0.5
            despues = j + 1 < len(pal) and nuevo[j + 1] and nuevo[j + 1][2] >= 0.5
            if antes and despues and j - k < 5:
                for q in range(k, j + 1):
                    fiable[q] = True
            k = j + 1
        else:
            k += 1
    salida, informe = [], []
    for k, w in enumerate(pal):
        n = nuevo[k]
        if fiable[k]:
            ini, fin, conf = n
        else:
            ini, fin, conf = w["inicio"], w["fin"], n[2] if n else 0.0
        salida.append({**w, "inicio": round(ini, 3), "fin": round(max(fin, ini + 0.02), 3), "al": int(fiable[k])})
        informe.append({"i": w["i"], "w": w["w"], "conf": round(conf, 2),
                        "desplazamiento": round(ini - w["inicio"], 3), "alineada": fiable[k],
                        "fuera_del_corte": k in fuera})
    # CTC marca el fin en el último carácter reconocido, antes de que se apague la voz: alargar el fin mientras haya
    # voz (energía a 10 ms), sin pasar del inicio de la siguiente ni +0,35 s.
    hop = SR // 100
    nf = len(voz) // hop
    db = 10 * np.log10((voz[:nf * hop].reshape(nf, hop) ** 2).mean(1) + 1e-12)
    hay_voz = db > np.percentile(db, 95) - 24
    for k, w in enumerate(salida):
        if not informe[k]["alineada"]:
            continue
        tope = min(salida[k + 1]["inicio"] if k + 1 < len(salida) else dur, w["fin"] + 0.35)
        q = int(w["fin"] * 100)
        while q < nf and (q + 1) / 100 <= tope and hay_voz[q]:
            q += 1
        w["fin"] = round(max(w["fin"], min(q / 100, tope)), 3)
    for k in range(1, len(salida)):                 # orden y sin solapes
        if salida[k]["inicio"] < salida[k - 1]["fin"]:
            if salida[k]["inicio"] >= salida[k - 1]["inicio"]:
                salida[k - 1]["fin"] = salida[k]["inicio"]
            else:
                salida[k]["inicio"] = salida[k - 1]["fin"]
                salida[k]["fin"] = max(salida[k]["fin"], salida[k]["inicio"] + 0.02)

    escribir_json(ruta, salida)
    escribir_json(a.base.with_name(a.base.name + ".alineacion.json"), informe)
    desp = np.abs([r["desplazamiento"] for r in informe if r["alineada"]])
    sin = [r for r in informe if not r["alineada"] and not r["fuera_del_corte"]]
    print(f"{len(pal)} palabras ({len(fuera)} fuera del corte) · {len(pal) - len(fuera) - len(sin)} alineadas ({disp}) · desplazamiento mediano "
          f"{np.median(desp) * 1000:.0f} ms · > 150 ms: {int((desp > 0.15).sum())} · > 500 ms: {int((desp > 0.5).sum())}")
    if sin:
        print("  sin alinear (se queda el tiempo de Whisper): " + ", ".join(f"«{r['w']}»" for r in sin[:15])
              + (" …" if len(sin) > 15 else ""))
    print(f"→ {ruta}  (Whisper en {copia.name})")


if __name__ == "__main__":
    main()
