// Sistema visual de los anuncios de producto (composición Anuncio): mundo claro con objetos 3D flotantes,
// tipografía cinética con palabras resaltadas, barridos con formas orgánicas, paneles de la app en 3D y cursor.
// Colores SIEMPRE derivados de marca.json (marca blanca).
import React, { useMemo } from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { colores, fuentes } from "../marca";
import { azar, easeInOut, easeOut, mezclar, prog, rgba } from "../lib/util";

/** Centro vertical de los paneles de app: en 9:16 por encima de la zona que tapan las apps. */
export const panelY = (movil: boolean) => (movil ? 0.56 : 0.6);

export const P = {
  claro: mezclar(colores.brillo, "#FFFFFF", 0.62),
  claro2: mezclar(colores.brillo, "#FFFFFF", 0.25),
  tinta: colores.fondo,
  acento: colores.acento,
  acento2: colores.acento2,
  panel: colores.superficie,
  panel2: colores.superficie2,
  borde: colores.borde,
  texto: colores.texto,
  suave: colores.textoSuave,
  aviso: colores.etiqueta,
  alerta: "#F05252",
};

/** Medidas del lienzo: u = 1 px de diseño a 1080 de ancho. */
export const useLienzoPromo = () => {
  const { width: W, height: H, fps } = useVideoConfig();
  const movil = H / W > 1.6;
  return { W, H, fps, u: W / 1080, movil, cx: W / 2, cy: H / 2, arriba: movil ? 230 : 80, abajo: movil ? 450 : 90 };
};

/** Segundos absolutos del anuncio → fotograma local de la escena. */
export const useT = (desde: number) => {
  const { fps } = useVideoConfig();
  return (s: number) => Math.round((s - desde) * fps);
};

export const resorte = (frame: number, at: number, fps: number, damping = 12, stiffness = 160) =>
  spring({ frame: frame - at, fps, config: { damping, stiffness, mass: 0.8 } });

// ─────────────────────────── fondo ───────────────────────────
export const Mundo: React.FC<{ oscuro?: boolean; semilla?: number }> = ({ oscuro, semilla = 1 }) => {
  const frame = useCurrentFrame();
  const { W, H } = useLienzoPromo();
  const base = oscuro ? P.tinta : P.claro;
  const manchas = [0, 1, 2].map((i) => {
    const a = semilla * 1.7 + i * 2.1;
    return { x: W * (0.5 + 0.38 * Math.sin(frame / 90 + a)), y: H * (0.45 + 0.3 * Math.cos(frame / 110 + a * 1.3)),
             r: W * (0.55 + 0.1 * i), c: i === 1 ? P.acento2 : P.acento };
  });
  return (
    <AbsoluteFill style={{ backgroundColor: base, overflow: "hidden" }}>
      {manchas.map((m, i) => (
        <div key={i} style={{ position: "absolute", left: m.x - m.r, top: m.y - m.r, width: m.r * 2, height: m.r * 2,
                              borderRadius: "50%", filter: "blur(60px)",
                              background: `radial-gradient(circle, ${rgba(m.c, oscuro ? 0.22 : 0.2)} 0%, transparent 65%)` }} />
      ))}
      <AbsoluteFill style={{ backgroundImage: `radial-gradient(${rgba(oscuro ? P.texto : P.tinta, oscuro ? 0.07 : 0.06)} 1.6px, transparent 1.6px)`,
                             backgroundSize: "34px 34px", backgroundPosition: `${(frame * 0.4) % 34}px ${(frame * 0.6) % 34}px` }} />
    </AbsoluteFill>
  );
};

