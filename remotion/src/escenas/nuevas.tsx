// Piezas a pantalla completa añadidas tras revisar la skill de animaciones de referencia (ideas reimplementadas):
// notificación, buscador, ruta de pasos y comentarios/chat. Responsivas (16:9, 9:16, 4:5) y sobre Depth.
import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { colores, fuentes, logos as logosMarca } from "../marca";
import type { LogosIndex } from "../types";
import { Efecto, buscarMarca } from "../componentes/piezas";
import { esClaro, f, prog, rgba, useEntradaSalida, useLienzo } from "../lib/util";
import { Completa, Titular } from "./completas";
import type { Escena } from "../types";

type P<T extends Escena["type"]> = { escena: Extract<Escena, { type: T }>; logos: LogosIndex };

const cristal = (a = 0.1): React.CSSProperties => ({
  background: `linear-gradient(160deg, ${rgba(colores.texto, a + 0.04)} 0%, ${rgba(colores.texto, a * 0.4)} 100%)`,
  border: `1px solid ${rgba(colores.texto, 0.16)}`,
  boxShadow: `0 30px 60px -28px rgba(0,0,0,0.75), inset 0 1px 0 ${rgba("#FFFFFF", 0.18)}`,
  backdropFilter: "blur(18px) saturate(140%)",
});

/** Icono cuadrado de una app/marca: su color y su logo; la marca propia, con el isotipo; si no, la inicial. */
const Icono: React.FC<{ slug?: string; logos: LogosIndex; tam: number; letra?: string }> = ({ slug, logos, tam, letra }) => {
  const m = buscarMarca(logos, slug);
  const propia = m?.propia;
  const fondo = propia ? colores.superficie : m?.logoColor ? colores.superficie2 : m?.color ?? colores.acento;
  const src = propia ? logosMarca.isotipo : m ? staticFile(m.archivo) : null;
  const claro = esClaro(fondo);
  return (
    <div style={{ width: tam, height: tam, borderRadius: tam * 0.26, background: fondo, flexShrink: 0,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  border: `1px solid ${rgba("#FFFFFF", 0.22)}`, boxShadow: `0 8px 20px -8px ${rgba(fondo, 0.7)}` }}>
      {src ? (
        <Img src={src} style={{ width: tam * (propia ? 0.78 : 0.56), height: tam * (propia ? 0.78 : 0.56), objectFit: "contain",
                                filter: !propia && claro && !m?.fondoPropio ? "invert(1)" : undefined }} />
      ) : (
        <span style={{ fontFamily: fuentes.texto, fontWeight: 800, fontSize: tam * 0.46, color: claro ? "#111" : "#FFF" }}>
          {(letra ?? slug ?? "?").slice(0, 1).toUpperCase()}
        </span>
      )}
    </div>
  );
};

/** Momento de entrada (en fotogramas de la escena) de cada elemento: `at` o escalonado. */
const entradas = (items: { at?: number }[], desde: number, inicial: number, paso: number) =>
  items.map((it, i) => (it.at !== undefined ? f(it.at - desde) : inicial + i * paso));

