// Láminas para LinkedIn (1080×1350, 4:5): carrusel PDF e imagen suelta. Guion: videos/<id>/linkedin.json
//   { "carrusel": [ {tipo: "portada" | "idea" | "dato" | "cierre", …}, … ], "imagen": { …misma forma… } }
// Mismo lenguaje visual que los vídeos: fondo Depth, titulares serif en cursiva con *acentos*, cristal y marca.
import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { canal, colores, fuentes, logos as logosMarca, marca } from "./marca";
import type { LogosIndex } from "./types";
import { Depth } from "./fondo/Depth";
import { Bloque, FichaMarca, palabrasConAcento } from "./componentes/piezas";
import { rgba } from "./lib/util";

export interface DatosLamina {
  tipo: "portada" | "idea" | "dato" | "cierre";
  kicker?: string;
  titulo: string;           // *palabras* en acento
  texto?: string;
  numero?: number;          // idea: 1, 2, 3…
  valor?: string;           // dato: «78 %»
  logo?: string;            // slug de logos/index.json
  cta?: string;             // cierre
}
export interface GuionLinkedin { carrusel: DatosLamina[]; imagen?: DatosLamina }
export type PropsLamina = { guion: string; indice: number; datos?: { lamina: DatosLamina; total: number; pagina: number; logos: LogosIndex } };

export const calcularLamina = async ({ props }: { props: PropsLamina }) => {
  const leer = async (r: string) => (await fetch(staticFile(r))).json();
  const [g, logos] = await Promise.all([leer(props.guion) as Promise<GuionLinkedin>, leer("_shared/logos/index.json")]);
  // indice -1 = imagen suelta
  const lamina = props.indice < 0 ? (g.imagen ?? g.carrusel[0]) : g.carrusel[props.indice];
  return { props: { ...props, datos: { lamina, total: g.carrusel.length, pagina: props.indice + 1, logos } } };
};

const Titulo: React.FC<{ texto: string; tam: number; align?: "left" | "center" }> = ({ texto, tam, align = "left" }) => (
  <div style={{ fontFamily: fuentes.titulares, fontStyle: "italic", fontSize: tam, lineHeight: 1.04, color: colores.texto,
                textAlign: align, letterSpacing: "-0.01em" }}>
    {palabrasConAcento(texto).map((p, i) => (
      <span key={i} style={{ color: p.acento ? colores.acento : undefined }}>{i ? " " : ""}{p.t}</span>
    ))}
  </div>
);

export const Lamina: React.FC<PropsLamina> = ({ datos, indice }) => {
  if (!datos) return null;
  const { lamina: l, total, pagina, logos } = datos;
  const suelta = indice < 0;
  return (
    <AbsoluteFill style={{ backgroundColor: colores.fondo }}>
      <Depth semilla={3 + Math.max(indice, 0)} velocidad={0} impulso={1} />
      <AbsoluteFill style={{ padding: "110px 96px 150px", display: "flex", flexDirection: "column",
                             justifyContent: "center", gap: 40 }}>
        {l.kicker && (
          <div style={{ fontFamily: fuentes.mono, fontSize: 30, letterSpacing: 6, textTransform: "uppercase", color: colores.etiqueta }}>
            {l.kicker}
          </div>
        )}
        {l.tipo === "idea" && l.numero !== undefined && (
          <div style={{ fontFamily: fuentes.titulares, fontStyle: "italic", fontSize: 240, lineHeight: 0.9, color: colores.acento,
                        textShadow: `0 0 50px ${rgba(colores.acento, 0.4)}` }}>{String(l.numero).padStart(2, "0")}</div>
        )}
        {l.tipo === "dato" && l.valor && (
          <div style={{ fontFamily: fuentes.titulares, fontStyle: "italic", fontSize: 260, lineHeight: 0.9, color: colores.texto }}>{l.valor}</div>
        )}
        <Titulo texto={l.titulo} tam={l.tipo === "portada" ? 132 : l.tipo === "cierre" ? 112 : 100} />
        {l.texto && (
          <Bloque variante="cristal" radio={26} style={{ padding: "30px 36px" }}>
            <div style={{ fontFamily: fuentes.texto, fontWeight: 500, fontSize: 50, lineHeight: 1.32, color: colores.texto }}>{l.texto}</div>
          </Bloque>
        )}
        {l.logo && <div style={{ alignSelf: "flex-start" }}><FichaMarca ficha={{ logo: l.logo }} logos={logos} alto={120} /></div>}
        {l.tipo === "cierre" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 18, marginTop: 10 }}>
            {l.cta && <Bloque variante="acento" style={{ fontFamily: fuentes.texto, fontWeight: 800, fontSize: 48, alignSelf: "flex-start" }}>{l.cta}</Bloque>}
            <div style={{ fontFamily: fuentes.mono, fontSize: 32, color: colores.textoSuave, letterSpacing: 2 }}>
              {(canal as { sitio?: string }).sitio?.replace(/^https?:\/\//, "")} · {canal.handle}
            </div>
          </div>
        )}
      </AbsoluteFill>

      {/* pie: persona y paginación */}
      <div style={{ position: "absolute", left: 96, right: 96, bottom: 60, display: "flex", alignItems: "center", gap: 18 }}>
        {logosMarca.avatar && (
          <Img src={logosMarca.avatar} style={{ width: 64, height: 64, borderRadius: 32, border: `2px solid ${colores.acento}`, objectFit: "cover" }} />
        )}
        <div style={{ display: "flex", flexDirection: "column" }}>
          <span style={{ fontFamily: fuentes.texto, fontWeight: 700, fontSize: 28, color: colores.texto }}>{marca.persona.nombre}</span>
          <span style={{ fontFamily: fuentes.mono, fontSize: 20, letterSpacing: 2, color: colores.textoSuave, textTransform: "uppercase" }}>
            {marca.persona.cargo}
          </span>
        </div>
        <div style={{ flex: 1 }} />
        {!suelta && (
          <span style={{ fontFamily: fuentes.mono, fontSize: 26, color: colores.textoSuave }}>
            {pagina}/{total}{pagina < total ? "  →" : ""}
          </span>
        )}
        {suelta && logosMarca.isotipo && <Img src={logosMarca.isotipo} style={{ height: 56, opacity: 0.9 }} />}
      </div>
    </AbsoluteFill>
  );
};
