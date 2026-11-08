"use strict";
// Analisi del § 9 che non usano norme UNI, nel codice pubblico (05/11/2026; prima nel modulo privato, solo come
// struttura): **13** Cambiamento climatico (prima «Clima che cambia»), **7** Comunità energetiche, **9** cielo visibile (le funzioni di calcolo sono qui,
// la scena 3D è in edificio3d.js). Solo statistica e geometria di base; nessun coefficiente di norme, nessun dato GME o
// GSE, nessun prezzo: l'energia condivisa di una CER è un conto di energia, gli incentivi dipendono dai prezzi di mercato.
//
//   tendenza(x, y)        → { pendenza, intercetta, errore, r2, sen, mk: { s, z, p }, n }   (minimi quadrati, Theil–Sen,
//                           Mann–Kendall con la varianza senza correzione per i valori uguali)
//   proietta(t, x)        → { valore, basso, alto }   estrapolazione della retta con l'intervallo al 95 % della previsione
//   consumoAnnuo(firma, gg) consumo = 12 · base + pendenza · GG (firma mensile: consumo del mese = base + pendenza · GG)
//   condivisa(righe)      → energia condivisa per cabina e ora: min(Σ immissioni, Σ prelievi) delle sedi della stessa
//                           cabina primaria (D.Lgs. 199/2021, art. 31 e 32; DM MASE 7/12/2023 n. 414)
//   leggiCer(testo)       → righe { ora, sede, cabina, prelievo, immissione } da un CSV in formato lungo
(function (radice) {
  function tendenza(x, y) {
    const p = x.map((v, i) => [+v, +y[i]]).filter(([a, b]) => Number.isFinite(a) && Number.isFinite(b));
    const n = p.length;
    if (n < 3) return null;
    const mx = p.reduce((s, q) => s + q[0], 0) / n, my = p.reduce((s, q) => s + q[1], 0) / n;
    let sxx = 0, sxy = 0, syy = 0;
    for (const [a, b] of p) { sxx += (a - mx) ** 2; sxy += (a - mx) * (b - my); syy += (b - my) ** 2; }
    const b1 = sxy / sxx, b0 = my - b1 * mx;
    const res = p.reduce((s, [a, b]) => s + (b - b0 - b1 * a) ** 2, 0);
    const s2 = res / (n - 2);
    // Theil–Sen: mediana delle pendenze tra tutte le coppie
    const pend = [];
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) if (p[j][0] !== p[i][0]) pend.push((p[j][1] - p[i][1]) / (p[j][0] - p[i][0]));
    pend.sort((a, b) => a - b);
    const med = pend.length % 2 ? pend[(pend.length - 1) / 2] : (pend[pend.length / 2 - 1] + pend[pend.length / 2]) / 2;
    // Mann–Kendall
    let S = 0;
    const q = [...p].sort((a, b) => a[0] - b[0]);
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) S += Math.sign(q[j][1] - q[i][1]);
    const vs = n * (n - 1) * (2 * n + 5) / 18, z = S > 0 ? (S - 1) / Math.sqrt(vs) : S < 0 ? (S + 1) / Math.sqrt(vs) : 0;
    return { n, pendenza: b1, intercetta: b0, errore: Math.sqrt(s2 / sxx), r2: syy > 0 ? 1 - res / syy : null, sen: med,
      mk: { s: S, z, p: 2 * (1 - fiNormale(Math.abs(z))) }, _s2: s2, _mx: mx, _sxx: sxx };
  }
  function fiNormale(z) {      // funzione di ripartizione normale (Abramowitz–Stegun 26.2.17)
    const t = 1 / (1 + 0.2316419 * z), d = 0.3989423 * Math.exp(-z * z / 2);
    const p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))));
    return 1 - p;
  }
  function proietta(t, x) {
    if (!t) return null;
    const v = t.intercetta + t.pendenza * x;
    const se = Math.sqrt(t._s2 * (1 + 1 / t.n + (x - t._mx) ** 2 / t._sxx));
    return { valore: v, basso: v - 1.96 * se, alto: v + 1.96 * se };
  }
  function consumoAnnuo(firma, gg) {
    if (!firma || !Number.isFinite(firma.base) || !Number.isFinite(firma.pendenza) || !Number.isFinite(gg)) return null;
    return 12 * firma.base + firma.pendenza * gg;
  }

  // ------------------------------------------------------------------ CER (analisi 7)
  const num = (s) => { if (typeof s === "number") return s; const t = String(s == null ? "" : s).trim().replace(/\s/g, "");
    if (!t) return NaN; return Number(t.includes(",") ? t.replace(/\./g, "").replace(",", ".") : t); };
  function leggiCer(testo) {
    const righe = String(testo).replace(/^﻿/, "").split(/\r?\n/).filter((r) => r.trim() && !r.startsWith("#"));
    if (righe.length < 2) throw new Error("il file non ha righe di dati");
    const sep = (righe[0].match(/;/g) || []).length >= (righe[0].match(/,/g) || []).length ? ";" : ",";
    const tit = righe[0].split(sep).map((x) => x.trim().toLowerCase().replace(/\s*\(.*\)$/, ""));
    const c = (...n) => tit.findIndex((t) => n.includes(t));
    const io = c("ora", "data_ora", "data e ora", "timestamp"), is = c("sede", "pod", "utenza"), ic = c("cabina", "cabina_primaria"),
      ip = c("prelievo", "prelievo_kwh", "prelevata", "consumo_kwh"), ii = c("immissione", "immissione_kwh", "immessa");
    if ([io, is, ic, ip, ii].some((x) => x < 0)) throw new Error("servono le colonne ora, sede, cabina, prelievo e immissione (kWh)");
    const out = [];
    for (const r of righe.slice(1)) {
      const v = r.split(sep);
      const p = num(v[ip]), m = num(v[ii]);
      if (!v[io] || !v[is]) continue;
      out.push({ ora: v[io].trim(), sede: v[is].trim(), cabina: (v[ic] || "").trim() || "—", prelievo: Number.isFinite(p) ? p : 0,
        immissione: Number.isFinite(m) ? m : 0 });
    }
    if (!out.length) throw new Error("nessuna riga valida");
    return out;
  }
  function condivisa(righe) {
    const cab = new Map();
    for (const r of righe) {
      if (!cab.has(r.cabina)) cab.set(r.cabina, { ore: new Map(), sedi: new Map() });
      const c = cab.get(r.cabina);
      const o = c.ore.get(r.ora) || { p: 0, m: 0, sedi: [] };
      o.p += r.prelievo; o.m += r.immissione; o.sedi.push(r);
      c.ore.set(r.ora, o);
      const s = c.sedi.get(r.sede) || { prelievo: 0, immissione: 0, quota: 0 };
      s.prelievo += r.prelievo; s.immissione += r.immissione; c.sedi.set(r.sede, s);
    }
    const out = [];
    for (const [nome, c] of cab) {
      let cond = 0, P = 0, M = 0;
      for (const o of c.ore.values()) {
        const x = Math.min(o.p, o.m);
        cond += x; P += o.p; M += o.m;
        // quota della condivisa attribuita a chi preleva, in proporzione al prelievo dell'ora (ripartizione di esempio:
        // la regola vera la decide lo statuto della comunità)
        if (o.p > 0) for (const r of o.sedi) c.sedi.get(r.sede).quota += x * r.prelievo / o.p;
      }
      out.push({ cabina: nome, ore: c.ore.size, prelievo: P, immissione: M, condivisa: cond,
        quota_su_immissione: M > 0 ? cond / M : null, quota_su_prelievo: P > 0 ? cond / P : null,
        sedi: [...c.sedi].map(([sede, s]) => ({ sede, ...s })) });
    }
    return out.sort((a, b) => b.condivisa - a.condivisa);
  }
  const API = { tendenza, proietta, consumoAnnuo, leggiCer, condivisa, fiNormale };
  radice.EUGENIO_ANALISI = API;
  if (typeof module !== "undefined" && module.exports) { module.exports = API; return; }

  // ------------------------------------------------------------------ pagine
  const $ = (id) => document.getElementById(id);
  const fmt = (v, d = 0) => (Number.isFinite(+v) ? (+v).toLocaleString("it-IT", { maximumFractionDigits: d, minimumFractionDigits: d }) : "—");
  const segno = (v, d = 0) => (Number.isFinite(+v) ? (v > 0 ? "+" : "") + fmt(v, d) : "—");
  const h = (tag, cls, t) => { const e = document.createElement(tag); if (cls) e.className = cls; if (t !== undefined) e.textContent = t; return e; };
  const msg = (id, t, err = false) => { const m = $(id); if (m) { m.textContent = t; m.classList.toggle("errore", err); } };
  const G = window.EUGENIO_GRAFICI;

  // ---- analisi 13: Cambiamento climatico (Clima e meteo)
  if ($("clima-comune")) {
    const st = { comuni: null, dati: null };
    const V = (() => { try { return new URL(document.currentScript.src).search; } catch { return ""; } })();
    async function comuni() {
      if (st.comuni) return st.comuni;
      try { const r = await fetch("/api/comuni"); st.comuni = r.ok ? await r.json() : []; } catch { st.comuni = []; }
      const dl = $("elenco-comuni");
      if (dl) st.comuni.slice(0, 9000).forEach((c) => { const o = document.createElement("option"); o.value = `${c.nome} (${c.provincia || c.istat})`; dl.appendChild(o); });
      return st.comuni;
    }
    async function istatDa(testo) {
      const t = String(testo || "").trim();
      if (/^\d{6}$/.test(t)) return t;
      const l = await comuni(), n = t.toLowerCase().replace(/\s*\(.*\)$/, "");
      const c = l.find((x) => x.nome.toLowerCase() === n);
      return c ? String(c.istat).padStart(6, "0") : null;
    }
    async function carica() {
      const istat = await istatDa($("clima-comune").value);
      if (!istat) return msg("messaggio-clima", "Comune non trovato: scrivi il nome come nell'elenco o il codice ISTAT di 6 cifre.", true);
      msg("messaggio-clima", "Carico il clima dal 1940 del comune…");
      try {
        const reg = await (await fetch(`dati/clima/regioni.json${V}`)).json();
        const rr = reg[istat] || reg[String(+istat)];
        if (!rr) throw new Error("comune senza dati del clima dal 1940");
        st.dati = await (await fetch(`dati/clima/${rr}/${istat}.json${V}`)).json();
      } catch (e) {
        st.dati = null;
        return msg("messaggio-clima", `Il clima dal 1940 di questo comune non è disponibile qui (${e.message || e}): sul server vero i file stanno in dati/clima/.`, true);
      }
      calcola();
    }
    function calcola() {
      const d = st.dati; if (!d) return;
      const S = d.stagioni, x = S.gg_zona.map((_, i) => S.da + i), y = S.gg_zona;
      const dal = +$("clima-dal").value || x[0];
      const xs = [], ys = [];
      x.forEach((v, i) => { if (v >= dal && Number.isFinite(y[i])) { xs.push(v); ys.push(y[i]); } });
      const t = tendenza(xs, ys);
      if (!t) return msg("messaggio-clima", "Troppo poche stagioni nel periodo scelto.", true);
      const anni = [2030, 2040, 2050], firma = { base: Number(String($("firma-base").value).replace(",", ".")), pendenza: Number(String($("firma-pendenza").value).replace(",", ".")) };
      const ultimo = xs[xs.length - 1], media10 = ys.slice(-10).reduce((s, v) => s + v, 0) / Math.min(10, ys.length);
      msg("messaggio-clima", `${d.nome || "Comune"}: ${t.n} stagioni dal ${xs[0]}/${String(xs[0] + 1).slice(2)}; tendenza ${segno(10 * t.pendenza)} GG per decennio`
        + ` (Theil–Sen ${segno(10 * t.sen)}; Mann–Kendall p = ${fmt(t.mk.p, 3)}${t.mk.p < 0.05 ? ", significativa" : ", non significativa al 5 %"}).`);
      const box = $("risultati-clima"); box.innerHTML = "";
      const tab = h("table", "mensili"), r1 = tab.createTHead().insertRow();
      ["Stagione", "GG (tendenza)", "intervallo al 95 %", "consumo atteso con la firma"].forEach((c) => r1.appendChild(h("th", null, c)));
      const b = tab.createTBody(), righe = [];
      const conRif = consumoAnnuo(firma, media10);
      const r0 = b.insertRow();
      [`media delle ultime 10 (fino al ${ultimo}/${String(ultimo + 1).slice(2)})`, fmt(media10), "—", conRif === null ? "—" : fmt(conRif)].forEach((v, i) => r0.appendChild(h(i ? "td" : "th", i ? "num" : null, v)));
      for (const a of anni) {
        const p = proietta(t, a), c = consumoAnnuo(firma, p.valore);
        righe.push({ a, p, c });
        const r = b.insertRow();
        [`${a}/${String(a + 1).slice(2)}`, fmt(p.valore), `${fmt(p.basso)} – ${fmt(p.alto)}`,
          c === null ? "—" : `${fmt(c)} (${segno(100 * (c / conRif - 1), 1)} %)`].forEach((v, i) => r.appendChild(h(i ? "td" : "th", i ? "num" : null, v)));
      }
      box.appendChild(tab);
      st.ultimo = { d, t, righe, media10, firma };
      if (G) G.registra($("grafico-clima"), (dest, mis) => grafico(dest, mis, xs, ys, t, righe), { titolo: "Gradi giorno dal 1940 e tendenza", adatta: true });
      $("passo-clima-risultati").hidden = false;
    }
    function grafico(dest, mis, xs, ys, t, righe) {
      const NS = "http://www.w3.org/2000/svg", W = mis && mis.riquadro ? mis.larghezza : Math.max(320, Math.min(900, dest.clientWidth || 620)),
        H = mis && mis.riquadro ? mis.altezza : 240;
      const el = (tag, a, p) => { const e = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(a)) { if ((k === "fill" || k === "stroke") && String(v).startsWith("var(")) e.style.setProperty(k, v); else e.setAttribute(k, v); } if (p) p.appendChild(e); return e; };
      const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Gradi giorno dal 1940 e tendenza" }, dest);
      const x0 = xs[0], x1 = 2050, ymax = Math.max(...ys, ...righe.map((r) => r.p.alto)) * 1.05, ymin = Math.min(...ys, ...righe.map((r) => r.p.basso)) * 0.9;
      const sx = 46, sy = 10, X = (v) => sx + (W - sx - 10) * (v - x0) / (x1 - x0), Y = (v) => sy + (H - sy - 26) * (1 - (v - ymin) / (ymax - ymin));
      const punti = [];
      xs.forEach((v, i) => { const c = el("circle", { cx: X(v), cy: Y(ys[i]), r: 2.4, fill: "var(--serie-1)" }, svg);
        punti.push({ x: X(v), titolo: `Stagione ${v}/${String(v + 1).slice(2)}`, righe: [["var(--serie-1)", `${fmt(ys[i])} GG`]], elementi: [c] }); });
      el("line", { x1: X(xs[0]), y1: Y(t.intercetta + t.pendenza * xs[0]), x2: X(x1), y2: Y(t.intercetta + t.pendenza * x1), stroke: "var(--inchiostro)", "stroke-dasharray": "5 4" }, svg);
      for (const r of righe) el("line", { x1: X(r.a), x2: X(r.a), y1: Y(r.p.basso), y2: Y(r.p.alto), stroke: "var(--serie-2)", "stroke-width": 3 }, svg);
      for (let a = Math.ceil(x0 / 10) * 10; a <= x1; a += 10) { const tt = el("text", { x: X(a), y: H - 8, "text-anchor": "middle", "font-size": 11, fill: "var(--tenue)" }, svg); tt.textContent = a; }
      const ty = el("text", { x: 2, y: 14, "font-size": 11, fill: "var(--tenue)" }, svg); ty.textContent = `${fmt(ymax)} GG`;
      if (G && G.osserva) G.osserva(svg, punti, { area: [sx, sy, W - 10, H - 26] });
    }
    $("clima-carica").addEventListener("click", carica);
    ["clima-dal", "firma-base", "firma-pendenza"].forEach((id) => $(id).addEventListener("change", calcola));
    const q = new URLSearchParams(location.search).get("istat");
    if (q) { $("clima-comune").value = q; carica(); }
    $("clima-comune").addEventListener("focus", comuni, { once: true });
  }

  // ---- analisi 7: Comunità energetiche
  if ($("cer-file")) {
    const st = { righe: null, esito: null };
    async function leggi(f) {
      try {
        const T = window.EUGENIO_TABELLE;
        const testo = T ? (await T.leggi(f)).testo : await f.text();     // CSV nel browser; Excel/ODS convertiti come altrove
        st.righe = leggiCer(testo);
        mostra(f.name);
      } catch (e) { msg("messaggio-cer", `File non letto: ${e.message || e}.`, true); }
    }
    function mostra(nome) {
      const es = condivisa(st.righe); st.esito = es;
      const ore = new Set(st.righe.map((r) => r.ora)).size, sedi = new Set(st.righe.map((r) => r.sede)).size;
      msg("messaggio-cer", `${nome}: ${st.righe.length} righe, ${sedi} sedi, ${ore} ore, ${es.length} ${es.length === 1 ? "cabina" : "cabine"}.`);
      const box = $("risultati-cer"); box.innerHTML = "";
      const t = h("table", "mensili"), r1 = t.createTHead().insertRow();
      ["Cabina primaria", "Prelievi (kWh)", "Immissioni (kWh)", "Energia condivisa (kWh)", "% delle immissioni", "% dei prelievi"].forEach((c) => r1.appendChild(h("th", null, c)));
      const b = t.createTBody();
      for (const c of es) {
        const r = b.insertRow();
        [c.cabina, fmt(c.prelievo), fmt(c.immissione), fmt(c.condivisa), fmt(100 * c.quota_su_immissione, 1), fmt(100 * c.quota_su_prelievo, 1)]
          .forEach((v, i) => r.appendChild(h(i ? "td" : "th", i ? "num" : null, v)));
      }
      box.appendChild(t);
      const ts = h("table", "mensili"), s1 = ts.createTHead().insertRow();
      ["Sede", "Cabina", "Prelievi (kWh)", "Immissioni (kWh)", "Condivisa attribuita (kWh)"].forEach((c) => s1.appendChild(h("th", null, c)));
      const bs = ts.createTBody();
      for (const c of es) for (const s of c.sedi) {
        const r = bs.insertRow();
        [s.sede, c.cabina, fmt(s.prelievo), fmt(s.immissione), fmt(s.quota)].forEach((v, i) => r.appendChild(h(i ? "td" : "th", i ? "num" : null, v)));
      }
      $("sedi-cer").innerHTML = ""; $("sedi-cer").appendChild(ts);
      $("passo-cer-risultati").hidden = false;
    }
    $("cer-file").addEventListener("change", (e) => { const f = e.target.files && e.target.files[0]; if (f) leggi(f); });
    $("cer-esempio").addEventListener("click", async () => {
      try { const r = await fetch("esempi/cer_esempio_sintetico.csv"); st.righe = leggiCer(await r.text()); mostra("esempio sintetico (dati inventati)"); }
      catch (e) { msg("messaggio-cer", `Esempio non caricato: ${e.message || e}.`, true); }
    });
  }
})(typeof self !== "undefined" ? self : globalThis);
