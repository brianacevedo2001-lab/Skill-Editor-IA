// Escenas a pantalla completa. Siempre sobre el fondo 3D Depth (nunca un fondo plano).
import React from "react";
import { AbsoluteFill, Img, OffthreadVideo, interpolate, spring, staticFile, useVideoConfig } from "remotion";
import { colores, fuentes, logos as logosMarca } from "../marca";
import type { Escena, Ficha, LogosIndex } from "../types";
import { Fondo } from "../fondo/Fondos";
import { Esfera } from "../componentes/Esfera";
import { Efecto, FichaMarca, buscarMarca, inclinacion, palabrasConAcento } from "../componentes/piezas";
import { azar, easeInOut, f, prog, rgba, useEntradaSalida, useLienzo } from "../lib/util";

type P<T extends Escena["type"]> = { escena: Extract<Escena, { type: T }>; logos: LogosIndex };

/** Marco común: Depth + entrada desde la cámara + salida. */
export const Completa: React.FC<{ tint?: string; children: React.ReactNode; semilla?: number; velocidad?: number }> = ({
  tint, children, semilla = 1, velocidad,
}) => {
  const { ent, sal } = useEntradaSalida(10, 14);
  return (
    <AbsoluteFill style={{ opacity: ent * (1 - sal), transform: `scale(${1.04 - 0.04 * ent + 0.03 * sal})` }}>
      <Fondo tint={tint} semilla={semilla} velocidad={velocidad} />
      {children}
    </AbsoluteFill>
  );
};

/** Titular que entra palabra a palabra (anclado a `wordsAt` o escalonado). */
export const Titular: React.FC<{
  texto: string; frame: number; desde: number; wordsAt?: number[]; inicioEscena: number; accent?: number[];
  tam?: number; style?: React.CSSProperties; sal?: number;
}> = ({ texto, frame, desde, wordsAt, inicioEscena, accent = [], tam = 104, style, sal = 0 }) => {
  const pals = palabrasConAcento(texto);
  const { W, vertical } = useLienzo();
  return (
    <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: `0 ${tam * 0.26}px`,
                  fontFamily: fuentes.titulares, fontStyle: "italic", fontSize: tam, lineHeight: 1.08,
                  color: colores.texto, maxWidth: vertical ? W - 140 : 1500, textAlign: "center", ...style }}>
      {pals.map((p, i) => {
        const t0 = wordsAt?.[i] !== undefined ? f(wordsAt[i] - inicioEscena) : desde + i * 4;
        const e = prog(frame, t0, t0 + 12);
        const acento = p.acento || accent.includes(i);
        return (
          <span key={i} style={{
            display: "inline-block", opacity: e * (1 - sal),
            transform: `translateY(${(1 - e) * 34 - sal * 20}px)`, filter: `blur(${(1 - e) * 10 + sal * 6}px)`,
            color: acento ? colores.acento : undefined,
          }}>{p.t}</span>
        );
      })}
    </div>
  );
};

// ─────────────────────────── orbOpen ───────────────────────────
export const OrbOpen: React.FC<P<"orbOpen">> = ({ escena: e }) => {
  const { frame, sal } = useEntradaSalida();
  const figAt = e.figureAt !== undefined ? f(e.figureAt - e.from) : Infinity;
  const morph = e.figure ? prog(frame, figAt, figAt + 36, easeInOut) : 0;
  const isoOp = (e.isotipo ?? true) ? prog(frame, 8, 30) * (1 - morph) * (1 - sal) : 0;
  const L = useLienzo();
  const cyOrb = L.vertical ? L.H * 0.4 : 430;
  return (
    <Completa tint={e.tint} semilla={2}>
      <Esfera frame={frame} radio={250 + prog(frame, 0, 40) * 20} cy={cyOrb} figura={e.figure ?? null} morph={morph}
              color={e.tint ?? colores.acento} opacidad={prog(frame, 0, 18) * (1 - sal)} />
      {logosMarca.isotipo && (
        <Img src={logosMarca.isotipo} style={{ position: "absolute", left: L.cx - 55, top: cyOrb - 60, height: 120,
             width: 110, objectFit: "contain", opacity: isoOp, filter: `drop-shadow(0 0 24px ${rgba(colores.acento, 0.6)})` }} />
      )}
      <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: L.vertical ? L.abajo + 60 : 150 }}>
        <Titular texto={e.headline} frame={frame} desde={14} wordsAt={e.wordsAt} inicioEscena={e.from}
                 accent={e.accent} sal={sal} />
      </AbsoluteFill>
      <Efecto nombre={e.sfx === undefined ? "sub_hit" : e.sfx} />
      {e.figure && Number.isFinite(figAt) && <Efecto nombre="swell" desde={figAt - 20} volumen={0.35} />}
    </Completa>
  );
};

