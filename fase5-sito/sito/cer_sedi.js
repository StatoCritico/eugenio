"use strict";
// Fotovoltaico › «Comunità energetiche» (edificio-cer.html), sedi e cabine primarie (20/11/2026; riferimento tecnico:
// documenti/CABINE_PRIMARIE_GSE_SERVIZIO_2026-11-17.md, punti A-D). Il calcolo dell'energia condivisa resta in
// analisi_pubbliche.js, che per ogni sede usa la cabina scritta qui (cabinaDi) e si ricalcola all'evento «eugenio:cer-sedi».
//
//  - Sede → area convenzionale dal vivo (punto A): per ogni sede con le coordinate il browser chiede al servizio del GSE
//    l'area che la contiene (R.gse.areeAccanto, rete.js: 50 m di margine; più aree = sede sul confine, mostrate tutte e
//    due con un avviso; nessuna area = isola minore, SDC o mare, con un avviso). Il COD_AC PRECOMPILA il campo «Cabina»,
//    che resta modificabile, con la nota R.GSE.NOTA_SEDE. Elenchi CSV/Excel/ODS: al massimo R.GSE.INSIEME (4) richieste
//    alla volta, in coda; risposte in memoria per la durata della pagina (rete.js), niente localStorage, niente proxy.
//  - Menu delle cabine di e-distribuzione del comune della sede (comune dai confini ISTAT del sito, cabine da GET
//    /api/rete/cabine/comune/<istat>, una richiesta per comune): nome, COD_AC del raccordo, saturazione. Comuni di un altro
//    distributore (R.statoComune = "altro"): avviso e rimando alla mappa del GSE; «servito in parte da un altro
//    distributore» (servitoed = 0 ma con trasformatori di e-distribuzione: mai «non concessionario»): nota e menu.
//  - Mappa: sedi, cabine dei loro comuni (colore della saturazione, come in Cabine primarie) e strato «Aree convenzionali
//    (GSE)» (punto B): casella spenta in partenza, attivo da zoom R.GSE.ZOOM_MIN (10; sotto, un messaggio), richiesta per il
//    riquadro visibile ~400 ms dopo la fine di ogni spostamento (R.gse.areeNelRiquadro, riquadri già visti in memoria),
//    contorni con l'etichetta COD_AC (segnaposto HTML: la mappa non ha font), riquadro al clic con codice, gestore, data di
//    consegna e collegamento alla mappa del GSE, attribuzione fissa sotto la mappa quando è acceso.
//  - Immagini (esporta_mappa.js): strato GSE spento durante la copia (punto C). File CSV, Excel, ODS, PDF (rete.js,
//    pulsantiDati): solo il codice della cabina con la nota R.GSE.NOTA_FILE, mai i perimetri.
//  (20/11/2026, 08:49, Paolo) struttura delle altre pagine: mappa con ortofoto, livelli, righello e comandi a sinistra;
//    istruzioni, ricerca, sedi ed esiti a destra; «Aggiungi sedi» sotto la mappa aggiunge una sede a ogni clic.
//  Nessuna richiesta al GSE senza un'azione dell'utente: solo per le sedi che aggiunge e con lo strato acceso.
//  ?prova=1: dati sintetici di rete.js (nessuna richiesta al server né al GSE).
(function () {
  const $ = (id) => document.getElementById(id);
  const R = window.EUGENIO_RETE, C = window.EUGENIO_CONFINI, T = window.EUGENIO_TABELLE;
  if (!$("tabella-sedi-cer") || !R) return;
  const ml = window.maplibregl;
  const MASSIMO = 200, ATTESA_MS = 400;
  const vuota = () => ({ type: "FeatureCollection", features: [] });
  const sopraArea = ["boolean", ["feature-state", "sopra"], false];
  const fondoColore = () => ["case", sopraArea, "#bfe3ff", colore("--primario", "#e4572e")];
  const colore = (n, d = "#888") => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || d;
  function h(tag, cls, t) { const e = document.createElement(tag); if (cls) e.className = cls; if (t !== undefined && t !== null) e.textContent = t; return e; }
  function messaggio(id, t, errore = false) { const m = $(id); if (!m) return; m.textContent = t; m.classList.toggle("errore", errore); }
  const chiave = (nome) => String(nome || "").trim().toLowerCase();
  const st = { sedi: [], seq: 0, mappa: null, comuni: new Map(), acceso: false, attesa: 0, giro: 0, aree: null, etichette: [], popup: null,
    modo: "sposta", fonti: [], fonte: null, contesto: null, manuale: false, strati: null, righello: null, sposta: null, citazioneOrto: "" };
  const E = window.EUGENIO, CONTESTO = "s2cloudless2016";
  // (20/11/2026, 14:08, Paolo) confini delle aree delle sedi a qualsiasi zoom, come in Cabine primarie
  Object.assign(st, { vicine: new Map(), poligoni: new Map(), confini: null, sopra: null });
  const MASSIMO_AREE = 600;
  R.avvisoProva(document.querySelector("main .pannello") || document.querySelector("main"));

  // ================================================================== coda delle richieste al GSE (4 alla volta)
  const coda = []; let inCorso = 0;
  function inCoda(fn) { return new Promise((ok, ko) => { coda.push({ fn, ok, ko }); avanti(); }); }
  function avanti() {
    while (inCorso < R.GSE.INSIEME && coda.length) {
      const { fn, ok, ko } = coda.shift(); inCorso++;
      fn().then(ok, ko).finally(() => { inCorso--; avanti(); });
    }
  }

  // ================================================================== sedi
  const coordinate = (s) => Number.isFinite(s.lat) && Number.isFinite(s.lon);
  function aggiungi(d) {
    if (st.sedi.length >= MASSIMO) { messaggio("messaggio-sedi", `Al massimo ${MASSIMO} sedi: togline qualcuna.`, true); return null; }
    const s = { k: ++st.seq, nome: String(d.nome || "").trim() || `Sede ${st.seq}`, lat: d.lat === undefined ? NaN : +d.lat, lon: d.lon === undefined ? NaN : +d.lon,
      istat: /^\d{6}$/.test(String(d.istat || "")) ? String(d.istat) : "", comune: "", prov: "",
      cabina: String(d.cabina || "").trim(), origine: d.cabina ? "file" : "", gse: null, giro: 0 };
    st.sedi.push(s);
    analizza(s);
    return s;
  }
  function togli(k) { st.sedi = st.sedi.filter((s) => s.k !== k); tabella(); disegnaSedi(); disegnaCabine(); ricomponiConfini(); cambiate(); }
  async function analizza(s) {
    const giro = ++s.giro;
    s.gse = coordinate(s) ? { stato: "attesa" } : null;
    tabella(); disegnaSedi();
    if (coordinate(s) && !s.istat && C) {
      try { const c = await C.comuneNelPunto(s.lon, s.lat); if (c) { s.istat = c.istat; s.comune = c.nome; s.prov = c.prov || ""; } } catch { /* fuori dai confini */ }
    }
    if (giro !== s.giro) return;
    if (coordinate(s)) {
      try { s.gse = { stato: "ok", ...(await inCoda(() => R.gse.areeAccanto(s.lon, s.lat))) }; }
      catch (e) { s.gse = { stato: "errore", errore: e.message || "servizio del GSE non raggiungibile" }; }
      if (giro !== s.giro) return;
      proponi(s);
      confiniSede(s);
    }
    riga(s);
    if (s.istat) {
      await cabineComune(s.istat).catch(() => null);
      if (giro !== s.giro) return;
      if (!s.comune) { const c = st.comuni.get(s.istat); const j = c && c.dati; if (j && j.nome) s.comune = j.nome; }
      riga(s); disegnaCabine();
    }
    avanzamento();
  }
  // COD_AC proposto dal GSE nel campo «Cabina», se l'utente non l'ha già scritto o scelto (né preso dal file)
  function proponi(s) {
    const g = s.gse;
    if (!g || g.stato !== "ok" || !["", "gse"].includes(s.origine)) return;
    const a = g.dentro[0] || null;            // sul confine: quella che contiene il punto; fuori da tutte: niente
    s.cabina = a ? a.COD_AC : ""; s.origine = a ? "gse" : "";
    cambiate();
  }
  // ---- confini delle aree delle sedi (20/11/2026, 14:08, richiesta di Paolo: «una volta che si sceglie un punto si devono
  // vedere a qualsiasi zoom»): per ogni sede l'area del GSE che la contiene (bordo spesso) e tutte le confinanti (sottili),
  // sommate fra le sedi, come in Cabine primarie (R.gse.areeVicine, poi R.gse.aree con where=COD_AC IN (…)). Lette dal
  // browser, solo a video, mai nelle immagini né nei file; i codici delle vicine si chiedono una volta per area.
  function vicineDi(s, a) {
    if (!st.vicine.has(a.COD_AC)) {
      const pr = inCoda(() => R.gse.areeVicine(s.lon, s.lat, a)).then((v) => { pr._codici = v.codici; return v.codici; });
      pr.catch(() => st.vicine.delete(a.COD_AC));
      st.vicine.set(a.COD_AC, pr);
    }
    return st.vicine.get(a.COD_AC);
  }
  async function poligoniDi(codici) {
    const mancano = codici.filter((c) => !st.poligoni.has(c));
    for (let i = 0; i < mancano.length; i += R.GSE.MASSIMO) {
      const fc = await inCoda(() => R.gse.aree(mancano.slice(i, i + R.GSE.MASSIMO)));
      for (const f of fc.features) if (f.properties && f.properties.COD_AC) st.poligoni.set(f.properties.COD_AC, f);
    }
  }
  function areaSede(s) { return s.gse && s.gse.stato === "ok" && s.gse.dentro[0] ? s.gse.dentro[0] : null; }
  async function confiniSede(s) {
    const a = areaSede(s);
    if (!a) { ricomponiConfini(); return; }
    if (st.poligoni.size >= MASSIMO_AREE) { messaggio("messaggio-aree-gse", `Ci sono già ${st.poligoni.size} aree a video: togli qualche sede per vederne altre.`, true); return; }
    try {
      const codici = await vicineDi(s, a);
      await poligoniDi(codici);
      if (!st.sedi.includes(s)) return;
      ricomponiConfini();
      const n = codici.filter((c) => c !== a.COD_AC && st.poligoni.has(c)).length;
      messaggio("messaggio-aree-gse", `Confini letti dal GSE: area ${a.COD_AC} di «${s.nome}» (bordo spesso) e ${n} ${n === 1 ? "area confinante" : "aree confinanti"}; si vedono a qualsiasi zoom e restano solo a video.`);
    } catch (e) {
      messaggio("messaggio-aree-gse", `Confini dell'area di «${s.nome}» non letti: ${e.message}. Il servizio del GSE potrebbe essere lento o non raggiungibile.`, true);
    }
  }
  function ricomponiConfini() {
    const centrali = new Set(st.sedi.map(areaSede).filter(Boolean).map((a) => a.COD_AC)), tieni = new Set();
    for (const c of centrali) { tieni.add(c); const v = st.vicine.get(c); if (v && v._codici) v._codici.forEach((x) => tieni.add(x)); }
    const features = [...tieni].filter((c) => st.poligoni.has(c)).map((c) => {
      const f = st.poligoni.get(c);
      return { type: "Feature", geometry: f.geometry, properties: { ...(f.properties || {}), _centrale: centrali.has(c) } };
    });
    st.confini = features.length ? { type: "FeatureCollection", features } : null;
    const m = st.mappa;
    if (m && m.getSource("cer-confini")) {
      st.sopra = null;
      m.getSource("cer-confini").setData(st.confini || vuota());
      for (const id of ["cer-confini-fondo", "cer-confini-linea"]) m.setLayoutProperty(id, "visibility", st.confini ? "visible" : "none");
    }
    visibilitaStrato();
  }
  function cabinaDi(nome) {
    const k = chiave(nome), s = st.sedi.find((x) => chiave(x.nome) === k && x.cabina);
    return s ? s.cabina : "";
  }
  // l'energia condivisa (analisi_pubbliche.js) si ricalcola quando cambiano le cabine
  let tCambio = 0;
  function cambiate() { clearTimeout(tCambio); tCambio = setTimeout(() => document.dispatchEvent(new CustomEvent("eugenio:cer-sedi")), 60); }

  // ================================================================== cabine e-distribuzione del comune
  function cabineComune(istat) {
    if (!st.comuni.has(istat)) {
      const v = { dati: null, errore: "", pr: null };
      v.pr = R.api(`/api/rete/cabine/comune/${istat}`).then((j) => {
        (j.cabine || []).forEach((c) => { if (typeof c.trasf === "string") { try { c.trasf = JSON.parse(c.trasf); } catch { /* resta */ } } });
        v.dati = j; return j;
      }, (e) => { v.errore = e.message || "errore"; st.comuni.delete(istat); throw e; });
      st.comuni.set(istat, v);
    }
    return st.comuni.get(istat).pr;
  }
  const cabineEd = (j) => (j && j.cabine ? j.cabine.filter((c) => R.eDistribuzione(c.gestore) && (c.cod_cp_ed || c.nome_cp_ed)) : []);
  const saturazione = (c) => (c.livello ? `saturazione: ${R.NOMI[c.livello] || c.livello}` : "saturazione: nessun dato");
  function voceCabina(c) { return `${R.nomeCabina(c)} · ${c.cod_ac || "COD_AC non abbinato"} · ${saturazione(c)}`; }

  // ================================================================== tabella delle sedi
  function avvisoGse(s) {
    const g = s.gse;
    if (!coordinate(s)) return { t: "Sede senza coordinate: niente area del GSE; scrivi la cabina a mano o scegli una cabina del comune.", tipo: "" };
    if (!g || g.stato === "attesa") return { t: "Chiedo l'area convenzionale alla mappa del GSE…", tipo: "" };
    if (g.stato === "errore") return { t: `Area convenzionale non letta (${g.errore}): il servizio del GSE potrebbe essere lento o non raggiungibile. Scrivi la cabina a mano o riprova.`, tipo: "errore", riprova: true };
    const tutte = [...g.dentro, ...g.vicine];
    if (!tutte.length) return { t: "Nessuna area convenzionale del GSE in questo punto (isola minore, sistema di distribuzione chiuso o mare?): controlla le coordinate, scrivi la cabina a mano o cerca il POD sulla mappa del GSE.", tipo: "attenzione" };
    if (tutte.length > 1) {
      const el = tutte.map((a) => `${a.COD_AC}${a.RAG_SOC ? ` (${a.RAG_SOC})` : ""}`).join(" e ");
      return { t: `Sede a meno di ${R.GSE.CONFINE_M} m dal confine tra le aree ${el}${g.dentro.length ? `: proposta ${g.dentro[0].COD_AC}, che contiene il punto` : ": il punto non è dentro nessuna delle due"}. Verifica con la ricerca per POD sulla mappa del GSE o nell'Area Clienti.`, tipo: "attenzione" };
    }
    const a = tutte[0];
    return { t: `Area ${a.COD_AC}${a.RAG_SOC ? ` (${a.RAG_SOC})` : ""}${s.origine !== "gse" && s.cabina && s.cabina !== a.COD_AC ? ` proposta dalla mappa del GSE (nel campo resta la tua cabina)` : ""}: ${R.GSE.NOTA_SEDE}.`, tipo: "" };
  }
  const ORIGINI = { gse: "proposta dalla mappa del GSE", menu: "scelta dal menu delle cabine del comune", mano: "scritta a mano", file: "dal file delle sedi" };
  function cellaComune(s) {
    const td = h("td", "comune-cer");
    if (!s.istat) { td.textContent = coordinate(s) ? "fuori dai confini dei comuni" : "–"; return td; }
    td.append(h("span", null, `${s.comune || s.istat}${s.prov ? ` (${s.prov})` : ""}`));
    return td;
  }
  function cellaMenu(s) {
    const td = h("td", "menu-cer");
    if (!s.istat) { td.appendChild(h("span", "aiuto", "Comune sconosciuto: nessun menu.")); return td; }
    const v = st.comuni.get(s.istat);
    if (!v || (!v.dati && !v.errore)) { td.appendChild(h("span", "aiuto", "Cerco le cabine del comune…")); return td; }
    if (!v.dati) { td.appendChild(h("span", "aiuto errore", `Cabine del comune non disponibili (${v.errore}).`)); return td; }
    const stato = R.statoComune(v.dati);
    if (stato === "altro") {
      const p = h("p", "avviso-comune attenzione");
      const a = h("a", null, "mappa del GSE"); a.href = R.GSE.SCHEDA; a.target = "_blank"; a.rel = "noopener";
      p.append("Comune servito da un altro distributore (non e-distribuzione): EuGEnio non ha le sue cabine. Cerca l'area convenzionale sulla ", a, ".");
      td.appendChild(p); return td;
    }
    const cab = cabineEd(v.dati);
    if (stato === "in_parte") {
      const p = h("p", "avviso-comune");
      const a = h("a", null, "mappa del GSE"); a.href = R.GSE.SCHEDA; a.target = "_blank"; a.rel = "noopener";
      p.append(`Comune ${v.dati.nota || "servito in parte da un altro distributore"}: la sede potrebbe non essere servita da e-distribuzione; verifica sulla `, a, ".");
      td.appendChild(p);
    }
    if (!cab.length) { td.appendChild(h("span", "aiuto", "Nessuna cabina di e-distribuzione abbinata al comune.")); return td; }
    const sel = h("select"); sel.setAttribute("aria-label", `Cabine di e-distribuzione del comune di ${s.comune || s.istat} per ${s.nome}`);
    const o0 = h("option", null, `${cab.length} ${cab.length === 1 ? "cabina" : "cabine"} di e-distribuzione del comune…`); o0.value = ""; sel.appendChild(o0);
    cab.forEach((c, i) => { const o = h("option", null, voceCabina(c)); o.value = String(i); if (s.cabina && (s.cabina === c.cod_ac || s.cabina === c.cod_cp_ed) && s.origine === "menu") o.selected = true; sel.appendChild(o); });
    sel.addEventListener("change", () => {
      const c = cab[+sel.value]; if (!c) return;
      s.cabina = c.cod_ac || c.cod_cp_ed; s.origine = "menu";
      riga(s); cambiate();
    });
    td.appendChild(sel);
    return td;
  }
  function cellaCabina(s) {
    const td = h("td", "cabina-cer");
    const inp = h("input"); inp.type = "text"; inp.value = s.cabina; inp.autocomplete = "off"; inp.spellcheck = false;
    inp.placeholder = "COD_AC o codice della cabina"; inp.setAttribute("aria-label", `Cabina primaria o area convenzionale di ${s.nome}`);
    inp.dataset.k = s.k;
    inp.addEventListener("change", () => {
      s.cabina = inp.value.trim(); s.origine = s.cabina ? "mano" : "";
      riga(s); cambiate();
    });
    td.appendChild(inp);
    if (s.cabina && ORIGINI[s.origine]) td.appendChild(h("p", "origine-cabina", ORIGINI[s.origine]));
    const av = avvisoGse(s), p = h("p", `avviso-gse${av.tipo ? ` ${av.tipo}` : ""}`, av.t);
    if (av.riprova) {
      const b = h("button", "bottone secondario piccolo", "Riprova"); b.type = "button";
      b.addEventListener("click", () => analizza(s));
      p.append(" ", b);
    }
    td.appendChild(p);
    return td;
  }
  function creaRiga(s) {
    const tr = h("tr"); tr.dataset.k = s.k;
    const th = h("th", null); th.scope = "row";
    th.append(h("strong", null, s.nome));
    if (coordinate(s)) th.append(h("span", "coordinate-cer", `${s.lat.toFixed(5)} N, ${s.lon.toFixed(5)} E`));
    const t = h("button", "bottone secondario piccolo", "Togli"); t.type = "button"; t.setAttribute("aria-label", `Togli ${s.nome}`);
    t.addEventListener("click", () => togli(s.k));
    const tt = h("td"); tt.appendChild(t);
    tr.append(th, cellaComune(s), cellaCabina(s), cellaMenu(s), tt);
    return tr;
  }
  // riga ridisegnata; mentre si sostituisce, il campo che perde il fuoco può mandare un altro «change»: si rimanda
  let inRiga = false;
  function riga(s) {
    if (inRiga) { queueMicrotask(() => riga(s)); return; }
    const vecchia = document.querySelector(`#tabella-sedi-cer tr[data-k="${s.k}"]`);
    if (!vecchia || !vecchia.parentNode) { if (st.sedi.includes(s)) tabella(); return; }
    const focus = vecchia.contains(document.activeElement) && document.activeElement.tagName === "INPUT";
    const nuova = creaRiga(s);
    inRiga = true;
    try { vecchia.replaceWith(nuova); } finally { inRiga = false; }
    if (focus) { const i = nuova.querySelector("input"); if (i) i.focus(); }
    disegnaLegenda();
  }
  function tabella() {
    const box = $("tabella-sedi-cer"); box.innerHTML = "";
    $("sedi-svuota").disabled = !st.sedi.length;
    if (!st.sedi.length) { box.appendChild(h("p", "aiuto", "Nessuna sede: aggiungine una con le coordinate o carica un elenco.")); return; }
    const scorre = h("div", "tabella-scorre");
    const t = h("table", "sedi-cer"), r1 = t.createTHead().insertRow();
    ["Sede", "Comune", "Cabina (area convenzionale)", "Cabine di e-distribuzione del comune", ""].forEach((x) => r1.appendChild(h("th", null, x)));
    const b = t.createTBody();
    st.sedi.forEach((s) => b.appendChild(creaRiga(s)));
    scorre.appendChild(t); box.appendChild(scorre);
    disegnaLegenda();
  }
  function avanzamento() {
    const n = st.sedi.filter((s) => coordinate(s)).length, fatte = st.sedi.filter((s) => coordinate(s) && s.gse && s.gse.stato !== "attesa").length;
    const a = $("avanzamento-sedi");
    if (!n || fatte >= n) { a.hidden = true; return; }
    a.hidden = false; $("barra-sedi").style.width = `${(100 * fatte / n).toFixed(1)}%`;
  }

  // ---- aggiunta a mano e da file
  const numero = (v) => { const t = String(v || "").trim().replace(/\s/g, ""); if (!t) return NaN; return Number(t.includes(",") ? t.replace(/\./g, "").replace(",", ".") : t); };
  const inItalia = (lat, lon) => lat > 35 && lat < 48 && lon > 6 && lon < 19.5;
  $("sede-aggiungi").addEventListener("click", () => {
    const lat = numero($("sede-lat").value), lon = numero($("sede-lon").value);
    if (!Number.isFinite(lat) || !Number.isFinite(lon) || !inItalia(lat, lon)) { messaggio("messaggio-sedi", "Coordinate non valide: latitudine e longitudine in gradi decimali, in Italia (es. 44,4949 e 11,3426).", true); return; }
    const s = aggiungi({ nome: $("sede-nome").value, lat, lon });
    if (!s) return;
    messaggio("messaggio-sedi", `«${s.nome}» aggiunta: chiedo al GSE la sua area convenzionale.`);
    $("sede-nome").value = ""; $("sede-lat").value = ""; $("sede-lon").value = "";
    inquadra();
  });
  // ricerca (indirizzo, foglio e particella o comune: cerca_luogo.js, come Cabine primarie): il luogo trovato diventa una sede
  if (window.EUGENIO_CERCA && $("cerca-luogo")) {
    window.EUGENIO_CERCA.crea($("cerca-luogo"), {
      suTrovato: (lon, lat, riga) => {
        const nome = riga.centro_comune ? `Centro di ${riga.comune_catasto || "comune"}` : (riga.indirizzo_trovato || (riga.mappale ? `Foglio ${riga.foglio_catasto} part. ${riga.mappale}` : "Sede cercata"));
        const s = aggiungi({ nome, lat, lon });
        if (!s) return;
        tabella(); disegnaSedi(); cambiate();
        messaggio("messaggio-sedi", `«${s.nome}» aggiunta: chiedo al GSE la sua area convenzionale.`);
        if (st.mappa) st.mappa.flyTo({ center: [lon, lat], zoom: riga.zoom || window.EUGENIO_CERCA.ZOOM || 17, duration: 900 });
      },
    });
  }
  $("sedi-svuota").addEventListener("click", () => { st.sedi = []; tabella(); disegnaSedi(); disegnaCabine(); ricomponiConfini(); avanzamento(); cambiate(); messaggio("messaggio-sedi", "Sedi tolte."); });
  const norm = (c) => String(c || "").trim().toLowerCase().replace(/["']/g, "").replace(/[^a-z0-9àèéìòù_]/g, "_").replace(/^_+|_+$/g, "");
  if (T) $("sedi-file").setAttribute("accept", T.ACCETTA);
  $("sedi-file").addEventListener("change", async (e) => {
    const f = e.target.files && e.target.files[0]; if (!f) return;
    try { await caricaElenco(f); } catch (x) { messaggio("messaggio-sedi", `File non letto: ${x.message || x}.`, true); }
    e.target.value = "";
  });
  async function caricaElenco(file) {
    if (!T) throw new Error("lettore dei file non disponibile");
    messaggio("messaggio-sedi", "Lettura del file…");
    const letto = await T.leggi(file);
    const linee = letto.testo.split(/\r?\n/).filter((r) => r.trim() && !r.trim().startsWith("#") && !/^"?Fonte: EuGEnio/i.test(r.trim()));
    if (linee.length < 2) throw new Error("il file non contiene righe di dati");
    const tab = T.righe(linee.join("\n"), T.separatore(linee[0]));
    const testa = tab[0].map(norm), corpo = tab.slice(1).filter((r) => r.some((x) => String(x).trim()));
    if (corpo.length + st.sedi.length > MASSIMO) throw new Error(`il file ha ${corpo.length} righe: al massimo ${MASSIMO} sedi in questa pagina`);
    const col = (...n) => testa.findIndex((x) => n.includes(x));
    const iNome = col("sede", "nome", "denominazione", "id", "pod", "utenza"), iLat = col("lat", "latitudine"), iLon = col("lon", "lng", "longitudine"),
      iCab = col("cabina", "cabina_primaria", "cod_ac"), iIstat = col("istat", "codice_istat");
    if (iNome < 0) throw new Error("serve la colonna «sede» (o nome, denominazione)");
    const val = (r, i) => (i >= 0 ? String(r[i] ?? "").trim() : "");
    let con = 0, senza = 0, scarti = 0;
    for (const r of corpo) {
      const lat = T.numero(val(r, iLat), { decimalePunto: letto.decimalePunto }), lon = T.numero(val(r, iLon), { decimalePunto: letto.decimalePunto });
      const ok = lat !== null && lon !== null && inItalia(lat, lon), grezzo = val(r, iIstat), istat = /^\d{4,6}$/.test(grezzo) ? grezzo.padStart(6, "0") : "";
      if (!ok && !/^\d{6}$/.test(istat)) { scarti++; continue; }
      if (aggiungi({ nome: val(r, iNome), lat: ok ? lat : NaN, lon: ok ? lon : NaN, istat: ok ? "" : istat, cabina: val(r, iCab) })) { if (ok) con++; else senza++; }
    }
    inquadra();
    messaggio("messaggio-sedi", [`${con + senza} sedi aggiunte (${con} con le coordinate, chieste al GSE ${R.GSE.INSIEME} alla volta)${scarti ? `; ${scarti} righe senza coordinate né codice ISTAT scartate` : ""}.`, letto.nota].filter(Boolean).join(" "));
  }

  // ================================================================== mappa
  function fcSedi() {
    return { type: "FeatureCollection", features: st.sedi.filter(coordinate).map((s) => ({ type: "Feature", geometry: { type: "Point", coordinates: [s.lon, s.lat] },
      properties: { k: s.k, nome: s.nome } })) };
  }
  function fcCabine() {
    const viste = new Map(), istat = new Set(st.sedi.map((s) => s.istat).filter(Boolean));
    for (const i of istat) {
      const v = st.comuni.get(i);
      for (const c of cabineEd(v && v.dati)) {
        if (!Number.isFinite(+c.lat) || !Number.isFinite(+c.lon) || c.lat === null || c.lon === null) continue;
        const k = c.cod_cp_ed || c.cod_ac; if (viste.has(k)) continue;
        viste.set(k, { type: "Feature", geometry: { type: "Point", coordinates: [+c.lon, +c.lat] }, properties: { ...c, trasf: c.trasf, _colore: R.coloreCabina(c) } });
      }
    }
    return { type: "FeatureCollection", features: [...viste.values()] };
  }
  function disegnaSedi() { const m = st.mappa; if (m && m.getSource("cer-sedi")) m.getSource("cer-sedi").setData(fcSedi()); disegnaLegenda(); }
  function disegnaCabine() { const m = st.mappa; if (m && m.getSource("cer-cabine")) m.getSource("cer-cabine").setData(fcCabine()); disegnaLegenda(); }
  function inquadra() {
    const m = st.mappa, pts = st.sedi.filter(coordinate);
    if (!m || !pts.length) return;
    const xs = pts.map((s) => s.lon), ys = pts.map((s) => s.lat);
    if (pts.length === 1) m.easeTo({ center: [xs[0], ys[0]], zoom: Math.max(m.getZoom(), 13), duration: 600 });
    else m.fitBounds([[Math.min(...xs), Math.min(...ys)], [Math.max(...xs), Math.max(...ys)]], { padding: 40, maxZoom: 14, duration: 600 });
  }
  function disegnaLegenda() {
    const L = $("legenda-cer"); if (!L) return;
    L.innerHTML = "";
    const voce = (i, t) => { const s = h("span"); s.append(i, t); L.appendChild(s); };
    voce(R.campione("punto", "#1e88e5"), "sedi");
    if (st.mappa && st.mappa.getSource("cer-cabine") && fcCabine().features.length) {
      voce(R.campione("cabina", "VERDE"), "cabine del comune: verde (bianco)");
      for (const k of ["GIALLO", "ARANCIONE", "ROSSO"]) voce(R.campione("cabina", k), R.NOMI[k]);
      voce(R.campione("cabina", "GRIGIO"), "senza dato");
    }
    if (st.confini) voce(R.campione("area"), "aree del GSE delle sedi (bordo spesso) e confinanti, a qualsiasi zoom");
    if (st.acceso) voce(R.campione("area"), "aree convenzionali del GSE (dal vivo, da zoom 10)");
  }
  // (20/11/2026, richiesta di Paolo: «come le altre pagine») mappa a sinistra con l'ortofoto (fonte scelta da sola nel
  // punto, menu per cambiarla, come Cabine primarie e Ortofoto), particelle catastali e contorni degli edifici (strati_gl.js),
  // frecce per spostare l'ortofoto (sposta_ortofoto.js), righello (righello.js), confini ISTAT; «Sposta» / «Aggiungi sedi».
  async function creaMappa() {
    if (!ml || !$("mappa-cer")) return;
    const I = (C && C.ITALIA) || [6.6, 35.4, 18.6, 47.1];
    const m = new ml.Map({ container: "mappa-cer", bounds: [[I[0], I[1]], [I[2], I[3]]], fitBoundsOptions: { padding: 10 }, maxZoom: 21, minZoom: 4,
      attributionControl: false, canvasContextAttributes: { preserveDrawingBuffer: true },
      style: { version: 8, sources: {}, layers: [{ id: "sfondo", type: "background", paint: { "background-color": colore("--carta", "#fff") } }] } });
    st.mappa = m;
    if (window.EUGENIO_LIMITI) window.EUGENIO_LIMITI.collega(m);
    m.addControl(new ml.NavigationControl({ showCompass: false }), "top-right");
    m.addControl(new ml.ScaleControl({ unit: "metric" }), "bottom-left");
    m.addControl(new ml.AttributionControl({ compact: true }), "bottom-right");
    await new Promise((ok) => m.on("load", ok));
    m.resize(); vediItalia(m, 0);
    $("mappa-cer").querySelectorAll(".maplibregl-compact-show").forEach((x) => x.classList.remove("maplibregl-compact-show"));
    document.addEventListener("eugenio:aspetto", () => m.setPaintProperty("sfondo", "background-color", colore("--carta", "#fff")));
    document.addEventListener("eugenio:ridimensiona", () => m.resize());
    if (window.pmtiles && !st.protocollo) { st.protocollo = new window.pmtiles.Protocol(); ml.addProtocol("pmtiles", st.protocollo.tile); }
    if (window.EUGENIO_RIGHELLO) st.righello = window.EUGENIO_RIGHELLO.aggiungi(m, { dove: $("posto-righello") });
    if (window.EUGENIO_SPOSTA && $("sposta-ortofoto")) st.sposta = window.EUGENIO_SPOSTA.crea($("sposta-ortofoto"), { pagina: "edificio-cer", suCambio: spostaTessere });
    if (C) { try { await C.aggiungi(m, { clic: false }); } catch { /* confini non disponibili */ } }
    m.addSource("cer-aree", { type: "geojson", data: vuota(), attribution: R.GSE.ATTRIBUZIONE_STRATO, promoteId: "COD_AC" });
    m.addLayer({ id: "cer-aree-fondo", type: "fill", source: "cer-aree", layout: { visibility: "none" }, paint: { "fill-color": fondoColore(), "fill-opacity": ["case", sopraArea, 0.38, 0.06] } });
    m.addLayer({ id: "cer-aree-linea", type: "line", source: "cer-aree", layout: { visibility: "none" }, paint: { "line-color": colore("--primario", "#e4572e"), "line-width": 2 } });
    // confini delle aree delle sedi: a qualsiasi zoom, bordo spesso l'area della sede, sottile le confinanti
    m.addSource("cer-confini", { type: "geojson", data: st.confini || vuota(), attribution: R.GSE.ATTRIBUZIONE_STRATO, promoteId: "COD_AC" });
    m.addLayer({ id: "cer-confini-fondo", type: "fill", source: "cer-confini", layout: { visibility: st.confini ? "visible" : "none" }, paint: {
      "fill-color": fondoColore(), "fill-opacity": ["case", sopraArea, 0.38, ["==", ["get", "_centrale"], true], 0.07, 0] } });
    m.addLayer({ id: "cer-confini-linea", type: "line", source: "cer-confini", layout: { visibility: st.confini ? "visible" : "none" }, paint: {
      "line-color": colore("--primario", "#e4572e"), "line-width": ["case", ["==", ["get", "_centrale"], true], 2.8, 1.4] } });
    // area sotto il mouse in azzurro chiaro trasparente, come in Cabine primarie (19/11/2026 sera)
    const togliSopra = () => {
      if (st.sopra) { try { m.setFeatureState({ source: st.sopra.src, id: st.sopra.id }, { sopra: false }); } catch { /* sparita */ } st.sopra = null; }
    };
    m.on("mousemove", (e) => {
      const ids = ["cer-confini-fondo", "cer-aree-fondo"].filter((id) => m.getLayer(id) && m.getLayoutProperty(id, "visibility") !== "none");
      const f = ids.length ? m.queryRenderedFeatures(e.point, { layers: ids })[0] : null;
      const nuovo = f && f.id !== undefined ? { src: f.source, id: f.id } : null;
      if ((nuovo && st.sopra && nuovo.src === st.sopra.src && nuovo.id === st.sopra.id) || (!nuovo && !st.sopra)) return;
      togliSopra();
      if (nuovo) { m.setFeatureState({ source: nuovo.src, id: nuovo.id }, { sopra: true }); st.sopra = nuovo; }
    });
    m.on("mouseout", togliSopra);
    m.addSource("cer-cabine", { type: "geojson", data: vuota(), attribution: "Cabine: © contributori OpenStreetMap (ODbL); e-distribuzione" });
    R.stratoCabine(m, "cer-cabine");
    m.addSource("cer-sedi", { type: "geojson", data: vuota() });
    m.addLayer({ id: "cer-sedi", type: "circle", source: "cer-sedi", paint: { "circle-radius": 7, "circle-color": "#1e88e5", "circle-stroke-color": "#ffffff", "circle-stroke-width": 2 } });
    R.suggerimento(m, () => ["cer-sedi", "cer-cabine-punti", "cer-confini-fondo"], (f) => {
      const p = f.properties || {};
      if (f.layer.id === "cer-confini-fondo") return { titolo: `Area convenzionale ${p.COD_AC}`, righe: [`Gestore: ${p.RAG_SOC || "–"}`,
        p._centrale === true ? "area di una sede" : "area confinante", "© GSE S.p.A., CC BY-NC-SA 3.0 IT"], cursore: false };
      if (f.layer.id === "cer-sedi") {
        const s = st.sedi.find((x) => x.k === +p.k);
        return s ? { titolo: s.nome, righe: [s.comune ? `Comune: ${s.comune}` : "", `Cabina: ${s.cabina || "–"}${ORIGINI[s.origine] ? ` (${ORIGINI[s.origine]})` : ""}`].filter(Boolean), cursore: false } : null;
      }
      let t = p.trasf; if (typeof t === "string") { try { t = JSON.parse(t); } catch { t = null; } }
      return { titolo: R.nomeCabina(p), righe: R.righeCabina({ ...p, trasf: t }), cursore: false };
    });
    if (window.EUGENIO_STRATI) {
      try { st.strati = await window.EUGENIO_STRATI.aggiungi(m, { caselle: $("caselle-strati"), legenda: $("legenda-strati"), sotto: () => primoSopra(m) }); }
      catch { /* strati non disponibili */ }
    }
    $("caselle-strati").addEventListener("change", aggiornaSposta);
    m.on("click", (e) => {
      if (st.modo === "scegli" && !(st.righello && st.righello.attivo && st.righello.attivo())) {
        const s = aggiungi({ nome: `Sede ${st.seq + 1}`, lat: e.lngLat.lat, lon: e.lngLat.lng });
        if (s) { tabella(); disegnaSedi(); cambiate(); messaggio("messaggio-sedi", `«${s.nome}» aggiunta: cerco l'area convenzionale del GSE e le cabine del comune.`); }
        return;
      }
      clicArea(e);
    });
    m.on("moveend", aggiornaStrato);
    document.addEventListener("eugenio:aspetto", () => {
      m.setPaintProperty("cer-aree-fondo", "fill-color", fondoColore());
      m.setPaintProperty("cer-confini-fondo", "fill-color", fondoColore());
      m.setPaintProperty("cer-confini-linea", "line-color", colore("--primario", "#e4572e"));
      m.setPaintProperty("cer-aree-linea", "line-color", colore("--primario", "#e4572e"));
    });
    await ortofoto(m);
    if (window.EUGENIO_ESPORTA) window.EUGENIO_ESPORTA.pulsanti($("scarica-mappa-cer"), m, opzioniImmagine, $("messaggio-mappa-cer"));
    disegnaSedi(); disegnaCabine(); inquadra();
  }
  function vediItalia(m, durata = 600) {
    if (!C || !C.ITALIA) return;
    const c = m.cameraForBounds([[C.ITALIA[0], C.ITALIA[1]], [C.ITALIA[2], C.ITALIA[3]]], { padding: 10 });
    if (c) m.easeTo({ ...c, zoom: Math.max(5, c.zoom), bearing: 0, pitch: 0, duration: durata });
  }
  // primo strato sopra le foto (particelle, edifici, confini, aree, cabine, sedi)
  function primoSopra(m) {
    const l = m.getStyle().layers.find((x) => !["sfondo", "contesto", "ortofoto"].includes(x.id));
    return l ? l.id : undefined;
  }
  // minimappa dell'Italia accanto al titolo: un clic su una regione porta lì la mappa
  async function vaiRegione(cod) {
    const b = C && C.riquadroRegione ? await C.riquadroRegione(cod) : null;
    if (E && E.seleziona) E.seleziona(cod);
    if (b && st.mappa) st.mappa.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 20, duration: 600 });
  }
  if (E) {
    E.suRegione = (cod) => vaiRegione(cod);
    E.suStessaRegione = (cod) => vaiRegione(cod);
    E.mappaPrincipale = { nazionale: () => st.mappa && vediItalia(st.mappa) };
  }
  // «Sposta» / «Aggiungi sedi» (come «Sposta» / «Scegli punti» in Cabine primarie)
  function modo(nuovo) {
    st.modo = nuovo;
    $("modo-sposta").setAttribute("aria-pressed", String(nuovo === "sposta"));
    $("modo-scegli").setAttribute("aria-pressed", String(nuovo === "scegli"));
    $("mappa-cer").classList.toggle("modo-scegli", nuovo === "scegli");
    if (nuovo === "scegli" && st.righello && st.righello.attivo && st.righello.attivo()) st.righello.spegni();
    messaggio("messaggio-mappa-cer", nuovo === "scegli" ? "Aggiungi sedi: ogni clic sulla mappa aggiunge una sede e cerca la sua area convenzionale." : "");
  }
  $("modo-sposta").addEventListener("click", () => modo("sposta"));
  $("modo-scegli").addEventListener("click", () => modo(st.modo === "scegli" ? "sposta" : "scegli"));

  // ---- ortofoto (come Cabine primarie e Ortofoto: fonti del server, migliore applicabile nel punto, scelta a mano dal menu)
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
    if (window.EUGENIO_ORTOFOTO_ANNI) window.EUGENIO_ORTOFOTO_ANNI.segui(m, "ortofoto", () => { const f = st.fonte; if (f && f.anni && citOrto(f) !== st.citazioneOrto) attribuzioneOrto(); });
    await elencoFonti();
    m.on("moveend", elencoFonti);
  }
  let giroFonti = 0;
  async function elencoFonti() {
    const m = st.mappa, mio = ++giroFonti, c = m.getCenter();
    let qui;
    try { qui = C && C.fontiNelPunto ? await C.fontiNelPunto(st.fonti, c.lng, c.lat) : st.fonti; } catch { qui = st.fonti; }
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
    const m = st.mappa, f = st.fonti.find((x) => x.id === id) || null;
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
  function citOrto(f) {
    return window.EUGENIO_ORTOFOTO_ANNI && st.mappa ? window.EUGENIO_ORTOFOTO_ANNI.citazione(f, st.mappa) : f.citazione;
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
    const src = st.mappa && st.mappa.getSource("ortofoto"), f = st.fonte;
    if (src && f && !f.pmtiles && src.setTiles) src.setTiles([tessere(f, true)]);
  }

  // ---- strato «Aree convenzionali (GSE)» (punto B)
  function visibilitaStrato() {
    const m = st.mappa;
    if (m) for (const id of ["cer-aree-fondo", "cer-aree-linea"]) if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", st.acceso ? "visible" : "none");
    st.etichette.forEach((x) => { x.getElement().hidden = !st.acceso; });
    const a = $("attribuzione-aree-gse"), vis = st.acceso || !!st.confini;
    a.hidden = !vis;
    a.textContent = vis ? `${R.GSE.ATTRIBUZIONE_STRATO}. Non entrano nelle immagini né nei file scaricati.` : "";
    disegnaLegenda();
  }
  function datiStrato(fc) {
    st.aree = fc;
    const m = st.mappa; if (m && m.getSource("cer-aree")) m.getSource("cer-aree").setData(fc || vuota());
    etichette(fc);
  }
  function aggiornaStrato() {
    clearTimeout(st.attesa);
    const m = st.mappa;
    if (!st.acceso || !m) return;
    if (m.getZoom() < R.GSE.ZOOM_MIN) {
      st.giro++; datiStrato(null);
      messaggio("messaggio-aree-gse", `Avvicinati per vedere le aree convenzionali (da zoom ${R.GSE.ZOOM_MIN}).`);
      return;
    }
    st.attesa = setTimeout(leggiStrato, ATTESA_MS);
  }
  async function leggiStrato() {
    const m = st.mappa, giro = ++st.giro, b = m.getBounds();
    messaggio("messaggio-aree-gse", "Leggo dal GSE le aree convenzionali della zona visibile…");
    try {
      const fc = await R.gse.areeNelRiquadro([b.getWest(), b.getSouth(), b.getEast(), b.getNorth()], m.getZoom());
      if (giro !== st.giro || !st.acceso) return;
      datiStrato(fc);
      const n = fc.features.length;
      messaggio("messaggio-aree-gse", fc.troppe ? `Troppe aree in questa zona: il GSE ne ha mandate solo ${n}. Avvicinati per vederle tutte.`
        : `${n} ${n === 1 ? "area convenzionale nella zona, letta" : "aree convenzionali nella zona, lette"} ora dal GSE: ${n === 1 ? "resta" : "restano"} solo a video, non ${n === 1 ? "viene salvata" : "vengono salvate"}.`, !!fc.troppe);
    } catch (e) {
      if (giro !== st.giro) return;
      messaggio("messaggio-aree-gse", `Aree convenzionali non lette: ${e.message}. Il servizio del GSE potrebbe essere lento o non raggiungibile: riprova più tardi.`, true);
    }
  }
  // punto interno per l'etichetta: centro della corda orizzontale più lunga alla quota del baricentro dell'anello esterno
  function puntoEtichetta(g) {
    const poligoni = g.type === "Polygon" ? [g.coordinates] : g.type === "MultiPolygon" ? g.coordinates : [];
    let anello = null, area = 0;
    for (const p of poligoni) {
      const r = p[0] || []; let a = 0;
      for (let i = 0; i < r.length - 1; i++) a += r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1];
      if (Math.abs(a) > area) { area = Math.abs(a); anello = r; }
    }
    if (!anello || anello.length < 4) return null;
    const ys = anello.map((q) => q[1]), y = (Math.min(...ys) + Math.max(...ys)) / 2, xs = [];
    for (let i = 0; i < anello.length - 1; i++) {
      const [x1, y1] = anello[i], [x2, y2] = anello[i + 1];
      if ((y1 <= y && y2 > y) || (y2 <= y && y1 > y)) xs.push(x1 + (y - y1) * (x2 - x1) / (y2 - y1));
    }
    xs.sort((a, b) => a - b);
    let best = null, largo = -1;
    for (let i = 0; i + 1 < xs.length; i += 2) if (xs[i + 1] - xs[i] > largo) { largo = xs[i + 1] - xs[i]; best = [(xs[i] + xs[i + 1]) / 2, y]; }
    return best;
  }
  function etichette(fc) {
    st.etichette.forEach((x) => x.remove()); st.etichette = [];
    if (!fc || !st.mappa || !ml) return;
    for (const f of fc.features) {
      const c = puntoEtichetta(f.geometry); if (!c) continue;
      const el = h("span", "etichetta-ac", f.properties.COD_AC); el.setAttribute("aria-hidden", "true"); el.hidden = !st.acceso;
      st.etichette.push(new ml.Marker({ element: el }).setLngLat(c).addTo(st.mappa));
    }
  }
  function clicArea(e) {
    const m = st.mappa;
    const ids = ["cer-confini-fondo", "cer-aree-fondo"].filter((id) => m.getLayer(id) && m.getLayoutProperty(id, "visibility") !== "none");
    if (!ids.length) return;
    const f = m.queryRenderedFeatures(e.point, { layers: ids })[0];
    if (!f) return;
    const p = f.properties || {};
    const box = h("div", "popup-ac");
    box.append(h("strong", null, `Area convenzionale ${p.COD_AC}`));
    box.append(h("div", null, `Gestore: ${p.RAG_SOC || "–"}`));
    box.append(h("div", null, `Data di consegna: ${R.gse.dataConsegna(p.COD_CONSEG) || "–"}`));
    const d = h("div"), a = h("a", null, "Mappa delle cabine primarie del GSE"); a.href = R.GSE.SCHEDA; a.target = "_blank"; a.rel = "noopener";
    d.appendChild(a); box.appendChild(d);
    box.append(h("div", "aiuto", "© GSE S.p.A., CC BY-NC-SA 3.0 IT"));
    if (st.popup) st.popup.remove();
    st.popup = new ml.Popup({ closeButton: true, maxWidth: "18rem" }).setLngLat(e.lngLat).setDOMContent(box).addTo(m);
  }
  $("strato-aree-gse").addEventListener("change", (e) => {
    st.acceso = e.target.checked;
    if (!st.acceso) { clearTimeout(st.attesa); st.giro++; datiStrato(null); if (st.popup) st.popup.remove(); messaggio("messaggio-aree-gse", ""); }
    visibilitaStrato();
    aggiornaStrato();
  });

  // ---- immagini: strato del GSE spento (punto C)
  function opzioniImmagine() {
    const m = st.mappa;
    const righe = [], f = st.fonte;
    if (f && !f.copia) return `«${f.nome}» è solo in consultazione dal vivo: per scaricare l'immagine scegli un'altra ortofoto.`;
    if (f) righe.push(`Ortofoto: ${citOrto(f)} – licenza ${f.licenza} (${f.scheda}).`);
    else if (st.contesto) righe.push(`Contesto: ${st.contesto.citazione} – licenza ${st.contesto.licenza} (${st.contesto.scheda}).`);
    if (f && st.sposta && st.sposta.riga()) righe.push(st.sposta.riga());
    if (st.strati) righe.push(...st.strati.righe());
    if (st.sedi.some(coordinate)) righe.push(`Sedi dell'utente: ${st.sedi.filter(coordinate).length}.`);
    if (fcCabine().features.length) righe.push(`Cabine primarie dei comuni delle sedi: livello peggiore dei trasformatori (bianco = verde, giallo, arancione, rosso). ${R.ATTR.osm}. ${R.ATTR.ed_breve}.`);
    righe.push(`${R.ATTR.confini}. Mappa: MapLibre GL JS (BSD-3).`);
    if (st.acceso || st.confini) righe.push("Le aree convenzionali del GSE non entrano nell'immagine (licenza CC BY-NC-SA 3.0 IT).");
    if (R.PROVA) righe.unshift("ATTENZIONE: DATI SINTETICI DI PROVA (?prova=1), non reali.");
    const accesi = ["cer-aree-fondo", "cer-aree-linea", "cer-confini-fondo", "cer-confini-linea"].filter((id) => m.getLayer(id) && m.getLayoutProperty(id, "visibility") !== "none");
    accesi.forEach((id) => m.setLayoutProperty(id, "visibility", "none"));
    st.etichette.forEach((x) => { x.getElement().hidden = true; });
    if (st.popup) st.popup.remove();
    return { titolo: "Comunità energetiche – sedi e cabine primarie", righe, nome: `comunita_energetiche_sedi_${new Date().toISOString().slice(0, 10)}`,
      dopo: () => { accesi.forEach((id) => { if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", "visible"); }); visibilitaStrato(); ricomponiConfini(); } };
  }

  // ================================================================== file scaricati: solo i codici (punto C)
  function datiFile() {
    const O = window.EUGENIO_CER_ORARI, esito = O && O.st && O.st.esito;
    if (!st.sedi.length && !esito) return "Niente da scaricare: aggiungi le sedi o carica i dati orari.";
    const proposta = (s) => (s.gse && s.gse.stato === "ok" ? [...s.gse.dentro, ...s.gse.vicine].map((a) => a.COD_AC).join(" ") : "");
    const sedi = st.sedi.map((s, i) => {
      const prop = proposta(s), conf = s.gse && s.gse.stato === "ok" && s.gse.dentro.length + s.gse.vicine.length > 1;
      return [i + 1, s.nome, coordinate(s) ? Math.round(s.lat * 1e6) / 1e6 : null, coordinate(s) ? Math.round(s.lon * 1e6) / 1e6 : null, s.comune, s.istat,
        s.cabina, ORIGINI[s.origine] || "", prop, prop ? `${R.GSE.NOTA_FILE}${conf ? ` (sede a meno di ${R.GSE.CONFINE_M} m dal confine tra due aree)` : ""}` : ""];
    });
    const sezioni = [];
    if (sedi.length) sezioni.push({ titolo: "Sedi e cabine primarie", intestazioni: ["N.", "Sede", "Latitudine", "Longitudine", "Comune", "ISTAT", "Cabina usata nel calcolo",
      "Origine della cabina", "Area convenzionale proposta (COD_AC)", "Nota"], righe: sedi });
    if (esito) {
      sezioni.push({ titolo: "Energia condivisa per cabina primaria", intestazioni: ["Cabina primaria", "Ore", "Prelievi (kWh)", "Immissioni (kWh)", "Energia condivisa (kWh)",
        "% delle immissioni", "% dei prelievi"], righe: esito.map((c) => [c.cabina, c.ore, Math.round(c.prelievo * 1000) / 1000, Math.round(c.immissione * 1000) / 1000,
        Math.round(c.condivisa * 1000) / 1000, c.quota_su_immissione === null ? null : Math.round(1000 * c.quota_su_immissione) / 10,
        c.quota_su_prelievo === null ? null : Math.round(1000 * c.quota_su_prelievo) / 10]) });
      sezioni.push({ titolo: "Energia per sede", intestazioni: ["Sede", "Cabina primaria", "Prelievi (kWh)", "Immissioni (kWh)", "Condivisa attribuita (kWh)"],
        righe: esito.flatMap((c) => c.sedi.map((s) => [s.sede, c.cabina, Math.round(s.prelievo * 1000) / 1000, Math.round(s.immissione * 1000) / 1000, Math.round(s.quota * 1000) / 1000])) });
    }
    const piede = [
      ...(R.PROVA ? ["ATTENZIONE: DATI SINTETICI DI PROVA (?prova=1), non reali."] : []),
      `Codici delle aree convenzionali: ${R.GSE.NOTA_FILE}. ${R.ATTR.gse_codici} (${R.GSE.SCHEDA}); nel file solo i codici, mai i confini delle aree (CC BY-NC-SA 3.0 IT).`,
      `${R.ATTR.ed}.`, `${R.ATTR.osm}.`,
      "Energia condivisa: minimo orario tra immissioni e prelievi delle sedi della stessa cabina primaria (D.Lgs. 199/2021, artt. 31 e 32; DM MASE 7/12/2023 n. 414); nessun prezzo né incentivo.",
      "Licenza: dati elaborati da EuGEnio CC BY 4.0.",
    ];
    const nome = `comunita_energetiche_${new Date().toISOString().slice(0, 10)}`;
    const doc = {
      titolo: "Comunità energetiche – sedi, cabine ed energia condivisa", sottotitolo: `${st.sedi.length} sedi${esito ? `, ${esito.length} cabine nel calcolo` : ""}`, nome_file: nome,
      sezioni: [
        { titolo: "Come leggere", blocchi: [
          ...(R.PROVA ? [{ tipo: "avvertenza", testo: "DATI SINTETICI DI PROVA (?prova=1): non reali." }] : []),
          { tipo: "avvertenza", livello: "info", testo: `Codici COD_AC: ${R.GSE.NOTA_FILE}. La cabina che conta per gli incentivi è quella dell'area che contiene il punto di connessione (POD).` },
          { tipo: "paragrafo", testo: "Energia condivisa dell'ora = minimo tra la somma delle immissioni e la somma dei prelievi delle sedi della stessa cabina primaria. Solo energia: nessun prezzo né incentivo." },
        ] },
        ...sezioni.map((s) => ({ titolo: s.titolo, blocchi: [{ tipo: "tabella", intestazioni: s.intestazioni, righe: s.righe.length ? s.righe : [s.intestazioni.map(() => null)] }] })),
      ],
      fonti: [
        { testo: "GSE S.p.A. – codici delle aree convenzionali (COD_AC), mappa interattiva delle cabine primarie", url: R.GSE.SCHEDA },
        { testo: "e-distribuzione S.p.A. – Aree critiche (dato mensile per trasformatore)", url: R.URL_ED },
        { testo: "© contributori OpenStreetMap – posizioni delle cabine primarie, ODbL 1.0", url: R.URL_OSM },
      ],
    };
    return { csv: [`${nome}.csv`, sezioni, piede], doc };
  }

  // ================================================================== avvio
  tabella(); disegnaLegenda();
  R.pulsantiDati($("scarica-cer"), datiFile, $("messaggio-scarica-cer"), ["csv", "xlsx", "ods", "pdf"]);
  creaMappa().catch((e) => messaggio("messaggio-mappa-cer", `Mappa non disponibile: ${e.message}`, true));
  window.EUGENIO_CER_SEDI = { st, aggiungi, cabinaDi, datiFile, opzioniImmagine, inquadra };
})();
