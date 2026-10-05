"""Sincroniza cámara ↔ pantalla correlando la envolvente del audio en ventanas de 20 s por TODO el vídeo.

Uso:
  python pipeline/05_sync.py <pantalla> <camara> <salida sync.json> [--max-desfase 180]

Resultado (tiempos de la PANTALLA, que es la referencia):
  {"tramos": [{"desde", "hasta", "desfase", "deriva"} | {"desde", "hasta", "sin_camara": true}],
   "palmada": {"pantalla", "camara", "desfase"}, "ventanas": [...]}
  t_camara = t_pantalla + desfase + deriva · (t_pantalla − desde)

- Envolvente de voz (300–3400 Hz) a 200 Hz, en log y sin la media lenta: resalta los ataques y es
  robusta aunque los micrófonos sean distintos (móvil vs micrófono USB).
- Si una de las grabaciones se paró, aparece un SALTO en el desfase entre ventanas; la frontera se pone
  en el silencio más largo entre esas ventanas. Ventanas sin correlación = tramo sin cámara.
- Dentro de cada tramo se ajusta una recta: el reloj del móvil y el del PC derivan (ms por minuto).
- La palmada (el ataque más fuerte de los primeros 20 s) sirve de comprobación cruzada.
"""
from __future__ import annotations

import argparse

import numpy as np

from comun import audio_16k, escribir_json

SR = 16000
TASA = 200            # muestras/s de la envolvente (5 ms)
VENTANA = 20.0        # s
PASO = 10.0           # s entre ventanas
BUSQUEDA = 30.0       # s alrededor del desfase global para buscar saltos
SALTO = 0.08          # s de diferencia entre ventanas que se considera salto (parada)
MIN_CORR = 0.35       # correlación mínima para fiarse de una ventana