// ─────────────────────────── lineup ───────────────────────────
const estadoFicha = (frame: number, fi: Ficha, i: number, n: number, inicio: number) => {
  const t0 = fi.at !== undefined ? f(fi.at - inicio) : 8 + i * 6;
  const ent = prog(frame, t0, t0 + 16);
  const st = fi.strikeAt !== undefined ? prog(frame, f(fi.strikeAt - inicio), f(fi.strikeAt - inicio) + 16, easeInOut) : 0;
  const ang = (i - (n - 1) / 2) * 5;
  return { t0, ent, st, ang };
};

export const Lineup: React.FC<P<"lineup">> = ({ escena: e, logos }) => {
  const { frame, sal } = useEntradaSalida();
  const n = e.items.length;
  const L = useLienzo();
  const alto = L.vertical ? (n >= 5 ? 100 : n === 4 ? 116 : 140) : n >= 5 ? 110 : n === 4 ? 128 : n === 3 ? 160 : 190;
  return (
    <Completa tint={e.tint} semilla={3}>
      {e.title && (
        <AbsoluteFill style={{ alignItems: "center", paddingTop: L.vertical ? L.arriba + 30 : 170 }}>
          <Titular texto={e.title} frame={frame} desde={2} inicioEscena={e.from} tam={L.vertical ? 72 : 78} sal={sal} />
        </AbsoluteFill>
      )}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: L.vertical ? "column" : "row",
                             gap: L.vertical ? 26 : n >= 4 ? 30 : 44,
                             padding: L.vertical ? `${L.arriba + (e.title ? 200 : 0)}px 60px ${L.abajo}px` : `${e.title ? 150 : 0}px 80px 0` }}>
        {e.items.map((fi, i) => {
          const { t0, ent, st, ang } = estadoFicha(frame, fi, i, n, e.from);
          return (
            <div key={i} style={{
              transform: `${inclinacion(7 + (1 - ent) * 30, -ang, 0)} translateY(${(1 - ent) * 90 + st * 46 + sal * 40}px) scale(${1 - st * 0.08})`,
              opacity: ent * (1 - st * 0.62) * (1 - sal),
              filter: `grayscale(${st}) blur(${st * 5 + sal * 4}px)`,
            }}>
              <FichaMarca ficha={fi} logos={logos} alto={alto} />
              <Efecto nombre={i === 0 ? (e.sfx === undefined ? "whoosh" : e.sfx) : "tick"} desde={t0} volumen={0.45}
                      pan={L.vertical || n < 2 ? 0 : ((i - (n - 1) / 2) / ((n - 1) / 2)) * 0.8} />
              {fi.strikeAt !== undefined && <Efecto nombre="fade_out" desde={f(fi.strikeAt - e.from)} volumen={0.5} />}
            </div>
          );
        })}
      </AbsoluteFill>
    </Completa>
  );
};

