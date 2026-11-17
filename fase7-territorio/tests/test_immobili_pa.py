"""Test degli immobili delle PA (MEF + particelle AdE). Nessuna chiamata di rete: CSV e GML costruiti qui,
con le stesse particolarità dei file veri (Windows-1252, a capo dentro le virgolette, virgola decimale, unità
graffate, riferimenti AdE con e senza sezione, poligoni con buco, ordine lat lon)."""
import io
import json
import zipfile
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import shapely

from territorio import immobili_pa as ip

INTEST = ('"Natura del bene";"Amministrazione Denominazione";"Tipologia Amministrazione";"ID bene";'
          '"Regione del bene";"Comune del bene";"Codice Comune del bene";"Fonte Georeferenziazione";"Latitudine";"Longitudine";"Identificativo catastale";'
          '"Tipologia Bene Immobile";"Superficie (mq)";"Descrizione Compendio"')
RIGHE = [
    '"FABBRICATO";"COMUNE DI ACQUASPARTA (TR)";"Comuni";1;"UMBRIA";"Acquasparta";"A045";"IDENTIFICATIVI_CATASTALI";42,7334;12,4930;"A045:::1:1::2";'
    '"Edificio scolastico (es.: scuola di ogni ordine e grado, università, scuola di formazione)";1.250;"SCUOLA ""G. VERDI""\r\nPLESSO"',
    '"FABBRICATO";"COMUNE DI ACQUASPARTA (TR)";"Comuni";2;"UMBRIA";"Acquasparta";"A045";"IDENTIFICATIVI_CATASTALI";42,7334;12,4930;"A045:::1:1::3";'
    '"Ufficio strutturato ed assimilabili";300;""',
    '"TERRENO";"REGIONE UMBRIA";"Regioni";3;"UMBRIA";"Acquasparta";"A045";"INDIRIZZO";42,70;12,50;"A045::0021:0064:::";'
    '"Terreno agricolo";10000;""',
    '"FABBRICATO";"COMUNE DI MODENA";"Comuni";4;"EMILIA-ROMAGNA";"Modena";"F363";"INDIRIZZO";44,64;10,92;'
    '"F363:A::13:100::1;F363:A::13:101::";"Caserma";500;""',
    '"FABBRICATO";"COMUNE DI MODENA";"Comuni";5;"EMILIA-ROMAGNA";"Modena";"F363";"";;;"";"Caserma";0;""',
    # codice comune troncato e particella rinumerata: si trova col punto (centroide AdE)
    '"FABBRICATO";"COMUNE DI ACQUASPARTA (TR)";"Comuni";6;"UMBRIA";"Acquasparta";"A045";"IDENTIFICATIVI_CATASTALI";42,7335;12,4926;"045:::1:999::";"Caserma";10;""',
]
CSV = ("\r\n".join([INTEST] + RIGHE) + "\r\n").encode("cp1252")


def _membro(ref, anelli):
    """anelli: [(lat, lon), …] esterno, poi eventuali buchi; coordinate scritte lat lon come nei file AdE."""
    pos = lambda a: " ".join(f"{la} {lo}" for la, lo in a)
    buchi = "".join(f"<gml:interior><gml:LinearRing><gml:posList srsDimension=\"2\">{pos(b)}</gml:posList>"
                    f"</gml:LinearRing></gml:interior>" for b in anelli[1:])
    return (f'<wfs:member><CP:CadastralParcel gml:id="CadastralParcel.IT.AGE.PLA.{ref}"><CP:msGeometry>'
            f'<gml:Polygon gml:id="x.1" srsName="urn:ogc:def:crs:EPSG::6706"><gml:exterior><gml:LinearRing>'
            f'<gml:posList srsDimension="2">{pos(anelli[0])}</gml:posList></gml:LinearRing></gml:exterior>{buchi}'
            f'</gml:Polygon></CP:msGeometry><CP:NATIONALCADASTRALREFERENCE>{ref}</CP:NATIONALCADASTRALREFERENCE>'
            f'</CP:CadastralParcel></wfs:member>')


QUADRO = [(42.7330, 12.4925), (42.7330, 12.4935), (42.7340, 12.4935), (42.7340, 12.4925), (42.7330, 12.4925)]
BUCO = [(42.7334, 12.4929), (42.7334, 12.4931), (42.7336, 12.4931), (42.7336, 12.4929), (42.7334, 12.4929)]


