"""Giornaliero a blocchi (07/11/2026): compatibilità con i file scritti prima (row group di altre dimensioni, comuni
divisi tra due row group, file non ordinato), conversione riprendibile e comando `giornaliero-blocchi`."""
import datetime as dt

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest

from meteo_storico import __main__ as cli, aggrega


def _gg(codici, giorni=30) -> pd.DataFrame:
    date = [dt.date(2025, 1, 1) + dt.timedelta(days=k) for k in range(giorni)]
    righe = [(c, d) for c in codici for d in date]
    df = pd.DataFrame(righe, columns=["istat", "data"])
    df["t_media"] = np.float32([int(c[-3:]) / 10 for c, _ in righe])
    df["gg20"] = np.float32(1)
    return df


def _uguali(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    a = a.sort_values(["istat", "data"]).reset_index(drop=True)
    b = b.sort_values(["istat", "data"]).reset_index(drop=True)
    return a.istat.tolist() == b.istat.tolist() and a.data.tolist() == b.data.tolist() and \
        np.allclose(a.t_media, b.t_media)


@pytest.fixture
def blocchi(monkeypatch):
    monkeypatch.setattr(aggrega, "COMUNI_PER_BLOCCO", 7)


def test_vecchio_file_ordinato_con_row_group_qualsiasi(tmp_path, blocchi):
    codici = [f"{k:06d}" for k in range(1000, 1023)]
    p = tmp_path / "giornaliero.parquet"
    _gg(codici).to_parquet(p, index=False, row_group_size=100)          # comuni divisi tra due row group
    inf = aggrega.info_giornaliero(p)
    assert inf["ordinato"] and not inf["a_blocchi"] and inf["formato"] is None
    assert len(aggrega.leggi_comune(p, "001010")) == 30                  # si legge anche prima della conversione
    aggrega.aggiorna_a_blocchi(p)                                        # solo conversione
    inf = aggrega.info_giornaliero(p)
    assert inf["a_blocchi"] and inf["formato"] == aggrega.FORMATO and inf["row_group"] == 4   # 7+7+7+2
    assert _uguali(pd.read_parquet(p), _gg(codici))
    assert not (tmp_path / "giornaliero.parquet.nuovo").exists()


def test_vecchio_file_non_ordinato_conversione_riprendibile(tmp_path, blocchi, monkeypatch):
    codici = [f"{k:06d}" for k in range(1000, 1020)]
    tutto = _gg(codici).sample(frac=1, random_state=3)                   # righe mescolate
    p = tmp_path / "giornaliero.parquet"
    tutto.to_parquet(p, index=False, row_group_size=97)
    assert not aggrega.info_giornaliero(p)["ordinato"]
    nuovi = _gg(["001003", "009999"], 1).assign(t_media=np.float32(9))
    # prima esecuzione interrotta al terzo blocco: i primi due restano in giornaliero.parziale/
    vero = aggrega._Parziale.scrivi
    conta = {"n": 0}

    def scrivi(self, k, df):
        conta["n"] += 1
        if conta["n"] == 3:
            raise KeyboardInterrupt
        vero(self, k, df)
    monkeypatch.setattr(aggrega._Parziale, "scrivi", scrivi)
    with pytest.raises(KeyboardInterrupt):
        aggrega.aggiorna_a_blocchi(p, nuovi)
    assert len(list((tmp_path / "giornaliero.parziale").glob("blocco_*.parquet"))) == 2
    assert pq.ParquetFile(p).metadata.num_rows == 600                    # originale intatto
    monkeypatch.setattr(aggrega._Parziale, "scrivi", vero)
    rifatti = []
    monkeypatch.setattr(aggrega._Parziale, "scrivi", lambda self, k, df: (rifatti.append(k), vero(self, k, df)))
    aggrega.aggiorna_a_blocchi(p, nuovi)
    assert rifatti == [2]                                                # ripresa: solo il blocco mancante
    assert not (tmp_path / "giornaliero.parziale").exists()
    g = pd.read_parquet(p)
    assert len(g) == 600 + 1 and aggrega.info_giornaliero(p)["a_blocchi"]
    assert g[(g.istat == "001003") & (g.data == dt.date(2025, 1, 1))].t_media.iloc[0] == 9


def test_comando_giornaliero_blocchi(tmp_path, blocchi, capsys):
    p = tmp_path / "giornaliero.parquet"
    _gg([f"{k:06d}" for k in range(1000, 1010)]).to_parquet(p, index=False, row_group_size=50)
    cli.main(["giornaliero-blocchi", "--file", str(p), "--solo-verifica"])
    assert "a blocchi: no" in capsys.readouterr().out
    cli.main(["giornaliero-blocchi", "--file", str(p)])
    out = capsys.readouterr().out
    assert "a blocchi: sì" in out and "righe: 300" in out
