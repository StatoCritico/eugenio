"""Fotovoltaico › «CER – Sviluppo impianti FV» (fv-cer.html, fv_cer.js, cer_fv_calcolo.js; 24/11/2026).

Sui file: voce sperimentale del menu dopo «Cabine primarie» (tendina e telefono), avviso sperimentale, script nell'ordine
giusto, niente localStorage né dati di mercato, indirizzo del GSE solo in rete.js, esempi sintetici dichiarati.
Calcolo con Node (si salta se Node non c'è): lettura delle curve nei tre formati, calendario dell'ora legale, bisezione
della potenza con e senza accumulo, impianti da 1 MW al massimo, punteggio e classi dei terreni.
In Chromium con ?prova=1 (dati sintetici di rete.js) e con /api/cer-fv/terreni simulata: esempio → calcolo → terreni
(A) con la sola probabilità di coltura → cabine del bando (B) → file con i soli codici del GSE; nessun errore JS.
"""
from __future__ import annotations

import functools
import json
import re
import shutil
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

QUI = Path(__file__).resolve().parents[1]
SITO = QUI / "sito"
sys.path.insert(0, str(QUI))
import costruisci_pagine as C  # noqa: E402

NODE = shutil.which("node")


# ---------------------------------------------------------------------------------------------- file
def test_menu_pagina_e_script():
    t = (C.PARTI / "testata.html").read_text(encoding="utf-8")
    # menu completo (pannello) con la parola intera, tendina con la «S»
    assert ('<li><a href="fv-cabine.html">Cabine primarie</a></li><li><a href="fv-cer.html">CER – Sviluppo impianti FV '
            '<span class="cantiere prova">sperimentale</span></a></li>') in t
    assert re.search(r'<li><a href="fv-cabine.html">Cabine primarie</a></li>\s*<li><a href="fv-cer.html">CER – Sviluppo impianti FV '
                     r'<span class="cantiere prova breve" title="sperimentale"><span aria-hidden="true">S</span>', t)
    assert t.count('href="fv-cer.html"') == 2
    s = (SITO / "fv-cer.html").read_text(encoding="utf-8")
    assert "<h1>CER – Sviluppo impianti FV</h1>" in s and 'class="messaggio attenzione sperimentale"' in s
    assert re.search(r'<script src="rete\.js\?v=\w+"></script>\s*<script src="edifici_calcoli\.js\?v=\w+"></script>\s*'
                     r'<script src="cer_fv_calcolo\.js\?v=\w+"></script>\s*<script src="fv_cer\.js\?v=\w+"></script>', s)
    piatto = re.sub(r"\s+", " ", s)
    assert "CC BY-NC-SA 3.0 IT" in piatto and "non si cedono" in piatto and "L.R. Emilia-Romagna 29/05/2026 n. 5" in piatto
    # ogni parametro finisce nel collegamento salvabile (mai i file)
    for k in ("h", "q", "den", "tipo", "incl", "orient", "perdite", "ha", "pmax", "ptot", "dist", "n", "toll"):
        assert f'data-collegamento="{k}"' in s
    assert not re.search(r'<input id="file-[a-z]+"[^>]*data-collegamento', s)
    assert C.main(["--controlla"]) == 0
    for f in ("fv_cer.js", "cer_fv_calcolo.js"):
        js = (SITO / f).read_text(encoding="utf-8")
        codice = "\n".join(r for r in js.splitlines() if not r.lstrip().startswith("//"))
        assert "arcgis.com" not in js and "localStorage" not in codice and "sessionStorage" not in codice
        assert not re.search(r"(?i)\b(pun|psv|igi|ttf)\b", codice)
    for f in ("cer_fv_sedi_esempio.csv", "cer_fv_curve_esempio.csv"):
        assert (SITO / "esempi" / f).read_text(encoding="utf-8").startswith("# DATI SINTETICI DI ESEMPIO")


