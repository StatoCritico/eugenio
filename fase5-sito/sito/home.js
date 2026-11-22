// Pagina iniziale (22/11/2026, richiesta di Paolo): disegno di un edificio con le reti, il territorio e il meteo,
// animato per stagione (estate: sole e pioggia; inverno: sole e neve). Passando il mouse su una parte compare il
// riquadretto con il gruppo di pagine (titolo, descrizione, voci); il clic (o Invio, o il tocco) apre la scheda del
// gruppo accanto al disegno; il clic su una voce apre la pagina con il menu del gruppo già fissato in orizzontale
// (localStorage «menu-fissato», lo stesso del clic sul titolo del gruppo nel menu, aspetto.js).
// Senza JavaScript le schede sono tutte visibili sotto il disegno.
(function () {
  "use strict";
  const scena = document.getElementById("scena");
  const svg = scena && scena.querySelector("svg");
  if (!scena || !svg) return;
  const tip = document.getElementById("scena-tip");
  const schede = [...document.querySelectorAll(".home-scheda[data-gruppo]")];
  const intro = document.getElementById("scheda-intro");
  const scelte = document.getElementById("home-scelte");
  const parti = [...svg.querySelectorAll(".parte")];
  let DATI = {};
  try { DATI = JSON.parse(document.getElementById("parti-home").textContent); } catch (e) { /* niente */ }
  const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const scheda = (g) => schede.find((s) => s.dataset.gruppo === g);
  const fermo = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let scelta = null;

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
    b.addEventListener("mouseenter", () => evidenzia("gruppo:" + s.dataset.gruppo));
    b.addEventListener("mouseleave", () => evidenzia(null));
    scelte.appendChild(b);
  });

  // g: chiave di una parte (data-parte) o, dai pulsanti dei gruppi, «gruppo:<id>» (si accendono tutte le sue parti)
  let parteScelta = null;
  function accesa(p, k) {
    if (!k) return false;
    return k.startsWith("gruppo:") ? p.dataset.gruppo === k.slice(7) : p.dataset.parte === k;
  }
  function evidenzia(k) {
    parti.forEach((p) => p.classList.toggle("su", accesa(p, k) || accesa(p, parteScelta)));
    scena.classList.toggle("indica", !!(k || parteScelta));
  }

  function scegli(g, fuoco, chiave) {
    scelta = g;
    parteScelta = chiave || (g ? "gruppo:" + g : null);
    schede.forEach((s) => { s.hidden = s.dataset.gruppo !== g; });
    intro.hidden = !!g;
    // pagine della parte scelta in evidenza nella scheda
    const pagine = chiave && DATI[chiave] ? DATI[chiave].voci.map((v) => v.pagina) : [];
    document.querySelectorAll(".home-scheda li[data-pagina]").forEach((li) => li.classList.toggle("evidenza", pagine.includes(li.dataset.pagina)));
    const titoloParte = g && document.querySelector(`#scheda-${g} .scheda-parte`);
    if (titoloParte) {
      titoloParte.hidden = !(chiave && DATI[chiave]);
      if (chiave && DATI[chiave]) titoloParte.textContent = `Dal disegno: ${DATI[chiave].titolo}` + (DATI[chiave].prossimamente ? " – prossimamente" : "");
    }
    parti.forEach((p) => p.setAttribute("aria-pressed", String(accesa(p, parteScelta))));
    scelte.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.gruppo === g)));
    evidenzia(null);
    const s = g ? scheda(g) : intro;
    if (fuoco && s) {
      const h = s.querySelector("h2");
      h.tabIndex = -1;
      h.focus({ preventScroll: true });
      const r = s.getBoundingClientRect();
      if (r.top < 0 || r.top > window.innerHeight * 0.6) s.scrollIntoView({ behavior: fermo ? "auto" : "smooth", block: "start" });
    }
  }

  // ------------------------------------------------------------------ parti del disegno
  function testoTip(k) {
    const d = DATI[k];
    if (!d) return "";
    const voci = d.voci.map((v) => `<li${v.attiva ? "" : ' class="in-arrivo"'}>${esc(v.nome)}${v.attiva ? "" : " (prossimamente)"}</li>`);
    return `<span class="tip-gruppo">${esc(d.titolo_gruppo)}</span><strong>${esc(d.titolo)}</strong>` +
      (d.prossimamente ? '<span class="tip-poi">Prossimamente</span>' : "") +
      `<p>${esc(d.descrizione)}</p>` + (voci.length ? `<ul>${voci.join("")}</ul>` : "") +
      `<p class="tip-clic">${d.prossimamente ? "Le pagine sono in preparazione: clicca per vedere il gruppo" : "Clicca per aprire le pagine"}</p>`;
  }

  function mostraTip(g, e) {
    if (!tip) return;
    tip.innerHTML = testoTip(g);
    tip.hidden = false;
    const box = scena.getBoundingClientRect();
    let x = e.clientX - box.left + 16, y = e.clientY - box.top + 16;
    const w = tip.offsetWidth, h = tip.offsetHeight;
    if (x + w > box.width - 8) x = Math.max(8, e.clientX - box.left - w - 16);
    if (y + h > box.height - 8) y = Math.max(8, box.height - h - 8);
    tip.style.left = `${x}px`; tip.style.top = `${y}px`;
  }

  parti.forEach((p) => {
    const g = p.dataset.gruppo, k = p.dataset.parte, d = DATI[k];
    if (d) p.setAttribute("aria-label", `${d.titolo} (${d.titolo_gruppo})${d.prossimamente ? ", prossimamente" : ""}`);
    if (d && d.prossimamente) p.classList.add("poi");
    p.setAttribute("aria-pressed", "false");
    p.addEventListener("pointermove", (e) => {
      if (e.pointerType !== "mouse") return;
      evidenzia(k);
      mostraTip(k, e);
    });
    p.addEventListener("pointerleave", () => { evidenzia(null); if (tip) tip.hidden = true; });
    p.addEventListener("click", () => { if (tip) tip.hidden = true; scegli(g, true, k); });
    p.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); scegli(g, true, k); }
    });
    p.addEventListener("focus", () => evidenzia(k));
    p.addEventListener("blur", () => evidenzia(null));
  });

  // ------------------------------------------------------------------ voce scelta: la pagina si apre con il menu fissato
  document.querySelectorAll(".home-scheda a[data-gruppo]").forEach((a) => {
    a.addEventListener("click", () => {
      try { localStorage.setItem("menu-fissato", a.dataset.gruppo); } catch (e) { /* niente */ }
    });
  });

  // ------------------------------------------------------------------ stagioni
  const FASI = [
    { stagione: "estate", meteo: "sole", nome: "Estate, sole" },
    { stagione: "estate", meteo: "pioggia", nome: "Estate, pioggia" },
    { stagione: "inverno", meteo: "sole", nome: "Inverno, sole" },
    { stagione: "inverno", meteo: "neve", nome: "Inverno, neve" },
  ];
  const barra = document.getElementById("scena-barra"), nomeFase = document.getElementById("scena-stagione");
  const pausa = document.getElementById("scena-pausa"), aiuto = document.getElementById("scena-aiuto");
  let fase = 0, giro = null;
  function mostraFase(i) {
    fase = (i + FASI.length) % FASI.length;
    const f = FASI[fase];
    scena.dataset.stagione = f.stagione;
    scena.dataset.meteo = f.meteo;
    nomeFase.textContent = f.nome;
  }
  function avvia() {
    if (giro) return;
    giro = setInterval(() => mostraFase(fase + 1), 4500);
    pausa.textContent = "❚❚"; pausa.setAttribute("aria-label", "Ferma l'animazione"); pausa.title = "Ferma l'animazione";
  }
  function ferma() {
    clearInterval(giro); giro = null;
    pausa.textContent = "▶"; pausa.setAttribute("aria-label", "Riprendi l'animazione"); pausa.title = "Riprendi l'animazione";
  }
  pausa.addEventListener("click", () => { if (fermo) mostraFase(fase + 1); else if (giro) ferma(); else avvia(); });
  barra.hidden = false;
  if (aiuto) aiuto.hidden = false;
  mostraFase(0);
  if (fermo) {   // niente animazione da sola: il pulsante passa alla fase successiva
    pausa.textContent = "›"; pausa.setAttribute("aria-label", "Stagione successiva"); pausa.title = "Stagione successiva";
  } else {
    avvia();
    document.addEventListener("visibilitychange", () => { if (document.hidden) { clearInterval(giro); giro = null; } else if (pausa.textContent === "❚❚") avvia(); });
  }
  scegli(null, false);
})();
