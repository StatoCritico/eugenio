"use strict";
// Territorio › Edifici pubblici (17/11/2026, richiesta di Paolo). Mappa MapLibre con gli immobili delle Pubbliche
// Amministrazioni (censimento MEF «Patrimonio della PA», dati al 31/12/2023, CC BY 4.0) disegnati con la loro particella
// catastale (Agenzia delle Entrate, CC BY 4.0), sopra l'ortofoto. Dati preparati dalla fase 7 (`immobili-pa`,
// `immobili-pa-sito`):
//  - tessere vettoriali statiche /edifici3d/immobili_pa/immobili_pa_<anno>_<versione>.pmtiles (strati «particelle», dallo zoom 13, e
//    «punti»: un punto per particella fino allo zoom 12 più i beni senza particella, `s` = 1), descritte da indice.json;
//  - ricerca e schede dall'API: /api/immobili-pa/cerca, /particella/{ref}, /bene/{id} (servizio/immobili_pa.py).
// Proprietà delle tessere: r (riferimento AdE o «b<id bene>»), t (E edifici, T terreni, M entrambi), n (beni), g (gruppo di
// enti, codici di indice.json «gruppi»: C Comuni, I Unioni di Comuni e Comunità montane, P Province e Città metropolitane,
// R, S, U, E, M, N, A; le caselle si costruiscono da lì), a (primo ente), tp (tipologie), s (1 = bene senza particella).
// Livelli accendibili: Edifici (E e M, retinati come in Modelli 3D), Terreni (T e M), Beni senza particella; filtro per
// gruppo di enti; ortofoto con scelta automatica della fonte migliore (come Ortofoto e Modelli 3D) o a mano; strati
// comuni (particelle catastali di tutti, contorni degli edifici: strati_gl.js). Ricerca dei luoghi con cerca_luogo.js.
// Indirizzo: ?lat=&lon=&z= per aprire su un punto, ?ref=<particella> o ?bene=<id> per aprire la scheda.
// Ricerca per ente (22/11/2026): seconda scheda del passo 1, in pubblici_enti.js (?modo=enti&sel=<chiavi>); qui solo gli
// agganci: clic e passaggio del mouse (prima i livelli degli enti), righe dell'immagine, «Mostra tutti i beni di questo
// ente» nella scheda, EUGENIO_PUBBLICI.pronto (promessa: mappa, livelli e indice pronti).
(function () {
  const $ = (id) => document.getElementById(id);
  const box = $("mappa-pubblici");
  if (!box || !window.maplibregl) return;
  const C = window.EUGENIO_CONFINI, R = window.EUGENIO_RETINO;
  const q = new URLSearchParams(location.search);
  const P0 = window.EUGENIO_CERCA && window.EUGENIO_CERCA.PARTENZA;
  const conPunto = q.get("lon") && q.get("lat") && Number.isFinite(+q.get("lon")) && Number.isFinite(+q.get("lat"));
  const CONTESTO = "s2cloudless2016";
  const COLORI = { E: R ? R.COLORE : "#c2185b", T: "#2e7d32", M: "#6a1b9a", S: "#ef6c00" };
  // usati solo se indice.json non ha «gruppi»; dal 22/11/2026 c'è I (Unioni di Comuni e Comunità montane, gruppo proprio)
  const GRUPPI_PREDEFINITI = { C: "Comuni", I: "Unioni di Comuni e Comunità montane", P: "Province e Città metropolitane", R: "Regioni", S: "Sanità (ASL e ospedali)",
    U: "Università", E: "Edilizia residenziale pubblica", M: "Stato: ministeri e organi costituzionali", N: "Previdenza (INPS, INAIL…)", A: "Altri enti" };
  const stato = { mappa: null, info: null, fonti: [], scelta: null, manuale: false, contesto: null, confini: null, strati: null,
    tipi: new Set(["E", "T", "S"]), gruppi: new Set(Object.keys(GRUPPI_PREDEFINITI)), selezione: null, regione: null, cercato: null };
  let segnalaPronto;
  const pronto = new Promise((ok) => { segnalaPronto = ok; });      // mappa, livelli e indice pronti (per pubblici_enti.js)
  const ENTI = () => window.EUGENIO_PUBBLICI_ENTI;                 // ricerca per ente (pubblici_enti.js, 22/11/2026)
  const colore = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || "#888";
  function h(tag, cls, t) { const e = document.createElement(tag); if (cls) e.className = cls; if (t !== undefined) e.textContent = t; return e; }
  function messaggio(id, t, errore = false) { const m = $(id); if (!m) return; m.textContent = t; m.classList.toggle("errore", errore); }
  const num = (v, dec = 0) => (v === undefined || v === null || v === "" ? "" : EUGENIO_NUMERI.formato(v, dec, 0, ""));
  const copre = (f, [lon, lat]) => !Array.isArray(f.riquadro) || (lon >= f.riquadro[0] && lon <= f.riquadro[2] && lat >= f.riquadro[1] && lat <= f.riquadro[3]);

  // ------------------------------------------------------------------ filtri delle tessere
  function filtri() {
    const T = stato.tipi, part = [];
    if (T.has("E")) part.push("E", "M");
    if (T.has("T")) part.push("T", "M");
    const g = ["in", ["get", "g"], ["literal", [...stato.gruppi]]];
    const conTipo = ["in", ["get", "t"], ["literal", [...new Set(part)]]];
    const senza = ["==", ["get", "s"], 1];
    return {
      particelle: ["all", g, conTipo],
      // punti: quelli delle particelle (fino allo zoom 12) con lo stesso filtro; i beni senza particella con «S» e il tipo
      punti: ["all", g, ["case", senza, ["all", T.has("S"), ["in", ["get", "t"], ["literal", [...T].filter((x) => x !== "S")]]], conTipo]],
    };
  }
  function applicaFiltri() {
    const m = stato.mappa, f = filtri();
    if (!m || !m.getLayer("pa-punti")) return;
    ["pa-terreni", "pa-misti", "pa-edifici", "pa-linea"].forEach((id) => {
      const base = { "pa-terreni": ["==", ["get", "t"], "T"], "pa-misti": ["==", ["get", "t"], "M"], "pa-edifici": ["in", ["get", "t"], ["literal", ["E", "M"]]], "pa-linea": true }[id];
      m.setFilter(id, ["all", base, f.particelle]);
    });
    m.setFilter("pa-punti", f.punti);
  }

  // ------------------------------------------------------------------ livelli degli immobili
  function aggiungiLivelli(m) {
    const info = stato.info;
    m.addSource("pa", { type: "vector", url: `pmtiles://${location.origin}${info.pmtiles}`, attribution: "MEF – Patrimonio della PA; Agenzia delle Entrate (CC BY 4.0)" });
    const retino = R ? R.aggiungi(m) : null;
    const sotto = ["cercato", "confini-comuni-clic", "confini-regioni-clic"].find((id) => m.getLayer(id));
    m.addLayer({ id: "pa-terreni", type: "fill", source: "pa", "source-layer": "particelle", paint: { "fill-color": COLORI.T, "fill-opacity": 0.35 } }, sotto);
    m.addLayer({ id: "pa-misti", type: "fill", source: "pa", "source-layer": "particelle", paint: { "fill-color": COLORI.M, "fill-opacity": 0.25 } }, sotto);
    m.addLayer({ id: "pa-edifici", type: "fill", source: "pa", "source-layer": "particelle",
      paint: retino ? { "fill-pattern": retino, "fill-opacity": 0.9 } : { "fill-color": COLORI.E, "fill-opacity": 0.4 } }, sotto);
    m.addLayer({ id: "pa-linea", type: "line", source: "pa", "source-layer": "particelle",
      paint: { "line-color": ["match", ["get", "t"], "T", COLORI.T, "M", COLORI.M, COLORI.E],
        "line-width": ["interpolate", ["linear"], ["zoom"], 12, 0.6, 18, 2] } }, sotto);
    m.addLayer({ id: "pa-scelta", type: "line", source: "pa", "source-layer": "particelle", filter: ["==", ["get", "r"], ""],
      paint: { "line-color": colore("--primario"), "line-width": 4 } }, sotto);
    m.addLayer({ id: "pa-punti", type: "circle", source: "pa", "source-layer": "punti",
      paint: { "circle-color": ["case", ["==", ["get", "s"], 1], COLORI.S, ["match", ["get", "t"], "T", COLORI.T, "M", COLORI.M, COLORI.E]],
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 4, 1, 8, 1.6, 11, 3, 13, 4.5, 16, 6],
        "circle-opacity": ["interpolate", ["linear"], ["zoom"], 4, 0.7, 11, 0.95],
        "circle-stroke-color": "#fff", "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 10, 0, 12, 1] } }, sotto);
    applicaFiltri();
    const cliccabili = ["pa-punti", "pa-edifici", "pa-misti", "pa-terreni"];
    m.on("click", (e) => {
      if (ENTI() && ENTI().suClic(e)) return;                       // pallini e contorni degli enti scelti, sopra
      const f = m.queryRenderedFeatures([[e.point.x - 3, e.point.y - 3], [e.point.x + 3, e.point.y + 3]], { layers: cliccabili })[0];
      if (f) { e.preventDefault && e.preventDefault(); apri(String(f.properties.r)); }
    });
    m.on("mousemove", (e) => {
      if (ENTI() && ENTI().suMovimento(e)) return;
      const f = m.queryRenderedFeatures([[e.point.x - 3, e.point.y - 3], [e.point.x + 3, e.point.y + 3]], { layers: cliccabili })[0];
      m.getCanvas().style.cursor = f ? "pointer" : "";
      m.getCanvas().title = f ? `${f.properties.a || ""}${f.properties.n > 1 ? ` e altri (${f.properties.n} beni)` : ""}${f.properties.tp ? ` – ${f.properties.tp}` : ""}` : "";
    });
  }

  // ------------------------------------------------------------------ scheda
  function evidenzia(ref) {
    stato.selezione = ref;
    const m = stato.mappa;
    if (m && m.getLayer("pa-scelta")) m.setFilter("pa-scelta", ["==", ["get", "r"], ref && !ref.startsWith("b") ? ref : ""]);
  }
  function riferimentoLeggibile(ref) {
    const t = ref.split(".")[0], sez = t[4] === "_" ? "" : t[4];
    return `comune catastale ${t.slice(0, 4)}${sez ? `, sezione ${sez}` : ""}, foglio ${Number(t.slice(5, 9)) || t.slice(5, 9)}, particella ${ref.split(".")[1]}`;
  }
  const AGGANCI = { esatto: "identificativo catastale uguale", senza_sezione: "identificativo senza sezione, particella unica",
    sezione_dal_punto: "sezione scelta col punto del censimento", punto: "particella trovata col punto del censimento (identificativo non più in mappa)" };
  function riga(dl, nome, valore) {
    if (valore === undefined || valore === null || valore === "") return;
    dl.append(h("dt", null, nome), h("dd", null, String(valore)));
  }
  function schedaBene(b) {
    const art = h("article", "bene-pubblico");
    art.append(h("h3", null, `${b.tipologia || (b.natura === "TERRENO" ? "Terreno" : "Fabbricato")}`));
    const dl = h("dl", "scheda-bene");
    riga(dl, "Ente", b.amministrazione);
    riga(dl, "Tipo di ente", b.tipologia_amm);
    riga(dl, "Natura", b.natura === "TERRENO" ? "terreno" : b.natura === "FABBRICATO" ? "fabbricato" : b.natura);
    riga(dl, "Indirizzo", [b.indirizzo, b.civico].filter(Boolean).join(" ") + (b.comune ? `, ${b.comune}${b.provincia ? ` (${b.provincia})` : ""}` : ""));
    riga(dl, "Identificativo catastale (MEF)", b.id_catastale);
    riga(dl, "Superficie dichiarata", b.superficie_mq ? `${num(b.superficie_mq)} m²` : "");
    riga(dl, "Cubatura", b.cubatura_mc ? `${num(b.cubatura_mc)} m³` : "");
    riga(dl, "Aree di pertinenza", b.sup_pertinenze_mq ? `${num(b.sup_pertinenze_mq)} m²` : "");
    riga(dl, "Epoca di costruzione", b.epoca);
    riga(dl, "Titolo", b.titolo_proprieta ? `${b.titolo_proprieta}${b.quota_proprieta && b.quota_proprieta !== 100 ? ` (${num(b.quota_proprieta, 2)} %)` : ""}` : b.titolo_detenzione);
    riga(dl, "Canone annuo", b.canone_annuo ? `${num(b.canone_annuo)} €` : "");
    riga(dl, "Utilizzo", [b.utilizzo, b.finalita, b.altra_finalita].filter(Boolean).join(" – "));
    const si = (v) => /^s[iì]$/i.test(v || "");                     // nei CSV MEF «Sì» (prima del 22/11 si cercava «SI»)
    riga(dl, "Dato a terzi", si(b.a_terzi_intera) ? "per intero" : si(b.a_terzi_parziale) ? "in parte" : "");
    riga(dl, "Vincolo", b.vincolo && b.vincolo !== "Nessuno" ? b.vincolo : "");
    riga(dl, "Natura giuridica", b.natura_giuridica && b.natura_giuridica !== "ND" ? b.natura_giuridica : "");
    riga(dl, "Compendio", [b.compendio, b.tipologia_compendio].filter(Boolean).join(" – "));
    riga(dl, "Aggancio alla particella", b.aggancio ? AGGANCI[b.aggancio] || b.aggancio : "nessuna particella trovata: si usa il punto del censimento");
    art.appendChild(dl);
    // ricerca per ente (22/11/2026): tutti i beni dell'ente che ha dichiarato questo
    if (b.ente_chiave && ENTI() && ENTI().stato.elenco) {
      const p = h("p", "collegamenti-scheda"), bt = h("button", "bottone secondario piccolo", "Mostra tutti i beni di questo ente");
      bt.type = "button";
      bt.addEventListener("click", () => {
        const E = ENTI();
        if (!E.stato.attivo) E.modo(true);
        if (!E.stato.scelti.some((s) => s.chiave === b.ente_chiave)) E.aggiungi(b.ente_chiave, { inquadra: true });
        const c = document.getElementById("passo-cerca"); if (c) c.scrollIntoView({ behavior: "smooth", block: "start" });
      });
      p.appendChild(bt); art.appendChild(p);
    }
    return art;
  }
  async function apri(ref, vola = false) {
    if (!ref) return;
    const out = $("scheda-pubblici"); out.innerHTML = "";
    evidenzia(ref);
    messaggio("messaggio-scheda", "Carico la scheda…");
    try {
      const bene = ref.startsWith("b");
      const r = await fetch(bene ? `/api/immobili-pa/bene/${encodeURIComponent(ref.slice(1))}` : `/api/immobili-pa/particella/${encodeURIComponent(ref)}`);
      if (!r.ok) throw new Error(r.status === 404 ? "non trovata" : r.status === 429 ? "troppe richieste: riprova tra poco" : `errore ${r.status}`);
      const d = await r.json();
      // un bene senza particella può avere più dichiarazioni (proprietario e chi lo ha in uso): tutte (22/11/2026)
      const beni = bene ? (d.dichiarazioni || [d.bene]) : d.beni, p = d.particella;
      const testa = h("div", "testa-scheda");
      if (p) {
        testa.append(h("p", null, `Particella ${p.ref_ade} – ${riferimentoLeggibile(p.ref_ade)}${p.area_m2 ? ` – ${num(p.area_m2)} m² (dalla mappa catastale)` : ""}.`));
        const altri = p.n_beni - beni.length;
        testa.append(h("p", "aiuto", `${beni.length === 1 ? "Un bene pubblico" : `${beni.length} beni pubblici`} dichiarati in questa particella`
          + (beni.length >= 500 ? " (i primi 500)" : altri > 0 ? `, più ${altri === 1 ? "un'unità" : `${altri} unità`} che ci sta${altri === 1 ? "" : "nno"} solo in parte (unità «graffate» su più particelle, con la scheda nell'altra)` : "") + "."));
      } else testa.append(h("p", null, `Bene senza particella agganciata: il punto è quello del censimento.${beni.length > 1 ? ` Lo dichiarano ${beni.length} enti (di solito chi ne è proprietario e chi lo ha in uso).` : ""}`));
      const punto = p ? p.punto : (beni[0] && beni[0].lon !== undefined ? [beni[0].lon, beni[0].lat] : null);
      if (punto) {
        const l = h("p", "collegamenti-scheda");
        const a3 = h("a", "bottone secondario", "Apri in Modelli 3D"); a3.href = `modelli3d.html?lat=${punto[1].toFixed(6)}&lon=${punto[0].toFixed(6)}`;
        const ao = h("a", "bottone secondario", "Apri in Ortofoto"); ao.href = `ortofoto.html?lat=${punto[1].toFixed(6)}&lon=${punto[0].toFixed(6)}&z=18`;
        l.append(a3, " ", ao); testa.appendChild(l);
        if (vola) stato.mappa.flyTo({ center: punto, zoom: Math.max(stato.mappa.getZoom(), p ? 17 : 16.5), duration: 900 });
      }
      out.appendChild(testa);
      beni.forEach((b) => out.appendChild(schedaBene(b)));
      messaggio("messaggio-scheda", "");
      try { const u = new URL(location.href); u.searchParams.delete("ref"); u.searchParams.delete("bene"); u.searchParams.set(bene ? "bene" : "ref", bene ? ref.slice(1) : ref); history.replaceState(null, "", u); } catch { /* niente */ }
    } catch (e) {
      messaggio("messaggio-scheda", `La scheda non è arrivata (${e.message || e}).`, true);
    }
  }

  // ------------------------------------------------------------------ ricerca negli immobili
  async function cerca(ev) {
    if (ev) ev.preventDefault();
    const t = $("testo-pubblici").value.trim(), g = $("gruppo-cerca").value, lista = $("risultati-pubblici");
    lista.innerHTML = "";
    if (t.replace(/\W/g, "").length < 2) { messaggio("messaggio-cerca", "Scrivi almeno una parola di due lettere.", true); return; }
    messaggio("messaggio-cerca", "Cerco…");
    try {
      const r = await fetch(`/api/immobili-pa/cerca?q=${encodeURIComponent(t)}&gruppo=${encodeURIComponent(g)}&limite=30`);
      if (!r.ok) throw new Error(r.status === 503 ? "dati non ancora sul server" : r.status === 429 ? "troppe richieste: riprova tra poco" : r.status === 400 ? "ricerca non valida" : `errore ${r.status}`);
      const d = await r.json();
      if (!d.risultati.length) { messaggio("messaggio-cerca", "Nessun immobile trovato: prova con meno parole o con parole diverse."); return; }
      messaggio("messaggio-cerca", `${EUGENIO_NUMERI.formato(d.risultati.length)}${d.altri ? " (e altri: aggiungi parole per restringere)" : ""} risultati: un clic porta la mappa sull'immobile e apre la scheda.`);
      d.risultati.forEach((b) => {
        const li = h("li"), bt = h("button", "risultato-pubblico");
        bt.type = "button";
        bt.append(h("b", null, b.amministrazione || "Ente"), h("span", null, ` – ${b.tipologia || b.natura || ""}`),
          h("span", "aiuto-breve", ` ${[b.indirizzo, b.civico].filter(Boolean).join(" ")}${b.comune ? `, ${b.comune}` : ""}`
            + (b.altri_nella_particella ? ` (e altre ${b.altri_nella_particella} unità nella stessa particella)` : "")));
        bt.addEventListener("click", () => {
          if (b.ref_ade) apri(b.ref_ade, true);
          else apri(`b${b.id_bene}`, true);
        });
        li.appendChild(bt); lista.appendChild(li);
      });
    } catch (e) { messaggio("messaggio-cerca", `La ricerca non è riuscita (${e.message || e}).`, true); }
  }

  // ------------------------------------------------------------------ ortofoto (fonte migliore nel punto, come Ortofoto)
  function attribuzione(f) {
    const a = $("attribuzione"); a.innerHTML = "";
    if (!$("strato-ortofoto").checked) { a.textContent = "Ortofoto spenta."; return; }
    if (!f) { a.textContent = "Nessuna ortofoto in questa zona: restano i confini."; return; }
    a.append("Ortofoto: ", f.citazione, " – licenza ");
    const l = h("a", null, f.licenza); l.href = f.scheda; a.appendChild(l);
    a.append(f.copia ? "." : ". Solo consultazione dal vivo: non entra nelle immagini scaricate.");
    if (stato.contesto && f.id !== CONTESTO) a.append(` Sotto, come contesto: ${stato.contesto.citazione}.`);
  }
  const sorgente = (f) => (f.pmtiles ? { type: "raster", url: `pmtiles://${location.origin}${f.pmtiles}`, tileSize: 256, attribution: f.citazione }
    : { type: "raster", tiles: [location.origin + f.tessere], tileSize: 256, minzoom: f.zoom[0], maxzoom: f.zoom[1], bounds: f.riquadro, attribution: f.citazione });
  const sopra = () => ["strato-particelle", "strato-osm", "pa-terreni", "cercato", "confini-comuni-clic", "confini-regioni-clic"].find((id) => stato.mappa.getLayer(id));
  function scegliFonte(f) {
    const m = stato.mappa;
    if (m.getLayer("ortofoto")) m.removeLayer("ortofoto");
    if (m.getSource("ortofoto")) m.removeSource("ortofoto");
    stato.scelta = f || null;
    const acceso = $("strato-ortofoto").checked;
    if (f && f.id !== CONTESTO) {
      m.addSource("ortofoto", sorgente(f));
      m.addLayer({ id: "ortofoto", type: "raster", source: "ortofoto", layout: { visibility: acceso ? "visible" : "none" } }, sopra());
    }
    if (m.getLayer("contesto")) m.setLayoutProperty("contesto", "visibility", acceso ? "visible" : "none");
    if (C) C.alza(m);
    attribuzione(f);
  }
  let giro = 0;
  async function fontiQui() {
    const mio = ++giro, m = stato.mappa, c = m.getCenter();
    let qui;
    try { qui = C && C.fontiNelPunto ? await C.fontiNelPunto(stato.fonti, c.lng, c.lat) : null; } catch { qui = null; }
    if (!qui) qui = stato.fonti.filter((f) => copre(f, [c.lng, c.lat]));
    if (mio !== giro) return;
    const sel = $("sfondo-ortofoto"), prima = sel.value;
    sel.innerHTML = ""; sel.appendChild(new Option("automatica (la migliore della zona)", ""));
    qui.forEach((f) => sel.appendChild(new Option(`${f.nome} (${f.licenza})`, f.id)));
    if (stato.manuale && !qui.some((f) => f.id === prima)) stato.manuale = false;
    sel.value = stato.manuale ? prima : "";
    const voluta = stato.manuale ? qui.find((f) => f.id === prima) : qui.find((f) => f.id !== CONTESTO) || qui[0];
    if (!stato.scelta || !voluta || stato.scelta.id !== voluta.id) scegliFonte(voluta);
  }
  async function ortofoto(m) {
    try {
      const r = await fetch("/api/ortofoto/fonti");
      if (!r.ok || !/json/.test(r.headers.get("Content-Type") || "")) throw new Error(String(r.status));
      stato.fonti = (await r.json()).fonti || [];
    } catch { attribuzione(null); return; }
    const f = stato.fonti.find((x) => x.id === CONTESTO);
    if (f) {
      stato.contesto = f;
      m.addSource("contesto", sorgente(f));
      m.addLayer({ id: "contesto", type: "raster", source: "contesto", paint: { "raster-opacity": 0.95 } }, sopra());
    }
    $("sfondo-ortofoto").addEventListener("change", (e) => {
      stato.manuale = !!e.target.value;
      if (stato.manuale) scegliFonte(stato.fonti.find((x) => x.id === e.target.value)); else { stato.scelta = null; fontiQui(); }
    });
    $("strato-ortofoto").addEventListener("change", () => scegliFonte(stato.scelta));
    await fontiQui();
    m.on("moveend", fontiQui);
  }

  // ------------------------------------------------------------------ immagine della vista
  function opzioniImmagine() {
    const m = stato.mappa, f = stato.scelta, c = m.getCenter(), z = m.getZoom(), righe = [];
    if (f && !f.copia && $("strato-ortofoto").checked) return `«${f.nome}» è solo in consultazione dal vivo: non si può scaricare. Scegli un'altra fonte o spegni l'ortofoto.`;
    if (f && $("strato-ortofoto").checked) righe.push(`Ortofoto: ${f.citazione} – licenza ${f.licenza} (${f.scheda}).`);
    if (stato.info) righe.push(`Immobili delle PA: ${stato.info.attribuzione}.`);
    const enti = ENTI() ? ENTI().righeImmagine() : [];
    if (enti.length) righe.push("Enti scelti (colore: ente):", ...enti);
    righe.push(enti.length ? "Attenuati: gli altri immobili pubblici (retino a righe oblique magenta: edifici; verde: terreni; viola: edifici e terreni; arancio: beni senza particella)."
      : "Retino a righe oblique: particelle con edifici pubblici; verde: terreni; viola: edifici e terreni; arancio: beni senza particella.");
    if (stato.strati) righe.push(...stato.strati.righe());
    if (stato.cercato) righe.push(`Punto cercato: ${stato.cercato}.`);
    righe.push(`${C ? C.ATTRIBUZIONE : "Confini: ISTAT (CC BY 4.0)"}. Mappa: MapLibre GL JS (BSD-3).`);
    return { titolo: `Edifici pubblici – centro ${c.lat.toFixed(5)} N, ${c.lng.toFixed(5)} E, zoom ${z.toFixed(1)}`, righe, nome: `edifici_pubblici_${c.lat.toFixed(4)}_${c.lng.toFixed(4)}` };
  }

  // ------------------------------------------------------------------ regioni (piccola mappa)
  async function vaiRegione(cod, sposta = true) {
    const b = C && await C.riquadroRegione(cod);
    if (!b) return;
    stato.regione = cod;
    if (stato.confini) { stato.confini.scegliRegione(cod); stato.confini.scegliComune(""); }
    if (window.EUGENIO && window.EUGENIO.seleziona) window.EUGENIO.seleziona(cod);
    if (sposta) stato.mappa.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 20, duration: 700 });
  }
  function togliRegione(sposta = true) {
    stato.regione = null;
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

  // ------------------------------------------------------------------ caselle dei livelli
  function caselle() {
    const gruppi = (stato.info && stato.info.gruppi) || GRUPPI_PREDEFINITI;
    stato.gruppi = new Set(Object.keys(gruppi));
    const fs = $("gruppi-pubblici"), sel = $("gruppo-cerca");
    Object.entries(gruppi).forEach(([k, nome]) => {
      const l = h("label", "casella-strato"), i = h("input"); i.type = "checkbox"; i.value = k; i.checked = true;
      l.append(i, ` ${nome}`); fs.appendChild(l);
      sel.appendChild(new Option(nome, k));
    });
    fs.addEventListener("change", () => { stato.gruppi = new Set([...fs.querySelectorAll("input:checked")].map((x) => x.value)); applicaFiltri(); });
    $("tipi-pubblici").addEventListener("change", () => { stato.tipi = new Set([...$("tipi-pubblici").querySelectorAll("input:checked")].map((x) => x.value)); applicaFiltri(); });
    const tutti = (si) => { fs.querySelectorAll("input").forEach((x) => { x.checked = si; }); fs.dispatchEvent(new Event("change")); };
    $("tutti-enti").addEventListener("click", () => tutti(true));
    $("nessun-ente").addEventListener("click", () => tutti(false));
    // campioni nella legenda: retino vero (stesso disegno della mappa)
    const leg = $("legenda-pubblici");
    if (R && leg) { const p = leg.querySelector(".pa-edifici"); if (p) p.replaceWith(R.campione()); }
  }

  // ------------------------------------------------------------------ avvio
  (async function avvio() {
    const centro = conPunto ? [+q.get("lon"), +q.get("lat")] : P0 ? [P0.lon, P0.lat] : [12.5683, 44.0594];
    const m = new window.maplibregl.Map({ container: box, center: centro, zoom: Number(q.get("z")) || (conPunto ? 17 : P0 ? P0.zoom : 7),
      maxZoom: 21, minZoom: 4.5, attributionControl: false, canvasContextAttributes: { preserveDrawingBuffer: true },
      style: { version: 8, sources: {}, layers: [{ id: "sfondo", type: "background", paint: { "background-color": colore("--carta") } }] } });
    stato.mappa = m;
    if (window.EUGENIO_LIMITI) window.EUGENIO_LIMITI.collega(m);
    m.addControl(new window.maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.addControl(new window.maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    m.addControl(new window.maplibregl.AttributionControl({ compact: true }), "bottom-right");
    if (window.pmtiles) { const proto = new window.pmtiles.Protocol(); window.maplibregl.addProtocol("pmtiles", proto.tile); }
    await new Promise((ok) => m.on("load", ok));
    box.querySelectorAll(".maplibregl-compact-show").forEach((x) => x.classList.remove("maplibregl-compact-show"));
    document.addEventListener("eugenio:ridimensiona", () => m.resize());
    document.addEventListener("eugenio:aspetto", () => {
      m.setPaintProperty("sfondo", "background-color", colore("--carta"));
      if (m.getLayer("pa-scelta")) m.setPaintProperty("pa-scelta", "line-color", colore("--primario"));
    });
    if (C) {
      try {
        stato.confini = await C.aggiungi(m, {
          attivo: (ev) => !m.queryRenderedFeatures(ev.point, { layers: ["pa-punti", "pa-edifici", "pa-misti", "pa-terreni"].filter((id) => m.getLayer(id)) }).length,
          suRegione: (cod) => { if (stato.regione === cod) togliRegione(false); else vaiRegione(cod, false); },
          suComune: (c) => { messaggio("messaggio-mappa", c ? `Comune di ${c.nome}${c.prov ? ` (${c.prov})` : ""}: avvicinati per vedere le particelle, o cerca il comune a destra.` : ""); },
        });
      } catch { /* confini non disponibili */ }
    }
    m.addSource("cercato", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    m.addLayer({ id: "cercato", type: "circle", source: "cercato", paint: { "circle-radius": 7, "circle-color": colore("--primario"),
      "circle-stroke-color": "#fff", "circle-stroke-width": 2 } }, ["confini-comuni-clic", "confini-regioni-clic"].find((id) => m.getLayer(id)));
    // dati degli immobili: indice delle tessere (file statico) e, per la ricerca, l'API
    try {
      const r = await fetch("/edifici3d/immobili_pa/indice.json", { cache: "no-cache" });
      if (!r.ok || !/json/.test(r.headers.get("Content-Type") || "")) throw new Error(String(r.status));
      stato.info = await r.json();
    } catch {
      messaggio("messaggio-mappa", "Gli immobili delle PA non sono ancora sul server: la mappa mostra solo ortofoto e confini.", true);
    }
    caselle();
    if (stato.info && stato.info.pmtiles) {
      aggiungiLivelli(m);
      $("attribuzione-pubblici").textContent = `Immobili: ${stato.info.attribuzione}. ${num(stato.info.beni)} beni, ${num(stato.info.particelle)} particelle.`;
    }
    await ortofoto(m);
    if (window.EUGENIO_STRATI) {
      try {
        stato.strati = await window.EUGENIO_STRATI.aggiungi(m, { caselle: $("caselle-strati"), legenda: $("legenda-strati"),
          sotto: () => ["pa-terreni", "cercato", "confini-comuni-clic", "confini-regioni-clic"].find((id) => m.getLayer(id)) });
      } catch { /* strati non disponibili */ }
    }
    if (window.EUGENIO_RIGHELLO) window.EUGENIO_RIGHELLO.aggiungi(m);      // righello per distanze e aree (19/11/2026)
    if (window.EUGENIO_ESPORTA) window.EUGENIO_ESPORTA.pulsanti($("scarica-pubblici"), m, opzioniImmagine, $("messaggio-immagine"));
    if (q.get("ref")) apri(q.get("ref").toUpperCase(), !conPunto);
    else if (/^\d+$/.test(q.get("bene") || "")) apri(`b${q.get("bene")}`, !conPunto);
  })().finally(() => {
    stato.pronto = true;
    segnalaPronto();
    if (stato.mappa && window.EUGENIO_COLLEGAMENTO) stato.mappa.on("moveend", () => window.EUGENIO_COLLEGAMENTO.aggiorna());
  });

  // collegamento a questa simulazione (20/11/2026): vista (lat, lon, z) e scheda aperta (ref o bene: la scrive già apri())
  // le legge la pagina all'apertura; qui anche tipi e gruppi di enti accesi (codici, vuoto = nessuno; tutti = parametro
  // assente); ortofoto, fonte, particelle e contorni sono controlli data-collegamento
  if (window.EUGENIO_COLLEGAMENTO) window.EUGENIO_COLLEGAMENTO.registra({
    regione: false,
    chiavi: ["lat", "lon", "z", "tipi", "enti"],
    pronto: () => stato.pronto,
    leggi() {
      const m = stato.mappa;
      if (!m || !stato.pronto) return null;
      const c = m.getCenter(), tutti = [...$("gruppi-pubblici").querySelectorAll("input")];
      const accesi = (box) => [...box.querySelectorAll("input:checked")].map((x) => x.value).join(",");
      return { lat: c.lat.toFixed(6), lon: c.lng.toFixed(6), z: m.getZoom().toFixed(2),
        tipi: stato.tipi.size === 3 ? null : accesi($("tipi-pubblici")) || "nessuno",
        enti: tutti.every((x) => x.checked) ? null : accesi($("gruppi-pubblici")) || "nessuno" };
    },
    applica(p) {
      const metti = (box, v) => {
        if (v === null) return;
        const si = new Set(v.split(","));
        box.querySelectorAll("input[type=checkbox]").forEach((x) => { x.checked = si.has(x.value); });
        box.dispatchEvent(new Event("change", { bubbles: true }));
      };
      metti($("tipi-pubblici"), p.get("tipi"));
      metti($("gruppi-pubblici"), p.get("enti"));
    },
  });

  $("cerca-pubblici").addEventListener("submit", cerca);
  if (window.EUGENIO_CERCA) {
    window.EUGENIO_CERCA.crea($("cerca-luogo"), {
      suTrovato: (lon, lat, riga) => {
        const m = stato.mappa;
        if (!m || !m.getSource("cercato")) return;
        m.getSource("cercato").setData({ type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [lon, lat] } }] });
        stato.cercato = riga.centro_comune ? `centro del comune di ${riga.comune_catasto} (confini ISTAT, CC BY 4.0)`
          : `${[riga.indirizzo_trovato, riga.comune_catasto].filter(Boolean).join(", ") || `${lat.toFixed(5)}, ${lon.toFixed(5)}`}`
          + ` (${riga.fonte_punto === "ANNCSU" ? "ANNCSU – Agenzia delle Entrate e ISTAT, CC BY 4.0" : "dati elaborati da Zornade, zornade.com"})`;
        m.flyTo({ center: [lon, lat], zoom: riga.zoom || window.EUGENIO_CERCA.ZOOM || 17, duration: 900 });
      },
    });
  }
  window.EUGENIO_PUBBLICI = { stato, filtri, applicaFiltri, apri, cerca, opzioniImmagine, pronto };
})();
