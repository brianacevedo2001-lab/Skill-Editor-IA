"""LinkedIn: carrusel PDF, imagen suelta y texto del post (el vídeo 4:5 lo hace 09_shorts.py).

Uso:
  python pipeline/10_linkedin.py <id> [--sin-drive]

Lee videos/<id>/linkedin.json:
  {
    "post": "texto del post (gancho en la 1.ª línea, saltos de línea cortos, 3–5 hashtags al final)",
    "carrusel": [
      {"tipo": "portada", "kicker": "<nombre de la serie> · 1", "titulo": "La venta se gana en los *primeros minutos*"},
      {"tipo": "idea", "numero": 1, "titulo": "…", "texto": "…", "logo": "whatsapp"},
      {"tipo": "dato", "valor": "4 h", "titulo": "al día respondiendo *a mano*"},
      {"tipo": "cierre", "titulo": "…", "cta": "Video completo en YouTube"}
    ],
    "imagen": { …una lámina con la misma forma, para un post de imagen suelta… }
  }
Salidas en out/entregas/<id>/linkedin/: <id>_carrusel.pdf (+ PNG por lámina), <id>_imagen.png, <id>_post.txt.
Se copia SIEMPRE a Drive (final/<id>/linkedin/) salvo --sin-drive.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from PIL import Image

from comun import MARCA, OUT, RAIZ, VIDEOS, copiar_reanudable, leer_json


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("id")
    p.add_argument("--sin-drive", action="store_true")
    a = p.parse_args()

    guion = VIDEOS / a.id / "linkedin.json"
    cfg = leer_json(guion)
    salida = OUT / "entregas" / a.id / "linkedin"
    tmp = OUT / "linkedin" / a.id
    print(f"Renderizando {len(cfg['carrusel'])} láminas + imagen…")
    r = subprocess.run(["node", "scripts/laminas.mjs", f"{a.id}/linkedin.json", str(tmp)], cwd=RAIZ / "remotion",
                       shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        sys.exit(f"Remotion falló:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")

    salida.mkdir(parents=True, exist_ok=True)
    laminas = sorted(tmp.glob("lamina_*.png"))
    paginas = [Image.open(x).convert("RGB") for x in laminas]
    pdf = salida / f"{a.id}_carrusel.pdf"
    paginas[0].save(pdf, save_all=True, append_images=paginas[1:], resolution=150)
    for x in laminas:
        Image.open(x).convert("RGB").save(salida / f"{a.id}_{x.stem}.jpg", quality=92)
    Image.open(tmp / "imagen.png").convert("RGB").save(salida / f"{a.id}_imagen.jpg", quality=92)
    (salida / f"{a.id}_post.txt").write_text(cfg.get("post", "").strip() + "\n", encoding="utf-8")
    print(f"✔ {pdf.name} ({len(paginas)} páginas, {pdf.stat().st_size / 1e6:.1f} MB) · {a.id}_imagen.jpg · {a.id}_post.txt")

    if not a.sin_drive:
        destino = Path(leer_json(MARCA / "proyecto.json")["entregas"]["carpetaLocalDrive"]) / a.id / "linkedin"
        for f in sorted(x for x in salida.iterdir() if x.is_file()):
            copiar_reanudable(f, destino / f.name)
        print(f"Copiado a {destino}")


if __name__ == "__main__":
    main()
