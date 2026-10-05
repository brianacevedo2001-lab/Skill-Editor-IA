import { Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

export const FPS = 30;
export const f = (s: number) => Math.round(s * FPS);

export const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
export const easeOut = Easing.bezier(0.16, 1, 0.3, 1);
export const easeInOut = Easing.bezier(0.65, 0, 0.35, 1);

/** Progreso 0→1 entre dos fotogramas con curva suave. */
export const prog = (frame: number, a: number, b: number, ease = easeOut) =>
  interpolate(frame, [a, b], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });

/**
 * Entrada y salida de una escena dentro de su <Sequence>. Las salidas necesitan tiempo para verse:
 * por defecto 14 fotogramas de entrada y 16 de salida.
 */
export const useEntradaSalida = (entrada = 14, salida = 16) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return {
    frame,
    dur: durationInFrames,
    ent: prog(frame, 0, entrada),
    sal: prog(frame, durationInFrames - salida, durationInFrames, easeInOut),
  };
};

/** Aleatorio determinista (mulberry32). */
export const azar = (semilla: number) => {
  let a = semilla >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
};

/**
 * Lienzo actual: las escenas se adaptan a 16:9 (YouTube), 9:16 (Shorts/Reels/TikTok) y 4:5 (LinkedIn).
 * `vertical` = más alto que ancho. `abajo` = margen inferior seguro (en 9:16 las apps tapan ~430 px).
 */
export const useLienzo = () => {
  const { width: W, height: H } = useVideoConfig();
  const vertical = H > W;
  const movil = H / W > 1.6;                     // 9:16 (no 4:5)
  return { W, H, cx: W / 2, cy: H / 2, vertical, movil, arriba: movil ? 230 : vertical ? 90 : 0,
           abajo: movil ? 440 : vertical ? 110 : 0 };
};

/** Proyección en perspectiva sencilla (cámara en z = -foco mirando a +z). */
export const proyectar = (x: number, y: number, z: number, foco = 900, cx = 960, cy = 540) => {
  const s = foco / Math.max(foco + z, 1);
  return { x: cx + x * s, y: cy + y * s, s };
};

/** Esfera de Fibonacci: n puntos repartidos uniformemente. */
export const esferaFibonacci = (n: number) => {
  const pts: [number, number, number][] = [];
  const phi = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < n; i++) {
    const y = 1 - (i / (n - 1)) * 2;
    const r = Math.sqrt(1 - y * y);
    pts.push([Math.cos(phi * i) * r, y, Math.sin(phi * i) * r]);
  }
  return pts;
};

export const rotarY = ([x, y, z]: [number, number, number], a: number): [number, number, number] =>
  [x * Math.cos(a) + z * Math.sin(a), y, -x * Math.sin(a) + z * Math.cos(a)];
export const rotarX = ([x, y, z]: [number, number, number], a: number): [number, number, number] =>
  [x, y * Math.cos(a) - z * Math.sin(a), y * Math.sin(a) + z * Math.cos(a)];

/** Hex → rgba. */
export const rgba = (hex: string, a: number) => {
  const h = hex.replace("#", "");
  const n = parseInt(h.length === 3 ? h.split("").map((c) => c + c).join("") : h, 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
};

/** Mezcla dos colores hex (t = 0 → a, 1 → b). */
export const mezclar = (a: string, b: string, t: number) => {
  const p = (h: string) => parseInt(h.replace("#", ""), 16);
  const x = p(a), y = p(b);
  const c = (s: number) => Math.round(((x >> s) & 255) * (1 - t) + ((y >> s) & 255) * t);
  return `rgb(${c(16)}, ${c(8)}, ${c(0)})`;
};

/** Luminancia relativa (para decidir texto claro/oscuro sobre un color). */
export const esClaro = (hex: string) => {
  const n = parseInt(hex.replace("#", ""), 16);
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.62;
};

/** Ruido suave determinista 1D (suma de senos) para la cámara en mano. */
export const ruidoSuave = (t: number, semilla = 0) =>
  Math.sin(t * 0.9 + semilla) * 0.5 + Math.sin(t * 2.3 + semilla * 1.7) * 0.3 + Math.sin(t * 5.1 + semilla * 2.9) * 0.2;

export const normalizar = (w: string) =>
  w.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^\p{L}\p{N}]/gu, "");
