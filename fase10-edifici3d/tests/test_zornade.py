"""Altezze di Zornade nell'archivio ODbL (Fase E), sul campione sintetico: nessun dato vero di Zornade né di OSM."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest
from shapely.geometry import box

from edifici3d import sintetico as S, uvl as U, zornade as Z
from edifici3d.modello import Corpo


@pytest.fixture
def estratto(tmp_path):
    return Z.campione(tmp_path / "z.geojson")


def _base():
    return [c for c in (U.corpo_da(p, g, None) for p, g in S.uvl()) if c]


def test_lettura_e_scarti(estratto):
    corpi, res = Z.leggi(estratto)
    assert res["righe"] == 10 and len(corpi) == 8
    assert res["scartati"] == {"altezza mancante o fuori scala": 1,
                               "altezza GlobalBuildingAtlas o non commerciale (esclusa)": 1}
    assert all(c.licenza == "ODbL 1.0" and c.fonte_altezza.startswith("Zornade") for c in corpi)
    assert res["colonne"]["altezza"] == "height_lidar"


def test_mappa_delle_colonne(estratto):
    with pytest.raises(ValueError):
        Z.leggi(estratto, mappa={"altezza": "non_esiste"})
    corpi, _ = Z.leggi(estratto, mappa={"altezza": "height_lidar"})
    assert len(corpi) == 8


def test_confronto(estratto):
    corpi, _ = Z.leggi(estratto)
    c = Z.confronta(_base(), corpi)
    r = c["riepilogo"]
    assert r["abbinati"] == 8 and r["corpi_base"] == 10
    assert 0 <= r["scarto_assoluto_medio_m"] < 3 and r["entro_3m_pct"] >= 75
    assert all(x["licenza_base"] == "CC BY 4.0" and x["iou"] >= 0.5 for x in c["righe"])


def test_altezze_solo_ai_corpi_deboli_e_diventano_odbl(estratto):
    corpi, _ = Z.leggi(estratto)
    base = _base()
    assert Z.applica_altezze(base, corpi) == []          # DBTR: altezza migliore, non si tocca
    deboli = [replace(c, gronda=0.0, fonte_altezza="nessuna", licenza="CC BY 4.0",
                      fonte_sagoma="Aggregati strutturali – Protezione Civile") for c in base]
    nuovi = Z.applica_altezze(deboli, corpi)
    assert len(nuovi) == 8
    assert all(c.licenza == "ODbL 1.0" and c.gronda > 0 and c.extra["licenza_sagoma"] == "CC BY 4.0" for c in nuovi)
    assert all(c.licenza == "CC BY 4.0" for c in deboli)  # gli originali CC BY restano com'erano


def test_prodotti_solo_in_odbl(estratto, tmp_path):
    corpi, res = Z.leggi(estratto)
    with pytest.raises(ValueError):
        Z.prepara(corpi, tmp_path / "cc-by" / "er" / "prodotti" / "zornade")
    estraneo = Corpo(id="x", edificio="x", sagoma=box(0, 0, 10, 10), quota_terreno=None, gronda=5, licenza="CC BY 4.0")
    with pytest.raises(ValueError):
        Z.prepara(corpi + [estraneo], tmp_path / "odbl" / "er" / "prodotti" / "zornade")
    out = tmp_path / "odbl" / "er" / "prodotti" / "zornade"
    e = Z.prepara(corpi, out, res, Z.confronta(_base(), corpi), sintetico=True)
    assert e["corpi"] == 8 and e["sintetico"] and (out / "corpi.pmtiles").stat().st_size > 0
    leggimi = (out / "LEGGIMI_ODbL.txt").read_text(encoding="utf-8")
    assert "ODbL 1.0" in leggimi and "https://zornade.com" in leggimi and "OpenStreetMap contributors" in leggimi
    assert "stessa licenza ODbL" in leggimi
    cella = json.loads(next((out / "contesto").glob("*.json")).read_text(encoding="utf-8"))
    assert cella["licenza"] == "ODbL 1.0" and "Zornade" in cella["attribuzione"]
    rias = json.loads((out / "confronto.json").read_text(encoding="utf-8"))
    assert rias["abbinati"] == 8 and "Zornade" in rias["attribuzione"]
    assert '<a href="https://zornade.com">Dati elaborati da Zornade</a>' in e["attribuzione_html"]


def test_nessun_accesso_all_api():
    src = (Z.__file__ and open(Z.__file__, encoding="utf-8").read())
    assert "api.zornade.com" not in src and "httpx" not in src
