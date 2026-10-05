// Fondos alternativos para las escenas a pantalla completa, elegibles por guion ("fondo": …) para que dos vídeos
// seguidos no se vean iguales (ver pipeline/historial.py). Por defecto, "profundidad" (Depth).
//   profundidad → partículas con paralaje y suelo de rejilla (Depth.tsx)
//   puntos      → rejilla de puntos que respira y se ilumina alrededor del centro
//   aurora      → manchas de color suaves que derivan despacio (más cálido, menos «tech»)
import React, { createContext, useContext, useMemo } from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { colores } from "../marca";
import { azar, rgba, useLienzo } from "../lib/util";
import { Depth } from "./Depth";

export type TipoFondo = "profundidad" | "puntos" | "aurora";
export const FondoContext = createContext<TipoFondo>("profundidad");

type Props = { tint?: string; velocidad?: number; impulso?: number; semilla?: number };

const Vineta: React.FC = () => (
  <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 45%, transparent 35%, ${rgba(colores.fondo, 0.92)} 100%)` }} />
);

export const Puntos: React.FC<Props> = ({ tint = colores.acento, semilla = 1 }) => {
  const frame = useCurrentFrame();
  const { W, H, cx, cy } = useLienzo();
  const paso = 46;
  const puntos = useMemo(() => {
    const r = azar(semilla * 97);
    const res: { x: number; y: number; fase: number }[] = [];
    for (let y = -paso; y < H + paso; y += paso) for (let x = -paso; x < W + paso; x += paso) res.push({ x, y, fase: r() * 6.28 });
    return res;
  }, [W, H, semilla]);
  const deriva = (frame * 0.35) % paso;
  const radio = Math.max(W, H) * 0.55;
  return (
    <AbsoluteFill style={{ backgroundColor: colores.fondo }}>
      <AbsoluteFill style={{ background: `radial-gradient(circle at 50% 45%, ${rgba(tint, 0.2)} 0%, transparent 55%)` }} />
      <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
        {puntos.map((p, i) => {
          const x = p.x + deriva, y = p.y + deriva * 0.4;
          const d = Math.hypot(x - cx, y - cy * 0.9) / radio;
          const luz = Math.max(0, 1 - d);
          const brillo = 0.5 + 0.5 * Math.sin(frame / 22 + p.fase);
          const a = 0.06 + luz * (0.22 + 0.25 * brillo);
          return <circle key={i} cx={x} cy={y} r={1.6 + luz * 1.6} fill={luz > 0.55 && brillo > 0.85 ? tint : colores.texto} opacity={a} />;
        })}
      </svg>
      <Vineta />
    </AbsoluteFill>
  );
};

export const Aurora: React.FC<Props> = ({ tint = colores.acento, semilla = 1 }) => {
  const frame = useCurrentFrame();
  const { W, H } = useLienzo();
  const manchas = useMemo(() => {
    const r = azar(semilla * 31);
    return [tint, colores.acento2, colores.superficie2, tint].map((c, i) => ({
      c, ax: 0.2 + r() * 0.6, ay: 0.2 + r() * 0.5, fx: 0.004 + r() * 0.004, fy: 0.003 + r() * 0.004,
      fase: r() * 6.28, tam: (0.55 + r() * 0.35) * Math.max(W, H), op: i === 2 ? 0.5 : 0.28,
    }));
  }, [tint, W, H, semilla]);
  return (
    <AbsoluteFill style={{ backgroundColor: colores.fondo, overflow: "hidden" }}>
      {manchas.map((m, i) => {
        const x = W * (m.ax + 0.16 * Math.sin(frame * m.fx + m.fase));
        const y = H * (m.ay + 0.12 * Math.cos(frame * m.fy + m.fase));
        return (
          <div key={i} style={{ position: "absolute", left: x - m.tam / 2, top: y - m.tam / 2, width: m.tam, height: m.tam,
                                borderRadius: "50%", background: `radial-gradient(circle, ${rgba(m.c, m.op)} 0%, transparent 62%)`,
                                filter: "blur(40px)" }} />
        );
      })}
      <Vineta />
    </AbsoluteFill>
  );
};

/** El fondo que toque según el guion (FondoContext). Mismas props que Depth. */
export const Fondo: React.FC<Props> = (p) => {
  const tipo = useContext(FondoContext);
  if (tipo === "puntos") return <Puntos {...p} />;
  if (tipo === "aurora") return <Aurora {...p} />;
  return <Depth {...p} />;
};
