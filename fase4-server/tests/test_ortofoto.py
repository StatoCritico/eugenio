"""Prove del proxy delle ortofoto (servizio/ortofoto.py, fase 10, Fase B) con risposte simulate: nessuna rete.

La prova dal vivo del WMS RER 2023-24 è stata fatta a mano il 04/11/2026 (vedi fase10-edifici3d/ortofoto/*.toml)."""
from __future__ import annotations

import io
import math
import re
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



_RER_BUCO = [False]


def _png_rer(buco=False):
    """Tessera PNG come quella della RER con TRANSPARENT=TRUE: piena, o con la metà sinistra senza dati (trasparente)."""
    from PIL import Image
    im = Image.new("RGBA", (256, 256), (120, 140, 90, 255))
    if buco:
        im.paste((0, 0, 0, 0), (0, 0, 128, 256))
    b = io.BytesIO(); im.save(b, "PNG")
    return b.getvalue()


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
        if "TRANSPARENT=TRUE" in url:      # RER (fonte «trasparente»): PNG, con un buco se l'URL lo chiede (BBOX di prova)
            return httpx.Response(200, content=_png_rer(buco=_RER_BUCO[0]), headers={"content-type": "image/png"})
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
    # ?t=1 (07/11/2026 sera): indirizzo nuovo delle tessere RER, le copie nere vecchie di browser e Cloudflare non valgono più
    assert rer["stato"] == "da confermare" and rer["tessere"] == "/api/ortofoto/rer2023/{z}/{x}/{y}.jpg?t=1"
    r = c.get("/api/ortofoto/rer2023/17/70114/47547.jpg")
    assert r.status_code == 200 and r.content[:3] == b"\xff\xd8\xff" and r.headers["content-type"] == "image/jpeg"
    assert r.headers["x-ortofoto-copia"] == "nuova" and "FORMAT=image/png&TRANSPARENT=TRUE" in chiamate[-1]
    assert "public" in r.headers["cache-control"] and r.headers["x-ortofoto-fonte"] == "rer2023"
    assert (tmp_path / "copia" / "rer2023_t" / "17" / "70114" / "47547.jpg").exists()
    r2 = c.get("/api/ortofoto/rer2023/17/70114/47547.jpg")
    assert r2.headers["x-ortofoto-copia"] == "si" and len(chiamate) == 1          # dalla copia, senza chiamare
    r3 = c.get("/api/ortofoto/rer2023/17/70114/47547.jpg", headers={"If-None-Match": r2.headers["etag"]})
    assert r3.status_code == 304
    # solo dal vivo: niente copia sul server né su Cloudflare, solo il browser (09/11/2026)
    r = c.get("/api/ortofoto/pcn2012/17/70114/47547.jpg")
    assert r.status_code == 200 and r.headers["cache-control"] == "private, max-age=86400"
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


def test_zone_senza_dati_trasparenti(client, tmp_path):
    """Brisighella (07/11/2026 sera): dove la RER 2023-24 non ha dati la tessera era nera e opaca. Ora è PNG con la
    trasparenza (sotto si vede il contesto); dalla copia esce con il tipo giusto."""
    import numpy as np
    from PIL import Image
    c, chiamate = client
    url = "/api/ortofoto/rer2023/17/70114/47548.jpg"
    _RER_BUCO[0] = True
    r = c.get(url)
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    a = np.asarray(Image.open(io.BytesIO(r.content)).convert("RGBA"))
    assert a[10, 10, 3] == 0 and a[10, 200, 3] == 255                 # buco trasparente, foto opaca
    r2 = c.get(url)
    assert r2.headers["x-ortofoto-copia"] == "si" and r2.headers["content-type"] == "image/png" and r2.content == r.content
    _RER_BUCO[0] = False
    assert O.tipo_di(b"\xff\xd8\xff\xe0", "x") == "image/jpeg" and O.tipo_di(b"abc", "image/jpeg") == "image/jpeg"


