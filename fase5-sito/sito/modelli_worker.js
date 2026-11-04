"use strict";
// Web Worker della pagina «Importa DXF/IFC»: legge il file dell'utente senza bloccare la pagina e senza mandarlo da
// nessuna parte (il worker non fa richieste di rete, a parte le proprie librerie da questo sito). web-ifc (WebAssembly,
// ~7 MB) si carica solo quando arriva un IFC. Messaggi:
//   → {azione: "leggi", nome, dati: ArrayBuffer, unita}     ← {tipo: "letto", sintesi} | {tipo: "errore", testo}
//   → {azione: "posa", posa, edificio}                       ← {tipo: "modello", geojson} | {tipo: "errore", testo}
//   ← {tipo: "stato", testo} durante il lavoro
const V = self.location.search || "";
importScripts(`lib/dxf-parser/dxf-parser.js${V}`, `lib/clipper-lib/clipper.js${V}`, `lib/proj4/proj4.js${V}`, `modelli_import.js${V}`);
const M = self.EUGENIO_MODELLI;
const lib = { DxfParser: self.DxfParser, ClipperLib: self.ClipperLib, proj4: self.proj4, WebIFC: null };
let api = null, letto = null;

const stato = (testo) => self.postMessage({ tipo: "stato", testo });
function messaggioErrore(e) {
  if (e instanceof M.ModelloNonValido) return e.message;
  const t = String((e && e.message) || e || "");
  if (e instanceof RangeError || /memory|memoria|allocat|OOM|Aborted\(/i.test(t))
    return "memoria del browser esaurita: il modello è troppo grande per la pagina. Convertilo sul PC (istruzioni qui sotto)";
  return `file non leggibile (${M.pulisci(t, 80) || "errore sconosciuto"})`;
}

async function ifcApi() {
  if (api) return api;
  stato("Carico il lettore IFC (web-ifc, una volta sola)…");
  importScripts(`lib/web-ifc/web-ifc-api-iife.js${V}`);
  lib.WebIFC = self.WebIFC;
  const a = new self.WebIFC.IfcAPI();
  await a.Init((percorso) => new URL(`lib/web-ifc/${percorso}${V}`, self.location.href).href, true);   // un solo thread
  api = a;
  return api;
}

async function sha256(buf) {
  const h = await crypto.subtle.digest("SHA-256", buf);
  return Array.from(new Uint8Array(h), (b) => b.toString(16).padStart(2, "0")).join("");
}

async function leggi({ nome, dati, unita }) {
  const tipo = M.controllaFile(nome, dati.byteLength, new Uint8Array(dati, 0, Math.min(256, dati.byteLength)));
  const impronta = await sha256(dati);
  let r;
  if (tipo === "dxf") {
    stato("Leggo il DXF…");
    const testo = new TextDecoder("utf-8", { fatal: false }).decode(dati);
    r = M.leggiDxf(testo, lib, unita || null);
  } else {
    const a = await ifcApi();
    stato("Leggo l'IFC e ricavo la geometria…");
    r = M.leggiIfc(new Uint8Array(dati), lib, a);
  }
  letto = { r, tipo, nome: M.pulisci(nome, 120), impronta };
  // per la pianta della pagina: sagome dei corpi nelle coordinate del disegno (metri)
  const piante = r.corpi.map((c) => ({ sagoma: c.sagoma.map((q) => [q[0], q[1]]), tetto: c.tetto, gronda: c.gronda, colmo: c.colmo }));
  return { tipo, corpi: r.corpi.length, avvisi: r.avvisi, georef: r.georef, unita_m: r.unita_m, schema: r.schema || "", piante };
}

self.onmessage = async (ev) => {
  const m = ev.data || {};
  try {
    if (m.azione === "leggi") {
      letto = null;
      self.postMessage({ tipo: "letto", sintesi: await leggi(m) });
    } else if (m.azione === "posa") {
      if (!letto) throw new M.ModelloNonValido("prima carica un file");
      const posa = m.posa ? M.inMetri(m.posa, letto.r.unita_m) : letto.r.georef;
      const g = M.geojson(letto.r, posa, letto.tipo, letto.nome, letto.impronta, lib.proj4, m.edificio || "MODELLO");
      self.postMessage({ tipo: "modello", geojson: g });
    }
  } catch (e) {
    self.postMessage({ tipo: "errore", testo: messaggioErrore(e) });
  }
};
