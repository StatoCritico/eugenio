// Prova della pagina indicatori.html con Playwright (chromium): errori JS, scorrimento orizzontale, screenshot.
//   cd <cartella del sito> && python3 -m http.server 8765 &
//   node tests/pagina.js http://localhost:8765 <cartella screenshot>
// Controlla anche che il menu "Indicatori" sia in tutte le pagine e che l'indice laterale di faq, metodo e
// sitografia funzioni ancora.
const { chromium } = require("playwright");

const base = process.argv[2] || "http://localhost:8765";
const cartella = process.argv[3] || "screenshot";
const PAGINE = ["index.html", "patrimonio.html", "legge10.html", "dati.html", "indicatori.html", "metodo.html", "faq.html",
  "sitografia.html", "mirror.html", "contatti.html", "licenza.html", "privacy.html"];

(async () => {
  const browser = await chromium.launch();
  const esiti = [];
  let errori = 0;
  for (const [larg, alt, nome] of [[1280, 900, "desktop"], [390, 844, "telefono"]]) {
    const ctx = await browser.newContext({ viewport: { width: larg, height: alt }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    const js = [];
    page.on("pageerror", (e) => js.push(e.message));
    page.on("console", (m) => { if (m.type() === "error" && !/Failed to load resource|404|\/api\//.test(m.text())) js.push(m.text()); });
    await page.goto(`${base}/indicatori.html`, { waitUntil: "networkidle" });
    await page.waitForSelector("#passo-risultato:not([hidden])", { timeout: 15000 });
    const dati = await page.evaluate(() => ({
      ente: document.getElementById("ente").value,
      titolo: document.getElementById("titolo-ente").textContent,
      confronto: [...document.querySelectorAll("#confronto tbody tr")].map((r) => [...r.children].map((c) => c.textContent)),
      scorre: document.documentElement.scrollWidth > window.innerWidth + 1,
      larghezza: document.documentElement.scrollWidth,
      minimappa: !!document.querySelector(".minimappa svg"),
      voceMenu: document.querySelector('nav[aria-label="Pagine"] a[aria-current="page"]')?.textContent,
    }));
    await page.screenshot({ path: `${cartella}/indicatori_${nome}.png`, fullPage: true });
    // interazioni: componenti, un altro indicatore, un'altra regione dalla piccola mappa, il consolidato
    await page.check("#mostra-componenti");
    await page.click("#scelta-rapporto button:nth-child(1)");
    await page.hover("#grafico-rapporto svg", { position: { x: 200, y: 100 } });
    await page.screenshot({ path: `${cartella}/indicatori_${nome}_componenti.png`, fullPage: true });
    await page.selectOption("#regione", "09");
    await page.waitForFunction(() => document.getElementById("ente").value.startsWith("090-"));
    const toscana = await page.evaluate(() => ({ ente: document.getElementById("ente").value,
      scorre: document.documentElement.scrollWidth > window.innerWidth + 1 }));
    await page.selectOption("#regione", "04");
    await page.waitForFunction(() => document.getElementById("ente").value.startsWith("04"));
    await page.screenshot({ path: `${cartella}/indicatori_${nome}_trentino.png`, fullPage: false });
    await page.click('.minimappa path[data-cod="08"]');
    await page.waitForFunction(() => document.getElementById("ente").value === "080-114");
    esiti.push({ nome, ...dati, toscana, errori_js: js });
    if (js.length || dati.scorre || toscana.scorre) errori++;
    // le altre pagine: menu con "Indicatori" subito dopo "Dati storici", niente errori, niente scorrimento
    for (const p of PAGINE) {
      const err = [];
      const q = await ctx.newPage();
      q.on("pageerror", (e) => err.push(e.message));
      await q.goto(`${base}/${p}`, { waitUntil: "load" });
      await q.waitForTimeout(300);
      const r = await q.evaluate(() => {
        const voci = [...document.querySelectorAll('nav[aria-label="Pagine"] a')].map((a) => a.textContent.trim());
        return { voci, dopo: voci[voci.indexOf("Dati storici") + 1], indice: !!document.querySelector(".indice-laterale"),
          scorre: document.documentElement.scrollWidth > window.innerWidth + 1,
          css: [...document.querySelectorAll('link[rel="stylesheet"], script[src]')].map((x) => x.getAttribute("href") || x.getAttribute("src")).filter((x) => /\.(css|js)\?/.test(x) && !/v=20261027g/.test(x)) };
      });
      if (["metodo.html", "faq.html", "sitografia.html"].includes(p) && nome === "desktop")
        await q.screenshot({ path: `${cartella}/menu_${p.replace(".html", "")}.png` });
      const ok = r.dopo === "Indicatori" && !r.scorre && !err.length && !r.css.length
        && (!["metodo.html", "faq.html", "sitografia.html"].includes(p) || r.indice);
      if (!ok) errori++;
      esiti.push({ nome, pagina: p, ok, ...r, errori_js: err });
      await q.close();
    }
    await ctx.close();
  }
  await browser.close();
  console.log(JSON.stringify(esiti, null, 1));
  console.log(errori ? `PROBLEMI: ${errori}` : "TUTTO A POSTO");
  process.exit(errori ? 1 : 0);
})();
