# Editor de vídeos con IA (marca blanca)

Proyecto marca blanca: nada de nombres, logos ni colores fijos en el código. Todo sale de `marca/`
(`marca.json` identidad y colores, `canal.json` canal, sitio y redes, `proyecto.json` equipo y carpetas).
Idioma de trabajo: español. Probado de punta a punta con un proyecto real (aquí, «proyecto01»: episodio de una serie de YouTube).

**Reglas de trabajo (adáptalas a tu caso)**
- No publicar nada, no gastar créditos y no subir archivos a ningún servicio sin preguntar (excepción: copiar
  las entregas a su Drive `final/<id>/`, que es SIEMPRE). Al gastar créditos, decir cuánto y cuánto queda.
- Enlaces públicos: SIEMPRE `https://tumarca.com` (nunca el dominio largo). Redes en `marca/canal.json`.
- Cámara real siempre; un gemelo digital (p. ej. HeyGen) solo como plan B.
- Cuando algo falle y se arregle, apuntarlo en «Reglas técnicas» (al final).

## 1. Entregables de CADA proyecto

1. **YouTube horizontal** (1920×1080, −14 LUFS): partes → montaje con capítulos, descripción y miniatura.
2. **UN vertical grabado aparte** (móvil en vertical) → 3 versiones con textos distintos: **YouTube Shorts con
   música**, **Instagram Reels SIN música** y **TikTok SIN música** (el usuario pone la música al publicar).
3. **LinkedIn**: vídeo 4:5 (el mismo vertical, sin música), carrusel PDF, imagen suelta y texto del post.
4. Si el usuario no trae guiones, Claude los escribe (`videos/_shared/plantillas/guiones.md`) y le entrega una guía de
   grabación paso a paso (ejemplo real: `videos/proyecto01/guia_grabacion.md`).
Todo termina en `<DRIVE>/final/<id>/` (`shorts/`, `linkedin/`). La publicación es manual.

## 2. Estructura

```
marca/            identidad (único sitio con nombres, colores, logos, redes)
pipeline/         scripts Python (numerados en el orden del flujo) + comun.py
remotion/         composiciones: Intro|Disclaimer|Catalogo (Parte), Grueso/GruesoGraficos, Short, Linkedin,
                  Lamina, Miniatura · escenas en src/escenas · scripts/qa.mjs, laminas.mjs, logos.mjs
videos/           publicDir de Remotion: SOLO lo que Remotion lee (cortes finales, JSON, broll, música, logos)
  _shared/        music/, logos/, fx/, marca/, descripciones/plantilla.txt, plantillas/guiones.md
  <id>/           plan.md, guia_grabacion.md, partes.json, <parte>.json, shorts.json, linkedin.json,
                  capitulos_youtube.txt, resumen.txt, miniatura*.json, broll/
raw/<id>/         brutos copiados de Drive + intermedios pesados (partes/*_bruto.mov, grueso_*.mp4)
out/              renders por parte, qa/, miniatura/, entregas/<id>/ (lo que va a Drive), lote_<id>.cmd/.log
```

## 3. Flujo completo de un proyecto (como proyecto01)

**0. Preparar** — guion y guía de grabación (`guia_grabacion.md`); si hay demo de la app, que sea un tenant con
datos ficticios (así no hay que pixelar). Grabación: móvil horizontal a la altura de los ojos (cámara frontal +
Nano Teleprompter), audio con el micrófono USB en OBS (plan B probado) o directo al móvil; claqueta «Bloque X, toma Y» y
palmada; bloque de pantalla con OBS + móvil; vertical aparte de pie.

**1. Traer y revisar** — `python pipeline/brutos.py traer <id> …` (o copia con `comun.copiar_reanudable`).
`ffprobe` de todo: rotación, resolución, fps. Mirar un fotograma con texto: **la cámara frontal graba en espejo**.

**2. Partes de cámara** (intro / datos / cierre…; una sesión con todos los bloques seguidos):
```
python pipeline/05_sync.py <obs_audio.mp4> <movil.mp4> videos/<id>/camara.sync.json      # desfase por voz
#  sesión = vídeo del móvil (hflip, fps=30) + audio de OBS desplazado → raw/<id>/camara_sesion.mov (ffmpeg)
python pipeline/02_transcribe.py raw/<id>/camara_sesion.mov videos/<id>/sesion.transcripcion.json
#  tramos de cada parte (tras la claqueta, ±0,3 s) → videos/<id>/partes.json
python pipeline/extraer_partes.py raw/<id>/camara_sesion.mov videos/<id>/partes.json  # → <parte>_bruto.mov
#  (mover los *_bruto.mov a raw/<id>/partes/: publicDir ligero)
python pipeline/02_transcribe.py raw/<id>/partes/<parte>_bruto.mov videos/<id>/<parte>.transcripcion.json
python pipeline/03_tomas.py videos/<id>/<parte>.transcripcion.json videos/<id>/<parte>.palabras.json [--quitar i-j]
python pipeline/01_cut_silences.py raw/<id>/partes/<parte>_bruto.mov videos/<id>/<parte>.mp4 --words videos/<id>/<parte>.palabras.json
#  (01_cut_silences y 04_grueso llaman solos a alinear.py: tiempos de palabra exactos; --sin-alinear para no)
python pipeline/recortar.py videos/<id>/<parte>.mp4 [--desde a --hasta b]   # opcional: persona con alfa (capas)
```
Leer el «Texto final» de 03_tomas: quitar a mano deslices que cambian el sentido. Verificación ≥ 98 %.

