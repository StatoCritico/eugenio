"""Dati di Terna (20/11/2026): quota, token, errori, storico che riprende, deduplicazione, ora legale, lavori del worker
(terna-api, elettricita, carichi). Nessuna rete: httpx.MockTransport e moduli finti della fase 15."""
from __future__ import annotations

import datetime as dt
import json
import logging
import sys
import types

import httpx
import pandas as pd
import pytest

from servizio import config as C
from servizio import terna as T

SEGRETO = "segreto-di-prova-da-non-registrare"


@pytest.fixture
def cartelle(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "DATI", tmp_path / "dati")
    monkeypatch.setattr(C, "TERNA_DATI", tmp_path / "dati" / "terna")
    monkeypatch.setattr(C, "SITO_DATI", tmp_path / "sito_dati")
    (tmp_path / "sito_dati").mkdir()
    monkeypatch.setattr(C, "TERNA_CLIENT_ID", "")
    monkeypatch.setattr(C, "TERNA_CLIENT_SECRET", "")
    return tmp_path


@pytest.fixture
def email(monkeypatch):
    from servizio import avvisi
    inviati = []
    monkeypatch.setattr(avvisi, "invia", lambda oggetto, testo, *a, **k: inviati.append((oggetto, testo)) or True)
    return inviati


class Orologio:
    def __init__(self):
        self.t = 1000.0
        self.attese = []

    def __call__(self):
        return self.t

    def dormi(self, s):
        self.attese.append(s)
        self.t += s


# ------------------------------------------------------------------------------------------------------- quota
def test_quota_tetto_e_azzeramento_il_giorno_dopo(tmp_path):
    giorno = {"g": dt.date(2026, 11, 20)}
    q = T.Quota(tmp_path / "quota.json", 3, oggi=lambda: giorno["g"])
    for _ in range(3):
        q.consuma()
    assert q.usate() == 3 and q.rimaste() == 0
    with pytest.raises(T.QuotaEsaurita):
        q.consuma()
    # persistente: un altro oggetto (riavvio del worker) legge lo stesso contatore
    assert T.Quota(tmp_path / "quota.json", 3, oggi=lambda: giorno["g"]).usate() == 3
    giorno["g"] = dt.date(2026, 11, 21)
    assert q.usate() == 0 and q.rimaste() == 3
    q.consuma()
    assert json.loads((tmp_path / "quota.json").read_text()) == {"giorno": "2026-11-21", "richieste": 1}


def test_tetto_mai_sopra_300(monkeypatch):
    import importlib
    monkeypatch.setenv("TERNA_API_TETTO", "1000")
    try:
        importlib.reload(C)
        assert C.TERNA_API_TETTO == 300
    finally:
        monkeypatch.delenv("TERNA_API_TETTO")
        importlib.reload(C)


# ------------------------------------------------------------------------------------------------------- API
def cliente(tmp_path, gestore, tetto=250):
    o = Orologio()
    http = httpx.Client(transport=httpx.MockTransport(gestore))
    q = T.Quota(tmp_path / "quota.json", tetto)
    return T.ClienteAPI("id-di-prova", SEGRETO, q, http=http, pausa=1.0, dormi=o.dormi, orologio=o), o


def test_token_nuovo_dopo_401(tmp_path, caplog):
    chiamate = []
    token = iter(["t1", "t2"])

    def gestore(req: httpx.Request):
        chiamate.append((req.method, req.url.path, req.headers.get("authorization")))
        if req.url.path.endswith("access-token"):
            corpo = dict(x.split("=") for x in req.content.decode().split("&"))
            assert corpo["grant_type"] == "client_credentials" and corpo["client_secret"] == SEGRETO
            return httpx.Response(200, json={"access_token": next(token), "token_type": "bearer", "expires_in": 300})
        if req.headers["authorization"] == "Bearer t1":
            return httpx.Response(401)
        return httpx.Response(200, json={"result": {"status": "Completed"}, "total_load": [{"date": "x"}]})
    caplog.set_level(logging.DEBUG)
    cli, o = cliente(tmp_path, gestore)
    d = cli.get("load/v2.0/total-load", {"dateFrom": "19/11/2026", "dateTo": "19/11/2026"})
    assert d["total_load"] == [{"date": "x"}]
    assert [c[1].rsplit("/", 1)[-1] for c in chiamate] == ["access-token", "total-load", "access-token", "total-load"]
    assert cli.quota.usate() == 4                    # anche le richieste del token contano
    assert all(a >= 0.999 for a in o.attese) and len(o.attese) == 3     # una richiesta al secondo
    # il token resta valido: la richiesta dopo non ne chiede un altro
    cli.get("load/v2.0/total-load", {"dateFrom": "18/11/2026", "dateTo": "18/11/2026"})
    assert len(chiamate) == 5
    assert SEGRETO not in caplog.text and "t2" not in repr(cli)


