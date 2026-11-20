"""Collegamento a questa simulazione (collegamento.js; 20/11/2026, richiesta di Paolo).

Sui file: modulo incluso in tutte le pagine della tabella «Collegamento» del README della fase 5 (e solo in quelle),
prima dello script della pagina; niente nelle pagine di testo; stile in stile.css; regola in README_stile.md.
In Chromium (si salta se Playwright o Chromium non ci sono), per ogni pagina a sole scelte e per le scelte delle pagine
con file: si fanno delle scelte, si legge il collegamento in fondo alla pagina, lo si apre in una pagina nuova e si
controlla che le scelte siano le stesse. Le rotte /api/ sono simulate (nessuna rete). In più: pulsante «Copia»,
indirizzo troppo lungo, nessuno scorrimento orizzontale a 375 px, nessun errore JavaScript.
"""
from __future__ import annotations

import functools
import json
import re
import threading
from urllib.parse import urlparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

QUI = Path(__file__).resolve().parents[1]
SITO = QUI / "sito"
PROVE = Path("/home/claude/wt_collegamento_prove")      # screenshot, solo se la cartella c'è

# (pagina, classe) – classe «a»: a sole scelte, collegamento completo; «b»: con file, solo le scelte che non dipendono
# dal file. Le pagine che non sono qui non hanno il collegamento (testo, segnaposto, moduli, solo file).
PAGINE = {
    "legge10.html": "a", "dati.html": "a", "indicatori.html": "a", "elettricita.html": "a",
    "rete-elettrica.html": "a", "ortofoto.html": "a",
    "edifici-pubblici.html": "a",
    "aria-trasformazioni.html": "a", "aria-ore.html": "a", "aria-latenti.html": "a", "aria-freecooling.html": "a",
    "cog-emissioni.html": "a", "edificio-clima.html": "a",
    "indici-prezzi.html": "b", "index.html": "b",
}
TESTO = ["faq.html", "metodo.html", "licenza.html", "privacy.html", "sitografia.html", "mirror.html", "novita.html",
         "contatti.html", "esempi.html", "contributi.html", "fv-leed.html", "cog-car.html", "lidar.html"]


def test_modulo_nelle_pagine_giuste():
    for nome in PAGINE:
        s = (SITO / nome).read_text(encoding="utf-8")
        m = re.search(r'<script src="collegamento\.js\?v=\w+"></script>', s)
        assert m, nome
        # prima dello script della pagina (che si registra) e dopo aspetto.js
        assert s.index("aspetto.js") < m.start(), nome
    for nome in TESTO:
        assert "collegamento.js" not in (SITO / nome).read_text(encoding="utf-8"), nome
    css = (SITO / "stile.css").read_text(encoding="utf-8")
    assert ".collegamento-simulazione" in css and ".collegamento-campo" in css
    js = (SITO / "collegamento.js").read_text(encoding="utf-8")
    for parola in ("replaceState", "execCommand", "clipboard", "LIMITE = 2000", "Collegamento a questa simulazione",
                   "non contiene file caricati"):
        assert parola in js, parola
    assert "fetch(" not in js            # niente al server
    regole = (SITO / "README_stile.md").read_text(encoding="utf-8")
    assert "Collegamento a questa simulazione" in regole and "data-collegamento" in regole
    readme = (QUI / "README.md").read_text(encoding="utf-8")
    for nome in PAGINE:
        assert f"`{nome}`" in readme, nome


# ---------------------------------------------------------------------------------------------- browser
class _Zitto(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def base():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Zitto, directory=str(SITO)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}/"
    srv.shutdown()


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


_FONTE = "Open-Meteo.com"
CATALOGO = {
    "dataset": [
        {"id": "meteo_giornaliero", "titolo": "Meteo giornaliero (ERA5 corretto)", "descrizione": "…", "fonte": _FONTE,
         "licenza": "CC BY 4.0", "licenza_url": "", "periodo": "date", "inizio": "2015-01-01", "fine": "2026-11-10", "area": True,
         "frequenze": [{"id": "giornaliera", "nome": "Giornaliera"}, {"id": "mensile", "nome": "Mensile"}],
         "frequenza_nativa": "giornaliera",
         "variabili": [{"id": "t_media", "nome": "Temperatura media", "gruppo": "Meteo", "predefinita": True},
                       {"id": "pioggia", "nome": "Pioggia", "gruppo": "Meteo", "predefinita": False},
                       {"id": "vento", "nome": "Vento", "gruppo": "Meteo", "predefinita": True}]},
        {"id": "legge10", "titolo": "Dati climatici per la Relazione Legge 10", "descrizione": "…", "fonte": _FONTE,
         "licenza": "CC BY 4.0", "licenza_url": "", "periodo": "stagioni", "inizio": "2015-01-01", "fine": "2026-11-10",
         "area": True, "frequenze": [], "variabili": [], "tipologie": [{"id": "mensili", "nome": "Mensili"}],
         "stagioni": {"min": 1, "max": 30, "predefinite": 10, "scelte": [1, 5, 10, 20, 0], "tutte": 0}}],
    "non_scaricabili": [], "regioni": ["08", "05"], "comuni": 2, "limiti": {"righe_csv": 500000},
}
STIMA = {"righe": 10, "colonne": 3, "dimensione": "1 kB", "byte": 1000, "comuni": 1, "dal": None, "al": None, "avvisi": [],
         "consentito": True, "motivo": "", "suggerimenti": []}


