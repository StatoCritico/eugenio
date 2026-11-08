/* EuGEnio – DB topografici regionali letti nel browser (pagina «Aggiungi edifici (DB topografico)», 07/11/2026).
 *
 * Stessa logica di fase10-edifici3d/edifici3d/uvl.py (DBTR Emilia-Romagna: regole delle altezze con la convenzione del
 * comune, cortili, legame corpo–edificio, foglio, numero, nome e destinazione) e di regionali.py (DBGT Lombardia, CTRN
 * Friuli Venezia Giulia), riscritta in JavaScript: stessi corpi, stesse proprietà, stesse coordinate WGS84 di
 * `tessere.feature_da_corpi` (test di parità in fase10-edifici3d/tests/test_dbtr_parita.py, con node e in Chromium).
 * Differenze solo nei lettori:
 *   - zip con fflate (MIT); GeoPackage (SQLite) con sql.js (MIT, WebAssembly); Shapefile e DBF letti qui (formato
 *     pubblico ESRI, poche decine di righe); sistemi di riferimento con proj4js (MIT);
 *   - le geometrie non valide non si riparano (in Python make_valid): si contano e si dicono nel riepilogo;
 *   - senza DTM: quota del terreno = base del DB topografico (B_UVL, quota del piede…), dichiarata.
 * Gira nel Web Worker della pagina (dbtr_worker.js) e in node per i test. Le librerie arrivano come argomenti (`lib`).
 */
