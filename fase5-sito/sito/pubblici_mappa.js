"use strict";
// Edifici pubblici retinati in Modelli 3D (17/11/2026, richiesta di Paolo: «gli edifici pubblici devono apparire retinati
// rispetto agli altri, sia in mappa che in vista 3D»).
//
// Un edificio è «pubblico» se il punto interno di uno dei suoi corpi cade in una particella con edifici del censimento MEF
// (tessere /edifici3d/immobili_pa/…pmtiles, strato «particelle», t = E o M; Territorio › Edifici pubblici). Gli edifici
// pubblici si copiano in una sorgente GeoJSON propria e si disegnano con il retino a righe oblique (retino.js):
//  - mappa 2D: «pubblici-2d» (fill-pattern di sole righe, fondo trasparente: i pezzi di tessera che si sovrappongono ai
//    bordi non lasciano bande più chiare) sopra le sagome (niente contorno: i pezzi di tessera ne avrebbero uno anche lungo i tagli);
//  - vista 3D: «pubblici-3d» (fill-extrusion-pattern con fondo pieno) con le sagome **intere** degli edifici vicini
//    (opz.interi: quelli che la pagina carica per il 3D, entro ~300 m), tolti con un filtro dalle estrusioni normali; mai
//    l'edificio scelto (lo disegna «scelto»): niente due solidi sovrapposti.
// Il calcolo usa le tessere già caricate (querySourceFeatures) e si rifà quando la mappa si ferma: niente richieste in più.
//
//  const p = await EUGENIO_PUBBLICI_MAPPA.collega(mappa, { sorgenti: () => [{ id, strato }], prima: "scelto",
//            in3d: () => bool, interi: () => [{ edificio, id, geometry, altezza }], casella: <div>, legenda: <div> })
//  p.edificioPubblico(lon, lat) → { ref, ente, tipologie, n } della particella nel punto (o null)
//  p.strati2d, p.strati3d        id dei livelli, per le liste di visibilità della pagina
(function () {
  const R = () => window.EUGENIO_RETINO;
  const vuota = () => ({ type: "FeatureCollection", features: [] });
  const Z_MIN = 13;              // come le sagome della mappa 2D

  // punto dentro un anello (lon/lat, pari-dispari)
  function dentroAnello(x, y, a) {
    let d = false;
    for (let i = 0, j = a.length - 1; i < a.length; j = i++) {
      const [xi, yi] = a[i], [xj, yj] = a[j];
      if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) d = !d;
    }
    return d;
  }
  function dentro(x, y, g) {
    const poli = g.type === "Polygon" ? [g.coordinates] : g.type === "MultiPolygon" ? g.coordinates : [];
    return poli.some((p) => p.length && dentroAnello(x, y, p[0]) && !p.slice(1).some((b) => dentroAnello(x, y, b)));
  }
  function riquadro(g) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    const poli = g.type === "Polygon" ? [g.coordinates] : g.type === "MultiPolygon" ? g.coordinates : [];
    poli.forEach((p) => (p[0] || []).forEach(([x, y]) => { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }));
    return [x0, y0, x1, y1];
  }
  // punto rappresentativo di un corpo: media dei vertici dell'anello esterno, o un vertice spostato verso il centro se la
  // media cade fuori (corpi a L o a C)
  function puntoInterno(g) {
    const p = g.type === "Polygon" ? g.coordinates : g.type === "MultiPolygon" ? g.coordinates[0] : null;
    if (!p || !p[0] || p[0].length < 3) return null;
    const a = p[0], n = a.length - 1;
    let x = 0, y = 0;
    for (let i = 0; i < n; i++) { x += a[i][0]; y += a[i][1]; }
    x /= n; y /= n;
    if (dentroAnello(x, y, a)) return [x, y];
    for (let i = 0; i < n; i++) {
      const c = [a[i][0] * 0.9 + x * 0.1, a[i][1] * 0.9 + y * 0.1];
      if (dentroAnello(c[0], c[1], a)) return c;
    }
    return [x, y];
  }

  async function collega(m, opz = {}) {
    let info = null;
    try {
      const r = await fetch("/edifici3d/immobili_pa/indice.json", { cache: "no-cache" });
      if (r.ok && /json/.test(r.headers.get("Content-Type") || "")) info = await r.json();
    } catch { /* dati non sul server */ }
    const st = { attivo: !!info, pubblici: new Set(), pubblici3d: new Set(), particelle: [] };
    const out = { stato: st, info, strati2d: ["pubblici-2d"], strati3d: ["pubblici-3d"], edificioPubblico: () => null, aggiorna: () => {} };
    if (!info || !info.pmtiles || !m) {
      if (opz.casella) opz.casella.append(Object.assign(document.createElement("p"), { className: "aiuto-breve", textContent: "Edifici pubblici: dati non ancora sul server." }));
      return out;
    }
    const retino = R() ? R().aggiungi(m, { nome: "retino-pubblico", fondo: "rgb(214,210,218)" }) : null;
    const righe = R() ? R().aggiungi(m, { nome: "retino-pubblico-righe", fondo: null }) : null;
    const COL = R() ? R().COLORE : "#c2185b";
    m.addSource("pa", { type: "vector", url: `pmtiles://${location.origin}${info.pmtiles}`, attribution: "Immobili pubblici: MEF – Patrimonio della PA; Agenzia delle Entrate (CC BY 4.0)" });
    // livello invisibile: serve solo a far caricare le tessere delle particelle (querySourceFeatures)
    m.addLayer({ id: "pa-carica", type: "fill", source: "pa", "source-layer": "particelle", minzoom: 13,
      filter: ["in", ["get", "t"], ["literal", ["E", "M"]]], paint: { "fill-opacity": 0 } }, opz.prima && m.getLayer(opz.prima) ? opz.prima : undefined);
    m.addSource("corpi-pubblici", { type: "geojson", data: vuota() });
    m.addSource("corpi-pubblici-3d", { type: "geojson", data: vuota() });
    const prima = opz.prima && m.getLayer(opz.prima) ? opz.prima : undefined;
    m.addLayer({ id: "pubblici-3d", type: "fill-extrusion", source: "corpi-pubblici-3d", layout: { visibility: opz.in3d && opz.in3d() ? "visible" : "none" },
      paint: { ...(retino ? { "fill-extrusion-pattern": retino } : { "fill-extrusion-color": COL }),
        "fill-extrusion-height": ["get", "altezza"], "fill-extrusion-base": 0, "fill-extrusion-opacity": 0.95 } }, prima);
    m.addLayer({ id: "pubblici-2d", type: "fill", source: "corpi-pubblici", minzoom: Z_MIN,
      paint: righe ? { "fill-pattern": righe } : { "fill-color": COL, "fill-opacity": 0.5 } }, prima);

    // casella «Edifici pubblici (retinati)» nei livelli della mappa e voce di legenda
    let cas = null;
    if (opz.casella) {
      const l = document.createElement("label"); l.className = "casella-strato";
      cas = document.createElement("input"); cas.type = "checkbox"; cas.id = "strato-pubblici"; cas.checked = true;
      l.append(cas, " Edifici pubblici (retinati; censimento MEF 2023)");
      opz.casella.appendChild(l);
    }
    if (opz.legenda && R()) {
      const s = document.createElement("span"); s.id = "legenda-pubblici";
      s.append(R().campione(), "edifici pubblici (censimento MEF «Patrimonio della PA» e particelle dell'Agenzia delle Entrate, CC BY 4.0)");
      opz.legenda.appendChild(s);
    }

    function particelle() {
      const fs = m.querySourceFeatures("pa", { sourceLayer: "particelle", filter: ["in", ["get", "t"], ["literal", ["E", "M"]]] });
      const viste = new Map();
      fs.forEach((f) => {
        const r = f.properties.r, g = f.geometry;
        if (!g) return;
        const l = viste.get(r) || []; l.push({ g, b: riquadro(g), p: f.properties }); viste.set(r, l);
      });
      return [...viste.values()].flat();
    }
    function nelPunto(x, y, ps) {
      return ps.find((q) => x >= q.b[0] && x <= q.b[2] && y >= q.b[1] && y <= q.b[3] && dentro(x, y, q.g)) || null;
    }
    function aggiorna() {
      const acceso = !cas || cas.checked;
      if (!acceso) {
        st.pubblici = new Set(); st.pubblici3d = new Set();
        m.getSource("corpi-pubblici").setData(vuota()); m.getSource("corpi-pubblici-3d").setData(vuota()); filtraCorpi();
        return;
      }
      if (m.getZoom() < Z_MIN) return;
      const ps = particelle();
      st.particelle = ps;
      // 2D: pezzi delle tessere dei corpi visibili
      const sorgenti = (opz.sorgenti ? opz.sorgenti() : []).filter((s) => m.getSource(s.id));
      const pezzi = [];
      sorgenti.forEach((s) => {
        try { m.querySourceFeatures(s.id, s.strato ? { sourceLayer: s.strato } : {}).forEach((f) => pezzi.push(f)); } catch { /* sorgente non pronta */ }
      });
      const pubblici = new Set();
      pezzi.forEach((f) => {
        const k = String(f.properties.edificio || f.properties.id || "");
        if (!k || pubblici.has(k)) return;
        const c = puntoInterno(f.geometry);
        if (c && nelPunto(c[0], c[1], ps)) pubblici.add(k);
      });
      st.pubblici = pubblici;
      const feats = pezzi.filter((f) => pubblici.has(String(f.properties.edificio || f.properties.id || "")))
        .map((f) => ({ type: "Feature", properties: { id: f.properties.id, edificio: String(f.properties.edificio || f.properties.id) }, geometry: f.geometry }));
      m.getSource("corpi-pubblici").setData({ type: "FeatureCollection", features: feats });
      // 3D: sagome intere dei vicini, senza l'edificio scelto
      const in3d = opz.in3d && opz.in3d(), scelto = opz.scelto ? String(opz.scelto() || "") : "";
      const tutti = in3d && opz.interi ? opz.interi() : [];
      const casi = new Map();
      tutti.forEach((c) => {
        const k = String(c.edificio || c.id || "");
        if (!k || k === scelto) return;
        if (!casi.has(k)) { const p = puntoInterno(c.geometry); casi.set(k, !!(p && nelPunto(p[0], p[1], ps))); }
      });
      const f3 = tutti.filter((c) => casi.get(String(c.edificio || c.id || "")))
        .map((c) => ({ type: "Feature", properties: { id: c.id, edificio: String(c.edificio || c.id), altezza: +c.altezza || 0 }, geometry: c.geometry }));
      st.pubblici3d = new Set(f3.map((f) => f.properties.edificio));
      m.getSource("corpi-pubblici-3d").setData({ type: "FeatureCollection", features: f3 });
      filtraCorpi();
    }
    // nelle estrusioni normali gli edifici pubblici del 3D si tolgono (li disegna «pubblici-3d»): il filtro lo compone la
    // pagina con i suoi (opz.filtra), altrimenti si mette qui
    function filtraCorpi() {
      const ids = [...(st.pubblici3d || [])];
      if (opz.filtra) { opz.filtra(ids); return; }
      (opz.sorgenti ? opz.sorgenti() : []).forEach((s) => {
        if (!m.getLayer(s.id)) return;
        m.setFilter(s.id, ids.length ? ["!", ["in", ["to-string", ["coalesce", ["get", "edificio"], ["get", "id"]]], ["literal", ids]]] : null);
      });
    }
    let attesa = null;
    const piu_tardi = () => { clearTimeout(attesa); attesa = setTimeout(aggiorna, 250); };
    m.on("moveend", piu_tardi);
    m.on("sourcedata", (e) => { if (e.isSourceLoaded && (e.sourceId === "pa" || (opz.sorgenti ? opz.sorgenti() : []).some((s) => s.id === e.sourceId))) piu_tardi(); });
    if (cas) cas.addEventListener("change", () => {
      const in3d = opz.in3d && opz.in3d();
      m.setLayoutProperty("pubblici-2d", "visibility", cas.checked && !in3d ? "visible" : "none");
      m.setLayoutProperty("pubblici-3d", "visibility", cas.checked && in3d ? "visible" : "none");
      aggiorna();
    });

    out.aggiorna = aggiorna;
    out.acceso = () => !cas || cas.checked;
    out.edificioPubblico = (lon, lat) => {
      const q = nelPunto(lon, lat, st.particelle.length ? st.particelle : particelle());
      return q ? { ref: q.p.r, ente: q.p.a, tipologie: q.p.tp, n: q.p.n } : null;
    };
    piu_tardi();
    return out;
  }

  window.EUGENIO_PUBBLICI_MAPPA = { collega, _dentro: dentro, _puntoInterno: puntoInterno };
})();
