"""Prove della fase 10 (Fase A) su dati sintetici e sul campione di attributi UVL letto dal WMS pubblico.

Dalla cartella fase10-edifici3d: `python -m pytest tests`. Nessuna rete: lo scaricamento si prova con un trasporto
httpx finto."""
from __future__ import annotations

import gzip
import json
import math
import sys
from pathlib import Path

import httpx
import numpy as np
import pytest
from shapely.geometry import box

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent))

from edifici3d import dtm as D, fonti as F, modello as M, osm as O, sintetico as S, tessere as T, uvl as U  # noqa: E402
from edifici3d.__main__ import main, prepara  # noqa: E402


# ---------------------------------------------------------------------------------------------- modello
def corpo(cid, eid, g, h, **kw):
    return M.Corpo(id=cid, edificio=eid, sagoma=g, quota_terreno=0.0, gronda=h, licenza="CC BY 4.0", **kw)


def test_stima_piani_per_uso():
    assert M.stima_piani(10, "residenziale") == 3
    assert M.stima_piani(22, "uffici") == 6
    assert M.stima_piani(16.5, "ospedale") == 4
    assert M.stima_piani(12, "capannone") == 1
    assert M.stima_piani(0) == 1
    assert M.uso_da(categoria="B/5") == "scuola"
    assert M.uso_da(categoria="A/2") == "residenziale"
    assert M.uso_da(osm_building="hospital") == "ospedale"
    assert M.uso_da("D/1", "house", dichiarato="Uffici") == "uffici"


def test_precedenza_csv_visura_stima():
    e = M.Edificio("E", [corpo("a", "E", box(0, 0, 10, 10), 9.3, uso="residenziale")])
    s = e.superfici()
    assert s["piani_fuori_terra"].valore == 3 and s["piani_fuori_terra"].fonte == "stima"
    assert s["superficie_lorda"].valore == pytest.approx(300)
    assert s["superficie_netta"].valore == pytest.approx(300 * M.NETTA_SU_LORDA)
    s = e.superfici(csv={"piani_fuori_terra": "", "superficie_lorda": "1.234,5"}, visura={"piani_fuori_terra": 4})
    assert (s["piani_fuori_terra"].valore, s["piani_fuori_terra"].fonte) == (4, "visura")
    assert (s["superficie_lorda"].valore, s["superficie_lorda"].fonte) == (1234.5, "csv")
    assert s["superficie_netta"].fonte == "stima"
    assert s["anno_costruzione"].fonte == "mancante"


def test_indicatori_cubo_isolato():
    e = M.Edificio("E", [corpo("a", "E", box(0, 0, 10, 10), 10)])
    i = M.indicatori(e)
    assert i["volume_lordo"] == pytest.approx(1000)
    assert i["pareti_esposte"] == pytest.approx(400)
    assert i["superficie_disperdente"] == pytest.approx(600)
    assert i["s_su_v"] == pytest.approx(0.6)
    for s in ("N", "E", "S", "O"):
        assert i["pareti_per_orientamento"][s] == pytest.approx(100)
    assert i["pareti_per_orientamento"]["NE"] == 0


def test_pareti_in_comune_e_parte_che_sporge():
    basso, alto = corpo("b", "E", box(0, 0, 10, 10), 6), corpo("t", "E", box(10, 0, 20, 10), 15)
    i = M.indicatori(M.Edificio("E", [basso, alto]))
    # parete comune lunga 10 m: in comune fino a 6 m; sporgono 9 m del corpo alto
    assert i["pareti_in_comune_tra_corpi"] == pytest.approx(60)
    assert i["pareti_per_orientamento"]["O"] == pytest.approx(10 * 6 + 10 * 9)
    assert i["pareti_per_orientamento"]["E"] == pytest.approx(150)
    vicino = corpo("v", "V", box(20, 0, 30, 10), 20)
    j = M.indicatori(M.Edificio("E", [basso, alto]), vicini=[vicino])
    assert j["pareti_in_comune_con_vicini"] == pytest.approx(150)
    assert j["pareti_per_orientamento"]["E"] == pytest.approx(0)


