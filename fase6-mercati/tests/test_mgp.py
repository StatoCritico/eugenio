"""Mercato del giorno prima (20/11/2026): offerte pubbliche in XML (con e senza i campi 2025), curve ordinate, serie
aggiuntive, lavoro notturno `mercato-mgp` (deduplicazione, ripresa, storico a blocchi, email solo per errori veri).
Tutti i dati sono inventati: nessun dato vero del GME nel repository."""
from __future__ import annotations

import base64
import datetime as dt
import io
import json
import os
import zipfile

import httpx
import pandas as pd
import pytest

from mercati_energia import archivio, gme, mgp, mgp_notturno
from mercati_energia.config import Config, Gme, Mgp, carica

# ---------------------------------------------------------------------------------------------- XML inventati
SCHEMA = """<xs:schema id="NewDataSet" xmlns="" xmlns:xs="http://www.w3.org/2001/XMLSchema"
 xmlns:msdata="urn:schemas-microsoft-com:xml-msdata"><xs:element name="NewDataSet" msdata:IsDataSet="true">
 <xs:complexType><xs:choice minOccurs="0" maxOccurs="unbounded"><xs:element name="OfferteOperatori">
 <xs:complexType><xs:sequence><xs:element name="PURPOSE_CD" type="xs:string" minOccurs="0" /></xs:sequence>
 </xs:complexType></xs:element></xs:choice></xs:complexType></xs:element></xs:schema>"""


def _offerta(**campi) -> str:
    return "<OfferteOperatori>" + "".join(f"<{k}>{v}</{k}>" for k, v in campi.items()) + "</OfferteOperatori>"


def _xml(offerte: list[dict]) -> bytes:
    return ('<?xml version="1.0" standalone="yes"?>\n<NewDataSet>' + SCHEMA
            + "".join(_offerta(**o) for o in offerte) + "</NewDataSet>").encode("utf-8")


def _zip(file: dict[str, bytes]) -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for n, d in file.items():
            z.writestr(n, d)
    return b.getvalue()


def offerta_2025(giorno="20251020", scopo="OFF", stato="ACC", zona="NORD", unita="UP_FINTA_1", q="10.000",
                 prezzo="50.00", acc="10.000", periodo=1, gran="PT15", tipo="S", merito=1, **altro):
    return {**dict(PURPOSE_CD=scopo, TYPE_CD="REG", STATUS_CD=stato, MARKET_CD="MGP", UNIT_REFERENCE_NO=unita,
                BID_OFFER_DATE_DT=giorno, TRANSACTION_REFERENCE_NO=f"T{unita}{periodo}{scopo}{prezzo}",
                QUANTITY_NO=q, AWARDED_QUANTITY_NO=acc, ENERGY_PRICE_NO=prezzo, MERIT_ORDER_NO=merito,
                PARTIAL_QTY_ACCEPTED_IN="N", ZONE_CD=zona, AWARDED_PRICE_NO="60.00", OPERATORE="OPERATORE FINTO SPA",
                SUBMITTED_DT="20251019093000123", BILATERAL_IN="false", OFFER_TYPE=tipo, BLOCK_ID="",
                PERIOD=periodo, GRANULARITY=gran, MINIMUM_ACCEPTANCE_RATIO=""), **altro}


def offerta_oraria(giorno="20240115", scopo="OFF", stato="ACC", zona="SUD", q="5,5", prezzo="70,25", ora=3, **k):
    """Formato fino al 30/9/2025: INTERVAL_NO, niente PERIOD/GRANULARITY/OFFER_TYPE, decimali con la virgola."""
    return dict(PURPOSE_CD=scopo, TYPE_CD="REG", STATUS_CD=stato, MARKET_CD="MGP", UNIT_REFERENCE_NO="UP_FINTA_9",
                INTERVAL_NO=ora, BID_OFFER_DATE_DT=giorno, QUANTITY_NO=q, AWARDED_QUANTITY_NO="0",
                ENERGY_PRICE_NO=prezzo, MERIT_ORDER_NO=1, ZONE_CD=zona, **k)


