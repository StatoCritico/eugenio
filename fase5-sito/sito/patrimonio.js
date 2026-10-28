"use strict";
// Patrimonio edilizio: CSV di edifici → /api/patrimonio (a blocchi) → mappa dei punti ed elenco con gli esiti.
const API = "/api";
const BLOCCO = 40;          // righe per richiesta: il tunnel Cloudflare chiude le richieste oltre i 100 secondi
const MASSIMO = 2000;       // edifici all'ora accettati dal server per indirizzo IP
const $ = (id) => document.getElementById(id);
const NS = "http://www.w3.org/2000/svg";
const ESITI = { ok: "trovato", verificare: "da verificare", non_trovato: "non trovato", errore: "errore" };
const stato = { file: null, righe: [], fonti: new Set(), filtro: "", scelto: null, svg: null, punti: null, vb: null };

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
const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
function messaggio(t, errore = false) { const m = $("messaggio"); m.textContent = t; m.classList.toggle("errore", errore); }

// ------------------------------------------------------------------ mappa
// coordinate geografiche → coordinate dei file di mappa (UTM 32N con la stessa scala di dati/mappa/*.json)
function lonlatSvg(lon, lat) {
  const k0 = 0.9996, a = 6378137, f = 1 / 298.257223563, e2 = f * (2 - f), ep2 = e2 / (1 - e2);
  const fi = lat * Math.PI / 180, l = (lon - 9) * Math.PI / 180;
  const N = a / Math.sqrt(1 - e2 * Math.sin(fi) ** 2), T = Math.tan(fi) ** 2, C = ep2 * Math.cos(fi) ** 2, A = Math.cos(fi) * l;
  const M = a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * fi - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * Math.sin(2 * fi)
    + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * Math.sin(4 * fi) - (35 * e2 ** 3 / 3072) * Math.sin(6 * fi));
  const E = 500000 + k0 * N * (A + (1 - T + C) * A ** 3 / 6 + (5 - 18 * T + T ** 2 + 72 * C - 58 * ep2) * A ** 5 / 120);
  const No = k0 * (M + N * Math.tan(fi) * (A ** 2 / 2 + (5 - T + 9 * C + 4 * C ** 2) * A ** 4 / 24 + (61 - 58 * T + T ** 2 + 600 * C - 330 * ep2) * A ** 6 / 720));
  const S = 0.0010012596459353985;
  return [S * E - 313.67365575107954, -S * No + 5226.851664605516];
}

async function caricaMappa() {
  const r = await fetch("dati/mappa/italia.json");
  if (!r.ok) throw new Error(`mappa non disponibile (${r.status})`);
  const m = await r.json();
  const svg = el("svg", { viewBox: m.viewBox.join(" "), role: "img", "aria-label": "Mappa d'Italia con gli edifici" });
  $("mappa").prepend(svg);
  const E = window.EUGENIO;
  stato.province = el("g", { class: "province" }, svg);
  stato.punti = el("g", { class: "punti" }, svg);
  stato.svg = svg;
  stato.vb = m.viewBox;
  if (E) {
    // regioni colorate sotto, confini regionali sopra le province, punti sopra a tutto
    await E.sfondoItalia(svg).catch(() => {});
    svg.appendChild(stato.punti);
    stato.zoom = E.mappaGrande(svg, m.viewBox);
  }
  await mostraRegione((E && E.regione) || "08");
  // la piccola mappa accanto al titolo cambia regione senza ricaricare: i risultati restano
  if (E) E.suRegione = (cod) => mostraRegione(cod, true).catch(() => {});
}

// inquadra una regione e ne disegna le province (dati/mappa/RR.json); i punti restano
async function mostraRegione(cod, inquadra = !stato.righe.length) {
  const r = await fetch(`dati/mappa/${cod}.json`);
  if (!r.ok) return;
  const m = await r.json();
  stato.province.innerHTML = "";
  for (const pr of m.province || []) el("title", {}, el("path", { d: pr.d }, stato.province)).textContent = pr.nome;
  stato.vb = m.viewBox;
  stato.svg.querySelectorAll(".italia-sfondo path").forEach((p) => p.classList.toggle("attiva", p.dataset.cod === cod));
  if (inquadra) {
    if (stato.zoom) stato.zoom.inquadra(m.viewBox); else stato.svg.setAttribute("viewBox", m.viewBox.join(" "));
    stato.svg.style.setProperty("--tratto", (Math.max(m.viewBox[2], m.viewBox[3]) / 640).toFixed(3));
  }
}

