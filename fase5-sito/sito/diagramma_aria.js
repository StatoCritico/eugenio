"use strict";
// Diagramma dell'aria umida (14/11/2026), componente comune delle pagine «Trattamento aria». Le regole generali dei
// grafici sono in README_stile.md; qui:
//  - due viste con i pulsanti «Psicrometrico» (predefinita: T in ascissa −10…50 °C, x in ordinata 0…30 g/kg, a destra) e
//    «Mollier» (x in ascissa 0…30 g/kg, coordinata di Mollier Y = (h − 2501·x)/1,006 in ordinata −10…50), stessa scala,
//    stesse famiglie di curve e stessi passi del foglio psicro_UTA.xlsx: saturazione spessa, UR 10…90 %, entalpia ogni
//    10 kJ/kg, volume specifico ogni 0,02 m³/kg (tratteggio), isoterme ogni 1 °C (etichette ogni 5 °C) nel Mollier;
//  - disegno su canvas (nitido con devicePixelRatio) e, con la stessa funzione di disegno, SVG per l'esportazione e per il
//    riquadro flottante della freccina ↗ (grafici.js: zoom, trascinamento, ✱ e ◐);
//  - strati: nuvole di punti (fino a ~750.000 ore: accumulo per pixel su un canvas a parte, trasparenza che dipende dalla
//    densità, oppure celle di densità), spezzate (trasformazioni: segmenti rettilinei spessi con marcatori), punti con
//    etichetta, zone (poligoni, rettangoli T–x o T–UR), rette (retta ambiente con R o Δh/Δx), legenda con «mostra»;
//  - suggerimento al passaggio del mouse: T, UR, x, h del cursore, il punto disegnato più vicino e le ore delle nuvole lì;
//  - colori dal tema (variabili CSS, ridisegno all'evento eugenio:aspetto); immagini PNG e SVG con i colori di stampa
//    (fondo bianco, colori del foglio Excel) e la fascia con la legenda degli strati visibili (nome, colore, nota), titolo,
//    fonti e «Fonte: EuGEnio – eugenio.statocritico.it»; il riquadro ↗ ha sotto il diagramma la stessa legenda della pagina.
// API: EUGENIO_DIAGRAMMA_ARIA.crea(box, opz) → diagramma; vedi API_MODULI_ARIA e il README della fase 5.
(function () {
  const P = window.EUGENIO_PSICRO;
  const KM = P.CPV / P.CPA;                       // 1,86/1,006: Y = T·(1 + KM·x)
  const SCALA = { tMin: -10, tMax: 50, xMax: 30, yMin: -10, yMax: 50 };   // x in g/kg
  const PHIS = [1, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1];
  const HVALS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120];
  // colori del foglio Excel (stampa e tema chiaro) e varianti più chiare per il tema scuro
  const EXCEL = { estate: "#0070C0", inverno: "#C00000", entalpia: "#2E75B6", volume: "#548235", ur: "#7F7F7F", isoterme: "#C9C9C9",
    isoterme5: "#7F7F7F", griglia: "#BFBFBF", grigliaMinore: "#E7E6E6", inchiostro: "#000000" };
  const SCURO = { estate: "#4DA3FF", inverno: "#FF6B6B", entalpia: "#6EA8DE", volume: "#8CC46A" };
  const COLORI = { estate: EXCEL.estate, inverno: EXCEL.inverno };
  const fmt = (n, d = 0) => (Number.isFinite(n) ? EUGENIO_NUMERI.formato(n, d) : "—");
  const meno = (s) => String(s).replace(/^-/, "−");
  function h(tag, cls, testo) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (testo !== undefined && testo !== null) e.textContent = testo;
    return e;
  }

  // ------------------------------------------------------------------ tavolozze
  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const scuro = () => document.documentElement.dataset.theme !== "light";
  function tavolozzaPagina() {
    const d = scuro();
    const font = (getComputedStyle(document.body).fontFamily || "sans-serif");
    return { stampa: false, scuro: d, fondo: null, inchiostro: css("--inchiostro") || "#eee", tenue: css("--tenue") || "#999",
      griglia: css("--linea") || "#444", grigliaMinore: css("--linea") || "#333", minoreAlfa: 0.45,
      ur: d ? (css("--tenue") || "#9a9a9a") : EXCEL.ur, isoterme: css("--linea") || EXCEL.isoterme, isoterme5: css("--tenue") || EXCEL.isoterme5,
      entalpia: d ? SCURO.entalpia : EXCEL.entalpia, volume: d ? SCURO.volume : EXCEL.volume, contorno: css("--foglio") || "#111", font };
  }
  function tavolozzaStampa() {
    return { stampa: true, scuro: false, fondo: "#ffffff", inchiostro: "#000000", tenue: "#404040", griglia: EXCEL.griglia,
      grigliaMinore: EXCEL.grigliaMinore, minoreAlfa: 1, ur: EXCEL.ur, isoterme: EXCEL.isoterme, isoterme5: EXCEL.isoterme5,
      entalpia: EXCEL.entalpia, volume: EXCEL.volume, contorno: "#ffffff", font: "Helvetica, Arial, sans-serif" };
  }
  // colore di uno strato: "estate", "inverno", "var(--serie-2)", "#hex", "rgb(…)"
  function risolvi(c, tav) {
    if (!c) return tav.inchiostro;
    if (c === "estate" || c === "inverno") return tav.scuro ? SCURO[c] : EXCEL[c];
    const m = /^var\((--[\w-]+)\)$/.exec(c);
    if (m) {
      const v = css(m[1]);
      if (tav.stampa) {                 // colori di stampa: le serie del tema chiaro
        const r = document.documentElement, prima = r.dataset.theme;
        if (prima !== "light") { r.dataset.theme = "light"; const w = css(m[1]); if (prima) r.dataset.theme = prima; else delete r.dataset.theme; return w || v; }
      }
      return v || tav.inchiostro;
    }
    return c;
  }
  function rgb(c) {
    let m = /^#([0-9a-f]{3})$/i.exec(c);
    if (m) return m[1].split("").map((x) => parseInt(x + x, 16));
    m = /^#([0-9a-f]{6})/i.exec(c);
    if (m) return [0, 2, 4].map((i) => parseInt(m[1].slice(i, i + 2), 16));
    m = /rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)/i.exec(c);
    if (m) return [+m[1], +m[2], +m[3]];
    return [128, 128, 128];
  }

  // ------------------------------------------------------------------ curve di base (in coordinate del diagramma)
  // psicrometrico: u = T, v = x [g/kg]; Mollier: u = x [g/kg], v = Y
  const copieCurve = new Map();
  function curve(p, modo) {
    const k = `${modo}|${Math.round(p)}`;
    if (copieCurve.has(k)) return copieCurve.get(k);
    const pk = p / 1000, X30 = 0.030;
    const tFineUR = (phi) => Math.min(50, P.tRugiadaPw(p * X30 / (P.EPS + X30) / phi));
    const xg = (t, phi) => 1000 * P.xDaUR(t, phi * 100, p);
    const tSatV = (v) => {               // T sulla saturazione con volume specifico v
      let lo = -60, hi = 80;
      for (let i = 0; i < 60; i++) { const m = (lo + hi) / 2; if (P.volume(m, P.xSat(m, p), p) > v) hi = m; else lo = m; }
      return (lo + hi) / 2;
    };
    const v0 = Math.ceil(P.RA * 263.15 / pk / 0.02 - 1e-9) * 0.02, VVALS = Array.from({ length: 10 }, (_, i) => +(v0 + 0.02 * i).toFixed(2));
    const out = { ur: [], h: [], v: [], iso: [], iso5: [] };
    if (modo === "psicrometrico") {
      for (const phi of PHIS) {
        const tf = tFineUR(phi), pts = [];
        for (let i = 0; i <= 120; i++) { const t = -10 + (tf + 10) * i / 120; pts.push([t, xg(t, phi)]); }
        out.ur.push({ phi, pts, nome: `${Math.round(phi * 100)} %` });
      }
      for (const hv of HVALS) {
        const ts = Math.max(-10, P.tSatDaH(hv, p), (hv - 2501 * X30) / (1.006 + 1.86 * X30)), tf = Math.max(ts, Math.min(50, hv / 1.006));
        const pts = [];
        for (let i = 0; i <= 8; i++) { const t = ts + (tf - ts) * i / 8; pts.push([t, Math.max(0, 1000 * P.xDaHT(hv, t))]); }
        out.h.push({ valore: hv, pts, nome: `h ${hv}` });
      }
      for (const vv of VVALS) {
        const ts = Math.max(-10, tSatV(vv), vv * pk / (P.RA * (1 + 1.607858 * X30)) - 273.15), tf = Math.max(ts, Math.min(50, vv * pk / P.RA - 273.15));
        const pts = [];
        for (let i = 0; i <= 6; i++) { const t = ts + (tf - ts) * i / 6; pts.push([t, Math.max(0, 1000 * (vv * pk / (P.RA * (t + 273.15)) - 1) / 1.607858)]); }
        out.v.push({ valore: vv, pts, nome: `v ${fmt(vv, 2)}` });
      }
    } else {
      const yM = (t, x) => t * (1 + KM * x / 1000);
      for (let t = -9; t <= 50; t++) {
        let lim = 30;
        if (t > 0) lim = (50 / t - 1) * 1006 / 1.86; else if (t < 0) lim = (-10 / t - 1) * 1006 / 1.86;
        const xe = Math.max(0, Math.min(1000 * P.xSat(t, p), 30, lim));
        const seg = { valore: t, pts: [[0, t], [xe, yM(t, xe)]], nome: `${meno(t)} °C` };
        (t % 5 === 0 && t >= -5 && t <= 45 ? out.iso5 : out.iso).push(seg);
      }
      for (const phi of PHIS) {
        // inizio dove Y = −10, fine dove la curva esce in alto (Y = 50) o a destra (x = 30)
        let t0 = -10;
        for (let i = 0; i < 30; i++) t0 = -10 / (1 + KM * xg(t0, phi) / 1000);
        let t1 = 50;
        for (let i = 0; i < 40; i++) t1 = 50 / (1 + KM * xg(t1, phi) / 1000);
        const tf = Math.min(tFineUR(phi), t1), pts = [];
        for (let i = 0; i <= 120; i++) { const t = t0 + (tf - t0) * i / 120; const x = xg(t, phi); pts.push([x, yM(t, x)]); }
        out.ur.push({ phi, pts, nome: `${Math.round(phi * 100)} %` });
      }
      for (const hv of HVALS) {
        const xa = Math.max(0, (hv - 50 * 1.006) / 2.501), ts = P.tSatDaH(hv, p);
        const xb = Math.max(xa, Math.min(30, 1000 * P.xDaHT(hv, ts), (hv + 10 * 1.006) / 2.501));
        out.h.push({ valore: hv, pts: [[xa, (hv - 2.501 * xa) / 1.006], [xb, (hv - 2.501 * xb) / 1.006]], nome: `h ${hv}` });
      }
      for (const vv of VVALS) {
        const T = (x) => vv * pk / (P.RA * (1 + 1.607858 * x / 1000)) - 273.15;
        const xa = Math.max(0, 1000 * (vv * pk / (P.RA * 323.15) - 1) / 1.607858);
        const xb = Math.min(30, 1000 * P.xSat(tSatV(vv), p));
        if (!(xb > xa)) continue;
        const pts = [];
        for (let i = 0; i <= 24; i++) { const x = xa + (xb - xa) * i / 24; pts.push([x, yM(T(x), x)]); }
        out.v.push({ valore: vv, pts, nome: `v ${fmt(vv, 2)}` });
      }
    }
    copieCurve.set(k, out);
    return out;
  }

  // ------------------------------------------------------------------ contesto SVG (stessa interfaccia del canvas 2D)
  function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  const r2 = (n) => Math.round(n * 100) / 100;
  class ContestoSvg {
    constructor(w, h) {
      this.w = w; this.h = h; this.parti = []; this.m = [1, 0, 0, 1, 0, 0]; this.pila = []; this.aperti = 0; this.d = ""; this.n = 0;
      this.strokeStyle = "#000"; this.fillStyle = "#000"; this.lineWidth = 1; this.font = "12px sans-serif"; this.textAlign = "left";
      this.textBaseline = "alphabetic"; this.globalAlpha = 1; this.dash = []; this.lineJoin = "miter"; this.lineCap = "butt";
      this.misura = document.createElement("canvas").getContext("2d");
    }
    save() { this.pila.push({ m: this.m.slice(), aperti: this.aperti, s: [this.strokeStyle, this.fillStyle, this.lineWidth, this.font, this.textAlign, this.textBaseline, this.globalAlpha, this.dash, this.lineJoin, this.lineCap] }); this.aperti = 0; }
    restore() {
      const s = this.pila.pop(); if (!s) return;
      while (this.aperti-- > 0) this.parti.push("</g>");
      this.m = s.m; this.aperti = s.aperti;
      [this.strokeStyle, this.fillStyle, this.lineWidth, this.font, this.textAlign, this.textBaseline, this.globalAlpha, this.dash, this.lineJoin, this.lineCap] = s.s;
    }
    translate(x, y) { const m = this.m; m[4] += m[0] * x + m[2] * y; m[5] += m[1] * x + m[3] * y; }
    rotate(a) { const [A, B, C, D] = this.m, c = Math.cos(a), s = Math.sin(a); this.m[0] = A * c + C * s; this.m[1] = B * c + D * s; this.m[2] = -A * s + C * c; this.m[3] = -B * s + D * c; }
    setTransform() { this.m = [1, 0, 0, 1, 0, 0]; }
    pt(x, y) { const m = this.m; return [r2(m[0] * x + m[2] * y + m[4]), r2(m[1] * x + m[3] * y + m[5])]; }
    beginPath() { this.d = ""; }
    moveTo(x, y) { const [a, b] = this.pt(x, y); this.d += `M${a} ${b}`; }
    lineTo(x, y) { const [a, b] = this.pt(x, y); this.d += `L${a} ${b}`; }
    closePath() { this.d += "Z"; }
    rect(x, y, w, h) { this.moveTo(x, y); this.lineTo(x + w, y); this.lineTo(x + w, y + h); this.lineTo(x, y + h); this.closePath(); }
    arc(x, y, r) { const [a, b] = this.pt(x, y); this.d += `M${r2(a - r)} ${b}a${r} ${r} 0 1 0 ${2 * r} 0a${r} ${r} 0 1 0 ${-2 * r} 0`; }
    setLineDash(d) { this.dash = d || []; }
    alfa() { return this.globalAlpha < 1 ? ` opacity="${r2(this.globalAlpha)}"` : ""; }
    stroke() {
      if (!this.d) return;
      const tr = this.dash.length ? ` stroke-dasharray="${this.dash.join(" ")}"` : "";
      this.parti.push(`<path d="${this.d}" fill="none" stroke="${this.strokeStyle}" stroke-width="${r2(this.lineWidth)}" stroke-linejoin="${this.lineJoin}" stroke-linecap="${this.lineCap}"${tr}${this.alfa()}/>`);
    }
    fill() { if (this.d) this.parti.push(`<path d="${this.d}" fill="${this.fillStyle}"${this.alfa()}/>`); }
    fillRect(x, y, w, h) { this.beginPath(); this.rect(x, y, w, h); this.fill(); }
    clearRect() {}
    clip() { const id = `c${++this.n}`; this.parti.push(`<clipPath id="${id}"><path d="${this.d}"/></clipPath><g clip-path="url(#${id})">`); this.aperti++; }
    measureText(s) { this.misura.font = this.font; return this.misura.measureText(s); }
    fillText(s, x, y) {
      const m = this.m, anc = { left: "start", start: "start", center: "middle", right: "end", end: "end" }[this.textAlign] || "start";
      const fm = /^(bold\s+|\d{3}\s+)?([\d.]+)px\s+(.*)$/.exec(this.font) || [];
      // linea di base con dy (dominant-baseline non vale in tutti i programmi: rsvg, Inkscape vecchi)
      const fs = Number(fm[2] || 12), dy = { top: 0.8, middle: 0.35, bottom: -0.22, alphabetic: 0 }[this.textBaseline] || 0;
      const peso = fm[1] ? ` font-weight="${fm[1].trim() === "bold" ? "700" : fm[1].trim()}"` : "";
      const tr = m[0] === 1 && m[1] === 0 && m[2] === 0 && m[3] === 1 ? "" : ` transform="matrix(${m.map(r2).join(" ")})"`;
      const [a, b] = tr ? [x, y] : this.pt(x, y);
      this.parti.push(`<text x="${r2(a)}" y="${r2(b)}"${tr} ${dy ? ` dy="${r2(dy * fs)}"` : ""} font-size="${fs}" font-family="${esc(fm[3] || "sans-serif")}"${peso} fill="${this.fillStyle}" text-anchor="${anc}"${this.alfa()}>${esc(s)}</text>`);
    }
    drawImage(c, x, y, w, h) {
      const [a, b] = this.pt(x, y);
      this.parti.push(`<image x="${a}" y="${b}" width="${r2(w)}" height="${r2(h)}" preserveAspectRatio="none" href="${c.toDataURL("image/png")}"${this.alfa()}/>`);
    }
    testo() { while (this.aperti-- > 0) this.parti.push("</g>"); this.aperti = 0; return this.parti.join("\n"); }
  }

  // ------------------------------------------------------------------ disegno (canvas o SVG)
  function geometria(W, H, modo) {
    const psi = modo === "psicrometrico";
    const L = psi ? 44 : 50, R = psi ? 50 : 16, T = 12, B = 42;
    const g = { W, H, L, R, T, B, pw: Math.max(40, W - L - R), ph: Math.max(40, H - T - B), modo,
      u0: psi ? SCALA.tMin : 0, u1: psi ? SCALA.tMax : SCALA.xMax, v0: psi ? 0 : SCALA.yMin, v1: psi ? SCALA.xMax : SCALA.yMax };
    g.X = (u) => g.L + (u - g.u0) / (g.u1 - g.u0) * g.pw;
    g.Y = (v) => g.T + (g.v1 - v) / (g.v1 - g.v0) * g.ph;
    // stato (t, x kg/kg) → coordinate del diagramma
    g.uv = psi ? (t, x) => [t, x * 1000] : (t, x) => [x * 1000, t * (1 + KM * x)];
    g.px = (t, x) => { const [u, v] = g.uv(t, x); return [g.X(u), g.Y(v)]; };
    g.inv = (px, py) => {           // pixel → (t, x kg/kg)
      const u = g.u0 + (px - g.L) / g.pw * (g.u1 - g.u0), v = g.v1 - (py - g.T) / g.ph * (g.v1 - g.v0);
      return psi ? { t: u, x: v / 1000 } : { t: v / (1 + KM * u / 1000), x: u / 1000 };
    };
    g.dentro = (px, py) => px >= g.L && px <= g.L + g.pw && py >= g.T && py <= g.T + g.ph;
    return g;
  }

  function polilinea(ctx, g, pts) {
    ctx.beginPath();
    pts.forEach(([u, v], i) => (i ? ctx.lineTo(g.X(u), g.Y(v)) : ctx.moveTo(g.X(u), g.Y(v))));
  }
  function simbolo(ctx, tipo, x, y, s) {
    ctx.beginPath();
    if (tipo === "rombo") { ctx.moveTo(x, y - s); ctx.lineTo(x + s, y); ctx.lineTo(x, y + s); ctx.lineTo(x - s, y); ctx.closePath(); }
    else if (tipo === "quadrato") ctx.rect(x - s * 0.8, y - s * 0.8, s * 1.6, s * 1.6);
    else if (tipo === "triangolo") { ctx.moveTo(x, y - s); ctx.lineTo(x + s, y + s * 0.8); ctx.lineTo(x - s, y + s * 0.8); ctx.closePath(); }
    else ctx.arc(x, y, s * 0.8, 0, Math.PI * 2);
  }

  // etichette senza sovrapposizioni (si salta quella che ne coprirebbe una già scritta)
  function etichettatore(ctx) {
    const occupati = [];
    const scrivi = function (testo, x, y, { align = "left", base = "middle", colore, font, sfondo, forza = false, limiti } = {}) {
      if (font) ctx.font = font;
      const w = ctx.measureText(testo).width, hh = parseFloat(/([\d.]+)px/.exec(ctx.font)[1]) * 1.15;
      let x0 = align === "center" ? x - w / 2 : align === "right" ? x - w : x;
      let y0 = base === "middle" ? y - hh / 2 : base === "top" ? y : y - hh;
      if (limiti) { x0 = Math.max(limiti[0], Math.min(limiti[2] - w, x0)); y0 = Math.max(limiti[1], Math.min(limiti[3] - hh, y0)); }
      const r = [x0 - 1, y0, x0 + w + 1, y0 + hh];
      if (forza !== true && occupati.some((o) => r[0] < o[2] && r[2] > o[0] && r[1] < o[3] && r[3] > o[1])) return false;
      if (forza === "prova") return true;                   // solo controllo: c'è posto
      occupati.push(r);
      if (sfondo) { ctx.save(); ctx.globalAlpha = 0.82; ctx.fillStyle = sfondo; ctx.fillRect(r[0] - 1, r[1], r[2] - r[0] + 2, r[3] - r[1]); ctx.restore(); }
      ctx.fillStyle = colore;
      ctx.textAlign = "left"; ctx.textBaseline = "middle";
      ctx.fillText(testo, x0, y0 + hh / 2);
      return true;
    };
    scrivi.occupa = (r) => occupati.push(r);
    return scrivi;
  }
  // posizioni delle etichette dei punti, nell'ordine in cui si provano (la preferita prima)
  const POSIZIONI = ["r", "t", "l", "b", "tr", "br", "tl", "bl"];
  function scostamento(pos, d) {
    const k = d * 0.75;
    return { r: [d, 0, "left", "middle"], l: [-d, 0, "right", "middle"], t: [0, -d, "center", "bottom"], b: [0, d, "center", "top"],
      tr: [k, -k, "left", "bottom"], br: [k, k, "left", "top"], tl: [-k, -k, "right", "bottom"], bl: [-k, k, "right", "top"] }[pos]
      || [d, 0, "left", "middle"];
  }

  // disegna tutto: base (griglia, curve, assi) e strati. nuvole: funzione (strato, g) → canvas già colorato
  function disegna(ctx, W, H, { modo, p, tav, strati, nuvola, didascalia, evidenzia }) {
    const g = geometria(W, H, modo), psi = modo === "psicrometrico", C = curve(p, modo);
    const f12 = `12px ${tav.font}`, f10 = `10.5px ${tav.font}`, f12b = `bold 12px ${tav.font}`;
    if (tav.fondo) { ctx.fillStyle = tav.fondo; ctx.fillRect(0, 0, W, H); }
    const scrivi = etichettatore(ctx);
    const lim = [g.L + 2, g.T + 2, g.L + g.pw - 2, g.T + g.ph - 2];
    // ---- griglia
    ctx.save();
    ctx.beginPath(); ctx.rect(g.L, g.T, g.pw, g.ph); ctx.clip();
    const linea = (u0, v0, u1, v1) => { ctx.beginPath(); ctx.moveTo(g.X(u0), g.Y(v0)); ctx.lineTo(g.X(u1), g.Y(v1)); ctx.stroke(); };
    ctx.lineWidth = 0.5; ctx.strokeStyle = tav.grigliaMinore; ctx.globalAlpha = tav.minoreAlfa;
    if (psi) {
      for (let t = -10; t <= 50; t++) if (t % 5) linea(t, 0, t, 30);
      for (let x = 1; x < 30; x += 2) linea(-10, x, 50, x);
    }
    ctx.globalAlpha = 1; ctx.lineWidth = 0.75; ctx.strokeStyle = tav.griglia;
    if (psi) { for (let t = -10; t <= 50; t += 5) linea(t, 0, t, 30); for (let x = 0; x <= 30; x += 2) linea(-10, x, 50, x); }
    else for (let x = 0; x <= 30; x += 2) linea(x, -10, x, 50);
    // ---- curve
    if (!psi) {
      ctx.strokeStyle = tav.isoterme; ctx.lineWidth = 0.5;
      C.iso.forEach((s) => { polilinea(ctx, g, s.pts); ctx.stroke(); });
      ctx.strokeStyle = tav.isoterme5; ctx.lineWidth = 0.9;
      C.iso5.forEach((s) => { polilinea(ctx, g, s.pts); ctx.stroke(); });
    }
    ctx.strokeStyle = tav.entalpia; ctx.lineWidth = 0.7;
    C.h.forEach((s) => { polilinea(ctx, g, s.pts); ctx.stroke(); });
    ctx.strokeStyle = tav.volume; ctx.lineWidth = 0.7; ctx.setLineDash([5, 3]);
    C.v.forEach((s) => { polilinea(ctx, g, s.pts); ctx.stroke(); });
    ctx.setLineDash([]);
    C.ur.forEach((s) => {
      ctx.strokeStyle = s.phi === 1 ? tav.inchiostro : tav.ur; ctx.lineWidth = s.phi === 1 ? 2.25 : 0.8;
      polilinea(ctx, g, s.pts); ctx.stroke();
    });
    ctx.restore();
    // ---- strati
    ctx.save();
    ctx.beginPath(); ctx.rect(g.L, g.T, g.pw, g.ph); ctx.clip();
    const ordine = { zona: 0, nuvola: 1, retta: 2, spezzata: 3, punto: 4 };
    const vis = strati.filter((s) => s.visibile).sort((a, b) => ordine[a.tipo] - ordine[b.tipo] || a.ordine - b.ordine);
    const segnaposti = [];
    for (const s of vis) {
      const col = risolvi(s.opz.colore || s.colore, tav), o = s.opz;
      if (s.tipo === "zona") {
        ctx.beginPath();
        s.poligono.forEach((q, i) => { const [x, y] = g.px(q.t, q.x); if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
        ctx.closePath();
        ctx.save(); ctx.globalAlpha = o.alpha === undefined ? 0.18 : o.alpha; ctx.fillStyle = col; ctx.fill(); ctx.restore();
        if (o.bordo !== false) { ctx.strokeStyle = col; ctx.lineWidth = o.spessore || 1.25; ctx.setLineDash(o.tratteggio || []); ctx.stroke(); ctx.setLineDash([]); }
      } else if (s.tipo === "nuvola") {
        const c = nuvola(s, g);
        if (c) ctx.drawImage(c, g.L, g.T, g.pw, g.ph);
      } else if (s.tipo === "retta") {
        ctx.strokeStyle = col; ctx.lineWidth = o.spessore || 1.5; ctx.setLineDash(o.tratteggio || [6, 4]);
        ctx.beginPath();
        s.punti.forEach((q, i) => { const [x, y] = g.px(q.t, q.x); if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
        ctx.stroke(); ctx.setLineDash([]);
      } else if (s.tipo === "spezzata") {
        ctx.strokeStyle = col; ctx.lineWidth = o.spessore || 3; ctx.lineJoin = "round"; ctx.lineCap = "round"; ctx.setLineDash(o.tratteggio || []);
        ctx.beginPath();
        s.punti.forEach((q, i) => { const [x, y] = g.px(q.t, q.x); if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
        ctx.stroke(); ctx.setLineDash([]); ctx.lineJoin = "miter"; ctx.lineCap = "butt";
        if (o.marcatori !== false) s.punti.forEach((q) => {
          const [x, y] = g.px(q.t, q.x);
          simbolo(ctx, "cerchio", x, y, (o.spessore || 3) + 1.6); ctx.fillStyle = col; ctx.fill();
          ctx.lineWidth = 1; ctx.strokeStyle = tav.contorno; ctx.stroke();
        });
        if (o.etichette !== false) s.punti.forEach((q) => { if (q.etichetta) segnaposti.push({ q, col, pos: q.posizione || "t", dim: 6 }); });
      } else if (s.tipo === "punto") {
        const [x, y] = g.px(s.punto.t, s.punto.x), dim = o.dimensione || 6.5;
        simbolo(ctx, o.simbolo || "cerchio", x, y, dim); ctx.fillStyle = col; ctx.fill();
        ctx.lineWidth = 1.2; ctx.strokeStyle = tav.contorno; ctx.stroke();
        if (o.etichetta) segnaposti.push({ q: { ...s.punto, etichetta: o.etichetta }, col, pos: o.posizione || "r", dim });
      }
    }
    if (evidenzia) {
      const [x, y] = g.px(evidenzia.t, evidenzia.x);
      ctx.beginPath(); ctx.arc(x, y, 7, 0, Math.PI * 2); ctx.lineWidth = 2; ctx.strokeStyle = tav.inchiostro; ctx.stroke();
    }
    ctx.restore();
    // etichette dei punti (prima di quelle delle curve: hanno la precedenza). I marcatori occupano il loro posto; ogni
    // etichetta prova la posizione preferita e poi le altre (destra, sopra, sinistra, sotto, diagonali) finché non ne
    // trova una libera; se non c'è, va nella preferita (14/11/2026: «I» e «4» uno sull'altro in Trasformazioni)
    for (const e of segnaposti) { const [x, y] = g.px(e.q.t, e.q.x); scrivi.occupa([x - e.dim, y - e.dim, x + e.dim, y + e.dim]); }
    for (const e of segnaposti) {
      const [x, y] = g.px(e.q.t, e.q.x), d = e.dim + 4;
      const opz = { colore: e.col, font: f12b, limiti: lim, sfondo: tav.fondo || tav.contorno };
      const ordine = [e.pos, ...POSIZIONI.filter((q) => q !== e.pos)];
      let scelta = ordine.find((pos) => { const [dx, dy, al, ba] = scostamento(pos, d); return scrivi(e.q.etichetta, x + dx, y + dy, { ...opz, align: al, base: ba, forza: "prova" }); });
      if (!scelta) scelta = e.pos;
      const [dx, dy, al, ba] = scostamento(scelta, d);
      scrivi(e.q.etichetta, x + dx, y + dy, { ...opz, align: al, base: ba, forza: true });
    }
    // ---- assi, tacche, titoli
    ctx.strokeStyle = tav.inchiostro; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.rect(g.L, g.T, g.pw, g.ph); ctx.stroke();
    ctx.font = f12; ctx.fillStyle = tav.tenue;
    const tacca = (x0, y0, x1, y1) => { ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke(); };
    ctx.strokeStyle = tav.tenue;
    if (psi) {
      for (let t = -10; t <= 50; t += 5) { const x = g.X(t); tacca(x, g.T + g.ph, x, g.T + g.ph + 4); scrivi(meno(t), x, g.T + g.ph + 6, { align: "center", base: "top", colore: tav.tenue, font: f12, forza: true }); }
      for (let x = 0; x <= 30; x += 2) { const y = g.Y(x); tacca(g.L + g.pw, y, g.L + g.pw + 4, y); scrivi(String(x), g.L + g.pw + 7, y, { align: "left", base: "middle", colore: tav.tenue, font: f12, forza: true }); }
    } else {
      for (let x = 0; x <= 30; x += 2) { const px = g.X(x); tacca(px, g.T + g.ph, px, g.T + g.ph + 4); scrivi(String(x), px, g.T + g.ph + 6, { align: "center", base: "top", colore: tav.tenue, font: f12, forza: true }); }
      for (let y = -10; y <= 50; y += 5) { const py = g.Y(y); tacca(g.L - 4, py, g.L, py); scrivi(meno(y), g.L - 7, py, { align: "right", base: "middle", colore: tav.tenue, font: f12, forza: true }); }
    }
    ctx.fillStyle = tav.inchiostro; ctx.font = f12;
    ctx.textAlign = "center"; ctx.textBaseline = "bottom";
    const tx = psi ? "Temperatura a bulbo secco T [°C]" : "Umidità specifica x [g/kg aria secca]";
    const ty = psi ? "Umidità specifica x [g/kg aria secca]" : "Temperatura [°C] (coordinata di Mollier)";
    ctx.fillText(tx, g.L + g.pw / 2, H - 4);
    ctx.save();
    // a destra il titolo si legge dall'alto in basso, a sinistra dal basso in alto; le lettere verso l'interno
    ctx.translate(psi ? W - 3 : 3, g.T + g.ph / 2); ctx.rotate(psi ? Math.PI / 2 : -Math.PI / 2);
    ctx.textAlign = "center"; ctx.textBaseline = "top";
    ctx.fillText(ty, 0, 0);
    ctx.restore();
    // ---- etichette delle curve (dopo i punti, saltano se si sovrappongono)
    const lbl = { font: f10, limiti: lim, sfondo: tav.fondo || null };
    const fuori = (u, v) => g.X(u) < g.L - 0.5 || g.X(u) > g.L + g.pw + 0.5 || g.Y(v) < g.T - 0.5 || g.Y(v) > g.T + g.ph + 0.5;
    const ultimoDentro = (pts) => { for (let i = pts.length - 1; i >= 0; i--) if (!fuori(...pts[i])) return pts[i]; return null; };
    const primoDentro = (pts) => { for (const q of pts) if (!fuori(...q)) return q; return null; };
    // x (pixel) della curva all'altezza py: l'incrocio più vicino al bordo alto
    const xAllaY = (pts, py) => {
      let r = NaN;
      for (let i = 1; i < pts.length; i++) {
        const y0 = g.Y(pts[i - 1][1]), y1 = g.Y(pts[i][1]);
        if ((y0 - py) * (y1 - py) <= 0 && y0 !== y1) { const x0 = g.X(pts[i - 1][0]), x1 = g.X(pts[i][0]); r = x0 + (x1 - x0) * (py - y0) / (y1 - y0); }
      }
      return r;
    };
    C.ur.forEach((s) => {
      const q = ultimoDentro(s.pts); if (!q) return;
      const inAlto = g.Y(q[1]) < g.T + 14;
      const testo = s.phi === 1 ? "UR 100 %" : s.nome, colore = s.phi === 1 ? tav.inchiostro : tav.ur;
      if (inAlto) {
        // in alto: a sinistra della propria curva, per tutta l'altezza della scritta (prima era centrata sull'incrocio:
        // «UR 100 %» tagliata dalla curva di saturazione e «90 %» saltata perché coperta)
        const xb = xAllaY(s.pts, g.T + 17), xa = g.X(q[0]);
        const xd = Math.min(xa, Number.isFinite(xb) ? xb : xa) - 4;
        scrivi(testo, xd, g.T + 3, { ...lbl, align: "right", base: "top", colore });
      } else scrivi(testo, g.X(q[0]) - 3, g.Y(q[1]) - 2, { ...lbl, align: "right", base: "bottom", colore });
    });
    C.h.forEach((s) => {
      const q = psi ? primoDentro(s.pts) : primoDentro(s.pts); if (!q) return;
      if (psi) scrivi(s.nome, g.X(q[0]) - 3, g.Y(q[1]) - 1, { ...lbl, align: "right", base: "bottom", colore: tav.entalpia });
      else scrivi(s.nome, g.X(q[0]) + 3, g.Y(q[1]) + 2, { ...lbl, align: "left", base: "top", colore: tav.entalpia });
    });
    C.v.forEach((s) => {
      const q = psi ? s.pts[1] : s.pts[Math.floor(s.pts.length / 2)]; if (!q || fuori(...q)) return;
      scrivi(s.nome, g.X(q[0]) + 3, g.Y(q[1]), { ...lbl, align: "left", base: "middle", colore: tav.volume });
    });
    if (!psi) C.iso5.forEach((s) => {
      const q = s.pts[1]; if (fuori(...q)) return;
      const dx = s.valore <= 30 ? 4 : -4;
      scrivi(s.nome, g.X(q[0]) + dx, g.Y(q[1]), { ...lbl, align: dx > 0 ? "left" : "right", base: "middle", colore: tav.isoterme5 });
    });
    if (didascalia) {
      if (psi) scrivi(didascalia, g.L + 6, g.T + 6, { font: f10, align: "left", base: "top", colore: tav.tenue, forza: true });
      else scrivi(didascalia, g.L + g.pw - 6, g.T + g.ph - 6, { font: f10, align: "right", base: "bottom", colore: tav.tenue, forza: true });
    }
    return g;
  }

  // ------------------------------------------------------------------ nuvole: accumulo per pixel
  const ALFA_LUT = new Map();
  function lut(a) {
    const k = Math.round(a * 1000);
    if (ALFA_LUT.has(k)) return ALFA_LUT.get(k);
    const t = new Uint8ClampedArray(4097);
    for (let c = 0; c <= 4096; c++) t[c] = Math.round(255 * (1 - Math.pow(1 - a, c)));
    ALFA_LUT.set(k, t);
    return t;
  }
  function alfaAuto(n) { return Math.max(0.03, Math.min(0.9, 25 / Math.sqrt(Math.max(1, n)))); }
  // conteggi (Uint16Array gw×gh) dei punti per pixel dell'area del grafico; scala = pixel del dispositivo per px CSS
  function conta(s, g, scala) {
    const gw = Math.max(1, Math.round(g.pw * scala)), gh = Math.max(1, Math.round(g.ph * scala));
    const raggio = (s.opz.raggio || 1) * scala, densita = s.modoNuvola(gw) === "densita";
    const cella = densita ? Math.max(1, Math.round((s.opz.cella || 4) * scala)) : 1;
    const cw = Math.ceil(gw / cella), ch = Math.ceil(gh / cella);
    const cnt = new Uint16Array(cw * ch);
    const T = s.dati.t, X = s.dati.x, idx = s.dati.indici, n = idx ? idx.length : T.length;
    const psi = g.modo === "psicrometrico";
    const su = gw / (g.u1 - g.u0) / cella, sv = gh / (g.v1 - g.v0) / cella, u0 = g.u0, v1 = g.v1;
    const nucleo = [];
    if (!densita && raggio > 0.75) {
      const r = raggio, R = Math.ceil(r);
      for (let dy = -R; dy <= R; dy++) for (let dx = -R; dx <= R; dx++) if (dx * dx + dy * dy <= r * r + 0.25) nucleo.push(dy * cw + dx, dx, dy);
    }
    for (let k = 0; k < n; k++) {
      const i = idx ? idx[k] : k, t = T[i], x = X[i];
      if (!(t === t) || !(x === x)) continue;
      const u = psi ? t : x * 1000, v = psi ? x * 1000 : t * (1 + KM * x);
      const px = Math.floor((u - u0) * su), py = Math.floor((v1 - v) * sv);
      if (px < 0 || py < 0 || px >= cw || py >= ch) continue;
      if (!nucleo.length) { const j = py * cw + px; if (cnt[j] < 65535) cnt[j]++; continue; }
      for (let q = 0; q < nucleo.length; q += 3) {
        const xx = px + nucleo[q + 1], yy = py + nucleo[q + 2];
        if (xx < 0 || yy < 0 || xx >= cw || yy >= ch) continue;
        const j = yy * cw + xx;
        if (cnt[j] < 65535) cnt[j]++;
      }
    }
    return { cnt, gw, gh, cella, cw, ch, densita, n, nucleo: Math.max(1, nucleo.length / 3) };
  }
  function colora(acc, colore, alfa) {
    const { cnt, gw, gh, cella, cw, densita } = acc;
    const c = document.createElement("canvas"); c.width = gw; c.height = gh;
    const g2 = c.getContext("2d"), im = g2.createImageData(gw, gh), d = im.data;
    const [R, G, B] = rgb(colore);
    if (!densita) {
      const L = lut(alfa);
      for (let j = 0; j < cnt.length; j++) {
        const v = cnt[j]; if (!v) continue;
        const o = j * 4; d[o] = R; d[o + 1] = G; d[o + 2] = B; d[o + 3] = L[v > 4096 ? 4096 : v];
      }
    } else {
      let max = 0;
      for (let j = 0; j < cnt.length; j++) if (cnt[j] > max) max = cnt[j];
      const lm = Math.log1p(max || 1);
      for (let j = 0; j < cnt.length; j++) {
        const v = cnt[j]; if (!v) continue;
        const a = Math.round(255 * (0.14 + 0.86 * Math.log1p(v) / lm));
        const cx = (j % cw) * cella, cy = Math.floor(j / cw) * cella;
        for (let yy = cy; yy < Math.min(gh, cy + cella); yy++) for (let xx = cx; xx < Math.min(gw, cx + cella); xx++) {
          const o = (yy * gw + xx) * 4; d[o] = R; d[o + 1] = G; d[o + 2] = B; d[o + 3] = a;
        }
      }
    }
    g2.putImageData(im, 0, 0);
    return c;
  }

  // ------------------------------------------------------------------ il componente
  let numero = 0;
  function crea(box, opz = {}) {
    if (!box) return null;
    const id = `diagramma-aria-${++numero}`;
    // (20/11/2026) collegamento a questa simulazione: ?diagramma=mollier nell'indirizzo (solo il primo diagramma della pagina)
    const linkModo = numero === 1 && typeof location !== "undefined" ? new URLSearchParams(location.search).get("diagramma") : null;
    if (linkModo === "mollier" || linkModo === "psicrometrico") opz = { ...opz, modo: linkModo };
    const st = { modo: opz.modo === "mollier" ? "mollier" : "psicrometrico", p: opz.pressione || 101325, strati: new Map(), ordine: 0,
      titolo: opz.titolo || "Diagramma dell'aria umida", attesa: 0, g: null, ascolta: { modo: [] }, evidenzia: null };
    box.classList.add("aria-diagramma");
    box.innerHTML = "";
    // comandi: Psicrometrico / Mollier
    const comandi = h("div", "aria-diagramma-comandi");
    const gruppo = h("div", "aria-vista"); gruppo.setAttribute("role", "group"); gruppo.setAttribute("aria-label", "Tipo di diagramma");
    const pulsanti = {};
    [["psicrometrico", "Psicrometrico"], ["mollier", "Mollier"]].forEach(([k, t]) => {
      const b = h("button", "bottone secondario piccolo", t); b.type = "button"; b.dataset.modo = k;
      b.title = k === "psicrometrico" ? "Diagramma psicrometrico (T in ascissa, x in ordinata)" : "Diagramma di Mollier (x in ascissa, T e h in ordinata)";
      b.addEventListener("click", () => api.modo(k));
      pulsanti[k] = b; gruppo.appendChild(b);
    });
    comandi.appendChild(gruppo);
    const area = h("div", "aria-diagramma-area");
    const canvas = h("canvas", "aria-diagramma-canvas");
    canvas.setAttribute("role", "img");
    canvas.id = id;
    area.appendChild(canvas);
    const legenda = h("div", "aria-legenda");
    const chiave = h("p", "aiuto aria-legenda-curve");
    const scarica = h("div", "scarica aria-scarica");
    scarica.appendChild(h("span", "scarica-titolo", "Scarica l'immagine:"));
    const msg = h("div", "messaggio aria-messaggio-immagine"); msg.setAttribute("role", "status"); msg.setAttribute("aria-live", "polite");
    ["png", "svg"].forEach((f) => {
      const b = h("button", "bottone secondario piccolo", f.toUpperCase()); b.type = "button"; b.dataset.formato = f;
      b.title = `Scarica il diagramma in ${f.toUpperCase()} (colori di stampa), con le fonti`;
      b.addEventListener("click", () => scaricaFile(f, b));
      scarica.appendChild(b);
    });
    box.append(comandi, area, legenda, chiave, scarica, msg);
    const sugg = h("div", "grafico-suggerimento aria-suggerimento"); sugg.setAttribute("aria-hidden", "true");
    document.body.appendChild(sugg);

    function aggiornaPulsanti() {
      for (const [k, b] of Object.entries(pulsanti)) b.setAttribute("aria-pressed", String(k === st.modo));
      canvas.setAttribute("aria-label", `${st.titolo}: ${st.modo === "psicrometrico" ? "diagramma psicrometrico" : "diagramma di Mollier"}`);
      chiave.textContent = st.modo === "psicrometrico"
        ? "Curva nera spessa: saturazione (UR 100 %); grigie: umidità relativa 10…90 %; blu: entalpia costante h [kJ/kg]; verdi tratteggiate: volume specifico v [m³/kg]."
        : "Rette grigie quasi orizzontali: isoterme ogni 1 °C (etichette ogni 5 °C); curva nera: saturazione; grigie: UR 10…90 %; blu: entalpia h [kJ/kg]; verdi tratteggiate: volume specifico v [m³/kg]. Y = (h − 2501·x)/1,006.";
    }

    // ---- misure e ridisegno
    function misure() {
      const W = Math.max(280, Math.floor(area.clientWidth || box.clientWidth || 640));
      const prop = opz.proporzione || 1.38;
      const H = Math.round(Math.max(280, Math.min(W / prop, Math.max(340, (window.innerHeight || 800) * 0.8))));
      return { W, H };
    }
    function nuvolaPagina(s, g) {
      const scala = window.devicePixelRatio || 1;
      const k = `${g.modo}|${Math.round(g.pw * scala)}x${Math.round(g.ph * scala)}|${s.versione}`;
      if (!s.copia || s.copia.k !== k) s.copia = { k, acc: conta(s, g, scala), col: null };
      const tav = tavolozzaPagina(), colore = risolvi(s.opz.colore || s.colore, tav);
      const alfa = s.opz.alpha || alfaAuto(s.copia.acc.n) / Math.sqrt(s.copia.acc.nucleo);
      if (!s.copia.col || s.copia.col.colore !== colore || s.copia.col.alfa !== alfa) s.copia.col = { colore, alfa, c: colora(s.copia.acc, colore, alfa) };
      return s.copia.col.c;
    }
    function ridisegna() {
      cancelAnimationFrame(st.attesa);
      st.attesa = requestAnimationFrame(disegnaOra);
    }
    function disegnaOra() {
      const { W, H } = misure(), dpr = window.devicePixelRatio || 1;
      if (canvas.width !== Math.round(W * dpr) || canvas.height !== Math.round(H * dpr)) {
        canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
      }
      canvas.style.width = `${W}px`; canvas.style.height = `${H}px`;
      const ctx = canvas.getContext("2d");
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      st.g = disegna(ctx, W, H, { modo: st.modo, p: st.p, tav: tavolozzaPagina(), strati: [...st.strati.values()], nuvola: nuvolaPagina,
        didascalia: didascalia(), evidenzia: st.evidenzia });
      st.W = W; st.H = H;
    }
    const didascalia = () => `p = ${fmt(st.p)} Pa`;

    // ---- strati
    function aggiungi(tipo, nome, dati) {
      const prima = st.strati.get(nome);
      const s = { tipo, nome, visibile: prima ? prima.visibile : (dati.opz && dati.opz.visibile === false ? false : true),
        ordine: prima ? prima.ordine : ++st.ordine, versione: (prima ? prima.versione : 0) + 1, opz: {}, ...dati };
      st.strati.set(nome, s);
      legendaOra();
      ridisegna();
      return api;
    }
    const xDi = (q) => (Number.isFinite(q.x) ? q.x : Number.isFinite(q.xg) ? q.xg / 1000 : P.xDaUR(q.t, q.ur, st.p));
    const norm = (q) => ({ ...q, t: q.t, x: xDi(q) });
    function poligonoZona(def) {
      if (Array.isArray(def)) return def.map(norm);
      const N = 24, out = [];
      if (Number.isFinite(def.urMin) || Number.isFinite(def.urMax)) {            // T da/a, UR da/a: lati curvi
        const a = def.tMin, b = def.tMax, u0 = def.urMin || 0, u1 = def.urMax || 100;
        for (let i = 0; i <= N; i++) { const t = a + (b - a) * i / N; out.push({ t, x: P.xDaUR(t, u0, st.p) }); }
        for (let i = 0; i <= N; i++) { const t = b - (b - a) * i / N; out.push({ t, x: P.xDaUR(t, u1, st.p) }); }
        return out;
      }
      const x0 = Number.isFinite(def.xgMin) ? def.xgMin / 1000 : (def.xMin || 0), x1 = Number.isFinite(def.xgMax) ? def.xgMax / 1000 : (def.xMax || 0.03);
      const a = def.tMin, b = def.tMax;
      const lato = (p0, p1) => { for (let i = 0; i < N; i++) out.push({ t: p0.t + (p1.t - p0.t) * i / N, x: p0.x + (p1.x - p0.x) * i / N }); };
      lato({ t: a, x: x0 }, { t: b, x: x0 }); lato({ t: b, x: x0 }, { t: b, x: x1 }); lato({ t: b, x: x1 }, { t: a, x: x1 }); lato({ t: a, x: x1 }, { t: a, x: x0 });
      return out;
    }
    function puntiRetta(q, dir, o) {
      const A = norm(q);
      let dt, dx;               // direzione in (T [K], x [kg/kg])
      const cp = P.cpUmido(A.x);
      if (dir.verso) { const B = norm(dir.verso); dt = B.t - A.t; dx = B.x - A.x; }
      else if (Number.isFinite(dir.R)) { const R = dir.R; dt = R * P.R0; dx = (1 - R) * cp; }       // ΔT/Δx = R·r0/((1−R)·cp)
      else if (Number.isFinite(dir.pendenza)) { dt = (dir.pendenza - P.R0); dx = cp; }              // Δh/Δx in kJ/kg
      else throw new Error("retta: serve R, pendenza (Δh/Δx) o verso");
      const nrm = Math.hypot(dt / 60, dx / 0.03) || 1;
      dt /= nrm; dx /= nrm;     // un passo = tutta la scala
      const k0 = o.estensione === undefined || o.estensione === "intera" ? -2 : 0;
      // estensione numerica (solo con «verso»): segmento da A a A + estensione·(B − A), come la retta ambiente del foglio (×2)
      const k1 = typeof o.estensione === "number" && dir.verso ? o.estensione * nrm : 2;
      const out = [];
      for (let i = 0; i <= 80; i++) { const k = k0 + (k1 - k0) * i / 80; out.push({ t: A.t + k * dt, x: A.x + k * dx }); }
      return out;
    }

    function legendaOra() {
      legenda.innerHTML = "";
      const tav = tavolozzaPagina();
      [...st.strati.values()].sort((a, b) => a.ordine - b.ordine).forEach((s) => {
        if (s.opz.legenda === false) return;
        const l = h("label", "casella aria-voce-legenda");
        const c = document.createElement("input"); c.type = "checkbox"; c.checked = s.visibile;
        c.addEventListener("change", () => { s.visibile = c.checked; ridisegna(); });
        const camp = h("span", `aria-segno aria-segno-${s.tipo}`); camp.setAttribute("aria-hidden", "true");
        camp.style.setProperty("--colore-strato", s.opz.colore && s.opz.colore.startsWith("var(") ? s.opz.colore : risolvi(s.opz.colore || s.colore, tav));
        l.append(c, camp, ` ${s.opz.etichetta || s.nome}`);
        if (s.opz.nota) l.appendChild(h("span", "aria-nota-legenda", ` ${s.opz.nota}`));
        legenda.appendChild(l);
      });
      legenda.hidden = !legenda.childElementCount;
    }

    // ---- suggerimento
    function contenuto(px, py, g, nuvolaConta) {
      if (!g || !g.dentro(px, py)) return null;
      const c = g.inv(px, py);
      const righe = [];
      const ur = P.pwDaX(c.x, st.p) / P.psat(c.t) * 100;
      righe.push([null, `T ${fmt(c.t, 1)} °C · UR ${ur > 100 ? "oltre 100" : fmt(ur, 0)} %`]);
      righe.push([null, `x ${fmt(c.x * 1000, 1)} g/kg · h ${fmt(P.entalpia(c.t, c.x), 1)} kJ/kg`]);
      let vicino = null, dmin = 12;
      for (const s of st.strati.values()) {
        if (!s.visibile) continue;
        const qs = s.tipo === "punto" ? [{ ...s.punto, etichetta: s.opz.etichetta }] : s.tipo === "spezzata" ? s.punti : [];
        for (const q of qs) {
          const [x, y] = g.px(q.t, q.x), d = Math.hypot(x - px, y - py);
          if (d < dmin) { dmin = d; vicino = { q, s }; }
        }
      }
      if (vicino) {
        const q = vicino.q, u = P.pwDaX(q.x, st.p) / P.psat(q.t) * 100, col = risolvi(vicino.s.opz.colore || vicino.s.colore, tavolozzaPagina());
        righe.push([col, `${q.etichetta || vicino.s.opz.etichetta || vicino.s.nome}: ${fmt(q.t, 1)} °C, UR ${fmt(u, 0)} %, x ${fmt(q.x * 1000, 2)} g/kg, h ${fmt(P.entalpia(q.t, q.x), 1)} kJ/kg`]);
      }
      if (nuvolaConta) for (const s of st.strati.values()) {
        if (!s.visibile || s.tipo !== "nuvola" || !s.copia) continue;
        const n = nuvolaConta(s, px, py);
        if (n > 0) righe.push([risolvi(s.opz.colore || s.colore, tavolozzaPagina()), `${s.opz.etichetta || s.nome}: ${fmt(n)} ${n === 1 ? "ora" : "ore"} qui`]);
      }
      return { titolo: st.modo === "psicrometrico" ? "Diagramma psicrometrico" : "Diagramma di Mollier", righe, vicino };
    }
    function contaPagina(s, px, py) {
      const a = s.copia && s.copia.acc, g = st.g; if (!a) return 0;
      const scala = a.gw / g.pw;
      const cx = Math.floor((px - g.L) * scala / a.cella), cy = Math.floor((py - g.T) * scala / a.cella);
      const r = a.densita ? 0 : Math.max(1, Math.round(2 * scala));
      let n = 0;
      for (let y = cy - r; y <= cy + r; y++) for (let x = cx - r; x <= cx + r; x++) if (x >= 0 && y >= 0 && x < a.cw && y < a.ch) n += a.cnt[y * a.cw + x];
      return Math.round(n / (a.densita ? 1 : a.nucleo));
    }
    function mostraSugg(c, cx, cy) {
      if (!c) { sugg.style.display = "none"; return; }
      sugg.innerHTML = "";
      sugg.appendChild(h("b", null, c.titolo));
      for (const [col, t] of c.righe) {
        const d = h("div"), q = h("i");
        if (col) q.style.background = col; else q.className = "vuoto";
        d.append(q, t); sugg.appendChild(d);
      }
      sugg.style.display = "block";
      const w = sugg.offsetWidth, hh = sugg.offsetHeight;
      let x = cx + 14, y = cy + 14;
      if (x + w > innerWidth - 4) x = cx - 14 - w;
      if (y + hh > innerHeight - 4) y = cy - 14 - hh;
      sugg.style.left = `${Math.max(4, x)}px`; sugg.style.top = `${Math.max(4, y)}px`;
    }
    canvas.addEventListener("pointermove", (e) => {
      const r = canvas.getBoundingClientRect();
      mostraSugg(contenuto(e.clientX - r.left, e.clientY - r.top, st.g, contaPagina), e.clientX, e.clientY);
    });
    canvas.addEventListener("pointerleave", () => mostraSugg(null));
    canvas.addEventListener("pointerdown", (e) => {
      if (e.pointerType !== "touch") return;
      const r = canvas.getBoundingClientRect();
      mostraSugg(contenuto(e.clientX - r.left, e.clientY - r.top, st.g, contaPagina), e.clientX, e.clientY);
      clearTimeout(st.tocco); st.tocco = setTimeout(() => mostraSugg(null), 3500);
    });
    addEventListener("scroll", () => mostraSugg(null), { passive: true, capture: true });

    // ---- SVG (esportazione e riquadro ↗)
    function nuvolaFissa(scala, tav) {
      return (s, g) => {
        const acc = conta(s, g, scala);
        return colora(acc, risolvi(s.opz.colore || s.colore, tav), s.opz.alpha || alfaAuto(acc.n) / Math.sqrt(acc.nucleo));
      };
    }
    // legenda nelle immagini scaricate (14/11/2026): gli strati visibili con nome, colore e nota (per esempio le ore),
    // messi in fila su più righe sotto il diagramma, prima delle righe della fascia
    function legendaFascia(W, tav) {
      const voci = [...st.strati.values()].filter((s) => s.visibile && s.opz.legenda !== false).sort((a, b) => a.ordine - b.ordine)
        .map((s) => ({ tipo: s.tipo, colore: risolvi(s.opz.colore || s.colore, tav), tratteggio: s.tipo === "retta" || (s.opz.tratteggio && s.opz.tratteggio.length),
          testo: `${s.opz.etichetta || s.nome}${s.opz.nota ? ` ${s.opz.nota}` : ""}` }));
      const righe = [];
      let riga = [], x = 12;
      for (const v of voci) {
        const w = 30 + v.testo.length * 6.4 + 18;
        if (riga.length && x + w > W - 12) { righe.push(riga); riga = []; x = 12; }
        riga.push({ ...v, x }); x += w;
      }
      if (riga.length) righe.push(riga);
      return righe;
    }
    function disegnaLegenda(ctx, righe, y0, rh) {
      righe.forEach((riga, i) => {
        const y = y0 + rh * i + 8;
        riga.forEach((v) => {
          ctx.save();
          ctx.strokeStyle = v.colore; ctx.fillStyle = v.colore; ctx.setLineDash([]);
          if (v.tipo === "nuvola") { ctx.globalAlpha = 0.8; ctx.beginPath(); ctx.arc(v.x + 11, y, 5, 0, 2 * Math.PI); ctx.fill(); }
          else if (v.tipo === "zona") {
            ctx.globalAlpha = 0.22; ctx.fillRect(v.x + 2, y - 6, 20, 12); ctx.globalAlpha = 1; ctx.lineWidth = 1.5;
            ctx.beginPath(); ctx.rect(v.x + 2, y - 6, 20, 12); ctx.stroke();
          } else if (v.tipo === "punto") { ctx.beginPath(); ctx.moveTo(v.x + 11, y - 6); ctx.lineTo(v.x + 17, y); ctx.lineTo(v.x + 11, y + 6); ctx.lineTo(v.x + 5, y); ctx.closePath(); ctx.fill(); }
          else {
            ctx.lineWidth = v.tipo === "retta" ? 2 : 3; if (v.tratteggio) ctx.setLineDash([6, 4]);
            ctx.beginPath(); ctx.moveTo(v.x, y); ctx.lineTo(v.x + 22, y); ctx.stroke();
          }
          ctx.restore();
          ctx.save(); ctx.font = "12.5px Helvetica, Arial, sans-serif"; ctx.fillStyle = "#000"; ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
          ctx.fillText(v.testo, v.x + 30, y + 4.5); ctx.restore();
        });
      });
    }
    function svgDi(W, H, { stampa = true, fascia = null } = {}) {
      const tav = stampa ? tavolozzaStampa() : tavolozzaPagina();
      const c = new ContestoSvg(W, H);
      const g = disegna(c, W, H, { modo: st.modo, p: st.p, tav, strati: [...st.strati.values()], nuvola: nuvolaFissa(Math.min(2, (window.devicePixelRatio || 1) * 1.5), tav), didascalia: didascalia() });
      let corpo = c.testo(), Ht = H;
      if (fascia) {
        const righe = fascia, rh = 17, leg = legendaFascia(W, tav), hl = leg.length ? leg.length * rh + 6 : 0, alt = 14 + hl + righe.length * rh + 6;
        corpo += `\n<rect x="0" y="${H}" width="${W}" height="${alt}" fill="#ffffff"/><line x1="0" y1="${H + 0.5}" x2="${W}" y2="${H + 0.5}" stroke="#000" stroke-width="1"/>`;
        if (leg.length) { const cl = new ContestoSvg(W, alt); disegnaLegenda(cl, leg, H + 14, rh); corpo += `\n${cl.testo()}`; }
        righe.forEach((r, i) => { corpo += `\n<text x="12" y="${H + 14 + hl + rh * i + 12}" font-size="12.5" font-family="Helvetica, Arial, sans-serif"${r.grassetto ? ' font-weight="700"' : ""} fill="${r.colore || "#000"}">${esc(r.t)}</text>`; });
        Ht = H + alt;
      }
      const fondo = tav.fondo ? `<rect width="${W}" height="${Ht}" fill="${tav.fondo}"/>\n` : "";
      return { testo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${Ht}" width="${W}" height="${Ht}" role="img" aria-label="${esc(st.titolo)}">\n${fondo}${corpo}\n</svg>`, g, H: Ht };
    }
    function righeFascia(larghezza) {
      const r = [{ t: st.titolo, grassetto: true }];
      const av = typeof opz.avviso === "function" ? opz.avviso() : opz.avviso;
      if (av) r.push({ t: av, grassetto: true, colore: "#8a1c1c" });
      const fonti = typeof opz.fonti === "function" ? opz.fonti() : (opz.fonti || []);
      fonti.filter(Boolean).forEach((t) => r.push({ t }));
      r.push({ t: `${st.modo === "psicrometrico" ? "Diagramma psicrometrico" : "Diagramma di Mollier"}, pressione ${fmt(st.p)} Pa. Proprietà dell'aria umida ASHRAE 2017 (Hyland–Wexler).` });
      r.push({ t: `Fonte: EuGEnio – eugenio.statocritico.it (CC BY 4.0) · vista del ${new Date().toLocaleString("it-IT", { dateStyle: "short", timeStyle: "short" })}` });
      // a capo con una stima della larghezza (Helvetica 12,5 px ≈ 6,4 px a carattere)
      const max = Math.max(40, Math.floor((larghezza - 24) / 6.4)), out = [];
      for (const x of r) {
        let riga = "";
        for (const p of x.t.split(/\s+/)) { if ((riga + " " + p).trim().length > max && riga) { out.push({ ...x, t: riga }); riga = p; } else riga = (riga + " " + p).trim(); }
        if (riga) out.push({ ...x, t: riga });
      }
      return out;
    }
    const DIM = { W: 1200, H: 840 };
    function esportaSvg() { return svgDi(DIM.W, DIM.H, { stampa: true, fascia: righeFascia(DIM.W) }).testo; }
    function esportaPng(scala = 2) {
      return new Promise((ok, no) => {
        const tav = tavolozzaStampa();
        const righe = righeFascia(DIM.W), W = DIM.W, H = DIM.H, rh = 17, leg = legendaFascia(W, tav), hl = leg.length ? leg.length * rh + 6 : 0;
        const alt = 14 + hl + righe.length * rh + 6;
        const c = document.createElement("canvas"); c.width = W * scala; c.height = (H + alt) * scala;
        const ctx = c.getContext("2d"); ctx.setTransform(scala, 0, 0, scala, 0, 0);
        disegna(ctx, W, H, { modo: st.modo, p: st.p, tav, strati: [...st.strati.values()], nuvola: nuvolaFissa(scala, tav), didascalia: didascalia() });
        ctx.fillStyle = "#fff"; ctx.fillRect(0, H, W, alt); ctx.fillStyle = "#000"; ctx.fillRect(0, H, W, 1);
        disegnaLegenda(ctx, leg, H + 14, rh);
        ctx.textBaseline = "alphabetic"; ctx.textAlign = "left";
        righe.forEach((r, i) => { ctx.font = `${r.grassetto ? "bold " : ""}12.5px Helvetica, Arial, sans-serif`; ctx.fillStyle = r.colore || "#000"; ctx.fillText(r.t, 12, H + 14 + hl + rh * i + 12); });
        c.toBlob((b) => (b ? ok(b) : no(new Error("immagine vuota"))), "image/png");
      });
    }
    async function salva(b, nome) {
      if (window.EUGENIO_ESPORTA && window.EUGENIO_ESPORTA.salva) return window.EUGENIO_ESPORTA.salva(b, nome, null);
      const url = URL.createObjectURL(b);
      const a = document.createElement("a"); a.href = url; a.download = nome; a.rel = "noopener"; a.hidden = true;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10 * 60 * 1000);
      return { modo: "avviato", nome, byte: b.size, url };
    }
    async function scaricaFile(formato, bottone) {
      const base = (typeof opz.nomeFile === "function" ? opz.nomeFile() : opz.nomeFile) || "diagramma-aria";
      const nome = `${base}-${st.modo}.${formato}`;
      try {
        if (bottone) bottone.disabled = true;
        msg.classList.remove("errore"); msg.textContent = `Preparo l'immagine (${formato.toUpperCase()})…`;
        const b = formato === "svg" ? new Blob([esportaSvg()], { type: "image/svg+xml" }) : await esportaPng(2);
        const r = await salva(b, nome);
        const kb = `${fmt(r.byte / 1024, 0)} kB`;
        msg.textContent = `Download avviato dal browser: ${r.nome} (${kb}). Se non compare tra i download, usa il collegamento:`;
        if (r.url) { const a = h("a", "salva-a-mano", `Salva ${r.nome}`); a.href = r.url; a.download = r.nome; msg.append(" ", a); }
      } catch (e) { msg.classList.add("errore"); msg.textContent = `Immagine non scaricata: ${e.message || e}.`; }
      finally { if (bottone) bottone.disabled = false; }
    }

    // riquadro flottante di grafici.js: in pagina un segnaposto invisibile (il pulsante ↗), nel riquadro l'SVG completo
    const apri = h("div", "aria-diagramma-apri");
    comandi.appendChild(apri);
    function registraRiquadro() {
      const G = window.EUGENIO_GRAFICI;
      if (!G) return;
      G.registra(apri, (dest, m) => {
        if (!m.riquadro) { const s = document.createElementNS("http://www.w3.org/2000/svg", "svg"); s.setAttribute("aria-hidden", "true"); s.setAttribute("class", "aria-segnaposto"); dest.appendChild(s); return; }
        const W = Math.max(320, m.larghezza), H = Math.max(240, m.altezza);
        const r = svgDi(W, H, { stampa: false });
        dest.insertAdjacentHTML("beforeend", r.testo.replace(/ width="\d+" height="\d+"/, ""));
        const svg = dest.querySelector("svg");
        svg.addEventListener("pointermove", (e) => {
          const ctm = svg.getScreenCTM(); if (!ctm) return;
          const q = new DOMPoint(e.clientX, e.clientY).matrixTransform(ctm.inverse());
          mostraSugg(contenuto(q.x, q.y, r.g, null), e.clientX, e.clientY);
        });
        svg.addEventListener("pointerleave", () => mostraSugg(null));
        const l = legenda.cloneNode(true);
        l.querySelectorAll("input").forEach((i) => { i.disabled = true; });
        dest.appendChild(l);
      }, { titolo: st.titolo, adatta: false });
    }

    // ---- API
    const api = {
      elemento: box,
      canvas,
      modo(m) {
        if (m === undefined) return st.modo;
        const nuovo = m === "mollier" ? "mollier" : "psicrometrico";
        if (nuovo !== st.modo) { st.modo = nuovo; aggiornaPulsanti(); ridisegna(); st.ascolta.modo.forEach((f) => f(nuovo)); }
        return api;
      },
      pressione(p) { if (p === undefined) return st.p; if (Number.isFinite(p) && p > 30000) { st.p = p; ridisegna(); } return api; },
      titolo(t) { if (t === undefined) return st.titolo; st.titolo = t; aggiornaPulsanti(); registraRiquadro(); return api; },
      // nuvola: dati = { t: Float32Array, x: Float32Array (kg/kg), indici?: Uint32Array } oppure [{ t, x }]
      nuvola(nome, colore, dati, o = {}) {
        let d = dati;
        if (Array.isArray(dati)) { d = { t: new Float32Array(dati.map((q) => q.t)), x: new Float32Array(dati.map((q) => xDi(q))) }; }
        else if (dati && !dati.t && dati.serie) d = { t: dati.serie.t, x: dati.x, indici: dati.indici };
        const s = { colore, dati: d, opz: o };
        s.modoNuvola = () => {
          const n = d.indici ? d.indici.length : d.t.length;
          return o.modo === "densita" || (o.modo === "auto" && n > (o.soglia || 300000)) ? "densita" : "punti";
        };
        return aggiungi("nuvola", nome, s);
      },
      spezzata(nome, punti, o = {}) { return aggiungi("spezzata", nome, { punti: punti.map(norm), colore: o.colore, opz: o }); },
      punto(nome, q, o = {}) { return aggiungi("punto", nome, { punto: norm(q), colore: o.colore, opz: o }); },
      zona(nome, def, o = {}) { return aggiungi("zona", nome, { poligono: poligonoZona(def), colore: o.colore, opz: o }); },
      retta(nome, q, dir, o = {}) { return aggiungi("retta", nome, { punti: puntiRetta(q, dir, o), colore: o.colore, opz: o }); },
      togli(nome) { if (st.strati.delete(nome)) { legendaOra(); ridisegna(); } return api; },
      svuota() { st.strati.clear(); legendaOra(); ridisegna(); return api; },
      mostra(nome, v) { const s = st.strati.get(nome); if (s) { s.visibile = v !== false; legendaOra(); ridisegna(); } return api; },
      strati: () => [...st.strati.values()].map((s) => ({ nome: s.nome, tipo: s.tipo, visibile: s.visibile })),
      evidenzia(q) { st.evidenzia = q ? norm(q) : null; ridisegna(); return api; },
      ridisegna() { ridisegna(); return api; },
      disegnaSubito() { disegnaOra(); return api; },
      coordinate(px, py) { return st.g && st.g.dentro(px, py) ? st.g.inv(px, py) : null; },
      pixel(t, x) { return st.g ? st.g.px(t, x) : null; },
      svg: (o = {}) => svgDi(o.larghezza || DIM.W, o.altezza || DIM.H, { stampa: o.stampa !== false, fascia: o.fascia === false ? null : righeFascia(o.larghezza || DIM.W) }).testo,
      png: (scala) => esportaPng(scala),
      scarica: (formato) => scaricaFile(formato === "svg" ? "svg" : "png"),
      su(evento, f) { if (st.ascolta[evento] && typeof f === "function") st.ascolta[evento].push(f); return api; },
    };
    aggiornaPulsanti();
    registraRiquadro();
    if ("ResizeObserver" in window) {
      let ultima = 0;
      new ResizeObserver(() => { const w = area.clientWidth; if (Math.abs(w - ultima) >= 2) { ultima = w; ridisegna(); } }).observe(area);
    }
    addEventListener("resize", ridisegna);
    document.addEventListener("eugenio:aspetto", () => { legendaOra(); ridisegna(); });
    document.addEventListener("eugenio:ridimensiona", ridisegna);
    disegnaOra();
    if (window.EUGENIO_COLLEGAMENTO && id === "diagramma-aria-1") {
      window.EUGENIO_COLLEGAMENTO.registra({ chiavi: ["diagramma"], leggi: () => ({ diagramma: st.modo === "mollier" ? "mollier" : null }) });
    }
    return api;
  }

  window.EUGENIO_DIAGRAMMA_ARIA = { crea, curve, COLORI, EXCEL, SCALA, ContestoSvg };
})();
