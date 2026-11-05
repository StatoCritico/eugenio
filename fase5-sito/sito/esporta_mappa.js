"use strict";
// Scarica la vista di una mappa MapLibre così come appare (Ortofoto, Modelli 3D; 05/11/2026), in JPG, PNG o PDF.
// Sotto l'immagine c'è sempre una fascia con titolo, licenza e citazione di ogni fonte visibile e «Fonte: EuGEnio –
// eugenio.statocritico.it»: la fascia fa parte dell'immagine, quindi resta anche se il file viene ritagliato male o
// inoltrato da solo. Nel PDF (A4 orizzontale, scritto qui senza librerie: un'immagine JPEG e testo Helvetica) le stesse
// righe ci sono anche come testo selezionabile. Tutto nel browser: niente va al server.
//
//  EUGENIO_ESPORTA.scarica(mappa, { formato: "jpg"|"png"|"pdf", nome, titolo, righe: [testo, …], avviso })
//  La mappa deve essere creata con canvasContextAttributes: { preserveDrawingBuffer: true } (altrimenti si ridisegna
//  prima di copiarla).
(function () {
  function aCapo(ctx, testo, larghezza) {
    const parole = String(testo).split(/\s+/), righe = [];
    let r = "";
    for (const p of parole) {
      const prova = r ? `${r} ${p}` : p;
      if (ctx.measureText(prova).width > larghezza && r) { righe.push(r); r = p; } else r = prova;
    }
    if (r) righe.push(r);
    return righe;
  }

  // canvas della mappa + fascia delle attribuzioni (testo nero su bianco, come i report)
  function componi(mappa, { titolo = "", righe = [], avviso = "" } = {}) {
    const src = mappa.getCanvas();
    const W = src.width, H = src.height, k = Math.max(1, W / 1200);
    const corpo = Math.round(13 * k), riga = Math.round(18 * k), margine = Math.round(14 * k);
    const prova = document.createElement("canvas").getContext("2d");
    prova.font = `${corpo}px Helvetica, Arial, sans-serif`;
    const testi = [];
    if (titolo) testi.push({ t: titolo, grassetto: true });
    if (avviso) testi.push({ t: avviso, grassetto: true, colore: "#8a1c1c" });
    righe.filter(Boolean).forEach((t) => testi.push({ t }));
    testi.push({ t: `Fonte: EuGEnio – eugenio.statocritico.it (CC BY 4.0) · vista del ${new Date().toLocaleString("it-IT", { dateStyle: "short", timeStyle: "short" })}` });
    const linee = [];
    for (const x of testi) {
      prova.font = `${x.grassetto ? "bold " : ""}${corpo}px Helvetica, Arial, sans-serif`;
      for (const l of aCapo(prova, x.t, W - 2 * margine)) linee.push({ ...x, t: l });
    }
    const fascia = 2 * margine + linee.length * riga;
    const c = document.createElement("canvas"); c.width = W; c.height = H + fascia;
    const g = c.getContext("2d");
    g.fillStyle = "#fff"; g.fillRect(0, 0, W, H + fascia);
    g.drawImage(src, 0, 0);
    g.fillStyle = "#000"; g.fillRect(0, H, W, Math.max(1, Math.round(k)));
    g.textBaseline = "top";
    linee.forEach((l, i) => {
      g.font = `${l.grassetto ? "bold " : ""}${corpo}px Helvetica, Arial, sans-serif`;
      g.fillStyle = l.colore || "#000";
      g.fillText(l.t, margine, H + margine + i * riga);
    });
    return { canvas: c, testi: testi.map((x) => x.t), larghezza: W, altezza: H + fascia };
  }

  const blob = (c, tipo, q) => new Promise((ok, no) => c.toBlob((b) => (b ? ok(b) : no(new Error("immagine non creata"))), tipo, q));
  function salva(b, nome) {
    const a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = nome;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }

  // ------------------------------------------------------------------ PDF minimo (una pagina A4 orizzontale)
  // Testo in WinAnsi (Helvetica standard): lettere accentate italiane, «–», «·», «€»; il resto diventa «?».
  const WIN = { "€": 0x80, "‚": 0x82, "„": 0x84, "…": 0x85, "‘": 0x91, "’": 0x92, "“": 0x93, "”": 0x94, "•": 0x95, "–": 0x96, "—": 0x97, "™": 0x99 };
  function winAnsi(s) {
    const out = [];
    for (const ch of String(s)) {
      const c = ch.codePointAt(0);
      let b = WIN[ch] !== undefined ? WIN[ch] : c >= 32 && c < 127 ? c : c >= 160 && c <= 255 ? c : c === 8217 ? 0x92 : 63;
      if (b === 40 || b === 41 || b === 92) out.push(92);          // ( ) \ si scrivono con la barra davanti
      out.push(b);
    }
    return out;
  }
  // larghezze di Helvetica (1/1000 dell'em) per andare a capo; valore medio per i caratteri non in tabella
  const LARG = { " ": 278, i: 222, l: 222, j: 222, f: 278, t: 278, r: 333, I: 278, ".": 278, ",": 278, ":": 278, ";": 278, "(": 333, ")": 333, "–": 556, m: 833, w: 722, M: 833, W: 944 };
  const largo = (s, corpo) => [...s].reduce((t, ch) => t + (LARG[ch] || (ch === ch.toUpperCase() && /[A-Z]/.test(ch) ? 667 : 556)), 0) * corpo / 1000;
  function righePdf(testo, corpo, w) {
    const parole = String(testo).split(/\s+/), out = [];
    let r = "";
    for (const p of parole) { const pr = r ? `${r} ${p}` : p; if (largo(pr, corpo) > w && r) { out.push(r); r = p; } else r = pr; }
    if (r) out.push(r);
    return out;
  }
  function pdf(jpeg, iw, ih, titolo, testi) {
    const PW = 842, PH = 595, M = 28, corpo = 8, interl = 10.5;
    const linee = [];
    if (titolo) linee.push({ t: titolo, b: true, c: 11 });
    for (const t of testi) for (const l of righePdf(t, corpo, PW - 2 * M)) linee.push({ t: l, b: false, c: corpo });
    const spazioTesto = 8 + linee.reduce((s, l) => s + (l.c > corpo ? 15 : interl), 0);
    const maxW = PW - 2 * M, maxH = PH - 2 * M - spazioTesto, s = Math.min(maxW / iw, maxH / ih);
    const dw = iw * s, dh = ih * s, x0 = M + (maxW - dw) / 2, y0 = PH - M - dh;
    const enc = new TextEncoder();
    let cont = `q ${dw.toFixed(2)} 0 0 ${dh.toFixed(2)} ${x0.toFixed(2)} ${y0.toFixed(2)} cm /Im1 Do Q\n`;
    const parti = [enc.encode(cont)];
    let y = y0 - 14;
    for (const l of linee) {
      parti.push(enc.encode(`BT /${l.b ? "F2" : "F1"} ${l.c} Tf ${M} ${y.toFixed(2)} Td (`), new Uint8Array(winAnsi(l.t)), enc.encode(") Tj ET\n"));
      y -= l.c > corpo ? 15 : interl;
    }
    const contenuto = concat(parti);
    const ogg = [];
    ogg.push(enc.encode("<< /Type /Catalog /Pages 2 0 R >>"));
    ogg.push(enc.encode("<< /Type /Pages /Kids [3 0 R] /Count 1 >>"));
    ogg.push(enc.encode(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${PW} ${PH}] /Resources << /XObject << /Im1 4 0 R >> /Font << /F1 5 0 R /F2 6 0 R >> >> /Contents 7 0 R >>`));
    ogg.push(concat([enc.encode(`<< /Type /XObject /Subtype /Image /Width ${iw} /Height ${ih} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpeg.length} >>\nstream\n`), jpeg, enc.encode("\nendstream")]));
    ogg.push(enc.encode("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"));
    ogg.push(enc.encode("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"));
    ogg.push(concat([enc.encode(`<< /Length ${contenuto.length} >>\nstream\n`), contenuto, enc.encode("\nendstream")]));
    const info = winAnsi(titolo || "Vista della mappa");
    ogg.push(concat([enc.encode("<< /Producer (EuGEnio - eugenio.statocritico.it) /Title ("), new Uint8Array(info), enc.encode(") >>")]));
    const pezzi = [enc.encode("%PDF-1.4\n%\xE2\xE3\xCF\xD3\n")], pos = [];
    let n = pezzi[0].length;
    ogg.forEach((o, i) => {
      pos.push(n);
      const a = enc.encode(`${i + 1} 0 obj\n`), b = enc.encode("\nendobj\n");
      pezzi.push(a, o, b); n += a.length + o.length + b.length;
    });
    let xref = `xref\n0 ${ogg.length + 1}\n0000000000 65535 f \n`;
    pos.forEach((p) => { xref += `${String(p).padStart(10, "0")} 00000 n \n`; });
    xref += `trailer\n<< /Size ${ogg.length + 1} /Root 1 0 R /Info ${ogg.length} 0 R >>\nstartxref\n${n}\n%%EOF\n`;
    pezzi.push(enc.encode(xref));
    return new Blob([concat(pezzi)], { type: "application/pdf" });
  }
  function concat(l) {
    const n = l.reduce((s, x) => s + x.length, 0), out = new Uint8Array(n);
    let k = 0; for (const x of l) { out.set(x, k); k += x.length; }
    return out;
  }

  async function scarica(mappa, opz = {}) {
    const formato = (opz.formato || "jpg").toLowerCase(), nome = opz.nome || "mappa";
    // immagine più nitida: la mappa si ridisegna per un momento a densità doppia (linee e testo; le foto restano quelle
    // delle tessere), poi torna com'era
    const pr0 = typeof mappa.getPixelRatio === "function" ? mappa.getPixelRatio() : null;
    const pr = pr0 ? Math.min(3, Math.max(2, pr0)) : null;
    if (pr && pr !== pr0) mappa.setPixelRatio(pr);
    let v;
    try {
      // un fotogramma nuovo prima di copiare (preserveDrawingBuffer tiene il contenuto), dopo l'arrivo delle tessere
      await new Promise((ok) => { const t = setTimeout(ok, 4000); mappa.once("idle", () => { clearTimeout(t); ok(); }); mappa.triggerRepaint(); });
      v = componi(mappa, opz);
    } finally { if (pr && pr !== pr0) mappa.setPixelRatio(pr0); }
    if (formato === "png") { salva(await blob(v.canvas, "image/png"), `${nome}.png`); return v; }
    const jpg = await blob(v.canvas, "image/jpeg", 0.9);
    if (formato === "pdf") {
      const b = new Uint8Array(await jpg.arrayBuffer());
      salva(pdf(b, v.canvas.width, v.canvas.height, opz.titolo || "", v.testi.slice(opz.titolo ? 1 : 0)), `${nome}.pdf`);
    } else salva(jpg, `${nome}.jpg`);
    return v;
  }

  // pulsanti «Scarica l'immagine: JPG · PNG · PDF» in un contenitore; opz() restituisce le opzioni al momento del clic
  // (o un testo: allora il download non si fa e il testo va nel messaggio)
  function pulsanti(dove, mappa, opz, messaggio, formati = ["jpg", "png", "pdf"]) {
    const box = document.createElement("div"); box.className = "scarica scarica-vista";
    const t = document.createElement("span"); t.className = "scarica-titolo"; t.textContent = "Scarica l'immagine:"; box.appendChild(t);
    for (const f of formati) {
      const b = document.createElement("button"); b.type = "button"; b.className = "bottone secondario"; b.dataset.formato = f;
      b.textContent = f.toUpperCase(); b.title = `Scarica la vista della mappa in ${f.toUpperCase()}, con licenze e citazioni delle fonti`;
      b.addEventListener("click", async () => {
        const m = typeof mappa === "function" ? mappa() : mappa;
        const o = typeof opz === "function" ? opz() : opz;
        if (!m) return;
        if (typeof o === "string") { if (messaggio) messaggio(o, true); return; }
        try { b.disabled = true; await scarica(m, { ...o, formato: f }); if (messaggio) messaggio(`Immagine scaricata (${f.toUpperCase()}), con le attribuzioni sotto la mappa.`); }
        catch (e) { if (messaggio) messaggio(`Immagine non scaricata: ${e.message || e}`, true); }
        finally { b.disabled = false; }
      });
      box.appendChild(b);
    }
    dove.appendChild(box);
    return box;
  }

  window.EUGENIO_ESPORTA = { scarica, componi, pulsanti, _pdf: pdf, _winAnsi: winAnsi };
})();
