"""Prove della Fase C (LiDAR, pipeline notturna, import DXF/IFC) sul campione **sintetico** e su modelli costruiti al
volo. Nessuna rete: le fonti con URL http si provano con un trasporto httpx finto.

Dalla cartella fase10-edifici3d: `python -m pytest tests`."""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

import httpx
import numpy as np
import pytest

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent))

from edifici3d import campione as K, lidar as L, pipeline as PL, sintetico as S  # noqa: E402
from edifici3d.__main__ import _campione, demo, main  # noqa: E402


@pytest.fixture(scope="module")
def radice(tmp_path_factory):
    r = tmp_path_factory.mktemp("campione")
    _campione(r)
    return r


def _pipeline(radice, tmp, **kw):
    z = PL.carica_zona("campione")
    for k, v in kw.pop("limiti", {}).items():
        z["limiti"][k] = v
    return PL.Pipeline(z, tmp / "archivio", tmp / "stato", radice=radice, **kw)


def _falde_corpi(radice):
    """Falde di tutti i corpi dal DSM e DTM del campione (senza pipeline)."""
    riq = (S.X0 - 50, S.Y0 - 50, S.X0 + 150, S.Y0 + 100)
    gs, ts = [], []
    for nome, x0, y0, x1, y1, ij in K.tessere():
        p = radice / "dsm" / f"{nome}.tif"
        if p.exists():
            gs.append(L.ricampiona(L.leggi_raster(p), (x0, y0, x1, y1)))
            ts.append(L.ricampiona(L.leggi_raster(radice / "dtm" / f"{nome}.tif"), (x0, y0, x1, y1)))
        else:
            a, b = L.griglie_da_las(L.leggi_las(radice / "las" / f"{nome}.las"), (x0, y0, x1, y1))
            gs.append(a); ts.append(b)
    dsm, dtm = L.unisci(gs, riq), L.unisci(ts, riq)
    return {p["Id_e"]: L.falde_corpo(g, dsm, dtm) for p, g in S.uvl()}


# ---------------------------------------------------------------------------------------------- falde
def test_falde_del_campione(radice):
    r = _falde_corpi(radice)
    c1 = r["C1"]
    assert c1["stato"] == "ok" and c1["tetto"] == "capanna" and len(c1["falde"]) == 2
    assert sorted(round(f["orientamento"]) % 360 for f in c1["falde"]) == [0, 180]
    assert all(abs(f["pendenza"] - math.degrees(math.atan(3 / 7))) < 1.0 for f in c1["falde"])
    assert c1["gronda"] == pytest.approx(10, abs=0.3) and c1["colmo"] == pytest.approx(13, abs=0.3)
    c6 = r["C6"]
    assert c6["tetto"] == "capanna" and sorted(round(f["orientamento"]) for f in c6["falde"]) == [90, 270]
    assert all(abs(f["pendenza"] - 31.0) < 1.0 for f in c6["falde"])
    c7 = r["C7"]
    assert c7["tetto"] == "padiglione" and len(c7["falde"]) == 4
    assert sorted(round(f["orientamento"] / 90) % 4 for f in c7["falde"]) == [0, 1, 2, 3]
    c4 = r["C4"]
    assert c4["tetto"] == "monofalda" and abs(c4["falde"][0]["pendenza"] - 6) < 1 and abs(c4["falde"][0]["orientamento"] - 180) < 3
    for cid, h in (("C2", 10), ("C3", 22), ("C5", 7), ("C8", 13)):
        assert r[cid]["tetto"] == "piano" and r[cid]["gronda"] == pytest.approx(h, abs=0.3), cid
    assert r["C3"]["tetto"] == "piano"                       # il camino non crea falde
    assert r["C10"]["stato"] == "non presente nel rilievo"   # demolito: resta la fonte successiva
    # superficie inclinata = area in pianta / cos(pendenza)
    f = c6["falde"][0]
    assert f["superficie"] == pytest.approx(f["area_pianta"] / math.cos(math.radians(f["pendenza"])), rel=0.01)
    assert sum(x["area_pianta"] for x in c7["falde"]) == pytest.approx(20 * 16, rel=0.03)


def test_tetto_irregolare_diventa_piano():
    rng = np.random.default_rng(3)
    from shapely.geometry import box
    g = L.Griglia(np.zeros((40, 40), dtype="float32"), 0, 40, 1.0)
    g.z[:] = 10 + rng.uniform(-2, 2, g.z.shape)
    t = L.Griglia(np.zeros((40, 40), dtype="float32"), 0, 40, 1.0)
    r = L.falde_corpo(box(5, 5, 35, 35), g, t)
    assert r["stato"] == "ok" and r["tetto"] == "piano" and any("irregolari" in n for n in r["note"])