def test_xml_2025_con_zip_dentro_zip():
    righe = [offerta_2025(periodo=p, merito=p) for p in (1, 2)] + [offerta_2025(scopo="BID", gran="PT60", periodo=1,
                                                                                  tipo="B", BLOCK_ID="BL1")]
    interno = _zip({"20251020MGPOffertePubbliche.xml": _xml(righe)})
    df = mgp.leggi_offerte_xml(_zip({"MGP_OffertePubbliche.zip": interno}))
    assert len(df) == 3
    assert list(df.periodo) == [1, 2, 1] and list(df.minuti) == [15, 15, 60]
    assert df.QUANTITY_NO.dtype == "float64" and df.QUANTITY_NO.iloc[0] == 10.0
    assert df.SUBMITTED_DT.iloc[0] == 20251019093000123
    assert df.data.iloc[0] == dt.date(2025, 10, 20)
    assert df.OFFER_TYPE.tolist() == ["S", "S", "B"] and df.BLOCK_ID.iloc[2] == "BL1"
    assert "INTERVAL_NO" not in df


def test_xml_orario_senza_campi_2025_e_virgola():
    df = mgp.leggi_offerte_xml(_zip({"a.xml": _xml([offerta_oraria(), offerta_oraria(ora=4, CAMPO_NUOVO="x")])}))
    assert list(df.periodo) == [3, 4] and set(df.minuti) == {60}
    assert df.QUANTITY_NO.tolist() == [5.5, 5.5] and df.ENERGY_PRICE_NO.iloc[0] == 70.25
    assert "PERIOD" not in df and "GRANULARITY" not in df
    assert df.CAMPO_NUOVO.iloc[1] == "x"                       # campi nuovi: restano, come testo


def test_xml_semplice_e_vuoto():
    assert len(mgp.leggi_offerte_xml(_xml([offerta_2025()]))) == 1
    assert mgp.leggi_offerte_xml(_zip({"leggimi.txt": b"niente"})).empty


def test_xml_a_blocchi_di_righe(monkeypatch):
    monkeypatch.setattr(mgp, "BLOCCO_RIGHE", 7)
    df = mgp.leggi_offerte_xml(_zip({"a.xml": _xml([offerta_2025(periodo=p % 96 + 1, unita=f"U{p}") for p in range(30)])}))
    assert len(df) == 30 and df.UNIT_REFERENCE_NO.nunique() == 30


# ---------------------------------------------------------------------------------------------- curve ordinate
def _offerte_curve() -> pd.DataFrame:
    o = [
        offerta_2025(scopo="OFF", prezzo="30", q="100", acc="100", periodo=5, gran="PT15", unita="A", merito=1),
        offerta_2025(scopo="OFF", prezzo="10", q="50", acc="50", periodo=3, gran="PT30", unita="B", merito=2),
        offerta_2025(scopo="OFF", prezzo="80", q="40", acc="0", stato="REJ", periodo=2, gran="PT60", unita="C",
                     merito=3),
        offerta_2025(scopo="OFF", prezzo="20", q="70", acc="0", stato="REV", periodo=5, unita="D"),  # revocata
        offerta_2025(scopo="OFF", prezzo="5", q="99", acc="99", periodo=6, unita="E"),               # altro periodo
        offerta_2025(scopo="OFF", prezzo="15", q="25", acc="25", periodo=5, zona="SICI", unita="F"),
        offerta_2025(scopo="BID", prezzo="3000", q="120", acc="120", periodo=5, unita="G"),
        offerta_2025(scopo="BID", prezzo="40", q="60", acc="55", periodo=2, gran="PT60", unita="H"),
        offerta_2025(scopo="BID", prezzo="40", q="10", acc="0", stato="REJ", periodo=5, unita="I"),
        offerta_2025(scopo="BID", prezzo="1", q="30", acc="0", stato="REJ", periodo=5, unita="L"),
    ]
    return mgp.leggi_offerte_xml(_zip({"a.xml": _xml(o)}))


