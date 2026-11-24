"use strict";
// Fotovoltaico › «CER – Sviluppo impianti FV» (fv-cer.html, 24/11/2026, richiesta di Paolo; proposta in
// documenti/PROPOSTA_TERRENI_CER_2026-11-24.md del Project). Calcoli senza DOM, usati da fv_cer.js e dalle prove con Node.
//
//  Anno tipo: 8.760 ore in ora locale italiana (CET/CEST), indice = giorno dell'anno non bisestile × 24 + ora; il 29
//  febbraio si scarta. Le curve di carico e la produzione si allineano su questo calendario.
//
//  leggiCurve(testo, { decimalePunto }) → { serie: Map(id → Float64Array(8760) kWh), copertura, passoMinuti, anni, avvisi }
//     formati accettati (separatore ; , o tabulazione):
//       lungo   id;data_ora;kwh            (anche pod/codice, timestamp/data, energia/consumo/valore)
//       largo   data_ora;<id1>;<id2>…      una colonna per edificio
//       giorno  id;data;v1;…;v24 (o v1…v96) una riga per giorno, valori in kWh dell'ora o del quarto d'ora
//     valori in kWh dell'intervallo, ora d'inizio dell'intervallo in ora locale; più anni → media per ora dell'anno tipo;
//     ore mancanti → media della stessa ora nello stesso mese (dichiarata nella copertura).
//  produzionePerKwp(clima, lat, lon, { inclinazione, orientamento, perdite }) → Float64Array(8760) kWh/kWp
//     clima = risposta di /api/edifici/clima-orario/{istat} (UTC, media dell'ora precedente): sole e trasposizione Perez
//     di edifici_calcoli.js, temperatura delle celle (NOCT 45 °C, −0,37 %/°C), perdite 14 % predefinite.
//  simula(consumi, pKwp, P, opz) → energia oraria con l'accumulo (E = h × P, si carica solo dal fotovoltaico)
//  dimensiona(consumi, pKwp, opz) → P* più alta con quota condivisa ≥ q_min (bisezione), impianti e superfici
//  terreni: fabbisognoTerreni, punteggioTerreno; distanzaM (haversine)
(function (radice) {
  const ORE = 8760;
  const GIORNI_MESE = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  const INIZIO_MESE = GIORNI_MESE.reduce((a, g, i) => (a.push(i ? a[i - 1] + GIORNI_MESE[i - 1] : 0), a), []);
  const ED = () => radice.EUGENIO_EDIFICI || (typeof require === "function" ? require("./edifici_calcoli.js") : null);

  // parametri predefiniti (valori indicativi, scritti nella pagina e nei file)
  const PREDEFINITI = {
    h: 0, crate: 0.5, rendimento: 0.9, socMin: 0.1, qMin: 0.6, denominatore: "produzione",
    tipo: "fisso", inclinazione: 25, orientamento: 180, perdite: 0.14, potenzaMassimaImpianto: 1000,
    potenzaMassima: null, distanzaKm: 5, nTerreni: 5, tolleranza: 1.3,
  };
  // superficie specifica per tipo di impianto (ha per MWp, indicativa: da confermare, scelta T6 della proposta) e quota
  // di suolo agricolo che conta per la L.R. Emilia-Romagna 5/2026, art. 5 (agrivoltaico 30 %, a terra tutta la recinzione)
  const TIPI = {
    fisso: { nome: "a terra, strutture fisse", haMw: 1.4, quotaSau: 1 },
    agrivoltaico: { nome: "agrivoltaico elevato", haMw: 2.5, quotaSau: 0.3 },
  };
  const ACCESSORI_HA = 0.02;          // cabina di consegna, accessi, per impianto
  const ACCUMULO_HA_MWH = 0.01;       // contenitori dell'accumulo e distanze, per MWh

  // ------------------------------------------------------------------ calendario
  const bisestile = (a) => (a % 4 === 0 && a % 100 !== 0) || a % 400 === 0;
  function slot(mese, giorno, ora) {          // mese 1-12; -1 per il 29 febbraio
    if (mese === 2 && giorno === 29) return -1;
    if (!(mese >= 1 && mese <= 12) || !(giorno >= 1 && giorno <= GIORNI_MESE[mese - 1]) || !(ora >= 0 && ora < 24)) return -2;
    return (INIZIO_MESE[mese - 1] + giorno - 1) * 24 + ora;
  }
  const meseDiSlot = (s) => { const g = Math.floor(s / 24); let m = 0; while (m < 11 && INIZIO_MESE[m + 1] <= g) m++; return m; };
  // ultima domenica del mese (UTC), per l'ora legale europea: dalle 01:00 UTC dell'ultima domenica di marzo alle 01:00 UTC
  // dell'ultima domenica di ottobre
  function ultimaDomenica(anno, mese0) { const d = new Date(Date.UTC(anno, mese0 + 1, 0)); return d.getUTCDate() - d.getUTCDay(); }
  function scartoRoma(ms) {
    const d = new Date(ms), a = d.getUTCFullYear();
    const inizio = Date.UTC(a, 2, ultimaDomenica(a, 2), 1), fine = Date.UTC(a, 9, ultimaDomenica(a, 9), 1);
    return ms >= inizio && ms < fine ? 2 : 1;
  }
  function slotDaUtc(ms) {
    const l = new Date(ms + scartoRoma(ms) * 3600000);
    return slot(l.getUTCMonth() + 1, l.getUTCDate(), l.getUTCHours());
  }

  // ------------------------------------------------------------------ lettura delle curve
  // come EUGENIO_TABELLE.numero: «1.234,5», «1234,5», «1234.5», «0.25»; con decimalePunto (file convertiti dal server)
  // il punto è sempre il separatore decimale
  function numero(v, decimalePunto = false) {
    if (v === null || v === undefined) return null;
    let t = String(v).trim().replace(/[\s\u00a0']/g, "").replace(/^"|"$/g, "");
    if (!t) return null;
    if (decimalePunto) t = t.replace(/,/g, "");
    else if (t.includes(",") && t.includes(".")) t = t.lastIndexOf(",") > t.lastIndexOf(".") ? t.replace(/\./g, "").replace(",", ".") : t.replace(/,/g, "");
    else if (t.includes(",")) t = /^-?\d{1,3}(,\d{3}){2,}$/.test(t) ? t.replace(/,/g, "") : t.replace(",", ".");
    else if (/^-?\d{1,3}(\.\d{3})+$/.test(t)) t = t.replace(/\./g, "");
    if (!/^[-+]?(\d+\.?\d*|\.\d+)(e[-+]?\d+)?$/i.test(t)) return null;
    const x = Number(t);
    return Number.isFinite(x) ? x : null;
  }
  // data e ora: «2025-01-31 13:15», «2025-01-31T13:15:00», «31/01/2025 13:15», «31-01-2025 13.15»; senza ora → 00:00
  function dataOra(s) {
    s = String(s || "").trim().replace(/^"|"$/g, "");
    let m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})(?:[T ](\d{1,2})[:.](\d{2})(?::\d{2}(?:\.\d+)?)?)?(?:Z|[+-]\d{2}:?\d{2})?$/);
    if (m) return { a: +m[1], mese: +m[2], g: +m[3], h: m[4] === undefined ? 0 : +m[4], min: m[5] === undefined ? 0 : +m[5] };
    m = s.match(/^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})(?:[ T](\d{1,2})[:.](\d{2})(?::\d{2})?)?$/);
    if (m) return { a: +m[3], mese: +m[2], g: +m[1], h: m[4] === undefined ? 0 : +m[4], min: m[5] === undefined ? 0 : +m[5] };
    return null;
  }
  function separatore(riga) {
    const c = { ";": 0, "\t": 0, ",": 0 };
    for (const ch of riga) if (ch in c) c[ch]++;
    return c[";"] ? ";" : c["\t"] ? "\t" : ",";
  }
  function righe(testo, sep) {
    return testo.split(/\r?\n/).map((r) => r.trim()).filter((r) => r && !r.startsWith("#") && !/^"?Fonte: EuGEnio/i.test(r))
      .map((r) => r.split(sep).map((x) => x.trim().replace(/^"|"$/g, "")));
  }
  const norm = (c) => String(c || "").trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  const COL_ID = ["id", "pod", "codice", "cod", "codice_pod", "edificio", "sede"];
  const COL_DATA = ["data_ora", "dataora", "timestamp", "data", "giorno", "ora", "datetime", "date", "time"];
  const COL_VAL = ["kwh", "energia", "consumo", "valore", "energia_kwh", "consumo_kwh", "prelievo", "prelievo_kwh"];

  function leggiCurve(testo, { decimalePunto = false } = {}) {
    const avvisi = [];
    const linee = testo.split(/\r?\n/).filter((r) => r.trim());
    if (linee.length < 2) throw new Error("il file delle curve non contiene righe di dati");
    const sep = separatore(linee.find((r) => !r.trim().startsWith("#")) || linee[0]);
    const tab = righe(testo, sep);
    const testa = tab[0].map(norm), corpo = tab.slice(1);
    const col = (nomi) => testa.findIndex((x) => nomi.includes(x));
    const iId = col(COL_ID), iData = col(COL_DATA), iVal = col(COL_VAL);
    const somme = new Map();                  // id → { v: Float64Array, n: Uint16Array (anni per ora), anni: Map(anno → Set slot) }
    let passi = new Map();
    const aggiungi = (id, d, kwh) => {
      if (kwh === null || !d) return;
      const s = slot(d.mese, d.g, d.h);
      if (s === -1) return;
      if (s < 0) throw new Error(`data non valida per «${id}»: ${d.g}/${d.mese}/${d.a} ${d.h}`);
      let x = somme.get(id);
      if (!x) { x = { v: new Map(), anni: new Set() }; somme.set(id, x); }
      const k = d.a * 10000 + s;                // somma per anno e ora (quarti d'ora sommati)
      x.v.set(k, (x.v.get(k) || 0) + kwh);
      x.anni.add(d.a);
    };
    let formato;
    const giornalieri = testa.filter((x, i) => i !== iId && i !== iData).length;
    if (iId >= 0 && iData >= 0 && iVal >= 0) {
      formato = "lungo";
      let prec = null;
      for (const r of corpo) {
        const d = dataOra(r[iData]);
        if (!d) continue;
        if (prec && prec.id === r[iId]) {
          const dm = (Date.UTC(d.a, d.mese - 1, d.g, d.h, d.min) - prec.t) / 60000;
          if (dm > 0) passi.set(dm, (passi.get(dm) || 0) + 1);
        }
        prec = { id: r[iId], t: Date.UTC(d.a, d.mese - 1, d.g, d.h, d.min) };
        aggiungi(String(r[iId]), d, numero(r[iVal], decimalePunto));
      }
    } else if (iId >= 0 && iData >= 0 && (giornalieri === 24 || giornalieri === 96)) {
      formato = "giorno";
      const passo = giornalieri === 24 ? 60 : 15;
      passi.set(passo, 1);
      const valori = testa.map((_, i) => i).filter((i) => i !== iId && i !== iData);
      for (const r of corpo) {
        const d = dataOra(r[iData]);
        if (!d) continue;
        valori.forEach((i, k) => {
          const min = k * passo;
          aggiungi(String(r[iId]), { a: d.a, mese: d.mese, g: d.g, h: Math.floor(min / 60), min: min % 60 }, numero(r[i], decimalePunto));
        });
      }
    } else if (iData >= 0 || testa.length >= 2) {
      formato = "largo";
      const iD = iData >= 0 ? iData : 0;
      const ids = testa.map((_, i) => i).filter((i) => i !== iD);
      let prec = null;
      for (const r of corpo) {
        const d = dataOra(r[iD]);
        if (!d) continue;
        const t = Date.UTC(d.a, d.mese - 1, d.g, d.h, d.min);
        if (prec !== null && t > prec) passi.set((t - prec) / 60000, (passi.get((t - prec) / 60000) || 0) + 1);
        prec = t;
        for (const i of ids) aggiungi(String(tab[0][i]).trim(), d, numero(r[i], decimalePunto));
      }
    } else throw new Error("formato delle curve non riconosciuto: servono le colonne id, data_ora e kwh (o una colonna per edificio)");
    if (!somme.size) throw new Error("nessun valore letto: controlla le colonne della data e dei consumi");
    const passoMinuti = [...passi.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] || 60;
    if (![15, 30, 60].includes(passoMinuti)) avvisi.push(`passo dei dati di ${passoMinuti} minuti: le ore si ottengono sommando`);
    const serie = new Map(), copertura = new Map(), anni = new Set();
    for (const [id, x] of somme) {
      const v = new Float64Array(ORE), n = new Uint8Array(ORE);
      for (const [k, kwh] of x.v) { const s = k % 10000; v[s] += kwh; n[s]++; }
      x.anni.forEach((a) => anni.add(a));
      let presenti = 0;
      for (let s = 0; s < ORE; s++) if (n[s]) { v[s] /= n[s]; presenti++; }
      // ore mancanti: media della stessa ora nello stesso mese
      if (presenti < ORE && presenti > 0) {
        const somma = new Float64Array(12 * 24), conta = new Uint32Array(12 * 24);
        for (let s = 0; s < ORE; s++) if (n[s]) { const k = meseDiSlot(s) * 24 + (s % 24); somma[k] += v[s]; conta[k]++; }
        const tutte = v.reduce((a, b) => a + b, 0) / presenti;
        for (let s = 0; s < ORE; s++) if (!n[s]) { const k = meseDiSlot(s) * 24 + (s % 24); v[s] = conta[k] ? somma[k] / conta[k] : tutte; }
      }
      serie.set(id, v);
      copertura.set(id, presenti / ORE);
    }
    return { serie, copertura, passoMinuti, anni: [...anni].sort(), formato, avvisi };
  }
  const totale = (v) => { let s = 0; for (let i = 0; i < v.length; i++) s += v[i]; return s; };
  function somma(vettori) { const o = new Float64Array(ORE); for (const v of vettori) for (let i = 0; i < ORE; i++) o[i] += v[i]; return o; }
  function riepilogoCurva(v, pKwp = null) {
    let picco = 0, sole = 0;
    const mesi = new Array(12).fill(0), ordinate = Float64Array.from(v).sort();
    for (let s = 0; s < ORE; s++) { picco = Math.max(picco, v[s]); mesi[meseDiSlot(s)] += v[s]; if (pKwp && pKwp[s] > 0) sole += v[s]; }
    const tot = totale(v);
    return { kwh: tot, picco_kw: picco, base_kw: ordinate[Math.floor(0.05 * ORE)], mesi, kwhOreSole: pKwp ? sole : null, quotaOreSole: pKwp && tot ? sole / tot : null };
  }

  // ------------------------------------------------------------------ produzione per kWp
  function produzionePerKwp(clima, lat, lon, { inclinazione = 25, orientamento = 180, perdite = 0.14, gamma = -0.0037, noct = 45 } = {}) {
    const E = ED();
    if (!E || !clima || !Array.isArray(clima.ghi)) throw new Error("clima orario mancante");
    const out = new Float64Array(ORE), conta = new Uint8Array(ORE);
    const iso = /(Z|[+-]\d{2}:?\d{2})$/.test(clima.inizio) ? clima.inizio : `${clima.inizio}Z`;   // l'archivio è in UTC
    const t0 = Date.parse(iso), passo = clima.passo_ore || 1;
    for (let i = 0; i < clima.ghi.length; i++) {
      const fine = t0 + i * passo * 3600000, s = slotDaUtc(fine - 3600000);   // valore dell'ora precedente
      if (s < 0) continue;
      conta[s]++;
      const ghi = clima.ghi[i];
      if (!(ghi > 0)) continue;
      const dhi = clima.dhi && clima.dhi[i] !== null && clima.dhi[i] !== undefined ? clima.dhi[i] : 0.3 * ghi;
      const sole = E.sole(new Date(fine - 1800000), lat, lon);
      if (sole.altezza <= 0) continue;
      const poa = E.trasponi(ghi, dhi, sole, inclinazione, orientamento).poa;
      const ta = clima.t && clima.t[i] !== null && clima.t[i] !== undefined ? clima.t[i] : 15;
      const tc = ta + poa * (noct - 20) / 800;
      out[s] += Math.max(0, poa / 1000 * (1 + gamma * (tc - 25)) * (1 - perdite));
    }
    for (let s = 0; s < ORE; s++) if (conta[s] > 1) out[s] /= conta[s];
    return out;
  }

  // ------------------------------------------------------------------ simulazione con l'accumulo
  // consumi e pKwp: Float64Array(8760) kWh; P in kW; E accumulo = h × P (kWh), potenza = crate × E
  function simula(consumi, pKwp, P, { h = 0, crate = 0.5, rendimento = 0.9, socMin = 0.1, dettaglio = false } = {}) {
    const E = h * P, Pb = E * crate, eta = Math.sqrt(rendimento), Emin = socMin * E;
    let soc = Emin, prod = 0, imm = 0, cond = 0, car = 0, sca = 0, cons = 0;
    const ore = dettaglio ? { prod: new Float64Array(ORE), imm: new Float64Array(ORE), cond: new Float64Array(ORE) } : null;
    for (let s = 0; s < ORE; s++) {
      const p = P * pKwp[s], c = consumi[s];
      let carica = 0, scarica = 0;
      if (E > 0) {
        carica = Math.min(Math.max(p - c, 0), Pb, (E - soc) / eta);
        soc += carica * eta;
        scarica = Math.min(Math.max(c - (p - carica), 0), Pb, Math.max(0, soc - Emin) * eta);
        soc -= scarica / eta;
      }
      const im = p - carica + scarica, ec = Math.min(im, c);
      prod += p; imm += im; cond += ec; car += carica; sca += scarica; cons += c;
      if (ore) { ore.prod[s] = p; ore.imm[s] = im; ore.cond[s] = ec; }
    }
    return { P, E, Pb, produzione: prod, immessa: imm, condivisa: cond, carica: car, scarica: sca, consumi: cons,
      quotaProduzione: prod ? cond / prod : 1, quotaImmessa: imm ? cond / imm : 1, autosufficienza: cons ? cond / cons : 0, ore };
  }
  const quotaDi = (r, den) => (den === "immessa" ? r.quotaImmessa : r.quotaProduzione);

  // P* più alta (kW, arrotondata per difetto al kW) con quota condivisa ≥ qMin; la quota scende al crescere di P
  function dimensiona(consumi, pKwp, opz = {}) {
    const o = { ...PREDEFINITI, ...opz };
    const resa = totale(pKwp), cons = totale(consumi);
    if (!(resa > 0)) throw new Error("produzione nulla: controlla il clima del comune");
    if (!(cons > 0)) return { P: 0, motivo: "consumi nulli", ...vuoto(o) };
    const q = (P) => quotaDi(simula(consumi, pKwp, P, o), o.denominatore);
    let lo = 0, hi = Math.max(1, 3 * cons / resa);
    let giri = 0;
    while (q(hi) >= o.qMin && giri++ < 20) hi *= 2;
    for (let i = 0; i < 50 && hi - lo > 0.5; i++) { const m = (lo + hi) / 2; if (q(m) >= o.qMin) lo = m; else hi = m; }
    let P = Math.floor(lo), motivo = "quota condivisa minima";
    if (o.potenzaMassima && P > o.potenzaMassima) { P = Math.floor(o.potenzaMassima); motivo = "potenza massima indicata"; }
    if (P < 1) return { P: 0, motivo: "nemmeno 1 kW rispetta la quota condivisa minima", ...vuoto(o) };
    const r = simula(consumi, pKwp, P, { ...o, dettaglio: false });
    return { ...r, motivo, quota: quotaDi(r, o.denominatore), resa_kwh_kwp: resa, ...impianti(P, r.E, o) };
  }
  function vuoto(o) { return { E: 0, produzione: 0, condivisa: 0, quota: null, impianti: [], nImpianti: 0, haTotali: 0, haSau: 0, tipo: o.tipo }; }
  // impianti da P_max al massimo, tutti uguali; superficie di ognuno (indicativa) e quota che conta come suolo agricolo
  function impianti(P, E, o = PREDEFINITI) {
    const t = TIPI[o.tipo] || TIPI.fisso, pm = o.potenzaMassimaImpianto || 1000;
    const n = P > 0 ? Math.ceil(P / pm - 1e-9) : 0;
    const lista = [];
    for (let i = 0; i < n; i++) {
      const p = P / n, e = E / n;
      const ha = p / 1000 * t.haMw + ACCESSORI_HA + e / 1000 * ACCUMULO_HA_MWH;
      lista.push({ kw: p, kwh_accumulo: e, ha, haMin: ha, haMax: ha * (o.tolleranza || 1.3), haSau: ha * t.quotaSau });
    }
    return { impianti: lista, nImpianti: n, haTotali: lista.reduce((s, x) => s + x.ha, 0), haSau: lista.reduce((s, x) => s + x.haSau, 0),
      tipo: o.tipo, tipoNome: t.nome, haMw: t.haMw };
  }

  // ------------------------------------------------------------------ terreni
  function distanzaM(lon1, lat1, lon2, lat2) {
    const r = Math.PI / 180, dLat = (lat2 - lat1) * r, dLon = (lon2 - lon1) * r;
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin(dLon / 2) ** 2;
    return 2 * 6371000 * Math.asin(Math.min(1, Math.sqrt(a)));
  }
  const PESI = { distanza: 35, superficie: 30, coltura: 20, unico: 15 };
  // classe della particella (fase 1): C = agricola non idonea per default (ammessi impianti CER fino a 1 MW o
  // agrivoltaico, art. 10 L.R. 5/2026); A = probabile coltura certificata (solo agrivoltaico); la classe I (aree idonee)
  // e la X (vincoli) arriveranno con gli strati regionali (fase 2)
  const it = (x, d = 2) => x.toFixed(d).replace(".", ",");
  function classeTerreno(t) {
    if (t.prob_coltura !== null && t.prob_coltura !== undefined && t.prob_coltura >= 50) return "A";
    return "C";
  }
  // (24/11/2026 sera) art. 10, c. 7 della L.R. 5/2026 come modificato dalla L.R. 27/10/2026 n. 15: senza più il limite di
  // 1 MW (resta quello degli incentivi del GSE per le CER, «Potenza massima per impianto»)
  const NOMI_CLASSI = {
    A: "probabile coltura certificata: solo agrivoltaico (serve l'attestazione di un agronomo)",
    C: "agricola non idonea: impianti a terra intestati a una CER o nella sua disponibilità, oppure agrivoltaico",
  };
  // t: { area_m2, distanza_m, prob_coltura (0-100 o null), n_enti, vincolo }; f: { haMin, haMax, distanzaMaxM, tipo, limite10 }
  // (24/11/2026 sera) limite10: occupazione al massimo del 10% del terreno con colture certificate (DAL 125/2023, parti
  // sulle colture di pregio, rimaste in vigore con l'art. 21 della L.R. 5/2026: interpretazione prudente, a scelta)
  function punteggioTerreno(t, f, pesi = PESI) {
    // (24/11/2026 sera) vincoli paesaggistici della Regione: conta solo la parte libera della particella; esclusa se
    // vincolata per metà o più
    const qv = Math.min(1, Math.max(0, +t.quota_vincolata || 0));
    const haTot = (t.area_m2 || 0) / 10000, ha = haTot * (1 - qv);
    const classe = classeTerreno(t);
    const motivi = [];
    if (qv >= 0.5) motivi.push(`vincoli paesaggistici sul ${Math.round(qv * 100)} % (${t.vincoli || "art. 136 e 142 del D.Lgs. 42/2004"})`);
    const k = classe === "A" && f.limite10 ? 10 : 1, haMin = f.haMin * k, haMax = f.haMax * k;
    if (t.vincolo && t.vincolo.classe === "non_idonea") motivi.push(`in area non idonea (${t.vincolo.nome})`);
    if (ha < haMin) motivi.push(`superficie${qv > 0 ? " libera dai vincoli" : ""} ${it(ha)} ha sotto ${it(haMin)} ha${k > 1 ? " (limite del 10% sulle colture certificate)" : ""}`);
    if (t.distanza_m > f.distanzaMaxM) motivi.push(`oltre ${it(f.distanzaMaxM / 1000, 1)} km dalla cabina`);
    if (classe === "A" && f.tipo !== "agrivoltaico") motivi.push("probabile coltura certificata: ammesso solo l'agrivoltaico");
    const ammesso = !motivi.length;
    // aderenza alla superficie giusta: 1 dentro la fascia, poi scende con l'eccesso (un terreno troppo grande si può usare
    // in parte, quindi resta ammesso)
    const sup = ha <= haMax ? 1 : Math.max(0, 1 - (ha / haMax - 1) / 4);
    const dist = Math.max(0, 1 - t.distanza_m / f.distanzaMaxM);
    const col = t.prob_coltura === null || t.prob_coltura === undefined ? 0.5 : 1 - t.prob_coltura / 100;
    const unico = (t.n_enti || 1) === 1 ? 1 : 0.5;
    const tot = pesi.distanza + pesi.superficie + pesi.coltura + pesi.unico;
    const punti = ammesso ? Math.round(100 * (pesi.distanza * dist + pesi.superficie * sup + pesi.coltura * col + pesi.unico * unico) / tot) : 0;
    return { punti, ammesso, motivi, classe, ha: haTot, haLibera: ha };
  }
  // fabbisogno di una cabina per il bando: numero di terreni e fascia di superficie
  function fabbisognoTerreni(d, o = PREDEFINITI) {
    if (!d || !d.nImpianti) return { n: 0, haMin: 0, haMax: 0 };
    const x = d.impianti[0];
    return { n: d.nImpianti, haMin: x.haMin, haMax: x.haMax, kwImpianto: x.kw, kwhAccumulo: x.kwh_accumulo, distanzaMaxM: (o.distanzaKm || 5) * 1000, tipo: o.tipo };
  }

  const API = { ORE, PREDEFINITI, TIPI, ACCESSORI_HA, ACCUMULO_HA_MWH, PESI, NOMI_CLASSI, slot, slotDaUtc, scartoRoma, meseDiSlot, dataOra,
    numero, leggiCurve, totale, somma, riepilogoCurva, produzionePerKwp, simula, dimensiona, impianti, distanzaM, classeTerreno,
    punteggioTerreno, fabbisognoTerreni, bisestile };
  radice.EUGENIO_CER_FV = API;
  if (typeof module !== "undefined" && module.exports) module.exports = API;
})(typeof self !== "undefined" ? self : globalThis);
