// Escenas del anuncio de producto. Cada escena recibe su bloque del JSON (`e`) con tiempos ABSOLUTOS del anuncio
// (segundos de la locución) y los convierte a fotogramas locales con useT(e.from).
import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { colores, fuentes, logos as logosMarca } from "../marca";
import type { LogosIndex } from "../types";
import { Efecto, buscarMarca } from "../componentes/piezas";
import { easeInOut, easeOut, prog, rgba } from "../lib/util";
import { Boton, Chip, Cursor, Estallido, Flotantes, Mundo, P, Panel3D, Rotulo, Titular, panelY, resorte, useInclinacion, useLienzoPromo, useT } from "./sistema";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type E = any;
type Props = { e: E; logos: LogosIndex; dur: number };
const OBJ = (n: string) => `_shared/obj/${n}.png`;

/** Salida común: los últimos 8 fotogramas de cada escena (por debajo del barrido). */
const useSalida = (dur: number, n = 8) => {
  const frame = useCurrentFrame();
  return prog(frame, dur - n, dur, easeInOut);
};

const IconoCanal: React.FC<{ canal: string; logos: LogosIndex; tam: number }> = ({ canal, logos, tam }) => {
  const m = buscarMarca(logos, canal);
  if (!m) {
    return (
      <svg width={tam} height={tam} viewBox="0 0 24 24"><circle cx="12" cy="12" r="9.5" fill="none" stroke={P.suave} strokeWidth="1.8" />
        <path d="M2.5 12h19M12 2.5c3 3 3 16 0 19M12 2.5c-3 3-3 16 0 19" fill="none" stroke={P.suave} strokeWidth="1.6" /></svg>
    );
  }
  return <Img src={staticFile(m.archivo)} style={{ width: tam, height: tam, objectFit: "contain", borderRadius: tam * 0.22,
                                                   background: m.logoColor ? undefined : m.color, padding: m.logoColor ? 0 : tam * 0.16 }} />;
};

// ─────────────────────────── 1. apertura ───────────────────────────
export const Apertura: React.FC<Props> = ({ e, dur }) => {
  const frame = useCurrentFrame();
  const t = useT(e.from);
  const { W, H, u, fps } = useLienzoPromo();
  const sal = useSalida(dur);
  // mancha de entrada: una estrella orgánica que se infla y se encoge hasta desaparecer tras el titular
  const kb = resorte(frame, 0, fps, 9, 60);
  const r = W * 0.42 * kb * (1 - prog(frame, t(e.at.cambio) - 4, t(e.at.cambio) + 10, easeInOut) * 0.75);
  const pts = Array.from({ length: 72 }, (_, i) => {
    const a = (i / 72) * Math.PI * 2 + frame / 50;
    const rr = r * (1 + 0.28 * Math.sin(a * 4 + frame / 12));
    return `${(W / 2 + rr * Math.cos(a)).toFixed(1)},${(H * 0.47 + rr * Math.sin(a)).toFixed(1)}`;
  }).join(" ");
  const cambio = t(e.at.cambio);
  return (
    <AbsoluteFill>
      <Mundo semilla={1} />
      <svg width={W} height={H} style={{ position: "absolute" }}>
        <polygon points={pts} fill={rgba(colores.acento, 0.22)} />
        <circle cx={W / 2} cy={H * 0.47} r={W * 0.36 * prog(frame, 4, 30, easeOut)} fill="none" stroke={rgba(colores.acento, 0.5 * (1 - prog(frame, 20, 50)))} strokeWidth={3 * u} />
      </svg>
      <Flotantes items={[
        { src: OBJ("chat"), x: 0.2, y: 0.22, tam: 230, rot: -12, at: 2 },
        { src: OBJ("avion"), x: 0.82, y: 0.28, tam: 200, rot: 8, at: 6 },
        { src: OBJ("rayo"), x: 0.78, y: 0.7, tam: 210, rot: 10, at: cambio },
        { src: OBJ("pildora"), x: 0.2, y: 0.72, tam: 190, rot: -25, at: cambio + 4, prof: 0.6 },
      ]} sal={sal} desplaza={[0, -frame * 0.6]} />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingBottom: H * 0.06 }}>
        {frame < cambio ? (
          <Titular lineas={e.texto1} at={e.at.p1.map(t)} tam={150} sal={prog(frame, cambio - 6, cambio)} />
        ) : (
          <Titular lineas={e.texto2} at={e.at.p2.map(t)} tam={124} sal={sal} />
        )}
      </AbsoluteFill>
      <Efecto nombre="swell" volumen={0.35} />
      {e.at.p1.map((s: number, i: number) => <Efecto key={i} nombre="golpe_corto" desde={t(s)} volumen={0.35} />)}
      <Efecto nombre="golpe" desde={t(e.at.p2[e.at.p2.length - 1])} volumen={0.5} />
    </AbsoluteFill>
  );
};

