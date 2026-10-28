"use strict";
// Indicatori della spesa energetica degli enti del SSN: file statici dati/indicatori/indice.json (Italia, consolidati
// regionali, fonti) e dati/indicatori/RR.json (enti della regione), prodotti da `python -m indicatori_ssn aggiorna`
// (fase 8). Le formule sono le stesse di indicatori_ssn/calcolo.py: spesa = BA1610 + BA1660 + BA1670 (o una sola
// componente); leva = AZ9999 / spesa; incidenza = spesa / AZ9999; peso = spesa / BZ9999; € per giornata, posto letto,
// cittadino = spesa / giornate di degenza ordinaria, posti letto pubblici, residenti al 31/12.
const $ = (id) => document.getElementById(id);
const NS = "http://www.w3.org/2000/svg";
const BASE = "dati/indicatori/";
const COMPONENTI = { totale: ["BA1610", "BA1660", "BA1670"], riscaldamento: ["BA1610"], elettricita: ["BA1660"], altre: ["BA1670"] };
const NOMI_COMP = { totale: "totale energia e utenze", riscaldamento: "riscaldamento", elettricita: "energia elettrica", altre: "altre utenze (gas, acqua)" };
const PARTI = [["BA1610", "Riscaldamento", "--ind-risc"], ["BA1660", "Energia elettrica", "--ind-ele"], ["BA1670", "Altre utenze (gas, acqua)", "--ind-altre"]];
// colori: variabili --ind-* di stile.css, alias delle serie --serie-1…3; tratti come le serie: continua, 7 4, 2 3
const SERIE = [["ente", "--ind-ente", null], ["regione", "--ind-regione", "7 4"], ["italia", "--ind-italia", "2 3"]];
const INDICATORI = {
  spesa: { nome: "Spesa per energia e utenze", unita: "€", dec: 0 },
  leva: { nome: "Leva", unita: "volte", dec: 1, lettura: "Euro di valore della produzione per ogni euro speso in energia e utenze: più è alta, meglio è.", meglio: "alto" },
  incidenza: { nome: "Incidenza", unita: "%", dec: 2, perc: true, lettura: "Quota della spesa energetica sul valore della produzione (l'inverso della leva): più è bassa, meglio è.", meglio: "basso" },
  peso: { nome: "Peso", unita: "%", dec: 2, perc: true, lettura: "Quota della spesa energetica sui costi della produzione: più è bassa, meglio è.", meglio: "basso" },
  per_cittadino: { nome: "Per cittadino", unita: "€", dec: 2, lettura: "Spesa energetica divisa per i residenti al 31 dicembre.", meglio: "basso" },
  per_giornata: { nome: "Per giornata di degenza", unita: "€", dec: 2, lettura: "Spesa energetica divisa per le giornate di degenza ordinaria negli ospedali pubblici (solo Emilia-Romagna).", meglio: "basso" },
  per_posto: { nome: "Per posto letto", unita: "€", dec: 0, lettura: "Spesa energetica divisa per i posti letto pubblici al 31 dicembre (solo Emilia-Romagna).", meglio: "basso" },
};
const stato = {
  indice: null, regioni: new Map(), regione: null, dati: null, chiave: null, comp: "totale", mostra: false,
  anno: null, rapporto: "incidenza", unitario: "per_cittadino", tabella: "ente", richiesta: 0,
};

function h(tag, cls, testo) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (testo !== undefined && testo !== null) e.textContent = testo;
  return e;
}
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
const num = (x, dec = 0) => (x === null || x === undefined || !Number.isFinite(x)) ? "n.d."
  : Number(x).toLocaleString("it-IT", { minimumFractionDigits: dec, maximumFractionDigits: dec });
function messaggio(t, errore = false) { const m = $("messaggio"); m.textContent = t; m.classList.toggle("errore", errore); }
function valore(ind, x) {
  const d = INDICATORI[ind];
  if (x === null || x === undefined || !Number.isFinite(x)) return "n.d.";
  if (d.perc) return `${num(x * 100, d.dec)} %`;
  if (ind === "leva") return `${num(x, d.dec)}x`;
  return `${num(x, d.dec)} €`;
}
function euroBreve(x) {
  const a = Math.abs(x);
  if (a >= 1e9) return `${num(x / 1e9, a >= 1e10 ? 0 : 1)} mld`;
  if (a >= 1e6) return `${num(x / 1e6, a >= 1e7 ? 0 : 1)} mln`;
  if (a >= 1e3) return `${num(x / 1e3, 0)} mila`;
  return num(x, 0);
}

// ------------------------------------------------------------------ calcolo (come calcolo.py)
const div = (a, b) => (a === null || a === undefined || b === null || b === undefined || b === 0) ? null : a / b;
function spesa(u, i, comp = stato.comp) {
  const v = COMPONENTI[comp].map((k) => u.v[k][i]);
  if (v.every((x) => x === null || x === undefined)) return null;
  return v.reduce((s, x) => s + (x || 0), 0);
}
function indicatori(u, i, comp = stato.comp) {
  if (!u) return {};
  const s = spesa(u, i, comp), g = (k) => (u[k] ? u[k][i] : null);
  return { spesa: s, leva: div(u.v.AZ9999[i], s), incidenza: div(s, u.v.AZ9999[i]), peso: div(s, u.v.BZ9999[i]),
    per_giornata: div(s, g("gg")), per_posto: div(s, g("pl")), per_cittadino: div(s, g("pop")) };
}
const anni = () => stato.indice.anni;
const provvisorio = (a) => stato.indice.provvisori.includes(a);

