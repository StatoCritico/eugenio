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


# ---------------------------------------------------------------- (24/11/2026) file «UtilizziGrafici» con le chiavi catastali
from cer_fv import agrea as A  # noqa: E402

CAMPI_UTI = ["ANNO_CAMP", "COD_AZI", "ISTAT_PROV", "ISTAT_COMU", "SEZIONE", "FOGLIO", "PARTICELLA", "DESC_USO", "DESC_COLT",
             "DESC_BIO", "DESC_MENZ", "DESC_CE_OL", "SUP_UTI"]


def _uti(d: Path, anno: int, righe: list[dict], provincia: str = "MO"):
    """Zip «Uti_Part_PCG_<anno>_<PR>.zip» con il tracciato vero (solo i campi usati), geometrie fittizie."""
    cart = d / str(anno)
    cart.mkdir(parents=True, exist_ok=True)
    base = cart / f"_Uti_{anno}"
    w = shapefile.Writer(str(base), shapeType=shapefile.POINT, encoding="latin-1")
    for c in CAMPI_UTI:
        w.field(c, "N" if c == "SUP_UTI" else "C", size=12 if c == "SUP_UTI" else 80, decimal=4 if c == "SUP_UTI" else 0)
    for r in righe:
        w.point(1_650_000, 4_940_000)
        w.record(*[r.get(c, "") if c != "SUP_UTI" else r.get(c, 0) for c in CAMPI_UTI])
    w.close()
    with zipfile.ZipFile(cart / f"Uti_Part_PCG_{anno}_{provincia}.zip", "w") as z:
        for e in (".shp", ".shx", ".dbf"):
            z.write(base.with_suffix(e), f"Uti_Part_PCG_{anno}_{provincia}{e}")
    for e in (".shp", ".shx", ".dbf"):
        base.with_suffix(e).unlink()


def _riga(foglio, part, colt, ha, bio="Convenzionale", menz="", ce="", sez="", comu="225"):
    return {"ANNO_CAMP": "2025", "COD_AZI": "6DC871BF", "ISTAT_PROV": "036", "ISTAT_COMU": comu, "SEZIONE": sez,
            "FOGLIO": foglio, "PARTICELLA": part, "DESC_USO": "", "DESC_COLT": colt, "DESC_BIO": bio, "DESC_MENZ": menz,
            "DESC_CE_OL": ce, "SUP_UTI": ha}


def test_campi_veri_bio_e_menzioni():
    R = K.regole()
    assert K.peso_appezzamento({"desc_colt": "MAIS", "desc_bio": "Biologico"}, "036", R) == 1
    assert K.peso_appezzamento({"desc_colt": "MAIS", "desc_bio": "In Conversione"}, "036", R) == 1
    assert K.peso_appezzamento({"desc_colt": "MAIS", "desc_bio": "Convenzionale"}, "036", R) == pytest.approx(0.05)
    assert K.peso_appezzamento({"desc_colt": "OLIVO DA OLIO", "desc_menz": "COLLINE DI ROMAGNA - DOP"}, "033", R) == 1
    assert K.peso_appezzamento({"desc_colt": "OLIVO DA OLIO", "desc_ce_ol": "DOP"}, "033", R) == 1
    assert K.chiave_da_ref("F257_000012.34", "12", "34") == ("F257", "", "12", "34")
    assert K.chiave_da_ref("A944A_000003.7", "0003", "007") == ("A944", "A", "3", "7")
    assert K.chiave("F257", "", "013", "01133") == ("F257", "", "13", "1133")


