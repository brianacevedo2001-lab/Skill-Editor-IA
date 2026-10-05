// Miniatura de YouTube (Still 1920×1080; se exporta a 1280×720 con --scale).
// La imagen base (persona + fondo, sin texto) viene de Higgsfield o de un fotograma; el texto se pone aquí
// para que salga nítido y con las tipografías y colores de marca. Todo el contenido sale del JSON.
import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { colores, fuentes, logos } from "./marca";
import { rgba } from "./lib/util";

export interface GuionMiniatura {
  imagen: string;            // relativa a publicDir (videos/)
  etiqueta?: string;         // línea pequeña superior (serie, capítulo)
  destacado: string;         // palabra o cifra grande, en color de acento
  titulo: string;            // 1–2 líneas bajo el destacado ("\n" para partir)
  /** Desplaza la imagen base (fracción del ancho) si la persona queda tapada por el texto. */
  desplazamiento?: number;
}
export type PropsMiniatura = { guion: string; datos?: GuionMiniatura };

export const calcularMiniatura = async ({ props }: { props: PropsMiniatura }) => {
  const datos: GuionMiniatura = await (await fetch(staticFile(props.guion))).json();
  return { props: { ...props, datos } };
};

export const Miniatura: React.FC<PropsMiniatura> = ({ datos }) => {
  if (!datos) return null;
  return (
    <AbsoluteFill style={{ backgroundColor: colores.fondo }}>
      <Img src={staticFile(datos.imagen)} style={{
        position: "absolute", width: "100%", height: "100%", objectFit: "cover",
        transform: `translateX(${(datos.desplazamiento ?? 0) * 100}%)`,
      }} />
      {/* velo a la izquierda para que el texto se lea siempre */}
      <AbsoluteFill style={{
        background: `linear-gradient(90deg, ${rgba(colores.fondo, 0.92)} 0%, ${rgba(colores.fondo, 0.75)} 38%, ${rgba(colores.fondo, 0)} 62%)`,
      }} />
      <div style={{ position: "absolute", left: 110, top: 0, bottom: 0, width: 1020, display: "flex",
                    flexDirection: "column", justifyContent: "center", gap: 18 }}>
        {datos.etiqueta && (
          <div style={{ fontFamily: fuentes.mono, fontSize: 38, letterSpacing: 6, textTransform: "uppercase",
                        color: colores.etiqueta }}>{datos.etiqueta}</div>
        )}
        <div style={{ fontFamily: fuentes.texto, fontWeight: 800, fontSize: 250, lineHeight: 0.9, letterSpacing: -8,
                      color: colores.acento, textShadow: `0 0 60px ${rgba(colores.acento, 0.45)}, 0 8px 30px rgba(0,0,0,.6)` }}>
          {datos.destacado}
        </div>
        <div style={{ fontFamily: fuentes.texto, fontWeight: 800, fontSize: 104, lineHeight: 1.0, letterSpacing: -3,
                      color: colores.texto, whiteSpace: "pre-line", textShadow: "0 6px 24px rgba(0,0,0,.7)" }}>
          {datos.titulo}
        </div>
      </div>
      {logos.isotipo && (
        <Img src={logos.isotipo} style={{ position: "absolute", left: 110, bottom: 70, height: 70, opacity: 0.9 }} />
      )}
    </AbsoluteFill>
  );
};
