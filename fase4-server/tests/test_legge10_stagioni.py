"""Legge 10 con le scelte di stagioni della pagina (14/11/2026): ultima, 5, 10, 20 o tutte (anni=0).
legge10.calcola (fase 3) e la rotta /api/clima-legge10/{istat} con dati sintetici, senza archivio vero."""
from __future__ import annotations

import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RADICE = Path(__file__).resolve().parents[2]
for p in (RADICE / "fase4-server", RADICE / "fase3-storico"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from meteo_storico import legge10  # noqa: E402


def giornaliero(dal="2015-01-01", al="2026-11-10"):
    d = pd.date_range(dal, al, freq="D")
    anni = (d.year - 2015) + d.dayofyear / 366
    t = 14 - 10 * np.cos(2 * np.pi * (d.dayofyear - 20) / 365) + 0.05 * anni     # un po' più caldo ogni anno
    return pd.DataFrame({"data": d.date, "t_media": t, "t_min": t - 5, "t_max": t + 6, "ur_media": 70.0,
                         "rad_globale_kwh_m2": 3.0, "rad_diffusa_kwh_m2": 1.2, "vento_medio_kmh": 8.0})


def test_calcola_ultima_stagione():
    r = legge10.calcola(giornaliero(), 1)
    assert r["stagioni"] == ["2025/26"] and r["stagioni_richieste"] == 1 and r["stagioni_disponibili"] == 11
    gg = r["gradi_giorno"]
    assert gg["tendenza_gg_per_decennio"] is None and gg["minimo"] == gg["massimo"] == gg["gg_periodo_zona"]
    assert len(r["mensili"]) == 12 and r["temperatura_progetto"]["invernale"] < r["temperatura_progetto"]["estiva"]
    assert any("indicativi" in n for n in r["note"])


def test_calcola_venti_e_tutte():
    venti = legge10.calcola(giornaliero(), 20)
    tutte = legge10.calcola(giornaliero(), 0)
    assert venti["stagioni"] == tutte["stagioni"] and len(tutte["stagioni"]) == 11
    assert tutte["stagioni"][0] == "2015/16" and tutte["prima_stagione_disponibile"] == "2015/16"
    assert any("Chieste 20 stagioni" in n and "dalla 2015/16" in n for n in venti["note"])
    assert tutte["note"] == [] and tutte["stagioni_richieste"] == 0
    assert tutte["gradi_giorno"]["tendenza_gg_per_decennio"] < 0          # più caldo → meno gradi giorno
    cinque = legge10.calcola(giornaliero(), 5)
    assert cinque["stagioni"] == tutte["stagioni"][-5:] and cinque["note"] == []
    with pytest.raises(ValueError):
        legge10.calcola(giornaliero(), -1)


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from servizio import app as A
    A._storia.clear()
    return TestClient(A.app), A


def test_rotta_accetta_1_20_e_0(client, monkeypatch):
    cl, A = client
    monkeypatch.setattr(A.meteo, "comuni", lambda: pd.DataFrame({"istat": ["099014"], "nome": ["Rimini"]}))
    monkeypatch.setattr(A.meteo, "storico_giornaliero", lambda istat: giornaliero())
    import servizio.storici as S
    monkeypatch.setattr(S, "zona_dpr", lambda istat: "E")
    for anni, n in ((1, 1), (5, 5), (10, 10), (20, 11), (0, 11), (99, 11)):
        r = cl.get(f"/api/clima-legge10/099014?anni={anni}")
        assert r.status_code == 200 and len(r.json()["stagioni"]) == n, anni
    d = cl.get("/api/clima-legge10/099014?anni=0").json()
    assert d["comune"] == "Rimini" and d["stagioni_richieste"] == 0 and d["stagioni_disponibili"] == 11
    assert cl.get("/api/clima-legge10/099014?anni=-2").status_code == 422