def test_lettura_dbf_a_pezzi(tmp_path):
    _uti(tmp_path, 2025, [_riga("12", "00034", "ERBA MEDICA", 1.5), _riga("13", "1", "VITE", 0.25, sez="B")])
    for nome, z, n in A.dbf_negli_zip(tmp_path / "2025"):        # lo zip resta aperto dentro il giro
        with z.open(n) as f:
            assert A.campi_dbf(f)[:3] == ["ANNO_CAMP", "COD_AZI", "ISTAT_PROV"]
        with z.open(n) as f:
            rr = list(A.righe_dbf(f, ["FOGLIO", "PARTICELLA", "SUP_UTI", "SEZIONE"]))
    assert rr == [{"SEZIONE": "", "FOGLIO": "12", "PARTICELLA": "00034", "SUP_UTI": "1.5000"},
                  {"SEZIONE": "B", "FOGLIO": "13", "PARTICELLA": "1", "SUP_UTI": "0.2500"}]


def test_costruisci_con_chiavi_catastali(tmp_path):
    _immobili(tmp_path)
    ag = tmp_path / "agrea"
    # particelle di 40.000 m² (area_m2 dell'indice): 12/34 biologica per 4 ha; 12/35 medica per 2 ha (metà) nel 2024 e
    # 4 ha nel 2025; 13/1 mais; una particella privata (99/9) che non deve restare in memoria; un comune non in tabella
    _uti(ag, 2024, [_riga("12", "00034", "FRUMENTO TENERO", 4, bio="Biologico"), _riga("12", "35", "ERBA MEDICA", 2),
                    _riga("13", "1", "MAIS DA GRANELLA", 4), _riga("99", "9", "VITE", 1), _riga("12", "34", "VITE", 1, comu="999")])
    _uti(ag, 2025, [_riga("012", "035", "ERBA MEDICA", 4)])
    comuni = tmp_path / "comuni.csv"
    intestazione = ";".join(f"c{i}" for i in range(20))
    comuni.write_text(intestazione + "\n" + ";".join(["08", "", "", "", "036023"] + [""] * 14 + ["F257"]) + "\n", encoding="latin-1")
    # il codice ISTAT di Modena è 036023: le righe dei test hanno 036225, quindi prima nessun abbinamento…
    info = T.costruisci(tmp_path, tmp_path / "cer_fv", ag, comuni=comuni)
    db = sqlite3.connect(info["file"])
    assert db.execute("SELECT COUNT(prob_coltura) FROM terreni").fetchone()[0] == 0
    # …poi con il codice giusto
    comuni.write_text(intestazione + "\n" + ";".join(["08", "", "", "", "036225"] + [""] * 14 + ["F257"]) + "\n", encoding="latin-1")
    info = T.costruisci(tmp_path, tmp_path / "cer_fv", ag, comuni=comuni)
    assert info["campagne_agrea"] == [2024, 2025]
    db = sqlite3.connect(info["file"]); db.row_factory = sqlite3.Row
    r = {x["ref"]: dict(x) for x in db.execute("SELECT * FROM terreni")}
    assert r["F257_000012.34"]["prob_coltura"] == 100 and r["F257_000012.34"]["quota_dichiarata"] == 1
    assert r["F257_000012.35"]["prob_coltura"] == 60          # 2025: tutta medica × 0,6 × Modena 1,0 (2024: metà)
    assert r["F257_000013.1"]["prob_coltura"] == 5
    assert not (ag / "comuni_istat.csv").exists()               # nessuno scaricamento: la tabella è quella data


def test_elenco_e_campagne_chiuse():
    import datetime as dt
    assert A.campagne_chiuse([2021, 2022, 2023, 2024, 2025, 2026], oggi=dt.date(2026, 11, 24)) == [2023, 2024, 2025]
    assert A.campagne_chiuse([2021, 2022], oggi=dt.date(2026, 11, 24)) == [2021, 2022]


