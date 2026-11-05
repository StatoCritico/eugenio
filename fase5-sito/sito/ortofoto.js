"use strict";
// Pagina Patrimonio › Ortofoto (fase 10, Fase B, § 6 della proposta). Mappa MapLibre con le ortofoto servite dal proxy
// del server (/api/ortofoto/fonti e /api/ortofoto/<fonte>/<z>/<x>/<y>.jpg, servizio/ortofoto.py), selettore delle
// fonti che coprono la zona e attribuzione sempre visibile sotto la mappa (citazione, licenza, scheda, stato).
// Contorni degli edifici dall'archivio 3D (PMTiles dei corpi) se c'è; altrimenti niente. Ortofoto AGEA dei singoli siti
// (scaricate a mano, ridotte a 50 cm: comando `edifici3d ortofoto-sito`) da /edifici3d/cc-by/ortofoto_siti/indice.json,
// aggiunte come fonti in PMTiles.
//
// 05/11/2026 (prove di Paolo sul sito pubblicato: «se ingrandisco sparisce tutto»): la RER e le altre ortofoto regionali
// hanno tessere solo dallo zoom 12; fuori da quegli zoom o dal loro riquadro la mappa restava nera, senza nessun
// riferimento. Ora:
//  - sotto la fonte scelta c'è sempre il contesto Sentinel-2 cloudless 2016 (zoom 5–15, poi ingrandito), e oltre lo zoom
//    massimo di una fonte MapLibre ingrandisce l'ultimo livello (maxzoom della sorgente) invece di lasciare il vuoto;
//  - confini di regioni, province (da zoom 7) e comuni (da zoom 9) sempre sopra la foto (confini_gl.js, ISTAT CC BY);
//  - un avviso sulla mappa dice quando si è fuori dal riquadro o dagli zoom della fonte e cosa si vede al suo posto;
//  - piccola mappa d'Italia in alto a destra (minimappa.js): clic su una regione = la mappa va lì, secondo clic = la
//    scelta si toglie e si torna all'Italia; sulla mappa grande clic su regione (zoom basso) o comune (zoom medio),
//    secondo clic sul comune = lo toglie;
//  - «Scarica l'immagine» in JPG, PNG o PDF della vista com'è, con licenza e citazione delle fonti dentro l'immagine
//    (esporta_mappa.js); non per le fonti «solo consultazione dal vivo».
// Indirizzo: ?lat=…&lon=…&z=… per aprire su un punto, ?fonte=<id> per scegliere la fonte.
(function () {
  const $ = (id) => document.getElementById(id);
  const box = $("mappa-ortofoto");
  if (!box || !window.maplibregl) return;
  const C = window.EUGENIO_CONFINI;
  const q = new URLSearchParams(location.search);
  const centro = [Number(q.get("lon")) || 12.5683, Number(q.get("lat")) || 44.0594];
  const CONTESTO = "s2cloudless2016";
  const stato = { fonti: [], scelta: null, mappa: null, contesto: null, edifici: null, confini: null, regione: null, comune: null };
  const colore = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || "#888";
  function h(tag, cls, t) { const e = document.createElement(tag); if (cls) e.className = cls; if (t !== undefined) e.textContent = t; return e; }
  function messaggio(t, errore = false) { const m = $("messaggio"); m.textContent = t; m.classList.toggle("errore", errore); }
  const copre = (f, [lon, lat]) => lon >= f.riquadro[0] && lon <= f.riquadro[2] && lat >= f.riquadro[1] && lat <= f.riquadro[3];

  // avviso sulla mappa (in alto a sinistra): fuori riquadro, sotto lo zoom minimo, oltre lo zoom massimo
  const avviso = h("div", "avviso-mappa"); avviso.setAttribute("role", "status"); avviso.hidden = true; box.appendChild(avviso);
  function aggiornaAvviso() {
    const m = stato.mappa, f = stato.scelta;
    if (!m) return;
    const z = m.getZoom(), c = m.getCenter(), p = [c.lng, c.lat], ctx = stato.contesto;
    const ctxVisibile = ctx && copre(ctx, p) && (!f || f.id !== CONTESTO);
    const sotto = ctxVisibile ? ` Sotto si vede il contesto ${ctx.nome}.` : " Restano i confini di regioni e comuni.";
    let t = "";
    if (!f) t = "Nessuna ortofoto scelta." + sotto;
    else if (!copre(f, p)) t = `«${f.nome}» non copre questa zona.` + sotto;
    else if (z < f.zoom[0] - 0.01) t = `«${f.nome}» si vede dallo zoom ${f.zoom[0]}: avvicinati (ora ${z.toFixed(1)}).` + sotto;
    else if (z > f.zoom[1] + 0.5) t = `Oltre lo zoom ${f.zoom[1]} «${f.nome}» non ha immagini più dettagliate: quella che vedi è ingrandita.`;
    avviso.textContent = t; avviso.hidden = !t;
  }

  function attribuzione(f) {
    const a = $("attribuzione"); a.innerHTML = "";
    if (!f) { a.textContent = "Nessuna ortofoto: scegli una fonte."; return; }
    a.append("Ortofoto: ", f.citazione, " – licenza ");
    const l = h("a", null, f.licenza); l.href = f.scheda; a.appendChild(l);
    if (f.stato === "da confermare") a.append(". Uso tramite il server di EuGEnio in attesa di conferma della fonte");
    a.append(f.copia ? "." : ". Solo consultazione dal vivo: non entra nei report né nelle immagini scaricate.");
    if (stato.contesto && f.id !== CONTESTO) a.append(` Sotto, come contesto: ${stato.contesto.citazione}.`);
  }
  function sorgente(f) {
    return f.pmtiles
      ? { type: "raster", url: `pmtiles://${location.origin}${f.pmtiles}`, tileSize: 256, attribution: f.citazione }
      : { type: "raster", tiles: [location.origin + f.tessere], tileSize: 256, minzoom: f.zoom[0], maxzoom: f.zoom[1], bounds: f.riquadro, attribution: f.citazione };
  }
  const sopraLe = () => ["edifici", "confini-comuni-clic", "confini-regioni-clic"].find((id) => stato.mappa.getLayer(id));
  function contesto() {
    const m = stato.mappa, f = stato.fonti.find((x) => x.id === CONTESTO);
    stato.contesto = f || null;
    if (!f) return;
    m.addSource("contesto", sorgente(f));
    m.addLayer({ id: "contesto", type: "raster", source: "contesto", paint: { "raster-opacity": 0.95 } }, sopraLe());
  }
  function scegli(id) {
    const m = stato.mappa, f = stato.fonti.find((x) => x.id === id) || null;
    if (m.getLayer("ortofoto")) m.removeLayer("ortofoto");
    if (m.getSource("ortofoto")) m.removeSource("ortofoto");
    stato.scelta = f;
    if (f && f.id !== CONTESTO) {
      m.addSource("ortofoto", sorgente(f));
      m.addLayer({ id: "ortofoto", type: "raster", source: "ortofoto" }, sopraLe());
    }
    // il contesto si vede sempre sotto (anche con «Nessuna ortofoto» resta il riferimento della zona)
    if (m.getLayer("contesto")) m.setLayoutProperty("contesto", "visibility", "visible");
    if (C) C.alza(m);
    try { const u = new URL(location.href); if (f) u.searchParams.set("fonte", f.id); else u.searchParams.delete("fonte"); history.replaceState(null, "", u); } catch { /* niente */ }
    attribuzione(f);
    document.querySelectorAll('#fonti input[name="fonte"]').forEach((i) => { i.checked = i.value === (f ? f.id : ""); });
    aggiornaAvviso();
  }
  function elenco() {
    const fs = $("fonti");
    fs.querySelectorAll("label").forEach((x) => x.remove());
    const c = stato.mappa.getCenter(), qui = stato.fonti.filter((f) => copre(f, [c.lng, c.lat]));
    if (!qui.length) messaggio("Nessuna ortofoto copre questa zona: restano i confini.", true); else messaggio("");
    for (const f of qui) {
      const l = h("label"), i = h("input"); i.type = "radio"; i.name = "fonte"; i.value = f.id; i.checked = stato.scelta && stato.scelta.id === f.id;
      i.addEventListener("change", () => { stato.manuale = true; scegli(f.id); });
      const n = h("span", "nome-fonte", f.nome);
      const d = h("span", "dettagli-fonte");
      const st = !f.copia ? h("span", "stato-fonte da-confermare", "solo consultazione")
        : h("span", `stato-fonte ${f.stato === "confermata" ? "confermata" : "da-confermare"}`, f.stato === "confermata" ? "licenza verificata" : "uso da confermare");
      d.append(`${f.licenza} · zoom ${f.zoom[0]}–${f.zoom[1]} · ${f.copia ? "con copia sul server" : "solo dal vivo"} `, st);
      l.append(i, n, d); fs.appendChild(l);
    }
    const nessuna = h("label"), i0 = h("input"); i0.type = "radio"; i0.name = "fonte"; i0.value = ""; i0.checked = !stato.scelta;
    i0.addEventListener("change", () => { stato.manuale = true; scegli(""); });
    nessuna.append(i0, h("span", "nome-fonte", "Nessuna ortofoto (solo il contesto e i confini)")); fs.appendChild(nessuna);
    // finché l'utente non sceglie a mano si usa sempre la migliore che copre la zona (l'elenco è già in ordine di
    // dettaglio); dopo una scelta a mano si cambia solo se la fonte scelta non copre più la zona
    const migliore = qui.find((f) => f.id !== CONTESTO) || qui[0];
    if (!stato.manuale && migliore && (!stato.scelta || stato.scelta.id !== migliore.id)) scegli(migliore.id);
    else if (stato.scelta && !copre(stato.scelta, [c.lng, c.lat]) && qui.length) scegli(migliore.id);
    aggiornaAvviso();
  }

  async function edifici(m) {
    // contorni dei corpi dall'archivio 3D (dati veri): solo per riconoscere i tetti. La demo sintetica non si sovrappone
    // mai alla foto: le sue sagome sono inventate e non corrispondono a nessun edificio (05/11/2026, «edifici storti»)
    for (const b of ["/edifici3d/cc-by/er/prodotti/"]) {
      try {
        const r = await fetch(`${b}indice.json`);
        if (!r.ok || !/json/.test(r.headers.get("Content-Type") || "")) continue;
        const ind = await r.json();
        if (ind.sintetico) continue;
        m.addSource("corpi", { type: "vector", url: `pmtiles://${new URL(b + "corpi.pmtiles", location.href).href}`, attribution: ind.attribuzione || "" });
        m.addLayer({ id: "edifici", type: "line", source: "corpi", "source-layer": "corpi", paint: { "line-color": colore("--primario"), "line-width": 1.2 } });
        stato.edifici = ind;
        return true;
      } catch { /* prossimo archivio */ }
    }
    $("edifici").disabled = true; $("edifici").parentElement.append(" – archivio degli edifici non ancora sul server");
    return false;
  }

  async function siti() {
    try {
      const r = await fetch("/edifici3d/cc-by/ortofoto_siti/indice.json");
      if (!r.ok || !/json/.test(r.headers.get("Content-Type") || "")) return;
      const l = (await r.json()).siti || [];
      for (const x of l) stato.fonti.unshift({ id: `sito-${x.sito}`, nome: `${x.sito} – AGEA ${x.anno} (50 cm)`, licenza: x.licenza,
        citazione: x.citazione, scheda: x.scheda, stato: "confermata", copia: true, nei_report: true, zoom: x.zoom, riquadro: x.riquadro, pmtiles: x.pmtiles });
      if (l.length) { const d = $("siti"); d.hidden = false; d.textContent = `Ortofoto dei siti già pronte: ${l.map((x) => x.sito).join(", ")}.`; }
    } catch { /* nessun sito */ }
  }

  // ------------------------------------------------------------------ regioni e comuni (piccola mappa e mappa grande)
  async function vaiRegione(cod) {
    const b = C && await C.riquadroRegione(cod);
    if (!b) return;
    stato.regione = cod; stato.comune = null;
    if (stato.confini) { stato.confini.scegliRegione(cod); stato.confini.scegliComune(""); }
    if (window.EUGENIO && window.EUGENIO.seleziona) window.EUGENIO.seleziona(cod);
    stato.mappa.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 20, duration: 700 });
  }
  function togliRegione() {
    stato.regione = null; stato.comune = null;
    if (stato.confini) { stato.confini.scegliRegione(""); stato.confini.scegliComune(""); }
    if (window.EUGENIO && window.EUGENIO.evidenziaPiccola) window.EUGENIO.evidenziaPiccola(null);
    const I = C ? C.ITALIA : [6.6, 35.4, 18.6, 47.1];
    stato.mappa.fitBounds([[I[0], I[1]], [I[2], I[3]]], { padding: 10, duration: 700 });
  }
  if (window.EUGENIO) {
    window.EUGENIO.suRegione = (cod) => { vaiRegione(cod); };
    window.EUGENIO.suStessaRegione = (cod) => { if (stato.regione === cod) togliRegione(); else vaiRegione(cod); };
    window.EUGENIO.mappaPrincipale = { nazionale: togliRegione };
  }

  // ------------------------------------------------------------------ immagine della vista
  function opzioniImmagine() {
    const f = stato.scelta, m = stato.mappa;
    if (f && !f.copia) return `«${f.nome}» è solo in consultazione dal vivo: non si può scaricare. Scegli un'altra fonte.`;
    const c = m.getCenter(), p = [c.lng, c.lat], z = m.getZoom(), righe = [];
    const fotoVisibile = f && f.id !== CONTESTO && copre(f, p) && z >= f.zoom[0] - 0.01;
    if (fotoVisibile || (f && f.id === CONTESTO))
      righe.push(`Ortofoto: ${f.citazione} – licenza ${f.licenza} (${f.scheda})${f.stato === "da confermare" ? "; uso tramite il server di EuGEnio in attesa di conferma della fonte" : ""}.`);
    if (stato.contesto && copre(stato.contesto, p) && !fotoVisibile && (!f || f.id !== CONTESTO))
      righe.push(`Contesto: ${stato.contesto.citazione} – licenza ${stato.contesto.licenza} (${stato.contesto.scheda}).`);
    if (stato.edifici && m.getLayer("edifici") && m.getLayoutProperty("edifici", "visibility") !== "none")
      righe.push(`Edifici: ${stato.edifici.attribuzione || "DBTR Emilia-Romagna"} (${stato.edifici.licenza || "CC BY 4.0"}).`);
    righe.push(`${C ? C.ATTRIBUZIONE : "Confini: ISTAT (CC BY 4.0)"}. Mappa: MapLibre GL JS (BSD-3).`);
    const pos = `centro ${c.lat.toFixed(5)} N, ${c.lng.toFixed(5)} E, zoom ${z.toFixed(1)}`;
    return { titolo: `Ortofoto – ${pos}`, righe, nome: `ortofoto_${c.lat.toFixed(4)}_${c.lng.toFixed(4)}` };
  }

  (async function avvio() {
    const m = new window.maplibregl.Map({ container: box, center: centro, zoom: Number(q.get("z")) || 16, maxZoom: 21, minZoom: 4.5,
      attributionControl: false, canvasContextAttributes: { preserveDrawingBuffer: true },
      style: { version: 8, sources: {}, layers: [{ id: "sfondo", type: "background", paint: { "background-color": colore("--carta") } }] } });
    stato.mappa = m;
    m.addControl(new window.maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.addControl(new window.maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    m.addControl(new window.maplibregl.AttributionControl({ compact: true }), "bottom-right");
    await new Promise((ok) => m.on("load", ok));
    // attribuzione compatta chiusa (le citazioni complete sono sotto la mappa): aperta copriva il fondo della mappa
    box.querySelectorAll(".maplibregl-compact-show").forEach((x) => x.classList.remove("maplibregl-compact-show"));
    document.addEventListener("eugenio:ridimensiona", () => m.resize());
    document.addEventListener("eugenio:aspetto", () => {
      m.setPaintProperty("sfondo", "background-color", colore("--carta"));
      if (m.getLayer("edifici")) m.setPaintProperty("edifici", "line-color", colore("--primario"));
    });
    if (window.pmtiles) { const proto = new window.pmtiles.Protocol(); window.maplibregl.addProtocol("pmtiles", proto.tile); }
    // i confini prima di tutto: ci sono anche se il servizio delle ortofoto non risponde
    if (C) {
      try {
        stato.confini = await C.aggiungi(m, {
          suRegione: (cod) => { if (stato.regione === cod) togliRegione(); else vaiRegione(cod); },
          suComune: async (c) => {
            stato.comune = c;
            const x = $("messaggio-mappa");
            if (!c) { x.textContent = ""; return; }
            const b = await C.riquadroComune(c.istat);
            if (b) m.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 30, duration: 700, maxZoom: 16 });
            x.textContent = `Comune di ${c.nome}${c.prov ? ` (${c.prov})` : ""}: un secondo clic sul comune lo toglie.`;
          },
        });
      } catch { /* confini non disponibili */ }
    }
    try {
      const r = await fetch("/api/ortofoto/fonti");
      if (!r.ok || !/json/.test(r.headers.get("Content-Type") || "")) throw new Error(String(r.status));
      stato.fonti = (await r.json()).fonti || [];
    } catch {
      messaggio("Il servizio delle ortofoto non risponde: riprova più tardi. Restano i confini.", true); attribuzione(null); aggiornaAvviso();
      return;
    }
    await siti();
    await edifici(m);
    contesto();
    $("edifici").addEventListener("change", (e) => { if (m.getLayer("edifici")) m.setLayoutProperty("edifici", "visibility", e.target.checked ? "visible" : "none"); });
    const c = [m.getCenter().lng, m.getCenter().lat], qui = stato.fonti.filter((f) => copre(f, c) && f.id !== CONTESTO);
    const chiesta = stato.fonti.find((f) => f.id === q.get("fonte"));
    scegli(chiesta ? chiesta.id : qui.length ? qui[0].id : "");
    elenco();
    m.on("moveend", elenco);
    m.on("zoomend", aggiornaAvviso);
    m.on("error", (e) => { if (e && (e.sourceId === "ortofoto" || e.sourceId === "contesto")) messaggio("Alcune tessere non sono arrivate (fonte lenta o fuori zona).", true); });
    if (window.EUGENIO_ESPORTA) {
      window.EUGENIO_ESPORTA.pulsanti($("scarica-ortofoto"), m, opzioniImmagine, (t, e) => {
        const x = $("messaggio-immagine"); x.textContent = t; x.classList.toggle("errore", !!e);
      });
    }
  })();
  window.EUGENIO_ORTOFOTO = { stato, opzioniImmagine };
})();
