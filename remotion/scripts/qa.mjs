// Fotogramas de control (QA) sin re-empaquetar para cada uno.
//   node scripts/qa.mjs <Composición> <guion.json relativo a videos/> <seg1> <seg2> … [--nombre prefijo]
// Guarda out/qa/<prefijo>_<seg>s.jpg
import path from "node:path";
import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";

const args = process.argv.slice(2);
const iNombre = args.indexOf("--nombre");
const prefijo = iNombre >= 0 ? args.splice(iNombre, 2)[1] : "qa";
const [id, guion, ...segs] = args;
const raiz = path.resolve(import.meta.dirname, "..");
const out = path.resolve(raiz, "..", "out", "qa");
const serveUrl = await bundle({ entryPoint: path.join(raiz, "src", "index.ts"), publicDir: path.resolve(raiz, "..", "videos") });
const inputProps = { guion };
const composition = await selectComposition({ serveUrl, id, inputProps });
for (const s of segs) {
  const frame = Math.min(composition.durationInFrames - 1, Math.round(Number(s) * 30));
  const output = path.join(out, `${prefijo}_${s}s.jpg`);
  await renderStill({ composition, serveUrl, output, frame, inputProps, imageFormat: "jpeg", jpegQuality: 88, timeoutInMilliseconds: 180000 });
  console.log(`✔ ${path.relative(path.resolve(raiz, ".."), output)}`);
}
