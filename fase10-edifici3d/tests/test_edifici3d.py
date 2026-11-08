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
    assert "altezza del corpo" in testo and "numero di piani" in testo


def test_corpo_da_uvl_con_virgola_e_colmo():
    # WMS (nomi con l'iniziale maiuscola, virgola decimale): H_uvl intero = altezza; H_COLMO quota assoluta
    p = {"Id_e": "x", "Edi_id_e": "E", "H_uvl": "6", "H_GRONDA": "Null", "H_COLMO": "21,3", "B_uvl": "12,3",
         "Tipo_fonte": "SIT", "Qualita": "20"}
    c = U.corpo_da(p, box(0, 0, 10, 10))
    assert c.gronda == 6.0 and c.colmo == 9.0 and c.tetto == "capanna" and c.quota_terreno == 12.3
    assert c.licenza == "CC BY 4.0" and "H_UVL" in c.fonte_altezza and "H_COLMO − B_UVL" in c.fonte_altezza
    assert U.corpo_da({"H_uvl": "Null"}, box(0, 0, 10, 10)) is None


def test_altezze_dbtr_regole_del_geopackage():
    """Regole verificate il 07/11/2026 sul DBTR di Rimini contro DTM 2025 e DSM LiDAR 2019 (README della fase 10)."""
    a = U.altezze({"H_UVL": 7.0, "B_UVL": 5.2, "H_GRONDA": 5.4, "H_COLMO": 0.0})
    assert a["gronda"] == 7.0 and a["colmo"] is None and a["tipo"] == "relativa"     # gronda come quota: non usata
    a = U.altezze({"H_UVL": 18.37, "B_UVL": 6.02, "H_GRONDA": 0.0, "H_COLMO": 0.0})
    assert a["gronda"] == pytest.approx(12.35) and a["tipo"] == "assoluta"           # H_UVL decimale = quota del tetto
    assert U.altezze({"H_UVL": 27.31, "B_UVL": 27.3})["gronda"] is None              # quota senza altezza
    assert U.altezze({"H_UVL": 0.0, "B_UVL": 3.0})["tipo"] == "nessuna"
    assert U.altezze({"H_UVL": 66.0, "B_UVL": 60.5})["gronda"] == 5.5                # intero in collina: quota
    assert U.altezze({"H_UVL": 7.0, "B_UVL": 60.5})["gronda"] == 7.0                 # intero in collina: altezza
    # Faenza (07/11/2026): molti decimali sotto la base → convenzione «altezze», niente quote neanche sopra la base
    faenza = [{"H_UVL": 6.5 + i % 5, "B_UVL": 33.0} for i in range(40)] + [{"H_UVL": 44.5, "B_UVL": 37.5}]
    assert U.convenzione(faenza) == "altezze"
    assert U.altezze({"H_UVL": 44.5, "B_UVL": 37.5}, "altezze")["gronda"] == 44.5     # campanile, non 7 m
    assert U.altezze({"H_UVL": 24.0, "B_UVL": 16.72}, "altezze")["gronda"] == 24.0
    rimini = [{"H_UVL": 18.37 + i, "B_UVL": 6.02} for i in range(40)]
    assert U.convenzione(rimini) == "quote"
    a = U.altezze({"H_UVL": 9.0, "B_UVL": 2.0, "H_COLMO": 13.5})
    assert a["colmo"] == 11.5                                                        # 13,5 − 2,0
    assert U.altezze({"H_UVL": 9.0, "B_UVL": 2.0, "H_COLMO": 10.0})["colmo"] is None  # colmo sotto la gronda
    a = U.altezze({"H_UVL": 9.2, "B_UVL": 32.8, "H_COLMO": 9.9})                     # Faenza: decimali = altezze
    assert a["gronda"] == 9.2 and a["tipo"] == "relativa" and a["colmo"] == pytest.approx(9.9)