// ─────────────────────────── objetos 3D flotantes ───────────────────────────
export type Flotante = { src: string; x: number; y: number; tam: number; rot?: number; prof?: number; at?: number };
/** Objetos 3D (PNG con alfa) que entran con resorte y flotan con paralaje. x, y en fracción del lienzo. */
export const Flotantes: React.FC<{ items: Flotante[]; sal?: number; desplaza?: [number, number] }> = ({ items, sal = 0, desplaza = [0, 0] }) => {
  const frame = useCurrentFrame();
  const { W, H, u, fps } = useLienzoPromo();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {items.map((o, i) => {
        const k = resorte(frame, o.at ?? i * 3, fps, 10, 140);
        const prof = o.prof ?? 1;
        const fl = Math.sin(frame / 22 + i * 1.9) * 14 * u;
        const x = o.x * W + desplaza[0] * prof * u - (o.tam * u) / 2;
        const y = o.y * H + desplaza[1] * prof * u + fl - (o.tam * u) / 2;
        const rot = (o.rot ?? 0) + Math.sin(frame / 30 + i) * 6;
        return (
          <Img key={i} src={staticFile(o.src)} style={{
            position: "absolute", left: x, top: y, width: o.tam * u, height: o.tam * u, objectFit: "contain",
            transform: `scale(${k * (1 - sal)}) rotate(${rot}deg)`, filter: `drop-shadow(0 ${24 * u}px ${30 * u}px rgba(0,0,0,0.22)) blur(${prof < 0.7 ? 2 : 0}px)`,
            opacity: Math.min(1, k * 1.4) * (1 - sal) }} />
        );
      })}
    </AbsoluteFill>
  );
};

// ─────────────────────────── tipografía cinética ───────────────────────────
type Pal = { t: string; acento: boolean };
const partir = (linea: string): Pal[] => {
  const res: Pal[] = [];
  let dentro = false;
  for (const tok of linea.split(/\s+/).filter(Boolean)) {
    const abre = tok.startsWith("*"), cierra = tok.endsWith("*");
    if (abre) dentro = true;
    res.push({ t: tok.replace(/\*/g, ""), acento: dentro });
    if (cierra) dentro = false;
  }
  return res;
};

const grupos = (pals: Pal[]): Pal[][] => {
  const res: Pal[][] = [];
  for (const p of pals) {
    const ult = res[res.length - 1];
    if (p.acento && ult && ult[0].acento) ult.push(p);
    else res.push([p]);
  }
  return res;
};

/**
 * Titular que entra palabra a palabra (resorte, desde abajo y algo girado). Las palabras *acento* llevan un bloque
 * del color de acento que se dibuja de izquierda a derecha. `at[i]` = fotograma local de cada palabra.
 */
export const Titular: React.FC<{
  lineas: string[]; at?: number[]; desde?: number; paso?: number; tam?: number; color?: string; alinear?: "center" | "left";
  sal?: number; ancho?: number; colorAcento?: string; tintaAcento?: string;
}> = ({ lineas, at, desde = 0, paso = 4, tam = 110, color = P.tinta, alinear = "center", sal = 0, ancho, colorAcento = P.acento, tintaAcento = P.tinta }) => {
  const frame = useCurrentFrame();
  const { u, fps, W } = useLienzoPromo();
  let n = 0;
  const T = tam * u;
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: alinear === "center" ? "center" : "flex-start",
                  gap: T * 0.06, width: ancho ? ancho * u : W - 120 * u }}>
      {lineas.map((l, li) => (
        <div key={li} style={{ display: "flex", flexWrap: "wrap", justifyContent: alinear === "center" ? "center" : "flex-start",
                               gap: `${T * 0.08}px ${T * 0.24}px` }}>
          {grupos(partir(l)).map((g, gi) => {
            // un grupo = una palabra normal o varias de acento seguidas (no se parten de línea y comparten bloque)
            const t0g = at?.[n] ?? desde + n * paso;
            const kb = prog(frame, t0g + 2, t0g + 12 + (g.length - 1) * 3, easeInOut);
            const acento = g[0].acento;
            return (
              <span key={gi} style={{ position: "relative", display: "inline-flex", gap: T * 0.24, whiteSpace: "nowrap",
                                      padding: acento ? `0 ${T * 0.12}px` : undefined, opacity: 1 - sal, filter: `blur(${sal * 10}px)` }}>
                {acento && (
                  <span style={{ position: "absolute", top: T * 0.04, bottom: -T * 0.02, left: 0, right: 0, borderRadius: T * 0.2,
                                 background: `linear-gradient(120deg, ${colorAcento}, ${mezclar(colorAcento, P.acento2, 0.5)})`,
                                 transformOrigin: "left center", transform: `scaleX(${kb})`, zIndex: 0,
                                 boxShadow: `0 ${T * 0.12}px ${T * 0.3}px -${T * 0.12}px ${rgba(colorAcento, 0.8)}` }} />
                )}
                {g.map((w, wi) => {
                  const t0 = at?.[n] ?? desde + n * paso;
                  n++;
                  const k = resorte(frame, t0, fps, 11, 170);
                  return (
                    <span key={wi} style={{ position: "relative", zIndex: 1, display: "inline-block", fontFamily: fuentes.texto, fontWeight: 800,
                                            fontSize: T, lineHeight: 1.04, letterSpacing: "-0.035em", color: w.acento ? tintaAcento : color,
                                            opacity: Math.min(1, k * 1.5),
                                            transform: `translateY(${(1 - k) * T * 0.55 - sal * T * 0.4}px) rotate(${(1 - k) * 7}deg) scale(${0.85 + 0.15 * k})` }}>{w.t}</span>
                  );
                })}
              </span>
            );
          })}
        </div>
      ))}
    </div>
  );
};