// ------------------------------------------------------------------ dati
async function json(url) {
  const r = await fetch(url, { cache: "no-cache" });
  if (!r.ok) throw new Error(`${url.split("?")[0]} non disponibile (${r.status})`);
  return r.json();
}
async function carica() {
  messaggio("Caricamento dei dati…");
  try {
    stato.indice = await json(`${BASE}indice.json`);
  } catch (e) {
    throw new Error(/\(404\)/.test(e.message) ? "i dati non sono ancora stati pubblicati sul server, riprova più tardi." : e.message);
  }
  const sel = $("regione");
  for (const r of stato.indice.regioni) {
    stato.regioni.set(r.mappa, r);
    const o = h("option", null, r.nome); o.value = r.mappa; sel.appendChild(o);
  }
  sel.addEventListener("change", () => cambiaRegione(sel.value, true));
  const a = $("anno");
  const consolidati = anni().filter((x) => !provvisorio(x));
  [...anni()].reverse().forEach((x) => { const o = h("option", null, provvisorio(x) ? `${x} (provvisorio)` : String(x)); o.value = x; a.appendChild(o); });
  stato.anno = consolidati.length ? consolidati[consolidati.length - 1] : anni()[anni().length - 1];
  a.value = stato.anno;
  a.addEventListener("change", () => { stato.anno = +a.value; mostra(); });
  $("componente").addEventListener("change", (e) => { stato.comp = e.target.value; mostra(); });
  $("mostra-componenti").addEventListener("change", (e) => { stato.mostra = e.target.checked; mostra(); });
  $("ente").addEventListener("change", (e) => scegliEnte(e.target.value));
  const reg = (window.EUGENIO && window.EUGENIO.regione) || "08";
  if (window.EUGENIO) window.EUGENIO.suRegione = (cod) => cambiaRegione(cod, false);
  await cambiaRegione(stato.regioni.has(reg) ? reg : "08", false, new URLSearchParams(location.search).get("ente"));
}

async function cambiaRegione(cod, dallElenco, enteRichiesto) {
  const n = ++stato.richiesta;
  stato.regione = cod;
  $("regione").value = cod;
  if (dallElenco) aggiornaMinimappa(cod);
  const u = new URL(location.href);
  u.searchParams.set("regione", cod);
  if (!enteRichiesto) u.searchParams.delete("ente");
  history.replaceState(null, "", u);
  messaggio("Caricamento degli enti…");
  try {
    const d = await json(`${BASE}${stato.regioni.get(cod).file}?v=${encodeURIComponent(stato.indice.aggiornato)}`);
    if (n !== stato.richiesta) return;
    stato.dati = d;
    messaggio("");
  } catch (e) {
    if (n !== stato.richiesta) return;
    messaggio(`Dati della regione non disponibili: ${e.message}`, true);
    return;
  }
  riempiEnti(enteRichiesto);
}

// la piccola mappa segue la scelta fatta dall'elenco (la regione resta ricordata come nelle altre pagine)
function aggiornaMinimappa(cod) {
  if (window.EUGENIO && window.EUGENIO.seleziona) window.EUGENIO.seleziona(cod);
}

function etichettaEnte(e) {
  const [da, a] = e.anni_presenti || [];
  const ultimo = anni()[anni().length - 1];
  const periodo = a !== undefined && a < ultimo ? ` (fino al ${a})` : da !== undefined && da > anni()[0] ? ` (dal ${da})` : "";
  return `${e.nome}${periodo}`;
}

function riempiEnti(richiesto) {
  const sel = $("ente"); sel.innerHTML = "";
  const piu = stato.dati.ambiti.length > 1;
  let predefinito = null;
  for (const amb of stato.dati.ambiti) {
    const g = piu ? h("optgroup") : sel;
    if (piu) { g.label = amb.nome; sel.appendChild(g); }
    if (stato.indice.consolidati[amb.ce]) {
      const o = h("option", null, stato.indice.consolidati[amb.ce].nome); o.value = `${amb.ce}-999`; g.appendChild(o);
      if (!predefinito) predefinito = o.value;
    }
    [...amb.enti].sort((a, b) => a.nome.localeCompare(b.nome, "it")).forEach((e) => {
      const o = h("option", null, etichettaEnte(e)); o.value = `${amb.ce}-${e.cod}`; g.appendChild(o);
    });
  }
  if (stato.regione === "08" && !richiesto) predefinito = "080-114";        // AUSL della Romagna
  const valido = (k) => k && [...sel.options].some((o) => o.value === k);
  scegliEnte(valido(richiesto) ? richiesto : valido(predefinito) ? predefinito : (sel.options[0] || {}).value);
  $("nota-ente").textContent = "Ci sono tutte le aziende presenti nei conti economici e il consolidato della regione. "
    + "Manca la gestione sanitaria accentrata (GSA): non è un'azienda ma la contabilità dei fondi che la regione gestisce "
    + "direttamente, ed è già compresa nel consolidato.";
}