// ─────────────────────────── revealStat ───────────────────────────
export const RevealStat: React.FC<P<"revealStat">> = ({ escena: e, logos }) => {
  const { frame, sal } = useEntradaSalida();
  const { fps } = useVideoConfig();
  const impacto = spring({ frame, fps, config: { damping: 11, stiffness: 140 } });
  const temblor = frame < 14 ? Math.sin(frame * 3.1) * (14 - frame) * 0.6 : 0;
  const inicioRejilla = 20;
  const llenas = Math.round(interpolate(frame, [inicioRejilla, inicioRejilla + 40], [0, e.value],
                                        { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeInOut }));
  const marca = buscarMarca(logos, e.logo);
  const color = e.tint ?? (marca && !marca.propia ? marca.color : colores.acento);
  const L = useLienzo();
  return (
    <Completa tint={color} semilla={4}>
      <AbsoluteFill style={{ flexDirection: L.vertical ? "column" : "row", alignItems: "center", justifyContent: "center",
                             gap: L.vertical ? 70 : 130, padding: `${L.arriba}px 0 ${L.abajo}px`,
                             opacity: 1 - sal, transform: `translateY(${sal * 30}px)` }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 40 }}>
          {e.logo && (
            <div style={{ transform: `${inclinacion(6, 10)} scale(${2 - impacto}) translate(${temblor}px, ${-temblor * 0.5}px)`,
                          opacity: Math.min(1, impacto * 1.5) }}>
              <FichaMarca ficha={{ logo: e.logo }} logos={logos} alto={170} />
            </div>
          )}
          {e.grid === false && !e.logo ? (
            // Cifra sola (24/7, 4 h…): es el golpe de la escena → grande, en acento y con impacto inmediato
            <div style={{ fontFamily: fuentes.titulares, fontStyle: "italic", fontSize: L.vertical ? 330 : 280, lineHeight: 1,
                          color: color, opacity: Math.min(1, impacto * 1.6),
                          transform: `scale(${1.6 - 0.6 * impacto}) translate(${temblor}px, ${-temblor * 0.5}px)`,
                          textShadow: `0 0 60px ${rgba(color, 0.45)}` }}>
              {e.display ?? `${e.value}`}
            </div>
          ) : (
            <div style={{ fontFamily: fuentes.titulares, fontStyle: "italic", fontSize: 190, lineHeight: 1,
                          color: colores.texto, opacity: prog(frame, 16, 30) }}>
              {e.display ?? `${llenas} %`}
            </div>
          )}
          <div style={{ fontFamily: fuentes.mono, fontSize: e.grid === false && !e.logo ? 34 : 26, letterSpacing: 4,
                        textTransform: "uppercase", color: colores.textoSuave, maxWidth: 560, textAlign: "center",
                        opacity: e.grid === false && !e.logo ? prog(frame, 8, 20) : prog(frame, 24, 40) }}>
            {e.label}
          </div>
          {e.fuente && <Fuente texto={e.fuente} frame={frame} />}
        </div>
        {e.grid !== false && <div style={{ display: "grid", gridTemplateColumns: "repeat(10, 40px)", gap: 9,
                      transform: inclinacion(10, -14), opacity: prog(frame, 10, 24) }}>
          {Array.from({ length: 100 }, (_, i) => {
            const llena = i < llenas;
            return (
              <div key={i} style={{
                width: 40, height: 40, borderRadius: 9,
                background: llena ? `linear-gradient(160deg, ${color}, ${rgba(color, 0.7)})` : rgba(colores.texto, 0.06),
                border: `1px solid ${llena ? rgba("#FFFFFF", 0.3) : rgba(colores.texto, 0.1)}`,
                boxShadow: llena ? `0 6px 18px -6px ${rgba(color, 0.8)}` : undefined,
              }} />
            );
          })}
        </div>}
      </AbsoluteFill>
      <Efecto nombre={e.sfx === undefined ? "sub_hit" : e.sfx} />
      {e.grid !== false && Array.from({ length: Math.min(12, Math.ceil(e.value / 8)) }, (_, k) => (
        <Efecto key={k} nombre="tick" desde={inicioRejilla + Math.round((k * 40) / Math.max(1, Math.ceil(e.value / 8)))} volumen={0.25} />
      ))}
    </Completa>
  );
};