/** Rótulo de escena de app: titular pequeño arriba (sirve de subtítulo cuando se ve sin sonido). */
export const Rotulo: React.FC<{ texto: string; at?: number; sal?: number; color?: string }> = ({ texto, at = 0, sal = 0, color }) => {
  const { arriba, u, movil } = useLienzoPromo();
  return (
    <AbsoluteFill style={{ alignItems: "center", paddingTop: arriba + (movil ? 40 : 10) * u }}>
      <Titular lineas={[texto]} desde={at} paso={3} tam={movil ? 84 : 70} sal={sal} color={color} ancho={940} />
    </AbsoluteFill>
  );
};

// ─────────────────────────── barrido orgánico ───────────────────────────
const blob = (cx: number, cy: number, r: number, fase: number, n = 9) => {
  const pts: [number, number][] = [];
  for (let i = 0; i < 64; i++) {
    const a = (i / 64) * Math.PI * 2;
    const rr = r * (1 + 0.1 * Math.sin(a * 3 + fase) + 0.06 * Math.sin(a * n - fase * 1.3));
    pts.push([cx + rr * Math.cos(a), cy + rr * Math.sin(a)]);
  }
  return "M" + pts.map((p) => p.map((v) => v.toFixed(1)).join(",")).join("L") + "Z";
};
const circulo = (cx: number, cy: number, r: number) =>
  `M${cx - r},${cy}a${r},${r} 0 1,0 ${r * 2},0a${r},${r} 0 1,0 ${-r * 2},0Z`;

/**
 * Transición: una mancha orgánica crece desde (x, y) hasta cubrir la pantalla (fotogramas en-dur..en) y luego se
 * abre un agujero en el centro que deja ver la escena siguiente (en..en+dur). Montar en la capa superior.
 */
export const Barrido: React.FC<{ en: number; x?: number; y?: number; color?: string; dur?: number }> = ({ en, x = 0.5, y = 0.5, color = P.acento, dur = 10 }) => {
  const frame = useCurrentFrame();
  const { W, H } = useLienzoPromo();
  if (frame < en - dur || frame > en + dur + 2) return null;
  const R = Math.hypot(W, H);
  const crece = prog(frame, en - dur, en, easeInOut);
  const abre = prog(frame, en, en + dur, easeInOut);
  const cx = W * x, cy = H * y;
  const d = blob(cx, cy, R * 0.75 * crece, frame / 6) + (abre > 0 ? circulo(W / 2, H / 2, R * 0.62 * abre) : "");
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <svg width={W} height={H}><path d={d} fill={color} fillRule="evenodd" /></svg>
    </AbsoluteFill>
  );
};

