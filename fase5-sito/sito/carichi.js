"use strict";
// Statistiche › «Carichi elettrici» (carichi.html, 20/11/2026, richiesta di Paolo; sperimentale).
// Pagina a tutta larghezza, senza mappa grande. (22/11/2026 b, Paolo) Sotto il titolo la pagina è divisa in due metà
// (divisore.js, ognuna con la sua barra di scorrimento) con le stesse scelte e gli stessi grafici, per confrontare due zone
// o due periodi: creaLato(0) e creaLato(1); la metà destra la copia copiaMeta() dalla sinistra (identificativi «-2»).
// Zona: casella a discesa di ogni metà (Italia e le sette zone) o piccola mappa accanto al titolo, una sola (zone al posto
// delle regioni; dati/mappa/zone.json, costruito da costruisci_zone.py): il clic su una zona la sceglie in tutte e due le
// metà, un secondo clic torna all'Italia; le zone delle due metà sono evidenziate con due stili spiegati sotto la mappa.
// Periodo: due date (predefinito gli ultimi 12 mesi), «Ultimi 12 mesi», anno intero (menu e «‹ ›»); casella «Quarti
// d'ora» (senza: ore, media dei quattro quarti d'ora).
// Grafici (SVG disegnato a ogni vista, con percorsi aggregati per pixel: decine di migliaia di quarti d'ora restano
// leggeri):
//   1. profilo giornaliero: per ogni quarto d'ora (o ora) del giorno minimo, media e massimo della potenza richiesta;
//   2. curva di durata: le potenze del periodo dalla più alta alla più bassa;
//   3. potenza per fonte in MW, aree impilate per quarto d'ora (o ora), solo Italia (Terna non pubblica la produzione per
//      zona), con le caselle per accendere e spegnere le fonti (22/11/2026);
//   4. fonti: barre al 100 % per quarto d'ora (o ora), solo Italia; le fonti spente restano al loro posto, color sfondo.
// I grafici 3 e 4 hanno la stessa vista (gruppo st.finestra): pulsanti «Ieri» … «Ultimo anno», «Tutto il periodo» e
// cursore «Sposta di un mese» sopra il grafico 3 (22/11/2026, richiesta di Paolo), su tutto l'archivio (22/11/2026 b):
// quando la finestra esce dal periodo, il periodo si sposta. I tratti senza dati sono tratteggiati («dati mancanti»).
// Ogni grafico si ingrandisce con la rotella e si sposta trascinando (asse orizzontale) nella pagina e nel riquadro
// grande di grafici.js (svg.__zoomProprio: grafici.js gli passa rotella, tasti e «Vista iniziale").
// Dati: dati/carichi/indice.json, carico_AAAA-MM.json, fonti_AAAA-MM.json (fase 15, elettricita/carichi.py, costruiti
// dal worker con i dati di Terna). Decisione di Paolo (20/11/2026): i dati non si scaricano.
// Le scelte stanno nell'indirizzo: ?zona=NORD&da=AAAA-MM-GG&a=AAAA-MM-GG&passo=60&finestra=AAAA-MM-GG_AAAA-MM-GG&spente=fv,eol
// e per la metà destra gli stessi con «2» (zona2, da2, …) (history.replaceState; finestra e spente dal 22/11/2026, solo se
// diverse dal predefinito); il riquadro
// «Collegamento a questa simulazione» in fondo alla pagina lo mostra e lo copia (collegamento.js).
// (21/11/2026, Paolo) all'apertura: ultimi 12 mesi che finiscono all'ultimo giorno con i dati, già scritti nelle caselle
// Dal/al, e quarti d'ora accesi. I valori predefiniti non vanno nell'indirizzo (Italia = niente zona, quarti d'ora =
// niente passo; passo=15 dei collegamenti già salvati vale ancora). Senza dati restano solo il titolo e il messaggio.
(function () {
  const $ = (id) => document.getElementById(id);
  const G = window.EUGENIO_GRAFICI, E = window.EUGENIO;
  const V = (document.currentScript && /[?&]v=([\w-]+)/.exec(document.currentScript.src) || [])[1] || "";
  const conV = (u) => (V ? `${u}?v=${V}` : u);
  const CARTELLA = "dati/carichi/";
  const NS = "http://www.w3.org/2000/svg";
  const ORA = 3600000, GIORNO = 86400000, Q = 900000;
  function h(tag, cls, t) { const e = document.createElement(tag); if (cls) e.className = cls; if (t !== undefined && t !== null) e.textContent = t; return e; }
  function s(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if ((k === "fill" || k === "stroke") && typeof v === "string" && v.startsWith("var(")) e.style.setProperty(k, v); else e.setAttribute(k, v);
    }
    if (parent) parent.appendChild(e);
    return e;
  }
  // numeri all'italiana, sempre con il punto delle migliaia (anche a 4 cifre: 4.063): modulo comune numeri.js
  const num = (v, d = 0) => EUGENIO_NUMERI.formato(v, d);
  const MW = (v) => `${num(v)} MW`;
  const pc = (v) => `${num(v, v < 10 ? 1 : 0)} %`;
  const limita = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
  const COLORE_ZONA = { NORD: "03", CNOR: "09", CSUD: "12", SUD: "16", CALA: "18", SICI: "19", SARD: "20" };

  // dati comuni alle due metà (indice, mesi, file già letti); ogni metà ha il suo stato (creaLato)
  const D = { ix: null, mesi: [], file: new Map(), lati: [], pronto: false, percorsi: null };
  // dati non disponibili: via comandi, piccola mappa e metà (titoli senza grafici), resta il messaggio
  function senzaDati(t) {
    const m = $("stato-carichi"); m.textContent = t; m.classList.add("errore");
    const meta = $("carichi-meta");
    if (meta) meta.after(m);
    document.querySelectorAll(".comandi-carichi, .carichi-sezione, #minimappa-zone, .minimappa-con-legenda, #carichi-meta, .carichi-due-meta-nota").forEach((e) => { e.hidden = true; });
  }

  // ------------------------------------------------------------------ tempo (ora italiana)
  // fuso di un istante (minuti dall'UTC) dai cambi d'ora scritti nell'indice; fuori dai mesi, con Intl
  const fmtFuso = new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Rome", hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
  function fusoIntl(ms) {
    const p = Object.fromEntries(fmtFuso.formatToParts(new Date(ms)).map((x) => [x.type, x.value]));
    return Math.round((Date.UTC(+p.year, p.month - 1, +p.day, +p.hour, +p.minute) - Math.floor(ms / 60000) * 60000) / 60000);
  }
  function fuso(ms) {
    const M = D.mesi;
    let lo = 0, hi = M.length - 1;
    if (!M.length || ms < M[0].t0 || ms >= M[hi].t0 + M[hi].n * Q) return fusoIntl(ms);
    while (lo < hi) { const m = (lo + hi + 1) >> 1; if (M[m].t0 <= ms) lo = m; else hi = m - 1; }
    const i = Math.floor((ms - M[lo].t0) / Q);
    let off = M[lo].ora_legale[0][1];
    for (const [k, o] of M[lo].ora_legale) if (k <= i) off = o;
    return off;
  }
  const locale = (ms) => new Date(ms + fuso(ms) * 60000);          // campi UTC = ora italiana
  const due = (n) => String(n).padStart(2, "0");
  const MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"];
  const dataIso = (ms) => { const d = locale(ms); return `${d.getUTCFullYear()}-${due(d.getUTCMonth() + 1)}-${due(d.getUTCDate())}`; };
  const dataBreve = (ms) => { const d = locale(ms); return `${d.getUTCDate()} ${MESI[d.getUTCMonth()]} ${d.getUTCFullYear()}`; };
  const oraBreve = (ms) => { const d = locale(ms); return `${due(d.getUTCHours())}:${due(d.getUTCMinutes())}`; };
  // mezzanotte italiana del giorno AAAA-MM-GG, in ms UTC
  function mezzanotte(iso) {
    const [y, m, d] = iso.split("-").map(Number), g = Date.UTC(y, m - 1, d);
    let t = g - 60 * 60000;
    t = g - fuso(t) * 60000;
    return g - fuso(t) * 60000;
  }
  const giornoDopo = (iso) => { const [y, m, d] = iso.split("-").map(Number); const x = new Date(Date.UTC(y, m - 1, d + 1)); return x.toISOString().slice(0, 10); };

  // ------------------------------------------------------------------ dati
  async function json(u) { const r = await fetch(conV(CARTELLA + u)); if (!r.ok) throw new Error(`${u}: ${r.status}`); return r.json(); }
  function file(nome) { if (!D.file.has(nome)) D.file.set(nome, json(nome).catch((e) => { D.file.delete(nome); throw e; })); return D.file.get(nome); }
  // ------------------------------------------------------------------ grafici con zoom proprio (asse orizzontale)
  // grafico(box, cfg): cfg.dominio() → [x0, x1]; cfg.disegna(g, v) disegna il contenuto della vista v = { x0, x1, X, Xi,
  // area, W, H }; cfg.punto(x, v) → { titolo, righe, segni: [[xSvg, ySvg, colore]] } per il suggerimento; cfg.legenda(dest).
  // La vista è comune alla pagina e al riquadro: ogni cambio ridisegna tutte le copie del grafico.
  const sugg = h("div", "grafico-suggerimento");
  sugg.setAttribute("aria-hidden", "true");
  function mostraSugg(svg, p, cx, cy) {
    const casa = svg.closest("dialog") || document.body;
    if (sugg.parentNode !== casa) casa.appendChild(sugg);
    sugg.innerHTML = "";
    sugg.appendChild(h("b", null, p.titolo));
    for (const [c, t] of p.righe) { const d = h("div"), q = h("i"); if (c) q.style.background = c; else q.className = "vuoto"; d.append(q, t); sugg.appendChild(d); }
    sugg.style.display = "block";
    const w = sugg.offsetWidth, hh = sugg.offsetHeight;
    let x = cx + 14, y = cy + 14;
    if (x + w > innerWidth - 4) x = cx - 14 - w;
    if (y + hh > innerHeight - 4) y = cy - 14 - hh;
    sugg.style.left = `${Math.max(4, x)}px`; sugg.style.top = `${Math.max(4, y)}px`;
  }
  const nascondiSugg = () => { sugg.style.display = "none"; document.querySelectorAll(".carichi-cursore").forEach((g) => g.replaceChildren()); };
  addEventListener("scroll", nascondiSugg, { passive: true, capture: true });

  // cfg.gruppo = { vista, grafici: [], suCambio() }: grafici con la stessa vista (i due delle fonti, 22/11/2026): zoom,
  // trascinamento, tasti e doppio clic in uno spostano anche gli altri; suCambio() dopo ogni cambio della vista.
  function grafico(box, cfg) {
    const gr = { cfg, copie: new Set() };
    const gruppo = cfg.gruppo || null;
    let propria = null;
    Object.defineProperty(gr, "vista", { get: () => (gruppo ? gruppo.vista : propria), set: (x) => { if (gruppo) gruppo.vista = x; else propria = x; } });
    if (gruppo) gruppo.grafici.push(gr);
    gr.dominio = () => cfg.dominio();
    gr.reset = () => { gr.vista = null; aggiorna(); };
    function vista() { const d = gr.dominio(); return gr.vista || d; }
    function imposta(a, b) {
      const [d0, d1] = gr.dominio(), min = cfg.minimo ? cfg.minimo() : (d1 - d0) / 2000;
      let w = limita(b - a, min, d1 - d0);
      let x0 = limita(a, d0, d1 - w);
      gr.vista = Math.abs(w - (d1 - d0)) < 1e-9 && x0 === d0 ? null : [x0, x0 + w];
      aggiorna();
    }
    gr.aggiornaCopie = () => { for (const c of [...gr.copie]) { if (!c.svg.isConnected) gr.copie.delete(c); else c.disegna(); } };
    function aggiorna() {
      for (const g of gruppo ? gruppo.grafici : [gr]) g.aggiornaCopie();
      if (gruppo && gruppo.suCambio) gruppo.suCambio();
    }
    gr.imposta = imposta;
    gr.zoom = (f, xData) => { const [a, b] = vista(); const x = xData === undefined ? (a + b) / 2 : xData; imposta(x - (x - a) / f, x + (b - x) / f); };
    gr.monta = (dest, mis) => {
      const W = Math.max(280, (mis && mis.larghezza) || box.clientWidth || 720);
      const H = mis && mis.riquadro ? mis.altezza : Math.round(limita(W * 0.4, 230, 340));
      const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": cfg.titolo(), class: "zoom-proprio", tabindex: "0" }, dest);
      const sx = W < 480 ? 48 : 60, dx = 10, su = 18, gi = 26, area = [sx, su, W - dx, H - gi];
      const id = `taglio-${Math.random().toString(36).slice(2, 9)}`;
      s("rect", { x: area[0], y: area[1] - 2, width: area[2] - area[0], height: area[3] - area[1] + 2 }, s("clipPath", { id }, s("defs", {}, svg)));
      const fondo = s("g", {}, svg), corpo = s("g", { "clip-path": `url(#${id})` }, svg), assi = s("g", {}, svg), cursore = s("g", { class: "carichi-cursore" }, svg);
      const copia = { svg, cursore };
      let vs = null;
      copia.disegna = () => {
        const [x0, x1] = vista();
        const X = (x) => area[0] + (x - x0) / (x1 - x0) * (area[2] - area[0]);
        const Xi = (px) => x0 + (px - area[0]) / (area[2] - area[0]) * (x1 - x0);
        vs = { x0, x1, X, Xi, area, W, H, fondo, corpo, assi, zoom: !!gr.vista };
        fondo.replaceChildren(); corpo.replaceChildren(); assi.replaceChildren(); cursore.replaceChildren();
        cfg.disegna(vs);
        svg.classList.toggle("ingrandito", !!gr.vista);
      };
      gr.copie.add(copia);
      copia.disegna();
      if (cfg.legenda) cfg.legenda(dest);
      // ---- coordinate
      const pxSvg = (e) => { const m = svg.getScreenCTM(); if (!m) return null; const p = new DOMPoint(e.clientX, e.clientY).matrixTransform(m.inverse()); return p; };
      const pxPerUnita = () => { const r = svg.getBoundingClientRect(); return r.width / W; };
      // ---- suggerimento
      let attivo = null;
      function accendi(xData, cx, cy) {
        const p = cfg.punto(xData, vs);
        cursore.replaceChildren();
        if (!p) { sugg.style.display = "none"; attivo = null; return; }
        attivo = xData;
        const xs = vs.X(p.x !== undefined ? p.x : xData);
        s("line", { class: "guida", x1: xs, x2: xs, y1: area[1], y2: area[3] }, cursore);
        const k = 1 / (pxPerUnita() || 1);
        for (const [x, y, c] of p.segni || []) s("circle", { cx: vs.X(x), cy: y, r: 4.5 * k, fill: c || "var(--inchiostro)", stroke: "var(--foglio)", "stroke-width": 1.5 * k }, cursore);
        if (cx === undefined) { const r = svg.getBoundingClientRect(); cx = r.left + xs * pxPerUnita(); cy = r.top + area[1] * pxPerUnita(); }
        mostraSugg(svg, p, cx, cy);
      }
      // ---- rotella, trascinamento, pizzico, doppio clic
      svg.addEventListener("wheel", (e) => {
        const p = pxSvg(e); if (!p) return;
        e.preventDefault(); e.stopPropagation();
        const d = e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 400 : 1);
        nascondiSugg();
        gr.zoom(Math.exp(-d * 0.0015), vs.Xi(limita(p.x, area[0], area[2])));
      }, { passive: false });
      const dita = new Map();
      let inizio = null;
      const avvia = () => {
        const q = [...dita.values()], v = vista();
        if (q.length === 1) inizio = { v, x: q[0].x, mosso: false };
        else if (q.length >= 2) inizio = { v, d: Math.abs(q[0].x - q[1].x) || 1, c: (q[0].x + q[1].x) / 2, mosso: true };
      };
      svg.addEventListener("pointerdown", (e) => {
        if (e.pointerType === "mouse" && e.button !== 0) return;
        e.stopPropagation();
        dita.set(e.pointerId, { x: e.clientX, y: e.clientY });
        if (e.pointerType !== "touch" || dita.size > 1) try { svg.setPointerCapture(e.pointerId); } catch (err) { /* già rilasciato */ }
        avvia();
      });
      svg.addEventListener("pointermove", (e) => {
        if (dita.has(e.pointerId) && inizio) {
          dita.set(e.pointerId, { x: e.clientX, y: e.clientY });
          const q = [...dita.values()], u = pxPerUnita(), [a, b] = inizio.v, scala = (b - a) / ((area[2] - area[0]) * u);
          if (q.length === 1) {
            const dxp = e.clientX - inizio.x;
            if (!inizio.mosso && Math.abs(dxp) < 4) return;
            inizio.mosso = true; svg.classList.add("trascina"); nascondiSugg();
            imposta(a - dxp * scala, b - dxp * scala);
          } else if (q.length >= 2) {
            const d = Math.abs(q[0].x - q[1].x) || 1, r = svg.getBoundingClientRect();
            const xc = a + ((inizio.c - r.left) / u - area[0]) * (b - a) / (area[2] - area[0]);
            const f = d / inizio.d; nascondiSugg();
            imposta(xc - (xc - a) / f, xc + (b - xc) / f);
          }
          return;
        }
        if (e.pointerType === "touch") return;
        const p = pxSvg(e);
        if (!p || p.x < area[0] - 4 || p.x > area[2] + 4 || p.y < area[1] - 8 || p.y > area[3] + 8) { if (attivo !== null) { nascondiSugg(); attivo = null; } return; }
        accendi(vs.Xi(limita(p.x, area[0], area[2])), e.clientX, e.clientY);
      });
      const fine = (e) => {
        if (!dita.has(e.pointerId)) return;
        const tocco = inizio && !inizio.mosso && dita.size === 1;
        dita.delete(e.pointerId); svg.classList.remove("trascina");
        if (tocco) { const p = pxSvg(e); if (p && p.x >= area[0] && p.x <= area[2]) accendi(vs.Xi(p.x), e.clientX, e.clientY); }
        if (dita.size) avvia(); else inizio = null;
      };
      svg.addEventListener("pointerup", fine);
      svg.addEventListener("pointercancel", fine);
      svg.addEventListener("pointerleave", (e) => { if (e.pointerType !== "touch" && !dita.size) { nascondiSugg(); attivo = null; } });
      svg.addEventListener("dblclick", (e) => { e.preventDefault(); e.stopPropagation(); nascondiSugg(); gr.reset(); });
      svg.addEventListener("keydown", (e) => {
        if (e.defaultPrevented) return;          // + − 0 nel riquadro: li gestisce grafici.js (e li passa a __zoomProprio)
        const [a, b] = vista(), passo = cfg.passoTasti ? cfg.passoTasti() : (b - a) / 50;
        let x = attivo === null ? (a + b) / 2 : attivo;
        switch (e.key) {
          case "ArrowRight": x = Math.min(b, x + passo); break;
          case "ArrowLeft": x = Math.max(a, x - passo); break;
          case "Home": x = a; break;
          case "End": x = b; break;
          case "+": case "=": gr.zoom(1.25, attivo === null ? undefined : attivo); e.preventDefault(); return;
          case "-": case "_": gr.zoom(0.8, attivo === null ? undefined : attivo); e.preventDefault(); return;
          case "0": gr.reset(); e.preventDefault(); return;
          default: return;
        }
        e.preventDefault(); e.stopPropagation();
        accendi(x);
        const p = cfg.punto(x, vs);
        if (p) annuncio.textContent = `${p.titolo}: ${p.righe.map((r) => r[1]).join("; ")}`;
      });
      svg.addEventListener("blur", () => { nascondiSugg(); attivo = null; });
      // per il riquadro di grafici.js: rotella, + − 0 e «Vista iniziale» passano da qui
      svg.__zoomProprio = {
        zoom: (f, cx) => { const r = svg.getBoundingClientRect(); const px = cx === undefined ? undefined : vs.Xi(limita((cx - r.left) / pxPerUnita(), area[0], area[2])); gr.zoom(f, px); },
        vistaIniziale: () => gr.reset(),
      };
    };
    G.registra(box, (dest, mis) => gr.monta(dest, mis), { titolo: cfg.titolo(), adatta: true });
    gr.ridisegna = () => G.registra(box, (dest, mis) => gr.monta(dest, mis), { titolo: cfg.titolo(), adatta: true });
    return gr;
  }
  const annuncio = h("div", "solo-lettori");
  annuncio.setAttribute("role", "status"); annuncio.setAttribute("aria-live", "polite");
  document.body.appendChild(annuncio);

  // assi
  function scala(max) {
    const p = 10 ** Math.floor(Math.log10(max || 1)), passo = [1, 2, 2.5, 5, 10].map((k) => k * p).find((k) => max / k <= 5) || p * 10;
    return { passo, top: Math.ceil(max / passo) * passo || 1 };
  }
  // asseY(v, top, unita, fmt, bot): da bot (0 se manca) a top; con il grafico ingrandito bot può essere più alto di 0
  function asseY(v, top, unita, fmt = num, bot = 0) {
    const { area, fondo, assi } = v, Y = (y) => area[3] - (area[3] - area[1]) * (y - bot) / (top - bot || 1), { passo } = scala(top - bot);
    for (let y = Math.ceil(bot / passo) * passo; y <= top + 1e-9; y += passo) {
      const base = Math.abs(y - bot) < 1e-9;
      s("line", { x1: area[0], x2: area[2], y1: Y(y), y2: Y(y), stroke: base ? "var(--inchiostro)" : "var(--linea)", "stroke-width": base ? 1 : 0.6 }, fondo);
      s("text", { x: area[0] - 5, y: Y(y) + 4, "text-anchor": "end" }, assi).textContent = fmt(y);
    }
    s("text", { x: 4, y: 12 }, assi).textContent = unita;
    return Y;
  }
  function asseX(v, ticks) {
    const { area, assi, fondo } = v;
    for (const [x, t, forte] of ticks) {
      const px = v.X(x);
      if (px < area[0] - 0.5 || px > area[2] + 0.5) continue;
      s("line", { x1: px, x2: px, y1: area[1], y2: area[3], stroke: "var(--linea)", "stroke-width": forte ? 0.8 : 0.4 }, fondo);
      s("text", { x: px, y: area[3] + 16, "text-anchor": "middle" }, assi).textContent = t;
    }
  }
  // intervallo verticale: da 0 nella vista intera; ingrandito, attorno ai valori visibili
  function intervallo(v, mn, mx) {
    if (!v.zoom || !Number.isFinite(mn)) return [0, scala(mx * 1.04 || 1).top];
    const marg = Math.max(1, (mx - mn) * 0.08), { passo } = scala(Math.max(1, mx - mn + 2 * marg));
    return [Math.max(0, Math.floor((mn - marg) / passo) * passo), Math.ceil((mx + marg) / passo) * passo];
  }
  // tacche dell'asse dei tempi, in ora italiana
  function tackeTempo(x0, x1, largo) {
    const max = Math.max(2, Math.floor(largo / 56)), span = x1 - x0;   // (22/11/2026) 56 px: una settimana col telefono ha le date
    const passi = [[15 * 60000, "m"], [30 * 60000, "m"], [ORA, "h"], [3 * ORA, "h"], [6 * ORA, "h"], [12 * ORA, "h"], [GIORNO, "g"], [2 * GIORNO, "g"], [3 * GIORNO, "g"],
      [7 * GIORNO, "g"], [14 * GIORNO, "g"], [1, "M"], [2, "M"], [3, "M"], [6, "M"], [12, "M"]];
    const [p, tipo] = passi.find(([q, t]) => (t === "M" ? span / (q * 30.4 * GIORNO) : span / q) <= max) || [12, "M"];
    const out = [];
    if (tipo === "M") {
      const d = locale(x0); let y = d.getUTCFullYear(), m = d.getUTCMonth();
      m = Math.ceil(m / p) * p;
      for (let k = 0; k < 400; k++) {
        const yy = y + Math.floor(m / 12), mm = m % 12, t = mezzanotte(`${yy}-${due(mm + 1)}-01`);
        if (t > x1) break;
        if (t >= x0) out.push([t, mm === 0 ? String(yy) : MESI[mm], mm === 0]);
        m += p;
      }
      return out;
    }
    // giorni e ore: allineati alla mezzanotte italiana
    let t = mezzanotte(dataIso(x0));
    if (tipo === "g") {
      for (let k = 0; k < 400 && t <= x1; k++) {
        const d = locale(t);
        const giorno = Math.round((Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()) / GIORNO));
        if (t >= x0 && giorno % (p / GIORNO) === 0) out.push([t, `${d.getUTCDate()} ${MESI[d.getUTCMonth()]}`, d.getUTCDate() === 1]);
        t = mezzanotte(giornoDopo(dataIso(t + ORA)));
      }
      return out;
    }
    for (let k = 0; k < 2000 && t <= x1; k++, t += p) {
      if (t < x0) continue;
      const d = locale(t), mezzo = d.getUTCHours() === 0 && d.getUTCMinutes() === 0;
      out.push([t, mezzo ? `${d.getUTCDate()} ${MESI[d.getUTCMonth()]}` : oraBreve(t), mezzo]);
    }
    return out;
  }

  function cerca(T, x) { let lo = 0, hi = T.length; while (lo < hi) { const m = (lo + hi) >> 1; if (T[m] < x) lo = m + 1; else hi = m; } return lo; }
  const oraDelGiorno = (o) => { const m = Math.round(o * 60); return `${due(Math.floor(m / 60))}:${due(m % 60)}`; };
  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || "#888";
  function voce(colore, testo, tipo) {
    const sp = h("span"), i = h("i", tipo === "linea" || tipo === "linea tratto" ? `linea ${tipo === "linea tratto" ? "tratto" : ""}` : "");
    if (tipo === "fascia") { i.style.background = colore; i.style.opacity = ".35"; } else if (tipo && tipo.startsWith("linea")) i.style.color = colore; else i.style.background = colore;
    sp.append(i, testo); return sp;
  }
  // giorno AAAA-MM-GG spostato di k mesi indietro (giorno del mese tenuto, o l'ultimo del mese se non c'è; k < 0 = avanti)
  function mesiIndietro(iso, k) {
    const [y, m, d] = iso.split("-").map(Number), fine = new Date(Date.UTC(y, m - 1 - k + 1, 0)).getUTCDate();
    return new Date(Date.UTC(y, m - 1 - k, Math.min(d, fine))).toISOString().slice(0, 10);
  }
  const giorniIndietro = (iso, k) => { const [y, m, d] = iso.split("-").map(Number); return new Date(Date.UTC(y, m - 1, d - k)).toISOString().slice(0, 10); };
  const giorniTra = (a, b) => Math.round((Date.UTC(...b.split("-").map((x, i) => +x - (i === 1))) - Date.UTC(...a.split("-").map((x, i) => +x - (i === 1)))) / GIORNO);
  const aMezzanotte = (t) => { const d = locale(t); return d.getUTCHours() === 0 && d.getUTCMinutes() === 0; };
  function testoFinestra(a, b) {
    const ini = aMezzanotte(a) ? dataBreve(a) : `${dataBreve(a)}, ${oraBreve(a)}`;
    const fin = aMezzanotte(b) ? dataBreve(b - 1) : `${dataBreve(b)}, ${oraBreve(b)}`;
    return ini === fin ? ini : `dal ${ini} al ${fin}`;
  }
  function leggiFinestra(t) {
    const m = /^(\d{4}-\d\d-\d\d)(?:T(\d\d)(\d\d))?_(\d{4}-\d\d-\d\d)(?:T(\d\d)(\d\d))?$/.exec(t || "");
    if (!m) return null;
    const a = mezzanotte(m[1]) + (m[2] ? (+m[2] * 60 + +m[3]) * 60000 : 0);
    const b = m[5] ? mezzanotte(m[4]) + (+m[5] * 60 + +m[6]) * 60000 : mezzanotte(giornoDopo(m[4]));
    return Number.isFinite(a) && Number.isFinite(b) && b > a ? [a, b] : null;
  }
  const SFONDO = "var(--sfondo-grafico, var(--carta))";
  const rettangolo = (x, larg, y0, y1) => `M${x.toFixed(2)},${y1.toFixed(2)}h${larg.toFixed(2)}V${y0.toFixed(2)}h${(-larg).toFixed(2)}z`;
  const nomeLegenda = (q) => (q.id === "saldo" ? "saldo con l'estero, pompaggi e accumuli (quando positivo)" : q.nome);


  // ================================================================== una metà della pagina
  // (22/11/2026, Paolo) la pagina è divisa in due metà con le loro scelte e i loro grafici: k = 0 (sinistra, identificativi
  // di sempre, parametri ?zona=&da=…) e k = 1 (destra, identificativi con «-2», parametri ?zona2=&da2=…). Dentro, «st» è
  // lo stato della metà (con ix, mesi, primo e ultimo giorno comuni) e «$» trova gli elementi della metà.
  function creaLato(k) {
    const suf = k ? "-2" : "", P = k ? "2" : "";
    const $ = (id) => document.getElementById(id + suf);
    const st = { k, P, zona: "ITA", da: null, a: null, passo: 15, giro: 0, serie: null, grafici: {}, spente: new Set(),
      get ix() { return D.ix; }, get mesi() { return D.mesi; }, get primoGiorno() { return D.primoGiorno; },
      get ultimoGiorno() { return D.ultimoGiorno; }, get passoFonti60() { return D.passoFonti60; }, get pronto() { return D.pronto; } };
    const radice = $("carichi-lato");
    function stato(t, errore = false) { const m = $("stato-carichi"); m.textContent = t; m.classList.toggle("errore", errore); }


  // serie del periodo: istanti, potenza della zona e fonti dell'Italia, al passo scelto
  async function serie() {
    const T0 = mezzanotte(st.da), T1 = mezzanotte(giornoDopo(st.a));
    const mesi = st.mesi.filter((m) => m.t0 < T1 && m.t0 + m.n * Q > T0);
    const caricati = await Promise.all(mesi.map((m) => Promise.all([file(`carico_${m.mese}.json`),
      m.fonti ? file(`fonti_${m.mese}.json`).catch(() => null) : Promise.resolve(null)])));
    const voci = st.ix.voci.map((v) => v.id);
    let n = 0;
    const pezzi = mesi.map((m, j) => {
      const i0 = Math.max(0, Math.ceil((T0 - m.t0) / Q)), i1 = Math.min(m.n, Math.floor((T1 - m.t0) / Q));
      n += Math.max(0, i1 - i0);
      return { m, i0, i1, car: caricati[j][0].zone[st.zona] || [], carIt: caricati[j][0].zone.ITA || [], fon: caricati[j][1] && caricati[j][1].voci };
    });
    const T = new Float64Array(n), L = new Float32Array(n).fill(NaN), LI = new Float32Array(n).fill(NaN), F = {};
    voci.forEach((k) => { F[k] = new Float32Array(n).fill(NaN); });
    let p = 0;
    for (const { m, i0, i1, car, carIt, fon } of pezzi) {
      for (let i = i0; i < i1; i++, p++) {
        T[p] = m.t0 + i * Q;
        const v = car[i]; if (v !== null && v !== undefined) L[p] = v;
        const w = carIt[i]; if (w !== null && w !== undefined) LI[p] = w;
        if (fon) for (const k of voci) { const x = fon[k] && fon[k][i]; if (x !== null && x !== undefined) F[k][p] = x; }
      }
    }
    return st.passo === 60 ? orarie(T, L, LI, F, voci) : { T, L, LI, F, passo: 15 };
  }
  // ore: media dei quarti d'ora con un valore (i mesi iniziano a mezzanotte italiana, cioè a un'ora piena UTC)
  function orarie(T, L, LI, F, voci) {
    const n = T.length, out = [];
    for (let i = 0; i < n;) {
      const ora = Math.floor(T[i] / ORA); let j = i;
      while (j < n && Math.floor(T[j] / ORA) === ora) j++;
      out.push([i, j]); i = j;
    }
    const m = out.length, T2 = new Float64Array(m), L2 = new Float32Array(m), LI2 = new Float32Array(m), F2 = {};
    const media = (a, i, j) => { let t = 0, c = 0; for (let k = i; k < j; k++) if (!Number.isNaN(a[k])) { t += a[k]; c++; } return c ? t / c : NaN; };
    voci.forEach((k) => { F2[k] = new Float32Array(m); });
    out.forEach(([i, j], q) => {
      T2[q] = Math.floor(T[i] / ORA) * ORA; L2[q] = media(L, i, j); LI2[q] = media(LI, i, j);
      for (const k of voci) F2[k][q] = media(F[k], i, j);
    });
    return { T: T2, L: L2, LI: LI2, F: F2, passo: 60 };
  }

  // ------------------------------------------------------------------ elaborazioni
  function profilo(S) {
    const K = 1440 / S.passo, mn = new Array(K).fill(Infinity), mx = new Array(K).fill(-Infinity), tot = new Array(K).fill(0), c = new Array(K).fill(0);
    const tmin = new Array(K).fill(null), tmax = new Array(K).fill(null);
    for (let i = 0; i < S.T.length; i++) {
      const v = S.L[i]; if (Number.isNaN(v)) continue;
      const t = S.T[i], k = Math.floor((((t + fuso(t) * 60000) % GIORNO) + GIORNO) % GIORNO / (S.passo * 60000));
      if (v < mn[k]) { mn[k] = v; tmin[k] = t; }
      if (v > mx[k]) { mx[k] = v; tmax[k] = t; }
      tot[k] += v; c[k]++;
    }
    return { K, passo: S.passo, mn, mx, media: tot.map((x, k) => (c[k] ? x / c[k] : NaN)), c, tmin, tmax };
  }
  function durata(S) {
    const v = Array.from(S.L).filter((x) => !Number.isNaN(x));
    return Float32Array.from(v.sort((a, b) => b - a));
  }
  function riepilogo(S) {
    let mx = -Infinity, mn = Infinity, tmx = null, tmn = null, tot = 0, c = 0, ren = 0, cRen = 0, carRen = 0;
    const R = ["bio", "idro", "geo", "eol", "fv"];
    for (let i = 0; i < S.T.length; i++) {
      const v = S.L[i]; if (Number.isNaN(v)) continue;
      c++; tot += v;
      if (v > mx) { mx = v; tmx = S.T[i]; }
      if (v < mn) { mn = v; tmn = S.T[i]; }
    }
    if (st.zona === "ITA") for (let i = 0; i < S.T.length; i++) {
      if (Number.isNaN(S.L[i]) || R.some((k) => Number.isNaN(S.F[k][i]))) continue;
      ren += R.reduce((t, k) => t + S.F[k][i], 0); carRen += S.L[i]; cRen++;
    }
    return { c, n: S.T.length, mx, mn, tmx, tmn, media: c ? tot / c : NaN, energia: tot * S.passo / 60, quotaRen: cRen ? 100 * ren / carRen : null };
  }
  // ------------------------------------------------------------------ grafico 1: profilo giornaliero
  function cfgProfilo() {
    return {
      titolo: () => `Profilo giornaliero della potenza richiesta – ${nomeZona()} – ${periodoTesto()}`,
      dominio: () => [0, 24],
      minimo: () => 1,
      passoTasti: () => st.passo / 60,
      disegna(v) {
        const P = st.prof; if (!P) return;
        const w = st.passo / 60, xc = (k) => k * w + w / 2;
        let top = 0, bot = Infinity;
        for (let k = 0; k < P.K; k++) if (xc(k) >= v.x0 - w && xc(k) <= v.x1 + w && P.c[k]) { top = Math.max(top, P.mx[k]); bot = Math.min(bot, P.mn[k]); }
        const [y0, y1] = intervallo(v, bot, top);
        const Y = asseY(v, y1, "MW", num, y0);
        const quante = Math.max(3, (v.area[2] - v.area[0]) / 55);
        const passoOre = [0.25, 0.5, 1, 2, 3, 6].find((p) => (v.x1 - v.x0) / p <= quante) || 6;
        const tk = [];
        for (let o = Math.ceil(v.x0 / passoOre - 1e-9) * passoOre; o <= v.x1 + 1e-9; o += passoOre) tk.push([o, oraDelGiorno(o), Math.abs(o % 6) < 1e-9]);
        asseX(v, tk);
        const ok = [...Array(P.K).keys()].filter((k) => P.c[k]);
        if (!ok.length) return;
        const banda = ok.map((k) => `${v.X(xc(k)).toFixed(1)},${Y(P.mx[k]).toFixed(1)}`).concat(ok.slice().reverse().map((k) => `${v.X(xc(k)).toFixed(1)},${Y(P.mn[k]).toFixed(1)}`));
        s("polygon", { points: banda.join(" "), fill: "var(--primario)", "fill-opacity": 0.22 }, v.corpo);
        const linea = (arr, attrs) => s("polyline", { points: ok.map((k) => `${v.X(xc(k)).toFixed(1)},${Y(arr[k]).toFixed(1)}`).join(" "), fill: "none", ...attrs }, v.corpo);
        linea(P.mx, { stroke: "var(--primario)", "stroke-width": 1.2 });
        linea(P.mn, { stroke: "var(--primario)", "stroke-width": 1.2, "stroke-dasharray": "4 3" });
        linea(P.media, { stroke: "var(--inchiostro)", "stroke-width": 2 });
        v.Y = Y;
      },
      punto(x, v) {
        const P = st.prof; if (!P || !v.Y) return null;
        const w = st.passo / 60, k = limita(Math.floor(x / w), 0, P.K - 1);
        if (!P.c[k]) return null;
        const xc = k * w + w / 2;
        return { x: xc, titolo: `${oraDelGiorno(k * w)}–${oraDelGiorno((k + 1) * w)}`, segni: [[xc, v.Y(P.mx[k]), "var(--primario)"], [xc, v.Y(P.media[k]), "var(--inchiostro)"], [xc, v.Y(P.mn[k]), "var(--primario)"]],
          righe: [["var(--primario)", `massimo: ${MW(P.mx[k])} (${dataBreve(P.tmax[k])})`], [css("--inchiostro"), `media: ${MW(P.media[k])}`],
            ["var(--primario)", `minimo: ${MW(P.mn[k])} (${dataBreve(P.tmin[k])})`], [null, `${num(P.c[k])} ${st.passo === 15 ? "quarti d'ora" : "ore"} nel periodo`]] };
      },
      legenda(dest) {
        const L = h("div", "legenda legenda-grafico");
        L.append(voce("var(--primario)", "fascia tra minimo e massimo", "fascia"), voce("var(--inchiostro)", "media", "linea"),
          voce("var(--primario)", "massimo", "linea"), voce("var(--primario)", "minimo", "linea tratto"));
        dest.appendChild(L);
      },
    };
  }
  // ------------------------------------------------------------------ grafico 2: curva di durata
  function cfgDurata() {
    return {
      titolo: () => `Curva di durata della potenza richiesta – ${nomeZona()} – ${periodoTesto()}`,
      dominio: () => [0, Math.max(1, (st.dur ? st.dur.length : 1) * st.passo / 60)],
      minimo: () => Math.max(1, st.passo / 60 * 8),
      passoTasti: () => st.passo / 60,
      disegna(v) {
        const D = st.dur; if (!D || !D.length) return;
        const w = st.passo / 60, idx = (x) => limita(Math.floor(x / w), 0, D.length - 1);
        const [y0, y1] = intervallo(v, D[idx(v.x1)], D[idx(v.x0)]);
        const Y = asseY(v, y1, "MW", num, y0);
        v.Y = Y;
        const span = v.x1 - v.x0, largo = v.area[2] - v.area[0];
        const p = 10 ** Math.floor(Math.log10(span / Math.max(2, largo / 90))), passo = [1, 2, 5, 10].map((k) => k * p).find((k) => span / k <= Math.max(2, largo / 90)) || p * 10;
        const tk = [];
        for (let x = Math.ceil(v.x0 / passo) * passo; x <= v.x1 + 1e-9; x += passo) tk.push([x, `${num(x, passo < 1 ? 2 : 0)} h`, false]);
        asseX(v, tk);
        // un punto per pixel (la curva è monotona: basta il valore all'inizio di ogni colonna)
        const pts = [], colonne = Math.ceil(largo);
        for (let c = 0; c <= colonne; c++) {
          const x = v.x0 + span * c / colonne;
          if (x > D.length * w) break;
          pts.push(`${(v.area[0] + c * largo / colonne).toFixed(1)},${Y(D[idx(x)]).toFixed(1)}`);
        }
        const xFine = Math.min(v.area[2], v.X(D.length * w));
        s("polygon", { points: `${v.area[0]},${Y(y0)} ${pts.join(" ")} ${xFine.toFixed(1)},${Y(y0)}`, fill: "var(--primario)", "fill-opacity": 0.18 }, v.corpo);
        s("polyline", { points: pts.join(" "), fill: "none", stroke: "var(--primario)", "stroke-width": 2 }, v.corpo);
      },
      punto(x, v) {
        const D = st.dur; if (!D || !D.length || !v.Y) return null;
        const w = st.passo / 60, i = limita(Math.floor(x / w), 0, D.length - 1), ore = (i + 1) * w;
        return { x: ore, titolo: `${num(ore, w < 1 ? 2 : 0)} ore (${pc(100 * (i + 1) / D.length)} del periodo)`, segni: [[ore, v.Y(D[i]), "var(--primario)"]],
          righe: [["var(--primario)", `potenza almeno ${MW(D[i])}`], [null, `${num(i + 1)} ${st.passo === 15 ? "quarti d'ora" : "ore"} su ${num(D.length)}`]] };
      },
      legenda(dest) {
        const L = h("div", "legenda legenda-grafico");
        L.append(voce("var(--primario)", "potenza richiesta, dalla più alta alla più bassa", "linea"));
        dest.appendChild(L);
      },
    };
  }

  // ------------------------------------------------------------------ grafici 3 e 4: fonti, in MW e al 100 %
  // (22/11/2026, richiesta di Paolo) prima delle barre al 100 % la potenza per fonte in valore assoluto, stessa scomposizione
  // e stessi colori; i due grafici hanno la stessa vista (st.finestra, gruppo di grafico()), i pulsanti della finestra e
  // il cursore «Sposta di un mese». Le fonti spente (st.spente, caselle sotto il grafico in MW) escono dalla pila del grafico
  // in MW; in quello al 100 % restano al loro posto, del colore dello sfondo (--sfondo-grafico: --carta nella pagina,
  // --foglio nel riquadro grande).
  const dominioFonti = () => (st.serieIt && st.serieIt.T.length ? [st.serieIt.T[0], st.serieIt.T[st.serieIt.T.length - 1] + st.passo * 60000] : [0, 1]);
  function colonneFonti(S, v, fa) {
    const voci = st.ix.voci, dt = st.passo * 60000;
    const i0 = Math.max(0, cerca(S.T, v.x0 - dt)), i1 = Math.min(S.T.length, cerca(S.T, v.x1) + 1);
    const largo = v.area[2] - v.area[0], perPx = (i1 - i0) / largo, perPixel = perPx > 0.5;
    const passi = perPixel ? Math.ceil(largo) : i1 - i0;
    for (let c = 0; c < passi; c++) {
      let a, b, xa, xb;
      if (perPixel) { xa = v.Xi(v.area[0] + c); xb = v.Xi(v.area[0] + c + 1); a = Math.max(i0, cerca(S.T, xa)); b = Math.min(i1, cerca(S.T, xb)); }
      else { a = i0 + c; b = a + 1; xa = S.T[a]; xb = S.T[a] + dt; }
      const tot = voci.map(() => 0); let n = 0;
      for (let i = a; i < b; i++) {
        if (voci.some((q) => Number.isNaN(S.F[q.id][i]))) continue;
        voci.forEach((q, j) => { tot[j] += Math.max(0, S.F[q.id][i]); });
        n++;
      }
      if (!n) continue;
      const pxa = v.X(xa), pxb = v.X(xb);
      fa(pxa, Math.max(0.6, pxb - pxa - (perPixel ? 0 : Math.min(1, (pxb - pxa) * 0.12))), tot.map((t) => t / n));
    }
  }
  const passoNome = () => (st.passo === 15 ? "quarto d'ora" : "ora");

  function cfgAssoluti() {
    return {
      gruppo: st.finestra,
      titolo: () => `Potenza per fonte, MW medi per ${passoNome()} – Italia – ${periodoTesto()}`,
      dominio: dominioFonti,
      minimo: () => st.passo * 60000 * 6,
      passoTasti: () => st.passo * 60000,
      disegna(v) {
        const S = st.serieIt; if (!S || !S.T.length) return;
        const voci = st.ix.voci, accesa = voci.map((q) => !st.spente.has(q.id));
        const col = [];
        let max = 0;
        colonneFonti(S, v, (x, larg, m) => {
          const tot = m.reduce((t, y, j) => t + (accesa[j] ? y : 0), 0);
          if (tot > max) max = tot;
          col.push([x, larg, m]);
        });
        const Y = asseY(v, scala(max * 1.04 || 1000).top, "MW");
        asseX(v, tackeTempo(v.x0, v.x1, v.area[2] - v.area[0]));
        v.Y = Y;
        if (!accesa.some(Boolean)) {
          s("text", { x: (v.area[0] + v.area[2]) / 2, y: (v.area[1] + v.area[3]) / 2, "text-anchor": "middle", class: "carichi-vuoto" }, v.assi).textContent = "Nessuna fonte accesa";
          return;
        }
        const d = voci.map(() => []);
        for (const [x, larg, m] of col) {
          let acc = 0;
          voci.forEach((q, j) => {
            if (!accesa[j] || !m[j]) return;
            const y0 = Y(acc); acc += m[j];
            d[j].push(rettangolo(x, larg, y0, Y(acc)));
          });
        }
        voci.forEach((q, j) => { if (d[j].length) s("path", { d: d[j].join(""), fill: q.colore, "shape-rendering": "crispEdges", "data-fonte": q.id }, v.corpo); });
        tratteggia(v, S, mancaFonti);
      },
      punto(x, v) {
        const S = st.serieIt; if (!S || !S.T.length || !v.Y) return null;
        const dt = st.passo * 60000, i = limita(cerca(S.T, x + 1) - 1, 0, S.T.length - 1);
        const t = S.T[i], voci = st.ix.voci;
        const titolo = `${dataBreve(t)}, ${oraBreve(t)}–${oraBreve(t + dt)}`;
        if (voci.some((q) => Number.isNaN(S.F[q.id][i]))) return { x: t + dt / 2, titolo, righe: [[null, "dati mancanti: Terna non ha pubblicato la produzione per fonte"], [null, "(il server riprova a scaricarli ogni giorno)"]] };
        const accese = voci.filter((q) => !st.spente.has(q.id));
        const tot = accese.reduce((tt, q) => tt + Math.max(0, S.F[q.id][i]), 0);
        const righe = voci.slice().reverse().map((q) => [st.spente.has(q.id) ? null : q.colore,
          `${q.nome}: ${MW(S.F[q.id][i])}${st.spente.has(q.id) ? " (spenta)" : ""}`]);
        righe.push([null, `fonti accese, in tutto: ${MW(tot)}`]);
        if (!Number.isNaN(S.L[i])) righe.push([null, `potenza richiesta (Italia): ${MW(S.L[i])}`]);
        if (S.passo === 15 && st.passoFonti60 && st.passoFonti60(t)) righe.push([null, "dati orari di Terna: uguali nei quattro quarti d'ora"]);
        return { x: t + dt / 2, titolo, righe, segni: accese.length ? [[t + dt / 2, v.Y(tot), "var(--inchiostro)"]] : [] };
      },
      // caselle per fonte (anche nel riquadro grande: tutte le copie restano allineate), «Accendi tutte», «Spegni tutte»
      legenda(dest) {
        const L = h("div", "legenda legenda-grafico legenda-caselle");
        L.setAttribute("role", "group"); L.setAttribute("aria-label", "Fonti accese nel grafico della potenza");
        st.ix.voci.slice().reverse().forEach((q) => {
          const lab = h("label", "casella-fonte"), c = h("input"), i = h("i"), e = h("small", "energia-fonte");
          c.type = "checkbox"; c.dataset.fonte = q.id; c.dataset.lato = k; c.checked = !st.spente.has(q.id);
          i.style.background = q.colore; e.dataset.energia = q.id; e.dataset.lato = k;
          lab.append(c, i, nomeLegenda(q), e);
          c.addEventListener("change", () => accendiFonti([q.id], c.checked));
          L.appendChild(lab);
        });
        const b = h("div", "legenda-tutte");
        for (const [t, si] of [["Accendi tutte", true], ["Spegni tutte", false]]) {
          const x = h("button", "filtro", t); x.type = "button"; x.dataset.tutte = si ? "1" : "0";
          x.addEventListener("click", () => accendiFonti(st.ix.voci.map((q) => q.id), si));
          b.appendChild(x);
        }
        L.appendChild(b);
        dest.appendChild(L);
        scriviEnergie();
      },
    };
  }

  function cfgFonti() {
    return {
      gruppo: st.finestra,
      titolo: () => `Fonti di produzione, quota per ${passoNome()} – Italia – ${periodoTesto()}`,
      dominio: dominioFonti,
      minimo: () => st.passo * 60000 * 6,
      passoTasti: () => st.passo * 60000,
      disegna(v) {
        const S = st.serieIt; if (!S || !S.T.length) return;
        const Y = asseY(v, 100, "%", (y) => `${num(y)}`);
        asseX(v, tackeTempo(v.x0, v.x1, v.area[2] - v.area[0]));
        const voci = st.ix.voci, d = voci.map(() => []);
        colonneFonti(S, v, (x, larg, m) => {
          const somma = m.reduce((t, y) => t + y, 0);
          if (!somma) return;
          let acc = 0;
          voci.forEach((q, j) => {
            if (!m[j]) return;
            const y0 = Y(100 * acc / somma); acc += m[j];
            d[j].push(rettangolo(x, larg, y0, Y(100 * acc / somma)));
          });
        });
        voci.forEach((q, j) => {
          if (!d[j].length) return;
          const spenta = st.spente.has(q.id);
          s("path", { d: d[j].join(""), fill: spenta ? SFONDO : q.colore, "shape-rendering": "crispEdges", "data-fonte": q.id, class: spenta ? "fonte-spenta" : "" }, v.corpo);
        });
        tratteggia(v, S, mancaFonti);
        v.Y = Y;
      },
      punto(x, v) {
        const S = st.serieIt; if (!S || !S.T.length) return null;
        const dt = st.passo * 60000, i = limita(cerca(S.T, x + 1) - 1, 0, S.T.length - 1);
        const t = S.T[i], voci = st.ix.voci;
        const titolo = `${dataBreve(t)}, ${oraBreve(t)}–${oraBreve(t + dt)}`;
        if (voci.some((q) => Number.isNaN(S.F[q.id][i]))) return { x: t + dt / 2, titolo, righe: [[null, "dati mancanti: Terna non ha pubblicato la produzione per fonte"], [null, "(il server riprova a scaricarli ogni giorno)"]] };
        const pos = voci.reduce((tt, q) => tt + Math.max(0, S.F[q.id][i]), 0);
        const righe = voci.slice().reverse().map((q) => [st.spente.has(q.id) ? null : q.colore,
          `${q.nome}: ${MW(S.F[q.id][i])}${S.F[q.id][i] > 0 ? ` (${pc(100 * S.F[q.id][i] / pos)})` : ""}${st.spente.has(q.id) ? " (spenta)" : ""}`]);
        if (!Number.isNaN(S.L[i])) righe.push([null, `potenza richiesta (Italia): ${MW(S.L[i])}`]);
        if (S.passo === 15 && st.passoFonti60 && st.passoFonti60(t)) righe.push([null, "dati orari di Terna: uguali nei quattro quarti d'ora"]);
        return { x: t + dt / 2, titolo, righe };
      },
      legenda(dest) {
        const L = h("div", "legenda legenda-grafico");
        st.ix.voci.slice().reverse().forEach((q) => {
          const v = voce(q.colore, nomeLegenda(q));
          v.dataset.fonteLegenda = q.id; v.dataset.lato = k; v.classList.toggle("spenta", st.spente.has(q.id));
          L.append(v);
        });
        dest.appendChild(L);
      },
    };
  }

  // ---- tratti senza dati (22/11/2026, Paolo: il buco del 14–15 gennaio 2026): rettangoli tratteggiati con la scritta
  // «dati mancanti» al posto di un vuoto che non si capisce; elenco dei tratti nella nota sotto lo stato della metà
  const mancaFonti = (i) => st.ix.voci.some((q) => Number.isNaN(st.serieIt.F[q.id][i]));
  function tratti(S, manca) {
    const out = [];
    for (let i = 0; i < S.T.length;) {
      if (!manca(i)) { i++; continue; }
      let j = i; while (j < S.T.length && manca(j)) j++;
      out.push([i, j]); i = j;
    }
    return out;
  }
  function tratteggia(v, S, manca) {
    const dt = st.passo * 60000, i0 = Math.max(0, cerca(S.T, v.x0 - dt)), i1 = Math.min(S.T.length, cerca(S.T, v.x1) + 1);
    let pid = null;
    for (let i = i0; i < i1;) {
      if (!manca(i)) { i++; continue; }
      let j = i; while (j < i1 && manca(j)) j++;
      if (!pid) {
        pid = `tratteggio-${Math.random().toString(36).slice(2, 9)}`;
        const pat = s("pattern", { id: pid, patternUnits: "userSpaceOnUse", width: 8, height: 8, patternTransform: "rotate(45)" }, s("defs", {}, v.corpo));
        s("line", { x1: 0, y1: 0, x2: 0, y2: 8, stroke: "var(--tenue)", "stroke-width": 2.5 }, pat);
      }
      const xa = Math.max(v.area[0], v.X(S.T[i])), xb = Math.min(v.area[2], v.X(S.T[j - 1] + dt));
      s("rect", { x: xa, y: v.area[1], width: Math.max(1.5, xb - xa), height: v.area[3] - v.area[1], fill: `url(#${pid})`, "fill-opacity": 0.6, class: "carichi-mancanti-area" }, v.corpo);
      if (xb - xa > 96) s("text", { x: (xa + xb) / 2, y: (v.area[1] + v.area[3]) / 2, "text-anchor": "middle", class: "carichi-mancanti-testo" }, v.corpo).textContent = "dati mancanti";
      i = j;
    }
  }
  function scriviMancanti(S) {
    const dt = st.passo * 60000, nota = $("carichi-mancanti");
    const testo = (tt) => { const p = tt.slice(0, 4).map(([i, j]) => testoFinestra(S.T[i], S.T[j - 1] + dt)); if (tt.length > 4) p.push(`e altri ${num(tt.length - 4)} tratti`); return p.join("; "); };
    const car = tratti(S, (i) => Number.isNaN(S.L[i])), fon = tratti(S, mancaFonti), righe = [];
    if (car.length) righe.push(`potenza richiesta (${nomeZona()}): ${testo(car)}`);
    if (fon.length) righe.push(`produzione per fonte: ${testo(fon)}`);
    nota.hidden = !righe.length;
    nota.textContent = righe.length ? `Dati mancanti nel periodo – ${righe.join(". ")}. Terna non li ha pubblicati: il server riprova a scaricarli ogni giorno e i grafici delle fonti li mostrano tratteggiati.` : "";
  }

  // ---- fonti accese e spente
  function accendiFonti(ids, si) {
    for (const id of ids) { if (si) st.spente.delete(id); else st.spente.add(id); }
    document.querySelectorAll(`input[data-fonte][data-lato="${k}"]`).forEach((c) => { c.checked = !st.spente.has(c.dataset.fonte); });
    document.querySelectorAll(`[data-fonte-legenda][data-lato="${k}"]`).forEach((e) => e.classList.toggle("spenta", st.spente.has(e.dataset.fonteLegenda)));
    st.finestra.grafici.forEach((g) => g.aggiornaCopie());
    const n = st.spente.size, tutte = st.ix.voci.length;
    annuncio.textContent = n === 0 ? "Tutte le fonti accese" : n === tutte ? "Tutte le fonti spente" : `${num(tutte - n)} fonti accese su ${num(tutte)}`;
    scriviPresto();
  }
  // energia di ogni fonte nella finestra visibile (quarti d'ora che cominciano dentro la finestra), accanto alle caselle
  function scriviEnergie() {
    const S = st.serieIt; if (!S || !S.T.length) return;
    const [x0, x1] = st.finestra.vista || dominioFonti(), i0 = cerca(S.T, x0), i1 = cerca(S.T, x1), h0 = st.passo / 60;
    for (const q of st.ix.voci) {
      let e = 0, c = 0;
      const a = S.F[q.id];
      for (let i = i0; i < i1; i++) if (!Number.isNaN(a[i])) { e += a[i] * h0; c++; }
      const g = e / 1000, t = c ? ` · ${num(g, Math.abs(g) >= 100 ? 0 : Math.abs(g) >= 10 ? 1 : 2)} GWh` : "";
      document.querySelectorAll(`[data-energia="${q.id}"][data-lato="${k}"]`).forEach((x) => { x.textContent = t; });
    }
  }

  // ---- finestra dei due grafici delle fonti: pulsanti e cursore «Sposta di un mese»
  // giorno AAAA-MM-GG spostato di k mesi indietro (giorno del mese tenuto, o l'ultimo del mese se non c'è)
  // ultimo giorno con i dati delle fonti nel periodo (tutte le fonti), altrimenti l'ultimo del periodo
  // ultimo giorno con i dati di tutte le fonti: nella serie, se il periodo arriva in fondo all'archivio; altrimenti quello
  // dell'archivio (dall'indice: ultimo mese con le fonti)
  function ultimoGiornoFonti() {
    const S = st.serieIt, voci = st.ix.voci;
    if (S && S.T.length && st.a >= st.ultimoGiorno) {
      for (let i = S.T.length - 1; i >= 0; i--) if (!voci.some((q) => Number.isNaN(S.F[q.id][i]))) return dataIso(S.T[i]);
    }
    return D.ultimoGiornoFonti || st.ultimoGiorno;
  }
  const FINESTRE = { giorno: (u) => u, settimana: (u) => giorniIndietro(u, 6), mese: (u) => mesiIndietro(giornoDopo(u), 1),
    trimestre: (u) => mesiIndietro(giornoDopo(u), 3), anno: (u) => mesiIndietro(giornoDopo(u), 12) };
  const archivio = () => [mezzanotte(st.primoGiorno), mezzanotte(giornoDopo(st.ultimoGiorno))];
  // finestra di un pulsante, in tutto l'archivio (22/11/2026 b): dall'ultimo giorno con i dati delle fonti indietro
  function finestraDi(tipo) {
    if (tipo === "tutto" || !FINESTRE[tipo]) return dominioFonti();
    const u = ultimoGiornoFonti();
    return [Math.max(archivio()[0], mezzanotte(FINESTRE[tipo](u))), mezzanotte(giornoDopo(u))];
  }
  // finestra dentro il periodo scelto
  function vaiFinestra(a, b) {
    const g = st.finestra.grafici[0]; if (!g) return;
    const [d0, d1] = dominioFonti();
    if (b - a >= d1 - d0 - 1000) g.reset(); else g.imposta(a, b);
  }
  // (22/11/2026 b, Paolo: «tornare indietro a tutti gli anni») pulsanti e cursore scorrono su tutto l'archivio: se la
  // finestra esce dal periodo Dal/al, il periodo si sposta con la stessa lunghezza in giorni (più lungo se la finestra non
  // ci sta), si ricalcola e la finestra si rimette dopo il calcolo
  function vaiA(a, b) {
    const [d0, d1] = dominioFonti();
    if (st.serieIt && st.serieIt.T.length && a >= d0 - 1000 && b <= d1 + 1000) { vaiFinestra(a, b); return; }
    const n = giorniTra(st.da, st.a) + 1;
    let fine = dataIso(b - 1), ini = giorniIndietro(fine, n - 1);
    if (ini > dataIso(a)) ini = dataIso(a);
    if (ini < st.primoGiorno) { ini = st.primoGiorno; const f = giorniIndietro(ini, -(n - 1)); if (f > fine) fine = f; }
    if (fine > st.ultimoGiorno) fine = st.ultimoGiorno;
    st.da = ini; st.a = fine; st.finestraIniziale = [a, b];
    scriviDate(); indirizzo(); calcola();
  }
  const vistaFonti = () => st.finestra.vista || dominioFonti();
  // posizioni del cursore in tutto l'archivio: la finestra con la larghezza di adesso (tutto il periodo, se non è
  // ingrandita), che finisce alla fine dell'archivio e poi un mese prima a ogni scatto; l'ultima comincia all'inizio
  // dell'archivio. Dalla più vecchia alla più recente.
  function posizioni() {
    const [A0, A1] = archivio(), [a, b] = vistaFonti(), w = b - a;
    if (w >= A1 - A0 - 1000) return [];
    const out = [];
    for (let j = 0; j < 1200; j++) {
      const e = j === 0 ? A1 : mezzanotte(mesiIndietro(dataIso(A1), j));
      if (e - w <= A0) break;
      out.push([e - w, e]);
    }
    out.push([A0, A0 + w]);
    return out.reverse();
  }
  function scriviFinestra() {
    if (!st.serieIt || !st.serieIt.T.length) return;
    const [a, b] = vistaFonti(), cur = $("carichi-scorri"), out = $("carichi-scorri-testo");
    $("carichi-finestre").querySelectorAll("[data-finestra]").forEach((x) => {
      const [p, q] = finestraDi(x.dataset.finestra);
      x.setAttribute("aria-pressed", String(x.dataset.finestra === "tutto" ? !st.finestra.vista : Math.abs(p - a) < 60000 && Math.abs(q - b) < 60000));
    });
    st.posizioni = posizioni();
    const P = st.posizioni, testo = testoFinestra(a, b);
    if (P.length < 2) {
      cur.disabled = true; cur.max = "0"; cur.value = "0";
      cur.setAttribute("aria-valuetext", `tutto l'archivio, ${testo}`);
      out.textContent = testo;
    } else {
      let j = 0;
      P.forEach(([, e], i) => { if (Math.abs(e - b) < Math.abs(P[j][1] - b)) j = i; });
      cur.disabled = false; cur.max = String(P.length - 1); cur.value = String(j);
      cur.setAttribute("aria-valuetext", testo);
      out.textContent = testo;
    }
    scriviEnergie();
  }
  let timerIndirizzo = 0;
  function scriviPresto() {
    clearTimeout(timerIndirizzo);
    timerIndirizzo = setTimeout(() => { if (st.pronto) { indirizzo(); if (window.EUGENIO_COLLEGAMENTO) window.EUGENIO_COLLEGAMENTO.aggiorna(); } }, 300);
  }
  st.finestra = { vista: null, grafici: [], suCambio: () => { scriviFinestra(); scriviPresto(); } };
  // finestra nell'indirizzo: finestra=AAAA-MM-GG_AAAA-MM-GG (giorni interi, fine compresa) o con l'ora, AAAA-MM-GGTHHMM
  // (l'istante esatto, ora italiana); niente parametro = tutto il periodo
  function finestraTesto() {
    if (!st.finestra.vista) return null;
    const [a, b] = st.finestra.vista.map((t) => Math.round(t / 60000) * 60000);
    const ora = (t) => { const d = locale(t); return `T${due(d.getUTCHours())}${due(d.getUTCMinutes())}`; };
    return `${dataIso(a)}${aMezzanotte(a) ? "" : ora(a)}_${aMezzanotte(b) ? dataIso(b - 1) : dataIso(b) + ora(b)}`;
  }
  // ------------------------------------------------------------------ testo
  const nomeZona = () => (st.ix.zone.find((z) => z.id === st.zona) || { nome: "Italia" }).nome;
  const periodoTesto = () => `dal ${dataBreve(mezzanotte(st.da))} al ${dataBreve(mezzanotte(st.a))}`;
  function scriviRiepilogo(R) {
    const dl = $("riepilogo-carichi"); dl.replaceChildren();
    const riga = (t, v, nota) => { const d = h("div"); d.append(h("dt", null, t)); const dd = h("dd", null, v); if (nota) dd.appendChild(h("small", null, nota)); d.appendChild(dd); dl.appendChild(d); };
    const unita = st.passo === 15 ? "quarti d'ora" : "ore";
    riga("Energia richiesta", R.energia >= 1e6 ? `${num(R.energia / 1e6, 2)} TWh` : `${num(R.energia / 1e3, 1)} GWh`);
    riga("Potenza massima", MW(R.mx), R.tmx !== null ? `${dataBreve(R.tmx)}, ${oraBreve(R.tmx)}` : "");
    riga("Potenza minima", MW(R.mn), R.tmn !== null ? `${dataBreve(R.tmn)}, ${oraBreve(R.tmn)}` : "");
    riga("Potenza media", MW(R.media), Number.isFinite(R.mx) && R.mx ? `${pc(100 * R.media / R.mx)} della massima` : "");
    if (R.quotaRen !== null) riga("Produzione rinnovabile", pc(R.quotaRen), "della potenza richiesta (Italia)");
    riga(st.passo === 15 ? "Quarti d'ora" : "Ore", num(R.c), R.c < R.n ? `${num(R.n - R.c)} ${unita} senza dati` : "tutti con i dati");
  }

  // ------------------------------------------------------------------ calcolo e disegno
  async function calcola() {
    const mio = ++st.giro;
    stato("Calcolo…");
    scriviAnno();
    try {
      const S = await serie();
      if (mio !== st.giro) return;
      st.serie = S; st.serieIt = { ...S, L: S.LI };
      st.prof = profilo(S); st.dur = durata(S);
      scriviRiepilogo(riepilogo(S));
      $("titolo-profilo").textContent = `Profilo giornaliero – ${nomeZona()}`;
      $("titolo-durata").textContent = `Curva di durata – ${nomeZona()}`;
      $("titolo-assoluti").textContent = "Potenza per fonte – Italia";
      $("titolo-fonti").textContent = "Fonti di produzione – Italia";
      $("nota-zona-fonti").hidden = st.zona === "ITA";
      const g = st.grafici, periodo = `${st.da}|${st.a}`;
      if (!g.profilo) {
        g.profilo = grafico($("grafico-profilo"), cfgProfilo());
        g.durata = grafico($("grafico-durata"), cfgDurata());
        g.assoluti = grafico($("grafico-assoluti"), cfgAssoluti());
        g.fonti = grafico($("grafico-fonti"), cfgFonti());
      } else {
        g.profilo.vista = g.profilo.vista && st.passoPrima === st.passo ? g.profilo.vista : null;
        g.durata.vista = null;
        // (22/11/2026) la finestra delle fonti (tempi, sempre dell'Italia) resta col cambio di zona o di passo
        if (st.periodoPrima !== periodo) st.finestra.vista = null;
        Object.values(g).forEach((x) => x.ridisegna());
      }
      // finestra dell'indirizzo o di un pulsante / del cursore fuori dal periodo di prima: dentro il periodo nuovo
      if (st.finestraIniziale) { const [a, b] = st.finestraIniziale; st.finestraIniziale = null; vaiFinestra(a, b); }
      st.passoPrima = st.passo; st.periodoPrima = periodo;
      scriviFinestra();
      scriviMancanti(S);
      const senza = S.T.length && Array.from(S.L).every(Number.isNaN);
      const ultimo = st.mesi[st.mesi.length - 1];
      stato(senza ? "Nessun dato nel periodo scelto." : `Dati di Terna fino al ${dataBreve(ultimo.t0 + (ultimo.n - 1) * Q)}, ${oraBreve(ultimo.t0 + (ultimo.n - 1) * Q)} (aggiornati il ${new Date(st.ix.aggiornato).toLocaleDateString("it-IT")}).`, !!senza);
    } catch (e) {
      if (mio === st.giro) stato(`Errore nel caricamento dei dati: ${e.message}`, true);
    }
  }

  const spenteTesto = () => (st.ix ? st.ix.voci.filter((q) => st.spente.has(q.id)).map((q) => q.id).join(",") : "") || null;
  // parametri della metà nell'indirizzo (la destra con «2» in fondo: zona2, da2, …); i predefiniti no (Italia, quarti
  // d'ora, tutto il periodo, tutte le fonti accese); prima dei grafici la finestra dell'indirizzo resta
  function parametri() {
    return { [`zona${P}`]: st.zona === "ITA" ? null : st.zona, [`da${P}`]: st.da, [`a${P}`]: st.a,
      [`passo${P}`]: st.passo === 15 ? null : String(st.passo),
      [`finestra${P}`]: st.grafici.assoluti ? finestraTesto() : undefined, [`spente${P}`]: spenteTesto() };
  }
  function scegliZona(id, perMappa = false) {
    if (!st.ix.zone.some((z) => z.id === id)) id = "ITA";
    st.zona = id;
    $("carichi-zona").value = id;
    evidenzia(); if (!perMappa) indirizzo(); calcola();
  }
  // ------------------------------------------------------------------ comandi
  function periodoValido(da, a) {
    const min = st.primoGiorno, max = st.ultimoGiorno;
    const ok = (x) => /^\d{4}-\d\d-\d\d$/.test(x || "");
    da = ok(da) ? da : null; a = ok(a) ? a : null;
    if (!a || a > max) a = max;
    if (a < min) a = min;
    if (!da) { const [y, m, d] = a.split("-").map(Number); da = new Date(Date.UTC(y - 1, m - 1, d + 1)).toISOString().slice(0, 10); }
    if (da < min) da = min;
    if (da > a) [da, a] = [a, da];
    return [da, a];
  }
  function ultimi12() { [st.da, st.a] = periodoValido(null, st.ultimoGiorno); scriviDate(); indirizzo(); calcola(); }
  function scriviDate() {
    for (const [id, v] of [["carichi-da", st.da], ["carichi-a", st.a]]) { const i = $(id); i.min = st.primoGiorno; i.max = st.ultimoGiorno; i.value = v; }
    scriviAnno();
  }
  // (22/11/2026 b, Paolo) anno intero: menu dell'anno e «‹ ›» (anno precedente e successivo) che scrivono Dal/al
  const anniArchivio = () => { const out = []; for (let y = +st.primoGiorno.slice(0, 4); y <= +st.ultimoGiorno.slice(0, 4); y++) out.push(y); return out; };
  const limitiAnno = (y) => [`${y}-01-01` < st.primoGiorno ? st.primoGiorno : `${y}-01-01`, `${y}-12-31` > st.ultimoGiorno ? st.ultimoGiorno : `${y}-12-31`];
  function annoScelto() {
    const y = +st.da.slice(0, 4), [a, b] = limitiAnno(y);
    return st.da === a && st.a === b ? y : null;
  }
  function scegliAnno(y) {
    if (!anniArchivio().includes(y)) return;
    [st.da, st.a] = limitiAnno(y); scriviDate(); indirizzo(); calcola();
  }
  const annoPrima = () => { const y = annoScelto(); return y !== null ? y - 1 : +st.a.slice(0, 4) - 1; };
  const annoDopo = () => { const y = annoScelto(); return y !== null ? y + 1 : +st.a.slice(0, 4); };
  function scriviAnno() {
    if (!st.da || !D.ix) return;
    const sel = $("carichi-anno"), y = annoScelto(), anni = anniArchivio();
    if (sel.options.length !== anni.length + 1) {
      sel.replaceChildren(new Option("Anno…", ""), ...anni.map((x) => new Option(String(x), String(x))));
    }
    sel.value = y === null ? "" : String(y);
    $("anno-prima").disabled = !anni.includes(annoPrima());
    $("anno-dopo").disabled = !anni.includes(annoDopo()) || annoDopo() === y;
  }

  // ------------------------------------------------------------------ avvio della metà
  function avvia(q) {
    const z = (q.get(`zona${P}`) || "").toUpperCase();
    st.zona = st.ix.zone.some((x) => x.id === z) ? z : "ITA";
    st.passo = q.get(`passo${P}`) === "60" ? 60 : 15;
    [st.da, st.a] = periodoValido(q.get(`da${P}`), q.get(`a${P}`));
    (q.get(`spente${P}`) || "").split(",").forEach((id) => { if (st.ix.voci.some((v) => v.id === id)) st.spente.add(id); });
    st.finestraIniziale = leggiFinestra(q.get(`finestra${P}`));
    const sel = $("carichi-zona");
    sel.replaceChildren(...st.ix.zone.map((x) => new Option(x.id === "ITA" ? "Italia (tutte le zone)" : x.nome, x.id)));
    sel.value = st.zona;
    sel.addEventListener("change", () => scegliZona(sel.value));
    $("carichi-quarti").checked = st.passo === 15;
    scriviDate();
    const date = () => { [st.da, st.a] = periodoValido($("carichi-da").value || st.da, $("carichi-a").value || st.a); scriviDate(); indirizzo(); calcola(); };
    $("carichi-da").addEventListener("change", date);
    $("carichi-a").addEventListener("change", date);
    $("ultimi-12").addEventListener("click", ultimi12);
    $("carichi-anno").addEventListener("change", (e) => { if (e.target.value) scegliAnno(+e.target.value); });
    $("anno-prima").addEventListener("click", () => scegliAnno(annoPrima()));
    $("anno-dopo").addEventListener("click", () => scegliAnno(annoDopo()));
    $("carichi-quarti").addEventListener("change", (e) => { st.passo = e.target.checked ? 15 : 60; indirizzo(); calcola(); });
    $("carichi-finestre").querySelectorAll("[data-finestra]").forEach((b) => b.addEventListener("click", () => vaiA(...finestraDi(b.dataset.finestra))));
    $("carichi-scorri").addEventListener("input", (e) => { const p = st.posizioni && st.posizioni[+e.target.value]; if (p) vaiA(p[0], p[1]); });
  }
  Object.assign(st, { calcola, avvia, parametri, scegliZona, finestraDi, finestraTesto, spenteTesto, nomeZona, stato,
    posizioniCursore: () => st.posizioni, radice });
  return st;
  }   // fine di creaLato

  // ================================================================== parti comuni alle due metà
  function indirizzo() {
    const u = new URL(location.href);
    for (const L of D.lati) {
      for (const [k, v] of Object.entries(L.parametri())) {
        if (v === undefined) continue;                     // finestra prima dei grafici: resta com'è
        if (v === null || v === "") u.searchParams.delete(k); else u.searchParams.set(k, v);
      }
    }
    if (u.href !== location.href) history.replaceState(null, "", u);
  }

  // metà destra: copia della sinistra (comandi, sezioni, grafici vuoti) con gli identificativi e i riferimenti con «-2»
  function copiaMeta() {
    const sx = $("carichi-lato"), dx = $("carichi-lato-2");
    if (!sx || !dx || dx.childElementCount) return;
    const c = sx.cloneNode(true);
    const rinomina = (v) => v.split(/\s+/).map((x) => (x ? `${x}-2` : x)).join(" ");
    c.querySelectorAll("[id]").forEach((e) => { e.id += "-2"; });
    for (const a of ["for", "aria-labelledby", "aria-describedby", "aria-controls"]) {
      c.querySelectorAll(`[${a}]`).forEach((e) => e.setAttribute(a, rinomina(e.getAttribute(a))));
    }
    c.querySelector(".comandi-carichi").setAttribute("aria-label", "Scelte della metà destra");
    dx.append(...c.childNodes);
  }

  // ------------------------------------------------------------------ piccola mappa delle zone (comune alle due metà)
  // (22/11/2026 b, Paolo) il clic su una zona la sceglie in tutte e due le metà (un secondo clic, con la zona già in tutte
  // e due, torna all'Italia); le zone delle due metà sono evidenziate con due stili (sinistra: bordo pieno scuro, destra:
  // bordo tratteggiato colorato; la stessa zona in tutte e due: bordo pieno colorato e spesso) e spiegate sotto la mappa
  async function minimappa() {
    const box = $("minimappa-zone");
    let m;
    try { const r = await fetch(conV("dati/mappa/zone.json")); if (!r.ok) throw new Error(String(r.status)); m = await r.json(); } catch { box.remove(); return; }
    box.innerHTML = '<div class="minimappa-etichetta" role="status"></div>' +
      '<div class="minimappa-comandi"><button type="button" data-z="1.6" title="Ingrandisci" aria-label="Ingrandisci la piccola mappa">+</button>' +
      '<button type="button" data-z="0.625" title="Rimpicciolisci" aria-label="Rimpicciolisci la piccola mappa">−</button>' +
      '<button type="button" data-z="0" title="Ripristina la vista" aria-label="Ripristina la vista della piccola mappa">⟲</button></div>';
    const et = box.querySelector(".minimappa-etichetta");
    const svg = s("svg", { viewBox: m.viewBox.join(" "), role: "group", "aria-label": "Scegli la zona di mercato (per tutte e due le metà)" });
    box.prepend(svg);
    const g = s("g", {}, svg);
    D.percorsi = new Map();
    const tutte = (id) => D.lati.every((L) => L.zona === id);
    const scegli = (id) => { const n = tutte(id) ? "ITA" : id; D.lati.forEach((L) => L.scegliZona(n, true)); indirizzo(); };
    for (const z of m.zone) {
      const p = s("path", { d: z.d, fill: `var(--reg-${COLORE_ZONA[z.id] || "08"})`, tabindex: "0", role: "button", "aria-label": `Zona ${z.nome}` }, g);
      p.dataset.zona = z.id;
      D.percorsi.set(z.id, p);
      const nomeEt = () => (tutte(z.id) ? `${z.nome}: clic per tornare all'Italia` : `Zona ${z.nome}`);
      p.addEventListener("mousemove", (e) => {
        const b = box.getBoundingClientRect();
        et.textContent = nomeEt(); et.style.display = "block";
        et.style.left = `${Math.max(0, Math.min(e.clientX - b.left + 10, b.width - et.offsetWidth))}px`;
        et.style.top = `${Math.max(0, e.clientY - b.top - 28)}px`;
      });
      p.addEventListener("mouseleave", () => { et.style.display = "none"; });
      p.addEventListener("focus", () => { et.textContent = nomeEt(); et.style.display = "block"; et.style.left = "0"; et.style.top = "0"; });
      p.addEventListener("blur", () => { et.style.display = "none"; });
      p.addEventListener("click", () => scegli(z.id));
      p.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); scegli(z.id); } });
    }
    if (E && E.zoomabile) {
      const vb = m.viewBox.map(Number);
      const z = E.zoomabile(svg, { limiti: () => vb, ritorno: () => vb, minimo: 1 / 12,
        suCambio: (f) => { svg.style.setProperty("--tratto-mm", (1.2 * f).toFixed(3)); box.classList.toggle("ingrandita", f < 0.999); } });
      box.querySelectorAll(".minimappa-comandi button[data-z]").forEach((b) => b.addEventListener("click", () => z.zoom(+b.dataset.z)));
    } else box.querySelector(".minimappa-comandi").remove();
    evidenzia();
  }
  function evidenzia() {
    const [s0, s1] = D.lati.map((L) => L.zona);
    const leg = $("minimappa-legenda");
    if (leg && D.lati.length === 2) {
      const nome = (id) => (D.ix.zone.find((z) => z.id === id) || { nome: "Italia" }).nome;
      const voceL = (cls, t) => { const sp = h("span", "voce-meta"); sp.append(h("i", cls), t); return sp; };
      leg.replaceChildren();
      if (s0 === s1) leg.append(voceL(s0 === "ITA" ? "meta-italia" : "meta-tutte", s0 === "ITA" ? "Tutte e due le metà: Italia (tutte le zone)" : `Tutte e due le metà: ${nome(s0)}`));
      else leg.append(voceL(s0 === "ITA" ? "meta-italia" : "meta-sx", `Sinistra: ${s0 === "ITA" ? "Italia (tutte le zone)" : nome(s0)}`),
        voceL(s1 === "ITA" ? "meta-italia" : "meta-dx", `Destra: ${s1 === "ITA" ? "Italia (tutte le zone)" : nome(s1)}`));
    }
    if (!D.percorsi) return;
    D.percorsi.forEach((p, id) => {
      const a = id === s0, b = id === s1;
      p.classList.toggle("attiva", a || b);
      p.classList.toggle("meta-sx", a && !b); p.classList.toggle("meta-dx", b && !a); p.classList.toggle("meta-tutte", a && b);
      p.setAttribute("aria-pressed", String(a && b));
      p.setAttribute("aria-label", `Zona ${(D.ix.zone.find((z) => z.id === id) || {}).nome || id}${a && b ? " (scelta in tutte e due le metà)" : a ? " (scelta nella metà sinistra)" : b ? " (scelta nella metà destra)" : ""}`);
    });
    for (const id of [s0, s1]) { const p = D.percorsi.get(id); if (p) p.parentNode.appendChild(p); }
    const box = $("minimappa-zone");
    if (box) { box.classList.toggle("tutta-italia", s0 === "ITA" && s1 === "ITA"); box.classList.toggle("con-scelta", s0 !== "ITA" || s1 !== "ITA"); }
  }

  async function avvio() {
    try { D.ix = await json("indice.json"); } catch {
      senzaDati("I dati di Terna non sono ancora disponibili su questo server (li prepara il worker una volta al giorno).");
      return;
    }
    D.mesi = (D.ix.mesi || []).map((m) => ({ ...m, t0: Date.parse(m.inizio) }));
    if (!D.mesi.length) { senzaDati("Nessun dato di Terna disponibile su questo server."); return; }
    const ult = D.mesi[D.mesi.length - 1], ultF = D.mesi.filter((m) => m.fonti).pop();
    D.primoGiorno = dataIso(D.mesi[0].t0);
    D.ultimoGiorno = dataIso(ult.t0 + (ult.n - 1) * Q);
    D.ultimoGiornoFonti = ultF ? dataIso(ultF.t0 + (ultF.n - 1) * Q) : D.ultimoGiorno;
    D.passoFonti60 = (t) => { const m = D.mesi.find((x) => t >= x.t0 && t < x.t0 + x.n * Q); return m && m.passo_fonti === 60; };
    copiaMeta();
    const q = new URLSearchParams(location.search);
    D.lati = [creaLato(0), creaLato(1)];
    D.lati.forEach((L) => L.avvia(q));
    window.EUGENIO_CARICHI = { stato: D.lati[0], destra: D.lati[1], lati: D.lati, dati: D, scegliZona: (id) => D.lati[0].scegliZona(id),
      calcola: () => D.lati[0].calcola(), finestraDi: (t) => D.lati[0].finestraDi(t), posizioni: () => D.lati[0].posizioniCursore() };   // per le prove
    indirizzo();
    minimappa();
    evidenzia();
    await Promise.all(D.lati.map((L) => L.calcola()));
    indirizzo();                     // con la finestra dell'indirizzo, rimessa dopo il primo calcolo
  }
  avvio().catch((e) => { const m = $("stato-carichi"); m.textContent = `Errore: ${e.message}`; m.classList.add("errore"); })
    .finally(() => { D.pronto = true; });

  // collegamento a questa simulazione (20/11/2026, collegamento.js): l'avvio legge già i parametri delle due metà (dal
  // 22/11/2026 b: zona, da, a, passo, finestra, spente e gli stessi con «2» per la metà destra), quindi basta dire al
  // modulo quali sono e quando la pagina è pronta.
  const CHIAVI = ["zona", "da", "a", "passo", "finestra", "spente"];
  if (window.EUGENIO_COLLEGAMENTO) window.EUGENIO_COLLEGAMENTO.registra({
    regione: false,
    chiavi: [...CHIAVI, ...CHIAVI.map((c) => `${c}2`)],
    principali: [...CHIAVI, ...CHIAVI.map((c) => `${c}2`)],
    pronto: () => D.pronto,
    leggi: () => {
      if (!D.pronto || !D.ix || D.lati.length !== 2 || !D.lati[0].da) return null;
      const out = {};
      for (const L of D.lati) for (const [k, v] of Object.entries(L.parametri())) out[k] = v === undefined ? null : v;
      return out;
    },
  });
})();