# ---------------------------------------------------------------------------------------------- calcolo (Node)
PROVA_NODE = r"""
const E = require(process.argv[1] + "/edifici_calcoli.js"); globalThis.EUGENIO_EDIFICI = E;
const F = require(process.argv[1] + "/cer_fv_calcolo.js");
const out = {};
// calendario: 1/7 10:00 UTC = 12:00 ora legale; 15/1 10:00 UTC = 11:00 ora solare; 29 febbraio scartato
out.slotLuglio = F.slotDaUtc(Date.UTC(2025, 6, 1, 10)) === F.slot(7, 1, 12);
out.slotGennaio = F.slotDaUtc(Date.UTC(2025, 0, 15, 10)) === F.slot(1, 15, 11);
out.bisestile = F.slot(2, 29, 3);
// tre formati, stessi consumi (1 kWh all'ora, 0,25 ogni quarto d'ora)
const lungo = ["id;data_ora;kwh"], largo = ["data_ora;A;B"], giorno = ["id;data;" + Array.from({ length: 24 }, (_, i) => "h" + (i + 1)).join(";")];
for (let d = 0; d < 365; d++) {
  const t0 = Date.UTC(2025, 0, 1) + d * 864e5, g = new Date(t0).toISOString().slice(0, 10);
  giorno.push(`A;${g.split("-").reverse().join("/")};` + Array(24).fill("1").join(";"));
  for (let h = 0; h < 24; h++) {
    const s = new Date(t0 + h * 36e5).toISOString().slice(0, 16).replace("T", " ");
    largo.push(`${s};1;2,5`);
    for (let q = 0; q < 4; q++) lungo.push(`A;${new Date(t0 + h * 36e5 + q * 9e5).toISOString().slice(0, 16)};0,25`);
  }
}
const L1 = F.leggiCurve(lungo.join("\n")), L2 = F.leggiCurve(largo.join("\n")), L3 = F.leggiCurve(giorno.join("\n"));
out.formati = [L1.formato, L2.formato, L3.formato];
out.passi = [L1.passoMinuti, L2.passoMinuti, L3.passoMinuti];
out.totali = [F.totale(L1.serie.get("A")), F.totale(L2.serie.get("A")), F.totale(L2.serie.get("B")), F.totale(L3.serie.get("A"))].map(Math.round);
out.copertura = L1.copertura.get("A");
// ore mancanti riempite con la media della stessa ora nello stesso mese
const buchi = largo.filter((r, i) => i === 0 || i % 10 !== 0);
const L4 = F.leggiCurve(buchi.join("\n"));
out.buchi = [Math.round(100 * L4.copertura.get("A")), Math.round(F.totale(L4.serie.get("A")))];
// dimensionamento: ufficio 50 kW 8-18 nei giorni feriali, 10 kW altrimenti
const cons = new Float64Array(8760);
for (let s = 0; s < 8760; s++) { const g = Math.floor(s / 24), h = s % 24, fer = (g + 3) % 7 < 5; cons[s] = fer && h >= 8 && h < 18 ? 50 : 10; }
const clima = E.climaSintetico(2025, 44.06, 12.57);
const p = F.produzionePerKwp(clima, 44.06, 12.57);
out.resa = Math.round(F.totale(p));
const d0 = F.dimensiona(cons, p, { qMin: 0.6 }), d2 = F.dimensiona(cons, p, { qMin: 0.6, h: 2 });
const piu = F.simula(cons, p, d0.P + 2), meno = F.simula(cons, p, d0.P);
out.dim = { P0: d0.P, q0: d0.quota, P2: d2.P, E2: d2.E, q2: d2.quota, piu: piu.quotaProduzione, meno: meno.quotaProduzione, n0: d0.nImpianti };
const grande = new Float64Array(8760).fill(900);
const dg = F.dimensiona(grande, p, { qMin: 0.5 });
out.grande = { P: dg.P, n: dg.nImpianti, kw: dg.impianti.map((x) => Math.round(x.kw)), max: Math.max(...dg.impianti.map((x) => x.kw)) };
const lim = F.dimensiona(grande, p, { qMin: 0.5, potenzaMassima: 300 });
out.limite = [lim.P, lim.motivo];
const agri = F.dimensiona(cons, p, { qMin: 0.6, tipo: "agrivoltaico" });
out.agri = [agri.impianti[0].haSau / agri.impianti[0].ha];
// terreni: classe A sopra il 50 %, esclusi i piccoli e i lontani, punti più alti per il più vicino
const f = F.fabbisognoTerreni(d0, { distanzaKm: 5, tipo: "fisso", tolleranza: 1.3 });
const t = (a, d, pc) => F.punteggioTerreno({ area_m2: a, distanza_m: d, prob_coltura: pc, n_enti: 1 }, f);
out.terreni = { vicino: t(f.haMin * 10000 * 1.1, 500, 10), lontano: t(f.haMin * 10000 * 1.1, 4000, 10), piccolo: t(f.haMin * 10000 * 0.5, 500, 10),
  oltre: t(f.haMin * 10000 * 1.1, 6000, 10), dop: t(f.haMin * 10000 * 1.1, 500, 80), ignoto: t(f.haMin * 10000 * 1.1, 500, null) };
console.log(JSON.stringify(out));
"""


