"""Statistiche › «Produzione e consumi di elettricità» (elettricita.html, elettricita.js; 20/11/2026, richiesta di Paolo).

Sui file: voce del menu (sperimentale), fonti, nessun collegamento per scaricare i dati di Terna (decisione di Paolo:
si scarica solo l'immagine della mappa), nessun dato di mercato.
In Chromium (si salta se Playwright o Chromium non ci sono), con i file della pagina costruiti da dati inventati
(fase 15, costruisci) e serviti al posto di dati/elettricita/: istogrammi nella mappa, clic sulla regione → province,
secondo clic → Italia, cambio di grandezza e di anno, burden sharing con gli obiettivi, niente scorrimento orizzontale a
375 px, nessun errore JavaScript.
Emissioni (21/11/2026): selettore, anelli nella mappa, tre riquadri con i riferimenti MEF e ISPRA, righe delle zone di
mercato e totale Italia nella tabella, collegamento salvabile con la scelta.
"""
from __future__ import annotations

import functools
import re
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

QUI = Path(__file__).resolve().parents[1]
SITO = QUI / "sito"
sys.path.insert(0, str(QUI))
sys.path.insert(0, str(QUI.parent / "fase15-elettricita"))
sys.path.insert(0, str(QUI.parent / "fase15-elettricita" / "tests"))
import costruisci_pagine as C  # noqa: E402


def test_menu_e_pagina():
    t = (C.PARTI / "testata.html").read_text(encoding="utf-8")
    assert t.count('href="elettricita.html"') == 2
    assert re.search(r'href="elettricita.html">Produzione e consumi di elettricità <span class="cantiere prova">sperimentale', t)
    s = (SITO / "elettricita.html").read_text(encoding="utf-8")
    assert '<p class="gruppo-servizio">Statistiche</p>' in s and "Servizio sperimentale non ancora verificato" in s
    assert s.count('aria-current="page"') == 2 and "dati.terna.it" in s and "21 giugno 2024" in s
    assert re.search(r'<script src="rete\.js\?v=\d{8}[a-z]"></script>\s*<script src="cursore_periodo\.js\?v=\d{8}[a-z]"></script>\s*<script src="elettricita\.js\?v=', s)
    assert 'id="anno-inizio"' in s and 'id="anno-fine"' in s and 'aria-label="Anno finale del periodo"' in s
    js = (SITO / "elettricita.js").read_text(encoding="utf-8")
    for vietato in ("PUN", "TTF", "€/MWh", "pulsantiDati", ".csv", "xlsx"):
        assert vietato not in s + js, vietato
    assert "#elettricita" in s and 'id="elettricita"' in (SITO / "metodo.html").read_text(encoding="utf-8")