// ─────────────────────────── notificacion ───────────────────────────
/** Notificaciones del móvil que caen una sobre otra (la nueva arriba empuja a las anteriores). */
export const Notificacion: React.FC<P<"notificacion">> = ({ escena: e, logos }) => {
  const { frame, sal } = useEntradaSalida();
  const L = useLienzo();
  const z = L.movil ? 1.22 : 1;                                       // en 9:16 todo un poco más grande
  const ancho = L.vertical ? L.W - 120 : 980;
  const alto = (L.vertical ? 190 : 176) * z;
  const hueco = 22;
  const t = entradas(e.items, e.from, 6, 16);
  const arriba = e.title ? (L.vertical ? L.arriba + 260 : 300) : L.vertical ? L.arriba + 120 : 200;
  return (
    <Completa tint={e.tint} semilla={11}>
      {e.title && (
        <AbsoluteFill style={{ alignItems: "center", paddingTop: L.vertical ? L.arriba + 40 : 90 }}>
          <Titular texto={e.title} frame={frame} desde={0} inicioEscena={e.from} tam={L.vertical ? 76 : 84} sal={sal} />
        </AbsoluteFill>
      )}
      {e.items.map((it, i) => {
        const k = prog(frame, t[i], t[i] + 14);
        if (k <= 0) return null;
        // cuántas notificaciones posteriores ya han entrado: empujan esta hacia abajo
        const empuje = e.items.reduce((s, _, j) => s + (j > i ? prog(frame, t[j], t[j] + 14) : 0), 0);
        const y = arriba + empuje * (alto + hueco) - (1 - k) * 70;
        const lejos = Math.max(0, empuje - 2.6);                  // más de 3 en pantalla: la más vieja se va
        return (
          <div key={i} style={{ position: "absolute", left: L.cx - ancho / 2, top: y, width: ancho, height: alto,
                                borderRadius: 38 * z, padding: `${24 * z}px ${30 * z}px`, display: "flex", gap: 24 * z,
                                alignItems: "flex-start",
                                opacity: k * (1 - sal) * (1 - Math.min(1, lejos)), transform: `scale(${0.94 + 0.06 * k})`,
                                ...cristal(0.11) }}>
            <Icono slug={it.app} logos={logos} tam={76 * z} letra={it.nombre} />
            <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 6 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontFamily: fuentes.mono, fontSize: 22 * z,
                            letterSpacing: 2, textTransform: "uppercase", color: colores.textoSuave }}>
                <span>{it.nombre ?? buscarMarca(logos, it.app)?.nombre ?? it.app ?? ""}</span>
                <span>{it.hora ?? "ahora"}</span>
              </div>
              <div style={{ fontFamily: fuentes.texto, fontWeight: 700, fontSize: 36 * z, color: colores.texto,
                            whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{it.titulo}</div>
              {it.texto && (
                <div style={{ fontFamily: fuentes.texto, fontSize: 30 * z, color: colores.textoSuave, lineHeight: 1.25,
                              whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{it.texto}</div>
              )}
            </div>
            <Efecto nombre={e.sfx === undefined ? "notificacion" : e.sfx} desde={t[i]} volumen={0.45} />
          </div>
        );
      })}
    </Completa>
  );
};

// ─────────────────────────── buscador ───────────────────────────
const Lupa: React.FC<{ tam: number; color: string }> = ({ tam, color }) => (
  <svg width={tam} height={tam} viewBox="0 0 24 24" style={{ flexShrink: 0 }}>
    <circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke={color} strokeWidth="2.4" />
    <line x1="15.5" y1="15.5" x2="21" y2="21" stroke={color} strokeWidth="2.6" strokeLinecap="round" />
  </svg>
);

/** Barra de búsqueda que se escribe sola y despliega resultados; el que importa, en acento. */
export const Buscador: React.FC<P<"buscador">> = ({ escena: e, logos }) => {
  const { frame, sal } = useEntradaSalida();
  const L = useLienzo();
  const z = L.movil ? 1.22 : 1;
  const ancho = (L.vertical ? L.W - 120 : 1240) / z;
  const t0 = e.typeAt !== undefined ? f(e.typeAt - e.from) : 10;
  const cps = e.speed ?? 16;                                         // letras por segundo
  const fin = t0 + Math.ceil((e.query.length / cps) * 30);
  const n = Math.max(0, Math.min(e.query.length, Math.floor(((frame - t0) / 30) * cps)));
  const cursor = frame < fin + 8 || Math.floor(frame / 15) % 2 === 0;
  const res = e.results ?? [];
  const tr = entradas(res, e.from, fin + 10, 6);
  const tamTxt = L.vertical ? 44 : 50;
  return (
    <Completa tint={e.tint} semilla={12}>
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", gap: 40,
                             padding: `${L.arriba}px 0 ${L.abajo}px`, opacity: 1 - sal, transform: `translateY(${sal * 24}px)` }}>
        {e.title && <Titular texto={e.title} frame={frame} desde={0} inicioEscena={e.from} tam={L.vertical ? 76 : 88} />}
        <div style={{ width: ancho, display: "flex", flexDirection: "column", gap: 0, zoom: z,
                      opacity: prog(frame, 0, 10), transform: `translateY(${(1 - prog(frame, 0, 14)) * 30}px)` }}>
          <div style={{ minHeight: 124, borderRadius: res.length && frame >= tr[0] ? "44px 44px 0 0" : 62,
                        display: "flex", alignItems: "center", gap: 26, padding: "24px 40px", ...cristal(0.12) }}>
            {e.logo ? <Icono slug={e.logo} logos={logos} tam={64} /> : <Lupa tam={48} color={colores.textoSuave} />}
              <div style={{ fontFamily: fuentes.texto, fontWeight: 500, fontSize: tamTxt, color: colores.texto,
                          lineHeight: 1.2, minWidth: 0 }}>
              {e.query.slice(0, n)}
              <span style={{ display: "inline-block", width: 4, height: tamTxt * 1.05, marginLeft: 4, verticalAlign: "middle",
                             background: colores.acento, opacity: cursor ? 1 : 0 }} />
            </div>
          </div>
          {res.length > 0 && (       // siempre en el layout (invisible hasta que entra): la barra no salta
            <div style={{ borderRadius: "0 0 44px 44px", padding: "14px 0 22px", ...cristal(0.07), borderTop: "none",
                          opacity: prog(frame, tr[0] - 4, tr[0] + 4) }}>
              {res.map((r, i) => {
                const k = prog(frame, tr[i], tr[i] + 10);
                return (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 26, padding: "16px 40px", margin: "0 14px",
                                        borderRadius: 24, opacity: k, transform: `translateY(${(1 - k) * 14}px)`,
                                        background: r.accent ? rgba(colores.acento, 0.16 * k) : undefined,
                                        border: r.accent ? `1px solid ${rgba(colores.acento, 0.5 * k)}` : "1px solid transparent" }}>
                    <Lupa tam={34} color={r.accent ? colores.acento : colores.textoSuave} />
                    <span style={{ fontFamily: fuentes.texto, fontSize: tamTxt * 0.78, fontWeight: r.accent ? 700 : 400,
                                   color: r.accent ? colores.texto : colores.textoSuave }}>{r.text}</span>
                    <Efecto nombre="tick_suave" desde={tr[i]} volumen={0.35} />
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </AbsoluteFill>
      <Efecto nombre={e.sfx === undefined ? "tecleo" : e.sfx} desde={t0} volumen={0.5} />
      {res.length > 0 && <Efecto nombre="bip" desde={fin + 6} volumen={0.4} />}
    </Completa>
  );
};

// ─────────────────────────── pasos ───────────────────────────
/** Ruta de pasos: nodos numerados unidos por una línea que se dibuja; el paso actual brilla en acento. */
export const Pasos: React.FC<P<"pasos">> = ({ escena: e, logos }) => {
  const { frame, sal } = useEntradaSalida();
  const L = useLienzo();
  const n = e.items.length;
  const t = entradas(e.items, e.from, 8, 20);
  const activo = t.reduce((a, ti, i) => (frame >= ti ? i : a), -1);
  const nodo = L.vertical ? 104 : 112;
  // posiciones de los nodos: en fila (16:9) o en columna (vertical)
  const zonaTop = (e.title ? (L.vertical ? L.arriba + 230 : 360) : L.vertical ? L.arriba + 80 : 300);
  const pos = e.items.map((_, i) => L.vertical
    ? { x: L.W * 0.17, y: zonaTop + (i + 0.5) * ((L.H - L.abajo - zonaTop) / n) }
    : { x: L.cx + (i - (n - 1) / 2) * Math.min(400, 1640 / Math.max(n - 1, 1)), y: e.title ? L.cy + 10 : L.cy - 60 });
  const anchoTxt = L.vertical ? L.W * 0.62 : Math.min(360, 1640 / Math.max(n - 1, 1) - 30);
  return (
    <Completa tint={e.tint} semilla={13}>
      {e.title && (
        <AbsoluteFill style={{ alignItems: "center", paddingTop: L.vertical ? L.arriba + 40 : 120 }}>
          <Titular texto={e.title} frame={frame} desde={0} inicioEscena={e.from} tam={L.vertical ? 76 : 92} sal={sal} />
        </AbsoluteFill>
      )}
      <svg width={L.W} height={L.H} style={{ position: "absolute", inset: 0, opacity: 1 - sal }}>
        {pos.slice(0, -1).map((p, i) => {
          const q = pos[i + 1];
          const k = prog(frame, t[i + 1] - 12, t[i + 1]);
          return (
            <g key={i}>
              <line x1={p.x} y1={p.y} x2={q.x} y2={q.y} stroke={rgba(colores.texto, 0.14)} strokeWidth={6} strokeLinecap="round" />
              <line x1={p.x} y1={p.y} x2={p.x + (q.x - p.x) * k} y2={p.y + (q.y - p.y) * k}
                    stroke={colores.acento} strokeWidth={6} strokeLinecap="round"
                    style={{ filter: `drop-shadow(0 0 8px ${rgba(colores.acento, 0.7)})` }} />
            </g>
          );
        })}
      </svg>
      {e.items.map((it, i) => {
        const k = prog(frame, t[i], t[i] + 12);
        const esActivo = i === activo;
        const hecho = i < activo;
        const p = pos[i];
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: p.x - nodo / 2, top: p.y - nodo / 2, width: nodo, height: nodo,
                          borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
                          opacity: (0.35 + 0.65 * k) * (1 - sal), transform: `scale(${0.8 + 0.2 * k + (esActivo ? 0.08 : 0)})`,
                          background: esActivo ? `linear-gradient(160deg, ${colores.acento}, ${colores.acento2})`
                            : `linear-gradient(${rgba(hecho ? colores.acento : colores.texto, hecho ? 0.22 : 0.08)}, ${rgba(hecho ? colores.acento : colores.texto, hecho ? 0.22 : 0.08)}), ${colores.superficie}`,
                          border: `2px solid ${esActivo || hecho ? colores.acento : rgba(colores.texto, 0.2)}`,
                          boxShadow: esActivo ? `0 0 40px ${rgba(colores.acento, 0.6)}` : undefined,
                          fontFamily: fuentes.titulares, fontStyle: "italic", fontSize: nodo * 0.5,
                          color: esActivo ? colores.fondo : colores.texto }}>
              {it.logo ? <Icono slug={it.logo} logos={logos} tam={nodo * 0.62} /> : i + 1}
            </div>
            <div style={{ position: "absolute", width: anchoTxt, opacity: k * (1 - sal),
                          transform: `translateY(${(1 - k) * 18}px)`,
                          ...(L.vertical
                            ? { left: p.x + nodo / 2 + 34, top: p.y - nodo / 2 + 4, textAlign: "left" as const }
                            : { left: p.x - anchoTxt / 2, top: p.y + nodo / 2 + 30, textAlign: "center" as const }) }}>
              <div style={{ fontFamily: fuentes.texto, fontWeight: 700, fontSize: L.vertical ? 44 : 40, lineHeight: 1.15,
                            color: esActivo ? colores.texto : rgba(colores.texto, hecho ? 0.75 : 0.55) }}>{it.title}</div>
              {it.text && (
                <div style={{ fontFamily: fuentes.texto, fontSize: L.vertical ? 32 : 29, lineHeight: 1.3, marginTop: 8,
                              color: colores.textoSuave }}>{it.text}</div>
              )}
            </div>
            <Efecto nombre={i === n - 1 ? "brillo" : "tick_suave"} desde={t[i]} volumen={i === n - 1 ? 0.35 : 0.45} />
          </React.Fragment>
        );
      })}
      <Efecto nombre={e.sfx === undefined ? "whoosh" : e.sfx} volumen={0.35} />
    </Completa>
  );
};

// ─────────────────────────── comentario ───────────────────────────
const colorAvatar = (nombre: string) => {
  const paleta = [colores.acento, colores.acento2, colores.superficie2, colores.borde ?? colores.superficie2];
  let h = 0;
  for (const c of nombre) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return paleta[h % paleta.length];
};

const Avatar: React.FC<{ nombre: string; tam: number }> = ({ nombre, tam }) => {
  const c = colorAvatar(nombre);
  return (
    <div style={{ width: tam, height: tam, borderRadius: "50%", background: c, flexShrink: 0, display: "flex",
                  alignItems: "center", justifyContent: "center", fontFamily: fuentes.texto, fontWeight: 800,
                  fontSize: tam * 0.44, color: esClaro(c) ? "#111" : "#FFF" }}>{nombre.slice(0, 1).toUpperCase()}</div>
  );
};

const Pulgar: React.FC<{ tam: number; color: string }> = ({ tam, color }) => (
  <svg width={tam} height={tam} viewBox="0 0 24 24">
    <path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3m7-2V5a3 3 0 0 0-3-3l-4 9v11h11.3a2 2 0 0 0 2-1.7l1.4-9A2 2 0 0 0 19.7 9H14z"
          fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
  </svg>
);

/**
 * Comentarios o chat. estilo "chat": burbujas (las propias, `yo`, a la derecha en acento) con «escribiendo…» antes de
 * cada mensaje ajeno. estilo "comentarios": lista tipo YouTube con avatar, nombre y «me gusta» que suben.
 */
export const Comentario: React.FC<P<"comentario">> = ({ escena: e, logos }) => {
  const { frame, sal } = useEntradaSalida();
  const L = useLienzo();
  const chat = (e.estilo ?? "chat") === "chat";
  const z = L.movil ? 1.22 : 1;
  const ancho = (L.vertical ? L.W - 120 : 1180) / z;
  const t = entradas(e.items, e.from, chat ? 22 : 8, chat ? 26 : 14);
  const tam = L.vertical ? 38 : 36;
  return (
    <Completa tint={e.tint} semilla={14}>
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", gap: 36,
                             padding: `${L.arriba}px 0 ${L.abajo}px`, opacity: 1 - sal, transform: `translateY(${sal * 24}px)` }}>
        {(e.title || e.app) && (
          <div style={{ display: "flex", alignItems: "center", gap: 22, opacity: prog(frame, 0, 12), zoom: z }}>
            {e.app && <Icono slug={e.app} logos={logos} tam={66} />}
            {e.title && <span style={{ fontFamily: fuentes.titulares, fontStyle: "italic", fontSize: L.vertical ? 66 : 72,
                                       color: colores.texto }}>{e.title}</span>}
          </div>
        )}
        <div style={{ width: ancho, display: "flex", flexDirection: "column", gap: chat ? 20 : 30, zoom: z }}>
          {e.items.map((it, i) => {
            const k = prog(frame, t[i], t[i] + 12);
            const escribiendo = chat && !it.yo && frame >= t[i] - 20 && frame < t[i];
            if (chat) {
              const fondo = it.yo ? colores.acento : undefined;
              return (
                <div key={i} style={{ display: "flex", justifyContent: it.yo ? "flex-end" : "flex-start", minHeight: tam * 1.9 }}>
                  {escribiendo && (
                    <div style={{ borderRadius: 32, padding: "22px 30px", display: "flex", gap: 10, ...cristal(0.1) }}>
                      {[0, 1, 2].map((d) => (
                        <span key={d} style={{ width: 14, height: 14, borderRadius: 7, background: colores.textoSuave,
                                               opacity: 0.35 + 0.65 * Math.max(0, Math.sin((frame - d * 4) / 4)) }} />
                      ))}
                    </div>
                  )}
                  {k > 0 && (
                    <div style={{ maxWidth: ancho * 0.78, borderRadius: it.yo ? "34px 34px 8px 34px" : "34px 34px 34px 8px",
                                  padding: "20px 30px", opacity: k, transform: `translateY(${(1 - k) * 20}px) scale(${0.96 + 0.04 * k})`,
                                  transformOrigin: it.yo ? "right bottom" : "left bottom",
                                  ...(it.yo ? { background: `linear-gradient(160deg, ${colores.acento}, ${colores.acento2})`,
                                                boxShadow: `0 20px 40px -20px ${rgba(colores.acento, 0.7)}` } : cristal(0.12)),
                                  fontFamily: fuentes.texto, fontSize: tam, lineHeight: 1.3,
                                  color: fondo && esClaro(fondo) ? colores.fondo : colores.texto }}>
                      {!it.yo && e.items.some((x) => x.autor !== it.autor && !x.yo) && (
                        <div style={{ fontSize: tam * 0.62, fontWeight: 700, color: colorAvatar(it.autor), marginBottom: 4 }}>{it.autor}</div>
                      )}
                      {it.texto}
                    </div>
                  )}
                  <Efecto nombre={it.yo ? "bip" : "ping"} desde={t[i]} volumen={it.yo ? 0.35 : 0.3} pan={it.yo ? 0.5 : -0.5} />
                </div>
              );
            }
            const likes = Math.round((it.likes ?? 0) * prog(frame, t[i] + 8, t[i] + 40));
            return (
              <div key={i} style={{ display: "flex", gap: 26, opacity: k, transform: `translateY(${(1 - k) * 22}px)`,
                                    padding: "26px 30px", borderRadius: 30, ...cristal(0.09) }}>
                <Avatar nombre={it.autor} tam={L.vertical ? 76 : 72} />
                <div style={{ display: "flex", flexDirection: "column", gap: 8, minWidth: 0 }}>
                  <span style={{ fontFamily: fuentes.texto, fontWeight: 700, fontSize: tam * 0.74, color: colores.textoSuave }}>
                    {it.autor.startsWith("@") ? it.autor : `@${it.autor}`}
                  </span>
                  <span style={{ fontFamily: fuentes.texto, fontSize: tam, lineHeight: 1.3, color: colores.texto }}>{it.texto}</span>
                  {it.likes !== undefined && (
                    <span style={{ display: "flex", alignItems: "center", gap: 10, fontFamily: fuentes.texto, fontSize: tam * 0.7,
                                   color: colores.textoSuave }}>
                      <Pulgar tam={tam * 0.8} color={colores.textoSuave} /> {likes.toLocaleString("es")}
                    </span>
                  )}
                </div>
                <Efecto nombre="tick_suave" desde={t[i]} volumen={0.4} />
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
      {e.sfx !== undefined && <Efecto nombre={e.sfx} volumen={0.35} />}
    </Completa>
  );
};
