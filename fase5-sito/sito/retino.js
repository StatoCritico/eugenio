"use strict";
// Retino degli immobili pubblici (17/11/2026): righe oblique a 45° disegnate su una tela e registrate come immagine nella
// mappa MapLibre, da usare come «fill-pattern» (2D) e «fill-extrusion-pattern» (3D). Lo usano Territorio › Edifici pubblici
// (particelle con edifici) e Modelli 3D (edifici pubblici tra gli altri). Colore e spessore uguali ovunque: chi vede le
// righe oblique sa che è un immobile pubblico (legende delle due pagine).
//
//  EUGENIO_RETINO.aggiungi(mappa, { nome: "retino-pubblico", colore: "#c2185b", fondo: "rgba(…)" })  → nome dell'immagine
//  EUGENIO_RETINO.COLORE      colore delle righe (anche per legende e bordi)
//  EUGENIO_RETINO.campione()  piccolo canvas per le legende (stesso disegno)
(function () {
  const COLORE = "#c2185b";            // magenta scuro: si distingue da edifici DBTR, OSM, scelto, falde e FV
  const LATO = 12;                     // px del motivo (si ripete senza giunture)

  function disegna(colore = COLORE, fondo = "rgba(255,255,255,0.55)", lato = LATO, scala = 1) {
    const n = lato * scala, c = document.createElement("canvas");
    c.width = n; c.height = n;
    const x = c.getContext("2d");
    if (fondo) { x.fillStyle = fondo; x.fillRect(0, 0, n, n); }
    x.strokeStyle = colore; x.lineWidth = 2.2 * scala; x.lineCap = "square";
    // tre diagonali parallele: quella centrale e le due che continuano nelle copie vicine (nessuna giuntura)
    for (const d of [-n, 0, n]) { x.beginPath(); x.moveTo(d, n); x.lineTo(d + n, 0); x.stroke(); }
    return c;
  }

  function aggiungi(m, opz = {}) {
    const nome = opz.nome || "retino-pubblico";
    if (!m || (m.hasImage && m.hasImage(nome))) return nome;
    const r = window.devicePixelRatio > 1 ? 2 : 1;
    const c = disegna(opz.colore || COLORE, opz.fondo === undefined ? "rgba(255,255,255,0.55)" : opz.fondo, LATO, r);
    const dati = c.getContext("2d").getImageData(0, 0, c.width, c.height);
    m.addImage(nome, { width: c.width, height: c.height, data: new Uint8Array(dati.data.buffer) }, { pixelRatio: r });
    return nome;
  }

  function campione(dim = 14) {
    const c = disegna(COLORE, "rgba(255,255,255,0.7)", dim, 1);
    c.className = "campione-retino"; c.setAttribute("aria-hidden", "true");
    return c;
  }

  window.EUGENIO_RETINO = { aggiungi, disegna, campione, COLORE };
})();