function unita(chiave) {
  if (!chiave) return null;
  const [ce, cod] = chiave.split("-");
  if (cod === "999") return stato.indice.consolidati[ce] || null;
  const amb = stato.dati.ambiti.find((a) => a.ce === ce);
  return amb ? amb.enti.find((e) => e.cod === cod) || null : null;
}

function scegliEnte(chiave) {
  stato.chiave = chiave;
  $("ente").value = chiave || "";
  const u = new URL(location.href);
  if (chiave) u.searchParams.set("ente", chiave); else u.searchParams.delete("ente");
  history.replaceState(null, "", u);
  mostra();
}

// le tre unità del confronto; per un consolidato la "regione" è l'ente stesso e non si ripete
function terne() {
  const ente = unita(stato.chiave);
  if (!ente) return null;
  const consolidato = ente.cod === "999";
  return { ente, regione: consolidato ? null : stato.indice.consolidati[ente.reg] || null, italia: stato.indice.italia, consolidato };
}
function nomeRegione(reg) {
  const amb = stato.dati.ambiti.find((a) => a.ce === reg);
  return amb ? amb.nome : "Regione";
}

// ------------------------------------------------------------------ pagina
function mostra() {
  const t = terne();
  $("passo-risultato").hidden = !t;
  if (!t) return;
  const nomeComp = NOMI_COMP[stato.comp];
  $("titolo-ente").textContent = t.ente.nome;
  const storia = (t.ente.nomi || []).map(([da, a, n]) => `${n} (${da === a ? da : `${da}–${a}`})`).join("; ");
  $("sottotitolo-ente").textContent = (t.consolidato ? "Conto economico consolidato della regione (codice 999), confrontato con l'Italia. "
    : `Codice ente ${t.ente.cod}, ${nomeRegione(t.ente.reg)}. Confronto con il consolidato regionale e con l'Italia. `)
    + `Spesa considerata: ${nomeComp}.` + (storia ? ` Nomi nel tempo: ${storia}.` : "");
  confronto(t);
  graficoSpesa(t);
  scelte("scelta-rapporto", ["leva", "incidenza", "peso"], "rapporto", t);
  scelte("scelta-unitario", ["per_cittadino", "per_giornata", "per_posto"], "unitario", t);
  scelteTabella(t);
  tabella(t);
  fonti();
}

function nomiColonne(t) {
  return { ente: t.consolidato ? nomeRegione(t.ente.reg) : "Ente", regione: t.regione ? `${nomeRegione(t.ente.reg)} (consolidato)` : null, italia: "Italia" };
}

