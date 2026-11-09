"use strict";
// Pagina Patrimonio › Importa DXF/IFC (04/11/2026). Il file dell'utente si legge in un Web Worker (modelli_worker.js:
// dxf-parser, web-ifc, Clipper, proj4js, stessa logica di `importa-modello`), mai inviato al server. La pagina mostra la
// pianta dei corpi, fa scegliere la posa (dal file, sistema di riferimento, due punti noti, un punto e la rotazione o,
// dal 05/11/2026, agganciandolo alla sagoma di un edificio dell'archivio di EuGEnio, letta dai file statici /edifici3d/),
// disegna il risultato sulla mappa e lo passa alla pagina Modelli 3D nella memoria della scheda (sessionStorage) o
// lo fa scaricare come .geojson «eugenio-modello-1». Le richieste di rete della pagina sono solo le sue librerie e le
// tessere dell'ortofoto di sfondo (/api/ortofoto/…).
(function () {
  const $ = (id) => document.getElementById(id);
  const MOD = window.EUGENIO_MODELLI;
  if (!MOD || !$("file-modello")) return;
  const V = (() => { try { return new URL(document.currentScript.src).search; } catch { return ""; } })();
  const L = MOD.LIMITI;
  const CHIAVE = "eugenio-modello";
  const stato = { worker: null, timer: null, sintesi: null, geojson: null, nomeFile: "modello", scegli: null, mappa: null,
    marcatori: [null, null], fonti: [], fonte: null, piante: [], archivio: null, sagoma: null, celle: new Map() };
  const E = window.EUGENIO_EDIFICI;
  const colore = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || "#888";
  function h(tag, cls, t) { const e = document.createElement(tag); if (cls) e.className = cls; if (t !== undefined) e.textContent = t; return e; }
  function messaggio(id, t, tipo = "") {
    const m = $(id); m.textContent = t || "";
    m.classList.toggle("errore", tipo === "errore"); m.classList.toggle("successo", tipo === "ok"); m.classList.toggle("attenzione", tipo === "attenzione");
  }
  const num = (s) => { const t = String(s == null ? "" : s).trim().replace(/\s/g, "").replace(",", "."); return t === "" ? NaN : Number(t); };
  const fmt = (v, n = 2) => (Number.isFinite(+v) ? (+v).toLocaleString("it-IT", { maximumFractionDigits: n }) : "—");

  // ------------------------------------------------------------------ worker
  function nuovoWorker() {
    if (stato.worker) stato.worker.terminate();
    const w = new Worker(`modelli_worker.js${V}`);
    w.onmessage = (ev) => ricevi(ev.data || {});
    w.onerror = (e) => { fermaTimer(); messaggio("messaggio", `Lettura non riuscita: ${e.message || "errore del lettore"}. Prova a convertire il file sul PC (passo 5).`, "errore"); e.preventDefault && e.preventDefault(); };
    stato.worker = w;
    return w;
  }
  function fermaTimer() { if (stato.timer) clearTimeout(stato.timer); stato.timer = null; }
  function avviaTimer() {
    fermaTimer();
    stato.timer = setTimeout(() => {
      nuovoWorker();
      messaggio("messaggio", `Lettura interrotta dopo ${L.TEMPO_S} secondi: il modello è troppo complesso per il browser. Convertilo sul PC (passo 5).`, "errore");
    }, L.TEMPO_S * 1000);
  }
  function ricevi(m) {
    if (m.tipo === "stato") { messaggio("messaggio", m.testo); return; }
    fermaTimer();
    if (m.tipo === "errore") {
      if (stato.sintesi && !$("passo-posa").hidden) messaggio("messaggio-posa", `Posa non riuscita: ${m.testo}.`, "errore");
      else messaggio("messaggio", `Modello non letto: ${m.testo}.`, "errore");
      return;
    }
    if (m.tipo === "letto") mostraLettura(m.sintesi);
    if (m.tipo === "modello") mostraModello(m.geojson, true);
  }

  // ------------------------------------------------------------------ passo 1: file
  function azzera() {
    stato.sintesi = null; stato.geojson = null; stato.scegli = null; stato.piante = [];
    ["passo-letto", "passo-posa", "passo-risultato"].forEach((id) => { $(id).hidden = true; });
    messaggio("messaggio-posa", "");
    if (stato.mappa && stato.mappa.getSource("modello")) stato.mappa.getSource("modello").setData({ type: "FeatureCollection", features: [] });
    stato.marcatori.forEach((mk) => mk && mk.remove()); stato.marcatori = [null, null];
    document.querySelectorAll(".punti-posa input").forEach((i) => { i.value = ""; });
  }
  $("file-modello").addEventListener("change", async (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    azzera();
    const mb = f.size / 1024 / 1024;
    const av = $("avviso-pesante");             // .messaggio vuoto = nascosto (lo stile vince su «hidden»)
    av.hidden = mb <= L.CONSIGLIO_MB;
    av.textContent = mb <= L.CONSIGLIO_MB ? "" : mb > L.MAX_MB
      ? `File di ${fmt(mb, 0)} MB: oltre ${L.MAX_MB} MB il browser non lo apre. Convertilo sul PC (passo 5).`
      : `File di ${fmt(mb, 0)} MB: oltre ${L.CONSIGLIO_MB} MB la lettura nel browser può essere lenta o esaurire la memoria. Se si blocca, convertilo sul PC (passo 5).`;
    stato.nomeFile = MOD.pulisci(f.name.replace(/\.[^.]*$/, ""), 60) || "modello";
    try {
      if (/\.(geojson|json)$/i.test(f.name)) {
        if (f.size > 10 * 1024 * 1024) throw new Error("modello convertito oltre 10 MB");
        const d = JSON.parse(await f.text());
        if (!d || d.type !== "FeatureCollection" || d.formato !== MOD.FORMATO || !Array.isArray(d.features))
          throw new Error("non è un modello di EuGEnio (serve il .geojson prodotto da questa pagina o da «importa-modello»)");
        messaggio("messaggio", `Modello già convertito: ${d.features.length} corpi.`, "ok");
        mostraModello(d, false);
        return;
      }
      if (mb > L.MAX_MB) throw new MOD.ModelloNonValido(`file oltre ${L.MAX_MB} MB`);
      const testa = new Uint8Array(await f.slice(0, 256).arrayBuffer());
      MOD.controllaFile(f.name, f.size, testa);           // stessi controlli del worker, subito
      const dati = await f.arrayBuffer();
      messaggio("messaggio", "Lettura in corso, in questo browser…");
      avviaTimer();
      (stato.worker || nuovoWorker()).postMessage({ azione: "leggi", nome: f.name, dati, unita: num($("unita").value) || null }, [dati]);
    } catch (err) {
      messaggio("messaggio", `Modello non letto: ${err.message || err}.`, "errore");
    } finally { e.target.value = ""; }
  });

  // ------------------------------------------------------------------ passo 2: sintesi e pianta
  function mostraLettura(s) {
    stato.sintesi = s; stato.piante = s.piante || [];
    $("passo-letto").hidden = false; $("passo-posa").hidden = false;
    const tipi = {};
    for (const p of stato.piante) tipi[p.tetto] = (tipi[p.tetto] || 0) + 1;
    $("sintesi").textContent = `${s.tipo.toUpperCase()}${s.schema ? " " + s.schema : ""}: ${s.corpi} ${s.corpi === 1 ? "corpo" : "corpi"} (`
      + Object.entries(tipi).map(([k, v]) => `${v} ${k}`).join(", ") + `), unità del disegno ${fmt(s.unita_m, 4)} m.`;
    const ul = $("avvisi-lettura"); ul.innerHTML = "";
    for (const a of s.avvisi || []) ul.appendChild(h("li", null, a));
    messaggio("messaggio", "File letto: scegli come posizionarlo sulla mappa (passo 3).", "ok");
    disegnaPianta();
    const rf = $("riga-file");
    rf.hidden = !s.georef;
    $("posa-file").textContent = s.georef ? `(${s.georef.origine}${s.georef.crs ? ", " + s.georef.crs : ""})` : "";
    const scelta = s.georef ? "file" : "due_punti";
    document.querySelectorAll('input[name="posa"]').forEach((i) => { i.checked = i.value === scelta; });
    campiPosa();
    if (s.georef) $("posiziona").click();
  }
  function svgEl(tag, a, p) { const e = document.createElementNS("http://www.w3.org/2000/svg", tag); for (const [k, v] of Object.entries(a)) e.setAttribute(k, v); if (p) p.appendChild(e); return e; }
  function disegnaPianta() {
    const svg = $("pianta"); svg.innerHTML = "";
    const pts = stato.piante.flatMap((p) => p.sagoma);
    if (!pts.length) return;
    let x0 = Math.min(...pts.map((q) => q[0])), x1 = Math.max(...pts.map((q) => q[0]));
    let y0 = Math.min(...pts.map((q) => q[1])), y1 = Math.max(...pts.map((q) => q[1]));
    const m = Math.max(x1 - x0, y1 - y0, 1) * 0.06;
    x0 -= m; x1 += m; y0 -= m; y1 += m;
    svg.setAttribute("viewBox", `${x0} ${-y1} ${x1 - x0} ${y1 - y0}`);
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    stato.vista = { x0, x1, y0, y1, r: Math.max(x1 - x0, y1 - y0) / 160 };
    const g = svgEl("g", {}, svg);
    stato.piante.forEach((p) => svgEl("polygon", { class: "corpo", points: p.sagoma.map((q) => `${q[0]},${-q[1]}`).join(" ") }, g));
    for (const q of pts) svgEl("circle", { class: "spigolo", cx: q[0], cy: -q[1], r: stato.vista.r }, g);
    stato.segniPianta = svgEl("g", {}, svg);
    segniPianta();
  }
  function segniPianta() {
    if (!stato.segniPianta) return;
    stato.segniPianta.innerHTML = "";
    const k = (stato.sintesi && stato.sintesi.unita_m) || 1;
    puntiDaCampi().forEach((p, i) => {
      if (!Number.isFinite(p.x) || !Number.isFinite(p.y)) return;
      const x = p.x * k, y = p.y * k, r = stato.vista.r * 3;
      svgEl("circle", { class: "scelto", cx: x, cy: -y, r }, stato.segniPianta);
      const t = svgEl("text", { x: x + r * 1.4, y: -y - r * 1.4, "font-size": r * 4 }, stato.segniPianta); t.textContent = String(i + 1);
    });
  }
  $("pianta").addEventListener("click", (ev) => {
    if (!stato.vista) return;
    const svg = $("pianta"), pt = svg.createSVGPoint(); pt.x = ev.clientX; pt.y = ev.clientY;
    const q = pt.matrixTransform(svg.getScreenCTM().inverse());
    let x = q.x, y = -q.y, dm = Infinity, best = null;
    for (const s of stato.piante.flatMap((p) => p.sagoma)) { const d = Math.hypot(s[0] - x, s[1] - y); if (d < dm) { dm = d; best = s; } }
    if (best && dm < stato.vista.r * 12) { x = best[0]; y = best[1]; }
    const k = (stato.sintesi && stato.sintesi.unita_m) || 1;
    const riga = prossimaRiga("x");
    riga.querySelector('[data-c="x"]').value = +(x / k).toFixed(4);
    riga.querySelector('[data-c="y"]').value = +(y / k).toFixed(4);
    segniPianta();
    if ($("campi-punti").hidden) { document.querySelector('input[name="posa"][value="due_punti"]').checked = true; campiPosa(); }
    sceglieSullaMappa(+riga.dataset.punto);
  });
  function prossimaRiga(c) {           // la prima riga senza quel valore, altrimenti quella in scelta o la seconda
    const righe = [...document.querySelectorAll(".punti-posa tbody tr")].filter((r) => !r.hidden);
    return righe.find((r) => !r.querySelector(`[data-c="${c}"]`).value) || righe[stato.scegli != null ? stato.scegli : righe.length - 1] || righe[0];
  }
  function puntiDaCampi() {
    return [...document.querySelectorAll(".punti-posa tbody tr")].map((r) => {
      const v = (c) => num(r.querySelector(`[data-c="${c}"]`).value);
      return { x: v("x"), y: v("y"), lon: v("lon"), lat: v("lat") };
    });
  }

  // ------------------------------------------------------------------ passo 3: posa
  function sceltaPosa() { const i = document.querySelector('input[name="posa"]:checked'); return i ? i.value : "due_punti"; }
  function campiPosa() {
    const s = sceltaPosa();
    $("campi-crs").hidden = s !== "crs";
    $("campi-punti").hidden = !(s === "due_punti" || s === "punto");
    $("campo-rotazione").hidden = s !== "punto";
    $("campi-sagoma").hidden = s !== "sagoma";
    if (s === "sagoma") mostraArchivio();
    document.querySelector('.punti-posa tbody tr[data-punto="1"]').hidden = s === "punto";
    $("aiuto-mappa").textContent = s === "due_punti" || s === "punto"
      ? "Premi «sulla mappa» accanto al punto e poi fai clic sul punto vero: la pagina ne prende longitudine e latitudine."
      : "Trascina per spostare, rotella o due dita per ingrandire.";
  }
  document.querySelectorAll('input[name="posa"]').forEach((i) => i.addEventListener("change", campiPosa));
  for (const [c, [nome]] of Object.entries(MOD.SISTEMI)) { const o = h("option", null, `${c} – ${nome}`); o.value = c; $("crs").appendChild(o); }
  document.querySelectorAll(".punti-posa input").forEach((i) => i.addEventListener("input", () => { segniPianta(); marcatoriDaCampi(); }));
  document.querySelectorAll("[data-mappa]").forEach((b) => b.addEventListener("click", () => sceglieSullaMappa(+b.dataset.mappa)));
  function sceglieSullaMappa(i) {
    stato.scegli = i;
    document.querySelectorAll(".punti-posa tbody tr").forEach((r) => r.classList.toggle("in-scelta", +r.dataset.punto === i));
    messaggio("messaggio-posa", `Fai clic sulla mappa sul punto ${i + 1} vero (lo stesso spigolo scelto nella pianta).`);
    if (stato.mappa) stato.mappa.getCanvas().style.cursor = "crosshair";
  }
  function marcatoriDaCampi() {
    if (!stato.mappa || !window.maplibregl) return;
    puntiDaCampi().forEach((p, i) => {
      if (stato.marcatori[i]) { stato.marcatori[i].remove(); stato.marcatori[i] = null; }
      if (!Number.isFinite(p.lon) || !Number.isFinite(p.lat)) return;
      const el = h("div", "marcatore-punto", String(i + 1));
      Object.assign(el.style, { width: "22px", height: "22px", borderRadius: "50%", display: "grid", placeItems: "center", font: "700 12px sans-serif",
        background: colore("--attenzione"), color: "#111", border: "2px solid #fff" });
      stato.marcatori[i] = new window.maplibregl.Marker({ element: el }).setLngLat([p.lon, p.lat]).addTo(stato.mappa);
    });
  }
  $("posiziona").addEventListener("click", () => {
    if (!stato.sintesi || !stato.worker) { messaggio("messaggio-posa", "Prima carica un file DXF o IFC (passo 1).", "errore"); return; }
    const s = sceltaPosa();
    let posa = null;
    const pp = puntiDaCampi();
    const ok = (p) => [p.x, p.y, p.lon, p.lat].every(Number.isFinite);
    if (s === "file") posa = null;
    else if (s === "crs") posa = { tipo: "crs", crs: $("crs").value };
    else if (s === "due_punti") {
      if (!ok(pp[0]) || !ok(pp[1])) { messaggio("messaggio-posa", "Servono X, Y, longitudine e latitudine di tutti e due i punti.", "errore"); return; }
      posa = { tipo: "due_punti", punti: pp.map((p) => [p.x, p.y, p.lon, p.lat]) };
    } else if (s === "sagoma") {
      if (!stato.sagoma || !E) { messaggio("messaggio-posa", "Fai prima clic sulla sagoma di un edificio sulla mappa.", "errore"); return; }
      const r = E.posaDaSagoma(stato.piante.map((p) => p.sagoma), stato.sagoma.anelli);
      if (!r) { messaggio("messaggio-posa", "Aggancio non riuscito: il modello o la sagoma non hanno abbastanza punti.", "errore"); return; }
      const k = (stato.sintesi && stato.sintesi.unita_m) || 1;
      posa = { tipo: "due_punti", punti: r.punti.map(([x, y, lon, lat]) => [x / k, y / k, lon, lat]) };
      stato.aggancio = r;
      const avvisi = [];
      if (r.iou < 0.6) avvisi.push("le due impronte si sovrappongono poco: forse è un altro edificio, o il modello ha parti che la sagoma non ha");
      if (r.rapporto_aree && (r.rapporto_aree < 0.85 || r.rapporto_aree > 1.15))
        avvisi.push(`l'impronta del modello è il ${fmt(100 * r.rapporto_aree, 0)} % della sagoma: controlla le unità del disegno`);
      stato.notaAggancio = `Agganciato alla sagoma dell'edificio ${stato.sagoma.edificio}: rotazione ${fmt(r.rotazione, 1)}°, sovrapposizione ${fmt(100 * r.iou, 0)} %`
        + (avvisi.length ? ` – attenzione: ${avvisi.join("; ")}.` : ".");
    } else {
      const r = num($("rotazione").value);
      if (!ok(pp[0]) || !Number.isFinite(r)) { messaggio("messaggio-posa", "Servono X, Y, longitudine, latitudine del punto e la rotazione.", "errore"); return; }
      posa = { tipo: "punto", x: pp[0].x, y: pp[0].y, lon: pp[0].lon, lat: pp[0].lat, rotazione: r };
    }
    messaggio("messaggio-posa", "Posiziono il modello…");
    stato.worker.postMessage({ azione: "posa", posa });
  });

  // ------------------------------------------------------------------ passo 4: risultato
  function fuoriItalia(g) {
    return g.features.some((f) => (f.geometry.coordinates[0] || []).some((q) => !(q[0] > 6 && q[0] < 19 && q[1] > 35 && q[1] < 48)));
  }
  function mostraModello(g, daPosa) {
    stato.geojson = g;
    $("passo-risultato").hidden = false;
    const tb = $("tabella-corpi").querySelector("tbody"); tb.innerHTML = "";
    for (const f of g.features) {
      const p = f.properties || {}, tr = h("tr");
      const falde = (p.falde || []).filter((x) => x.pendenza >= 5).map((x) => `${fmt(x.pendenza, 0)}° ${x.settore}`).join(", ");
      [p.id, p.tetto, fmt(p.gronda), fmt(p.colmo), fmt(p.area, 0), falde || "piano"].forEach((v) => tr.appendChild(h("td", null, v == null ? "—" : String(v))));
      tb.appendChild(tr);
    }
    const ul = $("avvisi-modello"); ul.innerHTML = "";
    for (const a of g.avvisi || []) ul.appendChild(h("li", null, a));
    const fuori = fuoriItalia(g);
    $("apri-3d").disabled = fuori;
    if (daPosa && stato.notaAggancio && sceltaPosa() === "sagoma") {
      messaggio("messaggio-posa", fuori ? "Il modello cade fuori dall'Italia: controlla la posa." : `${stato.notaAggancio} Controllalo sulla mappa.`,
        fuori ? "errore" : /attenzione/.test(stato.notaAggancio) ? "attenzione" : "ok");
    } else if (daPosa) messaggio("messaggio-posa", fuori ? "Il modello cade fuori dall'Italia: controlla la posa (unità, punti, sistema di riferimento)." : "Modello posizionato: controllalo sulla mappa.", fuori ? "errore" : "ok");
    else if (fuori) messaggio("messaggio", "Il modello cade fuori dall'Italia: la pagina 3D non lo aprirà.", "errore");
    if (stato.mappa) {
      const src = stato.mappa.getSource("modello");
      if (src) src.setData(g);
      let b = null;
      for (const f of g.features) for (const q of f.geometry.coordinates[0]) b = b ? [Math.min(b[0], q[0]), Math.min(b[1], q[1]), Math.max(b[2], q[0]), Math.max(b[3], q[1])] : [q[0], q[1], q[0], q[1]];
      if (b) stato.mappa.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 60, maxZoom: 19, duration: 500 });
    }
  }
  $("apri-3d").addEventListener("click", () => {
    if (!stato.geojson) return;
    try {
      sessionStorage.setItem(CHIAVE, JSON.stringify({ nome: stato.nomeFile, testo: JSON.stringify(stato.geojson) }));
    } catch {
      messaggio("messaggio-posa", "Il browser non ha spazio per passare il modello alla pagina 3D: scaricalo e aprilo là con «Usa il tuo modello».", "errore");
      return;
    }
    location.href = "modelli3d.html?modello=locale";
  });
  $("scarica").addEventListener("click", () => {
    if (!stato.geojson) return;
    const a = h("a"); a.href = URL.createObjectURL(new Blob([JSON.stringify(stato.geojson)], { type: "application/geo+json" }));
    a.download = `${stato.nomeFile}.geojson`; document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  });

  // ------------------------------------------------------------------ sagome dell'archivio (posa «sagoma», 05/11/2026)
  // Stessi file statici della pagina 3D (celle di 0,01° in contesto/), letti solo quando si sceglie questa posa: sono
  // richieste GET di file pubblici, il modello dell'utente non lascia mai il browser.
  const BASI = ["/edifici3d/cc-by/er/prodotti/", "dati/edifici3d/"];
  async function leggiJson(u) { const r = await fetch(u); if (!r.ok || !/json/.test(r.headers.get("Content-Type") || "")) throw new Error(String(r.status)); return r.json(); }
  async function archivio() {
    if (stato.archivio !== null) return stato.archivio;
    stato.archivio = false;
    for (const b of BASI) {
      try { const ind = await leggiJson(`${b}indice.json`); stato.archivio = { base: b, indice: ind }; break; } catch { /* la prossima */ }
    }
    return stato.archivio;
  }
  async function mostraArchivio(centra = true) {
    const m = stato.mappa, a = await archivio();
    if (!m || !m.getSource("archivio")) return;
    if (!a) { $("sagoma-scelta").textContent = "L'archivio degli edifici non è disponibile su questo server: usa un'altra posa."; return; }
    if (centra && !stato.archivioCentrato && a.indice.centro && !stato.geojson) {
      stato.archivioCentrato = true;
      const c = m.getCenter(), [lon, lat] = a.indice.centro;
      if (Math.hypot(c.lng - lon, c.lat - lat) > 0.005) m.jumpTo({ center: [lon, lat], zoom: Math.max(m.getZoom(), 16.5) });
    }
    const cella = a.indice.cella || 0.01, c = m.getCenter(), feats = new Map();
    const nomi = [];
    for (let i = Math.floor((c.lng - 0.005) / cella); i <= Math.floor((c.lng + 0.005) / cella); i++)
      for (let j = Math.floor((c.lat - 0.004) / cella); j <= Math.floor((c.lat + 0.004) / cella); j++) nomi.push(`${i}_${j}`);
    // (09/11/2026 b) solo le celle che l'archivio ha davvero (indice.nomi_celle): niente 404 in Console fuori dagli edifici
    const ha = Array.isArray(a.indice.nomi_celle) ? new Set(a.indice.nomi_celle) : null;
    for (const n of nomi) {
      if (ha && !ha.has(n)) continue;
      if (!stato.celle.has(n)) stato.celle.set(n, leggiJson(`${a.base}contesto/${n}.json`).catch(() => ({ features: [] })));
      ((await stato.celle.get(n)).features || []).forEach((f) => feats.set(String(f.properties.id), f));
    }
    stato.featArchivio = [...feats.values()];
    m.getSource("archivio").setData({ type: "FeatureCollection", features: stato.featArchivio });
    if (a.indice.sintetico) $("sagoma-scelta").textContent = stato.sagoma ? $("sagoma-scelta").textContent
      : "Archivio di prova sintetico (isolato inventato vicino a Rimini): fai clic su un edificio.";
  }
  function scegliSagoma(ev) {
    const m = stato.mappa;
    const fs = m.queryRenderedFeatures(ev.point, { layers: ["archivio-area"] });
    if (!fs.length) { messaggio("messaggio-posa", "Qui non c'è una sagoma dell'archivio: fai clic dentro un contorno tratteggiato.", "attenzione"); return; }
    const ed = String(fs[0].properties.edificio);
    const corpi = ((stato.featArchivio && stato.featArchivio.length) ? stato.featArchivio : fs).filter((f) => String(f.properties.edificio) === ed);
    const anelli = corpi.map((f) => (f.geometry.type === "MultiPolygon" ? f.geometry.coordinates[0][0] : f.geometry.coordinates[0]));
    stato.sagoma = { edificio: ed, anelli };
    m.getSource("sagoma").setData({ type: "FeatureCollection", features: corpi });
    const lic = [...new Set(corpi.map((f) => f.properties.licenza).filter(Boolean))].join(", ");
    $("sagoma-scelta").textContent = `Sagoma scelta: edificio ${ed}, ${corpi.length} ${corpi.length === 1 ? "corpo" : "corpi"}`
      + (lic ? ` (${lic})` : "") + ". Ora premi «Posiziona il modello».";
    messaggio("messaggio-posa", "");
  }

  // ------------------------------------------------------------------ mappa con l'ortofoto di sfondo
  const copre = (f, [lon, lat]) => lon >= f.riquadro[0] && lon <= f.riquadro[2] && lat >= f.riquadro[1] && lat <= f.riquadro[3];
  function attribuzione(f) {
    const a = $("attribuzione"); a.innerHTML = "";
    if (!f) { a.textContent = stato.fonti.length ? "Nessuna ortofoto copre questa zona." : ""; return; }
    a.append("Ortofoto: ", f.citazione, " – licenza ");
    const l = h("a", null, f.licenza); l.href = f.scheda; a.appendChild(l);
    a.append(f.stato === "da confermare" ? ". Uso tramite il server di EuGEnio in attesa di conferma della fonte." : ".");
  }
  function sfondo() {
    const m = stato.mappa; if (!m) return;
    const c = [m.getCenter().lng, m.getCenter().lat];
    if (stato.fonte && copre(stato.fonte, c)) return;
    const f = stato.fonti.find((x) => copre(x, c) && x.copia) || stato.fonti.find((x) => copre(x, c)) || null;
    if (m.getLayer("ortofoto")) m.removeLayer("ortofoto");
    if (m.getSource("ortofoto")) m.removeSource("ortofoto");
    stato.fonte = f;
    if (f && f.tessere) {
      m.addSource("ortofoto", { type: "raster", tiles: [location.origin + f.tessere], tileSize: 256, minzoom: f.zoom[0], maxzoom: f.zoom[1], attribution: f.citazione });
      m.addLayer({ id: "ortofoto", type: "raster", source: "ortofoto" }, "modello-area");
    }
    attribuzione(f);
  }
  (async function avvio() {
    const box = $("mappa-importa");
    if (!box || !window.maplibregl) return;
    const q = new URLSearchParams(location.search);
    try {
      const m = new window.maplibregl.Map({ container: box, center: [Number(q.get("lon")) || 12.5683, Number(q.get("lat")) || 44.0594],
        zoom: Number(q.get("z")) || 15, maxZoom: 20, minZoom: 5, attributionControl: false,
        style: { version: 8, sources: {}, layers: [{ id: "sfondo", type: "background", paint: { "background-color": colore("--carta") } }] } });
      if (window.EUGENIO_LIMITI) window.EUGENIO_LIMITI.collega(m);   // 429 delle fonti (09/11/2026)
      stato.mappa = m;
      m.addControl(new window.maplibregl.NavigationControl({ showCompass: false }), "top-right");
      m.addControl(new window.maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
      m.addControl(new window.maplibregl.AttributionControl({ compact: true }), "bottom-right");
      await new Promise((ok) => m.on("load", ok));
      m.addSource("modello", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addLayer({ id: "modello-area", type: "fill", source: "modello", paint: { "fill-color": colore("--primario"), "fill-opacity": 0.35 } });
      m.addLayer({ id: "modello-linea", type: "line", source: "modello", paint: { "line-color": colore("--primario"), "line-width": 2 } });
      m.addSource("archivio", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addSource("sagoma", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addLayer({ id: "archivio-area", type: "fill", source: "archivio", paint: { "fill-color": colore("--inchiostro"), "fill-opacity": 0.04 } }, "modello-area");
      m.addLayer({ id: "archivio-linea", type: "line", source: "archivio", paint: { "line-color": colore("--inchiostro"), "line-width": 1, "line-dasharray": [2, 2] } }, "modello-area");
      m.addLayer({ id: "sagoma-linea", type: "line", source: "sagoma", paint: { "line-color": colore("--attenzione"), "line-width": 3 } });
      document.addEventListener("eugenio:ridimensiona", () => m.resize());
      document.addEventListener("eugenio:aspetto", () => {
        m.setPaintProperty("sfondo", "background-color", colore("--carta"));
        m.setPaintProperty("modello-area", "fill-color", colore("--primario")); m.setPaintProperty("modello-linea", "line-color", colore("--primario"));
      });
      m.on("click", (ev) => {
        if (stato.scegli == null && sceltaPosa() === "sagoma") { scegliSagoma(ev); return; }
        if (stato.scegli == null) return;
        const r = document.querySelector(`.punti-posa tbody tr[data-punto="${stato.scegli}"]`);
        r.querySelector('[data-c="lon"]').value = ev.lngLat.lng.toFixed(7);
        r.querySelector('[data-c="lat"]').value = ev.lngLat.lat.toFixed(7);
        r.classList.remove("in-scelta");
        messaggio("messaggio-posa", `Punto ${stato.scegli + 1} fissato sulla mappa.`, "ok");
        stato.scegli = null; m.getCanvas().style.cursor = "";
        marcatoriDaCampi();
      });
      try {
        const r = await fetch("/api/ortofoto/fonti");
        if (r.ok && /json/.test(r.headers.get("Content-Type") || "")) stato.fonti = ((await r.json()).fonti || []).filter((f) => f.tessere);
      } catch { /* senza ortofoto la mappa resta neutra: le coordinate si possono scrivere a mano */ }
      if (!stato.fonti.length) $("attribuzione").textContent = "Ortofoto non disponibili: puoi scrivere longitudine e latitudine a mano.";
      sfondo();
      m.on("moveend", sfondo);
      m.on("moveend", () => { if (sceltaPosa() === "sagoma") mostraArchivio(false); });
      if (stato.geojson) mostraModello(stato.geojson, false);
    } catch (e) {
      $("attribuzione").textContent = `La mappa non si è aperta (${e.message || e}): puoi comunque scrivere le coordinate a mano.`;
    }
  })();
  window.EUGENIO_IMPORTA = { stato };
})();
