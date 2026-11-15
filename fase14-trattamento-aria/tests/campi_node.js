"use strict";
// Campi dell'ora locale di gruppi_ore.js per una serie lunga (prova di regressione del 14/11/2026: giorno della
// settimana prima del 1970, ora legale storica italiana). Argomenti: inizio (ISO UTC), n ore, gruppi in JSON.
const path = require("path");
const G = require(path.join(__dirname, "..", "..", "fase5-sito", "sito", "gruppi_ore.js"));
const [inizio, nTesto, gruppiTesto] = process.argv.slice(2);
const n = +nTesto;
const t = new Float32Array(n).fill(10), ur = new Float32Array(n).fill(50);
const serie = { inizio: Date.parse(inizio), n, t, ur };
const c = G.campiOrari(serie);
const out = { ora: Array.from(c.ora), dow: Array.from(c.dow), giorno: Array.from(c.giorno), mese: Array.from(c.mese), anno: Array.from(c.anno) };
out.gruppi = JSON.parse(gruppiTesto || "[]").map((g) => Array.from(G.filtra(serie, g)).length);
process.stdout.write(JSON.stringify(out));
