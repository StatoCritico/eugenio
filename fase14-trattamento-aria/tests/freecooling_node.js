"use strict";
// Parità aria_freecooling.js ↔ aria/freecooling.py (14/11/2026): legge i casi (JSON, primo argomento), calcola con il sito
// (psicro.js, gruppi_ore.js, aria_freecooling.js in node) e scrive su stdout x e h della serie, gli array ora per ora e i
// riassunti dei gruppi per ogni insieme di opzioni. Lo usa tests/test_freecooling.py.
const fs = require("fs"), path = require("path");
const SITO = path.resolve(__dirname, "..", "..", "fase5-sito", "sito");
const P = require(path.join(SITO, "psicro.js"));
const G = require(path.join(SITO, "gruppi_ore.js"));
const F = require(path.join(SITO, "aria_freecooling.js"));
const C = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const num = (v) => (Number.isFinite(v) ? v : null);
const t = Float32Array.from(C.serie.t.map((v) => (v === null ? NaN : v))), ur = Float32Array.from(C.serie.ur.map((v) => (v === null ? NaN : v)));
const p = C.serie.p, V = P.vettori(t, ur, p);
const serie = { inizio: C.serie.inizio, n: t.length, t, ur };
const campi = G.campiOrari(serie);
const indici = C.gruppi.map((g) => G.filtra(serie, g));
const out = { x: Array.from(V.x, num), h: Array.from(V.h, num), mese: Array.from(campi.mese), indici: indici.map((a) => Array.from(a)),
  anni: C.gruppi.map((g) => (g.anni ? Math.min(g.anni, G.anniSerie(serie)) : G.anniSerie(serie))), casi: [] };
for (const o of C.opzioni) {
  const R = F.calcola(t, V.x, V.h, p, o);
  out.casi.push({ opzioni: R.opzioni, regime: Array.from(R.regime), bandiere: Array.from(R.bandiere), fcT: Array.from(R.fcT), fcH: Array.from(R.fcH),
    rec: Array.from(R.rec), perso: Array.from(R.perso), q0: Array.from(R.q0), pVent: R.pVent,
    riassunti: indici.map((ix, k) => F.riassumi(R, ix, out.anni[k], campi.mese)) });
}
out.ore = C.ore.map(([tt, u, o]) => F.unOra(tt, u, p, o));
process.stdout.write(JSON.stringify(out, (k, v) => (typeof v === "number" && !Number.isFinite(v) ? null : v)));
