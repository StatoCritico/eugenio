"""Test della ricerca di un luogo (territorio/luogo.py, 17/11/2026): particella del civico dal WFS catastale, metà della via
da OpenStreetMap o dai civici ANNCSU, vie fra cui scegliere. Dati finti (forme e nomi come nelle risposte vere di Rimini e
Perugia del 17/11/2026), nessuna chiamata di rete."""
import math

import pandas as pd
import pytest

from territorio import luogo as L
from territorio.anncsu import Indirizzario

# ---------------------------------------------------------------------------------------------- WFS catastale finto
def _anello(punti):
    """(lon, lat) → posList «lat lon» chiusa, come il WFS dell'Agenzia (EPSG:6706)."""
    p = list(punti) + [punti[0]]
    return " ".join(f"{y:.8f} {x:.8f}" for x, y in p)


def _particella(rif, esterno, buchi=()):
    interni = "".join(f"<gml:interior><gml:LinearRing><gml:posList srsDimension=\"2\">{_anello(b)}</gml:posList>"
                      "</gml:LinearRing></gml:interior>" for b in buchi)
    return (f'<wfs:member><CP:CadastralParcel gml:id="CadastralParcel.IT.AGE.PLA.{rif}"><gml:boundedBy><gml:Envelope>'
            f'</gml:Envelope></gml:boundedBy><CP:msGeometry><gml:Polygon gml:id="x" srsName="urn:ogc:def:crs:EPSG::6706">'
            f'<gml:exterior><gml:LinearRing><gml:posList srsDimension="2">{_anello(esterno)}</gml:posList></gml:LinearRing>'
            f'</gml:exterior>{interni}</gml:Polygon></CP:msGeometry><CP:INSPIREID_LOCALID>IT.AGE.PLA.{rif}</CP:INSPIREID_LOCALID>'
            f'<CP:LABEL>{rif.rsplit(".", 1)[1]}</CP:LABEL><CP:NATIONALCADASTRALREFERENCE>{rif}</CP:NATIONALCADASTRALREFERENCE>'
            f'<CP:ADMINISTRATIVEUNIT>{rif[:4]}</CP:ADMINISTRATIVEUNIT></CP:CadastralParcel></wfs:member>')


def _wfs(*particelle):
    return ('<?xml version="1.0" encoding="UTF-8" ?><wfs:FeatureCollection xmlns:CP="http://mapserver.gis.umn.edu/mapserver" '
            'xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:wfs="http://www.opengis.net/wfs/2.0" numberMatched="2">'
            + "".join(particelle) + "</wfs:FeatureCollection>")


# particella a L (il baricentro cade fuori), una piccola, la strada (particella STRADA) che le separa
ELLE = [(12.5890, 44.0420), (12.5900, 44.0420), (12.5900, 44.0422), (12.5892, 44.0422), (12.5892, 44.0430), (12.5890, 44.0430)]
PICCOLA = [(12.5903, 44.0420), (12.5905, 44.0420), (12.5905, 44.0422), (12.5903, 44.0422)]
STRADA = [(12.5880, 44.0418), (12.5910, 44.0418), (12.5910, 44.04195), (12.5880, 44.04195)]
XML = _wfs(_particella("H294_009900.2330", ELLE), _particella("H294_009900.2476", PICCOLA),
           _particella("H294_009900.STRADA002", STRADA))


def test_leggi_wfs_e_geometria():
    ps = L.leggi_wfs(XML)
    assert [p.riferimento for p in ps] == ["H294_009900.2330", "H294_009900.2476", "H294_009900.STRADA002"]
    elle, piccola, strada = ps
    assert strada.strada and not elle.strada
    assert elle.parti["foglio"] == "99" and elle.mappale == "2330" and elle.parti["belfiore"] == "H294"
    assert elle.riquadro() == pytest.approx([12.5890, 44.0420, 12.5900, 44.0430])
    # area: 0,001° × 0,0002° + 0,0002° × 0,0008° ≈ 80 m × 22 m + 16 m × 89 m
    assert 2800 < elle.area_m2() < 3300
    # il baricentro della L cade fuori: il punto interno è sempre dentro la particella
    x, y = elle.punto_interno()
    assert elle.contiene(x, y)
    assert piccola.contiene(*piccola.punto_interno())
    assert piccola.distanza_m(12.5900, 44.0421) == pytest.approx(0.0003 * 111_320 * math.cos(math.radians(44.0421)), rel=0.02)


