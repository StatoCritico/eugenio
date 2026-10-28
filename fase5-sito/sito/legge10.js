"use strict";
// Dati climatici per la Legge 10: scelta del comune (mappa o elenco) → /api/clima-legge10/{istat},
// accanto ai valori di legge dell'Allegato A del DPR 412/93 (dati/dpr412.json, file statico del sito).
const API = "/api";
const $ = (id) => document.getElementById(id);
const NS = "http://www.w3.org/2000/svg";
const MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"];
const REGIONE = (window.EUGENIO && window.EUGENIO.regione) || (new URLSearchParams(location.search).get("regione") || "08").replace(/\D/g, "").padStart(2, "0");
const stato = { comuni: new Map(), percorsi: new Map(), istat: null, dati: null, svg: null, richiesta: 0, dpr: null };
const DPR_URL = "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.del.presidente.della.repubblica:1993-08-26;412!vig=";
const ZONE = ["A", "B", "C", "D", "E", "F"];

function el(tag, attrs = {}, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) {
    // colori "var(--…)": nello stile, così seguono da soli il cambio di tema o di vestito
    if ((k === "fill" || k === "stroke") && typeof v === "string" && v.startsWith("var(")) e.style.setProperty(k, v);
    else e.setAttribute(k, v);
  }
  if (parent) parent.appendChild(e);
  return e;
}
function h(tag, cls, testo) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (testo !== undefined && testo !== null) e.textContent = testo;
  return e;
}
const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const num = (x, dec = 0) => (x === null || x === undefined || Number.isNaN(x)) ? "—"
  : Number(x).toLocaleString("it-IT", { minimumFractionDigits: dec, maximumFractionDigits: dec });
function messaggio(t, errore = false) { const m = $("messaggio"); m.textContent = t; m.classList.toggle("errore", errore); }

// ------------------------------------------------------------------ mappa e scelta del comune
async function caricaMappa() {
  const r = await fetch(`dati/mappa/${REGIONE}.json`);
  if (!r.ok) throw new Error(`mappa non disponibile (${r.status})`);
  const m = await r.json();
  const svg = el("svg", { viewBox: m.viewBox.join(" "), role: "img", "aria-label": "Mappa dei comuni" });
  $("mappa").prepend(svg);
  const g = el("g", {}, svg);
  for (const c of m.comuni) {
    const p = el("path", { d: c.d, fill: (window.EUGENIO && window.EUGENIO.fondoComuni ? window.EUGENIO.fondoComuni(REGIONE) : "var(--linea)") }, g);
    el("title", {}, p).textContent = c.nome;
    p.addEventListener("click", () => scegli(c.istat));
    p.addEventListener("mousemove", (e) => etichetta(e, c.nome));
    p.addEventListener("mouseleave", () => ($("etichetta").style.display = "none"));
    stato.percorsi.set(c.istat, p);
    stato.comuni.set(c.istat, c);
  }
  if (m.province) {   // confini provinciali sopra i comuni, senza intercettare i clic
    const gp = el("g", { class: "province" }, svg);
    for (const pr of m.province) el("title", {}, el("path", { d: pr.d }, gp)).textContent = pr.nome;
  }
  if (window.EUGENIO) {   // Italia intera sotto, confini regionali sopra, zoom e trascinamento
    window.EUGENIO.sfondoItalia(svg).catch(() => {});
    stato.zoom = window.EUGENIO.mappaGrande(svg, m.viewBox);
  }
  stato.svg = svg;
  const sel = $("comune");
  [...m.comuni].sort((a, b) => a.nome.localeCompare(b.nome, "it")).forEach((c) => {
    const o = document.createElement("option"); o.value = c.istat; o.textContent = `${c.nome} (${c.prov})`; sel.appendChild(o);
  });
  sel.addEventListener("change", () => sel.value && scegli(sel.value));
  const dalLink = new URLSearchParams(location.search).get("comune");
  if (dalLink && stato.comuni.has(dalLink)) scegli(dalLink);
}

function etichetta(e, testo) {
  const et = $("etichetta"), box = $("mappa").getBoundingClientRect();
  et.textContent = testo;
  et.style.display = "block";
  et.style.left = `${Math.min(e.clientX - box.left + 12, box.width - et.offsetWidth)}px`;
  et.style.top = `${e.clientY - box.top + 12}px`;
}