// ─────────────────────────── rise ───────────────────────────
const curvaSuave = (pts: [number, number][]) => {
  // Catmull-Rom → Bézier: curva continua sin picos.
  let d = `M ${pts[0][0]} ${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += ` C ${c1[0]} ${c1[1]}, ${c2[0]} ${c2[1]}, ${p2[0]} ${p2[1]}`;
  }
  return d;
};

export const Rise: React.FC<P<"rise">> = ({ escena: e }) => {
  const { frame, sal } = useEntradaSalida();
  const color = e.tint ?? colores.acento;
  const valores = e.points ?? [8, 10, 13, 18, 26, 38, 55, 78, 100];
  const max = Math.max(...valores);
  const L = useLienzo();
  const [x0, x1, y0, y1] = L.vertical ? [110, L.W - 110, L.H * 0.66, L.H * 0.36] : [300, 1620, 820, 330];
  const pts = valores.map((v, i) => [x0 + ((x1 - x0) * i) / (valores.length - 1), y0 - ((y0 - y1) * v) / max] as [number, number]);
  const d = curvaSuave(pts);
  const avance = prog(frame, 10, 64, easeInOut);
  const largo = 2400;
  const punta = pts[Math.min(pts.length - 1, Math.floor(avance * (pts.length - 1) + 0.0001))];
  const puntaFinal = avance >= 0.999 ? pts[pts.length - 1] : punta;
  return (
    <Completa tint={color} semilla={5}>
      <AbsoluteFill style={{ alignItems: "center", paddingTop: L.vertical ? L.arriba + 40 : 110 }}>
        <Titular texto={e.title} frame={frame} desde={2} inicioEscena={e.from} tam={L.vertical ? 76 : 82} sal={sal} />
      </AbsoluteFill>
      <svg width={L.W} height={L.H} style={{ position: "absolute", inset: 0, opacity: 1 - sal, transform: inclinacion(8, -6) }}>
        <defs>
          <linearGradient id="areaRise" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={color} stopOpacity="0.32" />
            <stop offset="1" stopColor={color} stopOpacity="0" />
          </linearGradient>
          <clipPath id="clipRise"><rect x={0} y={0} width={x0 + (x1 - x0) * avance} height={L.H} /></clipPath>
        </defs>
        {[0, 1, 2, 3].map((k) => (
          <line key={k} x1={x0} x2={x1} y1={y0 - ((y0 - y1) * k) / 3} y2={y0 - ((y0 - y1) * k) / 3}
                stroke={rgba(colores.texto, 0.07)} strokeWidth={1} />
        ))}
        <path d={`${d} L ${x1} ${y0} L ${x0} ${y0} Z`} fill="url(#areaRise)" clipPath="url(#clipRise)" />
        <path d={d} fill="none" stroke={color} strokeWidth={7} strokeLinecap="round"
              strokeDasharray={largo} strokeDashoffset={largo * (1 - avance)}
              style={{ filter: `drop-shadow(0 0 14px ${rgba(color, 0.7)})` }} />
        <circle cx={puntaFinal[0]} cy={puntaFinal[1]} r={13} fill={colores.texto} opacity={avance > 0.02 ? 1 : 0}
                style={{ filter: `drop-shadow(0 0 16px ${color})` }} />
      </svg>
      {e.valueLabel && (
        <div style={{ position: "absolute", left: x1 - 40, top: y1 - 120, transform: "translateX(-100%)",
                      fontFamily: fuentes.titulares, fontStyle: "italic", fontSize: 96, color: colores.texto,
                      opacity: prog(frame, 60, 74) * (1 - sal) }}>{e.valueLabel}</div>
      )}
      <Efecto nombre={e.sfx === undefined ? "swell" : e.sfx} volumen={0.4} />
      <Efecto nombre="nota" desde={62} volumen={0.4} />
    </Completa>
  );
};

// ─────────────────────────── orbChips ───────────────────────────
export const OrbChips: React.FC<P<"orbChips">> = ({ escena: e, logos }) => {
  const { frame, sal } = useEntradaSalida();
  const n = e.chips.length;
  const giro = frame * 0.008;
  const L = useLienzo();
  const cyO = L.vertical ? L.H * 0.47 : 520, rx = L.vertical ? L.W * 0.36 : 640;
  const chips = e.chips.map((c, i) => {
    const a = (i / n) * Math.PI * 2 + giro;
    const z = Math.sin(a);
    const t0 = c.at !== undefined ? f(c.at - e.from) : 12 + i * 6;
    return { c, i, x: L.cx + Math.cos(a) * rx, y: cyO + z * 150, esc: 0.78 + (z + 1) * 0.18, z, ent: prog(frame, t0, t0 + 16), t0 };
  });
  const centro = e.center ?? "isotipo";
  return (
    <Completa tint={e.tint} semilla={6}>
      {e.title && (
        <AbsoluteFill style={{ alignItems: "center", paddingTop: L.vertical ? L.arriba + 20 : 100 }}>
          <Titular texto={e.title} frame={frame} desde={2} inicioEscena={e.from} tam={L.vertical ? 72 : 80} sal={sal} />
        </AbsoluteFill>
      )}
      {chips.filter((c) => c.z < 0).map((c) => <Chip key={c.i} {...c} logos={logos} sal={sal} />)}
      <Esfera frame={frame} radio={190} cy={cyO + 20} n={420} color={e.tint ?? colores.acento} opacidad={prog(frame, 0, 16) * (1 - sal)} />
      {centro === "isotipo" && logosMarca.isotipo ? (
        <Img src={logosMarca.isotipo} style={{ position: "absolute", left: L.cx - 60, top: cyO + 20 - 66, height: 132, width: 120,
             objectFit: "contain", opacity: prog(frame, 6, 22) * (1 - sal), filter: `drop-shadow(0 0 30px ${rgba(colores.acento, 0.7)})` }} />
      ) : centro !== "isotipo" ? (
        <div style={{ position: "absolute", left: 0, right: 0, top: cyO - 20, textAlign: "center", fontFamily: fuentes.titulares,
                      fontStyle: "italic", fontSize: 72, color: colores.texto, opacity: prog(frame, 6, 22) * (1 - sal) }}>{centro}</div>
      ) : null}
      {chips.filter((c) => c.z >= 0).map((c) => <Chip key={c.i} {...c} logos={logos} sal={sal} />)}
      <Efecto nombre={e.sfx === undefined ? "sub_hit" : e.sfx} volumen={0.5} />
      {chips.map((c) => <Efecto key={c.i} nombre="tick" desde={c.t0} volumen={0.3} />)}
    </Completa>
  );
};

const Chip: React.FC<{ c: Ficha; x: number; y: number; esc: number; z: number; ent: number; logos: LogosIndex; sal: number }> = ({
  c, x, y, esc, z, ent, logos, sal,
}) => (
  <div style={{ position: "absolute", left: x, top: y, transform: `translate(-50%, -50%) scale(${esc * (0.6 + 0.4 * ent)})`,
                opacity: ent * (0.55 + 0.45 * (z + 1) / 2) * (1 - sal), filter: `blur(${Math.max(0, -z) * 2.5}px)` }}>
    <FichaMarca ficha={c} logos={logos} alto={104} />
  </div>
);

// ─────────────────────────── dissolve ───────────────────────────
export const Dissolve: React.FC<P<"dissolve">> = ({ escena: e }) => {
  const { frame, dur, sal } = useEntradaSalida();
  const t0 = e.dissolveAt !== undefined ? f(e.dissolveAt - e.from) : Math.round(dur * 0.45);
  const d = prog(frame, t0, t0 + 40, easeInOut);
  const L = useLienzo();
  const tam = L.vertical ? Math.min(230, (L.W - 140) / (e.word.length * 0.44)) : 230;
  const ancho = e.word.length * tam * 0.44;
  const r = azar(e.word.length * 31);
  const polvo = Array.from({ length: 260 }, () => ({
    x: L.cx + (r() - 0.5) * ancho, y: L.cy + (r() - 0.5) * tam * 0.6,
    vx: 80 + r() * 520, vy: -40 - r() * 320, retraso: r() * 0.5, tam: 1.6 + r() * 3.6,
  }));
  return (
    <Completa tint={e.tint} semilla={7} velocidad={3}>
      <svg width={0} height={0} style={{ position: "absolute" }}>
        <filter id="deshacer">
          <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="3" seed="4" />
          <feDisplacementMap in="SourceGraphic" scale={d * 160} xChannelSelector="R" yChannelSelector="G" />
        </filter>
      </svg>
      {e.kicker && (
        <AbsoluteFill style={{ alignItems: "center", paddingTop: L.vertical ? L.cy - tam - 60 : 300 }}>
          <div style={{ fontFamily: fuentes.mono, fontSize: 26, letterSpacing: 5, textTransform: "uppercase",
                        color: colores.textoSuave, opacity: prog(frame, 4, 16) * (1 - sal) }}>{e.kicker}</div>
        </AbsoluteFill>
      )}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <div style={{ fontFamily: fuentes.titulares, fontStyle: "italic", fontSize: tam, color: colores.texto,
                      opacity: prog(frame, 0, 12) * (1 - d), filter: `url(#deshacer) blur(${d * 3}px)`,
                      transform: `translateX(${d * 40}px)` }}>{e.word}</div>
      </AbsoluteFill>
      <svg width={L.W} height={L.H} style={{ position: "absolute", inset: 0 }}>
        {polvo.map((p, i) => {
          const k = Math.max(0, Math.min(1, (d - p.retraso * 0.6) / 0.6));
          if (k <= 0) return null;
          return <circle key={i} cx={p.x + p.vx * k} cy={p.y + p.vy * k} r={p.tam * (1 - k * 0.5)}
                         fill={i % 4 === 0 ? colores.acento : colores.texto} opacity={Math.min(1, (1 - k) * 1.4)} />;
        })}
      </svg>
      <Efecto nombre={e.sfx === undefined ? "nota_mi" : e.sfx} volumen={0.4} />
      <Efecto nombre="whoosh" desde={t0} volumen={0.5} />
    </Completa>
  );
};

