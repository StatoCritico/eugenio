"use strict";
// Gruppi di ore (14/11/2026), controllo comune delle pagine «Trattamento aria» (Ore di funzionamento, Carichi latenti,
// Free cooling e recupero). Fino a 4 gruppi; per ognuno: nome (va in legenda), «Mostra», anni (ultimo anno · 2 · 5 · 10 ·
// 20 · tutta la serie caricata), data da/a (giorno/mese, ripetuti ogni anno, anche a cavallo d'anno), ora da/a (ora locale
// Europe/Rome, anche a cavallo della mezzanotte: l'ora h è compresa se da ≤ h < a, scritto sotto i campi: «dalle 8 alle
// 18, cioè ore 8:00–17:59»), giorni (tutti o feriali lun–ven) e i
// pulsanti Estate · Inverno · Tutto l'anno · Ore d'ufficio · Tutto il giorno.
//
// Parte pura (anche in node, per i test): campiOrari(serie) calcola una volta per serie anno, mese, giorno, ora locale
// (ora legale italiana: dal 1996 la regola europea, dall'ultima domenica di marzo alle 01 UTC all'ultima domenica di
// ottobre alle 01 UTC; prima del 1996 le date storiche dell'Italia prese da tzdata, Europe/Rome: 1940–1948 periodi di
// guerra e dopoguerra, niente ora legale 1949–1965, 1966–1979 da fine maggio a fine settembre, 1980–1995 fino a fine
// settembre; senza Intl per ogni ora), giorno della settimana (0 = lunedì, giusto anche prima del 1970) e
// mmgg = mese·100 + giorno; filtra(serie, gruppo) dà gli
// indici delle ore (Uint32Array) in pochi millisecondi anche su 750.000 ore.
// Parte nella pagina: EUGENIO_GRUPPI_ORE.crea(box, opz) → controllo (vedi API_MODULI_ARIA e README della fase 5).
(function (radice) {
  const ORA = 3600000;
  const ANNI = [1, 2, 5, 10, 20, 0];                     // 0 = tutta la serie caricata
  const ETICHETTE_ANNI = ["ultimo anno", "2", "5", "10", "20", "tutta la serie"];
  // periodi di accensione del DPR 412/93 (art. 9) per l'«Inverno secondo la zona climatica»
  const ZONE = { A: ["01/12", "15/03"], B: ["01/12", "31/03"], C: ["15/11", "31/03"], D: ["01/11", "15/04"], E: ["15/10", "15/04"] };
  const PRESET = {
    estate: { nome: "Estate", da: "01/06", a: "30/09" },
    inverno: { nome: "Inverno", da: "01/11", a: "31/03" },
    anno: { nome: "Tutto l'anno", da: "01/01", a: "31/12" },
    ufficio: { nome: "Ore d'ufficio", oraDa: 8, oraA: 18, giorni: "feriali" },
    giorno: { nome: "Tutto il giorno", oraDa: 0, oraA: 24, giorni: "tutti" },
  };
  const NOMI_PRESET = [["estate", "Estate"], ["inverno", "Inverno"], ["anno", "Tutto l'anno"], ["ufficio", "Ore d'ufficio"], ["giorno", "Tutto il giorno"]];
  const PREDEFINITO = { nome: "Tutto l'anno", mostra: true, anni: 0, da: "01/01", a: "31/12", oraDa: 0, oraA: 24, giorni: "tutti" };

  // ------------------------------------------------------------------ date senza Intl
  // giorni dal 1970-01-01 → [anno, mese 1-12, giorno] (algoritmo di H. Hinnant)
  function civile(z) {
    z += 719468;
    const era = Math.floor(z / 146097), doe = z - era * 146097;
    const yoe = Math.floor((doe - Math.floor(doe / 1460) + Math.floor(doe / 36524) - Math.floor(doe / 146096)) / 365);
    const doy = doe - (365 * yoe + Math.floor(yoe / 4) - Math.floor(yoe / 100));
    const mp = Math.floor((5 * doy + 2) / 153), d = doy - Math.floor((153 * mp + 2) / 5) + 1, m = mp < 10 ? mp + 3 : mp - 9;
    return [yoe + era * 400 + (m <= 2 ? 1 : 0), m, d];
  }
  // ora legale in Italia prima del 1996 (tzdata, Europe/Rome): coppie [inizio, fine) in ore UTC dal 1970-01-01
  const LEGALE_STORICA = [-259009, -238127, -234599, -230063, -225695, -221687, -216959, -212977, -208583, -203711, -199849, -194977, -191447, -186239, -31681, -28658, -22777, -19921, -14041, -11185, -5137, -2281, 3599, 6455, 12167, 15191, 21071, 24095, 29975, 32831, 38543, 41567, 47447, 50303, 56183, 59039, 64751, 67775, 73655, 76679, 82391, 85415, 89953, 94153, 98521, 102889, 107257, 111625, 115993, 120361, 124729, 129265, 133633, 138001, 142369, 146737, 151105, 155473, 159841, 164209, 168577, 172945, 177313, 181849, 186217, 190585, 194953, 199321, 203689, 208057, 212425, 216793, 221161, 225529];
  const FINE_STORICA = 1996;
  // ora (UTC, ore dal 1970) dell'ultima domenica del mese alle 01 UTC
  function ultimaDomenica01(anno, mese) {
    const fine = Date.UTC(anno, mese, 0);                     // ultimo giorno del mese (mese 1-12)
    const dow = new Date(fine).getUTCDay();                   // 0 = domenica
    return (fine - dow * 86400000) / ORA + 1;
  }
  function leggiInizio(serie) {
    if (typeof serie.inizio === "number") return serie.inizio;
    return Date.parse(String(serie.inizio).replace(/Z?$/, "Z").replace(/:00ZZ$/, ":00Z"));
  }

  const copieCampi = new WeakMap();
  function campiOrari(serie) {
    const chiave = serie.t || serie;
    const c = copieCampi.get(chiave);
    if (c) return c;
    const n = serie.n || serie.t.length, base = Math.round(leggiInizio(serie) / ORA);
    const anno = new Uint16Array(n), mese = new Uint8Array(n), giorno = new Uint8Array(n), ora = new Uint8Array(n),
      dow = new Uint8Array(n), mmgg = new Uint16Array(n);
    const a0 = civile(Math.floor(base / 24))[0] - 1, a1 = civile(Math.floor((base + n) / 24))[0] + 1;
    const legale = [];
    for (let j = 0; j < LEGALE_STORICA.length; j += 2) legale.push([LEGALE_STORICA[j], LEGALE_STORICA[j + 1]]);
    for (let a = Math.max(a0, FINE_STORICA); a <= Math.max(a1, FINE_STORICA); a++) legale.push([ultimaDomenica01(a, 3), ultimaDomenica01(a, 10)]);
    let k = 0, giornoPrima = NaN, ym = [0, 0, 0];
    for (let i = 0; i < n; i++) {
      const u = base + i;
      while (k < legale.length - 1 && u >= legale[k][1]) k++;
      const L = u + (u >= legale[k][0] && u < legale[k][1] ? 2 : 1);
      const g = Math.floor(L / 24);
      if (g !== giornoPrima) { ym = civile(g); giornoPrima = g; }
      anno[i] = ym[0]; mese[i] = ym[1]; giorno[i] = ym[2]; ora[i] = L - g * 24;
      dow[i] = ((g + 3) % 7 + 7) % 7; mmgg[i] = ym[1] * 100 + ym[2];   // g < 0 prima del 1970: % di JS è negativo
    }
    const r = { n, anno, mese, giorno, ora, dow, mmgg, base };
    copieCampi.set(chiave, r);
    return r;
  }

  // «gg/mm» → mese·100 + giorno (null se non valida)
  function leggiData(s) {
    const m = /^\s*(\d{1,2})\s*[/.-]\s*(\d{1,2})\s*$/.exec(String(s || ""));
    if (!m) return null;
    const g = +m[1], me = +m[2];
    if (me < 1 || me > 12 || g < 1 || g > [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][me - 1]) return null;
    return me * 100 + g;
  }
  // primo indice degli «ultimi N anni» (N×12 mesi fino all'ultima ora della serie); 0 per tutta la serie
  function inizioAnni(serie, anni) {
    const n = serie.n || serie.t.length;
    if (!anni) return 0;
    // come il server (inizio_finestra: ultima ora + 1 h − N anni, con il 29/02 portato al 28/02 negli anni non bisestili)
    const t0 = leggiInizio(serie), fine = new Date(t0 + n * ORA);
    const a = fine.getUTCFullYear() - anni, m = fine.getUTCMonth();
    const g = Math.min(fine.getUTCDate(), new Date(Date.UTC(a, m + 1, 0)).getUTCDate());
    const taglio = Date.UTC(a, m, g, fine.getUTCHours());
    return Math.max(0, Math.min(n, Math.round((taglio - t0) / ORA)));
  }
  // anni (con decimali) coperti dalla serie
  const anniSerie = (serie) => ((serie.n || serie.t.length) - 1) / 8766;

  // indici delle ore del gruppo (Uint32Array). Ore senza T o UR escluse (salvo { mancanti: true })
  function filtra(serie, gruppo, opz = {}) {
    const C = campiOrari(serie), n = C.n, g = { ...PREDEFINITO, ...gruppo };
    const da = leggiData(g.da) || 101, a = leggiData(g.a) || 1231;
    const oda = Math.max(0, Math.min(24, Math.round(+g.oraDa || 0))), oa = Math.max(0, Math.min(24, Math.round(g.oraA === undefined ? 24 : +g.oraA)));
    const tutteOre = oda === oa || (oda === 0 && oa === 24), feriali = g.giorni === "feriali";
    const okOra = new Uint8Array(24);
    for (let h = 0; h < 24; h++) okOra[h] = tutteOre ? 1 : (oda < oa ? (h >= oda && h < oa) : (h >= oda || h < oa)) ? 1 : 0;
    const t = serie.t, u = serie.ur, mancanti = !!opz.mancanti, attraverso = da > a;
    const out = new Uint32Array(n);
    let k = 0;
    for (let i = inizioAnni(serie, g.anni); i < n; i++) {
      const d = C.mmgg[i];
      if (attraverso ? (d < da && d > a) : (d < da || d > a)) continue;
      if (!okOra[C.ora[i]] || (feriali && C.dow[i] > 4)) continue;
      if (!mancanti && (!(t[i] === t[i]) || !(u[i] === u[i]))) continue;
      out[k++] = i;
    }
    return out.slice(0, k);
  }
  // un preset applicato a un gruppo (zona: lettera DPR 412 per l'«Inverno secondo la zona», facoltativa)
  function applicaPreset(gruppo, nome, zona) {
    const p = { ...PRESET[nome] };
    if (nome === "inverno" && zona && ZONE[zona]) { p.da = ZONE[zona][0]; p.a = ZONE[zona][1]; p.nome = `Inverno (zona ${zona})`; }
    const g = { ...gruppo, ...p };
    // il nome si cambia solo se è vuoto, «Gruppo N» o il nome di un preset: un nome scritto dall'utente resta; i preset
    // delle ore (ufficio, tutto il giorno) non tolgono il nome di un periodo (Estate resta Estate)
    const vecchio = String(gruppo.nome || "").trim();
    const nomiPeriodo = ["Estate", "Inverno", "Tutto l'anno"], nomiOre = ["Ore d'ufficio", "Tutto il giorno"];
    const dalPreset = !vecchio || /^Gruppo \d$/.test(vecchio) || /^Inverno \(zona [A-F]\)$/.test(vecchio) || nomiPeriodo.includes(vecchio) || nomiOre.includes(vecchio);
    const periodo = nome === "estate" || nome === "inverno" || nome === "anno";
    if (!dalPreset || (!periodo && vecchio && !nomiOre.includes(vecchio) && !/^Gruppo \d$/.test(vecchio))) g.nome = vecchio;
    return g;
  }

  const API = { ANNI, ETICHETTE_ANNI, PRESET, ZONE, PREDEFINITO, civile, ultimaDomenica01, campiOrari, leggiData, inizioAnni,
    anniSerie, filtra, applicaPreset };
  radice.EUGENIO_GRUPPI_ORE = API;
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  if (typeof document === "undefined") return;

  // ------------------------------------------------------------------ controllo nella pagina
  const MAX = 4;
  const fmt = (n, d = 0) => Number(n).toLocaleString("it-IT", { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: "always" });   // 4.357 ore, non 4357
  function h(tag, cls, testo) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (testo !== undefined && testo !== null) e.textContent = testo;
    return e;
  }
  let conta = 0;
  // cursore a scatti «ultimo anno · 2 · 5 · 10 · 20 · tutta la serie» (stesso aspetto del passo 1)
  function cursoreAnni(etichetta, valore, suCambio) {
    const id = `aria-anni-g${++conta}`;
    const box = h("div", "aria-cursore");
    const l = h("label", null, etichetta); l.htmlFor = id;
    const r = document.createElement("input");
    r.type = "range"; r.min = "0"; r.max = String(ANNI.length - 1); r.step = "1"; r.id = id;
    r.value = String(Math.max(0, ANNI.indexOf(valore)));
    const scala = h("div", "aria-cursore-scala");
    scala.setAttribute("aria-hidden", "true");
    ETICHETTE_ANNI.forEach((t) => scala.appendChild(h("span", null, t)));
    const testo = () => (ANNI[+r.value] === 0 ? "tutta la serie caricata" : ANNI[+r.value] === 1 ? "ultimo anno" : `ultimi ${ANNI[+r.value]} anni`);
    r.setAttribute("aria-valuetext", testo());
    r.addEventListener("input", () => { r.setAttribute("aria-valuetext", testo()); suCambio(ANNI[+r.value]); });
    box.append(l, r, scala);
    return { box, imposta: (v) => { r.value = String(Math.max(0, ANNI.indexOf(v))); r.setAttribute("aria-valuetext", testo()); } };
  }

  function crea(box, opz = {}) {
    if (!box) return null;
    box.classList.add("aria-gruppi");
    box.innerHTML = "";
    const massimo = Math.max(1, Math.min(MAX, opz.massimo || MAX));
    let serie = opz.serie || null, zona = opz.zona || null, gruppi = [], ascoltatori = [], attesa = 0;
    const elenco = h("div", "aria-gruppi-elenco");
    const piede = h("div", "aria-gruppi-piede");
    const aggiungi = h("button", "bottone secondario piccolo", "Aggiungi un gruppo");
    aggiungi.type = "button";
    const zonaBox = h("label", "casella aria-zona");
    const zonaCasella = document.createElement("input"); zonaCasella.type = "checkbox";
    const zonaTesto = h("span");
    zonaBox.append(zonaCasella, zonaTesto);
    zonaBox.hidden = true;
    const nota = h("p", "aiuto aria-gruppi-nota");
    nota.setAttribute("role", "status");
    piede.append(aggiungi, zonaBox);
    box.append(elenco, piede, nota);

    const colore = (i) => `var(--serie-${(i % 6) + 1})`;
    function coloreCalcolato(i) {
      return getComputedStyle(document.documentElement).getPropertyValue(`--serie-${(i % 6) + 1}`).trim() || "#888";
    }

    function avvisa() {
      clearTimeout(attesa);
      attesa = setTimeout(() => {
        ricalcola();
        const det = { gruppi: stato() };
        ascoltatori.forEach((f) => { try { f(det.gruppi); } catch (e) { console.error(e); } });
        box.dispatchEvent(new CustomEvent("eugenio:aria-gruppi", { bubbles: true, detail: det }));
      }, 60);
    }
    function ricalcola() {
      const nTot = serie ? (serie.n || serie.t.length) : 0;
      const anniTot = serie ? anniSerie(serie) : 0;
      const corti = [];
      gruppi.forEach((g, i) => {
        g.indici = serie ? filtra(serie, g.def) : new Uint32Array(0);
        g.vista.conteggio.textContent = serie
          ? `${fmt(g.indici.length)} ore (${fmt(nTot ? g.indici.length / nTot * 100 : 0, 1)} % delle ore della serie)`
          : "Scegli il comune e la serie al passo 1.";
        if (serie && g.def.anni && g.def.anni > anniTot + 0.01) corti.push(`gruppo ${i + 1}`);
      });
      nota.textContent = corti.length
        ? `La serie caricata copre ${fmt(anniTot, anniTot < 2 ? 1 : 0)} anni: per ${corti.join(", ")} uso tutta la serie caricata.` : "";
    }
    function stato() {
      return gruppi.map((g, i) => ({ id: g.id, indice: i, ...g.def, colore: colore(i), coloreCalcolato: coloreCalcolato(i), indici: g.indici }));
    }

    // ore in chiaro (14/11/2026): «alle» è esclusa, quindi 8–18 = dalle 8:00 alle 17:59 (10 ore)
    function spiegaOre(def) {
      const da = Math.max(0, Math.min(24, Math.round(+def.oraDa || 0))), a = Math.max(0, Math.min(24, Math.round(def.oraA === undefined ? 24 : +def.oraA)));
      if (da === a || (da === 0 && a === 24)) return "Ore: tutto il giorno (0:00–23:59).";
      const n = da < a ? a - da : 24 - da + a;
      if (da < a) return `Ore: dalle ${da} alle ${a}, cioè ore ${da}:00–${a - 1}:59 (${n} ore al giorno; l'ora «alle» è esclusa).`;
      return `Ore: dalle ${da} alle ${a} del giorno dopo, cioè ore ${da}:00–23:59${a ? ` e 0:00–${a - 1}:59` : ""} (${n} ore al giorno; l'ora «alle» è esclusa).`;
    }
    function campo(etichetta, valore, attributi, suCambio) {
      const l = h("label", "aria-campo");
      l.append(h("span", null, etichetta));
      const inp = document.createElement("input");
      Object.assign(inp, attributi);
      inp.value = valore;
      inp.addEventListener("input", () => suCambio(inp));
      l.appendChild(inp);
      return { l, inp };
    }
    function vistaGruppo(g) {
      const el = h("fieldset", "aria-gruppo");
      const leg = h("legend", "aria-gruppo-testa");
      const camp = h("span", "aria-campione"); camp.setAttribute("aria-hidden", "true");
      const nome = document.createElement("input");
      nome.type = "text"; nome.className = "aria-gruppo-nome"; nome.value = g.def.nome; nome.maxLength = 40;
      nome.addEventListener("input", () => { g.def.nome = nome.value.trim() || `Gruppo ${gruppi.indexOf(g) + 1}`; avvisa(); });
      const mostra = h("label", "casella aria-mostra");
      const mc = document.createElement("input"); mc.type = "checkbox"; mc.checked = g.def.mostra !== false;
      mc.addEventListener("change", () => { g.def.mostra = mc.checked; el.classList.toggle("spento", !mc.checked); avvisa(); });
      mostra.append(mc, " Mostra");
      const togli = h("button", "bottone secondario piccolo aria-togli", "Togli");
      togli.type = "button";
      togli.addEventListener("click", () => { gruppi = gruppi.filter((x) => x !== g); el.remove(); rinumera(); avvisa(); });
      leg.append(camp, nome, mostra, togli);
      const preset = h("div", "aria-preset");
      preset.setAttribute("role", "group");
      NOMI_PRESET.forEach(([k, t]) => {
        const b = h("button", "bottone secondario piccolo", t); b.type = "button"; b.dataset.preset = k;
        if (k === "ufficio") b.title = "Giorni feriali, dalle 8 alle 18, cioè ore 8:00–17:59";
        b.addEventListener("click", () => { g.def = applicaPreset(g.def, k, zonaCasella.checked ? zona : null); aggiorna(g); avvisa(); });
        preset.appendChild(b);
      });
      const cur = cursoreAnni("Anni", g.def.anni, (v) => { g.def.anni = v; avvisa(); });
      const righe = h("div", "aria-campi");
      const da = campo("Dal (gg/mm)", g.def.da, { type: "text", inputMode: "numeric", size: 5, placeholder: "01/06" }, (i) => {
        const ok = leggiData(i.value); i.setAttribute("aria-invalid", ok ? "false" : "true"); if (ok) { g.def.da = i.value.trim(); avvisa(); } });
      const a = campo("al (gg/mm)", g.def.a, { type: "text", inputMode: "numeric", size: 5, placeholder: "30/09" }, (i) => {
        const ok = leggiData(i.value); i.setAttribute("aria-invalid", ok ? "false" : "true"); if (ok) { g.def.a = i.value.trim(); avvisa(); } });
      const oda = campo("Dalle ore", g.def.oraDa, { type: "number", min: 0, max: 24, step: 1 }, (i) => {
        const v = +i.value; const ok = Number.isInteger(v) && v >= 0 && v <= 24; i.setAttribute("aria-invalid", ok ? "false" : "true"); if (ok) { g.def.oraDa = v; g.vista.oreTesto.textContent = spiegaOre(g.def); avvisa(); } });
      const oa = campo("alle ore", g.def.oraA, { type: "number", min: 0, max: 24, step: 1 }, (i) => {
        const v = +i.value; const ok = Number.isInteger(v) && v >= 0 && v <= 24; i.setAttribute("aria-invalid", ok ? "false" : "true"); if (ok) { g.def.oraA = v; g.vista.oreTesto.textContent = spiegaOre(g.def); avvisa(); } });
      const gl = h("label", "aria-campo");
      gl.append(h("span", null, "Giorni"));
      const gs = document.createElement("select");
      [["tutti", "tutti"], ["feriali", "feriali (lun–ven)"]].forEach(([v, t]) => { const o = h("option", null, t); o.value = v; gs.appendChild(o); });
      gs.value = g.def.giorni;
      gs.addEventListener("change", () => { g.def.giorni = gs.value; avvisa(); });
      gl.appendChild(gs);
      righe.append(da.l, a.l, oda.l, oa.l, gl);
      const oreTesto = h("p", "aiuto aria-ore-spiega", spiegaOre(g.def));
      const conteggio = h("p", "aiuto aria-gruppo-conteggio");
      el.append(leg, preset, cur.box, righe, oreTesto, conteggio);
      g.vista = { el, camp, nome, mc, cur, da: da.inp, a: a.inp, oda: oda.inp, oa: oa.inp, gs, conteggio, togli, oreTesto };
      return el;
    }
    function aggiorna(g) {
      const v = g.vista;
      v.nome.value = g.def.nome; v.mc.checked = g.def.mostra !== false; v.cur.imposta(g.def.anni);
      v.da.value = g.def.da; v.a.value = g.def.a; v.oda.value = g.def.oraDa; v.oa.value = g.def.oraA; v.gs.value = g.def.giorni;
      v.oreTesto.textContent = spiegaOre(g.def);
      [v.da, v.a, v.oda, v.oa].forEach((i) => i.setAttribute("aria-invalid", "false"));
      v.el.classList.toggle("spento", g.def.mostra === false);
    }
    function rinumera() {
      gruppi.forEach((g, i) => {
        g.vista.camp.style.background = colore(i);
        g.vista.el.style.setProperty("--colore-gruppo", colore(i));
        g.vista.nome.setAttribute("aria-label", `Nome del gruppo ${i + 1} (va in legenda)`);
        g.vista.togli.hidden = gruppi.length <= 1;
        g.vista.togli.setAttribute("aria-label", `Togli il gruppo ${i + 1}`);
      });
      aggiungi.hidden = gruppi.length >= massimo;
    }
    function nuovo(def) {
      if (gruppi.length >= massimo) return null;
      let d = { ...PREDEFINITO, nome: `Gruppo ${gruppi.length + 1}`, ...(def || {}) };
      if (def && def.preset) { d = applicaPreset({ ...PREDEFINITO, ...def, nome: "" }, def.preset, null); if (def.nome) d.nome = def.nome; }
      delete d.preset;
      const g = { id: `g${++conta}`, def: d, indici: new Uint32Array(0) };
      gruppi.push(g);
      elenco.appendChild(vistaGruppo(g));
      aggiorna(g);
      rinumera();
      return g;
    }
    aggiungi.addEventListener("click", () => { const g = nuovo({ preset: "anno" }); if (g) { g.vista.nome.focus(); avvisa(); } });
    zonaCasella.addEventListener("change", () => avvisa());

    // (20/11/2026) collegamento a questa simulazione: i gruppi nell'indirizzo, separati da «_», campi separati da «*»
    // (caratteri che l'indirizzo non trasforma in %..):
    // nome*mostra(1/0)*anni*da(ggmm)*a(ggmm)*ora da*ora a*giorni(t = tutti, f = feriali). Nome del parametro: l'id del box
    // senza «aria-» (gruppi, gruppi-estate, gruppi-inverno…) o opz.collegamento
    const chiaveLink = opz.collegamento || (box.id ? box.id.replace(/^aria-/, "") : "gruppi");
    const testoLink = () => gruppi.map((g) => { const d = g.def; return [String(d.nome || "").replace(/[*_]/g, " ").trim(), d.mostra === false ? 0 : 1,
      d.anni, d.da.replace("/", ""), d.a.replace("/", ""), d.oraDa, d.oraA, d.giorni === "feriali" ? "f" : "t"].join("*"); }).join("_");
    const daLink = (testo) => String(testo || "").split("_").filter(Boolean).slice(0, massimo).map((r) => {
      const [nome, mostra, anni, da, a, oraDa, oraA, giorni] = r.split("*");
      const dm = (x, pred) => (/^\d{4}$/.test(x || "") ? `${x.slice(0, 2)}/${x.slice(2)}` : pred);
      const ora = (x, pred) => (Number.isFinite(+x) && x !== "" ? Math.max(0, Math.min(24, Math.round(+x))) : pred);
      return { nome: nome || "Gruppo", mostra: mostra !== "0", anni: ANNI.includes(+anni) ? +anni : PREDEFINITO.anni,
        da: dm(da, PREDEFINITO.da), a: dm(a, PREDEFINITO.a), oraDa: ora(oraDa, 0), oraA: ora(oraA, 24), giorni: giorni === "f" ? "feriali" : "tutti" };
    });
    const parametroLink = typeof location !== "undefined" ? new URLSearchParams(location.search).get(chiaveLink) : null;
    const dalCollegamento = parametroLink ? daLink(parametroLink) : [];
    (dalCollegamento.length ? dalCollegamento : opz.iniziali && opz.iniziali.length ? opz.iniziali : [{ preset: "anno" }]).forEach((d) => nuovo(d));
    if (typeof window !== "undefined" && window.EUGENIO_COLLEGAMENTO) {
      window.EUGENIO_COLLEGAMENTO.registra({ chiavi: [chiaveLink], leggi: () => ({ [chiaveLink]: testoLink() }) });
    }
    ricalcola();
    document.addEventListener("eugenio:aspetto", () => avvisa());

    const ctrl = {
      serie(s) { if (s === undefined) return serie; serie = s; avvisa(); return ctrl; },
      zona(z) {
        if (z === undefined) return zona;
        zona = z && ZONE[z] ? z : (z === "F" ? "F" : null);
        zonaBox.hidden = !zona;
        if (zona === "F") { zonaCasella.checked = false; zonaCasella.disabled = true; zonaTesto.textContent = " Zona F (DPR 412): nessun limite di legge al periodo di accensione; l'Inverno resta 01/11–31/03"; }
        else if (zona) { zonaCasella.disabled = false; zonaTesto.textContent = ` «Inverno» secondo la zona climatica ${zona} del comune (DPR 412: ${ZONE[zona][0]}–${ZONE[zona][1]})`; }
        return ctrl;
      },
      gruppi: () => stato(),
      visibili: () => stato().filter((g) => g.mostra),
      aggiungi: (def) => { const g = nuovo(def); avvisa(); return !!g; },
      imposta(defs) { gruppi.forEach((g) => g.vista.el.remove()); gruppi = []; (defs || []).forEach((d) => nuovo(d)); avvisa(); return ctrl; },
      su(f) { if (typeof f === "function") ascoltatori.push(f); return ctrl; },
      ricalcola() { ricalcola(); return stato(); },
      elemento: box,
    };
    if (opz.zona) ctrl.zona(opz.zona);
    if (serie) avvisa();
    return ctrl;
  }
  API.crea = crea;
})(typeof self !== "undefined" ? self : globalThis);