def _api(route):
    url = route.request.url
    if "/api/storici/catalogo" in url:
        return route.fulfill(json=CATALOGO)
    if "/api/storici/stima" in url:
        return route.fulfill(json=STIMA)
    percorso = urlparse(url).path
    for chiave, risposta in RISPOSTE.items():
        if percorso == chiave:
            return route.fulfill(json=risposta(url) if callable(risposta) else risposta)
    return route.fulfill(status=404, body=json.dumps({"detail": "non simulata"}), content_type="application/json")


FONTI = {"fonti": [
    {"id": "rer2023", "nome": "Ortofoto RER 2023-24 (20 cm)", "licenza": "CC BY 4.0", "citazione": "Regione Emilia-Romagna – Ortofoto RER",
     "scheda": "https://geoportale.regione.emilia-romagna.it/", "stato": "da confermare", "copia": True, "nei_report": True,
     "zoom": [12, 20], "riquadro": [9.19, 43.73, 12.84, 45.16], "tessere": "/api/ortofoto/rer2023/{z}/{x}/{y}.jpg",
     "spostabile": True, "spostamento_max": 20},
    {"id": "s2cloudless2016", "nome": "Sentinel-2 cloudless 2016 (10 m)", "licenza": "CC BY 4.0", "citazione": "Sentinel-2 cloudless – EOX",
     "scheda": "https://cloudless.eox.at/", "stato": "confermata", "copia": True, "nei_report": True, "zoom": [5, 15],
     "riquadro": [6.6, 35.4, 18.6, 47.1], "tessere": "/api/ortofoto/s2cloudless2016/{z}/{x}/{y}.jpg", "spostabile": False,
     "spostamento_max": 0},
    {"id": "pcn2012", "nome": "Geoportale Nazionale (solo consultazione)", "licenza": "da verificare", "citazione": "Geoportale – AGEA 2012",
     "scheda": "https://gn.mase.gov.it/", "stato": "da confermare", "copia": False, "nei_report": False, "zoom": [12, 19],
     "riquadro": [6.6, 35.4, 18.6, 47.1], "tessere": "/api/ortofoto/pcn2012/{z}/{x}/{y}.jpg", "spostabile": True,
     "spostamento_max": 20}]}
STRATI = {"strati": [
    {"id": "catasto", "tema": "particelle", "nome": "Confini delle particelle catastali", "licenza": "CC BY 4.0",
     "citazione": "Agenzia delle Entrate – Cartografia catastale, CC BY 4.0", "scheda": "https://www.agenziaentrate.gov.it/",
     "stato": "confermata", "regioni": [], "zoom": [16, 20], "riquadro": [6.6, 35.4, 18.6, 47.1], "colore": "#ffd400",
     "legenda": "linee gialle", "tipo": "immagine", "nota": "", "tessere": "/api/ortofoto/strati/catasto/{z}/{x}/{y}.png"},
    {"id": "osm_edifici", "tema": "edifici", "nome": "Contorni OSM", "licenza": "ODbL 1.0",
     "citazione": "© contributori OpenStreetMap (ODbL 1.0)", "scheda": "https://www.openstreetmap.org/copyright",
     "stato": "confermata", "regioni": [], "zoom": [16, 16], "riquadro": [6.6, 35.4, 18.6, 47.1], "colore": "#00e5ff",
     "legenda": "linee azzurre", "tipo": "vettori", "nota": "", "tessere": "/api/ortofoto/strati/osm_edifici/{z}/{x}/{y}.json"}]}
RISPOSTE: dict = {"/api/ortofoto/fonti": FONTI, "/api/ortofoto/strati": STRATI}


def _apri(browser, url, larghezza=1400, altezza=950, rotte=()):
    ctx = browser.new_context(viewport={"width": larghezza, "height": altezza})
    pg = ctx.new_page()
    errori = []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    pg.route(lambda u: not u.startswith("http://127.0.0.1"), lambda r: r.abort())     # nessuna rete esterna
    pg.route("**/api/**", _api)
    for schema, gestore in rotte:
        pg.route(schema, gestore)
    pg.goto(url)
    pg.wait_for_selector("html[data-collegamento-pronto]", state="attached", timeout=30000)
    return ctx, pg, errori


