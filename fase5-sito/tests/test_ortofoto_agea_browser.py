"""Prove nel browser (Chromium headless, Playwright) delle ortofoto AGEA 2022-2024 (17/11/2026).

Una sola fonte «agea» con più anni: il server dice in X-Ortofoto-Anno l'anno di volo di ogni tessera; protezione.js li
raccoglie e la citazione sotto la mappa e nell'immagine scaricata dice gli anni veri della vista. Scelta automatica:
in Emilia-Romagna resta la RER 2023-24 (regionale, priorità 1), a Milano AGEA. Le rotte /api/ sono simulate (nessuna
rete). Si salta se Playwright o Chromium non ci sono.
"""
from __future__ import annotations

import io
import json
import re

import pytest

pytest.importorskip("playwright.sync_api")

from test_mappe_browser import attendi, base, browser, webgl  # noqa: E402,F401  (fixture condivise)

AGEA = {"id": "agea", "nome": "AGEA – ortofoto RGB 2022-2024 (20 cm, anno più recente)", "licenza": "CC BY 4.0",
        "citazione": "AGEA – Agenzia per le Erogazioni in Agricoltura, ortofoto RGB 2022-2024 (CC BY 4.0)",
        "citazione_anni": "AGEA – Agenzia per le Erogazioni in Agricoltura, ortofoto RGB {anni} (CC BY 4.0)",
        "anni": [2024, 2023, 2022], "scheda": "https://geoportale.agea.gov.it/legal-notes", "stato": "confermata",
        "regione": "00", "copia": True, "nei_report": True, "zoom": [10, 19], "riquadro": [6.6, 35.4, 18.6, 47.1],
        "priorita": 2, "tessere": "/api/ortofoto/agea/{z}/{x}/{y}.jpg", "spostabile": False, "spostamento_max": 0}
FONTI = {"fonti": [
    {"id": "rer2023", "nome": "Ortofoto RER 2023-24 (20 cm)", "licenza": "CC BY 4.0", "citazione": "Regione Emilia-Romagna – Ortofoto RER 2023-24 (CC BY 4.0)",
     "scheda": "https://geoportale.regione.emilia-romagna.it/", "stato": "da confermare", "regione": "08", "copia": True, "nei_report": True,
     "zoom": [12, 19], "riquadro": [9.19, 43.73, 12.84, 45.16], "priorita": 1, "tessere": "/api/ortofoto/rer2023/{z}/{x}/{y}.jpg?t=1",
     "spostabile": True, "spostamento_max": 20},
    AGEA,
    {"id": "pcn2012", "nome": "Geoportale Nazionale (solo consultazione)", "licenza": "da verificare", "citazione": "Geoportale Nazionale – AGEA 2012",
     "scheda": "https://gn.mase.gov.it/", "stato": "confermata", "regione": "00", "copia": False, "nei_report": False, "zoom": [12, 18],
     "riquadro": [6.6, 35.4, 18.6, 47.1], "priorita": 8, "tessere": "/api/ortofoto/pcn2012/{z}/{x}/{y}.jpg", "spostabile": True, "spostamento_max": 20},
    {"id": "s2cloudless2016", "nome": "Sentinel-2 cloudless 2016 (10 m)", "licenza": "CC BY 4.0", "citazione": "Sentinel-2 cloudless – EOX (2016)",
     "scheda": "https://cloudless.eox.at/", "stato": "confermata", "regione": "00", "copia": True, "nei_report": True, "zoom": [5, 15],
     "riquadro": [6.6, 35.4, 18.6, 47.1], "priorita": 9, "tessere": "/api/ortofoto/s2cloudless2016/{z}/{x}/{y}.jpg", "spostabile": False, "spostamento_max": 0}]}


def _jpeg():
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (256, 256), (90, 120, 70)).save(b, "JPEG")
    return b.getvalue()


