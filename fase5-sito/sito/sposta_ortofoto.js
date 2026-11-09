"use strict";
// Spostamento manuale dell'ortofoto rispetto alla cartografia (08/11/2026, richiesta di Paolo): quattro frecce (dal 09/11/2026
// affiancate su una riga con lo stato e «Azzera»)
// sotto la mappa (Modelli 3D e pagine 3D unificate accanto a «Genera il 3D», Ortofoto accanto a «Scarica l'immagine»)
// spostano la foto di 1 m a nord, sud, ovest o est; «Azzera» la rimette al suo posto. Serve a compensare a occhio gli
// scarti di 1–5 m tra la foto e particelle, contorni e sagome (F.A.Q. #sfasamento): i vettori restano dove sono.
//
// Tecnica: il proxy delle ortofoto (servizio/ortofoto.py) accetta ?de=<m>&dn=<m> (interi, ±20) e chiede alla fonte WMS
// il riquadro della tessera spostato di quei metri sul terreno, nella proiezione delle tessere (EPSG:3857): spostamento
// esatto a ogni zoom, nessuna riproiezione dell'immagine. Qui si cambia solo l'indirizzo delle tessere della sorgente
// «ortofoto» (setTiles): la camera non si muove, 2D e 3D uguali. Fonti a tessere già pronte (Sentinel-2 cloudless,
// ortofoto dei siti in PMTiles): frecce spente con il motivo (MapLibre non sa spostare uno strato raster).
// Lo spostamento vale per la sessione (sessionStorage, per pagina e fonte) e si azzera cambiando fonte o con «Azzera».
// Decisione di Paolo (08/11/2026): frecce e «Azzera» attive solo con un'ortofoto spostabile accesa **e** almeno uno strato
// vettoriale acceso (particelle, contorni, edifici dell'archivio o OSM); altrimenti spente, con il motivo nel title dei
// pulsanti e del gruppo (Chrome non mostra sempre il title di un pulsante disattivato) e nel testo per i lettori di schermo.
//
//  const s = EUGENIO_SPOSTA.crea(contenitore, { pagina: "ortofoto", suCambio: (de, dn) => … })
//  s.fonte(f, { visibile, vettori })  fonte scelta (oggetto di /api/ortofoto/fonti) o null; visibile = false o
//                            vettori = false spengono le frecce (si richiama a ogni cambio di livelli o di fonte)
//  s.url(tessere)            indirizzo delle tessere con &de=…&dn=… (uguale se lo spostamento è nullo)
//  s.riga()                  «Ortofoto spostata manualmente di 2 m E, 1 m S rispetto alla cartografia» o ""
//  s.de, s.dn, s.sposta(de, dn), s.imposta(de, dn), s.azzera()
(function () {
  // ordine a schermo (09/11/2026): ← ↑ ↓ → affiancate su una riga
  const DIREZIONI = [
    { id: "o", freccia: "←", nome: "ovest", de: -1, dn: 0, tasto: "ArrowLeft" },
    { id: "n", freccia: "↑", nome: "nord", de: 0, dn: 1, tasto: "ArrowUp" },
    { id: "s", freccia: "↓", nome: "sud", de: 0, dn: -1, tasto: "ArrowDown" },
    { id: "e", freccia: "→", nome: "est", de: 1, dn: 0, tasto: "ArrowRight" },
  ];
  function h(tag, cls, t) { const e = document.createElement(tag); if (cls) e.className = cls; if (t !== undefined) e.textContent = t; return e; }
  function testo(de, dn) {
    const p = [];
    if (de) p.push(`${Math.abs(de)} m ${de > 0 ? "E" : "O"}`);
    if (dn) p.push(`${Math.abs(dn)} m ${dn > 0 ? "N" : "S"}`);
    return p.join(", ");
  }

  function crea(box, opz = {}) {
    const chiave = `eugenio-sposta-ortofoto:${opz.pagina || location.pathname}`;
    const st = { de: 0, dn: 0, fonte: null, max: 20, attiva: false, motivo: "", ripreso: false, tempo: null };
    const leggi = () => { try { return JSON.parse(sessionStorage.getItem(chiave) || "null"); } catch { return null; } };
    const scrivi = () => {
      try {
        if (st.fonte && (st.de || st.dn)) sessionStorage.setItem(chiave, JSON.stringify({ fonte: st.fonte.id, de: st.de, dn: st.dn }));
        else sessionStorage.removeItem(chiave);
      } catch { /* sessionStorage non disponibile: vale solo per questa pagina */ }
    };

    // ------------------------------------------------------------------ interfaccia
    const gruppo = h("div", "sposta-ortofoto");
    gruppo.setAttribute("role", "group"); gruppo.setAttribute("aria-label", "Spostamento dell'ortofoto rispetto alla cartografia");
    const croce = h("div", "croce");
    const pulsanti = {};
    for (const d of DIREZIONI) {
      const b = h("button", `freccia freccia-${d.id}`, d.freccia);
      b.type = "button"; b.dataset.direzione = d.id;
      const et = `Sposta l'ortofoto di 1 m verso ${d.nome} rispetto alla cartografia`;
      b.setAttribute("aria-label", et); b.title = et;
      b.addEventListener("click", () => sposta(d.de, d.dn));
      pulsanti[d.id] = b; croce.appendChild(b);
    }
    const mezzo = h("span", "passo", "1 m"); mezzo.setAttribute("aria-hidden", "true"); croce.appendChild(mezzo);   // dopo le quattro frecce
    const lato = h("div", "sposta-lato");
    const stato = h("span", "sposta-stato"); stato.setAttribute("role", "status"); stato.setAttribute("aria-live", "polite");
    stato.id = `sposta-stato-${Math.random().toString(36).slice(2, 8)}`;
    gruppo.setAttribute("aria-describedby", stato.id);
    const azzera = h("button", "bottone secondario piccolo sposta-azzera", "Azzera");
    azzera.type = "button"; azzera.title = "Rimetti l'ortofoto al suo posto (spostamento 0 m)";
    azzera.addEventListener("click", () => imposta(0, 0));
    lato.append(stato, azzera);
    gruppo.append(croce, lato);
    // tastiera: con il fuoco su una freccia le frecce della tastiera spostano (Invio e spazio premono il pulsante)
    croce.addEventListener("keydown", (e) => {
      const d = DIREZIONI.find((x) => x.tasto === e.key);
      if (!d || e.altKey || e.ctrlKey || e.metaKey) return;
      e.preventDefault();
      if (!st.attiva) return;
      sposta(d.de, d.dn);
      const b = pulsanti[d.id];
      if (!b.disabled) b.focus();
    });
    if (box) { box.innerHTML = ""; box.appendChild(gruppo); }

    function disegna() {
      const t = testo(st.de, st.dn);
      const conta = t && st.fonte && st.fonte.spostabile;
      stato.textContent = !st.attiva ? `${conta ? `Ortofoto spostata: ${t}. ` : ""}${st.motivo}` : t ? `Ortofoto spostata: ${t}` : "Ortofoto al suo posto";
      stato.classList.toggle("spostata", !!conta);
      stato.title = stato.textContent;
      for (const d of DIREZIONI) {
        const b = pulsanti[d.id], oltre = Math.abs(st.de + d.de) > st.max || Math.abs(st.dn + d.dn) > st.max;
        b.disabled = !st.attiva || oltre;
        b.title = !st.attiva ? st.motivo : oltre ? `Spostamento massimo: ${st.max} m` : b.getAttribute("aria-label");
        if (st.attiva) b.removeAttribute("aria-describedby"); else b.setAttribute("aria-describedby", stato.id);
      }
      azzera.disabled = !st.attiva || !(st.de || st.dn);
      azzera.title = !st.attiva ? st.motivo : st.de || st.dn ? "Rimetti l'ortofoto al suo posto (spostamento 0 m)" : "L'ortofoto è già al suo posto";
      // title anche sul gruppo: sopra un pulsante disattivato alcuni browser mostrano quello del contenitore
      gruppo.title = st.attiva ? "Frecce: sposta l'ortofoto di 1 m rispetto alla cartografia (particelle, contorni, edifici)" : st.motivo;
      gruppo.classList.toggle("spenta", !st.attiva);
    }
    function avvisa() {
      clearTimeout(st.tempo);
      // più clic di fila: le tessere si richiedono una volta sola, dopo l'ultimo clic
      st.tempo = setTimeout(() => { if (opz.suCambio) opz.suCambio(st.de, st.dn); }, opz.attesa === undefined ? 350 : opz.attesa);
    }
    function imposta(de, dn, silenzioso = false) {
      const lim = (v) => Math.max(-st.max, Math.min(st.max, Math.round(Number(v) || 0)));
      const nde = lim(de), ndn = lim(dn), cambiato = nde !== st.de || ndn !== st.dn;
      st.de = nde; st.dn = ndn;
      scrivi(); disegna();
      if (cambiato && !silenzioso) avvisa();
      return cambiato;
    }
    function sposta(de, dn) { if (st.attiva) imposta(st.de + de, st.dn + dn); }

    // fonte scelta dalla pagina: cambiare fonte azzera; alla prima fonte della pagina si riprende lo spostamento della
    // sessione se era per la stessa fonte
    function fonte(f, o = {}) {
      const vecchia = st.fonte;
      st.fonte = f || null;
      if (!f || !vecchia || vecchia.id !== f.id) {
        let de = 0, dn = 0;
        if (!st.ripreso && f) {
          const s = leggi();
          if (s && s.fonte === f.id) { de = s.de; dn = s.dn; }
        }
        if (f) st.ripreso = true;
        st.max = f && f.spostamento_max ? f.spostamento_max : 20;
        imposta(de, dn, true);
      }
      st.motivo = !f ? "Accendi un'ortofoto e almeno uno strato vettoriale (particelle o contorni) per allineare la foto alla cartografia."
        : f.pmtiles ? `«${f.nome}» è un'ortofoto già pronta in tessere: non si può spostare.`
        : !f.spostabile ? `«${f.nome}» ha tessere già pronte${/sentinel/i.test(f.nome) ? " e pixel di 10 m" : ""}: lo spostamento di 1 m non si applica.`
        : o.visibile === false ? "Ortofoto spenta nei livelli. Accendi un'ortofoto e almeno uno strato vettoriale (particelle o contorni) per allineare la foto alla cartografia."
        : o.vettori === false ? "Accendi un'ortofoto e almeno uno strato vettoriale (particelle o contorni) per allineare la foto alla cartografia."
        : "";
      st.attiva = !st.motivo;
      disegna();
    }
    function url(tessere) {
      if (!st.fonte || !st.fonte.spostabile || !(st.de || st.dn)) return tessere;
      return `${tessere}${tessere.includes("?") ? "&" : "?"}de=${st.de}&dn=${st.dn}`;
    }
    function riga() {
      const t = st.fonte && st.fonte.spostabile ? testo(st.de, st.dn) : "";
      return t ? `Ortofoto spostata manualmente di ${t} rispetto alla cartografia.` : "";
    }
    function nascondi(si) { gruppo.hidden = !!si; }
    disegna();
    const api = { fonte, url, riga, sposta, imposta, azzera: () => imposta(0, 0), nascondi, elemento: gruppo };
    Object.defineProperty(api, "de", { get: () => (st.fonte && st.fonte.spostabile ? st.de : 0) });
    Object.defineProperty(api, "dn", { get: () => (st.fonte && st.fonte.spostabile ? st.dn : 0) });
    Object.defineProperty(api, "attiva", { get: () => st.attiva });
    return api;
  }

  window.EUGENIO_SPOSTA = { crea, testo };
})();
