// Réplicas fieles de YouTube (tema oscuro): `index` (reproductor con capítulos) y `subscribe`.
import React from "react";
import { AbsoluteFill, Img, interpolate } from "remotion";
import { loadFont } from "@remotion/google-fonts/Roboto";
import { canal, formatoSuscriptores, logos as logosMarca } from "../marca";
import type { Escena } from "../types";
import { Efecto } from "../componentes/piezas";
import { easeInOut, f, prog, useEntradaSalida } from "../lib/util";

const { fontFamily: roboto } = loadFont("normal", { weights: ["400", "500", "700"], subsets: ["latin", "latin-ext"] });

const YT = {
  fondo: "#0F0F0F", sup: "#272727", sup2: "#3F3F3F", texto: "#F1F1F1", gris: "#AAAAAA",
  rojo: "#FF0033", azul: "#3EA6FF", menu: "#282828",
};

const mmss = (s: number) => {
  const t = Math.max(0, Math.floor(s));
  return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;
};

// ── Iconos (trazos al estilo de YouTube) ──
const Icono: React.FC<{ d: string; tam?: number; color?: string; relleno?: boolean }> = ({ d, tam = 24, color = YT.texto, relleno = true }) => (
  <svg width={tam} height={tam} viewBox="0 0 24 24">
    <path d={d} fill={relleno ? color : "none"} stroke={relleno ? "none" : color} strokeWidth={1.6} strokeLinejoin="round" />
  </svg>
);
const I = {
  campana: "M12 3a6 6 0 0 0-6 6v4.5L4.5 16v1h15v-1L18 13.5V9a6 6 0 0 0-6-6Zm0 19a2.5 2.5 0 0 0 2.4-2h-4.8A2.5 2.5 0 0 0 12 22Z",
  campanaSonando: "M12 3a6 6 0 0 0-6 6v4.5L4.5 16v1h15v-1L18 13.5V9a6 6 0 0 0-6-6Zm0 19a2.5 2.5 0 0 0 2.4-2h-4.8A2.5 2.5 0 0 0 12 22ZM3.3 8.4 1.8 7.6A10.9 10.9 0 0 1 5 3.2l1 1.2a9.4 9.4 0 0 0-2.7 4Zm17.4 0a9.4 9.4 0 0 0-2.7-4l1-1.2a10.9 10.9 0 0 1 3.2 4.4Z",
  campanaTachada: "M3.3 2.2 2.2 3.3 6.3 7.4A6 6 0 0 0 6 9v4.5L4.5 16v1h11.3l4.9 4.9 1.1-1.1ZM12 22a2.5 2.5 0 0 0 2.4-2h-4.8A2.5 2.5 0 0 0 12 22Zm6-8.5V9a6 6 0 0 0-9.7-4.7L18 14Z",
  persona: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm0 2c-4 0-8 2-8 5v1h16v-1c0-3-4-5-8-5Z",
  chevron: "M7 10l5 5 5-5z",
  play: "M8 5v14l11-7z",
  pausa: "M6 5h4v14H6zM14 5h4v14h-4z",
  sig: "M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z",
  volumen: "M3 9v6h4l5 5V4L7 9H3zm13.5 3A4.5 4.5 0 0 0 14 8v8a4.5 4.5 0 0 0 2.5-4z",
  ajustes: "M19.4 13a7.5 7.5 0 0 0 0-2l2.1-1.6-2-3.5-2.5 1a7.6 7.6 0 0 0-1.7-1L15 3h-4l-.4 2.9a7.6 7.6 0 0 0-1.7 1l-2.5-1-2 3.5L6.6 11a7.5 7.5 0 0 0 0 2l-2.1 1.6 2 3.5 2.5-1a7.6 7.6 0 0 0 1.7 1L11 21h4l.4-2.9a7.6 7.6 0 0 0 1.7-1l2.5 1 2-3.5ZM13 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7Z",
  pantalla: "M4 14h2v4h4v2H4v-6zm0-4V4h6v2H6v4H4zm14 8h-4v2h6v-6h-2v4zM14 4v2h4v4h2V4h-6z",
  like: "M2 21h4V9H2v12Zm20-11a2 2 0 0 0-2-2h-6.3l1-4.6v-.3a1.5 1.5 0 0 0-.5-1L13.2 1 6.6 7.6A2 2 0 0 0 6 9v10a2 2 0 0 0 2 2h9a2 2 0 0 0 1.8-1.2l3-7.1a2 2 0 0 0 .2-.7Z",
  buscar: "M15.5 14h-.8l-.3-.3A6.5 6.5 0 1 0 14 15.5l.3.3v.8l5 5 1.5-1.5-5-5Zm-6 0a4.5 4.5 0 1 1 0-9 4.5 4.5 0 0 1 0 9Z",
  menu: "M3 6h18v2H3zm0 5h18v2H3zm0 5h18v2H3z",
};

