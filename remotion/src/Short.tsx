// Vídeo vertical: Short (1080×1920) para YouTube Shorts, Instagram Reels y TikTok, y la misma composición en
// 4:5 (1080×1350) para LinkedIn. Todo se coloca con useLienzo(), así sirve para los dos tamaños.
// Guion: videos/<id>/shorts/<nombre>/short.json, generado por pipeline/09_shorts.py.
// Todo lo importante va dentro de la ZONA SEGURA: las apps tapan arriba (cabecera), abajo (descripción,
// música) y la derecha (botones).
import React, { useMemo } from "react";
import { AbsoluteFill, Audio, CalculateMetadataFunction, Img, OffthreadVideo, Sequence, staticFile, useCurrentFrame } from "remotion";
import { colores, fuentes, logos as logosMarca } from "./marca";
import type { Escena, LogosIndex } from "./types";
import { PANTALLA_COMPLETA } from "./types";
import { EscenaCompleta } from "./escenas/despacho";
import { AutoLogo, Callout, Camara, desenfoqueEn, eventosLogos } from "./escenas/camara";
import { Grano } from "./fondo/Depth";
import { FondoContext } from "./fondo/Fondos";
import { Bloque, Efecto } from "./componentes/piezas";
import { f, prog, rgba, useEntradaSalida, useLienzo } from "./lib/util";

/** Zona segura: en 9:16 las apps tapan arriba, abajo (descripción, música) y la derecha (botones). */
const useSegura = () => {
  const L = useLienzo();
  return { ...L, izq: 70, der: L.movil ? 170 : 70, corte: Math.round(L.H * 0.52) };   // corte: dividido
};

interface PalabraShort { w: string; inicio: number; fin: number }
export interface GuionShort {
  layout: "camara" | "dividido";
  camara: string;
  pantalla?: string;
  voz: string;
  fotogramas: number;
  posicion?: [number, number];   // encuadre vertical de la cámara (fracción x, y)
  foco?: [number, number];       // punto del punch-in
  punchIn?: number;
  cortes: number[];              // s en el short (saltos de corte → punch-in alterno)
  palabras: PalabraShort[];
  escenas: Escena[];
  fondo?: "profundidad" | "puntos" | "aurora";
  gancho?: { lineas: string[]; hasta: number; posicion?: "arriba" | "abajo" };
  cierre?: { texto: string; desde: number };
  autoLogos?: boolean;
  subtitulos?: boolean;
}
export type PropsShort = { guion: string; datos?: { guion: GuionShort; logos: LogosIndex } };

export const calcularShort: CalculateMetadataFunction<PropsShort> = async ({ props }) => {
  const leer = async (r: string) => (await fetch(staticFile(r))).json();
  const [guion, logos] = await Promise.all([leer(props.guion), leer("_shared/logos/index.json")]);
  return { durationInFrames: guion.fotogramas, props: { ...props, datos: { guion, logos } } };
};

/** Punch-in alterno en cada corte (como en la intro), con el mismo límite del 9 %. */
const escalasDe = (cortes: number[], punch: number) => {
  const p = Math.min(Math.max(punch, 0), 0.09);
  const res = [{ desde: 0, escala: 1 }];
  let ultimo = 0, arriba = false;
  for (const c of cortes) {
    const t = f(c);
    if (t - ultimo < f(1.2)) continue;
    arriba = !arriba;
    res.push({ desde: t, escala: arriba ? 1 + p : 1 });
    ultimo = t;
  }
  return res;
};

