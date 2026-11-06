"""Prove degli strati sopra le ortofoto (servizio/strati.py, 05/11/2026): particelle catastali dell'Agenzia delle Entrate
(riproiezione da EPSG:4258), contorni degli edifici del DBTR e di OpenStreetMap. Risposte simulate: nessuna rete.

Le prove dal vivo (WMS dell'Agenzia e del DBTR dal container) sono scritte nei TOML di fase10-edifici3d/ortofoto/strati/."""
from __future__ import annotations

import io
import math
import sys
import tomllib
from pathlib import Path

import httpx
import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from servizio import config as C, ortofoto as O, protezione as P, strati as T   # noqa: E402

REPO = Path(__file__).resolve().parents[2]
STRATI = REPO / "fase10-edifici3d" / "ortofoto" / "strati"


def _png(a) -> bytes:
    b = io.BytesIO()
    Image.fromarray(a.astype("uint8"), "RGBA").save(b, "PNG")
    return b.getvalue()


def test_toml_del_repository_e_regioni_attive():
    tutti = {s.id: s for f in sorted(STRATI.glob("*.toml")) for s in T.leggi_toml(f)}
    assert {"catasto", "dbtr_edifici", "osm_edifici"} <= set(tutti)
    c = tutti["catasto"]
    assert c.licenza == "CC BY 4.0" and "Agenzia delle Entrate" in c.citazione and c.crs == "EPSG:4258"
    assert c.metatessera == 2 and c.contorni and c.tema == "particelle"
    assert tutti["osm_edifici"].licenza == "ODbL 1.0" and not tutti["osm_edifici"].regioni
    # uno strato regionale degli edifici solo dove regioni.toml ha la fonte «edifici» attiva
    reg = tomllib.loads((REPO / "fase10-edifici3d" / "fonti" / "regioni.toml").read_text(encoding="utf-8"))
    attive = {r["codice"] for r in reg["regione"] for f in r.get("fonte", []) if f["tema"] == "edifici" and f["stato"] == "attiva"}
    for s in tutti.values():
        assert s.citazione and s.licenza and s.scheda.startswith("http"), s.id
        if s.tema == "edifici":
            assert set(s.regioni) <= attive, (s.id, s.regioni)