def test_buchi_e_poligono_ad_anello():
    esterno = [(0.0, 45.0), (0.001, 45.0), (0.001, 45.001), (0.0, 45.001)]
    buco = [(0.0002, 45.0002), (0.0008, 45.0002), (0.0008, 45.0008), (0.0002, 45.0008)]
    p = L.leggi_wfs(_wfs(_particella("A944_019000.1", esterno, [buco])))[0]
    assert not p.contiene(0.0005, 45.0005)                       # il cortile non è della particella
    x, y = p.punto_interno()
    assert p.contiene(x, y)


def test_scegli_particella():
    ps = L.leggi_wfs(XML)
    p, d = L.scegli_particella(ps, 44.0421, 12.5891)              # dentro la L
    assert p.mappale == "2330" and d == 0
    # fuori dalle particelle edificate (fra la L e la piccola): la più vicina entro 15 m
    p, d = L.scegli_particella(ps, 44.04199, 12.59012)
    assert p.mappale == "2330" and 9 < d < 10.5
    # sulla strada (STRADA002 non conta mai)
    p, _ = L.scegli_particella(ps, 44.04190, 12.59040)
    assert p.mappale == "2476"
    # quella scelta da Zornade, se è nel raggio, vale più della più vicina
    p, _ = L.scegli_particella(ps, 44.04199, 12.59012, {"belfiore": "H294", "foglio": "99", "mappale": "2476"})
    assert p.mappale == "2476"
    # niente entro il raggio
    assert L.scegli_particella(ps, 44.0500, 12.6000) == (None, 0.0)
    par = L.parametri_wfs(44.0421, 12.5891)
    s, o, n, e = map(float, par["BBOX"].split(","))
    assert s < 44.0421 < n and o < 12.5891 < e and (n - s) * 110_574 == pytest.approx(30, rel=0.01)


def test_accessi_vicini():
    punti = [(12.589748, 44.042903), (12.589789, 44.042567), (12.589041, 44.047484), (12.62, 44.06), (12.589789, 44.042567)]
    assert L.vicini_entro(punti, 44.042903, 12.589748) == [(12.589748, 44.042903), (12.589789, 44.042567), (12.589041, 44.047484)]


# ---------------------------------------------------------------------------------------------- metà della via
def _retta(lon0, lat0, lon1, lat1, n=5):
    return [(lon0 + (lon1 - lon0) * i / n, lat0 + (lat1 - lat0) * i / n) for i in range(n + 1)]


def test_meta_della_via_e_catene():
    # una via a tratti (come OSM la spezza agli incroci), con i tratti in ordine e verso sparsi
    via = _retta(12.60, 44.04, 12.57, 43.99, 30)
    tratti = [via[20:], via[:8][::-1], via[7:21]]
    assert len(L.catene(tratti)) == 1
    x, y, l = L.meta_via(tratti)
    assert (x, y) == pytest.approx((12.585, 44.015), abs=2e-4)
    assert 5800 < l < 6300
    # il baricentro dei vertici di una via con i vertici fitti da una parte è lontano dalla metà: qui no
    fitta = _retta(12.60, 44.04, 12.59, 44.0233, 40) + _retta(12.59, 44.0233, 12.57, 43.99, 2)[1:]
    x, y, _ = L.meta_via([fitta])
    assert (x, y) == pytest.approx((12.585, 44.015), abs=3e-4)