def _collegamento(pg):
    pg.wait_for_timeout(700)             # il modulo riscrive l'indirizzo con un piccolo ritardo
    v = pg.input_value("#collegamento-indirizzo")
    assert v == pg.url, (v, pg.url)
    return v


def _foto(pg, nome):
    if PROVE.is_dir():
        pg.screenshot(path=str(PROVE / nome), full_page=False)
        pg.locator(".collegamento-simulazione").scroll_into_view_if_needed()
        pg.screenshot(path=str(PROVE / nome.replace(".png", "_riquadro.png")), full_page=False)


def _stretta(browser, url, nome, rotte=()):
    """A 375 px: niente scorrimento orizzontale e riquadro visibile."""
    ctx, pg, errori = _apri(browser, url, 375, 800, rotte)
    pg.wait_for_timeout(500)
    larga = pg.evaluate("document.documentElement.scrollWidth")
    assert larga <= 376, (nome, larga)
    box = pg.locator(".collegamento-simulazione")
    assert box.count() == 1
    box.scroll_into_view_if_needed()
    if PROVE.is_dir():
        pg.screenshot(path=str(PROVE / f"{nome}_375.png"), full_page=False)
    assert not errori, errori
    ctx.close()


# ---------------------------------------------------------------------------------------------- Legge 10
def test_legge10(browser, base):
    ctx, pg, errori = _apri(browser, base + "legge10.html")
    pg.wait_for_selector("#comune option[value='037006']", state="attached")
    pg.select_option("#comune", "037006")
    pg.select_option("#anni", "5")
    link = _collegamento(pg)
    assert "comune=037006" in link and "anni=5" in link and "regione=08" in link
    _foto(pg, "legge10_1400.png")
    ctx.close()
    ctx, pg, errori2 = _apri(browser, link)
    pg.wait_for_function("document.getElementById('comune').value === '037006'")
    assert pg.input_value("#anni") == "5"
    assert pg.input_value("#collegamento-indirizzo") == link
    ctx.close()
    assert not errori and not errori2
    _stretta(browser, link, "legge10")


# ---------------------------------------------------------------------------------------------- Dati climatici
def test_dati(browser, base):
    ctx, pg, errori = _apri(browser, base + "dati.html?dataset=meteo_giornaliero")
    pg.wait_for_function("document.getElementById('dal').value !== ''")
    pg.uncheck("input[name='variabile'][value='vento']")
    pg.check("input[name='variabile'][value='pioggia']")
    pg.check("input[name='frequenza'][value='mensile']")
    pg.fill("#dal", "2020-03-01")
    pg.dispatch_event("#dal", "change")
    pg.select_option("#copertura", index=1)
    pg.check("input[name='area'][value='comuni']")
    pg.wait_for_selector("#mappa svg path[data-nome='Bologna']", state="attached")
    pg.dispatch_event("#mappa svg path[data-nome='Bologna']", "click")
    pg.dispatch_event("#mappa svg path[data-nome='Imola']", "click")
    pg.check("input[name='formato'][value='ods']")
    cop = pg.input_value("#copertura")
    link = _collegamento(pg)
    for parte in ("dataset=meteo_giornaliero", "var=t_media%2Cpioggia", "freq=mensile", "dal=2020-03-01", "area=comuni",
                  "formato=ods", "comuni="):
        assert parte in link, parte
    _foto(pg, "dati_1400.png")
    ctx.close()
    ctx, pg, errori2 = _apri(browser, link)
    assert pg.is_checked("input[name='variabile'][value='pioggia']") and not pg.is_checked("input[name='variabile'][value='vento']")
    assert pg.is_checked("input[name='frequenza'][value='mensile']") and pg.input_value("#copertura") == cop
    assert pg.input_value("#dal") == "2020-03-01" and pg.is_checked("input[name='formato'][value='ods']")
    chips = pg.eval_on_selector_all("#comuni-scelti .comune-chip", "bs => bs.map(b => b.textContent)")
    assert sorted(chips) == ["Bologna (BO)", "Imola (BO)"]
    assert pg.input_value("#collegamento-indirizzo") == link
    ctx.close()
    assert not errori and not errori2
    _stretta(browser, link, "dati")