// ─────────────────────────── 2. canales → un solo lugar ───────────────────────────
export const Canales: React.FC<Props> = ({ e, logos, dur }) => {
  const frame = useCurrentFrame();
  const t = useT(e.from);
  const { W, H, u, fps, movil } = useLienzoPromo();
  const sal = useSalida(dur);
  const kLogo = resorte(frame, t(e.at.marca), fps, 9, 150);
  const junta = prog(frame, t(e.at.junta) - 6, t(e.at.junta) + 10, easeInOut);
  const canales = e.canales as { canal: string; nombre: string; texto: string; at: number }[];
  const cy = H * (movil ? 0.56 : 0.58);
  return (
    <AbsoluteFill>
      <Mundo semilla={2} />
      <Rotulo texto={e.rotulo} at={t(e.at.rotulo)} sal={sal} />
      {/* marca grande que luego sube y se hace pequeña */}
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: 1 - sal }}>
        <div style={{ display: "flex", alignItems: "center", gap: 26 * u,
                      transform: `translateY(${interpolate(junta, [0, 1], [-H * 0.02, -cy + H * 0.36 + (movil ? 90 : 60) * u])}px) scale(${kLogo * (1 - 0.45 * junta)})` }}>
          {logosMarca.isotipo && <Img src={logosMarca.isotipo} style={{ height: 150 * u, filter: `drop-shadow(0 ${16 * u}px ${28 * u}px ${rgba(colores.acento, 0.5)})` }} />}
          <span style={{ fontFamily: fuentes.texto, fontWeight: 800, fontSize: 120 * u, letterSpacing: "-0.04em", color: P.tinta }}>{e.marca}</span>
        </div>
      </AbsoluteFill>
      {/* canales que entran volando y se juntan en una bandeja */}
      {canales.map((c, i) => {
        const k = resorte(frame, t(c.at), fps, 11, 150);
        const ang = [-1, 0, 1][i] ?? 0;
        const sueltoX = W / 2 + ang * W * 0.3, sueltoY = H * 0.68 + Math.abs(ang) * -H * 0.04;
        const filaY = cy - 120 * u + i * 150 * u;
        const x = interpolate(junta, [0, 1], [sueltoX, W / 2]);
        const y = interpolate(junta, [0, 1], [sueltoY, filaY]);
        const anchoFila = interpolate(junta, [0, 1], [200, 880]) * u;
        return (
          <div key={i} style={{ position: "absolute", left: x - anchoFila / 2, top: y - 62 * u, width: anchoFila, height: 124 * u,
                                borderRadius: 30 * u, display: "flex", alignItems: "center", gap: 24 * u, padding: `0 ${30 * u}px`,
                                background: junta > 0.02 ? `linear-gradient(160deg, ${P.panel2}, ${P.panel})` : "#FFFFFF",
                                boxShadow: `0 ${24 * u}px ${50 * u}px -${16 * u}px rgba(0,0,0,0.35)`,
                                transform: `scale(${k * (1 - sal)}) rotate(${(1 - junta) * ang * 10}deg)`, overflow: "hidden" }}>
            <IconoCanal canal={c.canal} logos={logos} tam={76 * u} />
            {junta > 0.4 && (
              <div style={{ opacity: prog(junta, 0.4, 1), display: "flex", flexDirection: "column", gap: 4 * u, minWidth: 0 }}>
                <span style={{ fontFamily: fuentes.texto, fontWeight: 800, fontSize: 34 * u, color: P.texto, whiteSpace: "nowrap" }}>{c.nombre}</span>
                <span style={{ fontFamily: fuentes.texto, fontSize: 28 * u, color: P.suave, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{c.texto}</span>
              </div>
            )}
            <Efecto nombre="bip" desde={t(c.at)} volumen={0.4} pan={ang * 0.6} />
          </div>
        );
      })}
      <Efecto nombre="golpe" desde={t(e.at.marca)} volumen={0.55} />
      <Efecto nombre="whoosh" desde={t(e.at.junta) - 6} volumen={0.4} />
    </AbsoluteFill>
  );
};

