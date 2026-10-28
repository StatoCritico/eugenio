"""Previsione senza dati meteo del comune sul server: niente errore 500, previsione col solo calendario e avviso."""
import numpy as np
import pandas as pd
import pytest

from meteo_storico import VARIABILI
from servizio import meteo, modello


def _finto_esegui(target, cov, orizzonte, freq):
    return pd.DataFrame({q: np.full(orizzonte, 1.0) for q in modello.QUANTILI})


@pytest.fixture
def senza_meteo(monkeypatch):
    monkeypatch.setattr(meteo, "storico_orario", lambda istat: pd.DataFrame(columns=["time", *VARIABILI]))
    monkeypatch.setattr(meteo, "previsioni", lambda istat: pd.DataFrame(columns=["time", *VARIABILI, "peso_icon2i"]))

    def mancante(istat):
        raise FileNotFoundError("giornaliero.parquet")
    monkeypatch.setattr(meteo, "storico_giornaliero", mancante)
    monkeypatch.setattr(modello, "_esegui", _finto_esegui)


@pytest.mark.parametrize("modalita,freq,n,orizzonte", [("breve", "h", 24 * 30, 72), ("lungo", "D", 400, 30)])
def test_previsione_senza_meteo(senza_meteo, modalita, freq, n, orizzonte):
    idx = pd.date_range("2026-09-01", periods=n, freq=freq)
    s = pd.Series(np.random.default_rng(0).uniform(1, 2, n), index=idx)
    ris = modello.prevedi(s, "037006", modalita, orizzonte)
    assert len(ris["previsione"]["0.5"]) == orizzonte
    assert any("non sono ancora sul server" in a for a in ris["avvisi"])
    assert not any(c in ris["covariate"] for c in ("temperatura", "radiazione"))


def test_meteo_orario_con_storico_vuoto_e_previsioni(monkeypatch):
    """Storico vuoto ma previsioni presenti: l'indice concatenato non deve diventare di tipo object."""
    t = pd.date_range("2026-10-28", periods=48, freq="h", tz="UTC")
    pr = pd.DataFrame({"time": t, **{v: np.ones(48) for v in VARIABILI}, "peso_icon2i": np.ones(48)})
    monkeypatch.setattr(meteo, "storico_orario", lambda istat: pd.DataFrame(columns=["time", *VARIABILI]))
    monkeypatch.setattr(meteo, "previsioni", lambda istat: pr)
    df, fonte = modello._meteo_orario("037006")
    assert isinstance(df.index, pd.DatetimeIndex) and len(df) == 48 and df.index.tz is None
