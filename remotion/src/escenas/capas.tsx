// Capas con la persona recortada (pipeline/recortar.py → <parte>.persona.webm): gráficos DETRÁS de la persona.
// Orden en Parte: cámara → escenas con "capa": "detras" → persona (mismos punch-in) → resto de escenas.
import React from "react";
import { AbsoluteFill } from "remotion";
import { colores, fuentes } from "../marca";
import type { Escena } from "../types";
import { Fondo } from "../fondo/Fondos";
import { Efecto, palabrasConAcento } from "../componentes/piezas";
import { easeInOut, f, prog, rgba, useEntradaSalida, useLienzo } from "../lib/util";

/** Titular gigante detrás de la cabeza. fondo "depth": la sala desaparece y la persona flota sobre el fondo 3D. */
export const TituloDetras: React.FC<{ escena: Extract<Escena, { type: "tituloDetras" }> }> = ({ escena: e }) => {
  const { frame, ent, sal } = useEntradaSalida(12, 14);
  const L = useLienzo();
  const pals = palabrasConAcento(e.text);
  const largo = e.text.replace(/\*/g, "").length;
  const tam = (L.vertical ? L.W * 0.26 : L.H * 0.3) * Math.min(1, 11 / Math.max(largo, 6));
  return (
    <AbsoluteFill>
      {e.fondo === "depth" && (
        <AbsoluteFill style={{ opacity: ent * (1 - sal) }}>
          <Fondo tint={e.tint} semilla={21} velocidad={4} />
        </AbsoluteFill>
      )}
      <AbsoluteFill style={{ alignItems: "center", paddingTop: L.H * (e.y ?? 0.08) }}>
        {e.kicker && (
          <div style={{ fontFamily: fuentes.mono, fontSize: L.vertical ? 30 : 28, letterSpacing: 8, textTransform: "uppercase",
                        color: colores.acento, opacity: prog(frame, 4, 16) * (1 - sal), marginBottom: 10 }}>{e.kicker}</div>
        )}
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: `0 ${tam * 0.22}px`,
                      maxWidth: L.W * 0.94, fontFamily: fuentes.titulares, fontStyle: "italic", fontSize: tam,
                      lineHeight: 0.95, textAlign: "center" }}>
          {pals.map((p, i) => {
            const k = prog(frame, 2 + i * 4, 18 + i * 4);
            return (
              <span key={i} style={{ display: "inline-block", opacity: k * (1 - sal),
                                     color: p.acento ? colores.acento : rgba(colores.texto, 0.94),
                                     transform: `translateY(${(1 - k) * tam * 0.35 - sal * 30}px) scale(${0.92 + 0.08 * k})`,
                                     filter: `blur(${(1 - k) * 14}px)`,
                                     textShadow: `0 ${tam * 0.06}px ${tam * 0.2}px rgba(0,0,0,0.35)` }}>{p.t}</span>
            );
          })}
        </div>
      </AbsoluteFill>
      <Efecto nombre={e.sfx === undefined ? "golpe_corto" : e.sfx} desde={8} volumen={0.5} />
    </AbsoluteFill>
  );
};

/** Halo (contorno luminoso) de la persona mientras haya una escena detrás que lo pida. 0..1 */
export const haloEn = (frame: number, escenas: Escena[]) => {
  let h = 0;
  for (const e of escenas) {
    if (e.capa !== "detras" || e.halo === false) continue;
    const a = f(e.from), b = f(e.to);
    h = Math.max(h, Math.min(prog(frame, a, a + 12), 1 - prog(frame, b - 12, b)));
  }
  return h;
};

/** Entrada en iris: la escena se abre en círculo desde el foco (la cara) y se cierra igual al salir. */
export const Iris: React.FC<{ foco: [number, number]; activo?: boolean; children: React.ReactNode }> = ({ foco, activo, children }) => {
  const { frame, dur } = useEntradaSalida();
  const L = useLienzo();
  if (!activo) return <>{children}</>;
  // curva propia (lineal + easeInOut): con la de useEntradaSalida el círculo ya estaba casi abierto a los 5 fotogramas
  const lin = Math.min(1, frame / 20, (dur - frame) / 16);
  const k = easeInOut(Math.max(0, lin));
  const r = k * Math.hypot(L.W, L.H) * 1.05;
  return (
    <AbsoluteFill style={{ clipPath: `circle(${r}px at ${foco[0] * 100}% ${foco[1] * 100}%)` }}>{children}</AbsoluteFill>
  );
};
