"use strict";
// Statistiche › «Stato della rete elettrica» (rete-elettrica.html, 17/11/2026, richiesta di Paolo). Mappa MapLibre della
// regione scelta (piccola mappa e clic, come Ortofoto: confini_gl.js) con quattro strati spegnibili, ciascuno con la sua
// legenda: criticità dei comuni (pieno o a strisce, regola in rete.js), comuni serviti da altri distributori (retino),
// cabine primarie (punti grandi colorati), interruzioni in corso. A destra le date di aggiornamento (/api/rete/stato), le
// province senza dato e, scelto un comune, criticità, cabine, interruzioni in corso e statistiche storiche
// (/api/rete/interruzioni/comune/<istat>). Download: immagine della mappa (esporta_mappa.js) e dati CSV, Excel, PDF
// (rete.js), con fonti e licenze (ODbL per le posizioni delle cabine). ?prova=1: dati sintetici (rete.js).
(function () {
  const $ = (id) => document.getElementById(id);
  const box = $("mappa-rete");
  const R = window.EUGENIO_RETE, C = window.EUGENIO_CONFINI;
  if (!box || !window.maplibregl || !R || !C) return;
  const E = window.EUGENIO;
  const st = { mappa: null, regione: null, nomeRegione: "", righe: [], perIstat: new Map(), comuniFc: null, cabine: null, interruzioni: null,
    stato: null, scelto: null, dettaglio: null, giro: 0, giroComune: 0, nomiProvince: new Map() };
  const vuota = () => ({ type: "FeatureCollection", features: [] });
  const colore = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || "#888";
  function h(tag, cls, t) { const e = document.createElement(tag); if (cls) e.className = cls; if (t !== undefined && t !== null) e.textContent = t; return e; }
  function messaggio(id, t, errore = false) { const m = $(id); if (!m) return; m.textContent = t; m.classList.toggle("errore", errore); }
  const STRATI = {
    criticita: ["rete-pieno", "rete-strisce", "rete-senza-dato", "rete-in-parte"],
    nonConc: ["rete-non-conc"],
    cabine: ["rete-cabine-punti"],
    interruzioni: ["rete-interruzioni"],
  };
  const acceso = (k) => { const i = { criticita: "strato-criticita", nonConc: "strato-non-concessionari", cabine: "strato-cabine", interruzioni: "strato-interruzioni" }[k]; return !$(i) || $(i).checked; };
  // campi delle interruzioni attive: nomi del contratto con i ripieghi sui nomi della fonte
  const I = {
    inizio: (p) => p.inizio || p.data_interruzione,
    ripristino: (p) => p.ripristino_previsto || p.data_prev_ripristino || null,
    ripristinoTesto: (p) => { const r = p.ripristino_previsto || p.data_prev_ripristino; return r ? R.oraIt(r) : (p.ripristino_testo || "non indicato"); },
    fine: (p) => p.fine_stimata || (p.chiusa_il ? p.ultima_lettura || p.chiusa_il : null),
    clienti: (p) => (p.clienti !== undefined ? p.clienti : p.num_cli_disalim),
    clientiComune: (p) => (p.clienti_comune !== undefined ? p.clienti_comune : (p.clienti !== undefined ? p.clienti : p.num_cli_disalim)),
    causa: (p) => p.causa || p.causa_interruzione || p.causa_disalimentazione || "",
    durata: (p) => (p.durata_min !== undefined ? p.durata_min : p.durata_finora_min),
    comune: (p) => String(p.comune || "").padStart(6, "0"),
  };
  // (17/11/2026 sera, decisione di Paolo) comuni segnati «non serviti» da e-distribuzione ma con suoi trasformatori: colore
  // della criticità come gli altri, bordo tratteggiato e la nota del servizio
  const inParte = (r) => !!(r && r.concessionario !== false && r.servito_in_parte);
  const notaInParte = () => (st.stato && st.stato.nota_servito_in_parte) || "servito in parte da un altro distributore";
  const durata = (min) => (min === null || min === undefined || !Number.isFinite(+min) ? "–"
    : +min < 60 ? `${Math.round(+min)} min` : `${Math.floor(+min / 60)} h ${String(Math.round(+min % 60)).padStart(2, "0")} min`);

  R.avvisoProva(document.querySelector(".pannello"));

  // ------------------------------------------------------------------ stato dei dati
  async function caricaStato() {
    try {
      st.stato = await R.api("/api/rete/stato");
    } catch (e) {
      st.stato = null;
      const dl = $("stato-rete"); dl.innerHTML = "";
      dl.append(h("dt", null, "Stato"), h("dd", null, "non disponibile"));
      messaggio("messaggio-stato", `Il servizio della rete non risponde (${e.message}): riprova più tardi.`, true);
      return;
    }
    messaggio("messaggio-stato", "");
    const s = st.stato, dl = $("stato-rete"); dl.innerHTML = "";
    const riga = (k, v) => dl.append(h("dt", null, k), h("dd", null, v));
    riga("Saturazione delle cabine", `aggiornata il ${R.oraIt(s.saturazione_aggiornata)} (dato mensile di e-distribuzione, letto ogni notte)`);
    riga("Interruzioni", `lette il ${R.oraIt(s.interruzioni_aggiornate)} (ogni 15 minuti)`);
    riga("Interruzioni in corso", R.num(s.attive));
    const dal = s.raccolta_dal || s.raccolta_interruzioni_dal;
    if (dal) riga("Raccolta delle interruzioni", `dal ${R.dataIt(dal)}`);
    const ferme = Object.keys(s.province_non_aggiornate || {});
    if (ferme.length) riga("Province con il dato non aggiornato", ferme.map((c) => `${st.nomiProvince.get(c) || c} (ultimo dato del ${R.dataIt(s.province_non_aggiornate[c])})`).join(", "));
    avvisoProvince();
  }
  function provinceMancanti() {
    return ((st.stato && st.stato.province_mancanti) || []).map((p) => (typeof p === "string" ? { cod: p, nome: "" } : { cod: String(p.cod || ""), nome: p.nome || "" }));
  }
  // «di Torino (001)» se il nome è noto (dal servizio o dai confini della regione aperta), altrimenti «con codice ISTAT 001»
  const nomeProvincia = (p) => { const n = p.nome || st.nomiProvince.get(p.cod); return n ? `di ${n} (${p.cod})` : `con codice ISTAT ${p.cod}`; };
  function avvisoProvince() {
    const a = $("avviso-province"), l = provinceMancanti();
    if (!l.length) { a.hidden = true; return; }
    const nomi = l.map(nomeProvincia);
    a.innerHTML = "";
    const d = h("div");
    d.append(h("b", null, `Dato non disponibile per ${l.length === 1 ? "la provincia" : "le province"} ${nomi.join(", ")}`),
      "Il servizio di e-distribuzione oggi non restituisce i trasformatori di questa provincia: i suoi comuni sono grigi a righe sottili. Si riprova a ogni aggiornamento notturno.");
    a.appendChild(d); a.hidden = false;
  }

  // ------------------------------------------------------------------ mappa
  async function avvio() {
    const m = new window.maplibregl.Map({ container: box, center: [12.4, 42.6], zoom: 5, maxZoom: 16, minZoom: 4.5, attributionControl: false,
      canvasContextAttributes: { preserveDrawingBuffer: true },
      style: { version: 8, sources: {}, layers: [{ id: "sfondo", type: "background", paint: { "background-color": colore("--carta") } }] } });
    st.mappa = m;
    m.addControl(new window.maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.addControl(new window.maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    m.addControl(new window.maplibregl.AttributionControl({ compact: true }), "bottom-right");
    await new Promise((ok) => m.on("load", ok));
    box.querySelectorAll(".maplibregl-compact-show").forEach((x) => x.classList.remove("maplibregl-compact-show"));
    document.addEventListener("eugenio:ridimensiona", () => m.resize());
    R.immagini(m);
    try { await C.aggiungi(m, { clic: false }); } catch { messaggio("messaggio-mappa", "Confini non disponibili."); }
    const prima = m.getLayer("confini-regioni-clic") ? "confini-regioni-clic" : undefined;
    m.addSource("rete-comuni", { type: "geojson", data: vuota(), attribution: R.ATTR.criticita });
    m.addLayer({ id: "rete-pieno", type: "fill", source: "rete-comuni", filter: ["has", "pieno"],
      paint: { "fill-color": ["match", ["get", "pieno"], "GIALLO", R.COLORI.GIALLO, "ARANCIONE", R.COLORI.ARANCIONE, "ROSSO", R.COLORI.ROSSO, R.COLORI.GRIGIO], "fill-opacity": 0.78 } }, prima);
    m.addLayer({ id: "rete-strisce", type: "fill", source: "rete-comuni", filter: ["has", "strisce"],
      paint: { "fill-pattern": ["concat", "strisce-", ["get", "strisce"]], "fill-opacity": 0.85 } }, prima);
    m.addLayer({ id: "rete-senza-dato", type: "fill", source: "rete-comuni", filter: ["==", ["get", "mancante"], true],
      paint: { "fill-pattern": "senza-dato", "fill-opacity": 0.8 } }, prima);
    m.addLayer({ id: "rete-non-conc", type: "fill", source: "rete-comuni", filter: ["==", ["get", "conc"], false],
      paint: { "fill-pattern": "retino", "fill-opacity": 0.9 } }, prima);
    m.addLayer({ id: "rete-comuni-linee", type: "line", source: "rete-comuni",
      paint: { "line-color": colore("--inchiostro"), "line-width": ["interpolate", ["linear"], ["zoom"], 6, 0.3, 12, 1], "line-opacity": 0.45 } }, prima);
    m.addLayer({ id: "rete-in-parte", type: "line", source: "rete-comuni", filter: ["==", ["get", "in_parte"], true],
      paint: { "line-color": colore("--inchiostro"), "line-width": 2, "line-dasharray": [2, 1.5] } }, prima);
    m.addLayer({ id: "rete-comuni-clic", type: "fill", source: "rete-comuni", paint: { "fill-color": "#000", "fill-opacity": 0 } }, prima);
    m.addLayer({ id: "rete-comune-scelto", type: "line", source: "rete-comuni", filter: ["==", ["get", "istat"], ""],
      paint: { "line-color": colore("--primario"), "line-width": 3.5 } });
    m.addSource("rete-cabine", { type: "geojson", data: vuota(), attribution: "© contributori OpenStreetMap (ODbL); e-distribuzione" });
    R.stratoCabine(m, "rete-cabine");
    m.addSource("rete-int", { type: "geojson", data: vuota(), attribution: "Interruzioni: e-distribuzione" });
    m.addLayer({ id: "rete-interruzioni", type: "circle", source: "rete-int", paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 5, 4, 10, 6, 14, 8], "circle-color": "#2f6fdb",
      "circle-stroke-color": "#ffffff", "circle-stroke-width": 1.6 } });
    document.addEventListener("eugenio:aspetto", () => {
      m.setPaintProperty("sfondo", "background-color", colore("--carta"));
      m.setPaintProperty("rete-comuni-linee", "line-color", colore("--inchiostro"));
      m.setPaintProperty("rete-in-parte", "line-color", colore("--inchiostro"));
      m.setPaintProperty("rete-comune-scelto", "line-color", colore("--primario"));
    });
    R.suggerimento(m, () => ["rete-interruzioni", "rete-cabine-punti", "rete-comuni-clic"], contenutoSuggerimento);
    m.on("click", clic);
    for (const id of ["strato-criticita", "strato-non-concessionari", "strato-cabine", "strato-interruzioni"]) $(id).addEventListener("change", strati);
    strati();
    if (window.EUGENIO_ESPORTA) window.EUGENIO_ESPORTA.pulsanti($("scarica-mappa"), m, opzioniImmagine, $("messaggio-immagine"));
    R.pulsantiDati($("scarica-dati"), datiFile, $("messaggio-dati"));
    if (E) {
      E.suRegione = (cod) => vaiRegione(cod, true);
      E.suStessaRegione = (cod) => vaiRegione(cod, true);
      E.mappaPrincipale = { nazionale: () => m.fitBounds([[C.ITALIA[0], C.ITALIA[1]], [C.ITALIA[2], C.ITALIA[3]]], { padding: 10, duration: 600 }) };
    }
    const q = new URLSearchParams(location.search);
    await vaiRegione((E && E.regione) || "08", true, q.get("comune"));
    // aggiornamento automatico delle interruzioni (il servizio le legge ogni 15 minuti)
    setInterval(() => { caricaStato(); caricaInterruzioni(); }, 5 * 60 * 1000);
  }

  function strati() {
    const m = st.mappa;
    for (const [k, ids] of Object.entries(STRATI)) ids.forEach((id) => { if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", acceso(k) ? "visible" : "none"); });
    legenda();
  }
  function legenda() {
    const L = $("legenda-rete"); L.innerHTML = "";
    const voce = (i, t) => { const s = h("span"); s.append(i, t); L.appendChild(s); };
    if (acceso("criticita")) {
      for (const k of ["GIALLO", "ARANCIONE", "ROSSO"]) voce(R.campione("strisce", k), `qualche ${R.NOMI[k]} (fino a metà dei trasformatori)`);
      for (const k of ["GIALLO", "ARANCIONE", "ROSSO"]) voce(R.campione("pieno", k), `${R.NOMI[k]} (più di metà)`);
      voce(R.campione("senza-dato"), "dato non disponibile");
      voce(R.campione("in-parte"), notaInParte());
      const n = h("span", "legenda-nota", "Criticità dei comuni: classificazione di EuGEnio dai dati mensili per trasformatore di e-distribuzione; comuni senza colore: tutti i trasformatori verdi.");
      L.appendChild(n);
    }
    if (acceso("nonConc")) voce(R.campione("retino"), "comune con un altro distributore");
    if (acceso("cabine")) {
      voce(R.campione("cabina", "VERDE"), "cabina primaria: verde (bianco)");
      for (const k of ["GIALLO", "ARANCIONE", "ROSSO"]) voce(R.campione("cabina", k), R.NOMI[k]);
      voce(R.campione("cabina", "GRIGIO"), "altro distributore o senza dato");
    }
    if (acceso("interruzioni")) voce(R.campione("punto", "#2f6fdb"), "interruzione in corso");
  }

  function contenutoSuggerimento(f) {
    const p = f.properties || {};
    if (f.layer.id === "rete-cabine-punti") return { titolo: R.nomeCabina(p), righe: R.righeCabina(p) };
    if (f.layer.id === "rete-interruzioni") {
      const nome = p.nome_comune || (st.perIstat.get(I.comune(p)) || {}).nome || "";
      return { titolo: `Interruzione in corso${nome ? ` – ${nome}` : ""}`, righe: [
        `Causa: ${I.causa(p) || "non indicata"}`, `Clienti senza corrente: ${R.num(I.clienti(p))}`,
        `Inizio: ${R.oraIt(I.inizio(p))}`, `Ripristino previsto: ${I.ripristinoTesto(p)}`, `Durata finora (stimata): ${durata(I.durata(p))}`] };
    }
    const r = st.perIstat.get(p.istat);
    const titolo = `${p.nome}${p.prov ? ` (${p.prov})` : ""}`;
    if (p.mancante) return { titolo, righe: ["dato non disponibile per la provincia"], cursore: true };
    if (!r) return { titolo, righe: ["nessun dato"] };
    if (!r.concessionario) return { titolo, righe: ["distributore diverso da e-distribuzione"] };
    return { titolo, righe: [[r.pieno ? R.COLORI[r.pieno] : r.strisce ? R.COLORI[r.strisce[1]] : null, `criticità: ${R.testoClasse(r)}`],
      `trasformatori: ${R.testoTrasf(r.trasf)}`, ...(inParte(r) ? [notaInParte()] : []), "clic per i dettagli"] };
  }

  function clic(e) {
    const m = st.mappa, su = (ids) => ids.filter((id) => m.getLayer(id) && m.getLayoutProperty(id, "visibility") !== "none");
    if (m.queryRenderedFeatures(e.point, { layers: su(["rete-interruzioni", "rete-cabine-punti"]) }).length) return;
    const c = m.queryRenderedFeatures(e.point, { layers: su(["rete-comuni-clic"]) })[0];
    if (c) { if (st.scelto === c.properties.istat) togliComune(); else apriComune(c.properties.istat); return; }
    const r = m.getLayer("confini-regioni-clic") && m.queryRenderedFeatures(e.point, { layers: ["confini-regioni-clic"] })[0];
    if (r && r.properties.cod !== st.regione) vaiRegione(r.properties.cod, false);     // un clic sulla mappa non sposta la vista
  }

  // ------------------------------------------------------------------ regione
  async function vaiRegione(cod, sposta, comune = null) {
    const m = st.mappa, mio = ++st.giro;
    st.regione = cod; st.righe = []; st.perIstat = new Map();
    togliComune();
    if (E && E.seleziona) E.seleziona(cod);
    try {
      const it = E && E.italia ? await E.italia() : null;
      st.nomeRegione = (it && (it.regioni.find((x) => x.cod === cod) || {}).nome) || `regione ${cod}`;
    } catch { st.nomeRegione = `regione ${cod}`; }
    if (sposta) { const b = await C.riquadroRegione(cod); if (b && mio === st.giro) m.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 20, duration: 600 }); }
    if (m.getLayer("confini-regione-scelta")) m.setFilter("confini-regione-scelta", ["==", ["get", "cod"], cod]);
    messaggio("messaggio-mappa", `Carico i dati di ${st.nomeRegione}…`);
    if (!st.stato) await caricaStato();
    let fc, prov, righe = [], cabine = vuota(), errori = [];
    try { [fc, prov] = await Promise.all([C.comuniRegione(cod), C.provinceRegione(cod)]); } catch { fc = vuota(); prov = vuota(); }
    prov.features.forEach((p) => st.nomiProvince.set(p.properties.cod, p.properties.nome));
    avvisoProvince();
    const [a, b] = await Promise.allSettled([R.api(`/api/rete/comuni?regione=${cod}`), R.api(`/api/rete/cabine?regione=${cod}`)]);
    if (mio !== st.giro) return;
    if (a.status === "fulfilled" && Array.isArray(a.value)) righe = a.value; else errori.push(`criticità dei comuni (${a.reason ? a.reason.message : "risposta non valida"})`);
    if (b.status === "fulfilled") cabine = R.preparaCabine(b.value); else errori.push(`cabine primarie (${b.reason.message})`);
    st.righe = righe; st.perIstat = new Map(righe.map((r) => [String(r.istat).padStart(6, "0"), r])); st.comuniFc = fc; st.cabine = cabine;
    const mancanti = new Set(provinceMancanti().map((p) => p.cod));
    st.disegnati = { type: "FeatureCollection", features: fc.features.map((f) => {
      const r = st.perIstat.get(f.properties.istat), p = { ...f.properties };
      if (mancanti.has(f.properties.istat.slice(0, 3)) || (r && (r.mancante || (r.concessionario !== false && r.dato_disponibile === false)))) p.mancante = true;
      else if (r) {
        p.conc = r.concessionario !== false;
        if (p.conc && r.pieno) p.pieno = r.pieno;
        if (p.conc && Array.isArray(r.strisce) && r.strisce.length === 2) p.strisce = r.strisce[1];
        if (inParte(r)) p.in_parte = true;
      }
      return { type: "Feature", properties: p, geometry: f.geometry };
    }) };
    m.getSource("rete-comuni").setData(st.disegnati);
    m.getSource("rete-cabine").setData(cabine);
    const dl = $("comuni-rete"); dl.innerHTML = "";
    fc.features.map((f) => f.properties).sort((x, y) => x.nome.localeCompare(y.nome, "it")).forEach((p) => { const o = h("option"); o.value = `${p.nome} (${p.prov})`; dl.appendChild(o); });
    await caricaInterruzioni();
    if (mio !== st.giro) return;
    const conc = righe.filter((r) => r.concessionario !== false).length;
    messaggio("messaggio-mappa", errori.length ? `${st.nomeRegione}: non disponibili ${errori.join(" e ")}.`
      : `${st.nomeRegione}: ${R.num(cabine.features.length)} cabine primarie, ${R.num(conc)} comuni serviti da e-distribuzione su ${R.num(fc.features.length)}.`, !!errori.length);
    chiudiAttribuzione();
    if (comune && /^\d{6}$/.test(comune)) apriComune(comune);
  }
  // attribuzione compatta chiusa (le fonti complete sono sotto la mappa): MapLibre la riapre quando arrivano nuove fonti
  function chiudiAttribuzione() {
    const t = () => box.querySelectorAll(".maplibregl-compact-show").forEach((x) => x.classList.remove("maplibregl-compact-show"));
    t(); st.mappa.once("idle", t);
  }

  async function caricaInterruzioni() {
    if (!st.mappa || !st.regione) return;
    try {
      const d = await R.api(`/api/rete/interruzioni/attive?regione=${st.regione}`);
      st.interruzioni = { type: "FeatureCollection", features: ((d && d.features) || []).filter((f) => f.geometry && f.geometry.type === "Point") };
    } catch { st.interruzioni = vuota(); }
    st.mappa.getSource("rete-int").setData(st.interruzioni);
  }

  // ------------------------------------------------------------------ comune scelto
  function togliComune() {
    st.scelto = null; st.dettaglio = null; st.giroComune++;
    if (st.mappa && st.mappa.getLayer("rete-comune-scelto")) st.mappa.setFilter("rete-comune-scelto", ["==", ["get", "istat"], ""]);
    $("scheda-comune").innerHTML = "";
    messaggio("messaggio-comune", "");
    try { const u = new URL(location.href); u.searchParams.delete("comune"); history.replaceState(null, "", u); } catch { /* niente */ }
  }
  function cercaComune() {
    const t = $("cerca-comune-rete").value.trim().toLowerCase().replace(/\s*\([a-z]{2}\)\s*$/i, "");
    if (!t || !st.comuniFc) return;
    const f = st.comuniFc.features.find((x) => x.properties.nome.toLowerCase() === t)
      || st.comuniFc.features.find((x) => x.properties.nome.toLowerCase().startsWith(t));
    if (!f) { messaggio("messaggio-comune", `Nessun comune «${$("cerca-comune-rete").value}» in ${st.nomeRegione}: scegli la regione con la piccola mappa.`, true); return; }
    apriComune(f.properties.istat);
  }
  $("apri-comune").addEventListener("click", cercaComune);
  $("cerca-comune-rete").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); cercaComune(); } });

  async function apriComune(istat) {
    const mio = ++st.giroComune;
    const f = st.comuniFc && st.comuniFc.features.find((x) => x.properties.istat === istat);
    if (!f) return;
    st.scelto = istat;
    st.mappa.setFilter("rete-comune-scelto", ["==", ["get", "istat"], istat]);
    try { const u = new URL(location.href); u.searchParams.set("comune", istat); history.replaceState(null, "", u); } catch { /* niente */ }
    const p = f.properties, r = st.perIstat.get(istat), S = $("scheda-comune");
    S.innerHTML = "";
    messaggio("messaggio-comune", "");
    const t = h("h3", "titolo-comune", `${p.nome} (${p.prov})`); S.appendChild(t);
    st.dettaglio = { istat, nome: p.nome, prov: p.prov, riga: r || null, cabine: [], inter: null };
    const mancante = new Set(provinceMancanti().map((x) => x.cod)).has(istat.slice(0, 3)) || (r && (r.mancante || (r.concessionario !== false && r.dato_disponibile === false)));
    if (mancante) {
      S.appendChild(avviso("attenzione", "Dato non disponibile", "Il servizio di e-distribuzione oggi non restituisce i trasformatori di questa provincia: criticità e cabine mancano. Si riprova a ogni aggiornamento notturno."));
    } else if (r && r.concessionario === false) {
      const d = avviso("", "Il distributore è un altro", "In questo comune la rete elettrica non è di e-distribuzione: EuGEnio non ha i dati di saturazione né le interruzioni. Le cabine primarie e le aree convenzionali di tutti i distributori sono nella ");
      const a = h("a", null, "mappa interattiva delle cabine primarie del GSE"); a.href = R.GSE.SCHEDA; a.rel = "noopener"; a.target = "_blank";
      d.querySelector("div").append(a, ".");
      S.appendChild(d);
      return;
    } else if (!r) {
      S.appendChild(avviso("", "Nessun dato", "Il servizio non ha dati per questo comune."));
    } else {
      S.appendChild(h("h4", null, "Criticità"));
      const c = h("p", "criticita-comune");
      c.append(r.pieno ? R.campione("pieno", r.pieno) : r.strisce ? R.campione("strisce", r.strisce[1]) : R.campione("pieno", "VERDE"), ` ${R.testoClasse(r)}`);
      S.appendChild(c);
      if (inParte(r)) S.appendChild(avviso("", "Servito in parte da un altro distributore",
        `${notaInParte().replace(/^./, (x) => x.toUpperCase())}: e-distribuzione segna il comune come non suo, ma vi ha trasformatori. La criticità vale per la parte servita da e-distribuzione.`));
      S.appendChild(h("p", "aiuto", `Trasformatori delle cabine che servono il comune: ${R.testoTrasf(r.trasf)}. Classificazione di EuGEnio dai dati mensili per trasformatore di e-distribuzione${st.stato ? ` (aggiornati il ${R.dataIt(st.stato.saturazione_aggiornata)})` : ""}.`));
    }
    // cabine e interruzioni in parallelo
    const [cab, inter] = await Promise.allSettled([R.api(`/api/rete/cabine/comune/${istat}`), R.api(`/api/rete/interruzioni/comune/${istat}`)]);
    if (mio !== st.giroComune) return;
    let cabine = [];
    if (cab.status === "fulfilled") {
      const v = cab.value;
      cabine = (Array.isArray(v) ? v : (v && (v.cabine || v.features)) || []).map((x) => x.properties || x);
      cabine.forEach((x) => { if (typeof x.trasf === "string") { try { x.trasf = JSON.parse(x.trasf); } catch { /* resta */ } } });
    }
    if (!cabine.length && st.cabine) {   // ripiego: le cabine della regione che dichiarano il comune tra quelli serviti
      const cod = new Set((r && r.cabine) || []);
      cabine = st.cabine.features.map((x) => x.properties).filter((x) => cod.has(x.cod_cp_ed) || String(x.comuni_serviti || "").split(";").includes(istat));
    }
    st.dettaglio.cabine = cabine;
    if (cab.status === "fulfilled" && cab.value && cab.value.servito_in_parte && !inParte(r) && !S.querySelector(".nota-in-parte"))
      S.insertBefore(Object.assign(h("p", "aiuto nota-in-parte", cab.value.nota || notaInParte())), S.children[1] || null);
    if (!mancante) {
      S.appendChild(h("h4", null, "Cabine primarie che servono il comune"));
      if (!cabine.length) S.appendChild(h("p", "aiuto", "Nessuna cabina primaria abbinata."));
      else S.appendChild(R.tabella(["Cabina", "Codice e-distribuzione", "COD_AC (GSE)", "Livello", "Trasformatori", "Dato del"],
        cabine.map((x) => [R.nomeCabina(x), x.cod_cp_ed || "–", x.cod_ac || "–", x.livello ? R.NOMI[x.livello] || x.livello : "–", R.testoTrasf(x.trasf), R.dataIt(x.data_saturazione)]),
        { titolo: `Cabine primarie – ${p.nome}` }));
    }
    S.appendChild(h("h4", null, "Interruzioni"));
    if (inter.status !== "fulfilled" || !inter.value) {
      S.appendChild(h("p", "aiuto", `Statistiche delle interruzioni non disponibili (${inter.reason ? inter.reason.message : "nessuna risposta"}).`));
      return;
    }
    const d = inter.value; st.dettaglio.inter = d;
    const attive = d.attive || [];
    S.appendChild(h("p", null, attive.length ? `${attive.length} ${attive.length === 1 ? "interruzione in corso" : "interruzioni in corso"}:` : "Nessuna interruzione in corso."));
    if (attive.length) S.appendChild(R.tabella(["Inizio", "Causa", "Clienti", "Ripristino previsto", "Durata finora (stimata)"],
      attive.map((x) => [R.oraIt(I.inizio(x)), I.causa(x) || "–", R.num(I.clientiComune(x)), I.ripristinoTesto(x), durata(I.durata(x))]), { titolo: `Interruzioni in corso – ${p.nome}`, num: [2] }));
    const tot = d.totale || {};
    S.appendChild(h("p", "aiuto", `Statistiche raccolte da EuGEnio dalla mappa pubblica di e-distribuzione dal ${R.dataIt(d.dal)}, ogni 15 minuti: `
      + "prima di quella data non ci sono dati. La durata è stimata: dall'inizio dichiarato all'ultima lettura in cui l'interruzione compare; "
      + "medie e massimi contano solo le interruzioni chiuse. I clienti sono quelli del comune."));
    const dl = h("dl", "scheda-rete");
    const riga = (k, v) => dl.append(h("dt", null, k), h("dd", null, v));
    riga("Interruzioni", R.num(tot.n)); riga("di cui guasti", R.num(tot.guasti)); riga("di cui programmate", R.num(tot.programmati));
    riga("Clienti coinvolti (somma)", R.num(tot.clienti)); riga("Durata media (stimata)", durata(tot.durata_media_min)); riga("Durata massima (stimata)", durata(tot.durata_max_min));
    S.appendChild(dl);
    const mesi = d.per_mese || [];
    if (mesi.length) {
      const g = h("div", "grafico-rete"); g.id = "grafico-interruzioni"; S.appendChild(g);
      disegnaMesi(g, mesi, p.nome);
      S.appendChild(R.tabella(["Mese", "Interruzioni", "Guasti", "Programmate", "Clienti", "Durata media", "Durata massima"],
        mesi.map((x) => [meseIt(x.mese), R.num(x.n), R.num(x.guasti), R.num(x.programmati), R.num(x.clienti), durata(x.durata_media_min), durata(x.durata_max_min)]),
        { titolo: `Interruzioni per mese – ${p.nome}`, num: [1, 2, 3, 4] }));
    }
    const cause = Object.entries(d.per_causa || {});
    if (cause.length) S.appendChild(R.tabella(["Causa", "Interruzioni"], cause.map(([k, v]) => [k, R.num(typeof v === "object" && v ? v.n : v)]), { titolo: `Interruzioni per causa – ${p.nome}`, num: [1] }));
    if ((d.ultime || []).length) {
      const det = h("details", "ultime-interruzioni"); det.appendChild(h("summary", null, `Ultime interruzioni (${d.ultime.length})`));
      det.appendChild(R.tabella(["Inizio", "Fine stimata", "Causa", "Clienti", "Durata (stimata)"],
        d.ultime.map((x) => [R.oraIt(I.inizio(x)), I.fine(x) ? R.oraIt(I.fine(x)) : "in corso", I.causa(x) || "–", R.num(I.clientiComune(x)), durata(I.durata(x))]), { titolo: `Ultime interruzioni – ${p.nome}`, num: [3] }));
      S.appendChild(det);
    }
  }
  function avviso(classe, titolo, testo) {
    const d = h("div", `messaggio ${classe}`.trim()); d.setAttribute("role", "note");
    const x = h("div"); x.append(h("b", null, titolo), testo); d.appendChild(x);
    return d;
  }
  const MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];
  const meseIt = (m) => { const [a, b] = String(m || "").split("-"); return b ? `${MESI[+b - 1]} ${a}` : String(m || "–"); };

  // grafico delle interruzioni per mese (guasti e programmate impilate), regole di README_stile.md § Grafici
  function disegnaMesi(dove, mesi, nome) {
    const G = window.EUGENIO_GRAFICI, NS = "http://www.w3.org/2000/svg";
    const el = (tag, a, padre) => { const e = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(a)) { if ((k === "fill" || k === "stroke") && String(v).startsWith("var(")) e.style.setProperty(k, v); else e.setAttribute(k, v); } if (padre) padre.appendChild(e); return e; };
    function disegna(dest, misure) {
      const W = misure && misure.riquadro ? misure.larghezza : 560, H = misure && misure.riquadro ? misure.altezza : 200;
      const sx = 34, dx = 8, su = 10, gi = 24;
      const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `Interruzioni per mese – ${nome}` }, dest);
      const max = Math.max(1, ...mesi.map((x) => +x.n || 0)), passo = (W - sx - dx) / mesi.length;
      const Y = (v) => su + (H - su - gi) * (1 - v / max);
      for (let k = 0; k <= max; k += Math.max(1, Math.ceil(max / 4))) {
        el("line", { x1: sx, x2: W - dx, y1: Y(k), y2: Y(k), stroke: "var(--linea)", "stroke-width": 1 }, svg);
        const t = el("text", { x: sx - 6, y: Y(k) + 4, "text-anchor": "end", "font-size": 11, fill: "var(--tenue)" }, svg); t.textContent = String(k);
      }
      const punti = mesi.map((x, i) => {
        const cx = sx + passo * (i + 0.5), w = passo * 0.6, g = +x.guasti || 0, pr = +x.programmati || 0;
        const b1 = el("rect", { x: cx - w / 2, y: Y(g), width: w, height: Y(0) - Y(g), fill: "var(--serie-1)" }, svg);
        const b2 = el("rect", { x: cx - w / 2, y: Y(g + pr), width: w, height: Y(g) - Y(g + pr), fill: "var(--serie-2)" }, svg);
        const t = el("text", { x: cx, y: H - 8, "text-anchor": "middle", "font-size": 11, fill: "var(--tenue)" }, svg);
        t.textContent = MESI[+String(x.mese).split("-")[1] - 1] ? MESI[+String(x.mese).split("-")[1] - 1].slice(0, 3) : x.mese;
        return { x: cx, titolo: meseIt(x.mese), elementi: [b1, b2], righe: [["var(--serie-1)", `guasti: ${R.num(g)}`], ["var(--serie-2)", `programmate: ${R.num(pr)}`],
          [null, `clienti: ${R.num(x.clienti)}`], [null, `durata media (stimata): ${durata(x.durata_media_min)}`]] };
      });
      if (G) G.osserva(svg, punti, { area: [sx, su, W - dx, H - gi], guida: false });
      const L = h("div", "legenda"); const s1 = h("span"), i1 = h("i"); i1.style.background = "var(--serie-1)"; s1.append(i1, "guasti");
      const s2 = h("span"), i2 = h("i"); i2.style.background = "var(--serie-2)"; s2.append(i2, "lavori programmati"); L.append(s1, s2); dest.appendChild(L);
    }
    if (G) G.registra(dove, disegna, { titolo: `Interruzioni per mese – ${nome}`, adatta: false });
    else disegna(dove, null);
  }

  // ------------------------------------------------------------------ download
  const righeAttribuzione = () => {
    const r = [R.ATTR.ed, R.ATTR.criticita, R.ATTR.osm, R.ATTR.gse_codici, R.ATTR.confini, "Mappa: MapLibre GL JS (BSD-3)."];
    if (st.stato) r.unshift(`Saturazione aggiornata il ${R.oraIt(st.stato.saturazione_aggiornata)}; interruzioni lette il ${R.oraIt(st.stato.interruzioni_aggiornate)}.`);
    if (R.PROVA) r.unshift("ATTENZIONE: DATI SINTETICI DI PROVA (?prova=1), non reali.");
    return r;
  };
  function opzioniImmagine() {
    if (!st.regione) return "Scegli prima una regione.";
    const righe = [];
    if (acceso("criticita") && st.righe.some(inParte)) righe.push(`Bordo tratteggiato: comune ${notaInParte()}.`);
    if (acceso("criticita")) righe.push("Comuni: pieni = più di metà dei trasformatori al livello più alto presente (giallo, arancione, rosso); a strisce = fino a metà (strisce tra il livello precedente e quello più alto; bianco = verde); grigio a righe = dato non disponibile. " + R.ATTR.criticita + ".");
    if (acceso("nonConc")) righe.push("Retino: comuni serviti da un distributore diverso da e-distribuzione.");
    if (acceso("cabine")) righe.push("Cabine primarie (punti grandi): livello peggiore dei trasformatori (bianco = verde, giallo, arancione, rosso); grigio = altro distributore o senza dato. " + R.ATTR.osm + ".");
    if (acceso("interruzioni")) righe.push("Punti blu: interruzioni in corso (e-distribuzione).");
    righe.push(...righeAttribuzione().filter((x) => x !== R.ATTR.osm || !acceso("cabine")));
    const nome = `rete_elettrica_${st.nomeRegione.toLowerCase().replace(/[^a-z0-9]+/g, "_")}_${new Date().toISOString().slice(0, 10)}`;
    return { titolo: `Stato della rete elettrica – ${st.nomeRegione}${st.dettaglio ? ` – ${st.dettaglio.nome}` : ""}`, righe, nome };
  }
  function datiFile() {
    if (!st.regione || !st.comuniFc) return "Scegli prima una regione e aspetta che i dati siano caricati.";
    const mancanti = new Set(provinceMancanti().map((p) => p.cod));
    const comuni = st.comuniFc.features.map((f) => f.properties).sort((a, b) => a.istat.localeCompare(b.istat)).map((p) => {
      const r = st.perIstat.get(p.istat) || {}, t = r.trasf || {};
      const stato = mancanti.has(p.istat.slice(0, 3)) || r.mancante || (r.concessionario !== false && r.dato_disponibile === false) ? "dato non disponibile" : r.concessionario === false ? "altro distributore" : r.istat ? "e-distribuzione" : "nessun dato";
      const classe = r.pieno ? `pieno ${R.NOMI[r.pieno]}` : Array.isArray(r.strisce) ? `strisce ${R.NOMI[r.strisce[0]]}/${R.NOMI[r.strisce[1]]}` : r.livello ? "nessuna" : "";
      return [p.istat, p.nome, p.prov, stato, r.livello ? R.NOMI[r.livello] : "", Number.isFinite(+r.quota) && r.quota !== null ? Math.round(1000 * r.quota) / 10 : null, classe,
        t.VERDE ?? null, t.GIALLO ?? null, t.ARANCIONE ?? null, t.ROSSO ?? null, inParte(r) ? "sì" : "", (r.cabine || []).join(" ")];
    });
    const intC = ["ISTAT", "Comune", "Prov.", "Distributore", "Livello più alto", "Quota al livello (%)", "Colore sulla mappa", "Trasf. verdi", "Trasf. gialli", "Trasf. arancioni", "Trasf. rossi", "Servito in parte da un altro distributore", "Cabine (codici e-distribuzione)"];
    const cab = (st.cabine ? st.cabine.features : []).map((f) => { const p = f.properties, t = p.trasf || {}, [lon, lat] = f.geometry.coordinates;
      return [p.cod_cp_ed || "", R.nomeCabina(p), p.cod_ac || "", p.gestore || "", p.livello ? R.NOMI[p.livello] : "", t.VERDE ?? null, t.GIALLO ?? null, t.ARANCIONE ?? null, t.ROSSO ?? null,
        p.data_saturazione || "", Math.round(lat * 1e5) / 1e5, Math.round(lon * 1e5) / 1e5, p.esito || ""]; });
    const intK = ["Codice e-distribuzione", "Nome", "COD_AC (GSE)", "Gestore", "Livello peggiore", "Trasf. verdi", "Trasf. gialli", "Trasf. arancioni", "Trasf. rossi", "Dato del", "Latitudine", "Longitudine", "Raccordo"];
    const sezioni = [{ titolo: `Comuni – ${st.nomeRegione}`, intestazioni: intC, righe: comuni }, { titolo: `Cabine primarie – ${st.nomeRegione}`, intestazioni: intK, righe: cab }];
    const d = st.dettaglio;
    if (d && d.inter) {
      sezioni.push({ titolo: `Interruzioni per mese – ${d.nome} (dal ${R.dataIt(d.inter.dal)}, durata stimata)`, intestazioni: ["Mese", "Interruzioni", "Guasti", "Programmate", "Clienti", "Durata media (min)", "Durata massima (min)"],
        righe: (d.inter.per_mese || []).map((x) => [x.mese, x.n ?? null, x.guasti ?? null, x.programmati ?? null, x.clienti ?? null, x.durata_media_min ?? null, x.durata_max_min ?? null]) });
      sezioni.push({ titolo: `Interruzioni per causa – ${d.nome}`, intestazioni: ["Causa", "Interruzioni"], righe: Object.entries(d.inter.per_causa || {}).map(([k, v]) => [k, typeof v === "object" && v ? v.n : v]) });
      sezioni.push({ titolo: `Interruzioni in corso – ${d.nome}`, intestazioni: ["Inizio", "Causa", "Clienti", "Ripristino previsto", "Durata finora (min, stimata)"],
        righe: (d.inter.attive || []).map((x) => [I.inizio(x) || "", I.causa(x), I.clientiComune(x) ?? null, I.ripristino(x) || x.ripristino_testo || "", I.durata(x) ?? null]) });
    }
    const piede = righeAttribuzione().concat(["Licenza: dati elaborati da EuGEnio CC BY 4.0; posizioni delle cabine ODbL 1.0 (© contributori OpenStreetMap); codici e-distribuzione e GSE con citazione della fonte."]);
    const nome = `rete_elettrica_${st.regione}${d ? `_${d.istat}` : ""}_${new Date().toISOString().slice(0, 10)}`;
    const doc = {
      titolo: `Stato della rete elettrica – ${st.nomeRegione}`,
      sottotitolo: d ? `con il comune di ${d.nome}` : "comuni e cabine primarie",
      nome_file: nome,
      sezioni: [
        { titolo: "Dati e regole", blocchi: [
          ...(R.PROVA ? [{ tipo: "avvertenza", testo: "DATI SINTETICI DI PROVA (?prova=1): non reali." }] : []),
          { tipo: "paragrafo", testo: st.stato ? `Saturazione aggiornata il ${R.oraIt(st.stato.saturazione_aggiornata)}; interruzioni lette il ${R.oraIt(st.stato.interruzioni_aggiornate)} (ogni 15 minuti).` : "Date di aggiornamento non disponibili." },
          { tipo: "paragrafo", testo: "Criticità del comune (classificazione di EuGEnio): L = livello più alto tra i trasformatori delle cabine che servono il comune, q = quota dei trasformatori a quel livello. L verde: nessuna criticità; q > 0,5: pieno di L; altrimenti strisce tra il livello precedente e L. Comuni segnati da e-distribuzione come serviti da altri ma con suoi trasformatori: colore della criticità e nota «servito in parte da un altro distributore». Durata delle interruzioni stimata: dall'inizio dichiarato all'ultima lettura in cui compare." },
          ...(provinceMancanti().length ? [{ tipo: "avvertenza", testo: `Dato non disponibile per la provincia ${provinceMancanti().map(nomeProvincia).join(", ")}.` }] : []),
        ] },
        ...sezioni.map((s) => ({ titolo: s.titolo, blocchi: [{ tipo: "tabella", intestazioni: s.intestazioni, righe: s.righe.length ? s.righe : [s.intestazioni.map(() => null)] }] })),
      ],
      fonti: [
        { testo: "e-distribuzione S.p.A. – Aree critiche (dato mensile per trasformatore) e mappa delle interruzioni", url: R.URL_ED },
        { testo: "© contributori OpenStreetMap – posizioni delle cabine primarie, ODbL 1.0", url: R.URL_OSM },
        { testo: "GSE S.p.A. – codici delle aree convenzionali (COD_AC)", url: R.GSE.SCHEDA },
        { testo: "ISTAT – confini delle unità amministrative (CC BY 4.0)", url: "https://www.istat.it/" },
      ],
    };
    return { csv: [`${nome}.csv`, sezioni, piede], doc };
  }

  avvio().catch((e) => messaggio("messaggio-mappa", `Mappa non disponibile: ${e.message}`, true));
  window.EUGENIO_RETE_PAGINA = { st, apriComune, vaiRegione, datiFile, opzioniImmagine };
})();
