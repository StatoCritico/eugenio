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
          '"Regione del bene";"Comune del bene";"Latitudine";"Longitudine";"Identificativo catastale";'
          '"Tipologia Bene Immobile";"Superficie (mq)";"Descrizione Compendio"')
RIGHE = [
    '"FABBRICATO";"COMUNE DI ACQUASPARTA (TR)";"Comuni";1;"UMBRIA";"Acquasparta";42,7334;12,4930;"A045:::1:1::2";'
    '"Edificio scolastico (es.: scuola di ogni ordine e grado, università, scuola di formazione)";1.250;"SCUOLA ""G. VERDI""\r\nPLESSO"',
    '"FABBRICATO";"COMUNE DI ACQUASPARTA (TR)";"Comuni";2;"UMBRIA";"Acquasparta";42,7334;12,4930;"A045:::1:1::3";'
    '"Ufficio strutturato ed assimilabili";300;""',
    '"TERRENO";"REGIONE UMBRIA";"Regioni";3;"UMBRIA";"Acquasparta";42,70;12,50;"A045::0021:0064:::";'
    '"Terreno agricolo";10000;""',
    '"FABBRICATO";"COMUNE DI MODENA";"Comuni";4;"EMILIA-ROMAGNA";"Modena";44,64;10,92;'
    '"F363:A::13:100::1;F363:A::13:101::";"Caserma";500;""',
    '"FABBRICATO";"COMUNE DI MODENA";"Comuni";5;"EMILIA-ROMAGNA";"Modena";;;"";"Caserma";0;""',
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
    for strano in ("A045_0001001", "A045_00010.1", "x"):
        try:
            ip.chiave_ade(strano)
            raise AssertionError(strano)
        except ValueError:
            pass


def test_csv_mef():
    df = ip.leggi_csv_mef(CSV)
    assert len(df) == 5 and "natura" in df and "id_catastale" in df
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
    assert stat["agganciate"] == 3 and stat["comuni"] == 2
    f = tmp_path / "poligoni.parquet"
    pq.write_table(tab, f)

    bf = tmp_path / "mef.parquet"
    beni.to_parquet(bf)
    ris = ip.componi(bf, [f], tmp_path, 2023)
    assert ris == {"beni": 5, "beni_con_identificativo": 4, "beni_con_poligono": 4, "particelle": 3}

    b = pq.read_table(tmp_path / "immobili_pa_2023_beni.parquet")
    meta = json.loads(b.schema.metadata[b"geo"])
    assert meta["primary_column"] == "geometry" and b"EuGEnio" in b.schema.metadata[b"attribuzione"]
    bd = b.to_pandas()
    assert bd.loc[bd.id_bene == "4", "particella_chiave"].item() == "F363|A|0013|100"   # graffato: la parte trovata
    assert bd.loc[bd.id_bene == "5", "geometry"].isna().item()

    p = pq.read_table(tmp_path / "immobili_pa_2023_particelle.parquet").to_pandas()
    scuola = p[p.chiave == "A045||0001|1"].iloc[0]
    assert scuola.n_beni == 2 and scuola.n_fabbricati == 2 and "Edificio scolastico" in scuola.tipologie
    g = shapely.from_wkb(scuola.geometry)
    assert len(g.interiors) == 1
    assert 8000 < scuola.area_m2 < 9500            # 0,001° x 0,001° a 42,7° N meno il buco ≈ 8.800 m²
