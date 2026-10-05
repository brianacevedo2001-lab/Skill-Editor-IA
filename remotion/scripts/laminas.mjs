// Renderiza todas las láminas de LinkedIn de un guion empaquetando una sola vez.
//   node scripts/laminas.mjs <id>/linkedin.json <carpeta de salida>
// Escribe lamina_01.png … y imagen.png (la imagen suelta).
import fs from "node:fs";
import path from "node:path";
import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";

const [guion, salida] = process.argv.slice(2);
const raiz = path.resolve(import.meta.dirname, "..");
const videos = path.resolve(raiz, "..", "videos");
const datos = JSON.parse(fs.readFileSync(path.join(videos, guion), "utf-8"));
fs.mkdirSync(salida, { recursive: true });
const serveUrl = await bundle({ entryPoint: path.join(raiz, "src", "index.ts"), publicDir: videos });
const indices = [...datos.carrusel.map((_, i) => i), -1];
for (const indice of indices) {
  const inputProps = { guion, indice };
  const composition = await selectComposition({ serveUrl, id: "Lamina", inputProps });
  const nombre = indice < 0 ? "imagen.png" : `lamina_${String(indice + 1).padStart(2, "0")}.png`;
  await renderStill({ composition, serveUrl, output: path.join(salida, nombre), frame: 0, inputProps, imageFormat: "png", timeoutInMilliseconds: 180000 });
  console.log(`✔ ${nombre}`);
}
