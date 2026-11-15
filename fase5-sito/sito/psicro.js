"use strict";
// Psicrometria dell'aria umida (14/11/2026), modulo comune delle pagine «Trattamento aria». Funzioni pure, niente DOM:
// si usa nel browser (window.EUGENIO_PSICRO) e in node (require), come edifici_calcoli.js.
//
// Formule = foglio psicro_UTA.xlsx (fase14-trattamento-aria/foglio) = psychrolib 2.5 SI (ASHRAE Fundamentals 2017):
//   p(z) = 101325·(1 − 2,25577e-5·z)^5,2559                      pressione dalla quota [Pa]
//   psat(t) Hyland–Wexler, sul ghiaccio per t ≤ 0,01 °C            [Pa]
//   x = 0,621945·pw/(p − pw)                                       umidità specifica [kg/kg aria secca]
//   h = 1,006·t + x·(2501 + 1,86·t)                                entalpia [kJ/kg aria secca]
//   v = 0,287042·(t + 273,15)·(1 + 1,607858·x)/(p/1000)            volume specifico [m³/kg aria secca]
//   T di rugiada, bulbo umido, ADP: iterazioni (Newton) fino a convergenza (l'Excel ne fa 3-6, stesso risultato)
//   coordinata di Mollier Y = (h − 2501·x)/1,006 = T·(1 + 1,86·x/1,006)
// Unità: t in °C, x in kg/kg (xg = g/kg solo dove scritto), UR in %, h in kJ/kg, potenze in kW, acqua in kg/h, carichi
// della sequenza in W come nel foglio. Il gemello Python è fase14-trattamento-aria/aria/psicro.py (test di parità).
(function (radice) {
  const EPS = 0.621945, RA = 0.287042, K0 = 273.15, R0 = 2501, CPA = 1.006, CPV = 1.86;
  const H_VAPORE = 2676, BF_PRED = 0.1, UR_PRERISC = 90;
  const fin = Number.isFinite;

  // ------------------------------------------------------------------ proprietà di base
  function pressione(z) {
    const q = Math.max(-500, Math.min(8000, Number(z) || 0));
    return 101325 * Math.pow(1 - 2.25577e-5 * q, 5.2559);
  }
  function lnPsat(t) {
    const T = t + K0;
    if (t <= 0.01) return -5674.5359 / T + 6.3925247 - 0.009677843 * T + 0.00000062215701 * T * T
      + 0.0000000020747825 * T * T * T - 9.484024e-13 * T * T * T * T + 4.1635019 * Math.log(T);
    return -5800.2206 / T + 1.3914993 - 0.048640239 * T + 0.000041764768 * T * T - 0.000000014452093 * T * T * T
      + 6.5459673 * Math.log(T);
  }
  function dLnPsat(t) {
    const T = t + K0;
    if (t <= 0.01) return 5674.5359 / (T * T) - 0.009677843 + 2 * 0.00000062215701 * T + 3 * 0.0000000020747825 * T * T
      - 4 * 9.484024e-13 * T * T * T + 4.1635019 / T;
    return 5800.2206 / (T * T) - 0.048640239 + 2 * 0.000041764768 * T - 3 * 0.000000014452093 * T * T + 6.5459673 / T;
  }
  const psat = (t) => Math.exp(lnPsat(t));
  const xDaPw = (pw, p) => EPS * pw / (p - pw);
  const pwDaX = (x, p) => Math.max(p * x / (EPS + x), 0.001);
  const xSat = (t, p) => { const ps = psat(t); return EPS * ps / (p - ps); };
  const xDaUR = (t, ur, p) => { const pw = ur / 100 * psat(t); return EPS * pw / (p - pw); };
  const entalpia = (t, x) => CPA * t + x * (R0 + CPV * t);
  const volume = (t, x, p) => RA * (t + K0) * (1 + 1.607858 * x) / (p / 1000);
  const tDaHX = (h, x) => (h - R0 * x) / (CPA + CPV * x);
  const xDaHT = (h, t) => (h - CPA * t) / (R0 + CPV * t);
  const cpUmido = (x) => CPA + CPV * x;
  // coordinata di Mollier (ordinata del diagramma h–x «alla tedesca», in °C: a x = 0 coincide con T)
  const mollierY = (t, x) => t * (1 + CPV * x / CPA);
  const tDaMollier = (y, x) => y / (1 + CPV * x / CPA);

  // T di rugiada dalla pressione parziale del vapore: Newton su ln psat partendo da Magnus (acqua o ghiaccio)
  function tRugiadaPw(pw) {
    if (!(pw > 0)) return NaN;
    const g = Math.log(pw / 611.2);
    let t = pw >= 611.2 ? 243.12 * g / (17.62 - g) : 272.62 * g / (22.46 - g);
    const lp = Math.log(pw);
    for (let i = 0; i < 50; i++) {
      const d = (lnPsat(t) - lp) / dLnPsat(t);
      t -= d;
      if (Math.abs(d) < 1e-9) break;
    }
    return t;
  }
  const tRugiada = (x, p) => tRugiadaPw(pwDaX(x, p));

  // umidità specifica dall'equazione del bulbo umido ASHRAE (2017, cap. 1, eq. 33 e 35)
  function xBulboUmido(t, tw, p) {
    const ps = psat(tw), ws = EPS * ps / (p - ps);
    return tw >= 0 ? ((2501 - 2.326 * tw) * ws - 1.006 * (t - tw)) / (2501 + 1.86 * t - 4.186 * tw)
      : ((2830 - 0.24 * tw) * ws - 1.006 * (t - tw)) / (2830 + 1.86 * t - 2.1 * tw);
  }
  // T di bulbo umido come psychrolib (GetTWetBulbFromHumRatio): bisezione tra T di rugiada e T con tolleranza 0,001 K,
  // equazione «acqua» se il punto medio è ≥ 0 °C e «ghiaccio» se è sotto. Vicino a 0 °C l'equazione ha un salto e due
  // radici possibili: la bisezione decide quale, come psychrolib (14/11/2026, verifica indipendente). Lontano da 0 °C la
  // radice è unica e basta Newton (più veloce sulle serie lunghe), che dà lo stesso valore entro 0,0005 K.
  function tBulboUmidoPsychrolib(t, x, p) {
    const w = Math.max(x, 1e-7);
    let inf = tRugiada(w, p), sup = t, tw = (inf + sup) / 2;
    for (let i = 0; i < 100 && sup - inf > 0.001; i++) {
      if (xBulboUmido(t, tw, p) > w) sup = tw; else inf = tw;
      tw = (sup + inf) / 2;
    }
    return tw;
  }
  const ZONA_SALTO = 3;                                     // K attorno a 0 °C in cui si usa sempre la bisezione
  function tBulboUmido(t, x, p) {
    if (!fin(t) || !fin(x)) return NaN;
    let tw = t;
    for (let i = 0; i < 40; i++) {
      const a = xBulboUmido(t, tw, p) - x, b = xBulboUmido(t, tw + 0.001, p) - x;
      if (b === a) break;
      const d = a * 0.001 / (b - a);
      tw -= d;
      if (!(tw > -100 && tw <= t + 1e-9)) break;           // fuori campo (aria molto secca): bisezione
      if (Math.abs(d) < 1e-7) return Math.abs(tw) < ZONA_SALTO ? tBulboUmidoPsychrolib(t, x, p) : tw;
    }
    return tBulboUmidoPsychrolib(t, x, p);
  }

  // T sulla curva a UR φ (frazione 0–1) con entalpia h: Newton (foglio: righe s7 della umidificazione adiabatica)
  function tIsoentalpicaUR(h, phi, p, t0) {
    const g = (t) => { const ps = psat(t); return xDaHT(h, t) - EPS * phi * ps / (p - phi * ps); };
    let t = fin(t0) ? t0 : h / 2.5;
    for (let i = 0; i < 60; i++) {
      const a = g(t), b = g(t + 0.001);
      if (b === a) break;
      const d = a * 0.001 / (b - a);
      t -= d;
      if (Math.abs(d) < 1e-9) break;
    }
    return t;
  }
  const tSatDaH = (h, p) => tIsoentalpicaUR(h, 1, p);

  // ADP di una batteria: punto sulla saturazione della retta (in T–x) che passa per ingresso e uscita, oltre l'uscita
  function adpRetta(tIn, xIn, tOut, xOut, p) {
    const dt = tOut - tIn, dx = xOut - xIn;
    const f = (s) => xIn + s * dx - xSat(tIn + s * dt, p);
    if (f(1) >= 0) return null;                    // l'uscita è già satura o oltre: nessun ADP sulla retta
    let lo = 1, hi = 1.5, k = 0;
    while (f(hi) < 0 && k++ < 60) hi = 1 + (hi - 1) * 2;
    if (f(hi) < 0) return null;
    for (let i = 0; i < 100; i++) { const m = (lo + hi) / 2; if (f(m) < 0) lo = m; else hi = m; }
    const s = (lo + hi) / 2;
    return { t: tIn + s * dt, x: xIn + s * dx };
  }
  // ADP dal fattore di bypass (foglio): x_ADP = (x_out − BF·x_in)/(1 − BF), T_ADP = rugiada di x_ADP
  function adpDaBF(xIn, xOut, bf, p) {
    const x = (xOut - bf * xIn) / (1 - bf);
    return { x, t: tRugiada(x, p) };
  }

  // ------------------------------------------------------------------ stato dell'aria
  // statoTX: tutto da T e x (kg/kg), come una riga del «motore degli stati» del foglio
  function statoTX(t, x, p) {
    p = p || 101325;
    t = Math.max(-100, Math.min(200, t));
    const pw = pwDaX(x, p), ps = psat(t), h = entalpia(t, x), v = volume(t, x, p);
    return { t, x, xg: x * 1000, ur: pw / ps * 100, phi: pw / ps, pw, psat: ps, h, v, rho: (1 + x) / v,
      tdew: tRugiadaPw(pw), twb: tBulboUmido(t, x, p), p };
  }
  // stato(t, dato, p): dato = UR % (numero) oppure { ur } | { x } (kg/kg) | { xg } (g/kg) | { twb } | { tdew } | { h }
  function stato(t, dato, p) {
    p = p || 101325;
    let x;
    if (typeof dato === "number") x = xDaUR(t, dato, p);
    else if (dato && fin(dato.ur)) x = xDaUR(t, dato.ur, p);
    else if (dato && fin(dato.x)) x = dato.x;
    else if (dato && fin(dato.xg)) x = dato.xg / 1000;
    else if (dato && fin(dato.twb)) x = xBulboUmido(t, dato.twb, p);
    else if (dato && fin(dato.tdew)) x = xSat(dato.tdew, p);
    else if (dato && fin(dato.h)) x = xDaHT(dato.h, t);
    else throw new Error("stato: serve UR, x, bulbo umido, rugiada o entalpia");
    return statoTX(t, x, p);
  }
  const statoHX = (h, x, p) => statoTX(tDaHX(h, x), x, p);

  // ------------------------------------------------------------------ testi come FIXED(n; d; VERO) del foglio
  function fisso(n, d) {
    if (!fin(n)) return "—";
    const s = (Math.round(Math.abs(n) * Math.pow(10, d) + 1e-9) / Math.pow(10, d)).toFixed(d);
    return (n < 0 && Number(s) !== 0 ? "-" : "") + s.replace(".", ",");
  }

  // ------------------------------------------------------------------ tipi di trasformazione (stessi codici del foglio)
  const TIPI = ["Nessuna", "Miscela con ricircolo", "Recuperatore di calore", "Riscaldamento sensibile", "Raffreddamento sensibile",
    "Raffreddamento con deumidificazione", "Umidificazione adiabatica", "Umidificazione a vapore", "Preriscaldamento",
    "Post-riscaldamento", "Ventilatore"];
  const PARAMETRI = [
    "Riga inattiva: lo stato passa invariato.",
    "P1 = frazione di ricircolo [0–1] o AUTO (= 1 − quota aria esterna)",
    "P1 = εs sensibile [0–1] | P2 = εl latente [0–1] (vuoto = solo sensibile)",
    "P1 = T uscita [°C] | oppure P2 = potenza [kW]",
    "P1 = T uscita [°C] | oppure P2 = potenza frigorifera [kW]",
    "P1 = x uscita [g/kg] o AUTO (= x imm.) | P2 = BF (vuoto = 0,10) | P3 = T ADP [°C] (prevale su P1)",
    "h costante. P1 = x uscita [g/kg] o AUTO | oppure P2 = UR uscita [%] | oppure P3 = efficienza [0–1]",
    "P1 = x uscita [g/kg] o AUTO | oppure P2 = UR uscita [%] | P3 = h vapore [kJ/kg] (vuoto = 2676)",
    "P1 = T uscita [°C] o AUTO (isoentalpica per x imm. a UR = P3) | P2 = potenza [kW] | P3 = UR [%] (vuoto = 90)",
    "P1 = T uscita [°C] o AUTO (= T imm. − ΔT ventilatori a valle) | oppure P2 = potenza [kW]",
    "P1 = ΔT [K] (tip. 0,5–1) | oppure P2 = potenza ceduta all'aria [kW]",
  ];
  const RIF_PORTATA = ["Aria esterna (condizioni di progetto)", "Aria ambiente", "Aria standard 20 °C, 101325 Pa (ρ = 1,204 kg/m³)",
    "Densità fissa ρ = 1,2 kg/m³"];
  // sequenze preimpostate del foglio (tipo, P1, P2, P3) e dati di progetto predefiniti (Te, URe, Ta, URa, Qs W, Ql W)
  const PRESET = {
    estate: [["Miscela con ricircolo", "AUTO", null, null], ["Raffreddamento con deumidificazione", "AUTO", 0.1, null],
      ["Post-riscaldamento", "AUTO", null, null], ["Ventilatore", 0.7, null, null], ["Nessuna", null, null, null], ["Nessuna", null, null, null]],
    inverno: [["Recuperatore di calore", 0.6, null, null], ["Miscela con ricircolo", "AUTO", null, null], ["Preriscaldamento", "AUTO", null, 90],
      ["Umidificazione adiabatica", "AUTO", null, null], ["Post-riscaldamento", "AUTO", null, null], ["Ventilatore", 0.7, null, null]],
  };
  const DATI_PREDEFINITI = { estate: { esterno: { t: 32, ur: 50 }, ambiente: { t: 26, ur: 50 }, Qs: 5000, Ql: 1500 },
    inverno: { esterno: { t: -5, ur: 80 }, ambiente: { t: 20, ur: 40 }, Qs: 8000, Ql: 500 }, V: 5000, quotaEsterna: 100, quota: 120 };

  function codiceTipo(tipo) {
    if (fin(tipo)) return tipo >= 1 && tipo <= 11 ? Math.round(tipo) : 1;
    const i = TIPI.indexOf(String(tipo || "").trim());
    return i >= 0 ? i + 1 : 1;
  }
  // un parametro come nel foglio: numero (anche "0,7"), "AUTO" (solo P1 ne tiene conto) o vuoto
  function leggiParametro(v) {
    if (typeof v === "number") return fin(v) ? { ha: true, v, auto: false } : { ha: false, v: 0, auto: false };
    if (typeof v === "string") {
      const s = v.trim();
      if (s.toUpperCase() === "AUTO") return { ha: false, v: 0, auto: true };
      if (/^[-+]?(\d+([.,]\d*)?|[.,]\d+)([eE][-+]?\d+)?$/.test(s)) return { ha: true, v: Number(s.replace(",", ".")), auto: false };
    }
    return { ha: false, v: 0, auto: false };
  }

  // Una trasformazione (riga della sequenza). ingresso = stato (almeno t e x); par = [P1, P2, P3];
  // ctx = { p, ambiente: stato, immissione: { t, x }, mdot (kg/s della riga), mtot, fgen, ventilatoriValle (K) }.
  // Restituisce { codice, tipo, t, x, uscita (stato), mdot, Qt, Ql, Qs (kW), acqua (kg/h, + aggiunta, − condensata),
  //   ventilatoreDT, nonRaggiungibile, dettagli, nota (testo come la colonna «Note / avvisi» del foglio), avvisi [] }.
  function trasforma(tipo, ingresso, par, ctx) {
    const code = codiceTipo(tipo);
    const [P1, P2, P3] = [0, 1, 2].map((i) => leggiParametro(par ? par[i] : null));
    const p = ctx.p || 101325, A = ctx.ambiente, imm = ctx.immissione || { t: NaN, x: NaN };
    const tin = ingresso.t, xin = ingresso.x, hin = entalpia(tin, xin);
    const tdin = fin(ingresso.tdew) ? ingresso.tdew : tRugiada(xin, p);
    const mdot = ctx.mdot, cpin = cpUmido(xin);
    let t = tin, x = xin, d = {}, inf = false, fan = 0;
    switch (code) {
      case 2: {        // miscela con aria di ricircolo alle condizioni ambiente
        const f = Math.max(0, Math.min(1, P1.ha ? P1.v : (ctx.fgen || 0)));
        x = (1 - f) * xin + f * A.x;
        const h = (1 - f) * hin + f * A.h;
        t = (h - R0 * x) / (CPA + CPV * x);
        d.frazione = f;
        break;
      }
      case 3:          // recuperatore sensibile (P1) ed entalpico (P2), portate bilanciate, ripresa = ambiente
        if (P1.ha) { t = tin + P1.v * (A.t - tin); x = xin + (P2.ha ? P2.v : 0) * (A.x - xin); }
        break;
      case 4: t = P1.ha ? P1.v : (P2.ha ? tin + P2.v / (mdot * cpin) : tin); break;
      case 5: t = P1.ha ? P1.v : (P2.ha ? tin - P2.v / (mdot * cpin) : tin); break;
      case 6: {        // batteria fredda con deumidificazione: BF e ADP
        const bf = P2.ha ? P2.v : BF_PRED;
        const xt = P1.ha ? P1.v / 1000 : (P1.auto ? imm.x : -1);
        let xadp, tadp;
        if (P3.ha) { xadp = xSat(P3.v, p); tadp = P3.v; } else {
          xadp = xt > 0 && bf < 1 ? (xt - bf * xin) / (1 - bf) : -1;
          tadp = tRugiada(xadp > 0 ? xadp : EPS * 611.2 / (p - 611.2), p);
        }
        const ok = xadp > 0 && bf >= 0 && bf < 1, secca = P3.ha && xadp >= xin, nessuna = !P3.ha && xt >= xin;
        t = !ok || nessuna ? tin : tadp + bf * (tin - tadp);
        x = !ok || nessuna || secca ? xin : xadp + bf * (xin - xadp);
        d = { bf, xObiettivo: xt, xADP: xadp, tADP: tadp, ok, secca, nessuna };
        break;
      }
      case 7: {        // umidificazione adiabatica: h costante
        const modo = P1.ha || P1.auto ? 1 : (P2.ha ? 2 : (P3.ha ? 3 : 0));
        const phit = modo === 2 ? Math.min(1, Math.max(0.01, P2.v / 100)) : 1;
        const ts = tIsoentalpicaUR(hin, phit, p, tin);
        const xs = xDaHT(hin, ts);
        const xt = P1.ha ? P1.v / 1000 : (P1.auto ? imm.x : 0);
        const te = modo === 3 ? tin - Math.max(0, Math.min(1, P3.v)) * (tin - ts) : tin;
        x = [xin, Math.max(xin, Math.min(xt, xs)), Math.max(xin, xs), Math.max(xin, xDaHT(hin, te))][modo];
        t = x <= xin + 1e-9 ? tin : tDaHX(hin, x);
        d = { modo, xObiettivo: xt, xSaturazione: xs, tSaturazione: ts };
        break;
      }
      case 8: {        // umidificazione a vapore: Δh = Δx·h vapore
        const hv = P3.ha ? P3.v : H_VAPORE;
        const modo = P1.ha || P1.auto ? 1 : (P2.ha ? 2 : 0);
        const xt = P1.ha ? P1.v / 1000 : (P1.auto ? imm.x : 0);
        const phit = Math.min(1, Math.max(0.01, P2.v / 100));
        let xu = xin;
        if (modo === 2) {           // punto fisso su T (quasi isoterma), fino a convergenza
          let tk = tin;
          for (let i = 0; i < 60; i++) {
            const ps = psat(tk), xk = EPS * phit * ps / (p - phit * ps);
            const tn = (hin + (xk - xin) * hv - R0 * xk) / (CPA + CPV * xk);
            const fine = Math.abs(tn - tk) < 1e-10;
            tk = tn;
            if (fine) break;
          }
          const ps = psat(tk);
          xu = EPS * phit * ps / (p - phit * ps);
        }
        x = modo === 1 ? Math.max(xin, xt) : (modo === 2 ? Math.max(xin, xu) : xin);
        t = (hin + (x - xin) * hv - R0 * x) / (CPA + CPV * x);
        d = { modo, hVapore: hv, xObiettivo: xt };
        break;
      }
      case 9: {        // preriscaldamento (AUTO: fino all'isoentalpica che porta a x immissione con UR = P3)
        const phi = P3.ha ? Math.min(1, Math.max(0.05, P3.v / 100)) : UR_PRERISC / 100;
        const pw = Math.max(1, p * imm.x / (EPS + imm.x) / phi);
        const tb = tRugiadaPw(pw), h9 = entalpia(tb, imm.x), ta = tDaHX(h9, xin);
        t = P1.ha ? P1.v : (P1.auto ? Math.max(tin, ta) : (P2.ha ? tin + P2.v / (mdot * cpin) : tin));
        d = { urObiettivo: phi * 100, hObiettivo: h9, tAuto: ta };
        break;
      }
      case 10: {       // post-riscaldamento (AUTO: T immissione − ΔT dei ventilatori a valle)
        const ta = imm.t - (ctx.ventilatoriValle || 0);
        t = P1.ha ? P1.v : (P1.auto ? Math.max(tin, ta) : (P2.ha ? tin + P2.v / (mdot * cpin) : tin));
        inf = P1.auto && tin > ta + 0.05;
        d = { tAuto: ta };
        break;
      }
      case 11:
        fan = P1.ha ? P1.v : (P2.ha ? P2.v / (mdot * cpin) : 0);
        t = tin + fan;
        break;
      default: break;
    }
    const usc = statoTX(t, x, p);
    const mix = code === 2;
    const Qt = mix ? 0 : mdot * (usc.h - hin), Ql = mix ? 0 : mdot * (usc.x - xin) * R0, Qs = Qt - Ql;
    const acqua = mix ? 0 : mdot * (usc.x - xin) * 3600;
    // avvisi, con le stesse parole della colonna «Note / avvisi» del foglio
    const sconosciuto = !fin(tipo) && String(tipo || "").trim() !== "" && TIPI.indexOf(String(tipo).trim()) < 0;
    const modo7 = P1.ha || P1.auto ? 1 : (P2.ha ? 2 : (P3.ha ? 3 : 0)), modo8 = P1.ha || P1.auto ? 1 : (P2.ha ? 2 : 0);
    const manca = (code === 3 && !P1.ha) || ([4, 5, 11].includes(code) && !(P1.ha || P2.ha)) ||
      ([9, 10].includes(code) && !(P1.ha || P1.auto || P2.ha)) || (code === 6 && !(P1.ha || P1.auto || P3.ha)) ||
      (code === 7 && modo7 === 0) || (code === 8 && modo8 === 0);
    const wmiss = (sconosciuto ? "Tipo non riconosciuto. " : "") + (manca ? "Parametro mancante: la riga non modifica lo stato. " : "");
    let wtype = "";
    const tout = usc.t, xout = usc.x;
    switch (code) {
      case 2: wtype = d.frazione === 0 ? "Frazione di ricircolo 0: nessuna miscela (100 % aria esterna). "
        : `Ricircolo ${fisso(d.frazione * 100, 0)} % in massa; portata a monte ${fisso(ctx.mtot * (1 - d.frazione), 3)} kg/s. `; break;
      case 3: wtype = P1.ha ? `Potenza recuperata ${fisso(Math.abs(Qt), 2)} kW. ` : ""; break;
      case 4: wtype = tout < tin - 0.001 ? "Attenzione: T uscita < T ingresso (non è un riscaldamento). " : ""; break;
      case 5: wtype = (tout > tin + 0.001 ? "Attenzione: T uscita > T ingresso. " : "") + (tout < tdin - 0.01
        ? "T uscita sotto la T di rugiada dell'aria in ingresso: si forma condensa, usare «Raffreddamento con deumidificazione». " : ""); break;
      case 6: wtype = !d.ok ? "Dati batteria non validi (x ADP ≤ 0 oppure BF ≥ 1). "
        : d.nessuna ? "x obiettivo ≥ x ingresso: nessuna deumidificazione necessaria (riga senza effetto). "
          : `ADP = ${fisso(d.tADP, 1)} °C; SHR = ${fisso(Qt !== 0 ? Qs / Qt : 0, 2)}; BF = ${fisso(d.bf, 2)}. `
          + (d.tADP < 0 ? "ADP < 0 °C: rischio di brina. " : "") + (d.secca ? "Batteria secca (ADP sopra la rugiada). " : ""); break;
      case 7: wtype = (d.modo === 1 && d.xObiettivo > d.xSaturazione + 1e-7 ? "x obiettivo oltre la saturazione: limitato a UR 100 %. " : "")
        + (d.modo > 0 && xout <= xin + 1e-9 ? "Nessuna umidificazione (obiettivo ≤ ingresso). " : "")
        + (d.modo > 0 ? `h costante = ${fisso(hin, 2)} kJ/kg. ` : ""); break;
      case 8: wtype = (d.modo > 0 && xout <= xin + 1e-9 ? "Nessuna umidificazione (obiettivo ≤ ingresso). " : "")
        + (d.modo > 0 ? `Vapore ${fisso(acqua, 2)} kg/h. ` : ""); break;
      case 9: wtype = P1.auto && d.tAuto <= tin ? "Preriscaldamento non necessario (entalpia già sufficiente). "
        : P1.auto ? `AUTO: fino a h = ${fisso(d.hObiettivo, 2)} kJ/kg (isoentalpica per x_imm a UR ${fisso(d.urObiettivo, 0)} %). ` : ""; break;
      case 10: wtype = inf ? `PUNTO DI IMMISSIONE NON RAGGIUNGIBILE: T ingresso (${fisso(tin, 1)} °C) > T richiesta (${fisso(d.tAuto, 1)} °C). Aumentare la portata o ridurre BF. `
        : P1.auto ? `AUTO: T = T_imm − ΔT ventilatori a valle = ${fisso(d.tAuto, 1)} °C. ` : ""; break;
      default: break;
    }
    const wgen = usc.phi > 1.0001 ? "OLTRE SATURAZIONE (UR > 100 %): stato non fisico, nebbia/condensa. " : "";
    const nota = code === 1 ? wmiss : (wmiss + wtype + wgen ? wmiss + wgen + wtype : "OK");
    const avvisi = nota && nota !== "OK" ? nota.split(/(?<=\.) (?=[A-ZÈÀ«])/).map((s) => s.trim()).filter(Boolean) : [];
    return { codice: code, tipo: TIPI[code - 1], ingresso, t: usc.t, x: usc.x, uscita: usc, mdot, Qt, Ql, Qs, acqua,
      ventilatoreDT: fan, nonRaggiungibile: inf, dettagli: d, nota, avvisi };
  }

  // ------------------------------------------------------------------ portata, punto di immissione
  // riferimento della portata in volume: 0..3 (o il testo di RIF_PORTATA). Restituisce { mtot kg/s, vref, rho, xref }
  function portataMassica(V, riferimento, esterno, ambiente) {
    let i = fin(riferimento) ? Math.round(riferimento) : RIF_PORTATA.indexOf(riferimento);
    if (!(i >= 0 && i <= 3)) i = 0;
    const xref = [esterno.x, ambiente.x, 0, esterno.x][i];
    const vref = [esterno.v, ambiente.v, RA * 293.15 / 101.325, (1 + esterno.x) / 1.2][i];
    return { mtot: V / 3600 / vref, vref, rho: (1 + xref) / vref, xref, riferimento: i };
  }
  // punto di immissione dai carichi: apportoSensibile e apportoLatente in W (positivi = calore o vapore che entrano
  // nell'ambiente; in inverno le dispersioni sono un apporto sensibile negativo); m = portata di aria secca [kg/s]
  function puntoImmissione(ambiente, apportoSensibile, apportoLatente, m, p) {
    const cp = cpUmido(ambiente.x);
    const t = ambiente.t - apportoSensibile / 1000 / (m * cp), x = ambiente.x - apportoLatente / 1000 / (m * R0);
    return statoTX(t, x, p || ambiente.p || 101325);
  }

  // ------------------------------------------------------------------ sequenza dell'UTA (= una stagione del foglio)
  // opz = { p | quota, V (m³/h), quotaEsterna (%), riferimento (0..3), stagione: "estate"|"inverno",
  //   esterno: { t, ur }, ambiente: { t, ur }, Qs (W: in estate carico sensibile, in inverno dispersioni, positive),
  //   Ql (W, apporto latente), righe: [{ tipo, p1, p2, p3 }] oppure [[tipo, p1, p2, p3]] (predefinite: PRESET) }
  function sequenza(opz = {}) {
    const inverno = opz.stagione === "inverno";
    const pred = DATI_PREDEFINITI[inverno ? "inverno" : "estate"];
    const p = fin(opz.p) ? Math.max(30000, Math.min(120000, opz.p)) : pressione(fin(opz.quota) ? opz.quota : DATI_PREDEFINITI.quota);
    const V = fin(opz.V) ? opz.V : DATI_PREDEFINITI.V, qe = fin(opz.quotaEsterna) ? opz.quotaEsterna : DATI_PREDEFINITI.quotaEsterna;
    const e = opz.esterno || pred.esterno, a = opz.ambiente || pred.ambiente;
    const Qs = fin(opz.Qs) ? opz.Qs : pred.Qs, Ql = fin(opz.Ql) ? opz.Ql : pred.Ql;
    const E = stato(e.t, { ur: e.ur }, p), A = stato(a.t, { ur: a.ur }, p);
    const port = portataMassica(V, fin(opz.riferimento) ? opz.riferimento : 0, E, A);
    const mtot = port.mtot, cpA = cpUmido(A.x);
    const I = statoTX(inverno ? A.t + Qs / 1000 / (mtot * cpA) : A.t - Qs / 1000 / (mtot * cpA), A.x - Ql / 1000 / (mtot * R0), p);
    const fgen = Math.max(0, Math.min(1, 1 - qe / 100));
    const righe = (opz.righe || PRESET[inverno ? "inverno" : "estate"]).map((r) => Array.isArray(r)
      ? { tipo: r[0], par: [r[1], r[2], r[3]] } : { tipo: r.tipo, par: [r.p1, r.p2, r.p3] });
    const codici = righe.map((r) => codiceTipo(r.tipo));
    const mixidx = codici.indexOf(2);                               // −1 = nessuna miscela
    const fmix = mixidx >= 0 ? Math.max(0, Math.min(1, leggiParametro(righe[mixidx].par[0]).ha ? leggiParametro(righe[mixidx].par[0]).v : fgen)) : 0;
    const ctxBase = { p, ambiente: A, immissione: I, mtot, fgen };
    // i ventilatori a valle del post-riscaldamento AUTO: con P2 (potenza) il loro ΔT dipende dalla x a valle, quindi si
    // ripete il calcolo finché i ΔT non cambiano (nel foglio è un grafo senza cicli: stesso risultato)
    let fans = righe.map((r, i) => (codici[i] === 11 && leggiParametro(r.par[0]).ha ? leggiParametro(r.par[0]).v : 0));
    let out = [];
    for (let giro = 0; giro < 8; giro++) {
      out = [];
      let cur = E;
      righe.forEach((r, i) => {
        const valle = fans.slice(i + 1).reduce((s, v) => s + v, 0);
        const mdot = mixidx >= 0 && i < mixidx ? mtot * (1 - fmix) : mtot;
        const o = trasforma(r.tipo, cur, r.par, { ...ctxBase, mdot, ventilatoriValle: valle });
        o.n = i + 1;
        out.push(o);
        cur = o.uscita;
      });
      const nuovi = out.map((o) => o.ventilatoreDT);
      const fermo = nuovi.every((v, i) => Math.abs(v - fans[i]) < 1e-12);
      fans = nuovi;
      if (fermo) break;
    }
    const punti = [E, ...out.map((o) => o.uscita)];
    const somma = (codes, k) => out.reduce((s, o) => s + (codes.includes(o.codice) ? o[k] : 0), 0);
    const riepilogo = {
      frigoTotale: -somma([5, 6], "Qt"), frigoSensibile: -somma([5, 6], "Qs"), frigoLatente: -somma([5, 6], "Ql"),
      preriscaldamento: somma([9], "Qt"), postRiscaldamento: somma([10, 4], "Qt"), condensa: -somma([6], "acqua"),
      umidificazione: somma([7, 8], "acqua"), recuperata: Math.abs(somma([3], "Qt")), ventilatori: somma([11], "Qt"),
    };
    const R = inverno ? (-Qs + Ql !== 0 ? -Qs / (-Qs + Ql) : 1) : (Qs + Ql !== 0 ? Qs / (Qs + Ql) : 1);
    const dT = Math.abs(A.t - I.t), lim = inverno ? 15 : 10;
    const verifiche = (I.phi > 1 ? "UR immissione > 100 %: punto impossibile, aumentare la portata. " : "")
      + (dT > lim ? `ΔT di immissione > ${lim} K: rischio discomfort/stratificazione, aumentare la portata. ` : "")
      + (mtot <= 0 ? "Portata nulla. " : "")
      + (fgen > 0 && mixidx < 0 ? "Ricircolo previsto nei dati generali ma nessuna riga «Miscela» nella sequenza (calcolo a tutta aria esterna). " : "")
      + (I.x <= 0 ? "x immissione ≤ 0: carico latente troppo alto. " : "");
    const U = punti[punti.length - 1];
    const scostamento = { t: U.t - I.t, ur: U.ur - I.ur, xg: U.xg - I.xg, h: U.h - I.h };
    const inf = out.some((o) => o.nonRaggiungibile);
    const raggiungibile = !(inf || Math.abs(scostamento.t) > 0.3 || Math.abs(scostamento.xg) > 0.1);
    const esito = inf ? "PUNTO DI IMMISSIONE NON RAGGIUNGIBILE: l'aria a monte del post-riscaldamento è già più calda della T di immissione richiesta (post-riscaldamento = 0). Aumentare la portata o ridurre il fattore di bypass BF."
      : raggiungibile ? "Lo stato in uscita dall'UTA coincide con il punto di immissione richiesto."
        : "L'uscita dell'UTA NON coincide con il punto di immissione: verificare tipi e parametri della sequenza (scostamenti sopra).";
    return { stagione: inverno ? "inverno" : "estate", p, V, quotaEsterna: qe, ...port, mOA: mtot * (1 - fmix), fgen, fmix,
      mixidx: mixidx >= 0 ? mixidx + 1 : null, cpA, esterno: E, ambiente: A, immissione: I, R, dT, verifiche: verifiche || "OK",
      punti, righe: out, riepilogo, uscita: U, scostamento, raggiungibile, raggiungibileTesto: raggiungibile ? "SÌ" : "NO", esito };
  }

  // ------------------------------------------------------------------ serie orarie (fino a ~750.000 ore): vettori
  // vettori(t, ur, p): x (kg/kg), h, twb come Float32Array, calcolati una volta per serie (copia in una WeakMap legata
  // all'array delle temperature). NaN dove manca T o UR. tdew solo a richiesta (vettori(..., { rugiada: true })).
  const copie = new WeakMap();
  function vettori(t, ur, p, opz = {}) {
    p = p || 101325;
    const c = copie.get(t);
    if (c && c.ur === ur && c.p === p && (!opz.rugiada || c.tdew)) return c;
    const n = t.length, x = new Float32Array(n), h = new Float32Array(n), twb = new Float32Array(n);
    const tdew = opz.rugiada ? new Float32Array(n) : null;
    for (let i = 0; i < n; i++) {
      const ti = t[i], u = ur[i];
      if (!(ti === ti) || !(u === u) || u < 0) { x[i] = h[i] = twb[i] = NaN; if (tdew) tdew[i] = NaN; continue; }
      const pw = Math.min(u, 100) / 100 * Math.exp(lnPsat(ti)), xi = EPS * pw / (p - pw);
      x[i] = xi;
      h[i] = CPA * ti + xi * (R0 + CPV * ti);
      // bulbo umido: Newton dalla T (come il foglio), bisezione se non converge
      let tw = ti, ok = false;                          // come tBulboUmido: vicino a 0 °C la radice di psychrolib
      for (let k = 0; k < 30; k++) {
        const a = xBulboUmido(ti, tw, p) - xi, b = xBulboUmido(ti, tw + 0.001, p) - xi;
        if (b === a) break;
        const dd = a * 0.001 / (b - a);
        tw -= dd;
        if (!(tw > -100 && tw <= ti + 1e-9)) break;
        if (Math.abs(dd) < 1e-7) { ok = true; break; }
      }
      twb[i] = ok && Math.abs(tw) >= ZONA_SALTO ? tw : tBulboUmidoPsychrolib(ti, xi, p);
      if (tdew) tdew[i] = pw > 0 ? tRugiadaPw(pw) : NaN;
    }
    const r = { ur, p, x, h, twb, tdew };
    copie.set(t, r);
    return r;
  }
  // coordinate di Mollier di una serie (Y), dalla x già calcolata
  function vettoreMollier(t, x) {
    const n = t.length, y = new Float32Array(n);
    for (let i = 0; i < n; i++) y[i] = t[i] * (1 + CPV * x[i] / CPA);
    return y;
  }

  // ------------------------------------------------------------------ condizioni di progetto da una serie oraria
  // Statistiche della serie scelta (NON valori di norma): percentili sulle ore valide (T e UR presenti), quantile con
  // interpolazione lineare sui valori ordinati; valore «coincidente» = media della grandezza abbinata sulle ore il cui
  // valore cade entro ±metà classe dal percentile (classi: 1 K per T e bulbo umido, 2 kJ/kg per h, 0,5 g/kg per x),
  // allargata finché ci sono almeno 10 ore. Come le tabelle ASHRAE (cap. 14) ma sulla serie scelta.
  // Livelli (decisione del 14/11/2026: predefinito 99 % / 1 %, modificabili dall'utente):
  //   inverno = % delle ore in cui la T è SUPERIORE al valore di progetto (99 → quantile 1 %; 99,6 → 0,4 %)
  //   estate  = % delle ore in cui la grandezza SUPERA il valore di progetto (1 → quantile 99 %; 0,4 → 99,6 %)
  // Risultato:
  //   inverno:     T di progetto invernale e UR media coincidente
  //   estate:      T di progetto estiva e bulbo umido medio coincidente
  //   entalpia:    h superata nel livello estivo delle ore e T media coincidente
  //   umidita:     x superata nel livello estivo delle ore e T media coincidente
  //   bulboUmido:  bulbo umido superato nel livello estivo delle ore e T media coincidente
  // opz = { inverno: 99, estate: 1, indici: Uint32Array (sottoinsieme di ore, facoltativo) }
  const LIVELLI_PREDEFINITI = { inverno: 99, estate: 1 };
  const SCELTE_LIVELLO = { inverno: [99.6, 99, 95], estate: [0.4, 1, 5] };   // scelte rapide (decisione del 14/11/2026)
  function quantile(ordinati, q) {
    const n = ordinati.length;
    if (!n) return NaN;
    const pos = q * (n - 1), i = Math.floor(pos), f = pos - i;
    return i + 1 < n ? ordinati[i] * (1 - f) + ordinati[i + 1] * f : ordinati[i];
  }
  function coincidente(valori, abbinati, scelti, v, meta) {
    for (let d = meta, giro = 0; giro < 12; giro++, d *= 2) {
      let s = 0, n = 0;
      for (let k = 0; k < scelti.length; k++) {
        const i = scelti[k], a = valori[i];
        if (a >= v - d && a <= v + d) { const b = abbinati[i]; if (b === b) { s += b; n++; } }
      }
      if (n >= 10 || n === scelti.length) return { media: n ? s / n : NaN, ore: n, classe: 2 * d };
    }
    return { media: NaN, ore: 0, classe: NaN };
  }
  function livelli(opz = {}) {
    const lv = (v, pred, lo, hi) => { const n = typeof v === "string" ? Number(v.replace(",", ".")) : v; return fin(n) && n > lo && n < hi ? n : pred; };
    return { inverno: lv(opz.inverno, LIVELLI_PREDEFINITI.inverno, 50, 100), estate: lv(opz.estate, LIVELLI_PREDEFINITI.estate, 0, 50) };
  }
  function condizioniProgetto(t, ur, p, opz = {}) {
    p = p || 101325;
    const L = livelli(opz), qi = 1 - L.inverno / 100, qe = 1 - L.estate / 100;
    const V = vettori(t, ur, p);
    const sorg = opz.indici || null, n0 = sorg ? sorg.length : t.length;
    const tmp = new Uint32Array(n0);
    let n = 0;
    for (let k = 0; k < n0; k++) { const i = sorg ? sorg[k] : k; if (V.x[i] === V.x[i]) tmp[n++] = i; }
    const scelti = tmp.subarray(0, n);
    if (n < 24) return { ore: n, livelli: L, avviso: "Troppe poche ore valide per le condizioni di progetto." };
    const ordina = (arr) => { const a = new Float32Array(n); for (let k = 0; k < n; k++) a[k] = arr[scelti[k]]; return a.sort(); };
    const sT = ordina(t), sH = ordina(V.h), sX = ordina(V.x), sW = ordina(V.twb);
    const voce = (valori, ord, q, abbinati, meta) => {
      const v = quantile(ord, q), c = coincidente(valori, abbinati, scelti, v, meta);
      return { valore: v, coincidente: c.media, ore: c.ore };
    };
    const w = voce(t, sT, qi, ur, 0.5), s = voce(t, sT, qe, V.twb, 0.5), hh = voce(V.h, sH, qe, t, 1);
    const xx = voce(V.x, sX, qe, t, 0.00025), bb = voce(V.twb, sW, qe, t, 0.5);
    const st = (tt, dato) => (fin(tt) ? stato(tt, dato, p) : null);
    return {
      ore: n, livelli: L, metodo: "percentili delle ore valide della serie scelta (non valori di norma)",
      inverno: { t: w.valore, ur: w.coincidente, ore: w.ore, livello: L.inverno, stato: st(w.valore, { ur: Math.min(100, w.coincidente) }) },
      estate: { t: s.valore, twb: s.coincidente, ore: s.ore, livello: L.estate, stato: st(s.valore, { twb: Math.min(s.valore, s.coincidente) }) },
      entalpia: { h: hh.valore, t: hh.coincidente, ore: hh.ore, livello: L.estate, stato: st(hh.coincidente, { h: hh.valore }) },
      umidita: { x: xx.valore, xg: xx.valore * 1000, t: xx.coincidente, ore: xx.ore, livello: L.estate, stato: st(xx.coincidente, { x: xx.valore }) },
      bulboUmido: { twb: bb.valore, t: bb.coincidente, ore: bb.ore, livello: L.estate, stato: st(bb.coincidente, { twb: Math.min(bb.coincidente, bb.valore) }) },
    };
  }
  // descrizioni per le pagine (livello in %, con la virgola)
  function nomiProgetto(opz = {}) {
    const L = livelli(opz), pc = (v) => `${fisso(v, v % 1 ? 1 : 0)} %`;
    const nel = (v) => { const c = pc(v); return /^(1|8|11)(\D|$)/.test(c) ? `nell'${c}` : c.startsWith("0") ? `nello ${c}` : `nel ${c}`; };
    return {
      inverno: `Inverno ${pc(L.inverno)}: temperatura superata ${nel(L.inverno)} delle ore, con l'UR media di quelle ore`,
      estate: `Estate ${pc(L.estate)}: temperatura superata solo ${nel(L.estate)} delle ore (circa ${fisso(L.estate * 87.66, 0)} ore l'anno), con il bulbo umido medio di quelle ore`,
      entalpia: `Entalpia ${pc(L.estate)}: entalpia superata solo ${nel(L.estate)} delle ore, con la temperatura media di quelle ore`,
      umidita: `Umidità specifica ${pc(L.estate)}: umidità superata solo ${nel(L.estate)} delle ore, con la temperatura media di quelle ore`,
      bulboUmido: `Bulbo umido ${pc(L.estate)}: bulbo umido superato solo ${nel(L.estate)} delle ore, con la temperatura media di quelle ore`,
    };
  }

  const API = { EPS, RA, R0, CPA, CPV, H_VAPORE, BF_PRED, UR_PRERISC,
    pressione, psat, lnPsat, dLnPsat, xDaPw, pwDaX, xSat, xDaUR, entalpia, volume, tDaHX, xDaHT, cpUmido, mollierY, tDaMollier,
    tRugiadaPw, tRugiada, xBulboUmido, tBulboUmido, tIsoentalpicaUR, tSatDaH, adpRetta, adpDaBF,
    statoTX, stato, statoHX, fisso, TIPI, PARAMETRI, RIF_PORTATA, PRESET, DATI_PREDEFINITI, codiceTipo, leggiParametro,
    trasforma, portataMassica, puntoImmissione, sequenza, vettori, vettoreMollier, quantile, LIVELLI_PREDEFINITI, SCELTE_LIVELLO, livelli, condizioniProgetto, nomiProgetto };
  radice.EUGENIO_PSICRO = API;
  if (typeof module !== "undefined" && module.exports) module.exports = API;
})(typeof self !== "undefined" ? self : globalThis);
