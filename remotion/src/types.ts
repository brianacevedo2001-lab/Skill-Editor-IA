// Guion de una parte del vídeo (videos/<id>/intro.json, disclaimer.json, grueso.json).
// Todos los tiempos (`from`, `to`, `…At`) son SEGUNDOS del corte (anclados a palabras de
// <corte>.palabras_corte.json). Si se vuelve a cortar el clip: pipeline/remap_times.py.

/** Nombre de un efecto de videos/_shared/sfx sin extensión. `null` = sin efecto. */
export type Sfx = string | null;

interface EscenaBase {
  from: number;
  to: number;
  /** Cámara en mano sutil. */
  handheld?: boolean;
  /** Efecto de sonido al entrar. Si se omite, cada escena usa el suyo por defecto; `null` = ninguno. */
  sfx?: Sfx;
  /** Toque de color de la escena (hex). Por defecto, el acento de la marca. */
  tint?: string;
  /** Solo documentación: la frase a la que va anclada. */
  ancla?: string;
  /** "detras": se pinta DETRÁS de la persona recortada (requiere "persona" en el guion; recortar.py). */
  capa?: "detras";
  /** Con capa "detras": contorno luminoso en la persona (por defecto sí). */
  halo?: boolean;
  /** Entrada de una escena a pantalla completa: "iris" = se abre en círculo desde la cara (sin corte seco). */
  entrada?: "iris";
}

/** Ficha de `lineup` / `orbChips`: logo de la librería (slug de logos/index.json) o texto. */
export interface Ficha {
  logo?: string;
  text?: string;
  /** Segundo en el que la ficha se desvanece (negar/descartar): gris, desenfoque, se hunde. */
  strikeAt?: number;
  /** Segundo en el que aparece (por defecto, escalonado al entrar). */
  at?: number;
  /** Ficha de texto en el color de acento (la idea que «gana»). */
  accent?: boolean;
}

export type Escena =
  // ── Pantalla completa (siempre sobre el fondo 3D Depth) ──
  | (EscenaBase & {
      type: "orbOpen";
      headline: string;
      /** Segundos en que entra cada palabra del titular (si no, escalonado). */
      wordsAt?: number[];
      /** Palabras del titular resaltadas en el color de acento (índices). */
      accent?: number[];
      /** Los puntos de la esfera forman una figura. */
      figure?: "robot" | "chat" | null;
      figureAt?: number;
      isotipo?: boolean;
    })
  | (EscenaBase & { type: "lineup"; items: Ficha[]; title?: string })
  | (EscenaBase & {
      type: "revealStat";
      logo?: string;
      /** 0-100: celdas de la cuadrícula de 100 que se llenan. */
      value: number;
      label: string;
      /** Texto grande (por defecto «value %»). */
      display?: string;
      /** Fuente del dato, en pequeño (obligatoria para cifras de estudios). */
      fuente?: string;
      /** false = sin la cuadrícula de 100 (cifras que no son porcentaje: «4 h»). */
      grid?: boolean;
    })
  | (EscenaBase & {
      type: "bars";
      title?: string;
      /** Barras horizontales 0-100 que crecen; `at` = segundo en que entra cada una. */
      items: { label: string; value: number; display?: string; at?: number; accent?: boolean }[];
      fuente?: string;
    })
  | (EscenaBase & {
      type: "broll";
      /** Vídeo de apoyo (relativo a videos/), a pantalla completa y sin sonido; la voz sigue. */
      src: string;
      /** Segundo del clip desde el que empieza. */
      startFrom?: number;
      /** Rótulo pequeño opcional abajo a la izquierda. */
      label?: string;
    })
  | (EscenaBase & {
      type: "notificacion";
      title?: string;
      /** Notificaciones del móvil; la nueva entra arriba y empuja a las anteriores. app = slug de logos. */
      items: { app?: string; nombre?: string; titulo: string; texto?: string; hora?: string; at?: number }[];
    })
  | (EscenaBase & {
      type: "buscador";
      title?: string;
      /** Lo que se escribe en la barra (letra a letra, `speed` letras/s, desde `typeAt`). */
      query: string;
      typeAt?: number;
      speed?: number;
      /** Logo del buscador (slug), si no, una lupa. */
      logo?: string;
      results?: { text: string; accent?: boolean; at?: number }[];
    })
  | (EscenaBase & {
      type: "pasos";
      title?: string;
      /** Ruta de 2–5 pasos: en fila en 16:9, en columna en vertical. `at` = segundo en que se activa cada paso. */
      items: { title: string; text?: string; logo?: string; at?: number }[];
    })
  | (EscenaBase & {
      type: "comentario";
      /** "chat" (burbujas, `yo` a la derecha) o "comentarios" (lista con avatar y me gusta). */
      estilo?: "chat" | "comentarios";
      title?: string;
      app?: string;
      items: { autor: string; texto: string; at?: number; likes?: number; yo?: boolean }[];
    })
  | (EscenaBase & { type: "rise"; title: string; points?: number[]; valueLabel?: string })
  | (EscenaBase & { type: "orbChips"; chips: Ficha[]; title?: string; center?: "isotipo" | string })
  | (EscenaBase & { type: "dissolve"; word: string; dissolveAt?: number; kicker?: string })
  | (EscenaBase & { type: "outro"; title: string; kicker?: string })
  // ── Sobre la cámara ──
  | (EscenaBase & {
      type: "callout";
      /** Líneas del rótulo. Palabras entre *asteriscos* van en bloque de acento. */
      lines: string[];
      /** Segundos en que entra cada palabra (en orden, todas las líneas). */
      wordsAt?: number[];
    })
  | (EscenaBase & {
      type: "index";
      title: string;
      chapters: { title: string; start: number; jumpAt?: number }[];
      /** Duración total del vídeo final en segundos (para la barra). */
      total: number;
    })
  | (EscenaBase & {
      type: "subscribe";
      subscribeAt: number;
      bellAt?: number;
      commentAt?: number;
      commentText?: string;
    })
  | (EscenaBase & { type: "lowerThird" })
  | (EscenaBase & {
      type: "tituloDetras";
      /** Titular gigante detrás de la cabeza (*acento* permitido). Va siempre en la capa "detras". */
      text: string;
      kicker?: string;
      /** "depth": la sala se sustituye por el fondo 3D (la persona flota sobre él). */
      fondo?: "camara" | "depth";
      /** Altura del titular (fracción del alto, desde arriba). */
      y?: number;
    });