function disegnaPunti() {
  if (!stato.svg) return;
  stato.punti.innerHTML = "";
  const con = stato.righe.map((r, i) => ({ r, i })).filter(({ r }) => r.lat !== null && r.lat !== undefined && r.lon !== null);
  if (!con.length) { stato.svg.setAttribute("viewBox", stato.vb.join(" ")); return; }
  const xy = con.map(({ r }) => lonlatSvg(+r.lon, +r.lat));
  const xs = xy.map((p) => p[0]), ys = xy.map((p) => p[1]);
  let [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const lato = Math.max(x1 - x0, y1 - y0, 30), pad = lato * 0.12;
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, w = Math.max(x1 - x0, 30) + 2 * pad, hh = Math.max(y1 - y0, 30) + 2 * pad;
  stato.svg.setAttribute("viewBox", `${cx - w / 2} ${cy - hh / 2} ${w} ${hh}`);
  const raggio = Math.max(w, hh) / 160;
  stato.svg.style.setProperty("--tratto", (raggio / 4).toFixed(3));
  con.forEach(({ r, i }, k) => {
    const c = el("circle", { cx: xy[k][0], cy: xy[k][1], r: raggio, class: `punto ${r.esito}`, tabindex: "0",
                             role: "button", "aria-label": `${r.id} ${r.denominazione || ""}` }, stato.punti);
    c.dataset.i = i;
    el("title", {}, c).textContent = `${r.id}${r.denominazione ? " – " + r.denominazione : ""}`;
    c.addEventListener("click", () => scegli(i, true));
    c.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); scegli(i, true); } });
  });
  $("legenda-mappa").hidden = false;
}

function scegli(i, scorri) {
  stato.scelto = i;
  document.querySelectorAll(".punto.scelto, .edificio.scelto").forEach((x) => x.classList.remove("scelto"));
  const c = stato.punti && stato.punti.querySelector(`circle[data-i="${i}"]`);
  if (c) { c.classList.add("scelto"); c.parentNode.appendChild(c); }
  const card = document.querySelector(`.edificio[data-i="${i}"]`);
  if (card) {
    card.classList.add("scelto");
    if (scorri) card.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }
}

// ------------------------------------------------------------------ lettura e invio a blocchi
async function testoDelFile(f) {
  const buf = await f.arrayBuffer();
  let t;
  try { t = new TextDecoder("utf-8", { fatal: true }).decode(buf); }
  catch { t = new TextDecoder("windows-1252").decode(buf); }   // CSV di Excel salvato con la codifica di Windows
  return t.replace(/^﻿/, "");
}

