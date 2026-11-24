"use strict";
// Fotovoltaico › «CER – Sviluppo impianti FV» (fv-cer.html, 24/11/2026, richiesta di Paolo; proposta in
// documenti/PROPOSTA_TERRENI_CER_2026-11-24.md del Project). Struttura e mappa come «Cabine primarie» (fv_cabine.js).
//
//  1. edifici (file di Patrimonio: coordinate dal file, le altre righe a POST /api/patrimonio) e curve di carico
//     (cer_fv_calcolo.js, lette nel browser e mai inviate al server);
//  2. area convenzionale del GSE di ogni edificio letta dal browser (R.gse.areaNelPunto, al massimo 4 domande alla volta);
//  3. per area: curve sommate, clima orario del comune della cabina (/api/edifici/clima-orario), potenza FV + accumulo
//     più alta con la quota condivisa minima (bisezione), impianti e superfici;
//  4. A – terreni pubblici vicino alla cabina (/api/cer-fv/terreni: MEF + AdE, probabilità di coltura DOP o certificata
//     da AGREA), graduatoria e verifica dell'area del GSE per i primi;
//  5. B – cabine per la manifestazione di interesse, avviso tipo (PDF da /api/report) e modulo CSV;
//  6. file con i soli codici delle aree del GSE e il solo indicatore delle colture.
// Con ?prova=1 niente server (rete.js): clima, cabine e terreni SINTETICI, dichiarati in pagina e nei file.
(function () {
  const $ = (id) => document.getElementById(id);
  const R = window.EUGENIO_RETE, C = window.EUGENIO_CONFINI, T = window.EUGENIO_TABELLE, F = window.EUGENIO_CER_FV, ED = window.EUGENIO_EDIFICI;
  if (!$("mappa-dettaglio") || !window.maplibregl || !R || !C || !F || !ED) return;
  const ml = window.maplibregl;
  const MASSIMO = 200, BLOCCO = 40, VERIFICA_GSE = 2;     // terreni verificati col GSE: n × VERIFICA_GSE per cabina
  const RAGGIO_CABINE = ["interpolate", ["linear"], ["zoom"], 5, 4, 10, 6, 14, 8];
  const BORDO_CABINE = ["interpolate", ["linear"], ["zoom"], 5, 1.2, 12, 1.6];
  const CONTESTO = "s2cloudless2016";
  const COLORE_EDIFICI = "#1e88e5";
  const COLORI_TERRENI = { C: "#2e9d4f", A: "#f08a00", X: "#9a9a9a" };
  const vuota = () => ({ type: "FeatureCollection", features: [] });
  const colore = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || "#888";
  const num = (x, d = 0) => (x === null || x === undefined || !Number.isFinite(+x) ? "–" : R.num(+x, d));
  const pct = (x, d = 0) => (x === null || x === undefined ? "–" : `${R.num(100 * x, d)} %`);
  function h(tag, cls, t) { const e = document.createElement(tag); if (cls) e.className = cls; if (t !== undefined && t !== null) e.textContent = t; return e; }
  function messaggio(id, t, errore = false) { const m = $(id); if (!m) return; m.textContent = t; m.classList.toggle("errore", errore); }
  const st = {
    det: null, fonti: [], fonte: null, contesto: null, manuale: false, sposta: null, strati: null, pronto: false,
    fileEdifici: null, fileCurve: null, edifici: [], curve: null, cabine: [], tutte: null, aree: null,
    parametri: null, calcolato: false, terreniCercati: false, infoTerreni: null,
  };
  R.avvisoProva(document.querySelector(".pannello"));

  // ================================================================== parametri
  function parametri() {
    const v = (id) => $(id).value, n = (id) => { const x = Number(v(id)); return Number.isFinite(x) ? x : null; };
    const tipo = v("p-tipo") === "agrivoltaico" ? "agrivoltaico" : "fisso";
    const o = { ...F.PREDEFINITI, h: Math.max(0, n("p-h") || 0), qMin: Math.min(1, Math.max(0.05, (n("p-q") || 60) / 100)),
      denominatore: v("p-den") === "immessa" ? "immessa" : "produzione", tipo, inclinazione: n("p-incl") ?? 25,
      orientamento: n("p-orient") ?? 180, perdite: Math.min(0.4, Math.max(0, (n("p-perdite") ?? 14) / 100)),
      potenzaMassimaImpianto: Math.min(1000, Math.max(20, n("p-pmax") || 1000)), potenzaMassima: v("p-ptot") === "" ? null : n("p-ptot"),
      distanzaKm: Math.min(15, Math.max(0.5, n("p-dist") || 5)), nTerreni: Math.min(30, Math.max(1, Math.round(n("p-n") || 5))),
      tolleranza: Math.min(5, Math.max(1, n("p-toll") || 1.3)) };
    // superficie specifica scelta dall'utente al posto di quella del tipo (valori indicativi)
    F.TIPI[tipo] = { ...F.TIPI[tipo], haMw: Math.min(6, Math.max(0.5, n("p-ha") || F.TIPI[tipo].haMw)) };
    return o;
  }
  $("p-tipo").addEventListener("change", () => { $("p-ha").value = $("p-tipo").value === "agrivoltaico" ? "2.5" : "1.4"; });

  // ================================================================== 1. file
  for (const [id, chiave, nome] of [["file-edifici", "fileEdifici", "nome-file-edifici"], ["file-curve", "fileCurve", "nome-file-curve"]]) {
    $(id).addEventListener("change", (e) => {
      st[chiave] = e.target.files[0] || null;
      $(nome).textContent = st[chiave] ? st[chiave].name : "";
      $("carica").disabled = !(st.fileEdifici && st.fileCurve);
    });
  }
  $("carica").addEventListener("click", () => leggiTutto(st.fileEdifici, st.fileCurve));
  $("esempio").addEventListener("click", async () => {
    try {
      const [a, b] = await Promise.all(["esempi/cer_fv_sedi_esempio.csv", "esempi/cer_fv_curve_esempio.csv"].map(async (u) => {
        const r = await fetch(u); if (!r.ok) throw new Error(`${u}: errore ${r.status}`);
        return new File([await r.blob()], u.split("/").pop(), { type: "text/csv" });
      }));
      $("nome-file-edifici").textContent = a.name; $("nome-file-curve").textContent = b.name;
      await leggiTutto(a, b);
    } catch (e) { messaggio("messaggio-edifici", `Esempio non disponibile: ${e.message}`, true); }
  });

  const norm = (c) => String(c || "").trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  const cella = (v) => (/[;"\n\r]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));
  async function leggiTutto(fe, fc) {
    $("carica").disabled = true; $("esempio").disabled = true;
    st.calcolato = false; st.terreniCercati = false; st.cabine = []; st.edifici = []; st.curve = null; st.aree = null;
    disegna(); elencoCabine(); elencoTerreni(); elencoBando();
    try {
      messaggio("messaggio-edifici", "Lettura delle curve di carico…");
      const lc = await T.leggi(fc);
      st.curve = F.leggiCurve(lc.testo, { decimalePunto: lc.decimalePunto });
      messaggio("messaggio-edifici", "Lettura degli edifici…");
      await leggiEdifici(fe);
      const conCurva = st.edifici.filter((e) => st.curve.serie.has(e.id));
      const senzaEdificio = [...st.curve.serie.keys()].filter((id) => !st.edifici.some((e) => e.id === id));
      const note = [`${st.edifici.length} edifici, ${conCurva.length} con la curva di carico (${st.curve.formato === "largo" ? "una colonna per edificio" : st.curve.formato === "giorno" ? "una riga per giorno" : "una riga per valore"}, passo ${st.curve.passoMinuti} minuti, anni ${st.curve.anni.join(", ")}).`];
      const senza = st.edifici.filter((e) => !st.curve.serie.has(e.id));
      if (senza.length) note.push(`Senza curva (esclusi dal calcolo): ${senza.map((e) => e.id).join(", ")}.`);
      if (senzaEdificio.length) note.push(`Curve senza edificio (ignorate): ${senzaEdificio.slice(0, 10).join(", ")}${senzaEdificio.length > 10 ? "…" : ""}.`);
      const scarse = conCurva.filter((e) => st.curve.copertura.get(e.id) < 0.9);
      if (scarse.length) note.push(`Curve con meno del 90 % delle ore (le mancanti sono la media della stessa ora nello stesso mese): ${scarse.map((e) => `${e.id} ${pct(st.curve.copertura.get(e.id))}`).join(", ")}.`);
      note.push(...st.curve.avvisi);
      if (lc.nota) note.push(lc.nota);
      messaggio("messaggio-edifici", note.join(" "));
      await aree();
      $("calcola").disabled = !conCurva.some((e) => e.area);
    } catch (e) {
      messaggio("messaggio-edifici", `File non letti: ${e.message}`, true);
    } finally { $("carica").disabled = !(st.fileEdifici && st.fileCurve); $("esempio").disabled = false; elencoEdifici(); disegna(); }
  }
  async function leggiEdifici(file) {
    const letto = await T.leggi(file);
    const linee = letto.testo.split(/\r?\n/).filter((r) => r.trim() && !r.trim().startsWith("#") && !/^"?Fonte: EuGEnio/i.test(r.trim()));
    if (linee.length < 2) throw new Error("il file degli edifici non contiene righe di dati");
    const tab = T.righe(linee.join("\n"), T.separatore(linee[0]));
    const testa = tab[0].map(norm), corpo = tab.slice(1).filter((r) => r.some((x) => String(x).trim()));
    if (corpo.length > MASSIMO) throw new Error(`il file degli edifici ha ${corpo.length} righe: al massimo ${MASSIMO}`);
    const col = (...n) => testa.findIndex((x) => n.includes(x));
    const iId = col("id", "codice", "cod", "codice_edificio", "pod"), iNome = col("denominazione", "nome"), iInd = col("indirizzo", "via"),
      iCiv = col("civico"), iCom = col("comune"), iLat = col("lat", "latitudine"), iLon = col("lon", "lng", "longitudine");
    if (iId < 0) throw new Error("manca la colonna id degli edifici (serve per collegarli alle curve)");
    const val = (r, i) => (i >= 0 ? String(r[i] ?? "").trim() : "");
    const numero = (s) => T.numero(s, { decimalePunto: letto.decimalePunto });
    const altre = [];
    for (const r of corpo) {
      const lat = numero(val(r, iLat)), lon = numero(val(r, iLon));
      if (lat !== null && lon !== null && lat > 35 && lat < 48 && lon > 6 && lon < 19.5) {
        st.edifici.push({ id: val(r, iId), nome: val(r, iNome), lat, lon, indirizzo: [val(r, iInd), val(r, iCiv), val(r, iCom)].filter(Boolean).join(" "), origine: "coordinate del file" });
      } else altre.push(r);
    }
    if (!altre.length) return;
    if (R.PROVA) { messaggio("messaggio-edifici", `${altre.length} edifici senza coordinate non cercati: nel modo di prova la pagina non usa il server.`); return; }
    $("avanzamento-edifici").hidden = false;
    try {
      for (let i = 0; i < altre.length; i += BLOCCO) {
        $("barra-edifici").style.width = `${(100 * i / altre.length).toFixed(1)}%`;
        const testo = [tab[0], ...altre.slice(i, i + BLOCCO)].map((x) => x.map(cella).join(";")).join("\n");
        const fd = new FormData(); fd.append("file", new Blob([testo], { type: "text/csv;charset=utf-8" }), "edifici.csv");
        const rr = await fetch("/api/patrimonio", { method: "POST", body: fd });
        const d = await rr.json().catch(() => null);
        if (!rr.ok) throw new Error((d && d.detail) || `errore ${rr.status}`);
        for (const x of d.righe || []) {
          const lat = +x.lat, lon = +x.lon;
          if (!Number.isFinite(lat) || !Number.isFinite(lon) || x.lat === null || x.esito === "non_trovato" || x.esito === "errore") continue;
          st.edifici.push({ id: String(x.id || ""), nome: x.denominazione || "", lat, lon, indirizzo: x.indirizzo_trovato || "", origine: x.esito === "verificare" ? "ricerca (da verificare)" : "ricerca" });
        }
      }
    } finally { $("avanzamento-edifici").hidden = true; }
  }

  // ================================================================== 2. aree convenzionali del GSE (dal browser)
  const coda = []; let inCorso = 0;
  function inCoda(fn) { return new Promise((ok, ko) => { coda.push({ fn, ok, ko }); avanti(); }); }
  function avanti() { while (inCorso < R.GSE.INSIEME && coda.length) { const { fn, ok, ko } = coda.shift(); inCorso++; fn().then(ok, ko).finally(() => { inCorso--; avanti(); }); } }
  async function aree() {
    messaggio("messaggio-calcolo", "Cerco l'area convenzionale del GSE di ogni edificio…");
    await Promise.all(st.edifici.map(async (e) => {
      try { e.area = await inCoda(() => R.gse.areaNelPunto(e.lon, e.lat)); e.errArea = ""; }
      catch (x) { e.area = null; e.errArea = x.message || "servizio del GSE non raggiungibile"; }
    }));
    const senza = st.edifici.filter((e) => !e.area);
    messaggio("messaggio-calcolo", senza.length ? `${senza.length} edifici senza area del GSE (esclusi): ${senza.map((e) => e.id).join(", ")}.` : "Aree del GSE trovate: imposta i parametri e premi «Calcola».", !!senza.length);
    const pts = st.edifici;
    if (pts.length && st.det) {
      const xs = pts.map((p) => p.lon), ys = pts.map((p) => p.lat);
      st.det.fitBounds([[Math.min(...xs), Math.min(...ys)], [Math.max(...xs), Math.max(...ys)]], { padding: 60, maxZoom: 14, duration: 700 });
    }
  }
  function elencoEdifici() {
    const d = $("elenco-edifici"); d.innerHTML = "";
    if (!st.edifici.length) return;
    d.appendChild(R.tabella(["Id", "Nome", "Area GSE", "Consumo annuo (MWh)", "Ore presenti"], st.edifici.map((e) => {
      const v = st.curve && st.curve.serie.get(e.id);
      return [e.id, e.nome || e.indirizzo, e.area ? e.area.COD_AC : e.area === null ? (e.errArea ? "non letta" : "nessuna") : "…",
        v ? num(F.totale(v) / 1000, 1) : "senza curva", v ? pct(st.curve.copertura.get(e.id)) : "–"];
    }), { titolo: "Edifici", num: [3, 4] }));
  }

  // ================================================================== 3. calcolo per cabina
  function tutteLeCabine() {
    if (!st.tutte) { st.tutte = R.api("/api/rete/cabine").then(R.preparaCabine); st.tutte.catch(() => { st.tutte = null; }); }
    return st.tutte;
  }
  const climi = new Map();
  async function clima(istat, lat, lon) {
    if (R.PROVA || !istat) return ED.climaSintetico(new Date().getFullYear() - 1, lat, lon);
    if (!climi.has(istat)) {
      const p = fetch(`/api/edifici/clima-orario/${istat}`).then(async (r) => {
        const d = await r.json().catch(() => null);
        if (!r.ok) throw new Error((d && d.detail) || `errore ${r.status}`);
        return d;
      });
      p.catch(() => climi.delete(istat));
      climi.set(istat, p);
    }
    return climi.get(istat);
  }
  $("calcola").addEventListener("click", () => calcola().catch((e) => messaggio("messaggio-calcolo", `Calcolo non riuscito: ${e.message}`, true)));
  async function calcola() {
    $("calcola").disabled = true;
    const o = parametri(); st.parametri = o;
    st.terreniCercati = false;
    try {
      let feats = [];
      try { feats = (await tutteLeCabine()).features; } catch (e) { messaggio("messaggio-calcolo", `Cabine di e-distribuzione non disponibili (${e.message}): restano i codici del GSE.`, true); }
      const byAc = new Map(feats.filter((f) => f.properties.cod_ac).map((f) => [f.properties.cod_ac, f]));
      const gruppi = new Map();
      for (const e of st.edifici) {
        if (!e.area || !st.curve.serie.has(e.id)) continue;
        const k = e.area.COD_AC;
        if (!gruppi.has(k)) gruppi.set(k, { cod_ac: k, gestoreGse: e.area.RAG_SOC || "", edifici: [] });
        gruppi.get(k).edifici.push(e);
      }
      st.cabine = [];
      $("avanzamento-calcolo").hidden = false;
      let i = 0;
      for (const g of gruppi.values()) {
        $("barra-calcolo").style.width = `${(100 * i++ / gruppi.size).toFixed(1)}%`;
        messaggio("messaggio-calcolo", `Calcolo dell'area ${g.cod_ac} (${i} di ${gruppi.size})…`);
        const f = byAc.get(g.cod_ac);
        const xs = g.edifici.map((e) => e.lon), ys = g.edifici.map((e) => e.lat);
        const bari = [xs.reduce((a, b) => a + b, 0) / xs.length, ys.reduce((a, b) => a + b, 0) / ys.length];
        const coord = f ? f.geometry.coordinates : null, centro = coord || bari;
        let com = null; try { com = await C.comuneNelPunto(centro[0], centro[1]); } catch { /* fuori dai confini */ }
        const c = { ...g, props: f ? f.properties : null, coord, centro, posizione: coord ? "cabina (OpenStreetMap)" : "baricentro degli edifici",
          istat: com ? com.istat : null, comune: com ? com.nome : "", prov: com ? com.prov : "", errore: "" };
        try {
          const cl = await clima(c.istat, centro[1], centro[0]);
          c.clima = { anno: cl.anno, comune: cl.comune || c.comune, sintetico: !!cl.sintetico };
          c.consumi = F.somma(g.edifici.map((e) => st.curve.serie.get(e.id)));
          c.pKwp = F.produzionePerKwp(cl, centro[1], centro[0], { inclinazione: o.inclinazione, orientamento: o.orientamento, perdite: o.perdite });
          c.curva = F.riepilogoCurva(c.consumi, c.pKwp);
          c.ris = F.dimensiona(c.consumi, c.pKwp, o);
          c.fabbisogno = F.fabbisognoTerreni(c.ris, o);
        } catch (e) { c.errore = e.message; }
        st.cabine.push(c);
        await new Promise((ok) => setTimeout(ok, 0));
      }
      st.cabine.sort((a, b) => ((b.ris && b.ris.P) || 0) - ((a.ris && a.ris.P) || 0));
      st.calcolato = true;
      const tot = st.cabine.reduce((s, c) => s + ((c.ris && c.ris.P) || 0), 0), imp = st.cabine.reduce((s, c) => s + ((c.ris && c.ris.nImpianti) || 0), 0);
      const sint = st.cabine.some((c) => c.clima && c.clima.sintetico);
      messaggio("messaggio-calcolo", `${st.cabine.length} cabine: ${num(tot / 1000, 2)} MW in tutto, ${imp} impianti.${sint ? " Clima SINTETICO (cielo sereno ridotto): solo per prova." : ""}`);
      await areeCabine();
    } finally {
      $("avanzamento-calcolo").hidden = true;
      $("calcola").disabled = false;
      $("cerca-terreni").disabled = !st.cabine.some((c) => c.ris && c.ris.nImpianti);
      elencoCabine(); elencoTerreni(); elencoBando(); disegna(); inquadra();
      if (window.EUGENIO_COLLEGAMENTO) window.EUGENIO_COLLEGAMENTO.aggiorna();
    }
  }
  async function areeCabine() {
    const codici = st.cabine.map((c) => c.cod_ac).slice(0, R.GSE.MASSIMO);
    try {
      const fc = await R.gse.aree(codici);
      st.aree = { ...fc, letto: new Date().toISOString() };
    } catch (e) { st.aree = null; messaggio("messaggio-dettaglio", `Confini delle aree del GSE non letti: ${e.message}.`, true); }
    disegna();
  }
  const nomeCabina = (c) => (c.props ? R.nomeCabina(c.props) : `area ${c.cod_ac}`);
  const livello = (c) => (c.props && c.props.livello ? R.NOMI[c.props.livello] || c.props.livello : "–");
  function elencoCabine() {
    const d = $("elenco-cabine"); d.innerHTML = "";
    if (!st.calcolato) { d.appendChild(h("p", "aiuto", "Carica edifici e curve, poi premi «Calcola».")); return; }
    d.appendChild(R.tabella(["COD_AC (GSE)", "Cabina", "Saturazione", "Edifici", "Consumi (MWh)", "Consumi nelle ore di sole", "FV (kW)", "Accumulo (kWh)",
      "Produzione (MWh)", "Condivisa (MWh)", "Quota condivisa", "Autosufficienza", "Impianti", "Superficie per impianto (ha)"], st.cabine.map((c) => {
      const r = c.ris;
      if (!r) return [c.cod_ac, nomeCabina(c), livello(c), c.edifici.length, "–", "–", "–", "–", "–", "–", "–", "–", "–", c.errore || "–"];
      const x = r.impianti && r.impianti[0];
      return [c.cod_ac, nomeCabina(c), livello(c), c.edifici.length, num(c.curva.kwh / 1000, 1), pct(c.curva.quotaOreSole), num(r.P), num(r.E),
        num(r.produzione / 1000, 1), num(r.condivisa / 1000, 1), pct(r.quota), pct(r.autosufficienza), r.nImpianti ? `${r.nImpianti} × ${num(x.kw)} kW` : r.motivo,
        x ? `${num(x.haMin, 2)}–${num(x.haMax, 2)}` : "–"];
    }), { titolo: "Potenza per cabina primaria", num: [3, 4, 5, 6, 7, 8, 9, 10, 11] }));
    const o = st.parametri;
    d.appendChild(h("p", "aiuto", `Impianti ${F.TIPI[o.tipo].nome}, ${num(F.TIPI[o.tipo].haMw, 1)} ha per MWp più ${num(F.ACCESSORI_HA, 2)} ha per impianto e ${num(F.ACCUMULO_HA_MWH, 2)} ha per MWh di accumulo (valori indicativi). Clima: ${[...new Set(st.cabine.filter((c) => c.clima).map((c) => `${c.clima.comune} ${c.clima.anno}${c.clima.sintetico ? " (sintetico)" : ""}`))].join(", ")}.`));
  }

  // ================================================================== 4. A – terreni pubblici
  $("cerca-terreni").addEventListener("click", () => cercaTerreni().catch((e) => messaggio("messaggio-terreni", `Ricerca non riuscita: ${e.message}`, true)));
  // terreni sintetici per ?prova=1: deterministici per cabina, dichiarati come tali
  function terreniProva(c, o) {
    let s = [...c.cod_ac].reduce((a, ch) => (a * 31 + ch.charCodeAt(0)) >>> 0, 7);
    const rnd = () => ((s = (s * 1103515245 + 12345) >>> 0) / 4294967296);
    const f = c.fabbisogno, out = [];
    for (let i = 0; i < 14; i++) {
      const a = rnd() * 2 * Math.PI, dm = 300 + rnd() * o.distanzaKm * 900;
      const lon = c.centro[0] + dm * Math.sin(a) / (111320 * Math.cos(c.centro[1] * Math.PI / 180)), lat = c.centro[1] + dm * Math.cos(a) / 111320;
      const p = rnd() < 0.3 ? Math.round(55 + rnd() * 45) : rnd() < 0.2 ? null : Math.round(rnd() * 45);
      out.push({ ref: `PROVA_${c.cod_ac}_${i + 1}`, lon, lat, area_m2: Math.round(10000 * f.haMin * (0.6 + rnd() * 1.6)), comune: c.comune || "–", foglio: String(1 + Math.floor(rnd() * 60)),
        particella: String(1 + Math.floor(rnd() * 400)), ente: ["COMUNE DI PROVA", "PROVINCIA DI PROVA", "AZIENDA SANITARIA DI PROVA"][i % 3], settore: "dati sintetici",
        ente_sede: "", n_enti: 1, tipologie: "Terreno (sintetico)", prob_coltura: p, classe_coltura: p === null ? "non dichiarata" : p >= 60 ? "alta" : p >= 30 ? "media" : "bassa",
        distanza_m: Math.round(F.distanzaM(c.centro[0], c.centro[1], lon, lat)) });
    }
    return out;
  }
  async function cercaTerreni() {
    $("cerca-terreni").disabled = true;
    const o = st.parametri;
    try {
      if (!R.PROVA && !st.infoTerreni) {
        try { st.infoTerreni = await R.api("/api/cer-fv/info"); } catch { st.infoTerreni = { disponibile: false }; }
      }
      if (!R.PROVA && st.infoTerreni && st.infoTerreni.disponibile === false) throw new Error("i terreni pubblici non sono ancora sul server");
      const conImpianti = st.cabine.filter((c) => c.ris && c.ris.nImpianti);
      $("avanzamento-terreni").hidden = false;
      let i = 0;
      for (const c of conImpianti) {
        $("barra-terreni").style.width = `${(100 * i++ / conImpianti.length).toFixed(1)}%`;
        messaggio("messaggio-terreni", `Terreni pubblici vicino a ${nomeCabina(c)} (${i} di ${conImpianti.length})…`);
        const f = { ...c.fabbisogno, distanzaMaxM: o.distanzaKm * 1000, tipo: o.tipo };
        let lista;
        if (R.PROVA) lista = terreniProva(c, o);
        else {
          const r = await fetch(`/api/cer-fv/terreni?lon=${c.centro[0].toFixed(6)}&lat=${c.centro[1].toFixed(6)}&raggio_km=${o.distanzaKm}&min_m2=${Math.floor(f.haMin * 10000)}&limite=300`);
          const d = await r.json().catch(() => null);
          if (!r.ok) throw new Error((d && d.detail) || `errore ${r.status}`);
          lista = d.terreni || [];
          c.attribuzioneTerreni = d.attribuzione;
        }
        c.terreni = lista.map((t) => ({ ...t, ...F.punteggioTerreno(t, f) })).sort((a, b) => (b.ammesso - a.ammesso) || (b.punti - a.punti) || (a.distanza_m - b.distanza_m));
        // verifica dell'area del GSE per i primi ammessi: fuori area → esclusi
        const daVerificare = c.terreni.filter((t) => t.ammesso).slice(0, o.nTerreni * VERIFICA_GSE);
        await Promise.all(daVerificare.map(async (t) => {
          try { const a = await inCoda(() => R.gse.areaNelPunto(t.lon, t.lat)); t.areaGse = a ? a.COD_AC : null; }
          catch { t.areaGse = undefined; }
          if (t.areaGse !== undefined && t.areaGse !== c.cod_ac) { t.ammesso = false; t.punti = 0; t.motivi.push(t.areaGse ? `in un'altra area del GSE (${t.areaGse})` : "fuori dalle aree del GSE"); }
        }));
        c.terreni.sort((a, b) => (b.ammesso - a.ammesso) || (b.punti - a.punti) || (a.distanza_m - b.distanza_m));
        c.pubbliciAdatti = c.terreni.filter((t) => t.ammesso && t.areaGse === c.cod_ac).slice(0, o.nTerreni);
      }
      st.terreniCercati = true;
      const tot = st.cabine.reduce((s, c) => s + ((c.pubbliciAdatti && c.pubbliciAdatti.length) || 0), 0);
      messaggio("messaggio-terreni", `${tot} terreni pubblici adatti nelle stesse aree delle cabine.${R.PROVA ? " TERRENI SINTETICI DI PROVA." : ""}`);
    } finally {
      $("avanzamento-terreni").hidden = true;
      $("cerca-terreni").disabled = false;
      elencoTerreni(); elencoBando(); disegna(); inquadra();
    }
  }
  const testoColtura = (t) => (t.prob_coltura === null || t.prob_coltura === undefined ? (t.classe_coltura === "non dichiarata" ? "non dichiarata" : "nessun dato") : `${t.prob_coltura} % (${t.classe_coltura})`);
  const testoGse = (t, c) => (t.areaGse === undefined ? (t.ammesso ? "non verificata" : "–") : t.areaGse === c.cod_ac ? "stessa area" : t.areaGse || "fuori area");
  function elencoTerreni() {
    const d = $("elenco-terreni"); d.innerHTML = "";
    if (!st.terreniCercati) return;
    for (const c of st.cabine.filter((x) => x.terreni)) {
      const lista = c.terreni.slice(0, Math.max(st.parametri.nTerreni * 2, 10));
      d.appendChild(R.tabella(["#", "Comune", "Foglio", "Particella", "Superficie (ha)", "Distanza (km)", "Ente proprietario", "Settore", "Coltura DOP o certificata", "Classe", "Area GSE", "Punti", "Note"],
        lista.map((t, i) => [i + 1, t.comune || "–", t.foglio || "–", t.particella || "–", num(t.ha, 2), num(t.distanza_m / 1000, 2), t.n_enti > 1 ? `${t.ente} (+${t.n_enti - 1})` : t.ente,
          t.settore || "–", testoColtura(t), t.classe, testoGse(t, c), t.ammesso ? t.punti : "escluso", t.motivi.join("; ") || "–"]),
        { titolo: `${c.cod_ac} – ${nomeCabina(c)}: ${c.fabbisogno.n} terreni da ${num(c.fabbisogno.haMin, 2)}–${num(c.fabbisogno.haMax, 2)} ha`, num: [0, 4, 5, 11] }));
      if (!c.terreni.length) d.appendChild(h("p", "aiuto", `${c.cod_ac}: nessun terreno pubblico di almeno ${num(c.fabbisogno.haMin, 2)} ha entro ${num(st.parametri.distanzaKm, 1)} km.`));
    }
    d.appendChild(h("p", "aiuto", `Classe C: agricola non idonea, ammessi impianti fino a 1 MW intestati a una CER o l'agrivoltaico. Classe A: ${F.NOMI_CLASSI.A}. Le aree idonee (classe I) e i vincoli si aggiungeranno con gli strati regionali.`));
  }

  // ================================================================== 5. B – cabine per la manifestazione di interesse
  function righeBando() {
    const o = st.parametri;
    return st.cabine.filter((c) => c.ris && c.ris.nImpianti).map((c) => {
      const f = c.fabbisogno, pub = st.terreniCercati ? (c.pubbliciAdatti || []).length : null;
      const cercare = Math.max(0, f.n - (pub || 0));
      const comuni = c.props && c.props.comuni_serviti ? String(c.props.comuni_serviti).split(";").filter(Boolean).length : null;
      return { c, cercare, pub, riga: [c.cod_ac, nomeCabina(c), c.props ? c.props.cod_cp_ed || "" : "", livello(c), comuni ?? "–", c.comune || "–",
        num(c.ris.P), num(c.ris.E), f.n, pub ?? "non cercati", cercare, num(f.kwImpianto), `${num(f.haMin, 2)}–${num(f.haMax, 2)}`, num(o.distanzaKm, 1),
        o.tipo === "agrivoltaico" ? "C, A (agrivoltaico)" : "C (fino a 1 MW per CER); A solo agrivoltaico"] };
    });
  }
  const INT_BANDO = ["COD_AC (GSE)", "Cabina", "Codice e-distribuzione", "Saturazione", "Comuni serviti", "Comune della cabina", "FV (kW)", "Accumulo (kWh)",
    "Impianti", "Terreni pubblici adatti", "Terreni da cercare", "kW per impianto", "Superficie (ha)", "Distanza massima (km)", "Classi ammesse"];
  function elencoBando() {
    const d = $("elenco-bando"); d.innerHTML = "";
    const rr = st.calcolato ? righeBando() : [];
    $("avviso-pdf").disabled = $("modulo-csv").disabled = !rr.length;
    if (!rr.length) return;
    d.appendChild(R.tabella(INT_BANDO, rr.map((x) => x.riga), { titolo: "Cabine per la manifestazione di interesse", num: [4, 6, 7, 8, 9, 10, 11, 13] }));
    if (!st.terreniCercati) d.appendChild(h("p", "aiuto", "I terreni pubblici non sono ancora stati cercati: «Terreni da cercare» vale per ora tutti gli impianti."));
  }
  const CRITERI = [["Distanza dalla cabina primaria", F.PESI.distanza, "da 0 al limite indicato per la cabina"],
    ["Superficie vicina a quella necessaria", F.PESI.superficie, "piena nella fascia indicata, poi decrescente"],
    ["Assenza di colture certificate", F.PESI.coltura, "dichiarazione del proprietario per le ultime tre campagne"],
    ["Proprietà in capo a un solo soggetto o lotti già uniti", F.PESI.unico, "anche più particelle confinanti candidate insieme"]];
  $("avviso-pdf").addEventListener("click", async () => {
    const rr = righeBando(), o = st.parametri;
    const doc = {
      titolo: "Avviso pubblico – manifestazione di interesse per terreni destinati a impianti fotovoltaici di comunità energetiche rinnovabili",
      sottotitolo: "Testo tipo da adattare da parte del promotore (Comune, CER o altro soggetto): le parti tra parentesi quadre vanno completate",
      nome_file: `avviso_terreni_cer_${new Date().toISOString().slice(0, 10)}`,
      sezioni: [
        { titolo: "Oggetto", blocchi: [
          ...(R.PROVA ? [{ tipo: "avvertenza", testo: "DATI SINTETICI DI PROVA (?prova=1): non reali." }] : []),
          { tipo: "paragrafo", testo: "[Nome del promotore] intende individuare terreni da destinare a impianti fotovoltaici a terra o agrivoltaici al servizio di una comunità energetica rinnovabile (CER), in ciascuna delle aree delle cabine primarie elencate sotto. I proprietari interessati possono presentare una manifestazione di interesse entro il [data], secondo il modulo allegato." },
          { tipo: "paragrafo", testo: "L'avviso non vincola il promotore né i proprietari: serve a raccogliere disponibilità da confrontare con criteri dichiarati in anticipo. L'eventuale accordo (diritto di superficie, affitto o cessione) sarà definito dopo le verifiche tecniche e autorizzative." },
        ] },
        { titolo: "Terreni cercati per cabina primaria", blocchi: [
          { tipo: "tabella", intestazioni: ["COD_AC (GSE)", "Cabina", "Comune della cabina", "Terreni da cercare", "kW per impianto", "Superficie (ha)", "Distanza massima (km)", "Classi ammesse"],
            righe: rr.map((x) => [x.riga[0], x.riga[1], x.riga[5], x.cercare, x.riga[11], x.riga[12], x.riga[13], x.riga[14]]) },
          { tipo: "paragrafo", testo: `Impianti ${F.TIPI[o.tipo].nome}; superfici stimate con ${R.num(F.TIPI[o.tipo].haMw, 1)} ha per MWp più accessi, cabina di consegna e accumulo. I terreni devono trovarsi nell'area convenzionale della cabina indicata (verifica ufficiale: GSE, ricerca per punto di connessione).` },
        ] },
        { titolo: "Requisiti e regole", blocchi: [
          { tipo: "elenco", voci: [
            "Terreni in zona agricola o in area idonea ai sensi dell'art. 11-bis del D.Lgs. 190/2024 e della L.R. Emilia-Romagna 29/05/2026 n. 5.",
            "Fuori dalle aree idonee sono ammessi impianti fotovoltaici a terra fino a 1 MW intestati a una CER o che le cedono tutta l'energia, oppure impianti agrivoltaici (art. 10 della L.R. 5/2026).",
            "Sui terreni con colture certificate (biologico, produzione integrata, DOP/IGP, foraggi per il Parmigiano Reggiano) nelle ultime tre campagne è ammesso solo l'agrivoltaico, con l'attestazione di un agronomo.",
            "Il proprietario dichiara la titolarità allegando una propria visura catastale aggiornata.",
          ] },
        ] },
        { titolo: "Criteri della graduatoria", blocchi: [
          { tipo: "tabella", intestazioni: ["Criterio", "Punti (su 100)", "Come si valuta"], righe: CRITERI },
          { tipo: "paragrafo", testo: "A parità di punteggio prevale la candidatura arrivata prima. Il promotore può affiancare ai criteri tecnici una valutazione economica (canone, durata, tipo di diritto), dichiarandone il peso nell'avviso." },
        ] },
        { titolo: "Modulo della manifestazione di interesse", blocchi: [
          { tipo: "elenco", numerato: true, voci: ["Dati del proprietario (nome o ragione sociale, recapiti) – restano al promotore", "Comune, foglio e particella di ogni terreno; superficie disponibile (ha)",
            "Cabina primaria (COD_AC) di riferimento, se nota", "Tipo di accordo proposto (diritto di superficie, affitto, cessione), canone o prezzo e durata",
            "Disponibilità all'agrivoltaico e all'ingresso nella CER come socio", "Dichiarazione sulle colture certificate nelle ultime tre campagne", "Impegno a mantenere l'offerta per [n] mesi", "Visura catastale allegata"] },
          { tipo: "avvertenza", livello: "info", testo: "Trattamento dei dati personali: titolare è il promotore, che pubblica l'informativa (art. 13 del Regolamento UE 2016/679). EuGEnio non riceve né conserva le domande." },
        ] },
      ],
      fonti: [{ testo: "L.R. Emilia-Romagna 29/05/2026 n. 5 – aree idonee", url: "https://bur.regione.emilia-romagna.it/area-bollettini/n-135-del-29-05-2026-parte-prima/individuazione-delle-aree-idonee-e-disciplina-dellinstallazione-degli-impianti-alimentati-a-fonti-rinnovabili-nel-territorio-regionale/l-r-5-2026" },
        { testo: "GSE S.p.A. – codici delle aree convenzionali (COD_AC)", url: R.GSE.SCHEDA }],
    };
    $("avviso-pdf").disabled = true;
    try { await R.documento(doc, "pdf", $("messaggio-bando")); } finally { $("avviso-pdf").disabled = false; }
  });
  $("modulo-csv").addEventListener("click", () => {
    const testa = ["cod_ac", "comune", "foglio", "particella", "superficie_ha", "accordo", "canone_euro_anno", "durata_anni", "agrivoltaico_si_no", "socio_cer_si_no", "colture_certificate_si_no", "note"];
    R.csv(`modulo_candidature_terreni_cer_${new Date().toISOString().slice(0, 10)}.csv`, [{ titolo: "Candidature", intestazioni: testa, righe: [] }],
      ["Una riga per particella candidata, senza dati personali: i dati del proprietario restano nella domanda presso il promotore."]);
    messaggio("messaggio-bando", "Modulo scaricato.");
  });

  // ================================================================== mappa
  function fcEdifici() {
    return { type: "FeatureCollection", features: st.edifici.map((e) => ({ type: "Feature", geometry: { type: "Point", coordinates: [e.lon, e.lat] },
      properties: { id: e.id, nome: e.nome, area: e.area ? e.area.COD_AC : "", curva: !!(st.curve && st.curve.serie.has(e.id)) } })) };
  }
  function fcCabine() {
    return { type: "FeatureCollection", features: st.cabine.filter((c) => c.coord).map((c) => ({ type: "Feature", geometry: { type: "Point", coordinates: c.coord },
      properties: { ...c.props, cod_ac: c.cod_ac } })) };
  }
  function fcTerreni() {
    const out = [];
    for (const c of st.cabine) for (const t of (c.terreni || []).slice(0, Math.max(st.parametri.nTerreni * 2, 10))) {
      const cl = t.ammesso ? t.classe : "X";
      out.push({ type: "Feature", geometry: { type: "Point", coordinates: [t.lon, t.lat] },
        properties: { ref: t.ref, cod_ac: c.cod_ac, colore: COLORI_TERRENI[cl] || COLORI_TERRENI.X, punti: t.punti, ammesso: t.ammesso } });
    }
    return { type: "FeatureCollection", features: out };
  }
  function disegna() {
    const m = st.det; if (!m || !m.getSource("cer-edifici")) return;
    m.getSource("cer-edifici").setData(fcEdifici());
    m.getSource("cer-cabine").setData(fcCabine());
    m.getSource("cer-terreni").setData(st.terreniCercati ? fcTerreni() : vuota());
    m.getSource("cer-aree").setData(st.aree || vuota());
    const a = $("attribuzione-gse");
    a.hidden = !st.aree;
    a.textContent = st.aree ? `${R.ATTR.gse} (${R.GSE.SCHEDA}); aree semplificate, lette il ${R.oraIt(st.aree.letto)}. Non entrano nelle immagini scaricate.` : "";
    legenda(); chiudiAttribuzione();
  }
  // inquadra edifici, cabine e terreni mostrati; attribuzione compatta chiusa (le fonti complete sono sotto la mappa)
  function inquadra() {
    const m = st.det; if (!m) return;
    const pts = [...st.edifici.map((e) => [e.lon, e.lat]), ...st.cabine.filter((c) => c.coord).map((c) => c.coord),
      ...(st.terreniCercati ? fcTerreni().features.map((f) => f.geometry.coordinates) : [])];
    if (!pts.length) return;
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    m.fitBounds([[Math.min(...xs), Math.min(...ys)], [Math.max(...xs), Math.max(...ys)]], { padding: 50, maxZoom: 15, duration: 700 });
  }
  function chiudiAttribuzione() {
    const m = st.det; if (!m) return;
    const t = () => m.getContainer().querySelectorAll(".maplibregl-compact-show").forEach((x) => x.classList.remove("maplibregl-compact-show"));
    t(); m.once("idle", t);
  }
  function legenda() {
    const L = $("legenda-cer"); L.innerHTML = "";
    const voce = (i, t) => { const s = h("span"); s.append(i, t); L.appendChild(s); };
    voce(R.campione("cabina", "VERDE"), "cabina primaria (colore della saturazione)");
    voce(R.campione("punto", COLORE_EDIFICI), "edifici");
    if (st.aree) voce(R.campione("area"), "aree del GSE delle cabine (dal vivo)");
    if (st.terreniCercati) for (const [k, t] of [["C", "terreno pubblico adatto"], ["A", "solo agrivoltaico"], ["X", "escluso"]]) {
      const i = h("i", "campione-rete"); i.style.background = COLORI_TERRENI[k]; i.style.borderRadius = "2px"; i.setAttribute("aria-hidden", "true"); voce(i, t);
    }
  }
  function stratiCer(m, prima) {
    m.addSource("cer-aree", { type: "geojson", data: vuota(), attribution: R.ATTR.gse });
    m.addLayer({ id: "cer-aree-fondo", type: "fill", source: "cer-aree", paint: { "fill-color": colore("--primario"), "fill-opacity": 0.06 } }, prima);
    m.addLayer({ id: "cer-aree-linea", type: "line", source: "cer-aree", paint: { "line-color": colore("--primario"), "line-width": 2.4 } }, prima);
    m.addSource("cer-tutte", { type: "geojson", data: vuota(), attribution: "Cabine: © contributori OpenStreetMap (ODbL); e-distribuzione" });
    R.stratoCabine(m, "cer-tutte", { prima, raggio: RAGGIO_CABINE, bordo: BORDO_CABINE });
    m.addSource("cer-cabine", { type: "geojson", data: vuota() });
    m.addLayer({ id: "cer-cabine-anello", type: "circle", source: "cer-cabine", paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 5, 8, 10, 10, 14, 13],
      "circle-color": "rgba(0,0,0,0)", "circle-stroke-color": colore("--primario"), "circle-stroke-width": 3 } }, prima);
    m.addSource("cer-terreni", { type: "geojson", data: vuota() });
    m.addLayer({ id: "cer-terreni", type: "circle", source: "cer-terreni", paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 4, 14, 9],
      "circle-color": ["get", "colore"], "circle-stroke-color": "#1a1a1a", "circle-stroke-width": 1.2, "circle-pitch-alignment": "map" } }, prima);
    m.addSource("cer-edifici", { type: "geojson", data: vuota() });
    m.addLayer({ id: "cer-edifici", type: "circle", source: "cer-edifici", paint: { "circle-radius": 6, "circle-color": COLORE_EDIFICI,
      "circle-stroke-color": "#1a1a1a", "circle-stroke-width": 1.5, "circle-opacity": ["case", ["get", "curva"], 1, 0.45] } }, prima);
    R.suggerimento(m, () => ["cer-edifici", "cer-terreni", "cer-cabine-anello", "cer-tutte-punti", "cer-aree-fondo"], (f) => {
      const p = f.properties || {};
      if (f.layer.id === "cer-edifici") return { titolo: [p.id, p.nome].filter(Boolean).join(" · "), righe: [p.area ? `Area GSE: ${p.area}` : "Nessuna area del GSE", p.curva ? "con la curva di carico" : "senza curva di carico"] };
      if (f.layer.id === "cer-terreni") {
        const c = st.cabine.find((x) => x.cod_ac === p.cod_ac), t = c && c.terreni.find((x) => x.ref === p.ref);
        if (!t) return null;
        return { titolo: `${t.comune || ""} – foglio ${t.foglio || "–"}, particella ${t.particella || "–"}`, righe: [`${num(t.ha, 2)} ha a ${num(t.distanza_m / 1000, 2)} km dalla cabina ${c.cod_ac}`,
          `Ente: ${t.ente}${t.n_enti > 1 ? ` e altri ${t.n_enti - 1}` : ""}`, `Coltura DOP o certificata: ${testoColtura(t)}`, t.ammesso ? `Classe ${t.classe}, ${t.punti} punti` : `Escluso: ${t.motivi.join("; ")}`] };
      }
      if (f.layer.id === "cer-aree-fondo") return { titolo: `Area convenzionale ${p.COD_AC}`, righe: [`Gestore: ${p.RAG_SOC || "–"}`, R.ATTR.gse], cursore: false };
      if (f.layer.id === "cer-cabine-anello") {
        const c = st.cabine.find((x) => x.cod_ac === p.cod_ac);
        const r = c && c.ris ? [`FV ${num(c.ris.P)} kW, accumulo ${num(c.ris.E)} kWh`, `${c.ris.nImpianti} impianti, quota condivisa ${pct(c.ris.quota)}`] : [];
        return { titolo: c ? nomeCabina(c) : p.cod_ac, righe: [...(c && c.props ? R.righeCabina(c.props) : []), ...r] };
      }
      return { titolo: R.nomeCabina(p), righe: R.righeCabina(p), cursore: false };
    });
    document.addEventListener("eugenio:aspetto", () => {
      m.setPaintProperty("cer-aree-fondo", "fill-color", colore("--primario"));
      m.setPaintProperty("cer-aree-linea", "line-color", colore("--primario"));
      m.setPaintProperty("cer-cabine-anello", "circle-stroke-color", colore("--primario"));
    });
  }
  function primoSopra(m) { const l = m.getStyle().layers.find((x) => !["sfondo", "contesto", "ortofoto"].includes(x.id)); return l ? l.id : undefined; }
  async function mappa() {
    const m = new ml.Map({ container: "mappa-dettaglio", bounds: [[C.ITALIA[0], C.ITALIA[1]], [C.ITALIA[2], C.ITALIA[3]]], fitBoundsOptions: { padding: 10 },
      maxZoom: 21, minZoom: 4, attributionControl: false, canvasContextAttributes: { preserveDrawingBuffer: true },
      style: { version: 8, sources: {}, layers: [{ id: "sfondo", type: "background", paint: { "background-color": colore("--carta") } }] } });
    st.det = m;
    if (window.EUGENIO_LIMITI) window.EUGENIO_LIMITI.collega(m);
    m.addControl(new ml.NavigationControl({ showCompass: false }), "top-right");
    m.addControl(new ml.ScaleControl({ unit: "metric" }), "bottom-left");
    m.addControl(new ml.AttributionControl({ compact: true }), "bottom-right");
    await new Promise((ok) => m.on("load", ok));
    m.resize();
    const cam = m.cameraForBounds([[C.ITALIA[0], C.ITALIA[1]], [C.ITALIA[2], C.ITALIA[3]]], { padding: 10 });
    if (cam) m.jumpTo({ ...cam, zoom: Math.max(5, cam.zoom) });
    document.addEventListener("eugenio:ridimensiona", () => m.resize());
    document.addEventListener("eugenio:aspetto", () => m.setPaintProperty("sfondo", "background-color", colore("--carta")));
    if (window.pmtiles) { const proto = new window.pmtiles.Protocol(); ml.addProtocol("pmtiles", proto.tile); }
    if (window.EUGENIO_RIGHELLO) st.righello = window.EUGENIO_RIGHELLO.aggiungi(m, { dove: $("posto-righello") });
    if (window.EUGENIO_SPOSTA && $("sposta-ortofoto")) st.sposta = window.EUGENIO_SPOSTA.crea($("sposta-ortofoto"), { pagina: "fv-cer", suCambio: spostaTessere });
    try { await C.aggiungi(m, { clic: false }); } catch { /* confini non disponibili */ }
    stratiCer(m);
    tutteLeCabine().then((fc) => { if (m.getSource("cer-tutte")) m.getSource("cer-tutte").setData(fc); })
      .catch((e) => messaggio("messaggio-dettaglio", `Cabine primarie non disponibili: ${e.message}`, true));
    if (window.EUGENIO_STRATI) {
      try { st.strati = await window.EUGENIO_STRATI.aggiungi(m, { caselle: $("caselle-strati"), legenda: $("legenda-strati"), sotto: () => primoSopra(m) }); } catch { /* strati non disponibili */ }
    }
    $("caselle-strati").addEventListener("change", aggiornaSposta);
    await ortofoto(m);
    if (window.EUGENIO_ESPORTA) window.EUGENIO_ESPORTA.pulsanti($("scarica-dettaglio"), m, () => opzioniImmagine(m), $("messaggio-dettaglio"));
    disegna();
  }
  // ---- ortofoto (come in «Cabine primarie»)
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
    } catch { $("attribuzione-ortofoto").textContent = "Il servizio delle ortofoto non risponde: restano i confini, le particelle e gli edifici."; return; }
    st.contesto = st.fonti.find((f) => f.id === CONTESTO) || null;
    if (st.contesto) { m.addSource("contesto", sorgente(st.contesto)); m.addLayer({ id: "contesto", type: "raster", source: "contesto", paint: { "raster-opacity": 0.95 } }, primoSopra(m)); }
    $("fonte-dettaglio").addEventListener("change", (e) => { st.manuale = true; scegliFonte(e.target.value); });
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
    if (f && f.id !== CONTESTO) { m.addSource("ortofoto", sorgente(f, true)); m.addLayer({ id: "ortofoto", type: "raster", source: "ortofoto" }, primoSopra(m)); }
    aggiornaSposta(); attribuzioneOrto();
  }
  function citOrto(f) { return window.EUGENIO_ORTOFOTO_ANNI && st.det ? window.EUGENIO_ORTOFOTO_ANNI.citazione(f, st.det) : f.citazione; }
  function attribuzioneOrto() {
    const f = st.fonte, a = $("attribuzione-ortofoto"); a.innerHTML = "";
    if (!f) a.textContent = st.contesto ? `Nessuna ortofoto: sotto si vede il contesto ${st.contesto.citazione} (${st.contesto.licenza}).` : "Nessuna ortofoto.";
    else { a.append("Ortofoto: ", citOrto(f), " – licenza "); const l = h("a", null, f.licenza); l.href = f.scheda; a.appendChild(l); a.append(f.copia ? "." : ". Solo consultazione dal vivo: non entra nelle immagini scaricate."); }
    st.citazioneOrto = f ? citOrto(f) : "";
  }
  function vettoriAccesi() { const s = st.strati && st.strati.stato; return !!(s && (s.particelle || s.edifici)); }
  function aggiornaSposta() { if (st.sposta) st.sposta.fonte(st.fonte, { vettori: vettoriAccesi() }); }
  function spostaTessere() { const src = st.det && st.det.getSource("ortofoto"), f = st.fonte; if (src && f && !f.pmtiles && src.setTiles) src.setTiles([tessere(f, true)]); }
  function opzioniImmagine(m) {
    const righe = [], f = st.fonte;
    if (f && !f.copia) return `«${f.nome}» è solo in consultazione dal vivo: per scaricare l'immagine scegli un'altra ortofoto.`;
    if (f) righe.push(`Ortofoto: ${citOrto(f)} – licenza ${f.licenza} (${f.scheda}).`);
    else if (st.contesto) righe.push(`Contesto: ${st.contesto.citazione} – licenza ${st.contesto.licenza} (${st.contesto.scheda}).`);
    if (st.strati) righe.push(...st.strati.righe());
    righe.push("Cabine primarie: colore della saturazione; anello = cabine degli edifici. " + `${R.ATTR.osm}. ${R.ATTR.ed_breve}.`);
    if (st.terreniCercati) righe.push("Terreni pubblici: MEF – Patrimonio della PA e AdE (CC BY 4.0); verde adatto, arancione solo agrivoltaico, grigio escluso.");
    righe.push(`${R.ATTR.confini}. Mappa: MapLibre GL JS (BSD-3).`);
    if (st.aree) righe.push("Le aree convenzionali del GSE non entrano nell'immagine (licenza CC BY-NC-SA).");
    if (R.PROVA) righe.unshift("ATTENZIONE: DATI SINTETICI DI PROVA (?prova=1), non reali.");
    const accese = ["cer-aree-fondo", "cer-aree-linea"].filter((id) => m.getLayer(id) && m.getLayoutProperty(id, "visibility") !== "none");
    accese.forEach((id) => m.setLayoutProperty(id, "visibility", "none"));
    const c = m.getCenter();
    return { titolo: `CER – Sviluppo impianti FV – ${c.lat.toFixed(5)} N, ${c.lng.toFixed(5)} E`, righe, nome: `cer_impianti_fv_${new Date().toISOString().slice(0, 10)}`,
      dopo: () => accese.forEach((id) => { if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", "visible"); }) };
  }

  // ================================================================== 6. file
  function datiFile() {
    if (!st.calcolato) return "Niente da scaricare: carica edifici e curve e premi «Calcola».";
    const o = st.parametri;
    const par = [["Ore di accumulo", o.h], ["Quota minima condivisa (%)", Math.round(o.qMin * 100)], ["Quota calcolata su", o.denominatore === "immessa" ? "energia immessa" : "produzione"],
      ["Tipo di impianto", F.TIPI[o.tipo].nome], ["Superficie specifica (ha/MWp)", F.TIPI[o.tipo].haMw], ["Inclinazione (°)", o.inclinazione], ["Orientamento (°)", o.orientamento],
      ["Perdite (%)", Math.round(o.perdite * 100)], ["Potenza massima per impianto (kW)", o.potenzaMassimaImpianto], ["Potenza massima per cabina (kW)", o.potenzaMassima ?? "nessuna"],
      ["Distanza massima dei terreni (km)", o.distanzaKm], ["Terreni per cabina", o.nTerreni], ["Tolleranza sulla superficie", o.tolleranza]];
    const edi = st.edifici.map((e) => { const v = st.curve && st.curve.serie.get(e.id);
      return [e.id, e.nome, e.indirizzo, Math.round(e.lat * 1e6) / 1e6, Math.round(e.lon * 1e6) / 1e6, e.origine, e.area ? e.area.COD_AC : "", v ? Math.round(F.totale(v)) : null, v ? Math.round(100 * st.curve.copertura.get(e.id)) : null]; });
    const cab = st.cabine.map((c) => { const r = c.ris || {}, x = r.impianti && r.impianti[0];
      return [c.cod_ac, nomeCabina(c), c.props ? c.props.cod_cp_ed || "" : "", livello(c), c.edifici.length, c.curva ? Math.round(c.curva.kwh) : null, r.P ?? null, r.E != null ? Math.round(r.E) : null,
        r.produzione != null ? Math.round(r.produzione) : null, r.condivisa != null ? Math.round(r.condivisa) : null, r.quota != null ? Math.round(1000 * r.quota) / 10 : null,
        r.autosufficienza != null ? Math.round(1000 * r.autosufficienza) / 10 : null, r.nImpianti ?? null, x ? Math.round(x.kw) : null, x ? Math.round(100 * x.haMin) / 100 : null,
        x ? Math.round(100 * x.haMax) / 100 : null, r.haSau != null ? Math.round(100 * r.haSau) / 100 : null, c.clima ? `${c.clima.comune} ${c.clima.anno}${c.clima.sintetico ? " sintetico" : ""}` : "", c.errore || r.motivo || ""]; });
    const ter = [];
    for (const c of st.cabine) for (const [i, t] of (c.terreni || []).slice(0, Math.max(o.nTerreni * 2, 10)).entries())
      ter.push([c.cod_ac, i + 1, t.comune || "", t.foglio || "", t.particella || "", Math.round(100 * t.ha) / 100, Math.round(t.distanza_m), t.ente || "", t.n_enti || 1, t.settore || "",
        t.ente_sede || "", t.tipologie || "", t.prob_coltura ?? null, t.classe_coltura || "", t.classe, testoGse(t, c), t.ammesso ? t.punti : null, t.motivi.join("; "), Math.round(t.lat * 1e5) / 1e5, Math.round(t.lon * 1e5) / 1e5]);
    const bando = st.calcolato ? righeBando().map((x) => x.riga) : [];
    const sezioni = [
      { titolo: "Parametri", intestazioni: ["Parametro", "Valore"], righe: par },
      { titolo: "Edifici", intestazioni: ["Id", "Nome", "Indirizzo", "Latitudine", "Longitudine", "Origine", "COD_AC (GSE)", "Consumo annuo (kWh)", "Ore presenti (%)"], righe: edi },
      { titolo: "Potenza per cabina primaria", intestazioni: ["COD_AC (GSE)", "Cabina", "Codice e-distribuzione", "Saturazione", "Edifici", "Consumi (kWh)", "FV (kW)", "Accumulo (kWh)", "Produzione (kWh)",
        "Condivisa (kWh)", "Quota condivisa (%)", "Autosufficienza (%)", "Impianti", "kW per impianto", "ha per impianto (min)", "ha per impianto (max)", "Suolo agricolo occupato (ha)", "Clima", "Note"], righe: cab },
      { titolo: "A – Terreni pubblici", intestazioni: ["COD_AC (GSE)", "N.", "Comune", "Foglio", "Particella", "Superficie (ha)", "Distanza (m)", "Ente proprietario", "Enti", "Settore", "Sede dell'ente",
        "Tipologie", "Probabilità di coltura DOP o certificata (%)", "Classe di probabilità", "Classe del terreno", "Area GSE", "Punti", "Note", "Latitudine", "Longitudine"], righe: ter },
      { titolo: "B – Cabine per la manifestazione di interesse", intestazioni: INT_BANDO, righe: bando },
    ];
    const piede = [
      ...(R.PROVA ? ["ATTENZIONE: DATI SINTETICI DI PROVA (?prova=1), non reali."] : []),
      `${R.ATTR.gse_codici} (${R.GSE.SCHEDA}); nel file solo i codici. La cabina che conta per gli incentivi è quella dell'area del punto di connessione (POD): verifica ufficiale con la ricerca per POD del GSE.`,
      `${R.ATTR.ed}. ${R.ATTR.osm}.`, "Clima orario: elaborazione EuGEnio su dati Open-Meteo.com (ERA5/Copernicus corretto verso ICON), CC BY 4.0.",
      "Terreni pubblici: MEF – Patrimonio della PA, dati al 31/12/2023 (CC BY 4.0), su cartografia catastale dell'Agenzia delle Entrate (CC BY 4.0). Probabilità di coltura DOP o certificata: indicatore di EuGEnio sui piani colturali grafici di AGREA (dati non ceduti), non è una certificazione.",
      "Regole: L.R. Emilia-Romagna 29/05/2026 n. 5 e art. 11-bis del D.Lgs. 190/2024; superfici, perdite e accumulo indicativi.",
      "Licenza: dati elaborati da EuGEnio CC BY 4.0; posizioni delle cabine ODbL 1.0 (© contributori OpenStreetMap).",
    ];
    const nome = `cer_impianti_fv_${new Date().toISOString().slice(0, 10)}`;
    const doc = { titolo: "CER – Sviluppo impianti FV", sottotitolo: `${st.edifici.length} edifici, ${st.cabine.length} cabine primarie`, nome_file: nome,
      sezioni: [
        { titolo: "Come leggere", blocchi: [
          ...(R.PROVA ? [{ tipo: "avvertenza", testo: "DATI SINTETICI DI PROVA (?prova=1): non reali." }] : []),
          { tipo: "paragrafo", testo: "Per ogni area convenzionale del GSE con almeno un edificio: consumi orari sommati, potenza fotovoltaica più alta per cui l'energia condivisa (ora per ora, minimo fra energia immessa e consumi) resta sopra la quota scelta, accumulo, numero e superficie degli impianti. A: terreni pubblici in proprietà vicino alla cabina; B: terreni da cercare con una manifestazione di interesse." },
          { tipo: "avvertenza", livello: "info", testo: "Stima preliminare: idoneità dei terreni, vincoli e colture certificate vanno verificati (strumenti urbanistici, attestazione di un agronomo); la cabina che conta è quella del punto di connessione." },
        ] },
        ...sezioni.map((s) => ({ titolo: s.titolo, blocchi: [{ tipo: "tabella", intestazioni: s.intestazioni, righe: s.righe.length ? s.righe : [s.intestazioni.map(() => null)] }] })),
      ],
      fonti: [{ testo: "GSE S.p.A. – codici delle aree convenzionali (COD_AC)", url: R.GSE.SCHEDA }, { testo: "e-distribuzione S.p.A. – Aree critiche", url: R.URL_ED },
        { testo: "© contributori OpenStreetMap – posizioni delle cabine primarie, ODbL 1.0", url: R.URL_OSM }, { testo: "Open-Meteo.com – ERA5/ICON (CC BY 4.0)", url: "https://open-meteo.com/" },
        { testo: "MEF – Patrimonio della PA (CC BY 4.0)", url: "https://www.dt.mef.gov.it/it/attivita_istituzionali/patrimonio_pubblico/" },
        { testo: "AGREA – piani colturali grafici (solo l'indicatore)", url: "https://agrea.regione.emilia-romagna.it/servizi/documentazione/open-data-sullutilizzo-del-suolo-1" }] };
    return { csv: [`${nome}.csv`, sezioni, piede], doc };
  }

  // ================================================================== avvio e collegamento
  elencoCabine();
  R.pulsantiDati($("scarica-dati"), datiFile, $("messaggio-dati"));
  mappa().catch((e) => messaggio("messaggio-dettaglio", `Mappa non disponibile: ${e.message}`, true))
    .finally(() => { st.pronto = true; if (st.det && window.EUGENIO_COLLEGAMENTO) st.det.on("moveend", () => window.EUGENIO_COLLEGAMENTO.aggiorna()); });
  // collegamento a questa simulazione (regola del 20/11/2026): vista, ortofoto scelta a mano e parametri (data-collegamento);
  // mai i file caricati
  const sei = (x) => Number(x).toFixed(6);
  if (window.EUGENIO_COLLEGAMENTO) window.EUGENIO_COLLEGAMENTO.registra({
    regione: false, chiavi: ["centro", "fonte"], principali: ["centro", "fonte"], pronto: () => st.pronto,
    leggi() { const m = st.det; if (!m || !st.pronto) return null; const c = m.getCenter();
      return { centro: [sei(c.lat), sei(c.lng), m.getZoom().toFixed(2)].join("*"), fonte: st.manuale ? (st.fonte ? st.fonte.id : "nessuna") : null }; },
    async applica(p) {
      const m = st.det; if (!m) return;
      const [lat, lon, z] = (p.get("centro") || "").split("*").map(Number);
      if ([lat, lon, z].every(Number.isFinite)) m.jumpTo({ center: [lon, lat], zoom: z });
      if (p.has("fonte")) { st.manuale = true; const id = p.get("fonte") === "nessuna" ? "" : p.get("fonte"); if (!id || st.fonti.some((f) => f.id === id)) scegliFonte(id); await elencoFonti(); }
    },
  });
  window.EUGENIO_CER_FV_PAGINA = { st, datiFile, parametri, righeBando, opzioniImmagine };
})();