function confronto(t) {
  const i = anni().indexOf(stato.anno);
  const tab = $("confronto"); tab.innerHTML = "";
  const cols = nomiColonne(t);
  const vals = { ente: indicatori(t.ente, i), regione: indicatori(t.regione, i), italia: indicatori(t.italia, i) };
  const testa = tab.createTHead().insertRow();
  testa.appendChild(h("th", null, `${stato.anno}${provvisorio(stato.anno) ? " (provvisorio)" : ""}`));
  const brevi = { ente: t.consolidato ? "Regione" : "Ente", regione: "Regione", italia: "Italia" };
  const sotto = { ente: t.consolidato ? "consolidato" : `codice ${t.ente.cod}`, regione: t.regione ? `${nomeRegione(t.ente.reg)}, consolidato` : "", italia: "somma delle regioni" };
  for (const k of ["ente", "regione", "italia"]) if (cols[k]) {
    const c = h("th", "num", brevi[k]); c.appendChild(h("small", null, sotto[k])); testa.appendChild(c);
  }
  const rif = t.regione ? "regione" : "italia";
  const th = h("th", "num", "Differenza");
  th.appendChild(h("small", null, rif === "regione" ? "dalla regione" : "dall'Italia"));
  testa.appendChild(th);
  const corpo = tab.createTBody();
  for (const ind of Object.keys(INDICATORI)) {
    const r = corpo.insertRow();
    const nome = h("th", null, ind === "spesa" ? `Spesa (${nomeComp()})` : INDICATORI[ind].nome);
    if (ind !== "spesa") nome.appendChild(h("small", null, { leva: "€ di produzione per 1 € di energia", incidenza: "sul valore della produzione",
      peso: "sui costi della produzione", per_cittadino: "€ per residente", per_giornata: "€ per giornata di degenza ordinaria", per_posto: "€ per posto letto pubblico" }[ind]));
    r.appendChild(nome);
    for (const k of ["ente", "regione", "italia"]) {
      if (!cols[k]) continue;
      const x = vals[k][ind];
      const c = h("td", x === null || x === undefined ? "num nd" : "num", ind === "spesa" ? valore("spesa", x) : valore(ind, x));
      r.appendChild(c);
    }
    const a = vals.ente[ind], b = vals[rif][ind];
    let diff = null;
    if (ind !== "spesa" && a !== null && a !== undefined && b) diff = (a - b) / b;
    const meglio = INDICATORI[ind].meglio;
    const c = h("td", diff === null ? "num nd" : "num", diff === null ? (ind === "spesa" ? "" : "n.d.") : `${diff > 0 ? "+" : ""}${num(diff * 100, 1)} %`);
    if (diff !== null && Math.abs(diff) >= 0.005) {
      // giudizio solo per leva, incidenza e peso; per i valori unitari i perimetri sono diversi (vedi avvertenze)
      if (["leva", "incidenza", "peso"].includes(ind)) {
        const favorevole = meglio === "alto" ? diff > 0 : diff < 0;
        c.classList.add(favorevole ? "meno" : "piu");
        c.appendChild(h("small", null, favorevole ? "più favorevole" : "meno favorevole"));
      } else c.appendChild(h("small", null, diff < 0 ? "più bassa" : "più alta"));
    }
    r.appendChild(c);
  }
  const note = [];
  const pop = t.ente.pop && t.ente.pop[i];
  if (!t.consolidato && !pop) note.push(t.ente.reg === "080"
    ? "Per le aziende ospedaliere e gli IRCCS non c'è una popolazione di riferimento: la spesa per cittadino non si calcola."
    : "La spesa per cittadino delle singole aziende si calcola, per ora, solo in Emilia-Romagna, dove SISEPS pubblica i residenti per Azienda USL.");
  if (!(t.ente.gg && t.ente.gg[i])) note.push("Giornate di degenza e posti letto ci sono solo per l'Emilia-Romagna (ReportER): altrove questi indicatori sono n.d.");
  if (t.ente.fonte_pop === "siseps") note.push("Residenti dell'Emilia-Romagna e delle sue AUSL: SISEPS (ReportER); regioni e Italia: ISTAT.");
  const via = (t.italia.regioni_mancanti || [])[i] || [];
  if (via.length) note.push(`Italia ${stato.anno}: nei dati OpenBDAP manca il conto consolidato di ${via.join(", ")}; somma e popolazione sono quelle delle altre regioni.`);
  if (provvisorio(stato.anno)) note.push(`Il ${stato.anno} è provvisorio: conto economico del IV trimestre, che può cambiare con il consuntivo.`);
  $("nota-confronto").textContent = note.join(" ");
}
const nomeComp = () => NOMI_COMP[stato.comp];

// ------------------------------------------------------------------ grafici
// dest: dove disegnare (il box della pagina o il corpo del riquadro di grafici.js), già vuoto; misure: da grafici.js
function contenitore(dest, misure, etichetta) {
  // larghezza del disegno vicina a quella vera, così su un telefono le scritte restano leggibili; nel riquadro tutta
  const W = misure && misure.riquadro ? misure.larghezza : Math.round(Math.max(340, Math.min(640, (misure && misure.larghezza) || 640)));
  const H = misure && misure.riquadro ? misure.altezza : (W < 480 ? 220 : 240);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": etichetta }, dest);
  return { box: dest, svg, W, H };
}
// disegno nella pagina col pulsante del riquadro (grafici.js); si rifà da sé quando il box cambia larghezza
function registraGrafico(id, titolo, disegna) {
  const box = $(id);
  if (window.EUGENIO_GRAFICI) window.EUGENIO_GRAFICI.registra(box, disegna, { titolo, adatta: true });
  else { box.innerHTML = ""; disegna(box, { larghezza: box.clientWidth, altezza: null, riquadro: false }); }
}
function passoTondo(max) {
  if (!(max > 0)) return 1;
  const grezzo = max / 4, p = 10 ** Math.floor(Math.log10(grezzo));
  return [1, 2, 2.5, 5, 10].map((m) => m * p).find((s) => grezzo <= s) || 10 * p;
}
function assi(g, max, fmt) {
  const { svg, W, H } = g, sx = W < 480 ? 52 : 64, dx = 12, su = 14, gi = 28;
  const passo = passoTondo(max), cima = Math.max(passo, Math.ceil(max / passo) * passo);
  const Y = (v) => su + (H - su - gi) * (1 - v / cima);
  for (let v = 0; v <= cima + passo / 1e6; v += passo) {
    el("line", { x1: sx, x2: W - dx, y1: Y(v), y2: Y(v), class: "asse" }, svg);
    el("text", { x: sx - 6, y: Y(v) + 4, "text-anchor": "end" }, svg).textContent = fmt(v);
  }
  const n = anni().length, larg = (W - sx - dx) / n;
  const X = (i) => sx + larg * (i + 0.5);
  anni().forEach((a, i) => {
    if (provvisorio(a)) el("rect", { x: sx + larg * i, y: su, width: larg, height: H - su - gi, class: "zona-provvisoria" }, svg).parentNode.insertBefore(svg.lastChild, svg.firstChild);
    if ((W >= 480 && n <= 12) || i % 2 === 0 || i === n - 1) el("text", { x: X(i), y: H - 8, "text-anchor": "middle" }, svg).textContent = provvisorio(a) ? `${a}*` : a;
  });
  return { X, Y, larg, sx, dx, su, gi };
}
// valori anno per anno al passaggio del mouse, al tocco o con le frecce (grafici.js, EUGENIO_GRAFICI.osserva):
// testo(i) → righe [colore, testo]; segni(i) → punti da evidenziare [x, y, colore]; elementi(i) → barre da evidenziare
function bersagli(g, a, testo, { segni = () => [], elementi = () => [], guida = true } = {}) {
  if (!window.EUGENIO_GRAFICI) return;
  const punti = anni().map((anno, i) => ({
    x: a.X(i), titolo: `${anno}${provvisorio(anno) ? " (provvisorio)" : ""}`, righe: testo(i), segni: segni(i), elementi: elementi(i),
  }));
  window.EUGENIO_GRAFICI.osserva(g.svg, punti, { area: [a.sx, a.su, g.W - a.dx, g.H - a.gi], guida });
}
function legenda(box, voci) {
  const leg = h("div", "legenda");
  for (const [colore, testo, forma] of voci) {
    const s = h("span"); const i = h("i", forma || null);
    if (forma) i.style.color = colore; else i.style.background = colore;
    s.append(i, testo); leg.appendChild(s);
  }
  box.appendChild(leg);
}

