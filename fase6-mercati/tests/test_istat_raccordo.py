"""Cambi di base ISTAT: serie unica nella base più recente (decisione del 28/10/2026).
Valori veri del FOI senza tabacchi (00ST) letti il 28/10/2026: media 2025 in base 2015 = 121,4."""
import pandas as pd
import pytest

from mercati_energia import istat

CSV = """DATAFLOW,FREQ,REF_AREA,DATA_TYPE,MEASURE,ECOICOP_2,TIME_PERIOD,OBS_VALUE,OBS_STATUS,NOTE_DS,BASE_PER
IT1:169_748(1.0),M,IT,101,4,00ST,2026-01,100.4,,,
IT1:169_748(1.0),M,IT,101,4,00ST,2026-09,104.3,p,,
IT1:169_748(1.0),M,IT,55,4,00ST,2025-10,121.4,,,
IT1:169_748(1.0),M,IT,55,4,00ST,2025-11,121.3,,,
IT1:169_748(1.0),M,IT,55,4,00ST,2025-12,121.5,,,
IT1:169_748(1.0),M,IT,55,4,00,2025-12,121.6,,,
"""
FOI = {"dataflow": "169_748", "chiave": "M.IT..4.00ST", "filtri": {"ECOICOP_2": "00ST"},
       "base": {"tipo": "101", "precedente": "55", "anno": 2025, "nome": "2025=100"}}


class Risposta:
    def __init__(self, testo):
        self.text = testo


def test_raccordo_con_coefficiente_calcolato(tmp_path, monkeypatch):
    chiamate = []
    monkeypatch.setattr(istat, "_get", lambda url, accept, timeout=300: chiamate.append(url) or Risposta(CSV))
    d = istat.serie(tmp_path, "foi_mensile", FOI)
    assert "/data/169_748/M.IT..4.00ST/ALL/" in chiamate[0]
    assert list(d.periodo) == ["2025-10", "2025-11", "2025-12", "2026-01", "2026-09"]
    vecchi = d[d.raccordato]
    # media del IV trimestre del campione = 121,4 → coefficiente 1,214 (come ISTAT per il FOI 2025)
    assert (vecchi.coefficiente == 1.214).all()
    assert vecchi.loc[vecchi.periodo == "2025-10", "valore"].iloc[0] == pytest.approx(100.0)
    assert vecchi.loc[vecchi.periodo == "2025-12", "valore_originale"].iloc[0] == 121.5
    nuovi = d[~d.raccordato]
    assert list(nuovi.valore) == [100.4, 104.3] and nuovi.coefficiente.isna().all()
    assert (d.base == "2025=100").all() and d.loc[d.periodo == "2026-09", "stato"].iloc[0] == "p"
    assert "NOTE_DS" not in d and "BASE_PER" not in d            # colonne vuote di note scartate
    # seconda volta: dalla cache, nessuna richiesta
    istat.serie(tmp_path, "foi_mensile", FOI)
    assert len(chiamate) == 1


def test_coefficiente_indicato_in_configurazione():
    df = pd.DataFrame({"periodo": ["2020-01", "2021-06", "2026-01"], "valore": [110.0, 121.0, 99.0],
                       "DATA_TYPE": ["IND_PRIC2", "IND_PRIC2", "IND_PRIC_2021"]})
    d = istat.raccorda(df, {"tipo": "IND_PRIC_2021", "precedente": "IND_PRIC2", "anno": 2021, "coefficiente": 1.1})
    assert d.loc[d.periodo == "2020-01", "valore"].iloc[0] == pytest.approx(100.0)
    assert d.loc[d.periodo == "2026-01", "raccordato"].iloc[0] == False  # noqa: E712


def test_la_base_nuova_vince_sui_periodi_doppi():
    df = pd.DataFrame({"periodo": ["2021-01", "2021-01", "2020-12"], "valore": [105.0, 100.0, 104.0],
                       "DATA_TYPE": ["IND_PRIC2", "IND_PRIC_2021", "IND_PRIC2"]})
    d = istat.raccorda(df, {"tipo": "IND_PRIC_2021", "precedente": "IND_PRIC2", "anno": 2021})
    assert list(d.periodo) == ["2020-12", "2021-01"]
    assert d.loc[d.periodo == "2021-01", "valore"].iloc[0] == 100.0
    assert d.loc[d.periodo == "2020-12", "coefficiente"].iloc[0] == 1.05


def test_anno_di_base_mancante():
    df = pd.DataFrame({"periodo": ["2019", "2026"], "valore": [110.0, 101.0], "DATA_TYPE": ["56", "102"]})
    with pytest.raises(RuntimeError, match="manca l'anno 2025"):
        istat.raccorda(df, {"tipo": "102", "precedente": "56", "anno": 2025})


def test_dimensione_sbagliata_errore_chiaro(tmp_path, monkeypatch):
    monkeypatch.setattr(istat, "_get", lambda url, accept, timeout=300: Risposta(CSV))
    with pytest.raises(RuntimeError, match="E_COICOP_REV_ISTAT non esiste"):
        istat.serie(tmp_path, "x", {"dataflow": "169_748", "filtri": {"E_COICOP_REV_ISTAT": "00"}})
