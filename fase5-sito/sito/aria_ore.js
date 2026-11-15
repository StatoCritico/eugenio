"use strict";
// Trattamento aria › Ore di funzionamento (14/11/2026). Invece dei soli punti di progetto estremi, la «nuvola» delle ore
// reali del comune (T a bulbo secco e UR della serie oraria) sul diagramma psicrometrico o di Mollier, in 4 gruppi di ore
// (gruppi_ore.js) con i loro colori; per ogni gruppo statistiche, condizioni di progetto al livello scelto (modificabili a
// mano), tabelle delle classi («metodo dei bin»: ore per classe di T da 2 K e di x da 1 g/kg) e ore dentro/fuori da una
// zona di comfort con le ore che chiedono riscaldamento, raffreddamento, umidificazione, deumidificazione.
//
// Parte pura (anche in node, per i test di parità con fase14-trattamento-aria/aria/ore.py): statistiche, classiT, classiX,
// matriceTX, zona. Tutte lavorano sugli indici delle ore di un gruppo (Uint32Array di gruppi_ore.filtra) e sui vettori x,
// h, twb di psicro.vettori (Float32Array, in cache per serie).
// Parte nella pagina: passo 1 da scelta_aria.js, passo 2 gruppi_ore.js, diagramma da diagramma_aria.js.
(function (radice) {
  const P = radice.EUGENIO_PSICRO || (typeof require === "function" ? require("./psicro.js") : null);
  const ANNO = 8766;                                  // ore di un anno medio (bisestili compresi)
  const PASSO_T = 2, PASSO_X = 1;                     // K e g/kg

  // quantile con interpolazione lineare sui valori ordinati (come numpy.quantile e psicro.quantile)
  const quantile = (o, q) => P.quantile(o, q);

  // statistiche di un gruppo. i0 = primo indice della finestra «ultimi N anni» (gruppi_ore.inizioAnni), n = ore della serie
  function statistiche(t, ur, p, indici, i0 = 0, n = t.length) {
    const V = P.vettori(t, ur, p), m = indici.length;
    const xs = new Float32Array(m), hs = new Float32Array(m);
    let k = 0, tMin = Infinity, tMax = -Infinity, sT = 0, sU = 0, wMax = -Infinity;
    for (let j = 0; j < m; j++) {
      const i = indici[j], x = V.x[i];
      if (!(x === x)) continue;
      const tt = t[i];
      if (tt < tMin) tMin = tt;
      if (tt > tMax) tMax = tt;
      sT += tt; sU += ur[i];
      xs[k] = x; hs[k] = V.h[i]; k++;
      const w = V.twb[i];
      if (w > wMax) wMax = w;
    }
    const periodo = Math.max(0, n - i0), anni = periodo / ANNO;
    const X = xs.subarray(0, k).sort(), H = hs.subarray(0, k).sort();
    const q = (o, v, f) => (k ? quantile(o, v) * f : NaN);
    return {
      ore: k, anni, oreAnno: anni > 0 ? k / anni : NaN, quota: periodo ? k / periodo * 100 : NaN,
      tMin: k ? tMin : NaN, tMedia: k ? sT / k : NaN, tMax: k ? tMax : NaN, urMedia: k ? sU / k : NaN,
      x01: q(X, 0.01, 1000), x50: q(X, 0.5, 1000), x99: q(X, 0.99, 1000),
      h01: q(H, 0.01, 1), h50: q(H, 0.5, 1), h99: q(H, 0.99, 1),
      twbMax: k ? wMax : NaN,
    };
  }

  // classi di temperatura [da, a) di «passo» K: ore e valori medi coincidenti (UR, x g/kg, h, bulbo umido)
  function classiT(t, ur, p, indici, passo = PASSO_T) {
    const V = P.vettori(t, ur, p);
    let kMin = Infinity, kMax = -Infinity;
    for (let j = 0; j < indici.length; j++) {
      const i = indici[j];
      if (!(V.x[i] === V.x[i])) continue;
      const c = Math.floor(t[i] / passo);
      if (c < kMin) kMin = c;
      if (c > kMax) kMax = c;
    }
    if (kMin > kMax) return [];
    const L = kMax - kMin + 1, ore = new Float64Array(L), sU = new Float64Array(L), sX = new Float64Array(L), sH = new Float64Array(L), sW = new Float64Array(L);
    for (let j = 0; j < indici.length; j++) {
      const i = indici[j], x = V.x[i];
      if (!(x === x)) continue;
      const c = Math.floor(t[i] / passo) - kMin;
      ore[c]++; sU[c] += ur[i]; sX[c] += x; sH[c] += V.h[i]; sW[c] += V.twb[i];
    }
    const out = [];
    for (let c = 0; c < L; c++) {
      const o = ore[c];
      out.push({ da: (c + kMin) * passo, a: (c + kMin + 1) * passo, ore: o, ur: o ? sU[c] / o : NaN, x: o ? sX[c] / o * 1000 : NaN,
        h: o ? sH[c] / o : NaN, twb: o ? sW[c] / o : NaN });
    }
    return out;
  }

  // classi di umidità specifica [da, a) di «passo» g/kg: ore e T, UR, h medie coincidenti
  function classiX(t, ur, p, indici, passo = PASSO_X) {
    const V = P.vettori(t, ur, p);
    let kMin = Infinity, kMax = -Infinity;
    for (let j = 0; j < indici.length; j++) {
      const x = V.x[indici[j]];
      if (!(x === x)) continue;
      const c = Math.floor(x * 1000 / passo);
      if (c < kMin) kMin = c;
      if (c > kMax) kMax = c;
    }
    if (kMin > kMax) return [];
    const L = kMax - kMin + 1, ore = new Float64Array(L), sT = new Float64Array(L), sU = new Float64Array(L), sH = new Float64Array(L);
    for (let j = 0; j < indici.length; j++) {
      const i = indici[j], x = V.x[i];
      if (!(x === x)) continue;
      const c = Math.floor(x * 1000 / passo) - kMin;
      ore[c]++; sT[c] += t[i]; sU[c] += ur[i]; sH[c] += V.h[i];
    }
    const out = [];
    for (let c = 0; c < L; c++) {
      const o = ore[c];
      out.push({ da: (c + kMin) * passo, a: (c + kMin + 1) * passo, ore: o, t: o ? sT[c] / o : NaN, ur: o ? sU[c] / o : NaN, h: o ? sH[c] / o : NaN });
    }
    return out;
  }

  // tabella a doppia entrata: ore per classe di T (righe) e di x (colonne)
  function matriceTX(t, ur, p, indici, passoT = PASSO_T, passoX = PASSO_X) {
    const V = P.vettori(t, ur, p);
    let a = Infinity, b = -Infinity, c = Infinity, d = -Infinity;
    for (let j = 0; j < indici.length; j++) {
      const i = indici[j], x = V.x[i];
      if (!(x === x)) continue;
      const kt = Math.floor(t[i] / passoT), kx = Math.floor(x * 1000 / passoX);
      if (kt < a) a = kt; if (kt > b) b = kt; if (kx < c) c = kx; if (kx > d) d = kx;
    }
    if (a > b) return { t: [], x: [], ore: [] };
    const nt = b - a + 1, nx = d - c + 1, ore = Array.from({ length: nt }, () => new Array(nx).fill(0));
    for (let j = 0; j < indici.length; j++) {
      const i = indici[j], x = V.x[i];
      if (!(x === x)) continue;
      ore[Math.floor(t[i] / passoT) - a][Math.floor(x * 1000 / passoX) - c]++;
    }
    return { t: Array.from({ length: nt }, (_, k) => (a + k) * passoT), x: Array.from({ length: nx }, (_, k) => (c + k) * passoX), ore };
  }

  // zona di comfort (rettangolo T–UR, limiti compresi). Regole semplici, ora per ora:
  //  - T sotto tMin → riscaldamento, sopra tMax → raffreddamento (sensibile, a x costante, fino al limite più vicino);
  //  - l'UR alla temperatura così raggiunta (stessa pressione del vapore: UR·psat(T)/psat(Tc)) sotto urMin →
  //    umidificazione, sopra urMax → deumidificazione;
  //  - «nella zona» = nessuno dei quattro trattamenti. Un'ora può chiedere due trattamenti (es. riscaldare e umidificare).
  function zona(t, ur, p, indici, z) {
    const V = P.vettori(t, ur, p);
    const tMin = +z.tMin, tMax = +z.tMax, uMin = +z.urMin, uMax = +z.urMax;
    const lMin = P.lnPsat(tMin), lMax = P.lnPsat(tMax);
    let ore = 0, dentro = 0, risc = 0, raff = 0, umid = 0, deum = 0;
    for (let j = 0; j < indici.length; j++) {
      const i = indici[j];
      if (!(V.x[i] === V.x[i])) continue;
      ore++;
      const T = t[i], U = Math.min(ur[i], 100);
      let Uc = U, fatto = false;
      if (T < tMin) { risc++; fatto = true; Uc = U * Math.exp(P.lnPsat(T) - lMin); }
      else if (T > tMax) { raff++; fatto = true; Uc = U * Math.exp(P.lnPsat(T) - lMax); }
      if (Uc < uMin) { umid++; fatto = true; } else if (Uc > uMax) { deum++; fatto = true; }
      if (!fatto) dentro++;
    }
    return { ore, dentro, fuori: ore - dentro, riscaldare: risc, raffreddare: raff, umidificare: umid, deumidificare: deum };
  }

  const API = { ANNO, PASSO_T, PASSO_X, statistiche, classiT, classiX, matriceTX, zona };
  radice.EUGENIO_ARIA_ORE = API;
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  if (typeof document === "undefined") return;

  // ==================================================================== la pagina
  const GO = window.EUGENIO_GRUPPI_ORE, SA = window.EUGENIO_SCELTA_ARIA;
  const $ = (id) => document.getElementById(id);
  // migliaia sempre col punto (anche 2.485, come 14.633)
  const fmt = (n, d = 0) => (Number.isFinite(n) ? Number(n).toLocaleString("it-IT", { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: "always" }) : "—");
  const meno = (s) => String(s).replace(/^-/, "−");
  const fmtS = (n, d = 0) => meno(fmt(n, d));
  function h(tag, cls, testo) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (testo !== undefined && testo !== null) e.textContent = testo;
    return e;
  }
  const titolo = "Ore di funzionamento";
  // nomi dei colori di stampa delle serie 1–4 (tema chiaro), per la fascia delle immagini
  const NOMI_COLORI = ["rosso mattone", "blu", "ocra", "magenta", "verde", "grigio"];
  const INIZIALI = [
    { preset: "estate", anni: 5, nome: "Estate, ultimi 5 anni" },
    { preset: "inverno", anni: 5, nome: "Inverno, ultimi 5 anni" },
    { preset: "estate", anni: 20, nome: "Estate, ultimi 20 anni" },
    { preset: "inverno", anni: 20, nome: "Inverno, ultimi 20 anni" },
  ];
  const RAGGI = [["piccoli", 0.7], ["medi", 1], ["grandi", 1.6]];
  const TRASP = [0.35, 0.6, 1, 1.7, 3];                // fattori sulla trasparenza automatica (indice 2 = automatica)
  const MAX_RIGHE_CSV = 100000;

  const st = {
    raggio: 1, trasp: 2, modo: "punti",
    zona: { tMin: 20, tMax: 26, urMin: 30, urMax: 60 }, mostraZona: true, mostraProgetto: true,
    modifiche: new Map(),          // gruppo → { firma, valori modificati a mano }
    manuale: false,                // l'utente ha scelto a mano gli anni del passo 1: non li cambio più da solo
    prima: new Map(),              // gruppo → { anni, mostra } dell'evento precedente
    nomi: new Map(),               // gruppo → nome scritto dalla pagina (null = scritto dall'utente)
    ris: null, attesa: 0, vista: "confronto", nuvole: [],
  };
  const cache = { stat: new Map(), prog: new Map(), serie: null };

  // ---------------------------------------------------------------- moduli comuni
  const D = window.EUGENIO_DIAGRAMMA_ARIA.crea($("diagramma-aria"), {
    titolo,
    nomeFile: () => "eugenio-aria-ore",
    avviso: () => (S && S.serie() && S.serie().sintetica ? "Dati sintetici di prova, non reali." : ""),
    fonti: () => righeFonti(),
  });
  const S = SA.crea({ mappa: "#mappa", passo: "#scelta-aria" });
  const G = GO.crea($("aria-gruppi"), { iniziali: INIZIALI });
  // la serie del passo 1 deve coprire gli anni dei gruppi visibili: la porto subito al massimo che serve (prima che parta il
  // primo caricamento, così non si scarica due volte)
  {
    const serve = anniNecessari(G.visibili());
    if (serve && rango(serve) > rango(S.anni())) S.anni(serve);
  }
  const L = SA.livelloProgetto("#aria-livello", { titolo: "Livello delle condizioni di progetto" });

  // legenda propria (dentro quella del modulo, che la pagina riempie: i gruppi hanno già «Mostra») e aspetto della nuvola
  const boxLegenda = D.elemento.querySelector(".aria-legenda");
  const aspetto = h("div", "aria-ore-aspetto");
  boxLegenda.after(aspetto);
  costruisciAspetto();

  // ---------------------------------------------------------------- anni della serie e dei gruppi
  function rango(a) { return a === 0 ? Infinity : a; }
  // anni che servono: il massimo dei gruppi visibili; «tutta la serie caricata» (0) non chiede niente
  function anniNecessari(gr) { return gr.reduce((m, g) => (g.anni && g.anni > m ? g.anni : m), 0); }
  const testoAnni = (a) => (a === 0 ? "tutta la serie" : a === 1 ? "ultimo anno" : `ultimi ${a} anni`);
  $("aria-anni").addEventListener("change", () => { st.manuale = true; st.notaAlzata = ""; });

  function controllaAnni(gr) {
    let cambiato = false;
    gr.forEach((g) => { const p = st.prima.get(g.id); if (!p || p.anni !== g.anni || p.mostra !== g.mostra) cambiato = true; st.prima.set(g.id, { anni: g.anni, mostra: g.mostra }); });
    const vis = gr.filter((g) => g.mostra), serve = anniNecessari(vis), caricati = S.anni();
    const box = $("aria-ore-nota-anni");
    box.innerHTML = "";
    if (!serve || rango(serve) <= rango(caricati)) { if (st.notaAlzata) box.textContent = st.notaAlzata; return; }
    const chi = vis.filter((g) => g.anni && rango(g.anni) > rango(caricati)).map((g) => `«${g.nome}»`).join(", ");
    if (cambiato || !st.manuale) {
      st.manuale = false;
      st.notaAlzata = `Ho portato la serie del passo 1 a «${testoAnni(serve)}», perché ${chi} ${chi.includes(",") ? "li chiedono" : "li chiede"}.`;
      box.textContent = st.notaAlzata;
      S.anni(serve);
      return;
    }
    box.append(`La serie del passo 1 è «${testoAnni(caricati)}»: ${chi} ${chi.includes(",") ? "chiedono" : "chiede"} ${testoAnni(serve)} e per ora ${chi.includes(",") ? "usano" : "usa"} la serie caricata. `);
    const b = h("button", "bottone secondario piccolo", `Carica ${testoAnni(serve)}`);
    b.type = "button";
    b.addEventListener("click", () => { st.manuale = false; st.notaAlzata = ""; box.textContent = ""; S.anni(serve); });
    box.appendChild(b);
  }

  // nomi automatici: un nome scritto dalla pagina (es. «Estate, ultimi 5 anni») segue i cambi del gruppo; uno scritto
  // dall'utente resta com'è
  function nomeAuto(d) {
    const da = GO.leggiData(d.da), a = GO.leggiData(d.a);
    let per = { "601|930": "Estate", "1101|331": "Inverno", "101|1231": "Tutto l'anno" }[`${da}|${a}`];
    if (!per) {
      const z = Object.entries(GO.ZONE).find(([, v]) => GO.leggiData(v[0]) === da && GO.leggiData(v[1]) === a);
      per = z ? `Inverno (zona ${z[0]})` : `${d.da}–${d.a}`;
    }
    const tutte = (+d.oraDa === +d.oraA) || (+d.oraDa === 0 && +d.oraA === 24), fer = d.giorni === "feriali";
    const ore = tutte ? (fer ? "feriali" : "") : (+d.oraDa === 8 && +d.oraA === 18 && fer) ? "ore d'ufficio" : `ore ${d.oraDa}–${d.oraA}${fer ? " feriali" : ""}`;
    return [per, testoAnni(d.anni).replace("tutta la serie", "tutta la serie caricata"), ore].filter(Boolean).join(", ");
  }
  function nomiAutomatici(gr) {
    let rinomina = false;
    const campi = G.elemento.querySelectorAll(".aria-gruppo");
    gr.forEach((g, i) => {
      const nuovo = nomeAuto(g);
      const auto = st.nomi.has(g.id) ? g.nome === st.nomi.get(g.id) : g.nome === nuovo || INIZIALI.some((x) => x.nome === g.nome);
      if (auto && g.nome !== nuovo && campi[i]) {
        const inp = campi[i].querySelector(".aria-gruppo-nome");
        inp.value = nuovo; inp.dispatchEvent(new Event("input"));
        rinomina = true;
      }
      st.nomi.set(g.id, auto ? nuovo : null);
    });
    return rinomina;
  }

  // ---------------------------------------------------------------- nuvole, zona, punti di progetto
  const colore = (g) => g.colore;
  function alfa(n) {
    const dpr = window.devicePixelRatio || 1, r = st.raggio * dpr;
    let nucleo = 1;
    if (r > 0.75) { nucleo = 0; const R = Math.ceil(r); for (let y = -R; y <= R; y++) for (let x = -R; x <= R; x++) if (x * x + y * y <= r * r + 0.25) nucleo++; }
    const auto = Math.max(0.03, Math.min(0.9, 25 / Math.sqrt(Math.max(1, n)))) / Math.sqrt(nucleo);
    return Math.max(0.004, Math.min(1, auto * TRASP[st.trasp]));
  }
  function disegnaNuvole() {
    st.nuvole.forEach((n) => D.togli(n));
    st.nuvole = [];
    const s = S.serie();
    if (s) {
      const V = P.vettori(s.t, s.ur, s.p);
      // prima i gruppi con più anni (le nuvole lunghe stanno sotto, quelle corte sopra): a parità, nell'ordine dei gruppi
      const vis = G.gruppi().filter((g) => g.mostra && g.indici.length);
      vis.sort((a, b) => rango(b.anni) - rango(a.anni) || a.indice - b.indice);
      vis.forEach((g) => {
        const nome = `nuvola-${g.id}`;
        D.nuvola(nome, colore(g), { t: s.t, x: V.x, indici: g.indici },
          { etichetta: g.nome, legenda: false, raggio: st.raggio, alpha: alfa(g.indici.length), modo: st.modo === "densita" ? "densita" : "punti", cella: 4 });
        st.nuvole.push(nome);
      });
    }
    legenda();
  }
  function disegnaZona() {
    D.togli("zona-comfort");
    const z = st.zona;
    if (st.mostraZona && S.serie() && zonaValida(z))
      D.zona("zona-comfort", { tMin: z.tMin, tMax: z.tMax, urMin: z.urMin, urMax: z.urMax }, { colore: "var(--serie-5)", alpha: 0.12, tratteggio: [6, 3], etichetta: "Zona di comfort", legenda: false });
    legenda();
  }
  const zonaValida = (z) => [z.tMin, z.tMax, z.urMin, z.urMax].every(Number.isFinite) && z.tMin < z.tMax && z.urMin < z.urMax && z.urMin >= 0 && z.urMax <= 100;
  function disegnaProgetto() {
    D.strati().filter((x) => x.nome.startsWith("progetto-")).forEach((x) => D.togli(x.nome));
    if (st.mostraProgetto && st.ris && S.serie()) {
      st.ris.gruppi.forEach((r) => {
        if (!r.mostra || !r.progetto || !r.progetto.inverno) return;
        const v = valoriProgetto(r);
        const n = r.indice + 1;
        if (Number.isFinite(v.invT) && Number.isFinite(v.invUR))
          D.punto(`progetto-i-${r.id}`, { t: v.invT, ur: Math.min(100, v.invUR) }, { colore: r.colore, simbolo: "quadrato", etichetta: `${n} inv.`, posizione: ["l", "t", "b", "r"][r.indice % 4], legenda: false });
        const se = statoEstate(v);
        if (se) D.punto(`progetto-e-${r.id}`, { t: se.t, x: se.x }, { colore: r.colore, simbolo: "rombo", etichetta: `${n} est.`, posizione: ["t", "r", "b", "l"][r.indice % 4], legenda: false });
      });
    }
    legenda();
  }
  function statoEstate(v) {
    const s = S.serie();
    if (!s || !Number.isFinite(v.estT) || !Number.isFinite(v.estTwb)) return null;
    try { return P.stato(v.estT, { twb: Math.min(v.estT, v.estTwb) }, s.p); } catch (e) { return null; }
  }

  // legenda: un rigo per gruppo (casella = «Mostra» del gruppo), zona, punti di progetto
  function legenda() {
    boxLegenda.innerHTML = "";
    const s = S.serie();
    G.gruppi().forEach((g, i) => {
      const l = h("label", "casella aria-voce-legenda");
      const c = document.createElement("input"); c.type = "checkbox"; c.checked = g.mostra;
      c.setAttribute("aria-label", `Mostra il gruppo ${i + 1}: ${g.nome}`);
      c.addEventListener("change", () => {
        const mc = G.elemento.querySelectorAll(".aria-gruppo")[i]?.querySelector(".aria-mostra input");
        if (mc) { mc.checked = c.checked; mc.dispatchEvent(new Event("change")); }
      });
      const camp = h("span", "aria-segno aria-segno-nuvola"); camp.setAttribute("aria-hidden", "true");
      camp.style.setProperty("--colore-strato", g.colore);
      l.append(c, camp, ` ${g.nome}`);
      if (s) l.appendChild(h("span", "aria-nota-legenda", ` (${fmt(g.indici.length)} ore)`));
      boxLegenda.appendChild(l);
    });
    if (s) {
      const voce = (testo, cls, col, val, f) => {
        const l = h("label", "casella aria-voce-legenda");
        const c = document.createElement("input"); c.type = "checkbox"; c.checked = val;
        c.addEventListener("change", () => f(c.checked));
        const camp = h("span", `aria-segno ${cls}`); camp.setAttribute("aria-hidden", "true");
        camp.style.setProperty("--colore-strato", col);
        l.append(c, camp, ` ${testo}`);
        boxLegenda.appendChild(l);
      };
      if (zonaValida(st.zona)) voce(`Zona di comfort ${fmt(st.zona.tMin, 1).replace(",0", "")}–${fmt(st.zona.tMax, 1).replace(",0", "")} °C, UR ${fmt(st.zona.urMin)}–${fmt(st.zona.urMax)} %`, "aria-segno-zona", "var(--serie-5)", st.mostraZona, (v) => { st.mostraZona = v; $("ore-zona-mostra").checked = v; disegnaZona(); });
      voce("Punti di progetto (■ inverno, ◆ estate)", "aria-segno-punto", "var(--tenue)", st.mostraProgetto, (v) => { st.mostraProgetto = v; $("ore-progetto-mostra").checked = v; disegnaProgetto(); });
    }
    boxLegenda.hidden = !boxLegenda.childElementCount;
  }

  function costruisciAspetto() {
    aspetto.innerHTML = "";
    const riga = h("div", "aria-ore-aspetto-riga");
    // punti / densità
    const gm = h("div", "aria-vista aria-ore-modo"); gm.setAttribute("role", "group"); gm.setAttribute("aria-label", "Come disegnare le ore");
    [["punti", "Punti", "Un punto per ora, più pieno dove le ore si addensano"], ["densita", "Densità", "Celle colorate secondo quante ore ci cadono (scala logaritmica)"]].forEach(([k, t, ti]) => {
      const b = h("button", "bottone secondario piccolo", t); b.type = "button"; b.dataset.nuvola = k; b.title = ti;
      b.setAttribute("aria-pressed", String(st.modo === k));
      b.addEventListener("click", () => { st.modo = k; gm.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x.dataset.nuvola === k))); disegnaNuvole(); });
      gm.appendChild(b);
    });
    const lr = h("label", "aria-campo"); lr.append(h("span", null, "Punti"));
    const sr = h("select"); sr.id = "ore-raggio";
    RAGGI.forEach(([t, v]) => { const o = h("option", null, t); o.value = String(v); sr.appendChild(o); });
    sr.value = String(st.raggio);
    sr.addEventListener("change", () => { st.raggio = +sr.value; disegnaNuvole(); });
    lr.appendChild(sr);
    const lt = h("label", "aria-campo aria-ore-trasp"); lt.append(h("span", null, "Trasparenza"));
    const rt = document.createElement("input"); rt.type = "range"; rt.min = "0"; rt.max = String(TRASP.length - 1); rt.step = "1"; rt.value = String(st.trasp); rt.id = "ore-trasp";
    const tt = () => ["molto trasparenti", "più trasparenti", "automatica", "più piene", "molto piene"][+rt.value];
    rt.setAttribute("aria-valuetext", tt());
    let att = 0;
    rt.addEventListener("input", () => { rt.setAttribute("aria-valuetext", tt()); clearTimeout(att); att = setTimeout(() => { st.trasp = +rt.value; disegnaNuvole(); }, 80); });
    lt.appendChild(rt);
    riga.append(gm, lr, lt);
    aspetto.append(riga, h("p", "aiuto aria-ore-aspetto-nota", "Le nuvole con più anni sono disegnate sotto, quelle con meno anni sopra: dove si sovrappongono si vede il colore del gruppo più corto. Passa il mouse sul diagramma per contare le ore di ogni gruppo in quel punto."));
  }

  // ---------------------------------------------------------------- calcoli dei risultati (con copie per gruppo)
  const firma = (g) => JSON.stringify([g.anni, g.da, g.a, g.oraDa, g.oraA, g.giorni]);
  function calcola() {
    const s = S.serie();
    if (!s) { st.ris = null; return null; }
    if (cache.serie !== s) { cache.serie = s; cache.stat.clear(); cache.prog.clear(); }
    const Lv = L.valori(), lk = `${Lv.inverno}|${Lv.estate}`, zk = JSON.stringify(st.zona);
    const gruppi = G.gruppi().map((g) => {
      const f = firma(g);
      let c = cache.stat.get(f);
      if (!c) {
        const i0 = GO.inizioAnni(s, g.anni);
        c = { i0, stat: statistiche(s.t, s.ur, s.p, g.indici, i0, s.n), classiT: classiT(s.t, s.ur, s.p, g.indici), classiX: classiX(s.t, s.ur, s.p, g.indici), zone: new Map() };
        cache.stat.set(f, c);
      }
      let pr = cache.prog.get(`${f}|${lk}`);
      if (!pr) { pr = P.condizioniProgetto(s.t, s.ur, s.p, { inverno: Lv.inverno, estate: Lv.estate, indici: g.indici }); cache.prog.set(`${f}|${lk}`, pr); }
      let zr = c.zone.get(zk);
      if (!zr && zonaValida(st.zona)) { zr = zona(s.t, s.ur, s.p, g.indici, st.zona); c.zone.set(zk, zr); }
      return { id: g.id, indice: g.indice, nome: g.nome, mostra: g.mostra, colore: g.colore, def: g, indici: g.indici, ...c, progetto: pr, zona: zr || null, firmaProgetto: `${f}|${lk}` };
    });
    st.ris = { serie: s, livelli: Lv, gruppi };
    return st.ris;
  }
  function pianifica(subito) {
    clearTimeout(st.attesa);
    const fai = () => {
      const a = performance.now();
      calcola();
      mostraRisultati();
      disegnaProgetto();
      st.msCalcolo = performance.now() - a;
    };
    if (subito) fai(); else st.attesa = setTimeout(fai, 150);
  }

  // valori di progetto: dai dati, o quelli scritti a mano (che valgono finché non cambiano gruppo, serie o livello)
  function valoriProgetto(r) {
    const c = r.progetto, base = c && c.inverno ? { invT: c.inverno.t, invUR: c.inverno.ur, estT: c.estate.t, estTwb: c.estate.twb } : {};
    const m = st.modifiche.get(r.id);
    if (m && m.firma === r.firmaProgetto && m.serie === st.ris.serie) return { ...base, ...m.valori };
    return base;
  }

  // ---------------------------------------------------------------- tabelle
  function tabella(testa, righe, opz = {}) {
    const box = h("div", "tabella-scorre");
    const t = h("table", `mensili aria-ore-tabella${opz.cls ? ` ${opz.cls}` : ""}`);
    if (opz.didascalia) t.appendChild(h("caption", "solo-lettori", opz.didascalia));
    const th = h("thead"), tr = h("tr");
    testa.forEach((c) => { const e = h("th"); e.scope = "col"; if (c instanceof Node) e.appendChild(c.cloneNode(true)); else e.textContent = c; tr.appendChild(e); });
    th.appendChild(tr); t.appendChild(th);
    const tb = h("tbody");
    righe.forEach((r) => {
      const tr2 = h("tr");
      r.forEach((c, i) => {
        const e = h(i === 0 ? "th" : "td");
        if (i === 0) e.scope = "row";
        if (c instanceof Node) e.appendChild(c); else e.textContent = c;
        tr2.appendChild(e);
      });
      tb.appendChild(tr2);
    });
    t.appendChild(tb); box.appendChild(t);
    return box;
  }
  function testaGruppo(r) {
    const s = h("span", "aria-ore-testa");
    const c = h("span", "aria-campione"); c.style.background = r.colore; c.setAttribute("aria-hidden", "true");
    s.append(c, h("span", null, r.nome));
    if (!r.mostra) s.appendChild(h("small", null, " (nascosto)"));
    return s;
  }

  function mostraRisultati() {
    const boxS = $("ore-stat"), box = $("aria-risultati"), boxZ = $("ore-zona-risultati");
    const r = st.ris;
    $("passo-risultati").hidden = !r;
    $("passo-zona").hidden = !r;
    if (!r) { boxS.innerHTML = ""; box.innerHTML = ""; boxZ.innerHTML = ""; return; }
    const s = r.serie, gr = r.gruppi;
    boxS.innerHTML = ""; box.innerHTML = "";
    const testa = ["", ...gr.map(testaGruppo)];
    boxS.appendChild(h("p", "aiuto", `${s.sintetica ? "Dati sintetici di prova" : `Serie oraria di ${s.comune || "comune"}`}: ogni colonna è un gruppo di ore del passo 2. Le statistiche contano solo le ore con temperatura e umidità; «ore l'anno» = ore del gruppo divise per gli anni della sua finestra (anno medio di ${fmt(ANNO)} ore).`));

    // statistiche
    const R = (nome, f, d) => [nome, ...gr.map((g) => fmtS(f(g.stat), d))];
    boxS.appendChild(tabella(testa, [
      R("Ore (totale)", (x) => x.ore, 0),
      R("Anni della finestra", (x) => x.anni, 1),
      R("Ore l'anno (media)", (x) => x.oreAnno, 0),
      R("Quota dell'anno (%)", (x) => x.quota, 1),
      R("T minima (°C)", (x) => x.tMin, 1),
      R("T media (°C)", (x) => x.tMedia, 1),
      R("T massima (°C)", (x) => x.tMax, 1),
      R("UR media (%)", (x) => x.urMedia, 0),
      R("x: 1° percentile (g/kg)", (x) => x.x01, 2),
      R("x: mediana (g/kg)", (x) => x.x50, 2),
      R("x: 99° percentile (g/kg)", (x) => x.x99, 2),
      R("h: 1° percentile (kJ/kg)", (x) => x.h01, 1),
      R("h: mediana (kJ/kg)", (x) => x.h50, 1),
      R("h: 99° percentile (kJ/kg)", (x) => x.h99, 1),
      R("Bulbo umido massimo (°C)", (x) => x.twbMax, 1),
    ], { didascalia: "Statistiche delle ore di ogni gruppo", cls: "aria-ore-stat" }));

    // condizioni di progetto (modificabili)
    const Lv = r.livelli, pc = (v) => `${fmt(v, v % 1 ? 1 : 0)} %`;
    box.appendChild(h("p", "aiuto", "Percentili calcolati sulle ore di ciascun gruppo. I campi si possono correggere a mano: i punti sul diagramma e il CSV usano i valori scritti; se cambi gruppo, serie o livello tornano quelli dei dati."));
    const campo = (rr, k, d, lim) => {
      const v = valoriProgetto(rr)[k];
      const inp = document.createElement("input");
      inp.type = "text"; inp.inputMode = "decimal"; inp.className = "aria-ore-campo"; inp.dataset.gruppo = rr.id; inp.dataset.campo = k;
      inp.value = Number.isFinite(v) ? fmt(v, d).replace(/\./g, "") : "";
      inp.setAttribute("aria-label", `${rr.nome}: ${{ invT: "temperatura invernale di progetto", invUR: "UR invernale di progetto", estT: "temperatura estiva di progetto", estTwb: "bulbo umido estivo di progetto" }[k]}`);
      const m = st.modifiche.get(rr.id);
      if (m && m.firma === rr.firmaProgetto && m.valori[k] !== undefined) inp.classList.add("modificato");
      inp.addEventListener("change", () => {
        const n = Number(inp.value.replace(",", "."));
        const ok = inp.value.trim() !== "" && Number.isFinite(n) && n >= lim[0] && n <= lim[1];
        inp.setAttribute("aria-invalid", ok ? "false" : "true");
        if (!ok) return;
        let mm = st.modifiche.get(rr.id);
        if (!mm || mm.firma !== rr.firmaProgetto || mm.serie !== st.ris.serie) { mm = { firma: rr.firmaProgetto, serie: st.ris.serie, valori: {} }; st.modifiche.set(rr.id, mm); }
        mm.valori[k] = n;
        mostraRisultati(); disegnaProgetto();
        const dopo = document.querySelector(`.aria-ore-campo[data-gruppo="${rr.id}"][data-campo="${k}"]`);
        if (dopo) dopo.focus();
      });
      return inp;
    };
    const deriv = (rr, f, d) => { const se = statoEstate(valoriProgetto(rr)); return se ? fmtS(f(se), d) : "—"; };
    const righeP = [
      [`Inverno ${pc(Lv.inverno)}: T (°C)`, ...gr.map((g) => (g.progetto.inverno ? campo(g, "invT", 1, [-60, 50]) : "—"))],
      ["Inverno: UR coincidente (%)", ...gr.map((g) => (g.progetto.inverno ? campo(g, "invUR", 0, [1, 100]) : "—"))],
      [`Estate ${pc(Lv.estate)}: T (°C)`, ...gr.map((g) => (g.progetto.inverno ? campo(g, "estT", 1, [-40, 60]) : "—"))],
      ["Estate: bulbo umido coincidente (°C)", ...gr.map((g) => (g.progetto.inverno ? campo(g, "estTwb", 1, [-40, 45]) : "—"))],
      ["Estate: UR (%)", ...gr.map((g) => deriv(g, (q) => q.ur, 0))],
      ["Estate: x (g/kg)", ...gr.map((g) => deriv(g, (q) => q.xg, 2))],
      ["Estate: h (kJ/kg)", ...gr.map((g) => deriv(g, (q) => q.h, 1))],
      [`Entalpia ${pc(Lv.estate)} (kJ/kg)`, ...gr.map((g) => (g.progetto.entalpia ? fmtS(g.progetto.entalpia.h, 1) : "—"))],
      [`Umidità specifica ${pc(Lv.estate)} (g/kg)`, ...gr.map((g) => (g.progetto.umidita ? fmt(g.progetto.umidita.xg, 2) : "—"))],
      ["… con la T media (°C)", ...gr.map((g) => (g.progetto.umidita ? fmtS(g.progetto.umidita.t, 1) : "—"))],
    ];
    box.appendChild(tabella(testa, righeP, { didascalia: "Condizioni di progetto di ogni gruppo", cls: "aria-ore-progetto" }));
    const rip = h("div", "aria-ore-azioni");
    const bR = h("button", "bottone secondario piccolo", "Ripristina dai dati"); bR.type = "button"; bR.id = "ore-ripristina";
    bR.disabled = !st.modifiche.size;
    bR.addEventListener("click", () => { st.modifiche.clear(); mostraRisultati(); disegnaProgetto(); });
    const lp = h("label", "casella aria-ore-casella");
    const cp = document.createElement("input"); cp.type = "checkbox"; cp.id = "ore-progetto-mostra"; cp.checked = st.mostraProgetto;
    cp.addEventListener("change", () => { st.mostraProgetto = cp.checked; disegnaProgetto(); });
    lp.append(cp, " Mostra i punti di progetto sul diagramma");
    rip.append(bR, lp);
    if (gr.some((g) => !g.progetto.inverno)) rip.appendChild(h("p", "aiuto", "Un gruppo con meno di 24 ore valide non ha condizioni di progetto."));
    box.appendChild(rip);

    // classi (metodo dei bin)
    box.appendChild(h("h3", null, "Ore per classe (metodo dei bin)"));
    box.appendChild(h("p", "aiuto", "Ore per classe di temperatura (2 K) e di umidità specifica (1 g/kg): servono per stimare l'energia delle batterie e le ore di funzionamento di ogni regime dell'UTA. Classe «da … a»: il primo valore è compreso, il secondo no."));
    const lv = h("label", "aria-campo aria-ore-vista"); lv.append(h("span", null, "Tabella"));
    const sv = h("select"); sv.id = "ore-vista";
    [["confronto", "Confronto dei gruppi (ore l'anno)"], ...gr.map((g) => [g.id, `Gruppo ${g.indice + 1}: ${g.nome} (valori medi)`])].forEach(([v, t]) => { const o = h("option", null, t); o.value = v; sv.appendChild(o); });
    if (st.vista !== "confronto" && !gr.some((g) => g.id === st.vista)) st.vista = "confronto";
    sv.value = st.vista;
    sv.addEventListener("change", () => { st.vista = sv.value; mostraRisultati(); const e = $("ore-vista"); if (e) e.focus(); });
    lv.appendChild(sv);
    box.appendChild(lv);
    box.append(...tabelleClassi(gr));

    // scaricamenti
    const sc = h("div", "scarica aria-ore-scarica");
    const b1 = h("button", "bottone secondario", "Statistiche e classi (CSV)"); b1.type = "button"; b1.id = "ore-csv";
    b1.addEventListener("click", scaricaStatistiche);
    const lg = h("label", "aria-campo"); lg.append(h("span", null, "Ore di un gruppo"));
    const sg = h("select"); sg.id = "ore-csv-gruppo";
    gr.forEach((g) => { const o = h("option", null, `Gruppo ${g.indice + 1}: ${g.nome}`); o.value = g.id; sg.appendChild(o); });
    lg.appendChild(sg);
    const b2 = h("button", "bottone secondario", "Ore del gruppo (CSV)"); b2.type = "button"; b2.id = "ore-csv-orario";
    b2.addEventListener("click", () => scaricaOre(sg.value));
    sc.append(b1, lg, b2);
    box.appendChild(sc);
    box.appendChild(h("p", "aiuto", `Il CSV delle ore ha una riga per ora (ora UTC e locale, T, UR, x, h, bulbo umido): al massimo ${fmt(MAX_RIGHE_CSV)} righe, le più recenti se il gruppo ne ha di più. L'immagine del diagramma si scarica sotto il diagramma (PNG o SVG, con i gruppi elencati nella fascia).`));
    const msg = h("div", "messaggio"); msg.id = "ore-msg"; msg.setAttribute("role", "status"); msg.setAttribute("aria-live", "polite");
    box.appendChild(msg);

    mostraZona(gr);
  }

  function tabelleClassi(gr) {
    const out = [];
    const etT = (c) => `${fmtS(c.da)} … ${fmtS(c.a)}`;
    if (st.vista === "confronto") {
      const testa = ["T (°C)", ...gr.map(testaGruppo)];
      const unisci = (chiave) => {
        const m = new Map();
        gr.forEach((g, j) => g[chiave].forEach((c) => { if (!c.ore) return; const k = c.da; if (!m.has(k)) m.set(k, { c, v: new Array(gr.length).fill(0) }); m.get(k).v[j] = c.ore / (g.stat.anni || 1); }));
        return [...m.entries()].sort((a, b) => a[0] - b[0]).map(([, x]) => x);
      };
      const val = (v) => (v ? fmt(v, v < 10 ? 1 : 0) : "");
      out.push(tabella(testa, unisci("classiT").map((x) => [etT(x.c), ...x.v.map(val)]), { didascalia: "Ore l'anno per classe di temperatura", cls: "aria-ore-classi" }));
      const testaX = ["x (g/kg)", ...gr.map(testaGruppo)];
      out.push(tabella(testaX, unisci("classiX").map((x) => [etT(x.c), ...x.v.map(val)]), { didascalia: "Ore l'anno per classe di umidità specifica", cls: "aria-ore-classi" }));
      return out;
    }
    const g = gr.find((x) => x.id === st.vista), anni = g.stat.anni || 1;
    out.push(tabella(["T (°C)", "Ore", "Ore l'anno", "UR media (%)", "x media (g/kg)", "h media (kJ/kg)", "Bulbo umido medio (°C)"],
      g.classiT.filter((c) => c.ore).map((c) => [etT(c), fmt(c.ore), fmt(c.ore / anni, c.ore / anni < 10 ? 1 : 0), fmt(c.ur, 0), fmt(c.x, 2), fmtS(c.h, 1), fmtS(c.twb, 1)]),
      { didascalia: `Classi di temperatura del gruppo ${g.nome}`, cls: "aria-ore-classi" }));
    out.push(tabella(["x (g/kg)", "Ore", "Ore l'anno", "T media (°C)", "UR media (%)", "h media (kJ/kg)"],
      g.classiX.filter((c) => c.ore).map((c) => [etT(c), fmt(c.ore), fmt(c.ore / anni, c.ore / anni < 10 ? 1 : 0), fmtS(c.t, 1), fmt(c.ur, 0), fmtS(c.h, 1)]),
      { didascalia: `Classi di umidità specifica del gruppo ${g.nome}`, cls: "aria-ore-classi" }));
    return out;
  }

  function mostraZona(gr) {
    const box = $("ore-zona-risultati");
    box.innerHTML = "";
    if (!zonaValida(st.zona)) { box.appendChild(h("p", "messaggio errore", "Controlla i limiti della zona: T minima < T massima e 0 ≤ UR minima < UR massima ≤ 100.")); return; }
    const testa = ["", ...gr.map(testaGruppo)];
    const cella = (g, k) => { const z = g.zona; if (!z || !z.ore) return "—"; const a = g.stat.anni || 1; return `${fmt(z[k] / a, 0)} (${fmt(z[k] / z.ore * 100, 0)} %)`; };
    box.appendChild(tabella(testa, [
      ["Nella zona", ...gr.map((g) => cella(g, "dentro"))],
      ["Fuori dalla zona", ...gr.map((g) => cella(g, "fuori"))],
      ["Riscaldamento", ...gr.map((g) => cella(g, "riscaldare"))],
      ["Raffreddamento", ...gr.map((g) => cella(g, "raffreddare"))],
      ["Umidificazione", ...gr.map((g) => cella(g, "umidificare"))],
      ["Deumidificazione", ...gr.map((g) => cella(g, "deumidificare"))],
    ], { didascalia: "Ore l'anno dentro e fuori dalla zona di comfort", cls: "aria-ore-zona" }));
    box.appendChild(h("p", "aiuto", "Ore l'anno e, tra parentesi, quota delle ore del gruppo. Un'ora può chiedere due trattamenti (per esempio riscaldare e umidificare), quindi le righe dei trattamenti non si sommano."));
  }

  // ---------------------------------------------------------------- scaricamenti
  const num = (v, d) => (Number.isFinite(v) ? v.toFixed(d).replace(".", ",") : "");
  const testoCsv = (v) => (/[;"\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));
  function scaricaFile(nome, righe) {
    const b = new Blob(["﻿" + righe.map((r) => r.map(testoCsv).join(";")).join("\r\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(b); a.download = nome; a.hidden = true;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 60000);
    const m = $("ore-msg"); if (m) m.textContent = `Download avviato: ${nome} (${fmt(b.size / 1024, 0)} kB).`;
  }
  const nomeBase = () => { const s = st.ris && st.ris.serie; return `eugenio-aria-ore-${s ? (s.sintetica ? "prova" : s.istat) : "comune"}`; };
  function intestazione() {
    const s = st.ris.serie;
    return [["EuGEnio – Trattamento aria › Ore di funzionamento (pagina sperimentale)"],
      ["Comune", `${s.comune || ""}${s.istat ? ` (${s.istat})` : ""}`], ["Serie", `dal ${s.dal || ""} al ${s.al || ""}, ${s.n} ore`], ["Fonte", s.fonte || ""],
      ["Pressione di calcolo (Pa)", num(s.p, 0)],
      ...(s.sintetica ? [["Avviso", "Dati sintetici di prova, non reali."]] : []),
      ["Nota", "Statistiche della serie oraria, non valori di norma."]];
  }
  function descriviGruppo(g) {
    const d = g.def;
    return `${d.da}–${d.a}, ore ${d.oraDa}–${d.oraA}, giorni ${d.giorni}, ${testoAnni(d.anni).replace("tutta la serie", "tutta la serie caricata")}`;
  }
  function scaricaStatistiche() {
    const r = st.ris; if (!r) return;
    const gr = r.gruppi, out = intestazione();
    out.push([], ["Gruppi"], ["Gruppo", "Nome", "Filtro", "Mostrato"]);
    gr.forEach((g) => out.push([g.indice + 1, g.nome, descriviGruppo(g), g.mostra ? "sì" : "no"]));
    out.push([], ["Statistiche"], ["Grandezza", ...gr.map((g) => `${g.indice + 1} ${g.nome}`)]);
    [["Ore (totale)", "ore", 0], ["Anni della finestra", "anni", 3], ["Ore l'anno", "oreAnno", 1], ["Quota dell'anno (%)", "quota", 2], ["T minima (°C)", "tMin", 1],
      ["T media (°C)", "tMedia", 2], ["T massima (°C)", "tMax", 1], ["UR media (%)", "urMedia", 1], ["x 1° percentile (g/kg)", "x01", 3], ["x mediana (g/kg)", "x50", 3],
      ["x 99° percentile (g/kg)", "x99", 3], ["h 1° percentile (kJ/kg)", "h01", 2], ["h mediana (kJ/kg)", "h50", 2], ["h 99° percentile (kJ/kg)", "h99", 2],
      ["Bulbo umido massimo (°C)", "twbMax", 2]].forEach(([t, k, d]) => out.push([t, ...gr.map((g) => num(g.stat[k], d))]));
    const Lv = r.livelli;
    out.push([], [`Condizioni di progetto (livelli inverno ${num(Lv.inverno, 1)} %, estate ${num(Lv.estate, 1)} %; valori eventualmente corretti a mano)`]);
    out.push(["Grandezza", ...gr.map((g) => `${g.indice + 1} ${g.nome}`)]);
    const V = gr.map((g) => valoriProgetto(g)), SE = V.map((v) => statoEstate(v));
    out.push(["Inverno T (°C)", ...V.map((v) => num(v.invT, 1))], ["Inverno UR (%)", ...V.map((v) => num(v.invUR, 0))],
      ["Estate T (°C)", ...V.map((v) => num(v.estT, 1))], ["Estate bulbo umido (°C)", ...V.map((v) => num(v.estTwb, 1))],
      ["Estate x (g/kg)", ...SE.map((q) => (q ? num(q.xg, 2) : ""))], ["Estate h (kJ/kg)", ...SE.map((q) => (q ? num(q.h, 1) : ""))],
      ["Entalpia di progetto (kJ/kg)", ...gr.map((g) => (g.progetto.entalpia ? num(g.progetto.entalpia.h, 1) : ""))],
      ["Umidità specifica di progetto (g/kg)", ...gr.map((g) => (g.progetto.umidita ? num(g.progetto.umidita.xg, 2) : ""))],
      ["Corretti a mano", ...gr.map((g) => { const m = st.modifiche.get(g.id); return m && m.firma === g.firmaProgetto ? Object.keys(m.valori).join(" ") : ""; })]);
    if (zonaValida(st.zona)) {
      const z = st.zona;
      out.push([], [`Zona di comfort T ${num(z.tMin, 1)}–${num(z.tMax, 1)} °C, UR ${num(z.urMin, 0)}–${num(z.urMax, 0)} % (ore totali del gruppo)`]);
      out.push(["Ore", ...gr.map((g) => `${g.indice + 1} ${g.nome}`)]);
      [["Nella zona", "dentro"], ["Fuori", "fuori"], ["Riscaldamento", "riscaldare"], ["Raffreddamento", "raffreddare"], ["Umidificazione", "umidificare"], ["Deumidificazione", "deumidificare"]]
        .forEach(([t, k]) => out.push([t, ...gr.map((g) => (g.zona ? g.zona[k] : ""))]));
      out.push(["Regole", "T < T min: riscaldamento; T > T max: raffreddamento (a x costante fino al limite); poi UR a quella T < UR min: umidificazione, > UR max: deumidificazione."]);
    }
    gr.forEach((g) => {
      out.push([], [`Gruppo ${g.indice + 1} – ${g.nome}: classi di temperatura (2 K)`], ["T da (°C)", "T a (°C)", "Ore", "Ore l'anno", "UR media (%)", "x media (g/kg)", "h media (kJ/kg)", "Bulbo umido medio (°C)"]);
      g.classiT.forEach((c) => out.push([num(c.da, 0), num(c.a, 0), c.ore, num(c.ore / (g.stat.anni || 1), 1), num(c.ur, 1), num(c.x, 3), num(c.h, 2), num(c.twb, 2)]));
      out.push([], [`Gruppo ${g.indice + 1} – ${g.nome}: classi di umidità specifica (1 g/kg)`], ["x da (g/kg)", "x a (g/kg)", "Ore", "Ore l'anno", "T media (°C)", "UR media (%)", "h media (kJ/kg)"]);
      g.classiX.forEach((c) => out.push([num(c.da, 0), num(c.a, 0), c.ore, num(c.ore / (g.stat.anni || 1), 1), num(c.t, 2), num(c.ur, 1), num(c.h, 2)]));
      const s = r.serie, M = matriceTX(s.t, s.ur, s.p, g.indici);
      out.push([], [`Gruppo ${g.indice + 1} – ${g.nome}: ore per classe di T (righe, °C) e di x (colonne, g/kg)`], ["T \\ x", ...M.x.map((x) => `${x}–${x + PASSO_X}`)]);
      M.ore.forEach((riga, i) => out.push([`${M.t[i]}–${M.t[i] + PASSO_T}`, ...riga]));
    });
    out.push([], ["Fonte", "EuGEnio – eugenio.statocritico.it (CC BY 4.0)"]);
    scaricaFile(`${nomeBase()}-statistiche.csv`, out);
  }
  function scaricaOre(id) {
    const r = st.ris; if (!r) return;
    const g = r.gruppi.find((x) => x.id === id) || r.gruppi[0], s = r.serie;
    const V = P.vettori(s.t, s.ur, s.p), C = GO.campiOrari(s);
    const idx = g.indici, da = Math.max(0, idx.length - MAX_RIGHE_CSV);
    const out = intestazione();
    out.push(["Gruppo", `${g.indice + 1} ${g.nome} (${descriviGruppo(g)})`]);
    if (da) out.push(["Attenzione", `Il gruppo ha ${idx.length} ore: qui ci sono solo le ultime ${MAX_RIGHE_CSV}.`]);
    out.push([], ["Ora UTC", "Data e ora locale", "T (°C)", "UR (%)", "x (g/kg)", "h (kJ/kg)", "Bulbo umido (°C)"]);
    const due = (v) => String(v).padStart(2, "0");
    for (let k = da; k < idx.length; k++) {
      const i = idx[k];
      out.push([new Date(s.inizio + i * 3600000).toISOString().slice(0, 16) + "Z", `${C.anno[i]}-${due(C.mese[i])}-${due(C.giorno[i])} ${due(C.ora[i])}:00`,
        num(s.t[i], 1), num(s.ur[i], 0), num(V.x[i] * 1000, 2), num(V.h[i], 1), num(V.twb[i], 1)]);
    }
    scaricaFile(`${nomeBase()}-gruppo${g.indice + 1}-ore.csv`, out);
  }

  // righe sotto le immagini del diagramma: serie, gruppi con il loro colore di stampa, zona e punti
  function righeFonti() {
    const s = S && S.serie();
    if (!s) return [];
    const r = [`Serie oraria: ${s.comune || ""}, ${s.fonte}${s.licenza && s.licenza !== "—" ? ` (${s.licenza})` : ""}, dal ${s.dal || ""} al ${s.al || ""}.`];
    G.gruppi().forEach((g, i) => { if (g.mostra) r.push(`Gruppo ${i + 1} (${NOMI_COLORI[i % 6]}): ${g.nome} – ${fmt(g.indici.length)} ore.`); });
    if (st.mostraZona && zonaValida(st.zona)) r.push(`Zona di comfort (verde, tratteggio): T ${fmt(st.zona.tMin, 1)}–${fmt(st.zona.tMax, 1)} °C, UR ${fmt(st.zona.urMin)}–${fmt(st.zona.urMax)} %.`);
    if (st.mostraProgetto && st.ris) { const Lv = st.ris.livelli; r.push(`Punti di progetto dei gruppi: quadrato = inverno ${fmt(Lv.inverno, 1)} %, rombo = estate ${fmt(Lv.estate, 1)} % (statistiche della serie, non valori di norma).`); }
    return r;
  }

  // ---------------------------------------------------------------- passo 4: zona di comfort
  function costruisciZona() {
    const box = $("ore-zona-campi");
    const righe = h("div", "aria-campi");
    [["tMin", "T minima (°C)"], ["tMax", "T massima (°C)"], ["urMin", "UR minima (%)"], ["urMax", "UR massima (%)"]].forEach(([k, t]) => {
      const l = h("label", "aria-campo"); l.append(h("span", null, t));
      const inp = document.createElement("input"); inp.type = "text"; inp.inputMode = "decimal"; inp.id = `ore-zona-${k}`; inp.size = 5;
      inp.value = fmt(st.zona[k], 0);
      let att = 0;
      inp.addEventListener("input", () => {
        const v = Number(inp.value.replace(",", "."));
        const ok = inp.value.trim() !== "" && Number.isFinite(v);
        inp.setAttribute("aria-invalid", ok ? "false" : "true");
        if (!ok) return;
        clearTimeout(att);
        att = setTimeout(() => { st.zona = { ...st.zona, [k]: v }; disegnaZona(); pianifica(true); }, 200);
      });
      l.appendChild(inp); righe.appendChild(l);
    });
    const lm = h("label", "casella aria-ore-casella");
    const cm = document.createElement("input"); cm.type = "checkbox"; cm.id = "ore-zona-mostra"; cm.checked = st.mostraZona;
    cm.addEventListener("change", () => { st.mostraZona = cm.checked; disegnaZona(); });
    lm.append(cm, " Mostra la zona sul diagramma");
    box.append(righe, lm);
  }

  // ---------------------------------------------------------------- collegamenti
  costruisciZona();
  S.su((d) => {
    D.titolo(d.serie ? `${titolo} – ${d.comune}` : titolo);
    if (d.serie) D.pressione(d.serie.p);
    G.zona(d.zona);
    G.serie(d.serie);
    if (!d.serie) { st.ris = null; disegnaNuvole(); disegnaZona(); disegnaProgetto(); mostraRisultati(); }
  });
  G.su((gr) => {
    if (nomiAutomatici(gr)) return;              // arriva subito un altro evento con i nomi nuovi
    controllaAnni(gr);
    disegnaNuvole();
    disegnaZona();
    if (S.serie()) pianifica(false); else { st.ris = null; mostraRisultati(); }
  });
  L.su(() => { if (S.serie()) pianifica(false); });
  document.addEventListener("eugenio:aspetto", () => { legenda(); if (st.ris) mostraRisultati(); });

  legenda();
  window.EUGENIO_ARIA_PAGINA = { diagramma: D, scelta: S, gruppi: G, livello: L, calcoli: API, risultati: () => st.ris, stato: st,
    ricalcola: () => { pianifica(true); return st.ris; } };
})(typeof self !== "undefined" ? self : globalThis);