// ─────────────────────────── panel 3D ───────────────────────────
/** Panel de la app (oscuro) inclinado en 3D. rx/ry/rz en grados; escala; el contenido en px de diseño. */
export const Panel3D: React.FC<{ ancho: number; alto?: number; rx: number; ry: number; rz?: number; escala?: number;
                                 x?: number; y?: number; children: React.ReactNode; opacidad?: number; radio?: number }> =
  ({ ancho, alto, rx, ry, rz = 0, escala = 1, x = 0.5, y = 0.55, children, opacidad = 1, radio = 34 }) => {
  const { W, H, u } = useLienzoPromo();
  return (
    <div style={{ position: "absolute", left: W * x, top: H * y, width: ancho * u,
                  height: alto ? alto * u : undefined, opacity: opacidad,
                  // centrado en (x, y) también sin alto fijo (antes se anclaba por arriba y bajaba fuera de la zona segura)
                  transform: `translate(-50%, -50%) perspective(${1800 * u}px) rotateX(${rx}deg) rotateY(${ry}deg) rotateZ(${rz}deg) scale(${escala})`,
                  transformStyle: "preserve-3d" }}>
      <div style={{ width: "100%", height: "100%", borderRadius: radio * u, background: `linear-gradient(165deg, ${P.panel2} 0%, ${P.panel} 38%, ${P.tinta} 100%)`,
                    border: `${1.5 * u}px solid ${rgba(P.texto, 0.12)}`, overflow: "hidden",
                    boxShadow: `0 ${60 * u}px ${120 * u}px -${30 * u}px rgba(0,0,0,0.55), 0 0 0 ${1 * u}px rgba(0,0,0,0.4), inset 0 ${1 * u}px 0 ${rgba("#FFFFFF", 0.12)}` }}>
        {children}
      </div>
    </div>
  );
};

/** Movimiento de cámara típico de los paneles: llega inclinado y se endereza un poco, con deriva lenta. */
export const useInclinacion = (dur: number, ini: [number, number, number] = [22, -18, 6], fin: [number, number, number] = [9, -7, 2]) => {
  const frame = useCurrentFrame();
  const { fps } = useLienzoPromo();
  const k = resorte(frame, 0, fps, 16, 90);
  const deriva = frame / Math.max(dur, 1);
  return {
    rx: interpolate(k, [0, 1], [ini[0] + 30, fin[0]]) - deriva * 3,
    ry: interpolate(k, [0, 1], [ini[1] - 20, fin[1]]) + deriva * 5,
    rz: interpolate(k, [0, 1], [ini[2] + 8, fin[2]]),
    escala: interpolate(k, [0, 1], [0.7, 1]) + deriva * 0.06,
    k,
  };
};

// ─────────────────────────── piezas de la app ───────────────────────────
export const Chip: React.FC<{ texto: string; color: string; u: number; tam?: number; lleno?: boolean; style?: React.CSSProperties }> =
  ({ texto, color, u, tam = 24, lleno = false, style }) => (
  <span style={{ display: "inline-flex", alignItems: "center", padding: `${tam * 0.22 * u}px ${tam * 0.55 * u}px`, borderRadius: 999,
                 fontFamily: fuentes.texto, fontWeight: 700, fontSize: tam * u, lineHeight: 1, whiteSpace: "nowrap",
                 color: lleno ? P.tinta : color, background: lleno ? color : rgba(color, 0.16), border: `${1.5 * u}px solid ${rgba(color, 0.55)}`, ...style }}>{texto}</span>
);

