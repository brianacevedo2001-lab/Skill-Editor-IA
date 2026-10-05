// Genera / amplía la librería de logos: videos/_shared/logos/<slug>.svg + index.json
//
//   node scripts/logos.mjs                      → (re)genera las marcas de la lista MARCAS
//   node scripts/logos.mjs añadir <simpleIconsSlug> "Alias 1" "Alias 2"   → añade una marca de Simple Icons
//   node scripts/logos.mjs oficial <slug> "<Nombre>" <#color> "<consulta>" "Alias 1" …  → logo oficial a color
//
// Cadena para logos oficiales a color (OFICIALES y las retiradas de Simple Icons): Lobe Icons (marcas de IA,
// jsDelivr @lobehub/icons-static-svg, variante «-color»), luego SVGL (api.svgl.app, variante oscura si la hay),
// luego Lobe monocromo (se pinta en blanco); si nada responde, monograma. Un logo a color lleva "logoColor": true
// y se pinta sobre la superficie oscura de la marca (no sobre su color). Idea de una skill de referencia.
//
// - Marcas de Simple Icons: SVG monocolor (se pinta en blanco sobre el color de la marca).
// - Marcas retiradas de Simple Icons (Excel, ChatGPT…): «monograma» (inicial sobre su color). Si luego
//   dejas el SVG oficial en videos/_shared/logos/<slug>.svg y pones "fondoPropio": true, se usa tal cual.
// - La marca propia (TuMarca) sale de marca/marca.json (isotipo PNG) — nunca fija en el código.
// - `bloqueados`: alias que son palabras comunes en español y NO deben disparar un logo.
import fs from "node:fs";
import path from "node:path";
import * as si from "simple-icons";

const RAIZ = path.resolve(import.meta.dirname, "..", "..");
const DIR = path.join(RAIZ, "videos", "_shared", "logos");
fs.mkdirSync(DIR, { recursive: true });
const INDEX = path.join(DIR, "index.json");

const MARCAS = [
  ["whatsapp", ["whatsapp", "whats app", "wasap", "guasap"]],
  ["instagram", ["instagram", "insta"]],
  ["messenger", ["messenger"]],
  ["telegram", ["telegram"]],
  ["facebook", ["facebook"]],
  ["youtube", ["youtube"]],
  ["tiktok", ["tiktok", "tik tok"]],
  ["googlesheets", ["google sheets", "hojas de cálculo de google"]],
  ["googledrive", ["google drive", "drive"]],
  ["googlecalendar", ["google calendar"]],
  ["gmail", ["gmail"]],
  ["shopify", ["shopify"]],
  ["woocommerce", ["woocommerce"]],
  ["wordpress", ["wordpress"]],
  ["stripe", ["stripe"]],
  ["mercadopago", ["mercado pago", "mercadopago"]],
  ["hubspot", ["hubspot"]],
  ["zapier", ["zapier"]],
  ["make", ["make.com"]],
  ["n8n", ["n8n"]],
  ["notion", ["notion"]],
  ["airtable", ["airtable"]],
  ["calendly", ["calendly"]],
  ["claude", ["claude"]],
  ["anthropic", ["anthropic"]],
  ["googlegemini", ["gemini"]],
  ["meta", ["meta"]],
  ["googleads", ["google ads"]],
  ["discord", ["discord"]],
  ["github", ["github"]],
];
// Retiradas de Simple Icons → monograma.
const MONOGRAMAS = [
  { slug: "excel", nombre: "Excel", color: "#217346", letra: "X", alias: ["excel"] },
  { slug: "chatgpt", nombre: "ChatGPT", color: "#10A37F", letra: "G", alias: ["chatgpt", "chat gpt", "openai"] },
  { slug: "canva", nombre: "Canva", color: "#00C4CC", letra: "C", alias: ["canva"] },
  { slug: "linkedin", nombre: "LinkedIn", color: "#0A66C2", letra: "in", alias: ["linkedin"] },
  { slug: "slack", nombre: "Slack", color: "#4A154B", letra: "S", alias: ["slack"] },
];
// Logos oficiales a color: [slug, nombre, color de marca, consulta Lobe/SVGL, alias]. Incluye las retiradas de
// Simple Icons (si la red falla, quedan como monograma).
const OFICIALES = [
  ["excel", "Excel", "#217346", "Microsoft Excel", ["excel"]],
  ["chatgpt", "ChatGPT", "#10A37F", "openai", ["chatgpt", "chat gpt", "openai"]],
  ["canva", "Canva", "#00C4CC", "Canva", ["canva"]],
  ["linkedin", "LinkedIn", "#0A66C2", "LinkedIn", ["linkedin"]],
  ["slack", "Slack", "#4A154B", "Slack", ["slack"]],
  ["google", "Google", "#4285F4", "Google", ["google"]],
  ["gemini", "Gemini", "#8E75B2", "gemini", ["gemini", "google gemini"]],
  ["deepseek", "DeepSeek", "#4D6BFE", "deepseek", ["deepseek", "deep seek"]],
  ["perplexity", "Perplexity", "#20808D", "perplexity", ["perplexity"]],
  ["mistral", "Mistral", "#FA520F", "mistral", ["mistral"]],
  ["copilot", "Copilot", "#0078D4", "copilot", ["copilot"]],
  ["grok", "Grok", "#000000", "grok", ["grok"]],
  ["midjourney", "Midjourney", "#000000", "midjourney", ["midjourney"]],
  ["claudeai", "Claude", "#D97757", "claude", ["claude"]],
];
const BLOQUEADOS = ["meta", "drive", "insta", "make", "x"];
const LOBE = "https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons";