def test_curve_ordinate_italia_quarto_d_ora():
    c = mgp.curve_ordinate(_offerte_curve(), periodo=5)
    off, dom = c["offerta"], c["domanda"]
    assert off.unita.tolist() == ["B", "F", "A", "C"]          # PT30 periodo 3 e PT60 periodo 2 valgono per il 5
    assert off.prezzo.tolist() == [10, 15, 30, 80]
    assert off.cumulata.tolist() == [50, 75, 175, 215]
    assert off.cumulata_accettata.tolist() == [50, 75, 175, 175]
    assert dom.prezzo.tolist() == [3000, 40, 40, 1]            # domanda: prezzo decrescente
    assert dom.cumulata.tolist() == [120, 180, 190, 220]
    assert set(off.stato) == {"ACC", "REJ"}


def test_curve_zona_stati_e_aggregate():
    o = _offerte_curve()
    nord = mgp.curve_ordinate(o, periodo=5, zona="NORD")
    assert "F" not in nord["offerta"].unita.tolist()
    tutte = mgp.curve_ordinate(o, periodo=5, stati=None)
    assert "D" in tutte["offerta"].unita.tolist()
    agg = mgp.curve_ordinate(o, periodo=5, aggrega=True)["domanda"]
    assert agg.prezzo.tolist() == [3000, 40, 1] and agg.quantita.tolist() == [120, 70, 30]
    assert agg.offerte.tolist() == [1, 2, 1]
    # periodo 8 = ultimo quarto d'ora della seconda ora: valgono ancora le offerte orarie, non la PT30 del periodo 3
    p8 = mgp.curve_ordinate(o, periodo=8)["offerta"]
    assert p8.unita.tolist() == ["C"]


def test_curve_orarie_e_da_archivio(tmp_path):
    o = mgp.leggi_offerte_xml(_xml([offerta_oraria(ora=3, prezzo="10"), offerta_oraria(ora=3, prezzo="5"),
                                    offerta_oraria(ora=3, scopo="BID", prezzo="100"), offerta_oraria(ora=4)]))
    archivio.scrivi_giorno(tmp_path, "mgp_offerte", dt.date(2024, 1, 15), o)
    c = mgp.curve(tmp_path, dt.date(2024, 1, 15), 3)
    assert c["offerta"].prezzo.tolist() == [5, 10] and len(c["domanda"]) == 1
    assert mgp.curve(tmp_path, dt.date(2024, 1, 16), 3)["offerta"].empty


# ---------------------------------------------------------------------------------------------- serie JSON
def test_tempo_quarti_d_ora_orario_e_cambio_d_ora():
    righe = [{"FlowDate": 20251026, "Hour": 3, "Period": "9", "Market": "MGP", "Liquidity": "70.5",
              "ExchangeVolumes": 1, "OffExchangeVolumes": 2},
             {"FlowDate": 20240115, "Hour": 2, "Period": None, "Market": "MGP", "Liquidity": 60,
              "ExchangeVolumes": 1, "OffExchangeVolumes": 2}]
    df = mgp.normalizza(righe, mgp.SERIE["mgp_liquidita"][1])
    assert df.minuti.tolist() == [15, 60] and df.periodo.tolist() == [9, 2]
    assert df.inizio_utc.iloc[0] == pd.Timestamp("2025-10-26 00:00", tz="UTC")   # 02:00 ora legale, prima delle due
    assert df.inizio_utc.iloc[1] == pd.Timestamp("2024-01-15 00:00", tz="UTC")   # 01:00 ora solare
    assert df.liquidita.tolist() == [70.5, 60.0]