def test_token_scaduto_si_rinnova(tmp_path):
    n = {"token": 0}

    def gestore(req):
        if req.url.path.endswith("access-token"):
            n["token"] += 1
            return httpx.Response(200, json={"access_token": f"t{n['token']}", "expires_in": 300})
        return httpx.Response(200, json={"total_load": []})
    cli, o = cliente(tmp_path, gestore)
    cli.get("load/v2.0/total-load", {})
    o.t += 400
    cli.get("load/v2.0/total-load", {})
    assert n["token"] == 2


def test_429_e_5xx_rimandano_senza_ripetere(tmp_path):
    for stato in (429, 503):
        chiamate = []

        def gestore(req):
            chiamate.append(req.url.path)
            if req.url.path.endswith("access-token"):
                return httpx.Response(200, json={"access_token": "t", "expires_in": 300})
            return httpx.Response(stato)
        cli, _ = cliente(tmp_path / str(stato), gestore)
        with pytest.raises(T.Rimanda):
            cli.get("load/v2.0/total-load", {})
        assert len(chiamate) == 2                    # token + una sola richiesta, nessuna ripetizione


def test_corpo_vuoto_si_registra(tmp_path, caplog):
    def gestore(req):
        if req.url.path.endswith("access-token"):
            return httpx.Response(200, json={"access_token": "t", "expires_in": 300})
        return httpx.Response(200, content=b"")
    cli, _ = cliente(tmp_path, gestore)
    with caplog.at_level(logging.WARNING, logger="terna"):
        assert cli.get("load/v2.0/total-load", {"biddingZone": "Nord"}) is None
    assert "corpo vuoto" in caplog.text


def test_token_rifiutato_non_mostra_le_chiavi(tmp_path, caplog):
    def gestore(req):
        return httpx.Response(400, text=f"invalid client {SEGRETO}")
    cli, _ = cliente(tmp_path, gestore)
    with pytest.raises(T.ErroreTerna) as e:
        cli.get("load/v2.0/total-load", {})
    assert SEGRETO not in str(e.value) and SEGRETO not in caplog.text


def test_quota_esaurita_ferma_le_richieste(tmp_path):
    chiamate = []

    def gestore(req):
        chiamate.append(req.url.path)
        if req.url.path.endswith("access-token"):
            return httpx.Response(200, json={"access_token": "t", "expires_in": 300})
        return httpx.Response(200, json={"total_load": []})
    cli, _ = cliente(tmp_path, gestore, tetto=3)
    cli.get("a", {})
    cli.get("b", {})
    with pytest.raises(T.QuotaEsaurita):
        cli.get("c", {})
    assert len(chiamate) == 3


# ------------------------------------------------------------------------------------------------------- normalizzazione
def test_numeri_in_formati_misti():
    assert T._numero("1.234,5") == 1234.5 and T._numero("1,234.5") == 1234.5 and T._numero(" 13") == 13.0
    assert T._numero("12,5") == 12.5 and T._numero(7) == 7.0 and T._numero("") is None and T._numero(None) is None


def test_date_del_download_center():
    assert T._data_dc(63897551100000) == dt.datetime(2025, 10, 31, 23, 45)       # ora locale «ingenua»
    assert T._istante_api("2022-06-10 23:45:00", "+02:00") == dt.datetime(2022, 6, 10, 21, 45, tzinfo=dt.timezone.utc)


def ms(d: dt.datetime) -> int:
    return int((d - dt.datetime(1970, 1, 1)).total_seconds() * 1000) + T.EPOCA_DC_MS