**3. Concepto y escenas**
```
python pipeline/lectura.py <id> <parte>          # ritmo, énfasis, cifras, marcas, bloques → <parte>.lectura.md
python pipeline/historial.py comparar <id>       # qué repetiría respecto a los últimos vídeos; fondo sugerido
#  → videos/<id>/concepto.md (plantilla videos/_shared/plantillas/concepto.md): idea, fondo, piezas, capas, música
#  → videos/<id>/<parte>.json (catálogo §4) anclado a <parte>.palabras_corte.json; "ancla" = frase que se oye
python pipeline/golpe_musica.py videos/<id>/intro.json --en <seg del momento clave> [--tambien …] --aplicar 1
```
Música: intro épica 0,16; resto jazz 0,13; `musica.desde` = segundo del tema en que arranca (golpe_musica.py lo
cuadra para que un golpe caiga en el momento clave). `camara.foco` = posición de la cara (medir con rejilla).
QA: `node remotion/scripts/qa.mjs Intro <id>/<parte>.json 3 9 17 … --nombre x` y MIRAR los fotogramas.
Tras el render de cada parte: `python pipeline/verificar_sync.py videos/<id>/<parte>.json out/<id>_<parte>.mp4`
→ duraciones, voz vs corte y cada escena contra su ancla + hoja de contactos `out/qa/<id>_<parte>_sync.jpg`.

**4. Bloque de pantalla (grueso)**
```
python pipeline/05_sync.py <pantalla.mp4> <movil.mp4> videos/<id>/grueso.sync.json
python pipeline/02_transcribe.py <pantalla.mp4> videos/<id>/grueso.transcripcion.json
python pipeline/03_tomas.py videos/<id>/grueso.transcripcion.json videos/<id>/grueso.palabras.json
#  grueso.prep.json: recorte/rellenar, voltearCamara, quitar (arranques y «esto no sale»), pixelar
#  (datos reales: hojas.py + pixelar_auto.py; datos ficticios: solo la cuenta de la cabecera)
python pipeline/04_grueso.py videos/<id>/grueso.prep.json
python pipeline/06_zooms.py videos/<id>/grueso_pantalla.mp4 videos/<id>/grueso.json
#  + acercamientos manuales a lo que se nombra (frases del corte ↔ posición en pantalla)
#  mover grueso_pantalla/camara a raw/<id>/partes/ y apuntar grueso.json a ../raw/...
python pipeline/render_grueso.py videos/<id>/grueso.json        # híbrido ffmpeg + Remotion, ~3–10 min
```

**5. B-roll, miniatura y renders**
- B-roll: Higgsfield Kling 3.0 std 5 s sin sonido (~6,25 créditos/clip) → `videos/<id>/broll/` (1080p30, `-g 15`).
- Miniatura: §6. Dos variantes, elegir la que no choca con el texto.
- Renders de las partes de cámara: proceso independiente `out/lote_<id>.cmd` (Start-Process), ~20–25 min por
  3 min de vídeo (`npx remotion render src/index.ts Intro ../out/<id>_<parte>.mp4 --props=… --timeout=180000`).

**6. Montaje final** — `capitulos_youtube.txt` (tiempos relativos a cada parte) + `resumen.txt` (con fuentes):
```
python pipeline/07_final.py out/entregas/<id> "<Título>.mp4" out/<id>_intro.mp4 out/<id>_datos.mp4 out/<id>_grueso.mp4 out/<id>_cierre.mp4 --id <id> --capitulos videos/<id>/capitulos_youtube.txt --titulo "<Título>" --miniatura out/miniatura/<id>_miniatura.jpg
```
→ −14 LUFS, capítulos válidos, descripción, miniatura, y copia a Drive. Revisar las uniones entre partes.

**7. Vertical + LinkedIn**
```
#  vertical: 02 → 03 → 01 sobre el bruto (hflip; sale 1080×1920) · videos/<id>/vertical.json con escenas
#  shorts.json: {"parte": "vertical", "tramos": [[0, dur]], "gancho": [...], "textos": {youtube, instagram, tiktok, linkedin}}
python pipeline/09_shorts.py <id> --sin-render ; node remotion/scripts/qa.mjs Short <id>/shorts/<n>/short.json 1.2 7 22
python pipeline/09_shorts.py <id>          # YT (música) + IG + TikTok + LinkedIn 4:5 + portada + textos → Drive
python pipeline/10_linkedin.py <id>        # carrusel PDF + JPG + imagen + post → Drive
```
Anuncio corto (ejemplo real: `videos/promo01/`, promo de 12 s grabada por otra persona): mismo flujo de vertical,
escenas densas (gancho → `notificacion` del problema → marca a cámara con autoLogo → `comentario` chat que
responde → `revealStat` cifra sola) y `"cola": 4` en el short = segundos extra tras la última palabra (cámara
congelada, sin voz) para un `outro` de marca con `tumarca.com`; `"cierre": ""` quita el rótulo pequeño.