@pytest.mark.skipif(not NODE, reason="Node non disponibile")
def test_calcolo_con_node():
    r = subprocess.run([NODE, "-e", PROVA_NODE, str(SITO)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    o = json.loads(r.stdout)
    assert o["slotLuglio"] and o["slotGennaio"] and o["bisestile"] == -1
    assert o["formati"] == ["lungo", "largo", "giorno"] and o["passi"] == [15, 60, 60]
    assert o["totali"] == [8760, 8760, 21900, 8760] and o["copertura"] == 1
    assert o["buchi"][0] == 90 and o["buchi"][1] == 8760
    assert 1000 < o["resa"] < 1600
    d = o["dim"]
    assert d["q0"] >= 0.6 and d["meno"] >= 0.6 > d["piu"]            # la più alta che rispetta la quota
    assert d["P2"] > d["P0"] and d["E2"] == 2 * d["P2"] and d["q2"] >= 0.6 and d["n0"] == 1
    g = o["grande"]
    assert g["n"] == -(-g["P"] // 1000) and g["max"] <= 1000 and len(set(g["kw"])) == 1
    assert o["limite"] == [300, "potenza massima indicata"]
    assert o["agri"][0] == pytest.approx(0.3)
    t = o["terreni"]
    assert t["vicino"]["ammesso"] and t["vicino"]["classe"] == "C" and t["vicino"]["punti"] > t["lontano"]["punti"] > 0
    assert not t["piccolo"]["ammesso"] and "sotto" in t["piccolo"]["motivi"][0] and "," in t["piccolo"]["motivi"][0]
    assert not t["oltre"]["ammesso"]
    assert t["dop"]["classe"] == "A" and not t["dop"]["ammesso"] and "agrivoltaico" in t["dop"]["motivi"][0]
    assert t["ignoto"]["ammesso"] and t["ignoto"]["punti"] < t["vicino"]["punti"]


# ---------------------------------------------------------------------------------------------- Chromium
class Silenzioso(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def base():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Silenzioso, directory=str(SITO)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/"
    srv.shutdown()


@pytest.fixture(scope="module")
def browser():
    pw = pytest.importorskip("playwright.sync_api")
    with pw.sync_playwright() as p:
        try:
            b = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"Chromium non disponibile: {e}")
        yield b
        b.close()


def test_pagina_in_prova(browser, base):
    ctx = browser.new_context(viewport={"width": 1366, "height": 900})
    pg = ctx.new_page()
    errori = []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    pg.goto(base + "fv-cer.html?prova=1")
    pg.wait_for_function("window.EUGENIO_CER_FV_PAGINA && window.EUGENIO_CER_FV_PAGINA.st.pronto", timeout=20000)
    assert pg.eval_on_selector("#calcola", "b => b.disabled")
    assert pg.evaluate("window.EUGENIO_CER_FV_PAGINA.datiFile()").startswith("Niente da scaricare")
    pg.click("#esempio")
    pg.wait_for_function("!document.querySelector('#calcola').disabled", timeout=60000)
    assert "5 edifici, 5 con la curva di carico" in pg.inner_text("#messaggio-edifici")
    pg.fill("#p-h", "2")
    pg.click("#calcola")
    pg.wait_for_function("!document.querySelector('#cerca-terreni').disabled", timeout=120000)
    assert "SINTETICO" in pg.inner_text("#messaggio-calcolo")
    cab = pg.evaluate("window.EUGENIO_CER_FV_PAGINA.st.cabine.map(c => ({ ac: c.cod_ac, P: c.ris.P, E: c.ris.E, q: c.ris.quota, n: c.ris.nImpianti }))")
    assert cab and all(c["P"] > 0 and c["E"] == 2 * c["P"] and c["q"] >= 0.6 for c in cab)
    pg.click("#cerca-terreni")
    pg.wait_for_function("/adatti/.test(document.querySelector('#messaggio-terreni').textContent)", timeout=60000)
    testo = pg.inner_text("#elenco-terreni")
    assert "Coltura DOP o certificata" in testo and "stessa area" in testo
    bando = pg.inner_text("#elenco-bando")
    assert "Terreni da cercare" in bando and not pg.eval_on_selector("#avviso-pdf", "b => b.disabled")
    d = pg.evaluate("(() => { const d = window.EUGENIO_CER_FV_PAGINA.datiFile(); return { sez: d.csv[1].map(s => [s.titolo, s.righe.length, s.intestazioni]), piede: d.csv[2], doc: d.doc.titolo }; })()")
    titoli = [s[0] for s in d["sez"]]
    assert titoli == ["Parametri", "Edifici", "Potenza per cabina primaria", "A – Terreni pubblici", "B – Cabine per la manifestazione di interesse"]
    assert all(n > 0 for _, n, _ in d["sez"])
    terreni = next(s for s in d["sez"] if s[0].startswith("A"))
    assert "Probabilità di coltura DOP o certificata (%)" in terreni[2]
    assert not any(re.search(r"(?i)desc_colt|flag|codice fiscale", x) for x in terreni[2])
    piede = " ".join(d["piede"])
    assert "DATI SINTETICI" in piede and "non ceduti" in piede and "solo i codici" in piede
    # immagine della mappa: aree del GSE spente e riaccese dopo
    acc = pg.evaluate("""(() => { const P = window.EUGENIO_CER_FV_PAGINA, m = P.st.det, o = P.opzioniImmagine(m);
      const spenta = m.getLayoutProperty('cer-aree-linea', 'visibility'); o.dopo(); return [spenta, m.getLayoutProperty('cer-aree-linea', 'visibility')]; })()""")
    assert acc[0] == "none" and acc[1] == "visible"
    assert not errori, errori
    ctx.close()
