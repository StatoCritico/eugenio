"""Trattamento aria (14/11/2026): menu, pagine, moduli comuni (senza browser).

- il gruppo «Trattamento aria» sta tra Edifici e Cogenerazione (tendina, menu del telefono), con il sottotitolo non
  cliccabile «Psicrometria» e 4 voci sperimentali («S» nella tendina, «sperimentale» nel telefono);
- le 4 pagine si costruiscono: etichetta del gruppo, «Nello stesso gruppo», due colonne (mappa e diagramma a sinistra,
  passi a destra), script dei moduli nell'ordine giusto, foglio Excel scaricabile;
- psicro.js e gruppi_ore.js in node: stato, sequenza di riferimento, livelli di progetto (99 % / 1 % predefiniti),
  ora legale (la parità completa con il Python è in fase14-trattamento-aria/tests/test_parita_js.py).
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

QUI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(QUI))
import costruisci_pagine as C  # noqa: E402

PAGINE = ["aria-trasformazioni.html", "aria-ore.html", "aria-latenti.html", "aria-freecooling.html"]
NOMI = ["Trasformazioni (UTA)", "Ore di funzionamento", "Carichi latenti", "Free cooling e recupero"]


@pytest.fixture()
def sito(tmp_path):
    d = tmp_path / "sito"
    d.mkdir()
    for f in list((QUI / "sito").glob("*.html")) + list((QUI / "sito").glob("*.js")):
        shutil.copy(f, d)
    return d


def test_menu_gruppo_trattamento_aria():
    t = (C.PARTI / "testata.html").read_text(encoding="utf-8")
    gruppi = C.gruppi_menu(t)
    assert [g["id"] for g in gruppi] == ["clima", "patrimonio", "edificio", "aria", "cogenerazione", "fotovoltaico", "statistiche"]
    aria = next(g for g in gruppi if g["id"] == "aria")
    assert aria["titolo"] == "Trattamento aria"
    assert [(v["pagina"], v["nome"], v["tipo"]) for v in aria["voci"]] == [(p, n, "") for p, n in zip(PAGINE, NOMI)]
    tendina = re.search(r'data-gruppo="aria"><summary>Trattamento aria</summary>\s*<ul class="tendina">(.*?)</ul>', t, re.S).group(1)
    assert tendina.strip().startswith('<li class="voce-sottotitolo">Psicrometria</li>')
    assert tendina.count('<span class="cantiere prova breve" title="sperimentale">') == 4
    tel = re.search(r'<details class="pannello-gruppo" data-gruppo="aria"><summary>Trattamento aria</summary>(.*?)</details>', t, re.S).group(1)
    assert '<li class="voce-sottotitolo">Psicrometria</li>' in tel and tel.count(">sperimentale<") == 4
    assert all(f'href="{p}"' in tel for p in PAGINE)
    # dopo Edifici e prima di Cogenerazione, sia nella tendina sia nel telefono
    for cls in ("voce-gruppo", "pannello-gruppo"):
        pos = [t.index(f'<details class="{cls}" data-gruppo="{g}"') for g in ("edificio", "aria", "cogenerazione")]
        assert pos == sorted(pos), cls
    assert "clima|patrimonio|edificio|aria|cogenerazione|fotovoltaico|statistiche" in (C.PARTI / "testa.html").read_text(encoding="utf-8")
    css = (QUI / "sito" / "stile.css").read_text(encoding="utf-8")
    assert ".tendina .voce-sottotitolo" in css and ".riga-voci > .voce-sottotitolo" in css


def test_pagine_costruite(sito):
    assert C.main(["--sito", str(sito)]) == 0
    for p, nome in zip(PAGINE, NOMI):
        s = (sito / p).read_text(encoding="utf-8")
        assert '<main class="strumento pagina-aria"' in s and '<p class="gruppo-servizio">Trattamento aria</p>' in s, p
        assert s.count("<!-- in-lavorazione -->") == 0 and "Pagina in lavorazione" not in s, p
        assert re.search(r'<details class="voce-gruppo" data-gruppo="aria" data-attivo>', s) and s.count("data-attivo") == 2, p
        assert len(re.findall(rf'<a href="{p}" aria-current="page">', s)) == 3, p     # tendina, telefono, «Nello stesso gruppo»
        blocco = re.search(r'<ul class="stesso-gruppo">(.*?)</ul>', s, re.S).group(1)
        assert re.findall(r'href="([^"]+)"', blocco) == PAGINE, p
        sinistra = re.search(r'<section class="mappa-area".*?</section>', s, re.S).group(0)
        assert 'id="mappa"' in sinistra and sinistra.index('id="mappa"') < sinistra.index('id="diagramma-aria"'), p
        destra = re.search(r'<section class="pannello".*?</section>', s, re.S).group(0)
        assert 'id="scelta-aria"' in destra and '<span class="n">1</span>Comune e serie meteo' in destra, p
        script = re.findall(r'<script src="([\w.]+)\?v=\d{8}[a-z]?"></script>', s)
        # collegamento.js (20/11/2026) subito dopo aspetto.js, prima degli script che si registrano
        ordine = ["protezione.js", "numeri.js", "aspetto.js", "collegamento.js", "grafici.js", "divisore.js", "minimappa.js", "esporta_mappa.js", "psicro.js", "diagramma_aria.js", "scelta_aria.js"]
        assert script[:len(ordine)] == ordine and script[-1] == p.replace("-", "_").replace(".html", ".js"), (p, script)
        assert ("gruppi_ore.js" in script) == (p != "aria-trasformazioni.html"), p
        assert "Open-Meteo.com" in s and "psychrolib" in s and "non valori di norma" in s, p
    s = (sito / "aria-trasformazioni.html").read_text(encoding="utf-8")
    assert 'href="strumenti/psicro_UTA.xlsx" download' in s and 'id="aria-livello"' in s
    assert (QUI / "sito" / "strumenti" / "psicro_UTA.xlsx").stat().st_size > 50_000


def test_nessun_dato_vietato_nelle_pagine_aria():
    for f in PAGINE + ["psicro.js", "diagramma_aria.js", "scelta_aria.js", "gruppi_ore.js"]:
        s = (QUI / "sito" / f).read_text(encoding="utf-8")
        if f.endswith(".html"):                          # il menu comune ha le etichette «licenza GME»: solo il contenuto
            s = s[s.index("<!-- /testata -->"):s.index("<!-- piede -->")]
        for vietato in ("PUN", "PSV", "TTF", "GME", "EEX", "Arpae"):
            assert not re.search(rf"\b{vietato}\b", s), (f, vietato)


def _node(prova):
    node = shutil.which("node")
    if not node:
        pytest.skip("node non installato")
    return json.loads(subprocess.run([node, "-e", prova, str(QUI / "sito")], capture_output=True, text=True, encoding="utf-8", check=True).stdout)


def test_psicro_e_gruppi_con_node():
    d = _node(r'''
const S = process.argv[1], P = require(S + "/psicro.js"), G = require(S + "/gruppi_ore.js");
const s = P.stato(26, { ur: 50 }, 101325);
const q = P.sequenza({ p: 101325, V: 5000, stagione: "estate", esterno: { t: 32, ur: 50 }, ambiente: { t: 26, ur: 50 }, Qs: 5000, Ql: 1500 });
const n = 3 * 8766, t = new Float32Array(n), u = new Float32Array(n);
for (let i = 0; i < n; i++) { t[i] = 13 + 10 * Math.sin(i / 8766 * 6.2832 - 1.6) + 4 * Math.sin(i / 24 * 6.2832); u[i] = 70 - 15 * Math.sin(i / 24 * 6.2832); }
const c = P.condizioniProgetto(t, u, 101325), c4 = P.condizioniProgetto(t, u, 101325, { inverno: 99.6, estate: 0.4 });
const serie = { inizio: "2026-03-29T00:00Z", n: 6, t: new Float32Array(6), ur: new Float32Array(6) };
const campi = G.campiOrari(serie);
console.log(JSON.stringify({ x: s.xg, h: s.h, twb: s.twb, frigo: q.riepilogo.frigoTotale, ragg: q.raggiungibileTesto, note: q.righe.map((r) => r.nota),
  L: c.livelli, L4: c4.livelli, wi: [c.inverno.t, c4.inverno.t], es: [c.estate.t, c4.estate.t], scelte: P.SCELTE_LIVELLO,
  ore: Array.from(campi.ora), nomi: P.nomiProgetto().estate, Y: P.mollierY(20, 0.01) }));
''')
    assert d["x"] == pytest.approx(10.4963, abs=1e-3) and d["h"] == pytest.approx(52.912, abs=2e-3) and d["twb"] == pytest.approx(18.71, abs=0.01)
    assert d["frigo"] == pytest.approx(46.383, abs=0.01) and d["ragg"] == "SÌ"
    assert d["note"][1] == "ADP = 13,4 °C; SHR = 0,59; BF = 0,10. " and d["note"][3] == "OK"
    assert d["L"] == {"inverno": 99, "estate": 1} and d["L4"] == {"inverno": 99.6, "estate": 0.4}
    assert d["scelte"] == {"inverno": [99.6, 99, 95], "estate": [0.4, 1, 5]}
    assert d["wi"][1] < d["wi"][0] and d["es"][1] > d["es"][0]
    assert d["ore"] == [1, 3, 4, 5, 6, 7]                       # 29/03/2026: alle 01 UTC le 02 diventano 03
    assert d["nomi"].startswith("Estate 1 %: temperatura superata solo nell'1 % delle ore")
    assert d["Y"] == pytest.approx(20 * (1 + 1.86 * 0.01 / 1.006))
