"use strict";
// Ricerca di un luogo per indirizzo (via e civico, comune) o per dati catastali (comune, foglio, particella), comune alle
// pagine Modelli 3D e Ortofoto (05/11/2026, seconda pubblicazione: prima era solo in edificio3d.js).
//
// Una riga a POST /api/patrimonio, la stessa rotta della pagina Patrimonio: indirizzi prima nell'ANNCSU (sul server, CC BY
// 4.0), poi, per quello che manca e per le particelle, Zornade. Nessuna dipendenza nuova da Zornade (§ 14.2 aperto). La
// verifica anti-robot (Turnstile) la aggiunge da sé protezione.js, che avvolge fetch.
//
//  EUGENIO_CERCA.crea(contenitore, { suTrovato(lon, lat, riga), prima() })
//    (09/11/2026 b, prove di Paolo) crea **un solo modulo** (#cerca-luogo-modulo): Comune una volta sola in cima
//    (#cerca-comune), Indirizzo (#cerca-via), Foglio e Particella affiancati (#catasto-foglio, #catasto-particella), poi i
//    pulsanti «Cerca l'indirizzo» (#cerca-indirizzo: Comune + Indirizzo), «Cerca la particella» (#cerca-particella: Comune +
//    Foglio + Particella) e un solo «Reset» (#cerca-reset) che svuota tutto; la nota sulle fonti e la riga dei messaggi
//    (#messaggio-cerca). Con il solo Comune tutti e due i pulsanti portano al centro del comune. Invio in Indirizzo cerca
//    l'indirizzo, in Foglio o Particella la particella, nel Comune quello che è scritto (indirizzo, poi particella, poi
//    centro del comune). Prima c'erano due moduli con due «Comune» e due «Reset»: con un comune diverso nei due blocchi
//    (Bagno di Romagna nella particella, Susegana rimasto nell'indirizzo) la ricerca finiva nel comune sbagliato.
//    suTrovato riceve il punto e la riga della risposta; prima() si chiama prima di ogni ricerca.
//  Un risultato in un altro comune (comune catastale diverso da quello scritto, per esempio una via omonima trovata da
//    Zornade altrove) non sposta la mappa sul punto: si va al centro del comune scritto, con l'avviso.
//  EUGENIO_CERCA.cerca({ indirizzo, comune, foglio, particella }, suScelta) → la riga trovata (o null) e il messaggio scritto;
//    con più vie fra cui scegliere { scelta: [...], riga } (niente lon/lat) e i pulsanti nel messaggio, che chiamano
//    suScelta(lon, lat, riga).
//  EUGENIO_CERCA.ZOOM: zoom della mappa sul punto trovato, uguale in Modelli 3D e Ortofoto (07/11/2026: 17, l'isolato
//    intero con il segnaposto; prima 18 in tutte e due).
//  (07/11/2026 sera) Solo il comune (senza indirizzo o senza particella): la mappa va al centro del comune (baricentro
//    del confine ISTAT dei file dati/mappa/<regione>.json del sito, nessuna chiamata al server), a ZOOM_COMUNE. Una
//    risposta senza coordinate vere (vuote o 0,0: civico non georeferenziato in ANNCSU né da Zornade, Novafeltria) non
//    è mai un punto: si va al centro del comune con l'avviso. La riga passata a suTrovato ha allora centro_comune = true
//    e zoom = ZOOM_COMUNE.
//  (17/11/2026, segnalazione di Paolo) La richiesta porta `luogo=1`: il server aggiunge alla riga dove mettere il segnaposto e
//    cosa inquadrare (fase4-server/servizio/luogo.py, fase7-territorio/territorio/luogo.py). Con il **civico** (o foglio e
//    particella) il segnaposto va su un punto interno della **particella catastale** del civico (Agenzia delle Entrate –
//    Cartografia catastale, CC BY 4.0) e la mappa inquadra la particella; con più accessi dello stesso civico (2, 2/B … 2/O)
//    la più grande fra le loro particelle (decisione di Paolo, «scelta B»: l'ospedale Infermi di Rimini, viale Settembrini
//    2, è la particella n. 1, non quella dell'accesso «2» all'angolo sud); `luogo_regola` dice la regola applicata.
//    Con la **sola via** il segnaposto va a **metà della via** (strade di OpenStreetMap, ODbL, o civici ANNCSU) e la mappa
//    è centrata lì con uno zoom che fa vedere la via (via Coriano a Rimini: ~6 km). Più vie compatibili (stesso nome in
//    frazioni diverse, via non riconosciuta: «via Sant'Andrea delle Fratte» a Perugia è una frazione) → l'elenco da scegliere
//    nella riga dei messaggi, la mappa non si muove. Senza questi campi (server di prima, fonti non disponibili) tutto come
//    prima, con un avviso discreto. La riga passata a suTrovato ha in più `riquadro` ([ovest, sud, est, nord]),
//    `luogo_tipo` e `fonte_testo` (attribuzione completa del punto); inquadra(mappa, lon, lat, riga, extra) muove la mappa.
//  EUGENIO_CERCA.PARTENZA (08/11/2026, decisione di Paolo): punto di apertura delle pagine di mappa con la ricerca di
//    edifici e ortofoto (Ortofoto, Modelli 3D, pagine 3D) quando l'indirizzo non dice altro (?lat=&lon=, ?sede=, ?edificio=,
//    ?modello=, ?dbtr=, una regione scelta diversa dall'Emilia-Romagna): Cesena, ospedale Bufalini (viale Ghirotti 286), in
//    collina. Centro: baricentro dei 59 corpi DBTR della particella foglio 149 n. 387 (archivio DBTR di Cesena, quote del
//    terreno 38–59 m: 44,1338 N 12,2597 E), spostato di ~130 m a sud perché si veda anche la collina; zoom 15,6 (ospedale e collina insieme).
//    Lo stesso indirizzo è l'esempio nei campi di ricerca.
(function () {
  function h(tag, cls, t) { const e = document.createElement(tag); if (cls) e.className = cls; if (t !== undefined) e.textContent = t; return e; }
  function campo(etichetta, id, attr = {}) {
    const l = h("label", null, `${etichetta} `), i = h("input");
    i.id = id; i.type = "text";
    Object.entries(attr).forEach(([k, v]) => i.setAttribute(k, v));
    l.appendChild(i);
    return l;
  }
  let msg = null;
  function messaggio(t, errore = false) { if (!msg) return; msg.textContent = t; msg.classList.toggle("errore", errore); }

  // ------------------------------------------------------------------ centro del comune (senza server)
  const ZOOM_COMUNE = 14;
  const S = 0.0010012596459353985, AX = -313.67365575107954, AY = 5226.851664605516;   // come confini_gl.js
  const V = (document.currentScript && /[?&]v=([\w-]+)/.exec(document.currentScript.src) || [])[1] || "";
  const piano = (t) => String(t || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  const REGIONI = ["08", "11", "09", "05", "03", "07", "01", "02", "04", "06", "10", "12", "13", "14", "15", "16", "17", "18", "19", "20"];
  const mappe = new Map();
  async function mappa(cod) {
    if (!mappe.has(cod)) mappe.set(cod, fetch(`dati/mappa/${cod}.json${V ? `?v=${V}` : ""}`).then((r) => (r.ok ? r.json() : null)).catch(() => null));
    return mappe.get(cod);
  }
  function svgLonlat(x, y) {
    const C = window.EUGENIO_CONFINI;
    if (C && C.svgLonlat) return C.svgLonlat(x, y);
    return null;
  }
  // centro del comune per nome (Emilia-Romagna per prima, poi le regioni vicine e le altre): { lon, lat, nome, istat }
  async function centroComune(nome) {
    const q = piano(nome);
    if (q.length < 2) return null;
    for (const cod of REGIONI) {
      const m = await mappa(cod);
      const c = m && (m.comuni || []).find((x) => piano(x.nome) === q);
      if (c && Number.isFinite(+c.x) && Number.isFinite(+c.y)) {
        const p = svgLonlat(+c.x, +c.y);
        if (p) return { lon: p[0], lat: p[1], nome: c.nome, istat: c.istat };
      }
    }
    return null;
  }
  // coordinate vere: numeri, non 0,0, dentro l'Italia larga (mai la mappa sul golfo di Guinea)
  const vero = (lat, lon) => lat !== null && lon !== null && lat !== "" && lon !== "" && Number.isFinite(+lat) && Number.isFinite(+lon)
    && !(Math.abs(+lat) < 1e-6 && Math.abs(+lon) < 1e-6) && +lat > 35 && +lat < 48 && +lon > 6 && +lon < 19.5;
  // comune catastale della risposta diverso da quello scritto: il server lo segnala nella nota (codice catastale diverso)
  // e i nomi non hanno nulla in comune (i comuni nati da fusione contengono il nome di quello d'origine: Montescudo)
  function altroComune(x, comune) {
    const a = piano(x && x.comune_catasto), b = piano(comune);
    if (!a || !b || a === b || a.includes(b) || b.includes(a)) return false;
    return /diverso da quello indicato/.test(String((x && x.nota) || ""));
  }
  async function alCentro(comune, perche) {
    const c = await centroComune(comune);
    if (!c) { messaggio(`${perche}Comune «${comune}» non trovato nei confini ISTAT: controlla il nome.`, true); return null; }
    messaggio(`${perche}Ti porto al centro del comune di ${c.nome} (confini ISTAT, CC BY 4.0): avvicinati e sposta il punto `
      + "sull'edificio (trascinalo o fai clic sulla mappa).", !!perche);
    return { lon: c.lon, lat: c.lat, riga: { centro_comune: true, zoom: ZOOM_COMUNE, comune_catasto: c.nome, istat: c.istat,
      indirizzo_trovato: "", fonte_punto: "ISTAT" } };
  }

  const ATTR = { ANNCSU: "ANNCSU – Agenzia delle Entrate e ISTAT (CC BY 4.0)", Zornade: "Dati elaborati da Zornade" };
  const numeri = (r) => Array.isArray(r) && r.length === 4 && r.every((v) => v !== null && Number.isFinite(+v));
  // pulsanti delle vie fra cui scegliere (o «altre vie simili»), nella riga dei messaggi
  function scelte(titolo, lista, suScelta, errore) {
    if (!msg) return;
    msg.innerHTML = ""; msg.classList.toggle("errore", false); msg.classList.toggle("attenzione", !!errore);
    const corpo = h("div", "cerca-corpo");
    corpo.append(titolo);
    const riga = h("div", "cerca-scelte");
    lista.forEach((c) => {
      const b = h("button", "bottone secondario", c.testo); b.type = "button";
      b.addEventListener("click", () => suScelta(c));
      riga.appendChild(b);
    });
    corpo.appendChild(riga);
    msg.appendChild(corpo);
  }
  // una via (o località) dell'elenco come riga per suTrovato
  function rigaDaVia(x, c) {
    return { ...x, indirizzo_trovato: c.nome, fonte_punto: /OpenStreetMap/.test(c.fonte) ? "OpenStreetMap" : "ANNCSU",
      fonte_testo: c.fonte, riquadro: numeri(c.riquadro) ? c.riquadro.map(Number) : null, luogo_tipo: c.tipo,
      zoom: c.tipo === "località" ? ZOOM_LOCALITA : x.zoom, centro_comune: false };
  }

  async function cerca(campi, suScelta) {
    const col = ["id", "denominazione", "indirizzo", "civico", "comune", "foglio", "particella"];
    const pulito = (v) => String(v || "").replace(/[;\r\n"]+/g, " ").trim().slice(0, 120);
    const testo = `${col.join(";")}\n${["1", "ricerca", pulito(campi.indirizzo), "", pulito(campi.comune), pulito(campi.foglio), pulito(campi.particella)].join(";")}\n`;
    messaggio("Cerco…");
    const fd = new FormData();
    fd.append("file", new Blob([testo], { type: "text/csv;charset=utf-8" }), "ricerca.csv");
    fd.append("luogo", "1");              // (17/11/2026) particella del civico, metà della via, vie fra cui scegliere
    let r, d = null;
    try { r = await fetch("/api/patrimonio", { method: "POST", body: fd }); } catch { messaggio("Il server non risponde: riprova più tardi.", true); return null; }
    try { d = await r.json(); } catch { /* non JSON */ }
    if (!r.ok) { messaggio(r.status === 503 ? "La ricerca non è attiva su questo server." : `Ricerca non riuscita: ${(d && d.detail) || r.status}.`, true); return null; }
    const x = d && d.righe && d.righe[0];
    // (17/11/2026) più vie compatibili o via non riconosciuta: si sceglie, la mappa non si muove
    if (x && x.scegli_via && Array.isArray(x.vie_candidate) && x.vie_candidate.length) {
      const lista = x.vie_candidate.filter((c) => vero(c.lat, c.lon)).map((c) => ({ testo: c.etichetta || c.nome, lon: +c.lon, lat: +c.lat, riga: rigaDaVia(x, c) }));
      if (vero(x.lat, x.lon) && x.esito !== "non_trovato" && !(campi.comune && altroComune(x, campi.comune))) {
        lista.push({ testo: `Punto trovato: ${x.indirizzo_trovato || "indirizzo"} (${x.fonte_punto === "ANNCSU" ? "ANNCSU" : "Zornade"})`,
          lon: +x.lon, lat: +x.lat, riga: { ...x, fonte_testo: x.fonte_punto === "ANNCSU" ? ATTR.ANNCSU : `${ATTR.Zornade} (zornade.com)` } });
      }
      const nome = String(campi.indirizzo || "").trim();
      scelte(`«${nome}» non è una sola via${campi.comune ? ` a ${campi.comune}` : ""}: scegli quella giusta (vie e località da `
        + "OpenStreetMap, ODbL, e dall'ANNCSU, CC BY 4.0).", lista, (c) => {
        if (suScelta) suScelta(c.lon, c.lat, c.riga);
        messaggio(`Scelta: ${c.testo}. Fonte: ${c.riga.fonte_testo || ""}.`);
      }, true);
      return { scelta: lista, riga: x };
    }
    const luogo = x && vero(x.luogo_lat, x.luogo_lon) && !(campi.comune && altroComune(x, campi.comune));
    if (!luogo && (!x || !vero(x.lat, x.lon) || x.esito === "non_trovato")) {
      // senza coordinate (07/11/2026 sera): al centro del comune, se c'è
      if (campi.comune) {
        const perche = campi.indirizzo ? `Indirizzo senza coordinate in ANNCSU né da Zornade${x && x.nota ? ` (${x.nota})` : ""}. `
          : `Particella non trovata${x && x.nota ? ` (${x.nota})` : ""}. `;
        return alCentro(campi.comune, perche);
      }
      messaggio(`Non trovato${x && x.nota ? `: ${x.nota}` : ""}. Controlla il testo o prova con foglio e particella.`, true); return null;
    }
    // (09/11/2026 b) risultato in un altro comune: mai la mappa lì (Bagno di Romagna → «via San Salvatore 13, Susegana»)
    if (campi.comune && altroComune(x, campi.comune)) {
      const cosa = campi.indirizzo ? "L'indirizzo trovato" : "La particella trovata";
      return alCentro(campi.comune, `${cosa} è nel comune di ${x.comune_catasto}, non in quello scritto (${campi.comune}). `);
    }
    let lat = +x.lat, lon = +x.lon;
    const pa = x.particella_ade, via = x.via_scelta;
    const riga = { ...x };
    if (luogo) {                           // (17/11/2026) segnaposto nella particella o a metà della via, riquadro da inquadrare
      lat = +x.luogo_lat; lon = +x.luogo_lon;
      riga.riquadro = numeri(x.luogo_riquadro) ? x.luogo_riquadro.map(Number) : null;
      if (x.luogo_tipo === "località") riga.zoom = ZOOM_LOCALITA;
      if (via) { riga.indirizzo_trovato = via.nome; if (/OpenStreetMap/.test(via.fonte)) riga.fonte_punto = "OpenStreetMap"; }
    }
    const fonte = riga.fonte_punto === "ANNCSU" ? ATTR.ANNCSU : riga.fonte_punto === "OpenStreetMap" ? "" : ATTR.Zornade;
    // testo per i report e le immagini (Zornade con il dominio: lì il collegamento non c'è)
    riga.fonte_testo = [fonte === ATTR.Zornade ? `${fonte} (zornade.com)` : fonte,
      luogo && x.luogo_fonte ? `${x.luogo_tipo === "particella" ? "particella: " : ""}${x.luogo_fonte}` : ""].filter(Boolean).join("; ");
    const dove = [riga.indirizzo_trovato, x.comune_catasto].filter(Boolean).join(", ");
    const part = luogo && pa ? `particella foglio ${pa.foglio}, ${pa.mappale}${pa.area_m2 ? ` (${Math.round(pa.area_m2).toLocaleString("it-IT")} m²)` : ""}`
      + (x.luogo_regola === "particella_piu_grande_del_civico" ? ", la più grande fra quelle degli accessi del civico" : "")
      : x.mappale ? `particella ${x.foglio_catasto ? `foglio ${x.foglio_catasto}, ` : ""}${x.mappale}` : "";
    const meta = luogo && via ? `metà della via${via.lunghezza_m ? ` (${via.lunghezza_m >= 1000 ? `${(via.lunghezza_m / 1000).toFixed(1).replace(".", ",")} km` : `${via.lunghezza_m} m`})` : ""}` : "";
    // con la via scelta, la nota «civico non indicato: usato il …» del civico centrale non vale più
    const nota = luogo && via ? "" : x.nota;
    if (msg) {
      msg.innerHTML = ""; msg.classList.toggle("errore", x.esito !== "ok" && !(luogo && via)); msg.classList.toggle("attenzione", false);
      const corpo = h("div", "cerca-corpo");
      corpo.append(`${x.esito === "ok" || (luogo && via) ? "Trovato" : "Trovato, da verificare"}: ${[dove, part, meta].filter(Boolean).join(" – ") || `${lat.toFixed(5)}, ${lon.toFixed(5)}`}`
        + `${nota ? ` (${nota})` : ""}. Fonte: `);
      if (fonte === ATTR.Zornade) { const a = h("a", null, fonte); a.href = "https://zornade.com"; corpo.appendChild(a); } else if (fonte) corpo.append(fonte);
      if (luogo && x.luogo_fonte) corpo.append(`${fonte ? "; " : ""}${x.luogo_tipo === "particella" ? "particella: " : ""}${x.luogo_fonte}`);
      corpo.append(".");
      if (x.luogo_avviso) { const s = h("span", "cerca-avviso", ` Nota: ${x.luogo_avviso}.`); corpo.appendChild(s); }
      const altre = (Array.isArray(x.vie_candidate) ? x.vie_candidate : []).filter((c) => vero(c.lat, c.lon));
      if (altre.length && suScelta) {
        corpo.append(" Altre vie simili:");
        const r = h("div", "cerca-scelte");
        altre.forEach((c) => {
          const b = h("button", "bottone secondario", c.etichetta || c.nome); b.type = "button";
          b.addEventListener("click", () => { suScelta(+c.lon, +c.lat, rigaDaVia(x, c)); messaggio(`Scelta: ${c.etichetta || c.nome}. Fonte: ${c.fonte}.`); });
          r.appendChild(b);
        });
        corpo.appendChild(r);
      }
      msg.appendChild(corpo);
    }
    return { lon, lat, riga };
  }

  // (17/11/2026) muove la mappa sul risultato: particella → tutta la particella (e gli altri accessi dello stesso civico)
  // nella vista, zoom al più ZOOM_PARTICELLA; via → centrata sulla metà, zoom che fa vedere tutta la via (o, se la metà è
  // molto fuori centro, buona parte); senza riquadro come prima (zoom della riga o ZOOM). extra: altre opzioni di flyTo
  // (pitch, bearing).
  function inquadra(m, lon, lat, riga = {}, extra = {}) {
    if (!m) return;
    const r = riga && numeri(riga.riquadro) ? riga.riquadro.map(Number) : null;
    const opz = { padding: 40, bearing: extra.bearing !== undefined ? extra.bearing : m.getBearing() };
    let cam = null;
    try {
      if (r && riga.luogo_tipo === "particella") {
        const c = m.cameraForBounds([[Math.min(r[0], lon), Math.min(r[1], lat)], [Math.max(r[2], lon), Math.max(r[3], lat)]], { ...opz, maxZoom: ZOOM_PARTICELLA });
        if (c) cam = { center: c.center, zoom: Math.min(c.zoom, ZOOM_PARTICELLA) };
      } else if (r) {
        const dx = Math.max(lon - r[0], r[2] - lon, 1e-5), dy = Math.max(lat - r[1], r[3] - lat, 1e-5);
        const tutta = m.cameraForBounds([[lon - dx, lat - dy], [lon + dx, lat + dy]], { ...opz, maxZoom: ZOOM });
        const box = m.cameraForBounds([[r[0], r[1]], [r[2], r[3]]], { ...opz, maxZoom: ZOOM });
        if (tutta && box) cam = { center: [lon, lat], zoom: Math.min(ZOOM, Math.max(tutta.zoom, box.zoom - 1)) };
      }
    } catch { cam = null; }
    if (!cam || !Number.isFinite(cam.zoom)) cam = { center: [lon, lat], zoom: (riga && riga.zoom) || ZOOM };
    m.flyTo({ ...extra, ...cam, duration: 900 });
  }

  function crea(dove, opz = {}) {
    if (!dove) return null;
    dove.classList.add("cerca-edificio");
    const f = h("form", "cerca-modulo"); f.id = "cerca-luogo-modulo"; f.noValidate = true;
    const riga = (cls, ...figli) => { const r = h("div", `riga-cerca ${cls}`); r.append(...figli); return r; };
    const pulsante = (id, testo, cls, title) => { const b = h("button", cls, testo); b.type = "button"; b.id = id; if (title) b.title = title; return b; };
    const bInd = pulsante("cerca-indirizzo", "Cerca l'indirizzo", "bottone secondario", "Cerca con Comune e Indirizzo (solo il Comune: al centro del comune)");
    const bPar = pulsante("cerca-particella", "Cerca la particella", "bottone secondario", "Cerca con Comune, Foglio e Particella (solo il Comune: al centro del comune)");
    const bReset = pulsante("cerca-reset", "Reset", "bottone secondario cerca-reset", "Svuota tutti i campi della ricerca");
    f.append(
      riga("riga-comune", campo("Comune", "cerca-comune", { autocomplete: "address-level2", placeholder: "Cesena" })),
      riga("riga-indirizzo", campo("Indirizzo", "cerca-via", { autocomplete: "street-address", placeholder: "viale Ghirotti 286" })),
      riga("riga-catasto", campo("Foglio", "catasto-foglio", { inputmode: "numeric", size: "5", placeholder: "149" }),
        campo("Particella", "catasto-particella", { inputmode: "numeric", size: "6", placeholder: "387" })),
      riga("riga-pulsanti", bInd, bPar, bReset));
    const aiuto = h("p", "aiuto");
    aiuto.append("Scrivi il comune una volta sola, poi l'indirizzo («Cerca l'indirizzo») oppure foglio e particella («Cerca la "
      + "particella»); con il solo comune la mappa va al centro del comune. Gli indirizzi si cercano prima nell'archivio nazionale "
      + "dei civici ANNCSU (Agenzia delle Entrate e ISTAT, CC BY 4.0) e, se mancano, con la geocodifica di Zornade; foglio e "
      + "particella con le particelle catastali di Zornade, come nella pagina ");
    const a = h("a", null, "Patrimonio"); a.href = "patrimonio.html"; aiuto.append(a, ". I dati catastali non sostituiscono visure ed estratti ufficiali.");
    msg = h("div", "messaggio"); msg.id = "messaggio-cerca"; msg.setAttribute("role", "status"); msg.setAttribute("aria-live", "polite");
    dove.append(f, aiuto, msg);
    const val = (id) => f.querySelector(`#${id}`).value.trim();
    const vaiAlComune = async (comune) => {
      if (opz.prima) opz.prima();
      messaggio("Cerco il comune…");
      const t = await alCentro(comune, "");
      if (t && opz.suTrovato) await opz.suTrovato(t.lon, t.lat, t.riga);
    };
    const vai = async (campi) => {
      if (opz.prima) opz.prima();
      const t = await cerca(campi, opz.suTrovato ? (lon, lat, riga) => opz.suTrovato(lon, lat, riga) : null);
      if (t && !t.scelta && opz.suTrovato) await opz.suTrovato(t.lon, t.lat, t.riga);
    };
    // «indirizzo» usa solo Comune + Indirizzo, «particella» solo Comune + Foglio + Particella: l'altro gruppo di campi non
    // entra mai nella richiesta, anche se è pieno
    function esegui(azione) {
      const comune = val("cerca-comune"), via = val("cerca-via"), foglio = val("catasto-foglio"), particella = val("catasto-particella");
      if (azione === "auto") azione = via ? "indirizzo" : particella ? "particella" : "indirizzo";
      if (comune.length < 2) {
        messaggio(azione === "particella" ? "Scrivi il comune (il primo campo), poi foglio e particella."
          : via ? "Scrivi anche il comune (il primo campo)." : "Scrivi il comune (e, se vuoi, l'indirizzo o foglio e particella).", true);
        f.querySelector("#cerca-comune").focus();
        return;
      }
      if (azione === "indirizzo") {
        if (via.length < 3) { vaiAlComune(comune); return; }          // solo il comune: al centro, senza server
        vai({ indirizzo: via, comune });
        return;
      }
      if (!particella) { vaiAlComune(comune); return; }
      vai({ comune, foglio, particella });
    }
    bInd.addEventListener("click", () => esegui("indirizzo"));
    bPar.addEventListener("click", () => esegui("particella"));
    bReset.addEventListener("click", () => { f.reset(); f.querySelectorAll("input").forEach((i) => { i.value = ""; }); messaggio(""); });
    // Invio: secondo il campo in cui si scrive (con quattro campi di testo e nessun pulsante «submit» il modulo non si invia da sé)
    const PER_CAMPO = { "cerca-via": "indirizzo", "catasto-foglio": "particella", "catasto-particella": "particella", "cerca-comune": "auto" };
    f.addEventListener("keydown", (e) => {
      if (e.key !== "Enter" || !e.target || !PER_CAMPO[e.target.id]) return;
      e.preventDefault();
      esegui(PER_CAMPO[e.target.id]);
    });
    f.addEventListener("submit", (e) => { e.preventDefault(); esegui("auto"); });
    return { messaggio, esegui };
  }

  const ZOOM = 17;
  const ZOOM_PARTICELLA = 19;            // (17/11/2026) zoom massimo sulla particella del civico (particelle piccole)
  const ZOOM_LOCALITA = 15;              // località (frazione) scelta dall'elenco: nessun riquadro
  const PARTENZA = { lon: 12.2597, lat: 44.1326, zoom: 15.6, nome: "Cesena, ospedale Bufalini (viale Ghirotti 286)" };
  // vale la partenza su Cesena? No se l'indirizzo porta un punto, una sede, un edificio, un modello o un file, o se la
  // regione scelta (?regione= o ricordata dalla piccola mappa) non è l'Emilia-Romagna
  function partenzaLibera() {
    const q = new URLSearchParams(location.search);
    if (["lat", "lon", "sede", "edificio", "modello", "dbtr", "archivio"].some((k) => q.get(k))) return false;
    const r = (window.EUGENIO && window.EUGENIO.regione) || q.get("regione") || "08";
    return String(r).padStart(2, "0") === "08";
  }
  window.EUGENIO_CERCA = { crea, cerca, messaggio, centroComune, inquadra, ZOOM, ZOOM_COMUNE, ZOOM_PARTICELLA, ZOOM_LOCALITA, PARTENZA, partenzaLibera };
})();