// ─────────────────────────── 3. medianoche (teléfono) ───────────────────────────
export const Medianoche: React.FC<Props> = ({ e, logos, dur }) => {
  const frame = useCurrentFrame();
  const t = useT(e.from);
  const { W, H, u, fps, movil } = useLienzoPromo();
  const sal = useSalida(dur);
  const k = resorte(frame, 0, fps, 13, 110);
  const tel = { w: 560 * u, h: 1140 * u };
  const escala = movil ? 1 : 0.78;
  const y = H * (movil ? 0.6 : 0.62);
  return (
    <AbsoluteFill>
      <Mundo oscuro semilla={3} />
      <Rotulo texto={e.rotulo} at={2} sal={sal} color={P.texto} />
      <div style={{ position: "absolute", left: W / 2 - tel.w / 2, top: y - tel.h / 2, width: tel.w, height: tel.h,
                    transform: `perspective(${1600 * u}px) rotateY(${interpolate(k, [0, 1], [-70, -12])}deg) rotateX(${interpolate(k, [0, 1], [20, 6])}deg) rotateZ(${interpolate(k, [0, 1], [-14, -4])}deg) scale(${escala * (0.8 + 0.2 * k) * (1 - sal * 0.3)})`,
                    opacity: Math.min(1, k * 1.5) * (1 - sal), borderRadius: 86 * u, background: "#0A0A0A", padding: 18 * u,
                    boxShadow: `0 ${60 * u}px ${120 * u}px -${20 * u}px rgba(0,0,0,0.7), 0 0 0 ${3 * u}px #2A2A2A` }}>
        <div style={{ width: "100%", height: "100%", borderRadius: 70 * u, overflow: "hidden", position: "relative",
                      background: `linear-gradient(180deg, #0B1B2E 0%, ${P.tinta} 70%)` }}>
          <div style={{ position: "absolute", left: "50%", top: 24 * u, width: 170 * u, height: 48 * u, marginLeft: -85 * u, borderRadius: 30 * u, background: "#000" }} />
          <div style={{ position: "absolute", top: 120 * u, width: "100%", textAlign: "center", color: "#FFF", fontFamily: fuentes.texto }}>
            <div style={{ fontSize: 30 * u, fontWeight: 600, opacity: 0.8 }}>{e.fecha}</div>
            <div style={{ fontSize: 170 * u, fontWeight: 700, letterSpacing: "-0.04em", lineHeight: 1 }}>{e.hora}</div>
          </div>
          {(e.notificaciones as { canal: string; titulo: string; texto: string; at: number }[]).map((n, i, arr) => {
            const kn = resorte(frame, t(n.at), fps, 12, 160);
            const despues = arr.filter((m, j) => j > i && frame >= t(m.at)).length;
            return (
              <div key={i} style={{ position: "absolute", left: 22 * u, right: 22 * u, top: 420 * u + despues * 150 * u,
                                    transform: `translateY(${(1 - kn) * -80 * u}px) scale(${0.9 + 0.1 * kn})`, opacity: kn,
                                    borderRadius: 34 * u, padding: `${20 * u}px ${24 * u}px`, display: "flex", gap: 18 * u,
                                    background: "rgba(255,255,255,0.14)", backdropFilter: "blur(20px)", border: `${1 * u}px solid rgba(255,255,255,0.12)` }}>
                <IconoCanal canal={n.canal} logos={logos} tam={64 * u} />
                <div style={{ minWidth: 0, fontFamily: fuentes.texto, color: "#FFF" }}>
                  <div style={{ fontSize: 26 * u, fontWeight: 800 }}>{n.titulo}</div>
                  <div style={{ fontSize: 25 * u, opacity: 0.85, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{n.texto}</div>
                </div>
                <Efecto nombre="notificacion" desde={t(n.at)} volumen={0.5} />
              </div>
            );
          })}
        </div>
      </div>
      <Flotantes items={[{ src: OBJ("chat"), x: movil ? 0.8 : 0.78, y: movil ? 0.38 : 0.4, tam: 200, rot: 14, at: t(e.notificaciones[0].at) }]} sal={sal} />
      <Efecto nombre="whoosh" volumen={0.4} />
    </AbsoluteFill>
  );
};

// ─────────────────────────── 4. chat con el vendedor IA ───────────────────────────
export const ChatIA: React.FC<Props> = ({ e, logos, dur }) => {
  const frame = useCurrentFrame();
  const t = useT(e.from);
  const { u, fps, movil } = useLienzoPromo();
  const sal = useSalida(dur);
  const inc = useInclinacion(dur, [18, 16, -4], [7, 5, -1]);
  const mensajes = e.mensajes as { de: "cliente" | "ia"; texto: string; at: number }[];
  const link = e.link as { titulo: string; monto: string; at: number };
  const kl = resorte(frame, t(link.at), fps, 11, 150);
  return (
    <AbsoluteFill>
      <Mundo semilla={4} />
      <Rotulo texto={e.rotulo} at={t(e.at.rotulo)} sal={sal} />
      <Panel3D ancho={920} alto={movil ? 900 : 760} y={panelY(movil)} rx={inc.rx} ry={inc.ry} rz={inc.rz} escala={inc.escala * (movil ? 1 : 0.86) * (1 - sal * 0.2)} opacidad={1 - sal}>
        <div style={{ display: "flex", alignItems: "center", gap: 20 * u, padding: `${28 * u}px ${32 * u}px`, borderBottom: `${1.5 * u}px solid ${rgba(P.texto, 0.08)}` }}>
          <div style={{ width: 72 * u, height: 72 * u, borderRadius: 22 * u, background: P.acento, display: "flex", alignItems: "center", justifyContent: "center",
                        fontFamily: fuentes.texto, fontWeight: 800, fontSize: 30 * u, color: P.tinta }}>{e.iniciales}</div>
          <div style={{ fontFamily: fuentes.texto }}>
            <div style={{ fontSize: 34 * u, fontWeight: 800, color: P.texto }}>{e.cliente}</div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 * u, fontSize: 24 * u, color: P.suave }}>
              <IconoCanal canal={e.canal} logos={logos} tam={28 * u} /> {e.canalNombre}
            </div>
          </div>
          <div style={{ marginLeft: "auto" }}><Chip texto="IA activa" color={P.acento} u={u} /></div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 20 * u, padding: `${30 * u}px ${32 * u}px` }}>
          {mensajes.map((m, i) => {
            const km = resorte(frame, t(m.at), fps, 13, 170);
            const ia = m.de === "ia";
            // la IA «escribe» su mensaje: aparece letra a letra en ~1,1 s
            const letras = ia ? Math.floor(m.texto.length * prog(frame, t(m.at), t(m.at) + 34)) : m.texto.length;
            const escribiendo = ia && frame >= t(m.at) - 14 && frame < t(m.at);
            return (
              <div key={i} style={{ alignSelf: ia ? "flex-end" : "flex-start", maxWidth: "84%" }}>
                {escribiendo && (
                  <div style={{ display: "flex", gap: 10 * u, padding: `${22 * u}px ${28 * u}px`, borderRadius: 30 * u, background: rgba(P.acento, 0.15) }}>
                    {[0, 1, 2].map((d) => <span key={d} style={{ width: 14 * u, height: 14 * u, borderRadius: 99, background: P.acento, opacity: 0.4 + 0.6 * Math.max(0, Math.sin((frame - d * 4) / 4)) }} />)}
                  </div>
                )}
                {frame >= t(m.at) && (
                  <div style={{ opacity: km, transform: `translateY(${(1 - km) * 30 * u}px) scale(${0.94 + 0.06 * km})`, transformOrigin: ia ? "right bottom" : "left bottom",
                                padding: `${20 * u}px ${26 * u}px`, borderRadius: ia ? `${30 * u}px ${30 * u}px ${8 * u}px ${30 * u}px` : `${30 * u}px ${30 * u}px ${30 * u}px ${8 * u}px`,
                                background: ia ? rgba(P.acento, 0.16) : rgba(P.texto, 0.07), border: `${1.5 * u}px solid ${ia ? rgba(P.acento, 0.5) : rgba(P.texto, 0.08)}` }}>
                    <div style={{ fontFamily: fuentes.mono, fontSize: 18 * u, letterSpacing: 2, color: ia ? P.acento : P.suave, marginBottom: 6 * u }}>
                      {ia ? "ASISTENTE · AHORA" : "CLIENTE · 11:58 P. M."}
                    </div>
                    <div style={{ fontFamily: fuentes.texto, fontSize: 30 * u, lineHeight: 1.35, color: P.texto }}>{m.texto.slice(0, letras)}</div>
                  </div>
                )}
                {ia ? <Efecto nombre="tecleo" desde={t(m.at)} volumen={0.35} pan={0.4} /> : <Efecto nombre="ping" desde={t(m.at)} volumen={0.3} pan={-0.4} />}
              </div>
            );
          })}
          {frame >= t(link.at) - 2 && (
            <div style={{ alignSelf: "flex-end", width: "74%", opacity: kl, transform: `translateY(${(1 - kl) * 50 * u}px) scale(${0.9 + 0.1 * kl}) rotate(${(1 - kl) * 4}deg)`,
                          borderRadius: 30 * u, overflow: "hidden", border: `${2 * u}px solid ${P.acento}`, background: P.panel,
                          boxShadow: `0 ${20 * u}px ${50 * u}px -${16 * u}px ${rgba(P.acento, 0.6)}` }}>
              <div style={{ padding: `${22 * u}px ${26 * u}px`, display: "flex", alignItems: "center", gap: 18 * u }}>
                <Img src={staticFile(OBJ("check"))} style={{ width: 70 * u, height: 70 * u }} />
                <div style={{ fontFamily: fuentes.texto }}>
                  <div style={{ fontSize: 22 * u, color: P.suave, fontWeight: 700, letterSpacing: 1 }}>LINK DE PAGO</div>
                  <div style={{ fontSize: 30 * u, color: P.texto, fontWeight: 800 }}>{link.titulo}</div>
                  <div style={{ fontSize: 36 * u, color: P.acento, fontWeight: 800 }}>{link.monto}</div>
                </div>
              </div>
              <div style={{ padding: `0 ${26 * u}px ${22 * u}px` }}><Boton texto="Pagar ahora" u={u} tam={28} style={{ width: "100%", justifyContent: "center" }} /></div>
              <Efecto nombre="golpe_corto" desde={t(link.at)} volumen={0.5} />
            </div>
          )}
        </div>
      </Panel3D>
      <Flotantes items={[{ src: OBJ("avion"), x: 0.84, y: movil ? 0.82 : 0.86, tam: 190, rot: -10, at: t(link.at) }]} sal={sal} />
    </AbsoluteFill>
  );
};

