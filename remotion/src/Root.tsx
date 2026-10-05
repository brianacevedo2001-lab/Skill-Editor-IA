import { Composition, Still } from "remotion";
import { Prueba } from "./Prueba";
import { Parte, calcularParte } from "./Parte";
import { Grueso, GruesoGraficos, calcularGrueso } from "./Grueso";
import { Miniatura, calcularMiniatura } from "./Miniatura";
import { Short, calcularShort } from "./Short";
import { Lamina, calcularLamina } from "./Lamina";
import { Anuncio, calcularAnuncio } from "./promo/Anuncio";

export const ANCHO = 1920;
export const ALTO = 1080;
export const FPS = 30;

// El guion se elige por props:  npx remotion render src/index.ts Intro --props='{"guion":"<id>/intro.json"}'
export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition id="Prueba" component={Prueba} durationInFrames={90} fps={FPS} width={ANCHO} height={ALTO} />
      {(["Intro", "Disclaimer", "Catalogo"] as const).map((id) => (
        <Composition
          key={id}
          id={id}
          component={Parte}
          calculateMetadata={calcularParte}
          durationInFrames={300}
          fps={FPS}
          width={ANCHO}
          height={ALTO}
          defaultProps={{
            guion: id === "Catalogo" ? "ejemplo/catalogo.json" : `ejemplo/${id.toLowerCase()}.json`,
          }}
        />
      ))}
      <Composition id="Grueso" component={Grueso} calculateMetadata={calcularGrueso} durationInFrames={300}
                   fps={FPS} width={ANCHO} height={ALTO} defaultProps={{ guion: "_prueba_grueso/grueso.json" }} />
      <Composition id="GruesoGraficos" component={GruesoGraficos} calculateMetadata={calcularGrueso} durationInFrames={300}
                   fps={FPS} width={ANCHO} height={ALTO} defaultProps={{ guion: "_prueba_grueso/grueso.json" }} />
      <Composition id="Short" component={Short} calculateMetadata={calcularShort} durationInFrames={300}
                   fps={FPS} width={1080} height={1920} defaultProps={{ guion: "ejemplo/shorts/3-minutos/short.json" }} />
      <Composition id="Linkedin" component={Short} calculateMetadata={calcularShort} durationInFrames={300}
                   fps={FPS} width={1080} height={1350} defaultProps={{ guion: "ejemplo/shorts/3-minutos/short.json" }} />
      <Composition id="Anuncio" component={Anuncio} calculateMetadata={calcularAnuncio} durationInFrames={300}
                   fps={FPS} width={1080} height={1920} defaultProps={{ guion: "ejemplo/anuncio.json" }} />
      <Composition id="AnuncioLinkedin" component={Anuncio} calculateMetadata={calcularAnuncio} durationInFrames={300}
                   fps={FPS} width={1080} height={1350} defaultProps={{ guion: "ejemplo/anuncio.json" }} />
      <Still id="Lamina" component={Lamina} calculateMetadata={calcularLamina} width={1080} height={1350}
             defaultProps={{ guion: "ejemplo/linkedin.json", indice: 0 }} />
      <Still id="Miniatura" component={Miniatura} calculateMetadata={calcularMiniatura} width={ANCHO} height={ALTO}
             defaultProps={{ guion: "ejemplo/miniatura.json" }} />
    </>
  );
};
