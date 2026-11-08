"""Tessere del terreno su richiesta (servizio/terreno.py, 07/11/2026): DTM sintetico in EPSG:7791 scritto come COG con
la stessa funzione della fase 10 (`dtm-server`), Copernicus simulato; nessuna rete.

La prova sul quadrante SE vero (Brisighella e Rimini, tessere uguali a quelle degli archivi di prima entro la
precisione Terrarium) è nel README della fase 10."""
from __future__ import annotations

import io
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
pytest.importorskip("rasterio")

from servizio import config as C, protezione as P, terreno as T   # noqa: E402

FASE10 = Path(__file__).resolve().parents[2] / "fase10-edifici3d"


def _dtm(cartella: Path) -> dict:
    """Piano inclinato attorno a Brisighella (EPSG:7791, 5 m): quota = 100 + 0,01·(x − x0) + 0,02·(y − y0)."""
    import rasterio
    from rasterio.transform import from_origin
    sys.path.insert(0, str(FASE10))
    from edifici3d import dtm_locale as DL
    x0, y0, n = 723000.0, 4895000.0, 1200             # 6 km × 6 km
    xs = np.arange(n) * 5 + 2.5
    ys = np.arange(n) * 5 + 2.5
    z = (100 + 0.01 * xs[None, :] + 0.02 * (n * 5 - ys)[:, None]).astype("float32")
    z[:50, :50] = -9999                               # un vuoto nell'angolo
    src = cartella / "_grezzo.tif"
    with rasterio.open(src, "w", driver="GTiff", width=n, height=n, count=1, dtype="float32", crs="EPSG:7791",
                       transform=from_origin(x0, y0 + n * 5, 5, 5), nodata=-9999) as d:
        d.write(z, 1)
    out = DL.cog_server(src, cartella / "dtm_prova.tif", attribuzione="Prova – DTM sintetico, CC BY 4.0")
    src.unlink()
    return out


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    (tmp_path / "terreno").mkdir()
    scheda = _dtm(tmp_path / "terreno")
    monkeypatch.setattr(C, "CARTELLA_TERRENO", tmp_path / "terreno")
    monkeypatch.setattr(C, "CARTELLA_TERRENO_TESSERE", tmp_path / "tessere")
    monkeypatch.setattr(C, "TERRENO_ATTIVO", True)
    monkeypatch.setattr(T, "_dtm_cache", None)
    chiamate = []

    def cop(z, x, y):
        chiamate.append((z, x, y))
        return np.full((256, 256), 50.0, dtype="float32")
    monkeypatch.setattr(T, "leggi_copernicus", cop)
    P.limiti.clear()
    from servizio.app import app
    yield TestClient(app), scheda, chiamate


def _quote(r) -> np.ndarray:
    from PIL import Image
    return T.decodifica(np.asarray(Image.open(io.BytesIO(r.content)).convert("RGB")))


def _tessera(lon, lat, z):
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    return x, y


def _centro(scheda):
    a, b, c, d = scheda["riquadro_wgs84"]
    return (a + c) / 2, (b + d) / 2


def test_cog_server_scheda(client):
    _, scheda, _ = client
    assert scheda["crs"] == "EPSG:7791" and scheda["licenza"] == "CC BY 4.0" and scheda["passo_m"] == [5.0, 5.0]
    import rasterio
    with rasterio.open(Path(C.CARTELLA_TERRENO) / "dtm_prova.tif") as s:
        assert s.profile["tiled"] and s.overviews(1)        # COG a tessere con panoramiche
    assert T.dtm_disponibili()[0]["attribuzione"].startswith("Prova")