def test_tetto_a_capanna():
    c = corpo("a", "E", box(0, 0, 10, 20), 6, colmo=9, tetto="capanna", falde=2)
    assert c.altezza_media == pytest.approx(7.5)
    i = M.indicatori(M.Edificio("E", [c]))
    assert i["superficie_tetti"] == pytest.approx(200 / math.cos(math.atan(3 / 5)))


def test_orientamento_indipendente_dal_verso():
    ccw = M.indicatori(M.Edificio("E", [corpo("a", "E", box(0, 0, 10, 4), 3)]))
    from shapely.geometry.polygon import orient
    cw = M.indicatori(M.Edificio("E", [corpo("a", "E", orient(box(0, 0, 10, 4), -1), 3)]))
    assert ccw["pareti_per_orientamento"] == pytest.approx(cw["pareti_per_orientamento"])
    assert ccw["pareti_per_orientamento"]["N"] == pytest.approx(30)


# ---------------------------------------------------------------------------------------------- UVL
def test_controllo_attributi_sul_campione_wms():
    prop = U.leggi_geojson_wms(QUI / "uvl_wms_campione.json")
    c = U.controlla(prop)
    assert c["corpi"] == 5 and not c["mancanti"]
    assert c["pieni"]["H_GRONDA"] == 0 and c["campi_piani"] == []
    testo = U.rapporto(c)
    assert "gronda o di colmo" in testo and "numero di piani" in testo


def test_corpo_da_uvl_con_virgola_e_colmo():
    p = {"Id_e": "x", "Edi_id_e": "E", "H_uvl": "6,5", "H_GRONDA": "Null", "H_COLMO": "9,0", "B_uvl": "12,3",
         "Tipo_fonte": "SIT", "Qualita": "20"}
    c = U.corpo_da(p, box(0, 0, 10, 10))
    assert c.gronda == 6.5 and c.colmo == 9.0 and c.tetto == "capanna" and c.quota_terreno == 12.3
    assert c.licenza == "CC BY 4.0" and "da verificare" in c.fonte_altezza
    assert U.corpo_da({"H_uvl": "Null"}, box(0, 0, 10, 10)) is None


def test_url_getfeatureinfo():
    u = U.url_getfeatureinfo("http://x/wms", 44.06, 12.566)
    assert "info_format=application/geojson" in u and "bbox=44.0585,12.5645" in u


# ---------------------------------------------------------------------------------------------- fonti e archivi
def test_zona_e_archivi_separati(tmp_path):
    z = F.carica_zona()
    f = F.fonti(z)
    assert f["dbtr_uvl"].licenza == "CC BY 4.0" and f["osm"].licenza == "ODbL 1.0"
    a = F.cartella(tmp_path, z, "CC BY 4.0"); b = F.cartella(tmp_path, z, "ODbL 1.0")
    assert a != b and "cc-by" in a.parts and "odbl" in b.parts


def test_licenza_senza_archivio(tmp_path):
    p = tmp_path / "z.toml"
    p.write_text('[zona]\nnome="x"\ncodice="x"\n[archivi]\n"CC BY 4.0"="cc-by"\n[fonti.a]\nlicenza="CC BY-NC"\n', encoding="utf-8")
    with pytest.raises(ValueError):
        F.carica_zona(p)


def test_scarica_con_ripresa_e_registro(tmp_path):
    contenuto = b"0123456789" * 100

    def risposta(req):
        r = req.headers.get("range")
        if r:
            da = int(r.split("=")[1].rstrip("-"))
            return httpx.Response(206, content=contenuto[da:])
        return httpx.Response(200, content=contenuto)
    cl = httpx.Client(transport=httpx.MockTransport(risposta))
    z = F.carica_zona()
    z["fonti"]["osm"]["url"] = "https://esempio.invalid/dati/nord-est.osm.pbf"
    dest = F.cartella(tmp_path, z, "ODbL 1.0") / "nord-est.osm.pbf"
    dest.parent.mkdir(parents=True)
    dest.with_name(dest.name + ".parziale").write_bytes(contenuto[:300])     # download interrotto
    [p] = F.scarica_fonte(tmp_path, z, "osm", cl)
    assert p.read_bytes() == contenuto
    reg = json.loads((p.parent.parent / "fonti.json").read_text(encoding="utf-8"))
    assert reg["file"][0]["licenza"] == "ODbL 1.0" and len(reg["file"][0]["sha256"]) == 64


