// Anuncio de producto (vertical 9:16 «Anuncio» y 4:5 «AnuncioLinkedin»), guiado por videos/<id>/anuncio.json:
// {voz, duracion, escenas: [{tipo, from, to, transicion?, …}]}. Tiempos en segundos ABSOLUTOS de la locución.
// La música NO va aquí: se mezcla al exportar (versión con música para YouTube; IG/TikTok sin música).
import React from "react";
import { AbsoluteFill, Audio, CalculateMetadataFunction, Sequence, staticFile } from "remotion";
import type { LogosIndex } from "../types";
import { Grano } from "../fondo/Depth";
import { f } from "../lib/util";
import { Barrido, P } from "./sistema";
import { Apertura, Canales, ChatIA, Final, Handoff, Hoy, Leads, Listo, Medianoche, Pago, Pildoras, Recupera, Remate, type E } from "./escenas";

export type PropsAnuncio = { guion: string; datos?: { g: E; logos: LogosIndex } };

export const calcularAnuncio: CalculateMetadataFunction<PropsAnuncio> = async ({ props }) => {
  const leer = async (r: string) => (await fetch(staticFile(r))).json();
  const [g, logos] = await Promise.all([leer(props.guion), leer("_shared/logos/index.json")]);
  return { durationInFrames: f(g.duracion), props: { ...props, datos: { g, logos } } };
};

const ESCENAS: Record<string, React.FC<{ e: E; logos: LogosIndex; dur: number }>> = {
  apertura: Apertura, canales: Canales, medianoche: Medianoche, chat: ChatIA, leads: Leads, handoff: Handoff,
  pago: Pago, listo: Listo, pildoras: Pildoras, hoy: Hoy, recupera: Recupera, remate: Remate, final: Final,
};

export const Anuncio: React.FC<PropsAnuncio> = ({ datos }) => {
  if (!datos) return null;
  const { g, logos } = datos;
  const escenas = g.escenas as E[];
  return (
    <AbsoluteFill style={{ backgroundColor: P.tinta }}>
      {escenas.map((e, i) => {
        const C = ESCENAS[e.tipo];
        const a = f(e.from), b = f(e.to);
        return C ? (
          <Sequence key={i} from={a} durationInFrames={Math.max(1, b - a)}>
            <C e={e} logos={logos} dur={b - a} />
          </Sequence>
        ) : null;
      })}
      {/* barridos orgánicos en los cambios marcados con "transicion": "mancha" */}
      {escenas.map((e, i) => e.transicion === "mancha" && (
        <Barrido key={`b${i}`} en={f(e.from)} x={e.transicionX ?? 0.5} y={e.transicionY ?? 0.5} color={e.transicionColor === "tinta" ? P.tinta : P.acento} />
      ))}
      <Grano opacidad={0.035} />
      <Audio src={staticFile(g.voz)} />
    </AbsoluteFill>
  );
};