def pagina(browser, anno_di):
    """Pagina con le fonti simulate; `anno_di(x)` dà X-Ortofoto-Anno della tessera AGEA di colonna x."""
    ctx = browser.new_context(viewport={"width": 1366, "height": 900}, accept_downloads=True)
    ctx.add_init_script("try { delete window.showSaveFilePicker; window.showSaveFilePicker = undefined; } catch (e) {}")
    pg = ctx.new_page()
    pg.errori, pg.agea = [], []
    pg.on("pageerror", lambda e: pg.errori.append(str(e)))
    foto = _jpeg()

    def tessera(r):
        m = re.search(r"/api/ortofoto/agea/(\d+)/(\d+)/(\d+)\.jpg", r.request.url)
        pg.agea.append(tuple(map(int, m.groups())))
        r.fulfill(status=200, body=foto, headers={"Content-Type": "image/jpeg", "X-Ortofoto-Fonte": "agea",
                                                  "X-Ortofoto-Anno": anno_di(int(m.group(2)))})

    pg.route("**/api/**", lambda r: r.fulfill(status=404, body="{}"))
    pg.route("**/api/ortofoto/fonti", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(FONTI)))
    pg.route(re.compile(r".*/api/ortofoto/agea/\d+/\d+/\d+\.jpg.*"), tessera)
    pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), lambda r: r.fulfill(status=404, body="{}"))
    return ctx, pg


ST = "window.EUGENIO_ORTOFOTO.stato"


def test_citazione_con_l_anno_vero_della_vista(browser, base, tmp_path):
    # Milano: fuori dall'Emilia-Romagna la scelta automatica è AGEA (prima di AGEA 2012 e Sentinel-2); anno 2024
    ctx, pg = pagina(browser, lambda x: "2024")
    pg.goto(base + "ortofoto.html?lat=45.4642&lon=9.19&z=16")
    webgl(pg)
    attendi(pg, f"window.EUGENIO_ORTOFOTO && {ST}.scelta && {ST}.scelta.id === 'agea'", 30000)
    attendi(pg, "/ortofoto RGB 2024 \\(CC BY 4\\.0\\)/.test(document.getElementById('attribuzione').textContent)", 20000)
    assert pg.agea and all(10 <= z <= 19 for z, _, _ in pg.agea)
    att = pg.locator("#attribuzione").text_content()
    assert "2022-2024" not in att and "licenza CC BY 4.0" in att and "Solo consultazione" not in att
    righe = pg.evaluate("window.EUGENIO_ORTOFOTO.opzioniImmagine().righe")
    assert any("AGEA – Agenzia per le Erogazioni in Agricoltura, ortofoto RGB 2024 (CC BY 4.0)" in r for r in righe), righe
    # l'immagine si scarica (fonte con copia) e dentro c'è l'anno
    with pg.expect_download() as d:
        pg.evaluate("document.querySelector('#scarica-ortofoto button[data-formato=\"pdf\"]').click()")
    dest = tmp_path / "vista.pdf"; d.value.save_as(dest)
    assert b"2024" in dest.read_bytes()
    assert not pg.errori, pg.errori
    ctx.close()


def test_confine_tra_anni_e_scelta_regionale(browser, base):
    # confine tra due anni nella stessa vista (colonne pari 2023, dispari 2022 e 2023 composte): «2022 e 2023»
    ctx, pg = pagina(browser, lambda x: "2023" if x % 2 == 0 else "2023,2022")
    pg.goto(base + "ortofoto.html?lat=43.966&lon=12.757&z=15&fonte=agea")
    webgl(pg)
    attendi(pg, f"window.EUGENIO_ORTOFOTO && {ST}.scelta && {ST}.scelta.id === 'agea'", 30000)
    attendi(pg, "/ortofoto RGB 2022 e 2023 \\(CC BY 4\\.0\\)/.test(document.getElementById('attribuzione').textContent)", 20000)
    # le funzioni comuni: anni noti per fonte, solo nella vista
    assert pg.evaluate("window.EUGENIO_ORTOFOTO_ANNI.testoAnni([2024, 2022, 2022])") == "2022 e 2024"
    assert pg.evaluate("window.EUGENIO_ORTOFOTO_ANNI.anniNelRiquadro('agea', [0, 0, 1, 1], 0, 22)") == []
    assert pg.evaluate("window.EUGENIO_ORTOFOTO_ANNI.citazione({id: 'x', citazione: 'Fonte com\\'è'}, null)") == "Fonte com'è"
    # in Emilia-Romagna, senza scelta a mano, la RER 2023-24 (regionale) resta davanti ad AGEA
    pg.evaluate(f"{ST}.manuale = false; {ST}.mappa.jumpTo({{center: [12.5683, 44.0594], zoom: 16}})")
    attendi(pg, f"{ST}.scelta && {ST}.scelta.id === 'rer2023'", 20000)
    nomi = pg.evaluate("[...document.querySelectorAll('#fonti input[name=\"fonte\"]')].map((i) => i.value)")
    assert nomi.index("rer2023") < nomi.index("agea") < nomi.index("pcn2012"), nomi
    assert not pg.errori, pg.errori
    ctx.close()