def test_domanda_offerta_e_totali():
    class Cl:
        def richiesta(self, seg, nome, dal, al, *a, **k):
            assert (seg, nome) == ("MGP", "ME_DemandAndSupply")
            return [{"FlowDate": 20251020, "Hour": 1, "Period": 1, "Market": "MGP", "MarketZone": "NORD", "Type": t,
                     "Quantity": q, "AcceptedQuantity": a, "ZonalPrice": 90, "Price": p, "Notes": None}
                    for t, q, a, p in (("OFF", 10, 10, 20), ("OFF", 5, 0, 120), ("BID", 8, 8, 3000))]
    do = mgp.domanda_offerta(Cl(), dt.date(2025, 10, 20))
    assert do.scopo.tolist() == ["OFF", "OFF", "BID"]
    t = mgp.totali_offerta_domanda(do).set_index("lato")
    assert t.loc["OFF", "quantita"] == 15 and t.loc["OFF", "quantita_accettata"] == 10
    assert t.loc["BID", "quantita"] == 8


def test_offerte_dal_client_vero_con_mock_transport(monkeypatch):
    """Il client GME restituisce lo ZIP grezzo per Offers_PublicDomain; se il GME non ha dati, b''."""
    monkeypatch.setattr(gme, "_dormi", lambda s: None)
    corpo = base64.b64encode(_zip({"o.xml": _xml([offerta_2025(), offerta_2025(MARKET_CD="MI-A1")])})).decode()
    risposte = [{"ContentResponse": corpo}, {"ResultRequest": "Nessun dato disponibile"}]
    viste = []

    def g(req):
        if req.url.path.endswith("/Auth"):
            return httpx.Response(200, json={"Success": True, "token": "t"})
        if req.url.path.endswith("/GetMyQuotas"):
            return httpx.Response(200, json={"limits": {}})
        viste.append(json.loads(req.content))
        return httpx.Response(200, json=risposte.pop(0))
    cl = gme.ClientGME("utente", "segreto", transport=httpx.MockTransport(g))
    df = mgp.offerte_pubbliche(cl, dt.date(2025, 10, 20))
    assert len(df) == 1 and df.MARKET_CD.iloc[0] == "MGP"
    assert viste[0]["DataName"] == "Offers_PublicDomain" and viste[0]["IntervalStart"] == 20251020
    assert mgp.offerte_pubbliche(cl, dt.date(2025, 10, 21)).empty


def test_credenziali_rifiutate():
    def g(req):
        return httpx.Response(200, json={"Success": False, "Reason": "Password scaduta"})
    cl = gme.ClientGME("utente", "segreto", transport=httpx.MockTransport(g))
    with pytest.raises(gme.CredenzialiGME):
        cl.richiesta("MGP", "ME_Liquidity", dt.date(2025, 10, 20), dt.date(2025, 10, 20))


# ---------------------------------------------------------------------------------------------- lavoro notturno
OGGI = dt.date(2025, 11, 20)