# ------------------------------------------------------------------ ortofoto spostata a mano (08/11/2026)
@pytest.mark.parametrize("z,x,y,de,dn", [(19, 280456, 190190, 1, 0), (19, 280456, 190190, 0, -1), (17, 70114, 47547, 20, -20),
                                         (12, 2190, 1478, -7, 13), (18, 139000, 93000, 3, 4)])
def test_bbox_spostato_di_n_metri_sul_terreno(z, x, y, de, dn):
    """Il BBOX chiesto alla fonte è quello della tessera spostato di (−de, −dn) metri **sul terreno** (ellissoide WGS84),
    misurato con pyproj: la foto appare spostata di de m a est e dn m a nord. Scarto < 1 cm (anche allo zoom 12)."""
    from pyproj import Geod, Transformer
    t = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    g = Geod(ellps="WGS84")
    w, s, e, n = O.limiti_tessera(z, x, y)
    w2, s2, e2, n2 = O.bbox_spostato(z, x, y, de, dn)
    assert e2 - w2 == pytest.approx(e - w, abs=1e-6) and n2 - s2 == pytest.approx(n - s, abs=1e-6)   # stessa scala, nessuna riproiezione
    lon0, lat0 = t.transform((w + e) / 2, (s + n) / 2)
    lon1, lat1 = t.transform((w2 + e2) / 2, (s2 + n2) / 2)
    # componenti est e nord del passo, misurate separatamente sul terreno
    _, _, est = g.inv(lon0, lat0, lon1, lat0)
    _, _, nord = g.inv(lon1, lat0, lon1, lat1)
    assert math.copysign(est, lon1 - lon0) == pytest.approx(-de, abs=0.01)
    assert math.copysign(nord, lat1 - lat0) == pytest.approx(-dn, abs=0.01)
    assert O.bbox_spostato(z, x, y) == (w, s, e, n)
    ke, kn = O.scala_mercatore(44.0)
    assert ke == pytest.approx(1.388, abs=0.001) and kn == pytest.approx(1.393, abs=0.001)


def test_spostamento_rotta_limiti_e_niente_copia(client, tmp_path):
    c, chiamate = client
    fonti = {x["id"]: x for x in c.get("/api/ortofoto/fonti").json()["fonti"]}
    assert fonti["rer2023"]["spostabile"] and fonti["pcn2012"]["spostabile"] and fonti["toscana2023"]["spostamento_max"] == 20
    assert not fonti["s2cloudless2016"]["spostabile"] and fonti["s2cloudless2016"]["spostamento_max"] == 0
    base = "/api/ortofoto/toscana2023/16/34800/23900.jpg"
    r0 = c.get(base)
    assert r0.headers["x-ortofoto-copia"] == "nuova" and len(chiamate) == 1
    r = c.get(base + "?de=2&dn=-1")
    assert r.status_code == 200 and r.headers["x-ortofoto-copia"] == "no" and r.headers["x-ortofoto-spostamento"] == "de=2; dn=-1"
    assert len(chiamate) == 2 and "max-age=86400" in r.headers["cache-control"]       # sempre dalla fonte, mai dalla copia
    bb = lambda u: [float(v) for v in re.search(r"BBOX=([^&]+)", u).group(1).split(",")]
    w, s, e, n = O.limiti_tessera(16, 34800, 23900)
    ke, kn = O.scala_mercatore(math.degrees(math.atan(math.sinh(((s + n) / 2) / 6378137.0))))
    assert bb(chiamate[-1]) == pytest.approx([w - 2 * ke, s + kn, e - 2 * ke, n + kn], abs=0.002)
    assert bb(chiamate[0]) == pytest.approx([w, s, e, n], abs=0.002)
    c.get(base + "?de=2&dn=-1")
    assert len(chiamate) == 3                                                          # nessuna copia su disco
    copie = sorted(p.relative_to(tmp_path / "copia").as_posix() for p in (tmp_path / "copia").rglob("*.jpg"))
    assert copie == ["toscana2023/16/34800/23900.jpg"]                                 # solo la tessera normale
    assert c.get(base + "?de=0&dn=0").headers["x-ortofoto-copia"] == "si"              # spostamento nullo = tessera normale
    # RER trasparente (?t=1 nell'indirizzo) e Geoportale dal vivo: spostabili
    r = c.get("/api/ortofoto/rer2023/17/70114/47547.jpg?t=1&de=-1&dn=0")
    assert r.status_code == 200 and "TRANSPARENT=TRUE" in chiamate[-1] and not (tmp_path / "copia" / "rer2023_t").exists()
    r = c.get("/api/ortofoto/pcn2012/17/70114/47547.jpg?de=0&dn=5")
    assert r.status_code == 200 and r.headers["cache-control"] == "private, max-age=86400"
    # limiti: interi da -20 a 20; tessere già pronte (Sentinel-2) non spostabili
    n0 = len(chiamate)
    for q in ("de=21", "dn=-21", "de=1.5", "de=a"):
        assert c.get(f"{base}?{q}").status_code == 422, q
    assert c.get("/api/ortofoto/s2cloudless2016/12/2190/1478.jpg?de=1").status_code == 400
    assert len(chiamate) == n0                                                         # nessuna chiamata alla fonte


