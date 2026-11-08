// Lettura di un DB topografico con il lettore del sito (fase5-sito/sito/dbtr_lettore.js) in node, per i test di parità
// con il Python (test_dbtr_parita.py). Uso: node dbtr_node.js <cartella sito> <regione> <uscita.json> <file|cartella>…
"use strict";
const fs = require("fs");
const path = require("path");
const [sito, regione, uscita, ...ingressi] = process.argv.slice(2);
const lib = { fflate: require(path.join(sito, "lib/fflate/fflate.js")), proj4: require(path.join(sito, "lib/proj4/proj4.js")) };
const D = require(path.join(sito, "dbtr_lettore.js"));
const initSqlJs = require(path.join(sito, "lib/sql.js/sql-wasm.js"));

(async () => {
  lib.SQL = await initSqlJs({ locateFile: (f) => path.join(sito, "lib/sql.js", f) });
  const files = [];
  for (const p of ingressi) {
    const st = fs.statSync(p);
    if (st.isDirectory()) for (const n of fs.readdirSync(p)) files.push({ nome: n, dati: new Uint8Array(fs.readFileSync(path.join(p, n))) });
    else files.push({ nome: path.basename(p), dati: new Uint8Array(fs.readFileSync(p)) });
  }
  let out;
  try {
    const t0 = Date.now();
    const r = D.leggi(files, regione, lib);
    out = { features: r.features, sintesi: r.sintesi, ms: Date.now() - t0 };
  } catch (e) {
    out = { errore: String(e && e.message || e), tipo: e && e.constructor && e.constructor.name };
  }
  fs.writeFileSync(uscita, JSON.stringify(out));
})();
