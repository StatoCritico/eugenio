"use strict";
// inizioAnni di gruppi_ore.js per serie che finiscono in date date (prova del 29/02, 14/11/2026). Argomento: JSON
// [[inizio ISO, n ore, anni], …] → indici.
const path = require("path");
const G = require(path.join(__dirname, "..", "..", "fase5-sito", "sito", "gruppi_ore.js"));
const casi = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(casi.map(([ini, n, a]) => G.inizioAnni({ inizio: Date.parse(ini), n, t: { length: n } }, a))));