def test_fonte_senza_url_messaggio_chiaro(tmp_path):
    with pytest.raises(RuntimeError, match="URL vuoto"):
        F.scarica_fonte(tmp_path, F.carica_zona(), "dbtr_uvl")


# ---------------------------------------------------------------------------------------------- OSM
def test_osm_solo_dove_manca_il_dbtr():
    uvl = [corpo("u", "E", box(0, 0, 10, 10), 9)]
    el = [({"building": "house", "height": "7,5 m", "osm_id": "1"}, box(1, 1, 9, 9)),
          ({"building": "school", "building:levels": "3", "osm_id": "2"}, box(30, 0, 50, 20))]
    [c] = O.corpi_da_osm(el, uvl)
    assert c.id == "2" and c.gronda == 9.0 and c.licenza == "ODbL 1.0" and c.uso == "scuola" and c.piani == 3
    assert O.altezza({"height": "7,5"}) == (7.5, "OSM height")


# ---------------------------------------------------------------------------------------------- DTM e tessere
def test_terrarium_andata_e_ritorno():
    z = np.array([[0.0, 8.25], [-12.5, 1234.75]])
    assert np.allclose(D.decodifica_terrarium(D.codifica_terrarium(z)), z, atol=1 / 256)


def test_demo_sintetica_completa(tmp_path):
    assert main(["demo", "--uscita", str(tmp_path)]) == 0
    ind = json.loads((tmp_path / "indice.json").read_text(encoding="utf-8"))
    assert ind["sintetico"] and ind["corpi"] == 10 and ind["licenza"] == "CC BY 4.0"
    from pmtiles.reader import Reader, MmapSource
    import mapbox_vector_tile
    with open(tmp_path / "corpi.pmtiles", "rb") as f:
        r = Reader(MmapSource(f))
        h = r.header()
        assert h["min_zoom"] == 13 and h["max_zoom"] == 16
        meta = r.metadata()
        assert meta["licenza"] == "CC BY 4.0"
        x, y = T.lonlat_a_tessera(h["center_lon_e7"] / 1e7, h["center_lat_e7"] / 1e7, 16)
        dati = r.get(16, x, y)
        assert dati
        strati = mapbox_vector_tile.decode(gzip.decompress(dati))
        p = strati["corpi"]["features"][0]["properties"]
        for k in ("id", "edificio", "gronda", "altezza", "licenza", "fonte_sagoma", "fonte_altezza", "sintetico"):
            assert k in p, k
    with open(tmp_path / "terreno.pmtiles", "rb") as f:
        r = Reader(MmapSource(f))
        assert r.metadata()["encoding"] == "terrarium"
    celle = list((tmp_path / "contesto").glob("*.json"))
    fc = json.loads(celle[0].read_text(encoding="utf-8"))
    assert fc["licenza"] == "CC BY 4.0" and len(fc["features"]) == 10
    lon, lat = fc["features"][0]["geometry"]["coordinates"][0][0]
    assert 12 < lon < 13 and 43.9 < lat < 44.2         # vicino a Rimini
    q = [f["properties"]["quota_terreno"] for f in fc["features"]]
    assert all(5 < v < 12 for v in q)
    import rasterio
    with rasterio.open(tmp_path / "dtm_cog.tif") as src:
        assert src.profile.get("compress", "").lower() == "deflate" and src.overviews(1) is not None
    cons = json.loads((tmp_path / "consumi_esempio.json").read_text(encoding="utf-8"))
    assert cons["sintetico"] and len(cons["mesi"]) == 12