def test_gpkg_sintetico_con_nomi_veri_fori_ed_edifici(tmp_path):
    """GeoPackage sintetico con gli strati e le colonne dell'estrazione vera (V_UVL_GPG, V_EDI_GPG, V_EDI_CT_USO_AVM)."""
    import numpy as np
    import pyogrio.raw as R
    from shapely import to_wkb
    from shapely.geometry import Polygon
    gpkg = tmp_path / "estraz_procons.gpkg"
    corte = Polygon([(0, 0), (40, 0), (40, 30), (0, 30)], [[(10, 10), (30, 10), (30, 20), (10, 20)]])
    g = [corte, box(40, 0, 50, 30), box(100, 100, 110, 110)]
    g = [Polygon([(x + 785000, y + 4884000) for x, y in p.exterior.coords], [[(x + 785000, y + 4884000) for x, y in r.coords] for r in p.interiors]) for p in g]
    campi = {"ID_E": np.array(["u1", "u2", "u3"], dtype=object), "EDI_ID_E": np.array(["e1", "e1", "e2"], dtype=object),
             "H_UVL": np.array([12.0, 15.0, 0.0], dtype="float32"), "B_UVL": np.array([7.0, 7.1, 6.0]),
             "H_GRONDA": np.array([0.0, 0.0, 0.0], dtype="float32"), "H_COLMO": np.array([22.5, 0.0, 0.0], dtype="float32"),
             "TIPO_FONTE": np.array(["DTM DSM 2008"] * 3, dtype=object), "QUALITA": np.array([20.0, 20.0, 20.0]),
             "D_TETTO": np.array(["Non assegnato"] * 3, dtype=object), "D_TY_PORZ": np.array(["generica"] * 3, dtype=object),
             "DATA_DA": np.array([20080101.0] * 3), "DATA_A": np.array([20081231.0] * 3)}
    R.write(str(gpkg), np.array([to_wkb(x) for x in g], dtype=object), list(campi.values()), fields=list(campi), layer="V_UVL_GPG",
            driver="GPKG", geometry_type="Polygon", crs="EPSG:7791")
    e = {"ID_E": np.array(["e1", "e2"], dtype=object), "FOGLIO": np.array([74.0, 0.0]), "NUMERO": np.array(["1100 ", None], dtype=object),
         "NOME": np.array(["Palazzo di prova", None], dtype=object), "D_TY_EDI": np.array(["edificio monumentale", "baracca"], dtype=object),
         "D_STAT_E": np.array(["in esercizio", "in esercizio"], dtype=object), "COD_COM": np.array(["H294", "H294"], dtype=object)}
    R.write(str(gpkg), np.array([to_wkb(g[0].union(g[1])), to_wkb(g[2])], dtype=object), list(e.values()), fields=list(e), layer="V_EDI_GPG",
            driver="GPKG", geometry_type="Polygon", crs="EPSG:7791", append=True)
    u = {"ID_E": np.array(["e1"], dtype=object), "CT_USO": np.array([303], dtype="int32"), "D_CT_USO": np.array(["sede di scuola"], dtype=object)}
    R.write(str(gpkg), None, list(u.values()), fields=list(u), layer="V_EDI_CT_USO_AVM", driver="GPKG", append=True)
    righe = U.leggi_gpkg(gpkg)
    assert len(righe) == 3 and righe[0][0]["ID_E"] == "u1" and len(righe[0][1].interiors) == 1
    edi = U.leggi_edifici(gpkg)
    assert edi["e1"]["D_CT_USO"] == "sede di scuola"
    ctl = U.controlla([p for p, _ in righe])
    assert ctl["corpi"] == 3 and ctl["edifici"] == 2 and ctl["colmi"] == 1 and not ctl["mancanti"]
    from edifici3d.__main__ import main
    assert main(["prepara", "--gpkg", str(gpkg), "--archivio", str(tmp_path / "a"), "--archivi-json"]) == 0
    out = tmp_path / "a" / "cc-by" / "er" / "prodotti"
    ind = json.loads((out / "indice.json").read_text(encoding="utf-8"))
    assert ind["corpi"] == 2 and ind["licenza"] == "CC BY 4.0" and "CC BY 4.0" in ind["attribuzione"] and ind["nome"] == "DBTR Emilia-Romagna"
    fs = [f for c in out.glob("contesto/*.json") for f in json.loads(c.read_text(encoding="utf-8"))["features"]]
    u1 = next(f for f in fs if f["properties"]["id"] == "u1")
    assert len(u1["geometry"]["coordinates"]) == 2                                  # cortile
    assert u1["properties"]["edificio"] == "e1" and u1["properties"]["foglio"] == "74" and u1["properties"]["numero"] == "1100"
    assert u1["properties"]["uso"] == "scuola" and u1["properties"]["colmo"] == 15.5 and u1["properties"]["area"] == 1000.0
    arch = json.loads((tmp_path / "a" / "archivi.json").read_text(encoding="utf-8"))
    assert arch["archivi"][0]["base"] == "/edifici3d/cc-by/er/prodotti/"
    assert "CC BY 4.0" in (tmp_path / "a" / "cc-by" / "er" / "LICENZE.txt").read_text(encoding="utf-8")


