"use strict";
// Statistiche › «Carichi elettrici» (carichi.html, 20/11/2026, richiesta di Paolo; sperimentale).
// Pagina unica a tutta larghezza, senza mappa grande: la zona di mercato si sceglie solo nella piccola mappa accanto al
// titolo (zone al posto delle regioni; dati/mappa/zone.json, costruito da costruisci_zone.py). Clic su una zona = i suoi
// valori; secondo clic (o «Tutta Italia») = Italia. Sotto: periodo (due date, predefinito gli ultimi 12 mesi) e casella
// «Quarti d'ora» (senza: ore, media dei quattro quarti d'ora).
// Grafici (SVG disegnato a ogni vista, con percorsi aggregati per pixel: decine di migliaia di quarti d'ora restano
// leggeri):
//   1. profilo giornaliero: per ogni quarto d'ora (o ora) del giorno minimo, media e massimo della potenza richiesta;
//   2. curva di durata: le potenze del periodo dalla più alta alla più bassa;
//   3. fonti: barre al 100 % per quarto d'ora (o ora), solo Italia (Terna non pubblica la produzione per zona).
// Ogni grafico si ingrandisce con la rotella e si sposta trascinando (asse orizzontale) nella pagina e nel riquadro
// grande di grafici.js (svg.__zoomProprio: grafici.js gli passa rotella, tasti e «Vista iniziale").
// Dati: dati/carichi/indice.json, carico_AAAA-MM.json, fonti_AAAA-MM.json (fase 15, elettricita/carichi.py, costruiti
// dal worker con i dati di Terna). Decisione di Paolo (20/11/2026): i dati non si scaricano.
// Le scelte stanno nell'indirizzo: ?zona=NORD&da=AAAA-MM-GG&a=AAAA-MM-GG&passo=15|60 (history.replaceState); il riquadro
// «Collegamento a questa simulazione» in fondo alla pagina lo mostra e lo copia (collegamento.js).
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
  // numeri all'italiana, sempre con il punto delle migliaia (anche a 4 cifre: 4.063). In it-IT il raggruppamento
  // normale scatta solo da 5 cifre, quindi useGrouping: "always"; dove il browser non lo conosce (controllo fatto
  // una volta sola), si formatta senza raggruppamento e si mette il punto ogni tre cifre nella parte intera.
  const GRUPPI_SEMPRE = (() => { try { return new Intl.NumberFormat("it-IT", { useGrouping: "always" }).format(1234) === "1.234"; } catch (e) { return false; } })();
  const formati = new Map();
  const num = (v, d = 0) => {
    if (v === null || v === undefined || !Number.isFinite(+v)) return "–";
    let f = formati.get(d);
    if (!f) { f = new Intl.NumberFormat("it-IT", { useGrouping: GRUPPI_SEMPRE ? "always" : false, minimumFractionDigits: d, maximumFractionDigits: d }); formati.set(d, f); }
    const t = f.format(+v);
    return GRUPPI_SEMPRE ? t : t.replace(/^(\D*)(\d+)/, (_, segno, intera) => segno + intera.replace(/\B(?=(\d{3})+$)/g, "."));
  };
  const MW = (v) => `${num(v)} MW`;
  const pc = (v) => `${num(v, v < 10 ? 1 : 0)} %`;
  const limita = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
  function stato(t, errore = false) { const m = $("stato-carichi"); m.textContent = t; m.classList.toggle("errore", errore); }

  // colori delle zone nella piccola mappa: quelli di una regione della zona (variabili --reg-RR di stile.css)
  const COLORE_ZONA = { NORD: "03", CNOR: "09", CSUD: "12", SUD: "16", CALA: "18", SICI: "19", SARD: "20" };

  const st = { ix: null, mesi: [], zona: "ITA", da: null, a: null, passo: 15, file: new Map(), giro: 0, serie: null, grafici: {} };

  // ------------------------------------------------------------------ tempo (ora italiana)
  // fuso di un istante (minuti dall'UTC) dai cambi d'ora scritti nell'indice; fuori dai mesi, con Intl
  const fmtFuso = new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Rome", hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
  function fusoIntl(ms) {
    const p = Object.fromEntries(fmtFuso.formatToParts(new Date(ms)).map((x) => [x.type, x.value]));
    return Math.round((Date.UTC(+p.year, p.month - 1, +p.day, +p.hour, +p.minute) - Math.floor(ms / 60000) * 60000) / 60000);
  }
  function fuso(ms) {
    const M = st.mesi;
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
  function file(nome) { if (!st.file.has(nome)) st.file.set(nome, json(nome).catch((e) => { st.file.delete(nome); throw e; })); return st.file.get(nome); }

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

  function grafico(box, cfg) {
    const gr = { cfg, vista: null, copie: new Set() };
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
    function aggiorna() { for (const c of [...gr.copie]) { if (!c.svg.isConnected) gr.copie.delete(c); else c.disegna(); } }
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
    const max = Math.max(2, Math.floor(largo / 80)), span = x1 - x0;
    const passi = [[15 * 60000, "m"], [30 * 60000, "m"], [ORA, "h"], [3 * ORA, "h"], [6 * ORA, "h"], [12 * ORA, "h"], [GIORNO, "g"], [2 * GIORNO, "g"],
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
  const oraDelGiorno = (o) => { const m = Math.round(o * 60); return `${due(Math.floor(m / 60))}:${due(m % 60)}`; };
  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || "#888";
  function voce(colore, testo, tipo) {
    const sp = h("span"), i = h("i", tipo === "linea" || tipo === "linea tratto" ? `linea ${tipo === "linea tratto" ? "tratto" : ""}` : "");
    if (tipo === "fascia") { i.style.background = colore; i.style.opacity = ".35"; } else if (tipo && tipo.startsWith("linea")) i.style.color = colore; else i.style.background = colore;
    sp.append(i, testo); return sp;
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

  // ------------------------------------------------------------------ grafico 3: fonti, barre al 100 %
  const POSITIVE = (k) => k !== "saldo";
  function cfgFonti() {
    return {
      titolo: () => `Fonti di produzione, quota per ${st.passo === 15 ? "quarto d'ora" : "ora"} – Italia – ${periodoTesto()}`,
      dominio: () => (st.serieIt && st.serieIt.T.length ? [st.serieIt.T[0], st.serieIt.T[st.serieIt.T.length - 1] + st.passo * 60000] : [0, 1]),
      minimo: () => st.passo * 60000 * 6,
      passoTasti: () => st.passo * 60000,
      disegna(v) {
        const S = st.serieIt; if (!S || !S.T.length) return;
        const Y = asseY(v, 100, "%", (y) => `${num(y)}`);
        asseX(v, tackeTempo(v.x0, v.x1, v.area[2] - v.area[0]));
        const voci = st.ix.voci, dt = st.passo * 60000;
        const i0 = Math.max(0, cerca(S.T, v.x0 - dt)), i1 = Math.min(S.T.length, cerca(S.T, v.x1) + 1);
        const largo = v.area[2] - v.area[0], perPx = (i1 - i0) / largo;
        // colonne: un quarto d'ora (o un'ora) ciascuna se c'è posto, altrimenti un pixel che somma i quarti d'ora che copre
        const passi = perPx > 0.5 ? Math.ceil(largo) : i1 - i0;
        const d = voci.map(() => []);
        for (let c = 0; c < passi; c++) {
          let a, b, xa, xb;
          if (perPx > 0.5) { xa = v.Xi(v.area[0] + c); xb = v.Xi(v.area[0] + c + 1); a = Math.max(i0, cerca(S.T, xa)); b = Math.min(i1, cerca(S.T, xb)); }
          else { a = i0 + c; b = a + 1; xa = S.T[a]; xb = S.T[a] + dt; }
          const tot = voci.map(() => 0); let somma = 0;
          for (let i = a; i < b; i++) {
            if (voci.some((q) => Number.isNaN(S.F[q.id][i]))) continue;
            voci.forEach((q, j) => { const x = Math.max(0, S.F[q.id][i]); tot[j] += x; somma += x; });
          }
          if (!somma) continue;
          const pxa = v.X(xa), pxb = v.X(xb), larg = Math.max(0.6, pxb - pxa - (perPx > 0.5 ? 0 : Math.min(1, (pxb - pxa) * 0.12)));
          let acc = 0;
          voci.forEach((q, j) => {
            if (!tot[j]) return;
            const y0 = Y(100 * acc / somma); acc += tot[j]; const y1 = Y(100 * acc / somma);
            d[j].push(`M${pxa.toFixed(2)},${y1.toFixed(2)}h${larg.toFixed(2)}V${y0.toFixed(2)}h${(-larg).toFixed(2)}z`);
          });
        }
        voci.forEach((q, j) => { if (d[j].length) s("path", { d: d[j].join(""), fill: q.colore, "shape-rendering": "crispEdges" }, v.corpo); });
        v.Y = Y;
      },
      punto(x, v) {
        const S = st.serieIt; if (!S || !S.T.length) return null;
        const dt = st.passo * 60000, i = limita(cerca(S.T, x + 1) - 1, 0, S.T.length - 1);
        const t = S.T[i], voci = st.ix.voci;
        const titolo = `${dataBreve(t)}, ${oraBreve(t)}–${oraBreve(t + dt)}`;
        if (voci.some((q) => Number.isNaN(S.F[q.id][i]))) return { x: t + dt / 2, titolo, righe: [[null, "produzione per fonte non disponibile"]] };
        const pos = voci.reduce((tt, q) => tt + Math.max(0, S.F[q.id][i]), 0);
        const righe = voci.slice().reverse().map((q) => [q.colore, `${q.nome}: ${MW(S.F[q.id][i])}${S.F[q.id][i] > 0 ? ` (${pc(100 * S.F[q.id][i] / pos)})` : ""}`]);
        if (!Number.isNaN(S.L[i])) righe.push([null, `potenza richiesta (Italia): ${MW(S.L[i])}`]);
        if (S.passo === 15 && st.passoFonti60 && st.passoFonti60(t)) righe.push([null, "dati orari di Terna: uguali nei quattro quarti d'ora"]);
        return { x: t + dt / 2, titolo, righe };
      },
      legenda(dest) {
        const L = h("div", "legenda legenda-grafico");
        st.ix.voci.slice().reverse().forEach((q) => L.append(voce(q.colore, q.id === "saldo" ? "saldo con l'estero, pompaggi e accumuli (quando positivo)" : q.nome)));
        dest.appendChild(L);
      },
    };
  }
  function cerca(T, x) { let lo = 0, hi = T.length; while (lo < hi) { const m = (lo + hi) >> 1; if (T[m] < x) lo = m + 1; else hi = m; } return lo; }

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
    try {
      const S = await serie();
      if (mio !== st.giro) return;
      st.serie = S; st.serieIt = { ...S, L: S.LI };
      st.prof = profilo(S); st.dur = durata(S);
      scriviRiepilogo(riepilogo(S));
      $("titolo-profilo").textContent = `Profilo giornaliero – ${nomeZona()}`;
      $("titolo-durata").textContent = `Curva di durata – ${nomeZona()}`;
      $("titolo-fonti").textContent = "Fonti di produzione – Italia";
      $("nota-zona-fonti").hidden = st.zona === "ITA";
      const g = st.grafici;
      if (!g.profilo) {
        g.profilo = grafico($("grafico-profilo"), cfgProfilo());
        g.durata = grafico($("grafico-durata"), cfgDurata());
        g.fonti = grafico($("grafico-fonti"), cfgFonti());
      } else {
        g.profilo.vista = g.profilo.vista && st.passoPrima === st.passo ? g.profilo.vista : null;
        g.durata.vista = null; g.fonti.vista = null;
        Object.values(g).forEach((x) => x.ridisegna());
      }
      st.passoPrima = st.passo;
      const senza = S.T.length && Array.from(S.L).every(Number.isNaN);
      const ultimo = st.mesi[st.mesi.length - 1];
      stato(senza ? "Nessun dato nel periodo scelto." : `Dati di Terna fino al ${dataBreve(ultimo.t0 + (ultimo.n - 1) * Q)}, ${oraBreve(ultimo.t0 + (ultimo.n - 1) * Q)} (aggiornati il ${new Date(st.ix.aggiornato).toLocaleDateString("it-IT")}).`, !!senza);
    } catch (e) {
      if (mio === st.giro) stato(`Errore nel caricamento dei dati: ${e.message}`, true);
    }
  }

  function indirizzo() {
    const u = new URL(location.href);
    if (st.zona === "ITA") u.searchParams.delete("zona"); else u.searchParams.set("zona", st.zona);
    u.searchParams.set("da", st.da); u.searchParams.set("a", st.a); u.searchParams.set("passo", String(st.passo));
    history.replaceState(null, "", u);
  }

  // ------------------------------------------------------------------ piccola mappa delle zone
  async function minimappa() {
    const box = $("minimappa-zone");
    let m;
    try { const r = await fetch(conV("dati/mappa/zone.json")); if (!r.ok) throw new Error(String(r.status)); m = await r.json(); } catch { box.remove(); return; }
    box.innerHTML = '<div class="minimappa-etichetta" role="status"></div>' +
      '<div class="minimappa-comandi"><button type="button" data-z="1.6" title="Ingrandisci" aria-label="Ingrandisci la piccola mappa">+</button>' +
      '<button type="button" data-z="0.625" title="Rimpicciolisci" aria-label="Rimpicciolisci la piccola mappa">−</button>' +
      '<button type="button" data-z="0" title="Ripristina la vista" aria-label="Ripristina la vista della piccola mappa">⟲</button></div>';
    const et = box.querySelector(".minimappa-etichetta");
    const svg = s("svg", { viewBox: m.viewBox.join(" "), role: "group", "aria-label": "Scegli la zona di mercato" });
    box.prepend(svg);
    const g = s("g", {}, svg);
    st.percorsi = new Map();
    for (const z of m.zone) {
      const p = s("path", { d: z.d, fill: `var(--reg-${COLORE_ZONA[z.id] || "08"})`, tabindex: "0", role: "button", "aria-label": `Zona ${z.nome}` }, g);
      p.dataset.zona = z.id;
      st.percorsi.set(z.id, p);
      const nomeEt = () => (st.zona === z.id ? `${z.nome}: clic per tornare all'Italia` : `Zona ${z.nome}`);
      p.addEventListener("mousemove", (e) => {
        const b = box.getBoundingClientRect();
        et.textContent = nomeEt(); et.style.display = "block";
        et.style.left = `${Math.max(0, Math.min(e.clientX - b.left + 10, b.width - et.offsetWidth))}px`;
        et.style.top = `${Math.max(0, e.clientY - b.top - 28)}px`;
      });
      p.addEventListener("mouseleave", () => { et.style.display = "none"; });
      p.addEventListener("focus", () => { et.textContent = nomeEt(); et.style.display = "block"; et.style.left = "0"; et.style.top = "0"; });
      p.addEventListener("blur", () => { et.style.display = "none"; });
      p.addEventListener("click", () => scegliZona(st.zona === z.id ? "ITA" : z.id));
      p.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); scegliZona(st.zona === z.id ? "ITA" : z.id); } });
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
    if (!st.percorsi) return;
    st.percorsi.forEach((p, id) => { p.classList.toggle("attiva", id === st.zona); p.setAttribute("aria-pressed", String(id === st.zona)); });
    const p = st.percorsi.get(st.zona); if (p) p.parentNode.appendChild(p);
    const box = $("minimappa-zone"); if (box) box.classList.toggle("tutta-italia", st.zona === "ITA");
  }
  function scegliZona(id) {
    if (!st.ix.zone.some((z) => z.id === id)) id = "ITA";
    st.zona = id;
    $("zona-scelta").textContent = nomeZona();
    $("torna-italia").hidden = id === "ITA";
    evidenzia(); indirizzo(); calcola();
  }

  // ------------------------------------------------------------------ comandi e avvio
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
  }
  async function avvio() {
    try { st.ix = await json("indice.json"); } catch {
      stato("I dati di Terna non sono ancora disponibili su questo server (li prepara il worker una volta al giorno).", true);
      return;
    }
    st.mesi = st.ix.mesi.map((m) => ({ ...m, t0: Date.parse(m.inizio) }));
    if (!st.mesi.length) { stato("Nessun dato disponibile.", true); return; }
    const ult = st.mesi[st.mesi.length - 1];
    st.primoGiorno = dataIso(st.mesi[0].t0);
    st.ultimoGiorno = dataIso(ult.t0 + (ult.n - 1) * Q);
    st.passoFonti60 = (t) => { const m = st.mesi.find((x) => t >= x.t0 && t < x.t0 + x.n * Q); return m && m.passo_fonti === 60; };
    const q = new URLSearchParams(location.search);
    const z = (q.get("zona") || "").toUpperCase();
    st.zona = st.ix.zone.some((x) => x.id === z) ? z : "ITA";
    st.passo = q.get("passo") === "60" ? 60 : 15;
    [st.da, st.a] = periodoValido(q.get("da"), q.get("a"));
    $("carichi-quarti").checked = st.passo === 15;
    $("zona-scelta").textContent = nomeZona();
    $("torna-italia").hidden = st.zona === "ITA";
    scriviDate();
    const date = () => { [st.da, st.a] = periodoValido($("carichi-da").value || st.da, $("carichi-a").value || st.a); scriviDate(); indirizzo(); calcola(); };
    $("carichi-da").addEventListener("change", date);
    $("carichi-a").addEventListener("change", date);
    $("ultimi-12").addEventListener("click", ultimi12);
    $("carichi-quarti").addEventListener("change", (e) => { st.passo = e.target.checked ? 15 : 60; indirizzo(); calcola(); });
    $("torna-italia").addEventListener("click", () => scegliZona("ITA"));
    window.EUGENIO_CARICHI = { stato: st, scegliZona, calcola };    // per le prove
    indirizzo();
    minimappa();
    await calcola();
  }
  avvio().catch((e) => stato(`Errore: ${e.message}`, true)).finally(() => { st.pronto = true; });

  // collegamento a questa simulazione (20/11/2026, collegamento.js): l'avvio legge già ?zona=&da=&a=&passo= (Italia =
  // niente zona), quindi basta dire al modulo quali sono i parametri e quando la pagina è pronta.
  if (window.EUGENIO_COLLEGAMENTO) window.EUGENIO_COLLEGAMENTO.registra({
    regione: false,
    chiavi: ["zona", "da", "a", "passo"],
    principali: ["zona", "da", "a", "passo"],
    pronto: () => st.pronto,
    leggi: () => (st.pronto && st.ix && st.da
      ? { zona: st.zona === "ITA" ? null : st.zona, da: st.da, a: st.a, passo: String(st.passo) } : null),
  });
})();