def test_ora_ripetuta_di_ottobre_per_continuita():
    """Download Center: 02:00–02:45 del 26/10/2025 ripetute, in ordine qualsiasi; la riga più vicina alla precedente
    è l'ora legale."""
    righe = [{"Date": ms(dt.datetime(2025, 10, 26, 1, 45)), "Total Load [MW]": 21734, "Bidding Zone": "Italy"}]
    for q, (legale, solare) in enumerate([(21528, 20820), (21403, 20666), (21130, 20605), (21104, 20430)]):
        d = ms(dt.datetime(2025, 10, 26, 2, 15 * q))
        coppia = [{"Date": d, "Total Load [MW]": legale, "Bidding Zone": "Italy"},
                  {"Date": d, "Total Load [MW]": solare, "Bidding Zone": "Italy"}]
        righe += coppia[::-1] if q % 2 else coppia
    righe.append({"Date": ms(dt.datetime(2025, 10, 26, 3, 0)), "Total Load [MW]": 20574, "Bidding Zone": "Italy"})
    n = sorted(T.normalizza("carico_totale", righe, "dc"), key=lambda r: r["istante"])
    assert len({r["istante"] for r in n}) == 10
    assert [r["carico_mw"] for r in n] == [21734, 21528, 21403, 21130, 21104, 20820, 20666, 20605, 20430, 20574]
    assert n[1]["istante"] == dt.datetime(2025, 10, 26, 0, 0, tzinfo=dt.timezone.utc)
    assert n[5]["istante"] == dt.datetime(2025, 10, 26, 1, 0, tzinfo=dt.timezone.utc)


def test_picco_valle_del_download_center_con_il_totale():
    d = ms(dt.datetime(2025, 10, 31, 11))
    righe = [{"Date": d, "Peak Load [MW]": 42.329, "Valley Load [MW]": None, "Type": f, "Primary Source [GW]": v}
             for f, v in (("Hydro", 3.396), ("Thermal", 18.84))]
    n = T.normalizza("picco_valle", righe, "dc")
    tot = [r for r in n if r["fonte"] == ""]
    assert len(n) == 3 and tot[0]["picco_gw"] == 42.329 and tot[0]["valle_gw"] is None


# ------------------------------------------------------------------------------------------------------- archivio
def test_archivio_deduplica_vince_l_ultima(cartelle):
    r = {"date": "2026-11-19 10:00:00", "date_offset": "+01:00", "total_load_MW": "30000.5",
         "forecast_total_load_MW": "1,234.5", "bidding_zone": "Italy"}
    T.archivia("carico_totale", T.normalizza("carico_totale", [r, dict(r, bidding_zone="North")], "api"))
    T.archivia("carico_totale", T.normalizza("carico_totale", [dict(r, total_load_MW="31000")], "dc"))
    df = pd.read_parquet(C.TERNA_DATI / "serie" / "carico_totale" / "2026-11.parquet")
    assert len(df) == 2
    italia = df[df.zona == "Italy"].iloc[0]
    assert italia.carico_mw == 31000 and italia.origine == "dc" and pd.isna(italia.previsione_mw) is False
    assert str(df.istante.dt.tz) == "UTC" and df.istante.iloc[0] == pd.Timestamp("2026-11-19 09:00", tz="UTC")
    assert list(df.columns) == ["istante", "zona", "carico_mw", "previsione_mw", "origine"]


def test_archivio_mese_italiano(cartelle):
    """Il 31/10 alle 23:30 italiane (22:30 UTC) sta nel file di ottobre, l'1/11 alle 00:15 (23:15 UTC del 31) in novembre."""
    righe = [{"date": "2026-10-31 23:30:00", "date_offset": "+01:00", "actual_generation_GWh": "1", "primary_source": "Hydro"},
             {"date": "2026-11-01 00:15:00", "date_offset": "+01:00", "actual_generation_GWh": "2", "primary_source": "Hydro"}]
    T.archivia("produzione", T.normalizza("produzione", righe, "api"))
    s = C.TERNA_DATI / "serie" / "produzione"
    assert len(pd.read_parquet(s / "2026-10.parquet")) == 1 and len(pd.read_parquet(s / "2026-11.parquet")) == 1


def test_imcei_deduplicato(cartelle):
    righe = [{"year": "2021", "month": "11", "region": "Abruzzo", "sector": "ALTRI", "tension_type": "AT",
              "monthly_imcei": " 4", "consumption_Gwh": "11"}]
    T.archivia("imcei", T.normalizza_imcei(righe, 2021, 11))
    T.archivia("imcei", T.normalizza_imcei([dict(righe[0], consumption_Gwh="12")], 2021, 11))
    df = pd.read_parquet(C.TERNA_DATI / "serie" / "imcei" / "2021-11.parquet")
    assert len(df) == 1 and df.consumo_gwh.iloc[0] == 12 and df.indice.iloc[0] == 4 and df.mese.iloc[0] == "2021-11"


