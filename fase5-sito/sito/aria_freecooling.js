"use strict";
// Trattamento aria › Free cooling e recupero (14/11/2026, pagina sperimentale). Dalla serie oraria del comune (passo 1,
// scelta_aria.js) e dai gruppi di ore (gruppi_ore.js) stima, ora per ora, le ore e l'energia del free cooling di un'UTA a
// tutt'aria (economizzatore a temperatura ed entalpico) e del recuperatore di calore tra espulsione e aria esterna (inverno
// ed estate, rischio di brina, sbrinamento con by-pass, elettricità in più dei ventilatori). È una stima del potenziale con
// un modello semplice e dichiarato, non una simulazione dell'edificio: le formule sono nel commento di
// fase14-trattamento-aria/aria/freecooling.py, gemello Python della parte di calcolo (test di parità in node).
//
// Parte pura (anche in node: require("./aria_freecooling.js")): opzioni, calcola, riassumi, unOra, REGIMI.
// Parte nella pagina: passo 2 (gruppi e dati dell'UTA), passo 3 (risultati, CSV), passo 4 (potenza di progetto), diagramma.
(function (radice) {
  const P = radice.EUGENIO_PSICRO || (typeof require === "function" ? require("./psicro.js") : null);
  const REGIMI = ["nessuno", "totale", "parziale", "entalpico", "estivo", "invernale", "brina"];
  const SENZA_DATI = 255;
  const PREDEFINITI = {
    V: 10000, riferimento: 0, quotaMinima: 30, estate: { t: 26, ur: 50 }, inverno: { t: 20, ur: 40 },
    tMandata: 16, tBilancio: 12, economizzatore: "entalpico", xMax: null,
    epsS: 0.7, epsL: 0, regolaBrina: "rugiada", tSoglia: -5, sbrinamento: true, dP: 150, etaV: 0.6,
  };
  const X_MAX_RIF = [26, 60];                  // x massima predefinita: x a 26 °C e UR 60 %
  const EPS_L_ENTALPICO = 0.6;                 // εl proposta quando si sceglie il recuperatore entalpico (ruota)

  const num = (v, pred) => { const n = typeof v === "string" ? Number(v.replace(",", ".")) : Number(v); return v !== null && v !== "" && Number.isFinite(n) ? n : pred; };
  const lim = (v, a, b) => Math.min(b, Math.max(a, v));
  // opzioni complete e limitate ai campi sensati (stessa funzione in Python)
  function opzioni(o, p) {
    o = o || {};
    const d = PREDEFINITI, est = o.estate || {}, inv = o.inverno || {};
    const r = {
      V: lim(num(o.V, d.V), 0, 1e7),
      riferimento: lim(Math.round(num(o.riferimento, d.riferimento)), 0, 3),
      quotaMinima: lim(num(o.quotaMinima, d.quotaMinima), 0, 100),
      estate: { t: lim(num(est.t, d.estate.t), 10, 40), ur: lim(num(est.ur, d.estate.ur), 1, 100) },
      inverno: { t: lim(num(inv.t, d.inverno.t), 5, 35), ur: lim(num(inv.ur, d.inverno.ur), 1, 100) },
      tMandata: lim(num(o.tMandata, d.tMandata), 0, 35),
      tBilancio: lim(num(o.tBilancio, d.tBilancio), -30, 40),
      economizzatore: o.economizzatore === "temperatura" ? "temperatura" : "entalpico",
      epsS: lim(num(o.epsS, d.epsS), 0, 1),
      epsL: lim(num(o.epsL, d.epsL), 0, 1),
      regolaBrina: o.regolaBrina === "soglia" ? "soglia" : "rugiada",
      tSoglia: lim(num(o.tSoglia, d.tSoglia), -40, 20),
      sbrinamento: o.sbrinamento !== false,
      dP: lim(num(o.dP, d.dP), 0, 5000),
      etaV: lim(num(o.etaV, d.etaV), 0.05, 1),
    };
    const xm = num(o.xMax, NaN);
    r.xMax = xm > 0 ? xm : P.xDaUR(X_MAX_RIF[0], X_MAX_RIF[1], p);
    return r;
  }
  // kW elettrici in più nelle ore di recupero: 2 flussi × (f_min·V/3600) m³/s × ΔP Pa / η
  const potenzaVentilatore = (o) => 2 * (o.quotaMinima / 100 * o.V / 3600) * o.dP / o.etaV / 1000;

  // Calcolo ora per ora su tutta la serie (formule nel commento di freecooling.py). t °C, x kg/kg, h kJ/kg (NaN = ora
  // senza dati). Risultato: regime (Uint8: codici di REGIMI, 255 senza dati), bandiere (1 free cooling a temperatura,
  // 2 entalpico, 4 modo raffrescamento), fcT, fcH (kW di freddo evitati), rec (kW recuperati), perso (kW persi per lo
  // sbrinamento), q0 (kW della batteria fredda senza economizzatore), m (kg/s), pVent (kW elettrici nelle ore di recupero).
  function calcola(t, x, h, p, oIn) {
    const o = opzioni(oIn, p);
    const n = t.length;
    const regime = new Uint8Array(n), bandiere = new Uint8Array(n);
    const fcT = new Float64Array(n), fcH = new Float64Array(n), rec = new Float64Array(n), perso = new Float64Array(n),
      q0a = new Float64Array(n), ma = new Float64Array(n);
    const E = o.estate, I = o.inverno;
    const xrE = P.xDaUR(E.t, E.ur, p), xrI = P.xDaUR(I.t, I.ur, p), trE = E.t, trI = I.t;
    const hrE = P.entalpia(trE, xrE), hrI = P.entalpia(trI, xrI), vE = P.volume(trE, xrE, p), vI = P.volume(trI, xrI, p);
    const tS = o.tMandata, xSatS = P.xSat(tS, p), fm = o.quotaMinima / 100, eS = o.epsS, eL = o.epsL;
    const vStd = P.RA * 293.15 / 101.325, rif = o.riferimento, tB = o.tBilancio, xMax = o.xMax;
    const entalpico = o.economizzatore === "entalpico", soglia = o.regolaBrina === "soglia", sbrina = o.sbrinamento;
    const tLimSoglia = trI - eS * (trI - o.tSoglia);
    const hm = (xx) => P.entalpia(tS, Math.min(xx, xSatS));
    for (let i = 0; i < n; i++) {
      const te = t[i], xe = x[i], he = h[i];
      if (!(te === te) || !(xe === xe) || !(he === he)) { regime[i] = SENZA_DATI; continue; }
      const raff = te > tB;
      const vref = rif === 0 ? P.volume(te, xe, p) : rif === 1 ? (raff ? vE : vI) : rif === 2 ? vStd : (1 + xe) / 1.2;
      const m = o.V / 3600 / vref, mOA = fm * m;
      ma[i] = m;
      if (raff) {
        const xin0 = fm * xe + (1 - fm) * xrE, hin0 = fm * he + (1 - fm) * hrE;
        const q0 = m * Math.max(0, hin0 - hm(xin0)), qOA = m * Math.max(0, he - hm(xe));
        const tot = te <= tS, onT = !tot && te < trE, onH = !tot && he < hrE && xe <= xMax;
        fcT[i] = tot ? q0 : onT ? q0 - qOA : 0;
        fcH[i] = tot ? q0 : onH ? q0 - qOA : 0;
        q0a[i] = q0;
        bandiere[i] = (tot || onT ? 1 : 0) | (tot || onH ? 2 : 0) | 4;
        const on = entalpico ? onH : onT;
        if (tot) regime[i] = 1;
        else if (on) regime[i] = te < trE ? 2 : 3;
        else {
          const dh = he - P.entalpia(te + eS * (trE - te), xe + eL * (xrE - xe));
          if (dh > 0) { rec[i] = mOA * dh; regime[i] = 4; } else regime[i] = 0;
        }
      } else if (te < trI) {
        let q = mOA * Math.max(0, P.entalpia(te + eS * (trI - te), xe + eL * (xrI - xe)) - he);
        const tX = trI - eS * (trI - te);
        let brina, tLim;
        if (soglia) { brina = te < o.tSoglia; tLim = tLimSoglia; }
        else { brina = tX < 0 && tX < P.tRugiada(xrI - eL * (xrI - xe), p); tLim = 0; }
        if (brina && sbrina) {
          const eEff = Math.min(eS, Math.max(0, (trI - tLim) / (trI - te)));
          const lEff = eS > 0 ? eL * eEff / eS : 0;
          const qBy = mOA * Math.max(0, P.entalpia(te + eEff * (trI - te), xe + lEff * (xrI - xe)) - he);
          perso[i] = q - qBy; q = qBy;
        }
        rec[i] = q;
        regime[i] = brina ? 6 : q > 0 ? 5 : 0;
      } else regime[i] = 0;
    }
    return { opzioni: o, n, p, regime, bandiere, fcT, fcH, rec, perso, q0: q0a, m: ma, pVent: potenzaVentilatore(o) };
  }

  // Somme di un gruppo di ore (indici), per anno medio (anni coperti dal gruppo). mese (Uint8Array 1–12 per ogni ora
  // della serie) facoltativo: tabella mensile dell'anno medio.
  function riassumi(R, indici, anni, mese) {
    const o = R.opzioni, a = Math.max(anni, 1 / 8766), entalpico = o.economizzatore === "entalpico";
    const oreRegime = new Array(REGIMI.length).fill(0);
    let ore = 0, raffN = 0, fcTN = 0, fcHN = 0, kT = 0, kH = 0, pT = 0, pH = 0, kInv = 0, kEst = 0, pInv = 0, pEst = 0, kPerso = 0, nRec = 0;
    const M = mese ? { oreFc: new Float64Array(12), kwhFc: new Float64Array(12), kwhInverno: new Float64Array(12), kwhEstate: new Float64Array(12),
      oreBrina: new Float64Array(12), kwhElettrici: new Float64Array(12), kwhPerso: new Float64Array(12) } : null;
    const bit = entalpico ? 2 : 1;
    for (let k = 0; k < indici.length; k++) {
      const i = indici[k], r = R.regime[i];
      if (r === SENZA_DATI) continue;
      ore++;
      oreRegime[r]++;
      const b = R.bandiere[i], raff = (b & 4) > 0, ft = R.fcT[i], fh = R.fcH[i], q = R.rec[i];
      if (raff) raffN++;
      if (b & 1) fcTN++;
      if (b & 2) fcHN++;
      kT += ft; kH += fh;
      if (ft > pT) pT = ft;
      if (fh > pH) pH = fh;
      const inv = !raff && q > 0, est = raff && r === 4;
      if (inv) { kInv += q; if (q > pInv) pInv = q; }
      if (est) { kEst += q; if (q > pEst) pEst = q; }
      kPerso += R.perso[i];
      if (q > 0) nRec++;
      if (M) {
        const mm = mese[i] - 1;
        if (b & bit) M.oreFc[mm]++;
        M.kwhFc[mm] += entalpico ? fh : ft;
        if (inv) M.kwhInverno[mm] += q;
        if (est) M.kwhEstate[mm] += q;
        if (r === 6) M.oreBrina[mm]++;
        if (q > 0) M.kwhElettrici[mm] += R.pVent;
        M.kwhPerso[mm] += R.perso[i];
      }
    }
    const out = {
      ore, anni: a, oreRegime: oreRegime.map((v) => v / a), oreRaffrescamento: raffN / a, oreFcT: fcTN / a, oreFcH: fcHN / a,
      kwhFcT: kT / a, kwhFcH: kH / a, kwhFc: (entalpico ? kH : kT) / a, piccoFcT: pT, piccoFcH: pH,
      kwhInverno: kInv / a, kwhEstate: kEst / a, piccoInverno: pInv, piccoEstate: pEst, kwhPerso: kPerso / a,
      oreBrina: oreRegime[6] / a, oreRecupero: nRec / a, kwhElettrici: nRec * R.pVent / a,
    };
    out.rapporto = out.kwhElettrici > 0 ? (out.kwhInverno + out.kwhEstate) / out.kwhElettrici : NaN;
    if (M) { out.mensile = {}; for (const k of Object.keys(M)) out.mensile[k] = Array.from(M[k], (v) => v / a); }
    return out;
  }
  // una sola ora (condizioni di progetto, controlli a mano)
  function unOra(t, ur, p, o) {
    const x = P.xDaUR(t, ur, p);
    const R = calcola([t], [x], [P.entalpia(t, x)], p, o);
    return { regime: REGIMI[R.regime[0]] || "senza dati", raffrescamento: (R.bandiere[0] & 4) > 0, fcT: R.fcT[0], fcH: R.fcH[0],
      rec: R.rec[0], perso: R.perso[0], q0: R.q0[0], m: R.m[0], pVent: R.pVent, opzioni: R.opzioni };
  }

  const API = { REGIMI, SENZA_DATI, PREDEFINITI, X_MAX_RIF, EPS_L_ENTALPICO, opzioni, potenzaVentilatore, calcola, riassumi, unOra };
  radice.EUGENIO_FREECOOLING = API;
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  if (typeof document === "undefined") return;

  // ==================================================================== la pagina
  // migliaia sempre col punto (it-IT non separa i numeri di 4 cifre)
  const fmt = (n, d = 0) => (Number.isFinite(n) ? Number(n).toLocaleString("it-IT", { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: "always" }) : "—");
  const fmtT = (n, d = 1) => fmt(n, d).replace(/^-/, "−");
  const kwh = (n) => (Number.isFinite(n) ? fmt(Math.abs(n) >= 100 ? Math.round(n / 10) * 10 : n, 0) : "—");
  const kw = (n) => fmt(n, Math.abs(n) >= 100 ? 0 : 1);
  // numero scritto all'italiana: «0,7», «−5», «10000» (con la virgola i punti sono separatori delle migliaia)
  function leggiNum(testo) {
    let t = String(testo).trim().replace(/\s/g, "").replace(/^[−–]/, "-");
    if (t === "") return NaN;
    if (t.includes(",")) t = t.replace(/\./g, "").replace(",", ".");
    return Number(t);
  }
  function h(tag, cls, testo) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (testo !== undefined && testo !== null) e.textContent = testo;
    return e;
  }
  const $ = (s) => document.querySelector(s);
  const titolo = "Free cooling e recupero";
  const NOMI_REGIME = {
    totale: "Free cooling totale", parziale: "Free cooling parziale", entalpico: "Free cooling entalpico (aria calda ma secca)",
    estivo: "Recupero estivo (freddo)", invernale: "Recupero invernale (caldo)", brina: "Rischio brina", nessuno: "Nessuno dei due",
  };
  const COLORI_REGIME = { totale: "#2ca25f", parziale: "#8fd16a", entalpico: "#e0a100", estivo: "estate", invernale: "inverno", brina: "#8e6bd8", nessuno: "#9a9a9a" };
  const ORDINE_REGIMI = ["totale", "parziale", "entalpico", "estivo", "invernale", "brina", "nessuno"];
  const MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"];

  let S = null;
  const D = window.EUGENIO_DIAGRAMMA_ARIA.crea(document.getElementById("diagramma-aria"), {
    titolo,
    nomeFile: () => "eugenio-aria-freecooling",
    avviso: () => (S && S.serie() && S.serie().sintetica ? "Dati sintetici di prova, non reali." : ""),
    fonti: () => {
      const s = S && S.serie();
      if (!s) return [];
      const o = st.opz, g = gruppoDiagramma();
      return [`Serie oraria: ${s.comune || ""}, ${s.fonte}${s.licenza && s.licenza !== "—" ? ` (${s.licenza})` : ""}.`,
        g ? `Ore: ${g.nome}. Ambiente estate ${fmt(o.estate.t, 1)} °C/${fmt(o.estate.ur)} %, inverno ${fmt(o.inverno.t, 1)} °C/${fmt(o.inverno.ur)} %; mandata ${fmt(o.tMandata, 1)} °C; T di bilancio ${fmtT(o.tBilancio)} °C; economizzatore ${o.economizzatore}; εs ${fmt(o.epsS, 2)}, εl ${fmt(o.epsL, 2)}. Stima del potenziale, non simulazione dell'edificio.` : "",
].filter(Boolean);
    },
  });
  S = window.EUGENIO_SCELTA_ARIA.crea({ mappa: "#mappa", passo: "#scelta-aria" });
  S.su((d) => D.titolo(d.serie ? `${titolo} – ${d.comune}` : titolo));

  // gruppi di ore: G1 ore d'ufficio tutto l'anno, G2 tutte le ore; G3 e G4 nascosti (estate e inverno in ufficio)
  const UFFICIO = { oraDa: 8, oraA: 18, giorni: "feriali", anni: 10 };
  const G = window.EUGENIO_GRUPPI_ORE.crea(document.getElementById("aria-gruppi"), {
    iniziali: [
      { nome: "Ore d'ufficio, tutto l'anno", da: "01/01", a: "31/12", ...UFFICIO, mostra: true },
      { nome: "Tutto il giorno, tutto l'anno", da: "01/01", a: "31/12", oraDa: 0, oraA: 24, giorni: "tutti", anni: 10, mostra: true },
      { nome: "Estate, ore d'ufficio", da: "01/06", a: "30/09", ...UFFICIO, mostra: false },
      { nome: "Inverno, ore d'ufficio", da: "01/11", a: "31/03", ...UFFICIO, mostra: false },
    ],
  });

  const st = { opz: opzioni({}, 101325), R: null, riassunti: [], diagrammaId: null, xMaxToccato: false, attesa: 0, progettoToccato: false };

  // ------------------------------------------------------------------ passo 2: dati dell'UTA, free cooling, recuperatore
  const box = document.getElementById("aria-pagina");
  box.innerHTML = "";
  const campi = {};
  function campoNumero(chiave, etichetta, valore, { min, max, dec = 1, aiuto, unita } = {}) {
    const l = h("label", "aria-campo aria-fc-campo");
    const sp = h("span", null, unita ? `${etichetta} [${unita}]` : etichetta);
    const inp = document.createElement("input");
    inp.type = "text"; inp.inputMode = "decimal"; inp.id = `fc-${chiave}`; inp.autocomplete = "off";
    inp.value = fmt(valore, dec).replace(/\./g, "");
    if (aiuto) inp.title = aiuto;
    inp.dataset.min = min; inp.dataset.max = max;
    inp.addEventListener("input", () => {
      const v = leggiNum(inp.value);
      const ok = Number.isFinite(v) && v >= min && v <= max;
      inp.setAttribute("aria-invalid", ok ? "false" : "true");
      if (ok) { if (chiave === "xMax") st.xMaxToccato = true; programma(); }
    });
    l.append(sp, inp);
    campi[chiave] = { inp, dec, min, max, valore: () => { const v = leggiNum(inp.value); return Number.isFinite(v) && v >= min && v <= max ? v : null; },
      imposta: (v) => { inp.value = fmt(v, dec).replace(/\./g, ""); inp.setAttribute("aria-invalid", "false"); } };
    return l;
  }
  function campoScelta(chiave, etichetta, opzioniSel, valore) {
    const l = h("label", "aria-campo aria-fc-campo");
    l.appendChild(h("span", null, etichetta));
    const sel = h("select"); sel.id = `fc-${chiave}`;
    opzioniSel.forEach(([v, t]) => { const o = h("option", null, t); o.value = String(v); sel.appendChild(o); });
    sel.value = String(valore);
    sel.addEventListener("change", () => programma());
    l.appendChild(sel);
    campi[chiave] = { inp: sel, valore: () => sel.value, imposta: (v) => { sel.value = String(v); } };
    return l;
  }
  function gruppoCampi(titoloGruppo, figli, nota) {
    const fs = h("fieldset", "aria-fc-blocco");
    fs.appendChild(h("legend", null, titoloGruppo));
    const r = h("div", "aria-campi");
    figli.forEach((f) => r.appendChild(f));
    fs.appendChild(r);
    if (nota) fs.appendChild(Object.assign(h("p", "aiuto aria-fc-nota"), { innerHTML: nota }));
    return fs;
  }
  const d0 = PREDEFINITI;
  box.append(
    h("h3", "aria-fc-titolo", "UTA e ambiente"),
    gruppoCampi("Portata e aria esterna", [
      campoNumero("V", "Portata di mandata", d0.V, { min: 100, max: 1e6, dec: 0, unita: "m³/h" }),
      campoScelta("riferimento", "La portata in volume è riferita a", P.RIF_PORTATA.map((t, i) => [i, t]), d0.riferimento),
      campoNumero("quotaMinima", "Aria esterna minima", d0.quotaMinima, { min: 0, max: 100, dec: 0, unita: "%" }),
    ], "La portata in massa è ṁ = V/(3600·v) con v dello stato scelto, come nel foglio e nella pagina Trasformazioni (aria esterna = quella di ogni ora). " +
      "L'aria esterna minima è la quota che l'UTA prende sempre (ricambi igienici): passa nel recuperatore. Con 100 % l'UTA è a tutt'aria esterna: il free cooling c'è già e il risparmio esce zero."),
    gruppoCampi("Ambiente (aria di ripresa ed espulsione)", [
      campoNumero("estateT", "Estate T", d0.estate.t, { min: 10, max: 40, dec: 1, unita: "°C" }),
      campoNumero("estateUR", "UR", d0.estate.ur, { min: 1, max: 100, dec: 0, unita: "%" }),
      campoNumero("invernoT", "Inverno T", d0.inverno.t, { min: 5, max: 35, dec: 1, unita: "°C" }),
      campoNumero("invernoUR", "UR", d0.inverno.ur, { min: 1, max: 100, dec: 0, unita: "%" }),
      campoNumero("tBilancio", "T di bilancio", d0.tBilancio, { min: -30, max: 40, dec: 1, unita: "°C" }),
    ], "Stessi valori predefiniti della pagina Carichi latenti. <b>T di bilancio</b>: sopra questa temperatura esterna l'edificio chiede freddo " +
      "(free cooling e recupero estivo), sotto chiede caldo (recupero invernale). 12 °C va bene per uffici con molti apporti interni; per le zone " +
      "interne che chiedono freddo tutto l'anno abbassala."),
    h("h3", "aria-fc-titolo", "Free cooling"),
    gruppoCampi("Economizzatore", [
      campoScelta("economizzatore", "Tipo", [["entalpico", "entalpico (h esterna < h ripresa)"], ["temperatura", "a temperatura (T esterna < T ripresa)"]], d0.economizzatore),
      campoNumero("tMandata", "T di mandata richiesta", d0.tMandata, { min: 0, max: 35, dec: 1, unita: "°C" }),
      campoNumero("xMax", "x massima dell'aria esterna", 1000 * P.xDaUR(26, 60, 101325), { min: 1, max: 30, dec: 1, unita: "g/kg" }),
    ], "Mandata a 16 °C: 10 K sotto l'ambiente estivo di 26 °C, il salto di solito accettato per il comfort (lo stesso limite della verifica " +
      "nella pagina Trasformazioni). La x massima (predefinita: x a 26 °C e 60 %) vale solo per l'economizzatore entalpico: sopra non si fa " +
      "entrare aria troppo umida. Le tabelle danno sempre tutti e due i tipi; il tipo scelto decide i colori del diagramma e il recupero estivo."),
    h("h3", "aria-fc-titolo", "Recuperatore di calore"),
    gruppoCampi("Recuperatore tra espulsione e aria esterna", [
      campoScelta("tipoRec", "Tipo", [["sensibile", "sensibile (piastre)"], ["entalpico", "entalpico (ruota)"]], "sensibile"),
      campoNumero("epsS", "εs sensibile", d0.epsS, { min: 0, max: 1, dec: 2 }),
      campoNumero("epsL", "εl latente", d0.epsL, { min: 0, max: 1, dec: 2 }),
      campoScelta("regolaBrina", "Regola della brina", [["rugiada", "espulsione sotto 0 °C e sotto la rugiada"], ["soglia", "T esterna sotto una soglia (piastre)"]], d0.regolaBrina),
      campoNumero("tSoglia", "Soglia", d0.tSoglia, { min: -40, max: 20, dec: 1, unita: "°C" }),
      campoScelta("sbrinamento", "Nelle ore a rischio brina", [["si", "by-pass parziale (sbrinamento)"], ["no", "nessuna azione (si contano solo le ore)"]], "si"),
      campoNumero("dP", "Perdita di carico per lato", d0.dP, { min: 0, max: 5000, dec: 0, unita: "Pa" }),
      campoNumero("etaV", "Rendimento del ventilatore", d0.etaV, { min: 0.05, max: 1, dec: 2 }),
    ], "Uscita dell'aria esterna: T = T<sub>e</sub> + εs·(T<sub>amb</sub> − T<sub>e</sub>), x = x<sub>e</sub> + εl·(x<sub>amb</sub> − x<sub>e</sub>) (la funzione «Recuperatore di calore» del foglio, portate bilanciate). " +
      "Scegliendo «entalpico» εl diventa 0,6 (si può cambiare). Il by-pass nelle ore a rischio brina riduce lo scambio quanto basta perché l'espulsione " +
      "non scenda sotto 0 °C (o, con la soglia, perché il recuperatore non scambi più che alla soglia). I ventilatori pagano la perdita di carico " +
      "sui due flussi solo nelle ore in cui il recuperatore recupera: nelle altre si suppone una serranda di by-pass."),
  );
  const selDiagramma = h("select"); selDiagramma.id = "fc-gruppo-diagramma";
  const lDiag = h("label", "aria-campo aria-fc-campo");
  lDiag.append(h("span", null, "Gruppo nel diagramma e nella tabella mensile"), selDiagramma);
  const ripristina = h("button", "bottone secondario piccolo", "Valori predefiniti");
  ripristina.type = "button";
  const rigaDiag = h("div", "aria-campi aria-fc-diagramma");
  rigaDiag.append(lDiag, ripristina);
  box.appendChild(rigaDiag);
  const campoSoglia = campi.tSoglia.inp.closest("label");

  campi.tipoRec.inp.addEventListener("change", () => {
    const ent = campi.tipoRec.inp.value === "entalpico";
    campi.epsL.imposta(ent ? EPS_L_ENTALPICO : 0);
  });
  selDiagramma.addEventListener("change", () => { st.diagrammaId = selDiagramma.value; mostraTutto(); });
  ripristina.addEventListener("click", () => {
    const p = S.serie() ? S.serie().p : 101325;
    campi.V.imposta(d0.V); campi.riferimento.imposta(d0.riferimento); campi.quotaMinima.imposta(d0.quotaMinima);
    campi.estateT.imposta(d0.estate.t); campi.estateUR.imposta(d0.estate.ur); campi.invernoT.imposta(d0.inverno.t); campi.invernoUR.imposta(d0.inverno.ur);
    campi.tBilancio.imposta(d0.tBilancio); campi.economizzatore.imposta(d0.economizzatore); campi.tMandata.imposta(d0.tMandata);
    st.xMaxToccato = false; campi.xMax.imposta(1000 * P.xDaUR(26, 60, p));
    campi.tipoRec.imposta("sensibile"); campi.epsS.imposta(d0.epsS); campi.epsL.imposta(d0.epsL); campi.regolaBrina.imposta(d0.regolaBrina);
    campi.tSoglia.imposta(d0.tSoglia); campi.sbrinamento.imposta("si"); campi.dP.imposta(d0.dP); campi.etaV.imposta(d0.etaV);
    programma();
  });

  function leggiOpzioni() {
    const v = (k) => campi[k].valore();
    const p = S.serie() ? S.serie().p : 101325;
    // x massima: finché l'utente non tocca il campo vale x(26 °C, 60 %) esatta alla pressione del comune (il campo la
    // mostra arrotondata a 0,1 g/kg; 14/11/2026, verifica indipendente: con 12,8 invece di 12,82 cambiavano le ore)
    const xm = st.xMaxToccato ? v("xMax") : null;
    return opzioni({
      V: v("V"), riferimento: Number(v("riferimento")), quotaMinima: v("quotaMinima"),
      estate: { t: v("estateT"), ur: v("estateUR") }, inverno: { t: v("invernoT"), ur: v("invernoUR") },
      tBilancio: v("tBilancio"), economizzatore: v("economizzatore"), tMandata: v("tMandata"), xMax: xm === null ? null : xm / 1000,
      epsS: v("epsS"), epsL: v("epsL"), regolaBrina: v("regolaBrina"), tSoglia: v("tSoglia"), sbrinamento: v("sbrinamento") === "si",
      dP: v("dP"), etaV: v("etaV"),
    }, p);
  }

  // ------------------------------------------------------------------ passo 3 e 4: contenitori
  const risultati = document.getElementById("aria-risultati");
  const passoRis = document.getElementById("passo-risultati");
  const passoProg = document.getElementById("passo-progetto");
  const vuoto = h("p", "aiuto aria-fc-vuoto", "Scegli un comune al passo 1: i risultati compaiono qui.");
  box.appendChild(vuoto);

  // ------------------------------------------------------------------ calcolo
  function programma() { clearTimeout(st.attesa); st.attesa = setTimeout(ricalcola, 150); }
  function ricalcola() {
    clearTimeout(st.attesa);
    const s = S.serie();
    st.opz = leggiOpzioni();
    campoSoglia.hidden = st.opz.regolaBrina !== "soglia";
    if (!s) { st.R = null; mostraTutto(); return; }
    const V = P.vettori(s.t, s.ur, s.p);
    st.R = calcola(s.t, V.x, V.h, s.p, st.opz);
    mostraTutto();
  }
  function anniGruppo(g, s) {
    const tot = window.EUGENIO_GRUPPI_ORE.anniSerie(s);
    return g.anni ? Math.min(g.anni, tot) : tot;
  }
  function gruppoDiagramma() {
    const vis = G.gruppi().filter((g) => g.mostra);
    return vis.find((g) => g.id === st.diagrammaId) || vis[0] || null;
  }
  function aggiornaSceltaDiagramma() {
    const vis = G.gruppi().filter((g) => g.mostra);
    const g = gruppoDiagramma();
    selDiagramma.innerHTML = "";
    vis.forEach((x) => { const o = h("option", null, x.nome); o.value = x.id; selDiagramma.appendChild(o); });
    if (g) selDiagramma.value = g.id;
    selDiagramma.disabled = !vis.length;
  }

  function mostraTutto() {
    const s = S.serie(), R = st.R;
    aggiornaSceltaDiagramma();
    vuoto.hidden = !!s;
    passoRis.hidden = !s || !R;
    passoProg.hidden = !s;
    if (!s || !R) { st.riassunti = []; disegna(); progetto(false); return; }
    const C = window.EUGENIO_GRUPPI_ORE.campiOrari(s);
    const gd = gruppoDiagramma();
    st.riassunti = G.gruppi().filter((g) => g.mostra).map((g) => ({ g, r: riassumi(R, g.indici, anniGruppo(g, s), g === gd || (gd && g.id === gd.id) ? C.mese : null) }));
    tabelle();
    progetto(false);
    disegna();
  }

  // ------------------------------------------------------------------ diagramma
  // strati della pagina: stessi nomi a ogni ricalcolo (così restano le scelte «mostra» della legenda); si tolgono quelli
  // che non servono più
  let usati = new Set();
  function disegna() {
    const s = S.serie(), R = st.R, o = st.opz;
    usati = new Set();
    const nuvola = (nome, ...a) => { usati.add(nome); D.nuvola(nome, ...a); };
    const spezzata = (nome, ...a) => { usati.add(nome); D.spezzata(nome, ...a); };
    const punto = (nome, ...a) => { usati.add(nome); D.punto(nome, ...a); };
    const pulisci = () => D.strati().forEach((x) => { if (/^(reg-|fc-)/.test(x.nome) && !usati.has(x.nome)) D.togli(x.nome); });
    if (!s || !R) { pulisci(); return; }
    D.pressione(s.p);
    const g = gruppoDiagramma();
    const V = P.vettori(s.t, s.ur, s.p);
    if (g) {
      const conta = new Uint32Array(REGIMI.length);
      for (let k = 0; k < g.indici.length; k++) { const r = R.regime[g.indici[k]]; if (r !== SENZA_DATI) conta[r]++; }
      const liste = REGIMI.map((_, r) => new Uint32Array(conta[r]));
      const pos = new Uint32Array(REGIMI.length);
      for (let k = 0; k < g.indici.length; k++) { const i = g.indici[k], r = R.regime[i]; if (r !== SENZA_DATI) liste[r][pos[r]++] = i; }
      const anni = anniGruppo(g, s);
      // la legenda (regimi con le ore l'anno, tratteggi) va nelle immagini scaricate dal modulo del diagramma
      ORDINE_REGIMI.forEach((nome) => {
        const r = REGIMI.indexOf(nome);
        if (nome === "entalpico" && o.economizzatore !== "entalpico") return;
        nuvola(`reg-${nome}`, COLORI_REGIME[nome], { t: s.t, x: V.x, indici: liste[r] },
          { etichetta: NOMI_REGIME[nome], nota: `(${fmt(conta[r] / anni)} ore l'anno)` });
      });
    }
    const p = s.p, E = o.estate, I = o.inverno;
    const tS = o.tMandata, tB = o.tBilancio;
    spezzata("fc-mandata", [{ t: tS, x: 0 }, { t: tS, x: P.xSat(tS, p) }], { colore: "estate", spessore: 1.6, tratteggio: [7, 4], marcatori: false, etichetta: `T di mandata ${fmt(tS, 1)} °C` });
    if (tB > -10 && tB < 50) spezzata("fc-bilancio", [{ t: tB, x: 0 }, { t: tB, x: P.xSat(tB, p) }], { colore: "#8a8a8a", spessore: 1.4, tratteggio: [2, 3], marcatori: false, etichetta: `T di bilancio ${fmtT(tB)} °C` });
    const xrE = P.xDaUR(E.t, E.ur, p), hr = P.entalpia(E.t, xrE);
    const t0 = P.tSatDaH(hr, p), t1 = hr / P.CPA, iso = [];
    for (let k = 0; k <= 16; k++) { const t = t0 + (t1 - t0) * k / 16; iso.push({ t, x: Math.max(0, P.xDaHT(hr, t)) }); }
    spezzata("fc-hripresa", iso, { colore: "#17a2b8", spessore: 1.6, tratteggio: [6, 3], marcatori: false, etichetta: `h di ripresa ${fmt(hr, 1)} kJ/kg` });
    if (o.economizzatore === "entalpico") spezzata("fc-xmax", [{ t: Math.max(-10, P.tRugiada(o.xMax, p)), x: o.xMax }, { t: 50, x: o.xMax }], { colore: "var(--serie-4)", spessore: 1.6, tratteggio: [3, 3], marcatori: false, etichetta: `x massima ${fmt(o.xMax * 1000, 1)} g/kg` });
    punto("fc-amb-estate", { t: E.t, ur: E.ur }, { colore: "estate", simbolo: "quadrato", etichetta: "A estate", posizione: "r", legenda: false });
    punto("fc-amb-inverno", { t: I.t, ur: I.ur }, { colore: "inverno", simbolo: "quadrato", etichetta: "A inverno", posizione: "l", legenda: false });
    const pr = st.progetto;
    if (pr) {
      punto("fc-prog-inverno", { t: pr.inverno.t, ur: pr.inverno.ur }, { colore: "inverno", simbolo: "rombo", etichetta: "Progetto inverno", posizione: "r", legenda: false });
      punto("fc-prog-estate", { t: pr.estate.t, ur: pr.estate.ur }, { colore: "estate", simbolo: "rombo", etichetta: "Progetto estate", posizione: "l", legenda: false });
    }
    pulisci();
  }

  // ------------------------------------------------------------------ tabelle dei risultati
  const RIGHE = [
    ["Ore del gruppo", "ore/anno", (r) => fmt(r.ore / r.anni)],
    ["Ore con richiesta di freddo (T > T di bilancio)", "ore/anno", (r) => fmt(r.oreRaffrescamento)],
    ...ORDINE_REGIMI.map((n) => [`· ${NOMI_REGIME[n]}`, "ore/anno", (r) => fmt(r.oreRegime[REGIMI.indexOf(n)])]),
    ["Ore di free cooling, economizzatore a temperatura", "ore/anno", (r) => fmt(r.oreFcT)],
    ["Ore di free cooling, economizzatore entalpico", "ore/anno", (r) => fmt(r.oreFcH)],
    ["Freddo evitato, economizzatore a temperatura", "kWh/anno", (r) => kwh(r.kwhFcT)],
    ["Freddo evitato, economizzatore entalpico", "kWh/anno", (r) => kwh(r.kwhFcH)],
    ["Picco del freddo evitato (tipo scelto)", "kW", (r, o) => kw(o.economizzatore === "entalpico" ? r.piccoFcH : r.piccoFcT)],
    ["Calore recuperato in inverno", "kWh/anno", (r) => kwh(r.kwhInverno)],
    ["Picco del calore recuperato", "kW", (r) => kw(r.piccoInverno)],
    ["Freddo recuperato in estate", "kWh/anno", (r) => kwh(r.kwhEstate)],
    ["Picco del freddo recuperato", "kW", (r) => kw(r.piccoEstate)],
    ["Ore a rischio brina", "ore/anno", (r) => fmt(r.oreBrina)],
    ["Recupero perso per lo sbrinamento", "kWh/anno", (r) => kwh(r.kwhPerso)],
    ["Elettricità in più dei ventilatori", "kWh/anno", (r) => kwh(r.kwhElettrici)],
    ["Recuperato / elettricità in più", "kWh termici per kWh elettrico", (r) => (Number.isFinite(r.rapporto) ? fmt(r.rapporto, 1) : "—")],
  ];
  const COLONNE_MESE = [
    ["oreFc", "Ore di free cooling", "ore", (v) => fmt(v)],
    ["kwhFc", "Freddo evitato", "kWh", kwh],
    ["kwhInverno", "Calore recuperato", "kWh", kwh],
    ["kwhEstate", "Freddo recuperato", "kWh", kwh],
    ["oreBrina", "Ore a rischio brina", "ore", (v) => fmt(v)],
    ["kwhPerso", "Perso per lo sbrinamento", "kWh", kwh],
    ["kwhElettrici", "Elettricità ventilatori", "kWh", kwh],
  ];
  function cifra(valore, unita, etichetta, nota) {
    const d = h("div", "cifra");
    const b = h("b", null, valore);
    if (unita) b.appendChild(h("small", null, ` ${unita}`));
    d.append(b, h("span", null, etichetta));
    if (nota) d.appendChild(h("small", null, nota));
    return d;
  }
  function tabelle() {
    const o = st.opz, s = S.serie();
    risultati.innerHTML = "";
    const gd = gruppoDiagramma(), rd = st.riassunti.find((x) => gd && x.g.id === gd.id);
    if (!rd) { risultati.appendChild(h("p", "aiuto", "Nessun gruppo da mostrare: accendi «Mostra» in almeno un gruppo.")); return; }
    const r = rd.r, nomeEc = o.economizzatore === "entalpico" ? "entalpico" : "a temperatura";
    risultati.appendChild(h("p", "aiuto", `Anno medio di «${rd.g.nome}» (${fmt(r.anni, r.anni < 2 ? 1 : 0)} anni di serie, ${fmt(r.ore)} ore). Stima del potenziale, non simulazione dell'edificio.`));
    const cifre = h("div", "cifre aria-fc-cifre");
    cifre.append(
      cifra(fmt(o.economizzatore === "entalpico" ? r.oreFcH : r.oreFcT), "ore", "di free cooling l'anno", `economizzatore ${nomeEc}; ${fmt(r.oreRegime[1])} ore di free cooling totale (T esterna ≤ T di mandata)`),
      cifra(kwh(r.kwhFc), "kWh", "di freddo evitato l'anno", `rispetto all'aria esterna minima (${fmt(o.quotaMinima)} %)`),
      cifra(kwh(r.kwhInverno), "kWh", "di calore recuperato l'anno", `picco ${kw(r.piccoInverno)} kW`),
      cifra(kwh(r.kwhEstate), "kWh", "di freddo recuperato l'anno", `picco ${kw(r.piccoEstate)} kW`),
      cifra(fmt(r.oreBrina), "ore", "a rischio brina l'anno", o.sbrinamento ? `${kwh(r.kwhPerso)} kWh persi con il by-pass` : "senza sbrinamento"),
      cifra(kwh(r.kwhElettrici), "kWh el.", "in più ai ventilatori", Number.isFinite(r.rapporto) ? `${fmt(r.rapporto, 1)} kWh recuperati per kWh elettrico` : "nessuna ora di recupero"),
    );
    risultati.appendChild(cifre);
    if (r.kwhFcT < 0 || st.riassunti.some((x) => x.r.kwhFcT < 0)) {
      risultati.appendChild(h("p", "messaggio attenzione", "Con l'economizzatore a temperatura il freddo evitato esce negativo in alcuni gruppi: nelle ore umide l'aria esterna più fresca dell'ambiente ha più entalpia della ripresa, e farla entrare costa più freddo. È il motivo per cui si usa l'economizzatore entalpico."));
    }
    // per gruppo
    risultati.appendChild(h("h3", null, "Per gruppo di ore (anno medio)"));
    const sc = h("div", "tabella-scorre");
    const tb = h("table", "mensili aria-fc-tabella");
    tb.id = "fc-tabella-gruppi";
    const th = h("thead"), tr = h("tr");
    tr.appendChild(h("th", null, "Voce"));
    st.riassunti.forEach(({ g }) => {
      const c = h("th", "num");
      const camp = h("span", "aria-campione aria-fc-campione"); camp.style.background = g.colore; camp.setAttribute("aria-hidden", "true");
      c.append(camp, g.nome);
      tr.appendChild(c);
    });
    th.appendChild(tr); tb.appendChild(th);
    const tbo = h("tbody");
    RIGHE.forEach(([nome, unita, f]) => {
      const riga = h("tr");
      const t0 = h("th", null, nome); t0.appendChild(h("small", null, unita));
      riga.appendChild(t0);
      st.riassunti.forEach(({ r: rr }) => riga.appendChild(h("td", "num", f(rr, o))));
      tbo.appendChild(riga);
    });
    tb.appendChild(tbo); sc.appendChild(tb); risultati.appendChild(sc);
    // mensile
    risultati.appendChild(h("h3", null, `Mese per mese: «${rd.g.nome}», anno medio`));
    const sc2 = h("div", "tabella-scorre");
    const tm = h("table", "mensili aria-fc-tabella");
    tm.id = "fc-tabella-mesi";
    const th2 = h("thead"), tr2 = h("tr");
    tr2.appendChild(h("th", null, "Mese"));
    COLONNE_MESE.forEach(([, n, u]) => { const c = h("th", "num", n); c.appendChild(h("small", null, u)); tr2.appendChild(c); });
    th2.appendChild(tr2); tm.appendChild(th2);
    const tb2 = h("tbody");
    for (let m = 0; m < 12; m++) {
      const riga = h("tr");
      riga.appendChild(h("th", null, MESI[m]));
      COLONNE_MESE.forEach(([k, , , f]) => riga.appendChild(h("td", "num", f(r.mensile[k][m]))));
      tb2.appendChild(riga);
    }
    const tot = h("tr", "evidenziata");
    tot.appendChild(h("th", null, "anno"));
    COLONNE_MESE.forEach(([k, , , f]) => tot.appendChild(h("td", "num", f(r.mensile[k].reduce((a, b) => a + b, 0)))));
    tb2.appendChild(tot);
    tm.appendChild(tb2); sc2.appendChild(tm); risultati.appendChild(sc2);
    // scaricamenti
    const sca = h("div", "scarica");
    [["csv-gruppi", "Risultati per gruppo (CSV)", csvGruppi], ["csv-mesi", "Mese per mese (CSV)", csvMesi], ["csv-ore", "Ore del gruppo nel diagramma (CSV)", csvOre]]
      .forEach(([id, t, f]) => { const b = h("button", "bottone secondario", t); b.type = "button"; b.id = `fc-${id}`; b.addEventListener("click", f); sca.appendChild(b); });
    risultati.appendChild(sca);
    risultati.appendChild(metodo());
    risultati.appendChild(h("p", "fonti", `Serie: ${s.comune}, ${s.fonte}${s.licenza && s.licenza !== "—" ? ` (${s.licenza})` : ""}. Formule dell'aria umida: psicro.js (ASHRAE 2017, come il foglio psicro_UTA.xlsx).`));
  }
  function metodo() {
    const d = h("details", "aria-fc-metodo");
    d.appendChild(h("summary", null, "Come è fatto il calcolo"));
    const testi = [
      "Per ogni ora del gruppo con T e UR: <b>modo</b> raffrescamento se T<sub>e</sub> &gt; T di bilancio, altrimenti riscaldamento. Portata in massa ṁ = V/(3600·v); aria esterna minima ṁ<sub>OA</sub> = f<sub>min</sub>·ṁ.",
      "<b>Free cooling</b> (modo raffrescamento, ripresa = ambiente estivo R). La batteria fredda porta l'aria alla T di mandata T<sub>m</sub> (se l'aria è troppo umida condensa fino a UR 100 %): h<sub>m</sub> = h(T<sub>m</sub>, min(x, x<sub>sat</sub>(T<sub>m</sub>))). Senza economizzatore entra la miscela con l'aria esterna minima: Q<sub>0</sub> = ṁ·max(0, h<sub>mix</sub> − h<sub>m</sub>). Con l'economizzatore: se T<sub>e</sub> ≤ T<sub>m</sub> si miscela fino a T<sub>m</sub> e la batteria è spenta (<b>totale</b>); se l'economizzatore è attivo (T<sub>e</sub> &lt; T<sub>R</sub> a temperatura, h<sub>e</sub> &lt; h<sub>R</sub> e x<sub>e</sub> ≤ x<sub>max</sub> entalpico) entra solo aria esterna e Q = ṁ·max(0, h<sub>e</sub> − h<sub>m</sub>) (<b>parziale</b>; per l'entalpico con T<sub>e</sub> ≥ T<sub>R</sub> è il regime <b>entalpico</b>); altrimenti si resta all'aria esterna minima. Freddo evitato = Q<sub>0</sub> − Q.",
      "<b>Recuperatore</b>: uscita dell'aria esterna T = T<sub>e</sub> + εs·(T<sub>R</sub> − T<sub>e</sub>), x = x<sub>e</sub> + εl·(x<sub>R</sub> − x<sub>e</sub>). In inverno (riscaldamento, T<sub>e</sub> &lt; T<sub>R</sub>) recupera ṁ<sub>OA</sub>·(h<sub>uscita</sub> − h<sub>e</sub>). In estate recupera freddo ṁ<sub>OA</sub>·(h<sub>e</sub> − h<sub>uscita</sub>) solo quando l'economizzatore scelto è spento (aria esterna peggiore della ripresa): quando l'aria esterna è più fresca conviene il free cooling e il recuperatore va in by-pass.",
      "<b>Brina</b>: espulsione in uscita T<sub>x</sub> = T<sub>R</sub> − εs·(T<sub>R</sub> − T<sub>e</sub>), x<sub>x</sub> = x<sub>R</sub> − εl·(x<sub>R</sub> − x<sub>e</sub>); rischio se T<sub>x</sub> &lt; 0 °C e sotto la sua rugiada (oppure, regola semplice per le piastre, T<sub>e</sub> sotto la soglia, predefinita −5 °C). Con lo sbrinamento a by-pass lo scambio scende a ε<sub>eff</sub> = (T<sub>R</sub> − T<sub>lim</sub>)/(T<sub>R</sub> − T<sub>e</sub>), con T<sub>lim</sub> = 0 °C (o T<sub>R</sub> − εs·(T<sub>R</sub> − soglia)); la differenza è il recupero perso.",
      "<b>Ventilatori</b>: nelle ore di recupero P<sub>el</sub> = 2·(f<sub>min</sub>·V/3600)·ΔP/η. Il confronto è tra kWh termici recuperati e kWh elettrici in più: per passare all'energia primaria servono il rendimento del generatore e i fattori di conversione, che qui non si mettono.",
      "Tutto è per anno medio: somme sulle ore del gruppo divise per gli anni di serie che il gruppo usa. Non ci sono apporti solari, inerzia dell'edificio, umidità prodotta in ambiente, regolazioni reali: è il potenziale del clima del comune per un'UTA con queste scelte.",
    ];
    testi.forEach((t) => { const p = h("p"); p.innerHTML = t; d.appendChild(p); });
    return d;
  }

  // ------------------------------------------------------------------ passo 4: potenza alle condizioni di progetto
  const boxProg = document.getElementById("aria-progetto");
  const L = window.EUGENIO_SCELTA_ARIA.livelloProgetto("#aria-livello");
  const campiProg = {};
  (function costruisciProgetto() {
    boxProg.innerHTML = "";
    const r = h("div", "aria-campi");
    [["invT", "Inverno T", "°C", -40, 30, 1], ["invUR", "UR", "%", 1, 100, 0], ["estT", "Estate T", "°C", 10, 50, 1], ["estUR", "UR", "%", 1, 100, 0]].forEach(([k, et, u, mn, mx, dec]) => {
      const l = h("label", "aria-campo aria-fc-campo");
      const inp = document.createElement("input");
      inp.type = "text"; inp.inputMode = "decimal"; inp.id = `fc-prog-${k}`; inp.autocomplete = "off";
      inp.addEventListener("input", () => {
        const v = leggiNum(inp.value), ok = Number.isFinite(v) && v >= mn && v <= mx;
        inp.setAttribute("aria-invalid", ok ? "false" : "true");
        if (ok) { st.progettoToccato = true; progetto(true); }
      });
      l.append(h("span", null, `${et} [${u}]`), inp);
      r.appendChild(l);
      campiProg[k] = { inp, mn, mx, dec, valore: () => { const v = leggiNum(inp.value); return Number.isFinite(v) && v >= mn && v <= mx ? v : null; } };
    });
    const rip = h("button", "bottone secondario piccolo", "Ripristina dai dati");
    rip.type = "button"; rip.id = "fc-prog-ripristina";
    rip.addEventListener("click", () => { st.progettoToccato = false; progetto(); });
    r.appendChild(rip);
    boxProg.append(r, h("div", "aria-fc-progetto-esito"));
  })();
  L.su(() => { st.progettoToccato = false; progetto(); });
  function progetto(daCampo) {
    const s = S.serie(), esito = boxProg.querySelector(".aria-fc-progetto-esito");
    if (!s) { st.progetto = null; esito.innerHTML = ""; return; }
    if (!st.progettoToccato) {
      const c = P.condizioniProgetto(s.t, s.ur, s.p, L.valori());
      if (!c.inverno) { esito.textContent = c.avviso || ""; return; }
      const imp = (k, v) => { campiProg[k].inp.value = fmt(v, campiProg[k].dec).replace(/\./g, ""); campiProg[k].inp.setAttribute("aria-invalid", "false"); };
      imp("invT", c.inverno.t); imp("invUR", Math.min(100, c.inverno.ur)); imp("estT", c.estate.t); imp("estUR", c.estate.stato.ur);
    }
    const v = (k) => campiProg[k].valore();
    if ([v("invT"), v("invUR"), v("estT"), v("estUR")].some((x) => x === null)) return;
    st.progetto = { inverno: { t: v("invT"), ur: v("invUR") }, estate: { t: v("estT"), ur: v("estUR") } };
    const o = st.opz, a = unOra(st.progetto.inverno.t, st.progetto.inverno.ur, s.p, o), b = unOra(st.progetto.estate.t, st.progetto.estate.ur, s.p, o);
    const modo = (u) => (u.raffrescamento ? "raffrescamento" : "riscaldamento");
    const fc = (u) => (o.economizzatore === "entalpico" ? u.fcH : u.fcT);
    const righe = [
      ["Modo (rispetto alla T di bilancio)", modo(a), modo(b)],
      ["Regime", NOMI_REGIME[a.regime] || a.regime, NOMI_REGIME[b.regime] || b.regime],
      ["Potenza recuperata [kW]", kw(a.rec), kw(b.rec)],
      ["Persa per lo sbrinamento [kW]", kw(a.perso), kw(b.perso)],
      ["Freddo evitato dal free cooling [kW]", kw(fc(a)), kw(fc(b))],
      ["Ventilatori in più [kW el.]", kw(a.rec > 0 ? a.pVent : 0), kw(b.rec > 0 ? b.pVent : 0)],
    ];
    esito.innerHTML = "";
    const sc = h("div", "tabella-scorre"), t = h("table", "mensili aria-fc-tabella");
    t.id = "fc-tabella-progetto";
    const tr = h("tr");
    ["", "Inverno di progetto", "Estate di progetto"].forEach((x, i) => tr.appendChild(h("th", i ? "num" : null, x)));
    const th = h("thead"); th.appendChild(tr); t.appendChild(th);
    const tb = h("tbody");
    righe.forEach(([n, x, y]) => { const r = h("tr"); r.append(h("th", null, n), h("td", "num", x), h("td", "num", y)); tb.appendChild(r); });
    t.appendChild(tb); sc.appendChild(t); esito.appendChild(sc);
    esito.appendChild(h("p", "aiuto", "Valori di partenza: statistiche della serie scelta al livello indicato (non valori di norma). Si possono scrivere a mano; «Ripristina dai dati» li ricalcola."));
    if (daCampo !== false) disegna();
  }

  // ------------------------------------------------------------------ CSV
  const LICENZA = "CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/deed.it)";
  const csvNum = (v, d = 1) => (Number.isFinite(v) ? (Math.round(v * 10 ** d) / 10 ** d).toString().replace(".", ",") : "");
  function scaricaTesto(nome, righe) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob(["﻿" + righe.join("\r\n")], { type: "text/csv;charset=utf-8" }));
    a.download = nome;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }
  function piedeCsv() {
    const s = S.serie(), o = st.opz;
    return ["", `Comune;${s.comune} (${s.istat})`, `Serie;dal ${s.dal} al ${s.al}, ${s.fonte}`, `Pressione (Pa);${csvNum(s.p, 0)}`,
      `Portata (m³/h);${csvNum(o.V, 0)};riferita a: ${P.RIF_PORTATA[o.riferimento]}`, `Aria esterna minima (%);${csvNum(o.quotaMinima, 0)}`,
      `Ambiente estate;${csvNum(o.estate.t)} °C;${csvNum(o.estate.ur, 0)} %`, `Ambiente inverno;${csvNum(o.inverno.t)} °C;${csvNum(o.inverno.ur, 0)} %`,
      `T di bilancio (°C);${csvNum(o.tBilancio)}`, `Economizzatore;${o.economizzatore}`, `T di mandata (°C);${csvNum(o.tMandata)}`, `x massima (g/kg);${csvNum(o.xMax * 1000, 2)}`,
      `εs;${csvNum(o.epsS, 2)}`, `εl;${csvNum(o.epsL, 2)}`, `Regola della brina;${o.regolaBrina === "soglia" ? `T esterna < ${csvNum(o.tSoglia)} °C` : "espulsione < 0 °C e sotto la rugiada"}`,
      `Sbrinamento con by-pass;${o.sbrinamento ? "sì" : "no"}`, `Perdita di carico per lato (Pa);${csvNum(o.dP, 0)}`, `Rendimento ventilatore;${csvNum(o.etaV, 2)}`,
      "Avvertenza;Stima del potenziale con un modello semplice (pagina «Free cooling e recupero», metodo nella pagina), non simulazione dell'edificio. Pagina sperimentale.",
      `Licenza;${LICENZA}`, `Fonte;EuGEnio – eugenio.statocritico.it (dati estratti il ${new Date().toLocaleDateString("it-IT")})`];
  }
  function csvGruppi() {
    const righe = [["voce", "unità", ...st.riassunti.map(({ g }) => g.nome.replace(/;/g, ","))].join(";")];
    const valori = [
      ["ore del gruppo", "ore/anno", (r) => r.ore / r.anni, 0], ["ore con richiesta di freddo", "ore/anno", (r) => r.oreRaffrescamento, 0],
      ...ORDINE_REGIMI.map((n) => [`regime: ${NOMI_REGIME[n]}`, "ore/anno", (r) => r.oreRegime[REGIMI.indexOf(n)], 0]),
      ["ore di free cooling, a temperatura", "ore/anno", (r) => r.oreFcT, 0], ["ore di free cooling, entalpico", "ore/anno", (r) => r.oreFcH, 0],
      ["freddo evitato, a temperatura", "kWh/anno", (r) => r.kwhFcT, 0], ["freddo evitato, entalpico", "kWh/anno", (r) => r.kwhFcH, 0],
      ["picco freddo evitato, a temperatura", "kW", (r) => r.piccoFcT, 1], ["picco freddo evitato, entalpico", "kW", (r) => r.piccoFcH, 1],
      ["calore recuperato in inverno", "kWh/anno", (r) => r.kwhInverno, 0], ["picco calore recuperato", "kW", (r) => r.piccoInverno, 1],
      ["freddo recuperato in estate", "kWh/anno", (r) => r.kwhEstate, 0], ["picco freddo recuperato", "kW", (r) => r.piccoEstate, 1],
      ["ore a rischio brina", "ore/anno", (r) => r.oreBrina, 0], ["recupero perso per lo sbrinamento", "kWh/anno", (r) => r.kwhPerso, 0],
      ["ore di recupero", "ore/anno", (r) => r.oreRecupero, 0], ["elettricità in più dei ventilatori", "kWh/anno", (r) => r.kwhElettrici, 0],
      ["recuperato / elettricità in più", "kWh/kWh", (r) => r.rapporto, 2], ["anni di serie del gruppo", "anni", (r) => r.anni, 2],
    ];
    valori.forEach(([n, u, f, d]) => righe.push([n, u, ...st.riassunti.map(({ r }) => csvNum(f(r), d))].join(";")));
    st.riassunti.forEach(({ g }) => righe.push(`Gruppo «${g.nome.replace(/;/g, ",")}»;dal ${g.da} al ${g.a}, ore ${g.oraDa}–${g.oraA}, giorni ${g.giorni}, anni ${g.anni || "tutta la serie"}`));
    scaricaTesto(`eugenio_freecooling_gruppi_${S.serie().istat}.csv`, righe.concat(piedeCsv()));
  }
  function csvMesi() {
    const gd = gruppoDiagramma(), rd = st.riassunti.find((x) => gd && x.g.id === gd.id);
    if (!rd) return;
    const righe = [`Gruppo;${rd.g.nome.replace(/;/g, ",")} (anno medio)`, ["mese", ...COLONNE_MESE.map(([, n, u]) => `${n} (${u})`)].join(";")];
    for (let m = 0; m < 12; m++) righe.push([MESI[m], ...COLONNE_MESE.map(([k]) => csvNum(rd.r.mensile[k][m], 1))].join(";"));
    scaricaTesto(`eugenio_freecooling_mesi_${S.serie().istat}.csv`, righe.concat(piedeCsv()));
  }
  function csvOre() {
    const gd = gruppoDiagramma(), s = S.serie(), R = st.R;
    if (!gd || !R) return;
    const C = window.EUGENIO_GRUPPI_ORE.campiOrari(s), V = P.vettori(s.t, s.ur, s.p), ent = st.opz.economizzatore === "entalpico";
    const due = (n) => String(n).padStart(2, "0");
    const righe = [`Gruppo;${gd.nome.replace(/;/g, ",")}`, "data;ora locale;T (°C);UR (%);x (g/kg);h (kJ/kg);regime;freddo evitato (kW);recuperato (kW);perso per sbrinamento (kW)"];
    for (const i of gd.indici) {
      const r = R.regime[i];
      if (r === SENZA_DATI) continue;
      righe.push([`${C.anno[i]}-${due(C.mese[i])}-${due(C.giorno[i])}`, `${due(C.ora[i])}:00`, csvNum(s.t[i], 1), csvNum(s.ur[i], 0), csvNum(V.x[i] * 1000, 2), csvNum(V.h[i], 2),
        REGIMI[r], csvNum(ent ? R.fcH[i] : R.fcT[i], 2), csvNum(R.rec[i], 2), csvNum(R.perso[i], 2)].join(";"));
    }
    scaricaTesto(`eugenio_freecooling_ore_${s.istat}.csv`, righe.concat(piedeCsv()));
  }

  // ------------------------------------------------------------------ collegamenti
  G.su(() => mostraTutto());
  S.su((d) => {
    G.serie(d.serie); G.zona(d.zona);
    if (d.serie && !st.xMaxToccato) campi.xMax.imposta(1000 * P.xDaUR(26, 60, d.serie.p));
    st.progettoToccato = false;
    ricalcola();
  });
  campoSoglia.hidden = true;
  window.EUGENIO_ARIA_PAGINA = { diagramma: D, scelta: S, gruppi: G, livello: L, calcolo: API,
    opzioni: () => st.opz, risultati: () => st.riassunti.map(({ g, r }) => ({ id: g.id, nome: g.nome, ...r })), progetto: () => st.progetto,
    ricalcola: () => { ricalcola(); return st.riassunti.map(({ g, r }) => ({ id: g.id, nome: g.nome, ...r })); } };
})(typeof self !== "undefined" ? self : globalThis);