export const Boton: React.FC<{ texto: string; u: number; tam?: number; pulsado?: number; style?: React.CSSProperties }> = ({ texto, u, tam = 28, pulsado = 0, style }) => (
  <span style={{ display: "inline-flex", alignItems: "center", gap: 10 * u, padding: `${tam * 0.5 * u}px ${tam * 0.9 * u}px`, borderRadius: tam * 0.4 * u,
                 background: `linear-gradient(160deg, ${P.acento}, ${mezclar(P.acento, P.acento2, 0.4)})`, color: P.tinta,
                 fontFamily: fuentes.texto, fontWeight: 800, fontSize: tam * u, whiteSpace: "nowrap",
                 transform: `scale(${1 - 0.08 * pulsado})`, boxShadow: `0 ${10 * u}px ${30 * u}px -${8 * u}px ${rgba(P.acento, 0.8 - 0.4 * pulsado)}`, ...style }}>{texto}</span>
);

/** Cursor que viaja hasta (x, y) [px de pantalla] y pulsa en `clic` (fotograma local), con onda. */
export const Cursor: React.FC<{ desde: [number, number]; hasta: [number, number]; llega: number; clic: number; aparece?: number; sal?: number }> =
  ({ desde, hasta, llega, clic, aparece = 0, sal = 0 }) => {
  const frame = useCurrentFrame();
  const { u } = useLienzoPromo();
  if (frame < aparece) return null;
  const k = prog(frame, aparece, llega, easeInOut);
  const x = desde[0] + (hasta[0] - desde[0]) * k, y = desde[1] + (hasta[1] - desde[1]) * k + Math.sin(k * Math.PI) * -60 * u;
  const pulsa = frame >= clic - 3 && frame <= clic + 4 ? 1 - Math.abs(frame - clic) / 4 : 0;
  const onda = prog(frame, clic, clic + 16, easeOut);
  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: 1 - sal }}>
      {frame >= clic && onda < 1 && (
        <div style={{ position: "absolute", left: hasta[0] - 70 * u * onda, top: hasta[1] - 70 * u * onda, width: 140 * u * onda, height: 140 * u * onda,
                      borderRadius: "50%", border: `${4 * u}px solid ${rgba(P.acento, 1 - onda)}`, background: rgba(P.acento, 0.25 * (1 - onda)) }} />
      )}
      <svg width={64 * u} height={64 * u} viewBox="0 0 24 24" style={{ position: "absolute", left: x - 6 * u, top: y - 4 * u,
           transform: `scale(${1 - 0.18 * pulsa})`, filter: `drop-shadow(0 ${6 * u}px ${10 * u}px rgba(0,0,0,0.35))` }}>
        <path d="M4 2 L4 19 L8.5 14.8 L11.6 21.5 L14.4 20.3 L11.4 13.7 L17.6 13.7 Z" fill="#FFFFFF" stroke={P.tinta} strokeWidth="1.4" strokeLinejoin="round" />
      </svg>
    </AbsoluteFill>
  );
};

/** Partículas que estallan desde un punto (éxito, revelado). */
export const Estallido: React.FC<{ x: number; y: number; en: number; n?: number; radio?: number; color?: string }> = ({ x, y, en, n = 26, radio = 420, color = P.acento }) => {
  const frame = useCurrentFrame();
  const { u } = useLienzoPromo();
  const parts = useMemo(() => {
    const r = azar(n * 7 + Math.round(x));
    return Array.from({ length: n }, () => ({ a: r() * Math.PI * 2, d: 0.4 + r() * 0.6, t: 6 + r() * 14, f: r() }));
  }, [n, x]);
  if (frame < en) return null;
  const k = prog(frame, en, en + 30, easeOut);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {parts.map((p, i) => {
        const dd = p.d * radio * u * k;
        const s = p.t * u * (1 - k * 0.7);
        return <div key={i} style={{ position: "absolute", left: x + Math.cos(p.a) * dd - s / 2, top: y + Math.sin(p.a) * dd - s / 2,
                                     width: s, height: p.f > 0.6 ? s * 2.4 : s, borderRadius: 99, opacity: 1 - k,
                                     background: p.f > 0.5 ? color : P.acento2, transform: `rotate(${p.a}rad)` }} />;
      })}
    </AbsoluteFill>
  );
};
