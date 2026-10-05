"""Genera la librería de efectos de sonido y el grano de película, sin descargas ni créditos.

Uso:  python pipeline/sfx_generar.py

Sonido minimalista y de intriga (nada de «pops»):
  sub_hit     golpe grave (sub de 45 Hz con caída)            → entradas a pantalla completa, impacto de logo
  tick        tic seco y agudo                                → cada palabra que entra, celdas de la cuadrícula
  swell       subida de ruido filtrado + tono (1,2 s)         → antes de una revelación
  nota        nota suave tipo campana (La / Mi)               → rótulos, fichas
  whoosh      barrido suave de ruido                          → transiciones, salida de fichas
  fade_out    «desvanecer»: nota grave que baja de tono       → strikeAt / negar algo
  click       clic de ratón                                   → subscribe (cursor)
  campana     campanita de notificación                       → subscribe (campana)
  tecla       tecleo                                          → subscribe (comentario)
Ampliación (2026-10-02, ideas de una skill de referencia reimplementadas aquí, todo sintetizado):
  golpe / golpe_corto / impacto     nombre, logo o cifra que entra con fuerza; revelados (impacto = el más grande)
  aire / aire_salida / barrido      pieza que entra / sale / viaja; transicion = cambio de plano
  tick_suave / bip / descarte       elementos en serie, contadores, algo que se descarta
  ping / brillo / nota_doble        acierto, «gratis», «listo», algo que se enciende
  notificacion                      un mensaje de chat que entra (dos tonos)
  tecleo                            un buscador o un prompt que se escribe (ráfaga de teclas)
  subida                            anticipación larga (4,8 s): termina en el golpe (ancla «fin»)
  corte                             transición seca de cuchilla
  glitch / glitch_fuerte / fallo    cambio digital, algo que falla (poco)
Todos a 48 kHz, sin silencio inicial y con el pico normalizado (−3 dBFS; los ticks −9 dBFS).
Además de <nombre>.wav (mono) salen <nombre>_izq.wav y <nombre>_der.wav (estéreo, paneo ±0,6 de potencia constante)
y videos/_shared/sfx/sonidos.json + remotion/src/sonidos.json: duración, dónde cae el golpe (pico), con qué se alinea
(ancla: inicio | pico | fin) y la ganancia de su familia (gain_db) para que todas suenen parejas bajo la voz.

Grano: videos/_shared/fx/grano_*.png (6 fotogramas de ruido que se alternan).
"""
from __future__ import annotations

import wave

import numpy as np
from PIL import Image

from comun import VIDEOS

SR = 48000
DIR = VIDEOS / "_shared" / "sfx"
FX = VIDEOS / "_shared" / "fx"
rng = np.random.default_rng(7)


def t(d):
    return np.arange(int(d * SR)) / SR


def env(d, a=0.005, r=None, curva=4.0):
    x = t(d)
    e = np.minimum(x / max(a, 1e-4), 1.0)
    return e * np.exp(-curva * x / (r or d))


def paso_bajo(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


META: dict[str, dict] = {}
FAMILIA_DB = {"golpe": 0.0, "aire": -3.0, "tick": -2.0, "nota": -4.0, "aviso": -2.0, "tecla": -4.0, "subida": -4.0,
              "corte": -3.0, "glitch": -6.0}


def _wav(ruta, canales):
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(canales.shape[1]); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(canales, -1, 1) * 32767).astype("<i2").tobytes())