async function texto(url) {
  try {
    const r = await fetch(url, { signal: AbortSignal.timeout(15000) });
    return r.ok ? await r.text() : null;
  } catch { return null; }
}

/** Logo oficial: Lobe a color → SVGL (variante oscura) → Lobe monocromo en blanco. null si no hay. */
async function oficial(consulta) {
  const q = consulta.toLowerCase().replace(/\s+/g, "");
  let svg = await texto(`${LOBE}/${q}-color.svg`);
  if (svg?.includes("<svg")) return { svg, fuente: "lobe-icons", color: true };
  const lista = await texto(`https://api.svgl.app?search=${encodeURIComponent(consulta)}`);
  if (lista) {
    try {
      const res = JSON.parse(lista);
      const m = res.find((x) => x.title.toLowerCase() === consulta.toLowerCase()) ?? res[0];
      const ruta = m && (typeof m.route === "string" ? m.route : m.route.dark ?? m.route.light);
      svg = ruta ? await texto(ruta) : null;
      if (svg?.includes("<svg")) return { svg, fuente: "svgl", color: true };
    } catch { /* respuesta inesperada: siguiente fuente */ }
  }
  svg = await texto(`${LOBE}/${q}.svg`);
  if (svg?.includes("<svg")) return { svg: svg.replace(/currentColor/g, "#FFFFFF"), fuente: "lobe-icons", color: false };
  return null;
}

