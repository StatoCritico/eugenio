"use strict";
// Mappe del sito, parte comune alle pagine delle funzioni (previsione, patrimonio, Legge 10, dati, indicatori):
//  - la piccola mappa d'Italia accanto al titolo: regioni colorate, nome al passaggio del mouse, zoom con la
//    rotella (+, −, doppio clic per tornare), clic = regione della mappa grande;
//  - la regione scelta (?regione=RR nell'indirizzo, ricordata nel browser, predefinita l'Emilia-Romagna);
//  - gli strumenti per la mappa grande: Italia intera sotto la regione scelta, confini delle regioni sopra a
//    tutto, zoom e trascinamento;
//  - i riquadretti col nome di regioni e comuni al passaggio del mouse o al tocco (suggerimenti), per tutte le mappe
//    grandi, anche quella tridimensionale del patrimonio (mappa3d.js).
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const PREDEFINITA = "08";
  const CHIAVE = "eugenio-regione";
  const VALIDE = /^(0[1-9]|1\d|20)$/;
  // un colore per regione: variabili --reg-01 … --reg-20 di stile.css, diverse per tema scuro e chiaro e uguali per
  // tutti i vestiti (si cambiano solo lì). Si leggono quando la mappa viene disegnata.
  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const colore = (cod) => css(`--reg-${cod}`) || css("--linea") || "#999";
  // fondo dei comuni della regione scelta nella mappa grande: nel tema scuro il colore della regione, un po'
  // schiarito, così la regione scelta è la più luminosa e i confini comunali (tratti scuri) si vedono bene;
  // nel tema chiaro il grigio chiaro di sempre
  const scuro = () => document.documentElement.dataset.theme !== "light";
  function schiarisci(hex, t) {
    const m = /^#?([0-9a-f]{6})$/i.exec(hex || "");
    if (!m) return hex;
    const n = parseInt(m[1], 16), c = [n >> 16, (n >> 8) & 255, n & 255].map((x) => Math.round(x + (255 - x) * t));
    return "#" + c.map((x) => x.toString(16).padStart(2, "0")).join("");
  }
  const fondoComuni = (cod) => (scuro() ? schiarisci(colore(cod), 0.18) : css("--linea"));
  const pulisci = (v) => (v || "").replace(/\D/g, "").padStart(2, "0").slice(0, 2);
  function leggiRicordata() { try { return localStorage.getItem(CHIAVE); } catch { return null; } }
  function ricorda(cod) { try { localStorage.setItem(CHIAVE, cod); } catch { /* navigazione privata */ } }

  // Vista d'Italia all'apertura della mappa grande (le regioni si scelgono con un clic):
  //  - sempre con ?vista=italia nell'indirizzo;
  //  - anche alla prima visita (nessuna regione nell'indirizzo né ricordata) se ITALIA_ALLA_PRIMA_VISITA è true.
  // Oggi è false: alla prima visita si apre l'Emilia-Romagna, l'unica con il meteo completo.
  const ITALIA_ALLA_PRIMA_VISITA = false;
  const parametri = new URLSearchParams(location.search);
  const primaVisita = !parametri.get("regione") && !leggiRicordata();
  const apriSuItalia = parametri.get("vista") === "italia" || (ITALIA_ALLA_PRIMA_VISITA && primaVisita);
  let regione = pulisci(parametri.get("regione") || leggiRicordata() || PREDEFINITA);
  if (!VALIDE.test(regione)) regione = PREDEFINITA;
  ricorda(regione);

  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      // colori "var(--…)": nello stile, così seguono da soli il cambio di tema o di vestito
      if ((k === "fill" || k === "stroke") && typeof v === "string" && v.startsWith("var(")) e.style.setProperty(k, v);
      else e.setAttribute(k, v);
    }
    if (parent) parent.appendChild(e);
    return e;
  }

  let promessaItalia = null;
  function italia() {
    if (!promessaItalia) promessaItalia = fetch("dati/mappa/italia.json").then((r) => {
      if (!r.ok) throw new Error(`mappa d'Italia non disponibile (${r.status})`);
      return r.json();
    }).then((m) => ({ ...m, viewBox: m.viewBox.map(Number), regioni: m.regioni.filter((x) => VALIDE.test(x.cod)) }));
    return promessaItalia;
  }

  // zoom con la rotella attorno al puntatore, trascinamento, doppio clic per tornare a `ritorno()`.
  // Un trascinamento non vale come clic (il clic catturato prima che arrivi ai comuni o alle regioni).
  function zoomabile(svg, { limiti, ritorno, minimo = 1 / 40, suCambio } = {}) {
    let inizio = null, trascinato = false;
    const vbOra = () => { const b = svg.viewBox.baseVal; return [b.x, b.y, b.width, b.height]; };
    function imposta([x, y, w, h]) {
      const L = limiti();
      const ww = Math.max(L[2] * minimo, Math.min(w, L[2] * 1.15)), hh = h * ww / w;
      // il centro resta dentro i limiti (l'Italia)
      const cx = Math.min(L[0] + L[2], Math.max(L[0], x + w / 2)), cy = Math.min(L[1] + L[3], Math.max(L[1], y + h / 2));
      svg.setAttribute("viewBox", `${cx - ww / 2} ${cy - hh / 2} ${ww} ${hh}`);
      if (suCambio) suCambio(ww / L[2]);
    }
    function zoom(f, cx, cy) {
      if (f === 0) return imposta(ritorno());
      const [x, y, w, h] = vbOra();
      if (cx === undefined) { cx = x + w / 2; cy = y + h / 2; }
      imposta([cx - (cx - x) / f, cy - (cy - y) / f, w / f, h / f]);
    }
    function puntoSvg(e) {
      const p = svg.createSVGPoint(); p.x = e.clientX; p.y = e.clientY;
      const q = p.matrixTransform(svg.getScreenCTM().inverse());
      return [q.x, q.y];
    }
    svg.addEventListener("wheel", (e) => { e.preventDefault(); const [cx, cy] = puntoSvg(e); zoom(e.deltaY < 0 ? 1.25 : 0.8, cx, cy); }, { passive: false });
    svg.addEventListener("dblclick", (e) => { e.preventDefault(); zoom(0); });
    svg.addEventListener("pointerdown", (e) => { if (e.button === 0) { inizio = { x: e.clientX, y: e.clientY, vb: vbOra() }; trascinato = false; } });
    svg.addEventListener("pointermove", (e) => {
      if (!inizio) return;
      const dx = e.clientX - inizio.x, dy = e.clientY - inizio.y;
      if (!trascinato && Math.hypot(dx, dy) < 5) return;
      trascinato = true;
      svg.classList.add("trascina");
      const s = 1 / svg.getScreenCTM().a;
      imposta([inizio.vb[0] - dx * s, inizio.vb[1] - dy * s, inizio.vb[2], inizio.vb[3]]);
    });
    window.addEventListener("pointerup", () => { inizio = null; svg.classList.remove("trascina"); });
    svg.addEventListener("click", (e) => { if (trascinato) { e.stopPropagation(); e.preventDefault(); trascinato = false; } }, true);
    return { imposta, zoom };
  }

  // ------------------------------------------------------------------ riquadretti della mappa grande (29/10/2026)
  // Un solo meccanismo per tutte le mappe grandi: passando col mouse sopra una regione non selezionata compare il suo
  // nome, sopra un comune della regione scelta il nome del comune con la sigla della provincia (e una riga in più se la
  // pagina la mette in data-dettaglio). Gli elementi si descrivono con gli attributi data-nome, data-prov e
  // data-dettaglio; chi vuole altro passa { contenuto(elemento) } che restituisce { titolo, righe: [[colore, testo]] }
  // oppure null. Col tocco il riquadretto compare dove si tocca e resta qualche secondo; su una regione vicina il primo
  // tocco mostra solo il nome e il secondo la apre (così sul telefono non si cambia regione per sbaglio). Durante il
  // trascinamento e lo zoom il riquadretto si spegne.
  const tocchiRegione = new WeakMap();      // svg → regione appena toccata una volta (attende il secondo tocco)
  function contenutoPredefinito(t, tocco) {
    if (!t || !t.dataset || !t.dataset.nome) return null;
    if (t.closest(".italia-sfondo")) {
      // la regione scelta: sopra ci sono i suoi comuni; dove non ce ne sono (province non disegnate, piccoli vuoti
      // lungo i confini) compare comunque il nome della regione
      if (t.classList.contains("attiva")) return { titolo: t.dataset.nome, righe: [[null, "regione scelta"]] };
      return { titolo: t.dataset.nome, righe: [[null, tocco ? "regione: tocca di nuovo per aprirla" : "regione: clic per aprirla"]] };
    }
    const righe = [];
    if (t.dataset.dettaglio) t.dataset.dettaglio.split("\n").forEach((r) => righe.push([null, r]));
    return { titolo: t.dataset.prov ? `${t.dataset.nome} (${t.dataset.prov})` : t.dataset.nome, righe };
  }
  function suggerimenti(svg, opz = {}) {
    if (!svg || svg.__suggerimenti) return svg && svg.__suggerimenti;
    const box = svg.closest(".mappa") || svg.parentNode;
    let et = box.querySelector(".etichetta-mappa");
    if (!et) { et = document.createElement("div"); et.className = "etichetta-mappa"; box.appendChild(et); }
    et.setAttribute("aria-hidden", "true");
    const trova = (bersaglio) => (bersaglio && bersaglio.closest ? bersaglio.closest(opz.selettore || "[data-nome], [data-barra]") : null);
    let attivo = null, timer = 0;
    function contenuto(t, tocco) {
      if (opz.contenuto) { const c = opz.contenuto(t, tocco); if (c !== undefined) return c; }
      return contenutoPredefinito(t, tocco);
    }
    function mostra(t, x, y, tocco) {
      const c = t && contenuto(t, tocco);
      if (!c) { nascondi(); return; }
      if (t !== attivo) {
        et.innerHTML = "";
        const b = document.createElement("b"); b.textContent = c.titolo; et.appendChild(b);
        for (const [colore, testo] of c.righe || []) {
          const d = document.createElement("div");
          if (colore) { const q = document.createElement("i"); q.style.background = colore; d.appendChild(q); }
          d.append(testo);
          et.appendChild(d);
        }
        if (attivo && attivo.classList) attivo.classList.remove("sotto-mouse");
        attivo = t;
        if (opz.evidenzia !== false && t.classList) t.classList.add("sotto-mouse");
      }
      et.style.display = "block";
      const r = box.getBoundingClientRect(), w = et.offsetWidth, h = et.offsetHeight;
      let sx = x - r.left + 14, sy = y - r.top + 16;
      if (sx + w > r.width - 4) sx = x - r.left - 14 - w;
      if (sy + h > r.height - 4) sy = y - r.top - 16 - h;
      et.style.left = `${Math.max(4, Math.min(sx, r.width - w - 4))}px`;
      et.style.top = `${Math.max(4, sy)}px`;
    }
    function nascondi() {
      clearTimeout(timer);
      et.style.display = "none";
      if (attivo && attivo.classList) attivo.classList.remove("sotto-mouse");
      attivo = null;
    }
    const trascina = () => svg.classList.contains("trascina");
    svg.addEventListener("pointermove", (e) => {
      if (e.pointerType === "touch") return;                 // col dito vale il tocco
      if (e.buttons || trascina()) { if (attivo) nascondi(); return; }
      mostra(trova(e.target), e.clientX, e.clientY, false);
    });
    svg.addEventListener("pointerleave", (e) => { if (e.pointerType !== "touch") nascondi(); });
    svg.addEventListener("wheel", () => nascondi(), { passive: true });
    let giu = null;
    svg.addEventListener("pointerdown", (e) => { giu = { x: e.clientX, y: e.clientY, t: e.pointerType }; if (e.pointerType === "touch") nascondi(); });
    svg.addEventListener("pointerup", (e) => {
      if (e.pointerType !== "touch" || !giu || Math.hypot(e.clientX - giu.x, e.clientY - giu.y) > 8 || trascina()) return;
      const t = trova(e.target);
      // regione vicina: il primo tocco mostra il nome, il secondo (entro 4 secondi) la apre
      if (t && t.closest(".italia-sfondo") && !t.classList.contains("attiva")) {
        const prima = tocchiRegione.get(svg);
        tocchiRegione.set(svg, prima && prima.el === t && Date.now() - prima.quando < 4000 ? { el: t, conferma: true } : { el: t, quando: Date.now() });
      }
      mostra(t, e.clientX, e.clientY, true);
      clearTimeout(timer);
      timer = setTimeout(nascondi, 3500);
    });
    addEventListener("scroll", () => { if (attivo) nascondi(); }, { passive: true, capture: true });
    svg.__suggerimenti = { nascondi, mostra };
    return svg.__suggerimenti;
  }
  // per il clic su una regione vicina: col tocco vale solo il secondo tocco
  function toccoConfermato(svg, p, e) {
    if (!e || e.pointerType !== "touch") return true;       // click col mouse (pointerType "mouse" o vuoto)
    const t = tocchiRegione.get(svg);
    if (t && t.el === p && t.conferma) { tocchiRegione.delete(svg); return true; }
    return false;
  }

  // sotto la mappa grande: tutte le regioni (colore tenue); sopra: i loro confini, più spessi delle province
  async function sfondoItalia(svg) {
    const m = await italia();
    const sotto = el("g", { class: "italia-sfondo" });
    svg.insertBefore(sotto, svg.firstChild);
    const sopra = el("g", { class: "confini-regioni" }, svg);
    for (const r of m.regioni) {
      const p = el("path", { d: r.d, fill: `var(--reg-${r.cod})` }, sotto);
      p.dataset.cod = r.cod;
      p.dataset.nome = r.nome;            // riquadretto col nome (suggerimenti), al posto del vecchio <title>
      if (r.cod === regione) p.classList.add("attiva");
      // clic su una regione vicina: diventa la regione della mappa grande, come dalla piccola mappa
      p.addEventListener("click", (e) => { if (r.cod !== regione && toccoConfermato(svg, p, e)) cambiaRegione(r.cod, r.nome); });
      el("path", { d: r.d }, sopra);
    }
    suggerimenti(svg);
    return m;
  }

  // la mappa grande: si apre sulla regione scelta (riquadro dal file RR.json), si muove su tutta l'Italia
  const ITALIA = [0, 0, 1000, 1288.1];   // viewBox comune a tutti i file di dati/mappa
  function mappaGrande(svg, riquadroRegione) {
    let riquadro = riquadroRegione;
    svg.setAttribute("viewBox", riquadro.join(" "));
    const z = zoomabile(svg, { limiti: () => ITALIA, ritorno: () => riquadro });
    suggerimenti(svg);                     // nomi di regioni e comuni al passaggio del mouse o al tocco
    const mappa = {
      ...z,
      inquadra(r) { riquadro = r; svg.setAttribute("viewBox", r.join(" ")); },
      nazionale() { svg.setAttribute("viewBox", ITALIA.join(" ")); },   // la freccia accanto alla piccola mappa
    };
    window.EUGENIO.mappaPrincipale = mappa;
    if (apriSuItalia) mappa.nazionale();
    return mappa;
  }

  // i collegamenti alle altre pagine delle funzioni portano con sé la regione
  function aggiornaCollegamenti(cod) {
    document.querySelectorAll('.testata nav a, .pannello a, .sotto a').forEach((a) => {
      const href = a.getAttribute("href") || "";
      if (!/^(\.\/|patrimonio\.html|legge10\.html|dati\.html|indicatori\.html)(\?|$)/.test(href)) return;
      const u = new URL(href, location.href);
      u.searchParams.set("regione", cod);
      a.setAttribute("href", (u.pathname.split("/").pop() || "./") + u.search);
    });
  }

  async function piccola() {
    const area = document.querySelector(".mappa-area");
    const titolo = area && area.querySelector("h1");
    if (!titolo) return;
    const sotto = titolo.nextElementSibling && titolo.nextElementSibling.classList.contains("sotto") ? titolo.nextElementSibling : null;
    const riga = document.createElement("div");
    riga.className = "intestazione";
    const testi = document.createElement("div");
    testi.className = "intestazione-testi";
    titolo.before(riga);
    riga.appendChild(testi);
    testi.appendChild(titolo);
    if (sotto) testi.appendChild(sotto);
    const box = document.createElement("div");
    box.className = "minimappa";
    box.innerHTML = '<div class="minimappa-etichetta" role="status"></div>' +
      '<div class="minimappa-comandi"><button type="button" data-z="1.6" title="Ingrandisci" aria-label="Ingrandisci la piccola mappa">+</button>' +
      '<button type="button" data-z="0.625" title="Rimpicciolisci" aria-label="Rimpicciolisci la piccola mappa">−</button>' +
      '<button type="button" data-z="0" title="Ripristina la vista" aria-label="Ripristina la vista della piccola mappa">⟲</button></div>';
    riga.appendChild(box);
    const etichetta = box.querySelector(".minimappa-etichetta");
    // freccia in basso, ultima dei comandi: la mappa grande (qui sotto) mostra tutta l'Italia; la regione scelta resta
    const su = document.createElement("button");
    su.type = "button";
    su.className = "minimappa-su";
    su.textContent = "↓";
    su.title = "Mostra tutta l'Italia nella mappa grande";
    su.setAttribute("aria-label", "Mostra tutta l'Italia nella mappa grande");
    su.addEventListener("click", () => window.EUGENIO.mappaPrincipale && window.EUGENIO.mappaPrincipale.nazionale());
    box.querySelector(".minimappa-comandi").appendChild(su);

    let m;
    try { m = await italia(); } catch { box.remove(); return; }
    const svg = el("svg", { viewBox: m.viewBox.join(" "), role: "group", "aria-label": "Scegli la regione" });
    box.prepend(svg);
    const g = el("g", {}, svg);
    const percorsi = new Map();
    for (const reg of m.regioni) {
      const p = el("path", { d: reg.d, fill: `var(--reg-${reg.cod})`, tabindex: "0", role: "button", "aria-label": reg.nome }, g);
      p.dataset.cod = reg.cod;
      if (reg.cod === regione) p.classList.add("attiva");
      percorsi.set(reg.cod, p);
      p.addEventListener("mousemove", (e) => mostra(e, reg.nome));
      p.addEventListener("mouseleave", () => (etichetta.style.display = "none"));
      p.addEventListener("focus", () => { etichetta.textContent = reg.nome; etichetta.style.display = "block"; etichetta.style.left = "0"; etichetta.style.top = "0"; });
      p.addEventListener("blur", () => (etichetta.style.display = "none"));
      p.addEventListener("click", () => scegli(reg.cod, reg.nome));
      p.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); scegli(reg.cod, reg.nome); } });
    }
    const attiva = percorsi.get(regione);
    if (attiva) attiva.parentNode.appendChild(attiva);
    evidenzia = (cod) => {
      percorsi.forEach((p) => p.classList.remove("attiva"));
      const p = percorsi.get(cod);
      if (p) { p.classList.add("attiva"); p.parentNode.appendChild(p); }
    };

    function mostra(e, nome) {
      const b = box.getBoundingClientRect();
      etichetta.textContent = nome;
      etichetta.style.display = "block";
      etichetta.style.left = `${Math.max(0, Math.min(e.clientX - b.left + 10, b.width - etichetta.offsetWidth))}px`;
      etichetta.style.top = `${Math.max(0, e.clientY - b.top - 28)}px`;
    }
    function scegli(cod, nome) { cambiaRegione(cod, nome); }
    const z = zoomabile(svg, {
      limiti: () => m.viewBox, ritorno: () => m.viewBox, minimo: 1 / 12,
      suCambio: (frazione) => {
        svg.style.setProperty("--tratto-mm", (1.2 * frazione).toFixed(3));
        box.classList.toggle("ingrandita", frazione < 0.999);
      },
    });
    // solo +, − e ⟲: la freccia ↓ non ha data-z e non deve toccare la piccola mappa (prima la zoomava con NaN)
    box.querySelectorAll(".minimappa-comandi button[data-z]").forEach((b) => b.addEventListener("click", () => z.zoom(+b.dataset.z)));
  }

  // cambio di regione dalla piccola mappa o da una regione vicina nella mappa grande: stessa strada per entrambe
  function cambiaRegione(cod, nome) {
    if (cod === regione || !VALIDE.test(cod)) return;
    regione = cod;
    window.EUGENIO.regione = cod;
    ricorda(cod);
    if (evidenzia) evidenzia(cod);
    document.querySelectorAll(".mappa .italia-sfondo path").forEach((p) => p.classList.toggle("attiva", p.dataset.cod === cod));
    aggiornaCollegamenti(cod);
    const u = new URL(location.href);
    u.searchParams.set("regione", cod);
    u.searchParams.delete("vista");          // scelta la regione, la mappa grande si apre su di lei
    if (typeof window.EUGENIO.suRegione === "function") {
      // la pagina cambia regione da sola (patrimonio, dati: niente ricarica, i risultati restano)
      history.replaceState(null, "", u);
      window.EUGENIO.suRegione(cod, nome);
    } else {
      u.searchParams.delete("comune");
      location.href = u.toString();
    }
  }

  // la pagina ha cambiato regione da sola (per esempio da un elenco): la piccola mappa e i collegamenti la seguono
  let evidenzia = null;
  function seleziona(cod) {
    if (!VALIDE.test(cod)) return;
    regione = cod;
    window.EUGENIO.regione = cod;
    ricorda(cod);
    if (evidenzia) evidenzia(cod);
    aggiornaCollegamenti(cod);
  }

  window.EUGENIO = { regione, colore, fondoComuni, italia, zoomabile, sfondoItalia, mappaGrande, el, seleziona, suggerimenti };
  window.EUGENIO_REGIONE = regione;     // compatibilità
  aggiornaCollegamenti(regione);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => piccola().catch(() => {}));
  else piccola().catch(() => {});
})();
