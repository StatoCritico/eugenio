"use strict";
// Pagina interna dello stato della pipeline degli edifici (fase 10, Fase C): legge /api/interno/edifici/stato
// (Cloudflare Access + JWT verificato dall'api) e mostra zone, tessere, notti, errori, disco e fonti. Sola lettura.
(function () {
  const $ = (id) => document.getElementById(id);
  const fmt = (v, d = 0) => (v === null || v === undefined || !Number.isFinite(+v) ? "—" : (+v).toLocaleString("it-IT", { maximumFractionDigits: d, minimumFractionDigits: d }));
  const data = (s) => { if (!s) return "—"; const d = new Date(s); return Number.isNaN(+d) ? String(s) : d.toLocaleString("it-IT", { dateStyle: "short", timeStyle: "short" }); };
  function h(tag, cls, testo) { const e = document.createElement(tag); if (cls) e.className = cls; if (testo !== undefined && testo !== null) e.textContent = String(testo); return e; }
  function tabella(intest, righe, numeriche = []) {
    const w = h("div", "tabella-scorre"), t = h("table"), r1 = t.createTHead().insertRow();
    intest.forEach((x, k) => r1.appendChild(h("th", numeriche.includes(k) ? "num" : null, x)));
    const b = t.createTBody();
    righe.forEach((r) => { const tr = b.insertRow(); r.forEach((c, k) => tr.appendChild(h("td", numeriche.includes(k) ? "num" : null, c))); });
    w.appendChild(t); return w;
  }
  const STATI = [["fatta", "s-fatta", "fatte"], ["errore", "s-errore", "con errore (da riprovare)"], ["saltata", "s-saltata", "saltate"],
    ["senza rilievo", "s-senza", "senza rilievo"], ["da fare", "s-dafare", "da fare"]];

  // frase dello stato della zona: quella del server (situazione, dal 05/11/2026, coerente con l'ultima notte); con un'api
  // più vecchia si ricava qui con la stessa regola
  function testoSituazione(z) {
    if (z.situazione && z.situazione.testo) {
      return z.situazione.stato === "completata" && z.completata ? `Zona completata il ${data(z.completata)}.` : z.situazione.testo;
    }
    const dsm = (z.fonti || []).some((f) => (f.tipo === "dsm" || f.tipo === "las") && f.stato === "attiva");
    const m = [];
    if (!dsm) m.push("nessuna fonte DSM o LAS attiva");
    if (!z.corpi || !z.totale_tessere) m.push(`${z.corpi || 0} corpi della Fase A (manca prepara)`);
    if (m.length) return `In attesa: ${m.join(" e ")}.`;
    return z.completata ? `Zona completata il ${data(z.completata)}.` : "Zona in corso.";
  }

  function zona(z) {
    const s = h("section", "zona");
    const t = h("h2", null, z.nome || z.zona); if (z.prova) t.appendChild(h("span", "prova", "prova"));
    s.appendChild(t);
    const c = z.conteggi || {}, tot = z.totale_tessere || 0;
    const fatte = (c.fatta || 0) + (c["senza rilievo"] || 0) + (c.saltata || 0);
    s.appendChild(h("p", null, `${fmt(fatte)} tessere su ${fmt(tot)} completate (${tot ? fmt(100 * fatte / tot) : 0} %), ${fmt(z.corpi)} corpi della Fase A nella zona. `
      + testoSituazione(z) + ` Ultimo aggiornamento: ${data(z.aggiornato)}.`));
    const barra = h("div", "barra"); barra.setAttribute("role", "img");
    barra.setAttribute("aria-label", STATI.map(([k, , n]) => `${c[k] || 0} ${n}`).join(", "));
    STATI.forEach(([k, cls]) => { if (c[k] && tot) { const i = h("i", cls); i.style.width = `${100 * c[k] / tot}%`; barra.appendChild(i); } });
    s.appendChild(barra);
    const leg = h("p", "legenda-barra");
    STATI.forEach(([k, cls, n]) => { const sp = h("span"); sp.appendChild(h("i", cls)); sp.append(`${n}: ${fmt(c[k] || 0)}`); leg.appendChild(sp); });
    s.appendChild(leg);
    const q = Object.entries(z.qualita || {});
    if (q.length) { s.appendChild(h("h3", null, "Esiti per qualità (corpi)")); s.appendChild(tabella(["Esito", "Corpi"], q.sort((a, b) => b[1] - a[1]).map(([k, v]) => [k, fmt(v)]), [1])); }
    s.appendChild(h("h3", null, "Coda"));
    s.appendChild(h("p", null, z.prossime && z.prossime.length ? `Prossime tessere: ${z.prossime.join(", ")}.` : "Nessuna tessera in coda."));
    if (z.saltate && z.saltate.length) s.appendChild(h("p", "errore", `Tessere saltate dopo troppi tentativi: ${z.saltate.join(", ")}.`));
    const e = (z.esecuzioni || []).slice().reverse();
    s.appendChild(h("h3", null, `Ultime ${e.length} notti`));
    s.appendChild(tabella(["Inizio", "Fine", "Esito", "Motivo", "Tessere fatte", "Errori", "Corpi", "Scaricati (MB)"],
      e.map((x) => [data(x.inizio), data(x.fine), x.esito || "—", x.motivo || "", fmt(x.tessere_fatte), fmt(x.tessere_errore), fmt(x.corpi), fmt((x.byte || 0) / 1048576, 1)]), [4, 5, 6, 7]));
    const er = (z.errori || []).slice().reverse();
    s.appendChild(h("h3", null, "Errori"));
    s.appendChild(er.length ? tabella(["Quando", "Tessera", "Tentativo", "Errore"], er.map((x) => [data(x.quando), x.tessera, fmt(x.tentativo), x.errore]), [2])
      : h("p", null, "Nessun errore."));
    s.appendChild(h("h3", null, "Fonti"));
    const ft = tabella(["Fonte", "Tipo", "Stato", "Licenza", "Motivo", "Ultima verifica"], (z.fonti || []).map((f) => [f.descrizione || f.id, f.tipo, f.stato,
      `${f.licenza || "—"}${f.licenza_confermata ? "" : " (da confermare)"}`, f.stato === "attiva" ? "" : (f.motivo || ""), f.verifica || ""]));
    ft.querySelectorAll("tbody tr").forEach((tr) => { const td = tr.children[2]; td.className = `stato-fonte ${td.textContent === "attiva" ? "attiva" : "attesa"}`; });
    s.appendChild(ft);
    const ts = Object.entries(z.tessere || {}).filter(([, v]) => v.stato === "fatta").slice(-40).reverse();
    if (ts.length) {
      s.appendChild(h("h3", null, "Ultime tessere elaborate"));
      s.appendChild(tabella(["Tessera", "Fonte", "Fatta", "Corpi", "Falde", "Secondi", "Scaricati (MB)", "Restano (kB)"],
        ts.map(([k, v]) => [k, v.fonte || "—", data(v.fatta), fmt(v.corpi), fmt(v.falde), fmt(v.secondi, 1), fmt((v.byte_scaricati || 0) / 1048576, 1), fmt((v.byte_prodotti || 0) / 1024)]), [3, 4, 5, 6, 7]));
    }
    return s;
  }

  async function carica() {
    const m = $("messaggio");
    try {
      const r = await fetch("/api/interno/edifici/stato", { credentials: "same-origin", cache: "no-store" });
      if (!r.ok) {
        let d = ""; try { d = (await r.json()).detail || ""; } catch { /* testo semplice */ }
        throw new Error(r.status === 403 ? "accesso riservato (serve l'accesso di Cloudflare)" : d || `HTTP ${r.status}`);
      }
      const d = await r.json();
      m.textContent = d.zone.length ? "" : "La pipeline non ha ancora scritto nessuno stato.";
      m.classList.remove("errore");
      $("utente").textContent = d.utente ? `Accesso: ${d.utente}.` : "";
      $("generato").textContent = data(d.generato);
      const sd = $("schede-disco"); sd.innerHTML = "";
      Object.entries(d.disco || {}).forEach(([k, v]) => {
        const c = h("div", "scheda"); c.appendChild(h("span", null, k === "dati" ? "Disco dei dati" : "Archivio degli edifici"));
        c.appendChild(h("b", null, `${fmt(v.libero_gb, 1)} GB liberi`)); c.appendChild(h("small", null, `su ${fmt(v.totale_gb, 0)} GB (usati ${fmt(v.usato_gb, 1)})`));
        sd.appendChild(c);
      });
      $("disco").hidden = !Object.keys(d.disco || {}).length;
      const zz = $("zone"); zz.innerHTML = "";
      d.zone.forEach((z) => zz.appendChild(zona(z)));
    } catch (e) {
      m.textContent = `Stato non disponibile: ${e.message || e}`; m.classList.add("errore");
    }
  }
  $("ricarica").addEventListener("click", carica);
  carica();
})();
