"use strict";
// Pagina Patrimonio › Ortofoto (fase 10, Fase B, § 6 della proposta). Mappa MapLibre con le ortofoto servite dal proxy
// del server (/api/ortofoto/fonti e /api/ortofoto/<fonte>/<z>/<x>/<y>.jpg, servizio/ortofoto.py), selettore delle
// fonti che coprono la zona e attribuzione sempre visibile sotto la mappa (citazione, licenza, scheda, stato).
// Contorni degli edifici dall'archivio 3D (PMTiles dei corpi) se c'è; altrimenti niente. Ortofoto AGEA dei singoli siti
// (scaricate a mano, ridotte a 50 cm: comando `edifici3d ortofoto-sito`) da /edifici3d/cc-by/ortofoto_siti/indice.json,
// aggiunte come fonti in PMTiles.
// Indirizzo: ?lat=…&lon=…&z=… per aprire su un punto, ?fonte=<id> per scegliere la fonte.
(function () {
  const $ = (id) => document.getElementById(id);
  const box = $("mappa-ortofoto");
  if (!box || !window.maplibregl) return;
  const q = new URLSearchParams(location.search);
  const centro = [Number(q.get("lon")) || 12.5683, Number(q.get("lat")) || 44.0594];
  const stato = { fonti: [], scelta: null, mappa: null };
  const colore = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || "#888";
  function h(tag, cls, t) { const e = document.createElement(tag); if (cls) e.className = cls; if (t !== undefined) e.textContent = t; return e; }
  function messaggio(t, errore = false) { const m = $("messaggio"); m.textContent = t; m.classList.toggle("errore", errore); }
  const copre = (f, [lon, lat]) => lon >= f.riquadro[0] && lon <= f.riquadro[2] && lat >= f.riquadro[1] && lat <= f.riquadro[3];

  function attribuzione(f) {
    const a = $("attribuzione"); a.innerHTML = "";
    if (!f) { a.textContent = "Nessuna ortofoto: scegli una fonte."; return; }
    a.append("Ortofoto: ", f.citazione, " – licenza ");
    const l = h("a", null, f.licenza); l.href = f.scheda; a.appendChild(l);
    if (f.stato === "da confermare") a.append(". Uso tramite il server di EuGEnio in attesa di conferma della fonte");
    a.append(f.copia ? "." : ". Solo consultazione dal vivo: non entra nei report.");
  }
  function scegli(id) {
    const m = stato.mappa, f = stato.fonti.find((x) => x.id === id) || null;
    if (m.getLayer("ortofoto")) m.removeLayer("ortofoto");
    if (m.getSource("ortofoto")) m.removeSource("ortofoto");
    stato.scelta = f;
    if (f) {
      m.addSource("ortofoto", f.pmtiles
        ? { type: "raster", url: `pmtiles://${location.origin}${f.pmtiles}`, tileSize: 256, attribution: f.citazione }
        : { type: "raster", tiles: [location.origin + f.tessere], tileSize: 256, minzoom: f.zoom[0], maxzoom: f.zoom[1], attribution: f.citazione });
      m.addLayer({ id: "ortofoto", type: "raster", source: "ortofoto" }, m.getLayer("edifici") ? "edifici" : undefined);
      try { history.replaceState(null, "", `?fonte=${f.id}`); } catch { /* niente */ }
    }
    attribuzione(f);
    document.querySelectorAll('#fonti input[name="fonte"]').forEach((i) => { i.checked = i.value === (f ? f.id : ""); });
  }
  function elenco() {
    const fs = $("fonti");
    fs.querySelectorAll("label").forEach((x) => x.remove());
    const c = stato.mappa.getCenter(), qui = stato.fonti.filter((f) => copre(f, [c.lng, c.lat]));
    if (!qui.length) { messaggio("Nessuna fonte copre questa zona.", true); return; }
    messaggio("");
    for (const f of qui) {
      const l = h("label"), i = h("input"); i.type = "radio"; i.name = "fonte"; i.value = f.id; i.checked = stato.scelta && stato.scelta.id === f.id;
      i.addEventListener("change", () => scegli(f.id));
      const n = h("span", "nome-fonte", f.nome);
      const d = h("span", "dettagli-fonte");
      const st = !f.copia ? h("span", "stato-fonte da-confermare", "solo consultazione")
        : h("span", `stato-fonte ${f.stato === "confermata" ? "confermata" : "da-confermare"}`, f.stato === "confermata" ? "licenza verificata" : "uso da confermare");
      d.append(`${f.licenza} · zoom ${f.zoom[0]}–${f.zoom[1]} · ${f.copia ? "con copia sul server" : "solo dal vivo"} `, st);
      l.append(i, n, d); fs.appendChild(l);
    }
    const nessuna = h("label"), i0 = h("input"); i0.type = "radio"; i0.name = "fonte"; i0.value = ""; i0.checked = !stato.scelta;
    i0.addEventListener("change", () => scegli(""));
    nessuna.append(i0, h("span", "nome-fonte", "Nessuna ortofoto")); fs.appendChild(nessuna);
    if (stato.scelta && !copre(stato.scelta, [c.lng, c.lat])) scegli(qui[0].id);
  }

  async function edifici(m) {
    // contorni dei corpi dall'archivio 3D (dati veri o demo sintetica): solo per riconoscere i tetti
    for (const b of ["/edifici3d/cc-by/er/prodotti/", "dati/edifici3d/"]) {
      try {
        const r = await fetch(`${b}indice.json`);
        if (!r.ok) continue;
        const ind = await r.json();
        if (ind.sintetico) continue;         // sagome inventate su foto vere: no
        m.addSource("corpi", { type: "vector", url: `pmtiles://${new URL(b + "corpi.pmtiles", location.href).href}`, attribution: ind.attribuzione || "" });
        m.addLayer({ id: "edifici", type: "line", source: "corpi", "source-layer": "corpi", paint: { "line-color": colore("--primario"), "line-width": 1.2 } });
        return true;
      } catch { /* prossimo archivio */ }
    }
    $("edifici").disabled = true; $("edifici").parentElement.append(" – archivio degli edifici non ancora sul server");
    return false;
  }

  async function siti() {
    try {
      const r = await fetch("/edifici3d/cc-by/ortofoto_siti/indice.json");
      if (!r.ok || !/json/.test(r.headers.get("Content-Type") || "")) return;
      const l = (await r.json()).siti || [];
      for (const x of l) stato.fonti.unshift({ id: `sito-${x.sito}`, nome: `${x.sito} – AGEA ${x.anno} (50 cm)`, licenza: x.licenza,
        citazione: x.citazione, scheda: x.scheda, stato: "confermata", copia: true, nei_report: true, zoom: x.zoom, riquadro: x.riquadro, pmtiles: x.pmtiles });
      if (l.length) { const d = $("siti"); d.hidden = false; d.textContent = `Ortofoto dei siti già pronte: ${l.map((x) => x.sito).join(", ")}.`; }
    } catch { /* nessun sito */ }
  }

  (async function avvio() {
    const m = new window.maplibregl.Map({ container: box, center: centro, zoom: Number(q.get("z")) || 16, maxZoom: 20, minZoom: 5,
      attributionControl: false, style: { version: 8, sources: {}, layers: [{ id: "sfondo", type: "background", paint: { "background-color": colore("--carta") } }] } });
    stato.mappa = m;
    m.addControl(new window.maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.addControl(new window.maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    m.addControl(new window.maplibregl.AttributionControl({ compact: true }), "bottom-right");
    await new Promise((ok) => m.on("load", ok));
    document.addEventListener("eugenio:ridimensiona", () => m.resize());
    document.addEventListener("eugenio:aspetto", () => {
      m.setPaintProperty("sfondo", "background-color", colore("--carta"));
      if (m.getLayer("edifici")) m.setPaintProperty("edifici", "line-color", colore("--primario"));
    });
    try {
      const r = await fetch("/api/ortofoto/fonti");
      if (!r.ok || !/json/.test(r.headers.get("Content-Type") || "")) throw new Error(String(r.status));
      stato.fonti = (await r.json()).fonti || [];
    } catch {
      messaggio("Il servizio delle ortofoto non risponde: riprova più tardi.", true); attribuzione(null); return;
    }
    if (window.pmtiles) { const proto = new window.pmtiles.Protocol(); window.maplibregl.addProtocol("pmtiles", proto.tile); }
    await siti();
    await edifici(m);
    $("edifici").addEventListener("change", (e) => { if (m.getLayer("edifici")) m.setLayoutProperty("edifici", "visibility", e.target.checked ? "visible" : "none"); });
    const c = [m.getCenter().lng, m.getCenter().lat], qui = stato.fonti.filter((f) => copre(f, c));
    const chiesta = stato.fonti.find((f) => f.id === q.get("fonte"));
    scegli(chiesta ? chiesta.id : qui.length ? qui[0].id : "");
    elenco();
    m.on("moveend", elenco);
    m.on("error", (e) => { if (e && e.sourceId === "ortofoto") messaggio("Alcune tessere non sono arrivate (fonte lenta o fuori zona).", true); });
  })();
  window.EUGENIO_ORTOFOTO = { stato };
})();