# ------------------------------------------------------------------------------------------------------- Download Center
def test_download_center_a_pagine():
    pagine = []

    def gestore(req):
        corpo = json.loads(req.content)
        pagine.append(corpo["pageIndex"])
        assert corpo["filterDataset"] == "TotalLoad" and corpo["filterMonth"] == "10" and corpo["db"] == "dati"
        i = int(corpo["pageIndex"])
        dati = [[ms(dt.datetime(2025, 10, 1, 0, 15 * k)), 1.0 * k, None, "Italy"] for k in range(2 * i, 2 * i + 2)]
        return httpx.Response(200, json={"Columns": {"Date": "Date", "Total Load [MW]": "Number",
                                                     "Forecast Total Load [MW]": "Number", "Bidding Zone": "String"},
                                         "Count": 3, "Data": dati[: 3 - 2 * i]})
    o = Orologio()
    dc = T.ClienteDC(http=httpx.Client(transport=httpx.MockTransport(gestore)), pausa=1.0, dormi=o.dormi, orologio=o,
                     righe_pagina=2)
    righe = dc.mese("TotalLoad", 2025, 10)
    assert pagine == ["0", "1"] and len(righe) == 3 and righe[0]["Bidding Zone"] == "Italy"
    assert o.attese == [1.0]


class DCFinto:
    """Download Center finto: una riga per mese e dataset; `guasti` = mesi che non rispondono."""

    def __init__(self, guasti=()):
        self.chiamate = []
        self.guasti = set(guasti)

    def mese(self, dataset, anno, mese):
        self.chiamate.append((dataset, f"{anno:04d}-{mese:02d}"))
        if f"{anno:04d}-{mese:02d}" in self.guasti:
            raise T.Rimanda("HTTP 503")
        d = ms(dt.datetime(anno, mese, 10, 12))
        if dataset in ("TotalLoad", "MarketLoad"):
            return [{"Date": d, f"{dataset[:-4]} Load [MW]": 1.0, "Bidding Zone": "Italy"}]
        if dataset == "PeakValleyLoad":
            return [{"Date": d, "Peak Load [MW]": 40.0, "Valley Load [MW]": None, "Type": "Hydro", "Primary Source [GW]": 3}]
        nome = {"ActualGeneration": ("Actual Generation", "Primary Source"),
                "RenewableGeneration": ("Renewable Generation", "Energy Source"),
                "EnergyBalance": ("Energy Balance", "Energy Source")}[dataset]
        return [{"Date": d, nome[0]: 2.0, nome[1]: "Hydro"}]


def test_storico_riprende_dallo_stato(cartelle, email, monkeypatch, caplog):
    monkeypatch.setattr(C, "TERNA_STORICO_MESI", 2)
    T.stato_scrivi({"dc": {s: "2021-03" for s in T.SERIE}})
    dc = DCFinto()
    with caplog.at_level(logging.INFO, logger="terna"):
        e = T.aggiorna(oggi=dt.date(2021, 6, 10), dc=dc)
    assert "TERNA_CLIENT_ID o TERNA_CLIENT_SECRET mancanti" in caplog.text and e["api"] == "spenta"
    storico = [c for c in dc.chiamate if c[1] != "2021-06"]
    assert sorted({c[1] for c in storico}) == ["2021-03", "2021-04"] and len(storico) == 12
    assert T.stato_leggi()["dc"] == {s: "2021-05" for s in T.SERIE}
    assert not [c for c in dc.chiamate if c[1] == "2021-06"]    # storico non finito: niente mese in corso
    dc2 = DCFinto()
    T.aggiorna(oggi=dt.date(2021, 6, 11), dc=dc2)
    assert sorted({c[1] for c in dc2.chiamate}) == ["2021-05", "2021-06"]   # ultimo mese finito, poi la riserva del mese in corso
    assert T.stato_leggi()["dc"] == {s: "2021-06" for s in T.SERIE}
    assert (C.TERNA_DATI / "serie" / "carico_totale" / "2021-03.parquet").exists()
    assert email == []                                          # chiavi mancanti: nessuna email


def test_storico_si_ferma_se_il_download_center_non_risponde(cartelle, email, monkeypatch):
    monkeypatch.setattr(C, "TERNA_STORICO_MESI", 3)
    dc = DCFinto(guasti={"2021-01"})
    e = T.aggiorna(oggi=dt.date(2021, 6, 10), dc=dc)
    assert len(dc.chiamate) == 2 and T.stato_leggi().get("dc", {}) == {}
    assert any("non scaricato" in a for a in e["avvisi"]) and email == []


