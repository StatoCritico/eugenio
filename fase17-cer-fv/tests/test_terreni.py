"""Prove della fase 17 (24/11/2026): terreni pubblici e probabilità di coltura DOP o certificata, su dati sintetici.

Indice degli immobili con la struttura della fase 7 (enti, ente_particelle, comuni), parquet delle particelle con i
poligoni, piani colturali AGREA finti in Gauss-Boaga (EPSG:3003) scritti con pyshp in uno zip, senza .prj. Nessuna rete.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import zipfile
from pathlib import Path

import pytest

shapely = pytest.importorskip("shapely")
pyproj = pytest.importorskip("pyproj")
shapefile = pytest.importorskip("shapefile")
pa = pytest.importorskip("pyarrow")
import pyarrow.parquet as pq  # noqa: E402
from shapely.geometry import box  # noqa: E402
import shapely.ops  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cer_fv import colture as K, terreni as T  # noqa: E402

TR = pyproj.Transformer.from_crs(4326, 3003, always_xy=True)
# tre particelle a Modena (lon, lat del vertice SO), circa 200 × 200 m
PART = {"F257_000012.34": (10.90, 44.60), "F257_000012.35": (10.91, 44.60), "F257_000013.1": (10.92, 44.60)}
D = 0.0025


def _poligono(lon, lat):
    return box(lon, lat, lon + D, lat + D * 0.8)


def _immobili(d: Path):
    db = sqlite3.connect(d / "immobili_pa_2023.sqlite")
    db.execute("CREATE TABLE enti (id, chiave, nome, tipologia_amm, gruppo, settore, sede_comune, sede_provincia)")
    db.executemany("INSERT INTO enti VALUES (?,?,?,?,?,?,?,?)", [
        (1, "k1", "COMUNE DI MODENA", "Comuni", "C", "Amministrazioni locali", "MODENA", "MO"),
        (2, "k2", "UNIVERSITA' DI MODENA", "Università", "U", "Istruzione", "MODENA", "MO")])
    db.execute("CREATE TABLE ente_particelle (ente, ref, ruolo, natura, lon, lat, n_beni, sup_mq, cubatura_mc, area_m2,"
               " comune_cod, indirizzo, tipologie, epoca, utilizzo, titolo)")
    righe = []
    for ref, (lon, lat) in PART.items():
        righe.append((1, ref, "P", "T", lon + D / 2, lat + D / 2, 1, 40000, 0, 40000, "F257", "", "Terreno agricolo", None, "Uso agricolo", "Proprietà"))
    righe.append((2, "F257_000013.1", "P", "T", 10.92 + D / 2, 44.6 + D / 2, 1, 10000, 0, 40000, "F257", "", "Terreno", None, "", "Proprietà"))
    righe.append((1, "F257_000099.1", "P", "E", 10.95, 44.6, 1, 500, 0, 600, "F257", "", "Scuola", None, "", "Proprietà"))   # fabbricato
    righe.append((1, "F257_000098.1", "U", "T", 10.96, 44.6, 1, 500, 0, 600, "F257", "", "Terreno", None, "", "Locazione"))  # solo in uso
    righe.append((1, "b123", "P", "T", 10.97, 44.6, 1, 500, 0, 0, "F257", "", "Terreno", None, "", "Proprietà"))           # senza particella
    db.executemany(f"INSERT INTO ente_particelle VALUES ({','.join('?' * 16)})", righe)
    db.execute("CREATE TABLE comuni (comune_cod, comune, provincia, regione)")
    db.execute("INSERT INTO comuni VALUES ('F257', 'MODENA', 'MODENA', 'EMILIA-ROMAGNA')")
    db.commit(); db.close()
    t = pa.table({"ref_ade": list(PART), "foglio": ["12", "12", "13"], "particella": ["34", "35", "1"],
                  "geometry": [shapely.to_wkb(_poligono(*v)) for v in PART.values()]})
    pq.write_table(t, d / "immobili_pa_2023_particelle.parquet")


def _agrea(d: Path, anno: int, appezzamenti: list[tuple]):
    """appezzamenti: (lon, lat, larghezza in gradi, DESC_COLT, FLAG_BIO, FLAG_INTE) → zip con uno shapefile in 3003."""
    lavoro = d / f"_shp{anno}"; lavoro.mkdir(parents=True, exist_ok=True)
    w = shapefile.Writer(str(lavoro / "PC_MO"), shapeType=shapefile.POLYGON)
    for nome in ("ID_APPEZ", "DESC_COLT", "DESC_USO", "DESC_QUAL", "FLAG_BIO", "FLAG_INTE"):
        w.field(nome, "C", 60)
    for i, (lon, lat, larg, colt, bio, inte) in enumerate(appezzamenti):
        g = shapely.ops.transform(TR.transform, box(lon, lat, lon + larg, lat + D * 0.8))
        w.poly([list(g.exterior.coords)])
        w.record(str(i), colt, "SEMINATIVO", "", bio, inte)
    w.close()
    c = d / str(anno); c.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(c / "PC_MO.zip", "w") as z:
        for e in (".shp", ".shx", ".dbf"):
            z.write(lavoro / f"PC_MO{e}", f"PC_MO{e}")


def test_pesi_e_classi():
    R = K.regole()
    assert K.peso_appezzamento({"desc_colt": "FRUMENTO", "flag_bio": "S"}, "036", R) == 1
    assert K.peso_appezzamento({"desc_colt": "MAIS", "desc_qual": "Qualità DOP"}, "033", R) == 1
    assert K.peso_appezzamento({"desc_colt": "ERBA MEDICA"}, "036", R) == pytest.approx(0.6)
    assert K.peso_appezzamento({"desc_colt": "ERBA MEDICA"}, "039", R) == pytest.approx(0.06)
    assert K.peso_appezzamento({"desc_colt": "VITE PER UVA DA VINO"}, "099", R) == pytest.approx(0.7)
    assert K.peso_appezzamento({"desc_colt": "MAIS DA GRANELLA"}, "036", R) == pytest.approx(0.05)
    assert (R.classe(None), R.classe(10), R.classe(30), R.classe(60)) == ("non dichiarata", "bassa", "media", "alta")
    assert K.codice_provincia("Forlì-Cesena") == "040" and K.codice_provincia("ROMA") == ""


def test_costruisci_con_agrea(tmp_path):
    _immobili(tmp_path)
    ag = tmp_path / "agrea"
    # 2023: prima particella biologica; seconda metà medica; terza mais. 2024: seconda tutta medica. 2020 troppo vecchia.
    _agrea(ag, 2020, [(10.90, 44.60, D, "VITE", "S", "N")])
    _agrea(ag, 2022, [(10.92, 44.60, D, "MAIS DA GRANELLA", "N", "N")])
    _agrea(ag, 2023, [(10.90, 44.60, D, "FRUMENTO TENERO", "S", "N"), (10.91, 44.60, D / 2, "ERBA MEDICA", "N", "N"),
                      (10.92, 44.60, D, "MAIS DA GRANELLA", "N", "N")])
    _agrea(ag, 2024, [(10.91, 44.60, D, "ERBA MEDICA", "N", "N")])
    info = T.costruisci(tmp_path, tmp_path / "cer_fv", ag)
    assert info["particelle"] == 3 and info["con_indicatore"] == 3 and info["campagne_agrea"] == [2022, 2023, 2024]
    db = sqlite3.connect(info["file"]); db.row_factory = sqlite3.Row
    r = {x["ref"]: dict(x) for x in db.execute("SELECT * FROM terreni")}
    assert r["F257_000012.34"]["prob_coltura"] == 100 and r["F257_000012.34"]["classe_coltura"] == "alta"
    assert r["F257_000012.35"]["prob_coltura"] == 60       # 2024: tutta medica × 0,6 (2023: metà)
    assert r["F257_000013.1"]["prob_coltura"] == 5 and r["F257_000013.1"]["classe_coltura"] == "bassa"
    assert r["F257_000013.1"]["n_enti"] == 2 and r["F257_000013.1"]["ente"] == "COMUNE DI MODENA"
    assert r["F257_000012.34"]["foglio"] == "12" and r["F257_000012.34"]["particella"] == "34"
    assert r["F257_000012.34"]["comune"] == "MODENA" and r["F257_000012.34"]["regione"] == "EMILIA-ROMAGNA"
    # nessun dato AGREA oltre all'indicatore, nessun codice fiscale
    colonne = [c[1] for c in db.execute("PRAGMA table_info(terreni)")]
    assert not any(k in " ".join(colonne).lower() for k in ("desc_colt", "flag", "fiscale", "cedente"))
    assert db.execute("SELECT COUNT(*) FROM terreni_rt WHERE ovest > 10.89 AND est < 10.915").fetchone()[0] == 2
    assert "non ceduti" in json.loads(db.execute("SELECT valore FROM info WHERE chiave = 'fonti'").fetchone()[0])


def test_costruisci_senza_agrea(tmp_path):
    _immobili(tmp_path)
    info = T.costruisci(tmp_path, tmp_path / "cer_fv")
    db = sqlite3.connect(info["file"])
    assert info["con_indicatore"] == 0
    assert db.execute("SELECT COUNT(*), COUNT(prob_coltura) FROM terreni").fetchone() == (3, 0)


def test_particella_non_dichiarata(tmp_path):
    _immobili(tmp_path)
    ag = tmp_path / "agrea"
    # appezzamenti ai due lati: particelle dentro la zona coperta da AGREA ma non dichiarate
    _agrea(ag, 2024, [(10.88, 44.60, D, "VITE", "S", "N"), (10.95, 44.60, D, "VITE", "S", "N")])
    info = T.costruisci(tmp_path, tmp_path / "cer_fv", ag)
    db = sqlite3.connect(info["file"])
    assert db.execute("SELECT DISTINCT classe_coltura FROM terreni").fetchall() == [("non dichiarata",)]