class GMEFinto:
    """Client finto: liquidità, transiti, fabbisogno, curve aggregate e offerte per giorno, dal 15/10/2025."""
    def __init__(self, inizio=dt.date(2025, 10, 15), offerte_fino=OGGI - dt.timedelta(days=8)):
        self.inizio, self.offerte_fino = inizio, offerte_fino
        self.chiamate: list[tuple] = []
        self.guasti: dict = {}             # (nome, giorno) → eccezione
        self.credenziali_ok = True
        self.oggi = lambda: OGGI

    def richiesta(self, seg, nome, dal, al, attributi=None, piattaforma="PublicMarketResults", dati_stimati=0,
                  grezzo=False, attese_quota=6):
        self.chiamate.append((nome, dal, al))
        if not self.credenziali_ok:
            raise gme.CredenzialiGME("Autenticazione GME fallita: password scaduta")
        if (nome, dal) in self.guasti:
            raise self.guasti[(nome, dal)]
        giorni = [dal + dt.timedelta(days=i) for i in range((al - dal).days + 1)]
        oggi = self.oggi()
        giorni = [g for g in giorni if g >= self.inizio and g <= oggi + dt.timedelta(days=1)]
        if nome == "Offers_PublicDomain":
            g = dal
            if g < self.inizio or g > self.offerte_fino:
                return b""
            return _zip({f"{g:%Y%m%d}MGPOffertePubbliche.xml": _xml(
                [offerta_2025(giorno=f"{g:%Y%m%d}", periodo=p, unita=f"U{p}") for p in (1, 2, 3)])})
        righe = []
        for g in giorni:
            for p in (1, 2):
                base = {"FlowDate": int(f"{g:%Y%m%d}"), "Hour": 1, "Period": str(p), "Market": "MGP"}
                if nome == "ME_Liquidity":
                    righe.append(base | {"Liquidity": 70, "ExchangeVolumes": 100, "OffExchangeVolumes": 40})
                elif nome == "ME_Transits":
                    righe.append(base | {"From": "NORD", "To": "CNOR", "Transit": 500, "Notes": None})
                elif nome == "ME_Demand":
                    righe.append(base | {"Zone": "NORD", "Demand": 20000})
                elif nome == "ME_DemandAndSupply":
                    if g > oggi:
                        continue
                    righe += [base | {"MarketZone": "NORD", "Type": "OFF", "Quantity": 10, "AcceptedQuantity": 5,
                                      "ZonalPrice": 90, "Price": 50},
                              base | {"MarketZone": "NORD", "Type": "BID", "Quantity": 8, "AcceptedQuantity": 5,
                                      "ZonalPrice": 90, "Price": 3000}]
        return righe


class Orologio:
    def __init__(self, giorno=OGGI):
        self.t = dt.datetime.combine(giorno, dt.time(4, 15), gme.ROMA).timestamp()
        self.pause = []

    def adesso(self):
        self.t += 0.01
        return self.t

    def dormi(self, s):
        self.pause.append(s)
        self.t += s


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    """Archivio in DATI/mercati e cartella di lavoro separata, per vedere che non si scrive altrove."""
    dati, lavoro = tmp_path / "DATI" / "mercati", tmp_path / "lavoro"
    lavoro.mkdir()
    monkeypatch.chdir(lavoro)
    o = Orologio()
    monkeypatch.setattr(mgp_notturno, "_adesso", o.adesso)
    monkeypatch.setattr(mgp_notturno, "_dormi", o.dormi)
    cfg = Config(cartella=dati, gme=Gme(utente="utente", inizio_orario=dt.date(2025, 10, 1)),
                 mgp=Mgp(inizio_serie=dt.date(2025, 10, 1), domanda_offerta_inizio=dt.date(2025, 10, 1),
                         offerte_inizio=dt.date(2025, 10, 1), offerte_giorni_per_notte=3, pausa_s=20,
                         domanda_offerta_giorni_per_notte=10, spazio_minimo_gb=0))
    return cfg, o, tmp_path, lavoro


def _file(cartella):
    return sorted(str(p.relative_to(cartella)) for p in cartella.rglob("*") if p.is_file())


