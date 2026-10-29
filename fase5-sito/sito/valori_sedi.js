"use strict";
// Patrimonio, sezione «Valori per sede» (29/10/2026, seconda versione): un file di sedi con lo stesso modello della
// geolocalizzazione (id;denominazione;indirizzo;civico;comune;foglio;particella;lat;lon) più colonne di valori. Le
// sedi si trovano con /api/patrimonio (vanno al server solo le colonne del modello), i valori restano nel browser e si
// uniscono riga per riga. Regole in README_stile.md, «Barre a mattoncini» e «Valori per sede».
//
//  - Colonne: in valuta (€, EUR, $, USD, £, GBP, CHF, ¥… nell'unità, nel titolo o accanto ai numeri) = costi; le altre
//    = consumi. Con entrambi: due mappe (sopra i consumi, sotto i costi) e due tabelle. Abbinamento per posizione: la
//    i-esima colonna di consumo va con la i-esima di costo (costo unitario medio = Σ costi / Σ consumi).
//  - Territorio: con i valori la mappa mostra le regioni che contengono sedi e, dentro, i comuni delle sole province
//    con sedi con dati; le sedi senza coordinate ma col comune riconosciuto vanno al centro del comune.
//  - Sedi accese: ogni sede si accende o si spegne dalla tabella; in un comune con più di tre sedi all'inizio sono
//    accese le tre col valore più alto nella prima colonna di consumo (o, se manca, nella prima colonna con un
//    valore); sedi nello stesso punto si mettono in fila con la più piccola davanti. Totali e Pareto usano tutte le sedi.
//  - Colori: famiglie per tipo (elettricità verde, gas e termica gialli/arancio/rossi, acqua azzurri), tonalità lontana
//    dai colori delle regioni visibili; ogni costo prende il colore del consumo abbinato.
//  - Mattoncini: come prima (numero tondo, 20 mattoncini al massimo, cubi, l'ultimo parziale).
(function () {
  const P = window.EUGENIO_PATRIMONIO, T = window.EUGENIO_TABELLE, M3 = window.EUGENIO_MAPPA3D;
  if (!P || !T || !M3) return;
  const $ = (id) => document.getElementById(id);
  const NS = "http://www.w3.org/2000/svg";
  const MAX_MATTONCINI = 20, SEDI_PER_COMUNE = 3;
  const MODELLO = new Set(["id", "codice", "cod", "codice_edificio", "denominazione", "nome", "indirizzo", "via", "civico",
    "numero_civico", "comune", "provincia", "cap", "foglio", "particella", "mappale", "sezione", "subalterno", "lat", "lon",
    "latitudine", "longitudine"]);
  const ID = ["id", "codice", "cod", "codice_edificio"];
  // famiglie di tinte per tipo di consumo (richiesta di Paolo, 29/10/2026): elettricità = verdi, gas ed energia termica
  // = gialli, arancioni e rossi, acqua = azzurri; le altre colonne prendono i colori liberi
  const FAMIGLIE = {
    elettricita: [["#2e9a5a", "Verde"], ["#5cc96b", "Verde chiaro"], ["#1b6e3a", "Verde scuro"], ["#9bd147", "Verde prato"], ["#14a38b", "Verde acqua"]],
    termica: [["#f2c12e", "Giallo"], ["#f39c12", "Arancio"], ["#e8590c", "Arancio scuro"], ["#d62828", "Rosso"], ["#9c1f1f", "Rosso scuro"]],
    acqua: [["#3fa9f5", "Azzurro"], ["#1f77d0", "Blu"], ["#5fd3e8", "Ciano"], ["#7fb8ff", "Celeste"], ["#24539c", "Blu scuro"]],
    // rifiuti, combustibili ed emissioni di CO2
    marrone: [["#8d5524", "Marrone"], ["#c68642", "Nocciola"], ["#5d4037", "Cioccolato"], ["#a0522d", "Terra di Siena"], ["#3e2723", "Marrone scuro"]],
  };
  const LIBERI = [
    ["var(--serie-1)", "Colore 1 del vestito"], ["var(--serie-2)", "Colore 2 del vestito"], ["var(--serie-3)", "Colore 3 del vestito"],
    ["var(--serie-4)", "Colore 4 del vestito"], ["var(--serie-5)", "Colore 5 del vestito"], ["var(--serie-6)", "Colore 6 del vestito"],
    ["#8a4fc8", "Viola"], ["#c2185b", "Magenta"], ["#8c8c8c", "Grigio"],
  ];
  // menu a discesa del colore: le tonalità delle tre famiglie, poi gli altri colori
  const COLORI = [...FAMIGLIE.elettricita, ...FAMIGLIE.termica, ...FAMIGLIE.acqua, ...FAMIGLIE.marrone, ...LIBERI];
  const ESITI = { ok: "trovato", verificare: "da verificare", non_trovato: "non trovato", errore: "errore" };
  const NOMI = { consumo: "consumi", costo: "costi" };
  // avviso del file d'esempio (testo concordato con Paolo, da non cambiare)
  const AVVISO_TITOLO = "Dati di esempio non reali";
  const AVVISO_TESTO = "Il file di esempio usa i nomi e gli indirizzi dei 13 ospedali dell'AUSL della Romagna solo per mostrare come "
    + "funziona la pagina: consumi e costi sono numeri inventati, generati a caso entro intervalli plausibili, e non rappresentano "
    + "in alcun modo i consumi o le spese reali di queste strutture. Non citarli e non usarli per confronti.";
  const stato = { file: null, colonne: [], sedi: [], scale: [], fonti: new Set(), mappe: { consumo: null, costo: null },
    tipiMappe: [], esempio: false, regioni: [], caricato: false };

  const norm = (c) => String(c).trim().toLowerCase().replace(/["']/g, "").replace(/[^a-z0-9àèéìòù_]/g, "_").replace(/^_+|_+$/g, "");
  const nomeComune = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
    .replace(/[^a-z0-9]+/g, " ").trim();
  const fmt = (v, dec) => Number(v).toLocaleString("it-IT", { maximumFractionDigits: dec !== undefined ? dec : Math.abs(v) < 10 ? 2 : Math.abs(v) < 1000 ? 1 : 0 });
  function h(tag, cls, testo) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (testo !== undefined && testo !== null) e.textContent = testo;
    return e;
  }
  function el(tag, attrs = {}, parent) {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) {
      if ((k === "fill" || k === "stroke") && typeof v === "string" && v.startsWith("var(")) e.style.setProperty(k, v);
      else e.setAttribute(k, v);
    }
    if (parent) parent.appendChild(e);
    return e;
  }
  function messaggio(t, errore = false) { const m = $("messaggio-valori"); m.textContent = t; m.classList.toggle("errore", errore); }
  function risolvi(colore) { return M3.testoRgb(M3.rgb(colore)); }
  const colonneDi = (tipo) => stato.colonne.filter((c) => c.tipo === tipo);

  // ------------------------------------------------------------------ unità di misura e valute
  const SCALE_SI = {
    energia: [["Wh", 1], ["kWh", 1e3], ["MWh", 1e6], ["GWh", 1e9], ["TWh", 1e12]],
    potenza: [["W", 1], ["kW", 1e3], ["MW", 1e6], ["GW", 1e9]],
    joule: [["J", 1], ["kJ", 1e3], ["MJ", 1e6], ["GJ", 1e9], ["TJ", 1e12]],
    massa: [["g", 1], ["kg", 1e3], ["t", 1e6]],
  };
  const RICONOSCI = [
    [/^wh$/, "energia", 1], [/^kwh$/, "energia", 1e3], [/^mwh$/, "energia", 1e6], [/^gwh$/, "energia", 1e9], [/^twh$/, "energia", 1e12],
    [/^w$/, "potenza", 1], [/^kw$/, "potenza", 1e3], [/^mw$/, "potenza", 1e6], [/^gw$/, "potenza", 1e9],
    [/^j$/, "joule", 1], [/^kj$/, "joule", 1e3], [/^mj$/, "joule", 1e6], [/^gj$/, "joule", 1e9], [/^tj$/, "joule", 1e12],
    [/^(g|grammi)$/, "massa", 1], [/^(kg|chili|chilogrammi)$/, "massa", 1e3], [/^(t|ton|tonnellate)$/, "massa", 1e6],
    [/^(l|lt|litri|litro)$/, "volume", 1, "litri"], [/^(m3|mc|metri_cubi)$/, "volume", 1000, "m³"],
    [/^(smc|sm3|standard_metri_cubi)$/, "smc", 1, "Smc"],
  ];
  // valute: simbolo o codice nell'unità («€», «EUR», «€/anno», «k€», «migliaia di euro», «$», «USD», «£»…)
  const VALUTE = [
    ["EUR", "€", /€|\beur\b|\beuro\b|\beuri\b/], ["USD", "$", /\$|\busd\b|\bdollar/], ["GBP", "£", /£|\bgbp\b|\bsterlin/],
    ["CHF", "CHF", /\bchf\b|\bfranchi\b/], ["JPY", "¥", /¥|\bjpy\b|\byen\b/], ["CNY", "CN¥", /\bcny\b|\byuan\b|\brmb\b/],
    ["INR", "₹", /₹|\binr\b/], ["SEK", "kr", /\bsek\b/], ["NOK", "kr", /\bnok\b/], ["DKK", "kr", /\bdkk\b/], ["PLN", "zł", /zł|\bpln\b/],
  ];
  const SIMBOLI_VALUTA = /[€$£¥₹]|\b(EUR|USD|GBP|CHF|JPY|CNY|INR|PLN|SEK|NOK|DKK)\b|zł/gi;
  function valuta(testo) {
    const t = String(testo || "").trim().toLowerCase();
    if (!t) return null;
    const v = VALUTE.find(([, , re]) => re.test(t));
    if (!v) return null;
    const fattore = /^(k\s*[€$£]|k\s*(eur|usd|gbp)|migliaia)/.test(t) ? 1e3 : /^(m\s*[€$£]|meur|milioni)/.test(t) ? 1e6 : 1;
    return { scritta: String(testo).trim(), famiglia: `valuta:${v[0]}`, fattore, simbolo: v[1], valuta: v[0] };
  }
  function unita(testo) {
    const scritta = String(testo || "").trim();
    if (!scritta) return null;
    const v = valuta(scritta);
    if (v) return v;
    const k = scritta.toLowerCase().replace(/³/g, "3").replace(/\s+/g, "_").replace(/\.$/, "");
    for (const [re, famiglia, fattore, simbolo] of RICONOSCI) if (re.test(k)) return { scritta, famiglia, fattore, simbolo: simbolo || scritta };
    return { scritta, famiglia: `altro:${k}`, fattore: 1, simbolo: scritta };
  }
  function conUnita(valoreBase, famiglia, simboloGruppo) {
    const passi = SCALE_SI[famiglia];
    if (passi) {
      let scelto = passi[0];
      for (const p of passi) if (Math.abs(valoreBase) >= p[1] * (1 - 1e-9)) scelto = p;
      return `${fmt(valoreBase / scelto[1], 3)} ${scelto[0]}`;
    }
    if (famiglia === "volume" && simboloGruppo === "m³") return `${fmt(valoreBase / 1000, 3)} m³`;
    return `${fmt(valoreBase, 3)}${simboloGruppo ? " " + simboloGruppo : ""}`;
  }
  function mattoncino(massimo) {
    if (!(massimo > 0)) return 1;
    const minimo = massimo / MAX_MATTONCINI, e = Math.floor(Math.log10(minimo));
    for (const k of [e - 1, e, e + 1]) for (const m of [1, 2, 2.5, 5]) {
      const v = Number((m * Math.pow(10, k)).toPrecision(12));
      if (v >= minimo * (1 - 1e-12)) return v;
    }
    return Math.pow(10, e + 1);
  }
  // l'unità scritta in una cella di valori (per i totali e le tabelle)
  const testoUnita = (c) => (c.unita ? c.unita.scritta : "");

  // famiglia di una colonna di consumo: prima dal nome, poi dall'unità.
  //  - nome: rifiuti, combustibili, gasolio, olio, pellet, legna, emissioni, CO2 → marrone; elettric, luce, EE →
  //    elettricità; gas, metano, Smc, termic, calore, riscaldamento, teleriscaldamento, vapore, «servizio energia», S.E.
  //    (sigla, come parola a sé) → termica; acqua, idric → acqua;
  //  - unità: kWh → elettricità, MWh e Smc → termica, m³ e litri → acqua, kg, t, tCO2, kgCO2 → marrone.
  function famigliaDi(c) {
    const grezzo = String(c.nome || "").toLowerCase(), n = nomeComune(c.nome);
    if (/rifiut|combustibil|gasolio|\bolio\b|pellet|\blegna\b|emission|\bco2\b|anidride carbonica/.test(n) || /co₂/.test(grezzo)) return "marrone";
    if (/elettric|\bluce\b|\bee\b|energia attiva/.test(n)) return "elettricita";
    if (/\bgas\b|metano|\bsmc\b|termic|calore|riscaldament|vapore|\bgpl\b|servizio energia|(^| )s e( |$)|(^| )se( |$)/.test(n)) return "termica";
    if (/acqua|idric/.test(n)) return "acqua";
    const u = c.unita;
    if (!u) return null;
    if (/co2|co₂/i.test(u.scritta) || u.famiglia === "massa") return "marrone";
    if (u.famiglia === "energia") return u.fattore <= 1e3 ? "elettricita" : "termica";
    if (u.famiglia === "smc") return "termica";
    if (u.famiglia === "volume") return "acqua";
    return null;
  }
  const deltaE = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
  // colori delle barre, scelti quando si conosce il territorio: per ogni colonna di consumo la tonalità della sua
  // famiglia (o un colore libero) più lontana (ΔE CIE76) dai colori delle regioni visibili sulla mappa 3D, e diversa da
  // quelle già date alle colonne precedenti; ogni colonna di costo eredita il colore del consumo abbinato
  function assegnaColori() {
    const m = mappaDi(stato.tipiMappe[0]) || P.mappa();
    const regioni = (m && m.coloriVisibili ? m.coloriVisibili() : [M3.fondoNeutro()]).map((c) => lab(M3.rgb(c)));
    const lontananza = (c) => Math.min(...regioni.map((r) => deltaE(lab(M3.rgb(c)), r)));
    const usati = [];
    const scegli = (candidati) => {
      const ordinati = candidati.map(([c]) => c).filter((c) => !usati.includes(c))
        .map((c) => ({ c, d: lontananza(c), u: usati.length ? Math.min(...usati.map((x) => deltaE(lab(M3.rgb(c)), lab(M3.rgb(x))))) : 99 }))
        .sort((a, b) => (b.u >= 20) - (a.u >= 20) || b.d - a.d);
      const c = ordinati.length ? ordinati[0].c : candidati[0][0];
      usati.push(c);
      return c;
    };
    const liberi = LIBERI.filter(([c]) => Math.hypot(...lab(M3.rgb(c)).slice(1)) >= 25);   // niente grigi tra i liberi
    const cons = colonneDi("consumo"), cost = colonneDi("costo");
    cons.forEach((c) => { const f = famigliaDi(c); c.famiglia = f; c.colore = scegli(f ? FAMIGLIE[f] : liberi); });
    cost.forEach((c, i) => { c.colore = cons[i] ? cons[i].colore : scegli(liberi); });
  }
  // sRGB → CIELAB (D65)
  function lab([r, g, b]) {
    const lin = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    const R = lin(r), Gg = lin(g), B = lin(b);
    const X = (0.4124 * R + 0.3576 * Gg + 0.1805 * B) / 0.95047, Y = 0.2126 * R + 0.7152 * Gg + 0.0722 * B, Z = (0.0193 * R + 0.1192 * Gg + 0.9505 * B) / 1.08883;
    const f = (t) => (t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116);
    return [116 * f(Y) - 16, 500 * (f(X) - f(Y)), 200 * (f(Y) - f(Z))];
  }

  // ------------------------------------------------------------------ lettura del file
  function analizza(testo, decimalePunto) {
    // righe di nota in cima al file (cominciano con #): si saltano; quella del file d'esempio lo fa riconoscere
    const linee = testo.split(/\r?\n/);
    let note = "";
    while (linee.length && (linee[0].trim().startsWith("#") || !linee[0].trim())) note += linee.shift() + "\n";
    testo = linee.join("\n");
    const prima = testo.split(/\r?\n/, 1)[0] || "";
    const sep = T.separatore(prima);
    const righe = T.righe(testo, sep);
    if (righe.length < 2) throw new Error("il file non contiene righe di dati");
    const titoli = righe[0].map((t) => t.trim());
    const chiavi = titoli.map(norm);
    // i simboli di valuta accanto ai numeri («€ 1.234,56», «1.234,56 EUR») non impediscono di leggerli
    const num = (s) => T.numero(String(s || "").replace(SIMBOLI_VALUTA, ""), { decimalePunto });
    const conSimbolo = (s) => { SIMBOLI_VALUTA.lastIndex = 0; return SIMBOLI_VALUTA.test(String(s || "")); };
    const dati = righe.length > 2 ? righe.slice(2) : righe.slice(1);
    const candidate = titoli.map((t, i) => i).filter((i) => {
      if (!titoli[i] || MODELLO.has(chiavi[i])) return false;
      const celle = dati.map((r) => (r[i] || "").trim()).filter(Boolean);
      return celle.length && celle.filter((c) => num(c) !== null).length >= celle.length * 0.6;
    });
    if (!candidate.length) throw new Error("nel file non ci sono colonne di valori numerici oltre a quelle delle sedi");
    const seconda = righe[1];
    const celle2 = candidate.map((i) => (seconda[i] || "").trim()).filter(Boolean);
    const rigaUnita = celle2.length > 0 && celle2.every((c) => num(c) === null);
    const corpo = righe.slice(rigaUnita ? 2 : 1);
    const colonne = candidate.map((i) => {
      let nome = titoli[i], u = rigaUnita ? unita(seconda[i]) : null;
      const tra = /^(.*?)\s*[([]\s*([^()[\]]{1,24})\s*[)\]]\s*$/.exec(nome);      // «Gas 2025 (Smc)», «Costo (€)»
      if (tra) { nome = tra[1] || nome; if (!u) u = unita(tra[2]); }
      if (!u) {     // simboli di valuta nelle celle (almeno metà di quelle piene)
        const piene = corpo.map((r) => (r[i] || "").trim()).filter(Boolean);
        const sim = piene.filter(conSimbolo);
        if (piene.length && sim.length >= piene.length / 2) { SIMBOLI_VALUTA.lastIndex = 0; u = valuta(sim[0].match(SIMBOLI_VALUTA)[0]); }
      }
      return { indice: i, nome, unita: u, tipo: u && u.valuta ? "costo" : "consumo", visibile: true, chiave: `c${i}` };
    });
    // colori provvisori: quelli veri li sceglie assegnaColori() quando si conoscono le regioni visibili
    colonne.forEach((c, k) => { c.colore = LIBERI[k % 5][0]; });
    const sedi = corpo.map((r, n) => ({ riga: n, celle: r, valori: colonne.map((c) => num(r[c.indice])) }));
    return { sep, titoli, chiavi, colonne, sedi, rigaUnita, esempio: note.includes(AVVISO_TITOLO) };
  }

  function csvPerServer(a) {
    const usate = a.titoli.map((t, i) => i).filter((i) => MODELLO.has(a.chiavi[i]));
    const conId = usate.some((i) => ID.includes(a.chiavi[i]));
    const cella = (v) => { const s = String(v === undefined || v === null ? "" : v); return /[;"\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
    const testa = [...(conId ? [] : ["id"]), ...usate.map((i) => a.titoli[i])];
    const righe = [testa.join(";")];
    a.sedi.forEach((s, n) => righe.push([...(conId ? [] : [`S${n + 1}`]), ...usate.map((i) => s.celle[i])].map(cella).join(";")));
    const iId = conId ? usate.find((i) => ID.includes(a.chiavi[i])) : -1;
    a.sedi.forEach((s, n) => { s.id = conId ? String(s.celle[iId] || "").trim() || `S${n + 1}` : `S${n + 1}`; });
    return righe.join("\n");
  }

  // ------------------------------------------------------------------ territorio: regioni, province, centro dei comuni
  const caricate = new Map();
  function regioneDati(cod) {
    if (!caricate.has(cod)) caricate.set(cod, fetch(`dati/mappa/${cod}.json`).then((r) => (r.ok ? r.json() : null)).then((m) => {
      if (!m) return null;
      m.comuni.forEach((c) => { c.poli = M3.poligoni(c.d); c.box = riquadro(c.poli); c.chiave = nomeComune(c.nome); });
      return m;
    }).catch(() => null));
    return caricate.get(cod);
  }
  function riquadro(poli) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const p of poli) for (let i = 0; i < p.length; i += 2) {
      if (p[i] < x0) x0 = p[i]; if (p[i] > x1) x1 = p[i]; if (p[i + 1] < y0) y0 = p[i + 1]; if (p[i + 1] > y1) y1 = p[i + 1];
    }
    return [x0, y0, x1, y1];
  }
  function dentro(pt, poli, box) {
    const [x, y] = pt;
    if (box && (x < box[0] || x > box[2] || y < box[1] || y > box[3])) return false;
    let si = false;
    for (const p of poli) for (let i = 0, j = p.length - 2; i < p.length; j = i, i += 2) {
      const yi = p[i + 1], yj = p[j + 1];
      if ((yi > y) !== (yj > y) && x < (p[j] - p[i]) * (y - yi) / (yj - yi) + p[i]) si = !si;
    }
    return si;
  }
  async function territorio() {
    const E = window.EUGENIO;
    const it = await E.italia();
    const regioni = it.regioni.map((r) => { const poli = M3.poligoni(r.d); return { ...r, poli, box: riquadro(poli) }; });
    const sedi = stato.sedi;
    // 1. la regione di ogni sede con le coordinate (se il punto cade appena fuori dal contorno, la regione più vicina)
    for (const s of sedi) {
      if (!s.punto) continue;
      let r = regioni.find((x) => dentro(s.punto, x.poli, x.box));
      if (!r) r = regioni.map((x) => ({ x, d: Math.hypot(s.punto[0] - (x.box[0] + x.box[2]) / 2, s.punto[1] - (x.box[1] + x.box[3]) / 2) }))
        .sort((a, b) => a.d - b.d)[0].x;
      s.regione = r.cod;
    }
    // 2. sedi senza coordinate col comune: centro del comune (prima nelle regioni delle altre sedi, poi nelle altre)
    const daCercare = sedi.filter((s) => !s.punto && s.comuneFile);
    if (daCercare.length) {
      const ordine = [...new Set([...sedi.map((s) => s.regione).filter(Boolean), E.regione, ...regioni.map((r) => r.cod)])];
      for (const cod of ordine) {
        const m = await regioneDati(cod);
        if (!m) continue;
        for (const s of daCercare) {
          if (s.punto) continue;
          const c = m.comuni.find((x) => x.chiave === nomeComune(s.comuneFile));
          if (c) Object.assign(s, { punto: [c.x, c.y], centroide: true, regione: cod, istat: c.istat, prov: c.prov, comune: s.comune || c.nome });
        }
        if (daCercare.every((s) => s.punto)) break;
      }
    }
    // 3. comune e provincia delle sedi con le coordinate
    for (const s of sedi) {
      if (!s.punto || s.centroide || !s.regione) continue;
      const m = await regioneDati(s.regione);
      const c = m && m.comuni.find((x) => dentro(s.punto, x.poli, x.box));
      if (c) Object.assign(s, { istat: c.istat, prov: c.prov, comune: s.comune || c.nome });
    }
    // 4. regioni con sedi (con dati, se ce ne sono) e comuni delle sole province con sedi con dati
    const conDati = sedi.filter((s) => s.punto && s.valori.some((v) => v !== null));
    const base = conDati.length ? conDati : sedi.filter((s) => s.punto);
    const codici = [...new Set(base.map((s) => s.regione).filter(Boolean))];
    if (!codici.length) codici.push(E.regione);
    const province = new Set(conDati.map((s) => `${s.regione}:${s.prov}`));
    const comuni = [];
    for (const cod of codici) {
      const m = await regioneDati(cod);
      if (m) m.comuni.forEach((c) => { if (province.has(`${cod}:${c.prov}`)) comuni.push({ nome: c.nome, prov: c.prov, d: c.d, cod }); });
    }
    stato.regioni = codici.map((cod) => regioni.find((r) => r.cod === cod)).filter(Boolean);
    return { sagome: stato.regioni.map((r) => ({ cod: r.cod, d: r.d, nome: r.nome })), comuni };
  }

  // ------------------------------------------------------------------ scale e mattoncini
  function calcolaScale() {
    const gruppi = new Map();
    stato.colonne.forEach((c, k) => {
      const fam = c.unita ? c.unita.famiglia : `senza:${k}`;
      if (!gruppi.has(fam)) gruppi.set(fam, { famiglia: fam, colonne: [], simbolo: c.unita ? c.unita.simbolo : "" });
      gruppi.get(fam).colonne.push(c);
    });
    stato.scale = [...gruppi.values()].map((g) => {
      let massimo = 0;
      for (const c of g.colonne) {
        const f = c.unita ? c.unita.fattore : 1, k = stato.colonne.indexOf(c);
        stato.sedi.forEach((s) => { const v = s.valori[k]; if (v > 0 && v * f > massimo) massimo = v * f; });
      }
      const m = mattoncino(massimo);
      Object.assign(g, { massimo, mattoncino: m, mattonciniMax: massimo / m, testoMattoncino: conUnita(m, g.famiglia, g.simbolo) });
      g.colonne.forEach((c) => { c.scala = g; });
      return g;
    });
  }

  // ------------------------------------------------------------------ sedi accese
  // peso di una sede: il valore della prima colonna di consumo; se manca, della prima colonna con un valore
  function peso(s) {
    const k0 = stato.colonne.findIndex((c) => c.tipo === "consumo");
    if (k0 >= 0 && s.valori[k0] !== null) return s.valori[k0];
    const v = s.valori.find((x) => x !== null);
    return v === undefined ? 0 : v;
  }
  const chiaveComune = (s) => (s.istat ? `i${s.istat}` : s.comune ? `n${nomeComune(s.comune)}` : `s${s.riga}`);
  function sceltaAutomatica() {
    const perComune = new Map();
    stato.sedi.forEach((s) => {
      if (!s.valori.some((v) => v !== null)) { s.attiva = true; return; }
      const k = chiaveComune(s);
      if (!perComune.has(k)) perComune.set(k, []);
      perComune.get(k).push(s);
    });
    perComune.forEach((lista) => lista.sort((a, b) => peso(b) - peso(a)).forEach((s, i) => { s.attiva = i < SEDI_PER_COMUNE; }));
  }

  // ------------------------------------------------------------------ mappe
  function mappaDi(tipo) { return stato.mappe[tipo]; }
  function creaMappaCosti() {
    if (stato.mappe.costo) return stato.mappe.costo;
    const m = M3.crea($("mappa-costi"), {
      suCambio: (vista, barre) => document.dispatchEvent(new CustomEvent("eugenio:vista3d", { detail: { vista, barre } })),
    });
    stato.mappe.costo = m;
    return m;
  }
  // pulsante «Copia la vista sull'altra mappa» nei comandi di ciascuna mappa (visibile solo con due mappe)
  function pulsanteCopia(da, a) {
    let g = da.comandi.querySelector('[data-gruppo="Altra mappa"]');
    if (!g) {
      g = h("span", "mappa3d-gruppo");
      g.dataset.gruppo = "Altra mappa";
      g.setAttribute("role", "group");
      g.setAttribute("aria-label", "Altra mappa");
      const b = h("button", "mappa3d-copia", "Copia la vista sull'altra mappa");
      b.type = "button";
      b.title = "Porta rotazione, inclinazione, zoom e vista delle barre di questa mappa sull'altra";
      b.addEventListener("click", () => { const altra = a(); if (altra) altra.applica(da.statoCompleto()); });
      g.appendChild(b);
      da.comandi.appendChild(g);
    }
    return g;
  }

  function barre(tipo) {
    const mappa = mappaDi(tipo);
    if (!mappa) return;
    const cols = colonneDi(tipo);
    const gruppi = [];
    const accese = stato.sedi.filter((s) => s.punto && s.attiva);
    // sedi nello stesso punto (centro del comune, o coordinate entro circa 100 metri): in fila, la più grande in fondo
    const pile = new Map();
    accese.forEach((s) => {
      const k = s.centroide ? `c${s.istat}` : `${Math.round(s.punto[0] * 10)},${Math.round(s.punto[1] * 10)}`;
      if (!pile.has(k)) pile.set(k, []);
      pile.get(k).push(s);
    });
    pile.forEach((lista) => lista.sort((a, b) => peso(b) - peso(a)).forEach((s, i) => { s.pila = { rango: i, n: lista.length }; }));
    // stessa base per tutte le barre della mappa (decisione di Paolo, 29/10/2026): il lato del mattoncino è quello della
    // scala con più mattoncini; le altre scale arrivano più in basso (altezze diverse), i mattoncini restano cubici
    const latoComune = 1 / Math.max(1, ...cols.map((c) => c.scala ? c.scala.mattonciniMax : 1));
    accese.forEach((s) => {
      const voci = [];
      cols.forEach((c) => {
        const k = stato.colonne.indexOf(c), v = s.valori[k];
        if (v === null || v === undefined) return;
        const f = c.unita ? c.unita.fattore : 1, g = c.scala;
        voci.push({ chiave: c.chiave, colore: c.colore, visibile: c.visibile, colonna: c.nome,
          mattoni: Math.max(0, v * f / g.mattoncino), latoRel: latoComune,
          testo: `${fmt(v)}${c.unita ? " " + c.unita.scritta : ""}` });
      });
      if (voci.length) gruppi.push({ x: s.punto[0], y: s.punto[1], titolo: s.titolo, voci, pila: s.pila,
        sotto: [s.comune, s.centroide ? "posizione: centro del comune" : "", s.esito && s.esito !== "ok" ? ESITI[s.esito] || s.esito : ""].filter(Boolean).join(" · ") });
    });
    mappa.barre(gruppi);
  }
  const ridisegnaBarre = () => stato.tipiMappe.forEach(barre);

  async function preparaMappe() {
    const tipi = ["consumo", "costo"].filter((t) => colonneDi(t).length);
    stato.tipiMappe = tipi;
    stato.mappe.consumo = null;
    const principale = P.mappa();
    // la mappa principale mostra i consumi (o i costi, se nel file ci sono solo costi); la seconda i costi
    const due = tipi.length === 2;
    stato.mappe[tipi[0]] = principale;
    $("blocco-costi").hidden = !due;
    document.querySelector(".mappa-area").classList.toggle("due-mappe", due);
    const titolo = $("titolo-consumi");
    titolo.hidden = false;
    titolo.textContent = tipi[0] === "costo" ? "Costi" : "Consumi";
    if (due) creaMappaCosti(); else if (stato.mappe.costo) stato.mappe.costo = null;
    const scena = await territorio();
    P.territorioAutomatico = true;
    const nomi = stato.regioni.map((r) => r.nome).join(", ");
    for (const t of tipi) {
      const m = stato.mappe[t];
      m.scena(scena);
      m.svg.closest(".mappa").setAttribute("aria-label", `Mappa dei ${NOMI[t]}: ${nomi}`);
    }
    assegnaColori();            // ora si sanno le regioni visibili e i loro colori
    ridisegnaBarre();
    // con le due mappe visibili e misurate: vista 3D sul territorio delle sedi
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    for (const t of tipi) stato.mappe[t].vista("3d");
    const m0 = stato.mappe[tipi[0]], m1 = due ? stato.mappe.costo : null;
    pulsanteCopia(m0, () => m1).hidden = !due;
    if (m1) pulsanteCopia(m1, () => m0).hidden = false;
    scriviCursori(m0.statoBarre());
    legende();
  }

  // ------------------------------------------------------------------ legende sotto le mappe: mostra e colore
  function legende() {
    for (const t of ["consumo", "costo"]) {
      const box = $(t === "consumo" ? "legenda-consumi" : "legenda-costi");
      const tipoBox = t === "consumo" ? stato.tipiMappe[0] : "costo";
      if (t === "consumo" && !stato.tipiMappe.length) { box.hidden = true; continue; }
      box.innerHTML = "";
      box.hidden = false;
      const cols = colonneDi(tipoBox);
      cols.forEach((c) => {
        const d = h("div", "legenda-colonna");
        d.classList.toggle("spenta", !c.visibile);
        const lab = h("label", "colonna-mostra");
        const spunta = h("input");
        spunta.type = "checkbox"; spunta.checked = c.visibile; spunta.dataset.colonna = c.chiave;
        spunta.addEventListener("change", () => mostraColonna(c, spunta.checked));
        const campione = h("i", "campione");
        campione.style.background = c.colore;
        lab.append(spunta, campione, h("span", null, c.nome));
        const sel = h("select");
        sel.setAttribute("aria-label", `Colore delle barre di ${c.nome}`);
        for (const [valore, nome] of COLORI) { const o = h("option", null, nome); o.value = valore; sel.appendChild(o); }
        sel.value = c.colore;
        sel.addEventListener("change", () => { c.colore = sel.value; campione.style.background = c.colore; aggiornaColori(); });
        const info = h("small", "colonna-info", `1 mattoncino = ${c.scala.testoMattoncino}`);
        d.append(lab, sel, info);
        box.appendChild(d);
      });
    }
  }
  function aggiornaColori() {
    stato.tipiMappe.forEach((t) => {
      const per = {};
      colonneDi(t).forEach((c) => { per[c.chiave] = { colore: c.colore, visibile: c.visibile }; });
      mappaDi(t).aggiornaBarre(per);
    });
    document.querySelectorAll(".tabella-valori .campione[data-colonna]").forEach((i) => {
      const c = stato.colonne.find((x) => x.chiave === i.dataset.colonna);
      if (c) i.style.background = c.colore;
    });
    pareto();
  }
  function mostraColonna(c, si) {
    c.visibile = si;
    document.querySelectorAll(`input[data-colonna="${c.chiave}"]`).forEach((i) => { i.checked = si; });
    document.querySelectorAll(".legenda-colonna").forEach((d) => { const i = d.querySelector("input"); d.classList.toggle("spenta", !i.checked); });
    aggiornaColori();
  }
  function accendiSede(s, si) {
    s.attiva = si;
    document.querySelectorAll(`input[data-sede="${s.riga}"]`).forEach((i) => { i.checked = si; i.closest("tr").classList.toggle("spenta", !si); });
    ridisegnaBarre();
  }

  // ------------------------------------------------------------------ totali e costi unitari medi
  function totaliDi(c) {
    const k = stato.colonne.indexOf(c);
    let somma = 0, n = 0;
    stato.sedi.forEach((s) => { const v = s.valori[k]; if (v !== null && v !== undefined) { somma += v; n++; } });
    return { somma, n };
  }
  function coppie() {
    const cons = colonneDi("consumo"), cost = colonneDi("costo");
    return cons.slice(0, cost.length).map((c, i) => ({ consumo: c, costo: cost[i] }));
  }
  // somme di consumo (nell'unità base della sua famiglia) e di costo (in valuta) sulle sedi con entrambi i valori
  function somme(p, sedi) {
    const kc = stato.colonne.indexOf(p.consumo), kk = stato.colonne.indexOf(p.costo);
    const fk = p.costo.unita ? p.costo.unita.fattore : 1, fc = p.consumo.unita ? p.consumo.unita.fattore : 1;
    let sc = 0, sk = 0, n = 0;
    sedi.forEach((s) => { const a = s.valori[kc], b = s.valori[kk]; if (a > 0 && b !== null) { sc += a * fc; sk += b * fk; n++; } });
    return { sc, sk, n };
  }
  // unità del costo unitario: per l'energia sempre €/MWh con 2 decimali, anche se i consumi sono in kWh (decisione di
  // Paolo, 29/10/2026); per le altre grandezze l'unità del consumo com'è nel file (€/Smc, €/m³)
  function scalaPrezzo(p) {
    const val = p.costo.unita ? p.costo.unita.simbolo : "€";
    const u = p.consumo.unita;
    if (u && u.famiglia === "energia") return { unita: `${val}/MWh`, m: 1e6, decimali: 2 };
    return { unita: `${val}/${u ? u.scritta : "unità"}`, m: u ? u.fattore : 1, decimali: null };
  }
  // decimali di un costo unitario: quelli fissati dalla scala (2 per l'energia), altrimenti 3 sotto 10 e 2 sopra
  const decimaliPrezzo = (p, x) => { const d = scalaPrezzo(p).decimali; return d !== null ? d : (x < 10 ? 3 : 2); };
  const unitaPrezzo = (p) => scalaPrezzo(p).unita;
  function prezzo(p, sedi = stato.sedi) {
    const { sc, sk, n } = somme(p, sedi);
    return { valore: sc > 0 ? sk / sc * scalaPrezzo(p).m : null, n };
  }
  function totali() {
    const box = $("totali");
    box.innerHTML = "";
    for (const t of ["consumo", "costo"]) {
      const cols = colonneDi(t);
      if (!cols.length) continue;
      const tab = h("table", "totali");
      tab.appendChild(h("caption", null, t === "consumo" ? "Consumi" : "Costi"));
      const corpo = tab.createTBody();
      cols.forEach((c) => {
        const { somma, n } = totaliDi(c);
        const r = corpo.insertRow();
        r.appendChild(h("th", null, c.nome));
        const td = h("td", "num");
        td.append(h("b", null, fmt(somma, Math.abs(somma) < 100 ? 2 : 0)), " ", h("span", "unita", testoUnita(c)));
        r.appendChild(td);
        r.appendChild(h("td", "num sedi", `${n} ${n === 1 ? "sede" : "sedi"}`));
      });
      box.appendChild(tab);
    }
    box.appendChild(h("p", "aiuto", `Somme su tutte le ${stato.sedi.length} sedi del file, anche quelle spente sulla mappa.`));
    const pz = $("prezzi");
    pz.innerHTML = "";
    const cp = coppie();
    $("passo-prezzi").hidden = !cp.length;
    if (!cp.length) return;
    const tab = h("table", "totali");
    const corpo = tab.createTBody();
    cp.forEach((p) => {
      const { valore, n } = prezzo(p);
      const r = corpo.insertRow();
      const th = h("th", null, p.consumo.nome);
      th.appendChild(h("small", null, `con ${p.costo.nome}`));
      r.appendChild(th);
      const td = h("td", "num");
      td.append(h("b", null, valore === null ? "—" : fmt(valore, decimaliPrezzo(p, valore))), " ", h("span", "unita", unitaPrezzo(p)));
      r.appendChild(td);
      r.appendChild(h("td", "num sedi", `${n} ${n === 1 ? "sede" : "sedi"}`));
    });
    pz.appendChild(tab);
    const resto = Math.abs(colonneDi("consumo").length - colonneDi("costo").length);
    if (resto) pz.appendChild(h("p", "aiuto", `${resto} ${resto === 1 ? "colonna è rimasta" : "colonne sono rimaste"} senza abbinamento (le colonne di consumo e di costo non sono lo stesso numero).`));
  }

  // ------------------------------------------------------------------ tabelle con gli interruttori
  function comandiTabella(tipo) {
    const box = $(tipo === "consumo" ? "comandi-consumi" : "comandi-costi");
    box.innerHTML = "";
    const gruppo = (nome, azioni) => {
      const g = h("div", "filtri");
      g.setAttribute("role", "group");
      g.setAttribute("aria-label", nome);
      g.appendChild(h("span", "comandi-nome", `${nome}:`));
      for (const [testo, fa] of azioni) { const b = h("button", "filtro", testo); b.type = "button"; b.addEventListener("click", fa); g.appendChild(b); }
      box.appendChild(g);
    };
    gruppo("Sedi", [
      ["Accendi tutte", () => { stato.sedi.forEach((s) => { s.attiva = true; }); tabelle(); ridisegnaBarre(); }],
      ["Spegni tutte", () => { stato.sedi.forEach((s) => { s.attiva = false; }); tabelle(); ridisegnaBarre(); }],
      ["Ripristina", () => { sceltaAutomatica(); tabelle(); ridisegnaBarre(); }],
    ]);
    gruppo("Colonne", [
      ["Accendi tutte", () => colonneDi(tipo).forEach((c) => mostraColonna(c, true))],
      ["Spegni tutte", () => colonneDi(tipo).forEach((c) => mostraColonna(c, false))],
      ["Ripristina", () => colonneDi(tipo).forEach((c) => mostraColonna(c, true))],
    ]);
  }
  function posizione(s) {
    if (!s.punto) return s.esito === "non_trovato" || !s.esito ? "non sulla mappa" : `${ESITI[s.esito] || s.esito}, non sulla mappa`;
    return [ESITI[s.esito] || s.esito, s.centroide ? "posizione: centro del comune" : ""].filter(Boolean).join(" · ");
  }
  function tabella(tipo) {
    const t = $(tipo === "consumo" ? "tabella-consumi" : "tabella-costi");
    t.innerHTML = "";
    const cols = colonneDi(tipo);
    const conPrezzi = tipo === "costo" && $("prezzi-per-sede").checked ? coppie() : [];
    const r1 = t.createTHead().insertRow();
    const th0 = h("th", null, "Sede");
    th0.appendChild(h("small", null, "casella: sulla mappa"));
    r1.appendChild(th0);
    r1.appendChild(h("th", null, "Posizione"));
    cols.forEach((c) => {
      const th = h("th", "num");
      const lab = h("label", "intestazione-colonna");
      const i = h("input");
      i.type = "checkbox"; i.checked = c.visibile; i.dataset.colonna = c.chiave;
      i.setAttribute("aria-label", `Mostra le barre di ${c.nome}`);
      i.addEventListener("change", () => mostraColonna(c, i.checked));
      const camp = h("i", "campione"); camp.dataset.colonna = c.chiave; camp.style.background = c.colore;
      lab.append(i, camp, h("span", null, c.nome));
      th.append(lab, h("small", null, testoUnita(c) || "—"));
      r1.appendChild(th);
    });
    conPrezzi.forEach((p) => { const th = h("th", "num", `Costo unitario ${p.consumo.nome}`); th.appendChild(h("small", null, unitaPrezzo(p))); r1.appendChild(th); });
    const corpo = t.createTBody();
    stato.sedi.forEach((s) => {
      const r = corpo.insertRow();
      r.classList.toggle("spenta", !s.attiva);
      const th = h("th");
      const lab = h("label", "intestazione-sede");
      const i = h("input");
      i.type = "checkbox"; i.checked = !!s.attiva; i.dataset.sede = s.riga;
      i.setAttribute("aria-label", `Mostra sulla mappa: ${s.titolo}`);
      i.addEventListener("change", () => accendiSede(s, i.checked));
      lab.append(i, h("span", null, s.titolo));
      th.appendChild(lab);
      if (s.comune) th.appendChild(h("small", null, s.comune));
      r.appendChild(th);
      r.appendChild(h("td", `posizione esito-${s.esito || "nd"}`, posizione(s)));
      cols.forEach((c) => { const v = s.valori[stato.colonne.indexOf(c)]; r.appendChild(h("td", v === null ? "num nd" : "num", v === null ? "—" : fmt(v))); });
      conPrezzi.forEach((p) => { const x = prezzo(p, [s]).valore; r.appendChild(h("td", x === null ? "num nd" : "num", x === null ? "—" : fmt(x, decimaliPrezzo(p, x)))); });
    });
  }
  function tabelle() {
    for (const t of ["consumo", "costo"]) {
      const passo = $(t === "consumo" ? "passo-consumi" : "passo-costi");
      passo.hidden = !colonneDi(t).length;
      if (passo.hidden) continue;
      comandiTabella(t);
      tabella(t);
    }
  }
  $("prezzi-per-sede").addEventListener("change", () => stato.caricato && tabella("costo"));

  // ------------------------------------------------------------------ diagrammi di Pareto (un riquadro a schede per tipo)
  function serieOrdinata(c) {
    const k = stato.colonne.indexOf(c);
    return stato.sedi.map((s) => ({ s, v: s.valori[k] })).filter((x) => x.v > 0).sort((a, b) => b.v - a.v);
  }
  function tondo(max) {
    const e = Math.pow(10, Math.floor(Math.log10(max || 1)));
    return [1, 2, 2.5, 5, 10].map((m) => m * e).find((x) => x >= max) || max;
  }
  const breve = (v) => (Math.abs(v) >= 1e6 ? `${fmt(v / 1e6, 1)} mln` : Math.abs(v) >= 1e4 ? `${fmt(v / 1e3, 0)} mila` : fmt(v));
  function disegnaPareto(dest, misure, c) {
    const dati = serieOrdinata(c);
    const riq = misure && misure.riquadro;
    const W = riq ? misure.larghezza : Math.max(300, (misure && misure.larghezza) || 600), H = riq ? misure.altezza : 290;
    const n = dati.length;
    const etichette = n <= 20;
    const sx = 64, dx = 46, su = 26, gi = etichette ? 54 : 24;
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img",
      "aria-label": `Diagramma di Pareto di ${c.nome}: ${n} sedi in ordine decrescente e percentuale cumulata` }, dest);
    if (!n) { el("text", { x: W / 2, y: H / 2, "text-anchor": "middle" }, svg).textContent = "Nessun valore positivo"; return; }
    const totale = dati.reduce((a, x) => a + x.v, 0), max = 4 * tondo(dati[0].v / 4);     // tacche a multipli tondi
    const passo = (W - sx - dx) / n, larg = Math.max(1, passo * 0.72);
    const Y = (v) => su + (H - su - gi) * (1 - v / max), Yp = (p) => su + (H - su - gi) * (1 - p / 100);
    for (let i = 0; i <= 4; i++) {
      const v = max * i / 4;
      el("line", { x1: sx, x2: W - dx, y1: Y(v), y2: Y(v), stroke: "var(--linea)", "stroke-width": 0.6 }, svg);
      el("text", { x: sx - 6, y: Y(v) + 4, "text-anchor": "end" }, svg).textContent = breve(v);
      el("text", { x: W - dx + 6, y: Yp(25 * i) + 4, "text-anchor": "start" }, svg).textContent = `${25 * i} %`;
    }
    el("text", { x: sx - 6, y: 12, "text-anchor": "end", class: "unita-asse" }, svg).textContent = testoUnita(c);
    const y80 = Yp(80);
    el("line", { x1: sx, x2: W - dx, y1: y80, y2: y80, stroke: "var(--segno)", "stroke-dasharray": "7 4", "stroke-width": 1.5 }, svg);
    let cum = 0, k80 = 0;
    const punti = [], linea = [];
    dati.forEach(({ s, v }, i) => {
      const x = sx + passo * (i + 0.5);
      const r = el("rect", { x: x - larg / 2, y: Y(v), width: larg, height: Y(0) - Y(v), fill: c.colore, class: "barra" }, svg);
      cum += v;
      const p = 100 * cum / totale;
      if (!k80 && p >= 80 - 1e-9) k80 = i + 1;
      linea.push(`${x.toFixed(1)},${Yp(p).toFixed(1)}`);
      if (etichette) {
        const t = el("text", { x, y: H - gi + 12, "text-anchor": "end", transform: `rotate(-40 ${x.toFixed(1)} ${(H - gi + 12).toFixed(1)})`, class: "piccolo" }, svg);
        t.textContent = s.id;
      }
      punti.push({ x, titolo: s.titolo, elementi: [r], segni: [[x, Yp(p), "var(--inchiostro)"]],
        righe: [[c.colore, `${c.nome}: ${fmt(v)} ${testoUnita(c)}`], ["var(--inchiostro)", `cumulata: ${fmt(p, 1)} % del totale`],
          [null, `posizione ${i + 1} di ${n}`]] });
    });
    el("polyline", { points: linea.join(" "), fill: "none", stroke: "var(--inchiostro)", "stroke-width": 2, "stroke-linejoin": "round" }, svg);
    if (n <= 60) dati.forEach((d, i) => { const [x, y] = linea[i].split(","); el("circle", { cx: x, cy: y, r: 2.6, fill: "var(--inchiostro)" }, svg); });
    el("text", { x: W - dx - 4, y: y80 - 5, "text-anchor": "end", fill: "var(--segno)", class: "etichetta-legge" }, svg).textContent = "80 %";
    const leg = h("div", "legenda");
    const voce = (cl, colore, testo) => { const sp = h("span"); const i = h("i", cl); i.style.color = colore; if (!cl) i.style.background = colore; sp.append(i, testo); leg.appendChild(sp); };
    voce(null, c.colore, `${c.nome} per sede, dal più grande`);
    voce("linea", "var(--inchiostro)", "percentuale cumulata (asse destro)");
    voce("linea tratto", "var(--segno)", "80 % del totale");
    dest.appendChild(leg);
    dest.appendChild(h("p", "aiuto pareto-sintesi", `Le prime ${k80} sedi su ${n} (${fmt(100 * k80 / n, 0)} %) fanno l'80 % del totale (${fmt(totale)} ${testoUnita(c)}).`));
    if (window.EUGENIO_GRAFICI) window.EUGENIO_GRAFICI.osserva(svg, punti, { area: [sx, su, W - dx, H - gi], guida: false });
  }
  function pareto() {
    for (const t of ["consumo", "costo"]) {
      const box = $(t === "consumo" ? "pareto-consumi" : "pareto-costi");
      const cols = colonneDi(t);
      const scelta = box.dataset.scelta;
      box.innerHTML = "";
      if (!cols.length) continue;
      const schede = h("div", "schede");
      schede.setAttribute("role", "tablist");
      schede.setAttribute("aria-label", `Diagrammi di Pareto dei ${NOMI[t]}`);
      box.appendChild(schede);
      const pannelli = [];
      cols.forEach((c, i) => {
        const b = h("button", null, c.nome);
        b.type = "button"; b.setAttribute("role", "tab"); b.id = `pareto-${c.chiave}`;
        const pan = h("div", "pareto-pannello");
        pan.setAttribute("role", "tabpanel"); pan.setAttribute("aria-labelledby", b.id); pan.id = `pannello-${c.chiave}`;
        b.setAttribute("aria-controls", pan.id);
        schede.appendChild(b); box.appendChild(pan);
        pannelli.push({ b, pan, c });
      });
      const apri = (k, fuoco) => {
        pannelli.forEach((x, j) => {
          const su = j === k;
          x.b.setAttribute("aria-selected", String(su)); x.b.tabIndex = su ? 0 : -1; x.pan.hidden = !su;
          if (su) {
            const g = h("div");
            x.pan.innerHTML = ""; x.pan.appendChild(g);
            if (window.EUGENIO_GRAFICI) window.EUGENIO_GRAFICI.registra(g, (dest, misure) => disegnaPareto(dest, misure, x.c),
              { titolo: `Pareto: ${x.c.nome} (${testoUnita(x.c) || "senza unità"})`, adatta: true });
            else disegnaPareto(g, null, x.c);
          }
        });
        box.dataset.scelta = pannelli[k].c.chiave;
        if (fuoco) pannelli[k].b.focus();
      };
      pannelli.forEach((x, j) => {
        x.b.addEventListener("click", () => apri(j));
        x.b.addEventListener("keydown", (e) => {
          const k = { ArrowRight: j + 1, ArrowLeft: j - 1, Home: 0, End: pannelli.length - 1 }[e.key];
          if (k === undefined) return;
          e.preventDefault();
          apri((k + pannelli.length) % pannelli.length, true);
        });
      });
      apri(Math.max(0, pannelli.findIndex((x) => x.c.chiave === scelta)));
    }
  }

  // ------------------------------------------------------------------ cursori della vista delle barre (tutte le mappe)
  const rot = $("rotazione-barre"), inc = $("inclinazione-barre"), alt = $("altezza-barre"), segue = $("segue-barre");
  function scriviCursori(b) {
    rot.value = Math.round(b.rotazione); inc.value = Math.round(b.inclinazione); alt.value = Math.round(b.altezza * 100);
    segue.checked = b.segue;
    $("rotazione-barre-valore").textContent = `${Math.round(b.rotazione)}°`;
    $("inclinazione-barre-valore").textContent = `${Math.round(b.inclinazione)}°`;
    $("altezza-barre-valore").textContent = `${Math.round(b.altezza * 100)} %`;
  }
  const leggiCursori = () => stato.tipiMappe.forEach((t) => mappaDi(t).impostaBarre({ rotazione: +rot.value, inclinazione: +inc.value, altezza: alt.value / 100, segue: segue.checked }));
  [rot, inc, alt].forEach((c) => c.addEventListener("input", leggiCursori));
  segue.addEventListener("change", leggiCursori);
  $("barre-di-fronte").addEventListener("click", () => {
    stato.tipiMappe.forEach((t) => mappaDi(t).barreDiFronte());
    if (stato.tipiMappe.length) scriviCursori(mappaDi(stato.tipiMappe[0]).statoBarre());
  });
  document.addEventListener("eugenio:vista3d", (e) => {
    if (stato.caricato && ![rot, inc, alt].includes(document.activeElement)) scriviCursori(e.detail.barre);
  });

  // ------------------------------------------------------------------ disegni (SVG) e report
  function notaFonti() {
    return `${P.CITAZIONE} (disegno del ${new Date().toLocaleDateString("it-IT")}). Sedi geolocalizzate con Dati elaborati da Zornade (https://zornade.com)`
      + `${stato.fonti.size ? "; " + [...stato.fonti].join("; ") : ""}`
      + `${[...stato.fonti].some((f) => /ANNCSU/.test(f)) ? "" : "; numeri civici ANNCSU – Agenzia delle Entrate e ISTAT (CC BY 4.0)"}`
      + "; confini dei comuni ISTAT (CC BY 4.0). I valori sono quelli del file caricato.";
  }
  function disegnoMappa(tipo, leggero = false) {
    const m = mappaDi(tipo);
    const visibili = colonneDi(tipo).filter((c) => c.visibile);
    const legenda = visibili.map((c) => [risolvi(c.colore), `${c.nome}${c.unita ? ` (${c.unita.scritta})` : ""}`]);
    const scale = stato.scale.filter((g) => g.colonne.some((c) => c.visibile && c.tipo === tipo));
    const mattoni = scale.map((g) => `1 mattoncino = ${g.testoMattoncino}${scale.length > 1 ? ` (${g.colonne.filter((c) => c.visibile).map((c) => c.nome).join(", ")})` : ""}`);
    const nomi = stato.regioni.map((r) => r.nome).join(", ");
    return m.esporta({
      leggero,
      titolo: `${tipo === "costo" ? "Costi" : "Consumi"} per sede${nomi ? " – " + nomi : ""}`,
      legenda,
      note: [(mattoni.join(" · ") || "") + ". Barre a mattoncini cubici; l'ultimo in cima può essere parziale.", notaFonti()],
    });
  }
  function aggiornaDownload() {
    const box = $("scarica-disegni");
    box.innerHTML = "";
    stato.tipiMappe.forEach((t) => {
      const b = h("button", "bottone secondario", `Scarica la mappa dei ${NOMI[t]} (SVG)`);
      b.type = "button";
      b.addEventListener("click", () => P.scarica(`mappa_${NOMI[t]}.svg`, disegnoMappa(t), "image/svg+xml;charset=utf-8"));
      box.appendChild(b);
    });
  }
  // per il report: colori di stampa (tema chiaro, vestito Corallo), applicati e tolti nello stesso istante, prima che il
  // browser ridisegni la pagina: l'utente non vede nessun cambio
  // (le transizioni dei colori si spengono, altrimenti il colore letto sarebbe quello di partenza della transizione)
  function conColoriDiStampa(fa) {
    const r = document.documentElement, tema = r.dataset.theme, vestito = r.dataset.vestito;
    r.classList.add("senza-transizioni");
    r.dataset.theme = "light"; delete r.dataset.vestito;
    stato.tipiMappe.forEach((t) => mappaDi(t).ricolora());
    try { return fa(); } finally {
      if (tema === undefined) delete r.dataset.theme; else r.dataset.theme = tema;
      if (vestito !== undefined) r.dataset.vestito = vestito;
      stato.tipiMappe.forEach((t) => mappaDi(t).ricolora());
      const p = document.querySelector(".mappa3d .comuni path");
      if (p) void getComputedStyle(p).fill;           // applica i colori veri prima di riaccendere le transizioni
      r.classList.remove("senza-transizioni");
    }
  }
  function base64(testo) {
    const b = new TextEncoder().encode(testo);
    let s = "";
    for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
    return btoa(s);
  }
  function paretoPiatto(c) {
    const fuori = h("div", "grafico fuori-schermo");
    document.body.appendChild(fuori);
    try {
      disegnaPareto(fuori, { larghezza: 760, altezza: 340, riquadro: true }, c);
      const svg = fuori.querySelector("svg");
      const piatto = M3.appiattisci(svg);
      piatto.setAttribute("xmlns", NS);
      piatto.setAttribute("width", 760); piatto.setAttribute("height", 340);
      const fondo = el("rect", { x: 0, y: 0, width: 760, height: 340, fill: "#ffffff" });
      piatto.insertBefore(fondo, piatto.firstChild);
      return new XMLSerializer().serializeToString(piatto);
    } finally { fuori.remove(); }
  }
  function corpoReport() {
    if (!stato.caricato) return null;
    const totali = [], prezzi = [];
    stato.colonne.forEach((c) => { const t = totaliDi(c); totali.push({ colonna: c.nome, tipo: c.tipo, totale: t.somma, unita: testoUnita(c), sedi: t.n }); });
    coppie().forEach((p) => { const x = prezzo(p); prezzi.push({ consumo: p.consumo.nome, costo: p.costo.nome, valore: x.valore, unita: unitaPrezzo(p), sedi: x.n,
      decimali: x.valore === null ? null : decimaliPrezzo(p, x.valore) }); });
    const immagini = conColoriDiStampa(() => ({
      mappe: stato.tipiMappe.map((t) => ({ titolo: `Mappa dei ${NOMI[t]}`, svg: base64(disegnoMappa(t, true)) })),
      pareto: stato.colonne.slice(0, 8).map((c) => ({ titolo: `Pareto: ${c.nome}`, tipo: c.tipo, svg: base64(paretoPiatto(c)) })),
    }));
    const tabelle = ["consumo", "costo"].filter((t) => colonneDi(t).length).map((t) => {
      const cols = colonneDi(t), cp = t === "costo" && $("prezzi-per-sede").checked ? coppie() : [];
      return {
        titolo: t === "consumo" ? "Consumi per sede" : "Costi per sede", tipo: t,
        intestazioni: ["Sede", "Comune", "Posizione", "Sulla mappa", ...cols.map((c) => `${c.nome}${c.unita ? ` (${c.unita.scritta})` : ""}`),
          ...cp.map((p) => `Costo unitario ${p.consumo.nome} (${unitaPrezzo(p)})`)],
        righe: stato.sedi.map((s) => [s.titolo, s.comune || null, posizione(s), s.attiva && s.punto ? "sì" : "no",
          ...cols.map((c) => s.valori[stato.colonne.indexOf(c)]), ...cp.map((p) => prezzo(p, [s]).valore)]),
        // decimali: nessuno per le colonne coi valori grandi (MWh, Smc, €), due per le altre; costi unitari: 2 per l'energia (€/MWh), 3 per gli altri
        decimali: [null, null, null, null, ...cols.map((c) => (Math.max(0, ...stato.sedi.map((s) => Math.abs(s.valori[stato.colonne.indexOf(c)] || 0))) >= 1000 ? 0 : 2)),
          ...cp.map((p) => (scalaPrezzo(p).decimali !== null ? scalaPrezzo(p).decimali : 3))],
      };
    });
    const note = ["I totali e i diagrammi di Pareto sono calcolati su tutte le sedi del file; le mappe mostrano solo le sedi accese.",
      "Abbinamento per posizione: la prima colonna di consumo da sinistra va con la prima colonna di costo da sinistra, e così via."];

    const nomi = stato.regioni.map((r) => r.nome).join(", ");
    return { titolo: "Valori per sede", sottotitolo: `${stato.sedi.length} sedi${nomi ? " – " + nomi : ""}`,
      totali, prezzi, ...immagini, tabelle, note, fonti: [...stato.fonti],
      ...(stato.esempio ? { avviso: { titolo: AVVISO_TITOLO, testo: AVVISO_TESTO } } : {}) };
  }
  if (window.EUGENIO_REPORT) {
    const area = h("div", "messaggio");
    area.id = "messaggio-report"; area.setAttribute("role", "status");
    $("report-valori").appendChild(area);
    window.EUGENIO_REPORT.pulsanti($("report-valori"), {
      tipo: "valori_sedi", corpo: corpoReport, nome: (ext) => `valori_per_sede.${ext}`,
      messaggio: (t, e) => { area.textContent = t; area.classList.toggle("errore", !!e); }, area: "messaggio-report",
    });
  }

  // avviso del file d'esempio sotto i titoli di mappe e tabelle (tolto se si carica un altro file)
  function avvisiEsempio() {
    document.querySelectorAll(".avviso-esempio").forEach((x) => x.remove());
    if (!stato.esempio) return;
    const crea = () => {
      const d = h("div", "messaggio attenzione avviso-esempio");
      d.setAttribute("role", "note");
      const dd = h("div");
      dd.append(h("b", null, AVVISO_TITOLO), AVVISO_TESTO);
      d.appendChild(dd);
      return d;
    };
    // nella colonna sinistra un solo riquadro, in fondo, subito prima delle fonti («Particelle catastali…»)
    const piede = $("piede");
    if (piede && piede.parentElement === document.querySelector(".mappa-area")) piede.before(crea());
    else document.querySelector(".mappa-area").appendChild(crea());
    ["passo-totali", "passo-consumi", "passo-costi"].forEach((id) => $(id).querySelector("h2").after(crea()));
  }

  // ------------------------------------------------------------------ invio
  $("calcola-valori").addEventListener("click", async () => {
    const b = $("calcola-valori");
    b.disabled = true;
    try {
      messaggio("Lettura del file…");
      const letto = await T.leggi(stato.file);
      const a = analizza(letto.testo, letto.decimalePunto);
      const testo = csvPerServer(a);
      $("avanzamento-valori").hidden = false;
      const r = await P.geolocalizza(testo, "sedi.csv", {
        avvisa: (t) => messaggio(t.replace("gli edifici", "le sedi")),
        barra: (f) => { $("barra-valori").style.width = `${(100 * f).toFixed(1)}%`; },
      });
      const perId = new Map(r.righe.map((x) => [String(x.id), x]));
      const iCom = a.chiavi.indexOf("comune"), iDen = a.chiavi.indexOf("denominazione");
      a.sedi.forEach((s, n) => {
        let x = r.righe[n];
        if (!x || String(x.id) !== s.id) x = perId.get(s.id) || null;
        s.esito = x ? x.esito : null;
        s.comuneFile = (iCom >= 0 && s.celle[iCom]) || (x && x.comune) || "";
        s.comune = (x && (x.comune || x.comune_catasto)) || s.comuneFile || "";
        const den = (iDen >= 0 && s.celle[iDen]) || (x && x.denominazione) || "";
        s.titolo = [s.id, den].filter(Boolean).join(" · ");
        s.punto = x && x.lat !== null && x.lat !== undefined && x.lon !== null && x.lon !== undefined ? P.lonlatSvg(+x.lon, +x.lat) : null;
      });
      stato.colonne = a.colonne; stato.sedi = a.sedi; stato.fonti = r.fonti;
      stato.esempio = a.esempio || /valori_sedi_esempio/i.test(stato.file.name);
      avvisiEsempio();
      messaggio("Preparo la mappa…");
      calcolaScale();
      await preparaMappe();          // territorio, centro dei comuni, comuni e province delle sedi
      sceltaAutomatica();
      ridisegnaBarre();
      // inquadratura con le barre delle sedi accese (5 % di bordo intorno a mappa e cime delle barre)
      stato.tipiMappe.forEach((t) => mappaDi(t).adatta());
      stato.caricato = true;
      const sulla = a.sedi.filter((s) => s.punto).length, centro = a.sedi.filter((s) => s.centroide).length;
      const spente = a.sedi.filter((s) => !s.attiva).length;
      const nc = colonneDi("consumo").length, nk = colonneDi("costo").length;
      const unitaTesto = a.rigaUnita ? `Riga delle unità riconosciuta (${a.colonne.map((c) => c.unita ? c.unita.scritta : "—").join(", ")}).`
        : a.colonne.some((c) => c.unita) ? "Unità lette dai titoli o dalle celle." : "Nessuna unità: ogni colonna ha la sua scala.";
      messaggio([
        stato.esempio ? `${AVVISO_TITOLO}.` : "",
        `${nc} ${nc === 1 ? "colonna" : "colonne"} di consumo e ${nk} di costo; ${sulla} sedi su ${a.sedi.length} sulla mappa`
          + (centro ? ` (${centro} al centro del comune)` : "") + (spente ? `, ${spente} spente perché nel loro comune ce ne sono più di ${SEDI_PER_COMUNE}` : "") + ".",
        unitaTesto, letto.nota, r.interrotto].filter(Boolean).join(" "), !!r.interrotto);
      totali();
      tabelle();
      pareto();
      aggiornaDownload();
      ["passo-totali", "passo-vista", "passo-report"].forEach((id) => { $(id).hidden = false; });
      $("fonti-valori").textContent = "";
      const z = h("a", null, "Dati elaborati da Zornade"); z.href = "https://zornade.com";
      $("fonti-valori").append("Sedi geolocalizzate con: ", z, ". ", [...stato.fonti].join("; "), stato.fonti.size ? ". " : "",
        "I valori sono quelli del file caricato e non lasciano il browser.");
      P.numeraPassi();
    } catch (e) {
      console.warn(e);
      messaggio(`Non riuscito: ${e.message}`, true);
    } finally {
      $("avanzamento-valori").hidden = true;
      b.disabled = !stato.file;
    }
  });

  function impostaFile(f) {
    stato.file = f || null;
    $("nome-valori").textContent = f ? `${f.name} · ${(f.size / 1024).toFixed(0)} kB` : "Scegli il file o trascinalo qui";
    $("zona-valori").classList.toggle("pieno", !!f);
    $("calcola-valori").disabled = !f;
    messaggio("");
  }
  const campo = $("file-valori");
  campo.setAttribute("accept", T.ACCETTA);
  campo.addEventListener("change", (e) => impostaFile(e.target.files[0]));
  const zona = $("zona-valori");
  ["dragover", "dragenter"].forEach((t) => zona.addEventListener(t, (e) => { e.preventDefault(); zona.classList.add("pieno"); }));
  zona.addEventListener("dragleave", () => zona.classList.toggle("pieno", !!stato.file));
  zona.addEventListener("drop", (e) => { e.preventDefault(); impostaFile(e.dataTransfer.files[0]); });

  // per le prove: le funzioni di calcolo senza interfaccia e lo stato
  window.EUGENIO_VALORI = { analizza, unita, valuta, mattoncino, conUnita, corpoReport, stato };
})();