class _Zitto(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def base():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Zitto, directory=str(SITO)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


@pytest.fixture(scope="module")
def dati(tmp_path_factory):
    from elettricita import costruisci as K
    T = _prove_costruisci_elettricita()
    tmp = tmp_path_factory.mktemp("el")
    K.costruisci(T._raw(tmp), tmp / "out", SITO / "dati" / "mappa")
    return tmp / "out"


@pytest.fixture(scope="module")
def browser():
    pw = pytest.importorskip("playwright.sync_api")
    with pw.sync_playwright() as p:
        try:
            b = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
        except Exception as e:  # pragma: no cover
            pytest.skip(f"Chromium non disponibile: {e}")
        yield b
        b.close()


def _pagina(browser, base, dati, larghezza=1400, altezza=950, query="vista=italia"):
    pg = browser.new_page(viewport={"width": larghezza, "height": altezza})
    errori = []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    pg.route("**/api/**", lambda r: r.fulfill(status=404, body="no"))
    pg.route("**/dati/elettricita/**", lambda r: r.fulfill(path=str(dati / r.request.url.split("/dati/elettricita/")[1].split("?")[0])))
    pg.goto(f"{base}/elettricita.html?{query}")
    pg.wait_for_function("() => window.EUGENIO_ELETTRICITA && window.EUGENIO_ELETTRICITA.stato.mappa && window.EUGENIO_ELETTRICITA.stato.mappa.getSource('el-barre')", timeout=20000)
    pg.wait_for_timeout(1500)
    return pg, errori


def test_pagina(browser, base, dati):
    pg, errori = _pagina(browser, base, dati)
    n = pg.evaluate("() => window.EUGENIO_ELETTRICITA.stato.barre")
    assert n == 2                                               # Emilia-Romagna e Sardegna nei dati inventati
    assert pg.locator("#titolo-vista").inner_text() == "Italia"
    assert pg.locator("#tabella-elettricita tfoot th").inner_text() == "Italia"
    assert pg.locator("#scarica-mappa button, #scarica-mappa a").count() >= 1   # solo l'immagine
    # clic sulla regione (sotto la base del suo istogramma) → province; secondo clic → Italia
    p = pg.evaluate("""() => { const S = window.EUGENIO_ELETTRICITA.stato, m = S.mappa, r = S.it.regioni.find((x) => x.cod === '08');
      const q = m.project([r.lon, r.lat]), b = m.getCanvas().getBoundingClientRect(); return [q.x + b.x, q.y + b.y + 10]; }""")
    pg.mouse.click(*p)
    pg.wait_for_function("() => document.getElementById('titolo-vista').textContent === 'Emilia-Romagna'", timeout=10000)
    pg.wait_for_timeout(1500)
    assert "Totale Emilia-Romagna" in pg.locator("#tabella-elettricita tfoot").inner_text()
    assert "Forlì-Cesena" in pg.locator("#tabella-elettricita tbody").inner_text()
    assert pg.locator("#grafico-province svg[role=img]").count() == 1
    p = pg.evaluate("""() => { const S = window.EUGENIO_ELETTRICITA.stato, m = S.mappa, r = S.it.regioni.find((x) => x.cod === '08');
      const q = m.project([r.lon + 0.3, r.lat - 0.15]), b = m.getCanvas().getBoundingClientRect(); return [q.x + b.x, q.y + b.y]; }""")
    pg.mouse.click(*p)
    pg.wait_for_function("() => document.getElementById('titolo-vista').textContent === 'Italia'", timeout=10000)
    # carichi: per le province nessuna barra e la nota
    pg.evaluate("() => window.EUGENIO_ELETTRICITA.scegliRegione('08')")
    pg.click('[data-modo="richiesta"]')
    pg.wait_for_timeout(1500)
    assert pg.locator("#nota-province").is_visible() and "solo per regione" in pg.locator("#messaggio-mappa").inner_text()
    # burden sharing all'Italia: obiettivi della Tabella A
    pg.click("#torna-italia")
    pg.click('[data-modo="burden"]')
    pg.wait_for_timeout(1500)
    testo = pg.locator("#tabella-elettricita").inner_text()
    assert "Obiettivo 2030" in testo and "6.330" in testo and "6330" not in testo     # punto delle migliaia anche a 4 cifre
    assert pg.locator("#periodo-scelto").inner_text() == "2021"
    assert errori == []


def test_telefono(browser, base, dati):
    pg, errori = _pagina(browser, base, dati, 375, 800)
    assert pg.evaluate("document.documentElement.scrollWidth") <= 376
    assert errori == []


def test_emissioni(browser, base, dati):
    pg, errori = _pagina(browser, base, dati)
    assert pg.locator('[data-modo="emissioni"]').is_visible()
    pg.click('[data-modo="emissioni"]')
    pg.wait_for_timeout(1500)
    # anelli: due regioni con la produzione nei dati inventati (Emilia-Romagna, Sardegna)
    st = pg.evaluate("() => { const S = window.EUGENIO_ELETTRICITA.stato; return { n: S.barre, anelli: S.anelli, anno: S.anno }; }")
    assert st == {"n": 2, "anelli": 2, "anno": 2021}
    assert "l'area cresce in proporzione alla produzione" in pg.locator("#legenda-elettricita").inner_text()
    # tre riquadri con i valori nazionali e i riferimenti (MEF 0,187 tep/MWh; ISPRA 2021)
    rq = pg.locator("#riquadri-emissioni")
    assert rq.is_visible() and rq.locator(".cifra").count() == 3
    testo = rq.inner_text()
    assert "Valori nazionali – 2021" in testo and "0,187 tep/MWh" in testo and "ISPRA 2021" in testo and "430/2026" in testo
    # fattore medio Italia 2021: 630 kt / 2250 GWh = 0,280; termoelettrico 630 / 1400 = 0,450
    assert rq.locator('[data-cifra="medio"] b').inner_text().startswith("0,280")
    assert rq.locator('[data-cifra="termo"] b').inner_text().startswith("0,450")
    # tabella: regioni, 7 righe di zona di mercato, totale Italia
    tab = pg.locator("#tabella-elettricita")
    assert tab.locator("tr.riga-zona").count() == 7 and "Zona Nord" in tab.inner_text() and "Sardegna (regione e zona)" in tab.inner_text()
    assert tab.locator("tfoot th").inner_text() == "Italia" and "Fattore medio" in tab.locator("thead").inner_text()
    assert pg.locator("#grafico-andamento svg[role=img]").count() == 1
    # regione scelta: anelli per provincia, fattori regionali, tabella sempre per regione con la riga scelta
    pg.evaluate("() => window.EUGENIO_ELETTRICITA.scegliRegione('08')")
    pg.wait_for_function("() => document.getElementById('titolo-vista').textContent === 'Emilia-Romagna'", timeout=10000)
    pg.wait_for_timeout(1500)
    assert pg.evaluate("() => window.EUGENIO_ELETTRICITA.stato.barre") >= 1
    assert "Emilia-Romagna:" in rq.inner_text() and tab.locator("tr.scelta").count() == 1
    assert "solo per regione" in pg.locator("#legenda-elettricita").inner_text()
    # collegamento: la scelta «emissioni» e il periodo vanno nell'indirizzo e si ripristinano (indicatore finale sul primo
    # anno: spinge con sé l'iniziale, periodo 2020–2020)
    pg.eval_on_selector("#anno-fine", "c => { c.value = 0; c.dispatchEvent(new Event('input', {bubbles: true})); c.dispatchEvent(new Event('change', {bubbles: true})); }")
    pg.wait_for_timeout(900)
    link = pg.url
    assert "modo=emissioni" in link and "inizio=2020" in link and "fine=2020" in link and "regione=08" in link
    assert errori == []
    pg2, errori2 = _pagina(browser, base, dati, query=link.split("?", 1)[1])
    pg2.wait_for_function("() => window.EUGENIO_ELETTRICITA.stato.pronto", timeout=20000)
    pg2.wait_for_timeout(1000)
    assert pg2.get_attribute('[data-modo="emissioni"]', "aria-pressed") == "true"
    assert pg2.inner_text("#periodo-scelto") == "2020" and "Valori nazionali – 2020" in pg2.locator("#riquadri-emissioni").inner_text()
    assert errori2 == []


def test_emissioni_telefono(browser, base, dati):
    pg, errori = _pagina(browser, base, dati, 375, 800, query="vista=italia&modo=emissioni")
    assert pg.evaluate("document.documentElement.scrollWidth") <= 376
    assert pg.locator("#riquadri-emissioni .cifra").count() == 3
    assert errori == []


def _immagine(pg, id_):
    """Misura sulla mappa (px CSS) dell'immagine di un istogramma o di un anello."""
    return pg.evaluate(f"""() => {{ const i = window.EUGENIO_ELETTRICITA.stato.mappa.getImage('{id_}');
      return i ? [i.data.width / i.pixelRatio, i.data.height / i.pixelRatio] : null; }}""")


def test_istogrammi_ingranditi(browser, base, dati):
    """(21/11/2026, Paolo) istogrammi e colonne del burden sharing più grandi: il doppio, poi (22/11/2026, 00:59) ridotti
    del 30 % → 1,4 volte le misure di prima; (22/11/2026) anelli delle emissioni più piccoli, che non si sovrappongono né
    fra le regioni né fra le province (la loro misura non cambia con gli istogrammi)."""
    pg, errori = _pagina(browser, base, dati)
    assert pg.evaluate("() => window.EUGENIO_ELETTRICITA.INGRANDISCI") == 1.4
    n = pg.evaluate("() => window.EUGENIO_ELETTRICITA.stato.it.voci.capacita.length")
    w, h = _immagine(pg, "el-08")
    assert abs(w - 1.4 * (n * 7 + 3)) <= 1 and abs(h - 1.4 * 72) <= 1   # prima: barre larghe 6 px, alte 70 px
    pg.click('[data-modo="burden"]'); pg.wait_for_timeout(1200)
    w, h = _immagine(pg, "el-08")
    assert abs(w - 1.4 * 24) <= 1 and abs(h - 1.4 * 74) <= 1            # colonna verticale: 24 × 74 unità, × 1,4
    pg.click('[data-modo="emissioni"]'); pg.wait_for_timeout(1200)
    assert _immagine(pg, "el-08")[0] <= 2 * 21 + 8                       # raggio al più 21 px
    assert _sovrapposti(pg) == []
    pg.evaluate("() => window.EUGENIO_ELETTRICITA.scegliRegione('08')")
    pg.wait_for_function("() => document.getElementById('titolo-vista').textContent === 'Emilia-Romagna'", timeout=10000)
    pg.wait_for_timeout(1500)
    assert len(pg.evaluate("() => window.EUGENIO_ELETTRICITA.cerchi()")) >= 1 and _sovrapposti(pg) == []
    assert errori == []


def _sovrapposti(pg):
    return pg.evaluate("""() => { const c = window.EUGENIO_ELETTRICITA.cerchi(), out = [];
      for (let i = 0; i < c.length; i++) for (let j = i + 1; j < c.length; j++)
        if (Math.hypot(c[i].x - c[j].x, c[i].y - c[j].y) < c[i].r + c[j].r) out.push(c[i].nome + '/' + c[j].nome);
      return out; }""")


def test_burden_suggerimento_obiettivo(browser, base, dati):
    """(21/11/2026, Paolo) burden sharing verticale: col mouse sulla parte vuota del rettangolo arancione dell'obiettivo
    2030 (sopra la potenza già installata) compaiono obiettivo 2030 della regione, percentuale raggiunta e MW che mancano; gli stessi valori nel
    grafico a destra (anche sul riquadro dell'anno scelto) e nella tabella."""
    pg, errori = _pagina(browser, base, dati, query="vista=italia&modo=burden")
    # punto al 90 % dell'altezza del rettangolo dell'obiettivo 2030 dell'Emilia-Romagna, sopra la potenza installata
    # (scala: obiettivo 2030 più grande fra le regioni = 70 unità, × 1,4 = 98 px; base 2,8 px sopra il punto della regione)
    xy = pg.evaluate("""() => { const S = window.EUGENIO_ELETTRICITA.stato, m = S.mappa, r = S.it.regioni.find((x) => x.cod === '08');
      const mx = Math.max(...S.it.regioni.filter((x) => x.obiettivi).map((x) => x.obiettivi[x.obiettivi.length - 1]));
      const q = m.project([r.lon, r.lat]), b = m.getCanvas().getBoundingClientRect();
      return [q.x + b.x, q.y + b.y - 2.8 - 0.9 * 98 * 6330 / mx]; }""")
    tocca = pg.evaluate("""([x, y]) => { const m = window.EUGENIO_ELETTRICITA.stato.mappa, b = m.getCanvas().getBoundingClientRect();
      return m.queryRenderedFeatures([x - b.x, y - b.y], { layers: ['el-barre'] }).map((f) => f.properties.cod); }""", xy)
    assert tocca == ["08"]
    # (22/11/2026) prima del mouse nessun rettangolo dell'obiettivo; sulla regione compare solo il suo
    assert pg.evaluate("() => window.EUGENIO_ELETTRICITA.stato.obiettivoSu") is None
    pg.mouse.move(*xy)
    pg.wait_for_timeout(500)
    assert pg.evaluate("() => window.EUGENIO_ELETTRICITA.stato.obiettivoSu") == "08"
    assert pg.evaluate("""() => { const m = window.EUGENIO_ELETTRICITA.stato.mappa; return m.getFilter('el-obiettivi'); }""") == ["==", ["get", "cod"], "08"]
    assert _immagine(pg, "el-08-ob") == _immagine(pg, "el-08")          # stessa misura: la colonna non si sposta
    et = pg.locator("#mappa-elettricita .etichetta-mappa:not(.righello-etichetta)")
    assert et.is_visible()
    testo = et.inner_text()
    righe = testo.split("\n")
    assert righe[0] == "Emilia-Romagna – 2021" and righe[1] == "Obiettivo 2030: 6.330 MW", righe
    assert re.match(r"Raggiunto: \d+ % \([\d.]+ MW in più dal 2020\)$", righe[2]) and re.match(r"Mancano: [\d.]+ MW$", righe[3]), righe
    # mouse fuori dalla mappa: il rettangolo sparisce
    pg.mouse.move(5, 5); pg.wait_for_timeout(300)
    assert pg.evaluate("() => window.EUGENIO_ELETTRICITA.stato.obiettivoSu") is None
    # grafico a destra: riquadro dell'anno scelto, in alto (sopra le barre)
    svg = pg.locator("#grafico-andamento svg[role=img]")
    svg.scroll_into_view_if_needed()
    r = pg.evaluate("""() => { const t = [...document.querySelectorAll('#grafico-andamento svg[role=img] rect')].find((x) => x.style.stroke);
      const b = t.getBoundingClientRect(); return [b.x + b.width / 2, b.y + 12]; }""")
    pg.mouse.move(*r)
    pg.wait_for_timeout(300)
    s = pg.locator(".grafico-suggerimento").first
    assert s.is_visible() and s.inner_text().startswith("2021") and "Obiettivo 2030: 80.002 MW" in s.inner_text()
    assert "Obiettivo 2030: " in s.inner_text() and "Mancano: " in s.inner_text() and "Raggiunto: " in s.inner_text()
    # tabella: colonna dei MW che mancano al 2030
    assert "obiettivo 2030" in pg.locator("#legenda-elettricita").inner_text() and "valori negativi" in pg.locator("#legenda-elettricita").inner_text()
    assert "Mancano al 2030 (MW)" in pg.locator("#tabella-elettricita thead").inner_text()
    # provincia: valori della sua regione
    pg.evaluate("() => window.EUGENIO_ELETTRICITA.scegliRegione('08')")
    pg.wait_for_function("() => document.getElementById('titolo-vista').textContent === 'Emilia-Romagna'", timeout=10000)
    pg.wait_for_timeout(1500)
    assert pg.evaluate("() => window.EUGENIO_ELETTRICITA.stato.barre") >= 1
    assert errori == []


def test_burden_tocco(browser, base, dati):
    """(22/11/2026) col dito: il primo tocco su una regione mostra il suo obiettivo, il secondo apre le province."""
    ctx = browser.new_context(viewport={"width": 1400, "height": 950}, has_touch=True)
    pg = ctx.new_page()
    errori = []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    pg.route("**/api/**", lambda r: r.fulfill(status=404, body="no"))
    pg.route("**/dati/elettricita/**", lambda r: r.fulfill(path=str(dati / r.request.url.split("/dati/elettricita/")[1].split("?")[0])))
    pg.goto(f"{base}/elettricita.html?vista=italia&modo=burden")
    pg.wait_for_function("() => window.EUGENIO_ELETTRICITA && window.EUGENIO_ELETTRICITA.stato.pronto", timeout=20000)
    pg.wait_for_timeout(1500)
    xy = pg.evaluate("""() => { const S = window.EUGENIO_ELETTRICITA.stato, m = S.mappa, r = S.it.regioni.find((x) => x.cod === '08');
      const q = m.project([r.lon + 0.3, r.lat - 0.2]), b = m.getCanvas().getBoundingClientRect(); return [q.x + b.x, q.y + b.y]; }""")
    pg.touchscreen.tap(*xy)
    pg.wait_for_timeout(600)
    assert pg.evaluate("() => window.EUGENIO_ELETTRICITA.stato.obiettivoSu") == "08"
    assert pg.locator("#titolo-vista").inner_text() == "Italia"
    pg.touchscreen.tap(*xy)
    pg.wait_for_function("() => document.getElementById('titolo-vista').textContent === 'Emilia-Romagna'", timeout=10000)
    assert errori == []
    ctx.close()


def test_periodo(browser, base, dati):
    """(22/11/2026, Paolo) periodo a due indicatori (componente comune cursore_periodo.js, come in Suolo e aree agricole):
    all'apertura tutti e due sull'ultimo anno; flussi sommati sul periodo, fattori come rapporto delle somme; stati
    all'anno finale con la variazione dall'iniziale (riquadretto, tabella, trattino); anni del periodo evidenziati nel
    grafico a destra; tastiera; collegamento con inizio e fine."""
    pg, errori = _pagina(browser, base, dati)
    S = "window.EUGENIO_ELETTRICITA.stato"
    anni = pg.evaluate(f"() => {S}.it.anni.capacita")
    primo, ultimo = anni[0], anni[-1]
    assert primo < ultimo
    assert pg.evaluate(f"() => [{S}.inizio, {S}.fine, {S}.anno]") == [ultimo, ultimo, ultimo]
    assert pg.inner_text("#periodo-scelto") == str(ultimo)
    assert "Variazione" not in pg.locator("#tabella-elettricita thead").inner_text()
    # tastiera: Inizio sull'indicatore iniziale → periodo dal primo all'ultimo anno
    pg.focus("#anno-inizio")
    pg.keyboard.press("Home")
    pg.wait_for_timeout(1200)
    assert pg.evaluate(f"() => [{S}.inizio, {S}.fine]") == [primo, ultimo]
    assert pg.inner_text("#periodo-scelto") == f"{primo}–{ultimo}"
    assert pg.get_attribute("#anno-inizio", "aria-valuetext") == str(primo)
    # capacità (stato): valori dell'anno finale, variazione dal primo anno nella tabella, trattino nella legenda
    testa = pg.locator("#tabella-elettricita thead").inner_text()
    assert f"Variazione del totale dal {primo}" in testa
    assert pg.locator("#tabella-elettricita small.variazione").count() >= 1
    assert f"trattino: valore del {primo}" in pg.locator("#legenda-elettricita").inner_text()
    tot = pg.evaluate(f"""() => {{ let t = 0; for (const r of {S}.it.regioni) {{ const v = r.capacita[String({ultimo})]; if (v) t += v.reduce((a, b) => a + b, 0); }} return Math.round(t); }}""")
    piede = pg.locator("#tabella-elettricita tfoot td").all_inner_texts()
    assert EUGENIO_NUMERO(tot) in [c.split("\n")[0] for c in piede], (tot, piede)
    # grafico a destra: riquadro del periodo largo quanto gli anni scelti
    w = pg.evaluate("() => { const r = document.querySelector('#grafico-andamento rect.periodo-scelto'); return r ? +r.getAttribute('width') : 0; }")
    w1 = pg.evaluate("""() => { const b = [...document.querySelectorAll('#grafico-andamento svg[role=img] rect')].filter((x) => !x.classList.contains('periodo-scelto'));
      return b.length ? +b[0].getAttribute('width') / 0.72 : 0; }""")
    assert w > 1.5 * w1 > 0
    # produzione (flusso): somma degli anni del periodo nella tabella
    pg.click('[data-modo="produzione"]')
    pg.wait_for_timeout(1200)
    assert pg.evaluate(f"() => [{S}.inizio, {S}.fine]") == [primo, ultimo]
    somma = pg.evaluate(f"""() => {{ let t = 0; for (const r of {S}.it.regioni) for (const a of [{primo}, {ultimo}]) {{ const v = r.produzione[String(a)]; if (v) t += v.reduce((x, y) => x + y, 0); }} return Math.round(t); }}""")
    assert EUGENIO_NUMERO(somma) in pg.locator("#tabella-elettricita tfoot").inner_text()
    assert f"Valori del periodo {primo}–{ultimo}: somma degli anni" in pg.locator("#tabella-elettricita").inner_text()
    # emissioni: fattore medio dell'Italia = somma delle emissioni / somma della produzione
    pg.click('[data-modo="emissioni"]')
    pg.wait_for_timeout(1200)
    a0, a1 = pg.evaluate(f"() => [{S}.inizio, {S}.fine]")
    atteso = pg.evaluate(f"""() => {{ const E = {S}.it.emissioni.italia; let c = 0, t = 0;
      for (const [a, v] of Object.entries(E)) if (+a >= {a0} && +a <= {a1}) {{ c += v[3]; t += v[2]; }} return c / t; }}""")
    if a0 < a1:
        assert f"Valori nazionali – {a0}–{a1}" in pg.locator("#riquadri-emissioni").inner_text()
    assert pg.locator('[data-cifra="medio"] b').inner_text().startswith(EUGENIO_NUMERO(atteso, 3))
    # tastiera: Fine sull'indicatore iniziale lo porta all'ultimo anno (un anno solo)
    pg.focus("#anno-inizio")
    pg.keyboard.press("End")
    pg.wait_for_timeout(900)
    assert pg.evaluate(f"() => [{S}.inizio, {S}.fine]") == [a1, a1]
    # collegamento con inizio e fine
    pg.focus("#anno-fine")
    pg.keyboard.press("Home")
    pg.wait_for_timeout(900)
    assert pg.evaluate(f"() => [{S}.inizio, {S}.fine]")[0] == pg.evaluate(f"() => {S}.fine")
    pg.evaluate("() => window.EUGENIO_ELETTRICITA.periodo(%d, %d)" % (primo, ultimo))
    pg.evaluate("() => window.EUGENIO_COLLEGAMENTO && window.EUGENIO_COLLEGAMENTO.aggiorna()")
    pg.wait_for_timeout(900)
    i, f = pg.evaluate(f"() => [{S}.inizio, {S}.fine]")
    assert i < f and f"inizio={i}" in pg.url and f"fine={f}" in pg.url and "anno=" not in pg.url
    assert errori == []


def EUGENIO_NUMERO(v, d=0):
    """Numero all'italiana come numeri.js (punto delle migliaia, virgola dei decimali)."""
    t = f"{v:,.{d}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return t


def _prove_costruisci_elettricita():
    """tests/test_costruisci.py della fase 15 caricato per percorso: la fase 16 ha un file con lo stesso nome e, con le
    prove delle due pagine nella stessa sessione, «import test_costruisci» prenderebbe quello sbagliato."""
    import importlib.util
    f = QUI.parent / "fase15-elettricita" / "tests" / "test_costruisci.py"
    spec = importlib.util.spec_from_file_location("prove_costruisci_elettricita", f)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