function scegli(istat) {
  if (!stato.comuni.has(istat)) return;
  stato.istat = istat;
  stato.percorsi.forEach((p) => p.classList.remove("scelto"));
  const p = stato.percorsi.get(istat);
  p.classList.add("scelto"); p.parentNode.appendChild(p);
  $("comune").value = istat;
  const u = new URL(location.href);
  u.searchParams.set("comune", istat);
  history.replaceState(null, "", u);
  calcola();
}
$("anni").addEventListener("change", () => stato.istat && calcola());

// Allegato A del DPR 412/93: un solo file per tutta Italia, caricato una volta. Se manca, la pagina
// funziona lo stesso senza il confronto.
let tabellaDPR = null;
function caricaDPR() {
  if (!tabellaDPR) tabellaDPR = fetch("dati/dpr412.json?v=20261028e")
    .then((r) => (r.ok ? r.json() : null)).catch(() => null);
  return tabellaDPR;
}
function valoriDPR(tab, istat) {
  const v = tab && tab.comuni && tab.comuni[istat];
  if (!Array.isArray(v)) return null;
  const [gg, zona, alt, nome, nota, origini] = v;
  return { gg, zona, alt, nome: nome || "", nota: nota || "",
    origini: (origini || []).map(([g, z, a, n]) => ({ nome: n, gg: g, zona: z, alt: a })) };
}

// serie dal 1940 (file statici, indipendenti dall'API): compare anche se il calcolo sulle ultime stagioni non risponde
async function storico() {
  const box = $("clima-storico"), passo = $("passo-storico");
  if (!box || !window.EUGENIO_CLIMA) return;
  passo.hidden = false;
  try {
    stato.dpr = valoriDPR(await caricaDPR(), stato.istat);
    await window.EUGENIO_CLIMA.mostra(stato.istat, box, { ggDpr: stato.dpr && Number.isFinite(stato.dpr.gg) ? stato.dpr.gg : null });
  } catch { passo.hidden = true; }
}

// indicatori dagli anni tipo del CTI (file statici): compaiono anche se il calcolo sulle ultime stagioni non risponde
async function annoTipo() {
  const box = $("anno-tipo-cti"), passo = $("passo-cti");
  if (!box || !window.EUGENIO_CTI) return;
  const istat = stato.istat;
  try {
    const dpr = valoriDPR(await caricaDPR(), istat);
    const ok = await window.EUGENIO_CTI.mostra(box, { istat, regione: REGIONE, dpr });
    if (istat === stato.istat) passo.hidden = !ok;
  } catch { passo.hidden = true; }
}

async function calcola() {
  const n = ++stato.richiesta;      // se si cambia comune prima della risposta, vale l'ultima richiesta
  messaggio("Calcolo in corso…");
  try {
    const [r, tab] = await Promise.all([fetch(`${API}/clima-legge10/${stato.istat}?anni=${$("anni").value}`), caricaDPR()]);
    let d = null;
    try { d = await r.json(); } catch { /* risposta non JSON */ }
    if (!r.ok) throw new Error((d && d.detail) || `errore ${r.status}`);
    if (n !== stato.richiesta) return;
    stato.dati = d;
    stato.dpr = valoriDPR(tab, stato.istat);
    messaggio("");
    mostra(d);
  } catch (e) {
    if (n !== stato.richiesta) return;
    $("passo-risultato").hidden = true;
    messaggio(`Dati delle ultime stagioni non disponibili per questo comune: ${e.message}`, true);
  }
  if (n === stato.richiesta) { annoTipo(); storico(); }
}

// ------------------------------------------------------------------ risultato
function cifra(valore, etichetta, nota, cls) {
  const d = h("div", cls ? `cifra ${cls}` : "cifra");
  d.append(h("b", null, valore), h("span", null, etichetta));
  if (nota) d.appendChild(h("small", null, nota));
  return d;
}