# ---------------------------------------------------------------------------------------------- Costi energetici Sanità
def test_indicatori(browser, base):
    ctx, pg, errori = _apri(browser, base + "indicatori.html")
    pg.wait_for_function("document.getElementById('ente').options.length > 2")
    pg.select_option("#regione", "05")
    pg.wait_for_function("document.getElementById('ente').value.startsWith('050')")
    ente = pg.eval_on_selector("#ente", "s => s.options[s.options.length - 1].value")
    pg.select_option("#ente", ente)
    pg.select_option("#componente", "elettricita")
    pg.check("#mostra-componenti")
    anno = pg.eval_on_selector("#anno", "s => s.options[s.options.length - 1].value")
    pg.select_option("#anno", anno)
    link = _collegamento(pg)
    assert "regione=05" in link and f"ente={ente}" in link and "comp=elettricita" in link and "componenti=1" in link
    _foto(pg, "indicatori_1400.png")
    ctx.close()
    ctx, pg, errori2 = _apri(browser, link)
    assert pg.input_value("#regione") == "05" and pg.input_value("#ente") == ente
    assert pg.input_value("#componente") == "elettricita" and pg.is_checked("#mostra-componenti")
    assert pg.input_value("#anno") == anno
    assert pg.input_value("#collegamento-indirizzo") == link
    ctx.close()
    assert not errori and not errori2
    _stretta(browser, link, "indicatori")


# ---------------------------------------------------------------------------------------------- Elettricità (Terna)
@pytest.fixture(scope="module")
def dati_el(tmp_path_factory):
    import sys
    sys.path.insert(0, str(QUI.parent / "fase15-elettricita"))
    sys.path.insert(0, str(QUI.parent / "fase15-elettricita" / "tests"))
    from elettricita import costruisci as K
    import test_costruisci as T
    tmp = tmp_path_factory.mktemp("el")
    K.costruisci(T._raw(tmp), tmp / "out", SITO / "dati" / "mappa")
    out = tmp / "out"
    return [("**/dati/elettricita/**",
             lambda r: r.fulfill(path=str(out / r.request.url.split("/dati/elettricita/")[1].split("?")[0])))]


def test_elettricita(browser, base, dati_el):
    pronta = "() => window.EUGENIO_ELETTRICITA && window.EUGENIO_ELETTRICITA.stato.pronto"
    ctx, pg, errori = _apri(browser, base + "elettricita.html?vista=italia", rotte=dati_el)
    pg.wait_for_function(pronta, timeout=20000)
    pg.evaluate("() => window.EUGENIO_ELETTRICITA.scegliRegione('08')")
    pg.wait_for_function("() => document.getElementById('titolo-vista').textContent === 'Emilia-Romagna'", timeout=10000)
    # i dati inventati hanno due anni di capacità (2020, 2021): si sceglie il primo, non predefinito
    pg.eval_on_selector("#anno-elettricita", "c => { c.value = 0; c.dispatchEvent(new Event('input', {bubbles: true})); c.dispatchEvent(new Event('change', {bubbles: true})); }")
    anno = pg.inner_text("#anno-scelto")
    pg.uncheck("#strato-fondo")
    pg.check("#strato-ortofoto")
    link = _collegamento(pg)
    for parte in ("regione=08", "modo=capacita", "anno=2020", "fondo=0", "ortofoto=1", "barre=1"):
        assert parte in link, parte
    _foto(pg, "elettricita_1400.png")
    ctx.close()
    ctx, pg, errori2 = _apri(browser, link, rotte=dati_el)
    assert pg.evaluate("() => window.EUGENIO_ELETTRICITA.stato.regione") == "08"
    assert pg.get_attribute('[data-modo="capacita"]', "aria-pressed") == "true"
    assert pg.inner_text("#anno-scelto") == anno and pg.evaluate("() => String(window.EUGENIO_ELETTRICITA.stato.anno)") == anno
    assert not pg.is_checked("#strato-fondo") and pg.is_checked("#strato-ortofoto") and pg.is_checked("#strato-barre")
    pg.wait_for_timeout(800)
    assert pg.input_value("#collegamento-indirizzo") == link
    ctx.close()
    assert not errori and not errori2
    _stretta(browser, link, "elettricita", dati_el)


# ---------------------------------------------------------------------------------------------- Stato della rete elettrica
SENZA_ARCGIS = [("https://services-eu1.arcgis.com/**", lambda r: r.abort())]


def test_rete_elettrica(browser, base):
    pronta = "() => window.EUGENIO_RETE_PAGINA && window.EUGENIO_RETE_PAGINA.st.pronto"
    ctx, pg, errori = _apri(browser, base + "rete-elettrica.html?prova=1&regione=08", rotte=SENZA_ARCGIS)
    pg.wait_for_function(pronta, timeout=20000)
    istat = pg.evaluate("window.EUGENIO_RETE_PAGINA.st.righe.find((r) => r.concessionario && r.pieno).istat")
    pg.evaluate(f"window.EUGENIO_RETE_PAGINA.apriComune('{istat}')")
    pg.uncheck("#strato-cabine")
    pg.uncheck("#strato-ortofoto")
    link = _collegamento(pg)
    for parte in ("prova=1", "regione=08", f"comune={istat}", "cabine=0", "ortofoto=0", "criticita=1"):
        assert parte in link, parte
    _foto(pg, "rete_elettrica_1400.png")
    ctx.close()
    ctx, pg, errori2 = _apri(browser, link, rotte=SENZA_ARCGIS)
    pg.wait_for_function(pronta, timeout=20000)
    assert pg.evaluate("window.EUGENIO_RETE_PAGINA.st.scelto") == istat
    assert not pg.is_checked("#strato-cabine") and not pg.is_checked("#strato-ortofoto") and pg.is_checked("#strato-criticita")
    assert pg.evaluate("window.EUGENIO_RETE_PAGINA.st.mappa.getLayoutProperty('rete-cabine-punti', 'visibility')") == "none"
    pg.wait_for_timeout(800)
    assert pg.input_value("#collegamento-indirizzo") == link
    ctx.close()
    assert not errori and not errori2
    _stretta(browser, link, "rete_elettrica", SENZA_ARCGIS)


