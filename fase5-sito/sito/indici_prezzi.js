"use strict";
// Statistiche › Indici dei prezzi (11/11/2026). Legge dati/prezzi/indici.json, scritto ogni notte dal worker
// (mercati_energia/prezzi_pubblici.py): per ogni indice l'anno prima e l'anno in corso, gennaio–dicembre.
// Per ogni indice: barre affiancate (anno prima tenue, anno in corso pieno) e tabella con la variazione; il lotto si
// sceglie dalla casella a discesa (Intercent-ER, Consip), la fascia o l'uso con i pulsanti. Nessun PUN né TTF: il file
// non li contiene.
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre",
    "novembre", "dicembre"];
  const INIZIALI = ["G", "F", "M", "A", "M", "G", "L", "A", "S", "O", "N", "D"];
  const COLORE = { elettricita: "var(--prezzi-ele)", gas: "var(--prezzi-gas)" };
  const $ = (id) => document.getElementById(id);
  const scelte = {};      // id dell'indice → { lotto, variante }
  const decimali = (ind) => Number.isInteger(ind.decimali) ? ind.decimali : ind.unita === "€/Smc" ? 4 : 2;   // PSV e PFOR: 4
  const nomeVariante = (v) => v === "F0" ? "Monoraria" : /^F\d$/.test(v) ? `Fascia ${v}` : v;

  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if ((k === "fill" || k === "stroke") && String(v).startsWith("var(")) e.style.setProperty(k, v);
      else e.setAttribute(k, v);
    }
    if (parent) parent.appendChild(e);
    return e;
  }
  function h(tag, cls, testo) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (testo !== undefined && testo !== null) e.textContent = testo;
    return e;
  }
  const num = (x, d = 2) => x === null || x === undefined ? "—"
    : x.toLocaleString("it-IT", { minimumFractionDigits: d, maximumFractionDigits: d });
  const variazione = (prima, ora) => (prima && ora !== null && ora !== undefined && prima !== null) ? (ora - prima) / prima : null;
  const segno = (v) => v === null ? "" : `${v > 0 ? "+" : v < 0 ? "−" : ""}${num(Math.abs(v * 100), 1)} %`;

  function passoTondo(max) {
    if (!(max > 0)) return 1;
    const grezzo = max / 4, p = 10 ** Math.floor(Math.log10(grezzo));
    return [1, 2, 2.5, 5, 10].map((m) => m * p).find((s) => grezzo <= s) || 10 * p;
  }

  // barre affiancate: per ogni mese l'anno prima (tenue) e l'anno in corso (pieno)
  function disegna(dest, misure, ind, serie, anni, colore) {
    const W = misure && misure.riquadro ? misure.larghezza : Math.round(Math.max(320, Math.min(720, (misure && misure.larghezza) || 640)));
    const H = misure && misure.riquadro ? misure.altezza : (W < 480 ? 220 : 260);
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img",
      "aria-label": `${ind.titolo}: ${anni[0]} e ${anni[1]}, mese per mese, in ${ind.unita}` }, dest);
    const a = serie[anni[0]] || [], b = serie[anni[1]] || [];
    const max = Math.max(0, ...a.concat(b).filter((x) => x !== null && x !== undefined));
    const sx = W < 480 ? 44 : 52, dx = 8, su = 12, gi = 26;
    const passo = passoTondo(max), cima = Math.max(passo, Math.ceil(max / passo) * passo);
    const Y = (v) => su + (H - su - gi) * (1 - v / cima);
    for (let v = 0; v <= cima + passo / 1e6; v += passo) {
      el("line", { x1: sx, x2: W - dx, y1: Y(v), y2: Y(v), class: "asse" }, svg);
      el("text", { x: sx - 6, y: Y(v) + 4, "text-anchor": "end" }, svg).textContent = num(v, passo < 0.1 ? 2 : passo < 1 ? 1 : 0);
    }
    const larg = (W - sx - dx) / 12, barra = Math.min(larg * 0.36, misure && misure.riquadro ? 30 : 18);
    const X = (i) => sx + larg * (i + 0.5);
    const barre = [];
    for (let i = 0; i < 12; i++) {
      const coppia = [];
      [[a[i], -1, "prima"], [b[i], 0, "ora"]].forEach(([v, off, cls]) => {
        if (v === null || v === undefined) return;
        coppia.push(el("rect", { x: X(i) + off * barra - (off ? 1 : -1), y: Y(v), width: barra, height: Math.max(0, Y(0) - Y(v)),
          rx: 2, fill: colore, class: cls }, svg));
      });
      barre.push(coppia);
      el("text", { x: X(i), y: H - 8, "text-anchor": "middle" }, svg).textContent = W < 520 ? INIZIALI[i] : MESI[i].slice(0, 3);
    }
    if (window.EUGENIO_GRAFICI) {
      const punti = MESI.map((m, i) => {
        const righe = [];
        if (a[i] !== null && a[i] !== undefined) righe.push([colore, `${anni[0]}: ${num(a[i], decimali(ind))} ${ind.unita}`]);
        if (b[i] !== null && b[i] !== undefined) righe.push([colore, `${anni[1]}: ${num(b[i], decimali(ind))} ${ind.unita}`]);
        const v = variazione(a[i], b[i]);
        if (v !== null) righe.push(["var(--linea)", `Variazione: ${segno(v)}`]);
        return { x: X(i), titolo: m[0].toUpperCase() + m.slice(1), righe, elementi: barre[i] };
      });
      window.EUGENIO_GRAFICI.osserva(svg, punti, { area: [sx, su, W - dx, H - gi], guida: false });
    }
    const leg = h("div", "legenda");
    [[anni[0], ".42"], [anni[1], "1"]].forEach(([anno, op]) => {
      const s = h("span"), i = h("i");
      i.style.background = colore; i.style.opacity = op;
      s.append(i, String(anno)); leg.appendChild(s);
    });
    dest.appendChild(leg);
  }

  function tabella(ind, serie, anni) {
    const t = h("table", "mensili");
    const testa = t.createTHead().insertRow();
    ["Mese", String(anni[0]), String(anni[1]), "Variazione"].forEach((x, j) => {
      const c = h("th", j ? "num" : null, x); c.scope = "col"; testa.appendChild(c);
    });
    const corpo = t.createTBody();
    const a = serie[anni[0]] || [], b = serie[anni[1]] || [];
    MESI.forEach((m, i) => {
      const r = corpo.insertRow();
      const th = h("th", null, m[0].toUpperCase() + m.slice(1)); th.scope = "row";
      const det = (ind.dettagli || {})[`${anni[1]}-${String(i + 1).padStart(2, "0")}`];
      if (det) th.appendChild(h("small", null, `${det.trimestre}${det.provvisorio ? ", provvisorio" : ""}`));
      r.appendChild(th);
      r.appendChild(h("td", a[i] === null || a[i] === undefined ? "num nd" : "num", num(a[i], decimali(ind))));
      r.appendChild(h("td", b[i] === null || b[i] === undefined ? "num nd" : "num", num(b[i], decimali(ind))));
      const v = variazione(a[i], b[i]);
      r.appendChild(h("td", v === null ? "num nd" : `num ${v > 0 ? "su" : v < 0 ? "giu" : ""}`, v === null ? "" : segno(v)));
    });
    const cap = t.createCaption();
    cap.className = "solo-lettori";
    cap.textContent = `${ind.titolo}, ${ind.unita}`;
    return t;
  }

  function mostraIndice(box, ind, anni, sezione) {
    const lotti = Object.keys(ind.lotti);
    const sc = scelte[ind.id] || (scelte[ind.id] = { lotto: ind.lotto_predefinito, variante: null });
    if (!lotti.includes(sc.lotto)) sc.lotto = lotti[0];
    const lotto = ind.lotti[sc.lotto];
    const varianti = Object.keys(lotto.varianti);
    if (!varianti.includes(sc.variante)) sc.variante = varianti[0];
    box.innerHTML = "";
    box.appendChild(h("h3", null, ind.titolo));
    const fonte = h("p", "aiuto");
    fonte.append(`Fonte: ${ind.fonte}${ind.licenza ? ` (${ind.licenza})` : ""}. ${ind.nota}`);
    box.appendChild(fonte);
    if (lotti.length > 1) {
      const riga = h("div", "riga");
      const id = `lotto-${ind.id}`;
      const etichetta = h("label", null, "Lotto"); etichetta.htmlFor = id;
      const sel = h("select"); sel.id = id;
      lotti.forEach((k) => { const o = h("option", null, ind.lotti[k].nome); o.value = k; o.selected = k === sc.lotto; sel.appendChild(o); });
      sel.addEventListener("change", () => { sc.lotto = sel.value; mostraIndice(box, ind, anni, sezione); box.querySelector("select").focus(); });
      const d = h("div"); d.append(etichetta, sel); riga.appendChild(d);
      box.appendChild(riga);
    }
    if (varianti.length > 1) {
      const f = h("div", "filtri"); f.setAttribute("role", "group"); f.setAttribute("aria-label", "Fascia o uso");
      varianti.forEach((v) => {
        const b = h("button", "filtro", nomeVariante(v)); b.type = "button";
        b.setAttribute("aria-pressed", String(v === sc.variante));
        b.addEventListener("click", () => { sc.variante = v; mostraIndice(box, ind, anni, sezione); });
        f.appendChild(b);
      });
      box.appendChild(f);
    }
    const serie = lotto.varianti[sc.variante];
    const corpo = h("div", "ip-corpo");
    const g = h("div", "grafico");
    const t = h("div", "tabella-scorre");
    corpo.append(g, t);
    box.appendChild(corpo);
    const parti = [ind.titolo, lotti.length > 1 ? lotto.nome : "", varianti.length > 1 ? nomeVariante(sc.variante).toLowerCase() : ""]
      .filter(Boolean);
    const titolo = `${parti.join(", ")} (${ind.unita}), ${anni[0]} e ${anni[1]}`;
    const colore = COLORE[sezione] || "var(--primario)";
    if (window.EUGENIO_GRAFICI) window.EUGENIO_GRAFICI.registra(g, (d, m) => disegna(d, m, ind, serie, anni, colore), { titolo, adatta: true });
    else disegna(g, { larghezza: g.clientWidth, altezza: null, riquadro: false }, ind, serie, anni, colore);
    t.appendChild(tabella(ind, serie, anni));
  }

  // ------------------------------------------------------------------ confronto sui consumi dell'utente (11/11/2026)
  // Un file con una riga per mese e i kWh in F1, F2, F3: lo stesso profilo moltiplicato per i prezzi di Intercent-ER
  // lotto 1 e lotto 2 e di Consip (lotto a scelta), anno prima e anno in corso, sugli stessi mesi (quelli con il prezzo
  // di tutte e tre le offerte in entrambi gli anni). Il file resta nel browser (i fogli di calcolo passano dalla
  // conversione del server, tabelle.js, senza essere salvati).
  const MESI_BREVI = MESI.map((m) => m.slice(0, 3));
  function meseDa(testo) {
    const t = String(testo || "").trim().toLowerCase();
    if (!t) return null;
    let m = t.match(/^(\d{4})[-/.](\d{1,2})(?:[-/.]\d{1,2})?$/);          // 2026-01, 2026-01-01
    if (m) return +m[2] >= 1 && +m[2] <= 12 ? +m[2] : null;
    m = t.match(/^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$/);                 // 01/01/2026
    if (m) return +m[2] >= 1 && +m[2] <= 12 ? +m[2] : null;
    m = t.match(/^(\d{1,2})[-/.](\d{4})$/);                              // 01/2026
    if (m) return +m[1] >= 1 && +m[1] <= 12 ? +m[1] : null;
    if (/^\d{1,2}$/.test(t)) return +t >= 1 && +t <= 12 ? +t : null;       // 1 … 12
    const i = MESI_BREVI.indexOf(t.slice(0, 3));
    return i >= 0 ? i + 1 : null;
  }
  function leggiConsumi(testo, decimalePunto) {
    const T = window.EUGENIO_TABELLE;
    const righe = T.righe(testo, T.separatore(testo.split(/\r?\n/)[0] || ""));
    if (righe.length < 2) throw new Error("Il file è vuoto o ha solo la riga dei titoli.");
    const tit = righe[0].map((x) => String(x || "").trim().toLowerCase());
    const cm = tit.findIndex((x) => /^(mese|month|periodo|data)/.test(x));
    const cf = ["f1", "f2", "f3"].map((f) => tit.findIndex((x) => x.replace(/[^a-z0-9]/g, "").startsWith(f)));
    if (cm < 0 || cf.some((c) => c < 0)) throw new Error("Servono le colonne «mese», «F1», «F2» e «F3» (kWh).");
    const scala = cf.map((c) => /mwh/.test(tit[c]) ? 1000 : 1);
    const kwh = {};
    let doppi = 0;
    for (const r of righe.slice(1)) {
      if (!r.some((x) => String(x || "").trim())) continue;
      const m = meseDa(r[cm]);
      if (!m) continue;
      const v = cf.map((c, j) => { const x = T.numero(r[c], { decimalePunto }); return x === null ? null : x * scala[j]; });
      if (v.some((x) => x === null || x < 0)) continue;
      if (kwh[m]) doppi++;
      kwh[m] = v;
    }
    if (!Object.keys(kwh).length) throw new Error("Nessuna riga valida: controlla il mese e i numeri dei consumi.");
    return { kwh, doppi };
  }
  const euro = (x) => `${num(x, 0)} €`;

  function confronto(indici, anni) {
    const ic = indici.find((i) => i.centrale === "Intercent-ER");
    const cs = indici.find((i) => i.centrale === "Consip");
    if (!ic || !cs || !ic.lotti["1"] || !ic.lotti["2"]) return null;
    const box = h("article", "ip-indice ip-confronto");
    box.id = "confronto-consumi";
    box.appendChild(h("h3", null, "Confronta le convenzioni sui tuoi consumi"));
    box.appendChild(h("p", "aiuto", "Carica un file con una riga per mese e i consumi in kWh nelle tre fasce (colonne «mese», «F1», «F2», «F3»; "
      + "il mese anche come numero o data). Lo stesso profilo di consumi si moltiplica per i prezzi di Intercent-ER (lotti 1 e 2) e di Consip, "
      + `nel ${anni[0]} e nel ${anni[1]}. Il file resta nel tuo browser.`));
    const riga = h("div", "riga");
    const d1 = h("div"); const l1 = h("label", null, "File dei consumi (CSV, Excel o ODS)"); l1.htmlFor = "file-consumi";
    const inp = h("input"); inp.type = "file"; inp.id = "file-consumi"; inp.accept = window.EUGENIO_TABELLE ? window.EUGENIO_TABELLE.ACCETTA : ".csv";
    d1.append(l1, inp);
    const d2 = h("div"); const l2 = h("label", null, "Lotto Consip"); l2.htmlFor = "lotto-confronto";
    const sel = h("select"); sel.id = "lotto-confronto";
    Object.keys(cs.lotti).forEach((k) => { const o = h("option", null, cs.lotti[k].nome); o.value = k; o.selected = k === cs.lotto_predefinito; sel.appendChild(o); });
    d2.append(l2, sel);
    riga.append(d1, d2);
    box.appendChild(riga);
    const es = h("p", "aiuto"); const a = h("a", null, "file di esempio"); a.href = "esempi/consumi_fasce_esempio.csv"; a.download = "";
    es.append("Non hai un file? Prova con il ", a, " (dati inventati).");
    box.appendChild(es);
    const msg = h("p", "messaggio"); msg.setAttribute("role", "status"); msg.setAttribute("aria-live", "polite");
    box.appendChild(msg);
    const esito = h("div");
    box.appendChild(esito);
    let consumi = null;
    const calcola = () => {
      esito.innerHTML = "";
      if (!consumi) return;
      const offerte = [["Intercent-ER lotto 1", ic.lotti["1"]], ["Intercent-ER lotto 2", ic.lotti["2"]],
        [`Consip lotto ${sel.value}`, cs.lotti[sel.value]]];
      // mesi con i consumi e con il prezzo F1, F2, F3 di tutte le offerte in entrambi gli anni
      const prezzo = (lotto, f, anno, m) => ((lotto.varianti[f] || {})[anno] || [])[m - 1];
      const mesi = Object.keys(consumi.kwh).map(Number).sort((x, y) => x - y).filter((m) => offerte.every(([, lo]) =>
        anni.every((an) => ["F1", "F2", "F3"].every((f) => { const p = prezzo(lo, f, String(an), m); return p !== null && p !== undefined; }))));
      if (!mesi.length) { msg.textContent = "Nessun mese con i prezzi di tutte le offerte in entrambi gli anni."; return; }
      const mwh = mesi.reduce((s, m) => s + consumi.kwh[m].reduce((a2, b) => a2 + b, 0), 0) / 1000;
      const ris = offerte.map(([nome, lo]) => ({ nome, costi: anni.map((an) => mesi.reduce((s, m) =>
        s + ["F1", "F2", "F3"].reduce((t2, f, j) => t2 + consumi.kwh[m][j] / 1000 * prezzo(lo, f, String(an), m), 0), 0)) }));
      const elenco = mesi.length === 12 ? "tutto l'anno" : mesi.map((m) => MESI[m - 1]).join(", ");
      esito.appendChild(h("p", "aiuto", `Mesi confrontati: ${elenco} (${num(mwh, 1)} MWh). Costo della sola energia con i prezzi dei listini, IVA esclusa: `
        + "senza perdite di rete, dispacciamento, trasporto, oneri e imposte, che si aggiungono a tutte le offerte. "
        + "Sottolineato il costo più basso di ogni anno."));
      const corpo = h("div", "ip-corpo"); const g = h("div", "grafico"); const tb = h("div", "tabella-scorre");
      corpo.append(g, tb); esito.appendChild(corpo);
      const disegnaC = (dest, misure) => {
        const W = misure && misure.riquadro ? misure.larghezza : Math.round(Math.max(320, Math.min(720, (misure && misure.larghezza) || 640)));
        const H = misure && misure.riquadro ? misure.altezza : (W < 480 ? 230 : 270);
        const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `Costo dell'energia con le tre offerte, ${anni[0]} e ${anni[1]}` }, dest);
        const max = Math.max(...ris.flatMap((r) => r.costi));
        const sx = W < 480 ? 56 : 70, dx = 8, su = 18, gi = 30;
        const passo = passoTondo(max), cima = Math.max(passo, Math.ceil(max / passo) * passo);
        const Y = (v) => su + (H - su - gi) * (1 - v / cima);
        for (let v = 0; v <= cima + passo / 1e6; v += passo) {
          el("line", { x1: sx, x2: W - dx, y1: Y(v), y2: Y(v), class: "asse" }, svg);
          el("text", { x: sx - 6, y: Y(v) + 4, "text-anchor": "end" }, svg).textContent = v >= 1e6 ? `${num(v / 1e6, 1)} M€` : `${num(v / 1000, 0)} k€`;
        }
        const larg = (W - sx - dx) / 3, barra = Math.min(larg * 0.3, misure && misure.riquadro ? 60 : 44);
        const punti = [];
        ris.forEach((r, i) => {
          const cx = sx + larg * (i + 0.5);
          const el2 = [];
          r.costi.forEach((c, k) => {
            const x = cx + (k ? 2 : -barra - 2);
            el2.push(el("rect", { x, y: Y(c), width: barra, height: Math.max(0, Y(0) - Y(c)), rx: 2, fill: "var(--prezzi-ele)", class: k ? "ora" : "prima" }, svg));
            if (W >= 480) el("text", { x: x + barra / 2, y: Y(c) - 4, "text-anchor": "middle" }, svg).textContent = `${num(c / 1000, 0)} k€`;
          });
          el("text", { x: cx, y: H - 10, "text-anchor": "middle" }, svg).textContent = W < 480 ? r.nome.replace("Intercent-ER ", "IER ") : r.nome;
          punti.push({ x: cx, titolo: r.nome, elementi: el2, righe: r.costi.map((c, k) => ["var(--prezzi-ele)", `${anni[k]}: ${euro(c)} (${num(c / mwh)} €/MWh)`]) });
        });
        if (window.EUGENIO_GRAFICI) window.EUGENIO_GRAFICI.osserva(svg, punti, { area: [sx, su, W - dx, H - gi], guida: false });
        const leg = h("div", "legenda");
        [[anni[0], ".42"], [anni[1], "1"]].forEach(([an, op]) => { const s2 = h("span"), i2 = h("i"); i2.style.background = "var(--prezzi-ele)"; i2.style.opacity = op; s2.append(i2, String(an)); leg.appendChild(s2); });
        dest.appendChild(leg);
      };
      if (window.EUGENIO_GRAFICI) window.EUGENIO_GRAFICI.registra(g, disegnaC, { titolo: `Costo dell'energia con le tre offerte (${elenco}), ${anni[0]} e ${anni[1]}`, adatta: true });
      else disegnaC(g, { larghezza: g.clientWidth });
      const t = h("table", "mensili");
      const th = t.createTHead().insertRow();
      ["Offerta", `${anni[0]}`, `${anni[1]}`, "Variazione"].forEach((x, j) => { const c = h("th", j ? "num" : null, x); c.scope = "col"; th.appendChild(c); });
      const tbody = t.createTBody();
      const minimo = anni.map((_, k) => Math.min(...ris.map((r) => r.costi[k])));
      ris.forEach((r) => {
        const tr = tbody.insertRow();
        const c0 = h("th", null, r.nome); c0.scope = "row"; tr.appendChild(c0);
        r.costi.forEach((c, k) => {
          const td = h("td", "num", euro(c));
          td.appendChild(h("small", null, `${num(c / mwh)} €/MWh`));
          if (c === minimo[k]) td.classList.add("meglio");
          tr.appendChild(td);
        });
        const v = variazione(r.costi[0], r.costi[1]);
        tr.appendChild(h("td", `num ${v > 0 ? "su" : v < 0 ? "giu" : ""}`, segno(v)));
      });
      tb.appendChild(t);
    };
    inp.addEventListener("change", async () => {
      const f = inp.files && inp.files[0];
      consumi = null; esito.innerHTML = ""; msg.textContent = "";
      if (!f) return;
      try {
        if ((await window.EUGENIO_TABELLE.tipo(f)) === "xls") throw new Error(window.EUGENIO_TABELLE.MSG_XLS);
        msg.textContent = "Lettura del file…";
        const l = await window.EUGENIO_TABELLE.leggi(f);
        consumi = leggiConsumi(l.testo, l.decimalePunto);
        msg.textContent = `Letti ${Object.keys(consumi.kwh).length} mesi.${consumi.doppi ? ` ${consumi.doppi} mesi ripetuti: vale l'ultima riga.` : ""} ${l.nota || ""}`.trim();
        calcola();
      } catch (e) { msg.textContent = e.message || String(e); }
    });
    sel.addEventListener("change", calcola);
    return box;
  }

  function mostra(dati) {
    const dove = $("indici-prezzi");
    dove.innerHTML = "";
    const anni = dati.anni;
    let quanti = 0;
    for (const s of dati.sezioni) {
      dove.appendChild(h("h2", null, s.titolo));
      if (!s.indici.length) dove.appendChild(h("p", "aiuto", "Valori non ancora disponibili."));
      for (const ind of s.indici) {
        const box = h("article", "ip-indice");
        box.id = ind.id;
        dove.appendChild(box);
        mostraIndice(box, ind, anni, s.id);
        quanti++;
      }
      if (s.id === "elettricita") {
        for (const x of dati.in_attesa || []) dove.appendChild(h("p", "ip-attesa", `${x.titolo}: ${x.motivo}.`));
        const conf = confronto(s.indici, anni);
        if (conf) dove.appendChild(conf);
      }
    }
    if (!quanti) dove.appendChild(h("p", "aiuto", "I valori non sono ancora pronti: tornano dopo il prossimo aggiornamento notturno."));
    const d = new Date(`${dati.aggiornato}T12:00:00`);
    $("aggiornato-prezzi").textContent = `Aggiornato il ${d.toLocaleDateString("it-IT", { day: "numeric", month: "long", year: "numeric" })}. `
      + "Si aggiorna ogni notte; i listini e il PSV di un mese escono nei primi giorni del mese dopo.";
  }

  fetch("dati/prezzi/indici.json", { cache: "no-cache" })
    .then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.json(); })
    .then(mostra)
    .catch(() => {
      $("indici-prezzi").innerHTML = "";
      $("indici-prezzi").appendChild(h("p", "aiuto", "I valori non sono ancora pronti: tornano dopo il prossimo aggiornamento notturno."));
    });
})();
