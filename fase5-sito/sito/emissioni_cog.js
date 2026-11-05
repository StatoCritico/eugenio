"use strict";
// Cogenerazione › Emissioni (report 18, 05/11/2026): CO₂ del cogeneratore contro quella dell'alternativa separata
// (elettricità dalla rete + calore da una caldaia a gas), con i fattori di emissione di ISPRA (Rapporto 430/2026,
// Tabelle 1.4 e 1.7, CC BY 4.0, in dati/ispra_fattori_emissione.json). Tutto nel browser, nessun dato inviato al server.
// **Nessun dato GME o EEX**: la pagina non usa prezzi, né strategie economiche, né profili di mercato; la scelta del
// fattore della rete (consumi, produzione lorda, termoelettrico) è dell'utente e la pagina li mostra tutti.
//
//   calcola({ elettrica_mwh, calore_mwh, gas_mwh_pci }, { fattore_rete_g_kwh, fattore_gas_t_tj, rendimento_caldaia })
//     → { co2_chp_t, co2_rete_t, co2_caldaia_t, co2_separata_t, evitata_t, evitata_pct, intensita_kg_mwh }
//   daTaglia({ potenza_kwe, ore, rendimento_elettrico, rendimento_termico }) → { elettrica_mwh, calore_mwh, gas_mwh_pci }
(function (radice) {
  const KWH_SMC = (8190 * 4.1868) / 3600;        // pci del gas di ISPRA: 8190 kcal/Sm³ ≈ 9,525 kWh/Sm³
  const TJ_MWH = 277.7778;                        // 1 TJ = 277,78 MWh
  const ETICHETTE = { termoelettrica_lorda_solo_fossili: "produzione termoelettrica lorda, solo fossili",
    termoelettrica_lorda: "produzione termoelettrica lorda", produzione_elettrica_lorda: "produzione elettrica lorda (con le rinnovabili)",
    consumi_elettrici: "consumi elettrici (con perdite di rete e importazioni)" };

  function daTaglia({ potenza_kwe, ore, rendimento_elettrico, rendimento_termico }) {
    if (!(potenza_kwe > 0) || !(ore > 0) || !(rendimento_elettrico > 0 && rendimento_elettrico < 1) || !(rendimento_termico >= 0)
        || rendimento_elettrico + rendimento_termico > 1) return null;
    const e = potenza_kwe * ore / 1000, g = e / rendimento_elettrico;
    return { elettrica_mwh: e, calore_mwh: g * rendimento_termico, gas_mwh_pci: g };
  }
  function calcola(d, f) {
    const e = +d.elettrica_mwh, q = +d.calore_mwh, g = +d.gas_mwh_pci;
    if (!(e >= 0) || !(q >= 0) || !(g > 0) || !(f.fattore_rete_g_kwh > 0) || !(f.fattore_gas_t_tj > 0)
        || !(f.rendimento_caldaia > 0 && f.rendimento_caldaia <= 1.1)) return null;
    const kgGas = f.fattore_gas_t_tj * 1000 / TJ_MWH;     // kg CO₂ per MWh di gas (pci)
    const co2Chp = g * kgGas / 1000;
    const co2Rete = e * f.fattore_rete_g_kwh / 1000;      // MWh × g/kWh = kg… /1000 → t (g/kWh = kg/MWh)
    const co2Caldaia = (q / f.rendimento_caldaia) * kgGas / 1000;
    const sep = co2Rete + co2Caldaia;
    return { co2_chp_t: co2Chp, co2_rete_t: co2Rete, co2_caldaia_t: co2Caldaia, co2_separata_t: sep, evitata_t: sep - co2Chp,
      evitata_pct: sep > 0 ? 100 * (sep - co2Chp) / sep : null, gas_kg_mwh: kgGas,
      rendimento_globale: (e + q) / g, intensita_kg_mwh: (e + q) > 0 ? 1000 * co2Chp / (e + q) : null,
      // fattore della rete sotto il quale il cogeneratore emette più dell'alternativa separata
      soglia_rete_g_kwh: e > 0 ? Math.max(0, (co2Chp - co2Caldaia) * 1000 / e) : null };
  }
  const API = { KWH_SMC, TJ_MWH, ETICHETTE, daTaglia, calcola };
  radice.EUGENIO_EMISSIONI = API;
  if (typeof module !== "undefined" && module.exports) { module.exports = API; return; }

  // ------------------------------------------------------------------ pagina
  const $ = (id) => document.getElementById(id);
  if (!$("calcola-emissioni")) return;
  const fmt = (v, d = 0) => (Number.isFinite(+v) ? (+v).toLocaleString("it-IT", { maximumFractionDigits: d, minimumFractionDigits: d }) : "—");
  const num = (s) => { const t = String(s == null ? "" : s).trim().replace(/\s/g, "").replace(/\./g, "").replace(",", "."); return t === "" ? NaN : Number(t); };
  const h = (tag, cls, t) => { const e = document.createElement(tag); if (cls) e.className = cls; if (t !== undefined) e.textContent = t; return e; };
  const G = window.EUGENIO_GRAFICI;
  const stato = { dati: null, ultimo: null };

  function modo() { const i = document.querySelector('input[name="modo-cog"]:checked'); return i ? i.value : "consuntivo"; }
  function mostraModo() { $("campi-consuntivo").hidden = modo() !== "consuntivo"; $("campi-taglia").hidden = modo() !== "taglia"; }
  document.querySelectorAll('input[name="modo-cog"]').forEach((i) => i.addEventListener("change", mostraModo));

  function riempiAnni() {
    const anni = Object.keys(stato.dati.elettrico_g_kwh.anni).sort().reverse();
    const s = $("anno-fattori"); s.innerHTML = "";
    for (const a of anni) { const o = h("option", null, a + (stato.dati.elettrico_g_kwh.preliminari.includes(a) ? " (preliminare)" : "")); o.value = a; s.appendChild(o); }
    const r = $("fattore-rete"); r.innerHTML = "";
    stato.dati.elettrico_g_kwh.campi.forEach((c) => { const o = h("option", null, ETICHETTE[c] || c); o.value = c; r.appendChild(o); });
    r.value = "consumi_elettrici";
  }
  function fattori() {
    const a = $("anno-fattori").value, el = stato.dati.elettrico_g_kwh, campi = el.campi;
    const anniGas = Object.keys(stato.dati.gas_naturale.anni).sort();
    const ag = anniGas.includes(a) ? a : anniGas.filter((x) => x <= a).pop() || anniGas[0];
    return { anno: a, anno_gas: ag, rete: Object.fromEntries(campi.map((c, i) => [c, el.anni[a][i]])),
      gas_t_tj: stato.dati.gas_naturale.anni[ag].t_co2_tj };
  }
  function ingressi() {
    if (modo() === "taglia") {
      return daTaglia({ potenza_kwe: num($("potenza").value), ore: num($("ore").value),
        rendimento_elettrico: num($("eta-e").value) / 100, rendimento_termico: num($("eta-t").value) / 100 });
    }
    const unita = $("unita-gas").value, gas = num($("gas").value);
    return { elettrica_mwh: num($("elettrica").value), calore_mwh: num($("calore").value),
      gas_mwh_pci: unita === "smc" ? gas * KWH_SMC / 1000 : gas };
  }
  function messaggio(t, errore = false) { const m = $("messaggio-emissioni"); m.textContent = t; m.classList.toggle("errore", errore); }

  function esegui() {
    if (!stato.dati) return messaggio("I fattori di emissione non sono stati caricati: ricarica la pagina.", true);
    const d = ingressi();
    if (!d || !(d.gas_mwh_pci > 0)) return messaggio("Controlla i dati: servono energia elettrica, calore e gas (o potenza, ore e rendimenti, con rendimento elettrico + termico ≤ 100 %).", true);
    const f = fattori(), eta = num($("eta-caldaia").value) / 100, scelto = $("fattore-rete").value;
    const r = calcola(d, { fattore_rete_g_kwh: f.rete[scelto], fattore_gas_t_tj: f.gas_t_tj, rendimento_caldaia: eta });
    if (!r) return messaggio("Controlla il rendimento della caldaia (tra 1 e 110 %).", true);
    stato.ultimo = { d, f, r, eta, scelto };
    messaggio(r.evitata_t >= 0
      ? `Con il fattore della rete scelto il cogeneratore evita ${fmt(r.evitata_t, 1)} t di CO₂ all'anno (${fmt(r.evitata_pct, 1)} % dell'alternativa separata).`
      : `Con il fattore della rete scelto il cogeneratore emette ${fmt(-r.evitata_t, 1)} t di CO₂ all'anno in più dell'alternativa separata.`);
    const box = $("risultati-emissioni"); box.innerHTML = "";
    const t = h("table", "totali"), b = t.createTBody();
    [["Energia elettrica prodotta", `${fmt(d.elettrica_mwh, 1)} MWh`], ["Calore utile", `${fmt(d.calore_mwh, 1)} MWh`],
      ["Gas consumato (pci)", `${fmt(d.gas_mwh_pci, 1)} MWh (${fmt(d.gas_mwh_pci * 1000 / KWH_SMC, 0)} Sm³)`],
      ["Rendimento globale", `${fmt(100 * r.rendimento_globale, 1)} %`],
      ["CO₂ del cogeneratore", `${fmt(r.co2_chp_t, 1)} t`],
      [`CO₂ della rete per la stessa elettricità (${fmt(f.rete[scelto], 1)} g/kWh)`, `${fmt(r.co2_rete_t, 1)} t`],
      [`CO₂ della caldaia per lo stesso calore (rendimento ${fmt(100 * eta, 0)} %)`, `${fmt(r.co2_caldaia_t, 1)} t`],
      ["CO₂ evitata (+) o aggiunta (−)", `${fmt(r.evitata_t, 1)} t (${fmt(r.evitata_pct, 1)} %)`],
      ["Fattore della rete di pareggio", r.soglia_rete_g_kwh !== null ? `${fmt(r.soglia_rete_g_kwh, 0)} g/kWh: con una rete più pulita il cogeneratore emette di più` : "—"]]
      .forEach(([k, v]) => { const tr = b.insertRow(); tr.appendChild(h("th", null, k)); tr.appendChild(h("td", "num", v)); });
    box.appendChild(t);
    // sensibilità: tutti i fattori della rete dell'anno scelto
    const ts = h("table", "mensili"), r1 = ts.createTHead().insertRow();
    ["Fattore della rete (ISPRA, " + f.anno + ")", "g CO₂/kWh", "CO₂ evitata (t)", "%"].forEach((x) => r1.appendChild(h("th", null, x)));
    const bs = ts.createTBody(), righe = [];
    for (const [c, v] of Object.entries(f.rete)) {
      const x = calcola(d, { fattore_rete_g_kwh: v, fattore_gas_t_tj: f.gas_t_tj, rendimento_caldaia: eta });
      righe.push({ c, v, x });
      const tr = bs.insertRow(); if (c === scelto) tr.className = "riga-scelta";
      [ETICHETTE[c], fmt(v, 1), fmt(x.evitata_t, 1), fmt(x.evitata_pct, 1)].forEach((y, i) => tr.appendChild(h(i ? "td" : "th", i ? "num" : null, y)));
    }
    $("sensibilita").innerHTML = ""; $("sensibilita").appendChild(ts);
    if (G) G.registra($("grafico-emissioni"), (dest, mis) => grafico(dest, mis, r), { titolo: "CO₂ del cogeneratore e dell'alternativa separata", adatta: true });
    $("passo-risultati").hidden = false;
  }
  function grafico(dest, mis, r) {
    const NS = "http://www.w3.org/2000/svg", W = mis && mis.riquadro ? mis.larghezza : Math.max(320, Math.min(900, dest.clientWidth || 520)),
      H = mis && mis.riquadro ? mis.altezza : 180;
    const el = (tag, a, p) => { const e = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(a)) e.setAttribute(k, v); if (p) p.appendChild(e); return e; };
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "CO₂ del cogeneratore e dell'alternativa separata" }, dest);
    const max = Math.max(r.co2_chp_t, r.co2_separata_t) || 1, sx = 150, larg = W - sx - 80;
    const barra = (y, valori, titolo) => {
      el("text", { x: 4, y: y + 22, "font-size": 13, fill: "currentColor" }, svg).textContent = titolo;
      let x = sx;
      const elementi = [];
      for (const [v, col] of valori) { const w = larg * v / max; elementi.push(el("rect", { x, y, width: Math.max(0, w), height: 34, fill: col }, svg)); x += w; }
      el("text", { x: x + 6, y: y + 22, "font-size": 13, fill: "currentColor" }, svg).textContent = `${fmt(valori.reduce((s, [v]) => s + v, 0), 1)} t`;
      return elementi;
    };
    // marrone per le emissioni (regola dei colori del 29/10/2026), due toni per rete e caldaia
    const a = barra(30, [[r.co2_chp_t, "#7a4a2b"]], "Cogeneratore");
    const b = barra(110, [[r.co2_rete_t, "#a8724a"], [r.co2_caldaia_t, "#d2a47c"]], "Rete + caldaia");
    if (G && G.osserva) G.osserva(svg, [
      { x: sx + 20, titolo: "Cogeneratore", elementi: a, righe: [["#7a4a2b", `${fmt(r.co2_chp_t, 1)} t CO₂`]] },
      { x: sx + 40, titolo: "Rete + caldaia", elementi: b, righe: [["#a8724a", `rete ${fmt(r.co2_rete_t, 1)} t`], ["#d2a47c", `caldaia ${fmt(r.co2_caldaia_t, 1)} t`]] }],
    { area: [sx, 20, W - 10, H - 20], guida: false });
  }
  $("calcola-emissioni").addEventListener("click", esegui);
  $("scarica-emissioni").addEventListener("click", () => {
    if (!stato.ultimo) return;
    const { d, f, r, eta, scelto } = stato.ultimo, q = (x) => (x === null || x === undefined ? "" : String(x).replace(".", ","));
    const righe = [["voce", "valore", "unità"], ["energia elettrica prodotta", q(d.elettrica_mwh), "MWh"], ["calore utile", q(d.calore_mwh), "MWh"],
      ["gas (pci)", q(d.gas_mwh_pci), "MWh"], ["rendimento caldaia", q(eta), ""], [`fattore rete ${scelto} ${f.anno}`, q(f.rete[scelto]), "g CO2/kWh"],
      [`fattore gas ${f.anno_gas}`, q(f.gas_t_tj), "t CO2/TJ"], ["CO2 cogeneratore", q(r.co2_chp_t), "t"], ["CO2 rete", q(r.co2_rete_t), "t"],
      ["CO2 caldaia", q(r.co2_caldaia_t), "t"], ["CO2 evitata", q(r.evitata_t), "t"]];
    const testo = "﻿" + righe.map((x) => x.join(";")).join("\r\n") + `\r\n\r\n${stato.dati.citazione}, ${stato.dati.licenza}\r\nFonte: EuGEnio – eugenio.statocritico.it (CC BY 4.0)\r\n`;
    const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([testo], { type: "text/csv" })); a.download = "emissioni_cogeneratore.csv";
    document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  });
  (async function avvio() {
    mostraModo();
    try {
      const V = (() => { try { return new URL(document.currentScript.src).search; } catch { return ""; } })();
      const r = await fetch(`dati/ispra_fattori_emissione.json${V}`);
      stato.dati = await r.json();
      riempiAnni();
      $("fonte-fattori").textContent = `${stato.dati.citazione} (${stato.dati.licenza}). Dati 2025 preliminari.`;
    } catch (e) { messaggio("I fattori di emissione non si sono caricati: ricarica la pagina.", true); }
  })();
})(typeof self !== "undefined" ? self : globalThis);
