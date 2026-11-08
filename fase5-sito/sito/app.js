"use strict";
// Interfaccia: mappa dei comuni, ricerca indirizzo, invio del CSV, grafico della previsione.
const API = "/api";
const $ = (id) => document.getElementById(id);
const NS = "http://www.w3.org/2000/svg";
const stato = { istat: null, comuni: new Map(), percorsi: new Map(), file: null, giro: 0, scheda: null };

const COV = {
  breve: [["temperatura", "Temperatura", true], ["radiazione", "Radiazione solare", true], ["umidita", "Umidità", true],
          ["diffusa", "Radiazione diffusa", false], ["vento", "Vento", false], ["nuvolosita", "Nuvolosità", false],
          ["pioggia", "Pioggia", false], ["neve", "Neve", false]],
  lungo: [["temperatura", "Temperatura media", true], ["gradi_giorno", "Gradi giorno", true],
          ["gradi_raffrescamento", "Gradi giorno estivi", true], ["radiazione", "Radiazione solare", true],
          ["umidita", "Umidità", false], ["vento", "Vento", false], ["pioggia", "Pioggia", false]],
};

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
const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

async function json(url, opts) {
  const r = await fetch(url, opts);
  let d = null;
  try { d = await r.json(); } catch { /* risposta non JSON */ }
  if (!r.ok) throw new Error((d && d.detail) || `Errore ${r.status}`);
  return d;
}

// ------------------------------------------------------------------ mappa
// colori dal CSS: "#rgb", "#rrggbb" o "rgb(r, g, b)" → [r, g, b]
function rgb(c) {
  c = (c || "").trim();
  if (c[0] === "#") {
    const h = c.length === 4 ? [...c.slice(1)].map((x) => x + x).join("") : c.slice(1, 7);
    return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  }
  const m = c.match(/\d+(\.\d+)?/g);
  return m && m.length >= 3 ? m.slice(0, 3).map(Number) : [128, 128, 128];
}
let scala = null;   // [da, a], letti alla prima occorrenza; si rileggono al cambio di tema o di vestito
function colore(t) { // 0..1 → da --scala-da (pochi gradi giorno, chiaro) a --scala-a (molti, scuro)
  if (!scala) scala = [rgb(css("--scala-da")), rgb(css("--scala-a"))];
  const [a, b] = scala;
  const c = a.map((x, i) => Math.round(x + (b[i] - x) * Math.max(0, Math.min(1, t))));
  return `rgb(${c.join(",")})`;
}

// regione mostrata: ?regione=RR nell'indirizzo, altrimenti Emilia-Romagna (i file sono per tutta Italia)
// (minimappa.js la sceglie dall'indirizzo o dal browser e la mette in window.EUGENIO_REGIONE)
const REGIONE = (window.EUGENIO && window.EUGENIO.regione) || (new URLSearchParams(location.search).get("regione") || "08").replace(/\D/g, "").padStart(2, "0");