function graficoSpesa(t) {
  const n = anni().length;
  registraGrafico("grafico-spesa", `Spesa per ${nomeComp()} di ${t.ente.nome}, dal ${anni()[0]} al ${anni()[n - 1]}`,
    (dest, misure) => disegnaSpesa(dest, misure, t));
}
function disegnaSpesa(dest, misure, t) {
  const u = t.ente, n = anni().length;
  const parti = stato.mostra ? PARTI.filter(([k]) => COMPONENTI[stato.comp].includes(k)) : null;
  const tot = anni().map((_, i) => spesa(u, i));
  const max = Math.max(0, ...tot.filter((x) => x !== null));
  const g = contenitore(dest, misure, `Spesa per ${nomeComp()} di ${u.nome}, dal ${anni()[0]} al ${anni()[n - 1]}`);
  const a = assi(g, max || 1, euroBreve);
  const larg = Math.min(a.larg * 0.6, misure && misure.riquadro ? 64 : 38);
  const barre = anni().map(() => []);
  anni().forEach((anno, i) => {
    if (tot[i] === null) return;
    const x = a.X(i) - larg / 2;
    const segmenti = parti ? parti.map(([k, , c]) => [u.v[k][i] || 0, `var(${c})`]) : [[tot[i], "var(--ind-ente)"]];
    let base = 0;
    segmenti.forEach(([v, colore], j) => {
      if (!(v > 0)) return;
      const y0 = a.Y(base), y1 = a.Y(base + v);
      const alto = j === segmenti.length - 1 || segmenti.slice(j + 1).every(([w]) => !(w > 0));
      const gap = base > 0 ? 1 : 0;                       // 2px di stacco tra i segmenti
      const r = el("rect", { x, y: y1, width: larg, height: Math.max(0, y0 - y1 - gap), fill: colore, rx: alto ? 3 : 0 }, g.svg);
      if (provvisorio(anno)) r.setAttribute("fill-opacity", ".55");
      barre[i].push(r);
      base += v;
    });
  });
  bersagli(g, a, (i) => {
    if (tot[i] === null) return [];
    const nc = NOMI_COMP[stato.comp];
    const righe = [["var(--ind-ente)", `${nc[0].toUpperCase()}${nc.slice(1)}: ${valore("spesa", tot[i])}`]];
    if (parti) parti.forEach(([k, nome, c]) => righe.push([`var(${c})`, `${nome}: ${valore("spesa", u.v[k][i])}`]));
    const comb = u.v.BA0340[i];
    if (comb !== null && comb !== undefined) righe.push(["var(--linea)", `Combustibili e carburanti, esclusi: ${valore("spesa", comb)}`]);
    return righe;
  }, { elementi: (i) => barre[i], guida: false });
  if (parti) legenda(g.box, parti.map(([, nome, c]) => [`var(${c})`, nome]));
  g.box.appendChild(h("p", "aiuto", `In euro all'anno. ${anni().filter(provvisorio).map((x) => `${x}*`).join(", ")} provvisorio, su fondo grigio. `
    + "I combustibili e carburanti (voce BA0340, comprende il carburante degli automezzi) non sono nel totale: si vedono passando sulle colonne."));
}