// ─────────────────────────── outro ───────────────────────────
export const Outro: React.FC<P<"outro">> = ({ escena: e }) => {
  const { frame, sal } = useEntradaSalida(10, 20);
  const exp = interpolate(frame, [6, 60], [1, 5.5], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeInOut });
  const L = useLienzo();
  return (
    <Completa tint={e.tint} semilla={8} velocidad={9}>
      <Esfera frame={frame} radio={240} expansion={exp} opacidad={interpolate(exp, [1, 5.5], [1, 0])} color={e.tint ?? colores.acento} />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", gap: 34 }}>
        {e.kicker && (
          <div style={{ fontFamily: fuentes.mono, fontSize: 26, letterSpacing: 6, textTransform: "uppercase",
                        color: colores.acento, opacity: prog(frame, 30, 44) * (1 - sal) }}>{e.kicker}</div>
        )}
        <Titular texto={e.title} frame={frame} desde={36} inicioEscena={e.from} tam={L.vertical ? 92 : 112} sal={sal} />
      </AbsoluteFill>
      {logosMarca.logotipo && (
        <Img src={logosMarca.logotipo} style={{ position: "absolute", left: L.cx - 130, bottom: L.vertical ? L.abajo : 70, width: 260,
             opacity: 0.32 * prog(frame, 44, 64) * (1 - sal) }} />
      )}
      <Efecto nombre={e.sfx === undefined ? "swell" : e.sfx} volumen={0.4} />
      <Efecto nombre="sub_hit" desde={34} volumen={0.45} />
    </Completa>
  );
};

