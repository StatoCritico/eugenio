"use strict";
// Interfaccia: mappa dei comuni, ricerca indirizzo, invio del CSV, grafico della previsione.
const API = "/api";
const $ = (id) => document.getElementById(id);
const NS = "http://www.w3.org/2000/svg";
const stato = { istat: null, comuni: new Map(), percorsi: new Map(), file: null };

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
    const t = el("title", {}, p); t.textContent = c.nome;
    stato.percorsi.set(c.istat, p);
    stato.comuni.set(c.istat, { ...stato.comuni.get(c.istat), nome: c.nome, prov: c.prov, x: c.x, y: c.y });
    p.addEventListener("click", () => scegli(c.istat));
    p.addEventListener("mousemove", (e) => mostraEtichetta(e, c.istat));
    p.addEventListener("mouseleave", () => ($("etichetta").style.display = "none"));
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
  try { coloraMappa(await json(`${API}/mappa?giorni=7`)); } catch { $("scala-min").textContent = "previsioni meteo non disponibili"; }
}

function coloraMappa(d) {
  stato.mappa = d;
  const v = Object.values(d.comuni).map((x) => x.gg);
  if (!v.length) return;
  const min = Math.min(...v), max = Math.max(...v);
  for (const [istat, x] of Object.entries(d.comuni)) {
    const p = stato.percorsi.get(istat);
    if (!p) continue;
    p.setAttribute("fill", colore((x.gg - min) / (max - min || 1)));
    Object.assign(stato.comuni.get(istat), x);
  }
  $("scala-min").textContent = `${min.toFixed(0)} GG`;
  $("scala-max").textContent = `${max.toFixed(0)} GG`;
  $("scala-barra").style.background = `linear-gradient(90deg, ${colore(0)}, ${colore(1)})`;
}

function mostraEtichetta(e, istat) {
  const c = stato.comuni.get(istat), et = $("etichetta"), box = $("mappa").getBoundingClientRect();
  et.textContent = c.gg !== undefined ? `${c.nome}: ${c.gg} GG, media ${c.t} °C` : c.nome;
  et.style.display = "block";
  et.style.left = `${Math.min(e.clientX - box.left + 12, box.width - et.offsetWidth)}px`;
  et.style.top = `${e.clientY - box.top + 12}px`;
}

function scegli(istat, punto) {
  const c = stato.comuni.get(istat);
  if (!c) return messaggio("Questo comune non è ancora coperto dal servizio.", true);
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
  sm.textContent = c.gg !== undefined ? `Prossimi 7 giorni: ${c.gg} gradi giorno, temperatura media ${c.t} °C` : `Provincia di ${c.prov}`;
  s.append(sm);
  stato.svg.querySelectorAll(".segnaposto").forEach((x) => x.remove());
  if (punto) el("circle", { class: "segnaposto", cx: punto[0], cy: punto[1], r: 1.6 }, stato.svg);
  aggiornaBottone();
}

// ------------------------------------------------------------------ ricerca indirizzo (Zornade)
let attesa;
$("cerca").addEventListener("input", (e) => {
  clearTimeout(attesa);
  const q = e.target.value.trim();
  if (q.length < 4) { $("risultati").innerHTML = ""; return; }
  attesa = setTimeout(async () => {
    try {
      const d = await json(`${API}/geocodifica?q=${encodeURIComponent(q)}`);
      const ul = $("risultati"); ul.innerHTML = "";
      if (!d.risultati.length) { ul.innerHTML = "<li><button disabled>Nessun indirizzo trovato</button></li>"; return; }
      for (const r of d.risultati) {
        const li = document.createElement("li"), b = document.createElement("button");
        b.type = "button"; b.textContent = r.etichetta;
        b.addEventListener("click", () => scegliIndirizzo(r));
        li.appendChild(b); ul.appendChild(li);
      }
    } catch (err) { messaggio(`Ricerca indirizzi non disponibile: ${err.message}. Scegli il comune dall'elenco.`, true); }
  }, 450);
});

