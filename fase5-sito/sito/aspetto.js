"use strict";
// Aspetto del sito, parte comune a tutte le pagine: tema (scuro o chiaro) e «vestito» (Corallo, Ambra, Indaco, Lime,
// Verde). Lo script anticipato nel <head> di ogni pagina legge le scelte salvate e mette data-theme e data-vestito su
// <html> prima del CSS; qui si collegano i pulsanti.
//  - Tema: i pulsanti ◐ (.tema), uno nella riga del menu e uno, per il telefono, nella riga del marchio.
//  - Vestito: il pulsante con l'asterisco (.vestito-pulsante) apre l'elenco a discesa (role="listbox"); nel menu del
//    telefono lo stesso elenco è sempre aperto. Tastiera: frecce, Inizio/Fine, Invio o Spazio per scegliere, Esc per
//    chiudere; un clic fuori chiude l'elenco.
// Dopo una scelta la pagina NON si ricarica (nella Previsione si perderebbe il file caricato): si cambiano gli
// attributi su <html> e i loghi, poi si ricolorano mappe e grafici già disegnati (che hanno i colori scritti negli
// attributi SVG) sostituendo ogni colore che era il valore di una variabile CSS con il nuovo valore della stessa
// variabile; infine si emette l'evento "eugenio:aspetto" per i colori calcolati (fondo dei comuni, scale), che gli
// script delle pagine rifanno da sé. La scelta si salva nel browser, se si può.
(function () {
  const radice = document.documentElement;
  const VESTITI = { corallo: "Corallo", ambra: "Ambra", indaco: "Indaco", lime: "Lime", verde: "Verde" };
  let attivo = VESTITI[radice.dataset.vestito] ? radice.dataset.vestito : "corallo";
  let chiaro = radice.dataset.theme === "light";

  function salva(chiave, valore) {
    try { localStorage.setItem(chiave, valore); return localStorage.getItem(chiave) === valore; } catch (e) { return false; }
  }
  if (typeof window.eugenioLoghi === "function") window.eugenioLoghi();

  // ------------------------------------------------------------------ testata fissa
  // la testata resta ferma in alto (position: sticky): la sua altezza va in --alto-testata, che il CSS usa per gli
  // altri elementi fissi (mappa, indice laterale) e per i punti d'arrivo dei collegamenti interni
  const testata = document.querySelector(".testata");
  if (testata) {
    const misura = () => radice.style.setProperty("--alto-testata", `${testata.offsetHeight}px`);
    misura();
    if ("ResizeObserver" in window) new ResizeObserver(misura).observe(testata);
    else window.addEventListener("resize", misura);
  }

  // ------------------------------------------------------------------ cambio di colori senza ricaricare
  // nomi delle variabili CSS definite nei fogli di stile del sito (stesso dominio)
  function nomiVariabili() {
    const nomi = new Set();
    const giro = (regole) => {
      for (const r of regole) {
        if (r.style) for (const p of r.style) if (p.startsWith("--")) nomi.add(p);
        if (r.cssRules) giro(r.cssRules);
      }
    };
    for (const f of document.styleSheets) { try { giro(f.cssRules); } catch (e) { /* foglio di un altro dominio */ } }
    return [...nomi];
  }
  // colore in forma unica (#rrggbb o rgba(...)), per confrontare "#FF7A50", "#ff7a50" e "rgb(255, 122, 80)"
  const tela = document.createElement("canvas").getContext("2d");
  function norma(v) {
    v = (v || "").trim();
    if (!v || !/^(#|rgb|hsl)/i.test(v)) return null;
    tela.fillStyle = "#010203"; tela.fillStyle = v;
    const n = tela.fillStyle;
    return n === "#010203" && !/^#010203$/i.test(v) ? null : n;
  }
  function fotografia(nomi) {
    const cs = getComputedStyle(radice), m = new Map();
    for (const n of nomi) { const v = norma(cs.getPropertyValue(n)); if (v) m.set(n, v); }
    return m;
  }
  // ogni colore scritto negli attributi o nello stile in linea che era il valore di una variabile → nuovo valore
  function ricolora(prima, dopo) {
    const indice = new Map();      // vecchio valore → nuovo (la prima variabile con quel valore)
    for (const [n, v] of prima) if (!indice.has(v) && dopo.has(n)) indice.set(v, dopo.get(n));
    const nuovo = (v) => { const k = norma(v); return k && indice.has(k) ? indice.get(k) : null; };
    const PROP = ["color", "background-color", "fill", "stroke", "border-color", "border-top-color"];
    for (const e of document.querySelectorAll("body [fill], body [stroke], body [stop-color], body [style]")) {
      for (const a of ["fill", "stroke", "stop-color"]) {
        const v = e.getAttribute(a);
        if (v && v !== "none") { const n = nuovo(v); if (n) e.setAttribute(a, n); }
      }
      if (e.style && e.style.length) {
        for (const p of PROP) {
          const v = e.style.getPropertyValue(p);
          if (v) { const n = nuovo(v); if (n) e.style.setProperty(p, n); }
        }
        const sf = e.style.getPropertyValue("background");
        if (sf && !/gradient/.test(sf)) { const n = nuovo(sf); if (n) e.style.setProperty("background", n); }
      }
    }
  }
  function cambiaAspetto(applica) {
    const nomi = nomiVariabili(), prima = fotografia(nomi);
    applica();
    if (window.eugenioLoghi) window.eugenioLoghi();
    ricolora(prima, fotografia(nomi));
    document.dispatchEvent(new CustomEvent("eugenio:aspetto", { detail: { tema: chiaro ? "chiaro" : "scuro", vestito: attivo } }));
  }

  // ------------------------------------------------------------------ tema
  function etichetteTema() {
    const testo = chiaro ? "Passa al tema scuro" : "Passa al tema chiaro";
    document.querySelectorAll(".tema").forEach((b) => { b.setAttribute("aria-label", testo); b.title = testo; });
  }
  etichetteTema();
  function cambiaTema() {
    cambiaAspetto(() => {
      chiaro = !chiaro;
      if (chiaro) radice.dataset.theme = "light"; else delete radice.dataset.theme;
      salva("tema", chiaro ? "light" : "dark");
    });
    etichetteTema();
  }
  function collegaTema(b) { b.addEventListener("click", cambiaTema); }
  document.querySelectorAll(".tema").forEach(collegaTema);

  // ------------------------------------------------------------------ vestito
  const aggiornatori = [];        // un aggiornamento per ogni elenco dei vestiti (testata e menu del telefono)
  function scegli(v) {
    if (!VESTITI[v] || v === attivo) return;
    cambiaAspetto(() => {
      attivo = v;
      if (v === "corallo") delete radice.dataset.vestito; else radice.dataset.vestito = v;
      salva("vestito", v);
    });
    aggiornatori.forEach((f) => f());
  }

  function elenco(ul, pulsante) {
    const voci = [...ul.querySelectorAll('[role="option"]')];
    if (!voci.length) return;
    const scelto = () => Math.max(0, voci.findIndex((o) => o.dataset.vestito === attivo));
    let i = scelto();
    const segnaScelto = () => voci.forEach((o) => o.setAttribute("aria-selected", String(o.dataset.vestito === attivo)));
    segnaScelto();
    function evidenzia(n) {
      i = (n + voci.length) % voci.length;
      voci.forEach((o, k) => o.classList.toggle("attiva", k === i));
      ul.setAttribute("aria-activedescendant", voci[i].id);
    }
    evidenzia(i);

    function fuori(e) { if (!ul.contains(e.target) && !pulsante.contains(e.target)) chiudi(false); }
    function apri(dove) {
      ul.hidden = false;
      pulsante.setAttribute("aria-expanded", "true");
      evidenzia(dove === undefined ? scelto() : dove);
      ul.focus();
      document.addEventListener("pointerdown", fuori, true);
    }
    function chiudi(rimetti) {
      ul.hidden = true;
      pulsante.setAttribute("aria-expanded", "false");
      document.removeEventListener("pointerdown", fuori, true);
      if (rimetti) pulsante.focus();
    }
    function conferma(k) {
      evidenzia(k);
      if (pulsante) chiudi(true);
      scegli(voci[k].dataset.vestito);
    }

    ul.addEventListener("keydown", (e) => {
      switch (e.key) {
        case "ArrowDown": case "ArrowRight": evidenzia(i + 1); break;
        case "ArrowUp": case "ArrowLeft": evidenzia(i - 1); break;
        case "Home": evidenzia(0); break;
        case "End": evidenzia(voci.length - 1); break;
        case "Enter": case " ": conferma(i); break;
        case "Escape": if (!pulsante) return; chiudi(true); break;
        case "Tab": if (pulsante) chiudi(false); return;
        default: return;
      }
      e.preventDefault();
    });
    voci.forEach((o, k) => o.addEventListener("click", () => conferma(k)));

    const nomePulsante = () => {
      if (!pulsante) return;
      const nome = `Vestito del sito: ${VESTITI[attivo]}`;
      pulsante.setAttribute("aria-label", nome);
      pulsante.title = nome;
    };
    aggiornatori.push(() => { segnaScelto(); nomePulsante(); });
    if (!pulsante) return;
    nomePulsante();
    pulsante.addEventListener("click", () => (ul.hidden ? apri() : chiudi(true)));
    pulsante.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") { e.preventDefault(); apri(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); apri(); }
    });
  }

  function collegaVestito(box) {
    const ul = box.querySelector(".vestito-elenco");
    if (ul) elenco(ul, box.querySelector(".vestito-pulsante"));
  }
  document.querySelectorAll(".vestito").forEach(collegaVestito);

  // per gli altri script (per esempio il riquadro dei grafici di grafici.js, che ha i suoi ✱ e ◐): le stesse funzioni
  // dei pulsanti della testata, così il cambio vale per tutta la pagina
  //  - collegaTema(pulsante): un nuovo pulsante ◐ (classe .tema, per le etichette «Passa al tema …»)
  //  - collegaVestito(box): un nuovo blocco .vestito con .vestito-pulsante e .vestito-elenco (id propri)
  window.EUGENIO_ASPETTO = {
    cambiaTema, scegliVestito: scegli, collegaTema, collegaVestito, etichetteTema,
    vestito: () => attivo, chiaro: () => chiaro, VESTITI: { ...VESTITI },
  };

  // menu dei servizi a gruppi (03/11/2026; comportamento nuovo del 04/11/2026): cinque <details class="voce-gruppo">
  // con il sottomenu a tendina. Senza JavaScript si aprono e chiudono comunque con un clic. Con JavaScript:
  //  - la tendina verticale si apre al passaggio del mouse e al fuoco da tastiera (Tab sul titolo), si chiude quando il
  //    mouse esce (con un piccolo ritardo), con Esc (il fuoco torna sul titolo), con un clic fuori o quando il fuoco esce;
  //    frecce ↓ ↑ Inizio Fine tra le voci, ← → tra i gruppi; un solo gruppo aperto alla volta;
  //  - il clic (o Invio, Spazio) sul titolo NON apre la tendina: «fissa» il gruppo, cioè ne mostra le voci in
  //    orizzontale nella riga nera sotto la barra dei menu (nav.riga-fissata, la riempie questo script copiando le voci
  //    della tendina); la tendina di quel gruppo allora non si apre più. Clic su un altro gruppo: la riga passa a quello.
  //    Secondo clic sullo stesso titolo: la riga sparisce e torna la tendina. Sul titolo aria-pressed dice se è fissato;
  //    title e una descrizione per i lettori di schermo dicono cosa fa il clic;
  //  - la scelta resta nel browser (localStorage «menu-fissato»): lo script nel <head> mette data-menu-fissato su <html>
  //    prima del CSS, così la riga ha già il suo posto e la pagina non salta;
  //  - sul telefono (sotto 861 px) la barra dei gruppi non c'è: la riga fissata resta visibile, scorre in orizzontale e ha
  //    il pulsante × per richiuderla.
  // Le voci in attesa della licenza GME sono <span class="voce-gme"> e non collegamenti: non si cliccano, non prendono il
  // fuoco e hanno il suggerimento «In attesa di autorizzazione dal GME» (con un tocco la nota compare anche sul telefono).
  const gruppi = [...document.querySelectorAll("details.voce-gruppo")];
  const vociDi = (d) => [...d.querySelectorAll(".tendina a")];
  const chiudiGruppi = (tranne) => gruppi.forEach((d) => { if (d !== tranne) d.open = false; });
  const riga = document.querySelector("nav.riga-fissata");
  const CHIAVE = "menu-fissato";
  const nomeGruppo = (d) => {
    const s = d.querySelector("summary");
    return s ? (s.dataset.nome || s.textContent).trim() : "";
  };
  const gruppoDa = (id) => gruppi.find((d) => d.dataset.gruppo === id) || null;
  let fissato = riga ? gruppoDa(radice.dataset.menuFissato) : null;

  function suggerimento(d) {
    const s = d.querySelector("summary"), nome = nomeGruppo(d), su = d === fissato;
    const testo = su ? `Clicca qui per richiudere la barra di ${nome} e tornare al menu a tendina`
                     : `Clicca qui per fissare il menu ${nome} sotto la barra`;
    s.title = testo;
    s.setAttribute("aria-pressed", String(su));
    if (su && riga) s.setAttribute("aria-controls", riga.id); else s.removeAttribute("aria-controls");
    const desc = document.getElementById(`suggerimento-${d.dataset.gruppo}`);
    if (desc) desc.textContent = testo;
    d.classList.toggle("fissato", su);
  }

  function riempiRiga() {
    if (!riga) return;
    riga.textContent = "";
    if (!fissato) { delete radice.dataset.menuFissato; return; }
    radice.dataset.menuFissato = fissato.dataset.gruppo;
    const nome = nomeGruppo(fissato);
    riga.setAttribute("aria-label", `Menu ${nome}, fissato`);
    const dentro = document.createElement("div");
    dentro.className = "riga-dentro";
    const titolo = document.createElement("span");
    titolo.className = "riga-titolo";
    titolo.textContent = nome;
    const ul = document.createElement("ul");
    ul.className = "riga-voci";
    fissato.querySelectorAll(".tendina > li").forEach((li) => {
      const copia = li.cloneNode(true);
      copia.querySelectorAll(".voce-gme").forEach((v) => { v.classList.remove("con-nota"); delete v.dataset.collegata; });
      ul.appendChild(copia);
    });
    const chiudi = document.createElement("button");
    chiudi.type = "button";
    chiudi.className = "riga-chiudi";
    chiudi.setAttribute("aria-label", `Chiudi la barra di ${nome}`);
    chiudi.title = `Chiudi la barra di ${nome}`;
    chiudi.textContent = "×";
    chiudi.addEventListener("click", () => fissa(null));
    dentro.append(titolo, ul, chiudi);
    riga.appendChild(dentro);
    collegaGme(riga);
    // la voce della pagina aperta resta in vista quando la riga scorre (telefono)
    const qui = ul.querySelector('[aria-current="page"]');
    const mostra = () => {
      if (!qui || ul.scrollWidth <= ul.clientWidth) return;
      const x = qui.getBoundingClientRect().left - ul.getBoundingClientRect().left + ul.scrollLeft;
      ul.scrollLeft = Math.max(0, x - 16);
    };
    mostra();
    if (qui && document.fonts && document.fonts.ready) document.fonts.ready.then(mostra);   // le larghezze cambiano con i caratteri
  }

  function fissa(d) {
    fissato = d;
    try { if (d) localStorage.setItem(CHIAVE, d.dataset.gruppo); else localStorage.removeItem(CHIAVE); } catch (e) { /* niente */ }
    chiudiGruppi(null);
    gruppi.forEach(suggerimento);
    riempiRiga();
  }

  gruppi.forEach((d, i) => {
    const titolo = d.querySelector("summary"), li = d.parentElement;
    titolo.dataset.nome = titolo.textContent.trim();
    // descrizione per i lettori di schermo (fuori dal <details>, così si legge anche a tendina chiusa)
    const desc = document.createElement("span");
    desc.className = "solo-lettori";
    desc.id = `suggerimento-${d.dataset.gruppo}`;
    li.appendChild(desc);
    titolo.setAttribute("aria-describedby", desc.id);
    suggerimento(d);

    d.addEventListener("toggle", () => { if (d.open) chiudiGruppi(d); });

    // passaggio del mouse: apre la tendina (non quella del gruppo fissato), la chiude poco dopo l'uscita
    let timer = 0;
    const apri = () => { clearTimeout(timer); if (d !== fissato) d.open = true; };
    li.addEventListener("mouseenter", apri);
    li.addEventListener("mouseleave", () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const fuoco = d.contains(document.activeElement) && document.activeElement.matches(":focus-visible");
        if (!li.matches(":hover") && !fuoco) d.open = false;
      }, 180);
    });
    // fuoco da tastiera sul titolo: apre la tendina (il fuoco del clic del mouse non conta)
    titolo.addEventListener("focus", () => { if (d !== fissato && titolo.matches(":focus-visible")) d.open = true; });

    // clic, Invio o Spazio sul titolo: fissa o richiude la riga, non apre la tendina
    titolo.addEventListener("click", (e) => {
      if (!riga) return;
      e.preventDefault();
      if (d === fissato) {
        fissa(null);
        if (li.matches(":hover") || titolo.matches(":focus-visible")) d.open = true;   // torna il menu a tendina
      } else {
        fissa(d);
      }
    });

    d.addEventListener("keydown", (e) => {
      const voci = vociDi(d), qui = voci.indexOf(document.activeElement);
      const vai = (n) => {
        e.preventDefault();
        if (d === fissato) {                      // gruppo fissato: le frecce portano nella riga
          const r = riga ? [...riga.querySelectorAll(".riga-voci a")] : [];
          if (r.length) r[n < 0 ? r.length - 1 : 0].focus();
          return;
        }
        d.open = true;
        voci[(n + voci.length) % voci.length].focus();
      };
      if (e.key === "Escape" && d.open) {
        e.preventDefault(); e.stopPropagation(); d.open = false; titolo.focus();
      } else if (e.key === "ArrowDown") vai(qui < 0 ? 0 : qui + 1);
      else if (e.key === "ArrowUp") vai(qui < 0 ? -1 : qui - 1);
      else if (e.key === "Home" && qui >= 0) vai(0);
      else if (e.key === "End" && qui >= 0) vai(voci.length - 1);
      else if ((e.key === "ArrowRight" || e.key === "ArrowLeft") && gruppi.length > 1) {
        e.preventDefault();
        const altro = gruppi[(i + (e.key === "ArrowRight" ? 1 : -1) + gruppi.length) % gruppi.length];
        const aperto = d.open;
        d.open = false;
        altro.querySelector("summary").focus();
        altro.open = aperto && altro !== fissato;
      }
    });
    // il fuoco che esce dal gruppo (Tab oltre l'ultima voce) lo chiude
    d.addEventListener("focusout", (e) => { if (d.open && e.relatedTarget && !d.contains(e.relatedTarget)) d.open = false; });
  });
  document.addEventListener("click", (e) => { if (!e.target.closest || !e.target.closest("details.voce-gruppo")) chiudiGruppi(null); });

  // riga fissata: frecce ← → tra le voci, Esc rimette il fuoco sul titolo del gruppo
  if (riga) {
    riga.addEventListener("keydown", (e) => {
      const voci = [...riga.querySelectorAll(".riga-voci a")], qui = voci.indexOf(document.activeElement);
      if (qui < 0) return;
      let n = null;
      if (e.key === "ArrowRight") n = qui + 1;
      else if (e.key === "ArrowLeft") n = qui - 1;
      else if (e.key === "Home") n = 0;
      else if (e.key === "End") n = voci.length - 1;
      else if (e.key === "Escape" && fissato) { e.preventDefault(); fissato.querySelector("summary").focus(); return; }
      if (n === null) return;
      e.preventDefault();
      voci[(n + voci.length) % voci.length].focus();
    });
    if (fissato) fissato.open = false;
    if (radice.dataset.menuFissato && !fissato) {   // valore salvato non valido
      try { localStorage.removeItem(CHIAVE); } catch (e) { /* niente */ }
    }
    riempiRiga();
  }

  // voci in attesa della licenza GME: un tocco (o un clic) mostra la nota anche dove il title non compare
  function collegaGme(dove) {
    dove.querySelectorAll(".voce-gme").forEach((v) => {
      if (v.dataset.collegata) return;
      v.dataset.collegata = "1";
      v.addEventListener("click", (e) => {
        e.preventDefault(); e.stopPropagation();
        const prima = v.classList.contains("con-nota");
        document.querySelectorAll(".voce-gme.con-nota").forEach((x) => x.classList.remove("con-nota"));
        if (!prima) v.classList.add("con-nota");
      });
    });
  }
  collegaGme(document);

  // menu del telefono: Esc lo chiude e rimette il fuoco sul pulsante «Menu»
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    document.querySelectorAll("details.menu-tutto[open]").forEach((d) => {
      d.open = false;
      const s = d.querySelector("summary");
      if (s) s.focus();
    });
  });
})();
