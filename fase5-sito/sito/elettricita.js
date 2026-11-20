"use strict";
// Statistiche › «Produzione e consumi di elettricità» (elettricita.html, 20/11/2026, richiesta di Paolo).
// Mappa MapLibre dell'Italia con le regioni bianche e, in ogni regione, un istogramma (barre verticali affiancate, una per
// fonte o settore, scalate sul valore più alto fra tutte le regioni e tutti gli anni della grandezza scelta). Un clic su
// una regione (nella mappa grande o nella piccola) la sceglie: la mappa si avvicina e gli istogrammi passano alle
// province; un secondo clic torna all'Italia. Sotto la mappa il selettore (capacità, produzione, richiesta, consumi,
// burden sharing) e il cursore dell'anno. A destra il grafico cumulato (Italia o regione, anno per anno), le barre delle
// province nell'anno scelto e la tabella dei valori con i totali.
// Burden sharing: per ogni regione due barre orizzontali, l'obiettivo 2030 del DM 21/6/2024 (Tabella A, con il segno
// dell'obiettivo dell'anno scelto) e la potenza rinnovabile in più rispetto al 2020, colorata per fonte.
// Dati: dati/elettricita/italia.json e RR.json (fase 15, costruiti dal worker con le statistiche di Terna).
// Decisione di Paolo (20/11/2026): i dati non si scaricano; si scarica solo l'immagine della mappa (esporta_mappa.js).
// Gli istogrammi sono immagini della mappa (addImage + strato di simboli), così finiscono anche nell'immagine scaricata.
(function () {
  const $ = (id) => document.getElementById(id);
  const box = $("mappa-elettricita");
  const C = window.EUGENIO_CONFINI, R = window.EUGENIO_RETE, G = window.EUGENIO_GRAFICI;
  if (!box || !window.maplibregl || !C) return;
  const E = window.EUGENIO;
  const V = (document.currentScript && /[?&]v=([\w-]+)/.exec(document.currentScript.src) || [])[1] || "";
  const conV = (u) => (V ? `${u}?v=${V}` : u);
  const NS = "http://www.w3.org/2000/svg";
  const vuota = () => ({ type: "FeatureCollection", features: [] });
  const css = (n, r = "#888") => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || r;
  function h(tag, cls, t) { const e = document.createElement(tag); if (cls) e.className = cls; if (t !== undefined && t !== null) e.textContent = t; return e; }
  function s(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if ((k === "fill" || k === "stroke") && typeof v === "string" && v.startsWith("var(")) e.style.setProperty(k, v); else e.setAttribute(k, v);
    }
    if (parent) parent.appendChild(e);
    return e;
  }
  // numeri all'italiana, sempre con il punto delle migliaia (anche a 4 cifre: 4.063): modulo comune numeri.js
  const num = (v, d = 0) => EUGENIO_NUMERI.formato(v, d);
  const dec = (v) => (Math.abs(v) >= 100 ? 0 : 1);
  function messaggio(id, t, errore = false) { const m = $(id); if (!m) return; m.textContent = t; m.classList.toggle("errore", errore); }

  const MODI = {
    capacita: { nome: "Capacità installata", breve: "capacità", grandezza: "capacita" },
    produzione: { nome: "Produzione", breve: "produzione", grandezza: "produzione" },
    richiesta: { nome: "Carichi (richiesta per regione)", breve: "richiesta", grandezza: "richiesta" },
    consumi: { nome: "Consumi per settore", breve: "consumi", grandezza: "consumi" },
    burden: { nome: "Burden sharing 2030", breve: "burden sharing", grandezza: "capacita" },
  };
  const st = { mappa: null, it: null, prov: new Map(), modo: "capacita", anno: null, regione: null, giro: 0, img: new Set(), sugg: null };
  const D = () => st.it;
  const voci = (g) => D().voci[g];
  const unita = (g) => D().unita[g];
  const anniDi = (modo) => (modo === "burden" ? D().anni.capacita.filter((a) => a >= 2021) : D().anni[MODI[modo].grandezza]);
  const valori = (x, g, a) => (x && x[g] && x[g][String(a)]) || null;
  const somma = (arr) => (arr || []).reduce((t, v) => t + v, 0);

  // ------------------------------------------------------------------ dati
  async function carica(u) { const r = await fetch(conV(u)); if (!r.ok) throw new Error(`${u}: ${r.status}`); return r.json(); }
  async function province(cod) {
    if (!st.prov.has(cod)) st.prov.set(cod, carica(`dati/elettricita/${cod}.json`));
    return st.prov.get(cod);
  }
  // FER in più rispetto al 2020 (MW), per fonte rinnovabile: [{id, v}], v ≥ 0 per le barre; netto = somma con i segni
  function aggiunta(x, a) {
    const ids = D().voci.capacita.map((v) => v.id), base = valori(x, "capacita", D().obiettivi_base), ora = valori(x, "capacita", a);
    if (!base || !ora) return null;
    const parti = D().fer.map((id) => { const i = ids.indexOf(id); return { id, v: ora[i] - base[i] }; });
    return { parti, netto: somma(parti.map((p) => p.v)) };
  }
  const obiettivo = (x, a) => { const o = x && x.obiettivi; if (!o) return null; const i = D().obiettivi_anni.indexOf(a); return i >= 0 ? o[i] : null; };
  const colore = (g, id) => (voci(g).find((v) => v.id === id) || {}).colore || "#999";

  // ------------------------------------------------------------------ istogrammi come immagini della mappa
  const PR = Math.min(2, window.devicePixelRatio || 1);
  function tela(w, hgt) { const c = document.createElement("canvas"); c.width = Math.round(w * PR); c.height = Math.round(hgt * PR); const k = c.getContext("2d"); k.scale(PR, PR); return [c, k]; }
  function barreVerticali(vals, colori, max, alto, neg) {
    // barre affiancate: base in basso (o al centro per i valori negativi della richiesta), contorno scuro sottile
    const n = vals.length, lb = st.regione ? 8 : 6, gap = 1, W = n * (lb + gap) + 3, Hneg = neg ? Math.round(alto * 0.3) : 0, Ht = alto + Hneg + 2;
    const [c, k] = tela(W, Ht);
    const y0 = alto + 1;
    vals.forEach((v, i) => {
      if (!v) return;
      const hh = Math.max(1, Math.abs(v) / max * alto) * (v < 0 ? Math.min(1, Hneg / alto) : 1);
      const x = 2 + i * (lb + gap);
      k.fillStyle = colori[i];
      if (v > 0) k.fillRect(x, y0 - hh, lb, hh); else k.fillRect(x, y0, lb, Math.min(hh, Hneg));
      k.strokeStyle = "rgba(0,0,0,0.55)"; k.lineWidth = 0.6;
      if (v > 0) k.strokeRect(x + 0.3, y0 - hh + 0.3, lb - 0.6, hh - 0.6); else k.strokeRect(x + 0.3, y0 + 0.3, lb - 0.6, Math.min(hh, Hneg) - 0.6);
    });
    k.strokeStyle = "#222"; k.lineWidth = 1; k.beginPath(); k.moveTo(0, y0 + 0.5); k.lineTo(W, y0 + 0.5); k.stroke();
    return { c, ancora: neg ? [0, (Ht / 2 - y0) / Ht] : null };
  }
  function barreBurden(parti, ob2030, obAnno, max, largo) {
    const W = largo + 4, Ht = 18, [c, k] = tela(W, Ht), sc = (v) => Math.max(0, v) / max * largo;
    // obiettivo 2030: barra grigia chiara con il bordo
    k.fillStyle = "#d9d9d9"; k.fillRect(2, 2, sc(ob2030), 6);
    k.strokeStyle = "#555"; k.lineWidth = 0.8; k.strokeRect(2.4, 2.4, Math.max(0, sc(ob2030) - 0.8), 5.2);
    if (obAnno !== null) { k.fillStyle = "#111"; k.fillRect(2 + sc(obAnno) - 0.8, 0.5, 1.6, 9); }
    // installato dal 2021, per fonte
    let x = 2;
    for (const p of parti) { if (p.v <= 0) continue; const w = sc(p.v); k.fillStyle = colore("capacita", p.id); k.fillRect(x, 10, w, 6); x += w; }
    k.strokeStyle = "#333"; k.lineWidth = 0.6; k.strokeRect(2.3, 10.3, Math.max(0, x - 2.6), 5.4);
    if (obAnno !== null) { k.fillStyle = "#111"; k.fillRect(2 + sc(obAnno) - 0.8, 9, 1.6, 8.5); }
    return { c };
  }
  function immagine(id, disegno) {
    const m = st.mappa, k = disegno.c.getContext("2d"), dati = k.getImageData(0, 0, disegno.c.width, disegno.c.height);
    if (m.hasImage(id)) m.removeImage(id);
    m.addImage(id, { width: disegno.c.width, height: disegno.c.height, data: dati.data }, { pixelRatio: PR });
    st.img.add(id);
  }

  // max delle barre: fra tutte le unità (regioni o province della regione) e tutti gli anni della grandezza
  function massimo(unita, modo) {
    let mx = 0;
    if (modo === "burden") {
      for (const x of unita) {
        if (x.obiettivi) mx = Math.max(mx, x.obiettivi[x.obiettivi.length - 1]);
        for (const a of anniDi("burden")) { const ag = aggiunta(x, a); if (ag) mx = Math.max(mx, somma(ag.parti.map((p) => Math.max(0, p.v)))); }
      }
      return mx || 1;
    }
    const g = MODI[modo].grandezza;
    for (const x of unita) for (const v of Object.values(x[g] || {})) for (const y of v) mx = Math.max(mx, Math.abs(y));
    return mx || 1;
  }

  async function disegnaBarre() {
    const m = st.mappa, mio = ++st.giro;
    let unitaMappa = D().regioni;
    if (st.regione) {
      const p = await province(st.regione);
      if (mio !== st.giro) return;
      unitaMappa = p.province;
    }
    const modo = st.modo, g = MODI[modo].grandezza, a = st.anno;
    const max = massimo(unitaMappa, modo), features = [];
    const alto = st.regione ? 90 : 70;
    const neg = g === "richiesta";
    for (const x of unitaMappa) {
      const id = `el-${x.cod || x.nome}`.replace(/[^\w-]/g, "_");
      let dis = null;
      if (modo === "burden") {
        const ag = aggiunta(x, a);
        if (ag) dis = barreBurden(ag.parti, x.obiettivi ? x.obiettivi[x.obiettivi.length - 1] : 0, obiettivo(x, a), max, st.regione ? 110 : 80);
      } else {
        const v = valori(x, g, a);
        if (v && somma(v.map(Math.abs)) > 0) dis = barreVerticali(v, voci(g).map((q) => q.colore), max, alto, neg);
      }
      if (!dis) continue;
      immagine(id, dis);
      features.push({ type: "Feature", geometry: { type: "Point", coordinates: [x.lon, x.lat] },
        properties: { img: id, nome: x.nome, cod: x.cod || "", storica: !!x.storica, burden: modo === "burden", neg } });
    }
    // regione con la richiesta solo regionale: le province non hanno dati
    if (st.regione && g === "richiesta") messaggio("messaggio-mappa", "Terna pubblica la richiesta di energia solo per regione: le province non hanno barre.");
    else messaggio("messaggio-mappa", "");
    m.getSource("el-barre").setData({ type: "FeatureCollection", features });
    st.barre = features.length;
    m.setLayoutProperty("el-barre", "icon-anchor", modo === "burden" ? "center" : neg ? "center" : "bottom");
    legenda();
    chiudiAttribuzione();
  }
  // attribuzione compatta chiusa (le fonti complete sono sotto la mappa), come in Stato della rete elettrica
  function chiudiAttribuzione() {
    const t = () => box.querySelectorAll(".maplibregl-compact-show").forEach((x) => x.classList.remove("maplibregl-compact-show"));
    t(); st.mappa.once("idle", t);
  }

  // ------------------------------------------------------------------ mappa
  async function avvio() {
    try { st.it = await carica("dati/elettricita/italia.json"); } catch (e) {
      messaggio("messaggio-mappa", "I dati di Terna non sono ancora disponibili su questo server (li prepara il worker una volta al mese).", true);
      return;
    }
    preparaComandi();
    const m = new window.maplibregl.Map({ container: box, center: [12.4, 42.1], zoom: 4.9, maxZoom: 12, minZoom: 4, attributionControl: false,
      canvasContextAttributes: { preserveDrawingBuffer: true },
      style: { version: 8, sources: {}, layers: [{ id: "sfondo", type: "background", paint: { "background-color": css("--carta", "#f4f4f4") } }] } });
    st.mappa = m;
    window.EUGENIO_ELETTRICITA = { stato: st, scegliRegione, togliRegione, cambiaModo };   // per le prove
    m.addControl(new window.maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.addControl(new window.maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    m.addControl(new window.maplibregl.AttributionControl({ compact: true }), "bottom-right");
    await new Promise((ok) => m.on("load", ok));
    document.addEventListener("eugenio:ridimensiona", () => m.resize());
    try { await C.aggiungi(m, { clic: false }); } catch { messaggio("messaggio-mappa", "Confini non disponibili.", true); }
    const prima = m.getLayer("confini-comuni-clic") ? "confini-comuni-clic" : undefined;
    // (20/11/2026, Paolo) regioni bianche: i colori sono quelli delle barre
    m.addLayer({ id: "el-fondo", type: "fill", source: "confini-regioni", paint: { "fill-color": "#ffffff", "fill-opacity": 1 } }, prima);
    m.addSource("el-province", { type: "geojson", data: vuota() });
    m.addLayer({ id: "el-province-clic", type: "fill", source: "el-province", paint: { "fill-color": "#000", "fill-opacity": 0 } });
    m.addLayer({ id: "el-province-linee", type: "line", source: "el-province", paint: { "line-color": "#555", "line-width": 0.8 } });
    m.addSource("el-barre", { type: "geojson", data: vuota(), attribution: "Terna S.p.A. (dati statistici); elaborazione EuGEnio" });
    m.addLayer({ id: "el-barre", type: "symbol", source: "el-barre", layout: { "icon-image": ["get", "img"], "icon-allow-overlap": true,
      "icon-ignore-placement": true, "icon-anchor": "bottom" } });
    if (m.getLayer("confini-regioni-clic")) m.setLayerZoomRange("confini-regioni-clic", 0, 24);
    if (R && R.suggerimento) st.sugg = R.suggerimento(m, () => ["el-barre", "el-province-clic", "confini-regioni-clic"], suggerimento);
    m.on("click", clic);
    for (const id of ["strato-barre", "strato-fondo", "strato-ortofoto"]) $(id).addEventListener("change", strati);
    if (window.EUGENIO_RIGHELLO) window.EUGENIO_RIGHELLO.aggiungi(m, { dove: $("strati-elettricita") });
    ortofoto(m);
    if (window.EUGENIO_ESPORTA) window.EUGENIO_ESPORTA.pulsanti($("scarica-mappa"), m, opzioniImmagine, $("messaggio-immagine"));
    if (E) {
      E.suRegione = (cod) => scegliRegione(cod);
      E.suStessaRegione = (cod) => (st.regione === cod ? togliRegione() : scegliRegione(cod));
      if (E.evidenziaPiccola) E.evidenziaPiccola(null);
    }
    strati();
    const q = new URLSearchParams(location.search);
    if (q.get("modo") && MODI[q.get("modo")]) cambiaModo(q.get("modo"), false);
    if (/^\d\d$/.test(q.get("regione") || "") && q.get("vista") !== "italia" && D().regioni.some((r) => r.cod === q.get("regione"))) await scegliRegione(q.get("regione"));
    else { await disegnaBarre(); pannello(); }
    st.pronto = true;
    document.addEventListener("eugenio:aspetto", () => { m.setPaintProperty("sfondo", "background-color", css("--carta", "#f4f4f4")); pannello(); });
  }

  function strati() {
    const m = st.mappa, vis = (id, on) => { if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", on ? "visible" : "none"); };
    vis("el-barre", $("strato-barre").checked);
    vis("el-fondo", $("strato-fondo").checked);
    ["contesto", "ortofoto"].forEach((id) => vis(id, $("strato-ortofoto").checked));
    if ($("strato-ortofoto").checked && orto.fonti.length) sceltaOrto();
    attribuzioneOrto();
    legenda();
  }

  function clic(e) {
    const m = st.mappa;
    const r = m.queryRenderedFeatures(e.point, { layers: ["confini-regioni-clic"].filter((id) => m.getLayer(id)) })[0];
    const cod = r ? r.properties.cod : null;
    if (!cod) return;
    if (st.regione === cod) togliRegione(); else scegliRegione(cod);
  }

  async function scegliRegione(cod) {
    if (!D().regioni.some((r) => r.cod === cod)) return;
    st.regione = cod;
    if (E && E.seleziona) E.seleziona(cod);
    const m = st.mappa;
    if (m.getLayer("confini-regione-scelta")) m.setFilter("confini-regione-scelta", ["==", ["get", "cod"], cod]);
    const b = await C.riquadroRegione(cod);
    if (b && st.regione === cod) m.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 30, duration: 600 });
    try { m.getSource("el-province").setData(await C.provinceRegione(cod)); } catch { m.getSource("el-province").setData(vuota()); }
    aggiornaIndirizzo();
    await disegnaBarre();
    pannello();
  }
  async function togliRegione() {
    st.regione = null;
    if (E && E.evidenziaPiccola) E.evidenziaPiccola(null);
    const m = st.mappa;
    if (m.getLayer("confini-regione-scelta")) m.setFilter("confini-regione-scelta", ["==", ["get", "cod"], ""]);
    m.getSource("el-province").setData(vuota());
    m.fitBounds([[C.ITALIA[0], C.ITALIA[1]], [C.ITALIA[2], C.ITALIA[3]]], { padding: 10, duration: 600 });
    aggiornaIndirizzo();
    await disegnaBarre();
    pannello();
  }
  function aggiornaIndirizzo() {
    const u = new URL(location.href);
    if (st.regione) { u.searchParams.set("regione", st.regione); u.searchParams.delete("vista"); } else { u.searchParams.delete("regione"); u.searchParams.set("vista", "italia"); }
    u.searchParams.set("modo", st.modo);
    history.replaceState(null, "", u);
  }

  function suggerimento(f) {
    const p = f.properties || {}, id = f.layer.id;
    let x = null;
    if (st.regione) {
      if (id === "confini-regioni-clic" && p.cod !== st.regione) x = D().regioni.find((r) => r.cod === p.cod);
      else if (cacheProv && cacheProv.cod === st.regione && (id === "el-barre" || id === "el-province-clic"))
        x = cacheProv.province.find((q) => (p.cod && q.cod === p.cod) || q.nome === p.nome) || null;
    } else if (id === "el-barre" || id === "confini-regioni-clic") x = D().regioni.find((r) => r.cod === p.cod);
    if (!x) return null;
    const righe = righeValori(x);
    if (!st.regione) righe.push([null, "clic per le province"]);
    else if (D().regioni.includes(x)) righe.push([null, "clic per scegliere questa regione"]);
    return { titolo: `${x.nome}${x.storica ? " (provincia soppressa)" : ""} – ${st.anno}`, righe, cursore: true };
  }
  let cacheProv = null;
  function righeValori(x) {
    const a = st.anno;
    if (st.modo === "burden") {
      const ag = aggiunta(x, a), ob = obiettivo(x, a), ob30 = x.obiettivi ? x.obiettivi[x.obiettivi.length - 1] : null;
      if (!ag) return ["nessun dato"];
      const r = [];
      if (ob30 !== null) r.push(["#d9d9d9", `obiettivo 2030: ${num(ob30)} MW`]);
      if (ob !== null) r.push(["#111", `obiettivo ${a}: ${num(ob)} MW`]);
      r.push([null, `rinnovabili in più dal 2020: ${num(ag.netto)} MW${ob ? ` (${num(100 * ag.netto / ob)} % dell'obiettivo ${a})` : ""}`]);
      ag.parti.forEach((q) => r.push([colore("capacita", q.id), `${voci("capacita").find((v) => v.id === q.id).nome}: ${num(q.v, dec(q.v))} MW`]));
      return r;
    }
    const g = MODI[st.modo].grandezza, v = valori(x, g, a);
    if (!v) return ["nessun dato per quest'anno"];
    const r = voci(g).map((q, i) => [q.colore, `${q.nome}: ${num(v[i], dec(v[i]))} ${unita(g)}`]).filter((_, i) => v[i]);
    r.push([null, `Totale: ${num(somma(v), 0)} ${unita(g)}`]);
    return r;
  }

  // ------------------------------------------------------------------ comandi
  function preparaComandi() {
    document.querySelectorAll("#modo-elettricita [data-modo]").forEach((b) => b.addEventListener("click", () => cambiaModo(b.dataset.modo, true)));
    const cur = $("anno-elettricita");
    cur.addEventListener("input", () => { st.anno = anniDi(st.modo)[+cur.value]; $("anno-scelto").textContent = String(st.anno); });
    cur.addEventListener("change", async () => { await disegnaBarre(); pannello(); });
    $("torna-italia").addEventListener("click", () => togliRegione());
    cambiaModo("capacita", false);
  }
  // collegamento a questa simulazione (20/11/2026): regione, vista e modo li scrive già aggiornaIndirizzo(); qui l'anno
  // (l'anno vero, non la posizione del cursore) e, con data-collegamento, le caselle barre, fondo e ortofoto
  if (window.EUGENIO_COLLEGAMENTO) window.EUGENIO_COLLEGAMENTO.registra({
    regione: false,                    // la regione la decide la pagina (assente con vista=italia)
    chiavi: ["modo", "anno"],
    pronto: () => st.pronto,
    leggi: () => (st.pronto ? { modo: st.modo, anno: st.anno } : null),
    async applica(p) {
      const a = +p.get("anno"), anni = anniDi(st.modo);
      if (!a || !anni.includes(a) || a === st.anno) return;
      st.anno = a;
      $("anno-elettricita").value = anni.indexOf(a);
      $("anno-scelto").textContent = String(a);
      await disegnaBarre(); pannello();
    },
  });

  function cambiaModo(modo, ridisegna) {
    st.modo = modo;
    document.querySelectorAll("#modo-elettricita [data-modo]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.modo === modo)));
    const anni = anniDi(modo), cur = $("anno-elettricita");
    // anno predefinito: l'ultimo con i dati (per il burden sharing l'anno corrente, se Terna lo ha già pubblicato)
    if (!st.anno || !anni.includes(st.anno) || modo === "burden") st.anno = anni[anni.length - 1];
    cur.min = 0; cur.max = anni.length - 1; cur.value = anni.indexOf(st.anno);
    $("anno-min").textContent = anni[0]; $("anno-max").textContent = anni[anni.length - 1]; $("anno-scelto").textContent = String(st.anno);
    if (ridisegna && st.mappa) { aggiornaIndirizzo(); disegnaBarre().then(pannello); }
  }

  // ------------------------------------------------------------------ legenda e immagine
  function voceLegenda(L, colore, testo, bordo) {
    const sp = h("span"), i = h("i");
    i.style.background = colore; if (bordo) i.style.outline = "1px solid #555";
    sp.append(i, testo); L.appendChild(sp);
  }
  function legenda() {
    const L = $("legenda-elettricita"); if (!L || !D()) return;
    L.innerHTML = "";
    if (st.modo === "burden") {
      voceLegenda(L, "#d9d9d9", "obiettivo 2030 (DM 21/6/2024, Tabella A)", true);
      voceLegenda(L, "#111", `segno: obiettivo del ${st.anno}`);
      D().fer.forEach((id) => voceLegenda(L, colore("capacita", id), `${voci("capacita").find((v) => v.id === id).nome} in più dal 2020`));
      L.appendChild(h("span", "legenda-nota", "Barre in scala con l'obiettivo 2030 più grande. La potenza in più è una stima: variazione della potenza efficiente lorda rinnovabile di Terna rispetto al 2020."));
      return;
    }
    const g = MODI[st.modo].grandezza;
    voci(g).forEach((v) => voceLegenda(L, v.colore, v.nome));
    L.appendChild(h("span", "legenda-nota", `Barre in ${unita(g)}, in scala con il valore più alto fra ${st.regione ? "le province della regione" : "tutte le regioni"} in tutti gli anni${g === "richiesta" ? "; sotto la linea i valori negativi (saldo esportato, pompaggi)" : ""}.`));
  }
  function opzioniImmagine() {
    if (!D()) return "Dati non ancora caricati.";
    const ro = righeOrto();
    if (ro === null) return `«${orto.fonte.nome}» è solo in consultazione dal vivo: per scaricare l'immagine spegni la casella «Ortofoto».`;
    const nomeReg = st.regione ? D().regioni.find((r) => r.cod === st.regione).nome : "Italia";
    const g = MODI[st.modo].grandezza;
    const leg = st.modo === "burden"
      ? `Barra grigia: obiettivo 2030 di potenza rinnovabile aggiuntiva rispetto al 2020 (${D().obiettivi_fonte}); segno nero: obiettivo del ${st.anno}; barra colorata: potenza rinnovabile in più rispetto al 2020 per fonte (${D().fer.map((id) => voci("capacita").find((v) => v.id === id).nome.toLowerCase()).join(", ")}), stima EuGEnio dalla potenza efficiente lorda di Terna.`
      : `Barre (${unita(g)}), da sinistra: ${voci(g).map((v) => v.nome.toLowerCase()).join(", ")}; scala comune a ${st.regione ? "tutte le province della regione" : "tutte le regioni"} e a tutti gli anni.`;
    const righe = [leg, `Dati: ${D().fonte}.`, ...ro, C.ATTRIBUZIONE];
    const nome = `elettricita_${st.modo}_${st.anno}_${nomeReg.toLowerCase().replace(/[^a-z0-9]+/g, "_")}`;
    return { titolo: `${MODI[st.modo].nome} – ${nomeReg} – ${st.anno}`, righe, nome };
  }

  // ------------------------------------------------------------------ pannello di destra
  async function pannello() {
    if (!D()) return;
    const g = MODI[st.modo].grandezza, reg = st.regione ? D().regioni.find((r) => r.cod === st.regione) : null;
    $("titolo-vista").textContent = reg ? reg.nome : "Italia";
    $("torna-italia").style.display = reg ? "" : "none";
    $("titolo-andamento").textContent = st.modo === "burden" ? `Rinnovabili in più rispetto al 2020 e obiettivi – ${reg ? reg.nome : "Italia"}`
      : `${MODI[st.modo].nome} – ${reg ? reg.nome : "Italia"}, anno per anno`;
    // serie dell'unità scelta: Italia = somma delle regioni
    const tot = reg || totaleItalia();
    G.registra($("grafico-andamento"), (dest, mis) => (st.modo === "burden" ? graficoBurden(dest, mis, tot) : graficoAndamento(dest, mis, tot, g)),
      { titolo: $("titolo-andamento").textContent, adatta: true });
    let elenco = D().regioni, totale = totaleItalia(), tipo = "regioni";
    const scheda = $("blocco-province");
    if (reg) {
      const p = await province(reg.cod);
      cacheProv = { cod: reg.cod, province: p.province };
      elenco = p.province; totale = reg; tipo = "province";
    }
    const senzaProv = reg && g === "richiesta";
    scheda.hidden = !reg || senzaProv;
    if (reg && !senzaProv) {
      $("titolo-province").textContent = st.modo === "burden" ? `Rinnovabili in più rispetto al 2020 per provincia – ${st.anno}` : `${MODI[st.modo].nome} per provincia – ${st.anno}`;
      G.registra($("grafico-province"), (dest, mis) => graficoUnita(dest, mis, elenco.filter((x) => (st.modo === "burden" ? aggiunta(x, st.anno) : valori(x, g, st.anno))), g),
        { titolo: $("titolo-province").textContent, adatta: true });
    }
    $("nota-province").hidden = !senzaProv;
    tabella(senzaProv ? [] : elenco, totale, tipo, reg);
  }
  function totaleItalia() {
    const out = { nome: "Italia", obiettivi: null };
    for (const g of Object.keys(D().voci)) {
      out[g] = {};
      for (const a of D().anni[g]) {
        let acc = null;
        for (const r of D().regioni) { const v = valori(r, g, a); if (v) acc = acc ? acc.map((x, i) => x + v[i]) : [...v]; }
        if (acc) out[g][String(a)] = acc;
      }
    }
    out.obiettivi = D().regioni.reduce((t, r) => (r.obiettivi ? t.map((x, i) => x + r.obiettivi[i]) : t), D().obiettivi_anni.map(() => 0));
    return out;
  }

  // assi e griglia comuni
  function scala(max) {
    const p = 10 ** Math.floor(Math.log10(max || 1)), passi = [1, 2, 2.5, 5, 10].map((k) => k * p);
    const passo = passi.find((k) => max / k <= 5) || p * 10;
    return { passo, top: Math.ceil(max / passo) * passo || 1 };
  }
  function asseY(svg, sx, su, gi, W, H, min, max, unitaTesto) {
    const Y = (v) => su + (H - su - gi) * (max - v) / (max - min || 1);
    const { passo } = scala(Math.max(Math.abs(max), Math.abs(min)));
    for (let v = Math.ceil(min / passo) * passo; v <= max + 1e-9; v += passo) {
      s("line", { x1: sx, x2: W - 6, y1: Y(v), y2: Y(v), stroke: v === 0 ? "var(--inchiostro)" : "var(--linea)", "stroke-width": v === 0 ? 1 : 0.6 }, svg);
      const t = s("text", { x: sx - 4, y: Y(v) + 4, "text-anchor": "end", "font-size": 11, fill: "var(--tenue)" }, svg); t.textContent = num(v);
    }
    const t = s("text", { x: 4, y: 11, "font-size": 11, fill: "var(--tenue)" }, svg); t.textContent = unitaTesto;
    return Y;
  }
  function legendaHtml(dest, elementi) {
    const L = h("div", "legenda legenda-grafico");
    elementi.forEach(([c, t]) => voceLegenda(L, c, t));
    dest.appendChild(L);
  }
  function graficoAndamento(dest, mis, x, g) {
    const W = mis && mis.larghezza ? mis.larghezza : 560, H = mis && mis.riquadro ? mis.altezza : 260;
    const anni = D().anni[g].filter((a) => valori(x, g, a));
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": $("titolo-andamento").textContent }, dest);
    const sx = 56, gi = 22, su = 16;
    let max = 0, min = 0;
    for (const a of anni) { const v = valori(x, g, a); max = Math.max(max, somma(v.filter((y) => y > 0))); min = Math.min(min, somma(v.filter((y) => y < 0))); }
    const sc = scala(max), top = sc.top, bot = min < 0 ? -scala(-min).top : 0;
    const Y = asseY(svg, sx, su, gi, W, H, bot, top, unita(g));
    const passo = (W - sx - 8) / Math.max(1, anni.length), lb = Math.max(2, passo * 0.72);
    const punti = anni.map((a, i) => {
      const v = valori(x, g, a), cx = sx + passo * (i + 0.5), el = [];
      let su0 = 0, giu0 = 0;
      voci(g).forEach((q, j) => {
        const y = v[j]; if (!y) return;
        const da = y > 0 ? su0 : giu0, a2 = da + y;
        const r = s("rect", { x: cx - lb / 2, y: Math.min(Y(da), Y(a2)), width: lb, height: Math.abs(Y(da) - Y(a2)), fill: q.colore }, svg);
        el.push(r); if (y > 0) su0 = a2; else giu0 = a2;
      });
      const ogni = anni.length <= 14 ? 1 : Math.ceil(anni.length / 12);
      if (a === st.anno || ((i % ogni === 0) && Math.abs(a - st.anno) >= ogni)) {
        const t = s("text", { x: cx, y: H - 6, "text-anchor": "middle", "font-size": 11, fill: a === st.anno ? "var(--inchiostro)" : "var(--tenue)", "font-weight": a === st.anno ? 700 : 400 }, svg);
        t.textContent = String(a);
      }
      if (a === st.anno) s("rect", { x: cx - passo / 2, y: su, width: passo, height: H - su - gi, fill: "none", stroke: "var(--primario)", "stroke-width": 1.2 }, svg);
      return { x: cx, titolo: String(a), elementi: el, righe: [...voci(g).map((q, j) => [q.colore, `${q.nome}: ${num(v[j], dec(v[j]))} ${unita(g)}`]).filter((_, j) => v[j]),
        [null, `Totale: ${num(somma(v))} ${unita(g)}`]] };
    });
    G.osserva(svg, punti, { area: [sx, su, W - 8, H - gi], guida: false });
    legendaHtml(dest, voci(g).filter((q, j) => anni.some((a) => valori(x, g, a)[j])).map((q) => [q.colore, q.nome]));
  }
  function graficoBurden(dest, mis, x) {
    const W = mis && mis.larghezza ? mis.larghezza : 560, H = mis && mis.riquadro ? mis.altezza : 260;
    const anniOb = D().obiettivi_anni, anniDati = anniDi("burden");
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": $("titolo-andamento").textContent }, dest);
    const sx = 56, gi = 22, su = 16;
    let max = x.obiettivi ? Math.max(...x.obiettivi) : 0;
    for (const a of anniDati) { const ag = aggiunta(x, a); if (ag) max = Math.max(max, somma(ag.parti.map((p) => Math.max(0, p.v)))); }
    let min = 0;
    for (const a of anniDati) { const ag = aggiunta(x, a); if (ag) min = Math.min(min, somma(ag.parti.map((p) => Math.min(0, p.v)))); }
    const Y = asseY(svg, sx, su, gi, W, H, min < 0 ? -scala(-min).top : 0, scala(max).top, "MW");
    const passo = (W - sx - 8) / anniOb.length, lb = passo * 0.6;
    const linea = [];
    const punti = anniOb.map((a, i) => {
      const cx = sx + passo * (i + 0.5), el = [], righe = [];
      const ag = aggiunta(x, a);
      if (ag) {
        let su0 = 0, giu0 = 0;
        ag.parti.forEach((p) => {
          if (!p.v) return;
          const da = p.v > 0 ? su0 : giu0, a2 = da + p.v;
          el.push(s("rect", { x: cx - lb / 2, y: Math.min(Y(da), Y(a2)), width: lb, height: Math.abs(Y(da) - Y(a2)), fill: colore("capacita", p.id) }, svg));
          if (p.v > 0) su0 = a2; else giu0 = a2;
          righe.push([colore("capacita", p.id), `${voci("capacita").find((v) => v.id === p.id).nome}: ${num(p.v, dec(p.v))} MW`]);
        });
        righe.unshift([null, `In più dal 2020: ${num(ag.netto)} MW`]);
      }
      const ob = x.obiettivi ? x.obiettivi[i] : null;
      if (ob !== null) { linea.push([cx, Y(ob)]); righe.unshift(["#111", `Obiettivo: ${num(ob)} MW${ag ? ` (raggiunto ${num(100 * ag.netto / ob)} %)` : ""}`]); }
      const t = s("text", { x: cx, y: H - 6, "text-anchor": "middle", "font-size": 11, fill: a === st.anno ? "var(--inchiostro)" : "var(--tenue)", "font-weight": a === st.anno ? 700 : 400 }, svg);
      t.textContent = String(a);
      if (a === st.anno) s("rect", { x: cx - passo / 2, y: su, width: passo, height: H - su - gi, fill: "none", stroke: "var(--primario)", "stroke-width": 1.2 }, svg);
      return { x: cx, titolo: String(a), elementi: el, righe, segni: ob !== null ? [[cx, Y(ob), "#111"]] : [] };
    });
    if (linea.length) s("polyline", { points: linea.map((p) => p.join(",")).join(" "), fill: "none", stroke: "var(--inchiostro)", "stroke-width": 2, "stroke-dasharray": "5 3" }, svg);
    linea.forEach(([cx, cy]) => s("circle", { cx, cy, r: 2.8, fill: "var(--inchiostro)" }, svg));
    G.osserva(svg, punti, { area: [sx, su, W - 8, H - gi], guida: false });
    legendaHtml(dest, [[css("--inchiostro", "#111"), x.obiettivi ? "obiettivo (DM 21/6/2024, Tabella A)" : "nessun obiettivo per le province"],
      ...D().fer.map((id) => [colore("capacita", id), voci("capacita").find((v) => v.id === id).nome])]);
  }
  // barre impilate per provincia nell'anno scelto
  function graficoUnita(dest, mis, elenco, g) {
    const W = mis && mis.larghezza ? mis.larghezza : 560, H = mis && mis.riquadro ? mis.altezza : 240, a = st.anno;
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": $("titolo-province").textContent }, dest);
    const sx = 56, gi = 34, su = 16;
    const burden = st.modo === "burden";
    const parti = (x) => (burden ? (aggiunta(x, a) || { parti: [] }).parti.map((p) => ({ v: p.v, c: colore("capacita", p.id), n: voci("capacita").find((v) => v.id === p.id).nome }))
      : (valori(x, g, a) || []).map((v, j) => ({ v, c: voci(g)[j].colore, n: voci(g)[j].nome })));
    let max = 0, min = 0;
    elenco.forEach((x) => { const p = parti(x); max = Math.max(max, somma(p.map((q) => Math.max(0, q.v)))); min = Math.min(min, somma(p.map((q) => Math.min(0, q.v)))); });
    const Y = asseY(svg, sx, su, gi, W, H, min < 0 ? -scala(-min).top : 0, scala(max).top, burden ? "MW" : unita(g));
    const passo = (W - sx - 8) / Math.max(1, elenco.length), lb = Math.min(36, passo * 0.7);
    const punti = elenco.map((x, i) => {
      const cx = sx + passo * (i + 0.5), el = [], p = parti(x);
      let su0 = 0, giu0 = 0;
      p.forEach((q) => { if (!q.v) return; const da = q.v > 0 ? su0 : giu0, a2 = da + q.v;
        el.push(s("rect", { x: cx - lb / 2, y: Math.min(Y(da), Y(a2)), width: lb, height: Math.abs(Y(da) - Y(a2)), fill: q.c }, svg));
        if (q.v > 0) su0 = a2; else giu0 = a2; });
      const t = s("text", { x: cx, y: H - gi + 14, "text-anchor": "middle", "font-size": 11, fill: "var(--tenue)" }, svg);
      t.textContent = x.sigla || x.nome.slice(0, 3);
      return { x: cx, titolo: `${x.nome}${x.storica ? " (provincia soppressa)" : ""}`, elementi: el,
        righe: [...p.filter((q) => q.v).map((q) => [q.c, `${q.n}: ${num(q.v, dec(q.v))} ${burden ? "MW" : unita(g)}`]), [null, `Totale: ${num(somma(p.map((q) => q.v)))} ${burden ? "MW" : unita(g)}`]] };
    });
    G.osserva(svg, punti, { area: [sx, su, W - 8, H - gi], guida: false });
  }

  function tabella(elenco, totale, tipo, reg) {
    const dove = $("tabella-elettricita"); dove.innerHTML = "";
    const g = MODI[st.modo].grandezza, a = st.anno;
    $("titolo-tabella").textContent = `${st.modo === "burden" ? "Burden sharing" : MODI[st.modo].nome} – ${a} – ${reg ? `province di ${reg.nome}` : "regioni"}`;
    const t = h("table", "tabella-valori tabella-elettricita"), th = h("thead"), tb = h("tbody"), tf = h("tfoot");
    const trh = h("tr"); trh.appendChild(h("th", null, tipo === "province" ? "Provincia" : "Regione"));
    let colonne;
    if (st.modo === "burden") colonne = [`Obiettivo ${a} (MW)`, "Obiettivo 2030 (MW)", ...D().fer.map((id) => `${voci("capacita").find((v) => v.id === id).nome} (MW)`), "In più dal 2020 (MW)", `% obiettivo ${a}`, "% obiettivo 2030"];
    else colonne = [...voci(g).map((v) => `${v.nome} (${unita(g)})`), `Totale (${unita(g)})`];
    colonne.forEach((c) => trh.appendChild(h("th", null, c)));
    th.appendChild(trh);
    const riga = (x, dove2, nome) => {
      const tr = h("tr"); tr.appendChild(h("th", null, nome || `${x.nome}${x.storica ? " (soppressa)" : ""}`));
      let celle;
      if (st.modo === "burden") {
        const ag = aggiunta(x, a), ob = obiettivo(x, a), ob30 = x.obiettivi ? x.obiettivi[x.obiettivi.length - 1] : null;
        celle = [ob, ob30, ...(ag ? ag.parti.map((p) => p.v) : D().fer.map(() => null)), ag ? ag.netto : null,
          ag && ob ? 100 * ag.netto / ob : null, ag && ob30 ? 100 * ag.netto / ob30 : null];
        celle = celle.map((v, i) => num(v, i >= celle.length - 2 ? 0 : dec(v || 0)) + (i >= celle.length - 2 && v !== null ? " %" : ""));
      } else {
        const v = valori(x, g, a);
        celle = v ? [...v.map((y) => num(y, dec(y))), num(somma(v))] : colonne.map(() => "–");
      }
      celle.forEach((c) => tr.appendChild(h("td", null, c)));
      dove2.appendChild(tr);
    };
    [...elenco].sort((p, q) => p.nome.localeCompare(q.nome, "it")).forEach((x) => riga(x, tb));
    riga(totale, tf, tipo === "province" ? `Totale ${reg.nome}` : "Italia");
    t.append(th, tb, tf);
    const sc = h("div", "tabella-scorre"); sc.dataset.titolo = $("titolo-tabella").textContent; sc.appendChild(t);
    dove.appendChild(sc);
    if (tipo === "province" && elenco.some((x) => x.storica)) dove.appendChild(h("p", "aiuto", "Le province soppresse (Sardegna) compaiono con i nomi usati da Terna negli anni in cui esistevano; nella mappa le loro barre stanno in una posizione indicativa."));
  }

  // ------------------------------------------------------------------ ortofoto (spenta in partenza: le regioni sono bianche)
  const CONTESTO = "s2cloudless2016";
  const orto = { fonti: [], fonte: null, contesto: null, giro: 0 };
  const primoSopra = (m) => { const l = m.getStyle().layers.find((x) => !["sfondo", "contesto", "ortofoto"].includes(x.id)); return l ? l.id : undefined; };
  const sorgenteOrto = (f) => ({ type: "raster", tiles: [location.origin + f.tessere], tileSize: 256, minzoom: f.zoom[0], maxzoom: f.zoom[1],
    ...(Array.isArray(f.riquadro) && f.riquadro.length === 4 ? { bounds: f.riquadro } : {}), attribution: f.citazione });
  const citOrto = (f) => (window.EUGENIO_ORTOFOTO_ANNI && st.mappa ? window.EUGENIO_ORTOFOTO_ANNI.citazione(f, st.mappa) : f.citazione);
  async function ortofoto(m) {
    try {
      const r = await fetch("/api/ortofoto/fonti");
      if (!r.ok || !/json/.test(r.headers.get("Content-Type") || "")) throw new Error(String(r.status));
      orto.fonti = ((await r.json()).fonti || []).filter((f) => f && f.tessere && Array.isArray(f.zoom) && !f.pmtiles);
    } catch { orto.fonti = []; return; }
    orto.contesto = orto.fonti.find((f) => f.id === CONTESTO) || null;
    if (orto.contesto) {
      m.addSource("contesto", sorgenteOrto(orto.contesto));
      m.addLayer({ id: "contesto", type: "raster", source: "contesto", layout: { visibility: $("strato-ortofoto").checked ? "visible" : "none" } }, primoSopra(m));
    }
    m.on("moveend", () => { if ($("strato-ortofoto").checked) sceltaOrto(); });
    if ($("strato-ortofoto").checked) await sceltaOrto();
    attribuzioneOrto();
  }
  async function sceltaOrto() {
    const m = st.mappa, mio = ++orto.giro, c = m.getCenter();
    let qui;
    try { qui = C.fontiNelPunto ? await C.fontiNelPunto(orto.fonti, c.lng, c.lat) : orto.fonti; } catch { qui = orto.fonti; }
    if (mio !== orto.giro) return;
    const f = qui.find((x) => x.id !== CONTESTO) || null;
    if ((f ? f.id : "") === (orto.fonte ? orto.fonte.id : "") && (!f || m.getSource("ortofoto"))) { attribuzioneOrto(); return; }
    if (m.getLayer("ortofoto")) m.removeLayer("ortofoto");
    if (m.getSource("ortofoto")) m.removeSource("ortofoto");
    orto.fonte = f;
    if (f) {
      m.addSource("ortofoto", sorgenteOrto(f));
      m.addLayer({ id: "ortofoto", type: "raster", source: "ortofoto", layout: { visibility: $("strato-ortofoto").checked ? "visible" : "none" } }, primoSopra(m));
    }
    attribuzioneOrto();
  }
  function attribuzioneOrto() {
    const a = $("attribuzione-ortofoto");
    if (!a) return;
    a.hidden = !$("strato-ortofoto").checked || !orto.fonti.length;
    if (a.hidden) return;
    a.innerHTML = "";
    const f = orto.fonte, z = st.mappa ? st.mappa.getZoom() : 0, parti = [];
    if (f) parti.push([`Ortofoto: ${citOrto(f)} – licenza `, f.licenza, f.scheda, f.zoom[0] > z ? ` (si vede dallo zoom ${f.zoom[0]}: avvicinati)` : ""]);
    if (orto.contesto) parti.push([`${f ? "Da lontano, contesto" : "Contesto"}: ${orto.contesto.citazione} – licenza `, orto.contesto.licenza, orto.contesto.scheda, ""]);
    parti.forEach(([t, lic, url, dopo], i) => { if (i) a.append(" "); a.append(t); const l = h("a", null, lic); if (url) l.href = url; a.append(l, `${dopo}.`); });
    if (!parti.length) a.textContent = "Nessuna ortofoto disponibile qui.";
    if ($("strato-fondo").checked) a.append(" Le regioni bianche coprono l'ortofoto: spegni «Regioni bianche» per vederla.");
  }
  function righeOrto() {
    if (!$("strato-ortofoto").checked || !orto.fonti.length) return [];
    const f = orto.fonte, r = [];
    if (f && !f.copia) return null;
    if (f) r.push(`Ortofoto: ${citOrto(f)} – licenza ${f.licenza} (${f.scheda}).`);
    if (orto.contesto) r.push(`Contesto: ${orto.contesto.citazione} – licenza ${orto.contesto.licenza} (${orto.contesto.scheda}).`);
    return r;
  }

  avvio().catch((e) => messaggio("messaggio-mappa", `Errore nella mappa: ${e.message}`, true));
})();
