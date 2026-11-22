"use strict";
// Statistiche › «Suolo e aree agricole» (suolo.html, 22/11/2026, richiesta di Paolo). Stessa struttura di elettricita.js:
// mappa MapLibre dell'Italia con le regioni bianche e, in ogni regione, un istogramma (immagini della mappa, così finiscono
// anche nell'immagine scaricata), scalato sul valore più alto fra tutte le regioni (o le province della regione scelta).
// Un clic su una regione (mappa grande o piccola) la sceglie e gli istogrammi passano alle province; un secondo clic torna
// all'Italia. Con una regione scelta si può aprire una provincia (menu nel pannello o clic sulla sua barra nel grafico delle
// province): con «Suolo» la mappa colora i suoi comuni per percentuale di suolo consumato.
// Tre scelte (decisione di Paolo): Suolo (grandezze di stato, barre affiancate, unità ha / % / m² per abitante), Consumi
// (nuovo consumo per causa, barre impilate, più la barra «di cui su suolo agricolo» dove c'è l'incrocio di EuGEnio),
// Colture (superfici per famiglia, barre impilate).
// (22/11/2026, 01:00, Paolo) periodo con due indicatori: all'apertura tutti e due sull'ultimo anno. Flussi (Consumi) sommati
// sui periodi fra la carta dell'anno iniziale e quella dell'anno finale (con un anno solo: il periodo che finisce in
// quell'anno, anche lungo: 2006–2012, 2012–2015); stati (Suolo, Colture) all'anno finale, con la variazione dall'anno
// iniziale nel riquadretto e in tabella e, sugli istogrammi, un trattino nero al valore dell'anno iniziale.
// Dati: dati/suolo/italia.json e RR.json (fase 16, costruiti dal worker con i dati ISPRA/SNPA, ISTAT e Copernicus).
// Si scarica solo l'immagine della mappa (esporta_mappa.js), come nelle altre pagine delle statistiche.
(function () {
  const $ = (id) => document.getElementById(id);
  const box = $("mappa-suolo");
  const C = window.EUGENIO_CONFINI, R = window.EUGENIO_RETE, G = window.EUGENIO_GRAFICI;
  if (!box || !window.maplibregl || !C) return;
  const E = window.EUGENIO;
  const V = (document.currentScript && /[?&]v=([\w-]+)/.exec(document.currentScript.src) || [])[1] || "";
  const conV = (u) => (V ? `${u}?v=${V}` : u);
  const NS = "http://www.w3.org/2000/svg";
  const vuota = () => ({ type: "FeatureCollection", features: [] });
  const css = (n, r = "#888") => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || r;
  function h(tag, cls, t) { const e = document.createElement(tag); if (cls) e.className = cls; if (t !== undefined && t !== null) e.textContent = t; return e; }
  function s(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if ((k === "fill" || k === "stroke") && typeof v === "string" && v.startsWith("var(")) e.style.setProperty(k, v); else e.setAttribute(k, v);
    }
    if (parent) parent.appendChild(e);
    return e;
  }
  // numeri all'italiana, sempre con il punto delle migliaia (numeri.js)
  const num = (v, d = 0) => EUGENIO_NUMERI.formato(v, d);
  const dec = (v) => (v === null || v === undefined ? 0 : Math.abs(v) >= 100 ? 0 : Math.abs(v) >= 1 ? 1 : 2);
  const segno = (v, d) => (v === null || v === undefined ? "–" : (v > 0 ? "+" : v < 0 ? "−" : "") + num(Math.abs(v), d));
  function messaggio(id, t, errore = false) { const m = $(id); if (!m) return; m.textContent = t; m.classList.toggle("errore", errore); }
  const somma = (arr) => (arr || []).reduce((t, v) => t + (v || 0), 0);

  const MODI = {
    suolo: { nome: "Suolo", lungo: "Suolo consumato e aree agricole", tipo: "stato" },
    consumi: { nome: "Consumi", lungo: "Consumo di suolo per causa", tipo: "flusso" },
    colture: { nome: "Colture", lungo: "Superfici coltivate per famiglia", tipo: "stato" },
  };
  const UNITA = { ha: "ha", pct: "% del territorio", m2ab: "m²/ab" };
  const st = { mappa: null, it: null, prov: new Map(), modo: "suolo", unita: "ha", inizio: null, fine: null, regione: null,
    provincia: null, giro: 0, img: new Set(), sugg: null };
  const D = () => st.it;
  const voci = (g) => D().voci[g] || [];
  const NC = () => D().censimento_voci || 2;            // prime voci di «suolo»: censimento 2020 (SAU, non utilizzata)
  const anniDi = (modo) => (modo === "colture" ? D().anni.colture : D().anni.suolo);
  const anniFlusso = () => D().anni.consumi;
  // anni dei flussi del periodo: tra la carta di inizio e quella di fine; con un anno solo, il periodo che finisce lì
  const flussiDelPeriodo = (a, b) => (a < b ? anniFlusso().filter((t) => t > a && t <= b) : anniFlusso().includes(b) ? [b] : []);
  const periodoDi = (t) => D().periodi[String(t)] || [t - 1, t];
  const testoPeriodo = () => (st.inizio === st.fine ? String(st.fine) : `${st.inizio}–${st.fine}`);
  function testoFlussi(anni) {
    if (!anni.length) return "nessun periodo";
    return `${periodoDi(anni[0])[0]}–${anni[anni.length - 1]}`;
  }

  // ------------------------------------------------------------------ dati
  async function carica(u) { const r = await fetch(conV(u)); if (!r.ok) throw new Error(`${u}: ${r.status}`); return r.json(); }
  async function province(cod) {
    if (!st.prov.has(cod)) st.prov.set(cod, carica(`dati/suolo/${cod}.json`));
    return st.prov.get(cod);
  }
  const statoDi = (x, g, a) => (x && x[g] && x[g][String(a)]) || null;
  const popDi = (x, a) => (x && x.pop && (x.pop[String(a)] || x.pop[String(D().anni.suolo[D().anni.suolo.length - 1])])) || null;
  // conversione delle superfici (solo «Suolo»)
  function inUnita(v, x, a) {
    if (v === null || v === undefined) return null;
    if (st.modo !== "suolo" || st.unita === "ha") return v;
    if (st.unita === "pct") return x.sup ? 100 * v / x.sup : null;
    const p = popDi(x, a); return p ? v * 1e4 / p : null;
  }
  const unitaTesto = () => (st.modo === "suolo" ? UNITA[st.unita] : "ha");
  const decU = (v) => (st.modo === "suolo" && st.unita === "pct" ? (Math.abs(v || 0) >= 10 ? 1 : 2) : dec(v));
  // valori dell'unità x nel periodo scelto: { v (voci), prima (stati all'inizio, o null), bil, agr, anni (flussi) }
  function valori(x, a = st.inizio, b = st.fine, modo = st.modo) {
    if (!x) return null;
    if (modo === "consumi") {
      const anni = flussiDelPeriodo(a, b);
      let v = null, bil = null, agr = null, agrOk = anni.length > 0;
      for (const t of anni) {
        const f = statoDi(x, "consumi", t), q = statoDi(x, "bilancio", t), g = statoDi(x, "agricolo", t);
        if (f) v = v ? v.map((y, i) => y + f[i]) : [...f];
        if (q) bil = bil ? bil.map((y, i) => y + q[i]) : [...q];
        if (g && agrOk) agr = agr ? agr.map((y, i) => y + g[i]) : [...g]; else agrOk = false;
      }
      return v ? { v, bil, agr: agrOk ? agr : null, anni } : null;
    }
    const g = modo, vb = statoDi(x, g, b);
    if (!vb) return null;
    const conv = (arr, anno) => arr.map((y) => inUnita(y, x, anno));
    const va = a < b ? statoDi(x, g, a) : null;
    return { v: modo === "suolo" ? conv(vb, b) : vb, prima: va ? (modo === "suolo" ? conv(va, a) : va) : null, ha: vb };
  }

  // ------------------------------------------------------------------ istogrammi come immagini della mappa
  const PR = Math.min(2, window.devicePixelRatio || 1);
  const DOPPIO = 2;
  const AGRICOLO = "#1b5e20";
  function tela(w, hgt) { const f = PR * DOPPIO, c = document.createElement("canvas"); c.width = Math.round(w * f); c.height = Math.round(hgt * f); const k = c.getContext("2d"); k.scale(f, f); return [c, k]; }
  const tratto = (k, x, y, w) => { k.fillStyle = "#111"; k.fillRect(x - 1.5, y - 0.8, w + 3, 1.6); };
  // barre affiancate (Suolo): base in basso, contorno scuro sottile; trattino nero al valore iniziale del periodo
  function barreAffiancate(vals, prima, colori, max, alto) {
    const n = vals.length, lb = st.regione ? 7 : 5, gap = 1, W = n * (lb + gap) + 5, Ht = alto + 3, y0 = alto + 1;
    const [c, k] = tela(W, Ht);
    vals.forEach((v, i) => {
      const x = 2.5 + i * (lb + gap);
      if (v > 0) {
        const hh = Math.max(1, v / max * alto);
        k.fillStyle = colori[i]; k.fillRect(x, y0 - hh, lb, hh);
        k.strokeStyle = "rgba(0,0,0,0.55)"; k.lineWidth = 0.6; k.strokeRect(x + 0.3, y0 - hh + 0.3, lb - 0.6, hh - 0.6);
      }
      if (prima && prima[i] > 0) tratto(k, x, y0 - Math.max(1, prima[i] / max * alto), lb);
    });
    k.strokeStyle = "#222"; k.lineWidth = 1; k.beginPath(); k.moveTo(0, y0 + 0.5); k.lineTo(W, y0 + 0.5); k.stroke();
    return { c };
  }
  // colonna impilata (Consumi, Colture) e, accanto, la colonna «di cui su suolo agricolo»
  function colonnaImpilata(vals, colori, max, alto, primaTot, agr) {
    const lo = st.regione ? 14 : 11, W = lo + (agr !== null && agr !== undefined ? lo * 0.6 + 2 : 0) + 6, Ht = alto + 3, y0 = alto + 1, x0 = 3;
    const [c, k] = tela(W, Ht), sc = (v) => Math.max(0, v) / max * alto;
    let y = y0;
    vals.forEach((v, i) => { if (!(v > 0)) return; const hh = sc(v); k.fillStyle = colori[i]; k.fillRect(x0, y - hh, lo, hh); y -= hh; });
    if (y < y0) { k.strokeStyle = "rgba(0,0,0,0.55)"; k.lineWidth = 0.6; k.strokeRect(x0 + 0.3, y + 0.3, lo - 0.6, y0 - y - 0.6); }
    if (primaTot > 0) tratto(k, x0, y0 - sc(primaTot), lo);
    if (agr > 0) {
      const la = lo * 0.6, hh = Math.max(1, sc(agr)), xa = x0 + lo + 2;
      k.fillStyle = AGRICOLO; k.fillRect(xa, y0 - hh, la, hh);
      k.strokeStyle = "rgba(0,0,0,0.6)"; k.lineWidth = 0.6; k.strokeRect(xa + 0.3, y0 - hh + 0.3, la - 0.6, hh - 0.6);
    }
    k.strokeStyle = "#222"; k.lineWidth = 1; k.beginPath(); k.moveTo(0, y0 + 0.5); k.lineTo(W, y0 + 0.5); k.stroke();
    return { c };
  }
  function immagine(id, disegno) {
    const m = st.mappa, k = disegno.c.getContext("2d"), dati = k.getImageData(0, 0, disegno.c.width, disegno.c.height);
    if (m.hasImage(id)) m.removeImage(id);
    m.addImage(id, { width: disegno.c.width, height: disegno.c.height, data: dati.data }, { pixelRatio: PR });
    st.img.add(id);
  }
  // scala comune: tutte le unità e, per gli stati, tutti gli anni; per i flussi tutti i periodi di un anno (non quelli lunghi,
  // 2006–2012 e 2012–2015, che schiaccerebbero le barre annuali) e il periodo scelto
  function massimo(unita) {
    let mx = 0;
    const impila = st.modo !== "suolo";
    const prova = (r) => { if (!r) return; const tot = impila ? somma(r.v.filter((y) => y > 0)) : Math.max(0, ...r.v.map((y) => y || 0));
      mx = Math.max(mx, tot, r.agr ? somma(r.agr) : 0); };
    const annuali = () => anniFlusso().filter((t) => periodoDi(t)[1] - periodoDi(t)[0] === 1);
    for (const x of unita) {
      if (st.modo === "consumi") { for (const t of annuali()) prova(valori(x, t, t)); prova(valori(x)); }
      else for (const a of anniDi(st.modo)) prova(valori(x, a, a));
    }
    return mx || 1;
  }

  async function disegnaBarre() {
    const m = st.mappa, mio = ++st.giro;
    let unitaMappa = D().regioni;
    if (st.regione) {
      const p = await province(st.regione);
      if (mio !== st.giro) return;
      unitaMappa = p.province.filter((x) => st.modo !== "colture" || x.colture);
    }
    const max = massimo(unitaMappa), features = [], alto = st.regione ? 90 : 70, colori = voci(st.modo).map((q) => q.colore);
    for (const x of unitaMappa) {
      const id = `su-${x.cod}`.replace(/[^\w-]/g, "_"), r = valori(x);
      if (!r) continue;
      if (st.provincia === x.cod && st.modo === "suolo") continue;       // i suoi comuni colorati restano scoperti
      let dis;
      if (st.modo === "suolo") dis = barreAffiancate(r.v.map((y) => y || 0), r.prima, colori, max, alto);
      else {
        if (!(somma(r.v) > 0) && !(r.agr && somma(r.agr) > 0)) continue;
        dis = colonnaImpilata(r.v, colori, max, alto, r.prima ? somma(r.prima) : 0, r.agr ? somma(r.agr) : null);
      }
      immagine(id, dis);
      features.push({ type: "Feature", geometry: { type: "Point", coordinates: [x.lon, x.lat] }, properties: { img: id, nome: x.nome, cod: x.cod } });
    }
    let msg = "";
    if (st.modo === "consumi" && !flussiDelPeriodo(st.inizio, st.fine).length) msg = `Nessun consumo da mostrare: il ${st.fine} è la prima carta di ISPRA. Sposta l'indicatore finale.`;
    else if (st.regione === "20" && st.modo === "colture") msg = "In Sardegna le province delle stime ISTAT non sono confrontabili: c'è solo il dato regionale.";
    else if (st.provincia && st.modo !== "suolo") msg = "La mappa dei comuni c'è con «Suolo».";
    messaggio("messaggio-mappa", msg);
    m.getSource("su-barre").setData({ type: "FeatureCollection", features });
    st.barre = features.length;
    await disegnaComuni();
    legenda();
    chiudiAttribuzione();
  }
  function chiudiAttribuzione() {
    const t = () => box.querySelectorAll(".maplibregl-compact-show").forEach((x) => x.classList.remove("maplibregl-compact-show"));
    t(); st.mappa.once("idle", t);
  }

  // ------------------------------------------------------------------ comuni della provincia scelta (Suolo, % consumato)
  const CLASSI = [[2, "#fff5d6"], [5, "#fdd99b"], [10, "#f9a65a"], [20, "#e6603c"], [40, "#b3261e"], [Infinity, "#6b0f1a"]];
  const coloreClasse = (p) => (CLASSI.find(([lim]) => p < lim) || CLASSI[CLASSI.length - 1])[1];
  let comuniGeo = null;
  function datiComune(p, ist) {
    const c = p.comuni, i = c.anni.indexOf(st.fine), j = c.anni.indexOf(st.inizio), riga = (st.comuniIndice || {})[ist];
    if (!riga || i < 0) return null;
    const cons = riga[4][i], prima = st.inizio < st.fine && j >= 0 ? riga[4][j] : null;
    return { nome: riga[1], sup: riga[3], cons, pct: riga[3] ? 100 * cons / riga[3] : null, prima, netto: riga[5][i] };
  }
  async function disegnaComuni() {
    const m = st.mappa, src = m.getSource("su-comuni");
    if (!src) return;
    if (!st.provincia || st.modo !== "suolo") { src.setData(vuota()); st.comuniColorati = 0; return; }
    const p = await province(st.regione);
    if (!comuniGeo || comuniGeo.cod !== st.regione) comuniGeo = { cod: st.regione, fc: await C.comuniRegione(st.regione) };
    st.comuniIndice = Object.fromEntries(p.comuni.dati.filter((r) => r[2] === st.provincia).map((r) => [r[0], r]));
    const feats = [];
    for (const f of comuniGeo.fc.features) {
      const d = datiComune(p, f.properties.istat);
      if (!d || d.pct === null) continue;
      feats.push({ type: "Feature", geometry: f.geometry, properties: { istat: f.properties.istat, nome: d.nome, colore: coloreClasse(d.pct) } });
    }
    src.setData({ type: "FeatureCollection", features: feats });
    st.comuniColorati = feats.length;
  }

  // ------------------------------------------------------------------ mappa
  async function avvio() {
    window.EUGENIO_SUOLO = { stato: st, scegliRegione, togliRegione, scegliProvincia, cambiaModo, periodo, valori };   // per le prove
    try { st.it = await carica("dati/suolo/italia.json"); } catch (e) {
      messaggio("messaggio-mappa", "I dati del suolo non sono ancora disponibili su questo server (li prepara il worker, controllo una volta al mese).", true);
      st.pronto = true;
      return;
    }
    preparaComandi();
    const m = new window.maplibregl.Map({ container: box, center: [12.4, 42.1], zoom: 4.9, maxZoom: 13, minZoom: 4, attributionControl: false,
      canvasContextAttributes: { preserveDrawingBuffer: true },
      style: { version: 8, sources: {}, layers: [{ id: "sfondo", type: "background", paint: { "background-color": css("--carta", "#f4f4f4") } }] } });
    st.mappa = m;
    m.addControl(new window.maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.addControl(new window.maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    m.addControl(new window.maplibregl.AttributionControl({ compact: true }), "bottom-right");
    await new Promise((ok) => m.on("load", ok));
    document.addEventListener("eugenio:ridimensiona", () => m.resize());
    try { await C.aggiungi(m, { clic: false }); } catch { messaggio("messaggio-mappa", "Confini non disponibili.", true); }
    const prima = m.getLayer("confini-comuni-clic") ? "confini-comuni-clic" : undefined;
    m.addLayer({ id: "su-fondo", type: "fill", source: "confini-regioni", paint: { "fill-color": "#ffffff", "fill-opacity": 1 } }, prima);
    m.addSource("su-comuni", { type: "geojson", data: vuota() });
    m.addLayer({ id: "su-comuni", type: "fill", source: "su-comuni", paint: { "fill-color": ["get", "colore"], "fill-opacity": 0.9 } }, prima);
    m.addLayer({ id: "su-comuni-linee", type: "line", source: "su-comuni", paint: { "line-color": "#6b5a4a", "line-width": 0.5 } }, prima);
    m.addSource("su-province", { type: "geojson", data: vuota() });
    m.addLayer({ id: "su-province-clic", type: "fill", source: "su-province", paint: { "fill-color": "#000", "fill-opacity": 0 } });
    m.addLayer({ id: "su-province-linee", type: "line", source: "su-province", paint: { "line-color": "#555", "line-width": 0.8 } });
    m.addLayer({ id: "su-provincia-scelta", type: "line", source: "su-province", filter: ["==", ["get", "cod"], "-"],
      paint: { "line-color": css("--primario", "#c4572e"), "line-width": 2.4 } });
    m.addSource("su-barre", { type: "geojson", data: vuota(), attribution: "ISPRA/SNPA, ISTAT, Copernicus (CC BY 4.0); elaborazione EuGEnio" });
    m.addLayer({ id: "su-barre", type: "symbol", source: "su-barre", layout: { "icon-image": ["get", "img"], "icon-allow-overlap": true,
      "icon-ignore-placement": true, "icon-anchor": "bottom" } });
    if (m.getLayer("confini-regioni-clic")) m.setLayerZoomRange("confini-regioni-clic", 0, 24);
    if (R && R.suggerimento) st.sugg = R.suggerimento(m, () => ["su-barre", "su-comuni", "su-province-clic", "confini-regioni-clic"], suggerimento);
    m.on("click", clic);
    for (const id of ["strato-barre", "strato-fondo", "strato-ortofoto"]) $(id).addEventListener("change", strati);
    if (window.EUGENIO_RIGHELLO) window.EUGENIO_RIGHELLO.aggiungi(m, { dove: $("strati-suolo") });
    ortofoto(m);
    if (window.EUGENIO_ESPORTA) window.EUGENIO_ESPORTA.pulsanti($("scarica-mappa"), m, opzioniImmagine, $("messaggio-immagine"));
    if (E) {
      E.suRegione = (cod) => scegliRegione(cod);
      E.suStessaRegione = (cod) => (st.regione === cod ? togliRegione() : scegliRegione(cod));
      if (E.evidenziaPiccola) E.evidenziaPiccola(null);
    }
    strati();
    m.fitBounds([[C.ITALIA[0], C.ITALIA[1]], [C.ITALIA[2], C.ITALIA[3]]], { padding: margini(10), duration: 0 });
    const q = new URLSearchParams(location.search);
    if (q.get("modo") && MODI[q.get("modo")]) cambiaModo(q.get("modo"), false);
    if (q.get("unita") && UNITA[q.get("unita")]) scegliUnita(q.get("unita"), false);
    applicaPeriodo(+q.get("inizio"), +q.get("fine"));
    const reg = q.get("regione");
    if (/^\d\d$/.test(reg || "") && q.get("vista") !== "italia" && D().regioni.some((r) => r.cod === reg)) {
      await scegliRegione(reg, /^\d{3}$/.test(q.get("provincia") || "") ? q.get("provincia") : null);
    } else { await disegnaBarre(); pannello(); }
    st.pronto = true;
    document.addEventListener("eugenio:aspetto", () => { m.setPaintProperty("sfondo", "background-color", css("--carta", "#f4f4f4")); pannello(); });
  }
  function margini(p) {
    const alto = Math.round((st.regione ? 90 : 70) * DOPPIO * 0.85), H = box.clientHeight || 600;
    return { top: Math.max(p, Math.min(alto, Math.round(H * 0.4))), bottom: p, left: p, right: p };
  }
  function strati() {
    const m = st.mappa, vis = (id, on) => { if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", on ? "visible" : "none"); };
    vis("su-barre", $("strato-barre").checked);
    vis("su-fondo", $("strato-fondo").checked);
    ["contesto", "ortofoto"].forEach((id) => vis(id, $("strato-ortofoto").checked));
    if ($("strato-ortofoto").checked && orto.fonti.length) sceltaOrto();
    attribuzioneOrto();
    legenda();
  }
  function clic(e) {
    const m = st.mappa;
    const r = m.queryRenderedFeatures(e.point, { layers: ["confini-regioni-clic"].filter((id) => m.getLayer(id)) })[0];
    const cod = r ? r.properties.cod : null;
    if (!cod) return;
    if (st.regione === cod) togliRegione(); else scegliRegione(cod);
  }
  const riquadroFC = (fc) => { let w = 180, so = 90, ea = -180, n = -90;
    for (const f of fc.features) for (const p of f.geometry.coordinates) for (const [x, y] of p[0]) { w = Math.min(w, x); ea = Math.max(ea, x); so = Math.min(so, y); n = Math.max(n, y); }
    return [w, so, ea, n]; };
  async function scegliRegione(cod, provincia = null) {
    if (!D().regioni.some((r) => r.cod === cod)) return;
    st.regione = cod; st.provincia = null;
    if (E && E.seleziona) E.seleziona(cod);
    const m = st.mappa;
    if (m.getLayer("confini-regione-scelta")) m.setFilter("confini-regione-scelta", ["==", ["get", "cod"], cod]);
    let fc = vuota();
    try { fc = await C.provinceRegione(cod); } catch { /* senza confini delle province */ }
    m.getSource("su-province").setData(fc);
    st.provinceGeo = fc;
    const p = await province(cod);
    preparaProvince(p);
    if (provincia && p.province.some((x) => x.cod === provincia)) return scegliProvincia(provincia);
    const b = await C.riquadroRegione(cod);
    if (b && st.regione === cod) m.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: margini(30), duration: 600 });
    evidenziaProvincia();
    aggiornaIndirizzo();
    await disegnaBarre();
    pannello();
  }
  async function scegliProvincia(cod) {
    if (!st.regione) return;
    st.provincia = cod || null;
    $("provincia-suolo").value = st.provincia || "";
    evidenziaProvincia();
    const m = st.mappa;
    const f = st.provinceGeo && st.provinceGeo.features.filter((x) => x.properties.cod === st.provincia);
    if (st.provincia && f && f.length) { const b = riquadroFC({ features: f }); m.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: margini(30), duration: 600 }); }
    else { const b = await C.riquadroRegione(st.regione); if (b) m.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: margini(30), duration: 600 }); }
    aggiornaIndirizzo();
    await disegnaBarre();
    pannello();
  }
  function evidenziaProvincia() {
    const m = st.mappa;
    if (m && m.getLayer("su-provincia-scelta")) m.setFilter("su-provincia-scelta", ["==", ["get", "cod"], st.provincia || "-"]);
  }
  async function togliRegione() {
    st.regione = null; st.provincia = null;
    if (E && E.evidenziaPiccola) E.evidenziaPiccola(null);
    const m = st.mappa;
    if (m.getLayer("confini-regione-scelta")) m.setFilter("confini-regione-scelta", ["==", ["get", "cod"], ""]);
    m.getSource("su-province").setData(vuota());
    evidenziaProvincia();
    m.fitBounds([[C.ITALIA[0], C.ITALIA[1]], [C.ITALIA[2], C.ITALIA[3]]], { padding: margini(10), duration: 600 });
    aggiornaIndirizzo();
    await disegnaBarre();
    pannello();
  }
  function preparaProvince(p) {
    const sel = $("provincia-suolo");
    sel.innerHTML = "";
    sel.appendChild(new Option("Tutte le province", ""));
    [...p.province].sort((a, b) => a.nome.localeCompare(b.nome, "it")).forEach((x) => sel.appendChild(new Option(x.nome, x.cod)));
    sel.value = st.provincia || "";
  }
  function aggiornaIndirizzo() {
    const u = new URL(location.href);
    if (st.regione) { u.searchParams.set("regione", st.regione); u.searchParams.delete("vista"); } else { u.searchParams.delete("regione"); u.searchParams.set("vista", "italia"); }
    if (st.provincia) u.searchParams.set("provincia", st.provincia); else u.searchParams.delete("provincia");
    u.searchParams.set("modo", st.modo);
    history.replaceState(null, "", u);
  }

  // ------------------------------------------------------------------ riquadretti
  let cacheProv = null;
  function suggerimento(f) {
    const p = f.properties || {}, id = f.layer.id;
    if (id === "su-comuni" && cacheProv) {
      const d = datiComune(cacheProv, p.istat);
      if (!d) return null;
      const r = [[coloreClasse(d.pct), `Suolo consumato: ${num(d.cons, dec(d.cons))} ha (${num(d.pct, 1)} % del territorio)`]];
      if (d.prima !== null) r.push([null, `Variazione dal ${st.inizio}: ${segno(d.cons - d.prima, 2)} ha`]);
      else if (d.netto !== null && d.netto !== undefined) r.push([null, `Incremento netto ${testoFlussi(flussiDelPeriodo(st.fine, st.fine))}: ${segno(d.netto, 2)} ha`]);
      r.push([null, `Superficie del comune: ${num(d.sup)} ha`]);
      return { titolo: `${d.nome} – ${testoPeriodo()}`, righe: r, cursore: true };
    }
    let x = null;
    if (st.regione) {
      if (id === "confini-regioni-clic" && p.cod !== st.regione) x = D().regioni.find((r) => r.cod === p.cod);
      else if (cacheProv && cacheProv.regione === st.regione && (id === "su-barre" || id === "su-province-clic"))
        x = cacheProv.province.find((q) => q.cod === p.cod) || null;
      else if (id === "confini-regioni-clic") x = D().regioni.find((r) => r.cod === p.cod);
    } else if (id === "su-barre" || id === "confini-regioni-clic") x = D().regioni.find((r) => r.cod === p.cod);
    if (!x) return null;
    const righe = righeValori(x);
    if (!st.regione) righe.push([null, "clic per le province"]);
    else if (x.cod === st.regione) righe.push([null, "clic per tornare all'Italia"]);
    else if (D().regioni.includes(x)) righe.push([null, "clic per scegliere questa regione"]);
    return { titolo: `${x.nome} – ${st.modo === "consumi" ? testoFlussi(flussiDelPeriodo(st.inizio, st.fine)) : testoPeriodo()}`, righe, cursore: true };
  }
  function righeValori(x) {
    const r = valori(x), u = unitaTesto(), vv = voci(st.modo);
    if (!r) return [st.modo === "colture" && x.cod && x.cod.length === 3 ? "nessun dato per le province di questa regione" : "nessun dato per questo periodo"];
    if (st.modo === "suolo") {
      const out = vv.map((q, i) => [q.colore, `${q.nome}: ${num(r.v[i], decU(r.v[i]))} ${u}${r.prima && r.prima[i] !== null && i >= NC()
        ? ` (${segno(r.v[i] - r.prima[i], decU(r.v[i] - r.prima[i]))} dal ${st.inizio})` : ""}`]).filter((_, i) => r.v[i] !== null);
      const rev = x.rev && x.rev[String(st.fine)];
      if (rev !== undefined) out.push([null, `${st.fine} rev: nell'edizione successiva ISPRA ha rivisto il suolo consumato in ${num(rev)} ha`]);
      return out;
    }
    if (st.modo === "consumi") {
      const out = vv.map((q, i) => [q.colore, `${q.nome}: ${num(r.v[i], dec(r.v[i]))} ha`]).filter((_, i) => r.v[i]);
      if (r.bil) out.push([null, `Consumo lordo: ${num(r.bil[0], dec(r.bil[0]))} ha · ripristini ${num(r.bil[1], dec(r.bil[1]))} ha · netto ${segno(r.bil[2], dec(r.bil[2]))} ha`]);
      if (r.agr) out.push([AGRICOLO, `di cui su suolo agricolo (stima EuGEnio): ${num(somma(r.agr), dec(somma(r.agr)))} ha (${num(100 * somma(r.agr) / (somma(r.v) || 1))} %)`]);
      else if (D().anni.agricolo.length) out.push([null, `suolo agricolo: stima solo per ${D().anni.agricolo.map((t) => testoFlussi([t])).join(", ")}`]);
      const anni = r.anni.length ? periodoDi(r.anni[r.anni.length - 1])[1] - periodoDi(r.anni[0])[0] : 1;
      if (anni > 1) out.push([null, `Media annua: ${num(somma(r.v) / anni, 0)} ha (${anni} anni)`]);
      return out;
    }
    const out = vv.map((q, i) => [q.colore, `${q.nome}: ${num(r.v[i])} ha`]).filter((_, i) => r.v[i]);
    out.push([null, `Totale: ${num(somma(r.v))} ha${r.prima ? ` (${segno(somma(r.v) - somma(r.prima))} dal ${st.inizio})` : ""}`]);
    return out;
  }

  // ------------------------------------------------------------------ comandi: grandezza, unità, periodo
  function preparaComandi() {
    document.querySelectorAll("#modo-suolo [data-modo]").forEach((b) => b.addEventListener("click", () => cambiaModo(b.dataset.modo, true)));
    document.querySelectorAll("#unita-suolo [data-unita]").forEach((b) => b.addEventListener("click", () => scegliUnita(b.dataset.unita, true)));
    const i0 = $("anno-inizio"), i1 = $("anno-fine");
    const muovi = (chi) => {
      let a = +i0.value, b = +i1.value;
      if (a > b) { if (chi === i0) b = a; else a = b; i0.value = a; i1.value = b; }
      const anni = anniDi(st.modo); st.inizio = anni[a]; st.fine = anni[b]; scriviPeriodo();
    };
    for (const el of [i0, i1]) {
      el.addEventListener("input", () => muovi(el));
      el.addEventListener("change", async () => { muovi(el); await disegnaBarre(); pannello(); });
    }
    $("torna-italia").addEventListener("click", () => togliRegione());
    $("provincia-suolo").addEventListener("change", (e) => scegliProvincia(e.target.value));
    cambiaModo("suolo", false);
  }
  // posizione dei cursori e testo del periodo; il cursore più in alto è quello che si prende per primo vicino all'altro
  function scriviPeriodo() {
    const anni = anniDi(st.modo), i0 = $("anno-inizio"), i1 = $("anno-fine"), n = Math.max(1, anni.length - 1);
    i0.value = anni.indexOf(st.inizio); i1.value = anni.indexOf(st.fine);
    $("cursore-doppio").style.setProperty("--da", `${100 * i0.value / n}%`);
    $("cursore-doppio").style.setProperty("--a", `${100 * i1.value / n}%`);
    i0.style.zIndex = +i0.value === n ? 3 : 1; i1.style.zIndex = 2;
    i0.setAttribute("aria-valuetext", String(st.inizio)); i1.setAttribute("aria-valuetext", String(st.fine));
    $("periodo-scelto").textContent = st.modo === "consumi" ? `${testoPeriodo()} (consumi ${testoFlussi(flussiDelPeriodo(st.inizio, st.fine))})` : testoPeriodo();
  }
  // periodo valido per la grandezza: anni della lista, inizio ≤ fine; predefinito l'ultimo anno per tutti e due
  function applicaPeriodo(a, b) {
    const anni = anniDi(st.modo), ult = anni[anni.length - 1];
    const vicino = (x) => (anni.includes(x) ? x : anni.reduce((p, q) => (Math.abs(q - x) < Math.abs(p - x) ? q : p), ult));
    b = b ? vicino(b) : ult; a = a ? vicino(a) : b;
    if (a > b) a = b;
    st.inizio = a; st.fine = b;
    const i0 = $("anno-inizio"), i1 = $("anno-fine");
    i0.min = i1.min = 0; i0.max = i1.max = anni.length - 1;
    $("anno-min").textContent = anni[0]; $("anno-max").textContent = ult;
    scriviPeriodo();
  }
  async function periodo(a, b) { applicaPeriodo(a, b); await disegnaBarre(); pannello(); }   // per le prove
  function cambiaModo(modo, ridisegna) {
    st.modo = modo;
    document.querySelectorAll("#modo-suolo [data-modo]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.modo === modo)));
    $("unita-suolo").hidden = modo !== "suolo";
    applicaPeriodo(st.inizio, st.fine);
    if (ridisegna && st.mappa) { aggiornaIndirizzo(); disegnaBarre().then(pannello); }
  }
  function scegliUnita(u, ridisegna) {
    st.unita = u;
    document.querySelectorAll("#unita-suolo [data-unita]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.unita === u)));
    if (ridisegna && st.mappa) disegnaBarre().then(pannello);
  }
  // collegamento a questa simulazione: regione, provincia, vista e modo li scrive aggiornaIndirizzo(); qui periodo e unità
  if (window.EUGENIO_COLLEGAMENTO) window.EUGENIO_COLLEGAMENTO.registra({
    regione: false,
    chiavi: ["inizio", "fine", "unita"],
    principali: ["inizio", "fine"],
    pronto: () => st.pronto,
    leggi: () => (st.pronto && D() ? { inizio: st.inizio, fine: st.fine, unita: st.unita !== "ha" ? st.unita : null } : null),
    async applica(p) {
      if (!D()) return;
      const u = p.get("unita");
      if (u && UNITA[u] && u !== st.unita) scegliUnita(u, false);
      const a = +p.get("inizio"), b = +p.get("fine");
      if ((a && a !== st.inizio) || (b && b !== st.fine) || u) { applicaPeriodo(a, b); await disegnaBarre(); pannello(); }
    },
  });

  // ------------------------------------------------------------------ legenda e immagine
  function voceLegenda(L, colore, testo, bordo) {
    const sp = h("span"), i = h("i");
    i.style.background = colore; if (bordo) i.style.outline = "1px solid #555";
    sp.append(i, testo); L.appendChild(sp);
  }
  function legenda() {
    const L = $("legenda-suolo"); if (!L || !D()) return;
    L.innerHTML = "";
    voci(st.modo).forEach((v) => voceLegenda(L, v.colore, v.nome));
    if (st.modo === "consumi" && D().anni.agricolo.length) voceLegenda(L, AGRICOLO, "di cui su suolo agricolo (stima EuGEnio, barra accanto)");
    if (st.inizio < st.fine && st.modo !== "consumi") voceLegenda(L, "#111", `trattino: valore del ${st.inizio}`);
    const dove = st.regione ? "le province della regione" : "tutte le regioni";
    const nota = st.modo === "suolo" ? `Barre affiancate in ${unitaTesto()}, da sinistra nell'ordine della legenda, in scala con il valore più alto fra ${dove} in tutti gli anni; le voci del suolo consumato si sovrappongono.`
      : st.modo === "consumi" ? `Colonna impilata: nuovo consumo nel periodo per causa (ha), in scala con il valore più alto fra ${dove} (periodi di un anno e periodo scelto).`
        : `Colonna impilata: superfici coltivate per famiglia (ha), in scala con il valore più alto fra ${dove} in tutti gli anni.`;
    L.appendChild(h("span", "legenda-nota", nota));
    if (st.provincia && st.modo === "suolo") {
      const lim = [0, ...CLASSI.map(([l]) => l)];
      CLASSI.forEach(([l, c], i) => voceLegenda(L, c, `comuni: ${l === Infinity ? `oltre ${lim[i]}` : `${lim[i]}–${l}`} % consumato`, true));
    }
  }
  function opzioniImmagine() {
    if (!D()) return "Dati non ancora caricati.";
    const ro = righeOrto();
    if (ro === null) return `«${orto.fonte.nome}» è solo in consultazione dal vivo: per scaricare l'immagine spegni la casella «Ortofoto».`;
    const reg = st.regione ? D().regioni.find((r) => r.cod === st.regione) : null;
    const pr = st.provincia && cacheProv ? cacheProv.province.find((p) => p.cod === st.provincia) : null;
    const nome = pr ? pr.nome : reg ? reg.nome : "Italia";
    const dove = st.regione ? "tutte le province della regione" : "tutte le regioni";
    const leg = st.modo === "suolo" ? `Barre affiancate (${unitaTesto()}), da sinistra: ${voci("suolo").map((v) => v.nome.toLowerCase()).join(", ")}; scala comune a ${dove} e a tutti gli anni.${st.inizio < st.fine ? ` Trattino nero: valore del ${st.inizio}.` : ""}${pr ? " Comuni colorati per percentuale di suolo consumato." : ""}`
      : st.modo === "consumi" ? `Colonna impilata: nuovo consumo di suolo ${testoFlussi(flussiDelPeriodo(st.inizio, st.fine))} per causa (${voci("consumi").map((v) => v.nome.toLowerCase()).join(", ")}), ha.${valori(D().italia) && valori(D().italia).agr ? " Barra verde scura: di cui su suolo agricolo (stima EuGEnio: carta dei cambiamenti ISPRA × Carta di uso del suolo ISPRA 2023)." : ""}`
        : `Colonna impilata: superfici coltivate per famiglia (${voci("colture").map((v) => v.nome.toLowerCase()).join(", ")}), ha.${st.inizio < st.fine ? ` Trattino nero: totale del ${st.inizio}.` : ""}`;
    const righe = [leg, `Dati: ${D().fonte}.`, ...ro, C.ATTRIBUZIONE];
    const file = `suolo_${st.modo}_${testoPeriodo().replace("–", "-")}_${nome.toLowerCase().replace(/[^a-z0-9]+/g, "_")}`;
    return { titolo: `${MODI[st.modo].lungo} – ${nome} – ${st.modo === "consumi" ? testoFlussi(flussiDelPeriodo(st.inizio, st.fine)) : testoPeriodo()}`, righe, nome: file };
  }

  // ------------------------------------------------------------------ pannello di destra
  async function pannello() {
    if (!D()) return;
    const reg = st.regione ? D().regioni.find((r) => r.cod === st.regione) : null;
    let p = null;
    if (reg) { p = await province(reg.cod); cacheProv = p; }
    const pr = st.provincia && p ? p.province.find((x) => x.cod === st.provincia) : null;
    const unita = pr || reg || D().italia, nome = pr ? pr.nome : reg ? reg.nome : "Italia";
    $("titolo-vista").textContent = pr ? `${pr.nome} (${reg.nome})` : nome;
    $("torna-italia").style.display = reg ? "" : "none";
    $("blocco-scelta-provincia").hidden = !reg;
    cifre(unita, nome);
    $("titolo-andamento").textContent = `${MODI[st.modo].lungo} – ${nome}, anno per anno`;
    G.registra($("grafico-andamento"), (dest, mis) => graficoAndamento(dest, mis, unita), { titolo: $("titolo-andamento").textContent, adatta: true });
    const elenco = p ? p.province.filter((x) => valori(x)) : [];
    const conProv = reg && elenco.length > 0;
    $("blocco-province").hidden = !conProv;
    if (conProv) {
      $("titolo-province").textContent = `${MODI[st.modo].lungo} per provincia – ${st.modo === "consumi" ? testoFlussi(flussiDelPeriodo(st.inizio, st.fine)) : testoPeriodo()}`;
      G.registra($("grafico-province"), (dest, mis) => graficoUnita(dest, mis, elenco), { titolo: $("titolo-province").textContent, adatta: true });
    }
    const nota = $("nota-vista");
    nota.hidden = !(reg && !conProv);
    nota.textContent = reg && !conProv ? (st.modo === "colture" && reg.cod === "20" ? "In Sardegna le province delle stime ISTAT delle colture non sono confrontabili (mescolano le vecchie e le nuove): c'è solo il dato regionale." : "Nessun dato per le province in questo periodo.") : "";
    if (pr && st.modo === "suolo") tabellaComuni(p, pr);
    else tabella(reg ? elenco : D().regioni, reg || D().italia, reg ? "province" : "regioni", reg);
  }
  function cifre(x, nome) {
    const el = $("cifre-suolo"), b = st.fine;
    if (st.modo !== "suolo") { el.textContent = ""; return; }
    const v = statoDi(x, "suolo", b);
    if (!v) { el.textContent = ""; return; }
    const c = v[NC()], pop = popDi(x, b);
    el.textContent = `${nome}, ${b}: ${num(c)} ha di suolo consumato (${num(x.sup ? 100 * c / x.sup : null, 2)} % del territorio${pop ? `, ${num(c * 1e4 / pop)} m² per abitante` : ""}).`;
  }

  // assi e griglia comuni (come elettricita.js)
  function scala(max) {
    const p = 10 ** Math.floor(Math.log10(max || 1)), passi = [1, 2, 2.5, 5, 10].map((k) => k * p);
    const passo = passi.find((k) => max / k <= 5) || p * 10;
    return { passo, top: Math.ceil(max / passo) * passo || 1 };
  }
  function asseY(svg, sx, su, gi, W, H, min, max, unitaTesto2) {
    const Y = (v) => su + (H - su - gi) * (max - v) / (max - min || 1);
    const { passo } = scala(Math.max(Math.abs(max), Math.abs(min)));
    const cifre2 = passo >= 1 ? 0 : Math.min(3, (String(+passo.toFixed(6)).split(".")[1] || "").length);
    for (let i = Math.ceil(min / passo - 1e-9); i * passo <= max + 1e-9; i++) {
      const v = +(i * passo).toFixed(6);
      s("line", { x1: sx, x2: W - 6, y1: Y(v), y2: Y(v), stroke: v === 0 ? "var(--inchiostro)" : "var(--linea)", "stroke-width": v === 0 ? 1 : 0.6 }, svg);
      const t = s("text", { x: sx - 4, y: Y(v) + 4, "text-anchor": "end", "font-size": 11, fill: "var(--tenue)" }, svg); t.textContent = num(v, v === 0 ? 0 : cifre2);
    }
    const t = s("text", { x: 4, y: 11, "font-size": 11, fill: "var(--tenue)" }, svg); t.textContent = unitaTesto2;
    return Y;
  }
  function legendaHtml(dest, elementi) {
    const L = h("div", "legenda legenda-grafico");
    elementi.forEach(([c, t]) => voceLegenda(L, c, t));
    dest.appendChild(L);
  }
  // andamento anno per anno su un asse di anni di calendario: gli anni senza carta restano vuoti; i periodi lunghi dei
  // consumi sono barre larghe alte quanto la media annua; il periodo scelto è riquadrato
  function graficoAndamento(dest, mis, x) {
    const W = mis && mis.larghezza ? mis.larghezza : 560, H = mis && mis.riquadro ? mis.altezza : 260;
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": $("titolo-andamento").textContent }, dest);
    const sx = 56, gi = 22, su = 18;
    const anniTutti = st.modo === "colture" ? D().anni.colture : D().anni.suolo;
    const a0 = anniTutti[0], a1 = anniTutti[anniTutti.length - 1], nAnni = a1 - a0 + 1;
    const passo = (W - sx - 8) / nAnni, X = (anno) => sx + passo * (anno - a0 + 0.5);
    const vv = voci(st.modo), punti = [];
    let max = 0;
    const colonne = [];
    if (st.modo === "suolo") {
      // solo le voci del suolo consumato (SAU e non utilizzata sono del censimento, uguali in tutti gli anni)
      for (const a of D().anni.suolo) { const r = valori(x, a, a); if (r) { colonne.push({ a, r }); max = Math.max(max, ...r.v.slice(NC()).map((y) => y || 0)); } }
    } else if (st.modo === "consumi") {
      for (const t of anniFlusso()) { const r = valori(x, t, t); if (!r) continue; const [da, al] = periodoDi(t), n = al - da;
        colonne.push({ a: t, da, al, n, r }); max = Math.max(max, somma(r.v) / n, r.agr ? somma(r.agr) / n : 0); }
    } else {
      for (const a of D().anni.colture) { const r = valori(x, a, a); if (r) { colonne.push({ a, r }); max = Math.max(max, somma(r.v)); } }
    }
    if (!colonne.length) { s("text", { x: W / 2, y: H / 2, "text-anchor": "middle", "font-size": 12, fill: "var(--tenue)" }, svg).textContent = "Nessun dato"; return; }
    const Y = asseY(svg, sx, su, gi, W, H, 0, scala(max).top, st.modo === "consumi" ? "ha all'anno" : unitaTesto());
    // periodo scelto
    const sa = st.modo === "consumi" ? (st.inizio < st.fine ? st.inizio + 1 : periodoDi(st.fine)[0] + 1) : st.inizio;
    s("rect", { x: X(sa) - passo / 2, y: su, width: passo * (st.fine - sa + 1), height: H - su - gi, fill: "var(--primario)", "fill-opacity": 0.08, stroke: "var(--primario)", "stroke-width": 1.2 }, svg);
    for (const col of colonne) {
      const el = [], righe = [];
      if (st.modo === "suolo") {
        const ids = vv.slice(NC()), n = ids.length, lb = Math.max(1.2, passo * 0.8 / n);
        ids.forEach((q, j) => { const y = col.r.v[NC() + j]; if (!(y > 0)) return;
          el.push(s("rect", { x: X(col.a) - passo * 0.4 + j * lb, y: Y(y), width: lb, height: Y(0) - Y(y), fill: q.colore }, svg));
          righe.push([q.colore, `${q.nome}: ${num(y, decU(y))} ${unitaTesto()}`]); });
        const rev = x.rev && x.rev[String(col.a)];
        if (rev !== undefined) {
          s("text", { x: X(col.a), y: su - 4, "text-anchor": "middle", "font-size": 10, fill: "var(--tenue)" }, svg).textContent = "rev";
          righe.push([null, `rev: rivisto da ISPRA in ${num(rev)} ha`]);
        }
        punti.push({ x: X(col.a), titolo: String(col.a), elementi: el, righe });
      } else if (st.modo === "consumi") {
        const x0 = sx + passo * (col.da + 1 - a0), w = passo * col.n, lb = col.n > 1 ? w - passo * 0.25 : passo * 0.72, cx = x0 + w / 2;
        let y0 = 0;
        vv.forEach((q, j) => { const y = col.r.v[j] / col.n; if (!(y > 0)) return;
          el.push(s("rect", { x: cx - lb / 2, y: Y(y0 + y), width: lb, height: Y(y0) - Y(y0 + y), fill: q.colore, "fill-opacity": col.n > 1 ? 0.7 : 1 }, svg)); y0 += y;
          righe.push([q.colore, `${q.nome}: ${num(col.r.v[j], dec(col.r.v[j]))} ha`]); });
        if (col.r.agr) { const y = somma(col.r.agr) / col.n;
          el.push(s("rect", { x: cx + lb / 2 - Math.max(2, lb * 0.25), y: Y(y), width: Math.max(2, lb * 0.25), height: Y(0) - Y(y), fill: AGRICOLO, stroke: "#fff", "stroke-width": 0.6 }, svg));
          righe.push([AGRICOLO, `di cui su suolo agricolo (stima EuGEnio): ${num(somma(col.r.agr))} ha`]); }
        if (col.r.bil) righe.push([null, `Lordo ${num(col.r.bil[0])} ha · ripristini ${num(col.r.bil[1])} ha · netto ${segno(col.r.bil[2], 0)} ha`]);
        if (col.n > 1) {
          righe.push([null, `Media annua: ${num(somma(col.r.v) / col.n)} ha (periodo di ${col.n} anni)`]);
          s("text", { x: cx, y: Y(y0) - 4, "text-anchor": "middle", "font-size": 10, fill: "var(--tenue)" }, svg).textContent = "media annua";
        }
        punti.push({ x: cx, titolo: `${col.da}–${col.al}`, elementi: el, righe });
      } else {
        const lb = passo * 0.72; let y0 = 0;
        vv.forEach((q, j) => { const y = col.r.v[j]; if (!(y > 0)) return;
          el.push(s("rect", { x: X(col.a) - lb / 2, y: Y(y0 + y), width: lb, height: Y(y0) - Y(y0 + y), fill: q.colore }, svg)); y0 += y;
          righe.push([q.colore, `${q.nome}: ${num(y)} ha`]); });
        righe.push([null, `Totale: ${num(somma(col.r.v))} ha`]);
        punti.push({ x: X(col.a), titolo: String(col.a), elementi: el, righe });
      }
    }
    const ogni = nAnni <= 14 ? 1 : nAnni <= 24 ? 2 : 3;
    for (let a = a0; a <= a1; a++) {
      const scelto = a === st.inizio || a === st.fine;
      if (!scelto && ((a - a0) % ogni || Math.abs(a - st.fine) < ogni || Math.abs(a - st.inizio) < ogni)) continue;
      const t = s("text", { x: X(a), y: H - 6, "text-anchor": "middle", "font-size": 11, fill: scelto ? "var(--inchiostro)" : "var(--tenue)", "font-weight": scelto ? 700 : 400 }, svg);
      t.textContent = String(a);
    }
    G.osserva(svg, punti, { area: [sx, su, W - 8, H - gi], guida: false });
    const leg = (st.modo === "suolo" ? vv.slice(NC()) : vv).map((q) => [q.colore, q.nome]);
    if (st.modo === "consumi" && D().anni.agricolo.length) leg.push([AGRICOLO, "di cui su suolo agricolo (stima EuGEnio)"]);
    legendaHtml(dest, leg);
  }
  // barre per provincia nel periodo scelto (clic: apre la provincia)
  function graficoUnita(dest, mis, elenco) {
    const W = mis && mis.larghezza ? mis.larghezza : 560, H = mis && mis.riquadro ? mis.altezza : 240;
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": $("titolo-province").textContent }, dest);
    const sx = 56, gi = 34, su = 16, vv = voci(st.modo), impila = st.modo !== "suolo", da = impila ? 0 : NC();
    let max = 0;
    const rr = elenco.map((x) => ({ x, r: valori(x) }));
    rr.forEach(({ r }) => { max = Math.max(max, impila ? somma(r.v) : Math.max(...r.v.slice(da).map((y) => y || 0)), r.agr ? somma(r.agr) : 0); });
    const Y = asseY(svg, sx, su, gi, W, H, 0, scala(max).top, unitaTesto());
    const passo = (W - sx - 8) / Math.max(1, rr.length), lb = Math.min(36, passo * 0.72);
    const punti = rr.map(({ x, r }, i) => {
      const cx = sx + passo * (i + 0.5), el = [];
      if (impila) {
        let y0 = 0;
        vv.forEach((q, j) => { const y = r.v[j]; if (!(y > 0)) return;
          el.push(s("rect", { x: cx - lb / 2, y: Y(y0 + y), width: lb, height: Y(y0) - Y(y0 + y), fill: q.colore }, svg)); y0 += y; });
      } else {
        const n = vv.length - da, l = lb / n;
        vv.slice(da).forEach((q, j) => { const y = r.v[da + j]; if (!(y > 0)) return;
          el.push(s("rect", { x: cx - lb / 2 + j * l, y: Y(y), width: l, height: Y(0) - Y(y), fill: q.colore }, svg)); });
      }
      if (x.cod === st.provincia) s("rect", { x: cx - passo / 2, y: su, width: passo, height: H - su - gi, fill: "none", stroke: "var(--primario)", "stroke-width": 1.4 }, svg);
      const t = s("text", { x: cx, y: H - gi + 14, "text-anchor": "middle", "font-size": 11, fill: x.cod === st.provincia ? "var(--inchiostro)" : "var(--tenue)" }, svg);
      t.textContent = x.sigla || x.nome.slice(0, 3);
      const zona = s("rect", { x: cx - passo / 2, y: su, width: passo, height: H - su, fill: "transparent", "data-provincia": x.cod, style: "cursor:pointer" }, svg);
      zona.addEventListener("click", () => scegliProvincia(st.provincia === x.cod ? "" : x.cod));
      return { x: cx, titolo: x.nome, elementi: el, righe: [...righeValori(x), [null, st.provincia === x.cod ? "clic per tutte le province" : "clic per aprire la provincia"]] };
    });
    G.osserva(svg, punti, { area: [sx, su, W - 8, H - gi], guida: false });
  }

  function tabella(elenco, totale, tipo, reg) {
    const dove = $("tabella-suolo"); dove.innerHTML = "";
    const vv = voci(st.modo), u = unitaTesto(), per = st.modo === "consumi" ? testoFlussi(flussiDelPeriodo(st.inizio, st.fine)) : testoPeriodo();
    $("titolo-tabella").textContent = `${MODI[st.modo].lungo} – ${per} – ${reg ? `province di ${reg.nome}` : "regioni"}`;
    const t = h("table", "tabella-valori tabella-elettricita tabella-suolo"), th = h("thead"), tb = h("tbody"), tf = h("tfoot");
    const trh = h("tr"); trh.appendChild(h("th", null, tipo === "province" ? "Provincia" : "Regione"));
    let colonne = vv.map((v) => `${v.nome} (${u})`);
    const varia = st.inizio < st.fine;
    if (st.modo === "suolo" && varia) colonne.push(`Suolo consumato: variazione dal ${st.inizio} (${u})`);
    if (st.modo === "consumi") { colonne.push("Consumo lordo (ha)", "Ripristini (ha)", "Consumo netto (ha)"); if (D().anni.agricolo.length) colonne.push("Di cui su suolo agricolo (ha, stima EuGEnio)"); }
    if (st.modo === "colture") { colonne.push("Totale (ha)"); if (varia) colonne.push(`Variazione dal ${st.inizio} (ha)`); }
    colonne.forEach((c) => trh.appendChild(h("th", null, c)));
    th.appendChild(trh);
    const riga = (x, dove2, nome, cls) => {
      const tr = h("tr", cls || null); tr.appendChild(h("th", null, nome || x.nome));
      const r = valori(x);
      let celle;
      if (!r) celle = colonne.map(() => "–");
      else if (st.modo === "suolo") {
        celle = r.v.map((y) => num(y, decU(y)));
        if (varia) celle.push(r.prima ? segno(r.v[NC()] - r.prima[NC()], decU(r.v[NC()] - r.prima[NC()])) : "–");
      } else if (st.modo === "consumi") {
        celle = [...r.v.map((y) => num(y, dec(y))), ...(r.bil ? [num(r.bil[0], dec(r.bil[0])), num(r.bil[1], dec(r.bil[1])), segno(r.bil[2], dec(r.bil[2]))] : ["–", "–", "–"])];
        if (D().anni.agricolo.length) celle.push(r.agr ? num(somma(r.agr), dec(somma(r.agr))) : "–");
      } else {
        celle = [...r.v.map((y) => num(y)), num(somma(r.v))];
        if (varia) celle.push(r.prima ? segno(somma(r.v) - somma(r.prima)) : "–");
      }
      celle.forEach((c) => tr.appendChild(h("td", null, c)));
      dove2.appendChild(tr);
    };
    [...elenco].sort((p, q) => p.nome.localeCompare(q.nome, "it")).forEach((x) => riga(x, tb, null, x.cod === st.provincia ? "scelta" : ""));
    riga(totale, tf, tipo === "province" ? `Totale ${reg.nome}` : "Italia");
    t.append(th, tb, tf);
    const sc = h("div", "tabella-scorre"); sc.dataset.titolo = $("titolo-tabella").textContent; sc.appendChild(t);
    dove.appendChild(sc);
    const note = [];
    if (st.modo === "suolo") note.push("Le voci del suolo consumato (aree a pericolosità, costa, aree protette) sono parti del suolo consumato e possono sovrapporsi. SAU e superficie agricola non utilizzata: censimento ISTAT 2020.");
    if (st.modo === "consumi" && !varia && flussiDelPeriodo(st.inizio, st.fine).length && periodoDi(st.fine)[1] - periodoDi(st.fine)[0] > 1)
      note.push(`Il ${st.fine} chiude un periodo di ${periodoDi(st.fine)[1] - periodoDi(st.fine)[0]} anni (${testoFlussi([st.fine])}): i valori sono il totale del periodo.`);
    if (st.modo === "suolo" && D().rev.includes(String(st.fine))) note.push(`${st.fine}: valori pubblicati nell'edizione ${+st.fine + 1}; ISPRA li ha rivisti nell'edizione successiva (valore «rev» nel riquadretto).`);
    note.forEach((n) => dove.appendChild(h("p", "aiuto", n)));
  }
  // con una provincia scelta e «Suolo»: comuni della provincia
  function tabellaComuni(p, pr) {
    const dove = $("tabella-suolo"); dove.innerHTML = "";
    $("titolo-tabella").textContent = `Suolo consumato – ${testoPeriodo()} – comuni della provincia di ${pr.nome}`;
    const t = h("table", "tabella-valori tabella-elettricita tabella-suolo"), th = h("thead"), tb = h("tbody"), tf = h("tfoot");
    const trh = h("tr"), varia = st.inizio < st.fine;
    ["Comune", "Suolo consumato (ha)", "% del territorio", varia ? `Variazione dal ${st.inizio} (ha)` : `Incremento netto ${testoFlussi(flussiDelPeriodo(st.fine, st.fine))} (ha)`, "Superficie (ha)"]
      .forEach((c) => trh.appendChild(h("th", null, c)));
    th.appendChild(trh);
    const righe = p.comuni.dati.filter((r) => r[2] === pr.cod).map((r) => [r[0], datiComune(p, r[0])]).filter(([, d]) => d);
    righe.sort((a, b) => a[1].nome.localeCompare(b[1].nome, "it")).forEach(([, d]) => {
      const tr = h("tr"); tr.appendChild(h("th", null, d.nome));
      [num(d.cons, dec(d.cons)), num(d.pct, 1), varia ? (d.prima !== null ? segno(d.cons - d.prima, 2) : "–") : segno(d.netto, 2), num(d.sup)].forEach((c) => tr.appendChild(h("td", null, c)));
      tb.appendChild(tr);
    });
    const v = statoDi(pr, "suolo", st.fine), va = varia ? statoDi(pr, "suolo", st.inizio) : null, bil = statoDi(pr, "bilancio", st.fine);
    const tr = h("tr"); tr.appendChild(h("th", null, `Totale ${pr.nome}`));
    [v ? num(v[NC()]) : "–", v && pr.sup ? num(100 * v[NC()] / pr.sup, 2) : "–", varia ? (va ? segno(v[NC()] - va[NC()], 1) : "–") : (bil ? segno(bil[2], 1) : "–"), num(pr.sup)].forEach((c) => tr.appendChild(h("td", null, c)));
    tf.appendChild(tr);
    t.append(th, tb, tf);
    const sc = h("div", "tabella-scorre"); sc.dataset.titolo = $("titolo-tabella").textContent; sc.appendChild(t);
    dove.appendChild(sc);
    dove.appendChild(h("p", "aiuto", "Valori dei comuni come li pubblica ISPRA (arrotondati a 0,01 ha); l'incremento netto può essere negativo quando i ripristini superano il nuovo consumo."));
  }

  // ------------------------------------------------------------------ ortofoto (spenta in partenza: le regioni sono bianche)
  const CONTESTO = "s2cloudless2016";
  const orto = { fonti: [], fonte: null, contesto: null, giro: 0 };
  const primoSopra = (m) => { const l = m.getStyle().layers.find((x) => !["sfondo", "contesto", "ortofoto"].includes(x.id)); return l ? l.id : undefined; };
  const sorgenteOrto = (f) => ({ type: "raster", tiles: [location.origin + f.tessere], tileSize: 256, minzoom: f.zoom[0], maxzoom: f.zoom[1],
    ...(Array.isArray(f.riquadro) && f.riquadro.length === 4 ? { bounds: f.riquadro } : {}), attribution: f.citazione });
  const citOrto = (f) => (window.EUGENIO_ORTOFOTO_ANNI && st.mappa ? window.EUGENIO_ORTOFOTO_ANNI.citazione(f, st.mappa) : f.citazione);
  async function ortofoto(m) {
    try {
      const r = await fetch("/api/ortofoto/fonti");
      if (!r.ok || !/json/.test(r.headers.get("Content-Type") || "")) throw new Error(String(r.status));
      orto.fonti = ((await r.json()).fonti || []).filter((f) => f && f.tessere && Array.isArray(f.zoom) && !f.pmtiles);
    } catch { orto.fonti = []; return; }
    orto.contesto = orto.fonti.find((f) => f.id === CONTESTO) || null;
    if (orto.contesto) {
      m.addSource("contesto", sorgenteOrto(orto.contesto));
      m.addLayer({ id: "contesto", type: "raster", source: "contesto", layout: { visibility: $("strato-ortofoto").checked ? "visible" : "none" } }, primoSopra(m));
    }
    m.on("moveend", () => { if ($("strato-ortofoto").checked) sceltaOrto(); });
    if ($("strato-ortofoto").checked) await sceltaOrto();
    attribuzioneOrto();
  }
  async function sceltaOrto() {
    const m = st.mappa, mio = ++orto.giro, c = m.getCenter();
    let qui;
    try { qui = C.fontiNelPunto ? await C.fontiNelPunto(orto.fonti, c.lng, c.lat) : orto.fonti; } catch { qui = orto.fonti; }
    if (mio !== orto.giro) return;
    const f = qui.find((x) => x.id !== CONTESTO) || null;
    if ((f ? f.id : "") === (orto.fonte ? orto.fonte.id : "") && (!f || m.getSource("ortofoto"))) { attribuzioneOrto(); return; }
    if (m.getLayer("ortofoto")) m.removeLayer("ortofoto");
    if (m.getSource("ortofoto")) m.removeSource("ortofoto");
    orto.fonte = f;
    if (f) {
      m.addSource("ortofoto", sorgenteOrto(f));
      m.addLayer({ id: "ortofoto", type: "raster", source: "ortofoto", layout: { visibility: $("strato-ortofoto").checked ? "visible" : "none" } }, primoSopra(m));
    }
    attribuzioneOrto();
  }
  function attribuzioneOrto() {
    const a = $("attribuzione-ortofoto");
    if (!a) return;
    a.hidden = !$("strato-ortofoto").checked || !orto.fonti.length;
    if (a.hidden) return;
    a.innerHTML = "";
    const f = orto.fonte, z = st.mappa ? st.mappa.getZoom() : 0, parti = [];
    if (f) parti.push([`Ortofoto: ${citOrto(f)} – licenza `, f.licenza, f.scheda, f.zoom[0] > z ? ` (si vede dallo zoom ${f.zoom[0]}: avvicinati)` : ""]);
    if (orto.contesto) parti.push([`${f ? "Da lontano, contesto" : "Contesto"}: ${orto.contesto.citazione} – licenza `, orto.contesto.licenza, orto.contesto.scheda, ""]);
    parti.forEach(([t, lic, url, dopo], i) => { if (i) a.append(" "); a.append(t); const l = h("a", null, lic); if (url) l.href = url; a.append(l, `${dopo}.`); });
    if (!parti.length) a.textContent = "Nessuna ortofoto disponibile qui.";
    if ($("strato-fondo").checked) a.append(" Le regioni bianche coprono l'ortofoto: spegni «Regioni bianche» per vederla.");
  }
  function righeOrto() {
    if (!$("strato-ortofoto").checked || !orto.fonti.length) return [];
    const f = orto.fonte, r = [];
    if (f && !f.copia) return null;
    if (f) r.push(`Ortofoto: ${citOrto(f)} – licenza ${f.licenza} (${f.scheda}).`);
    if (orto.contesto) r.push(`Contesto: ${orto.contesto.citazione} – licenza ${orto.contesto.licenza} (${orto.contesto.scheda}).`);
    return r;
  }

  avvio().catch((e) => { st.pronto = true; messaggio("messaggio-mappa", `Errore nella mappa: ${e.message}`, true); });
})();
