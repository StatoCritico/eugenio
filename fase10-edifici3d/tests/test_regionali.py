"""Prove del blocco «edifici fuori Emilia-Romagna» (05/11/2026): adattatori dei DB topografici di Lombardia, FVG e
Liguria su piccoli campioni scaricati dal vivo (tests/dati/, CC BY 4.0 delle Regioni, attribuzione nel file), zone
LiDAR di Bolzano e Trento, copertura delle fonti nella pipeline e fonti a più file con indice. Nessuna rete: i servizi
si provano con un trasporto httpx finto.

Dalla cartella fase10-edifici3d: `python -m pytest tests`."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
import numpy as np
import pytest

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent))

from edifici3d import coperture as CO, fonti as F, pipeline as PL, regionali as R  # noqa: E402
from edifici3d.__main__ import _campione, main  # noqa: E402

DATI = QUI / "dati"


def _dtm_costante(dest: Path, riquadro, valore: float, crs: str, passo: float = 1.0) -> Path:
    import rasterio
    from rasterio.transform import from_origin
    x0, y0, x1, y1 = riquadro
    w, h = int((x1 - x0) / passo), int((y1 - y0) / passo)
    with rasterio.open(dest, "w", driver="GTiff", width=w, height=h, count=1, dtype="float32", crs=crs,
                       transform=from_origin(x0, y1, passo, passo), nodata=-9999.0) as d:
        d.write(np.full((h, w), valore, dtype="float32"), 1)
    return dest


# ---------------------------------------------------------------------------------------------- adattatori
def test_lombardia_dbgt_campione():
    righe, crs = R.leggi_file(DATI / "lombardia_dbgt_campione.geojson")
    assert len(righe) == 8 and crs in ("EPSG:4326", "EPSG:4979")          # GeoJSON dell'ArcGIS: WGS84 con le z
    ctl = R.controlla(righe, "lombardia_dbgt")
    assert not ctl["mancanti"] and "8 su 8" in ctl["coerenza"]
    corpi, res = R.corpi(righe, "lombardia_dbgt", "EPSG:7791", crs)
    assert res["corpi"] == 8 and not res["scarti"]
    c = next(x for x in corpi if x.id == "UN_VOL_57115")
    assert c.edificio == "EDIFC_4831" and abs(c.gronda - 22.264) < 1e-6
    assert abs(c.quota_terreno - (146.674 - 22.264)) < 0.01                  # terreno = UN_VOL_QE − UN_VOL_AV
    assert c.licenza == "CC BY 4.0" and "DBGT Lombardia" in c.fonte_sagoma and "da verificare" in c.fonte_altezza
    x0, y0, x1, y1 = c.sagoma.bounds                                         # metri in EPSG:7791, a Milano
    assert 514600 < x0 < 514900 and 5034400 < y0 < 5034700 and 50 < c.area < 60
    assert len({x.edificio for x in corpi}) < len(corpi)                     # più corpi per edificio (CEDIUV)


def test_lombardia_porzione_con_base_sotto_terra():
    p = {"CLASSID": "X", "CEDIUV": "E", "UN_VOL_AV": 26.068, "UN_VOL_QE": 150.0, "UN_VOL_POR": "03"}
    from shapely.geometry import box
    c = R.LOMBARDIA.corpo(p, box(0, 0, 10, 10), 150.0 - 29.57, None)
    assert abs(c.quota_terreno - (150.0 - 26.068)) < 1e-6 and c.extra["base_sotto_terra_m"] == 3.5
    assert R.LOMBARDIA.corpo({**p, "UN_VOL_AV": 0, "UN_VOL_QE": None}, box(0, 0, 10, 10), None, None) is None


def test_fvg_ctrn_campione():
    righe, crs = R.leggi_file(DATI / "fvg_ctrn_campione.geojson")
    assert "6708" in crs
    assert "6 su 6" in R.controlla(righe, "fvg_ctrn")["coerenza"]
    corpi, res = R.corpi(righe, "fvg_ctrn", "EPSG:6708", crs)
    assert res["corpi"] == 6 and res["edifici"] == 6
    c = next(x for x in corpi if x.id == "44937")
    assert c.gronda == 5.88 and c.quota_terreno == 256.32 and c.uso == "residenziale"
    assert "QUOTA_GRONDA − QUOTA_PIEDE" in c.fonte_altezza and abs(c.area - 97.2) < 1.0
    # con un DTM la quota del terreno viene dal DTM
    corpi7791, _ = R.corpi(righe, "fvg_ctrn", "EPSG:7791", crs)                 # anche in un'altra proiezione
    assert len(corpi7791) == 6 and abs(next(x for x in corpi7791 if x.id == "44937").area - 97.2) < 1.5


def test_liguria_ctr3d_serve_il_dtm(tmp_path):
    righe, crs = R.leggi_file(DATI / "liguria_ctr3d_campione.geojson")
    assert "3003" in crs and "5 su 5" in R.controlla(righe, "liguria_ctr3d")["coerenza"]
    senza, res = R.corpi(righe, "liguria_ctr3d", "EPSG:7791", crs)
    assert senza == [] and res["scarti"] == {"manca la quota del terreno (DTM)": 5}
    # DTM costante a 137 m: il valore letto dal vivo (GetFeatureInfo del DTM 2023) nel punto del primo edificio
    sag = [R._poligono(g)[0] for _, g in righe]
    from pyproj import Transformer
    from shapely.ops import transform
    tr = Transformer.from_crs("EPSG:3003", "EPSG:7791", always_xy=True)
    b = [transform(tr.transform, s).bounds for s in sag]
    riq = (min(x[0] for x in b) - 20, min(x[1] for x in b) - 20, max(x[2] for x in b) + 20, max(x[3] for x in b) + 20)
    dtm = _dtm_costante(tmp_path / "dtm.tif", [round(v) for v in riq], 137.0, "EPSG:7791")
    corpi, res = R.corpi(righe, "liguria_ctr3d", "EPSG:7791", crs, dtm)
    zeta = {str(p["id"]): R._poligono(g)[1] for p, g in righe}
    assert res["corpi"] == 5
    for c in corpi:
        assert abs(c.gronda - (zeta[c.id] - 137.0)) < 0.01 and c.quota_terreno == 137.0
    assert next(c for c in corpi if c.id == "257123_656").gronda == pytest.approx(4.02, abs=0.01)


def test_liguria_scarti():
    from shapely.geometry import box
    g = box(0, 0, 10, 10)
    base = {"id": "1", "def_sotterr": "Non sotterraneo", "def_stato": "In esercizio", "def_porz_est": "Ingombro al suolo"}
    assert R.LIGURIA.corpo(base, g, 110.0, 100.0).gronda == 10.0
    assert R.LIGURIA.corpo({**base, "def_sotterr": "Sotterraneo"}, g, 110.0, 100.0) is None
    assert R.LIGURIA.corpo({**base, "def_porz_est": "Aggetto"}, g, 110.0, 100.0) is None
    assert R.LIGURIA.corpo({**base, "def_stato": "Diruto"}, g, 110.0, 100.0) is None
    assert R.LIGURIA.corpo(base, g, 100.5, 100.0) is None                   # meno di 1,5 m: non è un edificio


def test_prepara_regione_cli(tmp_path, capsys):
    arch = tmp_path / "arch"
    assert main(["--zona", "lombardia", "prepara-regione", "--file", str(DATI / "lombardia_dbgt_campione.geojson"),
                 "--archivio", str(arch)]) == 0
    out = json.loads(capsys.readouterr().out)
    prod = arch / "cc-by" / "lom" / "prodotti"
    assert out["corpi"] == 8 and out["crs"] == "EPSG:7791" and (prod / "corpi.pmtiles").exists()
    ind = json.loads((prod / "indice.json").read_text(encoding="utf-8"))
    assert ind["fonte_edifici"]["adattatore"] == "lombardia_dbgt" and "Regione Lombardia" in ind["attribuzione"]
    cella = json.loads(next((prod / "contesto").glob("*.json")).read_text(encoding="utf-8"))
    f = cella["features"][0]
    assert 9.18 < f["geometry"]["coordinates"][0][0][0] < 9.20 and f["properties"]["licenza"] == "CC BY 4.0"


def test_prepara_regione_senza_dtm_in_liguria_fallisce(tmp_path):
    with pytest.raises(ValueError, match="nessun corpo"):
        main(["--zona", "liguria", "prepara-regione", "--file", str(DATI / "liguria_ctr3d_campione.geojson"),
              "--archivio", str(tmp_path)])


def test_toml_regionali_coerenti():
    for nome, ad in (("lombardia", "lombardia_dbgt"), ("friuli_venezia_giulia", "fvg_ctrn_ed2"), ("liguria", "liguria_ctr3d")):
        z = F.carica_zona(nome)
        f = z["fonti"]["edifici"]
        assert f["adattatore"] == ad and f["licenza"] == "CC BY 4.0" and f["servizio"].startswith("https://")
        assert z["zona"]["crs"].startswith("EPSG:") and "geodati.gov.it" in f["scheda"]
    # FVG (08/11/2026): edizione 2 predefinita, edizione 1 scelta dai campi del file
    f = F.carica_zona("friuli_venezia_giulia")["fonti"]["edifici"]
    assert f["alternativi"] == ["fvg_ctrn"]
    assert R.scegli_adattatore(f, [({"ID": 1, "ALTEZZA": 6, "QUOTA_PIEDE": 1, "QUOTA_GRONDA": 7, "NOME": "x"}, None)]).chiave == "fvg_ctrn"
    assert R.scegli_adattatore(f, [({"ID1": 1, "ALTEZZA": 6, "QUOTA_PIEDE": 1, "QUOTA_GRONDA": 7, "NOME": "x",
                                     "DATA_VOLO": "2003-05-23"}, None)]).chiave == "fvg_ctrn_ed2"


def test_campione_a_pagine_e_errori(tmp_path):
    chiamate = []

    def risposta(req):
        chiamate.append(str(req.url))
        n = int(req.url.params.get("count") or req.url.params.get("resultRecordCount"))
        inizio = int(req.url.params.get("startIndex") or req.url.params.get("resultOffset") or 0)
        tot = 5
        fs = [{"type": "Feature", "properties": {"ID": i}, "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}}
              for i in range(inizio, min(inizio + n, tot))]
        return httpx.Response(200, json={"type": "FeatureCollection", "features": fs,
                                         "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::6708"}}})
    z = F.carica_zona("friuli_venezia_giulia")
    cl = httpx.Client(transport=httpx.MockTransport(risposta))
    r = R.scarica_campione(z["fonti"]["edifici"], (1, 2, 3, 4), tmp_path / "c.geojson", max_oggetti=10, pagina=2,
                           client=cl, pausa=0)
    assert r["oggetti"] == 5 and len(chiamate) == 3 and "bbox=1%2C2%2C3%2C4%2CEPSG%3A6708" in chiamate[0]
    assert "EDIFICATO_CTRN_ED2_110" in chiamate[0]       # edizione 2 dall'08/11/2026
    lom = F.carica_zona("lombardia")["fonti"]["edifici"]
    u = R.url_campione(lom, (1, 2, 3, 4), "EPSG:7791", 10)
    assert "/query?" in u and "returnZ=true" in u and "inSR=7791" in u and "f=geojson" in u
    errore = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    with pytest.raises(httpx.HTTPStatusError):
        R.scarica_campione(z["fonti"]["edifici"], (1, 2, 3, 4), tmp_path / "e.geojson", client=errore, pausa=0)


# ---------------------------------------------------------------------------------------------- copertura e zone
def test_copertura_riquadri_e_soglia():
    from shapely.geometry import box
    t = PL.Tessera("t", 0, 0, 1000, 1000, 0, 0)
    area = PL.area_coperta({"copertura": {"riquadri": [[0, 0, 500, 1000]]}}, "EPSG:7791", PL.ZONE)
    assert PL.copre(None, t)                                          # senza limiti: tutto coperto, come prima
    assert not PL.copre(area, t)                                      # metà tessera < 95 %
    assert PL.copre(area, t, minima=0.5)
    assert PL.copre(area, t, [box(100, 100, 200, 200)])               # edifici tutti dentro
    assert not PL.copre(area, t, [box(100, 100, 200, 200), box(700, 700, 900, 900)])
    assert PL.copre(area, t, [box(100, 100, 200, 200), box(700, 700, 900, 900)], minima=0.2)
    lontana = PL.Tessera("l", 5000, 5000, 6000, 6000, 5, 5)
    assert not PL.copre(area, lontana, minima=0.0)


def test_dsm_costa_solo_sulle_tessere_coperte():
    z = PL.carica_zona("rimini")
    f = z["fonti"]["rer_dsm_costa_2019"]
    assert PL.usabile(f)[0] and f["copertura"]["minima"] == 0.10
    pl = PL.Pipeline(z, Path("/tmp"), Path("/tmp"))
    area = pl.area("rer_dsm_costa_2019", f)
    assert 20 < area.area / 1e6 < 40                                  # fascia costiera di ~28 km²
    from shapely.geometry import box
    mare = pl.griglia[(785, 4886)]                                    # tessera tutta dentro la fascia
    entroterra = pl.griglia[(760, 4850)]                              # Valmarecchia, lontano dalla costa
    assert pl.versione("rer_dsm_costa_2019", f, mare) == "rer_dsm_costa_2019:2019"
    assert pl.versione("rer_dsm_costa_2019", f, entroterra) is None
    # un edificio nell'entroterra della tessera costiera non basta: deve cadere dentro la maschera
    t = pl.griglia[(785, 4884)]
    assert pl.versione("rer_dsm_costa_2019", f, t, [box(785050, 4884050, 785070, 4884070)]) is None
    # tessera tagliata dalla fascia: con il solo edificio dentro la maschera la fonte vale, con uno fuori grande no
    tt = next(x for x in pl.griglia.values() if 0.2 < area.intersection(box(*x.riquadro)).area / 1e6 < 0.6)
    dentro = area.intersection(box(*tt.riquadro)).representative_point()
    sag = box(dentro.x - 5, dentro.y - 5, dentro.x + 5, dentro.y + 5)
    assert pl.versione("rer_dsm_costa_2019", f, tt, [sag]) == "rer_dsm_costa_2019:2019"
    fuori = box(*tt.riquadro).difference(area.buffer(5)).representative_point()
    grande = box(fuori.x - 20, fuori.y - 20, fuori.x + 20, fuori.y + 20)
    assert pl.versione("rer_dsm_costa_2019", f, tt, [sag, grande]) is None


def test_zone_bolzano_e_trento():
    bz, tn = PL.carica_zona("bolzano"), PL.carica_zona("trento")
    assert bz["zona"]["crs"] == tn["zona"]["crs"] == "EPSG:25832"
    assert {f["id"]: f["stato"] for f in PL.elenco_fonti(bz)} == {"bz_dsm05": "attiva", "bz_dtm05": "attiva", "bz_dtm25": "attiva"}
    assert all(z["fonti"][k]["licenza"] in z["archivi"] for z in (bz, tn) for k in z["fonti"])
    g, _ = PL.griglia_tessere(bz)
    t = g[(678, 5152)]
    u = PL.Pipeline(bz, Path("/tmp"), Path("/tmp")).url(bz["fonti"]["bz_dsm05"], t)
    assert "subset=E(678000.0,679000.0)" in u and "subset=N(5152000.0,5153000.0)" in u and "scalefactor=0.5" in u
    assert "DigitalElevationModel-0.5m" in u and t.nome == "bz_678_5152"
    g, lato = PL.griglia_tessere(tn)
    assert lato == 2000 and g[(355, 2577)].nome == "tn_710_5154"
    pl = PL.Pipeline(tn, Path("/tmp"), Path("/tmp"))
    assert pl.url(tn["fonti"]["pat_dtm_2009"], g[(355, 2577)], "dsm000007_wor.tif").endswith("_dtm_1mX1m/dtm000007_wor.tif")
    # senza i corpi della Fase A le due zone restano in attesa e non entrano nella scelta automatica
    for z in (bz, tn):
        assert PL.Pipeline(z, Path("/tmp/vuoto"), Path("/tmp/vuoto_s")).esegui(subito=True)["esito"] == "in attesa"


def test_fonte_a_piu_file_mosaico(tmp_path):
    """Fonte con indice (come il LiDAR di Trento) sul campione sintetico: i DSM delle tessere diventano «file» di un
    indice; la pipeline li cerca nell'indice, li scarica e ne fa il mosaico."""
    import rasterio
    radice = tmp_path / "campione"
    _campione(radice)
    file = []
    for p in sorted((radice / "dsm").glob("*.tif")):
        with rasterio.open(p) as s:
            b = s.bounds
        file.append({"nome": p.name, "riquadro": [b.left, b.bottom, b.right, b.top]})
    (tmp_path / "indice.json").write_text(json.dumps({"crs": "EPSG:7791", "file": file}), encoding="utf-8")
    z = PL.carica_zona("campione")
    z["fonti"]["campione_dsm"]["attiva"] = False
    z["fonti"]["campione_las"]["attiva"] = False
    z["fonti"]["mosaico"] = {"tipo": "dsm", "priorita": 1, "licenza": "dati sintetici", "licenza_confermata": True,
                             "attiva": True, "attribuzione": "Dati sintetici", "versione": "fissa", "versione_fissa": "x",
                             "indice": str(tmp_path / "indice.json"), "url": "file:{radice}/dsm/{file}"}
    pl = PL.Pipeline(z, tmp_path / "a", tmp_path / "s", radice=radice)
    e = pl.esegui(subito=True)
    st = json.loads((tmp_path / "s" / "campione.json").read_text(encoding="utf-8"))
    fatte = [n for n, v in st["tessere"].items() if v["stato"] == "fatta"]
    assert e["tessere_fatte"] == len(fatte) >= 5 and all(st["tessere"][n]["fonte"] == "mosaico" for n in fatte)
    assert all(st["tessere"][n]["versione"].startswith("mosaico:x:") for n in fatte)
    assert (tmp_path / "a" / "sintetico" / "campione" / "prodotti" / "lidar" / "indice.json").exists()
    senza = [n for n, v in st["tessere"].items() if v["stato"] == "senza rilievo"]
    assert senza                                                     # le tessere del LAS non sono nell'indice
    t = pl.griglia[next(iter(pl.griglia))]
    assert len(PL.file_della_tessera({"file": file * 3}, t, 2)) <= 2                  # al più max_file_tessera