# ---------------------------------------------------------------------------------------------- Ortofoto
def test_ortofoto(browser, base):
    pronta = "() => window.EUGENIO_ORTOFOTO && window.EUGENIO_ORTOFOTO.stato.pronto"
    ctx, pg, errori = _apri(browser, base + "ortofoto.html")
    pg.wait_for_function(pronta, timeout=20000)
    pg.evaluate("() => window.EUGENIO_ORTOFOTO.stato.mappa.jumpTo({ center: [11.3426, 44.4949], zoom: 15.5 })")
    pg.check("input[name='fonte'][value='pcn2012']")
    pg.check("#strato-particelle")
    link = _collegamento(pg)
    for parte in ("lat=44.494900", "lon=11.342600", "z=15.50", "fonte=pcn2012", "particelle=1", "contorni=0"):
        assert parte in link, parte
    _foto(pg, "ortofoto_1400.png")
    ctx.close()
    ctx, pg, errori2 = _apri(browser, link)
    pg.wait_for_function(pronta, timeout=20000)
    c = pg.evaluate("() => { const m = window.EUGENIO_ORTOFOTO.stato.mappa, c = m.getCenter(); return [c.lat, c.lng, m.getZoom()]; }")
    assert abs(c[0] - 44.4949) < 1e-5 and abs(c[1] - 11.3426) < 1e-5 and abs(c[2] - 15.5) < 1e-6
    assert pg.evaluate("() => window.EUGENIO_ORTOFOTO.stato.scelta.id") == "pcn2012"
    assert pg.is_checked("#strato-particelle") and not pg.is_checked("#strato-edifici")
    assert pg.evaluate("() => window.EUGENIO_ORTOFOTO.stato.strati.stato.particelle") is True
    pg.wait_for_timeout(800)
    assert pg.input_value("#collegamento-indirizzo") == link
    ctx.close()
    assert not errori and not errori2
    _stretta(browser, link, "ortofoto")


# ---------------------------------------------------------------------------------------------- Edifici pubblici
def test_edifici_pubblici(browser, base):
    pronta = "() => window.EUGENIO_PUBBLICI && window.EUGENIO_PUBBLICI.stato.pronto"
    ctx, pg, errori = _apri(browser, base + "edifici-pubblici.html?lat=44.1394&lon=12.2431&z=16")
    pg.wait_for_function(pronta, timeout=20000)
    pg.uncheck("#tipi-pubblici input[value='T']")
    pg.uncheck("#gruppi-pubblici input[value='U']")
    pg.wait_for_selector("#sfondo-ortofoto option[value='pcn2012']", state="attached")
    pg.select_option("#sfondo-ortofoto", "pcn2012")
    pg.uncheck("#strato-ortofoto")
    link = _collegamento(pg)
    for parte in ("lat=44.139400", "z=16.00", "tipi=E%2CS", "enti=", "fonte=pcn2012", "ortofoto=0"):
        assert parte in link, parte
    assert "U" not in re.search(r"enti=([^&]*)", link).group(1).replace("%2C", ",").split(",")
    _foto(pg, "edifici_pubblici_1400.png")
    ctx.close()
    ctx, pg, errori2 = _apri(browser, link)
    pg.wait_for_function(pronta, timeout=20000)
    assert pg.evaluate("() => [...window.EUGENIO_PUBBLICI.stato.tipi].sort().join()") == "E,S"
    assert not pg.evaluate("() => window.EUGENIO_PUBBLICI.stato.gruppi.has('U')")
    assert pg.evaluate("() => window.EUGENIO_PUBBLICI.stato.gruppi.has('C')")
    assert pg.input_value("#sfondo-ortofoto") == "pcn2012" and not pg.is_checked("#strato-ortofoto")
    pg.wait_for_timeout(800)
    assert pg.input_value("#collegamento-indirizzo") == link
    ctx.close()
    assert not errori and not errori2
    _stretta(browser, link, "edifici_pubblici")