function mostra(d) {
  $("passo-risultato").hidden = false;
  $("titolo-comune").textContent = d.comune;
  const s = d.stagioni;
  $("periodo").textContent = `${s.length} stagioni di riscaldamento, dalla ${s[0]} alla ${s[s.length - 1]} (${num(d.giorni)} giorni).`;
  const gg = d.gradi_giorno, tp = d.temperatura_progetto;
  const tend = gg.tendenza_gg_per_decennio;
  const box = $("cifre"); box.innerHTML = "";
  box.append(
    cifra(num(gg.gg_periodo_zona), "gradi giorno", `base 20 °C, periodo di accensione della zona ${gg.zona_di_riferimento}`),
    cifra(gg.zona_risultante, "zona climatica che ne risulta", "DPR 412/93, art. 2"),
    cifra(num(gg.gg_anno_intero), "gradi giorno sull'anno intero", `da ${num(gg.minimo)} a ${num(gg.massimo)} nel periodo della zona`),
    cifra(tend === null ? "—" : `${tend > 0 ? "+" : ""}${num(tend)}`, "gradi giorno per decennio", tend === null ? "servono almeno 5 stagioni" : "tendenza sul periodo"),
    cifra(`${num(tp.invernale, 1)} °C`, "temperatura di progetto invernale", tp.metodo),
    cifra(`${num(tp.estiva, 1)} °C`, "temperatura di progetto estiva", null),
  );
  $("avvertenza").textContent = d.avvertenza;
  confrontoDPR(gg, stato.dpr);
  graficoGG(gg, stato.dpr && Number.isFinite(stato.dpr.gg) ? stato.dpr.gg : null);
  tabellaMensile(d.mensili);
  tabellaZone(gg);
  const f = $("fonti"); f.innerHTML = "";
  const a = h("a", null, "Weather data by Open-Meteo.com");
  a.href = "https://open-meteo.com/";
  f.append(`Fonte: ${d.fonte}. `, a, ".");
}

// ------------------------------------------------------------------ confronto con il DPR 412/93
function differenza(calc, legge) {
  if (!Number.isFinite(calc) || !Number.isFinite(legge) || !legge) return null;
  return Math.round(1000 * (calc - legge) / legge) / 10;
}

function confrontoDPR(gg, dpr) {
  const box = $("dpr"); box.innerHTML = "";
  box.hidden = !dpr;
  if (!dpr) return;
  box.appendChild(h("h3", null, "Il confronto con il DPR 412/93"));
  const cifre = h("div", "cifre");
  const zonaOk = ZONE.includes(dpr.zona) && ZONE.includes(gg.zona_risultante);
  if (Number.isFinite(dpr.gg)) {
    const diff = differenza(gg.gg_periodo_zona, dpr.gg);
    box.appendChild(confronto(gg.gg_periodo_zona, dpr.gg, diff));
    // gradi giorno di legge e differenza stanno nel riquadro di confronto; qui zona e altitudine
    cifre.append(
      cifra(dpr.zona || "—", "zona climatica di legge", zonaOk ? (dpr.zona === gg.zona_risultante
        ? "coincide con quella calcolata" : `quella calcolata è la ${gg.zona_risultante}`) : null, "legge"),
      cifra(Number.isFinite(dpr.alt) ? `${num(dpr.alt)} m` : "—", "altitudine della casa comunale", "come nel DPR"),
    );
  } else if (dpr.origini.length) {
    const zone = [...new Set(dpr.origini.map((o) => o.zona))].join(", ");
    cifre.append(cifra(dpr.zona || zone || "—", "zona climatica di legge",
      (dpr.zona ? "uguale per tutti i comuni d'origine" : "diversa tra i comuni d'origine")
      + (zonaOk ? (dpr.zona === gg.zona_risultante ? "; coincide con quella calcolata" : `; quella calcolata è la ${gg.zona_risultante}`) : ""), "legge"));
  }
  if (cifre.childNodes.length) box.appendChild(cifre);
  if (dpr.origini.length) {
    box.appendChild(h("p", "aiuto", Number.isFinite(dpr.gg)
      ? "Questo comune ne ha incorporati altri dopo il 1993: vale il valore del comune che li ha incorporati. I comuni incorporati nel DPR:"
      : "Il comune è nato dopo il 1993 dalla fusione di altri comuni e il DPR non ha un valore unico. I valori dei comuni d'origine:"));
    const t = h("table", "mensili");
    const r1 = t.createTHead().insertRow();
    for (const [testo, cl] of [["Comune nel DPR", null], ["GG", "num"], ["Zona", "num"], ["Alt. (m)", "num"]]) r1.appendChild(h("th", cl, testo));
    const corpo = t.createTBody();
    for (const o of dpr.origini) {
      const r = corpo.insertRow();
      r.appendChild(h("th", null, o.nome));
      r.append(h("td", "num", num(o.gg)), h("td", "num", o.zona || "—"), h("td", "num", num(o.alt)));
    }
    const s = h("div", "tabella-scorre"); s.appendChild(t); box.appendChild(s);
  } else if (!Number.isFinite(dpr.gg)) {
    box.appendChild(h("p", "aiuto", `${dpr.nota || "Il comune non è nel DPR 412/93"}. Per l'art. 2 del DPR il Sindaco adotta i gradi giorno del comune più vicino, corretti per la differenza di quota.`));
  }
  if (Number.isFinite(dpr.gg) && (dpr.nome || dpr.nota)) {
    box.appendChild(h("p", "aiuto", dpr.nota || `Nel DPR come ${dpr.nome}.`));
  }
  box.appendChild(h("p", "aiuto", "I valori del DPR 412/93 sono quelli di legge: fissati nel 1993 sul clima dei decenni "
    + "precedenti, restano quelli da usare nella relazione tecnica. Il calcolo di EuGEnio descrive invece il clima reale "
    + "delle ultime stagioni: la differenza dice quanto è cambiato e aiuta a leggere i consumi."));
  const f = h("p", "fonti");
  const a = h("a", null, "DPR 26 agosto 1993, n. 412, Allegato A");
  a.href = DPR_URL; a.rel = "noopener";
  const c = h("a", null, "Scarica i valori del DPR di tutti i comuni (CSV)");
  c.href = "dati/dpr412.csv"; c.setAttribute("download", "dpr412.csv");
  f.append("Fonte: ", a, " (testo vigente su Normattiva), abbinato ai codici ISTAT attuali. ", c, ".");
  box.appendChild(f);
}

