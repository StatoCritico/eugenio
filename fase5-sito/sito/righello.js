"use strict";
// Righello delle mappe con l'ortofoto (19/11/2026, richiesta di Paolo): Modelli 3D e pagine 3D, Ortofoto, Edifici pubblici,
// Aggiungi edifici, Cabine primarie (mappa di dettaglio), Stato della rete elettrica.
//  - Un piccolo pulsante con il righello sotto la mappa, accanto alle caselle dei livelli. Acceso: clic sinistro = punto
//    successivo; clic sul primo punto (con almeno tre punti) = la linea si chiude e diventa un'area; un punto si trascina
//    con il mouse; clic destro = azzera i punti (il righello resta acceso); Esc o un secondo clic sul pulsante = spento.
//  - Passando sopra la linea o l'area compare un riquadretto con la lunghezza (o perimetro e area). Distanze orizzontali
//    sull'ellissoide (formula dell'emisenoverso), aree nella proiezione locale equivalente attorno al centro (errore
//    trascurabile sotto qualche chilometro): misure indicative, non sostituiscono un rilievo.
//  - Con il righello acceso i clic sulla mappa non arrivano alla pagina (non scelgono edifici, non spostano punti): gli
//    eventi si fermano sul contenitore della mappa prima di MapLibre; spostamento e zoom restano quelli di sempre.
//
//  EUGENIO_RIGHELLO.aggiungi(mappa, { dove, prima })  → { attivo(), misura(), spegni(), punti(lonlat[]) }
//  dove: elemento in cui mettere il pulsante (in fondo, o in testa con prima: true); senza, una riga subito sotto la mappa.
(function () {
  const R = 6371008.8;                      // raggio medio della Terra (m)
  const ID = { fondo: "righello-area", bordo: "righello-bordo", linea: "righello-linea", anteprima: "righello-anteprima", punti: "righello-punti" };
  const VICINO = 9;                         // px: presa di un punto, chiusura sul primo punto
  const SOPRA = 8;                          // px: distanza dalla linea per il riquadretto
  const MOSSO = 4;                          // px: oltre, un clic è la fine di uno spostamento della mappa
  const ICONA = '<svg class="icona-righello" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">'
    + '<path d="M2.8 15.6 15.6 2.8l5.6 5.6L8.4 21.2z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>'
    + '<path d="M6.4 12l2 2M8.8 9.6l1.3 1.3M11.2 7.2l2 2M13.6 4.8l1.3 1.3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>';
  function h(tag, cls, t) { const e = document.createElement(tag); if (cls) e.className = cls; if (t !== undefined && t !== null) e.textContent = t; return e; }
  const rad = (g) => g * Math.PI / 180;

  // ------------------------------------------------------------------ misure
  function distanza(a, b) {
    const f1 = rad(a[1]), f2 = rad(b[1]), df = f2 - f1, dl = rad(b[0] - a[0]);
    const s = Math.sin(df / 2) ** 2 + Math.cos(f1) * Math.cos(f2) * Math.sin(dl / 2) ** 2;
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(s)));
  }
  function lunghezza(pts, chiuso) {
    let l = 0;
    for (let i = 1; i < pts.length; i++) l += distanza(pts[i - 1], pts[i]);
    if (chiuso && pts.length > 2) l += distanza(pts[pts.length - 1], pts[0]);
    return l;
  }
  // area in m²: proiezione cilindrica equivalente (Lambert) attorno alla latitudine media, formula di Gauss
  function area(pts) {
    if (pts.length < 3) return 0;
    const lat0 = pts.reduce((s, p) => s + p[1], 0) / pts.length, lon0 = pts[0][0], c = Math.cos(rad(lat0));
    const xy = pts.map((p) => [R * rad(p[0] - lon0) * c, R * Math.sin(rad(p[1])) / c]);
    let a = 0;
    for (let i = 0; i < xy.length; i++) { const p = xy[i], q = xy[(i + 1) % xy.length]; a += p[0] * q[1] - q[0] * p[1]; }
    return Math.abs(a) / 2;
  }
  const num = (v, d) => v.toLocaleString("it-IT", { minimumFractionDigits: d, maximumFractionDigits: d });
  const testoL = (m) => (m < 1000 ? `${num(m, m < 100 ? 2 : 1)} m` : `${num(m / 1000, 3)} km`);
  function testoA(a) {
    if (a < 10000) return `${num(a, a < 100 ? 2 : 0)} m²`;
    if (a < 1e6) return `${num(a, 0)} m² (${num(a / 10000, 2)} ha)`;
    return `${num(a / 1e6, 3)} km² (${num(a / 10000, 0)} ha)`;
  }

  // ------------------------------------------------------------------ geometria in pixel
  function distSegmento(p, a, b) {
    const ex = b[0] - a[0], ey = b[1] - a[1], l2 = ex * ex + ey * ey || 1;
    const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * ex + (p[1] - a[1]) * ey) / l2));
    return Math.hypot(a[0] + t * ex - p[0], a[1] + t * ey - p[1]);
  }
  function dentro(p, poli) {
    let s = false;
    for (let i = 0, j = poli.length - 1; i < poli.length; j = i++) {
      const [xi, yi] = poli[i], [xj, yj] = poli[j];
      if ((yi > p[1]) !== (yj > p[1]) && p[0] < (xj - xi) * (p[1] - yi) / (yj - yi) + xi) s = !s;
    }
    return s;
  }

  function aggiungi(m, opz = {}) {
    if (!m) return null;
    if (m._eugenioRighello) return m._eugenioRighello;
    const box = m.getContainer(), canvas = () => m.getCanvas(), tela = () => m.getCanvasContainer();
    const st = { attivo: false, punti: [], chiuso: false, cursore: null, trascina: -1, giu: null, giuDestro: null, finito: 0 };

    // ---------------------------------------------------------------- pulsante e aiuto
    const b = h("button", "bottone secondario righello");
    b.type = "button"; b.innerHTML = ICONA;
    const titolo = "Righello: misura distanze e aree sulla mappa (clic per i punti, clic destro per azzerare)";
    b.title = titolo; b.setAttribute("aria-label", titolo); b.setAttribute("aria-pressed", "false");
    const aiuto = h("span", "aiuto-breve righello-aiuto",
      "Clic: punto · clic sul primo punto: area · trascina un punto per spostarlo · clic destro: azzera · Esc: spegni. Passa sopra la misura per i valori.");
    aiuto.hidden = true;
    if (opz.dove) {
      const g = h("span", "righello-gruppo"); g.id = `righello-${box.id || "mappa"}`; g.append(b, aiuto);
      if (opz.prima) opz.dove.prepend(g); else opz.dove.appendChild(g);
    } else {
      const riga = h("div", "righello-riga"); riga.id = `righello-${box.id || "mappa"}`; riga.append(b, aiuto);
      // subito sotto la mappa; se c'è la maniglia dell'altezza (divisore.js), sotto la maniglia
      const dopo = box.nextElementSibling && box.nextElementSibling.classList.contains("maniglia-mappa") ? box.nextElementSibling : box;
      dopo.after(riga);
    }
    const et = h("div", "etichetta-mappa righello-etichetta");
    et.setAttribute("aria-hidden", "true");
    box.appendChild(et);
    const stato = h("span", "solo-lettori");
    stato.setAttribute("role", "status"); stato.setAttribute("aria-live", "polite");
    (b.parentNode || box).appendChild(stato);

    // ---------------------------------------------------------------- strati della mappa
    const vuota = () => ({ type: "FeatureCollection", features: [] });
    function strati() {
      if (m.getSource("righello")) return true;
      try {
        m.addSource("righello", { type: "geojson", data: vuota() });
        m.addSource("righello-punti", { type: "geojson", data: vuota() });
        m.addLayer({ id: ID.fondo, type: "fill", source: "righello", filter: ["==", ["geometry-type"], "Polygon"],
          paint: { "fill-color": "#ffd23f", "fill-opacity": 0.2 } });
        m.addLayer({ id: ID.bordo, type: "line", source: "righello", layout: { "line-cap": "round", "line-join": "round" },
          paint: { "line-color": "#1a1a1a", "line-width": 5, "line-opacity": 0.75 } });
        m.addLayer({ id: ID.linea, type: "line", source: "righello", filter: ["!", ["has", "anteprima"]], layout: { "line-cap": "round", "line-join": "round" },
          paint: { "line-color": "#ffd23f", "line-width": 2.6 } });
        // tratto verso il puntatore mentre si disegna: tratteggiato (strato a parte: line-dasharray non dipende dai dati)
        m.addLayer({ id: ID.anteprima, type: "line", source: "righello", filter: ["has", "anteprima"],
          paint: { "line-color": "#ffd23f", "line-width": 2.2, "line-dasharray": [2, 1.5] } });
        m.addLayer({ id: ID.punti, type: "circle", source: "righello-punti",
          paint: { "circle-radius": ["case", ["get", "primo"], 6, 4.5], "circle-color": ["case", ["get", "primo"], "#ffd23f", "#ffffff"],
            "circle-stroke-color": "#1a1a1a", "circle-stroke-width": 1.6 } });
        return true;
      } catch { return false; }
    }
    // sempre in cima: le pagine aggiungono strati anche dopo (ortofoto, particelle, edifici…)
    function inCima() {
      const ls = (m.getStyle() && m.getStyle().layers) || [];
      const ids = [ID.fondo, ID.bordo, ID.linea, ID.anteprima, ID.punti];
      const coda = ls.slice(-ids.length).map((l) => l.id);
      if (coda.join("|") === ids.join("|")) return;
      ids.forEach((id) => { if (m.getLayer(id)) m.moveLayer(id); });
    }
    function disegna() {
      if (!strati()) return;
      inCima();
      const P = st.punti, fs = [];
      if (st.chiuso && P.length > 2) fs.push({ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [[...P, P[0]]] } });
      else if (P.length > 1) fs.push({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: P } });
      if (st.attivo && !st.chiuso && P.length && st.cursore && st.trascina < 0)
        fs.push({ type: "Feature", properties: { anteprima: true }, geometry: { type: "LineString", coordinates: [P[P.length - 1], st.cursore] } });
      m.getSource("righello").setData({ type: "FeatureCollection", features: fs });
      m.getSource("righello-punti").setData({ type: "FeatureCollection", features: P.map((p, i) => ({ type: "Feature",
        properties: { primo: i === 0 && !st.chiuso && P.length > 2 }, geometry: { type: "Point", coordinates: p } })) });
    }

    // ---------------------------------------------------------------- testi
    function righe(conCursore = false) {
      const P = st.punti;
      if (st.chiuso && P.length > 2) return { titolo: "Area misurata", righe: [`Area: ${testoA(area(P))}`, `Perimetro: ${testoL(lunghezza(P, true))}`, `${P.length} vertici`] };
      if (!P.length) return null;
      const r = [];
      const tot = lunghezza(P, false);
      if (conCursore && st.cursore && st.attivo) {
        const ult = distanza(P[P.length - 1], st.cursore);
        r.push(`Fino al puntatore: ${testoL(tot + ult)}`, `Ultimo tratto: ${testoL(ult)}`);
        if (P.length > 1) r.push(`Fissata: ${testoL(tot)}`);
      } else r.push(`Lunghezza: ${testoL(tot)}`, `${P.length} ${P.length === 1 ? "punto" : "punti"}${P.length > 1 ? `, ${P.length - 1} ${P.length === 2 ? "tratto" : "tratti"}` : ""}`);
      if (st.attivo && P.length > 2) r.push("clic sul primo punto: chiudi l'area");
      return { titolo: "Distanza misurata", righe: r };
    }
    function mostra(c, px) {
      if (!c) { et.style.display = "none"; return; }
      et.innerHTML = "";
      et.appendChild(h("b", null, c.titolo));
      c.righe.forEach((x) => et.appendChild(h("div", null, x)));
      et.style.display = "block";
      const W = box.clientWidth, H = box.clientHeight, w = et.offsetWidth, hh = et.offsetHeight;
      let x = px[0] + 14, y = px[1] + 16;
      if (x + w > W - 4) x = px[0] - 14 - w;
      if (y + hh > H - 4) y = px[1] - 16 - hh;
      et.style.left = `${Math.max(4, Math.min(x, W - w - 4))}px`; et.style.top = `${Math.max(4, y)}px`;
    }
    function annuncia() { const c = righe(false); stato.textContent = c ? `${c.titolo}: ${c.righe[0]}` : ""; }

    // ---------------------------------------------------------------- eventi
    const pixel = (e) => { const r = canvas().getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
    const sullaTela = (e) => !!(e.target && tela().contains(e.target));
    const proietta = (ll) => { const p = m.project(ll); return [p.x, p.y]; };
    function puntoVicino(px) {
      let k = -1, d = VICINO;
      st.punti.forEach((p, i) => { const q = proietta(p), x = Math.hypot(q[0] - px[0], q[1] - px[1]); if (x <= d) { d = x; k = i; } });
      return k;
    }
    function sopraForma(px) {
      const P = st.punti.map(proietta);
      if (!P.length) return false;
      if (P.length === 1) return Math.hypot(P[0][0] - px[0], P[0][1] - px[1]) <= VICINO;
      const giri = st.chiuso ? [...P, P[0]] : P;
      for (let i = 1; i < giri.length; i++) if (distSegmento(px, giri[i - 1], giri[i]) <= SOPRA) return true;
      return st.chiuso && P.length > 2 && dentro(px, P);
    }
    const ll = (px) => { const p = m.unproject(px); return [p.lng, p.lat]; };

    function giu(e) {
      if (!st.attivo || !sullaTela(e)) return;
      const px = pixel(e);
      if (e.button === 2) { st.giuDestro = px; return; }
      if (e.button !== 0) return;
      st.giu = px;
      const k = puntoVicino(px);
      if (k < 0) return;                                  // fuori dai punti: la mappa si sposta come sempre
      e.preventDefault(); e.stopPropagation();
      st.trascina = k;
      box.classList.add("righello-trascina");
      let mosso = false;
      const muovi = (ev) => {
        const q = pixel(ev);
        if (!mosso && Math.hypot(q[0] - px[0], q[1] - px[1]) <= MOSSO) return;      // ancora un clic, non un trascinamento
        mosso = true; st.punti[st.trascina] = ll(q); disegna(); mostra(righe(false), q);
      };
      const su = () => {
        window.removeEventListener("mousemove", muovi, true); window.removeEventListener("mouseup", su, true);
        // un clic fermo su un punto resta un clic (sul primo punto chiude l'area): il click che segue non si scarta
        if (mosso) st.finito = Date.now();
        st.trascina = -1; box.classList.remove("righello-trascina"); disegna(); annuncia();
      };
      window.addEventListener("mousemove", muovi, true); window.addEventListener("mouseup", su, true);
    }
    function clic(e) {
      if (!st.attivo || !sullaTela(e)) return;
      e.stopPropagation(); e.preventDefault();
      if (Date.now() - st.finito < 350) return;                         // fine del trascinamento di un punto
      const px = pixel(e);
      if (st.giu && Math.hypot(st.giu[0] - px[0], st.giu[1] - px[1]) > MOSSO) return;   // fine di uno spostamento della mappa
      st.giu = null;
      if (st.chiuso) { st.punti = []; st.chiuso = false; }             // area finita: il clic ne comincia un'altra
      if (st.punti.length > 2) {
        const q = proietta(st.punti[0]);
        if (Math.hypot(q[0] - px[0], q[1] - px[1]) <= VICINO) { st.chiuso = true; st.cursore = null; disegna(); mostra(righe(false), px); annuncia(); return; }
      }
      st.punti.push(ll(px));
      st.cursore = st.punti[st.punti.length - 1];
      disegna(); mostra(righe(true), px); annuncia();
    }
    function destro(e) {
      if (!st.attivo || !sullaTela(e)) return;
      e.preventDefault(); e.stopPropagation();
      const px = pixel(e);
      // dopo una rotazione col tasto destro (pagine 3D) i punti restano
      if (st.giuDestro && Math.hypot(st.giuDestro[0] - px[0], st.giuDestro[1] - px[1]) > MOSSO) { st.giuDestro = null; return; }
      st.giuDestro = null;
      azzera();
    }
    function ferma(e) { if (st.attivo && sullaTela(e)) { e.stopPropagation(); e.preventDefault(); } }
    function muovi(e) {
      if (st.trascina >= 0) return;
      if (!sullaTela(e)) { if (!st.attivo) mostra(null); return; }
      const px = pixel(e);
      box.classList.toggle("righello-su-punto", st.attivo && puntoVicino(px) >= 0);
      if (st.attivo && !st.chiuso && st.punti.length) {
        st.cursore = ll(px); disegna(); mostra(righe(true), px); return;
      }
      mostra(sopraForma(px) ? righe(false) : null, px);
    }
    const fuori = () => { mostra(null); if (st.attivo && st.cursore && !st.chiuso) { st.cursore = null; disegna(); } };
    function tasto(e) {
      if (!st.attivo || e.key !== "Escape") return;
      const t = e.target && e.target.tagName;
      if (/^(INPUT|SELECT|TEXTAREA)$/.test(t || "")) return;
      spegni();
    }
    box.addEventListener("mousedown", giu, true);
    box.addEventListener("click", clic, true);
    box.addEventListener("contextmenu", destro, true);
    box.addEventListener("dblclick", ferma, true);
    box.addEventListener("mousemove", muovi);
    box.addEventListener("mouseleave", fuori);
    document.addEventListener("keydown", tasto);

    function azzera() { st.punti = []; st.chiuso = false; st.cursore = null; mostra(null); disegna(); annuncia(); }
    function accendi() {
      st.attivo = true; b.setAttribute("aria-pressed", "true"); aiuto.hidden = false; box.classList.add("righello-attivo");
      disegna(); stato.textContent = "Righello acceso: clic sulla mappa per i punti.";
    }
    function spegni() {
      st.attivo = false; b.setAttribute("aria-pressed", "false"); aiuto.hidden = true;
      box.classList.remove("righello-attivo", "righello-su-punto");
      azzera(); stato.textContent = "Righello spento.";
    }
    b.addEventListener("click", () => (st.attivo ? spegni() : accendi()));

    const api = {
      attivo: () => st.attivo, spegni, accendi, azzera, pulsante: b,
      misura: () => ({ punti: st.punti.map((p) => [...p]), chiuso: st.chiuso, lunghezza: lunghezza(st.punti, st.chiuso),
        area: st.chiuso ? area(st.punti) : null }),
      punti: (pts, chiuso = false) => { st.punti = (pts || []).map((p) => [+p[0], +p[1]]); st.chiuso = !!chiuso && st.punti.length > 2; st.cursore = null; disegna(); annuncia(); },
    };
    m._eugenioRighello = api;
    return api;
  }

  window.EUGENIO_RIGHELLO = { aggiungi, distanza, lunghezza, area, testoL, testoA };
})();
