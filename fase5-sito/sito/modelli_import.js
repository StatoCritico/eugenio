/* EuGEnio – modelli DXF e IFC dell'utente letti nel browser (pagina «Importa DXF/IFC», Fase C, § 5).
 *
 * Stessa logica di fase10-edifici3d/edifici3d/importa.py (comando `importa-modello`), riscritta in JavaScript: stessi
 * controlli, stessi tetti sul file, stessa regola dei tetti e dei corpi, stesso file in uscita (GeoJSON WGS84
 * «eugenio-modello-1») che la pagina Modelli 3D apre senza mandarlo al server. Le differenze sono solo nei lettori:
 *   - DXF con dxf-parser (MIT) invece di ezdxf: solo DXF di testo (ASCII), non quelli binari;
 *   - IFC con web-ifc (MPL-2.0, WebAssembly) invece di IfcOpenShell;
 *   - unioni e margini dei poligoni con Clipper (clipper-lib, Boost Software License) invece di shapely/GEOS;
 *   - sistemi di riferimento con proj4js (MIT) invece di pyproj, con le definizioni dei sistemi italiani qui sotto.
 * Gira in un Web Worker (modelli_worker.js) e, per i test di parità, in node. Le librerie arrivano come argomenti
 * (`lib`), così questo file non carica niente da solo.
 */
