"use strict";
// Strati attivabili sopra le ortofoto in una mappa MapLibre (05/11/2026, seconda pubblicazione; Modelli 3D e Ortofoto):
//  - confini delle particelle catastali (Agenzia delle Entrate, WMS INSPIRE, CC BY 4.0) dal proxy del server, che
//    riproietta in web mercator e lascia solo linee e numeri (servizio/strati.py);
//  - contorni degli edifici: lo strato della regione al centro della mappa se c'è (DBTR dell'Emilia-Romagna, CC BY 4.0),
//    altrove le sagome di OpenStreetMap (ODbL 1.0) a tessere dello zoom 16.
// Elenco e licenze da GET /api/ortofoto/strati. Con un livello acceso la legenda e l'attribuzione sono sempre visibili
// sotto la mappa, e righe() le restituisce per la fascia dell'immagine scaricata (esporta_mappa.js).
//
//  const s = await EUGENIO_STRATI.aggiungi(mappa, { caselle, legenda, sotto: () => idStrato|undefined })
//  s.righe()  → testi di legenda e attribuzione dei livelli visibili;  s.stato  → { particelle, edifici, … }
(function () {
  const C = () => window.EUGENIO_CONFINI;
  function h(tag, cls, t) { const e = document.createElement(tag); if (cls) e.className = cls; if (t !== undefined) e.textContent = t; return e; }
  const vuota = () => ({ type: "FeatureCollection", features: [] });
  const tessera = (lon, lat, z) => {
    const n = 2 ** z, x = Math.floor((lon + 180) / 360 * n);
    const y = Math.floor((1 - Math.asinh(Math.tan(lat * Math.PI / 180)) / Math.PI) / 2 * n);
    return [Math.max(0, Math.min(n - 1, x)), Math.max(0, Math.min(n - 1, y))];
  };

  async function aggiungi(m, opz = {}) {
    let elenco = [];
    try {
      const r = await fetch("/api/ortofoto/strati");
      if (r.ok && /json/.test(r.headers.get("Content-Type") || "")) elenco = (await r.json()).strati || [];
    } catch { /* server senza strati: le caselle restano spente */ }
    const st = { particelle: false, edifici: false, regione: null, edificiStrato: null, osm: new Map(), errori: 0, elenco };
    const particelle = elenco.find((s) => s.tema === "particelle");
    const edificiRegionali = elenco.filter((s) => s.tema === "edifici" && s.regioni.length);
    const osm = elenco.find((s) => s.tema === "edifici" && !s.regioni.length);
    const sotto = () => (opz.sotto ? opz.sotto() : undefined);

    // ---------------------------------------------------------------- caselle
    const box = opz.caselle;
    const casella = (id, testo, attiva) => {
      const l = h("label", "casella-strato"), i = h("input");
      i.type = "checkbox"; i.id = id; i.disabled = !attiva;
      l.append(i, ` ${testo}`);
      if (!attiva) l.append(h("span", "aiuto-breve", " (non disponibile su questo server)"));
      if (box) box.appendChild(l);
      return i;
    };
    const cP = casella("strato-particelle", "Confini delle particelle catastali", !!particelle);
    const cE = casella("strato-edifici", "Contorni degli edifici", !!(edificiRegionali.length || osm));

    // ---------------------------------------------------------------- particelle (immagini trasparenti)
    if (particelle) {
      m.addSource("strato-particelle", { type: "raster", tiles: [location.origin + particelle.tessere], tileSize: 256,
        minzoom: particelle.zoom[0], maxzoom: particelle.zoom[1], bounds: particelle.riquadro, attribution: particelle.citazione });
      m.addLayer({ id: "strato-particelle", type: "raster", source: "strato-particelle", minzoom: particelle.zoom[0] - 0.5,
        layout: { visibility: "none" } }, sotto());
    }
    // ---------------------------------------------------------------- edifici: regionale (immagini) o OSM (vettori)
    edificiRegionali.forEach((s) => {
      m.addSource(`strato-${s.id}`, { type: "raster", tiles: [location.origin + s.tessere], tileSize: 256, minzoom: s.zoom[0],
        maxzoom: s.zoom[1], bounds: s.riquadro, attribution: s.citazione });
      m.addLayer({ id: `strato-${s.id}`, type: "raster", source: `strato-${s.id}`, minzoom: s.zoom[0] - 0.5, layout: { visibility: "none" } }, sotto());
    });
    if (osm) {
      m.addSource("strato-osm", { type: "geojson", data: vuota(), attribution: osm.citazione });
      m.addLayer({ id: "strato-osm", type: "line", source: "strato-osm", minzoom: 15.5, layout: { visibility: "none" },
        paint: { "line-color": osm.colore, "line-width": ["interpolate", ["linear"], ["zoom"], 16, 1, 20, 2.2] } }, sotto());
    }

    function vedi(id, si) { if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", si ? "visible" : "none"); }
    async function scegliEdifici() {
      const c = m.getCenter();
      const cod = C() ? await C().regioneNelPunto(c.lng, c.lat) : null;
      st.regione = cod;
      const reg = edificiRegionali.find((s) => cod && s.regioni.includes(cod)) || null;
      st.edificiStrato = reg || osm || null;
      edificiRegionali.forEach((s) => vedi(`strato-${s.id}`, st.edifici && reg === s));
      vedi("strato-osm", st.edifici && !reg && !!osm);
      if (st.edifici && !reg && osm) await caricaOsm();
      legenda();
    }
    async function caricaOsm() {
      if (m.getZoom() < 15.5) return;
      const b = m.getBounds(), [x0, y0] = tessera(b.getWest(), b.getNorth(), 16), [x1, y1] = tessera(b.getEast(), b.getSouth(), 16);
      const chiavi = [];
      for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) chiavi.push(`${x}/${y}`);
      if (chiavi.length > 16) return;                       // vista troppo larga: si aspetta di avvicinarsi
      const nuove = chiavi.filter((k) => !st.osm.has(k));
      await Promise.all(nuove.map(async (k) => {
        try {
          const r = await fetch(location.origin + osm.tessere.replace("{z}/{x}/{y}", `16/${k}`));
          st.osm.set(k, r.ok ? ((await r.json()).features || []) : []);
          if (!r.ok) st.errori++;
        } catch { st.osm.set(k, []); st.errori++; }
      }));
      if (st.osm.size > 200) [...st.osm.keys()].slice(0, st.osm.size - 200).forEach((k) => st.osm.delete(k));
      const src = m.getSource("strato-osm");
      if (src) src.setData({ type: "FeatureCollection", features: [...st.osm.values()].flat() });
    }

    // ---------------------------------------------------------------- legenda e attribuzioni (sempre visibili se acceso)
    const leg = opz.legenda;
    function voce(s, nome) {
      const p = h("p", "voce-strato");
      const seg = h("i", "segno-strato"); seg.style.borderColor = s.colore; seg.setAttribute("aria-hidden", "true");
      p.append(seg, `${nome}: ${s.legenda || s.nome}. Fonte: ${s.citazione} – licenza `);
      const a = h("a", null, s.licenza); a.href = s.scheda; p.append(a, ".");
      if (m.getZoom() < s.zoom[0] - 0.5) p.append(` Si vede dallo zoom ${s.zoom[0]}: avvicinati.`);
      if (s.nota) p.append(` ${s.nota}`);
      return p;
    }
    function legenda() {
      if (!leg) return;
      leg.innerHTML = "";
      if (st.particelle && particelle) leg.appendChild(voce(particelle, "Particelle catastali"));
      if (st.edifici && st.edificiStrato) {
        const p = voce(st.edificiStrato, "Contorni degli edifici");
        if (st.edificiStrato === osm && st.errori && !st.osm.size) p.append(" Le sagome di OpenStreetMap non sono arrivate: riprova più tardi.");
        leg.appendChild(p);
      }
      leg.hidden = !leg.childNodes.length;
    }

    cP.addEventListener("change", () => { st.particelle = cP.checked; vedi("strato-particelle", cP.checked); legenda(); });
    cE.addEventListener("change", () => { st.edifici = cE.checked; scegliEdifici(); });
    m.on("moveend", () => { if (st.edifici) scegliEdifici(); else legenda(); });

    function righe() {
      const out = [], z = m.getZoom();
      if (st.particelle && particelle && z >= particelle.zoom[0] - 0.5)
        out.push(`Particelle catastali (${particelle.legenda || "linee"}): ${particelle.citazione} (${particelle.scheda}).`);
      const s = st.edificiStrato;
      if (st.edifici && s && z >= s.zoom[0] - 0.5) out.push(`Contorni degli edifici (${s.legenda || "linee"}): ${s.citazione} (${s.scheda}).`);
      return out;
    }
    function alza() {   // dopo l'aggiunta di un'ortofoto: gli strati restano sopra la foto
      ["strato-particelle", ...edificiRegionali.map((s) => `strato-${s.id}`), "strato-osm"].forEach((id) => {
        if (m.getLayer(id)) m.moveLayer(id, sotto());
      });
    }
    function accendi(tema, si) {   // per le prove e per gli altri script
      const c = tema === "particelle" ? cP : cE;
      if (c.disabled) return false;
      c.checked = si; c.dispatchEvent(new Event("change"));
      return true;
    }
    legenda();
    return { stato: st, righe, alza, accendi, legenda };
  }

  window.EUGENIO_STRATI = { aggiungi };
})();