def test_salto_dentro_il_corpo_segnalato():
    from shapely.geometry import box
    g = L.Griglia(np.full((30, 40), 6.0, dtype="float32"), 0, 30, 1.0)
    g.z[:, 20:] = 15.0
    t = L.Griglia(np.zeros((30, 40), dtype="float32"), 0, 30, 1.0)
    r = L.falde_corpo(box(1, 1, 39, 29), g, t)
    assert any("salto" in n for n in r["note"])


def test_dsm_ridotto_int16_decimetri(tmp_path):
    g = L.Griglia(np.array([[12.34, np.nan], [0.04, 3276.7]], dtype="float32"), 100, 202, 1.0)
    p = L.scrivi_ridotto(g, tmp_path / "d.tif")
    import rasterio
    with rasterio.open(p) as f:
        assert f.dtypes[0] == "int16" and f.nodata == L.VUOTO_I16
        assert f.read(1).tolist() == [[123, L.VUOTO_I16], [0, 32767]]
    r = L.leggi_raster(p)
    assert r.z[0, 0] == pytest.approx(12.3) and np.isnan(r.z[0, 1])


# ---------------------------------------------------------------------------------------------- pipeline
def test_pipeline_campione_completa_e_idempotente(radice, tmp_path):
    pl = _pipeline(radice, tmp_path)
    e = pl.esegui(subito=True)
    assert e["esito"] == "completata" and e["tessere_errore"] == 0
    s = json.loads((tmp_path / "stato" / "campione.json").read_text())
    assert s["conteggi"] == {"fatta": s["totale_tessere"]} and s["totale_tessere"] == 8
    assert {v["fonte"] for v in s["tessere"].values()} == {"campione_dsm", "campione_las"}
    assert any(f["id"] == "esempio_in_attesa" and f["stato"] == "in attesa" for f in s["fonti"])
    prod = tmp_path / "archivio" / "sintetico" / "campione" / "prodotti" / "lidar"
    assert len(list((prod / "dsm").glob("*.tif"))) == 8 and (prod / "indice.json").exists()
    assert not (tmp_path / "archivio" / "sintetico" / "campione" / "grezzi" / "lidar").exists() or \
        not any((tmp_path / "archivio" / "sintetico" / "campione" / "grezzi" / "lidar").rglob("*.*"))   # grezzi cancellati
    celle = {}
    for p in (prod / "falde").glob("*.json"):
        celle.update(json.loads(p.read_text())["corpi"])
    assert set(celle) == {f"C{i}" for i in range(1, 11)}
    c4 = celle["C4"]                                   # a cavallo di due tessere (una solo LAS): copertura piena
    assert c4["copertura"] > 0.95 and c4["tetto"] == "monofalda"
    lon, lat = c4["falde"][0]["geometria"]["coordinates"][0][0]
    assert 12 < lon < 13.5 and 43.5 < lat < 44.5        # WGS84
    assert celle["C10"]["stato"] == "non presente nel rilievo"
    ind = json.loads((prod / "indice.json").read_text())
    assert ind["sintetico"] and ind["attribuzioni"]["campione_dsm"]["tessere"] >= 6
    # di nuovo: niente da rifare
    e2 = _pipeline(radice, tmp_path).esegui(subito=True)
    assert e2["tessere_fatte"] == 0 and e2["esito"] == "completata"
    s2 = json.loads((tmp_path / "stato" / "campione.json").read_text())
    assert len(s2["esecuzioni"]) == 2


def test_ripresa_dopo_interruzione(radice, tmp_path):
    _pipeline(radice, tmp_path).esegui(subito=True, solo=["C_787950_4884050"])
    s = json.loads((tmp_path / "stato" / "campione.json").read_text())
    assert s["tessere"]["C_787950_4884050"]["stato"] == "fatta"
    nome = "C_788000_4884000"
    s["tessere"][nome]["stato"] = "in corso"           # esecuzione interrotta a metà tessera
    (tmp_path / "stato" / "campione.json").write_text(json.dumps(s))
    e = _pipeline(radice, tmp_path).esegui(subito=True)
    s = json.loads((tmp_path / "stato" / "campione.json").read_text())
    assert e["esito"] == "completata" and s["tessere"][nome]["stato"] == "fatta" and s["tessere"][nome]["tentativi"] == 1


