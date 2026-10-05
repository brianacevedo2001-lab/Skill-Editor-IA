// Cámara virtual y escenas que van SOBRE la cámara (callout, lowerThird, autoLogos).
import React from "react";
import { AbsoluteFill, Freeze, Img, OffthreadVideo, staticFile, useCurrentFrame } from "remotion";
import { colores, fuentes, logos as logosMarca, marca } from "../marca";
import type { Cuts, Escena, LogosIndex } from "../types";
import { Bloque, Efecto, FichaMarca, inclinacion, palabrasConAcento } from "../componentes/piezas";
import { f, prog, rgba, ruidoSuave, useEntradaSalida } from "../lib/util";

// ─────────────────────────── cámara virtual ───────────────────────────
/**
 * Punch-in (zoom a la cara) alterno en cada corte para disimular los jump cuts: 1 ↔ 1+punch.
 * Como mucho un 9 % (16–22 % queda exagerado). Cortes a menos de 1,2 s del anterior no alternan.
 */
export const escalasPunchIn = (cuts: Cuts | null, punch: number) => {
  const p = Math.min(Math.max(punch, 0), 0.09);
  const cambios: { desde: number; escala: number }[] = [{ desde: 0, escala: 1 }];
  if (!cuts) return cambios;
  let ultimo = 0, arriba = false;
  for (const s of cuts.segmentos.slice(1)) {
    const t = f(s.cut[0]);
    if (t - ultimo < f(1.2)) continue;
    arriba = !arriba;
    cambios.push({ desde: t, escala: arriba ? 1 + p : 1 });
    ultimo = t;
  }
  return cambios;
};

export const Camara: React.FC<{
  src: string;
  fotogramasVideo: number;
  escalas: { desde: number; escala: number }[];
  foco: [number, number];
  desenfoque: number;       // 0..1
  handheld: boolean;
  /** Fotograma del vídeo en el que empieza (para usarla dentro de una Sequence). */
  inicio?: number;
  silenciada?: boolean;
  style?: React.CSSProperties;
  /** Encuadre del recorte con objectFit cover (p. ej. vertical 9:16 de un vídeo 16:9): fracción x, y. */
  posicion?: [number, number];
  /** Vídeo con alfa (persona recortada): sin fondo y con `transparent` en OffthreadVideo. */
  transparente?: boolean;
  /** Filtro extra sobre el vídeo (p. ej. el halo de la persona). */
  filtro?: string;
}> = ({ src, fotogramasVideo, escalas, foco, desenfoque, handheld, inicio = 0, silenciada = false, style, posicion,
        transparente = false, filtro }) => {
  const local = useCurrentFrame();
  const frame = local + inicio;
  let escala = 1;
  for (const c of escalas) if (frame >= c.desde) escala = c.escala;
  const t = frame / 30;
  const mano = handheld
    ? `translate(${ruidoSuave(t, 1) * 4}px, ${ruidoSuave(t, 7) * 3}px) rotate(${ruidoSuave(t, 3) * 0.12}deg)`
    : "";
  const video = (
    <OffthreadVideo src={staticFile(src)} startFrom={inicio} muted={silenciada} pauseWhenBuffering transparent={transparente}
                    style={{ width: "100%", height: "100%", objectFit: "cover",
                           objectPosition: posicion ? `${posicion[0] * 100}% ${posicion[1] * 100}%` : undefined }} />
  );
  const pasado = frame >= fotogramasVideo;
  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: transparente ? undefined : colores.fondo, ...style }}>
      <AbsoluteFill style={{
        transform: `${mano} scale(${escala * (1 + desenfoque * 0.04)})`,
        transformOrigin: `${foco[0] * 100}% ${foco[1] * 100}%`,
        filter: [desenfoque > 0.001 ? `blur(${desenfoque * 26}px) brightness(${1 - desenfoque * 0.38}) saturate(${1 - desenfoque * 0.25})` : "",
                 filtro ?? ""].join(" ").trim() || undefined,
      }}>
        {/* Si una animación pasa del final del clip, se congela el último fotograma. */}
        {pasado ? <Freeze frame={fotogramasVideo - 1 - inicio}>{video}</Freeze> : video}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** Intensidad de desenfoque de la cámara (0..1) por las escenas que lo piden. */
