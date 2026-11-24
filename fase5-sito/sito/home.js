// Pagina iniziale (23/11/2026). Il disegno è fermo (parti/scena_home.html: un fondale WebP per tema) e gli unici elementi
// attivi sono i bersagli (button.sh-punto data-parte data-gruppo). Qui:
//  - la scena si adatta alla finestra: larga quanto la pagina, ma non più alta dello spazio che resta sotto titolo e testo
//    (23/11/2026: si vede tutta senza scorrere); rapporto letto dall'aspect-ratio del CSS (16:9);
//  - i titoli dei bersagli compaiono a turno, uno alla volta (1 s acceso, 0,5 s spento), e si fermano quando si usa la
//    scena; il titolo sta a sinistra del bersaglio quando questo è nella parte destra del disegno;
//  - sostando su un bersaglio (o con il fuoco da tastiera) compare la descrizione breve;
//  - il clic (Invio, tocco) apre sull'immagine la scheda flottante della parte con le sue pagine;
//  - il clic su una pagina la apre con il menu del suo gruppo già aperto in orizzontale (localStorage «menu-fissato»,
//    letto da aspetto.js come il clic sul titolo del gruppo nel menu).
// Sotto il disegno restano le schede dei gruppi (con i pulsanti «Da dove cominciare»); senza JavaScript sono tutte visibili.
(function () {
  "use strict";
  const scena = document.getElementById("scena-home");
  if (!scena) return;
  const quadro = scena.querySelector(".sh-quadro");
  const punti = [...scena.querySelectorAll(".sh-punto")];
  const descr = document.getElementById("sh-descr");
  const scheda = document.getElementById("sh-scheda");
  const schede = [...document.querySelectorAll(".home-scheda[data-gruppo]")];
  const intro = document.getElementById("scheda-intro");
  const scelte = document.getElementById("home-scelte");
  const fermo = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let DATI = {};
  try { DATI = JSON.parse(document.getElementById("parti-home").textContent); } catch (e) { /* niente */ }

  // ------------------------------------------------------------------ dimensione sulla finestra
  function misura() {
    const pagina = document.documentElement.clientWidth;
    // spazio dal bordo alto del disegno (sotto testata, titolo e testo, a pagina non scorsa) al fondo della finestra
    const inizio = scena.getBoundingClientRect().top + window.scrollY;
    const spazio = Math.max(260, window.innerHeight - inizio - 12);
    const w = Math.round(Math.min(pagina, spazio * rapporto()));
    scena.style.setProperty("--sh-w", w + "px");
    // posizione senza lo spostamento attuale (vale anche con bordi o margini del genitore: 23/11/2026, 1 px di troppo sul
    // telefono con il bordo del contenitore); per difetto, così il bordo destro non supera mai la pagina
    const base = scena.getBoundingClientRect().left - (parseFloat(getComputedStyle(scena).left) || 0);
    scena.style.setProperty("--sh-x", Math.floor((pagina - w) / 2 - base) + "px");
  }
  function rapporto() {                       // larghezza / altezza del quadro, dal CSS (aspect-ratio: 16 / 9 o 1200 / 875)
    const a = getComputedStyle(quadro).aspectRatio.split("/").map(parseFloat);
    return a.length === 2 && a[0] > 0 && a[1] > 0 ? a[0] / a[1] : (a[0] > 0 ? a[0] : 1200 / 875);
  }
  function lati() {                           // titolo a sinistra dei bersagli nella parte destra del disegno
    const q = quadro.getBoundingClientRect();
    if (!q.width) return;
    const fuori = (p) => {                    // quanti px del titolo escono dal disegno
      const t = p.querySelector(".sh-titolo");
      if (!t) return 0;
      const r = t.getBoundingClientRect();
      return Math.max(0, q.left - r.left) + Math.max(0, r.right - q.right);
    };
    punti.forEach((p) => {
      const t = p.querySelector(".sh-titolo");
      if (t) t.style.removeProperty("--dx");
      const r = p.getBoundingClientRect();
      p.classList.toggle("sh-sx", (r.left + r.width / 2 - q.left) / q.width > 0.6);
      const prima = fuori(p);                 // se non ci sta da quella parte, prova l'altra (telefoni: titoli lunghi)
      if (prima > 0) {
        p.classList.toggle("sh-sx");
        if (fuori(p) >= prima) p.classList.toggle("sh-sx");
      }
      if (t && fuori(p) > 0) {                // più lungo dello spazio da entrambe le parti: lo fa scorrere dentro il bordo
        const b = t.getBoundingClientRect();
        const dx = b.left < q.left ? q.left - b.left + 4 : q.right - b.right - 4;
        t.style.setProperty("--dx", Math.round(dx) + "px");
      }
    });
  }
  function adatta() { misura(); lati(); }
  misura();
  lati();
  window.addEventListener("resize", adatta);
  if (window.ResizeObserver) new ResizeObserver(adatta).observe(document.documentElement);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(adatta);   // il testo sopra cambia altezza coi font

  // ------------------------------------------------------------------ titoli a turno
  let turno = 0, acceso = false, fermi = false;
  const ACCESO = 1000, SPENTO = 500;          // ms (23/11/2026, Paolo: 0,5 s tra un titolo e l'altro)
  function giro() {
    if (!fermi && !document.hidden) {
      punti.forEach((p) => p.classList.remove("sh-acceso"));
      if (!acceso) punti[turno].classList.add("sh-acceso");
      else turno = (turno + 1) % punti.length;
      acceso = !acceso;
    }
    setTimeout(giro, acceso ? ACCESO : SPENTO);
  }
  function ferma(v) {
    fermi = v;
    if (v) punti.forEach((p) => p.classList.remove("sh-acceso"));
  }
  setTimeout(giro, SPENTO);

  // ------------------------------------------------------------------ posizione di un riquadro accanto al bersaglio
  function accosta(box, p) {
    const q = quadro.getBoundingClientRect(), r = p.getBoundingClientRect();
    const bw = box.offsetWidth, bh = box.offsetHeight, m = 10;
    const cx = r.left + r.width / 2 - q.left, cy = r.top + r.height / 2 - q.top;
    let x = cx + r.width / 2 + m;
    if (x + bw > q.width - m) x = cx - r.width / 2 - m - bw;
    x = Math.max(m, Math.min(x, q.width - bw - m));
    let y = cy - bh / 2;
    y = Math.max(m, Math.min(y, q.height - bh - m));
    box.style.left = x + "px";
    box.style.top = y + "px";
  }

  function esc(t) {
    return String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

  // ------------------------------------------------------------------ descrizione breve
  let attesa = null;
  function mostraDescr(p) {
    // (24/11/2026) bersaglio-collegamento (a.sh-punto, file per gli LLM): titolo e descrizione dagli attributi data-
    const d = p.tagName === "A" ? { titolo: p.dataset.titolo || "", descrizione: p.dataset.descrizione || "", link: true } : DATI[p.dataset.parte];
    if (!d || !scheda.hidden) return;
    descr.innerHTML = `<strong>${esc(d.titolo)}</strong>${esc(d.descrizione)}` +
      `<span class="sh-nota">${d.link ? "Clic per aprire il file" : d.prossimamente ? "Prossimamente" : "Clic per le pagine"}</span>`;
    descr.hidden = false;
    accosta(descr, p);
  }
  function nascondiDescr() {
    clearTimeout(attesa);
    descr.hidden = true;
  }

  // ------------------------------------------------------------------ scheda flottante
  let aperto = null;
  function gruppoPagina(pagina, riserva) {
    const a = document.querySelector(`.home-scheda a[href="${CSS.escape(pagina)}"]`);
    return (a && a.dataset.gruppo) || riserva;
  }
  function apri(p) {
    const k = p.dataset.parte, d = DATI[k];
    if (!d) return;
    nascondiDescr();
    if (aperto) aperto.setAttribute("aria-expanded", "false");
    aperto = p;
    p.setAttribute("aria-expanded", "true");
    const voci = d.voci.length ? d.voci.map((v) => v.attiva
      ? `<li><a href="${esc(v.pagina)}" data-gruppo="${esc(gruppoPagina(v.pagina, d.gruppo))}">${esc(v.nome)}` +
        (v.stato ? `<span class="sh-stato">${esc(v.stato)}</span>` : "") + `</a></li>`
      : `<li><span class="sh-spenta" aria-disabled="true">${esc(v.nome)}<span class="sh-stato">${esc(v.stato)}</span></span></li>`).join("")
      : `<li class="sh-vuota">Pagine in preparazione.</li>`;
    scheda.innerHTML = `<button type="button" class="sh-chiudi" aria-label="Chiudi">×</button>` +
      `<p class="sh-gruppo">${esc(d.titolo_gruppo)}</p><h2 id="sh-scheda-titolo">${esc(d.titolo)}</h2>` +
      `<p>${esc(d.descrizione)}</p><ul>${voci}</ul>` +
      (document.getElementById(`scheda-${d.gruppo}`) ? `<a class="sh-tutte" href="#scheda-${esc(d.gruppo)}" data-scheda="${esc(d.gruppo)}">Tutte le pagine di ${esc(d.titolo_gruppo)}</a>` : "");
    scheda.hidden = false;
    accosta(scheda, p);
    ferma(true);
    scheda.querySelector("a[href]:not(.sh-tutte), .sh-chiudi").focus({ preventScroll: true });
  }
  function chiudi(torna) {
    if (scheda.hidden) return;
    scheda.hidden = true;
    const p = aperto;
    if (p) p.setAttribute("aria-expanded", "false");
    aperto = null;
    ferma(false);
    if (torna && p) p.focus({ preventScroll: true });
  }

  scheda.addEventListener("click", (e) => {
    if (e.target.closest(".sh-chiudi")) { chiudi(true); return; }
    const tutte = e.target.closest("a[data-scheda]");
    if (tutte) { e.preventDefault(); chiudi(false); scegli(tutte.dataset.scheda, true); return; }
    const a = e.target.closest("a[data-gruppo]");
    if (a) { try { localStorage.setItem("menu-fissato", a.dataset.gruppo); } catch (err) { /* niente */ } }
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") { nascondiDescr(); chiudi(true); } });
  document.addEventListener("pointerdown", (e) => {
    if (!scheda.hidden && !scheda.contains(e.target) && !e.target.closest(".sh-punto")) chiudi(false);
  });

  punti.forEach((p) => {
    if (p.tagName === "A") {                  // collegamento diretto: descrizione al passaggio, nessuna scheda
      p.addEventListener("pointerenter", (e) => { if (e.pointerType === "touch") return; ferma(true); clearTimeout(attesa); attesa = setTimeout(() => mostraDescr(p), fermo ? 0 : 350); });
      p.addEventListener("pointerleave", () => { nascondiDescr(); if (scheda.hidden) ferma(false); });
      p.addEventListener("focus", () => { if (p.matches(":focus-visible")) { ferma(true); mostraDescr(p); } });
      p.addEventListener("blur", () => { nascondiDescr(); if (scheda.hidden) ferma(false); });
      return;
    }
    p.setAttribute("aria-expanded", "false");
    p.setAttribute("aria-haspopup", "dialog");
    p.setAttribute("aria-controls", "sh-scheda");
    p.addEventListener("pointerenter", (e) => {
      if (e.pointerType === "touch") return;
      ferma(true);
      clearTimeout(attesa);
      attesa = setTimeout(() => mostraDescr(p), fermo ? 0 : 350);
    });
    p.addEventListener("pointerleave", () => { nascondiDescr(); if (scheda.hidden) ferma(false); });
    p.addEventListener("focus", () => { if (p.matches(":focus-visible")) { ferma(true); mostraDescr(p); } });
    p.addEventListener("blur", () => { nascondiDescr(); if (scheda.hidden) ferma(false); });
    p.addEventListener("click", () => { if (aperto === p) chiudi(false); else apri(p); });
  });
  window.addEventListener("resize", () => { if (aperto) accosta(scheda, aperto); nascondiDescr(); });

  // ------------------------------------------------------------------ schede dei gruppi sotto il disegno
  if (!intro || !scelte) return;
  schede.forEach((s) => {
    s.hidden = true;
    const x = document.createElement("button");
    x.type = "button"; x.className = "scheda-chiudi"; x.textContent = "×";
    x.setAttribute("aria-label", "Chiudi la scheda"); x.title = "Torna all'inizio";
    x.addEventListener("click", () => scegli(null, true));
    s.prepend(x);
    const b = document.createElement("button");
    b.type = "button"; b.textContent = s.querySelector("h2").textContent; b.dataset.gruppo = s.dataset.gruppo;
    b.setAttribute("aria-pressed", "false");
    b.addEventListener("click", () => scegli(s.dataset.gruppo, true));
    scelte.appendChild(b);
  });
  function scegli(g, fuoco) {
    schede.forEach((s) => { s.hidden = s.dataset.gruppo !== g; });
    intro.hidden = !!g;
    scelte.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.gruppo === g)));
    const s = g ? document.getElementById(`scheda-${g}`) : intro;
    if (fuoco && s) {
      const h = s.querySelector("h2");
      h.tabIndex = -1;
      h.focus({ preventScroll: true });
      s.scrollIntoView({ behavior: fermo ? "auto" : "smooth", block: "start" });
    }
  }
  document.querySelectorAll(".home-scheda a[data-gruppo]").forEach((a) => {
    a.addEventListener("click", () => {
      try { localStorage.setItem("menu-fissato", a.dataset.gruppo); } catch (e) { /* niente */ }
    });
  });
  scegli(null, false);
})();
