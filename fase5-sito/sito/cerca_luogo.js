"use strict";
// Ricerca di un luogo per indirizzo (via e civico, comune) o per dati catastali (comune, foglio, particella), comune alle
// pagine Modelli 3D e Ortofoto (05/11/2026, seconda pubblicazione: prima era solo in edificio3d.js).
//
// Una riga a POST /api/patrimonio, la stessa rotta della pagina Patrimonio: indirizzi prima nell'ANNCSU (sul server, CC BY
// 4.0), poi, per quello che manca e per le particelle, Zornade. Nessuna dipendenza nuova da Zornade (§ 14.2 aperto). La
// verifica anti-robot (Turnstile) la aggiunge da sé protezione.js, che avvolge fetch.
//
//  EUGENIO_CERCA.crea(contenitore, { suTrovato(lon, lat, riga), prima() })
//    crea i due moduli (indirizzo; comune, foglio, particella), la nota sulle fonti e la riga dei messaggi
//    (id: cerca-indirizzo, cerca-via, cerca-comune, cerca-catasto, catasto-comune, catasto-foglio, catasto-particella,
//    messaggio-cerca). suTrovato riceve il punto e la riga della risposta; prima() si chiama prima di ogni ricerca.
//  EUGENIO_CERCA.cerca({ indirizzo, comune, foglio, particella }) → la riga trovata (o null) e il messaggio scritto.
//  EUGENIO_CERCA.ZOOM: zoom della mappa sul punto trovato, uguale in Modelli 3D e Ortofoto (07/11/2026: 17, l'isolato
//    intero con il segnaposto; prima 18 in tutte e due).
//  (07/11/2026 sera) Solo il comune (senza indirizzo o senza particella): la mappa va al centro del comune (baricentro
//    del confine ISTAT dei file dati/mappa/<regione>.json del sito, nessuna chiamata al server), a ZOOM_COMUNE. Una
//    risposta senza coordinate vere (vuote o 0,0: civico non georeferenziato in ANNCSU né da Zornade, Novafeltria) non
//    è mai un punto: si va al centro del comune con l'avviso. La riga passata a suTrovato ha allora centro_comune = true
//    e zoom = ZOOM_COMUNE.
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
  async function alCentro(comune, perche) {
    const c = await centroComune(comune);
    if (!c) { messaggio(`${perche}Comune «${comune}» non trovato nei confini ISTAT: controlla il nome.`, true); return null; }
    messaggio(`${perche}Ti porto al centro del comune di ${c.nome} (confini ISTAT, CC BY 4.0): avvicinati e sposta il punto `
      + "sull'edificio (trascinalo o fai clic sulla mappa).", !!perche);
    return { lon: c.lon, lat: c.lat, riga: { centro_comune: true, zoom: ZOOM_COMUNE, comune_catasto: c.nome, istat: c.istat,
      indirizzo_trovato: "", fonte_punto: "ISTAT" } };
  }

  async function cerca(campi) {
    const col = ["id", "denominazione", "indirizzo", "civico", "comune", "foglio", "particella"];
    const pulito = (v) => String(v || "").replace(/[;\r\n"]+/g, " ").trim().slice(0, 120);
    const testo = `${col.join(";")}\n${["1", "ricerca", pulito(campi.indirizzo), "", pulito(campi.comune), pulito(campi.foglio), pulito(campi.particella)].join(";")}\n`;
    messaggio("Cerco…");
    const fd = new FormData();
    fd.append("file", new Blob([testo], { type: "text/csv;charset=utf-8" }), "ricerca.csv");
    let r, d = null;
    try { r = await fetch("/api/patrimonio", { method: "POST", body: fd }); } catch { messaggio("Il server non risponde: riprova più tardi.", true); return null; }
    try { d = await r.json(); } catch { /* non JSON */ }
    if (!r.ok) { messaggio(r.status === 503 ? "La ricerca non è attiva su questo server." : `Ricerca non riuscita: ${(d && d.detail) || r.status}.`, true); return null; }
    const x = d && d.righe && d.righe[0];
    if (!x || !vero(x.lat, x.lon) || x.esito === "non_trovato") {
      // senza coordinate (07/11/2026 sera): al centro del comune, se c'è
      if (campi.comune) {
        const perche = campi.indirizzo ? `Indirizzo senza coordinate in ANNCSU né da Zornade${x && x.nota ? ` (${x.nota})` : ""}. `
          : `Particella non trovata${x && x.nota ? ` (${x.nota})` : ""}. `;
        return alCentro(campi.comune, perche);
      }
      messaggio(`Non trovato${x && x.nota ? `: ${x.nota}` : ""}. Controlla il testo o prova con foglio e particella.`, true); return null;
    }
    const lat = +x.lat, lon = +x.lon;
    const dove = [x.indirizzo_trovato, x.comune_catasto].filter(Boolean).join(", ");
    const part = x.mappale ? `particella ${x.foglio_catasto ? `foglio ${x.foglio_catasto}, ` : ""}${x.mappale}` : "";
    const fonte = x.fonte_punto === "ANNCSU" ? "ANNCSU – Agenzia delle Entrate e ISTAT (CC BY 4.0)" : "Dati elaborati da Zornade";
    if (msg) {
      msg.innerHTML = ""; msg.classList.toggle("errore", x.esito !== "ok");
      msg.append(`${x.esito === "ok" ? "Trovato" : "Trovato, da verificare"}: ${[dove, part].filter(Boolean).join(" – ") || `${lat.toFixed(5)}, ${lon.toFixed(5)}`}`
        + `${x.nota ? ` (${x.nota})` : ""}. Fonte: `);
      if (x.fonte_punto === "ANNCSU") msg.append(fonte); else { const a = h("a", null, fonte); a.href = "https://zornade.com"; msg.appendChild(a); }
      msg.append(".");
    }
    return { lon, lat, riga: x };
  }

  function crea(dove, opz = {}) {
    if (!dove) return null;
    dove.classList.add("cerca-edificio");
    const f1 = h("form", "riga-campi"); f1.id = "cerca-indirizzo";
    f1.append(campo("Indirizzo", "cerca-via", { autocomplete: "street-address", placeholder: "viale Ghirotti 286" }),
      campo("Comune", "cerca-comune", { autocomplete: "address-level2", placeholder: "Cesena" }));
    const b1 = h("button", "bottone secondario", "Cerca l'indirizzo"); b1.type = "submit"; f1.appendChild(b1);
    const f2 = h("form", "riga-campi"); f2.id = "cerca-catasto";
    f2.append(campo("Comune", "catasto-comune", { placeholder: "Cesena" }), campo("Foglio", "catasto-foglio", { inputmode: "numeric", size: "5", placeholder: "149" }),
      campo("Particella", "catasto-particella", { inputmode: "numeric", size: "6", placeholder: "387" }));
    const b2 = h("button", "bottone secondario", "Cerca la particella"); b2.type = "submit"; f2.appendChild(b2);
    const aiuto = h("p", "aiuto");
    aiuto.append("Gli indirizzi si cercano prima nell'archivio nazionale dei civici ANNCSU (Agenzia delle Entrate e ISTAT, CC BY 4.0) e, "
      + "se mancano, con la geocodifica di Zornade; foglio e particella con le particelle catastali di Zornade, come nella pagina ");
    const a = h("a", null, "Patrimonio"); a.href = "patrimonio.html"; aiuto.append(a, ". I dati catastali non sostituiscono visure ed estratti ufficiali.");
    msg = h("div", "messaggio"); msg.id = "messaggio-cerca"; msg.setAttribute("role", "status"); msg.setAttribute("aria-live", "polite");
    dove.append(f1, f2, aiuto, msg);
    const vaiAlComune = async (comune) => {
      if (opz.prima) opz.prima();
      messaggio("Cerco il comune…");
      const t = await alCentro(comune, "");
      if (t && opz.suTrovato) await opz.suTrovato(t.lon, t.lat, t.riga);
    };
    const vai = async (campi) => {
      if (opz.prima) opz.prima();
      const t = await cerca(campi);
      if (t && opz.suTrovato) await opz.suTrovato(t.lon, t.lat, t.riga);
    };
    f1.addEventListener("submit", (e) => {
      e.preventDefault();
      const via = f1.querySelector("#cerca-via").value.trim(), comune = f1.querySelector("#cerca-comune").value.trim();
      if (comune.length < 2) { messaggio(via ? "Scrivi anche il comune." : "Scrivi il comune (e, se vuoi, via e civico).", true); return; }
      if (via.length < 3) { vaiAlComune(comune); return; }          // solo il comune: al centro, senza server
      vai({ indirizzo: via, comune });
    });
    f2.addEventListener("submit", (e) => {
      e.preventDefault();
      const comune = f2.querySelector("#catasto-comune").value.trim(), particella = f2.querySelector("#catasto-particella").value.trim();
      if (comune.length < 2) { messaggio("Scrivi il comune e la particella (e, se lo sai, il foglio).", true); return; }
      if (!particella) { vaiAlComune(comune); return; }
      vai({ comune, foglio: f2.querySelector("#catasto-foglio").value.trim(), particella });
    });
    return { messaggio };
  }

  const ZOOM = 17;
  const PARTENZA = { lon: 12.2597, lat: 44.1326, zoom: 15.6, nome: "Cesena, ospedale Bufalini (viale Ghirotti 286)" };
  // vale la partenza su Cesena? No se l'indirizzo porta un punto, una sede, un edificio, un modello o un file, o se la
  // regione scelta (?regione= o ricordata dalla piccola mappa) non è l'Emilia-Romagna
  function partenzaLibera() {
    const q = new URLSearchParams(location.search);
    if (["lat", "lon", "sede", "edificio", "modello", "dbtr", "archivio"].some((k) => q.get(k))) return false;
    const r = (window.EUGENIO && window.EUGENIO.regione) || q.get("regione") || "08";
    return String(r).padStart(2, "0") === "08";
  }
  window.EUGENIO_CERCA = { crea, cerca, messaggio, centroComune, ZOOM, ZOOM_COMUNE, PARTENZA, partenzaLibera };
})();