def test_meta_con_diramazioni():
    """Diramazioni con lo stesso nome (service, residential): la metà resta sulla via principale, verso il centro."""
    via = _retta(12.60, 44.04, 12.57, 43.99, 30)
    rami = [_retta(*via[5], via[5][0] + 0.002, via[5][1], 2), _retta(*via[25], via[25][0] - 0.002, via[25][1], 2)]
    x, y, _ = L.meta_via([via[:11], via[10:21], via[20:], *rami])
    assert abs(y - 44.015) < 0.002 and abs(x - 12.585) < 0.002


def test_gruppi_frazioni():
    a = _retta(12.0, 44.0, 12.0, 44.01)
    b = _retta(12.0, 44.0101, 12.0, 44.02)           # 10 m dopo: stesso tratto
    c = _retta(12.1, 44.0, 12.1, 44.01)              # 8 km più in là: un'altra frazione
    assert L.gruppi([a, b, c], L.GRUPPO_M) == [[0, 1], [2]]


def test_meta_civici():
    punti = [(12.0, 44.0 + i * 0.001) for i in range(11)][::-1]
    x, y, l = L.meta_civici(punti)
    assert (x, y) == pytest.approx((12.0, 44.005)) and l == pytest.approx(1105.7, rel=0.01)


# ---------------------------------------------------------------------------------------------- vie e scelte
def _way(nome, punti, highway="secondary"):
    return {"type": "way", "tags": {"name": nome, "highway": highway}, "geometry": [{"lon": x, "lat": y} for x, y in punti]}


VIA_CORIANO = _retta(12.600, 44.040, 12.576, 43.991, 20)
OSM_RIMINI = {"elements": [
    _way("Via Coriano", VIA_CORIANO[:9]), _way("Via Coriano", VIA_CORIANO[8:]),
    _way("Via Coriano", _retta(*VIA_CORIANO[4], VIA_CORIANO[4][0] + 0.001, VIA_CORIANO[4][1], 2), "service"),
]}
OSM_PERUGIA = {"elements": [
    {"type": "node", "lat": 43.0743033, "lon": 12.3382, "tags": {"name": "Sant'Andrea delle Fratte", "place": "suburb"}},
    _way("Strada delle Fratte", _retta(12.3200, 43.0730, 12.3236, 43.0705, 4), "residential"),
    _way("Strada di Sant'Andrea d'Agliano", _retta(12.400, 43.050, 12.404, 43.048, 3), "unclassified"),
    _way("Strada di Sant'Andrea D'Agliano", _retta(12.404, 43.048, 12.405, 43.047, 3), "unclassified"),
]}


def _idx():
    righe = [("099014", "H294", "VIA CORIANO", c, "", 44.040 - c * 0.00015, 12.600 - c * 0.00007, 4) for c in range(1, 330, 4)]
    righe += [("099014", "H294", "VIA CORCIANO", c, "", 44.012, 12.60 + c * 0.0001, 4) for c in range(1, 40, 2)]
    righe += [("099014", "H294", "VIALE LUIGI SETTEMBRINI", 2, e, 44.042903 + i * 0.0004, 12.589748, 4)
              for i, e in enumerate(["", "B", "O"])]
    righe += [("054039", "G478", "STRADA DELLE FRATTE", c, "", 43.0717, 12.3218, 4) for c in range(1, 6)]
    righe += [("054039", "G478", "VIA SANT'ANDREA", c, "", 43.1119, 12.3897, 4) for c in range(1, 4)]
    return Indirizzario(pd.DataFrame(righe, columns=["istat", "belfiore", "odonimo", "civico", "esponente", "lat", "lon",
                                                     "metodo"]))


def test_query_overpass():
    q = L.query_overpass("054039", "via Sant'Andrea delle Fratte")
    assert 'area["ref:ISTAT"="054039"]' in q and '[aàáâ]ndr[eèéê][aàáâ]|fr[aàáâ]tt[eèéê]' in q
    assert "cycleway" not in q and "footway" not in q and 'node(area.a)["place"' in q
    assert '"g[iìíî][uùúû]gn[oòóô]",i]' in L.query_overpass("054039", "via 2 Giugno")         # numeri fuori dal filtro
    assert L.query_overpass("12", "via Coriano") is None          # mai un codice ISTAT strano nella query


