/* Numeri nel testo mostrato (20/11/2026, regola in README_stile.md, «Numeri»): sempre con il punto delle migliaia,
   anche a 4 cifre (1.234, non 1234), e la virgola dei decimali.

   EUGENIO_NUMERI.formato(v, decimali = 0, minimi = decimali, vuoto = "–")
       testo del numero v con al più `decimali` cifre decimali e almeno `minimi` (formato(1234.5, 1) = "1.234,5",
       formato(0.25, 2, 0) = "0,25", formato(3, 2, 0) = "3"); `vuoto` se v non è un numero finito (null, "", NaN).
   EUGENIO_NUMERI.raggruppa(testo)
       mette il punto ogni tre cifre nella parte intera di un numero già scritto senza raggruppamento ("-12345,6" →
       "-12.345,6").

   Intl.NumberFormat("it-IT") raggruppa da solo solo da 5 cifre (12.345 ma 1234): si chiede useGrouping: "always"; dove
   il browser non lo conosce (controllo fatto una volta sola) si formatta senza raggruppamento e si mette il punto a mano
   (lo stesso ripiego che c'era in carichi.js ed elettricita.js).

   Solo per il testo mostrato: mai nei file CSV/Excel/ODS (lì i numeri restano numeri), negli indirizzi, nei campi
   modificabili, e mai per date, anni, codici (ISTAT, CAP, catastali) e numeri di versione.

   Caricato nella testa di ogni pagina (parti/testa.html), quindi prima degli script delle pagine; funziona anche nei
   Web Worker (importScripts) e in node (require), per i moduli comuni provati con node. */
(function (radice) {
  "use strict";
  const SEMPRE = (() => {
    try { return new Intl.NumberFormat("it-IT", { useGrouping: "always" }).format(1234) === "1.234"; } catch (e) { return false; }
  })();
  const formati = new Map();

  function raggruppa(testo) {
    return String(testo).replace(/^(\D*)(\d+)/, (_, segno, intera) => segno + intera.replace(/\B(?=(\d{3})+$)/g, "."));
  }

  function formato(v, decimali = 0, minimi = decimali, vuoto = "–") {
    if (v === null || v === undefined || v === "" || typeof v === "boolean") return vuoto;
    const x = +v;
    if (!Number.isFinite(x)) return vuoto;
    const mx = Math.max(0, Math.min(20, decimali | 0)), mn = Math.max(0, Math.min(mx, minimi | 0));
    const chiave = `${mn}|${mx}`;
    let f = formati.get(chiave);
    if (!f) {
      f = new Intl.NumberFormat("it-IT", { useGrouping: SEMPRE ? "always" : false, minimumFractionDigits: mn, maximumFractionDigits: mx });
      formati.set(chiave, f);
    }
    const t = f.format(x);
    return SEMPRE ? t : raggruppa(t);
  }

  const N = { formato, raggruppa, sempre: SEMPRE };
  radice.EUGENIO_NUMERI = N;
  if (typeof module === "object" && module.exports) module.exports = N;
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);
