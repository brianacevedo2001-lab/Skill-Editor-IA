// Esfera de puntos que gira. Opcional: los puntos salen de la esfera y forman una figura.
import React, { useMemo } from "react";
import { colores } from "../marca";
import { azar, esferaFibonacci, proyectar, rgba, rotarX, rotarY, useLienzo } from "../lib/util";

type Punto = [number, number, number];

/** Figuras en coordenadas normalizadas (-1..1), construidas con formas simples. */
const figura = (nombre: "robot" | "chat", n: number): Punto[] => {
  const r = azar(nombre === "robot" ? 11 : 23);
  const pts: Punto[] = [];
  const contorno = (cx: number, cy: number, w: number, h: number, k: number) => {
    for (let i = 0; i < k; i++) {
      const t = i / k;
      const per = 2 * (w + h);
      let d = t * per, x, y;
      if (d < w) { x = cx - w / 2 + d; y = cy - h / 2; }
      else if ((d -= w) < h) { x = cx + w / 2; y = cy - h / 2 + d; }
      else if ((d -= h) < w) { x = cx + w / 2 - d; y = cy + h / 2; }
      else { d -= w; x = cx - w / 2; y = cy + h / 2 - d; }
      pts.push([x, y, (r() - 0.5) * 0.08]);
    }
  };
  const circulo = (cx: number, cy: number, rad: number, k: number, relleno = false) => {
    for (let i = 0; i < k; i++) {
      const a = (i / k) * Math.PI * 2;
      const rr = relleno ? rad * Math.sqrt(r()) : rad;
      pts.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr, (r() - 0.5) * 0.08]);
    }
  };
  if (nombre === "robot") {
    const u = n / 100;
    contorno(0, -0.28, 0.9, 0.62, Math.round(26 * u));          // cabeza
    circulo(-0.2, -0.3, 0.09, Math.round(9 * u), true);          // ojos
    circulo(0.2, -0.3, 0.09, Math.round(9 * u), true);
    for (let i = 0; i < 5 * u; i++) pts.push([-0.16 + (0.32 * i) / (5 * u), -0.1, 0]); // boca
    for (let i = 0; i < 5 * u; i++) pts.push([0, -0.6 - (0.16 * i) / (5 * u), 0]);     // antena
    circulo(0, -0.8, 0.05, Math.round(4 * u), true);
    contorno(0, 0.42, 1.1, 0.62, Math.round(28 * u));           // cuerpo
    circulo(0, 0.42, 0.11, Math.round(8 * u));                   // «corazón»
  } else {
    // burbuja de chat con tres puntos
    const k = Math.round(n * 0.75);
    for (let i = 0; i < k; i++) {
      const a = (i / k) * Math.PI * 2;
      pts.push([Math.cos(a) * 0.95, Math.sin(a) * 0.62 - 0.05, 0]);
    }
    for (let i = 0; i < 6; i++) pts.push([-0.55 - i * 0.05, 0.5 + i * 0.07, 0]);
    circulo(-0.35, -0.05, 0.08, 6, true); circulo(0, -0.05, 0.08, 6, true); circulo(0.35, -0.05, 0.08, 6, true);
  }
  while (pts.length < n) pts.push(pts[Math.floor(r() * pts.length)].map((v) => v + (r() - 0.5) * 0.03) as Punto);
  return pts.slice(0, n);
};

export const Esfera: React.FC<{
  frame: number;
  radio?: number;
  n?: number;
  cx?: number;
  cy?: number;
  color?: string;
  /** 0 = esfera, 1 = figura. */
  morph?: number;
  figura?: "robot" | "chat" | null;
  /** Escala extra (outro: la esfera se expande). */
  expansion?: number;
  opacidad?: number;
}> = ({ frame, radio = 300, n = 520, cx: cxProp, cy: cyProp, color = colores.acento, morph = 0, figura: fig = null,
        expansion = 1, opacidad = 1 }) => {
  const lienzo = useLienzo();
  const cx = cxProp ?? lienzo.cx, cy = cyProp ?? lienzo.cy - 20;
  const base = useMemo(() => esferaFibonacci(n), [n]);
  const destino = useMemo(() => (fig ? figura(fig, n) : null), [fig, n]);
  const rot = frame * 0.012;
  const puntos = base.map((p, i) => {
    let q = rotarX(rotarY(p, rot), -0.32);
    let [x, y, z] = [q[0] * radio * expansion, q[1] * radio * expansion, q[2] * radio * expansion];
    if (destino && morph > 0) {
      // retardo por punto: salen de la esfera en oleada
      const m = Math.min(1, Math.max(0, morph * 1.4 - (i % 37) / 37 * 0.4));
      const e = m * m * (3 - 2 * m);
      const d = destino[i];
      x = x * (1 - e) + d[0] * radio * 1.15 * e;
      y = y * (1 - e) + d[1] * radio * 1.15 * e;
      z = z * (1 - e) + d[2] * radio * e;
    }
    const pr = proyectar(x, y, z + radio * 1.2, 1100, cx, cy);
    return { x: pr.x, y: pr.y, s: pr.s, z };
  });
  return (
    <svg width={lienzo.W} height={lienzo.H} style={{ position: "absolute", inset: 0, opacity: opacidad }}>
      <defs>
        <radialGradient id="halo">
          <stop offset="0" stopColor={color} stopOpacity="0.28" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx={cx} cy={cy} r={radio * expansion * 1.25} fill="url(#halo)" />
      {puntos
        .sort((a, b) => b.z - a.z)
        .map((p, i) => {
          const frente = Math.max(0, Math.min(1, 0.5 - p.z / (radio * expansion * 2)));
          return (
            <circle key={i} cx={p.x} cy={p.y} r={Math.max(0.8, 3.1 * p.s)}
                    fill={frente > 0.55 ? color : rgba(colores.texto, 0.9)}
                    opacity={0.25 + 0.75 * frente} />
          );
        })}
    </svg>
  );
};
