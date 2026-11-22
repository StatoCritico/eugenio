"use strict";
// Territorio › Edifici pubblici, ricerca per ente (22/11/2026, richiesta di Paolo; studio
// documenti/EDIFICI_PUBBLICI_RICERCA_ENTE_2026-11-22.md). Seconda scheda del passo 1 («Per ente», ?modo=enti):
//  - elenco degli enti da un file statico (indice.json → «enti»: /edifici3d/immobili_pa/enti_<anno>_<versione>.json, scritto
//    dalla fase 7) e autocompletamento tutto nel browser (combobox ARIA: frecce, Invio, Esc), con filtri per tipologia
//    (gruppo) e regione dove l'ente ha beni;
//  - fino a 8 enti insieme, ciascuno con un colore (tavolozza leggibile anche da chi non distingue bene i colori e diversa
//    dai colori della legenda generale), «Inquadra», «×» e «Togli tutti»;
//  - caselle ruolo (in proprietà, acceso; in uso = detenzione, spento) e natura (fabbricati acceso, terreni spento);
//  - mappa: fino allo zoom delle particelle (13) un pallino per particella (dalla rotta /api/immobili-pa/ente/{chiave}/punti,
//    raggruppati per gli enti con molti punti), poi i contorni delle particelle delle tessere con la proprietà «e»
//    (",<id><p|u>,…") nel colore dell'ente, retino nel colore dell'ente per i fabbricati; i livelli normali si attenuano;
//  - passo «Edifici degli enti selezionati»: per ogni ente una riga di totali (/api/immobili-pa/ente/{chiavi}, con più
//    enti anche i totali sui beni distinti) e una tabella ordinabile (tabella_ordinabile.js) con una riga per particella;
//    oltre 200 righe l'elenco parte per comune o è paginato dal server; clic su una riga → la mappa vola lì e si apre la
//    scheda;
//  - collegamento: modo, sel (chiavi degli enti, nell'ordine: i colori restano gli stessi), ruolo, natura, ordina;
//    tipologia e regione dei filtri sono controlli data-collegamento;
//  - immagine: legenda degli enti (colore scritto come testo) nella fascia sotto la mappa. Nessuna esportazione della
//    tabella (decisione «non scaricabile»).
// Nessun codice fiscale e nessun soggetto cedente: non sono né nel file degli enti né nelle risposte dell'API.
(function () {
  const $ = (id) => document.getElementById(id);
  const P = window.EUGENIO_PUBBLICI, T = window.EUGENIO_TABELLA_ORDINABILE, R = window.EUGENIO_RETINO;
  if (!P || !$("pannello-enti")) return;
  const MAX = 8, PER_PAGINA = 100, TUTTE = 200, GRUPPI_DA = 3000, PROPOSTE = 12;
  // Okabe–Ito senza arancio e porpora, più ocra e grigio-blu (studio § 4.3): nome scritto per l'immagine e i lettori.
  // Ordine scelto per distinguere bene i primi tre (blu, vermiglione, verde acqua: prova del 22/11/2026 sulla mappa)
  const TAVOLOZZA = [["#0072B2", "blu"], ["#D55E00", "vermiglione"], ["#009E73", "verde acqua"], ["#F0E442", "giallo"],
    ["#56B4E9", "celeste"], ["#222222", "nero"], ["#B8860B", "ocra"], ["#5C6B7A", "grigio-blu"]];
  const ATTENUATI = { "pa-terreni": ["fill-opacity", 0.35, 0.07], "pa-misti": ["fill-opacity", 0.25, 0.06],
    "pa-edifici": ["fill-opacity", 0.9, 0.14], "pa-linea": ["line-opacity", 1, 0.15], "pa-punti": ["circle-opacity", null, 0.12] };
  const num = (v, d = 0) => EUGENIO_NUMERI.formato(v, d, d, "–");
  const ha = (mq) => EUGENIO_NUMERI.formato((mq || 0) / 10000, 1, 1);
  const perc = (a, b) => (b ? `${EUGENIO_NUMERI.formato((100 * a) / b, 1, 1)} %` : "–");
  function h(tag, cls, t) { const e = document.createElement(tag); if (cls) e.className = cls; if (t !== undefined) e.textContent = t; return e; }
  function messaggio(t, errore = false) { const m = $("messaggio-enti"); m.textContent = t; m.classList.toggle("errore", errore); }

  const stato = { attivo: false, elenco: null, campi: null, regioni: [], gruppi: {}, scelti: [], ruoli: new Set(["proprieta"]),
    nature: new Set(["E"]), ordine: { chiave: null, verso: null }, insieme: null, livelli: false, pronto: false, giro: 0,
    proposte: [], attiva: -1 };

  // ------------------------------------------------------------------ nomi leggibili (i nomi MEF sono in maiuscolo)
  const PICCOLE = new Set(["di", "del", "della", "dello", "dei", "degli", "delle", "e", "ed", "per", "la", "il", "lo", "le", "gli",
    "in", "a", "al", "alla", "allo", "ai", "agli", "alle", "da", "dal", "dalla", "dai", "su", "sul", "sulla", "nel", "nella", "con", "tra", "fra"]);
  const SIGLE = new Set(["ausl", "usl", "asl", "asp", "acer", "ater", "aterp", "iacp", "arca", "inps", "inail", "anas", "crea", "cri", "enea",
    "aci", "irccs", "asst", "ats", "aou", "ao", "ulss", "asur", "ast", "arpa", "arpae", "erp", "apsp", "ipab", "pcm", "cnr", "infn",
    "ingv", "ispra", "istat", "agea", "enit", "consap", "sogei", "ssn", "ii", "iii", "iv", "ats", "aulss", "aslto", "cciaa"]);
  // «Universita'» → «Università» (nei CSV MEF gli accenti finali sono apostrofi)
  const accenti = (s) => (s || "").replace(/([aeiouAEIOU])'(?=[\s)\-,.]|$)/g, (_, v) => ({ a: "à", e: "è", i: "ì", o: "ò", u: "ù" })[v.toLowerCase()] || v);
  function nomeLeggibile(s) {
    if (!s || s !== s.toUpperCase()) return accenti(s);
    let t = accenti(s.toLowerCase());
    let primo = true;
    t = t.replace(/[\p{L}\p{N}]+/gu, (p, pos) => {
      const prima = t[pos - 1], dopo = t[pos + p.length];
      let out;
      if (prima === "(" && dopo === ")" && p.length <= 3) out = p.toUpperCase();          // sigla della provincia
      else if (SIGLE.has(p)) out = p.toUpperCase();
      else if (!primo && PICCOLE.has(p) && prima !== "'") out = p;
      else out = p[0].toUpperCase() + p.slice(1);
      primo = false;
      return out;
    });
    return t.replace(/\b(Dell|Dall|Nell|Sull|All|D|L)'(\p{L})/gu, (m, a, b) => `${a.toLowerCase()}'${b.toUpperCase()}`)
      .replace(/^(\p{L})/u, (m) => m.toUpperCase());
  }
  const norma = (s) => (s || "").normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/['’`´]/g, " ").toLowerCase()
    .replace(/[^a-z0-9]+/g, " ").trim();
  // sigle e nomi brevi che si scrivono spesso al posto del nome MEF
  const SINONIMI = { ausl: ["azienda usl", "ausl", "azienda unita sanitaria locale"], usl: ["usl", "azienda usl"],
    asl: ["asl", "azienda sanitaria locale"], acer: ["azienda casa emilia romagna", "acer"], ater: ["ater", "azienda territoriale"],
    iacp: ["iacp", "istituto autonomo case popolari", "istituto autonomo per le case popolari"],
    unibo: ["universita di bologna", "alma mater"], universita: ["universita", "universita degli studi", "alma mater", "politecnico"],
    ministero: ["ministero"], difesa: ["ministero della difesa", "difesa"] };

  // ------------------------------------------------------------------ elenco degli enti (file statico)
  function riga(i) {
    const r = stato.elenco[i], c = stato.campi;
    return { id: r[c.id], chiave: r[c.chiave], nome: r[c.nome], gruppo: r[c.gruppo], sede: r[c.sede], beni: r[c.beni],
      fabbricati: r[c.fabbricati], terreni: r[c.terreni], particelle: r[c.particelle], regioni: r[c.regioni] || [], i };
  }
  async function caricaElenco() {
    const info = P.stato.info;
    if (!info || !info.enti) {
      messaggio("La ricerca per ente non è ancora disponibile sul server: servono i dati preparati dal 22/11/2026.", true);
      $("cerca-ente").disabled = true;
      return false;
    }
    try {
      const r = await fetch(info.enti);
      if (!r.ok || !/json/.test(r.headers.get("Content-Type") || "")) throw new Error(String(r.status));
      const d = await r.json();
      stato.campi = Object.fromEntries(d.campi.map((k, i) => [k, i]));
      stato.elenco = d.enti; stato.regioni = d.regioni || []; stato.gruppi = d.gruppi || info.gruppi || {};
      stato.indice = d.enti.map((x) => { const n = norma(x[stato.campi.nome]); return { n, parole: n.split(" "), sede: norma(x[stato.campi.sede]) }; });
      stato.perChiave = new Map(d.enti.map((x, i) => [x[stato.campi.chiave], i]));
    } catch (e) {
      messaggio(`L'elenco degli enti non è arrivato (${e.message || e}).`, true);
      return false;
    }
    const tipo = $("tipo-ente"), reg = $("regione-ente");
    Object.entries(stato.gruppi).forEach(([k, n]) => tipo.appendChild(new Option(n, k)));
    stato.regioni.forEach((n, i) => reg.appendChild(new Option(nomeLeggibile(n.replace(/-/g, " - ")).replace(/ - /g, "-"), String(i))));
    $("conta-enti").textContent = `tra ${num(stato.elenco.length)} enti`;
    return true;
  }

  // ------------------------------------------------------------------ autocompletamento
  function cerca(testo) {
    const q = norma(testo), tipo = $("tipo-ente").value, reg = $("regione-ente").value;
    const scelti = new Set(stato.scelti.map((s) => s.chiave));
    const parole = q ? q.split(" ") : [];
    const out = [];
    for (let i = 0; i < stato.elenco.length; i++) {
      const r = stato.elenco[i], c = stato.campi;
      if (tipo && r[c.gruppo] !== tipo) continue;
      if (reg !== "" && !(r[c.regioni] || []).includes(+reg)) continue;
      const ix = stato.indice[i];
      let punti = 0, ok = true;
      for (const p of parole) {
        const esatta = ix.parole.includes(p), prefisso = esatta || ix.parole.some((w) => w.startsWith(p));
        const sin = (SINONIMI[p] || []).some((x) => ix.n.includes(x));
        const sede = ix.sede.split(" ").some((w) => w.startsWith(p));
        if (!(prefisso || sin || sede)) { ok = false; break; }
        punti += esatta ? 3 : prefisso ? 2 : sin ? 2 : 1;
      }
      if (!ok) continue;
      if (q && ix.n.startsWith(q)) punti += 2;
      if (q && (ix.n === q || ix.n === `comune di ${q}` || ix.n.startsWith(`comune di ${q} `))) punti += 4;
      out.push([punti, r[c.beni], i]);
    }
    out.sort((a, b) => b[0] - a[0] || b[1] - a[1] || a[2] - b[2]);
    return out.slice(0, PROPOSTE).map((x) => x[2]).filter((i) => !scelti.has(stato.elenco[i][stato.campi.chiave]));
  }
  function mostraProposte() {
    const lista = $("proposte-enti"), campo = $("cerca-ente");
    const testo = campo.value.trim();
    lista.textContent = "";
    stato.attiva = -1; campo.removeAttribute("aria-activedescendant");
    if (!stato.elenco || (!testo && !$("tipo-ente").value && $("regione-ente").value === "")) { chiudiProposte(); return; }
    stato.proposte = cerca(testo);
    if (!stato.proposte.length) {
      const li = h("li", "nessuna", "Nessun ente trovato: prova con meno parole, una sigla (AUSL, ACER, ATER…) o un altro filtro.");
      li.setAttribute("role", "option"); li.setAttribute("aria-disabled", "true");
      lista.appendChild(li);
    }
    stato.proposte.forEach((i, k) => {
      const e = riga(i), li = h("li");
      li.id = `proposta-ente-${k}`; li.setAttribute("role", "option"); li.setAttribute("aria-selected", "false");
      li.append(h("b", null, nomeLeggibile(e.nome)),
        h("span", "aiuto-breve", ` – ${stato.gruppi[e.gruppo] || "altri enti"}${e.sede ? ` – sede: ${e.sede}` : ""} – ${num(e.beni)} ${e.beni === 1 ? "bene" : "beni"}`));
      li.addEventListener("mousedown", (ev) => ev.preventDefault());       // il campo non perde il fuoco
      li.addEventListener("click", () => scegliProposta(k));
      lista.appendChild(li);
    });
    lista.hidden = false; campo.setAttribute("aria-expanded", "true");
  }
  function chiudiProposte() {
    $("proposte-enti").hidden = true; $("cerca-ente").setAttribute("aria-expanded", "false");
    $("cerca-ente").removeAttribute("aria-activedescendant"); stato.attiva = -1;
  }
  function evidenziaProposta(k) {
    const voci = [...$("proposte-enti").querySelectorAll("li[id]")];
    if (!voci.length) return;
    stato.attiva = (k + voci.length) % voci.length;
    voci.forEach((v, j) => v.setAttribute("aria-selected", j === stato.attiva ? "true" : "false"));
    const v = voci[stato.attiva];
    $("cerca-ente").setAttribute("aria-activedescendant", v.id);
    v.scrollIntoView({ block: "nearest" });
  }
  function scegliProposta(k) {
    const i = stato.proposte[k];
    if (i === undefined) return;
    $("cerca-ente").value = "";
    chiudiProposte();
    aggiungi(stato.elenco[i][stato.campi.chiave], { inquadra: true });
  }
  function tastiCombo(ev) {
    const aperta = !$("proposte-enti").hidden;
    if (ev.key === "ArrowDown") { ev.preventDefault(); if (!aperta) mostraProposte(); evidenziaProposta(stato.attiva + 1); }
    else if (ev.key === "ArrowUp") { ev.preventDefault(); if (!aperta) mostraProposte(); evidenziaProposta(stato.attiva - 1); }
    else if (ev.key === "Enter") {
      if (!aperta) return;
      ev.preventDefault();
      scegliProposta(stato.attiva >= 0 ? stato.attiva : 0);
    } else if (ev.key === "Escape") {
      if (aperta) { ev.preventDefault(); chiudiProposte(); } else if ($("cerca-ente").value) $("cerca-ente").value = "";
    }
  }

  // ------------------------------------------------------------------ selezione
  const slotLibero = () => { const usati = new Set(stato.scelti.map((s) => s.slot)); for (let k = 0; k < MAX; k++) if (!usati.has(k)) return k; return -1; };
  const parametri = () => {
    const u = new URLSearchParams();
    u.set("ruolo", [...stato.ruoli].join(",")); u.set("natura", [...stato.nature].join(","));
    return u;
  };
  function aggiungi(chiave, opz = {}) {
    if (!stato.elenco || !stato.perChiave.has(chiave)) { messaggio("Ente non trovato nell'elenco (forse i dati sono cambiati)."); return false; }
    if (stato.scelti.some((s) => s.chiave === chiave)) { messaggio("Questo ente è già tra quelli scelti."); return false; }
    if (stato.scelti.length >= MAX) { messaggio(`Al massimo ${MAX} enti insieme: togline uno per aggiungerne un altro.`, true); return false; }
    const e = riga(stato.perChiave.get(chiave)), slot = slotLibero();
    const s = { ...e, nome: nomeLeggibile(e.nome), slot, colore: TAVOLOZZA[slot][0], nomeColore: TAVOLOZZA[slot][1], punti: null,
      scheda: null, vista: { comune: null, pagina: 1 } };
    stato.scelti.push(s);
    messaggio("");
    if (!stato.attivo && opz.attiva !== false) modo(true);
    disegnaScelti();
    caricaPunti(s);
    if (!opz.senzaAggiorna) aggiornaTutto(opz.inquadra ? s : null);
    if (window.EUGENIO_COLLEGAMENTO) window.EUGENIO_COLLEGAMENTO.aggiorna();
    return true;
  }
  function togli(chiave) {
    const s = stato.scelti.find((x) => x.chiave === chiave);
    if (!s) return;
    stato.scelti = stato.scelti.filter((x) => x !== s);
    togliSorgente(s);
    disegnaScelti(); aggiornaTutto();
    if (window.EUGENIO_COLLEGAMENTO) window.EUGENIO_COLLEGAMENTO.aggiorna();
  }
  function togliTutti() {
    stato.scelti.forEach(togliSorgente);
    stato.scelti = [];
    disegnaScelti(); aggiornaTutto();
    if (window.EUGENIO_COLLEGAMENTO) window.EUGENIO_COLLEGAMENTO.aggiorna();
  }
  function inquadra(s) {
    const q = s.scheda && s.scheda.riquadro, m = P.stato.mappa;
    if (!q || !m) return;
    const largo = Math.abs(q[2] - q[0]) < 0.002 && Math.abs(q[3] - q[1]) < 0.002;
    if (largo) m.flyTo({ center: [(q[0] + q[2]) / 2, (q[1] + q[3]) / 2], zoom: 16, duration: 800 });
    else m.fitBounds([[q[0], q[1]], [q[2], q[3]]], { padding: 40, duration: 800, maxZoom: 16 });
  }
  function campione(colore) {
    const c = h("i", "campione-ente"); c.style.background = colore; c.setAttribute("aria-hidden", "true"); return c;
  }
  function disegnaScelti() {
    const ul = $("enti-scelti");
    ul.textContent = "";
    stato.scelti.forEach((s) => {
      const li = h("li", "ente-scelto");
      li.style.setProperty("--colore-ente", s.colore);
      const t = s.scheda ? s.scheda.totali : null;
      const testo = h("span", "ente-nome");
      testo.append(campione(s.colore), h("b", null, s.nome),
        h("span", "aiuto-breve", t ? ` ${num(t.n_beni)} ${t.n_beni === 1 ? "bene" : "beni"}, ${num(t.n_particelle)} ${t.n_particelle === 1 ? "particella" : "particelle"}` : ` ${num(s.beni)} beni dichiarati`),
        h("span", "solo-lettori", ` (colore ${s.nomeColore})`));
      const bi = h("button", "bottone secondario piccolo", "Inquadra"); bi.type = "button";
      bi.setAttribute("aria-label", `Inquadra ${s.nome}`);
      bi.addEventListener("click", () => inquadra(s));
      const bx = h("button", "togli-ente", "×"); bx.type = "button";
      bx.setAttribute("aria-label", `Togli ${s.nome}`); bx.title = `Togli ${s.nome}`;
      bx.addEventListener("click", () => togli(s.chiave));
      li.append(testo, bi, bx);
      ul.appendChild(li);
    });
    $("togli-enti").hidden = stato.scelti.length < 2;
    $("cerca-ente").disabled = !stato.elenco || stato.scelti.length >= MAX;
    $("cerca-ente").placeholder = stato.scelti.length >= MAX ? `${MAX} enti scelti: togline uno per aggiungerne altri` : "es. comune di cesena, ausl romagna, università bologna";
    legenda();
  }

  // ------------------------------------------------------------------ mappa: pallini (punti dell'ente) e contorni (tessere)
  const filtroRuolo = (r) => stato.ruoli.has(r === "U" ? "uso" : "proprieta");
  function geojson(s) {
    const per = new Map();
    for (const [lon, lat, n, natura, ruolo, ref] of s.punti || []) {
      if (!filtroRuolo(ruolo) || !stato.nature.has(natura)) continue;
      const x = per.get(ref);
      if (x) x.properties.n += n;
      else per.set(ref, { type: "Feature", properties: { n, ref, b: ref[0] === "b" ? 1 : 0 }, geometry: { type: "Point", coordinates: [lon, lat] } });
    }
    return { type: "FeatureCollection", features: [...per.values()] };
  }
  const idSorgente = (s) => `pe-${s.chiave}`;
  function sopraLivelli() { const m = P.stato.mappa; return ["cercato", "confini-comuni-clic", "confini-regioni-clic"].find((id) => m.getLayer(id)); }
  function sorgente(s) {
    const m = P.stato.mappa, id = idSorgente(s), dati = geojson(s), zoomP = (P.stato.info && P.stato.info.zoom_particelle) || 13;
    if (!m || !s.punti) return;
    const grande = dati.features.length > GRUPPI_DA;
    if (m.getSource(id)) {
      // il raggruppamento si decide alla creazione: se cambia (filtri) la sorgente si ricrea
      if (s.grande === grande) { m.getSource(id).setData(dati); return; }
      togliSorgente(s);
    }
    s.grande = grande;
    m.addSource(id, { type: "geojson", data: dati, ...(grande ? { cluster: true, clusterMaxZoom: 11, clusterRadius: 38, clusterProperties: { n: ["+", ["get", "n"]] } } : {}) });
    const raggio = ["interpolate", ["linear"], ["zoom"], 5, ["min", 7, ["+", 2.2, ["*", 0.5, ["sqrt", ["get", "n"]]]]],
      10, ["min", 11, ["+", 3, ["*", 0.9, ["sqrt", ["get", "n"]]]]], 13, ["min", 15, ["+", 4.5, ["*", 1.3, ["sqrt", ["get", "n"]]]]]];
    const tratto = "#fff";
    const sotto = sopraLivelli();
    if (grande) {
      m.addLayer({ id: `${id}-gruppi`, type: "circle", source: id, filter: ["has", "point_count"], maxzoom: zoomP,
        paint: { "circle-color": s.colore, "circle-opacity": 0.75, "circle-stroke-color": tratto, "circle-stroke-width": 1.5,
          "circle-radius": ["min", 26, ["+", 7, ["*", 1.6, ["sqrt", ["get", "point_count"]]]]] } }, sotto);
    }
    m.addLayer({ id: `${id}-pallini`, type: "circle", source: id, maxzoom: zoomP, filter: grande ? ["!", ["has", "point_count"]] : true,
      paint: { "circle-color": s.colore, "circle-opacity": 0.9, "circle-radius": raggio, "circle-stroke-color": tratto,
        "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 5, 0.6, 11, 1.2] } }, sotto);
    // dallo zoom delle particelle restano i soli beni senza particella (le particelle si vedono con i contorni)
    m.addLayer({ id: `${id}-senza`, type: "circle", source: id, minzoom: zoomP, filter: ["all", ["!", ["has", "point_count"]], ["==", ["get", "b"], 1]],
      paint: { "circle-color": s.colore, "circle-radius": 6, "circle-stroke-color": tratto, "circle-stroke-width": 2 } }, sotto);
    visibilita();
  }
  function togliSorgente(s) {
    const m = P.stato.mappa, id = idSorgente(s);
    if (!m) return;
    [`${id}-gruppi`, `${id}-pallini`, `${id}-senza`].forEach((l) => { if (m.getLayer(l)) m.removeLayer(l); });
    if (m.getSource(id)) m.removeSource(id);
  }
  const livelliPunti = () => stato.scelti.flatMap((s) => [`${idSorgente(s)}-gruppi`, `${idSorgente(s)}-pallini`, `${idSorgente(s)}-senza`]).filter((l) => P.stato.mappa.getLayer(l));
  async function caricaPunti(s) {
    try {
      const r = await fetch(`/api/immobili-pa/ente/${encodeURIComponent(s.chiave)}/punti`);
      if (!r.ok) throw new Error(r.status === 429 ? "troppe richieste: riprova tra poco" : r.status === 503 ? "dati non ancora sul server" : `errore ${r.status}`);
      const d = await r.json();
      if (d.disponibile === false) throw new Error("ricerca per ente non ancora disponibile sul server");
      if (!stato.scelti.includes(s)) return;
      s.punti = d.righe;
      sorgente(s);
    } catch (e) { messaggio(`I punti di ${s.nome} non sono arrivati (${e.message || e}).`, true); }
  }
  // contorni: tre livelli sulla sorgente «pa» delle tessere (strato «particelle»), filtrati con la proprietà «e»
  function gettoni(s) { const out = []; if (stato.ruoli.has("proprieta")) out.push(`,${s.id}p,`); if (stato.ruoli.has("uso")) out.push(`,${s.id}u,`); return out; }
  const E = ["coalesce", ["get", "e"], ""];
  const dell = (s) => ["any", ...gettoni(s).map((g) => ["in", g, E]), false];
  function aggiungiContorni() {
    const m = P.stato.mappa;
    if (stato.livelli || !m || !m.getSource("pa")) return;
    TAVOLOZZA.forEach(([c], k) => { if (R) R.aggiungi(m, { nome: `retino-ente-${k}`, colore: c, fondo: "rgba(255,255,255,0.35)" }); });
    const prima = m.getLayer("pa-scelta") ? "pa-scelta" : sopraLivelli();
    const no = ["boolean", false];
    m.addLayer({ id: "pa-enti-terreni", type: "fill", source: "pa", "source-layer": "particelle", filter: no, paint: { "fill-color": "#888", "fill-opacity": 0.42 } }, prima);
    m.addLayer({ id: "pa-enti-edifici", type: "fill", source: "pa", "source-layer": "particelle", filter: no,
      paint: R ? { "fill-pattern": "retino-ente-0", "fill-opacity": 0.95 } : { "fill-color": "#888", "fill-opacity": 0.5 } }, prima);
    m.addLayer({ id: "pa-enti-linea", type: "line", source: "pa", "source-layer": "particelle", filter: no,
      paint: { "line-color": "#888", "line-width": ["interpolate", ["linear"], ["zoom"], 13, 1.4, 18, 3.2] } }, prima);
    stato.livelli = true;
  }
  function aggiornaContorni() {
    const m = P.stato.mappa;
    if (!stato.livelli || !m) return;
    const scelti = stato.scelti.filter((s) => gettoni(s).length);
    const no = ["boolean", false];
    if (!scelti.length || !stato.nature.size) { ["pa-enti-terreni", "pa-enti-edifici", "pa-enti-linea"].forEach((l) => m.setFilter(l, no)); return; }
    const qualcuno = ["any", ...scelti.map(dell)];
    const colore = ["case", ...scelti.flatMap((s) => [dell(s), s.colore]), "#888"];
    const retino = ["case", ...scelti.flatMap((s) => [dell(s), `retino-ente-${s.slot}`]), `retino-ente-${scelti[0].slot}`];
    const conE = stato.nature.has("E"), conT = stato.nature.has("T");
    m.setFilter("pa-enti-terreni", conT ? ["all", ["in", ["get", "t"], ["literal", conE ? ["T"] : ["T", "M"]]], qualcuno] : no);
    m.setFilter("pa-enti-edifici", conE ? ["all", ["in", ["get", "t"], ["literal", ["E", "M"]]], qualcuno] : no);
    m.setFilter("pa-enti-linea", ["all", ["in", ["get", "t"], ["literal", [...(conE ? ["E", "M"] : []), ...(conT ? ["T", "M"] : [])]]], qualcuno]);
    m.setPaintProperty("pa-enti-terreni", "fill-color", colore);
    m.setPaintProperty("pa-enti-linea", "line-color", colore);
    if (R) m.setPaintProperty("pa-enti-edifici", "fill-pattern", retino); else m.setPaintProperty("pa-enti-edifici", "fill-color", colore);
  }
  function visibilita() {
    const m = P.stato.mappa;
    if (!m) return;
    const v = stato.attivo ? "visible" : "none";
    [...livelliPunti(), "pa-enti-terreni", "pa-enti-edifici", "pa-enti-linea"].forEach((l) => { if (m.getLayer(l)) m.setLayoutProperty(l, "visibility", v); });
    // livelli normali attenuati nella modalità per ente
    Object.entries(ATTENUATI).forEach(([l, [prop, pieno, basso]]) => {
      if (!m.getLayer(l)) return;
      if (pieno === null) {
        if (!stato.opacitaPunti) stato.opacitaPunti = m.getPaintProperty(l, prop);
        m.setPaintProperty(l, prop, stato.attivo ? basso : stato.opacitaPunti);
        m.setPaintProperty(l, "circle-stroke-opacity", stato.attivo ? basso : 1);
      } else m.setPaintProperty(l, prop, stato.attivo ? basso : pieno);
    });
  }
  // descrizione al passaggio del mouse e clic (chiamati da edifici_pubblici.js prima dei livelli normali)
  function sottoIlMouse(e) {
    const m = P.stato.mappa;
    if (!stato.attivo || !m) return null;
    const ls = [...livelliPunti(), "pa-enti-edifici", "pa-enti-terreni"].filter((l) => m.getLayer(l));
    if (!ls.length) return null;
    return m.queryRenderedFeatures([[e.point.x - 4, e.point.y - 4], [e.point.x + 4, e.point.y + 4]], { layers: ls })[0] || null;
  }
  function descrizione(f) {
    const p = f.properties || {};
    if (p.point_count) return `${num(p.point_count)} particelle, ${num(p.n)} beni: fai clic per avvicinarti`;
    const e = p.e || "";
    const chi = stato.scelti.filter((s) => (p.ref ? f.source === idSorgente(s) : gettoni(s).some((g) => e.includes(g))));
    const nomi = chi.map((s) => s.nome).join(" e ");
    return `${nomi}${p.n ? ` – ${num(p.n)} ${p.n === 1 ? "bene" : "beni"}` : ""}${p.tp ? ` – ${p.tp}` : ""}`;
  }
  function suMovimento(e) {
    const f = sottoIlMouse(e);
    if (!f) return false;
    const m = P.stato.mappa;
    m.getCanvas().style.cursor = "pointer";
    m.getCanvas().title = descrizione(f);
    return true;
  }
  function suClic(e) {
    const f = sottoIlMouse(e);
    if (!f) return false;
    const m = P.stato.mappa, p = f.properties || {};
    if (p.point_count) {
      const src = m.getSource(f.source);
      Promise.resolve(src.getClusterExpansionZoom(p.cluster_id)).then((z) => m.easeTo({ center: f.geometry.coordinates, zoom: Math.min(z, 13), duration: 600 })).catch(() => {});
      return true;
    }
    const ref = p.ref || p.r;
    if (!ref) return false;
    evidenziaRighe(String(ref));
    if (p.ref && m.getZoom() < 13) m.flyTo({ center: f.geometry.coordinates, zoom: 17, duration: 900 });
    P.apri(String(ref));
    return true;
  }

  // ------------------------------------------------------------------ dati dell'API: totali ed elenchi
  async function api(u) {
    const r = await fetch(u);
    if (!r.ok) {
      let dett = "";
      try { dett = (await r.json()).detail || ""; } catch { /* niente */ }
      throw new Error(r.status === 429 ? "troppe richieste: riprova tra poco" : r.status === 503 ? (dett || "dati non ancora sul server") : r.status === 404 ? "ente non trovato" : dett || `errore ${r.status}`);
    }
    const d = await r.json();
    if (d.disponibile === false) throw new Error("ricerca per ente non ancora disponibile sul server");
    return d;
  }
  async function aggiornaTutto(daInquadrare = null) {
    const giro = ++stato.giro;
    stato.scelti.forEach((s) => { if (s.punti) sorgente(s); });
    aggiornaContorni();
    const box = $("elenco-enti");
    if (!stato.scelti.length) {
      box.textContent = "";
      box.appendChild(h("p", "aiuto", "Nessun ente scelto: cercane uno nel passo 1."));
      stato.insieme = null; legenda(); return;
    }
    if (!stato.ruoli.size || !stato.nature.size) {
      box.textContent = "";
      box.appendChild(h("p", "messaggio errore", !stato.ruoli.size ? "Scegli almeno uno tra «in proprietà» e «in uso»." : "Scegli almeno uno tra fabbricati e terreni."));
      return;
    }
    $("messaggio-elenco").textContent = "Carico i totali…";
    let d;
    try { d = await api(`/api/immobili-pa/ente/${stato.scelti.map((s) => s.chiave).join(",")}?${parametri()}`); } catch (e) {
      if (giro === stato.giro) $("messaggio-elenco").textContent = `I totali non sono arrivati (${e.message || e}).`;
      return;
    }
    if (giro !== stato.giro) return;
    $("messaggio-elenco").textContent = "";
    const per = new Map(d.enti.map((x) => [x.chiave, x]));
    stato.scelti.forEach((s) => { s.scheda = per.get(s.chiave) || null; });
    stato.insieme = d.insieme || null;
    disegnaScelti();
    if (daInquadrare && daInquadrare.scheda) inquadra(daInquadrare);
    box.textContent = "";
    for (const s of stato.scelti) {
      const sez = h("section", "gruppo-ente");
      sez.dataset.chiave = s.chiave;
      sez.style.setProperty("--colore-ente", s.colore);
      box.appendChild(sez);
      disegnaEnte(s, sez);
    }
    if (stato.insieme) {
      const t = stato.insieme, p = h("p", "totali-insieme");
      p.append(h("b", null, "Insieme: "), riassunto(t), h("span", "aiuto-breve", " (beni dichiarati da più enti scelti contati una volta)"));
      box.appendChild(p);
    }
    legenda();
  }
  function riassunto(t) {
    const pezzi = [`${num(t.n_beni)} ${t.n_beni === 1 ? "bene" : "beni"}`, `${num(t.n_fabbricati)} fabbricati`, `${num(t.n_terreni)} terreni`,
      `${num(t.n_particelle)} particelle`];
    if (t.n_fabbricati) pezzi.push(`superficie dichiarata dei fabbricati ${num(t.sup_fabbricati_mq)} m²`);
    if (t.n_terreni) pezzi.push(`dei terreni ${ha(t.sup_terreni_mq)} ha`);
    pezzi.push(`non utilizzati o inutilizzabili ${perc((t.n_non_utilizzati || 0) + (t.n_inutilizzabili || 0), t.n_beni)}`,
      `vincolati ${perc(t.n_vincolati, t.n_beni)}`, `in uso (non in proprietà) ${perc(t.n_detenzione, t.n_beni)}`,
      `${num(t.n_comuni)} ${t.n_comuni === 1 ? "comune" : "comuni"}`);
    return pezzi.join(" · ");
  }
  const COLONNE = [
    { chiave: "comune", titolo: "Comune", formato: (v, r) => (v ? `${nomeLeggibile(v)}${r.provincia && r.provincia.length <= 3 ? ` (${r.provincia})` : ""}` : "") },
    { chiave: "regione", titolo: "Regione", soloPiuRegioni: true, formato: (v) => (v ? nomeLeggibile(v) : "") },
    { chiave: "indirizzo", titolo: "Indirizzo", formato: (v, r) => v || (r.ref && r.ref[0] !== "b" ? "" : "") },
    { chiave: "tipologie", titolo: "Tipologia" },
    { chiave: "n_beni", titolo: "Unità", tipo: "numero", formato: (v) => num(v) },
    { chiave: "sup_mq", titolo: "Superficie dichiarata (m²)", tipo: "numero", formato: (v) => (v ? num(v) : "") },
    { chiave: "area_m2", titolo: "Area del lotto (m²)", tipo: "numero", formato: (v) => (v ? num(v) : ""), classe: "solo-largo" },
    { chiave: "epoca", titolo: "Epoca", classe: "solo-largo" },
    { chiave: "utilizzo", titolo: "Utilizzo", classe: "solo-largo" },
    { chiave: "titolo", titolo: "Titolo", classe: "solo-largo", formato: (v, r) => (v || (r.ruoli === "U" ? "in uso" : "")) },
  ];
  const COLONNE_COMUNI = [
    { chiave: "comune", titolo: "Comune", formato: (v, r) => `${nomeLeggibile(v) || r.comune_cod || ""}${r.provincia && r.provincia.length <= 3 ? ` (${r.provincia})` : ""}` },
    { chiave: "regione", titolo: "Regione", soloPiuRegioni: true, formato: (v) => (v ? nomeLeggibile(v) : "") },
    { chiave: "n_particelle", titolo: "Particelle", tipo: "numero", formato: (v) => num(v) },
    { chiave: "n_beni", titolo: "Unità", tipo: "numero", formato: (v) => num(v) },
    { chiave: "sup_mq", titolo: "Superficie dichiarata (m²)", tipo: "numero", formato: (v) => (v ? num(v) : "") },
  ];
  function colonne(s, quali) { return quali.filter((c) => !c.soloPiuRegioni || (s.scheda && s.scheda.totali_dichiarati.n_regioni > 1)); }
  function disegnaEnte(s, sez) {
    const e = s.scheda;
    const tit = h("h3", "titolo-ente");
    tit.append(campione(s.colore), h("span", null, s.nome), h("span", "solo-lettori", ` (colore ${s.nomeColore})`));
    sez.appendChild(tit);
    if (!e) { sez.appendChild(h("p", "messaggio errore", "Dati dell'ente non arrivati.")); return; }
    const sede = [e.sede.comune && nomeLeggibile(e.sede.comune), e.sede.regione && nomeLeggibile(e.sede.regione)].filter(Boolean).join(", ");
    sez.appendChild(h("p", "aiuto", `${e.tipologia_amm ? nomeLeggibile(e.tipologia_amm) : ""}${sede ? ` – sede: ${sede}` : ""}. Dichiarati in tutto: ${num(e.totali_dichiarati.n_beni)} beni.`));
    const t = e.totali, p = h("p", "totali-ente");
    p.append(h("b", null, "Con le scelte del passo 1: "), riassunto(t));
    sez.appendChild(p);
    if (!t.n_beni) { sez.appendChild(h("p", "aiuto", "Nessun bene con queste scelte (prova ad accendere «in uso» o i terreni).")); return; }
    const righe = e.comuni.reduce((a, c) => a + (c.n_righe || 0), 0);
    const corpo = h("div", "corpo-ente");
    sez.appendChild(corpo);
    if (s.vista.comune) return elencoPaginato(s, corpo, s.vista.comune);
    if (righe <= TUTTE) return elencoIntero(s, corpo);
    if (e.comuni.length > 1) return elencoComuni(s, corpo);
    return elencoPaginato(s, corpo, null);
  }
  function tabellaIn(contenitore, t) {
    const sc = h("div", "tabella-scorre tabella-enti");
    sc.appendChild(t.elemento);
    contenitore.appendChild(sc);
    return sc;
  }
  function suRiga(s) {
    return (r) => {
      evidenziaRighe(r.ref);
      const m = P.stato.mappa;
      if (r.lon !== undefined && r.lat !== undefined && m) m.flyTo({ center: [r.lon, r.lat], zoom: Math.max(m.getZoom(), r.ref[0] === "b" ? 16.5 : 17), duration: 900 });
      P.apri(r.ref, r.lon === undefined);
      const sch = $("passo-scheda");
      if (sch && matchMedia("(max-width: 860px)").matches) sch.scrollIntoView({ behavior: "smooth", block: "start" });
    };
  }
  function evidenziaRighe(ref) {
    stato.tabelle = (stato.tabelle || []).filter((t) => t.elemento.isConnected);
    stato.tabelle.forEach((t) => t.evidenzia((r) => r.ref === ref));
  }
  function registra(t) { stato.tabelle = [...(stato.tabelle || []).filter((x) => x.elemento.isConnected), t]; return t; }
  function suOrdinaGlobale(chiave, verso) {
    stato.ordine = { chiave, verso };
    if (window.EUGENIO_COLLEGAMENTO) window.EUGENIO_COLLEGAMENTO.aggiorna();
  }
  async function elencoIntero(s, corpo) {
    corpo.appendChild(h("p", "aiuto", "Carico l'elenco…"));
    let d;
    try { d = await api(`/api/immobili-pa/ente/${s.chiave}/beni?${parametri()}&per_pagina=${TUTTE}`); } catch (e) {
      corpo.textContent = ""; corpo.appendChild(h("p", "messaggio errore", `L'elenco non è arrivato (${e.message || e}).`)); return;
    }
    corpo.textContent = "";
    const t = registra(T.crea({ colonne: colonne(s, COLONNE), righe: d.righe, ordine: stato.ordine, suRiga: suRiga(s),
      didascalia: `Particelle e beni di ${s.nome}`, didascaliaNascosta: true, dopoOrdina: suOrdinaGlobale,
      piede: [{ testo: `Totale: ${num(d.totale)} ${d.totale === 1 ? "riga" : "righe"}, ${num(s.scheda.totali.n_beni)} beni`, colonne: colonne(s, COLONNE).length, intestazione: true }] }));
    tabellaIn(corpo, t);
    if (P.stato.selezione) t.evidenzia((r) => r.ref === P.stato.selezione);
  }
  function elencoComuni(s, corpo) {
    const e = s.scheda;
    corpo.appendChild(h("p", "aiuto", `${num(e.comuni.length)} comuni: fai clic su un comune per vedere le sue particelle (pagine da ${PER_PAGINA} righe).`));
    const ordine = COLONNE_COMUNI.some((c) => c.chiave === stato.ordine.chiave) ? stato.ordine : { chiave: "n_beni", verso: "desc" };
    const t = registra(T.crea({ colonne: colonne(s, COLONNE_COMUNI), righe: e.comuni, ordine, didascalia: `Comuni con beni di ${s.nome}`,
      didascaliaNascosta: true, suRiga: (r) => { s.vista = { comune: r.comune_cod, nomeComune: nomeLeggibile(r.comune), pagina: 1 }; ridisegnaEnte(s); },
      piede: [{ testo: `Totale: ${num(e.totali.n_beni)} beni in ${num(e.comuni.length)} comuni`, colonne: colonne(s, COLONNE_COMUNI).length, intestazione: true }] }));
    tabellaIn(corpo, t);
  }
  function ridisegnaEnte(s) {
    const sez = document.querySelector(`.gruppo-ente[data-chiave="${s.chiave}"]`);
    if (!sez) return;
    sez.textContent = "";
    disegnaEnte(s, sez);
  }
  async function elencoPaginato(s, corpo, comune) {
    const testa = h("div", "riga-campi testa-elenco");
    if (comune) {
      const indietro = h("button", "bottone secondario piccolo", "‹ Tutti i comuni"); indietro.type = "button";
      indietro.addEventListener("click", () => { s.vista = { comune: null, pagina: 1 }; ridisegnaEnte(s); });
      testa.append(indietro, h("b", null, ` ${s.vista.nomeComune || comune}`));
    }
    corpo.appendChild(testa);
    const zona = h("div");
    corpo.appendChild(zona);
    const nav = h("nav", "paginazione"); nav.setAttribute("aria-label", `Pagine dell'elenco di ${s.nome}`);
    corpo.appendChild(nav);
    let t = null;
    async function carica(pagina) {
      const o = stato.ordine.chiave && COLONNE.some((c) => c.chiave === stato.ordine.chiave) ? stato.ordine : { chiave: null };
      const u = `/api/immobili-pa/ente/${s.chiave}/beni?${parametri()}&pagina=${pagina}&per_pagina=${PER_PAGINA}${comune ? `&comune=${comune}` : ""}${o.chiave ? `&ordina=${o.chiave}&verso=${o.verso}` : ""}`;
      nav.textContent = "Carico…";
      let d;
      try { d = await api(u); } catch (e) { nav.textContent = `L'elenco non è arrivato (${e.message || e}).`; return; }
      s.vista.pagina = d.pagina;
      if (!t) {
        t = registra(T.crea({ colonne: colonne(s, COLONNE), righe: d.righe, ordine: o, suRiga: suRiga(s), didascalia: `Particelle e beni di ${s.nome}`,
          didascaliaNascosta: true, suOrdina: async (chiave, verso) => { suOrdinaGlobale(chiave, verso); await carica(1); } }));
        tabellaIn(zona, t);
      } else t.imposta(d.righe);
      t.piede([{ testo: `${num(d.totale)} righe${comune ? " nel comune" : ""} – pagina ${num(d.pagina)} di ${num(d.pagine)}`, colonne: colonne(s, COLONNE).length, intestazione: true }]);
      if (P.stato.selezione) t.evidenzia((r) => r.ref === P.stato.selezione);
      nav.textContent = "";
      const b = (testo, p, dis) => { const x = h("button", "bottone secondario piccolo", testo); x.type = "button"; x.disabled = dis; x.addEventListener("click", () => carica(p)); return x; };
      nav.append(b("‹ Precedenti", d.pagina - 1, d.pagina <= 1), h("span", null, ` pagina ${num(d.pagina)} di ${num(d.pagine)} `), b("Successive ›", d.pagina + 1, d.pagina >= d.pagine));
    }
    await carica(s.vista.pagina || 1);
  }

  // ------------------------------------------------------------------ legenda sotto la mappa e immagine
  function legenda() {
    const l = $("legenda-enti"), base = $("legenda-pubblici");
    if (!l) return;
    l.textContent = "";
    l.hidden = !stato.attivo;
    if (base) base.classList.toggle("attenuata", stato.attivo);
    if (!stato.attivo) return;
    if (!stato.scelti.length) { l.appendChild(h("span", null, "Scegli un ente a destra: i suoi immobili compariranno qui nel suo colore.")); return; }
    stato.scelti.forEach((s) => { const x = h("span"); x.append(campione(s.colore), `${s.nome}`); l.appendChild(x); });
    l.appendChild(h("span", "aiuto-breve", "Pallini: particelle (da lontano, più grandi con più beni); da vicino contorni e righe oblique nel colore dell'ente. Gli altri immobili pubblici sono attenuati."));
  }
  function righeImmagine() {
    if (!stato.attivo || !stato.scelti.length) return [];
    const out = stato.scelti.map((s) => {
      const t = s.scheda && s.scheda.totali;
      return `${s.nomeColore}: ${s.nome}${t ? ` – ${num(t.n_beni)} beni, ${num(t.n_particelle)} particelle` : ""}.`;
    });
    out.push(`Beni ${[...stato.ruoli].map((r) => (r === "uso" ? "in uso" : "in proprietà")).join(" e ")}; ${[...stato.nature].map((n) => (n === "E" ? "fabbricati" : "terreni")).join(" e ")}.`);
    out.push("Righe oblique colorate: fabbricati dell'ente; pallini: particelle (da lontano); gli altri immobili pubblici sono attenuati.");
    return out;
  }

  // ------------------------------------------------------------------ modo (schede del passo 1) e numeri dei passi
  function modo(enti, opz = {}) {
    stato.attivo = !!enti;
    const a = $("scheda-immobile"), b = $("scheda-enti");
    a.setAttribute("aria-selected", String(!enti)); b.setAttribute("aria-selected", String(enti));
    a.tabIndex = enti ? -1 : 0; b.tabIndex = enti ? 0 : -1;
    $("pannello-immobile").hidden = enti; $("pannello-enti").hidden = !enti;
    $("passo-elenco-enti").hidden = !enti;
    document.querySelector(".pagina-pubblici")?.classList.toggle("modo-enti", enti);
    let n = 1;
    document.querySelectorAll(".pagina-pubblici .pannello > .passo").forEach((p) => { if (!p.hidden) { const s = p.querySelector("h2 .n"); if (s) s.textContent = String(n++); } });
    if (enti) aggiungiContorni();
    aggiornaContorni();
    visibilita();
    legenda();
    if (opz.fuoco) (enti ? $("cerca-ente") : $("testo-pubblici")).focus();
    if (window.EUGENIO_COLLEGAMENTO && !opz.silenzioso) window.EUGENIO_COLLEGAMENTO.aggiorna();
  }
  function schede() {
    const lista = [$("scheda-immobile"), $("scheda-enti")];
    lista.forEach((t, k) => {
      t.addEventListener("click", () => modo(k === 1));
      t.addEventListener("keydown", (ev) => {
        let j = null;
        if (ev.key === "ArrowRight" || ev.key === "ArrowLeft") j = 1 - k;
        else if (ev.key === "Home") j = 0; else if (ev.key === "End") j = 1;
        if (j === null) return;
        ev.preventDefault(); lista[j].focus(); modo(j === 1);
      });
    });
  }

  // ------------------------------------------------------------------ avvio
  function caselle(box, insieme) {
    box.addEventListener("change", () => {
      insieme.clear();
      box.querySelectorAll("input:checked").forEach((x) => insieme.add(x.value));
      aggiornaTutto();
    });
  }
  schede();
  caselle($("ruolo-enti"), stato.ruoli);
  caselle($("natura-enti"), stato.nature);
  const campo = $("cerca-ente");
  let attesa = 0;
  campo.addEventListener("input", () => { clearTimeout(attesa); attesa = setTimeout(mostraProposte, 120); });
  campo.addEventListener("focus", () => { if (campo.value.trim()) mostraProposte(); });
  campo.addEventListener("keydown", tastiCombo);
  campo.addEventListener("blur", () => setTimeout(chiudiProposte, 150));
  $("tipo-ente").addEventListener("change", () => { if (document.activeElement !== campo) campo.focus(); mostraProposte(); });
  $("regione-ente").addEventListener("change", () => { if (document.activeElement !== campo) campo.focus(); mostraProposte(); });
  $("togli-enti").addEventListener("click", togliTutti);
  (P.pronto || Promise.resolve()).then(async () => {
    await caricaElenco();
    stato.pronto = true;
    if (stato.attivo) { aggiungiContorni(); aggiornaContorni(); visibilita(); }
    document.addEventListener("eugenio:aspetto", () => stato.scelti.forEach((s) => s.punti && sorgente(s)));
  });

  // collegamento: modo, enti scelti (chiavi nell'ordine), ruolo, natura e ordinamento; tipologia e regione dei filtri sono
  // controlli data-collegamento del pannello
  if (window.EUGENIO_COLLEGAMENTO) window.EUGENIO_COLLEGAMENTO.registra({
    regione: false,
    chiavi: ["modo", "sel", "ruolo", "natura", "ordina"],
    principali: ["modo", "sel"],
    pronto: () => stato.pronto,
    leggi() {
      if (!stato.pronto) return null;
      const r = [...stato.ruoli].sort().join(","), n = [...stato.nature].sort().join(",");
      return { modo: stato.attivo ? "enti" : null, sel: stato.scelti.map((s) => s.chiave).join(",") || null,
        ruolo: r === "proprieta" ? null : r || "nessuno", natura: n === "E" ? null : n || "nessuna",
        ordina: stato.ordine.chiave ? `${stato.ordine.chiave}:${stato.ordine.verso}` : null };
    },
    async applica(p) {
      const metti = (box, v, insieme) => {
        if (v === null) return;
        const si = new Set(v.split(","));
        insieme.clear();
        box.querySelectorAll("input").forEach((x) => { x.checked = si.has(x.value); if (x.checked) insieme.add(x.value); });
      };
      metti($("ruolo-enti"), p.get("ruolo"), stato.ruoli);
      metti($("natura-enti"), p.get("natura"), stato.nature);
      const o = (p.get("ordina") || "").match(/^([a-z_0-9]+):(asc|desc)$/);
      if (o) stato.ordine = { chiave: o[1], verso: o[2] };
      if (p.get("modo") === "enti") modo(true, { silenzioso: true });
      const sel = (p.get("sel") || "").split(",").filter((k) => /^[0-9a-f]{10}$/.test(k)).slice(0, MAX);
      sel.forEach((k) => aggiungi(k, { senzaAggiorna: true, attiva: p.get("modo") === "enti" }));
      if (sel.length || p.get("modo") === "enti") await aggiornaTutto();
    },
  });

  window.EUGENIO_PUBBLICI_ENTI = { stato, aggiungi, togli, togliTutti, modo, cerca, nomeLeggibile, suClic, suMovimento, righeImmagine,
    inquadra, TAVOLOZZA };
})();