def test_scarica_senza_rete(tmp_path, monkeypatch):
    import datetime as dt
    import io
    zip_finto = io.BytesIO()
    with zipfile.ZipFile(zip_finto, "w") as z:
        z.writestr("x.dbf", b"x")
    dati = zip_finto.getvalue()
    radice = ('<pre> 8/24/2023  9:11 AM        &lt;dir&gt; <A HREF="/agrea-file/UtilizziGrafici/2024/">2024</A><br>'
              ' 5/28/2026 12:28 AM        &lt;dir&gt; <A HREF="/agrea-file/UtilizziGrafici/2025/">2025</A><br>'
              ' 5/28/2026 12:28 AM        &lt;dir&gt; <A HREF="/agrea-file/UtilizziGrafici/2026/">2026</A><br></pre>')

    def anno(a):
        return "".join(f' 5/23/2025 11:00 PM {len(dati):>12} <A HREF="/agrea-file/UtilizziGrafici/{a}/Uti_Part_PCG_{a}_{p}.zip">x</A><br>'
                       for p in ("BO", "RN", "XX"))
    chiamate = []

    class Risposta(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def finto(url, timeout=0):
        chiamate.append(url)
        if url == A.BASE:
            return Risposta(radice.encode())
        if url.endswith("/"):
            return Risposta(anno(url.rstrip("/").rsplit("/", 1)[-1]).encode())
        return Risposta(dati)
    monkeypatch.setattr(A, "_get", finto)
    (tmp_path / "2019").mkdir()
    e = A.scarica(tmp_path, quante=2, oggi=dt.date(2026, 11, 24), togli_vecchie=True)
    assert e["campagne"] == [2024, 2025] and len(e["scaricati"]) == 4 and e["tolte"] == ["2019"]
    assert sorted(p.name for p in (tmp_path / "2025").iterdir()) == ["Uti_Part_PCG_2025_BO.zip", "Uti_Part_PCG_2025_RN.zip"]
    assert not any("_XX" in c for c in chiamate)
    e = A.scarica(tmp_path, quante=2, oggi=dt.date(2026, 11, 24))
    assert e["scaricati"] == [] and len(e["gia_presenti"]) == 4


def test_comuni_parquet_senza_belfiore_usa_elenco_istat(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    pq.write_table(pa.table({"istat": ["099014"], "nome": ["Rimini"]}), tmp_path / "comuni.parquet")
    intestazione = ";".join(f"c{i}" for i in range(20))
    (tmp_path / "comuni_istat.csv").write_text(intestazione + "\n" + ";".join(["08", "", "", "", "099014"] + [""] * 14 + ["H294"]) + "\n", encoding="latin-1")
    assert A.istat_belfiore(tmp_path / "comuni.parquet", tmp_path) == {"099014": "H294"}


# ---------------------------------------------------------------- (24/11/2026 sera) vincoli paesaggistici
from cer_fv import vincoli as V  # noqa: E402


def _zip_shp(f: Path, nome: str, poligoni: list, campi: dict):
    """Shapefile poligonale in UTM 32N (anelli orari) dentro uno zip, come quelli della Regione."""
    base = f.parent / f"_{nome}"
    w = shapefile.Writer(str(base), shapeType=shapefile.POLYGON, encoding="utf-8")
    for k in campi:
        w.field(k, "C", size=80)
    for anello in poligoni:
        w.poly([anello]); w.record(*campi.values())
    w.close()
    with zipfile.ZipFile(f, "w") as z:
        for e in ("shp", "shx", "dbf"):
            z.write(f"{base}.{e}", f"CARTELLA/{nome}.{e}")
    for e in ("shp", "shx", "dbf"):
        Path(f"{base}.{e}").unlink()


def _quadrato(x, y, d):   # orario
    return [[x - d, y - d], [x - d, y + d], [x + d, y + d], [x + d, y - d], [x - d, y - d]]


def _cartella_vincoli(d: Path, x, y):
    d.mkdir(parents=True, exist_ok=True)
    _zip_shp(d / "boschi.zip", "AS_FBO_PL", [_quadrato(x - 50, y, 50)], {"TIPO": "bosc"})            # metà sinistra
    _zip_shp(d / "fiumi.zip", "AS_P_FRF_pl", [_quadrato(x - 50, y, 50)], {"note": ""})               # sovrapposto
    _zip_shp(d / "usi_civici.zip", "AS_P_USC_PL", [_quadrato(x + 50, y, 50)], {"NOME_USU": "Demanio di prova"})
    from pyproj import Transformer
    lon, lat = Transformer.from_crs(V.EPSG_RER, 4326, always_xy=True).transform(x + 60, y + 60)
    q = " ".join(f"{lon + a},{lat + b}" for a, b in [(0, 0), (0.0002, 0), (0.0002, 0.0002), (0, 0.0002), (0, 0)])
    (d / "beni_archeologici.gml").write_text(f"""<?xml version='1.0' encoding="UTF-8" ?>
<wfs:FeatureCollection xmlns:ms="http://mapserver.gis.umn.edu/mapserver" xmlns:wfs="http://www.opengis.net/wfs" xmlns:gml="http://www.opengis.net/gml">
 <gml:featureMember><ms:ba_v_vincoli_pl fid="1"><ms:geom><gml:MultiPolygon srsName="EPSG:4326"><gml:polygonMember><gml:Polygon>
  <gml:outerBoundaryIs><gml:LinearRing><gml:coordinates>{q}</gml:coordinates></gml:LinearRing></gml:outerBoundaryIs>
 </gml:Polygon></gml:polygonMember></gml:MultiPolygon></ms:geom><ms:nome>Villa romana di prova</ms:nome></ms:ba_v_vincoli_pl></gml:featureMember>
</wfs:FeatureCollection>""", encoding="utf-8")


def test_vincoli_misura_e_mappa(tmp_path):
    import shapely
    x, y = 700_000, 4_900_000
    _cartella_vincoli(tmp_path, x, y)
    vv = V.Vincoli(tmp_path)
    m = vv.misura(shapely.box(x - 100, y - 100, x + 100, y + 100))        # particella di 200 × 200 m
    assert m["quota_vincolata"] == pytest.approx(0.25, abs=0.01)           # boschi e fiumi sullo stesso quarto: contati una volta
    assert "foreste e boschi" in m["vincoli"] and "corsi d'acqua" in m["vincoli"]
    assert "usi civici" in m["vincoli_segnalati"] and "Demanio di prova" in m["vincoli_segnalati"]
    assert vv.misura(shapely.box(x + 5000, y, x + 5100, y + 100)) == {"quota_vincolata": 0.0, "vincoli": None, "vincoli_segnalati": None}
    info = V.costruisci(tmp_path)
    assert info["per_fonte"] == {"boschi": 1, "fiumi": 1, "beni_archeologici": 1, "usi_civici": 1}
    db = sqlite3.connect(info["file"])
    assert db.execute("SELECT COUNT(*) FROM v_rt").fetchone()[0] == 4
    assert {r[0] for r in db.execute("SELECT classe FROM v")} == {"escluso", "segnalato"}


def test_costruisci_con_vincoli(tmp_path):
    from pyproj import Transformer
    _immobili(tmp_path)
    # vincoli centrati sulla particella 12/34 (centro del suo poligono, in UTM 32N): metà vincolata
    lon, lat = PART["F257_000012.34"]
    x, y = Transformer.from_crs(4326, V.EPSG_RER, always_xy=True).transform(lon + D / 2, lat + D / 2)
    _cartella_vincoli(tmp_path / "vincoli", x, y)
    info = T.costruisci(tmp_path, tmp_path / "cer_fv", vincoli=tmp_path / "vincoli")
    assert info["con_vincoli"] == 3
    db = sqlite3.connect(info["file"]); db.row_factory = sqlite3.Row
    r = {x["ref"]: dict(x) for x in db.execute("SELECT * FROM terreni")}
    assert 0 < r["F257_000012.34"]["quota_vincolata"] < 1 and "boschi" in r["F257_000012.34"]["vincoli"]
    assert "usi civici" in (r["F257_000012.34"]["vincoli_segnalati"] or "")
    # senza la cartella dei vincoli le colonne restano vuote
    info = T.costruisci(tmp_path, tmp_path / "cer_fv2", vincoli=tmp_path / "non_c_e")
    assert info["con_vincoli"] is None
