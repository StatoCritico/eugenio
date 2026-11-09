"""File per gli agenti AI nel sito (06/11/2026): EUGENIO_PER_AGENTI.md e llms.txt ci sono, la F.A.Q. ha la voce
#agenti-ai con il collegamento che scarica il file, la Sitografia ha la frase sotto Claude con il collegamento su
«questo file». In Chromium headless: l'ancora apre la voce della F.A.Q. e i due collegamenti scaricano il file intero.
Le prove nel browser si saltano se Playwright o Chromium non ci sono. Il confronto con le rotte dell'API e con la copia
nella radice del repository è in fase4-server/tests/test_agenti.py."""
from __future__ import annotations

import functools
import re
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

SITO = Path(__file__).resolve().parents[1] / "sito"
RADICE = SITO.parents[1]
NOME = "EUGENIO_PER_AGENTI.md"
FRASE = ("E lo puoi usare anche tu: per fargli imparare cosa può fare EuGEnio, scarica e fagli leggere "
         f'<a href="{NOME}" download="{NOME}">questo file</a>.')


def _testo(nome: str) -> str:
    return re.sub(r"\s+", " ", (SITO / nome).read_text(encoding="utf-8"))


def test_file_nel_sito():
    md = SITO / NOME
    assert md.exists() and (SITO / "llms.txt").exists()
    if (RADICE / NOME).exists():                       # nel repository completo (non nel solo pacchetto del sito)
        assert md.read_bytes() == (RADICE / NOME).read_bytes()
    assert md.read_text(encoding="utf-8").startswith("# EuGEnio per agenti AI")


def test_faq_voce_agenti():
    t = _testo("faq.html")
    m = re.search(r'<details id="agenti-ai">(.*?)</details>', t)
    assert m, "manca la voce #agenti-ai nella F.A.Q."
    assert f'href="{NOME}" download="{NOME}"' in m.group(1)
    assert 'href="llms.txt"' in m.group(1)


def test_sitografia_frase_claude():
    t = _testo("sitografia.html")
    m = re.search(r'<li class="ultimo" id="claude">(.*?)</li>', t)
    assert m and "non è open source" in m.group(1)
    assert FRASE in m.group(1), "manca la frase sull'uso del file per gli agenti nel paragrafo di Claude"


# ---------------------------------------------------------------------------------------------- Chromium
class Silenzioso(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".md": "text/markdown; charset=utf-8"}

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
    pw = pytest.importorskip("playwright.sync_api")     # senza Playwright si saltano solo le prove nel browser
    with pw.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"Chromium non disponibile: {e}")
        yield b
        b.close()


def _scarica(pg, selettore, tmp_path):
    with pg.expect_download() as d:
        pg.click(selettore)
    dl = d.value
    assert dl.suggested_filename == NOME
    dest = tmp_path / dl.suggested_filename
    dl.save_as(dest)
    assert dest.read_bytes() == (SITO / NOME).read_bytes()


@pytest.mark.parametrize("larghezza", [1366, 375])
def test_faq_e_sitografia_nel_browser(base, browser, tmp_path, larghezza):
    ctx = browser.new_context(viewport={"width": larghezza, "height": 800}, accept_downloads=True)
    pg = ctx.new_page()
    errori = []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    pg.route("**/api/**", lambda r: r.fulfill(status=404, body="{}"))
    pg.goto(base + "faq.html#agenti-ai")
    pg.wait_for_timeout(300)
    assert pg.evaluate("document.getElementById('agenti-ai').open"), "l'ancora #agenti-ai non apre la voce"
    link = f"#agenti-ai a[href='{NOME}']"
    assert pg.locator(link).is_visible()
    _scarica(pg, link, tmp_path)
    assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    pg.goto(base + "sitografia.html#claude")
    pg.wait_for_timeout(300)
    link = f"#claude a[href='{NOME}']"
    assert pg.locator(link).inner_text() == "questo file"
    _scarica(pg, link, tmp_path)
    r = pg.request.get(base + NOME)
    assert r.ok and r.headers["content-type"].startswith("text/markdown")
    assert not errori, errori
    ctx.close()


def test_spostamento_ortofoto_documentato():
    """08/11/2026: parametri de/dn delle tessere delle ortofoto (frecce sotto la mappa) in llms.txt e nel file per agenti."""
    md, llms = _testo(NOME), _testo("llms.txt")
    assert "?de=<m>&dn=<m>" in md and "`spostabile`" in md and "X-Ortofoto-Spostamento" in md
    assert "?de=<m>&dn=<m>" in llms and "±20" in llms


def test_tetti_e_sagome_regionali_documentati():
    """08/11/2026: sagome del Veneto con le altezze OSM, terreno da più DTM; dal 09/11/2026 c tetti tutti piani e tetti a
    falde scelti dall'utente in «Coperture» (l'ipotesi 22°/32° è sospesa), fonte dell'ortofoto automatica."""
    md, llms = _testo(NOME), _testo("llms.txt")
    assert "«Coperture»" in md and "«Forma dei tetti»" in md and "eugenio-tetti-v1" in md and "Tetti: N a falde scelti" in md
    assert "**sospese**" in md and "X-Ortofoto-Errore" in md
    assert "IODL 2.0" in md and "osm_vicini" in md and "X-Terreno-Nome" in md and "Edifici del Veneto (feb. 2022)" in md
    assert "Veneto" in llms and "Coperture" in llms and "Forma dei tetti" in llms and "X-Ortofoto-Errore" in llms