export const LogoYouTube: React.FC<{ alto?: number }> = ({ alto = 40 }) => (
  <div style={{ display: "flex", alignItems: "center", gap: alto * 0.12, height: alto }}>
    <svg height={alto} viewBox="0 0 28 20">
      <rect x="0" y="0" width="28" height="20" rx="5.6" fill={YT.rojo} />
      <path d="M11.2 5.7v8.6l7.3-4.3z" fill="#fff" />
    </svg>
    <span style={{ fontFamily: roboto, fontWeight: 700, fontSize: alto * 0.8, color: "#fff", letterSpacing: "-0.06em" }}>YouTube</span>
  </div>
);

const Avatar: React.FC<{ tam: number }> = ({ tam }) =>
  logosMarca.avatar ? (
    <Img src={logosMarca.avatar} style={{ width: tam, height: tam, borderRadius: "50%", objectFit: "cover" }} />
  ) : (
    <div style={{ width: tam, height: tam, borderRadius: "50%", background: YT.sup2 }} />
  );

/** Cursor tipo flecha del sistema. */
const Cursor: React.FC<{ x: number; y: number; pulsado: number }> = ({ x, y, pulsado }) => (
  <svg width={46} height={46} viewBox="0 0 24 24" style={{ position: "absolute", left: x - 6, top: y - 3,
       transform: `scale(${1 - pulsado * 0.12})`, filter: "drop-shadow(0 4px 8px rgba(0,0,0,.5))" }}>
    <path d="M5 2.5v17.2l4.3-4.2 2.9 6.6 2.6-1.1-2.9-6.5h6.1z" fill="#fff" stroke="#000" strokeWidth={1.2} strokeLinejoin="round" />
  </svg>
);

/** Trayectoria del cursor: lista de [fotograma, x, y]; interpola con curva suave. */
const posCursor = (frame: number, ruta: [number, number, number][]) => {
  const xs = interpolate(frame, ruta.map((r) => r[0]), ruta.map((r) => r[1]), { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeInOut });
  const ys = interpolate(frame, ruta.map((r) => r[0]), ruta.map((r) => r[2]), { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeInOut });
  return [xs, ys] as const;
};
const pulso = (frame: number, t: number) => (frame >= t && frame < t + 6 ? Math.sin(((frame - t) / 6) * Math.PI) : 0);