def test_limiti_della_notte(radice, tmp_path):
    e = _pipeline(radice, tmp_path / "a", limiti={"max_minuti": 0}).esegui(subito=True)
    assert e["esito"] == "fermata" and "tempo" in e["motivo"]
    e = _pipeline(radice, tmp_path / "b", limiti={"min_gb_liberi": 10 ** 9}).esegui(subito=True)
    assert e["esito"] == "fermata" and "spazio" in e["motivo"]
    e = _pipeline(radice, tmp_path / "c", limiti={"max_gb_notte": 1e-9}).esegui(subito=True)
    assert e["esito"] == "fermata" and "quota" in e["motivo"]
    ore = lambda h, m: (lambda: dt.datetime(2026, 11, 4, h, m, tzinfo=dt.timezone.utc))
    e = _pipeline(radice, tmp_path / "d", limiti={"finestra": ["03:30", "07:00"]}, adesso=ore(12, 0)).esegui()
    assert e["esito"] == "non avviata" and "finestra" in e["motivo"]
    e = _pipeline(radice, tmp_path / "e", limiti={"finestra": ["03:30", "07:00"]}, adesso=ore(4, 0)).esegui()
    assert e["esito"] == "completata"


def test_pausa_se_previsione_in_corso(radice, tmp_path, monkeypatch):
    risposte = iter([1, 1, 0] + [0] * 100)
    chiamate = []

    class R:
        def __init__(self, n): self.n = n
        def json(self): return {"previsioni_in_corso": self.n}
    monkeypatch.setattr(PL.httpx, "get", lambda u, timeout=3: chiamate.append(u) or R(next(risposte)))
    dormite = []
    pl = _pipeline(radice, tmp_path, limiti={"pausa_url": "http://api:8000/api/salute"}, dorme=dormite.append)
    assert pl.esegui(subito=True)["esito"] == "completata"
    assert dormite == [20, 20] and chiamate[0].endswith("/api/salute")


def test_tessera_rotta_saltata_dopo_i_tentativi(radice, tmp_path):
    import shutil
    rotta = tmp_path / "rotta"
    shutil.copytree(radice, rotta)
    (rotta / "dsm" / "C_788000_4884000.tif").write_bytes(b"non sono un tiff")
    for _ in range(2):
        _pipeline(rotta, tmp_path).esegui(subito=True)
    s = json.loads((tmp_path / "stato" / "campione.json").read_text())
    v = s["tessere"]["C_788000_4884000"]
    assert v["stato"] == "saltata" and v["tentativi"] == 2 and s["errori"]
    assert s["esecuzioni"][-1]["esito"] == "completata"            # le altre tessere sono andate avanti


def test_una_esecuzione_alla_volta(radice, tmp_path):
    pl = _pipeline(radice, tmp_path)
    with PL.blocco(tmp_path / "stato" / "campione.lock"):
        with pytest.raises(RuntimeError, match="già in corso"):
            pl.esegui(subito=True)


def test_rimini_fonti_in_attesa(tmp_path):
    z = PL.carica_zona("rimini")
    fonti = {f["id"]: f for f in PL.elenco_fonti(z)}
    for k in ("pnrr_dsm", "rer_las", "rer_dsm"):
        assert fonti[k]["stato"] == "in attesa", k
        assert not PL.usabile(z["fonti"][k])[0]
    # 05/11/2026: il DSM della costa 2019 è acceso, ma solo dentro la sua maschera di copertura
    assert fonti["rer_dsm_costa_2019"]["stato"] == "attiva" and z["fonti"]["rer_dsm_costa_2019"]["copertura"]["maschera"]
    assert fonti["rer_dtm05"]["stato"] == "attiva"
    g, lato = PL.griglia_tessere(z)
    assert g[(785, 4884)].nome == "32_78504884" and lato == 1000      # nome delle tavole RER
    e = PL.Pipeline(z, tmp_path / "a", tmp_path / "s").esegui(subito=True)
    assert e["esito"] == "in attesa" and "nessun corpo" in e["motivo"]  # senza i corpi della Fase A nessuna tessera
    # nessuna zona vera ha i corpi della Fase A nell'archivio vuoto; il campione non conta
    assert PL.scegli_zona(tmp_path / "s", archivio=tmp_path / "a") == (None, False)