# ---------------------------------------------------------------------------------------------- Trattamento aria (?prova=1)
ARIA_PRONTA = "() => window.EUGENIO_ARIA_PAGINA && window.EUGENIO_ARIA_PAGINA.scelta.serie()"


def _aria_comuni(pg):
    """Comune diverso da quello di partenza, anni, livello invernale e diagramma di Mollier (moduli comuni)."""
    pg.wait_for_function(ARIA_PRONTA, timeout=30000)
    pg.select_option("#aria-comune", "037032")                                    # Imola
    pg.eval_on_selector("#aria-anni", "r => { r.value = 1; r.dispatchEvent(new Event('change', {bubbles: true})); }")
    pg.select_option("select[id$='-inverno']", "95")
    pg.click(".aria-vista button[data-modo='mollier']")
    pg.wait_for_function(ARIA_PRONTA, timeout=30000)


def _aria_controlla_comuni(pg):
    pg.wait_for_function(ARIA_PRONTA, timeout=30000)
    st = pg.evaluate("() => window.EUGENIO_ARIA_PAGINA.scelta.stato()")
    assert st["istat"] == "037032" and st["anni"] == 2
    assert pg.evaluate("() => window.EUGENIO_ARIA_PAGINA.livello.valori().inverno") == 95
    assert pg.evaluate("() => window.EUGENIO_ARIA_PAGINA.diagramma.modo()") == "mollier"


def _aria(browser, base, pagina, cambia, controlla, parti):
    ctx, pg, errori = _apri(browser, base + f"{pagina}.html?prova=1")
    _aria_comuni(pg)
    cambia(pg)
    pg.wait_for_timeout(300)
    link = _collegamento(pg)
    for parte in ("prova=1", "comune=037032", "anni=2", "inverno=95", "diagramma=mollier", *parti):
        assert parte in link, parte
    _foto(pg, f"{pagina.replace('-', '_')}_1400.png")
    ctx.close()
    ctx, pg, errori2 = _apri(browser, link)              # contesto nuovo: niente memoria del browser
    _aria_controlla_comuni(pg)
    controlla(pg)
    pg.wait_for_timeout(800)
    assert pg.input_value("#collegamento-indirizzo") == link
    ctx.close()
    assert not errori and not errori2
    _stretta(browser, link, pagina.replace("-", "_"))
    return link


def test_aria_ore(browser, base):
    def cambia(pg):
        pg.click("#aria-gruppi .aria-gruppo >> nth=0 >> button[data-preset='ufficio']")
        pg.click(".aria-ore-modo button[data-nuvola='densita']")
        pg.select_option("#ore-raggio", "1.6")
        pg.fill("#ore-zona-tMin", "19")

    def controlla(pg):
        g = pg.evaluate("() => window.EUGENIO_ARIA_PAGINA.gruppi.gruppi().map((g) => [g.nome, g.oraDa, g.oraA, g.giorni])")
        assert g[0][1:] == [8, 18, "feriali"]
        st = pg.evaluate("() => { const s = window.EUGENIO_ARIA_PAGINA.stato; return [s.modo, s.raggio, s.zona.tMin]; }")
        assert st == ["densita", 1.6, 19]
        assert pg.input_value("#ore-raggio") == "1.6" and pg.input_value("#ore-zona-tMin") == "19"
    _aria(browser, base, "aria-ore", cambia, controlla, ("gruppi=", "nuvola=densita", "raggio=1.6", "comfort=19"))


def test_aria_latenti(browser, base):
    def cambia(pg):
        pg.evaluate("() => window.EUGENIO_ARIA_PAGINA.obiettivo('estate', 25, 55)")
        pg.fill("#lat-portata", "2500")
        pg.dispatch_event("#lat-portata", "input")
        pg.select_option("#lat-riferimento", "2")
        pg.click("#aria-gruppi-inverno button[data-preset='ufficio']")

    def controlla(pg):
        assert pg.input_value("#lat-portata").replace(".", "") == "2500" and pg.input_value("#lat-riferimento") == "2"
        g = pg.evaluate("() => window.EUGENIO_ARIA_PAGINA.gruppi.inverno.gruppi()[0]")
        assert [g["oraDa"], g["oraA"], g["giorni"]] == [8, 18, "feriali"]
    link = _aria(browser, base, "aria-latenti", cambia, controlla, ("portata=2500", "riferimento=2", "gruppi-inverno=", "obiettivo_estate=25*55"))
    assert "gruppi-estate=" in link