def test_dtm_ritaglio_da_zip_senza_estrarre(tmp_path):
    import zipfile
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    from edifici3d import dtm_locale as DL
    tif = tmp_path / "DTM5x5_prova_SE_7791.tif"
    with rasterio.open(tif, "w", driver="GTiff", width=600, height=400, count=1, dtype="float32", crs="EPSG:7791", nodata=-9999,
                       transform=from_origin(780000, 4890000, 5, 5)) as d:
        a = np.tile(np.arange(600, dtype="float32"), (400, 1)); a[:, :10] = -9999
        d.write(a[None])
    z = tmp_path / "DTM5x5_prova_SE_7791.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zz:
        zz.write(tif, tif.name); zz.writestr("licenza/x.pdf", b"x")
    assert DL.percorso_gdal(z).startswith("/vsizip/") and DL.grande(z)
    e = DL.ritaglia(z, (781000, 4888500, 782000, 4889500), tmp_path / "r.tif", margine=50)
    assert e["celle"] == [220, 220] and e["riquadro"] == [780950.0, 4888450.0, 782050.0, 4889550.0]
    with rasterio.open(tmp_path / "r.tif") as r:
        assert r.crs.to_epsg() == 7791 and float(r.read(1)[0, 0]) == 190.0 and r.profile["compress"] == "deflate"
    with pytest.raises(ValueError, match="fuori"):
        DL.ritaglia(z, (700000, 4800000, 701000, 4801000), tmp_path / "x.tif")


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


def test_pmtiles_sagoma_autointersecante(tmp_path):
    # Lugo, 07/11/2026: una sagoma con due vertici a 5 mm diventa autointersecante dopo l'arrotondamento a 7 decimali;
    # il ritaglio sulla tessera dava una GeometryCollection e mapbox_vector_tile si fermava. Ora resta solo il poligono.
    farfalla = {"type": "Polygon", "coordinates": [[[12.5, 44.0], [12.5002, 44.0002], [12.5002, 44.0], [12.5, 44.0002], [12.5, 44.0]]]}
    feat = [{"type": "Feature", "geometry": farfalla, "properties": {"licenza": "CC BY 4.0", "id": "x"}},
            {"type": "Feature", "geometry": box(12.5003, 44.0, 12.5004, 44.0001).__geo_interface__,
             "properties": {"licenza": "CC BY 4.0", "id": "y"}}]
    n = T.corpi_pmtiles(feat, tmp_path / "x.pmtiles", "CC BY 4.0", "x")
    assert n > 0 and (tmp_path / "x.pmtiles").stat().st_size > 0
    from shapely.geometry import GeometryCollection, Polygon, LineString
    gc = GeometryCollection([Polygon([(0, 0), (1, 0), (1, 1)]), LineString([(0, 0), (2, 2)])])
    assert T._solo_poligoni(gc).geom_type == "Polygon" and T._solo_poligoni(LineString([(0, 0), (1, 1)])) is None


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


def test_shapefile_e_piu_comuni(tmp_path):
    """Cartella Shapefile con gli stessi nomi (Faenza) e due comuni nello stesso archivio cc-by/er/."""
    import numpy as np
    import pyogrio.raw as R
    from shapely import to_wkb
    def comune(cartella, dx, ids, driver):
        cartella.mkdir()
        g = [box(785000 + dx + 20 * k, 4884000, 785010 + dx + 20 * k, 4884010) for k in range(len(ids))]
        campi = {"ID_E": np.array(ids, dtype=object), "EDI_ID_E": np.array([f"e{i}" for i in ids], dtype=object),
                 "H_UVL": np.array([9.0] * len(ids)), "B_UVL": np.array([5.0] * len(ids))}
        dest = cartella / ("V_UVL_GPG.shp" if driver == "ESRI Shapefile" else "estraz_procons.gpkg")
        R.write(str(dest), np.array([to_wkb(x) for x in g], dtype=object), list(campi.values()), fields=list(campi),
                layer="V_UVL_GPG", driver=driver, geometry_type="Polygon", crs="EPSG:7791")
        return cartella if driver == "ESRI Shapefile" else dest
    a = comune(tmp_path / "faenza", 0, ["f1", "f2"], "ESRI Shapefile")
    b = comune(tmp_path / "lugo", 500, ["l1", "f2"], "GPKG")            # f2 in tutti e due: una volta sola
    assert len(U.leggi_gpkg(a)) == 2 and U.leggi_edifici(a) == {}
    assert main(["prepara", "--gpkg", str(a), str(b), "--archivio", str(tmp_path / "x")]) == 0
    ind = json.loads((tmp_path / "x" / "cc-by" / "er" / "prodotti" / "indice.json").read_text(encoding="utf-8"))
    assert ind["corpi"] == 3 and [x["uvl_nuove"] for x in ind["fonte_edifici"]] == [2, 1]