def test_versione_dal_quadro_di_unione():
    z = PL.carica_zona("rimini")
    def risposta(req):
        assert "QU_LiDAR_RER2023_2024" in str(req.url) and "GetFeatureInfo" in str(req.url)
        return httpx.Response(200, json={"features": [{"properties": {"TAVOLA": "32_78504884", "DATA_1": "2023-03-25",
                                                                      "DATA_2": "2023-03-27", "DATA_3": " "}}]})
    pl = PL.Pipeline(z, Path("/tmp"), Path("/tmp"), client=httpx.Client(transport=httpx.MockTransport(risposta)))
    t = pl.griglia[(785, 4884)]
    assert pl.versione("rer_dsm", z["fonti"]["rer_dsm"], t) == "rer_dsm:32_78504884|2023-03-25|2023-03-27|||"
    vuota = PL.Pipeline(z, Path("/tmp"), Path("/tmp"),
                        client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"features": []}))))
    assert vuota.versione("rer_dsm", z["fonti"]["rer_dsm"], t) is None
    u = pl.url(z["fonti"]["rer_dtm05"], t)
    assert "bbox=785000.0,4884000.0,786000.0,4885000.0" in u and u.startswith("https://servizigis.regione.emilia-romagna.it/wcs/")


def test_errori_ripuliti():
    e = RuntimeError("https://esempio.it/x?token=SEGRETO&a=1 non risponde")
    assert "SEGRETO" not in PL.pulisci_errore(e) and "esempio.it/x?…" in PL.pulisci_errore(e)


def test_demo_del_sito_con_falde(tmp_path):
    e = demo(tmp_path / "sito")
    assert e["lidar"]["esito"] == "completata"
    celle = list((tmp_path / "sito" / "lidar" / "falde").glob("*.json"))
    assert celle and json.loads((tmp_path / "sito" / "lidar" / "indice.json").read_text())["sintetico"] is True
    assert (tmp_path / "sito" / "indice.json").exists()


def test_cli_lidar(radice, tmp_path, capsys):
    assert main(["lidar", "--zona", "campione", "--archivio", str(tmp_path / "a"), "--stato", str(tmp_path / "s"),
                 "--radice", str(radice), "--subito"]) == 0
    assert '"completata"' in capsys.readouterr().out
    assert main(["lidar-stato", "--stato", str(tmp_path / "s")]) == 0
    assert main(["lidar-fonti", "--zona", "rimini"]) == 0
    out = capsys.readouterr().out
    assert "in attesa" in out and "rer_dtm05" in out


# ---------------------------------------------------------------------------------------------- import DXF e IFC
def _casa(x0, y0, L_, W, g, c):
    A, B, C, D = (x0, y0, 0), (x0 + L_, y0, 0), (x0 + L_, y0 + W, 0), (x0, y0 + W, 0)
    a, b, cc, d = (x0, y0, g), (x0 + L_, y0, g), (x0 + L_, y0 + W, g), (x0, y0 + W, g)
    r1, r2 = (x0, y0 + W / 2, c), (x0 + L_, y0 + W / 2, c)
    return [[A, B, b, a], [B, C, cc, b], [C, D, d, cc], [D, A, a, d], [a, b, r2, r1], [d, cc, r2, r1],
            [a, r1, d, d], [b, r2, cc, cc], [A, B, C, D]]


@pytest.fixture
def dxf(tmp_path):
    ezdxf = pytest.importorskip("ezdxf")
    doc = ezdxf.new(); doc.header["$INSUNITS"] = 6
    m = doc.modelspace()
    for f in _casa(0, 0, 10, 8, 6, 9):
        m.add_3dface(f)
    m.add_lwpolyline([(20, 0), (32, 0), (32, 12), (20, 12)], close=True, dxfattribs={"thickness": 12.0, "layer": "TORRE"})
    m.add_lwpolyline([(40, 0), (46, 0), (46, 6), (40, 6)], close=True, dxfattribs={"layer": "BOX_H_4.5"})
    p = tmp_path / "casa.dxf"
    doc.saveas(p)
    return p


def test_importa_dxf(dxf):
    from edifici3d import importa as I
    r = I.importa_sicuro(dxf, posa=I.posa_da_argomenti(["0,0=12.5665,44.06"]))
    assert r["formato"] == "eugenio-modello-1" and r["licenza"] == "dati dell'utente"
    p = [f["properties"] for f in r["features"]]
    casa = next(x for x in p if x["tetto"] == "capanna")
    assert casa["gronda"] == pytest.approx(6) and casa["colmo"] == pytest.approx(9)
    assert sorted(round(f["orientamento"]) for f in casa["falde"]) == [0, 180]
    assert all(f["pendenza"] == pytest.approx(math.degrees(math.atan(3 / 4)), abs=0.2) for f in casa["falde"])
    assert sorted(x["gronda"] for x in p if x["tetto"] == "piano") == [4.5, 12.0]      # spessore e nome del layer
    from pyproj import Geod
    c = r["features"][0]["geometry"]["coordinates"][0]
    az = [round(Geod(ellps="WGS84").inv(*c[i], *c[i + 1])[0]) % 180 for i in range(len(c) - 1)]
    assert set(az) <= {0, 90}                                          # lati allineati al nord vero