// ─────────────────────────── subscribe ───────────────────────────
export const Subscribe: React.FC<{ escena: Extract<Escena, { type: "subscribe" }> }> = ({ escena: e }) => {
  const { frame, sal } = useEntradaSalida(10, 16);
  const tS = f(e.subscribeAt - e.from);
  const tB = e.bellAt !== undefined ? f(e.bellAt - e.from) : null;
  const tTodas = tB !== null ? tB + 22 : null;
  const tC = e.commentAt !== undefined ? f(e.commentAt - e.from) : null;
  const texto = e.commentText ?? "";
  const tEscribe = tC !== null ? tC + 12 : null;
  const tFinEscribe = tEscribe !== null ? tEscribe + Math.round(texto.length * 1.3) : null;
  const tPublica = tFinEscribe !== null ? tFinEscribe + 14 : null;

  // Logo grande → sube; ficha del canal entra.
  const logoSube = prog(frame, 16, 32, easeInOut);
  const ficha = prog(frame, 22, 38);
  const suscrito = frame >= tS + 2;
  const menuAbierto = tB !== null && tTodas !== null && frame >= tB + 2 && frame < tTodas + 4;
  const todas = tTodas !== null && frame >= tTodas + 2;
  const caja = tC !== null ? prog(frame, tC - 14, tC) : 0;
  const escritos = tEscribe !== null ? Math.max(0, Math.min(texto.length, Math.floor((frame - tEscribe) / 1.3))) : 0;
  const publicado = tPublica !== null && frame >= tPublica + 2;

  // Geometría (px)
  const cardY = 360, cardX = 380, cardW = 1160;
  const btn = { x: cardX + cardW - 330, y: cardY + 78, w: 270, h: 76 };
  const menu = { x: btn.x - 60, y: btn.y + btn.h + 12 };
  const itemTodas = { x: menu.x + 150, y: menu.y + 44 };
  const cajaY = cardY + 300;
  const botonComentar = { x: cardX + cardW - 130, y: cajaY + 120 };

  const ruta: [number, number, number][] = [[0, 1700, 1150], [Math.max(12, tS - 18), btn.x + 150, btn.y + 42], [tS, btn.x + 150, btn.y + 42]];
  if (tB !== null && tTodas !== null) ruta.push([tB - 14, btn.x + 60, btn.y + 42], [tB, btn.x + 60, btn.y + 42], [tTodas - 6, itemTodas.x, itemTodas.y], [tTodas, itemTodas.x, itemTodas.y]);
  if (tC !== null && tFinEscribe !== null && tPublica !== null)
    ruta.push([tC - 10, cardX + 400, cajaY + 40], [tC, cardX + 400, cajaY + 40], [tFinEscribe + 2, cardX + 420, cajaY + 60],
              [tPublica - 2, botonComentar.x, botonComentar.y], [tPublica, botonComentar.x, botonComentar.y]);
  const [cx, cy] = posCursor(frame, ruta.sort((a, b) => a[0] - b[0]));
  const clics = [tS, tB, tTodas, tC, tPublica].filter((t): t is number => t !== null);
  const pulsado = Math.max(...clics.map((t) => pulso(frame, t)));
  const cursorOp = prog(frame, 8, 20) * (1 - sal);

  return (
    <AbsoluteFill style={{ fontFamily: roboto, opacity: 1 - sal, transform: `translateY(${sal * 30}px)` }}>
      {/* logo de YouTube */}
      <div style={{ position: "absolute", left: "50%", top: interpolate(logoSube, [0, 1], [470, 190]),
                    transform: `translateX(-50%) scale(${interpolate(logoSube, [0, 1], [2.2, 1]) * (0.7 + 0.3 * prog(frame, 0, 10))})`,
                    opacity: prog(frame, 0, 8) }}>
        <LogoYouTube alto={56} />
      </div>
      {/* ficha del canal */}
      <div style={{ position: "absolute", left: cardX, top: cardY, width: cardW, opacity: ficha,
                    transform: `translateY(${(1 - ficha) * 40}px)` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 40, background: "rgba(15,15,15,0.92)", borderRadius: 28,
                      padding: "38px 44px", boxShadow: "0 40px 80px -30px rgba(0,0,0,.8)", border: "1px solid #2a2a2a" }}>
          <Avatar tam={160} />
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 54, fontWeight: 700, color: YT.texto, letterSpacing: "-0.01em" }}>{canal.nombre}</div>
            <div style={{ fontSize: 28, color: YT.gris, marginTop: 8 }}>
              {canal.handle} · {formatoSuscriptores(canal.suscriptores ?? 0)} suscriptores
            </div>
          </div>
          <div style={{ width: btn.w, height: btn.h }} />
        </div>
        {/* comentario */}
        {tC !== null && (
          <div style={{ marginTop: 26, opacity: caja, transform: `translateY(${(1 - caja) * 20}px)`, background: "rgba(15,15,15,0.92)",
                        borderRadius: 28, padding: "30px 44px", border: "1px solid #2a2a2a" }}>
            {!publicado ? (
              <div style={{ display: "flex", gap: 26, alignItems: "flex-start" }}>
                <Avatar tam={64} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 30, color: escritos ? YT.texto : YT.gris, paddingBottom: 12, minHeight: 42,
                                borderBottom: `2px solid ${frame >= (tC ?? 0) ? YT.texto : "#717171"}` }}>
                    {escritos ? texto.slice(0, escritos) : "Añade un comentario..."}
                    {frame >= (tC ?? 0) && Math.floor(frame / 8) % 2 === 0 && <span style={{ color: YT.texto }}>|</span>}
                  </div>
                  <div style={{ display: "flex", justifyContent: "flex-end", gap: 16, marginTop: 20, fontSize: 26, fontWeight: 500 }}>
                    <span style={{ padding: "14px 26px", color: YT.texto }}>Cancelar</span>
                    <span style={{ padding: "14px 30px", borderRadius: 40, background: escritos ? YT.azul : YT.sup,
                                   color: escritos ? "#0F0F0F" : "#717171",
                                   transform: `scale(${1 - (tPublica !== null ? pulso(frame, tPublica) * 0.06 : 0)})` }}>Comentar</span>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ display: "flex", gap: 26, alignItems: "flex-start", opacity: prog(frame, (tPublica ?? 0) + 2, (tPublica ?? 0) + 12) }}>
                <Avatar tam={64} />
                <div>
                  <div style={{ fontSize: 26, color: YT.texto, fontWeight: 500 }}>
                    {canal.handle} <span style={{ color: YT.gris, fontWeight: 400 }}>hace 1 segundo</span>
                  </div>
                  <div style={{ fontSize: 32, color: YT.texto, marginTop: 8 }}>{texto}</div>
                  <div style={{ display: "flex", gap: 30, marginTop: 14, alignItems: "center", color: YT.gris, fontSize: 24 }}>
                    <Icono d={I.like} tam={30} color={YT.gris} />
                    <span style={{ transform: "rotate(180deg)", display: "inline-flex" }}><Icono d={I.like} tam={30} color={YT.gris} /></span>
                    <span style={{ fontWeight: 500, color: YT.texto }}>Responder</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
      {/* botón Suscribirse / Suscrito */}
      <div style={{ position: "absolute", left: btn.x, top: btn.y, width: btn.w, height: btn.h, borderRadius: 40,
                    display: "flex", alignItems: "center", justifyContent: "center", gap: 12, fontSize: 30, fontWeight: 500,
                    background: suscrito ? YT.sup : YT.texto, color: suscrito ? YT.texto : "#0F0F0F", opacity: ficha,
                    transform: `scale(${1 - pulso(frame, tS) * 0.07})` }}>
        {suscrito ? (
          <>
            <span style={{ transform: todas && tTodas !== null ? `rotate(${Math.sin((frame - tTodas) * 0.9) * 18 * Math.max(0, 1 - (frame - tTodas) / 24)}deg)` : undefined, display: "inline-flex" }}>
              <Icono d={todas ? I.campanaSonando : I.campana} tam={34} />
            </span>
            Suscrito
            <Icono d={I.chevron} tam={30} />
          </>
        ) : "Suscribirse"}
      </div>
      {/* menú de la campana */}
      {menuAbierto && (
        <div style={{ position: "absolute", left: menu.x, top: menu.y, width: 380, background: YT.menu, borderRadius: 16,
                      padding: "12px 0", boxShadow: "0 16px 40px rgba(0,0,0,.6)", fontSize: 28, color: YT.texto,
                      opacity: prog(frame, (tB ?? 0) + 2, (tB ?? 0) + 7) }}>
          {[["Todas", I.campanaSonando], ["Personalizadas", I.campana], ["Ninguna", I.campanaTachada], ["Anular suscripción", I.persona]].map(([t, d], i) => (
            <div key={i} style={{ display: "flex", gap: 22, alignItems: "center", padding: "16px 28px",
                                  background: i === 0 && tTodas !== null && frame >= tTodas - 8 ? YT.sup2 : undefined }}>
              <Icono d={d} tam={32} />{t}
            </div>
          ))}
        </div>
      )}
      <div style={{ opacity: cursorOp }}><Cursor x={cx} y={cy} pulsado={pulsado} /></div>
      <Efecto nombre={e.sfx === undefined ? "whoosh" : e.sfx} volumen={0.3} />
      <Efecto nombre="click" desde={tS} volumen={0.8} />
      {tB !== null && <Efecto nombre="click" desde={tB} volumen={0.8} />}
      {tTodas !== null && <Efecto nombre="click" desde={tTodas} volumen={0.8} />}
      {tTodas !== null && <Efecto nombre="campana" desde={tTodas + 2} volumen={0.5} />}
      {tC !== null && <Efecto nombre="click" desde={tC} volumen={0.8} />}
      {tEscribe !== null && Array.from({ length: Math.ceil(texto.length / 3) }, (_, k) => (
        <Efecto key={k} nombre="tecla" desde={tEscribe + Math.round(k * 3 * 1.3)} volumen={0.5} />
      ))}
      {tPublica !== null && <Efecto nombre="click" desde={tPublica} volumen={0.8} />}
    </AbsoluteFill>
  );
};

