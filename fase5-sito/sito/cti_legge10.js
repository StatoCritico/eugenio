"use strict";
// Sezione "L'anno tipo del CTI" della pagina Legge 10: indicatori calcolati da EuGEnio dagli anni tipo climatici
// del CTI (cti_try/indicatori.py, come il foglio interpolatore del CTI), accanto ai valori di legge del DPR 412/93
// e al clima reale delle ultime 10 stagioni (sezione "Il clima dal 1940", file dati/clima/...).
// Legge solo file statici:
//   dati/cti/indice.json           metodo, fonte, attribuzione, località usate
//   dati/cti/<RR>/<istat>.json     indicatori del comune (~1 kB): GG, zone, θ di progetto, mensili, località
//   dati/clima/<RR>/<istat>.json   clima reale (per la colonna delle ultime 10 stagioni)
// Nessun dato orario del CTI: le condizioni del CTI vietano di ripubblicarli. Questi valori NON sono sotto
// CC BY 4.0: si possono solo citare, finché il CTI non risponde alla richiesta di autorizzazione.
// Uso: EUGENIO_CTI.mostra(contenitore, { istat, regione, dpr }) -> Promise<boolean> (false se il comune non c'è)
(function () {
  const V = "20261028d";
  const MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"];
  const FAQ = "faq.html#cti-elaborazioni";
  const CTI = "https://try.cti2000.it/";
  const FONTE = "elaborazione EuGEnio su anni tipo climatici CTI – Comitato Termotecnico Italiano";
  const COLONNE = [["t_media", "T media", "°C", 1], ["t_min", "T min", "°C", 1], ["t_max", "T max", "°C", 1],
    ["h_glob", "Irradiazione globale", "MJ/m² giorno", 2], ["h_dif", "di cui diffusa", "MJ/m² giorno", 2],
    ["pv", "Pressione del vapore", "Pa", 0], ["ur", "Umidità relativa", "%", 0], ["vento", "Vento", "m/s", 1]];
  const num = (x, dec = 0) => (x === null || x === undefined || Number.isNaN(x)) ? "—"
    : Number(x).toLocaleString("it-IT", { minimumFractionDigits: dec, maximumFractionDigits: dec });
  const segno = (x, dec = 0) => (x === null || x === undefined) ? "—" : `${x > 0 ? "+" : ""}${num(x, dec)}`;
  function h(tag, cls, testo) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (testo !== undefined && testo !== null) e.textContent = testo;
    return e;
  }
  function link(testo, href) { const a = h("a", null, testo); a.href = href; return a; }
  function cifra(valore, etichetta, nota) {
    const d = h("div", "cifra");
    d.append(h("b", null, valore), h("span", null, etichetta));
    if (nota) d.appendChild(h("small", null, nota));
    return d;
  }
  const json = (u) => fetch(u).then((r) => (r.ok ? r.json() : null)).catch(() => null);

  let indice = null;
  const cache = new Map();
  function carica(regione, istat) {
    if (!indice) indice = json(`dati/cti/indice.json?v=${V}`);
    if (!cache.has(istat)) cache.set(istat, Promise.all([json(`dati/cti/${regione}/${istat}.json?v=${V}`),
      json(`dati/clima/${regione}/${istat}.json`)]));
    return Promise.all([indice, cache.get(istat)]);
  }

  // "Calcolati dagli anni tipo CTI di Bologna (BO, 1,1 km, peso 99 %) e Modena (MO, 36 km, peso 1 %) …"
  function frase(c) {
    const tutte = c.localita || [];
    const loc = tutte.filter((l) => l.peso >= 0.005);   // una località con peso sotto lo 0,5 % non cambia i numeri
    const nomi = loc.map((l) => `${l.nome} (${l.prov}, ${num(l.dist_km, l.dist_km < 10 ? 1 : 0)} km${
      loc.length > 1 ? `, peso ${num(100 * l.peso)} %` : ""})`);
    const elenco = nomi.length > 1 ? `${nomi.slice(0, -1).join(", ")} e ${nomi[nomi.length - 1]}` : nomi[0];
    const dz = Math.max(0, ...loc.map((l) => Math.abs(l.dislivello_m || 0)));
    const quota = c.quota_m === null || c.quota_m === undefined
      ? "senza correzione di quota (quota del comune non disponibile)"
      : dz < 10 ? `temperature alla quota del comune (${num(c.quota_m)} m)`
      : `temperature riportate alla quota del comune (${num(c.quota_m)} m) con ${num(c.gradiente_c_km, 1)} °C ogni 1000 m`;
    const come = loc.length > 1
      ? "media ora per ora con pesi proporzionali a 1/distanza², come il foglio interpolatore del CTI"
      : tutte.length > 1 ? "la seconda località della regione, più lontana, pesa meno dello 0,5 %"
      : "la sola località più vicina della regione: il comune è più lontano da entrambe di quanto lo siano tra loro, "
        + "come prevede il foglio interpolatore del CTI";
    return `Calcolati dagli anni tipo climatici CTI di ${elenco}: ${come}; ${quota}.`;
  }

  async function mostra(box, { istat, regione, dpr }) {
    box.innerHTML = "";
    box.dataset.istat = istat;
    const [ind, [c, clima]] = await carica(regione, istat);
    if (box.dataset.istat !== istat) return false;   // nel frattempo è stato scelto un altro comune
    if (!c || c.istat !== istat) return false;       // comune senza file: la sezione resta nascosta

    const ggDpr = dpr && Number.isFinite(dpr.gg) ? dpr.gg : null;
    const diff = ggDpr ? 100 * (c.gg_zona / ggDpr - 1) : null;

    // perché questa sezione c'è: un confronto con il metodo ufficiale, non i valori di EuGEnio
    box.appendChild(h("p", "aiuto", "Qui mostriamo, solo per confronto, cosa dà per questo comune il metodo del CTI "
      + "(gli anni tipo della UNI 10349 e il loro foglio interpolatore). I valori che EuGEnio calcola da sé, comune per "
      + "comune, sono quelli del clima reale delle sezioni 2 e 4, ottenuti da dati aperti con codice open source."));

    // limiti noti del metodo del CTI, segnalati comune per comune
    const loc = (c.localita || []).filter((l) => l.peso >= 0.005);
    const dz = loc.reduce((s, l) => s + l.peso * Math.abs(l.dislivello_m || 0), 0) / (loc.reduce((s, l) => s + l.peso, 0) || 1);
    const limiti = [];
    if (dz >= 300) limiti.push(`la quota differisce di ${num(dz)} m da quella delle località CTI usate: il metodo `
      + "del CTI riporta la temperatura alla quota del comune con 6,5 °C ogni 1000 m, un valore medio annuo che d'inverno "
      + "in montagna è troppo forte, e tende a dare gradi giorno più alti del vero (in media +13 % rispetto al DPR 412/93 "
      + "con dislivelli tra 500 e 1000 m, +21 % oltre i 1000 m)");
    if (diff !== null && diff <= -15) limiti.push(`i gradi giorno sono ${num(-diff)} % sotto il DPR 412/93: spesso succede `
      + "quando la località CTI più vicina sta oltre un crinale o sul mare (per esempio i comuni del versante padano "
      + "della Liguria, che ha solo stazioni costiere) e trasferisce al comune un clima più mite del suo");
    else if (diff !== null && diff >= 15 && dz < 300) limiti.push(`i gradi giorno sono ${num(diff)} % sopra il DPR 412/93: `
      + "le località CTI sono spesso nell'entroterra o in aeroporto, mentre i valori del DPR sono tarati sui capoluoghi");
    if (limiti.length) {
      const av = h("div", "messaggio attenzione avviso-cti");
      const testo = h("span");                       // un solo blocco: .messaggio dispone i figli in riga
      testo.append(h("strong", null, "Da usare con cautela. "), `Per questo comune ${limiti.join("; inoltre ")}. `,
        "Lo segnaliamo perché il confronto serve proprio a mostrare i limiti dei metodi, compreso quello ufficiale.");
      av.appendChild(testo);
      box.appendChild(av);
    }
    const cifre = h("div", "cifre");
    cifre.append(
      cifra(num(c.gg_zona), `gradi giorno sul periodo della zona ${c.zona_riferimento}`,
        diff !== null ? `${segno(diff, 1)} % rispetto al DPR 412/93` : null),
      cifra(c.zona_coerente, "zona climatica che ne risulta", dpr && dpr.zona ? `DPR 412/93: zona ${dpr.zona}` : null),
      cifra(`${num(c.theta_inv, 1)} °C`, "temperatura di progetto invernale", "1° percentile delle minime giornaliere"),
      cifra(`${num(c.theta_est, 1)} °C`, "temperatura di progetto estiva", "99° percentile delle massime giornaliere"),
    );
    box.appendChild(cifre);

    // confronto: valori di legge, clima reale delle ultime 10 stagioni, anno tipo CTI
    const per = clima && clima.periodi ? Object.entries(clima.periodi).filter(([, p]) => p.anni === 10).pop() : null;
    const r10 = per ? per[1] : null;
    const t = h("table", "mensili confronto-cti");
    const r1 = t.createTHead().insertRow();
    for (const [testo, cl, nota] of [["", null], ["DPR 412/93", "num", "valori di legge"],
      ["Clima reale", "num", r10 ? `stagioni ${r10.stagioni[0]}–${r10.stagioni[1]}` : "ultime 10 stagioni"],
      ["Anno tipo CTI", "num", "dati 1983–2013"]]) {
      const th = h("th", cl, testo);
      if (nota) th.appendChild(h("small", null, nota));
      r1.appendChild(th);
    }
    const righe = [
      [`Gradi giorno (periodo della zona ${c.zona_riferimento})`, ggDpr !== null ? num(ggDpr) : "—",
        r10 ? num(r10.gg_zona) : "—", num(c.gg_zona)],
      ["Zona climatica", (dpr && dpr.zona) || "—", r10 ? r10.zona_coerente || r10.zona : "—", c.zona_coerente],
      ["Gradi giorno sull'anno intero", "—", r10 ? num(r10.gg_anno) : "—", num(c.gg_anno)],
      ["Temperatura di progetto invernale", "—", r10 ? `${num(r10.theta_inv, 1)} °C` : "—", `${num(c.theta_inv, 1)} °C`],
      ["Temperatura di progetto estiva", "—", r10 ? `${num(r10.theta_est, 1)} °C` : "—", `${num(c.theta_est, 1)} °C`],
    ];
    const corpo = t.createTBody();
    for (const [nome, ...v] of righe) {
      const r = corpo.insertRow();
      r.appendChild(h("th", null, nome));
      v.forEach((x) => r.appendChild(h("td", "num", x)));
    }
    const s = h("div", "tabella-scorre"); s.appendChild(t); box.appendChild(s);

    const nota = h("p", "aiuto", frase(c) + " ");
    nota.append(link("Come li calcoliamo e perché non pubblichiamo i dati del CTI", FAQ), ".");
    box.appendChild(nota);
    for (const a of c.avvisi || []) box.appendChild(h("p", "aiuto", `Attenzione: ${a}.`));
    box.appendChild(h("p", "aiuto", "L'anno tipo è un anno «medio» costruito dal CTI con mesi reali di anni diversi "
      + "(tra il 1983 e il 2013, secondo la località) ed è la base della UNI 10349:2016: descrive il clima di quel periodo, "
      + "non quello delle ultime stagioni né quello dei decenni prima del 1993 (DPR 412/93). "
      + "Per la relazione tecnica ex Legge 10 valgono comunque i valori normativi."));

    // dati mensili, chiusi per non allungare la pagina
    const det = h("details", "cti-mensili");
    det.appendChild(h("summary", null, "Dati mensili dell'anno tipo CTI"));
    const tm = h("table", "mensili");
    const th = tm.createTHead().insertRow();
    th.appendChild(h("th", null, "Mese"));
    for (const [, nome, unita] of COLONNE) { const c1 = h("th", "num", nome); c1.appendChild(h("small", null, unita)); th.appendChild(c1); }
    const cm = tm.createTBody();
    for (let i = 0; i < 12; i++) {
      const r = cm.insertRow();
      r.appendChild(h("th", null, MESI[i]));
      for (const [k, , , dec] of COLONNE) r.appendChild(h("td", "num", num(c.mensili && c.mensili[k] ? c.mensili[k][i] : null, dec)));
    }
    const sm = h("div", "tabella-scorre"); sm.appendChild(tm); det.appendChild(sm);
    box.appendChild(det);

    // licenza: solo citazione, finché il CTI non risponde
    const lic = h("p", "avviso-legale licenza-cti");
    lic.append(h("strong", null, "Licenza: solo citazione. "),
      "Questi valori non hanno la licenza CC BY 4.0 del resto del sito: puoi citarli indicando la fonte («" + FONTE
      + "»), ma non ridistribuirli, finché il CTI non risponde alla nostra richiesta di autorizzazione. Non sono "
      + "scaricabili in CSV e non compaiono nel report.");
    box.appendChild(lic);

    const f = h("p", "fonti");
    f.append("Fonte: ", FONTE, " (", link("try.cti2000.it", CTI),
      "), anni tipo costruiti dal CTI con i dati grezzi delle ARPA e degli altri enti regionali. Clima reale: ",
      link("Weather data by Open-Meteo.com", "https://open-meteo.com/"), " (CC BY 4.0), da ERA5 ed ERA5-Land.");
    box.appendChild(f);
    return true;
  }

  window.EUGENIO_CTI = { mostra, frase };
})();
