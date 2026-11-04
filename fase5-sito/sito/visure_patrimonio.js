"use strict";
// Passo «Visure catastali» della pagina Patrimonio (fase 11): legge nel browser i file di EuGEnio Visure (indice.csv,
// edifici_visure.csv, patrimonio_con_visure.csv, visure.json), abbina le unità agli edifici geolocalizzati con
// visure_abbina.js (stessa logica del lettore in Python) e aggiunge a ogni edificio le colonne visura_… (schede,
// CSV e GeoJSON scaricati). Niente di questo va al server: il report PDF/Excel/ODS, che si fa sul server, resta senza
// le colonne delle visure. Le colonne con dati personali si scartano appena lette.
(function () {
  const V = window.EUGENIO_VISURE, T = window.EUGENIO_TABELLE, P = () => window.EUGENIO_PATRIMONIO;
  if (!V || !T) return;
  const $ = (id) => document.getElementById(id);
  const ESITI = { ok: "abbinata", verificare: "da verificare", nessuna_visura: "senza visura" };
  // visure: { tipo, unita, edifici, nome }; perRiga: indice della riga di Patrimonio → colonne visura_…; daIngresso:
  // per i file caricati al passo 1, le colonne visura_… per id (patrimonio_con_visure.csv)
  const stato = { visure: null, perRiga: new Map(), nonAbbinate: [], daIngresso: null };

  function h(tag, cls, testo) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (testo !== undefined && testo !== null) e.textContent = testo;
    return e;
  }
  function messaggio(t, errore = false) { const m = $("messaggio-visure"); if (!m) return; m.textContent = t; m.classList.toggle("errore", errore); }
  const fmt = (n) => (n === null || n === undefined || n === "" ? "" : Number(V.numero(n)).toLocaleString("it-IT"));

  // ------------------------------------------------------------------ abbinamento alle righe della geolocalizzazione
  // un edificio già riassunto (edifici_visure.csv, patrimonio_con_visure.csv) come «unità» fittizia per coincide()
  function comePseudoUnita(a) {
    const c = String(a.codice_comune || "").toUpperCase() || (/^[A-Z]\d{3}$/i.test(a.comune || "") ? String(a.comune).toUpperCase() : "");
    return { comune: a.comune, codice_comune: c, sezione: a.sezione, foglio: a.foglio, particella: a.particella || a.mappale };
  }
  function colonneVisura(a) { const o = {}; V.COLONNE_EDIFICIO.forEach((k) => { if (a[k] !== undefined) o[k] = a[k]; }); return o; }

  function applica() {
    stato.perRiga = new Map(); stato.nonAbbinate = [];
    const righe = (P() && P().righe()) || [];
    if (!stato.visure || !righe.length) { riepilogo(); if (righe.length && P()) P().elenco(); return; }
    const vis = stato.visure;
    if (vis.tipo === "unita") {
      const a = V.abbina(righe, vis.unita);
      a.edifici.forEach((r, i) => stato.perRiga.set(i, colonneVisura(r)));
      stato.nonAbbinate = a.nonAbbinate;
    } else {
      const usati = new Set();
      righe.forEach((r, i) => {
        // prima per id (lo stesso file di Patrimonio), poi per comune, foglio e particella
        let j = vis.tipo === "patrimonio" ? vis.edifici.findIndex((a) => a.id && r.id && String(a.id) === String(r.id)) : -1;
        let esito = null;
        if (j < 0) {
          for (const k of V.chiaviEdificio(r)) {
            j = vis.edifici.findIndex((a) => (esito = V.coincide(k, comePseudoUnita(a))));
            if (j >= 0) break;
          }
        }
        if (j >= 0 && vis.edifici[j].visura_esito && vis.edifici[j].visura_esito !== "nessuna_visura") {
          const c = colonneVisura(vis.edifici[j]);
          if (esito === "verificare") c.visura_esito = "verificare";
          stato.perRiga.set(i, c);
          usati.add(j);
        } else stato.perRiga.set(i, { visura_esito: "nessuna_visura", visura_nota: "nessuna visura per questa particella" });
      });
      stato.nonAbbinate = vis.edifici.filter((a, j) => !usati.has(j) && a.visura_esito !== "nessuna_visura");
    }
    riepilogo();
    if (P()) P().elenco();
  }

  // ------------------------------------------------------------------ riepilogo del passo
  function riepilogo() {
    const box = $("riepilogo-visure"), az = $("azioni-visure");
    if (!box) return;
    box.innerHTML = "";
    const righe = (P() && P().righe()) || [];
    box.hidden = !stato.visure;
    az.hidden = !stato.visure;
    if (!stato.visure) return;
    const vis = stato.visure;
    const n = vis.tipo === "unita" ? `${vis.unita.length.toLocaleString("it-IT")} unità immobiliari` : `${vis.edifici.length.toLocaleString("it-IT")} edifici con le visure`;
    box.appendChild(h("p", null, `File: ${vis.nome} – ${n}.`));
    // .bottone ha un display proprio: si nasconde con lo stile, non con l'attributo hidden
    $("usa-visure").style.display = righe.length ? "none" : "";
    $("scarica-visure").style.display = righe.length ? "" : "none";
    if (!righe.length) {
      box.appendChild(h("p", "aiuto", "Nessun edificio geolocalizzato: carica il tuo elenco al passo 1 oppure usa le particelle delle visure come elenco degli edifici."));
      return;
    }
    const c = { ok: 0, verificare: 0, nessuna_visura: 0 };
    stato.perRiga.forEach((x) => { c[x.visura_esito] = (c[x.visura_esito] || 0) + 1; });
    const conteggi = h("div", "conteggi");
    for (const [k, et] of [["ok", "con la visura"], ["verificare", "da verificare"], ["nessuna_visura", "senza visura"]]) {
      const d = h("div", `conteggio ${k === "ok" ? "ok" : k === "verificare" ? "verificare" : "non_trovato"}`);
      d.append(h("b", null, (c[k] || 0).toLocaleString("it-IT")), h("span", null, et));
      conteggi.appendChild(d);
    }
    box.appendChild(conteggi);
    if (stato.nonAbbinate.length) {
      const det = h("details", "non-abbinate");
      det.appendChild(h("summary", null, `${stato.nonAbbinate.length} ${vis.tipo === "unita" ? "unità" : "edifici"} delle visure senza un edificio corrispondente`));
      const ul = h("ul", "aiuto elenco");
      stato.nonAbbinate.slice(0, 100).forEach((u) => ul.appendChild(h("li", null,
        [u.comune, u.foglio ? `foglio ${u.foglio}` : "", u.particella ? `particella ${u.particella}` : "", u.subalterno ? `sub ${u.subalterno}` : "", u.categoria || u.qualita || ""].filter(Boolean).join(", "))));
      det.appendChild(ul);
      box.appendChild(det);
    }
  }

  // ------------------------------------------------------------------ lettura del file
  async function carica(f) {
    if (!f) return;
    $("nome-visure").textContent = `${f.name} · ${(f.size / 1024).toFixed(0)} kB`;
    $("zona-visure").classList.add("pieno");
    if (/\.(xlsx|ods|xls)$/i.test(f.name)) { messaggio("Per le visure servono i file CSV o JSON di EuGEnio Visure (un foglio di calcolo andrebbe convertito dal server).", true); return; }
    try {
      const testo = T.decodifica(await f.arrayBuffer());
      const r = V.leggi(testo, f.name, T.righe);
      stato.visure = { ...r, nome: f.name };
      const avvisi = [];
      if (r.scartate.length) avvisi.push(`Ho ignorato ${r.scartate.length === 1 ? "la colonna" : "le colonne"} con dati personali (${r.scartate.join(", ")}): non servono e non si usano.`);
      messaggio(["Visure lette nel browser.", ...avvisi].join(" "));
      applica();
    } catch (e) {
      stato.visure = null;
      messaggio(`Non riuscito: ${e.message}`, true);
      applica();
    }
  }

  // il catasto scrive le vocali accentate finali con l'apostrofo («FORLI'»): per la ricerca del comune serve «Forlì»
  function comuneLeggibile(c) {
    const ACC = { A: "à", E: "è", I: "ì", O: "ò", U: "ù" };
    return String(c || "").trim().toLowerCase().replace(/([aeiou])['’](?=\s|$)/g, (m, v) => ACC[v.toUpperCase()])
      .replace(/(^|[\s-])(\p{L})/gu, (m, a, b) => a + b.toUpperCase());
  }

  // elenco degli edifici dalle visure (una riga per particella), per geolocalizzarli quando non c'è un altro elenco:
  // al server vanno solo id, comune, sezione, foglio e particella
  function csvDegliEdifici() {
    const vis = stato.visure;
    const ed = vis.tipo === "unita" ? V.edificiDaUnita(vis.unita) : vis.edifici;
    const cella = (v) => { const s = String(v === undefined || v === null ? "" : v); return /[;"\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
    const righe = ["id;comune;sezione;foglio;particella"];
    ed.forEach((e, i) => righe.push([e.id || `V${i + 1}`, comuneLeggibile(e.comune) || e.codice_comune, e.sezione, e.foglio, e.particella || e.mappale].map(cella).join(";")));
    return { testo: righe.join("\n"), n: ed.length };
  }

  // ------------------------------------------------------------------ file di EuGEnio Visure caricati al passo 1
  // restituisce { testo da mandare al server, nota } oppure null se il file non è di EuGEnio Visure
  function ingresso(testo, nome) {
    let r;
    try { r = V.leggi(testo, nome, T.righe); } catch { return null; }
    // un elenco qualsiasi con foglio, particella e categoria non basta: al passo 1 si riconoscono solo i file del lettore
    const testa = (testo.replace(/^\ufeff/, "").split(/\r?\n/).find((x) => x.trim() && !x.trim().startsWith("#")) || "").toLowerCase();
    if (r.tipo === "unita" && !/\.json$/i.test(nome || "") && !/(^|[;,])catasto([;,]|$)/.test(testa)) return null;
    stato.visure = { ...r, nome };
    const avvisi = r.scartate.length ? ` Colonne con dati personali ignorate: ${r.scartate.join(", ")}.` : "";
    if (r.tipo === "unita" || r.tipo === "edifici") {
      const c = csvDegliEdifici();
      return { testo: c.testo, nota: `File di EuGEnio Visure: ${c.n} particelle cercate come edifici (al server vanno solo comune, sezione, foglio e particella; le visure restano nel browser).${avvisi}` };
    }
    // patrimonio_con_visure.csv: si manda il file senza le colonne visura_… (né quelle personali)
    const prime = testo.replace(/^﻿/, "").split(/\r?\n/).filter((x) => x.trim() && !x.trim().startsWith("#"));
    const sep = T.separatore(prime[0]);
    const tutte = T.righe(prime.join("\n"), sep);
    const { visure, personali } = V.separaTitoli(tutte[0]);
    const via = new Set([...visure, ...personali]);
    const cella = (v) => { const s = String(v === undefined || v === null ? "" : v); return /[;"\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
    const out = tutte.map((riga) => riga.filter((_, i) => !via.has(i)).map(cella).join(";"));
    return { testo: out.join("\n"), nota: `Il file contiene già le colonne delle visure: restano nel browser e si riattaccano agli edifici trovati.${avvisi}` };
  }

  // ------------------------------------------------------------------ per patrimonio.js
  function dettaglio(i) {
    const c = stato.perRiga.get(i);
    if (!c || !c.visura_esito) return null;
    const p = h("p", `visura ${c.visura_esito}`);
    if (c.visura_esito === "nessuna_visura") { p.textContent = "Visura: nessuna per questa particella"; return p; }
    const piani = c.visura_piani ? `piani ${c.visura_piani}` + (c.visura_piani_fuori_terra !== "" && c.visura_piani_fuori_terra !== null && c.visura_piani_fuori_terra !== undefined
      ? ` (${c.visura_piani_fuori_terra} fuori terra${+c.visura_piani_interrati ? `, ${c.visura_piani_interrati} interrati` : ""})` : "") : "";
    const parti = [`${c.visura_unita} unità`, c.visura_categorie, c.visura_uso_prevalente ? `uso: ${c.visura_uso_prevalente}` : "", piani,
      c.visura_superficie_catastale ? `${fmt(c.visura_superficie_catastale)} m² catastali` : "",
      c.visura_consistenza_m3 ? `${fmt(c.visura_consistenza_m3)} m³` : ""].filter(Boolean);
    p.textContent = `Visura (${ESITI[c.visura_esito] || c.visura_esito}): ${parti.join(" · ")}`;
    return p;
  }
  function colonne(i) {
    const c = stato.perRiga.get(i);
    if (!c) return {};
    const o = {};
    V.COLONNE_EDIFICIO.forEach((k) => { o[k] = c[k] === undefined || c[k] === null ? "" : c[k]; });
    return o;
  }

  // ------------------------------------------------------------------ pagina
  function avvia() {
    const inp = $("file-visure");
    if (!inp) return;
    inp.addEventListener("change", (e) => carica(e.target.files[0]));
    const zona = $("zona-visure");
    ["dragover", "dragenter"].forEach((t) => zona.addEventListener(t, (e) => { e.preventDefault(); zona.classList.add("pieno"); }));
    zona.addEventListener("dragleave", () => zona.classList.toggle("pieno", !!stato.visure));
    zona.addEventListener("drop", (e) => { e.preventDefault(); carica(e.dataTransfer.files[0]); });
    $("usa-visure").addEventListener("click", () => {
      if (!stato.visure || !P()) return;
      const c = csvDegliEdifici();
      P().esegui(c.testo, "edifici_dalle_visure.csv", `Edifici dalle visure: ${c.n} particelle (al server solo comune, sezione, foglio e particella).`, false);
    });
    $("scarica-visure").addEventListener("click", () => { const b = $("scarica-csv"); if (b) b.click(); });
    $("togli-visure").addEventListener("click", () => {
      stato.visure = null; inp.value = "";
      $("nome-visure").textContent = "Scegli il file o trascinalo qui";
      zona.classList.remove("pieno");
      messaggio("");
      applica();
    });
    document.addEventListener("eugenio:patrimonio-risultato", () => applica());
  }

  window.EUGENIO_VISURE_UI = { ingresso, dettaglio, colonne, applica, stato };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", avvia); else avvia();
})();
