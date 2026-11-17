"""Test del raccordo delle cabine primarie (dati finti, nessuna chiamata di rete)."""
import json

import pytest

from territorio import cabine as cb
from territorio.cabine import classe_comune, codice_attuale, gettoni, livello_peggiore, punteggio_nome


# ------------------------------------------------------------------------------------------------ criticità

def test_classe_comune_regola_del_contratto():
    # nessun trasformatore
    assert classe_comune({}) == {"livello": None, "quota": None, "pieno": None, "strisce": None}
    # tutti verdi: nessun riempimento
    assert classe_comune({"VERDE": 3}) == {"livello": "VERDE", "quota": 1.0, "pieno": None, "strisce": None}
    # più della metà al livello più alto: colore pieno
    assert classe_comune({"VERDE": 1, "ROSSO": 2})["pieno"] == "ROSSO"
    # qualche ROSSO ma non più della metà: strisce arancione/rosso
    r = classe_comune({"VERDE": 2, "GIALLO": 1, "ROSSO": 1})
    assert r["livello"] == "ROSSO" and r["quota"] == 0.25 and r["pieno"] is None
    assert r["strisce"] == ["ARANCIONE", "ROSSO"]
    # esattamente la metà: strisce (serve q > 0,5 per il pieno)
    assert classe_comune({"GIALLO": 1, "ARANCIONE": 1})["strisce"] == ["GIALLO", "ARANCIONE"]
    # qualche GIALLO: strisce bianco/giallo (VERDE = bianco)
    assert classe_comune({"VERDE": 3, "GIALLO": 1})["strisce"] == ["VERDE", "GIALLO"]
    assert classe_comune({"GIALLO": 2, "VERDE": 1})["pieno"] == "GIALLO"
    # chiavi sconosciute ignorate
    assert classe_comune({"BLU": 4, "VERDE": 1})["livello"] == "VERDE"


def test_livello_peggiore():
    assert livello_peggiore(["VERDE", "ROSSO", "GIALLO"]) == "ROSSO"
    assert livello_peggiore(["?"]) is None and livello_peggiore([]) is None


def test_criticita_comuni_trasformatore_una_volta():
    tr = [("037006", "DE1", "01", "ROSSO", "BOLOGNA"), ("037006", "DE1", "02", "VERDE", "BOLOGNA"),
          ("037006", "DE2", "01", "VERDE", "BOLOGNA"),
          # due vecchi comuni ora fusi nello stesso codice: lo stesso trasformatore conta una volta
          ("028108", "DV9", "RO", "GIALLO", "(NUOVO=028108) CARCERI"),
          ("028108", "DV9", "RO", "GIALLO", "(NUOVO=028108) VIGHIZZOLO D'ESTE")]
    c = cb.criticita_comuni(tr, {"037006": "Bologna", "028108": "Santa Caterina d'Este"})
    assert c["037006"]["trasf"] == {"VERDE": 2, "GIALLO": 0, "ARANCIONE": 0, "ROSSO": 1}
    assert c["037006"]["strisce"] == ["ARANCIONE", "ROSSO"] and c["037006"]["cabine"] == ["DE1", "DE2"]
    assert c["028108"]["trasf"]["GIALLO"] == 1 and c["028108"]["pieno"] == "GIALLO"
    assert cb.conteggi_cabina(tr)["DE1"] == {"VERDE": 1, "GIALLO": 0, "ARANCIONE": 0, "ROSSO": 1}


# ----------------------------------------------------------------------------------------------------- nomi

@pytest.mark.parametrize("ed, osm, minimo", [
    ("PADOVA CENTRO", "Padova Centro", 1.0),
    ("PADOVA N.E.", "Padova NE", 1.0),
    ("PADOVA ZI", "Padova Z.I.", 1.0),
    ("FERMO Z.I.", "Fermo Zona Industriale", 1.0),
    ("S.GIUSTA", "Santa Giusta", 1.0),
    ("SAN GEMINI", "Sangemini", 1.0),
    ("TREZZO D'ADDA", "Trezzo sull'Adda", 1.0),
    ("CAMIN", "Camin CP", 1.0),
    ("GROTTAFUMATA", "Grottafumata TR3", 1.0),
    ("FLUMINIMAGGI", "Fluminimaggiore", 0.9),        # nome troncato a 12 caratteri
    ("Q.S.ELENA", "Quartu Sant'Elena", 0.85),       # iniziale
    ("CANOSA DI PUGLIA CP", "Canosa", 0.8),        # nome OSM accorciato
    ("EBOLI 1", "Eboli", 1.0),
    ("ISOLA C.R.", "Isola Capo Rizzuto", 0.9),      # sigla di iniziali
    ("LECCE IND. CP", "Lecce Industriale", 1.0),    # IND = industriale = ZI
    ("VIGEV.OV", "Vigevano Ovest", 0.85),
])
def test_punteggio_nome_simili(ed, osm, minimo):
    assert punteggio_nome(ed, [osm]) >= minimo


