"""Prove nel browser della ricerca di un luogo (17/11/2026, segnalazione di Paolo; cerca_luogo.js con `luogo=1`):
civico → segnaposto nella particella catastale e particella (con gli altri accessi dello stesso civico) tutta nella vista;
via senza civico → mappa centrata a metà della via con la via nella vista; più vie compatibili → elenco da scegliere, la
mappa non si muove finché non si sceglie; risposta di un server senza i campi nuovi → come prima. Risposte di
/api/patrimonio simulate con i numeri delle prove dal vivo del 17/11/2026 (Rimini, Perugia); nessuna rete. Si salta senza
Playwright o Chromium."""
from __future__ import annotations

import json

import pytest

pytest.importorskip("playwright.sync_api")

from test_mappe_browser import attendi, base, browser, pagina, webgl   # noqa: E402,F401

ORTO = "window.EUGENIO_ORTOFOTO.stato"
M3D = "window.EUGENIO_EDIFICIO3D.stato"
CATASTO = "Agenzia delle Entrate – Cartografia catastale (CC BY 4.0)"
OSM = "© OpenStreetMap contributors (ODbL 1.0)"
OSPEDALE = (12.5879, 44.0459)                  # ospedale Infermi (OpenStreetMap), Rimini

SETTEMBRINI = {"id": "1", "metodo": "indirizzo", "lat": 44.042903, "lon": 12.589748, "esito": "ok", "fonte_punto": "ANNCSU",
               "indirizzo_trovato": "VIALE LUIGI SETTEMBRINI 2", "comune_catasto": "RIMINI", "foglio_catasto": "99",
               "mappale": "2330", "nota": "", "luogo_tipo": "particella", "luogo_lat": 44.0465629, "luogo_lon": 12.5879915,
               "luogo_riquadro": [12.585209, 44.044708, 12.5909451, 44.0488949], "luogo_fonte": CATASTO, "luogo_avviso": "",
               "luogo_regola": "particella_piu_grande_del_civico",
               "particella_ade": {"riferimento": "H294_009900.1", "foglio": "99", "mappale": "1", "belfiore": "H294",
                                  "area_m2": 105819}, "vie_candidate": [], "scegli_via": False, "via_scelta": None}
CORIANO_SCELTA = {"nome": "Via Coriano", "tipo": "via", "lat": 44.0171787, "lon": 12.5939421,
                  "riquadro": [12.5758227, 43.9905919, 12.6040566, 44.0417247], "lunghezza_m": 8724, "fonte": OSM,
                  "punteggio": 1.05, "civici": 342, "etichetta": "Via Coriano (8,7 km, 342 civici)"}
CORIANO = {"id": "1", "metodo": "indirizzo", "lat": 44.015966, "lon": 12.595084, "esito": "verificare", "fonte_punto": "ANNCSU",
           "indirizzo_trovato": "VIA CORIANO 210/I", "comune_catasto": "RIMINI", "nota": "civico non indicato: usato il 210 di VIA CORIANO",
           "luogo_tipo": "via", "luogo_lat": 44.0171787, "luogo_lon": 12.5939421,
           "luogo_riquadro": [12.5758227, 43.9905919, 12.6040566, 44.0417247], "luogo_fonte": OSM, "luogo_avviso": "",
           "via_scelta": CORIANO_SCELTA, "scegli_via": False,
           "vie_candidate": [{"nome": "VIA CORCIANO", "tipo": "via", "lat": 44.0121092, "lon": 12.6036941,
                              "riquadro": [12.599562, 44.011114, 12.609251, 44.0151], "lunghezza_m": 789, "civici": 56,
                              "fonte": "ANNCSU – Agenzia delle Entrate e ISTAT (CC BY 4.0)", "punteggio": 0.703,
                              "etichetta": "VIA CORCIANO (789 m, 56 civici)"}]}
