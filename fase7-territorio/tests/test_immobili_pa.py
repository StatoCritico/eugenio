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

    assert c.execute("SELECT valore FROM info").fetchall() == []          # senza info: tabella vuota
    c.close()
    assert not list(tmp_path.glob(".*.nuovo"))                              # niente file provvisori rimasti

    if not shutil.which("tippecanoe"):
        pytest.skip("tippecanoe non installato")
    (tmp_path / "tessere").mkdir()
    vecchio = tmp_path / "tessere" / "immobili_pa_2023.pmtiles"; vecchio.write_bytes(b"vecchio")
    piu_vecchio = tmp_path / "tessere" / "immobili_pa_2023_202601010000.pmtiles"; piu_vecchio.write_bytes(b"x")
    (tmp_path / "tessere" / "indice.json").write_text(json.dumps({"pmtiles": "/edifici3d/immobili_pa/immobili_pa_2023.pmtiles"}))
    ind = s.prepara(tmp_path, 2023, tmp_path / "tessere", tmp_path / "indice", "prova", versione="202611221200")
    pm = tmp_path / "tessere" / "immobili_pa_2023_202611221200.pmtiles"
    assert pm.stat().st_size > 1000
    assert ind["pmtiles"] == "/edifici3d/immobili_pa/immobili_pa_2023_202611221200.pmtiles"
    # il precedente (quello di indice.json) resta per le pagine già aperte, i più vecchi si tolgono
    assert vecchio.exists() and not piu_vecchio.exists()
    scritto = json.loads((tmp_path / "tessere" / "indice.json").read_text())
    assert scritto["gruppi"]["U"] == "Università" and scritto["pmtiles"] == ind["pmtiles"]
    assert list(scritto["gruppi"])[:3] == ["C", "I", "P"]                   # ordine del menu: Unioni dopo i Comuni
    info = dict(sqlite3.connect(tmp_path / "indice" / "immobili_pa_2023.sqlite").execute("SELECT chiave, valore FROM info"))
    assert json.loads(info["pmtiles"]) == ind["pmtiles"]
    assert not list((tmp_path / "tessere").glob(".*")) and not list((tmp_path / "indice").glob(".*"))
    assert not [d for d in (tmp_path / "tessere").iterdir() if d.is_dir()]  # cartella di lavoro tolta
    pm_nome = pm.name
    # contenuto delle tessere (17/11/2026: con lo zoom minimo per feature restava una sola particella per tessera)
    lettore = pytest.importorskip("pmtiles.reader"); mvt = pytest.importorskip("mapbox_vector_tile")
    import gzip, math
    r = lettore.Reader(lettore.MmapSource(open(tmp_path / "tessere" / pm_nome, "rb")))
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


# tipologie come sono scritte nei CSV MEF 2023 (apostrofi al posto degli accenti), con il gruppo atteso
TIPOLOGIE_MEF = {
    "Comuni": "C", "Unioni di Comuni e Comunita' Montane": "I", "Citta' Metropolitane e Province": "P",
    "Regioni": "R", "Enti Locali del Servizio Sanitario": "S", "Universita'": "U",
    "Aziende, Enti e Istituti Territoriali per l'Edilizia Residenziale": "E",
    "Ministeri e Presidenza del Consiglio dei Ministri": "M", "Organi Costituzionali e di Rilievo Costituzionale": "M",
    "Agenzie Fiscali": "M", "Enti Nazionali Pubblici di Previdenza e Assistenza": "N",
    "Altre Amministrazioni Centrali": "A", "Altre Amministrazioni Locali": "A", "Aziende di Servizi alla Persona": "A",
    "Camere di Commercio e Unioni delle Camere di Commercio": "A", "Automobile Club d'Italia": "A",
    "Altre Aziende, Consorzi, Enti e Amministrazioni Locali": "A", "Altro": "A",
    "CONSORZI TRA AMMINISTRAZIONI LOCALI - NON IN S13": "A", "ENTI E ISTITUZIONI DI RICERCA - NON IN S13": "A",
    "ENTI PRODUTTORI DI SERVIZI ASSISTENZIALI, RICREATIVI E CULTURALI - NON IN S13": "A",
}


