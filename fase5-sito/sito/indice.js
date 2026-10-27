"use strict";
// Indice laterale delle pagine di testo (Come funziona, F.A.Q., Sitografia): elenca i raggruppamenti della pagina in
// un menu a sinistra che resta fermo mentre il testo scorre. Un clic porta alla sezione (e la apre se è chiusa);
// la voce della sezione visibile è evidenziata. Su schermi stretti l'indice diventa un riquadro richiudibile in alto.
(function () {
  const main = document.querySelector("main.articolo");
  if (!main) return;
  const slug = (t) => t.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60) || "sezione";

  // sezioni: gruppi richiudibili (F.A.Q., Sitografia) oppure titoli h2 (Come funziona)
  // pagine con titoli di gruppo (F.A.Q.): l'indice mostra solo i gruppi, le domande restano nel testo
  let voci = main.querySelector(":scope > h2") ? [] : [...main.querySelectorAll(":scope > details")].map((d) => ({
    el: d, testo: (d.querySelector("summary h2") || d.querySelector("summary")).textContent.trim(), apri: () => (d.open = true),
  }));
  // capitoli h2 con i loro paragrafi h3 (Come funziona)
  // titoli h2 con, sotto, i paragrafi h3 (Come funziona) o i gruppi richiudibili (Sitografia)
  if (!voci.length) voci = [...main.querySelectorAll(":scope > h2, :scope > h3, :scope > details.gruppo")].map((e) =>
    e.tagName === "DETAILS"
      ? { el: e, testo: (e.querySelector("summary h3, summary h2") || e.querySelector("summary")).textContent.trim(),
          sotto: true, apri: () => (e.open = true) }
      : { el: e, testo: e.textContent.trim(), sotto: e.tagName === "H3", apri: () => {} });
  if (voci.length < 3) return;
  const usati = new Set(document.querySelectorAll("[id]").length ? [...document.querySelectorAll("[id]")].map((x) => x.id) : []);
  voci.forEach((v) => {
    if (!v.el.id) {
      let id = slug(v.testo), n = 2;
      while (usati.has(id)) id = `${slug(v.testo)}-${n++}`;
      v.el.id = id; usati.add(id);
    }
  });

  // impaginazione: indice a sinistra, testo a destra
  const corpo = document.createElement("div");
  corpo.className = "articolo-corpo";
  while (main.firstChild) corpo.appendChild(main.firstChild);
  const aside = document.createElement("aside");
  aside.className = "indice-laterale";
  aside.setAttribute("aria-label", "Indice della pagina");
  const box = document.createElement("details");
  box.open = true;
  box.innerHTML = `<summary>Indice</summary><nav><ol></ol></nav>`;
  aside.appendChild(box);
  const ol = box.querySelector("ol");
  const link = new Map();
  voci.forEach((v) => {
    const li = document.createElement("li");
    if (v.sotto) li.className = "sotto";
    const a = document.createElement("a");
    a.href = `#${v.el.id}`;
    a.textContent = v.testo;
    a.addEventListener("click", (e) => {
      e.preventDefault();
      v.apri();
      v.el.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
      history.replaceState(null, "", `#${v.el.id}`);
      if (matchMedia("(max-width: 860px)").matches) box.open = false;
      segna(v.el.id);
      fermo = Date.now() + 1200; // durante lo scorrimento resta evidenziata la voce scelta
    });
    li.appendChild(a);
    ol.appendChild(li);
    link.set(v.el.id, a);
  });
  main.classList.add("con-indice");
  main.append(aside, corpo);
  if (matchMedia("(max-width: 860px)").matches) box.open = false;

  function segna(id) {
    link.forEach((a, k) => {
      const attiva = k === id;
      a.classList.toggle("attiva", attiva);
      if (attiva) a.setAttribute("aria-current", "location"); else a.removeAttribute("aria-current");
    });
  }
  // la sezione "attiva" è l'ultima il cui inizio ha superato il primo quarto della finestra
  let fermo = 0;
  function aggiorna() {
    if (Date.now() < fermo) return;
    const soglia = innerHeight * 0.25;
    let scelto = voci[0].el.id;
    for (const v of voci) if (v.el.getBoundingClientRect().top <= soglia) scelto = v.el.id;
    segna(scelto);
  }
  addEventListener("scroll", aggiorna, { passive: true });
  addEventListener("resize", aggiorna);
  // arrivando con un'ancora (#sezione) la si apre
  if (location.hash) {
    const v = voci.find((x) => `#${x.el.id}` === decodeURIComponent(location.hash));
    if (v) { v.apri(); setTimeout(() => v.el.scrollIntoView({ block: "start" }), 0); }
    else {   // collegamento a una singola domanda dentro un gruppo
      const d = document.getElementById(decodeURIComponent(location.hash.slice(1)));
      if (d && d.tagName === "DETAILS") { d.open = true; setTimeout(() => d.scrollIntoView({ block: "start" }), 0); }
    }
  }
  // su schermo largo l'indice è sempre aperto
  addEventListener("resize", () => { if (!matchMedia("(max-width: 860px)").matches) box.open = true; });
  aggiorna();
})();