def test_limite_solo_sulle_tessere_dalla_fonte_e_429_con_retry_after(client, monkeypatch):
    """09/11/2026 (prove J10: migliaia di 429 in Modelli 3D): la copia su disco non consuma il limite «ortofoto», solo il
    tetto anti-abuso «tessere_copia»; il 429 dice quanto aspettare (Retry-After) e quale limite (X-EuGEnio-Limite)."""
    c, chiamate = client
    monkeypatch.setattr(C, "ORTOFOTO_ORA", 2)
    h = {"X-Forwarded-For": "198.51.100.9"}
    assert c.get("/api/ortofoto/rer2023/17/70114/47547.jpg", headers=h).status_code == 200
    for _ in range(10):                                   # dalla copia: non contano nel limite della fonte
        assert c.get("/api/ortofoto/rer2023/17/70114/47547.jpg", headers=h).headers["x-ortofoto-copia"] == "si"
    assert c.get("/api/ortofoto/rer2023/17/70115/47547.jpg", headers=h).status_code == 200
    r = c.get("/api/ortofoto/rer2023/17/70116/47547.jpg", headers=h)
    assert r.status_code == 429 and "tessere di ortofoto" in r.json()["detail"]
    assert 1 <= int(r.headers["retry-after"]) <= 3600 and r.headers["x-eugenio-limite"] == "ortofoto"
    assert len(chiamate) == 2                             # la terza non è andata alla fonte
    # un altro indirizzo non è toccato
    assert c.get("/api/ortofoto/rer2023/17/70116/47547.jpg", headers={"X-Forwarded-For": "198.51.100.10"}).status_code == 200
    # tetto della copia
    monkeypatch.setattr(C, "TESSERE_COPIA_ORA", 3)
    P.limiti.clear()
    for _ in range(3):
        assert c.get("/api/ortofoto/rer2023/17/70114/47547.jpg", headers=h).status_code == 200
    r = c.get("/api/ortofoto/rer2023/17/70114/47547.jpg", headers=h)
    assert r.status_code == 429 and r.headers["x-eugenio-limite"] == "tessere_copia"


def test_attesa_del_limitatore():
    L = P.Limitatore()
    for t in range(10):
        assert L.prova("a", "x", 10, 3600, ora=1000.0 + t * 60)
    assert not L.prova("a", "x", 10, 3600, ora=1600.0)
    # per liberare 1 posto basta che scada il primo (istante 1000 + 3600 − 1600 = 3000 s); per liberarne 3 il terzo
    assert L.attesa("a", "x", 10, 3600, 1, ora=1600.0) == 3000
    assert L.attesa("a", "x", 10, 3600, 3, ora=1600.0) == 3120
    assert L.attesa("b", "x", 10, 3600, 3, ora=1600.0) == 0