def test_email_se_l_archivio_e_fermo_da_tre_giorni(cartelle, email):
    stato = {"ultimo_ok_dc": "2026-11-15T06:30:00+00:00"}
    esito = {"api": "spenta", "avvisi": ["x"]}
    T._controlla_avviso(stato, esito, adesso=dt.datetime(2026, 11, 17, 7, tzinfo=dt.timezone.utc))
    assert email == []
    T._controlla_avviso(stato, esito, adesso=dt.datetime(2026, 11, 18, 7, tzinfo=dt.timezone.utc))
    T._controlla_avviso(stato, esito, adesso=dt.datetime(2026, 11, 19, 7, tzinfo=dt.timezone.utc))
    assert len(email) == 1 and "Download Center" in email[0][1]
    stato["ultimo_ok_dc"] = "2026-11-19T08:00:00+00:00"
    T._controlla_avviso(stato, esito, adesso=dt.datetime(2026, 11, 19, 9, tzinfo=dt.timezone.utc))
    assert stato["avvisato_dc"] is False


# ------------------------------------------------------------------------------------------------------- aggiornamento dall'API
def api_finta(tmp_path, giorni_vuoti=(), guasto=None):
    chiamate = []

    def gestore(req):
        p = req.url.path
        chiamate.append((p.rsplit("/", 1)[-1], dict(req.url.params)))
        if p.endswith("access-token"):
            return httpx.Response(200, json={"access_token": "t", "expires_in": 300})
        if guasto and guasto in p:
            return httpx.Response(429)
        par = dict(req.url.params)
        if p.endswith("monthly-index-industrial-electrical-consumption"):
            if (int(par["year"]), int(par["month"])) >= (2026, 10):
                return httpx.Response(200, json={"result": {}, "monthly_index_industrial_electrical_consumption": []})
            return httpx.Response(200, json={"monthly_index_industrial_electrical_consumption": [
                {"year": par["year"], "month": par["month"], "region": "Lombardia", "sector": "ALTRI",
                 "tension_type": "AT", "monthly_imcei": "56", "consumption_Gwh": "609"}]})
        g = dt.datetime.strptime(par["dateFrom"], "%d/%m/%Y")
        base = {"date": g.strftime("%Y-%m-%d 12:00:00"), "date_tz": "Europe/Rome", "date_offset": "+01:00"}
        r = {"total-load": ("total_load", {"total_load_MW": "30000", "forecast_total_load_MW": "29000", "bidding_zone": "Italy"}),
             "market-load": ("marketLoad", {"market_load_MW": "28000", "forecast_market_load_MW": "1", "bidding_zone": "Italy"}),
             "peak-valley-load": ("peak_valley_load", {"peak_load_GW": "40.1", "valley_load_GW": ""}),
             "actual-generation": ("actual_generation", {"actual_generation_GWh": "14.38", "primary_source": "Thermal"}),
             "renewable-generation": ("renewable_generation", {"renewable_generation_GWh": "0.2", "energy_source": "Wind"}),
             "energy-balance": ("energy_balance", {"energy_balance_GWh": "14.38", "energy_source": "Thermal"})}
        nome, campi = r[p.rsplit("/", 1)[-1]]
        if g.date() in giorni_vuoti:
            return httpx.Response(200, content=b"")
        return httpx.Response(200, json={"result": {"status": "Completed"}, nome: [dict(base, **campi)]})
    o = Orologio()
    q = T.Quota(tmp_path / "quota_api.json", 250, oggi=lambda: dt.date(2026, 11, 20))
    cli = T.ClienteAPI("id", SEGRETO, q, http=httpx.Client(transport=httpx.MockTransport(gestore)), pausa=1.0,
                       dormi=o.dormi, orologio=o)
    return cli, chiamate