export const Short: React.FC<PropsShort> = ({ datos }) => {
  const frame = useCurrentFrame();
  const g = datos?.guion;
  const escalas = useMemo(() => (g ? escalasDe(g.cortes, g.punchIn ?? 0.09) : []), [g]);
  const eventos = useMemo(() => (g && datos && g.autoLogos !== false ? eventosLogos(g.palabras, datos.logos, g.escenas) : []),
                          [g, datos]);
  const S = useSegura();
  if (!g || !datos) return null;
  const desenfoque = desenfoqueEn(frame, g.escenas);
  const completas = g.escenas.filter((e) => PANTALLA_COMPLETA.includes(e.type));
  const t = frame / 30;
  const enGancho = g.gancho && t < g.gancho.hasta;
  const callouts = g.escenas.filter((e) => e.type === "callout") as Extract<Escena, { type: "callout" }>[];
  // Sin subtítulos bajo el gancho, las escenas ni el rótulo de cierre (se pisaban abajo).
  const tapado = enGancho || (g.cierre !== undefined && t >= g.cierre.desde - 0.1)
    || [...callouts, ...completas].some((e) => t >= e.from - 0.1 && t < e.to);

  const camara = (style?: React.CSSProperties) => (
    <Camara src={g.camara} fotogramasVideo={g.fotogramas} escalas={g.layout === "camara" ? escalas : [{ desde: 0, escala: 1 }]}
            foco={g.foco ?? [0.5, 0.4]} desenfoque={g.layout === "camara" ? desenfoque : 0} handheld={false}
            silenciada posicion={g.posicion ?? [0.5, 0.5]} style={style} />
  );

  return (
    <FondoContext.Provider value={g.fondo ?? "profundidad"}>
    <AbsoluteFill style={{ backgroundColor: colores.fondo }}>
      {g.layout === "camara" ? camara() : (
        <AbsoluteFill style={{ filter: desenfoque > 0.001 ? `blur(${desenfoque * 22}px) brightness(${1 - desenfoque * 0.4})` : undefined }}>
          <div style={{ position: "absolute", left: 0, top: 0, width: S.W, height: S.corte, overflow: "hidden" }}>
            <OffthreadVideo src={staticFile(g.pantalla!)} muted
                            style={{ width: "100%", height: "100%", objectFit: "cover",
                                     transform: `scale(${1 + 0.04 * frame / g.fotogramas})` }} />
          </div>
          {camara({ top: S.corte, height: S.H - S.corte })}
          <div style={{ position: "absolute", top: S.corte - 2, left: 0, width: S.W, height: 4,
                        background: `linear-gradient(90deg, ${colores.acento}, ${colores.acento2})`,
                        boxShadow: `0 0 24px ${rgba(colores.acento, 0.6)}` }} />
        </AbsoluteFill>
      )}

      {/* velo arriba y abajo: el texto de las apps y el nuestro se leen sobre cualquier fondo */}
      <AbsoluteFill style={{ background: `linear-gradient(180deg, ${rgba("#000000", 0.45)} 0%, transparent 18%, transparent 72%, ${rgba("#000000", 0.5)} 100%)` }} />

      {callouts.map((e, i) => (
        <Sequence key={`c${i}`} from={f(e.from)} durationInFrames={Math.max(1, f(e.to) - f(e.from))}>
          <AbsoluteFill style={{ padding: `${S.arriba}px ${S.der}px ${S.abajo}px ${S.izq}px` }}>
            <Callout escena={e} tam={96} />
          </AbsoluteFill>
        </Sequence>
      ))}

      {eventos.map((ev, i) => (
        <Sequence key={`l${i}`} from={f(ev.at) - 3} durationInFrames={f(2.4)}>
          <AbsoluteFill style={{ top: S.arriba - 120 }}>
            <AutoLogo ev={{ ...ev, lado: "izq" }} logos={datos.logos} />
          </AbsoluteFill>
        </Sequence>
      ))}

      {completas.map((e, i) => (
        <Sequence key={`p${i}`} from={f(e.from)} durationInFrames={Math.max(1, f(e.to) - f(e.from))}>
          <EscenaCompleta escena={e} logos={datos.logos} />
        </Sequence>
      ))}

      {g.subtitulos !== false && !tapado && (
        <Subtitulos palabras={g.palabras} y={g.layout === "dividido" ? S.corte : S.movil ? 1420 : S.H - S.abajo - 150} />
      )}

      {g.gancho && (
        <Sequence durationInFrames={f(g.gancho.hasta)}>
          <Gancho lineas={g.gancho.lineas} abajo={g.gancho.posicion === "abajo"} />
        </Sequence>
      )}
      {g.cierre && (
        <Sequence from={f(g.cierre.desde)}>
          <Cierre texto={g.cierre.texto} />
        </Sequence>
      )}

      <Grano opacidad={0.04} />
      <Audio src={staticFile(g.voz)} />
    </AbsoluteFill>
    </FondoContext.Provider>
  );
};

// ─────────────────────────── subtítulos palabra a palabra ───────────────────────────
const limpiar = (w: string) => w.trim().replace(/^[«"“(]+|[»"”),.;:…]+$/g, "");

/** Grupos de ≤ 3 palabras / ≤ 18 letras; se corta en pausas ≥ 0,3 s y en fin de frase. */
const agrupar = (ps: PalabraShort[]) => {
  const grupos: PalabraShort[][] = [];
  let g: PalabraShort[] = [];
  ps.forEach((p, i) => {
    g.push(p);
    const sig = ps[i + 1];
    const letras = g.map((x) => limpiar(x.w)).join(" ").length;
    const finFrase = /[.?!…]$/.test(p.w.trim()) || /,$/.test(p.w.trim());
    if (!sig || g.length >= 3 || letras >= 18 || finFrase || sig.inicio - p.fin >= 0.3) { grupos.push(g); g = []; }
  });
  return grupos;
};