// riquadro di confronto: gradi giorno calcolati contro quelli di legge, con la differenza e due barre in scala
function confronto(calc, legge, diff) {
  const d = h("div", "confronto");
  d.setAttribute("role", "group");
  d.setAttribute("aria-label", "Gradi giorno calcolati e di legge");
  const lato = (cls, valore, testo) => { const l = h("div", cls); l.append(h("b", null, valore), h("span", null, testo)); return l; };
  d.append(lato("lato", num(calc), "gradi giorno calcolati, ultime stagioni"),
    lato("lato legge", num(legge), "gradi giorno di legge, DPR 412/93"));
  const diffBox = h("div", "differenza");
  diffBox.append(h("b", null, diff === null ? "—" : `${diff > 0 ? "+" : ""}${num(diff, 1)} %`),
    h("span", null, diff === null ? "differenza non calcolabile" : diff < 0 ? "clima più mite del valore di legge" : "clima più freddo del valore di legge"));
  d.appendChild(diffBox);
  const barre = h("div", "barre");
  barre.setAttribute("aria-hidden", "true");
  const max = Math.max(calc, legge) || 1;
  const i1 = h("i"); i1.style.width = `${(100 * calc / max).toFixed(1)}%`;
  const i2 = h("i", "legge"); i2.style.width = `${(100 * legge / max).toFixed(1)}%`;
  barre.append(i1, i2);
  d.appendChild(barre);
  return d;
}

