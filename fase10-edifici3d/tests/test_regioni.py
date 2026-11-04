"""Fonti per regione (Fase E): forma del file, regola «attiva solo con licenza compatibile e prova dal vivo»,
coerenza con i TOML delle ortofoto. Nessuna rete: la prova dal vivo usa un trasporto finto."""
from __future__ import annotations

import tomllib
from pathlib import Path

import httpx

from edifici3d import regioni as RG
from edifici3d.__main__ import main

QUI = Path(__file__).resolve().parents[1]


def test_file_valido():
    d = RG.carica()
    assert RG.controlla(d) == []
    assert len(d["regione"]) == 21
    assert sum(len(r["fonte"]) for r in d["regione"]) == 84
    c = RG.conteggi(d)
    assert sum(c.values()) == 84 and c["attiva"] > 0


def test_regola_attiva():
    d = {"licenze_compatibili": ["CC BY 4.0"], "regione": [{"nome": "Prova", "fonte": [
        {"tema": t, "nome": "x", "stato": "attiva", "verifica": "2026-11-04", "licenza": "CC BY-NC 4.0",
         "scheda": "s", "prova": "200"} for t in RG.TEMI]}]}
    err = RG.controlla(d)
    assert any("non compatibile" in e for e in err) and any("attese 21" in e for e in err)
    d["regione"][0]["fonte"][0]["licenza"] = "CC BY 4.0"
    d["regione"][0]["fonte"][0].pop("prova")
    assert any("senza prova" in e for e in RG.controlla(d))


def test_ortofoto_accese_sono_attive_nel_registro():
    d = RG.carica()
    usate = " ".join(f.get("usata_in", "") for r in d["regione"] for f in r["fonte"] if f["stato"] == "attiva")
    usate += " " + " ".join(f.get("usata_in", "") for f in d["nazionale"] if f["stato"] == "attiva")
    for p in sorted((QUI / "ortofoto").glob("*.toml")):
        for f in tomllib.loads(p.read_text(encoding="utf-8")).get("fonte", []):
            if f.get("attiva") and f.get("id") != "pcn2012":
                assert p.name in usate, (p.name, f["id"])


def test_prova_dal_vivo_finta():
    d = {"regione": [{"nome": "R", "fonte": [{"tema": "dtm", "nome": "x", "stato": "attiva", "url_prova": "https://e.it/a"}]}]}
    c = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(206, headers={"content-type": "application/zip"})))
    assert RG.prova(d, c) == [{"regione": "R", "tema": "dtm", "nome": "x", "stato": "attiva", "esito": "206 application/zip"}]


def test_cli(capsys):
    assert main(["regioni"]) == 0
    out = capsys.readouterr().out
    assert "Provincia autonoma di Bolzano" in out and "conteggi" in out
    assert main(["regioni", "--markdown"]) == 0
    assert "| Regione |" in capsys.readouterr().out
