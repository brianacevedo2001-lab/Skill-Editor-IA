// Una escena a pantalla completa, sea del tipo que sea (lo usan Parte y Short: un solo sitio que mantener).
import React from "react";
import type { Escena, LogosIndex } from "../types";
import { Bars, Broll, Dissolve, Lineup, OrbChips, OrbOpen, Outro, RevealStat, Rise } from "./completas";
import { Buscador, Comentario, Notificacion, Pasos } from "./nuevas";

export const EscenaCompleta: React.FC<{ escena: Escena; logos: LogosIndex }> = ({ escena: e, logos }) => (
  <>
    {e.type === "orbOpen" && <OrbOpen escena={e} logos={logos} />}
    {e.type === "lineup" && <Lineup escena={e} logos={logos} />}
    {e.type === "revealStat" && <RevealStat escena={e} logos={logos} />}
    {e.type === "rise" && <Rise escena={e} logos={logos} />}
    {e.type === "orbChips" && <OrbChips escena={e} logos={logos} />}
    {e.type === "dissolve" && <Dissolve escena={e} logos={logos} />}
    {e.type === "outro" && <Outro escena={e} logos={logos} />}
    {e.type === "bars" && <Bars escena={e} logos={logos} />}
    {e.type === "broll" && <Broll escena={e} logos={logos} />}
    {e.type === "notificacion" && <Notificacion escena={e} logos={logos} />}
    {e.type === "buscador" && <Buscador escena={e} logos={logos} />}
    {e.type === "pasos" && <Pasos escena={e} logos={logos} />}
    {e.type === "comentario" && <Comentario escena={e} logos={logos} />}
  </>
);