(function (radice, fabbrica) {
  if (typeof module === "object" && module.exports) module.exports = fabbrica();
  else radice.EUGENIO_DBTR = fabbrica();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const LIMITI = { MAX_MB: 300, MAX_ESTRATTO: 3 * 1024 ** 3, MAX_VOCI: 2000, MAX_RAPPORTO: 200, MAX_CORPI: 400000 };
  class DbtrNonValido extends Error {}
  const err = (t) => new DbtrNonValido(t);

  // come edifici3d/coda.py: regioni della prima versione
  const REGIONI = {
    er: { nome: "Emilia-Romagna", istat: "08", crs: "EPSG:7791", sperimentale: false, fonte: "DBTR Emilia-Romagna – UVL",
      licenza: "CC BY 4.0", attribuzione: "Regione Emilia-Romagna – DBTR, CC BY 4.0", riquadro: [9.19, 43.73, 12.76, 45.14] },
    lom: { nome: "Lombardia", istat: "03", crs: "EPSG:7791", sperimentale: true, fonte: "DBGT Lombardia – Unità volumetrica (020101)",
      licenza: "CC BY 4.0", attribuzione: "Regione Lombardia – DBGT, Unità volumetrica (CC BY 4.0)", riquadro: [8.49, 44.67, 11.43, 46.64] },
    fvg: { nome: "Friuli Venezia Giulia", istat: "06", crs: "EPSG:6708", sperimentale: true, fonte: "IRDAT FVG – Edificato CTRN",
      licenza: "CC BY 4.0", attribuzione: "Regione Autonoma Friuli Venezia Giulia – IRDAT, Edificato CTRN (CC BY 4.0)", riquadro: [12.32, 45.58, 13.92, 46.65] },
    lig: { nome: "Liguria", istat: "07", crs: "EPSG:7791", sperimentale: true, fonte: "Regione Liguria – CTR 3D, Edificato",
      licenza: "CC BY 4.0", attribuzione: "Regione Liguria – Carta Tecnica Regionale 1:5000 3D / DB topografico (CC BY 4.0)", riquadro: [7.49, 43.75, 10.08, 44.68] },
  };
  // sistemi di riferimento (stesse definizioni di modelli_import.js e di PROJ; assi est, nord)
  const SISTEMI = {
    "EPSG:7791": "+proj=utm +zone=32 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs",
    "EPSG:7792": "+proj=utm +zone=33 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs",
    "EPSG:6707": "+proj=utm +zone=32 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs",
    "EPSG:6708": "+proj=utm +zone=33 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs",
    "EPSG:25832": "+proj=utm +zone=32 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs",
    "EPSG:25833": "+proj=utm +zone=33 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs",
    "EPSG:3064": "+proj=utm +zone=32 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs",
    "EPSG:3065": "+proj=utm +zone=33 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs",
    "EPSG:32632": "+proj=utm +zone=32 +datum=WGS84 +units=m +no_defs",
    "EPSG:32633": "+proj=utm +zone=33 +datum=WGS84 +units=m +no_defs",
    "EPSG:3003": "+proj=tmerc +lat_0=0 +lon_0=9 +k=0.9996 +x_0=1500000 +y_0=0 +ellps=intl +towgs84=-104.1,-49.1,-9.9,0.971,-2.917,0.714,-11.68 +units=m +no_defs",
    "EPSG:3004": "+proj=tmerc +lat_0=0 +lon_0=15 +k=0.9996 +x_0=2520000 +y_0=0 +ellps=intl +towgs84=-104.1,-49.1,-9.9,0.971,-2.917,0.714,-11.68 +units=m +no_defs",
    "EPSG:4326": "+proj=longlat +datum=WGS84 +no_defs",
    "EPSG:4258": "+proj=longlat +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +no_defs",
    "EPSG:6706": "+proj=longlat +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +no_defs",
    "EPSG:4979": "+proj=longlat +datum=WGS84 +no_defs",
  };
  const UTM32 = ["EPSG:7791", "EPSG:6707", "EPSG:25832", "EPSG:3064", "EPSG:32632"];

  // ============================================================================================ utilità
  const pulisci = (t, n = 80) => String(t == null ? "" : t).replace(/[\x00-\x1f\x7f<>]/g, " ").replace(/\s+/g, " ").trim().slice(0, n);
  const vuoto = (v) => v === null || v === undefined || (typeof v === "number" && Number.isNaN(v))
    || ["", "Null", "NULL", "null", "nan"].includes(String(v).trim());
  // modello.numero: numero anche all'italiana («1.234,5»); null per vuoti e testi
  function numero(v) {
    if (v === null || v === undefined || typeof v === "boolean") return null;
    if (typeof v === "number") return Number.isFinite(v) ? v : null;
    let s = String(v).trim().replace(/ /g, "");
    if (!s) return null;
    if (s.includes(",")) s = s.replace(/\./g, "").replace(",", ".");
    if (!/^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(s)) return null;
    const x = parseFloat(s);
    return Number.isFinite(x) ? x : null;
  }
  // uvl._num
  function num(v) {
    if (vuoto(v)) return null;
    if (typeof v === "number") return Number.isFinite(v) ? v : null;
    const s = String(v).trim();
    const x = /^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(s) ? parseFloat(s) : numero(v);
    return x !== null && Number.isFinite(x) ? x : null;
  }
  // round() di Python: sul valore binario esatto (toFixed lo usa), e a metà esatta verso la cifra pari
  function arrotonda(x, n) {
    if (!Number.isFinite(x)) return x;
    const esatto = Math.abs(x).toFixed(Math.min(100, n + 60));
    const [i, f = ""] = esatto.split(".");
    if (/^50*$/.test(f.slice(n))) {
      const tronco = Number(`${i}.${f.slice(0, n) || "0"}`);
      const ultima = Number((i + f.slice(0, n)).slice(-1));
      const v = ultima % 2 === 0 ? tronco : tronco + 10 ** -n;
      return Number((x < 0 ? -v : v).toFixed(n));
    }
    return Number(x.toFixed(n));
  }
  const r2 = (x) => arrotonda(x, 2);
  const r1 = (x) => arrotonda(x, 1);
  const r7 = (x) => Math.round(x * 1e7) / 1e7;
  const fmtG = (x) => String(Number(x.toPrecision(6)));          // come «{q:g}» di Python per i valori usati
  const maiuscole = (p) => { const o = {}; for (const k of Object.keys(p)) o[String(k).toUpperCase()] = p[k]; return o; };

  // ============================================================================================ geometrie
  // coordinate spostate sul primo vertice, come GEOS: con x ~ 780.000 e y ~ 4.880.000 la formula diretta perde i decimi di m²
  function areaAnello(r) {
    if (!r.length) return 0;
    const x0 = r[0][0], y0 = r[0][1];
    let s = 0;
    for (let i = 0, n = r.length; i < n; i++) {
      const a = r[i], b = r[(i + 1) % n];
      s += (a[0] - x0) * (b[1] - y0) - (b[0] - x0) * (a[1] - y0);
    }
    return s / 2;
  }
  // area di un poligono (anelli: esterno, poi fori) come shapely
  const areaPoligono = (pol) => Math.abs(areaAnello(pol[0])) - pol.slice(1).reduce((s, r) => s + Math.abs(areaAnello(r)), 0);
  function dentroAnello(p, r) {
    let d = false;
    for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
      const a = r[i], b = r[j];
      if ((a[1] > p[1]) !== (b[1] > p[1]) && p[0] < ((b[0] - a[0]) * (p[1] - a[1])) / (b[1] - a[1]) + a[0]) d = !d;
    }
    return d;
  }
  // anelli di un record Shapefile → poligoni: esterni in senso orario (area negativa), fori antiorari dentro un esterno
  function poligoniDaAnelli(anelli) {
    const est = [], fori = [];
    anelli.forEach((r) => { if (r.length >= 4) (areaAnello(r) <= 0 ? est : fori).push(r); });
    if (!est.length) return fori.map((r) => [r]);
    const pol = est.map((r) => [r]);
    for (const f of fori) {
      const k = pol.findIndex((p) => dentroAnello(f[0], p[0]));
      if (k >= 0) pol[k].push(f); else pol.push([f]);
    }
    return pol;
  }
  // geometria → poligono più grande (come shapely: MultiPolygon → parte con l'area maggiore)
  function piuGrande(poligoni) {
    if (!poligoni || !poligoni.length) return null;
    let m = null, a = -1;
    for (const p of poligoni) { const x = areaPoligono(p); if (x > a) { a = x; m = p; } }
    return m;
  }
  // anello con un'autointersezione evidente (lati non adiacenti che si tagliano): solo per contarli, su anelli piccoli
  function nonValido(pol) {
    const r = pol[0];
    if (r.length > 400) return false;
    const n = r.length - 1;
    const taglia = (p, q, s, t) => {
      const d = (a, b, c) => (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
      return d(p, q, s) * d(p, q, t) < 0 && d(s, t, p) * d(s, t, q) < 0;
    };
    for (let i = 0; i < n; i++) for (let j = i + 2; j < n; j++) {
      if (i === 0 && j === n - 1) continue;
      if (taglia(r[i], r[i + 1], r[j], r[j + 1])) return true;
    }
    return false;
  }

  // ---------------------------------------------------------------------------------------- WKB (GeoPackage)
  function leggiWkb(dv, o) {
    const le = dv.getUint8(o) === 1; o += 1;
    let tipo = dv.getUint32(o, le); o += 4;
    let z = false, m = false;
    if (tipo & 0x80000000) z = true;
    if (tipo & 0x40000000) m = true;
    if (tipo & 0x20000000) o += 4;                                  // SRID dell'EWKB
    tipo &= 0x0fffffff;
    if (tipo >= 3000) { z = true; m = true; tipo -= 3000; } else if (tipo >= 2000) { m = true; tipo -= 2000; } else if (tipo >= 1000) { z = true; tipo -= 1000; }
    const dim = 2 + (z ? 1 : 0) + (m ? 1 : 0);
    const anello = () => {
      const n = dv.getUint32(o, le); o += 4;
      const r = new Array(n);
      for (let i = 0; i < n; i++) {
        const x = dv.getFloat64(o, le), y = dv.getFloat64(o + 8, le);
        r[i] = z ? [x, y, dv.getFloat64(o + 16, le)] : [x, y];
        o += 8 * dim;
      }
      return r;
    };
    const poligono = () => { const n = dv.getUint32(o, le); o += 4; const p = []; for (let i = 0; i < n; i++) p.push(anello()); return p; };
    let out = [];
    if (tipo === 3) out = [poligono()];
    else if (tipo === 6 || tipo === 7 || tipo === 15) {
      const n = dv.getUint32(o, le); o += 4;
      for (let i = 0; i < n; i++) { const r = leggiWkb(dv, o); o = r.o; out = out.concat(r.poligoni); }
    } else if (tipo === 1) o += 8 * dim;
    else if (tipo === 2) { const n = dv.getUint32(o, le); o += 4 + n * 8 * dim; }
    else throw err(`geometria WKB di tipo ${tipo} non prevista`);
    return { poligoni: out, o };
  }
  // GeoPackage Binary: «GP», versione, flag (busta e ordine dei byte), srs_id, busta, poi WKB
  function leggiGpkgGeom(u8) {
    if (!u8 || u8.length < 8) return null;
    if (u8[0] !== 0x47 || u8[1] !== 0x50) return leggiWkb(new DataView(u8.buffer, u8.byteOffset, u8.byteLength), 0).poligoni;
    const flag = u8[3];
    if (flag & 0x10) return null;                                   // geometria vuota
    const busta = [0, 32, 48, 48, 64][(flag >> 1) & 7] || 0;
    const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
    return leggiWkb(dv, 8 + busta).poligoni;
  }

  // ---------------------------------------------------------------------------------------- Shapefile e DBF
  function leggiShp(u8) {
    const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
    if (u8.length < 100 || dv.getInt32(0, false) !== 9994) throw err("file .shp non valido");
    const tipoFile = dv.getInt32(32, true);
    if (![0, 5, 15, 25].includes(tipoFile)) throw err(`lo Shapefile non contiene poligoni (tipo ${tipoFile})`);
    const fine = Math.min(u8.length, dv.getInt32(24, false) * 2);
    const out = [];
    let o = 100;
    while (o + 8 <= fine) {
      const lung = dv.getInt32(o + 4, false) * 2;
      const c = o + 8;
      o = c + lung;
      if (o > u8.length) break;
      const tipo = dv.getInt32(c, true);
      if (tipo === 0) { out.push(null); continue; }
      if (![5, 15, 25].includes(tipo)) { out.push(null); continue; }
      const nParti = dv.getInt32(c + 36, true), nPunti = dv.getInt32(c + 40, true);
      if (nParti < 0 || nPunti < 0 || nParti > 1e6 || nPunti > 1e7) throw err("record dello Shapefile non valido");
      const parti = [];
      for (let i = 0; i < nParti; i++) parti.push(dv.getInt32(c + 44 + 4 * i, true));
      const p0 = c + 44 + 4 * nParti;
      const pti = new Array(nPunti);
      for (let i = 0; i < nPunti; i++) pti[i] = [dv.getFloat64(p0 + 16 * i, true), dv.getFloat64(p0 + 16 * i + 8, true)];
      if (tipo === 15) {
        const z0 = p0 + 16 * nPunti + 16;
        if (z0 + 8 * nPunti <= o) for (let i = 0; i < nPunti; i++) pti[i].push(dv.getFloat64(z0 + 8 * i, true));
      }
      const anelli = parti.map((s, i) => pti.slice(s, i + 1 < nParti ? parti[i + 1] : nPunti));
      out.push(poligoniDaAnelli(anelli));
    }
    return out;
  }
  function codificaDbf(ldid, cpg) {
    const c = String(cpg || "").trim().toUpperCase();
    if (/UTF-?8/.test(c)) return "utf-8";
    if (/1252|ANSI/.test(c)) return "windows-1252";
    if (/8859-?1|LATIN1/.test(c)) return "iso-8859-1";
    if (ldid === 0x57 || ldid === 0x03) return "windows-1252";
    return "iso-8859-1";                                             // come GDAL senza .cpg né codice di lingua
  }
  function leggiDbf(u8, cpg) {
    const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
    if (u8.length < 33) throw err("file .dbf non valido");
    const n = dv.getUint32(4, true), testa = dv.getUint16(8, true), lr = dv.getUint16(10, true);
    const dec = new TextDecoder(codificaDbf(u8[29], cpg));
    const campi = [];
    let o = 32, inizio = 1;
    while (o + 32 <= testa && u8[o] !== 0x0d) {
      let nome = ""; for (let i = 0; i < 11 && u8[o + i]; i++) nome += String.fromCharCode(u8[o + i]);
      campi.push({ nome, tipo: String.fromCharCode(u8[o + 11]), lung: u8[o + 16], dec: u8[o + 17], da: inizio });
      inizio += u8[o + 16];
      o += 32;
    }
    const righe = [];
    for (let k = 0; k < n; k++) {
      const b = testa + k * lr;
      if (b + lr > u8.length) break;
      const cancellato = u8[b] === 0x2a;
      const r = {};
      for (const c of campi) {
        const raw = u8.subarray(b + c.da, b + c.da + c.lung);
        let v = null;
        if (c.tipo === "C") { const t = dec.decode(raw).replace(/[\s\x00]+$/, ""); v = t === "" ? null : t; }
        else if (c.tipo === "N" || c.tipo === "F") {
          const t = new TextDecoder("latin1").decode(raw).trim();
          if (t && !/^\*+$/.test(t)) { const x = parseFloat(t); v = Number.isFinite(x) ? (c.dec === 0 && c.tipo === "N" ? Math.trunc(x) : x) : null; }
        } else if (c.tipo === "D") { const t = new TextDecoder("latin1").decode(raw).trim(); v = /^\d{8}$/.test(t) ? `${t.slice(0, 4)}-${t.slice(4, 6)}-${t.slice(6, 8)}` : null; }
        else if (c.tipo === "L") { const t = String.fromCharCode(raw[0] || 63).toUpperCase(); v = "TY".includes(t) ? 1 : "FN".includes(t) ? 0 : null; }
        else v = dec.decode(raw).trim() || null;
        r[c.nome] = v;
      }
      righe.push(cancellato ? null : r);
    }
    return { campi: campi.map((c) => c.nome), righe };
  }

  // ---------------------------------------------------------------------------------------- pacchetto
  const DATI = new Set([".gpkg", ".shp", ".shx", ".dbf", ".prj", ".cpg", ".geojson", ".json"]);
  const est = (n) => (String(n).match(/\.[^./\\]*$/) || [""])[0].toLowerCase();
  function nomeSicuro(nome) {
    if (String(nome).includes("\x00")) throw err("nome di file non valido nello zip");
    const n = String(nome).replace(/\\/g, "/");
    if (n.startsWith("/") || /^[A-Za-z]:/.test(n) || n.split("/").includes("..")) throw err(`percorso non ammesso nello zip: ${pulisci(nome, 80)}`);
    return n.split("/").filter((p) => p && p !== ".").join("/");
  }
  const testa = (u8, s) => s.every((c, i) => u8[i] === c);
  const GPKG = [0x53, 0x51, 0x4c, 0x69, 0x74, 0x65, 0x20, 0x66, 0x6f, 0x72, 0x6d, 0x61, 0x74, 0x20, 0x33, 0x00];
  // file dell'utente → mappa percorso → byte, con le regole di coda.py (percorsi, bombe, estensioni, uno zip annidato)
  function espandi(files, fflate, livello = 0, out = new Map(), conto = { tot: 0 }) {
    for (const f of files) {
      const u8 = f.dati instanceof Uint8Array ? f.dati : new Uint8Array(f.dati);
      const nome = nomeSicuro(f.nome);
      if (testa(u8, [0x50, 0x4b, 0x03, 0x04]) || testa(u8, [0x50, 0x4b, 0x05, 0x06])) {
        if (livello > 1) continue;
        if (!fflate) throw err("lettore zip non disponibile");
        let voci = 0;
        const dentro = fflate.unzipSync(u8, {
          filter: (v) => {
            if (++voci > LIMITI.MAX_VOCI) throw err(`troppe voci nello zip (oltre ${LIMITI.MAX_VOCI})`);
            const n = nomeSicuro(v.name);
            const e = est(n);
            if (!n || n.endsWith("/")) return false;
            if (!(DATI.has(e) || e === ".xml" || (e === ".zip" && livello < 1))) return false;
            conto.tot += v.originalSize;
            if (conto.tot > LIMITI.MAX_ESTRATTO) throw err("contenuto dello zip troppo grande una volta estratto (oltre 3 GB)");
            if (v.originalSize > 50 * 1024 * 1024 && v.size && v.originalSize / v.size > LIMITI.MAX_RAPPORTO)
              throw err(`compressione anomala nello zip (${pulisci(n, 60)}): file rifiutato`);
            return true;
          },
        });
        const sotto = Object.entries(dentro).map(([n, d]) => ({ nome: n, dati: d }));
        espandi(sotto, fflate, livello + 1, out, conto);
      } else if (testa(u8, GPKG)) out.set(est(nome) === ".gpkg" ? nome : `${nome}.gpkg`, u8);
      else if (DATI.has(est(nome)) || est(nome) === ".xml") out.set(nome, u8);
    }
    return out;
  }
  const base = (p) => p.replace(/\.[^./]*$/, "");
  const nomeFile = (p) => p.split("/").pop();

  // ---------------------------------------------------------------------------------------- sistemi di riferimento
  function sistema(definizione, codice) {
    const c = codice ? `EPSG:${codice}` : null;
    if (c && SISTEMI[c]) return { codice: c, def: SISTEMI[c] };
    const t = String(definizione || "");
    if (!t.trim()) return null;
    const m = t.match(/AUTHORITY\["EPSG",\s*"?(\d+)"?\]\s*\]\s*$/);
    if (m && SISTEMI[`EPSG:${m[1]}`]) return { codice: `EPSG:${m[1]}`, def: SISTEMI[`EPSG:${m[1]}`] };
    const s = t.replace(/\s+/g, "").toLowerCase();
    const zona = (s.match(/utm(?:_|-)?zone(?:_|-)?(\d\d)n/) || [])[1];
    if (zona && /(rdn2008|rete_dinamica|etrs|igm95|grs_?1980)/.test(s)) return { codice: zona === "32" ? "EPSG:7791" : "EPSG:6708", def: SISTEMI[zona === "32" ? "EPSG:7791" : "EPSG:6708"] };
    if (zona && /wgs_?84/.test(s)) return { codice: `EPSG:326${zona}`, def: SISTEMI[`EPSG:326${zona}`] };
    if (/monte_?mario/.test(s) && /gauss|tmerc|transverse/.test(s)) {
      const e = /1500000/.test(s) ? "EPSG:3003" : /2520000/.test(s) ? "EPSG:3004" : null;
      if (e) return { codice: e, def: SISTEMI[e] };
    }
    if (/^geogcs\[/.test(s) && /wgs_?(19)?84/.test(s)) return { codice: "EPSG:4326", def: SISTEMI["EPSG:4326"] };
    return { codice: null, def: t };                                // WKT generico: lo legge proj4js
  }
  function trasformatore(proj4, da, a) {
    if (!da || !a || da.def === a.def) return null;
    const t = proj4(da.def, a.def);
    return (q) => { const r = t.forward([q[0], q[1]]); return q.length > 2 ? [r[0], r[1], q[2]] : r; };
  }

  // ---------------------------------------------------------------------------------------- strati
  function strati(mappa, SQL) {
    const out = [];
    for (const [p, u8] of mappa) {
      if (est(p) !== ".gpkg") continue;
      if (!SQL) throw err("lettore GeoPackage non disponibile");
      let db;
      try { db = new SQL.Database(u8); } catch (e) { throw err("GeoPackage non leggibile"); }
      const q = (sql) => { const r = db.exec(sql); return r.length ? r[0].values.map((v) => Object.fromEntries(r[0].columns.map((c, i) => [c, v[i]]))) : []; };
      let cont;
      try { cont = q("SELECT table_name, data_type, srs_id FROM gpkg_contents"); } catch { db.close(); throw err("il file non è un GeoPackage (manca gpkg_contents)"); }
      const geomCol = Object.fromEntries(q("SELECT table_name, column_name FROM gpkg_geometry_columns").map((r) => [r.table_name, r.column_name]));
      const srs = Object.fromEntries(q("SELECT srs_id, organization, organization_coordsys_id, definition FROM gpkg_spatial_ref_sys").map((r) => [r.srs_id, r]));
      for (const c of cont) {
        const s = srs[c.srs_id] || {};
        out.push({ nome: String(c.table_name), file: p, tipo: "gpkg", db, colonnaGeom: geomCol[c.table_name] || null,
          sistema: sistema(s.definition, String(s.organization || "").toUpperCase() === "EPSG" ? s.organization_coordsys_id : null) });
      }
    }
    // Shapefile: .shp (+ .dbf, .prj, .cpg) per nome; .dbf da soli (tabelle come V_EDI_CT_USO_AVM)
    const gruppi = new Map();
    for (const p of mappa.keys()) {
      const e = est(p);
      if (![".shp", ".dbf", ".prj", ".cpg", ".shx"].includes(e)) continue;
      const k = base(p).toLowerCase();
      if (!gruppi.has(k)) gruppi.set(k, {});
      gruppi.get(k)[e.slice(1)] = p;
    }
    for (const [, g] of gruppi) {
      if (!g.dbf && !g.shp) continue;
      const nome = nomeFile(base(g.shp || g.dbf));
      const dec = new TextDecoder("latin1");
      out.push({ nome, file: g.shp || g.dbf, tipo: "shp", shp: g.shp ? mappa.get(g.shp) : null, dbf: g.dbf ? mappa.get(g.dbf) : null,
        cpg: g.cpg ? dec.decode(mappa.get(g.cpg)) : null, sistema: g.prj ? sistema(dec.decode(mappa.get(g.prj))) : null });
    }
    return out;
  }
  // righe di uno strato: [{p: proprietà, g: poligoni|null}]
  function righe(strato, conGeom = true) {
    if (strato.tipo === "gpkg") {
      const out = [];
      const st = strato.db.prepare(`SELECT * FROM "${strato.nome.replace(/"/g, '""')}"`);
      try {
        while (st.step()) {
          const o = st.getAsObject();
          const g = strato.colonnaGeom ? o[strato.colonnaGeom] : null;
          if (strato.colonnaGeom) delete o[strato.colonnaGeom];
          out.push({ p: o, g: conGeom && g instanceof Uint8Array ? leggiGpkgGeom(g) : null });
        }
      } finally { st.free(); }
      return out;
    }
    const d = strato.dbf ? leggiDbf(strato.dbf, strato.cpg) : { righe: [] };
    const gs = conGeom && strato.shp ? leggiShp(strato.shp) : [];
    const n = Math.max(d.righe.length, gs.length);
    const out = [];
    for (let i = 0; i < n; i++) {
      if (d.righe.length && d.righe[i] === null) continue;              // record cancellato nel DBF
      out.push({ p: d.righe[i] || {}, g: gs[i] || null });
    }
    return out;
  }
  // colonne di uno strato GeoPackage: la chiave primaria «id»/«fid» non è un attributo (pyogrio la toglie)
  function chiavePrimaria(strato) {
    if (strato.tipo !== "gpkg") return null;
    const r = strato.db.exec(`PRAGMA table_info("${strato.nome.replace(/"/g, '""')}")`);
    if (!r.length) return null;
    const pk = r[0].values.find((v) => v[5] === 1);
    return pk ? String(pk[1]) : null;
  }
  function righeSenzaChiave(strato, conGeom = true) {
    const pk = chiavePrimaria(strato);
    const rr = righe(strato, conGeom);
    if (pk) rr.forEach((r) => { delete r.p[pk]; });
    return rr;
  }

  // ============================================================================================ DBTR (uvl.py)
  const SOGLIA_ASSOLUTA = 1.0, BASE_COLLINA = 15.0, MIN_FALDA = 0.3;
  const USI = { 101: "residenziale", 705: "commerciale", 801: "capannone", 9: "capannone", 303: "scuola", 302: "ospedale",
    30102: "ospedale", 30101: "ospedale", 201: "uffici", 299: "uffici", 399: "uffici", 306: "uffici", 305: "uffici",
    100202: "palestra", 1002: "palestra", 100201: "palestra", 799: "commerciale" };
  const interoDi = (x) => Math.abs(x - Math.round(x)) < 0.005;

  function convenzione(proprieta) {
    let sopra = 0, sotto = 0;
    for (const p0 of proprieta) {
      const p = maiuscole(p0), hu = num(p.H_UVL), b = num(p.B_UVL);
      if (hu === null || hu <= 0 || b === null || b <= 0 || interoDi(hu)) continue;
      if (hu < b - SOGLIA_ASSOLUTA) sotto++; else if (hu > b + SOGLIA_ASSOLUTA) sopra++;
    }
    return sotto >= Math.max(5, 0.05 * (sopra + sotto)) ? "altezze" : "quote";
  }
  function altezze(p0, conv = "quote") {
    const p = maiuscole(p0), hu = num(p.H_UVL), b = num(p.B_UVL), hc = num(p.H_COLMO), tf = p.TIPO_FONTE;
    const da = !vuoto(tf) ? `, da ${tf}` : "";
    if (hu === null || hu <= 0) return { gronda: null, colmo: null, fonte: "DBTR senza altezza", tipo: "nessuna" };
    const intero = interoDi(hu);
    const rel = `DBTR H_UVL (altezza del corpo, ±3 m${da})`;
    let gronda, tipo, fonte;
    if (b === null || b <= 0 || conv === "altezze") { gronda = hu; tipo = "relativa"; fonte = rel; }
    else if (Math.abs(hu - b) <= SOGLIA_ASSOLUTA && (b >= BASE_COLLINA || !intero))
      return { gronda: null, colmo: null, fonte: "DBTR: H_UVL è una quota, non un'altezza", tipo: "nessuna" };
    else if (hu > b + SOGLIA_ASSOLUTA && (!intero || b >= BASE_COLLINA)) {
      gronda = r2(hu - b); tipo = "assoluta"; fonte = `DBTR H_UVL − B_UVL (quota del tetto meno quota della base${da})`;
    } else { gronda = hu; tipo = "relativa"; fonte = rel; }
    let colmo = null;
    if (hc && hc > 0 && tipo === "relativa") {
      const c = b && hc > b + gronda * 0.5 ? r2(hc - b) : r2(hc);
      if (gronda + MIN_FALDA <= c && c <= gronda + 25) {
        colmo = c;
        fonte += c !== r2(hc) ? "; colmo da H_COLMO − B_UVL" : "; colmo da H_COLMO";
      }
    }
    return { gronda, colmo, fonte, tipo };
  }
  // uvl.corpo_da: proprietà pubbliche come tessere.feature_da_corpi (EXTRA_PUBBLICI), sagoma nel sistema del file
  function corpoDbtr(p0, pol, edificio, conv) {
    const p = maiuscole(p0);
    if (!pol || !pol.length || areaPoligono(pol) < 1) return null;
    const a = altezze(p, conv);
    if (!a.gronda || a.gronda <= 0) return null;
    const q = num(p.QUALITA), base = num(p.B_UVL);
    const extra = { altezza_dbtr: a.tipo };
    let uso = null;
    if (edificio) {
      const e = maiuscole(edificio);
      for (const [ko, ki] of [["foglio", "FOGLIO"], ["numero", "NUMERO"], ["nome", "NOME"], ["tipo_edificio", "D_TY_EDI"], ["destinazione", "D_CT_USO"]]) {
        let v = e[ki];
        if (!vuoto(v) && !(ki === "FOGLIO" && num(v) === 0)) {
          v = String(v).trim();
          if (ki === "FOGLIO") v = String(Math.trunc(parseFloat(v)));
          if (v && v !== "Non assegnato") extra[ko] = v;
        }
      }
      const cu = num(e.CT_USO);
      uso = cu !== null ? USI[Math.trunc(cu)] || null : null;
    }
    return { id: String(p.ID_E || p.OBJECTID), edificio: String(p.EDI_ID_E || p.ID_E), sagoma: pol, quota_terreno: base,
      gronda: a.gronda, colmo: a.colmo, tetto: a.colmo ? "capanna" : "piano", falde: a.colmo ? 2 : 0, fonte_sagoma: REGIONI.er.fonte,
      licenza: "CC BY 4.0", fonte_altezza: a.fonte, qualita: q ? `DBTR qualità ${fmtG(q)}; altezza ±3 m` : "altezza ±3 m", uso, extra };
  }
  // ============================================================================================ plausibilità
  // Altezze del DBTR non plausibili → stima (07/11/2026): stessa regola, stesse soglie e stessa aritmetica di
  // fase10-edifici3d/edifici3d/plausibilita.py (il test di parità confronta i corpi cambiati).
  const PL = { SOGLIA_M: 30, MASSIMO_M: 150, SNELLEZZA: 8, AREA_M2: 30, RELATIVA: 3, RAGGIO_M: 100, VICINI_MAX_M: 40,
    CONTATTO_M: 3, CONTATTO_AREA_M2: 60, CONTATTO_SCARTO_M: 8, STIMA_MIN: 6, STIMA_MAX: 9,
    VERTICALI: ["culto", "campanile", "torre", "ciminiera", "industr", "impianto", "capannone", "serbatoio", "antenna", "faro", "inceneritore", "silo"],
    QUALITA: "altezza stimata (dato DBTR non plausibile)" };
  const INTERPIANI = { residenziale: 3.0, uffici: 3.4, scuola: 3.5, ospedale: 4.0, commerciale: 4.0, altro: 3.2 };
  const SOVRALZO = 0.3;
  const verticale = (d, t) => { const s = `${d || ""} ${t || ""}`.toLowerCase(); return PL.VERTICALI.some((v) => s.includes(v)); };
  function inviluppo(punti) {
    const visti = new Set(), p = [];
    for (const q of punti) { const k = `${+q[0]},${+q[1]}`; if (!visti.has(k)) { visti.add(k); p.push([+q[0], +q[1]]); } }
    p.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    if (p.length < 3) return p;
    const giro = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
    const sotto = [], sopra = [];
    for (const q of p) { while (sotto.length >= 2 && giro(sotto[sotto.length - 2], sotto[sotto.length - 1], q) <= 0) sotto.pop(); sotto.push(q); }
    for (let i = p.length - 1; i >= 0; i--) { const q = p[i]; while (sopra.length >= 2 && giro(sopra[sopra.length - 2], sopra[sopra.length - 1], q) <= 0) sopra.pop(); sopra.push(q); }
    return sotto.slice(0, -1).concat(sopra.slice(0, -1));
  }
  function larghezzaMinima(anello) {
    const h = inviluppo(anello);
    if (h.length < 3) return 0;
    let m = Infinity;
    for (let i = 0; i < h.length; i++) {
      const [ax, ay] = h[i], [bx, by] = h[(i + 1) % h.length];
      const lx = bx - ax, ly = by - ay, l = Math.hypot(lx, ly);
      if (l === 0) continue;
      const nx = -ly / l, ny = lx / l;
      let lo = Infinity, hi = -Infinity;
      for (const [x, y] of h) { const v = (x - ax) * nx + (y - ay) * ny; if (v < lo) lo = v; if (v > hi) hi = v; }
      m = Math.min(m, hi - lo);
    }
    return m === Infinity ? 0 : m;
  }
  const medianaDi = (v) => { const s = v.slice().sort((a, b) => a - b), n = s.length; return n ? (n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2) : null; };
  const mezzoMetro = (x) => Math.floor(x * 2 + 0.5) / 2;
  const testoMetri = (x) => { const v = Math.floor(x * 10 + 0.5) / 10; return (v === Math.trunc(v) ? String(Math.trunc(v)) : v.toFixed(1)).replace(".", ","); };
  function stimaUso(uso) {
    if (["capannone", "palestra", "industriale"].includes(uso)) return 8.0;
    const v = 2 * (INTERPIANI[uso || "altro"] !== undefined ? INTERPIANI[uso || "altro"] : INTERPIANI.altro) + SOVRALZO;
    return Math.min(PL.STIMA_MAX, Math.max(PL.STIMA_MIN, Math.floor(v * 10 + 0.5) / 10));
  }
  // corpi del DBTR (sistema metrico della zona): porta alla stima quelli non plausibili; restituisce i cambiati
  function plausibilita(corpi) {
    const el = corpi.map((c) => { const r = c.sagoma[0]; const anello = r.slice(0, r.length - 1);
      return { anello, area: areaPoligono(c.sagoma), gronda: c.gronda, destinazione: c.extra.destinazione, tipo: c.extra.tipo_edificio, uso: c.uso }; });
    const riq = el.map((e) => { let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      for (const [x, y] of e.anello) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; } return [x0, y0, x1, y1]; });
    const cen = riq.map((r) => [(r[0] + r[2]) / 2, (r[1] + r[3]) / 2]);
    const candidati = [];
    el.forEach((e, i) => {
      const h = e.gronda;
      if (h === null || h === undefined || h <= PL.SOGLIA_M || verticale(e.destinazione, e.tipo)) return;
      if (h > PL.MASSIMO_M || h / Math.max(larghezzaMinima(e.anello), 0.5) > PL.SNELLEZZA) candidati.push(i);
    });
    if (!candidati.length) return [];
    const R = PL.RAGGIO_M, griglia = new Map();
    cen.forEach(([x, y], j) => { const k = `${Math.floor(x / R)},${Math.floor(y / R)}`; if (!griglia.has(k)) griglia.set(k, []); griglia.get(k).push(j); });
    const vicini = (i) => {
      const [x, y] = cen[i], gx = Math.floor(x / R), gy = Math.floor(y / R), out = [];
      for (const dx of [-1, 0, 1]) for (const dy of [-1, 0, 1]) for (const j of griglia.get(`${gx + dx},${gy + dy}`) || [])
        if (j !== i && (cen[j][0] - x) ** 2 + (cen[j][1] - y) ** 2 <= R ** 2) out.push(j);
      return out.sort((a, b) => a - b);
    };
    const gr = (j) => el[j].gronda || 0;
    const scarti = new Map();
    for (const i of candidati) {
      const h = el[i].gronda, vv = vicini(i);
      if (h > PL.MASSIMO_M) { scarti.set(i, vv); continue; }
      const r = riq[i];
      const tocca = vv.some((j) => el[j].area >= PL.CONTATTO_AREA_M2 && gr(j) >= h - PL.CONTATTO_SCARTO_M
        && riq[j][0] <= r[2] + PL.CONTATTO_M && riq[j][2] >= r[0] - PL.CONTATTO_M && riq[j][1] <= r[3] + PL.CONTATTO_M && riq[j][3] >= r[1] - PL.CONTATTO_M);
      if (tocca) continue;
      const m = medianaDi(vv.filter((j) => gr(j) > 0 && gr(j) <= PL.VICINI_MAX_M).map(gr));
      if (el[i].area < PL.AREA_M2 || m === null || h > PL.RELATIVA * m) scarti.set(i, vv);
    }
    const cambi = [];
    for (const i of [...scarti.keys()].sort((a, b) => a - b)) {
      const vv = scarti.get(i), c = corpi[i], h0 = el[i].gronda;
      const m = medianaDi(vv.filter((j) => !scarti.has(j) && gr(j) > 0 && gr(j) <= PL.VICINI_MAX_M).map(gr));
      const stima = m !== null ? Math.max(2.0, mezzoMetro(m)) : stimaUso(el[i].uso);
      c.extra = Object.assign({}, c.extra, { h_dbtr_scartata: r2(h0), stima_altezza: m !== null ? "vicini" : "uso" });
      c.gronda = stima; c.colmo = null; c.tetto = "piano"; c.falde = 0;
      c.fonte_altezza = `stima: altezza DBTR non plausibile (${testoMetri(h0)} m)`;
      c.qualita = PL.QUALITA;
      cambi.push({ id: c.id, foglio: c.extra.foglio || null, numero: c.extra.numero || null, h_dbtr: c.extra.h_dbtr_scartata, stima });
    }
    return cambi;
  }

  // uvl.controlla (le voci che la pagina mostra e che il test di parità confronta)
  function controllaUvl(proprieta) {
    const pp = proprieta.map(maiuscole);
    const conv = convenzione(pp);
    const alt = pp.map((p) => num(p.H_UVL)).filter((a) => a !== null && a > 0).sort((x, y) => x - y);
    const tipi = {}; let colmi = 0; const gronde = [];
    for (const p of pp) {
      const a = altezze(p, conv);
      tipi[a.tipo] = (tipi[a.tipo] || 0) + 1;
      if (a.colmo) colmi++;
      if (a.gronda) gronde.push(a.gronda);
    }
    gronde.sort((x, y) => x - y);
    const g = gronde;
    return { corpi: pp.length, edifici: new Set(pp.map((p) => p.EDI_ID_E === undefined ? null : p.EDI_ID_E)).size, convenzione: conv,
      altezza: { conteggio: alt.length, min: alt.length ? alt[0] : null, max: alt.length ? alt[alt.length - 1] : null,
        mediana: alt.length ? alt[Math.floor(alt.length / 2)] : null, interi: alt.filter(interoDi).length },
      gronda: { conteggio: g.length, mediana: g.length ? g[Math.floor(g.length / 2)] : null, p95: g.length ? g[Math.floor(g.length * 0.95)] : null,
        max: g.length ? g[g.length - 1] : null },
      tipi_altezza: tipi, colmi };
  }

  // ============================================================================================ altre regioni (regionali.py)
  const TRONCATI = Object.fromEntries(["CLASSID", "CEDIUV", "UN_VOL_AV", "UN_VOL_QE", "UN_VOL_POR", "ID", "ALTEZZA", "QUOTA_PIEDE",
    "QUOTA_GRONDA", "VOLUME", "CODICE", "NOME", "id", "def_tipo_edil", "def_cat_uso", "def_sotterr", "def_stato", "def_porz_est", "ogr_fid"]
    .filter((n) => n.length > 10).map((n) => [n.slice(0, 10), n]));
  function nomiCompleti(p) {
    if (!Object.keys(p).some((k) => TRONCATI[k])) return p;
    const o = {};
    for (const k of Object.keys(p)) { const n = TRONCATI[k] && !(TRONCATI[k] in p) ? TRONCATI[k] : k; o[n] = p[k]; }
    return o;
  }
  const ADATTATORI = {
    lom: { campi: ["CLASSID", "CEDIUV", "UN_VOL_AV", "UN_VOL_QE", "UN_VOL_POR"], serveDtm: false,
      corpo(p, g, z) {
        let h = numero(p.UN_VOL_AV);
        const qe = numero(p.UN_VOL_QE);
        if ((h === null || h <= 0) && qe !== null && z !== null) h = qe - z;
        if (!h || h <= 0 || areaPoligono(g) < 1) return null;
        const base = qe !== null ? qe - h : z;
        return { id: String(p.CLASSID || p.OBJECTID), edificio: String(p.CEDIUV || p.CLASSID || p.OBJECTID), sagoma: g, quota_terreno: base,
          gronda: h, colmo: null, tetto: "piano", falde: 0, fonte_sagoma: REGIONI.lom.fonte, licenza: "CC BY 4.0",
          fonte_altezza: "DBGT Lombardia UN_VOL_AV (gronda o colmo da verificare)", qualita: "DBGT, altezza ±1–2 m (scala 1:2000)", uso: null, extra: {} };
      } },
    fvg: { campi: ["ID", "ALTEZZA", "QUOTA_PIEDE", "QUOTA_GRONDA", "NOME"], serveDtm: false,
      corpo(p, g) {
        let h = numero(p.ALTEZZA);
        const piede = numero(p.QUOTA_PIEDE), gr = numero(p.QUOTA_GRONDA);
        if ((h === null || h <= 0) && piede !== null && gr !== null) h = gr - piede;
        if (!h || h <= 0 || areaPoligono(g) < 1) return null;
        const nomeOrig = String(p.NOME || "").trim(), nome = nomeOrig.toUpperCase();
        const uso = nome.includes("CIVIL") ? "residenziale" : ["INDUSTR", "CAPANN"].some((k) => nome.includes(k)) ? "capannone" : null;
        return { id: String(p.ID === undefined ? null : p.ID), edificio: String(p.ID === undefined ? null : p.ID), sagoma: g, quota_terreno: piede,
          gronda: h, colmo: null, tetto: "piano", falde: 0, fonte_sagoma: REGIONI.fvg.fonte, licenza: "CC BY 4.0",
          fonte_altezza: "CTRN FVG ALTEZZA (QUOTA_GRONDA − QUOTA_PIEDE)", qualita: "CTRN 1:5000, altezza ±1–2 m", uso, extra: { nome: nomeOrig } };
      } },
    lig: { campi: ["id", "def_tipo_edil", "def_cat_uso", "def_sotterr", "def_stato", "def_porz_est"], serveDtm: true, corpo: () => null },
  };
  // regionali._poligono: parte più grande, z media del contorno esterno, sagoma 2D (con i fori)
  function poligono2d(pols) {
    const g = piuGrande(pols);
    if (!g) return { g: null, z: null };
    const zs = g[0].filter((c) => c.length > 2).map((c) => c[2]);
    return { g: g.map((r) => r.map((c) => [c[0], c[1]])), z: zs.length ? zs.reduce((s, x) => s + x, 0) / zs.length : null };
  }

  // ============================================================================================ uscita
  function feature(c, verso) {
    const sag = c.sagoma.map((r) => r.map((q) => { const w = verso ? verso(q) : q; return [r7(w[0]), r7(w[1])]; }));
    const p = { id: c.id, edificio: c.edificio, quota_terreno: c.quota_terreno, gronda: c.gronda, colmo: c.colmo, tetto: c.tetto,
      falde: c.falde, piani: null, fonte_sagoma: c.fonte_sagoma, licenza: c.licenza, fonte_altezza: c.fonte_altezza, qualita: c.qualita,
      uso: c.uso, area: r1(areaPoligono(c.sagoma)), altezza: r2(c.colmo ? c.colmo : c.gronda) };
    for (const k of ["foglio", "numero", "nome", "destinazione", "tipo_edificio", "altezza_dbtr", "h_dbtr_scartata", "stima_altezza"]) {
      const v = c.extra[k];
      if ((typeof v === "string" || typeof v === "number") && v !== "") p[k] = v;
    }
    for (const k of Object.keys(p)) if (p[k] === null || p[k] === undefined || p[k] === "") delete p[k];
    return { type: "Feature", id: c.id, geometry: { type: "Polygon", coordinates: sag }, properties: p };
  }
  const quantile = (a, q) => (a.length ? a[Math.min(a.length - 1, Math.floor(a.length * q))] : null);

  // dati personali: nomi di colonna e valori (codici fiscali, email) su un campione, come coda._dati_personali
  const PERSONALI = /^(cognome|nominativ|intestat|propriet|cod(ice)?_?fisc|c_?f$|cf$|partita_?iva|p_?iva|e_?mail|telefon|cellulare|titolare|possessor|residen|nato_|data_?nascita)/i;
  const CF = /\b[A-Z]{6}\d{2}[A-EHLMPR-T]\d{2}[A-Z]\d{3}[A-Z]\b/, EMAIL = /\b[\w.+-]+@[\w-]+\.[\w.]+\b/;
  function datiPersonali(nome, campione) {
    const out = [];
    const colonne = new Set(); campione.forEach((r) => Object.keys(r.p).forEach((k) => colonne.add(k)));
    for (const c of colonne) {
      if (PERSONALI.test(c)) out.push(`${nome}.${c}: nome di colonna da dato personale`);
      const testi = campione.map((r) => r.p[c]).filter((v) => typeof v === "string");
      if (testi.some((t) => CF.test(t))) out.push(`${nome}.${c}: valori che sembrano codici fiscali`);
      else if (testi.some((t) => EMAIL.test(t))) out.push(`${nome}.${c}: valori che sembrano indirizzi email`);
    }
    return out;
  }

  /**
   * files: [{nome, dati: Uint8Array|ArrayBuffer}] (zip, GeoPackage o le parti di uno Shapefile); regione: er|lom|fvg|lig.
   * lib: {fflate, SQL (sql.js già inizializzato), proj4}. Restituisce {features, sintesi}.
   */
  function leggi(files, regione, lib, stato = () => {}) {
    const R = REGIONI[regione];
    if (!R) throw err("regione non prevista");
    let tot = 0; files.forEach((f) => { tot += f.dati.byteLength; });
    if (tot > LIMITI.MAX_MB * 1024 * 1024) throw err(`file di ${Math.round(tot / 1048576)} MB: al massimo ${LIMITI.MAX_MB} MB`);
    stato("Apro il file…");
    const mappa = espandi(files, lib.fflate);
    const tutti = strati(mappa, lib.SQL);
    const avvisi = [], scarti = {};
    const conta = (k) => { scarti[k] = (scarti[k] || 0) + 1; };
    const zona = { codice: R.crs, def: SISTEMI[R.crs] };
    const wgs = { codice: "EPSG:4326", def: SISTEMI["EPSG:4326"] };
    let corpi = [], controllo = null, sorg = null, personali = [], comuni = [], stimate = [];
    try {
      if (regione === "er") {
        sorg = tutti.find((s) => ["V_UVL_GPG", "UVL_Unita_volumetrica", "UVL_GPG"].includes(s.nome) && (s.tipo === "gpkg" || s.shp))
          || null;
        if (!sorg) throw err("manca lo strato delle unità volumetriche V_UVL_GPG (nel GeoPackage o come V_UVL_GPG.shp con .dbf)");
        if (!sorg.sistema || !UTM32.includes(sorg.sistema.codice)) {
          throw err(`sistema di riferimento inatteso${sorg.sistema && sorg.sistema.codice ? ` (${sorg.sistema.codice})` : sorg.tipo === "shp" ? " (manca il file .prj?)" : ""}: il DBTR è in EPSG:7791 (RDN2008 / UTM 32N)`);
        }
        stato("Leggo le unità volumetriche…");
        const rr = righeSenzaChiave(sorg);
        const colonne = new Set(); rr.slice(0, 50).forEach((r) => Object.keys(maiuscole(r.p)).forEach((k) => colonne.add(k)));
        const mancanti = ["ID_E", "EDI_ID_E", "H_UVL", "B_UVL"].filter((c) => !colonne.has(c));
        if (mancanti.length) throw err(`colonne mancanti in V_UVL_GPG: ${mancanti.join(", ")}`);
        if (rr.length > LIMITI.MAX_CORPI) throw err(`troppi corpi (${rr.length}): nel browser al massimo ${LIMITI.MAX_CORPI}`);
        const sEdi = tutti.find((s) => s.nome === "V_EDI_GPG"), sUso = tutti.find((s) => s.nome === "V_EDI_CT_USO_AVM");
        const edifici = new Map();
        if (sEdi) {
          stato("Leggo gli edifici…");
          for (const r of righeSenzaChiave(sEdi, false)) if (r.p.ID_E) edifici.set(String(r.p.ID_E), r.p);
          if (sUso) for (const r of righeSenzaChiave(sUso, false)) {
            const e = edifici.get(String(r.p.ID_E));
            if (e) { e.CT_USO = r.p.CT_USO; e.D_CT_USO = r.p.D_CT_USO; }
          }
          comuni = [...new Set([...edifici.values()].map((e) => e.COD_COM).filter(Boolean).map(String))].sort().slice(0, 20);
          personali = personali.concat(datiPersonali("V_EDI_GPG", [...edifici.values()].slice(0, 3000).map((p) => ({ p }))));
        } else avvisi.push("manca lo strato Edificio (V_EDI_GPG): niente foglio, numero, nome e destinazione");
        if (sEdi && !sUso) avvisi.push("manca la destinazione d'uso (V_EDI_CT_USO_AVM)");
        personali = personali.concat(datiPersonali("V_UVL_GPG", rr.slice(0, 3000)));
        controllo = controllaUvl(rr.map((r) => r.p));
        const conv = controllo.convenzione;
        stato(`Ricavo i corpi (${rr.length.toLocaleString("it-IT")} unità volumetriche, convenzione «${conv}»)…`);
        for (const r of rr) {
          if (!r.g) continue;                                         // come _corpi_uvl: senza geometria, saltata
          const pol = piuGrande(r.g);
          if (pol && nonValido(pol)) conta("geometria non valida (non riparata nel browser)");
          const pm = maiuscole(r.p);
          const e = edifici.get(String(pm.EDI_ID_E || pm.Edi_id_e || ""));
          const c = corpoDbtr(r.p, pol, e, conv);
          if (c) corpi.push(c);
          else conta(!pol || areaPoligono(pol) < 1 ? "geometria vuota o sotto 1 m²" : "senza altezza utilizzabile (H_UVL ≤ 0 o quota)");
        }
        stimate = plausibilita(corpi);                               // come _corpi_uvl (plausibilita.applica)
      } else {
        const ad = ADATTATORI[regione];
        if (ad.serveDtm) throw err("le altezze della CTR 3D ligure si ricavano dal DTM regionale, che il browser non può scaricare: "
          + "proponi il file all'archivio comune (sotto) o usa il comando prepara-regione sul PC");
        const conGeom = tutti.filter((s) => s.tipo === "gpkg" ? s.colonnaGeom : s.shp);
        if (!conGeom.length) throw err("nessuno strato con geometrie nel file");
        // lo strato con le colonne dell'adattatore (il più grande se più d'uno)
        let migliore = null, punti = -1;
        for (const s of conGeom) {
          const rr = righeSenzaChiave(s);
          const col = new Set(); rr.slice(0, 50).forEach((r) => Object.keys(nomiCompleti(r.p)).forEach((k) => col.add(k)));
          const pt = ad.campi.filter((c) => col.has(c)).length * 1e7 + rr.length;
          if (pt > punti) { punti = pt; migliore = { s, rr, col }; }
        }
        sorg = migliore.s;
        const mancanti = ad.campi.filter((c) => !migliore.col.has(c));
        if (mancanti.length === ad.campi.length) throw err(`colonne attese mancanti per ${R.fonte}: ${mancanti.join(", ")}`);
        if (mancanti.length) avvisi.push(`colonne attese mancanti: ${mancanti.join(", ")}`);
        if (!sorg.sistema) throw err("il file non dichiara il sistema di riferimento (manca il .prj?)");
        personali = personali.concat(datiPersonali(sorg.nome, migliore.rr.slice(0, 3000)));
        const verso = trasformatore(lib.proj4, sorg.sistema, zona);
        stato(`Ricavo i corpi (${migliore.rr.length.toLocaleString("it-IT")} elementi)…`);
        for (const r0 of migliore.rr) {
          const p = nomiCompleti(r0.p);
          if (!r0.g) { conta("senza geometria"); continue; }
          let { g, z } = poligono2d(r0.g);
          if (!g) { conta("geometria non poligonale"); continue; }
          if (verso) g = g.map((r) => r.map(verso));
          const c = ad.corpo(p, g, z);
          if (!c) { conta("altezza assente o non valida, o elemento escluso"); continue; }
          corpi.push(c);
        }
        controllo = { letti: migliore.rr.length, corpi: corpi.length, scarti };
      }
    } finally {
      tutti.forEach((s) => { if (s.db) { try { s.db.close(); } catch { /* già chiuso */ } s.db = null; } });
    }
    if (!corpi.length) throw err("nessun corpo con altezza utilizzabile nel file");
    stato("Riproietto in WGS84…");
    const verso = trasformatore(lib.proj4, zona, wgs);
    const features = corpi.map((c) => feature(c, verso));
    // riepilogo
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const f of features) for (const q of f.geometry.coordinates[0]) { if (q[0] < x0) x0 = q[0]; if (q[0] > x1) x1 = q[0]; if (q[1] < y0) y0 = q[1]; if (q[1] > y1) y1 = q[1]; }
    const riquadro = [x0, y0, x1, y1].map((v) => Math.round(v * 1e6) / 1e6);
    const g = features.map((f) => f.properties.gronda).sort((a, b) => a - b);
    const rz = R.riquadro, m = 0.05;
    const dentro = riquadro[0] >= rz[0] - m && riquadro[1] >= rz[1] - m && riquadro[2] <= rz[2] + m && riquadro[3] <= rz[3] + m;
    if (!dentro) avvisi.push(`il riquadro dei dati esce dalla regione scelta (${R.nome}): controlla la regione`);
    const oltre60 = g.filter((x) => x > 60).length;
    if (oltre60 > Math.max(5, g.length * 0.001)) avvisi.push(`${oltre60} corpi oltre 60 m: controllare (quote non riconosciute?)`);
    // altezze non plausibili portate alla stima (plausibilita, 07/11/2026); i corpi piccoli e altissimi rimasti (campanili,
    // ciminiere, torri: tipi verticali) restano solo segnalati
    if (stimate.length) avvisi.push(`${stimate.length} corpi con altezza del DB topografico non plausibile portati alla stima (es. ${stimate.slice(0, 3)
      .map((x) => `${testoMetri(x.h_dbtr)} → ${testoMetri(x.stima)} m${x.foglio ? `, foglio ${x.foglio} numero ${x.numero}` : ""}`).join("; ")})`);
    const sospetti = features.filter((f) => f.properties.area < 30 && f.properties.gronda > 40 && f.properties.h_dbtr_scartata === undefined)
      .map((f) => ({ id: f.properties.id, area: f.properties.area, gronda: f.properties.gronda, foglio: f.properties.foglio || null, numero: f.properties.numero || null }));
    if (sospetti.length) avvisi.push(`${sospetti.length} corpi sotto 30 m² e oltre 40 m di tipo verticale (campanili, torri, ciminiere): da guardare (es. ${sospetti.slice(0, 3)
      .map((x) => `${x.area} m², ${x.gronda} m${x.foglio ? `, foglio ${x.foglio} numero ${x.numero}` : ""}`).join("; ")})`);
    if (personali.length) avvisi.push(`possibili dati personali nel file: ${personali.slice(0, 3).join("; ")}`);
    const scartati = Object.values(scarti).reduce((s, x) => s + x, 0) - (scarti["geometria non valida (non riparata nel browser)"] || 0);
    const sintesi = { regione, fonte: R.fonte, licenza: R.licenza, attribuzione: R.attribuzione, sperimentale: R.sperimentale,
      sorgente: sorg ? { tipo: sorg.tipo, nome: sorg.nome, sistema: sorg.sistema && sorg.sistema.codice } : null,
      corpi: features.length, edifici: new Set(features.map((f) => f.properties.edificio)).size, scartati, scarti,
      convenzione: controllo && controllo.convenzione || null, controllo, riquadro, dentro_regione: dentro,
      gronda_m: { mediana: quantile(g, 0.5), p95: quantile(g, 0.95), max: g.length ? g[g.length - 1] : null },
      a_capanna: features.filter((f) => f.properties.colmo).length,
      con_cortile: features.filter((f) => f.geometry.coordinates.length > 1).length,
      con_foglio_numero: features.filter((f) => f.properties.foglio && f.properties.numero).length,
      con_destinazione: features.filter((f) => f.properties.destinazione).length,
      comuni_catastali: comuni, dati_personali: personali, sospetti: sospetti.slice(0, 20), altezze_stimate: stimate.length,
      stimate: stimate.slice(0, 20), avvisi,
      terreno: "quote dei corpi dalla base del DB topografico (nessun DTM nel browser); terreno della vista 3D dal server" };
    return { features, sintesi };
  }

  return { LIMITI, REGIONI, SISTEMI, DbtrNonValido, leggi, espandi, strati, righe, leggiShp, leggiDbf, leggiGpkgGeom, sistema,
    convenzione, altezze, controllaUvl, numero, areaPoligono, poligoniDaAnelli, nomiCompleti, pulisci, plausibilita, larghezzaMinima, PL };
});
