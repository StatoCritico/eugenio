"use strict";
// Visure catastali in Patrimonio (fase 11, EuGEnio Visure), senza DOM: lettura dei file prodotti dal lettore locale
// (indice.csv, edifici_visure.csv, patrimonio_con_visure.csv, visure.json), abbinamento delle unità agli edifici e
// colonne visura_… per edificio. È la stessa logica di fase11-visure/visure/arricchisci.py e piani.py: un test
// (fase11-visure/tests/test_abbina_js.py) fa girare questo file con node e confronta i risultati con quelli di Python.
//
// Tutto resta nel browser: niente di quello che si legge qui va al server di EuGEnio. Le colonne con dati personali
// (intestatari, codici fiscali, nascite, diritti e quote) si scartano appena lette, anche se il file le contiene.
(function (radice) {
  const BELFIORE = /^[A-Z]\d{3}$/;
  const PERTINENZE = new Set(["C/2", "C/6", "C/7"]);
  // colonne con dati personali: si scartano sempre (nome della colonna già normalizzato)
  const PERSONALI = /(^|_)(intestat|codic[ei]_fiscal|cod_fisc|partita_iva|nominativ|cognom|nascit|titolar|diritt|propriet|soggett)|(^|_)(cf|piva|quota|quote|nato|nata)(_|$)/;
  const COLONNE_EDIFICIO = ["visura_unita", "visura_subalterni", "visura_categorie", "visura_uso_prevalente", "visura_uso",
    "visura_piani", "visura_piani_fuori_terra", "visura_piani_interrati", "visura_piano_piu_alto",
    "visura_superficie_catastale", "visura_consistenza_m3", "visura_rendita_euro", "visura_terreni_m2",
    "visura_data", "visura_indirizzo", "visura_esito", "visura_nota"];
  // descrizione breve e uso per le stime dei piani (come arricchisci.CATEGORIE)
  const CATEGORIE = {
    "A/1": ["abitazione signorile", "residenziale"], "A/2": ["abitazione civile", "residenziale"],
    "A/3": ["abitazione economica", "residenziale"], "A/4": ["abitazione popolare", "residenziale"],
    "A/5": ["abitazione ultrapopolare", "residenziale"], "A/6": ["abitazione rurale", "residenziale"],
    "A/7": ["villino", "residenziale"], "A/8": ["villa", "residenziale"], "A/9": ["castello o palazzo storico", "residenziale"],
    "A/10": ["uffici e studi privati", "uffici"], "A/11": ["abitazione tipica dei luoghi", "residenziale"],
    "B/1": ["collegi, convitti, caserme", "altro"], "B/2": ["case di cura e ospedali senza fine di lucro", "ospedale"],
    "B/3": ["prigioni e riformatori", "altro"], "B/4": ["uffici pubblici", "uffici"],
    "B/5": ["scuole e laboratori scientifici", "scuola"], "B/6": ["biblioteche, musei, accademie", "altro"],
    "B/7": ["cappelle e oratori", "altro"], "B/8": ["magazzini sotterranei", "capannone"],
    "C/1": ["negozi e botteghe", "commerciale"], "C/2": ["magazzini e depositi", "capannone"],
    "C/3": ["laboratori per arti e mestieri", "capannone"], "C/4": ["fabbricati per esercizi sportivi", "palestra"],
    "C/5": ["stabilimenti balneari", "altro"], "C/6": ["stalle, scuderie, rimesse, autorimesse", "altro"],
    "C/7": ["tettoie", "altro"],
    "D/1": ["opifici", "capannone"], "D/2": ["alberghi e pensioni", "altro"], "D/3": ["teatri, cinema, sale", "altro"],
    "D/4": ["case di cura e ospedali con fine di lucro", "ospedale"], "D/5": ["istituti di credito", "uffici"],
    "D/6": ["fabbricati per attività sportive", "palestra"], "D/7": ["fabbricati industriali", "capannone"],
    "D/8": ["fabbricati commerciali", "commerciale"], "D/9": ["edifici galleggianti", "altro"],
    "D/10": ["fabbricati per funzioni produttive agricole", "capannone"],
    "E/1": ["stazioni per servizi di trasporto", "altro"], "E/3": ["costruzioni per speciali esigenze pubbliche", "altro"],
    "E/9": ["altri immobili a destinazione particolare", "altro"],
    "F/1": ["area urbana", "altro"], "F/2": ["unità collabente", "altro"], "F/3": ["in corso di costruzione", "altro"],
    "F/4": ["in corso di definizione", "altro"], "F/5": ["lastrico solare", "altro"], "F/6": ["in attesa di dichiarazione", "altro"],
  };

  // ------------------------------------------------------------------ normalizzazioni
  const senzaAccenti = (s) => String(s).normalize("NFD").replace(/[̀-ͯ]/g, "");
  function normaComune(s) {
    let t = senzaAccenti(s === null || s === undefined ? "" : s).toUpperCase();
    t = t.replace(/^\s*COMUNE\s+DI\s+/, "");
    return t.replace(/['’]/g, "").replace(/[^A-Z0-9]+/g, " ").trim();
  }
  function normaNum(s) {
    let t = String(s === null || s === undefined ? "" : s).replace(/\s+/g, "").toUpperCase();
    if (/^\d+\.0$/.test(t)) t = t.slice(0, -2);
    return t.replace(/^0+(?=[0-9A-Z])/, "");
  }
  // numeri del CSV del lettore (virgola decimale) e di JSON
  function numero(v) {
    if (v === null || v === undefined || v === "") return null;
    if (typeof v === "number") return Number.isFinite(v) ? v : null;
    let t = String(v).trim().replace(/[\s ]/g, "").replace(/[^\d.,-]/g, "");
    if (!/\d/.test(t)) return null;
    if (t.includes(",")) t = t.replace(/\./g, "").replace(",", ".");
    else if (/^\d{1,3}(\.\d{3})+$/.test(t)) t = t.replace(/\./g, "");
    const n = Number(t);
    return Number.isFinite(n) ? n : null;
  }
  const val = (r, ...nomi) => {
    for (const n of nomi) {
      const v = r[n];
      if (v !== null && v !== undefined && v !== "" && !["nan", "none", "null"].includes(String(v).trim().toLowerCase())) return String(v).trim();
    }
    return "";
  };
  const normaTitolo = (c) => String(c).trim().toLowerCase().replace(/["']/g, "").replace(/[^a-z0-9àèéìòù_]/g, "_").replace(/_+/g, "_").replace(/^_+|_+$/g, "");

  // ------------------------------------------------------------------ piani (come piani.py)
  const TERRA = new Set(["T", "PT", "P.T.", "PT.", "TERRA", "PIANOTERRA", "R", "PR", "RIALZATO", "PIANORIALZATO", "TR", "P.R."]);
  const INTERRATO = new Set(["S", "SEMINTERRATO", "SEMINT", "SEMINT.", "INTERRATO", "SOTTOSTRADA", "SS", "SI", "SEMI"]);
  const AMMEZZATO = new Set(["AMMEZZATO", "AMM", "AMM.", "AM", "M", "MEZZANINO", "SOPPALCO"]);
  const SOTTOTETTO = new Set(["SOTTOTETTO", "SOFFITTA", "MANSARDA", "SOTT", "SOTT.", "SOTTOT", "SOTTOT."]);
  const VUOTE = new Set(["PIANO", "PIANI", "P", "P.", "E", "ED", "AL", "IL", "DEL", ""]);
  function livelli(testo) {
    if (!testo) return [[], []];
    let s = senzaAccenti(String(testo)).toUpperCase().trim();
    s = s.replace("PIANO TERRA", "T").replace("PIANO RIALZATO", "R").replace("PIANO SEMINTERRATO", "S1");
    const trovati = new Set(), altri = [];
    s = s.replace(/\bDA(?:L)?\s+(-?\d+)\D{0,3}\s+A(?:L)?\s+(-?\d+)/g, (m, a, b) => {
      const lo = Math.min(+a, +b), hi = Math.max(+a, +b);
      if (hi - lo <= 60) for (let x = lo; x <= hi; x++) trovati.add(x);
      return " ";
    });
    s = s.replace(/\bS\s*-\s*(\d)\b/g, "S$1");
    s = s.replace(/(^|[\s,;(])-\s*(\d)\b/g, "$1S$2");
    for (let t of s.split(/[\s,;/+\-–]+/)) {
      t = t.replace(/^[()[\]:]+|[()[\]:]+$/g, "");
      if (VUOTE.has(t)) continue;
      let m = /^(\d{1,2})(?:°|º|ª|O|A)?\.?$/.exec(t);
      if (m) { trovati.add(+m[1]); continue; }
      m = /^S(\d)$/.exec(t) || /^(?:INT|SI)(\d)$/.exec(t);
      if (m) { trovati.add(-m[1]); continue; }
      if (TERRA.has(t)) trovati.add(0);
      else if (INTERRATO.has(t)) trovati.add(-1);
      else if (AMMEZZATO.has(t)) { if (!altri.includes("ammezzato")) altri.push("ammezzato"); }
      else if (SOTTOTETTO.has(t)) { if (!altri.includes("sottotetto")) altri.push("sottotetto"); }
      else if (/^[A-Z]{1,3}\d?$/.test(t) || t.length > 1) altri.push("?" + t.toLowerCase());
    }
    return [[...trovati].sort((a, b) => a - b), altri];
  }
  const etichetta = (n) => (n === 0 ? "T" : n < 0 ? `S${-n}` : String(n));
  function riassumiPiani(insieme, altri = []) {
    altri = altri.filter((a) => !a.startsWith("?"));
    if (!insieme.length) return { piani: altri.join(";"), piani_fuori_terra: null, piani_interrati: null, piano_piu_alto: null };
    const sopra = insieme.filter((x) => x >= 0), sotto = insieme.filter((x) => x < 0);
    return {
      piani: [...insieme.map(etichetta), ...altri].join(";"),
      piani_fuori_terra: sopra.length ? Math.max(...sopra) + 1 : 0,
      piani_interrati: sotto.length ? -Math.min(...sotto) : 0,
      piano_piu_alto: etichetta(Math.max(...insieme)),
    };
  }

  // ------------------------------------------------------------------ abbinamento (come arricchisci.py)
  function chiaviEdificio(r) {
    const out = [];
    let b = val(r, "belfiore"), f = val(r, "foglio_catasto"), p = val(r, "mappale");
    if (b && f && p) out.push({ tipo: "forte", belfiore: b.toUpperCase(), nome: normaComune(val(r, "comune_catasto")),
      sezione: normaNum(val(r, "sezione")), foglio: normaNum(f), particella: normaNum(p) });
    const c = val(r, "comune"); f = val(r, "foglio"); p = val(r, "particella", "mappale");
    if (c && f && p) {
      const cu = c.trim().toUpperCase();
      out.push({ tipo: "dichiarata", belfiore: BELFIORE.test(cu) ? cu : "", nome: BELFIORE.test(cu) ? "" : normaComune(c),
        sezione: normaNum(val(r, "sezione")), foglio: normaNum(f), particella: normaNum(p) });
    }
    return out;
  }
  function coincide(k, u) {
    if (normaNum(u.particella) !== k.particella || normaNum(u.foglio) !== k.foglio) return null;
    const ub = String(u.codice_comune || "").toUpperCase(), un = normaComune(u.comune);
    let perCodice;
    if (k.belfiore && ub) { if (k.belfiore !== ub) return null; perCodice = true; }
    else if (k.nome && un) { if (k.nome !== un) return null; perCodice = false; }
    else return null;
    const us = normaNum(u.sezione);
    if (k.sezione && us && k.sezione !== us) return null;
    return perCodice && k.sezione === us ? "ok" : "verificare";
  }
  function dataIso(d) {
    const m = /(\d{1,2})\/(\d{1,2})\/(\d{4})/.exec(d || "");
    return m ? `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}` : "";
  }
  function somma(xs) {
    const v = xs.map(numero).filter((x) => x !== null);
    if (!v.length) return null;
    const s = v.reduce((a, b) => a + b, 0);
    return Number.isInteger(s) ? s : Math.round(s * 100) / 100;
  }
  function conta(xs) { const m = new Map(); xs.forEach((x) => m.set(x, (m.get(x) || 0) + 1)); return m; }
  const ordina = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  function riassunto(unita) {
    const fab = unita.filter((u) => u.catasto === "F"), ter = unita.filter((u) => u.catasto === "T");
    const cat = conta(fab.map((u) => u.categoria).filter(Boolean));
    const principali = [...cat.keys()].filter((c) => !PERTINENZE.has(c));
    const peso = new Map();
    for (const u of fab) {
      const c = u.categoria;
      if (!c || (principali.length && PERTINENZE.has(c))) continue;
      const cons = numero(u.consistenza);
      const w = numero(u.superficie_catastale) || (u.unita_consistenza === "m³" && cons ? cons / 3 : null) || 1;
      peso.set(c, (peso.get(c) || 0) + w);
    }
    const prev = peso.size ? [...peso.entries()].sort((a, b) => b[1] - a[1] || ordina(a[0], b[0]))[0][0] : null;
    const liv = new Set(), altri = [];
    for (const u of fab) { const [l, a] = livelli(u.piano); l.forEach((x) => liv.add(x)); a.forEach((x) => { if (!altri.includes(x)) altri.push(x); }); }
    const pp = riassumiPiani([...liv].sort((a, b) => a - b), altri);
    const date = unita.filter((u) => u.data_visura).map((u) => [dataIso(u.data_visura), u.data_visura]).sort((a, b) => ordina(a[0], b[0]) || ordina(a[1], b[1]));
    const ind = [...conta(fab.map((u) => u.indirizzo).filter(Boolean)).entries()];
    let migliore = null;
    for (const [k, n] of ind) if (!migliore || n > migliore[1]) migliore = [k, n];     // a parità il primo, come Counter
    const gruppo = (u) => String(u.categoria || "").slice(0, 1);
    const parziali = unita.filter((u) => u.esito === "parziale").length;
    return {
      visura_unita: unita.length,
      visura_subalterni: fab.length,
      visura_categorie: [...cat.entries()].sort((a, b) => b[1] - a[1] || ordina(a[0], b[0])).map(([c, n]) => (n > 1 ? `${c} ×${n}` : c)).join("; "),
      visura_uso_prevalente: prev ? `${prev} ${(CATEGORIE[prev] || [""])[0]}`.trim() : "",
      visura_uso: prev ? (CATEGORIE[prev] || ["", "altro"])[1] : "",
      visura_piani: pp.piani,
      visura_piani_fuori_terra: pp.piani_fuori_terra,
      visura_piani_interrati: pp.piani_interrati,
      visura_piano_piu_alto: pp.piano_piu_alto,
      visura_superficie_catastale: somma(fab.filter((u) => ["A", "B", "C"].includes(gruppo(u))).map((u) => u.superficie_catastale)),
      visura_consistenza_m3: somma(fab.filter((u) => gruppo(u) === "B" && u.unita_consistenza === "m³").map((u) => u.consistenza)),
      visura_rendita_euro: somma(fab.map((u) => u.rendita_euro)),
      visura_terreni_m2: somma(ter.map((u) => u.superficie_m2)),
      visura_data: date.length ? date[date.length - 1][1] : "",
      visura_indirizzo: migliore ? migliore[0] : "",
      visura_nota: parziali ? `${parziali} unità lette in parte` : "",
    };
  }
  // edifici: righe di Patrimonio (anche il risultato della geolocalizzazione); restituisce { edifici, nonAbbinate, indici }
  function abbina(edifici, unita) {
    const usate = new Set(), out = [], gruppi = [];
    for (const r of edifici) {
      let trovate = [], esito = null;
      for (const k of chiaviEdificio(r)) {
        const es = unita.map((u, i) => [i, coincide(k, u)]).filter(([, e]) => e);
        if (es.length) { trovate = es.map(([i]) => i); esito = es.every(([, e]) => e === "ok") ? "ok" : "verificare"; break; }
      }
      const riga = { ...r };
      if (trovate.length) {
        trovate.forEach((i) => usate.add(i));
        Object.assign(riga, riassunto(trovate.map((i) => unita[i])));
        riga.visura_esito = esito;
      } else {
        COLONNE_EDIFICIO.forEach((c) => { riga[c] = ""; });
        riga.visura_esito = "nessuna_visura";
        riga.visura_nota = chiaviEdificio(r).length ? "nessuna visura per questa particella" : "mancano comune, foglio o particella";
      }
      out.push(riga);
      gruppi.push(trovate.join(","));
    }
    const quante = conta(gruppi.filter(Boolean));
    out.forEach((r, n) => { if (gruppi[n] && quante.get(gruppi[n]) > 1) r.visura_nota = (r.visura_nota ? r.visura_nota + "; " : "") + "stessa particella in più righe"; });
    return { edifici: out, nonAbbinate: unita.filter((u, i) => !usate.has(i)), indici: gruppi.map((g) => (g ? g.split(",").map(Number) : [])) };
  }
  function edificiDaUnita(unita) {
    const gruppi = new Map();
    for (const u of unita) {
      const k = [String(u.codice_comune || "").toUpperCase() || normaComune(u.comune), normaNum(u.sezione), normaNum(u.foglio), normaNum(u.particella)].join("|");
      if (!gruppi.has(k)) gruppi.set(k, []);
      gruppi.get(k).push(u);
    }
    const out = [];
    for (const [k, uu] of gruppi) {
      const [cod, sez, fog, par] = k.split("|");
      const r = { id: `V${out.length + 1}`, comune: uu[0].comune || "", codice_comune: BELFIORE.test(cod) ? cod : "", sezione: sez, foglio: fog, particella: par };
      Object.assign(r, riassunto(uu));
      r.visura_esito = "ok";
      r.indirizzo = r.visura_indirizzo;
      out.push(r);
    }
    return out;
  }

  // ------------------------------------------------------------------ lettura dei file del lettore
  // righeCsv: funzione (testo, separatore) → righe di celle (EUGENIO_TABELLE.righe nel sito)
  // Restituisce { tipo: "unita" | "edifici" | "patrimonio", unita, edifici, scartate: [colonne personali tolte] }
  function leggi(testo, nome, righeCsv) {
    testo = String(testo || "").replace(/^﻿/, "");
    const scartate = new Set();
    const pulisci = (o) => {
      const r = {};
      for (const [k, v] of Object.entries(o || {})) { if (PERSONALI.test(normaTitolo(k))) scartate.add(k); else r[k] = v; }
      return r;
    };
    if (/\.json$/i.test(nome || "") || /^\s*[[{]/.test(testo)) {
      let d;
      try { d = JSON.parse(testo); } catch { throw new Error("il file JSON non è leggibile"); }
      // formato del lettore ({unita, edifici}); un elenco semplice di unità (es. un altro programma) è accettato
      // se ha almeno foglio e particella (alias: mappale, sub)
      const lista = Array.isArray(d) ? d : (d && Array.isArray(d.unita) ? d.unita : null);
      if (!lista) throw new Error("nel JSON non c'è l'elenco delle unità");
      const unita = lista.map(pulisci).map(alias).filter((u) => u.foglio && u.particella);
      if (!unita.length) throw new Error("nel JSON non ci sono unità con foglio e particella");
      return { tipo: "unita", unita, edifici: [], scartate: [...scartate] };
    }
    const prime = testo.split(/\r?\n/).filter((r) => r.trim() && !r.trim().startsWith("#"));
    if (prime.length < 2) throw new Error("il file non contiene righe di dati");
    const sep = (prime[0].match(/;/g) || []).length >= (prime[0].match(/,/g) || []).length ? ";" : ",";
    const tutte = righeCsv(prime.join("\n"), sep);
    const titoli = tutte[0].map((t) => t.trim());
    const oggetti = tutte.slice(1).map((c) => { const o = {}; titoli.forEach((t, i) => { o[t] = (c[i] || "").trim(); }); return pulisci(o); });
    const chiavi = new Set(titoli.map(normaTitolo));
    if (chiavi.has("catasto") && (chiavi.has("subalterno") || chiavi.has("categoria") || chiavi.has("qualita"))) {
      const unita = oggetti.map(alias).filter((u) => u.foglio && u.particella);
      return { tipo: "unita", unita, edifici: [], scartate: [...scartate] };
    }
    if (titoli.some((t) => t.startsWith("visura_"))) {
      return { tipo: chiavi.has("codice_comune") && !chiavi.has("denominazione") ? "edifici" : "patrimonio", unita: [], edifici: oggetti, scartate: [...scartate] };
    }
    // un elenco di unità senza la colonna «catasto» (altri programmi): basta che ci siano subalterno o categoria
    if (chiavi.has("foglio") && (chiavi.has("particella") || chiavi.has("mappale")) && (chiavi.has("categoria") || chiavi.has("subalterno") || chiavi.has("sub"))) {
      return { tipo: "unita", unita: oggetti.map(alias).filter((u) => u.foglio && u.particella), edifici: [], scartate: [...scartate] };
    }
    throw new Error("non riconosco il file: servono indice.csv, edifici_visure.csv, patrimonio_con_visure.csv o visure.json di EuGEnio Visure");
  }
  // nomi alternativi dei campi delle unità (altri formati, es. visura-api: da verificare su un esempio vero)
  function alias(u) {
    const o = { ...u };
    const prendi = (std, ...alt) => { if (o[std] === undefined || o[std] === "") for (const a of alt) if (o[a] !== undefined && o[a] !== "") { o[std] = o[a]; break; } };
    prendi("particella", "mappale", "numero");
    prendi("subalterno", "sub");
    prendi("codice_comune", "belfiore", "codice_catastale");
    prendi("rendita_euro", "rendita");
    prendi("superficie_catastale", "superficie");
    if (!o.catasto) o.catasto = o.qualita ? "T" : "F";
    if (o.categoria) { const m = /([A-F])\s?\/\s?0?(\d{1,2})/i.exec(String(o.categoria)); o.categoria = m ? `${m[1].toUpperCase()}/${+m[2]}` : o.categoria; }
    if (!o.unita_consistenza && o.consistenza && /m³|m3|mc/i.test(String(o.consistenza))) o.unita_consistenza = "m³";
    return o;
  }
  // colonne del file di Patrimonio che vengono dalle visure (restano nel browser) e colonne personali (si scartano)
  function separaTitoli(titoli) {
    const visure = [], personali = [];
    titoli.forEach((t, i) => { const n = normaTitolo(t); if (t.trim().startsWith("visura_")) visure.push(i); else if (PERSONALI.test(n)) personali.push(i); });
    return { visure, personali };
  }

  const API = { COLONNE_EDIFICIO, CATEGORIE, normaComune, normaNum, numero, livelli, riassumiPiani, chiaviEdificio, coincide,
    riassunto, abbina, edificiDaUnita, leggi, alias, separaTitoli, PERSONALI, normaTitolo };
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  else radice.EUGENIO_VISURE = API;
})(typeof window !== "undefined" ? window : globalThis);
