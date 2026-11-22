"""Costruzione dei file della pagina «Suolo e aree agricole» con dati inventati (campioni.py, niente rete)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import campioni as K
from suolo import colture, costruisci as C, mappa as M
from suolo.classi import GRUPPI, classe_nuovo_consumo

MAPPA = Path(__file__).resolve().parents[2] / "fase5-sito" / "sito" / "dati" / "mappa"
I_FV = [g for g, _, _, _ in GRUPPI].index("fv")
I_EDIFICI = [g for g, _, _, _ in GRUPPI].index("edifici")


def _costruisci(tmp_path, **kw):
    raw = K.raw(tmp_path / "raw", **{k: v for k, v in kw.items() if k in ("alterato", "edizione", "agricolo")})
    esito = C.costruisci(raw, tmp_path / "out", MAPPA, **{k: v for k, v in kw.items() if k in ("precedente", "forza")})
    it = json.loads((tmp_path / "out" / "italia.json").read_text(encoding="utf-8"))
    return esito, it


def test_costruisci(tmp_path):
    esito, it = _costruisci(tmp_path)
    assert esito["edizione"] == 2016 and esito["versione"] == "1.0" and esito["comuni"] == 3
    assert it["anni"]["suolo"] == [2006, 2012, 2015] and it["anni"]["consumi"] == [2012, 2015]
    assert it["periodi"] == {"2012": [2006, 2012], "2015": [2012, 2015]} and it["rev"] == ["2012"]
    assert [v["id"] for v in it["voci"]["suolo"]] == ["sau", "nonut", "cons", "idr", "frane", "coste", "protette"]
    ita = it["italia"]
    # suolo consumato 2015 = somma dei tre comuni; SAU del censimento (somma dei comuni assegnati)
    assert ita["suolo"]["2015"][2] == pytest.approx(5080 + 2040.5 + 101.5)
    assert ita["suolo"]["2015"][:2] == [22000.5, 120.0]
    assert ita["suolo"]["2015"][4] == pytest.approx((5080 + 2040.5 + 101.5) * 0.03)      # frane P3 + P4
    assert ita["rev"] == {"2012": pytest.approx(5055 + 2030 + 101)}
    # consumi: 2012 con la parte non attribuita (lordo 96 − classi 81 = 15), bilancio lordo/ripristini/netto
    c12 = ita["consumi"]["2012"]
    assert c12[I_EDIFICI] == 30 and c12[I_FV] == 30 and c12[-1] == pytest.approx(15)
    assert ita["bilancio"]["2015"] == [33.0, 2.0, 31.0]
    assert sum(ita["consumi"]["2015"]) == pytest.approx(33.0)
    # regioni: Emilia-Romagna e Sardegna con i valori; posizioni dalla mappa
    er = next(r for r in it["regioni"] if r["cod"] == "08")
    sa = next(r for r in it["regioni"] if r["cod"] == "20")
    assert er["suolo"]["2015"][2] == pytest.approx(7120.5) and sa["suolo"]["2015"][2] == pytest.approx(101.5)
    assert er["sup"] == pytest.approx(14073 + 20494) and er["lon"] and er["lat"]
    # SAU: Aggius (090001 nel censimento e nella mappa) va nella provincia nuova 113, non nella sigla vecchia SS
    assert sa["suolo"]["2015"][:2] == [4000.0, 100.0]
    p20 = json.loads((tmp_path / "out" / "20.json").read_text(encoding="utf-8"))
    assert [p["cod"] for p in p20["province"]] == ["113"] and p20["province"][0]["suolo"]["2015"][0] == 4000.0
    # comuni: codice della mappa, provincia 2026, superficie, suolo consumato e incremento netto per anno
    assert p20["comuni"]["dati"] == [["090001", "Aggius", "113", 8624.0, [100.0, 101.0, 101.5], [None, 1.0, 0.5]]]
    p08 = json.loads((tmp_path / "out" / "08.json").read_text(encoding="utf-8"))
    bo = next(p for p in p08["province"] if p["cod"] == "037")
    assert bo["sigla"] == "BO" and bo["agricolo"] == {"2015": [4.0, 0.0, 0.0, 6.0, 0.0, 0.0, 0.0]}
    assert {c[0] for c in p08["comuni"]["dati"]} == {"037006", "037032"}
    # agricolo: Italia e regione; scarto fra i pixel e l'Excel nelle note
    assert ita["agricolo"] == {"2015": [4.5, 0, 0, 6, 0, 0, 0]} and er["agricolo"]["2015"][3] == 6.0
    assert any("Incrocio agricolo 2015" in n for n in it["note"])
    assert it["riferimenti"]["agricolo"]["confronto"]["ha"] == 8208
    assert it["riferimenti"]["ispra"]["licenza"] == "CC BY 4.0" and "Munafò" in it["riferimenti"]["ispra"]["citazione"]
    assert "ISPRA/SNPA, ISTAT e Copernicus" in it["fonte"]
    # colture: famiglie, 2017 incompleto escluso, Sardegna solo regionale
    assert it["anni"]["colture"] == [2015, 2016]
    ids = [v["id"] for v in it["voci"]["colture"]]
    col16 = dict(zip(ids, ita["colture"]["2016"]))
    assert col16["prati"] == 180.0 and col16["cereali"] == pytest.approx(450.0) and col16["olivo"] == 36.0
    assert dict(zip(ids, ita["colture"]["2015"]))["prati"] == 150.0
    assert "colture" in sa and "colture" not in p20["province"][0] and "colture" in bo
    assert esito["italia_ultimo_anno"]["anno"] == 2015


def test_controlli_somme_e_anni(tmp_path):
    # un comune con un valore che non torna con la provincia e l'Italia
    with pytest.raises(ValueError, match="somma"):
        _costruisci(tmp_path / "a", alterato={("Comuni", "2015"): {"csuolo1": 9999.0}})
    # ultimo anno diverso da edizione − 1
    with pytest.raises(ValueError, match="edizione"):
        _costruisci(tmp_path / "b", edizione=2020)


def test_comune_non_abbinato(tmp_path, monkeypatch):
    monkeypatch.setitem(K.COMUNI, 113001, ("Comune che non esiste", 113, 20, 8624.0))
    with pytest.raises(ValueError, match="non abbinati"):
        _costruisci(tmp_path)


def test_confronto_con_i_file_pubblicati(tmp_path):
    _, it = _costruisci(tmp_path / "a")
    vecchio = tmp_path / "vecchio.json"
    it["regioni"][7]["suolo"]["2015"][2] *= 0.9                      # Emilia-Romagna: −10 % nell'edizione pubblicata
    vecchio.write_text(json.dumps(it))
    with pytest.raises(ValueError, match="2 %"):
        _costruisci(tmp_path / "b", precedente=vecchio)
    esito, it2 = _costruisci(tmp_path / "c", precedente=vecchio, forza=True)
    assert any("Emilia-Romagna 2015" in n for n in it2["note"])


def test_senza_agricolo(tmp_path):
    _, it = _costruisci(tmp_path, agricolo=False)
    assert it["anni"]["agricolo"] == [] and "agricolo" not in it["italia"] and it["riferimenti"]["agricolo"] is None


def test_colture_voci_nuove_e_territori(tmp_path):
    f = tmp_path / "c.csv"
    K.scrivi_colture(f, extra=[("IT", "VOCENUOVA", 2016, 5), ("ITZZZ", "WHEATD", 2016, 1)])
    r = colture.famiglie(f)
    assert any("VOCENUOVA" in n for n in r["note"]) and any("ITZZZ" in n for n in r["note"])
    assert r["scelte"][2016]["prati"] == [["PGRAPM"]] and r["scelte"][2015]["prati"] == [["PERMGRASSE", "POORINGS", "OTHEZINGS", "PGPNP"]]
    assert "037" in r["province"] and "08" in r["regioni"] and "20" in r["regioni"]


def test_classi_e_nomi():
    assert classe_nuovo_consumo(2125) == 125 and classe_nuovo_consumo(2122) == 122
    assert classe_nuovo_consumo(2201) is None and classe_nuovo_consumo(122111) is None and classe_nuovo_consumo(0) is None
    assert M.norm("Forlì-Cesena") == "forli cesena" and M.norm_comune("Bolzano/Bozen") == "bolzano"
    m = M.carica(MAPPA)
    abb, non = M.abbina_comuni({"113001": ("Aggius", "20"), "037006": ("Bologna", "08"), "999999": ("Nessuno", "08")}, m["comuni"])
    assert abb == {"113001": "090001", "037006": "037006"} and non == ["999999"]


def test_senza_calamine_con_openpyxl(tmp_path, monkeypatch):
    """Sul server c'è openpyxl e non python-calamine: stessi file."""
    import sys
    _, it1 = _costruisci(tmp_path / "a")
    monkeypatch.setitem(sys.modules, "python_calamine", None)
    _, it2 = _costruisci(tmp_path / "b")
    assert it1 == it2