// ─────────────────────────── index (reproductor) ───────────────────────────
export const Index: React.FC<{ escena: Extract<Escena, { type: "index" }>; camara: React.ReactNode }> = ({ escena: e, camara }) => {
  const { frame, sal, ent } = useEntradaSalida(12, 16);
  const cap = e.chapters;
  const saltos = cap.map((c, i) => ({ i, t: c.jumpAt !== undefined ? f(c.jumpAt - e.from) : null })).filter((s) => s.t !== null) as { i: number; t: number }[];
  // Tiempo de reproducción: avanza en tiempo real y salta (con 8 fotogramas de transición) al capítulo nombrado.
  let tiempo = (cap[0]?.start ?? 0) + frame / 30;
  let ultimoSalto: number | null = null;
  for (const s of saltos) {
    if (frame < s.t) break;
    const despues = cap[s.i].start + (frame - s.t) / 30;
    tiempo = interpolate(frame, [s.t, s.t + 8], [tiempo, despues], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeInOut });
    ultimoSalto = s.t;
  }
  let activo = 0;
  for (let i = 0; i < cap.length; i++) if (tiempo >= cap[i].start) activo = i;
  const P = { x: 72, y: 104, w: 1248, h: 702 };
  const barraY = P.y + P.h - 62;
  const frac = (s: number) => Math.min(1, s / e.total);
  const tooltip = ultimoSalto !== null ? prog(frame, ultimoSalto, ultimoSalto + 6) * (1 - prog(frame, ultimoSalto + 40, ultimoSalto + 50)) : 0;
  const escala = 0.96 + 0.04 * ent;

  return (
    <AbsoluteFill style={{ background: YT.fondo, fontFamily: roboto, opacity: ent * (1 - sal), transform: `scale(${escala})` }}>
      {/* barra superior */}
      <div style={{ position: "absolute", left: 32, top: 26, display: "flex", alignItems: "center", gap: 30 }}>
        <Icono d={I.menu} tam={34} /><LogoYouTube alto={30} />
      </div>
      <div style={{ position: "absolute", left: 640, top: 20, width: 640, height: 52, borderRadius: 30, border: "1px solid #303030",
                    background: "#121212", display: "flex", alignItems: "center", padding: "0 24px", color: "#888", fontSize: 22 }}>Buscar</div>
      <div style={{ position: "absolute", right: 40, top: 22 }}><Avatar tam={46} /></div>

      {/* reproductor */}
      <div style={{ position: "absolute", left: P.x, top: P.y, width: P.w, height: P.h, borderRadius: 18, overflow: "hidden", background: "#000" }}>
        {camara}
        <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 170, background: "linear-gradient(transparent, rgba(0,0,0,.75))" }} />
      </div>
      {/* barra de progreso con capítulos */}
      <div style={{ position: "absolute", left: P.x + 24, top: barraY, width: P.w - 48, height: 8 }}>
        {cap.map((c, i) => {
          const a = frac(c.start), b = frac(cap[i + 1]?.start ?? e.total);
          const lleno = Math.max(0, Math.min(1, (frac(tiempo) - a) / Math.max(b - a, 1e-6)));
          return (
            <div key={i} style={{ position: "absolute", left: `calc(${a * 100}% + ${i ? 3 : 0}px)`, width: `calc(${(b - a) * 100}% - 3px)`,
                                  top: i === activo ? -2 : 0, height: i === activo ? 12 : 8, background: "rgba(255,255,255,.3)", borderRadius: 2, overflow: "hidden" }}>
              <div style={{ width: `${lleno * 100}%`, height: "100%", background: YT.rojo }} />
            </div>
          );
        })}
        <div style={{ position: "absolute", left: `${frac(tiempo) * 100}%`, top: -8, width: 24, height: 24, borderRadius: "50%",
                      background: YT.rojo, transform: "translateX(-50%)" }} />
        <div style={{ position: "absolute", left: `${frac(tiempo) * 100}%`, bottom: 34, transform: `translateX(-50%) translateY(${(1 - tooltip) * 8}px)`,
                      opacity: tooltip, background: "rgba(28,28,28,.95)", color: "#fff", fontSize: 24, fontWeight: 500,
                      padding: "10px 18px", borderRadius: 8, whiteSpace: "nowrap" }}>
          {cap[activo]?.title} · {mmss(cap[activo]?.start ?? 0)}
        </div>
      </div>
      {/* controles */}
      <div style={{ position: "absolute", left: P.x + 26, top: barraY + 20, right: 1920 - P.x - P.w + 26, display: "flex",
                    alignItems: "center", gap: 26, color: "#fff", fontSize: 24 }}>
        <Icono d={I.pausa} tam={40} /><Icono d={I.sig} tam={36} /><Icono d={I.volumen} tam={36} />
        <span>{mmss(tiempo)} / {mmss(e.total)}</span>
        <span style={{ color: "#ddd" }}>· {cap[activo]?.title} ›</span>
        <span style={{ flex: 1 }} />
        <Icono d={I.ajustes} tam={34} /><Icono d={I.pantalla} tam={36} />
      </div>
      {/* título y canal */}
      <div style={{ position: "absolute", left: P.x, top: P.y + P.h + 22, width: P.w, fontSize: 36, fontWeight: 700, color: YT.texto, lineHeight: 1.25 }}>
        {e.title}
      </div>
      <div style={{ position: "absolute", left: P.x, top: P.y + P.h + 88, display: "flex", alignItems: "center", gap: 20 }}>
        <Avatar tam={62} />
        <div>
          <div style={{ fontSize: 26, fontWeight: 500, color: YT.texto }}>{canal.nombre}</div>
          <div style={{ fontSize: 20, color: YT.gris }}>{formatoSuscriptores(canal.suscriptores ?? 0)} suscriptores</div>
        </div>
        <div style={{ marginLeft: 20, background: YT.texto, color: "#0F0F0F", borderRadius: 30, padding: "12px 24px", fontSize: 22, fontWeight: 500 }}>Suscribirse</div>
      </div>
      {/* panel de capítulos */}
      <div style={{ position: "absolute", left: P.x + P.w + 36, top: P.y, width: 1920 - (P.x + P.w + 36) - 40, bottom: 60,
                    border: "1px solid #303030", borderRadius: 18, overflow: "hidden" }}>
        <div style={{ padding: "22px 26px", fontSize: 28, fontWeight: 700, color: YT.texto, borderBottom: "1px solid #303030" }}>Capítulos</div>
        {cap.map((c, i) => (
          <div key={i} style={{ display: "flex", gap: 18, padding: "16px 22px", alignItems: "center",
                                background: i === activo ? YT.sup : undefined, transition: "none" }}>
            <div style={{ width: 150, height: 84, borderRadius: 10, flexShrink: 0, overflow: "hidden", position: "relative",
                          background: `linear-gradient(135deg, #1f2a23, #0b120d)` }}>
              <div style={{ position: "absolute", right: 8, bottom: 6, fontSize: 18, background: "rgba(0,0,0,.8)", color: "#fff",
                            padding: "2px 6px", borderRadius: 4 }}>{mmss(c.start)}</div>
            </div>
            <div style={{ fontSize: 22, color: YT.texto, fontWeight: i === activo ? 700 : 500, lineHeight: 1.3 }}>
              {c.title}
              <div style={{ fontSize: 18, color: YT.azul, marginTop: 6 }}>{mmss(c.start)}</div>
            </div>
          </div>
        ))}
      </div>
      <Efecto nombre={e.sfx === undefined ? "whoosh" : e.sfx} volumen={0.3} />
      {saltos.map((s) => <Efecto key={s.i} nombre="click" desde={s.t} volumen={0.7} />)}
    </AbsoluteFill>
  );
};