// nella pagina col pulsante del riquadro (grafici.js); disegnaGG fa il disegno, con le misure del riquadro se servono
function graficoGG(gg, ggLegge = null) {
  const box = $("grafico-gg");
  if (!Object.keys(gg.per_stagione).length) { box.innerHTML = ""; return; }
  const disegna = (dest, misure) => disegnaGG(dest, misure, gg, ggLegge);
  if (window.EUGENIO_GRAFICI) window.EUGENIO_GRAFICI.registra(box, disegna, { titolo: `Gradi giorno per stagione: ${$("titolo-comune").textContent}` });
  else { box.innerHTML = ""; disegna(box, null); }
}
function disegnaGG(box, misure, gg, ggLegge) {
  const voci = Object.entries(gg.per_stagione);
  const W = misure && misure.riquadro ? misure.larghezza : 640, H = misure && misure.riquadro ? misure.altezza : 220;
  const sx = 44, dx = 8, su = 16, gi = 26;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img",
    "aria-label": `Gradi giorno per stagione, da ${num(gg.minimo)} a ${num(gg.massimo)}`
      + (ggLegge !== null ? `; valore del DPR 412/93 ${num(ggLegge)}` : "") }, box);
  // scala con valori tondi: passo da 100, 250, 500 o 1000 GG
  const picco = Math.max(...voci.map(([, v]) => v), ggLegge || 0) * 1.05;
  const passoY = [100, 250, 500, 1000].find((s) => picco / s <= 5) || 1000;
  const max = Math.ceil(picco / passoY) * passoY, Y = (v) => su + (H - su - gi) * (1 - v / max);
  for (let v = 0; v <= max; v += passoY) {
    const y = Y(v);
    el("line", { x1: sx, x2: W - dx, y1: y, y2: y, stroke: "var(--linea)", "stroke-width": .6 }, svg);
    el("text", { x: sx - 6, y: y + 4, "text-anchor": "end" }, svg).textContent = num(v);
  }
  const passo = (W - sx - dx) / voci.length, larg = Math.min(passo * 0.62, misure && misure.riquadro ? 72 : 46);
  const punti = [];
  voci.forEach(([st, v], i) => {
    const x = sx + passo * i + (passo - larg) / 2;
    const r = el("rect", { x, y: Y(v), width: larg, height: Y(0) - Y(v), fill: "var(--primario)", rx: 2, class: "barra" }, svg);
    const righe = [["var(--primario)", `Gradi giorno: ${num(v)} GG`]];
    const diff = differenza(v, ggLegge);
    if (diff !== null) righe.push(["var(--segno)", `rispetto al DPR 412/93 (${num(ggLegge)}): ${diff > 0 ? "+" : ""}${num(diff, 1)} %`]);
    punti.push({ x: x + larg / 2, titolo: `Stagione ${st}`, righe, elementi: [r] });
    if (i % Math.ceil(voci.length / 8) === 0 || i === voci.length - 1)
      el("text", { x: x + larg / 2, y: H - 8, "text-anchor": "middle" }, svg).textContent = st;
  });
  const ym = Y(gg.gg_periodo_zona);
  el("line", { x1: sx, x2: W - dx, y1: ym, y2: ym, stroke: "var(--inchiostro)", "stroke-dasharray": "2 4", "stroke-width": 1.5, class: "media" }, svg);
  el("text", { x: W - dx, y: ym - 5, "text-anchor": "end" }, svg).textContent = `media ${num(gg.gg_periodo_zona)}`;
  const leg = h("div", "legenda");
  const voce = (cl, colore, testo) => {
    const s = h("span"); const i = h("i", cl); i.style.color = colore; i.style.background = cl ? "" : colore;
    s.append(i, testo); leg.appendChild(s);
  };
  voce(null, "var(--primario)", "gradi giorno della stagione (calcolati)");
  voce("linea punti", "var(--inchiostro)", `media delle stagioni: ${num(gg.gg_periodo_zona)}`);
  if (ggLegge !== null) {
    const yl = Y(ggLegge);
    el("line", { x1: sx, x2: W - dx, y1: yl, y2: yl, stroke: "var(--segno)", "stroke-dasharray": "7 4", "stroke-width": 2, class: "legge" }, svg);
    // etichetta a sinistra, sopra o sotto la linea per non coprire quella della media
    const sotto = Math.abs(yl - ym) < 16 && yl > ym;
    const t = el("text", { x: sx + 6, y: sotto ? yl + 15 : yl - 6, "text-anchor": "start" }, svg);
    t.textContent = `DPR 412/93 ${num(ggLegge)}`;
    t.style.fill = "var(--segno)";
    t.setAttribute("class", "etichetta-legge");
    voce("linea tratto", "var(--segno)", `valore di legge (DPR 412/93): ${num(ggLegge)}`);
  } else if (stato.dpr && stato.dpr.origini.length) {
    leg.appendChild(h("span", null, "nessuna linea del DPR 412/93: il comune è nato da una fusione e la legge non ha un valore unico"));
  }
  box.appendChild(leg);
  if (window.EUGENIO_GRAFICI) window.EUGENIO_GRAFICI.osserva(svg, punti, { area: [sx, su, W - dx, H - gi], guida: false });
}

const COLONNE = [
  ["t_media", "T media", "°C", 1], ["t_min_media", "T min", "°C", 1], ["t_max_media", "T max", "°C", 1],
  ["h_globale_mj", "Irradiazione globale", "MJ/m² giorno", 1], ["h_diffusa_mj", "di cui diffusa", "MJ/m² giorno", 1],
  ["pv_pa", "Pressione del vapore", "Pa", 0], ["ur_media", "Umidità relativa", "%", 0], ["vento_ms", "Vento", "m/s", 1],
];

function tabellaMensile(mensili) {
  const t = $("mensili"); t.innerHTML = "";
  const testa = t.createTHead().insertRow();
  testa.appendChild(h("th", null, "Mese"));
  for (const [, nome, unita] of COLONNE) {
    const th = h("th", "num", nome);
    th.appendChild(h("small", null, unita));
    testa.appendChild(th);
  }
  const corpo = t.createTBody();
  for (const m of mensili) {
    const r = corpo.insertRow();
    r.appendChild(h("th", null, MESI[m.mese - 1]));
    for (const [k, , , dec] of COLONNE) r.appendChild(h("td", "num", num(m[k], dec)));
  }
}

