"use strict";
// Dati storici: catalogo (/api/storici/catalogo) → scelta di dataset, grandezze, periodo, frequenza e area →
// stima (/api/storici/stima) → file CSV o Excel (/api/storici/estrai). Nessun dato dell'utente viene inviato
// oltre ai filtri scelti.
const API = "/api/storici";
const $ = (id) => document.getElementById(id);
const NS = "http://www.w3.org/2000/svg";
const stato = {
  catalogo: null, ds: null, regione: (window.EUGENIO && window.EUGENIO.regione) || "08",
  nomiRegioni: new Map(), mappa: null, percorsi: new Map(), comuniRegione: [], province: [],
  scelti: new Map(),       // istat → {nome, prov}: comuni scelti uno per uno (anche di regioni diverse)
  inclusi: new Set(),      // comuni della regione mostrata che rientrano nella selezione
  stima: null, richiestaStima: 0, controllo: null, attesa: null, scaricando: false,
};

function h(tag, cls, testo) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (testo !== undefined && testo !== null) e.textContent = testo;
  return e;
}
function el(tag, attrs = {}, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}
const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const num = (x) => Number(x).toLocaleString("it-IT");
const dataIt = (s) => s ? s.split("-").reverse().join("/") : "—";
const normalizza = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
function messaggio(id, t, errore = false) { const m = $(id); m.textContent = t; m.classList.toggle("errore", errore); }
function radio(nome) { const r = document.querySelector(`input[name="${nome}"]:checked`); return r ? r.value : null; }
function dettaglio(d, codice) {
  if (d && typeof d.detail === "string") return d.detail;
  if (d && Array.isArray(d.detail)) return d.detail.map((x) => x.msg).join("; ");
  return `errore ${codice}`;
}

// ------------------------------------------------------------------ catalogo e dataset
async function caricaCatalogo() {
  const r = await fetch(`${API}/catalogo`);
  let d = null;
  try { d = await r.json(); } catch { /* risposta non JSON */ }
  if (!r.ok || !d) throw new Error(dettaglio(d, r.status));
  stato.catalogo = d;
  const box = $("dataset");
  box.innerHTML = "";
  if (!d.dataset.length) { messaggio("messaggio-catalogo", "Sul server non ci sono ancora dati scaricabili.", true); return; }
  messaggio("messaggio-catalogo", "");
  d.dataset.forEach((x, i) => {
    const lab = h("label", "dataset-voce");
    const inp = h("input");
    inp.type = "radio"; inp.name = "dataset"; inp.value = x.id;
    if (i === 0) inp.checked = true;
    const testi = h("span", "dataset-testi");
    testi.append(h("b", null, x.titolo));
    const meta = [];
    if (x.inizio) meta.push(`dal ${dataIt(x.inizio)} al ${dataIt(x.fine)}`);
    meta.push(`licenza ${x.licenza.length > 20 ? "Eurostat" : x.licenza}`);
    testi.append(h("small", null, meta.join(" · ")));
    const descr = h("span", "dataset-descrizione", x.descrizione);
    testi.append(descr);
    lab.append(inp, testi);
    inp.addEventListener("change", () => scegliDataset(x.id));
    box.appendChild(lab);
  });
  if (d.non_scaricabili && d.non_scaricabili.length) {
    const ul = $("non-scaricabili"); ul.innerHTML = "";
    d.non_scaricabili.forEach((x) => ul.appendChild(h("li", null, `${x.nome}: ${x.motivo}.`)));
  }
  const dalLink = new URLSearchParams(location.search).get("dataset");
  const primo = d.dataset.find((x) => x.id === dalLink) || d.dataset[0];
  document.querySelector(`input[name="dataset"][value="${primo.id}"]`).checked = true;
  scegliDataset(primo.id);
}

function scegliDataset(id) {
  const ds = stato.catalogo.dataset.find((x) => x.id === id);
  stato.ds = ds;
  document.querySelectorAll(".dataset-voce").forEach((v) => v.classList.toggle("scelto", v.querySelector("input").value === id));
  const u = new URL(location.href);
  u.searchParams.set("dataset", id);
  history.replaceState(null, "", u);
  grandezze(ds);
  periodo(ds);
  frequenze(ds);
  $("passo-area").hidden = !ds.area;
  $("passo-scarica").hidden = false;
  $("legenda-mappa").style.visibility = ds.area ? "visible" : "hidden";
  numeraPassi();
  fonti();
  colora();
  aggiornaStima();
}