def test_aria_freecooling(browser, base):
    def cambia(pg):
        pg.fill("#fc-V", "12000")
        pg.dispatch_event("#fc-V", "input")
        pg.select_option("#fc-tipoRec", "entalpico")
        pg.fill("#fc-epsL", "0,55")
        pg.dispatch_event("#fc-epsL", "input")
        pg.select_option("#fc-economizzatore", "temperatura")

    def controlla(pg):
        assert pg.input_value("#fc-V") == "12000" and pg.input_value("#fc-tipoRec") == "entalpico"
        assert pg.input_value("#fc-epsL") == "0,55" and pg.input_value("#fc-economizzatore") == "temperatura"
    _aria(browser, base, "aria-freecooling", cambia, controlla, ("V=12000", "tipoRec=entalpico", "epsL=0%2C55", "economizzatore=temperatura"))


def test_aria_trasformazioni(browser, base):
    def cambia(pg):
        pg.fill("#aria-trasformazioni-quota-esterna", "40")
        pg.dispatch_event("#aria-trasformazioni-quota-esterna", "input")
        pg.dispatch_event("#aria-trasformazioni-quota-esterna", "change")
        pg.select_option("#aria-trasformazioni-riferimento", "2")

    def controlla(pg):
        st = pg.evaluate("() => window.EUGENIO_ARIA_PAGINA.stato()")
        assert st["generali"]["quotaEsterna"] == 40 and st["generali"]["riferimento"] == 2
        assert pg.input_value("#aria-trasformazioni-riferimento") == "2"
    _aria(browser, base, "aria-trasformazioni", cambia, controlla, ("uta=",))


# ---------------------------------------------------------------------------------------------- Cogenerazione › Emissioni
def test_cog_emissioni(browser, base):
    ctx, pg, errori = _apri(browser, base + "cog-emissioni.html")
    pg.wait_for_selector("#anno-fattori option", state="attached")
    pg.check("input[name='modo-cog'][value='taglia']")
    pg.fill("#potenza", "350")
    pg.fill("#ore", "4200")
    anno = pg.eval_on_selector("#anno-fattori", "s => s.options[s.options.length - 1].value")
    pg.select_option("#anno-fattori", anno)
    pg.select_option("#fattore-rete", "termoelettrica_lorda")
    pg.fill("#eta-caldaia", "85")
    pg.click("#calcola-emissioni")
    risultato = pg.inner_text("#messaggio-emissioni")
    link = _collegamento(pg)
    for parte in ("modo=taglia", "potenza=350", "ore=4200", f"anno={anno}", "rete=termoelettrica_lorda", "eta_caldaia=85", "calcolato=1"):
        assert parte in link, parte
    _foto(pg, "cog_emissioni_1400.png")
    ctx.close()
    ctx, pg, errori2 = _apri(browser, link)
    assert pg.is_checked("input[name='modo-cog'][value='taglia']") and pg.is_visible("#campi-taglia")
    assert pg.input_value("#potenza") == "350" and pg.input_value("#ore") == "4200" and pg.input_value("#anno-fattori") == anno
    assert pg.input_value("#fattore-rete") == "termoelettrica_lorda" and pg.input_value("#eta-caldaia") == "85"
    assert pg.is_visible("#passo-risultati") and pg.inner_text("#messaggio-emissioni") == risultato
    pg.wait_for_timeout(800)
    assert pg.input_value("#collegamento-indirizzo") == link
    ctx.close()
    assert not errori and not errori2
    _stretta(browser, link, "cog_emissioni")


# ---------------------------------------------------------------------------------------------- Cambiamento climatico
def _clima(route):
    url = route.request.url
    if "dati/clima/regioni.json" in url:
        return route.fulfill(json={"037006": "08"})
    if "dati/clima/08/037006.json" in url:
        return route.fulfill(json={"nome": "Bologna", "stagioni": {"da": 1940, "gg_zona": [3000 - 8 * k for k in range(86)]}})
    return route.fallback()


def test_edificio_clima(browser, base):
    rotte = [("**/dati/clima/**", _clima)]
    ctx, pg, errori = _apri(browser, base + "edificio-clima.html", rotte=rotte)
    pg.fill("#clima-comune", "037006")
    pg.click("#clima-carica")
    pg.wait_for_function("document.getElementById('messaggio-clima').textContent.includes('stagioni dal')")
    pg.select_option("#clima-dal", "n20")
    pg.fill("#firma-base", "300")
    pg.dispatch_event("#firma-base", "change")
    pg.wait_for_function("document.getElementById('messaggio-clima').textContent.includes('20 stagioni')")
    testo = pg.inner_text("#messaggio-clima")
    link = _collegamento(pg)
    for parte in ("istat=037006", "dal=n20", "base=300"):
        assert parte in link, parte
    _foto(pg, "edificio_clima_1400.png")
    ctx.close()
    ctx, pg, errori2 = _apri(browser, link, rotte=rotte)
    pg.wait_for_function("document.getElementById('messaggio-clima').textContent.includes('20 stagioni')")
    assert pg.input_value("#clima-dal") == "n20" and pg.input_value("#firma-base") == "300"
    assert pg.inner_text("#messaggio-clima") == testo
    pg.wait_for_timeout(800)
    assert pg.input_value("#collegamento-indirizzo") == link
    ctx.close()
    assert not errori and not errori2
    _stretta(browser, link, "edificio_clima", rotte)


