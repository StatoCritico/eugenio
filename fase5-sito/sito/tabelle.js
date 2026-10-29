"use strict";
// Lettura dei file caricati (29/10/2026), parte comune alle pagine che accettano tabelle: CSV e TXT si leggono nel
// browser; i fogli di calcolo Excel (.xlsx) e OpenDocument (.ods) si mandano a /api/converti, che restituisce il primo
// foglio come testo CSV (separatore «;», punto decimale, date AAAA-MM-GG). Il vecchio formato .xls non si legge: il
// messaggio chiede di salvarlo come .xlsx, .ods o .csv. Il file non viene salvato da nessuna parte.
//
//  EUGENIO_TABELLE.ACCETTA            valore per l'attributo accept dei campi file
//  EUGENIO_TABELLE.tipo(file)         "testo" | "xlsx" | "ods" | "foglio" (zip senza estensione nota) | "xls"
//  EUGENIO_TABELLE.leggi(file)        → { testo, formato, fogli, foglio, nota, decimalePunto }
//                                     nota: «Il file ha 3 fogli: è stato letto il primo, «Consumi».» (o "")
//                                     decimalePunto: true se il testo viene dal server (numeri col punto decimale)
//  EUGENIO_TABELLE.righe(testo, sep)  il CSV in righe di celle (virgolette comprese)
//  EUGENIO_TABELLE.separatore(riga)   ";" o "," (quello più frequente nella riga dei titoli; a parità «;»)
//  EUGENIO_TABELLE.numero(testo, { decimalePunto })  numero anche all'italiana (1.234,5) o null
(function () {
  const API = "/api";
  const ACCETTA = ".csv,.txt,.xlsx,.ods,text/csv,text/plain,"
    + "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.oasis.opendocument.spreadsheet";
  const MSG_XLS = "Il vecchio formato Excel .xls non si può leggere: apri il file e salvalo come .xlsx, .ods o .csv, poi caricalo di nuovo.";

  async function tipo(f) {
    const nome = (f && f.name || "").toLowerCase();
    let b = new Uint8Array(0);
    try { b = new Uint8Array(await f.slice(0, 8).arrayBuffer()); } catch { /* file non leggibile: si decide dal nome */ }
    const zip = b[0] === 0x50 && b[1] === 0x4b;                                   // «PK»: xlsx e ods sono archivi zip
    const ole = b[0] === 0xd0 && b[1] === 0xcf && b[2] === 0x11 && b[3] === 0xe0;  // vecchio formato di Office
    if (nome.endsWith(".xls") || ole) return "xls";
    if (nome.endsWith(".xlsx")) return "xlsx";
    if (nome.endsWith(".ods")) return "ods";
    if (zip) return "foglio";
    return "testo";
  }

  function decodifica(buf) {
    let t;
    try { t = new TextDecoder("utf-8", { fatal: true }).decode(buf); }
    catch { t = new TextDecoder("windows-1252").decode(buf); }   // CSV di Excel salvato con la codifica di Windows
    return t.replace(/^﻿/, "");
  }

  async function leggi(f) {
    const t = await tipo(f);
    if (t === "xls") throw new Error(MSG_XLS);
    if (t === "testo") {
      return { testo: decodifica(await f.arrayBuffer()), formato: "csv", fogli: [], foglio: null, nota: "", decimalePunto: false };
    }
    const fd = new FormData();
    fd.append("file", f, f.name);
    let r;
    try { r = await fetch(`${API}/converti`, { method: "POST", body: fd }); }
    catch { throw new Error("server non raggiungibile: il foglio di calcolo non si può convertire"); }
    let d = null;
    try { d = await r.json(); } catch { /* risposta non JSON */ }
    if (!r.ok || !d) throw new Error((d && typeof d.detail === "string" && d.detail) || `conversione non riuscita (errore ${r.status})`);
    const fogli = Array.isArray(d.fogli) ? d.fogli : [];
    const foglio = d.foglio_usato || fogli[0] || null;
    const nota = fogli.length > 1 ? `Il file ha ${fogli.length} fogli: è stato letto il primo, «${foglio}».` : "";
    return { testo: String(d.csv || "").replace(/^﻿/, ""), formato: d.formato || t, fogli, foglio, nota,
      decimalePunto: (d.formato || t) !== "csv" };
  }

  function separatore(riga) {
    const pv = (riga.match(/;/g) || []).length, v = (riga.match(/,/g) || []).length, tab = (riga.match(/\t/g) || []).length;
    if (tab > pv && tab > v) return "\t";
    return pv >= v ? ";" : ",";
  }

  // CSV → righe di celle; le virgolette raddoppiate valgono una virgoletta; righe vuote scartate
  function righe(testo, sep) {
    const out = [];
    let riga = [], cella = "", virg = false;
    for (let i = 0; i < testo.length; i++) {
      const c = testo[i];
      if (virg) {
        if (c === '"') { if (testo[i + 1] === '"') { cella += '"'; i++; } else virg = false; }
        else cella += c;
      } else if (c === '"' && cella === "") virg = true;
      else if (c === sep) { riga.push(cella); cella = ""; }
      else if (c === "\n" || c === "\r") {
        if (c === "\r" && testo[i + 1] === "\n") i++;
        riga.push(cella); cella = "";
        if (riga.some((x) => x.trim() !== "")) out.push(riga);
        riga = [];
      } else cella += c;
    }
    riga.push(cella);
    if (riga.some((x) => x.trim() !== "")) out.push(riga);
    return out;
  }

  // «1.234,5», «1234,5», «1234.5», «1,234.5», «-3», «12 345» → numero; testo non numerico → null.
  // Con decimalePunto (file convertiti dal server) il punto è sempre il separatore decimale.
  function numero(s, opz = {}) {
    if (s === null || s === undefined) return null;
    let t = String(s).trim().replace(/[\s  ']/g, "");
    if (!t) return null;
    if (opz.decimalePunto) t = t.replace(/,/g, "");
    else if (t.includes(",") && t.includes(".")) {
      t = t.lastIndexOf(",") > t.lastIndexOf(".") ? t.replace(/\./g, "").replace(",", ".") : t.replace(/,/g, "");
    } else if (t.includes(",")) {
      t = /^-?\d{1,3}(,\d{3}){2,}$/.test(t) ? t.replace(/,/g, "") : t.replace(",", ".");
    } else if (/^-?\d{1,3}(\.\d{3})+$/.test(t)) t = t.replace(/\./g, "");       // 1.234 all'italiana: migliaia
    if (!/^[-+]?(\d+\.?\d*|\.\d+)(e[-+]?\d+)?$/i.test(t)) return null;
    const n = Number(t);
    return Number.isFinite(n) ? n : null;
  }

  window.EUGENIO_TABELLE = { API, ACCETTA, MSG_XLS, tipo, leggi, righe, separatore, numero, decodifica };
})();