def test_gruppi_con_le_tipologie_vere_dei_csv():
    """22/11/2026: con il confronto letterale Province, Università e Unioni (scritte con l'apostrofo) finivano in «A»."""
    from territorio import immobili_pa_sito as s
    assert len(TIPOLOGIE_MEF) == 21
    for t, g in TIPOLOGIE_MEF.items():
        assert s.gruppo_ente(t) == g, t
    # stesse tipologie con gli accenti del dizionario, maiuscole e spazi diversi
    assert s.gruppo_ente("Università") == "U" and s.gruppo_ente("  città   metropolitane e PROVINCE ") == "P"
    assert s.gruppo_ente("Unioni di Comuni e Comunità Montane") == "I" and s.gruppo_ente("Universita’") == "U"
    assert s.gruppo_ente("") == "A" and s.gruppo_ente(None) == "A"
    assert s.GRUPPI_ENTI["I"][0] == "Unioni di Comuni e Comunità montane"


def test_indice_sostituito_solo_intero(tmp_path: Path, monkeypatch):
    """L'API apre l'indice con immutable=1: un rifacimento interrotto non deve toccare il file in uso."""
    from territorio import immobili_pa_sito as s
    out = tmp_path / "immobili_pa_2023.sqlite"; out.write_bytes(b"in uso")
    def rotto(*a, **k):
        (tmp_path / ".immobili_pa_2023.sqlite.nuovo").write_bytes(b"a meta")
        raise RuntimeError("interrotto")
    monkeypatch.setattr(s, "_scrivi_indice", rotto)
    import pytest
    with pytest.raises(RuntimeError):
        s.indice_sqlite(tmp_path / "b.parquet", tmp_path / "p.parquet", out)
    assert out.read_bytes() == b"in uso" and not (tmp_path / ".immobili_pa_2023.sqlite.nuovo").exists()
    assert s.nome_pmtiles(2023, "202611221200") == "immobili_pa_2023_202611221200.pmtiles"


def test_prepara_versione_e_scambio_senza_tippecanoe(tmp_path: Path, monkeypatch):
    """prepara con le tessere finte: PMTiles con nome nuovo, indice.json per ultimo, precedente tenuto, vecchi tolti."""
    import sqlite3
    from territorio import immobili_pa_sito as s
    beni = ip.leggi_csv_mef(CSV); beni["tipologia_amm"] = "Universita'"
    bf = tmp_path / "mef.parquet"; beni.to_parquet(bf)
    comune = _zip({"A045_ACQUASPARTA_ple.gml": _gml(_membro("A045_000100.1", [QUADRO]))})
    reg = tmp_path / "R.zip"; reg.write_bytes(_zip({"TR.zip": _zip({"A045_ACQUASPARTA.zip": comune})}))
    tab, _ = ip.poligoni_regione(reg, ip.richieste_per_comune(beni), tmp_path)
    pq.write_table(tab, tmp_path / "pol.parquet")
    ip.componi(bf, [tmp_path / "pol.parquet"], tmp_path, 2023)
    tess, ind_dir = tmp_path / "tessere", tmp_path / "indice"
    tess.mkdir()
    (tess / "immobili_pa_2023.pmtiles").write_bytes(b"vecchio")
    (tess / "immobili_pa_2023_202601010000.pmtiles").write_bytes(b"piu vecchio")
    (tess / "indice.json").write_text(json.dumps({"pmtiles": "/edifici3d/immobili_pa/immobili_pa_2023.pmtiles"}))
    visto = {}
    def finte(part, ben, out, attr, e_di=None):
        visto["indice_al_momento"] = json.loads((tess / "indice.json").read_text())["pmtiles"]
        out.write_bytes(b"nuovo"); return {"particelle": 0, "punti": 0}
    monkeypatch.setattr(s, "tessere", finte)
    ind = s.prepara(tmp_path, 2023, tess, ind_dir, "prova", versione="202611221200")
    assert visto["indice_al_momento"].endswith("/immobili_pa_2023.pmtiles")   # indice.json cambia solo dopo
    assert ind["pmtiles"] == "/edifici3d/immobili_pa/immobili_pa_2023_202611221200.pmtiles"
    assert sorted(f.name for f in tess.iterdir()) == ["enti_2023_202611221200.json", "immobili_pa_2023.pmtiles",
                                                      "immobili_pa_2023_202611221200.pmtiles", "indice.json"]
    assert ind["enti"] == "/edifici3d/immobili_pa/enti_2023_202611221200.json"
    db = sqlite3.connect(ind_dir / "immobili_pa_2023.sqlite")
    assert db.execute("SELECT DISTINCT gruppo FROM beni").fetchall() == [("U",)]
    assert json.loads(dict(db.execute("SELECT chiave, valore FROM info"))["gruppi"])["I"].startswith("Unioni")
    db.close()
    # secondo giro: il primo PMTiles (non più in indice.json) si toglie
    s.prepara(tmp_path, 2023, tess, ind_dir, "prova", versione="202611231200")
    assert sorted(f.name for f in tess.glob("*.pmtiles")) == ["immobili_pa_2023_202611221200.pmtiles",
                                                              "immobili_pa_2023_202611231200.pmtiles"]
    assert sorted(f.name for f in tess.glob("enti_*.json")) == ["enti_2023_202611221200.json", "enti_2023_202611231200.json"]
    s.prepara(tmp_path, 2023, tess, ind_dir, "prova", versione="202611241200")
    assert sorted(f.name for f in tess.glob("enti_*.json")) == ["enti_2023_202611231200.json", "enti_2023_202611241200.json"]


