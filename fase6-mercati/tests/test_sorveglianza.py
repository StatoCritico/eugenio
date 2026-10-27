"""Sorveglianza delle fonti delle convenzioni, con un sito simulato che cambia da una notte all'altra."""
import datetime as dt
import tomllib

import httpx

from mercati_energia import convenzioni, sorveglianza as S

TOML = """# Convenzione di prova
[convenzione]
id = "prova-ee"
ente = "Centrale di prova"
commodity = "elettricita"
dal = 2027-01-01
al = 2027-12-31

[[lotto]]
id = "1"
regola_prezzo = "indice_piu_spread"
fasce = ["F1", "F2", "F3"]
indice = "PUN_FASCE"
spread = 2.00                        # €/MWh; listino di prova
perdite = 0.038

[[lotto]]
id = "2"
regola_prezzo = "indice_piu_spread"
fasce = ["F0"]
indice = "PUN_FASCE"
spread = 3.00                        # €/MWh
[lotto.corrispettivi]
fisso_pod_anno = 0                   # nessun corrispettivo fisso

[sorveglianza]
pagine = ["https://centrale.test/convenzioni/ee-2027"]

[[sorveglianza.valore]]
lotto = "1"
campo = "spread"
cerca = 'Lotto 1[^\\n]*?spread[^0-9]*({n})'
applica = true

[[sorveglianza.valore]]
lotto = "2"
campo = "spread"
cerca = 'Lotto 2[^\\n]*?spread[^0-9]*({n})'
""".replace("{n}", S.NUMERO)

CENTRALI = """
[[fonte]]
id = "centrale-elenco"
centrale = "Centrale di prova"
tipo = "elenco"
url = "https://centrale.test/convenzioni/"
"""


def _sito(notte):
    pagina_conv = {1: '<main><h1>EE 2027</h1><a href="/doc/capitolato.pdf">Capitolato</a></main>',
                   2: '<main><h1>EE 2027</h1><a href="/doc/capitolato.pdf">Capitolato</a>'
                      '<a href="/doc/listino_ee_2027.csv">Listino prezzi</a><a href="/doc/foto.jpg">Foto</a></main>'}
    elenco = {1: '<main><a href="/convenzioni/ee-2027">Energia elettrica 2027</a></main>',
              2: '<main><a href="/convenzioni/ee-2027">Energia elettrica 2027</a>'
                 '<a href="/convenzioni/gas-2027-28">Gas naturale 2027/28</a><a href="/news/1">Cancelleria</a></main>'}
    chiamate = []

    def risposta(req):
        chiamate.append(str(req.url))
        p = req.url.path
        if p == "/convenzioni/ee-2027":
            return httpx.Response(200, text=pagina_conv[notte[0]])
        if p == "/convenzioni/":
            return httpx.Response(200, text=elenco[notte[0]])
        if p == "/doc/capitolato.pdf":
            return httpx.Response(200, content=b"non un vero pdf")
        if p == "/doc/listino_ee_2027.csv":
            return httpx.Response(200, text="Lotto 1 - spread unico 2,44 EUR/MWh\nLotto 2 - spread 3,47 EUR/MWh\n")
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(risposta)), chiamate


def test_sorveglianza_due_notti(tmp_path):
    conv = tmp_path / "convenzioni"
    (conv / "fonti").mkdir(parents=True)
    (conv / "prova.toml").write_text(TOML, encoding="utf-8")
    (conv / "fonti" / "centrali.toml").write_text(CENTRALI, encoding="utf-8")
    arch = tmp_path / "archivio"
    notte = [1]
    cl, chiamate = _sito(notte)

    e1 = S.Sorveglianza(arch, conv, client=cl, oggi=dt.date(2026, 11, 3)).esegui()
    assert e1["controllate"] == 2 and not e1["da_segnalare"]       # prima notte: solo la base di confronto
    assert any(u.endswith("capitolato.pdf") for u in chiamate)       # documento scaricato in silenzio

    notte[0] = 2
    e2 = S.Sorveglianza(arch, conv, client=cl, oggi=dt.date(2026, 11, 4)).esegui()
    assert [g["titolo"] for g in e2["nuove_gare"]] == ["Gas naturale 2027/28"]   # "Cancelleria" no
    assert [d["titolo"] for d in e2["documenti_nuovi"]] == ["Listino prezzi"]    # la foto no
    assert not any(u.endswith("foto.jpg") for u in chiamate)
    # lotto 1: applica = true → aggiornato nel file, con commento e copia di sicurezza
    assert [(v["lotto"], v["trovati"]) for v in e2["valori_aggiornati"]] == [("1", [2.44])]
    nuovo = (conv / "prova.toml").read_text(encoding="utf-8")
    assert "spread = 2.44" in nuovo and "prima: 2.00" in nuovo and "# Convenzione di prova" in nuovo
    assert convenzioni.carica(conv / "prova.toml").lotto("1").spread == {"F1": 2.44, "F2": 2.44, "F3": 2.44}
    assert list((arch / "sorveglianza" / "copie_toml").glob("prova.*.toml"))
    # lotto 2: senza applica → solo proposto
    assert [(v["lotto"], v["nel_file"], v["trovati"]) for v in e2["proposte"]] == [("2", 3.0, [3.47])]
    assert tomllib.loads(nuovo)["lotto"][1]["spread"] == 3.0
    testo = S.riepilogo(e2)
    assert "VALORI AGGIORNATI" in testo and "DA CONTROLLARE" in testo and "Gas naturale 2027/28" in testo

    # terza notte, niente di nuovo: niente da segnalare (la proposta del lotto 2 non si ripete)
    e3 = S.Sorveglianza(arch, conv, client=cl, oggi=dt.date(2026, 11, 5)).esegui()
    assert not e3["da_segnalare"], S.riepilogo(e3)


