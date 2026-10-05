# Plantilla de concepto por vídeo

Claude escribe `videos/<id>/concepto.md` DESPUÉS de cortar y alinear (las palabras ya tienen tiempos exactos) y
ANTES de diseñar escenas. Sirve para que cada vídeo tenga una idea visual propia y no sea «el anterior con otro
texto». La PRIMERA línea es el concepto en una frase (historial.py la guarda).

Pasos previos:
```
python pipeline/lectura.py <id> intro           # y datos, cierre, vertical… → videos/<id>/<parte>.lectura.md
python pipeline/historial.py comparar <id>      # qué se usó en los últimos vídeos y qué conviene variar
```

---

# <Concepto en una frase: la imagen mental que deja el vídeo («el reloj que corre mientras no contestas»)>

## 1. Idea central
- Qué tiene que sentir quien lo ve (urgencia, alivio, curiosidad…) y en qué momento exacto (segundo de la parte).
- La frase que es el corazón del vídeo (de la lectura) y cómo se va a ver.

## 2. Dirección visual
- **Fondo**: profundidad | puntos | aurora — el que sugiera `historial.py` salvo que el concepto pida otro.
- **Tinte por bloques**: colores de plano de la lectura (alternar; el acento de marca para el momento clave).
- **Piezas protagonistas** (2–3, no las mismas 3 del vídeo anterior): p. ej. notificacion para el problema,
  pasos para el método, revealStat para el dato.
- **Capas**: ¿hay un momento para `tituloDetras` o una escena con `"capa": "detras"`? (requiere `recortar.py`).
  Máximo 2–3 por vídeo: es un golpe de efecto, no un recurso continuo.
- **Transiciones**: dónde un `"entrada": "iris"` sustituye a un corte seco (cambio de bloque, revelación).

## 3. Sonido
- **Música**: tema (no repetir el de los últimos vídeos) y `desde` cuadrado con `golpe_musica.py` para que un golpe
  caiga en el momento clave (`--en <segundo>`).
- **SFX**: familias que dominan (golpes para cifras, aire para transiciones, notas para revelaciones). Paneo según
  el lado por el que entra cada pieza.

## 4. Mapa de escenas (por bloque de la lectura)
| Bloque | Tiempo | Frase ancla | Pieza | Notas (acento, tinte, capa, sfx) |
|---|---|---|---|---|
| 1 | 0–8 s | «…» | notificacion | gancho; golpe de música en 2,1 s |

## 5. Qué NO hacer en este vídeo
- Lo que `historial.py comparar` marcó como repetido.
- Textos largos en tramos rápidos (> 170 pal/min según la lectura).

## 6. Verificación
- `verificar_sync.py` tras el render de cada parte: hoja de contactos revisada, ninguna escena «TARDE».
- Al entregar: `python pipeline/historial.py registrar <id>`.