// ─────────────────────────── 5. leads con puntaje ───────────────────────────
const TEMP: Record<string, string> = { Caliente: colores.acento, Tibio: colores.etiqueta, Frío: "#5AA9F0" };
export const Leads: React.FC<Props> = ({ e, logos, dur }) => {
  const frame = useCurrentFrame();
  const t = useT(e.from);
  const { u, movil } = useLienzoPromo();
  const sal = useSalida(dur);
  const inc = useInclinacion(dur, [24, -20, 7], [10, -8, 3]);
  const filas = e.filas as { nombre: string; canal: string; etapa: string; puntaje: number; temp: string }[];
  // resaltado por temperatura sincronizado con la voz
  const foco = (temp: string) => {
    const at = e.at[temp];
    if (at === undefined) return 0;
    const sig = Object.values(e.at).filter((v) => typeof v === "number" && (v as number) > at) as number[];
    const fin = sig.length ? Math.min(...sig) : e.to;
    return Math.min(prog(frame, t(at) - 2, t(at) + 6), 1 - prog(frame, t(fin) - 2, t(fin) + 4));
  };
  return (
    <AbsoluteFill>
      <Mundo semilla={5} />
      <Rotulo texto={e.rotulo} at={t(e.at.rotulo)} sal={sal} />
      <Panel3D ancho={940} y={panelY(movil)} rx={inc.rx} ry={inc.ry} rz={inc.rz} escala={inc.escala * (movil ? 1 : 0.84) * (1 - sal * 0.2)} opacidad={1 - sal}>
        <div style={{ padding: `${26 * u}px ${30 * u}px ${12 * u}px`, display: "flex", alignItems: "baseline", gap: 16 * u, fontFamily: fuentes.texto }}>
          <span style={{ fontSize: 40 * u, fontWeight: 800, color: P.texto }}>Leads</span>
          <span style={{ fontSize: 24 * u, color: P.suave }}>{e.total}</span>
        </div>
        <div style={{ display: "flex", gap: 10 * u, padding: `${6 * u}px ${30 * u}px ${18 * u}px` }}>
          {["Caliente", "Tibio", "Frío"].map((c) => (
            <Chip key={c} texto={c} color={TEMP[c]} u={u} lleno={foco(c) > 0.5} style={{ transform: `scale(${1 + 0.12 * foco(c)})` }} />
          ))}
        </div>
        {filas.map((r, i) => {
          const k = prog(frame, 6 + i * 3, 18 + i * 3, easeOut);
          const f = foco(r.temp);
          const num = Math.round(r.puntaje * prog(frame, 8 + i * 3, 34 + i * 3, easeOut));
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 18 * u, padding: `${16 * u}px ${30 * u}px`,
                                  borderTop: `${1.5 * u}px solid ${rgba(P.texto, 0.06)}`, opacity: k * (1 - 0.55 * (anyFoco(e, frame, t) && f < 0.5 ? 1 : 0)),
                                  transform: `translateX(${(1 - k) * 80 * u}px) scale(${1 + 0.03 * f})`,
                                  background: f > 0 ? rgba(TEMP[r.temp], 0.12 * f) : undefined, fontFamily: fuentes.texto }}>
              <IconoCanal canal={r.canal} logos={logos} tam={46 * u} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 30 * u, fontWeight: 800, color: P.texto, whiteSpace: "nowrap" }}>{r.nombre}</div>
                <div style={{ fontSize: 22 * u, color: P.suave, whiteSpace: "nowrap" }}>{r.etapa}</div>
              </div>
              <span style={{ fontSize: 44 * u, fontWeight: 800, color: TEMP[r.temp], width: 90 * u, textAlign: "right" }}>{num}</span>
              <Chip texto={r.temp} color={TEMP[r.temp]} u={u} tam={22} lleno={f > 0.5} />
              <Efecto nombre="tick" desde={6 + i * 3} volumen={0.25} />
            </div>
          );
        })}
      </Panel3D>
      {["Caliente", "Tibio", "Frío"].map((c) => e.at[c] !== undefined && <Efecto key={c} nombre="bip" desde={t(e.at[c])} volumen={0.45} />)}
      <Flotantes items={[{ src: OBJ("rayo"), x: 0.86, y: movil ? 0.36 : 0.3, tam: 170, rot: 12, at: t(e.at.Caliente) }]} sal={sal} />
    </AbsoluteFill>
  );
};
const anyFoco = (e: E, frame: number, t: (s: number) => number) =>
  ["Caliente", "Tibio", "Frío"].some((c) => e.at[c] !== undefined && frame >= t(e.at[c]) - 2);