export const desenfoqueEn = (frame: number, escenas: Escena[]) => {
  let d = 0;
  for (const e of escenas) {
    if (e.type !== "callout" && e.type !== "subscribe") continue;
    const a = f(e.from), b = f(e.to);
    const v = Math.min(prog(frame, a - 2, a + 8), 1 - prog(frame, b - 12, b));
    d = Math.max(d, v);
  }
  return d;
};

// ─────────────────────────── callout ───────────────────────────
export const Callout: React.FC<{ escena: Extract<Escena, { type: "callout" }>; tam?: number }> = ({ escena: e, tam: tamFijo }) => {
  const { frame, sal } = useEntradaSalida(10, 14);
  let k = 0;
  const tam = tamFijo ?? (e.lines.join(" ").length > 36 ? 104 : 128);
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", gap: tam * 0.2,
                           transform: `${inclinacion(6, -6)} translateY(${sal * -30}px)`, opacity: 1 - sal }}>
      {e.lines.map((linea, li) => {
        // Agrupa palabras consecutivas del mismo tipo en un bloque.
        const grupos: { acento: boolean; pals: { t: string; idx: number }[] }[] = [];
        for (const p of palabrasConAcento(linea)) {
          const g = grupos[grupos.length - 1];
          const item = { t: p.t, idx: k++ };
          if (g && g.acento === p.acento) g.pals.push(item);
          else grupos.push({ acento: p.acento, pals: [item] });
        }
        return (
          <div key={li} style={{ display: "flex", gap: tam * 0.16, alignItems: "center" }}>
            {grupos.map((g, gi) => {
              const t0 = e.wordsAt?.[g.pals[0].idx] !== undefined ? f(e.wordsAt[g.pals[0].idx] - e.from) : 2 + g.pals[0].idx * 3;
              const ent = prog(frame, t0, t0 + 12);
              return (
                <div key={gi} style={{ opacity: ent, transform: `translateY(${(1 - ent) * 40}px) scale(${0.92 + 0.08 * ent})` }}>
                  <Bloque variante={g.acento ? "acento" : "cristal"}
                          style={{ fontFamily: fuentes.titulares, fontStyle: "italic", fontSize: tam, lineHeight: 1.05 }}>
                    {g.pals.map((p, pi) => {
                      const tp = e.wordsAt?.[p.idx] !== undefined ? f(e.wordsAt[p.idx] - e.from) : 2 + p.idx * 3;
                      const ep = prog(frame, tp, tp + 10);
                      return (
                        <span key={pi} style={{ opacity: ep, filter: `blur(${(1 - ep) * 8}px)` }}>
                          {pi ? " " : ""}{p.t}
                        </span>
                      );
                    })}
                  </Bloque>
                </div>
              );
            })}
          </div>
        );
      })}
      <Efecto nombre={e.sfx === undefined ? "nota" : e.sfx} volumen={0.35} />
    </AbsoluteFill>
  );
};

// ─────────────────────────── lowerThird ───────────────────────────
export const LowerThird: React.FC<{ escena: Extract<Escena, { type: "lowerThird" }> }> = ({ escena: e }) => {
  const { frame, sal } = useEntradaSalida(16, 16);
  const ent = prog(frame, 0, 18);
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", padding: "0 0 110px 110px" }}>
      <div style={{ transform: `${inclinacion(4, 12)} translateX(${(1 - ent) * -80 - sal * 60}px)`, opacity: ent * (1 - sal),
                    alignSelf: "flex-start" }}>
        <Bloque radio={26} style={{ display: "flex", alignItems: "center", gap: 28, padding: "26px 40px 26px 30px",
                                     // fondo oscuro de marca: legible también sobre pantallas claras (grueso)
                                     background: `linear-gradient(160deg, ${rgba(colores.superficie, 0.92)} 0%, ${rgba(colores.fondo, 0.88)} 100%)` }}>
          {logosMarca.isotipo && <Img src={logosMarca.isotipo} style={{ height: 84, width: 76, objectFit: "contain" }} />}
          <div style={{ width: 2, height: 80, background: `linear-gradient(${colores.acento}, ${colores.acento2})`,
                        transform: `scaleY(${prog(frame, 8, 22)})` }} />
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div style={{ fontFamily: fuentes.texto, fontWeight: 700, fontSize: 50, color: colores.texto, letterSpacing: "-0.01em",
                          opacity: prog(frame, 6, 20) }}>{marca.persona.nombre}</div>
            <div style={{ fontFamily: fuentes.mono, fontSize: 24, letterSpacing: 3, textTransform: "uppercase",
                          color: colores.textoSuave, opacity: prog(frame, 12, 26) }}>{marca.persona.cargo}</div>
          </div>
        </Bloque>
      </div>
      <Efecto nombre={e.sfx === undefined ? "whoosh" : e.sfx} volumen={0.35} />
    </AbsoluteFill>
  );
};

