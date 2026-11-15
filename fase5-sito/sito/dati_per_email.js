// Pagina «Dati per email» (14/11/2026, decisione di Paolo): tre servizi separati (mensile per regione, previsioni
// settimanali per fino a 5 comuni, avvisi meteo del giorno dopo), scelti con un collegamento personale spedito per email.
//
// Tre stati, dall'indirizzo della pagina:
//   (niente)    modulo dell'email → POST /api/email/link (verifica anti-robot con protezione.js)
//   #t=<g>      scelte: POST /api/email/leggi, poi POST /api/email/salva
//   #via=<g>    cancellazione da un servizio: POST /api/email/via
// Il gettone resta dopo «#» (non arriva al server nell'indirizzo) e si toglie dalla barra appena letto, così non
// finisce in una cronologia o in una schermata condivisa.
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const API = "/api/email";
  let opzioni = null;
  let gettone = null;
  let comuniItalia = null;
  let scelti = [];                         // [{istat, nome, provincia}]
  const NOMI_SERVIZIO = { mensile: "la newsletter mensile", settimanale: "le previsioni settimanali", avvisi: "gli avvisi meteo" };

  function mostra(id) {
    for (const s of ["dpe-chiedi", "dpe-scelte", "dpe-via", "dpe-spento"]) $(s).hidden = s !== id;
  }

  async function chiama(percorso, corpo) {
    const r = await fetch(API + percorso, corpo === undefined ? {} : {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo) });
    let dati = null;
    try { dati = await r.json(); } catch (e) { /* risposta senza JSON */ }
    if (!r.ok) {
      const err = new Error((dati && dati.detail && (typeof dati.detail === "string" ? dati.detail : "Dati non validi.")) ||
        `Errore ${r.status}: riprova tra poco.`);
      err.stato = r.status;
      throw err;
    }
    return dati;
  }

  function leggiHash() {
    const h = new URLSearchParams(location.hash.replace(/^#/, ""));
    const out = { t: h.get("t"), via: h.get("via") };
    if (out.t || out.via) {
      try { history.replaceState(null, "", location.pathname + location.search); } catch (e) { /* niente */ }
    }
    return out;
  }

  // --------------------------------------------------------------------------- 1. collegamento personale
  function preparaModuloEmail() {
    $("dpe-modulo-email").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const campo = $("dpe-email");
      const email = campo.value.trim();
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
        campo.setAttribute("aria-invalid", "true");
        $("dpe-esito-email").textContent = "Scrivi un indirizzo email valido.";
        return;
      }
      campo.removeAttribute("aria-invalid");
      const b = $("dpe-manda");
      b.setAttribute("aria-busy", "true");
      b.disabled = true;
      try {
        await chiama("/link", { email });
        $("dpe-esito-email").textContent = "Fatto. Se l'indirizzo è giusto, tra pochi minuti ricevi un'email da " +
          "eugenio@statocritico.it con il collegamento (guarda anche nella posta indesiderata).";
      } catch (e) {
        $("dpe-esito-email").textContent = e.message;
        b.disabled = false;
      } finally {
        b.removeAttribute("aria-busy");
      }
    });
  }

  // --------------------------------------------------------------------------- 2. scelte
  function disegnaRegioni(attive) {
    const box = $("dpe-regioni");
    box.textContent = "";
    for (const r of opzioni.regioni) {
      const l = document.createElement("label");
      const c = document.createElement("input");
      c.type = "checkbox";
      c.value = r.cod;
      c.checked = attive.includes(r.cod);
      c.addEventListener("change", limitaRegioni);
      l.append(c, " " + r.nome);
      box.append(l);
    }
    limitaRegioni();
  }

  function regioniScelte() {
    return [...$("dpe-regioni").querySelectorAll("input:checked")].map((c) => c.value);
  }

  function limitaRegioni() {
    const piene = regioniScelte().length >= opzioni.max_regioni;
    for (const c of $("dpe-regioni").querySelectorAll("input")) c.disabled = piene && !c.checked;
  }

  function disegnaAvvisi(attivi) {
    const box = $("dpe-avvisi");
    box.textContent = "";
    for (const a of opzioni.avvisi) {
      const l = document.createElement("label");
      l.className = "dpe-spunta";
      const c = document.createElement("input");
      c.type = "checkbox";
      c.value = a.id;
      c.checked = attivi.includes(a.id);
      const testo = document.createElement("span");
      const s = document.createElement("small");
      s.textContent = ` (${a.soglia})`;
      testo.append(a.nome, s);
      l.append(c, testo);
      box.append(l);
    }
    if (opzioni.avvertenza) $("dpe-avvertenza").textContent = opzioni.avvertenza;
  }

  function disegnaComuni() {
    const ul = $("dpe-comuni");
    ul.textContent = "";
    for (const c of scelti) {
      const li = document.createElement("li");
      li.textContent = c.provincia ? `${c.nome} (${c.provincia}) ` : `${c.nome} `;
      const b = document.createElement("button");
      b.type = "button";
      b.className = "bottone secondario piccolo";
      b.textContent = "Togli";
      b.setAttribute("aria-label", `Togli ${c.nome}`);
      b.addEventListener("click", () => { scelti = scelti.filter((x) => x.istat !== c.istat); disegnaComuni(); });
      li.append(b);
      ul.append(li);
    }
    const pieno = scelti.length >= opzioni.max_comuni;
    $("dpe-cerca").disabled = pieno;
    $("dpe-cerca").placeholder = pieno ? `Hai già ${opzioni.max_comuni} comuni: togline uno per cambiarlo`
      : "nome del comune, per esempio Cesena";
  }

  function normale(s) {
    return (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  async function cercaComuni() {
    const q = normale($("dpe-cerca").value.trim());
    const ul = $("dpe-risultati");
    ul.textContent = "";
    if (q.length < 2) return;
    if (!comuniItalia) {
      try { comuniItalia = await chiama("/comuni"); } catch (e) { return; }
    }
    const presi = new Set(scelti.map((c) => c.istat));
    const trovati = comuniItalia.filter((c) => !presi.has(c.istat) && normale(c.nome).includes(q))
      .sort((a, b) => (normale(a.nome).startsWith(q) ? 0 : 1) - (normale(b.nome).startsWith(q) ? 0 : 1) ||
        a.nome.localeCompare(b.nome, "it"))
      .slice(0, 8);
    for (const c of trovati) {
      const li = document.createElement("li");
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = c.nome + " ";
      const s = document.createElement("small");
      s.textContent = c.provincia || "";
      b.append(s);
      b.addEventListener("click", () => {
        if (scelti.length < opzioni.max_comuni) scelti.push({ istat: c.istat, nome: c.nome, provincia: c.provincia || "" });
        $("dpe-cerca").value = "";
        ul.textContent = "";
        disegnaComuni();
        $("dpe-cerca").focus();
      });
      li.append(b);
      ul.append(li);
    }
  }

  function compila(stato) {
    $("dpe-chi").textContent = `Scelte per ${stato.email}.`;
    $("dpe-mensile").checked = !!stato.mensile;
    $("dpe-settimanale").checked = !!stato.settimanale;
    scelti = (stato.comuni || []).slice();
    disegnaRegioni(stato.regioni || []);
    disegnaAvvisi(stato.avvisi || []);
    disegnaComuni();
  }

  async function apriScelte() {
    mostra("dpe-scelte");
    $("dpe-esito").textContent = "Carico le tue scelte…";
    try {
      compila(await chiama("/leggi", { t: gettone }));
      $("dpe-esito").textContent = "";
    } catch (e) {
      $("dpe-esito").textContent = e.message;
      if (e.stato === 401) { mostra("dpe-chiedi"); $("dpe-esito-email").textContent = e.message; }
    }
  }

  function preparaModuloScelte() {
    let tempo = null;
    $("dpe-cerca").addEventListener("input", () => { clearTimeout(tempo); tempo = setTimeout(cercaComuni, 150); });
    $("dpe-modulo-scelte").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const avvisi = [...$("dpe-avvisi").querySelectorAll("input:checked")].map((c) => c.value);
      const corpo = { t: gettone, mensile: $("dpe-mensile").checked, regioni: regioniScelte(),
                      settimanale: $("dpe-settimanale").checked, comuni: scelti.map((c) => c.istat), avvisi };
      if ((corpo.settimanale || avvisi.length) && !corpo.comuni.length) {
        $("dpe-esito").textContent = "Per le previsioni settimanali e gli avvisi meteo scegli almeno un comune.";
        $("dpe-cerca").focus();
        return;
      }
      const b = $("dpe-salva");
      b.setAttribute("aria-busy", "true");
      b.disabled = true;
      try {
        const stato = await chiama("/salva", corpo);
        compila(stato);
        const attivi = ["mensile", "settimanale"].filter((k) => stato[k]).map((k) => NOMI_SERVIZIO[k]);
        if (stato.avvisi && stato.avvisi.length) attivi.push(NOMI_SERVIZIO.avvisi);
        $("dpe-esito").textContent = attivi.length ? `Salvato. Riceverai ${attivi.join(", ").replace(/, ([^,]*)$/, " e $1")}.`
          : "Salvato: non riceverai più niente da EuGEnio.";
      } catch (e) {
        $("dpe-esito").textContent = e.message;
      } finally {
        b.disabled = false;
        b.removeAttribute("aria-busy");
      }
    });
  }

  // --------------------------------------------------------------------------- 3. cancellazione
  async function cancella(g) {
    mostra("dpe-via");
    try {
      const r = await chiama("/via", { t: g });
      const p = $("dpe-esito-via");
      p.textContent = `Fatto: non riceverai più ${NOMI_SERVIZIO[r.cancellato] || "questo servizio"}. `;
      const a = document.createElement("a");
      a.href = "#" + r.preferenze;
      a.textContent = "Cambia gli altri servizi";
      a.addEventListener("click", (ev) => {
        ev.preventDefault();
        gettone = new URLSearchParams(r.preferenze).get("t");
        apriScelte();
      });
      p.append(a);
    } catch (e) {
      $("dpe-esito-via").textContent = e.message;
    }
  }

  async function avvia() {
    try {
      opzioni = await chiama("/opzioni");
    } catch (e) {
      opzioni = null;
    }
    if (!opzioni || !opzioni.attivo) { mostra("dpe-spento"); return; }
    for (const el of document.querySelectorAll(".dpe-max-regioni")) el.textContent = opzioni.max_regioni;
    for (const el of document.querySelectorAll(".dpe-max-comuni")) el.textContent = opzioni.max_comuni;
    for (const el of document.querySelectorAll(".dpe-giorno")) el.textContent = opzioni.giorno_mensile;
    preparaModuloEmail();
    preparaModuloScelte();
    const h = leggiHash();
    if (h.via) cancella(h.via);
    else if (h.t) { gettone = h.t; apriScelte(); }
    else mostra("dpe-chiedi");
  }

  window.addEventListener("hashchange", () => {
    const h = leggiHash();
    if (h.via) cancella(h.via);
    else if (h.t) { gettone = h.t; apriScelte(); }
  });
  avvia();
})();