def test_punteggio_nome_diversi():
    assert punteggio_nome("PADOVA FIERA", ["Padova San Lazzaro SC"], {"PADOVA"}) < 0.5
    assert punteggio_nome("VACCARO", ["Torre Mozza"]) == 0
    assert punteggio_nome("PALAU 2", ["Palau"]) < punteggio_nome("PALAU 2", ["Palau 2"])
    assert gettoni("C.P. S. Lorenzo 132 kV e-distribuzione") == ["S", "LORENZO"]
    assert gettoni("Borgonovo V. T.") == ["BORGONOVO", "VT"]


def test_espandi_sigla():
    assert cb.espandi_sigla("VI MONTEVIALE", {"VI": "Vicenza"}) == "VICENZA MONTEVIALE"
    assert cb.espandi_sigla("VIGONOVO", {"VI": "Vicenza"}) == "VIGONOVO"
    assert punteggio_nome(cb.espandi_sigla("ME RIVIERA", {"ME": "Messina"}), ["Messina Riviera"]) == 1.0


# ---------------------------------------------------------------------------------------------------- ISTAT

ATTUALI = {"028108": "Santa Caterina d'Este", "090064": "San Teodoro", "083079": "San Teodoro",
           "111002": "Armungia", "037006": "Bologna"}


def test_codice_attuale():
    assert codice_attuale("037006", "BOLOGNA", ATTUALI) == ("037006", "uguale")
    assert codice_attuale("028022", "(NUOVO=028108) CARCERI", ATTUALI) == ("028108", "nuovo_ed")
    # cambi di provincia in catena (092002 → 107002 → 111002)
    assert codice_attuale("092002", "ARMUNGIA", ATTUALI, {"092002": "107002", "107002": "111002"}) == \
        ("111002", "variazioni")
    # codice sconosciuto (118001 di e-distribuzione): si usa il nome
    assert codice_attuale("118001", "ARMUNGIA", ATTUALI) == ("111002", "nome")
    # omonimi: decide la provincia
    assert codice_attuale("113021", "SAN TEODORO", ATTUALI) == (None, "ambiguo")
    assert codice_attuale("113021", "SAN TEODORO", ATTUALI, provincia={"090", "113"}) == ("090064", "nome")
    assert codice_attuale("999999", "NESSUNO", ATTUALI) == (None, "non_trovato")


def test_leggi_successivi_istat(tmp_path):
    (tmp_path / "var.csv").write_bytes(
        ("Anno;Tipo variazione;Codice Regione;Codice Unità territoriale sovracomunale;"
         "Codice Comune formato alfanumerico;Denominazione Comune;Codice Regione associato alla variazione;"
         "Codice Unità territoriale sovracomunale associato alla variazione;"
         "Codice del Comune associato alla variazione o nuovo codice Istat del Comune ;Denominazione\n"
         "2016;AP;20;092;092002;Armungia;20;111;111002;\n"
         "1991;CD;08;035;035018;Ciano d'Enza;08;035;035018;Canossa\n").encode("latin1"))
    (tmp_path / "soppressi.csv").write_bytes(
        ("Anno;Sigla Automobilistica;Codice Unità territoriale sovracomunale (Uts);Codice Comune;"
         "Denominazione Comune;Comune soppresso per scorporo;Data evento;"
         "Codice del Comune associato alla variazione;Denominazione Comune associato alla variazione\n"
         "2024;VI;024;024044;Gambugliano;;22/01/2024;024128;Sovizzo\n").encode("latin1"))
    s = cb.leggi_successivi_istat(tmp_path)
    assert s == {"092002": "111002", "024044": "024128"}


# ----------------------------------------------------------------------------------------------- OSM e scelta

def test_candidata_osm():
    assert cb.candidata_osm({"name": "Camin CP", "operator": "e-distribuzione S.p.A.", "substation": "distribution",
                             "voltage": "132000"})
    assert not cb.candidata_osm({"substation": "minor_distribution", "operator": "e-distribuzione S.p.A."})
    assert not cb.candidata_osm({"name": "Padova FS", "operator": "Rete Ferroviaria Italiana", "voltage": "132000"})
    assert not cb.candidata_osm({"name": "Acciaierie Venete 132", "operator": "Acciaierie Venete",
                                 "substation": "transmission", "voltage": "132000"})
    # CP dentro la stazione di una centrale Enel, o etichettata male ma con il nome giusto
    assert cb.candidata_osm({"name": "Quero", "operator": "Enel Green Power", "substation": "transmission",
                             "voltage": "132000"})
    assert cb.candidata_osm({"name": "Cabina Primaria Pula", "substation": "minor_distribution", "voltage": "150000"})
    assert not cb.candidata_osm({"area_m2": 20})          # cabina secondaria senza attributi
    assert cb.kv_massimo("380000;132000") == 380 and cb.kv_massimo(None) is None