def test_indice_dalle_intestazioni(tmp_path):
    z = PL.carica_zona("trento")
    z["_file"] = str(tmp_path / "trento.toml")
    html = '<a href="../">..</a><a href="dsm000007_wor.tif">x</a><a href="dsm000008_wor.tif">y</a><a href="licenza.pdf">l</a>'
    cl = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, text=html)))
    letti = []

    def lettore(u):
        letti.append(u)
        n = int(u[-12:-8])
        return [700000.0 + n * 2000, 5150000.0, 702000.0 + n * 2000, 5152000.0], None
    r = CO.indice_fonte(z, "pat_dsm_2009", client=cl, pausa=0, lettore=lettore)
    assert r["file_elencati"] == 2 and r["nuovi"] == 2 and letti[0].endswith("_dsm_1mX1m/dsm000007_wor.tif")
    d = json.loads((tmp_path / "coperture" / "trento_pat_lidar_2009.json").read_text(encoding="utf-8"))
    assert [x["nome"] for x in d["file"]] == ["dsm000007_wor.tif", "dsm000008_wor.tif"] and d["crs"] == "EPSG:25832"
    assert CO.indice_fonte(z, "pat_dsm_2009", client=cl, pausa=0, lettore=lettore)["nuovi"] == 0   # ripresa


