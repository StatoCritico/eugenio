"use strict";
// Strumento 3D degli edifici (fase 10, Fase A): pagine Modelli 3D, Edificio › Geometria, Edificio › Consumi,
// Fotovoltaico › Ombre e Fotovoltaico › Producibilità. Stessa pagina, con un'apertura diversa (data-vista sul <main>).
//
// Dati (file statici serviti da Caddy, vedi fase4-server/Caddyfile, o la demo sintetica in dati/edifici3d/):
//   <base>/indice.json          centro, riquadro, celle, licenza, attribuzione, sintetico
//   <base>/corpi.pmtiles        corpi estrusi (MapLibre, protocollo pmtiles)
//   /api/terreno/{z}/{x}/{y}.png terreno raster-dem in codifica Terrarium, generato dal server su richiesta dal DTM 5 m
//                                (07/11/2026: il DTM non è più negli archivi dei comuni; <base>/terreno.pmtiles solo se
//                                l'archivio lo ha ancora: demo sintetica, archivi vecchi, prove con --terreno-archivio)
//   <base>/contesto/<i>_<j>.json  sagome intere per i calcoli (celle di 0,01°)
// La base è /edifici3d/cc-by/er/prodotti/ sul server; se manca si usa la demo sintetica (con l'avviso).
// Clima: /api/edifici/clima-orario/{istat} e /api/edifici/gradi-giorno/{istat} (archivio meteo di EuGEnio); se il server
// non li ha ancora la producibilità usa un anno di cielo sereno ridotto (sintetico, dichiarato) e la firma non si calcola.
// Profilo d'orizzonte delle aree FV e delle facciate nel Web Worker ombre_worker.js. Report con report.js (tipo «edificio»).
//
// Fase B (04/11/2026): sfondo con le ortofoto del proxy del server (/api/ortofoto/fonti, licenza e citazione sotto la
// mappa e nel report), orizzonte lontano dal Copernicus DEM (/api/edifici/orizzonte) unito a quello degli edifici vicini,
// sole sulle facciate segmento per segmento (solo le parti esposte, § 7), confronto con PVGIS chiamato dal server
// (/api/edifici/pvgis), obblighi di legge (D.Lgs. 199/2021, Allegato III; S/V e zona climatica, analisi 14) e classifica
// di priorità del patrimonio (analisi 4).
//
// Fase C (04/11/2026): falde dei tetti dal LiDAR (<base>/lidar/indice.json e lidar/falde/<i>_<j>.json, scritti dalla
// pipeline notturna della fase 10): gronda, colmo, tetto e falde (pendenza, orientamento, superficie) prendono il posto
// delle stime del DBTR, le falde inclinate si vedono a gradini colorati per orientamento e le aree FV disegnate su una
// falda ne prendono inclinazione e orientamento. Modello dell'utente: GeoJSON «eugenio-modello-1» prodotto dal comando
// `importa-modello` (DXF, IFC) e aperto solo nel browser, senza inviarlo al server.
//
// Modelli 3D in due tempi (05/11/2026, prove di Paolo sul sito pubblicato): la pagina Modelli 3D si apre su una mappa 2D
// (Italia e regione con la piccola mappa, confini ISTAT, ortofoto o contesto Sentinel-2 sotto, zoom con la rotella e
// trascinamento) con la ricerca per indirizzo o per foglio e particella (POST /api/patrimonio con una riga: ANNCSU, poi
// Zornade, come la pagina Patrimonio) e il clic sull'edificio (in evidenza; secondo clic = lo toglie). «Genera il 3D»
// costruisce l'alzato dell'edificio e dell'intorno con, per ogni corpo, la fonte più affidabile disponibile (falde LiDAR →
// DB topografico regionale con le altezze → modello importato DXF/IFC → OSM → stima), detta in pagina, nell'immagine e nel
// report; rotazione e zoom con gli stessi comandi della mappa 3D del Patrimonio (mappa3d.js), «Scarica l'immagine» (JPG,
// PNG, PDF con le attribuzioni) e «Torna alla mappa 2D». La demo sintetica si apre solo con ?archivio=demo (pulsante
// «Prova la demo sintetica»), è dichiarata e non va mai sopra un'ortofoto vera: le sue sagome sono inventate, allineate
// alla griglia UTM e non a strade vere, e sembravano «storte» sulla foto. Le altre pagine 3D restano in un tempo solo.
// Archivi: /edifici3d/archivi.json ({"archivi": [{"base": "/edifici3d/cc-by/er/prodotti/", "nome": …}, …]}, in ordine di
// affidabilità) se c'è, altrimenti il DBTR dell'Emilia-Romagna; i corpi di un archivio meno affidabile che cadono dentro
// quelli di uno più affidabile non si usano.
//
// Seconda pubblicazione del 05/11/2026 (prove di Paolo su ?v=20261109b):
//  - il punto trovato con la ricerca (cerca_luogo.js, modulo comune con Ortofoto) si **trascina** per correggerlo (l'ANNCSU
//    è a volte impreciso) e, da zoom 15, un clic sulla mappa lo sposta lì; la scelta dell'edificio usa sempre il punto
//    corretto (l'edificio che lo contiene, o il più vicino entro 30 m) e «Genera il 3D» parte da lì;
//  - **«Esci dalla demo»** sempre visibile nella demo (2D e 3D): riapre la pagina normale, con ortofoto e ricerca;
//    «Torna alla mappa 2D» nella demo resta nella 2D della demo;
//  - **livelli** con le caselle: ortofoto (con la scelta della fonte), confini delle particelle catastali e contorni degli
//    edifici (strati_gl.js, dal proxy del server), con legenda e attribuzioni sotto la mappa e nell'immagine scaricata;
//    nella demo restano spenti (i dati veri non vanno sopra gli edifici inventati).
//
// Ripiego OpenStreetMap (07/11/2026, decisione di Paolo): dove il punto (ricerca, punto trascinato, clic, sede del
// Patrimonio) cade fuori da ogni archivio DBTR – fuori dall'Emilia-Romagna e nei comuni ER non ancora preparati – la
// pagina chiede al server gli edifici OSM intorno al punto (GET /api/edifici/osm, Overpass, celle di 0,002° con copia) e
// li usa come corpi, con licenza ODbL 1.0 e altezze in parte stimate, dichiarate in pagina, nell'immagine e nel report.
// Dove c'è il DBTR vale il DBTR e OSM non si mescola: un archivio di un comune intero (`istat` in archivi.json) copre il
// confine ISTAT del comune (confini_gl.js), gli altri il riquadro dei corpi; i corpi OSM che cadono in un comune coperto
// si scartano. Archivio «virtuale» in fondo a stato.archivi ({ osm: true }), sorgente GeoJSON «corpi_<k>» sulla mappa.
//
// DB topografico letto nel browser (07/11/2026, pagina «Aggiungi edifici (DB topografico)», dbtr_locale.js): con
// ?dbtr=locale (o nella stessa sessione della scheda) gli edifici del file dell'utente diventano un archivio «locale»
// ({ locale: true }, sorgente GeoJSON, celle in memoria), prima degli archivi del server per la scelta dei corpi (dove si
// sovrappongono vince il file dell'utente) e «zona coperta» per la sessione: confine ISTAT del comune se il file è il
// comune intero, altrimenti il riquadro dei corpi; fuori resta il ripiego OSM. Mai inviati al server.
(function () {
  const E = window.EUGENIO_EDIFICI, G = window.EUGENIO_GRAFICI, R = window.EUGENIO_REPORT;
  const main = document.querySelector("main.pagina-edificio3d");
  if (!E || !main) return;
  const $ = (id) => document.getElementById(id);
  const VISTA = main.dataset.vista || "modelli";
  // ?archivio=demo forza la demo sintetica; ?archivio=<percorso> un altro archivio (per esempio odbl/er/prodotti/)
  const SCELTA = new URLSearchParams(location.search).get("archivio");
  const BASI = SCELTA === "demo" ? ["dati/edifici3d/"] : SCELTA ? [`/edifici3d/${SCELTA.replace(/^\/+|\.\.+/g, "").replace(/\/?$/, "/")}`]
    : ["/edifici3d/cc-by/er/prodotti/", "dati/edifici3d/"];
  const RAGGIO = 250;
  const ZOOM_CERCA = (window.EUGENIO_CERCA && window.EUGENIO_CERCA.ZOOM) || 17;   // zoom dopo la ricerca, uguale in Ortofoto (cerca_luogo.js)
  // Modelli 3D in due tempi (05/11/2026): mappa 2D con ricerca e scelta, poi «Genera il 3D». Dal 07/11/2026 sera tutte le
  // pagine 3D (Edificio, Fotovoltaico) hanno la stessa mappa di Modelli 3D (stessi elementi nell'HTML): stessi archivi per
  // comune, ripiego OSM, DB topografico del browser, terreno dal server; data-vista sceglie solo il passo in evidenza
  const DUE_TEMPI = !!$("genera-3d");
  const TITOLO = VISTA === "modelli" ? "Modelli 3D" : (($("mappa3d") && document.querySelector("main h1")) || {}).textContent || "Modelli 3D";
  const C = window.EUGENIO_CONFINI;
  const fmt = (v, d = 0) => (v === null || v === undefined || !Number.isFinite(+v) ? "—" : (+v).toLocaleString("it-IT", { maximumFractionDigits: d, minimumFractionDigits: d }));
  const NOMI_FONTE = { csv: "dato inserito", visura: "visura", stima: "stima", mancante: "—", "dato del corpo": "dato del corpo" };
  const stato = { base: null, indice: null, mappa: null, celle: new Map(), corpi: [], originali: [], edificio: null, vicini: [],
    proj: null, istat: null, comune: null, csv: {}, uso: "", aree: [], modo: null, punti: [], anima: null, firma: null, fv: null,
    giornaliero: null, sintetico: false, ortofoto: null, fontiOrtofoto: [], lontano: null, facciate: null, pvgis: null,
    fvOrizzonti: {}, obblighi: null, dpr: null, lidar: null, falde: new Map(), celleFalde: new Map(), nascostiExtra: [], modello: null,
    alberi: new Map(), celleAlberi: new Map(), visura: {}, sede: null, archivi: [], in3d: !DUE_TEMPI, daGenerare: null, regione: null,
    osmAttivo: false, osm: { celle: new Map(), visti: new Map(), errore: null, info: null },
    // (09/11/2026) colore degli edifici e alberi accesi (spenti in partenza): preferenze del browser
    coloreEdifici: (() => { try { return localStorage.getItem("eugenio-colore-edifici") || "grigio"; } catch { return "grigio"; } })(),
    alberiVisibili: (() => { try { return localStorage.getItem("eugenio-alberi-3d") === "1"; } catch { return false; } })() };
  // archivio «virtuale» del ripiego OpenStreetMap (07/11/2026): ultimo di stato.archivi, senza file statici
  const ATTRIBUZIONE_OSM = "© OpenStreetMap contributors (ODbL 1.0)";
  // terreno 3D dal server (07/11/2026, fase4-server/servizio/terreno.py): DTM regionale, altrove Copernicus DEM 90 m
  const ATTRIBUZIONE_TERRENO = "Terreno: DTM regionali (Regione Emilia-Romagna – DTM 5×5 m, CC BY 4.0; Regione del Veneto – DTM 5 m da voli LiDAR, IODL 2.0); altrove Copernicus DEM GLO-90 (© DLR e Airbus)";
  const TESSERE_TERRENO = "/api/terreno/{z}/{x}/{y}.png";
  const MARGINE_CONFINE = 150;             // m: un punto a questa distanza da un corpo DBTR è coperto (confini ISTAT generalizzati)
  const COLORE_OSM = "#9a6440";            // marrone: edifici OpenStreetMap (altezza dal dato OSM, dai piani, dai vicini o 9 m)
  // colore degli edifici del DB topografico (09/11/2026, richiesta di Paolo): menu a discesa come quello dell'asterisco della
  // testata; grigio (predefinito, --serie-6 del tema), giallo, rosso, indaco, violetto. L'edificio scelto resta nel colore
  // primario (arancio), gli edifici OpenStreetMap restano marroni (dicono la fonte). Scelta ricordata nel browser.
  const COLORI_EDIFICI = [
    { id: "grigio", nome: "Grigio", colore: null }, { id: "giallo", nome: "Giallo", colore: "#e0b400" },
    { id: "rosso", nome: "Rosso", colore: "#c62828" }, { id: "indaco", nome: "Indaco", colore: "#4757c9" },
    { id: "violetto", nome: "Violetto", colore: "#8a4fd0" }];
  const CHIAVE_COLORE = "eugenio-colore-edifici", CHIAVE_ALBERI = "eugenio-alberi-3d";
  const leggiPref = (k) => { try { return localStorage.getItem(k); } catch { return null; } };
  const scriviPref = (k, v) => { try { localStorage.setItem(k, v); } catch { /* archivio del browser non disponibile */ } };
  const voceColore = () => COLORI_EDIFICI.find((c) => c.id === stato.coloreEdifici) || COLORI_EDIFICI[0];
  const coloreEdifici = () => voceColore().colore || colore("--serie-6");
  // l'archivio ha ancora le sue tessere del terreno? (indice.tessere_terreno: demo sintetica, archivi preparati prima del 07/11)
  const terrenoProprio = (a) => !!(a && a.base && !a.osm && !a.locale && a.indice && a.indice.tessere_terreno);
  const ARCHIVIO_OSM = { base: null, osm: true, indice: { nome: "OpenStreetMap (ripiego fuori dal DBTR)", licenza: "ODbL 1.0", attribuzione: ATTRIBUZIONE_OSM } };
  const CELLA_OSM = 0.002;                 // come servizio/edifici_osm.py: una richiesta (e una copia) per cella
  const veri = () => stato.archivi.filter((a) => !a.osm);
  const LOCALE = window.EUGENIO_DBTR_LOCALE;
  // archivio «locale» (DB topografico letto nel browser): celle di 0,01° in memoria, come le celle di contesto del server
  function archivioLocale(d) {
    const C0 = 0.01, celle = new Map();
    const fs = d.features.filter((f) => f && f.geometry && f.properties && f.properties.id !== undefined);
    for (const f of fs) {
      const r = anelli(f.geometry)[0];
      if (!r) continue;
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      for (const q of r) { if (q[0] < x0) x0 = q[0]; if (q[0] > x1) x1 = q[0]; if (q[1] < y0) y0 = q[1]; if (q[1] > y1) y1 = q[1]; }
      for (let i = Math.floor(x0 / C0); i <= Math.floor(x1 / C0); i++)
        for (let j = Math.floor(y0 / C0); j <= Math.floor(y1 / C0); j++) {
          const k = `${i}_${j}`; if (!celle.has(k)) celle.set(k, []); celle.get(k).push(f);
        }
      f.properties.licenza = f.properties.licenza || d.licenza || "CC BY 4.0";
    }
    const r = Array.isArray(d.riquadro) && d.riquadro.length === 4 ? d.riquadro.map(Number) : [0, 0, 0, 0];
    return { base: null, locale: true, celle, features: fs, istat: /^\d{6}$/.test(String(d.istat || "")) ? String(d.istat) : null,
      indice: { nome: String(d.nome || "DB topografico dal tuo file").slice(0, 120), licenza: d.licenza || "CC BY 4.0",
        attribuzione: `${String(d.attribuzione || "").slice(0, 200)} (file caricato dall'utente, letto solo in questo browser)`,
        riquadro: r, cella: C0, centro: [(r[0] + r[2]) / 2, (r[1] + r[3]) / 2], corpi: fs.length } };
  }
  const archivioDi = (c) => stato.archivi[(c && c.archivio) || 0] || null;
  // la rotta del ripiego OSM c'è? (422 senza parametri = sì; 404 = spenta o api non ancora ricostruita)
  async function osmDisponibile() {
    try { const r = await fetch("/api/edifici/osm"); return r.status !== 404; } catch { return false; }
  }

  function h(tag, cls, testo) { const e = document.createElement(tag); if (cls) e.className = cls; if (testo !== undefined && testo !== null) e.textContent = testo; return e; }
  function messaggio(id, t, errore = false) { const m = $(id); if (!m) return; m.textContent = t; m.classList.toggle("errore", errore); }
  const colore = (nome) => getComputedStyle(document.documentElement).getPropertyValue(nome).trim() || "#888";

  // ------------------------------------------------------------------ dati
  async function json(url) { const r = await fetch(url); if (!r.ok) throw new Error(`${url}: ${r.status}`); return r.json(); }
  async function trovaBase() {
    for (const b of BASI) {
      try { const i = await json(`${b}indice.json`); return { base: b, indice: i }; } catch { /* prossima */ }
    }
    throw new Error("archivio degli edifici non raggiungibile");
  }
  // tutti gli archivi veri, nell'ordine di affidabilità (pagina Modelli 3D in due tempi); la demo solo con ?archivio=demo
  async function trovaArchivi() {
    if (SCELTA || !DUE_TEMPI) { try { return [await trovaBase()]; } catch { return []; } }
    let elenco = null;
    const valida = (b) => typeof b === "string" && /^\/edifici3d\/[\w-]+(\/[\w-]+)*\/$/.test(b) && !b.includes("..");
    try {
      const r = await fetch("/edifici3d/archivi.json?v=20261109b", { cache: "no-cache" });   // mai l'elenco vecchio
      if (r.ok && /json/.test(r.headers.get("Content-Type") || "")) {
        const d = await r.json();
        elenco = d.archivi;
        if (valida(d.lidar)) stato.baseLidar = d.lidar;        // falde LiDAR dell'ER (07/11/2026: archivi per comune)
      }
    } catch { /* nessun elenco: solo l'archivio dell'Emilia-Romagna */ }
    // fino a 150 archivi (un archivio DBTR per comune dal 07/11/2026; 60 fino al 09/11/2026, quando sono diventati 69): la
    // pagina legge le celle solo di quelli vicini al punto
    // `istat` (07/11/2026): archivio di un comune intero, zona coperta = confine ISTAT del comune
    const voci = (Array.isArray(elenco) && elenco.length ? elenco : [{ base: "/edifici3d/cc-by/er/prodotti/" }])
      .filter((x) => x && valida(x.base)).slice(0, 150);
    const codice = (v) => (/^\d{6}$/.test(String(v || "")) ? String(v) : null);
    const trovati = await Promise.all(voci.map((v) => json(`${v.base}indice.json`)
      .then((i) => ({ base: v.base, indice: i, istat: i.parziale ? null : codice(v.istat) || codice(i.istat) })).catch(() => null)));
    return trovati.filter((x) => x && !x.indice.sintetico);
  }
  // celle che l'archivio ha davvero (indice.nomi_celle): le altre non si chiedono (07/11/2026 sera: 404 rumorosi nella
  // console quando il raggio di 250 m tocca il riquadro di un comune vicino)
  function haCella(base, nome) {
    const a = stato.archivi.find((x) => x.base === base) || (base === stato.base ? { indice: stato.indice } : null);
    const n = a && a.indice && a.indice.nomi_celle;
    if (!Array.isArray(n)) return true;
    if (!a.insiemeCelle) a.insiemeCelle = new Set(n);
    return a.insiemeCelle.has(nome);
  }
  async function cella(nome, base = stato.base) {
    const k = `${base}|${nome}`;
    if (!haCella(base, nome)) return { features: [] };
    if (!stato.celle.has(k)) stato.celle.set(k, json(`${base}contesto/${nome}.json`).catch(() => ({ features: [] })));
    return stato.celle.get(k);
  }
  // (09/11/2026 b, righe rosse in Console) celle LiDAR che esistono davvero: `lidar/indice.json` ha dal 09/11 b l'elenco
  // `celle.falde` e `celle.alberi` (scritto dalla pipeline a ogni tessera e dal comando `lidar-celle`); le altre non si
  // chiedono più (prima: 404 per ogni cella attorno al punto, anche a Roma, Susegana, Firenze, dove la pipeline non passa).
  // Indice senza elenco (pipeline di prima): solo dentro il riquadro di un archivio dell'Emilia-Romagna (unica zona della
  // pipeline), mai altrove
  function haCellaLidar(tipo, nome, lon, lat) {
    const L = stato.lidar;
    if (!L) return false;
    const el = L.celle && L.celle[tipo];
    if (Array.isArray(el)) {
      const k = `insieme_${tipo}`;
      if (!L[k]) Object.defineProperty(L, k, { value: new Set(el), enumerable: false });
      return L[k].has(nome);
    }
    return stato.archivi.some((a) => a.base && a.base.startsWith("/edifici3d/cc-by/er/") && Array.isArray(a.indice && a.indice.riquadro)
      && lon >= a.indice.riquadro[0] && lon <= a.indice.riquadro[2] && lat >= a.indice.riquadro[1] && lat <= a.indice.riquadro[3]);
  }
  // alberi dal DSM (05/11/2026): quadrati di 2 m con l'altezza della chioma, per tessera, nelle stesse celle di 0,01°
  async function cellaAlberi(nome) {
    if (!stato.celleAlberi.has(nome)) {
      stato.celleAlberi.set(nome, json(`${stato.baseLidar || stato.base}lidar/alberi/${nome}.json`).then((d) => {
        Object.values((d && d.tessere) || {}).forEach((l) => l.forEach((a) => stato.alberi.set(`${a[0]},${a[1]}`, a)));
      }).catch(() => null));
    }
    return stato.celleAlberi.get(nome);
  }
  // falde dal LiDAR (stesse celle di 0,01°, indicizzate per corpo); senza rilievo la cella non c'è
  async function cellaFalde(nome) {
    if (!stato.celleFalde.has(nome)) {
      stato.celleFalde.set(nome, json(`${stato.baseLidar || stato.base}lidar/falde/${nome}.json`).then((d) => {
        Object.entries((d && d.corpi) || {}).forEach(([id, r]) => stato.falde.set(String(id), r));
      }).catch(() => null));
    }
    return stato.celleFalde.get(nome);
  }
  // falde (dal LiDAR o dal modello dell'utente) → coordinate locali; solo valori numerici controllati
  function faldeLocali(lista, fonte) {
    if (!Array.isArray(lista)) return null;
    const out = [];
    for (const f of lista.slice(0, 60)) {
      const g = f && f.geometria;
      const anello = g && (g.type === "Polygon" ? g.coordinates[0] : g.type === "MultiPolygon" ? g.coordinates[0][0] : null);
      const n = (v) => (Number.isFinite(+v) ? +v : null);
      if (!Array.isArray(anello) || anello.length < 4 || n(f.pendenza) === null) continue;
      out.push({ id: String(f.id || `F${out.length + 1}`).slice(0, 12), ring: anello.slice(0, 2000).map((q) => stato.proj.avanti([+q[0], +q[1]])),
        pendenza: Math.min(90, Math.max(0, n(f.pendenza))), orientamento: ((n(f.orientamento) ?? 180) % 360 + 360) % 360,
        superficie: n(f.superficie), area_pianta: n(f.area_pianta), alto: n(f.alto), basso: n(f.basso), fonte });
    }
    return out.length ? out : null;
  }
  // corpi nel raggio di 250 m da (lon, lat): celle che coprono il cerchio
  function nomiCelle(indice, lon, lat) {
    const c = (indice && indice.cella) || 0.01, dlon = RAGGIO / (111320 * Math.cos(lat * Math.PI / 180)), dlat = RAGGIO / 110574;
    const nomi = [];
    for (let i = Math.floor((lon - dlon) / c); i <= Math.floor((lon + dlon) / c); i++)
      for (let j = Math.floor((lat - dlat) / c); j <= Math.floor((lat + dlat) / c); j++) nomi.push(`${i}_${j}`);
    return nomi;
  }
  // con più archivi: per ogni archivio, nell'ordine, i corpi che non cadono dentro quelli di un archivio già usato
  async function contesto(lon, lat) {
    const archivi = stato.archivi.length ? stato.archivi : stato.base ? [{ base: stato.base, indice: stato.indice }] : [];
    if (!archivi.length) return [];
    const nomi0 = nomiCelle({ cella: (stato.lidar && stato.lidar.cella) || 0.01 }, lon, lat);
    await Promise.all([Promise.all(nomi0.filter((n) => haCellaLidar("falde", n, lon, lat)).map(cellaFalde)),
      Promise.all(nomi0.filter((n) => haCellaLidar("alberi", n, lon, lat)).map(cellaAlberi))]);
    const pr = E.proiezione(lon, lat), visti = new Map(), sagome = [];
    const vicino = (a) => { const r = a.indice && a.indice.riquadro, m = 0.004;          // ~300 m: i 250 m del contesto
      return !Array.isArray(r) || r.length !== 4 || (lon >= r[0] - m && lon <= r[2] + m && lat >= r[1] - m && lat <= r[3] + m); };
    // ripiego OSM solo se il punto è fuori da ogni archivio DBTR (07/11/2026)
    const usaOsm = stato.osmAttivo && archivi.some((a) => a.osm) && !(await coperto(lon, lat));
    // il DB topografico letto nel browser per primo: dove si sovrappone a un archivio del server vince il file dell'utente
    const ordine = archivi.map((_, k) => k).sort((x, y) => (archivi[y].locale ? 1 : 0) - (archivi[x].locale ? 1 : 0));
    for (const k of ordine) {
      const a = archivi[k];
      if (a.osm ? !usaOsm : !vicino(a)) continue;
      const fc = a.osm ? [{ features: await edificiOsm(lon, lat) }]
        : a.locale ? nomiCelle(a.indice, lon, lat).map((n) => ({ features: a.celle.get(n) || [] }))
          : await Promise.all(nomiCelle(a.indice, lon, lat).map((n) => cella(n, a.base)));
      const lic = a.indice.licenza || "";
      const nuovi = [];
      fc.forEach((x) => (x.features || []).forEach((f) => {
        const id = String(f.properties.id);
        if (visti.has(id) || !f.geometry) return;
        const [esterno, ...fori] = anelli(f.geometry);
        if (!esterno) return;
        const sag = { ring: esterno.map(pr.avanti), buchi: fori.map((r) => r.map(pr.avanti)), lic, locale: !!a.locale };
        // già coperto da una fonte migliore (un corpo nel cortile di un altro non è coperto)
        // (archivi della stessa licenza, come i DBTR di due comuni vicini, non si sovrappongono: niente controllo)
        if (sagome.some((s) => (s.lic !== lic || s.locale) && E.dentroCorpo(E.centroide(sag.ring), s))) return;
        f.properties.archivio = k;
        visti.set(id, f); nuovi.push(sag);
      }));
      sagome.push(...nuovi);
    }
    return [...visti.values()];
  }
  // edifici OSM della cella del punto (servizio/edifici_osm.py): una richiesta per cella, tenuta in memoria; i corpi che
  // cadono in un comune coperto dal DBTR si scartano (dove c'è il DBTR, OSM non si mescola)
  async function edificiOsm(lon, lat) {
    const k = `${Math.round(lat / CELLA_OSM)}_${Math.round(lon / CELLA_OSM)}`;
    if (!stato.osm.celle.has(k)) {
      stato.osm.celle.set(k, (async () => {
        messaggio("messaggio", "Qui non c'è ancora il DBTR: chiedo gli edifici al server (sagome della Regione dove ci sono, altrimenti OpenStreetMap; può volerci qualche secondo)…");
        const r = await fetch(`/api/edifici/osm?lon=${lon.toFixed(6)}&lat=${lat.toFixed(6)}`);
        let d = null;
        try { d = await r.json(); } catch { d = null; }
        if (!r.ok || !d || !Array.isArray(d.features)) {
          const t = d && typeof d.detail === "string" ? d.detail : `il server ha risposto ${r.status}`;
          throw new Error(r.status === 404 && !(d && d.detail) ? "ripiego OpenStreetMap non disponibile su questo server." : t);
        }
        const fs = await fuoriDalDbtr(d.features.filter((f) => f && f.geometry && f.properties && f.properties.id !== undefined));
        // sagome regionali al volo (08/11/2026): licenza della sagoma dal server (IODL 2.0 per il Veneto, con l'altezza ODbL)
        fs.forEach((f) => { f.properties.licenza = f.properties.regione_sagoma && f.properties.licenza ? String(f.properties.licenza) : "ODbL 1.0";
          f.properties.edificio = String(f.properties.edificio || f.properties.id);
          f.properties.origine_altezza = origineAltezza(f.properties); });
        // altezze fisse vicino al DB topografico caricato nel browser: mediana dei suoi corpi entro 200 m (il server fa lo
        // stesso con gli archivi DBTR che ha, servizio/edifici_osm.py)
        if (stato.locale) altezzeDaVicini(fs, puntiDbtr(stato.locale.features), "del DB topografico del tuo file");
        stato.osm.info = { data: d.data || null, stimate: fs.filter((f) => /^(fissa|dbtr_vicini|osm_vicini)$/.test(f.properties.origine_altezza)).length, corpi: fs.length };
        if (d.sagome && d.sagome.attribuzione) stato.osm.sagome = { ...d.sagome };
        if (d.avviso_sagome) stato.osm.avvisoSagome = String(d.avviso_sagome).slice(0, 300);
        return fs;
      })());
    }
    try {
      const fs = await stato.osm.celle.get(k);
      stato.osm.errore = null;
      mostraOsm(fs);
      return fs;
    } catch (e) {
      stato.osm.celle.delete(k);                 // si riprova al prossimo punto
      stato.osm.errore = String((e && e.message) || e);
      return [];
    }
  }
  // altezze dei corpi OSM (07/11/2026 sera, decisione di Paolo; stessa regola di osm_campione.altezze_da_vicini): senza
  // height né building:levels, mediana dei corpi DBTR vicini (entro 200 m, almeno 3, altezze non stimate), altrimenti 9 m;
  // origine per corpo: osm_height, osm_piani, dbtr_vicini, fissa
  const ORIGINI_ALTEZZA = ["osm_height", "osm_piani", "dbtr_vicini", "osm_vicini", "fissa"];
  function origineAltezza(p) {
    if (ORIGINI_ALTEZZA.includes(p.origine_altezza)) return p.origine_altezza;
    const f = String(p.fonte_altezza || "");
    return f.startsWith("OSM height") ? "osm_height" : f.startsWith("OSM building:levels") ? "osm_piani" : "fissa";
  }
  const arrotonda2 = (x) => { const y = x * 2, r = Math.round(y); return (Math.abs(y % 1) === 0.5 ? (r % 2 ? r - 1 : r) : r) / 2; };   // come round() di Python
  function puntiDbtr(features) {
    const out = [];
    for (const f of features || []) {
      const p = f.properties || {}, g = +p.gronda;
      if (!Number.isFinite(g) || g < 2 || g > 80 || (p.h_dbtr_scartata !== undefined && p.h_dbtr_scartata !== null && p.h_dbtr_scartata !== "")
        || /stima/i.test(String(p.fonte_altezza || ""))) continue;
      const r = anelli(f.geometry)[0];
      if (r) out.push([r.reduce((s, q) => s + q[0], 0) / r.length, r.reduce((s, q) => s + q[1], 0) / r.length, g]);
    }
    return out;
  }
  function altezzeDaVicini(fs, vicini, nomeFonte = "DBTR", raggio = 200, minimo = 3) {
    if (!fs.length || !vicini.length) return 0;
    const n0 = Math.min(vicini.length, 50), lat0 = vicini.slice(0, 50).reduce((s, v) => s + v[1], 0) / n0;
    const kx = 111320 * Math.cos(lat0 * Math.PI / 180), ky = 110574, griglia = new Map();
    for (const [lo, la, g] of vicini) {
      const x = lo * kx, y = la * ky, k = `${Math.floor(x / raggio)}_${Math.floor(y / raggio)}`;
      if (!griglia.has(k)) griglia.set(k, []); griglia.get(k).push([x, y, g]);
    }
    let n = 0;
    for (const f of fs) {
      const p = f.properties;
      if (origineAltezza(p) !== "fissa") continue;
      const r = anelli(f.geometry)[0];
      if (!r) continue;
      const x = r.reduce((s, q) => s + q[0], 0) / r.length * kx, y = r.reduce((s, q) => s + q[1], 0) / r.length * ky;
      const i = Math.floor(x / raggio), j = Math.floor(y / raggio), hs = [];
      for (let di = -1; di <= 1; di++) for (let dj = -1; dj <= 1; dj++)
        for (const [vx, vy, g] of griglia.get(`${i + di}_${j + dj}`) || []) if ((vx - x) ** 2 + (vy - y) ** 2 <= raggio * raggio) hs.push(g);
      if (hs.length < minimo) continue;
      hs.sort((a, b) => a - b);
      const m = hs.length % 2 ? hs[(hs.length - 1) / 2] : (hs[hs.length / 2 - 1] + hs[hs.length / 2]) / 2, h = arrotonda2(m);
      Object.assign(p, { gronda: h, altezza: h, piani: Math.max(1, Math.round(h / 3)), qualita: "stima", origine_altezza: "dbtr_vicini",
        fonte_altezza: `stima: mediana dei corpi ${nomeFonte} vicini (${hs.length} entro ${raggio} m: ${String(h)} m)` });
      delete p.colmo;
      n++;
    }
    return n;
  }
  // conteggi per origine delle altezze dei corpi OSM; nota sotto la mappa, nell'immagine e nel report
  function contaOrigini(lista) {
    const n = { osm_height: 0, osm_piani: 0, dbtr_vicini: 0, osm_vicini: 0, fissa: 0, regionali: 0 };
    lista.forEach((p) => { n[origineAltezza(p)]++; if (p.regione_sagoma) n.regionali++; });
    return n;
  }
  // sagome regionali al volo (08/11/2026): «Sagome dalla Regione X (licenza), altezze da OpenStreetMap dove ci sono, altrimenti stimate»
  function testoSagomeRegionali() {
    const s = stato.osm && stato.osm.sagome;
    return s ? `Sagome dalla ${String(s.nome || s.regione).replace(/ – .*$/, "")} (${s.licenza}), altezze da OpenStreetMap dove ci sono, altrimenti stimate.` : "";
  }
  function testoAltezzeOsm(n, dove = "") {
    const tot = n.osm_height + n.osm_piani + n.dbtr_vicini + n.osm_vicini + n.fissa;
    if (!tot) return "";
    const parti = [`${n.osm_height + n.osm_piani} con l'altezza dal dato OSM (height o piani × 3 m${n.regionali ? ", dall'edificio OSM sovrapposto" : ""})`,
      `${n.dbtr_vicini} stimati dalla mediana dei corpi DBTR vicini (entro 200 m)`,
      ...(n.osm_vicini ? [`${n.osm_vicini} dalla mediana dei vicini con l'altezza OSM (entro 200 m)`] : []), `${n.fissa} a 9 m fissi (stima)`];
    const chi = n.regionali ? `Edifici fuori dal DBTR${dove}: ${tot.toLocaleString("it-IT")} (${n.regionali.toLocaleString("it-IT")} con la sagoma della Regione, `
      + `${(tot - n.regionali).toLocaleString("it-IT")} da OpenStreetMap)` : `Edifici OpenStreetMap${dove}: ${tot.toLocaleString("it-IT")}`;
    return `${n.regionali ? `${testoSagomeRegionali()} ` : ""}${chi}, di cui ${parti.join(", ")}. Le altezze stimate sono indicate come «stima» nella tabella dei corpi.`;
  }
  // corpi OSM della vista: in 3D l'edificio e i vicini, in 2D le sagome OSM ricevute che cadono nella mappa
  function altezzeOsmVista() {
    if (stato.in3d) return contaOrigini(stato.corpi.concat(stato.vicini).filter((c) => (archivioDi(c) || {}).osm));
    const m = stato.mappa, b = m && m.getBounds();
    return contaOrigini([...stato.osm.visti.values()].filter((f) => {
      if (!b) return true;
      const r = anelli(f.geometry)[0];
      return r && b.contains([r[0][0], r[0][1]]);
    }).map((f) => f.properties));
  }
  function notaAltezzeOsm() {
    if (!stato.osmAttivo) return;
    let p = $("nota-altezze-osm");
    if (!p) {
      const dopo = $("fonti-corpi") || $("comandi-edificio") || $("mappa3d");
      if (!dopo) return;
      p = h("p", "aiuto nota-altezze-osm"); p.id = "nota-altezze-osm"; p.setAttribute("aria-live", "polite"); p.hidden = true;
      dopo.after(p);
    }
    const t = testoAltezzeOsm(altezzeOsmVista(), stato.in3d ? " dell'edificio e dei vicini" : " nella vista");
    p.textContent = t; p.hidden = !t;
  }
  // corpi OSM fuori dai comuni (o dai riquadri) coperti dal DBTR
  async function fuoriDalDbtr(fs) {
    const arch = veri().filter((a) => !a.indice.sintetico && Array.isArray(a.indice.riquadro) && a.indice.riquadro.length === 4);
    if (!arch.length) return fs;
    const out = [];
    for (const f of fs) {
      const r0 = anelli(f.geometry)[0];
      if (!r0) continue;
      const lon = r0.reduce((x, q) => x + q[0], 0) / r0.length, lat = r0.reduce((x, q) => x + q[1], 0) / r0.length;
      const nei = arch.filter((a) => { const r = a.indice.riquadro; return lon >= r[0] && lon <= r[2] && lat >= r[1] && lat <= r[3]; });
      if (nei.some((a) => !a.istat)) continue;
      if (nei.length) {
        const c = await comuneNelPunto(lon, lat);
        if (c && nei.some((a) => a.istat === c.istat)) continue;
        // vicino al confine generalizzato: fuori se c'è un corpo DBTR entro 30 m (lo stesso edificio, già nel DBTR)
        let doppio = false;
        for (const a of nei) if (await vicinoAlDbtr(a, lon, lat, 30)) { doppio = true; break; }
        if (doppio) continue;
      }
      out.push(f);
    }
    return out;
  }
  // sagome OSM ricevute finora sulla mappa (sorgente GeoJSON dell'archivio virtuale)
  function mostraOsm(fs) {
    const k = stato.archivi.findIndex((a) => a.osm), m = stato.mappa;
    if (k < 0) return;
    fs.forEach((f) => { if (!stato.osm.visti.has(f.properties.id)) stato.osm.visti.set(f.properties.id, f); });
    while (stato.osm.visti.size > 6000) stato.osm.visti.delete(stato.osm.visti.keys().next().value);
    const src = m && m.getSource(stato.sorgentiCorpi[k]);
    if (src) src.setData({ type: "FeatureCollection", features: [...stato.osm.visti.values()] });
    const p = $("fonti-osm");
    if (p) p.hidden = !stato.osm.visti.size;
    const lo = $("legenda-osm"); if (lo) lo.hidden = !stato.osm.visti.size;
    notaAltezzeOsm();
  }
  // il corpo viene dal ripiego OSM? (per i messaggi)
  function avvisoOsm(k) {
    const a = stato.archivi[k];
    if (!a || !a.osm) return "";
    if (stato.osm.sagome) return ` Qui non c'è ancora il DBTR: ${testoSagomeRegionali()} Edifici OSM senza sagoma regionale: © OpenStreetMap contributors (ODbL 1.0).`;
    return (stato.osm.avvisoSagome ? ` ${stato.osm.avvisoSagome}` : "") + " Qui non c'è ancora il DBTR: si usa OpenStreetMap come ripiego (© OpenStreetMap contributors, ODbL 1.0), con qualità "
      + "inferiore e altezze in parte stimate (dove OSM non ha né altezza né piani: mediana dei corpi DBTR vicini, se ci sono, altrimenti 9 m).";
  }
  // la rotta del terreno risponde? (prima della mappa: se tutte le tessere danno 404 MapLibre non finisce mai di caricare,
  // per esempio prima del rebuild dell'api o con TERRENO_ATTIVO=false; allora mappa piatta come senza DTM)
  async function provaTerreno() {
    try {
      const ctl = new AbortController(), t = setTimeout(() => ctl.abort(), 4000);
      const r = await fetch("/api/terreno/fonti", { signal: ctl.signal });
      clearTimeout(t);
      if (!r.ok) return false;
      const j = await r.json();
      return !!(j && j.attivo);
    } catch { return false; }
  }
  // sorgente raster-dem del terreno: le tessere del server, o quelle dell'archivio se le ha ancora (terrenoProprio);
  // null se non c'è né l'una né l'altra (mappa piatta)
  function sorgenteTerreno(a) {
    if (terrenoProprio(a)) return { type: "raster-dem", url: `pmtiles://${new URL(a.base + "terreno.pmtiles", location.href).href}`, encoding: "terrarium", tileSize: 256 };
    if (!stato.terrenoServer) return null;
    // location.origin + percorso, non new URL(): codificherebbe le graffe di {z}/{x}/{y}
    return { type: "raster-dem", tiles: [location.origin + TESSERE_TERRENO], encoding: "terrarium", tileSize: 256,
      minzoom: 8, maxzoom: 15, attribution: ATTRIBUZIONE_TERRENO };
  }
  // terreno 3D dell'edificio scelto: dal server (un solo terreno per tutti gli archivi), salvo archivi con le loro tessere
  function terrenoDi(k) {
    const a = stato.archivi[k], m = stato.mappa;
    if (!a || !m || a.osm) return;
    const chiave = terrenoProprio(a) ? a.base : "server";
    if (stato.baseTerreno === chiave) return;
    const src = sorgenteTerreno(a);
    if (!src) return;
    try {
      ["terreno", "rilievo"].forEach((id) => {
        const s = m.getSource(id);
        if (!s) return;
        if (src.url && typeof s.setUrl === "function") s.setUrl(src.url);
        else if (src.tiles && typeof s.setTiles === "function") s.setTiles(src.tiles);
      });
      stato.baseTerreno = chiave;
    } catch { /* resta il terreno di prima */ }
  }
  // anelli di una sagoma (07/11/2026): il primo è l'esterno, gli altri i fori (cortili); solo il primo poligono
  function anelli(geom) {
    const g = geom && (geom.type === "MultiPolygon" ? geom.coordinates[0] : geom.coordinates);
    return Array.isArray(g) ? g.filter((r) => Array.isArray(r) && r.length >= 4) : [];
  }
  function aCorpo(f) {
    const p = f.properties, [esterno, ...fori] = anelli(f.geometry), ring = esterno.map(stato.proj.avanti);
    const buchi = fori.slice(0, 200).map((r) => r.map(stato.proj.avanti));
    return { id: String(p.id), edificio: String(p.edificio), ring, buchi, lonlat: f.geometry, gronda: +p.gronda, colmo: p.colmo ? +p.colmo : null,
      tetto: p.tetto || "piano", falde: +p.falde || 0, piani: p.piani ? +p.piani : null, quota: p.quota_terreno !== undefined ? +p.quota_terreno : 0,
      fonte_sagoma: p.fonte_sagoma || "", fonte_altezza: p.fonte_altezza || "", licenza: p.licenza || "", qualita: p.qualita || "",
      uso: p.uso || null, sintetico: !!p.sintetico, modificato: false, falde: null, lidar: null, archivio: +p.archivio || 0,
      foglio: p.foglio || null, numero: p.numero || null, nome: p.nome || null, destinazione: p.destinazione || null,
      origine_altezza: p.origine_altezza || null, tipo_edificio: p.tipo_edificio || null, regione_sagoma: p.regione_sagoma || null,
      quotaNota: p.quota_terreno !== undefined && p.quota_terreno !== null && Number.isFinite(+p.quota_terreno),
      h_scartata: Number.isFinite(+p.h_dbtr_scartata) && p.h_dbtr_scartata !== undefined && p.h_dbtr_scartata !== null ? +p.h_dbtr_scartata : null };
  }
  // fonte dell'altezza da mostrare (07/11/2026): l'altezza del DBTR non plausibile portata alla stima si dichiara
  function testoAltezza(c) {
    if (c.h_scartata !== null && c.h_scartata !== undefined && !c.modificato && !(c.lidar && c.lidar.stato === "ok"))
      return `altezza stimata (dato DBTR non plausibile: ${(+c.h_scartata).toLocaleString("it-IT", { maximumFractionDigits: 1 })} m)`;
    if (c.tettoStimato) return `${c.fonte_altezza}; ${c.falde && c.falde[0] ? c.falde[0].fonte : FONTE_STIMA_TETTO} (${c.tetto === "padiglione" ? "a padiglione" : c.tetto === "monofalda" ? "a una falda" : "a capanna"})`;
    if (c.fonteTetto === "piano" && !c.modificato && c.motivoPiano) return `${c.fonte_altezza}; tetto piano (${c.motivoPiano})`;
    return c.fonte_altezza;
  }
  // tetto a falde stimato dal colmo del DB topografico (07/11/2026 sera): dove non ci sono falde misurate e il colmo è più
  // alto della gronda, falde a capanna sul lato lungo o a padiglione (corpi quasi quadrati), dichiarate «stimate»
  const FONTE_STIMA_TETTO = "tetto stimato dal colmo DBTR";
  function stimaTetto(c, fonte = FONTE_STIMA_TETTO, tipo = null) {
    c.tettoStimato = false;
    if (c.falde && c.falde.length) return c;
    const r = E.faldeStimate ? E.faldeStimate(c, tipo) : null;
    if (!r) return c;
    c.falde = r.falde.map((f) => ({ ...f, fonte })); c.tetto = r.tipo; c.tettoStimato = true;
    return c;
  }
  // ------------------------------------------------------------------ forma dei tetti: tre fonti (08/11/2026, decisione di Paolo)
  // 1. falde misurate dal LiDAR (pipeline notturna, lidar/indice.json dell'archivio); 2. tetto stimato dal colmo DBTR
  // (stimaTetto); 3. tetto ipotizzato a falde, 22° in pianura e 32° in montagna (E.tettoIpotizzato: stessa forma, colmo =
  // gronda + semiluce × tan(inclinazione)), o piano dove la regola dice piano (capannoni, commerciali, corpi molto grandi,
  // bassi, con cortile o poco rettangolari). In Modelli 3D le fonti valgono in cascata per ogni corpo; nelle pagine
  // Edificio e Fotovoltaico l'utente sceglie la forma con «Forma dei tetti» (#forma-tetti): «lidar» e «colmo» partono da
  // quella fonte e scendono la cascata dove manca, «ipotesi» ipotizza tutti i corpi (salvo i piani), «piani» li fa tutti
  // piani. Il modello dell'utente (DXF/IFC) e i corpi corretti a mano non cambiano: hanno la precedenza.
  const SCELTE_TETTO = { auto: ["lidar", "colmo", "ipotesi"], lidar: ["lidar", "colmo", "ipotesi"], colmo: ["colmo", "ipotesi"], ipotesi: ["ipotesi"], piani: [] };
  const NOMI_SCELTA_TETTO = { auto: "in cascata: LiDAR, poi colmo DBTR, poi ipotesi automatica", lidar: "Misurata (LiDAR) dove c'è",
    colmo: "Stimata dal colmo DBTR dove c'è", ipotesi: "Ipotesi automatica (22°/32°)", piani: "Tutti piani" };
  const SELETTORE_TETTI = () => (VISTA !== "modelli" ? $("forma-tetti") : null);
  stato.formaTetti = "auto";
  // un corpo con le sue falde: il modello dell'utente resta com'è; per gli altri si ricordano i valori del DB topografico
  // (c.base) e il record LiDAR, poi applicaTetto sceglie la fonte
  function conFalde(c, p) {
    c.base = { gronda: c.gronda, colmo: c.colmo, tetto: c.tetto, fonte_altezza: c.fonte_altezza, qualita: c.qualita };
    if (c.edificio === "MODELLO") {                                  // modello dell'utente (importa-modello)
      c.tettoFisso = true; c.fonteTetto = "modello";
      if (Array.isArray(p.falde) && p.falde.length) c.falde = faldeLocali(p.falde, p.fonte_altezza || "modello dell'utente");
      else stimaTetto(c, "tetto stimato dal colmo del modello");
      return c;
    }
    c.recLidar = stato.falde.get(c.id) || null;
    return applicaTetto(c);
  }
  // quota per la regola pianura/montagna: terreno sotto il corpo (DTM, nei corpi DBTR) o, senza, altitudine del comune (DPR 412/93)
  function quotaPerTetto(c) {
    if (c.quotaNota) return { quota: c.quota, testo: `quota del terreno ${fmt(c.quota)} m` };
    const riga = stato.dpr && stato.comune ? stato.dpr.comuni[stato.comune.istat] : null;
    if (riga && Number.isFinite(+riga[2])) return { quota: +riga[2], testo: `altitudine del comune ${fmt(riga[2])} m, DPR 412/93` };
    return { quota: null, testo: "quota non nota" };
  }
  function ipotesiDi(c) {
    const q = quotaPerTetto(c);
    return { ...E.tettoIpotizzato(c, { quota: q.quota, istat: stato.comune ? stato.comune.istat : null }), testoQuota: q.testo };
  }
  function applicaTetto(c, scelta = stato.formaTetti || "auto") {
    if (c.tettoFisso || c.modificato) return c;                      // modello dell'utente e correzioni a mano: precedenza
    const b = c.base || {};
    Object.assign(c, { gronda: b.gronda, colmo: b.colmo, tetto: b.tetto, fonte_altezza: b.fonte_altezza, qualita: b.qualita,
      falde: null, lidar: null, tettoStimato: false, ipotesi: null, motivoPiano: null, fonteTetto: "piano" });
    const rec = c.recLidar;
    if (rec && rec.stato !== "ok") conLidar(c, rec);                 // solo le note (resta l'altezza del DBTR)
    for (const f of SCELTE_TETTO[scelta] || SCELTE_TETTO.auto) {
      if (f === "lidar" && rec && rec.stato === "ok") { conLidar(c, rec); c.fonteTetto = "lidar"; return c; }
      if (f === "colmo") { stimaTetto(c); if (c.tettoStimato) { c.fonteTetto = "colmo"; return c; } }
      if (f === "ipotesi") {
        const r = ipotesiDi(c);
        if (r.piano) { c.motivoPiano = r.motivo; break; }
        const fonte = `tetto ipotizzato a ${r.inclinazione}° (${r.montagna ? "montagna" : "pianura"}: ${r.testoQuota})`;
        Object.assign(c, { colmo: r.colmo, tetto: r.tipo, falde: r.falde.map((x) => ({ ...x, fonte })), tettoStimato: true, fonteTetto: "ipotesi",
          ipotesi: { inclinazione: r.inclinazione, montagna: r.montagna, quota: r.quota, testo: r.testoQuota } });
        return c;
      }
    }
    if (scelta === "piani") { c.colmo = null; c.tetto = "piano"; c.motivoPiano = "scelta «Tutti piani»"; }
    return c;
  }
  function testoSceltaTetti() {
    return `Forma dei tetti: ${VISTA !== "modelli" && SELETTORE_TETTI() ? `«${NOMI_SCELTA_TETTO[stato.formaTetti] || NOMI_SCELTA_TETTO.auto}»` : NOMI_SCELTA_TETTO.auto}.`;
  }
  function applicaTetti() { [...stato.corpi, ...stato.vicini].forEach((c) => applicaTetto(c)); }
  // fonte del tetto di ogni corpo: lidar, colmo, ipotesi, piano, modello, utente
  function fonteTettoDi(c) { return c.modificato ? "utente" : c.fonteTetto || (c.falde && c.falde.length ? "colmo" : "piano"); }
  function contaTetti(corpi = stato.corpi) {
    const n = { lidar: 0, colmo: 0, ipotesi: 0, piano: 0, modello: 0, utente: 0, pianura: 0, montagna: 0 };
    corpi.forEach((c) => { const f = fonteTettoDi(c); n[f] = (n[f] || 0) + 1; if (f === "ipotesi" && c.ipotesi) n[c.ipotesi.montagna ? "montagna" : "pianura"]++; });
    return n;
  }
  // «Tetti: N misurati dal LiDAR, M stimati dal colmo DBTR, K ipotizzati (22° pianura / 32° montagna), P piani»
  function testoTetti(corpi = stato.corpi) {
    if (!corpi.length) return "";
    const n = contaTetti(corpi), pl = (k, s, p) => `${k} ${k === 1 ? s : p}`;
    const qui = [n.pianura ? `${n.pianura} a 22°` : "", n.montagna ? `${n.montagna} a 32°` : ""].filter(Boolean).join(", ");
    const parti = [`${pl(n.lidar, "misurato", "misurati")} dal LiDAR`, `${pl(n.colmo, "stimato", "stimati")} dal colmo DBTR`,
      `${pl(n.ipotesi, "ipotizzato", "ipotizzati")} (22° pianura / 32° montagna${qui ? `: ${qui}` : ""})`, pl(n.piano, "piano", "piani")];
    if (n.modello) parti.push(`${n.modello} dal modello dell'utente`);
    if (n.utente) parti.push(`${pl(n.utente, "corretto", "corretti")} a mano`);
    const scelta = VISTA !== "modelli" && SELETTORE_TETTI() ? ` Forma dei tetti scelta: «${NOMI_SCELTA_TETTO[stato.formaTetti] || NOMI_SCELTA_TETTO.auto}».` : "";
    return `Tetti: ${parti.join(", ")}.${scelta}`;
  }
  // opzioni del selettore per l'edificio scelto: disponibili o spente con il motivo; predefinita la più affidabile
  function opzioniTetti() {
    const corpi = stato.corpi.filter((c) => !c.tettoFisso);
    const out = { lidar: null, colmo: null, ipotesi: null, piani: null };
    if (!corpi.length) { const m = "tetti dal modello dell'utente"; return { lidar: m, colmo: m, ipotesi: m, piani: m }; }
    if (!corpi.some((c) => c.recLidar && c.recLidar.stato === "ok"))
      out.lidar = stato.lidar ? "la pipeline LiDAR non ha ancora misurato le falde di questo edificio" : "nessun rilievo LiDAR elaborato per questo archivio";
    if (!corpi.some((c) => E.faldeStimate({ ring: c.ring, buchi: c.buchi, gronda: c.base.gronda, colmo: c.base.colmo })))
      out.colmo = corpi.some((c) => c.base.colmo > c.base.gronda) ? "forma dei corpi non adatta alla stima dal colmo" : "il DB topografico non dà il colmo di questi corpi";
    const ip = corpi.map((c) => ipotesiDi({ ...c, gronda: c.base.gronda }));
    if (ip.every((r) => r.piano)) out.ipotesi = `corpi plausibilmente piani (${ip[0].motivo})`;
    return out;
  }
  function preparaSelettoreTetti(nuovo = false) {
    const sel = SELETTORE_TETTI();
    if (!sel) return;
    const off = opzioniTetti(), nota = $("motivi-forma-tetti");
    [...sel.options].forEach((o) => {
      o.textContent = NOMI_SCELTA_TETTO[o.value] + (off[o.value] ? ` – non disponibile: ${off[o.value]}` : "");
      o.disabled = !!off[o.value]; o.title = off[o.value] || "";
    });
    if (nuovo || off[stato.formaTetti] || stato.formaTetti === "auto") stato.formaTetti = ["lidar", "colmo", "ipotesi", "piani"].find((k) => !off[k]) || "piani";
    sel.value = stato.formaTetti; sel.disabled = stato.corpi.every((c) => c.tettoFisso);
    if (nota) {
      const spente = Object.entries(off).filter(([, m]) => m).map(([k, m]) => `«${NOMI_SCELTA_TETTO[k]}»: ${m}`);
      nota.textContent = spente.length ? `Non disponibili per questo edificio: ${spente.join("; ")}.` : "";
    }
  }
  // dopo un cambio di forma: aree FV sulle falde nuove (salvo inclinazione e orientamento corretti a mano), ombre, sole e
  // producibilità ricalcolati se erano già stati calcolati
  function cambiaFormaTetti(scelta) {
    stato.formaTetti = scelta;
    applicaTetti();
    stato.originali = stato.corpi.map((c) => ({ ...c, ring: c.ring.map((p) => [...p]), buchi: (c.buchi || []).map((b) => b.map((p) => [...p])) }));
    for (const a of stato.aree) {
      if (a.manuale) continue;
      const c = stato.corpi.find((x) => x.id === a.corpo);
      if (!c) continue;
      const f = (c.falde || []).find((x) => E.dentro(E.centroide(a.ring), x.ring) && x.pendenza >= 5);
      Object.assign(a, f ? { falda: f.id, inclinazione: Math.round(f.pendenza), orientamento: Math.round(f.orientamento), montaggio: "aderente",
        quota: Number.isFinite(f.alto) && Number.isFinite(f.basso) ? (f.alto + f.basso) / 2 : c.gronda, fonte: f.fonte }
        : { falda: null, inclinazione: 10, orientamento: 180, montaggio: "telai", quota: c.gronda, fonte: null });
    }
    const fv = !!stato.fv, facc = !!stato.facciate;
    stato.fv = null; stato.pvgis = null; stato.facciate = null; mostraFacciate();
    if ($("pvgis")) $("pvgis").innerHTML = "";
    if ($("calcola-pvgis")) $("calcola-pvgis").disabled = true;
    aggiorna(); tabellaFv(); fontiCorpi();
    if (stato.in3d && stato.mappa) ridisegna();
    if (fv && stato.aree.length) $("calcola-fv").click();
    if (facc) $("calcola-facciate").click();
  }
  if (SELETTORE_TETTI()) SELETTORE_TETTI().addEventListener("change", (e) => { if (stato.corpi.length) cambiaFormaTetti(e.target.value); });
  function conLidar(c, r) {
    c.lidar = { stato: r.stato, qualita: r.qualita || null, rmse: r.rmse, copertura: r.copertura, fonte: r.descrizione_fonte || r.fonte,
      note: Array.isArray(r.note) ? r.note.slice(0, 5).map(String) : [], sintetico: !!r.sintetico, versione: r.versione };
    if (r.stato !== "ok") return c;
    const ok = (v) => Number.isFinite(+v) && +v > 0 && +v < 400;
    if (ok(r.gronda)) c.gronda = Math.round(+r.gronda * 10) / 10;
    c.colmo = ok(r.colmo) && +r.colmo > c.gronda + 0.2 ? Math.round(+r.colmo * 10) / 10 : null;
    c.tetto = ["piano", "monofalda", "capanna", "padiglione"].includes(r.tetto) ? r.tetto : "piano";
    c.falde = faldeLocali(r.falde, `LiDAR – ${c.lidar.fonte}`);
    c.fonte_altezza = `LiDAR – ${c.lidar.fonte}${r.qualita ? ` (qualità ${r.qualita})` : ""}`;
    c.qualita = r.qualita || c.qualita;
    return c;
  }

  // ------------------------------------------------------------------ rilievo: ombreggiatura, esagerazione, fonte
  function paintRilievo(conFoto) {
    const scuro = !document.documentElement.matches('[data-theme="light"]') && (document.documentElement.matches('[data-theme="dark"]')
      || (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches));
    return { "hillshade-exaggeration": conFoto ? 0.3 : 0.75, "hillshade-shadow-color": scuro ? "#000000" : "#3a3a3a",
      "hillshade-highlight-color": scuro ? "#d9d4c7" : "#ffffff", "hillshade-accent-color": scuro ? "#1b1b1b" : "#5a5a5a",
      "hillshade-illumination-direction": 315 };
  }
  function coloriRilievo() {
    const m = stato.mappa;
    if (!m || !m.getLayer("rilievo")) return;
    const p = paintRilievo(ortoVisibile && ortoVisibile() && !!stato.ortofoto);
    Object.entries(p).forEach(([k, v]) => { try { m.setPaintProperty("rilievo", k, v); } catch { /* proprietà non supportata */ } });
  }
  // esagerazione verticale del rilievo nella vista 3D: ×1 (predefinito), ×1,5, ×2
  function terreno3d() {
    const m = stato.mappa;
    if (!m || !stato.in3d) return;
    const osm = stato.corpi.some((c) => (archivioDi(c) || {}).osm && !c.quotaNota);   // sagome regionali con la quota dal DTM: terreno vero
    try { if (osm || !m.getSource("terreno")) m.setTerrain(null); else m.setTerrain({ source: "terreno", exaggeration: stato.esagera || 1 }); } catch { /* piatta */ }
    quotaCamera();
  }
  // (07/11/2026 sera, «diventa nera» a Bagno di Romagna) la camera guarda il centro della mappa alla quota del centro: con
  // il terreno appena acceso MapLibre la teneva a 0 m finché le tessere non arrivavano, e in collina (550–780 m) la camera
  // finiva dentro il versante (tutto nero, nessuna tessera chiesta). Si dà subito la quota del terreno sotto l'edificio
  // (dal DTM, già nei corpi), moltiplicata per l'esagerazione; poi MapLibre la affina con le tessere
  function quotaDelCentro() {
    const m = stato.mappa;
    if (!m || !m.getTerrain || !m.getTerrain() || !stato.corpi.length) return 0;
    return (Number.isFinite(stato.q0) ? stato.q0 : 0) * (stato.esagera || 1);
  }
  function quotaCamera() {
    const m = stato.mappa;
    if (!m || typeof m.setCenterElevation !== "function") return;
    try { m.setCenterElevation(stato.in3d ? quotaDelCentro() : 0); } catch { /* versione senza quota del centro */ }
  }
  function esagera(x) {
    stato.esagera = x;
    if (stato.barra3d) stato.barra3d.querySelectorAll("[data-esagera]").forEach((b) => b.setAttribute("aria-pressed", String(+b.dataset.esagera === x)));
    terreno3d();
    legendaTerreno();
  }
  // fonte delle tessere del terreno al centro della vista (intestazione X-Terreno-Fonte della rotta /api/terreno)
  const NOMI_TERRENO = { dtm: "DTM 5 m Regione Emilia-Romagna (CC BY 4.0)", "dtm+copernicus": "DTM 5 m Regione Emilia-Romagna e Copernicus DEM GLO-90",
    copernicus: "Copernicus DEM GLO-90 (© DLR e Airbus)", piatta: "piatto (nessun modello del terreno disponibile qui)" };
  async function fonteTerreno() {
    const m = stato.mappa;
    if (!m || !stato.terrenoServer || !m.getSource("terreno")) { stato.fonteTerreno = m && m.getSource("terreno") ? null : "piatta"; legendaTerreno(); return; }
    const c = m.getCenter(), z = Math.min(15, Math.max(8, Math.floor(m.getZoom()) - 1)), n = 2 ** z;
    const x = Math.floor((c.lng + 180) / 360 * n), y = Math.floor((1 - Math.asinh(Math.tan(c.lat * Math.PI / 180)) / Math.PI) / 2 * n);
    try {
      const r = await fetch(TESSERE_TERRENO.replace("{z}", z).replace("{x}", x).replace("{y}", y));
      stato.fonteTerreno = r.ok ? (r.headers.get("X-Terreno-Fonte") || null) : "piatta";
      stato.nomeTerreno = r.ok ? (r.headers.get("X-Terreno-Nome") || null) : null;     // 08/11/2026: più DTM regionali
    } catch { stato.fonteTerreno = null; stato.nomeTerreno = null; }
    legendaTerreno();
  }
  function legendaTerreno() {
    const l = $("legenda-3d");
    if (!l) return;
    let el = $("legenda-terreno");
    if (!el) { el = h("span"); el.id = "legenda-terreno"; l.appendChild(el); }
    const osm = stato.corpi.some((c) => (archivioDi(c) || {}).osm && !c.quotaNota);   // sagome regionali con la quota dal DTM: terreno vero
    const dtm = /^dtm/.test(stato.fonteTerreno || "") && stato.nomeTerreno
      ? `${stato.nomeTerreno}${/copernicus/.test(stato.fonteTerreno) ? " e Copernicus DEM GLO-90" : ""}` : null;
    const f = osm ? "piatto (edifici OpenStreetMap: nessuna quota del terreno)" : dtm || NOMI_TERRENO[stato.fonteTerreno] || (stato.fonteTerreno ? stato.fonteTerreno : "dal server");
    el.textContent = `Terreno: ${f}${stato.esagera && stato.esagera !== 1 ? `, rilievo esagerato ×${String(stato.esagera).replace(".", ",")}` : ""}`;
    el.hidden = !stato.in3d;
  }

  // ------------------------------------------------------------------ mappa
  // punto di apertura (08/11/2026, decisione di Paolo): Cesena, ospedale Bufalini, se l'indirizzo della pagina non porta
  // un punto, una sede, un edificio, un modello, un file o la demo e la regione scelta è l'Emilia-Romagna; null altrimenti
  function partenza() {
    const C0 = window.EUGENIO_CERCA;
    if (!DUE_TEMPI || !C0 || !C0.PARTENZA || !C0.partenzaLibera() || stato.locale || (stato.indice && stato.indice.sintetico)) return null;
    return C0.PARTENZA;
  }
  async function creaMappa() {
    const ml = window.maplibregl;
    if (!ml) throw new Error("libreria della mappa non caricata");
    const proto = new window.pmtiles.Protocol();
    ml.addProtocol("pmtiles", proto.tile);
    const abs = (p) => new URL(p, location.href).href;
    // (08/11/2026) prima apertura senza indicazioni nell'indirizzo: Cesena, ospedale Bufalini (cerca_luogo.js, PARTENZA)
    const P = partenza();
    const [lon, lat] = P ? [P.lon, P.lat] : stato.indice ? stato.indice.centro : [12.5683, 44.0594];
    const vuota = () => ({ type: "geojson", data: { type: "FeatureCollection", features: [] } });
    const sources = { ombre: vuota(), scelto: vuota(), fv: vuota(), linea: vuota(), facciate: vuota(), falde: vuota(), alberi: vuota(), cercato: vuota() };
    const archivi = stato.archivi.length ? stato.archivi : stato.base ? [{ base: stato.base, indice: stato.indice }] : [];
    {
      // terreno: dal server (se la rotta risponde), o dalle tessere dell'archivio di partenza se le ha
      stato.terrenoServer = await provaTerreno();
      const a0 = stato.base ? { base: stato.base, indice: stato.indice || {} } : null, t0 = sorgenteTerreno(a0);
      if (t0) {
        sources.terreno = t0;
        sources.rilievo = sorgenteTerreno(a0);
        stato.baseTerreno = terrenoProprio(a0) ? a0.base : "server";
      }
    }
    // un sorgente vettoriale per archivio: «corpi» il primo (il più affidabile), «corpi_1», «corpi_2»… gli altri
    // (il ripiego OSM, senza file statici, è una sorgente GeoJSON riempita da edificiOsm)
    stato.sorgentiCorpi = archivi.map((a, k) => {
      const id = k ? `corpi_${k}` : "corpi";
      sources[id] = a.osm ? { type: "geojson", data: { type: "FeatureCollection", features: [] }, attribution: ATTRIBUZIONE_OSM }
        : a.locale ? { type: "geojson", data: { type: "FeatureCollection", features: a.features }, attribution: a.indice.attribuzione }
        : { type: "vector", url: `pmtiles://${abs(a.base + "corpi.pmtiles")}`, attribution: a.indice.attribuzione || "" };
      return id;
    });
    const strato = (k) => (archivi[k].osm || archivi[k].locale ? {} : { "source-layer": "corpi" });
    const layers = [{ id: "sfondo", type: "background", paint: { "background-color": colore("--carta") } }];
    // ombreggiatura del rilievo (07/11/2026 sera, prova a Bagno di Romagna: «non sembra 3D»): nella vista 3D sempre, più
    // marcata senza ortofoto; colori dal tema (ombre scure, luci chiare), sopra il fondo e sotto ortofoto e strati
    if (sources.rilievo) layers.push({ id: "rilievo", type: "hillshade", source: "rilievo", paint: paintRilievo(false) });
    layers.push({ id: "ombre", type: "fill", source: "ombre", paint: { "fill-color": "#000", "fill-opacity": 0.32 } });
    // colori (07/11/2026 sera): edifici del DB topografico come prima, quelli di OpenStreetMap (ripiego) in marrone
    const coloreDi = (k) => (archivi[k].osm ? COLORE_OSM : coloreEdifici());
    stato.sorgentiCorpi.forEach((id, k) => layers.push({ id, type: "fill-extrusion", source: id, ...strato(k),
      paint: { "fill-extrusion-color": coloreDi(k), "fill-extrusion-height": ["+", ["get", "altezza"], 0], "fill-extrusion-base": 0, "fill-extrusion-opacity": 0.85 } }));
    layers.push(
      { id: "scelto", type: "fill-extrusion", source: "scelto",
        paint: { "fill-extrusion-color": colore("--primario"), "fill-extrusion-height": ["get", "altezza"], "fill-extrusion-base": 0, "fill-extrusion-opacity": 0.95 } },
      // falde inclinate (LiDAR o modello) a gradini: dal giallo-arancio (verso sud) al blu (verso nord)
      { id: "falde", type: "fill-extrusion", source: "falde",
        paint: { "fill-extrusion-color": ["interpolate", ["linear"], ["get", "t"], 0, "#f4a261", 0.5, "#9c89b8", 1, "#457b9d"],
          "fill-extrusion-height": ["get", "z"], "fill-extrusion-base": 0, "fill-extrusion-opacity": 0.95 } },
      { id: "fv", type: "fill-extrusion", source: "fv",
        paint: { "fill-extrusion-color": "#1f4fa3", "fill-extrusion-height": ["+", ["get", "quota"], 0.3], "fill-extrusion-base": ["get", "quota"], "fill-extrusion-opacity": 0.95 } },
      { id: "facciate", type: "fill-extrusion", source: "facciate",
        paint: { "fill-extrusion-color": ["interpolate", ["linear"], ["get", "t"], 0, "#ffffcc", 0.5, "#41b6c4", 1, "#253494"],
          "fill-extrusion-height": ["get", "z1"], "fill-extrusion-base": ["get", "z0"], "fill-extrusion-opacity": 0.95 } },
      // alberi (chiome dal LiDAR: DSM − DTM, celle di 2 m): dal 09/11/2026 ottagoni un po' più larghi della cella, così le
      // celle vicine si fondono in una chioma (niente «cubetti»), verde più chiaro per le chiome più alte; spenti in partenza
      { id: "alberi", type: "fill-extrusion", source: "alberi",
        paint: { "fill-extrusion-color": ["interpolate", ["linear"], ["get", "h"], 3, "#3f6f2f", 12, "#5f9a45", 25, "#86b860"],
          "fill-extrusion-height": ["get", "h"], "fill-extrusion-base": ["*", ["get", "h"], 0.4], "fill-extrusion-opacity": 0.82 } },
      { id: "linea", type: "line", source: "linea", paint: { "line-color": colore("--segno"), "line-width": 3 } });
    // mappa 2D (Modelli 3D in due tempi): sagome piatte, sagoma scelta in evidenza, punto cercato
    stato.strati2d = [];
    if (DUE_TEMPI) {
      stato.sorgentiCorpi.forEach((id, k) => {
        // sagome OSM (ripiego) tratteggiate: si distinguono da quelle del DBTR
        layers.push({ id: `${id}-2d`, type: "fill", source: id, ...strato(k), minzoom: 13,
          paint: { "fill-color": coloreDi(k), "fill-opacity": archivi[k].osm ? 0.35 : 0.3 } });
        layers.push({ id: `${id}-2d-linea`, type: "line", source: id, ...strato(k), minzoom: 13,
          paint: { "line-color": colore("--inchiostro"), "line-width": ["interpolate", ["linear"], ["zoom"], 14, 0.6, 19, 1.6], "line-opacity": 0.85,
            ...(archivi[k].osm ? { "line-dasharray": [2, 1] } : {}) } });
        layers.push({ id: `${id}-2d-scelto`, type: "fill", source: id, ...strato(k), filter: ["==", ["get", "edificio"], ""],
          paint: { "fill-color": colore("--primario"), "fill-opacity": 0.75 } });
        layers.push({ id: `${id}-2d-bordo`, type: "line", source: id, ...strato(k), filter: ["==", ["get", "edificio"], ""],
          paint: { "line-color": colore("--inchiostro"), "line-width": 2.5 } });
        stato.strati2d.push(`${id}-2d`);
      });
      // zone coperte dagli archivi veri: riquadro tratteggiato, discreto (07/11/2026)
      const zone = archivi.filter((a) => !a.indice.sintetico && Array.isArray(a.indice.riquadro) && a.indice.riquadro.length === 4)
        .map((a) => { const [x0, y0, x1, y1] = a.indice.riquadro.map(Number);
          return { type: "Feature", properties: { nome: a.indice.nome || "" }, geometry: { type: "LineString", coordinates: [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]] } }; });
      sources.zone = { type: "geojson", data: { type: "FeatureCollection", features: zone } };
      layers.push({ id: "zone-coperte", type: "line", source: "zone",
        paint: { "line-color": colore("--inchiostro"), "line-width": 1.2, "line-opacity": 0.55, "line-dasharray": [3, 3] } });
      layers.push({ id: "cercato", type: "circle", source: "cercato",
        paint: { "circle-radius": 7, "circle-color": colore("--primario"), "circle-stroke-color": "#fff", "circle-stroke-width": 2 } });
    }
    const m = new ml.Map({
      container: "mappa3d", center: [lon, lat], zoom: P ? P.zoom : DUE_TEMPI ? (stato.base ? 16 : 7) : 17.2, pitch: DUE_TEMPI ? 0 : 55,
      bearing: DUE_TEMPI ? 0 : -20, maxPitch: 80, maxZoom: 21, attributionControl: false,
      // per copiare la vista nel report e nell'immagine scaricata (con l'ortofoto)
      canvasContextAttributes: { preserveDrawingBuffer: true },
      style: { version: 8, sources, layers },
    });
    m.addControl(new ml.NavigationControl({ visualizePitch: true, showCompass: !DUE_TEMPI }), "top-right");
    m.addControl(new ml.AttributionControl({ compact: true, customAttribution: "MapLibre" }), "bottom-right");
    if (DUE_TEMPI) m.addControl(new ml.ScaleControl({ unit: "metric" }), "bottom-left");
    if (window.EUGENIO_LIMITI) window.EUGENIO_LIMITI.collega(m);      // 429 delle fonti: pausa, nota e niente righe rosse (09/11/2026)
    await new Promise((ok) => m.on("load", ok));
    if (DUE_TEMPI) m.getContainer().querySelectorAll(".maplibregl-compact-show").forEach((x) => x.classList.remove("maplibregl-compact-show"));
    if (DUE_TEMPI) zoneComuni(m, archivi);
    if (!DUE_TEMPI) { try { if (m.getSource("terreno")) m.setTerrain({ source: "terreno", exaggeration: 1 }); } catch { /* terreno non disponibile: mappa piatta */ } }
    m.on("click", (e) => clic(e));
    m.on("moveend", () => { if (!stato.in3d) notaAltezzeOsm(); else if (DUE_TEMPI) lontanoDal3d(); });
    m.on("mousemove", (e) => {
      if (stato.trascino) return;
      if (DUE_TEMPI && !stato.in3d && m.getLayer("cercato") && m.queryRenderedFeatures(e.point, { layers: ["cercato"] }).length) {
        m.getCanvas().style.cursor = "move"; return;
      }
      const ids = (stato.in3d ? [...stato.sorgentiCorpi, "scelto"] : stato.strati2d).filter((id) => m.getLayer(id));
      const f = ids.length ? m.queryRenderedFeatures(e.point, { layers: ids }) : [];
      m.getCanvas().style.cursor = stato.modo ? "crosshair" : f.length ? "pointer" : "";
    });
    document.addEventListener("eugenio:aspetto", () => {
      m.setPaintProperty("sfondo", "background-color", colore("--carta"));
      stato.sorgentiCorpi.forEach((id, k) => {
        const col = (stato.archivi[k] || {}).osm ? COLORE_OSM : coloreEdifici();
        m.setPaintProperty(id, "fill-extrusion-color", col);
        if (m.getLayer(`${id}-2d`)) { m.setPaintProperty(`${id}-2d`, "fill-color", col); m.setPaintProperty(`${id}-2d-scelto`, "fill-color", colore("--primario")); }
      });
      coloriRilievo();
      m.setPaintProperty("scelto", "fill-extrusion-color", colore("--primario"));
      m.setPaintProperty("linea", "line-color", colore("--segno"));
    });
    document.addEventListener("eugenio:ridimensiona", () => m.resize());
    if (DUE_TEMPI) {
      m.dragRotate.disable(); m.touchPitch.disable(); m.touchZoomRotate.disableRotation(); m.keyboard.disable();
      vedi(m, strati3d(), false);
      if (C) {
        try {
          stato.confini = await C.aggiungi(m, {
            // da zoom 15 il clic sposta il punto (o sceglie l'edificio): regioni e comuni si scelgono da più lontano
            attivo: (ev) => !stato.in3d && !stato.modo && m.getZoom() < 15 && !(stato.strati2d.length && m.queryRenderedFeatures(ev.point, { layers: stato.strati2d.filter((id) => m.getLayer(id)) }).length),
            // (09/11/2026, punto J delle prove di Paolo: «cliccando la mappa impazzisce» e tornava al comune intero) un clic
            // sulla mappa non sposta MAI la vista: regione e comune si evidenziano soltanto; ci si sposta con la piccola mappa,
            // la ricerca, la rotella e il trascinamento
            suRegione: (cod) => { if (stato.regione === cod) togliRegione(false); else vaiRegione(cod, false); },
            suComune: async (c) => {
              if (!c) { messaggio("messaggio-cerca", ""); return; }
              messaggio("messaggio-cerca", `Comune di ${c.nome}${c.prov ? ` (${c.prov})` : ""}: avvicinati con la rotella (o cerca l'indirizzo) e fai clic su un edificio (secondo clic sul comune: lo togli).`);
            },
          });
        } catch { /* confini non disponibili */ }
      }
      comandi3d(m);
      trascinaPunto(m);
      m.getContainer().addEventListener("keydown", tastiera3d);
      m.on("dblclick", (e) => { if (stato.in3d) { e.preventDefault(); vistaNominata("3d"); } });
    }
    return m;
  }

  // zone coperte (07/11/2026): per gli archivi di un comune intero il confine ISTAT del comune al posto del riquadro
  async function zoneComuni(m, archivi) {
    if (!C || typeof C.geometriaComune !== "function" || !m.getSource("zone")) return;
    const feats = [];
    for (const a of archivi) {
      if (a.osm || a.indice.sintetico || !Array.isArray(a.indice.riquadro) || a.indice.riquadro.length !== 4) continue;
      const [x0, y0, x1, y1] = a.indice.riquadro.map(Number);
      const g = a.istat ? await C.geometriaComune(a.istat, (x0 + x1) / 2, (y0 + y1) / 2) : null;
      const linee = g ? (g.type === "MultiPolygon" ? g.coordinates : [g.coordinates]).flat() : [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]];
      feats.push({ type: "Feature", properties: { nome: a.indice.nome || "" }, geometry: { type: "MultiLineString", coordinates: linee } });
    }
    try { m.getSource("zone").setData({ type: "FeatureCollection", features: feats }); } catch { /* restano i riquadri */ }
  }

  // ------------------------------------------------------------------ Modelli 3D in due tempi (05/11/2026)
  function vedi(m, ids, si) { ids.forEach((id) => { if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", si ? "visible" : "none"); }); }
  const strati3d = () => [...(stato.sorgentiCorpi || []), "rilievo", "ombre", "scelto", "falde", "fv", "facciate", "alberi", "linea"];
  const strati2dTutti = () => (stato.sorgentiCorpi || []).flatMap((id) => [`${id}-2d`, `${id}-2d-linea`, `${id}-2d-scelto`, `${id}-2d-bordo`]).concat(["zone-coperte", "cercato"]);
  function evidenzia2d(edificio) {
    const m = stato.mappa;
    (stato.sorgentiCorpi || []).forEach((id) => ["2d-scelto", "2d-bordo"].forEach((suf) => {
      if (m.getLayer(`${id}-${suf}`)) m.setFilter(`${id}-${suf}`, ["==", ["get", "edificio"], edificio || ""]);
    }));
  }
  // clic sulla mappa 2D: sceglie l'edificio (o lo toglie se è già quello scelto) e ci porta il punto; da zoom 15 un clic
  // fuori dagli edifici sposta solo il punto. false se il clic non riguarda il punto né un edificio
  function clic2d(e) {
    if (Date.now() - (stato.trascinato || 0) < 400) return true;     // fine di un trascinamento del punto
    const m = stato.mappa, ids = stato.strati2d.filter((id) => m.getLayer(id));
    const f = ids.length ? m.queryRenderedFeatures(e.point, { layers: ids })[0] : null;
    if (!f) {
      if (m.getZoom() < 15) return false;
      impostaPunto(e.lngLat.lng, e.lngLat.lat, "clic");
      puntoCambiato();
      return true;
    }
    const edificio = String(f.properties.edificio || "");
    if (stato.daGenerare && stato.daGenerare.edificio === edificio) { togliScelta2d(); return true; }
    impostaPunto(e.lngLat.lng, e.lngLat.lat, "clic");
    scegli2d(edificio, e.lngLat.lng, e.lngLat.lat, null, ids.indexOf(f.layer.id));
    return true;
  }
  // punto della ricerca, del clic o spostato a mano: segnaposto sulla mappa 2D
  function impostaPunto(lon, lat, origine) {
    const m = stato.mappa;
    stato.punto = { ...(stato.punto || {}), lon, lat, origine };      // fonte e indirizzo della ricerca restano
    if (m && m.getSource("cercato")) {
      m.getSource("cercato").setData({ type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [lon, lat] } }] });
    }
  }
  // zona coperta dagli archivi (07/11/2026): per un archivio di un comune intero (istat) il confine ISTAT del comune, per
  // gli altri il riquadro [lon0, lat0, lon1, lat1] dei corpi (che sborda sui comuni vicini)
  async function coperto(lon, lat) {
    const archivi = veri().length ? veri() : stato.indice && !stato.archivi.length ? [{ indice: stato.indice }] : [];
    const dentro = (a) => { const r = a.indice && a.indice.riquadro;
      return Array.isArray(r) && r.length === 4 && lon >= r[0] && lon <= r[2] && lat >= r[1] && lat <= r[3]; };
    if (archivi.some((a) => !a.istat && dentro(a))) return true;
    const conIstat = archivi.filter((a) => a.istat);
    if (!conIstat.length) return false;
    const c = await comuneNelPunto(lon, lat);
    if (c && conIstat.some((a) => a.istat === c.istat)) return true;
    // (07/11/2026 sera) i confini ISTAT del sito sono generalizzati (~100 m): vicino al confine il 5 % dei corpi DBTR
    // (Cattolica 13 %) cadeva «fuori» e prendeva OpenStreetMap. Coperto anche se l'archivio ha un corpo entro 150 m.
    for (const a of conIstat.filter(dentro)) if (await vicinoAlDbtr(a, lon, lat)) return true;
    return false;
  }
  async function vicinoAlDbtr(a, lon, lat, metri = MARGINE_CONFINE) {
    if (!a.base) return false;
    const dlat = metri / 110574, dlon = metri / (111320 * Math.cos(lat * Math.PI / 180)), c = (a.indice && a.indice.cella) || 0.01;
    for (let i = Math.floor((lon - dlon) / c); i <= Math.floor((lon + dlon) / c); i++) {
      for (let j = Math.floor((lat - dlat) / c); j <= Math.floor((lat + dlat) / c); j++) {
        const d = await cella(`${i}_${j}`, a.base);
        for (const f of (d && d.features) || []) {
          const r0 = anelli(f.geometry)[0];
          if (r0 && r0.some((q) => Math.abs(q[0] - lon) <= dlon && Math.abs(q[1] - lat) <= dlat)) return true;
        }
      }
    }
    return false;
  }
  // comune del punto: confini di tutta Italia (confini_gl.js), altrimenti quelli dell'Emilia-Romagna (dati/mappa/08.json)
  async function comuneNelPunto(lon, lat) {
    if (C && typeof C.comuneNelPunto === "function") { try { const c = await C.comuneNelPunto(lon, lat); if (c) return c; } catch { /* sotto */ } }
    return comuneDi(lon, lat);
  }
  function nomiArchivi() {
    const n = (veri().length ? veri() : stato.indice && !stato.archivi.length ? [{ indice: stato.indice }] : [])
      .map((a) => a.indice && (a.indice.nome || a.indice.attribuzione)).filter(Boolean);
    return n.length ? (n.length > 4 ? `${n.slice(0, 4).map((x) => `«${x}»`).join(", ")} e altri ${n.length - 4}` : n.map((x) => `«${x}»`).join(", ")) : "«archivio degli edifici»";
  }
  // testo quando nessun edificio contiene il punto: fuori dalla zona coperta (con o senza il ripiego OSM), o dentro ma
  // lontano dagli edifici
  async function nessunEdificio(lon, lat, prima) {
    if (!(await coperto(lon, lat))) {
      const zona = veri().length ? `dall'archivio degli edifici (${nomiArchivi()})` : "da un archivio degli edifici di qualità (DBTR)";
      if (stato.osmAttivo && stato.osm.errore) {
        return `${prima}il punto è fuori dalla zona coperta ${zona} e OpenStreetMap, il ripiego per queste zone, non ha risposto `
          + `(${stato.osm.errore.replace(/\.$/, "")}): qui il 3D non si può generare ora. Riprova tra qualche minuto.`;
      }
      if (stato.osmAttivo) {
        return `${prima}il punto è fuori dalla zona coperta ${zona}: qui si usano gli edifici di OpenStreetMap (ripiego, altezze in `
          + "parte stimate), ma nessuno contiene il punto né è entro 30 m. Trascina il punto sull'edificio o fai clic sull'edificio.";
      }
      return `${prima}il punto è fuori dalla zona coperta ${zona}: qui il 3D non si può ancora `
        + "generare. Le zone coperte sono tratteggiate sulla mappa.";
    }
    return `${prima}nessun edificio dell'archivio lo contiene (né entro 30 m). Trascina il punto sull'edificio o fai clic sull'edificio.`;
  }
  // il punto è cambiato (trascinato o clic): sceglie l'edificio che lo contiene (o il più vicino entro 30 m)
  async function puntoCambiato() {
    const p = stato.punto;
    if (!p) return;
    const dove = `${p.lat.toFixed(6)} N, ${p.lon.toFixed(6)} E`;
    if (!stato.archivi.length && !stato.base) {
      messaggio("messaggio", `Punto ${p.origine === "spostato" ? "spostato" : "messo"} in ${dove}. L'archivio degli edifici di questa zona non è `
        + "ancora sul server: il 3D non si può generare qui (prova la demo sintetica).", true);
      return;
    }
    const f = edificioNelPunto(await contesto(p.lon, p.lat), p.lon, p.lat);
    if (f) {
      scegli2d(String(f.properties.edificio), p.lon, p.lat, null, +f.properties.archivio || 0);
      if (p.origine === "spostato") messaggio("messaggio", `Punto spostato in ${dove}: scelto l'edificio ${f.properties.edificio}. Premi «Genera il 3D» `
        + "o sposta ancora il punto." + avvisoOsm(+f.properties.archivio || 0));
    } else {
      stato.daGenerare = null; evidenzia2d(""); $("genera-3d").disabled = true;
      messaggio("messaggio", await nessunEdificio(p.lon, p.lat, `Punto in ${dove}: `), true);
    }
  }
  // trascinamento del segnaposto (mouse e dito) nella mappa 2D
  function trascinaPunto(m) {
    const muovi = (e) => { impostaPunto(e.lngLat.lng, e.lngLat.lat, "spostato"); };
    const fine = () => {
      m.off("mousemove", muovi); m.off("touchmove", muovi);
      stato.trascino = false; stato.trascinato = Date.now();
      m.getCanvas().style.cursor = "";
      puntoCambiato();
    };
    const inizio = (e, tocco) => {
      if (stato.in3d || stato.modo || !stato.punto) return;
      e.preventDefault();                       // niente spostamento della mappa durante il trascinamento
      stato.trascino = true; m.getCanvas().style.cursor = "grabbing";
      m.on(tocco ? "touchmove" : "mousemove", muovi);
      m.once(tocco ? "touchend" : "mouseup", fine);
    };
    m.on("mousedown", "cercato", (e) => inizio(e, false));
    m.on("touchstart", "cercato", (e) => { if (e.points && e.points.length === 1) inizio(e, true); });
  }
  function scegli2d(edificio, lon, lat, sede = null, k = 0) {
    stato.daGenerare = { edificio, lon, lat, sede };
    evidenzia2d(edificio);
    $("genera-3d").disabled = false;
    const a = stato.archivi[Math.max(0, k)], f = a && a.osm ? stato.osm.visti.get(edificio) : null;
    const att = f && f.properties && f.properties.regione_sagoma ? String(f.properties.fonte_sagoma || "") : a && a.indice.attribuzione;   // sagome regionali (08/11/2026)
    const fonte = att ? ` (sagome: ${att})` : "";
    messaggio("messaggio", `Edificio ${edificio} scelto${fonte}. Premi «Genera il 3D» sotto la mappa; un altro clic cambia la scelta, `
      + "un clic sullo stesso edificio la toglie." + avvisoOsm(Math.max(0, k)));
  }
  function togliScelta2d() {
    stato.daGenerare = null; evidenzia2d(""); $("genera-3d").disabled = true;
    messaggio("messaggio", "Nessun edificio scelto: fai clic su un edificio della mappa.");
  }
  async function genera() {
    const d = stato.daGenerare;
    if (!d) return;
    $("genera-3d").disabled = true;
    try { if (await scegli(d.edificio, d.lon, d.lat, d.sede)) entra3d(); }
    finally { $("genera-3d").disabled = !stato.daGenerare || stato.in3d; }
  }
  function entra3d() {
    const m = stato.mappa;
    if (!DUE_TEMPI || !m) return;
    stato.in3d = true;
    vedi(m, strati3d(), true); vedi(m, strati2dTutti(), false); vedi(m, ["confini-comuni", "confini-province"], false);
    vedi(m, ["alberi"], !!stato.alberiVisibili);           // casella «Alberi» (09/11/2026)
    // edificio OSM (ripiego): niente DTM, mappa piatta come le quote dei corpi
    terreno3d(); coloriRilievo(); fonteTerreno();
    m.dragRotate.enable(); m.touchPitch.enable(); m.touchZoomRotate.enableRotation(); m.doubleClickZoom.disable();
    $("torna-2d").hidden = false; $("genera-3d").hidden = true; $("aiuto-2d").hidden = true; $("aiuto-3d").hidden = false;
    if (stato.barra3d) stato.barra3d.hidden = false;
    m.getCanvas().setAttribute("tabindex", "0");
    vistaNominata("3d");
    fontiCorpi();
  }
  // azzera (07/11/2026 sera, prove di Paolo): nuova ricerca o mappa portata lontano dall'edificio durante il 3D; si torna
  // alla mappa 2D dritta (subito, senza animazione: un volo partito subito dopo la interromperebbe e la mappa restava
  // inclinata, un «3D piatto») e il 3D dell'edificio di prima si toglie dalla mappa
  function esci3d(azzera = false) {
    const m = stato.mappa;
    if (!DUE_TEMPI || !m || !stato.in3d) return;
    stato.in3d = false;
    finisciModo();
    if (stato.anima) $("anima").click();
    vedi(m, strati3d(), false); vedi(m, strati2dTutti(), true); vedi(m, ["confini-comuni", "confini-province"], true);
    try { m.setTerrain(null); } catch { /* niente */ }
    quotaCamera();
    m.dragRotate.disable(); m.touchPitch.disable(); m.touchZoomRotate.disableRotation(); m.doubleClickZoom.enable();
    if (typeof m.setVerticalFieldOfView === "function") m.setVerticalFieldOfView(36.87);
    if (azzera) {
      m.jumpTo({ pitch: 0, bearing: 0, roll: 0 });
      stato.corpi = []; stato.vicini = []; stato.originali = []; stato.aree = []; stato.edificio = null; stato.daGenerare = null;
      evidenzia2d("");
      ["scelto", "falde", "fv", "ombre", "facciate", "linea", "alberi"].forEach((id) => { const g = m.getSource(id); if (g) g.setData({ type: "FeatureCollection", features: [] }); });
    } else m.easeTo({ pitch: 0, bearing: 0, roll: 0, duration: 600 });
    $("torna-2d").hidden = true; $("genera-3d").hidden = false; $("genera-3d").disabled = !stato.daGenerare;
    $("aiuto-2d").hidden = false; $("aiuto-3d").hidden = true;
    if (stato.barra3d) stato.barra3d.hidden = true;
    messaggio("messaggio", azzera ? "Mappa 2D: il 3D dell'edificio di prima è stato tolto. Scegli l'edificio con un clic, poi «Genera il 3D»."
      : "Mappa 2D: scegli un altro edificio con un clic (o cercalo), poi «Genera il 3D». A destra restano i dati dell'ultimo edificio generato.");
    fontiCorpi();
  }
  // nella vista 3D la mappa portata a più di 2 km dall'edificio: si torna al 2D (stesso comportamento della ricerca)
  const LONTANO_3D = 2000;
  function lontanoDal3d() {
    const m = stato.mappa;
    if (!stato.in3d || !stato.proj || !m) return;
    const c = m.getCenter(), p = stato.proj.avanti([c.lng, c.lat]);
    if (Math.hypot(p[0], p[1]) > LONTANO_3D) esci3d(true);
  }
  // viste come in mappa3d.js: dall'alto, 3D (inclinazione 55°, imbardata −20°), isometrica (60°, −45°, prospettiva quasi
  // nulla: MapLibre non ha la proiezione ortografica, si usa un campo visivo stretto)
  function vistaNominata(nome) {
    const m = stato.mappa;
    if (!m) return;
    const v = { alto: { pitch: 0, bearing: 0 }, "3d": { pitch: 55, bearing: -20 }, iso: { pitch: 60, bearing: -45 } }[nome] || { pitch: 55, bearing: -20 };
    if (typeof m.setVerticalFieldOfView === "function") m.setVerticalFieldOfView(nome === "iso" ? 8 : 36.87);
    let centro = stato.proj ? stato.proj.indietro([0, 0]) : m.getCenter();
    let z = 17.6;
    // isometrica (07/11/2026 sera, «troppo vicina»): l'inquadratura è circa il doppio dell'edificio (lato maggiore della
    // pianta o altezza, il più grande), centrata sull'edificio
    if (nome === "iso" && stato.corpi.length && stato.proj) {
      const pts = stato.corpi.flatMap((c) => c.ring);
      const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
      const L = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys), ...stato.corpi.map((c) => c.colmo || c.gronda || 0), 10);
      centro = stato.proj.indietro([(Math.max(...xs) + Math.min(...xs)) / 2, (Math.max(...ys) + Math.min(...ys)) / 2]);
      const lato = Math.min(m.getContainer().clientWidth || 600, m.getContainer().clientHeight || 400);
      z = Math.max(14, Math.min(20, Math.log2(78271.517 * Math.cos(centro[1] * Math.PI / 180) * lato / (2 * L))));
    }
    quotaCamera();
    m.easeTo({ ...v, roll: 0, center: centro, zoom: stato.edificio ? z : m.getZoom(), ...(stato.in3d ? { elevation: quotaDelCentro() } : {}), duration: 600 });
  }
  function comandi3d(m) {
    const comandi = h("div", "mappa3d-comandi"); comandi.setAttribute("role", "toolbar"); comandi.setAttribute("aria-label", "Comandi della vista 3D");
    const ruota = (d) => m.easeTo({ bearing: m.getBearing() + d, duration: 250 });
    const inclina = (d) => m.easeTo({ pitch: Math.max(0, Math.min(80, m.getPitch() + d)), duration: 250 });
    const rolla = (d) => { if (typeof m.setRoll === "function") m.setRoll((m.getRoll() || 0) + d); };
    const gruppi = [
      ["Zoom", [["−", "Rimpicciolisci", () => m.zoomOut()], ["+", "Ingrandisci", () => m.zoomIn()]]],
      ["Vista", [["Dall'alto", "Vista dall'alto (tasto 0)", () => vistaNominata("alto")], ["3D", "Vista 3D predefinita (tasto 3)", () => vistaNominata("3d")],
        ["Isometrica", "Vista isometrica: prospettiva quasi nulla, mappa vista a 30° sopra l'orizzonte (tasto I)", () => vistaNominata("iso")]]],
      ["Ruota", [["↺", "Ruota la mappa a sinistra", () => ruota(-15)], ["↻", "Ruota la mappa a destra", () => ruota(15)]]],
      ["Inclina", [["−", "Inclina di meno, verso la vista dall'alto", () => inclina(-10)], ["+", "Inclina di più", () => inclina(10)]]],
      ["Rollio", [["↺", "Rollio a sinistra", () => rolla(-15)], ["↻", "Rollio a destra", () => rolla(15)]]],
      ["Rilievo", [["×1", "Rilievo vero (predefinito)", () => esagera(1), 1], ["×1,5", "Rilievo esagerato una volta e mezza", () => esagera(1.5), 1.5],
        ["×2", "Rilievo esagerato due volte", () => esagera(2), 2]]],
    ];
    for (const [nome, pulsanti] of gruppi) {
      const g = h("span", "mappa3d-gruppo"); g.setAttribute("role", "group"); g.setAttribute("aria-label", nome); g.dataset.gruppo = nome;
      g.appendChild(h("span", "mappa3d-nome", nome));
      for (const [t, titolo, fa, x] of pulsanti) {
        const b = h("button", null, t); b.type = "button"; b.title = titolo; b.setAttribute("aria-label", titolo); b.addEventListener("click", fa);
        if (x) { b.dataset.esagera = String(x); b.setAttribute("aria-pressed", String(x === 1)); }
        g.appendChild(b);
      }
      comandi.appendChild(g);
    }
    comandi.hidden = true;
    $("comandi-edificio").after(comandi);
    stato.barra3d = comandi;
  }
  // tastiera come in mappa3d.js (solo nella vista 3D): frecce = spostamento, Ctrl+frecce = rotazione e inclinazione,
  // Ctrl+Maiuscolo+frecce = rollio, + e − = zoom, 0 = dall'alto, 3 = vista 3D, I = isometrica
  function tastiera3d(e) {
    const m = stato.mappa;
    if (!stato.in3d || !m || /^(INPUT|SELECT|TEXTAREA)$/.test((e.target && e.target.tagName) || "")) return;
    const frecce = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
    if (frecce[e.key]) {
      const [dx, dy] = frecce[e.key], ruota = e.ctrlKey || e.metaKey;
      if (ruota && e.shiftKey) { if (typeof m.setRoll === "function") m.setRoll((m.getRoll() || 0) + dx * 10); }
      // passi istantanei, come in mappa3d.js: un'animazione breve verrebbe interrotta dal gestore degli eventi di MapLibre
      else if (ruota) m.jumpTo({ bearing: m.getBearing() + dx * 10, pitch: Math.max(0, Math.min(80, m.getPitch() - dy * 5)) });
      else m.panBy([dx * 80, dy * 80], { duration: 0 });
    } else if (e.key === "+" || e.key === "=") m.zoomIn();
    else if (e.key === "-" || e.key === "_") m.zoomOut();
    else if (e.key === "0") vistaNominata("alto");
    else if (e.key === "3") vistaNominata("3d");
    else if (e.key === "i" || e.key === "I") vistaNominata("iso");
    else return;
    e.preventDefault();
  }
  // regione dalla piccola mappa o dalla mappa: si va lì (e si torna al 2D); secondo clic sulla stessa = Italia intera
  // sposta = false (clic sulla mappa grande, 09/11/2026): si sceglie ed evidenzia la regione senza muovere la vista
  async function vaiRegione(cod, sposta = true) {
    const b = C && await C.riquadroRegione(cod);
    if (!b || !stato.mappa) return;
    if (sposta) esci3d();
    stato.regione = cod;
    if (stato.confini) { stato.confini.scegliRegione(cod); stato.confini.scegliComune(""); }
    if (window.EUGENIO && window.EUGENIO.seleziona) window.EUGENIO.seleziona(cod);
    if (sposta) stato.mappa.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 20, duration: 700 });
  }
  function togliRegione(sposta = true) {
    if (!stato.mappa) return;
    if (sposta) esci3d();
    stato.regione = null;
    if (stato.confini) { stato.confini.scegliRegione(""); stato.confini.scegliComune(""); }
    if (window.EUGENIO && window.EUGENIO.evidenziaPiccola) window.EUGENIO.evidenziaPiccola(null);
    const I = C ? C.ITALIA : [6.6, 35.4, 18.6, 47.1];
    if (sposta) stato.mappa.fitBounds([[I[0], I[1]], [I[2], I[3]]], { padding: 10, duration: 700 });
  }
  if (DUE_TEMPI && window.EUGENIO) {
    window.EUGENIO.suRegione = (cod) => { vaiRegione(cod); };
    window.EUGENIO.suStessaRegione = (cod) => { if (stato.regione === cod) togliRegione(); else vaiRegione(cod); };
    window.EUGENIO.mappaPrincipale = { nazionale: () => togliRegione() };
  }

  // fonte usata per ogni corpo, dalla più affidabile (05/11/2026): falde LiDAR → DB topografico regionale con le altezze →
  // modello importato DXF/IFC → OSM → stima
  const LIVELLI = ["falde LiDAR", "corpi dal LiDAR", "DB topografico regionale", "modello importato (DXF/IFC)", "sagome regionali con altezze OSM o stimate", "OpenStreetMap", "stima", "dato dell'utente", "dati sintetici"];
  function livelloFonte(c) {
    if (c.sintetico) return "dati sintetici";
    if (c.modificato) return "dato dell'utente";
    if (c.edificio === "MODELLO") return "modello importato (DXF/IFC)";
    if (c.lidar && c.lidar.stato === "ok") return "falde LiDAR";
    if (c.regione_sagoma) return "sagome regionali con altezze OSM o stimate";      // 08/11/2026 (Veneto)
    const t = `${c.fonte_sagoma} ${c.fonte_altezza} ${c.licenza}`.toLowerCase();
    if (/stima|stimat/.test(String(c.fonte_altezza).toLowerCase())) return "stima";
    if (/osm|openstreetmap|odbl/.test(t)) return "OpenStreetMap";
    // «DBTR … da DTM DSM 2008» è un'altezza del DB topografico (07/11/2026): il LiDAR si riconosce dalla sagoma
    if (/dbtr|db topografico|database topografico|dbgt|ctrn|ctr 3d/.test(t)) return "DB topografico regionale";
    if (/lidar|dsm/.test(t)) return "corpi dal LiDAR";
    return "DB topografico regionale";
  }
  function testoFontiCorpi() {
    if (!stato.corpi.length) return "";
    const per = new Map();
    for (const c of stato.corpi) { const l = livelloFonte(c); per.set(l, [...(per.get(l) || []), c.id]); }
    const parti = [...per.entries()].sort((a, b) => LIVELLI.indexOf(a[0]) - LIVELLI.indexOf(b[0]))
      .map(([l, ids]) => `${l}: ${ids.length > 6 ? `${ids.length} corpi` : ids.join(", ")}`);
    return `Fonte del 3D per corpo (dalla più affidabile): ${parti.join("; ")}. Il dettaglio (sagoma, altezza, licenza) è nella tabella «Corpi».`;
  }
  // tetti stimati e ipotizzati: forma e precedenza, per la nota, l'immagine e il report
  function testoTettiStimati() {
    const n = contaTetti(), t = [];
    if (n.colmo) t.push(`Tetto a falde stimato dal colmo DBTR per ${n.colmo} ${n.colmo === 1 ? "corpo" : "corpi"}`);
    if (n.ipotesi) t.push(`tetto ipotizzato a falde per ${n.ipotesi} ${n.ipotesi === 1 ? "corpo" : "corpi"} (22° in pianura, 32° in montagna: quota del terreno da 600 m al Nord, da 700 m al Centro-Sud)`);
    if (!t.length) return "";
    const s = t.join("; ");
    return `${s[0].toUpperCase()}${s.slice(1)}: forma a capanna sul lato lungo o a padiglione; le falde LiDAR, quando ci saranno, prendono il posto delle stime.`;
  }
  function fontiCorpi() {
    const p = $("fonti-corpi");
    if (!p) return;
    const t = testoFontiCorpi();
    p.textContent = t; p.hidden = !t || !stato.in3d;
    const nt = $("nota-tetti"), tt = stato.in3d ? testoTetti() : "";
    if (nt) { nt.textContent = tt; nt.hidden = !tt; }
    const lf = $("legenda-falde");
    if (lf) {
      const n = contaTetti();
      lf.lastChild.textContent = stato.in3d && stato.corpi.length
        ? `falde dei tetti: ${n.lidar} LiDAR, ${n.colmo} dal colmo DBTR, ${n.ipotesi} ipotizzate (22°/32°), ${n.piano} piani (dall'arancio, a sud, al blu, a nord)`
        : "falde dei tetti: LiDAR, stimate dal colmo DBTR o ipotizzate a 22°/32° (dall'arancio, a sud, al blu, a nord)";
    }
    const lo = $("legenda-osm"); if (lo) lo.hidden = !(stato.osm && stato.osm.visti && stato.osm.visti.size);
    legendaTerreno();
    notaAltezzeOsm();
  }

  // immagine della vista (2D o 3D) con le attribuzioni di tutto quello che si vede
  function opzioniImmagine() {
    const m = stato.mappa, righe = [];
    if (!m) return "La mappa non è pronta.";
    const f = ortoVisibile() ? stato.ortofoto : null;
    if (f && !f.copia) return `«${f.nome}» è solo in consultazione dal vivo: per scaricare l'immagine scegli un'altra ortofoto o nessuna.`;
    if (f) righe.push(`Ortofoto: ${f.citazione} – licenza ${f.licenza} (${f.scheda})${f.stato === "da confermare" ? "; uso tramite il server di EuGEnio in attesa di conferma della fonte" : ""}.`);
    if (f && stato.sposta && stato.sposta.riga()) righe.push(stato.sposta.riga());
    if (stato.contestoOrto && m.getLayer("contesto") && !f && ortoVisibile()) righe.push(`Contesto: ${stato.contestoOrto.citazione} – licenza ${stato.contestoOrto.licenza}.`);
    const archivi = stato.archivi.length ? stato.archivi : stato.indice ? [{ indice: stato.indice }] : [];
    new Set(archivi.filter((a) => !a.osm).map((a) => {
      const att = a.indice.attribuzione || "archivio di EuGEnio", lic = a.indice.licenza || "";
      return `Edifici: ${att}${lic && !att.includes(lic) ? ` (${lic})` : ""}.`;
    })).forEach((t) => righe.push(t));
    // ripiego OSM (07/11/2026): licenza della sagoma, mai confusa con quella dell'archivio CC BY
    if (archivi.some((a) => a.osm) && stato.osm.visti.size && stato.osm.sagome)
      righe.push(`Sagome degli edifici fuori dal DBTR: ${stato.osm.sagome.attribuzione} (${stato.osm.sagome.scheda || ""}), dal servizio WFS della Regione.`);
    if (archivi.some((a) => a.osm) && stato.osm.visti.size)
      righe.push("Edifici fuori dal DBTR: © OpenStreetMap contributors, ODbL 1.0 (openstreetmap.org/copyright), tramite l'API Overpass; "
        + "ripiego con altezze in parte stimate.");
    if (archivi.some((a) => a.osm) && (stato.osm.visti.size || stato.in3d)) { const t = testoAltezzeOsm(altezzeOsmVista(), stato.in3d ? " dell'edificio e dei vicini" : " nella vista"); if (t) righe.push(t); }
    if (stato.in3d && stato.lidar && stato.corpi.some((c) => c.lidar && c.lidar.stato === "ok"))
      Object.values(stato.lidar.attribuzioni || {}).forEach((a) => righe.push(`Falde dei tetti: ${a.attribuzione || a.descrizione} (${a.licenza}).`));
    if (stato.in3d && stato.terrenoServer && !stato.sintetico && !stato.corpi.some((c) => (archivioDi(c) || {}).osm)) righe.push(`${ATTRIBUZIONE_TERRENO}; quote dei corpi dal DTM 5×5 m.`);
    else if (stato.in3d && stato.terrenoServer && stato.nomeTerreno) righe.push(`Terreno: ${stato.nomeTerreno}; altrove Copernicus DEM GLO-90 (© DLR e Airbus).`);
    // legenda dei colori e del terreno nella vista 3D (07/11/2026 sera)
    if (stato.in3d) {
      const osmVisti = stato.osmAttivo && (stato.osm.visti.size || stato.vicini.some((c) => (archivioDi(c) || {}).osm));
      const ts = testoTettiStimati();
      const alberiVisti = stato.alberiVisibili && alberiVicini().length;
      righe.push(`Colori: edificio scelto in evidenza; edifici vicini del DB topografico in ${voceColore().nome.toLowerCase()}${osmVisti ? "; edifici OpenStreetMap in marrone (altezza da OSM o stimata)" : ""}`
        + `${stato.corpi.some((c) => c.falde && c.falde.length) ? "; falde dei tetti dall'arancio (a sud) al blu (a nord)" : ""}`
        + `${alberiVisti ? "; alberi in verde (chiome dal LiDAR, DSM meno DTM)" : ""}.`
        + (ts ? ` ${ts}` : ""));
      if (stato.corpi.length) righe.push(testoTetti());
      const t = $("legenda-terreno");
      if (t && t.textContent) righe.push(`${t.textContent}.`);
    }
    if (stato.in3d && stato.corpi.some((c) => (archivioDi(c) || {}).locale)) righe.push("Edifici dal DB topografico caricato dall'utente (letto solo nel browser): quote dei corpi dalla base del DB topografico, terreno 3D dal server.");
    if (stato.in3d) { const t = testoFontiCorpi(); if (t) righe.push(t.replace(/ Il dettaglio.*$/, "")); }
    if (stato.modello) righe.push(`Modello dell'utente «${stato.modello}» (letto solo nel browser).`);
    if (stato.strati) righe.push(...stato.strati.righe());
    if (!stato.in3d && stato.punto) {
      const p = stato.punto;
      righe.push(`Punto: ${p.lat.toFixed(6)} N, ${p.lon.toFixed(6)} E${p.testo ? ` (${p.testo})` : ""}${p.fonte ? `, da ${p.fonte}` : ""}${p.origine === "spostato" || p.origine === "clic" ? ", posizione corretta a mano" : ""}.`);
    }
    righe.push(`${C ? C.ATTRIBUZIONE : "Confini: ISTAT (CC BY 4.0)"}. Mappa: MapLibre GL JS (BSD-3).`);
    const titolo = stato.in3d && stato.edificio
      ? `${TITOLO} – ${stato.modello ? `modello «${stato.modello}»` : `edificio ${stato.edificio}`}${stato.comune ? `, ${stato.comune.nome}` : ""}`
      : `${TITOLO} – mappa 2D, ${m.getCenter().lat.toFixed(5)} N ${m.getCenter().lng.toFixed(5)} E`;
    const sint = stato.sintetico || (stato.indice && stato.indice.sintetico);
    return { titolo, righe, avviso: sint ? "Dati sintetici di esempio: sagome, altezze e terreno inventati, non rappresentano edifici reali." : "",
      nome: stato.in3d && stato.edificio ? `modello3d_${String(stato.edificio).replace(/[^\w-]+/g, "_").slice(0, 40)}` : "modelli3d_mappa" };
  }

  // ricerca per indirizzo o per foglio e particella (cerca_luogo.js, comune con la pagina Ortofoto): la mappa va sul punto,
  // con il segnaposto da trascinare se l'indirizzo è impreciso; l'edificio è quello che contiene il punto
  async function trovato(lon, lat, x) {
    const m = stato.mappa;
    if (!m) return;
    esci3d(true);
    stato.punto = { lon, lat, origine: "ricerca", fonte: x.centro_comune ? "centro del comune (confini ISTAT, CC BY 4.0)"
      : x.fonte_punto === "ANNCSU" ? "ANNCSU – Agenzia delle Entrate e ISTAT (CC BY 4.0)" : "dati elaborati da Zornade (zornade.com)",
      testo: [x.indirizzo_trovato, x.comune_catasto].filter(Boolean).join(", ") };
    impostaPunto(lon, lat, "ricerca");
    m.flyTo({ center: [lon, lat], zoom: x.zoom || ZOOM_CERCA, pitch: 0, bearing: 0, duration: 900 });
    // solo il comune, o indirizzo senza coordinate (07/11/2026 sera): nessun edificio scelto, si avvicina l'utente
    if (x.centro_comune) {
      stato.daGenerare = null; evidenzia2d(""); $("genera-3d").disabled = true;
      messaggio("messaggio", `Centro del comune di ${x.comune_catasto || ""}: avvicinati, poi fai clic sull'edificio (o trascina il punto); infine «Genera il 3D».`);
      return;
    }
    if (stato.archivi.length || stato.base) {
      const f = edificioNelPunto(await contesto(lon, lat), lon, lat);
      if (f) {
        scegli2d(String(f.properties.edificio), lon, lat, null, +f.properties.archivio || 0);
        messaggio("messaggio", `Edificio ${f.properties.edificio} scelto nel punto trovato. Se il punto non è sull'edificio giusto `
          + "(l'indirizzo può essere impreciso) trascinalo o fai clic sull'edificio; poi «Genera il 3D»." + avvisoOsm(+f.properties.archivio || 0));
      } else messaggio("messaggio", await nessunEdificio(lon, lat, "Punto trovato: "), true);
    } else messaggio("messaggio", "Punto trovato (trascinalo per correggerlo). L'archivio degli edifici di questa zona non è ancora sul server: "
      + "il 3D non si può generare qui.", true);
  }
  if (DUE_TEMPI) {
    if (window.EUGENIO_CERCA) window.EUGENIO_CERCA.crea($("cerca-edificio"), { suTrovato: trovato });
    $("genera-3d").addEventListener("click", genera);
    $("torna-2d").addEventListener("click", esci3d);
  }

  function inclinate(c) { return (c.falde || []).filter((f) => f.pendenza >= 5 && Number.isFinite(f.alto) && Number.isFinite(f.basso)); }
  function geojson(corpi, quotaBase = false) {
    return { type: "FeatureCollection", features: corpi.map((c) => ({ type: "Feature",
      // con le falde inclinate il prisma arriva alla gronda e sopra si vedono le falde a gradini
      properties: { id: c.id, altezza: inclinate(c).length ? c.gronda : (c.colmo || c.gronda), quota: quotaBase ? c.quota : 0 },
      geometry: { type: "Polygon", coordinates: [c.ring, ...(c.buchi || [])].map((r) => E.chiudi(r).map(stato.proj.indietro)) } })) };
  }
  // una falda divisa in strisce lungo la discesa, ognuna alta quanto il suo bordo superiore (Sutherland–Hodgman)
  function taglia(ring, d, s0, s1) {
    let pts = E.chiudi(ring).slice(0, -1);
    for (const [segno, lim] of [[1, s0], [-1, s1]]) {
      const dentro = (q) => segno * (q[0] * d[0] + q[1] * d[1] - lim) >= 0, out = [];
      for (let i = 0; i < pts.length; i++) {
        const a = pts[i], b = pts[(i + 1) % pts.length], ia = dentro(a), ib = dentro(b);
        if (ia) out.push(a);
        if (ia !== ib) {
          const sa = a[0] * d[0] + a[1] * d[1], sb = b[0] * d[0] + b[1] * d[1], t = (lim - sa) / (sb - sa);
          out.push([a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]);
        }
      }
      pts = out;
      if (pts.length < 3) return null;
    }
    return E.chiudi(pts);
  }
  function strisce(c) {
    const out = [];
    for (const f of inclinate(c)) {
      const az = f.orientamento * Math.PI / 180, d = [Math.sin(az), Math.cos(az)];
      const s = E.chiudi(f.ring).slice(0, -1).map((q) => q[0] * d[0] + q[1] * d[1]), s0 = Math.min(...s), s1 = Math.max(...s);
      const n = Math.max(2, Math.min(14, Math.ceil((f.alto - f.basso) / 0.35)));
      const t = (1 - Math.cos(az - Math.PI)) / 2;
      for (let k = 0; k < n; k++) {
        const r = taglia(f.ring, d, s0 + (s1 - s0) * k / n, s0 + (s1 - s0) * (k + 1) / n);
        if (r) out.push({ type: "Feature", properties: { z: f.alto - (f.alto - f.basso) * k / n, t },
          geometry: { type: "Polygon", coordinates: [r.map(stato.proj.indietro)] } });
      }
    }
    return out;
  }
  function ridisegna() {
    const m = stato.mappa;
    if (!m) return;
    m.getSource("scelto").setData(geojson(stato.corpi));
    m.getSource("falde").setData({ type: "FeatureCollection", features: stato.corpi.flatMap(strisce) });
    if (m.getSource("alberi")) m.getSource("alberi").setData({ type: "FeatureCollection", features: alberiVicini().map((a) => ({ type: "Feature",
      properties: { h: a.h }, geometry: { type: "Polygon", coordinates: [ottagono(a).map(stato.proj.indietro)] } })) });
    // corpi modificati o divisi: si nasconde la loro versione nelle tessere
    const nascosti = [...new Set(stato.originali.map((c) => c.id).concat(stato.nascostiExtra))];
    (stato.sorgentiCorpi || ["corpi"]).forEach((id) => { if (m.getLayer(id)) m.setFilter(id, nascosti.length ? ["!", ["in", ["get", "id"], ["literal", nascosti]]] : null); });
    m.getSource("fv").setData({ type: "FeatureCollection", features: stato.aree.map((a) => ({ type: "Feature",
      properties: { quota: a.quota }, geometry: { type: "Polygon", coordinates: [E.chiudi(a.ring).map(stato.proj.indietro)] } })) });
    ombre();
  }

  // ------------------------------------------------------------------ selezione
  async function clic(e) {
    if (DUE_TEMPI && !stato.in3d) return clic2d(e);
    const p = stato.proj ? stato.proj.avanti([e.lngLat.lng, e.lngLat.lat]) : null;
    if (stato.modo === "dividi") return puntoDivisione(p);
    if (stato.modo === "fv") return aggiungiArea(p);
    const ids = ["scelto", ...(stato.sorgentiCorpi || [])].filter((id) => stato.mappa.getLayer(id));
    const f = stato.mappa.queryRenderedFeatures(e.point, { layers: ids });
    if (!f.length) return;
    const edificio = String(f[0].properties.edificio || "");
    if (f[0].layer.id === "scelto" && stato.edificio) return;
    await scegli(edificio, e.lngLat.lng, e.lngLat.lat);
  }

  // sede: dati di una sede del Patrimonio ({ nome, facoltative, visura }) quando l'edificio si apre da lì; senza, i dati
  // della sede aperta prima si tolgono (restano quelli scritti a mano solo per l'edificio su cui si lavora)
  function impostaSede(sede) {
    if (!sede && !stato.sede) return;
    stato.sede = sede || null;
    stato.visura = sede ? E.daVisura(sede.visura || {}) : {};
    stato.csv = sede ? { ...(sede.facoltative || {}) } : {};
    for (const k of Object.keys(E.FACOLTATIVE)) { const i = $(`csv-${k}`); if (i) i.value = stato.csv[k] !== undefined ? stato.csv[k] : ""; }
    const n = $("nota-sede");
    if (n) {
      n.hidden = !sede;
      if (sede) {
        const v = stato.visura, parti = [];
        if (v.piani_fuori_terra) parti.push(`${v.piani_fuori_terra} piani fuori terra`);
        if (v.piani_interrati) parti.push(`${v.piani_interrati} interrati`);
        if (v.superficie_catastale) parti.push(`${fmt(v.superficie_catastale)} m² catastali`);
        if (v.uso) parti.push(`uso ${v.uso}`);
        n.textContent = `Sede «${sede.nome}» aperta dal Patrimonio: ${Object.keys(stato.csv).length ? "colonne facoltative del file nei campi qui sopra" : "nessuna colonna facoltativa nel file"}`
          + (parti.length ? `; dalla visura (EuGEnio Visure, non sostituisce la visura ufficiale): ${parti.join(", ")}.` : ".")
          + " Precedenza: file → visura → stima.";
      }
    }
  }
  async function scegli(edificio, lon, lat, sede = null) {
    impostaSede(sede);
    messaggio("messaggio", "Carico gli edifici nel raggio di 250 m…");
    stato.proj = E.proiezione(lon, lat);
    const fs = await contesto(lon, lat);
    const tutti = fs.map((f) => conFalde(aCorpo(f), f.properties));
    const corpi = tutti.filter((c) => c.edificio === edificio);
    if (!corpi.length) { messaggio("messaggio", "Edificio non trovato nell'archivio.", true); return false; }
    terrenoDi(corpi[0].archivio);
    // edificio OSM (ripiego, nessun DTM): tutto sullo stesso piano, anche i corpi DBTR vicini oltre il confine del comune
    const daOsm = (archivioDi(corpi[0]) || {}).osm;
    // sagome regionali con la quota dal DTM del server (08/11/2026): terreno vero; altrimenti tutto sullo stesso piano
    const conQuota = daOsm && corpi.every((c) => c.quotaNota);
    if (daOsm && !conQuota) tutti.forEach((c) => { c.quota = 0; });
    else if (conQuota) { const q = Math.min(...corpi.map((c) => c.quota)); tutti.forEach((c) => { if (!c.quotaNota) c.quota = q; }); }
    const centro = E.centroide(corpi[0].ring);
    stato.vicini = tutti.filter((c) => c.edificio !== edificio && Math.hypot(...E.centroide(c.ring).map((v, i) => v - centro[i])) <= RAGGIO + 60);
    stato.modello = null; stato.nascostiExtra = [];
    stato.corpi = corpi; stato.edificio = edificio;
    stato.aree = []; stato.firma = null; stato.fv = null; stato.sintetico = corpi.some((c) => c.sintetico);
    stato.q0 = Math.min(...corpi.map((c) => c.quota || 0)); stato.lontano = null; stato.facciate = null; stato.pvgis = null;
    stato.fvOrizzonti = {}; mostraFacciate();
    // comune del punto (07/11/2026: confini di tutta Italia, serve anche fuori dall'Emilia-Romagna con il ripiego OSM)
    stato.comune = daOsm ? await comuneNelPunto(lon, lat) : await comuneDi(lon, lat);
    // forma dei tetti (08/11/2026): con il comune (soglia di montagna 600/700 m, altitudine del comune per i corpi senza quota)
    await datiDpr();
    preparaSelettoreTetti(true); applicaTetti();
    stato.originali = corpi.map((c) => ({ ...c, ring: c.ring.map((p) => [...p]) }));
    $("avviso-sintetico").hidden = !stato.sintetico;
    ["passo-corpi", "passo-superfici", "passo-geometria", "passo-obblighi", "passo-ombre", "passo-facciate", "passo-fv", "passo-pvgis",
      "passo-consumi", "passo-report"].forEach((id) => { $(id).hidden = false; });
    $("aggiungi-priorita").disabled = false; $("calcola-pvgis").disabled = true;
    messaggio("messaggio", `Edificio ${edificio}: ${corpi.length} ${corpi.length === 1 ? "corpo" : "corpi"}, ${stato.vicini.length} corpi vicini.`
      + (stato.comune ? ` Comune: ${stato.comune.nome}.` : "") + (daOsm ? avvisoOsm(corpi[0].archivio) + (conQuota ? " Quote dei corpi dal terreno del server (DTM regionale o, dove manca, Copernicus DEM 90 m)." : " Quote del terreno non disponibili: edifici sullo stesso piano.") : ""));
    aggiorna();
    if (!DUE_TEMPI) stato.mappa.easeTo({ center: [lon, lat], zoom: 17.6, duration: 600 });
    apriVista();
    fontiCorpi();
    if (DUE_TEMPI) { stato.daGenerare = { edificio, lon, lat, sede }; evidenzia2d(edificio); }
    return true;
  }

  // edificio dell'archivio che contiene il punto (lon, lat); se nessuno lo contiene, il più vicino entro 30 m
  // (un punto in un cortile non è contenuto; la distanza conta anche dai lati dei cortili)
  function edificioNelPunto(fs, lon, lat) {
    const pr = E.proiezione(lon, lat);
    let vicino = null, dmin = 30;
    for (const f of fs) {
      const [esterno, ...fori] = anelli(f.geometry);
      if (!esterno) continue;
      const c = { ring: esterno.map(pr.avanti), buchi: fori.map((r) => r.map(pr.avanti)) };
      if (E.dentroCorpo([0, 0], c)) return f;
      for (const [a, b] of E.latiCorpo(c)) {
        const ex = b[0] - a[0], ey = b[1] - a[1], l2 = ex * ex + ey * ey || 1;
        const t = Math.max(0, Math.min(1, -(a[0] * ex + a[1] * ey) / l2)), d = Math.hypot(a[0] + t * ex, a[1] + t * ey);
        if (d < dmin) { dmin = d; vicino = f; }
      }
    }
    return vicino;
  }

  // comune che contiene il punto (confini ISTAT del sito, dati/mappa/08.json, stesse coordinate di patrimonio.js)
  async function comuneDi(lon, lat) {
    try {
      const m = await json("dati/mappa/08.json?v=20261109b");
      const p = lonlatSvg(lon, lat);
      for (const c of m.comuni) {
        for (const parte of c.d.split("M").filter(Boolean)) {
          const r = parte.replace(/Z/g, "").split("L").map((x) => x.split(",").map(Number));
          if (E.dentro(p, r)) return { istat: c.istat, nome: c.nome };
        }
      }
    } catch { /* senza confini: niente clima */ }
    return null;
  }
  function lonlatSvg(lon, lat) {   // stessa trasformazione di patrimonio.js (UTM 32N con la scala dei file di mappa)
    const k0 = 0.9996, a = 6378137, f = 1 / 298.257223563, e2 = f * (2 - f), ep2 = e2 / (1 - e2);
    const fi = lat * Math.PI / 180, l = (lon - 9) * Math.PI / 180;
    const N = a / Math.sqrt(1 - e2 * Math.sin(fi) ** 2), T = Math.tan(fi) ** 2, C = ep2 * Math.cos(fi) ** 2, A = Math.cos(fi) * l;
    const M = a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * fi - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * Math.sin(2 * fi)
      + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * Math.sin(4 * fi) - (35 * e2 ** 3 / 3072) * Math.sin(6 * fi));
    const Ee = 500000 + k0 * N * (A + (1 - T + C) * A ** 3 / 6 + (5 - 18 * T + T ** 2 + 72 * C - 58 * ep2) * A ** 5 / 120);
    const No = k0 * (M + N * Math.tan(fi) * (A ** 2 / 2 + (5 - T + 9 * C + 4 * C ** 2) * A ** 4 / 24 + (61 - 58 * T + T ** 2 + 600 * C - 330 * ep2) * A ** 6 / 720));
    const S = 0.0010012596459353985;
    return [S * Ee - 313.67365575107954, -S * No + 5226.851664605516];
  }

  // ------------------------------------------------------------------ corpi: tabella e correzioni
  function aggiorna() {
    tabellaCorpi(); tabellaFalde(); schedaEdificio(); superfici(); geometria(); obblighi(); ridisegna();
    $("calcola-fv").disabled = !stato.aree.length;
  }
  function campo(c, chiave, passo, min) {
    const i = h("input"); i.type = "number"; i.step = passo; i.min = min; i.value = c[chiave] === null ? "" : c[chiave];
    i.setAttribute("aria-label", `${chiave} del corpo ${c.id}`);
    i.addEventListener("change", () => {
      const v = E.numero(i.value);
      c[chiave] = v === null ? null : v;
      if (chiave === "colmo") c.tetto = c.colmo && c.colmo > c.gronda ? (c.tetto === "piano" ? "capanna" : c.tetto) : "piano";
      c.fonte_altezza = "dato dell'utente"; c.modificato = true;
      if (chiave !== "piani") { c.falde = null; if (c.tetto !== "piano") stimaTetto(c, "tetto stimato dai valori inseriti", c.tetto); }   // le falde misurate non valgono più
      aggiorna();
    });
    return i;
  }
  function tabellaCorpi() {
    const t = $("tabella-corpi"); t.innerHTML = "";
    const r1 = t.createTHead().insertRow();
    ["Corpo", "Area (m²)", "Gronda (m)", "Colmo (m)", "Tetto", "Piani", "Fonte"].forEach((x, k) => r1.appendChild(h("th", k && k < 6 ? "num" : null, x)));
    const corpo = t.createTBody();
    stato.corpi.forEach((c) => {
      const r = corpo.insertRow();
      r.appendChild(h("th", null, c.id));
      r.appendChild(h("td", "num", fmt(E.areaCorpo(c))));
      const g = h("td", "num"); g.appendChild(campo(c, "gronda", 0.5, 0.5)); r.appendChild(g);
      const k = h("td", "num"); k.appendChild(campo(c, "colmo", 0.5, 0)); r.appendChild(k);
      const tt = h("td"); const s = h("select");
      [["piano", "piano"], ["monofalda", "a una falda"], ["capanna", "a capanna"], ["padiglione", "a padiglione"]].forEach(([v, n]) => { const o = h("option", null, n); o.value = v; o.selected = c.tetto === v; s.appendChild(o); });
      s.setAttribute("aria-label", `Tetto del corpo ${c.id}`);
      s.addEventListener("change", () => {
        c.tetto = s.value;
        if (c.tetto === "piano") c.colmo = null; else if (!c.colmo || c.colmo <= c.gronda) c.colmo = c.gronda + 3;
        c.modificato = true; c.fonte_altezza = "dato dell'utente"; c.falde = null;
        if (c.tetto !== "piano") stimaTetto(c, "tetto stimato dai valori inseriti", c.tetto);
        aggiorna();
      });
      tt.appendChild(s); r.appendChild(tt);
      const p = h("td", "num"); p.appendChild(campo(c, "piani", 1, 1)); r.appendChild(p);
      const f = h("td", "fonte"); f.append(testoAltezza(c) || "—"); f.appendChild(h("small", null, `${c.fonte_sagoma} · ${c.licenza}`)); r.appendChild(f);
    });
  }
  function tabellaFalde() {
    const box = $("falde-tetti"); if (!box) return;
    const t = $("tabella-falde"); t.innerHTML = "";
    const con = stato.corpi.filter((c) => c.falde && c.falde.length);
    const note = [];
    stato.corpi.forEach((c) => {
      if (c.lidar && c.lidar.stato !== "ok") note.push(`corpo ${c.id}: ${c.lidar.stato} (resta l'altezza del DBTR)`);
      (c.lidar && c.lidar.note || []).forEach((n) => note.push(`corpo ${c.id}: ${n}`));
    });
    if (!con.length) {
      messaggio("messaggio-falde", (stato.lidar ? "Nessuna falda misurata per questo edificio" : "Nessun rilievo LiDAR in questo archivio")
        + `: tetti piani. ${testoTetti()}` + (note.length ? ` ${note.join("; ")}.` : ""));
      return;
    }
    const r1 = t.createTHead().insertRow();
    ["Corpo", "Falda", "Pendenza (°)", "Orientamento (°)", "Superficie (m²)", "In pianta (m²)", "Fonte"].forEach((x, k) => r1.appendChild(h("th", k > 1 && k < 6 ? "num" : null, x)));
    const b = t.createTBody();
    con.forEach((c) => c.falde.forEach((f) => {
      const r = b.insertRow();
      r.appendChild(h("th", null, c.id)); r.appendChild(h("td", null, f.id));
      r.appendChild(h("td", "num", fmt(f.pendenza, 1)));
      r.appendChild(h("td", "num", f.pendenza < 5 ? "— (piano)" : `${fmt(f.orientamento)} ${E.SETTORI[Math.floor(((f.orientamento + 22.5) % 360) / 45)]}`));
      r.appendChild(h("td", "num", fmt(f.superficie))); r.appendChild(h("td", "num", fmt(f.area_pianta)));
      r.appendChild(h("td", "fonte", f.fonte + (c.lidar && c.lidar.qualita ? ` · qualità ${c.lidar.qualita}` : "")));
    }));
    const sint = con.some((c) => c.lidar && c.lidar.sintetico), ts = testoTettiStimati();
    messaggio("messaggio-falde", `${con.reduce((s, c) => s + c.falde.length, 0)} falde in ${con.length} ${con.length === 1 ? "corpo" : "corpi"}`
      + (sint ? " dal rilievo LiDAR sintetico di esempio (inventato)." : ".") + ` ${testoTetti()}` + (ts ? ` ${ts}` : "")
      + (note.length ? ` ${note.join("; ")}.` : ""), sint);
  }
  function schedaEdificio() {
    const d = $("scheda-edificio"); d.hidden = false; d.innerHTML = "";
    const c0 = stato.corpi.find((c) => c.nome || c.foglio || c.destinazione) || {};
    const voci = [["Edificio", c0.nome ? `${c0.nome} (${stato.edificio})` : stato.edificio], ["Comune", stato.comune ? stato.comune.nome : "—"],
      ...(c0.foglio || c0.numero ? [["Foglio e numero (DBTR)", [c0.foglio && `foglio ${c0.foglio}`, c0.numero && `numero ${c0.numero}`].filter(Boolean).join(", ")]] : []),
      ...(c0.destinazione ? [["Destinazione d'uso (DBTR)", c0.destinazione]] : []),
      ["Corpi", stato.corpi.length], ["Licenza delle sagome", [...new Set(stato.corpi.map((c) => c.licenza))].join(", ")]];
    voci.forEach(([k, v]) => { d.appendChild(h("dt", null, k)); d.appendChild(h("dd", null, String(v))); });
  }

  // divisione di un corpo con una linea (due clic)
  function puntoDivisione(p) {
    stato.punti.push(p);
    const linea = stato.punti.map(stato.proj.indietro);
    stato.mappa.getSource("linea").setData({ type: "Feature", geometry: { type: linea.length > 1 ? "LineString" : "Point", coordinates: linea.length > 1 ? linea : linea[0] } });
    if (stato.punti.length < 2) return;
    const [a, b] = stato.punti;
    let fatto = false;
    stato.corpi = stato.corpi.flatMap((c) => {
      if (fatto) return [c];
      const parti = E.dividi(c.ring, a, b);
      if (!parti) return [c];
      fatto = true;
      // i cortili restano nella parte che contiene il loro centro (un cortile tagliato dalla linea si approssima così)
      return parti.map((r, k) => ({ ...c, id: `${c.id}.${k + 1}`, ring: r, buchi: (c.buchi || []).filter((b) => E.dentro(E.centroide(b), r)),
        modificato: true, falde: null, fonte_sagoma: `${c.fonte_sagoma} (divisa dall'utente)` }));
    });
    finisciModo();
    messaggio("messaggio", fatto ? "Corpo diviso: ora dai a ciascuna parte la sua altezza." : "La linea non attraversa nessun corpo dell'edificio.", !fatto);
    aggiorna();
  }
  function finisciModo() {
    stato.modo = null; stato.punti = [];
    $("dividi").setAttribute("aria-pressed", "false"); $("aggiungi-fv").setAttribute("aria-pressed", "false"); $("aiuto-dividi").hidden = true;
    if (stato.mappa) stato.mappa.getSource("linea").setData({ type: "FeatureCollection", features: [] });
  }
  $("dividi").addEventListener("click", () => {
    if (stato.modo === "dividi") return finisciModo();
    finisciModo(); stato.modo = "dividi"; $("dividi").setAttribute("aria-pressed", "true"); $("aiuto-dividi").hidden = false;
  });
  $("ripristina").addEventListener("click", () => {
    stato.corpi = stato.originali.map((c) => ({ ...c, ring: c.ring.map((p) => [...p]), buchi: (c.buchi || []).map((b) => b.map((p) => [...p])) })); stato.aree = [];
    stato.corpi.forEach((c) => { if (c.base) c.modificato = false; applicaTetto(c); }); aggiorna(); fontiCorpi();
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && stato.modo) finisciModo(); });

  // ------------------------------------------------------------------ piani e superfici
  function superfici() {
    const vis = stato.visura || {};
    const corpi = stato.corpi.map((c) => ({ ...c, uso: stato.uso || vis.uso || c.uso || "altro" }));
    const s = E.superfici(corpi, stato.csv, vis);
    stato.superfici = s;
    const box = $("superfici"); box.innerHTML = "";
    const t = h("table", "totali"); const b = t.createTBody();
    for (const k of Object.keys(E.ETICHETTE)) {
      const v = s[k], r = b.insertRow();
      r.appendChild(h("th", null, E.ETICHETTE[k]));
      const unita = /superficie/.test(k) ? " m²" : "";
      r.appendChild(h("td", "num", v.valore === null ? "—" : fmt(v.valore, 0) + unita));
      r.appendChild(h("td", "fonte", NOMI_FONTE[v.fonte] || v.fonte));
    }
    box.appendChild(t);
  }
  for (const k of Object.keys(E.FACOLTATIVE)) {
    const i = $(`csv-${k}`);
    if (i) i.addEventListener("change", () => { const v = E.numero(i.value); if (v === null) delete stato.csv[k]; else stato.csv[k] = v; if (stato.edificio) aggiorna(); });
  }
  $("uso").addEventListener("change", () => { stato.uso = $("uso").value; if (stato.edificio) aggiorna(); });

  // ------------------------------------------------------------------ indicatori geometrici
  function geometria() {
    const g = E.indicatori(stato.corpi, stato.vicini);
    stato.geometria = g;
    const box = $("geometria"); box.innerHTML = "";
    const t = h("table", "totali"); const b = t.createTBody();
    [["Volume lordo", g.volume_lordo, "m³", 0], ["Superficie disperdente", g.superficie_disperdente, "m²", 0], ["Rapporto S/V", g.s_su_v, "m⁻¹", 2],
      ["Tetti", g.superficie_tetti, "m²", 0], ["Pavimento a terra", g.superficie_pavimento_terra, "m²", 0], ["Pareti esposte", g.pareti_esposte, "m²", 0],
      ["Pareti in comune tra corpi", g.pareti_in_comune_tra_corpi, "m²", 0], ["Pareti in comune con edifici vicini", g.pareti_in_comune_con_vicini, "m²", 0]]
      .forEach(([n, v, u, d]) => { const r = b.insertRow(); r.appendChild(h("th", null, n)); r.appendChild(h("td", "num", `${fmt(v, d)} ${u}`)); });
    box.appendChild(t);
    if (G) G.registra($("grafico-orientamenti"), (dest, mis) => disegnaRosa(dest, mis, g.pareti_per_orientamento), { titolo: "Pareti esposte per orientamento" });
  }
  function svgEl(tag, a, p) { const e = document.createElementNS("http://www.w3.org/2000/svg", tag); for (const [k, v] of Object.entries(a)) { if ((k === "fill" || k === "stroke") && String(v).startsWith("var(")) e.style.setProperty(k, v); else e.setAttribute(k, v); } if (p) p.appendChild(e); return e; }
  function disegnaRosa(dest, mis, po) {
    const W = mis && mis.riquadro ? mis.larghezza : 520, H = mis && mis.riquadro ? mis.altezza : 220;
    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Pareti esposte per orientamento" }, dest);
    const sx = 44, gi = 26, su = 12, n = E.SETTORI.length, passo = (W - sx - 8) / n, max = Math.max(1, ...Object.values(po));
    const Y = (v) => su + (H - su - gi) * (1 - v / max);
    svgEl("line", { x1: sx, x2: W - 8, y1: Y(0), y2: Y(0), stroke: "var(--linea)" }, svg);
    const punti = E.SETTORI.map((s, i) => {
      const x = sx + passo * (i + 0.5), v = po[s] || 0;
      const r = svgEl("rect", { x: x - passo * 0.3, y: Y(v), width: passo * 0.6, height: Y(0) - Y(v), fill: "var(--primario)" }, svg);
      const t = svgEl("text", { x, y: H - 8, "text-anchor": "middle", "font-size": 12, fill: "var(--tenue)" }, svg); t.textContent = s;
      return { x, titolo: `Pareti esposte a ${s}`, elementi: [r], righe: [["var(--primario)", `${fmt(v)} m²`]] };
    });
    const t = svgEl("text", { x: 4, y: su + 4, "font-size": 12, fill: "var(--tenue)" }, svg); t.textContent = `${fmt(max)} m²`;
    if (G) G.osserva(svg, punti, { area: [sx, su, W - 8, H - gi], guida: false });
  }

  // ------------------------------------------------------------------ ombre animate
  function dataScelta() {
    const g = $("giorno").value || new Date().toISOString().slice(0, 10), m = +$("ora").value;
    const [a, me, gi] = g.split("-").map(Number);
    // ora italiana → UTC (ora legale dall'ultima domenica di marzo all'ultima di ottobre)
    const ultimaDom = (anno, mese) => { const d = new Date(Date.UTC(anno, mese + 1, 0)); return d.getUTCDate() - d.getUTCDay(); };
    const legale = (me > 3 && me < 10) || (me === 3 && gi >= ultimaDom(a, 2)) || (me === 10 && gi < ultimaDom(a, 9));
    return new Date(Date.UTC(a, me - 1, gi, 0, m) - (legale ? 2 : 1) * 3600000);
  }
  function ombre() {
    if (!stato.mappa || !stato.proj || !stato.edificio) return;
    const [lon, lat] = stato.proj.indietro([0, 0]);
    const s = E.sole(dataScelta(), lat, lon);
    const tutti = [...stato.corpi, ...stato.vicini, ...alberiVicini().map((a) => ({ ring: a.ring, gronda: a.h }))];
    const feats = s.altezza > 0.5 ? tutti.map((c) => E.ombra(c.ring, c.colmo || c.gronda, s)).filter(Boolean).map((r) => ({ type: "Feature", properties: {},
      geometry: { type: "Polygon", coordinates: [r.map(stato.proj.indietro)] } })) : [];
    stato.mappa.getSource("ombre").setData({ type: "FeatureCollection", features: feats });
    const m = +$("ora").value;
    $("sole").textContent = s.altezza > 0
      ? `Ore ${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")} – sole a ${fmt(s.azimut)}° da nord, ${fmt(s.altezza, 1)}° sull'orizzonte.`
      : `Ore ${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")} – il sole è sotto l'orizzonte.`;
    try { stato.mappa.setLight({ anchor: "map", position: [1.5, (s.azimut + 180) % 360, Math.max(10, 90 - Math.max(0, s.altezza))], intensity: 0.5 }); } catch { /* luce non supportata */ }
  }
  $("giorno").value = new Date().toISOString().slice(0, 10);
  $("ora").value = 12 * 60;
  $("giorno").addEventListener("input", ombre); $("ora").addEventListener("input", ombre);
  $("anima").addEventListener("click", () => {
    const b = $("anima");
    if (stato.anima) { clearInterval(stato.anima); stato.anima = null; b.setAttribute("aria-pressed", "false"); b.textContent = "▶ Ciclo del giorno"; return; }
    b.setAttribute("aria-pressed", "true"); b.textContent = "❚❚ Ferma";
    stato.anima = setInterval(() => { $("ora").value = (+$("ora").value + 15) % 1440; ombre(); }, 120);
  });

  // ------------------------------------------------------------------ aree FV
  function latiModulo() {
    const v = $("modulo-lati").value.split(/[x×*]/i).map(E.numero).filter((x) => x > 0);
    return v.length === 2 ? v : [1.13, 1.72];
  }
  // rettangolo massimo allineato al lato più lungo del corpo, ridotto della fascia di rispetto
  // area FV su una falda misurata: rettangolo lungo le curve di livello della falda, inclinazione e orientamento della falda
  function areaSuFalda(c, f, fascia) {
    const az = f.orientamento * Math.PI / 180, d = [Math.sin(az), Math.cos(az)], u = [d[1], -d[0]];
    const pts = E.chiudi(f.ring).slice(0, -1);
    const s = pts.map((q) => q[0] * u[0] + q[1] * u[1]), t = pts.map((q) => q[0] * d[0] + q[1] * d[1]);
    const s0 = Math.min(...s) + fascia, s1 = Math.max(...s) - fascia, t0 = Math.min(...t) + fascia, t1 = Math.max(...t) - fascia;
    if (s1 - s0 < 1 || t1 - t0 < 1) return null;
    const P = (ss, tt) => [ss * u[0] + tt * d[0], ss * u[1] + tt * d[1]];
    const ring = [P(s0, t0), P(s1, t0), P(s1, t1), P(s0, t1)];
    const fuori = ring.some((q) => !E.dentro(q, f.ring));
    const piano = f.pendenza < 5, quota = Number.isFinite(f.alto) && Number.isFinite(f.basso) ? (f.alto + f.basso) / 2 : c.gronda;
    return { id: `A${stato.aree.length + 1}`, corpo: c.id, falda: f.id, ring: E.chiudi(ring), quota, fuori,
      inclinazione: piano ? 10 : Math.round(f.pendenza), orientamento: piano ? 180 : Math.round(f.orientamento),
      montaggio: piano ? "telai" : "aderente", fonte: f.fonte };
  }
  function aggiungiArea(p) {
    const c = stato.corpi.find((x) => E.dentroCorpo(p, x));
    if (!c) { messaggio("messaggio-fv", "Fai clic sul tetto di un corpo dell'edificio scelto.", true); return; }
    const fascia = Math.max(0, E.numero($("fascia").value) || 0);
    const falda = (c.falde || []).find((f) => E.dentro(p, f.ring));
    if (falda) {
      const a = areaSuFalda(c, falda, fascia);
      if (!a) { messaggio("messaggio-fv", "La falda è troppo piccola per un'area con questa fascia di rispetto.", true); return; }
      stato.aree.push(a);
      finisciModo(); tabellaFv(); ridisegna(); $("calcola-fv").disabled = false;
      messaggio("messaggio-fv", `Area aggiunta sulla falda ${falda.id} del corpo ${c.id} (${falda.fonte}): inclinazione ${a.inclinazione}°, orientamento ${a.orientamento}°`
        + (a.fuori ? ". La falda non è rettangolare: controlla che l'area stia sul tetto." : "."));
      return;
    }
    const lati = E.lati(c.ring).sort((x, y) => Math.hypot(y[1][0] - y[0][0], y[1][1] - y[0][1]) - Math.hypot(x[1][0] - x[0][0], x[1][1] - x[0][1]));
    const [a, b] = lati[0], L = Math.hypot(b[0] - a[0], b[1] - a[1]), ux = (b[0] - a[0]) / L, uy = (b[1] - a[1]) / L;
    const pts = E.chiudi(c.ring).slice(0, -1);
    const s = pts.map((q) => q[0] * ux + q[1] * uy), t = pts.map((q) => -q[0] * uy + q[1] * ux);
    const s0 = Math.min(...s) + fascia, s1 = Math.max(...s) - fascia, t0 = Math.min(...t) + fascia, t1 = Math.max(...t) - fascia;
    if (s1 - s0 < 1 || t1 - t0 < 1) { messaggio("messaggio-fv", "Il tetto è troppo piccolo per un'area con questa fascia di rispetto.", true); return; }
    const P = (ss, tt) => [ss * ux - tt * uy, ss * uy + tt * ux];
    let ring = [P(s0, t0), P(s1, t0), P(s1, t1), P(s0, t1)];
    // sagome non rettangolari: si tengono solo i vertici dentro il corpo (la pagina lo dice)
    const fuori = ring.some((q) => !E.dentroCorpo(q, c));
    ring = E.chiudi(ring);
    const piano = c.tetto === "piano" || !c.colmo;
    // falda verso sud: normale del lato più lungo più vicina al sud
    const az = (Math.atan2(uy, -ux) * 180 / Math.PI + 360) % 360, verso = Math.abs(((az - 180 + 540) % 360) - 180) < 90 ? az : (az + 180) % 360;
    const semi = Math.max((t1 - t0) / 2, 0.5), incl = piano ? 10 : Math.atan(((c.colmo || c.gronda) - c.gronda) / semi) * 180 / Math.PI;
    const area = { id: `A${stato.aree.length + 1}`, corpo: c.id, ring, quota: c.colmo && !piano ? (c.gronda + c.colmo) / 2 : c.gronda,
      inclinazione: Math.round(incl), orientamento: Math.round(piano ? 180 : verso), montaggio: piano ? "telai" : "aderente", fuori };
    stato.aree.push(area);
    finisciModo(); tabellaFv(); ridisegna(); $("calcola-fv").disabled = false;
    messaggio("messaggio-fv", fuori ? "Area aggiunta: la sagoma del corpo non è rettangolare, controlla che il rettangolo stia sul tetto." : "Area aggiunta.");
  }
  function conteggio(a) {
    const [w, l] = latiModulo(), A = E.area(a.ring);
    // telai su tetto piano: file distanziate per non farsi ombra al solstizio d'inverno a mezzogiorno (sole a ~22,5°)
    const occupazione = a.montaggio === "telai" ? (l * Math.cos(a.inclinazione * Math.PI / 180) + l * Math.sin(a.inclinazione * Math.PI / 180) / Math.tan(22.5 * Math.PI / 180)) / l : 1 / Math.cos(0);
    const moduli = Math.max(0, Math.floor(A / (w * l * occupazione)));
    return { area: A, moduli, kwp: moduli * (E.numero($("modulo-w").value) || 430) / 1000 };
  }
  function tabellaFv() {
    const t = $("tabella-fv"); t.innerHTML = "";
    if (!stato.aree.length) { obblighi(); return; }
    const r1 = t.createTHead().insertRow();
    ["Area", "Corpo", "m²", "Inclinazione (°)", "Orientamento (°)", "Montaggio", "Moduli", "kWp", "kWh/anno", "Ombre", ""].forEach((x) => r1.appendChild(h("th", null, x)));
    const b = t.createTBody();
    stato.aree.forEach((a, k) => {
      const c = conteggio(a), r = b.insertRow(), ris = stato.fv && stato.fv.find((x) => x.id === a.id);
      r.appendChild(h("th", null, a.id)); r.appendChild(h("td", null, a.falda ? `${a.corpo} · ${a.falda}` : a.corpo)); r.appendChild(h("td", "num", fmt(c.area)));
      for (const kk of ["inclinazione", "orientamento"]) {
        const td = h("td", "num"), i = h("input"); i.type = "number"; i.value = a[kk]; i.min = 0; i.max = kk === "inclinazione" ? 90 : 359;
        i.setAttribute("aria-label", `${kk} dell'area ${a.id}`);
        i.addEventListener("change", () => { a[kk] = E.numero(i.value) || 0; a.manuale = true; stato.fv = null; tabellaFv(); });
        td.appendChild(i); r.appendChild(td);
      }
      const tm = h("td"), sm = h("select");
      [["telai", "su telai"], ["aderente", "aderente"]].forEach(([v, n]) => { const o = h("option", null, n); o.value = v; o.selected = a.montaggio === v; sm.appendChild(o); });
      sm.addEventListener("change", () => { a.montaggio = sm.value; a.manuale = true; stato.fv = null; tabellaFv(); });
      tm.appendChild(sm); r.appendChild(tm);
      r.appendChild(h("td", "num", fmt(c.moduli))); r.appendChild(h("td", "num", fmt(c.kwp, 2)));
      r.appendChild(h("td", "num", ris ? fmt(ris.kwh) : "—")); r.appendChild(h("td", "num", ris ? `−${fmt(ris.perdita, 1)} %` : "—"));
      const tx = h("td"), x = h("button", "filtro", "Togli"); x.type = "button";
      x.addEventListener("click", () => { stato.aree.splice(k, 1); stato.fv = null; tabellaFv(); ridisegna(); $("calcola-fv").disabled = !stato.aree.length; });
      tx.appendChild(x); r.appendChild(tx);
    });
    obblighi();
  }
  $("aggiungi-fv").addEventListener("click", () => {
    if (stato.modo === "fv") return finisciModo();
    finisciModo(); stato.modo = "fv"; $("aggiungi-fv").setAttribute("aria-pressed", "true");
    messaggio("messaggio-fv", "Fai clic sul tetto di un corpo.");
  });

  let lavoratore = null;
  function orizzonti(punti, ostacoli, lontano = null) {
    return new Promise((ok, ko) => {
      try { lavoratore = lavoratore || new Worker("ombre_worker.js?v=20261109b"); } catch (e) { ko(e); return; }
      const id = Math.random();
      const f = (e) => { if (e.data.id === id) { lavoratore.removeEventListener("message", f); ok(e.data.orizzonti); } };
      lavoratore.addEventListener("message", f);
      lavoratore.onerror = (e) => ko(e);
      lavoratore.postMessage({ id, punti, ostacoli, direzioni: 72, lontano });
    });
  }
  function campioni(a, n = 3) {
    const pts = E.chiudi(a.ring).slice(0, -1), out = [];
    for (let i = 1; i <= n; i++) for (let j = 1; j <= n; j++) {
      const u = i / (n + 1), v = j / (n + 1);
      const x = (1 - u) * (1 - v) * pts[0][0] + u * (1 - v) * pts[1][0] + u * v * pts[2][0] + (1 - u) * v * pts[3][0];
      const y = (1 - u) * (1 - v) * pts[0][1] + u * (1 - v) * pts[1][1] + u * v * pts[2][1] + (1 - u) * v * pts[3][1];
      out.push([x, y, a.quota + rel(stato.corpi.find((c) => c.id === a.corpo)) + 0.5]);
    }
    return out;
  }
  async function clima() {
    const [lon, lat] = stato.proj.indietro([0, 0]);
    if (stato.comune) {
      try {
        const r = await fetch(`/api/edifici/clima-orario/${stato.comune.istat}`);
        if (r.ok && /json/.test(r.headers.get("Content-Type") || "")) { const d = await r.json(); return { ...d, sintetico: false }; }
      } catch { /* server non raggiungibile */ }
    }
    return E.climaSintetico(new Date().getUTCFullYear() - 1, lat, lon);
  }
  $("calcola-fv").addEventListener("click", async () => {
    const b = $("calcola-fv"); b.disabled = true;
    try {
      messaggio("messaggio-fv", "Calcolo il profilo d'orizzonte dei punti delle aree (edifici entro 250 m)…");
      const ostacoli = ostacoliRelativi();
      const lont = await orizzonteLontano();
      const aree = [];
      for (const a of stato.aree) {
        const oz = await orizzonti(campioni(a), ostacoli, lont);
        stato.fvOrizzonti[a.id] = oz[0].map((_, k) => oz.reduce((s, h) => s + h[k], 0) / oz.length);   // media dei punti, per PVGIS
        aree.push({ id: a.id, inclinazione: a.inclinazione, orientamento: a.orientamento, kwp: conteggio(a).kwp, orizzonti: oz });
      }
      const cl = await clima();
      const [lon, lat] = stato.proj.indietro([0, 0]);
      messaggio("messaggio-fv", "Calcolo la producibilità ora per ora…");
      await new Promise((ok) => setTimeout(ok, 20));
      stato.fv = E.producibilita(cl, lat, lon, aree);
      stato.fvClima = cl;
      tabellaFv();
      const tot = stato.fv.reduce((s, x) => s + x.kwh, 0);
      messaggio("messaggio-fv", `Producibilità totale: ${fmt(tot)} kWh/anno` + (cl.sintetico
        ? ". Attenzione: il clima orario del comune non è ancora sul server, il calcolo usa un anno di cielo sereno ridotto (sintetico): è solo una prova."
        : ` con il clima orario del ${cl.anno} di ${cl.comune}.`) + (lont ? " Orizzonte: edifici entro 250 m e terreno fino a 25 km."
        : " Orizzonte: solo edifici entro 250 m (il terreno lontano non è disponibile ora).") + ` ${testoSceltaTetti()}`, !!cl.sintetico);
      $("calcola-pvgis").disabled = false; stato.pvgis = null; $("pvgis").innerHTML = ""; messaggio("messaggio-pvgis", "");
      if (G) G.registra($("grafico-fv"), (dest, mis) => disegnaMensile(dest, mis), { titolo: "Producibilità mensile" });
    } catch (e) {
      console.warn(e); messaggio("messaggio-fv", `Calcolo non riuscito: ${e.message || e}`, true);
    } finally { b.disabled = !stato.aree.length; }
  });
  const MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"];
  function disegnaMensile(dest, mis) {
    const W = mis && mis.riquadro ? mis.larghezza : 520, H = mis && mis.riquadro ? mis.altezza : 220;
    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Producibilità mensile" }, dest);
    const v = MESI.map((m, i) => stato.fv.reduce((s, x) => s + x.mensile[i], 0)), max = Math.max(1, ...v);
    const sx = 50, gi = 26, su = 12, passo = (W - sx - 8) / 12, Y = (x) => su + (H - su - gi) * (1 - x / max);
    const punti = v.map((x, i) => {
      const cx = sx + passo * (i + 0.5);
      const r = svgEl("rect", { x: cx - passo * 0.3, y: Y(x), width: passo * 0.6, height: Y(0) - Y(x), fill: "var(--serie-3)" }, svg);
      const t = svgEl("text", { x: cx, y: H - 8, "text-anchor": "middle", "font-size": 12, fill: "var(--tenue)" }, svg); t.textContent = MESI[i];
      return { x: cx, titolo: MESI[i], elementi: [r], righe: [["var(--serie-3)", `${fmt(x)} kWh`]] };
    });
    const t = svgEl("text", { x: 4, y: su + 4, "font-size": 12, fill: "var(--tenue)" }, svg); t.textContent = `${fmt(max)} kWh`;
    if (G) G.osserva(svg, punti, { area: [sx, su, W - 8, H - gi], guida: false });
  }

  // ------------------------------------------------------------------ consumi e firma energetica
  function leggiConsumi(testo) {
    return testo.split(/\r?\n/).map((r) => r.trim()).filter((r) => r && !/^mese/i.test(r)).map((r) => {
      const [m, v] = r.split(/[;,\t]/);
      return { mese: (m || "").trim().slice(0, 7), consumo: E.numero(v) };
    }).filter((x) => /^\d{4}-\d{2}$/.test(x.mese) && x.consumo !== null);
  }
  $("esempio-consumi").addEventListener("click", async () => {
    try {
      const d = await json(`${stato.base || "dati/edifici3d/"}consumi_esempio.json`);
      $("consumi").value = d.mesi.map((m) => `${m.mese};${m.gas_smc}`).join("\n");
      stato.consumiSintetici = d.mesi;
      messaggio("messaggio-firma", "Consumi sintetici di esempio, inventati: servono solo a provare la pagina.");
    } catch { messaggio("messaggio-firma", "Consumi di esempio non disponibili.", true); }
  });
  $("calcola-firma").addEventListener("click", async () => {
    const consumi = leggiConsumi($("consumi").value);
    if (consumi.length < 3) { messaggio("messaggio-firma", "Servono almeno tre mesi di consumi (2025-01;4170).", true); return; }
    let gg = null, fonte = "";
    if (stato.comune) {
      try {
        const r = await fetch(`/api/edifici/gradi-giorno/${stato.comune.istat}?dal=${consumi[0].mese}&al=${consumi[consumi.length - 1].mese}`);
        if (r.ok && /json/.test(r.headers.get("Content-Type") || "")) { const d = await r.json(); gg = new Map(d.mesi.map((m) => [m.mese, m.gg20])); fonte = d.fonte; }
      } catch { /* server non raggiungibile */ }
    }
    let sintetici = false;
    if (!gg && stato.consumiSintetici) {   // solo per i consumi d'esempio: i loro gradi giorno, anch'essi sintetici
      gg = new Map(stato.consumiSintetici.map((m) => [m.mese, m.gg_esempio])); sintetici = true;
    }
    if (!gg) { messaggio("messaggio-firma", "I gradi giorno reali del comune non sono ancora sul server: la firma si potrà calcolare quando arriva l'archivio meteo.", true); return; }
    const punti = consumi.map((c) => ({ ...c, gg: gg.has(c.mese) ? gg.get(c.mese) : NaN }));
    const f = E.firma(punti);
    if (!f) { messaggio("messaggio-firma", "Dati insufficienti per la firma (servono mesi con gradi giorno diversi).", true); return; }
    const unita = $("unita-consumi").value || "";
    stato.firma = { ...f, unita, mesi: punti.map((p, i) => ({ mese: p.mese, consumo: p.consumo, gg20: Number.isFinite(p.gg) ? p.gg : null, atteso: f.atteso[i] })), sintetici, fonte };
    const box = $("firma"); box.innerHTML = "";
    const t = h("table", "totali"), b = t.createTBody();
    const anno = punti.reduce((s, p) => s + p.consumo, 0) * 12 / punti.length;
    const s = stato.superfici || {}, lorda = s.superficie_lorda && s.superficie_lorda.valore, netta = s.superficie_netta && s.superficie_netta.valore;
    const vol = stato.geometria && stato.geometria.volume_lordo;
    const norm = [["Consumo annuo (dai mesi inseriti)", anno, unita, 0], [`Per m² lordo`, lorda ? anno / lorda : null, `${unita}/m²`, 2],
      [`Per m² netto`, netta ? anno / netta : null, `${unita}/m²`, 2], [`Per m³ lordo`, vol ? anno / vol : null, `${unita}/m³`, 3]];
    stato.normalizzati = norm.filter((x) => x[1] !== null).map(([voce, valore, u]) => ({ voce, valore, unita: u }));
    [["Carico di base", f.base, `${unita}/mese`, 0], ["Sensibilità al clima", f.pendenza, `${unita}/(°C·giorno)`, 2], ["R²", f.r2, "", 2], ...norm]
      .forEach(([n, v, u, d]) => { const r = b.insertRow(); r.appendChild(h("th", null, n)); r.appendChild(h("td", "num", `${fmt(v, d)} ${u}`)); });
    box.appendChild(t);
    messaggio("messaggio-firma", sintetici ? "Firma calcolata con i gradi giorno sintetici dell'esempio (il server non ha ancora l'archivio meteo)."
      : `Firma calcolata con i gradi giorno reali di ${stato.comune.nome}. ${fonte}`);
    if (G) G.registra($("grafico-firma"), (dest, mis) => disegnaFirma(dest, mis), { titolo: "Firma energetica" });
  });
  function disegnaFirma(dest, mis) {
    const W = mis && mis.riquadro ? mis.larghezza : 520, H = mis && mis.riquadro ? mis.altezza : 240, F = stato.firma;
    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Firma energetica: consumo mensile e gradi giorno" }, dest);
    const sx = 56, gi = 30, su = 12, dx = 10, ps = F.mesi.filter((m) => m.gg20 !== null);
    const xm = Math.max(1, ...ps.map((m) => m.gg20)), ym = Math.max(1, ...ps.map((m) => m.consumo), F.base + F.pendenza * xm);
    const X = (v) => sx + (W - sx - dx) * v / xm, Y = (v) => su + (H - su - gi) * (1 - v / ym);
    svgEl("line", { x1: sx, x2: W - dx, y1: Y(0), y2: Y(0), stroke: "var(--linea)" }, svg);
    svgEl("line", { x1: X(0), x2: X(xm), y1: Y(F.base), y2: Y(F.base + F.pendenza * xm), stroke: "var(--serie-2)", "stroke-width": 2 }, svg);
    const segni = ps.map((m) => { svgEl("circle", { cx: X(m.gg20), cy: Y(m.consumo), r: 4, fill: "var(--primario)" }, svg); return m; });
    const t1 = svgEl("text", { x: W - dx, y: H - 8, "text-anchor": "end", "font-size": 12, fill: "var(--tenue)" }, svg); t1.textContent = `gradi giorno del mese (max ${fmt(xm)})`;
    const t2 = svgEl("text", { x: 4, y: su + 4, "font-size": 12, fill: "var(--tenue)" }, svg); t2.textContent = `${fmt(ym)} ${F.unita}`;
    if (G) G.osserva(svg, segni.sort((a, b) => a.gg20 - b.gg20).map((m) => ({ x: X(m.gg20), titolo: m.mese,
      segni: [[X(m.gg20), Y(m.consumo), "var(--primario)"]], righe: [["var(--primario)", `consumo: ${fmt(m.consumo)} ${F.unita}`], [null, `gradi giorno: ${fmt(m.gg20)}`],
        ["var(--serie-2)", `dalla firma: ${fmt(m.atteso)} ${F.unita}`]] })), { area: [sx, su, W - dx, H - gi] });
  }

  // ------------------------------------------------------------------ Fase B: quote relative e orizzonte lontano
  // quote dei corpi rispetto al terreno più basso dell'edificio scelto (gli ostacoli vicini hanno la loro quota)
  function rel(c) { return c ? (c.quota || 0) - (stato.q0 || 0) : 0; }
  // alberi entro il raggio del contesto, nei metri locali: quadrati con la cima della chioma (quota + h, relativa a q0)
  function alberiVicini() {
    if (!stato.proj || !stato.alberi.size) return [];
    const out = [];
    for (const a of stato.alberi.values()) {
      const [x, y] = stato.proj.avanti([a[0], a[1]]);
      if (Math.hypot(x, y) > RAGGIO + 30) continue;
      const m = (a[4] || 2) / 2;
      out.push({ ring: [[x - m, y - m], [x + m, y - m], [x + m, y + m], [x - m, y + m], [x - m, y - m]], h: a[2], quota: a[3],
        cima: (a[3] - (stato.q0 || 0)) + a[2], albero: true });
    }
    return out;
  }
  // resa della chioma (09/11/2026): ottagono di raggio 0,62 × lato attorno al centro della cella (le celle di 2 m vicine si
  // sovrappongono e formano una chioma unica); per ombre e calcoli resta il quadrato della cella
  function ottagono(a) {
    const cx = (a.ring[0][0] + a.ring[2][0]) / 2, cy = (a.ring[0][1] + a.ring[2][1]) / 2, r = Math.abs(a.ring[2][0] - a.ring[0][0]) * 0.62;
    const out = [];
    for (let k = 0; k < 8; k++) { const t = (k + 0.5) * Math.PI / 4; out.push([cx + r * Math.cos(t), cy + r * Math.sin(t)]); }
    out.push(out[0]);
    return out;
  }
  function ostacoliRelativi() {
    return [...stato.corpi, ...stato.vicini].map((c) => ({ ring: c.ring, cima: rel(c) + (c.colmo || c.gronda) }))
      .concat(alberiVicini().map((a) => ({ ring: a.ring, cima: a.cima })));
  }
  // orizzonte del terreno fino a 25 km dal server (Copernicus DEM 90 m); null se il server non lo dà
  async function orizzonteLontano() {
    if (stato.lontano !== null) return stato.lontano || null;
    stato.lontano = false;
    try {
      const [lon, lat] = stato.proj.indietro([0, 0]);
      const h = Math.max(...stato.corpi.map((c) => c.gronda)) / 2;
      const r = await fetch(`/api/edifici/orizzonte?lat=${lat.toFixed(4)}&lon=${lon.toFixed(4)}&h=${h.toFixed(0)}&direzioni=72`);
      if (r.ok && /json/.test(r.headers.get("Content-Type") || "")) {
        const d = await r.json();
        stato.lontano = d.angoli; stato.lontanoInfo = { quota: d.quota_dem, raggio: d.raggio_km, massimo: Math.max(...d.angoli), fonte: d.fonte };
      }
    } catch { /* server non raggiungibile: solo l'orizzonte vicino */ }
    return stato.lontano || null;
  }

  // ------------------------------------------------------------------ Fase B: ortofoto (proxy del server)
  // ------------------------------------------------------------------ colore degli edifici e alberi (09/11/2026)
  // menu a discesa con lo stesso aspetto e la stessa tastiera di quello dell'asterisco della testata (aspetto.js: frecce,
  // Home/Fine, Invio, Esc, clic fuori) e casella «Alberi»; tutto ricordato nel browser, entra nel PNG e nella legenda
  function applicaColoreEdifici() {
    const m = stato.mappa, col = coloreEdifici();
    if (m) (stato.sorgentiCorpi || []).forEach((id, k) => {
      if ((stato.archivi[k] || {}).osm) return;
      if (m.getLayer(id)) m.setPaintProperty(id, "fill-extrusion-color", col);
      if (m.getLayer(`${id}-2d`)) m.setPaintProperty(`${id}-2d`, "fill-color", col);
    });
    document.querySelectorAll(".legenda .pallino.vicini").forEach((x) => { x.style.background = voceColore().colore || ""; });
  }
  function applicaAlberi() {
    const m = stato.mappa;
    if (m) vedi(m, ["alberi"], !!stato.alberiVisibili && stato.in3d);
    const l = $("legenda-alberi");
    if (l) l.hidden = !stato.alberiVisibili;
  }
  function controlliAspetto3d() {
    const box = $("caselle-strati");
    if (!box || $("colore-edifici")) return;
    const riga = h("div", "riga-campi aspetto-3d"); riga.id = "aspetto-3d";
    // (09/11/2026 b) nella riga sotto la mappa l'etichetta visibile è «Colore» (il nome intero è nel tooltip e nell'aria-label
    // del pulsante): con «Colore degli edifici» per intero a 1366 px il gruppo andava a capo
    const et = h("span", "etichetta-colore", "Colore"); et.title = "Colore degli edifici"; et.setAttribute("aria-hidden", "true");
    const blocco = h("div", "vestito colore-edifici"); blocco.id = "colore-edifici";
    const quad = (c) => { const i = h("i", "campione-colore"); i.setAttribute("aria-hidden", "true"); i.style.background = c.colore || "var(--serie-6)"; return i; };
    const pul = h("button", "vestito-pulsante colore-edifici-pulsante"); pul.type = "button";
    pul.setAttribute("aria-haspopup", "listbox"); pul.setAttribute("aria-expanded", "false"); pul.setAttribute("aria-controls", "colore-edifici-elenco");
    const ul = h("ul", "vestito-elenco a-discesa"); ul.id = "colore-edifici-elenco"; ul.setAttribute("role", "listbox");
    ul.setAttribute("aria-label", "Colore degli edifici"); ul.tabIndex = -1; ul.hidden = true;
    const voci = COLORI_EDIFICI.map((c) => { const li = h("li"); li.setAttribute("role", "option"); li.id = `colore-edifici-${c.id}`; li.dataset.colore = c.id;
      li.append(quad(c), c.nome); ul.appendChild(li); return li; });
    blocco.append(pul, ul);
    let i = 0;
    const scelto = () => Math.max(0, COLORI_EDIFICI.findIndex((c) => c.id === stato.coloreEdifici));
    function disegna() {
      const v = voceColore();
      pul.innerHTML = ""; pul.append(quad(v), h("span", "nome-colore", v.nome));
      const t = `Colore degli edifici: ${v.nome}`; pul.setAttribute("aria-label", t); pul.title = t;
      voci.forEach((o) => o.setAttribute("aria-selected", String(o.dataset.colore === v.id)));
    }
    function evidenzia(n) { i = (n + voci.length) % voci.length; voci.forEach((o, k) => o.classList.toggle("attiva", k === i)); ul.setAttribute("aria-activedescendant", voci[i].id); }
    const fuori = (e) => { if (!ul.contains(e.target) && !pul.contains(e.target)) chiudi(false); };
    function apri() { ul.hidden = false; pul.setAttribute("aria-expanded", "true"); evidenzia(scelto()); ul.focus(); document.addEventListener("pointerdown", fuori, true); }
    function chiudi(rimetti) { ul.hidden = true; pul.setAttribute("aria-expanded", "false"); document.removeEventListener("pointerdown", fuori, true); if (rimetti) pul.focus(); }
    function conferma(k) {
      evidenzia(k); chiudi(true);
      stato.coloreEdifici = COLORI_EDIFICI[k].id; scriviPref(CHIAVE_COLORE, stato.coloreEdifici);
      disegna(); applicaColoreEdifici();
    }
    ul.addEventListener("keydown", (e) => {
      switch (e.key) {
        case "ArrowDown": case "ArrowRight": evidenzia(i + 1); break;
        case "ArrowUp": case "ArrowLeft": evidenzia(i - 1); break;
        case "Home": evidenzia(0); break;
        case "End": evidenzia(voci.length - 1); break;
        case "Enter": case " ": conferma(i); break;
        case "Escape": chiudi(true); break;
        case "Tab": chiudi(false); return;
        default: return;
      }
      e.preventDefault();
    });
    voci.forEach((o, k) => o.addEventListener("click", () => conferma(k)));
    pul.addEventListener("click", () => (ul.hidden ? apri() : chiudi(true)));
    pul.addEventListener("keydown", (e) => { if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); apri(); } });
    // alberi: chiome dal LiDAR (dove la pipeline delle falde è passata); restano tra gli ostacoli delle ombre anche spenti
    const la = h("label", "casella-strato casella-alberi"), ca = h("input"); ca.type = "checkbox"; ca.id = "strato-alberi"; ca.checked = !!stato.alberiVisibili;
    la.title = "Chiome degli alberi dal LiDAR (DSM meno DTM, celle di 2 m), nella vista 3D. Anche spente restano tra gli ostacoli per le ombre.";
    la.append(ca, " Alberi");
    ca.addEventListener("change", () => { stato.alberiVisibili = ca.checked; scriviPref(CHIAVE_ALBERI, ca.checked ? "1" : "0"); applicaAlberi(); });
    riga.append(et, blocco, la);
    // (09/11/2026 b, richiesta di Paolo) sotto la mappa, nella riga di «Genera il 3D» e delle frecce dell'ortofoto, dopo
    // «Azzera»: non più nel pannello di destra sotto i livelli; con la colonna stretta il gruppo va a capo intero
    const sotto = $("comandi-edificio");
    if (sotto) sotto.appendChild(riga); else box.after(riga);
    const leg = $("legenda-3d");
    if (leg && !$("legenda-alberi")) {
      const s0 = h("span"); s0.id = "legenda-alberi"; const p0 = h("i", "pallino alberi"); s0.append(p0, "alberi (chiome dal LiDAR)");
      const f = $("legenda-falde"); if (f) f.after(s0); else leg.appendChild(s0);
    }
    disegna(); applicaColoreEdifici(); applicaAlberi();
  }
  async function caricaOrtofoto() {
    const sel = $("sfondo-ortofoto");
    if (!sel) return;
    // (08/11/2026) frecce sotto la mappa, accanto a «Genera il 3D»: spostano l'ortofoto di 1 m rispetto ai vettori
    // (sposta_ortofoto.js); nella demo sintetica non ci sono ortofoto: nascoste
    if (window.EUGENIO_SPOSTA && $("sposta-ortofoto") && !stato.sposta)
      stato.sposta = window.EUGENIO_SPOSTA.crea($("sposta-ortofoto"), { pagina: location.pathname.split("/").pop() || "modelli3d", suCambio: spostaTessere });
    let fonti = [];
    try {
      const r = await fetch("/api/ortofoto/fonti");
      if (r.ok && /json/.test(r.headers.get("Content-Type") || "")) fonti = (await r.json()).fonti || [];
    } catch { /* senza server niente ortofoto */ }
    // demo sintetica: mai sopra una foto vera (sagome inventate, allineate alla griglia UTM e non alle strade: sembravano
    // «storte» rispetto agli edifici veri della foto, 05/11/2026)
    if (stato.indice && stato.indice.sintetico) {
      sel.disabled = true; sel.options[0].textContent = "nessuna: la demo sintetica non va sopra le foto vere";
      if (stato.sposta) stato.sposta.nascondi(true);
      if ($("strato-ortofoto")) { $("strato-ortofoto").checked = false; $("strato-ortofoto").disabled = true; }
      return;
    }
    stato.tutteOrtofoto = fonti;
    const copre = (f, [lon, lat]) => lon >= f.riquadro[0] && lon <= f.riquadro[2] && lat >= f.riquadro[1] && lat <= f.riquadro[3];
    // contesto Sentinel-2 sotto tutto nella mappa 2D (orientamento anche lontano dalle ortofoto regionali)
    const ctx = DUE_TEMPI && fonti.find((f) => f.id === "s2cloudless2016");
    if (ctx && !stato.mappa.getSource("contesto")) {
      stato.contestoOrto = ctx;
      stato.mappa.addSource("contesto", { type: "raster", tiles: [location.origin + ctx.tessere], tileSize: 256, minzoom: ctx.zoom[0], maxzoom: ctx.zoom[1],
        bounds: ctx.riquadro, attribution: ctx.citazione });
      stato.mappa.addLayer({ id: "contesto", type: "raster", source: "contesto", layout: { visibility: ortoVisibile() ? "visible" : "none" } },
        stato.mappa.getLayer("rilievo") ? "rilievo" : "ombre");
      if (stato.strati) stato.strati.alza();
    }
    // (09/11/2026) la RER 2023-24 ha zone senza immagini (Bologna, Modena, Parma, Faenza, Bagno di Romagna…): il server
    // dichiara le tessere vuote (X-Ortofoto-Vuota); finché l'utente non sceglie a mano si passa alla fonte successiva
    const zonaVuota = (f, c) => { const z = 12, n = 2 ** z; return `${f.id}@${Math.floor((c.lng + 180) / 360 * n)}_${Math.floor((1 - Math.asinh(Math.tan(c.lat * Math.PI / 180)) / Math.PI) / 2 * n)}`; };
    stato.vuote = stato.vuote || new Set(); stato.provate = stato.provate || new Set();
    async function provaVuota(f) {
      const m = stato.mappa, c = m.getCenter(), z = Math.max(f.zoom[0], Math.min(f.zoom[1], Math.floor(m.getZoom())));
      const k = zonaVuota(f, c);
      if (!f.tessere || f.pmtiles || stato.provate.has(k) || m.getZoom() < f.zoom[0] - 0.5) return;
      stato.provate.add(k);
      const n = 2 ** z, x = Math.floor((c.lng + 180) / 360 * n), y = Math.floor((1 - Math.asinh(Math.tan(c.lat * Math.PI / 180)) / Math.PI) / 2 * n);
      try {
        const r = await fetch(location.origin + f.tessere.replace("{z}", z).replace("{x}", x).replace("{y}", y));
        if (r.ok && r.headers.get("X-Ortofoto-Vuota") === "1") {
          stato.vuote.add(k);
          if (!stato.manuale && stato.ortofoto && stato.ortofoto.id === f.id) {
            opzioni();
            const g = stato.ortofoto;
            messaggio("messaggio-cerca", `«${f.nome}» non ha immagini in questa zona${g && g.id !== f.id ? `: uso «${g.nome}»` : ""}. Puoi scegliere un'altra fonte nei livelli.`);
          }
        }
      } catch { /* niente: resta la fonte scelta */ }
    }
    function opzioni() {
      // (07/11/2026 sera) stesso elenco e stesso ordine della pagina Ortofoto: anche Sentinel-2 cloudless, che resta pure come contesto sotto
      const c = stato.mappa.getCenter(), qui = fonti.filter((f) => copre(f, [c.lng, c.lat]));
      const auto = qui.filter((f) => !stato.vuote.has(zonaVuota(f, c)));       // per la scelta automatica, senza le fonti vuote qui
      const prima = sel.value;
      while (sel.options.length > 1) sel.remove(1);
      qui.forEach((f) => { const o = h("option", null, f.nome + (f.stato === "da confermare" ? " (licenza da confermare)" : "")); o.value = f.id; sel.appendChild(o); });
      stato.fontiOrtofoto = qui;
      sel.disabled = !qui.length || !ortoVisibile();
      sel.options[0].textContent = qui.length ? "nessuna ortofoto" : "ortofoto non disponibili qui";
      if (qui.some((f) => f.id === prima) && (stato.manuale || auto.some((f) => f.id === prima))) sel.value = prima;
      else if (prima) { sel.value = auto.length && !stato.manuale ? auto[0].id : ""; sfondo(sel.value); }
      else if (!stato.manuale && auto.length && !stato.ortofoto) { sel.value = auto[0].id; sfondo(sel.value); }
      if (!stato.manuale && stato.ortofoto) provaVuota(stato.ortofoto);
    }
    sel.addEventListener("change", () => { stato.manuale = true; sfondo(sel.value); });
    if ($("strato-ortofoto")) $("strato-ortofoto").addEventListener("change", vediOrtofoto);
    if ($("caselle-strati")) $("caselle-strati").addEventListener("change", aggiornaSposta);
    opzioni();
    aggiornaSposta();
    stato.mappa.on("moveend", opzioni);
  }
  // casella «Ortofoto» dei livelli (seconda pubblicazione del 05/11): spenta = niente foto né contesto, la fonte scelta resta
  const ortoVisibile = () => !$("strato-ortofoto") || $("strato-ortofoto").checked;
  // strati vettoriali sopra la foto: sagome degli edifici dell'archivio (DBTR, OSM, DB topografico caricato: sempre
  // disegnate), particelle e contorni degli edifici dei livelli
  function vettoriAccesi() {
    const st = stato.strati && stato.strati.stato;
    return !!((stato.sorgentiCorpi || []).length || stato.osmAttivo || (st && (st.particelle || st.edifici)));
  }
  function aggiornaSposta() {
    if (stato.sposta) stato.sposta.fonte(stato.ortofoto, { visibile: ortoVisibile(), vettori: vettoriAccesi() });
  }
  const tessereOrto = (f) => location.origin + (stato.sposta ? stato.sposta.url(f.tessere) : f.tessere);
  function spostaTessere() {
    const f = stato.ortofoto, src = stato.mappa && stato.mappa.getSource("ortofoto");
    if (src && f && src.setTiles) src.setTiles([tessereOrto(f)]);     // nessun salto della camera, 2D e 3D
  }
  function vediOrtofoto() {
    const m = stato.mappa, si = ortoVisibile();
    if (!m) return;
    vedi(m, ["ortofoto", "contesto"], si);
    const att = $("attribuzione-ortofoto");
    if (att) att.hidden = !si || !stato.ortofoto;
    if ($("sfondo-ortofoto") && !(stato.indice && stato.indice.sintetico)) $("sfondo-ortofoto").disabled = !si || !(stato.fontiOrtofoto || []).length;
    aggiornaSposta();
    coloriRilievo();
  }
  function sfondo(id) {
    const m = stato.mappa, f = (stato.tutteOrtofoto || stato.fontiOrtofoto).find((x) => x.id === id) || null;
    if (m.getLayer("ortofoto")) m.removeLayer("ortofoto");
    if (m.getSource("ortofoto")) m.removeSource("ortofoto");
    stato.ortofoto = f;
    aggiornaSposta();
    const att = $("attribuzione-ortofoto");
    if (!f) { att.hidden = true; return; }
    m.addSource("ortofoto", { type: "raster", tiles: [tessereOrto(f)], tileSize: 256, minzoom: f.zoom[0], maxzoom: f.zoom[1],
      bounds: f.riquadro, attribution: `${f.citazione}` });
    m.addLayer({ id: "ortofoto", type: "raster", source: "ortofoto", paint: { "raster-opacity": 1 },
      layout: { visibility: ortoVisibile() ? "visible" : "none" } }, m.getLayer("rilievo") ? "rilievo" : "ombre");
    if (stato.strati) stato.strati.alza();
    att.hidden = !ortoVisibile(); att.innerHTML = "";
    att.append("Ortofoto: ", f.citazione, " – licenza ");
    const a = h("a", null, f.licenza); a.href = f.scheda; att.appendChild(a);
    if (f.stato === "da confermare") att.append(" (uso tramite il server di EuGEnio in attesa di conferma della fonte)");
    if (!f.copia) att.append(" – solo consultazione dal vivo, non entra nei report");
    att.append(".");
  }
  // vista della mappa per il report: PNG ridotto, solo con un'ortofoto che può entrare nei report
  function immagineMappa() {
    const f = stato.ortofoto;
    if (!f || !f.nei_report || !stato.mappa) return null;
    try {
      const c = stato.mappa.getCanvas(), w = Math.min(900, c.width), hh = Math.round(c.height * w / c.width);
      const o = document.createElement("canvas"); o.width = w; o.height = hh;
      o.getContext("2d").drawImage(c, 0, 0, w, hh);
      let dati = o.toDataURL("image/png");
      if (dati.length > 1.3e6 * 4 / 3) { o.width = Math.round(w * 0.7); o.height = Math.round(hh * 0.7); o.getContext("2d").drawImage(c, 0, 0, o.width, o.height); dati = o.toDataURL("image/png"); }
      const sp = stato.sposta ? { de: stato.sposta.de, dn: stato.sposta.dn } : {};     // dichiarato nella didascalia del report
      return { titolo: `Vista 3D dell'edificio con l'ortofoto. ${f.citazione}`, png: dati.split(",")[1], ortofoto: { id: f.id, licenza: f.licenza, citazione: f.citazione, scheda: f.scheda, ...sp } };
    } catch { return null; }
  }

  // ------------------------------------------------------------------ Fase B: facciate al sole (§ 7)
  function mostraFacciate() {
    if (!stato.mappa || !stato.mappa.getSource("facciate")) return;
    const F = stato.facciate, feats = [];
    if (F) {
      const v = F.irr.map((x) => x.annuo), lo = Math.min(...v), hi = Math.max(...v);
      F.parti.forEach((p, k) => {
        const [a, b] = p.estremi, n = [Math.sin(p.azimut * Math.PI / 180) * 0.4, Math.cos(p.azimut * Math.PI / 180) * 0.4];
        const ring = [a, b, [b[0] + n[0], b[1] + n[1]], [a[0] + n[0], a[1] + n[1]], a].map(stato.proj.indietro);
        const c = stato.corpi.find((x) => x.id === p.corpo);
        const z0 = p.z[0] - rel(c), z1 = p.z[1] - rel(c);
        feats.push({ type: "Feature", properties: { t: hi > lo ? (v[k] - lo) / (hi - lo) : 0.5, z0, z1: z1 + 0.02 }, geometry: { type: "Polygon", coordinates: [ring] } });
      });
    }
    stato.mappa.getSource("facciate").setData({ type: "FeatureCollection", features: feats });
  }
  $("calcola-facciate").addEventListener("click", async () => {
    const b = $("calcola-facciate"); b.disabled = true;
    try {
      const corpi = stato.corpi.map((c) => ({ ...c, quota: rel(c) })), vicini = stato.vicini.map((c) => ({ ...c, quota: rel(c) }));
      const parti = E.partiFacciate(corpi, vicini);
      if (!parti.length) { messaggio("messaggio-facciate", "Nessuna parte esposta: tutte le pareti sono in comune.", true); return; }
      messaggio("messaggio-facciate", `Calcolo l'orizzonte di ${parti.length} pezzi di facciata esposti…`);
      const lont = await orizzonteLontano();
      const oz = await orizzonti(parti.map((p) => p.centro), ostacoliRelativi(), lont);
      const cl = await clima();
      const [lon, lat] = stato.proj.indietro([0, 0]);
      messaggio("messaggio-facciate", "Calcolo il sole ora per ora…");
      await new Promise((ok) => setTimeout(ok, 20));
      const irr = E.irraggiamentoFacciate(cl, lat, lon, parti, oz);
      stato.facciate = { parti, irr, riepilogo: E.riepilogoFacciate(parti, irr), clima: cl, lontano: !!lont };
      tabellaFacciate(); mostraFacciate();
      const tot = Object.values(stato.facciate.riepilogo).reduce((s, x) => s + x.area, 0);
      messaggio("messaggio-facciate", `${fmt(tot)} m² di facciate esposte in ${parti.length} pezzi.` + (cl.sintetico
        ? " Attenzione: il clima orario del comune non è ancora sul server, il calcolo usa un anno di cielo sereno ridotto (sintetico)."
        : ` Clima orario del ${cl.anno}.`) + (lont ? "" : " Orizzonte del terreno lontano non disponibile: solo edifici vicini.") + ` ${testoSceltaTetti()}`, !!cl.sintetico);
    } catch (e) {
      console.warn(e); messaggio("messaggio-facciate", `Calcolo non riuscito: ${e.message || e}`, true);
    } finally { b.disabled = false; }
  });
  function tabellaFacciate() {
    const R = stato.facciate.riepilogo, box = $("facciate"); box.innerHTML = "";
    const t = h("table"), r1 = t.createTHead().insertRow();
    ["Orientamento", "Esposta (m²)", "kWh/m² anno", "kWh anno", "Estate giu–ago (kWh)", "Inverno dic–feb (kWh)", "Ombre", "Cielo visibile"].forEach((x, k) => r1.appendChild(h("th", k ? "num" : null, x)));
    const b = t.createTBody();
    E.SETTORI.forEach((s) => {
      const x = R[s]; if (!x.area) return;
      const r = b.insertRow(); r.appendChild(h("th", null, s));
      [[x.area, 0], [x.kwh_m2, 0], [x.kwh, 0], [x.estate, 0], [x.inverno, 0]].forEach(([v, d]) => r.appendChild(h("td", "num", fmt(v, d))));
      r.appendChild(h("td", "num", `−${fmt(x.perdita, 1)} %`));
      r.appendChild(h("td", "num", x.cielo === null ? "—" : fmt(100 * x.cielo, 0) + " %"));
    });
    { const sc = h("div", "tabella-scorre"); sc.appendChild(t); box.appendChild(sc); }   // telefono: niente scorrimento di lato
    box.appendChild(h("p", "aiuto", "Cielo visibile: quota del cielo che la facciata vede davanti a sé (100 % = nessun edificio, albero o rilievo davanti), media sull'area esposta; indica l'accesso alla luce naturale (analisi 9)."));
    if (G) G.registra($("grafico-facciate"), (dest, mis) => {
      const W = mis && mis.riquadro ? mis.larghezza : 520, H = mis && mis.riquadro ? mis.altezza : 220;
      const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "kWh/m² all'anno per orientamento" }, dest);
      const sx = 44, gi = 26, su = 12, passo = (W - sx - 8) / 8, max = Math.max(1, ...E.SETTORI.map((s) => R[s].kwh_m2));
      const Y = (v) => su + (H - su - gi) * (1 - v / max);
      const punti = E.SETTORI.map((s, i) => {
        const x = sx + passo * (i + 0.5), v = R[s].kwh_m2;
        const rr = svgEl("rect", { x: x - passo * 0.3, y: Y(v), width: passo * 0.6, height: Y(0) - Y(v), fill: "var(--serie-4)" }, svg);
        const tt = svgEl("text", { x, y: H - 8, "text-anchor": "middle", "font-size": 12, fill: "var(--tenue)" }, svg); tt.textContent = s;
        return { x, titolo: `Facciate a ${s}`, elementi: [rr], righe: [["var(--serie-4)", `${fmt(v)} kWh/m² anno`], [null, `${fmt(R[s].area)} m² esposti`]] };
      });
      const tt = svgEl("text", { x: 4, y: su + 4, "font-size": 12, fill: "var(--tenue)" }, svg); tt.textContent = `${fmt(max)} kWh/m²`;
      G.osserva(svg, punti, { area: [sx, su, W - 8, H - gi], guida: false });
    }, { titolo: "Sole sulle facciate per orientamento" });
  }

  // ------------------------------------------------------------------ Fase B: confronto con PVGIS
  $("calcola-pvgis").addEventListener("click", async () => {
    const b = $("calcola-pvgis"); b.disabled = true;
    try {
      if (!stato.fv) { messaggio("messaggio-pvgis", "Prima calcola la producibilità delle aree.", true); return; }
      const [lon, lat] = stato.proj.indietro([0, 0]);
      const aree = stato.aree.map((a) => ({ id: a.id, kwp: conteggio(a).kwp, inclinazione: a.inclinazione, orientamento: a.orientamento,
        montaggio: a.montaggio, perdite: 14, orizzonte: (stato.fvOrizzonti[a.id] || []).map((x) => Math.round(x * 10) / 10) })).filter((a) => a.kwp > 0);
      if (!aree.length) { messaggio("messaggio-pvgis", "Nessuna area con moduli.", true); return; }
      messaggio("messaggio-pvgis", "Chiedo a PVGIS (dal nostro server)…");
      const r = await fetch("/api/edifici/pvgis", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ lat, lon, aree }) });
      if (!r.ok || !/json/.test(r.headers.get("Content-Type") || "")) {
        let d = ""; try { d = (await r.json()).detail; } catch { /* niente */ }
        throw new Error(d || (r.status === 404 ? "il confronto con PVGIS non è ancora attivo sul server" : `risposta ${r.status}`));
      }
      const d = await r.json();
      stato.pvgis = { ...d, aree: d.aree.map((x) => ({ ...x, eugenio: (stato.fv.find((f) => f.id === x.id) || {}) })) };
      tabellaPvgis();
      messaggio("messaggio-pvgis", `${d.nota} ${d.fonte}.` + (stato.fvClima && stato.fvClima.sintetico ? " Il calcolo di EuGEnio usa un clima sintetico: il confronto non è significativo." : ""));
    } catch (e) {
      messaggio("messaggio-pvgis", `Confronto non riuscito: ${e.message || e}`, true);
    } finally { b.disabled = !stato.fv; }
  });
  function tabellaPvgis() {
    const P_ = stato.pvgis, box = $("pvgis"); box.innerHTML = "";
    const t = h("table"), r1 = t.createTHead().insertRow();
    ["Area", "EuGEnio (kWh/anno)", "PVGIS con orizzonte", "PVGIS senza", "Differenza", "Dati PVGIS"].forEach((x, k) => r1.appendChild(h("th", k ? "num" : null, x)));
    const b = t.createTBody();
    P_.aree.forEach((x) => {
      const e = x.eugenio.kwh, p = x.con_orizzonte.kwh_anno, r = b.insertRow();
      r.appendChild(h("th", null, x.id));
      r.appendChild(h("td", "num", fmt(e))); r.appendChild(h("td", "num", fmt(p))); r.appendChild(h("td", "num", fmt(x.senza_orizzonte_utente.kwh_anno)));
      r.appendChild(h("td", "num", e && p ? `${e >= p ? "+" : "−"}${fmt(Math.abs(100 * (e - p) / p), 1)} %` : "—"));
      r.appendChild(h("td", "fonte", `${x.con_orizzonte.banca_dati || ""} ${(x.con_orizzonte.anni || []).join("–")}`));
    });
    { const sc = h("div", "tabella-scorre"); sc.appendChild(t); box.appendChild(sc); }   // telefono: niente scorrimento di lato
    const MESI_ = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"];
    const eu = MESI_.map((_, i) => P_.aree.reduce((s, x) => s + ((x.eugenio.mensile || [])[i] || 0), 0));
    const pv = MESI_.map((_, i) => P_.aree.reduce((s, x) => s + ((x.con_orizzonte.kwh_mensili || [])[i] || 0), 0));
    if (G) G.registra($("grafico-pvgis"), (dest, mis) => {
      const W = mis && mis.riquadro ? mis.larghezza : 520, H = mis && mis.riquadro ? mis.altezza : 230;
      const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Producibilità mensile: EuGEnio e PVGIS" }, dest);
      const sx = 50, gi = 26, su = 12, passo = (W - sx - 8) / 12, max = Math.max(1, ...eu, ...pv), Y = (v) => su + (H - su - gi) * (1 - v / max);
      const punti = MESI_.map((m, i) => {
        const x = sx + passo * (i + 0.5);
        const a = svgEl("rect", { x: x - passo * 0.36, y: Y(eu[i]), width: passo * 0.34, height: Y(0) - Y(eu[i]), fill: "var(--serie-3)" }, svg);
        const c = svgEl("rect", { x: x + passo * 0.02, y: Y(pv[i]), width: passo * 0.34, height: Y(0) - Y(pv[i]), fill: "var(--serie-1)" }, svg);
        const tt = svgEl("text", { x, y: H - 8, "text-anchor": "middle", "font-size": 12, fill: "var(--tenue)" }, svg); tt.textContent = m;
        return { x, titolo: m, elementi: [a, c], righe: [["var(--serie-3)", `EuGEnio: ${fmt(eu[i])} kWh`], ["var(--serie-1)", `PVGIS: ${fmt(pv[i])} kWh`]] };
      });
      const tt = svgEl("text", { x: 4, y: su + 4, "font-size": 12, fill: "var(--tenue)" }, svg); tt.textContent = `${fmt(max)} kWh`;
      G.osserva(svg, punti, { area: [sx, su, W - 8, H - gi], guida: false });
      const leg = h("p", "legenda"); leg.innerHTML = '<span><i class="pallino" style="background:var(--serie-3)"></i>EuGEnio</span> <span><i class="pallino" style="background:var(--serie-1)"></i>PVGIS con l\'orizzonte di EuGEnio</span>';
      dest.appendChild(leg);
    }, { titolo: "Producibilità mensile: EuGEnio e PVGIS" });
  }

  // ------------------------------------------------------------------ Fase B: obblighi di legge (analisi 14)
  const NOMI_INTERVENTO = { nuovo: "nuova costruzione", primo: "ristrutturazione importante di primo livello",
    secondo: "ristrutturazione importante di secondo livello", impianto: "ristrutturazione dell'impianto termico" };
  async function datiDpr() {
    if (stato.dpr === null) {
      stato.dpr = false;
      try { stato.dpr = await json("dati/dpr412.json?v=20261109b"); } catch { /* senza file: niente zona */ }
    }
    return stato.dpr || null;
  }
  async function obblighi() {
    const box = $("obblighi");
    if (!box || !stato.edificio) return;
    const S = stato.corpi.reduce((s, c) => s + E.areaCorpo(c), 0);
    const intervento = $("intervento-199").value, pubblico = $("pubblico-199").checked;
    const o = E.obbligoFer(S, { intervento, pubblico });
    const kwpFv = stato.aree.reduce((s, a) => s + conteggio(a).kwp, 0);
    const dpr = await datiDpr(), riga = dpr && stato.comune ? dpr.comuni[stato.comune.istat] : null;
    const zona = riga ? riga[1] : null, gg = riga ? riga[0] : null, sv = stato.geometria ? stato.geometria.s_su_v : null;
    const ht = E.htMassimo(zona, sv);
    const qIns = E.numero($("quota-vetrata") ? $("quota-vetrata").value : null);
    const qSt = qIns === null ? E.quotaVetrataStimata(stato.geometria, stato.uso || (stato.visura || {}).uso || "altro") : null;
    const quota = qIns !== null ? qIns : qSt ? qSt.quota : null;
    const ht11 = quota !== null ? E.htMassimoPrimoLivello(zona, quota) : null;
    const testoQuota = qIns !== null ? `${fmt(qIns, Number.isInteger(qIns) ? 0 : 1)} % (dato inserito)` : qSt
      ? `${fmt(qSt.quota, 1)} % (stima: finestre ${fmt(100 * qSt.finestre_su_pareti)} % delle pareti esposte, uso ${qSt.uso})` : "—";
    const testoHt11 = ht11 ? `${fmt(ht11.valore, 2)} W/m²K (zona ${zona}, vetrate ${testoQuota.replace(/ \(.*$/, "")}`
      + (ht11.interpolato ? `; tra le colonne ${ht11.colonne.map(([q, v]) => `${q} % = ${fmt(v, 2)}`).join(" e ")}, interpolazione lineare di EuGEnio`
        : ht11.nota ? `; ${ht11.nota}` : "") + ")" : "—";
    const righe = [
      ["Superficie in pianta S (proiezione al suolo della sagoma)", `${fmt(S)} m²`, "D.Lgs. 199/2021, All. III, sez. B, punto 3"],
      ["Coefficiente k", `${fmt(o.k, 3)} (${intervento === "nuovo" ? "nuova costruzione" : "edificio esistente"})`, "All. III, sez. B, punto 3"],
      ...(pubblico ? [["Edificio pubblico", "potenza +10 %, quote +5 punti", "All. III, sez. B, punto 5"]] : []),
      ["Potenza minima FER sopra o dentro l'edificio P = k · S", `${fmt(o.kw, 1)} kW`, pubblico ? "All. III, sez. B, punti 3 e 5" : "All. III, sez. B, punto 3"],
      ["Potenza FV disegnata sui tetti", stato.aree.length ? `${fmt(kwpFv, 1)} kWp – ${kwpFv >= o.kw ? "copre" : "non copre"} la potenza minima` : "nessuna area disegnata", "passo «Fotovoltaico sui tetti»"],
      ["Quota rinnovabile dei consumi previsti", (o.quota_acs !== null ? `${o.quota_acs} % dell'ACS e ` : "") + `${o.quota_totale} % di ${o.quota_acs !== null ? "ACS + riscaldamento + raffrescamento" : "riscaldamento + raffrescamento"}`, "All. III, sez. B, punto 1" + (pubblico ? " e 5" : "")],
      ["Zona climatica e gradi giorno del comune", zona ? `zona ${zona}, ${fmt(gg)} GG` : "—", "DPR 412/93, Allegato A"],
      ["Rapporto di forma S/V", sv ? `${fmt(sv, 2)} m⁻¹` : "—", "indicatori geometrici (passo 4)"],
      ["H'T massimo per nuova costruzione e demolizione/ricostruzione", ht ? `${fmt(ht.valore, 2)} W/m²K (zona ${zona}, ${ht.fascia})` : "—", "DM 26/6/2015, All. 1, App. A, § 2.1, Tab. 10 (DM 28/10/2025)"],
      ["Superfici vetrate sul totale dei componenti dell'involucro, prima dell'intervento", testoQuota, qIns !== null ? "dato inserito" : "stima di EuGEnio (da rilevare)"],
      [`H'T massimo per ristrutturazione importante di primo livello${intervento === "primo" ? " (intervento scelto)" : ""}`, testoHt11, "DM 26/6/2015, All. 1, App. A, § 2.1, Tab. 11 (DM 28/10/2025)"],
    ];
    stato.obblighi = { intervento: NOMI_INTERVENTO[intervento], pubblico, superficie: S, k: o.k, kw: o.kw, kwp_fv: kwpFv,
      quota_acs: o.quota_acs, quota_totale: o.quota_totale, zona, gg, s_su_v: sv, ht_max: ht ? ht.valore : null, ht_fascia: ht ? ht.fascia : null,
      quota_vetrata: quota, quota_vetrata_fonte: qIns !== null ? "dato inserito" : qSt ? "stima" : null, ht_max_primo_livello: ht11 ? ht11.valore : null,
      righe: righe.map(([v, x, r]) => ({ voce: v, valore: x, riferimento: r })) };
    box.innerHTML = "";
    const t = h("table"), r1 = t.createTHead().insertRow();
    ["Voce", "Valore", "Riferimento"].forEach((x) => r1.appendChild(h("th", null, x)));
    const b = t.createTBody();
    righe.forEach(([v, x, r]) => { const tr = b.insertRow(); tr.appendChild(h("th", null, v)); tr.appendChild(h("td", null, x)); tr.appendChild(h("td", "fonte", r)); });
    { const sc = h("div", "tabella-scorre"); sc.appendChild(t); box.appendChild(sc); }   // telefono: niente scorrimento di lato
    const telai = stato.aree.some((a) => a.montaggio === "telai");
    $("nota-obblighi").textContent = "Le quote di copertura valgono sui consumi previsti dal progetto (servono le metodiche di calcolo, qui non "
      + "fatte); la potenza minima si può coprire anche con altre fonti rinnovabili. Gli impianti a terra non contano; quelli nelle pertinenze sì "
      + "(All. III, sez. C, punto 2). Valori dell'atto normativo vigente (Normattiva, 04/11/2026): le Regioni possono alzarli (art. 26, comma 7)."
      + (telai ? " Tetti piani: l'asse dei moduli non deve superare la balaustra o, senza balaustra, 30 cm dal piano (sez. C, punto 3): controlla i telai." : "");
  }
  ["intervento-199", "pubblico-199", "quota-vetrata"].forEach((id) => { if ($(id)) $(id).addEventListener("change", obblighi); });

  // ------------------------------------------------------------------ Fase B: classifica di priorità (analisi 4)
  const CHIAVE_PRIORITA = "eugenio_priorita";
  const NOMI_CRITERI = { intensita: "Consumo per m²", sensibilita: "Sensibilità al clima", base: "Carico di base", costo: "Costo per m²", fv: "FV possibile per m²" };
  const KWH_SMC = 0.03852 * 1e3 / 3.6;            // PCS convenzionale 0,03852 GJ/Smc ≈ 10,70 kWh/Smc
  let pesi = { ...E.PESI_PRIORITA };
  function leggiPriorita() { try { return JSON.parse(localStorage.getItem(CHIAVE_PRIORITA) || "[]"); } catch { return []; } }
  function salvaPriorita(l) { try { localStorage.setItem(CHIAVE_PRIORITA, JSON.stringify(l)); } catch { /* solo per la pagina aperta */ } stato.sedi = l; }
  stato.sedi = leggiPriorita();
  const inKwh = (v, u) => (/smc|m3|m³/i.test(u || "") ? v * KWH_SMC : /mwh/i.test(u || "") ? v * 1000 : v);
  function sedeDaQui() {
    const s = stato.superfici || {}, lorda = s.superficie_lorda && s.superficie_lorda.valore;
    if (!lorda) return null;
    const F = stato.firma, u = F ? F.unita : "";
    const anno = F ? F.mesi.reduce((x, m) => x + m.consumo, 0) * 12 / F.mesi.length : null;
    const fv = stato.fv ? stato.fv.reduce((x, a) => x + a.kwh, 0) : null;
    const costo = E.numero($("costo-edificio") ? $("costo-edificio").value : null);
    return { id: `${stato.edificio}`, nome: `Edificio ${stato.edificio}` + (stato.comune ? ` (${stato.comune.nome})` : ""), superficie: lorda,
      kwh_m2: anno ? inKwh(anno, u) / lorda : null, sensibilita: F ? inKwh(F.pendenza, u) / lorda : null,
      base_quota: F && anno ? Math.max(0, Math.min(1, F.base * 12 / anno)) : null, fv_kwh_m2: fv ? fv / lorda : null,
      costo_m2: costo ? costo / lorda : null, s_su_v: stato.geometria ? stato.geometria.s_su_v : null,
      sintetico: stato.sintetico || !!(F && F.sintetici), fonte: "pagina 3D" };
  }
  $("aggiungi-priorita").addEventListener("click", () => {
    const x = sedeDaQui();
    if (!x) { messaggio("messaggio-priorita", "Serve la superficie lorda dell'edificio (passo «Piani e superfici»).", true); return; }
    const l = leggiPriorita().filter((y) => y.id !== x.id); l.push(x); salvaPriorita(l); classifica();
    messaggio("messaggio-priorita", `${x.nome} aggiunto` + (x.kwh_m2 === null ? ": senza consumi (calcola prima la firma) conta solo per gli altri criteri." : "."));
  });
  $("svuota-priorita").addEventListener("click", () => { salvaPriorita([]); classifica(); messaggio("messaggio-priorita", "Classifica svuotata."); });
  $("file-priorita").addEventListener("change", async (ev) => {
    const f = ev.target.files[0]; ev.target.value = "";
    if (!f || !window.EUGENIO_TABELLE) return;
    try {
      const T = window.EUGENIO_TABELLE, d = await T.leggi(f), righe = T.righe(d.testo, T.separatore(d.testo.split(/\r?\n/)[0]));
      const tit = righe[0].map((x) => E.norm(String(x).replace(/\s*[([].*$/, "")));
      const col = (...n) => tit.findIndex((x) => n.includes(x));
      const c = { nome: col("nome", "sede", "edificio", "descrizione"), sup: col("superficie", "superficie_lorda", "sup_lorda", "slp", "m2"),
        ter: col("consumo_termico", "termico", "gas", "calore"), ut: col("unita_termico", "unita_gas"), ele: col("consumo_elettrico", "elettrico", "energia_elettrica"),
        costo: col("costo", "costo_annuo", "spesa"), fv: col("fv_kwh", "fv", "fotovoltaico"), sens: col("sensibilita"), base: col("base", "carico_base") };
      if (c.nome < 0 || c.sup < 0) throw new Error("servono almeno le colonne «nome» e «superficie»");
      const n = (r, i) => (i < 0 ? null : T.numero(r[i], { decimalePunto: d.decimalePunto }));
      const nuove = righe.slice(1).filter((r) => r.length > 1 && !String(r[0]).startsWith("#")).map((r, i) => {
        const sup = n(r, c.sup); if (!(sup > 0)) return null;
        const ter = n(r, c.ter), ele = n(r, c.ele), ut = c.ut >= 0 ? r[c.ut] : "kWh";
        const kwh = (ter !== null ? inKwh(ter, ut) : 0) + (ele || 0);
        return { id: `file-${i}-${r[c.nome]}`, nome: String(r[c.nome]).slice(0, 80), superficie: sup, kwh_m2: ter !== null || ele !== null ? kwh / sup : null,
          sensibilita: n(r, c.sens) !== null ? n(r, c.sens) / sup : null, base_quota: n(r, c.base), costo_m2: n(r, c.costo) !== null ? n(r, c.costo) / sup : null,
          fv_kwh_m2: n(r, c.fv) !== null ? n(r, c.fv) / sup : null, fonte: `file ${f.name}` };
      }).filter(Boolean);
      salvaPriorita([...leggiPriorita().filter((y) => !String(y.id).startsWith("file-")), ...nuove]); classifica();
      messaggio("messaggio-priorita", `${nuove.length} sedi lette dal file. ${d.nota || ""}`);
    } catch (e) { messaggio("messaggio-priorita", `File non letto: ${e.message || e}`, true); }
  });
  function campiPesi() {
    const box = $("pesi-priorita"); if (!box) return;
    box.innerHTML = "";
    for (const [k, n] of Object.entries(NOMI_CRITERI)) {
      const l = h("label", null, n), i = h("input"); i.type = "number"; i.min = 0; i.max = 1; i.step = 0.05; i.value = pesi[k];
      i.addEventListener("change", () => { pesi[k] = Math.max(0, E.numero(i.value) || 0); classifica(); });
      l.appendChild(i); box.appendChild(l);
    }
  }
  function classifica() {
    const box = $("priorita"); box.innerHTML = "";
    const l = stato.sedi || [];
    if (!l.length) { stato.priorita = null; return; }
    const righe = E.priorita(l, pesi);
    stato.priorita = { righe, pesi: { ...pesi } };
    const t = h("table"), r1 = t.createTHead().insertRow();
    ["Posto", "Sede", "Punteggio", ...Object.values(NOMI_CRITERI), "kWh/m²", ""].forEach((x, k) => r1.appendChild(h("th", k > 1 ? "num" : null, x)));
    const b = t.createTBody();
    righe.forEach((x) => {
      const r = b.insertRow();
      r.appendChild(h("td", "num", x.posto ?? "—")); r.appendChild(h("th", null, x.nome + (x.sintetico ? " (sintetico)" : "")));
      r.appendChild(h("td", "num", fmt(x.punteggio)));
      Object.keys(NOMI_CRITERI).forEach((k) => r.appendChild(h("td", "num", x.punteggi[k] === undefined || x.punteggi[k] === null ? "—" : fmt(x.punteggi[k]))));
      r.appendChild(h("td", "num", fmt(x.kwh_m2)));
      const tx = h("td"), bt = h("button", "filtro", "Togli"); bt.type = "button";
      bt.addEventListener("click", () => { salvaPriorita(leggiPriorita().filter((y) => y.id !== x.id)); classifica(); });
      tx.appendChild(bt); r.appendChild(tx);
    });
    box.appendChild(t);
    if (l.length < 3) box.appendChild(h("p", "aiuto", "Con meno di tre sedi la classifica dice poco: aggiungine altre."));
  }
  campiPesi(); classifica();

  // ------------------------------------------------------------------ report
  function corpoReport() {
    if (!stato.edificio) return null;
    const s = stato.superfici || {};
    const sup = {};
    for (const k of Object.keys(E.ETICHETTE)) if (s[k]) sup[k] = { valore: s[k].valore, fonte: NOMI_FONTE[s[k].fonte] || s[k].fonte };
    const fonti = [...new Set(stato.corpi.map((c) => c.fonte_sagoma.replace(/ \(divisa dall'utente\)/, "")))].map((f) => `Sagome: ${f}`)
      .concat([...new Set(stato.corpi.map((c) => c.licenza))].map((l) => `Licenza delle sagome: ${l}`));
    // attribuzione di ogni archivio da cui vengono i corpi e i vicini (07/11/2026: anche il ripiego OSM, con la sua licenza)
    const usati = [...new Set(stato.corpi.filter((c) => c.edificio !== "MODELLO").concat(stato.vicini).map((c) => c.archivio || 0))]
      .map((k) => stato.archivi[k]).filter(Boolean);
    const osmUsato = usati.some((a) => a.osm);
    const attr = usati.map((a) => (a.osm ? "© OpenStreetMap contributors, Open Database License 1.0 (https://www.openstreetmap.org/copyright): "
      + "sagome degli edifici fuori dal DBTR, tramite l'API Overpass" : a.indice.attribuzione)).filter(Boolean);
    if (!attr.length && stato.indice && stato.indice.attribuzione) attr.push(stato.indice.attribuzione);
    fonti.push(...new Set(attr));
    const note = [];
    if (usati.some((a) => a.locale)) note.push("Sagome e altezze dal DB topografico caricato dall'utente e letto solo nel browser (stesse regole "
      + "dell'archivio del server; quote dei corpi dalla base data dal DB topografico, terreno della vista 3D dal DTM del server).");
    if (osmUsato && stato.osm.sagome) {
      note.push(`${testoSagomeRegionali()} ${stato.osm.sagome.attribuzione}; altezze ed edifici aggiunti © OpenStreetMap contributors (ODbL 1.0). `
        + "Altezza di ogni sagoma dall'edificio OSM che le si sovrappone di più (height, poi piani × 3 m), altrimenti mediana dei vicini o 9 m.");
      fonti.push(`${stato.osm.sagome.attribuzione} – ${stato.osm.sagome.scheda || ""}`);
    }
    if (osmUsato) {
      note.push("Sagome da OpenStreetMap (ripiego dove non c'è ancora il DBTR): completezza variabile, qualità inferiore, altezze dal tag height "
        + "o dai piani (× 3 m) e altrove stimate (mediana dei corpi DBTR entro 200 m dove ci sono, altrimenti 9 m), indicate come «stima» nella "
        + "tabella dei corpi; terreno piano (nessun DTM).");
      const t = testoAltezzeOsm(contaOrigini(stato.corpi.concat(stato.vicini).filter((c) => (archivioDi(c) || {}).osm)), " dell'edificio e dei vicini");
      if (t) note.push(t);
    }
    if (stato.lidar && stato.corpi.some((c) => c.lidar && c.lidar.stato === "ok"))
      Object.values(stato.lidar.attribuzioni || {}).forEach((a) => fonti.push(`Falde dei tetti: ${a.attribuzione || a.descrizione} (${a.licenza})`));
    if (stato.corpi.some((c) => c.lidar && c.lidar.sintetico)) note.push("Falde dei tetti dal rilievo LiDAR sintetico di esempio: inventate.");
    if (stato.fvClima && stato.fvClima.sintetico) note.push("Producibilità calcolata con un anno di cielo sereno ridotto (sintetico): il clima orario del comune non era disponibile.");
    if (stato.firma && stato.firma.sintetici) note.push("Firma energetica calcolata con consumi e gradi giorno sintetici di esempio.");
    if (stato.facciate && stato.facciate.clima.sintetico) note.push("Sole sulle facciate calcolato con un anno di cielo sereno ridotto (sintetico).");
    if (stato.lontanoInfo) fonti.push(stato.lontanoInfo.fonte);
    if (stato.pvgis) fonti.push(stato.pvgis.fonte);
    if (stato.sede) note.push(`Edificio aperto dalla sede «${stato.sede.nome}» del Patrimonio` + (stato.sede.visura ? "; piani e superficie catastale dalle visure lette da EuGEnio Visure (non sostituiscono le visure ufficiali)." : "."));
    if (stato.obblighi && stato.obblighi.quota_vetrata_fonte === "stima") note.push("Quota di superfici vetrate stimata dall'uso dell'edificio: il limite della Tabella 11 va ricontrollato con il rilievo.");
    { const t = testoFontiCorpi(); if (t) note.push(t.replace(/ Il dettaglio.*$/, "")); }
    { const t = testoTettiStimati(); if (t) note.push(`${t} Falde, pendenze e superfici dei tetti di questi corpi sono stime.`); }
    if (stato.obblighi) fonti.push("D.Lgs. 8 novembre 2021, n. 199, art. 26 e Allegato III (testo vigente, Normattiva); DPR 412/93, Allegato A; DM 26/6/2015 come modificato dal DM 28/10/2025 (GU n. 283 del 5/12/2025)");
    return {
      tetti: stato.corpi.length ? { scelta: VISTA !== "modelli" && SELETTORE_TETTI() ? NOMI_SCELTA_TETTO[stato.formaTetti] : NOMI_SCELTA_TETTO.auto,
        testo: testoTetti(), conteggi: contaTetti() } : null,
      titolo: "Edificio in 3D", sintetico: stato.sintetico || !!(stato.firma && stato.firma.sintetici),
      edificio: { id: stato.edificio, nome: stato.modello ? `Modello dell'utente «${stato.modello}»` : `Edificio ${stato.edificio}`, comune: stato.comune ? stato.comune.nome : null },
      superfici: sup, geometria: stato.geometria,
      corpi: stato.corpi.map((c) => ({ id: c.id, area: E.areaCorpo(c), gronda: c.gronda, colmo: c.colmo, tetto: c.tetto, fonte_tetto: fonteTettoDi(c),
        piani: c.piani || E.stimaPiani(c.gronda, stato.uso || c.uso || "altro"), fonte_sagoma: c.fonte_sagoma, fonte_altezza: testoAltezza(c),
        licenza: c.licenza, qualita: c.qualita })),
      falde: stato.corpi.flatMap((c) => (c.falde || []).map((f) => ({ corpo: c.id, falda: f.id, pendenza: f.pendenza,
        orientamento: f.pendenza < 5 ? null : f.orientamento, superficie: f.superficie, area_pianta: f.area_pianta, fonte: f.fonte }))),
      firma: stato.firma ? { base: stato.firma.base, pendenza: stato.firma.pendenza, r2: stato.firma.r2, unita: stato.firma.unita, mesi: stato.firma.mesi } : null,
      consumi_normalizzati: stato.normalizzati || [],
      fv: stato.fv ? { aree: stato.aree.map((a) => { const c = conteggio(a), r = stato.fv.find((x) => x.id === a.id) || {};
        return { nome: `${a.id} (corpo ${a.corpo}${a.falda ? `, falda ${a.falda}` : ""})`, area: c.area, inclinazione: a.inclinazione, orientamento: a.orientamento, moduli: c.moduli, kwp: c.kwp,
          kwh_anno: r.kwh, perdita_ombre: r.perdita }; }), totale_kwh: stato.fv.reduce((s, x) => s + x.kwh, 0),
        anno_clima: stato.fvClima && !stato.fvClima.sintetico ? String(stato.fvClima.anno) : null, modello_cielo: "Perez (1990)" } : null,
      obblighi: stato.obblighi,
      facciate: stato.facciate ? { per_orientamento: E.SETTORI.filter((s) => stato.facciate.riepilogo[s].area).map((s) => ({ orientamento: s,
        ...stato.facciate.riepilogo[s] })), parti: stato.facciate.parti.length, anno_clima: stato.facciate.clima.sintetico ? null : String(stato.facciate.clima.anno),
        orizzonte_lontano: stato.facciate.lontano, modello_cielo: "Perez (1990)" } : null,
      orizzonte_lontano: stato.lontanoInfo ? { ...stato.lontanoInfo } : null,
      pvgis: stato.pvgis ? { aree: stato.pvgis.aree.map((x) => ({ id: x.id, eugenio_kwh: x.eugenio.kwh, pvgis_kwh: x.con_orizzonte.kwh_anno,
        pvgis_senza_kwh: x.senza_orizzonte_utente.kwh_anno, banca_dati: x.con_orizzonte.banca_dati, anni: x.con_orizzonte.anni })), fonte: stato.pvgis.fonte } : null,
      priorita: stato.priorita ? { pesi: stato.priorita.pesi, sedi: stato.priorita.righe.slice(0, 200).map((x) => ({ posto: x.posto, nome: x.nome,
        punteggio: x.punteggio, kwh_m2: x.kwh_m2, punteggi: x.punteggi, fonte: x.fonte })) } : null,
      immagini_png: [immagineMappa()].filter(Boolean),
      note, fonti,
    };
  }
  if (R) {
    const area = h("div", "messaggio"); area.id = "messaggio-report"; area.setAttribute("role", "status");
    $("report").appendChild(area);
    R.pulsanti($("report"), { tipo: "edificio", corpo: corpoReport, nome: (ext) => `edificio.${ext}`,
      messaggio: (t, e) => { area.textContent = t; area.classList.toggle("errore", !!e); }, area: "messaggio-report" });
  }

  // ------------------------------------------------------------------ modello dell'utente (DXF/IFC → GeoJSON, solo nel browser)
  const MAX_MODELLO_MB = 10, MAX_CORPI_MODELLO = 500;
  function controllaModello(d) {
    if (!d || d.type !== "FeatureCollection" || d.formato !== "eugenio-modello-1" || !Array.isArray(d.features))
      throw new Error("non è un modello di EuGEnio (serve il GeoJSON prodotto da «importa-modello»)");
    if (!d.features.length || d.features.length > MAX_CORPI_MODELLO) throw new Error(`da 1 a ${MAX_CORPI_MODELLO} corpi`);
    const fin = (v) => Number.isFinite(+v);
    return d.features.map((f, k) => {
      const g = f && f.geometry, p = (f && f.properties) || {};
      if (!g || g.type !== "Polygon" || !Array.isArray(g.coordinates) || !Array.isArray(g.coordinates[0])) throw new Error(`corpo ${k + 1}: sagoma non valida`);
      const anello = g.coordinates[0].slice(0, 5000);
      if (anello.length < 4 || !anello.every((q) => Array.isArray(q) && fin(q[0]) && fin(q[1]) && +q[0] > 6 && +q[0] < 19 && +q[1] > 35 && +q[1] < 48))
        throw new Error(`corpo ${k + 1}: coordinate fuori dall'Italia o non numeriche`);
      const gr = fin(p.gronda) && +p.gronda > 0 && +p.gronda < 300 ? +p.gronda : 3;
      return { type: "Feature", geometry: { type: "Polygon", coordinates: [anello.map((q) => [+q[0], +q[1]])] },
        properties: { id: `M${k + 1}`, edificio: "MODELLO", gronda: gr, colmo: fin(p.colmo) && +p.colmo > gr ? +p.colmo : null,
          tetto: ["piano", "monofalda", "capanna", "padiglione", "a falde"].includes(p.tetto) ? p.tetto : "piano",
          fonte_sagoma: "modello dell'utente", fonte_altezza: fin(p.gronda) ? "modello dell'utente" : "modello dell'utente (altezza da completare)",
          licenza: "dati dell'utente", falde: Array.isArray(p.falde) ? p.falde.slice(0, 60) : [] } };
    });
  }
  async function apriModello(testo, nome = "modello") {
    const fs = controllaModello(JSON.parse(testo));
    const ring0 = fs[0].geometry.coordinates[0];
    const lon = ring0.reduce((s, q) => s + q[0], 0) / ring0.length, lat = ring0.reduce((s, q) => s + q[1], 0) / ring0.length;
    stato.proj = E.proiezione(lon, lat);
    const archivio = (await contesto(lon, lat)).map((f) => conFalde(aCorpo(f), f.properties));
    const corpi = fs.map((f) => { const c = conFalde(aCorpo(f), f.properties); c.fonte_altezza = f.properties.fonte_altezza; return c; });
    // gli edifici dell'archivio sotto il modello si nascondono e non fanno da vicini
    const sotto = (c) => corpi.some((m) => E.dentro(E.centroide(c.ring), m.ring));
    stato.nascostiExtra = archivio.filter(sotto).map((c) => c.id);
    stato.vicini = archivio.filter((c) => !sotto(c) && Math.hypot(...E.centroide(c.ring)) <= RAGGIO + 60);
    stato.corpi = corpi; stato.edificio = "MODELLO"; stato.modello = String(nome).slice(0, 80);
    stato.aree = []; stato.firma = null; stato.fv = null; stato.sintetico = false;
    stato.q0 = Math.min(...corpi.map((c) => c.quota || 0)); stato.lontano = null; stato.facciate = null; stato.pvgis = null;
    stato.fvOrizzonti = {}; mostraFacciate();
    stato.comune = await comuneDi(lon, lat);
    await datiDpr();
    preparaSelettoreTetti(true); applicaTetti();
    stato.originali = corpi.map((c) => ({ ...c, ring: c.ring.map((q) => [...q]) }));
    $("avviso-sintetico").hidden = true;
    ["passo-corpi", "passo-superfici", "passo-geometria", "passo-obblighi", "passo-ombre", "passo-facciate", "passo-fv", "passo-pvgis",
      "passo-consumi", "passo-report"].forEach((id) => { $(id).hidden = false; });
    $("aggiungi-priorita").disabled = false; $("calcola-pvgis").disabled = true;
    messaggio("messaggio", `Modello «${stato.modello}»: ${corpi.length} ${corpi.length === 1 ? "corpo" : "corpi"} (letto solo in questo browser), `
      + `${stato.vicini.length} corpi vicini dall'archivio.` + (stato.comune ? ` Comune: ${stato.comune.nome}.` : ""));
    aggiorna();
    if (stato.mappa && !DUE_TEMPI) stato.mappa.easeTo({ center: [lon, lat], zoom: 17.6, duration: 600 });
    apriVista();
    if (DUE_TEMPI) { stato.daGenerare = null; entra3d(); }
    return true;
  }
  if ($("modello-file")) $("modello-file").addEventListener("change", async (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    try {
      if (f.size > MAX_MODELLO_MB * 1024 * 1024) throw new Error(`file oltre ${MAX_MODELLO_MB} MB`);
      if (/\.(dxf|ifc)$/i.test(f.name)) throw new Error("i DXF e gli IFC si aprono nella pagina «Importa DXF/IFC» (menu Patrimonio), che li converte in questo browser");
      await apriModello(await f.text(), f.name);
    } catch (err) {
      messaggio("messaggio", `Modello non aperto: ${err.message || err}`, true);
    } finally { e.target.value = ""; }
  });

  // ------------------------------------------------------------------ apertura secondo la pagina
  function apriVista() {
    const passo = { geometria: "passo-geometria", consumi: "passo-consumi", ombre: "passo-ombre", producibilita: "passo-fv",
      facciate: "passo-facciate", pvgis: "passo-pvgis", obblighi: "passo-obblighi", dlgs199: "passo-obblighi", priorita: "passo-priorita" }[VISTA];
    if (passo) {
      const p = $(passo);
      document.querySelectorAll(".pagina-edificio3d .passo").forEach((x) => x.classList.toggle("in-evidenza", x === p));
      if (VISTA === "ombre" && !stato.anima) $("anima").click();
    }
  }
  function numeraPassi() {
    let n = 0;
    document.querySelectorAll(".pagina-edificio3d .passo").forEach((p) => { const s = p.querySelector("h2 .n"); if (s) s.textContent = ++n; });
  }

  // ------------------------------------------------------------------ avvio
  (async function avvio() {
    numeraPassi();
    if ($("legenda-osm")) $("legenda-osm").hidden = true;
    try {
      const q0 = new URLSearchParams(location.search);
      if (DUE_TEMPI) {
        stato.archivi = await trovaArchivi();
        // aperta dal Patrimonio (?sede=locale) o con ?edificio=, senza archivio vero: si ripiega sulla demo dichiarata,
        // come prima del 05/11 (la pagina dice che nessun edificio contiene il punto della sede); l'ingresso semplice no
        // (07/11/2026 sera: solo se non c'è nemmeno il ripiego OSM, cioè la rotta risponde 404)
        if (!stato.archivi.length && !SCELTA && (q0.get("sede") === "locale" || q0.get("edificio")) && !(await osmDisponibile())) {
          try { stato.archivi = [{ base: "dati/edifici3d/", indice: await json("dati/edifici3d/indice.json") }]; } catch { /* niente demo */ }
        }
        if (stato.archivi.length) { stato.base = stato.archivi[0].base; stato.indice = stato.archivi[0].indice; }
        // DB topografico letto nel browser (07/11/2026): solo nella sessione aperta dalla pagina «Aggiungi edifici»
        if (!SCELTA && LOCALE && !(stato.indice && stato.indice.sintetico) && (q0.get("dbtr") === "locale" || LOCALE.attivo())) {
          if (q0.get("dbtr") === "locale") LOCALE.attiva();
          const d = await LOCALE.leggi();
          if (d && Array.isArray(d.features) && d.features.length) { stato.locale = archivioLocale(d); stato.archivi.push(stato.locale); }
        }
        // ripiego OSM (07/11/2026): fuori dagli archivi DBTR; mai nella demo né con ?archivio=
        if (!SCELTA && !(stato.indice && stato.indice.sintetico)) { stato.osmAttivo = true; stato.archivi.push(ARCHIVIO_OSM); }
      } else {
        const { base, indice } = await trovaBase();
        stato.base = base; stato.indice = indice;
      }
      const base = stato.base, indice = stato.indice;
      if (base) {
        // falde: con gli archivi per comune solo se archivi.json dice dove sono (07/11/2026 sera: niente 404 prima della pipeline)
        stato.lidar = DUE_TEMPI && !SCELTA && !stato.baseLidar && !(indice && indice.sintetico) ? null : await json(`${stato.baseLidar || base}lidar/indice.json`).catch(() => null);
        if (stato.lidar) $("fonti-3d").append(" ", h("span", null, "Falde dei tetti: " + Object.values(stato.lidar.attribuzioni || {})
          .map((a) => `${a.attribuzione || a.descrizione} (${a.licenza})`).join("; ") + "."));
        if (indice.sintetico) $("avviso-sintetico").hidden = false;
        // una riga per attribuzione (i DBTR dei comuni hanno tutti la stessa)
        [...new Set(veri().slice(1).concat(indice.attribuzione ? [{ indice }] : []).map((a) => a.indice.attribuzione).filter(Boolean))]
          .forEach((t) => $("fonti-3d").append(" ", h("span", null, `Questo archivio: ${t}.`)));
      }
      if (stato.locale && $("fonti-3d")) {
        const o = h("span", null, `Edifici del tuo file: ${stato.locale.indice.attribuzione}. `);
        const b = h("button", "bottone secondario piccolo", "Togli gli edifici del file"); b.type = "button"; b.id = "togli-locale";
        b.addEventListener("click", async () => { await LOCALE.togli(); location.href = location.pathname; });
        o.appendChild(b); $("fonti-3d").append(" ", o);
      }
      if (stato.osmAttivo && $("fonti-3d")) {
        const o = h("span", null, "Fuori dal DBTR (ripiego): in Veneto sagome della Regione del Veneto – Edifici del Veneto (feb. 2022), IODL 2.0, "
          + "con le altezze di OpenStreetMap; altrove edifici © OpenStreetMap contributors, ODbL 1.0; altezze in parte stimate.");
        o.id = "fonti-osm"; o.hidden = true; $("fonti-3d").append(" ", o);
      }
      stato.mappa = await creaMappa();
      // livelli sopra la foto (particelle, contorni degli edifici): non nella demo, i cui edifici sono inventati
      if (DUE_TEMPI && window.EUGENIO_STRATI && $("caselle-strati")) {
        if (indice && indice.sintetico) {
          $("caselle-strati").append(h("p", "aiuto-breve", "Particelle e contorni degli edifici non si mostrano sulla demo sintetica (edifici inventati)."));
        } else {
          try {
            const m = stato.mappa;
            stato.strati = await window.EUGENIO_STRATI.aggiungi(m, { caselle: $("caselle-strati"), legenda: $("legenda-strati"),
              sotto: () => (m.getLayer("rilievo") ? "rilievo" : "ombre") });
          } catch { /* strati non disponibili */ }
        }
      }
      if (DUE_TEMPI && !(indice && indice.sintetico)) controlliAspetto3d();
      caricaOrtofoto();
      if (DUE_TEMPI && window.EUGENIO_ESPORTA) window.EUGENIO_ESPORTA.pulsanti($("scarica-3d"), stato.mappa, opzioniImmagine, $("messaggio-immagine"));
      // demo sintetica: si esce sempre con «Esci dalla demo», che riapre la pagina normale (mappa 2D vera, ortofoto, ricerca)
      if (DUE_TEMPI && indice && indice.sintetico && $("esci-demo")) { $("esci-demo").hidden = false; $("apri-demo").hidden = true; }
      const q = new URLSearchParams(location.search);
      if (DUE_TEMPI && stato.locale) {
        const r = stato.locale.indice.riquadro;
        stato.mappa.fitBounds([[r[0], r[1]], [r[2], r[3]]], { padding: 30, duration: 0, maxZoom: 16 });
        messaggio("messaggio", `Edifici del tuo file «${stato.locale.indice.nome}»: ${stato.locale.features.length.toLocaleString("it-IT")} corpi, letti solo in `
          + "questo browser. Avvicinati e fai clic su un edificio (o cercalo con l'indirizzo), poi «Genera il 3D»."
          + (stato.osmAttivo ? " Fuori dalla zona del file (tratteggiata) valgono gli archivi del server e il ripiego OpenStreetMap." : ""));
      } else if (DUE_TEMPI) {
        if (!base) {
          $("apri-demo").hidden = false;
          messaggio("messaggio", stato.osmAttivo
            ? "L'archivio DBTR degli edifici non è ancora sul server: cerca un indirizzo o fai clic su un edificio; si useranno gli edifici di "
              + "OpenStreetMap come ripiego (qualità inferiore, altezze in parte stimate). C'è anche la demo sintetica (edifici inventati)."
            : "L'archivio degli edifici non è ancora sul server: puoi cercare un indirizzo e guardare la zona, ma il 3D "
            + "si genera solo dove ci sono le sagome. Per vedere come funziona c'è la demo sintetica (edifici inventati).");
          // la regione della piccola mappa (predefinita l'Emilia-Romagna)
          const cod = (window.EUGENIO && window.EUGENIO.regione) || "08";
          if (!q.get("modello") && !q.get("sede") && !partenza()) await vaiRegione(cod);
        } else if (indice.sintetico) {
          messaggio("messaggio", "Demo sintetica: isolato inventato vicino a Rimini, senza foto sotto (non corrisponde a edifici veri). "
            + "Fai clic su un edificio (E-DEMO è l'esempio a tre corpi, con la torre), poi «Genera il 3D». Per tornare alla mappa vera: «Esci dalla demo».");
        } else {
          messaggio("messaggio", "Avvicinati e fai clic su un edificio (o cercalo con l'indirizzo), poi «Genera il 3D»."
            + (stato.osmAttivo ? " Fuori dalle zone del DBTR (tratteggiate) si usano gli edifici di OpenStreetMap come ripiego." : ""));
          // (08/11/2026) regione scelta diversa dall'Emilia-Romagna e nessuna indicazione nell'indirizzo: si apre su di lei
          const cod = (window.EUGENIO && window.EUGENIO.regione) || "08";
          if (cod !== "08" && !["modello", "sede", "edificio", "lat", "lon", "dbtr"].some((k) => q.get(k))) await vaiRegione(cod);
        }
      } else {
        messaggio("messaggio", indice.sintetico ? "Isolato sintetico di prova: fai clic su un edificio (quello arancione più alto è l'esempio a tre corpi)." : "Fai clic su un edificio.");
      }
      // modello passato dalla pagina «Importa DXF/IFC» nella memoria di questa scheda (mai dal server)
      if (q.get("modello") === "locale") {
        let m = null;
        try { m = JSON.parse(sessionStorage.getItem("eugenio-modello") || "null"); sessionStorage.removeItem("eugenio-modello"); } catch { m = null; }
        try { history.replaceState(null, "", location.pathname); } catch { /* niente */ }
        if (m && m.testo) {
          try { await apriModello(m.testo, m.nome || "modello"); return; }
          catch (err) { messaggio("messaggio", `Modello non aperto: ${err.message || err}`, true); return; }
        }
        messaggio("messaggio", "Il modello importato non è più nella memoria della scheda: riaprilo dalla pagina «Importa DXF/IFC» o con «Usa il tuo modello».", true);
        return;
      }
      // sede passata dalla pagina Patrimonio nella memoria di questa scheda (mai dal server): si apre l'edificio che
      // contiene il punto della sede, con le sue colonne facoltative e le colonne visura_…
      if (q.get("sede") === "locale") {
        let sd = null;
        try { sd = JSON.parse(sessionStorage.getItem("eugenio-sede") || "null"); } catch { sd = null; }
        try { history.replaceState(null, "", location.pathname); } catch { /* niente */ }
        if (sd && Number.isFinite(+sd.lat) && Number.isFinite(+sd.lon)) {
          const fs = await contesto(+sd.lon, +sd.lat);
          const f = edificioNelPunto(fs, +sd.lon, +sd.lat);
          if (f) { if (await scegli(String(f.properties.edificio), +sd.lon, +sd.lat, sd)) entra3d(); return; }
          stato.mappa.easeTo({ center: [+sd.lon, +sd.lat], zoom: DUE_TEMPI ? ZOOM_CERCA : 17.6, duration: 600 });
          messaggio("messaggio", await nessunEdificio(+sd.lon, +sd.lat, `Sede «${sd.nome}» (punto dalla geolocalizzazione del Patrimonio): `), true);
          return;
        }
      }
      if (!indice) return;
      const scelto = q.get("edificio") || (indice.sintetico && VISTA !== "modelli" && !DUE_TEMPI ? "E-DEMO" : null);
      if (scelto) {
        // ?edificio=<id>&lon=&lat= (07/11/2026 sera: con gli archivi per comune serve il punto; senza, il centro del primo archivio)
        const lo = +q.get("lon"), la = +q.get("lat"), conPunto = Number.isFinite(lo) && Number.isFinite(la) && q.get("lon") && q.get("lat");
        const [x0, y0] = conPunto ? [lo, la] : indice.centro;
        const fs = await contesto(x0, y0);
        const f = fs.find((x) => String(x.properties.edificio) === scelto);
        if (f) { const c = anelli(f.geometry)[0][0]; if (await scegli(scelto, conPunto ? x0 : c[0], conPunto ? y0 : c[1])) entra3d(); }
        else messaggio("messaggio", `Edificio «${scelto}» non trovato${conPunto ? " vicino al punto indicato" : " nell'archivio"}: cercalo con l'indirizzo o con un clic.`, true);
      }
    } catch (e) {
      console.warn(e);
      messaggio("messaggio", `La mappa 3D non si è aperta: ${e.message || e}. Serve un browser con WebGL.`, true);
    }
  })();
  window.EUGENIO_EDIFICIO3D = { stato, corpoReport, scegli, apriModello, edificioNelPunto, alberiVicini, ostacoliRelativi, genera, entra3d, esci3d,
    vistaNominata, opzioniImmagine, livelloFonte, scegli2d, impostaPunto, puntoCambiato, trovato, coperto, nessunEdificio, geojson, edificiOsm,
    esagera, fonteTerreno, testoAltezza, lontanoDal3d, testoTetti, contaTetti, cambiaFormaTetti };
})();