**Anuncio de producto animado con locución** (ejemplo real: `videos/anuncio01/`, réplica del estilo de un anuncio
de SaaS que el usuario grabó de Instagram): sin cámara; la app de la marca recreada en paneles 3D.
```
#  1. Estudiar la referencia: hojas de 1 fps (ffmpeg tile) + transcribir su locución → estructura de frases.
#  2. Pantallas reales de la app (p. ej. raw/<id>/partes/grueso_pantalla.mp4 de proyecto01) → datos de demostración.
#  3. Guion de locución (≈ 40–45 s, una idea por frase) → Higgsfield `elevenlabs_v4` (ver §7) → voz.
#  4. videos/<id>/locucion.voz.wav (−16 LUFS) + palabras (Whisper) + alinear.py → tiempos de cada palabra.
#  5. videos/<id>/anuncio.json: escenas {tipo, from, to, transicion, at:{…palabra…}} (tiempos sacados de las
#     palabras con un script) + musica {src, volumen, desde} + portada + textos por red.
node remotion/scripts/qa.mjs Anuncio <id>/anuncio.json 1.2 7.9 … ; … AnuncioLinkedin …   # ¡mirar 9:16 y 4:5!
python pipeline/anuncio.py <id>     # render Anuncio + AnuncioLinkedin → YT (música), IG, TikTok, LinkedIn → Drive
```
Escenas (`remotion/src/promo/`): `apertura` (mancha orgánica + titular cinético), `canales` (logo + canales que
se juntan en una bandeja), `medianoche` (teléfono 3D con notificaciones), `chat` (vendedor IA escribiendo + link
de pago), `leads` (tabla con puntaje y resaltado caliente/tibio/frío sincronizado), `handoff` (traspaso con
contexto), `pago` (comprobante + cursor que pulsa), `listo` (check con estallido), `pildoras` (columnas de
píldoras + frase), `hoy` (panel de tareas del día), `recupera` (cursor + barra + pago recuperado), `remate` (frases
cinéticas + cifra gigante), `final` (logo, lema y botón). `"transicion": "mancha"` = barrido orgánico con agujero.
Mundo claro derivado de `brillo` + paneles oscuros de la app + objetos 3D de Higgsfield (`videos/_shared/obj/`).

**8. Cerrar** — `python pipeline/historial.py registrar <id>`; informe para el usuario (`out/entregas/<id>/LEEME_<id>.md`, también en Drive): qué hay, qué revisar,
créditos gastados, textos listos para pegar por red.

## 4. Catálogo de escenas (`type` en los JSON; tiempos = segundos del corte)

Sobre la cámara:
- `callout` — rótulo grande con la cámara desenfocada; `lines`, `*acento*`, `wordsAt` (entra palabra a palabra).
  Frases clave, ganchos, conclusiones. En vertical: líneas ≤ 17 letras.
- `lowerThird` — nombre y cargo (de `marca.json`) al presentarse.
- autoLogos (`"autoLogos": true`) — ficha con logo cuando se nombra una marca de `_shared/logos/index.json`.
A pantalla completa (fondo 3D; se adaptan a 16:9, 9:16 y 4:5):
- `orbOpen` — esfera de partículas + titular; `figure: chat|robot` (apertura de capítulo, tesis).
- `lineup` — fichas en fila (logos o texto); `strikeAt` apaga una idea (negación = gris y desenfoque, nunca tachado
  rojo); `accent` la que gana.
- `revealStat` — cifra grande + cuadrícula de 100; `display`, `label`, `fuente`, `grid:false` para no-porcentajes.
- `bars` — barras comparativas (56 % vs 28 %), `accent` en la importante, `fuente`.
- `rise` — curva que sube; `orbChips` — logos orbitando (canales); `dissolve` — palabra que se deshace;
  `outro` — cierre con kicker; `broll` — plano de apoyo a pantalla completa (la voz sigue).
- `notificacion` — notificaciones del móvil que caen (la nueva arriba empuja a las demás); `items[{app, nombre,
  titulo, texto, hora, at}]`. El problema («mientras no contestas…»).
- `buscador` — barra que se escribe sola (`query`, `typeAt`, `speed`) y despliega `results` (`accent` el bueno).
- `pasos` — ruta de 2–5 pasos (fila en 16:9, columna en vertical); `items[{title, text, logo, at}]`; el activo brilla.
- `comentario` — `estilo: "chat"` (burbujas, `yo` a la derecha, «escribiendo…») o `"comentarios"` (avatar + me gusta).
- Grueso: `zooms` (automáticos + manuales), `showcase` (recorte de pantalla en grande), `camFull` (monólogo final).
Capas (requieren `"persona": "<id>/<parte>.persona.webm"` de `recortar.py`; solo partes a cámara, composición Parte):
- `tituloDetras` — titular gigante DETRÁS de la cabeza; `fondo: "depth"` cambia la sala por el fondo 3D (la persona
  flota). Cualquier escena a pantalla completa con `"capa": "detras"` queda detrás de la persona (presentador
  delante del gráfico), con halo de acento (`"halo": false` para quitarlo). Máx. 2–3 por vídeo; gráficos que el
  cuerpo no tape (titulares, cifras a un lado).
- `"entrada": "iris"` en una escena a pantalla completa: se abre en círculo desde la cara (transición sin corte).
Fondos de las escenas a pantalla completa: `"fondo": "profundidad" | "puntos" | "aurora"` en el guion (los shorts lo
heredan). Variarlo entre vídeos seguidos (historial.py). Ejemplo de anuncio completo: `videos/ejemplo/anuncio.json`.
Toda cifra de un estudio lleva su fuente en pantalla.

## 5. Estilo

3D minimalista con la paleta de `marca.json`; titulares en Instrument Serif cursiva, texto Manrope, etiquetas
JetBrains Mono. Cortes secos y punch-in alterno ≤ 9 %. SFX sutiles (sin «pops»): `<Efecto nombre alinear pan>`
— `alinear` «inicio» | «pico» (el golpe del sonido cae en el fotograma) | «fin» (una subida que termina en el
revelado); por defecto el ancla de `sonidos.json`; `pan` −1…1 (lo que entra por la izquierda suena a la izquierda).
Librería de 30 sonidos (`python pipeline/sfx_generar.py`: familias golpe/aire/tick/nota/glitch, ganancia por familia). Música: épica solo en la intro,
jazz en el resto, ~16 dB bajo la voz. Logo: isotipo al abrir, logotipo tenue al cerrar. Nunca logos encima de la
pantalla del grueso. Shorts: gancho los primeros 2,8 s (en vertical grabado, a la altura del pecho), subtítulos
palabra a palabra con la activa en acento, zona segura de las apps, cierre con `tumarca.com`.

