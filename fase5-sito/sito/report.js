"use strict";
// Report scaricabili (Excel, Word, PDF), parte comune alle pagine delle funzioni (previsione, Legge 10, patrimonio).
// Il server riceve la stessa risposta che la pagina ha avuto dalla sua API e restituisce il file già pronto.
// Contratto: POST /api/report/{tipo}?formato=xlsx|docx|pdf, corpo JSON, risposta binaria con Content-Disposition.
// Se il contratto cambia, si adatta qui: indirizzoReport() per l'URL, le pagine passano il corpo con corpo().
(function () {
  const API = "/api";
  const FORMATI = [
    ["xlsx", "Excel (.xlsx)"],
    ["docx", "Word (.docx)"],
    ["pdf", "PDF"],
  ];

  function indirizzoReport(tipo, formato) {
    return `${API}/report/${encodeURIComponent(tipo)}?formato=${encodeURIComponent(formato)}`;
  }

  // nome del file da Content-Disposition (filename* in UTF-8 ha la precedenza), ripulito da percorsi e caratteri strani
  function nomeDaIntestazione(cd) {
    if (!cd) return null;
    let nome = null;
    const esteso = cd.match(/filename\*\s*=\s*([^']*)'[^']*'([^;]+)/i);
    if (esteso) { try { nome = decodeURIComponent(esteso[2].trim().replace(/^"|"$/g, "")); } catch { nome = null; } }
    if (!nome) {
      const semplice = cd.match(/filename\s*=\s*("([^"]*)"|[^;]+)/i);
      if (semplice) nome = (semplice[2] !== undefined ? semplice[2] : semplice[1]).trim();
    }
    if (!nome) return null;
    nome = nome.split(/[\\/]/).pop().replace(/[\x00-\x1f<>:"|?*]/g, "_").trim();
    return nome && nome !== "." && nome !== ".." ? nome : null;
  }

  async function dettaglio(r) {
    try {
      const d = await r.clone().json();
      if (d && typeof d.detail === "string") return d.detail;
    } catch { /* risposta non JSON */ }
    return null;
  }

  async function erroreChiaro(r) {
    const det = await dettaglio(r);
    if (r.status === 404) return "Il servizio dei report non è ancora attivo sul server. Riprova più tardi; intanto puoi usare gli altri download.";
    if (r.status === 429) {
      const attesa = parseInt(r.headers.get("Retry-After") || "", 10);
      const quando = attesa > 0 ? (attesa < 120 ? `tra ${attesa} secondi` : `tra circa ${Math.ceil(attesa / 60)} minuti`) : "tra qualche minuto";
      return `Hai raggiunto il limite di report per ora: riprova ${quando}.`;
    }
    if (r.status === 413) return "I dati sono troppo grandi per un report: prova con un periodo o un elenco più piccolo.";
    if (r.status >= 500) return `Il server non è riuscito a preparare il report (errore ${r.status}). Riprova tra poco.`;
    return det ? `Report non preparato: ${det}` : `Report non preparato (errore ${r.status}).`;
  }

  function scaricaBlob(blob, nome) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = nome;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  // Aggiunge i tre pulsanti a `contenitore`.
  //   tipo:      "previsione" | "legge10" | "patrimonio"
  //   corpo():   oggetto da inviare (letto al momento del clic, così vale sempre l'ultimo risultato)
  //   nome(ext): nome di riserva se il server non manda Content-Disposition
  //   messaggio(testo, errore): l'area messaggi della pagina
  function pulsanti(contenitore, { tipo, corpo, nome, messaggio, area }) {
    const gruppo = document.createElement("div");
    gruppo.className = "scarica report";
    gruppo.setAttribute("role", "group");
    gruppo.setAttribute("aria-label", "Scarica il report");
    const titolo = document.createElement("span");
    titolo.className = "report-titolo";
    titolo.textContent = "Report:";
    gruppo.appendChild(titolo);
    const bottoni = [];
    let mio = null;   // ultimo messaggio scritto da qui, da cancellare al tentativo successivo

    const avvisa = (testo, errore) => {
      mio = testo;
      messaggio(testo, errore);
      const m = area && document.getElementById(area);
      if (errore && m && m.scrollIntoView) m.scrollIntoView({ block: "nearest", behavior: "smooth" });
    };

    for (const [formato, etichetta] of FORMATI) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "bottone secondario";
      b.textContent = etichetta;
      b.dataset.formato = formato;
      b.addEventListener("click", async () => {
        const area_ = area && document.getElementById(area);
        if (mio !== null && area_ && area_.textContent === mio) messaggio("");
        mio = null;
        bottoni.forEach((x) => { x.disabled = true; });
        b.textContent = "Preparo il file…";
        b.setAttribute("aria-busy", "true");
        gruppo.setAttribute("aria-busy", "true");
        try {
          let dati;
          try { dati = corpo(); } catch { dati = null; }
          if (!dati) throw new Error("Non c'è ancora un risultato da mettere nel report.");
          let r;
          try {
            r = await fetch(indirizzoReport(tipo, formato), {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(dati),
            });
          } catch {
            throw new Error("Server non raggiungibile: controlla la connessione e riprova.");
          }
          if (!r.ok) throw new Error(await erroreChiaro(r));
          // una pagina HTML al posto del file vuol dire che sul server l'indirizzo non porta ancora al servizio
          if (/text\/html/i.test(r.headers.get("Content-Type") || ""))
            throw new Error("Il servizio dei report non è ancora attivo sul server. Riprova più tardi; intanto puoi usare gli altri download.");
          const blob = await r.blob();
          if (!blob.size) throw new Error("Il server ha restituito un file vuoto. Riprova tra poco.");
          scaricaBlob(blob, nomeDaIntestazione(r.headers.get("Content-Disposition")) || nome(formato));
        } catch (e) {
          avvisa(e.message || "Report non preparato.", true);
        } finally {
          b.textContent = etichetta;
          b.removeAttribute("aria-busy");
          gruppo.removeAttribute("aria-busy");
          bottoni.forEach((x) => { x.disabled = false; });
        }
      });
      bottoni.push(b);
      gruppo.appendChild(b);
    }
    contenitore.appendChild(gruppo);
    return gruppo;
  }

  window.EUGENIO_REPORT = { pulsanti, indirizzoReport, nomeDaIntestazione };
})();