def _gml(*membri):
    return ('<?xml version="1.0"?><wfs:FeatureCollection xmlns:CP="x" xmlns:gml="y" xmlns:wfs="z">'
            + "".join(membri) + "</wfs:FeatureCollection>").encode()


def _zip(contenuto: dict) -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for n, d in contenuto.items():
            z.writestr(n, d)
    return b.getvalue()


def test_chiavi():
    assert ip.chiave_ade("A045_000100.1") == ("A045", "", "0001", "1")
    assert ip.chiave_ade("F363A001300.0100") == ("F363", "A", "0013", "100")
    assert ip.chiavi_mef("A045:::62:308::", "FABBRICATO") == [("A045", "", "0062", "308")]
    assert ip.chiavi_mef("A045::62:307:::", "TERRENO") == [("A045", "", "0062", "307")]
    assert ip.chiavi_mef("A952:::21:3027:0:E:18", "FABBRICATO") == [("A952", "", "0021", "3027")]  # tavolare
    assert len(ip.chiavi_mef("G273:::133:117::1;G273:::133:126::4", "FABBRICATO")) == 2           # graffato
    assert ip.chiavi_mef("", "FABBRICATO") == []
    assert ip.chiavi_mef("205::5:726:::", "TERRENO", "F205") == [("F205", "", "0005", "726")]   # codice troncato
    for strano in ("A045_0001001", "A045_00010.1", "x"):
        try:
            ip.chiave_ade(strano)
            raise AssertionError(strano)
        except ValueError:
            pass


def test_csv_mef():
    df = ip.leggi_csv_mef(CSV)
    assert len(df) == 6 and "natura" in df and "id_catastale" in df
    assert df.loc[0, "compendio"] == 'SCUOLA "G. VERDI" PLESSO'
    assert df.loc[0, "superficie_mq"] == 1250 and abs(df.loc[0, "lat"] - 42.7334) < 1e-9
    assert pd.isna(df.loc[4, "lat"])


def test_link_mef():
    html = ('<a href="/modules/documenti_it/attivo_patrimonio/immobili_2023/opendata_imm/Imm_Universita_2023.zip">u</a>'
            '<a href="/export/sites/sitode/modules/documenti_it/attivo_patrimonio/immobili_2023/Dizionario_Immobili_2023.pdf">d</a>'
            '<a href="/altro.zip">no</a>')
    u = ip.link_mef(html, 2023)
    assert len(u) == 2 and all(x.startswith("https://www.de.mef.gov.it/") for x in u)


def test_leggi_ple_solo_le_richieste():
    dati = _gml(_membro("A045_000100.1", [QUADRO, BUCO]), _membro("A045_000100.2", [QUADRO]),
                _membro("A045X", [QUADRO]))
    tot, trovate, strani = ip.leggi_ple(dati, {("A045", "", "0001", "1")})
    assert tot == 3 and strani == ["A045X"] and len(trovate) == 1
    k, ref, g, agg = trovate[0]
    assert agg == "esatto"
    assert ref == "A045_000100.1" and len(g.interiors) == 1
    assert 12.49 < g.centroid.x < 12.50 and 42.73 < g.centroid.y < 42.74          # lon lat dopo lo scambio


def test_aggancio_senza_sezione():
    # il MEF scrive H501:::488:2 (senza sezione), l'AdE H501D048800.2: si aggancia solo se la sezione è unica
    dati = _gml(_membro("H501D048800.2", [QUADRO]), _membro("H501C011100.5", [QUADRO]),
                _membro("H501D011100.5", [QUADRO]))
    tot, trovate, _ = ip.leggi_ple(dati, {("H501", "", "0488", "2"), ("H501", "", "0111", "5")})
    assert [(t[0], t[1], t[3]) for t in trovate] == [(("H501", "", "0488", "2"), "H501D048800.2", "senza_sezione")]