def test_toml_sbagliati(tmp_path):
    (tmp_path / "a.toml").write_text('[[strato]]\nid = "xx"\ntema = "strade"\ntipo = "wms"\nurl = "https://x"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="tema"):
        T.leggi_toml(tmp_path / "a.toml")
    (tmp_path / "b.toml").write_text('[[strato]]\nid = "xx"\ntema = "edifici"\ntipo = "wms"\nurl = "https://x"\ncrs = "EPSG:32632"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="crs"):
        T.leggi_toml(tmp_path / "b.toml")


def test_url_wms_geografico_con_blocco():
    s = {x.id: x for x in T.leggi_toml(STRATI / "catasto.toml")}["catasto"]
    z, x, y = 18, 140223, 95260
    u, lato = T.url_wms(s, z, x, y)
    assert lato == 512 and "CRS=EPSG:4258" in u and "WIDTH=512" in u and "TRANSPARENT=TRUE" in u
    bbox = [float(v) for v in u.split("BBOX=")[1].split("&")[0].split(",")]
    lo0, la0, lo1, la1 = O.lonlat_tessera(z, x - 1, y)[0], O.lonlat_tessera(z, x, y + 1)[1], O.lonlat_tessera(z, x, y)[2], O.lonlat_tessera(z, x, y)[3]
    assert bbox == pytest.approx([la0, lo0, la1, lo1], abs=1e-8)              # lat,lon; blocco: tessera a sinistra e sotto
    d = {x.id: x for x in T.leggi_toml(STRATI / "edifici.toml")}["dbtr_edifici"]
    u, lato = T.url_wms(d, z, x, y)
    assert lato == 256 and "CRS=EPSG:3857" in u and "LAYERS=EDI_Edificio" in u


def test_riproiezione_righe_esatta():
    # immagine 512×512 lineare in latitudine: una riga rossa a una latitudine nota deve finire sulla riga mercatore giusta
    z, x, y = 12, 2190, 1488
    s = T.Strato(id="t", tema="particelle", nome="t", tipo="wms", url="u", licenza="", citazione="", scheda="",
                 stato="confermata", crs="EPSG:4258", metatessera=2)
    _, la_s, _, la_n = O.lonlat_tessera(z, x, y + 1)[0], O.lonlat_tessera(z, x, y + 1)[1], 0, O.lonlat_tessera(z, x, y)[3]
    lat_riga = O.lonlat_tessera(z, x, y)[1] + 0.3 * (O.lonlat_tessera(z, x, y)[3] - O.lonlat_tessera(z, x, y)[1])
    a = np.zeros((512, 512, 4))
    r = int(round((la_n - lat_riga) / (la_n - la_s) * 512 - 0.5))
    a[r, :, :] = (255, 0, 0, 255)
    out = np.asarray(Image.open(io.BytesIO(T.elabora(s, _png(a), z, x, y))))
    righe = np.where(out[:, 100, 3] > 0)[0]
    # riga attesa nella tessera di arrivo (web mercator)
    n = 2 ** z
    j = (1 - math.asinh(math.tan(math.radians(lat_riga))) / math.pi) / 2 * n
    attesa = (j - y) * 256
    assert len(righe) >= 1 and abs(righe.mean() - attesa) <= 1.0


def test_solo_contorni():
    a = np.zeros((256, 256, 4))
    a[50:150, 50:150] = (250, 230, 190, 255)            # particella piena beige
    a[100, 50:150] = (0, 0, 0, 255)                     # linea interna nera
    out = T.solo_contorni(a.astype("uint8"), "#ffd400")
    assert tuple(out[100, 120]) == (255, 212, 0, 255)  # linea
    assert tuple(out[50, 120]) == (255, 212, 0, 255)   # bordo della zona piena
    assert out[75, 75, 3] == 0 and out[10, 10, 3] == 0  # riempimento e vuoto trasparenti
    piena = np.zeros((256, 256, 4)); piena[...] = (250, 230, 190, 255)
    assert T.solo_contorni(piena.astype("uint8"), "#ffd400")[..., 3].max() == 0     # nessuna griglia sui bordi della tessera


def test_geojson_da_overpass():
    d = {"elements": [
        {"type": "way", "id": 1, "geometry": [{"lat": 44.0, "lon": 12.0}, {"lat": 44.0, "lon": 12.001}, {"lat": 44.001, "lon": 12.001}, {"lat": 44.0, "lon": 12.0}]},
        {"type": "way", "id": 2, "geometry": [{"lat": 44.0, "lon": 12.0}, {"lat": 44.0, "lon": 12.001}]},       # aperta: scartata
        {"type": "relation", "id": 3, "members": [{"role": "outer", "geometry": [{"lat": 1, "lon": 1}, {"lat": 1, "lon": 2}, {"lat": 2, "lon": 2}, {"lat": 1, "lon": 1}]},
                                                    {"role": "inner", "geometry": []}]}]}
    g = T.geojson_da_overpass(d)
    assert [f["properties"]["osm"] for f in g["features"]] == ["w1", "r3"] and "OpenStreetMap" in g["attribution"]
    assert "building" in T.query_overpass(16, 34894, 23807) and "out geom" in T.query_overpass(16, 34894, 23807)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    monkeypatch.setattr(C, "ORTOFOTO_FONTI", REPO / "fase10-edifici3d" / "ortofoto")
    monkeypatch.setattr(C, "CARTELLA_ORTOFOTO", tmp_path / "copia")
    monkeypatch.setattr(C, "STRATI_SPENTI", set())
    T.strati(ricarica=True)
    O.ritmo.svuota()
    P.limiti.clear()
    chiamate = []

    def finto(url, dati=None):
        chiamate.append((url, dati))
        if dati is not None:
            return httpx.Response(200, json={"elements": []}, headers={"content-type": "application/json"})
        if "errore" in url:
            return httpx.Response(200, content=b"<ServiceExceptionReport/>", headers={"content-type": "text/xml"})
        lato = int(url.split("WIDTH=")[1].split("&")[0])
        a = np.zeros((lato, lato, 4)); a[10:200, 10:200] = (250, 230, 190, 255)
        return httpx.Response(200, content=_png(a), headers={"content-type": "image/png"})

    monkeypatch.setattr(T, "_scarica", finto)
    app = FastAPI()
    app.include_router(T.router)
    app.include_router(O.router)
    yield TestClient(app), chiamate
    T.strati(ricarica=True)


def test_rotte_copia_e_spegnimento(client, tmp_path, monkeypatch):
    c, chiamate = client
    r = c.get("/api/ortofoto/strati")
    assert r.status_code == 200
    l = {x["id"]: x for x in r.json()["strati"]}
    assert l["catasto"]["tessere"] == "/api/ortofoto/strati/catasto/{z}/{x}/{y}.png" and l["osm_edifici"]["tipo"] == "vettori"
    assert l["dbtr_edifici"]["regioni"] == ["08"]
    r = c.get("/api/ortofoto/strati/catasto/18/140223/95260.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png" and r.headers["x-strato"] == "catasto"
    im = Image.open(io.BytesIO(r.content))
    assert im.size == (256, 256) and im.mode == "RGBA"
    assert (tmp_path / "copia" / "strati" / "catasto" / "18" / "140223" / "95260.png").exists()
    n = len(chiamate)
    assert c.get("/api/ortofoto/strati/catasto/18/140223/95260.png").status_code == 200 and len(chiamate) == n   # copia
    assert c.get("/api/ortofoto/strati/catasto/12/2190/1488.png").status_code == 404                           # zoom
    assert c.get("/api/ortofoto/strati/dbtr_edifici/17/1/1.png").status_code == 404                             # fuori ER
    r = c.get("/api/ortofoto/strati/osm_edifici/16/34894/23807.json")
    assert r.status_code == 200 and r.json()["type"] == "FeatureCollection" and chiamate[-1][1]
    assert c.get("/api/ortofoto/strati/osm_edifici/17/1/1.json").status_code == 404
    monkeypatch.setattr(C, "STRATI_SPENTI", {"catasto"})
    assert c.get("/api/ortofoto/strati/catasto/18/140223/95261.png").status_code == 404
    assert "catasto" not in [x["id"] for x in c.get("/api/ortofoto/strati").json()["strati"]]
    # le ortofoto restano raggiungibili accanto agli strati
    assert c.get("/api/ortofoto/fonti").status_code == 200


def test_errore_della_fonte_non_si_copia(client, tmp_path, monkeypatch):
    c, _ = client
    s = T.strati()["dbtr_edifici"]
    monkeypatch.setattr(s, "url", s.url + "?errore=1")
    assert c.get("/api/ortofoto/strati/dbtr_edifici/18/140223/95260.png").status_code == 502
    assert not (tmp_path / "copia" / "strati" / "dbtr_edifici").exists()


def test_overpass_istanza_di_riserva(monkeypatch):
    """06/11/2026: overpass-api.de risponde 502 quando è sovraccarico; si prova l'istanza di riserva del TOML."""
    s = {x.id: x for f in sorted(STRATI.glob("*.toml")) for x in T.leggi_toml(f)}["osm_edifici"]
    assert s.url_riserva and "maps.mail.ru" in s.url_riserva[0]
    chiamate = []

    def finto(url, dati=None):
        chiamate.append(url)
        if url == s.url:
            return httpx.Response(502, headers={"content-type": "text/plain"}, text="Bad Gateway")
        return httpx.Response(200, headers={"content-type": "application/json"}, json={"elements": []})

    monkeypatch.setattr(T, "_scarica", finto)
    r = T._overpass(s, "[out:json];")
    assert r.status_code == 200 and chiamate == [s.url, s.url_riserva[0]]

    def sempre_giu(url, dati=None):
        raise httpx.ConnectTimeout("lento")

    monkeypatch.setattr(T, "_scarica", sempre_giu)
    with pytest.raises(httpx.HTTPError):
        T._overpass(s, "[out:json];")
