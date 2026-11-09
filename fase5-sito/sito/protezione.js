// Verifica anti-robot (Cloudflare Turnstile) per le richieste che costano o consumano quote: previsione, patrimonio,
// geocodifica, particella, estrazione dei Dati climatici, edifici OpenStreetMap al volo di Modelli 3D e proposta di un DB
// topografico all'archivio comune (07/11/2026;
// servizio/protezione.py sul server).
//
// Si carica in tutte le pagine (parti/testa.html) e avvolge window.fetch: le pagine non cambiano. Alla prima
// richiesta protetta legge /api/protezione; se il server ha la verifica accesa carica Turnstile, ottiene un gettone
// (di solito senza chiedere nulla: il riquadro compare solo se Cloudflare vuole un clic), lo scambia con un gettone di
// sessione (POST /api/sessione, valido mezz'ora) e lo manda nell'intestazione X-EuGEnio-Sessione. Se il server
// risponde 401 con X-EuGEnio-Verifica (sessione scaduta, rete cambiata, api riavviata) rifà la verifica una volta
// e ripete la richiesta. Senza verifica sul server (prove, mirror) non fa nulla.
// Dal 09/11/2026 gestisce anche i limiti orari delle fonti della mappa (429 di ortofoto, strati, edifici OSM, terreno):
// pausa della fonte per il tempo del Retry-After e nota sotto la mappa (vedi «limiti orari delle fonti della mappa»).
// Dal 09/11/2026 c anche le fonti che non rispondono (tessere vuote con X-Ortofoto-Errore, risposte 5xx, rete caduta):
// dopo errori ripetuti la fonte si ferma qualche minuto, con la nota «La fonte … non risponde, riprovo tra N minuti»
// (vedi «fonti che non rispondono»). Turnstile si carica solo alla prima richiesta protetta (ricerca, edifici
// OpenStreetMap, Patrimonio…): le righe di challenges.cloudflare.com in Console (CSP «connect-src … data:», «OTS parsing
// error», avvisi WebGPU) vengono dal suo riquadro e dalla sua pagina, non da EuGEnio.
(function () {
  "use strict";
  const PROTETTE = /\/api\/(previsione|patrimonio|geocodifica|particella|storici\/estrai|edifici\/osm|dbtr\/inizia)(?:[/?#]|$)/;
  const SCRIPT = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
  const CHIAVE = "eugenio_sessione";
  const originale = window.fetch.bind(window);
  let config = null;          // promessa della configurazione del server
  let script = null;          // promessa del caricamento di Turnstile
  let inCorso = null;         // promessa di una sessione in arrivo
  let sessione = null;        // { g, scade, base }
  let riquadro = null;

  try {
    const s = JSON.parse(sessionStorage.getItem(CHIAVE) || "null");
    if (s && s.g && s.scade * 1000 > Date.now()) sessione = s;
  } catch (e) { /* archivio del browser non disponibile: si rifà la verifica */ }

  function salva(s) {
    sessione = s;
    try { s ? sessionStorage.setItem(CHIAVE, JSON.stringify(s)) : sessionStorage.removeItem(CHIAVE); } catch (e) { /* niente */ }
  }

  function indirizzo(input) {
    if (typeof input === "string") return input;
    if (input instanceof URL) return input.href;
    return (input && input.url) || "";
  }

  // "https://…/api/previsione" o "/api/previsione" → base del sito ("" per lo stesso sito)
  function base(url) {
    const u = new URL(url, location.href);
    const i = u.pathname.indexOf("/api/");
    const b = u.origin + u.pathname.slice(0, i);
    return u.origin === location.origin && i === 0 ? "" : b;
  }

  function errore(testo, stato) {
    return new Response(JSON.stringify({ detail: testo }), {
      status: stato || 401, headers: { "Content-Type": "application/json; charset=utf-8" } });
  }

  function leggiConfig(b) {
    if (!config) {
      config = originale(b + "/api/protezione", { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : { turnstile: null }))
        .catch(() => { config = null; return { turnstile: null }; });
    }
    return config;
  }

  function caricaTurnstile() {
    if (window.turnstile) return Promise.resolve(window.turnstile);
    if (!script) {
      script = new Promise((ok, ko) => {
        const s = document.createElement("script");
        s.src = SCRIPT;
        s.async = true;
        s.onload = () => (window.turnstile ? ok(window.turnstile) : ko(new Error("Turnstile non disponibile")));
        s.onerror = () => { script = null; ko(new Error("non caricata")); };
        document.head.appendChild(s);
      });
    }
    return script;
  }

  // riquadro in basso a destra, visibile solo se Cloudflare chiede un'interazione
  function preparaRiquadro() {
    if (riquadro) return riquadro;
    riquadro = document.createElement("div");
    riquadro.className = "verifica-robot";
    riquadro.setAttribute("role", "dialog");
    riquadro.setAttribute("aria-label", "Verifica anti-robot");
    riquadro.style.cssText = "visibility:hidden;position:fixed;right:16px;bottom:16px;z-index:1000;max-width:calc(100vw - 32px);" +
      "padding:12px 14px;border:1px solid var(--bordo,#888);border-radius:8px;background:var(--foglio,#fff);" +
      "color:var(--inchiostro,#111);box-shadow:0 6px 24px rgba(0,0,0,.35);font-size:14px;line-height:1.4";
    const p = document.createElement("p");
    p.style.cssText = "margin:0 0 8px";
    p.textContent = "Una verifica veloce per sapere che non sei un programma automatico.";
    const w = document.createElement("div");
    w.className = "verifica-widget";
    riquadro.append(p, w);
    document.body.appendChild(riquadro);
    return riquadro;
  }

  async function gettoneTurnstile(sitekey) {
    let ts;
    try { ts = await caricaTurnstile(); }
    catch (e) {
      throw new Error("La verifica anti-robot di Cloudflare non si è caricata: controlla che il browser o un " +
        "blocco pubblicità non fermino challenges.cloudflare.com, poi ricarica la pagina.");
    }
    const box = preparaRiquadro();
    return new Promise((ok, ko) => {
      let id = null;
      // il riquadro resta nella pagina ma invisibile (con display:none il controllo di Cloudflare non partirebbe)
      const fine = (fn, valore) => {
        box.style.visibility = "hidden";
        setTimeout(() => { try { ts.remove(id); } catch (e) { /* già tolto */ } }, 0);
        fn(valore);
      };
      id = ts.render(box.querySelector(".verifica-widget"), {
        sitekey,
        action: "sessione",
        appearance: "interaction-only",
        theme: document.documentElement.dataset.theme === "light" ? "light" : "dark",
        language: "it",
        callback: (t) => fine(ok, t),
        "error-callback": () => { fine(ko, new Error("Verifica anti-robot non riuscita: ricarica la pagina e riprova.")); return true; },
        "timeout-callback": () => fine(ko, new Error("Verifica anti-robot scaduta: riprova.")),
        "before-interactive-callback": () => { box.style.visibility = "visible"; },
      });
    });
  }

  function nuovaSessione(b) {
    if (inCorso) return inCorso;
    inCorso = (async () => {
      const cfg = await leggiConfig(b);
      if (!cfg || !cfg.turnstile) return null;
      const token = await gettoneTurnstile(cfg.turnstile);
      const r = await originale(b + "/api/sessione", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }) });
      let d = null;
      try { d = await r.json(); } catch (e) { /* risposta non JSON */ }
      if (!r.ok) throw new Error((d && d.detail) || `Verifica anti-robot non riuscita (errore ${r.status})`);
      salva(d && d.sessione ? { g: d.sessione, scade: d.scade, base: b } : null);
      return sessione && sessione.g;
    })().finally(() => { inCorso = null; });
    return inCorso;
  }

  async function gettone(b, forza) {
    if (!forza && sessione && sessione.base === b && sessione.scade * 1000 - Date.now() > 60000) return sessione.g;
    if (forza) salva(null);
    return nuovaSessione(b);
  }

  function invia(input, init, g) {
    const opts = Object.assign({}, init || {});
    const h = new Headers(opts.headers || (input instanceof Request ? input.headers : undefined));
    if (g) h.set("X-EuGEnio-Sessione", g);
    opts.headers = h;
    return originale(input, opts);
  }

  // ------------------------------------------------------------------ limiti orari delle fonti della mappa (09/11/2026)
  // Prove J10 di Paolo: dopo il primo 429 la mappa chiedeva ancora migliaia di tessere, tutte rifiutate (righe rosse in
  // Console, ortofoto e terreno neri). Ora un 429 di ortofoto, strati (particelle e contorni), edifici OpenStreetMap o
  // terreno ferma le richieste di quella fonte per il tempo indicato dal server (Retry-After, tra 30 secondi e 20 minuti):
  // nel frattempo la pagina risponde da sé con un 429 «finto», senza rete (niente righe in Console né carico sul server).
  // Sotto la mappa, prima di «Genera il 3D» (o dei comandi di Ortofoto), una nota dice quale fonte è ferma, che è il
  // limite orario e tra quanto riprova; finita la pausa le pagine ricaricano le tessere (evento «eugenio:limite») e la
  // nota sparisce alla prima risposta buona della fonte.
  const FONTI_LIMITE = {
    ortofoto: "Ortofoto", strati: "Particelle catastali e contorni degli edifici", edifici_osm: "Edifici OpenStreetMap",
    terreno: "Terreno 3D", tessere_copia: "Tessere della mappa (ortofoto, particelle, terreno)", edifici_osm_copia: "Edifici OpenStreetMap" };
  // un limite della copia ferma tutte le famiglie che ne dipendono
  const COPRE = { tessere_copia: ["ortofoto", "strati", "terreno"], edifici_osm_copia: ["edifici_osm"] };
  const PAUSA_MIN_S = 30, PAUSA_MAX_S = 1200;
  const pause = {};            // tipo → { fino, prova } (prova: pausa finita, si aspetta la prima risposta buona)
  let nota = null, orologio = null;
  function famigliaDi(url) {
    let pth;
    try { pth = new URL(url, location.href).pathname; } catch (e) { return null; }
    if (/^\/api\/terreno\/\d/.test(pth)) return "terreno";
    if (/^\/api\/edifici\/osm(?:[/?#]|$)/.test(pth)) return "edifici_osm";
    const m = /^\/api\/ortofoto\/strati\/([^/]+)\/\d/.exec(pth);
    if (m) return /osm/.test(m[1]) ? "edifici_osm" : "strati";
    if (/^\/api\/ortofoto\/(?!fonti|strati)[^/]+\/\d+\/\d+\/\d+\./.test(pth)) return "ortofoto";
    return null;
  }
  function inPausa(fam) {
    const ora = Date.now();
    for (const [tipo, p] of Object.entries(pause)) {
      if (p.fino <= ora) continue;
      if (tipo === fam || (COPRE[tipo] || []).includes(fam)) return p;
    }
    return null;
  }
  function minuti(ms) {
    const s = Math.max(0, Math.round(ms / 1000));
    if (s < 60) return `${s} secondi`;
    const m = Math.ceil(s / 60);
    return m === 1 ? "1 minuto" : `${m} minuti`;
  }
  // dove va la nota: sotto la mappa, prima di «Genera il 3D» (#comandi-edificio) o dei comandi di Ortofoto; altrimenti
  // subito dopo la prima mappa della pagina
  function preparaNota() {
    if (nota && document.body.contains(nota)) return nota;
    nota = document.getElementById("nota-limiti");
    if (!nota) {
      nota = document.createElement("p");
      nota.id = "nota-limiti"; nota.className = "aiuto nota-limiti"; nota.setAttribute("role", "status"); nota.setAttribute("aria-live", "polite");
      nota.hidden = true;
      const prima = document.getElementById("comandi-edificio") || document.querySelector(".comandi-ortofoto");
      const mappa = document.querySelector(".mappa-gl, .mappa");
      if (prima && prima.parentNode) prima.parentNode.insertBefore(nota, prima);
      else if (mappa && mappa.parentNode) mappa.after(nota);
      else (document.querySelector("main") || document.body).prepend(nota);
    }
    return nota;
  }
  function disegnaNota() {
    const ora = Date.now(), righe = [];
    for (const [tipo, p] of Object.entries(pause)) {
      const nome = FONTI_LIMITE[tipo] || tipo;
      if (p.fino > ora) righe.push(`${nome}: raggiunto il limite orario di richieste per il tuo indirizzo. Mi fermo e riprovo da solo tra ${minuti(p.fino - ora)}.`);
      else righe.push(`${nome}: riprovo adesso…`);
    }
    for (const g of Object.values(guasti)) {
      if (!g.nome) continue;
      if (g.fino > ora) righe.push(`${g.nome}: la fonte non risponde (o è molto richiesta). Mi fermo e riprovo da solo tra ${minuti(g.fino - ora)}.`);
      else if (g.prova) righe.push(`${g.nome}: riprovo adesso…`);
    }
    const n = preparaNota();
    if (!n) return;
    n.textContent = righe.join(" ");
    n.hidden = !righe.length;
    if (!righe.length && orologio) { clearInterval(orologio); orologio = null; }
  }
  function riprendi(tipo) {
    const p = pause[tipo];
    if (!p || p.prova) return;
    p.prova = true;
    disegnaNota();
    document.dispatchEvent(new CustomEvent("eugenio:limite", { detail: { tipo, famiglie: [tipo, ...(COPRE[tipo] || [])], fermo: false } }));
  }
  function ferma(tipo, secondi) {
    const s = Math.min(PAUSA_MAX_S, Math.max(PAUSA_MIN_S, Number.isFinite(secondi) ? secondi : 180));
    const vecchia = pause[tipo];
    if (vecchia && vecchia.fino > Date.now() && !vecchia.prova) return;      // già ferma: un solo messaggio
    pause[tipo] = { fino: Date.now() + s * 1000, prova: false };
    if (vecchia && vecchia.timer) clearTimeout(vecchia.timer);
    pause[tipo].timer = setTimeout(() => riprendi(tipo), s * 1000);
    if (window.console && console.info) console.info(`EuGEnio: ${FONTI_LIMITE[tipo] || tipo} ferma per ${Math.round(s)} s (limite orario raggiunto)`);
    disegnaNota();
    if (!orologio) orologio = setInterval(disegnaNota, 15000);
    document.dispatchEvent(new CustomEvent("eugenio:limite", { detail: { tipo, famiglie: [tipo, ...(COPRE[tipo] || [])], fermo: true, secondi: s } }));
  }
  function rispostaBuona(fam) {
    let cambiato = false;
    for (const [tipo, p] of Object.entries(pause)) {
      if (p.fino > Date.now()) continue;
      if (tipo === fam || (COPRE[tipo] || []).includes(fam)) { delete pause[tipo]; cambiato = true; }
    }
    if (cambiato) disegnaNota();
  }
  // ------------------------------------------------------------------ fonti che non rispondono (09/11/2026 c)
  // Prove P9 di Paolo: righe rosse «502 Bad Gateway» di AGEA 2012 e ortofoto «a pezzi», senza nessuna spiegazione. Il
  // server ora risponde a un errore della fonte con una tessera vuota (200, X-Ortofoto-Errore: fonte, occupata o ferma,
  // Retry-After): niente righe rosse. Qui si contano questi errori (e le risposte 5xx o la rete caduta, per tutte le
  // fonti della mappa): dopo ERRORI_SOGLIA errori in ERRORI_FINESTRA_S secondi, o subito se il server dice «ferma», la
  // fonte si ferma per il tempo del Retry-After (da 30 s a 20 minuti), con la nota sotto la mappa; finita la pausa le
  // tessere si ricaricano. Un errore isolato fa solo ricaricare le tessere di quella fonte poco dopo (i buchi si riempiono).
  const ERRORI_SOGLIA = 4, ERRORI_FINESTRA_S = 60;
  const nomiFonti = {};          // id della fonte di ortofoto → nome (da /api/ortofoto/fonti)
  const guasti = {};             // chiave (ortofoto:<id>, strati, terreno…) → { errori: [ms], fino, timer, nome, fam }
  let ricarica = null;
  function chiaveFonte(fam, url, r) {
    if (fam !== "ortofoto") return fam;
    const id = (r && r.headers && r.headers.get("X-Ortofoto-Fonte")) || ((/\/api\/ortofoto\/([^/]+)\//.exec(url) || [])[1]) || "?";
    return `ortofoto:${id}`;
  }
  function nomeGuasto(k, fam) {
    if (k.startsWith("ortofoto:")) { const id = k.slice(9); return `Ortofoto «${nomiFonti[id] || id}»`; }
    return FONTI_LIMITE[fam] || fam;
  }
  function guastoAttivo(k) { const g = guasti[k]; return g && g.fino > Date.now() ? g : null; }
  function ricaricaPresto(fam, secondi) {
    // un errore isolato: le tessere di quella famiglia si richiedono una volta, dopo il Retry-After (15–90 s)
    if (ricarica) return;
    const s = Math.min(90, Math.max(15, Number.isFinite(secondi) ? secondi : 30));
    ricarica = setTimeout(() => { ricarica = null; document.dispatchEvent(new CustomEvent("eugenio:limite", { detail: { tipo: fam, famiglie: [fam], fermo: false } })); }, s * 1000);
  }
  function erroreFonte(fam, url, r, motivo, secondi) {
    const k = chiaveFonte(fam, url, r), ora = Date.now();
    const g = guasti[k] = guasti[k] || { errori: [], fino: 0, fam };
    if (g.fino > ora) return;
    g.errori = g.errori.filter((t) => ora - t < ERRORI_FINESTRA_S * 1000).concat(ora);
    if (motivo !== "ferma" && g.errori.length < ERRORI_SOGLIA) { ricaricaPresto(fam, secondi); return; }
    const s = Math.min(PAUSA_MAX_S, Math.max(PAUSA_MIN_S, Number.isFinite(secondi) && secondi > 0 ? secondi : 120));
    g.fino = ora + s * 1000; g.errori = []; g.nome = nomeGuasto(k, fam);
    if (g.timer) clearTimeout(g.timer);
    g.timer = setTimeout(() => {
      g.prova = true; disegnaNota();
      document.dispatchEvent(new CustomEvent("eugenio:limite", { detail: { tipo: fam, famiglie: [fam], fermo: false, fonte: k } }));
    }, s * 1000);
    if (window.console && console.info) console.info(`EuGEnio: ${g.nome} non risponde, ferma per ${Math.round(s)} s`);
    disegnaNota();
    if (!orologio) orologio = setInterval(disegnaNota, 15000);
    document.dispatchEvent(new CustomEvent("eugenio:limite", { detail: { tipo: fam, famiglie: [fam], fermo: true, secondi: s, fonte: k } }));
  }
  function fonteBuona(fam, url, r) {
    const k = chiaveFonte(fam, url, r), g = guasti[k];
    if (!g) return;
    if (g.fino > Date.now()) return;
    delete guasti[k];
    if (g.prova || g.nome) disegnaNota();
  }
  async function conLimiti(fam, chiama, url) {
    const p = inPausa(fam);
    if (p) {
      return new Response(JSON.stringify({ detail: "Fonte ferma per il limite orario: riprovo più tardi." }), {
        status: 429, headers: { "Content-Type": "application/json; charset=utf-8", "X-EuGEnio-Pausa": "1",
          "Retry-After": String(Math.ceil((p.fino - Date.now()) / 1000)) } });
    }
    const g = guastoAttivo(chiaveFonte(fam, url, null));
    if (g) {
      return new Response(JSON.stringify({ detail: "Fonte che non risponde: riprovo più tardi." }), {
        status: 503, headers: { "Content-Type": "application/json; charset=utf-8", "X-EuGEnio-Pausa": "1",
          "Retry-After": String(Math.ceil((g.fino - Date.now()) / 1000)) } });
    }
    let r;
    try { r = await chiama(); }
    catch (e) {
      if (!(e && e.name === "AbortError")) erroreFonte(fam, url, null, "rete", NaN);
      throw e;
    }
    const errore = r.headers.get("X-Ortofoto-Errore");
    if (r.status === 429) {
      const tipo = r.headers.get("X-EuGEnio-Limite") || fam;
      ferma(FONTI_LIMITE[tipo] ? tipo : fam, parseInt(r.headers.get("Retry-After") || "", 10));
    } else if (errore || (r.status >= 500 && r.status !== 501)) {
      erroreFonte(fam, url, r, errore || String(r.status), parseInt(r.headers.get("Retry-After") || "", 10));
    } else if (r.ok) { rispostaBuona(fam); fonteBuona(fam, url, r); }
    return r;
  }
  // mappa MapLibre: gli errori delle tessere (429, 503, 404 fuori zona) non vanno in Console uno per uno (MapLibre scrive
  // console.error per ogni tessera se nessuno ascolta «error»); finita una pausa si ricaricano le sorgenti di quella fonte
  function collega(m) {
    if (!m || m.__eugenioLimiti) return;
    m.__eugenioLimiti = true;
    let avvisati = 0;
    m.on("error", (e) => {
      const st = e && e.error && (e.error.status || (/\((\d{3})\)/.exec(String(e.error.message || "")) || [])[1]);
      if (e && (e.tile || e.sourceId) && /^(4|5)\d\d$/.test(String(st || ""))) return;      // tessera rifiutata: la nota basta
      if (avvisati++ < 3 && window.console) console.warn("Mappa:", (e && e.error && e.error.message) || e);
    });
    document.addEventListener("eugenio:limite", (ev) => {
      if (!ev.detail || ev.detail.fermo) return;
      const fam = ev.detail.famiglie || [];
      let stile;
      try { stile = m.getStyle(); } catch (e) { return; }
      const strati = (stile && stile.layers) || [];
      for (const [id, def] of Object.entries((stile && stile.sources) || {})) {
        const t = def && def.tiles && def.tiles[0];
        if (!t || !fam.includes(famigliaDi(t.replace(/\{[xyz]\}/g, "1")))) continue;
        // si tolgono e si rimettono sorgente e strati, nello stesso ordine: ricaricare le tessere raster finite in errore
        // (setTiles o refreshTiles) fa fallire il disegno dentro MapLibre 5 (TypeError «reading 'bind'»)
        try {
          const usa = strati.map((l, k) => [l, k]).filter(([l]) => l.source === id);
          const dopo = usa.map(([, k]) => { const s2 = strati.slice(k + 1).find((l) => l.source !== id && m.getLayer(l.id)); return s2 ? s2.id : undefined; });
          const terreno = m.getTerrain && m.getTerrain();
          const sotto = terreno && terreno.source === id;
          if (sotto) m.setTerrain(null);
          usa.forEach(([l]) => { if (m.getLayer(l.id)) m.removeLayer(l.id); });
          m.removeSource(id);
          m.addSource(id, def);
          usa.forEach(([l], k) => m.addLayer(l, dopo[k] && m.getLayer(dopo[k]) ? dopo[k] : undefined));
          if (sotto) m.setTerrain(terreno);
        } catch (e) { /* sorgente cambiata nel frattempo: la pagina la rifà da sé */ }
      }
    });
  }
  window.EUGENIO_LIMITI = { famigliaDi, inPausa, ferma, riprendi, pause, collega, FONTI: FONTI_LIMITE, guasti, nomiFonti, erroreFonte };

  // nomi delle fonti di ortofoto per la nota (dalla risposta di /api/ortofoto/fonti, chiunque la chieda)
  function leggiNomi(r) {
    try { r.clone().json().then((d) => ((d && d.fonti) || []).forEach((f) => { if (f && f.id) nomiFonti[f.id] = f.nome || f.id; })).catch(() => {}); }
    catch (e) { /* niente */ }
    return r;
  }
  window.fetch = async function (input, init) {
    const url = indirizzo(input);
    const fam = famigliaDi(url);
    if (/\/api\/ortofoto\/fonti(?:[?#]|$)/.test(url)) return originale(input, init).then(leggiNomi);
    if (!PROTETTE.test(url)) return fam ? conLimiti(fam, () => originale(input, init), url) : originale(input, init);
    if (fam) return conLimiti(fam, () => protetta(url, input, init), url);
    return protetta(url, input, init);
  };
  async function protetta(url, input, init) {
    const b = base(url);
    let g;
    try { g = await gettone(b, false); } catch (e) { return errore(e.message); }
    let r = await invia(input, init, g);
    if (r.status === 401 && r.headers.get("X-EuGEnio-Verifica")) {
      try { g = await gettone(b, true); } catch (e) { return errore(e.message); }
      r = await invia(input, init, g);
    }
    return r;
  };
})();