function numeraPassi() {
  let n = 0;
  document.querySelectorAll(".pannello .passo h2 .n").forEach((s) => {
    if (!s.closest(".passo").hidden) s.textContent = ++n;
  });
}

// ------------------------------------------------------------------ grandezze
function spunta(nome, valore, testo, dettaglioTesto, acceso, tipo = "checkbox") {
  const l = h("label");
  const i = h("input");
  i.type = tipo; i.name = nome; i.value = valore; i.checked = !!acceso;
  i.addEventListener("change", aggiornaStima);
  l.append(i, document.createTextNode(` ${testo}`));
  if (dettaglioTesto) l.appendChild(h("small", null, ` ${dettaglioTesto}`));
  return l;
}

function grandezze(ds) {
  const box = $("grandezze"); box.innerHTML = "";
  const passo = $("passo-grandezze");
  passo.hidden = false;
  if (ds.id === "legge10") {
    $("titolo-grandezze").textContent = "Tipologia";
    const g = h("div", "spunte verticali");
    ds.tipologie.forEach((t, i) => g.appendChild(spunta("tipologia", t.id, t.nome, null, i === 0, "radio")));
    box.append(g);
    if (ds.avvertenza) box.appendChild(h("p", "avviso-legale", ds.avvertenza));
  } else if (ds.id === "eurostat_pmi") {
    $("titolo-grandezze").textContent = "Serie e tassazione";
    const s = h("div", "spunte verticali");
    ds.variabili.forEach((v) => s.appendChild(spunta("variabile", v.id, v.nome, null, v.predefinita)));
    const t = h("div", "spunte verticali");
    ds.tassazione.forEach((v) => t.appendChild(spunta("tassazione", v.id, `${v.id}`, v.nome, v.predefinita)));
    box.append(h("h3", null, "Serie"), s, h("h3", null, "Livello di tassazione"), t);
  } else if (ds.id === "comuni" || ds.id === "dpr412") {
    $("titolo-grandezze").textContent = "Colonne";
    box.append(h("p", "aiuto", `Il file contiene: ${ds.colonne.join(", ")}.`));
    if (ds.id === "dpr412") {   // tutta Italia anche come file statico del sito
      const p = h("p", "aiuto", "L'elenco di tutti i comuni italiani è anche nel file ");
      const a = h("a", null, "dpr412.csv"); a.href = "dati/dpr412.csv"; a.download = "";
      const n = h("a", null, "Normattiva"); n.href = ds.fonte_url || "https://www.normattiva.it/";
      p.append(a, " (testo del DPR su ", n, ").");
      box.appendChild(p);
    }
    if (ds.avvertenza) box.appendChild(h("p", "avviso-legale", ds.avvertenza));
  } else {
    $("titolo-grandezze").textContent = "Grandezze";
    const gruppi = new Map();
    ds.variabili.forEach((v) => { if (!gruppi.has(v.gruppo)) gruppi.set(v.gruppo, []); gruppi.get(v.gruppo).push(v); });
    const comandi = h("div", "filtri");
    for (const [testo, valore] of [["tutte", true], ["nessuna", false]]) {
      const b = h("button", "filtro", testo); b.type = "button";
      b.addEventListener("click", () => { box.querySelectorAll('input[name="variabile"]').forEach((i) => (i.checked = valore)); aggiornaStima(); });
      comandi.appendChild(b);
    }
    box.appendChild(comandi);
    for (const [gruppo, voci] of gruppi) {
      const f = h("div", "gruppo-grandezze");
      f.appendChild(h("h3", null, gruppo));
      const s = h("div", "spunte verticali");
      voci.forEach((v) => {
        const unita = v.unita_aggregata && v.unita_aggregata !== v.unita ? `${v.unita}; aggregata ${v.unita_aggregata}` : v.unita;
        s.appendChild(spunta("variabile", v.id, v.nome, `(${unita}${v.aggregazione ? ` – ${v.aggregazione}` : ""})`, v.predefinita));
      });
      f.appendChild(s);
      box.appendChild(f);
    }
  }
}