def envolvente(audio: np.ndarray) -> np.ndarray:
    espectro = np.fft.rfft(audio)
    fq = np.fft.rfftfreq(len(audio), 1 / SR)
    espectro[(fq < 300) | (fq > 3400)] = 0
    voz = np.fft.irfft(espectro, n=len(audio))
    hop = SR // TASA
    n = len(voz) // hop
    rms = np.sqrt((voz[:n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12)
    e = np.log10(rms + 1e-4)
    lenta = np.convolve(e, np.ones(TASA) / TASA, mode="same")   # media de 1 s
    return (e - lenta).astype(np.float32)


def mejor_desfase(ref: np.ndarray, otra: np.ndarray, centro: int, radio: int) -> tuple[float, float]:
    """Busca `ref` (ventana de pantalla) dentro de `otra` alrededor de `centro` (muestras). Devuelve
    (posición en `otra` con precisión sub-muestra, correlación normalizada)."""
    a0 = max(0, centro - radio)
    a1 = min(len(otra), centro + radio + len(ref))
    trozo = otra[a0:a1]
    if len(trozo) < len(ref):
        return float("nan"), 0.0
    r = ref - ref.mean()
    c = np.correlate(trozo - trozo.mean(), r, mode="valid")
    # normalización por energía local de `trozo`
    acum = np.concatenate([[0], np.cumsum((trozo - trozo.mean()) ** 2)])
    energia = np.sqrt(np.maximum(acum[len(r):] - acum[:-len(r)], 1e-9)) * np.sqrt((r ** 2).sum() + 1e-9)
    cn = c / energia
    k = int(np.argmax(cn))
    fino = float(k)
    if 0 < k < len(cn) - 1:   # interpolación parabólica
        y0, y1, y2 = cn[k - 1], cn[k], cn[k + 1]
        den = y0 - 2 * y1 + y2
        if abs(den) > 1e-9:
            fino = k + 0.5 * (y0 - y2) / den
    return a0 + fino, float(cn[k])


def palmada(audio: np.ndarray) -> float:
    """Instante (s) de la palmada: el golpe más fuerte en AGUDOS (2–7 kHz) de los primeros 20 s.
    Una palmada es un golpe de banda ancha; los arranques de voz tienen la energía más abajo."""
    trozo = audio[: 20 * SR]
    esp = np.fft.rfft(trozo)
    fq = np.fft.rfftfreq(len(trozo), 1 / SR)
    esp[(fq < 2000) | (fq > 7000)] = 0
    agudos = np.fft.irfft(esp, n=len(trozo))
    hop = SR // TASA
    n = len(agudos) // hop
    e = 20 * np.log10(np.abs(agudos[: n * hop]).reshape(n, hop).max(1) + 1e-6)
    # El móvil arranca con ~0,8 s de silencio DIGITAL (−120 dB): sin este suelo, el primer ruido de sala
    # «sube» 60 dB y gana a la palmada (prueba01).
    e = np.maximum(e, np.percentile(e[e > -100] if (e > -100).any() else e, 20))
    # Ataque contra la mediana de los 300 ms anteriores (sin los últimos 20 ms): el golpe sube a lo largo
    # de varios fotogramas de 5 ms y ninguno por separado supera el umbral.
    base = np.array([np.median(e[max(0, i - 60):max(1, i - 4)]) for i in range(n)])
    ataque = e - base
    candidatos = np.flatnonzero(ataque >= 15)
    k = candidatos[np.argmax(e[candidatos])] if len(candidatos) else int(np.argmax(ataque))
    return float(k) / TASA


def corr_fija(ep: np.ndarray, ec: np.ndarray, t: float, largo: float, desfase: float) -> float:
    """Correlación normalizada de pantalla[t, t+largo] con cámara desplazada un desfase fijo."""
    a, b = int(t * TASA), int((t + largo) * TASA)
    c0 = int(round((t + desfase) * TASA))
    if a < 0 or c0 < 0 or b > len(ep) or c0 + (b - a) > len(ec):
        return float("nan")
    x, y = ep[a:b], ec[c0:c0 + (b - a)]
    if x.std() < 1e-3 or y.std() < 1e-3:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def silencio_cercano(audio: np.ndarray, t: float, hacia: int, radio: float = 1.5) -> float:
    """Silencio más cercano a `t` buscando solo hacia atrás (hacia=-1) o hacia delante (+1)."""
    hop = SR // 100
    a, b = (t - radio, t) if hacia < 0 else (t, t + radio)
    a = max(a, 0.0)
    seg = audio[int(a * SR): int(b * SR)]
    n = len(seg) // hop
    if n < 3:
        return t
    db = 20 * np.log10(np.sqrt((seg[: n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)
    sil = db < np.percentile(20 * np.log10(np.abs(audio[::hop]) + 1e-9), 35)
    idx = np.flatnonzero(sil)
    if not len(idx):
        return t
    k = idx[-1] if hacia < 0 else idx[0]
    return round(a + k / 100, 3)


def silencio_mas_largo(audio: np.ndarray, t0: float, t1: float) -> float:
    hop = SR // 100
    a, b = int(t0 * 100), int(t1 * 100)
    seg = audio[a * hop: b * hop]
    n = len(seg) // hop
    if n < 2:
        return (t0 + t1) / 2
    db = 20 * np.log10(np.sqrt((seg[: n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)
    sil = db < np.percentile(db, 30)
    mejor, largo, i = (t0 + t1) / 2, 0, 0
    while i < n:
        if sil[i]:
            j = i
            while j < n and sil[j]:
                j += 1
            if j - i > largo:
                largo, mejor = j - i, t0 + (i + j) / 200
            i = j
        else:
            i += 1
    return mejor


def sincronizar(pantalla, camara, max_desfase: float = 180.0) -> dict:
    ap, ac = audio_16k(pantalla), audio_16k(camara)
    ep, ec = envolvente(ap), envolvente(ac)
    dur = len(ap) / SR

    # 1) desfase global: una ventana de 60 s del CENTRO de la pantalla buscada en la cámara (así da igual
    #    cuál de las dos grabaciones empezó antes)
    largo = min(60.0, dur / 2)
    t_ref = max(0.0, dur / 2 - largo / 2)
    ref = ep[int(t_ref * TASA): int((t_ref + largo) * TASA)]
    pos, corr_g = mejor_desfase(ref, ec, int(t_ref * TASA), int(max_desfase * TASA))
    global_ = pos / TASA - t_ref
    print(f"Desfase global: cámara = pantalla {global_:+.3f} s  (correlación {corr_g:.2f})")

    # 2) ventanas de 20 s cada 10 s
    ventanas = []
    t = 0.0
    while t + VENTANA <= dur:
        a, b = int(t * TASA), int((t + VENTANA) * TASA)
        ref = ep[a:b]
        if np.std(ref) < 1e-3:
            t += PASO
            continue
        pos, c = mejor_desfase(ref, ec, int((t + global_) * TASA), int(BUSQUEDA * TASA))
        ventanas.append({"t": round(t + VENTANA / 2, 2), "desfase": round(pos / TASA - t, 4), "corr": round(c, 3)})
        t += PASO

    # 3) tramos: sin cámara / saltos de desfase
    tramos = []
    buenas = [v for v in ventanas if v["corr"] >= MIN_CORR]
    if not buenas:
        raise SystemExit("No encuentro correlación entre cámara y pantalla. ¿Son de la misma grabación?")
    grupo = [buenas[0]]
    grupos = []
    for v in buenas[1:]:
        if abs(v["desfase"] - np.median([g["desfase"] for g in grupo[-3:]])) > SALTO:
            grupos.append(grupo)
            grupo = [v]
        else:
            grupo.append(v)
    grupos.append(grupo)

    ajustes = []
    for g in grupos:
        ts = np.array([v["t"] for v in g])
        ds = np.array([v["desfase"] for v in g])
        deriva, base = np.polyfit(ts, ds, 1) if len(g) >= 3 else (0.0, float(np.median(ds)))
        ajustes.append((float(base), float(deriva)))
    en = lambda k, t: ajustes[k][0] + ajustes[k][1] * t

    # Frontera precisa entre grupos: ventanas de 2 s cada 0,25 s probando los dos desfases.
    #  - Último instante en que casa el desfase A → fin de A.  Primer instante en que casa B → inicio de B.
    #  - Si la cámara se paró, entre medias queda un HUECO sin cámara (dura lo que el salto).
    #  - Las fronteras se llevan a un silencio (A hacia atrás, B hacia delante): nunca a mitad de palabra.
    limites = []
    for k in range(len(grupos) - 1):
        t0, t1 = grupos[k][-1]["t"] - VENTANA / 2, grupos[k + 1][0]["t"] + VENTANA / 2
        fin_a, ini_b = t0, t1
        t = t0
        L = 2.0
        while t < t1:
            ca, cb = corr_fija(ep, ec, t, L, en(k, t)), corr_fija(ep, ec, t, L, en(k + 1, t))
            if not np.isnan(ca) and ca >= 0.5:
                fin_a = max(fin_a, t + L)
            if not np.isnan(cb) and cb >= 0.5 and ini_b == t1:
                ini_b = t
            t += 0.1
        # Conservador: media ventana hacia dentro a cada lado. Mejor unos instantes sin cámara en la
        # esquina que la cámara de otro momento.
        fin_a, ini_b = fin_a - L / 2, ini_b + L / 2
        if ini_b < fin_a:
            fin_a = ini_b = (fin_a + ini_b) / 2
        limites.append((silencio_cercano(ap, fin_a, -1), silencio_cercano(ap, ini_b, +1)))

    for k, g in enumerate(grupos):
        desde = 0.0 if k == 0 else limites[k - 1][1]
        hasta = dur if k + 1 == len(grupos) else limites[k][0]
        base, deriva = ajustes[k]
        if k > 0 and limites[k - 1][1] - limites[k - 1][0] > 0.3:
            tramos.append({"desde": limites[k - 1][0], "hasta": limites[k - 1][1], "sin_camara": True})
        tramos.append({"desde": round(desde, 3), "hasta": round(hasta, 3),
                       "desfase": round(base + deriva * desde, 4), "deriva": round(deriva, 7),
                       "ventanas": len(g)})

    # Huecos donde las ventanas no correlan (la cámara no grababa): se marcan sin cámara.
    malas = [v for v in ventanas if v["corr"] < MIN_CORR]
    for v in malas:
        print(f"  · ventana en {v['t']:7.1f} s sin correlación ({v['corr']:.2f}) — ¿cámara parada?")

    tp, tc = palmada(ap), palmada(ac)
    res = {"pantalla": str(pantalla), "camara": str(camara), "duracion": round(dur, 3), "tramos": tramos,
           "palmada": {"pantalla": round(tp, 3), "camara": round(tc, 3), "desfase": round(tc - tp, 3)},
           "ventanas": ventanas}
    print(f"Palmada: pantalla {tp:.3f} s · cámara {tc:.3f} s → desfase {tc - tp:+.3f} s")
    for tr in tramos:
        if tr.get("sin_camara"):
            print(f"  hueco {tr['desde']:8.2f}–{tr['hasta']:8.2f} s: SIN CÁMARA (solo pantalla)")
            continue
        print(f"  tramo {tr['desde']:8.2f}–{tr['hasta']:8.2f} s: desfase {tr['desfase']:+.4f} s, "
              f"deriva {tr['deriva'] * 60000:+.1f} ms/min ({tr['ventanas']} ventanas)")
    if abs((tc - tp) - tramos[0]["desfase"]) > 0.06:
        print("  ⚠ la palmada no coincide con el desfase del primer tramo: revisar")
    return res


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("pantalla")
    p.add_argument("camara")
    p.add_argument("salida")
    p.add_argument("--max-desfase", type=float, default=180.0)
    a = p.parse_args()
    escribir_json(a.salida, sincronizar(a.pantalla, a.camara, a.max_desfase))
    print(f"→ {a.salida}")


if __name__ == "__main__":
    main()