# ---------------------------------------------------------------------------------------------- ricerca per ente (22/11/2026)
INTEST_ENTI = ('"Amministrazione Denominazione";"Amministrazione Codice Fiscale";"Tipologia Amministrazione";'
               '"Regione (Amministrazione)";"Provincia (Amministrazione)";"Comune (Amministrazione)";"Titolo proprietà";'
               '"Titolo detenzione";"Sogg. cedente (denominazione)";"Soggetto cedente (CF)";"Natura del bene";"ID bene";'
               '"Regione del bene";"Provincia del bene";"Comune del bene";"Codice Comune del bene";"Indirizzo";"Numero Civico";'
               '"Fonte Georeferenziazione";"Immobile Geo-Ref.";"Latitudine";"Longitudine";"Identificativo catastale";'
               '"Tipologia Bene Immobile";"Superficie (mq)";"Superficie di Riferimento (mq)";"Epoca Costruzione";'
               '"Vinc. culturale/paesaggistico";"Utilizzo del bene";"ui data interamente a terzi"')
CF_COMUNE, CF_ATER = "00012345678", "80098765432"
RIGHE_ENTI = [
    # comune proprietario di due unità nella stessa particella e di un terreno
    f'"COMUNE DI ACQUASPARTA (TR)";"{CF_COMUNE}";"Comuni";"UMBRIA";"TR";"ACQUASPARTA";"Piena proprietà";"";"";"";'
    '"FABBRICATO";1;"UMBRIA";"TR";"Acquasparta";"A045";"Via Roma";"3";"IDENTIFICATIVI_CATASTALI";"Sì";42,7334;12,4930;'
    '"A045:::1:1::2";"Edificio scolastico";1.250;1.250;"Dal 1961 al 1970";"Nessuno";"Utilizzato direttamente";"No"',
    f'"COMUNE DI ACQUASPARTA (TR)";"{CF_COMUNE}";"Comuni";"UMBRIA";"TR";"ACQUASPARTA";"Piena proprietà";"";"";"";'
    '"FABBRICATO";2;"UMBRIA";"TR";"Acquasparta";"A045";"Via Roma";"3";"IDENTIFICATIVI_CATASTALI";"Sì";42,7334;12,4930;'
    '"A045:::1:1::3";"Ufficio strutturato ed assimilabili";0;300;"ND";"Dichiarazione di interesse culturale";"Non utilizzato";"Sì"',
    f'"COMUNE DI ACQUASPARTA (TR)";"{CF_COMUNE}";"Comuni";"UMBRIA";"TR";"ACQUASPARTA";"Piena proprietà";"";"";"";'
    '"TERRENO";3;"UMBRIA";"TR";"Acquasparta";"A045";"";"";"IDENTIFICATIVI_CATASTALI";"Sì";42,70;12,50;"A045::0021:0064:::";'
    '"Terreno agricolo";10.000;10.000;"";"";"";""',
    # stesso bene 2 dichiarato anche dall'ATER che lo gestisce (detenzione): il cedente non deve uscire da nessuna parte
    f'"ATER DELLA PROVINCIA DI TERNI";"{CF_ATER}";"Aziende, Enti e Istituti Territoriali per l\'Edilizia Residenziale";'
    '"UMBRIA";"TR";"TERNI";"";"in gestione per conto di";"MARIO ROSSI";"RSSMRA00A01H501X";'
    '"FABBRICATO";2;"UMBRIA";"TR";"Acquasparta";"A045";"Via Roma";"3";"IDENTIFICATIVI_CATASTALI";"Sì";42,7334;12,4930;'
    '"A045:::1:1::3";"Ufficio strutturato ed assimilabili";0;300;"";"Nessuno";"";""',
    # bene dell'ATER senza particella ma con un punto affidabile
    f'"ATER DELLA PROVINCIA DI TERNI";"{CF_ATER}";"Aziende, Enti e Istituti Territoriali per l\'Edilizia Residenziale";'
    '"UMBRIA";"TR";"TERNI";"Piena proprietà";"";"";"";'
    '"FABBRICATO";9;"UMBRIA";"TR";"Terni";"L117";"Via Lungonera";"1";"UTENTE";"Sì";42,56;12,64;"";"Abitazione";80;80;"";"";"";""',
]
CSV_ENTI = ("\r\n".join([INTEST_ENTI] + RIGHE_ENTI) + "\r\n").encode("cp1252")


