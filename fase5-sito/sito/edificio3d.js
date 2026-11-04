"use strict";
// Strumento 3D degli edifici (fase 10, Fase A): pagine Modelli 3D, Edificio › Geometria, Edificio › Consumi,
// Fotovoltaico › Ombre e Fotovoltaico › Producibilità. Stessa pagina, con un'apertura diversa (data-vista sul <main>).
//
// Dati (file statici serviti da Caddy, vedi fase4-server/Caddyfile, o la demo sintetica in dati/edifici3d/):
//   <base>/indice.json          centro, riquadro, celle, licenza, attribuzione, sintetico
//   <base>/corpi.pmtiles        corpi estrusi (MapLibre, protocollo pmtiles)
//   <base>/terreno.pmtiles      terreno raster-dem in codifica Terrarium
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
  const fmt = (v, d = 0) => (v === null || v === undefined || !Number.isFinite(+v) ? "—" : (+v).toLocaleString("it-IT", { maximumFractionDigits: d, minimumFractionDigits: d }));
  const NOMI_FONTE = { csv: "dato inserito", visura: "visura", stima: "stima", mancante: "—", "dato del corpo": "dato del corpo" };
  const stato = { base: null, indice: null, mappa: null, celle: new Map(), corpi: [], originali: [], edificio: null, vicini: [],
    proj: null, istat: null, comune: null, csv: {}, uso: "", aree: [], modo: null, punti: [], anima: null, firma: null, fv: null,
    giornaliero: null, sintetico: false, ortofoto: null, fontiOrtofoto: [], lontano: null, facciate: null, pvgis: null,
    fvOrizzonti: {}, obblighi: null, dpr: null, lidar: null, falde: new Map(), celleFalde: new Map(), nascostiExtra: [], modello: null };

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
  async function cella(nome) {
    if (!stato.celle.has(nome)) stato.celle.set(nome, json(`${stato.base}contesto/${nome}.json`).catch(() => ({ features: [] })));
    return stato.celle.get(nome);
  }
  // falde dal LiDAR (stesse celle di 0,01°, indicizzate per corpo); senza rilievo la cella non c'è
  async function cellaFalde(nome) {
    if (!stato.celleFalde.has(nome)) {
      stato.celleFalde.set(nome, json(`${stato.base}lidar/falde/${nome}.json`).then((d) => {
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
  async function contesto(lon, lat) {
    const c = stato.indice.cella || 0.01, dlon = RAGGIO / (111320 * Math.cos(lat * Math.PI / 180)), dlat = RAGGIO / 110574;
    const nomi = [];
    for (let i = Math.floor((lon - dlon) / c); i <= Math.floor((lon + dlon) / c); i++)
      for (let j = Math.floor((lat - dlat) / c); j <= Math.floor((lat + dlat) / c); j++) nomi.push(`${i}_${j}`);
    const [fc] = await Promise.all([Promise.all(nomi.map(cella)), stato.lidar ? Promise.all(nomi.map(cellaFalde)) : null]);
    const visti = new Map();
    fc.forEach((x) => (x.features || []).forEach((f) => visti.set(String(f.properties.id), f)));
    return [...visti.values()];
  }
  function aCorpo(f) {
    const p = f.properties, ring = (f.geometry.type === "MultiPolygon" ? f.geometry.coordinates[0][0] : f.geometry.coordinates[0]).map(stato.proj.avanti);
    return { id: String(p.id), edificio: String(p.edificio), ring, lonlat: f.geometry, gronda: +p.gronda, colmo: p.colmo ? +p.colmo : null,
      tetto: p.tetto || "piano", falde: +p.falde || 0, piani: p.piani ? +p.piani : null, quota: p.quota_terreno !== undefined ? +p.quota_terreno : 0,
      fonte_sagoma: p.fonte_sagoma || "", fonte_altezza: p.fonte_altezza || "", licenza: p.licenza || "", qualita: p.qualita || "",
      uso: p.uso || null, sintetico: !!p.sintetico, modificato: false, falde: null, lidar: null };
  }
  // un corpo con le sue falde: prima il modello dell'utente, poi il LiDAR, altrimenti la stima del DBTR
  function conFalde(c, p) {
    if (Array.isArray(p.falde) && p.falde.length) {               // modello dell'utente (importa-modello)
      c.falde = faldeLocali(p.falde, p.fonte_altezza || "modello dell'utente");
      return c;
    }
    const r = stato.falde.get(c.id);
    if (!r) return c;
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

  // ------------------------------------------------------------------ mappa
  async function creaMappa() {
    const ml = window.maplibregl;
    if (!ml) throw new Error("libreria della mappa non caricata");
    const proto = new window.pmtiles.Protocol();
    ml.addProtocol("pmtiles", proto.tile);
    const abs = (p) => new URL(p, location.href).href;
    const [lon, lat] = stato.indice.centro;
    const m = new ml.Map({
      container: "mappa3d", center: [lon, lat], zoom: 17.2, pitch: 55, bearing: -20, maxPitch: 80, attributionControl: false,
      // per copiare la vista nel report (immagine con l'ortofoto)
      canvasContextAttributes: { preserveDrawingBuffer: true },
      style: {
        version: 8,
        sources: {
          terreno: { type: "raster-dem", url: `pmtiles://${abs(stato.base + "terreno.pmtiles")}`, encoding: "terrarium", tileSize: 256 },
          rilievo: { type: "raster-dem", url: `pmtiles://${abs(stato.base + "terreno.pmtiles")}`, encoding: "terrarium", tileSize: 256 },
          corpi: { type: "vector", url: `pmtiles://${abs(stato.base + "corpi.pmtiles")}`,
            attribution: stato.indice.attribuzione || "" },
          ombre: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
          scelto: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
          fv: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
          linea: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
          facciate: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
          falde: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
        },
        layers: [
          { id: "sfondo", type: "background", paint: { "background-color": colore("--carta") } },
          { id: "rilievo", type: "hillshade", source: "rilievo", paint: { "hillshade-exaggeration": 0.4, "hillshade-shadow-color": colore("--linea") } },
          { id: "ombre", type: "fill", source: "ombre", paint: { "fill-color": "#000", "fill-opacity": 0.32 } },
          { id: "corpi", type: "fill-extrusion", source: "corpi", "source-layer": "corpi",
            paint: { "fill-extrusion-color": colore("--serie-6"), "fill-extrusion-height": ["+", ["get", "altezza"], 0],
              "fill-extrusion-base": 0, "fill-extrusion-opacity": 0.85 } },
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
          { id: "linea", type: "line", source: "linea", paint: { "line-color": colore("--segno"), "line-width": 3 } },
        ],
      },
    });
    m.addControl(new ml.NavigationControl({ visualizePitch: true }), "top-right");
    m.addControl(new ml.AttributionControl({ compact: true, customAttribution: "MapLibre" }), "bottom-right");
    await new Promise((ok) => m.on("load", ok));
    try { m.setTerrain({ source: "terreno", exaggeration: 1 }); } catch { /* terreno non disponibile: mappa piatta */ }
    m.on("click", (e) => clic(e));
    m.on("mousemove", (e) => {
      const f = m.queryRenderedFeatures(e.point, { layers: ["corpi", "scelto"] });
      m.getCanvas().style.cursor = stato.modo ? "crosshair" : f.length ? "pointer" : "";
    });
    document.addEventListener("eugenio:aspetto", () => {
      m.setPaintProperty("sfondo", "background-color", colore("--carta"));
      m.setPaintProperty("corpi", "fill-extrusion-color", colore("--serie-6"));
      m.setPaintProperty("scelto", "fill-extrusion-color", colore("--primario"));
      m.setPaintProperty("linea", "line-color", colore("--segno"));
    });
    document.addEventListener("eugenio:ridimensiona", () => m.resize());
    return m;
  }

  function inclinate(c) { return (c.falde || []).filter((f) => f.pendenza >= 5 && Number.isFinite(f.alto) && Number.isFinite(f.basso)); }
  function geojson(corpi, quotaBase = false) {
    return { type: "FeatureCollection", features: corpi.map((c) => ({ type: "Feature",
      // con le falde inclinate il prisma arriva alla gronda e sopra si vedono le falde a gradini
      properties: { id: c.id, altezza: inclinate(c).length ? c.gronda : (c.colmo || c.gronda), quota: quotaBase ? c.quota : 0 },
      geometry: { type: "Polygon", coordinates: [E.chiudi(c.ring).map(stato.proj.indietro)] } })) };
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
    // corpi modificati o divisi: si nasconde la loro versione nelle tessere
    const nascosti = [...new Set(stato.originali.map((c) => c.id).concat(stato.nascostiExtra))];
    m.setFilter("corpi", nascosti.length ? ["!", ["in", ["get", "id"], ["literal", nascosti]]] : null);
    m.getSource("fv").setData({ type: "FeatureCollection", features: stato.aree.map((a) => ({ type: "Feature",
      properties: { quota: a.quota }, geometry: { type: "Polygon", coordinates: [E.chiudi(a.ring).map(stato.proj.indietro)] } })) });
    ombre();
  }

  // ------------------------------------------------------------------ selezione
  async function clic(e) {
    const p = stato.proj ? stato.proj.avanti([e.lngLat.lng, e.lngLat.lat]) : null;
    if (stato.modo === "dividi") return puntoDivisione(p);
    if (stato.modo === "fv") return aggiungiArea(p);
    const f = stato.mappa.queryRenderedFeatures(e.point, { layers: ["scelto", "corpi"] });
    if (!f.length) return;
    const edificio = String(f[0].properties.edificio || "");
    if (f[0].layer.id === "scelto" && stato.edificio) return;
    await scegli(edificio, e.lngLat.lng, e.lngLat.lat);
  }

  async function scegli(edificio, lon, lat) {
    messaggio("messaggio", "Carico gli edifici nel raggio di 250 m…");
    stato.proj = E.proiezione(lon, lat);
    const fs = await contesto(lon, lat);
    const tutti = fs.map((f) => conFalde(aCorpo(f), f.properties));
    const corpi = tutti.filter((c) => c.edificio === edificio);
    if (!corpi.length) { messaggio("messaggio", "Edificio non trovato nell'archivio.", true); return; }
    const centro = E.centroide(corpi[0].ring);
    stato.vicini = tutti.filter((c) => c.edificio !== edificio && Math.hypot(...E.centroide(c.ring).map((v, i) => v - centro[i])) <= RAGGIO + 60);
    stato.modello = null; stato.nascostiExtra = [];
    stato.corpi = corpi; stato.edificio = edificio; stato.originali = corpi.map((c) => ({ ...c, ring: c.ring.map((p) => [...p]) }));
    stato.aree = []; stato.firma = null; stato.fv = null; stato.sintetico = corpi.some((c) => c.sintetico);
    stato.q0 = Math.min(...corpi.map((c) => c.quota || 0)); stato.lontano = null; stato.facciate = null; stato.pvgis = null;
    stato.fvOrizzonti = {}; mostraFacciate();
    stato.comune = await comuneDi(lon, lat);
    $("avviso-sintetico").hidden = !stato.sintetico;
    ["passo-corpi", "passo-superfici", "passo-geometria", "passo-obblighi", "passo-ombre", "passo-facciate", "passo-fv", "passo-pvgis",
      "passo-consumi", "passo-report"].forEach((id) => { $(id).hidden = false; });
    $("aggiungi-priorita").disabled = false; $("calcola-pvgis").disabled = true;
    messaggio("messaggio", `Edificio ${edificio}: ${corpi.length} ${corpi.length === 1 ? "corpo" : "corpi"}, ${stato.vicini.length} corpi vicini.`
      + (stato.comune ? ` Comune: ${stato.comune.nome}.` : ""));
    aggiorna();
    stato.mappa.easeTo({ center: [lon, lat], zoom: 17.6, duration: 600 });
    apriVista();
  }

  // comune che contiene il punto (confini ISTAT del sito, dati/mappa/08.json, stesse coordinate di patrimonio.js)
  async function comuneDi(lon, lat) {
    try {
      const m = await json("dati/mappa/08.json?v=20261104c");
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
      if (chiave !== "piani") c.falde = null;          // le falde misurate non valgono più per il corpo corretto
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
      r.appendChild(h("td", "num", fmt(E.area(c.ring))));
      const g = h("td", "num"); g.appendChild(campo(c, "gronda", 0.5, 0.5)); r.appendChild(g);
      const k = h("td", "num"); k.appendChild(campo(c, "colmo", 0.5, 0)); r.appendChild(k);
      const tt = h("td"); const s = h("select");
      [["piano", "piano"], ["monofalda", "a una falda"], ["capanna", "a capanna"], ["padiglione", "a padiglione"]].forEach(([v, n]) => { const o = h("option", null, n); o.value = v; o.selected = c.tetto === v; s.appendChild(o); });
      s.setAttribute("aria-label", `Tetto del corpo ${c.id}`);
      s.addEventListener("change", () => {
        c.tetto = s.value;
        if (c.tetto === "piano") c.colmo = null; else if (!c.colmo || c.colmo <= c.gronda) c.colmo = c.gronda + 3;
        c.modificato = true; c.fonte_altezza = "dato dell'utente"; c.falde = null; aggiorna();
      });
      tt.appendChild(s); r.appendChild(tt);
      const p = h("td", "num"); p.appendChild(campo(c, "piani", 1, 1)); r.appendChild(p);
      const f = h("td", "fonte"); f.append(c.fonte_altezza || "—"); f.appendChild(h("small", null, `${c.fonte_sagoma} · ${c.licenza}`)); r.appendChild(f);
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
        + ": tetti stimati dal DBTR (piani, salvo correzioni)." + (note.length ? ` ${note.join("; ")}.` : ""));
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
    const sint = con.some((c) => c.lidar && c.lidar.sintetico);
    messaggio("messaggio-falde", `${con.reduce((s, c) => s + c.falde.length, 0)} falde in ${con.length} ${con.length === 1 ? "corpo" : "corpi"}`
      + (sint ? " dal rilievo LiDAR sintetico di esempio (inventato)." : ".") + (note.length ? ` ${note.join("; ")}.` : ""), sint);
  }
  function schedaEdificio() {
    const d = $("scheda-edificio"); d.hidden = false; d.innerHTML = "";
    const voci = [["Edificio", stato.edificio], ["Comune", stato.comune ? stato.comune.nome : "—"], ["Corpi", stato.corpi.length],
      ["Licenza delle sagome", [...new Set(stato.corpi.map((c) => c.licenza))].join(", ")]];
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
      return parti.map((r, k) => ({ ...c, id: `${c.id}.${k + 1}`, ring: r, modificato: true, falde: null, fonte_sagoma: `${c.fonte_sagoma} (divisa dall'utente)` }));
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
    stato.corpi = stato.originali.map((c) => ({ ...c, ring: c.ring.map((p) => [...p]) })); stato.aree = []; aggiorna();
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && stato.modo) finisciModo(); });

  // ------------------------------------------------------------------ piani e superfici
  function superfici() {
    const corpi = stato.corpi.map((c) => ({ ...c, uso: stato.uso || c.uso || "altro" }));
    const s = E.superfici(corpi, stato.csv, {});
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
    const tutti = [...stato.corpi, ...stato.vicini];
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
    const c = stato.corpi.find((x) => E.dentro(p, x.ring));
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
    const fuori = ring.some((q) => !E.dentro(q, c.ring));
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
        i.addEventListener("change", () => { a[kk] = E.numero(i.value) || 0; stato.fv = null; tabellaFv(); });
        td.appendChild(i); r.appendChild(td);
      }
      const tm = h("td"), sm = h("select");
      [["telai", "su telai"], ["aderente", "aderente"]].forEach(([v, n]) => { const o = h("option", null, n); o.value = v; o.selected = a.montaggio === v; sm.appendChild(o); });
      sm.addEventListener("change", () => { a.montaggio = sm.value; stato.fv = null; tabellaFv(); });
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
      try { lavoratore = lavoratore || new Worker("ombre_worker.js?v=20261104c"); } catch (e) { ko(e); return; }
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
        : " Orizzonte: solo edifici entro 250 m (il terreno lontano non è disponibile ora)."), !!cl.sintetico);
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
  function ostacoliRelativi() {
    return [...stato.corpi, ...stato.vicini].map((c) => ({ ring: c.ring, cima: rel(c) + (c.colmo || c.gronda) }));
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
  async function caricaOrtofoto() {
    const sel = $("sfondo-ortofoto");
    if (!sel) return;
    let fonti = [];
    try {
      const r = await fetch("/api/ortofoto/fonti");
      if (r.ok && /json/.test(r.headers.get("Content-Type") || "")) fonti = (await r.json()).fonti || [];
    } catch { /* senza server niente ortofoto */ }
    const [lon, lat] = stato.indice.centro;
    stato.fontiOrtofoto = fonti.filter((f) => lon >= f.riquadro[0] && lon <= f.riquadro[2] && lat >= f.riquadro[1] && lat <= f.riquadro[3]);
    if (!stato.fontiOrtofoto.length) { sel.disabled = true; sel.options[0].textContent = "ortofoto non disponibili"; return; }
    stato.fontiOrtofoto.forEach((f) => { const o = h("option", null, f.nome + (f.stato === "da confermare" ? " (licenza da confermare)" : "")); o.value = f.id; sel.appendChild(o); });
    sel.addEventListener("change", () => sfondo(sel.value));
    // con i dati veri si accende subito la migliore; con la demo sintetica resta spenta (sagome inventate su foto vere)
    if (!stato.indice.sintetico) { sel.value = stato.fontiOrtofoto[0].id; sfondo(sel.value); }
  }
  function sfondo(id) {
    const m = stato.mappa, f = stato.fontiOrtofoto.find((x) => x.id === id) || null;
    if (m.getLayer("ortofoto")) m.removeLayer("ortofoto");
    if (m.getSource("ortofoto")) m.removeSource("ortofoto");
    stato.ortofoto = f;
    const att = $("attribuzione-ortofoto");
    if (!f) { att.hidden = true; return; }
    m.addSource("ortofoto", { type: "raster", tiles: [location.origin + f.tessere], tileSize: 256, minzoom: f.zoom[0], maxzoom: f.zoom[1],
      attribution: `${f.citazione}` });
    m.addLayer({ id: "ortofoto", type: "raster", source: "ortofoto", paint: { "raster-opacity": 1 } }, "ombre");
    att.hidden = false; att.innerHTML = "";
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
      return { titolo: `Vista 3D dell'edificio con l'ortofoto. ${f.citazione}`, png: dati.split(",")[1], ortofoto: { id: f.id, licenza: f.licenza, citazione: f.citazione, scheda: f.scheda } };
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
        : ` Clima orario del ${cl.anno}.`) + (lont ? "" : " Orizzonte del terreno lontano non disponibile: solo edifici vicini."), !!cl.sintetico);
    } catch (e) {
      console.warn(e); messaggio("messaggio-facciate", `Calcolo non riuscito: ${e.message || e}`, true);
    } finally { b.disabled = false; }
  });
  function tabellaFacciate() {
    const R = stato.facciate.riepilogo, box = $("facciate"); box.innerHTML = "";
    const t = h("table"), r1 = t.createTHead().insertRow();
    ["Orientamento", "Esposta (m²)", "kWh/m² anno", "kWh anno", "Estate giu–ago (kWh)", "Inverno dic–feb (kWh)", "Ombre"].forEach((x, k) => r1.appendChild(h("th", k ? "num" : null, x)));
    const b = t.createTBody();
    E.SETTORI.forEach((s) => {
      const x = R[s]; if (!x.area) return;
      const r = b.insertRow(); r.appendChild(h("th", null, s));
      [[x.area, 0], [x.kwh_m2, 0], [x.kwh, 0], [x.estate, 0], [x.inverno, 0]].forEach(([v, d]) => r.appendChild(h("td", "num", fmt(v, d))));
      r.appendChild(h("td", "num", `−${fmt(x.perdita, 1)} %`));
    });
    box.appendChild(t);
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
    box.appendChild(t);
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
      try { stato.dpr = await json("dati/dpr412.json?v=20261104c"); } catch { /* senza file: niente zona */ }
    }
    return stato.dpr || null;
  }
  async function obblighi() {
    const box = $("obblighi");
    if (!box || !stato.edificio) return;
    const S = stato.corpi.reduce((s, c) => s + E.area(c.ring), 0);
    const intervento = $("intervento-199").value, pubblico = $("pubblico-199").checked;
    const o = E.obbligoFer(S, { intervento, pubblico });
    const kwpFv = stato.aree.reduce((s, a) => s + conteggio(a).kwp, 0);
    const dpr = await datiDpr(), riga = dpr && stato.comune ? dpr.comuni[stato.comune.istat] : null;
    const zona = riga ? riga[1] : null, gg = riga ? riga[0] : null, sv = stato.geometria ? stato.geometria.s_su_v : null;
    const ht = E.htMassimo(zona, sv);
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
    ];
    stato.obblighi = { intervento: NOMI_INTERVENTO[intervento], pubblico, superficie: S, k: o.k, kw: o.kw, kwp_fv: kwpFv,
      quota_acs: o.quota_acs, quota_totale: o.quota_totale, zona, gg, s_su_v: sv, ht_max: ht ? ht.valore : null, ht_fascia: ht ? ht.fascia : null,
      righe: righe.map(([v, x, r]) => ({ voce: v, valore: x, riferimento: r })) };
    box.innerHTML = "";
    const t = h("table"), r1 = t.createTHead().insertRow();
    ["Voce", "Valore", "Riferimento"].forEach((x) => r1.appendChild(h("th", null, x)));
    const b = t.createTBody();
    righe.forEach(([v, x, r]) => { const tr = b.insertRow(); tr.appendChild(h("th", null, v)); tr.appendChild(h("td", null, x)); tr.appendChild(h("td", "fonte", r)); });
    box.appendChild(t);
    const telai = stato.aree.some((a) => a.montaggio === "telai");
    $("nota-obblighi").textContent = "Le quote di copertura valgono sui consumi previsti dal progetto (servono le metodiche di calcolo, qui non "
      + "fatte); la potenza minima si può coprire anche con altre fonti rinnovabili. Gli impianti a terra non contano; quelli nelle pertinenze sì "
      + "(All. III, sez. C, punto 2). Valori dell'atto normativo vigente (Normattiva, 04/11/2026): le Regioni possono alzarli (art. 26, comma 7)."
      + (telai ? " Tetti piani: l'asse dei moduli non deve superare la balaustra o, senza balaustra, 30 cm dal piano (sez. C, punto 3): controlla i telai." : "");
  }
  ["intervento-199", "pubblico-199"].forEach((id) => $(id).addEventListener("change", obblighi));

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
    if (stato.indice && stato.indice.attribuzione) fonti.push(stato.indice.attribuzione);
    const note = [];
    if (stato.lidar && stato.corpi.some((c) => c.lidar && c.lidar.stato === "ok"))
      Object.values(stato.lidar.attribuzioni || {}).forEach((a) => fonti.push(`Falde dei tetti: ${a.attribuzione || a.descrizione} (${a.licenza})`));
    if (stato.corpi.some((c) => c.lidar && c.lidar.sintetico)) note.push("Falde dei tetti dal rilievo LiDAR sintetico di esempio: inventate.");
    if (stato.fvClima && stato.fvClima.sintetico) note.push("Producibilità calcolata con un anno di cielo sereno ridotto (sintetico): il clima orario del comune non era disponibile.");
    if (stato.firma && stato.firma.sintetici) note.push("Firma energetica calcolata con consumi e gradi giorno sintetici di esempio.");
    if (stato.facciate && stato.facciate.clima.sintetico) note.push("Sole sulle facciate calcolato con un anno di cielo sereno ridotto (sintetico).");
    if (stato.lontanoInfo) fonti.push(stato.lontanoInfo.fonte);
    if (stato.pvgis) fonti.push(stato.pvgis.fonte);
    if (stato.obblighi) fonti.push("D.Lgs. 8 novembre 2021, n. 199, art. 26 e Allegato III (testo vigente, Normattiva); DPR 412/93, Allegato A; DM 26/6/2015 come modificato dal DM 28/10/2025 (GU n. 283 del 5/12/2025)");
    return {
      titolo: "Edificio in 3D", sintetico: stato.sintetico || !!(stato.firma && stato.firma.sintetici),
      edificio: { id: stato.edificio, nome: stato.modello ? `Modello dell'utente «${stato.modello}»` : `Edificio ${stato.edificio}`, comune: stato.comune ? stato.comune.nome : null },
      superfici: sup, geometria: stato.geometria,
      corpi: stato.corpi.map((c) => ({ id: c.id, area: E.area(c.ring), gronda: c.gronda, colmo: c.colmo, tetto: c.tetto,
        piani: c.piani || E.stimaPiani(c.gronda, stato.uso || c.uso || "altro"), fonte_sagoma: c.fonte_sagoma, fonte_altezza: c.fonte_altezza,
        licenza: c.licenza, qualita: c.qualita })),
      falde: stato.corpi.flatMap((c) => (c.falde || []).map((f) => ({ corpo: c.id, falda: f.id, pendenza: f.pendenza,
        orientamento: f.pendenza < 5 ? null : f.orientamento, superficie: f.superficie, area_pianta: f.area_pianta, fonte: f.fonte }))),
      firma: stato.firma ? { base: stato.firma.base, pendenza: stato.firma.pendenza, r2: stato.firma.r2, unita: stato.firma.unita, mesi: stato.firma.mesi } : null,
      consumi_normalizzati: stato.normalizzati || [],
      fv: stato.fv ? { aree: stato.aree.map((a) => { const c = conteggio(a), r = stato.fv.find((x) => x.id === a.id) || {};
        return { nome: `${a.id} (corpo ${a.corpo}${a.falda ? `, falda ${a.falda}` : ""})`, area: c.area, inclinazione: a.inclinazione, orientamento: a.orientamento, moduli: c.moduli, kwp: c.kwp,
          kwh_anno: r.kwh, perdita_ombre: r.perdita }; }), totale_kwh: stato.fv.reduce((s, x) => s + x.kwh, 0),
        anno_clima: stato.fvClima && !stato.fvClima.sintetico ? String(stato.fvClima.anno) : null } : null,
      obblighi: stato.obblighi,
      facciate: stato.facciate ? { per_orientamento: E.SETTORI.filter((s) => stato.facciate.riepilogo[s].area).map((s) => ({ orientamento: s,
        ...stato.facciate.riepilogo[s] })), parti: stato.facciate.parti.length, anno_clima: stato.facciate.clima.sintetico ? null : String(stato.facciate.clima.anno),
        orizzonte_lontano: stato.facciate.lontano } : null,
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
    stato.originali = corpi.map((c) => ({ ...c, ring: c.ring.map((q) => [...q]) }));
    stato.aree = []; stato.firma = null; stato.fv = null; stato.sintetico = false;
    stato.q0 = Math.min(...corpi.map((c) => c.quota || 0)); stato.lontano = null; stato.facciate = null; stato.pvgis = null;
    stato.fvOrizzonti = {}; mostraFacciate();
    stato.comune = await comuneDi(lon, lat);
    $("avviso-sintetico").hidden = true;
    ["passo-corpi", "passo-superfici", "passo-geometria", "passo-obblighi", "passo-ombre", "passo-facciate", "passo-fv", "passo-pvgis",
      "passo-consumi", "passo-report"].forEach((id) => { $(id).hidden = false; });
    $("aggiungi-priorita").disabled = false; $("calcola-pvgis").disabled = true;
    messaggio("messaggio", `Modello «${stato.modello}»: ${corpi.length} ${corpi.length === 1 ? "corpo" : "corpi"} (letto solo in questo browser), `
      + `${stato.vicini.length} corpi vicini dall'archivio.` + (stato.comune ? ` Comune: ${stato.comune.nome}.` : ""));
    aggiorna();
    if (stato.mappa) stato.mappa.easeTo({ center: [lon, lat], zoom: 17.6, duration: 600 });
    apriVista();
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
    try {
      const { base, indice } = await trovaBase();
      stato.base = base; stato.indice = indice;
      stato.lidar = await json(`${base}lidar/indice.json`).catch(() => null);
      if (stato.lidar) $("fonti-3d").append(" ", h("span", null, "Falde dei tetti: " + Object.values(stato.lidar.attribuzioni || {})
        .map((a) => `${a.attribuzione || a.descrizione} (${a.licenza})`).join("; ") + "."));
      if (indice.sintetico) $("avviso-sintetico").hidden = false;
      if (indice.attribuzione) $("fonti-3d").append(" ", h("span", null, `Questo archivio: ${indice.attribuzione}.`));
      stato.mappa = await creaMappa();
      caricaOrtofoto();
      messaggio("messaggio", indice.sintetico ? "Isolato sintetico di prova: fai clic su un edificio (quello arancione più alto è l'esempio a tre corpi)." : "Fai clic su un edificio.");
      const q = new URLSearchParams(location.search);
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
      const scelto = q.get("edificio") || (indice.sintetico ? "E-DEMO" : null);
      if (scelto && (q.get("edificio") || VISTA !== "modelli")) {
        const fs = await contesto(...indice.centro);
        const f = fs.find((x) => String(x.properties.edificio) === scelto);
        if (f) { const c = f.geometry.coordinates[0][0]; await scegli(scelto, c[0], c[1]); }
      }
    } catch (e) {
      console.warn(e);
      messaggio("messaggio", `La mappa 3D non si è aperta: ${e.message || e}. Serve un browser con WebGL.`, true);
    }
  })();
  window.EUGENIO_EDIFICIO3D = { stato, corpoReport, scegli, apriModello };
})();
