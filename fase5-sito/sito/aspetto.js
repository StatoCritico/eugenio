"use strict";
// Aspetto del sito, parte comune a tutte le pagine: tema (scuro o chiaro) e «vestito» (Corallo, Ambra, Indaco, Lime,
// Verde). Lo script anticipato nel <head> di ogni pagina legge le scelte salvate e mette data-theme e data-vestito su
// <html> prima del CSS; qui si collegano i pulsanti.
//  - Tema: i pulsanti ◐ (.tema), uno nella riga del menu e uno, per il telefono, nella riga del marchio.
//  - Vestito: il pulsante con l'asterisco (.vestito-pulsante) apre l'elenco a discesa (role="listbox"); nel menu del
//    telefono lo stesso elenco è sempre aperto. Tastiera: frecce, Inizio/Fine, Invio o Spazio per scegliere, Esc per
//    chiudere; un clic fuori chiude l'elenco.
// Dopo una scelta la pagina si ricarica: mappe e grafici leggono i colori dal CSS quando vengono disegnati.
// Se il browser non salva le scelte (navigazione privata con memoria bloccata), il cambio vale solo per la pagina aperta.
(function () {
  const radice = document.documentElement;
  const VESTITI = { corallo: "Corallo", ambra: "Ambra", indaco: "Indaco", lime: "Lime", verde: "Verde" };
  const attivo = VESTITI[radice.dataset.vestito] ? radice.dataset.vestito : "corallo";
  const chiaro = radice.dataset.theme === "light";

  function salva(chiave, valore) {
    try { localStorage.setItem(chiave, valore); return localStorage.getItem(chiave) === valore; } catch (e) { return false; }
  }
  if (typeof window.eugenioLoghi === "function") window.eugenioLoghi();

  // ------------------------------------------------------------------ tema
  document.querySelectorAll(".tema").forEach((b) => {
    const testo = chiaro ? "Passa al tema scuro" : "Passa al tema chiaro";
    b.setAttribute("aria-label", testo);
    b.title = testo;
    b.addEventListener("click", () => {
      if (salva("tema", chiaro ? "dark" : "light")) { location.reload(); return; }
      if (chiaro) delete radice.dataset.theme; else radice.dataset.theme = "light";
      if (window.eugenioLoghi) window.eugenioLoghi();
    });
  });

  // ------------------------------------------------------------------ vestito
  function scegli(v) {
    if (!VESTITI[v] || v === attivo) return;
    if (salva("vestito", v)) { location.reload(); return; }
    if (v === "corallo") delete radice.dataset.vestito; else radice.dataset.vestito = v;
    if (window.eugenioLoghi) window.eugenioLoghi();
  }

  function elenco(ul, pulsante) {
    const voci = [...ul.querySelectorAll('[role="option"]')];
    if (!voci.length) return;
    const scelto = () => Math.max(0, voci.findIndex((o) => o.dataset.vestito === attivo));
    let i = scelto();
    voci.forEach((o) => o.setAttribute("aria-selected", String(o.dataset.vestito === attivo)));
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

    if (!pulsante) return;
    const nome = `Vestito del sito: ${VESTITI[attivo]}`;
    pulsante.setAttribute("aria-label", nome);
    pulsante.title = nome;
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
