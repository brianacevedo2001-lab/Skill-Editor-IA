// Composición genérica de una parte a cámara (intro, disclaimer), guiada por videos/<id>/<parte>.json.
import React, { useMemo } from "react";
import { AbsoluteFill, Audio, CalculateMetadataFunction, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { getVideoMetadata } from "@remotion/media-utils";
import type { Cuts, DatosParte, Escena, Guion, LogosIndex, Palabra } from "./types";
import { PANTALLA_COMPLETA } from "./types";
import { Grano } from "./fondo/Depth";
import { AutoLogo, Callout, Camara, LowerThird, desenfoqueEn, escalasPunchIn, eventosLogos } from "./escenas/camara";
import { EscenaCompleta } from "./escenas/despacho";
import { Iris, TituloDetras, haloEn } from "./escenas/capas";
import { FondoContext } from "./fondo/Fondos";
import { Index, Subscribe } from "./escenas/youtube";
import { f, rgba, ruidoSuave } from "./lib/util";
import { colores } from "./marca";

export type PropsParte = { guion: string; datos?: DatosParte };

const leer = async <T,>(ruta: string): Promise<T> => {
  const r = await fetch(staticFile(ruta));
  if (!r.ok) throw new Error(`No puedo leer ${ruta} (${r.status})`);
  return r.json();
};

export const calcularParte: CalculateMetadataFunction<PropsParte> = async ({ props }) => {
  const guion = await leer<Guion>(props.guion);
  const [palabras, cuts, logos] = await Promise.all([
    guion.palabras ? leer<Palabra[]>(guion.palabras) : Promise.resolve([]),
    guion.cuts ? leer<Cuts>(guion.cuts) : Promise.resolve(null),
    leer<LogosIndex>("_shared/logos/index.json"),
  ]);
  const fotogramasVideo = cuts?.fotogramas ?? Math.round((await getVideoMetadata(staticFile(guion.video))).durationInSeconds * 30);
  const finEscenas = Math.max(0, ...guion.escenas.map((e) => f(e.to)));
  return {
    durationInFrames: Math.max(fotogramasVideo, finEscenas),
    props: { ...props, datos: { guion, palabras, cuts, logos, fotogramasVideo } },
  };
};

/** Cámara en mano sutil para una escena concreta. */
const EnMano: React.FC<{ activo?: boolean; children: React.ReactNode }> = ({ activo, children }) => {
  const frame = useCurrentFrame();
  if (!activo) return <>{children}</>;
  const t = frame / 30;
  return (
    <AbsoluteFill style={{ transform: `translate(${ruidoSuave(t, 11) * 5}px, ${ruidoSuave(t, 17) * 4}px) rotate(${ruidoSuave(t, 5) * 0.18}deg)` }}>
      {children}
    </AbsoluteFill>
  );
};

export const Parte: React.FC<PropsParte> = ({ datos }) => {
  const frame = useCurrentFrame();
  if (!datos) return null;
  const { guion, palabras, cuts, logos, fotogramasVideo } = datos;
  const cam = guion.camara ?? {};
  const foco = cam.foco ?? [0.5, 0.4];
  const escalas = useMemo(() => escalasPunchIn(cuts, cam.punchIn ?? 0.09), [cuts, cam.punchIn]);
  const eventos = useMemo(() => {
    if (!guion.autoLogos) return [];
    const excluir = typeof guion.autoLogos === "object" ? guion.autoLogos.excluir : [];
    return eventosLogos(palabras, logos, guion.escenas, excluir);
  }, [guion, palabras, logos]);

  const escenas = guion.escenas;
  // Sin persona recortada, "capa": "detras" no tiene sentido: todo va delante.
  const detras = (e: Escena) => !!guion.persona && (e.capa === "detras" || e.type === "tituloDetras");
  const completas = escenas.filter((e) => PANTALLA_COMPLETA.includes(e.type) && !detras(e));
  const capaDetras = escenas.filter((e) => detras(e) && (PANTALLA_COMPLETA.includes(e.type) || e.type === "tituloDetras"));
  const halo = haloEn(frame, capaDetras);
  const sobreCamara = escenas.filter((e) => ["callout", "lowerThird", "subscribe"].includes(e.type));
  const indices = escenas.filter((e) => e.type === "index") as Extract<Escena, { type: "index" }>[];

  const camaraProps = { src: guion.video, fotogramasVideo, escalas, foco, handheld: !!cam.handheld };

  return (
    <FondoContext.Provider value={guion.fondo ?? "profundidad"}>
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <Camara {...camaraProps} desenfoque={desenfoqueEn(frame, escenas)} />

      {/* Capa de detrás: gráficos entre la cámara y la persona recortada */}
      {capaDetras.map((e, i) => (
        <Sequence key={`d${i}`} from={f(e.from)} durationInFrames={Math.max(1, f(e.to) - f(e.from))}>
          <Iris foco={foco} activo={e.entrada === "iris"}>
            {e.type === "tituloDetras" ? <TituloDetras escena={e} /> : <EscenaCompleta escena={e} logos={logos} />}
          </Iris>
          <Camara {...camaraProps} src={guion.persona!} desenfoque={0} inicio={f(e.from)} silenciada transparente
                  filtro={halo > 0.01 ? `drop-shadow(0 0 ${18 * halo}px ${rgba(colores.acento, 0.55 * halo)})` : undefined} />
        </Sequence>
      ))}

      {sobreCamara.map((e, i) => (
        <Sequence key={`c${i}`} from={f(e.from)} durationInFrames={Math.max(1, f(e.to) - f(e.from))}>
          <EnMano activo={e.handheld}>
            {e.type === "callout" && <Callout escena={e} />}
            {e.type === "lowerThird" && <LowerThird escena={e} />}
            {e.type === "subscribe" && <Subscribe escena={e} />}
          </EnMano>
        </Sequence>
      ))}

      {eventos.map((ev, i) => (
        <Sequence key={`l${i}`} from={f(ev.at) - 3} durationInFrames={f(2.4)}>
          <AutoLogo ev={ev} logos={logos} />
        </Sequence>
      ))}

      {indices.map((e, i) => (
        <Sequence key={`i${i}`} from={f(e.from)} durationInFrames={Math.max(1, f(e.to) - f(e.from))}>
          <EnMano activo={e.handheld}>
            <Index escena={e} camara={<Camara {...camaraProps} desenfoque={0} inicio={f(e.from)} silenciada />} />
          </EnMano>
        </Sequence>
      ))}

      {completas.map((e, i) => (
        <Sequence key={`p${i}`} from={f(e.from)} durationInFrames={Math.max(1, f(e.to) - f(e.from))}>
          <EnMano activo={e.handheld}>
            <Iris foco={foco} activo={e.entrada === "iris"}>
              <EscenaCompleta escena={e} logos={logos} />
            </Iris>
          </EnMano>
        </Sequence>
      ))}

      <Grano opacidad={0.045} />
      {guion.musica?.src && <Musica src={guion.musica.src} volumen={guion.musica.volumen} desde={guion.musica.desde ?? 0} />}
    </AbsoluteFill>
    </FondoContext.Provider>
  );
};

/** Música de fondo: entra en 1 s y sale en los últimos 2 s de la parte. */
const Musica: React.FC<{ src: string; volumen: number; desde: number }> = ({ src, volumen, desde }) => {
  const { durationInFrames, fps } = useVideoConfig();
  return (
    <Audio src={staticFile(src)} startFrom={Math.round(desde * fps)} volume={(fr) =>
      volumen * interpolate(fr, [0, fps, durationInFrames - 2 * fps, durationInFrames], [0, 1, 1, 0],
                            { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
  );
};