def test_aggiornamento_giornaliero_dall_api(cartelle, email, monkeypatch):
    monkeypatch.setattr(C, "TERNA_STORICO_MESI", 0)
    T.stato_scrivi({"api_giorno": "2026-11-17", "imcei": "2026-08", "dc": {s: "2026-11" for s in T.SERIE}})
    cli, chiamate = api_finta(C.TERNA_DATI)
    dc = DCFinto()
    e = T.aggiorna(oggi=dt.date(2026, 11, 20), api=cli, dc=dc)
    assert e["giorni_api"] == ["2026-11-18", "2026-11-19"] and not e["rimandato"]
    stato = T.stato_leggi()
    assert stato["api_giorno"] == "2026-11-19" and stato["imcei"] == "2026-10"
    assert dc.chiamate == []                                    # l'API ha risposto: niente riserva
    giorni = [c for c in chiamate if c[0] == "total-load"]
    assert giorni[0][1] == {"dateFrom": "18/11/2026", "dateTo": "18/11/2026"} and "biddingZone" not in giorni[0][1]
    assert [c[1] for c in chiamate if c[0].startswith("monthly")] == [{"year": "2026", "month": "8"},
                                                                         {"year": "2026", "month": "9"},
                                                                         {"year": "2026", "month": "10"}]
    assert e["quota_usata"] == len(chiamate) == 1 + 12 + 3
    pv = pd.read_parquet(C.TERNA_DATI / "serie" / "picco_valle" / "2026-11.parquet")
    assert pv.picco_gw.tolist() == [40.1, 40.1] and pv.valle_gw.isna().all() and (pv.fonte == "").all()
    cm = pd.read_parquet(C.TERNA_DATI / "serie" / "carico_mercato" / "2026-11.parquet")
    assert cm.carico_mw.tolist() == [28000, 28000]
    assert email == []
    # lo stesso giorno, di nuovo: niente da chiedere (l'IMCEI si prova una volta al giorno)
    cli2, chiamate2 = api_finta(C.TERNA_DATI)
    T.aggiorna(oggi=dt.date(2026, 11, 20), api=cli2, dc=dc)
    assert chiamate2 == []


def test_429_rimanda_e_lo_stato_non_avanza(cartelle, email, monkeypatch):
    monkeypatch.setattr(C, "TERNA_STORICO_MESI", 0)
    T.stato_scrivi({"api_giorno": "2026-11-18", "dc": {s: "2026-11" for s in T.SERIE}})
    cli, chiamate = api_finta(C.TERNA_DATI, guasto="market-load")
    dc = DCFinto()
    e = T.aggiorna(oggi=dt.date(2026, 11, 20), api=cli, dc=dc)
    assert e["rimandato"] and T.stato_leggi()["api_giorno"] == "2026-11-18"
    assert len([c for c in chiamate if c[0] == "market-load"]) == 1        # nessuna ripetizione immediata
    assert {c[1] for c in dc.chiamate} == {"2026-11"}                      # riserva: mese in corso dal Download Center
    assert email == []


def test_primo_avvio_con_le_chiavi_al_piu_sette_giorni(cartelle, monkeypatch):
    monkeypatch.setattr(C, "TERNA_STORICO_MESI", 0)
    T.stato_scrivi({"imcei": "2026-11", "dc": {s: "2026-11" for s in T.SERIE}})
    cli, chiamate = api_finta(C.TERNA_DATI)
    e = T.aggiorna(oggi=dt.date(2026, 11, 20), api=cli, dc=DCFinto())
    assert e["giorni_api"][0] == "2026-11-13" and e["giorni_api"][-1] == "2026-11-19" and len(e["giorni_api"]) == 7


def test_riserva_dello_storico_dall_api(cartelle, monkeypatch):
    monkeypatch.setattr(C, "TERNA_STORICO_MESI", 1)
    T.stato_scrivi({"api_giorno": "2026-11-19", "imcei": "2026-11", "dc": {s: "2026-10" for s in T.SERIE}})
    cli, chiamate = api_finta(C.TERNA_DATI)
    e = T.aggiorna(oggi=dt.date(2026, 11, 20), api=cli, dc=DCFinto(guasti={"2026-10"}))
    mesi = [c[1] for c in chiamate if c[0] == "total-load"]
    assert mesi == [{"dateFrom": "01/10/2026", "dateTo": "31/10/2026"}]
    assert T.stato_leggi()["dc"]["carico_totale"] == "2026-11"
    assert any("dall'API" in a for a in e["avvisi"])


def test_giorno_con_corpo_vuoto_non_blocca(cartelle, monkeypatch, caplog):
    monkeypatch.setattr(C, "TERNA_STORICO_MESI", 0)
    T.stato_scrivi({"api_giorno": "2026-11-18", "imcei": "2026-11", "dc": {s: "2026-11" for s in T.SERIE}})
    cli, _ = api_finta(C.TERNA_DATI, giorni_vuoti={dt.date(2026, 11, 19)})
    with caplog.at_level(logging.WARNING, logger="terna"):
        T.aggiorna(oggi=dt.date(2026, 11, 20), api=cli, dc=DCFinto())
    assert "corpo vuoto" in caplog.text and SEGRETO not in caplog.text


