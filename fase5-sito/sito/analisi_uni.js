/* Analisi avanzate degli edifici (§ 9, analisi 5 e 7–13; fase 10, Fase E): stato del modulo facoltativo.
   Ogni elemento [data-analisi="N"] parte con «analisi non disponibile in questa installazione» (vale anche senza
   JavaScript e sui mirror senza la rotta); se GET /api/analisi/stato dice che l'analisi è disponibile, il testo cambia.
   Il modulo con le metodiche UNI è privato e sta solo sul server: il sito non riceve né mostra i suoi contenuti. */
(function () {
  "use strict";
  const NON = "analisi non disponibile in questa installazione";
  const voci = Array.from(document.querySelectorAll("[data-analisi]"));
  if (!voci.length) return;
  function scrivi(el, ok) {
    const nome = el.getAttribute("data-nome") || ("Analisi " + el.getAttribute("data-analisi"));
    el.textContent = nome + ": " + (ok
      ? "il modulo di calcolo è installato su questo server; la pagina di calcolo non è ancora pubblicata."
      : NON + ".");
    el.classList.toggle("successo", !!ok);
    el.setAttribute("data-disponibile", ok ? "1" : "0");
  }
  voci.forEach(function (el) { scrivi(el, false); });
  fetch("/api/analisi/stato", { headers: { "Accept": "application/json" } })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (d) {
      const ok = {};
      ((d && d.analisi) || []).forEach(function (a) { ok[String(a.id)] = !!a.disponibile; });
      voci.forEach(function (el) { scrivi(el, ok[el.getAttribute("data-analisi")] === true); });
    })
    .catch(function () { /* resta «non disponibile» */ });
})();
