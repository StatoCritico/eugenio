"use strict";
// Divisore tra le due colonne delle pagine dei servizi (28/10/2026): trascinandolo si allarga o si restringe il
// pannello di destra (.pannello) a spese della colonna di sinistra (.mappa-area). Funziona col mouse, col dito
// (pointer events) e con la tastiera (frecce quando ha il fuoco, Maiuscolo per passi grandi, Inizio e Fine per i limiti;
// doppio clic o Canc per tornare alla larghezza predefinita). La larghezza si ricorda per pagina nel browser, come
// frazione della larghezza della pagina. Sotto gli 861 px le colonne diventano una sola e il divisore sparisce (CSS).
// Dopo ogni cambio emette l'evento "eugenio:ridimensiona" su document: mappe e grafici si adattano (gli SVG da soli,
// i grafici registrati con { adatta: true } in grafici.js col loro ResizeObserver).
(function () {
  const main = document.querySelector("main.strumento");
  const pannello = main && main.querySelector(":scope > .pannello");
  const sinistra = main && main.querySelector(":scope > .mappa-area");
  if (!main || !pannello || !sinistra) return;

  const MIN_PANNELLO = 340, MIN_SINISTRA = 300, PASSO = 24, PASSO_GRANDE = 96;
  const una = window.matchMedia("(max-width: 860px)");
  const pagina = (location.pathname.split("/").pop() || "index.html").replace(/\.html?$/, "") || "index";
  const CHIAVE = `larghezza-pannello:${pagina}`;

  function leggi() {
    try { const q = parseFloat(localStorage.getItem(CHIAVE)); return q > 0 && q < 1 ? q : null; } catch (e) { return null; }
  }
  function scrivi(q) {
    try { if (q === null) localStorage.removeItem(CHIAVE); else localStorage.setItem(CHIAVE, q.toFixed(4)); } catch (e) { /* niente memoria */ }
  }

  if (!pannello.id) pannello.id = "pannello";
  const div = document.createElement("div");
  div.className = "divisore";
  div.setAttribute("role", "separator");
  div.setAttribute("aria-orientation", "vertical");
  div.setAttribute("aria-controls", pannello.id);
  div.setAttribute("aria-label", "Larghezza del pannello: trascina, oppure usa le frecce sinistra e destra; doppio clic per tornare alla larghezza iniziale");
  div.title = "Trascina per allargare o restringere il pannello (doppio clic: larghezza iniziale)";
  div.tabIndex = 0;
  div.innerHTML = '<span class="divisore-presa" aria-hidden="true"></span>';
  main.appendChild(div);

  let quota = leggi();       // frazione della larghezza di main occupata dal pannello, null = predefinita
  let avviso = 0;
  function avvisa() {        // al più una volta per fotogramma
    cancelAnimationFrame(avviso);
    avviso = requestAnimationFrame(() => document.dispatchEvent(new CustomEvent("eugenio:ridimensiona", {
      detail: { pannello: pannello.offsetWidth, sinistra: sinistra.offsetWidth },
    })));
  }
  function limiti() {
    const W = main.clientWidth;
    return [MIN_PANNELLO, Math.max(MIN_PANNELLO, W - MIN_SINISTRA)];
  }
  function posiziona() {
    if (una.matches) return;
    div.style.left = `${pannello.offsetLeft}px`;
    const W = main.clientWidth || 1, [lo, hi] = limiti();
    div.setAttribute("aria-valuemin", String(Math.round(lo / W * 100)));
    div.setAttribute("aria-valuemax", String(Math.round(hi / W * 100)));
    div.setAttribute("aria-valuenow", String(Math.round(pannello.offsetWidth / W * 100)));
    div.setAttribute("aria-valuetext", `pannello largo ${Math.round(pannello.offsetWidth)} pixel, ${Math.round(pannello.offsetWidth / W * 100)} per cento`);
  }
  function applica(px) {
    const [lo, hi] = limiti();
    px = Math.round(Math.min(hi, Math.max(lo, px)));
    main.style.setProperty("--larghezza-pannello", `${px}px`);
    main.classList.add("ridimensionato");
    quota = px / (main.clientWidth || 1);
    posiziona();
    avvisa();
  }
  function predefinita() {
    quota = null;
    main.classList.remove("ridimensionato");
    main.style.removeProperty("--larghezza-pannello");
    scrivi(null);
    posiziona();
    avvisa();
  }
  if (quota !== null && !una.matches) applica(quota * main.clientWidth);
  posiziona();

  // la pagina cambia larghezza: stessa frazione, dentro i limiti
  const adegua = () => {
    if (una.matches) return;
    if (quota !== null) {
      const [lo, hi] = limiti(), px = Math.min(hi, Math.max(lo, quota * main.clientWidth));
      main.style.setProperty("--larghezza-pannello", `${Math.round(px)}px`);
      main.classList.add("ridimensionato");
    }
    posiziona();
  };
  if ("ResizeObserver" in window) new ResizeObserver(adegua).observe(main);
  else addEventListener("resize", adegua);
  if (una.addEventListener) una.addEventListener("change", adegua);

  // ------------------------------------------------------------------ mouse e dito
  let presa = null;          // { id, destra }: bordo destro di main al momento della presa
  div.addEventListener("pointerdown", (e) => {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    e.preventDefault();
    presa = { id: e.pointerId, destra: main.getBoundingClientRect().right };
    try { div.setPointerCapture(e.pointerId); } catch (err) { /* già rilasciato */ }
    document.documentElement.classList.add("ridimensiona-colonne");
    div.classList.add("attivo");
  });
  div.addEventListener("pointermove", (e) => {
    if (!presa || e.pointerId !== presa.id) return;
    applica(presa.destra - e.clientX);
  });
  const lascia = (e) => {
    if (!presa || e.pointerId !== presa.id) return;
    presa = null;
    document.documentElement.classList.remove("ridimensiona-colonne");
    div.classList.remove("attivo");
    if (quota !== null) scrivi(quota);
    avvisa();
  };
  div.addEventListener("pointerup", lascia);
  div.addEventListener("pointercancel", lascia);
  div.addEventListener("lostpointercapture", lascia);
  div.addEventListener("dblclick", predefinita);

  // ------------------------------------------------------------------ tastiera
  div.addEventListener("keydown", (e) => {
    const ora = pannello.offsetWidth, passo = e.shiftKey ? PASSO_GRANDE : PASSO, [lo, hi] = limiti();
    switch (e.key) {
      case "ArrowLeft": applica(ora + passo); break;      // il confine va a sinistra: pannello più largo
      case "ArrowRight": applica(ora - passo); break;
      case "Home": applica(lo); break;
      case "End": applica(hi); break;
      case "Delete": case "Backspace": predefinita(); return;
      default: return;
    }
    e.preventDefault();
    scrivi(quota);
  });
})();