def test_pmtiles_rifiuta_licenze_mescolate(tmp_path):
    feat = [{"type": "Feature", "geometry": box(12.5, 44.0, 12.5001, 44.0001).__geo_interface__,
             "properties": {"licenza": "ODbL 1.0"}}]
    with pytest.raises(ValueError, match="licenza"):
        T.corpi_pmtiles(feat, tmp_path / "x.pmtiles", "CC BY 4.0", "x")


def test_quota_corpo_dal_dtm(tmp_path):
    tif = S.dtm(tmp_path / "d.tif")
    g = box(S.X0, S.Y0, S.X0 + 20, S.Y0 + 20)
    q = D.quota(tif, g)
    assert q and abs(q["mediana"] - S.quota(S.X0 + 10, S.Y0 + 10)) < 0.5
    assert D.quota(tif, box(0, 0, 10, 10)) is None


# ---------------------------------------------------------------------------------------------- coerenza col sito
def test_interpiani_uguali_nel_sito():
    js = (QUI.parents[1] / "fase5-sito" / "sito" / "edifici_calcoli.js").read_text(encoding="utf-8")
    for uso, v in M.INTERPIANI.items():
        assert f"{uso}: {v}" in js, uso
    assert f"NETTA_SU_LORDA = {M.NETTA_SU_LORDA}" in js and f"SOVRALZO = {M.SOVRALZO}" in js


# ---------------------------------------------------------------- Fase B (04/11/2026): ortofoto AGEA per un sito
def test_ortofoto_sito_agea(tmp_path):
    import json
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    from edifici3d import ortofoto_sito as O
    # due tessere sintetiche a 20 cm in EPSG:7791 con quattro bande (la quarta, infrarosso, va scartata)
    tif = []
    for i in range(2):
        p = tmp_path / f"t{i}.tif"
        with rasterio.open(p, "w", driver="GTiff", width=500, height=500, count=4, dtype="uint8", crs="EPSG:7791",
                           transform=from_origin(797000 + i * 100, 4880000, 0.2, 0.2)) as d:
            d.write(np.full((4, 500, 500), 90 + 40 * i, dtype="uint8"))
        tif.append(p)
    s = O.prepara(tif, "prova-sito", 2023, tmp_path / "archivio")
    assert s["licenza"] == "CC BY 4.0" and "AGEA" in s["citazione"] and "2023" in s["citazione"]
    assert s["tessere"] > 0 and any("infrarosso" in a for a in s["avvisi"]) and len(s["originali"][0]["sha256"]) == 64
    base = tmp_path / "archivio" / "cc-by" / "ortofoto_siti"
    with rasterio.open(base / "prova-sito" / "ortofoto_cog.tif") as d:
        assert d.count == 3 and d.crs.to_epsg() == 3857
        assert abs(d.res[0] / (1 / np.cos(np.radians(44.05))) - 0.5) < 0.01          # 50 cm a terra
    assert (base / "prova-sito" / "ortofoto.pmtiles").stat().st_size > 1000
    assert json.loads((base / "indice.json").read_text(encoding="utf-8"))["siti"][0]["sito"] == "prova-sito"
    import pytest
    with pytest.raises(ValueError):
        O.prepara(tif, "Nome Sbagliato", 2023, tmp_path / "archivio")
    with pytest.raises(ValueError):
        O.prepara(tif, "vecchia", 2012, tmp_path / "archivio")


def test_fonti_ortofoto_toml():
    import tomllib
    from pathlib import Path
    for f in sorted((Path(__file__).resolve().parents[1] / "ortofoto").glob("*.toml")):
        d = tomllib.loads(f.read_text(encoding="utf-8"))
        for x in d["fonte"]:
            assert x["stato"] in ("confermata", "da confermare", "spenta") and x["licenza"] and x["citazione"], x["id"]
            assert "google" not in x["url"] and "arcgis" not in x["url"] and "bing" not in x["url"]