async function caricaMappa() {
  const m = await json(`dati/mappa/${REGIONE}.json`);
  const svg = el("svg", { viewBox: m.viewBox.join(" "), role: "img", "aria-label": "Mappa dei comuni" });
  $("mappa").prepend(svg);
  const g = el("g", {}, svg);
  for (const c of m.comuni) {
    const p = el("path", { d: c.d, fill: (window.EUGENIO && window.EUGENIO.fondoComuni ? window.EUGENIO.fondoComuni(REGIONE) : "var(--linea)"), tabindex: "-1" }, g);
    p.dataset.istat = c.istat;
    p.dataset.nome = c.nome;            // nome e provincia nel riquadretto comune a tutte le mappe (minimappa.js)
    p.dataset.prov = c.prov;
    stato.percorsi.set(c.istat, p);
    stato.comuni.set(c.istat, { ...stato.comuni.get(c.istat), nome: c.nome, prov: c.prov, x: c.x, y: c.y });
    p.addEventListener("click", () => alterna(c.istat));   // secondo clic sullo stesso comune = lo si toglie
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
  sel.addEventListener("change", () => (sel.value ? scegli(sel.value) : togliComune()));   // «Scegli…» = nessun comune
  try { coloraMappa(await json(`${API}/mappa?giorni=7`)); } catch { $("scala-min").textContent = "previsioni meteo non disponibili"; }
}

// Freddo o caldo: la mappa mostra i gradi giorno di riscaldamento (base 20 °C) o quelli estivi di raffrescamento
// (base 24 °C), secondo quale dei due prevale nei prossimi 7 giorni su tutti i comuni; senza previsioni decide la
// stagione (giugno–settembre = caldo).
const STAGIONI = {
  freddo: { titolo: "Il freddo dei prossimi 7 giorni, comune per comune", campo: "gg", nome: "gradi giorno",
    sotto: "Gradi giorno previsti (base 20 °C): più il colore è scuro, più servirà riscaldare. Tocca un comune per sceglierlo, toccalo di nuovo per toglierlo." },
  caldo: { titolo: "Il caldo dei prossimi 7 giorni, comune per comune", campo: "gc", nome: "gradi giorno estivi",
    sotto: "Gradi giorno estivi previsti (base 24 °C): più il colore è scuro, più servirà raffrescare. Tocca un comune per sceglierlo, toccalo di nuovo per toglierlo." },
};

function stagione(d) {
  const c = d ? Object.values(d.comuni || {}) : [];
  if (c.length && c[0].gc !== undefined) {
    const somma = (k) => c.reduce((a, x) => a + (x[k] || 0), 0);
    return somma("gc") > somma("gg") ? "caldo" : "freddo";
  }
  const mese = new Date().getMonth() + 1;
  return mese >= 6 && mese <= 9 ? "caldo" : "freddo";
}

function titolaMappa(s) {
  $("titolo-mappa").textContent = STAGIONI[s].titolo;
  $("sotto-mappa").textContent = STAGIONI[s].sotto;
}
titolaMappa(stagione(null));

function coloraMappa(d) {
  stato.mappa = d;
  const s = STAGIONI[stagione(d)];
  titolaMappa(stagione(d));
  const v = Object.values(d.comuni).map((x) => x[s.campo]);
  if (!v.length) return;
  const min = Math.min(...v), max = Math.max(...v);
  for (const [istat, x] of Object.entries(d.comuni)) {
    const p = stato.percorsi.get(istat);
    if (!p) continue;
    p.setAttribute("fill", colore((x[s.campo] - min) / (max - min || 1)));
    p.dataset.dettaglio = `Prossimi 7 giorni: ${x[s.campo]} ${s.nome}\ntemperatura media ${x.t} °C`;
    Object.assign(stato.comuni.get(istat), x, { sintesi: `${x[s.campo]} ${s.nome}` });
  }
  $("scala-min").textContent = `${min.toFixed(0)} GG`;
  $("scala-max").textContent = `${max.toFixed(0)} GG`;
  $("scala-barra").style.background = `linear-gradient(90deg, ${colore(0)}, ${colore(1)})`;
}

// secondo clic sul comune già scelto = lo si toglie (funzione comune in minimappa.js, qui una copia se manca)
function alterna(istat) {
  if (window.EUGENIO && window.EUGENIO.alterna) return window.EUGENIO.alterna(istat, stato.istat, scegli, togliComune);
  if (istat === stato.istat) togliComune(); else scegli(istat);
}

// Cambio o deselezione del comune: il file dei consumi caricato e i risultati appartengono al comune di prima, quindi si
// tolgono (anche una risposta ancora in arrivo viene ignorata), con un breve messaggio.
function azzeraPerComune(motivo) {
  stato.giro = (stato.giro || 0) + 1;
  const avevaFile = !!stato.file;
  $("file").value = "";
  impostaFile(null);
  $("risultato").innerHTML = "";
  stato.richiesta = null;
  if (avevaFile) messaggio(`${motivo}: il file dei consumi caricato è stato tolto. Caricalo di nuovo per il comune scelto.`);
  else messaggio("");
}

function togliComune() {
  if (!stato.istat) return;
  stato.istat = null;
  if (window.EUGENIO && window.EUGENIO.togliScelto) window.EUGENIO.togliScelto(stato.percorsi);
  else stato.percorsi.forEach((p) => p.classList.remove("scelto"));
  $("comune").value = "";
  const s = $("comune-scelto"); s.hidden = true; s.innerHTML = "";
  if (stato.svg) stato.svg.querySelectorAll(".segnaposto").forEach((x) => x.remove());
  azzeraPerComune("Comune tolto");
  aggiornaBottone();
}

function scegli(istat, punto) {
  const c = stato.comuni.get(istat);
  if (!c) return messaggio("Questo comune non è ancora coperto dal servizio.", true);
  if (stato.istat && stato.istat !== istat) azzeraPerComune("Comune cambiato");
  stato.istat = istat;
  stato.percorsi.forEach((p) => p.classList.remove("scelto"));
  const p = stato.percorsi.get(istat);
  p.classList.add("scelto"); p.parentNode.appendChild(p);
  $("comune").value = istat;
  const s = $("comune-scelto");
  s.hidden = false;
  s.innerHTML = "";
  s.append(c.nome);
  const sm = document.createElement("small");
  sm.textContent = c.sintesi ? `Prossimi 7 giorni: ${c.sintesi}, temperatura media ${c.t} °C` : `Provincia di ${c.prov}`;
  s.append(sm);
  stato.svg.querySelectorAll(".segnaposto").forEach((x) => x.remove());
  if (punto) el("circle", { class: "segnaposto", cx: punto[0], cy: punto[1], r: 1.6 }, stato.svg);
  aggiornaBottone();
}

// ------------------------------------------------------------------ ricerca indirizzo (Zornade)
// (08/11/2026) Con il solo nome del comune (o «via…, Comune» con il comune scritto per intero) compare per prima la voce
// «Comune di X»: sceglie il comune della mappa, senza chiedere nulla al server. Le risposte senza coordinate vere (vuote
// o 0,0) non sono mai un punto.
const piano = (t) => String(t || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
const coordVere = (lat, lon) => lat !== null && lon !== null && lat !== "" && lon !== "" && Number.isFinite(+lat) && Number.isFinite(+lon)
  && !(Math.abs(+lat) < 1e-6 && Math.abs(+lon) < 1e-6);
function comuniNelTesto(q) {
  const t = piano(q), ultimo = piano(String(q).split(",").pop());
  const out = [];
  for (const [istat, c] of stato.comuni) {
    const n = piano(c.nome);
    if (n && (n === t || n === ultimo)) out.push([istat, c]);
  }
  return out;
}
function bottoneComune(ul, istat, c) {
  const li = document.createElement("li"), b = document.createElement("button");
  b.type = "button"; b.textContent = `Comune di ${c.nome}${c.prov ? ` (${c.prov})` : ""}`;
  b.addEventListener("click", () => { $("risultati").innerHTML = ""; $("cerca").value = c.nome; scegli(istat, [c.x, c.y]); });
  li.appendChild(b); ul.appendChild(li);
}
let attesa;
$("cerca").addEventListener("input", (e) => {
  clearTimeout(attesa);
  const q = e.target.value.trim();
  if (q.length < 3) { $("risultati").innerHTML = ""; return; }
  const comuni = comuniNelTesto(q);
  const ul = $("risultati"); ul.innerHTML = "";
  comuni.forEach(([istat, c]) => bottoneComune(ul, istat, c));
  if (q.length < 4 || (comuni.length && piano(q) === piano(comuni[0][1].nome))) return;    // solo il comune: basta la voce
  attesa = setTimeout(async () => {
    try {
      const d = await json(`${API}/geocodifica?q=${encodeURIComponent(q)}`);
      ul.innerHTML = "";
      comuni.forEach(([istat, c]) => bottoneComune(ul, istat, c));
      const buoni = (d.risultati || []).filter((r) => coordVere(r.lat, r.lon));
      if (!buoni.length && !comuni.length) { ul.innerHTML = "<li><button disabled>Nessun indirizzo trovato</button></li>"; return; }
      for (const r of buoni) {
        const li = document.createElement("li"), b = document.createElement("button");
        b.type = "button"; b.textContent = r.etichetta;
        b.addEventListener("click", () => scegliIndirizzo(r));
        li.appendChild(b); ul.appendChild(li);
      }
    } catch (err) { if (!comuni.length) messaggio(`Ricerca indirizzi non disponibile: ${err.message}. Scegli il comune dall'elenco.`, true); }
  }, 450);
});

async function scegliIndirizzo(r) {
  $("risultati").innerHTML = "";
  $("cerca").value = r.etichetta;
  if (!coordVere(r.lat, r.lon)) return messaggio("Indirizzo senza coordinate: scegli il comune dall'elenco o sulla mappa.", true);
  try {
    const d = await json(`${API}/particella?lat=${r.lat}&lon=${r.lon}`);
    if (!d.comune || !d.comune.istat) return messaggio("L'indirizzo è fuori dall'area coperta dal servizio.", true);
    scegli(d.comune.istat, lonlatSvg(r.lon, r.lat));
    const prima = $("messaggio").textContent;     // l'eventuale avviso del file dei consumi tolto resta
    if (d.particella) messaggio((prima ? `${prima} ` : "") + `Particella catastale ${d.particella.etichetta || d.particella.id}` +
      (d.particella.area_m2 ? `, ${Math.round(d.particella.area_m2).toLocaleString("it-IT")} m²` : "") + ".");
  } catch (err) { messaggio(err.message, true); }
}

// coordinate geografiche → mappa (UTM 32N, trasformazione stimata nella fase 3)
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

// ------------------------------------------------------------------ file e opzioni
// CSV, Excel (.xlsx) e OpenDocument (.ods) vanno al server così come sono (/api/previsione li legge tutti, primo
// foglio); il vecchio .xls si ferma qui con un messaggio chiaro (tabelle.js)
async function impostaFile(f) {
  const giro = stato.giro;
  const tipo = f && window.EUGENIO_TABELLE ? await window.EUGENIO_TABELLE.tipo(f) : null;
  if (giro !== stato.giro) return;      // nel frattempo il comune è cambiato o è stato tolto: il file non vale più
  if (f && tipo === "xls") {
    messaggio(window.EUGENIO_TABELLE.MSG_XLS, true);
    $("file").value = "";
    f = null;
  } else if (f && /^(xlsx|ods|foglio)$/.test(tipo || "")) {
    messaggio("Foglio di calcolo: il server leggerà il primo foglio.");
  } else if (f) messaggio("");
  stato.file = f;
  $("nome-file").textContent = f ? `${f.name} · ${(f.size / 1024).toFixed(0)} kB` : "Scegli il file o trascinalo qui";
  $("zona-file").classList.toggle("pieno", !!f);
  aggiornaBottone();
}
$("file").addEventListener("change", (e) => impostaFile(e.target.files[0]));
if (window.EUGENIO_TABELLE) $("file").setAttribute("accept", window.EUGENIO_TABELLE.ACCETTA);
const zona = $("zona-file");
["dragover", "dragenter"].forEach((t) => zona.addEventListener(t, (e) => { e.preventDefault(); zona.classList.add("pieno"); }));
zona.addEventListener("dragleave", () => zona.classList.toggle("pieno", !!stato.file));
zona.addEventListener("drop", (e) => { e.preventDefault(); impostaFile(e.dataTransfer.files[0]); });

function modalita() { return document.querySelector("input[name=modalita]:checked").value; }
function disegnaCovariate() {
  const m = modalita(), box = $("covariate"); box.innerHTML = "";
  for (const [k, nome, pred] of COV[m]) {
    const l = document.createElement("label"), i = document.createElement("input");
    i.type = "checkbox"; i.value = k; i.checked = pred; l.append(i, nome); box.appendChild(l);
  }
  const o = $("orizzonte");
  if (m === "breve") { $("orizzonte-etichetta").textContent = "Ore da prevedere"; o.max = 360; o.value = 72; }
  else { $("orizzonte-etichetta").textContent = "Giorni da prevedere"; o.max = 365; o.value = 30; }
}
document.querySelectorAll("input[name=modalita]").forEach((r) => r.addEventListener("change", disegnaCovariate));
// «Cosa prevedere»: i consumi (serve il file) o solo il clima del comune (nessun file, /api/clima-previsto)
const soloClima = () => (document.querySelector("input[name=cosa]:checked") || {}).value === "clima";
function aggiornaCosa() {
  const c = soloClima();
  $("blocco-consumi").hidden = c;
  $("aiuto-solo-clima").hidden = !c;
  $("blocco-verifica").hidden = c;
  $("calcola").textContent = c ? "Mostra le previsioni del clima" : "Calcola la previsione";
  stato.giro = (stato.giro || 0) + 1;      // il risultato dell'altra scelta non vale più
  $("risultato").innerHTML = "";
  aggiornaBottone();
}
document.querySelectorAll("input[name=cosa]").forEach((r) => r.addEventListener("change", aggiornaCosa));
function aggiornaBottone() { $("calcola").disabled = !(stato.istat && (soloClima() || stato.file)); }
function messaggio(t, errore = false) { const m = $("messaggio"); m.textContent = t; m.classList.toggle("errore", errore); }

async function calcolaClima() {
  const giro = stato.giro, m = modalita(), cov = [...document.querySelectorAll("#covariate input:checked")].map((i) => i.value);
  if (!cov.length) return messaggio("Scegli almeno una variabile meteo da mostrare.", true);
  stato.richiesta = { istat: stato.istat, comune: (stato.comuni.get(stato.istat) || {}).nome || null, modalita: m,
    orizzonte: Number($("orizzonte").value), covariate: cov, solo_clima: true };
  $("calcola").disabled = true;
  messaggio("Lettura delle previsioni del clima…");
  $("risultato").innerHTML = "";
  try {
    const q = new URLSearchParams({ modalita: m, orizzonte: $("orizzonte").value, covariate: cov.join(",") });
    const r = await json(`${API}/clima-previsto/${stato.istat}?${q}`);
    if (giro !== stato.giro) return;
    messaggio("");
    mostraRisultato(r);
  } catch (err) {
    if (giro === stato.giro) messaggio(`Previsioni del clima non disponibili: ${err.message}`, true);
  } finally { aggiornaBottone(); }
}

$("calcola").addEventListener("click", async () => {
  if (soloClima()) return calcolaClima();
  const giro = stato.giro;
  const fd = new FormData();
  fd.append("file", stato.file);
  fd.append("istat", stato.istat);
  fd.append("modalita", modalita());
  fd.append("orizzonte", $("orizzonte").value);
  fd.append("tipo", $("tipo").value);
  fd.append("covariate", [...document.querySelectorAll("#covariate input:checked")].map((i) => i.value).join(","));
  fd.append("verifica", $("verifica").value);
  // le scelte dell'utente, da allegare al report (campo "richiesta")
  stato.richiesta = {
    istat: stato.istat, comune: (stato.comuni.get(stato.istat) || {}).nome || null,
    modalita: modalita(), orizzonte: Number($("orizzonte").value), tipo: $("tipo").value,
    covariate: [...document.querySelectorAll("#covariate input:checked")].map((i) => i.value),
    verifica: $("verifica").value === "true",
  };
  $("calcola").disabled = true;
  messaggio("Calcolo in corso: di solito bastano pochi secondi.");
  $("risultato").innerHTML = "";
  try {
    const r = await json(`${API}/previsione`, { method: "POST", body: fd });
    if (giro !== stato.giro) return;          // nel frattempo il comune è cambiato o è stato tolto
    messaggio("");
    mostraRisultato(r);
  } catch (err) {
    if (giro === stato.giro) messaggio(`Previsione non riuscita: ${err.message}`, true);
  } finally { aggiornaBottone(); }
});

// ------------------------------------------------------------------ risultato a schede (04/11/2026)
// Una scheda per i consumi (spenta in «Solo clima») e una per ogni variabile meteo attiva, nell'ordine delle opzioni
// della pagina (COV). Ogni scheda ha il suo grafico (col pulsante del riquadro, grafici.js), le cifre, gli avvisi e
// «Scarica la previsione (CSV)»; il CSV e i report hanno sempre tutti i valori, in colonne affiancate.
const nomeVariabile = (m, k) => (COV[m].find((x) => x[0] === k) || [k, k])[1];
function variabiliClima(r) {
  const cl = r.clima || {};
  const ordine = [...COV[r.modalita].map((x) => x[0]), ...Object.keys(cl)];
  return ordine.filter((k, i) => cl[k] && ordine.indexOf(k) === i);
}

function mostraRisultato(r) {
  const box = $("risultato");
  box.innerHTML = "";
  const nome = (stato.comuni.get(r.istat) || {}).nome;
  const schede = [{ chiave: "consumo", nome: "Consumo", spenta: !!r.solo_clima },
    ...variabiliClima(r).map((k) => ({ chiave: k, nome: nomeVariabile(r.modalita, k) }))];
  const barra = document.createElement("div");
  barra.className = "schede schede-previsione";
  barra.setAttribute("role", "tablist");
  barra.setAttribute("aria-label", "Grafici della previsione");
  box.appendChild(barra);
  const pannelli = schede.map((sc) => {
    const b = document.createElement("button");
    b.type = "button"; b.setAttribute("role", "tab"); b.id = `scheda-${sc.chiave}`; b.textContent = sc.nome;
    b.dataset.chiave = sc.chiave;
    const pan = document.createElement("div");
    pan.className = "pannello-scheda"; pan.id = `pannello-${sc.chiave}`;
    pan.setAttribute("role", "tabpanel"); pan.setAttribute("aria-labelledby", b.id);
    b.setAttribute("aria-controls", pan.id);
    if (sc.spenta) { b.disabled = true; b.title = "Solo clima: nessun consumo caricato"; b.setAttribute("aria-disabled", "true"); }
    barra.appendChild(b); box.appendChild(pan);
    return { sc, b, pan };
  });
  const attive = pannelli.filter((x) => !x.sc.spenta);
  if (r.solo_clima) {
    const nota = document.createElement("p");
    nota.className = "aiuto nota-schede";
    nota.textContent = "Solo clima: la scheda Consumo è spenta perché non è stato caricato nessun file.";
    barra.after(nota);
  }
  const apri = (x, fuoco) => {
    pannelli.forEach((y) => {
      const su = y === x;
      y.b.setAttribute("aria-selected", String(su)); y.b.tabIndex = su ? 0 : -1; y.pan.hidden = !su;
    });
    if (!x.pan.childElementCount) riempiScheda(x.pan, x.sc.chiave, r, nome);
    stato.scheda = x.sc.chiave;
    if (fuoco) x.b.focus();
  };
  attive.forEach((x, j) => {
    x.b.addEventListener("click", () => apri(x));
    x.b.addEventListener("keydown", (e) => {
      const k = { ArrowRight: j + 1, ArrowLeft: j - 1, Home: 0, End: attive.length - 1 }[e.key];
      if (k === undefined) return;
      e.preventDefault();
      apri(attive[(k + attive.length) % attive.length], true);
    });
  });
  if (attive.length) apri(attive.find((x) => x.sc.chiave === stato.scheda) || attive[0]);
  // report (PDF, Excel, ODS): uno solo per tutte le schede, con tutti i valori
  if (window.EUGENIO_REPORT) {
    const richiesta = stato.richiesta;
    const prefisso = r.solo_clima ? "clima_previsto" : "previsione";
    window.EUGENIO_REPORT.pulsanti(box, {
      tipo: "previsione",
      corpo: () => corpoReport(r, richiesta),
      nome: (ext) => `${prefisso}_${r.istat}_${r.modalita}.${ext}`,
      messaggio, area: "messaggio",
    });
  }
}

function riempiScheda(pan, chiave, r, nome) {
  const g = document.createElement("div"); g.className = "grafico"; pan.appendChild(g);
  const consumo = chiave === "consumo";
  const titolo = consumo ? `Previsione dei consumi${nome ? ` – ${nome}` : ""}`
    : `${nomeVariabile(r.modalita, chiave)} (${r.clima[chiave].unita || "senza unità"})${nome ? ` – ${nome}` : ""}`;
  // grafico col pulsante del riquadro (grafici.js); le funzioni usano le misure del riquadro quando servono
  const disegna = consumo ? (dest, misure) => disegnaPrevisione(dest, misure, r)
    : (dest, misure) => disegnaClima(dest, misure, r, chiave);
  if (window.EUGENIO_GRAFICI) window.EUGENIO_GRAFICI.registra(g, disegna, { titolo });
  else disegna(g, null);
  mostraDettagli(r, pan, consumo);
}

const numero = (x, dec = 2) => x === null || x === undefined ? "—" : Number(x).toLocaleString("it-IT", { maximumFractionDigits: dec });
const DEBOLI = { "previsione IFS": "meteo globale", "miscela ICON-2I/IFS": null, "climatologia": "climatologia" };

// zone con meteo meno affidabile (modello globale o climatologia), sopra il fondo e sotto le linee
function zoneDeboli(svg, fonti, n0, X, su, altezza) {
  let inizio = null;
  fonti.forEach((f, i) => {
    const debole = f in DEBOLI;
    if (debole && inizio === null) inizio = i;
    if ((!debole || i === fonti.length - 1) && inizio !== null) {
      const fine = debole ? i : i - 1;
      el("rect", { x: X(n0 + inizio), y: su, width: Math.max(1, X(n0 + fine) - X(n0 + inizio)), height: altezza, fill: "var(--tinta)", opacity: .55 }, svg);
      const t = el("text", { x: X(n0 + inizio) + 4, y: su + 12 }, svg);
      t.textContent = fonti[fine] === "climatologia" ? "meteo: climatologia" : "meteo: modello globale";
      inizio = null;
    }
  });
}

// griglia orizzontale con i valori e date sull'asse dei tempi
function assiTempo(svg, { W, H, sx, dx, su, gi, ymin, ymax, Y, X, etich, passo }) {
  const n = etich.length;
  for (let k = 0; k <= 4; k++) {
    const v = ymin + (ymax - ymin) * k / 4, y = Y(v);
    el("line", { x1: sx, x2: W - dx, y1: y, y2: y, stroke: "var(--linea)", "stroke-width": .6 }, svg);
    const t = el("text", { x: sx - 6, y: y + 4, "text-anchor": "end" }, svg);
    t.textContent = v.toLocaleString("it-IT", { maximumFractionDigits: Math.abs(ymax - ymin) < 20 ? 1 : 0 });
  }
  const passi = Math.max(2, Math.min(12, Math.round((W - sx - dx) / 100)));
  for (let k = 0; k <= passi; k++) {
    const i = Math.round((n - 1) * k / passi), d = new Date(etich[i]);
    const t = el("text", { x: X(i), y: H - 8, "text-anchor": k === 0 ? "start" : k === passi ? "end" : "middle" }, svg);
    t.textContent = passo === "ora"
      ? (n > 96 ? d.toLocaleDateString("it-IT", { day: "numeric", month: "short" })
                : `${d.toLocaleDateString("it-IT", { day: "numeric", month: "short" })} ore ${d.getHours()}`)
      : d.toLocaleDateString("it-IT", { day: "numeric", month: "short", year: "2-digit" });
  }
}
const quando = (t, passo) => {
  const d = new Date(t);
  return passo === "ora"
    ? `${d.toLocaleDateString("it-IT", { weekday: "short", day: "numeric", month: "long", year: "numeric" })}, ore ${d.getHours()}`
    : d.toLocaleDateString("it-IT", { weekday: "short", day: "numeric", month: "long", year: "numeric" });
};
function tracciaLinea(svg, vals, off, col, w, tratt, X, Y) {
  let dpath = "", su_ = false;
  vals.forEach((v, i) => { if (v === null || v === undefined) { su_ = false; return; } dpath += `${su_ ? "L" : "M"}${X(off + i)},${Y(v)}`; su_ = true; });
  if (dpath) el("path", { d: dpath, fill: "none", stroke: col, "stroke-width": w, "stroke-dasharray": tratt || "none", "stroke-linejoin": "round" }, svg);
}

function disegnaPrevisione(g, misure, r) {
  const W = misure && misure.riquadro ? misure.larghezza : 640, H = misure && misure.riquadro ? misure.altezza : 300;
  const sx = 44, dx = 8, su = 12, gi = 28;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Grafico della previsione dei consumi" }, g);
  const st = r.storico, pr = r.previsione, n0 = st.t.length, n = n0 + pr.t.length;
  const tutti = [...st.v, ...pr["0.1"], ...pr["0.9"], ...((r.verifica && r.verifica.reale) || [])].filter((x) => x !== null);
  let ymin = Math.min(...tutti), ymax = Math.max(...tutti);
  const pad = (ymax - ymin) * 0.08 || 1; ymin -= pad; ymax += pad;
  const X = (i) => sx + (W - sx - dx) * i / (n - 1), Y = (v) => su + (H - su - gi) * (1 - (v - ymin) / (ymax - ymin));
  zoneDeboli(svg, pr.fonte_meteo, n0, X, su, H - su - gi);
  const etich = [...st.t, ...pr.t];
  assiTempo(svg, { W, H, sx, dx, su, gi, ymin, ymax, Y, X, etich, passo: r.passo });
  const area = (lo, hi, op) => {
    const su_ = pr[hi].map((v, i) => `${X(n0 + i)},${Y(v)}`), giu = pr[lo].map((v, i) => `${X(n0 + i)},${Y(v)}`).reverse();
    el("polygon", { points: [...su_, ...giu].join(" "), fill: "var(--serie-1)", opacity: op }, svg);
  };
  area("0.1", "0.9", .18); area("0.3", "0.7", .3);
  tracciaLinea(svg, st.v, 0, "var(--inchiostro)", 1.3, null, X, Y);
  if (r.verifica) tracciaLinea(svg, r.verifica.reale, n0, "var(--serie-2)", 1.6, "7 4", X, Y);
  tracciaLinea(svg, pr["0.5"], n0, "var(--serie-1)", 2, null, X, Y);
  el("line", { x1: X(n0 - .5), x2: X(n0 - .5), y1: su, y2: H - gi, stroke: "var(--tenue)", "stroke-dasharray": "2 3" }, svg);

  const leg = document.createElement("div"); leg.className = "legenda";
  leg.innerHTML = `<span><i class="linea" style="color:${"var(--inchiostro)"}"></i>dati caricati</span>` +
    (r.verifica ? `<span><i class="linea tratto" style="color:${"var(--serie-2)"}"></i>valori reali nascosti al modello</span>` : "") +
    `<span><i class="linea" style="color:${"var(--serie-1)"};border-top-width:3px"></i>previsione (mediana)</span>` +
    `<span><i style="background:${"var(--serie-1)"};opacity:.45"></i>4 casi su 10 / 8 casi su 10</span>`;
  g.appendChild(leg);

  // valori al passaggio del mouse, al tocco o con le frecce (grafici.js)
  if (window.EUGENIO_GRAFICI) {
    const punti = etich.map((t, i) => {
      const righe = [], segni = [];
      if (i < n0) {
        if (st.v[i] !== null) { righe.push(["var(--inchiostro)", `dati caricati: ${numero(st.v[i])}`]); segni.push([X(i), Y(st.v[i]), "var(--inchiostro)"]); }
      } else {
        const k = i - n0, med = pr["0.5"][k];
        if (med !== null) { righe.push(["var(--serie-1)", `previsione (mediana): ${numero(med)}`]); segni.push([X(i), Y(med), "var(--serie-1)"]); }
        righe.push([null, `8 casi su 10 tra ${numero(pr["0.1"][k])} e ${numero(pr["0.9"][k])}`]);
        righe.push([null, `4 casi su 10 tra ${numero(pr["0.3"][k])} e ${numero(pr["0.7"][k])}`]);
        const vero = r.verifica && r.verifica.reale ? r.verifica.reale[k] : null;
        if (vero !== null && vero !== undefined) { righe.push(["var(--serie-2)", `valore reale: ${numero(vero)}`]); segni.push([X(i), Y(vero), "var(--serie-2)"]); }
        if (pr.fonte_meteo[k]) righe.push([null, `meteo: ${pr.fonte_meteo[k]}`]);
      }
      return { x: X(i), titolo: quando(t, r.passo), righe, segni };
    });
    window.EUGENIO_GRAFICI.osserva(svg, punti, { area: [sx, su, W - dx, H - gi] });
  }
}

// una variabile meteo: osservata (o nel periodo dei dati caricati) e poi prevista, con le stesse zone del meteo
function disegnaClima(g, misure, r, k) {
  const W = misure && misure.riquadro ? misure.larghezza : 640, H = misure && misure.riquadro ? misure.altezza : 300;
  const sx = 44, dx = 8, su = 16, gi = 28;
  const v = r.clima[k], u = v.unita || "", nomeV = nomeVariabile(r.modalita, k);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `Grafico: ${nomeV}` }, g);
  const pr = r.previsione, n0 = r.storico.t.length, n = Math.max(2, n0 + pr.t.length);
  const tutti = [...v.storico, ...v.previsione].filter((x) => x !== null && x !== undefined);
  let ymin = tutti.length ? Math.min(...tutti) : 0, ymax = tutti.length ? Math.max(...tutti) : 1;
  const pad = (ymax - ymin) * 0.08 || 1; ymin -= pad; ymax += pad;
  const X = (i) => sx + (W - sx - dx) * i / (n - 1), Y = (x) => su + (H - su - gi) * (1 - (x - ymin) / (ymax - ymin));
  zoneDeboli(svg, pr.fonte_meteo, n0, X, su, H - su - gi);
  const etich = [...r.storico.t, ...pr.t];
  assiTempo(svg, { W, H, sx, dx, su, gi, ymin, ymax, Y, X, etich, passo: r.passo });
  if (u) el("text", { x: sx, y: su - 4 }, svg).textContent = u;
  tracciaLinea(svg, v.storico, 0, "var(--inchiostro)", 1.3, null, X, Y);
  tracciaLinea(svg, v.previsione, n0, "var(--serie-1)", 2, null, X, Y);
  if (n0) el("line", { x1: X(n0 - .5), x2: X(n0 - .5), y1: su, y2: H - gi, stroke: "var(--tenue)", "stroke-dasharray": "2 3" }, svg);
  const passato = r.solo_clima ? "osservato" : "nel periodo dei dati caricati";
  const leg = document.createElement("div"); leg.className = "legenda";
  leg.innerHTML = `<span><i class="linea" style="color:var(--inchiostro)"></i>${passato}</span>` +
    `<span><i class="linea" style="color:var(--serie-1);border-top-width:3px"></i>previsto</span>`;
  g.appendChild(leg);
  if (window.EUGENIO_GRAFICI) {
    const punti = etich.map((t, i) => {
      const futuro = i >= n0, x = futuro ? v.previsione[i - n0] : v.storico[i];
      const righe = [], segni = [];
      if (x !== null && x !== undefined) {
        const col = futuro ? "var(--serie-1)" : "var(--inchiostro)";
        righe.push([col, `${futuro ? "previsto" : passato}: ${numero(x, 1)} ${u}`]);
        segni.push([X(i), Y(x), col]);
      }
      const f = futuro ? pr.fonte_meteo[i - n0] : (r.fonte_storico || [])[i];
      if (f) righe.push([null, `meteo: ${f}`]);
      return { x: X(i), titolo: quando(t, r.passo), righe, segni };
    });
    window.EUGENIO_GRAFICI.osserva(svg, punti, { area: [sx, su, W - dx, H - gi] });
  }
}