def test_pagina_che_non_risponde(tmp_path):
    conv = tmp_path / "convenzioni"
    (conv / "fonti").mkdir(parents=True)
    (conv / "fonti" / "centrali.toml").write_text(CENTRALI, encoding="utf-8")
    cl = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    notti = [S.Sorveglianza(tmp_path, conv, client=cl, oggi=dt.date(2026, 11, g)).esegui() for g in range(1, 12)]
    segnalate = [i + 1 for i, e in enumerate(notti) if e["pagine_in_errore"]]
    assert segnalate == [3, 10]                    # alla terza notte, poi una volta a settimana


def test_imposta_valore_in_sottotabella(tmp_path):
    f = tmp_path / "c.toml"
    f.write_text(TOML, encoding="utf-8")
    S.imposta_valore(f, "2", "corrispettivi.fisso_pod_anno", 12.5, "prova")
    raw = tomllib.loads(f.read_text(encoding="utf-8"))
    assert raw["lotto"][1]["corrispettivi"]["fisso_pod_anno"] == 12.5 and raw["lotto"][0]["spread"] == 2.0
    assert S.valore_attuale(f, "1", "spread") == 2.0


def test_psv_mancante(tmp_path):
    conv = tmp_path / "convenzioni"
    conv.mkdir()
    cl = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    e = S.Sorveglianza(tmp_path, conv, client=cl, oggi=dt.date(2026, 12, 9)).esegui(tmp_path)
    assert e["avvisi"] and "2026-11" in e["avvisi"][0]
    e = S.Sorveglianza(tmp_path, conv, client=cl, oggi=dt.date(2026, 12, 10)).esegui(tmp_path)
    assert not e["avvisi"]                          # una volta sola per mese


def test_convenzioni_reali_si_caricano():
    """Le sezioni [sorveglianza] dei file veri sono lette e le regex compilano."""
    import re
    from pathlib import Path
    cartella = Path(__file__).parent.parent / "convenzioni"
    fonti, regole = S.carica_fonti(cartella)
    assert fonti and all(f.url.startswith("https://") for f in fonti)
    for g in regole:
        re.compile(g.cerca)
        assert S.valore_attuale(g.file, g.lotto, g.campo) is not None
    assert len(convenzioni.carica_tutte(cartella)) >= 6     # fonti/centrali.toml non è preso per una convenzione


def test_testo_da_pdf_e_zip():
    import io
    import zipfile
    import pytest
    canvas = pytest.importorskip("reportlab.pdfgen.canvas")
    b = io.BytesIO()
    c = canvas.Canvas(b)
    c.drawString(72, 720, "Lotto 1 - spread 1,180 EUR/MWh")
    c.drawString(72, 700, "Opzione verde: maggiorazione 1,500 EUR/MWh nel Lotto 1")
    c.save()
    z = io.BytesIO()
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("documenti/listino.pdf", b.getvalue())
    testo = S.estrai_testo("documentazione.zip", z.getvalue())
    assert "spread 1,180" in testo
    precisa = S.Regola("x", None, "1", "spread", r"Lotto 1 - spread (" + S.NUMERO + ")")
    generica = S.Regola("x", None, "1", "spread", r"(" + S.NUMERO + r") EUR/MWh")
    assert S.cerca_valori(precisa, {"zip": testo}) == [1.18]
    assert S.cerca_valori(generica, {"zip": testo}) == [1.18, 1.5]     # ambiguo: non si applica


def test_valore_per_fascia_diventa_proposta(tmp_path):
    """Uno spread scritto per fascia non si aggiorna da solo: resta una proposta, senza fermare il resto."""
    conv = tmp_path / "convenzioni"
    conv.mkdir()
    (conv / "prova.toml").write_text(TOML.replace("spread = 2.00 ", "spread = { F1 = 2.0, F2 = 2.0, F3 = 2.0 }"),
                                     encoding="utf-8")
    notte = [2]
    cl, _ = _sito(notte)
    s = S.Sorveglianza(tmp_path / "a", conv, client=cl, oggi=dt.date(2026, 11, 4))
    e = s.esegui()
    p = [v for v in e["proposte"] if v["lotto"] == "1"]
    assert p and "non aggiornato da solo" in p[0]["nota"] and not e["valori_aggiornati"]
    assert "spread = { F1 = 2.0" in (conv / "prova.toml").read_text(encoding="utf-8")