## 6. Miniatura (Higgsfield + Remotion)

1. Fotograma nítido de la cara de esta grabación → recorte cuadrado 1024 (`out/miniatura/referencia_<id>.jpg`).
2. Higgsfield (avisar coste y saldo): `media_upload` → PUT con curl → `media_confirm`; `generate_image` con
   `params: {model: "gpt_image_2", aspect_ratio: "16:9", resolution: "2k", quality: "high", medias: [{value:
   <media_id>, role: "image"}, …], prompt}` (≈ 6,5 créditos). Boca cerrada, persona a la derecha, izquierda
   vacía y oscura, SIN texto; si hay móvil, pantalla hacia el espectador. Funciona bien: la persona señalando el
   título con un objeto relacionado desenfocado detrás.
3. Texto con Remotion: `videos/<id>/miniatura.json` {imagen, etiqueta, destacado, titulo} →
   `npx remotion still src/index.ts Miniatura ../out/miniatura/<id>_miniatura.jpg --props='{"guion":"<id>/miniatura.json"}' --image-format=jpeg --jpeg-quality=92 --scale=0.6667`.

## 7. Herramientas externas

- **Higgsfield** (conector MCP): imágenes y vídeo (B-roll, miniaturas). NO genera música.
  - **Voz ElevenLabs v4**: `generate_audio` con `model: "elevenlabs_v4"` y `dialogue: [{text, voice_id,
    voice_type: "preset"}]` (voces de `list_voices`; todas son inglesas pero hablan español nativo: Whisper lo
    detecta «es» 0,99). Etiquetas de emoción en el texto (`[excited]`, `[curious]`, `[confident]`): no se leen.
    Coste ≈ 0,46 créditos por frase corta; 43 s de locución ≈ 4 créditos. anuncio01: voz **Andre**
    (`f1e8226e-2248-4d5f-b43c-0a79e9949dbf`, enérgica).
  - **Objetos 3D**: `gpt_image_2_5` 1:1 con 6 objetos en rejilla 3×2 sobre blanco puro y sin sombras (≈ 6,5
    créditos) → recorte local con relleno desde los bordes (scipy `ndimage.label` de lo casi blanco conectado al
    borde) → PNG con alfa por objeto.
- **Música**: Biblioteca de audio de YouTube (sin atribución) → normalizada en `videos/_shared/music/`.
- **HeyGen** (conector MCP): gemelo digital, solo plan B («<look del avatar>», 25 fps, permiso previo).
- **Blotato**: no se usa; la publicación es manual.
- **Logos**: `node remotion/scripts/logos.mjs` → Simple Icons (monocromo sobre el color de la marca) + oficiales a
  color (`OFICIALES`: Lobe Icons para marcas de IA, luego SVGL, luego Lobe monocromo; si no, monograma).
  Añadir uno: `node scripts/logos.mjs oficial <slug> "<Nombre>" <#color> "<consulta>" "alias"…`.
- **Modelos locales (PyTorch cu128 en .venv)**: alineación forzada MMS_FA de torchaudio (`alinear.py`, 1,2 GB en
  la caché de torch) y Robust Video Matting (`recortar.py`, torch.hub, GPL-3.0 usado como herramienta externa).

## Entorno

- Windows 11 · i9-14900HX · RTX 4060 Laptop 8 GB · 48 GB RAM.
- Python: `.venv/` (3.13): `.venv\Scripts\python.exe pipeline\<script>.py`. ffmpeg 9 (winget Gyan.FFmpeg,
  `comun.py` lo localiza). Remotion 4 en `remotion/` (publicDir `../videos`); marca en `remotion/src/marca.ts`.
- Logos de `marca/` copiados a `videos/_shared/marca/` (Remotion solo sirve desde publicDir).

## Reglas técnicas

### Heredadas (evitar desde el principio)
- La webcam suele entrar a ~30 fps aunque OBS grabe a 60: `mpdecimate` antes de `fps=30`.
- Umbral de voz relativo al nivel de la voz (voz − 24 dB), no solo al ruido.
- Whisper a veces coloca mal palabras enteras (duración ~0 y fuera de sitio): el corte NO quita huecos con
  voz continua ≥ 0,2 s (salvo si son de una toma descartada). Comprobar palabra a palabra tras cortar.
- Palabras cortas al empezar frase salen con duración 0 y tarde: retroceder el inicio hasta 250 ms mientras haya voz.
- Fondo 3D con velocidad variable: integrar la velocidad por fotograma (nunca `camZ = t · speed`).
- Medir el pico real de cada SFX y normalizarlo; recortar su silencio inicial.
- Suscriptores en formato YouTube español: «85,6 mil», «1,23 M», nunca «K».
- `npx tsc --noEmit` antes de cada render; QA con `npx remotion still … --frame=N` de cada escena.
- Renders largos con `--hardware-acceleration=if-possible`; 4K opcional con `--scale=2`.
- Procesar siempre desde disco local. En `<DRIVE>` (Google Drive para escritorio) solo se COPIA,
  nunca se procesa: `pipeline/brutos.py traer <id>` (<DRIVE> → `raw/<id>/`, reanudable y verificado con ffprobe)
  y `pipeline/brutos.py entregar <id>` (`out/entregas/<id>/` → <DRIVE>). ffmpeg/Whisper/Remotion hacen lecturas
  aleatorias y con Drive en streaming se cuelgan; la copia lineal no. Plan B: `pipeline/drive_api.py` (API).