// ─────────────────────────── 6. traspaso a una persona ───────────────────────────
export const Handoff: React.FC<Props> = ({ e, logos, dur }) => {
  const frame = useCurrentFrame();
  const t = useT(e.from);
  const { u, fps, movil } = useLienzoPromo();
  const sal = useSalida(dur);
  const inc = useInclinacion(dur, [16, 22, -6], [6, 8, -2]);
  const pulso = 0.5 + 0.5 * Math.sin(frame / 4);
  const kc = resorte(frame, t(e.at.contexto), fps, 12, 150);
  return (
    <AbsoluteFill>
      <Mundo semilla={6} />
      <Rotulo texto={e.rotulo} at={t(e.at.rotulo)} sal={sal} />
      <Panel3D ancho={920} y={panelY(movil)} rx={inc.rx} ry={inc.ry} rz={inc.rz} escala={inc.escala * (movil ? 1 : 0.84) * (1 - sal * 0.2)} opacidad={1 - sal}>
        <div style={{ display: "flex", alignItems: "center", gap: 22 * u, padding: `${30 * u}px ${32 * u}px`, fontFamily: fuentes.texto }}>
          <div style={{ width: 96 * u, height: 96 * u, borderRadius: 28 * u, background: P.acento, display: "flex", alignItems: "center", justifyContent: "center",
                        fontWeight: 800, fontSize: 38 * u, color: P.tinta }}>{e.iniciales}</div>
          <div>
            <div style={{ fontSize: 40 * u, fontWeight: 800, color: P.texto }}>{e.cliente}</div>
            <div style={{ display: "flex", gap: 10 * u, marginTop: 8 * u, alignItems: "center" }}>
              <Chip texto={e.temp} color={colores.etiqueta} u={u} tam={22} />
              <Chip texto="Pide atención humana" color={P.alerta} u={u} tam={22} style={{ boxShadow: `0 0 ${24 * u * pulso}px ${rgba(P.alerta, 0.7 * pulso)}` }} />
            </div>
          </div>
        </div>
        <div style={{ margin: `0 ${32 * u}px ${30 * u}px`, borderRadius: 28 * u, padding: `${26 * u}px ${28 * u}px`, background: rgba(P.acento, 0.08),
                      border: `${1.5 * u}px solid ${rgba(P.acento, 0.35)}`, fontFamily: fuentes.texto }}>
          <div style={{ fontSize: 22 * u, fontWeight: 800, letterSpacing: 2, color: P.acento, marginBottom: 16 * u }}>RESUMEN PARA TU EQUIPO</div>
          {(e.contexto as { k: string; v: string }[]).map((c, i) => {
            const k = prog(frame, t(e.at.contexto) + i * 6, t(e.at.contexto) + i * 6 + 12, easeOut);
            return (
              <div key={i} style={{ display: "flex", gap: 16 * u, padding: `${12 * u}px 0`, opacity: k, transform: `translateY(${(1 - k) * 20 * u}px)`,
                                    borderTop: i ? `${1 * u}px solid ${rgba(P.texto, 0.07)}` : undefined }}>
                <span style={{ fontSize: 26 * u, color: P.suave, width: 190 * u, flexShrink: 0 }}>{c.k}</span>
                <span style={{ fontSize: 28 * u, color: P.texto, fontWeight: 600, lineHeight: 1.3 }}>{c.v}</span>
                <Efecto nombre="tick_suave" desde={t(e.at.contexto) + i * 6} volumen={0.4} />
              </div>
            );
          })}
        </div>
        <div style={{ padding: `0 ${32 * u}px ${32 * u}px`, display: "flex", gap: 16 * u, alignItems: "center",
                      opacity: kc, transform: `translateY(${(1 - kc) * 30 * u}px)` }}>
          <Boton texto="Atender ahora" u={u} tam={28} />
          <span style={{ fontFamily: fuentes.texto, fontSize: 24 * u, color: P.suave }}>{e.nota}</span>
        </div>
      </Panel3D>
      <Efecto nombre="notificacion" desde={t(e.at.persona)} volumen={0.45} />
    </AbsoluteFill>
  );
};

// ─────────────────────────── 7. confirmar pago (cursor) ───────────────────────────
export const Pago: React.FC<Props> = ({ e, dur }) => {
  const frame = useCurrentFrame();
  const t = useT(e.from);
  const { W, H, u, fps, movil } = useLienzoPromo();
  const sal = useSalida(dur);
  const inc = useInclinacion(dur, [12, -10, 2], [3, -2, 0]);
  const clic = t(e.at.toque);
  const hecho = prog(frame, clic, clic + 8);
  const kc = resorte(frame, t(e.at.comprobante), fps, 11, 150);
  const pY = panelY(movil);
  // posición del botón en pantalla (el panel apenas está inclinado al final): centro del panel, abajo
  const boton: [number, number] = [W * 0.5, H * pY + 214 * u * (movil ? 1.04 : 0.86)];
  return (
    <AbsoluteFill>
      <Mundo semilla={7} />
      <Rotulo texto={e.rotulo} at={t(e.at.rotulo)} sal={sal} />
      <Panel3D ancho={900} alto={600} y={pY} rx={inc.rx} ry={inc.ry} rz={inc.rz} escala={inc.escala * (movil ? 1 : 0.84) * (1 - sal * 0.2)} opacidad={1 - sal}>
        <div style={{ padding: `${30 * u}px ${34 * u}px`, fontFamily: fuentes.texto }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 * u }}>
            <span style={{ fontSize: 34 * u, fontWeight: 800, color: P.texto }}>Pagos por confirmar</span>
            <span style={{ marginLeft: "auto", minWidth: 44 * u, height: 44 * u, borderRadius: 99, display: "flex", alignItems: "center", justifyContent: "center",
                           background: rgba(P.acento, 0.2), color: P.acento, fontWeight: 800, fontSize: 24 * u }}>{hecho > 0.5 ? 0 : 1}</span>
          </div>
          <div style={{ display: "flex", gap: 26 * u, marginTop: 26 * u, alignItems: "center" }}>
            {/* comprobante */}
            <div style={{ width: 230 * u, height: 300 * u, borderRadius: 22 * u, background: "#F4F7F4", padding: 18 * u, flexShrink: 0,
                          transform: `rotate(${-6 + 6 * kc}deg) scale(${0.6 + 0.4 * kc})`, opacity: kc, boxShadow: `0 ${20 * u}px ${40 * u}px -${10 * u}px rgba(0,0,0,0.5)` }}>
              <div style={{ width: 54 * u, height: 54 * u, borderRadius: 99, background: P.acento, margin: `${8 * u}px auto ${12 * u}px`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg width={30 * u} height={30 * u} viewBox="0 0 24 24"><path d="M5 12.5l4.2 4.2L19 7" fill="none" stroke={P.tinta} strokeWidth="3" strokeLinecap="round" /></svg>
              </div>
              <div style={{ textAlign: "center", fontSize: 18 * u, color: "#556", fontWeight: 700 }}>Transferencia exitosa</div>
              <div style={{ textAlign: "center", fontSize: 34 * u, color: P.tinta, fontWeight: 800, margin: `${6 * u}px 0 ${12 * u}px` }}>{e.monto}</div>
              {[0.9, 0.7, 0.8, 0.5].map((w, i) => <div key={i} style={{ height: 10 * u, width: `${w * 100}%`, borderRadius: 9, background: "#D7DDD8", margin: `${10 * u}px auto 0` }} />)}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 26 * u, color: P.suave }}>{e.cliente}</div>
              <div style={{ fontSize: 44 * u, fontWeight: 800, color: P.texto, margin: `${6 * u}px 0` }}>{e.monto}</div>
              <div style={{ fontSize: 24 * u, color: P.suave, fontFamily: fuentes.mono }}>{e.detalle}</div>
            </div>
          </div>
          <div style={{ marginTop: 30 * u, display: "flex", justifyContent: "center" }}>
            {hecho < 0.5 ? (
              <Boton texto="Confirmar pago" u={u} tam={34} pulsado={frame >= clic - 3 && frame <= clic + 3 ? 1 : 0} style={{ width: "100%", justifyContent: "center" }} />
            ) : (
              <div style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: 14 * u, padding: `${18 * u}px`, borderRadius: 16 * u,
                            border: `${2 * u}px solid ${P.acento}`, color: P.acento, fontWeight: 800, fontSize: 34 * u, transform: `scale(${0.9 + 0.1 * hecho})` }}>
                ✓ Pago confirmado
              </div>
            )}
          </div>
        </div>
      </Panel3D>
      <Cursor desde={[W * 0.9, H * 0.95]} hasta={boton} aparece={t(e.at.cursor)} llega={clic - 4} clic={clic} sal={sal} />
      <Estallido x={boton[0]} y={boton[1]} en={clic} />
      <Efecto nombre="click" desde={clic} volumen={0.7} />
      <Efecto nombre="nota_doble" desde={clic + 2} volumen={0.4} />
      <Efecto nombre="whoosh" desde={t(e.at.comprobante)} volumen={0.3} />
    </AbsoluteFill>
  );
};

