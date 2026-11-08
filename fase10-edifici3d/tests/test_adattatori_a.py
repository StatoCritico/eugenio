"""Prove degli adattatori del gruppo A (08/11/2026): DBGT Lazio 2014 (Roma), DBGT Basilicata (Potenza), BDTRE Piemonte
(Torino) e lettura dello Shapefile del DBT 2020 del Comune di Milano con `lombardia_dbgt`; zone `fonti/lazio.toml`,
`basilicata.toml`, `piemonte.toml`, `lombardia_milano.toml`; supporto `edifici3d/a_comuni.py` (ritaglio sul confine,
DTM dal WCS a blocchi). Campioni scaricati dal vivo in `tests/dati/` (fonte e licenza nel file); nessuna rete: il WCS si
prova con un trasporto httpx finto.

Dalla cartella fase10-edifici3d: `python -m pytest tests/test_adattatori_a.py`."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
import numpy as np
import pytest
from shapely.geometry import Polygon, box, mapping

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent))

from edifici3d import a_comuni as AC, fonti as F, regionali as R  # noqa: E402
from edifici3d.__main__ import main  # noqa: E402

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


def test_adattatori_registrati():
    for k in ("lazio_dbgt", "basilicata_dbgt", "piemonte_bdtre"):
        assert k in R.ADATTATORI and hasattr(R.ADATTATORI[k], "coerenza")
    assert R.ADATTATORI["basilicata_dbgt"].licenza == "IODL 2.0"
    assert R.ADATTATORI["piemonte_bdtre"].licenza == "CC BY 2.5"


# ---------------------------------------------------------------------------------------------- Lazio
def test_lazio_dbgt_campione():
    righe, crs = R.leggi_file(DATI / "lazio_dbgt_campione.geojson")
    assert len(righe) == 14 and "25833" in crs
    ad = R.ADATTATORI["lazio_dbgt"]
    assert not R.controlla(righe, ad)["mancanti"]
    co = ad.coerenza(righe)
    assert "= altezza in 14 su 14" in co and "2 volumi in porzione sotterranea" in co
    corpi, res = R.corpi(righe, ad, "EPSG:25833", crs)
    assert res["corpi"] == 12 and res["scarti"] == {"altezza assente o non valida, o elemento escluso": 2}
    assert all(c.extra["porzione"] != "08" for c in corpi)
    c = next(x for x in corpi if x.id == "RM374_0000863235")                 # Policlinico Gemelli, corpo più alto
    assert c.gronda == 46.03 and c.edificio == "RM374_0001008856"
    assert abs(c.quota_terreno - (137.86 - 46.03)) < 0.01                      # terreno = UN_VOL_QE − UN_VOL_AV
    assert c.extra["anno_dato"] == "2003" and c.extra["istat"] == "058091" and c.licenza == "CC BY 4.0"
    x0, y0, _, _ = c.sagoma.bounds
    assert 286700 < x0 < 287000 and 4645100 < y0 < 4645400 and abs(c.area - 1480.1) < 1


def test_lazio_prepara_regione(tmp_path):
    assert main(["--zona", "lazio", "prepara-regione", "--file", str(DATI / "lazio_dbgt_campione.geojson"),
                 "--archivio", str(tmp_path), "--comune", "roma", "--parziale"]) == 0
    ind = json.loads((tmp_path / "cc-by/laz/roma/prodotti/indice.json").read_text(encoding="utf-8"))
    assert ind["corpi"] == 12 and ind["licenza"] == "CC BY 4.0" and ind["parziale"] is True and "istat" not in ind
    assert "Regione Lazio" in ind["attribuzione"] and ind["crs"] == "EPSG:25833"
    lon, lat = ind["centro"]
    assert 12.42 < lon < 12.44 and 41.92 < lat < 41.94                        # Gemelli, in WGS84


# ---------------------------------------------------------------------------------------------- Basilicata
def test_basilicata_dbgt_wfs(tmp_path):
    righe, crs = R.leggi_file(DATI / "basilicata_dbgt_campione.geojson")
    ad = R.ADATTATORI["basilicata_dbgt"]
    assert "25833" in crs and not R.controlla(righe, ad)["mancanti"]
    assert "z della base (geometria 3D) in 12 su 12" in ad.coerenza(righe)
    corpi, res = R.corpi(righe, ad, "EPSG:25833", crs)
    assert res["corpi"] == 10                                                  # 2 volumi «08» scartati
    c = max(corpi, key=lambda x: x.gronda)                                     # padiglione del San Carlo
    assert c.gronda == 38.64 and abs(c.area - 19833.1) < 1 and c.id.startswith("un_vol.")
    assert abs(c.quota_terreno - 744.07) < 0.01                                # senza DTM: z della base
    assert c.licenza == "IODL 2.0" and "z della base" in c.fonte_altezza
    dtm = _dtm_costante(tmp_path / "dtm.tif", (567700, 4500100, 568500, 4500800), 740.0, "EPSG:25833", 5.0)
    con, _ = R.corpi(righe, ad, "EPSG:25833", crs, dtm=dtm)
    c2 = next(x for x in con if x.id == c.id)
    assert c2.quota_terreno == 740.0 and c2.extra["quota_base_db"] == 744.07 and "DTM 740.0" in c2.fonte_altezza


def test_basilicata_zip_comunale_2d(tmp_path):
    """Shapefile del DBGT per comune (`unita_volumetrica_17076063.shp`): 2D, `ALTEZZA_VO`, `PORZIONE`, `CEDIUV`."""
    import pyogrio.raw as PR
    import shapely
    g = [box(568000, 4500000, 568020, 4500010), box(568030, 4500000, 568040, 4500010), box(568050, 4500000, 568060, 4500010)]
    campi = [np.array([12.5, 4.0, 3.0]), np.array(["01", "08", "01"], dtype=object), np.array(["01", "01", "01"], dtype=object),
             np.array(["E1", "E1", "E2"], dtype=object)]
    shp = tmp_path / "unita_volumetrica_17076063.shp"
    PR.write(str(shp), shapely.to_wkb(g), campi, ["ALTEZZA_VO", "PORZIONE", "TIPO_PORZ", "CEDIUV"],
             driver="ESRI Shapefile", geometry_type="Polygon", crs="EPSG:25833")
    righe, crs = R.leggi_file(shp)
    ad = R.ADATTATORI["basilicata_dbgt"]
    assert "serve --dtm" in ad.coerenza(righe)
    senza, _ = R.corpi(righe, ad, "EPSG:25833", crs)
    assert len(senza) == 2 and all(c.quota_terreno is None for c in senza)   # niente quota: la pagina usa il comune
    dtm = _dtm_costante(tmp_path / "dtm.tif", (567900, 4499900, 568100, 4500100), 801.5, "EPSG:25833", 5.0)
    con, res = R.corpi(righe, ad, "EPSG:25833", crs, dtm=dtm)
    assert res["corpi"] == 2 and {c.edificio for c in con} == {"E1", "E2"}
    assert next(c for c in con if c.edificio == "E1").gronda == 12.5 and all(c.quota_terreno == 801.5 for c in con)


def test_basilicata_prepara_cartella_iodl(tmp_path):
    zona = F.carica_zona("basilicata")
    assert F.cartella(tmp_path, zona, "IODL 2.0", "") == tmp_path / "iodl" / "bas" / ""
    assert main(["--zona", "basilicata", "prepara-regione", "--file", str(DATI / "basilicata_dbgt_campione.geojson"),
                 "--archivio", str(tmp_path), "--comune", "potenza", "--istat", "076063"]) == 0
    ind = json.loads((tmp_path / "iodl/bas/potenza/prodotti/indice.json").read_text(encoding="utf-8"))
    assert ind["licenza"] == "IODL 2.0" and ind["istat"] == "076063" and ind["corpi"] == 10
    assert not (tmp_path / "cc-by").exists()                                    # mai mescolato con CC BY


# ---------------------------------------------------------------------------------------------- Piemonte
def test_piemonte_bdtre_campione():
    righe, crs = R.leggi_file(DATI / "piemonte_bdtre_campione.geojson")
    ad = R.ADATTATORI["piemonte_bdtre"]
    assert "32632" in crs and not R.controlla(righe, ad)["mancanti"]
    assert "altezza > 0 in 8 su 10" in ad.coerenza(righe)
    corpi, res = R.corpi(righe, ad, "EPSG:32632", crs)
    assert res["corpi"] == 8 and res["edifici"] == 8                          # nessun cediuv: un edificio per volume
    c = max(corpi, key=lambda x: x.gronda)                                     # grattacielo Intesa Sanpaolo
    assert c.gronda == 166.0 and c.id == c.edificio and c.quota_terreno is None
    assert c.extra["anno_dato"] == "2017" and "DSM-DTM" in c.extra["modo_prod"] and c.licenza == "CC BY 2.5"
    x0, y0, _, _ = c.sagoma.bounds
    assert 394650 < x0 < 394800 and 4991450 < y0 < 4991600


def test_piemonte_porzione_testuale_sotterranea():
    ad = R.ADATTATORI["piemonte_bdtre"]
    g = box(0, 0, 10, 10)
    assert ad.corpo({"uuid": "a", "un_vol_av": "9", "un_vol_por": "al suolo"}, g, None, None).gronda == 9.0
    assert ad.corpo({"uuid": "b", "un_vol_av": "3", "un_vol_por": "sotterranea"}, g, None, None) is None
    assert ad.corpo({"uuid": "c", "un_vol_av": "", "un_vol_por": "al suolo"}, g, None, None) is None
    assert ad.corpo({"uuid": "d", "un_vol_av": "7", "un_vol_por": "al suolo"}, g, None, 230.0).quota_terreno == 230.0


def test_piemonte_prepara_regione(tmp_path):
    assert main(["--zona", "piemonte", "prepara-regione", "--file", str(DATI / "piemonte_bdtre_campione.geojson"),
                 "--archivio", str(tmp_path), "--comune", "torino", "--istat", "001272"]) == 0
    ind = json.loads((tmp_path / "cc-by/pie/torino/prodotti/indice.json").read_text(encoding="utf-8"))
    assert ind["licenza"] == "CC BY 2.5" and ind["istat"] == "001272" and ind["corpi"] == 8


# ---------------------------------------------------------------------------------------------- Milano
def test_milano_shp_dbt2020_con_lombardia_dbgt():
    """Lo Shapefile del DBT 2020 del Comune (EPSG:7791, PolygonZ, nomi ≤ 10 caratteri) entra con `lombardia_dbgt`."""
    righe, crs = R.leggi_file(DATI / "lombardia_milano_un_vol.shp")
    assert crs == "EPSG:7791" and len(righe) == 22
    ctl = R.controlla(righe, "lombardia_dbgt")
    assert not ctl["mancanti"] and "19 su 22" in ctl["coerenza"]
    corpi, res = R.corpi(righe, "lombardia_dbgt", "EPSG:7791", crs)
    assert res["corpi"] == 22 and not res["scarti"]
    c = max(corpi, key=lambda x: x.gronda)                                     # Pirellone, alto 127 m
    assert c.id == "UN_VOL_124850" and c.gronda == 125.5 and abs(c.quota_terreno - (248.034 - 125.5)) < 0.01


def test_nomi_troncati_dbf():
    """Nomi a 10 caratteri di un DBF (es. QUOTA_GRON) e maiuscole diverse: letti dagli adattatori del gruppo A."""
    from edifici3d.adattatori.a_dbgt import minuscole, primo
    p = R.nomi_completi({"UN_VOL_AV": 5.0, "QUOTA_GRON": 10.0})
    assert p["QUOTA_GRONDA"] == 10.0
    assert primo(minuscole({"Un_Vol_Av": "7"}), ("UN_VOL_AV",)) == "7"


def test_zone_toml():
    for nome, cod, lic, cart in (("lazio", "laz", "CC BY 4.0", "cc-by"), ("basilicata", "bas", "IODL 2.0", "iodl"),
                                 ("piemonte", "pie", "CC BY 2.5", "cc-by"), ("lombardia_milano", "lom", "CC BY 4.0", "cc-by")):
        z = F.carica_zona(nome)
        f = z["fonti"]["edifici"]
        assert z["zona"]["codice"] == cod and f["licenza"] == lic and z["archivi"][lic] == cart
        assert f["adattatore"] in R.ADATTATORI


# ---------------------------------------------------------------------------------------------- a_comuni
def test_ritaglia_sul_confine():
    confine = box(0, 0, 100, 100)
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"n": 1}, "geometry": mapping(box(10, 10, 20, 20))},
        {"type": "Feature", "properties": {"n": 2}, "geometry": mapping(box(95, 10, 130, 20))},    # punto interno fuori
        {"type": "Feature", "properties": {"n": 3}, "geometry": mapping(box(90, 10, 104, 20))}]}   # punto interno dentro
    assert [f["properties"]["n"] for f in AC.ritaglia(fc, confine)["features"]] == [1, 3]


def test_confine_da_file_istat(tmp_path):
    import pyogrio.raw as PR
    import shapely
    shp = tmp_path / "Com01012025_g_WGS84.shp"
    PR.write(str(shp), shapely.to_wkb([box(390000, 4985000, 400000, 4995000), box(0, 0, 1, 1)]),
             [np.array(["001272", "001001"], dtype=object), np.array(["Torino", "Altro"], dtype=object)],
             ["PRO_COM_T", "COMUNE"], driver="ESRI Shapefile", geometry_type="Polygon", crs="EPSG:32632")
    g, p = AC.confine_file(shp, "001272", "EPSG:32632")
    assert g.bounds == (390000, 4985000, 400000, 4995000) and p["nome"] == "Torino"
    g2, _ = AC.confine_file(shp, "001272", "EPSG:7791")                        # stesso fuso: riproiettato, metri vicini
    assert abs(g2.bounds[0] - 390000) < 5


def test_dtm_wcs_a_blocchi(tmp_path):
    """Due blocchi del WCS (trasporto finto) cuciti in un GeoTIFF nel sistema della zona."""
    import io
    import re
    import rasterio
    from rasterio.transform import from_origin

    def tiff(x0, x1, y0, y1, v):
        buf = io.BytesIO()
        w, h = int((x1 - x0) / 5), int((y1 - y0) / 5)
        with rasterio.MemoryFile() as mf:
            with mf.open(driver="GTiff", width=w, height=h, count=1, dtype="float32", crs="EPSG:25833",
                         transform=from_origin(x0, y1, 5, 5), nodata=-9999.0) as d:
                d.write(np.full((h, w), v, dtype="float32"), 1)
            buf.write(mf.read())
        return buf.getvalue()

    chieste = []

    def risposta(req: httpx.Request):
        u = str(req.url)
        chieste.append(u)
        e = [float(v) for v in re.search(r"subset=E\(([\d.]+),([\d.]+)\)", u).groups()]
        n = [float(v) for v in re.search(r"subset=N\(([\d.]+),([\d.]+)\)", u).groups()]
        return httpx.Response(200, content=tiff(e[0], e[1], n[0], n[1], 700.0 + e[0] / 1000), headers={"content-type": "image/tiff"})

    cl = httpx.Client(transport=httpx.MockTransport(risposta))
    fonte = {"wcs": "https://esempio.invalid/wcs", "coverage": "rsdi_wcs__dtm_5m", "crs": "EPSG:25833"}
    out = AC.dtm_wcs(fonte, (0, 0, 1500, 1000), tmp_path / "dtm5.tif", blocco=1000, client=cl, pausa=0)
    assert len(chieste) == 2 and "coverageId=rsdi_wcs__dtm_5m" in chieste[0]
    with rasterio.open(out) as s:
        a = s.read(1)
        assert s.crs.to_epsg() == 25833 and s.shape == (200, 300) and s.res == (5.0, 5.0)
        assert a[0, 0] == 700.0 and a[0, -1] == 701.0
    assert not (tmp_path / "dtm5.pezzi").exists()