### Aprendidas en este proyecto
- **faster-whisper 1.2.1 + PyAV ≥ 15 no son compatibles** (`av.open(metadata_errors=…)` → TypeError).
  No pasar rutas a `model.transcribe`: decodificar con `comun.audio_16k()` (ffmpeg → float32 16 kHz) y
  pasar el array.
- **CUDA en Windows**: `comun.registrar_dll_cuda()` antes de importar faster_whisper (cuBLAS/cuDNN vienen
  de los paquetes pip `nvidia-cublas-cu12` y `nvidia-cudnn-cu12`).
- **Whisper con `condition_on_previous_text=False`**: con True, audio repetitivo provoca bucles de
  re-decodificación (una prueba de 10 min no acabó en 10 min).
- Modelo por defecto **turbo** (x11,8 tiempo real en la 4060; large-v3 x3,4, mismas palabras).
  Pasar siempre `hotwords=` con `proyecto.json › equipo.transcripcion.vocabulario`: sin él, los nombres
  propios (marca, productos) salen mal escritos.
- La VRAM (8 GB) se comparte con OBS/Chrome: cerrar OBS antes de transcribir si va lento.
- `marca.ts › formatoSuscriptores`: no quitar ceros finales cuando no hay decimales («120 mil», no «12 mil»).
- La primera ejecución de `npx remotion still` puede fallar mientras descarga Chrome Headless Shell;
  basta con repetir.
- En bash, no dejar un `cat > archivo` sin heredoc: espera stdin y cuelga el comando.
- **Ruido que roza el umbral trocea los silencios** (prueba01: «fuera» traía 2,5 s de pausa dentro y
  sobrevivía al corte, porque a 10 ms el ruido a −40 dB cruzaba el umbral de −37,6 a ratos). En
  `01_cut_silences.py`: envolvente suavizada a 30 ms, destellos < 50 ms = silencio, y voz aislada < 120 ms
  rodeada de ≥ 250 ms de silencio y lejos de bordes de palabra = silencio. El corte avisa de cualquier
  pausa > 250 ms que quede: la verificación por palabras NO la ve (no falta ni sobra texto).
- Whisper mete pausas DENTRO de palabras («fuera» de 4 s): nunca fiarse de los tiempos de palabra
  para cortar; decidir con la energía del audio.
- **Whisper se salta las repeticiones** cuando transcribe el archivo entero (prueba01: «no por el
  producto, no porque el producto, no porque el producto fuera malo» → solo la última). Sin esas palabras,
  03_tomas no puede quitarlas y el corte las conserva como «voz sin palabra». Solución en 02_transcribe:
  segunda pasada **trozo a trozo, secuencial** (el modo por lotes también se las salta) con un
  `initial_prompt` de titubeos genérico (`PROMPT_LITERAL`). Probado: estable y literal.
- **`hotwords` hace alucinar en silencios** («Telegram», «www», «Facebook»); en trozos sin voz Whisper
  también se inventa «Gracias por ver el video» / «¡Suscríbete al canal!». Por eso la pasada literal
  va sin hotwords (vocabulario dentro del prompt) y solo sustituye trozos donde la pasada completa ya
  oyó voz y el texto se parece (≥ 50 %).
- `clip_timestamps` de faster-whisper va en SEGUNDOS y sin solapes (si no, AssertionError).
- 03_tomas: regla de **reinicios** (misma palabra de arranque y ≥ 60 % de parecido en ≤ 12 palabras)
  además de tomas entre frases.
- **Finales de frase comidos** («respuest-», «promet-»): la última sílaba se dice flojo, por debajo del
  umbral. Colas con umbral suave (umbral − 7 dB, nunca a < 4 dB del ruido), salvando caídas ≤ 60 ms
  (la «t» de «promete»), como mucho 150 ms (más es reverberación de la sala) y fundido de salida de
  20 ms. El script avisa si algún corte cae sobre voz clara (mirando el fotograma exacto del corte).
- Entre una toma descartada y la buena sin pausa, cortar en el valle de energía más cercano.
- Salidas de 01_cut_silences: `<corte>.palabras_corte.json` (nunca `<corte>.palabras.json`: pisaba la
  entrada de 03_tomas).
- El móvil puede grabar con rotación (prueba01: −180°). ffmpeg la aplica al recodificar; comprobar
  siempre un fotograma del bruto antes de cortar.
- Móvil = VFR (29,92 fps de media): el corte pasa por `fps=30` y redondeo acumulado; comprobar que
  vídeo y audio tienen el mismo número de fotogramas (lo hace el script).
- **QA de Remotion**: `node remotion/scripts/qa.mjs <Composición> <id>/<parte>.json <seg> <seg>… --nombre x`
  empaqueta una vez y renderiza los fotogramas a `out/qa/` (mucho más rápido que un `remotion still`
  por fotograma). Mirar SIEMPRE los fotogramas antes del render completo.
- Fondo `Depth`: nada de rectángulos opacos de «niebla» sobre el horizonte: dejan una banda visible.
- `lineup`: con 4 fichas, alto 128 (una fila); con título, padding superior para que no lo tapen.
- Texto sobre color de marca: blanco salvo colores muy claros (luminancia > 0,62). WhatsApp va en blanco.
- Fichas de solo texto (conceptos): bloque de cristal con la tipografía de titulares; la idea que
  «gana», con `"accent": true`.
- `remotion render` con `--crf` desactiva la aceleración por hardware (aviso en consola): normal.
- Logos: `node remotion/scripts/logos.mjs` (Simple Icons + monogramas para Excel, ChatGPT, Canva,
  LinkedIn, Slack) → `videos/_shared/logos/index.json`. Añadir marca: `… logos.mjs añadir <slug> "alias"`.
  Alias bloqueados (palabras comunes): meta, drive, insta, make, x.