def _prodotti_enti(tmp_path: Path):
    beni = ip.leggi_csv_mef(CSV_ENTI)
    bf = tmp_path / "mef.parquet"; beni.to_parquet(bf)
    comune = _zip({"A045_ACQUASPARTA_ple.gml": _gml(_membro("A045_000100.1", [QUADRO]), _membro("A045_002100.64", [QUADRO]))})
    reg = tmp_path / "R.zip"; reg.write_bytes(_zip({"TR.zip": _zip({"A045_ACQUASPARTA.zip": comune})}))
    tab, _ = ip.poligoni_regione(reg, ip.richieste_per_comune(beni), tmp_path)
    pq.write_table(tab, tmp_path / "pol.parquet")
    ip.componi(bf, [tmp_path / "pol.parquet"], tmp_path, 2023)
    return tmp_path / "immobili_pa_2023_beni.parquet", tmp_path / "immobili_pa_2023_particelle.parquet"


def test_enti_tabelle_e_tessere(tmp_path: Path):
    """Id ordinati per nome, chiave stabile dal CF, totali, coppie ente–particella con il ruolo, proprietà «e» delle
    tessere, elenco enti.json; mai CF dell'ente né soggetto cedente in uscita."""
    import sqlite3
    from territorio import immobili_pa_sito as s
    ben, part = _prodotti_enti(tmp_path)
    en = s.enti(ben, part)
    e = en["enti"].set_index("nome")
    # id per nome: «ATER …» prima di «COMUNE …»
    assert list(en["enti"]["nome"]) == ["ATER DELLA PROVINCIA DI TERNI", "COMUNE DI ACQUASPARTA (TR)"]
    assert list(en["enti"]["id"]) == [1, 2]
    assert e.loc["COMUNE DI ACQUASPARTA (TR)", "chiave"] == s.chiave_ente(CF_COMUNE) == s.chiave_ente(" 00012345678 ")
    assert len(s.chiave_ente(CF_COMUNE)) == 10 and s.chiave_ente(CF_COMUNE) != s.chiave_ente(CF_ATER)
    assert e.loc["ATER DELLA PROVINCIA DI TERNI", "gruppo"] == "E"
    c = e.loc["COMUNE DI ACQUASPARTA (TR)"]
    assert (c.n_beni, c.n_fabbricati, c.n_terreni, c.n_particelle) == (3, 2, 1, 2)
    assert c.sup_fabbricati_mq == 1550 and c.sup_terreni_mq == 10000        # superficie di riferimento se manca la dichiarata
    assert (c.n_non_utilizzati, c.n_vincolati, c.n_a_terzi, c.n_detenzione) == (1, 1, 1, 0)
    assert c.epoca_prevalente == "Dal 1961 al 1970" and c.sede_provincia == "TR"
    a = e.loc["ATER DELLA PROVINCIA DI TERNI"]
    assert (a.n_beni, a.n_proprieta, a.n_detenzione, a.n_senza_particella, a.n_particelle) == (2, 1, 1, 1, 1)
    assert list(en["ruolo_righe"]) == ["P", "P", "P", "U", "P"]
    cp = en["coppie"].set_index(["ente", "ref", "ruolo", "natura"])
    assert cp.loc[(2, "A045_000100.1", "P", "E"), "n_beni"] == 2
    assert cp.loc[(1, "A045_000100.1", "U", "E"), "n_beni"] == 1
    assert cp.loc[(1, "b9", "P", "E"), "lon"] == 12.64                    # senza particella: punto del censimento
    assert en["e_di"]["A045_000100.1"] == ",1u,2p," and en["e_di"]["b9"] == ",1p,"
    assert en["e_di"]["A045_002100.64"] == ",2p,"

    # tessere: «e» in tutti e due gli strati
    s.scrivi_geojsonseq(part, ben, tmp_path / "gj", en["e_di"])
    righe = [json.loads(x) for x in (tmp_path / "gj" / "particelle.geojsonl").read_text().splitlines()]
    assert {r["properties"]["r"]: r["properties"]["e"] for r in righe} == {"A045_000100.1": ",1u,2p,", "A045_002100.64": ",2p,"}
    punti = [json.loads(x)["properties"] for x in (tmp_path / "gj" / "punti.geojsonl").read_text().splitlines()]
    assert all("e" in p for p in punti) and any(p["r"] == "b9" and p["e"] == ",1p," for p in punti)

    # indice: tabelle nuove, colonna ente e ruolo, niente CF né cedente in nessuna tabella
    db = tmp_path / "i.sqlite"
    s.indice_sqlite(ben, part, db, en=en)
    q = sqlite3.connect(db)
    tabelle = [r[0] for r in q.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    for t in ("beni", "particelle", "enti", "ente_particelle", "comuni", "info"):
        assert t in tabelle, t
    for t in tabelle:
        colonne = {r[1] for r in q.execute(f"PRAGMA table_info({t})")}
        assert not colonne & {"amm_cf", "cedente", "cedente_cf"}, t
    testo = b"".join(open(db, "rb").read().split(b"\x00"))
    for segreto in (CF_COMUNE.encode(), CF_ATER.encode(), b"RSSMRA00A01H501X", b"MARIO ROSSI"):
        assert segreto not in testo, segreto
    assert q.execute("SELECT ente, ruolo FROM beni WHERE id_bene='2' ORDER BY ente").fetchall() == [(1, "U"), (2, "P")]
    assert q.execute("SELECT nome, n_beni FROM enti WHERE chiave=?", [s.chiave_ente(CF_ATER)]).fetchone() == \
        ("ATER DELLA PROVINCIA DI TERNI", 2)
    assert q.execute("SELECT comune, provincia FROM comuni WHERE comune_cod='A045'").fetchone() == ("Acquasparta", "TR")
    assert q.execute("SELECT COUNT(*) FROM ente_particelle WHERE ente=2").fetchone()[0] == 2
    q.close()

    # elenco per il browser
    j = s.enti_json(en, 2023)
    testo_j = json.dumps(j, ensure_ascii=False)
    assert CF_COMUNE not in testo_j and CF_ATER not in testo_j and "ROSSI" not in testo_j
    assert j["campi"][:3] == ["id", "chiave", "nome"]
    r = dict(zip(j["campi"], j["enti"][1]))
    assert r["nome"] == "COMUNE DI ACQUASPARTA (TR)" and r["sede"] == "Acquasparta (TR)" and r["beni"] == 3
    assert [j["regioni"][i] for i in r["regioni"]] == ["UMBRIA"]


def test_enti_senza_codice_fiscale():
    """File senza la colonna del codice fiscale (le prove più vecchie): si raggruppa per nome, chiave dal nome."""
    from territorio import immobili_pa_sito as s
    assert s.chiave_ente(None, "Comune di X") == s.chiave_ente("", "COMUNE  DI X") != s.chiave_ente("X")