function valori(nome) { return [...document.querySelectorAll(`input[name="${nome}"]:checked`)].map((i) => i.value); }

// ------------------------------------------------------------------ periodo
function sposta(data, mesi) {
  const d = new Date(`${data}T12:00:00Z`);
  d.setUTCMonth(d.getUTCMonth() - mesi);
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10);
}

function periodo(ds) {
  const date = $("periodo-date"), stag = $("periodo-stagioni");
  $("passo-periodo").hidden = !ds.periodo;
  date.hidden = !(ds.periodo === "date" || ds.periodo === "semestri");
  stag.hidden = ds.periodo !== "stagioni";
  for (const id of ["dal", "al", "fino-al"]) { $(id).min = ds.inizio || ""; $(id).max = ds.fine || ""; }
  if (ds.periodo === "stagioni") { $("fino-al").value = ds.fine; return; }
  if (!ds.inizio) return;
  $("periodi-rapidi").hidden = ds.periodo === "semestri";
  const mesi = ds.id === "meteo_orario" ? 1 : ds.periodo === "semestri" ? 0 : 12;
  impostaPeriodo(mesi);
  $("limiti-periodo").textContent = ds.periodo === "semestri"
    ? `Prezzi semestrali dal ${dataIt(ds.inizio)} al ${dataIt(ds.fine)}: si includono i semestri che toccano il periodo scelto.`
    : `Dati disponibili dal ${dataIt(ds.inizio)} al ${dataIt(ds.fine)}.`;
}

function impostaPeriodo(mesi) {
  const ds = stato.ds;
  $("al").value = ds.fine;
  $("dal").value = mesi ? [sposta(ds.fine, mesi), ds.inizio].sort().pop() : ds.inizio;
  document.querySelectorAll("#periodi-rapidi .filtro").forEach((b) => b.setAttribute("aria-pressed", String(+b.dataset.mesi === mesi)));
}
document.querySelectorAll("#periodi-rapidi .filtro").forEach((b) => b.addEventListener("click", () => { impostaPeriodo(+b.dataset.mesi); aggiornaStima(); }));
for (const id of ["dal", "al"]) $(id).addEventListener("change", () => {
  document.querySelectorAll("#periodi-rapidi .filtro").forEach((b) => b.setAttribute("aria-pressed", "false"));
  aggiornaStima();
});
for (const id of ["fino-al", "stagioni", "copertura", "provincia"]) $(id).addEventListener("change", () => { colora(); aggiornaStima(); });

// ------------------------------------------------------------------ frequenza
const AIUTO_FREQUENZA = "Medie per temperatura, umidità, vento e nuvolosità; somme per radiazione, pioggia, neve e gradi " +
  "giorno; minimo e massimo per le temperature minime e massime. Il periodo si allarga a mesi, anni o stagioni interi; " +
  "i periodi con meno dati della soglia restano vuoti e il file riporta dati validi e attesi.";
const NOMI_BREVI = { oraria: "Oraria", giornaliera: "Giornaliera", mensile: "Mensile", annuale: "Annuale", stagione: "Stagione" };

function frequenze(ds) {
  const box = $("frequenze"); box.innerHTML = "";
  $("passo-frequenza").hidden = !ds.frequenze.length;
  const predefinita = ds.id === "gradi_giorno" ? "mensile" : ds.frequenza_nativa;
  ds.frequenze.forEach((f) => {
    const l = h("label");
    const i = h("input");
    i.type = "radio"; i.name = "frequenza"; i.value = f.id; i.checked = f.id === predefinita;
    i.title = f.nome;
    i.addEventListener("change", () => { copertura(); aggiornaStima(); });
    l.append(i, h("span", null, NOMI_BREVI[f.id] || f.nome));
    box.appendChild(l);
  });
  copertura();
}
function copertura() {
  const ds = stato.ds, f = radio("frequenza");
  const aggregata = ds && f && f !== ds.frequenza_nativa;
  $("blocco-copertura").hidden = !aggregata;
  $("aiuto-frequenza").textContent = aggregata ? (f === "stagione" ? "Stagione di riscaldamento dal 1 luglio al 30 giugno. " : "") + AIUTO_FREQUENZA : "";
}