def test_via_coriano_una_via_sola():
    idx = _idx()
    u = L.unisci_candidate(L.candidate_osm(OSM_RIMINI, "via Coriano"), L.candidate_anncsu(idx, "099014", "H294", "via Coriano"))
    scelta, elenco, scegli = L.decidi(u)
    assert not scegli and scelta["nome"] == "Via Coriano" and scelta["civici"] == 83
    assert (scelta["lon"], scelta["lat"]) == pytest.approx(((12.600 + 12.576) / 2, (44.040 + 43.991) / 2), abs=8e-4)
    assert scelta["riquadro"] == pytest.approx([12.576, 43.991, 12.600, 44.040], abs=2e-4)
    assert [c["nome"] for c in elenco] == ["VIA CORCIANO"]      # simile (errore di battitura), solo come «altre vie»


def test_perugia_si_sceglie():
    idx = _idx()
    via = "via Sant'Andrea delle Fratte"
    u = L.unisci_candidate(L.candidate_osm(OSM_PERUGIA, via), L.candidate_anncsu(idx, "054039", "G478", via))
    scelta, elenco, scegli = L.decidi(u)
    assert scelta is None and scegli
    nomi = [c["nome"] for c in elenco]
    assert nomi[0] == "Sant'Andrea delle Fratte" and elenco[0]["tipo"] == "località"
    assert "Strada delle Fratte" in nomi and "VIA SANT'ANDREA" in nomi
    assert sum(n.lower().startswith("strada di sant'andrea") for n in nomi) == 1     # «d'Agliano» e «D'Agliano»: una via
    fr = elenco[nomi.index("Strada delle Fratte")]
    assert fr["civici"] == 5 and fr["fonte"] == L.ATTRIBUZIONE_OSM                # ANNCSU e OSM uniti


def test_stessa_via_in_due_frazioni():
    osm = {"elements": [_way("Via Roma", _retta(12.0, 44.0, 12.0, 44.005)), _way("Via Roma", _retta(12.1, 44.0, 12.1, 44.005))]}
    scelta, elenco, scegli = L.decidi(L.candidate_osm(osm, "via Roma"))
    assert scelta is None and scegli and [c["tratto"] for c in elenco] == [1, 2]
    assert L.etichetta(elenco[0]).startswith("Via Roma (tratto 1, ")


# ---------------------------------------------------------------------------------------------- una ricerca
RIGA_CIVICO = {"metodo": "indirizzo", "indirizzo": "via Settembrini 2", "civico": "", "fonte_punto": "ANNCSU",
               "indirizzo_trovato": "VIALE LUIGI SETTEMBRINI 2", "lat": 44.0421, "lon": 12.5891, "nota": "",
               "belfiore": "H294", "foglio_catasto": "99", "mappale": "2330", "istat": "099014"}
# Rimini, ospedale Infermi (forme semplificate dei dati veri del 17/11/2026): l'accesso «2» nella particella 2330 a sud,
# «2/B» nella piccola 2476, «2/O» nella particella n. 1 dell'ospedale (~10 ettari)
OSPEDALE = [(12.5852, 44.0447), (12.5909, 44.0447), (12.5909, 44.0489), (12.5852, 44.0489)]
XML_OSPEDALE = _wfs(_particella("H294_009900.1", OSPEDALE))


PARTICELLE_RIMINI = [("H294_009900.2330", ELLE), ("H294_009900.2476", PICCOLA), ("H294_009900.STRADA002", STRADA),
                     ("H294_009900.1", OSPEDALE)]