// ─────────────────────────── 8. ¡listo! ───────────────────────────
export const Listo: React.FC<Props> = ({ e, dur }) => {
  const frame = useCurrentFrame();
  const t = useT(e.from);
  const { W, H, u, fps } = useLienzoPromo();
  const sal = useSalida(dur, 6);
  const a = t(e.at.listo) - 3;
  const circ = prog(frame, a, a + 12, easeOut);
  const chk = prog(frame, a + 6, a + 16, easeOut);
  const k = resorte(frame, a, fps, 8, 180);
  const R = 190 * u;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ backgroundColor: P.acento }} />
      <Mundo semilla={8} />
      <AbsoluteFill style={{ background: rgba(colores.acento, 0.85) }} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 40 * u, opacity: 1 - sal, transform: `scale(${k * (1 + sal * 0.4)})` }}>
        <svg width={R * 2.4} height={R * 2.4} viewBox="0 0 240 240">
          <circle cx="120" cy="120" r="100" fill={P.tinta} opacity={circ} />
          <circle cx="120" cy="120" r="100" fill="none" stroke="#FFFFFF" strokeWidth="10" strokeDasharray={628} strokeDashoffset={628 * (1 - circ)} transform="rotate(-90 120 120)" />
          <path d="M70 124 L105 158 L172 88" fill="none" stroke={P.acento} strokeWidth="20" strokeLinecap="round" strokeLinejoin="round" strokeDasharray={180} strokeDashoffset={180 * (1 - chk)} />
        </svg>
        <span style={{ fontFamily: fuentes.texto, fontWeight: 800, fontSize: 150 * u, letterSpacing: "-0.04em", color: P.tinta }}>{e.texto}</span>
      </AbsoluteFill>
      <Estallido x={W / 2} y={H / 2 - 80 * u} en={a + 8} n={34} radio={620} color={P.tinta} />
      <Efecto nombre="campana" desde={a + 4} volumen={0.45} />
      <Efecto nombre="golpe" desde={a} volumen={0.5} />
    </AbsoluteFill>
  );
};

