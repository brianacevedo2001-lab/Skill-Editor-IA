// Composición de prueba de la fase 1: comprueba fuentes, colores y logo de la marca.
import { AbsoluteFill, Img, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { canal, colores, formatoSuscriptores, fuentes, logos, marca } from "./marca";

export const Prueba: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const entrada = spring({ frame, fps, config: { damping: 200 } });

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(60% 50% at 50% 40%, ${colores.superficie} 0%, ${colores.fondo} 70%)`,
        alignItems: "center",
        justifyContent: "center",
        gap: 36,
      }}
    >
      {logos.isotipo && (
        <Img
          src={logos.isotipo}
          style={{ height: 260, opacity: entrada, transform: `translateY(${interpolate(entrada, [0, 1], [40, 0])}px)` }}
        />
      )}
      <div style={{ fontFamily: fuentes.titulares, fontStyle: "italic", fontSize: 110, color: colores.texto }}>
        Cada chat es una venta<span style={{ color: colores.acento }}>.</span>
      </div>
      <div style={{ fontFamily: fuentes.texto, fontSize: 40, fontWeight: 600, color: colores.texto }}>
        {marca.persona.nombre} <span style={{ color: colores.textoSuave, fontWeight: 400 }}>· {marca.persona.cargo}</span>
      </div>
      <div style={{ fontFamily: fuentes.mono, fontSize: 24, letterSpacing: 3, color: colores.etiqueta, textTransform: "uppercase" }}>
        {canal.handle} — {formatoSuscriptores(canal.suscriptores ?? 0)} suscriptores
      </div>
    </AbsoluteFill>
  );
};