(function (radice, fabbrica) {
  if (typeof module === "object" && module.exports) module.exports = fabbrica();
  else radice.EUGENIO_MODELLI = fabbrica();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // stessi valori di importa.py; il browser ha in più la soglia oltre la quale si consiglia il PC
  const LIMITI = { MAX_MB: 50, CONSIGLIO_MB: 30, MAX_ENTITA: 200000, MAX_PROFONDITA: 8, MAX_TRIANGOLI: 2000000,
    MAX_CORPI: 500, ALTEZZA_MAX: 300, COORD_MAX: 1e7, TEMPO_S: 180, MEMORIA_IFC_MB: 1024, ESTENSIONE_MAX_M: 50000 };
  const LICENZA = "dati dell'utente";
  const FORMATO = "eugenio-modello-1";
  const UNITA_DXF = { 1: 0.0254, 2: 0.3048, 4: 0.001, 5: 0.01, 6: 1.0, 7: 1000.0, 14: 0.1 };   // $INSUNITS → metri

  // sistemi di riferimento che la pagina conosce (definizioni di PROJ, come pyproj; Gauss-Boaga con i 7 parametri
  // della trasformazione Roma 40 → WGS84 che pyproj usa senza griglie). Assi sempre est, nord (come always_xy).
  const SISTEMI = {
    "EPSG:7791": ["RDN2008 / UTM 32N", "+proj=utm +zone=32 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs"],
    "EPSG:7792": ["RDN2008 / UTM 33N", "+proj=utm +zone=33 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs"],
    "EPSG:6707": ["RDN2008 / UTM 32N (N-E)", "+proj=utm +zone=32 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs"],
    "EPSG:6708": ["RDN2008 / UTM 33N (N-E)", "+proj=utm +zone=33 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs"],
    "EPSG:6875": ["RDN2008 / Italy zone (N-E)", "+proj=tmerc +lat_0=0 +lon_0=12 +k=0.9985 +x_0=7000000 +y_0=0 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs"],
    "EPSG:25832": ["ETRS89 / UTM 32N", "+proj=utm +zone=32 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs"],
    "EPSG:25833": ["ETRS89 / UTM 33N", "+proj=utm +zone=33 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs"],
    "EPSG:3064": ["IGM95 / UTM 32N", "+proj=utm +zone=32 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs"],
    "EPSG:3065": ["IGM95 / UTM 33N", "+proj=utm +zone=33 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs"],
    "EPSG:32632": ["WGS 84 / UTM 32N", "+proj=utm +zone=32 +datum=WGS84 +units=m +no_defs"],
    "EPSG:32633": ["WGS 84 / UTM 33N", "+proj=utm +zone=33 +datum=WGS84 +units=m +no_defs"],
    "EPSG:3003": ["Monte Mario / Gauss-Boaga fuso Ovest", "+proj=tmerc +lat_0=0 +lon_0=9 +k=0.9996 +x_0=1500000 +y_0=0 +ellps=intl +towgs84=-104.1,-49.1,-9.9,0.971,-2.917,0.714,-11.68 +units=m +no_defs"],
    "EPSG:3004": ["Monte Mario / Gauss-Boaga fuso Est", "+proj=tmerc +lat_0=0 +lon_0=15 +k=0.9996 +x_0=2520000 +y_0=0 +ellps=intl +towgs84=-104.1,-49.1,-9.9,0.971,-2.917,0.714,-11.68 +units=m +no_defs"],
  };

  class ModelloNonValido extends Error {}
  const err = (t) => new ModelloNonValido(t);

  function pulisci(t, n = 80) {
    t = String(t == null ? "" : t).replace(/[\x00-\x1f\x7f<>]/g, " ");
    return t.replace(/\s+/g, " ").trim().slice(0, n);
  }

  // ============================================================================================ controlli sul file
  function controllaFile(nome, dimensione, testa) {
    const mb = dimensione / 1024 / 1024;
    if (!dimensione) throw err("il file è vuoto");
    if (mb > LIMITI.MAX_MB) throw err(`file di ${Math.round(mb)} MB: nel browser al massimo ${LIMITI.MAX_MB} MB. Convertilo sul PC (istruzioni nella pagina)`);
    const est = (String(nome).match(/\.[^.]*$/) || [""])[0].toLowerCase();
    const testo = new TextDecoder("latin1").decode(testa.slice(0, 256));
    const t = testo.replace(/^﻿/, "").replace(/^ï»¿/, "").replace(/^[ \r\n\t]+/, "");
    if (est === ".ifc") {
      if (!t.startsWith("ISO-10303-21")) throw err("non è un IFC in formato STEP (ISO-10303-21); IFC compressi (.ifczip) e ifcXML non sono accettati");
      return "ifc";
    }
    if (est === ".dxf") {
      if (testo.startsWith("AutoCAD Binary DXF")) throw err("DXF binario: nel browser si leggono solo i DXF di testo (ASCII). Salvalo come DXF ASCII dal CAD o convertilo sul PC");
      if (!/^0\s*\r?\n\s*SECTION/.test(t) && !/^999\s*\r?\n/.test(t)) throw err("non sembra un DXF (manca la sezione iniziale)");
      return "dxf";
    }
    throw err("formato non gestito: servono .dxf o .ifc (per il DWG: convertirlo prima in DXF)");
  }

  // ============================================================================================ geometria piana
  // Poligoni come { esterno: [[x,y]…], buchi: [[[x,y]…]…] }, anelli aperti (senza punto di chiusura).
  const SCALA = 1e4;                    // Clipper lavora con interi: 0,1 mm
  function areaAnello(r) { let a = 0; for (let i = 0, j = r.length - 1; i < r.length; j = i++) a += (r[j][0] + r[i][0]) * (r[j][1] - r[i][1]); return -a / 2; }
  const areaPoli = (p) => Math.abs(areaAnello(p.esterno)) - p.buchi.reduce((s, b) => s + Math.abs(areaAnello(b)), 0);
  const areaInsieme = (ps) => ps.reduce((s, p) => s + areaPoli(p), 0);

  function geometria(C) {
    const aInt = (r) => r.map((q) => ({ X: Math.round(q[0] * SCALA), Y: Math.round(q[1] * SCALA) }));
    const daInt = (r) => r.map((q) => [q.X / SCALA, q.Y / SCALA]);
    const percorsi = (ps) => { const o = []; for (const p of ps) { o.push(aInt(p.esterno)); for (const b of p.buchi) o.push(aInt(b)); } return o; };
    function insieme(paths) {           // percorsi interi → poligoni con buchi (unione con riempimento non nullo)
      const c = new C.Clipper(); const albero = new C.PolyTree();
      c.AddPaths(paths, C.PolyType.ptSubject, true);
      c.Execute(C.ClipType.ctUnion, albero, C.PolyFillType.pftNonZero, C.PolyFillType.pftNonZero);
      return C.JS.PolyTreeToExPolygons(albero).map((e) => ({ esterno: daInt(e.outer), buchi: (e.holes || []).map(daInt) }))
        .filter((p) => p.esterno.length >= 3);
    }
    function unione(anelli) { return insieme(anelli.map(aInt)); }
    function unionePoli(ps) { return insieme(percorsi(ps)); }
    function margine(ps, d) {           // come buffer(d) di shapely; giunti ad angolo (non arrotondati): così
      if (!ps.length) return [];        // margine(+d) e poi margine(−d) restituiscono gli spigoli esatti, come GEOS
      const co = new C.ClipperOffset(10, 0.002 * SCALA);
      co.AddPaths(percorsi(ps), C.JoinType.jtMiter, C.EndType.etClosedPolygon);
      const out = new C.Paths(); co.Execute(out, d * SCALA);
      return insieme(out);
    }
    function interseca(a, b) {          // area dell'intersezione
      const c = new C.Clipper(); const out = new C.Paths();
      c.AddPaths(percorsi(a), C.PolyType.ptSubject, true); c.AddPaths(percorsi(b), C.PolyType.ptClip, true);
      c.Execute(C.ClipType.ctIntersection, out, C.PolyFillType.pftNonZero, C.PolyFillType.pftNonZero);
      return out.reduce((s, r) => s + Math.abs(areaAnello(daInt(r))), 0);
    }
    function semplifica(ps, tol) {      // Douglas-Peucker su ogni anello (come simplify(tol) di shapely)
      const dp = (r) => {
        const chiuso = r.concat([r[0]]);
        const tieni = new Uint8Array(chiuso.length); tieni[0] = tieni[chiuso.length - 1] = 1;
        const pila = [[0, chiuso.length - 1]];
        while (pila.length) {
          const [a, b] = pila.pop(); let dm = -1, im = -1;
          const [ax, ay] = chiuso[a], [bx, by] = chiuso[b], L = Math.hypot(bx - ax, by - ay);
          for (let i = a + 1; i < b; i++) {
            const [px, py] = chiuso[i];
            const d = L > 0 ? Math.abs((bx - ax) * (ay - py) - (ax - px) * (by - ay)) / L : Math.hypot(px - ax, py - ay);
            if (d > dm) { dm = d; im = i; }
          }
          if (im > 0 && dm > tol) { tieni[im] = 1; pila.push([a, im], [im, b]); }
        }
        const o = chiuso.filter((_, i) => tieni[i]); o.pop();
        return o;
      };
      const out = [];
      for (const p of ps) {
        // l'anello chiuso parte dal primo punto: se il primo punto è su un lato dritto si toglie anche lui
        let e = dp(p.esterno);
        if (e.length < 3) continue;
        const buchi = p.buchi.map(dp).filter((b) => b.length >= 3 && Math.abs(areaAnello(b)) > 0);
        out.push({ esterno: e, buchi });
      }
      return out.filter((p) => areaPoli(p) > 0);
    }
    function ripara(anello) {           // come buffer(0) di un poligono non valido: un solo poligono o nulla
      const ps = unione([anello]);
      return ps.length === 1 ? ps[0] : null;
    }
    return { unione, unionePoli, margine, interseca, semplifica, ripara };
  }

  const maggiore = (ps) => ps.reduce((m, p) => (!m || areaPoli(p) > areaPoli(m) ? p : m), null);
  const limiti2 = (ps) => {
    let a = [Infinity, Infinity, -Infinity, -Infinity];
    for (const p of ps) for (const q of p.esterno) { a = [Math.min(a[0], q[0]), Math.min(a[1], q[1]), Math.max(a[2], q[0]), Math.max(a[3], q[1])]; }
    return a;
  };
  const chiudi = (r) => r.concat([r[0].slice()]);

  // ============================================================================================ tetti e corpi dai triangoli
  /** Triangoli (Float64Array n×9, metri, coordinate del disegno) → corpi con falde: tetti = facce rivolte in alto che
   * sono la superficie più alta nel loro punto; raggruppate per piano → falde; falde a contatto con la stessa gronda →
   * un corpo (come corpi_da_triangoli di importa.py). */
  function corpiDaTriangoli(T, C, tollAngolo = 5.0, tollDistanza = 0.3) {
    const n0 = T.length / 9;
    if (!n0) return [];
    // si lavora vicino all'origine (Clipper con interi), poi si rimette lo spostamento
    let ox = Infinity, oy = Infinity, mx = -Infinity, my = -Infinity, zmin = Infinity;
    for (let i = 0; i < T.length; i += 3) { ox = Math.min(ox, T[i]); oy = Math.min(oy, T[i + 1]); mx = Math.max(mx, T[i]); my = Math.max(my, T[i + 1]); }
    if (mx - ox > LIMITI.ESTENSIONE_MAX_M || my - oy > LIMITI.ESTENSIONE_MAX_M) throw err(`modello esteso oltre ${LIMITI.ESTENSIONE_MAX_M / 1000} km: controlla le unità del disegno`);
    const G = geometria(C);
    const t = new Float64Array(T.length);
    for (let i = 0; i < T.length; i += 3) { t[i] = T[i] - ox; t[i + 1] = T[i + 1] - oy; t[i + 2] = T[i + 2]; }
    const N = new Float64Array(n0 * 3), A3 = new Float64Array(n0), ok = new Uint8Array(n0);
    for (let k = 0; k < n0; k++) {
      const b = k * 9;
      const ux = t[b + 3] - t[b], uy = t[b + 4] - t[b + 1], uz = t[b + 5] - t[b + 2];
      const vx = t[b + 6] - t[b], vy = t[b + 7] - t[b + 1], vz = t[b + 8] - t[b + 2];
      const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx, L = Math.hypot(nx, ny, nz);
      A3[k] = L / 2;
      if (A3[k] > 1e-4) { ok[k] = 1; N[k * 3] = nx / L; N[k * 3 + 1] = ny / L; N[k * 3 + 2] = nz / L; }
      if (ok[k]) zmin = Math.min(zmin, t[b + 2], t[b + 5], t[b + 8]);
    }
    const zmaxT = (k) => Math.max(t[k * 9 + 2], t[k * 9 + 5], t[k * 9 + 8]);
    // normali verso l'alto (i modelli non sempre le hanno coerenti)
    const cand = [];
    for (let k = 0; k < n0; k++) {
      if (!ok[k]) continue;
      const nz = N[k * 3 + 2], su = nz > 0.15, giu = nz < -0.15;
      if (giu) { N[k * 3] *= -1; N[k * 3 + 1] *= -1; N[k * 3 + 2] *= -1; }
      if ((su || giu) && zmaxT(k) > zmin + 1.0) {
        const b = k * 9;
        const a2 = Math.abs((t[b + 3] - t[b]) * (t[b + 7] - t[b + 1]) - (t[b + 6] - t[b]) * (t[b + 4] - t[b + 1])) / 2;
        if (a2 > 1e-3) cand.push(k);
      }
    }
    if (!cand.length) return [];
    // indice a griglia dei riquadri dei triangoli candidati
    const lato = Math.max(1, Math.sqrt(((mx - ox) * (my - oy) || 1) / Math.max(1, cand.length)) * 2);
    const griglia = new Map();
    const chiave = (i, j) => i * 1000003 + j;
    const rq = cand.map((k) => {
      const b = k * 9;
      return [Math.min(t[b], t[b + 3], t[b + 6]), Math.min(t[b + 1], t[b + 4], t[b + 7]), Math.max(t[b], t[b + 3], t[b + 6]), Math.max(t[b + 1], t[b + 4], t[b + 7])];
    });
    rq.forEach((r, j) => {
      for (let gi = Math.floor(r[0] / lato); gi <= Math.floor(r[2] / lato); gi++)
        for (let gj = Math.floor(r[1] / lato); gj <= Math.floor(r[3] / lato); gj++) {
          const c = chiave(gi, gj); if (!griglia.has(c)) griglia.set(c, []); griglia.get(c).push(j);
        }
    });
    const copre = (k, x, y) => {        // il triangolo (proiettato) contiene il punto, bordo compreso
      const b = k * 9, x1 = t[b], y1 = t[b + 1], x2 = t[b + 3], y2 = t[b + 4], x3 = t[b + 6], y3 = t[b + 7];
      const d = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3);
      const l1 = ((y2 - y3) * (x - x3) + (x3 - x2) * (y - y3)) / d, l2 = ((y3 - y1) * (x - x3) + (x1 - x3) * (y - y3)) / d, l3 = 1 - l1 - l2;
      const e = -1e-9;
      return l1 >= e && l2 >= e && l3 >= e;
    };
    const zIn = (k, x, y) => { const b = k * 9; return t[b + 2] - (N[k * 3] * (x - t[b]) + N[k * 3 + 1] * (y - t[b + 1])) / N[k * 3 + 2]; };
    const tetti = [];
    cand.forEach((k, j) => {
      const b = k * 9;
      const x = (t[b] + t[b + 3] + t[b + 6]) / 3, y = (t[b + 1] + t[b + 4] + t[b + 7]) / 3, z = (t[b + 2] + t[b + 5] + t[b + 8]) / 3;
      const vicini = griglia.get(chiave(Math.floor(x / lato), Math.floor(y / lato))) || [];
      let sopra = false;
      for (const jj of vicini) {
        const kk = cand[jj];
        if (kk === k) continue;
        const r = rq[jj];
        if (x < r[0] || x > r[2] || y < r[1] || y > r[3] || !copre(kk, x, y)) continue;
        if (zIn(kk, x, y) > z + 0.2) { sopra = true; break; }
      }
      if (!sopra) tetti.push(k);
    });
    // raggruppamento per piano
    const cosT = Math.cos(tollAngolo * Math.PI / 180);
    const gruppi = [];
    for (const k of tetti) {
      const nx = N[k * 3], ny = N[k * 3 + 1], nz = N[k * 3 + 2], b = k * 9;
      let messo = false;
      for (const g of gruppi) {
        if (g.n[0] * nx + g.n[1] * ny + g.n[2] * nz >= cosT && Math.abs(g.n[0] * t[b] + g.n[1] * t[b + 1] + g.n[2] * t[b + 2] - g.d) <= tollDistanza) {
          g.idx.push(k); g.area3 += A3[k]; messo = true; break;
        }
      }
      if (!messo) gruppi.push({ n: [nx, ny, nz], d: nx * t[b] + ny * t[b + 1] + nz * t[b + 2], idx: [k], area3: A3[k] });
    }
    const falde = [];
    for (const g of gruppi) {
      const anelli = g.idx.map((k) => { const b = k * 9; return [[t[b], t[b + 1]], [t[b + 3], t[b + 4]], [t[b + 6], t[b + 7]]]; });
      const poli = G.semplifica(G.margine(G.margine(G.unione(anelli), 0.01), -0.01), 0.02);
      if (!poli.length || areaInsieme(poli) < 1.0) continue;
      let alto = -Infinity, basso = Infinity;
      for (const k of g.idx) for (const o of [2, 5, 8]) { alto = Math.max(alto, t[k * 9 + o]); basso = Math.min(basso, t[k * 9 + o]); }
      const pend = Math.acos(Math.min(1, Math.abs(g.n[2]))) * 180 / Math.PI;
      const orient = pend >= 0.5 ? ((Math.atan2(g.n[0], g.n[1]) * 180 / Math.PI) + 360) % 360 : 180.0;
      falde.push({ poligono: poli, pendenza: pend, orientamento: orient, superficie: g.area3, alto, basso });
    }
    if (!falde.length) return [];
    // corpi: falde inclinate a contatto con gronde simili insieme; ogni tetto piano a sé
    const corpiIdx = [];
    falde.forEach((f, k) => {
      let messo = false;
      if (f.pendenza >= 5) {
        for (const grp of corpiIdx) {
          const g0 = falde[grp[0]];
          if (g0.pendenza >= 5 && Math.abs(g0.basso - f.basso) < 1.0
              && grp.some((q) => G.interseca(G.margine(falde[q].poligono, 0.3), f.poligono) > 0)) {
            grp.push(k); messo = true; break;
          }
        }
      }
      if (!messo) corpiIdx.push([k]);
    });
    const corpi = [];
    const sposta = (r) => r.map((q) => [q[0] + ox, q[1] + oy]);
    for (const grp of corpiIdx) {
      let ps = G.semplifica(G.margine(G.margine(G.unionePoli(grp.flatMap((k) => falde[k].poligono)), 0.05), -0.05), 0.02);
      const poli = maggiore(ps);
      if (!poli || areaPoli(poli) < 4) continue;
      // base: punto più basso dei triangoli sotto la sagoma (pareti comprese)
      const bb = limiti2([poli]); bb[0] -= 0.5; bb[1] -= 0.5; bb[2] += 0.5; bb[3] += 0.5;
      let base = Infinity;
      for (let k = 0; k < n0; k++) {
        if (!ok[k]) continue;
        const b = k * 9;
        const x0 = Math.min(t[b], t[b + 3], t[b + 6]), x1 = Math.max(t[b], t[b + 3], t[b + 6]);
        const y0 = Math.min(t[b + 1], t[b + 4], t[b + 7]), y1 = Math.max(t[b + 1], t[b + 4], t[b + 7]);
        if (x0 <= bb[2] && x1 >= bb[0] && y0 <= bb[3] && y1 >= bb[1]) base = Math.min(base, t[b + 2], t[b + 5], t[b + 8]);
      }
      if (!Number.isFinite(base)) base = zmin;
      const fs = grp.map((k) => falde[k]);
      const alto = Math.max(...fs.map((f) => f.alto)) - base, basso = Math.min(...fs.map((f) => f.basso)) - base;
      if (!(alto > 0 && alto <= LIMITI.ALTEZZA_MAX)) continue;
      const incl = fs.filter((f) => f.pendenza >= 5);
      const tetto = !incl.length ? "piano" : ({ 1: "monofalda", 2: "capanna", 4: "padiglione" }[incl.length] || "a falde");
      corpi.push({ sagoma: chiudi(sposta(poli.esterno)), base, gronda: arrot(incl.length ? basso : alto, 2), colmo: arrot(alto, 2), tetto,
        falde: fs.map((f) => ({ pendenza: f.pendenza, orientamento: f.orientamento, area_pianta: areaInsieme(f.poligono), superficie: f.superficie,
          alto: f.alto - base, basso: f.basso - base, anello: chiudi(sposta(maggiore(f.poligono).esterno)) })) });
      if (corpi.length >= LIMITI.MAX_CORPI) break;
    }
    return corpi;
  }
  // arrotondamento come round() di Python (metà al pari, sui valori decimali tipici basta toFixed corretto)
  function arrot(v, n) { const k = 10 ** n; const x = v * k; const r = Math.round(x); return (Math.abs(x - Math.trunc(x)) === 0.5 && r % 2 !== 0 ? r - 1 : r) / k; }

  // ============================================================================================ DXF
  class Raccolta {                       // triangoli in un Float64Array che cresce
    constructor() { this.a = new Float64Array(9 * 1024); this.n = 0; }
    push9(v) { if (this.n + 9 > this.a.length) { const b = new Float64Array(this.a.length * 2); b.set(this.a); this.a = b; } this.a.set(v, this.n); this.n += 9; }
    get triangoli() { return this.n / 9; }
    dati() { return this.a.subarray(0, this.n); }
  }

  function aggiungiPoligono(tri, v, k) {
    const pts = [];
    for (const p of v) {
      if (!p || !Number.isFinite(p[0]) || !Number.isFinite(p[1])) continue;
      const q = [p[0] * k, p[1] * k, (Number.isFinite(p[2]) ? p[2] : 0) * k];
      const last = pts[pts.length - 1];
      if (q.every((c) => Number.isFinite(c) && Math.abs(c) < LIMITI.COORD_MAX) && (!last || q[0] !== last[0] || q[1] !== last[1] || q[2] !== last[2])) pts.push(q);
    }
    if (pts.length > 1 && pts[0][0] === pts[pts.length - 1][0] && pts[0][1] === pts[pts.length - 1][1] && pts[0][2] === pts[pts.length - 1][2]) pts.pop();
    for (let i = 1; i < pts.length - 1; i++) tri.push9([...pts[0], ...pts[i], ...pts[i + 1]]);
  }

  // matrici 4×4 per i blocchi (INSERT): [riga][colonna]
  const I4 = () => [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]];
  function mul(a, b) { const o = I4(); for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) { let s = 0; for (let k = 0; k < 4; k++) s += a[i][k] * b[k][j]; o[i][j] = s; } return o; }
  const appl = (m, p) => [m[0][0] * p[0] + m[0][1] * p[1] + m[0][2] * p[2] + m[0][3], m[1][0] * p[0] + m[1][1] * p[1] + m[1][2] * p[2] + m[1][3],
    m[2][0] * p[0] + m[2][1] * p[1] + m[2][2] * p[2] + m[2][3]];
  const P = (o) => (o ? [+o.x || 0, +o.y || 0, +o.z || 0] : null);

  // gestori in più per dxf-parser: MESH (vertici e facce) e i solidi ACIS (solo contati, come importa.py)
  function gestoreMesh() {
    return class { constructor() { this.ForEntityName = "MESH"; }
      parseEntity(sc, g) {
        const e = { type: "MESH", vertices: [], faces: [] };
        let stato = null, resto = 0, fc = null, x = 0, y = 0;
        g = sc.next();
        while (!sc.isEOF() && g.code !== 0) {
          if (g.code === 8) e.layer = g.value;
          else if (g.code === 92) stato = "v";
          else if (g.code === 93) { stato = "f"; resto = g.value; }
          else if (g.code === 94 || g.code === 95 || g.code === 90 && stato !== "f") { if (g.code !== 90) stato = null; }
          else if (stato === "v" && g.code === 10) x = g.value;
          else if (stato === "v" && g.code === 20) y = g.value;
          else if (stato === "v" && g.code === 30) e.vertices.push([x, y, g.value]);
          else if (stato === "f" && g.code === 90) {
            if (!fc) fc = { n: g.value, i: [] }; else { fc.i.push(g.value); if (fc.i.length === fc.n) { e.faces.push(fc.i); fc = null; } }
            if (--resto <= 0) stato = null;
          }
          g = sc.next();
        }
        return e;
      } };
  }
  function gestoreSolido(nome) {
    return class { constructor() { this.ForEntityName = nome; }
      parseEntity(sc, g) { const e = { type: nome }; g = sc.next(); while (!sc.isEOF() && g.code !== 0) { if (g.code === 8) e.layer = g.value; g = sc.next(); } return e; } };
  }

  function altezzaLayer(nome) {
    const m = /(?:^|[^A-Za-z])(?:H|ALT|ALTEZZA)\s*[=_:]?\s*(\d+(?:[.,]\d+)?)/i.exec(String(nome || ""));
    return m ? parseFloat(m[1].replace(",", ".")) : null;
  }

  function leggiDxf(testo, lib, unita = null) {
    const parser = new lib.DxfParser();
    parser.registerEntityHandler(gestoreMesh());
    for (const s of ["3DSOLID", "BODY", "REGION", "SURFACE"]) parser.registerEntityHandler(gestoreSolido(s));
    let doc;
    const avvisi = [];
    try { doc = parser.parseSync(testo); } catch (e) { throw err(`DXF non leggibile (${pulisci(e && e.message, 60) || "errore"})`); }
    if (!doc || !Array.isArray(doc.entities)) throw err("DXF non leggibile (manca la sezione ENTITIES)");
    const ins = parseInt((doc.header || {}).$INSUNITS, 10) || 0;
    const k = unita || UNITA_DXF[ins] || 1.0;
    if (!unita && !(ins in UNITA_DXF)) avvisi.push("unità del disegno non indicate: si assumono metri (opzione «unità» per cambiarle)");
    const tri = new Raccolta(), prismi = [], conta = { n: 0, solidi: 0, ocs: 0 };
    const C = lib.ClipperLib, G = geometria(C);
    const blocchi = doc.blocks || {};

    function visita(entita, M, prof) {
      for (const e of entita || []) {
        if (++conta.n > LIMITI.MAX_ENTITA) throw err(`troppe entità (oltre ${LIMITI.MAX_ENTITA})`);
        const tp = e.type;
        try {
          if (tp === "INSERT") {
            if (prof >= LIMITI.MAX_PROFONDITA) throw err("blocchi annidati troppo in profondità");
            const b = blocchi[e.name];
            if (!b) continue;
            if (e.extrusionDirection && Math.abs((e.extrusionDirection.z == null ? 1 : e.extrusionDirection.z) - 1) > 1e-9) conta.ocs++;
            const pos = P(e.position) || [0, 0, 0], base = P(b.position) || [0, 0, 0];
            const r = (+e.rotation || 0) * Math.PI / 180, c = Math.cos(r), s = Math.sin(r);
            const sx = e.xScale == null ? 1 : +e.xScale, sy = e.yScale == null ? 1 : +e.yScale, sz = e.zScale == null ? 1 : +e.zScale;
            const Mi = [[c * sx, -s * sy, 0, pos[0]], [s * sx, c * sy, 0, pos[1]], [0, 0, sz, pos[2]], [0, 0, 0, 1]];
            const Tb = [[1, 0, 0, -base[0]], [0, 1, 0, -base[1]], [0, 0, 1, -base[2]], [0, 0, 0, 1]];
            visita(b.entities, mul(M, mul(Mi, Tb)), prof + 1);
          } else if (tp === "3DFACE") {
            aggiungiPoligono(tri, (e.vertices || []).slice(0, 4).map((v) => appl(M, P(v))), k);
          } else if (tp === "MESH") {
            const vs = e.vertices.map((v) => appl(M, v));
            for (const f of e.faces) aggiungiPoligono(tri, f.filter((i) => i >= 0 && i < vs.length).map((i) => vs[i]), k);
          } else if (tp === "POLYLINE" && e.isPolyfaceMesh) {
            const vs = (e.vertices || []).filter((v) => v.polyfaceMeshVertex && v.threeDPolylineMesh).map((v) => appl(M, [+v.x || 0, +v.y || 0, +v.z || 0]));
            for (const v of e.vertices || []) {
              if (!v.polyfaceMeshVertex || v.threeDPolylineMesh) continue;
              const idx = [v.faceA, v.faceB, v.faceC, v.faceD].filter((i) => i != null && i !== 0).map((i) => Math.abs(i) - 1);
              aggiungiPoligono(tri, idx.filter((i) => i >= 0 && i < vs.length).map((i) => vs[i]), k);
            }
          } else if ((tp === "LWPOLYLINE" || tp === "POLYLINE") && e.shape) {
            prisma(e, tp, k, M);
          } else if (tp === "3DSOLID" || tp === "BODY" || tp === "REGION" || tp === "SURFACE") {
            conta.solidi++;
          }
        } catch (ex) {
          if (ex instanceof ModelloNonValido) throw ex;
          continue;
        }
        if (tri.triangoli > LIMITI.MAX_TRIANGOLI) throw err(`troppi triangoli (oltre ${LIMITI.MAX_TRIANGOLI})`);
      }
    }

    function prisma(e, tp, k, M) {
      let pts, base;
      if (tp === "LWPOLYLINE") {
        const el = +e.elevation || 0;
        const q = (e.vertices || []).map((v) => appl(M, [+v.x, +v.y, el]));
        pts = q.map((p) => [p[0] * k, p[1] * k]);
        base = (q.length ? q[0][2] : el) * k;
      } else {
        const q = (e.vertices || []).map((v) => appl(M, [+v.x || 0, +v.y || 0, +v.z || 0]));
        pts = q.map((p) => [p[0] * k, p[1] * k]);
        base = q.length ? q[0][2] * k : 0;
      }
      const sz = Math.hypot(M[0][2], M[1][2], M[2][2]) || 1;
      const spRaw = tp === "LWPOLYLINE" ? +e.depth || 0 : +e.thickness || 0;
      const spessore = spRaw * sz * k;
      const h = spessore ? Math.abs(spessore) : altezzaLayer(e.layer);
      if (pts.length < 3 || !pts.every((p) => p.every((c) => Number.isFinite(c) && Math.abs(c) < LIMITI.COORD_MAX))) return;
      // il poligono si ripara come buffer(0): si lavora vicino all'origine per gli interi di Clipper
      const o = pts[0];
      let g = G.ripara(pts.map((p) => [p[0] - o[0], p[1] - o[1]]));
      if (!g || g.buchi.length && areaPoli(g) <= 0) return;
      g = { esterno: g.esterno.map((p) => [p[0] + o[0], p[1] + o[1]]), buchi: g.buchi.map((b) => b.map((p) => [p[0] + o[0], p[1] + o[1]])) };
      if (areaPoli(g) < 1) return;
      if (spessore < 0) base -= Math.abs(spessore);
      const gr = h && h > 0 && h <= LIMITI.ALTEZZA_MAX ? h : null;
      // se il poligono era già valido si tengono i punti com'erano (come shapely)
      const anello = Math.abs(Math.abs(areaAnello(pts)) - areaPoli(g)) < 1e-6 && g.buchi.length === 0 ? chiudi(pts) : chiudi(g.esterno);
      const a = areaPoli(g);
      prismi.push({ sagoma: anello, base, gronda: gr, colmo: gr, tetto: "piano",
        falde: [{ pendenza: 0.0, orientamento: 180.0, area_pianta: a, superficie: a, alto: gr || 0.0, basso: gr || 0.0, anello }],
        nota: gr ? null : "altezza non indicata nel DXF: da completare nella pagina", nome: pulisci(e.layer) });
    }

    visita(doc.entities, I4(), 0);
    if (conta.solidi) avvisi.push(`${conta.solidi} solidi ACIS (3DSOLID) non letti: esportarli come MESH o 3DFACE`);
    if (conta.ocs) avvisi.push(`${conta.ocs} blocchi con direzione di estrusione diversa da +Z: letti come se fossero in pianta`);
    let corpi = tri.triangoli ? corpiDaTriangoli(tri.dati(), C) : [];
    const sovrapposto = (a, b) => {
      const o = a.sagoma[0], loc = (r) => ({ esterno: r.slice(0, -1).map((q) => [q[0] - o[0], q[1] - o[1]]), buchi: [] });
      const pa = loc(a.sagoma), pb = loc(b.sagoma);
      return G.interseca([pa], [pb]) > 0.5 * Math.min(Math.abs(areaAnello(pa.esterno)), Math.abs(areaAnello(pb.esterno)));
    };
    corpi = corpi.concat(prismi.filter((c) => !corpi.some((d) => sovrapposto(c, d))));
    if (!corpi.length) throw err("nessun corpo trovato: servono polilinee chiuse con spessore o facce 3D");
    return { corpi: corpi.slice(0, LIMITI.MAX_CORPI), avvisi, georef: null, unita_m: k };
  }

  // ============================================================================================ IFC
  const TIPI_IFC_ESCLUSI = ["IFCSPACE", "IFCOPENINGELEMENT", "IFCSITE", "IFCANNOTATION", "IFCGRID", "IFCVIRTUALELEMENT",
    "IFCGEOGRAPHICELEMENT", "IFCFURNISHINGELEMENT", "IFCDISTRIBUTIONELEMENT"];
  const PREFISSI = { EXA: 1e18, PETA: 1e15, TERA: 1e12, GIGA: 1e9, MEGA: 1e6, KILO: 1e3, HECTO: 1e2, DECA: 10, DECI: 0.1, CENTI: 0.01,
    MILLI: 1e-3, MICRO: 1e-6, NANO: 1e-9 };
  // web-ifc dà i valori semplici come {value}, i numeri «tipizzati» come {_representationValue}
  const val = (x) => (x && typeof x === "object" ? ("value" in x ? x.value : "_representationValue" in x ? x._representationValue : x) : x);
  const lista = (x) => { x = val(x); return Array.isArray(x) ? x.map(val) : []; };

  /** IFC (Uint8Array) → corpi. `api` è un IfcAPI di web-ifc già inizializzato. */
  function leggiIfc(dati, lib, api) {
    const W = lib.WebIFC;
    let id;
    try { id = api.OpenModel(dati, { COORDINATE_TO_ORIGIN: false, MEMORY_LIMIT: LIMITI.MEMORIA_IFC_MB * 1024 * 1024 }); }
    catch (e) { throw err(`IFC non leggibile (${pulisci(e && e.message, 60) || "errore"})`); }
    if (id < 0) throw err("IFC non leggibile");
    try {
      const avvisi = [];
      const esclusi = new Set();
      for (const nome of TIPI_IFC_ESCLUSI) {
        if (W[nome] == null) continue;
        try { for (const x of api.GetLineIDsWithType(id, W[nome], true)) esclusi.add(x); } catch { /* tipo assente nello schema */ }
      }
      let prodotti = 0;
      try { prodotti = api.GetLineIDsWithType(id, W.IFCPRODUCT, true).size(); } catch { prodotti = 0; }
      if (prodotti > LIMITI.MAX_ENTITA) throw err(`troppi elementi (oltre ${LIMITI.MAX_ENTITA})`);
      const tri = new Raccolta();
      let troppi = false;
      api.StreamAllMeshes(id, (m) => {
        if (troppi || esclusi.has(m.expressID)) return;
        const n = m.geometries.size();
        for (let i = 0; i < n; i++) {
          const g = m.geometries.get(i);
          const geo = api.GetGeometry(id, g.geometryExpressID);
          const v = api.GetVertexArray(geo.GetVertexData(), geo.GetVertexDataSize());
          const ix = api.GetIndexArray(geo.GetIndexData(), geo.GetIndexDataSize());
          const M = g.flatTransformation;
          // web-ifc restituisce coordinate «Y in alto» (come three.js) già in metri: si torna a Z in alto
          const pos = new Float64Array((v.length / 6) * 3);
          let buono = true;
          for (let a = 0, b = 0; a < v.length; a += 6, b += 3) {
            const x = v[a], y = v[a + 1], z = v[a + 2];
            const X = M[0] * x + M[4] * y + M[8] * z + M[12], Y = M[1] * x + M[5] * y + M[9] * z + M[13], Z = M[2] * x + M[6] * y + M[10] * z + M[14];
            pos[b] = X; pos[b + 1] = -Z; pos[b + 2] = Y;
            if (!Number.isFinite(X) || !Number.isFinite(Y) || !Number.isFinite(Z) || Math.abs(X) > LIMITI.COORD_MAX || Math.abs(Y) > LIMITI.COORD_MAX || Math.abs(Z) > LIMITI.COORD_MAX) buono = false;
          }
          if (geo.delete) geo.delete();
          if (!buono || !ix.length) continue;
          for (let q = 0; q + 2 < ix.length; q += 3) {
            const a = ix[q] * 3, b = ix[q + 1] * 3, c = ix[q + 2] * 3;
            tri.push9([pos[a], pos[a + 1], pos[a + 2], pos[b], pos[b + 1], pos[b + 2], pos[c], pos[c + 1], pos[c + 2]]);
          }
          if (tri.triangoli > LIMITI.MAX_TRIANGOLI) { troppi = true; return; }
        }
      });
      if (troppi) throw err(`troppi triangoli (oltre ${LIMITI.MAX_TRIANGOLI})`);
      if (!tri.triangoli) throw err("nessuna geometria leggibile negli elementi dell'IFC");
      const corpi = corpiDaTriangoli(tri.dati(), lib.ClipperLib);
      if (!corpi.length) throw err("nessun tetto riconosciuto nel modello");
      let schema = "";
      try { schema = pulisci(api.GetModelSchema(id), 20); } catch { /* niente */ }
      return { corpi: corpi.slice(0, LIMITI.MAX_CORPI), avvisi, georef: georefIfc(api, id, W), unita_m: 1.0, schema };
    } finally {
      try { api.CloseModel(id); } catch { /* già chiuso */ }
    }
  }

  function unitaIfc(api, id, W) {
    try {
      for (const ua of api.GetLineIDsWithType(id, W.IFCUNITASSIGNMENT)) {
        const l = api.GetLine(id, ua, true);
        for (const u of l.Units || []) {
          if (val(u.UnitType) !== "LENGTHUNIT") continue;
          if (u.type === W.IFCSIUNIT) return u.Prefix ? PREFISSI[val(u.Prefix)] || 1 : 1;
          if (u.type === W.IFCCONVERSIONBASEDUNIT) {
            const mf = u.ConversionFactor, uc = mf && mf.UnitComponent;
            return +val(mf.ValueComponent) * (uc && uc.Prefix ? PREFISSI[val(uc.Prefix)] || 1 : 1);
          }
        }
      }
    } catch { /* unità non leggibili */ }
    return 1.0;
  }

  function piazzamento(api, id, pid, prof = 0) {   // matrice 4×4 di un IfcLocalPlacement, nelle unità del progetto
    if (!pid || prof > 20) return I4();
    const l = api.GetLine(id, pid, false);
    const rel = l.RelativePlacement ? api.GetLine(id, val(l.RelativePlacement), true) : null;
    let M = I4();
    if (rel && rel.Location) {
      const p = lista(rel.Location.Coordinates);
      const z = rel.Axis ? lista(rel.Axis.DirectionRatios) : [0, 0, 1];
      let x = rel.RefDirection ? lista(rel.RefDirection.DirectionRatios) : [1, 0, 0];
      const nz = Math.hypot(...z); const Z = z.map((c) => c / nz);
      const d = x[0] * Z[0] + x[1] * Z[1] + (x[2] || 0) * Z[2]; x = [x[0] - d * Z[0], x[1] - d * Z[1], (x[2] || 0) - d * Z[2]];
      const nx = Math.hypot(...x); const X = x.map((c) => c / nx);
      const Y = [Z[1] * X[2] - Z[2] * X[1], Z[2] * X[0] - Z[0] * X[2], Z[0] * X[1] - Z[1] * X[0]];
      M = [[X[0], Y[0], Z[0], p[0] || 0], [X[1], Y[1], Z[1], p[1] || 0], [X[2], Y[2], Z[2], p[2] || 0], [0, 0, 0, 1]];
    }
    return l.PlacementRelTo ? mul(piazzamento(api, id, val(l.PlacementRelTo), prof + 1), M) : M;
  }

  /** Posa dal file: IfcMapConversion (IFC4) se c'è, altrimenti latitudine/longitudine e nord vero di IfcSite. */
  function georefIfc(api, id, W) {
    const u = unitaIfc(api, id, W);
    try {
      if (W.IFCMAPCONVERSION != null) for (const mid of api.GetLineIDsWithType(id, W.IFCMAPCONVERSION)) {
        const mc = api.GetLine(id, mid, true);
        const nome = String(val(mc.TargetCRS && mc.TargetCRS.Name) || "");
        const m = /(\d{4,5})/.exec(nome);
        if (!m) continue;
        const a = mc.XAxisAbscissa != null ? +val(mc.XAxisAbscissa) : 1.0, b = mc.XAxisOrdinate != null ? +val(mc.XAxisOrdinate) : 0.0;
        return { tipo: "conversione", crs: `EPSG:${m[1]}`, e0: +val(mc.Eastings), n0: +val(mc.Northings), quota: +val(mc.OrthogonalHeight) || 0.0,
          a, b, scala: (+val(mc.Scale) || 1.0) / u, origine: "IfcMapConversion" };
      }
    } catch { /* niente */ }
    try {
      for (const sid of api.GetLineIDsWithType(id, W.IFCSITE)) {
        const s = api.GetLine(id, sid, false);
        if (!s.RefLatitude || !s.RefLongitude) continue;
        const g = (c) => { c = lista(c).map(Number); const v = Math.abs(c[0]) + c[1] / 60 + c[2] / 3600 + (c.length > 3 ? c[3] : 0) / 3.6e9; return (c[0] < 0 || c.some((x) => x < 0)) ? -v : v; };
        let rot = 0.0;
        for (const cid of api.GetLineIDsWithType(id, W.IFCGEOMETRICREPRESENTATIONCONTEXT)) {
          const c = api.GetLine(id, cid, true);
          if (c.TrueNorth && c.TrueNorth.DirectionRatios) { const [x, y] = lista(c.TrueNorth.DirectionRatios); rot = Math.atan2(x, y) * 180 / Math.PI; break; }
        }
        let ox = 0, oy = 0;
        try { const M = piazzamento(api, id, val(s.ObjectPlacement)); ox = M[0][3] * u; oy = M[1][3] * u; } catch { /* origine */ }
        return { tipo: "punto", lon: g(s.RefLongitude), lat: g(s.RefLatitude), x: ox, y: oy, rotazione: rot === 0 ? 0 : -rot,
          quota: +val(s.RefElevation) || 0.0, origine: "IfcSite" };
      }
    } catch { /* niente */ }
    return null;
  }

  // ============================================================================================ posa e GeoJSON
  function definisci(proj4) { for (const [c, [, d]] of Object.entries(SISTEMI)) if (!proj4.defs(c)) proj4.defs(c, d); }

  function trasformazione(posa, proj4) {
    definisci(proj4);
    const avvisi = [];
    if (!posa) throw err("manca la posa: il modello non è georeferenziato. Scegli il sistema di riferimento del disegno, oppure fissa due punti noti sulla mappa (o un punto e la rotazione)");
    const sistema = (c) => { if (!SISTEMI[c]) throw err(`sistema ${c} non noto alla pagina: scegline uno dell'elenco o converti il file sul PC`); return c; };
    const aWgs = (e, n) => proj4("EPSG:7791", "EPSG:4326", [e, n]), daWgs = (lo, la) => proj4("EPSG:4326", "EPSG:7791", [lo, la]);
    if (posa.tipo === "crs") { const c = sistema(posa.crs); return { f: (x, y) => proj4(c, "EPSG:4326", [x, y]), avvisi }; }
    if (posa.tipo === "conversione") {
      const c = sistema(posa.crs), h = Math.hypot(posa.a, posa.b) || 1.0, ca = posa.a / h, sa = posa.b / h, s = posa.scala;
      return { f: (x, y) => proj4(c, "EPSG:4326", [posa.e0 + s * (ca * x - sa * y), posa.n0 + s * (sa * x + ca * y)]), avvisi };
    }
    if (posa.tipo === "punto") {
      // rotazione = azimut (gradi da nord vero, senso orario) dell'asse +Y del disegno; nel reticolo UTM si aggiunge la
      // convergenza del meridiano
      const [e0, n0] = daWgs(posa.lon, posa.lat), [e1, n1] = daWgs(posa.lon, posa.lat + 0.001);
      const conv = Math.atan2(e1 - e0, n1 - n0) * 180 / Math.PI;
      const r = ((posa.rotazione || 0) + conv) * Math.PI / 180, cr = Math.cos(r), sr = Math.sin(r);
      return { f: (x, y) => { const dx = x - posa.x, dy = y - posa.y; return aWgs(e0 + cr * dx + sr * dy, n0 - sr * dx + cr * dy); }, avvisi };
    }
    if (posa.tipo === "due_punti") {
      const [[x1, y1, lo1, la1], [x2, y2, lo2, la2]] = posa.punti;
      const [e1, n1] = daWgs(lo1, la1), [e2, n2] = daWgs(lo2, la2);
      const zd = [x2 - x1, y2 - y1], zm = [e2 - e1, n2 - n1], q = zd[0] * zd[0] + zd[1] * zd[1];
      if (Math.sqrt(q) < 1e-6) throw err("posa: i due punti del disegno coincidono");
      const kr = (zm[0] * zd[0] + zm[1] * zd[1]) / q, ki = (zm[1] * zd[0] - zm[0] * zd[1]) / q, ks = Math.hypot(kr, ki);
      if (!(ks > 0.9 && ks < 1.1)) avvisi.push(`scala della posa ${ks.toFixed(3)} (attesa 1): controllare le unità del disegno e i due punti`);
      return { f: (x, y) => { const dx = x - x1, dy = y - y1; return aWgs(e1 + kr * dx - ki * dy, n1 + ki * dx + kr * dy); }, avvisi };
    }
    throw err("posa non riconosciuta");
  }

  function inMetri(posa, k) {
    if (!posa || k === 1.0) return posa;
    const q = { ...posa };
    if (q.tipo === "punto") { q.x *= k; q.y *= k; }
    else if (q.tipo === "due_punti") q.punti = q.punti.map(([x, y, lo, la]) => [x * k, y * k, lo, la]);
    return q;
  }

  const SETTORI = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"];
  const settore = (az) => SETTORI[Math.floor((((az + 22.5) % 360) + 360) % 360 / 45)];
  function centro(cs) { const p = cs.slice(0, -1); const n = p.length || 1; return [p.reduce((s, q) => s + q[0], 0) / n, p.reduce((s, q) => s + q[1], 0) / n]; }
  function azimutY(f, x, y) { const [lo0, la0] = f(x, y), [lo1, la1] = f(x, y + 1.0); return Math.atan2((lo1 - lo0) * Math.cos(la0 * Math.PI / 180), la1 - la0) * 180 / Math.PI; }
  const r8 = (v) => Math.round(v * 1e8) / 1e8;

  /** Corpi nelle coordinate del disegno → FeatureCollection WGS84 «eugenio-modello-1» (come geojson() di importa.py). */
  function geojson(r, posa, tipo, nomeFile, sha256, proj4, edificio = "MODELLO") {
    const { f, avvisi: av } = trasformazione(posa, proj4);
    const avvisi = (r.avvisi || []).concat(av);
    edificio = pulisci(edificio, 40) || "MODELLO";
    const fonte = `modello dell'utente (${tipo.toUpperCase()})`;
    const anello = (cs) => cs.map(([x, y]) => {
      const [lon, lat] = f(x, y);
      if (!(Number.isFinite(lon) && Number.isFinite(lat) && lon >= -180 && lon <= 180 && lat >= -90 && lat <= 90)) throw err("coordinate fuori scala dopo la posa");
      return [r8(lon), r8(lat)];
    });
    const feats = r.corpi.map((c, i) => {
      const cid = `${edificio}-${i + 1}`;
      const dy = azimutY(f, ...centro(c.sagoma));
      const falde = (c.falde || []).map((fa, j) => {
        const p = +fa.pendenza;
        const or = p >= 0.5 ? (((+fa.orientamento + dy) % 360) + 360) % 360 : +fa.orientamento;
        return { id: `F${j + 1}`, pendenza: arrot(p, 1), orientamento: arrot(or, 1) % 360, settore: p < 5 ? "—" : settore(or),
          area_pianta: arrot(+fa.area_pianta, 1), superficie: arrot(+fa.superficie, 1), alto: arrot(+fa.alto, 2), basso: arrot(+fa.basso, 2),
          geometria: { type: "Polygon", coordinates: [anello(fa.anello)] } };
      });
      const props = { id: cid, edificio, gronda: c.gronda, colmo: c.colmo, tetto: c.tetto || "piano", falde, fonte_sagoma: fonte, fonte_altezza: fonte,
        licenza: LICENZA, area: arrot(Math.abs(areaAnello(c.sagoma.slice(0, -1))), 1), quota_base_modello: arrot(+c.base || 0, 2) };
      if (c.nota) props.nota = c.nota;
      return { type: "Feature", id: cid, geometry: { type: "Polygon", coordinates: [anello(c.sagoma)] }, properties: props };
    });
    const pz = {};
    for (const [k, v] of Object.entries(posa || {})) if (k !== "punti") pz[k] = v;
    if (posa && posa.punti) pz.punti = posa.punti.length;
    return { type: "FeatureCollection", formato: FORMATO, fonte, file: nomeFile, sha256, licenza: LICENZA, avvisi: avvisi.slice(0, 20), posa: pz, features: feats };
  }

  return { LIMITI, SISTEMI, FORMATO, ModelloNonValido, pulisci, controllaFile, corpiDaTriangoli, leggiDxf, leggiIfc, trasformazione,
    inMetri, geojson, altezzaLayer, settore };
});
