"use strict";
// Pioggia misurata sulle mappe MapLibre (22/11/2026): parte comune a Clima e meteo › «Dati pluviometrici»
// (pluviometria.js) e Statistiche › «Stato della rete elettrica» (rete_elettrica.js, casella «Pioggia misurata»).
//
// Dati: solo il «Merging» del Dipartimento della Protezione Civile (radar corretto con i pluviometri, CUM3/6/12/24), un
// frame ogni 30 minuti; fini statistici, non di allerta (decisione di Paolo del 22/11/2026). Le immagini le prepara il
// worker (fase4-server/servizio/radar.py) in dati/radar/<prodotto>/<AAAAMMGGTHHMMZ>.png, riproiettate su una griglia fissa
// in Web Mercator: qui si mettono sulla mappa come sorgente «image» con i quattro angoli di dati/radar/indice.json.
// Licenza CC BY-SA 4.0 (Dipartimento della Protezione Civile): attribuzione sulla mappa, sotto la mappa e nei file.
//
//  const G = EUGENIO_PIOGGIA
//  await G.indice()                 dati/radar/indice.json (rilegge dopo 5 minuti)
//  G.strato(mappa, { id, prima })   sorgente e strato raster (vuoti); → { mostra(prodotto, nome), nascondi(), visibile(sì/no) }
//                                   l'attribuzione va nella legenda o nel controllo della mappa (customAttribution)
//  G.precarica(prodotto, nomi)      scarica in anticipo le immagini dell'animazione
//  G.legenda(dove, indice)          scala dei colori in mm e tratteggio «nessuna misura»
//  G.data(nome)                     "20261122T0500Z" → Date; G.nome(Date) → "20261122T0500Z"
//  G.testoFrame(prodotto, nome)     «pioggia delle 3 ore fino alle 06:00 di dom 22/11»
//  G.ATTRIBUZIONE, G.LICENZA, G.URL_DPC
(function () {
  const BASE = "dati/radar/";
  const VUOTA = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==";
  const ATTRIBUZIONE = "Pioggia: Dipartimento della Protezione Civile, «Merging» radar-pluviometri (CC BY-SA 4.0), elaborazione EuGEnio";
  const LICENZA = "CC BY-SA 4.0";
  const URL_DPC = "https://radar.protezionecivile.gov.it/";
  const ORE = { CUM3: 3, CUM6: 6, CUM12: 12, CUM24: 24 };
  let cache = null, letto = 0;
  const precaricate = new Map();

  async function indice(forza = false) {
    if (!forza && cache && Date.now() - letto < 5 * 60 * 1000) return cache;
    const r = await fetch(`${BASE}indice.json`, { cache: "no-cache" });
    if (!r.ok || !/json/.test(r.headers.get("Content-Type") || "json")) throw new Error(`indice dei dati pluviometrici: ${r.status}`);
    cache = await r.json(); letto = Date.now();
    return cache;
  }
  const url = (p, n) => `${BASE}${p}/${n}.png`;
  function data(n) {
    const m = /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})Z$/.exec(n || "");
    return m ? new Date(Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5])) : null;
  }
  function nome(d) {
    const z = (x) => String(x).padStart(2, "0");
    return `${d.getUTCFullYear()}${z(d.getUTCMonth() + 1)}${z(d.getUTCDate())}T${z(d.getUTCHours())}${z(d.getUTCMinutes())}Z`;
  }
  const FMT = new Intl.DateTimeFormat("it-IT", { timeZone: "Europe/Rome", weekday: "short", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  function oraIt(d) {
    const p = Object.fromEntries(FMT.formatToParts(d).map((x) => [x.type, x.value]));
    return `${p.hour}:${p.minute} di ${p.weekday} ${p.day}/${p.month}`;
  }
  function testoFrame(p, n) {
    const d = data(n), h = ORE[p];
    if (!d) return "";
    return `pioggia ${h === 24 ? "delle 24 ore" : `delle ${h} ore`} fino alle ${oraIt(d)}`;
  }
  function precarica(p, nomi) {
    for (const n of nomi) {
      const u = url(p, n);
      if (precaricate.has(u)) continue;
      const i = new Image(); i.decoding = "async"; i.src = u;
      precaricate.set(u, i);
      if (precaricate.size > 400) precaricate.delete(precaricate.keys().next().value);
    }
  }

  function strato(m, opz = {}) {
    const id = opz.id || "pioggia";
    let angoli = null, attuale = "", visibile = true;
    const prima = opz.prima && m.getLayer(opz.prima) ? opz.prima : undefined;
    const pronto = indice().then((ind) => {
      angoli = ind.griglia.angoli;
      m.addSource(id, { type: "image", url: VUOTA, coordinates: angoli });     // (le sorgenti «image» non hanno attribution)
      m.addLayer({ id, type: "raster", source: id, paint: { "raster-opacity": opz.opacita ?? 0.85, "raster-fade-duration": 0, "raster-resampling": "nearest" },
        layout: { visibility: "visible" } }, prima);
      return ind;
    });
    return {
      pronto,
      id,
      async mostra(p, n) {
        await pronto;
        const u = n ? url(p, n) : VUOTA;
        if (u === attuale) return;
        attuale = u;
        const s = m.getSource(id);
        if (s) s.updateImage({ url: u, coordinates: angoli });
      },
      async nascondi() { await this.mostra(null, null); },
      visibile(si) {
        visibile = !!si;
        pronto.then(() => { if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", visibile ? "visible" : "none"); });
      },
      get attuale() { return attuale; },
    };
  }

  function legenda(dove, ind, { titolo = "Pioggia caduta (mm)" } = {}) {
    if (!dove || !ind || !ind.scala || !ind.scala.mm) return;
    const box = document.createElement("span"); box.className = "legenda-pioggia";
    const t = document.createElement("span"); t.className = "legenda-pioggia-titolo"; t.textContent = `${titolo}:`;
    box.appendChild(t);
    const { soglie, colori } = ind.scala.mm;
    soglie.forEach((s, i) => {
      const v = document.createElement("span"); v.className = "legenda-pioggia-classe";
      const c = document.createElement("i"); c.style.background = colori[i];
      v.append(c, i === soglie.length - 1 ? `≥ ${s}` : `${String(s).replace(".", ",")}`);
      v.title = i === soglie.length - 1 ? `${s} mm e più` : `da ${s} a ${soglie[i + 1]} mm`;
      box.appendChild(v);
    });
    const n = document.createElement("span"); n.className = "legenda-pioggia-classe legenda-pioggia-mancante";
    const c = document.createElement("i"); c.className = "tratteggio";
    n.append(c, (ind.mancante && ind.mancante.testo) || "nessuna misura");
    box.appendChild(n);
    dove.appendChild(box);
  }

  window.EUGENIO_PIOGGIA = { indice, strato, precarica, legenda, data, nome, oraIt, testoFrame, url, ORE, ATTRIBUZIONE, LICENZA, URL_DPC };
})();
