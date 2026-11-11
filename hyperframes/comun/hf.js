// Piezas comunes de las plantillas de HyperFrames (marca blanca). Lo carga cada index.html DESPUÉS de assets/datos.js
// (window.DATOS, escrito por pipeline/motor.py) y ANTES de construir su línea de tiempo.
//
// Contrato de HyperFrames que se respeta aquí:
// - Los elementos con tiempo (.clip con data-start/data-duration) los escribe motor.py en el HTML; este archivo solo
//   rellena su interior y anima hijos, nunca el .clip.
// - Una sola línea de tiempo GSAP en pausa, construida de forma síncrona; todo en segundos ABSOLUTOS del vídeo.
// - Nada de relojes, azar sin semilla, red ni temporizadores: cada cuadro sale solo del tiempo.
(function () {
  "use strict";
  const D = window.DATOS;
  const L = D.lienzo;                                  // {ancho, alto, movil, u}
  const HF = (window.HF = { D, L });
  if (L.movil) document.documentElement.classList.add("movil");
  if (D.transparente) document.documentElement.classList.add("transparente");   // 9:16: estilos .movil de hf.css

  HF.esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

  /** "Todo en *un lugar*" → [{t:"Todo",a:false}, {t:"en",a:false}, {t:"un",a:true}, {t:"lugar",a:true}] */
  HF.acentos = (texto) => {
    const res = [];
    let dentro = false;
    for (const trozo of String(texto ?? "").split("*")) {
      for (const t of trozo.split(/\s+/).filter(Boolean)) res.push({ t, a: dentro });
      dentro = !dentro;
    }
    return res;
  };
  /** Texto con *acentos* como HTML: lo acentuado en <span class="ac">. */
  HF.conAcento = (texto) => HF.acentos(texto).map((p) => (p.a ? `<span class="ac">${HF.esc(p.t)}</span>` : HF.esc(p.t))).join(" ");

  const lineasDe = (v) => (Array.isArray(v) ? v : v ? [v] : []);
  HF.lineasDe = lineasDe;

  /** Titular en bloques: palabras seguidas del mismo tipo van en UN bloque (cristal o acento), como el Callout de Remotion.
   *  Devuelve el HTML; cada palabra es un .pal con data-k = índice global (para wordsAt). */
  HF.titular = (lineas, tam) => {
    let k = 0;
    const html = lineasDe(lineas).map((linea) => {
      const grupos = [];
      for (const p of HF.acentos(linea)) {
        const g = grupos[grupos.length - 1];
        if (g && g.a === p.a) g.pals.push({ t: p.t, k: k++ });
        else grupos.push({ a: p.a, pals: [{ t: p.t, k: k++ }] });
      }
      return `<div class="linea" style="gap:${tam * 0.16}px">` + grupos.map((g) =>
        `<span class="bloque ${g.a ? "acento" : "cristal"}" style="font-size:${tam}px">` +
        g.pals.map((p, i) => `<span class="pal" data-k="${p.k}">${i ? "&nbsp;" : ""}${HF.esc(p.t)}</span>`).join("") +
        `</span>`).join("") + `</div>`;
    }).join("");
    return `<div class="titular" style="gap:${tam * 0.2}px">${html}</div>`;
  };

  /** Entrada palabra a palabra de un titular: wordsAt[k] (segundos absolutos) o escalonado desde t0. */
  HF.animarTitular = (tl, raiz, t0, wordsAt) => {
    const pals = raiz.querySelectorAll(".pal");
    pals.forEach((p, i) => {
      const k = Number(p.dataset.k);
      const t = wordsAt && wordsAt[k] !== undefined ? Math.max(wordsAt[k], t0) : t0 + 0.07 + i * 0.1;
      tl.fromTo(p, { opacity: 0, y: 26, filter: "blur(8px)" }, { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.32, ease: "power3.out" }, t);
    });
    raiz.querySelectorAll(".bloque").forEach((b) => {
      const primera = b.querySelector(".pal");
      const k = Number(primera.dataset.k);
      const t = wordsAt && wordsAt[k] !== undefined ? Math.max(wordsAt[k], t0) : t0 + 0.07 + Number(primera.dataset.k) * 0.1;
      tl.fromTo(b, { scale: 0.9, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.4, ease: "back.out(1.6)" }, t);
    });
  };

  /** Logo de la marca (isotipo / logotipo) o, si no hay archivo, el nombre en texto. */
  HF.logo = (tipo, alto) => {
    const src = D.marca.logos[tipo];
    return src ? `<img src="${src}" alt="" style="height:${alto}px">`
               : `<div class="marca-nombre" style="font-size:${alto * 0.7}px">${HF.esc(D.marca.logos.soloTexto || D.marca.nombre)}</div>`;
  };

  /** Tamaño de titular según el lienzo (en px de 1080 de lado corto). */
  HF.tam = (texto, base) => {
    const largo = lineasDe(texto).join(" ").length;
    const b = base ?? (L.movil ? 96 : largo > 36 ? 104 : 128);
    return Math.round(b * L.u);
  };

  // ─────────────────────────── escenas ───────────────────────────
  // Nombres del catálogo de Remotion (type) → tipo de HyperFrames (tipo). Así los guiones existentes sirven tal cual.
  const ALIAS = { callout: "titulo", lineup: "tarjetas", revealStat: "dato", bars: "barras", lowerThird: "lowerThird", outro: "final" };
  HF.tipoDe = (e) => ALIAS[e.tipo ?? e.type] ?? e.tipo ?? e.type;

  const contenido = (el, html, clase = "") => {
    el.innerHTML = `<div class="contenido ${clase}">${html}</div>`;
    return el.firstElementChild;
  };
  const salida = (tl, c, e) => {
    const fin = e.to - 0.02;
    tl.fromTo(c, { opacity: 1 }, { opacity: 0, y: -24, duration: 0.3, ease: "power2.in", immediateRender: false }, Math.max(e.from + 0.3, fin - 0.3));
  };
  const at = (e, clave, defecto) => (e.at && typeof e.at === "object" && e.at[clave] !== undefined ? e.at[clave] : defecto);

  HF.escenas = {
    titulo(tl, el, e) {
      const lineas = e.lines ?? e.lineas ?? e.texto ?? e.rotulo;
      const c = contenido(el, HF.titular(lineas, HF.tam(lineas, e.tam)));
      HF.animarTitular(tl, c, e.from, e.wordsAt);
      salida(tl, c, e);
    },

    lowerThird(tl, el, e) {
      const nombre = e.nombre ?? D.marca.persona.nombre, cargo = e.cargo ?? D.marca.persona.cargo;
      el.innerHTML = `<div class="lt" style="left:${L.seg.izq}px;bottom:${L.movil ? 520 : 120 * L.u}px">
        <div class="lt-barra"></div>
        <div class="lt-caja"><div class="lt-nombre">${HF.esc(nombre)}</div><div class="lt-cargo">${HF.esc(cargo)}</div></div></div>`;
      const lt = el.firstElementChild;
      tl.fromTo(lt.querySelector(".lt-barra"), { scaleY: 0 }, { scaleY: 1, duration: 0.35, ease: "power3.out" }, e.from);
      tl.fromTo(lt.querySelector(".lt-caja"), { opacity: 0, x: -40 }, { opacity: 1, x: 0, duration: 0.45, ease: "power3.out" }, e.from + 0.12);
      salida(tl, lt, e);
    },

    tarjetas(tl, el, e) {
      const titulo = e.title ?? e.titulo;
      const items = e.items ?? [];
      const c = contenido(el,
        (titulo ? `<div class="titulo-escena">${HF.conAcento(titulo)}</div>` : "") +
        `<div class="tarjetas">` + items.map((it) =>
          `<div class="tarjeta${it.accent || it.acento ? " acento" : ""}">` +
          (it.logoSrc ? `<img src="${it.logoSrc}" alt="">` : "") +
          `<span>${HF.esc(it.text ?? it.texto ?? (it.logoSrc ? "" : it.logo))}</span></div>`).join("") + `</div>`);
      if (titulo) tl.fromTo(c.querySelector(".titulo-escena"), { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.4, ease: "power3.out" }, e.from);
      c.querySelectorAll(".tarjeta").forEach((t, i) => {
        const it = items[i];
        tl.fromTo(t, { opacity: 0, y: 50, scale: 0.92 }, { opacity: 1, y: 0, scale: 1, duration: 0.45, ease: "back.out(1.5)" },
                  it.at ?? e.from + 0.2 + i * 0.18);
        // negación = gris y desenfoque (nunca tachado rojo)
        if (it.strikeAt !== undefined) tl.to(t, { opacity: 0.35, filter: "blur(4px) grayscale(1)", y: 16, duration: 0.4 }, it.strikeAt);
      });
      salida(tl, c, e);
    },

    dato(tl, el, e) {
      const display = e.display ?? (e.value !== undefined ? `${e.value} %` : "");
      const c = contenido(el,
        `<div class="cifra" style="font-size:${Math.round(300 * L.u)}px">${HF.esc(display)}</div>` +
        (e.label ? `<div class="cifra-label">${HF.conAcento(e.label)}</div>` : "") +
        (e.fuente ? `<div class="fuente">Fuente: ${HF.esc(e.fuente)}</div>` : ""));
      // cifra sola: grande y con impacto desde el primer cuadro (regla del revealStat sin grid)
      tl.fromTo(c.querySelector(".cifra"), { scale: 1.25, opacity: 0.0, filter: "blur(10px)" },
                { scale: 1, opacity: 1, filter: "blur(0px)", duration: 0.35, ease: "power4.out" }, e.from);
      if (e.label) tl.fromTo(c.querySelector(".cifra-label"), { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.4 }, e.from + 0.3);
      if (e.fuente) tl.fromTo(c.querySelector(".fuente"), { opacity: 0 }, { opacity: 1, duration: 0.4 }, e.from + 0.5);
      salida(tl, c, e);
    },

    barras(tl, el, e) {
      const titulo = e.title ?? e.titulo;
      const items = e.items ?? [];
      const c = contenido(el,
        (titulo ? `<div class="titulo-escena">${HF.conAcento(titulo)}</div>` : "") +
        `<div class="barras">` + items.map((it) =>
          `<div class="barra-fila${it.accent || it.acento ? " acento" : ""}"><div class="barra-cab"><span>${HF.esc(it.label)}</span>` +
          `<span>${HF.esc(it.display ?? `${it.value} %`)}</span></div><div class="barra-fondo"><div class="barra-relleno"></div></div></div>`).join("") +
        `</div>` + (e.fuente ? `<div class="fuente">Fuente: ${HF.esc(e.fuente)}</div>` : ""));
      if (titulo) tl.fromTo(c.querySelector(".titulo-escena"), { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.4 }, e.from);
      c.querySelectorAll(".barra-fila").forEach((f, i) => {
        const t = items[i].at ?? e.from + 0.3 + i * 0.25;
        tl.fromTo(f, { opacity: 0, x: -30 }, { opacity: 1, x: 0, duration: 0.35, ease: "power3.out" }, t);
        tl.fromTo(f.querySelector(".barra-relleno"), { scaleX: 0 }, { scaleX: Math.max(0, Math.min(items[i].value, 100)) / 100,
                  duration: 0.9, ease: "power3.out" }, t + 0.1);
      });
      if (e.fuente) tl.fromTo(c.querySelector(".fuente"), { opacity: 0 }, { opacity: 1, duration: 0.4 }, e.from + 0.6);
      salida(tl, c, e);
    },

    // ── escenas del anuncio (mismas claves que remotion/src/promo) ──
    apertura(tl, el, e) {
      const cambio = at(e, "cambio", (e.from + e.to) / 2);
      const tam = HF.tam(e.texto1, L.movil ? 110 : 120);
      el.innerHTML = `<div class="contenido"><div class="t1">${HF.titular(e.texto1, tam)}</div></div>` +
                     `<div class="contenido capa"><div class="t2">${HF.titular(e.texto2, tam)}</div></div>`;
      const [c1, c2] = el.querySelectorAll(".contenido");
      HF.animarTitular(tl, c1, e.from, at(e, "p1"));
      tl.fromTo(c1, { opacity: 1, scale: 1 }, { opacity: 0, scale: 0.94, duration: 0.2, ease: "power2.in", immediateRender: false }, cambio - 0.2);
      HF.animarTitular(tl, c2, cambio, at(e, "p2"));
      salida(tl, c2, e);
    },

    chat(tl, el, e) {
      const msgs = e.mensajes ?? [];
      const c = contenido(el,
        (e.rotulo ? `<div class="titulo-escena">${HF.conAcento(e.rotulo)}</div>` : "") +
        `<div class="chat"><div class="chat-cab"><div class="chat-av">${HF.esc(e.iniciales ?? (e.cliente ?? "?").slice(0, 2))}</div>` +
        `<div class="chat-nombre">${HF.esc(e.cliente ?? "")}</div></div>` +
        msgs.map((m) => `<div class="burbuja ${m.de === "ia" || m.de === "yo" ? "ia" : "cliente"}">${HF.esc(m.texto)}</div>`).join("") +
        (e.link ? `<div class="burbuja ia"><div><b>${HF.esc(e.link.titulo)}</b></div><div>${HF.esc(e.link.monto ?? "")}</div></div>` : "") + `</div>`);
      if (e.rotulo) tl.fromTo(c.querySelector(".titulo-escena"), { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.4 }, at(e, "rotulo", e.from));
      tl.fromTo(c.querySelector(".chat"), { opacity: 0, y: 60, rotationX: 12 }, { opacity: 1, y: 0, rotationX: 0, duration: 0.5, ease: "power3.out" }, e.from);
      c.querySelectorAll(".burbuja").forEach((b, i) => {
        const t = i < msgs.length ? msgs[i].at ?? e.from + 0.4 + i * 0.8 : e.link.at ?? e.to - 1;
        tl.fromTo(b, { opacity: 0, y: 24, scale: 0.9 }, { opacity: 1, y: 0, scale: 1, duration: 0.35, ease: "back.out(1.6)" }, t);
      });
      salida(tl, c, e);
    },

    remate(tl, el, e) {
      const tam = HF.tam(e.lineas, L.movil ? 104 : 110);
      const c = contenido(el, HF.titular(e.lineas, tam) + (e.gigante ? `<div class="gigante" style="font-size:${Math.round(340 * L.u)}px">${HF.esc(e.gigante)}</div>` : ""));
      HF.animarTitular(tl, c, e.from, at(e, "palabras"));
      if (e.gigante) tl.fromTo(c.querySelector(".gigante"), { opacity: 0, scale: 1.4 }, { opacity: 1, scale: 1, duration: 0.35, ease: "power4.out" }, at(e, "gigante", e.from + 1));
      salida(tl, c, e);
    },

    final(tl, el, e) {
      const lema = e.lema ?? e.kicker ?? e.headline;
      const boton = e.boton ?? (D.marca.sitio || "").replace(/^https?:\/\//, "");
      const c = contenido(el, `<div class="marca-final">${HF.logo(D.marca.logos.logotipo ? "logotipo" : "isotipo", Math.round(170 * L.u))}` +
        (lema ? `<div class="titulo-escena">${HF.conAcento(lema)}</div>` : "") +
        (boton ? `<div class="boton">${HF.esc(boton)}</div>` : "") + `</div>`);
      const piezas = c.querySelector(".marca-final").children;
      tl.fromTo(piezas[0], { opacity: 0, scale: 0.8 }, { opacity: 1, scale: 1, duration: 0.5, ease: "back.out(1.7)" }, e.from + 0.1);
      if (lema) tl.fromTo(c.querySelector(".titulo-escena"), { opacity: 0, y: 26 }, { opacity: 1, y: 0, duration: 0.4 }, at(e, "lema", e.from + 0.5));
      if (boton) tl.fromTo(c.querySelector(".boton"), { opacity: 0, scale: 0.8 }, { opacity: 1, scale: 1, duration: 0.4, ease: "back.out(2)" }, at(e, "boton", e.from + 0.9));
      // el final se queda en pantalla (sin salida): es el último cuadro del vídeo
    },
  };

  /** Rellena y anima cada .clip[data-escena="i"] con DATOS.escenas[i]. Tipos desconocidos con "rotulo" → titulo. */
  HF.montarEscenas = (tl) => {
    document.querySelectorAll("[data-escena]").forEach((el) => {
      const e = D.escenas[Number(el.dataset.escena)];
      const tipo = HF.tipoDe(e);
      const f = HF.escenas[tipo] ?? (e.rotulo || e.lines || e.lineas ? HF.escenas.titulo : null);
      if (f) f(tl, el, e);
    });
  };

  /** Transiciones «barrido» / «mancha»: disco que cubre el cuadro en el corte y se desvanece. */
  HF.montarTransiciones = (tl) => {
    document.querySelectorAll("[data-transicion]").forEach((el) => {
      const t = Number(el.dataset.start), x = Number(el.dataset.x) * L.ancho, y = Number(el.dataset.y) * L.alto;
      const r = Math.hypot(Math.max(x, L.ancho - x), Math.max(y, L.alto - y)) * 1.08;
      el.innerHTML = `<div class="barrido-disco ${el.dataset.transicion === "mancha" ? "mancha" : ""}"
        style="left:${x - r}px;top:${y - r}px;width:${2 * r}px;height:${2 * r}px;background:${el.dataset.color === "tinta" ? "var(--fondo)" : "var(--acento)"}"></div>`;
      const d = el.firstElementChild;
      tl.fromTo(d, { scale: 0, rotation: -20 }, { scale: 1, rotation: 0, duration: 0.3, ease: "power2.in" }, t);
      tl.fromTo(d, { opacity: 1 }, { opacity: 0, duration: 0.26, ease: "power1.out", immediateRender: false }, t + 0.3);
    });
  };

  /** Fondo de marca: manchas de acento que derivan despacio (tweens finitos, deterministas). tl = null → quieto. */
  HF.montarFondo = (tl, el, claro) => {
    if (!el) return;
    const W = L.ancho, H = L.alto, R = Math.max(W, H) * 0.42;
    const manchas = [[0.2, 0.25, "var(--acento)"], [0.8, 0.7, "var(--acento2)"], [0.55, 0.95, "var(--acento)"]];
    el.innerHTML = `<div class="capa ${claro ? "fondo-claro" : "fondo-base"}"></div>` +
      manchas.map(([x, y, c]) => `<div class="mancha" style="left:${x * W - R}px;top:${y * H - R}px;width:${2 * R}px;height:${2 * R}px;` +
                                  `background:radial-gradient(circle, color-mix(in srgb, ${c} ${claro ? 30 : 38}%, transparent) 0%, transparent 65%)"></div>`).join("") +
      `<div class="capa puntos"></div>`;
    if (tl) el.querySelectorAll(".mancha").forEach((m, i) => {
      const s = i % 2 ? -1 : 1;
      tl.fromTo(m, { x: 0, y: 0 }, { x: s * W * 0.12, y: -s * H * 0.08, duration: Math.max(1, D.duracion), ease: "sine.inOut" }, 0);
    });
  };
})();