const norm = (c) => c.trim().toLowerCase().replace(/["']/g, "").replace(/[^a-z0-9àèéìòù_]/g, "_").replace(/^_+|_+$/g, "");

function dividi(testo) {
  const righe = testo.split(/\r?\n/).filter((r) => r.trim() !== "");
  if (righe.length < 2) throw new Error("il file non contiene righe di dati");
  let testa = righe[0];
  const sep = (testa.match(/;/g) || []).length >= (testa.match(/,/g) || []).length ? ";" : ",";
  let corpo = righe.slice(1);
  // senza una colonna identificativa il server numera da 1 in ogni blocco: la numerazione la diamo qui
  const nomi = testa.split(sep).map(norm);
  if (!nomi.some((n) => ["id", "codice", "cod", "codice_edificio"].includes(n))) {
    testa = `id${sep}${testa}`;
    corpo = corpo.map((r, i) => `${i + 1}${sep}${r}`);
  }
  const blocchi = [];
  for (let i = 0; i < corpo.length; i += BLOCCO) blocchi.push([testa, ...corpo.slice(i, i + BLOCCO)].join("\n"));
  return { blocchi, n: corpo.length };
}

async function invia(testo, nome) {
  const fd = new FormData();
  fd.append("file", new Blob([testo], { type: "text/csv;charset=utf-8" }), nome);
  for (let tentativo = 0; ; tentativo++) {
    let r;
    try { r = await fetch(`${API}/patrimonio`, { method: "POST", body: fd }); }
    catch (e) { if (tentativo < 1) continue; throw new Error("server non raggiungibile"); }
    let d = null;
    try { d = await r.json(); } catch { /* risposta non JSON */ }
    if (r.ok) return d;
    if (r.status >= 500 && r.status !== 503 && tentativo < 1) continue;
    throw new Error((d && d.detail) || `errore ${r.status}`);
  }
}

$("calcola").addEventListener("click", async () => {
  $("calcola").disabled = true;
  stato.righe = []; stato.fonti = new Set(); stato.scelto = null;
  $("passo-risultato").hidden = true;
  try {
    const { blocchi, n } = dividi(await testoDelFile(stato.file));
    if (n > MASSIMO) throw new Error(`il file ha ${n} edifici: il massimo è ${MASSIMO} all'ora, dividilo in più parti`);
    $("avanzamento").hidden = false;
    for (let b = 0; b < blocchi.length; b++) {
      messaggio(`Cerco gli edifici: ${Math.min(b * BLOCCO, n)} di ${n}…`);
      $("barra").style.width = `${(100 * b / blocchi.length).toFixed(1)}%`;
      try {
        const d = await invia(blocchi[b], stato.file.name);
        stato.righe.push(...d.righe);
        (d.fonti || []).forEach((f) => stato.fonti.add(f));
      } catch (e) {
        if (!stato.righe.length) throw e;
        messaggio(`Interrotto dopo ${stato.righe.length} edifici su ${n}: ${e.message}. Il risultato qui sotto è parziale.`, true);
        break;
      }
      if (b === blocchi.length - 1) messaggio("");
    }
    $("barra").style.width = "100%";
    mostra();
  } catch (e) {
    messaggio(`Non riuscito: ${e.message}`, true);
  } finally {
    $("avanzamento").hidden = true;
    $("calcola").disabled = !stato.file;
  }
});

// ------------------------------------------------------------------ risultato
function conta() {
  const c = { ok: 0, verificare: 0, non_trovato: 0, errore: 0 };
  stato.righe.forEach((r) => { c[r.esito] = (c[r.esito] || 0) + 1; });
  return c;
}

function mostra() {
  $("passo-risultato").hidden = false;
  const c = conta(), box = $("conteggi");
  box.innerHTML = "";
  for (const [k, etichetta] of [["ok", "trovati"], ["verificare", "da verificare"], ["non_trovato", "non trovati"]]) {
    const d = h("div", `conteggio ${k}`);
    d.append(h("b", null, c[k].toLocaleString("it-IT")), h("span", null, etichetta));
    box.appendChild(d);
  }
  if (c.errore) {
    const d = h("div", "conteggio errore");
    d.append(h("b", null, c.errore), h("span", null, "errori"));
    box.appendChild(d);
  }
  // attribuzioni: il link a Zornade è obbligatorio con il piano gratuito; ANNCSU solo se usato
  const p = $("fonti");
  p.innerHTML = "";
  const a = h("a", null, "Dati elaborati da Zornade");
  a.href = "https://zornade.com";
  p.append("Fonti: ", a, ". ", [...stato.fonti].join("; "), ".");
  disegnaPunti();
  elenco();
}

function elenco() {
  const box = $("edifici");
  box.innerHTML = "";
  document.querySelectorAll(".filtro").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.esito === stato.filtro)));
  const vis = stato.righe.map((r, i) => ({ r, i })).filter(({ r }) => !stato.filtro || r.esito === stato.filtro);
  if (!vis.length) { box.appendChild(h("p", "aiuto", "Nessun edificio in questa categoria.")); return; }
  for (const { r, i } of vis) {
    const art = h("article", `edificio ${r.esito}`);
    art.dataset.i = i;
    art.tabIndex = 0;
    const testa = h("div", "testa");
    testa.append(h("strong", null, [r.id, r.denominazione].filter(Boolean).join(" · ")), h("span", `esito ${r.esito}`, ESITI[r.esito] || r.esito));
    art.appendChild(testa);
    const cercato = [r.indirizzo, r.civico, r.comune].filter(Boolean).join(" ");
    if (r.indirizzo_trovato) art.appendChild(h("p", null, `${r.indirizzo_trovato}${r.fonte_punto ? " (" + r.fonte_punto + ")" : ""}`));
    else if (cercato) art.appendChild(h("p", null, cercato));
    if (r.mappale) {
      const parti = [r.comune_catasto, r.foglio_catasto ? `foglio ${r.foglio_catasto}` : "", `mappale ${r.mappale}`,
        r.area_m2 ? `${Math.round(r.area_m2).toLocaleString("it-IT")} m²` : "", r.tipo_particella].filter(Boolean);
      art.appendChild(h("p", "catasto", `Catasto: ${parti.join(", ")}`));
    }
    if (r.nota) art.appendChild(h("p", "nota", r.nota));
    art.addEventListener("click", () => scegli(i, false));
    art.addEventListener("keydown", (e) => { if (e.key === "Enter") scegli(i, false); });
    box.appendChild(art);
  }
  if (stato.scelto !== null) scegli(stato.scelto, false);
}