// ------------------------------------------------------------------ area e mappa
async function caricaRegione(cod) {
  stato.regione = cod;
  const r = await fetch(`dati/mappa/${cod}.json`);
  if (!r.ok) throw new Error(`mappa non disponibile (${r.status})`);
  const m = await r.json();
  const box = $("mappa");
  box.querySelectorAll("svg").forEach((s) => s.remove());
  stato.percorsi.clear();
  const svg = el("svg", { viewBox: m.viewBox.join(" "), role: "img", "aria-label": `Mappa dei comuni: ${m.nome}` });
  box.prepend(svg);
  const g = el("g", {}, svg);
  for (const c of m.comuni) {
    const p = el("path", { d: c.d, fill: css("--linea") }, g);
    p.addEventListener("click", () => tocca(c));
    p.addEventListener("mousemove", (e) => etichetta(e, `${c.nome} (${c.prov})`));
    p.addEventListener("mouseleave", () => ($("etichetta").style.display = "none"));
    stato.percorsi.set(c.istat, p);
  }
  if (m.province) {
    const gp = el("g", { class: "province" }, svg);
    for (const pr of m.province) el("path", { d: pr.d }, gp);
  }
  if (window.EUGENIO && window.EUGENIO.sfondoItalia) {
    window.EUGENIO.sfondoItalia(svg).catch(() => {});
    window.EUGENIO.mappaGrande(svg, m.viewBox);
  }
  stato.comuniRegione = m.comuni.map((c) => ({ istat: c.istat, nome: c.nome, prov: c.prov, chiave: normalizza(c.nome) }))
    .sort((a, b) => a.nome.localeCompare(b.nome, "it"));
  stato.province = (m.province || []).map((p) => ({ sigla: p.sigla, nome: p.nome })).sort((a, b) => a.nome.localeCompare(b.nome, "it"));
  stato.nomeRegione = m.nome;
  const sel = $("provincia"); sel.innerHTML = "";
  stato.province.forEach((p) => { const o = h("option", null, `${p.nome} (${p.sigla})`); o.value = p.sigla; sel.appendChild(o); });
  areaTesti();
  colora();
}

function etichetta(e, testo) {
  const et = $("etichetta"), box = $("mappa").getBoundingClientRect();
  et.textContent = testo;
  et.style.display = "block";
  et.style.left = `${Math.max(0, Math.min(e.clientX - box.left + 12, box.width - et.offsetWidth))}px`;
  et.style.top = `${e.clientY - box.top + 12}px`;
}

function tocca(c) {
  if (!stato.ds || !stato.ds.area) return;
  if (radio("area") !== "comuni") {
    // primo tocco: si passa alla scelta per comuni, partendo da quello toccato
    document.querySelector('input[name="area"][value="comuni"]').checked = true;
    stato.scelti.clear();
  }
  if (stato.scelti.has(c.istat)) stato.scelti.delete(c.istat);
  else stato.scelti.set(c.istat, { nome: c.nome, prov: c.prov });
  areaTesti();
  colora();
  aggiornaStima();
}

function areaTesti() {
  const tipo = radio("area");
  $("area-provincia").hidden = tipo !== "provincia";
  $("area-comuni").hidden = tipo !== "comuni";
  const nome = stato.nomeRegione || stato.nomiRegioni.get(stato.regione) || stato.regione;
  const testi = {
    regione: `Tutti i comuni della regione ${nome}. Per un'altra regione toccala sulla piccola mappa accanto al titolo.`,
    provincia: `Una provincia della regione ${nome}.`,
    comuni: "Cerca i comuni per nome o toccali sulla mappa; tocca di nuovo per toglierli.",
    tutti: `Tutti i comuni con dati meteo sul server (${num(stato.catalogo ? stato.catalogo.comuni : 0)}).`,
  };
  $("area-regione").textContent = testi[tipo];
  const servite = stato.catalogo ? stato.catalogo.regioni : [];
  const avviso = $("avviso-regione");
  avviso.hidden = !(stato.catalogo && servite.length && !servite.includes(stato.regione) && (tipo === "regione" || tipo === "provincia"));
  if (!avviso.hidden) {
    const nomi = servite.map((c) => stato.nomiRegioni.get(c) || c).join(", ");
    avviso.textContent = `Per ${nome} il server non ha ancora i dati meteo dei comuni. Regioni disponibili: ${nomi}.`;
  }
  chips();
}