def _wfs_rimini(chiamate, rifiuta_riquadro=False):
    """WFS finto: le particelle il cui riquadro tocca il BBOX chiesto (come il servizio vero); con rifiuta_riquadro le
    richieste grandi hanno «Richiesta non valida» (ServiceExceptionReport, come capita al servizio dell'Agenzia)."""
    def wfs(par):
        chiamate.append(par)
        s, o, n, e = map(float, par["BBOX"].split(","))
        if rifiuta_riquadro and n - s > 0.001:
            return ('<?xml version="1.0"?><ServiceExceptionReport version="1.1.1"><ServiceException code="InvalidFormat">'
                    '<![CDATA[Richiesta non valida ]]></ServiceException></ServiceExceptionReport>')
        dentro = [(r, a) for r, a in PARTICELLE_RIMINI
                  if min(x for x, _ in a) <= e and max(x for x, _ in a) >= o and min(y for _, y in a) <= n and max(y for _, y in a) >= s]
        return _wfs(*[_particella(r, a) for r, a in dentro])
    return wfs


def _idx_rimini(con_o=True):
    righe = [("099014", "H294", "VIALE LUIGI SETTEMBRINI", 2, "", 44.0421, 12.5891, 4),
             ("099014", "H294", "VIALE LUIGI SETTEMBRINI", 2, "B", 44.0421, 12.5904, 4),
             ("099014", "H294", "VIALE LUIGI SETTEMBRINI", 2, "C", 44.0421, 12.5904, 4)]       # stesso punto: una chiamata
    if con_o:
        righe.append(("099014", "H294", "VIALE LUIGI SETTEMBRINI", 2, "O", 44.047484, 12.589041, 4))
    righe.append(("099014", "H294", "VIALE LUIGI SETTEMBRINI", 2, "Z", 44.0600, 12.6200, 4))        # oltre 600 m: no
    return Indirizzario(pd.DataFrame(righe, columns=["istat", "belfiore", "odonimo", "civico", "esponente", "lat", "lon",
                                                     "metodo"]))


def test_arricchisci_civico_particella_piu_grande():
    """Scelta B (Paolo, 17/11/2026): fra le particelle degli accessi 2, 2/B, 2/O vince la n. 1 dell'ospedale."""
    chiamate = []
    e = L.arricchisci(RIGA_CIVICO, "099014", "H294", _idx_rimini(), _wfs_rimini(chiamate), None)
    assert e["luogo_regola"] == "particella_piu_grande_del_civico"
    assert e["particella_ade"]["mappale"] == "1" and e["particella_ade"]["area_m2"] > 100_000
    assert e["luogo_riquadro"] == pytest.approx([12.5852, 44.0447, 12.5909, 44.0489])
    o = L.leggi_wfs(XML_OSPEDALE)[0]
    assert o.contiene(e["luogo_lon"], e["luogo_lat"]) and e["luogo_fonte"] == L.ATTRIBUZIONE_CATASTO
    assert len(chiamate) == 1 and e["particella_ade"]["richiesta_wfs"] == "riquadro"   # una sola richiesta per tutti
    s, o, n, x = map(float, chiamate[0]["BBOX"].split(","))
    assert n < 44.0480 and x < 12.5910 and s > 44.0418 and o > 12.5885                   # accessi + 20 m, non quello a 2 km
    assert e["particella_ade"]["accessi"] == 3                                           # 2, 2/B (= 2/C), 2/O