def test_sezione_dal_punto_e_punto():
    piccolo = [(42.7330, 12.4925), (42.7330, 12.4927), (42.7332, 12.4927), (42.7332, 12.4925), (42.7330, 12.4925)]
    lontano = [(la + 0.01, lo) for la, lo in QUADRO]
    dati = _gml(_membro("H501C011100.5", [lontano]), _membro("H501D011100.5", [piccolo]),
                _membro("H501D099900.7", [piccolo]))
    rich = {("H501", "", "0111", "5"): [(12.4926, 42.7331)],          # il punto sta nella particella della sezione D
            ("H501", "", "0555", "1"): [(12.4926, 42.7331)],          # non esiste: si trova col punto
            ("H501", "", "0666", "2"): []}                            # non esiste e senza punto: resta fuori
    _, trovate, _ = ip.leggi_ple(dati, rich)
    got = {t[0]: (t[1], t[3]) for t in trovate}
    assert got[("H501", "", "0111", "5")] == ("H501D011100.5", "sezione_dal_punto")
    assert got[("H501", "", "0555", "1")][1] == "punto" and ("H501", "", "0666", "2") not in got


def test_regione_e_composizione(tmp_path: Path):
    beni = ip.leggi_csv_mef(CSV)
    rich = ip.richieste_per_comune(beni)
    comune_tr = _zip({"A045_ACQUASPARTA_ple.gml": _gml(_membro("A045_000100.1", [QUADRO, BUCO]),
                                                       _membro("A045_002100.64", [QUADRO])),
                      "A045_ACQUASPARTA_map.gml": b"<x/>"})
    comune_mo = _zip({"F363_MODENA_ple.gml": _gml(_membro("F363A001300.100", [QUADRO]))})
    regione = tmp_path / "PROVA.zip"
    regione.write_bytes(_zip({"TR.zip": _zip({"A045_ACQUASPARTA.zip": comune_tr, "Z999_ALTRO.zip": b"non letto"}),
                              "MO.zip": _zip({"F363_MODENA.zip": comune_mo})}))
    tab, stat = ip.poligoni_regione(regione, rich, tmp_path)
    assert stat["agganciate"] == 4 and stat["comuni"] == 2
    f = tmp_path / "poligoni.parquet"
    pq.write_table(tab, f)

    bf = tmp_path / "mef.parquet"
    beni.to_parquet(bf)
    ris = ip.componi(bf, [f], tmp_path, 2023)
    assert ris == {"beni": 6, "beni_con_identificativo": 5, "beni_con_poligono": 5, "particelle": 3}

    b = pq.read_table(tmp_path / "immobili_pa_2023_beni.parquet")
    meta = json.loads(b.schema.metadata[b"geo"])
    assert meta["primary_column"] == "geometry" and b"EuGEnio" in b.schema.metadata[b"attribuzione"]
    bd = b.to_pandas()
    assert bd.loc[bd.id_bene == "4", "ref_ade"].item() == "F363A001300.100"   # graffato: la parte trovata
    assert bd.loc[bd.id_bene == "6", ["ref_ade", "aggancio"]].values.tolist() == [["A045_000100.1", "punto"]]
    assert bd.loc[bd.id_bene == "5", "geometry"].isna().item()

    p = pq.read_table(tmp_path / "immobili_pa_2023_particelle.parquet").to_pandas()
    scuola = p[p.ref_ade == "A045_000100.1"].iloc[0]
    assert scuola.n_beni == 3 and scuola.n_fabbricati == 3 and scuola.aggancio == "esatto" and "Edificio scolastico" in scuola.tipologie
    g = shapely.from_wkb(scuola.geometry)
    assert len(g.interiors) == 1
    assert 8000 < scuola.area_m2 < 9500            # 0,001° x 0,001° a 42,7° N meno il buco ≈ 8.800 m²