def test_importa_ifc(tmp_path):
    ifcopenshell = pytest.importorskip("ifcopenshell")
    import ifcopenshell.api as api
    f = ifcopenshell.file(schema="IFC4")
    pr = api.run("root.create_entity", f, ifc_class="IfcProject", name="Prova")
    api.run("unit.assign_unit", f)
    ctx = api.run("context.add_context", f, context_type="Model")
    body = api.run("context.add_context", f, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=ctx)
    site = api.run("root.create_entity", f, ifc_class="IfcSite", name="Sito <script>")
    bld = api.run("root.create_entity", f, ifc_class="IfcBuilding", name="Edificio")
    api.run("aggregate.assign_object", f, relating_object=pr, products=[site])
    api.run("aggregate.assign_object", f, relating_object=site, products=[bld])
    site.RefLatitude = [44, 3, 36, 0]; site.RefLongitude = [12, 33, 59, 0]

    def mesh(cls, facce):
        el = api.run("root.create_entity", f, ifc_class=cls)
        vs, fs = [], []
        for fc in facce:
            idx = []
            for v in fc:
                if v not in vs:
                    vs.append(v)
                idx.append(vs.index(v))
            fs.append(idx)
        rep = api.run("geometry.add_mesh_representation", f, context=body, vertices=[vs], faces=[fs])
        api.run("geometry.assign_representation", f, product=el, representation=rep)
        api.run("spatial.assign_container", f, relating_structure=bld, products=[el])
    fc = _casa(0, 0, 12, 10, 7, 10)
    mesh("IfcWall", fc[:4])
    mesh("IfcRoof", [fc[4], fc[5]])
    mesh("IfcSlab", [fc[8], [(0, 0, 3), (12, 0, 3), (12, 10, 3), (0, 10, 3)]])    # solaio intermedio: non è un tetto
    p = tmp_path / "casa.ifc"
    f.write(str(p))
    from edifici3d import importa as I
    r = I.importa_sicuro(p)
    assert r["posa"]["origine"] == "IfcSite"
    (c,) = [x["properties"] for x in r["features"]]
    assert c["tetto"] == "capanna" and c["gronda"] == pytest.approx(7) and c["colmo"] == pytest.approx(10)
    assert c["area"] == pytest.approx(120, rel=0.01)
    lon, lat = r["features"][0]["geometry"]["coordinates"][0][0]
    assert abs(lon - (12 + 33 / 60 + 59 / 3600)) < 0.0005 and abs(lat - (44 + 3 / 60 + 36 / 3600)) < 0.0005


def test_import_file_non_fidati(tmp_path, monkeypatch):
    from edifici3d import importa as I
    falso = tmp_path / "x.ifc"; falso.write_text("<?xml version='1.0'?><ifcXML/>")
    with pytest.raises(I.ModelloNonValido, match="STEP"):
        I.importa_sicuro(falso)
    z = tmp_path / "x.ifczip"; z.write_bytes(b"PK\x03\x04")
    with pytest.raises(I.ModelloNonValido, match="formato"):
        I.importa_sicuro(z)
    d = tmp_path / "x.dxf"; d.write_text("ciao")
    with pytest.raises(I.ModelloNonValido, match="DXF"):
        I.importa_sicuro(d)
    grande = tmp_path / "g.dxf"; grande.write_text("0\nSECTION\n" + " " * 2048)
    monkeypatch.setattr(I, "MAX_MB", 0.001)
    with pytest.raises(I.ModelloNonValido, match="massimo"):
        I.importa_sicuro(grande)
    monkeypatch.setattr(I, "MAX_MB", 50)
    link = tmp_path / "l.dxf"; link.symlink_to(grande)
    with pytest.raises(I.ModelloNonValido, match="file normale"):
        I.importa_sicuro(link)
    rotto = tmp_path / "r.ifc"; rotto.write_text("ISO-10303-21;\nHEADER;\nnon è un IFC\n")
    with pytest.raises(I.ModelloNonValido):
        I.importa_sicuro(rotto)
    assert I.pulisci("Sito <script>\x00alert(1)") == "Sito script alert(1)"


def test_import_senza_posa(dxf):
    from edifici3d import importa as I
    with pytest.raises(I.ModelloNonValido, match="posa"):
        I.importa_sicuro(dxf)
    r = I.importa_sicuro(dxf, posa=I.posa_da_argomenti(["0,0=12.5665,44.06", "10,0=12.5668,44.06"]))
    assert any("scala" in a for a in r["avvisi"])          # 10 m nel disegno, ~24 m tra i due punti
