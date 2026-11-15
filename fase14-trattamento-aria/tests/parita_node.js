"use strict";
// Parità psicro.js / gruppi_ore.js ↔ aria/psicro.py (14/11/2026): legge i casi da un file JSON (primo argomento), li
// calcola con i moduli del sito e scrive i risultati in JSON su stdout. Lo usa tests/test_parita_js.py.
const fs = require("fs"), path = require("path");
const SITO = path.resolve(__dirname, "..", "..", "fase5-sito", "sito");
const P = require(path.join(SITO, "psicro.js"));
const G = require(path.join(SITO, "gruppi_ore.js"));
const C = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const num = (v) => (Number.isFinite(v) ? v : null);
const pulisci = (o) => JSON.parse(JSON.stringify(o, (k, v) => (typeof v === "number" && !Number.isFinite(v) ? null : v)));
const out = {};
out.stati = C.stati.map(([t, ur, p]) => { const s = P.stato(t, { ur }, p); return [s.x, s.h, s.v, s.tdew, s.twb, s.ur, s.rho]; });
out.sequenze = C.sequenze.map((o) => {
  const s = P.sequenza(o);
  return { mtot: s.mtot, immissione: [s.immissione.t, s.immissione.x], righe: s.righe.map((r) => [r.t, r.x, r.Qt, r.Ql, r.Qs, r.acqua, r.nota]),
    riepilogo: s.riepilogo, verifiche: s.verifiche, raggiungibile: s.raggiungibile, esito: s.esito, R: s.R };
});
const t = Float32Array.from(C.serie.t.map((v) => (v === null ? NaN : v))), ur = Float32Array.from(C.serie.ur.map((v) => (v === null ? NaN : v)));
const V = P.vettori(t, ur, C.serie.p);
out.vettori = { x: Array.from(V.x, num), h: Array.from(V.h, num), twb: Array.from(V.twb, num) };
out.progetto = C.livelli.map((L) => { const c = P.condizioniProgetto(t, ur, C.serie.p, L); delete c.metodo; for (const k of Object.keys(c)) if (c[k] && c[k].stato) delete c[k].stato; return c; });
const serie = { inizio: C.serie.inizio, n: t.length, t, ur };
const campi = G.campiOrari(serie);
out.campi = { anno: Array.from(campi.anno), mese: Array.from(campi.mese), giorno: Array.from(campi.giorno), ora: Array.from(campi.ora), dow: Array.from(campi.dow) };
out.gruppi = C.gruppi.map((g) => ({ indici: Array.from(G.filtra(serie, g)), inizio: G.inizioAnni(serie, g.anni || 0) }));
process.stdout.write(JSON.stringify(pulisci(out)));