def test_assegna_ungherese():
    p = {("A", 1): 0.9, ("A", 2): 0.8, ("B", 1): 0.85, ("B", 2): 0.1, ("C", 3): 0.1}
    assert cb.assegna(p, minimo=0.3) == {"A": 2, "B": 1}


def test_svg_utm_e_poligono():
    # il punto (0, 0) dei percorsi SVG corrisponde a E = -AX/S, N = AY/S
    e, n = cb.svg_utm(0, 0)
    assert e == pytest.approx(-cb.SVG_AX / cb.SVG_S) and n == pytest.approx(cb.SVG_AY / cb.SVG_S)
    g = cb.poligono_svg("M0,0L1,0L1,1L0,1Z")
    assert g.area == pytest.approx((1 / cb.SVG_S) ** 2, rel=1e-6)   # 1 unità ≈ 1 km
    x, y = cb.utm(9.0, 45.0)                                        # meridiano centrale del fuso 32
    assert float(x) == pytest.approx(500000, abs=0.01) and float(y) == pytest.approx(4982950.4, abs=1)


# ------------------------------------------------------------------------------------- raccordo completo

def _quadrato(x0, y0, x1, y1):
    from shapely.geometry import box
    return box(x0, y0, x1, y1)


def _lonlat(e, n):
    """Inversa approssimata di utm() per i test (Newton su due passi)."""
    lon, lat = 9 + (e - 500000) / 78000, n / 111000
    for _ in range(6):
        x, y = cb.utm(lon, lat)
        lon += (e - float(x)) / 78600
        lat += (n - float(y)) / 111100
    return lon, lat


@pytest.fixture
def scena():
    """Padova in piccolo: un comune di 10 km diviso in due aree GSE di e-distribuzione, due cabine che lo servono
    («PADOVA CENTRO» col nome in OSM, «PADOVA FIERA» che in OSM si chiama «Padova San Lazzaro SC»), un'area di un
    altro gestore con una sottostazione OSM e un comune senza sottostazioni."""
    E0, N0 = 725000, 5030000
    comuni = {"028060": {"nome": "Padova", "geom": _quadrato(E0, N0, E0 + 10000, N0 + 10000)},
              "028001": {"nome": "Abano Terme", "geom": _quadrato(E0 - 10000, N0, E0, N0 + 10000)},
              "058091": {"nome": "Roma", "geom": _quadrato(E0 + 50000, N0, E0 + 60000, N0 + 10000)}}
    aree = [{"COD_AC": "AC001E00906", "RAG_SOC": "e-distribuzione S.p.A.", "geom": _quadrato(E0, N0, E0 + 5000, N0 + 10000)},
            {"COD_AC": "AC001E00909", "RAG_SOC": "e-distribuzione S.p.A.",
             "geom": _quadrato(E0 + 5000, N0, E0 + 10000, N0 + 10000)},
            {"COD_AC": "AC001E00001", "RAG_SOC": "e-distribuzione S.p.A.", "geom": _quadrato(E0 - 10000, N0, E0, N0 + 10000)},
            {"COD_AC": "AC001A00001", "RAG_SOC": "ARETI SPA", "TXT1": " ", "TXT2": "",
             "geom": _quadrato(E0 + 50000, N0, E0 + 60000, N0 + 10000)}]

    def osm(i, e, n, **t):
        lo, la = _lonlat(e, n)
        return {"osm_id": i, "lon": lo, "lat": la, **t}
    sott = [osm("node/1", E0 + 2500, N0 + 5000, name="Padova Centro", operator="e-distribuzione S.p.A.",
                substation="distribution", voltage="50000"),
            osm("way/2", E0 + 7500, N0 + 5000, name="Padova San Lazzaro SC", operator="e-distribuzione S.p.A.",
                substation="distribution", voltage="132000"),
            osm("way/3", E0 + 55000, N0 + 5000, name="Tor di Quinto", operator="Areti", voltage="150000")]
    cabine = {"DV001381475": {"nome": "PADOVA CENTRO", "comuni": {"028060"}},
              "DV001382982": {"nome": "PADOVA FIERA", "comuni": {"028060", "028001"}},
              "DV001380000": {"nome": "ABANO", "comuni": {"028001"}}}
    return cabine, comuni, sott, aree