def test_notturno_completo_dedup_ripresa_e_solo_in_dati(ambiente):
    cfg, orologio, radice, lavoro = ambiente
    cl = GMEFinto()
    e1 = mgp_notturno.esegui(cfg, client=cl)
    assert e1["errori"] == [] and e1["da_segnalare"] == []
    liq = archivio.leggi(cfg.cartella, "mgp_liquidita")
    assert liq.data.min() == dt.date(2025, 10, 15) and liq.data.max() == OGGI + dt.timedelta(days=1)
    assert len(liq) == 2 * ((OGGI - dt.date(2025, 10, 15)).days + 2)
    st = json.loads((cfg.cartella / "mgp_stato.json").read_text())
    assert st["mgp_liquidita"]["completo"]                     # storico fino a inizio_serie (1/10/2025)
    # offerte: l'ultimo giorno pubblicato e 3 giorni di storico; pause gentili fra una richiesta e l'altra
    off = archivio.giorni(cfg.cartella, "mgp_offerte")
    assert off == [OGGI - dt.timedelta(days=d) for d in (11, 10, 9, 8)]
    assert 20 in orologio.pause
    # curve aggregate: fino a oggi e 10 giorni all'indietro; totali derivati
    do = archivio.giorni(cfg.cartella, "mgp_domanda_offerta")
    assert do[-1] == OGGI and len(do) == 11
    tot = archivio.leggi(cfg.cartella, "mgp_offerta_domanda_totali")
    assert set(tot.lato) == {"OFF", "BID"} and len(tot) == 11 * 2 * 2

    # seconda notte, stesso giorno: niente righe doppie, lo storico riprende da dove era arrivato
    cl.chiamate.clear()
    e2 = mgp_notturno.esegui(cfg, client=cl)
    assert len(archivio.leggi(cfg.cartella, "mgp_liquidita")) == len(liq)
    off2 = archivio.giorni(cfg.cartella, "mgp_offerte")
    assert off2[0] == OGGI - dt.timedelta(days=14) and len(off2) == 7
    assert not any(n == "Offers_PublicDomain" and d in off for n, d, _ in cl.chiamate)   # nessun giorno riscaricato
    for g in off2:
        assert len(archivio.leggi_giorno(cfg.cartella, "mgp_offerte", g)) == 3
    assert e2["da_segnalare"] == []
    # nulla fuori dall'archivio
    assert list(lavoro.iterdir()) == []
    assert all(f.startswith("DATI") for f in _file(radice) if not f.startswith("lavoro"))
    assert "mgp_ultima_esecuzione.json" in _file(cfg.cartella)


def test_storico_offerte_si_ferma_all_inizio_della_serie(ambiente):
    cfg, orologio, _, _ = ambiente
    cfg.mgp.offerte_giorni_per_notte = 50
    cl = GMEFinto(inizio=dt.date(2025, 11, 1))
    mgp_notturno.esegui(cfg, client=cl)
    st = json.loads((cfg.cartella / "mgp_stato.json").read_text())["mgp_offerte"]
    assert st["completo"] and st["inizia_il"] == "2025-11-01"
    assert archivio.giorni(cfg.cartella, "mgp_offerte")[0] == dt.date(2025, 11, 1)
    n = len(cl.chiamate)
    mgp_notturno.esegui(cfg, client=cl)                         # completo: nessuna richiesta di storico
    assert not any(c[0] == "Offers_PublicDomain" for c in cl.chiamate[n:])


def test_giorno_fallito_ritentato_poi_lasciato(ambiente):
    cfg, _, _, _ = ambiente
    cfg.mgp.domanda_offerta = False
    cl = GMEFinto()
    rotto = OGGI - dt.timedelta(days=10)
    cl.guasti[("Offers_PublicDomain", rotto)] = gme.QuotaGME("risposta troppo grande")
    e = mgp_notturno.esegui(cfg, client=cl)
    assert any("troppo grande" in x for x in e["errori"]) and e["da_segnalare"] == []
    assert rotto not in archivio.giorni(cfg.cartella, "mgp_offerte")
    for _ in range(3):
        mgp_notturno.esegui(cfg, client=cl)
    st = json.loads((cfg.cartella / "mgp_stato.json").read_text())["mgp_offerte"]
    assert st["non_scaricati"] == [str(rotto)]
    tentativi = sum(1 for n, d, _ in cl.chiamate if n == "Offers_PublicDomain" and d == rotto)
    assert tentativi == 3
    del cl.guasti[("Offers_PublicDomain", rotto)]
    assert rotto not in archivio.giorni(cfg.cartella, "mgp_offerte")   # oltre i 3 tentativi non si riprova da solo


def test_credenziali_scadute_una_email_per_episodio(ambiente):
    cfg, _, _, _ = ambiente
    cl = GMEFinto()
    cl.credenziali_ok = False
    e1 = mgp_notturno.esegui(cfg, client=cl)
    assert len(e1["da_segnalare"]) == 1 and "password" in e1["da_segnalare"][0].lower()
    e2 = mgp_notturno.esegui(cfg, client=cl)
    assert e2["da_segnalare"] == []
    cl.credenziali_ok = True
    mgp_notturno.esegui(cfg, client=cl)
    cl.credenziali_ok = False
    assert len(mgp_notturno.esegui(cfg, client=cl)["da_segnalare"]) == 1    # nuovo episodio