def test_tessera_vuota_dichiarata(client, tmp_path, monkeypatch):
    """09/11/2026: la RER 2023-24 ha zone senza immagini (Bologna, Modena, Faenza…): tessera tutta trasparente con
    X-Ortofoto-Vuota, la pagina passa da sola a un'altra fonte."""
    from PIL import Image
    c, chiamate = client
    b = io.BytesIO(); Image.new("RGBA", (256, 256), (0, 0, 0, 0)).save(b, "PNG")
    monkeypatch.setattr(O, "_scarica", lambda url: httpx.Response(200, content=b.getvalue(), headers={"content-type": "image/png"}))
    r = c.get("/api/ortofoto/rer2023/17/69665/47409.jpg")
    assert r.status_code == 200 and r.headers.get("x-ortofoto-vuota") == "1" and r.headers["content-type"] == "image/png"
    r = c.get("/api/ortofoto/rer2023/17/69665/47409.jpg")               # dalla copia: sempre dichiarata
    assert r.headers["x-ortofoto-copia"] == "si" and r.headers.get("x-ortofoto-vuota") == "1"
    assert "x-ortofoto-vuota" not in c.get("/api/ortofoto/pcn2012/17/69665/47409.jpg").headers


def _jpeg_segnaposto():
    """Come la WMS della Toscana fuori dalla regione: JPEG 256×256 bianco con una riga di testo scuro."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (256, 256), (255, 255, 255))
    ImageDraw.Draw(im).text((4, 120), "Fonte dei dati: Regione Toscana - Base informativa T", fill=(60, 60, 60))
    b = io.BytesIO(); im.save(b, "JPEG", quality=75)
    return b.getvalue()


def test_segnaposto_della_toscana_diventa_vuoto(client, tmp_path, monkeypatch):
    """09/11/2026 b (prove di Paolo, «strane scritte sul terreno bianco»): fuori dalla Toscana la WMS risponde 200 con un JPEG
    bianco e la scritta della fonte; il proxy lo rende una tessera vuota (PNG trasparente, X-Ortofoto-Vuota: 1), anche
    quando era già nella copia; una foto vera non si tocca."""
    import numpy as np
    from PIL import Image
    c, _ = client
    seg = _jpeg_segnaposto()
    assert len(seg) < 4000 and O.segnaposto_bianco(seg)
    foto = io.BytesIO(); Image.fromarray(np.random.default_rng(1).integers(0, 255, (256, 256, 3), dtype=np.uint8)).save(foto, "JPEG")
    assert not O.segnaposto_bianco(foto.getvalue()) and not O.segnaposto_bianco(O.vuota_png())
    assert O.fonti()["toscana2023"].segnaposto and not O.fonti()["pcn2012"].segnaposto
    t = next(x for x in c.get("/api/ortofoto/fonti").json()["fonti"] if x["id"] == "toscana2023")
    assert t["tessere"].endswith(".jpg?s=1")                        # indirizzi nuovi: niente segnaposto dalle copie di prima
    monkeypatch.setattr(O, "_scarica", lambda url: httpx.Response(200, content=seg, headers={"content-type": "image/jpeg"}))
    r = c.get("/api/ortofoto/toscana2023/16/34800/23900.jpg?s=1")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png" and r.headers.get("x-ortofoto-vuota") == "1"
    a = np.asarray(Image.open(io.BytesIO(r.content)).convert("RGBA"))
    assert a.shape == (256, 256, 4) and int(a[..., 3].max()) == 0
    # segnaposto copiato prima della correzione: dalla copia esce vuoto e la copia si corregge
    p = O.file_copia(O.fonti()["toscana2023"], 16, 34800, 23901)
    p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(seg)
    r = c.get("/api/ortofoto/toscana2023/16/34800/23901.jpg")
    assert r.headers["x-ortofoto-copia"] == "si" and r.headers.get("x-ortofoto-vuota") == "1" and r.headers["content-type"] == "image/png"
    assert p.read_bytes() == O.vuota_png()
    # una foto vera della Toscana passa com'è
    monkeypatch.setattr(O, "_scarica", lambda url: httpx.Response(200, content=foto.getvalue(), headers={"content-type": "image/jpeg"}))
    r = c.get("/api/ortofoto/toscana2023/16/34800/23902.jpg")
    assert r.headers["content-type"] == "image/jpeg" and "x-ortofoto-vuota" not in r.headers
