"""Traslada los tiempos de un guion ya escrito cuando se vuelve a cortar el clip.

Uso:
  python pipeline/remap_times.py <viejo.cuts.json> <nuevo.cuts.json> <guion.json> [<salida.json>]
  (sin salida, sobrescribe el guion y deja una copia <guion>.bak.json)

Cada tiempo va: corte viejo → bruto (inverso del mapa viejo) → corte nuevo (mapa nuevo).
Se trasladan las claves `from`, `to`, `at`, y cualquier clave que termine en `At`
(`strikeAt`, `subscribeAt`, `bellAt`, `commentAt`…), sean números o listas de números, a cualquier
profundidad del JSON. Si un instante cae en un trozo que el corte nuevo ya no tiene, se lleva al
siguiente instante conservado y se avisa.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from comun import escribir_json, leer_json


def corte_a_bruto(t: float, segs: list[dict]) -> float:
    for s in segs:
        if t <= s["cut"][1]:
            return s["src"][0] + max(t - s["cut"][0], 0)
    return segs[-1]["src"][1]


def bruto_a_corte(t: float, segs: list[dict]) -> tuple[float, bool]:
    """Devuelve (tiempo en el corte, estaba_dentro)."""
    for s in segs:
        if t < s["src"][0]:
            return s["cut"][0], False
        if t <= s["src"][1]:
            return s["cut"][0] + (t - s["src"][0]), True
    return segs[-1]["cut"][1], False


def es_clave_tiempo(k: str) -> bool:
    return k in ("from", "to", "at") or k.endswith("At")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("viejo", type=Path)
    p.add_argument("nuevo", type=Path)
    p.add_argument("guion", type=Path)
    p.add_argument("salida", type=Path, nargs="?")
    a = p.parse_args()

    viejo, nuevo = leer_json(a.viejo)["segmentos"], leer_json(a.nuevo)["segmentos"]
    guion = leer_json(a.guion)
    cambios, avisos = 0, []

    def mover(t: float, ruta: str) -> float:
        nonlocal cambios
        nt, dentro = bruto_a_corte(corte_a_bruto(t, viejo), nuevo)
        nt = round(nt, 3)
        if not dentro:
            avisos.append(f"{ruta}: {t:.3f} s cae en un trozo eliminado → {nt:.3f} s")
        if abs(nt - t) > 1e-3:
            cambios += 1
        return nt

    def recorrer(x, ruta="$"):
        if isinstance(x, dict):
            return {k: (mover_valor(v, f"{ruta}.{k}") if es_clave_tiempo(k) else recorrer(v, f"{ruta}.{k}"))
                    for k, v in x.items()}
        if isinstance(x, list):
            return [recorrer(v, f"{ruta}[{i}]") for i, v in enumerate(x)]
        return x

    def mover_valor(v, ruta):
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return mover(float(v), ruta)
        if isinstance(v, list):
            return [mover_valor(e, f"{ruta}[{i}]") for i, e in enumerate(v)]
        return v

    res = recorrer(guion)
    salida = a.salida or a.guion
    if not a.salida:
        shutil.copyfile(a.guion, a.guion.with_suffix(".bak.json"))
    escribir_json(salida, res)
    for av in avisos:
        print("  ⚠", av)
    print(f"{cambios} tiempos trasladados → {salida}")


if __name__ == "__main__":
    main()
