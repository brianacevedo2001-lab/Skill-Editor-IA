# Plantilla de guiones por proyecto

Claude escribe `videos/<id>/guiones.md` con esta estructura a partir de la información del vídeo horizontal
(tema, puntos clave, demo, datos). el usuario los revisa y graba. Español latino neutro, tuteo, frases cortas,
sin prometer lo que el producto no cumple. Una idea por pieza.

## 1. Intro horizontal (50–90 s, a cámara)
1. **Gancho** (≤ 8 s): una escena concreta o un dato que duela. Nada de «hola, hoy vamos a…».
2. **Tensión**: qué se pierde si no se resuelve.
3. **Promesa**: qué va a aprender en el vídeo (concreta, medible).
4. **Credencial** breve (quién soy y por qué me importa) — 1 frase.
5. **Puente** al contenido: «Te lo enseño en la pantalla».
Marcar con *asteriscos* las palabras que deben salir en grande (callouts) y las marcas que se nombran (logos).

## 2. Vertical (30–60 s, móvil en vertical, mirando a la lente)
1. **Gancho 0–2 s**: frase que pare el scroll (pregunta incómoda, número, contradicción). También va escrito
   en pantalla (`gancho` en shorts.json, 2 líneas: la 1.ª ≤ 12 letras en MAYÚSCULAS).
2. **Problema** (5–10 s) en palabras del cliente.
3. **Idea / truco** (15–30 s): UNA sola, con ejemplo concreto.
4. **Prueba**: dato, captura o resultado.
5. **Cierre** (3–5 s): llamada a la acción simple («guárdalo», «comenta X», «video completo en YouTube»).
Ritmo: frases de ≤ 12 palabras, sin introducciones; se graba de un tirón y los fallos se repiten (se cortan solos).

## 3. Textos por red (mismo vertical, textos distintos)
- **YouTube Shorts**: título ≤ 60 caracteres con la promesa + #Shorts; descripción de 1–2 frases + enlace al canal.
- **Instagram Reels**: primera línea gancho (se corta a ~125 caracteres), 3–5 líneas cortas, llamada a guardar o
  compartir, «link en la bio», 5 hashtags de nicho. Sin música en el archivo (se añade en la app).
- **TikTok**: 1–2 frases coloquiales con pregunta al público + 4–5 hashtags. Sin música en el archivo.
- **LinkedIn (vídeo 4:5)**: tono profesional, aprendizaje o caso, pregunta final, 3 hashtags.

## 4. LinkedIn — post de texto (acompaña al carrusel o a la imagen)
1. Línea 1: gancho (≤ 140 caracteres, se ve antes de «ver más»).
2. Historia o contexto personal (2–4 líneas cortas, una idea por línea).
3. Aprendizaje / idea central.
4. Pregunta a la audiencia.
5. Enlace al vídeo completo + 3–5 hashtags.

## 5. LinkedIn — carrusel (6–8 láminas, `videos/<id>/linkedin.json`)
1. **portada**: kicker de serie + promesa con *acento* (≤ 8 palabras) + subtítulo.
2–6. **idea** (numeradas) o **dato** (valor grande): un titular ≤ 6 palabras + texto ≤ 25 palabras, logo si se nombra marca.
7. **cierre**: pregunta o conclusión + `cta` («Video completo en YouTube»).
**imagen** suelta: la idea más fuerte en una lámina tipo portada.
