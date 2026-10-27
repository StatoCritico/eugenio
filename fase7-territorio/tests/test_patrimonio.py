"""Test con un client Zornade simulato (nessuna chiamata di rete)."""
from pathlib import Path

import pandas as pd

from territorio import patrimonio
from territorio.zornade import da_riferimento, senza_zeri

COMUNI = pd.DataFrame({"istat": ["037006", "039014", "040012"], "nome": ["Bologna", "Ravenna", "Forlì"],
                       "belfiore": ["A944", "H199", "D704"], "provincia": ["BO", "RA", "FC"]})


class Finto:
    """Imita le risposte reali verificate il 25/10/2026: `foglio` vuoto in /parcels/locate,
    foglio ricavabile da cadastral_reference, ricerca catastale per NOME del comune."""
    chiamate = 0

    def __init__(self, civico_noto=True):
        self.civico_noto = civico_noto
        self.query = []

    def particella_in_punto(self, lat, lon):
        if lat > 44.4:
            return {"fid": 16305467, "label": "170", "foglio": None, "kind": "immobile", "area_m2": 900,
                    "cadastral_reference": "A944_019000.170",
                    "municipality": {"code": "A944", "name": "Bologna"}, "centroid": {"lat": lat, "lng": lon}}
        return {"fid": 88890100, "label": "STRADA992", "foglio": None, "kind": "strada", "area_m2": 17555,
                "cadastral_reference": "D704_017800.STRADA992",
                "municipality": {"code": "D704", "name": "Forlì"}, "centroid": {"lat": lat, "lng": lon}}

    def cerca_particella(self, comune, foglio, mappale, sezione=None):
        assert comune == "Ravenna"          # il nome, non il codice H199
        return [{"fid": 2, "label": mappale, "foglio": foglio, "municipality": {"code": "H199", "name": "Ravenna"},
                 "centroid": {"lat": 44.41, "lng": 12.2}}]

    def geocodifica(self, q, limite=5):
        self.query.append(q)
        if "33" in q and not self.civico_noto:
            return []
        return [{"street_name": "Via Zamboni", "latitude": 44.4965, "longitude": 11.352,
                 "formatted_address": q}]


def test_riferimento():
    assert da_riferimento("A944_019000.170")["foglio"] == "190"
    assert da_riferimento("A944_019000.170")["mappale"] == "170"
    assert da_riferimento("niente") == {}
    assert senza_zeri("0190") == "190" and senza_zeri("12A") == "12A"


def test_patrimonio():
    df = patrimonio.leggi(Path(__file__).parent.parent / "esempi" / "patrimonio_esempio.csv")
    r = patrimonio.geolocalizza(df, Finto(), COMUNI).set_index("id")
    assert r.loc["E01", "metodo"] == "indirizzo" and r.loc["E01", "istat"] == "037006" and r.loc["E01", "esito"] == "ok"
    assert r.loc["E01", "foglio_catasto"] == "190" and r.loc["E01", "fonte_punto"] == "Zornade"
    assert r.loc["E02", "metodo"] == "catasto" and r.loc["E02", "istat"] == "039014"
    # una strada non è un edificio: da verificare, con la spiegazione
    assert r.loc["E03", "metodo"] == "coordinate" and r.loc["E03", "istat"] == "040012"
    assert r.loc["E03", "esito"] == "verificare" and "strada" in r.loc["E03", "nota"]
    g = patrimonio.geojson(r.reset_index())
    assert len(g["features"]) == 3 and 'href="https://zornade.com"' in g["attribution_html"]


def test_civico_mancante():
    df = patrimonio.leggi(Path(__file__).parent.parent / "esempi" / "patrimonio_esempio.csv").head(1)
    z = Finto(civico_noto=False)
    r = patrimonio.geolocalizza(df, z, COMUNI).iloc[0]
    assert z.query == ["Via Zamboni 33 Bologna", "Via Zamboni Bologna"]
    assert r.esito == "verificare" and "civico 33 non trovato" in r.nota


class FintoAllegato(Finto):
    def particella_in_punto(self, lat, lon):
        p = super().particella_in_punto(lat, lon)
        return {**p, "cadastral_reference": "A944_0190A0.170"}


def test_allegato_non_e_un_dubbio():
    df = patrimonio.leggi(Path(__file__).parent.parent / "esempi" / "patrimonio_esempio.csv").head(1)
    r = patrimonio.geolocalizza(df, FintoAllegato(), COMUNI).iloc[0]
    assert r.esito == "ok" and "allegato A" in r.nota


def test_csv_di_excel_con_codifica_windows():
    testo = "id;denominazione;indirizzo;civico;comune\nE1;Sede Forlì;Via Zamboni;33;Bologna\n"
    df = patrimonio.leggi(testo.encode("cp1252"))
    assert df.denominazione.iloc[0] == "Sede Forlì"


def test_pulizia_cache(tmp_path):
    import sqlite3
    import time
    from territorio.zornade import pulisci_cache
    f = tmp_path / "c.sqlite"
    with sqlite3.connect(f) as db:
        db.execute("CREATE TABLE cache (k TEXT PRIMARY KEY, v TEXT, t REAL)")
        db.execute("INSERT INTO cache VALUES ('vecchia', '{}', ?), ('nuova', '{}', ?)",
                   (time.time() - 400 * 86400, time.time()))
    assert pulisci_cache(f, 365) == 1
    with sqlite3.connect(f) as db:
        assert [r[0] for r in db.execute("SELECT k FROM cache")] == ["nuova"]
    assert pulisci_cache(tmp_path / "manca.sqlite") == 0