document.querySelectorAll(".filtro").forEach((b) => b.addEventListener("click", () => { stato.filtro = b.dataset.esito; elenco(); }));

// ------------------------------------------------------------------ download
// licenza (licenza.html#dati): la geolocalizzazione di EuGEnio è CC BY 4.0; i dati di Zornade restano alle sue condizioni
const CITAZIONE = "Fonte: EuGEnio – eugenio.statocritico.it";
const LICENZA = "Le colonne del file caricato restano di chi le ha fornite. Geolocalizzazione di EuGEnio con licenza CC BY 4.0 "
  + "(https://creativecommons.org/licenses/by/4.0/deed.it): si può riutilizzare citando EuGEnio come fonte. Particelle e indirizzi trovati con Zornade restano "
  + "soggetti alle condizioni di Zornade: citare «Dati elaborati da Zornade» con il collegamento a https://zornade.com, "
  + "niente ridistribuzione in blocco dei dati grezzi. ANNCSU e ISTAT: CC BY 4.0. Dettagli: https://eugenio.statocritico.it/licenza.html#dati";
const citazione = () => `${CITAZIONE} (dati estratti il ${new Date().toLocaleDateString("it-IT")})`;
function scarica(nome, contenuto, tipo) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([contenuto], { type: tipo }));
  a.download = nome;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

$("scarica-csv").addEventListener("click", () => {
  const col = [];
  stato.righe.forEach((r) => Object.keys(r).forEach((k) => { if (!col.includes(k)) col.push(k); }));
  const cella = (v) => {
    if (v === null || v === undefined) return "";
    const s = typeof v === "number" ? String(v).replace(".", ",") : String(v);
    return /[;"\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const righe = [col.join(";"), ...stato.righe.map((r) => col.map((k) => cella(r[k])).join(";"))];
  righe.push("", `Fonti: Dati elaborati da Zornade (https://zornade.com); ${[...stato.fonti].join("; ")}`,
    cella(`Licenza: ${LICENZA}`), `Come citare: ${citazione()}`);
  scarica("patrimonio_geolocalizzato.csv", "﻿" + righe.join("\r\n"), "text/csv;charset=utf-8");
});

$("scarica-geojson").addEventListener("click", () => {
  const feats = stato.righe.filter((r) => r.lat !== null && r.lat !== undefined).map((r) => {
    const { lat, lon, ...prop } = r;
    return { type: "Feature", geometry: { type: "Point", coordinates: [lon, lat] }, properties: prop };
  });
  const g = { type: "FeatureCollection", features: feats, attribution: "Dati elaborati da Zornade",
    attribution_url: "https://zornade.com", attribution_html: '<a href="https://zornade.com">Dati elaborati da Zornade</a>',
    sources: [...stato.fonti], licenza: LICENZA, citazione: citazione() };
  scarica("patrimonio_punti.geojson", JSON.stringify(g), "application/geo+json");
});

// report (PDF, Excel, ODS): le righe di tutti i blocchi unite e le fonti, come una sola risposta di /api/patrimonio
function corpoReport() { return stato.righe.length ? { righe: stato.righe, fonti: [...stato.fonti] } : null; }
if (window.EUGENIO_REPORT) window.EUGENIO_REPORT.pulsanti($("report"), {
  tipo: "patrimonio",
  corpo: corpoReport,
  nome: (ext) => `patrimonio_geolocalizzato.${ext}`,
  messaggio, area: "messaggio",
});

// ------------------------------------------------------------------ file
function impostaFile(f) {
  stato.file = f || null;
  $("nome-file").textContent = f ? `${f.name} · ${(f.size / 1024).toFixed(0)} kB` : "Scegli il file o trascinalo qui";
  $("zona-file").classList.toggle("pieno", !!f);
  $("calcola").disabled = !f;
  messaggio("");
}
$("file").addEventListener("change", (e) => impostaFile(e.target.files[0]));
const zona = $("zona-file");
["dragover", "dragenter"].forEach((t) => zona.addEventListener(t, (e) => { e.preventDefault(); zona.classList.add("pieno"); }));
zona.addEventListener("dragleave", () => zona.classList.toggle("pieno", !!stato.file));
zona.addEventListener("drop", (e) => { e.preventDefault(); impostaFile(e.dataTransfer.files[0]); });

caricaMappa().catch((e) => messaggio(`Mappa non disponibile: ${e.message}`, true));
