"use strict";
// Trattamento aria › Trasformazioni dell'aria (UTA) (14/11/2026). La pagina replica il foglio psicro_UTA.xlsx
// (fase14-trattamento-aria/foglio, mappa delle celle MAPPA_CELLE.md): dati generali, ESTATE e INVERNO con condizioni di
// progetto, carichi, punto di immissione e sequenza di trasformazioni (fino a 10 righe; il foglio ne ha 6), riepilogo e
// stima stagionale. Tutti i calcoli con EUGENIO_PSICRO.sequenza (psicro.js, già verificato col foglio e con psychrolib).
// Le condizioni esterne di progetto si precompilano dalla serie oraria del comune (percentili, livello scelto con
// livelloProgetto) e restano modificabili a mano. Scaricamenti: il foglio originale, il foglio con i dati della pagina
// (celle gialle compilate nel browser con fflate, nessun dato al server), CSV e JSON della configurazione e dei risultati.
// Parte pura (stima stagionale, celle del foglio, scrittura dell'xlsx) esportata anche per node: test in
// fase14-trattamento-aria/tests/test_trasformazioni.py e fase5-sito/tests/test_aria_trasformazioni*.py.
(function (radice) {
  const P = radice.EUGENIO_PSICRO || (typeof require === "function" ? require("./psicro.js") : null);
  const fin = Number.isFinite;
  const MAX_RIGHE = 10, RIGHE_FOGLIO = 6, CHIAVE = "eugenio-aria-trasf-v1";

  // ------------------------------------------------------------------ parte pura
  // numero scritto all'italiana ("1.234,5", "0,7", "-5") o all'inglese ("0.7"); NaN se non è un numero
  function numero(v) {
    if (typeof v === "number") return v;
    if (v === null || v === undefined) return NaN;
    let s = String(v).trim().replace(/\s/g, "").replace("−", "-");
    if (!s) return NaN;
    if (/^[-+]?\d{1,3}(\.\d{3})+(,\d*)?$/.test(s)) s = s.replace(/\./g, "");
    s = s.replace(",", ".");
    return /^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$/.test(s) ? Number(s) : NaN;
  }
  // parametro P1–P3 come testo per i campi (numeri con la virgola, AUTO, vuoto)
  const testoParametro = (v) => (v === null || v === undefined ? "" : typeof v === "number" ? String(v).replace(".", ",") : String(v));
  const righePreset = (stagione) => P.PRESET[stagione].map((r) => [r[0], testoParametro(r[1]), testoParametro(r[2]), testoParametro(r[3])]);

  // stato predefinito della pagina (= dati gialli del foglio; ambiente invernale 20 °C / 40 % come le altre pagine del
  // menu e, dal 15/11/2026, anche il foglio). null = valore automatico (dal comune o dalla serie).
  function predefiniti() {
    const D = P.DATI_PREDEFINITI;
    return {
      versione: 1, istat: null,
      generali: { quota: null, pressione: null, V: D.V, quotaEsterna: D.quotaEsterna, riferimento: 0 },
      estate: { esterno: { t: null, ur: null }, statistica: "temperatura", ambiente: { ...D.estate.ambiente }, Qs: D.estate.Qs, Ql: D.estate.Ql, righe: righePreset("estate") },
      inverno: { esterno: { t: null, ur: null }, ambiente: { ...D.inverno.ambiente }, Qs: D.inverno.Qs, Ql: D.inverno.Ql, righe: righePreset("inverno") },
      stima: { gg: null, ore: 12, rendimento: 0.9, pci: 9.59, oreEq: 500, eer: 3 },
      nuvola: false,
    };
  }

  // Stima stagionale del foglio (UTA!B77:H85): solo il calore sensibile per portare l'aria esterna di rinnovo da T
  // esterna a 20 °C (gradi giorno base 20 °C) con l'UTA in funzione «ore/24» del tempo; εs = P1 della prima riga
  // «Recuperatore» invernale (0 se manca); energia frigorifera = potenza frigorifera estiva × ore equivalenti.
  // inv, est = risultati di P.sequenza; righeInverno = righe invernali [[tipo, P1, P2, P3]]; d = dati della stima.
  function stimaStagionale(inv, est, righeInverno, d) {
    const rec = (righeInverno || []).find((r) => P.codiceTipo(r[0]) === 3);
    const lp = rec ? P.leggiParametro(rec[1]) : { ha: false };
    const eps = lp.ha ? lp.v : 0;
    const mOA = inv.mOA, cp = inv.cpA;
    const fabbisogno = mOA * cp * d.gg * d.ore;                       // kg/s · kJ/(kg K) · K·giorno · h/giorno = kWh
    const recuperata = fabbisogno * eps, netto = fabbisogno - recuperata;
    const combustibile = d.rendimento * d.pci > 0 ? netto / (d.rendimento * d.pci) : 0;
    const frigo = est.riepilogo.frigoTotale * d.oreEq, elettrica = d.eer > 0 ? frigo / d.eer : 0;
    return { mOA, eps, cp, fabbisogno, recuperata, netto, combustibile, frigo, elettrica };
  }

  // celle gialle del foglio UTA da una configurazione { p, quota, pressioneImposta, V, quotaEsterna, riferimento,
  // estate: { esterno, ambiente, Qs, Ql, righe }, inverno: {…}, stima: {gg, ore, rendimento, pci, oreEq, eer} }
  // → [[cella, valore]] (numero, testo o null = cella vuota). Solo le prime 6 righe di ogni sequenza.
  function celleExcel(c) {
    const out = [["D6", c.quota], ["D8", fin(c.pressioneImposta) ? c.pressioneImposta : null], ["D10", c.V], ["D11", c.quotaEsterna],
      ["D14", P.RIF_PORTATA[c.riferimento] || P.RIF_PORTATA[0]]];
    const par = (v) => { const s = testoParametro(v).trim(); if (!s) return null; if (s.toUpperCase() === "AUTO") return "AUTO"; const n = numero(s); return fin(n) ? n : s; };
    [["estate", 18, 28], ["inverno", 48, 58]].forEach(([k, r0, s0]) => {
      const s = c[k];
      out.push([`D${r0}`, s.esterno.t], [`D${r0 + 1}`, s.esterno.ur], [`D${r0 + 2}`, s.ambiente.t], [`D${r0 + 3}`, s.ambiente.ur], [`D${r0 + 4}`, s.Qs], [`D${r0 + 5}`, s.Ql]);
      for (let i = 0; i < RIGHE_FOGLIO; i++) {
        const r = s.righe[i] || ["Nessuna", "", "", ""];
        out.push([`C${s0 + i}`, P.TIPI[P.codiceTipo(r[0]) - 1]], [`D${s0 + i}`, par(r[1])], [`E${s0 + i}`, par(r[2])], [`F${s0 + i}`, par(r[3])]);
      }
    });
    const st = c.stima;
    out.push(["D78", st.gg], ["D79", st.ore], ["D80", st.rendimento], ["D81", st.pci], ["D82", st.oreEq], ["D83", st.eer]);
    return out;
  }
  const escXml = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  // sostituisce il contenuto di una cella nel foglio XML, tenendo lo stile (s="…"); la cella esiste già (foglio openpyxl)
  function impostaCella(xml, ref, val) {
    const re = new RegExp(`<c r="${ref}"((?:\\s[^>]*?)?)(/>|>[\\s\\S]*?</c>)`);
    const m = xml.match(re);
    if (!m) throw new Error(`cella ${ref} non trovata nel foglio`);
    const s = (m[1] || "").match(/\ss="(\d+)"/), sa = s ? ` s="${s[1]}"` : "";
    let nuovo;
    if (val === null || val === undefined || val === "" || (typeof val === "number" && !fin(val))) nuovo = `<c r="${ref}"${sa}/>`;
    else if (typeof val === "number") nuovo = `<c r="${ref}"${sa} t="n"><v>${val}</v></c>`;
    else nuovo = `<c r="${ref}"${sa} t="inlineStr"><is><t>${escXml(val)}</t></is></c>`;
    return xml.slice(0, m.index) + nuovo + xml.slice(m.index + m[0].length);
  }
  // compila il foglio: ff = fflate, buf = byte di psicro_UTA.xlsx, celle = celleExcel(…). Toglie i risultati salvati
  // delle formule (si ricalcolano all'apertura: workbook con fullCalcOnLoad) → Uint8Array del nuovo .xlsx
  function compilaXlsx(ff, buf, celle) {
    const files = ff.unzipSync(buf);
    const wb = ff.strFromU8(files["xl/workbook.xml"]), rels = ff.strFromU8(files["xl/_rels/workbook.xml.rels"]);
    const sh = wb.match(/<sheet\b[^>]*\bname="UTA"[^>]*>/);
    const rid = sh && sh[0].match(/r:id="([^"]+)"/);
    const rel = rid && rels.match(new RegExp(`<Relationship\\b[^>]*\\bId="${rid[1]}"[^>]*>`)) ;
    const tgt = rel && rel[0].match(/Target="([^"]+)"/);
    if (!tgt) throw new Error("foglio «UTA» non trovato nel file");
    const percorso = tgt[1].replace(/^\//, "").replace(/^(?!xl\/)/, "xl/");
    let xml = ff.strFromU8(files[percorso]);
    for (const [ref, v] of celle) xml = impostaCella(xml, ref, v);
    files[percorso] = ff.strToU8(xml);
    for (const k of Object.keys(files)) {
      if (!/^xl\/worksheets\/sheet\d+\.xml$/.test(k)) continue;
      const s = ff.strFromU8(files[k]);
      const t = s.replace(/(<f>[^<]*<\/f>|<f\s[^>]*>[^<]*<\/f>|<f\s[^>]*\/>)<v>[^<]*<\/v>/g, "$1");
      if (t !== s) files[k] = ff.strToU8(t);
    }
    let w = wb;
    if (/<calcPr\b/.test(w)) { if (!/fullCalcOnLoad=/.test(w)) w = w.replace(/<calcPr\b/, '<calcPr fullCalcOnLoad="1"'); }
    else w = w.replace("</workbook>", '<calcPr fullCalcOnLoad="1"/></workbook>');
    files["xl/workbook.xml"] = ff.strToU8(w);
    return ff.zipSync(files, { level: 6 });
  }
  // calcolo completo da una configurazione (come il foglio): { estate, inverno, stima }
  function calcolaConfigurazione(c) {
    const opz = (k) => ({ p: c.p, V: c.V, quotaEsterna: c.quotaEsterna, riferimento: c.riferimento, stagione: k,
      esterno: c[k].esterno, ambiente: c[k].ambiente, Qs: c[k].Qs, Ql: c[k].Ql, righe: c[k].righe });
    const estate = P.sequenza(opz("estate")), inverno = P.sequenza(opz("inverno"));
    return { estate, inverno, stima: stimaStagionale(inverno, estate, c.inverno.righe, c.stima) };
  }
  // la nota di una riga va evidenziata (stesse parole della formattazione condizionale del foglio, colonna «Note»)
  const notaDaEvidenziare = (s) => /RAGGIUNGIBILE|SATURAZIONE|mancante|Attenzione|brina|riconosciuto|non validi|rugiada dell/i.test(s || "");

  const PURA = { numero, testoParametro, righePreset, predefiniti, stimaStagionale, celleExcel, impostaCella, compilaXlsx, calcolaConfigurazione,
    notaDaEvidenziare, MAX_RIGHE, RIGHE_FOGLIO, CHIAVE };
  if (typeof module !== "undefined" && module.exports) { module.exports = PURA; return; }
  if (typeof document === "undefined") return;

  // ------------------------------------------------------------------ pagina
  const K = "aria-trasformazioni-";
  const VERSIONE = (() => { try { const m = (document.currentScript && document.currentScript.src || "").match(/\?v=[\w]+/); return m ? m[0] : ""; } catch (e) { return ""; } })();
  const $ = (s) => document.querySelector(s);
  function h(tag, cls, testo) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (testo !== undefined && testo !== null) e.textContent = testo;
    return e;
  }
  function fmt(v, d = 1) {
    if (!fin(v)) return "—";
    const f = Math.pow(10, d), r = Math.round(v * f) / f;
    // migliaia sempre col punto (5.592 kg/h) e segno meno tipografico (−1,7 °C), come le altre pagine
    return (r === 0 ? 0 : r).toLocaleString("it-IT", { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: "always" }).replace(/^-/, "−");
  }
  const fmtCampo = (v, d = 1) => (fin(v) ? String(Math.round(v * Math.pow(10, d)) / Math.pow(10, d)).replace(".", ",") : "");
  const dataIt = (s) => (/^\d{4}-\d{2}-\d{2}/.test(String(s || "")) ? `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}` : String(s || ""));
  const arrot = (v, d = 1) => Math.round(v * Math.pow(10, d)) / Math.pow(10, d);
  const NOMI = { estate: "Estate", inverno: "Inverno" };

  // ---- stato (ricordato nel browser)
  function leggiStato() {
    try { return daOggetto(JSON.parse(localStorage.getItem(CHIAVE) || "null")); } catch (e) { return predefiniti(); }
  }
  function daOggetto(j) {
    const pred = predefiniti();
    try {
      if (!j || j.versione !== 1) return pred;
      const unisci = (a, b) => { const o = { ...a }; for (const k of Object.keys(a)) if (b && b[k] !== undefined) o[k] = a[k] && typeof a[k] === "object" && !Array.isArray(a[k]) ? unisci(a[k], b[k]) : b[k]; return o; };
      const s = unisci(pred, j);
      for (const k of ["estate", "inverno"]) {
        const r = Array.isArray(j[k] && j[k].righe) ? j[k].righe.filter((x) => Array.isArray(x)).slice(0, MAX_RIGHE) : null;
        s[k].righe = r && r.length ? r.map((x) => [P.TIPI[P.codiceTipo(x[0]) - 1], testoParametro(x[1]), testoParametro(x[2]), testoParametro(x[3])]) : pred[k].righe;
      }
      return s;
    } catch (e) { return pred; }
  }
  // (20/11/2026) collegamento a questa simulazione: i dati e le sequenze che differiscono dai predefiniti vanno
  // nell'indirizzo come JSON compatto (?uta=…; «predefiniti» se non cambia niente); aprendolo valgono quelli e non la
  // memoria del browser. Comune, anni, livello e diagramma li portano i moduli comuni.
  function differenze(a, b) {
    if (JSON.stringify(a) === JSON.stringify(b)) return undefined;
    if (a && b && typeof a === "object" && typeof b === "object" && !Array.isArray(a) && !Array.isArray(b)) {
      const o = {};
      for (const k of Object.keys(b)) { const d = differenze(a[k], b[k]); if (d !== undefined) o[k] = d; }
      return Object.keys(o).length ? o : undefined;
    }
    return b;
  }
  function statoDalCollegamento() {
    const q = new URLSearchParams(location.search), t = q.get("uta");
    if (!t) return null;
    let j = {};
    if (t !== "predefiniti") { try { j = JSON.parse(t); } catch (e) { return null; } }
    const s = daOggetto({ ...j, versione: 1 });
    s.istat = q.get("comune") || null;
    return s;
  }
  let stato = statoDalCollegamento() || leggiStato();
  if (window.EUGENIO_COLLEGAMENTO) window.EUGENIO_COLLEGAMENTO.registra({
    chiavi: ["uta"],
    principali: [],
    leggi: () => {
      const d = differenze(predefiniti(), { ...stato, istat: null, versione: 1 });
      return { uta: d ? JSON.stringify(d) : "predefiniti" };
    },
  });
  function salvaStato() { try { localStorage.setItem(CHIAVE, JSON.stringify(stato)); } catch (e) { /* memoria piena o vietata */ } }

  // ---- moduli comuni: diagramma, passo 1, livello
  const titolo = "Trasformazioni dell'aria (UTA)";
  let S = null, L = null;
  const D = window.EUGENIO_DIAGRAMMA_ARIA.crea(document.getElementById("diagramma-aria"), {
    titolo,
    nomeFile: () => "eugenio-aria-trasformazioni",
    avviso: () => (S && S.serie() && S.serie().sintetica ? "Dati sintetici di prova, non reali." : ""),
    fonti: () => fontiDiagramma(),
  });
  S = window.EUGENIO_SCELTA_ARIA.crea({ mappa: "#mappa", passo: "#scelta-aria" });
  L = window.EUGENIO_SCELTA_ARIA.livelloProgetto("#aria-livello", { subito: false });

  // ---- condizioni di progetto dalla serie (in memoria finché non cambiano serie, livello o pressione)
  let clima = null, climaChiave = "", climaSerie = null;
  function aggiornaClima(p) {
    const s = S.serie();
    if (!s) { clima = null; climaSerie = null; climaChiave = ""; return; }
    const lv = L.valori(), k = `${lv.inverno}|${lv.estate}|${Math.round(p)}`;
    if (s === climaSerie && k === climaChiave) return;
    climaSerie = s; climaChiave = k;
    try {
      const c = P.condizioniProgetto(s.t, s.ur, p, lv);
      clima = c.inverno ? c : null;
    } catch (e) { console.error(e); clima = null; }
  }
  const STATISTICHE = [["temperatura", "Temperatura con bulbo umido coincidente"], ["entalpia", "Entalpia con temperatura coincidente"],
    ["umidita", "Umidità specifica con temperatura coincidente"]];
  // valori dal clima per una stagione: { t, ur, testo } (T e UR arrotondate a 0,1 come se si scrivessero a mano)
  function esternoClima(k) {
    if (!clima) return null;
    const nomi = P.nomiProgetto(L.valori());
    let t, ur, testo;
    if (k === "inverno") {
      const c = clima.inverno; t = c.t; ur = Math.min(100, c.ur);
      testo = `${nomi.inverno} (${fmt(c.ore, 0)} ore nella classe).`;
    } else {
      const q = stato.estate.statistica;
      const c = q === "entalpia" ? clima.entalpia : q === "umidita" ? clima.umidita : clima.estate;
      if (!c || !c.stato) return null;
      t = c.stato.t; ur = Math.min(100, c.stato.ur);
      testo = q === "entalpia" ? `${nomi.entalpia}: h = ${fmt(c.h, 1)} kJ/kg, T media ${fmt(c.t, 1)} °C (${fmt(c.ore, 0)} ore).`
        : q === "umidita" ? `${nomi.umidita}: x = ${fmt(c.xg, 2)} g/kg, T media ${fmt(c.t, 1)} °C (${fmt(c.ore, 0)} ore).`
          : `${nomi.estate}: bulbo umido ${fmt(c.twb, 1)} °C (${fmt(c.ore, 0)} ore).`;
    }
    if (!fin(t) || !fin(ur)) return null;
    return { t: arrot(t, 1), ur: arrot(ur, 1), testo };
  }
  function esternoUsato(k) {
    const m = stato[k].esterno, c = esternoClima(k), pr = P.DATI_PREDEFINITI[k].esterno;
    return { t: fin(m.t) ? m.t : c ? c.t : pr.t, ur: fin(m.ur) ? m.ur : c ? c.ur : pr.ur };
  }

  // ---- pressione e quota
  const serie = () => S.serie();
  function quotaComune() { const s = serie(); return s && fin(s.quota_m) ? s.quota_m : null; }
  function quotaUsata() { const g = stato.generali; return fin(g.quota) ? g.quota : fin(quotaComune()) ? quotaComune() : P.DATI_PREDEFINITI.quota; }
  function pressioneCalcolo() {
    const g = stato.generali, s = serie();
    if (fin(g.pressione)) return Math.max(30000, Math.min(120000, g.pressione));
    if (!fin(g.quota) && s && fin(s.p)) return s.p;
    return P.pressione(quotaUsata());
  }
  let ggComune = null, ggIstat = null, tabellaDPR = null;
  async function caricaGG(istat) {
    if (!istat) { ggComune = null; ggIstat = null; return; }
    try {
      if (!tabellaDPR) tabellaDPR = fetch(`dati/dpr412.json${VERSIONE}`).then((r) => (r.ok ? r.json() : null)).catch(() => null);
      const t = await tabellaDPR, v = t && t.comuni && t.comuni[istat];
      ggComune = Array.isArray(v) && fin(v[0]) && v[0] > 0 ? v[0] : null;
    } catch (e) { ggComune = null; }
    ggIstat = istat;
  }
  const ggUsati = () => (fin(stato.stima.gg) ? stato.stima.gg : fin(ggComune) ? ggComune : 2404);

  // ---- campi numerici con aggiornamento automatico
  const campi = [];
  // def = { etichetta, unita, leggi() → numero|null, scrivi(v|null), auto() → numero|null (valore automatico), d (decimali),
  //         min, max, vuoto (si può lasciare vuoto = automatico), aiuto, id }
  function campo(box, def) {
    const l = h("label", "aria-campo"); if (def.id) l.htmlFor = def.id;
    l.appendChild(h("span", null, def.unita ? `${def.etichetta} [${def.unita}]` : def.etichetta));
    const inp = document.createElement("input");
    inp.type = "text"; inp.inputMode = "decimal"; inp.autocomplete = "off"; inp.spellcheck = false;
    if (def.id) inp.id = def.id;
    if (def.chiave) inp.dataset.campo = def.chiave;
    if (def.aiuto) inp.title = def.aiuto;
    if (def.larga) inp.classList.add(`${K}largo`);
    l.appendChild(inp);
    box.appendChild(l);
    const mostra = (forza) => {
      if (!forza && document.activeElement === inp) return;
      const v = def.leggi();
      if (fin(v)) { inp.value = fmtCampo(v, def.d === undefined ? 2 : def.d); inp.classList.remove(`${K}auto`); }
      else { const a = def.auto ? def.auto() : null; inp.value = fin(a) ? fmtCampo(a, def.d === undefined ? 2 : def.d) : ""; inp.classList.toggle(`${K}auto`, !!def.auto); }
      inp.placeholder = def.segnaposto ? def.segnaposto() : "";
      inp.setAttribute("aria-invalid", "false");
    };
    inp.addEventListener("input", () => {
      const s = inp.value.trim();
      if (!s && def.vuoto) { def.scrivi(null); inp.setAttribute("aria-invalid", "false"); inp.classList.add(`${K}auto`); cambiato(); return; }
      const v = numero(s);
      const ok = fin(v) && (def.min === undefined || v >= def.min) && (def.max === undefined || v <= def.max);
      inp.setAttribute("aria-invalid", ok ? "false" : "true");
      if (ok) { def.scrivi(v); inp.classList.remove(`${K}auto`); cambiato(); }
    });
    inp.addEventListener("blur", () => { if (inp.getAttribute("aria-invalid") !== "true") mostra(true); });
    const c = { inp, mostra, def };
    campi.push(c);
    mostra(true);
    return c;
  }
  const aggiornaCampi = () => campi.forEach((c) => c.mostra(false));

  // ---- ricalcolo (al più ogni 100 ms)
  let attesa = 0, risultati = null;
  function cambiato() { salvaStato(); programma(); }
  function programma() { clearTimeout(attesa); attesa = setTimeout(calcola, 100); }

  // ================================================================== costruzione dei passi
  const pannello = $("#aria-trasf-passi");

  // ---- passo 2: dati generali
  const boxGen = $("#aria-trasf-generali");
  const campiGen = h("div", "aria-campi"); boxGen.appendChild(campiGen);
  campo(campiGen, { etichetta: "Altitudine", unita: "m", id: `${K}quota`, chiave: "quota", d: 0, min: -400, max: 4000, vuoto: true,
    leggi: () => stato.generali.quota, scrivi: (v) => { stato.generali.quota = v; }, auto: () => quotaUsata(),
    aiuto: "Dal comune scelto (quota della serie). Scrivi un altro valore per cambiarla; cancella per tornare a quella del comune." });
  campo(campiGen, { etichetta: "Pressione imposta (facoltativa)", unita: "Pa", id: `${K}pressione`, chiave: "pressione", d: 0, larga: true, min: 30000, max: 120000, vuoto: true,
    leggi: () => stato.generali.pressione, scrivi: (v) => { stato.generali.pressione = v; }, segnaposto: () => `calcolata: ${fmt(pressioneCalcolo(), 0)}`,
    aiuto: "Vuoto = pressione calcolata dall'altitudine (come la cella D8 del foglio)." });
  campo(campiGen, { etichetta: "Portata di mandata", unita: "m³/h", id: `${K}portata`, chiave: "V", d: 0, min: 1, max: 1e6,
    leggi: () => stato.generali.V, scrivi: (v) => { stato.generali.V = v; }, aiuto: "Portata in volume TOTALE immessa in ambiente (aria esterna + ricircolo)." });
  campo(campiGen, { etichetta: "Aria esterna", unita: "%", id: `${K}quota-esterna`, chiave: "quotaEsterna", d: 1, min: 0, max: 100,
    leggi: () => stato.generali.quotaEsterna, scrivi: (v) => { stato.generali.quotaEsterna = v; }, aiuto: "100 = tutta aria esterna; il resto è ricircolo alle condizioni ambiente (riga «Miscela con ricircolo», AUTO)." });
  const lRif = h("label", "aria-campo"); lRif.htmlFor = `${K}riferimento`;
  lRif.appendChild(h("span", null, "Riferimento della portata"));
  const selRif = h("select"); selRif.id = `${K}riferimento`;
  P.RIF_PORTATA.forEach((t, i) => { const o = h("option", null, t); o.value = String(i); selRif.appendChild(o); });
  selRif.addEventListener("change", () => { stato.generali.riferimento = Number(selRif.value); cambiato(); });
  lRif.appendChild(selRif);
  boxGen.appendChild(lRif);
  const quotaNota = h("p", "aiuto"); boxGen.appendChild(quotaNota);
  const tabGen = h("div", "tabella-scorre"); boxGen.appendChild(tabGen);

  // ---- passi 3 e 4: le due stagioni
  const UI = {};
  function costruisciStagione(k) {
    const box = $(`#aria-trasf-${k}`), ui = { k };
    UI[k] = ui;
    // condizioni esterne
    const fe = h("fieldset", `${K}gruppo`); fe.appendChild(h("legend", null, "Condizioni esterne di progetto"));
    if (k === "estate") {
      const ls = h("label", "aria-campo"); ls.htmlFor = `${K}statistica`;
      ls.appendChild(h("span", null, "Statistica dalla serie"));
      const ss = h("select"); ss.id = `${K}statistica`;
      STATISTICHE.forEach(([v, t]) => { const o = h("option", null, t); o.value = v; ss.appendChild(o); });
      ss.addEventListener("change", () => { stato.estate.statistica = ss.value; stato.estate.esterno = { t: null, ur: null }; cambiato(); aggiornaCampi(); });
      ls.appendChild(ss); fe.appendChild(ls); ui.statistica = ss;
    }
    const ce = h("div", "aria-campi"); fe.appendChild(ce);
    const autoE = (q) => () => { const c = esternoClima(k); return c ? c[q] : P.DATI_PREDEFINITI[k].esterno[q]; };
    campo(ce, { etichetta: "Temperatura", unita: "°C", id: `${K}${k}-te`, chiave: `${k}.esterno.t`, d: 1, min: -60, max: 60, vuoto: true,
      leggi: () => stato[k].esterno.t, scrivi: (v) => { stato[k].esterno.t = v; }, auto: autoE("t") });
    campo(ce, { etichetta: "Umidità relativa", unita: "%", id: `${K}${k}-ure`, chiave: `${k}.esterno.ur`, d: 1, min: 0.1, max: 100, vuoto: true,
      leggi: () => stato[k].esterno.ur, scrivi: (v) => { stato[k].esterno.ur = v; }, auto: autoE("ur") });
    const rip = h("button", `${K}collegamento`, "ripristina dal clima"); rip.type = "button";
    rip.addEventListener("click", () => { stato[k].esterno = { t: null, ur: null }; cambiato(); campi.forEach((c) => c.mostra(true)); });
    ce.appendChild(rip); ui.ripristina = rip;
    ui.fonteEsterno = h("p", "aiuto"); fe.appendChild(ui.fonteEsterno);
    box.appendChild(fe);
    // ambiente e carichi
    const fa = h("fieldset", `${K}gruppo`); fa.appendChild(h("legend", null, "Ambiente e carichi"));
    const ca = h("div", "aria-campi"); fa.appendChild(ca);
    campo(ca, { etichetta: "T ambiente", unita: "°C", id: `${K}${k}-ta`, chiave: `${k}.ambiente.t`, d: 1, min: -10, max: 50, leggi: () => stato[k].ambiente.t, scrivi: (v) => { stato[k].ambiente.t = v; } });
    campo(ca, { etichetta: "UR ambiente", unita: "%", id: `${K}${k}-ura`, chiave: `${k}.ambiente.ur`, d: 1, min: 0.1, max: 100, leggi: () => stato[k].ambiente.ur, scrivi: (v) => { stato[k].ambiente.ur = v; } });
    campo(ca, { etichetta: k === "estate" ? "Carico sensibile" : "Dispersioni da coprire con l'aria", unita: "W", id: `${K}${k}-qs`, chiave: `${k}.Qs`, d: 0, min: -1e7, max: 1e7, larga: true,
      leggi: () => stato[k].Qs, scrivi: (v) => { stato[k].Qs = v; },
      aiuto: k === "estate" ? "Positivo = calore che entra nell'ambiente (sole, persone, luci, apparecchi)." : "Positivo = calore perso dall'ambiente; 0 se l'aria è immessa a temperatura neutra." });
    campo(ca, { etichetta: "Carico latente", unita: "W", id: `${K}${k}-ql`, chiave: `${k}.Ql`, d: 0, min: -1e7, max: 1e7, larga: true,
      leggi: () => stato[k].Ql, scrivi: (v) => { stato[k].Ql = v; }, aiuto: "Vapore che entra nell'ambiente (persone, processi), in W." });
    box.appendChild(fa);
    // punti E, A, I
    box.appendChild(h("h3", null, "Punti di progetto"));
    ui.punti = h("div", "tabella-scorre"); box.appendChild(ui.punti);
    ui.verifiche = h("div", "messaggio"); ui.verifiche.setAttribute("role", "status"); box.appendChild(ui.verifiche);
    // sequenza: righe modificabili (schede) e tabella dei risultati come le colonne H–S del foglio
    box.appendChild(h("h3", null, "Sequenza di trattamento"));
    box.appendChild(h("p", "aiuto", "L'ingresso di ogni riga è l'uscita della riga precedente; la riga 0 è l'aria esterna. Nei parametri scrivi un numero (anche con la virgola) o AUTO dove previsto; vuoto = non usato o valore predefinito. Il diagramma e i risultati si aggiornano a ogni modifica."));
    ui.lista = h("div", `${K}lista`); ui.lista.dataset.stagione = k;
    box.appendChild(ui.lista);
    const comandi = h("div", `${K}comandi`);
    const bot = (testo, f, titoloB, az) => { const b = h("button", "bottone secondario piccolo", testo); b.type = "button"; if (az) b.dataset.azione = az; if (titoloB) b.title = titoloB; b.addEventListener("click", f); comandi.appendChild(b); return b; };
    bot(`Preset UTA ${k === "estate" ? "estiva" : "invernale"}`, () => { stato[k].righe = righePreset(k); righeOra(k); cambiato(); },
      k === "estate" ? "Miscela (AUTO) → Batteria fredda (AUTO, BF 0,10) → Post-riscaldamento (AUTO) → Ventilatore (0,7 K)"
        : "Recuperatore (εs 0,6) → Miscela (AUTO) → Preriscaldamento (AUTO, UR 90 %) → Umidificazione adiabatica (AUTO) → Post-riscaldamento (AUTO) → Ventilatore (0,7 K)", "preset");
    bot("Svuota", () => { stato[k].righe = stato[k].righe.map(() => ["Nessuna", "", "", ""]); righeOra(k); cambiato(); }, "Tutte le righe a «Nessuna»", "svuota");
    ui.aggiungi = bot("Aggiungi una riga", () => { if (stato[k].righe.length < MAX_RIGHE) { stato[k].righe.push(["Nessuna", "", "", ""]); righeOra(k); cambiato(); } }, `Fino a ${MAX_RIGHE} righe (il foglio Excel ne ha 6)`, "aggiungi");
    box.appendChild(comandi);
    box.appendChild(h("h3", null, "Tabella delle trasformazioni"));
    const scorre = h("div", `tabella-scorre ${K}scorre`);
    const tab = h("table", `mensili ${K}tabella`); tab.dataset.stagione = k;
    const th = (t, u) => `<th scope="col" class="num">${t}${u ? `<br><small>${u}</small>` : ""}</th>`;
    tab.innerHTML = `<caption class="solo-lettori">Tabella delle trasformazioni – ${NOMI[k]}</caption><thead><tr><th scope="col">N</th><th scope="col">Tipo</th><th scope="col">P1 · P2 · P3</th>`
      + th("T", "°C") + th("UR", "%") + th("x", "g/kg") + th("h", "kJ/kg") + th("T rugiada", "°C") + th("T bulbo umido", "°C") + th("ṁ", "kg/s")
      + th("Q sensibile", "kW") + th("Q latente", "kW") + th("Q totale", "kW") + th("Acqua", "kg/h") + "</tr></thead>";
    ui.tbody = h("tbody"); tab.appendChild(ui.tbody);
    scorre.appendChild(tab); box.appendChild(scorre);
    box.appendChild(h("p", "aiuto", "Potenze: positivo = calore ceduto all'aria, negativo = sottratto. Acqua: + aggiunta, − condensata."));
    // confronto uscita – immissione
    box.appendChild(h("h3", null, "Uscita dell'UTA e punto di immissione"));
    ui.confronto = h("div", "tabella-scorre"); box.appendChild(ui.confronto);
    ui.esito = h("div", "messaggio"); ui.esito.setAttribute("role", "status"); ui.esito.dataset.esito = k; box.appendChild(ui.esito);
    righeOra(k);
  }

  // righe della sequenza (si ricostruiscono solo quando cambia la struttura: preset, svuota, aggiungi, togli, sposta)
  function righeOra(k) {
    const ui = UI[k], righe = stato[k].righe;
    ui.lista.innerHTML = ""; ui.tbody.innerHTML = "";
    ui.righe = [];
    const ingresso = h("tr", `${K}ingresso`);
    ingresso.appendChild(Object.assign(h("th", null, "0"), { scope: "row" }));
    const ti = h("td", null, "Ingresso: aria esterna (punto E)"); ti.colSpan = 2; ingresso.appendChild(ti);
    ui.ingresso = celleRisultato(ingresso);
    ui.tbody.appendChild(ingresso);
    righe.forEach((r, i) => {
      const n = i + 1, et = `${NOMI[k]}, riga ${n}`;
      const sc = h("div", `${K}riga`); sc.dataset.riga = String(i); sc.setAttribute("role", "group"); sc.setAttribute("aria-label", et);
      const testa = h("div", `${K}riga-testa`);
      testa.appendChild(h("span", `${K}n`, String(n)));
      const sel = h("select"); sel.setAttribute("aria-label", `${et}: tipo di trasformazione`); sel.dataset.tipo = "";
      P.TIPI.forEach((t) => { const o = h("option", null, t); o.value = t; sel.appendChild(o); });
      sel.value = P.TIPI[P.codiceTipo(r[0]) - 1];
      testa.appendChild(sel);
      const ord = h("span", `${K}ordine`);
      const piccolo = (testo, nome, f, dis, az) => { const b = h("button", "bottone secondario piccolo", testo); b.type = "button"; b.dataset.azione = az; b.setAttribute("aria-label", `${nome}: riga ${n} (${NOMI[k].toLowerCase()})`); b.title = nome; b.disabled = !!dis; b.addEventListener("click", f); ord.appendChild(b); return b; };
      piccolo("↑", "Sposta in su", () => sposta(k, i, -1), i === 0, "su");
      piccolo("↓", "Sposta in giù", () => sposta(k, i, +1), i === righe.length - 1, "giu");
      piccolo("×", "Togli la riga", () => { if (stato[k].righe.length > 1) { stato[k].righe.splice(i, 1); righeOra(k); cambiato(); } }, righe.length <= 1, "togli");
      testa.appendChild(ord);
      const pars = h("div", `${K}riga-par`);
      const par = [1, 2, 3].map((j) => {
        const l = h("label", `${K}par`), inp = document.createElement("input");
        l.appendChild(h("span", null, `P${j}`));
        inp.type = "text"; inp.autocomplete = "off"; inp.spellcheck = false; inp.value = r[j] || "";
        inp.dataset.p = String(j);
        inp.setAttribute("aria-label", `${et}: P${j}`);
        inp.addEventListener("input", () => { stato[k].righe[i][j] = inp.value; validaParametro(inp, j); cambiato(); });
        validaParametro(inp, j);
        l.appendChild(inp); pars.appendChild(l);
        return inp;
      });
      const sig = h("p", `${K}significato`);
      pars.appendChild(sig);
      const esito = h("p", `${K}esito-riga`);
      const ris = h("span", `${K}risultato`), nota = h("span", `${K}nota`);
      esito.append(ris, nota);
      sc.append(testa, pars, esito);
      ui.lista.appendChild(sc);
      sel.addEventListener("change", () => { stato[k].righe[i][0] = sel.value; sig.textContent = P.PARAMETRI[P.codiceTipo(sel.value) - 1]; cambiato(); });
      sig.textContent = P.PARAMETRI[P.codiceTipo(sel.value) - 1];
      // riga della tabella dei risultati
      const tr = h("tr", `${K}riga-tab`); tr.dataset.riga = String(i);
      tr.appendChild(Object.assign(h("th", null, String(n)), { scope: "row" }));
      const tdTipo = h("td", `${K}tipo-tab`), tdPar = h("td", `${K}par-tab`);
      tr.append(tdTipo, tdPar);
      const celle = celleRisultato(tr);
      ui.tbody.appendChild(tr);
      ui.righe.push({ sc, tr, sel, par, sig, ris, nota, celle, tdTipo, tdPar });
    });
    ui.aggiungi.disabled = righe.length >= MAX_RIGHE;
    if (risultati) mostraRighe(k, risultati[k]);
  }
  function validaParametro(inp, j) {
    const s = inp.value.trim();
    const ok = !s || fin(numero(s)) || (j === 1 && s.toUpperCase() === "AUTO");
    inp.setAttribute("aria-invalid", ok ? "false" : "true");
    inp.title = ok ? "" : (j === 1 ? "Scrivi un numero o AUTO" : "Scrivi un numero");
  }
  function sposta(k, i, d) {
    const r = stato[k].righe, j = i + d;
    if (j < 0 || j >= r.length) return;
    [r[i], r[j]] = [r[j], r[i]];
    righeOra(k); cambiato();
    const b = UI[k].righe[j] && UI[k].righe[j].sc.querySelector(`button[data-azione="${d < 0 ? "su" : "giu"}"]`);
    if (b && !b.disabled) b.focus();
  }
  const COLONNE = [["t", 1], ["ur", 1], ["xg", 2], ["h", 1], ["tdew", 1], ["twb", 1], ["mdot", 3], ["Qs", 2], ["Ql", 2], ["Qt", 2], ["acqua", 2]];
  function celleRisultato(tr) {
    const o = {};
    COLONNE.forEach(([c]) => { const td = h("td", "num"); td.dataset.k = c; tr.appendChild(td); o[c] = td; });
    return o;
  }
  function scriviCella(td, v, d) { td.textContent = fmt(v, d); td.dataset.valore = fin(v) ? String(v) : ""; }
  function mostraRighe(k, r) {
    const ui = UI[k], E = r.esterno, conf = stato[k].righe;
    COLONNE.forEach(([c, d]) => scriviCella(ui.ingresso[c], c === "mdot" ? (r.mixidx ? r.mOA : r.mtot) : ["Qs", "Ql", "Qt", "acqua"].includes(c) ? NaN : E[c], d));
    ui.righe.forEach((u, i) => {
      const o = r.righe[i];
      if (!o) return;
      const vals = { ...o.uscita, mdot: o.mdot, Qs: o.Qs, Ql: o.Ql, Qt: o.Qt, acqua: o.acqua };
      COLONNE.forEach(([c, d]) => scriviCella(u.celle[c], vals[c], d));
      u.tdTipo.textContent = o.tipo;
      u.tdPar.textContent = (conf[i] || []).slice(1).map((x) => (String(x || "").trim() || "–")).join(" · ");
      const spenta = o.codice === 1, q = o.uscita;
      u.sc.classList.toggle(`${K}spenta`, spenta);
      u.tr.classList.toggle(`${K}spenta`, spenta);
      u.ris.textContent = spenta ? "" : `Uscita: ${fmt(q.t, 1)} °C · UR ${fmt(q.ur, 1)} % · x ${fmt(q.xg, 2)} g/kg · h ${fmt(q.h, 1)} kJ/kg`
        + (o.codice === 2 ? "" : ` · Q ${fmt(o.Qt, 2)} kW (sensibile ${fmt(o.Qs, 2)}, latente ${fmt(o.Ql, 2)})`)
        + (Math.abs(o.acqua) > 1e-6 ? ` · acqua ${fmt(o.acqua, 2)} kg/h` : "") + ". ";
      u.nota.textContent = o.nota && o.nota !== "OK" ? o.nota.trim() : o.nota === "OK" ? "OK" : "";
      const male = notaDaEvidenziare(o.nota);
      u.sc.classList.toggle(`${K}avviso`, male);
      u.tr.classList.toggle(`${K}avviso`, male);
    });
  }

  // ---- passo 5: riepilogo e stima stagionale
  const boxRiep = $("#aria-trasf-riepilogo");
  const cifre = h("div", `cifre ${K}cifre`); boxRiep.appendChild(cifre);
  const tabRiep = h("div", "tabella-scorre"); boxRiep.appendChild(tabRiep);
  const esitiRiep = h("div", `${K}esiti`); boxRiep.appendChild(esitiRiep);
  boxRiep.appendChild(h("h3", null, "Stima stagionale (indicativa)"));
  boxRiep.appendChild(h("p", "aiuto", "Come nel foglio: solo il calore sensibile per portare l'aria esterna di rinnovo dalla T esterna a 20 °C (gradi giorno base 20 °C), con l'UTA accesa per le ore al giorno indicate; non include umidificazione, post-riscaldamento per i carichi, perdite di distribuzione né la temperatura minima del recuperatore. εs è il P1 della prima riga «Recuperatore di calore» invernale."));
  const campiStima = h("div", "aria-campi"); boxRiep.appendChild(campiStima);
  campo(campiStima, { etichetta: "Gradi giorno", unita: "K·giorno", id: `${K}gg`, chiave: "stima.gg", d: 0, min: 0, max: 10000, vuoto: true,
    leggi: () => stato.stima.gg, scrivi: (v) => { stato.stima.gg = v; }, auto: () => ggUsati(),
    aiuto: "Dal DPR 412/93 per il comune scelto (base 20 °C). Scrivi un altro valore per cambiarlo; cancella per tornare a quello del comune." });
  campo(campiStima, { etichetta: "Ore al giorno", unita: "h/g", id: `${K}ore`, chiave: "stima.ore", d: 1, min: 0, max: 24, leggi: () => stato.stima.ore, scrivi: (v) => { stato.stima.ore = v; } });
  campo(campiStima, { etichetta: "Rendimento generazione", unita: "–", id: `${K}rend`, chiave: "stima.rendimento", d: 2, min: 0, max: 10, leggi: () => stato.stima.rendimento, scrivi: (v) => { stato.stima.rendimento = v; },
    aiuto: "Caldaia a condensazione 0,90–1,00; pompa di calore: COP medio (es. 3)." });
  campo(campiStima, { etichetta: "PCI gas naturale", unita: "kWh/Sm³", id: `${K}pci`, chiave: "stima.pci", d: 2, min: 0, max: 100, leggi: () => stato.stima.pci, scrivi: (v) => { stato.stima.pci = v; } });
  campo(campiStima, { etichetta: "Ore equivalenti estive", unita: "h", id: `${K}oreeq`, chiave: "stima.oreEq", d: 0, min: 0, max: 8760, leggi: () => stato.stima.oreEq, scrivi: (v) => { stato.stima.oreEq = v; },
    aiuto: "Ore di funzionamento a piena potenza della batteria fredda nella stagione estiva (tipico 300–900 h)." });
  campo(campiStima, { etichetta: "EER medio", unita: "–", id: `${K}eer`, chiave: "stima.eer", d: 2, min: 0, max: 20, leggi: () => stato.stima.eer, scrivi: (v) => { stato.stima.eer = v; } });
  const ggNota = h("p", "aiuto"); boxRiep.appendChild(ggNota);
  const tabStima = h("div", "tabella-scorre"); boxRiep.appendChild(tabStima);

  // ---- diagramma: nuvola delle ore (spenta di predefinito) e ripristino
  const boxOpz = $("#aria-trasf-opzioni");
  const lN = h("label", "casella");
  const cN = document.createElement("input"); cN.type = "checkbox"; cN.id = `${K}nuvola`; cN.checked = !!stato.nuvola;
  lN.append(cN, " Mostra sul diagramma le ore della serie scelta (nuvola chiara, per confronto)");
  boxOpz.appendChild(lN);
  cN.addEventListener("change", () => { stato.nuvola = cN.checked; salvaStato(); nuvolaOra(); });
  const bRip = h("button", "bottone secondario piccolo", "Ripristina predefiniti"); bRip.type = "button"; bRip.id = `${K}ripristina`;
  bRip.title = "Torna ai dati e alle sequenze predefinite (comune e serie restano quelli scelti)";
  bRip.addEventListener("click", () => {
    const istat = stato.istat;
    stato = predefiniti(); stato.istat = istat;
    try { localStorage.removeItem(CHIAVE); } catch (e) { /* niente */ }
    cN.checked = false; nuvolaOra();
    ["estate", "inverno"].forEach(righeOra);
    campi.forEach((c) => c.mostra(true));
    cambiato();
  });
  boxOpz.appendChild(bRip);

  // ---- passo 6: scaricamenti
  const boxSc = $("#aria-trasf-scarica");
  const rigaSc = h("div", "scarica"); boxSc.appendChild(rigaSc);
  const msgSc = h("div", "messaggio"); msgSc.setAttribute("role", "status"); msgSc.setAttribute("aria-live", "polite");
  function bottoneSc(testo, id, f, tit) {
    const b = h("button", "bottone secondario", testo); b.type = "button"; b.id = id; if (tit) b.title = tit;
    b.addEventListener("click", async () => {
      b.disabled = true; msgSc.classList.remove("errore"); msgSc.textContent = "Preparo il file…";
      try { await f(); } catch (e) { msgSc.classList.add("errore"); msgSc.textContent = `File non scaricato: ${e.message || e}.`; } finally { b.disabled = false; }
    });
    rigaSc.appendChild(b); return b;
  }
  bottoneSc("Foglio Excel con i miei dati", `${K}xlsx`, () => scaricaExcel(), "Il foglio psicro_UTA.xlsx con le celle gialle compilate con i dati di questa pagina (si ricalcola all'apertura)");
  bottoneSc("Configurazione e risultati (CSV)", `${K}csv`, () => scaricaTesto("csv"));
  bottoneSc("Configurazione e risultati (JSON)", `${K}json`, () => scaricaTesto("json"));
  bottoneSc("Diagramma PNG", `${K}png`, () => D.scarica("png").then(() => { msgSc.textContent = "Immagine pronta: vedi il messaggio sotto il diagramma."; }));
  bottoneSc("Diagramma SVG", `${K}svg`, () => D.scarica("svg").then(() => { msgSc.textContent = "Immagine pronta: vedi il messaggio sotto il diagramma."; }));
  boxSc.appendChild(msgSc);

  async function salva(blob, nome) {
    let r;
    if (window.EUGENIO_ESPORTA && window.EUGENIO_ESPORTA.salva) r = await window.EUGENIO_ESPORTA.salva(blob, nome, null);
    else {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = nome; a.rel = "noopener"; a.hidden = true;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10 * 60 * 1000);
      r = { nome, byte: blob.size, url };
    }
    msgSc.textContent = `Download avviato dal browser: ${r.nome || nome} (${fmt((r.byte || blob.size) / 1024, 0)} kB). Se non compare tra i download, usa il collegamento:`;
    if (r && r.url) { const a = h("a", "salva-a-mano", `Salva ${r.nome || nome}`); a.href = r.url; a.download = r.nome || nome; msgSc.append(" ", a); }
    return r;
  }
  const nomeBase = () => { const d = S.stato(); return `eugenio-uta${d.istat ? `-${d.istat}` : ""}`; };
  function caricaFflate() {
    if (window.fflate) return Promise.resolve(window.fflate);
    return new Promise((ok, ko) => {
      const s = document.createElement("script");
      s.src = `lib/fflate/fflate.js${VERSIONE}`;
      s.onload = () => (window.fflate ? ok(window.fflate) : ko(new Error("libreria zip non disponibile")));
      s.onerror = () => ko(new Error("libreria zip non caricata"));
      document.head.appendChild(s);
    });
  }
  async function scaricaExcel() {
    const ff = await caricaFflate();
    const r = await fetch(`strumenti/psicro_UTA.xlsx${VERSIONE}`);
    if (!r.ok) throw new Error(`foglio non disponibile (${r.status})`);
    const out = compilaXlsx(ff, new Uint8Array(await r.arrayBuffer()), celleExcel(configurazione()));
    await salva(new Blob([out], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }), `${nomeBase()}-psicro_UTA.xlsx`);
    const lunghe = ["estate", "inverno"].filter((k) => stato[k].righe.length > RIGHE_FOGLIO);
    if (lunghe.length) msgSc.append(` Attenzione: il foglio ha 6 righe per stagione, le righe dalla 7 in poi (${lunghe.map((k) => NOMI[k].toLowerCase()).join(" e ")}) non ci sono.`);
  }

  // configurazione usata dal calcolo (anche per il foglio e i file)
  function configurazione() {
    const g = stato.generali, p = pressioneCalcolo(), quota = quotaUsata();
    const stag = (k) => ({ esterno: esternoUsato(k), ambiente: { ...stato[k].ambiente }, Qs: stato[k].Qs, Ql: stato[k].Ql, righe: stato[k].righe.map((r) => r.slice()) });
    return { p, quota, pressioneImposta: fin(g.pressione) ? g.pressione : (Math.abs(p - P.pressione(quota)) > 1 ? arrot(p, 0) : null),
      V: g.V, quotaEsterna: g.quotaEsterna, riferimento: g.riferimento, estate: stag("estate"), inverno: stag("inverno"),
      stima: { gg: ggUsati(), ore: stato.stima.ore, rendimento: stato.stima.rendimento, pci: stato.stima.pci, oreEq: stato.stima.oreEq, eer: stato.stima.eer } };
  }

  // ================================================================== calcolo e risultati
  function calcola() {
    clearTimeout(attesa);
    const p = pressioneCalcolo();
    aggiornaClima(p);
    const conf = configurazione();
    let r;
    try { r = calcolaConfigurazione(conf); } catch (e) { console.error(e); return; }
    risultati = { ...r, conf };
    aggiornaCampi();
    mostraGenerali(r, conf);
    ["estate", "inverno"].forEach((k) => mostraStagione(k, r[k]));
    mostraRiepilogo(r, conf);
    disegna(r);
  }
  const intesta = (cols) => `<thead><tr>${cols.map((c, i) => `<th scope="col"${i ? ' class="num"' : ""}>${c}</th>`).join("")}</tr></thead>`;
  const cellaN = (v, d, attr) => `<td class="num"${attr ? ` ${attr}` : ""} data-valore="${fin(v) ? v : ""}">${fmt(v, d)}</td>`;

  function mostraGenerali(r, conf) {
    selRif.value = String(stato.generali.riferimento);
    const s = serie(), g = stato.generali;
    const qc = quotaComune();
    quotaNota.textContent = `${fin(g.quota) ? `Altitudine scritta a mano (${fmt(g.quota, 0)} m${fin(qc) ? `; quella del comune è ${fmt(qc, 0)} m` : ""}).`
      : s ? `Altitudine del comune: ${fmt(conf.quota, 0)} m.` : `${S.stato().istat ? "Serie oraria non disponibile" : "Nessun comune scelto"}: altitudine ${fmt(conf.quota, 0)} m (valore del foglio).`} `
      + `Pressione di calcolo ${fmt(conf.p, 0)} Pa. Portata di aria esterna ${fmt(g.V * g.quotaEsterna / 100, 0)} m³/h, di ricircolo ${fmt(g.V * (1 - g.quotaEsterna / 100), 0)} m³/h.`;
    const e = r.estate, i = r.inverno;
    tabGen.innerHTML = `<table class="mensili ${K}gen"><caption class="solo-lettori">Conversione della portata in massa</caption>${intesta(["Conversione portata", "Estate", "Inverno"])}<tbody>`
      + `<tr><th scope="row">v di riferimento [m³/kg]</th>${cellaN(e.vref, 4)}${cellaN(i.vref, 4)}</tr>`
      + `<tr><th scope="row">ρ aria umida di riferimento [kg/m³]</th>${cellaN(e.rho, 4)}${cellaN(i.rho, 4)}</tr>`
      + `<tr><th scope="row">ṁ aria secca [kg/s]</th>${cellaN(e.mtot, 4, 'data-gen="estate.mtot"')}${cellaN(i.mtot, 4, 'data-gen="inverno.mtot"')}</tr>`
      + `<tr><th scope="row">ṁ aria secca [kg/h]</th>${cellaN(e.mtot * 3600, 0)}${cellaN(i.mtot * 3600, 0)}</tr>`
      + `<tr><th scope="row">ṁ aria esterna [kg/s]</th>${cellaN(e.mOA, 4)}${cellaN(i.mOA, 4)}</tr>`
      + `<tr><th scope="row">Frazione di ricircolo (AUTO)</th>${cellaN(e.fgen, 3)}${cellaN(i.fgen, 3)}</tr></tbody></table>`;
  }

  function mostraStagione(k, r) {
    const ui = UI[k];
    if (ui.statistica) ui.statistica.value = stato.estate.statistica;
    const m = stato[k].esterno, c = esternoClima(k), manuale = fin(m.t) || fin(m.ur);
    const s = serie();
    ui.fonteEsterno.textContent = c ? `Dal clima di ${s.comune || "questo comune"} (${s.sintetica ? "dati sintetici di prova, " : ""}serie dal ${dataIt(s.dal)} al ${dataIt(s.al)}): ${fmt(c.t, 1)} °C e UR ${fmt(c.ur, 1)} %. ${c.testo} Statistiche della serie scelta, non valori di norma.`
      + (manuale ? " Hai scritto a mano almeno un valore: il calcolo usa i tuoi." : "")
      : s ? "Troppe poche ore valide nella serie: valori del foglio, modificabili." : `${S.stato().istat ? "Serie oraria non disponibile" : "Nessun comune scelto"}: valori del foglio (${fmt(P.DATI_PREDEFINITI[k].esterno.t, 0)} °C, UR ${fmt(P.DATI_PREDEFINITI[k].esterno.ur, 0)} %), modificabili.`;
    ui.ripristina.hidden = !(manuale && c);
    // punti E, A, I
    const riga = (nome, q, cod) => `<tr data-punto="${cod}"><th scope="row">${nome}</th>${cellaN(q.t, 1)}${cellaN(q.ur, 1)}${cellaN(q.xg, 2)}${cellaN(q.h, 2)}${cellaN(q.tdew, 1)}${cellaN(q.twb, 1)}${cellaN(q.v, 4)}${cellaN(q.rho, 3)}</tr>`;
    ui.punti.innerHTML = `<table class="mensili ${K}punti"><caption class="solo-lettori">Punti di progetto – ${NOMI[k]}</caption>${intesta(["Punto", "T [°C]", "UR [%]", "x [g/kg]", "h [kJ/kg]", "T rugiada [°C]", "T bulbo umido [°C]", "v [m³/kg]", "ρ [kg/m³]"])}<tbody>`
      + riga("E – aria esterna", r.esterno, "E") + riga("A – ambiente", r.ambiente, "A") + riga("I – immissione (dai carichi)", r.immissione, "I") + "</tbody></table>"
      + `<p class="aiuto">ΔT di immissione |T ambiente − T immissione| = ${fmt(r.dT, 2)} K · fattore termico R = ${fmt(r.R, 3)}${k === "inverno" ? " (con Qs = − dispersioni)" : ""}.</p>`;
    ui.verifiche.textContent = r.verifiche === "OK" ? "Verifiche del punto di immissione: OK." : `Verifiche del punto di immissione: ${r.verifiche.trim()}`;
    ui.verifiche.classList.toggle("attenzione", r.verifiche !== "OK");
    mostraRighe(k, r);
    const U = r.uscita, I = r.immissione, sc = r.scostamento;
    const rr = (n, a, b, c2, d2, attr) => `<tr${attr ? ` ${attr}` : ""}><th scope="row">${n}</th>${cellaN(a, 2)}${cellaN(b, 1)}${cellaN(c2, 2)}${cellaN(d2, 2)}</tr>`;
    ui.confronto.innerHTML = `<table class="mensili ${K}confronto"><caption class="solo-lettori">Confronto uscita – immissione – ${NOMI[k]}</caption>${intesta(["Confronto", "T [°C]", "UR [%]", "x [g/kg]", "h [kJ/kg]"])}<tbody>`
      + rr("Uscita UTA (ultima riga)", U.t, U.ur, U.xg, U.h) + rr("Immissione richiesta (I)", I.t, I.ur, I.xg, I.h) + rr("Scostamento (uscita − immissione)", sc.t, sc.ur, sc.xg, sc.h, 'class="' + K + 'scostamento"') + "</tbody></table>";
    ui.esito.innerHTML = "";
    const dv = h("div"); dv.append(h("b", null, `Punto di immissione raggiungibile? ${r.raggiungibileTesto}.`), " ", r.esito);
    ui.esito.appendChild(dv);
    ui.esito.dataset.raggiungibile = r.raggiungibileTesto;
    ui.esito.classList.toggle("errore", !r.raggiungibile);
  }

  function mostraRiepilogo(r, conf) {
    const e = r.estate.riepilogo, i = r.inverno.riepilogo;
    const cifra = (v, d, u, testo, nota, chiave) => `<div class="cifra"><b data-cifra="${chiave}" data-valore="${v}">${fmt(v, d)}<small> ${u}</small></b><span>${testo}</span>${nota ? `<small>${nota}</small>` : ""}</div>`;
    cifre.innerHTML = cifra(e.frigoTotale, 1, "kW", "Potenza frigorifera (estate)", `sensibile ${fmt(e.frigoSensibile, 1)} · latente ${fmt(e.frigoLatente, 1)} kW`, "frigo")
      + cifra(i.preriscaldamento + i.postRiscaldamento, 1, "kW", "Potenza termica (inverno)", `preriscaldamento ${fmt(i.preriscaldamento, 1)} · post-riscaldamento ${fmt(i.postRiscaldamento, 1)} kW`, "termica")
      + cifra(e.condensa, 1, "kg/h", "Acqua condensata (estate)", `umidificazione invernale ${fmt(i.umidificazione, 1)} kg/h`, "acqua")
      + cifra(i.recuperata, 1, "kW", "Potenza recuperata (inverno)", e.recuperata ? `estate ${fmt(e.recuperata, 1)} kW` : "", "recuperata");
    const voci = [["frigoTotale", "Potenza frigorifera totale batterie [kW]", 2], ["frigoSensibile", "   di cui sensibile [kW]", 2], ["frigoLatente", "   di cui latente [kW]", 2],
      ["preriscaldamento", "Preriscaldamento [kW]", 2], ["postRiscaldamento", "Post-riscaldamento / riscaldamento [kW]", 2], ["condensa", "Acqua condensata [kg/h]", 2],
      ["umidificazione", "Acqua di umidificazione [kg/h]", 2], ["recuperata", "Potenza recuperata [kW]", 2], ["ventilatori", "Calore dei ventilatori [kW]", 2]];
    tabRiep.innerHTML = `<table class="mensili ${K}riepilogo"><caption class="solo-lettori">Riepilogo per stagione</caption>${intesta(["Riepilogo", "Estate", "Inverno"])}<tbody>`
      + voci.map(([c, n, d]) => `<tr><th scope="row">${n.replace(/^ +/, "&emsp;")}</th>${cellaN(e[c], d, `data-riep="estate.${c}"`)}${cellaN(i[c], d, `data-riep="inverno.${c}"`)}</tr>`).join("")
      + `<tr><th scope="row">Punto di immissione raggiungibile?</th><td class="num ${r.estate.raggiungibile ? "" : K + "no"}" data-riep="estate.raggiungibile">${r.estate.raggiungibileTesto}</td><td class="num ${r.inverno.raggiungibile ? "" : K + "no"}" data-riep="inverno.raggiungibile">${r.inverno.raggiungibileTesto}</td></tr>`
      + "</tbody></table>";
    esitiRiep.innerHTML = "";
    ["estate", "inverno"].forEach((k) => {
      const m = h("div", `messaggio ${r[k].raggiungibile ? "" : "errore"}`);
      const dv = h("div"); dv.append(h("b", null, `${NOMI[k]}: `), r[k].esito); m.appendChild(dv);
      esitiRiep.appendChild(m);
    });
    const st = r.stima, sd = conf.stima;
    ggNota.textContent = fin(stato.stima.gg) ? `Gradi giorno scritti a mano${fin(ggComune) ? ` (DPR 412/93 per il comune: ${fmt(ggComune, 0)})` : ""}.`
      : fin(ggComune) ? `Gradi giorno del DPR 412/93 per ${S.stato().comune || "il comune"}: ${fmt(ggComune, 0)}.` : "Gradi giorno del foglio (Milano, 2404): scegli un comune o scrivi il valore.";
    const rs = (n, v, d, u, c) => `<tr><th scope="row">${n}</th>${cellaN(v, d, `data-stima="${c}"`)}<td>${u}</td></tr>`;
    tabStima.innerHTML = `<table class="mensili ${K}stima"><caption class="solo-lettori">Stima stagionale</caption>${intesta(["Stima", "Valore", "u.m."])}<tbody>`
      + rs("ṁ aria esterna (inverno)", st.mOA, 4, "kg/s", "mOA") + rs("εs recuperatore (prima riga invernale)", st.eps, 2, "–", "eps")
      + rs("Fabbisogno senza recupero ṁ·cp·GG·ore", st.fabbisogno, 0, "kWh", "fabbisogno") + rs("Energia recuperata = fabbisogno·ε", st.recuperata, 0, "kWh", "recuperata")
      + rs("Fabbisogno netto ventilazione", st.netto, 0, "kWh", "netto") + rs(`Combustibile = netto/(η·PCI)`, st.combustibile, 0, "Sm³", "combustibile")
      + rs("Energia frigorifera = P frigo · ore eq.", st.frigo, 0, "kWh", "frigo") + rs("Energia elettrica frigo = E frigo/EER", st.elettrica, 0, "kWh", "elettrica")
      + `</tbody></table>`;
    void sd;
  }

  // ---- diagramma
  function nuvolaOra() {
    const s = serie();
    if (!stato.nuvola || !s) { D.togli("ore"); return; }
    const V = P.vettori(s.t, s.ur, s.p);
    D.nuvola("ore", "#8c8c8c", { t: s.t, x: V.x }, { etichetta: "ore della serie", nota: `(${(s.n - s.mancanti).toLocaleString("it-IT", { useGrouping: "always" })} ore, contesto)` });
  }
  const uguali = (a, b) => Math.abs(a.t - b.t) < 0.005 && Math.abs(a.x - b.x) < 2e-6;
  function disegna(r) {
    D.pressione(r.estate.p);
    const s = serie();
    D.titolo(s ? `${titolo} – ${s.comune || S.stato().comune || ""}` : titolo);
    ["estate", "inverno"].forEach((k) => {
      const q = r[k], NOME = NOMI[k];
      const pts = [{ t: q.esterno.t, x: q.esterno.x }];
      const mol = D.modo() === "mollier", base = mol ? "l" : k === "estate" ? "t" : "b", opposta = { t: "b", b: "t", r: "l", l: "r" };
      let prima = null;
      q.righe.forEach((o) => {
        if (o.codice === 1 || uguali(o.uscita, pts[pts.length - 1])) return;
        // etichette di punti vicini (meno di 24 px) da parti opposte, per non sovrapporle
        let pos = base;
        const a = D.pixel(o.t, o.x), b = prima && D.pixel(prima.t, prima.x);
        if (a && b && Math.hypot(a[0] - b[0], a[1] - b[1]) < 24) pos = opposta[prima.posizione];
        const q2 = { t: o.t, x: o.x, etichetta: String(o.n), posizione: pos };
        pts.push(q2); prima = q2;
      });
      D.spezzata(`trasf-${k}`, pts, { colore: k, spessore: 3.5, etichetta: `${NOME}: trasformazioni`, nota: q.raggiungibile ? "" : "(immissione non raggiunta)" });
      const dist = Math.hypot((q.immissione.t - q.ambiente.t) / 60, (q.immissione.x - q.ambiente.x) / 0.03);
      if (dist > 1e-4) D.retta(`retta-${k}`, q.ambiente, { verso: q.immissione }, { colore: k, tratteggio: [6, 4], estensione: 2, etichetta: `${NOME}: retta ambiente`, nota: `(R = ${fmt(q.R, 2)})` });
      else D.togli(`retta-${k}`);
      D.punto(`E-${k}`, q.esterno, { colore: k, simbolo: "rombo", etichetta: "E", posizione: "r", legenda: false });
      D.punto(`A-${k}`, q.ambiente, { colore: k, simbolo: "quadrato", etichetta: "A", posizione: mol ? "r" : "l", legenda: false });
      D.punto(`I-${k}`, q.immissione, { colore: k, simbolo: "triangolo", etichetta: "I", posizione: mol || k !== "estate" ? "r" : "l", legenda: false });
    });
  }
  function fontiDiagramma() {
    const s = S && S.serie(), out = [];
    if (s) out.push(`Serie oraria: ${s.comune || ""}, ${s.fonte}${s.licenza && s.licenza !== "—" ? ` (${s.licenza})` : ""}.`);
    if (L) {
      const lv = L.valori(), pc = (v) => `${fmt(v, v % 1 ? 1 : 0)} %`;
      const man = ["estate", "inverno"].filter((k) => fin(stato[k].esterno.t) || fin(stato[k].esterno.ur));
      out.push(`Condizioni esterne ${s ? `dalla serie (Inverno ${pc(lv.inverno)}, Estate ${pc(lv.estate)}: statistiche, non valori di norma)` : "del foglio"}${man.length ? `; scritte a mano: ${man.map((k) => NOMI[k].toLowerCase()).join(", ")}` : ""}.`);
    }
    out.push("E esterno, A ambiente, I immissione; numeri = righe della sequenza. Calcolo come psicro_UTA.xlsx (EuGEnio).");
    return out;
  }

  // ---- file CSV e JSON
  function scaricaTesto(tipo) {
    if (!risultati) calcola();
    const r = risultati, c = r.conf, d = S.stato(), s = serie(), lv = L.valori();
    const data = new Date().toISOString().slice(0, 10);
    if (tipo === "json") {
      const punto = (q) => ({ t: q.t, ur: q.ur, xg: q.xg, h: q.h, tdew: q.tdew, twb: q.twb, v: q.v, rho: q.rho });
      const stag = (k) => {
        const q = r[k];
        return { esterno: punto(q.esterno), ambiente: punto(q.ambiente), immissione: punto(q.immissione), R: q.R, dT: q.dT, mtot: q.mtot, mOA: q.mOA, verifiche: q.verifiche,
          righe: q.righe.map((o, i) => ({ n: o.n, tipo: o.tipo, P1: c[k].righe[i][1], P2: c[k].righe[i][2], P3: c[k].righe[i][3], uscita: punto(o.uscita), mdot: o.mdot, Qs: o.Qs, Ql: o.Ql, Qt: o.Qt, acqua: o.acqua, nota: o.nota })),
          riepilogo: q.riepilogo, uscita: punto(q.uscita), scostamento: q.scostamento, raggiungibile: q.raggiungibileTesto, esito: q.esito };
      };
      const j = { fonte: "EuGEnio – eugenio.statocritico.it, Trattamento aria › Trasformazioni (UTA)", licenza: "CC BY 4.0", data,
        avvertenza: "Pagina sperimentale. Condizioni esterne da statistiche della serie oraria scelta, non valori di norma. Stesse formule del foglio psicro_UTA.xlsx (ASHRAE 2017).",
        comune: d.istat ? { istat: d.istat, nome: d.comune, zona: d.zona } : null,
        serie: s ? { dal: s.dal, al: s.al, anni: d.anni, fonte: s.fonte, licenza: s.licenza, sintetica: !!s.sintetica } : null,
        livelli: lv, statisticaEstiva: stato.estate.statistica, configurazione: c, risultati: { estate: stag("estate"), inverno: stag("inverno"), stima: r.stima } };
      return salva(new Blob([JSON.stringify(j, null, 2)], { type: "application/json" }), `${nomeBase()}.json`);
    }
    const n = (v, dd = 4) => (fin(v) ? String(Math.round(v * Math.pow(10, dd)) / Math.pow(10, dd)).replace(".", ",") : "");
    const q = (x) => { const t = String(x === null || x === undefined ? "" : x); return /[;"\n]/.test(t) ? `"${t.replace(/"/g, '""')}"` : t; };
    const R = [];
    const riga = (...a) => R.push(a.map(q).join(";"));
    riga("EuGEnio – Trasformazioni dell'aria (UTA)", data);
    riga("Comune", d.istat ? `${d.comune} (${d.istat})` : "nessuno");
    if (s) riga("Serie oraria", `${dataIt(s.dal)} – ${dataIt(s.al)}`, s.fonte, s.sintetica ? "DATI SINTETICI DI PROVA" : "");
    riga("Livello di progetto", `inverno ${n(lv.inverno, 1)} %`, `estate ${n(lv.estate, 1)} %`, "statistiche della serie, non valori di norma");
    riga("");
    riga("DATI GENERALI");
    riga("Altitudine [m]", n(c.quota, 0)); riga("Pressione di calcolo [Pa]", n(c.p, 0)); riga("Portata di mandata [m³/h]", n(c.V, 0));
    riga("Aria esterna [%]", n(c.quotaEsterna, 1)); riga("Riferimento della portata", P.RIF_PORTATA[c.riferimento]);
    ["estate", "inverno"].forEach((k) => {
      const x = r[k];
      riga(""); riga(k.toUpperCase());
      riga("T esterna [°C]", n(c[k].esterno.t, 1)); riga("UR esterna [%]", n(c[k].esterno.ur, 1));
      riga("T ambiente [°C]", n(c[k].ambiente.t, 1)); riga("UR ambiente [%]", n(c[k].ambiente.ur, 1));
      riga(k === "estate" ? "Carico sensibile [W]" : "Dispersioni [W]", n(c[k].Qs, 0)); riga("Carico latente [W]", n(c[k].Ql, 0));
      riga("ṁ aria secca [kg/s]", n(x.mtot)); riga("ΔT immissione [K]", n(x.dT, 2)); riga("Fattore termico R", n(x.R, 3)); riga("Verifiche", x.verifiche);
      riga("Punto", "T [°C]", "UR [%]", "x [g/kg]", "h [kJ/kg]", "T rugiada [°C]", "T bulbo umido [°C]", "v [m³/kg]", "ρ [kg/m³]");
      [["E esterno", x.esterno], ["A ambiente", x.ambiente], ["I immissione", x.immissione]].forEach(([nn, p]) => riga(nn, n(p.t, 2), n(p.ur, 2), n(p.xg, 3), n(p.h, 2), n(p.tdew, 2), n(p.twb, 2), n(p.v, 4), n(p.rho, 4)));
      riga("N", "Tipo", "P1", "P2", "P3", "T [°C]", "UR [%]", "x [g/kg]", "h [kJ/kg]", "T rugiada [°C]", "T bulbo umido [°C]", "ṁ [kg/s]", "Q sensibile [kW]", "Q latente [kW]", "Q totale [kW]", "Acqua [kg/h]", "Note");
      riga("0", "Ingresso: aria esterna (punto E)", "", "", "", n(x.esterno.t, 2), n(x.esterno.ur, 2), n(x.esterno.xg, 3), n(x.esterno.h, 2), n(x.esterno.tdew, 2), n(x.esterno.twb, 2));
      x.righe.forEach((o, i) => riga(o.n, o.tipo, c[k].righe[i][1], c[k].righe[i][2], c[k].righe[i][3], n(o.t, 2), n(o.uscita.ur, 2), n(o.uscita.xg, 3), n(o.uscita.h, 2),
        n(o.uscita.tdew, 2), n(o.uscita.twb, 2), n(o.mdot), n(o.Qs, 3), n(o.Ql, 3), n(o.Qt, 3), n(o.acqua, 3), o.nota));
      const e = x.riepilogo;
      riga("Potenza frigorifera totale [kW]", n(e.frigoTotale, 3)); riga("  di cui sensibile [kW]", n(e.frigoSensibile, 3)); riga("  di cui latente [kW]", n(e.frigoLatente, 3));
      riga("Preriscaldamento [kW]", n(e.preriscaldamento, 3)); riga("Post-riscaldamento / riscaldamento [kW]", n(e.postRiscaldamento, 3));
      riga("Acqua condensata [kg/h]", n(e.condensa, 3)); riga("Acqua di umidificazione [kg/h]", n(e.umidificazione, 3)); riga("Potenza recuperata [kW]", n(e.recuperata, 3));
      riga("Calore dei ventilatori [kW]", n(e.ventilatori, 3)); riga("Punto di immissione raggiungibile?", x.raggiungibileTesto, x.esito);
    });
    const st = r.stima;
    riga(""); riga("STIMA STAGIONALE (indicativa)");
    riga("Gradi giorno [K·giorno]", n(c.stima.gg, 0)); riga("Ore al giorno", n(c.stima.ore, 1)); riga("Rendimento", n(c.stima.rendimento, 2)); riga("PCI [kWh/Sm³]", n(c.stima.pci, 2));
    riga("Ore equivalenti estive [h]", n(c.stima.oreEq, 0)); riga("EER", n(c.stima.eer, 2));
    riga("Fabbisogno senza recupero [kWh]", n(st.fabbisogno, 0)); riga("Energia recuperata [kWh]", n(st.recuperata, 0)); riga("Fabbisogno netto [kWh]", n(st.netto, 0));
    riga("Combustibile [Sm³]", n(st.combustibile, 0)); riga("Energia frigorifera [kWh]", n(st.frigo, 0)); riga("Energia elettrica frigo [kWh]", n(st.elettrica, 0));
    riga(""); riga("Fonte", "EuGEnio – eugenio.statocritico.it (CC BY 4.0). Pagina sperimentale; stesse formule del foglio psicro_UTA.xlsx.");
    return salva(new Blob(["﻿" + R.join("\r\n")], { type: "text/csv;charset=utf-8" }), `${nomeBase()}.csv`);
  }

  // ================================================================== avvio
  ["estate", "inverno"].forEach(costruisciStagione);
  S.su(async (d) => {
    if (d.istat && stato.istat && d.istat !== stato.istat) {        // cambio di comune: i valori legati al comune tornano automatici
      stato.estate.esterno = { t: null, ur: null }; stato.inverno.esterno = { t: null, ur: null };
      stato.generali.quota = null; stato.stima.gg = null;
      campi.forEach((c) => c.mostra(true));
    }
    if (d.istat) stato.istat = d.istat;
    salvaStato();
    if (d.istat !== ggIstat) await caricaGG(d.istat);
    nuvolaOra();
    calcola();
  });
  L.su(() => { climaChiave = ""; calcola(); });
  D.su("modo", () => { if (risultati) setTimeout(() => disegna(risultati), 0); });   // etichette vicine: posizioni ricalcolate nella nuova vista
  calcola();
  void pannello;
  window.EUGENIO_ARIA_PAGINA = { diagramma: D, scelta: S, livello: L, pura: PURA,
    stato: () => JSON.parse(JSON.stringify(stato)), risultati: () => risultati, configurazione, calcola, clima: () => clima };
})(typeof self !== "undefined" ? self : globalThis);
