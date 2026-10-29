"use strict";
// Patrimonio edilizio: elenco di edifici (CSV, Excel o OpenDocument) → /api/patrimonio (a blocchi) → mappa dei punti
// ed elenco con gli esiti. Dal 29/10/2026 la mappa è quella tridimensionale di mappa3d.js (solo la regione scelta,
// che si cambia dalla piccola mappa) e la colonna di destra è un solo flusso di passi numerati: geolocalizzazione
// (questo file), poi valori per sede (valori_sedi.js, che usa le funzioni esposte qui sotto in
// window.EUGENIO_PATRIMONIO e, con i valori caricati, decide da sé il territorio mostrato dalla mappa).
const API = "/api";
const BLOCCO = 40;          // righe per richiesta: il tunnel Cloudflare chiude le richieste oltre i 100 secondi
const MASSIMO = 2000;       // edifici all'ora accettati dal server per indirizzo IP
const $ = (id) => document.getElementById(id);
const NS = "http://www.w3.org/2000/svg";
const ESITI = { ok: "trovato", verificare: "da verificare", non_trovato: "non trovato", errore: "errore" };
const stato = { file: null, righe: [], fonti: new Set(), filtro: "", scelto: null, mappa: null };

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

// la mappa tridimensionale (mappa3d.js): comuni della sola regione scelta, contorno della regione, punti e barre
async function caricaMappa() {
  const E = window.EUGENIO;
  stato.mappa = window.EUGENIO_MAPPA3D.crea($("mappa"), {
    // la vista delle barre cambia anche dalla mappa (Alt+trascinamento): i cursori della scheda «Valori per sede» la seguono
    suCambio: (vista, barre) => document.dispatchEvent(new CustomEvent("eugenio:vista3d", { detail: { vista, barre } })),
  });
  // la piccola mappa accanto al titolo cambia regione senza ricaricare: i risultati restano
  if (E) E.suRegione = (cod) => mostraRegione(cod).catch(() => {});
  await mostraRegione((E && E.regione) || "08");
}

// comuni della regione (dati/mappa/RR.json) e il suo contorno (dati/mappa/italia.json); punti e barre restano
async function mostraRegione(cod) {
  const E = window.EUGENIO;
  const [m, it] = await Promise.all([
    fetch(`dati/mappa/${cod}.json`).then((r) => (r.ok ? r.json() : null)),
    E ? E.italia().catch(() => null) : null,
  ]);
  if (!m) throw new Error("mappa della regione non disponibile");
  const reg = it && it.regioni.find((x) => x.cod === cod);
  // con i valori per sede caricati il territorio lo sceglie valori_sedi.js (le regioni delle sedi)
  if (!window.EUGENIO_PATRIMONIO || !window.EUGENIO_PATRIMONIO.territorioAutomatico) {
    stato.mappa.regione({ cod, comuni: m.comuni, contorno: reg ? reg.d : "", nome: m.nome || (reg && reg.nome) });
    $("mappa").setAttribute("aria-label", `Mappa di ${m.nome || (reg && reg.nome) || "regione"}`);
  }
  disegnaPunti(false);
}

function disegnaPunti(inquadra = true) {
  if (!stato.mappa) return;
  const con = stato.righe.map((r, i) => ({ r, i })).filter(({ r }) => r.lat !== null && r.lat !== undefined && r.lon !== null && r.lon !== undefined);
  const punti = con.map(({ r, i }) => {
    const [x, y] = lonlatSvg(+r.lon, +r.lat);
    return { x, y, i, classe: r.esito, etichetta: `${r.id}${r.denominazione ? " – " + r.denominazione : ""}` };
  });
  stato.mappa.punti(punti, (i) => scegli(i, true));
  if (stato.scelto !== null) scegli(stato.scelto, false);
  $("legenda-mappa").hidden = !punti.length;
  if (inquadra && punti.length) stato.mappa.inquadra(riquadroDi(punti));
}

// riquadro dei punti con un po' di margine (almeno 30 unità di lato, come prima)
function riquadroDi(punti) {
  const xs = punti.map((p) => p.x), ys = punti.map((p) => p.y);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, w = Math.max(x1 - x0, 30) * 1.24, hh = Math.max(y1 - y0, 30) * 1.24;
  return [cx - w / 2, cy - hh / 2, cx + w / 2, cy + hh / 2];
}

function scegli(i, scorri) {
  stato.scelto = i;
  document.querySelectorAll(".punto.scelto, .edificio.scelto").forEach((x) => x.classList.remove("scelto"));
  const c = stato.mappa && stato.mappa.svg.querySelector(`.punti circle[data-i="${i}"]`);
  if (c) { c.classList.add("scelto"); c.parentNode.appendChild(c); }
  const card = document.querySelector(`.edificio[data-i="${i}"]`);
  if (card) {
    card.classList.add("scelto");
    if (scorri) card.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }
}

