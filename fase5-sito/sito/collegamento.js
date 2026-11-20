"use strict";
// Collegamento a questa simulazione (20/11/2026, richiesta di Paolo).
//
// Nelle pagine che funzionano a scelte (niente file caricati) lo stato della pagina sta nella query string
// dell'indirizzo, con parametri leggibili e nomi brevi in italiano. In fondo alla pagina c'è un riquadro con
// l'indirizzo completo (campo di sola lettura) e il pulsante «Copia»: si aggiorna da solo a ogni modifica e,
// riaprendolo, la pagina riparte dalle stesse scelte. Tutto nel browser: niente va al server, niente file caricati,
// niente dati personali né segreti.
//
// Uso in una pagina (regole in README_stile.md § «Collegamento a questa simulazione»):
//   1. <script src="collegamento.js?v=…"></script> prima dello script della pagina;
//   2. controlli semplici (input, select, textarea con un id): attributo data-collegamento="nome" (vuoto = l'id);
//      i radio con lo stesso name: data-collegamento="nome" su ciascuno. Il modulo li legge e li rimette da solo,
//      nell'ordine della pagina, aspettando le opzioni dei menu che arrivano dopo (regione → comune → ente…);
//   3. scelte non fatte con controlli semplici (mappa, pulsanti, elenchi): una registrazione
//        EUGENIO_COLLEGAMENTO.registra({
//          chiavi: ["comune", "vista"],          // parametri gestiti (per toglierli quando la scelta sparisce)
//          principali: ["comune"],               // restano anche se l'indirizzo è troppo lungo
//          leggi: () => ({ comune: stato.istat, vista: stato.vista }),   // valore null, undefined o "" = parametro tolto;
//                                                // leggi() che restituisce null = pagina non pronta, parametri lasciati
//          applica: async (p) => { … },          // p: URLSearchParams dell'indirizzo aperto
//          pronto: () => stato.dati !== null,    // facoltativo: si aspetta prima di rimettere controlli e scelte
//          primaDeiControlli: true,              // facoltativo: applica prima dei controlli data-collegamento
//        });
//      e, dopo una scelta che non passa da un evento input/change/click, EUGENIO_COLLEGAMENTO.aggiorna().
//   I parametri che la pagina scrive già da sé (?regione=, ?comune=, ?vista=italia, ?prova=1…) restano: il modulo
//   aggiunge e toglie solo i suoi.
(function () {
  const LIMITE = 2000;                 // caratteri oltre i quali un indirizzo rischia di non funzionare ovunque
  const RITARDO = 350;                 // ms tra due riscritture dell'indirizzo (non a ogni tasto)
  const ATTESA_OPZIONI = 15000;        // ms: quanto si aspetta un'opzione di un menu caricato dopo
  const registrazioni = [];
  const sostituisci = history.replaceState.bind(history);
  const CHIAVE_USCITA = "eugenio-collegamento-uscita";
  // pagina lasciata da pochi secondi con l'indirizzo non ancora riscritto (ricarica subito dopo una scelta): prima che gli
  // script della pagina leggano l'indirizzo, si rimette quello giusto
  try {
    const u = JSON.parse(sessionStorage.getItem(CHIAVE_USCITA) || "null");
    sessionStorage.removeItem(CHIAVE_USCITA);
    if (u && u.percorso === location.pathname && u.vecchio === location.search && Date.now() - u.quando < 10000) {
      sostituisci(history.state, "", location.pathname + u.nuovo + location.hash);
    }
  } catch { /* sessionStorage non disponibile */ }
  let ripristino = true;               // durante il ripristino non si scrive niente
  let timer = 0, box = null, campo = null, stato = null, avviso = null;
  let ridotto = false;

  // ---------------------------------------------------------------- controlli semplici (data-collegamento)
  function controlli() {
    return [...document.querySelectorAll("input[data-collegamento], select[data-collegamento], textarea[data-collegamento]")]
      .filter((e) => e.type !== "file" && e.type !== "password" && e.type !== "email" && !e.closest(".collegamento-simulazione"));
  }
  const nome = (e) => e.dataset.collegamento || (e.type === "radio" ? e.name : e.id);
  function valore(e) {
    if (e.type === "checkbox") return e.checked ? "1" : "0";
    if (e.type === "radio") {
      const scelto = document.querySelector(`input[type=radio][name="${CSS.escape(e.name)}"]:checked`);
      return scelto ? scelto.value : "";
    }
    if (e.multiple) return [...e.selectedOptions].map((o) => o.value).join(",");
    return e.value;
  }
  function leggiControlli() {
    const out = {};
    for (const e of controlli()) {
      if (e.disabled && e.dataset.collegamentoSempre === undefined) continue;
      const k = nome(e);
      if (k && !(k in out)) out[k] = valore(e);
    }
    return out;
  }
  const attendi = (ms) => new Promise((r) => setTimeout(r, ms));
  function eventi(e) {
    e.dispatchEvent(new Event("input", { bubbles: true }));
    e.dispatchEvent(new Event("change", { bubbles: true }));
  }
  // un menu caricato dopo (fetch): si aspetta che compaia l'opzione, al più ATTESA_OPZIONI
  function opzionePronta(sel, v) {
    const c = () => v.split(",").every((x) => [...sel.options].some((o) => o.value === x));
    if (c()) return Promise.resolve(true);
    return new Promise((ris) => {
      const fine = (ok) => { mo.disconnect(); clearTimeout(t); ris(ok); };
      const mo = new MutationObserver(() => { if (c()) fine(true); });
      mo.observe(sel, { childList: true, subtree: true });
      const t = setTimeout(() => fine(c()), ATTESA_OPZIONI);
    });
  }
  async function applicaControllo(e, v) {
    if (e.type === "checkbox") {
      const c = v === "1" || v === "true" || v === "si" || v === "sì";
      if (e.checked !== c) { e.checked = c; eventi(e); }
      return;
    }
    if (e.type === "radio") {
      const r = document.querySelector(`input[type=radio][name="${CSS.escape(e.name)}"][value="${CSS.escape(v)}"]`);
      if (r && !r.checked) { r.checked = true; eventi(r); }
      return;
    }
    if (e.tagName === "SELECT") {
      if (!(await opzionePronta(e, v))) return;
      if (e.multiple) [...e.options].forEach((o) => { o.selected = v.split(",").includes(o.value); });
      else if (e.value === v) return;
      else e.value = v;
      eventi(e);
      return;
    }
    if (e.value !== v) { e.value = v; eventi(e); }
  }
  async function applicaControlli(p) {
    const fatti = new Set();
    for (const e of controlli()) {
      const k = nome(e);
      if (!k || fatti.has(k) || !p.has(k)) continue;
      fatti.add(k);
      try {
        await applicaControllo(e, p.get(k));
        await attendi(0);
      } catch (err) { console.warn("collegamento:", k, err); }
    }
  }

  // ---------------------------------------------------------------- indirizzo
  function statoPagina() {
    const valori = {}, gestite = new Set(), principali = new Set();
    for (const e of controlli()) {
      const k = nome(e);
      if (!k) continue;
      gestite.add(k);
      if (e.dataset.collegamentoSecondario === undefined) principali.add(k);
    }
    Object.assign(valori, leggiControlli());
    for (const r of registrazioni) {
      let v = {};
      try { v = r.leggi ? r.leggi() : {}; } catch (err) { console.warn("collegamento: leggi", err); v = null; }
      if (v === null || v === undefined) continue;     // pagina non ancora pronta: i suoi parametri restano come sono
      (r.chiavi || []).forEach((k) => gestite.add(k));
      (r.principali || r.chiavi || []).forEach((k) => principali.add(k));
      for (const [k, x] of Object.entries(v)) {
        gestite.add(k);
        if (!r.principali && !r.chiavi) principali.add(k);
        valori[k] = x;
      }
    }
    // la regione della piccola mappa: nell'indirizzo, così vale anche per chi non l'ha ricordata nel browser
    const reg = window.EUGENIO && window.EUGENIO.regione;
    if (reg && !registrazioni.some((r) => r.regione === false) && /^\d{2}$/.test(reg)) {
      if (!("regione" in valori)) valori.regione = reg;
      gestite.add("regione"); principali.add("regione");
    }
    return { valori, gestite, principali };
  }
  function costruisci(soloPrincipali) {
    const { valori, gestite, principali } = statoPagina();
    const u = new URL(location.href);
    u.hash = "";
    for (const k of gestite) {
      const v = valori[k];
      if (v === null || v === undefined || v === "" || (soloPrincipali && !principali.has(k))) u.searchParams.delete(k);
      else u.searchParams.set(k, String(v));
    }
    return u;
  }
  function indirizzo() {
    let u = costruisci(false);
    ridotto = false;
    if (u.href.length > LIMITE) { u = costruisci(true); ridotto = true; }
    return u;
  }
  function mostra(u) {
    if (!campo) return;
    campo.value = u.href;
    if (avviso) avviso.hidden = !ridotto;
  }
  function scrivi() {
    timer = 0;
    if (ripristino) return;
    ultima = Date.now();
    const u = indirizzo();
    const ora = new URL(location.href);
    if (u.search !== ora.search) {
      u.hash = ora.hash;
      try { sostituisci(history.state, "", u); } catch { /* file:// o browser senza history */ }
    }
    mostra(u);
  }
  // al più una riscrittura ogni RITARDO ms: la prima subito (appena la pagina ha finito di gestire l'evento), le altre in
  // coda; così un clic o una scelta finiscono nell'indirizzo prima di un eventuale «ricarica», e scrivere di seguito in un
  // campo non riscrive l'indirizzo a ogni tasto (Chrome limita anche il numero di replaceState)
  let ultima = 0;
  function aggiorna(subito) {
    if (timer) clearTimeout(timer);
    timer = 0;
    if (subito) { scrivi(); return; }
    timer = setTimeout(scrivi, Math.max(0, RITARDO - (Date.now() - ultima)));
  }
  // la pagina (o la piccola mappa) cambia l'indirizzo da sé: il campo la segue
  history.replaceState = function (...a) {
    const r = sostituisci(...a);
    if (!ripristino) aggiorna(); else if (campo) mostra(indirizzo());
    return r;
  };

  // ---------------------------------------------------------------- riquadro in fondo alla pagina
  function h(tag, cls, testo) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (testo) e.textContent = testo;
    return e;
  }
  function posto() {
    const dato = document.getElementById("collegamento-simulazione");
    if (dato) return { dentro: dato };
    const main = document.querySelector("main");
    if (!main) return null;
    const pannello = main.querySelector(":scope > .pannello");
    const colonna = pannello || main;
    // prima di «Nello stesso gruppo» (titolo #stesso-gruppo) se c'è, altrimenti in fondo al pannello o all'articolo
    const stesso = colonna.querySelector(":scope > #stesso-gruppo");
    return stesso ? { prima: stesso } : { dentro: colonna };
  }
  function creaRiquadro() {
    const p = posto();
    if (!p) return;
    box = h("section", "collegamento-simulazione");
    box.setAttribute("aria-labelledby", "titolo-collegamento");
    const t = h("h2", "collegamento-titolo", "Collegamento a questa simulazione");
    t.id = "titolo-collegamento";
    const riga = h("div", "collegamento-riga");
    campo = h("input", "collegamento-campo");
    campo.type = "text"; campo.readOnly = true; campo.id = "collegamento-indirizzo";
    campo.setAttribute("aria-label", "Indirizzo di questa simulazione");
    campo.spellcheck = false;
    campo.addEventListener("focus", () => campo.select());
    const copia = h("button", "bottone secondario collegamento-copia", "Copia");
    copia.type = "button"; copia.id = "collegamento-copia";
    stato = h("span", "collegamento-esito");
    stato.setAttribute("role", "status"); stato.setAttribute("aria-live", "polite");
    copia.addEventListener("click", copiaIndirizzo);
    riga.append(campo, copia, stato);
    const aiuto = h("p", "aiuto collegamento-aiuto",
      "Salvalo o mandalo: riaprendolo la pagina riparte con le stesse scelte; non contiene file caricati.");
    avviso = h("p", "aiuto collegamento-avviso",
      "Le scelte sono troppe per un indirizzo: il collegamento contiene solo quelle principali.");
    avviso.hidden = true;
    box.append(t, riga, aiuto, avviso);
    if (p.prima) p.prima.before(box); else p.dentro.appendChild(box);
  }
  async function copiaIndirizzo() {
    aggiorna(true);
    const testo = campo.value;
    let ok = false;
    try {
      if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(testo); ok = true; }
    } catch { ok = false; }
    if (!ok) {
      try {
        campo.focus(); campo.select(); campo.setSelectionRange(0, testo.length);
        ok = document.execCommand("copy");
      } catch { ok = false; }
    }
    stato.textContent = ok ? "Copiato" : "Copia non riuscita: seleziona l'indirizzo e copialo a mano (Ctrl+C)";
    stato.classList.toggle("errore", !ok);
    clearTimeout(copiaIndirizzo.t);
    copiaIndirizzo.t = setTimeout(() => { stato.textContent = ""; }, 4000);
  }

  // ---------------------------------------------------------------- avvio: ripristino delle scelte, poi ascolto
  let fineRipristino;
  const ripristinato = new Promise((r) => { fineRipristino = r; });
  async function avvia() {
    creaRiquadro();
    await attendi(0);                  // gli script della pagina hanno finito la parte sincrona
    const p = new URLSearchParams(location.search);
    const dalCollegamento = [...p.keys()].length > 0;
    if (dalCollegamento) {
      // pagine che si preparano in modo asincrono (dati, ascoltatori dei controlli): si aspetta che siano pronte
      for (const r of registrazioni.filter((x) => x.pronto)) await quando(r.pronto);
      for (const r of registrazioni.filter((x) => x.primaDeiControlli)) await applicaRegistrazione(r, p);
      await applicaControlli(p);
      for (const r of registrazioni.filter((x) => !x.primaDeiControlli)) await applicaRegistrazione(r, p);
    }
    ripristino = false;
    document.documentElement.dataset.collegamentoPronto = "";
    fineRipristino();
    // dopo il ripristino da un collegamento l'indirizzo resta quello aperto (più eventuali parametri mancanti);
    // senza parametri non lo si tocca finché l'utente non cambia qualcosa
    if (dalCollegamento) aggiorna(true); else mostra(indirizzo());
  }
  async function applicaRegistrazione(r, p) {
    if (!r.applica) return;
    try { await r.applica(p); } catch (err) { console.warn("collegamento: applica", err); }
  }
  // eventi da non contare: il riquadro stesso, i campi di file, la testata con il menu e il piè (non sono scelte)
  const FUORI = ".collegamento-simulazione, .testata, header, footer, nav.riga-fissata, .menu-pannello";
  const nostro = (ev) => { const t = ev.target; return !t || !t.closest || !!t.closest(FUORI) || t.type === "file"; };
  // fase di cattura: arriva sempre (anche con stopPropagation), ma prima della pagina → riscrittura in coda
  function ascolta(ev) { if (!nostro(ev)) aggiorna(); }
  ["input", "change", "click"].forEach((n) => document.addEventListener(n, ascolta, true));
  // fase di risalita sulla finestra: la pagina ha già aggiornato il suo stato → scelte e clic vanno nell'indirizzo subito;
  // i tasti e i cursori (input) al più ogni RITARDO ms
  function subito(ev) {
    if (nostro(ev) || ripristino) return;
    if (ev.type !== "input" || Date.now() - ultima >= RITARDO) aggiorna(true);
  }
  ["input", "change", "click"].forEach((n) => addEventListener(n, subito));
  // ricarica o «indietro» subito dopo una scelta, prima che l'indirizzo sia riscritto: l'indirizzo nuovo resta nella scheda
  // (sessionStorage) e la pagina riaperta con quello vecchio lo riprende (vedi in cima)
  addEventListener("pagehide", () => {
    if (ripristino) return;
    try {
      const nuovo = indirizzo();
      if (nuovo.search !== location.search) {
        sessionStorage.setItem(CHIAVE_USCITA, JSON.stringify({ percorso: location.pathname, vecchio: location.search, nuovo: nuovo.search, quando: Date.now() }));
      }
    } catch { /* sessionStorage non disponibile */ }
  });
  // i risultati arrivano dopo un clic (fetch): si rilegge anche un po' dopo
  document.addEventListener("click", (ev) => { if (!nostro(ev)) setTimeout(() => aggiorna(), 1200); }, true);

  // registrazione arrivata dopo il ripristino (pagina che si prepara in modo asincrono): si applica subito
  const iniziali = new URLSearchParams(location.search);
  async function tardiva(r) {
    if (!r.applica || ![...iniziali.keys()].length) { aggiorna(); return; }
    ripristino = true;
    await applicaRegistrazione(r, iniziali);
    ripristino = false;
    aggiorna(true);
  }
  // aspetta che la pagina sia pronta (dati caricati in modo asincrono), al più `ms`
  async function quando(cond, ms = ATTESA_OPZIONI) {
    const fine = Date.now() + ms;
    while (Date.now() < fine) {
      try { if (cond()) return true; } catch { /* non ancora */ }
      await attendi(60);
    }
    return false;
  }
  window.EUGENIO_COLLEGAMENTO = {
    quando,
    registra(r) { registrazioni.push(r || {}); if (!ripristino) tardiva(r); return r; },
    aggiorna,
    indirizzo: () => indirizzo().href,
    inRipristino: () => ripristino,
    ripristinato,
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", avvia, { once: true });
  else setTimeout(avvia, 0);
})();
