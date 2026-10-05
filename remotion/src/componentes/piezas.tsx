// Piezas reutilizables: bloque 3D (cristal / acento), ficha de marca, efecto de sonido.
import React from "react";
import { Audio, Img, Sequence, staticFile } from "remotion";
import { colores, fuentes, logos as logosMarca } from "../marca";
import type { Ficha, LogosIndex, Marca, Sfx } from "../types";
import { esClaro, f, rgba } from "../lib/util";
import sonidos from "../sonidos.json";

/** Inclinación 3D muy sutil y minimalista. */
export const inclinacion = (rx = 7, ry = -9, rz = 0) =>
  `perspective(1400px) rotateX(${rx}deg) rotateY(${ry}deg) rotateZ(${rz}deg)`;

export const Bloque: React.FC<{
  variante?: "cristal" | "acento";
  children: React.ReactNode;
  style?: React.CSSProperties;
  radio?: number;
}> = ({ variante = "cristal", children, style, radio = 22 }) => {
  const acento = variante === "acento";
  return (
    <div
      style={{
        position: "relative",
        borderRadius: radio,
        padding: "0.12em 0.42em 0.2em",
        background: acento
          ? `linear-gradient(160deg, ${colores.acento} 0%, ${colores.acento2} 130%)`
          : `linear-gradient(160deg, ${rgba(colores.texto, 0.13)} 0%, ${rgba(colores.texto, 0.04)} 100%)`,
        border: `1px solid ${acento ? rgba("#FFFFFF", 0.35) : rgba(colores.texto, 0.18)}`,
        boxShadow: acento
          ? `0 30px 60px -20px ${rgba(colores.acento, 0.55)}, 0 8px 0 -2px ${rgba(colores.fondo, 0.35)}, inset 0 1px 0 ${rgba("#FFFFFF", 0.5)}`
          : `0 30px 60px -24px rgba(0,0,0,0.7), inset 0 1px 0 ${rgba("#FFFFFF", 0.22)}`,
        backdropFilter: acento ? undefined : "blur(18px) saturate(140%)",
        color: acento ? colores.fondo : colores.texto,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

export const buscarMarca = (logos: LogosIndex, slug?: string): Marca | undefined =>
  slug ? logos.marcas.find((m) => m.slug === slug || m.nombre.toLowerCase() === slug.toLowerCase()) : undefined;

/** Ficha 3D de marca: fondo del color de la marca, logo y nombre. */
export const FichaMarca: React.FC<{
  ficha: Ficha;
  logos: LogosIndex;
  alto?: number;
  conNombre?: boolean;
  style?: React.CSSProperties;
}> = ({ ficha, logos, alto = 150, conNombre = true, style }) => {
  const m = buscarMarca(logos, ficha.logo);
  if (!m && ficha.text) {
    // Ficha de concepto (sin logo): bloque de cristal o de acento con la tipografía de titulares.
    return (
      <Bloque variante={ficha.accent ? "acento" : "cristal"} radio={alto * 0.24}
              style={{ height: alto, display: "flex", alignItems: "center", padding: `0 ${alto * 0.36}px`,
                       fontFamily: fuentes.titulares, fontStyle: "italic", fontSize: alto * 0.5, whiteSpace: "nowrap", ...style }}>
        {ficha.text}
      </Bloque>
    );
  }
  const propia = m?.propia;
  const fondo = propia ? colores.superficie : m?.logoColor ? colores.superficie2 : m?.color ?? colores.superficie2;
  const claro = esClaro(fondo);
  const nombre = ficha.text ?? m?.nombre ?? ficha.logo ?? "";
  const src = propia ? logosMarca.isotipo : m ? staticFile(m.archivo) : null;
  return (
    <div
      style={{
        height: alto,
        display: "flex",
        alignItems: "center",
        gap: alto * 0.2,
        padding: `0 ${alto * 0.3}px 0 ${src ? alto * 0.22 : alto * 0.3}px`,
        borderRadius: alto * 0.24,
        background: `linear-gradient(155deg, ${rgba("#FFFFFF", claro ? 0.0 : 0.16)} 0%, transparent 45%), ${fondo}`,
        border: `1px solid ${rgba("#FFFFFF", propia ? 0.14 : 0.28)}`,
        boxShadow: `0 ${alto * 0.25}px ${alto * 0.5}px -${alto * 0.18}px ${rgba(propia ? colores.acento : m?.logoColor ? m.color : fondo, 0.55)},
                    inset 0 1px 0 ${rgba("#FFFFFF", 0.35)}`,
        color: propia ? colores.texto : claro ? "#111" : "#FFF",
        fontFamily: fuentes.texto,
        fontWeight: 700,
        fontSize: alto * 0.34,
        letterSpacing: "-0.01em",
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      {src && (
        <Img
          src={src}
          style={{
            height: alto * (propia ? 0.72 : 0.5),
            width: alto * (propia ? 0.72 : 0.5),
            objectFit: "contain",
            filter: !propia && claro && !m?.fondoPropio ? "invert(1)" : undefined,
          }}
        />
      )}
      {conNombre && <span>{nombre}</span>}
    </div>
  );
};

/** Los 10 efectos originales conservan su volumen aprobado; el resto lleva la ganancia de su familia. */
const ORIGINALES = new Set(["sub_hit", "tick", "swell", "nota", "nota_mi", "whoosh", "fade_out", "click", "campana", "tecla"]);
type MetaSonido = { dur: number; pico: number; ancla: "inicio" | "pico" | "fin"; gain_db: number };
const META = sonidos as Record<string, MetaSonido>;

/**
 * Efecto de sonido en el fotograma `desde` de la secuencia actual.
 * - `alinear`: qué parte del sonido cae en `desde`: su inicio, su golpe (`pico`) o su final (`fin`, p. ej. una
 *   subida que termina en el revelado). Por defecto, el ancla del sonido en sonidos.json.
 * - `pan`: −1 izquierda … 1 derecha (una pieza que entra por un lado suena por ese lado).
 */
export const Efecto: React.FC<{ nombre: Sfx | undefined; desde?: number; volumen?: number; pan?: number;
                               alinear?: "inicio" | "pico" | "fin" }> = ({ nombre, desde = 0, volumen = 0.6, pan = 0, alinear }) => {
  if (!nombre) return null;
  const m = META[nombre];
  const modo = alinear ?? m?.ancla ?? "inicio";
  const adelanto = !m || modo === "inicio" ? 0 : f(modo === "pico" ? m.pico : m.dur);
  const inicio = desde - adelanto;
  const lado = pan <= -0.3 ? "_izq" : pan >= 0.3 ? "_der" : "";
  const ganancia = m && !ORIGINALES.has(nombre) ? 10 ** (m.gain_db / 20) : 1;
  return (
    <Sequence from={Math.max(0, inicio)} durationInFrames={f(Math.max(3, (m?.dur ?? 2) + 0.5))} layout="none">
      <Audio src={staticFile(`_shared/sfx/${nombre}${lado}.wav`)} volume={volumen * ganancia}
             startFrom={inicio < 0 ? -inicio : 0} />
    </Sequence>
  );
};

/** Divide «texto con *acento*» en palabras marcando las de acento. */
export const palabrasConAcento = (linea: string) => {
  const res: { t: string; acento: boolean }[] = [];
  let dentro = false;
  for (const tok of linea.split(/\s+/).filter(Boolean)) {
    const abre = tok.startsWith("*");
    const cierra = tok.endsWith("*");
    if (abre) dentro = true;
    res.push({ t: tok.replace(/\*/g, ""), acento: dentro });
    if (cierra) dentro = false;
  }
  return res;
};
