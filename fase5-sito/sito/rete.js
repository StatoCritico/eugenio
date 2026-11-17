"use strict";
// Rete elettrica (17/11/2026, richiesta di Paolo): parte comune alle pagine Statistiche › «Stato della rete elettrica»
// (rete-elettrica.html, rete_elettrica.js) e Fotovoltaico › «Cabine primarie» (fv-cabine.html, fv_cabine.js).
// Contratto dei dati e delle licenze: CONTRATTO_RETE (documenti/CABINE_PRIMARIE_DECISIONI_E_RACCORDO_2026-11-17.md e
// README della fase 5, § «Rete elettrica»).
//
//  - API del servizio (tutte GET, JSON): /api/rete/stato, /api/rete/cabine[?regione=RR], /api/rete/comuni?regione=RR,
//    /api/rete/interruzioni/attive[?regione=RR], /api/rete/interruzioni/comune/<istat>, /api/rete/cabine/comune/<istat>.
//    Con ?prova=1 nell'indirizzo (o window.EUGENIO_RETE_PROVA = true prima dello script) niente server: dati SINTETICI
//    generati qui dai confini ISTAT del sito (dati/mappa/RR.json), dichiarati con un avviso in pagina e nei file.
//  - Colori: cabine primarie dal livello peggiore dei trasformatori (VERDE = bianco, GIALLO, ARANCIONE, ROSSO; altri
//    gestori o senza dato = grigio), punti grandi con il bordo scuro; comuni pieni o a strisce secondo la regola della
//    criticità (classeComune, identica a quella del servizio notturno): livello più alto L e quota q dei trasformatori
//    con L; VERDE → niente; q > 0,5 → pieno di L; altrimenti strisce tra il livello precedente e L.
//  - GSE (aree convenzionali delle cabine primarie): letto **dal browser** dal servizio pubblico del GSE, mai dal server
//    di EuGEnio né salvato; l'indirizzo del servizio è solo qui (GSE.SERVIZIO). Punto → COD_AC senza geometria
//    (gse.areaNelPunto), poligoni semplificati delle sole aree scelte con where=COD_AC IN (…) (gse.aree, max 100).
//
//  const R = EUGENIO_RETE
//  R.PROVA, R.api(percorso), R.LIVELLI, R.COLORI, R.classeComune(trasf), R.coloreCabina(p), R.testoTrasf(trasf)
//  R.immagini(mappa)                      motivi delle strisce e del retino (si rifanno al cambio di tema)
//  R.stratoCabine(mappa, sorgente, { prima })  punti grandi delle cabine (id "<sorgente>-punti")
//  R.suggerimento(mappa, strati, contenuto)    riquadretto al passaggio del mouse o al tocco ({ titolo, righe })
//  R.righeCabina(p), R.dataIt(iso), R.oraIt(iso), R.num(n, dec)
//  R.csv(nome, sezioni, piede), R.documento(doc, formato, messaggio)  file CSV nel browser, PDF/XLSX da POST /api/report
//  R.gse.areaNelPunto(lon, lat), R.gse.aree(codici), R.gse.geojson(aree, sediPerArea)
(function () {
  const parametri = new URLSearchParams(location.search);
  const PROVA = parametri.get("prova") === "1" || window.EUGENIO_RETE_PROVA === true;
  const LIVELLI = ["VERDE", "GIALLO", "ARANCIONE", "ROSSO"];
  const NOMI = { VERDE: "verde", GIALLO: "giallo", ARANCIONE: "arancione", ROSSO: "rosso" };
  const PLURALI = { VERDE: "verdi", GIALLO: "gialli", ARANCIONE: "arancioni", ROSSO: "rossi" };
  // VERDE (nessuna criticità) disegnato bianco, come chiesto da Paolo; grigio per altri gestori o senza dato
  const COLORI = { VERDE: "#ffffff", GIALLO: "#f5c400", ARANCIONE: "#f08a00", ROSSO: "#d32f2f", GRIGIO: "#9a9a9a" };
  const BORDO = "#1a1a1a";
  const FONTE = "Fonte: EuGEnio – eugenio.statocritico.it";
  const ATTR = {
    ed: "Saturazione delle cabine primarie (dato mensile per trasformatore, «aree critiche») e interruzioni: e-distribuzione S.p.A., dati pubblici citati come fonte",
    ed_breve: "e-distribuzione S.p.A. (aree critiche e interruzioni, dati pubblici)",
    osm: "Posizioni delle cabine primarie: © contributori OpenStreetMap, ODbL 1.0 (https://www.openstreetmap.org/copyright)",
    gse: "Aree convenzionali: © GSE S.p.A. – CC BY-NC-SA 3.0 IT, letti dal servizio del GSE",
    gse_codici: "Codici delle aree convenzionali (COD_AC): GSE S.p.A., mappa interattiva delle cabine primarie",
    criticita: "Criticità dei comuni: classificazione di EuGEnio dai dati mensili per trasformatore di e-distribuzione",
    confini: "Confini: ISTAT, unità amministrative a fini statistici (generalizzati), CC BY 4.0",
  };
  const URL_ED = "https://www.e-distribuzione.it/a-chi-ci-rivolgiamo/produttori/aree-critiche.html";
  const URL_ED_INT = "https://www.e-distribuzione.it/";
  const URL_OSM = "https://www.openstreetmap.org/copyright";
  const GSE = {
    SERVIZIO: "https://services-eu1.arcgis.com/sawHMGY9o8rHlY2j/arcgis/rest/services/AC_Comuni_2025/FeatureServer/0",
    SCHEDA: "https://www.gse.it/servizi-per-te/autoconsumo/mappa-interattiva-delle-cabine-primarie",
    LICENZA: "CC BY-NC-SA 3.0 IT – https://creativecommons.org/licenses/by-nc-sa/3.0/it/",
    FONTE: "GSE S.p.A. – Mappa interattiva delle cabine primarie – https://www.gse.it/servizi-per-te/autoconsumo/mappa-interattiva-delle-cabine-primarie",
    AVVISO: "Estratto letto dal servizio pubblico del GSE al momento del download, geometrie semplificate. Non fa parte dei dati CC BY 4.0 di EuGEnio. La verifica ufficiale dell'area di un punto di connessione è la ricerca per POD del GSE.",
    MASSIMO: 100,
    SEMPLIFICA: 0.0002,         // ~20 m (maxAllowableOffset in gradi)
  };

  const num = (n, dec = 0) => (n === null || n === undefined || !Number.isFinite(+n) ? "–"
    : (+n).toLocaleString("it-IT", { minimumFractionDigits: dec, maximumFractionDigits: dec }));
  function dataIt(iso) {
    if (!iso) return "–";
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? String(iso) : d.toLocaleDateString("it-IT", { day: "2-digit", month: "2-digit", year: "numeric", timeZone: "Europe/Rome" });
  }
  function oraIt(iso) {
    if (!iso) return "–";
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? String(iso)
      : d.toLocaleString("it-IT", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Rome" });
  }
  const oggi = () => new Date().toLocaleDateString("it-IT", { timeZone: "Europe/Rome" });

  // ------------------------------------------------------------------ regola della criticità (come il servizio)
  function classeComune(trasf) {
    const t = trasf || {}, tot = LIVELLI.reduce((s, k) => s + (+t[k] || 0), 0);
    if (!tot) return { livello: null, quota: null, pieno: null, strisce: null };
    const L = [...LIVELLI].reverse().find((k) => (+t[k] || 0) > 0);
    const quota = (+t[L] || 0) / tot;
    if (L === "VERDE") return { livello: L, quota, pieno: null, strisce: null };
    if (quota > 0.5) return { livello: L, quota, pieno: L, strisce: null };
    return { livello: L, quota, pieno: null, strisce: [LIVELLI[LIVELLI.indexOf(L) - 1], L] };
  }
  const eDistribuzione = (g) => !g || /e-?\s?distribuzione/i.test(String(g));
  function coloreCabina(p) {
    if (!p || !p.livello || !LIVELLI.includes(p.livello) || !eDistribuzione(p.gestore)) return COLORI.GRIGIO;
    return COLORI[p.livello];
  }
  function testoTrasf(trasf) {
    if (!trasf) return "nessun dato";
    const parti = LIVELLI.filter((k) => +trasf[k]).map((k) => `${trasf[k]} ${+trasf[k] === 1 ? NOMI[k] : PLURALI[k]}`);
    return parti.length ? parti.join(", ") : "nessun dato";
  }
  function testoClasse(c) {
    if (!c || !c.livello) return "nessun dato";
    if (c.pieno) return `${NOMI[c.pieno]} pieno (${num(100 * c.quota)} % dei trasformatori ${PLURALI[c.livello]})`;
    if (c.strisce) return `strisce ${NOMI[c.strisce[0]]}/${NOMI[c.strisce[1]]} (${num(100 * c.quota)} % dei trasformatori ${PLURALI[c.livello]})`;
    return "nessuna criticità (tutti i trasformatori verdi)";
  }
  // righe del riquadretto e della scheda di una cabina
  function righeCabina(p) {
    const r = [];
    if (p.cod_cp_ed) r.push(`Codice e-distribuzione: ${p.cod_cp_ed}`);
    r.push(`Area GSE (COD_AC): ${p.cod_ac || "non abbinata"}`);
    r.push(`Gestore: ${p.gestore || "e-distribuzione"}`);
    r.push(`Trasformatori: ${testoTrasf(p.trasf)}`);
    if (p.data_saturazione) r.push(`Dato del ${dataIt(p.data_saturazione)}`);
    if (p.esito && p.esito !== "sicuro") r.push(`Raccordo: ${{ da_verificare: "da verificare", solo_gse: "solo area GSE (cabina senza dati di e-distribuzione)", senza_posizione: "senza posizione" }[p.esito] || p.esito}`);
    return r;
  }
  const nomeCabina = (p) => p.nome_cp_ed || p.osm_nome || p.nome || p.cod_cp_ed || p.cod_ac || "Cabina primaria";

  // ------------------------------------------------------------------ immagini delle strisce e del retino
  function rgb(hex) { const n = parseInt(String(hex).replace("#", ""), 16); return [n >> 16, (n >> 8) & 255, n & 255]; }
  function motivo(a, b, alfaB = 255, lato = 16, larga = 4) {
    // strisce diagonali a 45° di larghezza `larga` pixel, colori a e b (b null = trasparente)
    const d = new Uint8Array(lato * lato * 4), A = rgb(a), B = b ? rgb(b) : [0, 0, 0];
    for (let y = 0; y < lato; y++) for (let x = 0; x < lato; x++) {
      const k = (y * lato + x) * 4, primo = Math.floor(((x + y) % lato) / larga) % 2 === 0;
      const c = primo ? A : B;
      d[k] = c[0]; d[k + 1] = c[1]; d[k + 2] = c[2]; d[k + 3] = primo ? 255 : (b ? alfaB : 0);
    }
    return { width: lato, height: lato, data: d };
  }
  function retino(colore, lato = 10) {
    const d = new Uint8Array(lato * lato * 4), C = rgb(colore);
    for (let y = 0; y < lato; y++) for (let x = 0; x < lato; x++) {
      const k = (y * lato + x) * 4, su = (x + y) % lato === 0 || (x - y + lato) % lato === 0;
      d[k] = C[0]; d[k + 1] = C[1]; d[k + 2] = C[2]; d[k + 3] = su ? 230 : 0;
    }
    return { width: lato, height: lato, data: d };
  }
  const css = (n, d) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || d;
  function immagini(m) {
    const fai = () => {
      const im = {
        "strisce-GIALLO": motivo(COLORI.VERDE, COLORI.GIALLO),
        "strisce-ARANCIONE": motivo(COLORI.GIALLO, COLORI.ARANCIONE),
        "strisce-ROSSO": motivo(COLORI.ARANCIONE, COLORI.ROSSO),
        "retino": retino(/^#[0-9a-f]{6}$/i.test(css("--inchiostro")) ? css("--inchiostro") : "#888888"),
        "senza-dato": motivo("#9a9a9a", null, 0, 12, 2),
      };
      for (const [k, v] of Object.entries(im)) { if (m.hasImage(k)) m.updateImage(k, v); else m.addImage(k, v); }
    };
    fai();
    document.addEventListener("eugenio:aspetto", fai);
  }
  // campione CSS della legenda (stesso disegno delle immagini della mappa)
  function campione(tipo, livello) {
    const i = document.createElement("i");
    i.className = "campione-rete";
    if (tipo === "pieno") i.style.background = COLORI[livello];
    else if (tipo === "strisce") {
      const a = COLORI[LIVELLI[LIVELLI.indexOf(livello) - 1]], b = COLORI[livello];
      i.style.background = `repeating-linear-gradient(-45deg, ${a} 0 3px, ${b} 3px 6px)`;
    } else if (tipo === "retino") i.style.background = "repeating-linear-gradient(45deg, var(--inchiostro) 0 1px, transparent 1px 5px), repeating-linear-gradient(-45deg, var(--inchiostro) 0 1px, transparent 1px 5px)";
    else if (tipo === "senza-dato") i.style.background = "repeating-linear-gradient(-45deg, #9a9a9a 0 2px, transparent 2px 6px)";
    else if (tipo === "cabina") { i.className = "campione-rete cabina"; i.style.background = livello in COLORI ? COLORI[livello] : livello; }
    else if (tipo === "punto") { i.className = "campione-rete punto"; i.style.background = livello; }
    else if (tipo === "area") { i.className = "campione-rete area"; }
    else if (tipo === "in-parte") { i.className = "campione-rete in-parte"; }
    return i;
  }

  // ------------------------------------------------------------------ strato delle cabine
  function stratoCabine(m, sorgente, opz = {}) {
    const id = `${sorgente}-punti`;
    m.addLayer({ id, type: "circle", source: sorgente, paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 5, 4.5, 8, 7, 12, 10, 16, 12],
      "circle-color": ["coalesce", ["get", "_colore"], COLORI.GRIGIO],
      "circle-stroke-color": BORDO, "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 5, 1.2, 12, 2],
    } }, opz.prima && m.getLayer(opz.prima) ? opz.prima : undefined);
    return id;
  }
  // proprietà di disegno aggiunte alle cabine (colore calcolato una volta sola)
  function preparaCabine(gj) {
    const fs = (gj && gj.features) || [];
    fs.forEach((f) => { f.properties = f.properties || {}; if (typeof f.properties.trasf === "string") { try { f.properties.trasf = JSON.parse(f.properties.trasf); } catch { /* resta */ } } f.properties._colore = coloreCabina(f.properties); });
    return { type: "FeatureCollection", features: fs.filter((f) => f.geometry && f.geometry.type === "Point") };
  }

  // ------------------------------------------------------------------ riquadretto (mouse e tocco)
  function suggerimento(m, strati, contenuto) {
    const box = m.getContainer();
    let et = box.querySelector(":scope > .etichetta-mappa");
    if (!et) { et = document.createElement("div"); et.className = "etichetta-mappa"; et.setAttribute("aria-hidden", "true"); box.appendChild(et); }
    let timer = 0;
    const visibili = () => strati().filter((id) => m.getLayer(id) && m.getLayoutProperty(id, "visibility") !== "none");
    function mostra(e, tocco) {
      const f = visibili().length ? m.queryRenderedFeatures(e.point, { layers: visibili() })[0] : null;
      const c = f ? contenuto(f) : null;
      m.getCanvas().style.cursor = c && c.cursore !== false ? "pointer" : "";
      if (!c) { et.style.display = "none"; return; }
      et.innerHTML = "";
      const b = document.createElement("b"); b.textContent = c.titolo; et.appendChild(b);
      for (const r of c.righe || []) {
        const d = document.createElement("div");
        if (Array.isArray(r)) { if (r[0]) { const i = document.createElement("i"); i.style.background = r[0]; d.appendChild(i); } d.append(r[1]); }
        else d.textContent = r;
        et.appendChild(d);
      }
      et.style.display = "block";
      const W = box.clientWidth, H = box.clientHeight, w = et.offsetWidth, h = et.offsetHeight;
      let x = e.point.x + 14, y = e.point.y + 16;
      if (x + w > W - 4) x = e.point.x - 14 - w;
      if (y + h > H - 4) y = e.point.y - 16 - h;
      et.style.left = `${Math.max(4, Math.min(x, W - w - 4))}px`; et.style.top = `${Math.max(4, y)}px`;
      clearTimeout(timer);
      if (tocco) timer = setTimeout(() => { et.style.display = "none"; }, 3500);
    }
    m.on("mousemove", (e) => mostra(e, false));
    m.on("mouseout", () => { et.style.display = "none"; });
    m.on("movestart", () => { et.style.display = "none"; });
    m.on("click", (e) => { if (e.originalEvent && e.originalEvent.pointerType === "touch") mostra(e, true); });
    m.on("touchend", (e) => mostra(e, true));
    return { nascondi: () => { et.style.display = "none"; } };
  }

  // ------------------------------------------------------------------ API (o dati sintetici di prova)
  async function api(percorso) {
    if (PROVA) return finto(percorso);
    const r = await fetch(percorso, { headers: { Accept: "application/json" } });
    if (!r.ok) throw new Error(r.status === 404 ? "servizio della rete non ancora attivo sul server" : `errore ${r.status}`);
    if (!/json/.test(r.headers.get("Content-Type") || "")) throw new Error("risposta non valida dal server");
    return r.json();
  }

  // ---- dati SINTETICI (?prova=1): deterministici, dai confini ISTAT del sito; nessuna richiesta al server
  function hash(s) { let h = 2166136261; for (const c of String(s)) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }
  const casuale = (s, n) => hash(s) % n;
  function centro(g) {
    let migliore = null, area = -1;
    for (const p of g.coordinates) {
      const r = p[0]; let a = 0, x = 0, y = 0;
      for (let i = 0; i < r.length - 1; i++) { a += Math.abs(r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1]); x += r[i][0]; y += r[i][1]; }
      if (a > area) { area = a; migliore = [x / (r.length - 1), y / (r.length - 1)]; }
    }
    return migliore;
  }
  const finti = new Map();
  async function regioneFinta(cod) {
    if (finti.has(cod)) return finti.get(cod);
    const p = (async () => {
      const C = window.EUGENIO_CONFINI;
      const fc = await C.comuniRegione(cod);
      const comuni = fc.features.map((f) => ({ istat: f.properties.istat, nome: f.properties.nome, prov: f.properties.prov, c: centro(f.geometry) }))
        .filter((c) => c.c).sort((a, b) => a.istat.localeCompare(b.istat));
      const mancante = (istat) => istat.startsWith("001");          // Torino: come il servizio vero oggi (500)
      const cabine = comuni.filter((c, i) => i % 7 === 0).map((c, k) => {
        const altro = k % 11 === 5;
        const trasf = altro || mancante(c.istat) ? null : { VERDE: 1 + casuale(c.istat + "v", 3), GIALLO: casuale(c.istat + "g", 3),
          ARANCIONE: casuale(c.istat + "a", 4) > 1 ? casuale(c.istat + "a2", 2) : 0, ROSSO: casuale(c.istat + "r", 5) > 2 ? 1 + casuale(c.istat + "r2", 2) : 0 };
        const cl = trasf ? classeComune(trasf) : { livello: null };
        return { istat: c.istat, c: [c.c[0] + 0.004, c.c[1] + 0.003], p: {
          cod_ac: `AC${String(cod).padStart(3, "0")}E${String(10000 + casuale(c.istat + "ac", 89999)).padStart(5, "0")}`,
          gestore: altro ? "Altro distributore S.p.A. (sintetico)" : "e-distribuzione",
          cod_cp_ed: altro ? "" : `DV${String(100000000 + casuale(c.istat + "cp", 899999999))}`,
          nome_cp_ed: altro ? "" : `CP ${c.nome.toUpperCase()} (sintetica)`, osm_nome: altro ? `Sottostazione ${c.nome} (sintetica)` : "",
          esito: altro ? "solo_gse" : "sicuro", livello: cl.livello, trasf, data_saturazione: "2026-11-01", comuni_serviti: "" } };
      });
      // ogni comune servito dalla cabina più vicina (e, uno su cinque, anche dalla seconda)
      const serviti = new Map(cabine.map((x) => [x, []]));
      const d2 = (a, b) => (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2;
      for (const c of comuni) {
        const ord = cabine.filter((x) => x.p.gestore === "e-distribuzione").sort((a, b) => d2(a.c, c.c) - d2(b.c, c.c));
        ord.slice(0, casuale(c.istat + "2", 5) === 0 ? 2 : 1).forEach((x) => serviti.get(x).push(c.istat));
      }
      cabine.forEach((x) => { x.p.comuni_serviti = serviti.get(x).join(";"); });
      const gj = { type: "FeatureCollection", licenza: "ODbL 1.0 (posizioni) – DATI SINTETICI DI PROVA", attribuzione: ATTR.osm,
        features: cabine.map((x) => ({ type: "Feature", properties: { ...x.p }, geometry: { type: "Point", coordinates: x.c } })) };
      const perComune = new Map();
      cabine.forEach((x) => serviti.get(x).forEach((i) => { if (!perComune.has(i)) perComune.set(i, []); perComune.get(i).push(x); }));
      const righe = comuni.map((c) => {
        const conc = casuale(c.istat + "conc", 13) !== 0;
        const cs = perComune.get(c.istat) || [];
        if (!conc || mancante(c.istat)) return { istat: c.istat, nome: c.nome, concessionario: conc, mancante: conc && mancante(c.istat), pieno: null, strisce: null, livello: null, quota: null, trasf: null, cabine: [] };
        // trasformatori del comune: una parte di quelli delle sue cabine
        const t = { VERDE: 0, GIALLO: 0, ARANCIONE: 0, ROSSO: 0 };
        cs.forEach((x) => LIVELLI.forEach((k) => { t[k] += x.p.trasf ? Math.min(x.p.trasf[k], 1 + casuale(c.istat + k, 2)) : 0; }));
        if (!LIVELLI.some((k) => t[k])) t.VERDE = 1;
        // (17/11/2026 sera) un comune ogni 41 «servito in parte da un altro distributore» (come i 35 comuni milanesi veri)
        return { istat: c.istat, nome: c.nome, concessionario: true, servito_in_parte: casuale(c.istat + "parte", 41) === 7, ...classeComune(t), trasf: t,
          cabine: cs.map((x) => x.p.cod_cp_ed).filter(Boolean) };
      });
      const interruzioni = comuni.filter((c) => casuale(c.istat + "int", 37) === 3).slice(0, 12).map((c, k) => ({
        type: "Feature", geometry: { type: "Point", coordinates: [c.c[0] - 0.006, c.c[1] + 0.002] },
        properties: { id: `INT${cod}${k}`, comune: c.istat, nome_comune: c.nome, causa: k % 3 ? "Guasto" : "Lavori programmati",
          clienti: 5 + casuale(c.istat + "cl", 400), inizio: new Date(Date.now() - (20 + casuale(c.istat + "t", 300)) * 60000).toISOString(),
          ripristino_previsto: new Date(Date.now() + (30 + casuale(c.istat + "rp", 240)) * 60000).toISOString(),
          durata_min: 20 + casuale(c.istat + "t", 300) } }));
      return { comuni, cabine: gj, righe, interruzioni };
    })();
    p.catch(() => finti.delete(cod));
    finti.set(cod, p);
    return p;
  }
  // regione sintetica già generata che contiene il comune (le pagine caricano prima la regione)
  async function regioneDi(istat) {
    for (const p of finti.values()) { const r = await p; if (r.comuni.some((c) => c.istat === istat)) return r; }
    return null;
  }
  async function finto(percorso) {
    const u = new URL(percorso, location.href), p = u.pathname, reg = u.searchParams.get("regione") || "08";
    await new Promise((ok) => setTimeout(ok, 30));
    if (p.endsWith("/api/rete/stato")) return { saturazione_aggiornata: "2026-11-17T03:10:00+01:00", interruzioni_aggiornate: new Date(Date.now() - 6 * 60000).toISOString(),
      attive: 7, province_mancanti: ["001"], raccolta_dal: "2026-11-17T18:00:00+01:00", sintetico: true, nota_servito_in_parte: "servito in parte da un altro distributore",
      fonti: { saturazione: URL_ED, interruzioni: URL_ED_INT }, licenze: { posizioni: "ODbL 1.0", codici: "con citazione della fonte" } };
    if (p.endsWith("/api/rete/cabine")) return (await regioneFinta(reg)).cabine;
    if (p.endsWith("/api/rete/comuni")) return (await regioneFinta(reg)).righe;
    if (p.endsWith("/api/rete/interruzioni/attive")) return { type: "FeatureCollection", features: (await regioneFinta(reg)).interruzioni };
    let m = /\/api\/rete\/interruzioni\/comune\/(\d{6})$/.exec(p);
    if (m) {
      const istat = m[1], r = await regioneDi(istat), h = (k) => casuale(istat + k, 1000);
      const mesi = ["2026-06", "2026-07", "2026-08", "2026-09", "2026-10", "2026-11"];
      const per_mese = mesi.map((mese, i) => { const n = h(mese) % 6, g = Math.min(n, h(mese + "g") % 5); return { mese, n, guasti: g, programmati: n - g,
        clienti: n * (10 + h(mese + "c") % 90), durata_media_min: n ? 30 + h(mese + "d") % 200 : null, durata_max_min: n ? 120 + h(mese + "x") % 400 : null }; });
      const tot = per_mese.reduce((a, x) => ({ n: a.n + x.n, guasti: a.guasti + x.guasti, programmati: a.programmati + x.programmati, clienti: a.clienti + x.clienti }), { n: 0, guasti: 0, programmati: 0, clienti: 0 });
      const attive = r ? r.interruzioni.filter((f) => f.properties.comune === istat).map((f) => f.properties) : [];
      return { istat, dal: "2026-06-01", sintetico: true, totale: { ...tot, durata_media_min: tot.n ? 95 : null, durata_max_min: tot.n ? 480 : null },
        per_mese, per_causa: { Guasto: tot.guasti, "Lavori programmati": tot.programmati }, attive,
        ultime: per_mese.filter((x) => x.n).slice(-3).map((x, i) => ({ id: `S${i}`, inizio: `${x.mese}-1${i}T08:15:00+02:00`, fine_stimata: `${x.mese}-1${i}T10:00:00+02:00`,
          causa: i % 2 ? "Lavori programmati" : "Guasto", clienti: 40 + i * 13, durata_min: 105 })) };
    }
    m = /\/api\/rete\/cabine\/comune\/(\d{6})$/.exec(p);
    if (m) {
      const r = await regioneDi(m[1]);
      return { type: "FeatureCollection", features: r ? r.cabine.features.filter((f) => (f.properties.comuni_serviti || "").split(";").includes(m[1])) : [] };
    }
    throw new Error(`percorso di prova sconosciuto: ${p}`);
  }

  // ------------------------------------------------------------------ GSE dal browser
  const GSE_QUERY = `${GSE.SERVIZIO}/query`;
  async function gseGet(par) {
    const u = new URL(GSE_QUERY);
    Object.entries({ f: "geojson", outSR: "4326", ...par }).forEach(([k, v]) => u.searchParams.set(k, v));
    const r = await fetch(u.toString(), { mode: "cors", credentials: "omit" });
    if (!r.ok) throw new Error(`servizio del GSE: errore ${r.status}`);
    const d = await r.json();
    if (d && d.error) throw new Error(`servizio del GSE: ${d.error.message || "errore"}`);
    return d;
  }
  // area convenzionale che contiene il punto: { COD_AC, RAG_SOC, COD_CONSEG } o null (senza geometria)
  async function areaNelPunto(lon, lat) {
    if (PROVA) {
      const C = window.EUGENIO_CONFINI, cod = C && (await C.regioneNelPunto(lon, lat));
      if (!cod) return null;
      const r = await regioneFinta(cod);
      let best = null, d = Infinity;
      for (const f of r.cabine.features) { const [x, y] = f.geometry.coordinates, e = (x - lon) ** 2 + (y - lat) ** 2; if (e < d) { d = e; best = f; } }
      return best ? { COD_AC: best.properties.cod_ac, RAG_SOC: best.properties.gestore, COD_CONSEG: `CS${best.properties.cod_ac.slice(-4)}` } : null;
    }
    const d = await gseGet({ geometry: `${lon},${lat}`, geometryType: "esriGeometryPoint", inSR: "4326", spatialRel: "esriSpatialRelIntersects",
      outFields: "COD_AC,RAG_SOC,COD_CONSEG", returnGeometry: "false" });
    const f = d && d.features && d.features[0];
    return f ? { COD_AC: f.properties.COD_AC, RAG_SOC: f.properties.RAG_SOC, COD_CONSEG: f.properties.COD_CONSEG } : null;
  }
  // poligoni semplificati delle aree con questi codici (al massimo GSE.MASSIMO), FeatureCollection in lon/lat
  async function aree(codici) {
    const cs = [...new Set(codici.filter((c) => /^[A-Za-z0-9_-]{3,20}$/.test(String(c || ""))))];
    if (!cs.length) return { type: "FeatureCollection", features: [] };
    if (cs.length > GSE.MASSIMO) throw new Error(`troppe aree (${cs.length}): al massimo ${GSE.MASSIMO}, restringi la selezione`);
    if (PROVA) {
      const fs = [];
      for (const r of await Promise.all([...finti.values()])) for (const f of r.cabine.features) {
        if (!cs.includes(f.properties.cod_ac)) continue;
        const [x, y] = f.geometry.coordinates, a = 0.05, b = 0.035;
        fs.push({ type: "Feature", properties: { COD_AC: f.properties.cod_ac, RAG_SOC: f.properties.gestore, COD_CONSEG: `CS${f.properties.cod_ac.slice(-4)}` },
          geometry: { type: "Polygon", coordinates: [[[x - a, y - b], [x + a, y - b * 1.3], [x + a * 1.2, y + b], [x - a * 0.8, y + b * 1.1], [x - a, y - b]]] } });
      }
      return { type: "FeatureCollection", features: fs };
    }
    const fs = [];
    for (let i = 0; i < cs.length; i += 50) {          // URL corti: 50 codici per richiesta
      const parte = cs.slice(i, i + 50);
      const d = await gseGet({ where: `COD_AC IN (${parte.map((c) => `'${c}'`).join(",")})`, outFields: "COD_AC,RAG_SOC,COD_CONSEG",
        returnGeometry: "true", maxAllowableOffset: String(GSE.SEMPLIFICA), geometryPrecision: "5" });
      fs.push(...((d && d.features) || []));
    }
    return { type: "FeatureCollection", features: fs };
  }
  // il file separato (contratto: max 100 aree, proprietà solo COD_AC, gestore, COD_CONSEG e sedi dell'utente)
  function geojson(fc, sediPerArea) {
    return {
      type: "FeatureCollection",
      licenza: GSE.LICENZA,
      fonte: GSE.FONTE,
      servizio: GSE.SERVIZIO,
      letto_il: new Date().toISOString(),
      avviso: GSE.AVVISO,
      crs: { type: "name", properties: { name: "urn:ogc:def:crs:OGC:1.3:CRS84" } },
      features: fc.features.slice(0, GSE.MASSIMO).map((f) => ({ type: "Feature", geometry: f.geometry, properties: {
        COD_AC: f.properties.COD_AC, gestore: f.properties.RAG_SOC || "", COD_CONSEG: f.properties.COD_CONSEG || "",
        sedi: (sediPerArea && sediPerArea.get(f.properties.COD_AC)) || [] } })),
    };
  }

  // ------------------------------------------------------------------ file scaricati
  function scaricaBlob(blob, nome) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = nome;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }
  const cellaCsv = (v) => {
    if (v === null || v === undefined) return "";
    if (typeof v === "number") return Number.isInteger(v) ? String(v) : String(v).replace(".", ",");
    const s = String(v);
    return /[;"\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  // CSV per Excel italiano: citazione in riga 1 (regola dei file di EuGEnio), una sezione per tabella, fonti in fondo
  function csv(nome, sezioni, piede = []) {
    const righe = [`${FONTE} (dati estratti il ${oggi()})`];
    if (PROVA) righe.push("ATTENZIONE: DATI SINTETICI DI PROVA (?prova=1), non reali");
    for (const s of sezioni) {
      righe.push("", cellaCsv(s.titolo), s.intestazioni.map(cellaCsv).join(";"));
      for (const r of s.righe) righe.push(r.map(cellaCsv).join(";"));
    }
    righe.push("", ...piede.map((p) => `${cellaCsv(p)}`));
    scaricaBlob(new Blob(["﻿" + righe.join("\r\n")], { type: "text/csv;charset=utf-8" }), nome);
  }
  // PDF ed Excel dal servizio comune dei documenti (POST /api/report, modello in fase4-server/servizio/report.py)
  async function documento(doc, formato, messaggio) {
    const scrivi = (t, e = false) => { if (messaggio) { messaggio.textContent = t; messaggio.classList.toggle("errore", e); } };
    scrivi(`Preparo il file ${formato.toUpperCase()}…`);
    let r;
    try {
      r = await fetch(`/api/report?formato=${encodeURIComponent(formato)}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(doc) });
    } catch { scrivi("Server non raggiungibile: riprova più tardi (il CSV si prepara anche senza server).", true); return false; }
    if (!r.ok) {
      let det = "";
      try { const d = await r.json(); det = typeof d.detail === "string" ? d.detail : ""; } catch { /* niente */ }
      scrivi(r.status === 429 ? "Hai raggiunto il limite dei file per ora: riprova tra qualche minuto." : `File non preparato (errore ${r.status}${det ? `: ${det}` : ""}).`, true);
      return false;
    }
    const R = window.EUGENIO_REPORT;
    const nome = (R && R.nomeDaIntestazione(r.headers.get("Content-Disposition"))) || `${doc.nome_file || "eugenio"}.${formato}`;
    scaricaBlob(await r.blob(), nome);
    scrivi(`Download avviato: ${nome}.`);
    return true;
  }
  // pulsanti «Scarica i dati: CSV · Excel · PDF»; dati() → { csv: [nome, sezioni, piede], doc } o un testo (motivo)
  function pulsantiDati(dove, dati, messaggio) {
    const box = document.createElement("div"); box.className = "scarica scarica-dati-rete";
    const t = document.createElement("span"); t.className = "scarica-titolo"; t.textContent = "Scarica i dati:"; box.appendChild(t);
    for (const [f, nome] of [["csv", "CSV"], ["xlsx", "Excel"], ["pdf", "PDF"]]) {
      const b = document.createElement("button"); b.type = "button"; b.className = "bottone secondario"; b.dataset.formato = f; b.textContent = nome;
      b.title = `Scarica i dati in ${nome}, con fonti e licenze`;
      b.addEventListener("click", async () => {
        const d = dati();
        if (typeof d === "string") { if (messaggio) { messaggio.textContent = d; messaggio.classList.add("errore"); } return; }
        if (f === "csv") { csv(...d.csv); if (messaggio) { messaggio.textContent = `Download avviato: ${d.csv[0]}.`; messaggio.classList.remove("errore"); } return; }
        b.disabled = true;
        try { await documento(d.doc, f, messaggio); } finally { b.disabled = false; }
      });
      box.appendChild(b);
    }
    dove.appendChild(box);
    return box;
  }
  // tabella HTML semplice (table.mensili dentro .tabella-scorre, con la freccina del riquadro)
  function tabella(intestazioni, righe, { titolo = "", num: numeriche = [] } = {}) {
    const box = document.createElement("div"); box.className = "tabella-scorre"; if (titolo) box.dataset.titolo = titolo;
    const t = document.createElement("table"); t.className = "mensili";
    const th = t.createTHead().insertRow();
    intestazioni.forEach((x, i) => { const c = document.createElement("th"); c.textContent = x; if (numeriche.includes(i)) c.className = "num"; th.appendChild(c); });
    const tb = t.createTBody();
    for (const r of righe) {
      const tr = tb.insertRow();
      r.forEach((v, i) => {
        const c = tr.insertCell();
        if (v instanceof Node) c.appendChild(v); else c.textContent = v === null || v === undefined ? "–" : String(v);
        if (numeriche.includes(i)) c.className = "num";
      });
    }
    box.appendChild(t);
    return box;
  }
  function avvisoProva(dove) {
    if (!PROVA || !dove) return;
    const p = document.createElement("div"); p.className = "messaggio attenzione rete-prova"; p.setAttribute("role", "note");
    p.innerHTML = "<div><b>Dati sintetici di prova</b>Modo di prova (<code>?prova=1</code>): cabine, criticità, interruzioni e aree "
      + "sono inventati nel browser dai confini ISTAT, non vengono dal server né dal GSE e non sono reali.</div>";
    dove.prepend(p);
  }

  window.EUGENIO_RETE = { PROVA, LIVELLI, NOMI, COLORI, BORDO, ATTR, FONTE, URL_ED, URL_ED_INT, URL_OSM, GSE, api, classeComune, coloreCabina,
    testoTrasf, testoClasse, righeCabina, nomeCabina, eDistribuzione, immagini, campione, stratoCabine, preparaCabine, suggerimento, num, dataIt, oraIt, oggi,
    csv, documento, pulsantiDati, tabella, avvisoProva, scaricaBlob,
    gse: { areaNelPunto, aree, geojson } };
})();
