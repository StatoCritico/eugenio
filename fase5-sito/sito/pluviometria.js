"use strict";
// Clima e meteo › «Dati pluviometrici» (pluviometria.html, 22/11/2026, richiesta di Paolo).
//
// Solo il «Merging» del Dipartimento della Protezione Civile (radar corretto con i pluviometri, CUM3/6/12/24, un dato ogni
// 30 minuti), a fini statistici e non di allerta: niente radar puro, niente bollettini, niente avvisi (decisioni di Paolo del
// 22/11/2026). Licenza CC BY-SA 4.0, scritta sotto la mappa, nelle immagini e nei file.
//
// Mappa (MapLibre) con tre strati accendibili: pioggia misurata (immagini del worker, pioggia_gl.js), interruzioni della
// rete elettrica nel periodo (/api/rete/interruzioni/periodo, e-distribuzione), ortofoto sotto (spenta in partenza, come
// nelle altre pagine: contesto Sentinel-2 e fonte migliore della zona); righello; confini ISTAT.
// Animazione (richiesta di Paolo): «Durata» 3, 6, 12, 24 ore o 7 giorni; «Passo» 3 ore, 6 ore, 12 ore o 1 giorno, scelto da
// solo con la durata (fino a 24 ore: 3 ore; 7 giorni: 1 giorno) e modificabile (mai più lungo della durata); cursore «Fine
// del periodo» negli ultimi 7 giorni, a passi del passo scelto; «Secondi per passo» (predefinito 0,7); «Avvia» ripete il
// periodo finché non si ferma. Ogni immagine è la pioggia caduta nel passo che finisce a quell'ora (prodotto CUM<passo>).
// A destra: date di aggiornamento (dati/radar/indice.json); clic sulla mappa o ricerca (cerca_luogo.js): pioggia delle
// ultime 3/6/12/24 ore nel punto (/api/radar/punto) e serie giornaliera degli ultimi 30 giorni del comune, misurata e
// prevista (/api/radar/comune/<istat>), con grafico e tabella; download CSV, Excel e PDF (rete.js) con fonti e licenze.
(function () {
  const $ = (id) => document.getElementById(id);
  const box = $("mappa-pioggia");
  const G = window.EUGENIO_PIOGGIA, C = window.EUGENIO_CONFINI, R = window.EUGENIO_RETE;
  if (!box || !window.maplibregl || !G || !C || !R) return;
  const st = { mappa: null, ind: null, pioggia: null, fini: [], frames: [], i: 0, timer: 0, gioca: false, punto: null,
    valori: null, comune: null, serie: null, inter: null, interChiave: "", pronto: false, giroPunto: 0 };
  const vuota = () => ({ type: "FeatureCollection", features: [] });
  const colore = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || "#888";
  function h(tag, cls, t) { const e = document.createElement(tag); if (cls) e.className = cls; if (t !== undefined && t !== null) e.textContent = t; return e; }
  function messaggio(id, t, errore = false) { const m = $(id); if (!m) return; m.textContent = t; m.classList.toggle("errore", errore); }
  const mm = (x) => (x === null || x === undefined || !Number.isFinite(+x) ? "–" : `${R.num(+x, +x < 10 ? 1 : 0)} mm`);
  const ORA = 3600 * 1000;
  const acceso = (id) => !!($(id) && $(id).checked);
  const durata = () => +$("durata").value;
  const passo = () => +$("passo").value;
  const prodotto = () => `CUM${passo()}`;

  // ------------------------------------------------------------------ durata, passo, cursore
  // passo predefinito per la durata (richiesta di Paolo: da 3 ore a 1 giorno); i passi più lunghi della durata si spengono
  const passoAuto = (d) => (d >= 168 ? 24 : 3);
  function passiPossibili(auto) {
    const d = durata(), sel = $("passo");
    for (const o of sel.options) o.disabled = +o.value > d;
    if (auto || +sel.value > d) sel.value = String(passoAuto(d));
  }
  function aggiornaFini(tieniFine = true) {
    const vecchio = st.fini[+$("fine").value];
    const tutte = (st.ind && st.ind.prodotti[prodotto()] && st.ind.prodotti[prodotto()].frame) || [];
    st.fini = tutte.slice();
    const r = $("fine");
    r.max = String(Math.max(0, st.fini.length - 1));
    let i = st.fini.length - 1;
    if (tieniFine && vecchio) {
      const t = G.data(vecchio).getTime();
      const j = st.fini.findIndex((n) => G.data(n).getTime() >= t);
      if (j >= 0) i = j;
    }
    r.value = String(Math.max(0, i));
    r.disabled = !st.fini.length;
    periodo();
  }
  function periodo() {
    const fine = st.fini[+$("fine").value];
    const testo = $("periodo-testo");
    if (!fine) {
      st.frames = []; testo.textContent = "Nessuna immagine ancora disponibile per questo passo.";
      mostra(-1); return;
    }
    const tf = G.data(fine).getTime(), ti = tf - durata() * ORA;
    st.frames = st.fini.filter((n) => { const t = G.data(n).getTime(); return t > ti && t <= tf; });
    const primo = G.data(st.frames[0]).getTime() - passo() * ORA;
    const manca = durata() / passo() - st.frames.length;
    testo.textContent = `Periodo: dalle ${G.oraIt(new Date(ti))} alle ${G.oraIt(new Date(tf))}, ${st.frames.length} `
      + `${st.frames.length === 1 ? "immagine" : "immagini"} da ${passo() === 24 ? "1 giorno" : `${passo()} ore`}`
      + (manca > 0 ? ` (${manca} senza dato${primo > ti ? ": inizio della raccolta o dato scartato" : ""})` : "") + ".";
    G.precarica(prodotto(), st.frames);
    if (!st.gioca) st.i = st.frames.length - 1;
    else st.i = Math.min(st.i, st.frames.length - 1);
    mostra(st.i);
    caricaInterruzioni();
    if (window.EUGENIO_COLLEGAMENTO) window.EUGENIO_COLLEGAMENTO.aggiorna();
  }
  function mostra(i) {
    const n = st.frames[i];
    if (st.pioggia) st.pioggia.mostra(prodotto(), n || null);
    $("frame-testo").textContent = n ? `${st.frames.length > 1 ? `${i + 1} di ${st.frames.length}: ` : ""}${G.testoFrame(prodotto(), n)}` : "";
    filtraInterruzioni(n);
  }
  function avvia() {
    if (st.gioca) { ferma(); return; }
    if (st.frames.length < 2) { messaggio("messaggio-mappa", "Con questa durata e questo passo c'è una sola immagine: scegli un passo più breve o una durata più lunga."); return; }
    st.gioca = true;
    $("avvia").textContent = "❚❚ Ferma"; $("avvia").setAttribute("aria-pressed", "true");
    const giro = () => {
      if (!st.gioca) return;
      st.i = (st.i + 1) % st.frames.length;
      mostra(st.i);
      st.timer = setTimeout(giro, secondi() * 1000);
    };
    st.i = -1;
    giro();
  }
  function ferma() {
    st.gioca = false; clearTimeout(st.timer);
    $("avvia").textContent = "▶ Avvia"; $("avvia").setAttribute("aria-pressed", "false");
  }
  function secondi() {
    const v = parseFloat(String($("secondi").value).replace(",", "."));
    return Number.isFinite(v) ? Math.min(10, Math.max(0.1, v)) : 0.7;
  }

  // ------------------------------------------------------------------ stato dei dati
  async function caricaIndice() {
    try {
      st.ind = await G.indice(true);
    } catch (e) {
      st.ind = null;
      messaggio("messaggio-stato", `I dati pluviometrici non sono ancora disponibili (${e.message}): riprova più tardi.`, true);
      return false;
    }
    messaggio("messaggio-stato", "");
    const s = st.ind, dl = $("stato-pioggia"); dl.innerHTML = "";
    const riga = (k, v) => dl.append(h("dt", null, k), h("dd", null, v));
    const ult = (s.prodotti.CUM3 && s.prodotti.CUM3.ultimo) || null;
    riga("Ultimo dato", ult ? `pioggia fino alle ${G.oraIt(G.data(ult))} (il DPC lo pubblica ogni 30 minuti)` : "non ancora letto");
    riga("Immagini della mappa", `ultimi ${s.giorni_mappa} giorni, alle ore piene (ogni 3 ore, a mezzanotte per 1 giorno)`);
    if (s.raccolta_dal) riga("Raccolta di EuGEnio", `dal ${R.dataIt(s.raccolta_dal)}; recupero all'indietro fino a circa 5 mesi (quanto tiene il DPC)`);
    riga("Archivio", `mappe per ${s.archivio_anni} anni, valori per comune per sempre`);
    riga("Fonte", `${s.fonte}`);
    return true;
  }

  // ------------------------------------------------------------------ mappa
  async function avvio() {
    passiPossibili(false);
    const m = new window.maplibregl.Map({ container: box, center: [12.4, 42.6], zoom: 5, maxZoom: 14, minZoom: 4.5, attributionControl: false,
      canvasContextAttributes: { preserveDrawingBuffer: true },
      style: { version: 8, sources: {}, layers: [{ id: "sfondo", type: "background", paint: { "background-color": colore("--carta") } }] } });
    st.mappa = m;
    m.addControl(new window.maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.addControl(new window.maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    m.addControl(new window.maplibregl.AttributionControl({ compact: true, customAttribution: G.ATTRIBUZIONE }), "bottom-right");
    await new Promise((ok) => m.on("load", ok));
    box.querySelectorAll(".maplibregl-compact-show").forEach((x) => x.classList.remove("maplibregl-compact-show"));
    document.addEventListener("eugenio:ridimensiona", () => m.resize());
    try { await C.aggiungi(m, { clic: false }); } catch { messaggio("messaggio-mappa", "Confini non disponibili."); }
    const sopra = m.getStyle().layers.find((l) => l.id !== "sfondo");
    st.pioggia = G.strato(m, { id: "pioggia", prima: sopra ? sopra.id : undefined });
    m.addSource("pioggia-int", { type: "geojson", data: vuota(), attribution: "Interruzioni: e-distribuzione" });
    m.addLayer({ id: "pioggia-interruzioni", type: "circle", source: "pioggia-int", layout: { visibility: "none" }, paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 5, 3, 10, 5, 14, 7], "circle-color": "#2f6fdb",
      "circle-stroke-color": "#ffffff", "circle-stroke-width": 1.4 } });
    m.addSource("pioggia-punto", { type: "geojson", data: vuota() });
    m.addLayer({ id: "pioggia-punto", type: "circle", source: "pioggia-punto", paint: {
      "circle-radius": 7, "circle-color": "rgba(0,0,0,0)", "circle-stroke-color": colore("--primario"), "circle-stroke-width": 3 } });
    document.addEventListener("eugenio:aspetto", () => {
      m.setPaintProperty("sfondo", "background-color", colore("--carta"));
      m.setPaintProperty("pioggia-punto", "circle-stroke-color", colore("--primario"));
    });
    if (R.suggerimento) R.suggerimento(m, () => ["pioggia-interruzioni"], suggerimentoInterruzione);
    m.on("click", (e) => { if (!(window.EUGENIO_RIGHELLO && st.righello && st.righello.attivo())) scegliPunto(e.lngLat.lng, e.lngLat.lat); });
    for (const id of ["strato-pioggia", "strato-interruzioni", "strato-ortofoto"]) $(id).addEventListener("change", strati);
    $("durata").addEventListener("change", () => { passiPossibili(true); aggiornaFini(); });
    $("passo").addEventListener("change", () => aggiornaFini());
    $("fine").addEventListener("input", () => periodo());
    $("fine").addEventListener("change", () => { if (window.EUGENIO_COLLEGAMENTO) window.EUGENIO_COLLEGAMENTO.aggiorna(); });
    $("avvia").addEventListener("click", avvia);
    if (window.EUGENIO_RIGHELLO) st.righello = window.EUGENIO_RIGHELLO.aggiungi(m, { dove: $("strati-pioggia") });
    ortofoto(m);
    if (window.EUGENIO_ESPORTA) window.EUGENIO_ESPORTA.pulsanti($("scarica-mappa"), m, opzioniImmagine, $("messaggio-immagine"));
    R.pulsantiDati($("scarica-dati"), datiFile, $("messaggio-dati"));
    if (window.EUGENIO_CERCA) window.EUGENIO_CERCA.crea($("cerca-luogo"), { suTrovato: (lon, lat) => scegliPunto(lon, lat, true) });
    if (await caricaIndice()) {
      await st.pioggia.pronto;
      G.legenda($("legenda-pioggia"), st.ind);
      aggiornaFini(false);
    }
    strati();
    st.pronto = true;
    // nuovo dato ogni 30 minuti: si rilegge l'indice ogni 5 minuti; se il cursore era sull'ultimo, resta sull'ultimo
    setInterval(async () => {
      const allUltimo = +$("fine").value === st.fini.length - 1;
      if (await caricaIndice() && !st.gioca) aggiornaFini(!allUltimo);
    }, 5 * 60 * 1000);
  }

  function strati() {
    const m = st.mappa;
    if (st.pioggia) st.pioggia.visibile(acceso("strato-pioggia"));
    if (m.getLayer("pioggia-interruzioni")) m.setLayoutProperty("pioggia-interruzioni", "visibility", acceso("strato-interruzioni") ? "visible" : "none");
    for (const id of ["contesto", "ortofoto"]) if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", acceso("strato-ortofoto") ? "visible" : "none");
    if (acceso("strato-ortofoto") && orto.fonti.length) sceltaOrto();
    attribuzioneOrto();
    caricaInterruzioni();
  }

  // ------------------------------------------------------------------ interruzioni nel periodo (e-distribuzione)
  async function caricaInterruzioni() {
    if (!acceso("strato-interruzioni") || !st.frames.length) return;
    const tf = G.data(st.frames[st.frames.length - 1]), ti = new Date(tf.getTime() - durata() * ORA);
    const chiave = `${ti.toISOString()}|${tf.toISOString()}`;
    if (chiave === st.interChiave && st.inter) { filtraInterruzioni(st.frames[st.i]); return; }
    st.interChiave = chiave;
    try {
      const j = await R.api(`/api/rete/interruzioni/periodo?da=${encodeURIComponent(ti.toISOString())}&a=${encodeURIComponent(tf.toISOString())}`);
      if (chiave !== st.interChiave) return;
      st.inter = j;
      messaggio("messaggio-mappa", "");
    } catch (e) {
      st.inter = null;
      messaggio("messaggio-mappa", `Interruzioni non disponibili (${e.message}).`, true);
    }
    filtraInterruzioni(st.frames[st.i]);
  }
  // nel frame che finisce a n: interruzioni in corso in qualche momento del passo
  function filtraInterruzioni(n) {
    const s = st.mappa && st.mappa.getSource("pioggia-int");
    if (!s) return;
    if (!st.inter || !n || !acceso("strato-interruzioni")) { s.setData(vuota()); return; }
    const tf = G.data(n).getTime(), ti = tf - passo() * ORA;
    s.setData({ type: "FeatureCollection", features: st.inter.features.filter((f) => {
      const p = f.properties, a = Date.parse(p.inizio), b = Date.parse(p.fine_stimata || p.ultima_lettura || p.inizio);
      return Number.isFinite(a) && a <= tf && (!Number.isFinite(b) || b >= ti);
    }) });
  }
  function suggerimentoInterruzione(f) {
    const p = f.properties, d = h("div");
    d.append(h("b", null, `Interruzione${p.nome_comune ? ` – ${p.nome_comune}` : ""}`), h("br"),
      `${p.causa || ""}${p.clienti ? `, ${R.num(p.clienti)} clienti` : ""}`, h("br"),
      `dalle ${R.oraIt(p.inizio)} alle ${R.oraIt(p.fine_stimata)} (fine stimata)`);
    return d;
  }

  // ------------------------------------------------------------------ punto e comune
  async function scegliPunto(lon, lat, vola = false) {
    const mio = ++st.giroPunto;
    st.punto = { lon, lat };
    st.mappa.getSource("pioggia-punto").setData({ type: "FeatureCollection", features: [{ type: "Feature", geometry: { type: "Point", coordinates: [lon, lat] }, properties: {} }] });
    if (vola) st.mappa.flyTo({ center: [lon, lat], zoom: Math.max(st.mappa.getZoom(), 9), duration: 600 });
    messaggio("messaggio-punto", "Leggo i valori…");
    let v = null, com = null;
    try { v = await R.api(`/api/radar/punto?lat=${lat.toFixed(5)}&lon=${lon.toFixed(5)}`); } catch (e) { messaggio("messaggio-punto", `Valori non disponibili (${e.message}).`, true); }
    try { com = await C.comuneNelPunto(lon, lat); } catch { com = null; }
    if (mio !== st.giroPunto) return;
    st.valori = v;
    const istat = (com && com.istat) || (v && v.comune && v.comune.istat) || null;
    st.comune = istat ? { istat, nome: (com && com.nome) || (v && v.comune && v.comune.nome) || istat } : null;
    schedaPunto();
    st.serie = null;
    $("grafico-giorni").innerHTML = ""; $("tabella-giorni").innerHTML = "";
    if (istat) {
      try { st.serie = await R.api(`/api/radar/comune/${istat}?giorni=30`); } catch (e) { messaggio("messaggio-punto", `Serie del comune non disponibile (${e.message}).`, true); }
      if (mio !== st.giroPunto) return;
      serieComune();
    }
    if (v) messaggio("messaggio-punto", "");
    if (window.EUGENIO_COLLEGAMENTO) window.EUGENIO_COLLEGAMENTO.aggiorna();
  }
  function schedaPunto() {
    const d = $("scheda-punto"); d.innerHTML = "";
    if (!st.punto) return;
    const t = h("h3", null, st.comune ? `${st.comune.nome}` : "Punto scelto");
    d.appendChild(t);
    d.appendChild(h("p", "aiuto", `Punto: ${R.num(st.punto.lat, 4)} N, ${R.num(st.punto.lon, 4)} E.`));
    const val = (st.valori && st.valori.valori) || {};
    const righe = ["CUM3", "CUM6", "CUM12", "CUM24"].filter((p) => val[p]).map((p) => [
      `ultime ${p.slice(3)} ore`, mm(val[p].valore), `fino alle ${G.oraIt(new Date(val[p].fine))}`]);
    if (righe.length) d.appendChild(R.tabella(["Pioggia caduta", "Valore", "Dato"], righe, { titolo: "Pioggia caduta nel punto", num: [1] }));
    else d.appendChild(h("p", "aiuto", "Nessun valore recente nel punto."));
  }
  function serieComune() {
    const s = st.serie;
    if (!s || !s.giornalieri) return;
    const gg = s.giornalieri;
    if (!gg.length) { $("tabella-giorni").appendChild(h("p", "aiuto", "Per questo comune non ci sono ancora giorni completi nell'archivio di EuGEnio.")); return; }
    disegnaGiorni(gg);
    const tot = gg.filter((g) => g.mm !== null).reduce((a, g) => a + g.mm, 0);
    const conPrev = gg.some((g) => g.previsto_mm !== null && g.previsto_mm !== undefined);
    const righe = gg.slice().reverse().map((g) => [R.dataIt(g.data), mm(g.mm), ...(conPrev ? [mm(g.previsto_mm)] : [])]);
    const tit = `Pioggia di ogni giorno – ${s.nome}`;
    $("tabella-giorni").append(h("p", null, `Totale degli ultimi ${gg.length} giorni: ${mm(tot)} (${gg.filter((g) => g.mm !== null).length} giorni con misura).`),
      R.tabella(["Giorno", "Misurata", ...(conPrev ? ["Prevista"] : [])], righe, { titolo: tit, num: conPrev ? [1, 2] : [1] }),
      h("p", "aiuto", s.nota_giornalieri || ""));
  }
  function disegnaGiorni(gg) {
    const boxG = $("grafico-giorni");
    const disegna = (dest, misure) => {
      dest.innerHTML = "";
      const W = misure && misure.riquadro ? misure.larghezza : Math.round(Math.max(320, Math.min(640, (misure && misure.larghezza) || 600)));
      const H = misure && misure.riquadro ? misure.altezza : 220;
      const NS = "http://www.w3.org/2000/svg";
      const el = (t, a, p) => { const e = document.createElementNS(NS, t); for (const [k, v] of Object.entries(a || {})) e.setAttribute(k, v); if (p) p.appendChild(e); return e; };
      const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `Pioggia di ogni giorno, ${st.serie.nome}` }, dest);
      const sx = 44, dx = 8, su = 10, gi = 26, w = W - sx - dx, hh = H - su - gi;
      const max = Math.max(1, ...gg.map((g) => Math.max(g.mm || 0, g.previsto_mm || 0)));
      const pas = [1, 2, 5, 10, 20, 25, 50, 100, 200].find((p) => max / p <= 5) || 500, cima = Math.ceil(max / pas) * pas;
      const y = (v) => su + hh - (v / cima) * hh;
      for (let v = 0; v <= cima + 1e-9; v += pas) {
        el("line", { x1: sx, x2: W - dx, y1: y(v), y2: y(v), class: "griglia" }, svg);
        const t = el("text", { x: sx - 6, y: y(v) + 4, "text-anchor": "end" }, svg); t.textContent = R.num(v);
      }
      const bw = w / gg.length, punti = [];
      gg.forEach((g, i) => {
        const x = sx + i * bw;
        const elementi = [];
        if (g.mm === null) {
          const r = el("rect", { x: x + 1, y: su, width: Math.max(1, bw - 2), height: hh, fill: "url(#tratteggio-pioggia)", opacity: 0.5 }, svg); elementi.push(r);
        } else {
          const r = el("rect", { x: x + 1, y: y(g.mm), width: Math.max(1, bw - 2), height: Math.max(0, y(0) - y(g.mm)), class: "barra" }, svg); elementi.push(r);
        }
        const segni = [];
        if (g.previsto_mm !== null && g.previsto_mm !== undefined) {
          el("line", { x1: x + 1, x2: x + bw - 1, y1: y(g.previsto_mm), y2: y(g.previsto_mm), class: "media" }, svg);
          segni.push([x + bw / 2, y(g.previsto_mm), colore("--inchiostro")]);
        }
        if (i % Math.ceil(gg.length / 8) === 0 || i === gg.length - 1) {
          const t = el("text", { x: x + bw / 2, y: H - 8, "text-anchor": "middle" }, svg); t.textContent = R.dataIt(g.data).slice(0, 5);
        }
        punti.push({ x: x + bw / 2, titolo: R.dataIt(g.data), righe: [[colore("--primario"), `misurata ${mm(g.mm)}`],
          ...(g.previsto_mm !== null && g.previsto_mm !== undefined ? [[colore("--inchiostro"), `prevista ${mm(g.previsto_mm)}`]] : [])], segni, elementi });
      });
      const defs = el("defs", {}, svg), pat = el("pattern", { id: "tratteggio-pioggia", width: 6, height: 6, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" }, defs);
      el("line", { x1: 0, y1: 0, x2: 0, y2: 6, stroke: "#808080", "stroke-width": 2 }, pat);
      el("line", { x1: sx, x2: W - dx, y1: y(0), y2: y(0), class: "asse" }, svg);
      if (window.EUGENIO_GRAFICI) window.EUGENIO_GRAFICI.osserva(svg, punti, { area: [sx, su, W - dx, su + hh], guida: false });
      const L = h("div", "legenda");
      const v1 = h("span"); const c1 = h("i"); c1.style.background = colore("--primario"); v1.append(c1, "pioggia misurata (Merging DPC)"); L.appendChild(v1);
      if (gg.some((g) => g.previsto_mm !== null && g.previsto_mm !== undefined)) { const v2 = h("span"); const c2 = h("i", "tratteggio"); v2.append(c2, "pioggia prevista dal sito a inizio giornata"); L.appendChild(v2); }
      const v3 = h("span"); const c3 = h("i"); c3.style.background = "repeating-linear-gradient(45deg,#808080 0 2px,transparent 2px 6px)"; v3.append(c3, "nessuna misura"); L.appendChild(v3);
      dest.appendChild(L);
    };
    if (window.EUGENIO_GRAFICI) window.EUGENIO_GRAFICI.registra(boxG, disegna, { titolo: `Pioggia di ogni giorno – ${st.serie.nome}`, adatta: true });
    else disegna(boxG, { larghezza: boxG.clientWidth, altezza: null, riquadro: false });
  }

  // ------------------------------------------------------------------ ortofoto sotto (come in Stato della rete elettrica)
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
      m.addLayer({ id: "contesto", type: "raster", source: "contesto", layout: { visibility: acceso("strato-ortofoto") ? "visible" : "none" }, paint: { "raster-opacity": 0.95 } }, primoSopra(m));
    }
    m.on("moveend", () => { if (acceso("strato-ortofoto")) sceltaOrto(); });
    if (acceso("strato-ortofoto")) await sceltaOrto();
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
      m.addLayer({ id: "ortofoto", type: "raster", source: "ortofoto", layout: { visibility: acceso("strato-ortofoto") ? "visible" : "none" } }, primoSopra(m));
    }
    attribuzioneOrto();
  }
  function attribuzioneOrto() {
    const a = $("attribuzione-ortofoto");
    if (!a) return;
    a.hidden = !acceso("strato-ortofoto") || !orto.fonti.length;
    if (a.hidden) return;
    a.innerHTML = "";
    const f = orto.fonte, z = st.mappa ? st.mappa.getZoom() : 0, parti = [];
    if (f) parti.push([`Ortofoto: ${citOrto(f)} – licenza `, f.licenza, f.scheda, f.zoom[0] > z ? ` (si vede dallo zoom ${f.zoom[0]}: avvicinati)` : ""]);
    if (orto.contesto) parti.push([`${f ? "Da lontano, contesto" : "Contesto"}: ${orto.contesto.citazione} – licenza `, orto.contesto.licenza, orto.contesto.scheda, ""]);
    parti.forEach(([t, lic, url, dopo], i) => { if (i) a.append(" "); a.append(t); const l = h("a", null, lic); if (url) l.href = url; a.append(l, `${dopo}.`); });
  }
  function righeOrto() {
    if (!acceso("strato-ortofoto") || !orto.fonti.length) return [];
    const f = orto.fonte, r = [];
    if (f && !f.copia) return null;
    if (f) r.push(`Ortofoto: ${citOrto(f)} – licenza ${f.licenza} (${f.scheda}).`);
    if (orto.contesto) r.push(`Contesto: ${orto.contesto.citazione} – licenza ${orto.contesto.licenza} (${orto.contesto.scheda}).`);
    return r;
  }

  // ------------------------------------------------------------------ immagine e file
  function opzioniImmagine() {
    const ro = righeOrto();
    if (ro === null) return `«${orto.fonte.nome}» è solo in consultazione dal vivo: per scaricare l'immagine spegni la casella «Ortofoto».`;
    const n = st.frames[st.i];
    const righe = [...ro];
    if (acceso("strato-pioggia") && n) {
      const sc = st.ind.scala.mm;
      righe.push(`${G.testoFrame(prodotto(), n)[0].toUpperCase()}${G.testoFrame(prodotto(), n).slice(1)}. Classi in mm: ${sc.soglie.join(", ")} e più; tratteggio grigio = nessuna misura.`);
      righe.push(`${G.ATTRIBUZIONE}. Questa immagine ha la stessa licenza (CC BY-SA 4.0). Dati a fini statistici, non di allerta.`);
    }
    if (acceso("strato-interruzioni")) righe.push("Punti blu: interruzioni della rete in corso nel passo (e-distribuzione S.p.A., durata stimata).");
    righe.push("Confini: ISTAT (CC BY 4.0).");
    const nome = `pioggia_${n || "senza_dato"}`;
    return { titolo: `Dati pluviometrici${n ? ` – ${G.testoFrame(prodotto(), n)}` : ""}`, righe, nome };
  }
  function datiFile() {
    if (!st.punto) return "Scegli prima un punto sulla mappa o cerca un comune.";
    const val = (st.valori && st.valori.valori) || {};
    const sezioni = [{ titolo: `Pioggia caduta nel punto ${R.num(st.punto.lat, 4)} N, ${R.num(st.punto.lon, 4)} E`, intestazioni: ["Periodo", "Fine del periodo", "Pioggia (mm)"],
      righe: ["CUM3", "CUM6", "CUM12", "CUM24"].filter((p) => val[p]).map((p) => [`ultime ${p.slice(3)} ore`, R.oraIt(val[p].fine), val[p].valore]) }];
    if (st.serie && st.serie.giornalieri && st.serie.giornalieri.length) {
      sezioni.push({ titolo: `Pioggia di ogni giorno – ${st.serie.nome} (ISTAT ${st.serie.istat})`, intestazioni: ["Giorno", "Misurata (mm)", "Prevista (mm)"],
        righe: st.serie.giornalieri.map((g) => [g.data, g.mm, g.previsto_mm ?? null]) });
    }
    const piede = [`${G.ATTRIBUZIONE}. Licenza dei dati di pioggia e di questo file: CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/).`,
      "Valori vuoti = nessuna misura (non zero). Pioggia prevista: previsioni del sito (Arpae ICON-2I, ECMWF IFS via Open-Meteo.com, CC BY 4.0).",
      "Dati a fini statistici, non di allerta."];
    const nome = `pioggia_${st.comune ? st.comune.istat : "punto"}_${new Date().toISOString().slice(0, 10)}`;
    const doc = {
      titolo: `Dati pluviometrici${st.comune ? ` – ${st.comune.nome}` : ""}`,
      sottotitolo: "pioggia misurata dal «Merging» del Dipartimento della Protezione Civile",
      nome_file: nome,
      sezioni: [
        { titolo: "Dati e licenza", blocchi: [
          { tipo: "avvertenza", testo: "Dati a fini statistici, non di allerta. I dati di pioggia sono sotto licenza CC BY-SA 4.0 (Dipartimento della Protezione Civile): chi li riusa deve citarli e condividere i lavori derivati con la stessa licenza." },
          { tipo: "paragrafo", testo: "«Merging»: radar meteorologici corretti con i pluviometri, quadretti di circa 1 km, un dato ogni 30 minuti. Valore del comune: mediana dei 9 quadretti attorno al centro abitato. Pioggia del giorno: pioggia delle 24 ore che finisce alla mezzanotte italiana. Valori vuoti: nessuna misura." },
        ] },
        ...sezioni.map((s) => ({ titolo: s.titolo, blocchi: [{ tipo: "tabella", intestazioni: s.intestazioni, righe: s.righe.length ? s.righe : [s.intestazioni.map(() => null)] }] })),
      ],
      fonti: [
        { testo: "Dipartimento della Protezione Civile – prodotti «Merging» CUM3, CUM6, CUM12, CUM24 (CC BY-SA 4.0)", url: G.URL_DPC },
        { testo: "dpc-radar – libreria di lettura (Apache-2.0)", url: "https://github.com/agent-engineering-studio/dpc-radar" },
        { testo: "Previsioni: Arpae ICON-2I, ECMWF IFS via Open-Meteo.com (CC BY 4.0)", url: "https://open-meteo.com/" },
        { testo: "ISTAT – confini e codici dei comuni (CC BY 4.0)", url: "https://www.istat.it/" },
      ],
      licenza: "CC BY-SA 4.0",            // testi della licenza del file (report.py, _lic): dati «share alike» del DPC
    };
    return { csv: [`${nome}.csv`, sezioni, piede], doc };
  }

  // collegamento a questa simulazione: durata, passo, secondi e caselle sono controlli data-collegamento; qui il punto e la
  // fine del periodo, salvata come ora (AAAAMMGGTHHMMZ) e non come posizione del cursore, che cambia ogni 30 minuti; senza
  // «fine» (o se quell'ora non c'è più) il periodo finisce all'ultimo dato
  if (window.EUGENIO_COLLEGAMENTO) window.EUGENIO_COLLEGAMENTO.registra({
    chiavi: ["lat", "lon", "fine"], principali: ["lat", "lon"],
    leggi: () => {
      if (!st.pronto) return null;
      const i = +$("fine").value, ultimo = i === st.fini.length - 1;
      return { lat: st.punto ? st.punto.lat.toFixed(5) : null, lon: st.punto ? st.punto.lon.toFixed(5) : null, fine: ultimo ? null : st.fini[i] || null };
    },
    applica: async (p) => {
      const f = p.get("fine");
      if (f && st.fini.includes(f)) { $("fine").value = String(st.fini.indexOf(f)); periodo(); }
      const lat = parseFloat(p.get("lat")), lon = parseFloat(p.get("lon"));
      if (Number.isFinite(lat) && Number.isFinite(lon)) await scegliPunto(lon, lat, true);
    },
    pronto: () => st.pronto,
  });

  avvio().catch((e) => messaggio("messaggio-mappa", `La mappa non si è aperta: ${e.message}`, true));
})();
