"""Territorio › Edifici pubblici, ricerca per ente (pubblici_enti.js e tabella_ordinabile.js, 22/11/2026).

Sui file: moduli inclusi nella pagina nell'ordine giusto, combobox ARIA nel pannello, nessun pulsante di download della
tabella, regola delle tabelle ordinabili in README_stile.md. In Chromium (si salta se Playwright o Chromium non ci sono),
con l'elenco degli enti e le rotte /api/immobili-pa/ente/… simulate (nessuna rete): schede del passo 1, autocompletamento
da tastiera, enti scelti con il colore, limite di 8, totali e tabella per ente, ordinamento crescente → decrescente → non
ordinato con aria-sort, clic su una riga (scheda), ente grande per comune, collegamento riaperto con gli stessi enti e
colori, 375 px senza scorrimento orizzontale, nessun errore JavaScript; scheda in sovraimpressione sulla mappa e stili
proprietà / uso / terreni (22/11/2026 sera)."""
from __future__ import annotations

import functools
import json
import re
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

QUI = Path(__file__).resolve().parents[1]
SITO = QUI / "sito"
PROVE = Path("/home/claude/scr")          # screenshot, solo se la cartella c'è


def test_file():
    s = (SITO / "edifici-pubblici.html").read_text(encoding="utf-8")
    i = [s.index(f'src="{n}?v=') for n in ("collegamento.js", "tabella_ordinabile.js", "edifici_pubblici.js", "pubblici_enti.js")]
    assert i == sorted(i)
    assert 'role="tablist"' in s and 'id="scheda-enti"' in s and 'role="combobox"' in s and 'aria-controls="proposte-enti"' in s
    assert 'role="listbox"' in s and 'id="passo-elenco-enti"' in s and 'id="legenda-enti"' in s
    # testi e avvisi dello studio (§ 5.5)
    for t in ("possono mancare beni", "lorda per i fabbricati", "Il soggetto che cede l'immobile all'ente non è mostrato",
              "non si scarica"):
        assert t in s, t
    js = (SITO / "pubblici_enti.js").read_text(encoding="utf-8")
    assert "cedente" not in js.replace("Nessun codice fiscale e nessun soggetto cedente", "") and "amm_cf" not in js
    for vietato in ("text/csv", ".csv", "xlsx", "download ="):
        assert vietato not in js, vietato
    t = (SITO / "tabella_ordinabile.js").read_text(encoding="utf-8")
    assert "aria-sort" in t and 'localeCompare(String(b), "it"' in t
    regole = (SITO / "README_stile.md").read_text(encoding="utf-8")
    assert "Tabelle ordinabili" in regole and "tabella_ordinabile.js" in regole


# ---------------------------------------------------------------------------------------------- dati simulati
GRUPPI = {"C": "Comuni", "I": "Unioni di Comuni e Comunità montane", "S": "Sanità (ASL e ospedali)", "U": "Università", "A": "Altri enti"}
ENTI = [  # id, chiave, nome, gruppo, sede, beni, fabbricati, terreni, particelle, regioni
    [1, "aaaaaaaaa1", "ALMA MATER STUDIORUM UNIVERSITA' DI BOLOGNA", "U", "Bologna", 1134, 704, 430, 758, [0, 1]],
    [2, "aaaaaaaaa2", "AZIENDA USL DELLA ROMAGNA", "S", "Ravenna", 898, 398, 500, 715, [0]],
    [3, "aaaaaaaaa3", "COMUNE DI CESENA (FC)", "C", "Cesena", 4638, 2730, 1908, 2448, [0]],
    [4, "aaaaaaaaa4", "COMUNE DI CESENATICO (FC)", "C", "Cesenatico", 756, 453, 303, 396, [0]],
] + [[10 + k, f"bbbbbbbbb{k}", f"COMUNE DI PROVA {k} (FC)", "C", f"Prova {k}", 10 + k, 10 + k, 0, 5, [0]] for k in range(8)]
ELENCO = {"anno": 2023, "campi": ["id", "chiave", "nome", "gruppo", "sede", "beni", "fabbricati", "terreni", "particelle", "regioni"],
          "regioni": ["EMILIA ROMAGNA", "LAZIO"], "gruppi": GRUPPI, "enti": ENTI}
