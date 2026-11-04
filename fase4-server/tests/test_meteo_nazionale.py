"""Meteo per tutta Italia (4/11/2026): giornaliero.parquet nazionale (~34 milioni di righe) scritto, letto e aggiornato
un blocco alla volta; regioni servite (REGIONI) distinte da quelle aggiornate ogni giorno (REGIONI_AGGIORNATE)."""
import datetime as dt

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest

from meteo_storico import aggrega
from servizio import config as C, meteo


def _orario(istat: str, giorni: int = 40) -> pd.DataFrame:
    t = pd.date_range("2025-01-01", periods=24 * giorni, freq="h", tz="UTC")
    base = int(istat[-2:])
    return pd.DataFrame({"time": t, "temperature_2m": np.float32(base / 10), "relative_humidity_2m": np.float32(70),
                         "shortwave_radiation": np.float32(100), "diffuse_radiation": np.float32(50),
                         "wind_speed_10m": np.float32(5), "cloud_cover": np.float32(30),
                         "precipitation": np.float32(0), "snowfall": np.float32(0)})


@pytest.fixture
def archivio(tmp_path):
    a = tmp_path / "archivio"
    codici = [f"0{r:02d}0{k:02d}" for r in (1, 8, 19) for k in range(1, 21)]      # 60 comuni in 3 regioni
    (a / "orario" / "era5_corretto").mkdir(parents=True)
    (a / "orario" / "icon").mkdir(parents=True)
    for i in codici:
        _orario(i).to_parquet(a / "orario" / "era5_corretto" / f"{i}.parquet")
        _orario(i, 3).to_parquet(a / "orario" / "icon" / f"{i}.parquet")
    cm = pd.DataFrame({"istat": codici, "regione_cod": [i[1:3] for i in codici], "nome": codici})
    cm.to_parquet(a / "comuni.parquet")
    return a, cm


def test_esporta_a_blocchi(archivio, tmp_path, monkeypatch):
    a, cm = archivio
    monkeypatch.setattr(aggrega, "COMUNI_PER_BLOCCO", 25)
    dest = tmp_path / "pacchetto"
    aggrega.esporta(a, cm.sample(frac=1, random_state=1), dest)          # ordine qualsiasi in ingresso
    f = pq.ParquetFile(dest / "giornaliero.parquet")
    assert f.metadata.num_rows == 60 * 40 and f.metadata.num_row_groups == 3     # 25 + 25 + 10 comuni
    g = pd.read_parquet(dest / "giornaliero.parquet")
    assert list(g.istat.drop_duplicates()) == sorted(cm.istat)               # ordinato per comune
    assert len(list((dest / "orario").glob("*.parquet"))) == 60
    assert (dest / "comuni.parquet").exists() and not (dest / "giornaliero.parziale").exists()


def test_storico_di_un_comune_e_aggiornamento(archivio, tmp_path, monkeypatch):
    a, cm = archivio
    monkeypatch.setattr(aggrega, "COMUNI_PER_BLOCCO", 25)
    aggrega.esporta(a, cm, tmp_path / "dati")
    monkeypatch.setattr(C, "DATI", tmp_path / "dati")
    meteo._giornaliero_comune.cache_clear()
    s = meteo.storico_giornaliero("019005")
    assert len(s) == 40 and "istat" not in s and s.t_media.iloc[0] == pytest.approx(0.5)
    # due giorni nuovi per Bologna (uno corregge l'ultimo esistente) e un comune che non c'era
    nuovi = pd.DataFrame({"istat": ["008006", "008006", "099999"],
                          "data": [dt.date(2025, 2, 9), dt.date(2025, 2, 10), dt.date(2025, 2, 10)]})
    for c in s.columns:
        if c != "data":
            nuovi[c] = np.float32(9)
    p = tmp_path / "dati" / "giornaliero.parquet"
    meteo.aggiorna_giornaliero(p, nuovi)
    meteo._giornaliero_comune.cache_clear()
    b = meteo.storico_giornaliero("008006")
    assert len(b) == 41 and b.t_media.iloc[-2] == 9 and b.t_media.iloc[-1] == 9
    assert list(pd.to_datetime(b.data).dt.date)[-1] == dt.date(2025, 2, 10)
    assert len(meteo.storico_giornaliero("099999")) == 1
    assert len(meteo.storico_giornaliero("001003")) == 40                  # gli altri comuni intatti
    assert pq.ParquetFile(p).metadata.num_rows == 60 * 40 + 2


def test_regioni_servite_e_aggiornate(archivio, monkeypatch):
    a, cm = archivio
    monkeypatch.setattr(C, "DATI", a)
    monkeypatch.setattr(C, "SOLO_COMUNI", [])
    monkeypatch.setattr(C, "REGIONI", [])
    monkeypatch.setattr(C, "REGIONI_AGGIORNATE", ["08"])
    assert len(meteo.comuni()) == 60
    assert set(meteo.comuni(aggiornati=True).regione_cod) == {"08"}
    monkeypatch.setattr(C, "REGIONI_AGGIORNATE", [])
    assert len(meteo.comuni(aggiornati=True)) == 60
    monkeypatch.setattr(C, "REGIONI", ["01", "19"])
    monkeypatch.setattr(C, "REGIONI_AGGIORNATE", ["08"])
    assert len(meteo.comuni(aggiornati=True)) == 0                          # aggiornate solo tra quelle servite
