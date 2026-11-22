"use strict";
// Cursore del periodo a due indicatori (22/11/2026, richiesta di Paolo), comune a «Suolo e aree agricole» (suolo.js) e
// «Produzione e consumi di elettricità» (elettricita.js). Due input range sovrapposti dentro .cursore-doppio (stile in
// stile.css): si muovono con il mouse, il dito e la tastiera (frecce, Pagina su/giù, Inizio, Fine: comportamento
// normale degli input range). Se un indicatore supera l'altro lo spinge con sé (inizio ≤ fine sempre). La parte scelta
// della guida è colorata con le variabili CSS --da e --a. All'apertura (imposta senza anni) tutti e due sull'ultimo anno.
//
// Uso:
//   const cur = EUGENIO_PERIODO.crea({
//     inizio: el, fine: el,           // i due input range
//     doppio: el,                     // lo span.cursore-doppio che li contiene
//     min: el, max: el,               // facoltativi: dove scrivere il primo e l'ultimo anno
//     etichetta: el,                  // facoltativo: dove scrivere il periodo scelto
//     testo: (a, b) => "…",           // facoltativo: testo dell'etichetta (predefinito «2025» o «2015–2025»)
//     cambia: (a, b, finale) => {},   // a ogni movimento (finale = true al rilascio, evento change)
//   });
//   cur.imposta(anni, a, b)  → [a, b]  // anni validi (crescenti); a, b vicini a quelli chiesti (0/null = ultimo anno)
//   cur.scrivi()                       // riscrive posizione ed etichetta (per esempio dopo un cambio del testo)
(function () {
  function crea(o) {
    const i0 = o.inizio, i1 = o.fine;
    let anni = [], a = null, b = null;
    const testo = o.testo || ((x, y) => (x === y ? String(y) : `${x}–${y}`));
    function scrivi() {
      if (!anni.length) return;
      const n = Math.max(1, anni.length - 1);
      i0.value = anni.indexOf(a); i1.value = anni.indexOf(b);
      if (o.doppio) { o.doppio.style.setProperty("--da", `${100 * i0.value / n}%`); o.doppio.style.setProperty("--a", `${100 * i1.value / n}%`); }
      // il cursore più in alto è quello che si prende per primo quando i due sono vicini: in fondo alla guida l'iniziale
      i0.style.zIndex = +i0.value === n ? 3 : 1; i1.style.zIndex = 2;
      i0.setAttribute("aria-valuetext", String(a)); i1.setAttribute("aria-valuetext", String(b));
      if (o.etichetta) o.etichetta.textContent = testo(a, b);
    }
    function imposta(nuovi, x, y) {
      anni = [...nuovi];
      if (!anni.length) { a = b = null; return [a, b]; }
      const ult = anni[anni.length - 1];
      const vicino = (v) => (anni.includes(v) ? v : anni.reduce((p, q) => (Math.abs(q - v) < Math.abs(p - v) ? q : p), ult));
      b = y ? vicino(+y) : ult; a = x ? vicino(+x) : b;
      if (a > b) a = b;
      i0.min = i1.min = 0; i0.max = i1.max = anni.length - 1;
      if (o.min) o.min.textContent = anni[0];
      if (o.max) o.max.textContent = ult;
      scrivi();
      return [a, b];
    }
    function muovi(chi, finale) {
      let p = +i0.value, q = +i1.value;
      if (p > q) { if (chi === i0) q = p; else p = q; i0.value = p; i1.value = q; }
      a = anni[p]; b = anni[q];
      if (o.cambia) o.cambia(a, b, finale);
      scrivi();
    }
    for (const el of [i0, i1]) {
      el.addEventListener("input", () => muovi(el, false));
      el.addEventListener("change", () => muovi(el, true));
    }
    return { imposta, scrivi, get inizio() { return a; }, get fine() { return b; }, get anni() { return anni; } };
  }
  window.EUGENIO_PERIODO = { crea };
})();