INDICE = {"anno": 2023, "enti": "/edifici3d/immobili_pa/enti_2023_prova.json", "gruppi": GRUPPI, "zoom_particelle": 13,
          "attribuzione": "prova", "beni": 10, "particelle": 5}


def _righe(k: int, n: int):
    """Righe dell'elenco dell'ente k: particelle con superfici diverse (per l'ordinamento) e un bene senza particella."""
    out = [{"ref": f"C573_00{k}{i:03d}.1", "lon": 12.24 + i * 0.001, "lat": 44.13 + k * 0.01, "n_beni": (i % 4) + 1,
            "sup_mq": 100.0 * ((i * 7) % 11), "area_m2": 900 + i, "comune": "Cesena" if i % 2 else "Cesenatico",
            "provincia": "FC", "regione": "EMILIA ROMAGNA", "indirizzo": f"Via {chr(65 + (i * 5) % 26)} {i}",
            "tipologie": "Edificio scolastico", "epoca": "Dal 1961 al 1970", "utilizzo": "Utilizzato direttamente",
            "titolo": "Piena proprietà", "ruoli": "P"} for i in range(n)]
    out.append({"ref": f"b{900 + k}", "lon": 12.3, "lat": 44.2, "n_beni": 1, "comune": "Cesena", "provincia": "FC",
                "regione": "EMILIA ROMAGNA", "tipologie": "Ospedale", "titolo": "in uso gratuito", "ruoli": "U"})
    return out


def _ente(e, filtri):
    k = e[0]
    grande = k == 3                                    # Comune di Cesena: più di 200 righe in due comuni → per comune
    n = 6 if not grande else 300
    tot = {"n_beni": e[5], "n_fabbricati": e[6], "n_terreni": 0, "n_particelle": e[8], "sup_fabbricati_mq": 1056089,
           "sup_terreni_mq": 0, "n_non_utilizzati": 10, "n_inutilizzabili": 2, "n_vincolati": 5, "n_detenzione": 1, "n_comuni": 2}
    comuni = [{"comune_cod": "C573", "comune": "Cesena", "provincia": "FC", "regione": "EMILIA ROMAGNA", "n_particelle": n - 20,
               "n_righe": n - 20, "n_beni": e[5] - 30, "sup_mq": 900000},
              {"comune_cod": "C574", "comune": "Cesenatico", "provincia": "FC", "regione": "EMILIA ROMAGNA", "n_particelle": 20,
               "n_righe": 21, "n_beni": 30, "sup_mq": 5000}]
    return {"chiave": e[1], "id": k, "nome": e[2], "tipologia_amm": "Comuni" if e[3] == "C" else "Universita'", "gruppo": e[3],
            "settore": "S13", "macrocategoria": "x", "sede": {"regione": "EMILIA ROMAGNA", "provincia": "FC", "comune": e[4].upper()},
            "totali_dichiarati": {**tot, "n_regioni": 2 if k == 1 else 1}, "totali": tot,
            "riquadro": [12.2, 44.1, 12.3, 44.2], "comuni": comuni}