def test_raccorda_padova(scena):
    cabine, comuni, sott, aree = scena
    righe, diag = cb.raccorda(cabine, comuni, sott, aree)
    r = {x["cod_cp_ed"]: x for x in righe}
    assert r["DV001381475"]["cod_ac"] == "AC001E00906" and r["DV001381475"]["esito"] == "sicuro"
    assert r["DV001381475"]["osm_id"] == "node/1" and r["DV001381475"]["punteggio_nome"] == 1.0
    # PADOVA FIERA: per esclusione la sottostazione «Padova San Lazzaro SC», area AC001E00909, da verificare
    assert r["DV001382982"]["osm_id"] == "way/2" and r["DV001382982"]["cod_ac"] == "AC001E00909"
    assert r["DV001382982"]["esito"] == "da_verificare" and "nome" in r["DV001382982"]["nota"]
    # ABANO: nessuna sottostazione, area stimata dai comuni serviti
    assert r["DV001380000"]["esito"] == "senza_posizione" and r["DV001380000"]["cod_ac"] == "AC001E00001"
    assert "stimata" in r["DV001380000"]["nota"]
    assert diag["esiti"] == {"sicuro": 1, "da_verificare": 1, "senza_posizione": 1}
    # le aree non abbinate escono come solo_gse, con la sottostazione OSM che vi ricade
    solo = cb.righe_solo_gse(aree, {x["cod_ac"] for x in righe}, sott)
    assert [(x["cod_ac"], x["gestore"], x["osm_id"], x["esito"]) for x in solo] == \
        [("AC001A00001", "ARETI SPA", "way/3", "solo_gse")]


def test_uscite(scena, tmp_path):
    cabine, comuni, sott, aree = scena
    righe, _ = cb.raccorda(cabine, comuni, sott, aree)
    cb.scrivi_raccordo(righe, tmp_path / "r.csv", "2026-11-17", "AC_Comuni_2025")
    testa = (tmp_path / "r.csv").read_text(encoding="utf-8").splitlines()[0].split(",")
    assert testa[:14] == ["cod_ac", "gestore", "cod_cp_ed", "nome_cp_ed", "comuni_serviti", "osm_id", "osm_nome",
                          "lat", "lon", "punteggio_nome", "distanza_m", "esito", "data_raccordo", "versione_ac"]
    g = cb.geojson_cabine(righe, {"DV001381475": {"VERDE": 1, "GIALLO": 0, "ARANCIONE": 0, "ROSSO": 2}},
                          "2026-10-31", "2026-11-17", "AC_Comuni_2025")
    assert "OpenStreetMap" in g["attribuzione"] and "ODbL" in g["licenza"]
    p = {f["properties"]["cod_cp_ed"]: f["properties"] for f in g["features"]}
    assert p["DV001381475"]["livello"] == "ROSSO" and p["DV001382982"]["livello"] is None
    assert "DV001380000" not in p                   # senza posizione: niente punto
    json.dumps(g)                                   # serializzabile


def test_leggi_edistribuzione_e_non_concessionari(tmp_path):
    (tmp_path / "grezzi").mkdir()
    (tmp_path / "grezzi" / "028.json").write_text(json.dumps({
        "DataRisposta": "2026-11-17 17:56:05", "Provincia": "028", "_provincia": {"codice": "028"},
        "ElencoComuni": [{"CodiceIstat": "028022", "Descrizione": "(NUOVO=028108) CARCERI", "ElencoTrasformatori": [
            {"CodCabinaPrimaria": "DV001384581", "CodTrasformatore": "RO", "IdSezioneATMT": "536",
             "LivSaturTraformatore": "ROSSO", "NomeCabinaPrimaria": "ESTE NUOVA"}]}]}), encoding="utf-8")
    cab, tr, mappa, data = cb.leggi_edistribuzione(tmp_path, ATTUALI)
    assert cab["DV001384581"]["comuni"] == {"028108"} and mappa["028022"] == ("028108", "nuovo_ed")
    assert data == "2026-11-17" and tr[0][3] == "ROSSO"
    righe = [{"pro_com_t": "037006", "comune": "Bologna", "servitoed": 1},
             {"pro_com_t": "090064", "comune": "San Teodoro", "servitoed": 0},
             {"pro_com_t": "090064", "comune": "San Teodoro", "servitoed": 0},
             {"pro_com_t": " ", "comune": " ", "servitoed": 1}]
    nc = cb.non_concessionari(righe, ATTUALI, {}, {"090064": "20"}, con_trasformatori={"090064"})
    assert nc == [{"istat": "090064", "istat_2021": "090064", "nome": "San Teodoro", "nome_2021": "San Teodoro",
                   "regione": "20", "modo": "uguale", "con_trasformatori_ed": True}]
