"use strict";
// PROPOSTA (non ancora nel sito): sezione "Il clima dal 1940" della pagina Legge 10.
// Legge i file statici prodotti da indicatori/calcola.py:
//   dati/clima/<RR>/<istat>.json          sintesi (GG per stagione, zone, tendenze, periodi, progetto)
//   dati/clima/<RR>/<istat>_mensili.json  mensili anno per anno (caricato solo se si sceglie un anno)
//   dati/clima/regioni.json               codice ISTAT -> codice regione (le cartelle sono per regione)
// Uso: EUGENIO_CLIMA.mostra(istat, contenitore, { ggDpr })
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"];
  const SOGLIE = [[600, "A|B"], [900, "B|C"], [1400, "C|D"], [2100, "D|E"], [3000, "E|F"]];
  const COLORI_ZONA = { A: "#d9822b", B: "#e3a857", C: "#c9b458", D: "#6aa5a0", E: "#2e6f95", F: "#173f5f", "-": "#999" };
  const COLONNE = [["t_media", "T media", "°C", 1], ["t_min", "T min", "°C", 1], ["t_max", "T max", "°C", 1],
    ["h_glob", "Irradiazione globale", "MJ/m² giorno", 1], ["h_dif", "di cui diffusa", "MJ/m² giorno", 1],
    ["pv", "Pressione del vapore", "Pa", 0], ["vento", "Vento", "m/s", 1]];
  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const num = (x, dec = 0) => (x === null || x === undefined || Number.isNaN(x)) ? "—"
    : Number(x).toLocaleString("it-IT", { minimumFractionDigits: dec, maximumFractionDigits: dec });
  const segno = (x, dec = 0) => (x === null || x === undefined) ? "—" : `${x > 0 ? "+" : ""}${num(x, dec)}`;
  function el(tag, attrs = {}, parent) {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    if (parent) parent.appendChild(e);
    return e;
  }
  function h(tag, cls, testo) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (testo !== undefined && testo !== null) e.textContent = testo;
    return e;
  }
  const etichettaStagione = (s) => `${s}/${String(s + 1).slice(2)}`;

  let regioni = null;   // istat -> codice regione (dati/clima/regioni.json, ~90 kB, una volta sola)
  async function regioneDi(istat) {
    if (!regioni) regioni = fetch("dati/clima/regioni.json").then((r) => r.json());
    return (await regioni)[istat];
  }
  const cacheMensili = new Map();
  async function mensili(rr, istat) {
    if (!cacheMensili.has(istat)) cacheMensili.set(istat, fetch(`dati/clima/${rr}/${istat}_mensili.json`).then((r) => {
      if (!r.ok) throw new Error(`mensili non disponibili (${r.status})`);
      return r.json();
    }));
    return cacheMensili.get(istat);
  }

  // ------------------------------------------------------------------ cifre
  function cifra(valore, etichetta, nota) {
    const d = h("div", "cifra");
    d.append(h("b", null, valore), h("span", null, etichetta));
    if (nota) d.appendChild(h("small", null, nota));
    return d;
  }

  // ------------------------------------------------------------------ grafico dei GG stagione per stagione
  function mediaMobile(v, n) {
    return v.map((_, i) => {
      if (i < n - 1) return null;
      const f = v.slice(i - n + 1, i + 1).filter((x) => x !== null);
      return f.length === n ? f.reduce((a, b) => a + b, 0) / n : null;
    });
  }
  function regressione(x, y) {
    const p = x.map((xi, i) => [xi, y[i]]).filter(([, yi]) => yi !== null);
    const n = p.length; if (n < 10) return null;
    const mx = p.reduce((a, [xi]) => a + xi, 0) / n, my = p.reduce((a, [, yi]) => a + yi, 0) / n;
    const b = p.reduce((a, [xi, yi]) => a + (xi - mx) * (yi - my), 0) / p.reduce((a, [xi]) => a + (xi - mx) ** 2, 0);
    return { b, a: my - b * mx };
  }

  function graficoGG(box, d, ggDpr) {
    box.innerHTML = "";
    const S = d.stagioni, v = S.gg_zona, x = v.map((_, i) => S.da + i);
    const W = 720, H = 260, sx = 46, dx = 10, su = 14, gi = 40;
    const validi = v.filter((q) => q !== null);
    const lo = Math.min(...validi, ggDpr ?? Infinity), hi = Math.max(...validi, ggDpr ?? -Infinity);
    const passoY = [50, 100, 250, 500].find((s) => (hi - lo) * 1.2 / s <= 6) || 500;
    const ymin = Math.max(0, Math.floor((lo - (hi - lo) * .1) / passoY) * passoY);
    const ymax = Math.ceil((hi + (hi - lo) * .1) / passoY) * passoY;
    const Y = (q) => su + (H - su - gi) * (1 - (q - ymin) / (ymax - ymin));
    const X = (i) => sx + (W - sx - dx) * (i + .5) / v.length;
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img",
      "aria-label": `Gradi giorno per stagione dalla ${etichettaStagione(S.da)} alla ${etichettaStagione(x[x.length - 1])}` }, box);
    for (let q = ymin; q <= ymax; q += passoY) {
      el("line", { x1: sx, x2: W - dx, y1: Y(q), y2: Y(q), stroke: css("--linea"), "stroke-width": .6 }, svg);
      el("text", { x: sx - 6, y: Y(q) + 4, "text-anchor": "end" }, svg).textContent = num(q);
    }
    // confini di zona del DPR 412/93 che cadono nella scala
    for (const [s, t] of SOGLIE) if (s > ymin && s < ymax) {
      el("line", { x1: sx, x2: W - dx, y1: Y(s), y2: Y(s), stroke: css("--tenue"), "stroke-width": .8, "stroke-dasharray": "1 3" }, svg);
      el("text", { x: W - dx - 2, y: Y(s) - 3, "text-anchor": "end", class: "piccolo" }, svg).textContent = `zona ${t}`;
    }
    // barre sottili: stagioni ricostruite da ERA5 (prima del 1950) più chiare
    const larg = Math.max(1.5, (W - sx - dx) / v.length * .7);
    v.forEach((q, i) => {
      if (q === null) return;
      const r = el("rect", { x: X(i) - larg / 2, y: Y(q), width: larg, height: Y(ymin) - Y(q), rx: 1,
        fill: css("--freddo"), opacity: S.fonte[i] === "L" ? .55 : .3 }, svg);
      el("title", {}, r).textContent = `${etichettaStagione(x[i])}: ${num(q)} GG, zona ${S.zona[i]}`
        + (S.fonte[i] === "L" ? "" : " (ERA5 raccordato)");
    });
    // media mobile su 10 stagioni
    const mm = mediaMobile(v, 10);
    const pts = mm.map((q, i) => q === null ? null : `${X(i)},${Y(q)}`).filter(Boolean).join(" ");
    el("polyline", { points: pts, fill: "none", stroke: css("--gelo"), "stroke-width": 2.2 }, svg);
    // tendenza lineare su tutta la serie
    const rg = regressione(x, v);
    if (rg) el("line", { x1: X(0), x2: X(v.length - 1), y1: Y(rg.a + rg.b * x[0]), y2: Y(rg.a + rg.b * x[x.length - 1]),
      stroke: css("--inchiostro"), "stroke-width": 1, "stroke-dasharray": "4 3" }, svg);
    if (ggDpr !== null && ggDpr !== undefined) {
      el("line", { x1: sx, x2: W - dx, y1: Y(ggDpr), y2: Y(ggDpr), stroke: css("--avviso"), "stroke-width": 2, "stroke-dasharray": "7 4" }, svg);
      const t = el("text", { x: sx + 6, y: Y(ggDpr) - 6 }, svg); t.textContent = `DPR 412/93 ${num(ggDpr)}`; t.style.fill = css("--avviso");
    }
    // asse delle stagioni ogni 10 anni e striscia delle zone
    x.forEach((s, i) => {
      if (s % 10 === 0) el("text", { x: X(i), y: H - gi + 16, "text-anchor": "middle" }, svg).textContent = etichettaStagione(s);
      const r = el("rect", { x: X(i) - (W - sx - dx) / v.length / 2, y: H - 14, width: (W - sx - dx) / v.length + .3, height: 10,
        fill: COLORI_ZONA[S.zona[i]] || "#999" }, svg);
      el("title", {}, r).textContent = `${etichettaStagione(s)}: zona ${S.zona[i]}`;
    });
    const leg = h("div", "legenda");
    const voce = (cl, colore, testo) => { const s = h("span"); const i = h("i", cl); i.style.color = colore;
      i.style.background = cl ? "" : colore; s.append(i, testo); leg.appendChild(s); };
    voce(null, css("--freddo"), "gradi giorno della stagione (più chiari: prima del 1950, da ERA5)");
    voce(null, css("--gelo"), "media mobile su 10 stagioni");
    voce("tratteggio", css("--inchiostro"), `tendenza: ${segno(d.tendenze.gg_per_decennio.tutta)} GG per decennio`);
    if (ggDpr !== null && ggDpr !== undefined) voce("tratteggio", css("--avviso"), `valore di legge: ${num(ggDpr)}`);
    leg.appendChild(h("span", null, "striscia in basso: zona climatica che risulterebbe da ogni stagione"));
    box.appendChild(leg);
  }

  // ------------------------------------------------------------------ temperature di progetto (finestre mobili)
  function graficoProgetto(box, p) {
    box.innerHTML = "";
    if (!p.fine.length) return;
    const W = 720, H = 200, sx = 46, dx = 10, su = 12, gi = 26;
    const tutte = [...p.inv, ...p.est].filter((q) => q !== null);
    const lo = Math.floor(Math.min(...tutte) / 5) * 5 - 5, hi = Math.ceil(Math.max(...tutte) / 5) * 5 + 5;
    const Y = (q) => su + (H - su - gi) * (1 - (q - lo) / (hi - lo));
    const X = (i) => sx + (W - sx - dx) * i / Math.max(1, p.fine.length - 1);
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Temperature di progetto su finestre di 10 anni" }, box);
    for (let q = lo; q <= hi; q += 5) {
      el("line", { x1: sx, x2: W - dx, y1: Y(q), y2: Y(q), stroke: css("--linea"), "stroke-width": .6 }, svg);
      el("text", { x: sx - 6, y: Y(q) + 4, "text-anchor": "end" }, svg).textContent = `${q}°`;
    }
    for (const [serie, colore] of [[p.inv, css("--freddo")], [p.est, css("--avviso")]])
      el("polyline", { fill: "none", stroke: colore, "stroke-width": 2,
        points: serie.map((q, i) => q === null ? null : `${X(i)},${Y(q)}`).filter(Boolean).join(" ") }, svg);
    p.fine.forEach((a, i) => { if (a % 10 === 0) el("text", { x: X(i), y: H - 8, "text-anchor": "middle" }, svg).textContent = `${a - 9}–${String(a).slice(2)}`; });
    const leg = h("div", "legenda");
    leg.append(h("span", null, `invernale (1° percentile dei minimi giornalieri), ultima finestra ${num(p.inv[p.inv.length - 1], 1)} °C`),
      h("span", null, `estiva (99° percentile dei massimi), ultima finestra ${num(p.est[p.est.length - 1], 1)} °C`));
    box.appendChild(leg);
  }

  // ------------------------------------------------------------------ tabella mensile: periodo o anno
  function righeTabella(t, valori) {   // valori: {var: [12 numeri]}
    t.innerHTML = "";
    const testa = t.createTHead().insertRow();
    testa.appendChild(h("th", null, "Mese"));
    for (const [, nome, unita] of COLONNE) { const th = h("th", "num", nome); th.appendChild(h("small", null, unita)); testa.appendChild(th); }
    const corpo = t.createTBody();
    for (let m = 0; m < 12; m++) {
      const r = corpo.insertRow();
      r.appendChild(h("th", null, MESI[m]));
      for (const [k, , , dec] of COLONNE) r.appendChild(h("td", "num", num(valori[k][m], dec)));
    }
  }
  async function tabellaMensile(t, sel, rr, d) {
    const v = sel.value;
    if (v.startsWith("p:")) return righeTabella(t, d.periodi[v.slice(2)].mensili);
    const anno = Number(v.slice(2)), M = await mensili(rr, d.istat), i = anno - M.da;
    const valori = {};
    for (const [k] of COLONNE) valori[k] = M[k].slice(i * 12, i * 12 + 12).map((q) => q === null ? null : q / M.scala[k]);
    righeTabella(t, valori);
  }

  // ------------------------------------------------------------------ sezione completa
  async function mostra(istat, box, { ggDpr = null } = {}) {
    box.innerHTML = "";
    const rr = await regioneDi(istat);
    const r = await fetch(`dati/clima/${rr}/${istat}.json`);
    if (!r.ok) { box.appendChild(h("p", "aiuto", "Serie storica non disponibile per questo comune.")); return; }
    const d = await r.json();
    const S = d.stagioni, n = S.gg_zona.length, T = d.tendenze, c = d.confronto_dpr || {};
    if (ggDpr === null && c.gg_dpr) ggDpr = c.gg_dpr;
    box.appendChild(h("h3", null, `Il clima dal ${S.prima.split("/")[0]}: ${n} stagioni di riscaldamento`));
    const cifre = h("div", "cifre");
    cifre.append(
      cifra(num(T.media_10), "GG medi delle ultime 10 stagioni", c.diff_10_pct !== undefined ? `${segno(c.diff_10_pct, 1)} % rispetto al DPR` : null),
      cifra(num(T.media_30), "GG medi delle ultime 30 stagioni", c.diff_30_pct !== undefined ? `${segno(c.diff_30_pct, 1)} % rispetto al DPR` : null),
      cifra(segno(T.gg_per_decennio.tutta), "GG per decennio", `regressione su tutte le stagioni; dal 1981: ${segno(T.gg_per_decennio.dal_1981)}`),
      cifra(`${segno(T.t_media_annua_per_decennio, 2)} °C`, "temperatura media annua per decennio", null),
    );
    if (c.dpr_aggiornato_10) cifre.appendChild(cifra(num(c.dpr_aggiornato_10), "GG del DPR aggiornati alle ultime 10 stagioni",
      `GG di legge × variazione della serie rispetto al ${c.riferimento_rapporto}: zona ${c.zona_aggiornata_10}`));
    box.appendChild(cifre);
    const g1 = h("div", "grafico"); box.appendChild(g1); graficoGG(g1, d, ggDpr);
    box.appendChild(h("p", "aiuto", `GG sul periodo di accensione della zona ${d.zona_riferimento} (${d.origine_zona}). `
      + "Le stagioni vanno dal 1° luglio al 30 giugno."));
    // tabella mensile
    box.appendChild(h("h3", null, "Dati mensili di un periodo o di un anno"));
    const lab = h("label", null, "Periodo"); lab.htmlFor = "clima-periodo";
    const sel = h("select"); sel.id = "clima-periodo";
    const gP = document.createElement("optgroup"); gP.label = "Medie di periodo";
    for (const k of Object.keys(d.periodi)) { const o = h("option", null, k); o.value = `p:${k}`; gP.appendChild(o); }
    const gA = document.createElement("optgroup"); gA.label = "Un anno";
    const ultimo = Number(Object.keys(d.periodi).slice(-1)[0].split("-")[1]);
    for (let a = ultimo; a >= S.da + 1; a--) { const o = h("option", null, String(a)); o.value = `a:${a}`; gA.appendChild(o); }
    sel.append(gP, gA);
    sel.value = `p:${Object.keys(d.periodi).slice(-1)[0]}`;
    const t = h("table", "mensili"), sc = h("div", "tabella-scorre"); sc.appendChild(t);
    box.append(lab, sel, sc);
    sel.addEventListener("change", () => tabellaMensile(t, sel, rr, d).catch((e) => { t.innerHTML = ""; t.textContent = e.message; }));
    await tabellaMensile(t, sel, rr, d);
    // periodi: confronto in una riga per periodo
    box.appendChild(h("h3", null, "Gradi giorno e temperature di progetto per periodo"));
    const tp = h("table", "mensili"), r0 = tp.createTHead().insertRow();
    for (const [x, cl] of [["Periodo", null], ["GG zona", "num"], ["GG anno", "num"], ["Zona", "num"], ["θ inv. °C", "num"], ["θ est. °C", "num"]]) r0.appendChild(h("th", cl, x));
    const corpo = tp.createTBody();
    for (const [k, p] of Object.entries(d.periodi)) {
      const r = corpo.insertRow(); r.appendChild(h("th", null, k));
      r.append(h("td", "num", num(p.gg_zona)), h("td", "num", num(p.gg_anno)), h("td", "num", p.zona || "—"),
        h("td", "num", num(p.theta_inv, 1)), h("td", "num", num(p.theta_est, 1)));
    }
    if (c.gg_dpr) { const r = corpo.insertRow(); r.appendChild(h("th", null, "DPR 412/93"));
      r.append(h("td", "num", num(c.gg_dpr)), h("td", "num", "—"), h("td", "num", c.zona_dpr), h("td", "num", "—"), h("td", "num", "—")); }
    const sp = h("div", "tabella-scorre"); sp.appendChild(tp); box.appendChild(sp);
    box.appendChild(h("h3", null, "Temperature di progetto su finestre mobili di 10 anni"));
    const g2 = h("div", "grafico"); box.appendChild(g2); graficoProgetto(g2, d.progetto);
    const f = h("p", "fonti");
    const a = h("a", null, "Weather data by Open-Meteo.com"); a.href = "https://open-meteo.com/";
    f.append(a, " (CC BY 4.0), da ERA5 ed ERA5-Land senza correzione verso ICON. Contiene informazioni modificate del "
      + "Copernicus Climate Change Service. Valori dal clima ricostruito: non sostituiscono quelli normativi.");
    box.appendChild(f);
  }

  window.EUGENIO_CLIMA = { mostra };
})();
