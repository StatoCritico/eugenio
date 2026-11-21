"""Scaricatore del Download Center di Terna: paginazione con risposte finte (niente rete)."""
from __future__ import annotations

import json

import pytest

from elettricita import terna_dc as T

COLONNE = {"Anno": "Integer", "Regione": "String", "Mercato": "String", "Consumo (GWh)": "Number"}


def _finto(totale: int, pagina: int, dichiarato: int | None = None):
    """Un servizio finto con `totale` righe e pagine da `pagina` righe; registra le richieste."""
    righe = [[2019, "Lazio", "Autoconsumo", float(i)] for i in range(totale)]
    richieste = []

    def post(corpo: dict) -> dict:
        richieste.append(corpo)
        if corpo.get("pageSize") == "1" and "filterYear" not in corpo:
            return {"Years": ["2018", "2019"]}
        i = int(corpo["pageIndex"])
        return {"Columns": COLONNE, "Count": totale if dichiarato is None else dichiarato,
                "Data": righe[i * pagina:(i + 1) * pagina]}

    return post, richieste, righe


def test_legge_tutte_le_pagine(monkeypatch):
    post, richieste, righe = _finto(100368, 50000)
    monkeypatch.setattr(T, "_post", post)
    attese = []
    monkeypatch.setattr(T.time, "sleep", attese.append)
    d = T.scarica_anno("Market", 2019, pausa=1.0)
    assert d["Count"] == 100368 and d["Data"] == righe and d["Columns"] == COLONNE
    assert [r["pageIndex"] for r in richieste] == ["0", "1", "2"]
    assert all(r["pageSize"] == str(T.PAGINA) == "50000" for r in richieste)
    assert all(r["filterYear"] == "2019" and r["orderByColumn"] == "Consumo (GWh)" for r in richieste)
    assert attese == [1.0, 1.0]            # una pausa prima di ogni pagina successiva alla prima


def test_una_pagina_sola(monkeypatch):
    post, richieste, righe = _finto(11888, 50000)
    monkeypatch.setattr(T, "_post", post)
    monkeypatch.setattr(T.time, "sleep", lambda s: None)
    assert T.scarica_anno("Market", 2018)["Data"] == righe
    assert len(richieste) == 1


def test_esattamente_multiplo_della_pagina(monkeypatch):
    post, richieste, _ = _finto(100000, 50000)
    monkeypatch.setattr(T, "_post", post)
    monkeypatch.setattr(T.time, "sleep", lambda s: None)
    assert len(T.scarica_anno("Market", 2019)["Data"]) == 100000
    assert len(richieste) == 2            # non chiede una terza pagina vuota


def test_righe_mancanti_errore(monkeypatch):
    # il servizio dichiara più righe di quante ne restituisce: si ferma alla pagina vuota e segnala
    post, _, _ = _finto(60000, 50000, dichiarato=70000)
    monkeypatch.setattr(T, "_post", post)
    monkeypatch.setattr(T.time, "sleep", lambda s: None)
    with pytest.raises(RuntimeError, match="70000 righe, ricevute 60000"):
        T.scarica_anno("Market", 2019)


def test_righe_in_piu_errore(monkeypatch):
    post, _, _ = _finto(60000, 50000, dichiarato=55000)
    monkeypatch.setattr(T, "_post", post)
    monkeypatch.setattr(T.time, "sleep", lambda s: None)
    with pytest.raises(RuntimeError, match="55000 righe, ricevute 60000"):
        T.scarica_anno("Market", 2019)


def test_scarica_salta_anni_presenti(tmp_path, monkeypatch):
    post, richieste, _ = _finto(3, 2)
    monkeypatch.setattr(T, "_post", post)
    monkeypatch.setattr(T.time, "sleep", lambda s: None)
    (tmp_path / "Market_2018.json").write_text("{}", encoding="utf-8")
    assert T.scarica(tmp_path, ["Market"]) == {"Market": [2019]}
    d = json.loads((tmp_path / "Market_2019.json").read_text(encoding="utf-8"))
    assert d["Count"] == 3 and len(d["Data"]) == 3
    assert (tmp_path / "Market_2018.json").read_text(encoding="utf-8") == "{}"
    assert [r.get("filterYear") for r in richieste] == [None, "2019", "2019"]