function chips() {
  const box = $("comuni-scelti"); box.innerHTML = "";
  if (!stato.scelti.size) { box.appendChild(h("span", "aiuto", "Nessun comune scelto.")); return; }
  [...stato.scelti].sort((a, b) => a[1].nome.localeCompare(b[1].nome, "it")).forEach(([istat, c]) => {
    const b = h("button", "comune-chip");
    b.type = "button";
    b.textContent = `${c.nome} (${c.prov})`;
    b.setAttribute("aria-label", `Togli ${c.nome}`);
    b.addEventListener("click", () => { stato.scelti.delete(istat); chips(); colora(); aggiornaStima(); });
    box.appendChild(b);
  });
  if (stato.scelti.size > 1) {
    const via = h("button", "filtro", "togli tutti");
    via.type = "button";
    via.addEventListener("click", () => { stato.scelti.clear(); chips(); colora(); aggiornaStima(); });
    box.appendChild(via);
  }
}

$("cerca-comune").addEventListener("input", (e) => {
  const q = normalizza(e.target.value), ul = $("risultati-comuni");
  ul.innerHTML = "";
  if (q.length < 2) return;
  const trovati = stato.comuniRegione.filter((c) => c.chiave.includes(q))
    .sort((a, b) => (b.chiave.startsWith(q) - a.chiave.startsWith(q)) || a.nome.localeCompare(b.nome, "it")).slice(0, 8);
  if (!trovati.length) { ul.appendChild(h("li", "aiuto", `Nessun comune trovato in ${stato.nomeRegione}.`)); return; }
  trovati.forEach((c) => {
    const li = h("li"), b = h("button", null, `${c.nome} (${c.prov})${stato.scelti.has(c.istat) ? " – già scelto" : ""}`);
    b.type = "button";
    b.addEventListener("click", () => {
      stato.scelti.set(c.istat, { nome: c.nome, prov: c.prov });
      $("cerca-comune").value = ""; ul.innerHTML = "";
      chips(); colora(); aggiornaStima();
      $("cerca-comune").focus();
    });
    li.appendChild(b); ul.appendChild(li);
  });
});

document.querySelectorAll('input[name="area"]').forEach((i) => i.addEventListener("change", () => { areaTesti(); colora(); aggiornaStima(); }));
$("capoluoghi").addEventListener("change", aggiornaStima);

// colori della mappa: nel colore principale del vestito i comuni che rientrano nella selezione (i capoluoghi li conosce solo il server)
function colora() {
  if (!stato.percorsi.size) return;
  const tipo = radio("area"), prov = $("provincia").value;
  const attiva = stato.ds && stato.ds.area;
  const servita = !stato.catalogo || stato.catalogo.regioni.includes(stato.regione);
  const dentroColore = css("--primario"), grigio = css("--linea");
  stato.inclusi.clear();
  for (const c of stato.comuniRegione) {
    const dentro = attiva && servita && (tipo === "tutti" || tipo === "regione" || (tipo === "provincia" && c.prov === prov)
      || (tipo === "comuni" && stato.scelti.has(c.istat)));
    if (dentro) stato.inclusi.add(c.istat);
    const p = stato.percorsi.get(c.istat);
    p.setAttribute("fill", dentro ? dentroColore : grigio);
    p.classList.toggle("scelto", tipo === "comuni" && stato.scelti.has(c.istat));
  }
}

