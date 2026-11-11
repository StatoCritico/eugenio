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
// Seconda pubblicazione del 05/11/2026: ricerca per indirizzo o per comune, foglio e particella (cerca_luogo.js, lo stesso
// modulo di Modelli 3D) che porta la mappa sul punto con un segnaposto; strati attivabili sopra la foto (strati_gl.js:
// particelle catastali dell'Agenzia delle Entrate, contorni degli edifici) con legenda e attribuzione sotto la mappa e
// nell'immagine scaricata; messaggio dell'immagine solo a file davvero salvato o avviato (esporta_mappa.js).
// Indirizzo: ?lat=…&lon=…&z=… per aprire su un punto (senza: Cesena, ospedale Bufalini), ?fonte=<id> per scegliere la fonte.
// 08/11/2026: frecce sotto la mappa, accanto a «Scarica l'immagine», per spostare l'ortofoto di 1 m rispetto agli strati
// vettoriali (sposta_ortofoto.js; il proxy chiede alla fonte WMS il riquadro spostato). Attive solo con un'ortofoto
// spostabile e almeno uno strato vettoriale acceso (contorni dell'archivio, particelle, contorni degli edifici).
(function () {
  const $ = (id) => document.getElementById(id);
  const box = $("mappa-ortofoto");
  if (!box || !window.maplibregl) return;
  const C = window.EUGENIO_CONFINI;
  const q = new URLSearchParams(location.search);
  // (08/11/2026) senza ?lat=&lon= si apre su Cesena, ospedale Bufalini, in collina (cerca_luogo.js, PARTENZA)
  const P0 = window.EUGENIO_CERCA && window.EUGENIO_CERCA.PARTENZA;
  const conPunto = Number.isFinite(Number(q.get("lon"))) && Number.isFinite(Number(q.get("lat"))) && q.get("lon") && q.get("lat");
  const centro = conPunto ? [Number(q.get("lon")), Number(q.get("lat"))] : P0 ? [P0.lon, P0.lat] : [12.5683, 44.0594];
  const zoomIniziale = Number(q.get("z")) || (conPunto || !P0 ? 16 : P0.zoom);
  const CONTESTO = "s2cloudless2016";
  const stato = { fonti: [], scelta: null, mappa: null, contesto: null, edifici: null, confini: null, regione: null, comune: null, strati: null, cercato: null };
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
  // indirizzo delle tessere della fonte scelta, con lo spostamento manuale (il contesto sotto resta fermo)
  const tessere = (f, spostata) => location.origin + (spostata && stato.sposta ? stato.sposta.url(f.tessere) : f.tessere);
  function sorgente(f, spostata = false) {
    return f.pmtiles
      ? { type: "raster", url: `pmtiles://${location.origin}${f.pmtiles}`, tileSize: 256, attribution: f.citazione }
      : { type: "raster", tiles: [tessere(f, spostata)], tileSize: 256, minzoom: f.zoom[0], maxzoom: f.zoom[1], bounds: f.riquadro, attribution: f.citazione };
  }
  const sopraLe = () => ["strato-particelle", "strato-dbtr_edifici", "strato-osm", "edifici", "cercato", "confini-comuni-clic", "confini-regioni-clic"].find((id) => stato.mappa.getLayer(id));
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
    aggiornaSposta();
    if (f && f.id !== CONTESTO) {
      m.addSource("ortofoto", sorgente(f, true));
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
  // strati vettoriali accesi sopra la foto: contorni dell'archivio 3D, particelle, contorni degli edifici
  function vettoriAccesi() {
    const e = $("edifici"), st = stato.strati && stato.strati.stato;
    return !!((e && e.checked && !e.disabled && (stato.stratiEdifici || []).length) || (st && (st.particelle || st.edifici)));
  }
  function aggiornaSposta() { if (stato.sposta) stato.sposta.fonte(stato.scelta, { vettori: vettoriAccesi() }); }
  function spostaTessere() {
    const m = stato.mappa, f = stato.scelta, src = m && m.getSource("ortofoto");
    if (src && f && !f.pmtiles && src.setTiles) src.setTiles([tessere(f, true)]);    // la camera non si muove
  }
  // (09/11/2026 c, prove P9 di Paolo) solo le fonti applicabili nel punto (regione e riquadro: EUGENIO_CONFINI.fontiNelPunto):
  // a Firenze la Toscana e non la RER, in Veneto AGEA 2012 e Sentinel-2. Finché l'utente non sceglie a mano si usa la
  // migliore (regionale a 20 cm dove ha immagini, poi AGEA 2012, poi Sentinel-2); una scelta a mano resta finché la fonte
  // è applicabile, poi si torna all'automatico con una nota breve
  let giro = 0;
  async function elenco() {
    const mio = ++giro, c = stato.mappa.getCenter();
    let qui;
    try { qui = C && C.fontiNelPunto ? await C.fontiNelPunto(stato.fonti, c.lng, c.lat) : null; } catch { qui = null; }
    if (!qui) qui = stato.fonti.filter((f) => copre(f, [c.lng, c.lat]));
    if (mio !== giro) return;
    const fs = $("fonti");
    fs.querySelectorAll("label").forEach((x) => x.remove());
    let nota = "";
    if (stato.manuale && stato.scelta && !qui.some((f) => f.id === stato.scelta.id)) {
      nota = `«${stato.scelta.nome}» non copre questo punto: torno alla scelta automatica`;
      stato.manuale = false;
    }
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
    // (09/11/2026) le fonti che il server ha dichiarato vuote in questa zona (X-Ortofoto-Vuota: RER 2023-24 a Bologna,
    // Modena, Faenza…) non si scelgono da sole
    const migliore = qui.find((f) => f.id !== CONTESTO && !stato.vuote.has(zonaVuota(f, c))) || qui[0];
    if (!stato.manuale && migliore && (!stato.scelta || stato.scelta.id !== migliore.id)) scegli(migliore.id);
    if (nota) messaggio(`${nota}${migliore ? ` («${migliore.nome}»)` : ""}.`);
    else if (!qui.length) messaggio("Nessuna ortofoto copre questa zona: restano i confini.", true);
    else if (/^Nessuna ortofoto copre/.test($("messaggio").textContent)) messaggio("");
    if (!stato.manuale && stato.scelta) provaVuota(stato.scelta);
    aggiornaAvviso();
  }
  const zonaVuota = (f, c) => { const n = 2 ** 12; return `${f.id}@${Math.floor((c.lng + 180) / 360 * n)}_${Math.floor((1 - Math.asinh(Math.tan(c.lat * Math.PI / 180)) / Math.PI) / 2 * n)}`; };
  stato.vuote = new Set(); stato.provate = new Set();
  async function provaVuota(f) {
    const m = stato.mappa, c = m.getCenter(), k = zonaVuota(f, c);
    if (!f.tessere || f.pmtiles || f.id === CONTESTO || stato.provate.has(k) || m.getZoom() < f.zoom[0] - 0.5) return;
    stato.provate.add(k);
    const z = Math.max(f.zoom[0], Math.min(f.zoom[1], Math.floor(m.getZoom()))), n = 2 ** z;
    const x = Math.floor((c.lng + 180) / 360 * n), y = Math.floor((1 - Math.asinh(Math.tan(c.lat * Math.PI / 180)) / Math.PI) / 2 * n);
    try {
      const r = await fetch(location.origin + f.tessere.replace("{z}", z).replace("{x}", x).replace("{y}", y));
      if (r.ok && r.headers.get("X-Ortofoto-Vuota") === "1") {
        stato.vuote.add(k);
        if (!stato.manuale && stato.scelta && stato.scelta.id === f.id) {
          await elenco();
          const g = stato.scelta;
          messaggio(`«${f.nome}» non ha immagini in questa zona${g && g.id !== f.id ? `: uso «${g.nome}»` : ""}. Puoi scegliere un'altra fonte.`);
        }
      }
    } catch { /* resta la fonte scelta */ }
  }

  async function edifici(m) {
    // contorni dei corpi dall'archivio 3D (dati veri): solo per riconoscere i tetti. La demo sintetica non si sovrappone
    // mai alla foto: le sue sagome sono inventate e non corrispondono a nessun edificio (05/11/2026, «edifici storti»)
    // archivi di /edifici3d/archivi.json (dal 07/11/2026 un archivio DBTR per comune), altrimenti il DBTR dell'ER
    let basi = ["/edifici3d/cc-by/er/prodotti/"];
    try {
      const r = await fetch("/edifici3d/archivi.json?v=20261111b", { cache: "no-cache" });
      if (r.ok && /json/.test(r.headers.get("Content-Type") || "")) {
        const l = ((await r.json()).archivi || []).map((x) => x && x.base)
          .filter((b) => typeof b === "string" && /^\/edifici3d\/[\w-]+(\/[\w-]+)*\/$/.test(b) && !b.includes(".."));
        if (l.length) basi = l.slice(0, 150);       // 150 archivi al massimo (60 fino al 09/11/2026)
      }
    } catch { /* solo l'archivio regionale */ }
    const ids = [];
    // indici chiesti tutti insieme (09/11/2026: 69 archivi; prima uno dopo l'altro), strati aggiunti nell'ordine dell'elenco
    const indici = await Promise.all(basi.map((b) => fetch(`${b}indice.json`)
      .then((r) => (r.ok && /json/.test(r.headers.get("Content-Type") || "") ? r.json() : null)).catch(() => null)));
    for (const [k, b] of basi.entries()) {
      try {
        const ind = indici[k];
        if (!ind || ind.sintetico) continue;
        const id = k ? `edifici-${k}` : "edifici";
        m.addSource(`corpi-${k}`, { type: "vector", url: `pmtiles://${new URL(b + "corpi.pmtiles", location.href).href}`, attribution: ind.attribuzione || "" });
        m.addLayer({ id, type: "line", source: `corpi-${k}`, "source-layer": "corpi", paint: { "line-color": colore("--primario"), "line-width": 1.2 } });
        ids.push(id);
        if (!stato.edifici) stato.edifici = ind;
      } catch { /* prossimo archivio */ }
    }
    stato.stratiEdifici = ids;
    if (ids.length) return true;
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
  // sposta = false (clic sulla mappa grande, 09/11/2026): un clic sulla mappa non sposta mai la vista
  async function vaiRegione(cod, sposta = true) {
    const b = C && await C.riquadroRegione(cod);
    if (!b) return;
    stato.regione = cod; stato.comune = null;
    if (stato.confini) { stato.confini.scegliRegione(cod); stato.confini.scegliComune(""); }
    if (window.EUGENIO && window.EUGENIO.seleziona) window.EUGENIO.seleziona(cod);
    if (sposta) stato.mappa.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 20, duration: 700 });
  }
  function togliRegione(sposta = true) {
    stato.regione = null; stato.comune = null;
    if (stato.confini) { stato.confini.scegliRegione(""); stato.confini.scegliComune(""); }
    if (window.EUGENIO && window.EUGENIO.evidenziaPiccola) window.EUGENIO.evidenziaPiccola(null);
    const I = C ? C.ITALIA : [6.6, 35.4, 18.6, 47.1];
    if (sposta) stato.mappa.fitBounds([[I[0], I[1]], [I[2], I[3]]], { padding: 10, duration: 700 });
  }
  if (window.EUGENIO) {
    window.EUGENIO.suRegione = (cod) => { vaiRegione(cod); };
    window.EUGENIO.suStessaRegione = (cod) => { if (stato.regione === cod) togliRegione(); else vaiRegione(cod); };
    window.EUGENIO.mappaPrincipale = { nazionale: () => togliRegione() };
  }

  // ------------------------------------------------------------------ immagine della vista
  function opzioniImmagine() {
    const f = stato.scelta, m = stato.mappa;
    if (f && !f.copia) return `«${f.nome}» è solo in consultazione dal vivo: non si può scaricare. Scegli un'altra fonte.`;
    const c = m.getCenter(), p = [c.lng, c.lat], z = m.getZoom(), righe = [];
    const fotoVisibile = f && f.id !== CONTESTO && copre(f, p) && z >= f.zoom[0] - 0.01;
    if (fotoVisibile || (f && f.id === CONTESTO))
      righe.push(`Ortofoto: ${f.citazione} – licenza ${f.licenza} (${f.scheda})${f.stato === "da confermare" ? "; uso tramite il server di EuGEnio in attesa di conferma della fonte" : ""}.`);
    if (fotoVisibile && stato.sposta && stato.sposta.riga()) righe.push(stato.sposta.riga());
    if (stato.contesto && copre(stato.contesto, p) && !fotoVisibile && (!f || f.id !== CONTESTO))
      righe.push(`Contesto: ${stato.contesto.citazione} – licenza ${stato.contesto.licenza} (${stato.contesto.scheda}).`);
    if (stato.edifici && m.getLayer("edifici") && m.getLayoutProperty("edifici", "visibility") !== "none")   // stessa visibilità per tutti
      righe.push(`Edifici: ${stato.edifici.attribuzione || "DBTR Emilia-Romagna"} (${stato.edifici.licenza || "CC BY 4.0"}).`);
    if (stato.strati) righe.push(...stato.strati.righe());
    if (stato.cercato) righe.push(`Punto cercato: ${stato.cercato}.`);
    righe.push(`${C ? C.ATTRIBUZIONE : "Confini: ISTAT (CC BY 4.0)"}. Mappa: MapLibre GL JS (BSD-3).`);
    const pos = `centro ${c.lat.toFixed(5)} N, ${c.lng.toFixed(5)} E, zoom ${z.toFixed(1)}`;
    return { titolo: `Ortofoto – ${pos}`, righe, nome: `ortofoto_${c.lat.toFixed(4)}_${c.lng.toFixed(4)}` };
  }

  (async function avvio() {
    const m = new window.maplibregl.Map({ container: box, center: centro, zoom: zoomIniziale, maxZoom: 21, minZoom: 4.5,
      attributionControl: false, canvasContextAttributes: { preserveDrawingBuffer: true },
      style: { version: 8, sources: {}, layers: [{ id: "sfondo", type: "background", paint: { "background-color": colore("--carta") } }] } });
    stato.mappa = m;
    if (window.EUGENIO_LIMITI) window.EUGENIO_LIMITI.collega(m);      // 429 delle fonti: pausa, nota e niente righe rosse (09/11/2026)
    m.addControl(new window.maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.addControl(new window.maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    m.addControl(new window.maplibregl.AttributionControl({ compact: true }), "bottom-right");
    await new Promise((ok) => m.on("load", ok));
    // attribuzione compatta chiusa (le citazioni complete sono sotto la mappa): aperta copriva il fondo della mappa
    box.querySelectorAll(".maplibregl-compact-show").forEach((x) => x.classList.remove("maplibregl-compact-show"));
    document.addEventListener("eugenio:ridimensiona", () => m.resize());
    document.addEventListener("eugenio:aspetto", () => {
      m.setPaintProperty("sfondo", "background-color", colore("--carta"));
      (stato.stratiEdifici || []).forEach((id) => { if (m.getLayer(id)) m.setPaintProperty(id, "line-color", colore("--primario")); });
    });
    if (window.EUGENIO_SPOSTA && $("sposta-ortofoto"))
      stato.sposta = window.EUGENIO_SPOSTA.crea($("sposta-ortofoto"), { pagina: "ortofoto", suCambio: spostaTessere });
    if (window.pmtiles) { const proto = new window.pmtiles.Protocol(); window.maplibregl.addProtocol("pmtiles", proto.tile); }
    // i confini prima di tutto: ci sono anche se il servizio delle ortofoto non risponde
    if (C) {
      try {
        stato.confini = await C.aggiungi(m, {
          // (09/11/2026, punto J) il clic sulla mappa evidenzia soltanto: la vista non si sposta mai
          suRegione: (cod) => { if (stato.regione === cod) togliRegione(false); else vaiRegione(cod, false); },
          suComune: async (c) => {
            stato.comune = c;
            const x = $("messaggio-mappa");
            if (!c) { x.textContent = ""; return; }
            x.textContent = `Comune di ${c.nome}${c.prov ? ` (${c.prov})` : ""}: avvicinati con la rotella o cerca l'indirizzo; un secondo clic sul comune lo toglie.`;
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
    // segnaposto del punto cercato (sopra la foto e gli strati, sotto i confini cliccabili)
    m.addSource("cercato", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    m.addLayer({ id: "cercato", type: "circle", source: "cercato", paint: { "circle-radius": 7, "circle-color": colore("--primario"),
      "circle-stroke-color": "#fff", "circle-stroke-width": 2 } }, ["confini-comuni-clic", "confini-regioni-clic"].find((id) => m.getLayer(id)));
    if (window.EUGENIO_STRATI) {
      try {
        stato.strati = await window.EUGENIO_STRATI.aggiungi(m, { caselle: $("caselle-strati"), legenda: $("legenda-strati"),
          sotto: () => ["edifici", "cercato", "confini-comuni-clic", "confini-regioni-clic"].find((id) => m.getLayer(id)) });
      } catch { /* strati non disponibili */ }
    }
    $("edifici").addEventListener("change", (e) => (stato.stratiEdifici || []).forEach((id) => { if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", e.target.checked ? "visible" : "none"); }));
    $("edifici").addEventListener("change", aggiornaSposta);
    if ($("caselle-strati")) $("caselle-strati").addEventListener("change", aggiornaSposta);
    // fonte chiesta nell'indirizzo (?fonte=): vale come scelta a mano (resta finché è applicabile); altrimenti la migliore
    const chiesta = stato.fonti.find((f) => f.id === q.get("fonte"));
    if (chiesta) { stato.manuale = true; scegli(chiesta.id); }
    await elenco();
    m.on("moveend", elenco);
    m.on("zoomend", aggiornaAvviso);
    m.on("error", (e) => { if (e && (e.sourceId === "ortofoto" || e.sourceId === "contesto")) messaggio("Alcune tessere non sono arrivate (fonte lenta o fuori zona).", true); });
    if (window.EUGENIO_ESPORTA) window.EUGENIO_ESPORTA.pulsanti($("scarica-ortofoto"), m, opzioniImmagine, $("messaggio-immagine"));
  })();

  // ricerca per indirizzo o per dati catastali: la mappa va sul punto, con il segnaposto
  if (window.EUGENIO_CERCA) {
    window.EUGENIO_CERCA.crea($("cerca-luogo"), {
      suTrovato: (lon, lat, riga) => {
        const m = stato.mappa;
        if (!m || !m.getSource("cercato")) return;
        m.getSource("cercato").setData({ type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [lon, lat] } }] });
        stato.cercato = riga.centro_comune ? `centro del comune di ${riga.comune_catasto} (confini ISTAT, CC BY 4.0)`
          : `${[riga.indirizzo_trovato, riga.comune_catasto].filter(Boolean).join(", ") || `${lat.toFixed(5)}, ${lon.toFixed(5)}`}`
          + ` (${riga.fonte_punto === "ANNCSU" ? "ANNCSU – Agenzia delle Entrate e ISTAT, CC BY 4.0" : "dati elaborati da Zornade, zornade.com"})`;
        m.flyTo({ center: [lon, lat], zoom: riga.zoom || (window.EUGENIO_CERCA && window.EUGENIO_CERCA.ZOOM) || 17, duration: 900 });
      },
    });
  }
  window.EUGENIO_ORTOFOTO = { stato, opzioniImmagine };
})();