def test_particella_piu_grande_ripiego_per_accesso():
    """Riquadro rifiutato dal WFS (o troppo grande): una richiesta per accesso, al più 4 insieme; stesso risultato."""
    import threading
    import time
    chiamate, insieme, massimo, lock = [], [0], [0], threading.Lock()
    base = _wfs_rimini(chiamate, rifiuta_riquadro=True)

    def wfs(par):
        with lock:
            insieme[0] += 1
            massimo[0] = max(massimo[0], insieme[0])
        time.sleep(0.02)
        try:
            return base(par)
        finally:
            with lock:
                insieme[0] -= 1
    e = L.arricchisci(RIGA_CIVICO, "099014", "H294", _idx_rimini(), wfs, None)
    assert e["particella_ade"]["mappale"] == "1" and e["particella_ade"]["richiesta_wfs"] == "per_accesso"
    assert len(chiamate) == 2 + 3 and massimo[0] <= L.PARALLELE      # riquadro due volte, poi i 3 accessi
    # riquadro oltre il lato massimo: niente richiesta unica
    punti = [(12.5891, 44.0421), (12.5960, 44.0470)]                  # ~560 m × 545 m + margini: ancora uno solo
    _, modo, _ = L.particelle_degli_accessi(punti, _wfs_rimini([]))
    assert modo == "riquadro"
    chiamate = []
    _, modo, _ = L.particelle_degli_accessi(punti, _wfs_rimini(chiamate), lato_max_m=300)
    assert modo == "per_accesso" and len(chiamate) == 2
    # risposta troncata (numberMatched > numberReturned): ripiego
    tronca = lambda par: '<wfs:FeatureCollection numberMatched="900" numberReturned="500"></wfs:FeatureCollection>'  # noqa: E731
    assert not L.completo(tronca(None)) and L.completo(XML)


def test_arricchisci_civico_un_accesso_o_con_esponente():
    chiamate = []
    e = L.arricchisci(RIGA_CIVICO, "099014", "H294", _idx_rimini(con_o=False), _wfs_rimini(chiamate), None)
    assert e["luogo_regola"] == "particella_piu_grande_del_civico" and e["particella_ade"]["mappale"] == "2330"
    idx1 = Indirizzario(pd.DataFrame([("099014", "H294", "VIALE LUIGI SETTEMBRINI", 2, "", 44.0421, 12.5891, 4)],
                                     columns=["istat", "belfiore", "odonimo", "civico", "esponente", "lat", "lon", "metodo"]))
    chiamate = []
    e = L.arricchisci(RIGA_CIVICO, "099014", "H294", idx1, _wfs_rimini(chiamate), None)
    assert e["luogo_regola"] == "particella_del_civico" and e["particella_ade"]["mappale"] == "2330" and len(chiamate) == 1
    # «2/B» scritto: la particella di quell'accesso, non la più grande
    riga = {**RIGA_CIVICO, "indirizzo": "via Settembrini 2/B", "indirizzo_trovato": "VIALE LUIGI SETTEMBRINI 2/B",
            "lat": 44.0421, "lon": 12.5904}
    chiamate = []
    e = L.arricchisci(riga, "099014", "H294", _idx_rimini(), _wfs_rimini(chiamate), None)
    assert e["luogo_regola"] == "particella_dell_accesso" and e["particella_ade"]["mappale"] == "2476" and len(chiamate) == 1
    # foglio e particella (o punto di Zornade): la particella del punto
    e = L.arricchisci({**RIGA_CIVICO, "metodo": "catasto"}, "099014", "H294", _idx_rimini(), _wfs_rimini([]), None)
    assert e["luogo_regola"] == "particella_del_punto" and e["particella_ade"]["mappale"] == "2330"


def test_arricchisci_senza_fonti_o_con_errori():
    e = L.arricchisci(RIGA_CIVICO, "099014", "H294", _idx(), lambda p: (_ for _ in ()).throw(OSError("giù")), None)
    assert e["luogo_regola"] is None
    assert e["luogo_tipo"] is None and "cartografia catastale non disponibile" in e["luogo_avviso"]
    e = L.arricchisci(RIGA_CIVICO, "099014", "H294", _idx(), lambda p: _wfs(), None)
    assert e["luogo_tipo"] is None and "nessuna particella" in e["luogo_avviso"]
    e = L.arricchisci({**RIGA_CIVICO, "lat": None, "lon": None}, "099014", "H294", _idx(), lambda p: XML, None)
    assert e["luogo_tipo"] is None