// ------------------------------------------------------------------ richiesta, stima e download
function richiesta() {
  const ds = stato.ds;
  const r = { dataset: ds.id, copertura: +$("copertura").value };
  if (ds.periodo === "date" || ds.periodo === "semestri") { r.dal = $("dal").value || null; r.al = $("al").value || null; }
  if (ds.periodo === "stagioni") { r.stagioni = +$("stagioni").value; r.al = $("fino-al").value || null; }
  if (ds.frequenze.length) r.frequenza = radio("frequenza");
  if (ds.id === "legge10") r.tipologia = radio("tipologia");
  else if (ds.id !== "comuni" && ds.id !== "dpr412") r.variabili = valori("variabile");
  if (ds.id === "eurostat_pmi") r.tassazione = valori("tassazione");
  if (ds.area) {
    const tipo = radio("area");
    r.area = { tipo, solo_capoluoghi: $("capoluoghi").checked };
    if (tipo === "regione") r.area.regione = stato.regione;
    if (tipo === "provincia") r.area.provincia = $("provincia").value;
    if (tipo === "comuni") r.area.comuni = [...stato.scelti.keys()];
  }
  return r;
}

function controllaLocale(r) {
  const ds = stato.ds;
  if (!["comuni", "dpr412", "legge10"].includes(ds.id) && r.variabili && !r.variabili.length)
    return ds.id === "eurostat_pmi" ? "Scegli almeno una serie." : "Scegli almeno una grandezza.";
  if (ds.id === "eurostat_pmi" && !r.tassazione.length) return "Scegli almeno un livello di tassazione.";
  if (r.dal && r.al && r.dal > r.al) return "La data di inizio è successiva a quella di fine.";
  if (r.area && r.area.tipo === "comuni" && !r.area.comuni.length) return "Scegli almeno un comune: cercalo per nome o toccalo sulla mappa.";
  if (r.area && r.area.tipo === "provincia" && !r.area.provincia) return "Scegli la provincia.";
  return null;
}

function aggiornaStima() {
  clearTimeout(stato.attesa);
  $("scarica").disabled = true;
  stato.attesa = setTimeout(stima, 300);
}

