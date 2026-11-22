"use strict";
// Statistiche › «Produzione e consumi di elettricità» (elettricita.html, 20/11/2026, richiesta di Paolo).
// Mappa MapLibre dell'Italia con le regioni bianche e, in ogni regione, un istogramma (barre verticali affiancate, una per
// fonte o settore, scalate sul valore più alto fra tutte le regioni e tutti gli anni della grandezza scelta). Un clic su
// una regione (nella mappa grande o nella piccola) la sceglie: la mappa si avvicina e gli istogrammi passano alle
// province; un secondo clic torna all'Italia. Sotto la mappa il selettore (capacità, produzione, richiesta, consumi,
// burden sharing) e il cursore dell'anno. A destra il grafico cumulato (Italia o regione, anno per anno), le barre delle
// province nell'anno scelto e la tabella dei valori con i totali.
// Burden sharing (verticale dal 21/11/2026): per ogni regione la colonna dell'obiettivo 2030 del DM 21/6/2024 (Tabella A,
// rettangolo arancione vuoto, con la linea dell'obiettivo dell'anno scelto) e dentro la potenza rinnovabile in più
// rispetto al 2020, impilata per fonte; sotto la linea di base.
// Dati: dati/elettricita/italia.json e RR.json (fase 15, costruiti dal worker con le statistiche di Terna).
// Decisione di Paolo (20/11/2026): i dati non si scaricano; si scarica solo l'immagine della mappa (esporta_mappa.js).
// Gli istogrammi sono immagini della mappa (addImage + strato di simboli), così finiscono anche nell'immagine scaricata.
// Emissioni (21/11/2026, richiesta di Paolo): in ogni regione (o provincia della regione scelta) un anello con la
// produzione per fonte (stessi colori della Produzione); l'area dell'anello cresce in proporzione alla produzione, a
// partire da un anello minimo, e nel buco c'è il fattore di emissione medio della regione. A destra tre riquadri con i
// valori nazionali confrontati con il fattore MEF (0,187 tep/MWh) e con i fattori ISPRA, il grafico dei tre fattori anno
// per anno e la tabella per regione con i subtotali per zona di mercato e il totale Italia. Indicatori e riferimenti li
// calcola il costruttore (fase 15, indicatori() e riferimenti_emissioni.json): qui non c'è nessun numero scritto a mano.
// Periodo (22/11/2026, 02:08, Paolo): cursore a due indicatori come in «Suolo e aree agricole» (componente comune
// cursore_periodo.js), all'apertura tutti e due sull'ultimo anno. Con un periodo le grandezze di flusso (produzione,
// carichi, consumi, emissioni) si sommano sugli anni del periodo e i fattori (tCO₂/MWh, tep/MWh) si ricalcolano come
// rapporto delle somme; le grandezze di stato (capacità, burden sharing) sono quelle dell'anno finale, con la variazione
// rispetto all'anno iniziale nel riquadretto e nella tabella e un trattino nero al valore iniziale sull'istogramma. Nel
// grafico a destra gli anni del periodo sono evidenziati. Collegamento con inizio e fine (anno = un anno solo, i vecchi
// collegamenti continuano a funzionare).
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
    emissioni: { nome: "Emissioni", breve: "emissioni", grandezza: "produzione" },
  };
  const st = { mappa: null, it: null, prov: new Map(), modo: "capacita", inizio: null, fine: null, anno: null, regione: null, giro: 0, img: new Set(), sugg: null };
  const D = () => st.it;
  const voci = (g) => D().voci[g];
  const unita = (g) => D().unita[g];
  const anniDi = (modo) => (modo === "burden" ? D().anni.capacita.filter((a) => a >= 2021)
    : modo === "emissioni" ? (D().anni.emissioni || []).filter((a) => D().anni.produzione.includes(a)) : D().anni[MODI[modo].grandezza]);
  // emissioni: indicatori [termo GWh, rinnovabili GWh, totale GWh, CO2 kt, tep, fattore medio, fattore termo, tep/MWh]
  const EM = () => D().emissioni;
  const IND = { termo: 0, fer: 1, tot: 2, co2: 3, tep: 4, medio: 5, ftermo: 6, tepmwh: 7 };
  const indicatoriDi = (x, a) => (x && x.indicatori && x.indicatori[String(a)]) || null;
  const indItalia = (a) => (EM() && EM().italia[String(a)]) || null;
  // ISPRA: energia primaria per la produzione elettrica (nazionale, ktep) diviso la produzione termoelettrica di Terna
  const ispraTep = (a) => { const e = EM().riferimenti.ispra.energia_primaria, k = e && e.anni_ktep[String(a)], i = indItalia(a);
    return k !== undefined && k !== null && i && i[IND.termo] ? { ktep: k, tepmwh: k / i[IND.termo] } : null; };
  const ispra = (serie, a) => { const v = EM().riferimenti.ispra.serie[serie]; return v && v.anni[String(a)] !== undefined ? v.anni[String(a)] : null; };
  const valori = (x, g, a) => (x && x[g] && x[g][String(a)]) || null;
  const somma = (arr) => (arr || []).reduce((t, v) => t + v, 0);

  // ------------------------------------------------------------------ periodo
  // st.anno è sempre l'anno finale (le grandezze di stato, gli obiettivi del burden sharing)
  const flusso = (modo = st.modo) => modo !== "capacita" && modo !== "burden";
  const conPeriodo = () => st.inizio !== null && st.inizio < st.fine;
  const testoP = () => (conPeriodo() ? `${st.inizio}–${st.fine}` : String(st.fine));
  const nelPeriodo = (a) => a >= st.inizio && a <= st.fine;
  const anniPeriodo = (modo = st.modo) => anniDi(modo).filter(nelPeriodo);
  // valori dell'unità x per la grandezza g: flussi sommati sugli anni del periodo, stati all'anno finale
  function valoriP(x, g, modo = st.modo) {
    if (!flusso(modo)) return valori(x, g, st.fine);
    let acc = null;
    for (const a of anniPeriodo(modo)) { const v = valori(x, g, a); if (v) acc = acc ? acc.map((y, i) => y + v[i]) : [...v]; }
    return acc;
  }
  // stati all'anno iniziale (solo con un periodo)
  const valoriIniziali = (x, g) => (conPeriodo() && !flusso() ? valori(x, g, st.inizio) : null);
  // indicatori delle emissioni del periodo: [termo, fer, tot, CO2, tep] sommati, fattori come rapporto delle somme
  // (fattore medio = CO2 / tot, fattore del termoelettrico = CO2 / termo, tep/MWh = tep / termo / 1000)
  function indicatoriP(di) {
    const anni = anniPeriodo("emissioni");
    if (anni.length === 1 || !conPeriodo()) return di(st.fine);
    let acc = null;
    for (const a of anni) { const v = di(a); if (!v) continue; acc = acc ? acc.map((y, i) => y + (v[i] || 0)) : v.slice(0, 5).map((y) => y || 0); }
    if (!acc) return null;
    const r = (n, d, k = 1) => (d ? +(n / d / k).toFixed(4) : null);
    return [...acc, r(acc[IND.co2], acc[IND.tot]), r(acc[IND.co2], acc[IND.termo]), r(acc[IND.tep], acc[IND.termo], 1000)];
  }
  const indRegioneP = (x) => indicatoriP((a) => indicatoriDi(x, a));
  const indItaliaP = () => indicatoriP(indItalia);
  const segno = (v, d = 0) => (v === null || v === undefined ? "–" : (v > 0 ? "+" : v < 0 ? "−" : "") + num(Math.abs(v), d));

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
  // (21/11/2026, Paolo) quanto manca all'obiettivo 2030 nell'anno a: della regione (o del totale Italia); per una
  // provincia, della sua regione (le province non hanno obiettivi). { ob30, netto, pct, mancano, di } oppure null
  function verso2030(x, a) {
    const r = x && x.obiettivi ? x : (st.regione ? D().regioni.find((q) => q.cod === st.regione) : null);
    const ob30 = r && r.obiettivi ? r.obiettivi[r.obiettivi.length - 1] : null, ag = r ? aggiunta(r, a) : null;
    if (!ob30 || !ag) return null;
    return { ob30, netto: ag.netto, pct: 100 * ag.netto / ob30, mancano: Math.max(0, ob30 - ag.netto), di: r === x ? "" : ` (${r.nome})` };
  }
  const righe2030 = (v) => [[ARANCIO, `Obiettivo 2030${v.di}: ${num(v.ob30)} MW`],
    [null, `Raggiunto: ${num(v.pct)} % (${num(v.netto)} MW in più dal 2020)`], [null, `Mancano: ${num(v.mancano)} MW`]];

  // ------------------------------------------------------------------ istogrammi come immagini della mappa
  const PR = Math.min(2, window.devicePixelRatio || 1);
  // (21/11/2026, Paolo) istogrammi più grandi: si disegna con le misure di prima e la tela è ingrandita di INGRANDISCI
  // (resta nitida, non è un'immagine stirata dalla mappa). Prima il doppio; il 22/11/2026 (00:59) Paolo: «troppo
  // grandi, riducili del 30 %» → 1,4. Gli anelli delle emissioni hanno la loro misura (ANELLI, raggi in RAGGI).
  const INGRANDISCI = 1.4, ANELLI = 2;
  function tela(w, hgt, scala = INGRANDISCI) { const f = PR * scala, c = document.createElement("canvas"); c.width = Math.round(w * f); c.height = Math.round(hgt * f); const k = c.getContext("2d"); k.scale(f, f); return [c, k]; }
  function barreVerticali(vals, colori, max, alto, neg, iniziali) {
    // barre affiancate: base in basso (o al centro per i valori negativi della richiesta), contorno scuro sottile;
    // con un periodo e una grandezza di stato (capacità) un trattino nero al valore dell'anno iniziale
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
    if (iniziali) iniziali.forEach((v, i) => {
      if (!(v > 0)) return;
      k.fillStyle = "#111"; k.fillRect(2 + i * (lb + gap) - 1, y0 - Math.max(1, v / max * alto) - 0.6, lb + 2, 1.2);
    });
    k.strokeStyle = "#222"; k.lineWidth = 1; k.beginPath(); k.moveTo(0, y0 + 0.5); k.lineTo(W, y0 + 0.5); k.stroke();
    return { c, ancora: neg ? [0, (Ht / 2 - y0) / Ht] : null };
  }
  // (21/11/2026 notte, Paolo) burden sharing verticale come gli altri istogrammi: colonna delle rinnovabili in più dal
  // 2020 impilata per fonte (solo le parti positive: i valori negativi, per esempio le bioenergie dismesse, restano nel
  // riquadretto) con la linea di base (lo zero). (22/11/2026, 00:18) il rettangolo arancione vuoto dell'obiettivo 2030 e
  // la linea nera dell'obiettivo dell'anno scelto sono un'immagine a parte, della stessa misura, che compare solo sulla
  // regione sotto il mouse (o toccata): strato «el-obiettivi» filtrato sul codice. La scala comprende sempre gli
  // obiettivi 2030, così quando l'obiettivo compare la colonna non cambia. Le province non hanno obiettivi.
  const ARANCIO = "#f08a24";
  function misureBurden(alto) { const lo = st.regione ? 20 : 16; return { lo, li: st.regione ? 12 : 10, W: lo + 8, Ht: alto + 4, y0: alto + 2, x0: 4 }; }
  function barreBurden(parti, max, alto, iniziale) {
    const { lo, li, W, Ht, y0, x0 } = misureBurden(alto), [c, k] = tela(W, Ht), sc = (v) => Math.max(0, v) / max * alto;
    let y = y0;
    for (const p of parti) { if (!(p.v > 0)) continue; const hh = sc(p.v); k.fillStyle = colore("capacita", p.id); k.fillRect(x0 + (lo - li) / 2, y - hh, li, hh); y -= hh; }
    if (y < y0) { k.strokeStyle = "rgba(0,0,0,0.55)"; k.lineWidth = 0.6; k.strokeRect(x0 + (lo - li) / 2 + 0.3, y + 0.3, li - 0.6, y0 - y - 0.6); }
    // con un periodo: trattino nero all'altezza della colonna dell'anno iniziale
    if (iniziale > 0) { k.fillStyle = "#111"; k.fillRect(x0 + (lo - li) / 2 - 2, y0 - sc(iniziale) - 0.6, li + 4, 1.2); }
    k.strokeStyle = "#222"; k.lineWidth = 1; k.beginPath(); k.moveTo(0, y0 + 0.5); k.lineTo(W, y0 + 0.5); k.stroke();
    return { c };
  }
  function obiettivoBurden(ob2030, obAnno, max, alto) {
    const { lo, W, Ht, y0, x0 } = misureBurden(alto), [c, k] = tela(W, Ht), sc = (v) => Math.max(0, v) / max * alto;
    const hh = sc(ob2030); k.strokeStyle = ARANCIO; k.lineWidth = 1.6; k.strokeRect(x0 + 0.8, y0 - hh + 0.8, lo - 1.6, hh - 0.8);
    if (obAnno !== null && obAnno > 0) { k.fillStyle = "#111"; k.fillRect(x0 - 3, y0 - sc(obAnno) - 0.8, lo + 6, 1.6); }
    return { c };
  }
  // anello (torta con il buco): produzione per fonte, in senso orario da mezzogiorno; nel buco un testo (fattore medio)
  function anello(vals, colori, r, testo) {
    const W = 2 * r + 4, [c, k] = tela(W, W, ANELLI), cx = W / 2, ri = r * 0.55, tot = somma(vals.map((v) => Math.max(0, v)));
    let a0 = -Math.PI / 2;
    vals.forEach((v, i) => {
      if (!(v > 0)) return;
      const a1 = a0 + 2 * Math.PI * v / tot;
      k.beginPath(); k.arc(cx, cx, r, a0, a1); k.arc(cx, cx, ri, a1, a0, true); k.closePath();
      k.fillStyle = colori[i]; k.fill();
      k.strokeStyle = "rgba(0,0,0,0.45)"; k.lineWidth = 0.5; k.stroke();
      a0 = a1;
    });
    k.beginPath(); k.arc(cx, cx, r, 0, 2 * Math.PI); k.strokeStyle = "#222"; k.lineWidth = 0.9; k.stroke();
    k.beginPath(); k.arc(cx, cx, ri, 0, 2 * Math.PI); k.fillStyle = "rgba(255,255,255,0.92)"; k.fill(); k.strokeStyle = "#222"; k.lineWidth = 0.7; k.stroke();
    // testo nel buco solo se il buco è largo almeno 18 px sulla mappa (misure qui in unità di disegno, × ANELLI)
    if (testo && ri * ANELLI >= 9) {
      const fs = Math.min(6.5, Math.max(4.5, ri * 0.75));
      k.font = `700 ${fs}px system-ui, sans-serif`; k.textAlign = "center"; k.textBaseline = "middle"; k.fillStyle = "#111";
      k.fillText(testo, cx, cx + 0.5, 2 * ri - 2);
    }
    return { c };
  }
  // raggio dell'anello: area = area minima + parte proporzionale alla produzione (scala comune a tutte le unità e gli anni)
  // (22/11/2026, 00:18, Paolo) anelli più piccoli, che nella vista dell'Italia e delle province non si sovrappongono:
  // raggio in pixel sulla mappa da 9 a 24 (regioni) o da 7 a 20 (province), diviso per ANELLI perché la tela lo ingrandisce
  // Nella vista dell'Italia i raggi seguono lo zoom dell'inquadratura (mappa più piccola = Italia più piccola = anelli
  // più piccoli; riferimento: zoom 4,5 con la mappa di 800 × 640 px), mai più grandi del riferimento.
  const RAGGI = { regioni: [8, 21], province: [7, 20] };
  function scalaAnelli() {
    if (st.regione || !st.mappa) return 1;
    const cam = st.mappa.cameraForBounds([[C.ITALIA[0], C.ITALIA[1]], [C.ITALIA[2], C.ITALIA[3]]], { padding: margini(10) });
    return cam && Number.isFinite(cam.zoom) ? Math.max(0.5, Math.min(1, 2 ** (cam.zoom - 4.5))) : 1;
  }
  const raggio = (tot, max, k = 1) => { const [r0, r1] = RAGGI[st.regione ? "province" : "regioni"];
    return k * Math.sqrt(r0 * r0 + (r1 * r1 - r0 * r0) * Math.max(0, tot) / max) / ANELLI; };

  function immagine(id, disegno) {
    const m = st.mappa, k = disegno.c.getContext("2d"), dati = k.getImageData(0, 0, disegno.c.width, disegno.c.height);
    if (m.hasImage(id)) m.removeImage(id);
    m.addImage(id, { width: disegno.c.width, height: disegno.c.height, data: dati.data }, { pixelRatio: PR });   // misura sulla mappa = INGRANDISCI (o ANELLI) × disegno
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
    // con un periodo i flussi sono somme: la scala comprende anche il periodo scelto (oltre agli anni singoli)
    const tutti = (x) => [...Object.values(x[g] || {}), ...(flusso(modo) && conPeriodo() ? [valoriP(x, g, modo)].filter(Boolean) : [])];
    if (modo === "emissioni") { for (const x of unita) for (const v of tutti(x)) mx = Math.max(mx, somma(v.filter((y) => y > 0))); return mx || 1; }
    for (const x of unita) for (const v of tutti(x)) for (const y of v) mx = Math.max(mx, Math.abs(y));
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
    const max = massimo(unitaMappa, modo), features = [], kAnelli = modo === "emissioni" ? scalaAnelli() : 1;
    const alto = st.regione ? 90 : 70;
    const neg = g === "richiesta";
    for (const x of unitaMappa) {
      const id = `el-${x.cod || x.nome}`.replace(/[^\w-]/g, "_");
      let dis = null, conOb = "", rAnello = 0;
      if (modo === "burden") {
        const ag = aggiunta(x, a), ag0 = conPeriodo() ? aggiunta(x, st.inizio) : null;
        if (ag) dis = barreBurden(ag.parti, max, alto, ag0 ? somma(ag0.parti.map((p) => Math.max(0, p.v))) : 0);
        if (ag && x.obiettivi) { immagine(`${id}-ob`, obiettivoBurden(x.obiettivi[x.obiettivi.length - 1], obiettivo(x, a), max, alto)); conOb = `${id}-ob`; }
      } else if (modo === "emissioni") {
        const v = valoriP(x, g), ind = st.regione ? null : indRegioneP(x);
        if (v && somma(v.filter((y) => y > 0)) > 0) { rAnello = raggio(somma(v.filter((y) => y > 0)), max, kAnelli) * ANELLI;
          dis = anello(v, voci(g).map((q) => q.colore), rAnello / ANELLI, ind && ind[IND.medio] !== null ? num(ind[IND.medio], 2) : null); }
      } else {
        const v = valoriP(x, g);
        if (v && somma(v.map(Math.abs)) > 0) dis = barreVerticali(v, voci(g).map((q) => q.colore), max, alto, neg, valoriIniziali(x, g));
      }
      if (!dis) continue;
      immagine(id, dis);
      features.push({ type: "Feature", geometry: { type: "Point", coordinates: [x.lon, x.lat] },
        properties: { img: id, imgOb: conOb, r: rAnello, nome: x.nome, cod: x.cod || "", storica: !!x.storica, burden: modo === "burden", neg, anello: modo === "emissioni" } });
    }
    // regione con la richiesta solo regionale: le province non hanno dati
    if (st.regione && g === "richiesta") messaggio("messaggio-mappa", "Terna pubblica la richiesta di energia solo per regione: le province non hanno barre.");
    else messaggio("messaggio-mappa", "");
    m.getSource("el-barre").setData({ type: "FeatureCollection", features });
    st.barre = features.length;
    st.anelli = features.filter((f) => f.properties.anello).length;   // per le prove
    m.setLayoutProperty("el-barre", "icon-anchor", modo === "emissioni" || neg ? "center" : "bottom");
    st.cerchi = modo === "emissioni" ? features.map((f) => ({ cod: f.properties.cod, nome: f.properties.nome, c: f.geometry.coordinates, r: f.properties.r })) : null;   // per le prove
    mostraObiettivo(st.obiettivoSu);
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
    window.EUGENIO_ELETTRICITA = { stato: st, scegliRegione, togliRegione, cambiaModo, periodo, INGRANDISCI, mostraObiettivo,   // per le prove
      cerchi: () => (st.cerchi || []).map((q) => { const p = m.project(q.c); return { cod: q.cod, nome: q.nome, x: p.x, y: p.y, r: q.r }; }) };
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
    // (22/11/2026) obiettivo 2030 del burden sharing: solo sulla regione sotto il mouse (filtro sul codice)
    m.addLayer({ id: "el-obiettivi", type: "symbol", source: "el-barre", filter: ["==", ["get", "cod"], "-"],
      layout: { "icon-image": ["get", "imgOb"], "icon-allow-overlap": true, "icon-ignore-placement": true, "icon-anchor": "bottom" } });
    // tipo dell'ultimo puntatore: dopo un tocco il browser manda anche mousemove e click «di compatibilità», che qui
    // non devono contare come mouse
    const tipo = (e) => { st.puntatore = e.pointerType || "mouse"; };
    m.getCanvasContainer().addEventListener("pointerdown", tipo, true);
    m.getCanvasContainer().addEventListener("pointermove", tipo, true);
    m.on("mousemove", (e) => {
      if (st.puntatore === "touch") return;
      if (st.modo !== "burden" || st.regione) return mostraObiettivo(null);
      const f = m.queryRenderedFeatures(e.point, { layers: ["el-barre", "confini-regioni-clic"].filter((id) => m.getLayer(id)) })[0];
      mostraObiettivo(f ? f.properties.cod : null);
    });
    m.on("mouseout", () => { if (st.puntatore !== "touch") mostraObiettivo(null); });
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
    // (22/11/2026) margine in alto per le colonne più alte (Lombardia): l'Italia intera sta sotto
    m.fitBounds([[C.ITALIA[0], C.ITALIA[1]], [C.ITALIA[2], C.ITALIA[3]]], { padding: margini(10), duration: 0 });
    const q = new URLSearchParams(location.search);
    if (q.get("modo") && MODI[q.get("modo")]) cambiaModo(q.get("modo"), false);
    if (/^\d\d$/.test(q.get("regione") || "") && q.get("vista") !== "italia" && D().regioni.some((r) => r.cod === q.get("regione"))) await scegliRegione(q.get("regione"));
    else { await disegnaBarre(); pannello(); }
    st.pronto = true;
    document.addEventListener("eugenio:aspetto", () => { m.setPaintProperty("sfondo", "background-color", css("--carta", "#f4f4f4")); pannello(); });
  }

  // margini dell'inquadratura: in alto l'altezza delle colonne più alte (al più il 40 % della mappa), altrove p
  function margini(p) {
    const alto = Math.round((st.regione ? 90 : 70) * INGRANDISCI * 0.85), H = box.clientHeight || 600;
    return { top: Math.max(p, Math.min(alto, Math.round(H * 0.4))), bottom: p, left: p, right: p };
  }
  // rettangolo dell'obiettivo 2030 della regione cod (null = nessuno); solo con il burden sharing e la vista dell'Italia
  function mostraObiettivo(cod) {
    st.obiettivoSu = st.modo === "burden" && !st.regione && cod ? cod : null;
    if (st.mappa && st.mappa.getLayer("el-obiettivi")) st.mappa.setFilter("el-obiettivi", ["==", ["get", "cod"], st.obiettivoSu || "-"]);
  }
  function strati() {
    const m = st.mappa, vis = (id, on) => { if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", on ? "visible" : "none"); };
    vis("el-barre", $("strato-barre").checked);
    vis("el-obiettivi", $("strato-barre").checked);
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
    // (22/11/2026) burden sharing col dito: il primo tocco su una regione mostra il suo obiettivo (e il riquadretto),
    // il secondo apre le province
    const tocco = st.puntatore === "touch" || (e.originalEvent && e.originalEvent.pointerType === "touch");
    if (tocco && st.modo === "burden" && !st.regione && st.obiettivoSu !== cod) { mostraObiettivo(cod); return; }
    if (st.regione === cod) togliRegione(); else scegliRegione(cod);
  }

  async function scegliRegione(cod) {
    if (!D().regioni.some((r) => r.cod === cod)) return;
    st.regione = cod;
    if (E && E.seleziona) E.seleziona(cod);
    const m = st.mappa;
    if (m.getLayer("confini-regione-scelta")) m.setFilter("confini-regione-scelta", ["==", ["get", "cod"], cod]);
    const b = await C.riquadroRegione(cod);
    if (b && st.regione === cod) m.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: margini(30), duration: 600 });
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
    m.fitBounds([[C.ITALIA[0], C.ITALIA[1]], [C.ITALIA[2], C.ITALIA[3]]], { padding: margini(10), duration: 600 });
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
    return { titolo: `${x.nome}${x.storica ? " (provincia soppressa)" : ""} – ${testoP()}`, righe, cursore: true };
  }
  let cacheProv = null;
  function righeValori(x) {
    const a = st.anno, dal = conPeriodo() ? st.inizio : null;
    if (st.modo === "burden") {
      const ag = aggiunta(x, a), ob = obiettivo(x, a), v30 = verso2030(x, a), ag0 = dal ? aggiunta(x, dal) : null;
      if (!ag) return ["nessun dato"];
      // (21/11/2026) in cima obiettivo 2030, percentuale raggiunta e potenza che manca: anche sull'area vuota della barra
      const r = v30 ? righe2030(v30) : [];
      if (ob !== null) r.push(["#111", `obiettivo ${a}: ${num(ob)} MW`]);
      r.push([null, `rinnovabili in più dal 2020: ${num(ag.netto)} MW${ob ? ` (${num(100 * ag.netto / ob)} % dell'obiettivo ${a})` : ""}`]);
      if (ag0) r.push([null, `variazione dal ${dal}: ${segno(ag.netto - ag0.netto)} MW`]);
      ag.parti.forEach((q, i) => r.push([colore("capacita", q.id), `${voci("capacita").find((v) => v.id === q.id).nome}: ${num(q.v, dec(q.v))} MW${ag0 ? ` (${segno(q.v - ag0.parti[i].v, dec(q.v - ag0.parti[i].v))} dal ${dal})` : ""}`]));
      return r;
    }
    const g = MODI[st.modo].grandezza, v = valoriP(x, g), v0 = valoriIniziali(x, g);
    if (!v) return [conPeriodo() ? "nessun dato per questo periodo" : "nessun dato per quest'anno"];
    const d = (i) => (v0 ? ` (${segno(v[i] - v0[i], dec(v[i] - v0[i]))} dal ${dal})` : "");
    const r = voci(g).map((q, i) => [q.colore, `${q.nome}: ${num(v[i], dec(v[i]))} ${unita(g)}${d(i)}`]).filter((_, i) => v[i] || (v0 && v0[i]));
    r.push([null, `Totale: ${num(somma(v), 0)} ${unita(g)}${v0 ? ` (${segno(somma(v) - somma(v0))} dal ${dal})` : ""}`]);
    if (flusso() && conPeriodo()) r.unshift([null, `Somma degli anni ${testoP()}`]);
    if (st.modo === "emissioni") {
      // i fattori sono della regione (Terna pubblica le emissioni solo per regione); con un periodo rapporto delle somme
      const reg = x.indicatori ? x : D().regioni.find((q) => q.cod === st.regione), ind = indRegioneP(reg);
      if (ind) {
        const di = x.indicatori ? "" : ` (${reg.nome})`;
        r.push([null, `Fattore medio${di}: ${num(ind[IND.medio], 3)} tCO₂/MWh`], [null, `Fattore del termoelettrico${di}: ${num(ind[IND.ftermo], 3)} tCO₂/MWh`],
          [null, `Energia primaria del termoelettrico${di}: ${num(ind[IND.tepmwh], 3)} tep/MWh`]);
      }
    }
    return r;
  }

  // ------------------------------------------------------------------ comandi
  function preparaComandi() {
    document.querySelectorAll("#modo-elettricita [data-modo]").forEach((b) => b.addEventListener("click", () => cambiaModo(b.dataset.modo, true)));
    if (!EM() || !anniDi("emissioni").length) { const b = document.querySelector('#modo-elettricita [data-modo="emissioni"]'); if (b) b.hidden = true; delete MODI.emissioni; }
    // cursore del periodo: componente comune cursore_periodo.js (come in Suolo e aree agricole)
    st.cursore = window.EUGENIO_PERIODO.crea({ inizio: $("anno-inizio"), fine: $("anno-fine"), doppio: $("cursore-doppio"),
      min: $("anno-min"), max: $("anno-max"), etichetta: $("periodo-scelto"),
      cambia: async (a, b, finale) => { st.inizio = a; st.fine = b; st.anno = b; if (finale && st.mappa) { await disegnaBarre(); pannello(); } } });
    $("torna-italia").addEventListener("click", () => togliRegione());
    cambiaModo("capacita", false);
  }
  // periodo valido per la grandezza (anni della lista, inizio ≤ fine; predefinito l'ultimo anno per tutti e due)
  function applicaPeriodo(a, b) { [st.inizio, st.fine] = st.cursore.imposta(anniDi(st.modo), a, b); st.anno = st.fine; }
  async function periodo(a, b) { applicaPeriodo(a, b); await disegnaBarre(); pannello(); }   // per le prove
  // collegamento a questa simulazione (20/11/2026): regione, vista e modo li scrive già aggiornaIndirizzo(); qui il periodo
  // (gli anni veri, non la posizione dei cursori: inizio e fine) e, con data-collegamento, le caselle barre, fondo e
  // ortofoto. I collegamenti di prima del 22/11/2026 con un solo anno (anno=2020) aprono il periodo 2020–2020.
  if (window.EUGENIO_COLLEGAMENTO) window.EUGENIO_COLLEGAMENTO.registra({
    regione: false,                    // la regione la decide la pagina (assente con vista=italia)
    chiavi: ["modo", "inizio", "fine", "anno"],
    principali: ["modo", "inizio", "fine"],
    pronto: () => st.pronto,
    leggi: () => (st.pronto ? { modo: st.modo, inizio: st.inizio, fine: st.fine, anno: null } : null),
    async applica(p) {
      let a = +p.get("inizio"), b = +p.get("fine");
      if (!a && !b && +p.get("anno")) a = b = +p.get("anno");
      if (!a && !b) return;
      if (!b) b = st.fine;
      if (!a) a = b;
      const prima = [st.inizio, st.fine];
      applicaPeriodo(a, b);
      if (st.inizio === prima[0] && st.fine === prima[1]) return;
      await disegnaBarre(); pannello();
    },
  });

  function cambiaModo(modo, ridisegna) {
    st.modo = modo;
    document.querySelectorAll("#modo-elettricita [data-modo]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.modo === modo)));
    // il periodo resta, avvicinato agli anni della grandezza; all'apertura l'ultimo anno con i dati per tutti e due
    applicaPeriodo(st.inizio, st.fine);
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
      const sp = h("span"), i = h("i"); i.style.background = "transparent"; i.style.outline = `2px solid ${ARANCIO}`; i.style.outlineOffset = "-2px";
      sp.append(i, "obiettivo 2030 (DM 21/6/2024, Tabella A)"); L.appendChild(sp);
      voceLegenda(L, "#111", `linea: obiettivo del ${st.anno}`);
      if (conPeriodo()) voceLegenda(L, "#111", `trattino: rinnovabili in più nel ${st.inizio}`);
      D().fer.forEach((id) => voceLegenda(L, colore("capacita", id), `${voci("capacita").find((v) => v.id === id).nome} in più dal 2020`));
      L.appendChild(h("span", "legenda-nota", "Il rettangolo dell'obiettivo 2030 e la linea dell'obiettivo dell'anno compaiono sulla regione sotto il mouse (col dito: primo tocco; il secondo apre le province). Colonne in scala con l'obiettivo 2030 più grande, sopra la linea di base; i valori negativi (potenza dismessa) non si disegnano ma sono nel riquadretto. La potenza in più è una stima: variazione della potenza efficiente lorda rinnovabile di Terna rispetto al 2020."));
      return;
    }
    const g = MODI[st.modo].grandezza;
    voci(g).forEach((v) => voceLegenda(L, v.colore, v.nome));
    if (conPeriodo() && !flusso()) voceLegenda(L, "#111", `trattino: valore del ${st.inizio}`);
    const somme = flusso() && conPeriodo() ? `somma degli anni ${testoP()}; ` : "";
    if (st.modo === "emissioni") {
      L.appendChild(h("span", "legenda-nota", `Anelli: produzione lorda per fonte (${somme}fattori come rapporto delle somme); l'area cresce in proporzione alla produzione (scala comune a ${st.regione ? "le province della regione" : "tutte le regioni"} e a tutti gli anni, con un anello minimo). ${st.regione ? "I fattori di emissione restano quelli della regione: Terna pubblica le emissioni solo per regione." : "Nel buco: fattore di emissione medio della regione (tCO₂/MWh)."}`));
      return;
    }
    L.appendChild(h("span", "legenda-nota", `Barre in ${unita(g)} (${somme || (conPeriodo() ? `anno ${st.fine}, trattino al ${st.inizio}; ` : "")}scala con il valore più alto fra ${st.regione ? "le province della regione" : "tutte le regioni"} in tutti gli anni${somme ? " e nel periodo scelto" : ""})${g === "richiesta" ? "; sotto la linea i valori negativi (saldo esportato, pompaggi)" : ""}.`));
  }
  function opzioniImmagine() {
    if (!D()) return "Dati non ancora caricati.";
    const ro = righeOrto();
    if (ro === null) return `«${orto.fonte.nome}» è solo in consultazione dal vivo: per scaricare l'immagine spegni la casella «Ortofoto».`;
    const nomeReg = st.regione ? D().regioni.find((r) => r.cod === st.regione).nome : "Italia";
    const g = MODI[st.modo].grandezza;
    const leg = st.modo === "emissioni"
      ? `Anelli: produzione lorda per fonte${conPeriodo() ? ` sommata sugli anni ${testoP()} (fattori come rapporto delle somme)` : ""} (${voci(g).map((v) => v.nome.toLowerCase()).join(", ")}); l'area cresce in proporzione alla produzione, con un anello minimo; ${st.regione ? "fattori di emissione solo regionali" : "nel buco il fattore di emissione medio della regione (tCO₂/MWh: emissioni di CO₂ del termoelettrico / produzione lorda senza pompaggi e accumuli)"}.`
      : st.modo === "burden"
      ? `${st.obiettivoSu ? `Rettangolo arancione (${D().regioni.find((r) => r.cod === st.obiettivoSu).nome}): ` : "Rettangolo arancione (solo sulla regione indicata col mouse): "}obiettivo 2030 di potenza rinnovabile aggiuntiva rispetto al 2020 (${D().obiettivi_fonte}); linea nera: obiettivo del ${st.anno}; colonna colorata: potenza rinnovabile in più rispetto al 2020 per fonte, solo le parti positive${conPeriodo() ? `; trattino nero: valore del ${st.inizio}` : ""} (${D().fer.map((id) => voci("capacita").find((v) => v.id === id).nome.toLowerCase()).join(", ")}), stima EuGEnio dalla potenza efficiente lorda di Terna.`
      : `Barre (${unita(g)}${flusso() && conPeriodo() ? `, somma degli anni ${testoP()}` : ""}), da sinistra: ${voci(g).map((v) => v.nome.toLowerCase()).join(", ")}; scala comune a ${st.regione ? "tutte le province della regione" : "tutte le regioni"} e a tutti gli anni.${conPeriodo() && !flusso() ? ` Trattino nero: valore del ${st.inizio}.` : ""}`;
    const righe = [leg, `Dati: ${D().fonte}.`, ...ro, C.ATTRIBUZIONE];
    const nome = `elettricita_${st.modo}_${testoP().replace("–", "_")}_${nomeReg.toLowerCase().replace(/[^a-z0-9]+/g, "_")}`;
    return { titolo: `${MODI[st.modo].nome} – ${nomeReg} – ${testoP()}`, righe, nome };
  }

  // ------------------------------------------------------------------ pannello di destra
  async function pannello() {
    if (!D()) return;
    const g = MODI[st.modo].grandezza, reg = st.regione ? D().regioni.find((r) => r.cod === st.regione) : null;
    $("titolo-vista").textContent = reg ? reg.nome : "Italia";
    $("torna-italia").style.display = reg ? "" : "none";
    const emi = st.modo === "emissioni";
    $("titolo-andamento").textContent = st.modo === "burden" ? `Rinnovabili in più rispetto al 2020 e obiettivi – ${reg ? reg.nome : "Italia"}`
      : emi ? `Fattori di emissione ed energia primaria – ${reg ? reg.nome : "Italia"}, anno per anno`
      : `${MODI[st.modo].nome} – ${reg ? reg.nome : "Italia"}, anno per anno`;
    // serie dell'unità scelta: Italia = somma delle regioni
    const tot = reg || totaleItalia();
    G.registra($("grafico-andamento"), (dest, mis) => (st.modo === "burden" ? graficoBurden(dest, mis, tot) : emi ? graficoEmissioni(dest, mis, reg) : graficoAndamento(dest, mis, tot, g)),
      { titolo: $("titolo-andamento").textContent, adatta: true });
    $("riquadri-emissioni").hidden = !emi;
    if (emi) riquadri(reg);
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
      $("titolo-province").textContent = st.modo === "burden" ? `Rinnovabili in più rispetto al 2020 per provincia – ${st.anno}`
        : emi ? `Produzione per provincia – ${testoP()} (le emissioni sono solo regionali)` : `${MODI[st.modo].nome} per provincia – ${flusso() ? testoP() : st.anno}`;
      G.registra($("grafico-province"), (dest, mis) => graficoUnita(dest, mis, elenco.filter((x) => (st.modo === "burden" ? aggiunta(x, st.anno) : valoriP(x, g))), g),
        { titolo: $("titolo-province").textContent, adatta: true });
    }
    $("nota-province").hidden = !senzaProv;
    if (emi) tabellaEmissioni(reg); else tabella(senzaProv ? [] : elenco, totale, tipo, reg);
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
    const cifre = passo >= 1 ? 0 : Math.min(3, (String(+passo.toFixed(6)).split(".")[1] || "").length);
    for (let i = Math.ceil(min / passo - 1e-9); i * passo <= max + 1e-9; i++) {
      const v = +(i * passo).toFixed(6);
      s("line", { x1: sx, x2: W - 6, y1: Y(v), y2: Y(v), stroke: v === 0 ? "var(--inchiostro)" : "var(--linea)", "stroke-width": v === 0 ? 1 : 0.6 }, svg);
      const t = s("text", { x: sx - 4, y: Y(v) + 4, "text-anchor": "end", "font-size": 11, fill: "var(--tenue)" }, svg); t.textContent = num(v, v === 0 ? 0 : cifre);
    }
    const t = s("text", { x: 4, y: 11, "font-size": 11, fill: "var(--tenue)" }, svg); t.textContent = unitaTesto;
    return Y;
  }
  function legendaHtml(dest, elementi) {
    const L = h("div", "legenda legenda-grafico");
    elementi.forEach(([c, t]) => voceLegenda(L, c, t));
    dest.appendChild(L);
  }
  // anni del periodo nel grafico a destra: un riquadro (colorato appena, con un periodo) dal primo all'ultimo anno
  // scelto, sopra le barre; etichette dell'anno iniziale e finale in grassetto e sempre scritte
  function periodoNelGrafico(svg, anni, X, passo, su, H, gi) {
    const dentro = anni.map((a, i) => [a, i]).filter(([a]) => nelPeriodo(a));
    if (!dentro.length) return;
    const x0 = X(dentro[0][1]) - passo / 2, x1 = X(dentro[dentro.length - 1][1]) + passo / 2;
    const r = s("rect", { x: x0, y: su, width: x1 - x0, height: H - su - gi, fill: "var(--primario)", stroke: "var(--primario)", "stroke-width": 1.2 }, svg);
    r.style.fillOpacity = conPeriodo() ? 0.1 : 0; r.style.pointerEvents = "none"; r.classList.add("periodo-scelto");
  }
  function etichettaAnno(svg, a, i, cx, H, ogni) {
    const scelto = a === st.inizio || a === st.fine;
    if (!scelto && (i % ogni || Math.abs(a - st.fine) < ogni || Math.abs(a - st.inizio) < ogni)) return;
    const t = s("text", { x: cx, y: H - 6, "text-anchor": "middle", "font-size": 11, fill: scelto ? "var(--inchiostro)" : "var(--tenue)", "font-weight": scelto ? 700 : 400 }, svg);
    t.textContent = String(a);
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
      etichettaAnno(svg, a, i, cx, H, ogni);
      return { x: cx, titolo: String(a), elementi: el, righe: [...voci(g).map((q, j) => [q.colore, `${q.nome}: ${num(v[j], dec(v[j]))} ${unita(g)}`]).filter((_, j) => v[j]),
        [null, `Totale: ${num(somma(v))} ${unita(g)}`]] };
    });
    periodoNelGrafico(svg, anni, (i) => sx + passo * (i + 0.5), passo, su, H, gi);
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
      const v30 = ag ? verso2030(x, a) : null;
      if (v30) righe.push(...righe2030(v30));
      const ob = x.obiettivi ? x.obiettivi[i] : null;
      if (ob !== null) { linea.push([cx, Y(ob)]); righe.unshift(["#111", `Obiettivo: ${num(ob)} MW${ag ? ` (raggiunto ${num(100 * ag.netto / ob)} %)` : ""}`]); }
      etichettaAnno(svg, a, i, cx, H, 1);
      return { x: cx, titolo: String(a), elementi: el, righe, segni: ob !== null ? [[cx, Y(ob), "#111"]] : [] };
    });
    if (linea.length) s("polyline", { points: linea.map((p) => p.join(",")).join(" "), fill: "none", stroke: "var(--inchiostro)", "stroke-width": 2, "stroke-dasharray": "5 3" }, svg);
    linea.forEach(([cx, cy]) => s("circle", { cx, cy, r: 2.8, fill: "var(--inchiostro)" }, svg));
    periodoNelGrafico(svg, anniOb, (i) => sx + passo * (i + 0.5), passo, su, H, gi);
    G.osserva(svg, punti, { area: [sx, su, W - 8, H - gi], guida: false });
    legendaHtml(dest, [[css("--inchiostro", "#111"), x.obiettivi ? "obiettivo (DM 21/6/2024, Tabella A)" : "nessun obiettivo per le province"],
      ...D().fer.map((id) => [colore("capacita", id), voci("capacita").find((v) => v.id === id).nome])]);
  }
  // ------------------------------------------------------------------ emissioni: riquadri, grafico e tabella
  const COL_EM = () => ({ medio: css("--serie-2", "#1f6fb4"), ftermo: css("--serie-1", "#c43c12"), tep: css("--serie-5", "#4f7f22") });
  const scarto = (v, rif) => { if (v === null || !rif) return ""; const d = Math.round(100 * (v / rif - 1)); return ` (EuGEnio ${d > 0 ? "+" : ""}${num(d === 0 ? 0 : d, 0)} %)`; };
  function riquadri(reg) {
    // con un periodo: valori EuGEnio come rapporto delle somme; ISPRA come media dei fattori annuali pesata sulla produzione
    // lorda di Terna (sul termoelettrico per i fattori del termoelettrico), solo se ISPRA ha tutti gli anni del periodo
    const dove = $("riquadri-emissioni"), a = testoP(), ind = indItaliaP(), rif = EM().riferimenti, mef = rif.mef;
    const anniP = anniPeriodo("emissioni"), peso = (serie, y) => (indItalia(y) || [])[/termo/.test(serie) ? IND.termo : IND.tot] || 0;
    const ispraP = (serie) => { if (!conPeriodo()) return ispra(serie, st.fine);
      let n = 0, d = 0; for (const y of anniP) { const v = ispra(serie, y); if (v === null) return null; n += v * peso(serie, y); d += peso(serie, y); }
      return d ? n / d : null; };
    const ispraTepP = () => { if (!conPeriodo()) return ispraTep(st.fine);
      let k = 0, t = 0; for (const y of anniP) { const r = ispraTep(y); if (!r) return null; k += r.ktep; t += r.ktep / r.tepmwh; }
      return t ? { ktep: k, tepmwh: k / t } : null; };
    const media = conPeriodo() ? " (media pesata)" : "";
    dove.innerHTML = "";
    dove.appendChild(h("h3", null, `Valori nazionali – ${a}`));
    if (!ind) { dove.appendChild(h("p", "aiuto", `Nessun dato di emissione per ${conPeriodo() ? "il periodo" : "il"} ${a}.`)); return; }
    const box = h("div", "cifre cifre-emissioni"), pre = anniP.some((y) => rif.ispra.preliminari.includes(String(y))) ? (conPeriodo() ? " (con anni preliminari)" : " (preliminare)") : "";
    const indR = reg ? indRegioneP(reg) : null;
    const cifra = (chiave, v, d, u, testo, note) => {
      const c = h("div", "cifra"); c.dataset.cifra = chiave;
      const b = h("b", null, v === null ? "–" : num(v, d)); b.appendChild(h("small", null, ` ${u}`)); c.append(b, h("span", null, testo));
      note.filter(Boolean).forEach((n) => c.appendChild(h("small", null, n)));
      box.appendChild(c);
    };
    const isp = (serie, nome) => { const v = ispraP(serie); return v === null ? `ISPRA: nessun valore ${nome} per ${conPeriodo() ? "tutti gli anni del periodo" : `il ${a}`}` : `ISPRA ${a}${pre}${media}, ${nome}: ${num(v, 3)} tCO₂/MWh`; };
    cifra("tep", ind[IND.tepmwh], 3, "tep/MWh", "Energia primaria del termoelettrico (stima EuGEnio)", [
      `MEF/MASE: ${num(mef.valore, 3)} tep/MWh${scarto(ind[IND.tepmwh], mef.valore)}`,
      ispraTepP() ? `ISPRA ${a}${pre}: ${num(ispraTepP().tepmwh, 3)} tep/MWh (${num(ispraTepP().ktep / 1000, 2)} Mtep)${scarto(ind[IND.tepmwh], ispraTepP().tepmwh)}` : `ISPRA: nessun consumo di energia per ${conPeriodo() ? "tutti gli anni del periodo" : `il ${a}`}`,
      `Stima EuGEnio: ${num(ind[IND.tep] / 1e6, 2)} Mtep`,
      indR && `${reg.nome}: ${num(indR[IND.tepmwh], 3)} tep/MWh`]);
    cifra("medio", ind[IND.medio], 3, "tCO₂/MWh", "Fattore di emissione medio (produzione lorda)", [
      isp("produzione", "produzione lorda") + scarto(ind[IND.medio], ispraP("produzione")),
      ispraP("consumi") !== null && `ISPRA ${a}${pre}${media}, consumi elettrici: ${num(ispraP("consumi"), 3)} tCO₂/MWh`,
      indR && `${reg.nome}: ${num(indR[IND.medio], 3)} tCO₂/MWh`]);
    cifra("termo", ind[IND.ftermo], 3, "tCO₂/MWh", "Fattore di emissione del termoelettrico (marginale)", [
      isp("termoelettrica", "termoelettrico con le bioenergie") + scarto(ind[IND.ftermo], ispra("termoelettrica", a)),
      ispra("termoelettrica_fossili", a) !== null && `ISPRA ${a}${pre}, solo fossili: ${num(ispra("termoelettrica_fossili", a), 3)} tCO₂/MWh`,
      indR && `${reg.nome}: ${num(indR[IND.ftermo], 3)} tCO₂/MWh`]);
    dove.appendChild(box);
    const f = h("p", "aiuto fonti-riquadri");
    const link = (t, u) => { const l = h("a", null, t); l.href = u; return l; };
    f.append("Riferimenti: ", link(`MEF/MASE ${num(mef.valore, 3)} tep/MWh`, mef.url), ` – ${mef.fonte}. `, link(rif.ispra.fonte, rif.ispra.url),
      ` e file `, link(rif.ispra.excel.nome, rif.ispra.excel.url), ` (fogli «9»: fattori di emissione, Tabella 1.7 del rapporto; «23»: consumo di energia del parco termoelettrico; gCO₂/kWh convertiti in tCO₂/MWh; 2025 preliminare). Letti il ${rif.letto.split("-").reverse().join("/")}.`);
    dove.appendChild(f);
  }
  function graficoEmissioni(dest, mis, reg) {
    const W = mis && mis.larghezza ? mis.larghezza : 560, H = mis && mis.riquadro ? mis.altezza : 260;
    const anni = anniDi("emissioni"), di = (a) => (reg ? indicatoriDi(reg, a) : indItalia(a)), col = COL_EM(), mef = EM().riferimenti.mef.valore;
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": $("titolo-andamento").textContent }, dest);
    const sx = 48, gi = 22, su = 16;
    let max = mef;
    for (const a of anni) { const v = di(a); if (v) [IND.medio, IND.ftermo, IND.tepmwh].forEach((j) => { if (v[j] !== null) max = Math.max(max, v[j]); });
      if (!reg) ["produzione", "termoelettrica"].forEach((k) => { const r = ispra(k, a); if (r !== null) max = Math.max(max, r); }); }
    const Y = asseY(svg, sx, su, gi, W, H, 0, scala(max).top, "t/MWh");
    const passo = (W - sx - 8) / Math.max(1, anni.length), X = (i) => sx + passo * (i + 0.5);
    // MEF: costante
    s("line", { x1: sx, x2: W - 8, y1: Y(mef), y2: Y(mef), stroke: col.tep, "stroke-width": 1.4, "stroke-dasharray": "6 4" }, svg);
    const serie = [["medio", IND.medio], ["ftermo", IND.ftermo], ["tep", IND.tepmwh]];
    for (const [k, j] of serie) {
      const pts = anni.map((a, i) => { const v = di(a); return v && v[j] !== null ? `${X(i)},${Y(v[j])}` : null; }).filter(Boolean);
      if (pts.length) s("polyline", { points: pts.join(" "), fill: "none", stroke: col[k], "stroke-width": 2 }, svg);
    }
    // ISPRA (solo per l'Italia): punti vuoti sugli anni pubblicati
    if (!reg) for (const [k, c] of [["produzione", col.medio], ["termoelettrica", col.ftermo], ["tep", col.tep]])
      anni.forEach((a, i) => { const r = k === "tep" ? (ispraTep(a) || {}).tepmwh : ispra(k, a);
        if (r !== null && r !== undefined) s("circle", { cx: X(i), cy: Y(r), r: 3.2, fill: "var(--foglio)", stroke: c, "stroke-width": 1.6 }, svg); });
    const ogni = anni.length <= 14 ? 1 : Math.ceil(anni.length / 12);
    const punti = anni.map((a, i) => {
      const v = di(a), cx = X(i);
      etichettaAnno(svg, a, i, cx, H, ogni);
      const righe = [], segni = [];
      if (v) {
        righe.push([col.medio, `Fattore medio: ${num(v[IND.medio], 3)} tCO₂/MWh`], [col.ftermo, `Fattore del termoelettrico: ${num(v[IND.ftermo], 3)} tCO₂/MWh`],
          [col.tep, `Energia primaria del termoelettrico: ${num(v[IND.tepmwh], 3)} tep/MWh`]);
        serie.forEach(([k, j]) => { if (v[j] !== null) segni.push([cx, Y(v[j]), col[k]]); });
      }
      if (!reg) {
        const rp = ispra("produzione", a), rt = ispra("termoelettrica", a);
        if (rp !== null) righe.push([null, `ISPRA, produzione lorda: ${num(rp, 3)} tCO₂/MWh`]);
        if (rt !== null) righe.push([null, `ISPRA, termoelettrico: ${num(rt, 3)} tCO₂/MWh`]);
        if (ispraTep(a)) righe.push([null, `ISPRA, energia primaria: ${num(ispraTep(a).tepmwh, 3)} tep/MWh`]);
      }
      righe.push([null, `MEF/MASE: ${num(mef, 3)} tep/MWh`]);
      return { x: cx, titolo: String(a), righe, segni };
    });
    periodoNelGrafico(svg, anni, X, passo, su, H, gi);
    G.osserva(svg, punti, { area: [sx, su, W - 8, H - gi], guida: true });
    legendaHtml(dest, [[col.medio, "fattore medio (tCO₂/MWh)"], [col.ftermo, "fattore del termoelettrico (tCO₂/MWh)"], [col.tep, "energia primaria del termoelettrico (tep/MWh)"],
      [col.tep, `MEF/MASE ${num(mef, 3)} tep/MWh (tratteggio)`], ...(reg ? [] : [[css("--tenue", "#888"), "ISPRA 430/2026 (cerchi vuoti, colore della serie)"]])]);
  }
  function tabellaEmissioni(reg) {
    const dove = $("tabella-elettricita"), a = testoP(); dove.innerHTML = "";
    $("titolo-tabella").textContent = `Emissioni – ${a} – regioni e zone di mercato`;
    const t = h("table", "tabella-valori tabella-elettricita tabella-emissioni"), th = h("thead"), tb = h("tbody"), tf = h("tfoot");
    const trh = h("tr");
    ["Regione / zona", "Termoelettrico (GWh)", "Rinnovabili (GWh)", "Energia primaria del termoelettrico (tep)", "Emissioni (kt CO₂)",
      "Fattore medio (tCO₂/MWh)", "Fattore del termoelettrico (tCO₂/MWh)", "Energia primaria (tep/MWh)"].forEach((c) => trh.appendChild(h("th", null, c)));
    th.appendChild(trh);
    const riga = (dove2, nome, ind, cls) => {
      const tr = h("tr", cls || null); tr.appendChild(h("th", null, nome));
      const c = ind ? [num(ind[IND.termo]), num(ind[IND.fer]), num(ind[IND.tep]), num(ind[IND.co2], dec(ind[IND.co2] || 0)),
        num(ind[IND.medio], 3), num(ind[IND.ftermo], 3), num(ind[IND.tepmwh], 3)] : Array(7).fill("–");
      c.forEach((x) => tr.appendChild(h("td", null, x === "" || x === null ? "–" : x)));
      dove2.appendChild(tr); return tr;
    };
    for (const z of D().zone) {
      const regs = z.regioni.map((c) => D().regioni.find((r) => r.cod === c)).sort((p, q) => p.nome.localeCompare(q.nome, "it"));
      if (regs.length > 1) regs.forEach((r) => riga(tb, r.nome, indRegioneP(r), r.cod === (reg && reg.cod) ? "scelta" : ""));
      const tr = riga(tb, regs.length > 1 ? `Zona ${z.nome}` : `${z.nome} (regione e zona)`, indicatoriP((y) => z.indicatori[String(y)] || null),
        `riga-zona${regs.length === 1 && reg && regs[0].cod === reg.cod ? " scelta" : ""}`);
      tr.dataset.zona = z.id;
    }
    riga(tf, "Italia", indItaliaP());
    t.append(th, tb, tf);
    const sc = h("div", "tabella-scorre"); sc.dataset.titolo = $("titolo-tabella").textContent; sc.appendChild(t);
    dove.appendChild(sc);
    dove.appendChild(h("p", "aiuto", `Termoelettrico: produzione lorda delle centrali a combustibile di Terna, comprese le bioenergie (che quindi compaiono anche fra le rinnovabili). Fattore medio = emissioni / produzione lorda totale senza pompaggi e accumuli; fattore del termoelettrico = emissioni / produzione termoelettrica. Energia primaria: stima di EuGEnio dalle emissioni per combustibile (vedi «Come funziona»). Le zone di mercato sono quelle in vigore dal 2021, anche per gli anni precedenti.${conPeriodo() ? ` Periodo ${a}: produzioni, energia primaria ed emissioni sono la somma degli anni; i fattori sono il rapporto delle somme.` : ""}`));
  }

  // barre impilate per provincia nel periodo scelto (flussi sommati; stati e burden sharing all'anno finale, con la
  // variazione dall'anno iniziale nel suggerimento)
  function graficoUnita(dest, mis, elenco, g) {
    const W = mis && mis.larghezza ? mis.larghezza : 560, H = mis && mis.riquadro ? mis.altezza : 240, a = st.anno;
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": $("titolo-province").textContent }, dest);
    const sx = 56, gi = 34, su = 16;
    const burden = st.modo === "burden";
    const parti = (x) => (burden ? (aggiunta(x, a) || { parti: [] }).parti.map((p) => ({ v: p.v, c: colore("capacita", p.id), n: voci("capacita").find((v) => v.id === p.id).nome }))
      : (valoriP(x, g) || []).map((v, j) => ({ v, c: voci(g)[j].colore, n: voci(g)[j].nome })));
    const totIniziale = (x) => { if (!conPeriodo() || flusso()) return null;
      if (burden) { const ag0 = aggiunta(x, st.inizio); return ag0 ? ag0.netto : null; }
      const v0 = valori(x, g, st.inizio); return v0 ? somma(v0) : null; };
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
        righe: [...p.filter((q) => q.v).map((q) => [q.c, `${q.n}: ${num(q.v, dec(q.v))} ${burden ? "MW" : unita(g)}`]), [null, `Totale: ${num(somma(p.map((q) => q.v)))} ${burden ? "MW" : unita(g)}`],
          ...(totIniziale(x) !== null ? [[null, `Variazione dal ${st.inizio}: ${segno(somma(p.map((q) => q.v)) - totIniziale(x))} MW`]] : [])] };
    });
    G.osserva(svg, punti, { area: [sx, su, W - 8, H - gi], guida: false });
  }

  function tabella(elenco, totale, tipo, reg) {
    const dove = $("tabella-elettricita"); dove.innerHTML = "";
    const g = MODI[st.modo].grandezza, a = st.anno, dal = conPeriodo() && !flusso() ? st.inizio : null;
    $("titolo-tabella").textContent = `${st.modo === "burden" ? "Burden sharing" : MODI[st.modo].nome} – ${flusso() ? testoP() : a} – ${reg ? `province di ${reg.nome}` : "regioni"}`;
    const t = h("table", "tabella-valori tabella-elettricita"), th = h("thead"), tb = h("tbody"), tf = h("tfoot");
    const trh = h("tr"); trh.appendChild(h("th", null, tipo === "province" ? "Provincia" : "Regione"));
    let colonne;
    if (st.modo === "burden") colonne = [`Obiettivo ${a} (MW)`, "Obiettivo 2030 (MW)", ...D().fer.map((id) => `${voci("capacita").find((v) => v.id === id).nome} (MW)`), "In più dal 2020 (MW)",
      ...(dal ? [`Variazione dal ${dal} (MW)`] : []), "Mancano al 2030 (MW)", `% obiettivo ${a}`, "% obiettivo 2030"];
    else colonne = [...voci(g).map((v) => `${v.nome} (${unita(g)})`), `Totale (${unita(g)})`, ...(dal ? [`Variazione del totale dal ${dal} (${unita(g)})`] : [])];
    colonne.forEach((c) => trh.appendChild(h("th", null, c)));
    th.appendChild(trh);
    // cella con il valore e, sotto in piccolo, la variazione dall'anno iniziale (grandezze di stato con un periodo)
    const cella = (testo, delta) => { const td = h("td", null, testo); if (delta !== null && delta !== undefined) { td.appendChild(h("br")); td.appendChild(h("small", "variazione", segno(delta, dec(delta)))); } return td; };
    const riga = (x, dove2, nome) => {
      const tr = h("tr"); tr.appendChild(h("th", null, nome || `${x.nome}${x.storica ? " (soppressa)" : ""}`));
      if (st.modo === "burden") {
        const ag = aggiunta(x, a), ob = obiettivo(x, a), ob30 = x.obiettivi ? x.obiettivi[x.obiettivi.length - 1] : null, ag0 = dal ? aggiunta(x, dal) : null;
        const fer = ag ? ag.parti.map((p, i) => cella(num(p.v, dec(p.v)), ag0 ? p.v - ag0.parti[i].v : null)) : D().fer.map(() => cella("–"));
        const pc = (v) => (v === null ? "–" : `${num(v, 0)} %`);
        [cella(num(ob, dec(ob || 0))), cella(num(ob30, dec(ob30 || 0))), ...fer, cella(ag ? num(ag.netto, dec(ag.netto)) : "–"),
          ...(dal ? [cella(ag && ag0 ? segno(ag.netto - ag0.netto, dec(ag.netto - ag0.netto)) : "–")] : []),
          cella(ag && ob30 ? num(Math.max(0, ob30 - ag.netto), dec(Math.max(0, ob30 - ag.netto))) : "–"),
          cella(pc(ag && ob ? 100 * ag.netto / ob : null)), cella(pc(ag && ob30 ? 100 * ag.netto / ob30 : null))].forEach((c) => tr.appendChild(c));
      } else {
        const v = valoriP(x, g), v0 = dal ? valori(x, g, dal) : null;
        if (!v) colonne.forEach(() => tr.appendChild(cella("–")));
        else {
          v.forEach((y, i) => tr.appendChild(cella(num(y, dec(y)), v0 ? y - v0[i] : null)));
          tr.appendChild(cella(num(somma(v))));
          if (dal) tr.appendChild(cella(v0 ? segno(somma(v) - somma(v0)) : "–"));
        }
      }
      dove2.appendChild(tr);
    };
    [...elenco].sort((p, q) => p.nome.localeCompare(q.nome, "it")).forEach((x) => riga(x, tb));
    riga(totale, tf, tipo === "province" ? `Totale ${reg.nome}` : "Italia");
    t.append(th, tb, tf);
    const sc = h("div", "tabella-scorre"); sc.dataset.titolo = $("titolo-tabella").textContent; sc.appendChild(t);
    dove.appendChild(sc);
    if (flusso() && conPeriodo()) dove.appendChild(h("p", "aiuto", `Valori del periodo ${testoP()}: somma degli anni.`));
    if (dal) dove.appendChild(h("p", "aiuto", `Valori al ${a}; sotto ogni valore, in piccolo, la variazione rispetto al ${dal}.`));
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
