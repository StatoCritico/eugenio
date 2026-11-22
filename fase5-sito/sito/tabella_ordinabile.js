"use strict";
// Tabella ordinabile (22/11/2026, prima usata in Territorio › Edifici pubblici, ricerca per ente). Componente riusabile,
// senza dipendenze; regole in README_stile.md, «Tabelle ordinabili».
//
//   const t = EUGENIO_TABELLA_ORDINABILE.crea({
//     colonne: [{ chiave: "comune", titolo: "Comune", tipo: "testo" },          // tipo «testo» (predefinito) o «numero»
//               { chiave: "sup_mq", titolo: "Superficie (m²)", tipo: "numero",
//                 formato: (v, riga) => EUGENIO_NUMERI.formato(v),              // testo della cella (predefinito: il valore)
//                 classe: "solo-largo" }],                                      // classe di th e td (es. nascosta sul telefono)
//     righe: [...],                     // oggetti con le chiavi delle colonne
//     didascalia: "…",                  // <caption> (anche solo per i lettori di schermo: classe «solo-lettori»)
//     piede: [{ testo, colonne }],      // facoltativo: una riga di totali in <tfoot> (celle con colspan)
//     suOrdina: async (chiave, verso) => {…},   // facoltativo: ordina il server (verso «asc», «desc» o null) e poi la
//                                       // pagina chiama t.imposta(righe nuove); senza, ordina il browser
//     suRiga: (riga, tr, ev) => {…},    // facoltativo: clic, Invio o Spazio su una riga (le righe diventano focalizzabili)
//     ordine: { chiave, verso },        // facoltativo: ordinamento di partenza (es. dal collegamento)
//   });
//   contenitore.appendChild(t.elemento);    // <table class="tabella-ordinabile">
//   t.imposta(righe)                        // nuove righe (mantiene l'ordinamento scelto se ordina il browser)
//   t.ordina(chiave, verso)                 // ordina da programma; t.ordine → { chiave, verso } attuale
//   t.evidenzia(predicato)                  // classe «evidenziata» sulle righe per cui predicato(riga) è vero
//
// Clic sull'intestazione: crescente → decrescente → non ordinato (ordine di partenza delle righe). Le intestazioni sono
// pulsanti (tastiera: Tab, Invio, Spazio) e hanno aria-sort («ascending», «descending», «none»); l'icona mostra il verso.
// Confronto in italiano (localeCompare(…, "it"), con i numeri dentro i testi in ordine naturale), numeri come numeri,
// celle vuote sempre in fondo in tutti e due i versi.
(function (radice) {
  const VUOTO = (v) => v === null || v === undefined || v === "" || (typeof v === "number" && !Number.isFinite(v));
  const confrontaTesto = (a, b) => String(a).localeCompare(String(b), "it", { numeric: true, sensitivity: "base" });

  function confronto(col, verso) {
    const s = verso === "desc" ? -1 : 1;
    return (ra, rb) => {
      const a = ra[col.chiave], b = rb[col.chiave];
      const va = VUOTO(a), vb = VUOTO(b);
      if (va || vb) return va === vb ? 0 : va ? 1 : -1;            // vuoti in fondo, in tutti e due i versi
      if (col.tipo === "numero") return s * (Number(a) - Number(b));
      return s * confrontaTesto(a, b);
    };
  }

  function crea(opz) {
    const colonne = opz.colonne || [];
    let originali = (opz.righe || []).slice();
    let ordine = { chiave: null, verso: null };
    let evidenza = null;
    const tab = document.createElement("table");
    tab.className = "tabella-ordinabile" + (opz.classe ? ` ${opz.classe}` : "");
    if (opz.didascalia) {
      const cap = document.createElement("caption");
      cap.textContent = opz.didascalia;
      if (opz.didascaliaNascosta) cap.className = "solo-lettori";
      tab.appendChild(cap);
    }
    const thead = tab.createTHead(), trh = thead.insertRow();
    const intestazioni = colonne.map((c) => {
      const th = document.createElement("th");
      th.scope = "col";
      if (c.classe) th.className = c.classe;
      if (c.tipo === "numero") th.classList.add("num");
      if (c.ordinabile === false) { th.textContent = c.titolo; trh.appendChild(th); return th; }
      th.setAttribute("aria-sort", "none");
      const b = document.createElement("button");
      b.type = "button"; b.className = "ordina";
      const t = document.createElement("span"); t.textContent = c.titolo;
      const i = document.createElement("span"); i.className = "verso"; i.setAttribute("aria-hidden", "true");
      b.append(t, i);
      b.title = `Ordina per «${c.titolo}»`;
      b.addEventListener("click", () => {
        const verso = ordine.chiave !== c.chiave ? "asc" : ordine.verso === "asc" ? "desc" : ordine.verso === "desc" ? null : "asc";
        ordina(verso ? c.chiave : null, verso, true);
      });
      th.appendChild(b); trh.appendChild(th);
      return th;
    });
    const tbody = tab.createTBody();
    let tfoot = null;

    function segni() {
      colonne.forEach((c, k) => {
        const th = intestazioni[k];
        if (c.ordinabile === false) return;
        const v = ordine.chiave === c.chiave ? ordine.verso : null;
        th.setAttribute("aria-sort", v === "asc" ? "ascending" : v === "desc" ? "descending" : "none");
        th.querySelector(".verso").textContent = v === "asc" ? "▲" : v === "desc" ? "▼" : "↕";
      });
    }

    function disegna(righe) {
      tbody.textContent = "";
      const frammento = document.createDocumentFragment();
      righe.forEach((r) => {
        const tr = document.createElement("tr");
        colonne.forEach((c, k) => {
          const td = document.createElement(k === 0 && opz.primaIntestazione ? "th" : "td");
          if (k === 0 && opz.primaIntestazione) td.scope = "row";
          const v = r[c.chiave];
          const testo = c.formato ? c.formato(v, r) : VUOTO(v) ? "" : String(v);
          if (testo instanceof Node) td.appendChild(testo); else td.textContent = testo;
          if (c.classe) td.className = c.classe;
          if (c.tipo === "numero") td.classList.add("num");
          tr.appendChild(td);
        });
        if (opz.suRiga) {
          tr.tabIndex = 0; tr.classList.add("cliccabile");
          tr.addEventListener("click", (ev) => opz.suRiga(r, tr, ev));
          tr.addEventListener("keydown", (ev) => {
            if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); opz.suRiga(r, tr, ev); }
          });
        }
        if (evidenza && evidenza(r)) tr.classList.add("evidenziata");
        tr._riga = r;
        frammento.appendChild(tr);
      });
      tbody.appendChild(frammento);
    }

    function righeOrdinate() {
      if (opz.suOrdina || !ordine.chiave) return originali;
      const col = colonne.find((c) => c.chiave === ordine.chiave);
      return col ? originali.slice().sort(confronto(col, ordine.verso)) : originali;
    }

    async function ordina(chiave, verso, daClic = false) {
      ordine = { chiave: chiave && verso ? chiave : null, verso: chiave && verso ? verso : null };
      segni();
      if (opz.suOrdina && daClic) { await opz.suOrdina(ordine.chiave, ordine.verso); return; }
      disegna(righeOrdinate());
      if (opz.dopoOrdina && daClic) opz.dopoOrdina(ordine.chiave, ordine.verso);
    }

    function imposta(righe) {
      originali = (righe || []).slice();
      disegna(righeOrdinate());
    }

    function piede(celle) {
      if (tfoot) tfoot.remove();
      tfoot = null;
      if (!celle || !celle.length) return;
      tfoot = tab.createTFoot();
      const tr = tfoot.insertRow();
      celle.forEach((c) => {
        const td = document.createElement(c.intestazione ? "th" : "td");
        if (c.intestazione) td.scope = "row";
        td.textContent = c.testo || "";
        if (c.colonne > 1) td.colSpan = c.colonne;
        if (c.classe) td.className = c.classe;
        tr.appendChild(td);
      });
    }

    function evidenzia(pred) {
      evidenza = pred;
      tbody.querySelectorAll("tr").forEach((tr) => tr.classList.toggle("evidenziata", !!(pred && pred(tr._riga))));
    }

    if (opz.ordine && opz.ordine.chiave && colonne.some((c) => c.chiave === opz.ordine.chiave)) {
      ordine = { chiave: opz.ordine.chiave, verso: opz.ordine.verso === "desc" ? "desc" : "asc" };
    }
    segni();
    disegna(righeOrdinate());
    piede(opz.piede);
    return {
      elemento: tab, imposta, piede, evidenzia,
      ordina: (k, v) => ordina(k, v, false),
      get ordine() { return { ...ordine }; },
      get righe() { return originali.slice(); },
    };
  }

  const T = { crea, confronto };
  radice.EUGENIO_TABELLA_ORDINABILE = T;
  if (typeof module === "object" && module.exports) module.exports = T;
})(typeof globalThis !== "undefined" ? globalThis : this);