async function scegliIndirizzo(r) {
  $("risultati").innerHTML = "";
  $("cerca").value = r.etichetta;
  try {
    const d = await json(`${API}/particella?lat=${r.lat}&lon=${r.lon}`);
    if (!d.comune || !d.comune.istat) return messaggio("L'indirizzo è fuori dall'area coperta dal servizio.", true);
    scegli(d.comune.istat, lonlatSvg(r.lon, r.lat));
    if (d.particella) messaggio(`Particella catastale ${d.particella.etichetta || d.particella.id}` +
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
function impostaFile(f) {
  stato.file = f;
  $("nome-file").textContent = f ? `${f.name} · ${(f.size / 1024).toFixed(0)} kB` : "Scegli il file o trascinalo qui";
  $("zona-file").classList.toggle("pieno", !!f);
  aggiornaBottone();
}
$("file").addEventListener("change", (e) => impostaFile(e.target.files[0]));
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
function aggiornaBottone() { $("calcola").disabled = !(stato.istat && stato.file); }
function messaggio(t, errore = false) { const m = $("messaggio"); m.textContent = t; m.classList.toggle("errore", errore); }

$("calcola").addEventListener("click", async () => {
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
    messaggio("");
    mostraRisultato(r);
  } catch (err) {
    messaggio(`Previsione non riuscita: ${err.message}`, true);
  } finally { aggiornaBottone(); }
});

// ------------------------------------------------------------------ grafico
function mostraRisultato(r) {
  const box = $("risultato");
  const g = document.createElement("div"); g.className = "grafico"; box.appendChild(g);
  // nella pagina col pulsante del riquadro (grafici.js); disegnaPrevisione usa le misure del riquadro quando servono
  const disegna = (dest, misure) => disegnaPrevisione(dest, misure, r);
  const nome = (stato.comuni.get(r.istat) || {}).nome;
  if (window.EUGENIO_GRAFICI) window.EUGENIO_GRAFICI.registra(g, disegna, { titolo: `Previsione dei consumi${nome ? ` – ${nome}` : ""}` });
  else disegna(g, null);
  mostraDettagli(r, box);
}

const numero = (x, dec = 2) => x === null || x === undefined ? "—" : Number(x).toLocaleString("it-IT", { maximumFractionDigits: dec });
function disegnaPrevisione(g, misure, r) {
  const W = misure && misure.riquadro ? misure.larghezza : 640, H = misure && misure.riquadro ? misure.altezza : 300;
  const sx = 44, dx = 8, su = 12, gi = 28;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Grafico della previsione" }, g);
  const st = r.storico, pr = r.previsione, n0 = st.t.length, n = n0 + pr.t.length;
  const tutti = [...st.v, ...pr["0.1"], ...pr["0.9"], ...((r.verifica && r.verifica.reale) || [])].filter((x) => x !== null);
  let ymin = Math.min(...tutti), ymax = Math.max(...tutti);
  const pad = (ymax - ymin) * 0.08 || 1; ymin -= pad; ymax += pad;
  const X = (i) => sx + (W - sx - dx) * i / (n - 1), Y = (v) => su + (H - su - gi) * (1 - (v - ymin) / (ymax - ymin));
  // zone con meteo meno affidabile
  const deboli = { "previsione IFS": "meteo globale", "miscela ICON-2I/IFS": null, "climatologia": "climatologia" };
  let inizio = null;
  pr.fonte_meteo.forEach((f, i) => {
    const debole = f in deboli;
    if (debole && inizio === null) inizio = i;
    if ((!debole || i === pr.t.length - 1) && inizio !== null) {
      const fine = debole ? i : i - 1;
      el("rect", { x: X(n0 + inizio), y: su, width: X(n0 + fine) - X(n0 + inizio), height: H - su - gi, fill: "var(--tinta)", opacity: .55 }, svg);
      const t = el("text", { x: X(n0 + inizio) + 4, y: su + 12 }, svg);
      t.textContent = pr.fonte_meteo[fine] === "climatologia" ? "meteo: climatologia" : "meteo: modello globale";
      inizio = null;
    }
  });
  // griglia e assi
  for (let k = 0; k <= 4; k++) {
    const v = ymin + (ymax - ymin) * k / 4, y = Y(v);
    el("line", { x1: sx, x2: W - dx, y1: y, y2: y, stroke: "var(--linea)", "stroke-width": .6 }, svg);
    const t = el("text", { x: sx - 6, y: y + 4, "text-anchor": "end" }, svg);
    t.textContent = v.toLocaleString("it-IT", { maximumFractionDigits: v < 10 ? 1 : 0 });
  }
  const etich = [...st.t, ...pr.t], passi = Math.max(2, Math.min(12, Math.round((W - sx - dx) / 100)));
  for (let k = 0; k <= passi; k++) {
    const i = Math.round((n - 1) * k / passi), d = new Date(etich[i]);
    const t = el("text", { x: X(i), y: H - 8, "text-anchor": k === 0 ? "start" : k === passi ? "end" : "middle" }, svg);
    t.textContent = r.passo === "ora"
      ? (n > 96 ? d.toLocaleDateString("it-IT", { day: "numeric", month: "short" })
                : `${d.toLocaleDateString("it-IT", { day: "numeric", month: "short" })} ore ${d.getHours()}`)
      : d.toLocaleDateString("it-IT", { day: "numeric", month: "short", year: "2-digit" });
  }
  const area = (lo, hi, op) => {
    const su_ = pr[hi].map((v, i) => `${X(n0 + i)},${Y(v)}`), giu = pr[lo].map((v, i) => `${X(n0 + i)},${Y(v)}`).reverse();
    el("polygon", { points: [...su_, ...giu].join(" "), fill: "var(--serie-1)", opacity: op }, svg);
  };
  area("0.1", "0.9", .18); area("0.3", "0.7", .3);
  const linea = (vals, off, col, w, tratt) => {
    let dpath = "", su_ = false;
    vals.forEach((v, i) => { if (v === null) { su_ = false; return; } dpath += `${su_ ? "L" : "M"}${X(off + i)},${Y(v)}`; su_ = true; });
    el("path", { d: dpath, fill: "none", stroke: col, "stroke-width": w, "stroke-dasharray": tratt || "none", "stroke-linejoin": "round" }, svg);
  };
  linea(st.v, 0, "var(--inchiostro)", 1.3);
  if (r.verifica) linea(r.verifica.reale, n0, "var(--serie-2)", 1.6, "7 4");
  linea(pr["0.5"], n0, "var(--serie-1)", 2);
  el("line", { x1: X(n0 - .5), x2: X(n0 - .5), y1: su, y2: H - gi, stroke: "var(--tenue)", "stroke-dasharray": "2 3" }, svg);

  const leg = document.createElement("div"); leg.className = "legenda";
  leg.innerHTML = `<span><i class="linea" style="color:${"var(--inchiostro)"}"></i>dati caricati</span>` +
    (r.verifica ? `<span><i class="linea tratto" style="color:${"var(--serie-2)"}"></i>valori reali nascosti al modello</span>` : "") +
    `<span><i class="linea" style="color:${"var(--serie-1)"};border-top-width:3px"></i>previsione (mediana)</span>` +
    `<span><i style="background:${"var(--serie-1)"};opacity:.45"></i>4 casi su 10 / 8 casi su 10</span>`;
  g.appendChild(leg);

  // valori al passaggio del mouse, al tocco o con le frecce (grafici.js)
  if (window.EUGENIO_GRAFICI) {
    const quando = (t) => {
      const d = new Date(t);
      return r.passo === "ora"
        ? `${d.toLocaleDateString("it-IT", { weekday: "short", day: "numeric", month: "long", year: "numeric" })}, ore ${d.getHours()}`
        : d.toLocaleDateString("it-IT", { weekday: "short", day: "numeric", month: "long", year: "numeric" });
    };
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
      return { x: X(i), titolo: quando(t), righe, segni };
    });
    window.EUGENIO_GRAFICI.osserva(svg, punti, { area: [sx, su, W - dx, H - gi] });
  }
}

