// Prova senza browser: node prova_jsdom.js <cartella con clima/> <istat> [cartella node_modules di jsdom]
// Carica clima_storico.js in jsdom, serve i JSON da disco al posto di fetch e stampa cosa viene disegnato.
const fs = require("fs"), path = require("path");
const [, , base, istat, nm] = process.argv;
const { JSDOM } = require(nm ? path.join(nm, "jsdom") : "jsdom");
const dom = new JSDOM(`<!doctype html><div id="box"></div>`, { runScripts: "outside-only" });
const w = dom.window;
w.fetch = async (u) => {
  const p = path.join(base, u.replace(/^dati\//, "").split("?")[0]);
  const ok = fs.existsSync(p);
  return { ok, status: ok ? 200 : 404, json: async () => JSON.parse(fs.readFileSync(p, "utf8")) };
};
w.eval(fs.readFileSync(path.join(__dirname, "clima_storico.js"), "utf8"));
(async () => {
  const box = w.document.getElementById("box");
  await w.EUGENIO_CLIMA.mostra(istat, box, {});
  console.log("titolo:", box.querySelector("h3").textContent);
  console.log("cifre:", [...box.querySelectorAll(".cifra")].map((c) => c.textContent).join(" | "));
  const svgs = box.querySelectorAll("svg");
  console.log("grafici:", svgs.length, "barre:", svgs[0].querySelectorAll("rect").length,
    "linee:", svgs[0].querySelectorAll("line").length);
  const righe = box.querySelectorAll("table.mensili")[0].querySelectorAll("tbody tr");
  console.log("tabella mensile:", righe.length, "righe; gennaio:", righe[0].textContent);
  const sel = box.querySelector("select");
  sel.value = "a:1956"; sel.dispatchEvent(new w.Event("change"));
  await new Promise((r) => setTimeout(r, 50));
  console.log("anno 1956, febbraio:", box.querySelectorAll("table.mensili")[0].querySelectorAll("tbody tr")[1].textContent);
  console.log("periodi:", [...box.querySelectorAll("table.mensili")[1].querySelectorAll("tbody tr")].map((r) => r.textContent).join(" / "));
})().catch((e) => { console.error("ERRORE", e); process.exit(1); });