def test_maschera_da_raster(tmp_path):
    import rasterio
    from rasterio.transform import from_origin
    a = np.full((10, 10), -9999.0, dtype="float32")
    a[2:8, 3:6] = 5.0
    p = tmp_path / "m.tif"
    with rasterio.open(p, "w", driver="GTiff", width=10, height=10, count=1, dtype="float32", crs="EPSG:7791",
                       transform=from_origin(0, 1000, 100, 100), nodata=-9999.0) as d:
        d.write(a, 1)
    area = CO.maschera_da_raster(p, 100)
    assert abs(area.area - (600 - 100) * (300 - 100)) < 1                 # 6×3 celle ristrette di mezza cella per lato
    dest = CO.scrivi_maschera(area, tmp_path / "c" / "m.geojson", "EPSG:7791", "prova", "CC BY 4.0")
    back = PL.area_coperta({"copertura": {"maschera": str(dest)}}, "EPSG:7791", tmp_path)
    assert abs(back.area - area.area) < 1


def test_archivi_licenze_aperte(tmp_path):
    """08/11/2026: IODL 2.0, CC BY 2.5 e CC0 1.0 stanno con i DB topografici (prima di ODbL) e passano controlla-archivio."""
    import json
    from edifici3d.archivi import scrivi_archivi_json
    from edifici3d.__main__ import TESTI_LICENZA, controlla_archivio
    voci = {"odbl/er/prova/prodotti": ("ODbL 1.0", "OSM"), "iodl/pug/bari/prodotti": ("IODL 2.0", "Regione Puglia (IODL 2.0)"),
            "cc-by/bz/bolzano/prodotti": ("CC0 1.0", "Provincia di Bolzano (CC0 1.0)"),
            "cc-by/pie/torino/prodotti": ("CC BY 2.5", "Regione Piemonte (CC BY 2.5)")}
    for rel, (lic, att) in voci.items():
        d = tmp_path / rel
        (d / "contesto").mkdir(parents=True)
        (d / "indice.json").write_text(json.dumps({"licenza": lic, "attribuzione": att, "corpi": 0, "riquadro": [0, 0, 1, 1]}))
        (d / "corpi.pmtiles").write_bytes(b"x")
    basi = [v["base"] for v in scrivi_archivi_json(tmp_path)["archivi"]]
    assert basi[-1] == "/edifici3d/odbl/er/prova/prodotti/" and len(basi) == 4
    assert basi[:3] == sorted(basi[:3])
    assert set(TESTI_LICENZA) == {"CC BY 4.0", "CC BY 2.5", "IODL 2.0", "CC0 1.0"}
    for rel in list(voci)[1:]:
        assert controlla_archivio(tmp_path / rel)["problemi"] == []
    assert controlla_archivio(tmp_path / "odbl/er/prova/prodotti")["problemi"]