// CSV con tutti i valori in colonne affiancate: passato e futuro, consumi (se ci sono) e variabili meteo attive
function righeCsv(r) {
  const pr = r.previsione, q = ["0.1", "0.3", "0.5", "0.7", "0.9"], vars = variabiliClima(r), cl = r.clima || {};
  const reale = r.verifica && r.verifica.reale;
  const testo = (x) => (x === null || x === undefined ? "" : String(x).replace(".", ","));
  const testa = ["data", "parte"];
  if (!r.solo_clima) testa.push("consumo", ...q.map((x) => `q${x.replace(".", "")}`), ...(reale ? ["reale"] : []));
  testa.push(...vars.map((k) => `${k}${cl[k].unita ? ` (${cl[k].unita})` : ""}`), "fonte_meteo");
  const righe = [testa.join(";")];
  r.storico.t.forEach((t, i) => {
    const c = [t, r.solo_clima ? "osservato" : "dati caricati"];
    if (!r.solo_clima) c.push(testo(r.storico.v[i]), ...q.map(() => ""), ...(reale ? [""] : []));
    c.push(...vars.map((k) => testo(cl[k].storico[i])), (r.fonte_storico || [])[i] || "");
    righe.push(c.join(";"));
  });
  pr.t.forEach((t, i) => {
    const c = [t, "previsione"];
    if (!r.solo_clima) c.push("", ...q.map((x) => testo(pr[x][i])), ...(reale ? [testo(reale[i])] : []));
    c.push(...vars.map((k) => testo(cl[k].previsione[i])), pr.fonte_meteo[i] || "");
    righe.push(c.join(";"));
  });
  // fonti e licenza in fondo (licenza.html#dati): previsione di EuGEnio CC BY 4.0, riuso citando EuGEnio come fonte
  righe.push("", "Fonte meteo;Weather data by Open-Meteo.com (CC BY 4.0): Arpae ICON-2I, DWD ICON, ECMWF IFS, ERA5 Copernicus",
    "Licenza;" + (r.solo_clima ? "Variabili meteo del comune elaborate da EuGEnio" : "Previsione elaborata da EuGEnio con il modello TiRex-2 sui consumi forniti")
    + "; licenza CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/deed.it): si può riutilizzare citando EuGEnio come fonte e Open-Meteo. "
    + "Dettagli: https://eugenio.statocritico.it/licenza.html#dati",
    `Come citare;Fonte: EuGEnio – eugenio.statocritico.it (dati estratti il ${new Date().toLocaleDateString("it-IT")})`);
  return righe;
}