def guardar(nombre, x, pico_db=-3.0, familia="golpe", ancla="inicio"):
    x = np.asarray(x, dtype=np.float64)
    nz = np.flatnonzero(np.abs(x) > 1e-4)          # sin silencio inicial
    x = x[nz[0]:] if len(nz) else x
    x = x / (np.abs(x).max() + 1e-12) * 10 ** (pico_db / 20)
    n = int(0.004 * SR)
    x[-n:] *= np.linspace(1, 0, n)
    DIR.mkdir(parents=True, exist_ok=True)
    _wav(DIR / f"{nombre}.wav", x[:, None])
    for lado, pan in (("izq", -0.6), ("der", 0.6)):            # potencia constante
        ang = (pan + 1) * np.pi / 4
        _wav(DIR / f"{nombre}_{lado}.wav", np.stack([x * np.cos(ang), x * np.sin(ang)], axis=1) * np.sqrt(2))
    env_ = np.convolve(np.abs(x), np.ones(int(0.005 * SR)) / int(0.005 * SR), mode="same")
    META[nombre] = {"dur": round(len(x) / SR, 3), "pico": round(float(np.argmax(env_)) / SR, 3), "ancla": ancla,
                    "familia": familia, "gain_db": FAMILIA_DB.get(familia, 0.0)}
    print(f"  {nombre:<14} {len(x) / SR:5.2f} s  pico {pico_db:+.0f} dBFS  golpe en {META[nombre]['pico']:.3f} s")


def main():
    d = 1.4; x = t(d)
    f = 45 * np.exp(-x * 1.2) + 20                    # sub que cae de tono
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(d, 0.003, 0.9, 3.2)
    guardar("sub_hit", sub + 0.15 * paso_bajo(rng.standard_normal(len(x)), 900) * env(d, 0.001, 0.08, 8), familia="golpe")

    d = 0.06; x = t(d)
    guardar("tick", (np.sin(2 * np.pi * 3200 * x) + 0.3 * rng.standard_normal(len(x))) * env(d, 0.0005, 0.02, 6), -9, familia="tick")

    d = 1.3; x = t(d)
    rampa = (x / d) ** 2.5
    ruido = paso_bajo(rng.standard_normal(len(x)), 2500) * rampa
    tono = np.sin(2 * np.pi * (110 + 220 * rampa) * x) * rampa * 0.5
    sw = (ruido + tono) * np.minimum((d - x) / 0.04, 1)
    guardar("swell", sw, -6, familia="subida")

    for nombre, fr in (("nota", 880.0), ("nota_mi", 659.25)):
        d = 1.6; x = t(d)
        nota = sum(a * np.sin(2 * np.pi * fr * k * x) for k, a in ((1, 1), (2, .35), (3, .12), (4.2, .06)))
        guardar(nombre, nota * env(d, 0.004, 1.0, 5), -8, familia="nota")

    d = 0.7; x = t(d)
    fc = 300 + 2600 * np.sin(np.pi * x / d)
    wh = np.zeros(len(x)); acc = 0.0; ruido = rng.standard_normal(len(x))
    for i in range(len(x)):
        a = np.exp(-2 * np.pi * fc[i] / SR); acc = (1 - a) * ruido[i] + a * acc; wh[i] = acc
    guardar("whoosh", wh * np.sin(np.pi * x / d) ** 2, -8, familia="aire")

    d = 1.1; x = t(d)
    f = 220 * np.exp(-x * 1.4)
    guardar("fade_out", np.sin(2 * np.pi * np.cumsum(f) / SR) * env(d, 0.01, 0.9, 3) * 0.8
            + 0.2 * paso_bajo(rng.standard_normal(len(x)), 600) * env(d, 0.01, 0.5, 4), -8, familia="nota")

    d = 0.03; x = t(d)
    guardar("click", (rng.standard_normal(len(x)) * 0.6 + np.sin(2 * np.pi * 1800 * x)) * env(d, 0.0003, 0.008, 5), -10, familia="tick")

    d = 1.5; x = t(d)
    cam = sum(np.sin(2 * np.pi * fr * x) * a for fr, a in ((1568, 1), (2093, .6), (3136, .25)))
    cam = cam * env(d, 0.002, 1.0, 5) + np.roll(cam * env(d, 0.002, 1.0, 5), int(0.12 * SR)) * 0.7
    guardar("campana", cam, -9, familia="nota")

    d = 0.045; x = t(d)
    guardar("tecla", (paso_bajo(rng.standard_normal(len(x)), 4000) + 0.3 * np.sin(2 * np.pi * 900 * x)) * env(d, 0.0005, 0.015, 5), -14, familia="tecla")

    nuevos()

    FX.mkdir(parents=True, exist_ok=True)
    for k in range(6):
        g = rng.normal(128, 38, (540, 960)).clip(0, 255).astype(np.uint8)
        Image.fromarray(g, "L").resize((1920, 1080), Image.BILINEAR).save(FX / f"grano_{k}.png")
    print(f"  grano: 6 fotogramas en {FX}")


