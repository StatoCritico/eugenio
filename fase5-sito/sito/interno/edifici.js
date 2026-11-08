"use strict";
// Pagina interna dello stato della pipeline degli edifici (fase 10, Fase C): legge /api/interno/edifici/stato
// (Cloudflare Access + JWT verificato dall'api) e mostra zone, tessere, notti, errori, disco e fonti (sola lettura); dal
// 07/11/2026 anche la coda «Aggiungi DBTR» (/api/interno/dbtr/coda) con anteprima sull'ortofoto, Approva e Rifiuta.
(function () {
  const $ = (id) => document.getElementById(id);
  const fmt = (v, d = 0) => (v === null || v === undefined || !Number.isFinite(+v) ? "—" : (+v).toLocaleString("it-IT", { maximumFractionDigits: d, minimumFractionDigits: d }));
  const data = (s) => { if (!s) return "—"; const d = new Date(s); return Number.isNaN(+d) ? String(s) : d.toLocaleString("it-IT", { dateStyle: "short", timeStyle: "short" }); };
  function h(tag, cls, testo) { const e = document.createElement(tag); if (cls) e.className = cls; if (testo !== undefined && testo !== null) e.textContent = String(testo); return e; }
  function tabella(intest, righe, numeriche = []) {
    const w = h("div", "tabella-scorre"), t = h("table"), r1 = t.createTHead().insertRow();
    intest.forEach((x, k) => r1.appendChild(h("th", numeriche.includes(k) ? "num" : null, x)));
    const b = t.createTBody();
    righe.forEach((r) => { const tr = b.insertRow(); r.forEach((c, k) => tr.appendChild(h("td", numeriche.includes(k) ? "num" : null, c))); });
    w.appendChild(t); return w;
  }
  const STATI = [["fatta", "s-fatta", "fatte"], ["errore", "s-errore", "con errore (da riprovare)"], ["saltata", "s-saltata", "saltate"],
    ["senza rilievo", "s-senza", "senza rilievo"], ["da fare", "s-dafare", "da fare"]];

  // frase dello stato della zona: quella del server (situazione, dal 05/11/2026, coerente con l'ultima notte); con un'api
  // più vecchia si ricava qui con la stessa regola
  function testoSituazione(z) {
    if (z.situazione && z.situazione.testo) {
      return z.situazione.stato === "completata" && z.completata ? `Zona completata il ${data(z.completata)}.` : z.situazione.testo;
    }
    const dsm = (z.fonti || []).some((f) => (f.tipo === "dsm" || f.tipo === "las") && f.stato === "attiva");
    const m = [];
    if (!dsm) m.push("nessuna fonte DSM o LAS attiva");
    if (!z.corpi || !z.totale_tessere) m.push(`${z.corpi || 0} corpi della Fase A (manca prepara)`);
    if (m.length) return `In attesa: ${m.join(" e ")}.`;
    return z.completata ? `Zona completata il ${data(z.completata)}.` : "Zona in corso.";
  }

  function zona(z) {
    const s = h("section", "zona");
    const t = h("h2", null, z.nome || z.zona); if (z.prova) t.appendChild(h("span", "prova", "prova"));
    s.appendChild(t);
    const c = z.conteggi || {}, tot = z.totale_tessere || 0;
    const fatte = (c.fatta || 0) + (c["senza rilievo"] || 0) + (c.saltata || 0);
    s.appendChild(h("p", null, `${fmt(fatte)} tessere su ${fmt(tot)} completate (${tot ? fmt(100 * fatte / tot) : 0} %), ${fmt(z.corpi)} corpi della Fase A nella zona. `
      + testoSituazione(z) + ` Ultimo aggiornamento: ${data(z.aggiornato)}.`));
    const barra = h("div", "barra"); barra.setAttribute("role", "img");
    barra.setAttribute("aria-label", STATI.map(([k, , n]) => `${c[k] || 0} ${n}`).join(", "));
    STATI.forEach(([k, cls]) => { if (c[k] && tot) { const i = h("i", cls); i.style.width = `${100 * c[k] / tot}%`; barra.appendChild(i); } });
    s.appendChild(barra);
    const leg = h("p", "legenda-barra");
    STATI.forEach(([k, cls, n]) => { const sp = h("span"); sp.appendChild(h("i", cls)); sp.append(`${n}: ${fmt(c[k] || 0)}`); leg.appendChild(sp); });
    s.appendChild(leg);
    const q = Object.entries(z.qualita || {});
    if (q.length) { s.appendChild(h("h3", null, "Esiti per qualità (corpi)")); s.appendChild(tabella(["Esito", "Corpi"], q.sort((a, b) => b[1] - a[1]).map(([k, v]) => [k, fmt(v)]), [1])); }
    s.appendChild(h("h3", null, "Coda"));
    s.appendChild(h("p", null, z.prossime && z.prossime.length ? `Prossime tessere: ${z.prossime.join(", ")}.` : "Nessuna tessera in coda."));
    if (z.saltate && z.saltate.length) s.appendChild(h("p", "errore", `Tessere saltate dopo troppi tentativi: ${z.saltate.join(", ")}.`));
    const e = (z.esecuzioni || []).slice().reverse();
    s.appendChild(h("h3", null, `Ultime ${e.length} notti`));
    s.appendChild(tabella(["Inizio", "Fine", "Esito", "Motivo", "Tessere fatte", "Errori", "Corpi", "Scaricati (MB)"],
      e.map((x) => [data(x.inizio), data(x.fine), x.esito || "—", x.motivo || "", fmt(x.tessere_fatte), fmt(x.tessere_errore), fmt(x.corpi), fmt((x.byte || 0) / 1048576, 1)]), [4, 5, 6, 7]));
    const er = (z.errori || []).slice().reverse();
    s.appendChild(h("h3", null, "Errori"));
    s.appendChild(er.length ? tabella(["Quando", "Tessera", "Tentativo", "Errore"], er.map((x) => [data(x.quando), x.tessera, fmt(x.tentativo), x.errore]), [2])
      : h("p", null, "Nessun errore."));
    s.appendChild(h("h3", null, "Fonti"));
    const ft = tabella(["Fonte", "Tipo", "Stato", "Licenza", "Motivo", "Ultima verifica"], (z.fonti || []).map((f) => [f.descrizione || f.id, f.tipo, f.stato,
      `${f.licenza || "—"}${f.licenza_confermata ? "" : " (da confermare)"}`, f.stato === "attiva" ? "" : (f.motivo || ""), f.verifica || ""]));
    ft.querySelectorAll("tbody tr").forEach((tr) => { const td = tr.children[2]; td.className = `stato-fonte ${td.textContent === "attiva" ? "attiva" : "attesa"}`; });
    s.appendChild(ft);
    const ts = Object.entries(z.tessere || {}).filter(([, v]) => v.stato === "fatta").slice(-40).reverse();
    if (ts.length) {
      s.appendChild(h("h3", null, "Ultime tessere elaborate"));
      s.appendChild(tabella(["Tessera", "Fonte", "Fatta", "Corpi", "Falde", "Secondi", "Scaricati (MB)", "Restano (kB)"],
        ts.map(([k, v]) => [k, v.fonte || "—", data(v.fatta), fmt(v.corpi), fmt(v.falde), fmt(v.secondi, 1), fmt((v.byte_scaricati || 0) / 1048576, 1), fmt((v.byte_prodotti || 0) / 1024)]), [3, 4, 5, 6, 7]));
    }
    return s;
  }

  async function carica() {
    const m = $("messaggio");
    try {
      const r = await fetch("/api/interno/edifici/stato", { credentials: "same-origin", cache: "no-store" });
      if (!r.ok) {
        let d = ""; try { d = (await r.json()).detail || ""; } catch { /* testo semplice */ }
        throw new Error(r.status === 403 ? "accesso riservato (serve l'accesso di Cloudflare)" : d || `HTTP ${r.status}`);
      }
      const d = await r.json();
      m.textContent = d.zone.length ? "" : "La pipeline non ha ancora scritto nessuno stato.";
      m.classList.remove("errore");
      $("utente").textContent = d.utente ? `Accesso: ${d.utente}.` : "";
      $("generato").textContent = data(d.generato);
      const sd = $("schede-disco"); sd.innerHTML = "";
      Object.entries(d.disco || {}).forEach(([k, v]) => {
        const c = h("div", "scheda"); c.appendChild(h("span", null, k === "dati" ? "Disco dei dati" : "Archivio degli edifici"));
        c.appendChild(h("b", null, `${fmt(v.libero_gb, 1)} GB liberi`)); c.appendChild(h("small", null, `su ${fmt(v.totale_gb, 0)} GB (usati ${fmt(v.usato_gb, 1)})`));
        sd.appendChild(c);
      });
      $("disco").hidden = !Object.keys(d.disco || {}).length;
      const zz = $("zone"); zz.innerHTML = "";
      d.zone.forEach((z) => zz.appendChild(zona(z)));
    } catch (e) {
      m.textContent = `Stato non disponibile: ${e.message || e}`; m.classList.add("errore");
    }
  }
  // ------------------------------------------------------------------ coda «Aggiungi DBTR» (07/11/2026)
  const coda = { voci: [], scelta: null, mappa: null, fonti: [] };
  const MB = (b) => fmt((b || 0) / 1048576, 1);
  const classeStato = (s) => (s === "in attesa di approvazione" ? "attesa" : s === "controlli non superati" ? "ko" : "lavoro");
  async function api(url, metodo = "GET") {
    const r = await fetch(url, { method: metodo, credentials: "same-origin", cache: "no-store",
      headers: metodo === "GET" ? {} : { "X-EuGEnio-Interno": "1" } });
    let d = null; try { d = await r.json(); } catch { d = null; }
    if (!r.ok) throw new Error(r.status === 403 ? "accesso riservato" : (d && d.detail) || `HTTP ${r.status}`);
    return d;
  }
  async function caricaCoda() {
    const m = $("messaggio-coda");
    try {
      const d = await api("/api/interno/dbtr/coda");
      coda.voci = d.coda || [];
      m.textContent = (coda.voci.length ? `${coda.voci.length} proposte in coda` : "Nessuna proposta in coda")
        + `; spazio occupato ${fmt(d.occupato_mb, 1)} MB; limiti: ${fmt(d.limiti.max_mb)} MB per file, ${d.limiti.al_giorno_per_ip} file al giorno per IP`
        + `${d.attiva ? "" : "; proposte SPENTE (DBTR_CODA=false)"}.`;
      m.classList.remove("errore");
      const t = tabella(["Creata", "Comune", "Regione", "Formato", "MB", "Stato", "Corpi", "Gronda mediana / p95 / max (m)", "Convenzione", "Scartati"],
        coda.voci.map((v) => { const e = v.esito || {}, g = e.gronda_m || {};
          return [data(v.creata), `${v.comune}${v.intero ? " (comune intero)" : " (parte)"}`, v.regione, v.formato, MB(v.dimensione), v.stato,
            fmt(e.corpi), e.corpi ? `${fmt(g.mediana, 1)} / ${fmt(g.p95, 1)} / ${fmt(g.max, 1)}` : "—", e.convenzione || "—", fmt(e.scartati)]; }), [4, 6, 9]);
      t.querySelectorAll("tbody tr").forEach((tr, i) => {
        tr.style.cursor = "pointer"; tr.tabIndex = 0;
        tr.children[5].className = `stato-coda ${classeStato(coda.voci[i].stato)}`;
        const apri = () => dettaglio(coda.voci[i].id);
        tr.addEventListener("click", apri); tr.addEventListener("keydown", (ev) => { if (ev.key === "Enter") apri(); });
        if (coda.voci[i].id === coda.scelta) tr.classList.add("scelta");
      });
      $("tabella-coda").innerHTML = "";
      // coda vuota (07/11/2026 sera): niente tabella vuota, una frase chiara
      if (coda.voci.length) $("tabella-coda").appendChild(t);
      else $("tabella-coda").appendChild(h("p", "coda-vuota", "Nessuna proposta in coda. Le proposte arrivano solo quando qualcuno, nella pagina "
        + "«Aggiungi edifici (DB topografico)», spunta il consenso e preme «Invia il file»; la sola lettura nel browser non manda nulla."));
      const st = d.storico || [];
      $("storico-coda").innerHTML = "";
      if (st.length) {
        $("storico-coda").appendChild(h("h3", null, "Ultime decisioni"));
        $("storico-coda").appendChild(tabella(["Data", "Comune", "Regione", "Esito", "Corpi"], st.map((x) => [data(x.data), x.comune, x.regione, x.stato, fmt(x.corpi)]), [4]));
      }
      if (coda.scelta && !coda.voci.some((v) => v.id === coda.scelta)) { coda.scelta = null; $("dettaglio-coda").hidden = true; }
    } catch (e) { m.textContent = `Coda non disponibile: ${e.message || e}`; m.classList.add("errore"); }
  }
  function elenco(cls, righe) { const ul = h("ul", cls); righe.forEach((x) => ul.appendChild(h("li", null, x))); return ul; }
  async function dettaglio(id) {
    const v = coda.voci.find((x) => x.id === id); if (!v) return;
    coda.scelta = id;
    document.querySelectorAll("#tabella-coda tbody tr").forEach((tr, i) => tr.classList.toggle("scelta", coda.voci[i].id === id));
    $("dettaglio-coda").hidden = false;
    $("titolo-dettaglio").textContent = `${v.comune} (${v.regione}${v.istat ? `, ISTAT ${v.istat}` : ""}) – ${v.stato}`;
    const box = $("esito-coda"); box.innerHTML = "";
    const c = v.controlli || {}, e = v.esito || {};
    const righe = [["File", `${v.formato}, ${MB(v.dimensione)} MB, ricevuto ${data(v.ricevuto)}; strato letto ${(c.sorgente || {}).nome || "—"} (${c.crs ? String(c.crs).slice(0, 40) : "sistema ?"})`],
      ["Riquadro", c.riquadro ? `${c.riquadro.join(", ")} ${c.dentro_regione === false ? "(FUORI dalla regione)" : "(dentro la regione)"}` : "—"],
      ["Metadati della Regione", c.metadati ? `${c.metadati.file} file XML; regione citata: ${c.metadati.regione_citata ? "sì" : "no"}; licenze: ${(c.metadati.licenze || []).join(", ") || "—"}` : "—"],
      ["Comuni catastali", (c.comuni_catastali || []).join(", ") || "—"],
      ["Corpi", e.corpi ? `${fmt(e.corpi)} di ${fmt(e.edifici)} edifici; letti ${fmt(e.letti)}, scartati ${fmt(e.scartati)}` : "—"],
      ["Altezze", e.gronda_m ? `mediana ${fmt(e.gronda_m.mediana, 1)} m, p95 ${fmt(e.gronda_m.p95, 1)} m, max ${fmt(e.gronda_m.max, 1)} m; sotto 2 m ${fmt(e.gronda_m.sotto_2m)}, oltre 60 m ${fmt(e.gronda_m.oltre_60m)}` : "—"],
      ["Convenzione", e.convenzione || "—"], ["A capanna / con cortile", e.corpi ? `${fmt(e.a_capanna)} / ${fmt(e.con_cortile)}` : "—"],
      ["Foglio e numero / destinazione", e.corpi ? `${fmt(e.con_foglio_numero)} / ${fmt(e.con_destinazione)}` : "—"],
      ["Terreno", e.corpi ? (e.dtm ? "DTM del server" : "base del DB topografico (nessun DTM)") : "—"],
      ["Destinazione", e.percorso ? `${e.percorso}${e.sostituisce ? " (SOSTITUISCE l'archivio attuale: copia in _precedenti/)" : " (nuovo)"}` : "—"],
      ["Preparazione", v.secondi ? `${fmt(v.secondi, 1)} s` : "—"]];
    box.appendChild(tabella(["Voce", "Valore"], righe));
    if ((c.problemi || []).length) { box.appendChild(h("h3", null, "Problemi")); box.appendChild(elenco("problemi", c.problemi)); }
    const anom = (c.avvisi || []).concat(e.anomalie || [], (c.dati_personali || []).map((x) => `dati personali? ${x}`));
    if (anom.length) { box.appendChild(h("h3", null, "Anomalie e avvisi")); box.appendChild(elenco("anomalie", anom)); }
    if (e.altezze_stimate) box.appendChild(h("p", null, `${e.altezze_stimate} corpi con altezza del DBTR non plausibile portati alla stima (regola di plausibilità, 07/11/2026).`));
    if ((e.sospetti || []).length) box.appendChild(tabella(["Corpo sospetto", "m²", "Gronda (m)", "Foglio", "Numero"], e.sospetti.map((x) => [x.id, fmt(x.area, 1), fmt(x.gronda, 1), x.foglio || "—", x.numero || "—"]), [1, 2]));
    $("approva").disabled = v.stato !== "in attesa di approvazione";
    $("rifiuta").disabled = ["in preparazione", "approvato"].includes(v.stato);
    $("registro").href = `/api/interno/dbtr/${id}/registro`;
    await anteprima(v);
  }
  const COLORI = ["interpolate", ["linear"], ["coalesce", ["get", "g"], 0], 3, "#ffffb2", 9, "#fecc5c", 15, "#fd8d3c", 25, "#f03b20", 40, "#bd0026"];
  async function mappaCoda() {
    if (coda.mappa || !window.maplibregl) return coda.mappa;
    const m = new window.maplibregl.Map({ container: "mappa-coda", center: [12, 44.3], zoom: 7, maxZoom: 20, attributionControl: false,
      style: { version: 8, sources: {}, layers: [{ id: "sfondo", type: "background", paint: { "background-color": "#ddd" } }] } });
    m.addControl(new window.maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.addControl(new window.maplibregl.AttributionControl({ compact: true }), "bottom-right");
    await new Promise((ok) => m.on("load", ok));
    m.addSource("corpi", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    m.addLayer({ id: "corpi", type: "fill", source: "corpi", paint: { "fill-color": COLORI, "fill-opacity": 0.75 } });
    m.addLayer({ id: "corpi-linea", type: "line", source: "corpi", minzoom: 15, paint: { "line-color": "#222", "line-width": 0.5 } });
    m.on("click", "corpi", (ev) => { const p = ev.features[0].properties;
      new window.maplibregl.Popup().setLngLat(ev.lngLat).setText(`gronda ${fmt(p.g, 1)} m${p.c ? `, colmo ${fmt(p.c, 1)} m` : ""}`).addTo(m); });
    try { const r = await fetch("/api/ortofoto/fonti"); if (r.ok) coda.fonti = ((await r.json()).fonti || []).filter((f) => f.tessere && f.copia); } catch { /* senza ortofoto */ }
    coda.mappa = m;
    return m;
  }
  async function anteprima(v) {
    const m = await mappaCoda(); if (!m) return;
    let d = { type: "FeatureCollection", features: [] };
    if (v.anteprima) { try { d = await api(`/api/interno/dbtr/${v.id}/anteprima`); } catch { /* niente anteprima */ } }
    m.getSource("corpi").setData(d);
    $("legenda-coda").textContent = d.features.length ? `Anteprima: ${fmt(d.features.length)} corpi${d.passo > 1 ? ` (uno ogni ${d.passo} di ${fmt(d.totale)})` : ""}, colorati per gronda: giallo chiaro 3 m, arancio 15 m, rosso 25 m, rosso scuro 40 m e oltre.`
      : "Anteprima non ancora pronta (la prepara il servizio edifici-coda).";
    const r = (v.esito && v.esito.riquadro) || (v.controlli && v.controlli.riquadro);
    if (!r) return;
    m.fitBounds([[r[0], r[1]], [r[2], r[3]]], { padding: 20, duration: 0 });
    const c = [(r[0] + r[2]) / 2, (r[1] + r[3]) / 2];
    const f = coda.fonti.find((x) => c[0] >= x.riquadro[0] && c[0] <= x.riquadro[2] && c[1] >= x.riquadro[1] && c[1] <= x.riquadro[3]);
    if (m.getLayer("orto")) m.removeLayer("orto");
    if (m.getSource("orto")) m.removeSource("orto");
    if (f) { m.addSource("orto", { type: "raster", tiles: [location.origin + f.tessere], tileSize: 256, minzoom: f.zoom[0], maxzoom: f.zoom[1], attribution: f.citazione });
      m.addLayer({ id: "orto", type: "raster", source: "orto" }, "corpi"); }
  }
  async function decidi(azione) {
    const v = coda.voci.find((x) => x.id === coda.scelta); if (!v) return;
    const testo = azione === "approva" ? `Approvare ${v.comune}? L'archivio entra in ${(v.esito || {}).percorso || "cc-by/…"}${(v.esito || {}).sostituisce ? " al posto di quello attuale" : ""}.`
      : `Rifiutare ${v.comune}? Il file viene cancellato.`;
    if (!window.confirm(testo)) return;
    try { const d = await api(`/api/interno/dbtr/${v.id}/${azione}`, "POST"); $("messaggio-coda").textContent = d.messaggio; }
    catch (e) { $("messaggio-coda").textContent = `Non riuscito: ${e.message || e}`; }
    await caricaCoda();
    if (coda.scelta) dettaglio(coda.scelta);
  }
  $("approva").addEventListener("click", () => decidi("approva"));
  $("rifiuta").addEventListener("click", () => decidi("rifiuta"));
  window.EUGENIO_INTERNO = { coda, caricaCoda, dettaglio };

  $("ricarica").addEventListener("click", () => { carica(); caricaCoda(); });
  carica();
  caricaCoda();
})();
