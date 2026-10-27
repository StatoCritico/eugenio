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
  document.querySelectorAll(".tema").forEach((b) => {
    b.addEventListener("click", () => {
      cambiaAspetto(() => {
        chiaro = !chiaro;
        if (chiaro) radice.dataset.theme = "light"; else delete radice.dataset.theme;
        salva("tema", chiaro ? "light" : "dark");
      });
      etichetteTema();
    });
  });

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

  document.querySelectorAll(".vestito").forEach((box) => {
    const ul = box.querySelector(".vestito-elenco");
    if (ul) elenco(ul, box.querySelector(".vestito-pulsante"));
  });

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
