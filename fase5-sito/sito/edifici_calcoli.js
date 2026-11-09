"use strict";
// Calcoli degli edifici 3D (fase 10, Fase A), senza DOM: li usano le pagine (edificio3d.js, consumi_edificio.js,
// valori_sedi.js) e il Web Worker delle ombre (ombre_worker.js). Le regole su piani e superfici sono le stesse di
// fase10-edifici3d/edifici3d/modello.py (un test controlla che interpiani e rapporti coincidano).
//
//  Piani e superfici (§ 8): stimaPiani, scegli (CSV → visura → stima), superfici, colonne facoltative di Patrimonio
//  Geometria (§ 9, analisi 1): area, indicatori (volume, S/V, pareti per orientamento e in comune), dividi (linea);
//  corpi con i fori (07/11/2026): c.buchi, areaCorpo, dentroCorpo, latiCorpo (pareti dei cortili comprese)
//  Sole e ombre: sole (posizione NOAA), ombra (sagoma proiettata sul terreno), orizzonte (profilo per un punto, 72
//  direzioni), svf (fattore di vista del cielo)
//  FV (§ 9, analisi 6): trasponi (Perez 1990 dal 05/11/2026, isotropo a richiesta), producibilita (tipo PVWatts,
//  perdite 14 %, temperatura celle)
//  Firma energetica (§ 9, analisi 3): firma (minimi quadrati consumo ↔ gradi giorno)
//  Nessun coefficiente delle norme UNI: sono grandezze geometriche e modelli solari di letteratura aperta.
(function (radice) {
  const INTERPIANI = { residenziale: 3.0, uffici: 3.4, scuola: 3.5, ospedale: 4.0, commerciale: 4.0, altro: 3.2 };
  const UN_PIANO = new Set(["capannone", "palestra", "industriale"]);
  const SOVRALZO = 0.3, NETTA_SU_LORDA = 0.82, TOLLERANZA_COMUNE = 0.25;
  const SETTORI = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"];
  const GRAD = Math.PI / 180;

  // ------------------------------------------------------------------ numeri e colonne
  function numero(v) {
    if (v === null || v === undefined || typeof v === "boolean") return null;
    if (typeof v === "number") return Number.isFinite(v) ? v : null;
    let s = String(v).trim().replace(/\s/g, "");
    if (!s) return null;
    if (s.includes(",")) s = s.replace(/\./g, "").replace(",", ".");
    if (!/^[-+]?(\d+\.?\d*|\.\d+)(e[-+]?\d+)?$/i.test(s)) return null;
    const x = Number(s);
    return Number.isFinite(x) ? x : null;
  }
  const norm = (c) => String(c).trim().toLowerCase().replace(/["']/g, "").replace(/[^a-z0-9àèéìòù_]/g, "_").replace(/_+/g, "_").replace(/^_+|_+$/g, "");
  // colonne facoltative del CSV di Patrimonio (§ 8), con i nomi alternativi accettati; l'unità tra parentesi si ignora
  const FACOLTATIVE = {
    piani_fuori_terra: ["piani_fuori_terra", "piani", "n_piani", "numero_piani", "piani_ft", "piani_f_t"],
    piani_interrati: ["piani_interrati", "interrati", "piani_entro_terra", "n_interrati"],
    superficie_lorda: ["superficie_lorda", "sup_lorda", "slp", "superficie_lorda_di_pavimento"],
    superficie_netta: ["superficie_netta", "sup_netta", "superficie_utile", "superficie_utile_netta"],
    superficie_catastale: ["superficie_catastale", "sup_catastale"],
    anno_costruzione: ["anno_costruzione", "anno_di_costruzione", "anno_costr", "epoca_costruzione"],
  };
  const ETICHETTE = { piani_fuori_terra: "Piani fuori terra", piani_interrati: "Piani interrati", superficie_lorda: "Superficie lorda",
    superficie_netta: "Superficie netta", superficie_catastale: "Superficie catastale", anno_costruzione: "Anno di costruzione" };
  function colonnaFacoltativa(titolo) {
    const k = norm(String(titolo).replace(/\s*[([][^()[\]]*[)\]]\s*$/, ""));
    for (const [std, alias] of Object.entries(FACOLTATIVE)) if (alias.includes(k)) return std;
    return null;
  }
  // { indice di colonna: nome standard } delle colonne facoltative presenti tra i titoli
  function mappaFacoltative(titoli) {
    const m = {}, visti = new Set();
    titoli.forEach((t, i) => { const s = colonnaFacoltativa(t); if (s && !visti.has(s)) { m[i] = s; visti.add(s); } });
    return m;
  }
  function leggiFacoltative(mappa, celle) {
    const o = {};
    for (const [i, s] of Object.entries(mappa)) { const v = numero(celle[i]); if (v !== null && v > 0) o[s] = v; }
    return o;
  }

  // ------------------------------------------------------------------ piani e superfici (§ 8)
  function usoDa(categoria, osm, dichiarato) {
    if (dichiarato) return String(dichiarato).trim().toLowerCase();
    const CAT = { "A/10": "uffici", "B/2": "ospedale", "B/4": "uffici", "B/5": "scuola", "C/1": "commerciale", "D/1": "capannone",
      "D/4": "ospedale", "D/7": "capannone", "D/8": "commerciale", "C/2": "capannone", "C/3": "capannone" };
    if (categoria) {
      const c = String(categoria).toUpperCase().replace(/\s/g, "");
      if (CAT[c]) return CAT[c];
      if (c[0] === "A") return "residenziale";
    }
    const OSM = { house: "residenziale", apartments: "residenziale", residential: "residenziale", office: "uffici", school: "scuola",
      hospital: "ospedale", retail: "commerciale", commercial: "commerciale", industrial: "capannone", warehouse: "capannone" };
    return OSM[String(osm || "").toLowerCase()] || "altro";
  }
  function stimaPiani(gronda, uso = "altro") {
    if (UN_PIANO.has(uso)) return 1;
    if (!Number.isFinite(gronda) || gronda <= 0) return 1;
    return Math.max(1, Math.round((gronda - SOVRALZO) / (INTERPIANI[uso] || INTERPIANI.altro)));
  }
  function scegli(csv, visura, stima) {
    const nomi = ["csv", "visura", "stima"];
    const v = [csv, visura, stima];
    for (let i = 0; i < 3; i++) { const n = numero(v[i]); if (n !== null && n > 0) return { valore: n, fonte: nomi[i] }; }
    return { valore: null, fonte: "mancante" };
  }
  // corpi: [{ ring, gronda, piani, uso }]; csv, visura: oggetti con le colonne facoltative
  function superfici(corpi, csv = {}, visura = {}) {
    let lorda = 0, pmax = 0;
    const perCorpo = corpi.map((c) => {
      const p = c.piani || stimaPiani(c.gronda, c.uso || "altro");
      lorda += areaCorpo(c) * p; pmax = Math.max(pmax, p);
      return { corpo: c.id, piani: p, fonte: c.piani ? "dato del corpo" : "stima" };
    });
    const l = scegli(csv.superficie_lorda, visura.superficie_lorda, lorda || null);
    return {
      piani_fuori_terra: scegli(csv.piani_fuori_terra, visura.piani_fuori_terra, pmax || null),
      piani_interrati: scegli(csv.piani_interrati, visura.piani_interrati, null),
      superficie_lorda: l,
      superficie_netta: scegli(csv.superficie_netta, visura.superficie_netta, l.valore ? l.valore * NETTA_SU_LORDA : null),
      superficie_catastale: scegli(csv.superficie_catastale, visura.superficie_catastale, null),
      anno_costruzione: scegli(csv.anno_costruzione, visura.anno_costruzione, null),
      per_corpo: perCorpo,
    };
  }

  // ------------------------------------------------------------------ geometria piana (anelli [[x, y], …] in metri)
  function chiudi(r) { return r.length && (r[0][0] !== r[r.length - 1][0] || r[0][1] !== r[r.length - 1][1]) ? [...r, r[0]] : r; }
  function areaConSegno(r) {
    r = chiudi(r); let s = 0;
    for (let i = 0; i < r.length - 1; i++) s += r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1];
    return s / 2;
  }
  const area = (r) => Math.abs(areaConSegno(r));
  function centroide(r) {
    r = chiudi(r); let a = 0, x = 0, y = 0;
    for (let i = 0; i < r.length - 1; i++) {
      const f = r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1];
      a += f; x += (r[i][0] + r[i + 1][0]) * f; y += (r[i][1] + r[i + 1][1]) * f;
    }
    if (Math.abs(a) < 1e-9) return r[0];
    return [x / (3 * a), y / (3 * a)];
  }
  function lati(r) { r = chiudi(r); const o = []; for (let i = 0; i < r.length - 1; i++) if (r[i][0] !== r[i + 1][0] || r[i][1] !== r[i + 1][1]) o.push([r[i], r[i + 1]]); return o; }
  // corpi con i fori (cortili, 07/11/2026): c.ring è l'anello esterno, c.buchi (facoltativo) gli anelli interni. Come in
  // modello.py (shapely): area netta, punto nel foro = fuori, i lati dei fori sono pareti (la normale esterna guarda il
  // cortile: i fori si percorrono nel verso opposto all'esterno)
  const buchiDi = (c) => (c && Array.isArray(c.buchi) ? c.buchi.filter((b) => Array.isArray(b) && b.length >= 3) : []);
  function areaCorpo(c) { return Math.max(0, area(c.ring) - buchiDi(c).reduce((s, b) => s + area(b), 0)); }
  // cortili veri per i tetti (09/11/2026, prova 13 di Paolo a Bagno di Romagna, foglio 54 particella 216: il corpo di 178 m²
  // aveva un «buco» di 8 m² occupato da un altro corpo, un volume interno alto 4 m, e il tetto restava piano): contano solo i
  // buchi di almeno 25 m² o del 10 % della pianta; cavedi e buchi riempiti da corpi interni non rendono piano il tetto
  const CORTILE_MIN_M2 = 25, CORTILE_MIN_QUOTA = 0.10;
  function cortiliDi(c) { const A = c && Array.isArray(c.ring) ? area(c.ring) : 0; return buchiDi(c).filter((b) => area(b) >= CORTILE_MIN_M2 || area(b) >= CORTILE_MIN_QUOTA * A); }
  function dentroCorpo(p, c) { return dentro(p, c.ring) && !buchiDi(c).some((b) => dentro(p, b)); }
  function anelliOrientati(c) {
    const ccw = areaConSegno(c.ring) > 0;
    const verso = (r, voluto) => ((areaConSegno(r) > 0) === voluto ? chiudi(r) : chiudi(r).slice().reverse());
    return [chiudi(c.ring), ...buchiDi(c).map((b) => verso(b, !ccw))];
  }
  function latiCorpo(c) { return anelliOrientati(c).flatMap(lati); }
  function orientamento(a, b, ccw) {
    const dx = b[0] - a[0], dy = b[1] - a[1];
    const [nx, ny] = ccw ? [dy, -dx] : [-dy, dx];
    return (Math.atan2(nx, ny) / GRAD + 360) % 360;
  }
  const settore = (az) => SETTORI[Math.floor(((az + 22.5) % 360) / 45)];
  function inComune(a, b, altro) {
    const lung = Math.hypot(b[0] - a[0], b[1] - a[1]);
    const ux = (b[0] - a[0]) / lung, uy = (b[1] - a[1]) / lung;
    let tot = 0;
    for (const [c, d] of (Array.isArray(altro) ? lati(altro) : latiCorpo(altro))) {
      const l2 = Math.hypot(d[0] - c[0], d[1] - c[1]);
      if (l2 < 1e-6) continue;
      const vx = (d[0] - c[0]) / l2, vy = (d[1] - c[1]) / l2;
      if (Math.abs(ux * vy - uy * vx) > 0.087) continue;
      if (Math.abs((c[0] - a[0]) * uy - (c[1] - a[1]) * ux) > TOLLERANZA_COMUNE) continue;
      const t1 = (c[0] - a[0]) * ux + (c[1] - a[1]) * uy, t2 = (d[0] - a[0]) * ux + (d[1] - a[1]) * uy;
      tot += Math.max(0, Math.min(lung, Math.max(t1, t2)) - Math.max(0, Math.min(t1, t2)));
    }
    return Math.min(tot, lung);
  }
  function altezzaMedia(c) {
    if (!c.colmo || c.colmo <= c.gronda || c.tetto === "piano") return c.gronda;
    return c.gronda + (c.colmo - c.gronda) / (c.tetto === "capanna" ? 2 : 3);
  }
  function rettangoloMinimo(r) {
    // lati del rettangolo minimo orientato su un lato dell'inviluppo convesso (basta per la campata del tetto)
    const h = inviluppo(chiudi(r).slice(0, -1));
    let migliore = null;
    for (let i = 0; i < h.length; i++) {
      const a = h[i], b = h[(i + 1) % h.length], l = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (l < 1e-9) continue;
      const ux = (b[0] - a[0]) / l, uy = (b[1] - a[1]) / l;
      let s0 = Infinity, s1 = -Infinity, t0 = Infinity, t1 = -Infinity;
      for (const p of h) { const s = p[0] * ux + p[1] * uy, t = -p[0] * uy + p[1] * ux; s0 = Math.min(s0, s); s1 = Math.max(s1, s); t0 = Math.min(t0, t); t1 = Math.max(t1, t); }
      const A = (s1 - s0) * (t1 - t0);
      if (!migliore || A < migliore.A) migliore = { A, lati: [s1 - s0, t1 - t0], dir: Math.atan2(ux, uy) / GRAD };
    }
    return migliore || { A: 0, lati: [0, 0], dir: 0 };
  }
  // corpi: [{ id, edificio, ring, gronda, colmo, tetto }]; vicini: corpi di altri edifici
  function indicatori(corpi, vicini = []) {
    const altri = vicini.filter((v) => !corpi.some((c) => c.edificio === v.edificio));
    let volume = 0, tetti = 0, pavimenti = 0, stesso = 0, conVicini = 0;
    const pareti = Object.fromEntries(SETTORI.map((s) => [s, 0]));
    for (const c of corpi) {
      const A = areaCorpo(c);
      volume += A * altezzaMedia(c); pavimenti += A;
      if (c.colmo && c.colmo > c.gronda && c.tetto !== "piano") {
        const semi = Math.max(Math.min(...rettangoloMinimo(c.ring).lati) / 2, 0.5);
        tetti += A / Math.cos(Math.atan((c.colmo - c.gronda) / semi));
      } else tetti += A;
      const ccw = areaConSegno(c.ring) > 0;
      for (const [a, b] of latiCorpo(c)) {
        const lung = Math.hypot(b[0] - a[0], b[1] - a[1]);
        let esposta = lung * c.gronda;
        for (const o of [...corpi, ...altri]) {
          if (o === c) continue;
          const com = inComune(a, b, o);
          if (com <= 0.01) continue;
          const coperta = com * Math.min(c.gronda, o.gronda);
          esposta -= coperta;
          if (o.edificio === c.edificio) stesso += coperta / 2; else conVicini += coperta;
        }
        pareti[settore(orientamento(a, b, ccw))] += Math.max(esposta, 0);
      }
    }
    const esposte = Object.values(pareti).reduce((x, y) => x + y, 0), disp = esposte + tetti + pavimenti;
    return { volume_lordo: volume, superficie_pavimento_terra: pavimenti, superficie_tetti: tetti, pareti_esposte: esposte,
      pareti_per_orientamento: pareti, pareti_in_comune_tra_corpi: stesso, pareti_in_comune_con_vicini: conVicini,
      superficie_disperdente: disp, s_su_v: volume > 0 ? disp / volume : null };
  }
  // divide un anello con la retta per p1 e p2 (taglio dei semipiani): due anelli, o null se la retta non lo attraversa
  function dividi(r, p1, p2) {
    r = chiudi(r).slice(0, -1);
    const lato = (p) => (p2[0] - p1[0]) * (p[1] - p1[1]) - (p2[1] - p1[1]) * (p[0] - p1[0]);
    const taglia = (segno) => {
      const o = [];
      for (let i = 0; i < r.length; i++) {
        const a = r[i], b = r[(i + 1) % r.length], la = lato(a) * segno, lb = lato(b) * segno;
        if (la >= 0) o.push(a);
        if ((la >= 0) !== (lb >= 0)) { const t = la / (la - lb); o.push([a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]); }
      }
      return o.length >= 3 ? chiudi(o) : null;
    };
    const A = taglia(1), B = taglia(-1);
    if (!A || !B || area(A) < 1 || area(B) < 1) return null;
    return [A, B];
  }
  function inviluppo(p) {
    const q = [...p].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    if (q.length < 3) return q;
    const cr = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
    const lo = [], hi = [];
    for (const x of q) { while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], x) <= 0) lo.pop(); lo.push(x); }
    for (const x of q.reverse()) { while (hi.length >= 2 && cr(hi[hi.length - 2], hi[hi.length - 1], x) <= 0) hi.pop(); hi.push(x); }
    return lo.slice(0, -1).concat(hi.slice(0, -1));
  }
  function dentro(p, r) {
    let d = false; r = chiudi(r);
    for (let i = 0, j = r.length - 2; i < r.length - 1; j = i++) {
      const a = r[i], b = r[j];
      if ((a[1] > p[1]) !== (b[1] > p[1]) && p[0] < (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1]) + a[0]) d = !d;
    }
    return d;
  }

  // proiezione locale in metri attorno a (lon0, lat0): basta per i 250 m del contesto
  function proiezione(lon0, lat0) {
    const kx = 111320 * Math.cos(lat0 * GRAD), ky = 110574;
    return { avanti: ([lon, lat]) => [(lon - lon0) * kx, (lat - lat0) * ky], indietro: ([x, y]) => [lon0 + x / kx, lat0 + y / ky] };
  }

  // ------------------------------------------------------------------ sole (algoritmo NOAA) e ombre
  // data: Date (UTC); restituisce azimut (gradi da nord, orario) e altezza sull'orizzonte (gradi, con rifrazione)
  function sole(data, lat, lon) {
    const jd = data.getTime() / 86400000 + 2440587.5, T = (jd - 2451545) / 36525;
    const L0 = (280.46646 + T * (36000.76983 + T * 0.0003032)) % 360;
    const M = 357.52911 + T * (35999.05029 - 0.0001537 * T);
    const e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T);
    const C = Math.sin(M * GRAD) * (1.914602 - T * (0.004817 + 0.000014 * T)) + Math.sin(2 * M * GRAD) * (0.019993 - 0.000101 * T) + Math.sin(3 * M * GRAD) * 0.000289;
    const om = 125.04 - 1934.136 * T, lam = L0 + C - 0.00569 - 0.00478 * Math.sin(om * GRAD);
    const eps0 = 23 + (26 + (21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))) / 60) / 60, eps = eps0 + 0.00256 * Math.cos(om * GRAD);
    const decl = Math.asin(Math.sin(eps * GRAD) * Math.sin(lam * GRAD));
    const y = Math.tan(eps * GRAD / 2) ** 2;
    const eqt = 4 / GRAD * (y * Math.sin(2 * L0 * GRAD) - 2 * e * Math.sin(M * GRAD) + 4 * e * y * Math.sin(M * GRAD) * Math.cos(2 * L0 * GRAD)
      - 0.5 * y * y * Math.sin(4 * L0 * GRAD) - 1.25 * e * e * Math.sin(2 * M * GRAD));
    const minuti = data.getUTCHours() * 60 + data.getUTCMinutes() + data.getUTCSeconds() / 60;
    let ha = ((minuti + eqt + 4 * lon) / 4 - 180) * GRAD;
    const fi = lat * GRAD;
    const cz = Math.min(1, Math.max(-1, Math.sin(fi) * Math.sin(decl) + Math.cos(fi) * Math.cos(decl) * Math.cos(ha)));
    const zen = Math.acos(cz);
    let az = Math.atan2(Math.sin(ha), Math.cos(ha) * Math.sin(fi) - Math.tan(decl) * Math.cos(fi)) / GRAD + 180;
    let alt = 90 - zen / GRAD;
    if (alt > -0.575) {   // rifrazione atmosferica (Saemundsson), piccola correzione vicino all'orizzonte
      alt += 1.02 / Math.tan((alt + 10.3 / (alt + 5.11)) * GRAD) / 60;
    }
    // irradianza extraterrestre normale (W/m²) con la correzione della distanza Terra–Sole (Spencer, forma breve)
    const giorno = Math.floor((jd - 2451544.5) % 365.25), extra = 1367 * (1 + 0.033 * Math.cos(2 * Math.PI * giorno / 365.25));
    return { azimut: (az + 360) % 360, altezza: alt, declinazione: decl / GRAD, extra };
  }
  // ombra sul terreno di un prisma alto h (m) con base r: inviluppo della base e della base spostata controsole
  function ombra(r, h, s) {
    if (s.altezza <= 0.5 || h <= 0) return null;
    const L = Math.min(h / Math.tan(s.altezza * GRAD), 400), az = (s.azimut + 180) * GRAD;
    const dx = Math.sin(az) * L, dy = Math.cos(az) * L;
    const base = chiudi(r).slice(0, -1);
    return chiudi(inviluppo([...base, ...base.map(([x, y]) => [x + dx, y + dy])]));
  }
  // profilo d'orizzonte di un punto (x, y, z in m) dato da ostacoli [{ ring, cima }] (cima = quota del tetto, m):
  // per ogni direzione l'angolo massimo (gradi) sotto cui si vedono gli ostacoli entro maxDist
  function orizzonte(p, ostacoli, nDir = 72, maxDist = 250) {
    const h = new Float32Array(nDir);
    for (let k = 0; k < nDir; k++) {
      const az = k * 360 / nDir * GRAD, ux = Math.sin(az), uy = Math.cos(az);
      let max = 0;
      for (const o of ostacoli) {
        if (o.cima <= p[2]) continue;
        for (const [a, b] of lati(o.ring)) {
          // intersezione del raggio p + t·u con il segmento a–b
          const ex = b[0] - a[0], ey = b[1] - a[1], den = ux * ey - uy * ex;
          if (Math.abs(den) < 1e-12) continue;
          const qx = a[0] - p[0], qy = a[1] - p[1];
          const t = (qx * ey - qy * ex) / den, s = (qx * uy - qy * ux) / den;
          if (t <= 0.05 || t > maxDist || s < 0 || s > 1) continue;
          const ang = Math.atan((o.cima - p[2]) / t) / GRAD;
          if (ang > max) max = ang;
        }
      }
      h[k] = max;
    }
    return h;
  }
  function altezzaOrizzonte(h, azimut) {
    const n = h.length, f = ((azimut % 360) + 360) % 360 / 360 * n, i = Math.floor(f) % n, j = (i + 1) % n, t = f - Math.floor(f);
    return h[i] * (1 - t) + h[j] * t;
  }
  const svf = (h) => h.reduce((s, a) => s + Math.cos(a * GRAD) ** 2, 0) / h.length;

  // ------------------------------------------------------------------ fotovoltaico
  // Trasposizione sul piano (W/m²). Dal 05/11/2026 il modello predefinito è **Perez** (Perez, Ineichen, Seals, Michalsky,
  // Stewart, «Modeling daylight availability and irradiance components from direct and global irradiance», Solar Energy
  // 44(5), 1990, pp. 271–289, coefficienti «allsitescomposite1990», gli stessi di pvlib-python, BSD): il cielo diffuso
  // ha una parte isotropa, una circumsolare (che segue il sole: sparisce quando il sole è coperto dall'orizzonte del
  // punto) e una fascia all'orizzonte. Con un orizzonte (fattoreCielo < 1) la parte isotropa e la fascia si riducono con
  // il fattore di vista del cielo. Massa d'aria di Kasten e Young (1989). `modello: "isotropo"` dà il calcolo di prima.
  const PEREZ_EPS = [1.065, 1.23, 1.5, 1.95, 2.8, 4.5, 6.2];
  const PEREZ_F1 = [[-0.008, 0.588, -0.062], [0.13, 0.683, -0.151], [0.33, 0.487, -0.221], [0.568, 0.187, -0.295],
    [0.873, -0.392, -0.362], [1.132, -1.237, -0.412], [1.06, -1.6, -0.359], [0.678, -0.327, -0.25]];
  const PEREZ_F2 = [[-0.06, 0.072, -0.022], [-0.019, 0.066, -0.029], [0.055, -0.064, -0.026], [0.109, -0.152, -0.014],
    [0.226, -0.462, 0.001], [0.288, -0.823, 0.056], [0.264, -1.127, 0.131], [0.156, -1.377, 0.251]];
  function massaAria(zenGradi) {
    if (zenGradi >= 90) return null;
    return 1 / (Math.cos(zenGradi * GRAD) + 0.50572 * (96.07995 - zenGradi) ** -1.6364);
  }
  // parti del cielo diffuso sul piano secondo Perez: { isotropa, circumsolare, orizzonte } (W/m²)
  function perez(dhi, dni, zenGradi, extra, cosAoi, inclinazione) {
    const zero = { isotropa: 0, circumsolare: 0, orizzonte: 0 };
    if (!(dhi > 0)) return zero;
    const z = zenGradi * GRAD, b = inclinazione * GRAD, am = massaAria(zenGradi);
    if (am === null) return { isotropa: dhi * (1 + Math.cos(b)) / 2, circumsolare: 0, orizzonte: 0 };
    const k = 1.041, eps = ((dhi + dni) / dhi + k * z ** 3) / (1 + k * z ** 3), delta = dhi * am / (extra || 1367);
    let i = 0;
    while (i < PEREZ_EPS.length && eps >= PEREZ_EPS[i]) i++;
    const f1 = PEREZ_F1[i], f2 = PEREZ_F2[i];
    const F1 = Math.max(0, f1[0] + f1[1] * delta + f1[2] * z), F2 = f2[0] + f2[1] * delta + f2[2] * z;
    const a = Math.max(0, cosAoi), bb = Math.max(Math.cos(85 * GRAD), Math.cos(z));
    const r = { isotropa: dhi * (1 - F1) * (1 + Math.cos(b)) / 2, circumsolare: dhi * F1 * a / bb, orizzonte: dhi * F2 * Math.sin(b) };
    if (r.isotropa + r.circumsolare + r.orizzonte < 0) return zero;
    return r;
  }
  // beam = false se il sole è dietro l'orizzonte del punto (si perdono la diretta e la circumsolare)
  function trasponi(ghi, dhi, s, inclinazione, orientamento, { albedo = 0.2, fattoreCielo = 1, beam = true, modello = "perez" } = {}) {
    if (!(ghi > 0) || s.altezza <= 0) return { poa: 0, diretta: 0, diffusa: 0 };
    const cz = Math.sin(s.altezza * GRAD), b = inclinazione * GRAD;
    let dni = cz > 0.087 ? Math.max(0, (ghi - dhi) / cz) : 0;
    dni = Math.min(dni, 1100);
    const cosAoi = Math.cos(s.altezza * GRAD) * Math.sin(b) * Math.cos((s.azimut - orientamento) * GRAD) + cz * Math.cos(b);
    const diretta = beam ? dni * Math.max(0, cosAoi) : 0;
    const riflessa = ghi * albedo * (1 - Math.cos(b)) / 2;
    let diffusa;
    if (modello === "isotropo") diffusa = dhi * fattoreCielo * (1 + Math.cos(b)) / 2;
    else {
      const p = perez(dhi, dni, 90 - s.altezza, s.extra, cosAoi, inclinazione);
      diffusa = p.isotropa * fattoreCielo + (beam ? p.circumsolare : 0) + p.orizzonte * fattoreCielo;
    }
    return { poa: diretta + diffusa + riflessa, diretta, diffusa };
  }
  // clima: { inizio (ISO UTC), passo_ore: 1, ghi[], dhi[], t[] } (W/m² medi dell'ora precedente);
  // aree: [{ id, inclinazione, orientamento, kwp, orizzonti: [Float32Array per punto di campionamento] }]
  function producibilita(clima, lat, lon, aree, { perdite = 0.14, gamma = -0.0037, noct = 45, modello = "perez" } = {}) {
    const t0 = Date.parse(clima.inizio), n = clima.ghi.length;
    const out = aree.map((a) => ({ id: a.id, kwh: 0, kwhSenzaOmbre: 0, mensile: new Array(12).fill(0),
      svf: a.orizzonti.length ? a.orizzonti.reduce((s, h) => s + svf(h), 0) / a.orizzonti.length : 1 }));
    for (let i = 0; i < n; i++) {
      const ghi = clima.ghi[i], dhi = clima.dhi[i] === null || clima.dhi[i] === undefined ? 0.3 * ghi : clima.dhi[i];
      if (!(ghi > 0)) continue;
      const d = new Date(t0 + (i * (clima.passo_ore || 1) - 0.5) * 3600000), s = sole(d, lat, lon);
      if (s.altezza <= 0) continue;
      const ta = clima.t && clima.t[i] !== null && clima.t[i] !== undefined ? clima.t[i] : 15, mese = d.getUTCMonth();
      aree.forEach((a, k) => {
        const libero = trasponi(ghi, dhi, s, a.inclinazione, a.orientamento, { modello });
        let poa = 0;
        const pts = a.orizzonti.length ? a.orizzonti : [null];
        for (const h of pts) {
          const visto = !h || s.altezza > altezzaOrizzonte(h, s.azimut);
          poa += trasponi(ghi, dhi, s, a.inclinazione, a.orientamento, { fattoreCielo: h ? svf(h) : 1, beam: visto, modello }).poa;
        }
        poa /= pts.length;
        const pot = (g) => { const tc = ta + g * (noct - 20) / 800; return a.kwp * g / 1000 * (1 + gamma * (tc - 25)) * (1 - perdite); };
        const e = pot(poa), e0 = pot(libero.poa);
        out[k].kwh += e; out[k].kwhSenzaOmbre += e0; out[k].mensile[mese] += e;
      });
    }
    out.forEach((o) => { o.perdita = o.kwhSenzaOmbre > 0 ? 100 * (1 - o.kwh / o.kwhSenzaOmbre) : 0; });
    return out;
  }
  // clima di prova a cielo sereno (Haurwitz) ridotto del 35 %: **sintetico**, solo quando l'archivio non risponde
  function climaSintetico(anno, lat, lon) {
    const inizio = Date.UTC(anno, 0, 1), n = ((anno % 4 === 0 && anno % 100) || anno % 400 === 0) ? 8784 : 8760;
    const ghi = [], dhi = [], t = [];
    for (let i = 0; i < n; i++) {
      const d = new Date(inizio + (i - 0.5) * 3600000), s = sole(d, lat, lon), cz = Math.sin(Math.max(0, s.altezza) * GRAD);
      const g = cz > 0.01 ? 0.65 * 1098 * cz * Math.exp(-0.057 / cz) : 0;
      ghi.push(Math.round(g)); dhi.push(Math.round(g * 0.35));
      const giorno = i / 24;
      t.push(13.5 - 9.5 * Math.cos(2 * Math.PI * (giorno - 18) / 365) - 4 * Math.cos(2 * Math.PI * ((i % 24) - 3) / 24));
    }
    return { inizio: new Date(inizio).toISOString(), passo_ore: 1, ghi, dhi, t, sintetico: true, anno };
  }

  // ------------------------------------------------------------------ firma energetica
  // punti: [{ consumo, gg }] → retta consumo = base + pendenza × gg (minimi quadrati), R², atteso per punto
  function firma(punti) {
    const p = punti.filter((x) => Number.isFinite(x.consumo) && Number.isFinite(x.gg));
    if (p.length < 3) return null;
    const n = p.length, mx = p.reduce((s, x) => s + x.gg, 0) / n, my = p.reduce((s, x) => s + x.consumo, 0) / n;
    let sxx = 0, sxy = 0, syy = 0;
    for (const x of p) { sxx += (x.gg - mx) ** 2; sxy += (x.gg - mx) * (x.consumo - my); syy += (x.consumo - my) ** 2; }
    if (sxx === 0) return null;
    const pend = sxy / sxx, base = my - pend * mx, r2 = syy > 0 ? (sxy * sxy) / (sxx * syy) : 1;
    return { base, pendenza: pend, r2, n, atteso: punti.map((x) => Number.isFinite(x.gg) ? base + pend * x.gg : null) };
  }

  // ------------------------------------------------------------------ orizzonte combinato (Fase B)
  // massimo, direzione per direzione, tra l'orizzonte vicino dei corpi (stesso numero di direzioni) e quello lontano
  // del terreno (Copernicus DEM, /api/edifici/orizzonte, anche con un numero di direzioni diverso: interpolato)
  function uniscio(vicino, lontano) {
    if (!lontano || !lontano.length) return vicino;
    const n = vicino.length, o = new Float32Array(n);
    for (let k = 0; k < n; k++) o[k] = Math.max(vicino[k], altezzaOrizzonte(lontano, k * 360 / n));
    return o;
  }

  // ------------------------------------------------------------------ facciate segmento per segmento (§ 7, Fase B)
  // Ogni lato di ogni corpo è diviso in segmenti lunghi al più `passo` m e in fasce verticali alte al più `fascia` m.
  // Una fascia è **esposta** se non è coperta da un corpo confinante (stesso edificio o vicino) più alto della sua
  // quota: le parti in comune non ricevono sole. Per ogni parte esposta: centro, normale (azimut), area; l'orizzonte
  // del centro (72 direzioni) lo calcola chi chiama (Web Worker), qui si restano i dati geometrici.
  function partiFacciate(corpi, vicini = [], { passo = 4, fascia = 3 } = {}) {
    const tutti = [...corpi, ...vicini], parti = [];
    for (const c of corpi) {
      const ccw = areaConSegno(c.ring) > 0, base = c.quota || 0;
      latiCorpo(c).forEach(([a, b], il) => {
        const lung = Math.hypot(b[0] - a[0], b[1] - a[1]);
        if (lung < 0.3) return;
        const az = orientamento(a, b, ccw), ns = Math.max(1, Math.ceil(lung / passo)), nf = Math.max(1, Math.ceil(c.gronda / fascia));
        const nx = Math.sin(az * GRAD), ny = Math.cos(az * GRAD);
        for (let i = 0; i < ns; i++) {
          const t0 = i / ns, t1 = (i + 1) / ns;
          const p0 = [a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0], p1 = [a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1];
          // altezza fino a cui il segmento è coperto da un corpo confinante
          let coperto = 0;
          for (const o of tutti) {
            if (o === c) continue;
            if (inComune(p0, p1, o) > 0.5 * lung / ns) coperto = Math.max(coperto, Math.min(c.gronda, o.gronda + ((o.quota || 0) - base)));
          }
          for (let k = 0; k < nf; k++) {
            const z0 = k * c.gronda / nf, z1 = (k + 1) * c.gronda / nf;
            if (z1 <= coperto + 1e-6) continue;
            const zz0 = Math.max(z0, coperto), lseg = lung / ns;
            parti.push({ corpo: c.id, lato: il, segmento: i, azimut: az, settore: settore(az), area: lseg * (z1 - zz0),
              centro: [(p0[0] + p1[0]) / 2 + nx * 0.05, (p0[1] + p1[1]) / 2 + ny * 0.05, base + (zz0 + z1) / 2],
              estremi: [p0, p1], z: [base + zz0, base + z1] });
          }
        }
      });
    }
    return parti;
  }
  // irraggiamento sulle parti esposte delle facciate (verticali, inclinazione 90°): kWh/m² annui e mensili per parte,
  // con le ombre del loro orizzonte (vicino + lontano). clima come per producibilita.
  function irraggiamentoFacciate(clima, lat, lon, parti, orizzonti, { modello = "perez" } = {}) {
    const t0 = Date.parse(clima.inizio), n = clima.ghi.length;
    const out = parti.map((p, k) => ({ annuo: 0, libero: 0, mensile: new Array(12).fill(0), svf: orizzonti[k] ? svf(orizzonti[k]) : 1 }));
    for (let i = 0; i < n; i++) {
      const ghi = clima.ghi[i];
      if (!(ghi > 0)) continue;
      const dhi = clima.dhi[i] === null || clima.dhi[i] === undefined ? 0.3 * ghi : clima.dhi[i];
      const d = new Date(t0 + (i * (clima.passo_ore || 1) - 0.5) * 3600000), s = sole(d, lat, lon);
      if (s.altezza <= 0) continue;
      const mese = d.getUTCMonth();
      parti.forEach((p, k) => {
        const h = orizzonti[k], visto = !h || s.altezza > altezzaOrizzonte(h, s.azimut);
        // fattore di vista del cielo di una parete verticale: metà cielo, ridotto dagli ostacoli del suo lato
        const fc = h ? Math.min(1, out[k].svf * 2) : 1;
        const g = trasponi(ghi, dhi, s, 90, p.azimut, { fattoreCielo: fc, beam: visto, modello }).poa / 1000;
        const g0 = trasponi(ghi, dhi, s, 90, p.azimut, { modello }).poa / 1000;
        out[k].annuo += g; out[k].libero += g0; out[k].mensile[mese] += g;
      });
    }
    return out;
  }
  // riepilogo per orientamento: area esposta, kWh/anno, kWh/m² medi, perdita per ombre, estate (giu–ago) e inverno (dic–feb)
  function riepilogoFacciate(parti, irr) {
    const r = Object.fromEntries(SETTORI.map((s) => [s, { area: 0, kwh: 0, libero: 0, estate: 0, inverno: 0, cielo: 0 }]));
    parti.forEach((p, k) => {
      const x = r[p.settore], m = irr[k].mensile;
      x.area += p.area; x.kwh += irr[k].annuo * p.area; x.libero += irr[k].libero * p.area;
      x.estate += (m[5] + m[6] + m[7]) * p.area; x.inverno += (m[11] + m[0] + m[1]) * p.area;
      // analisi 9 (05/11/2026): cielo visibile dalla facciata, 0–1 (1 = nessun ostacolo davanti), media sull'area
      x.cielo += Math.min(1, 2 * (irr[k].svf ?? 0.5)) * p.area;
    });
    for (const x of Object.values(r)) {
      x.kwh_m2 = x.area ? x.kwh / x.area : 0; x.perdita = x.libero ? 100 * (1 - x.kwh / x.libero) : 0;
      x.cielo = x.area ? x.cielo / x.area : null;
    }
    return r;
  }

  // ------------------------------------------------------------------ obblighi di legge (analisi 14, § 9)
  // D.Lgs. 8 novembre 2021, n. 199, art. 26 e Allegato III (testo vigente su Normattiva, letto il 04/11/2026):
  //  - Sezione B, punto 3: P = k · S [kW], k = 0,025 edifici esistenti, 0,05 nuova costruzione; S = superficie in pianta
  //    dell'edificio al livello del terreno (proiezione al suolo della sagoma), m², senza le pertinenze;
  //  - Sezione B, punto 5: per gli edifici pubblici gli obblighi del punto 3 sono incrementati del 10 % e le
  //    percentuali del punto 1 maggiorate di cinque punti;
  //  - Sezione B, punto 1: quote di copertura dei consumi previsti (60 %/60 % nuovi; 40 %/40 % ristrutturazioni
  //    importanti di primo livello; 15 % di secondo livello e ristrutturazione dell'impianto termico) – richiedono il
  //    fabbisogno, quindi qui solo come promemoria;
  //  - Sezione A: si applica a nuova costruzione, ristrutturazioni importanti e ristrutturazione dell'impianto termico.
  const QUOTE_199 = { nuovo: { acs: 60, totale: 60 }, primo: { acs: 40, totale: 40 }, secondo: { acs: null, totale: 15 }, impianto: { acs: null, totale: 15 } };
  function obbligoFer(superficiePianta, { intervento = "primo", pubblico = false } = {}) {
    if (!(superficiePianta > 0)) return null;
    const k = intervento === "nuovo" ? 0.05 : 0.025;
    const p = k * superficiePianta * (pubblico ? 1.1 : 1);
    const q = QUOTE_199[intervento] || QUOTE_199.primo, piu = pubblico ? 5 : 0;
    return { k, superficie: superficiePianta, kw: p, pubblico, intervento,
      quota_acs: q.acs === null ? null : q.acs + piu, quota_totale: q.totale + piu };
  }
  // DM 26/6/2015 (Allegato 1, Appendice A, § 2.1), come modificato dal DM 28/10/2025 (GU n. 283 del 5/12/2025, in vigore
  // centottanta giorni dopo): Tabella 10, H'T massimo (W/m²K) per nuova costruzione e demolizione e ricostruzione, per
  // zona climatica e rapporto di forma S/V. Valori dell'atto normativo (non coperti da diritto d'autore).
  const HT_TAB10 = { A: [0.80, 0.63, 0.58], B: [0.80, 0.63, 0.58], C: [0.80, 0.60, 0.55], D: [0.80, 0.58, 0.53], E: [0.75, 0.55, 0.50], F: [0.70, 0.53, 0.48] };
  function htMassimo(zona, sv) {
    const r = HT_TAB10[String(zona || "").toUpperCase()];
    if (!r || !Number.isFinite(sv)) return null;
    const i = sv < 0.4 ? 0 : sv < 0.7 ? 1 : 2;
    return { valore: r[i], fascia: ["S/V < 0,4", "0,4 ≤ S/V < 0,7", "S/V ≥ 0,7"][i] };
  }

  // Stesso DM, Allegato 1, Appendice A, § 2.1, Tabella 11 (GU n. 283 del 5/12/2025, pp. 39–40): H'T massimo (W/m²K) per le
  // ristrutturazioni importanti di primo livello, per zona climatica e rapporto EX ANTE tra la superficie dei componenti
  // vetrati e la superficie di tutti i componenti (vetrati e/o opachi) dell'edificio oggetto di intervento (superfici
  // esterne lorde, § 2.1, comma 4). Valori dell'atto normativo. La norma dà solo le 20 colonne: tra due colonne EuGEnio
  // interpola in modo lineare (scelta sua, dichiarata nella pagina); sotto il 9 % vale la prima colonna.
  const HT_TAB11_QUOTE = [9, 14, 19, 24, 28, 33, 38, 43, 47, 52, 57, 62, 67, 71, 76, 81, 86, 90, 95, 100];
  const _AB = [0.72, 0.82, 0.92, 1.01, 1.1, 1.18, 1.26, 1.34, 1.41, 1.47, 1.53, 1.59, 1.64, 1.68, 1.72, 1.76, 1.79, 1.82, 1.84, 1.86];
  const HT_TAB11 = { A: _AB, B: _AB,
    C: [0.6, 0.64, 0.71, 0.78, 0.85, 0.91, 0.97, 1.03, 1.08, 1.14, 1.18, 1.23, 1.27, 1.31, 1.35, 1.38, 1.42, 1.44, 1.47, 1.49],
    D: [0.58, 0.58, 0.59, 0.65, 0.7, 0.75, 0.81, 0.86, 0.9, 0.95, 0.99, 1.03, 1.07, 1.11, 1.14, 1.18, 1.21, 1.24, 1.26, 1.29],
    E: [0.55, 0.55, 0.55, 0.55, 0.58, 0.62, 0.66, 0.7, 0.74, 0.78, 0.82, 0.85, 0.89, 0.92, 0.95, 0.99, 1.02, 1.04, 1.07, 1.1],
    F: [0.53, 0.53, 0.53, 0.53, 0.53, 0.53, 0.56, 0.6, 0.63, 0.66, 0.69, 0.72, 0.75, 0.79, 0.82, 0.85, 0.87, 0.9, 0.93, 0.96] };
  // quota: percentuale (0–100) di superfici vetrate sul totale dei componenti dell'involucro
  function htMassimoPrimoLivello(zona, quota) {
    const r = HT_TAB11[String(zona || "").toUpperCase()];
    if (!r || !Number.isFinite(quota) || quota < 0 || quota > 100) return null;
    const Q = HT_TAB11_QUOTE;
    if (quota <= Q[0]) return { valore: r[0], colonne: [[Q[0], r[0]]], interpolato: false, nota: quota < Q[0] ? "sotto il 9 %: prima colonna" : "" };
    let j = Q.findIndex((x) => x >= quota);
    if (Q[j] === quota) return { valore: r[j], colonne: [[Q[j], r[j]]], interpolato: false, nota: "" };
    const t = (quota - Q[j - 1]) / (Q[j] - Q[j - 1]);
    return { valore: Math.round((r[j - 1] + t * (r[j] - r[j - 1])) * 1000) / 1000, colonne: [[Q[j - 1], r[j - 1]], [Q[j], r[j]]],
      interpolato: true, nota: "interpolazione lineare tra due colonne (EuGEnio)" };
  }
  // Quota vetrata **stimata** quando l'utente non la conosce: rapporto finestre/pareti tipico per uso (valori assunti da
  // EuGEnio, non presi da norme: da sostituire con il rilievo), applicato alle pareti esposte e diviso per la superficie
  // disperdente (pareti esposte + tetti + pavimento a terra, come per H'T).
  const FINESTRE_SU_PARETI = { residenziale: 0.15, uffici: 0.3, scuola: 0.25, ospedale: 0.22, commerciale: 0.3, capannone: 0.08,
    palestra: 0.12, industriale: 0.08, altro: 0.18 };
  function quotaVetrataStimata(geometria, uso = "altro") {
    if (!geometria || !(geometria.superficie_disperdente > 0)) return null;
    const wwr = FINESTRE_SU_PARETI[uso] ?? FINESTRE_SU_PARETI.altro;
    return { quota: 100 * wwr * geometria.pareti_esposte / geometria.superficie_disperdente, finestre_su_pareti: wwr, uso };
  }

  // Colonne visura_… di EuGEnio Visure (fase 11) → stesse chiavi delle colonne facoltative, per la precedenza
  // CSV → visura → stima (§ 8). Le visure non danno superficie lorda né netta: solo piani, superficie catastale e uso.
  const DA_VISURA = { piani_fuori_terra: "visura_piani_fuori_terra", piani_interrati: "visura_piani_interrati",
    superficie_catastale: "visura_superficie_catastale" };
  function daVisura(colonne) {
    const o = {};
    if (!colonne || colonne.visura_esito === "nessuna_visura") return o;
    for (const [k, c] of Object.entries(DA_VISURA)) {
      const v = numero(colonne[c]);
      if (v !== null && v > 0) o[k] = v;
    }
    if (o.piani_fuori_terra === undefined) { const p = numero(colonne.visura_piani); if (p !== null && p > 0) o.piani_fuori_terra = p; }
    if (colonne.visura_uso) o.uso = String(colonne.visura_uso);
    return o;
  }
  // { indice di colonna: nome della colonna visura_… } tra i titoli di un file (Valori per sede, Patrimonio)
  function mappaVisura(titoli) {
    const m = {};
    titoli.forEach((t, i) => { const k = String(t).trim().toLowerCase(); if (k.startsWith("visura_")) m[i] = k; });
    return m;
  }
  function leggiVisura(mappa, celle) {
    const c = {};
    for (const [i, k] of Object.entries(mappa)) if (celle[i] !== undefined && String(celle[i]).trim() !== "") c[k] = String(celle[i]).trim();
    return daVisura(c);
  }

  // ------------------------------------------------------------------ posa di un modello sulla sagoma dell'archivio
  // Importa DXF/IFC (05/11/2026): il modello dell'utente (piante dei corpi in metri, coordinate del disegno) si aggancia
  // alla sagoma di un edificio dell'archivio (anelli in lon/lat). Rotazione dai rettangoli minimi delle due impronte
  // (quattro candidati a 90°), traslazione dei baricentri, scelta del candidato con la sovrapposizione (IoU) più alta,
  // stimata su una griglia di 80×80 punti. Nessuna scala: le unità del disegno sono già note; il rapporto delle aree
  // dice se tornano. Restituisce due coppie di punti (disegno → lon/lat), così la pagina usa la stessa posa «due punti».
  function posaDaSagoma(piante, sagomeLonLat) {
    const pm = piante.flatMap((r) => chiudi(r).slice(0, -1));
    const tutti = sagomeLonLat.flatMap((r) => chiudi(r).slice(0, -1));
    if (pm.length < 3 || tutti.length < 3) return null;
    const lon0 = tutti.reduce((s, q) => s + q[0], 0) / tutti.length, lat0 = tutti.reduce((s, q) => s + q[1], 0) / tutti.length;
    const pr = proiezione(lon0, lat0);
    const pa = tutti.map(pr.avanti);
    const hm = inviluppo(pm), ha = inviluppo(pa);
    const cm = centroide([...hm, hm[0]]), ca = centroide([...ha, ha[0]]);
    const rm = rettangoloMinimo([...hm, hm[0]]), ra = rettangoloMinimo([...ha, ha[0]]);
    const am = piante.reduce((x, r) => x + area(r), 0), aa = sagomeLonLat.reduce((x, r) => x + area(r.map(pr.avanti)), 0);
    // trasformazione: punto del disegno → metri locali attorno alla sagoma (rotazione oraria di «rot» gradi, come gli azimut)
    const muovi = (rot) => { const c = Math.cos(rot * GRAD), sn = Math.sin(rot * GRAD);
      return ([x, y]) => { const dx = x - cm[0], dy = y - cm[1]; return [ca[0] + dx * c + dy * sn, ca[1] - dx * sn + dy * c]; }; };
    const anelliA = sagomeLonLat.map((r) => r.map(pr.avanti));
    const iou = (rot) => {
      const f = muovi(rot), anelliM = piante.map((r) => r.map(f));
      const pts = [...anelliM.flat(), ...pa];
      const x0 = Math.min(...pts.map((q) => q[0])), x1 = Math.max(...pts.map((q) => q[0]));
      const y0 = Math.min(...pts.map((q) => q[1])), y1 = Math.max(...pts.map((q) => q[1]));
      let ent = 0, una = 0;
      const N = 80;
      for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) {
        const q = [x0 + (i + 0.5) * (x1 - x0) / N, y0 + (j + 0.5) * (y1 - y0) / N];
        const inM = anelliM.some((r) => dentro(q, r)), inA = anelliA.some((r) => dentro(q, r));
        if (inM && inA) ent++;
        if (inM || inA) una++;
      }
      return una ? ent / una : 0;
    };
    const candidati = [0, 90, 180, 270].map((k) => {
      const rot = ((ra.dir - rm.dir + k) % 360 + 360) % 360;
      return { rot, iou: iou(rot) };
    }).sort((a, b) => b.iou - a.iou);
    const best = candidati[0], f = muovi(best.rot);
    // due punti lontani del disegno: gli estremi dell'inviluppo lungo il lato lungo
    let p1 = hm[0], p2 = hm[0], dmax = -1;
    for (const a of hm) for (const b of hm) { const d = Math.hypot(a[0] - b[0], a[1] - b[1]); if (d > dmax) { dmax = d; p1 = a; p2 = b; } }
    const punti = [p1, p2].map((q) => { const [lon, lat] = pr.indietro(f(q)); return [q[0], q[1], lon, lat]; });
    return { rotazione: Math.round(best.rot * 100) / 100, iou: Math.round(best.iou * 1000) / 1000, rapporto_aree: aa > 0 ? am / aa : null,
      candidati, punti, centro: pr.indietro(ca) };
  }

  // ------------------------------------------------------------------ classifica di priorità (analisi 4, § 9)
  // sedi: [{ id, nome, kwh_m2, sensibilita (kWh/m² per grado giorno), base_quota (carico di base / consumo, 0–1),
  //   r2, fv_kwh_m2 (producibilità FV per m² lordo), costo_m2 (€/m², da convenzioni o prezzi ARERA) }]; campi mancanti
  //   ammessi. Ogni criterio diventa un punteggio 0–100 sul patrimonio (rango percentile: robusto agli estremi), poi
  //   media pesata dei criteri disponibili (pesi modificabili). Più alto = intervenire prima.
  const PESI_PRIORITA = { intensita: 0.35, sensibilita: 0.2, base: 0.1, costo: 0.2, fv: 0.15 };
  function priorita(sedi, pesi = PESI_PRIORITA) {
    const crit = { intensita: (s) => s.kwh_m2, sensibilita: (s) => s.sensibilita, base: (s) => s.base_quota, costo: (s) => s.costo_m2, fv: (s) => s.fv_kwh_m2 };
    const punteggi = {};
    for (const [k, f] of Object.entries(crit)) {
      const v = sedi.map(f).filter((x) => Number.isFinite(x));
      if (v.length < 2) continue;
      const ord = [...v].sort((a, b) => a - b);
      punteggi[k] = (x) => {
        if (!Number.isFinite(x)) return null;
        let sotto = 0, uguali = 0;
        for (const y of ord) { if (y < x) sotto++; else if (y === x) uguali++; }
        return 100 * (sotto + (uguali - 1) / 2) / (ord.length - 1);
      };
    }
    const righe = sedi.map((s) => {
      let somma = 0, peso = 0;
      const dettaglio = {};
      for (const [k, p] of Object.entries(punteggi)) {
        const v = p(crit[k](s));
        dettaglio[k] = v;
        if (v !== null && pesi[k] > 0) { somma += v * pesi[k]; peso += pesi[k]; }
      }
      return { ...s, punteggi: dettaglio, punteggio: peso ? somma / peso : null, criteri: Object.values(dettaglio).filter((x) => x !== null).length };
    });
    righe.sort((a, b) => (b.punteggio ?? -1) - (a.punteggio ?? -1));
    righe.forEach((r, i) => { r.posto = r.punteggio === null ? null : i + 1; });
    return righe;
  }

  // ------------------------------------------------------------------ tetto a falde stimato dal colmo (07/11/2026 sera)
  // Dove il DB topografico dà un colmo più alto della gronda (H_COLMO, Rimini 5.798 corpi) ma non ci sono falde misurate
  // (LiDAR), il tetto si stima sul rettangolo minimo orientato del corpo: **a capanna** con il colmo sul lato lungo, o **a
  // padiglione** per i corpi quasi quadrati (lato lungo / lato corto < 1,3) o se l'utente lo sceglie; «a una falda» se lo
  // sceglie l'utente (discesa verso il lato più a sud). Precedenza nella pagina: falde LiDAR → colmo DBTR → tetto piano.
  // Niente stima per i corpi con i cortili o poco rettangolari (area < 70 % del rettangolo): restano come prima.
  // Restituisce { tipo, falde: [{ id, ring, pendenza, orientamento, superficie, area_pianta, alto, basso }] } o null.
  const RAPPORTO_PADIGLIONE = 1.3, RIEMPIMENTO_MIN = 0.7, SALTO_MIN = 0.3;
  function clipConvesso(poli, taglio) {
    // Sutherland–Hodgman: poligono qualsiasi tagliato da un poligono convesso (anelli aperti, versi qualsiasi)
    const ccw = areaConSegno(taglio) > 0;
    let out = poli.slice();
    for (let i = 0; i < taglio.length && out.length; i++) {
      const a = taglio[i], b = taglio[(i + 1) % taglio.length], inp = out; out = [];
      const lato = (p) => { const v = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]); return ccw ? v >= -1e-9 : v <= 1e-9; };
      for (let k = 0; k < inp.length; k++) {
        const p = inp[k], q = inp[(k + 1) % inp.length], ip = lato(p), iq = lato(q);
        if (ip) out.push(p);
        if (ip !== iq) {
          const d1 = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]), d2 = (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0]);
          const t = d1 / (d1 - d2); out.push([p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])]);
        }
      }
    }
    return out.length >= 3 && area(out) > 0.05 ? out : null;
  }
  // rettangolo minimo orientato del corpo per il tetto: u lungo il lato lungo (La), v lungo il lato corto (Lb); null se
  // l'anello ha meno di 3 punti. Lo usano la stima dal colmo e l'ipotesi automatica (stesso rettangolo, stessa campata)
  function rettangoloTetto(c) {
    const anello = chiudi(c.ring).slice(0, -1);
    if (anello.length < 3) return null;
    const h = inviluppo(anello);
    let m = null;
    for (let i = 0; i < h.length; i++) {
      const a = h[i], b = h[(i + 1) % h.length], l = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (l < 1e-9) continue;
      const u = [(b[0] - a[0]) / l, (b[1] - a[1]) / l], v = [-u[1], u[0]];
      let s0 = Infinity, s1 = -Infinity, t0 = Infinity, t1 = -Infinity;
      for (const p of h) { const s = p[0] * u[0] + p[1] * u[1], t = p[0] * v[0] + p[1] * v[1]; s0 = Math.min(s0, s); s1 = Math.max(s1, s); t0 = Math.min(t0, t); t1 = Math.max(t1, t); }
      const A = (s1 - s0) * (t1 - t0);
      if (!m || A < m.A) m = { A, u, v, s0, s1, t0, t1 };
    }
    if (!m) return null;
    // asse a = lato lungo, b = lato corto
    let { u, v, s0, s1, t0, t1 } = m;
    if (s1 - s0 < t1 - t0) { const ou = u; u = v; v = [-ou[0], -ou[1]]; [s0, s1, t0, t1] = [t0, t1, -s1, -s0]; }
    return { A: m.A, u, v, s0, s1, t0, t1, La: s1 - s0, Lb: t1 - t0, anello, h };
  }
  function faldeStimate(c, tipoVoluto = null) {
    if (!c || !Array.isArray(c.ring) || !(c.colmo > c.gronda + SALTO_MIN) || cortiliDi(c).length) return null;
    const m = rettangoloTetto(c);
    if (!m || m.A < 1 || areaCorpo(c) / m.A < RIEMPIMENTO_MIN) return null;
    const { u, v, s0, s1, t0, t1, anello } = m;
    const La = s1 - s0, Lb = t1 - t0, semi = Lb / 2, salto = c.colmo - c.gronda;
    if (Lb < 2) return null;
    const pt = (s, t) => [s * u[0] + t * v[0], s * u[1] + t * v[1]];
    const az = (d) => ((Math.atan2(d[0], d[1]) / GRAD) + 360) % 360;
    let tipo = tipoVoluto && ["capanna", "padiglione", "monofalda"].includes(tipoVoluto) ? tipoVoluto : (La / Lb < RAPPORTO_PADIGLIONE ? "padiglione" : "capanna");
    // regioni convesse del rettangolo, ognuna con la direzione di discesa (versore) e la distanza dalla gronda
    const reg = [];
    const tm = (t0 + t1) / 2;
    if (tipo === "monofalda") {
      const verso = v[1] <= 0 ? v : [-v[0], -v[1]];      // discesa verso sud (y minore)
      const basso = verso === v ? t1 : t0;
      reg.push({ poli: [pt(s0, t0), pt(s1, t0), pt(s1, t1), pt(s0, t1)], d: verso, gronda: (p) => Math.abs(basso - (p[0] * v[0] + p[1] * v[1])), largo: Lb });
    } else if (tipo === "capanna") {
      reg.push({ poli: [pt(s0, t0), pt(s1, t0), pt(s1, tm), pt(s0, tm)], d: [-v[0], -v[1]], gronda: (p) => (p[0] * v[0] + p[1] * v[1]) - t0, largo: semi });
      reg.push({ poli: [pt(s0, tm), pt(s1, tm), pt(s1, t1), pt(s0, t1)], d: v, gronda: (p) => t1 - (p[0] * v[0] + p[1] * v[1]), largo: semi });
    } else {   // padiglione: due trapezi sui lati lunghi e due triangoli sulle testate, stessa pendenza
      const a0 = s0 + semi, a1 = s1 - semi;
      const S = (p) => p[0] * u[0] + p[1] * u[1], T = (p) => p[0] * v[0] + p[1] * v[1];
      reg.push({ poli: [pt(s0, t0), pt(s1, t0), pt(a1, tm), pt(a0, tm)], d: [-v[0], -v[1]], gronda: (p) => T(p) - t0, largo: semi });
      reg.push({ poli: [pt(a0, tm), pt(a1, tm), pt(s1, t1), pt(s0, t1)], d: v, gronda: (p) => t1 - T(p), largo: semi });
      reg.push({ poli: [pt(s0, t0), pt(a0, tm), pt(s0, t1)], d: [-u[0], -u[1]], gronda: (p) => S(p) - s0, largo: semi });
      reg.push({ poli: [pt(s1, t0), pt(s1, t1), pt(a1, tm)], d: u, gronda: (p) => s1 - S(p), largo: semi });
    }
    const falde = [];
    reg.forEach((r, k) => {
      const pezzo = clipConvesso(anello, r.poli);
      if (!pezzo) return;
      const tanp = salto / r.largo, dist = pezzo.map(r.gronda);
      const ap = area(pezzo), pend = Math.atan(tanp) / GRAD;
      falde.push({ id: `S${k + 1}`, ring: chiudi(pezzo), pendenza: Math.round(pend * 10) / 10, orientamento: Math.round(az(r.d)),
        superficie: Math.round(ap / Math.cos(pend * GRAD) * 10) / 10, area_pianta: Math.round(ap * 10) / 10,
        alto: Math.round((c.gronda + Math.min(salto, Math.max(...dist) * tanp)) * 100) / 100,
        basso: Math.round((c.gronda + Math.max(0, Math.min(...dist)) * tanp) * 100) / 100 });
    });
    return falde.length ? { tipo, falde } : null;
  }

  // ------------------------------------------------------------------ tetto ipotizzato (08/11/2026, decisione di Paolo)
  // Dove non ci sono né falde LiDAR né il colmo del DB topografico, il tetto si **ipotizza a falde**: 22° in pianura (e in
  // collina), 32° in montagna; stessa forma della stima dal colmo (capanna sul lato lungo, padiglione se lato lungo / lato
  // corto < 1,3), con colmo = gronda + semiluce × tan(inclinazione) (semiluce = metà del lato corto del rettangolo minimo).
  // Montagna: quota del terreno sotto il corpo (DTM) ≥ 600 m nei comuni del Nord, ≥ 700 m al Centro, al Sud e nelle isole
  // (soglie della definizione ISTAT di zona altimetrica di montagna); senza la quota del corpo, l'altitudine del comune
  // (DPR 412/93, Allegato A). La classificazione ISTAT dei comuni per zona altimetrica non è tra i dati del sito: la
  // quota sotto l'edificio dà anche il fondovalle di un comune montano (Bagno di Romagna paese, ~490 m: pianura/collina).
  // Restano **piani** i corpi plausibilmente piani: uso produttivo, commerciale o sportivo (DBTR/OSM: capannone,
  // commerciale, palestra; tipi DBTR industriali, tettoie, hangar, serre, cabine, tribune, palazzi dello sport), corpi
  // molto grandi (oltre 1.500 m² in pianta) o con il lato corto oltre 25 m, corpi bassi accessori (gronda sotto 3 m),
  // corpi con cortile, poco rettangolari (sotto il 70 % del rettangolo minimo) o più stretti di 2 m.
  const IPOTESI_TETTO = { pianura: 22, montagna: 32, soglia_nord: 600, soglia_centro_sud: 700, area_piano: 1500, lato_piano: 25, gronda_piano: 3 };
  const USI_TETTO_PIANO = ["capannone", "commerciale", "palestra", "industriale"];
  const TIPI_TETTO_PIANO = /industrial|capannone|hangar|tettoia|palazzo dello sport|tribuna|serra|impiant|cabina/i;
  // province del Nord (codice ISTAT del comune = provincia a 3 cifre + progressivo): Piemonte, Valle d'Aosta, Liguria,
  // Lombardia, Trentino-Alto Adige, Veneto, Friuli-Venezia Giulia, Emilia-Romagna
  const PROVINCE_NORD_NUOVE = [93, 96, 97, 98, 99, 103, 108];
  function comuneDelNord(istat) {
    const p = parseInt(String(istat || "").padStart(6, "0").slice(0, 3), 10);
    return Number.isFinite(p) && p > 0 ? p <= 40 || PROVINCE_NORD_NUOVE.includes(p) : null;
  }
  function zonaAltimetrica(quota, istat = null) {
    const nord = comuneDelNord(istat), soglia = nord === false ? IPOTESI_TETTO.soglia_centro_sud : IPOTESI_TETTO.soglia_nord;
    const q = quota === null || quota === undefined || quota === "" ? NaN : +quota;
    const montagna = Number.isFinite(q) && q >= soglia;
    return { montagna, soglia, quota: Number.isFinite(q) ? q : null, inclinazione: montagna ? IPOTESI_TETTO.montagna : IPOTESI_TETTO.pianura };
  }
  function motivoTettoPiano(c, m = undefined) {
    const uso = String((c && c.uso) || "").toLowerCase(), tipo = String((c && (c.tipo_edificio || c.destinazione)) || "");
    if (USI_TETTO_PIANO.includes(uso)) return `uso ${uso === "palestra" ? "sportivo" : uso === "commerciale" ? "commerciale" : "produttivo"} (${uso})`;
    if (TIPI_TETTO_PIANO.test(tipo)) return `tipo di edificio «${tipo}»`;
    if (cortiliDi(c).length) return "corpo con cortile";
    const A = areaCorpo(c);
    if (A > IPOTESI_TETTO.area_piano) return `corpo molto grande (${Math.round(A)} m²)`;
    if (!(c.gronda >= IPOTESI_TETTO.gronda_piano)) return "corpo basso, accessorio (gronda sotto 3 m)";
    if (m === undefined) m = rettangoloTetto(c);
    if (!m || m.A < 1 || A / m.A < RIEMPIMENTO_MIN) return "forma poco rettangolare";
    if (m.Lb > IPOTESI_TETTO.lato_piano) return `lato corto oltre 25 m (${Math.round(m.Lb)} m)`;
    if (m.Lb < 2) return "corpo più stretto di 2 m";
    return null;
  }
  // c: { ring, buchi, gronda, uso, tipo_edificio }; opz: { quota, istat, tipo } (tipo: capanna/padiglione voluto)
  // → { piano: true, motivo } oppure { tipo, falde, colmo, inclinazione, montagna, quota, soglia }
  function tettoIpotizzato(c, opz = {}) {
    if (!c || !Array.isArray(c.ring) || !Number.isFinite(+c.gronda)) return { piano: true, motivo: "corpo senza gronda" };
    const m = rettangoloTetto(c), motivo = motivoTettoPiano(c, m);
    if (motivo) return { piano: true, motivo };
    const z = zonaAltimetrica(opz.quota, opz.istat);
    const colmo = Math.round((+c.gronda + m.Lb / 2 * Math.tan(z.inclinazione * GRAD)) * 100) / 100;
    const r = faldeStimate({ ring: c.ring, buchi: c.buchi, gronda: +c.gronda, colmo }, opz.tipo || null);
    if (!r) return { piano: true, motivo: "forma poco rettangolare" };
    return { tipo: r.tipo, falde: r.falde, colmo, inclinazione: z.inclinazione, montagna: z.montagna, quota: z.quota, soglia: z.soglia };
  }

  const API = { INTERPIANI, CORTILE_MIN_M2, cortiliDi, faldeStimate, rettangoloTetto, IPOTESI_TETTO, USI_TETTO_PIANO, comuneDelNord, zonaAltimetrica, motivoTettoPiano, tettoIpotizzato, RAPPORTO_PADIGLIONE, UN_PIANO, SOVRALZO, NETTA_SU_LORDA, SETTORI, FACOLTATIVE, ETICHETTE, numero, norm, colonnaFacoltativa,
    mappaFacoltative, leggiFacoltative, usoDa, stimaPiani, scegli, superfici, area, centroide, lati, chiudi, indicatori, dividi,
    areaCorpo, dentroCorpo, latiCorpo, anelliOrientati,
    inviluppo, dentro, rettangoloMinimo, proiezione, sole, ombra, orizzonte, altezzaOrizzonte, svf, trasponi, producibilita,
    climaSintetico, firma, altezzaMedia, uniscio, partiFacciate, irraggiamentoFacciate, riepilogoFacciate, QUOTE_199, obbligoFer,
    HT_TAB10, htMassimo, HT_TAB11, HT_TAB11_QUOTE, htMassimoPrimoLivello, FINESTRE_SU_PARETI, quotaVetrataStimata, DA_VISURA,
    daVisura, mappaVisura, leggiVisura, perez, massaAria, posaDaSagoma, PESI_PRIORITA, priorita };
  radice.EUGENIO_EDIFICI = API;
  if (typeof module !== "undefined" && module.exports) module.exports = API;
})(typeof self !== "undefined" ? self : globalThis);
