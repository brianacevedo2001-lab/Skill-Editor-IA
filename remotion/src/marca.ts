// Única puerta de entrada a la identidad visual. Nada de colores, nombres ni fuentes
// fijos en las escenas: todo sale de marca/marca.json y marca/canal.json.
import { loadFont as cargarTitulares } from "@remotion/google-fonts/InstrumentSerif";
import { loadFont as cargarTexto } from "@remotion/google-fonts/Manrope";
import { loadFont as cargarMono } from "@remotion/google-fonts/JetBrainsMono";
import { staticFile } from "remotion";
import marcaJson from "../../marca/marca.json";
import canalJson from "../../marca/canal.json";

export const marca = marcaJson;
export const canal = canalJson;
export const colores = marcaJson.colores;

const titulares = cargarTitulares("italic", { weights: ["400"], subsets: ["latin", "latin-ext"] });
const texto = cargarTexto("normal", { weights: ["400", "500", "600", "700", "800"], subsets: ["latin", "latin-ext"] });
const mono = cargarMono("normal", { weights: ["400", "500"], subsets: ["latin", "latin-ext"] });

export const fuentes = {
  titulares: titulares.fontFamily,
  texto: texto.fontFamily,
  mono: mono.fontFamily,
};

// marca/*.png se copian a videos/_shared/marca/ (publicDir = ../videos).
const nombreArchivo = (ruta: string | null) => (ruta ? ruta.split("/").pop()! : null);
export const logos = {
  isotipo: marcaJson.logos.isotipo ? staticFile(`_shared/marca/${nombreArchivo(marcaJson.logos.isotipo)}`) : null,
  logotipo: marcaJson.logos.logotipo ? staticFile(`_shared/marca/${nombreArchivo(marcaJson.logos.logotipo)}`) : null,
  avatar: canalJson.avatar ? staticFile(`_shared/marca/${nombreArchivo(canalJson.avatar)}`) : null,
};

/** Suscriptores con el formato de YouTube en español: «51», «85,6 mil», «1,23 M». Nunca «K». */
export const formatoSuscriptores = (n: number): string => {
  const coma = (x: number, dec: number) =>
    (dec > 0 ? x.toFixed(dec).replace(/\.?0+$/, "") : x.toFixed(0)).replace(".", ",");
  if (n < 1000) return `${n}`;
  if (n < 10_000) return `${coma(n / 1000, 2)} mil`;
  if (n < 1_000_000) return `${coma(n / 1000, n < 100_000 ? 1 : 0)} mil`;
  return `${coma(n / 1_000_000, 2)} M`;
};