- SFX sintéticos: `python pipeline/sfx_generar.py` (sub_hit, tick, swell, nota, nota_mi, whoosh,
  fade_out, click, campana, tecla) + grano en `videos/_shared/fx/`.
- **Punch-in: 9 % por defecto** (preferencia del usuario tras ver prueba01: el 7 % se quedaba corto).
  Es el máximo del estilo; no subir más.
- **Sync (05_sync.py)**: envolvente de voz 300–3400 Hz a 200 Hz, ventanas de 20 s cada 10 s; el
  desfase global se busca con una ventana del CENTRO (no del principio: el móvil puede empezar después).
  Si la cámara se paró, el hueco se marca SIN CÁMARA con ventanas de 2 s y margen de 1 s hacia dentro
  (con ventanas de 1 s salen correlaciones espurias). Probado con datos sintéticos: desfase ±1 ms.
- **Palmada**: buscarla en AGUDOS (2–7 kHz), ataque contra la mediana de los 300 ms anteriores y, entre
  los ataques ≥ 15 dB, el MÁS FUERTE. El móvil empieza con ~0,8 s de silencio digital (−120 dB): poner
  suelo al nivel de ruido o el primer ruido de sala «gana» (prueba01: palmada real en 2,73 s).
- **04_grueso.py**: la cámara se corta con los mismos fotogramas del corte vía sync (con deriva);
  en tramos sin cámara sigue avanzando (Remotion oculta la esquina). Comprobado con PSNR: mismo archivo
  como pantalla y cámara → 40 dB de media; solo difiere el tramo sin cámara.
- **06_zooms.py**: la actividad de un segundo solo se une a la zona anterior si su centro está a < 20 %
  y hay ≤ 2 s quietos entre medias; si no, dos zonas lejanas se funden en una caja enorme y no hay zoom.
- `lowerThird` con fondo oscuro de marca (el cristal transparente no se lee sobre pantallas claras).
- 03_tomas: órdenes claras al editor («repetimos desde…», «vuelvo a empezar», «eso lo cortas») cuentan
  aunque la frase tenga hasta 10 palabras; se quitan ella y la frase anterior.
- **ffmpeg no aguanta un `select` con cientos de tramos** (prueba02: 330 → «Cannot allocate memory»).
  `01_cut_silences.codificar_indices()` codifica por bloques de 40 tramos (-ss + -copyts para que el
  pixelado por `t` siga valiendo), comprueba los fotogramas de cada bloque y une con concat sin recodificar.
  Regresión: mismo resultado que el método anterior (PSNR 56 dB).
- **OBS arrancó con ~6 s de silencio digital en el micro** (prueba02): la palmada solo quedó en el móvil.
  Esperar 3 s tras pulsar grabar en OBS antes de dar la palmada. La sincronización no depende de la
  palmada (usa la voz de todo el vídeo: correlación 0,91).
- Voz del micrófono USB a −30 LUFS en bruto (prueba02): subir la ganancia del micro; normalizar +14 dB sube ruido.
- **03_tomas, correcciones**: «voy a corregirlo», «empiezo nuevamente», «para la corrección del video»…
  anulan el PÁRRAFO anterior (hasta una pausa ≥ 1 s, máx. 40 s), no solo la frase anterior.
- **03_tomas, reinicios**: con habla real larga, la regla laxa cambiaba el sentido («pero no voy a
  atender» → «voy a atender»). Solo cuenta si el intento es ≤ 6 palabras, no es frase completa, hay
  titubeo (coma, «…», pausa ≥ 0,3 s o ≤ 2 palabras) y los 4 primeros tokens se parecen ≥ 70 %.
- **Pixelado**: bloques FIJOS de ~22 px (`"bloque"` por rectángulo), no proporcionales al rectángulo.
  `hojas.py --cambios 3` saca solo los fotogramas en que cambia la pantalla (48 en vez de 443).
  Para medir, fotogramas a 960 px con rejilla cada 256 px. La banda roja de aviso de la app desplaza
  todo ~120 px: medir con y sin ella. El scroll mueve los datos: usar zonas generosas por intervalo.
  Mejor aún: grabar con un tenant de demostración con datos ficticios.
- **Pixelado automático (pipeline/pixelar_auto.py)**: RapidOCR local sobre cada «estado» de pantalla
  (cambio de imagen a 4 fps) → correos, teléfonos, cédulas, números largos, fechas de nacimiento,
  «a nombre de…» y la lista `sensibles` del prep. UN solo proceso: RapidOCR ya usa casi todos los núcleos
  (6 procesos se estorbaron: 68 000 s de CPU sin terminar). ~27 min para 15 min de vídeo; el OCR se guarda
  en `grueso.ocr_cache.json` (fuera de git) y `--reclasificar` reaplica reglas en 0 s. Las fechas numéricas
  de este año o el anterior son marcas de tiempo de la app, no datos personales.
  En el scroll el OCR del estado puede no ver el dato que asoma: `anclas` del prep (rótulo → zona fija
  ± margen) y zonas manuales generosas para cabeceras. Verificar SIEMPRE con `hojas.py --cambios 2.5`.
- **Pixelado eficiente en ffmpeg**: pixelar el fotograma entero una vez + máscara (drawbox sobre
  `extractplanes=y`) + alphamerge + overlay. Con split/crop/overlay por zona, cientos de zonas no terminaban.
  OJO: `format=gray` en una rama de `split` pasa TODO el vídeo a gris (la negociación de formato es común).
