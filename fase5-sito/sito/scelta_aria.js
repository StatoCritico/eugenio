"use strict";
// Passo 1 comune alle pagine «Trattamento aria» (14/11/2026): comune scelto sulla mappa della regione (stessi componenti
// di Legge 10 e Previsioni: minimappa.js per la piccola mappa d'Italia, la mappa grande e i riquadretti) o dall'elenco,
// e la serie meteo oraria con il cursore a scatti «ultimo anno · 2 · 5 · 10 · 20 · tutta la serie».
//  - la scelta (comune e anni) resta nel browser (localStorage «eugenio-aria-v1», in try/catch) ed è la stessa nelle
//    quattro pagine; ?comune=ISTAT nell'indirizzo come in Legge 10;
//  - la serie arriva da GET /api/psicro/serie/{istat}?anni=N (rotta aperta, senza Turnstile) con una copia in memoria per
//    comune e anni; T in decimi di °C e UR in % diventano Float32Array (NaN dove manca il dato);
//  - a ogni serie nuova (o tolta: serie null) l'evento «eugenio:aria-serie» su document e le funzioni passate a su();
//  - modo di prova: ?prova=1 nell'indirizzo (o window.EUGENIO_ARIA_PROVA = true prima dello script, o { prova: true }):
//    una serie oraria sintetica realistica (cicli annuale e giornaliero di T e UR, simile a Milano) generata nel browser,
//    scritta chiaramente come «dati sintetici di prova», così le pagine funzionano anche senza server.
(function () {
  const CHIAVE = "eugenio-aria-v1";
  const ANNI = [1, 2, 5, 10, 20, 0];
  const ETICHETTE = ["ultimo anno", "2", "5", "10", "20", "tutta la serie"];
  const ORA = 3600000;
  const NS = "http://www.w3.org/2000/svg";
  const parametri = new URLSearchParams(location.search);
  const fmt = (n, d = 0) => Number(n).toLocaleString("it-IT", { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: "always" });   // 8.760 ore
  const data = (ms) => new Date(ms).toLocaleDateString("it-IT", { day: "2-digit", month: "2-digit", year: "numeric", timeZone: "Europe/Rome" });
  function h(tag, cls, testo) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (testo !== undefined && testo !== null) e.textContent = testo;
    return e;
  }
  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if ((k === "fill" || k === "stroke") && typeof v === "string" && v.startsWith("var(")) e.style.setProperty(k, v);
      else e.setAttribute(k, v);
    }
    if (parent) parent.appendChild(e);
    return e;
  }
  function leggi() { try { return JSON.parse(localStorage.getItem(CHIAVE) || "null") || {}; } catch (e) { return {}; } }
  // si scrive sempre fondendo con quello che c'è (comune e anni del passo 1, livelli di progetto…)
  function scrivi(v) { try { localStorage.setItem(CHIAVE, JSON.stringify({ ...leggi(), ...v })); } catch (e) { /* navigazione privata */ } }

  // ------------------------------------------------------------------ serie: normalizzazione e dati di prova
  function normalizza(j, opz = {}) {
    const n = j.n || (j.t ? j.t.length : 0);
    const t = new Float32Array(n), ur = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const a = j.t[i], b = j.ur[i];
      t[i] = a === null || a === undefined ? NaN : a / 10;
      ur[i] = b === null || b === undefined ? NaN : b;
    }
    const inizio = typeof j.inizio === "number" ? j.inizio : Date.parse(String(j.inizio).endsWith("Z") ? j.inizio : `${j.inizio}Z`);
    let mancanti = 0;
    for (let i = 0; i < n; i++) if (!(t[i] === t[i]) || !(ur[i] === ur[i])) mancanti++;
    const P = window.EUGENIO_PSICRO;
    const p = Number.isFinite(j.pressione_pa) ? j.pressione_pa : (P ? P.pressione(j.quota_m || 0) : 101325);
    return { istat: j.istat, comune: j.comune, quota_m: j.quota_m, pressione_pa: p, p, inizio, n, passo_h: j.passo_h || 1, t, ur,
      fine: inizio + (n - 1) * ORA, dal: j.dal, al: j.al, anni_richiesti: j.anni_richiesti, anni_dati: j.anni_dati,
      fonte: j.fonte || "", licenza: j.licenza || "", note: j.note || [], mancanti, sintetica: !!opz.sintetica };
  }

  // generatore deterministico (mulberry32) per i dati di prova
  function casuale(seme) {
    let a = seme >>> 0;
    return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  function gauss(r) { let u = 0, v = 0; while (u === 0) u = r(); while (v === 0) v = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); }
  // serie oraria sintetica «simile a Milano»: T media 13,5 °C, escursione annua ±10,5 °C (minimo a metà gennaio),
  // escursione giornaliera più ampia d'estate (massimo alle 15 ora solare, minimo alle 5), anomalie di più giorni
  // (processo autoregressivo); il punto di rugiada segue la media del giorno con uno scarto più grande d'estate e di giorno.
  function serieProva(istat, anni, opz = {}) {
    const r = casuale(Number(String(istat || "15146").replace(/\D/g, "")) || 15146);
    const fine = Math.floor((opz.fine || Date.now()) / ORA) * ORA - 2 * ORA;
    const da = anni ? Date.UTC(new Date(fine).getUTCFullYear() - anni, new Date(fine).getUTCMonth(), new Date(fine).getUTCDate(), new Date(fine).getUTCHours()) + ORA
      : Date.UTC(1991, 0, 1);
    const n = Math.round((fine - da) / ORA) + 1;
    const t = new Array(n), ur = new Array(n);
    const P = window.EUGENIO_PSICRO;
    const psat = P ? P.psat : (x) => 610.94 * Math.exp(17.625 * x / (x + 243.04));
    let anomalia = 0, umida = 0, giornoPrima = -1, rumore = 0;
    for (let i = 0; i < n; i++) {
      const ms = da + i * ORA, d = new Date(ms);
      const inizioAnno = Date.UTC(d.getUTCFullYear(), 0, 1), doy = (ms - inizioAnno) / 86400000;
      const giorno = Math.floor(ms / 86400000);
      if (giorno !== giornoPrima) {
        anomalia = 0.78 * anomalia + gauss(r) * 1.9;
        umida = 0.7 * umida + gauss(r) * 1.4;
        giornoPrima = giorno;
      }
      const stag = -Math.cos(2 * Math.PI * (doy - 15) / 365.25);           // −1 a metà gennaio, +1 a metà luglio
      const oraSolare = (d.getUTCHours() + 1) % 24;
      const estate = (stag + 1) / 2;
      const escurs = 3 + 3.5 * estate;
      const gg = Math.cos(2 * Math.PI * (oraSolare - 15) / 24) * 0.8 + Math.cos(4 * Math.PI * (oraSolare - 15) / 24) * 0.2;
      rumore = 0.6 * rumore + gauss(r) * 0.35;
      const media = 13.5 + 10.5 * stag + anomalia;
      const T = media + escurs * gg + rumore;
      const depressione = Math.max(0.3, 2.2 + 3.8 * estate + umida + 0.9 * escurs * Math.max(0, gg));
      const Td = Math.min(T, media - 1.2 + 1.5 * estate - depressione + escurs * 0.35 * gg + 0.6 * gauss(r));
      const U = Math.max(12, Math.min(100, 100 * psat(Td) / psat(T)));
      t[i] = Math.round(T * 10);
      ur[i] = Math.round(U);
    }
    for (let k = 0; k < Math.floor(n / 5000); k++) { const i = Math.floor(r() * n); t[i] = null; ur[i] = null; }   // qualche buco
    const iso = (ms) => new Date(ms).toISOString().slice(0, 13) + ":00Z";
    const anniDati = anni || Math.floor((n - 1) / 8766 + 1e-6);
    return normalizza({ istat, comune: opz.comune || "Comune di prova", quota_m: 120, pressione_pa: P ? P.pressione(120) : 99887,
      inizio: iso(da), passo_h: 1, n, t, ur, dal: iso(da).slice(0, 10), al: iso(fine).slice(0, 10), anni_richiesti: anni,
      anni_dati: anni ? Math.min(anni, anniDati) : anniDati,
      fonte: "dati sintetici di prova, generati nel browser (non reali)", licenza: "—",
      note: ["Dati sintetici di prova: cicli annuale e giornaliero di T e UR simili a Milano, non sono misure."] }, { sintetica: true });
  }

  // ------------------------------------------------------------------ il passo 1
  function crea(opz = {}) {
    const $ = (x) => (typeof x === "string" ? document.querySelector(x) : x);
    const boxMappa = $(opz.mappa || "#mappa"), passo = $(opz.passo || "#scelta-aria");
    const prova = !!(opz.prova || window.EUGENIO_ARIA_PROVA || parametri.get("prova") === "1");
    const E = window.EUGENIO;
    const ricordata = leggi();
    const st = { regione: (E && E.regione) || "08", comuni: new Map(), percorsi: new Map(), istat: null, nome: ricordata.nome || "", prov: ricordata.prov || "",
      anni: ANNI.includes(ricordata.anni) ? ricordata.anni : 10, serie: null, richiesta: 0, zona: null, svg: null };
    const copie = new Map();         // `${istat}|${anni}` → promessa della serie normalizzata
    const ascoltatori = [];

    // controlli del passo
    passo.classList.add("aria-scelta");
    const lc = h("label", null, "Comune"); lc.htmlFor = "aria-comune";
    const sel = h("select"); sel.id = "aria-comune";
    sel.appendChild(Object.assign(h("option", null, "Scegli…"), { value: "" }));
    const cur = h("div", "aria-cursore aria-cursore-serie");
    const lr = h("label", null, "Serie meteo oraria da usare"); lr.htmlFor = "aria-anni";
    const r = document.createElement("input");
    r.type = "range"; r.id = "aria-anni"; r.min = "0"; r.max = String(ANNI.length - 1); r.step = "1"; r.value = String(ANNI.indexOf(st.anni));
    const scala = h("div", "aria-cursore-scala"); scala.setAttribute("aria-hidden", "true");
    ETICHETTE.forEach((t) => scala.appendChild(h("span", null, t)));
    cur.append(lr, r, scala);
    const disp = h("p", "aiuto aria-disponibilita"); disp.setAttribute("aria-live", "polite");
    // note del server sulla serie (14/11/2026): archivio non ancora sul server, anni chiesti e anni disponibili, fonti per
    // periodo, ore senza dati, quota: in vista sotto la riga della disponibilità
    const noteBox = h("ul", "aria-note-serie"); noteBox.setAttribute("aria-live", "polite"); noteBox.hidden = true;
    const msg = h("div", "messaggio"); msg.setAttribute("role", "status"); msg.setAttribute("aria-live", "polite");
    passo.append(lc, sel, cur, disp, noteBox, msg);
    if (prova) {
      const p = h("div", "messaggio attenzione aria-prova");
      p.innerHTML = "<div><b>Dati sintetici di prova</b>Modo di prova (<code>?prova=1</code>): la serie oraria è generata nel browser, non viene dal server e non è reale.</div>";
      passo.prepend(p);
    }
    const testoAnni = (a) => (a === 0 ? "tutta la serie" : a === 1 ? "ultimo anno" : `ultimi ${a} anni`);
    const aggiornaCursore = () => r.setAttribute("aria-valuetext", testoAnni(ANNI[+r.value]));
    aggiornaCursore();

    function messaggio(t, tipo) {
      msg.textContent = t || "";
      msg.classList.toggle("errore", tipo === "errore");
      msg.classList.toggle("attenzione", tipo === "attenzione");
    }
    function ricorda() { scrivi({ istat: st.istat, nome: st.nome, prov: st.prov, anni: st.anni, regione: st.regione }); }

    // -------------------------------------------------------------- mappa della regione
    async function caricaRegione(cod) {
      const rr = await fetch(`dati/mappa/${cod}.json`);
      if (!rr.ok) throw new Error(`mappa non disponibile (${rr.status})`);
      const m = await rr.json();
      st.regione = cod;
      st.comuni.clear(); st.percorsi.clear();
      if (st.svg) st.svg.remove();
      const svg = el("svg", { viewBox: m.viewBox.join(" "), role: "img", "aria-label": "Mappa dei comuni: tocca un comune per sceglierlo" });
      boxMappa.prepend(svg);
      st.svg = svg;
      const g = el("g", {}, svg);
      for (const c of m.comuni) {
        const p = el("path", { d: c.d, fill: E && E.fondoComuni ? E.fondoComuni(cod) : "var(--linea)" }, g);
        p.dataset.nome = c.nome; p.dataset.prov = c.prov;
        p.addEventListener("click", () => alterna(c.istat));
        st.percorsi.set(c.istat, p);
        st.comuni.set(c.istat, c);
      }
      if (m.province) {
        const gp = el("g", { class: "province" }, svg);
        for (const pr of m.province) el("path", { d: pr.d }, gp);
      }
      if (E) {                                  // Italia sotto, confini regionali sopra, zoom e trascinamento (come dati.js)
        E.sfondoItalia(svg).catch(() => {});
        E.mappaGrande(svg, m.viewBox);
      }
      sel.length = 1;
      [...m.comuni].sort((a, b) => a.nome.localeCompare(b.nome, "it")).forEach((c) => {
        const o = h("option", null, `${c.nome} (${c.prov})`); o.value = c.istat; sel.appendChild(o);
      });
      if (st.istat && st.comuni.has(st.istat)) evidenzia(st.istat);
      else if (st.istat) {                      // comune scelto in un'altra regione: resta scelto, fuori elenco
        const o = h("option", null, `${st.nome}${st.prov ? ` (${st.prov})` : ""}`); o.value = st.istat; sel.appendChild(o);
      }
      sel.value = st.istat || "";
    }
    function evidenzia(istat) {
      st.percorsi.forEach((p) => p.classList.remove("scelto"));
      const p = st.percorsi.get(istat);
      if (p) { p.classList.add("scelto"); p.parentNode.appendChild(p); }
    }
    function alterna(istat) {
      if (E && E.alterna) return E.alterna(istat, st.istat, scegli, togli);
      if (istat === st.istat) togli(); else scegli(istat);
    }

    // -------------------------------------------------------------- scelta e serie
    function scegli(istat) {
      const c = st.comuni.get(istat);
      st.istat = istat;
      if (c) { st.nome = c.nome; st.prov = c.prov; } else if (istat !== ricordata.istat) { st.nome = ""; st.prov = ""; }
      if (!c && ![...sel.options].some((o) => o.value === istat)) {   // comune fuori dalla regione della mappa
        const o = h("option", null, st.nome || `Comune ${istat}`); o.value = istat; sel.appendChild(o);
      }
      evidenzia(istat);
      sel.value = istat;
      const u = new URL(location.href); u.searchParams.set("comune", istat); history.replaceState(null, "", u);
      ricorda();
      st.zonaPronta = zonaClimatica(istat);
      return carica();
    }
    function togli() {
      if (!st.istat) return;
      st.istat = null; st.serie = null; st.richiesta++;
      if (E && E.togliScelto) E.togliScelto(st.percorsi); else st.percorsi.forEach((p) => p.classList.remove("scelto"));
      sel.value = "";
      const u = new URL(location.href); u.searchParams.delete("comune"); history.replaceState(null, "", u);
      ricorda();
      disp.textContent = ""; noteBox.textContent = ""; noteBox.hidden = true; messaggio("");
      annuncia();
    }
    let tabellaDPR = null;
    async function zonaClimatica(istat) {
      try {
        if (!tabellaDPR) tabellaDPR = fetch("dati/dpr412.json?v=20261119e").then((x) => (x.ok ? x.json() : null)).catch(() => null);
        const t = await tabellaDPR, v = t && t.comuni && t.comuni[istat];
        st.zona = Array.isArray(v) && /^[A-F]$/.test(v[1]) ? v[1] : null;
      } catch (e) { st.zona = null; }
      return st.zona;
    }

    function erroreHttp(stato, dettaglio) {
      if (stato === 503) return `L'archivio orario non è ancora disponibile sul server: riprova più tardi.${dettaglio ? ` (${dettaglio})` : ""}`;
      if (stato === 429) return "Troppe richieste in poco tempo dallo stesso indirizzo: riprova tra qualche minuto.";
      if (stato === 404) return `Serie oraria non trovata per questo comune.${dettaglio ? ` (${dettaglio})` : ""}`;
      if (stato === 422) return `Richiesta non valida: ${dettaglio || "numero di anni non accettato"}.`;
      return `Serie non disponibile (errore ${stato})${dettaglio ? `: ${dettaglio}` : ""}.`;
    }
    function scarica(istat, anni) {
      const k = `${istat}|${anni}`;
      if (copie.has(k)) return copie.get(k);
      const pr = (async () => {
        if (prova) {
          await new Promise((ok) => setTimeout(ok, 30));
          return serieProva(istat, anni, { comune: st.nome || "Comune di prova" });
        }
        let rr;
        try { rr = await fetch(`/api/psicro/serie/${encodeURIComponent(istat)}?anni=${anni}`); }
        catch (e) { throw new Error("Server non raggiungibile: controlla la connessione e riprova."); }
        let j = null;
        try { j = await rr.json(); } catch (e) { /* risposta non JSON */ }
        if (!rr.ok) throw new Error(erroreHttp(rr.status, j && (typeof j.detail === "string" ? j.detail : "")));
        if (!j || !Array.isArray(j.t) || !Array.isArray(j.ur)) throw new Error("Risposta del server non valida.");
        return normalizza(j);
      })();
      copie.set(k, pr);
      pr.catch(() => copie.delete(k));          // un errore non resta in memoria: si può riprovare
      return pr;
    }
    async function carica() {
      if (!st.istat) return null;
      const n = ++st.richiesta, anni = st.anni;
      passo.setAttribute("aria-busy", "true");
      messaggio(`Carico la serie oraria${st.nome ? ` di ${st.nome}` : ""} (${testoAnni(anni)})…`);
      try {
        const [s] = await Promise.all([scarica(st.istat, anni), st.zonaPronta]);
        if (n !== st.richiesta) return null;
        if (!st.nome && s.comune) {
          st.nome = s.comune;
          const o = [...sel.options].find((x) => x.value === st.istat);
          if (o && !st.comuni.has(st.istat)) o.textContent = s.comune;
          ricorda();
        }
        st.serie = s;
        messaggio("");
        disponibilita(s, anni);
        annuncia();
        return s;
      } catch (e) {
        if (n !== st.richiesta) return null;
        st.serie = null;
        disp.textContent = ""; noteBox.textContent = ""; noteBox.hidden = true;
        messaggio(e.message || String(e), "errore");
        annuncia();
        return null;
      } finally { if (n === st.richiesta) passo.removeAttribute("aria-busy"); }
    }
    function disponibilita(s, anni) {
      const anniCop = (s.n - 1) / 8766;
      const righe = [`${s.sintetica ? "Dati sintetici di prova" : "Dati"} dal ${data(s.inizio)} al ${data(s.fine)}: ${fmt(anniCop, anniCop < 2 ? 1 : 0)} anni, ${fmt(s.n)} ore`
        + (s.mancanti ? ` (${fmt(s.mancanti)} senza dato).` : ".")];
      const note = (s.note || []).filter(Boolean);
      if (anni && Number.isFinite(s.anni_dati) && s.anni_dati < anni && !note.some((x) => /^Chiest/.test(x)))
        righe.push(`Hai chiesto ${anni} anni: per questo comune ce ne sono ${fmt(s.anni_dati)}, uso tutta la serie disponibile.`);
      if (s.quota_m !== undefined && s.quota_m !== null) righe.push(`Quota ${fmt(s.quota_m)} m, pressione di calcolo ${fmt(s.p)} Pa.`);
      disp.textContent = righe.join(" ");
      if (s.fonte) { disp.appendChild(document.createElement("br")); disp.append(`Fonte: ${s.fonte}${s.licenza && s.licenza !== "—" ? ` (${s.licenza})` : ""}.`); }
      noteBox.textContent = "";
      note.forEach((x) => {
        const li = h("li", /archivio dal 1940/i.test(x) ? "importante" : null, x);
        noteBox.appendChild(li);
      });
      noteBox.hidden = !note.length;
    }
    function dettaglio() {
      return { serie: st.serie, istat: st.istat, comune: st.nome || (st.serie && st.serie.comune) || "", prov: st.prov, regione: st.regione,
        anni: st.anni, zona: st.zona, sintetica: !!(st.serie && st.serie.sintetica), prova };
    }
    function annuncia() {
      const d = dettaglio();
      ascoltatori.forEach((f) => { try { f(d); } catch (e) { console.error(e); } });
      document.dispatchEvent(new CustomEvent("eugenio:aria-serie", { detail: d }));
    }

    sel.addEventListener("change", () => (sel.value ? scegli(sel.value) : togli()));
    r.addEventListener("input", aggiornaCursore);
    r.addEventListener("change", () => { st.anni = ANNI[+r.value]; ricorda(); if (st.istat) carica(); });
    if (E) E.suRegione = (cod) => caricaRegione(cod).catch((e) => messaggio(`Mappa non disponibile: ${e.message}`, "errore"));
    document.addEventListener("eugenio:aspetto", () => {          // fondo dei comuni calcolato: si rifà col tema
      const fondo = E && E.fondoComuni ? E.fondoComuni(st.regione) : null;
      if (fondo) st.percorsi.forEach((p) => p.setAttribute("fill", fondo));
    });

    const pronta = (async () => {
      try { await caricaRegione(st.regione); } catch (e) { messaggio(`Mappa non disponibile: ${e.message}`, "errore"); }
      // in prova, senza una scelta ricordata: il primo capoluogo di provincia della regione che si trova (o il primo comune)
      const capoluogo = () => [...st.comuni.values()].sort((a, b) => a.istat.localeCompare(b.istat))
        .find((c) => /^(Bologna|Milano|Torino|Roma|Napoli|Firenze|Venezia|Genova|Bari|Palermo|Cagliari|Trento|Bolzano|Trieste|Ancona|Perugia|Aosta|L'Aquila|Potenza|Catanzaro|Campobasso)$/.test(c.nome))
        || [...st.comuni.values()][0];
      const daLink = parametri.get("comune");
      const iniziale = daLink || ricordata.istat || (prova && st.comuni.size ? capoluogo().istat : null);
      if (iniziale) {
        if (!st.comuni.has(iniziale) && ricordata.istat === iniziale && ricordata.nome) st.nome = ricordata.nome;
        await scegli(iniziale);
      }
    })();

    const ctrl = {
      pronta,
      su(f) { if (typeof f === "function") ascoltatori.push(f); return ctrl; },
      serie: () => st.serie,
      stato: dettaglio,
      scegli: (istat) => scegli(String(istat)),
      togli,
      anni(a) { if (a === undefined) return st.anni; if (!ANNI.includes(a)) return st.anni; st.anni = a; r.value = String(ANNI.indexOf(a)); aggiornaCursore(); ricorda(); return carica(); },
      prova,
    };
    return ctrl;
  }

  // ------------------------------------------------------------------ livello delle condizioni di progetto
  // Controllo riusabile (14/11/2026, decisione di Paolo): livello invernale (% delle ore con T superiore: scelte rapide
  // 99,6 · 99 · 95 %, predefinito 99 %) ed estivo (% delle ore che superano il valore: 0,4 · 1 · 5 %, predefinito 1 %),
  // più un campo libero («altro»). Scelta ricordata in eugenio-aria-v1 (chiave «livelli»), comune alle quattro pagine;
  // a ogni cambio l'evento «eugenio:aria-livello» su document (detail { inverno, estate }) e le funzioni passate a su().
  // I valori di progetto che ne risultano restano modificabili a mano nelle pagine che li usano.
  let numLivello = 0;
  function livelloProgetto(box, opz = {}) {
    const $ = (x) => (typeof x === "string" ? document.querySelector(x) : x);
    box = $(box);
    if (!box) return null;
    const P = window.EUGENIO_PSICRO;
    const PRED = (P && P.LIVELLI_PREDEFINITI) || { inverno: 99, estate: 1 };
    const SCELTE = (P && P.SCELTE_LIVELLO) || { inverno: [99.6, 99, 95], estate: [0.4, 1, 5] };
    const norm = (o) => (P && P.livelli ? P.livelli(o || {}) : { ...PRED, ...(o || {}) });
    let val = norm({ ...PRED, ...(leggi().livelli || {}), ...(opz.valori || {}) });
    const ascoltatori = [];
    const id = `aria-livello-${++numLivello}`;
    box.classList.add("aria-livello");
    box.innerHTML = "";
    const fs = h("fieldset", "aria-livello-campi");
    fs.appendChild(h("legend", null, opz.titolo || "Livello delle condizioni di progetto"));
    const fmtL = (v) => `${fmt(v, v % 1 ? 1 : 0)} %`;
    const campi = {};
    for (const [k, nome, lim, aiuto] of [["inverno", "Inverno", [50, 100], "% delle ore con temperatura più alta"],
      ["estate", "Estate", [0, 50], "% delle ore che superano il valore"]]) {
      const l = h("label", "aria-campo"); l.htmlFor = `${id}-${k}`;
      l.appendChild(h("span", null, nome));
      const sel = h("select"); sel.id = `${id}-${k}`; sel.title = aiuto;
      SCELTE[k].forEach((v) => { const o = h("option", null, `${fmtL(v)}${v === PRED[k] ? " (predefinito)" : ""}`); o.value = String(v); sel.appendChild(o); });
      const altro = h("option", null, "altro…"); altro.value = "altro"; sel.appendChild(altro);
      const num = document.createElement("input");
      num.type = "text"; num.inputMode = "decimal"; num.size = 5; num.className = "aria-livello-libero";
      num.setAttribute("aria-label", `${nome}: livello in %, tra ${lim[0]} e ${lim[1]} (escluso)`);
      const riga = h("span", "aria-livello-riga");
      riga.append(sel, num, h("span", "aria-livello-unita", "%"));
      l.appendChild(riga);
      fs.appendChild(l);
      campi[k] = { sel, num, lim };
      sel.addEventListener("change", () => {
        if (sel.value === "altro") { num.hidden = false; num.nextSibling.hidden = false; num.focus(); return; }
        imposta({ [k]: Number(sel.value) });
      });
      num.addEventListener("input", () => {
        const v = Number(num.value.replace(",", "."));
        const ok = Number.isFinite(v) && v > lim[0] && v < lim[1];
        num.setAttribute("aria-invalid", ok ? "false" : "true");
        if (ok) imposta({ [k]: v }, true);
      });
    }
    const nota = h("p", "aiuto aria-livello-nota");
    box.append(fs, nota);
    function mostra(daCampo) {
      for (const k of ["inverno", "estate"]) {
        const c = campi[k], v = val[k], rapida = SCELTE[k].includes(v);
        if (!(daCampo && c.sel.value === "altro")) c.sel.value = rapida ? String(v) : "altro";
        const libero = c.sel.value === "altro";
        c.num.hidden = !libero; c.num.nextSibling.hidden = !libero;
        if (libero && !daCampo) c.num.value = fmt(v, v % 1 ? (String(v).split(".")[1] || "").length : 0);
      }
      nota.textContent = `Inverno: temperatura superata nel ${fmtL(val.inverno)} delle ore; estate: valori superati solo ${val.estate < 1 ? "nello" : "nel"} ${fmtL(val.estate)} delle ore (statistiche della serie scelta, non valori di norma).`
        .replace("nel 1 %", "nell'1 %");
    }
    function imposta(o, daCampo) {
      const nuovo = norm({ ...val, ...o });
      const cambiato = nuovo.inverno !== val.inverno || nuovo.estate !== val.estate;
      val = nuovo;
      mostra(daCampo);
      if (!cambiato) return ctrl;
      scrivi({ livelli: val });
      const d = { ...val };
      ascoltatori.forEach((f) => { try { f(d); } catch (e) { console.error(e); } });
      document.dispatchEvent(new CustomEvent("eugenio:aria-livello", { detail: d }));
      return ctrl;
    }
    const ctrl = {
      valori: () => ({ ...val }),
      imposta: (o) => imposta(o || {}),
      predefiniti: () => imposta({ ...PRED }),
      su(f) { if (typeof f === "function") { ascoltatori.push(f); if (opz.subito !== false) f({ ...val }); } return ctrl; },
      elemento: box,
    };
    mostra(false);
    return ctrl;
  }

  window.EUGENIO_SCELTA_ARIA = { crea, livelloProgetto, normalizza, serieProva, ANNI, ETICHETTE, CHIAVE };
})();