def test_fonte_ferma_per_giorni(ambiente, monkeypatch):
    cfg, orologio, _, _ = ambiente
    cfg.mgp.domanda_offerta = False
    cl = GMEFinto()
    cl.oggi = mgp_notturno._oggi
    assert mgp_notturno.esegui(cfg, client=cl)["da_segnalare"] == []
    cl.offerte_fino = OGGI - dt.timedelta(days=8)            # il GME smette di pubblicare le offerte
    avvisi = []
    for giorni in range(1, 8):
        orologio.t = dt.datetime.combine(OGGI + dt.timedelta(days=giorni), dt.time(4, 15), gme.ROMA).timestamp()
        avvisi += mgp_notturno.esegui(cfg, client=cl)["da_segnalare"]
    assert len(avvisi) == 1 and "mgp_offerte" in avvisi[0]


def test_senza_credenziali_non_fa_nulla(tmp_path, monkeypatch):
    monkeypatch.delenv("GME_PASSWORD", raising=False)
    cfg = Config(cartella=tmp_path / "mercati", gme=Gme(utente=""))
    e = mgp_notturno.esegui(cfg)
    assert e["saltato"].startswith("Credenziali GME mancanti") and e["da_segnalare"] == []
    assert not (tmp_path / "mercati").exists()


def test_configurazione_mgp(tmp_path):
    (tmp_path / "config.toml").write_text('[archivio]\ncartella = "a"\n[mgp]\nofferte_inizio = 2024-01-01\n'
                                          'offerte_giorni_per_notte = 5\nofferte = false\npausa_s = 2.5\n',
                                          encoding="utf-8")
    cfg = carica(tmp_path / "config.toml")
    assert cfg.mgp.offerte_inizio == dt.date(2024, 1, 1) and cfg.mgp.offerte_giorni_per_notte == 5
    assert cfg.mgp.offerte is False and cfg.mgp.pausa_s == 2.5 and cfg.mgp.domanda_offerta is True
    assert carica(tmp_path / "config.toml").mgp.inizio_serie is None


def test_nessun_dato_gme_nel_sito_o_nei_test():
    """Il modulo non scrive nel sito e il repository non contiene file di offerte vere."""
    radice = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for nome in ("mgp.py", "mgp_notturno.py"):
        testo = open(os.path.join(radice, "mercati_energia", nome), encoding="utf-8").read()
        assert "SITO_DATI" not in testo and "to_csv" not in testo
    estensioni = (".xml", ".parquet", ".zip")
    assert not [f for _, _, fs in os.walk(radice) for f in fs if f.lower().endswith(estensioni)]


def test_limiti_di_spazio(ambiente):
    cfg, _, _, _ = ambiente
    cfg.mgp.domanda_offerta = False
    cfg.mgp.offerte_max_gb = 1e-9                               # archivio "pieno": solo il giorno nuovo
    cl = GMEFinto()
    mgp_notturno.esegui(cfg, client=cl)
    assert archivio.giorni(cfg.cartella, "mgp_offerte") == [OGGI - dt.timedelta(days=8)]
    st = json.loads((cfg.cartella / "mgp_stato.json").read_text())["mgp_offerte"]
    assert st["fermo_per_spazio"]
    cfg.mgp.offerte_max_gb, cfg.mgp.spazio_minimo_gb = 12.0, 1e9  # disco "quasi pieno": un'email, una volta
    e1 = mgp_notturno.esegui(cfg, client=cl)
    e2 = mgp_notturno.esegui(cfg, client=cl)
    assert len(e1["da_segnalare"]) == 1 and "Spazio" in e1["da_segnalare"][0] and e2["da_segnalare"] == []
    assert len(archivio.giorni(cfg.cartella, "mgp_offerte")) == 1