// ------------------------------------------------------------------ lettura e invio a blocchi
// CSV e TXT letti qui; Excel (.xlsx) e OpenDocument (.ods) convertiti dal server (tabelle.js, primo foglio)
async function testoDelFile(f) {
  return window.EUGENIO_TABELLE.leggi(f);
}

const norm = (c) => c.trim().toLowerCase().replace(/["']/g, "").replace(/[^a-z0-9àèéìòù_]/g, "_").replace(/^_+|_+$/g, "");

function dividi(testo) {
  // le righe di nota in cima al file (che cominciano con #, come nel file d'esempio dei valori) non sono edifici
  const righe = testo.split(/\r?\n/).filter((r) => r.trim() !== "");
  while (righe.length && righe[0].trim().startsWith("#")) righe.shift();
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

// geolocalizzazione a blocchi di BLOCCO righe; avvisa(testo, errore) e barra(frazione) mostrano l'avanzamento.
// Usata anche dalla scheda «Valori per sede». Restituisce { righe, fonti, interrotto }.
async function geolocalizza(testo, nome, { avvisa, barra }) {
  const { blocchi, n } = dividi(testo);
  if (n > MASSIMO) throw new Error(`il file ha ${n} righe: il massimo è ${MASSIMO} all'ora, dividilo in più parti`);
  const righe = [], fonti = new Set();
  let interrotto = null;
  for (let b = 0; b < blocchi.length; b++) {
    avvisa(`Cerco gli edifici: ${Math.min(b * BLOCCO, n)} di ${n}…`);
    barra(b / blocchi.length);
    try {
      const d = await invia(blocchi[b], nome);
      righe.push(...d.righe);
      (d.fonti || []).forEach((f) => fonti.add(f));
    } catch (e) {
      if (!righe.length) throw e;
      interrotto = `Interrotto dopo ${righe.length} righe su ${n}: ${e.message}. Il risultato è parziale.`;
      break;
    }
  }
  barra(1);
  return { righe, fonti, interrotto, n };
}

$("calcola").addEventListener("click", async () => {
  $("calcola").disabled = true;
  stato.righe = []; stato.fonti = new Set(); stato.scelto = null;
  $("passo-risultato").hidden = true;
  try {
    messaggio("Lettura del file…");
    const letto = await testoDelFile(stato.file);
    $("avanzamento").hidden = false;
    const r = await geolocalizza(letto.testo, stato.file.name.replace(/\.(xlsx|ods)$/i, ".csv"), {
      avvisa: (t) => messaggio(t), barra: (f) => { $("barra").style.width = `${(100 * f).toFixed(1)}%`; },
    });
    stato.righe = r.righe; stato.fonti = r.fonti;
    messaggio([r.interrotto, letto.nota].filter(Boolean).join(" "), !!r.interrotto);
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
  numeraPassi();
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
$("file").setAttribute("accept", window.EUGENIO_TABELLE.ACCETTA);
const zona = $("zona-file");
["dragover", "dragenter"].forEach((t) => zona.addEventListener(t, (e) => { e.preventDefault(); zona.classList.add("pieno"); }));
zona.addEventListener("dragleave", () => zona.classList.toggle("pieno", !!stato.file));
zona.addEventListener("drop", (e) => { e.preventDefault(); impostaFile(e.dataTransfer.files[0]); });

// ------------------------------------------------------------------ passi numerati in sequenza
// la colonna di destra è un solo flusso: si numerano di seguito i passi visibili (geolocalizzazione, poi valori)
function numeraPassi() {
  let n = 0;
  document.querySelectorAll(".pannello .passo > h2 .n").forEach((x) => { if (!x.closest(".passo").hidden) x.textContent = ++n; });
}
numeraPassi();
// #valori nell'indirizzo porta alla prima sezione dei valori per sede (anche dai vecchi collegamenti alla scheda)
if (location.hash === "#valori") requestAnimationFrame(() => { const v = $("valori"); if (v) v.scrollIntoView({ block: "start" }); });

// piè di pagina: sul computer in fondo alla colonna sinistra (che scorre da sola); sul telefono, dove le colonne sono
// una sotto l'altra, torna in fondo alla pagina dopo la colonna destra
(function piede() {
  const p = $("piede"), area = document.querySelector(".mappa-area"), main = document.querySelector("main.strumento");
  if (!p || !area || !main) return;
  const telefono = window.matchMedia("(max-width: 860px)");
  const sistema = () => { if (telefono.matches) { if (p.parentElement !== document.body) main.after(p); } else if (p.parentElement !== area) area.appendChild(p); };
  sistema();
  telefono.addEventListener("change", sistema);
})();

// per la sezione «Valori per sede» (valori_sedi.js)
window.EUGENIO_PATRIMONIO = { geolocalizza, lonlatSvg, riquadroDi, scarica, mappa: () => stato.mappa, CITAZIONE, numeraPassi,
  mostraRegione, territorioAutomatico: false };

caricaMappa().catch((e) => messaggio(`Mappa non disponibile: ${e.message}`, true));
