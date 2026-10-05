// Composición del grueso: grabación de pantalla (con zooms suaves) + cámara en una esquina,
// monólogo final a pantalla completa (camFull), recortes en grande (showcase) y lowerThird.
// SIN logos encima de la pantalla durante la explicación: distraen.
import React from "react";
import { AbsoluteFill, Audio, CalculateMetadataFunction, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { colores } from "./marca";
import type { Cuts } from "./types";
import { Depth, Grano } from "./fondo/Depth";
import { LowerThird } from "./escenas/camara";
import { easeInOut, f, prog, rgba } from "./lib/util";
import { inclinacion } from "./componentes/piezas";

export interface Zoom { from: number; to: number; x: number; y: number; escala: number }
export type EscenaGrueso =
  | { type: "camFull"; from: number; to: number; ancla?: string }
  | { type: "showcase"; from: number; to: number; rect: [number, number, number, number]; ancla?: string }
  | { type: "lowerThird"; from: number; to: number; ancla?: string; sfx?: string | null; handheld?: boolean };

export interface GuionGrueso {
  parte: "grueso";
  pantalla: string;
  camara: string;
  cuts: string;
  palabras?: string;
  /** Cámara en la esquina: lado y ancho (fracción del ancho del vídeo). */
  esquina?: { lado: "der" | "izq"; ancho: number };
  musica?: { src: string | null; volumen: number; desde?: number };
  zooms: Zoom[];
  escenas: EscenaGrueso[];
}
export type PropsGrueso = { guion: string; datos?: { guion: GuionGrueso; cuts: Cuts & { sin_camara?: [number, number][] } } };

export const calcularGrueso: CalculateMetadataFunction<PropsGrueso> = async ({ props }) => {
  const leer = async (r: string) => (await fetch(staticFile(r))).json();
  const guion: GuionGrueso = await leer(props.guion);
  const cuts = await leer(guion.cuts);
  const fin = Math.max(cuts.fotogramas, ...guion.escenas.map((e) => f(e.to)));
  return { durationInFrames: fin, props: { ...props, datos: { guion, cuts } } };
};

const TRANS = 18; // fotogramas de entrada/salida de zooms y camFull

/** Transformación de la pantalla: zoom suave hacia (x, y). */
const zoomEn = (frame: number, zooms: Zoom[]) => {
  for (const z of zooms) {
    const a = f(z.from), b = f(z.to);
    if (frame < a - TRANS || frame > b + TRANS) continue;
    const k = Math.min(prog(frame, a - TRANS / 2, a + TRANS / 2, easeInOut), 1 - prog(frame, b - TRANS / 2, b + TRANS / 2, easeInOut));
    return { escala: 1 + (z.escala - 1) * k, x: z.x, y: z.y };
  }
  return { escala: 1, x: 0.5, y: 0.5 };
};

/** Presencia (0..1) de un tipo de escena en este fotograma, con rampas. */
const presencia = (frame: number, escenas: EscenaGrueso[], tipo: EscenaGrueso["type"]) => {
  let v = 0;
  for (const e of escenas) {
    if (e.type !== tipo) continue;
    const a = f(e.from), b = f(e.to);
    v = Math.max(v, Math.min(prog(frame, a, a + TRANS, easeInOut), 1 - prog(frame, b - TRANS, b, easeInOut)));
  }
  return v;
};

export const Grueso: React.FC<PropsGrueso> = ({ datos }) => {
  const frame = useCurrentFrame();
  if (!datos) return null;
  const { guion, cuts } = datos;
  const esq = guion.esquina ?? { lado: "der", ancho: 0.2 };
  const z = zoomEn(frame, guion.zooms);
  const full = presencia(frame, guion.escenas, "camFull");
  const sinCam = (cuts.sin_camara ?? []).some(([a, b]) => frame >= f(a) - 4 && frame < f(b) + 4);
  const visibleCam = sinCam && full < 0.01 ? 0 : 1;

  // Rectángulo de la cámara: de la esquina a pantalla completa según `full`.
  const margen = 36;
  const w0 = 1920 * esq.ancho, h0 = (w0 * 9) / 16;
  const x0 = esq.lado === "der" ? 1920 - w0 - margen : margen, y0 = 1080 - h0 - margen;
  const cam = {
    x: interpolate(full, [0, 1], [x0, 0]), y: interpolate(full, [0, 1], [y0, 0]),
    w: interpolate(full, [0, 1], [w0, 1920]), h: interpolate(full, [0, 1], [h0, 1080]),
    r: interpolate(full, [0, 1], [22, 0]),
  };
  // camFull: zoom lento durante el monólogo.
  const cf = guion.escenas.find((e) => e.type === "camFull" && frame >= f(e.from) && frame < f(e.to));
  const lento = cf ? interpolate(frame, [f(cf.from), f(cf.to)], [1, 1.07]) : 1;

  return (
    <AbsoluteFill style={{ backgroundColor: colores.fondo }}>
      {/* pantalla */}
      <AbsoluteFill style={{ transform: `scale(${z.escala})`, transformOrigin: `${z.x * 100}% ${z.y * 100}%` }}>
        <OffthreadVideo src={staticFile(guion.pantalla)} toneMapped={false} style={{ width: "100%", height: "100%" }} />
      </AbsoluteFill>

      {/* showcase: recorte de la pantalla en grande sobre Depth */}
      {guion.escenas.filter((e) => e.type === "showcase").map((e, i) => (
        <Sequence key={`s${i}`} from={f(e.from)} durationInFrames={f(e.to) - f(e.from)}>
          <Showcase escena={e as Extract<EscenaGrueso, { type: "showcase" }>} src={guion.pantalla} inicio={f(e.from)} />
        </Sequence>
      ))}

      {/* cámara (esquina ↔ pantalla completa) */}
      <div style={{
        position: "absolute", left: cam.x, top: cam.y, width: cam.w, height: cam.h, borderRadius: cam.r, overflow: "hidden",
        opacity: visibleCam, border: full < 0.99 ? `2px solid ${rgba(colores.acento, 0.55 * (1 - full))}` : undefined,
        boxShadow: `0 24px 60px -20px rgba(0,0,0,${0.8 * (1 - full)})`, backgroundColor: "#000",
      }}>
        <OffthreadVideo src={staticFile(guion.camara)} muted toneMapped={false}
                        style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${lento})` }} />
      </div>

      {guion.escenas.filter((e) => e.type === "lowerThird").map((e, i) => (
        <Sequence key={`l${i}`} from={f(e.from)} durationInFrames={f(e.to) - f(e.from)}>
          <LowerThird escena={{ ...e, type: "lowerThird", sfx: (e as { sfx?: string | null }).sfx }} />
        </Sequence>
      ))}

      <Grano opacidad={0.035} />
      {guion.musica?.src && <Audio src={staticFile(guion.musica.src)} startFrom={f(guion.musica.desde ?? 0)} volume={guion.musica.volumen} />}
    </AbsoluteFill>
  );
};

/**
 * Solo los gráficos del grueso (lowerThird, showcase) sobre fondo TRANSPARENTE, para el render híbrido
 * (pipeline/render_grueso.py): la base (pantalla con zooms + cámara) la compone ffmpeg con la GPU y esto
 * se superpone. Renderizar toda la composición Grueso en Remotion iba a 1/35 del tiempo real (prueba02:
 * 60 s en 35 min) por mover fotogramas de 2560×1440 y de la cámara en cada fotograma.
 */
export const GruesoGraficos: React.FC<PropsGrueso> = ({ datos }) => {
  if (!datos) return null;
  const { guion } = datos;
  return (
    <AbsoluteFill>
      {guion.escenas.filter((e) => e.type === "showcase").map((e, i) => (
        <Sequence key={`s${i}`} from={f(e.from)} durationInFrames={f(e.to) - f(e.from)}>
          <Showcase escena={e as Extract<EscenaGrueso, { type: "showcase" }>} src={guion.pantalla} inicio={f(e.from)} />
        </Sequence>
      ))}
      {guion.escenas.filter((e) => e.type === "lowerThird").map((e, i) => (
        <Sequence key={`l${i}`} from={f(e.from)} durationInFrames={f(e.to) - f(e.from)}>
          <LowerThird escena={{ ...e, type: "lowerThird", sfx: (e as { sfx?: string | null }).sfx }} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

const Showcase: React.FC<{ escena: Extract<EscenaGrueso, { type: "showcase" }>; src: string; inicio: number }> = ({ escena, src, inicio }) => {
  const frame = useCurrentFrame();
  const dur = f(escena.to) - f(escena.from);
  const ent = prog(frame, 0, 16), sal = prog(frame, dur - 16, dur, easeInOut);
  const [rx, ry, rw, rh] = escena.rect;              // fracciones de la pantalla
  const ancho = 1500, alto = (ancho * rh * 9) / (rw * 16);
  const esc = ancho / (1920 * rw);
  return (
    <AbsoluteFill style={{ opacity: ent * (1 - sal) }}>
      <Depth velocidad={3} impulso={2} semilla={9} />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <div style={{
          width: ancho, height: Math.min(alto, 900), overflow: "hidden", borderRadius: 24,
          border: `1px solid ${rgba(colores.texto, 0.18)}`, boxShadow: `0 50px 100px -30px rgba(0,0,0,.8), 0 0 60px -20px ${rgba(colores.acento, 0.4)}`,
          transform: `${inclinacion(6, -8)} scale(${0.94 + 0.06 * ent}) translateY(${sal * 30}px)`, position: "relative",
        }}>
          <div style={{ position: "absolute", width: 1920 * esc, height: 1080 * esc, left: -rx * 1920 * esc, top: -ry * 1080 * esc }}>
            <OffthreadVideo src={staticFile(src)} startFrom={inicio} muted toneMapped={false} style={{ width: "100%", height: "100%" }} />
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