/** Fuente de un dato: pequeña, en mono, sin competir con la cifra. */
export const Fuente: React.FC<{ texto: string; frame: number; desde?: number }> = ({ texto, frame, desde = 30 }) => (
  <div style={{ fontFamily: fuentes.mono, fontSize: 24, letterSpacing: 2, color: colores.textoSuave,
                textTransform: "uppercase", opacity: prog(frame, desde, desde + 14), textAlign: "center" }}>
    Fuente: {texto}
  </div>
);

// ─────────────────────────── bars ───────────────────────────
/** Barras horizontales comparativas (56 % vs 28 %…). La que importa, en acento; el resto en cristal. */
export const Bars: React.FC<P<"bars">> = ({ escena: e }) => {
  const { frame, sal } = useEntradaSalida();
  const L = useLienzo();
  const ancho = L.vertical ? L.W - 160 : 1340;
  return (
    <Completa tint={e.tint} semilla={9}>
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", gap: 44,
                             padding: `${L.arriba}px 0 ${L.abajo}px`, opacity: 1 - sal, transform: `translateY(${sal * 30}px)` }}>
        {e.title && <Titular texto={e.title} frame={frame} desde={2} inicioEscena={e.from} tam={L.vertical ? 74 : 88} />}
        <div style={{ display: "flex", flexDirection: "column", gap: 34, width: ancho, transform: inclinacion(6, -8) }}>
          {e.items.map((it, i) => {
            const t0 = it.at !== undefined ? f(it.at - e.from) : 8 + i * 10;
            const k = prog(frame, t0, t0 + 26, easeInOut);
            const color = it.accent ? colores.acento : colores.texto;
            return (
              <div key={i} style={{ display: "flex", flexDirection: "column", gap: 12, opacity: prog(frame, t0 - 4, t0 + 6) }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                  <span style={{ fontFamily: fuentes.texto, fontWeight: 600, fontSize: L.vertical ? 42 : 48, color: colores.texto }}>{it.label}</span>
                  <span style={{ fontFamily: fuentes.titulares, fontStyle: "italic", fontSize: L.vertical ? 96 : 120, lineHeight: 1,
                                 color: it.accent ? colores.acento : colores.texto }}>
                    {it.display ?? `${Math.round(it.value * k)} %`}
                  </span>
                </div>
                <div style={{ height: 38, borderRadius: 19, background: rgba(colores.texto, 0.07),
                              border: `1px solid ${rgba(colores.texto, 0.1)}`, overflow: "hidden" }}>
                  <div style={{ width: `${it.value * k}%`, height: "100%", borderRadius: 15,
                                background: it.accent ? `linear-gradient(90deg, ${rgba(color, 0.75)}, ${color})` : rgba(colores.texto, 0.55),
                                boxShadow: it.accent ? `0 0 26px ${rgba(colores.acento, 0.6)}` : undefined }} />
                </div>
                <Efecto nombre="tick" desde={t0} volumen={0.3} />
              </div>
            );
          })}
        </div>
        {e.fuente && <Fuente texto={e.fuente} frame={frame} desde={20} />}
      </AbsoluteFill>
      <Efecto nombre={e.sfx === undefined ? "whoosh" : e.sfx} volumen={0.4} />
    </Completa>
  );
};