def _gestore(chiamate):
    per = {e[1]: e for e in ENTI}

    def gestisci(route):
        u = urlparse(route.request.url)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        chiamate.append(u.path + ("?" + u.query if u.query else ""))
        p = u.path
        if p == "/edifici3d/immobili_pa/indice.json":
            return route.fulfill(json=INDICE)
        if p == "/edifici3d/immobili_pa/enti_2023_prova.json":
            return route.fulfill(json=ELENCO)
        m = re.fullmatch(r"/api/immobili-pa/ente/([0-9a-z,]+)(/punti|/beni)?", p)
        if m:
            chiavi = m.group(1).split(",")
            if any(c not in per for c in chiavi):
                return route.fulfill(status=404, json={"detail": "Ente non trovato"})
            e = per[chiavi[0]]
            if m.group(2) == "/punti":
                # terreni ogni tre righe (stile a righe), l'ultima riga in uso (stile trasparente)
                righe = [[r["lon"], r["lat"], r["n_beni"], "T" if i % 3 == 0 else "E", r["ruoli"], r["ref"]] for i, r in enumerate(_righe(e[0], 6))]
                return route.fulfill(json={"disponibile": True, "chiave": e[1], "id": e[0], "campi": ["lon", "lat", "n", "natura", "ruolo", "ref"], "righe": righe})
            if m.group(2) == "/beni":
                tutte = _righe(e[0], 300 if e[0] == 3 else 6)
                if q.get("comune"):
                    tutte = [r for r in tutte if (r["comune"] == "Cesena") == (q["comune"] == "C573")]
                if q.get("ordina"):
                    tutte.sort(key=lambda r: (r.get(q["ordina"]) is None, r.get(q["ordina"]) or 0), reverse=q.get("verso") == "desc")
                pp = min(200, int(q.get("per_pagina", 100))); pag = int(q.get("pagina", 1))
                return route.fulfill(json={"disponibile": True, "chiave": e[1], "totale": len(tutte), "pagina": pag, "per_pagina": pp,
                                           "pagine": -(-len(tutte) // pp), "righe": tutte[(pag - 1) * pp: pag * pp]})
            enti = [_ente(per[c], q) for c in chiavi]
            out = {"disponibile": True, "enti": enti, "filtri": {}}
            if len(enti) > 1:
                out["insieme"] = {**enti[0]["totali"], "n_beni": sum(x["totali"]["n_beni"] for x in enti) - 1}
            return route.fulfill(json=out)
        if p.startswith("/api/immobili-pa/particella/"):
            ref = p.rsplit("/", 1)[1]
            return route.fulfill(json={"particella": {"ref_ade": ref, "punto": [12.24, 44.13], "riquadro": [12.2, 44.1, 12.3, 44.2],
                                                      "area_m2": 900, "n_beni": 1},
                                       "beni": [{"id_bene": "1", "amministrazione": "COMUNE DI CESENA (FC)", "tipologia": "Edificio scolastico",
                                                 "natura": "FABBRICATO", "ente_chiave": "aaaaaaaaa3", "ruolo": "P",
                                                 "titolo_proprieta": "Proprietà", "superficie_mq": 1200, "sup_riferimento_mq": 1300},
                                                {"id_bene": "1", "amministrazione": "AZIENDA USL DELLA ROMAGNA", "tipologia": "Edificio scolastico",
                                                 "natura": "FABBRICATO", "ente_chiave": "aaaaaaaaa2", "ruolo": "U",
                                                 "titolo_detenzione": "in uso gratuito", "detenzione_intera": "Sì",
                                                 "ente_settore": "AMMINISTRAZIONI S13", "ente_macrocategoria": "Amministrazioni Locali",
                                                 "ente_sede": {"comune": "RAVENNA", "provincia": "RA", "regione": "EMILIA ROMAGNA"},
                                                 "sistema_catastale": "Ordinario", "geo_fonte": "IDENTIFICATIVI_CATASTALI",
                                                 "lat": 44.13, "lon": 12.24}]})
        return route.fulfill(status=404, json={"detail": "non simulata"})
    return gestisci


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


def _apri(browser, url, larghezza=1400, altezza=950):
    ctx = browser.new_context(viewport={"width": larghezza, "height": altezza})
    pg = ctx.new_page()
    errori, chiamate = [], []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    pg.route(lambda u: not u.startswith("http://127.0.0.1"), lambda r: r.abort())
    g = _gestore(chiamate)
    pg.route("**/api/**", g)
    pg.route("**/edifici3d/immobili_pa/**", g)
    pg.goto(url)
    pg.wait_for_function("() => window.EUGENIO_PUBBLICI_ENTI && window.EUGENIO_PUBBLICI_ENTI.stato.pronto", timeout=30000)
    pg.wait_for_selector("html[data-collegamento-pronto]", state="attached", timeout=30000)
    return ctx, pg, errori, chiamate


def _aggiungi(pg, testo):
    pg.fill("#cerca-ente", testo)
    pg.wait_for_selector("#proposte-enti li[id]")
    pg.keyboard.press("ArrowDown")
    assert pg.get_attribute("#cerca-ente", "aria-activedescendant") == "proposta-ente-0"
    pg.keyboard.press("Enter")


def test_ricerca_per_ente(browser, base):
    ctx, pg, errori, chiamate = _apri(browser, base + "edifici-pubblici.html?lat=44.14&lon=12.24&z=9")
    # schede del passo 1
    assert pg.get_attribute("#scheda-immobile", "aria-selected") == "true" and pg.is_hidden("#pannello-enti")
    pg.click("#scheda-enti")
    assert pg.get_attribute("#scheda-enti", "aria-selected") == "true" and pg.is_visible("#pannello-enti")
    assert pg.is_visible("#passo-elenco-enti") and pg.inner_text("#passo-elenco-enti h2 .n") == "2"
    assert pg.inner_text("#passo-livelli h2 .n") == "3"
    # filtro per tipologia: solo università
    assert "Università" in pg.inner_text("#tipo-ente")
    pg.fill("#cerca-ente", "bologna")
    pg.wait_for_selector("#proposte-enti li[id]")
    assert pg.get_attribute("#cerca-ente", "aria-expanded") == "true"
    prima = pg.inner_text("#proposte-enti li[id]")
    assert prima.startswith("Alma Mater Studiorum Università di Bologna") and "1.134 beni" in prima
    pg.keyboard.press("Escape")
    assert pg.get_attribute("#cerca-ente", "aria-expanded") == "false"
    # sigla: «ausl romagna», poi «cesena» (il comune prima di Cesenatico)
    _aggiungi(pg, "ausl romagna")
    pg.fill("#cerca-ente", "cesena")
    pg.wait_for_selector("#proposte-enti li[id]")
    assert pg.inner_text("#proposte-enti li[id]").startswith("Comune di Cesena (FC)")
    pg.keyboard.press("ArrowDown"); pg.keyboard.press("Enter")
    _aggiungi(pg, "alma mater")
    pg.wait_for_selector(".gruppo-ente >> nth=2")
    nomi = pg.eval_on_selector_all(".ente-scelto .ente-nome b", "bs => bs.map(b => b.textContent)")
    assert nomi == ["Azienda USL della Romagna", "Comune di Cesena (FC)", "Alma Mater Studiorum Università di Bologna"]
    colori = pg.eval_on_selector_all(".ente-scelto", "ls => ls.map(l => l.style.getPropertyValue('--colore-ente'))")
    assert colori == ["#0072B2", "#D55E00", "#009E73"]
    # totali con i numeri all'italiana e «insieme»
    pg.wait_for_selector(".totali-insieme")
    testo = pg.inner_text(".gruppo-ente >> nth=0")
    assert "1.056.089 m²" in testo and "1,3 %" in testo, testo[:600]
    assert "contati una volta" in pg.inner_text(".totali-insieme")
    # la prima chiamata dei totali porta i filtri predefiniti (solo proprietà, solo fabbricati)
    assert any("/api/immobili-pa/ente/aaaaaaaaa2,aaaaaaaaa3,aaaaaaaaa1?ruolo=proprieta&natura=E" in c for c in chiamate)
    # tabella dell'AUSL (7 righe, ordinata nel browser): crescente → decrescente → non ordinato
    t = pg.locator(".gruppo-ente").nth(0)
    t.locator("tbody tr").first.wait_for()
    partenza = t.locator("tbody tr td:nth-child(2)").all_inner_texts()
    th = t.locator("thead th", has_text="Superficie dichiarata")
    th.locator("button").click()
    assert th.get_attribute("aria-sort") == "ascending"
    sup = [x for x in t.locator("tbody tr td:nth-child(5)").all_inner_texts()]
    numeri = [int(x.replace(".", "")) for x in sup if x]
    assert numeri == sorted(numeri) and sup[-1] == ""                # vuoti in fondo
    th.locator("button").click()
    assert th.get_attribute("aria-sort") == "descending"
    numeri = [int(x.replace(".", "")) for x in t.locator("tbody tr td:nth-child(5)").all_inner_texts() if x]
    assert numeri == sorted(numeri, reverse=True) and t.locator("tbody tr td:nth-child(5)").all_inner_texts()[-1] == ""
    pg.wait_for_timeout(500)
    assert "ordina=sup_mq%3Adesc" in pg.input_value("#collegamento-indirizzo")
    th.locator("button").click()
    assert th.get_attribute("aria-sort") == "none" and t.locator("tbody tr td:nth-child(2)").all_inner_texts() == partenza
    # tastiera sull'intestazione
    t.locator("thead th", has_text="Unità").locator("button").focus()
    pg.keyboard.press("Enter")
    assert t.locator("thead th", has_text="Unità").get_attribute("aria-sort") == "ascending"
    # clic su una riga: scheda della particella e riga evidenziata
    t.locator("tbody tr").nth(1).click()
    pg.wait_for_selector("#scheda-pubblici .bene-pubblico")
    assert any(c.startswith("/api/immobili-pa/particella/") for c in chiamate)
    assert t.locator("tbody tr.evidenziata").count() == 1
    # Comune di Cesena: più di 200 righe in due comuni → elenco per comune; clic sul comune → pagine da 100
    c = pg.locator(".gruppo-ente").nth(1)
    assert "2 comuni" in c.inner_text()
    c.locator("tbody tr", has_text="Cesena").first.click()
    c.locator("nav.paginazione button", has_text="Successive").wait_for()
    assert "pagina 1 di 2" in c.inner_text() and c.locator("tbody tr").count() == 100
    c.locator("nav.paginazione button", has_text="Successive").click()
    pg.wait_for_function("() => document.querySelectorAll('.gruppo-ente')[1].innerText.includes('pagina 2 di 2')")
    assert any("comune=C573" in x and "pagina=2" in x for x in chiamate)
    # ordinamento fatto dal server per l'elenco paginato (l'ordinamento scelto nell'AUSL vale per tutti: Unità crescente)
    assert c.locator("thead th", has_text="Unità").get_attribute("aria-sort") == "ascending"
    c.locator("thead th", has_text="Unità").locator("button").click()
    pg.wait_for_timeout(600)
    assert c.locator("thead th", has_text="Unità").get_attribute("aria-sort") == "descending"
    assert any("comune=C573" in x and "ordina=n_beni&verso=desc" in x and "pagina=1" in x for x in chiamate)
    # collegamento: modo, enti nell'ordine (colori), ordinamento
    pg.wait_for_timeout(800)
    link = pg.input_value("#collegamento-indirizzo")
    assert "modo=enti" in link and "sel=aaaaaaaaa2%2Caaaaaaaaa3%2Caaaaaaaaa1" in link
    if PROVE.is_dir():
        pg.screenshot(path=str(PROVE / "prova_enti_test.png"))
    ctx.close()
    assert not errori, errori

    ctx, pg, errori2, chiamate = _apri(browser, link)
    pg.wait_for_selector(".gruppo-ente >> nth=2")
    assert pg.get_attribute("#scheda-enti", "aria-selected") == "true"
    assert pg.eval_on_selector_all(".ente-scelto", "ls => ls.map(l => l.style.getPropertyValue('--colore-ente'))") == ["#0072B2", "#D55E00", "#009E73"]
    assert pg.evaluate("() => EUGENIO_PUBBLICI_ENTI.stato.ordine.chiave") == "n_beni"
    # in uso acceso: va nell'indirizzo e nelle chiamate
    pg.check("#ruolo-enti input[value='uso']")
    pg.wait_for_timeout(900)
    assert "ruolo=proprieta%2Cuso" in pg.input_value("#collegamento-indirizzo")
    assert any("ruolo=proprieta%2Cuso" in x or "ruolo=proprieta,uso" in x for x in chiamate)
    # torna a «Cerca un immobile»: modo tolto dall'indirizzo, elenco nascosto
    pg.click("#scheda-immobile")
    pg.wait_for_timeout(700)
    assert pg.is_hidden("#passo-elenco-enti") and "modo=enti" not in pg.input_value("#collegamento-indirizzo")
    ctx.close()
    assert not errori2, errori2


def test_massimo_otto_e_togli(browser, base):
    ctx, pg, errori, _ = _apri(browser, base + "edifici-pubblici.html?modo=enti")
    assert pg.get_attribute("#scheda-enti", "aria-selected") == "true"
    for k in range(8):
        pg.evaluate(f"() => EUGENIO_PUBBLICI_ENTI.aggiungi('bbbbbbbbb{k}')")
    assert pg.locator(".ente-scelto").count() == 8 and pg.is_disabled("#cerca-ente")
    assert pg.evaluate("() => EUGENIO_PUBBLICI_ENTI.aggiungi('aaaaaaaaa1')") is False
    assert "Al massimo 8" in pg.inner_text("#messaggio-enti")
    # togliendo il secondo, il nuovo ente prende il suo colore (vermiglione)
    pg.click(".ente-scelto >> nth=1 >> button.togli-ente")
    pg.evaluate("() => EUGENIO_PUBBLICI_ENTI.aggiungi('aaaaaaaaa1')")
    assert pg.eval_on_selector(".ente-scelto:last-child", "l => l.style.getPropertyValue('--colore-ente')") == "#D55E00"
    pg.click("#togli-enti")
    assert pg.locator(".ente-scelto").count() == 0 and "Nessun ente scelto" in pg.inner_text("#elenco-enti")
    ctx.close()
    assert not errori, errori


def test_telefono(browser, base):
    ctx, pg, errori, _ = _apri(browser, base + "edifici-pubblici.html?modo=enti&sel=aaaaaaaaa2,aaaaaaaaa3", 375, 800)
    pg.wait_for_selector(".gruppo-ente >> nth=1")
    pg.wait_for_timeout(500)
    assert pg.evaluate("document.documentElement.scrollWidth") <= 376
    # le ultime colonne si nascondono sul telefono
    assert pg.locator(".gruppo-ente").first.locator("th.solo-largo").first.is_hidden()
    if PROVE.is_dir():
        pg.locator("#passo-cerca").scroll_into_view_if_needed()
        pg.screenshot(path=str(PROVE / "enti_telefono.png"))
    ctx.close()
    assert not errori, errori


def test_scheda_sopra_e_stili(browser, base):
    """Scheda in sovraimpressione (22/11/2026 sera): clic su una riga → riquadro sopra la mappa con tutti i dati (prima i
    beni degli enti scelti), chiuso con Esc, clic fuori e ×; stili proprietà / uso / terreni nei pallini, nella legenda e
    nelle righe dell'immagine; sul telefono il riquadro è a tutta larghezza in basso."""
    url = base + "edifici-pubblici.html?modo=enti&sel=aaaaaaaaa2&ruolo=proprieta,uso&natura=E,T"
    ctx, pg, errori, _ = _apri(browser, url)
    pg.wait_for_selector(".gruppo-ente tbody tr")
    assert pg.is_hidden("#scheda-sopra")
    riga = pg.locator(".gruppo-ente tbody tr").nth(1)
    riga.click()
    pg.wait_for_selector("#scheda-sopra:not([hidden]) .bene-pubblico")
    testo = pg.inner_text("#scheda-sopra")
    assert pg.inner_text("#titolo-scheda-sopra").startswith("Particella ")
    # tutti i campi pubblicabili, con il bene dell'ente scelto per primo; mai cedente né codici fiscali
    primo = pg.locator("#scheda-sopra .bene-pubblico").first.inner_text()
    assert "Azienda USL della Romagna" in primo and "in uso (detenzione)" in primo and "colore blu" in primo
    for t in ("Settore e macrocategoria", "Amministrazioni S13", "Sede dell'ente", "Ravenna (RA) – Emilia Romagna",
              "Detenzione dell'intera unità", "Sistema catastale", "dagli identificativi catastali", "Superficie di riferimento",
              "1.300 m²", "Identificativo del bene"):
        assert t in testo, t
    assert "cedente" not in testo.lower()
    # il riquadro sta sopra la mappa, in alto a sinistra, e lascia liberi i comandi a destra
    sopra, mappa = pg.locator("#scheda-sopra").bounding_box(), pg.locator("#mappa-pubblici").bounding_box()
    assert abs(sopra["x"] - mappa["x"] - 10) < 2 and sopra["x"] + sopra["width"] < mappa["x"] + mappa["width"] - 60
    assert sopra["y"] + sopra["height"] < mappa["y"] + mappa["height"] - 40
    # Esc chiude e il fuoco torna alla riga
    pg.keyboard.press("Escape")
    assert pg.is_hidden("#scheda-sopra")
    riga.click(); pg.wait_for_selector("#scheda-sopra:not([hidden]) .bene-pubblico")
    pg.click("h1"); pg.wait_for_timeout(200)                     # clic fuori
    assert pg.is_hidden("#scheda-sopra")
    riga.click(); pg.wait_for_selector("#scheda-sopra:not([hidden]) .bene-pubblico")
    pg.click("#chiudi-scheda-sopra")
    assert pg.is_hidden("#scheda-sopra")
    # stili dei pallini: proprietà pieni, uso ad anello, terreni a righe (icone)
    stili = pg.evaluate("""() => { const m = EUGENIO_PUBBLICI.stato.mappa, id = 'pe-aaaaaaaaa2';
      const d = m.getSource(id).serialize().data.features.map(f => f.properties);
      return { uso: d.filter(p => p.u === 1).length, terreni: d.filter(p => p.ter === 1).length,
        icona: JSON.stringify(m.getLayoutProperty(id + '-righe', 'icon-image')), opacita: JSON.stringify(m.getPaintProperty(id + '-pallini', 'circle-opacity')),
        immagini: ['pallino-terreno-0-p', 'pallino-terreno-0-u', 'terreno-ente-0'].every(n => m.hasImage(n)) }; }""")
    assert stili["uso"] >= 1 and stili["terreni"] >= 1 and stili["immagini"], stili
    assert "pallino-terreno-0-u" in stili["icona"] and "case" in stili["opacita"]
    # legenda con i tre stili e righe dell'immagine
    assert pg.locator("#legenda-enti [data-stile]").count() == 3
    assert pg.locator("#legenda-enti [data-stile] canvas").count() == 6
    righe = " ".join(pg.evaluate("() => EUGENIO_PUBBLICI.opzioniImmagine().righe"))
    assert "colore pieno: in proprietà" in righe and "trasparente" in righe and "righe chiare e scure: terreni" in righe
    # passando a «Cerca un immobile» il riquadro si chiude
    riga.click(); pg.wait_for_selector("#scheda-sopra:not([hidden]) .bene-pubblico")
    pg.click("#scheda-immobile")
    assert pg.is_hidden("#scheda-sopra")
    if PROVE.is_dir():
        pg.screenshot(path=str(PROVE / "enti2_test_scheda.png"))
    ctx.close()
    assert not errori, errori
    # telefono: a tutta larghezza in basso, senza scorrimento orizzontale
    ctx, pg, errori, _ = _apri(browser, url, 375, 800)
    pg.wait_for_selector(".gruppo-ente tbody tr")
    pg.locator(".gruppo-ente tbody tr").nth(1).click()
    pg.wait_for_selector("#scheda-sopra:not([hidden]) .bene-pubblico")
    r = pg.evaluate("() => { const r = document.getElementById('scheda-sopra').getBoundingClientRect(); return [r.left, r.right, r.bottom, r.height]; }")
    assert r[0] == 0 and r[1] == 375 and abs(r[2] - 800) < 1 and r[3] <= 0.63 * 800, r
    assert pg.evaluate("document.documentElement.scrollWidth") <= 376
    ctx.close()
    assert not errori, errori


def test_indice_vecchio(browser, base):
    """indice.json senza «enti» (dati preparati prima del 22/11/2026): messaggio chiaro e nessun errore."""
    ctx = browser.new_context(viewport={"width": 1200, "height": 900})
    pg = ctx.new_page()
    errori = []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    pg.route(lambda u: not u.startswith("http://127.0.0.1"), lambda r: r.abort())
    pg.route("**/edifici3d/immobili_pa/indice.json", lambda r: r.fulfill(json={k: v for k, v in INDICE.items() if k != "enti"}))
    pg.route("**/api/**", lambda r: r.fulfill(status=404, json={"detail": "x"}))
    pg.goto(base + "edifici-pubblici.html?modo=enti&sel=aaaaaaaaa3")
    pg.wait_for_function("() => window.EUGENIO_PUBBLICI_ENTI && window.EUGENIO_PUBBLICI_ENTI.stato.pronto", timeout=30000)
    pg.wait_for_timeout(500)
    assert "non è ancora disponibile" in pg.inner_text("#messaggio-enti") and pg.is_disabled("#cerca-ente")
    ctx.close()
    assert not errori, errori
