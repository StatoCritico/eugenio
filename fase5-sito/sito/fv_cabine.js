"use strict";
// Fotovoltaico › «Cabine primarie» (fv-cabine.html, 17/11/2026, richiesta di Paolo).
//  - In alto a sinistra una mappa selezionabile con i confini di regioni e comuni (confini_gl.js; clic su una regione =
//    la sceglie, su un comune = la mappa di dettaglio va lì); sotto una mappa di dettaglio con ortofoto (fonte automatica
//    come in Ortofoto, scelta a mano dal menu), particelle catastali ed edifici (strati_gl.js), frecce per spostare
//    l'ortofoto (sposta_ortofoto.js) e il punto scelto da trascinare come in Modelli 3D (niente 3D).
//  - A destra: ricerca per indirizzo e per dati catastali (cerca_luogo.js), elenco nello stesso formato di Patrimonio
//    (righe con lat/lon tenute nel browser, le altre a POST /api/patrimonio a blocchi), punti di colore impostabile.
//  - Per ogni punto: area convenzionale del GSE che lo contiene (richiesta dal browser, punto → COD_AC senza geometria,
//    rete.js) e la cabina con quel COD_AC da /api/rete/cabine?regione=RR; in più le cabine e-distribuzione che servono il
//    comune del punto (campo comuni_serviti). Disegnate come nella pagina «Stato della rete elettrica».
//  - «Aggiorna confini»: perimetri delle aree delle cabine spuntate letti dal GSE dal browser (where=COD_AC IN (…),
//    semplificati, al massimo 100), mai dal server né salvati; strato spegnibile con l'attribuzione del GSE, spento nelle
//    immagini scaricate. «Scarica i confini delle aree (GSE, CC BY-NC-SA)»: GeoJSON del contratto, fatto nel browser.
//  - Confini automatici (19/11/2026, richiesta di Paolo): un clic sulla mappa che mette o sposta il punto, la ricerca, il
//    trascinamento e il clic su un punto (sulla mappa o nell'elenco) chiedono da soli al GSE il perimetro dell'area che
//    contiene il punto e quelli di tutte le aree confinanti (R.gse.areeVicine, poi R.gse.aree): area del punto con il bordo
//    spesso, confinanti sottili; stesse regole di «Aggiorna confini» (dal browser, solo a video, spenti nelle immagini). Non
//    per i punti caricati da un elenco finché non si sceglie uno di loro.
//  - Download: immagini delle due mappe (esporta_mappa.js) e dati CSV, Excel, PDF con i soli codici (rete.js).
//  Indirizzo: ?lat=…&lon=… aggiunge un punto all'apertura; ?prova=1 dati sintetici (rete.js).
(function () {
  const $ = (id) => document.getElementById(id);
  const R = window.EUGENIO_RETE, C = window.EUGENIO_CONFINI, E = window.EUGENIO, T = window.EUGENIO_TABELLE;
  if (!$("mappa-cabine") || !$("mappa-dettaglio") || !window.maplibregl || !R || !C) return;
  const ml = window.maplibregl;
  const q = new URLSearchParams(location.search);
  const MASSIMO_PUNTI = 200, BLOCCO = 40, GSE_INSIEME = 4, ZOOM_CLIC = 13;
  const COLORI_PUNTI = [{ id: "azzurro", nome: "Azzurro", colore: "#1e88e5" }, { id: "viola", nome: "Viola", colore: "#8a4fd0" },
    { id: "verde", nome: "Verde", colore: "#2e9d4f" }, { id: "rosa", nome: "Rosa", colore: "#e0559a" }, { id: "ciano", nome: "Ciano", colore: "#00acc1" },
    { id: "nero", nome: "Nero", colore: "#222222" }];
  const CHIAVE_COLORE = "eugenio-colore-punti-cabine";
  const CONTESTO = "s2cloudless2016";
  const vuota = () => ({ type: "FeatureCollection", features: [] });
  const colore = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || "#888";
  function h(tag, cls, t) { const e = document.createElement(tag); if (cls) e.className = cls; if (t !== undefined && t !== null) e.textContent = t; return e; }
  function messaggio(id, t, errore = false) { const m = $(id); if (!m) return; m.textContent = t; m.classList.toggle("errore", errore); }
  const leggiPref = () => { try { return localStorage.getItem(CHIAVE_COLORE); } catch { return null; } };
  const st = {
    top: null, det: null, confiniTop: null, punti: [], attivo: null, seq: 0,
    colore: COLORI_PUNTI.find((c) => c.id === leggiPref()) || COLORI_PUNTI[0],
    cabineRegione: new Map(), tutte: null, cabine: [], selezione: new Set(), visti: new Set(), aree: null,
    fonti: [], fonte: null, contesto: null, manuale: false, sposta: null, strati: null, trascino: false, trascinato: 0, file: null,
    giroConfini: 0,
  };
  R.avvisoProva(document.querySelector(".pannello"));

  // ================================================================== punti
  const nomePunto = (p) => [p.id, p.nome].filter(Boolean).join(" · ") || `Punto ${p.k}`;
  function aggiungiPunto(d, { attiva = true, analizza: subito = true } = {}) {
    if (st.punti.length >= MASSIMO_PUNTI) { messaggio("messaggio-punti", `Al massimo ${MASSIMO_PUNTI} punti: togline qualcuno.`, true); return null; }
    const p = { k: ++st.seq, id: d.id || "", nome: d.nome || "", lon: +d.lon, lat: +d.lat, colore: d.colore || st.colore.colore, origine: d.origine || "mappa",
      indirizzo: d.indirizzo || "", esito: d.esito || "", area: undefined, errArea: "", istat: null, comune: "", prov: "", regione: null,
      confini: !!attiva };                    // confini automatici dopo la lettura dell'area (19/11/2026)
    st.punti.push(p);
    if (attiva) st.attivo = p.k;
    if (subito) analizza(p);
    disegnaPunti();
    return p;
  }
  const punto = (k) => st.punti.find((p) => p.k === k) || null;
  function attiva(k, vai = false) {
    st.attivo = k; disegnaPunti();
    const p = punto(k);
    // (19/11/2026) clic su un punto: i confini della sua area e delle confinanti, se non sono già quelli a video
    if (p && !(st.aree && st.aree.punto === p.k)) { p.confini = true; if (p.area !== undefined) confiniDelPunto(p); }
    if (p && vai) st.det.flyTo({ center: [p.lon, p.lat], zoom: Math.max(st.det.getZoom(), 16), duration: 700 });
    const li = document.querySelector(`#elenco-punti li[data-k="${k}"]`);
    if (li) li.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }
  function togli(k) {
    st.punti = st.punti.filter((p) => p.k !== k);
    if (st.attivo === k) st.attivo = st.punti.length ? st.punti[st.punti.length - 1].k : null;
    disegnaPunti(); aggiornaCabine();
  }
  function sposta(p, lon, lat) { p.lon = lon; p.lat = lat; p.spostato = true; p.confini = true; disegnaPunti(); }

  // comune, regione e area GSE del punto (le richieste al GSE: al massimo GSE_INSIEME alla volta, in coda)
  const coda = []; let inCorso = 0;
  function inCoda(fn) { return new Promise((ok, ko) => { coda.push({ fn, ok, ko }); avanti(); }); }
  function avanti() {
    while (inCorso < GSE_INSIEME && coda.length) {
      const { fn, ok, ko } = coda.shift(); inCorso++;
      fn().then(ok, ko).finally(() => { inCorso--; avanti(); });
    }
  }
  async function analizza(p) {
    const giro = (p.giro = (p.giro || 0) + 1), lon = p.lon, lat = p.lat;
    p.area = undefined; p.errArea = ""; elencoPunti();
    let com = null, reg = null;
    try { [com, reg] = await Promise.all([C.comuneNelPunto(lon, lat), C.regioneNelPunto(lon, lat)]); } catch { /* fuori dai confini */ }
    if (giro !== p.giro) return;
    p.istat = com ? com.istat : null; p.comune = com ? com.nome : ""; p.prov = com ? com.prov : ""; p.regione = reg;
    try { p.area = await inCoda(() => R.gse.areaNelPunto(lon, lat)); }
    catch (e) { p.area = null; p.errArea = e.message || "servizio del GSE non raggiungibile"; }
    if (giro !== p.giro) return;
    pianifica();
    if (p.confini && p.k === st.attivo) confiniDelPunto(p);
  }

  // ================================================================== confini automatici (19/11/2026)
  // area del GSE che contiene il punto (bordo spesso) e tutte quelle confinanti, lette dal browser come «Aggiorna confini»
  async function confiniDelPunto(p) {
    p.confini = false;
    const mio = ++st.giroConfini, nome = nomePunto(p);
    if (!p.area) {
      if (p.area === null) messaggio("messaggio-cabine", p.errArea ? `Confini non letti per «${nome}»: ${p.errArea}.` : `«${nome}»: nessuna area del GSE in questo punto, quindi nessun confine.`, !!p.errArea);
      return;
    }
    messaggio("messaggio-cabine", `Chiedo al GSE i confini dell'area ${p.area.COD_AC} di «${nome}» e delle aree confinanti…`);
    try {
      const v = await inCoda(() => R.gse.areeVicine(p.lon, p.lat, p.area));
      if (mio !== st.giroConfini) return;
      const fc = await inCoda(() => R.gse.aree(v.codici));
      if (mio !== st.giroConfini) return;
      const centrale = p.area.COD_AC;
      fc.features.forEach((f) => { f.properties = { ...(f.properties || {}), _centrale: f.properties && f.properties.COD_AC === centrale }; });
      const primaVolta = !st.aree;
      st.aree = { ...fc, letto: new Date().toISOString(), punto: p.k, centrale };
      disegnaAree();
      $("strato-fv-aree").disabled = false;
      if (primaVolta) $("strato-fv-aree").checked = true;
      visibilita();
      const n = fc.features.length - (fc.features.some((f) => f.properties._centrale) ? 1 : 0);
      messaggio("messaggio-cabine", `Confini letti dal GSE: area ${centrale} di «${nome}» (bordo spesso) e ${n} ${n === 1 ? "area confinante" : "aree confinanti"}. `
        + "Sono solo a video, non vengono salvati." + ($("strato-fv-aree").checked ? "" : " Accendi la casella «Aree convenzionali (GSE)» per vederli."));
      const tutte = fc.features.flatMap((f) => (f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates));
      if (tutte.length && st.top) {
        let w = 180, s = 90, e = -180, nn = -90;
        for (const pol of tutte) for (const [x, y] of pol[0]) { w = Math.min(w, x); e = Math.max(e, x); s = Math.min(s, y); nn = Math.max(nn, y); }
        st.top.fitBounds([[w, s], [e, nn]], { padding: 30, duration: 700, maxZoom: 13 });
      }
    } catch (e) {
      if (mio !== st.giroConfini) return;
      messaggio("messaggio-cabine", `Confini non letti: ${e.message}. Il servizio del GSE potrebbe essere lento o non raggiungibile: riprova più tardi o usa «Aggiorna confini».`, true);
    }
  }

  // ================================================================== cabine interessate
  function cabineDi(cod) {
    if (!st.cabineRegione.has(cod)) {
      const pr = R.api(`/api/rete/cabine?regione=${cod}`).then(R.preparaCabine);
      pr.catch(() => st.cabineRegione.delete(cod));
      st.cabineRegione.set(cod, pr);
    }
    return st.cabineRegione.get(cod);
  }
  function tutteLeCabine() {
    if (!st.tutte) { st.tutte = R.api("/api/rete/cabine").then(R.preparaCabine); st.tutte.catch(() => { st.tutte = null; }); }
    return st.tutte;
  }
  let timer = 0;
  function pianifica() { clearTimeout(timer); timer = setTimeout(() => { aggiornaCabine().catch((e) => messaggio("messaggio-cabine", `Cabine non disponibili: ${e.message}`, true)); }, 120); }
  async function aggiornaCabine() {
    elencoPunti();
    const regs = [...new Set(st.punti.map((p) => p.regione).filter(Boolean))];
    const errori = [];
    const fcs = (await Promise.allSettled(regs.map(cabineDi))).map((x, i) => { if (x.status !== "fulfilled") errori.push(`${regs[i]}: ${x.reason.message}`); return x.status === "fulfilled" ? x.value : vuota(); });
    let feats = fcs.flatMap((f) => f.features);
    const perAc = () => new Map(feats.filter((f) => f.properties.cod_ac).map((f) => [f.properties.cod_ac, f]));
    let byAc = perAc();
    if (st.punti.some((p) => p.area && p.area.COD_AC && !byAc.has(p.area.COD_AC))) {
      try { const t = await tutteLeCabine(); const visti = new Set(feats); feats = feats.concat(t.features.filter((f) => !visti.has(f))); byAc = perAc(); } catch { /* resta quello che c'è */ }
    }
    const voci = new Map();
    const voce = (chiave, f, ac) => {
      if (!voci.has(chiave)) voci.set(chiave, { chiave, props: f ? f.properties : { cod_ac: ac.COD_AC, _soloGse: true, _ragSoc: ac.RAG_SOC || "" },
        coord: f ? f.geometry.coordinates : null, area: [], comune: [] });
      return voci.get(chiave);
    };
    for (const p of st.punti) {
      if (p.area && p.area.COD_AC) voce(`ac:${p.area.COD_AC}`, byAc.get(p.area.COD_AC), p.area).area.push(p);
      if (p.istat) for (const f of feats) {
        const x = f.properties;
        if (!R.eDistribuzione(x.gestore) || !String(x.comuni_serviti || "").split(";").includes(p.istat)) continue;
        const v = voce(x.cod_ac ? `ac:${x.cod_ac}` : `ed:${x.cod_cp_ed}`, f, null);
        if (!v.comune.includes(p)) v.comune.push(p);
      }
    }
    st.cabine = [...voci.values()].sort((a, b) => (b.area.length - a.area.length) || R.nomeCabina(a.props).localeCompare(R.nomeCabina(b.props), "it"));
    for (const v of st.cabine) if (!st.visti.has(v.chiave)) { st.visti.add(v.chiave); st.selezione.add(v.chiave); }
    const chiavi = new Set(st.cabine.map((v) => v.chiave));
    [...st.selezione].forEach((k) => { if (!chiavi.has(k)) st.selezione.delete(k); });
    // (19/11/2026) il messaggio si toglie solo se era un errore delle cabine: quello dei confini automatici resta
    if (errori.length) { messaggio("messaggio-cabine", `Cabine di alcune regioni non disponibili (${errori.join("; ")}).`, true); st.erroreCabine = true; }
    else if (st.erroreCabine) { messaggio("messaggio-cabine", ""); st.erroreCabine = false; }
    elencoPunti(); elencoCabine(); disegnaCabine();
  }

  // ================================================================== mappe: sorgenti comuni alle due
  function fcPunti() {
    return { type: "FeatureCollection", features: st.punti.map((p) => ({ type: "Feature", geometry: { type: "Point", coordinates: [p.lon, p.lat] },
      properties: { k: p.k, colore: p.colore, attivo: p.k === st.attivo, nome: nomePunto(p) } })) };
  }
  function fcCabine() {
    return { type: "FeatureCollection", features: st.cabine.filter((v) => v.coord).map((v) => ({ type: "Feature", geometry: { type: "Point", coordinates: v.coord },
      properties: { ...v.props, chiave: v.chiave, _sel: st.selezione.has(v.chiave) } })) };
  }
  function disegnaPunti() {
    for (const m of [st.top, st.det]) if (m && m.getSource("fv-punti")) m.getSource("fv-punti").setData(fcPunti());
    elencoPunti();
  }
  function disegnaCabine() { for (const m of [st.top, st.det]) if (m && m.getSource("fv-cabine")) m.getSource("fv-cabine").setData(fcCabine()); legenda(); chiudiAttribuzione(); }
  function disegnaAree() { for (const m of [st.top, st.det]) if (m && m.getSource("fv-aree")) m.getSource("fv-aree").setData(st.aree || vuota()); chiudiAttribuzione(); }
  // attribuzione compatta chiusa (le fonti complete sono sotto le mappe): MapLibre la riapre quando arrivano nuove fonti
  function chiudiAttribuzione() {
    for (const m of [st.top, st.det]) {
      if (!m) continue;
      const t = () => m.getContainer().querySelectorAll(".maplibregl-compact-show").forEach((x) => x.classList.remove("maplibregl-compact-show"));
      t(); m.once("idle", t);
    }
  }
  function stratiRete(m, prima) {
    m.addSource("fv-aree", { type: "geojson", data: vuota(), attribution: R.ATTR.gse });
    // (19/11/2026) con i confini automatici l'area del punto ha il bordo spesso e il fondo più pieno, le confinanti sottili
    m.addLayer({ id: "fv-aree-fondo", type: "fill", source: "fv-aree", paint: { "fill-color": colore("--primario"), "fill-opacity": ["case", ["==", ["get", "_centrale"], false], 0.05, 0.12] } }, prima);
    m.addLayer({ id: "fv-aree-linea", type: "line", source: "fv-aree", paint: { "line-color": colore("--primario"), "line-width": ["case", ["==", ["get", "_centrale"], false], 1.4, 2.8] } }, prima);
    m.addSource("fv-cabine", { type: "geojson", data: vuota(), attribution: "Cabine: © contributori OpenStreetMap (ODbL); e-distribuzione" });
    R.stratoCabine(m, "fv-cabine", { prima });
    m.addSource("fv-punti", { type: "geojson", data: vuota() });
    m.addLayer({ id: "fv-punti", type: "circle", source: "fv-punti", paint: {
      "circle-radius": ["case", ["get", "attivo"], 8, 6], "circle-color": ["get", "colore"],
      "circle-stroke-color": ["case", ["get", "attivo"], "#ffffff", "#1a1a1a"], "circle-stroke-width": ["case", ["get", "attivo"], 3, 1.5] } }, prima);
    R.suggerimento(m, () => ["fv-punti", "fv-cabine-punti", "fv-aree-fondo"], (f) => {
      const p = f.properties || {};
      if (f.layer.id === "fv-punti") { const x = punto(+p.k); return x ? { titolo: nomePunto(x), righe: righePunto(x) } : null; }
      if (f.layer.id === "fv-aree-fondo") return { titolo: `Area convenzionale ${p.COD_AC}`, righe: [`Gestore: ${p.RAG_SOC || "–"}`,
        ...(p._centrale === true ? ["area del punto scelto"] : p._centrale === false ? ["area confinante"] : []), R.ATTR.gse], cursore: false };
      const v = st.cabine.find((x) => x.chiave === p.chiave);
      const righe = R.righeCabina(p);
      if (v && v.area.length) righe.push(`Area GSE di: ${v.area.map(nomePunto).join(", ")}`);
      if (v && v.comune.length) righe.push(`Serve il comune di: ${v.comune.map(nomePunto).join(", ")}`);
      righe.push(st.selezione.has(p.chiave) ? "spuntata per «Aggiorna confini» (clic per togliere)" : "clic per spuntarla");
      return { titolo: R.nomeCabina(p), righe };
    });
    document.addEventListener("eugenio:aspetto", () => {
      m.setPaintProperty("fv-aree-fondo", "fill-color", colore("--primario"));
      m.setPaintProperty("fv-aree-linea", "line-color", colore("--primario"));
    });
  }
  // clic comune alle due mappe: punto → lo sceglie; cabina → spunta/toglie. true se il clic è stato usato
  function clicRete(m, e) {
    const su = (ids) => ids.filter((id) => m.getLayer(id) && m.getLayoutProperty(id, "visibility") !== "none");
    const p = m.queryRenderedFeatures(e.point, { layers: su(["fv-punti"]) })[0];
    if (p) { attiva(+p.properties.k, m === st.top); return true; }
    const c = m.queryRenderedFeatures(e.point, { layers: su(["fv-cabine-punti"]) })[0];
    if (c) { const k = c.properties.chiave; if (st.selezione.has(k)) st.selezione.delete(k); else st.selezione.add(k); elencoCabine(); disegnaCabine(); return true; }
    return false;
  }
  function visibilita() {
    const vis = { "fv-cabine-punti": $("strato-fv-cabine").checked, "fv-punti": $("strato-fv-punti").checked,
      "fv-aree-fondo": $("strato-fv-aree").checked && !!st.aree, "fv-aree-linea": $("strato-fv-aree").checked && !!st.aree };
    for (const m of [st.top, st.det]) if (m) for (const [id, v] of Object.entries(vis)) if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", v ? "visible" : "none");
    const a = $("attribuzione-gse");
    a.hidden = !(st.aree && $("strato-fv-aree").checked);
    a.textContent = a.hidden ? "" : `${R.ATTR.gse} (${R.GSE.SCHEDA}); aree semplificate, letti il ${R.oraIt(st.aree.letto)}. Non entrano nelle immagini scaricate.`;
    legenda();
  }
  function legenda() {
    const L = $("legenda-cabine"); L.innerHTML = "";
    const voce = (i, t) => { const s = h("span"); s.append(i, t); L.appendChild(s); };
    if ($("strato-fv-cabine").checked) {
      voce(R.campione("cabina", "VERDE"), "cabina primaria: verde (bianco)");
      for (const k of ["GIALLO", "ARANCIONE", "ROSSO"]) voce(R.campione("cabina", k), R.NOMI[k]);
      voce(R.campione("cabina", "GRIGIO"), "altro distributore o senza dato");
    }
    if ($("strato-fv-punti").checked) voce(R.campione("punto", st.colore.colore), "punti (bordo bianco: quello scelto)");
    if (st.aree && $("strato-fv-aree").checked) voce(R.campione("area"), st.aree.centrale
      ? "aree convenzionali del GSE (dal vivo): bordo spesso l'area del punto, sottile le confinanti" : "aree convenzionali del GSE (dal vivo)");
  }

  // ================================================================== mappa in alto (regioni e comuni)
  async function mappaAlto() {
    const m = new ml.Map({ container: "mappa-cabine", center: [12.4, 42.6], zoom: 5, maxZoom: 17, minZoom: 4.5, attributionControl: false,
      canvasContextAttributes: { preserveDrawingBuffer: true },
      style: { version: 8, sources: {}, layers: [{ id: "sfondo", type: "background", paint: { "background-color": colore("--carta") } }] } });
    st.top = m;
    m.addControl(new ml.NavigationControl({ showCompass: false }), "top-right");
    m.addControl(new ml.ScaleControl({ unit: "metric" }), "bottom-left");
    m.addControl(new ml.AttributionControl({ compact: true }), "bottom-right");
    await new Promise((ok) => m.on("load", ok));
    $("mappa-cabine").querySelectorAll(".maplibregl-compact-show").forEach((x) => x.classList.remove("maplibregl-compact-show"));
    document.addEventListener("eugenio:ridimensiona", () => m.resize());
    document.addEventListener("eugenio:aspetto", () => m.setPaintProperty("sfondo", "background-color", colore("--carta")));
    try {
      st.confiniTop = await C.aggiungi(m, {
        attivo: (ev) => !m.queryRenderedFeatures(ev.point, { layers: ["fv-punti", "fv-cabine-punti"].filter((id) => m.getLayer(id)) }).length,
        suRegione: (cod) => vaiRegione(cod),
        suComune: async (c) => {
          if (!c) { messaggio("messaggio-dettaglio", ""); return; }
          const b = await C.riquadroComune(c.istat);
          if (b) st.det.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 20, duration: 700 });
          messaggio("messaggio-dettaglio", `Comune di ${c.nome}${c.prov ? ` (${c.prov})` : ""}: la mappa di dettaglio è andata lì; un clic sulla mappa di dettaglio crea un punto (da vicino).`);
        },
      });
    } catch { /* confini non disponibili */ }
    stratiRete(m);
    m.on("click", (e) => clicRete(m, e));
    if (E) {
      E.suRegione = (cod) => vaiRegione(cod);
      E.suStessaRegione = (cod) => vaiRegione(cod);
      E.mappaPrincipale = { nazionale: () => m.fitBounds([[C.ITALIA[0], C.ITALIA[1]], [C.ITALIA[2], C.ITALIA[3]]], { padding: 10, duration: 600 }) };
    }
    const reg = (E && E.regione) || "08", b = await C.riquadroRegione(reg);
    if (b) m.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 20, duration: 0 });
    if (st.confiniTop) st.confiniTop.scegliRegione(reg);
    if (window.EUGENIO_ESPORTA) window.EUGENIO_ESPORTA.pulsanti($("scarica-cabine"), m, () => opzioniImmagine(m, "panoramica"), $("messaggio-immagine"));
  }
  async function vaiRegione(cod) {
    const b = await C.riquadroRegione(cod);
    if (st.confiniTop) st.confiniTop.scegliRegione(cod);
    if (E && E.seleziona) E.seleziona(cod);
    if (b) st.top.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 20, duration: 600 });
  }

  // ================================================================== mappa di dettaglio (ortofoto, particelle, edifici)
  async function mappaDettaglio() {
    const P0 = window.EUGENIO_CERCA && window.EUGENIO_CERCA.PARTENZA;
    const lat0 = Number(q.get("lat")), lon0 = Number(q.get("lon")), conPunto = q.get("lat") && q.get("lon") && Number.isFinite(lat0) && Number.isFinite(lon0);
    const centro = conPunto ? [lon0, lat0] : P0 ? [P0.lon, P0.lat] : [12.2597, 44.1326];
    const m = new ml.Map({ container: "mappa-dettaglio", center: centro, zoom: conPunto ? 16 : (P0 ? P0.zoom : 15), maxZoom: 21, minZoom: 5, attributionControl: false,
      canvasContextAttributes: { preserveDrawingBuffer: true },
      style: { version: 8, sources: {}, layers: [{ id: "sfondo", type: "background", paint: { "background-color": colore("--carta") } }] } });
    st.det = m;
    if (window.EUGENIO_LIMITI) window.EUGENIO_LIMITI.collega(m);
    m.addControl(new ml.NavigationControl({ showCompass: false }), "top-right");
    m.addControl(new ml.ScaleControl({ unit: "metric" }), "bottom-left");
    m.addControl(new ml.AttributionControl({ compact: true }), "bottom-right");
    await new Promise((ok) => m.on("load", ok));
    $("mappa-dettaglio").querySelectorAll(".maplibregl-compact-show").forEach((x) => x.classList.remove("maplibregl-compact-show"));
    document.addEventListener("eugenio:ridimensiona", () => m.resize());
    document.addEventListener("eugenio:aspetto", () => m.setPaintProperty("sfondo", "background-color", colore("--carta")));
    if (window.pmtiles) { const proto = new window.pmtiles.Protocol(); ml.addProtocol("pmtiles", proto.tile); }
    if (window.EUGENIO_SPOSTA && $("sposta-ortofoto")) st.sposta = window.EUGENIO_SPOSTA.crea($("sposta-ortofoto"), { pagina: "fv-cabine", suCambio: spostaTessere });
    try { await C.aggiungi(m, { clic: false }); } catch { /* confini non disponibili */ }
    stratiRete(m);
    if (window.EUGENIO_STRATI) {
      try {
        st.strati = await window.EUGENIO_STRATI.aggiungi(m, { caselle: $("caselle-strati"), legenda: $("legenda-strati"), sotto: () => primoSopra(m) });
      } catch { /* strati non disponibili */ }
    }
    $("caselle-strati").addEventListener("change", aggiornaSposta);
    trascinamento(m);
    // (19/11/2026) righello per distanze e aree, accanto alle caselle dei livelli della mappa di dettaglio (righello.js)
    if (window.EUGENIO_RIGHELLO) window.EUGENIO_RIGHELLO.aggiungi(m, { dove: $("caselle-strati") });
    m.on("click", (e) => {
      if (st.trascino || Date.now() - st.trascinato < 400 || clicRete(m, e)) return;
      if (m.getZoom() < ZOOM_CLIC) { messaggio("messaggio-dettaglio", "Avvicinati (zoom 13 e oltre) per mettere o spostare il punto con un clic."); return; }
      const p = punto(st.attivo);
      if (p) { sposta(p, e.lngLat.lng, e.lngLat.lat); analizza(p); messaggio("messaggio-dettaglio", `«${nomePunto(p)}» spostato qui.`); }
      else if (!st.punti.length) aggiungiPunto({ lon: e.lngLat.lng, lat: e.lngLat.lat, origine: "mappa" });
    });
    await ortofoto(m);
    if (window.EUGENIO_ESPORTA) window.EUGENIO_ESPORTA.pulsanti($("scarica-dettaglio"), m, () => opzioniImmagine(m, "dettaglio"), $("messaggio-dettaglio"));
    if (conPunto) aggiungiPunto({ lon: lon0, lat: lat0, origine: "indirizzo della pagina", nome: "Punto dell'indirizzo" });
  }
  // primo strato sopra le foto (particelle, edifici, confini, aree, cabine, punti)
  function primoSopra(m) {
    const l = m.getStyle().layers.find((x) => !["sfondo", "contesto", "ortofoto"].includes(x.id));
    return l ? l.id : undefined;
  }
  function trascinamento(m) {
    const muovi = (e) => { const p = punto(st.attivo); if (p) sposta(p, e.lngLat.lng, e.lngLat.lat); };
    const fine = () => {
      m.off("mousemove", muovi); m.off("touchmove", muovi);
      st.trascino = false; st.trascinato = Date.now(); m.getCanvas().style.cursor = "";
      const p = punto(st.attivo); if (p) { analizza(p); messaggio("messaggio-dettaglio", `«${nomePunto(p)}» spostato: cerco di nuovo l'area del GSE e le cabine.`); }
    };
    const inizio = (e, tocco) => {
      const f = e.features && e.features[0];
      if (!f || +f.properties.k !== st.attivo) return;
      e.preventDefault();
      st.trascino = true; m.getCanvas().style.cursor = "grabbing";
      m.on(tocco ? "touchmove" : "mousemove", muovi);
      m.once(tocco ? "touchend" : "mouseup", fine);
    };
    m.on("mousedown", "fv-punti", (e) => inizio(e, false));
    m.on("touchstart", "fv-punti", (e) => { if (e.points && e.points.length === 1) inizio(e, true); });
  }

  // ---- ortofoto (come Ortofoto: fonti del server, migliore applicabile nel punto, scelta a mano dal menu)
  const tessere = (f, spostata) => location.origin + (spostata && st.sposta ? st.sposta.url(f.tessere) : f.tessere);
  function sorgente(f, spostata = false) {
    return f.pmtiles ? { type: "raster", url: `pmtiles://${location.origin}${f.pmtiles}`, tileSize: 256, attribution: f.citazione }
      : { type: "raster", tiles: [tessere(f, spostata)], tileSize: 256, minzoom: f.zoom[0], maxzoom: f.zoom[1], bounds: f.riquadro, attribution: f.citazione };
  }
  async function ortofoto(m) {
    try {
      const r = await fetch("/api/ortofoto/fonti");
      if (!r.ok || !/json/.test(r.headers.get("Content-Type") || "")) throw new Error(String(r.status));
      st.fonti = (await r.json()).fonti || [];
    } catch {
      $("attribuzione-ortofoto").textContent = "Il servizio delle ortofoto non risponde: restano i confini, le particelle e gli edifici.";
      return;
    }
    st.contesto = st.fonti.find((f) => f.id === CONTESTO) || null;
    if (st.contesto) {
      m.addSource("contesto", sorgente(st.contesto));
      m.addLayer({ id: "contesto", type: "raster", source: "contesto", paint: { "raster-opacity": 0.95 } }, primoSopra(m));
    }
    $("fonte-dettaglio").addEventListener("change", (e) => { st.manuale = true; scegliFonte(e.target.value); });
    // (17/11/2026) AGEA 2022-2024: a tessere arrivate la citazione sotto la mappa dice gli anni di volo della vista
    if (window.EUGENIO_ORTOFOTO_ANNI) window.EUGENIO_ORTOFOTO_ANNI.segui(m, "ortofoto", () => { const f = st.fonte; if (f && f.anni && citOrto(f) !== st.citazioneOrto) attribuzioneOrto(); });
    await elencoFonti();
    m.on("moveend", elencoFonti);
  }
  let giroFonti = 0;
  async function elencoFonti() {
    const m = st.det, mio = ++giroFonti, c = m.getCenter();
    let qui;
    try { qui = C.fontiNelPunto ? await C.fontiNelPunto(st.fonti, c.lng, c.lat) : st.fonti; } catch { qui = st.fonti; }
    if (mio !== giroFonti) return;
    const sel = $("fonte-dettaglio"); sel.innerHTML = "";
    qui.forEach((f) => { const o = h("option", null, `${f.nome}${f.copia ? "" : " (solo consultazione)"}`); o.value = f.id; sel.appendChild(o); });
    const n = h("option", null, "nessuna ortofoto"); n.value = ""; sel.appendChild(n);
    if (st.manuale && st.fonte && !qui.some((f) => f.id === st.fonte.id)) st.manuale = false;
    const migliore = qui.find((f) => f.id !== CONTESTO) || qui[0] || null;
    if (!st.manuale && (migliore ? migliore.id : "") !== (st.fonte ? st.fonte.id : "")) scegliFonte(migliore ? migliore.id : "");
    sel.value = st.fonte ? st.fonte.id : "";
  }
  function scegliFonte(id) {
    const m = st.det, f = st.fonti.find((x) => x.id === id) || null;
    if (m.getLayer("ortofoto")) m.removeLayer("ortofoto");
    if (m.getSource("ortofoto")) m.removeSource("ortofoto");
    st.fonte = f;
    if (f && f.id !== CONTESTO) {
      m.addSource("ortofoto", sorgente(f, true));
      m.addLayer({ id: "ortofoto", type: "raster", source: "ortofoto" }, primoSopra(m));
    }
    aggiornaSposta();
    attribuzioneOrto();
  }
  // (17/11/2026) citazione con gli anni di volo della vista per le fonti con più anni (AGEA 2022-2024, protezione.js)
  function citOrto(f) {
    return window.EUGENIO_ORTOFOTO_ANNI && st.det ? window.EUGENIO_ORTOFOTO_ANNI.citazione(f, st.det) : f.citazione;
  }
  function attribuzioneOrto() {
    const f = st.fonte, a = $("attribuzione-ortofoto"); a.innerHTML = "";
    if (!f) a.textContent = st.contesto ? `Nessuna ortofoto: sotto si vede il contesto ${st.contesto.citazione} (${st.contesto.licenza}).` : "Nessuna ortofoto.";
    else {
      a.append("Ortofoto: ", citOrto(f), " – licenza ");
      const l = h("a", null, f.licenza); l.href = f.scheda; a.appendChild(l);
      a.append(f.copia ? "." : ". Solo consultazione dal vivo: non entra nelle immagini scaricate.");
    }
    st.citazioneOrto = f ? citOrto(f) : "";
  }
  function vettoriAccesi() { const s = st.strati && st.strati.stato; return !!(s && (s.particelle || s.edifici)); }
  function aggiornaSposta() { if (st.sposta) st.sposta.fonte(st.fonte, { vettori: vettoriAccesi() }); }
  function spostaTessere() {
    const src = st.det && st.det.getSource("ortofoto"), f = st.fonte;
    if (src && f && !f.pmtiles && src.setTiles) src.setTiles([tessere(f, true)]);
  }

  // ================================================================== immagini (strato GSE spento)
  function opzioniImmagine(m, quale) {
    const righe = [];
    if (quale === "dettaglio") {
      const f = st.fonte;
      if (f && !f.copia) return `«${f.nome}» è solo in consultazione dal vivo: per scaricare l'immagine scegli un'altra ortofoto.`;
      if (f) righe.push(`Ortofoto: ${citOrto(f)} – licenza ${f.licenza} (${f.scheda}).`);
      else if (st.contesto) righe.push(`Contesto: ${st.contesto.citazione} – licenza ${st.contesto.licenza} (${st.contesto.scheda}).`);
      if (f && st.sposta && st.sposta.riga()) righe.push(st.sposta.riga());
      if (st.strati) righe.push(...st.strati.righe());
    }
    if ($("strato-fv-cabine").checked && st.cabine.some((v) => v.coord)) {
      righe.push("Cabine primarie (punti grandi): livello peggiore dei trasformatori (bianco = verde, giallo, arancione, rosso); grigio = altro distributore o senza dato.");
      righe.push(`${R.ATTR.osm}. ${R.ATTR.ed_breve}.`);
    }
    if ($("strato-fv-punti").checked && st.punti.length) righe.push(`Punti dell'utente: ${st.punti.length} (bordo bianco: quello scelto).`);
    righe.push(`${R.ATTR.confini}. Mappa: MapLibre GL JS (BSD-3).`);
    if (st.aree) righe.push("Le aree convenzionali del GSE non entrano nell'immagine (licenza CC BY-NC-SA, file separato).");
    if (R.PROVA) righe.unshift("ATTENZIONE: DATI SINTETICI DI PROVA (?prova=1), non reali.");
    // aree del GSE spente per l'immagine, riaccese dopo (esporta_mappa.js chiama opz.dopo)
    const accese = ["fv-aree-fondo", "fv-aree-linea"].filter((id) => m.getLayer(id) && m.getLayoutProperty(id, "visibility") !== "none");
    accese.forEach((id) => m.setLayoutProperty(id, "visibility", "none"));
    const c = m.getCenter();
    return { titolo: `Cabine primarie – ${quale === "dettaglio" ? `dettaglio ${c.lat.toFixed(5)} N, ${c.lng.toFixed(5)} E` : "panoramica"}`, righe,
      nome: `cabine_primarie_${quale}_${new Date().toISOString().slice(0, 10)}`,
      dopo: () => accese.forEach((id) => { if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", "visible"); }) };
  }

  // ================================================================== pannello: punti
  function righePunto(p) {
    const r = [];
    if (p.indirizzo) r.push(p.indirizzo);
    r.push(`${p.lat.toFixed(5)} N, ${p.lon.toFixed(5)} E${p.spostato ? " (spostato a mano)" : ""}`);
    if (p.comune) r.push(`Comune: ${p.comune}${p.prov ? ` (${p.prov})` : ""}`);
    if (p.area === undefined) r.push("Area del GSE: la cerco…");
    else if (p.area) {
      const v = st.cabine.find((x) => x.chiave === `ac:${p.area.COD_AC}`);
      r.push(`Area GSE: ${p.area.COD_AC}${v && !v.props._soloGse ? ` – cabina ${R.nomeCabina(v.props)}${v.props.livello ? ` (${R.NOMI[v.props.livello] || v.props.livello})` : ""}` : ""}`);
    } else r.push(p.errArea ? `Area del GSE non letta: ${p.errArea}` : "Nessuna area del GSE in questo punto");
    return r;
  }
  function elencoPunti() {
    const ol = $("elenco-punti"); ol.innerHTML = "";
    $("svuota-punti").disabled = !st.punti.length;
    for (const p of st.punti) {
      const li = h("li", `punto-rete${p.k === st.attivo ? " scelto" : ""}`); li.dataset.k = p.k; li.tabIndex = 0;
      const testa = h("div", "testa");
      const c = h("i", "campione-colore"); c.style.background = p.colore; c.setAttribute("aria-hidden", "true");
      testa.append(c, h("strong", null, nomePunto(p)));
      if (p.k === st.attivo) testa.append(h("span", "esito ok", "scelto"));
      const t = h("button", "bottone secondario piccolo", "Togli"); t.type = "button"; t.setAttribute("aria-label", `Togli ${nomePunto(p)}`);
      t.addEventListener("click", (e) => { e.stopPropagation(); togli(p.k); });
      testa.append(t);
      li.appendChild(testa);
      righePunto(p).forEach((x) => li.appendChild(h("p", null, x)));
      li.addEventListener("click", () => attiva(p.k, true));
      li.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); attiva(p.k, true); } });
      ol.appendChild(li);
    }
    if (!st.punti.length) ol.appendChild(h("li", "aiuto vuoto", "Nessun punto: cerca un luogo, carica un elenco o fai clic sulla mappa di dettaglio (da vicino)."));
  }
  $("nuovo-punto").addEventListener("click", () => {
    if (!st.det) return;
    const c = st.det.getCenter();
    aggiungiPunto({ lon: c.lng, lat: c.lat, origine: "mappa", nome: `Punto ${st.seq + 1}` });
  });
  $("svuota-punti").addEventListener("click", () => { st.punti = []; st.attivo = null; st.aree = null; disegnaAree(); disegnaPunti(); aggiornaCabine(); visibilita(); });

  // colore dei punti: menu come quello del colore degli edifici di Modelli 3D
  function menuColore() {
    const riga = h("div", "riga-campi aspetto-3d");
    const et = h("span", "etichetta-colore", "Colore"); et.title = "Colore del punto scelto e dei prossimi"; et.setAttribute("aria-hidden", "true");
    const blocco = h("div", "vestito colore-edifici"); blocco.id = "colore-punti";
    const quad = (c) => { const i = h("i", "campione-colore"); i.setAttribute("aria-hidden", "true"); i.style.background = c.colore; return i; };
    const pul = h("button", "vestito-pulsante colore-edifici-pulsante"); pul.type = "button";
    pul.setAttribute("aria-haspopup", "listbox"); pul.setAttribute("aria-expanded", "false"); pul.setAttribute("aria-controls", "colore-punti-elenco");
    const ul = h("ul", "vestito-elenco a-discesa"); ul.id = "colore-punti-elenco"; ul.setAttribute("role", "listbox");
    ul.setAttribute("aria-label", "Colore dei punti"); ul.tabIndex = -1; ul.hidden = true;
    const voci = COLORI_PUNTI.map((c) => { const li = h("li"); li.setAttribute("role", "option"); li.id = `colore-punti-${c.id}`; li.dataset.colore = c.id; li.append(quad(c), c.nome); ul.appendChild(li); return li; });
    blocco.append(pul, ul);
    let i = 0;
    function disegna() {
      pul.innerHTML = ""; pul.append(quad(st.colore), h("span", "nome-colore", st.colore.nome));
      const t = `Colore dei punti: ${st.colore.nome}`; pul.setAttribute("aria-label", t); pul.title = t;
      voci.forEach((o) => o.setAttribute("aria-selected", String(o.dataset.colore === st.colore.id)));
    }
    const evidenzia = (n) => { i = (n + voci.length) % voci.length; voci.forEach((o, k) => o.classList.toggle("attiva", k === i)); ul.setAttribute("aria-activedescendant", voci[i].id); };
    const fuori = (e) => { if (!ul.contains(e.target) && !pul.contains(e.target)) chiudi(false); };
    function apri() { ul.hidden = false; pul.setAttribute("aria-expanded", "true"); evidenzia(Math.max(0, COLORI_PUNTI.indexOf(st.colore))); ul.focus(); document.addEventListener("pointerdown", fuori, true); }
    function chiudi(rimetti) { ul.hidden = true; pul.setAttribute("aria-expanded", "false"); document.removeEventListener("pointerdown", fuori, true); if (rimetti) pul.focus(); }
    function conferma(k) {
      evidenzia(k); chiudi(true);
      st.colore = COLORI_PUNTI[k];
      try { localStorage.setItem(CHIAVE_COLORE, st.colore.id); } catch { /* niente */ }
      const p = punto(st.attivo); if (p) p.colore = st.colore.colore;
      disegna(); disegnaPunti(); legenda();
    }
    ul.addEventListener("keydown", (e) => {
      switch (e.key) {
        case "ArrowDown": case "ArrowRight": evidenzia(i + 1); break;
        case "ArrowUp": case "ArrowLeft": evidenzia(i - 1); break;
        case "Home": evidenzia(0); break;
        case "End": evidenzia(voci.length - 1); break;
        case "Enter": case " ": conferma(i); break;
        case "Escape": chiudi(true); break;
        case "Tab": chiudi(false); return;
        default: return;
      }
      e.preventDefault();
    });
    voci.forEach((o, k) => o.addEventListener("click", () => conferma(k)));
    pul.addEventListener("click", () => (ul.hidden ? apri() : chiudi(true)));
    pul.addEventListener("keydown", (e) => { if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); apri(); } });
    riga.append(et, blocco);
    $("comandi-punti").appendChild(riga);
    disegna();
  }

  // ================================================================== pannello: cabine
  function elencoCabine() {
    const box = $("elenco-cabine"); box.innerHTML = "";
    const n = st.cabine.length, sel = st.cabine.filter((v) => st.selezione.has(v.chiave) && v.props.cod_ac).length;
    $("aggiorna-confini").disabled = !sel; $("scarica-aree-gse").disabled = !sel;
    $("tutte-cabine").disabled = !n; $("nessuna-cabina").disabled = !n;
    if (!n) { box.appendChild(h("p", "aiuto", st.punti.length ? "Nessuna cabina primaria trovata per i punti (aspetta la risposta del GSE)." : "Nessun punto, quindi nessuna cabina.")); return; }
    const ul = h("ul", "elenco-cabine");
    for (const v of st.cabine) {
      const p = v.props, li = h("li", "cabina-rete");
      const l = h("label", "casella testa"), c = h("input"); c.type = "checkbox"; c.checked = st.selezione.has(v.chiave); c.disabled = !p.cod_ac;
      c.addEventListener("change", () => { if (c.checked) st.selezione.add(v.chiave); else st.selezione.delete(v.chiave); elencoCabine(); disegnaCabine(); });
      l.append(c, R.campione("cabina", p._soloGse ? "GRIGIO" : R.coloreCabina(p)), h("strong", null, p._soloGse ? `Area ${p.cod_ac}` : R.nomeCabina(p)));
      li.appendChild(l);
      const righe = p._soloGse ? [`Area GSE (COD_AC): ${p.cod_ac}`, `Gestore (GSE): ${p._ragSoc || "–"}`, "Cabina non presente nella tabella di raccordo di EuGEnio."] : R.righeCabina(p);
      righe.forEach((x) => li.appendChild(h("p", null, x)));
      if (v.area.length) li.appendChild(h("p", "sedi", `Area GSE di: ${v.area.map(nomePunto).join(", ")}`));
      if (v.comune.length) li.appendChild(h("p", "sedi", `Serve il comune di: ${[...new Set(v.comune.map((x) => `${nomePunto(x)} (${x.comune})`))].join(", ")}`));
      if (!p.cod_ac) li.appendChild(h("p", "aiuto", "Senza codice dell'area GSE: confini non disponibili."));
      ul.appendChild(li);
    }
    box.appendChild(ul);
  }
  $("tutte-cabine").addEventListener("click", () => { st.cabine.forEach((v) => st.selezione.add(v.chiave)); elencoCabine(); disegnaCabine(); });
  $("nessuna-cabina").addEventListener("click", () => { st.selezione.clear(); elencoCabine(); disegnaCabine(); });
  const codiciScelti = () => [...new Set(st.cabine.filter((v) => st.selezione.has(v.chiave) && v.props.cod_ac).map((v) => v.props.cod_ac))];
  $("aggiorna-confini").addEventListener("click", async () => {
    const cs = codiciScelti();
    if (cs.length > R.GSE.MASSIMO) { messaggio("messaggio-cabine", `Hai spuntato ${cs.length} aree: al massimo ${R.GSE.MASSIMO}, restringi la selezione.`, true); return; }
    const b = $("aggiorna-confini"); b.disabled = true;
    messaggio("messaggio-cabine", `Chiedo al GSE i confini di ${cs.length} ${cs.length === 1 ? "area" : "aree"}…`);
    try {
      const fc = await R.gse.aree(cs);
      st.aree = { ...fc, letto: new Date().toISOString() };
      disegnaAree();
      $("strato-fv-aree").disabled = false; $("strato-fv-aree").checked = true; visibilita();
      const mancano = cs.filter((c) => !fc.features.some((f) => f.properties.COD_AC === c));
      messaggio("messaggio-cabine", `Confini di ${fc.features.length} ${fc.features.length === 1 ? "area" : "aree"} letti dal GSE${mancano.length ? `; non trovate: ${mancano.join(", ")}` : ""}. Sono solo a video, non vengono salvati.`, !!mancano.length);
      const tutte = fc.features.flatMap((f) => (f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates));
      if (tutte.length) {
        let w = 180, s = 90, e = -180, n = -90;
        for (const pol of tutte) for (const [x, y] of pol[0]) { w = Math.min(w, x); e = Math.max(e, x); s = Math.min(s, y); n = Math.max(n, y); }
        st.top.fitBounds([[w, s], [e, n]], { padding: 30, duration: 700, maxZoom: 13 });
      }
    } catch (e) {
      messaggio("messaggio-cabine", `Confini non letti: ${e.message}. Il servizio del GSE potrebbe essere lento o non raggiungibile: riprova più tardi.`, true);
    } finally { b.disabled = !codiciScelti().length; }
  });
  $("scarica-aree-gse").addEventListener("click", async () => {
    const cs = codiciScelti();
    if (cs.length > R.GSE.MASSIMO) { messaggio("messaggio-cabine", `Hai spuntato ${cs.length} aree: il file ne contiene al massimo ${R.GSE.MASSIMO}, restringi la selezione.`, true); return; }
    const b = $("scarica-aree-gse"); b.disabled = true;
    messaggio("messaggio-cabine", "Leggo dal GSE le aree per il file…");
    try {
      const fc = await R.gse.aree(cs);
      const sedi = new Map();
      st.punti.forEach((p) => { if (p.area && p.area.COD_AC) { if (!sedi.has(p.area.COD_AC)) sedi.set(p.area.COD_AC, []); sedi.get(p.area.COD_AC).push(nomePunto(p)); } });
      const gj = R.gse.geojson(fc, sedi);
      if (R.PROVA) gj.avviso = `DATI SINTETICI DI PROVA (?prova=1), aree inventate. ${gj.avviso}`;
      const nome = `aree_convenzionali_GSE_${new Date().toISOString().slice(0, 10)}.geojson`;
      R.scaricaBlob(new Blob([JSON.stringify(gj, null, 1)], { type: "application/geo+json" }), nome);
      messaggio("messaggio-cabine", `Download avviato: ${nome} (${gj.features.length} aree, licenza CC BY-NC-SA 3.0 IT del GSE scritta nel file).`);
    } catch (e) {
      messaggio("messaggio-cabine", `File non preparato: ${e.message}.`, true);
    } finally { b.disabled = !codiciScelti().length; }
  });
  for (const id of ["strato-fv-cabine", "strato-fv-punti", "strato-fv-aree"]) $(id).addEventListener("change", visibilita);

  // ================================================================== ricerca e elenco
  if (window.EUGENIO_CERCA) {
    window.EUGENIO_CERCA.crea($("cerca-luogo"), {
      suTrovato: (lon, lat, riga) => {
        const ind = riga.centro_comune ? `centro del comune di ${riga.comune_catasto || ""}` : [riga.indirizzo_trovato, riga.comune_catasto].filter(Boolean).join(", ");
        const nome = riga.centro_comune ? `Centro di ${riga.comune_catasto || "comune"}` : (riga.indirizzo_trovato || (riga.mappale ? `Foglio ${riga.foglio_catasto} part. ${riga.mappale}` : "Punto cercato"));
        aggiungiPunto({ lon, lat, nome, indirizzo: ind, origine: "ricerca" });
        if (st.det) st.det.flyTo({ center: [lon, lat], zoom: riga.zoom || window.EUGENIO_CERCA.ZOOM || 17, duration: 900 });
      },
    });
  }
  const norm = (c) => String(c || "").trim().toLowerCase().replace(/["']/g, "").replace(/[^a-z0-9àèéìòù_]/g, "_").replace(/^_+|_+$/g, "");
  if (T && $("file-elenco")) $("file-elenco").setAttribute("accept", T.ACCETTA);
  $("file-elenco").addEventListener("change", (e) => {
    st.file = e.target.files && e.target.files[0] || null;
    $("nome-file-elenco").textContent = st.file ? st.file.name : "";
    $("carica-elenco").disabled = !st.file;
  });
  $("carica-elenco").addEventListener("click", async () => {
    if (!st.file || !T) return;
    const b = $("carica-elenco"); b.disabled = true;
    try { await caricaElenco(st.file); } catch (e) { messaggio("messaggio-elenco", `Non riuscito: ${e.message}`, true); }
    finally { b.disabled = !st.file; $("avanzamento-elenco").hidden = true; }
  });
  const cella = (v) => (/[;"\n\r]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));
  async function caricaElenco(file) {
    messaggio("messaggio-elenco", "Lettura del file…");
    const letto = await T.leggi(file);
    let linee = letto.testo.split(/\r?\n/).filter((r) => r.trim() && !r.trim().startsWith("#") && !/^"?Fonte: EuGEnio/i.test(r.trim()));
    if (linee.length < 2) throw new Error("il file non contiene righe di dati");
    const sep = T.separatore(linee[0]);
    const tab = T.righe(linee.join("\n"), sep);
    const testa = tab[0].map(norm), corpo = tab.slice(1).filter((r) => r.some((x) => String(x).trim()));
    if (corpo.length > MASSIMO_PUNTI) throw new Error(`il file ha ${corpo.length} righe: al massimo ${MASSIMO_PUNTI} in questa pagina (per elenchi più lunghi usa Patrimonio e poi carica qui le coordinate)`);
    const col = (...n) => testa.findIndex((x) => n.includes(x));
    const iId = col("id", "codice", "cod", "codice_edificio"), iNome = col("denominazione", "nome"), iInd = col("indirizzo", "via"), iCiv = col("civico"),
      iCom = col("comune"), iLat = col("lat", "latitudine"), iLon = col("lon", "lng", "longitudine");
    const val = (r, i) => (i >= 0 ? String(r[i] ?? "").trim() : "");
    const numero = (s) => T.numero(s, { decimalePunto: letto.decimalePunto });
    const dirette = [], altre = [];
    corpo.forEach((r, k) => {
      const lat = numero(val(r, iLat)), lon = numero(val(r, iLon));
      const ok = lat !== null && lon !== null && lat > 35 && lat < 48 && lon > 6 && lon < 19.5;
      (ok ? dirette : altre).push({ r, k, lat, lon });
    });
    let nuovi = 0;
    for (const { r, k, lat, lon } of dirette) {
      if (aggiungiPunto({ id: val(r, iId) || String(k + 1), nome: val(r, iNome), lat, lon, indirizzo: [val(r, iInd), val(r, iCiv), val(r, iCom)].filter(Boolean).join(" "),
        origine: "elenco (coordinate del file)" }, { attiva: false })) nuovi++;
    }
    let non = 0, interrotto = "";
    if (altre.length) {
      if (R.PROVA) { interrotto = `${altre.length} righe senza coordinate non cercate: nel modo di prova la pagina non usa il server.`; }
      else {
        const testaCsv = iId >= 0 ? tab[0] : ["id", ...tab[0]];
        const righe = altre.map(({ r, k }) => (iId >= 0 ? r : [String(k + 1), ...r]));
        $("avanzamento-elenco").hidden = false;
        for (let i = 0; i < righe.length; i += BLOCCO) {
          messaggio("messaggio-elenco", `Cerco le sedi: ${i} di ${righe.length}…`);
          $("barra-elenco").style.width = `${(100 * i / righe.length).toFixed(1)}%`;
          const testo = [testaCsv, ...righe.slice(i, i + BLOCCO)].map((x) => x.map(cella).join(";")).join("\n");
          const fd = new FormData(); fd.append("file", new Blob([testo], { type: "text/csv;charset=utf-8" }), "elenco.csv");
          let d;
          try {
            const rr = await fetch("/api/patrimonio", { method: "POST", body: fd });
            d = await rr.json().catch(() => null);
            if (!rr.ok) throw new Error((d && d.detail) || `errore ${rr.status}`);
          } catch (e) { interrotto = `Ricerca interrotta dopo ${i} righe: ${e.message}.`; break; }
          for (const x of d.righe || []) {
            const lat = x.lat === null || x.lat === undefined || x.lat === "" ? NaN : +x.lat, lon = x.lon === null || x.lon === undefined || x.lon === "" ? NaN : +x.lon;
            if (!Number.isFinite(lat) || !Number.isFinite(lon) || x.esito === "non_trovato" || x.esito === "errore") { non++; continue; }
            if (aggiungiPunto({ id: x.id || "", nome: x.denominazione || "", lat, lon, indirizzo: x.indirizzo_trovato || [x.indirizzo, x.civico, x.comune].filter(Boolean).join(" "),
              esito: x.esito, origine: x.esito === "verificare" ? "elenco (da verificare)" : "elenco" }, { attiva: false })) nuovi++;
          }
        }
        $("barra-elenco").style.width = "100%";
      }
    }
    if (nuovi && !st.attivo) st.attivo = st.punti[0].k;
    disegnaPunti();
    const pts = st.punti;
    if (pts.length) {
      const xs = pts.map((p) => p.lon), ys = pts.map((p) => p.lat);
      st.top.fitBounds([[Math.min(...xs), Math.min(...ys)], [Math.max(...xs), Math.max(...ys)]], { padding: 40, maxZoom: 11, duration: 700 });
    }
    messaggio("messaggio-elenco", [`${nuovi} ${nuovi === 1 ? "punto aggiunto" : "punti aggiunti"} su ${corpo.length} righe${non ? `, ${non} non trovati` : ""}.`, letto.nota, interrotto].filter(Boolean).join(" "), !!interrotto);
  }

  // ================================================================== dati scaricati (solo i codici)
  function datiFile() {
    if (!st.punti.length) return "Nessun punto: cerca un luogo o carica un elenco.";
    const cabArea = (p) => p.area && st.cabine.find((v) => v.chiave === `ac:${p.area.COD_AC}`);
    const punti = st.punti.map((p, i) => {
      const v = cabArea(p), c = v && !v.props._soloGse ? v.props : null;
      const delComune = st.cabine.filter((x) => x.comune.includes(p)).map((x) => x.props.cod_cp_ed).filter(Boolean);
      return [i + 1, p.id, p.nome, p.indirizzo, p.comune, p.istat || "", Math.round(p.lat * 1e6) / 1e6, Math.round(p.lon * 1e6) / 1e6, p.origine,
        p.area ? p.area.COD_AC : (p.area === null ? "non trovata" : "in attesa"), c ? c.cod_cp_ed || "" : "", c ? R.nomeCabina(c) : "", c && c.livello ? R.NOMI[c.livello] : "", delComune.join(" ")];
    });
    const intP = ["N.", "Id", "Nome", "Indirizzo", "Comune", "ISTAT", "Latitudine", "Longitudine", "Origine", "COD_AC (area GSE)", "Cabina dell'area: codice e-distribuzione",
      "Cabina dell'area: nome", "Livello della cabina", "Cabine e-distribuzione del comune"];
    const cab = st.cabine.map((v) => {
      const p = v.props, t = p.trasf || {}, ok = !p._soloGse;
      return [p.cod_ac || "", ok ? p.cod_cp_ed || "" : "", ok ? R.nomeCabina(p) : "", ok ? p.gestore || "" : "", ok && p.livello ? R.NOMI[p.livello] : "",
        ok ? t.VERDE ?? null : null, ok ? t.GIALLO ?? null : null, ok ? t.ARANCIONE ?? null : null, ok ? t.ROSSO ?? null : null, ok ? p.data_saturazione || "" : "",
        v.coord ? Math.round(v.coord[1] * 1e5) / 1e5 : null, v.coord ? Math.round(v.coord[0] * 1e5) / 1e5 : null, ok ? p.esito || "" : "solo codice GSE",
        v.area.map(nomePunto).join(", "), [...new Set(v.comune.map(nomePunto))].join(", "), st.selezione.has(v.chiave) ? "sì" : "no"];
    });
    const intK = ["COD_AC (GSE)", "Codice e-distribuzione", "Nome", "Gestore", "Livello peggiore", "Trasf. verdi", "Trasf. gialli", "Trasf. arancioni", "Trasf. rossi", "Dato del",
      "Latitudine", "Longitudine", "Raccordo", "Punti nell'area", "Punti nei comuni serviti", "Spuntata"];
    const sezioni = [{ titolo: "Punti", intestazioni: intP, righe: punti }, { titolo: "Cabine primarie interessate", intestazioni: intK, righe: cab }];
    const piede = [
      ...(R.PROVA ? ["ATTENZIONE: DATI SINTETICI DI PROVA (?prova=1), non reali."] : []),
      `${R.ATTR.ed}.`, `${R.ATTR.osm}.`, `${R.ATTR.gse_codici} (${R.GSE.SCHEDA}); nel file solo i codici, i confini delle aree sono nel file separato del GSE (CC BY-NC-SA 3.0 IT).`,
      "La cabina che conta per gli incentivi è quella dell'area che contiene il punto di connessione (POD): verifica ufficiale con la ricerca per POD del GSE.",
      "Ricerca degli indirizzi: ANNCSU – Agenzia delle Entrate e ISTAT (CC BY 4.0) e dati elaborati da Zornade (zornade.com).",
      "Licenza: dati elaborati da EuGEnio CC BY 4.0; posizioni delle cabine ODbL 1.0 (© contributori OpenStreetMap).",
    ];
    const nome = `cabine_primarie_${new Date().toISOString().slice(0, 10)}`;
    const doc = {
      titolo: "Cabine primarie dei punti", sottotitolo: `${st.punti.length} punti, ${st.cabine.length} cabine interessate`, nome_file: nome,
      sezioni: [
        { titolo: "Come leggere", blocchi: [
          ...(R.PROVA ? [{ tipo: "avvertenza", testo: "DATI SINTETICI DI PROVA (?prova=1): non reali." }] : []),
          { tipo: "paragrafo", testo: "Per ogni punto: l'area convenzionale del GSE che lo contiene (COD_AC, letto dal servizio del GSE) con la sua cabina e le cabine di e-distribuzione che servono il comune. Colore della cabina: livello peggiore dei suoi trasformatori (dato mensile di e-distribuzione)." },
          { tipo: "avvertenza", livello: "info", testo: "La cabina che conta per gli incentivi è quella dell'area che contiene il punto di connessione (POD): la verifica ufficiale è la ricerca per POD del GSE." },
        ] },
        ...sezioni.map((s) => ({ titolo: s.titolo, blocchi: [{ tipo: "tabella", intestazioni: s.intestazioni, righe: s.righe.length ? s.righe : [s.intestazioni.map(() => null)] }] })),
      ],
      fonti: [
        { testo: "e-distribuzione S.p.A. – Aree critiche (dato mensile per trasformatore)", url: R.URL_ED },
        { testo: "© contributori OpenStreetMap – posizioni delle cabine primarie, ODbL 1.0", url: R.URL_OSM },
        { testo: "GSE S.p.A. – codici delle aree convenzionali (COD_AC)", url: R.GSE.SCHEDA },
        { testo: "ANNCSU – Agenzia delle Entrate e ISTAT (CC BY 4.0)", url: "https://anncsu.open.agenziaentrate.gov.it/" },
        { testo: "Dati elaborati da Zornade", url: "https://zornade.com" },
      ],
    };
    return { csv: [`${nome}.csv`, sezioni, piede], doc };
  }

  // ================================================================== avvio
  menuColore();
  legenda();
  elencoPunti(); elencoCabine();
  R.pulsantiDati($("scarica-dati"), datiFile, $("messaggio-dati"));
  Promise.all([mappaAlto(), mappaDettaglio()]).then(() => { visibilita(); disegnaPunti(); disegnaCabine(); })
    .catch((e) => messaggio("messaggio-immagine", `Mappa non disponibile: ${e.message}`, true));
  window.EUGENIO_CABINE = { st, aggiungiPunto, attiva, datiFile, opzioniImmagine, aggiornaCabine };
})();