// ─────────────────────────── broll ───────────────────────────
/** Plano de apoyo a pantalla completa (sin sonido: la voz sigue), con zoom lento y fundidos cortos. */
export const Broll: React.FC<P<"broll">> = ({ escena: e }) => {
  const { frame, dur, ent, sal } = useEntradaSalida(8, 10);
  return (
    <AbsoluteFill style={{ opacity: ent * (1 - sal), backgroundColor: colores.fondo }}>
      <AbsoluteFill style={{ transform: `scale(${1.02 + 0.06 * (frame / Math.max(dur, 1))})` }}>
        <OffthreadVideo src={staticFile(e.src)} muted startFrom={Math.round((e.startFrom ?? 0) * 30)}
                        style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </AbsoluteFill>
      <AbsoluteFill style={{ background: `linear-gradient(180deg, transparent 70%, ${rgba(colores.fondo, 0.55)} 100%)` }} />
      {e.label && (
        <div style={{ position: "absolute", left: 70, bottom: 60, fontFamily: fuentes.mono, fontSize: 24, letterSpacing: 4,
                      textTransform: "uppercase", color: colores.textoSuave, opacity: prog(frame, 8, 20) }}>{e.label}</div>
      )}
      <Efecto nombre={e.sfx === undefined ? "whoosh" : e.sfx} volumen={0.25} />
    </AbsoluteFill>
  );
};
