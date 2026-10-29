// Verifica anti-robot (Cloudflare Turnstile) per le richieste che costano o consumano quote: previsione, patrimonio,
// geocodifica, particella ed estrazione dei Dati climatici (servizio/protezione.py sul server).
//
// Si carica in tutte le pagine (parti/testa.html) e avvolge window.fetch: le pagine non cambiano. Alla prima
// richiesta protetta legge /api/protezione; se il server ha la verifica accesa carica Turnstile, ottiene un gettone
// (di solito senza chiedere nulla: il riquadro compare solo se Cloudflare vuole un clic), lo scambia con un gettone di
// sessione (POST /api/sessione, valido mezz'ora) e lo manda nell'intestazione X-EuGEnio-Sessione. Se il server
// risponde 401 con X-EuGEnio-Verifica (sessione scaduta, rete cambiata, api riavviata) rifà la verifica una volta
// e ripete la richiesta. Senza verifica sul server (prove, mirror) non fa nulla.
(function () {
  "use strict";
  const PROTETTE = /\/api\/(previsione|patrimonio|geocodifica|particella|storici\/estrai)(?:[/?#]|$)/;
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

  window.fetch = async function (input, init) {
    const url = indirizzo(input);
    if (!PROTETTE.test(url)) return originale(input, init);
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
