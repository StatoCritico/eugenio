// Pagina iniziale (22/11/2026). Il disegno è la scena a strati di Claude Design (parti/scena_home.html): due scene, una
// per tema (scuro = futuristica, chiaro = tecnica), ognuna con i fondali WebP, l'animazione delle stagioni in CSS, le 16
// parti <g class="parte" data-parte data-gruppo> e i riquadri HUD (fase, informazioni della parte sotto il mouse, legende),
// tutto in CSS. Qui:
//  - la scena larga 1200 × 875 si riduce alla larghezza del contenitore (--k);
//  - il clic (o Invio, o il tocco) su una parte apre la scheda del suo gruppo, con le pagine della parte in evidenza;
//  - il clic su una voce apre la pagina con il menu del gruppo già fissato in orizzontale (localStorage «menu-fissato»,
//    come il clic sul titolo del gruppo nel menu, aspetto.js).
// Senza JavaScript le schede sono tutte visibili sotto il disegno.
(function () {
  "use strict";
  const contenitore = document.getElementById("scena-contenitore");
  if (!contenitore) return;
  const schede = [...document.querySelectorAll(".home-scheda[data-gruppo]")];
  const intro = document.getElementById("scheda-intro");
  const scelte = document.getElementById("home-scelte");
  const parti = [...contenitore.querySelectorAll(".parte")];
  const fermo = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let DATI = {};
  try { DATI = JSON.parse(document.getElementById("parti-home").textContent); } catch (e) { /* niente */ }

  // ------------------------------------------------------------------ scala della scena
  function scala() {
    contenitore.style.setProperty("--k", String(contenitore.clientWidth / 1200));
  }
  scala();
  if (window.ResizeObserver) new ResizeObserver(scala).observe(contenitore);
  else window.addEventListener("resize", scala);

  // ------------------------------------------------------------------ schede: una alla volta, con la chiusura
  schede.forEach((s) => {
    s.hidden = true;
    const x = document.createElement("button");
    x.type = "button"; x.className = "scheda-chiudi"; x.textContent = "×";
    x.setAttribute("aria-label", "Chiudi la scheda"); x.title = "Torna all'inizio";
    x.addEventListener("click", () => scegli(null, true));
    s.prepend(x);
    const dal = document.createElement("p");
    dal.className = "scheda-parte"; dal.hidden = true;
    s.querySelector("h2").before(dal);
    const b = document.createElement("button");
    b.type = "button"; b.textContent = s.querySelector("h2").textContent; b.dataset.gruppo = s.dataset.gruppo;
    b.setAttribute("aria-pressed", "false");
    b.addEventListener("click", () => scegli(s.dataset.gruppo, true));
    scelte.appendChild(b);
  });

  function scegli(g, fuoco, chiave) {
    schede.forEach((s) => { s.hidden = s.dataset.gruppo !== g; });
    intro.hidden = !!g;
    const d = chiave && DATI[chiave];
    const pagine = d ? d.voci.map((v) => v.pagina) : [];
    document.querySelectorAll(".home-scheda li[data-pagina]").forEach((li) => li.classList.toggle("evidenza", pagine.includes(li.dataset.pagina)));
    const riga = g && document.querySelector(`#scheda-${g} .scheda-parte`);
    if (riga) {
      riga.hidden = !d;
      if (d) riga.textContent = `Dal disegno: ${d.titolo}` + (d.prossimamente ? " – prossimamente" : "");
    }
    parti.forEach((p) => p.setAttribute("aria-pressed", String(!!chiave && p.dataset.parte === chiave)));
    scelte.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.gruppo === g)));
    const s = g ? document.getElementById(`scheda-${g}`) : intro;
    if (fuoco && s) {
      const h = s.querySelector("h2");
      h.tabIndex = -1;
      h.focus({ preventScroll: true });
      const r = s.getBoundingClientRect();
      if (r.top < 0 || r.top > window.innerHeight * 0.75) s.scrollIntoView({ behavior: fermo ? "auto" : "smooth", block: "start" });
    }
  }

  // ------------------------------------------------------------------ parti (le informazioni al passaggio sono in CSS)
  parti.forEach((p) => {
    const g = p.dataset.gruppo, k = p.dataset.parte, d = DATI[k];
    if (d) p.setAttribute("aria-label", `${d.titolo} (${d.titolo_gruppo})${d.prossimamente ? ", prossimamente" : ""}`);
    p.setAttribute("aria-pressed", "false");
    p.addEventListener("click", () => scegli(g, true, k));
    p.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); scegli(g, true, k); }
    });
  });

  // ------------------------------------------------------------------ voce scelta: la pagina si apre con il menu fissato
  document.querySelectorAll(".home-scheda a[data-gruppo]").forEach((a) => {
    a.addEventListener("click", () => {
      try { localStorage.setItem("menu-fissato", a.dataset.gruppo); } catch (e) { /* niente */ }
    });
  });

  scegli(null, false);
})();
