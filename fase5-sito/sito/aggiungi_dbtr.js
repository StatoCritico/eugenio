"use strict";
// Pagina Patrimonio › Aggiungi edifici (DB topografico) (07/11/2026, decisione di Paolo).
// Due destinazioni:
//  1. subito, solo per chi carica: il file si legge nel Web Worker (dbtr_worker.js con dbtr_lettore.js, stessa logica di
//     uvl.py e regionali.py) e i corpi passano a Modelli 3D dentro il browser (dbtr_locale.js), senza server;
//  2. dopo l'approvazione di Stato Critico, per tutti: solo con il consenso esplicito (casella non spuntata) lo stesso
//     file va a pezzi alla coda del server (POST /api/dbtr/inizia con Turnstile, PUT /api/dbtr/{id}/pezzo/{n},
//     POST /api/dbtr/{id}/fine), che lo prepara e lo mostra nella pagina interna per l'approvazione.
(function () {
  const $ = (id) => document.getElementById(id);
  const V = (document.currentScript && /[?&]v=([\w-]+)/.exec(document.currentScript.src) || [])[1] || "";
  const conV = (u) => (V ? `${u}?v=${V}` : u);
  const fmt = (v, d = 0) => (v === null || v === undefined || !Number.isFinite(+v) ? "—" : (+v).toLocaleString("it-IT", { maximumFractionDigits: d, minimumFractionDigits: d }));
  const colore = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || "#888";
  function h(tag, cls, testo) { const e = document.createElement(tag); if (cls) e.className = cls; if (testo !== undefined && testo !== null) e.textContent = String(testo); return e; }
  function messaggio(id, t, tipo) { const m = $(id); if (!m) return; m.textContent = t || ""; m.classList.toggle("errore", tipo === "errore"); m.classList.toggle("ok", tipo === "ok"); }
  const REGIONI = { er: { nome: "Emilia-Romagna", istat: "08" }, lom: { nome: "Lombardia", istat: "03" },
    fvg: { nome: "Friuli Venezia Giulia", istat: "06" }, lig: { nome: "Liguria", istat: "07" } };
  const MAX_MB = 300, PROPOSTE = "eugenio-dbtr-proposte";
  const stato = { mappa: null, fonti: [], fonte: null, files: [], features: null, sintesi: null, lavoro: null, inviando: false };
  window.EUGENIO_AGGIUNGI_DBTR = { stato };

  // ------------------------------------------------------------------ regione e comune
  async function comuni() {
    const r = REGIONI[$("regione").value];
    const sel = $("comune");
    sel.innerHTML = ""; sel.appendChild(new Option("— scegli il comune —", ""));
    try {
      const d = await (await fetch(conV(`dati/mappa/${r.istat}.json`))).json();
      (d.comuni || []).slice().sort((a, b) => a.nome.localeCompare(b.nome, "it")).forEach((c) => sel.appendChild(new Option(c.nome, c.istat)));
    } catch { sel.appendChild(new Option("(elenco dei comuni non disponibile)", "")); }
  }
  const comuneScelto = () => { const o = $("comune").selectedOptions[0]; return o && o.value ? { istat: o.value, nome: o.textContent } : null; };

  // ------------------------------------------------------------------ lettura nel Web Worker
  function lavoratore() {
    if (!stato.lavoro) {
      stato.lavoro = new Worker(conV("dbtr_worker.js"));
    }
    return stato.lavoro;
  }
  function chiedi(msg, trasferibili = []) {
    return new Promise((ok, no) => {
      const w = lavoratore();
      w.onmessage = (ev) => {
        const m = ev.data || {};
        if (m.tipo === "stato") { messaggio("messaggio", m.testo); return; }
        if (m.tipo === "errore") no(new Error(m.testo)); else ok(m);
      };
      w.onerror = (e) => no(new Error(e.message || "errore del lettore"));
      w.postMessage(msg, trasferibili);
    });
  }
  async function leggiFile(lista) {
    const files = [...lista].filter((f) => /\.(zip|gpkg|shp|shx|dbf|prj|cpg|xml)$/i.test(f.name));
    if (!files.length) { messaggio("messaggio", "Nessun file utile: servono uno zip, un GeoPackage (.gpkg) o le parti di uno Shapefile (.shp, .dbf…).", "errore"); return; }
    const mb = files.reduce((s, f) => s + f.size, 0) / 1048576;
    if (mb > MAX_MB) { messaggio("messaggio", `File di ${fmt(mb)} MB: nel browser al massimo ${MAX_MB} MB. Prova con un comune più piccolo.`, "errore"); return; }
    stato.files = files; stato.features = null; stato.sintesi = null;
    $("passo-letto").hidden = true; $("passo-proponi").hidden = true;
    messaggio("messaggio", `Leggo ${files.length === 1 ? files[0].name : `${files.length} file`} (${fmt(mb, 1)} MB) in questo browser…`);
    const t0 = performance.now();
    try {
      const dati = await Promise.all(files.map(async (f) => ({ nome: f.webkitRelativePath || f.name, dati: await f.arrayBuffer() })));
      const r = await chiedi({ azione: "leggi", files: dati, regione: $("regione").value }, dati.map((d) => d.dati));
      stato.features = r.features; stato.sintesi = r.sintesi;
      messaggio("messaggio", `File letto in ${fmt((performance.now() - t0) / 1000, 1)} s: ${fmt(r.sintesi.corpi)} corpi di ${fmt(r.sintesi.edifici)} edifici.`, "ok");
      mostraSintesi();
      mostraMappa();
    } catch (e) {
      messaggio("messaggio", `File non letto: ${e.message || e}`, "errore");
      if ($("regione").value === "lig") $("passo-proponi").hidden = false;     // Liguria: si può solo proporre
      aggiornaProponi();
    }
  }
  function mostraSintesi() {
    const s = stato.sintesi, c = comuneScelto();
    $("passo-letto").hidden = false; $("passo-proponi").hidden = false;
    $("sintesi").textContent = `${s.fonte} – ${c ? c.nome : "comune non scelto"}${s.sperimentale ? " (lettore sperimentale)" : ""}. Licenza ${s.licenza}: ${s.attribuzione}.`;
    const tb = $("tabella-sintesi").tBodies[0]; tb.innerHTML = "";
    const riga = (k, v) => { const tr = tb.insertRow(); tr.appendChild(h("th", null, k)); tr.appendChild(h("td", null, v)); };
    riga("Corpi con altezza", `${fmt(s.corpi)} (di ${fmt(s.edifici)} edifici)`);
    riga("Scartati", s.scartati ? `${fmt(s.scartati)}: ${Object.entries(s.scarti).filter(([k]) => !/non valida/.test(k)).map(([k, v]) => `${k} ${fmt(v)}`).join("; ")}` : "nessuno");
    riga("Altezza di gronda", `mediana ${fmt(s.gronda_m.mediana, 1)} m, 95° percentile ${fmt(s.gronda_m.p95, 1)} m, massimo ${fmt(s.gronda_m.max, 1)} m`);
    if (s.convenzione) riga("Convenzione delle altezze", s.convenzione === "quote" ? "quote (H_UVL decimale = quota del tetto: altezza = H_UVL − B_UVL)" : "altezze (H_UVL è sempre l'altezza del corpo)");
    riga("Tetti a capanna (colmo)", fmt(s.a_capanna));
    riga("Corpi con cortile", fmt(s.con_cortile));
    if (s.regione === "er") { riga("Con foglio e numero", fmt(s.con_foglio_numero)); riga("Con destinazione d'uso", fmt(s.con_destinazione)); }
    if (s.comuni_catastali && s.comuni_catastali.length) riga("Comuni catastali", s.comuni_catastali.join(", "));
    if (s.sorgente) riga("Strato letto", `${s.sorgente.nome} (${s.sorgente.tipo === "gpkg" ? "GeoPackage" : "Shapefile"}, ${s.sorgente.sistema || "sistema dal file"})`);
    if (s.scarti["geometria non valida (non riparata nel browser)"]) riga("Geometrie non valide", `${fmt(s.scarti["geometria non valida (non riparata nel browser)"])} (usate così come sono; sul server si riparano)`);
    riga("Terreno", s.terreno);
    const ul = $("avvisi-lettura"); ul.innerHTML = "";
    const avvisi = s.avvisi.slice();
    const lato = Math.max(s.riquadro[2] - s.riquadro[0], s.riquadro[3] - s.riquadro[1]);
    if ($("intero").checked && lato < 0.02) avvisi.push(`il file copre un riquadro di circa ${fmt(lato * 111, 1)} km: se è solo una parte del comune, togli la spunta «comune intero» e rileggi`);
    if (!c) avvisi.push("scegli il comune dell'estrazione (passo 2) prima di aprire Modelli 3D o di proporre il file");
    avvisi.forEach((a) => ul.appendChild(h("li", null, a)));
    aggiornaProponi();
  }

  // ------------------------------------------------------------------ mappa con l'ortofoto
  const copre = (f, [lon, lat]) => lon >= f.riquadro[0] && lon <= f.riquadro[2] && lat >= f.riquadro[1] && lat <= f.riquadro[3];
  function attribuzione(f) {
    const a = $("attribuzione"); a.innerHTML = "";
    if (stato.sintesi) a.append(`Edifici: ${stato.sintesi.attribuzione} (dal tuo file). `);
    if (!f) return;
    a.append("Ortofoto: ", f.citazione, " – licenza ");
    const l = h("a", null, f.licenza); l.href = f.scheda; a.appendChild(l); a.append(".");
  }
  function sfondo() {
    const m = stato.mappa; if (!m) return;
    const c = [m.getCenter().lng, m.getCenter().lat];
    const f = stato.fonti.find((x) => copre(x, c) && x.copia) || stato.fonti.find((x) => copre(x, c)) || null;
    if (f !== stato.fonte) {
      if (m.getLayer("ortofoto")) m.removeLayer("ortofoto");
      if (m.getSource("ortofoto")) m.removeSource("ortofoto");
      stato.fonte = f;
      if (f && f.tessere) {
        m.addSource("ortofoto", { type: "raster", tiles: [location.origin + f.tessere], tileSize: 256, minzoom: f.zoom[0], maxzoom: f.zoom[1], attribution: f.citazione });
        m.addLayer({ id: "ortofoto", type: "raster", source: "ortofoto" }, "edifici-area");
      }
    }
    attribuzione(f);
  }
  const COLORI = ["interpolate", ["linear"], ["get", "gronda"], 3, "#ffffb2", 9, "#fecc5c", 15, "#fd8d3c", 25, "#f03b20", 40, "#bd0026"];
  function mostraMappa() {
    const m = stato.mappa; if (!m || !stato.features) return;
    m.getSource("edifici").setData({ type: "FeatureCollection", features: stato.features });
    const r = stato.sintesi.riquadro;
    m.fitBounds([[r[0], r[1]], [r[2], r[3]]], { padding: 30, duration: 0, maxZoom: 17 });
    $("legenda-dbtr").textContent = "Colori per altezza di gronda: giallo chiaro 3 m, arancio 15 m, rosso 25 m, rosso scuro 40 m e oltre. Fai clic su un edificio per i suoi dati.";
    sfondo();
  }
  (async function avvioMappa() {
    const box = $("mappa-dbtr");
    if (!box || !window.maplibregl) return;
    try {
      const m = new window.maplibregl.Map({ container: box, center: [12.0, 44.3], zoom: 7, maxZoom: 20, minZoom: 5, attributionControl: false,
        style: { version: 8, sources: {}, layers: [{ id: "sfondo", type: "background", paint: { "background-color": colore("--carta") } }] } });
      if (window.EUGENIO_LIMITI) window.EUGENIO_LIMITI.collega(m);   // 429 delle fonti (09/11/2026)
      stato.mappa = m;
      m.addControl(new window.maplibregl.NavigationControl({ showCompass: false }), "top-right");
      m.addControl(new window.maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
      m.addControl(new window.maplibregl.AttributionControl({ compact: true }), "bottom-right");
      await new Promise((ok) => m.on("load", ok));
      m.addSource("edifici", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addLayer({ id: "edifici-area", type: "fill", source: "edifici", paint: { "fill-color": COLORI, "fill-opacity": 0.75 } });
      m.addLayer({ id: "edifici-linea", type: "line", source: "edifici", minzoom: 14, paint: { "line-color": colore("--inchiostro"), "line-width": 0.6 } });
      m.on("click", "edifici-area", (e) => {
        const p = e.features[0].properties;
        new window.maplibregl.Popup({ closeButton: true }).setLngLat(e.lngLat).setText(
          `${p.nome || "Edificio"}${p.foglio ? ` – foglio ${p.foglio} numero ${p.numero || "—"}` : ""}: gronda ${fmt(p.gronda, 1)} m`
          + `${p.colmo ? `, colmo ${fmt(p.colmo, 1)} m` : ""}, ${fmt(p.area)} m²${p.destinazione ? `, ${p.destinazione}` : ""}`).addTo(m);
      });
      document.addEventListener("eugenio:ridimensiona", () => m.resize());
      document.addEventListener("eugenio:aspetto", () => m.setPaintProperty("sfondo", "background-color", colore("--carta")));
      try {
        const r = await fetch("/api/ortofoto/fonti");
        if (r.ok && /json/.test(r.headers.get("Content-Type") || "")) stato.fonti = ((await r.json()).fonti || []).filter((f) => f.tessere);
      } catch { /* senza ortofoto la mappa resta neutra */ }
      m.on("moveend", sfondo);
      if (stato.features) mostraMappa();
    } catch (e) {
      $("legenda-dbtr").textContent = `La mappa non si è aperta (${e.message || e}): la lettura del file funziona lo stesso.`;
    }
  })();

  // ------------------------------------------------------------------ Modelli 3D (solo in questo browser)
  // (07/11/2026 sera, prova 6 di Paolo: «Apri» e «Togli» sembravano non fare nulla) l'esito si scrive accanto ai pulsanti,
  // i pulsanti restano spenti mentre lavorano e IndexedDB ha un tempo massimo
  const conTempo = (p, ms, cosa) => Promise.race([p, new Promise((_, no) => setTimeout(() => no(new Error(`${cosa}: nessuna risposta in ${ms / 1000} s`)), ms))]);
  function occupato(si) { ["apri-3d", "togli-locale"].forEach((id) => { const b = $(id); if (b) b.disabled = si; }); }
  async function apri3d() {
    const s = stato.sintesi, c = comuneScelto();
    if (!stato.features || !s) { messaggio("messaggio-3d", "Carica prima il file (passo 3).", "errore"); return; }
    if (!c) { messaggio("messaggio-3d", "Scegli prima il comune dell'estrazione (passo 2, più in alto).", "errore"); $("comune").focus(); return; }
    const L = window.EUGENIO_DBTR_LOCALE;
    if (!L) { messaggio("messaggio-3d", "Il modulo che conserva gli edifici nel browser non si è caricato: ricarica la pagina (Ctrl+F5).", "errore"); return; }
    occupato(true);
    messaggio("messaggio-3d", `Conservo ${fmt(s.corpi)} corpi in questo browser e apro Modelli 3D…`);
    try {
      await conTempo(L.salva({ formato: "eugenio-dbtr-locale-1", features: stato.features, regione: s.regione, comune: c.nome,
        istat: $("intero").checked ? c.istat : null, nome: `${s.fonte.replace(/ – .*$/, "")} – ${c.nome} (dal tuo file)`,
        licenza: s.licenza, attribuzione: s.attribuzione, riquadro: s.riquadro, data: new Date().toISOString(), corpi: s.corpi }), 30000, "memoria del browser");
    } catch (e) {
      occupato(false);
      messaggio("messaggio-3d", `Il browser non ha conservato gli edifici (${e.message || e}): finestra privata, dati del sito bloccati o un'altra scheda di EuGEnio che tiene occupata la memoria? Chiudi le altre schede e riprova.`, "errore");
      return;
    }
    location.href = `modelli3d.html?dbtr=locale&lon=${((s.riquadro[0] + s.riquadro[2]) / 2).toFixed(6)}&lat=${((s.riquadro[1] + s.riquadro[3]) / 2).toFixed(6)}`;
  }
  async function togliLocale() {
    const L = window.EUGENIO_DBTR_LOCALE;
    occupato(true);
    try {
      const prima = L ? await conTempo(L.leggi(), 15000, "memoria del browser") : null;
      if (L) await conTempo(L.togli(), 15000, "memoria del browser");
      messaggio("messaggio-3d", prima ? `Edifici del file (${prima.comune || "comune"}, ${fmt(prima.corpi)} corpi) tolti da questo browser: Modelli 3D torna agli archivi del server. Il file letto resta in questa pagina finché non la chiudi.`
        : "In questo browser non c'erano edifici di un file da togliere: Modelli 3D usa già gli archivi del server.", "ok");
    } catch (e) {
      messaggio("messaggio-3d", `Non sono riuscito a togliere gli edifici (${e.message || e}). Chiudi le altre schede di EuGEnio e riprova.`, "errore");
    } finally { occupato(false); }
  }

  // ------------------------------------------------------------------ proposta all'archivio comune
  function aggiornaProponi() {
    const b = $("proponi");
    const c = comuneScelto();
    const pronto = stato.files.length && c && $("consenso").checked && !stato.inviando
      && (stato.sintesi ? stato.sintesi.dentro_regione !== false : $("regione").value === "lig");
    b.disabled = !pronto;
  }
  async function sha256(buf) {
    const d = await crypto.subtle.digest("SHA-256", buf);
    return Array.from(new Uint8Array(d), (x) => x.toString(16).padStart(2, "0")).join("");
  }
  async function pacchetto() {
    const f = stato.files;
    if (f.length === 1) {
      const buf = await f[0].arrayBuffer();
      const u = new Uint8Array(buf, 0, Math.min(16, buf.byteLength));
      const gpkg = u[0] === 0x53 && u[1] === 0x51 && u[2] === 0x4c && u[3] === 0x69;
      const zip = u[0] === 0x50 && u[1] === 0x4b;
      if (gpkg || zip) return { buf, formato: gpkg ? "gpkg" : "zip" };
    }
    const dati = await Promise.all(f.map(async (x) => ({ nome: x.webkitRelativePath || x.name, dati: await x.arrayBuffer() })));
    const r = await chiedi({ azione: "impacchetta", files: dati }, dati.map((d) => d.dati));
    return { buf: r.dati.buffer.slice(r.dati.byteOffset, r.dati.byteOffset + r.dati.byteLength), formato: "zip" };
  }
  async function risposta(r) {
    let d = null; try { d = await r.json(); } catch { d = null; }
    if (!r.ok) throw new Error(d && typeof d.detail === "string" ? d.detail : `il server ha risposto ${r.status}`);
    return d;
  }
  async function proponi() {
    const c = comuneScelto();
    if (!c || !$("consenso").checked) return;
    stato.inviando = true; aggiornaProponi();
    const bar = $("avanzamento"); bar.hidden = false; bar.value = 0;
    try {
      messaggio("messaggio-proposta", "Preparo il file…");
      const { buf, formato } = await pacchetto();
      if (buf.byteLength > MAX_MB * 1048576) throw new Error(`file di ${fmt(buf.byteLength / 1048576)} MB: al massimo ${MAX_MB} MB`);
      const impronta = await sha256(buf);
      messaggio("messaggio-proposta", "Apro la proposta (verifica anti-robot)…");
      const ini = await risposta(await fetch("/api/dbtr/inizia", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ regione: $("regione").value, comune: c.nome, istat: c.istat, intero: $("intero").checked, formato,
          dimensione: buf.byteLength, consenso: true, impronta }) }));
      const h = { [`X-EuGEnio-Dbtr`]: ini.gettone };
      for (let n = 0; n < ini.pezzi; n++) {
        const pezzo = buf.slice(n * ini.pezzo_byte, Math.min(buf.byteLength, (n + 1) * ini.pezzo_byte));
        let ok = false, ultimo = null;
        for (let t = 0; t < 3 && !ok; t++) {
          try { await risposta(await fetch(`/api/dbtr/${ini.id}/pezzo/${n}`, { method: "PUT", headers: h, body: pezzo })); ok = true; }
          catch (e) { ultimo = e; await new Promise((x) => setTimeout(x, 1500 * (t + 1))); }
        }
        if (!ok) throw ultimo;
        bar.value = Math.round(100 * (n + 1) / ini.pezzi);
        messaggio("messaggio-proposta", `Invio: ${fmt(bar.value)} % (${n + 1} di ${ini.pezzi} pezzi)…`);
      }
      const fine = await risposta(await fetch(`/api/dbtr/${ini.id}/fine`, { method: "POST", headers: h }));
      ricorda({ id: ini.id, gettone: ini.gettone, comune: c.nome, regione: $("regione").value, data: new Date().toISOString() });
      messaggio("messaggio-proposta", `Grazie! ${fine.messaggio}`, "ok");
      $("consenso").checked = false;
      mostraProposte();
    } catch (e) {
      messaggio("messaggio-proposta", `Invio non riuscito: ${e.message || e}`, "errore");
    } finally {
      stato.inviando = false; bar.hidden = true; aggiornaProponi();
    }
  }
  function proposte() { try { return JSON.parse(localStorage.getItem(PROPOSTE) || "[]").filter((x) => x && /^[0-9a-f]{32}$/.test(x.id)); } catch { return []; } }
  function ricorda(p) { try { localStorage.setItem(PROPOSTE, JSON.stringify([p, ...proposte()].slice(0, 10))); } catch { /* niente */ } }
  function dimentica(id) { try { localStorage.setItem(PROPOSTE, JSON.stringify(proposte().filter((x) => x.id !== id))); } catch { /* niente */ } }
  async function mostraProposte() {
    const box = $("proposte"); box.innerHTML = "";
    const l = proposte();
    if (!l.length) return;
    box.appendChild(h("h3", null, "Le tue proposte (da questo browser)"));
    const ul = h("ul", "elenco-breve"); box.appendChild(ul);
    for (const p of l) {
      const li = h("li", null, `${p.comune} (${new Date(p.data).toLocaleDateString("it-IT")}): `); ul.appendChild(li);
      const s = h("span", null, "controllo…"); li.appendChild(s);
      try {
        const r = await fetch(`/api/dbtr/${p.id}`, { headers: { "X-EuGEnio-Dbtr": p.gettone } });
        if (r.status === 404) { s.textContent = "non più in coda (ritirata o scaduta)."; dimentica(p.id); continue; }
        const d = await risposta(r);
        s.textContent = d.messaggio;
        if (["caricamento", "ricevuto", "in attesa di approvazione", "controlli non superati"].includes(d.stato)) {
          const b = h("button", "bottone secondario piccolo", "Ritira"); b.type = "button";
          b.addEventListener("click", async () => {
            try { const x = await risposta(await fetch(`/api/dbtr/${p.id}`, { method: "DELETE", headers: { "X-EuGEnio-Dbtr": p.gettone } })); dimentica(p.id); messaggio("messaggio-proposta", x.messaggio, "ok"); mostraProposte(); }
            catch (e) { messaggio("messaggio-proposta", `Ritiro non riuscito: ${e.message || e}`, "errore"); }
          });
          li.append(" "); li.appendChild(b);
        }
        if (["installato", "rifiutato"].includes(d.stato)) dimentica(p.id);
      } catch (e) { s.textContent = `stato non disponibile (${e.message || e}).`; }
    }
  }

  // ------------------------------------------------------------------ avvio
  $("regione").addEventListener("change", () => { comuni(); if (stato.files.length) leggiFile(stato.files); });
  $("comune").addEventListener("change", () => { if (stato.sintesi) mostraSintesi(); aggiornaProponi(); });
  $("intero").addEventListener("change", () => { if (stato.sintesi) mostraSintesi(); });
  $("file-dbtr").addEventListener("change", (e) => { if (e.target.files.length) leggiFile(e.target.files); e.target.value = ""; });
  // trascina qui (07/11/2026 sera): file e cartelle senza la finestra di sistema per sfogliare
  async function daVoce(voce, percorso = "") {
    if (!voce) return [];
    if (voce.isFile) return [await new Promise((ok, no) => voce.file((f) => ok(percorso ? new File([f], f.name, { type: f.type }) : f), no))];
    if (!voce.isDirectory) return [];
    const r = voce.createReader(), tutte = [];
    for (;;) { const parte = await new Promise((ok, no) => r.readEntries(ok, no)); if (!parte.length) break; tutte.push(...parte); }
    return (await Promise.all(tutte.map((x) => daVoce(x, `${percorso}${voce.name}/`)))).flat();
  }
  const zona = $("trascina-dbtr");
  if (zona) {
    ["dragenter", "dragover"].forEach((t) => zona.addEventListener(t, (e) => { e.preventDefault(); e.dataTransfer.dropEffect = "copy"; zona.classList.add("sopra"); }));
    ["dragleave", "dragend"].forEach((t) => zona.addEventListener(t, () => zona.classList.remove("sopra")));
    zona.addEventListener("drop", async (e) => {
      e.preventDefault(); zona.classList.remove("sopra");
      const voci = [...(e.dataTransfer.items || [])].map((i) => (i.webkitGetAsEntry ? i.webkitGetAsEntry() : null)).filter(Boolean);
      let files = [];
      try { files = voci.length ? (await Promise.all(voci.map((v) => daVoce(v)))).flat() : [...e.dataTransfer.files]; }
      catch { files = [...e.dataTransfer.files]; }
      if (files.length) leggiFile(files); else messaggio("messaggio", "Non ho ricevuto nessun file: trascina lo zip, il GeoPackage o la cartella.", "errore");
    });
  }
  // un file lasciato fuori dalla zona non deve aprire il file nella scheda (si perderebbe la pagina)
  ["dragover", "drop"].forEach((t) => window.addEventListener(t, (e) => { if (!zona || !zona.contains(e.target)) e.preventDefault(); }));
  $("apri-3d").addEventListener("click", apri3d);
  $("togli-locale").addEventListener("click", togliLocale);
  $("consenso").addEventListener("change", aggiornaProponi);
  $("proponi").addEventListener("click", proponi);
  const q = new URLSearchParams(location.search);
  if (REGIONI[q.get("regione")]) $("regione").value = q.get("regione");
  comuni();
  mostraProposte();
})();