function tabellaZone(gg) {
  const t = $("zone"); t.innerHTML = "";
  const z = Object.entries(gg.gg_per_periodo_di_ogni_zona);
  const r1 = t.createTHead().insertRow(), r2 = t.createTBody().insertRow();
  r1.appendChild(h("th", null, "Zona"));
  r2.appendChild(h("th", null, "GG"));
  for (const [zona, v] of z) {
    const c = h("th", zona === gg.zona_risultante ? "num meglio" : "num", zona);
    r1.appendChild(c);
    r2.appendChild(h("td", zona === gg.zona_risultante ? "num meglio" : "num", num(v)));
  }
}

// ------------------------------------------------------------------ download
// licenza dei dati elaborati da EuGEnio (licenza.html#dati): CC BY 4.0, riuso citando EuGEnio come fonte
const CITAZIONE = "Fonte: EuGEnio – eugenio.statocritico.it";
const LICENZA = "Dati elaborati da EuGEnio con licenza CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/deed.it): si possono riutilizzare, anche modificati, "
  + "citando EuGEnio come fonte e mantenendo le fonti originali indicate, che restano soggette alle loro licenze. "
  + "Dettagli: https://eugenio.statocritico.it/licenza.html#dati";
const citazione = () => `${CITAZIONE} (dati estratti il ${new Date().toLocaleDateString("it-IT")})`;
function scarica(nome, contenuto, tipo) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([contenuto], { type: tipo }));
  a.download = nome;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
$("scarica-csv").addEventListener("click", () => {
  const d = stato.dati;
  const righe = [["mese", ...COLONNE.map(([k, , u]) => `${k} (${u})`)].join(";")];
  for (const m of d.mensili) righe.push([m.mese, ...COLONNE.map(([k]) => String(m[k]).replace(".", ","))].join(";"));
  righe.push("", `Comune;${d.comune} (${d.istat})`, `Stagioni;${d.stagioni.join(" ")}`, `Fonte;${d.fonte}`, `Avvertenza;${d.avvertenza}`);
  const p = stato.dpr;
  if (p && Number.isFinite(p.gg)) righe.push(`DPR 412/93 gradi giorno;${p.gg}`, `DPR 412/93 zona;${p.zona}`, `DPR 412/93 altitudine (m);${p.alt}`);
  else if (p && p.origini.length) p.origini.forEach((o) => righe.push(`DPR 412/93 ${o.nome};${o.gg} GG;zona ${o.zona};${o.alt} m`));
  if (p) righe.push(`Fonte DPR;DPR 26 agosto 1993 n. 412 Allegato A (Normattiva) ${DPR_URL}`);
  righe.push(`Licenza;${LICENZA}`, `Come citare;${citazione()}`);
  scarica(`clima_legge10_${d.istat}.csv`, "﻿" + righe.join("\r\n"), "text/csv;charset=utf-8");
});
$("scarica-json").addEventListener("click", () => {
  scarica(`clima_legge10_${stato.dati.istat}.json`, JSON.stringify({ licenza: LICENZA, citazione: citazione(), ...corpoReport() }, null, 2), "application/json");
});

// report (PDF, Excel, ODS): il corpo è la risposta di /api/clima-legge10/{istat} con, se c'è,
// il campo dpr412 {gg, zona, alt, nome, nota, origini} (il server ricalcola differenza e confronto)
function corpoReport() {
  return stato.dpr ? { ...stato.dati, dpr412: { ...stato.dpr, fonte: "DPR 26 agosto 1993, n. 412, Allegato A (Normattiva)", url: DPR_URL } } : stato.dati;
}
if (window.EUGENIO_REPORT) window.EUGENIO_REPORT.pulsanti($("report"), {
  tipo: "legge10",
  corpo: corpoReport,
  nome: (ext) => `clima_legge10_${stato.dati.istat}.${ext}`,
  messaggio, area: "messaggio",
});

caricaMappa().catch((e) => messaggio(`Mappa non disponibile: ${e.message}`, true));

// cambio di tema o di vestito (aspetto.js, senza ricaricare): il fondo dei comuni è un colore calcolato
document.addEventListener("eugenio:aspetto", () => {
  const fondo = window.EUGENIO && window.EUGENIO.fondoComuni ? window.EUGENIO.fondoComuni(REGIONE) : css("--linea");
  stato.percorsi.forEach((p) => p.setAttribute("fill", fondo));
});