- Con `-copyts`, `-t` se aplica al tiempo absoluto: limitar por `-frames:v`.
- **No escribir regex con `\b` a través de un heredoc de Python en el Bash tool**: llegaron como
  caracteres de retroceso (0x08) invisibles y la regex nunca casaba. Usar la herramienta Edit o `chr(92)`.
- Rutas de Windows en JSON/Python: usar `/` (`<DRIVE>/raw`). Con `\` dentro de un
  string Python normal, `\v`, `\r`, `\f` se convierten en caracteres de control.
- **Render del grueso = híbrido** (`pipeline/render_grueso.py`): renderizar la composición `Grueso` entera en
  Remotion iba a 1/35 del tiempo real (60 s en 35 min; con concurrency 16 fallaba por timeout de
  delayRender). La base (pantalla con zoompan + cámara en esquina/pantalla completa) la compone ffmpeg con
  NVENC y Remotion solo renderiza `GruesoGraficos` (ProRes 4444 con alfa) en los tramos con escenas.
  Los clips de gráficos se guardan en `out/render_grueso/<id>/` y se reutilizan si el tramo no cambia.
- En el montaje con ffmpeg, **solo mezclar `[k:a]` de los clips que tengan pista de audio** (comprobar con
  ffprobe): un showcase sin efecto sale sin audio y `[k:a]` hace fallar ffmpeg con EINVAL (-22).
- Si `ffmpeg` falla con `-loglevel error`, mostrar su stderr (`CalledProcessError.stderr`): el código de
  salida solo (4294967274) no dice nada.
- Un mensaje f-string con `\n` escrito por heredoc puede llegar como salto de línea real (f-string sin
  cerrar): editar con Edit.
- **Higgsfield no genera música** (solo voz; `sonilo_music` es solo para su flujo de juegos). La CLI usa los
  mismos modelos. Música = Biblioteca de audio de YouTube (sin atribución) en `videos/_shared/music/`.
- Conector Higgsfield: `generate_*` piden los argumentos dentro de `params`; `job_display` pide `id` suelto.
  Una generación fallida devuelve los créditos.
- **Música**: pistas de la Biblioteca de audio de YouTube (sin atribución) → `raw/_musica/{intro,grueso}/`;
  la elegida se normaliza a −16 LUFS (como la voz) en `videos/_shared/music/*.m4a` para que `volumen` signifique
  lo mismo con cualquier pista (intro 0,1; grueso 0,08 → ~20 dB bajo la voz). Para el grueso, antes un
  `acompressor` suave (ratio 3) que aplana subidas. Criterios: intro = fuerte desde el segundo 0 y poca energía
  en 300–3400 Hz (no tapa la voz); grueso = nivel estable (σ < 2 dB, sin saltos > 7 dB) y poca energía en la
  banda de la voz. Entrada 1–1,5 s y salida 2–3 s con fundido (Parte.tsx › Musica, render_grueso.py).
- **loudnorm `linear=true` no siempre es lineal**: si la ganancia lleva el pico por encima de TP, ffmpeg pasa
  a modo dinámico sin avisar (salvo en el JSON, `normalization_type`). prueba02: −16,2 LUFS y pico −2,5 dBTP
  → +2,2 dB dejaría el pico en −0,3. 07_final aplica la ganancia con `volume` y un `alimiter` solo para picos.
- Música más alta por preferencia del usuario (2026-10-01, «suena muy bajo»): intro 0,16 y grueso 0,13
  (~16 dB bajo la voz). Son los valores por defecto ahora.
- `copiar_reanudable` vuelve a copiar si el origen es más nuevo aunque pese lo mismo.
- Shorts: con el layout dividido la cara quedaba a la altura de la descripción de TikTok/Reels (zona tapada):
  se recorta la cámara alrededor de la cara (`focoCamara`) antes de componer. Los subtítulos en layout cámara
  van en y≈1420 (en 1240 tapaban la boca).
- **Cámara frontal del móvil = imagen en ESPEJO** (proyecto01: el nombre y el logo de la sudadera al revés). Siempre
  `hflip`: en la sesión de cámara al crearla, en 04_grueso con `"voltearCamara": true` y en el vertical.
  Comprobar con un texto en cuadro (sudadera, póster) antes de procesar.
- **Sesión de cámara en un solo archivo** (todos los bloques seguidos, claqueta «Bloque X»): móvil + OBS solo
  audio (micrófono USB) → `05_sync.py <obs> <movil>` (desfase por voz) → sesión = vídeo del móvil (hflip, fps=30) + audio
  de OBS desplazado → `02_transcribe` de la sesión → tramos por parte en `videos/<id>/partes.json` →
  `pipeline/extraer_partes.py` → cada `<parte>_bruto.mov` pasa por 02 → 03 → 01 como una intro. Partes de
  proyecto01: intro (bloques 0–1), datos (2–4), grueso (5, pantalla), cierre (6–7). Deslices que cambian el
  sentido («No por responder a tiempo») se quitan con `03_tomas --quitar`.
- **publicDir (`videos/`) LIGERO**: Remotion COPIA la carpeta entera en cada empaquetado; con ~5 GB de
  intermedios se quedaba colgado (proyecto01). Los brutos/intermedios van en `raw/<id>/partes/`; en `videos/` solo
  lo que Remotion lee (cortes finales, JSON, broll, música). render_grueso acepta rutas `../raw/...`.
- Las tareas en segundo plano del agente tienen límite de tiempo: los renders largos se lanzan como proceso
  independiente (`out/lote_<id>.cmd` con `Start-Process`, log en `out/lote_<id>.log`).
- `qa.mjs`/`laminas.mjs` con `timeoutInMilliseconds: 180000` y renders con `--timeout=180000`: el primer
  fotograma de un vídeo largo tarda en extraerse.
- Pantalla del portátil con pestañas y barra de tareas: `"recorte": {"y": 108, "alto": 1272, "rellenar":
  "0x0E1116"}` (recorta y rellena hasta 16:9 sin deformar) + pixelar la cuenta de la cabecera.
- Escenas nuevas: `bars` (barras comparativas con `fuente`), `broll` (plano de apoyo a pantalla completa, voz
  sigue) y `fuente`/`grid:false` en `revealStat`. Toda cifra de un estudio lleva su fuente en pantalla.
- B-roll con Higgsfield: Kling 3.0 std, 5 s, 16:9, `sound: off` ≈ 6,25 créditos por clip (proyecto01: 4 clips =
  25). Normalizar a 1920×1080/30 fps con GOP corto (`-g 15`) en `videos/<id>/broll/`.
- **01_cut_silences respeta la orientación**: antes forzaba 1920×1080 y a un vertical le recortaba el centro
  (proyecto01: el short salió como un primer plano de la boca). Ahora un bruto vertical sale 1080×1920.
- Shorts de un vertical grabado: el gancho va a la altura del pecho (`gancho.posicion: "abajo"`, por defecto en
  `parte: "vertical"`) para no tapar los ojos; los subtítulos se ocultan durante el rótulo de cierre.
- No escribir .cmd con `printf` desde bash (las `\` de las rutas se vuelven escapes): usar la herramienta Write.
- **Alineación forzada (alinear.py)**: Whisper dejaba ~10 % de inicios de palabra fuera de la voz (intro de proyecto01:
  inicios sobre voz 90,8 % → 99,6 % alineando). CTC marca el fin en el último carácter: alargar el fin con la
  energía (≤ 0,35 s, sin pisar la siguiente). Los números se reconocen mal (puntuación baja) pero caen en su sitio:
  aceptar palabras flojas si sus vecinas son fiables (≥ 0,5). Ventanas de ~25 s cortadas en pausas y con TODO el
  audio cubierto (un grupo con tiempos de Whisper a 0 se perdía). Palabras «fuera del corte» (≥ 3 seguidas con
  inicio = fin, de tramos quitados) no se alinean. `"al": 1/0` marca el archivo ya alineado (repetible).
- PyTorch y faster-whisper conviven en el .venv (torch 2.11 cu128 + torchvision 0.26): comprobado tras instalar.
- **Los mp4 de Remotion traen el priming del AAC como audio real**: la voz va ~45 ms TARDE respecto a la imagen
  (proyecto01: intro/datos/cierre +45 ms, grueso de ffmpeg 0; el montaje final de proyecto01 lo arrastra). 07_final y
  09_shorts lo miden contra la voz cortada (`verificar_sync.desfase_voz`) y lo recortan con `atrim`.
- `apad` sin `whole_dur` en una pasada a `-f null` no termina nunca (audio infinito): acotar siempre.
- verificar_sync: anticiparse a la palabra es estilo (hasta 0,45 s antes); llegar > 0,12 s tarde es error.
- **logos.mjs**: quitar width/height SOLO de la etiqueta `<svg>` raíz; en un `<rect>` de un clipPath recorta el
  logo entero (Canva salía vacío). Logos a color (`logoColor`) van sobre la superficie oscura, no sobre su color.
- **recortar.py**: RVM recurrente (bordes estables) a ~15 fps en 1080p (cuello: codificar VP9 con alfa); 80 s →
  2,5 min, 47 MB. Guardar el color ORIGINAL + alfa (no el `fgr` del modelo): la capa coincide píxel a píxel con la
  cámara y no hay salto al aparecer. Necesita torchvision (RVM lo importa).
- Iris: no reutilizar la curva de `useEntradaSalida` (easeOut): a los 5 fotogramas el círculo ya cubría casi todo.
- Piezas nuevas en 9:16: escala ×1,22 (`zoom`) o se ven pequeñas; la consulta del buscador puede ocupar 2 líneas.
- qa.mjs mientras corre un `remotion render` compiten por CPU/GPU: 4 fotogramas tardaron > 10 min. Esperar.
- En el Bash tool, un heredoc largo con comillas tipográficas y backticks falló al parsear (EOF inesperado):
  escribir el script en un archivo del scratchpad y ejecutarlo.
- `revealStat` con `grid: false` y sin logo = cifra sola (24/7): grande, en acento y con impacto desde el
  fotograma 0. Antes salía en blanco a 190 px y aparecía a los 16 fotogramas: en un anuncio no daba tiempo.
- Dos escenas a pantalla completa seguidas: solapar la siguiente ~0,4 s (la salida dura 16 fotogramas); si no,
  asoma la cámara entre ambas. El `outro` tarda 1,2 s en mostrar el titular: darle ≥ 3,4 s.
- **Panel3D** (anuncios): centrar con `translate(-50%, -50%)` también cuando no tiene alto fijo; anclado por arriba
  bajaba hasta la zona que tapan las apps. Con cursor que pulsa un botón, dar al panel un `alto` fijo para poder
  calcular dónde cae el botón.
- Titular cinético: las palabras de acento seguidas van en UN grupo sin salto de línea y con un solo bloque de
  color; por separado, el bloque se partía al cambiar de línea («un solo | lugar»).
- `remotion render` falló una vez al mezclar el audio («remotion-audio-mixing\0.wav: No such file or directory»,
  carpeta temporal que desaparece): es puntual; anuncio.py reintenta hasta 3 veces.
- Hoja de contactos con `fps=2/3`: no muestrea en los segundos «redondos»; un fotograma «vacío» puede ser la
  entrada de una escena. Comprobar con `-ss <t>` exacto antes de tocar nada.