# ------------------------------------------------------------------------------------------------------- worker
from test_worker import W, scrivi  # noqa: E402  (moduli segnaposto della fase 3 già sistemati lì)


def fase15(monkeypatch, costruisci=None, scarica=None, carichi=None):
    pacchetto = types.ModuleType("elettricita")
    dcm = types.ModuleType("elettricita.terna_dc")
    dcm.scarica = scarica or (lambda raw, dataset=None, ultimi=None: (raw.mkdir(parents=True, exist_ok=True),
                                                                      (raw / "ElectricalEnergy_2025.json").write_text("{}"),
                                                                      {"ElectricalEnergy": [2025]})[2])
    cm = types.ModuleType("elettricita.costruisci")

    def non_pronto(raw, uscita, mappa=None):
        raise NotImplementedError("in lavorazione")
    cm.costruisci = costruisci or non_pronto
    for nome, m in (("elettricita", pacchetto), ("elettricita.terna_dc", dcm), ("elettricita.costruisci", cm)):
        monkeypatch.setitem(sys.modules, nome, m)
    pacchetto.terna_dc, pacchetto.costruisci = dcm, cm
    if carichi is not None:
        km = types.ModuleType("elettricita.carichi")
        km.costruisci_carichi = carichi
        monkeypatch.setitem(sys.modules, "elettricita.carichi", km)
    else:
        monkeypatch.setitem(sys.modules, "elettricita.carichi", None)          # import fallisce


def test_elettricita_non_pubblica_se_costruisci_non_e_pronto(cartelle, email, monkeypatch, caplog):
    fase15(monkeypatch)
    with caplog.at_level(logging.WARNING, logger="worker"):
        e = W.elettricita()
    assert e["saltato"] == "costruisci non pronto" and "non è ancora pronto" in caplog.text
    assert not (C.SITO_DATI / "elettricita").exists() and not (C.SITO_DATI / ".elettricita_nuova").exists()
    assert email == [] and not W._archivio_elettricita_vuoto()


def test_elettricita_pubblica_se_il_controllo_passa(cartelle, email, monkeypatch):
    def costruisci(raw, uscita, mappa=None):
        scrivi(uscita, ["italia.json", "08.json", "burden_sharing.json"])
        return {"file": 3}
    fase15(monkeypatch, costruisci=costruisci)
    scrivi(C.SITO_DATI / "elettricita", ["italia.json", "vecchio.json"])
    e = W.elettricita()
    assert e["pubblicati"] == 3 and (C.SITO_DATI / "elettricita" / "08.json").exists()
    assert not (C.SITO_DATI / "elettricita" / "vecchio.json").exists() and email == []


def test_elettricita_file_pochi_lasciano_i_vecchi(cartelle, email, monkeypatch):
    def costruisci(raw, uscita, mappa=None):
        scrivi(uscita, ["italia.json"], '{"nuovo": 1}')
        return {}
    fase15(monkeypatch, costruisci=costruisci)
    scrivi(C.SITO_DATI / "elettricita", ["italia.json"] + [f"{r:02d}.json" for r in range(1, 21)])
    e = W.elettricita()
    assert "errore" in e and (C.SITO_DATI / "elettricita" / "20.json").exists()
    assert (C.SITO_DATI / "elettricita" / "italia.json").read_text() == "{}"
    assert len(email) == 1 and "incompleti" in email[0][0]


def test_elettricita_senza_italia_json_non_pubblica(cartelle, email, monkeypatch):
    fase15(monkeypatch, costruisci=lambda raw, uscita, mappa=None: scrivi(uscita, ["08.json"]) or {})
    W.elettricita()
    assert not (C.SITO_DATI / "elettricita").exists() and len(email) == 1


