"""Prove del proxy delle ortofoto (servizio/ortofoto.py, fase 10, Fase B) con risposte simulate: nessuna rete.

La prova dal vivo del WMS RER 2023-24 è stata fatta a mano il 04/11/2026 (vedi fase10-edifici3d/ortofoto/*.toml)."""
from __future__ import annotations

import sys
import types
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from servizio import config as C, ortofoto as O, protezione as P   # noqa: E402

FONTI_REPO = Path(__file__).resolve().parents[2] / "fase10-edifici3d" / "ortofoto"
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 100 + b"\xff\xd9"


def test_toml_del_repository():
    tutte = {}
    for f in sorted(FONTI_REPO.glob("*.toml")):
        for x in O.leggi_toml(f):
            tutte[x.id] = x
    assert {"rer2023", "toscana2023", "s2cloudless2016", "pcn2012"} <= set(tutte)
    assert tutte["rer2023"].stato == "da confermare" and tutte["rer2023"].livello == "RER2023_24_RGB"
    assert tutte["rer2023"].licenza == "CC BY 4.0" and "Emilia-Romagna" in tutte["rer2023"].citazione
    assert tutte["pcn2012"].cache is False and tutte["pcn2012"].nei_report is False      # solo dal vivo
    assert "2016" in tutte["s2cloudless2016"].citazione and tutte["s2cloudless2016"].licenza == "CC BY 4.0"
    for x in tutte.values():
        assert x.citazione and x.licenza and x.scheda.startswith("http"), x.id
        assert not O.ESCLUSI.search(x.url), x.id