def test_arricchisci_via_senza_civico():
    riga = {"metodo": "indirizzo", "indirizzo": "via Coriano", "civico": "", "fonte_punto": "ANNCSU", "lat": 44.016,
            "lon": 12.595, "nota": "civico non indicato: usato il 210 di VIA CORIANO"}
    e = L.arricchisci(riga, "099014", "H294", _idx(), lambda p: pytest.fail("niente WFS per una via"), lambda q: OSM_RIMINI)
    assert e["luogo_tipo"] == "via" and e["via_scelta"]["nome"] == "Via Coriano" and not e["scegli_via"]
    assert e["luogo_regola"] == "meta_della_via"
    assert e["luogo_fonte"] == L.ATTRIBUZIONE_OSM and e["vie_candidate"][0]["etichetta"].startswith("VIA CORCIANO (")
    # Overpass giù: restano i civici ANNCSU (metà della spezzata dei civici), con l'avviso
    e = L.arricchisci(riga, "099014", "H294", _idx(), None, lambda q: None)
    assert e["luogo_tipo"] == "via" and e["via_scelta"]["nome"] == "VIA CORIANO" and "OpenStreetMap" in e["luogo_avviso"]
    assert e["luogo_lat"] == pytest.approx(44.040 - 165 * 0.00015, abs=0.002)


def test_arricchisci_via_non_riconosciuta_con_civico():
    """Perugia, «via Sant'Andrea delle Fratte 5»: Zornade trova un punto lontano; con vie simili e nessuna riconosciuta si
    fa scegliere (la pagina aggiunge il punto di Zornade fra le scelte); nessuna chiamata al WFS."""
    riga = {"metodo": "indirizzo", "indirizzo": "via Sant'Andrea delle Fratte 5", "civico": "", "fonte_punto": "Zornade",
            "lat": 43.095, "lon": 12.338, "nota": ""}
    e = L.arricchisci(riga, "054039", "G478", _idx(), lambda p: pytest.fail("niente WFS"), lambda q: OSM_PERUGIA)
    assert e["scegli_via"] and e["vie_candidate"][0]["tipo"] == "località" and e["luogo_tipo"] is None
    # via che OSM conosce con quel nome (ANNCSU no): il punto di Zornade vale, si va alla particella
    osm = {"elements": [_way("Via Paoluzza", _retta(12.3, 43.09, 12.31, 43.09))]}
    riga2 = {**riga, "indirizzo": "via Paoluzza 3", "lat": 43.0901, "lon": 12.305}
    xml = _wfs(_particella("G478_012300.45", [(12.304, 43.0900), (12.306, 43.0900), (12.306, 43.0902), (12.304, 43.0902)]))
    e = L.arricchisci(riga2, "054039", "G478", _idx(), lambda p: xml, lambda q: osm)
    assert not e["scegli_via"] and e["luogo_tipo"] == "particella" and e["particella_ade"]["mappale"] == "45"


def test_gruppi_di_molti_civici_veloce_e_uguale_al_confronto_a_coppie():
    """19/11/2026, Venezia «piazza San Marco»: un odonimo ANNCSU con migliaia di civici (il sestiere) non deve fermare la
    ricerca. Solo punti: griglia (prima tutte le coppie, n²); stessi gruppi del confronto a coppie."""
    import random
    import time
    from territorio import luogo as L
    random.seed(7)
    pts = [[(12.33 + random.random() * 0.012, 45.432 + random.random() * 0.008)] for _ in range(20000)]
    t = time.perf_counter()
    assert len(L.gruppi(pts, L.GRUPPO_CIVICI_M)) == 1
    assert time.perf_counter() - t < 1.0
    for k in range(100):
        n = random.randint(1, 50)
        p = [[(12 + random.random() * 0.2, 44 + random.random() * 0.15)] for _ in range(n)]
        d = random.choice([300, 1000, 1500])
        a = sorted(sorted(g) for g in L.gruppi(p, d))
        b = sorted(sorted(g) for g in L.gruppi([q + q for q in p], d))     # linee degeneri: confronto a coppie
        assert a == b, (k, n, d)
