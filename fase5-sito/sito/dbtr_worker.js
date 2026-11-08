"use strict";
// Web Worker della pagina «Aggiungi edifici (DB topografico)» (07/11/2026): legge il DB topografico dell'utente senza
// bloccare la pagina e senza mandarlo da nessuna parte (nessuna richiesta di rete, a parte le proprie librerie da questo
// sito). sql.js (WebAssembly, ~650 kB) si carica solo quando arriva un GeoPackage. Messaggi:
//   → {azione: "leggi", files: [{nome, dati: ArrayBuffer}], regione}   ← {tipo: "letto", features, sintesi} | {tipo: "errore", testo}
//   → {azione: "impacchetta", files}                                   ← {tipo: "pacchetto", dati: Uint8Array (zip)}
//   ← {tipo: "stato", testo} durante il lavoro
const V = self.location.search || "";
importScripts(`lib/fflate/fflate.js${V}`, `lib/proj4/proj4.js${V}`, `dbtr_lettore.js${V}`);
const D = self.EUGENIO_DBTR;
let SQL = null;

const stato = (testo) => self.postMessage({ tipo: "stato", testo });
function messaggioErrore(e) {
  if (e instanceof D.DbtrNonValido) return e.message;
  const t = String((e && e.message) || e || "");
  if (e instanceof RangeError || /memory|memoria|allocat|OOM|Aborted\(/i.test(t))
    return "memoria del browser esaurita: il file è troppo grande per questa pagina (prova con un comune più piccolo o proponilo all'archivio comune)";
  return `file non leggibile (${D.pulisci(t, 100) || "errore sconosciuto"})`;
}
async function sqlJs() {
  if (SQL) return SQL;
  stato("Carico il lettore dei GeoPackage (sql.js, una volta sola)…");
  importScripts(`lib/sql.js/sql-wasm.js${V}`);
  SQL = await self.initSqlJs({ locateFile: (f) => new URL(`lib/sql.js/${f}${V}`, self.location.href).href });
  return SQL;
}
const serveSql = (files) => files.some((f) => /\.(gpkg|zip)$/i.test(f.nome) || (() => {
  const u = new Uint8Array(f.dati, 0, Math.min(16, f.dati.byteLength));
  return u[0] === 0x53 && u[1] === 0x51 && u[2] === 0x4c;
})());

self.onmessage = async (ev) => {
  const m = ev.data || {};
  try {
    if (m.azione === "leggi") {
      const lib = { fflate: self.fflate, proj4: self.proj4, SQL: serveSql(m.files) ? await sqlJs() : null };
      const r = D.leggi(m.files.map((f) => ({ nome: f.nome, dati: new Uint8Array(f.dati) })), m.regione, lib, stato);
      self.postMessage({ tipo: "letto", features: r.features, sintesi: r.sintesi });
    } else if (m.azione === "impacchetta") {
      // parti di uno Shapefile scelte una per una (o una cartella) → un solo zip per la proposta all'archivio comune
      stato("Preparo lo zip da inviare…");
      const voci = {};
      for (const f of m.files) if (/\.(shp|shx|dbf|prj|cpg|xml)$/i.test(f.nome)) voci[f.nome.split(/[\\/]/).pop()] = new Uint8Array(f.dati);
      const z = self.fflate.zipSync(voci, { level: 6 });
      self.postMessage({ tipo: "pacchetto", dati: z }, [z.buffer]);
    }
  } catch (e) {
    self.postMessage({ tipo: "errore", testo: messaggioErrore(e) });
  }
};