FRATTE = {"id": "1", "metodo": "indirizzo", "lat": 43.0951, "lon": 12.3381, "esito": "verificare", "fonte_punto": "Zornade",
          "indirizzo_trovato": "Via Sant'Andrea, Perugia", "comune_catasto": "PERUGIA", "nota": "", "luogo_tipo": None,
          "luogo_lat": None, "luogo_lon": None, "luogo_riquadro": None, "scegli_via": True, "via_scelta": None, "luogo_avviso": "",
          "vie_candidate": [
              {"nome": "Sant'Andrea delle Fratte", "tipo": "località", "lat": 43.0743033, "lon": 12.3382, "riquadro": None,
               "fonte": OSM, "punteggio": 0.79, "etichetta": "Sant'Andrea delle Fratte (località)"},
              {"nome": "Strada delle Fratte", "tipo": "via", "lat": 43.0717351, "lon": 12.3218663,
               "riquadro": [12.3200, 43.0705, 12.3236, 43.0730], "lunghezza_m": 614, "civici": 68, "fonte": OSM,
               "punteggio": 0.3, "etichetta": "Strada delle Fratte (614 m, 68 civici)"}]}


def _servi(pg, righe, mandati):
    def patrimonio(r):
        mandati.append(r.request.post_data or "")
        r.fulfill(status=200, content_type="application/json", body=json.dumps({"righe": [righe[len(mandati) - 1]]}))
    pg.route("**/api/patrimonio", patrimonio)


def _vista(pg, st):
    return pg.evaluate(f"(() => {{ const m = {st}.mappa, b = m.getBounds(), c = m.getCenter(); return {{ zoom: m.getZoom(), "
                       "c: [c.lng, c.lat], b: [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()] }; })()")


def _dentro(b, lon, lat):
    return b[0] <= lon <= b[2] and b[1] <= lat <= b[3]


def test_ortofoto_civico_particella_e_via(browser, base):
    ctx, pg = pagina(browser)
    mandati = []
    _servi(pg, [SETTEMBRINI, CORIANO, {**CORIANO_SCELTA}], mandati)
    pg.goto(base + "ortofoto.html?lat=44.0594&lon=12.5683&z=15")
    webgl(pg)
    attendi(pg, f"window.EUGENIO_ORTOFOTO && {ORTO}.mappa && {ORTO}.mappa.loaded() && !!document.getElementById('cerca-comune')", 30000)
    # civico con più accessi: segnaposto nella particella più grande (n. 1, l'ospedale), tutta nella vista (scelta B)
    pg.fill("#cerca-comune", "Rimini"); pg.fill("#cerca-via", "via Settembrini 2")
    pg.click("#cerca-indirizzo")
    attendi(pg, f"/particella foglio 99, 1 /.test(document.getElementById('messaggio-cerca').textContent) && !{ORTO}.mappa.isMoving()")
    assert 'name="luogo"' in mandati[0] and "\r\n\r\n1\r\n" in mandati[0]          # campo luogo=1 nella richiesta
    v = _vista(pg, ORTO)
    r = SETTEMBRINI["luogo_riquadro"]
    assert _dentro(v["b"], r[0], r[1]) and _dentro(v["b"], r[2], r[3]), v
    assert _dentro(v["b"], *OSPEDALE), v                                        # prima restava fuori (zoom 17 sul «2»)
    assert v["zoom"] > 15.5, v
    seg = pg.evaluate(f"{ORTO}.mappa.getSource('cercato').serialize().data.features[0].geometry.coordinates")
    assert seg == pytest.approx([12.5879915, 44.0465629])
    msg = pg.text_content("#messaggio-cerca")
    assert CATASTO in msg and "ANNCSU" in msg and "(105.819 m²), la più grande fra quelle degli accessi del civico" in msg, msg
    assert "Agenzia delle Entrate – Cartografia catastale" in pg.evaluate(f"{ORTO}.cercato")
    # via senza civico: centrata a metà della via, la via (8,7 km di strade) nella vista; «altre vie simili» da scegliere
    pg.fill("#cerca-via", "via Coriano")
    pg.click("#cerca-indirizzo")
    attendi(pg, f"/metà della via \\(8,7 km\\)/.test(document.getElementById('messaggio-cerca').textContent) && !{ORTO}.mappa.isMoving()")
    v = _vista(pg, ORTO)
    assert v["c"] == pytest.approx([12.5939421, 44.0171787], abs=2e-4), v
    r = CORIANO["luogo_riquadro"]
    assert _dentro(v["b"], r[0], r[1]) and _dentro(v["b"], r[2], r[3]), v
    assert 12 < v["zoom"] < 14.5, v
    msg = pg.text_content("#messaggio-cerca")
    assert OSM in msg and "civico non indicato" not in msg and "VIA CORCIANO (789 m, 56 civici)" in msg, msg
    pg.click("#messaggio-cerca .cerca-scelte button")
    attendi(pg, f"Math.abs({ORTO}.mappa.getCenter().lng - 12.6036941) < 3e-4 && !{ORTO}.mappa.isMoving()")
    assert len(mandati) == 2                                                    # la scelta non richiama il server
    assert not pg.errori, pg.errori
    ctx.close()