def test_indicatori_con_cortile_python_e_sito_uguali():
    """Corpo a corte (30×30 con cortile 10×10): area netta, pareti del cortile, stessi numeri in Python e nel sito."""
    import shutil
    import subprocess
    from shapely.geometry import Polygon
    node = shutil.which("node")
    if not node:
        pytest.skip("node non installato")
    est = [(0, 0), (30, 0), (30, 30), (0, 30)]
    foro = [(10, 10), (20, 10), (20, 20), (10, 20)]
    c = M.Corpo(id="a", edificio="E", sagoma=Polygon(est, [foro]), quota_terreno=0, gronda=10)
    py = M.indicatori(M.Edificio("E", [c]))
    assert py["superficie_pavimento_terra"] == pytest.approx(800) and py["volume_lordo"] == pytest.approx(8000)
    assert py["pareti_esposte"] == pytest.approx((120 + 40) * 10)
    prova = r'''
const E = require(process.argv[1]);
const c = { id: "a", edificio: "E", ring: JSON.parse(process.argv[2]), buchi: [JSON.parse(process.argv[3])], gronda: 10 };
const i = E.indicatori([c]);
console.log(JSON.stringify({ i, a: E.areaCorpo(c), nelForo: E.dentroCorpo([15, 15], c), dentro: E.dentroCorpo([5, 5], c),
  s: E.superfici([c]).superficie_lorda.valore }));
'''
    out = subprocess.run([node, "-e", prova, str(QUI.parents[1] / "fase5-sito" / "sito" / "edifici_calcoli.js"),
                          json.dumps(est), json.dumps(foro)], capture_output=True, text=True, encoding="utf-8", check=True).stdout
    d = json.loads(out)
    assert d["a"] == pytest.approx(800) and d["nelForo"] is False and d["dentro"] is True
    for k in ("volume_lordo", "superficie_pavimento_terra", "pareti_esposte", "superficie_disperdente", "s_su_v"):
        assert d["i"][k] == pytest.approx(py[k]), k
    for s_ in M.SETTORI:
        assert d["i"]["pareti_per_orientamento"][s_] == pytest.approx(py["pareti_per_orientamento"][s_]), s_
    assert d["s"] == pytest.approx(800 * M.stima_piani(10))