function scelte(id, chiavi, campo, t) {
  const box = $(id); box.innerHTML = "";
  const disponibili = chiavi.filter((k) => ["ente", "regione", "italia"].some((s) => t[s] && anni().some((_, i) => indicatori(t[s], i)[k] !== null && indicatori(t[s], i)[k] !== undefined)));
  if (!disponibili.includes(stato[campo])) stato[campo] = disponibili[0] || chiavi[0];
  for (const k of chiavi) {
    if (!disponibili.includes(k)) continue;
    const b = h("button", "filtro", INDICATORI[k].nome); b.type = "button";
    b.setAttribute("aria-pressed", String(stato[campo] === k));
    b.addEventListener("click", () => { stato[campo] = k; mostra(); });
    box.appendChild(b);
  }
  const grafico = campo === "rapporto" ? "grafico-rapporto" : "grafico-unitario";
  $(campo === "rapporto" ? "lettura-rapporto" : "lettura-unitario").textContent = INDICATORI[stato[campo]].lettura
    + (stato[campo] === "per_cittadino" ? " " + notaPopolazione(t) : "");
  graficoLinee(grafico, stato[campo], t);
}

function notaPopolazione(t) {
  const s = stato.indice.serie_popolazione || {};
  const ric = Object.keys(s).filter((a) => s[a] === "ricostruzione"), stime = Object.keys(s).filter((a) => s[a] === "stima");
  let testo = "Per regioni e Italia la popolazione è ISTAT";
  if (ric.length) testo += `: fino al ${ric[ric.length - 1]} dalla ricostruzione intercensuaria, dopo dal censimento permanente, con un piccolo salto tra le due serie`;
  if (stime.length) testo += `; per il ${stime.join(", ")} è la stima al 1° gennaio successivo`;
  testo += ".";
  if (t.ente.fonte_pop === "siseps") testo += " Per l'Emilia-Romagna e le sue AUSL si usano i residenti SISEPS, poco diversi da quelli ISTAT.";
  return testo;
}

function graficoLinee(id, ind, t) {
  registraGrafico(id, `${INDICATORI[ind].nome} dal ${anni()[0]} al ${anni()[anni().length - 1]}`,
    (dest, misure) => disegnaLinee(dest, misure, ind, t));
}
function disegnaLinee(dest, misure, ind, t) {
  const cols = nomiColonne(t);
  const serie = SERIE.filter(([k]) => t[k]).map(([k, c, tratto]) => ({ k, nome: k === "ente" && !t.consolidato ? t.ente.nome : cols[k], colore: `var(${c})`, tratto,
    v: anni().map((_, i) => { const x = indicatori(t[k], i)[ind]; return x === undefined ? null : x; }) }))
    .filter((s) => s.v.some((x) => x !== null));
  const d = INDICATORI[ind], scala = d.perc ? 100 : 1;
  const tutti = serie.flatMap((s) => s.v.filter((x) => x !== null).map((x) => x * scala));
  const g = contenitore(dest, misure, `${d.nome} dal ${anni()[0]} al ${anni()[anni().length - 1]}: ${serie.map((s) => s.nome).join(", ")}`);
  if (!tutti.length) { g.box.appendChild(h("p", "aiuto", "Nessun dato per questo indicatore.")); return; }
  const fmt = (v) => d.perc ? `${num(v, v < 10 && v % 1 ? 1 : 0)} %` : ind === "leva" ? `${num(v, 0)}x` : euroBreve(v);
  const a = assi(g, Math.max(...tutti) * 1.05, fmt);
  for (const s of serie) {
    let tratto = "";
    s.v.forEach((x, i) => {
      if (x === null) { tratto += " "; return; }
      const prima = i > 0 && s.v[i - 1] !== null;
      tratto += `${prima ? "L" : "M"}${a.X(i).toFixed(1)},${a.Y(x * scala).toFixed(1)}`;
    });
    el("path", { d: tratto.trim().replace(/\s+/g, " "), fill: "none", stroke: s.colore, "stroke-width": 2, "stroke-linejoin": "round",
      ...(s.tratto ? { "stroke-dasharray": s.tratto } : {}) }, g.svg);
    s.v.forEach((x, i) => {
      if (x === null) return;
      const c = el("circle", { cx: a.X(i), cy: a.Y(x * scala), r: 4, fill: s.colore, stroke: "var(--foglio)", "stroke-width": 2 }, g.svg);
      if (provvisorio(anni()[i])) { c.style.fill = "var(--foglio)"; c.style.stroke = s.colore; }
    });
  }
  bersagli(g, a, (i) => serie.filter((s) => s.v[i] !== null).map((s) => [s.colore, `${s.nome}: ${valore(ind, s.v[i])}`]),
    { segni: (i) => serie.filter((s) => s.v[i] !== null).map((s) => [a.X(i), a.Y(s.v[i] * scala), s.colore]) });
  legenda(g.box, serie.map((s) => [s.colore, s.nome, s.tratto ? (s.tratto === "2 3" ? "linea punti" : "linea tratto") : "linea"]));
  const mancano = SERIE.filter(([k]) => t[k] && !serie.some((s) => s.k === k)).map(([k]) => cols[k]);
  if (mancano.length) g.box.appendChild(h("p", "aiuto", `Non disponibile per: ${mancano.join(", ")}.`));
}

