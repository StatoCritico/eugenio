"use strict";
// Parità aria_ore.js ↔ aria/ore.py (14/11/2026): genera la serie sintetica di prova del sito (scelta_aria.serieProva, la
// stessa di ?prova=1, con una data di fine fissa), filtra i gruppi con gruppi_ore.js, calcola statistiche, classi, matrice e
// zona con aria_ore.js e scrive tutto in JSON su stdout (serie compresa). Casi dal file JSON del primo argomento.
const fs = require("fs"), path = require("path");
const SITO = path.resolve(__dirname, "..", "..", "fase5-sito", "sito");
globalThis.window = globalThis;
globalThis.location = { search: "" };
const P = require(path.join(SITO, "psicro.js"));
const G = require(path.join(SITO, "gruppi_ore.js"));
const A = require(path.join(SITO, "aria_ore.js"));
require(path.join(SITO, "scelta_aria.js"));
const C = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const pulisci = (o) => JSON.parse(JSON.stringify(o, (k, v) => (typeof v === "number" && !Number.isFinite(v) ? null : v)));
const s = window.EUGENIO_SCELTA_ARIA.serieProva(C.istat, C.anni, { fine: Date.parse(C.fine) });
const out = { serie: { inizio: s.inizio, n: s.n, p: s.p, t: Array.from(s.t, (v) => (v === v ? v : null)), ur: Array.from(s.ur, (v) => (v === v ? v : null)) }, gruppi: [] };
for (const g of C.gruppi) {
  const idx = G.filtra(s, g), i0 = G.inizioAnni(s, g.anni || 0);
  out.gruppi.push({ indici: Array.from(idx), i0, stat: A.statistiche(s.t, s.ur, s.p, idx, i0, s.n), classiT: A.classiT(s.t, s.ur, s.p, idx),
    classiX: A.classiX(s.t, s.ur, s.p, idx), matrice: A.matriceTX(s.t, s.ur, s.p, idx), zone: C.zone.map((z) => A.zona(s.t, s.ur, s.p, idx, z)) });
}
// tempi su 750.000 ore (serie ripetuta): filtro e statistiche
const n = 750000, t = new Float32Array(n), ur = new Float32Array(n);
for (let i = 0; i < n; i++) { t[i] = s.t[i % s.n]; ur[i] = s.ur[i % s.n]; }
const grande = { inizio: s.inizio, n, t, ur };
let a = performance.now();
const idx = G.filtra(grande, { da: "01/06", a: "30/09", oraDa: 8, oraA: 18, giorni: "feriali" });
out.msFiltro = performance.now() - a;
P.vettori(t, ur, s.p);
a = performance.now();
const tutte = G.filtra(grande, {});
A.statistiche(t, ur, s.p, tutte, 0, n); A.classiT(t, ur, s.p, tutte); A.classiX(t, ur, s.p, tutte); A.zona(t, ur, s.p, tutte, C.zone[0]);
out.msCalcolo = performance.now() - a;
out.nFiltro = idx.length;
process.stdout.write(JSON.stringify(pulisci(out)));