def test_tessera_dal_dtm_e_copia(client):
    cl, scheda, chiamate = client
    lon, lat = _centro(scheda)
    x, y = _tessera(lon, lat, 15)
    r = cl.get(f"/api/terreno/15/{x}/{y}.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert r.headers["x-terreno-fonte"] == "dtm" and r.headers["x-terreno-copia"] == "nuova"
    assert "max-age=2592000" in r.headers["cache-control"]
    q = _quote(r)
    # quota attesa nel centro della tessera (piano inclinato): confronto con la lettura diretta del COG
    import rasterio
    from pyproj import Transformer
    w, s, e, n = T.limiti_tessera(15, x, y)
    lo, la = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform((w + e) / 2, (s + n) / 2)
    ex, ny = Transformer.from_crs("EPSG:4326", "EPSG:7791", always_xy=True).transform(lo, la)
    with rasterio.open(Path(C.CARTELLA_TERRENO) / "dtm_prova.tif") as src:
        atteso = next(src.sample([(ex, ny)]))[0]
    assert abs(q[128, 128] - atteso) < 0.1 and not chiamate
    r2 = cl.get(f"/api/terreno/15/{x}/{y}.png")
    assert r2.headers["x-terreno-copia"] == "si" and r2.content == r.content
    assert cl.get(f"/api/terreno/15/{x}/{y}.png", headers={"if-none-match": r.headers["etag"]}).status_code == 304


def test_panoramica_per_zoom_basso_e_ripiego(client):
    cl, scheda, chiamate = client
    lon, lat = _centro(scheda)
    x, y = _tessera(lon, lat, 10)                         # tessera di ~39 km: il DTM di prova ne copre una parte
    r = cl.get(f"/api/terreno/10/{x}/{y}.png")
    assert r.status_code == 200 and r.headers["x-terreno-fonte"] == "dtm+copernicus" and chiamate
    q = _quote(r)
    assert np.isclose(q, 50.0, atol=0.01).any() and (q > 100).any()


def test_fuori_dal_dtm_copernicus_poi_piatta(client, monkeypatch):
    cl, _, chiamate = client
    x, y = _tessera(9.19, 45.46, 14)                      # Milano: nessun DTM di prova
    r = cl.get(f"/api/terreno/14/{x}/{y}.png")
    assert r.headers["x-terreno-fonte"] == "copernicus" and np.allclose(_quote(r), 50.0, atol=0.01)

    def rotto(*a):
        raise OSError("S3 non raggiungibile")
    monkeypatch.setattr(T, "leggi_copernicus", rotto)
    x, y = _tessera(9.30, 45.50, 14)
    r = cl.get(f"/api/terreno/14/{x}/{y}.png")
    assert r.headers["x-terreno-fonte"] == "piatta" and "max-age=300" in r.headers["cache-control"]
    assert np.allclose(_quote(r), 0.0) and not T.file_copia(14, x, y).exists()


def test_limiti_e_spegnimento(client, monkeypatch):
    cl, _, _ = client
    x, y = _tessera(-0.1, 51.5, 12)                       # Londra
    assert cl.get(f"/api/terreno/12/{x}/{y}.png").status_code == 404
    assert cl.get("/api/terreno/16/0/0.png").status_code == 404
    assert cl.get("/api/terreno/5/16/11.png").status_code == 404           # sotto TERRENO_ZOOM_MIN
    f = cl.get("/api/terreno/fonti").json()
    assert f["codifica"] == "terrarium" and f["dtm"][0]["licenza"] == "CC BY 4.0" and "Copernicus" in f["ripiego"]
    monkeypatch.setattr(C, "TERRENO_ATTIVO", False)
    x, y = _tessera(11.75, 44.2, 14)
    assert cl.get(f"/api/terreno/14/{x}/{y}.png").status_code == 404


def test_limite_per_ip_solo_sulle_nuove(client, monkeypatch):
    cl, scheda, _ = client
    monkeypatch.setattr(C, "TERRENO_ORA", 2)
    lon, lat = _centro(scheda)
    x, y = _tessera(lon, lat, 14)
    for _ in range(4):                                    # la stessa tessera: dopo la prima viene dalla copia
        assert cl.get(f"/api/terreno/14/{x}/{y}.png").status_code == 200
    assert cl.get(f"/api/terreno/14/{x + 1}/{y}.png").status_code == 200
    assert cl.get(f"/api/terreno/14/{x + 2}/{y}.png").status_code == 429


def test_pulizia(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "CARTELLA_TERRENO_TESSERE", tmp_path)
    monkeypatch.setattr(C, "TERRENO_MAX_GB", 3e-6)        # 3 kB
    for k in range(6):
        p = tmp_path / "v" / "14" / "1" / f"{k}.png"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x" * 1000)
        p.with_suffix(".txt").write_text("dtm\n")
    assert T.pulisci(forza=True) >= 3
    assert sum(1 for _ in tmp_path.rglob("*.png")) * 1000 <= 0.8 * 3000 + 1


def test_terrarium_andata_e_ritorno():
    z = np.array([[-10.5, 0.0], [123.25, 4807.0]], dtype="float32")
    assert np.allclose(T.decodifica(T.codifica(z)), z, atol=1 / 256)
    json.dumps(T.lonlat_tessera(15, 17000, 11800))


def _tavole_veneto(cartella: Path, passo: float = 5.0) -> list[Path]:
    """Quattro tavole ESRI ASCII Grid zippate (come quelle del Veneto: senza .prj) in EPSG:6876 intorno a Susegana:
    quota = 200 + 0,01·(x − 3018000) (riconoscibile), un vuoto -9999 in un angolo della prima."""
    import zipfile
    n = int(1000 / passo)
    out = []
    for k, (x0, y0) in enumerate([(3018000, 5078000), (3019000, 5078000), (3018000, 5079000), (3019000, 5079000)]):
        xs = x0 + (np.arange(n) + 0.5) * passo
        z = np.tile(200 + 0.01 * (xs - 3018000), (n, 1))
        if k == 0:
            z[-5:, :5] = -9999.0
        righe = [f"ncols {n}", f"nrows {n}", f"xllcenter {x0 + passo / 2:.3f}", f"yllcenter {y0 + passo / 2:.3f}",
                 f"cellsize {passo:.3f}", "nodata_value -9999.0"] + [" ".join(f"{v:.2f}" for v in r) for r in z]
        f = cartella / f"12_2K_{1359 + k}.asc.zip"
        with zipfile.ZipFile(f, "w") as zz:
            zz.writestr(f"12_2K_{1359 + k}.asc", "\n".join(righe) + "\n")
        out.append(f)
    return out


def test_piu_dtm_veneto_in_6876_il_piu_dettagliato_prima(client, tmp_path, monkeypatch):
    """08/11/2026: `dtm-server` mosaica più tavole ASCII Grid senza sistema con --crs EPSG:6876 (scheda del Veneto,
    IODL 2.0, data dei file); la rotta usa più DTM insieme, il più dettagliato prima, e dice quale (X-Terreno-Nome)."""
    cl, _, chiamate = client
    sys.path.insert(0, str(FASE10))
    from edifici3d import dtm_locale as DL
    grezzi = tmp_path / "grezzi"; grezzi.mkdir()
    _tavole_veneto(grezzi)
    with pytest.raises(ValueError, match="--crs"):
        DL.cog_server(grezzi, tmp_path / "x.tif", regione="er")              # senza sistema: errore chiaro
    sc = DL.cog_server(grezzi, Path(C.CARTELLA_TERRENO) / "dtm5_veneto_tv.tif", regione="veneto", crs="EPSG:6876")
    assert sc["crs"] == "EPSG:6876" and sc["tavole"] == 4 and sc["licenza"] == "IODL 2.0" and sc["passo_m"] == [5.0, 5.0]
    assert sc["nome"].startswith("DTM 5 m da voli LiDAR Regione del Veneto") and sc["data"]
    lon0, lat0, lon1, lat1 = sc["riquadro_wgs84"]
    assert 12.22 < lon0 < lon1 < 12.27 and 45.83 < lat0 < lat1 < 45.87             # Susegana: EPSG:6876 giusto
    # un secondo DTM più grossolano (20 m) sopra la stessa zona: vince il 5 m
    g2 = tmp_path / "g2"; g2.mkdir()
    _tavole_veneto(g2, passo=20.0)
    DL.cog_server(g2, Path(C.CARTELLA_TERRENO) / "a_grossolano.tif", regione="veneto", crs="EPSG:6876", nome="DTM grossolano di prova")
    monkeypatch.setattr(T, "_dtm_cache", None)
    assert [d["file"] for d in T.dtm_disponibili()][0] in ("dtm_prova.tif", "dtm5_veneto_tv.tif")
    assert T.dtm_disponibili()[-1]["file"] == "a_grossolano.tif"
    x, y = _tessera(12.2393, 45.8445, 15)
    r = cl.get(f"/api/terreno/15/{x}/{y}.png")
    assert r.status_code == 200, r.text
    assert r.headers["x-terreno-fonte"] == "dtm" and r.headers["x-terreno-nome"].startswith("DTM 5 m da voli LiDAR Regione del Veneto")
    q = _quote(r)
    assert 200 < float(np.median(q)) < 220 and not chiamate
    r2 = cl.get(f"/api/terreno/15/{x}/{y}.png")                                  # dalla copia: stesso nome
    assert r2.headers["x-terreno-copia"] == "si" and r2.headers["x-terreno-nome"] == r.headers["x-terreno-nome"]
    f = cl.get("/api/terreno/fonti").json()["dtm"]
    assert {d["licenza"] for d in f} >= {"IODL 2.0"} and any(d.get("data") for d in f)
