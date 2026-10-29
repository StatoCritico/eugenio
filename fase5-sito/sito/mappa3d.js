"use strict";
// Mappa tridimensionale della pagina Patrimonio (29/10/2026). SVG scritto a mano, nessuna libreria.
//
// La mappa (comuni della regione scelta, contorno della regione, punti degli edifici) sta su un piano orizzontale;
// una «camera» la guarda con tre angoli: imbardata (rotazione attorno all'asse verticale), inclinazione (0° = vista
// dall'alto, fino a 80°) e rollio (rotazione dell'immagine), con una prospettiva leggera. I percorsi dei comuni
// (dati/mappa/RR.json, solo comandi M, L e Z) diventano poligoni, ogni punto passa per la matrice di rotazione e la
// proiezione, e i percorsi si riscrivono a ogni fotogramma (requestAnimationFrame; durante il movimento si usa un
// punto su due per i poligoni lunghi).
//
// Le barre a mattoncini sono «grattacieli»: la base di ogni gruppo (una sede) si proietta con la camera della mappa,
// ma la barra si disegna sempre in piedi, dal basso verso l'alto dello schermo, come un parallelepipedo visto di lato
// con una vista sua: rotazione delle barre (che può seguire l'imbardata della mappa) e inclinazione delle barre. Facce
// in tre toni dello stesso colore, linee dei mattoncini, ordine dal fondo al davanti (algoritmo del pittore).
//
// Comandi: trascinamento = imbardata e inclinazione; Maiuscolo+trascinamento o tasto destro = rollio;
// Ctrl+trascinamento o tasto centrale = spostamento; Alt+trascinamento = vista delle barre; rotella = zoom attorno al
// puntatore; doppio clic = vista iniziale. Col dito: un dito ruota e inclina, due dita ingrandiscono, ruotano e
// spostano. Tastiera (la mappa prende il fuoco): frecce = imbardata e inclinazione, Maiuscolo+frecce = rollio,
// Ctrl+frecce = spostamento, Alt+frecce = barre, + e − = zoom, 0 = vista dall'alto, 3 = vista 3D. Ci sono anche i
// pulsanti sotto la mappa.
//
//  const m = EUGENIO_MAPPA3D.crea(box, { suCambio(vista, barre) })
//  m.regione({ cod, comuni: [{ istat, nome, prov, d }], contorno: "M…Z" })     comuni e contorno, inquadrati
//  m.punti([{ x, y, classe, etichetta, i }], suClic(i))                      punti (coordinate dei file di mappa)
//  m.barre([{ x, y, titolo, voci: [{ colore, mattoni, latoRel, colonna, testo, chiave }] }])
//        mattoni = valore / valore del mattoncino; latoRel = 1 / (mattoncini del valore più alto tra tutte le scale
//        della mappa: dal 29/10/2026 stessa base per tutte le barre, valori_sedi.js passa lo stesso latoRel a tutte):
//        il lato della base (e del mattoncino cubico) è latoRel × l'altezza massima, così il valore più alto di ogni
//        scala arriva all'altezza massima
//  m.vista("alto" | "3d"), m.inquadra([x0, y0, x1, y1]), m.impostaBarre({ rotazione, inclinazione, segue, altezza })
//  m.esporta({ titolo, legenda: [[colore, testo]], note: [testo] }) → testo SVG autonomo (colori risolti)
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const G = Math.PI / 180;
  const limita = (x, a, b) => Math.min(b, Math.max(a, x));
  const d1 = (x) => Math.round(x * 10) / 10;          // una cifra decimale (più veloce di toFixed nei percorsi lunghi)
  const VISTA_ALTO = { imbardata: 0, inclinazione: 0, rollio: 0, prospettiva: true };
  const VISTA_3D = { imbardata: -20, inclinazione: 55, rollio: 0, prospettiva: true };
  // isometrica «da videogioco»: proiezione ortografica, imbardata 45°, mappa vista a 2:1 (30° sopra l'orizzonte,
  // cioè inclinazione 60°: le diagonali dei quadrati diventano rombi larghi il doppio dell'altezza); le barre con la
  // stessa vista (allineate agli assi della mappa, 30° sopra l'orizzonte)
  // imbardata −45°: il nord punta in alto a destra dello schermo, come nei videogiochi isometrici classici
  const VISTA_ISO = { imbardata: -45, inclinazione: 60, rollio: 0, prospettiva: false };
  // barre: la fila di ogni sede è frontale (rotazione 0) e ogni barra è girata di 30° su se stessa (torsione), così si
  // vedono due facce; con «segue» spento (predefinito) girando la mappa le barre restano così sullo schermo
  const BARRE = { rotazione: 0, inclinazione: 28, segue: false, altezza: 1, torsione: 30 };
  const MARGINE = 0.05;      // inquadratura delle viste predefinite: 5 % di bordo su ogni lato

  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if ((k === "fill" || k === "stroke") && typeof v === "string" && v.startsWith("var(")) e.style.setProperty(k, v);
      else e.setAttribute(k, v);
    }
    if (parent) parent.appendChild(e);
    return e;
  }
  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

  // ------------------------------------------------------------------ colori: var(--…) → [r, g, b], toni delle facce
  const tela = document.createElement("canvas").getContext("2d");
  function rgb(colore) {
    let c = String(colore || "").trim();
    const v = /^var\((--[\w-]+)\)$/.exec(c);
    if (v) c = css(v[1]);
    tela.fillStyle = "#808080"; tela.fillStyle = c || "#808080";
    const n = tela.fillStyle;                       // "#rrggbb" oppure "rgba(r, g, b, a)"
    if (n[0] === "#") return [1, 3, 5].map((i) => parseInt(n.slice(i, i + 2), 16));
    const m = n.match(/[\d.]+/g);
    return m ? m.slice(0, 3).map(Number) : [128, 128, 128];
  }
  const mescola = (c, verso, t) => c.map((x, i) => Math.round(x + (verso[i] - x) * t));
  const testoRgb = (c) => `rgb(${c.join(",")})`;
  // grigio di fondo della mappa 3D quando le regioni visibili sono più di 10: --bordo mescolato con --carta; nel tema
  // scuro un grigio medio (circa rgb(92,88,100) con Corallo), nel chiaro un grigio chiaro (circa rgb(201,197,206))
  const temaScuro = () => document.documentElement.dataset.theme !== "light";
  function fondoNeutro() {
    return testoRgb(mescola(rgb("var(--bordo)"), rgb("var(--carta)"), temaScuro() ? 0.32 : 0.6));
  }
  // fondo di una regione nella mappa 3D: nel tema scuro quello delle altre mappe (EUGENIO.fondoComuni, il colore della
  // regione schiarito), nel chiaro il colore della regione mescolato al 55 % col bianco (le regioni restano riconoscibili)
  function fondoRegione(cod) {
    const E = window.EUGENIO;
    if (!E || !E.colore || !cod) return fondoNeutro();
    return temaScuro() ? E.fondoComuni(cod) : testoRgb(mescola(rgb(E.colore(cod)), [255, 255, 255], 0.55));
  }
  function toni(colore) {
    const c = rgb(colore), bianco = [255, 255, 255], nero = [0, 0, 0];
    return { tetto: testoRgb(mescola(c, bianco, 0.3)), chiaro: testoRgb(c), scuro: testoRgb(mescola(c, nero, 0.3)),
      linee: testoRgb(mescola(c, nero, 0.55)) };
  }

  // percorso "M x,y L x,y … Z M …" → poligoni (array piatti x0, y0, x1, y1 …) e versione ridotta per il movimento
  function poligoni(d) {
    const out = [];
    let cur = null;
    const re = /([MLZ])([^MLZ]*)/gi;
    let m;
    while ((m = re.exec(d))) {
      const cmd = m[1].toUpperCase(), n = m[2].trim() ? m[2].trim().split(/[\s,]+/).map(Number) : [];
      if (cmd === "M") { if (cur && cur.length >= 6) out.push(cur); cur = n.slice(); }
      else if (cmd === "L") { if (cur) cur.push(...n); }
      else { if (cur && cur.length >= 6) out.push(cur); cur = null; }
    }
    if (cur && cur.length >= 6) out.push(cur);
    return out.map((p) => Float64Array.from(p));
  }
  function riduci(p) {
    if (p.length <= 24) return p;
    const r = [];
    for (let i = 0; i < p.length; i += 4) r.push(p[i], p[i + 1]);
    return Float64Array.from(r);
  }

  function crea(box, opz = {}) {
    const svg = el("svg", { class: "mappa3d", role: "application", tabindex: "0", "aria-roledescription": "mappa tridimensionale",
      "aria-label": "Mappa della regione. Frecce: sposta; Ctrl con le frecce: ruota e inclina; Ctrl e Maiuscolo con le frecce: rollio; "
        + "Alt con le frecce: ruota le barre; più e meno: zoom; 0: vista dall'alto; 3: vista 3D; I: vista isometrica." });
    box.prepend(svg);
    const gZoccolo = el("g", { class: "zoccolo" }, svg);
    const gSagome = el("g", { class: "sagome" }, svg);      // regioni intere (solo quando ce n'è più d'una)
    const gComuni = el("g", { class: "comuni" }, svg);
    const gContorno = el("g", { class: "confini-regioni" }, svg);
    const gPunti = el("g", { class: "punti" }, svg);
    const gBarre = el("g", { class: "barre" }, svg);

    const vista = { ...VISTA_ALTO, zoom: 1, cx: 0, cy: 0 };
    const barre = { ...BARRE };
    let W = 600, H = 400, est = 100, k0 = 1, D = 260, codice = null;
    let comuni = [], contorno = [], zoccolo = null, contornoEl = null, sagome = [];
    let punti = [], suClicPunto = null;
    let gruppi = [], elBarre = [], ordine = "", ultimoOrdine = 0;
    let regioneBox = [0, 0, 100, 100];
    let movimento = false, fineMovimento = 0, fotogramma = 0;
    const sugg = window.EUGENIO && window.EUGENIO.suggerimenti
      ? window.EUGENIO.suggerimenti(svg, { contenuto: contenutoBarra }) : null;

    // ---------------------------------------------------------------- proiezione
    let M = null;
    function matrice() {
      const a = vista.imbardata * G, b = vista.inclinazione * G, c = vista.rollio * G;
      M = { ca: Math.cos(a), sa: Math.sin(a), cb: Math.cos(b), sb: Math.sin(b), cc: Math.cos(c), sc: Math.sin(c), k: k0 * vista.zoom };
    }
    const q = [0, 0, 1, 0];
    // (x, y) del file di mappa, z verso l'alto → q = [x schermo, y schermo, fattore prospettico, profondità]
    function proietta(x, y, z) {
      const X = x - vista.cx, Y = vista.cy - y;
      const x1 = X * M.ca - Y * M.sa, y1 = X * M.sa + Y * M.ca;
      const su = y1 * M.cb + z * M.sb, prof = y1 * M.sb - z * M.cb;
      const f = vista.prospettiva === false ? 1 : D / (D + prof);
      const sx = x1 * f, sy = su * f;
      q[0] = W / 2 + M.k * (sx * M.cc - sy * M.sc);
      q[1] = H / 2 - M.k * (sx * M.sc + sy * M.cc);
      q[2] = f; q[3] = prof;
      return q;
    }
    // punto dello schermo → punto del piano della mappa (inversa esatta per z = 0)
    function aTerra(px, py, v = vista) {
      const a = v.imbardata * G, b = v.inclinazione * G, c = v.rollio * G, k = k0 * v.zoom;
      const rx = (px - W / 2) / k, ry = -(py - H / 2) / k;
      const sx = rx * Math.cos(c) + ry * Math.sin(c), sy = -rx * Math.sin(c) + ry * Math.cos(c);
      let y1, f;
      if (v.prospettiva === false) { y1 = Math.abs(Math.cos(b)) < 1e-9 ? 0 : sy / Math.cos(b); f = 1; }
      else {
        const den = Math.cos(b) * D - sy * Math.sin(b);
        y1 = Math.abs(den) < 1e-9 ? 0 : sy * D / den;
        f = D / (D + y1 * Math.sin(b));
      }
      const x1 = sx / f;
      const X = x1 * Math.cos(a) + y1 * Math.sin(a), Y = -x1 * Math.sin(a) + y1 * Math.cos(a);
      return [v.cx + X, v.cy - Y];
    }

    let compatto = false;     // per il report: punti a meno di 1 pixel dal precedente tolti, coordinate intere
    function percorso(poli, ridotto, z) {
      let s = "";
      for (const p of poli) {
        const r = ridotto ? riduci(p) : p;
        let px = NaN, py = NaN, n = 0;
        for (let i = 0; i < r.length; i += 2) {
          proietta(r[i], r[i + 1], z);
          if (compatto) {
            const x = Math.round(q[0]), y = Math.round(q[1]);
            if (n && Math.abs(x - px) + Math.abs(y - py) < 1.5 && i < r.length - 2) continue;
            s += (n ? "L" : "M") + x + "," + y; px = x; py = y; n++;
          } else s += (i ? "L" : "M") + d1(q[0]) + "," + d1(q[1]);
        }
        s += "Z";
      }
      return s;
    }

    // ---------------------------------------------------------------- disegno
    function disegna() {
      fotogramma = 0;
      matrice();
      const rid = movimento;
      for (const c of sagome) c.el.setAttribute("d", percorso(rid ? c.ridotti : c.poli, false, 0));
      for (const c of comuni) c.el.setAttribute("d", percorso(rid ? c.ridotti : c.poli, false, 0));
      if (contornoEl) contornoEl.setAttribute("d", percorso(contorno, rid, 0));
      if (zoccolo) {
        // spessore della base costante sullo schermo (circa 12 pixel), qualunque sia lo zoom
        zoccolo.setAttribute("d", vista.inclinazione > 2 ? percorso(contorno, rid, -12 / M.k) : "");
      }
      const raggio = window.matchMedia("(pointer: coarse)").matches ? 6 : 4.5;
      for (const p of punti) { proietta(p.x, p.y, 0); p.el.setAttribute("cx", q[0].toFixed(1)); p.el.setAttribute("cy", q[1].toFixed(1)); p.el.setAttribute("r", raggio); }
      disegnaBarre();
      if (opz.suCambio) opz.suCambio({ ...vista }, { ...barre });
    }
    function richiedi(inMoto) {
      if (inMoto) {
        movimento = true;
        clearTimeout(fineMovimento);
        fineMovimento = setTimeout(() => { movimento = false; richiedi(); }, 160);
      }
      if (!fotogramma) fotogramma = requestAnimationFrame(disegna);
    }

    // altezza massima delle barre in pixel: circa un terzo del lato corto della mappa, cresce un po' con lo zoom
    const altezzaMassima = () => Math.min(H * 0.55, Math.min(W, H) * 0.28 * Math.pow(vista.zoom, 0.25)) * barre.altezza;

    function disegnaBarre() {
      if (!gruppi.length) return;
      const Hm = altezzaMassima();
      // fila: rotazione propria delle barre, più l'imbardata della mappa se «segue»; senza «segue» la fila resta
      // frontale sullo schermo qualunque sia la rotazione della mappa (le barre «controruotano»)
      const beta = (barre.rotazione + (barre.segue ? vista.imbardata : 0)) * G, alfa = limita(barre.inclinazione, 2, 85) * G;
      const cb = Math.cos(beta), sb = Math.sin(beta), ca = Math.cos(alfa), sa = Math.sin(alfa);
      const ct = Math.cos((barre.torsione || 0) * G), st = Math.sin((barre.torsione || 0) * G);
      const ord = [];
      // mostra o nasconde una barra solo quando cambia (cambiare lo stile di tutte a ogni fotogramma costa)
      const mostra = (v, si) => { if (v.mostrata !== si) { v.mostrata = si; v.el.style.display = si ? "" : "none"; } };
      for (const g of gruppi) {
        const voci = g.voci.filter((v) => v.visibile !== false && v.mattoni > 0);
        g.voci.forEach((v) => { if (!voci.includes(v)) mostra(v, false); });
        if (!voci.length) continue;
        proietta(g.x, g.y, 0);
        const ax = q[0], ay = q[1], s = q[2];
        if (!senzaTaglio && (ax < -200 || ax > W + 200 || ay < -50 || ay > H + Hm * 2)) { voci.forEach((v) => mostra(v, false)); continue; }   // fuori dalla vista
        // le barre del gruppo in fila lungo l'asse u della vista delle barre, centrate sulla sede
        const lati = voci.map((v) => v.latoRel * Hm), spazio = Math.min(...lati) * 0.25;
        // ingombro di una barra girata su se stessa lungo la fila
        const ingombri = lati.map((l) => l * (Math.abs(ct) + Math.abs(st)));
        const totale = ingombri.reduce((a, b) => a + b, 0) + spazio * (voci.length - 1);
        let u = -totale / 2;
        // sedi nello stesso punto (per esempio al centro del comune): in fila verso chi guarda, la più grande in fondo
        const pila = g.pila && g.pila.n > 1 ? g.pila : null;
        const off = pila ? ((pila.n - 1) / 2 - pila.rango) * (Math.max(...ingombri) + spazio * 2) : 0;
        voci.forEach((v, i) => {
          const lato = lati[i], u0 = u + ingombri[i] / 2;
          u += ingombri[i] + spazio;
          mostra(v, true);
          const h = v.mattoni * lato, m = lato / 2;
          // (a, b) nel riferimento della barra (girata di «torsione») → riferimento della fila → schermo
          const P = (a, b, w) => {
            const uu = u0 + a * ct - b * st, vv = a * st + b * ct + off;
            return [ax + (uu * cb - vv * sb) * s, ay - (w * ca + (uu * sb + vv * cb) * sa) * s];
          };
          const pt = (x) => x.map((p) => d1(p[0]) + "," + d1(p[1])).join(" ");
          v.tetto.setAttribute("points", pt([P(-m, -m, h), P(m, -m, h), P(m, m, h), P(-m, m, h)]));
          // facce laterali verso chi guarda (normale con componente di profondità negativa), le due più rivolte
          const facce = [[1, 0], [-1, 0], [0, 1], [0, -1]].map(([nu, nv]) => {
            const ru = nu * ct - nv * st, rv = nu * st + nv * ct;          // normale nel riferimento della fila
            return { nu, nv, prof: ru * sb + rv * cb, lx: ru * cb - rv * sb };
          }).sort((a, b) => a.prof - b.prof).slice(0, 2).sort((a, b) => a.lx - b.lx);
          let linee = "";
          const nm = Math.ceil(v.mattoni - 1e-6) - 1;       // linee tra i mattoncini (l'ultimo, in cima, può essere parziale)
          facce.forEach((f, j) => {
            // gli spigoli della faccia: centro della faccia ± metà lato lungo la sua direzione
            const cu = f.nu * m, cv = f.nv * m, du = -f.nv * m, dv = f.nu * m;
            const a0 = [cu - du, cv - dv], a1 = [cu + du, cv + dv];
            const poli = j === 0 ? v.chiaro : v.scuro;
            poli.setAttribute("points", pt([P(a0[0], a0[1], 0), P(a1[0], a1[1], 0), P(a1[0], a1[1], h), P(a0[0], a0[1], h)]));
            // le linee dei mattoncini si disegnano a mappa ferma: durante il trascinamento le barre sono lisce
            if (!movimento) for (let n = 1; n <= nm; n++) {
              const b0 = P(a0[0], a0[1], n * lato), b1 = P(a1[0], a1[1], n * lato);
              linee += "M" + d1(b0[0]) + "," + d1(b0[1]) + "L" + d1(b1[0]) + "," + d1(b1[1]);
            }
          });
          if (linee || v.conLinee) { v.linee.setAttribute("d", linee); v.conLinee = !!linee; }
          const sw = lato * s > 7 ? 0.9 : 0.6;
          if (v.sw !== sw) { v.sw = sw; v.linee.setAttribute("stroke-width", sw); }
          ord.push({ v, ay, prof: u0 * sb + off * cb });     // profondità del centro della barra
        });
      }
      // pittore: prima le sedi più in alto sullo schermo (più lontane), nel gruppo prima le barre più lontane
      ord.sort((a, b) => (a.ay - b.ay) || (b.prof - a.prof));
      // durante il trascinamento l'ordine si rifà al massimo ogni 120 ms (spostare centinaia di elementi costa)
      const ora = performance.now();
      if (movimento && ora - ultimoOrdine < 120) return;
      const chiave = ord.map((o) => o.v.k).join(",");
      if (chiave !== ordine) { ordine = chiave; ultimoOrdine = ora; for (const o of ord) gBarre.appendChild(o.v.el); }
    }

    function contenutoBarra(t) {
      const b = t && t.closest && t.closest("[data-barra]");
      if (!b) return undefined;                   // non è una barra: vale il riquadretto predefinito (comuni, punti)
      const v = elBarre[+b.dataset.barra];
      if (!v) return null;
      const g = v.gruppo;
      const righe = [[v.coloreTesto, `${v.colonna}: ${v.testo}`]];
      g.voci.forEach((x) => { if (x !== v && x.visibile !== false) righe.push([x.coloreTesto, `${x.colonna}: ${x.testo}`]); });
      if (g.sotto) righe.push([null, g.sotto]);
      return { titolo: g.titolo, righe };
    }

    // ---------------------------------------------------------------- dati
    // scena: regioni intere sotto (sagome, con il loro colore) e comuni sopra; regione(dati) è il caso di una sola
    // regione, scena() quello di più regioni con i comuni solo di alcune province (valori per sede)
    function scena({ sagome: sag = [], comuni: com = [] }) {
      gComuni.innerHTML = ""; gContorno.innerHTML = ""; gZoccolo.innerHTML = ""; gSagome.innerHTML = "";
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      const allarga = (poli) => { for (const p of poli) for (let i = 0; i < p.length; i += 2) {
        if (p[i] < x0) x0 = p[i]; if (p[i] > x1) x1 = p[i]; if (p[i + 1] < y0) y0 = p[i + 1]; if (p[i + 1] > y1) y1 = p[i + 1];
      } };
      const piu = sag.length > 1;
      grigio = sag.length > 10;
      sagome = sag.map((r) => {
        const poli = poligoni(r.d || "");
        allarga(poli);
        const e = el("path", { fill: fondo(r.cod) }, gSagome);
        // nome della regione nelle aree senza comuni disegnati (province senza sedi): riquadretto comune
        if (r.nome) { e.dataset.nome = r.nome; e.dataset.dettaglio = piu ? "regione" : "regione scelta"; }
        return { el: e, poli, ridotti: poli.map(riduci), cod: r.cod };
      });
      comuni = com.map((c) => {
        const poli = poligoni(c.d);
        if (!sag.length) allarga(poli);
        const e = el("path", { fill: fondo(c.cod) }, gComuni);
        e.dataset.nome = c.nome;
        if (c.prov) e.dataset.prov = c.prov;
        return { el: e, poli, ridotti: poli.map(riduci), cod: c.cod };
      });
      contorno = sagome.flatMap((r) => r.poli);
      zoccolo = contorno.length ? el("path", { class: "zoccolo-fianco" }, gZoccolo) : null;
      contornoEl = contorno.length ? el("path", {}, gContorno) : null;
      if (!Number.isFinite(x0)) { x0 = 0; y0 = 0; x1 = 1000; y1 = 1288; }
      regioneBox = [x0, y0, x1, y1];
      est = Math.max(x1 - x0, y1 - y0);
      D = est * 2.6;
      codice = sag.length ? sag[0].cod : codice;
      inquadra(regioneBox, false);
    }
    // fondo della mappa 3D (quarta versione): regioni colorate come nelle altre mappe; con più di 10 regioni visibili
    // tutte grigie. Le barre scelgono colori lontani da quelli delle regioni visibili (valori_sedi.js, coloriVisibili)
    let grigio = false;
    const fondo = (cod) => (grigio ? fondoNeutro() : fondoRegione(cod || codice));
    function coloriVisibili() {
      const cod = sagome.length ? sagome.map((r) => r.cod) : [codice];
      return [...new Set(cod.map((c) => fondo(c)))];
    }
    function regione(dati) {
      codice = dati.cod;
      scena({ sagome: dati.contorno ? [{ cod: dati.cod, d: dati.contorno, nome: dati.nome }] : [],
        comuni: dati.comuni.map((c) => ({ ...c, cod: dati.cod })) });
    }
    function ricolora() {
      [...sagome, ...comuni].forEach((c) => { const f = fondo(c.cod); if (f.startsWith("var(")) c.el.style.fill = f; else c.el.setAttribute("fill", f); });
      gruppi.forEach((g) => g.voci.forEach(coloraVoce));
      richiedi();
    }

    function impostaPunti(lista, suClic) {
      gPunti.innerHTML = "";
      suClicPunto = suClic || null;
      punti = (lista || []).map((p) => {
        const c = el("circle", { class: `punto ${p.classe || ""}`, r: 4.5, tabindex: "-1" }, gPunti);
        if (p.etichetta) c.dataset.nome = p.etichetta;
        c.dataset.i = p.i;
        c.addEventListener("click", () => suClicPunto && suClicPunto(p.i));
        return { ...p, el: c };
      });
      richiedi();
    }

    function coloraVoce(v) {
      const t = toni(v.colore);
      v.coloreTesto = t.chiaro;
      v.tetto.setAttribute("fill", t.tetto);
      v.chiaro.setAttribute("fill", t.chiaro);
      v.scuro.setAttribute("fill", t.scuro);
      [v.tetto, v.chiaro, v.scuro].forEach((p) => p.setAttribute("stroke", t.linee));
      v.linee.setAttribute("stroke", t.linee);
    }
    function impostaBarre(lista) {
      gBarre.innerHTML = "";
      elBarre = [];
      ordine = "";
      gruppi = (lista || []).map((g) => {
        const gr = { ...g, voci: g.voci.map((v) => ({ ...v })) };
        gr.voci.forEach((v) => {
          v.k = elBarre.length;
          v.gruppo = gr;
          v.el = el("g", { class: "barra" }, gBarre);
          v.el.dataset.barra = v.k;
          v.chiaro = el("polygon", { "stroke-width": 0.5, "stroke-linejoin": "round" }, v.el);
          v.scuro = el("polygon", { "stroke-width": 0.5, "stroke-linejoin": "round" }, v.el);
          v.tetto = el("polygon", { "stroke-width": 0.5, "stroke-linejoin": "round" }, v.el);
          v.linee = el("path", { fill: "none" }, v.el);
          coloraVoce(v);
          elBarre.push(v);
        });
        return gr;
      });
      richiedi();
    }
    // cambia colori o visibilità senza rifare gli elementi: { chiave: { colore, visibile } }
    function aggiornaBarre(per) {
      gruppi.forEach((g) => g.voci.forEach((v) => {
        const n = per[v.chiave];
        if (!n) return;
        if (n.colore && n.colore !== v.colore) { v.colore = n.colore; coloraVoce(v); }
        if (n.visibile !== undefined) v.visibile = n.visibile;
      }));
      ordine = "";
      richiedi();
    }

    // ---------------------------------------------------------------- vista
    function misura() {
      const r = box.getBoundingClientRect();
      W = Math.max(120, Math.round(r.width));
      H = Math.max(120, Math.round(r.height));
      svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
      const [x0, y0, x1, y1] = regioneBox;
      k0 = Math.min(W / Math.max(1, x1 - x0), H / Math.max(1, y1 - y0)) * 0.92;
    }
    function inquadra(bbox, conZoom = true) {
      misura();
      const [x0, y0, x1, y1] = bbox;
      vista.cx = (x0 + x1) / 2; vista.cy = (y0 + y1) / 2;
      if (conZoom) {
        const kk = Math.min(W / Math.max(1, x1 - x0), H / Math.max(1, y1 - y0)) * 0.86;
        vista.zoom = limita(kk / k0, 0.4, 40);
      } else vista.zoom = 1;
      richiedi();
    }
    function imposta(v, inMoto) {
      if (v.imbardata !== undefined) vista.imbardata = ((v.imbardata + 540) % 360) - 180;
      if (v.inclinazione !== undefined) vista.inclinazione = limita(v.inclinazione, 0, 80);
      if (v.rollio !== undefined) vista.rollio = ((v.rollio + 540) % 360) - 180;
      if (v.zoom !== undefined) vista.zoom = limita(v.zoom, 0.4, 40);
      if (v.cx !== undefined) { vista.cx = v.cx; vista.cy = v.cy; }
      richiedi(inMoto);
    }
    function vistaNominata(nome) {
      misura();
      sugg && sugg.nascondi();
      Object.assign(vista, nome === "3d" ? VISTA_3D : nome === "iso" ? VISTA_ISO : VISTA_ALTO,
        { zoom: 1, cx: (regioneBox[0] + regioneBox[2]) / 2, cy: (regioneBox[1] + regioneBox[3]) / 2 });
      if (nome === "3d") { Object.assign(barre, { inclinazione: BARRE.inclinazione, torsione: BARRE.torsione }); barreDiFronte(false); }
      // isometrica: barre allineate agli assi della mappa (fila lungo l'est), viste anch'esse a 30° sull'orizzonte
      if (nome === "iso") Object.assign(barre, { inclinazione: 30, torsione: 0, rotazione: barre.segue ? 0 : VISTA_ISO.imbardata });
      vista.ultima = nome;
      adatta();
    }
    // fila delle barre di nuovo frontale (azzera la loro rotazione propria)
    function barreDiFronte(ridisegna = true) {
      barre.rotazione = barre.segue ? -vista.imbardata : 0;
      barre.torsione = BARRE.torsione;
      if (ridisegna) richiedi();
    }
    // inquadratura: zoom e centro tali che mappa visibile e cime delle barre stiano nella finestra con il 5 % di bordo
    // su ogni lato (le barre crescono un po' con lo zoom e c'è la prospettiva: si ripete qualche volta)
    let senzaTaglio = false;
    function riquadroSchermo() {
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      for (const g of [gZoccolo, gSagome, gComuni, gContorno, gBarre, gPunti]) {
        if (!g.childElementCount) continue;
        let b;
        try { b = g.getBBox(); } catch { continue; }
        if (!b.width && !b.height) continue;
        x0 = Math.min(x0, b.x); y0 = Math.min(y0, b.y); x1 = Math.max(x1, b.x + b.width); y1 = Math.max(y1, b.y + b.height);
      }
      return Number.isFinite(x0) ? [x0, y0, x1, y1] : null;
    }
    function adatta() {
      misura();
      senzaTaglio = true;
      movimento = false;
      try {
        for (let i = 0; i < 5; i++) {
          disegna();
          const r = riquadroSchermo();
          if (!r) break;
          const bw = Math.max(1, r[2] - r[0]), bh = Math.max(1, r[3] - r[1]);
          matrice();
          const c = aTerra((r[0] + r[2]) / 2, (r[1] + r[3]) / 2), c0 = aTerra(W / 2, H / 2);
          vista.cx += c[0] - c0[0]; vista.cy += c[1] - c0[1];
          const f = Math.min(W * (1 - 2 * MARGINE) / bw, H * (1 - 2 * MARGINE) / bh);
          vista.zoom = limita(vista.zoom * f, 0.4, 40);
          if (Math.abs(f - 1) < 0.01 && Math.abs((r[0] + r[2]) / 2 - W / 2) < 2 && Math.abs((r[1] + r[3]) / 2 - H / 2) < 2) break;
        }
        disegna();
      } finally { senzaTaglio = false; }
    }
    function impostaVistaBarre(b, inMoto) {
      if (b.rotazione !== undefined) barre.rotazione = ((b.rotazione + 540) % 360) - 180;
      if (b.inclinazione !== undefined) barre.inclinazione = limita(b.inclinazione, 5, 80);
      if (b.segue !== undefined) barre.segue = !!b.segue;
      if (b.altezza !== undefined) barre.altezza = limita(b.altezza, 0.3, 3);
      richiedi(inMoto);
    }
    // zoom di un fattore attorno a un punto dello schermo (il punto della mappa sotto il puntatore resta lì)
    function zoomA(f, px = W / 2, py = H / 2) {
      matrice();
      const prima = aTerra(px, py);
      vista.zoom = limita(vista.zoom * f, 0.4, 40);
      const dopo = aTerra(px, py);
      vista.cx += prima[0] - dopo[0]; vista.cy += prima[1] - dopo[1];
      richiedi(true);
    }

    // ---------------------------------------------------------------- puntatore
    const dita = new Map();
    let gesto = null, trascinato = false;
    const punto = (e) => { const r = svg.getBoundingClientRect(); return [(e.clientX - r.left) * W / r.width, (e.clientY - r.top) * H / r.height]; };
    function avvia(e) {
      const p = [...dita.values()];
      if (p.length === 1) {
        // trascinamento semplice (e un dito) = spostamento; Ctrl (o ⌘, o tasto destro) = rotazione e inclinazione;
        // Ctrl+Maiuscolo (o Maiuscolo col tasto destro) = rollio; Alt = vista delle barre
        let modo = "sposta";
        const ruota = e.ctrlKey || e.metaKey || e.button === 2;
        if (e.altKey) modo = "barre";
        else if (ruota && e.shiftKey) modo = "rollio";
        else if (ruota) modo = "ruota";
        gesto = { modo, x: p[0][0], y: p[0][1], v: { ...vista }, b: { ...barre } };
      } else if (p.length >= 2) {
        const [a, b] = p;
        gesto = { modo: "dita", centro: [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2], dist: Math.hypot(a[0] - b[0], a[1] - b[1]) || 1,
          ang: Math.atan2(b[1] - a[1], b[0] - a[0]), v: { ...vista } };
        gesto.terra = aTerra(gesto.centro[0], gesto.centro[1], gesto.v);
      }
    }
    svg.addEventListener("contextmenu", (e) => e.preventDefault());
    svg.addEventListener("pointerdown", (e) => {
      if (e.pointerType === "mouse" && e.button > 2) return;
      if (e.button === 1) e.preventDefault();
      dita.set(e.pointerId, punto(e));
      trascinato = false;
      avvia(e);
    });
    svg.addEventListener("pointermove", (e) => {
      if (!dita.has(e.pointerId) || !gesto) return;
      dita.set(e.pointerId, punto(e));
      const p = [...dita.values()], v0 = gesto.v;
      if (gesto.modo === "dita" && p.length >= 2) {
        const [a, b] = p, centro = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
        const dist = Math.hypot(a[0] - b[0], a[1] - b[1]) || 1, ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
        trascinato = true;
        const nuova = { ...v0, zoom: limita(v0.zoom * dist / gesto.dist, 0.4, 40), imbardata: v0.imbardata - (ang - gesto.ang) / G };
        // il punto della mappa che stava sotto le dita resta sotto le dita
        const t = aTerra(centro[0], centro[1], nuova);
        nuova.cx = v0.cx + gesto.terra[0] - t[0]; nuova.cy = v0.cy + gesto.terra[1] - t[1];
        imposta(nuova, true);
      } else if (p.length === 1 && gesto.modo !== "dita") {
        const dx = p[0][0] - gesto.x, dy = p[0][1] - gesto.y;
        if (!trascinato && Math.hypot(dx, dy) < 4) return;
        if (!trascinato) { trascinato = true; try { svg.setPointerCapture(e.pointerId); } catch { /* già rilasciato */ } }
        svg.classList.add("trascina");
        sugg && sugg.nascondi();
        if (gesto.modo === "ruota") imposta({ imbardata: v0.imbardata - dx * 0.4, inclinazione: v0.inclinazione - dy * 0.3 }, true);
        else if (gesto.modo === "rollio") imposta({ rollio: v0.rollio + dx * 0.4 }, true);
        else if (gesto.modo === "barre") impostaVistaBarre({ rotazione: gesto.b.rotazione - dx * 0.5, inclinazione: gesto.b.inclinazione + dy * 0.3 }, true);
        else if (gesto.modo === "sposta") {
          const a = aTerra(gesto.x, gesto.y, v0), b = aTerra(p[0][0], p[0][1], v0);
          imposta({ cx: v0.cx + a[0] - b[0], cy: v0.cy + a[1] - b[1] }, true);
        }
      }
    });
    const fine = (e) => {
      if (!dita.has(e.pointerId)) return;
      dita.delete(e.pointerId);
      if (dita.size) avvia(e); else { gesto = null; setTimeout(() => svg.classList.remove("trascina"), 0); }
    };
    svg.addEventListener("pointerup", fine);
    svg.addEventListener("pointercancel", fine);
    // un trascinamento non vale come clic su un punto
    svg.addEventListener("click", (e) => { if (trascinato) { e.stopPropagation(); e.preventDefault(); trascinato = false; } }, true);
    svg.addEventListener("wheel", (e) => {
      e.preventDefault();
      const d = e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 400 : 1);
      const [x, y] = punto(e);
      zoomA(Math.exp(-d * 0.0015), x, y);
    }, { passive: false });
    svg.addEventListener("dblclick", (e) => { e.preventDefault(); vistaNominata(gruppi.length ? "3d" : "alto"); });
    svg.addEventListener("keydown", (e) => {
      const passo = 10, frecce = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
      if (frecce[e.key]) {
        const [dx, dy] = frecce[e.key];
        const ruota = e.ctrlKey || e.metaKey;
        if (e.altKey) impostaVistaBarre({ rotazione: barre.rotazione + dx * passo, inclinazione: barre.inclinazione - dy * 5 }, true);
        else if (ruota && e.shiftKey) imposta({ rollio: vista.rollio + dx * passo }, true);
        else if (ruota) imposta({ imbardata: vista.imbardata + dx * passo, inclinazione: vista.inclinazione - dy * 5 }, true);
        else {
          matrice();
          const a = aTerra(W / 2, H / 2), b = aTerra(W / 2 + dx * W * 0.1, H / 2 + dy * H * 0.1);
          imposta({ cx: vista.cx + b[0] - a[0], cy: vista.cy + b[1] - a[1] }, true);
        }
      } else if (e.key === "+" || e.key === "=") zoomA(1.25);
      else if (e.key === "-" || e.key === "_") zoomA(0.8);
      else if (e.key === "0") vistaNominata("alto");
      else if (e.key === "3") vistaNominata("3d");
      else if (e.key === "i" || e.key === "I") vistaNominata("iso");
      else return;
      e.preventDefault();
    });

    // ---------------------------------------------------------------- pulsanti sotto la mappa
    const comandi = document.createElement("div");
    comandi.className = "mappa3d-comandi";
    comandi.setAttribute("role", "toolbar");
    comandi.setAttribute("aria-label", "Comandi della mappa");
    const gruppiPulsanti = [
      ["Zoom", [["−", "Rimpicciolisci", () => zoomA(0.8)], ["+", "Ingrandisci", () => zoomA(1.25)]]],
      ["Vista", [["Dall'alto", "Vista dall'alto (tasto 0)", () => vistaNominata("alto")], ["3D", "Vista 3D predefinita (tasto 3)", () => vistaNominata("3d")],
        ["Isometrica", "Vista isometrica, come nei videogiochi: senza prospettiva, mappa vista a 2:1 (tasto I)", () => vistaNominata("iso")]]],
      ...(opz.pulsanti || []),
      ["Ruota", [["↺", "Ruota la mappa a sinistra", () => imposta({ imbardata: vista.imbardata - 15 })], ["↻", "Ruota la mappa a destra", () => imposta({ imbardata: vista.imbardata + 15 })]]],
      ["Inclina", [["−", "Inclina di meno, verso la vista dall'alto", () => imposta({ inclinazione: vista.inclinazione - 10 })], ["+", "Inclina di più", () => imposta({ inclinazione: vista.inclinazione + 10 })]]],
      ["Rollio", [["↺", "Rollio a sinistra", () => imposta({ rollio: vista.rollio - 15 })], ["↻", "Rollio a destra", () => imposta({ rollio: vista.rollio + 15 })]]],
    ];
    for (const [nome, pulsanti] of gruppiPulsanti) {
      const g = document.createElement("span");
      g.className = "mappa3d-gruppo";
      g.setAttribute("role", "group");
      g.setAttribute("aria-label", nome);
      g.dataset.gruppo = nome;
      const t = document.createElement("span"); t.className = "mappa3d-nome"; t.textContent = nome; g.appendChild(t);
      for (const [testo, titolo, fa] of pulsanti) {
        const b = document.createElement("button");
        b.type = "button"; b.textContent = testo; b.title = titolo; b.setAttribute("aria-label", titolo);
        b.addEventListener("click", fa);
        g.appendChild(b);
      }
      comandi.appendChild(g);
    }
    box.after(comandi);
    // i gruppi aggiunti dalla pagina (opz.pulsanti) si possono nascondere: data-gruppo = nome del gruppo

    if ("ResizeObserver" in window) {
      let attesa = 0;
      new ResizeObserver(() => { cancelAnimationFrame(attesa); attesa = requestAnimationFrame(() => { misura(); richiedi(); }); }).observe(box);
    } else addEventListener("resize", () => { misura(); richiedi(); });
    document.addEventListener("eugenio:aspetto", ricolora);

    // ---------------------------------------------------------------- esportazione in SVG piatto
    const xml = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    function esporta({ titolo = "", legenda = [], note = [], leggero = false } = {}) {
      sugg && sugg.nascondi();
      movimento = false;
      compatto = leggero;
      try { disegna(); } finally { compatto = false; }
      const carta = testoRgb(rgb("var(--carta)")), inchiostro = testoRgb(rgb("var(--inchiostro)")), tenue = testoRgb(rgb("var(--tenue)"));
      const copia = appiattisci(svg, leggero);
      if (leggero) richiedi();            // la mappa nella pagina torna con tutti i punti
      // titolo in alto, legenda e note in basso (a capo quando la riga è piena)
      const corpo = 12, riga = 17, carattere = corpo * 0.56, testa = titolo ? 34 : 10;
      const piedi = [];
      let x = 12, y = 0, righeLegenda = legenda.length ? 1 : 0;
      for (const [colore, testo] of legenda) {
        const larg = 18 + testo.length * carattere + 18;
        if (x + larg > W - 8 && x > 12) { x = 12; righeLegenda++; }
        piedi.push({ colore, testo, x, r: righeLegenda - 1 });
        x += larg;
      }
      const righeNote = [];
      const massimo = Math.max(20, Math.floor((W - 24) / (11 * 0.5)));
      for (const n of note) {
        let r = "";
        for (const parola of String(n).split(" ")) {
          if ((r + " " + parola).trim().length > massimo) { righeNote.push(r.trim()); r = parola; } else r += " " + parola;
        }
        if (r.trim()) righeNote.push(r.trim());
      }
      const altoPiede = 10 + righeLegenda * riga + (righeNote.length ? 6 + righeNote.length * (riga - 2) : 0) + 8;
      const HT = testa + H + altoPiede;
      const font = "font-family=\"Hanken Grotesk, Helvetica, Arial, sans-serif\"";
      let s = `<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${HT}" viewBox="0 0 ${W} ${HT}">\n`;
      s += `<title>${xml(titolo || "Mappa di EuGEnio")}</title>\n<rect x="0" y="0" width="${W}" height="${HT}" fill="${carta}"/>\n`;
      if (titolo) s += `<text x="12" y="23" ${font} font-size="16" font-weight="700" fill="${inchiostro}">${xml(titolo)}</text>\n`;
      copia.removeAttribute("viewBox"); copia.removeAttribute("width"); copia.removeAttribute("height");
      s += `<g transform="translate(0,${testa})">${copia.innerHTML}</g>\n`;
      y = testa + H + 10;
      for (const p of piedi) {
        const yy = y + p.r * riga;
        s += `<rect x="${p.x}" y="${yy + 2}" width="12" height="12" rx="2" fill="${p.colore}"/>`;
        s += `<text x="${p.x + 18}" y="${yy + 12}" ${font} font-size="${corpo}" fill="${inchiostro}">${xml(p.testo)}</text>\n`;
      }
      y += righeLegenda * riga + (righeNote.length ? 6 : 0);
      righeNote.forEach((r, i) => { s += `<text x="12" y="${y + 11 + i * (riga - 2)}" ${font} font-size="11" fill="${tenue}">${xml(r)}</text>\n`; });
      s += "</svg>\n";
      return s;
    }

    misura();
    const oggetto = {
      svg, regione, punti: impostaPunti, barre: impostaBarre, aggiornaBarre, vista: vistaNominata, inquadra, imposta,
      impostaBarre: impostaVistaBarre, zoom: zoomA, esporta, ridisegna: () => richiedi(),
      statoVista: () => ({ ...vista }), statoBarre: () => ({ ...barre }), ricolora, scena, comandi, adatta, coloriVisibili,
      barreDiFronte: () => barreDiFronte(true),
      // per «Copia la vista sull'altra mappa»: camera e vista delle barre insieme
      statoCompleto: () => ({ vista: { ...vista }, barre: { ...barre } }),
      applica(st) { if (!st) return; Object.assign(vista, st.vista); Object.assign(barre, st.barre); misura(); richiedi(); },
      dimensioni: () => [W, H],
    };
    return oggetto;
  }

  // copia piatta di un SVG della pagina: colori, spessori, trasparenze e caratteri calcolati dal CSS scritti come
  // attributi (fuori dal sito var(--…) non vale), senza classi, dati, ruoli e strati di servizio (riquadretti)
  const PROPRIETA = ["fill", "fill-opacity", "stroke", "stroke-width", "stroke-opacity", "stroke-linejoin", "stroke-dasharray",
    "opacity", "font-size", "font-weight", "font-family", "text-anchor"];
  function appiattisci(svg, leggero = false) {
    const copia = svg.cloneNode(true);
    const orig = [svg, ...svg.querySelectorAll("*")], dest = [copia, ...copia.querySelectorAll("*")];
    orig.forEach((o, i) => {
      const d = dest[i];
      if (i > 0) {
        const cs = getComputedStyle(o);
        if (cs.display === "none" || cs.visibility === "hidden" || o.classList.contains("osserva")) { d.remove(); return; }
        const testo = o.tagName === "text" || o.tagName === "tspan";
        for (const p of PROPRIETA) {
          if (!testo && /^(font|text-anchor)/.test(p)) continue;
          let v = cs.getPropertyValue(p);
          if (!v || (p === "stroke-dasharray" && v === "none")) continue;
          if (p === "fill" || p === "stroke") v = v === "none" ? "none" : testoRgb(rgb(v));
          if (p === "font-family") v = "Hanken Grotesk, Helvetica, Arial, sans-serif";
          else if (p !== "fill" && p !== "stroke" && p !== "font-weight" && p !== "text-anchor") v = v.replace(/px/g, "").replace(/\s*,\s*/g, " ");
          d.setAttribute(p, v);
        }
      }
      d.removeAttribute("style"); d.removeAttribute("class"); d.removeAttribute("tabindex"); d.removeAttribute("focusable");
      [...d.attributes].forEach((a) => { if (a.name.startsWith("data-") || a.name.startsWith("aria-") || a.name === "role") d.removeAttribute(a.name); });
    });
    if (leggero) {
      // attributi uguali in tutti i figli di un gruppo: scritti una volta sul gruppo (file molto più piccolo)
      copia.querySelectorAll("g").forEach((g) => {
        const figli = [...g.children];
        if (figli.length < 2) return;
        for (const p of PROPRIETA) {
          const v = figli[0].getAttribute(p);
          if (v !== null && figli.every((f) => f.getAttribute(p) === v)) { g.setAttribute(p, v); figli.forEach((f) => f.removeAttribute(p)); }
        }
      });
    }
    return copia;
  }

  window.EUGENIO_MAPPA3D = { crea, poligoni, appiattisci, rgb, testoRgb, fondoNeutro };
})();
