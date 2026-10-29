"use strict";
// Grafici: parte comune a tutte le pagine dei servizi (28/10/2026). Le regole sono in README_stile.md, sezione «Grafici».
//
//  EUGENIO_GRAFICI.registra(box, disegna, { titolo, adatta })
//    box      il contenitore del grafico nella pagina (un <div>, prende la classe .grafico)
//    disegna  funzione (destinazione, misure) che disegna l'SVG (ed eventuale legenda) dentro destinazione, vuota;
//             misure = { larghezza, altezza, riquadro }: nella pagina altezza è null e riquadro false (il grafico usa le
//             sue misure solite, o la larghezza del box se vuole adattarsi); nel riquadro sono i pixel disponibili e il
//             grafico deve usarli come viewBox, così le scritte restano della grandezza giusta
//    titolo   titolo del riquadro (se manca, l'aria-label dell'SVG)
//    adatta   true se il disegno nella pagina dipende dalla larghezza del box: si rifà quando il box cambia larghezza
//             (finestra ridimensionata o pannello allargato col divisore)
//  La funzione disegna subito il grafico e mette in alto a destra il pulsante con la freccina che lo apre nel riquadro
//  flottante: finestra modale con sfondo scurito, ✱ e ◐ come nella testata, zoom con la rotella o il pizzico,
//  trascinamento, «Vista iniziale», chiusura con ×, Esc o clic fuori.
//
//  EUGENIO_GRAFICI.osserva(svg, punti, { area, guida })
//    rende il grafico «osservabile»: passando il mouse (o toccando, o con le frecce quando l'SVG ha il fuoco) si
//    evidenzia il punto più vicino in orizzontale e compare un suggerimento.
//    punti = [{ x, titolo, righe: [[colore, testo], …], segni: [[x, y, colore], …], elementi: [rect, …] }]
//    opzioni: area = [x0, y0, x1, y1]; guida: false per non disegnare la linea verticale (grafici a sole barre)
//    x e i segni sono in coordinate dell'SVG; righe sono già formattate all'italiana; elementi (barre) prendono la
//    classe .evidenziata; area = [x0, y0, x1, y1] è la zona del disegno (per la linea guida).
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const registrati = new WeakMap();     // box → { box, disegna, opz, larghezza }

  function el(tag, attrs = {}, parent) {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) {
      if ((k === "fill" || k === "stroke") && typeof v === "string" && v.startsWith("var(")) e.style.setProperty(k, v);
      else e.setAttribute(k, v);
    }
    if (parent) parent.appendChild(e);
    return e;
  }
  function h(tag, cls, testo) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (testo !== undefined && testo !== null) e.textContent = testo;
    return e;
  }
  const limita = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
  function leggiVb(svg) {
    const v = (svg.getAttribute("viewBox") || "").split(/[\s,]+/).map(Number);
    return v.length === 4 && v.every(Number.isFinite) ? { x: v[0], y: v[1], w: v[2], h: v[3] } : null;
  }
  const scriviVb = (svg, v) => svg.setAttribute("viewBox", `${v.x} ${v.y} ${v.w} ${v.h}`);
  function puntoSvg(svg, cx, cy) {
    const m = svg.getScreenCTM();
    if (!m) return null;
    const p = new DOMPoint(cx, cy).matrixTransform(m.inverse());
    return { x: p.x, y: p.y };
  }
  function puntoSchermo(svg, x, y) {
    const m = svg.getScreenCTM();
    if (!m) return null;
    const p = new DOMPoint(x, y).matrixTransform(m);
    return { x: p.x, y: p.y };
  }

  // ------------------------------------------------------------------ suggerimento (uno solo per la pagina)
  const sugg = h("div", "grafico-suggerimento");
  sugg.setAttribute("aria-hidden", "true");
  const annuncio = h("div", "solo-lettori");          // per chi usa la tastiera con un lettore di schermo
  annuncio.setAttribute("role", "status");
  annuncio.setAttribute("aria-live", "polite");
  let spegniAttivo = null;                            // funzione che spegne il grafico evidenziato ora

  function casa(svg) { return (svg && svg.closest("dialog")) || document.body; }
  function mostraSuggerimento(svg, titolo, righe, cx, cy) {
    const c = casa(svg);
    if (sugg.parentNode !== c) c.appendChild(sugg);
    sugg.innerHTML = "";
    sugg.appendChild(h("b", null, titolo));
    for (const [colore, testo] of righe) {
      const d = h("div");
      const q = h("i");
      if (colore) q.style.background = colore; else q.className = "vuoto";
      d.append(q, testo);
      sugg.appendChild(d);
    }
    sugg.style.display = "block";
    const w = sugg.offsetWidth, hh = sugg.offsetHeight, m = 14;
    let x = cx + m, y = cy + m;
    if (x + w > innerWidth - 4) x = cx - m - w;
    if (y + hh > innerHeight - 4) y = cy - m - hh;
    sugg.style.left = `${Math.max(4, x)}px`;
    sugg.style.top = `${Math.max(4, y)}px`;
  }
  function nascondiSuggerimento() {
    sugg.style.display = "none";
    if (spegniAttivo) { const f = spegniAttivo; spegniAttivo = null; f(); }
  }
  // un tocco fuori dal grafico evidenziato spegne il suggerimento
  document.addEventListener("pointerdown", (e) => {
    if (spegniAttivo && !(e.target.closest && e.target.closest("svg.osservabile"))) nascondiSuggerimento();
  }, true);
  addEventListener("scroll", () => { if (spegniAttivo) nascondiSuggerimento(); }, { passive: true, capture: true });

  // ------------------------------------------------------------------ grafici osservabili
  function osserva(svg, punti, opz = {}) {
    punti = (punti || []).filter((p) => p && Number.isFinite(p.x) && p.righe && p.righe.length).sort((a, b) => a.x - b.x);
    if (!punti.length) return;
    const vb = leggiVb(svg) || { x: 0, y: 0, w: 100, h: 100 };
    const area = opz.area || [vb.x, vb.y, vb.x + vb.w, vb.y + vb.h];
    // margine laterale oltre il primo e l'ultimo punto: metà della distanza media tra i punti
    const meta = punti.length > 1 ? (punti[punti.length - 1].x - punti[0].x) / (punti.length - 1) / 2 : (area[2] - area[0]) / 2;
    const strato = el("g", { class: "osserva", "aria-hidden": "true" }, svg);
    const conGuida = opz.guida !== false;     // { guida: false } nei grafici a sole barre: basta la barra evidenziata
    const guida = el("line", { class: "guida", x1: 0, x2: 0, y1: area[1], y2: area[3], visibility: "hidden" }, strato);
    const segni = el("g", {}, strato);
    let attivo = -1;
    svg.classList.add("osservabile");
    if (!svg.hasAttribute("tabindex")) svg.setAttribute("tabindex", "0");

    function vicino(x) {
      let lo = 0, hi = punti.length - 1;
      while (hi - lo > 1) { const m = (lo + hi) >> 1; if (punti[m].x < x) lo = m; else hi = m; }
      return Math.abs(punti[lo].x - x) <= Math.abs(punti[hi].x - x) ? lo : hi;
    }
    function dentro(p) {
      return p && p.x >= area[0] - meta && p.x <= area[2] + meta && p.y >= area[1] - 8 && p.y <= area[3] + 8;
    }
    function spegni() {
      attivo = -1;
      guida.setAttribute("visibility", "hidden");
      segni.innerHTML = "";
      svg.querySelectorAll(".evidenziata").forEach((e) => e.classList.remove("evidenziata"));
    }
    function accendi(i, cx, cy) {
      const p = punti[i];
      if (spegniAttivo && spegniAttivo !== spegni) nascondiSuggerimento();
      if (i !== attivo) {
        spegni();
        attivo = i;
        if (conGuida) { guida.setAttribute("x1", p.x); guida.setAttribute("x2", p.x); guida.setAttribute("visibility", "visible"); }
        // raggio dei segni costante sullo schermo anche col grafico ingrandito nel riquadro
        const r = svg.getBoundingClientRect(), v = leggiVb(svg) || vb;
        const scala = r.width ? v.w / r.width : 1;
        for (const [x, y, colore] of p.segni || []) {
          el("circle", { cx: x, cy: y, r: 5 * scala, fill: colore || "var(--inchiostro)", stroke: "var(--foglio)", "stroke-width": 2 * scala }, segni);
        }
        (p.elementi || []).forEach((e) => e && e.classList.add("evidenziata"));
      }
      if (cx === undefined) {          // dalla tastiera: accanto al punto
        const y = p.segni && p.segni.length ? Math.min(...p.segni.map((s) => s[1])) : area[1];
        const s = puntoSchermo(svg, p.x, y) || { x: 0, y: 0 };
        cx = s.x; cy = s.y;
      }
      mostraSuggerimento(svg, p.titolo, p.righe, cx, cy);
      spegniAttivo = spegni;
    }

    svg.addEventListener("pointermove", (e) => {
      if (e.pointerType === "touch") return;              // col dito vale il tocco (click)
      if (e.buttons || svg.classList.contains("trascina")) { if (attivo >= 0) nascondiSuggerimento(); return; }
      const p = puntoSvg(svg, e.clientX, e.clientY);
      if (!dentro(p)) { if (attivo >= 0) nascondiSuggerimento(); return; }
      accendi(vicino(p.x), e.clientX, e.clientY);
    });
    svg.addEventListener("pointerleave", (e) => { if (e.pointerType !== "touch" && attivo >= 0) nascondiSuggerimento(); });
    svg.addEventListener("click", (e) => {
      if (svg.__trascinato) { svg.__trascinato = false; return; }
      const p = puntoSvg(svg, e.clientX, e.clientY);
      if (dentro(p)) accendi(vicino(p.x), e.clientX, e.clientY);
      else if (attivo >= 0) nascondiSuggerimento();
    });
    svg.addEventListener("keydown", (e) => {
      let i = attivo;
      switch (e.key) {
        case "ArrowRight": i = i < 0 ? 0 : Math.min(punti.length - 1, i + 1); break;
        case "ArrowLeft": i = i < 0 ? punti.length - 1 : Math.max(0, i - 1); break;
        case "Home": i = 0; break;
        case "End": i = punti.length - 1; break;
        default: return;
      }
      e.preventDefault();
      accendi(i);
      annuncio.textContent = `${punti[i].titolo}: ${punti[i].righe.map((r) => r[1]).join("; ")}`;
    });
    svg.addEventListener("blur", () => { if (attivo >= 0) nascondiSuggerimento(); });
  }

  // ------------------------------------------------------------------ registrazione dei grafici della pagina
  const ICONA_APRI = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M14 4h6v6M20 4l-8 8M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';

  function disegnaNellaPagina(reg) {
    const box = reg.box;
    if (spegniAttivo && box.contains(sugg)) nascondiSuggerimento();
    box.innerHTML = "";
    box.classList.add("grafico", "con-riquadro");
    reg.larghezza = box.clientWidth;
    reg.disegna(box, { larghezza: box.clientWidth || null, altezza: null, riquadro: false });
    if (!box.querySelector("svg")) return;               // niente da disegnare (per esempio nessun dato)
    const b = h("button", "grafico-apri");
    b.type = "button";
    b.innerHTML = ICONA_APRI;
    b.setAttribute("aria-label", "Apri il grafico in un riquadro");
    b.title = "Apri il grafico in un riquadro";
    b.setAttribute("aria-haspopup", "dialog");
    b.addEventListener("click", () => apri(reg));
    box.prepend(b);
  }

  function registra(box, disegna, opz = {}) {
    if (!box) return null;
    let reg = registrati.get(box);
    if (!reg) {
      reg = { box };
      registrati.set(box, reg);
      if ("ResizeObserver" in window) {
        let attesa = 0;
        new ResizeObserver(() => {
          if (!reg.opz.adatta || Math.abs(box.clientWidth - (reg.larghezza || 0)) < 8 || !box.clientWidth) return;
          cancelAnimationFrame(attesa);
          attesa = requestAnimationFrame(() => disegnaNellaPagina(reg));
        }).observe(box);
      }
    }
    reg.disegna = disegna;
    reg.opz = opz;
    disegnaNellaPagina(reg);
    if (riq && riq.reg && riq.reg.box === box && riq.dialogo.open) disegnaNelRiquadro(false);
    return { ridisegna: () => disegnaNellaPagina(reg) };
  }

  // ------------------------------------------------------------------ riquadro flottante
  let riq = null;    // { dialogo, corpo, titolo, reg, svg, vb0, misure }

  function copiaComandiAspetto(dove) {
    const A = window.EUGENIO_ASPETTO;
    if (!A) return;
    const v = document.querySelector(".testata-menu .vestito");
    if (v) {
      const c = v.cloneNode(true);
      const ul = c.querySelector(".vestito-elenco"), b = c.querySelector(".vestito-pulsante");
      ul.id = "vestiti-riquadro";
      ul.hidden = true;
      ul.querySelectorAll('[role="option"]').forEach((o) => { o.id = `vestiti-riquadro-${o.dataset.vestito}`; o.classList.remove("attiva"); });
      ul.removeAttribute("aria-activedescendant");
      if (b) { b.setAttribute("aria-controls", ul.id); b.setAttribute("aria-expanded", "false"); }
      dove.appendChild(c);
      A.collegaVestito(c);
    }
    const t = document.querySelector(".testata-menu .tema");
    if (t) {
      const c = t.cloneNode(true);
      dove.appendChild(c);
      A.collegaTema(c);
    }
  }

  function creaRiquadro() {
    const d = h("dialog", "riquadro-grafico");
    d.setAttribute("aria-labelledby", "riquadro-titolo");
    const fin = h("div", "riquadro-finestra");
    const testa = h("div", "riquadro-testa");
    const titolo = h("h2", "riquadro-titolo"); titolo.id = "riquadro-titolo";
    const comandi = h("div", "riquadro-comandi");
    const vista = h("button", "riquadro-vista");
    vista.type = "button";
    vista.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 12a8 8 0 1 0 2.4-5.7M4 4v4.5h4.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg><span>Vista iniziale</span>';
    vista.title = "Torna alla vista iniziale (tasto 0)";
    const chiudi = h("button", "riquadro-chiudi");
    chiudi.type = "button";
    chiudi.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>';
    chiudi.setAttribute("aria-label", "Chiudi il riquadro");
    chiudi.title = "Chiudi (Esc)";
    comandi.appendChild(vista);
    copiaComandiAspetto(comandi);
    comandi.appendChild(chiudi);
    testa.append(titolo, comandi);
    const corpo = h("div", "riquadro-corpo grafico");
    const aiuto = h("p", "riquadro-aiuto", AIUTO_GRAFICO);
    fin.append(testa, corpo, aiuto);
    d.appendChild(fin);
    document.body.appendChild(d);
    riq = { dialogo: d, corpo, titolo, reg: null, svg: null, vb0: null, aiuto, finestra: fin, tabella: null };

    vista.addEventListener("click", () => vistaIniziale());
    chiudi.addEventListener("click", () => d.close());
    // clic fuori dalla finestra (sullo sfondo scurito): chiude; solo se anche la pressione è iniziata fuori
    let premutoFuori = false;
    d.addEventListener("pointerdown", (e) => { premutoFuori = e.target === d; });
    d.addEventListener("click", (e) => { if (e.target === d && premutoFuori) d.close(); premutoFuori = false; });
    // Esc dentro l'elenco dei vestiti chiude solo l'elenco
    let escElenco = false;
    d.addEventListener("keydown", (e) => {
      if (e.key === "Escape") escElenco = !!e.target.closest(".vestito-elenco") || e.defaultPrevented;
      if (e.target.closest(".vestito-elenco")) return;
      if (e.key === "+" || e.key === "=") { e.preventDefault(); zoomCentro(1.25); }
      else if (e.key === "-" || e.key === "_") { e.preventDefault(); zoomCentro(0.8); }
      else if (e.key === "0") { e.preventDefault(); vistaIniziale(); }
    }, true);
    d.addEventListener("cancel", (e) => { if (escElenco) e.preventDefault(); escElenco = false; });
    d.addEventListener("close", () => {
      nascondiSuggerimento();
      rimettiTabella();                 // la tabella torna al suo posto nella pagina prima di svuotare il riquadro
      corpo.innerHTML = "";
      riq.svg = null;
      riq.reg = null;
      document.documentElement.classList.remove("riquadro-aperto");
    });
    if ("ResizeObserver" in window) {
      let attesa = 0, ultima = "";
      new ResizeObserver(() => {
        if (!d.open || !riq.reg) return;
        const m = `${corpo.clientWidth}x${corpo.clientHeight}`;
        if (m === ultima) return;
        ultima = m;
        cancelAnimationFrame(attesa);
        attesa = requestAnimationFrame(() => disegnaNelRiquadro(false));
      }).observe(corpo);
    } else addEventListener("resize", () => d.open && disegnaNelRiquadro(false));
    zoomETrascinamento(corpo);
    document.addEventListener("eugenio:aspetto", () => { if (d.open && riq.reg) disegnaNelRiquadro(true); });
  }

  function apri(reg) {
    if (!riq) creaRiquadro();
    modoGrafico();
    riq.reg = reg;
    const svg = reg.box.querySelector("svg:not(.grafico-apri svg)");
    riq.titolo.textContent = reg.opz.titolo || (svg && svg.getAttribute("aria-label")) || "Grafico";
    document.documentElement.classList.add("riquadro-aperto");
    riq.dialogo.showModal();
    disegnaNelRiquadro(false);
    const chiudi = riq.dialogo.querySelector(".riquadro-chiudi");
    if (chiudi) chiudi.focus();
  }

  // disegna il grafico con le misure del corpo del riquadro; conserva = tieni lo zoom attuale (cambio di colori)
  function disegnaNelRiquadro(conserva) {
    const { corpo, reg } = riq;
    if (!reg) return;
    const vbPrima = conserva && riq.svg ? leggiVb(riq.svg) : null, misurePrima = riq.misure;
    nascondiSuggerimento();
    corpo.innerHTML = "";
    corpo.style.overflow = "hidden";
    const W = Math.max(200, Math.floor(corpo.clientWidth)), H = Math.max(160, Math.floor(corpo.clientHeight));
    reg.disegna(corpo, { larghezza: W, altezza: H, riquadro: true });
    let svg = corpo.querySelector("svg");
    if (!svg) return;
    // legenda e note sotto il grafico: secondo passaggio con l'altezza che resta
    const resto = corpo.scrollHeight - svg.getBoundingClientRect().height;
    if (resto > 2) {
      corpo.innerHTML = "";
      reg.disegna(corpo, { larghezza: W, altezza: Math.max(160, H - resto - 2), riquadro: true });
      svg = corpo.querySelector("svg");
    }
    corpo.style.overflow = "";
    svg.classList.add("nel-riquadro");
    riq.svg = svg;
    riq.vb0 = leggiVb(svg);
    riq.misure = `${W}x${H}`;
    if (vbPrima && misurePrima === riq.misure) scriviVb(svg, vbPrima);
  }

  function vistaIniziale() { if (riq && riq.svg && riq.vb0) { nascondiSuggerimento(); scriviVb(riq.svg, riq.vb0); } }

  // ------------------------------------------------------------------ zoom (viewBox) e trascinamento nel riquadro
  const ZOOM_MAX = 12;
  function correggi(v) {
    const v0 = riq.vb0;
    v.w = limita(v.w, v0.w / ZOOM_MAX, v0.w);
    v.h = v.w * v0.h / v0.w;
    v.x = limita(v.x, v0.x, v0.x + v0.w - v.w);
    v.y = limita(v.y, v0.y, v0.y + v0.h - v.h);
    return v;
  }
  function zoomIn(fattore, cx, cy) {
    const svg = riq.svg, v = svg && leggiVb(svg);
    if (!v) return;
    const p = puntoSvg(svg, cx, cy);
    if (!p) return;
    const w = limita(v.w / fattore, riq.vb0.w / ZOOM_MAX, riq.vb0.w), k = w / v.w;
    scriviVb(svg, correggi({ x: p.x - (p.x - v.x) * k, y: p.y - (p.y - v.y) * k, w, h: v.h * k }));
    if (spegniAttivo) nascondiSuggerimento();
  }
  function zoomCentro(fattore) {
    if (!riq || !riq.svg) return;
    const r = riq.svg.getBoundingClientRect();
    zoomIn(fattore, r.left + r.width / 2, r.top + r.height / 2);
  }
  function zoomETrascinamento(corpo) {
    corpo.addEventListener("wheel", (e) => {
      if (!riq.svg || !riq.svg.contains(e.target)) return;
      e.preventDefault();
      const d = e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 400 : 1);
      zoomIn(Math.exp(-d * 0.0015), e.clientX, e.clientY);
    }, { passive: false });
    const dita = new Map();     // puntatori premuti: id → { x, y }
    let inizio = null;          // { vb, x, y } per il trascinamento, { vb, d, cx, cy } per il pizzico
    const avvia = () => {
      const svg = riq.svg, vb = leggiVb(svg), p = [...dita.values()];
      if (p.length === 1) inizio = { vb, x: p[0].x, y: p[0].y, mosso: false };
      else if (p.length >= 2) {
        const cx = (p[0].x + p[1].x) / 2, cy = (p[0].y + p[1].y) / 2;
        inizio = { vb, d: Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y) || 1, centro: puntoSvg(svg, cx, cy), cx, cy, mosso: true };
      }
    };
    corpo.addEventListener("pointerdown", (e) => {
      const svg = riq.svg;
      if (!svg || !svg.contains(e.target) || (e.pointerType === "mouse" && e.button !== 0)) return;
      dita.set(e.pointerId, { x: e.clientX, y: e.clientY });
      try { svg.setPointerCapture(e.pointerId); } catch (err) { /* puntatore già rilasciato */ }
      avvia();
    });
    corpo.addEventListener("pointermove", (e) => {
      const svg = riq.svg;
      if (!svg || !dita.has(e.pointerId) || !inizio) return;
      dita.set(e.pointerId, { x: e.clientX, y: e.clientY });
      const r = svg.getBoundingClientRect(), p = [...dita.values()], v0 = inizio.vb;
      if (p.length === 1) {
        const dx = e.clientX - inizio.x, dy = e.clientY - inizio.y;
        if (!inizio.mosso && Math.hypot(dx, dy) < 4) return;
        inizio.mosso = true;
        svg.__trascinato = true;
        svg.classList.add("trascina");
        if (spegniAttivo) nascondiSuggerimento();
        scriviVb(svg, correggi({ x: v0.x - dx * v0.w / r.width, y: v0.y - dy * v0.h / r.height, w: v0.w, h: v0.h }));
      } else if (p.length >= 2 && inizio.centro) {
        const d = Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y) || 1;
        const w = limita(v0.w * inizio.d / d, riq.vb0.w / ZOOM_MAX, riq.vb0.w), k = w / v0.w;
        const cx = (p[0].x + p[1].x) / 2, cy = (p[0].y + p[1].y) / 2;
        // il punto sotto le dita resta sotto le dita
        const fx = (cx - r.left) / r.width, fy = (cy - r.top) / r.height;
        svg.__trascinato = true;
        if (spegniAttivo) nascondiSuggerimento();
        scriviVb(svg, correggi({ x: inizio.centro.x - fx * w, y: inizio.centro.y - fy * v0.h * k, w, h: v0.h * k }));
      }
    });
    const fine = (e) => {
      if (!dita.has(e.pointerId)) return;
      dita.delete(e.pointerId);
      if (riq.svg) riq.svg.classList.remove("trascina");
      if (dita.size) avvia(); else inizio = null;
    };
    corpo.addEventListener("pointerup", fine);
    corpo.addEventListener("pointercancel", fine);
    corpo.addEventListener("dblclick", (e) => { if (riq.svg && riq.svg.contains(e.target)) { e.preventDefault(); vistaIniziale(); } });
  }

  // ------------------------------------------------------------------ tabelle nel riquadro (29/10/2026)
  // Ogni tabella dei dati (i contenitori .tabella-scorre e gli elementi con data-riquadro-tabella, anche quelli creati
  // dopo dagli script) ha in alto a destra lo stesso pulsante con la freccina dei grafici: apre la tabella nel riquadro
  // flottante, larga quanto le serve se sta nella finestra (altrimenti il 95 % della finestra, con scorrimento interno)
  // e alta al massimo il 95 % della finestra; ✱ e ◐ come per i grafici. La tabella vera si sposta nel riquadro e torna
  // al suo posto alla chiusura, così caselle e pulsanti continuano a funzionare. Titolo: data-titolo, <caption> o il
  // titolo (h2, h3) che la precede.
  const AIUTO_GRAFICO = "Rotella del mouse o due dita per ingrandire, trascina per spostarti; passa sopra il grafico o toccalo per leggere i valori.";
  const AIUTO_TABELLA = "Scorri la tabella se non sta tutta nella finestra; chiudi con ×, con Esc o con un clic fuori.";
  function modoGrafico() {
    rimettiTabella();
    riq.dialogo.classList.remove("con-tabella");
    riq.finestra.style.width = ""; riq.finestra.style.height = "";
    riq.aiuto.textContent = AIUTO_GRAFICO;
  }
  function rimettiTabella() {
    const t = riq && riq.tabella;
    if (!t) return;
    t.box.style.width = "";
    t.segnaposto.replaceWith(t.box);
    riq.tabella = null;
  }
  function titoloTabella(box) {
    if (box.dataset.titolo) return box.dataset.titolo;
    const cap = box.querySelector("caption");
    if (cap && cap.textContent.trim()) return cap.textContent.trim();
    const pulito = (t) => { const c = t.cloneNode(true); c.querySelectorAll(".n").forEach((n) => n.remove()); return c.textContent.trim(); };
    // il titolo (h2 o h3) più vicino che precede la tabella, risalendo fino al passo o alla sezione
    for (let e = box; e && !e.matches(".pannello, main, body"); e = e.parentElement) {
      for (let p = e.previousElementSibling; p; p = p.previousElementSibling) {
        if (/^H[23]$/.test(p.tagName)) return pulito(p);
        const dentro = p.querySelectorAll ? p.querySelectorAll("h2, h3") : [];
        if (dentro.length) return pulito(dentro[dentro.length - 1]);
      }
    }
    return "Tabella";
  }
  function dimensionaTabella() {
    const { box } = riq.tabella, fin = riq.finestra;
    const max = Math.floor(innerWidth * 0.95);
    fin.style.width = `${max}px`;
    box.style.width = "max-content";
    const cs = getComputedStyle(fin);
    const extra = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight) + parseFloat(cs.borderLeftWidth) + parseFloat(cs.borderRightWidth);
    const naturale = Math.ceil(box.getBoundingClientRect().width) + extra + 2;
    box.style.width = "";
    fin.style.width = `${Math.min(max, Math.max(360, naturale))}px`;
  }
  function apriTabella(box) {
    if (!riq) creaRiquadro();
    if (riq.dialogo.open) riq.dialogo.close();
    modoGrafico();
    nascondiSuggerimento();
    riq.reg = null; riq.svg = null;
    const segnaposto = h("div", "tabella-segnaposto");
    segnaposto.style.height = `${box.offsetHeight}px`;
    box.replaceWith(segnaposto);
    riq.tabella = { box, segnaposto };
    riq.corpo.innerHTML = "";
    riq.corpo.appendChild(box);
    riq.dialogo.classList.add("con-tabella");
    riq.titolo.textContent = titoloTabella(box);
    riq.aiuto.textContent = AIUTO_TABELLA;
    document.documentElement.classList.add("riquadro-aperto");
    riq.dialogo.showModal();
    dimensionaTabella();
    const chiudi = riq.dialogo.querySelector(".riquadro-chiudi");
    if (chiudi) chiudi.focus();
  }
  function registraTabella(box) {
    if (!box || box.dataset.riquadroPronto || box.closest("dialog")) return;
    box.dataset.riquadroPronto = "1";
    if (!box.dataset.titolo) box.dataset.titolo = titoloTabella(box);
    const contenitore = h("div", "tabella-con-riquadro");
    box.before(contenitore);
    contenitore.appendChild(box);
    const b = h("button", "grafico-apri");
    b.type = "button";
    b.innerHTML = ICONA_APRI;
    b.setAttribute("aria-label", "Apri la tabella in un riquadro");
    b.title = "Apri la tabella in un riquadro";
    b.setAttribute("aria-haspopup", "dialog");
    b.addEventListener("click", () => apriTabella(box));
    contenitore.prepend(b);
  }
  function cercaTabelle(radice) {
    (radice || document).querySelectorAll(".tabella-scorre, [data-riquadro-tabella]").forEach((x) => {
      if (x.closest("[data-riquadro-tabella]") !== x && x.closest("[data-riquadro-tabella]")) return;   // già dentro un contenitore registrato
      registraTabella(x);
    });
  }
  addEventListener("resize", () => { if (riq && riq.tabella && riq.dialogo.open) dimensionaTabella(); });
  const avviaTabelle = () => {
    cercaTabelle(document);
    let attesa = 0;
    new MutationObserver(() => { cancelAnimationFrame(attesa); attesa = requestAnimationFrame(() => cercaTabelle(document)); })
      .observe(document.body, { childList: true, subtree: true });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", avviaTabelle); else avviaTabelle();

  document.body.appendChild(annuncio);
  window.EUGENIO_GRAFICI = { registra, osserva, registraTabella, chiudiRiquadro: () => riq && riq.dialogo.open && riq.dialogo.close() };
})();