// ─────────────────────────── autoLogos ───────────────────────────
export interface EventoLogo { slug: string; at: number; lado: "izq" | "der" }

/**
 * Ficha 3D con el logo cada vez que se nombra una marca de logos/index.json, solo en tramos a cámara.
 * Nunca para «mi canal» / «este vídeo»; alias bloqueados (palabras comunes) no cuentan; la misma marca
 * no se repite en menos de 8 s.
 */
export const eventosLogos = (
  palabras: { w: string; inicio: number }[], logos: LogosIndex, escenas: Escena[], excluir: string[] = [],
): EventoLogo[] => {
  const norm = (s: string) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^\p{L}\p{N}. ]/gu, "").trim();
  const ws = palabras.map((p) => ({ n: norm(p.w).replace(/\.$/, ""), t: p.inicio }));
  const bloqueados = new Set(logos.bloqueados.map(norm));
  const ocupado = (t: number) => escenas.some((e) => e.type !== "lowerThird" && t >= e.from - 0.3 && t <= e.to + 0.3);
  const res: EventoLogo[] = [];
  const ultimo: Record<string, number> = {};
  for (let i = 0; i < ws.length; i++) {
    for (const m of logos.marcas) {
      if (excluir.includes(m.slug)) continue;
      const alias = m.alias.map(norm).filter((a) => !bloqueados.has(a));
      const hit = alias.find((a) => {
        const partes = a.split(" ");
        return partes.every((p, k) => ws[i + k]?.n === p);
      });
      if (!hit) continue;
      const previas = ws.slice(Math.max(0, i - 3), i).map((w) => w.n).join(" ");
      if (/\b(mi|este|esta)\s*$/.test(previas) && /(canal|video)/.test(hit)) continue;
      if (/\bmi canal\b|\beste video\b/.test(`${previas} ${hit}`)) continue;
      const t = ws[i].t;
      if (ocupado(t) || (ultimo[m.slug] !== undefined && t - ultimo[m.slug] < 8)) continue;
      ultimo[m.slug] = t;
      res.push({ slug: m.slug, at: t, lado: res.length % 2 ? "izq" : "der" });
    }
  }
  return res;
};

export const AutoLogo: React.FC<{ ev: EventoLogo; logos: LogosIndex }> = ({ ev, logos }) => {
  const { frame, sal } = useEntradaSalida(12, 14);
  const ent = prog(frame, 0, 14);
  const izq = ev.lado === "izq";
  return (
    <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: izq ? "flex-start" : "flex-end", padding: "170px 150px" }}>
      <div style={{
        transform: `${inclinacion(8 + (1 - ent) * 25, izq ? 14 : -14)} translateY(${(1 - ent) * 50 + sal * 30}px) scale(${0.85 + 0.15 * ent})`,
        opacity: ent * (1 - sal), filter: `blur(${sal * 6}px)`,
      }}>
        <FichaMarca ficha={{ logo: ev.slug }} logos={logos} alto={128} />
      </div>
      <Efecto nombre="nota_mi" volumen={0.22} pan={izq ? -0.6 : 0.6} />
    </AbsoluteFill>
  );
};

export const rgbaFondo = (a: number) => rgba(colores.fondo, a);