const Subtitulos: React.FC<{ palabras: PalabraShort[]; y: number }> = ({ palabras, y }) => {
  const frame = useCurrentFrame();
  const t = frame / 30;
  const grupos = useMemo(() => agrupar(palabras), [palabras]);
  const S = useSegura();
  const gi = grupos.findIndex((g, i) => t >= g[0].inicio - 0.05 && (i + 1 >= grupos.length
    ? t <= g[g.length - 1].fin + 0.4 : t < grupos[i + 1][0].inicio - 0.05));
  if (gi < 0) return null;
  const g = grupos[gi];
  const ent = prog(frame, f(g[0].inicio - 0.05), f(g[0].inicio - 0.05) + 5);
  return (
    <div style={{ position: "absolute", left: S.izq, right: S.der, top: y, transform: `translateY(-50%) scale(${0.9 + 0.1 * ent})`,
                  display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "0 30px", opacity: ent }}>
      {g.map((p, i) => {
        const activa = t >= p.inicio - 0.03 && (i + 1 < g.length ? t < g[i + 1].inicio - 0.03 : true);
        return (
          <span key={i} style={{
            fontFamily: fuentes.texto, fontWeight: 800, fontSize: 86, lineHeight: 1.1, letterSpacing: "-0.01em",
            color: activa ? colores.acento : colores.texto, transform: `scale(${activa ? 1.08 : 1})`, display: "inline-block",
            WebkitTextStroke: "12px #000", paintOrder: "stroke fill",
            textShadow: `0 6px 18px rgba(0,0,0,.65)${activa ? `, 0 0 30px ${rgba(colores.acento, 0.5)}` : ""}`,
          }}>{limpiar(p.w)}</span>
        );
      })}
    </div>
  );
};

// ─────────────────────────── gancho (primeros segundos) ───────────────────────────
const Gancho: React.FC<{ lineas: string[]; abajo?: boolean }> = ({ lineas, abajo }) => {
  const { frame, sal } = useEntradaSalida(8, 10);
  const S = useSegura();
  return (
    <AbsoluteFill style={{ alignItems: "center", paddingTop: abajo ? Math.round(S.H * 0.56) : S.arriba + 40, paddingLeft: S.izq, paddingRight: S.der }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14,
                    opacity: 1 - sal, transform: `translateY(${sal * -30}px)` }}>
        {lineas.map((l, i) => {
          const ent = prog(frame, i * 5, i * 5 + 10);
          return i === 0 ? (
            <Bloque key={i} variante="acento" style={{ fontFamily: fuentes.texto, fontWeight: 800, fontSize: 104, lineHeight: 1,
                                                       letterSpacing: "-0.02em", opacity: ent,
                                                       transform: `scale(${0.8 + 0.2 * ent})` }}>{l}</Bloque>
          ) : (
            <div key={i} style={{ fontFamily: fuentes.texto, fontWeight: 800, fontSize: 70, color: colores.texto, textAlign: "center",
                                  WebkitTextStroke: "10px #000", paintOrder: "stroke fill", opacity: ent,
                                  transform: `translateY(${(1 - ent) * 20}px)` }}>{l}</div>
          );
        })}
      </div>
      <Efecto nombre="whoosh" volumen={0.3} />
    </AbsoluteFill>
  );
};

// ─────────────────────────── cierre ───────────────────────────
const Cierre: React.FC<{ texto: string }> = ({ texto }) => {
  const frame = useCurrentFrame();
  const ent = prog(frame, 0, 12);
  const S = useSegura();
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: S.abajo + 40 }}>
      <div style={{ opacity: ent, transform: `translateY(${(1 - ent) * 30}px)` }}>
        <Bloque radio={24} style={{ display: "flex", alignItems: "center", gap: 20, padding: "18px 30px",
                                     background: `linear-gradient(160deg, ${rgba(colores.superficie, 0.94)}, ${rgba(colores.fondo, 0.9)})` }}>
          {logosMarca.isotipo && <Img src={logosMarca.isotipo} style={{ height: 56 }} />}
          <span style={{ fontFamily: fuentes.texto, fontWeight: 700, fontSize: 44, color: colores.texto }}>{texto}</span>
        </Bloque>
      </div>
    </AbsoluteFill>
  );
};