// ─────────────────────────── 9. píldoras + «se acabaron…» ───────────────────────────
export const Pildoras: React.FC<Props> = ({ e, dur }) => {
  const frame = useCurrentFrame();
  const t = useT(e.from);
  const { W, H, u } = useLienzoPromo();
  const sal = useSalida(dur);
  const cols = 7;
  const anchoCol = W / cols;
  return (
    <AbsoluteFill style={{ backgroundColor: P.tinta, overflow: "hidden" }}>
      {Array.from({ length: cols }, (_, c) => {
        const dir = c % 2 ? 1 : -1;
        const vel = 9 + (c % 3) * 4;
        return Array.from({ length: 6 }, (_, j) => {
          const alto = (260 + ((c * 7 + j * 13) % 5) * 70) * u;
          const y = ((j * 420 * u + dir * frame * vel * u) % (6 * 420 * u) + 6 * 420 * u) % (6 * 420 * u) - 420 * u;
          const k = prog(frame, c * 1.5, c * 1.5 + 14, easeOut);
          return (
            <div key={`${c}-${j}`} style={{ position: "absolute", left: c * anchoCol + anchoCol * 0.16, top: y + (1 - k) * dir * H, width: anchoCol * 0.68, height: alto,
                                            borderRadius: 999, background: (c + j) % 3 === 0 ? P.acento : rgba(colores.acento, 0.18 + 0.12 * ((c + j) % 2)),
                                            boxShadow: (c + j) % 3 === 0 ? `0 0 ${40 * u}px ${rgba(colores.acento, 0.5)}` : undefined }} />
          );
        });
      })}
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 50%, ${rgba(colores.fondo, 0.92)} 20%, ${rgba(colores.fondo, 0.2)} 70%)` }} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <Titular lineas={e.texto} at={e.at.palabras.map(t)} tam={118} color={P.texto} sal={sal} />
      </AbsoluteFill>
      <Efecto nombre="aire" desde={6} volumen={0.4} />
      <Efecto nombre="golpe_corto" desde={t(e.at.palabras[e.at.palabras.length - 2])} volumen={0.4} />
    </AbsoluteFill>
  );
};

// ─────────────────────────── 10. «Hoy»: lo que necesita tu decisión ───────────────────────────
export const Hoy: React.FC<Props> = ({ e, dur }) => {
  const frame = useCurrentFrame();
  const t = useT(e.from);
  const { u, movil } = useLienzoPromo();
  const sal = useSalida(dur);
  const inc = useInclinacion(dur, [26, 20, -8], [11, 9, -3]);
  const tarjetas = e.tarjetas as { titulo: string; detalle: string; n?: number; boton?: string; alerta?: boolean }[];
  const cuenta = Math.round(e.cuenta * prog(frame, t(e.at.cuenta), t(e.at.cuenta) + 30, easeOut));
  return (
    <AbsoluteFill>
      <Mundo semilla={9} />
      <Rotulo texto={e.rotulo} at={t(e.at.rotulo)} sal={sal} />
      <Panel3D ancho={940} y={panelY(movil)} rx={inc.rx} ry={inc.ry} rz={inc.rz} escala={inc.escala * (movil ? 1 : 0.8) * (1 - sal * 0.2)} opacidad={1 - sal}>
        <div style={{ padding: `${28 * u}px ${30 * u}px ${10 * u}px`, fontFamily: fuentes.texto }}>
          <div style={{ fontSize: 46 * u, fontWeight: 800, color: P.texto }}>Hoy</div>
          <div style={{ fontSize: 26 * u, color: P.suave }}>{e.fecha}</div>
          <div style={{ fontSize: 32 * u, color: P.texto, fontWeight: 700, marginTop: 8 * u }}>
            <span style={{ color: P.acento, fontSize: 44 * u, fontWeight: 800 }}>{cuenta}</span> tareas pendientes
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 * u, padding: `${18 * u}px ${30 * u}px ${30 * u}px` }}>
          {tarjetas.map((c, i) => {
            const k = prog(frame, 8 + i * 4, 22 + i * 4, easeOut);
            return (
              <div key={i} style={{ borderRadius: 22 * u, padding: `${20 * u}px ${20 * u}px`, background: rgba(P.texto, 0.05), border: `${1.5 * u}px solid ${rgba(P.texto, 0.08)}`,
                                    opacity: k, transform: `translateY(${(1 - k) * 60 * u}px) rotateX(${(1 - k) * 40}deg)`, fontFamily: fuentes.texto, minHeight: 150 * u }}>
                <div style={{ display: "flex", alignItems: "flex-start", gap: 8 * u }}>
                  <span style={{ fontSize: 25 * u, fontWeight: 800, color: P.texto, lineHeight: 1.2 }}>{c.titulo}</span>
                  {c.n !== undefined && <span style={{ marginLeft: "auto", fontSize: 22 * u, fontWeight: 800, color: c.alerta ? P.alerta : P.acento,
                                                      background: rgba(c.alerta ? P.alerta : P.acento, 0.15), borderRadius: 99, padding: `${4 * u}px ${12 * u}px` }}>{c.n}</span>}
                </div>
                <div style={{ fontSize: 22 * u, color: P.suave, marginTop: 8 * u, lineHeight: 1.3 }}>{c.detalle}</div>
                {c.boton && <div style={{ marginTop: 12 * u }}><Boton texto={c.boton} u={u} tam={20} /></div>}
                <Efecto nombre="tick_suave" desde={8 + i * 4} volumen={0.35} />
              </div>
            );
          })}
        </div>
      </Panel3D>
      <Flotantes items={[{ src: OBJ("calendario"), x: 0.87, y: movil ? 0.8 : 0.86, tam: 170, rot: 12, at: 14 }]} sal={sal} />
      <Efecto nombre="whoosh" volumen={0.35} />
    </AbsoluteFill>
  );
};

// ─────────────────────────── 11. recuperar pago ───────────────────────────
export const Recupera: React.FC<Props> = ({ e, dur }) => {
  const frame = useCurrentFrame();
  const t = useT(e.from);
  const { W, H, u, fps, movil } = useLienzoPromo();
  const sal = useSalida(dur);
  const inc = useInclinacion(dur, [14, 18, -3], [4, 4, -1]);
  const clic = t(e.at.recupera);
  const barra = prog(frame, clic + 2, t(e.at.pagado), easeInOut);
  const pagado = prog(frame, t(e.at.pagado), t(e.at.pagado) + 8);
  const pY = panelY(movil);
  const boton: [number, number] = [W * 0.5, H * pY + 138 * u * (movil ? 1.04 : 0.86)];
  const kCoin = resorte(frame, t(e.at.pagado), fps, 9, 150);
  return (
    <AbsoluteFill>
      <Mundo semilla={10} />
      <Rotulo texto={e.rotulo} at={t(e.at.rotulo)} sal={sal} />
      <Panel3D ancho={900} alto={460} y={pY} rx={inc.rx} ry={inc.ry} rz={inc.rz} escala={inc.escala * (movil ? 1 : 0.84) * (1 - sal * 0.2)} opacidad={1 - sal}>
        <div style={{ padding: `${30 * u}px ${34 * u}px`, fontFamily: fuentes.texto }}>
          <div style={{ fontSize: 36 * u, fontWeight: 800, color: P.texto }}>Cobros pendientes</div>
          <div style={{ fontSize: 26 * u, color: P.suave, marginTop: 6 * u }}>{e.resumen}</div>
          <div style={{ display: "flex", alignItems: "center", marginTop: 26 * u, padding: `${20 * u}px ${24 * u}px`, borderRadius: 22 * u,
                        background: rgba(pagado > 0.5 ? P.acento : P.texto, pagado > 0.5 ? 0.12 : 0.05), border: `${1.5 * u}px solid ${rgba(pagado > 0.5 ? P.acento : P.texto, 0.2)}` }}>
            <div>
              <div style={{ fontSize: 32 * u, fontWeight: 800, color: P.texto }}>{e.cliente}</div>
              <div style={{ fontSize: 24 * u, color: P.suave, fontFamily: fuentes.mono }}>{pagado > 0.5 ? "pagado · ahora" : e.hace}</div>
            </div>
            <div style={{ marginLeft: "auto", fontSize: 44 * u, fontWeight: 800, color: pagado > 0.5 ? P.acento : P.texto }}>{e.monto}</div>
          </div>
          <div style={{ marginTop: 26 * u }}>
            {pagado < 0.5 ? (
              <div style={{ position: "relative" }}>
                <Boton texto="Enviar recordatorio automático" u={u} tam={28} pulsado={frame >= clic - 3 && frame <= clic + 3 ? 1 : 0}
                       style={{ width: "100%", justifyContent: "center", opacity: barra > 0 ? 0.35 : 1 }} />
                {barra > 0 && (
                  <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", padding: `0 ${20 * u}px`, gap: 14 * u }}>
                    <div style={{ flex: 1, height: 12 * u, borderRadius: 9, background: rgba(P.texto, 0.15), overflow: "hidden" }}>
                      <div style={{ width: `${barra * 100}%`, height: "100%", background: P.acento, boxShadow: `0 0 ${16 * u}px ${P.acento}` }} />
                    </div>
                    <span style={{ fontSize: 24 * u, color: P.texto, fontWeight: 700 }}>Recordatorio enviado…</span>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 12 * u, padding: `${18 * u}px`, borderRadius: 16 * u,
                            background: P.acento, color: P.tinta, fontWeight: 800, fontSize: 32 * u, transform: `scale(${0.9 + 0.1 * pagado})` }}>✓ Pago recibido</div>
            )}
          </div>
        </div>
      </Panel3D>
      <Cursor desde={[W * 0.12, H * 0.95]} hasta={boton} aparece={t(e.at.cursor)} llega={clic - 4} clic={clic} sal={sal} />
      <Flotantes items={[{ src: OBJ("check"), x: 0.82, y: movil ? 0.36 : 0.3, tam: 210, rot: 10, at: t(e.at.pagado) }]} sal={sal} />
      {frame >= t(e.at.pagado) && <Estallido x={W * 0.82} y={H * (movil ? 0.36 : 0.3)} en={t(e.at.pagado)} n={20} radio={300} />}
      <Efecto nombre="click" desde={clic} volumen={0.7} />
      <Efecto nombre="subida" desde={t(e.at.pagado)} volumen={0.3} />
      <Efecto nombre="nota_doble" desde={t(e.at.pagado)} volumen={0.45} />
      {kCoin > 2 && null}
    </AbsoluteFill>
  );
};

// ─────────────────────────── 12. tú cierras / atiende / 24/7 ───────────────────────────
export const Remate: React.FC<Props> = ({ e, dur }) => {
  const frame = useCurrentFrame();
  const t = useT(e.from);
  const { W, H, u, fps } = useLienzoPromo();
  const sal = useSalida(dur, 6);
  const gigante = t(e.at.gigante);
  const antes = frame < gigante;
  const k = resorte(frame, gigante, fps, 8, 170);
  return (
    <AbsoluteFill>
      <Mundo semilla={11} oscuro={!antes} />
      {antes ? (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <Titular lineas={e.lineas} at={e.at.palabras.map(t)} tam={124} sal={prog(frame, gigante - 6, gigante)} />
        </AbsoluteFill>
      ) : (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <svg width={W} height={H} style={{ position: "absolute" }}>
            {[0, 1, 2].map((i) => {
              const r = prog(frame, gigante + i * 5, gigante + 30 + i * 5, easeOut);
              return <circle key={i} cx={W / 2} cy={H / 2} r={W * 0.7 * r} fill="none" stroke={rgba(colores.acento, 0.6 * (1 - r))} strokeWidth={6 * u} />;
            })}
          </svg>
          <span style={{ fontFamily: fuentes.texto, fontWeight: 800, fontSize: 330 * u, letterSpacing: "-0.06em", color: P.acento,
                         transform: `scale(${(1.8 - 0.8 * k) * (1 - sal * 0.3)})`, opacity: Math.min(1, k * 1.6) * (1 - sal),
                         textShadow: `0 0 ${80 * u}px ${rgba(colores.acento, 0.6)}` }}>{e.gigante}</span>
        </AbsoluteFill>
      )}
      {!antes && <Flotantes items={[
        { src: OBJ("rayo"), x: 0.2, y: 0.3, tam: 200, rot: -14, at: gigante + 2 },
        { src: OBJ("chat"), x: 0.82, y: 0.7, tam: 220, rot: 12, at: gigante + 5 },
      ]} sal={sal} />}
      {e.at.palabras.map((s: number, i: number) => <Efecto key={i} nombre="golpe_corto" desde={t(s)} volumen={0.3} />)}
      <Efecto nombre="impacto" desde={gigante} volumen={0.5} />
    </AbsoluteFill>
  );
};

// ─────────────────────────── 13. cierre de marca ───────────────────────────
export const Final: React.FC<Props> = ({ e }) => {
  const frame = useCurrentFrame();
  const t = useT(e.from);
  const { u, fps, movil } = useLienzoPromo();
  const k = resorte(frame, 0, fps, 10, 120);
  const kt = resorte(frame, t(e.at.lema), fps, 14, 140);
  const kb = resorte(frame, t(e.at.boton), fps, 10, 160);
  return (
    <AbsoluteFill>
      <Mundo oscuro semilla={12} />
      <Flotantes items={[
        { src: OBJ("chat"), x: 0.18, y: 0.24, tam: 190, rot: -14, at: 4 },
        { src: OBJ("check"), x: 0.84, y: 0.27, tam: 170, rot: 12, at: 8 },
        { src: OBJ("avion"), x: 0.8, y: movil ? 0.74 : 0.8, tam: 180, rot: -8, at: 12, prof: 0.6 },
        { src: OBJ("calendario"), x: 0.18, y: movil ? 0.72 : 0.8, tam: 170, rot: 10, at: 16, prof: 0.6 },
      ]} desplaza={[0, -frame * 0.4]} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 34 * u, paddingBottom: movil ? 120 * u : 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 28 * u, transform: `scale(${k})` }}>
          {logosMarca.isotipo && <Img src={logosMarca.isotipo} style={{ height: 170 * u, filter: `drop-shadow(0 0 ${40 * u}px ${rgba(colores.acento, 0.6)})` }} />}
          <span style={{ fontFamily: fuentes.texto, fontWeight: 800, fontSize: 130 * u, letterSpacing: "-0.045em", color: P.texto }}>{e.marca}</span>
        </div>
        <div style={{ fontFamily: fuentes.titulares, fontStyle: "italic", fontSize: 72 * u, color: P.texto, opacity: kt, transform: `translateY(${(1 - kt) * 30 * u}px)` }}>
          {e.lema.split("*").map((p: string, i: number) => <span key={i} style={{ color: i % 2 ? P.acento : undefined }}>{p}</span>)}
        </div>
        <div style={{ transform: `scale(${kb})`, marginTop: 20 * u }}>
          <Boton texto={e.boton} u={u} tam={46} />
        </div>
      </AbsoluteFill>
      <Efecto nombre="brillo" volumen={0.4} />
      <Efecto nombre="golpe_corto" desde={t(e.at.boton)} volumen={0.4} />
    </AbsoluteFill>
  );
};