def test_modelli3d_vie_da_scegliere(browser, base):
    """Perugia, «via Sant'Andrea delle Fratte»: è una frazione; prima Zornade portava 2,5 km più a nord senza avviso. Ora
    l'elenco (località, vie simili, il punto di Zornade) e la mappa ferma finché non si sceglie."""
    ctx, pg = pagina(browser)
    mandati = []
    _servi(pg, [FRATTE], mandati)
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {M3D}.mappa && {M3D}.mappa.loaded() && !!document.getElementById('cerca-comune')", 30000)
    prima = _vista(pg, M3D)
    pg.fill("#cerca-comune", "Perugia"); pg.fill("#cerca-via", "via Sant'Andrea delle Fratte")
    pg.click("#cerca-indirizzo")
    attendi(pg, "document.querySelectorAll('#messaggio-cerca .cerca-scelte button').length === 3")
    testi = pg.evaluate("[...document.querySelectorAll('#messaggio-cerca .cerca-scelte button')].map((b) => b.textContent)")
    assert testi == ["Sant'Andrea delle Fratte (località)", "Strada delle Fratte (614 m, 68 civici)",
                     "Punto trovato: Via Sant'Andrea, Perugia (Zornade)"], testi
    assert "non è una sola via a Perugia" in pg.text_content("#messaggio-cerca")
    pg.wait_for_timeout(300)
    assert _vista(pg, M3D)["c"] == pytest.approx(prima["c"], abs=1e-6)          # la mappa non si è mossa
    pg.click("#messaggio-cerca .cerca-scelte button >> nth=0")
    attendi(pg, f"Math.abs({M3D}.mappa.getCenter().lat - 43.0743033) < 2e-4 && !{M3D}.mappa.isMoving()")
    assert abs(pg.evaluate(f"{M3D}.mappa.getZoom()") - 15) < 0.05
    assert pg.evaluate(f"{M3D}.punto.fonte") == OSM
    assert "Scelta: Sant'Andrea delle Fratte (località)" in pg.text_content("#messaggio-cerca")
    assert not pg.errori, pg.errori
    ctx.close()


def test_server_senza_i_campi_nuovi_come_prima(browser, base):
    """Risposta senza luogo_* (server non aggiornato, LUOGO=false): punto e zoom 17 come prima."""
    ctx, pg = pagina(browser)
    vecchia = {k: v for k, v in SETTEMBRINI.items() if not k.startswith(("luogo_", "particella_ade", "vie_", "scegli", "via_"))}
    _servi(pg, [vecchia], [])
    pg.goto(base + "ortofoto.html?lat=44.0594&lon=12.5683&z=15")
    webgl(pg)
    attendi(pg, f"window.EUGENIO_ORTOFOTO && {ORTO}.mappa && {ORTO}.mappa.loaded() && !!document.getElementById('cerca-comune')", 30000)
    pg.fill("#cerca-comune", "Rimini"); pg.fill("#cerca-via", "via Settembrini 2")
    pg.click("#cerca-indirizzo")
    attendi(pg, f"/ANNCSU/.test(document.getElementById('messaggio-cerca').textContent) && Math.abs({ORTO}.mappa.getCenter().lat - 44.042903) < 1e-4 && !{ORTO}.mappa.isMoving()")
    assert abs(pg.evaluate(f"{ORTO}.mappa.getZoom()") - 17) < 0.05
    assert not pg.errori, pg.errori
    ctx.close()