def test_elettricita_email_solo_dopo_due_mesi_senza_risposta(cartelle, email, monkeypatch):
    def guasto(raw, dataset=None, ultimi=None):
        raise OSError("connessione rifiutata")
    fase15(monkeypatch, scarica=guasto)
    mese = {"m": dt.datetime(2026, 12, 5, 5, tzinfo=W.ROMA)}

    class Ora(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return mese["m"]
    monkeypatch.setattr(W.dt, "datetime", Ora)
    W.elettricita()
    W.elettricita()                       # stesso mese: non conta due volte
    assert email == []
    mese["m"] = dt.datetime(2027, 1, 5, 5, tzinfo=W.ROMA)
    W.elettricita()
    W.elettricita()
    assert len(email) == 1 and "due mesi" in email[0][0]


def test_carichi_assente_o_non_pronto_o_pubblicato(cartelle, email, monkeypatch):
    fase15(monkeypatch)
    assert W.carichi() == {"saltato": "costruisci_carichi assente"}

    def non_pronto(archivio, uscita):
        raise NotImplementedError
    fase15(monkeypatch, carichi=non_pronto)
    assert W.carichi()["saltato"] == "costruisci_carichi non pronto"
    visti = []

    def pronto(archivio, uscita):
        visti.append(archivio)
        scrivi(uscita, ["indice.json", "2026.json"])
        return {"file": 2}
    fase15(monkeypatch, carichi=pronto)
    assert W.carichi() == {"file": 2} and (C.SITO_DATI / "carichi" / "2026.json").exists()
    assert visti == [C.TERNA_DATI / "serie"] and email == []


def test_terna_api_rifa_i_carichi_dopo_un_aggiornamento(cartelle, monkeypatch):
    chiamati = []
    monkeypatch.setattr(T, "aggiorna", lambda: {"righe": {"carico_totale": 8}, "rimandato": False})
    monkeypatch.setattr(W, "carichi", lambda: chiamati.append(1) or {"file": 1})
    assert W.terna_api()["carichi"] == {"file": 1} and chiamati == [1]
    monkeypatch.setattr(T, "aggiorna", lambda: {"righe": {}, "rimandato": True})
    assert "carichi" not in W.terna_api() and chiamati == [1]


def test_lavori_di_terna_nel_ciclo_e_nei_comandi():
    import inspect
    s = inspect.getsource(W.ciclo)
    assert 'fatti.get("terna_api") != oggi' in s and "C.TERNA_RIPROVA_MIN" in s and "C.TERNA_RIPROVA_MAX" in s
    assert 'fatti.get("elettricita") != oggi' in s and "_archivio_elettricita_vuoto()" in s
    testa = W.__doc__
    assert "terna-api|elettricita|carichi" in testa
    sorgente = inspect.getsource(W)
    assert '"terna-api": terna_api' in sorgente and '"elettricita": elettricita' in sorgente and '"carichi": carichi' in sorgente


def test_nessun_catalogo_di_mercato_o_di_prezzo():
    """Prezzi, corrispettivi e MSD di Terna sono solo per uso interno: il worker non li scarica."""
    import inspect
    testo = inspect.getsource(T)
    for vietato in ("market/v", "fees/v", "/prices", "msd"):
        assert vietato not in testo.lower()
    assert all(S["api"].split("/")[0] in ("load", "generation") for S in T.SERIE.values())


def test_un_aggiornamento_alla_volta(cartelle):
    import fcntl
    C.TERNA_DATI.mkdir(parents=True)
    with open(C.TERNA_DATI / ".aggiorna.lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        dc = DCFinto()
        assert T.aggiorna(oggi=dt.date(2021, 6, 10), dc=dc)["saltato"] == "aggiornamento già in corso"
        assert dc.chiamate == []


def test_imcei_salta_i_mesi_vecchi_senza_dati(cartelle, monkeypatch):
    """Un mese vecchio vuoto non blocca il recupero; il primo mese recente vuoto lo ferma («non ancora pubblicato»)."""
    monkeypatch.setattr(C, "TERNA_STORICO_MESI", 0)
    T.stato_scrivi({"api_giorno": "2026-11-19", "imcei": "2026-03", "dc": {s: "2026-11" for s in T.SERIE}})
    cli, chiamate = api_finta(C.TERNA_DATI)
    vero = cli.get

    def get(percorso, params):
        if percorso.startswith("load/v2.0/monthly") and params["month"] == 4:
            return {"monthly_index_industrial_electrical_consumption": []}
        return vero(percorso, params)
    monkeypatch.setattr(cli, "get", get)
    T.aggiorna(oggi=dt.date(2026, 11, 20), api=cli, dc=DCFinto())
    assert T.stato_leggi()["imcei"] == "2026-10"
    assert not (C.TERNA_DATI / "serie" / "imcei" / "2026-04.parquet").exists()
    assert (C.TERNA_DATI / "serie" / "imcei" / "2026-09.parquet").exists()
