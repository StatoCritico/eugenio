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
    if (!x || !Number.isFinite(+x.lat) || !Number.isFinite(+x.lon)) {
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
    f1.append(campo("Indirizzo", "cerca-via", { autocomplete: "street-address", placeholder: "via Gambalunga 27" }),
      campo("Comune", "cerca-comune", { autocomplete: "address-level2", placeholder: "Rimini" }));
    const b1 = h("button", "bottone secondario", "Cerca l'indirizzo"); b1.type = "submit"; f1.appendChild(b1);
    const f2 = h("form", "riga-campi"); f2.id = "cerca-catasto";
    f2.append(campo("Comune", "catasto-comune", { placeholder: "Rimini" }), campo("Foglio", "catasto-foglio", { inputmode: "numeric", size: "5" }),
      campo("Particella", "catasto-particella", { inputmode: "numeric", size: "6" }));
    const b2 = h("button", "bottone secondario", "Cerca la particella"); b2.type = "submit"; f2.appendChild(b2);
    const aiuto = h("p", "aiuto");
    aiuto.append("Gli indirizzi si cercano prima nell'archivio nazionale dei civici ANNCSU (Agenzia delle Entrate e ISTAT, CC BY 4.0) e, "
      + "se mancano, con la geocodifica di Zornade; foglio e particella con le particelle catastali di Zornade, come nella pagina ");
    const a = h("a", null, "Patrimonio"); a.href = "patrimonio.html"; aiuto.append(a, ". I dati catastali non sostituiscono visure ed estratti ufficiali.");
    msg = h("div", "messaggio"); msg.id = "messaggio-cerca"; msg.setAttribute("role", "status"); msg.setAttribute("aria-live", "polite");
    dove.append(f1, f2, aiuto, msg);
    const vai = async (campi) => {
      if (opz.prima) opz.prima();
      const t = await cerca(campi);
      if (t && opz.suTrovato) await opz.suTrovato(t.lon, t.lat, t.riga);
    };
    f1.addEventListener("submit", (e) => {
      e.preventDefault();
      const via = f1.querySelector("#cerca-via").value.trim(), comune = f1.querySelector("#cerca-comune").value.trim();
      if (via.length < 3 || comune.length < 2) { messaggio("Scrivi via e civico e il comune.", true); return; }
      vai({ indirizzo: via, comune });
    });
    f2.addEventListener("submit", (e) => {
      e.preventDefault();
      const comune = f2.querySelector("#catasto-comune").value.trim(), particella = f2.querySelector("#catasto-particella").value.trim();
      if (comune.length < 2 || !particella) { messaggio("Scrivi il comune e la particella (e, se lo sai, il foglio).", true); return; }
      vai({ comune, foglio: f2.querySelector("#catasto-foglio").value.trim(), particella });
    });
    return { messaggio };
  }

  window.EUGENIO_CERCA = { crea, cerca, messaggio };
})();
