"use strict";
// Trattamento aria › Carichi latenti (14/11/2026). Scelte una condizione interna estiva (UR = massimo) e una invernale
// (UR = minimo), la pagina conta, sulla serie oraria del comune, le ore in cui l'aria esterna va deumidificata (estate) o
// umidificata a vapore (inverno) e quanta energia latente richiede il suo trattamento, per una portata d'aria esterna.
// Moduli comuni: psicro.js (formule), diagramma_aria.js (diagramma), scelta_aria.js (passo 1, livello di progetto),
// gruppi_ore.js (ore di funzionamento: un gruppo per stagione).
//
// Parte pura (anche in node, per il test di parità con fase14-trattamento-aria/aria/latenti.py):
//   EUGENIO_ARIA_LATENTI.calcola(opz) → risultato di una stagione. Regole:
//   x_t = x(T obiettivo, UR obiettivo, p); ṁ = V/(3600·v_rif) con v_rif ora per ora come psicro.portataMassica
//   (0 aria esterna di quell'ora, 1 aria interna obiettivo, 2 aria standard 20 °C, 3 densità fissa 1,2 kg/m³);
//   ESTATE: ora da deumidificare se x_e > x_t; Q_l = ṁ·(x_e − x_t)·2501 kW; condensa ṁ·Δx·3600 kg/h;
//           parte sensibile ṁ·(1,006 + 1,86·x_e)·(T_e − T_t) se T_e > T_t; totale ṁ·(h_e − h_t) se positivo;
//   INVERNO: ora da umidificare se x_e < x_t; Q_l = ṁ·(x_t − x_e)·2676 kW (vapore, come il foglio); acqua ṁ·Δx·3600 kg/h;
//           parte sensibile ṁ·(1,006 + 1,86·x_e)·(T_t − T_e) se T_e < T_t; totale ṁ·(h_t − h_e) se positivo.
//   Ogni ora vale 1 h (kWh = kW); «all'anno» = diviso per gli anni del gruppo; potenza di progetto = quantile delle potenze
//   di tutte le ore del gruppo superato solo nel livello % delle ore; SHR = ΣQ_s/(ΣQ_s + ΣQ_l).
(function (radice) {
  const R_LATENTE = 2501, H_VAPORE = 2676, ORE_ANNO = 8766, RA = 0.287042;
  // un'ora va trattata se x esterna supera (estate) o resta sotto (inverno) x obiettivo di più di 1e-7 kg/kg: le ore
  // esattamente all'obiettivo (T in decimi, UR intera) non contano per l'arrotondamento in Float32 (14/11/2026)
  const SOGLIA_DX = 1e-7;
  const Pm = radice.EUGENIO_PSICRO || (typeof require === "function" ? require("./psicro.js") : null);

  function quantile(ordinati, q) {
    const n = ordinati.length;
    if (!n) return NaN;
    const pos = q * (n - 1), i = Math.floor(pos), f = pos - i;
    return i + 1 < n ? ordinati[i] * (1 - f) + ordinati[i + 1] * f : ordinati[i];
  }
  const anniFinestra = (n, inizio) => Math.max(0, n - inizio) / ORE_ANNO;

  // opz = { stagione, t, x, h (Float32Array), indici (Uint32Array), p, tObiettivo, urObiettivo, V (m³/h), riferimento 0–3,
  //   mese (Uint8Array, mese locale di ogni ora), anni, livello (% delle ore), classe (g/kg), nClassi, puntiCurva, indiciOre }
  function calcola(opz) {
    const inverno = opz.stagione === "inverno";
    const p = opz.p || 101325, V = Number.isFinite(opz.V) ? opz.V : 1000;
    const rif = [0, 1, 2, 3].includes(opz.riferimento) ? opz.riferimento : 0;
    const ob = Pm.stato(opz.tObiettivo, { ur: opz.urObiettivo }, p);
    const xt = ob.x, ht = ob.h, tt = opz.tObiettivo;
    const t = opz.t, x = opz.x, h = opz.h, ind = opz.indici, mese = opz.mese || null;
    const anni = opz.anni > 0 ? opz.anni : 1, lv = Number.isFinite(opz.livello) ? opz.livello : 1;
    const classe = opz.classe || 1, nClassi = opz.nClassi || 10, puntiCurva = opz.puntiCurva || 200;
    const r = inverno ? H_VAPORE : R_LATENTE;
    const vStd = RA * 293.15 / 101.325;
    const nTot = ind.length;
    const tutte = new Float64Array(nTot), trattate = new Float64Array(nTot);
    const si = new Uint32Array(nTot), no = new Uint32Array(nTot);
    const mOre = new Float64Array(13), mE = new Float64Array(13), mA = new Float64Array(13), mS = new Float64Array(13), mG = new Float64Array(13);
    const cOre = new Float64Array(nClassi), cE = new Float64Array(nClassi);
    let n = 0, ore = 0, nNo = 0, E = 0, A = 0, S = 0, T = 0, picco = 0, acquaPicco = 0, mSomma = 0;
    for (let k = 0; k < nTot; k++) {
      const i = ind[k], te = t[i], xe = x[i];
      if (!(te === te) || !(xe === xe)) continue;
      const he = h[i];
      const vref = rif === 0 ? RA * (te + 273.15) * (1 + 1.607858 * xe) / (p / 1000) : rif === 1 ? ob.v : rif === 2 ? vStd : (1 + xe) / 1.2;
      const m = V / 3600 / vref;
      mSomma += m;
      const dx = inverno ? xt - xe : xe - xt;
      let ql = 0, aq = 0;
      if (dx > SOGLIA_DX) {
        ql = m * dx * r; aq = m * dx * 3600;
        trattate[ore++] = ql; si[ore - 1] = i;
        const c = Math.min(Math.floor(dx * 1000 / classe), nClassi - 1);
        cOre[c] += 1; cE[c] += ql;
        if (aq > acquaPicco) acquaPicco = aq;
      } else no[nNo++] = i;
      const dt = inverno ? tt - te : te - tt;
      const qs = dt > 0 ? m * (1.006 + 1.86 * xe) * dt : 0;
      const dh = inverno ? ht - he : he - ht;
      const qt = dh > 0 ? m * dh : 0;
      E += ql; A += aq; S += qs; T += qt;
      if (ql > picco) picco = ql;
      tutte[n++] = ql;
      if (mese) { const mm = mese[i]; mG[mm] += 1; if (dx > SOGLIA_DX) mOre[mm] += 1; mE[mm] += ql; mA[mm] += aq; mS[mm] += qs; }
    }
    const ordinate = tutte.subarray(0, n).sort();
    const giu = trattate.subarray(0, ore).sort();          // crescente: la curva di durata si legge dalla fine
    const curva = [];
    if (ore) {
      const npt = Math.min(puntiCurva, ore);
      let prima = -1;
      for (let j = 0; j < npt; j++) {
        const rk = npt === 1 ? 0 : Math.floor(j * (ore - 1) / (npt - 1) + 0.5);
        if (rk === prima) continue;
        prima = rk;
        curva.push({ ore: (rk + 1) / anni, kW: giu[ore - 1 - rk] });
      }
    }
    const mesi = [];
    for (let k = 1; k <= 12; k++) mesi.push({ mese: k, ore: mOre[k] / anni, energia: mE[k] / anni, acqua: mA[k] / anni, sensibile: mS[k] / anni, oreGruppo: mG[k] / anni });
    const classi = [];
    for (let k = 0; k < nClassi; k++) classi.push({ da: k * classe, a: k === nClassi - 1 ? null : (k + 1) * classe, ore: cOre[k] / anni, energia: cE[k] / anni });
    const totSL = S + E;
    return {
      stagione: inverno ? "inverno" : "estate",
      obiettivo: { t: tt, ur: opz.urObiettivo, x: xt, xg: xt * 1000, h: ht, v: ob.v, rho: ob.rho, tdew: ob.tdew, twb: ob.twb },
      V, riferimento: rif, anni, livello: lv, r,
      oreGruppo: n, ore, oreAnno: ore / anni, quota: n ? ore / n : 0,
      energia: E, energiaAnno: E / anni, acqua: A, acquaAnno: A / anni, sensibile: S, sensibileAnno: S / anni, totale: T, totaleAnno: T / anni,
      picco: n ? picco : 0, piccoLivello: n ? quantile(ordinate, 1 - lv / 100) : NaN, acquaPicco: n ? acquaPicco : 0,
      shr: totSL > 0 ? S / totSL : NaN, portataMedia: n ? mSomma / n : NaN,
      mesi, classi, curva, indiciSi: si.slice(0, ore), indiciNo: no.slice(0, nNo),
    };
  }

  const API = { R_LATENTE, H_VAPORE, ORE_ANNO, calcola, anniFinestra, quantile };
  radice.EUGENIO_ARIA_LATENTI = API;
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  if (typeof document === "undefined") return;

  // =================================================================================================== la pagina
  const P = window.EUGENIO_PSICRO, GO = window.EUGENIO_GRUPPI_ORE, SA = window.EUGENIO_SCELTA_ARIA, GR = window.EUGENIO_GRAFICI;
  const $ = (id) => document.getElementById(id);
  // migliaia sempre col punto (it-IT non separa i numeri di 4 cifre: 1.607, non 1607)
  const fmt = (v, d = 0) => (Number.isFinite(v) ? EUGENIO_NUMERI.formato(v, d) : "—");   // numeri.js
  const meno = (s) => String(s).replace(/^-/, "−");
  const fmtM = (v, d = 0) => meno(fmt(v, d));
  const num = (s) => { const v = Number(String(s).trim().replace(",", ".")); return Number.isFinite(v) ? v : NaN; };
  function h(tag, cls, testo) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (testo !== undefined && testo !== null) e.textContent = testo;
    return e;
  }
  const MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"];
  const CHIAVE = "eugenio-aria-latenti-v1";
  const COLORI = { estate: ["#4DA3FF", "#0070C0"], inverno: ["#FF6B6B", "#C00000"] };      // [scuro, chiaro] come il diagramma
  const colore = (s) => COLORI[s][document.documentElement.dataset.theme === "light" ? 1 : 0];
  const LIMITI = { t: [15, 30, 0.5], ur: [20, 80, 1] };
  const DEF = {
    estate: { nome: "Estate", pred: { t: 26, ur: 50 }, preset: "estate", titolo: "deumidificazione", urNome: "Umidità relativa massima",
      ore: "ore da deumidificare", energia: "energia latente", acqua: "condensa", sensibile: "raffreddamento sensibile fino alla T interna",
      totale: "raffreddamento totale (entalpia)", r: "r = 2501 kJ/kg" },
    inverno: { nome: "Inverno", pred: { t: 20, ur: 40 }, preset: "inverno", titolo: "umidificazione a vapore", urNome: "Umidità relativa minima",
      ore: "ore da umidificare", energia: "energia del vapore", acqua: "acqua per il vapore", sensibile: "riscaldamento sensibile fino alla T interna",
      totale: "riscaldamento totale (entalpia)", r: "h vapore = 2676 kJ/kg" },
  };
  const RIF = ["Aria esterna, ora per ora (come il foglio)", "Aria interna (condizione obiettivo)", "Aria standard 20 °C, 101325 Pa", "Densità fissa 1,2 kg/m³"];

  function leggiMemoria() { try { return JSON.parse(localStorage.getItem(CHIAVE) || "{}") || {}; } catch (e) { return {}; } }
  const mem = leggiMemoria();
  const st = {
    estate: { t: DEF.estate.pred.t, ur: DEF.estate.pred.ur, ris: null },
    inverno: { t: DEF.inverno.pred.t, ur: DEF.inverno.pred.ur, ris: null },
    V: 1000, rif: 0,
  };
  for (const s of ["estate", "inverno"]) {
    const m = mem[s] || {};
    if (Number.isFinite(m.t) && m.t >= LIMITI.t[0] && m.t <= LIMITI.t[1]) st[s].t = m.t;
    if (Number.isFinite(m.ur) && m.ur >= LIMITI.ur[0] && m.ur <= LIMITI.ur[1]) st[s].ur = m.ur;
  }
  if (Number.isFinite(mem.V) && mem.V > 0) st.V = mem.V;
  if ([0, 1, 2, 3].includes(mem.rif)) st.rif = mem.rif;
  // (20/11/2026) collegamento a questa simulazione: obiettivi (T*UR per stagione), portata e riferimento dall'indirizzo,
  // più forti della memoria del browser; comune, anni, livello, gruppi e diagramma li leggono i moduli comuni
  {
    const q = new URLSearchParams(location.search);
    for (const s of ["estate", "inverno"]) {
      const [t, ur] = (q.get(s === "estate" ? "obiettivo_estate" : "obiettivo_inverno") || "").split("*").map((x) => Number(x.replace(",", ".")));
      if (Number.isFinite(t) && t >= LIMITI.t[0] && t <= LIMITI.t[1]) st[s].t = t;
      if (Number.isFinite(ur) && ur >= LIMITI.ur[0] && ur <= LIMITI.ur[1]) st[s].ur = ur;
    }
    if (Number(q.get("portata")) > 0) st.V = Number(q.get("portata"));
    if (["0", "1", "2", "3"].includes(q.get("riferimento"))) st.rif = Number(q.get("riferimento"));
  }
  if (window.EUGENIO_COLLEGAMENTO) window.EUGENIO_COLLEGAMENTO.registra({
    chiavi: ["obiettivo_estate", "obiettivo_inverno", "portata", "riferimento"],
    leggi: () => ({ obiettivo_estate: `${st.estate.t}*${st.estate.ur}`, obiettivo_inverno: `${st.inverno.t}*${st.inverno.ur}`,
      portata: st.V, riferimento: st.rif }),
  });
  function salva() {
    try { localStorage.setItem(CHIAVE, JSON.stringify({ estate: { t: st.estate.t, ur: st.estate.ur }, inverno: { t: st.inverno.t, ur: st.inverno.ur }, V: st.V, rif: st.rif })); } catch (e) { /* niente */ }
  }

  // ---------------------------------------------------------------- diagramma, passo 1, livello
  const titolo = "Carichi latenti";
  const D = window.EUGENIO_DIAGRAMMA_ARIA.crea($("diagramma-aria"), {
    titolo,
    nomeFile: () => "eugenio-aria-latenti",
    avviso: () => (S && S.serie() && S.serie().sintetica ? "Dati sintetici di prova, non reali." : ""),
    fonti: () => {
      const s = S && S.serie();
      if (!s) return [];
      return [`Serie oraria: ${s.comune || ""}, ${s.fonte}${s.licenza && s.licenza !== "—" ? ` (${s.licenza})` : ""}.`,
        `Estate ${fmt(st.estate.t, 1)} °C ${fmt(st.estate.ur)} % (UR massima) · Inverno ${fmt(st.inverno.t, 1)} °C ${fmt(st.inverno.ur)} % (UR minima).`];
    },
  });
  const S = SA.crea({ mappa: "#mappa", passo: "#scelta-aria" });
  const L = SA.livelloProgetto("#aria-livello", { titolo: "Livello per la potenza di progetto" });

  // ---------------------------------------------------------------- una stagione: obiettivo e ore
  function cursore(s, k, etichetta, unita) {
    const [lo, hi, passo] = LIMITI[k];
    const id = `lat-${s}-${k}`;
    const box = h("div", "latenti-campo");
    const l = h("label", null, etichetta); l.htmlFor = id;
    const riga = h("div", "latenti-riga");
    const r = document.createElement("input");
    r.type = "range"; r.min = lo; r.max = hi; r.step = passo; r.value = st[s][k]; r.id = id;
    const n = document.createElement("input");
    n.type = "text"; n.inputMode = "decimal"; n.size = 4; n.className = "latenti-num";
    n.setAttribute("aria-label", `${etichetta} (${unita}), da ${fmt(lo)} a ${fmt(hi)}`);
    const scrivi = (v) => fmt(v, k === "t" && v % 1 ? 1 : 0);
    n.value = scrivi(st[s][k]);
    r.addEventListener("input", () => { st[s][k] = +r.value; n.value = scrivi(+r.value); n.setAttribute("aria-invalid", "false"); cambiaObiettivo(s); });
    n.addEventListener("input", () => {
      const v = num(n.value), ok = Number.isFinite(v) && v >= lo && v <= hi;
      n.setAttribute("aria-invalid", ok ? "false" : "true");
      if (ok) { st[s][k] = v; r.value = v; cambiaObiettivo(s); }
    });
    n.addEventListener("change", () => { if (n.getAttribute("aria-invalid") !== "true") n.value = scrivi(st[s][k]); });
    riga.append(r, n, h("span", "latenti-unita", unita));
    box.append(l, riga);
    return { box, imposta: (v) => { r.value = v; n.value = scrivi(v); n.setAttribute("aria-invalid", "false"); } };
  }

  const V = {};      // viste delle stagioni
  for (const s of ["estate", "inverno"]) {
    const d = DEF[s], box = $(`latenti-${s}`);
    box.classList.add("latenti-stagione", `stagione-${s}`);
    const ob = h("fieldset", "latenti-obiettivo");
    ob.appendChild(h("legend", null, `Condizione interna obiettivo (${s === "estate" ? "UR massima" : "UR minima"})`));
    const ct = cursore(s, "t", "Temperatura interna", "°C"), cu = cursore(s, "ur", d.urNome, "%");
    const prop = h("dl", "latenti-proprieta");
    const ripristina = h("button", "bottone secondario piccolo latenti-ripristina", `Condizioni di progetto (${fmt(d.pred.t)} °C, ${fmt(d.pred.ur)} %)`);
    ripristina.type = "button";
    ripristina.addEventListener("click", () => { st[s].t = d.pred.t; st[s].ur = d.pred.ur; ct.imposta(d.pred.t); cu.imposta(d.pred.ur); cambiaObiettivo(s); });
    ob.append(ct.box, cu.box, prop, ripristina);
    const gBox = h("div", "latenti-gruppi");
    gBox.id = `aria-gruppi-${s}`;
    const titoloOre = h("h3", "latenti-sotto", "Ore di funzionamento");
    const sintesi = h("p", "latenti-sintesi");
    sintesi.setAttribute("aria-live", "polite");
    box.append(ob, titoloOre, gBox, sintesi);
    const G = GO.crea(gBox, { iniziali: [{ preset: d.preset, anni: 10 }], massimo: 1 });
    const fs = gBox.querySelector(".aria-gruppo");
    if (fs) {
      fs.style.setProperty("--colore-gruppo", `var(--lat-${s})`);
      const c = fs.querySelector(".aria-campione"); if (c) c.style.background = `var(--lat-${s})`;
    }
    V[s] = { box, prop, sintesi, G, ct, cu };
    G.su(() => ricalcola(s));
  }

  function proprieta(s) {
    const p = S.serie() ? S.serie().p : D.pressione() || 101325;
    const o = P.stato(st[s].t, { ur: st[s].ur }, p);
    const voci = [["x", `${fmt(o.xg, 2)} g/kg`, "umidità specifica (assoluta)"], ["h", `${fmt(o.h, 1)} kJ/kg`, "entalpia"],
      ["T rugiada", `${fmtM(o.tdew, 1)} °C`, "temperatura di rugiada"], ["T bulbo umido", `${fmtM(o.twb, 1)} °C`, "temperatura di bulbo umido"],
      ["v", `${fmt(o.v, 3)} m³/kg`, "volume specifico"], ["ρ", `${fmt(o.rho, 3)} kg/m³`, "densità dell'aria umida"]];
    const dl = V[s].prop;
    dl.innerHTML = "";
    for (const [k, v, t] of voci) { const w = h("div"), dt = h("dt", null, k); dt.title = t; w.append(dt, h("dd", null, v)); dl.appendChild(w); }
    dl.setAttribute("aria-label", `Proprietà della condizione interna a ${fmt(p)} Pa`);
    return o;
  }

  // ---------------------------------------------------------------- calcolo
  const attesa = { estate: 0, inverno: 0 };
  let attesaRisultati = 0, attesaSalva = 0;
  function cambiaObiettivo(s) {
    proprieta(s);
    if (!attesa[s]) attesa[s] = requestAnimationFrame(() => { attesa[s] = 0; ricalcola(s); });
    clearTimeout(attesaSalva); attesaSalva = setTimeout(salva, 400);
  }
  function gruppo(s) { return V[s].G.gruppi()[0] || null; }
  function ricalcola(s) {
    const serie = S.serie(), g = gruppo(s);
    proprieta(s);
    if (!serie || !g) { st[s].ris = null; disegnaStagione(s); sintesi(s); programmaRisultati(); return; }
    const Vv = P.vettori(serie.t, serie.ur, serie.p);
    const campi = GO.campiOrari(serie);
    const lv = L.valori();
    st[s].ris = calcola({
      stagione: s, t: serie.t, x: Vv.x, h: Vv.h, indici: g.indici, p: serie.p, tObiettivo: st[s].t, urObiettivo: st[s].ur,
      V: st.V, riferimento: st.rif, mese: campi.mese, anni: anniFinestra(serie.n, GO.inizioAnni(serie, g.anni)),
      livello: s === "estate" ? lv.estate : 100 - lv.inverno,
    });
    st[s].ris.gruppo = g;
    disegnaStagione(s);
    sintesi(s);
    programmaRisultati();
  }
  const ricalcolaTutto = () => { ricalcola("estate"); ricalcola("inverno"); };

  function sintesi(s) {
    const r = st[s].ris, el = V[s].sintesi;
    if (!S.serie()) { el.textContent = "Scegli il comune e la serie al passo 1."; return; }
    if (!r || !r.oreGruppo) { el.textContent = "Nessuna ora nel gruppo: cambia date o ore."; return; }
    el.innerHTML = "";
    const b = (t) => h("b", null, t);
    el.append(b(`${fmt(r.oreAnno)} ${DEF[s].ore}`), ` all'anno (${fmt(r.quota * 100, 1)} % delle ore del gruppo) · `,
      b(`${fmt(r.energiaAnno)} kWh/anno`), ` di ${DEF[s].energia} · picco `, b(`${fmt(r.picco, 1)} kW`), ` con ${fmt(st.V)} m³/h di aria esterna.`);
  }

  // ---------------------------------------------------------------- diagramma
  function zonaPoligono(s, xt, p) {
    const out = [], N = 24, tMin = -10, tMax = 50, xMax = 0.03;
    const td = P.tRugiada(xt, p);
    if (s === "estate") {
      if (xt >= xMax) return null;
      const t30 = Math.min(tMax, P.tRugiada(xMax, p));
      out.push({ t: Math.max(tMin, td), x: xt }, { t: tMax, x: xt }, { t: tMax, x: xMax }, { t: t30, x: xMax });
      for (let i = 1; i < N; i++) { const t = t30 + (td - t30) * i / N; if (t > tMin) out.push({ t, x: P.xSat(t, p) }); }
      return out;
    }
    out.push({ t: tMin, x: 0 }, { t: tMax, x: 0 }, { t: tMax, x: xt });
    if (td > tMin) {
      out.push({ t: td, x: xt });
      for (let i = 1; i <= N; i++) { const t = td + (tMin - td) * i / N; out.push({ t, x: P.xSat(t, p) }); }
    } else out.push({ t: tMin, x: xt });
    return out;
  }
  function disegnaStagione(s) {
    const serie = S.serie(), r = st[s].ris, d = DEF[s];
    const nomi = [`${s}-no`, `${s}-si`, `${s}-zona`, `${s}-linea`, `${s}-punto`];
    if (!serie || !r) { nomi.forEach((n) => D.togli(n)); return; }
    const p = serie.p, xt = r.obiettivo.x, mostra = r.gruppo.mostra !== false;
    const Vv = P.vettori(serie.t, serie.ur, p);
    D.nuvola(`${s}-no`, "var(--tenue)", { t: serie.t, x: Vv.x, indici: r.indiciNo },
      { etichetta: `${d.nome}: ore senza ${s === "estate" ? "deumidificazione" : "umidificazione"}`, nota: `(${fmt((r.oreGruppo - r.ore) / r.anni)} ore/anno)`, alpha: undefined });
    D.nuvola(`${s}-si`, s, { t: serie.t, x: Vv.x, indici: r.indiciSi },
      { etichetta: `${d.nome}: ${d.ore}`, nota: `(${fmt(r.oreAnno)} ore/anno)` });
    const poli = zonaPoligono(s, xt, p);
    if (poli) D.zona(`${s}-zona`, poli, { colore: s, alpha: 0.07, bordo: false, etichetta: `${d.nome}: zona da ${s === "estate" ? "deumidificare (x sopra l'obiettivo)" : "umidificare (x sotto l'obiettivo)"}` });
    else D.togli(`${s}-zona`);
    const td = Math.max(-10, P.tRugiada(xt, p));
    D.spezzata(`${s}-linea`, [{ t: td, x: xt }, { t: 50, x: xt }], { colore: s, spessore: 1.6, marcatori: false, tratteggio: [6, 4], legenda: false });
    D.punto(`${s}-punto`, { t: st[s].t, x: xt }, { colore: s, simbolo: "quadrato", etichetta: `${d.nome} ${fmt(st[s].t, st[s].t % 1 ? 1 : 0)} °C ${fmt(st[s].ur)} %`,
      posizione: s === "estate" ? "r" : "l", legenda: false });
    nomi.forEach((n) => D.mostra(n, mostra));
  }

  // ---------------------------------------------------------------- portata d'aria
  (function portata() {
    const box = $("latenti-portata");
    const l1 = h("label", null, "Portata d'aria esterna (m³/h)"); l1.htmlFor = "lat-portata";
    const v = document.createElement("input");
    v.type = "text"; v.inputMode = "decimal"; v.id = "lat-portata"; v.size = 8; v.value = fmt(st.V);
    const l2 = h("label", null, "Riferimento della portata in volume"); l2.htmlFor = "lat-riferimento";
    const sel = document.createElement("select"); sel.id = "lat-riferimento";
    RIF.forEach((t, i) => { const o = h("option", null, t); o.value = String(i); sel.appendChild(o); });
    sel.value = String(st.rif);
    const aiuto = h("p", "aiuto", "I risultati sono proporzionali alla portata: accanto a ogni valore c'è anche quello per 1.000 m³/h, da moltiplicare per la portata del tuo impianto tutt'aria (o della sola aria esterna).");
    box.append(l1, v, l2, sel, aiuto);
    v.addEventListener("input", () => {
      const n = num(v.value.replace(/\./g, "").replace(/\s/g, "")), ok = Number.isFinite(n) && n > 0 && n <= 1e7;
      v.setAttribute("aria-invalid", ok ? "false" : "true");
      if (ok) { st.V = n; salva(); ricalcolaTutto(); }
    });
    v.addEventListener("change", () => { if (v.getAttribute("aria-invalid") !== "true") v.value = fmt(st.V); });
    sel.addEventListener("change", () => { st.rif = +sel.value; salva(); ricalcolaTutto(); });
  })();

  // ---------------------------------------------------------------- risultati
  function programmaRisultati() { clearTimeout(attesaRisultati); attesaRisultati = setTimeout(risultati, 120); }
  function cifra(valore, unita, etichetta, nota) {
    const d = h("div", "cifra");
    const b = h("b", null, valore);
    if (unita) b.appendChild(h("small", null, ` ${unita}`));
    d.append(b, h("span", null, etichetta));
    if (nota) d.appendChild(h("small", null, nota));
    return d;
  }
  function tabella(intestazioni, righe, cls) {
    const box = h("div", "tabella-scorre");
    const t = h("table", `mensili ${cls || ""}`.trim());
    const r1 = t.createTHead().insertRow();
    intestazioni.forEach((c) => r1.appendChild(h("th", null, c)));
    const b = t.createTBody();
    for (const r of righe) {
      const tr = b.insertRow();
      if (r.classe) tr.className = r.classe;
      r.celle.forEach((c, i) => tr.appendChild(h(i ? "td" : "th", i ? "num" : null, c)));
    }
    box.appendChild(t);
    return box;
  }
  const descrGruppo = (g) => `«${g.nome}» (${g.da}–${g.a}, ore ${g.oraDa}–${g.oraA}${g.giorni === "feriali" ? ", feriali" : ""}, ${g.anni ? (g.anni === 1 ? "ultimo anno" : `ultimi ${g.anni} anni`) : "tutta la serie"})`;
  const pc = (v) => `${fmt(v, v % 1 ? 1 : 0)} %`;

  function blocco(s) {
    const r = st[s].ris, d = DEF[s];
    const sez = h("section", `latenti-risultato stagione-${s}`);
    sez.appendChild(h("h3", null, `${d.nome}: ${d.titolo} dell'aria esterna`));
    if (!r || !r.oreGruppo) { sez.appendChild(h("p", "aiuto", "Nessuna ora nel gruppo.")); return sez; }
    const k = 1000 / st.V, o = r.obiettivo;
    sez.appendChild(h("p", "aiuto", `Gruppo ${descrGruppo(r.gruppo)}: ${fmt(r.oreGruppo)} ore valide, ${fmt(r.anni, 1)} anni. Obiettivo ${fmt(o.t, o.t % 1 ? 1 : 0)} °C, ${fmt(o.ur)} % `
      + `(${s === "estate" ? "massima" : "minima"}): x = ${fmt(o.xg, 2)} g/kg. Portata ${fmt(st.V)} m³/h (ṁ media ${fmt(r.portataMedia, 3)} kg/s di aria secca).`));
    const lvPc = pc(r.livello);                              // «nell'1 %», «nell'8 %», «nell'11 %», «nel 5 %»
    const lvTesto = `superata solo ${/^(8|1[ ,]|11[ ,])/.test(lvPc) ? "nell'" : "nel "}${lvPc} delle ore del gruppo`;
    const cifre = h("div", "cifre");
    cifre.append(
      cifra(fmt(r.oreAnno), "ore/anno", d.ore, `${fmt(r.quota * 100, 1)} % delle ore del gruppo`),
      cifra(fmt(r.energiaAnno), "kWh/anno", d.energia, `${fmt(r.energiaAnno * k)} kWh/anno per 1.000 m³/h`),
      cifra(fmt(r.picco, 1), "kW", "potenza massima", `di progetto ${fmt(r.piccoLivello, 1)} kW (${lvTesto}); per 1.000 m³/h: ${fmt(r.picco * k, 2)} e ${fmt(r.piccoLivello * k, 2)} kW`),
      s === "estate"
        ? cifra(fmt(r.acquaAnno), "kg/anno", d.acqua, `al massimo ${fmt(r.acquaPicco, 1)} kg/h`)
        : cifra(fmt(r.acquaAnno / 1000, 2), "m³/anno", d.acqua, `al massimo ${fmt(r.acquaPicco, 1)} kg/h`),
    );
    sez.appendChild(cifre);
    const righe = [
      [d.ore, "ore", r.oreAnno, r.ore, null, 0],
      [`${d.energia} (${d.r})`, "kWh", r.energiaAnno, r.energia, r.energiaAnno * k, 0],
      [d.acqua, "kg", r.acquaAnno, r.acqua, r.acquaAnno * k, 0],
      [d.sensibile, "kWh", r.sensibileAnno, r.sensibile, r.sensibileAnno * k, 0],
      [d.totale, "kWh", r.totaleAnno, r.totale, r.totaleAnno * k, 0],
    ].map(([n, u, a, tot, k1, dd]) => ({ celle: [`${n} (${u})`, fmt(a, dd), k1 === null ? "—" : fmt(k1, dd), fmt(tot, dd)] }));
    righe.push({ celle: ["potenza massima (kW)", fmt(r.picco, 2), fmt(r.picco * k, 2), ""] });
    righe.push({ celle: [`potenza di progetto, livello ${pc(r.livello)} (kW)`, fmt(r.piccoLivello, 2), fmt(r.piccoLivello * k, 2), ""] });
    righe.push({ celle: ["SHR dell'aria esterna (sensibile / sensibile + latente)", fmt(r.shr, 2), "", ""] });
    sez.appendChild(tabella(["Grandezza", "all'anno", "per 1.000 m³/h", `nel periodo (${fmt(r.anni, 1)} anni)`], righe, "latenti-sintesi-tab"));
    const det = h("details", "latenti-classi");
    det.appendChild(h("summary", null, `Ore per classe di Δx (${s === "estate" ? "x esterna − x obiettivo" : "x obiettivo − x esterna"})`));
    let cum = 0;
    const totOre = r.classi.reduce((a, c) => a + c.ore, 0);
    const rc = [];
    for (let i = r.classi.length - 1; i >= 0; i--) { cum += r.classi[i].ore; r.classi[i].sopra = cum; }
    r.classi.forEach((c) => rc.push({ celle: [c.a === null ? `≥ ${fmt(c.da)} g/kg` : `${fmt(c.da)}–${fmt(c.a)} g/kg`, fmt(c.ore), fmt(totOre ? c.ore / totOre * 100 : 0, 1), fmt(c.energia), fmt(c.sopra)] }));
    det.appendChild(tabella(["Δx", "ore/anno", "% delle ore trattate", "kWh/anno", "ore/anno con Δx almeno così"], rc));
    sez.appendChild(det);
    return sez;
  }

  function risultati() {
    const box = $("aria-risultati"), serie = S.serie();
    $("passo-risultati").hidden = !serie;
    if (!serie) { box.innerHTML = ""; return; }
    box.innerHTML = "";
    if (serie.sintetica) box.appendChild(h("p", "messaggio attenzione", "Dati sintetici di prova: i numeri servono solo a vedere come funziona la pagina."));
    box.append(blocco("estate"), blocco("inverno"));
    // curva di durata
    box.appendChild(h("h3", null, "Curva di durata: ore all'anno sopra ogni potenza"));
    box.appendChild(h("p", "aiuto", "Per ogni potenza (in verticale) quante ore all'anno la deumidificazione (blu) o l'umidificazione (rosso) la richiedono o la superano. L'area sotto la curva è l'energia all'anno."));
    const g = h("div", "grafico latenti-curva");
    g.id = "grafico-durata";
    box.appendChild(g);
    if (GR) GR.registra(g, (dest, m) => disegnaCurva(dest, m), { titolo: `Curva di durata – ${serie.comune || ""}`, adatta: true });
    else disegnaCurva(g, null);
    // mesi
    box.appendChild(h("h3", null, "Mese per mese (anno medio)"));
    const E = st.estate.ris, I = st.inverno.ris;
    const rm = [];
    let tot = [0, 0, 0, 0, 0, 0];
    for (let k = 0; k < 12; k++) {
      const e = E ? E.mesi[k] : null, i = I ? I.mesi[k] : null;
      const v = [e ? e.ore : 0, e ? e.energia : 0, e ? e.acqua : 0, i ? i.ore : 0, i ? i.energia : 0, i ? i.acqua : 0];
      tot = tot.map((a, j) => a + v[j]);
      rm.push({ celle: [MESI[k], ...v.map((x) => fmt(x))] });
    }
    rm.push({ classe: "totale", celle: ["anno", ...tot.map((x) => fmt(x))] });
    box.appendChild(tabella(["Mese", "Estate ore", "kWh latenti", "condensa kg", "Inverno ore", "kWh vapore", "acqua kg"], rm, "latenti-mesi"));
    box.appendChild(h("p", "aiuto", `Valori medi all'anno con ${fmt(st.V)} m³/h di aria esterna; ogni stagione conta solo le ore del suo gruppo.`));
    const sc = h("div", "scarica");
    const b1 = h("button", "bottone secondario", "Scarica i risultati (CSV)"); b1.type = "button"; b1.id = "lat-csv";
    b1.addEventListener("click", scaricaCsv);
    sc.appendChild(b1);
    box.appendChild(sc);
    const regole = h("details", "latenti-regole");
    regole.appendChild(h("summary", null, "Regole del calcolo"));
    regole.insertAdjacentHTML("beforeend", `<ul>
<li><b>Estate</b>: un'ora richiede deumidificazione quando l'umidità specifica esterna x<sub>e</sub> supera quella della condizione interna x<sub>t</sub> (T e UR obiettivo, con l'UR come <b>massimo</b>). Energia latente = ṁ·(x<sub>e</sub> − x<sub>t</sub>)·2501 kJ/kg; condensa = ṁ·(x<sub>e</sub> − x<sub>t</sub>).</li>
<li><b>Inverno</b>: un'ora richiede umidificazione a vapore quando x<sub>e</sub> è sotto x<sub>t</sub> (UR obiettivo come <b>minimo</b>). Energia = ṁ·(x<sub>t</sub> − x<sub>e</sub>)·2676 kJ/kg (entalpia del vapore, come il foglio Excel); acqua = ṁ·(x<sub>t</sub> − x<sub>e</sub>).</li>
<li>ṁ (aria secca) = portata in volume / volume specifico di riferimento: con «aria esterna» il volume specifico è quello dell'aria esterna di ogni ora. Ogni ora vale un'ora: i kW sono anche i kWh di quell'ora.</li>
<li>Per contesto: parte sensibile ṁ·(1,006 + 1,86·x<sub>e</sub>)·ΔT per portare l'aria esterna alla T interna, totale ṁ·Δh quando è positivo (le ore calde e secche possono avere Δh negativo, per questo il totale non è la somma delle parti); SHR = sensibile / (sensibile + latente).</li>
<li>«All'anno» = somma sulle ore del gruppo divisa per gli anni del gruppo. Potenza di progetto = potenza superata solo nel livello scelto delle ore del gruppo (al passo 4). Sono statistiche della serie oraria del comune, non valori di norma.</li>
<li>È il carico dell'aria esterna da sola: non comprende il carico latente interno (persone, processi) né il recupero di calore o umidità.</li></ul>`);
    box.appendChild(regole);
  }

  function disegnaCurva(dest, mis) {
    const NS = "http://www.w3.org/2000/svg";
    const W = mis && mis.riquadro ? mis.larghezza : Math.max(300, Math.min(900, dest.clientWidth || 620)), H = mis && mis.riquadro ? mis.altezza : 250;
    const el = (tag, a, p) => { const e = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(a)) { if ((k === "fill" || k === "stroke") && String(v).startsWith("var(")) e.style.setProperty(k, v); else e.setAttribute(k, v); } if (p) p.appendChild(e); return e; };
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Curva di durata delle potenze di deumidificazione e di umidificazione" }, dest);
    const curve = ["estate", "inverno"].map((s) => ({ s, c: st[s].ris ? st[s].ris.curva : [] })).filter((q) => q.c.length);
    const sx = 50, dx = 12, su = 12, gi = 34;
    if (!curve.length) { const t = el("text", { x: W / 2, y: H / 2, "text-anchor": "middle", "font-size": 12, fill: "var(--tenue)" }, svg); t.textContent = "Nessuna ora da trattare con queste condizioni."; return; }
    const xMax = passoBello(Math.max(...curve.map((q) => q.c[q.c.length - 1].ore)), true), yMax = passoBello(Math.max(...curve.map((q) => q.c[0].kW)) * 1.05, true);
    const X = (v) => sx + (W - sx - dx) * v / xMax, Y = (v) => su + (H - su - gi) * (1 - v / yMax);
    const tick = (max) => { const p = passoBello(max / 5, false); const a = []; for (let v = 0; v <= max + 1e-9; v += p) a.push(v); return a; };
    for (const v of tick(yMax)) {
      el("line", { x1: sx, x2: W - dx, y1: Y(v), y2: Y(v), stroke: "var(--linea)", "stroke-width": 1 }, svg);
      const t = el("text", { x: sx - 6, y: Y(v) + 4, "text-anchor": "end", "font-size": 11, fill: "var(--tenue)" }, svg); t.textContent = fmt(v, v % 1 ? (v * 10 % 1 ? 2 : 1) : 0);
    }
    for (const v of tick(xMax)) {
      const t = el("text", { x: X(v), y: H - gi + 16, "text-anchor": "middle", "font-size": 11, fill: "var(--tenue)" }, svg); t.textContent = fmt(v);
    }
    const ty = el("text", { x: 4, y: su - 2 + 8, "font-size": 11, fill: "var(--tenue)" }, svg); ty.textContent = "kW";
    const tx = el("text", { x: W - dx, y: H - 4, "text-anchor": "end", "font-size": 11, fill: "var(--tenue)" }, svg); tx.textContent = "ore all'anno con potenza almeno pari";
    for (const q of curve) {
      const pts = [`${X(0)},${Y(q.c[0].kW)}`, ...q.c.map((p) => `${X(p.ore).toFixed(1)},${Y(p.kW).toFixed(1)}`)];
      el("polyline", { points: pts.join(" "), fill: "none", stroke: colore(q.s), "stroke-width": 2.4, "stroke-linejoin": "round" }, svg);
    }
    // punti osservabili
    const punti = [];
    const valore = (c, v) => { for (const p of c) if (p.ore >= v) return p.kW; return null; };
    for (let j = 0; j <= 60; j++) {
      const v = xMax * j / 60, righe = [], segni = [];
      for (const q of curve) {
        const k = valore(q.c, v);
        if (k === null) continue;
        righe.push([colore(q.s), `${DEF[q.s].nome}: ${fmt(k, 2)} kW o più`]);
        segni.push([X(v), Y(k), colore(q.s)]);
      }
      if (righe.length) punti.push({ x: X(v), titolo: `${fmt(v)} ore all'anno`, righe, segni });
    }
    if (GR && GR.osserva) GR.osserva(svg, punti, { area: [sx, su, W - dx, H - gi] });
    const leg = h("div", "latenti-legenda");
    for (const q of curve) { const s = h("span"); const c = h("i"); c.style.background = colore(q.s); s.append(c, ` ${DEF[q.s].nome}: ${q.s === "estate" ? "deumidificazione (latente)" : "umidificazione a vapore"}`); leg.appendChild(s); }
    dest.appendChild(leg);
  }
  // valore «tondo» (1, 2, 2,5, 5 × 10^n) sopra (arrotonda in su) o vicino
  function passoBello(v, su) {
    if (!(v > 0)) return 1;
    const e = Math.pow(10, Math.floor(Math.log10(v))), f = v / e;
    const scelte = su ? [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10] : [1, 2, 2.5, 5, 10];
    for (const c of scelte) if (su ? f <= c + 1e-9 : f <= c * 1.25) return c * e;
    return 10 * e;
  }

  function scaricaCsv() {
    const serie = S.serie();
    if (!serie) return;
    const c = (v, d = 3) => (Number.isFinite(v) ? String(+v.toFixed(d)).replace(".", ",") : "");
    const righe = [];
    righe.push(`EuGEnio – Carichi latenti dell'aria esterna (sperimentale);${new Date().toLocaleDateString("it-IT")}`);
    righe.push(`Comune;${serie.comune || ""} (${serie.istat || ""})`, `Serie;${serie.fonte}${serie.sintetica ? " – DATI SINTETICI DI PROVA, NON REALI" : ""}`,
      `Pressione (Pa);${c(serie.p, 0)}`, `Portata aria esterna (m³/h);${c(st.V, 1)}`, `Riferimento della portata;${RIF[st.rif]}`, "");
    righe.push("Stagione;Gruppo;T obiettivo (°C);UR obiettivo (%);x obiettivo (g/kg);h obiettivo (kJ/kg);anni;ore del gruppo;ore trattate;ore/anno;"
      + "energia kWh/anno;energia kWh nel periodo;acqua kg/anno;sensibile kWh/anno;totale kWh/anno;potenza max kW;livello %;potenza di progetto kW;SHR;kWh/anno per 1000 m³/h;kW di progetto per 1000 m³/h");
    for (const s of ["estate", "inverno"]) {
      const r = st[s].ris;
      if (!r) continue;
      const k = 1000 / st.V;
      righe.push([s === "estate" ? "estate (deumidificazione)" : "inverno (umidificazione a vapore)", descrGruppo(r.gruppo).replace(/;/g, ","), c(r.obiettivo.t, 1), c(r.obiettivo.ur, 0),
        c(r.obiettivo.xg, 3), c(r.obiettivo.h, 2), c(r.anni, 2), r.oreGruppo, r.ore, c(r.oreAnno, 1), c(r.energiaAnno, 1), c(r.energia, 1), c(r.acquaAnno, 1),
        c(r.sensibileAnno, 1), c(r.totaleAnno, 1), c(r.picco, 3), c(r.livello, 2), c(r.piccoLivello, 3), c(r.shr, 3), c(r.energiaAnno * k, 1), c(r.piccoLivello * k, 3)].join(";"));
    }
    righe.push("", "Mese per mese (anno medio);");
    righe.push("mese;estate ore;estate kWh latenti;estate condensa kg;estate sensibile kWh;inverno ore;inverno kWh vapore;inverno acqua kg;inverno sensibile kWh");
    for (let k = 0; k < 12; k++) {
      const e = st.estate.ris && st.estate.ris.mesi[k], i = st.inverno.ris && st.inverno.ris.mesi[k];
      righe.push([MESI[k], ...(e ? [e.ore, e.energia, e.acqua, e.sensibile] : [0, 0, 0, 0]), ...(i ? [i.ore, i.energia, i.acqua, i.sensibile] : [0, 0, 0, 0])].map((v, j) => (j ? c(v, 1) : v)).join(";"));
    }
    for (const s of ["estate", "inverno"]) {
      const r = st[s].ris;
      if (!r) continue;
      righe.push("", `${DEF[s].nome}: ore per classe di Δx (g/kg);`, "da g/kg;a g/kg;ore/anno;kWh/anno");
      r.classi.forEach((q) => righe.push([c(q.da, 1), q.a === null ? "" : c(q.a, 1), c(q.ore, 1), c(q.energia, 1)].join(";")));
      righe.push("", `${DEF[s].nome}: curva di durata;`, "ore/anno;kW");
      r.curva.forEach((q) => righe.push(`${c(q.ore, 2)};${c(q.kW, 4)}`));
    }
    righe.push("", "Regole;Estate: ore con x esterna > x obiettivo, energia = ṁ·Δx·2501 kJ/kg. Inverno: ore con x esterna < x obiettivo, energia = ṁ·Δx·2676 kJ/kg. Statistiche della serie oraria, non valori di norma.",
      "Fonte;EuGEnio – eugenio.statocritico.it (CC BY 4.0)");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob(["﻿" + righe.join("\r\n")], { type: "text/csv;charset=utf-8" }));
    a.download = `eugenio-carichi-latenti-${(serie.comune || "comune").toLowerCase().replace(/[^a-z0-9]+/g, "-")}.csv`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  // ---------------------------------------------------------------- collegamenti
  S.su((d) => {
    D.titolo(d.serie ? `${titolo} – ${d.comune}` : titolo);
    if (d.serie) D.pressione(d.serie.p);
    for (const s of ["estate", "inverno"]) { V[s].G.zona(d.zona); V[s].G.serie(d.serie); }
    if (!d.serie) ricalcolaTutto();
  });
  L.su(() => { if (S.serie()) ricalcolaTutto(); });
  document.addEventListener("eugenio:aspetto", () => { if (S.serie()) programmaRisultati(); });
  ricalcolaTutto();

  window.EUGENIO_ARIA_PAGINA = {
    diagramma: D, scelta: S, livello: L, gruppi: { estate: V.estate.G, inverno: V.inverno.G },
    risultati: () => ({ estate: st.estate.ris, inverno: st.inverno.ris }),
    obiettivo: (s, t, ur) => {
      if (!V[s]) return null;
      if (Number.isFinite(t)) { st[s].t = t; V[s].ct.imposta(t); }
      if (Number.isFinite(ur)) { st[s].ur = ur; V[s].cu.imposta(ur); }
      proprieta(s); ricalcola(s); return st[s].ris;
    },
  };
})(typeof self !== "undefined" ? self : globalThis);