// cifre della verifica, avvisi e pulsanti per scaricare, sotto il grafico
function mostraDettagli(r, box) {
  const pr = r.previsione;

  if (r.verifica) {
    const v = r.verifica, d = document.createElement("div"); d.className = "verifica";
    const fmt = (x, p) => x === null ? "—" : p ? `${(x * 100).toFixed(0)} %` : x.toLocaleString("it-IT", { maximumFractionDigits: 2 });
    d.innerHTML = `<div><b>${fmt(v.wape, true)}</b><span>errore relativo complessivo (WAPE)</span></div>` +
      `<div><b>${fmt(v.mae)}</b><span>errore medio per ${r.passo}</span></div>` +
      `<div><b>${fmt(v.copertura_80, true)}</b><span>valori reali dentro la fascia larga (atteso 80 %)</span></div>`;
    box.appendChild(d);
  }
  if (r.avvisi.length) {
    const ul = document.createElement("ul"); ul.className = "avvisi";
    r.avvisi.forEach((a) => { const li = document.createElement("li"); li.textContent = a; ul.appendChild(li); });
    box.appendChild(ul);
  }
  const scarica = document.createElement("div"); scarica.className = "scarica";
  const csvBtn = document.createElement("button");
  csvBtn.type = "button"; csvBtn.className = "bottone secondario"; csvBtn.textContent = "Scarica la previsione (CSV)";
  csvBtn.addEventListener("click", () => {
    const q = ["0.1", "0.3", "0.5", "0.7", "0.9"];
    const righe = ["data;" + q.map((x) => `q${x.replace(".", "")}`).join(";") + ";fonte_meteo"];
    pr.t.forEach((t, i) => righe.push([t, ...q.map((x) => String(pr[x][i]).replace(".", ",")), pr.fonte_meteo[i]].join(";")));
    // fonti e licenza in fondo (licenza.html#dati): previsione di EuGEnio CC BY 4.0, riuso citando EuGEnio come fonte
    righe.push("", "Fonte meteo;Weather data by Open-Meteo.com (CC BY 4.0): Arpae ICON-2I, DWD ICON, ECMWF IFS, ERA5 Copernicus",
      "Licenza;Previsione elaborata da EuGEnio con il modello TiRex-2 sui consumi forniti; licenza CC BY 4.0 "
      + "(https://creativecommons.org/licenses/by/4.0/deed.it): si può riutilizzare citando EuGEnio come fonte e Open-Meteo. "
      + "Dettagli: https://eugenio.statocritico.it/licenza.html#dati",
      `Come citare;Fonte: EuGEnio – eugenio.statocritico.it (dati estratti il ${new Date().toLocaleDateString("it-IT")})`);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob(["\ufeff" + righe.join("\r\n")], { type: "text/csv;charset=utf-8" }));
    a.download = `previsione_${r.istat}_${r.modalita}.csv`; a.click();
  });
  scarica.appendChild(csvBtn);
  box.appendChild(scarica);
  if (window.EUGENIO_REPORT) {
    const richiesta = stato.richiesta;
    window.EUGENIO_REPORT.pulsanti(box, {
      tipo: "previsione",
      corpo: () => corpoReport(r, richiesta),
      nome: (ext) => `previsione_${r.istat}_${r.modalita}.${ext}`,
      messaggio, area: "messaggio",
    });
  }
}

// corpo del report: la risposta di /api/previsione così com'è, più le scelte fatte nella pagina
function corpoReport(r, richiesta) { return { ...r, richiesta: richiesta || null }; }

disegnaCovariate();

// cambio di tema o di vestito (aspetto.js, senza ricaricare la pagina): i grafici usano "var(--…)" e cambiano da
// soli; qui si rifanno i colori calcolati della mappa (fondo dei comuni e scala dei gradi giorno)
document.addEventListener("eugenio:aspetto", () => {
  scala = null;
  const fondo = window.EUGENIO && window.EUGENIO.fondoComuni ? window.EUGENIO.fondoComuni(REGIONE) : css("--linea");
  stato.percorsi.forEach((p) => p.setAttribute("fill", fondo));
  if (stato.mappa) coloraMappa(stato.mappa);
});
caricaMappa().catch((e) => messaggio(`Mappa non disponibile: ${e.message}`, true));
