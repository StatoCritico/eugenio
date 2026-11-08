"use strict";
// Confini amministrativi per le mappe MapLibre (Ortofoto, Modelli 3D; 05/11/2026). Stessi file delle altre mappe del
// sito (dati/mappa/italia.json e dati/mappa/RR.json: ISTAT, Confini delle unità amministrative a fini statistici,
// generalizzati, CC BY 4.0, via Gramscii): nessun dato nuovo da scaricare. I percorsi SVG (solo M, L, Z) sono in UTM 32N
// con la scala dei file di mappa (fase 3, meteo_storico/comuni.py: svg = S·E + AX, −S·N + AY) e qui tornano in WGS84 con
// la trasformazione inversa di Gauss–Krüger. Precisione: confini generalizzati con una cifra decimale (≈ 100 m), utili
// come orientamento a ogni zoom, non per misurare.
//
//  const C = EUGENIO_CONFINI
//  await C.aggiungi(mappa, { prima, suComune, suRegione })   regioni sempre; province da zoom 7; comuni da zoom 9 (della
//                                                            regione al centro, caricati quando servono); clic: sotto lo
//                                                            zoom 9 sulla regione, dal 9 al 15 sul comune (secondo clic
//                                                            sullo stesso comune = lo toglie)
//  C.alza(mappa)                    i confini tornano sopra a tutto (dopo aver aggiunto un'ortofoto o gli edifici)
//  await C.riquadroRegione("08")    [ovest, sud, est, nord] in gradi
//  await C.regioneNelPunto(lon, lat) "08" o null
//  C.ITALIA                         riquadro dell'Italia
//  C.ATTRIBUZIONE                   testo per la mappa e per le immagini scaricate
(function () {
  const S = 0.0010012596459353985, AX = -313.67365575107954, AY = 5226.851664605516;
  const A = 6378137, F = 1 / 298.257223563, E2 = F * (2 - F), EP2 = E2 / (1 - E2), K0 = 0.9996, L0 = 9 * Math.PI / 180;
  const ITALIA = [6.6, 35.4, 18.6, 47.1];
  const ATTRIBUZIONE = "Confini: ISTAT, unità amministrative a fini statistici 2026 (generalizzati), CC BY 4.0";
  const V = (document.currentScript && /[?&]v=([\w-]+)/.exec(document.currentScript.src) || [])[1] || "";
  const conV = (u) => (V ? `${u}?v=${V}` : u);

  // UTM 32N (WGS84) → lon, lat (inversa di Gauss–Krüger, serie di Snyder; errore sotto il millimetro in Italia)
  function utmLonlat(E, N) {
    const x = E - 500000, M = N / K0, mu = M / (A * (1 - E2 / 4 - 3 * E2 ** 2 / 64 - 5 * E2 ** 3 / 256));
    const e1 = (1 - Math.sqrt(1 - E2)) / (1 + Math.sqrt(1 - E2));
    const f1 = mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * Math.sin(2 * mu) + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * Math.sin(4 * mu)
      + (151 * e1 ** 3 / 96) * Math.sin(6 * mu) + (1097 * e1 ** 4 / 512) * Math.sin(8 * mu);
    const s = Math.sin(f1), c = Math.cos(f1), t = Math.tan(f1);
    const C1 = EP2 * c * c, T1 = t * t, N1 = A / Math.sqrt(1 - E2 * s * s), R1 = A * (1 - E2) / (1 - E2 * s * s) ** 1.5, D = x / (N1 * K0);
    const lat = f1 - (N1 * t / R1) * (D * D / 2 - (5 + 3 * T1 + 10 * C1 - 4 * C1 * C1 - 9 * EP2) * D ** 4 / 24
      + (61 + 90 * T1 + 298 * C1 + 45 * T1 * T1 - 252 * EP2 - 3 * C1 * C1) * D ** 6 / 720);
    const lon = L0 + (D - (1 + 2 * T1 + C1) * D ** 3 / 6 + (5 - 2 * C1 + 28 * T1 - 3 * C1 * C1 + 8 * EP2 + 24 * T1 * T1) * D ** 5 / 120) / c;
    return [lon * 180 / Math.PI, lat * 180 / Math.PI];
  }
  const svgLonlat = (x, y) => utmLonlat((x - AX) / S, (AY - y) / S);
  const r6 = (v) => Math.round(v * 1e6) / 1e6;

  // "M…L…Z M…" → anelli [[lon, lat], …] chiusi
  function anelli(d) {
    const out = [];
    for (const parte of String(d || "").split("M")) {
      const p = parte.replace(/Z/g, "").trim();
      if (!p) continue;
      const r = p.split("L").map((q) => { const [x, y] = q.split(",").map(Number); const [lo, la] = svgLonlat(x, y); return [r6(lo), r6(la)]; })
        .filter((q) => Number.isFinite(q[0]) && Number.isFinite(q[1]));
      if (r.length < 3) continue;
      if (r[0][0] !== r[r.length - 1][0] || r[0][1] !== r[r.length - 1][1]) r.push(r[0]);
      out.push(r);
    }
    return out;
  }
  // i percorsi non distinguono i buchi: ogni anello è un poligono a sé (per le linee e per il clic basta)
  const multi = (d) => ({ type: "MultiPolygon", coordinates: anelli(d).map((r) => [r]) });
  function riquadro(geom) {
    let w = 180, s = 90, e = -180, n = -90;
    for (const p of geom.coordinates) for (const [x, y] of p[0]) { if (x < w) w = x; if (x > e) e = x; if (y < s) s = y; if (y > n) n = y; }
    return [w, s, e, n];
  }

  let italia = null;
  const regioni = new Map();       // "08" → promessa di { comuni, province }
  async function json(u) { const r = await fetch(conV(u)); if (!r.ok) throw new Error(`${u}: ${r.status}`); return r.json(); }
  function datiItalia() {
    if (!italia) {
      italia = json("dati/mappa/italia.json").then((m) => {
        const feats = m.regioni.filter((r) => /^(0[1-9]|1\d|20)$/.test(r.cod)).map((r) => {
          const g = multi(r.d);
          return { type: "Feature", properties: { cod: r.cod, nome: r.nome }, geometry: g, bbox: riquadro(g) };
        });
        return { type: "FeatureCollection", features: feats };
      });
      italia.catch(() => { italia = null; });
    }
    return italia;
  }
  function datiRegione(cod) {
    if (!regioni.has(cod)) {
      const p = json(`dati/mappa/${cod}.json`).then((m) => ({
        comuni: { type: "FeatureCollection", features: (m.comuni || []).map((c) => ({ type: "Feature",
          properties: { istat: c.istat, nome: c.nome, prov: c.prov || "", regione: cod }, geometry: multi(c.d) })) },
        province: { type: "FeatureCollection", features: (m.province || []).map((p) => ({ type: "Feature",
          properties: { cod: p.cod, sigla: p.sigla || "", nome: p.nome }, geometry: multi(p.d) })) },
      }));
      p.catch(() => regioni.delete(cod));
      regioni.set(cod, p);
    }
    return regioni.get(cod);
  }
  function dentro([x, y], anello) {
    let d = false;
    for (let i = 0, j = anello.length - 1; i < anello.length; j = i++) {
      const [xi, yi] = anello[i], [xj, yj] = anello[j];
      if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) d = !d;
    }
    return d;
  }
  const contiene = (f, p) => f.geometry.coordinates.some((pol) => dentro(p, pol[0]));
  async function regioneNelPunto(lon, lat) {
    try {
      const it = await datiItalia();
      const f = it.features.find((x) => lon >= x.bbox[0] && lon <= x.bbox[2] && lat >= x.bbox[1] && lat <= x.bbox[3] && contiene(x, [lon, lat]));
      return f ? f.properties.cod : null;
    } catch { return null; }
  }
  async function comuneNelPunto(lon, lat) {
    const cod = await regioneNelPunto(lon, lat);
    if (!cod) return null;
    try {
      const r = await datiRegione(cod);
      const f = r.comuni.features.find((x) => contiene(x, [lon, lat]));
      return f ? { ...f.properties } : null;
    } catch { return null; }
  }
  async function riquadroRegione(cod) {
    try {
      const it = await datiItalia();
      const f = it.features.find((x) => x.properties.cod === cod);
      return f ? f.bbox : null;
    } catch { return null; }
  }
  async function riquadroComune(istat) {
    const cod = await regioneDelComune(istat);
    if (!cod) return null;
    const r = await datiRegione(cod);
    const f = r.comuni.features.find((x) => x.properties.istat === istat);
    return f ? riquadro(f.geometry) : null;
  }
  // confine del comune (MultiPolygon in lon/lat), per le zone coperte dal DBTR in Modelli 3D (07/11/2026); lon e lat
  // (un punto vicino al comune) servono a trovare la regione se non è ancora caricata
  async function geometriaComune(istat, lon, lat) {
    let cod = await regioneDelComune(istat);
    if (!cod && Number.isFinite(lon) && Number.isFinite(lat)) cod = await regioneNelPunto(lon, lat);
    if (!cod) return null;
    try {
      const r = await datiRegione(cod);
      const f = r.comuni.features.find((x) => x.properties.istat === istat);
      return f ? f.geometry : null;
    } catch { return null; }
  }
  // il codice ISTAT del comune comincia con quello della provincia, non della regione: si cerca nelle regioni già caricate
  async function regioneDelComune(istat) {
    for (const [cod, p] of regioni) { try { if ((await p).comuni.features.some((x) => x.properties.istat === istat)) return cod; } catch { /* prossima */ } }
    return null;
  }

  const css = (n, d) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || d;
  const STRATI = ["confini-comuni", "confini-comune-scelto", "confini-province", "confini-regioni-alone", "confini-regioni", "confini-regione-scelta"];
  function colori(m) {
    const ink = css("--inchiostro", "#222"), carta = css("--carta", "#fff"), acc = css("--primario", "#e4572e");
    const imp = [["confini-regioni", "line-color", ink], ["confini-regioni-alone", "line-color", carta], ["confini-province", "line-color", ink],
      ["confini-comuni", "line-color", ink], ["confini-comune-scelto", "line-color", acc], ["confini-regione-scelta", "line-color", acc]];
    for (const [id, k, v] of imp) if (m.getLayer(id)) m.setPaintProperty(id, k, v);
  }
  function alza(m) { for (const id of STRATI) if (m.getLayer(id)) m.moveLayer(id); }

  async function aggiungi(m, opz = {}) {
    const vuota = { type: "FeatureCollection", features: [] };
    const it = await datiItalia();
    m.addSource("confini-regioni", { type: "geojson", data: it, attribution: ATTRIBUZIONE });
    m.addSource("confini-province", { type: "geojson", data: vuota });
    m.addSource("confini-comuni", { type: "geojson", data: vuota });
    const prima = opz.prima && m.getLayer(opz.prima) ? opz.prima : undefined;
    // riempimento trasparente: serve solo al clic e al passaggio del mouse
    m.addLayer({ id: "confini-regioni-clic", type: "fill", source: "confini-regioni", maxzoom: 9, paint: { "fill-color": "#000", "fill-opacity": 0 } }, prima);
    m.addLayer({ id: "confini-comuni-clic", type: "fill", source: "confini-comuni", minzoom: 9, maxzoom: 15.5, paint: { "fill-color": "#000", "fill-opacity": 0 } }, prima);
    m.addLayer({ id: "confini-comuni", type: "line", source: "confini-comuni", minzoom: 9,
      paint: { "line-width": ["interpolate", ["linear"], ["zoom"], 9, 0.5, 14, 1.2], "line-opacity": 0.55, "line-dasharray": [3, 2] } }, prima);
    m.addLayer({ id: "confini-comune-scelto", type: "line", source: "confini-comuni", filter: ["==", ["get", "istat"], ""],
      paint: { "line-width": 3 } }, prima);
    m.addLayer({ id: "confini-province", type: "line", source: "confini-province", minzoom: 7,
      paint: { "line-width": ["interpolate", ["linear"], ["zoom"], 7, 0.8, 14, 1.8], "line-opacity": 0.7 } }, prima);
    // regioni: un alone del colore della carta sotto la linea, così il confine si legge anche sulle foto
    m.addLayer({ id: "confini-regioni-alone", type: "line", source: "confini-regioni",
      paint: { "line-width": ["interpolate", ["linear"], ["zoom"], 5, 3, 14, 6], "line-opacity": 0.6 } }, prima);
    m.addLayer({ id: "confini-regioni", type: "line", source: "confini-regioni",
      paint: { "line-width": ["interpolate", ["linear"], ["zoom"], 5, 1.2, 14, 2.6] } }, prima);
    m.addLayer({ id: "confini-regione-scelta", type: "line", source: "confini-regioni", filter: ["==", ["get", "cod"], ""],
      paint: { "line-width": ["interpolate", ["linear"], ["zoom"], 5, 2.5, 14, 4] } }, prima);
    colori(m);
    document.addEventListener("eugenio:aspetto", () => colori(m));

    // comuni e province della regione (o delle regioni) che si vedono: caricati una volta, quando si arriva allo zoom 7
    const caricate = new Set();
    async function aggiornaRegioni() {
      if (m.getZoom() < 7) return;
      const b = m.getBounds(), w = b.getWest(), s = b.getSouth(), e = b.getEast(), n = b.getNorth();
      const viste = it.features.filter((f) => f.bbox[0] < e && f.bbox[2] > w && f.bbox[1] < n && f.bbox[3] > s).map((f) => f.properties.cod);
      const nuove = viste.filter((c) => !caricate.has(c)).slice(0, 4);
      if (!nuove.length) return;
      nuove.forEach((c) => caricate.add(c));
      await Promise.all(nuove.map((c) => datiRegione(c).catch(() => null)));
      const tutte = await Promise.all([...caricate].map((c) => datiRegione(c).catch(() => null)));
      const ok = tutte.filter(Boolean);
      m.getSource("confini-comuni").setData({ type: "FeatureCollection", features: ok.flatMap((r) => r.comuni.features) });
      m.getSource("confini-province").setData({ type: "FeatureCollection", features: ok.flatMap((r) => r.province.features) });
    }
    m.on("moveend", () => { aggiornaRegioni().catch(() => {}); });
    aggiornaRegioni().catch(() => {});

    // clic: regione (zoom basso) o comune (zoom medio); il secondo clic sullo stesso comune lo toglie
    let comuneScelto = "";
    const stato = {
      comune: () => comuneScelto,
      scegliComune(istat) {
        comuneScelto = istat || "";
        m.setFilter("confini-comune-scelto", ["==", ["get", "istat"], comuneScelto]);
      },
      scegliRegione(cod) { m.setFilter("confini-regione-scelta", ["==", ["get", "cod"], cod || ""]); },
    };
    if (opz.clic !== false) {
      m.on("click", (ev) => {
        if (opz.attivo && !opz.attivo(ev)) return;
        const z = m.getZoom();
        if (z < 9) {
          const f = m.queryRenderedFeatures(ev.point, { layers: ["confini-regioni-clic"] })[0];
          if (f && opz.suRegione) opz.suRegione(f.properties.cod, f.properties.nome);
          return;
        }
        if (z > 15.5) return;
        const f = m.queryRenderedFeatures(ev.point, { layers: ["confini-comuni-clic"] })[0];
        if (!f) return;
        const istat = f.properties.istat;
        if (istat === comuneScelto) { stato.scegliComune(""); if (opz.suComune) opz.suComune(null); return; }
        stato.scegliComune(istat);
        if (opz.suComune) opz.suComune({ istat, nome: f.properties.nome, prov: f.properties.prov });
      });
      m.on("mousemove", (ev) => {
        if (opz.attivo && !opz.attivo(ev)) return;
        const z = m.getZoom(), strato = z < 9 ? "confini-regioni-clic" : z <= 15.5 ? "confini-comuni-clic" : null;
        if (!strato || !opz.suggerimento) return;
        const f = m.queryRenderedFeatures(ev.point, { layers: [strato] })[0];
        opz.suggerimento(f ? (f.properties.prov ? `${f.properties.nome} (${f.properties.prov})` : f.properties.nome) : "", ev);
      });
    }
    alza(m);
    return stato;
  }

  window.EUGENIO_CONFINI = { aggiungi, alza, riquadroRegione, riquadroComune, geometriaComune, regioneNelPunto, comuneNelPunto, utmLonlat, svgLonlat,
    ITALIA, ATTRIBUZIONE };
})();