async function stima() {
  if (!stato.ds) return;
  const r = richiesta(), formato = radio("formato");
  aiutoFormato(formato);
  const box = $("stima"); box.innerHTML = ""; $("suggerimenti").innerHTML = "";
  const errore = controllaLocale(r);
  if (errore) { messaggio("messaggio", errore, true); stato.stima = null; return; }
  const n = ++stato.richiestaStima;
  if (stato.controllo) stato.controllo.abort();
  stato.controllo = new AbortController();
  messaggio("messaggio", "Calcolo della dimensione del file…");
  try {
    const risp = await fetch(`${API}/stima?formato=${formato}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(r), signal: stato.controllo.signal,
    });
    let d = null;
    try { d = await risp.json(); } catch { /* risposta non JSON */ }
    if (n !== stato.richiestaStima) return;
    if (!risp.ok) throw new Error(dettaglio(d, risp.status));
    stato.stima = d;
    mostraStima(d);
  } catch (e) {
    if (e.name === "AbortError" || n !== stato.richiestaStima) return;
    stato.stima = null;
    messaggio("messaggio", e.message, true);
  }
}

function cifra(valore, testo) {
  const d = h("div", "cifra");
  d.append(h("b", null, valore), h("span", null, testo));
  return d;
}

function mostraStima(d) {
  const box = $("stima"); box.innerHTML = "";
  box.append(cifra(num(d.righe), "righe circa"), cifra(num(d.colonne), "colonne"), cifra(d.dimensione, "dimensione stimata"));
  if (d.comuni !== null && d.comuni !== undefined) box.append(cifra(num(d.comuni), d.comuni === 1 ? "comune" : "comuni"));
  const ul = $("suggerimenti"); ul.innerHTML = "";
  const righe = [];
  if (d.dal && d.al && stato.ds.periodo !== "stagioni") righe.push(`Periodo estratto: dal ${dataIt(d.dal)} al ${dataIt(d.al)}.`);
  righe.push(...d.avvisi);
  if (d.consentito) {
    messaggio("messaggio", righe.join(" "));
    $("scarica").disabled = stato.scaricando;
  } else {
    messaggio("messaggio", `${d.motivo}${d.suggerimenti.length ? " Per ridurre la richiesta:" : ""}`, true);
    d.suggerimenti.forEach((s) => ul.appendChild(h("li", null, s)));
    $("scarica").disabled = true;
  }
}

function aiutoFormato(formato) {
  const lim = stato.catalogo ? stato.catalogo.limiti : null;
  $("aiuto-formato").textContent = formato === "csv"
    ? `CSV per Excel italiano: separatore punto e virgola, decimali con la virgola, UTF-8; unità nelle intestazioni, fonti in fondo al file${lim ? `. Fino a ${num(lim.righe_csv)} righe` : ""}.`
    : `Un foglio "Dati" e un foglio "Info" con filtri scelti, fonti, licenze e significato delle colonne${lim ? `. Fino a ${num(lim.righe_xlsx)} righe` : ""}.`;
}
document.querySelectorAll('input[name="formato"]').forEach((i) => i.addEventListener("change", aggiornaStima));

function fonti() {
  const ds = stato.ds, f = $("fonti");
  f.innerHTML = "";
  f.append(h("b", null, "Fonti e licenza. "), `${ds.fonte} `);
  const a = h("a", null, `Licenza: ${ds.licenza}`);
  a.href = ds.licenza_url; a.rel = "license";
  const l = h("a", null, "CC BY 4.0"); l.href = "licenza.html#dati";
  f.append(a, ". Le elaborazioni di EuGEnio hanno licenza ", l, ": se riusi i dati, cita EuGEnio come fonte "
    + "(«Fonte: EuGEnio – eugenio.statocritico.it» con la data di estrazione) e le fonti originali. Sono scritte anche nel file.");
}

$("scarica").addEventListener("click", async () => {
  const r = richiesta(), formato = radio("formato");
  const b = $("scarica"), barra = $("avanzamento"), riemp = barra.querySelector("span");
  stato.scaricando = true;
  b.disabled = true;
  barra.hidden = false; riemp.style.width = "3%";
  messaggio("messaggio", "Preparazione del file…");
  try {
    const risp = await fetch(`${API}/estrai?formato=${formato}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(r),
    });
    if (!risp.ok) {
      let d = null;
      try { d = await risp.json(); } catch { /* risposta non JSON */ }
      throw new Error(dettaglio(d, risp.status));
    }
    const attesi = (stato.stima && stato.stima.byte) || 0;
    const lettore = risp.body.getReader(), pezzi = [];
    let ricevuti = 0;
    for (;;) {
      const { done, value } = await lettore.read();
      if (done) break;
      pezzi.push(value);
      ricevuti += value.length;
      if (attesi) riemp.style.width = `${Math.min(97, 3 + 94 * ricevuti / attesi)}%`;
      messaggio("messaggio", `Scaricamento… ${(ricevuti / 1048576).toLocaleString("it-IT", { maximumFractionDigits: 1 })} MB`);
    }
    const disp = risp.headers.get("Content-Disposition") || "";
    const nome = (disp.match(/filename="([^"]+)"/) || [])[1] || `eugenio_${r.dataset}.${formato}`;
    const blob = new Blob(pezzi, { type: risp.headers.get("Content-Type") || "application/octet-stream" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = nome;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    riemp.style.width = "100%";
    messaggio("messaggio", `File pronto: ${nome}.`);
  } catch (e) {
    messaggio("messaggio", `Download non riuscito: ${e.message}`, true);
  } finally {
    stato.scaricando = false;
    b.disabled = !(stato.stima && stato.stima.consentito);
    setTimeout(() => { barra.hidden = true; riemp.style.width = "0"; }, 1500);
  }
});

// ------------------------------------------------------------------ avvio
if (window.EUGENIO) {
  // la piccola mappa cambia regione senza ricaricare la pagina: i comuni già scelti restano
  window.EUGENIO.suRegione = (cod) => caricaRegione(cod).then(aggiornaStima).catch((e) => messaggio("messaggio", `Mappa non disponibile: ${e.message}`, true));
  window.EUGENIO.italia().then((m) => { m.regioni.forEach((r) => stato.nomiRegioni.set(r.cod, r.nome)); areaTesti(); }).catch(() => {});
}
caricaRegione(stato.regione).catch((e) => messaggio("messaggio-catalogo", `Mappa non disponibile: ${e.message}`, true));
caricaCatalogo().then(() => { areaTesti(); colora(); })
  .catch((e) => messaggio("messaggio-catalogo", `Elenco dei dati non disponibile: ${e.message}`, true));