// ------------------------------------------------------------------ tabella
function scelteTabella(t) {
  const box = $("scelta-tabella"); box.innerHTML = "";
  const cols = nomiColonne(t);
  if (!t[stato.tabella]) stato.tabella = "ente";
  for (const k of ["ente", "regione", "italia"]) {
    if (!t[k]) continue;
    const b = h("button", "filtro", cols[k] === "Ente" ? t.ente.nome : cols[k]); b.type = "button";
    b.setAttribute("aria-pressed", String(stato.tabella === k));
    b.addEventListener("click", () => { stato.tabella = k; scelteTabella(t); tabella(t); });
    box.appendChild(b);
  }
}
function colonne(u) {
  const c = [["spesa", `Spesa (${nomeComp()})`, "€", (i) => spesa(u, i), 0]];
  if (stato.mostra) {
    for (const [k, nome] of PARTI) if (COMPONENTI[stato.comp].includes(k)) c.push([k, nome, "€", (i) => u.v[k][i], 0]);
    c.push(["BA0340", "Combustibili e carburanti", "€, esclusi", (i) => u.v.BA0340[i], 0]);
  }
  c.push(["AZ9999", "Valore della produzione", "€", (i) => u.v.AZ9999[i], 0], ["BZ9999", "Costi della produzione", "€", (i) => u.v.BZ9999[i], 0]);
  const ind = (k) => (i) => indicatori(u, i)[k];
  c.push(["leva", "Leva", "volte", ind("leva"), 1], ["incidenza", "Incidenza", "%", (i) => pct(ind("incidenza")(i)), 2],
    ["peso", "Peso", "%", (i) => pct(ind("peso")(i)), 2]);
  if (u.gg) c.push(["gg", "Giornate di degenza", "ordinaria", (i) => u.gg[i], 0], ["per_giornata", "Per giornata", "€", ind("per_giornata"), 2]);
  if (u.pl) c.push(["pl", "Posti letto", "al 31/12", (i) => u.pl[i], 0], ["per_posto", "Per posto letto", "€", ind("per_posto"), 0]);
  if (u.pop) c.push(["pop", "Residenti", u.fonte_pop === "siseps" ? "SISEPS" : "ISTAT", (i) => u.pop[i], 0], ["per_cittadino", "Per cittadino", "€", ind("per_cittadino"), 2]);
  return c;
}
const pct = (x) => (x === null || x === undefined ? null : x * 100);
function tabella(t) {
  const u = t[stato.tabella] || t.ente;
  const nota = $("nota-tabella");
  const vie = anni().map((a, i) => [a, (u.regioni_mancanti || [])[i] || []]).filter(([, v]) => v.length);
  nota.textContent = (vie.length ? vie.map(([a, v]) => `${a}: manca il consolidato di ${v.join(", ")}.`).join(" ") + " " : "")
    + (stato.indice.provvisori.length ? `* ${stato.indice.provvisori.join(", ")} provvisorio.` : "");
  const tab = $("tabella"); tab.innerHTML = "";
  const c = colonne(u);
  const testa = tab.createTHead().insertRow();
  testa.appendChild(h("th", null, "Anno"));
  for (const [, nome, unita] of c) { const th = h("th", "num", nome); th.appendChild(h("small", null, unita)); testa.appendChild(th); }
  const corpo = tab.createTBody();
  anni().forEach((a, i) => {
    const r = corpo.insertRow();
    if (provvisorio(a)) r.className = "provvisorio";
    r.appendChild(h("th", null, provvisorio(a) ? `${a}*` : String(a)));
    for (const [, , , f, dec] of c) { const x = f(i); r.appendChild(h("td", x === null || x === undefined ? "num nd" : "num", num(x, dec))); }
  });
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
const cella = (x, dec = 6) => (x === null || x === undefined || !Number.isFinite(x)) ? "" : String(Math.round(x * 10 ** dec) / 10 ** dec).replace(".", ",");
const testo = (s) => /[;"\n]/.test(s) ? `"${String(s).replace(/"/g, '""')}"` : String(s);
const INTESTAZIONE = ["unita", "regione_ce", "codice_ente", "nome", "anno", "provvisorio", "BA1610_riscaldamento", "BA1660_elettricita",
  "BA1670_altre_utenze", "BA0340_combustibili_esclusi", "AZ9999_valore_produzione", "BZ9999_costi_produzione", "spesa_considerata",
  "leva", "incidenza_perc", "peso_perc", "giornate_degenza_ordinaria", "euro_per_giornata", "posti_letto", "euro_per_posto_letto",
  "residenti", "fonte_residenti", "euro_per_cittadino"];
function righeCsv(tipo, u) {
  return anni().map((a, i) => {
    const d = indicatori(u, i), v = (k) => (u[k] ? u[k][i] : null);
    return [tipo, u.reg, u.cod, testo(u.nome), a, provvisorio(a) ? "sì" : "no", ...["BA1610", "BA1660", "BA1670", "BA0340", "AZ9999", "BZ9999"].map((k) => cella(u.v[k][i], 2)),
      cella(d.spesa, 2), cella(d.leva, 4), cella(pct(d.incidenza), 4), cella(pct(d.peso), 4), cella(v("gg"), 0), cella(d.per_giornata, 4),
      cella(v("pl"), 0), cella(d.per_posto, 4), cella(v("pop"), 0), u.pop ? u.fonte_pop || "" : "", cella(d.per_cittadino, 4)].join(";");
  });
}
function piedeCsv() {
  const r = ["", `Spesa considerata;${NOMI_COMP[stato.comp]} (${COMPONENTI[stato.comp].join(" + ")})`,
    `Anni provvisori;${stato.indice.provvisori.join(" ")} (conto economico del IV trimestre)`, `Aggiornato;${stato.indice.aggiornato}`];
  for (const f of stato.indice.fonti) r.push(`Fonte;${testo(f.testo)};${f.url};licenza ${f.licenza};${f.licenza_url}`);
  r.push(`Elaborazione;${testo(stato.indice.elaborazione)}`, `Nota;${testo("Il consolidato regionale esclude gli scambi tra aziende della stessa regione; Italia = somma dei consolidati di regioni e province autonome.")}`,
    `Licenza;${testo(LICENZA)}`, `Come citare;${testo(citazione())}`);
  return r.concat("");
}
$("scarica-ente").addEventListener("click", () => {
  const t = terne(); if (!t) return;
  const righe = [INTESTAZIONE.join(";"), ...righeCsv(t.consolidato ? "regione" : "ente", t.ente)];
  if (t.regione) righe.push(...righeCsv("regione", t.regione));
  righe.push(...righeCsv("italia", t.italia), ...piedeCsv());
  scarica(`indicatori_energia_${t.ente.reg}_${t.ente.cod}.csv`, "﻿" + righe.join("\r\n"), "text/csv;charset=utf-8");
});
$("scarica-regione").addEventListener("click", () => {
  if (!stato.dati) return;
  const righe = [INTESTAZIONE.join(";")];
  for (const amb of stato.dati.ambiti) {
    if (stato.indice.consolidati[amb.ce]) righe.push(...righeCsv("regione", stato.indice.consolidati[amb.ce]));
    for (const e of amb.enti) righe.push(...righeCsv("ente", e));
  }
  righe.push(...righeCsv("italia", stato.indice.italia), ...piedeCsv());
  scarica(`indicatori_energia_regione_${stato.regione}.csv`, "﻿" + righe.join("\r\n"), "text/csv;charset=utf-8");
});

// report (PDF, Excel, ODS): il server riceve i valori già calcolati e li impagina (tipo "indicatori")
function corpoReport() {
  const t = terne(); if (!t) return null;
  const cols = nomiColonne(t);
  const unitaReport = (k) => {
    const u = t[k];
    return u ? { nome: k === "ente" ? u.nome : cols[k], codice: u.cod, regione_ce: u.reg, fonte_residenti: u.pop ? u.fonte_pop || null : null,
      anni: anni().map((a, i) => ({ anno: a, provvisorio: provvisorio(a), ...indicatori(u, i),
        BA1610: u.v.BA1610[i], BA1660: u.v.BA1660[i], BA1670: u.v.BA1670[i], BA0340: u.v.BA0340[i], AZ9999: u.v.AZ9999[i], BZ9999: u.v.BZ9999[i],
        giornate: u.gg ? u.gg[i] : null, posti_letto: u.pl ? u.pl[i] : null, residenti: u.pop ? u.pop[i] : null })) } : null;
  };
  return { ente: unitaReport("ente"), regione: unitaReport("regione"), italia: unitaReport("italia"), consolidato: t.consolidato,
    componente: NOMI_COMP[stato.comp], voci: COMPONENTI[stato.comp], anno_confronto: stato.anno, provvisori: stato.indice.provvisori,
    aggiornato: stato.indice.aggiornato, avvertenze: [...document.querySelectorAll(".ind-avvertenze li")].map((li) => li.textContent.trim()),
    fonti: stato.indice.fonti.map((f) => ({ testo: `${f.testo} (${f.licenza})`, url: f.url })), elaborazione: stato.indice.elaborazione };
}
if (window.EUGENIO_REPORT) window.EUGENIO_REPORT.pulsanti($("report"), {
  tipo: "indicatori",
  corpo: corpoReport,
  nome: (ext) => { const t = terne(); return `indicatori_energia_${t ? `${t.ente.reg}_${t.ente.cod}` : "ssn"}.${ext}`; },
  messaggio, area: "messaggio",
});

function fonti() {
  const f = $("fonti"); f.innerHTML = "";
  f.append("Fonti: ");
  stato.indice.fonti.forEach((x, i) => {
    const a = h("a", null, x.testo); a.href = x.url; a.rel = "noopener";
    const l = h("a", null, x.licenza); l.href = x.licenza_url; l.rel = "noopener";
    f.append(a, " (", l, ")", i < stato.indice.fonti.length - 1 ? "; " : ". ");
  });
  f.append(`${stato.indice.elaborazione} Dati aggiornati al ${new Date(stato.indice.aggiornato).toLocaleDateString("it-IT")}.`);
}

// i grafici si adattano da soli alla larghezza del loro box (finestra o divisore delle colonne): grafici.js

carica().catch((e) => messaggio(`Indicatori non disponibili: ${e.message}`, true));