# ---------------------------------------------------------------------------------------------- Indici dei prezzi (con file)
def test_indici_prezzi(browser, base):
    import sys
    sys.path.insert(0, str(QUI / "tests"))
    from test_indici_prezzi_browser import INDICI
    rotte = [("**/dati/prezzi/indici.json*", lambda r: r.fulfill(json=INDICI))]
    ctx, pg, errori = _apri(browser, base + "indici-prezzi.html", rotte=rotte)
    pg.wait_for_selector("#consip-ee22 table")
    pg.locator("#intercenter-ee19-2026 button.filtro", has_text="Fascia F3").click()
    pg.locator("#consip-ee22 select").select_option("1")
    pg.locator("#consip-ee22 button.filtro", has_text="Monoraria").click()
    pg.select_option("#lotto-confronto", "1")
    link = _collegamento(pg)
    for parte in ("intercenter-ee19-2026*1*F3", "consip-ee22*1*F0", "lotto_consip=1"):
        assert parte in link, parte
    _foto(pg, "indici_prezzi_1400.png")
    ctx.close()
    ctx, pg, errori2 = _apri(browser, link, rotte=rotte)
    assert pg.get_attribute("#intercenter-ee19-2026 button.filtro:has-text('Fascia F3')", "aria-pressed") == "true"
    assert pg.locator("#intercenter-ee19-2026 tbody tr").nth(0).inner_text().split("\t")[1] == "120,00"
    assert pg.locator("#consip-ee22 select").input_value() == "1"
    assert pg.get_attribute("#consip-ee22 button.filtro:has-text('Monoraria')", "aria-pressed") == "true"
    assert pg.input_value("#lotto-confronto") == "1"
    pg.wait_for_timeout(800)
    assert pg.input_value("#collegamento-indirizzo") == link
    ctx.close()
    assert not errori and not errori2
    _stretta(browser, link, "indici_prezzi", rotte)


# ---------------------------------------------------------------------------------------------- Previsioni (con file)
def test_previsioni(browser, base):
    ctx, pg, errori = _apri(browser, base + "index.html?regione=08")
    pg.wait_for_selector("#comune option[value='040007']", state="attached")       # Cesena
    pg.select_option("#comune", "040007")
    pg.check("input[name='cosa'][value='clima']")
    pg.check("input[name='modalita'][value='lungo']")
    pg.fill("#orizzonte", "60")
    pg.dispatch_event("#orizzonte", "change")
    primo = pg.eval_on_selector("#covariate input:checked", "i => i.value")
    pg.uncheck(f"#covariate input[value='{primo}']")
    cov = pg.eval_on_selector_all("#covariate input:checked", "is => is.map(i => i.value).join(',')")
    link = _collegamento(pg)
    for parte in ("regione=08", "comune=040007", "cosa=clima", "modalita=lungo", "orizzonte=60", "cov="):
        assert parte in link, parte
    assert "calcolato" not in link                       # nessun risultato in vista (previsioni simulate assenti)
    _foto(pg, "previsioni_1400.png")
    ctx.close()
    ctx, pg, errori2 = _apri(browser, link)
    assert pg.input_value("#comune") == "040007" and pg.is_checked("input[name='cosa'][value='clima']")
    assert pg.is_checked("input[name='modalita'][value='lungo']") and pg.input_value("#orizzonte") == "60"
    assert pg.eval_on_selector_all("#covariate input:checked", "is => is.map(i => i.value).join(',')") == cov
    assert pg.is_hidden("#blocco-consumi") and not pg.is_disabled("#calcola")
    pg.wait_for_timeout(800)
    assert pg.input_value("#collegamento-indirizzo") == link
    ctx.close()
    # con calcolato=1 («Solo il clima» già calcolato) la pagina rifà la richiesta da sola, con le stesse scelte
    chiamate = []
    ctx = browser.new_context(viewport={"width": 1400, "height": 950})
    pg = ctx.new_page()
    pg.route(lambda u: not u.startswith("http://127.0.0.1"), lambda r: r.abort())
    pg.route("**/api/**", lambda r: (chiamate.append(r.request.url), r.fulfill(status=404, json={"detail": "simulata"})))
    pg.goto(link + "&calcolato=1")
    pg.wait_for_function("document.getElementById('messaggio').textContent.includes('non disponibili')")
    richiesta = [c for c in chiamate if "/api/clima-previsto/040007" in c]
    assert richiesta and "modalita=lungo" in richiesta[0] and "orizzonte=60" in richiesta[0]
    ctx.close()
    assert not errori and not errori2
    _stretta(browser, link, "previsioni")