export type TipoEscena = Escena["type"];
export const PANTALLA_COMPLETA: TipoEscena[] = ["orbOpen", "lineup", "revealStat", "rise", "orbChips", "dissolve", "outro", "bars", "broll",
  "notificacion", "buscador", "pasos", "comentario"];

export interface Guion {
  parte: "intro" | "disclaimer" | "grueso" | "datos" | "cierre" | "vertical";
  /** Rutas relativas a videos/ (publicDir). */
  video: string;
  cuts?: string;
  palabras?: string;
  camara?: {
    /** Punto de la cara en el encuadre (0-1). */
    foco?: [number, number];
    /** Punch-in por corte, alternando. Máximo 0.09. */
    punchIn?: number;
    handheld?: boolean;
  };
  /** desde: segundo del tema en el que empieza (pipeline/golpe_musica.py lo cuadra con un golpe). */
  musica?: { src: string | null; volumen: number; desde?: number };
  /** Fondo de las escenas a pantalla completa (por defecto "profundidad"). Variar entre vídeos: historial.py. */
  fondo?: "profundidad" | "puntos" | "aurora";
  /** Persona recortada con alfa (pipeline/recortar.py), relativa a videos/: activa las escenas "capa": "detras". */
  persona?: string;
  /** Ficha con logo cada vez que se nombra una marca en tramos a cámara. */
  autoLogos?: boolean | { excluir?: string[] };
  escenas: Escena[];
}

// ── Datos que carga calculateMetadata ──
export interface Palabra { i: number; w: string; inicio: number; fin: number }
export interface Cuts { fps: number; fotogramas: number; duracion: number; segmentos: { src: [number, number]; cut: [number, number] }[] }
export interface Marca {
  slug: string; nombre: string; alias: string[]; color: string; archivo: string;
  fondoPropio: boolean; propia?: boolean; acento?: string;
  /** Logo oficial a color (Lobe Icons / SVGL): va sobre la superficie oscura de la marca, no sobre su color. */
  logoColor?: boolean;
}
export interface LogosIndex { marcas: Marca[]; bloqueados: string[] }

export interface DatosParte {
  guion: Guion;
  palabras: Palabra[];
  cuts: Cuts | null;
  logos: LogosIndex;
  /** Duración del clip de cámara en fotogramas. */
  fotogramasVideo: number;
}