def test_fonti_escluse_e_stati(tmp_path):
    (tmp_path / "x.toml").write_text('regione = "01"\n[[fonte]]\nid = "g"\nnome = "G"\ntipo = "xyz"\n'
                                     'url = "https://mt1.google.com/vt/{z}/{x}/{y}"\nstato = "confermata"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="escluso"):
        O.leggi_toml(tmp_path / "x.toml")
    (tmp_path / "y.toml").write_text('[[fonte]]\nid = "eox"\ntipo = "xyz"\nurl = "https://tiles.maps.eox.at/wmts/1.0.0/'
                                     's2cloudless-2020_3857/default/g/{z}/{y}/{x}.jpg"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="escluso"):
        O.leggi_toml(tmp_path / "y.toml")
    (tmp_path / "z.toml").write_text('[[fonte]]\nid = "a"\ntipo = "wms"\nurl = "https://x"\nstato = "boh"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="stato"):
        O.leggi_toml(tmp_path / "z.toml")


def test_url_wms_e_xyz():
    f = next(x for x in O.leggi_toml(FONTI_REPO / "emilia_romagna.toml") if x.id == "rer2023")
    # tessera z17 di Rimini
    z, x, y = 17, 70114, 47547
    u = O.url_tessera(f, z, x, y)
    assert u.startswith("https://servizigis.regione.emilia-romagna.it/wms/rer2023_24_rgb?SERVICE=WMS&VERSION=1.3.0")
    assert "LAYERS=RER2023_24_RGB" in u and "CRS=EPSG:3857" in u and "WIDTH=256" in u
    w, s, e, n = O.limiti_tessera(z, x, y)
    assert e - w == pytest.approx(305.748, abs=0.01)
    assert O.dentro(f, z, x, y) and not O.dentro(f, 10, 545, 370) and not O.dentro(f, 17, 0, 0)
    t = next(x for x in O.leggi_toml(FONTI_REPO / "toscana.toml"))
    assert O.url_tessera(t, 17, 1, 2).startswith("https://www502.regione.toscana.it/ows_ofc/com.rt.wms.RTmap/wms?map=owsofc_rt&SERVICE")
    s2 = next(x for x in O.leggi_toml(FONTI_REPO / "italia.toml") if x.id == "s2cloudless2016")
    assert O.url_tessera(s2, 12, 2190, 1478).endswith("/g/12/1478/2190.jpg")


def test_ritmo():
    f = O.Fonte(id="t", nome="t", tipo="xyz", url="u", formato="image/jpeg", licenza="", citazione="", scheda="",
                stato="confermata", regione="", al_secondo=2, all_ora=3)
    r = O.Ritmo()
    assert r.prova(f, 100.0) == 0 and r.prova(f, 100.1) == 0
    assert r.prova(f, 100.2) > 0                 # terza nello stesso secondo
    assert r.prova(f, 101.5) == 0                # nuovo secondo
    assert r.prova(f, 103.0) > 1000              # quarta nell'ora: tetto orario


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    monkeypatch.setattr(C, "ORTOFOTO_FONTI", FONTI_REPO)
    monkeypatch.setattr(C, "CARTELLA_ORTOFOTO", tmp_path / "copia")
    monkeypatch.setattr(C, "ORTOFOTO_SPENTE", set())
    monkeypatch.setattr(C, "ORTOFOTO_SOLO_CONFERMATE", False)
    O.fonti(ricarica=True)
    O.ritmo.svuota()
    P.limiti.clear()
    chiamate = []

    def finto(url):
        chiamate.append(url)
        if "errore" in url:
            return httpx.Response(200, content=b"<ServiceExceptionReport/>", headers={"content-type": "text/xml"})
        return httpx.Response(200, content=JPEG, headers={"content-type": "image/jpeg"})

    monkeypatch.setattr(O, "_scarica", finto)
    app = FastAPI()
    app.include_router(O.router)
    yield TestClient(app), chiamate
    O.fonti(ricarica=True)


def test_rotte_copia_e_intestazioni(client, tmp_path):
    c, chiamate = client
    r = c.get("/api/ortofoto/fonti")
    ids = [x["id"] for x in r.json()["fonti"]]
    assert r.status_code == 200 and "rer2023" in ids and "pcn2012" in ids
    rer = next(x for x in r.json()["fonti"] if x["id"] == "rer2023")
    assert rer["stato"] == "da confermare" and rer["tessere"] == "/api/ortofoto/rer2023/{z}/{x}/{y}.jpg"
    r = c.get("/api/ortofoto/rer2023/17/70114/47547.jpg")
    assert r.status_code == 200 and r.content == JPEG and r.headers["x-ortofoto-copia"] == "nuova"
    assert "public" in r.headers["cache-control"] and r.headers["x-ortofoto-fonte"] == "rer2023"
    assert (tmp_path / "copia" / "rer2023" / "17" / "70114" / "47547.jpg").exists()
    r2 = c.get("/api/ortofoto/rer2023/17/70114/47547.jpg")
    assert r2.headers["x-ortofoto-copia"] == "si" and len(chiamate) == 1          # dalla copia, senza chiamare
    r3 = c.get("/api/ortofoto/rer2023/17/70114/47547.jpg", headers={"If-None-Match": r2.headers["etag"]})
    assert r3.status_code == 304
    # solo dal vivo: niente copia, no-store
    r = c.get("/api/ortofoto/pcn2012/17/70114/47547.jpg")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    assert not (tmp_path / "copia" / "pcn2012").exists()
    # fuori zona, estensione sbagliata, fonte sconosciuta
    assert c.get("/api/ortofoto/rer2023/17/0/0.jpg").status_code == 404
    assert c.get("/api/ortofoto/rer2023/17/70114/47547.png").status_code == 404
    assert c.get("/api/ortofoto/google/17/70114/47547.jpg").status_code == 404


def test_fonte_spenta_dal_env_e_solo_confermate(client, monkeypatch):
    c, chiamate = client
    monkeypatch.setattr(C, "ORTOFOTO_SPENTE", {"rer2023"})
    assert c.get("/api/ortofoto/rer2023/17/70114/47547.jpg").status_code == 404
    assert "rer2023" not in [x["id"] for x in c.get("/api/ortofoto/fonti").json()["fonti"]]
    monkeypatch.setattr(C, "ORTOFOTO_SPENTE", set())
    monkeypatch.setattr(C, "ORTOFOTO_SOLO_CONFERMATE", True)
    assert c.get("/api/ortofoto/rer2023/17/70114/47547.jpg").status_code == 404
    assert c.get("/api/ortofoto/s2cloudless2016/12/2190/1478.jpg").status_code == 200
    assert not chiamate[:-1]


def test_errore_wms_non_si_copia_e_ritmo_503(client, tmp_path, monkeypatch):
    c, chiamate = client
    f = O.fonti()["toscana2023"]
    monkeypatch.setattr(f, "url", f.url + "&errore=1")
    r = c.get("/api/ortofoto/toscana2023/16/34800/23900.jpg")
    assert r.status_code == 502 and not (tmp_path / "copia" / "toscana2023").exists()
    monkeypatch.setattr(f, "al_secondo", 1)
    monkeypatch.setattr(C, "ORTOFOTO_ATTESA_S", 0)
    O.ritmo.svuota()
    assert c.get("/api/ortofoto/toscana2023/16/34800/23901.jpg").status_code == 502   # errore della fonte, conta
    r = c.get("/api/ortofoto/toscana2023/16/34800/23902.jpg")
    assert r.status_code == 503 and "retry-after" in r.headers


def test_pulizia_della_copia(tmp_path, monkeypatch):
    import os
    import time
    monkeypatch.setattr(C, "CARTELLA_ORTOFOTO", tmp_path)
    monkeypatch.setattr(C, "ORTOFOTO_MAX_GB", 1e-6)          # 1.000 byte
    for i in range(10):
        p = tmp_path / "a" / "1" / "1" / f"{i}.jpg"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x" * 300)
        os.utime(p, (time.time() - 1000 + i, time.time() - 1000 + i))
    assert O.pulisci(forza=True) >= 7
    rimasti = sorted(p.name for p in tmp_path.rglob("*.jpg"))
    assert "9.jpg" in rimasti and "0.jpg" not in rimasti                # tolte le più vecchie


def test_attesa_del_turno(client, monkeypatch):
    c, chiamate = client
    f = O.fonti()["s2cloudless2016"]
    monkeypatch.setattr(f, "al_secondo", 2)
    monkeypatch.setattr(C, "ORTOFOTO_ATTESA_S", 3)
    O.ritmo.svuota()
    codici = [c.get(f"/api/ortofoto/s2cloudless2016/12/2190/{1470 + i}.jpg").status_code for i in range(5)]
    assert codici == [200] * 5                       # aspettano il turno invece di fallire
