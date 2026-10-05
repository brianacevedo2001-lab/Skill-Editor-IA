// Fondo 3D de todas las escenas a pantalla completa: partículas con paralaje y bokeh, suelo de
// rejilla en perspectiva que avanza, viñeta y un toque del color de la escena.
//
// Regla técnica: si la velocidad cambia durante la escena, la distancia recorrida se INTEGRA
// (suma de velocidades por fotograma). Con `camZ = t · speed` y `speed` variable, todo salta de golpe.
import React, { useMemo } from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from "remotion";
import { colores } from "../marca";
import { azar, proyectar, rgba, useLienzo } from "../lib/util";

const N_PARTICULAS = 150;
const PROFUNDIDAD = 3200;
const FOCO = 900;
const SUELO_Y = 420;       // altura del suelo respecto al centro (px en z = 0)
const PASO_REJILLA = 220;

type Props = {
  /** Color de la escena (por defecto el acento de la marca). */
  tint?: string;
  /** Velocidad de avance en px/fotograma. */
  velocidad?: number;
  /** Arranque con impulso: empieza más rápido y frena (multiplicador inicial). */
  impulso?: number;
  semilla?: number;
  /** Mostrar el suelo de rejilla. */
  suelo?: boolean;
};

/** Velocidad en el fotograma k (impulso inicial que decae). */
const velocidadEn = (k: number, base: number, impulso: number) => base * (1 + (impulso - 1) * Math.exp(-k / 14));

export const distanciaRecorrida = (frame: number, base: number, impulso: number) => {
  let d = 0;
  for (let k = 0; k < frame; k++) d += velocidadEn(k, base, impulso);
  return d;
};

export const Depth: React.FC<Props> = ({ tint = colores.acento, velocidad = 6, impulso = 4, semilla = 1, suelo = true }) => {
  const frame = useCurrentFrame();
  const { W, H, cx, cy } = useLienzo();
  const altoRel = Math.max(1, H / 1080);         // en vertical las partículas ocupan también el alto extra
  const dist = distanciaRecorrida(frame, velocidad, impulso);

  const particulas = useMemo(() => {
    const r = azar(semilla * 9973);
    return Array.from({ length: N_PARTICULAS }, () => ({
      x: (r() - 0.5) * 3600,
      y: (r() - 0.62) * 1900 * altoRel,
      z: r() * PROFUNDIDAD,
      tam: 1.2 + r() * 2.6,
      brillo: 0.35 + r() * 0.65,
      acento: r() < 0.22,
    }));
  }, [semilla, altoRel]);

  const puntos = particulas
    .map((p, i) => {
      const z = (((p.z - dist) % PROFUNDIDAD) + PROFUNDIDAD) % PROFUNDIDAD - 250;
      const q = proyectar(p.x, p.y, z, FOCO, cx, cy);
      const cerca = z < 250;                       // muy cerca: bokeh grande y desenfocado
      const aparicion = Math.min(1, (PROFUNDIDAD - 250 - z) / 500); // nace suave al fondo
      const r = cerca ? p.tam * q.s * 9 : p.tam * q.s * 1.6;
      const op = (cerca ? 0.12 : p.brillo * Math.min(1, q.s * 1.6)) * aparicion;
      return { i, x: q.x, y: q.y, r, op, cerca, color: p.acento ? tint : colores.texto, z };
    })
    .filter((p) => p.op > 0.01 && p.x > -200 && p.x < W + 200 && p.y > -200 && p.y < H + 200)
    .sort((a, b) => b.z - a.z);

  // Suelo: líneas horizontales que avanzan (misma distancia integrada) y líneas que fugan al centro.
  const lineasH: React.ReactNode[] = [];
  const lineasV: React.ReactNode[] = [];
  if (suelo) {
    const desfase = dist % PASO_REJILLA;
    for (let k = 0; k < 16; k++) {
      const z = k * PASO_REJILLA - desfase;
      if (z < -FOCO * 0.6) continue;
      const a = proyectar(-6000, SUELO_Y, z, FOCO, cx, cy);
      const b = proyectar(6000, SUELO_Y, z, FOCO, cx, cy);
      const op = Math.max(0, 0.28 * (1 - z / (16 * PASO_REJILLA))) * Math.min(1, (z + FOCO * 0.6) / 300);
      lineasH.push(<line key={`h${k}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={rgba(tint, op)} strokeWidth={1.2} />);
    }
    for (let k = -14; k <= 14; k++) {
      const x = k * PASO_REJILLA;
      const a = proyectar(x, SUELO_Y, -FOCO * 0.6, FOCO, cx, cy);
      const b = proyectar(x, SUELO_Y, 16 * PASO_REJILLA, FOCO, cx, cy);
      lineasV.push(<line key={`v${k}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="url(#fugaRejilla)" strokeWidth={1} />);
    }
  }

  return (
    <AbsoluteFill style={{ backgroundColor: colores.fondo, overflow: "hidden" }}>
      {/* luz ambiental del color de la escena */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(60% 45% at 50% 38%, ${rgba(tint, 0.14)} 0%, transparent 70%),
                       radial-gradient(90% 60% at 50% 110%, ${rgba(tint, 0.1)} 0%, transparent 60%)`,
        }}
      />
      <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
        <defs>
          <linearGradient id="fugaRejilla" x1="0" y1="1" x2="0" y2="0" gradientUnits="objectBoundingBox">
            <stop offset="0" stopColor={rgba(tint, 0.22)} />
            <stop offset="1" stopColor={rgba(tint, 0)} />
          </linearGradient>
          <radialGradient id="bokeh">
            <stop offset="0" stopColor="#fff" stopOpacity="1" />
            <stop offset="0.55" stopColor="#fff" stopOpacity="0.55" />
            <stop offset="1" stopColor="#fff" stopOpacity="0" />
          </radialGradient>
        </defs>
        <g>{lineasV}</g>
        <g>{lineasH}</g>
        {puntos.map((p) =>
          p.cerca ? (
            <circle key={p.i} cx={p.x} cy={p.y} r={p.r} fill="url(#bokeh)" opacity={p.op}
                    style={{ mixBlendMode: "screen" }} />
          ) : (
            <circle key={p.i} cx={p.x} cy={p.y} r={Math.max(p.r, 0.6)} fill={p.color} opacity={p.op} />
          ),
        )}
      </svg>
      {/* viñeta */}
      <AbsoluteFill
        style={{ background: `radial-gradient(75% 70% at 50% 45%, transparent 55%, ${rgba(colores.fondo, 0.92)} 100%)` }}
      />
    </AbsoluteFill>
  );
};

/** Grano de película muy sutil (se alternan 6 fotogramas de ruido). */
export const Grano: React.FC<{ opacidad?: number }> = ({ opacidad = 0.05 }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ pointerEvents: "none", mixBlendMode: "overlay", opacity: opacidad }}>
      <Img src={staticFile(`_shared/fx/grano_${frame % 6}.png`)} style={{ width: "100%", height: "100%" }} />
    </AbsoluteFill>
  );
};