def test_prodotti_del_sito(tmp_path: Path):
    """GeoParquet di prova → GeoJSON per tippecanoe, PMTiles (se c'è tippecanoe) e indice SQLite senza dati personali."""
    import shutil
    import sqlite3
    import pytest
    from territorio import immobili_pa_sito as s
    beni = ip.leggi_csv_mef(CSV)
    beni["cedente"] = "MARIO ROSSI"; beni["cedente_cf"] = "RSSMRA00A01H501X"; beni["tipologia_amm"] = "Comuni"
    bf = tmp_path / "mef.parquet"; beni.to_parquet(bf)
    comune = _zip({"A045_ACQUASPARTA_ple.gml": _gml(_membro("A045_000100.1", [QUADRO, BUCO]), _membro("A045_002100.64", [QUADRO]))})
    reg = tmp_path / "R.zip"; reg.write_bytes(_zip({"TR.zip": _zip({"A045_ACQUASPARTA.zip": comune})}))
    tab, _ = ip.poligoni_regione(reg, ip.richieste_per_comune(beni), tmp_path)
    pq.write_table(tab, tmp_path / "pol.parquet")
    ip.componi(bf, [tmp_path / "pol.parquet"], tmp_path, 2023)
    part, ben = tmp_path / "immobili_pa_2023_particelle.parquet", tmp_path / "immobili_pa_2023_beni.parquet"

    cont = s.scrivi_geojsonseq(part, ben, tmp_path / "gj")
    assert cont["particelle"] == 2
    righe = [json.loads(x) for x in (tmp_path / "gj" / "particelle.geojsonl").read_text().splitlines()]
    misto = next(r for r in righe if r["properties"]["r"] == "A045_000100.1")
    assert misto["properties"]["t"] == "E" and misto["properties"]["g"] == "C" and misto["properties"]["n"] == 3
    assert s.gruppo_ente("Università") == "U" and s.gruppo_ente("qualcosa di nuovo") == "A"

    db = tmp_path / "i.sqlite"
    s.indice_sqlite(ben, part, db)
    c = sqlite3.connect(db)
    colonne = [r[1] for r in c.execute("PRAGMA table_info(beni)")]
    assert "cedente" not in colonne and "cedente_cf" not in colonne and "amm_cf" not in colonne
    trovati = c.execute("SELECT b.id_bene FROM cerca JOIN beni b ON b.rowid = cerca.rowid WHERE cerca MATCH ?",
                        ['acquasparta scolastico']).fetchall()
    assert trovati == [("1",)]
    assert c.execute("SELECT lon, lat FROM particelle WHERE ref_ade='A045_000100.1'").fetchone()[0] > 12

    if not shutil.which("tippecanoe"):
        pytest.skip("tippecanoe non installato")
    ind = s.prepara(tmp_path, 2023, tmp_path / "tessere", tmp_path / "indice", "prova")
    assert (tmp_path / "tessere" / "immobili_pa_2023.pmtiles").stat().st_size > 1000
    assert ind["pmtiles"] == "/edifici3d/immobili_pa/immobili_pa_2023.pmtiles"
    assert json.loads((tmp_path / "tessere" / "indice.json").read_text())["gruppi"]["U"] == "Università"
    # contenuto delle tessere (17/11/2026: con lo zoom minimo per feature restava una sola particella per tessera)
    lettore = pytest.importorskip("pmtiles.reader"); mvt = pytest.importorskip("mapbox_vector_tile")
    import gzip, math
    r = lettore.Reader(lettore.MmapSource(open(tmp_path / "tessere" / "immobili_pa_2023.pmtiles", "rb")))
    def strati(z, lon=12.4930, lat=42.7335):
        n = 2 ** z; x = int((lon + 180) / 360 * n); y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
        d = r.get(z, x, y)
        return {k: len(v["features"]) for k, v in mvt.decode(gzip.decompress(d)).items()} if d else {}
    assert strati(16).get("particelle") == 2 and strati(13).get("particelle") == 2       # le due particelle di prova
    assert strati(10).get("punti") == 2 and "particelle" not in strati(10)


def test_comando_immobili_pa_passa_il_percorso_a_componi(tmp_path, monkeypatch):
    """Il comando passava a componi la tabella invece del percorso del parquet (errore sul server il 17/11)."""
    from territorio import __main__ as cli
    f = tmp_path / "mef_immobili_pa_2023.parquet"
    pd.DataFrame({"id_bene": ["1"]}).to_parquet(f)
    visti = {}
    monkeypatch.setattr(ip, "scarica_poligoni", lambda dest, beni, reg: [])
    monkeypatch.setattr(ip, "componi", lambda b, pol, dest, anno: visti.setdefault("b", b) and {})
    assert cli.main(["immobili-pa", "--dest", str(tmp_path)]) == 0
    assert visti["b"] == f