async function desdeOficial([slug, nombre, color, consulta, alias]) {
  const o = await oficial(consulta);
  if (!o) {
    console.log(`  · ${nombre}: sin logo oficial (monograma)`);
    return monograma({ slug, nombre, color, letra: nombre.slice(0, 1), alias });
  }
  // Tamaño fijo fuera (lo pone Remotion) y sin <title> (no debe salir como texto).
  // (solo en la etiqueta <svg> raíz: un <rect> de un clipPath sin tamaño recorta el logo entero — pasó con Canva)
  const svg = o.svg.replace(/<title>.*?<\/title>/s, "")
    .replace(/<svg\b[^>]*>/, (raiz) => raiz.replace(/\s(width|height)="[^"]*"/g, ""));
  fs.writeFileSync(path.join(DIR, `${slug}.svg`), svg.includes("<svg") ? svg : o.svg);
  console.log(`  ✔ ${nombre}: ${o.fuente}${o.color ? " (a color)" : ""}`);
  return { slug, nombre, alias, color, archivo: `_shared/logos/${slug}.svg`, fondoPropio: o.color,
           logoColor: o.color, fuente: o.fuente };
}

const leer = () => (fs.existsSync(INDEX) ? JSON.parse(fs.readFileSync(INDEX, "utf8")) : { marcas: [], bloqueados: [] });
const guardar = (idx) => fs.writeFileSync(INDEX, JSON.stringify(idx, null, 2) + "\n", "utf8");
const clave = (s) => "si" + s.charAt(0).toUpperCase() + s.slice(1);

function desdeSimpleIcons(slug, alias) {
  const ic = si[clave(slug)];
  if (!ic) throw new Error(`No existe en Simple Icons: ${slug}`);
  fs.writeFileSync(path.join(DIR, `${slug}.svg`),
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="#FFFFFF" d="${ic.path}"/></svg>\n`);
  return { slug, nombre: ic.title, alias, color: `#${ic.hex}`, archivo: `_shared/logos/${slug}.svg`,
           fondoPropio: false, fuente: "simple-icons" };
}

function monograma({ slug, nombre, color, letra, alias }) {
  const archivo = path.join(DIR, `${slug}.svg`);
  const oficial = fs.existsSync(archivo) && !fs.readFileSync(archivo, "utf8").includes('data-monograma="1"');
  if (!oficial) {
    const tam = letra.length > 1 ? 13 : 16;
    fs.writeFileSync(archivo,
      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" data-monograma="1">` +
      `<text x="12" y="12" dy="0.36em" text-anchor="middle" font-family="Arial, sans-serif" font-weight="700" ` +
      `font-size="${tam}" fill="#FFFFFF">${letra}</text></svg>\n`);
  }
  return { slug, nombre, alias, color, archivo: `_shared/logos/${slug}.svg`, fondoPropio: oficial,
           fuente: oficial ? "oficial" : "monograma" };
}

function marcaPropia() {
  const m = JSON.parse(fs.readFileSync(path.join(RAIZ, "marca", "marca.json"), "utf8"));
  const nombre = m.logos.soloTexto || m.marca;
  const base = nombre.toLowerCase();
  return { slug: "_propia", nombre, alias: [base],
           color: m.colores.fondo, acento: m.colores.acento, archivo: `_shared/marca/isotipo.png`,
           fondoPropio: false, propia: true, fuente: "marca" };
}

const [, , cmd, ...resto] = process.argv;
const idx = leer();
const poner = (e) => { idx.marcas = idx.marcas.filter((x) => x.slug !== e.slug); idx.marcas.push(e); };

if (cmd === "añadir" || cmd === "anadir") {
  const [slug, ...alias] = resto;
  poner(desdeSimpleIcons(slug, alias.length ? alias.map((a) => a.toLowerCase()) : [slug]));
} else if (cmd === "oficial") {
  const [slug, nombre, color, consulta, ...alias] = resto;
  poner(await desdeOficial([slug, nombre, color, consulta, alias.length ? alias.map((a) => a.toLowerCase()) : [slug]]));
} else {
  for (const [slug, alias] of MARCAS) poner(desdeSimpleIcons(slug, alias));
  for (const m of MONOGRAMAS) poner(monograma(m));
  for (const o of OFICIALES) poner(await desdeOficial(o));
  // «claude» de Simple Icons queda como respaldo: el oficial a color gana el alias
  idx.marcas = idx.marcas.filter((x) => !(x.slug === "claude" && idx.marcas.some((y) => y.slug === "claudeai" && y.logoColor)));
  poner(marcaPropia());
  idx.bloqueados = [...new Set([...(idx.bloqueados || []), ...BLOQUEADOS])];
}
idx.marcas.sort((a, b) => a.nombre.localeCompare(b.nombre));
guardar(idx);
console.log(`${idx.marcas.length} marcas en ${path.relative(RAIZ, INDEX)} · bloqueados: ${idx.bloqueados.join(", ")}`);