def test_archivio_per_comune_archivi_json_e_controllo(tmp_path):
    """prepara --comune: archivio autonomo cc-by/er/<comune>/; archivi-json con i comuni prima delle prove OSM; pipeline
    LiDAR che trova i corpi dei comuni; controlla-archivio senza problemi."""
    import numpy as np
    import pyogrio.raw as R
    from shapely import to_wkb
    from edifici3d import pipeline as PL
    for k, nome in enumerate(("rimini", "riccione")):
        d = tmp_path / "dbtr" / nome; d.mkdir(parents=True)
        g = [box(785000 + 1000 * k + 20 * i, 4884000, 785010 + 1000 * k + 20 * i, 4884010) for i in range(3)]
        campi = {"ID_E": np.array([f"{nome}{i}" for i in range(3)], dtype=object), "EDI_ID_E": np.array([f"e{nome}"] * 3, dtype=object),
                 "H_UVL": np.array([9.0, 6.0, 12.0]), "B_UVL": np.array([5.0] * 3)}
        R.write(str(d / "estraz_procons.gpkg"), np.array([to_wkb(x) for x in g], dtype=object), list(campi.values()), fields=list(campi),
                layer="V_UVL_GPG", driver="GPKG", geometry_type="Polygon", crs="EPSG:7791")
        assert main(["prepara", "--comune", nome, "--gpkg", str(d / "estraz_procons.gpkg"), "--archivio", str(tmp_path / "a")]) == 0
    prova = tmp_path / "a" / "odbl" / "rimini-prova" / "prodotti"; prova.mkdir(parents=True)
    (prova / "indice.json").write_text(json.dumps({"licenza": "ODbL 1.0", "prova": True, "nome": "prova", "corpi": 1}), encoding="utf-8")
    with pytest.raises(SystemExit):
        main(["prepara", "--comune", "Nome Sbagliato", "--gpkg", str(tmp_path / "dbtr" / "rimini"), "--archivio", str(tmp_path / "a")])
    # 07/11/2026 (decisione di Paolo): l'archivio di prova OSM non si elenca più di predefinito (ripiego OSM al volo)
    # (07/11/2026 sera) senza lidar/indice.json niente «lidar» (la pagina non chiede un file che non c'è)
    assert main(["archivi-json", "--archivio", str(tmp_path / "a"), "--con-prova"]) == 0
    assert "lidar" not in json.loads((tmp_path / "a" / "archivi.json").read_text(encoding="utf-8"))
    (tmp_path / "a" / "cc-by" / "er" / "prodotti" / "lidar").mkdir(parents=True)
    (tmp_path / "a" / "cc-by" / "er" / "prodotti" / "lidar" / "indice.json").write_text("{}", encoding="utf-8")
    assert main(["archivi-json", "--archivio", str(tmp_path / "a"), "--con-prova"]) == 0
    aj = json.loads((tmp_path / "a" / "archivi.json").read_text(encoding="utf-8"))
    assert [x["base"] for x in aj["archivi"]] == ["/edifici3d/cc-by/er/riccione/prodotti/", "/edifici3d/cc-by/er/rimini/prodotti/",
                                                  "/edifici3d/odbl/rimini-prova/prodotti/"]
    assert aj["archivi"][1]["nome"] == "DBTR Emilia-Romagna – Rimini" and aj["lidar"] == "/edifici3d/cc-by/er/prodotti/"
    assert len(aj["archivi"][0]["riquadro"]) == 4
    # codice ISTAT del comune (confine del comune come zona coperta nella pagina); niente per le prove OSM
    assert [x.get("istat") for x in aj["archivi"]] == ["099013", "099014", None]
    ind = json.loads((tmp_path / "a" / "cc-by" / "er" / "rimini" / "prodotti" / "indice.json").read_text(encoding="utf-8"))
    assert ind["istat"] == "099014" and "parziale" not in ind
    for comando in (["archivi-json", "--archivio", str(tmp_path / "a")], ["archivi-json", "--archivio", str(tmp_path / "a"), "--senza-prova"]):
        assert main(comando) == 0
        assert [x["base"] for x in json.loads((tmp_path / "a" / "archivi.json").read_text(encoding="utf-8"))["archivi"]] == [
            "/edifici3d/cc-by/er/riccione/prodotti/", "/edifici3d/cc-by/er/rimini/prodotti/"]
    # un indice senza istat (archivio di Rimini preparato prima del 07/11) lo prende dalla tabella; un'estrazione parziale no
    del ind["istat"]; ind["comune"] = "rimini"
    (tmp_path / "a" / "cc-by" / "er" / "rimini" / "prodotti" / "indice.json").write_text(json.dumps(ind), encoding="utf-8")
    assert main(["archivi-json", "--archivio", str(tmp_path / "a")]) == 0
    assert json.loads((tmp_path / "a" / "archivi.json").read_text(encoding="utf-8"))["archivi"][1]["istat"] == "099014"
    ind["parziale"] = True
    (tmp_path / "a" / "cc-by" / "er" / "rimini" / "prodotti" / "indice.json").write_text(json.dumps(ind), encoding="utf-8")
    assert main(["archivi-json", "--archivio", str(tmp_path / "a")]) == 0
    assert "istat" not in json.loads((tmp_path / "a" / "archivi.json").read_text(encoding="utf-8"))["archivi"][1]
    with pytest.raises(SystemExit):
        main(["prepara", "--comune", "rimini", "--istat", "99014", "--gpkg", str(tmp_path / "dbtr" / "rimini" / "estraz_procons.gpkg"),
              "--archivio", str(tmp_path / "a")])
    pl = PL.Pipeline(PL.carica_zona("rimini"), tmp_path / "a", tmp_path / "stato")
    corpi = PL.leggi_corpi(pl.contesti(), pl.z, pl.griglia, pl.lato)
    assert len(corpi) == 6                                          # i corpi di tutti e due i comuni
    from edifici3d.__main__ import controlla_archivio
    r = controlla_archivio(tmp_path / "a" / "cc-by" / "er" / "rimini" / "prodotti", [(12.5654, 44.0608, "lontano")])
    assert r["corpi"] == 3 and r["gronda_m"]["mediana"] == 9.0 and r["problemi"] == ["punto «lontano»: nessun edificio entro 30 m"]
    assert r["terreno"] == "rotta del server" and not any("terreno" in x for x in r["avvisi"])