def ruido_filtrado(n, fc):
    return paso_bajo(rng.standard_normal(n), fc)


def barrido_ruido(d, f0, f1, forma):
    x = t(d)
    fc = f0 + (f1 - f0) * forma(x / d)
    y = np.zeros(len(x)); acc = 0.0; r = rng.standard_normal(len(x))
    for i in range(len(x)):
        a = np.exp(-2 * np.pi * fc[i] / SR); acc = (1 - a) * r[i] + a * acc; y[i] = acc
    return y


def nuevos():
    # golpes
    d = 0.9; x = t(d)
    f = 70 * np.exp(-x * 6) + 42
    cuerpo = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(d, 0.002, 0.5, 4)
    guardar("golpe", cuerpo + 0.35 * ruido_filtrado(len(x), 1800) * env(d, 0.0005, 0.04, 10), -3, "golpe", "pico")
    d = 0.35; x = t(d)
    f = 120 * np.exp(-x * 14) + 60
    guardar("golpe_corto", np.sin(2 * np.pi * np.cumsum(f) / SR) * env(d, 0.001, 0.25, 5)
            + 0.25 * ruido_filtrado(len(x), 3000) * env(d, 0.0003, 0.02, 12), -4, "golpe", "pico")
    d = 2.6; x = t(d)
    f = 38 * np.exp(-x * 0.8) + 24
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(d, 0.004, 2.0, 3)
    cola = ruido_filtrado(len(x), 700) * env(d, 0.002, 1.6, 4) * 0.5
    guardar("impacto", boom + cola + 0.3 * ruido_filtrado(len(x), 5000) * env(d, 0.0003, 0.05, 10), -2, "golpe", "pico")
    # aire
    guardar("aire", barrido_ruido(0.55, 400, 3200, lambda u: u ** 1.5) * np.sin(np.pi * t(0.55) / 0.55 * 0.5) ** 2
            * np.minimum((0.55 - t(0.55)) / 0.03, 1), -9, "aire", "fin")
    guardar("aire_salida", barrido_ruido(0.5, 3000, 300, lambda u: u) * np.exp(-3 * t(0.5) / 0.5)
            * np.minimum(t(0.5) / 0.01, 1), -10, "aire", "inicio")
    d = 1.1
    guardar("barrido", barrido_ruido(d, 200, 6000, lambda u: np.sin(np.pi * u)) * np.sin(np.pi * t(d) / d) ** 2, -8, "aire", "pico")
    d = 0.8
    tr = barrido_ruido(d, 300, 4500, lambda u: u ** 2) * (t(d) / d) ** 2 * np.minimum((d - t(d)) / 0.02, 1)
    guardar("transicion", tr, -7, "aire", "fin")
    # ticks
    d = 0.05; x = t(d)
    guardar("tick_suave", np.sin(2 * np.pi * 2400 * x) * env(d, 0.0008, 0.02, 6), -14, "tick", "inicio")
    d = 0.12; x = t(d)
    guardar("bip", np.sin(2 * np.pi * 1320 * x) * np.minimum(x / 0.003, 1) * np.minimum((d - x) / 0.01, 1), -14, "tick", "inicio")
    d = 0.45; x = t(d)
    f = 520 * np.exp(-x * 5)
    guardar("descarte", np.sin(2 * np.pi * np.cumsum(f) / SR) * env(d, 0.003, 0.35, 4), -12, "tick", "inicio")
    # notas
    for nombre, frs in (("ping", (1760,)), ("nota_doble", (880, 1318.5))):
        d = 1.2; x = t(d); y = np.zeros(len(x))
        for k, fr in enumerate(frs):
            ini = int(k * 0.11 * SR)
            xx = t(d - k * 0.11)
            tono = sum(a * np.sin(2 * np.pi * fr * m * xx) for m, a in ((1, 1), (2, .3), (3, .1))) * env(d - k * 0.11, 0.002, 0.9, 5)
            n = min(len(y) - ini, len(tono))
            y[ini:ini + n] += tono[:n]
        guardar(nombre, y, -10, "nota", "inicio")
    d = 1.6; x = t(d)
    br = sum(np.sin(2 * np.pi * fr * x + k) * env(d, 0.002 + k * 0.03, 1.2, 5) for k, fr in enumerate((2637, 3136, 3951, 5274)))
    guardar("brillo", br + 0.1 * ruido_filtrado(len(x), 9000) * env(d, 0.002, 0.6, 5), -12, "nota", "inicio")
    # aviso: notificación de chat de dos tonos
    d = 0.6; y = np.zeros(int(d * SR))
    for k, fr in enumerate((1046.5, 1568)):
        ini = int(k * 0.13 * SR); xx = t(0.35)
        tono = (np.sin(2 * np.pi * fr * xx) + 0.25 * np.sin(2 * np.pi * 2 * fr * xx)) * env(0.35, 0.002, 0.3, 5)
        y[ini:ini + len(tono)] += tono[: len(y) - ini]
    guardar("notificacion", y, -8, "aviso", "inicio")
    # tecleo: ráfaga de teclas irregulares
    d = 1.4; y = np.zeros(int(d * SR)); pos = 0.0
    while pos < d - 0.06:
        xx = t(0.04)
        k = (ruido_filtrado(len(xx), 3500 + rng.uniform(-800, 800)) + 0.25 * np.sin(2 * np.pi * rng.uniform(700, 1100) * xx)) \
            * env(0.04, 0.0004, 0.012, 5) * rng.uniform(0.6, 1.0)
        i = int(pos * SR); y[i:i + len(k)] += k[: len(y) - i]
        pos += rng.uniform(0.07, 0.16)
    guardar("tecleo", y, -14, "tecla", "inicio")
    # subida larga
    d = 4.8; x = t(d)
    rampa = (x / d) ** 3
    sub = ruido_filtrado(len(x), 1200) * rampa + np.sin(2 * np.pi * (80 + 400 * rampa) * x) * rampa * 0.4
    guardar("subida", sub * np.minimum((d - x) / 0.03, 1), -6, "subida", "fin")
    # corte
    d = 0.28; x = t(d)
    guardar("corte", barrido_ruido(d, 6000, 800, lambda u: u) * env(d, 0.001, 0.2, 6)
            + 0.4 * np.sin(2 * np.pi * 90 * x) * env(d, 0.001, 0.12, 6), -6, "corte", "inicio")
    # glitch / fallo
    for nombre, d, dens in (("glitch", 0.35, 0.5), ("glitch_fuerte", 0.7, 0.8)):
        n = int(d * SR); y = np.zeros(n); i = 0
        while i < n:
            L = int(rng.uniform(0.008, 0.035) * SR)
            if rng.random() < dens:
                xx = np.arange(min(L, n - i)) / SR
                y[i:i + len(xx)] = np.sign(np.sin(2 * np.pi * rng.uniform(200, 2400) * xx)) * rng.uniform(0.3, 1)
            i += L
        guardar(nombre, y * env(d, 0.001, d, 2), -16, "glitch", "inicio")
    d = 0.5; x = t(d)
    guardar("fallo", (np.sign(np.sin(2 * np.pi * 140 * x)) * 0.5 + np.sin(2 * np.pi * 147 * x)) * env(d, 0.005, 0.45, 3), -14, "glitch", "inicio")


def escribir_meta():
    import json
    from comun import RAIZ
    datos = json.dumps(META, ensure_ascii=False, indent=1, sort_keys=True)
    (DIR / "sonidos.json").write_text(datos, encoding="utf-8")
    (RAIZ / "remotion" / "src" / "sonidos.json").write_text(datos, encoding="utf-8")
    print(f"  metadatos de {len(META)} sonidos → sonidos.json")


if __name__ == "__main__":
    main()
    escribir_meta()