// cifre della verifica (scheda Consumo), avvisi e pulsante del CSV, sotto il grafico di ogni scheda
function mostraDettagli(r, box, consumo) {
  if (consumo && r.verifica) {
    const v = r.verifica, d = document.createElement("div"); d.className = "verifica";
    const fmt = (x, p) => x === null ? "—" : p ? `${(x * 100).toFixed(0)} %` : x.toLocaleString("it-IT", { maximumFractionDigits: 2 });
    d.innerHTML = `<div><b>${fmt(v.wape, true)}</b><span>errore relativo complessivo (WAPE)</span></div>` +
      `<div><b>${fmt(v.mae)}</b><span>errore medio per ${r.passo}</span></div>` +
      `<div><b>${fmt(v.copertura_80, true)}</b><span>valori reali dentro la fascia larga (atteso 80 %)</span></div>`;
    box.appendChild(d);
  }
  if (r.avvisi && r.avvisi.length) {
    const ul = document.createElement("ul"); ul.className = "avvisi";
    r.avvisi.forEach((a) => { const li = document.createElement("li"); li.textContent = a; ul.appendChild(li); });
    box.appendChild(ul);
  }
  const scarica = document.createElement("div"); scarica.className = "scarica";
  const csvBtn = document.createElement("button");
  csvBtn.type = "button"; csvBtn.className = "bottone secondario"; csvBtn.textContent = "Scarica la previsione (CSV)";
  csvBtn.title = "Tutti i valori in colonne affiancate: " + (r.solo_clima ? "" : "consumi e ") + "variabili meteo";
  csvBtn.addEventListener("click", () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob(["﻿" + righeCsv(r).join("\r\n")], { type: "text/csv;charset=utf-8" }));
    a.download = `${r.solo_clima ? "clima_previsto" : "previsione"}_${r.istat}_${r.modalita}.csv`; a.click();
  });
  scarica.appendChild(csvBtn);
  box.appendChild(scarica);
}

// corpo del report: la risposta di /api/previsione (o /api/clima-previsto) così com'è, più le scelte della pagina
function corpoReport(r, richiesta) { return { ...r, richiesta: richiesta || null }; }

disegnaCovariate();
aggiornaCosa();     // anche se il browser ha ricordato «Solo clima» tornando alla pagina

// cambio di tema o di vestito (aspetto.js, senza ricaricare la pagina): i grafici usano "var(--…)" e cambiano da
// soli; qui si rifanno i colori calcolati della mappa (fondo dei comuni e scala dei gradi giorno)
document.addEventListener("eugenio:aspetto", () => {
  scala = null;
  const fondo = window.EUGENIO && window.EUGENIO.fondoComuni ? window.EUGENIO.fondoComuni(REGIONE) : css("--linea");
  stato.percorsi.forEach((p) => p.setAttribute("fill", fondo));
  if (stato.mappa) coloraMappa(stato.mappa);
});
caricaMappa().catch((e) => messaggio(`Mappa non disponibile: ${e.message}`, true));
