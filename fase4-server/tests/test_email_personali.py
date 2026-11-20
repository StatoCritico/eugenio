"""Servizi email personali (14/11/2026): pagina «Dati per email», gettoni firmati, mensile per regione, previsioni
settimanali, avvisi meteo (non allerte), invio con l'API transazionale di listmonk e registro contro i doppioni."""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from servizio import config as C, listmonk as L, meteo_email as ME, notiziario as N   # noqa: E402
from servizio import preferenze_email as PE, protezione as P                         # noqa: E402


@pytest.fixture
def comuni(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "DATI", tmp_path)
    monkeypatch.setattr(C, "SITO_DATI", tmp_path / "sito")
    monkeypatch.setattr(C, "NOTIZIE_CHIAVE", "chiave-di-prova")
    monkeypatch.setattr(C, "NOTIZIE_PAUSA_S", 0)
    df = pd.DataFrame([
        {"istat": "037006", "nome": "Bologna", "provincia": "BO", "regione_cod": "08", "regione": "Emilia-Romagna",
         "capoluogo": True, "lat": 44.49, "lon": 11.34},
        {"istat": "040007", "nome": "Cesena", "provincia": "FC", "regione_cod": "08", "regione": "Emilia-Romagna",
         "capoluogo": False, "lat": 44.14, "lon": 12.24},
        {"istat": "040012", "nome": "Forlì", "provincia": "FC", "regione_cod": "08", "regione": "Emilia-Romagna",
         "capoluogo": True, "lat": 44.22, "lon": 12.04},
        {"istat": "015146", "nome": "Milano", "provincia": "MI", "regione_cod": "03", "regione": "Lombardia",
         "capoluogo": True, "lat": 45.46, "lon": 9.19},
        {"istat": "015002", "nome": "Abbiategrasso", "provincia": "MI", "regione_cod": "03", "regione": "Lombardia",
         "capoluogo": False, "lat": 45.4, "lon": 8.92},
        {"istat": "021008", "nome": "Bolzano", "provincia": "BZ", "regione_cod": "04",
         "regione": "Trentino-Alto Adige/Südtirol", "capoluogo": True, "lat": 46.5, "lon": 11.35}])
    df.to_parquet(tmp_path / "comuni.parquet", index=False)
    PE._comuni.cache_clear()
    return df


# ---------------------------------------------------------------------------------------------- gettoni
def test_gettoni_firmati(comuni):
    g = PE.gettone("pref", "Mario.Rossi@Esempio.it", 7)
    assert PE.leggi_gettone(g, "pref") == {"email": "mario.rossi@esempio.it"}
    assert "@" not in g                                           # l'indirizzo non è in chiaro
    v = PE.gettone("via", 42, 400, 5)
    assert PE.leggi_gettone(v, "via") == {"id": 42, "lista": 5}
    for cattivo in (g[:-1] + ("0" if g[-1] != "0" else "1"), g.replace("pref", "via"), "", "v1.pref.1.e.x"):
        with pytest.raises(HTTPException) as e:
            PE.leggi_gettone(cattivo, "pref" if "via" not in cattivo else "via")
        assert e.value.status_code == 401
    vecchio = PE.gettone("pref", 7, 1, ora=0)
    with pytest.raises(HTTPException, match="scaduto"):
        PE.leggi_gettone(vecchio, "pref")


def test_senza_chiave_niente_gettoni(comuni, monkeypatch):
    monkeypatch.setattr(C, "NOTIZIE_CHIAVE", "")
    monkeypatch.setattr(C, "SESSIONE_CHIAVE", "")
    with pytest.raises(HTTPException) as e:
        PE.gettone("pref", 1, 1)
    assert e.value.status_code == 503


def test_scelte_controllate(comuni):
    sc = PE._pulisci_scelte({"mensile": True, "regioni": ["8", "03"], "settimanale": True,
                             "comuni": ["40007", "015146"], "avvisi": ["neve", "pioggia", "grandine"]})
    assert sc == {"servizi": {"mensile": True, "settimanale": True, "avvisi": True}, "regioni": ["08", "03"],
                  "comuni": ["040007", "015146"], "avvisi": ["pioggia", "neve"]}
    for dati in ({"regioni": ["01", "03", "04", "08"]}, {"regioni": ["99"]},
                 {"comuni": ["037006", "040007", "040012", "015146", "015002", "021008"]},
                 {"settimanale": True, "comuni": []}, {"avvisi": ["vento"]}, {"comuni": ["999999"]}):
        with pytest.raises(HTTPException) as e:
            PE._pulisci_scelte(dati)
        assert e.value.status_code == 422
    assert [r["nome"] for r in PE.regioni()] == ["Lombardia", "Trentino-Alto Adige", "Emilia-Romagna"]


# ---------------------------------------------------------------------------------------------- previsioni e soglie
def test_giornalieri_e_soglie():
    ore = pd.date_range("2026-11-15 23:00", periods=48, freq="h", tz="UTC")     # 16 e 17 novembre, ora italiana
    o = pd.DataFrame({"time": ore, "temperature_2m": 2.0, "precipitation": 0.5, "snowfall": 0.0,
                      "wind_gusts_10m": 30.0})
    o.loc[5, "precipitation"] = 16.0                                # 16/11: 16 mm in un'ora
    o.loc[30:33, "snowfall"] = 1.0                                  # 17/11: 4 cm
    o.loc[40, "wind_gusts_10m"] = 80.0                              # 17/11: raffica 80 km/h
    g = ME.giornalieri(o)
    assert list(g.data) == [dt.date(2026, 11, 16), dt.date(2026, 11, 17)]
    assert g.gg20.round(1).tolist() == [18.0, 18.0]
    d16, d17 = ME.giorno(g, dt.date(2026, 11, 16)), ME.giorno(g, dt.date(2026, 11, 17))
    assert ME.superamenti(d16) == ["pioggia"]                       # 27,5 mm in 24 ore ma 16 in un'ora
    assert ME.superamenti(d17) == ["neve", "vento"]
    assert ME.superamenti({"pioggia": 40.0, "pioggia_1h": 3, "neve": float("nan"), "raffica": 74.9}) == ["pioggia"]


def test_avviso_non_e_un_allerta(comuni):
    c = {"istat": "040007", "nome": "Cesena", "provincia": "FC"}
    g = {"pioggia": 52.4, "pioggia_1h": 18.2, "neve": 0, "raffica": 40}
    assert N.testo_avviso(dt.date(2026, 11, 16), [(c, [], g)]) is None
    oggetto, testo = N.testo_avviso(dt.date(2026, 11, 16), [(c, ["pioggia"], g)])
    assert oggetto == "EuGEnio – avviso meteo per domani: pioggia forte a Cesena"
    assert "lunedì 16 novembre" in testo
    assert ("**Non è un'allerta.** Il servizio di avvisi meteo è gratuito, non fornisce garanzie e non sostituisce le "
            "allerte della Protezione Civile e degli enti pubblici.") in testo
    assert "- **Cesena (FC)**: pioggia forte, 52 mm nelle 24 ore (al massimo 18 mm in un'ora)." in testo
    assert N.BOLLETTINO_PC in testo and "IT-alert" in testo


def test_settimanale(comuni, monkeypatch):
    lun = dt.date(2026, 11, 16)
    giorni = [lun + dt.timedelta(days=i) for i in range(7)]
    prev = {"040007": pd.DataFrame({"data": giorni, "tmin": 1.0, "tmax": 9.0, "tmedia": 5.0, "pioggia": 2.0,
                                    "pioggia_1h": 1.0, "neve": 0.0, "raffica": [20.0] * 6 + [90.0], "gg20": 15.0})}
    monkeypatch.setattr(N, "_gg_stessi_giorni", lambda istat, g: (100.0, 2015, 2025))
    oggetto, testo = N.testo_settimanale(lun, [{"istat": "040007", "nome": "Cesena", "provincia": "FC"},
                                               {"istat": "037006", "nome": "Bologna", "provincia": "BO"}], prev)
    assert oggetto == "EuGEnio – previsioni dal 16 al 22 novembre: Cesena, Bologna"
    assert "## Cesena (FC)" in testo and "## Bologna" not in testo          # Bologna senza previsioni: saltata
    assert "| lun 16 | 1 °C | 9 °C | 2 mm | 0 cm | 20 km/h | 15,0 |  |" in testo
    assert "| dom 22 | 1 °C | 9 °C | 2 mm | 0 cm | 90 km/h | 15,0 | vento molto forte |" in testo
    assert "Gradi giorno previsti nella settimana: **105**; negli stessi giorni del 2015–2025 in media 100 (+5 %)." in testo
    assert "non sostituiscono le allerte" in testo
    assert N.testo_settimanale(lun, [{"istat": "037006", "nome": "Bologna", "provincia": "BO"}], prev) is None


# ---------------------------------------------------------------------------------------------- mensile per regione
def _giornaliero(cartella: Path, t: dict[str, dict[int, float]]) -> None:
    righe = []
    for istat, anni in t.items():
        for anno, x in anni.items():
            for d in pd.date_range(f"{anno}-10-01", f"{anno}-10-31"):
                righe.append({"istat": istat, "data": d, "gg20": max(0.0, 20 - x), "t_media": x})
    pd.DataFrame(righe).to_parquet(cartella / "giornaliero.parquet", index=False)


def test_mensile_per_regione(comuni, tmp_path):
    from test_notiziario_freddo import _indici
    _indici(tmp_path / "sito")
    _giornaliero(tmp_path, {"037006": {2025: 14, 2026: 16}, "040012": {2025: 15, 2026: 16},
                            "040007": {2025: 15, 2026: 16}, "015146": {2025: 13, 2026: 12}})
    cap = N._capoluoghi_italia()
    assert set(cap.nome) == {"Bologna", "Cesena", "Forlì", "Milano", "Bolzano"}     # Cesena secondo capoluogo
    voci = N._voci_freddo(cap, 2026, 10)
    nomi = N._nomi_regioni(cap)
    assert nomi["04"] == "Trentino-Alto Adige"
    oggetto, testo = N.testo_mensile_regioni(2026, 10, dt.date(2026, 12, 12), ["08"], voci, nomi)
    assert oggetto == "EuGEnio – prezzi e freddo di ottobre 2026 (Emilia-Romagna)"
    assert "## Il freddo di ottobre 2026, regione per regione" in testo
    assert "| Emilia-Romagna | 16,0 °C | +1,3 °C | 124 | −24 % |" in testo
    assert "| Lombardia | 12,0 °C | −1,0 °C | 248 | +14 % |" in testo
    assert "## Emilia-Romagna: i capoluoghi" in testo and "## Lombardia: i capoluoghi" not in testo
    assert testo.count("Il tuo comune non c'è?") == 1
    assert "Consip – Lotto 6: Emilia Romagna" in testo
    assert testo.index("## Indici dei prezzi") < testo.index("regione per regione")
    # nessuna regione scelta: tabella delle regioni e l'invito a sceglierle
    _, senza = N.testo_mensile_regioni(2026, 10, dt.date(2026, 12, 12), [], voci, nomi)
    assert ": i capoluoghi" not in senza and "Scegli fino a 3 regioni" in senza


def test_lotti_consip_per_regione():
    ind = {"lotto_predefinito": "6", "lotti": {"1": {"nome": "Lotto 1: Valle d'Aosta e Piemonte"},
                                               "3": {"nome": "Lotto 3: Trentino Alto Adige, Friuli Venezia Giulia"},
                                               "6": {"nome": "Lotto 6: Emilia Romagna"}}}
    assert N._lotti_regioni(ind, ["Valle d'Aosta", "Friuli-Venezia Giulia"]) == ["1", "3"]
    assert N._lotti_regioni(ind, ["Trentino-Alto Adige"]) == ["3"]
    assert N._lotti_regioni(ind, []) == ["6"] and N._lotti_regioni(ind, ["Sicilia"]) == ["6"]


# ---------------------------------------------------------------------------------------------- invio
def test_invio_personale_e_registro(comuni, monkeypatch):
    spediti = []
    monkeypatch.setattr(L, "modello_tx", lambda: 9)
    monkeypatch.setattr(L, "destinatari", lambda lista: [{"id": 1}, {"id": 2}, {"id": 3}])
    monkeypatch.setattr(L, "messaggio", lambda sid, m, o, h, via=None: spediti.append((sid, m, o, h, via)))

    def costruisci(s):
        if s["id"] == 2:
            return None
        if s["id"] == 3:
            raise RuntimeError("guasto")
        return "Oggetto", "# Titolo\n\n| A | B |\n|---|---:|\n| x | 1 |"
    errori = []
    monkeypatch.setattr(N.avvisi, "invia", lambda o, t, *a: errori.append(o))
    e = N.invia_personali("avvisi-2026-11-16", "avvisi", 7, costruisci)
    assert e["inviati"] == 1 and e["saltati"] == 1 and len(e["errori"]) == 1 and errori
    sid, modello, oggetto, html, via = spediti[0]
    assert (sid, modello, oggetto) == (1, 9, "Oggetto")
    assert "<table>" in html and "<h1>Titolo</h1>" in html
    assert "dati-per-email.html#t=" in html and "dati-per-email.html#via=" in html and "gli avvisi meteo" in html
    assert via.startswith(C.SITO_URL + "/api/email/via?t=v1.via.")
    # seconda esecuzione: il registro evita il doppione all'iscritto 1
    spediti.clear()
    N.invia_personali("avvisi-2026-11-16", "avvisi", 7, costruisci)
    assert [s[0] for s in spediti] == []


def test_mensile_personale_o_campagna(monkeypatch):
    chiamate = []
    monkeypatch.setattr(N, "mensile_personale", lambda a, m, i: chiamate.append(("personale", a, m)))
    monkeypatch.setattr(N, "_campagna", lambda *a: chiamate.append(("campagna",)))
    monkeypatch.setattr(N, "testo_mensile", lambda *a: ("o", "t"))
    monkeypatch.setattr(C, "LISTMONK_API_UTENTE", "u")
    monkeypatch.setattr(C, "LISTMONK_API_TOKEN", "t")
    N.mensile(invio=dt.date(2026, 12, 12))
    monkeypatch.setattr(C, "NOTIZIE_PERSONALI", False)
    N.mensile(invio=dt.date(2026, 12, 12))
    assert chiamate == [("personale", 2026, 11), ("campagna",)]


def test_salva_in_listmonk(monkeypatch):
    chiamate = []
    monkeypatch.setattr(C, "LISTMONK_API_UTENTE", "u")
    monkeypatch.setattr(C, "LISTMONK_API_TOKEN", "t")
    esistente = {"id": 5, "email": "a@b.it", "name": "A", "status": "enabled", "attribs": {"citta": "Cesena"},
                 "lists": [{"id": 3, "subscription_status": "confirmed"}, {"id": 8, "subscription_status": "confirmed"}]}
    monkeypatch.setattr(L, "iscritto", lambda e: esistente)
    monkeypatch.setattr(L, "_invia", lambda m, p, d: chiamate.append((m, p, d)) or {})
    L.salva("A@B.it", "", {7}, {8}, {"comuni": ["040007"]})
    (m1, p1, d1), (m2, p2, d2) = chiamate
    assert (m1, p1) == ("PUT", "subscribers/5") and d1["lists"] == [3, 7] and d1["preconfirm_subscriptions"]
    assert d1["attribs"] == {"citta": "Cesena", "eugenio": {"comuni": ["040007"]}}
    assert (m2, p2, d2) == ("PUT", "subscribers/lists", {"ids": [5], "action": "unsubscribe", "target_list_ids": [8]})
    assert L.iscritto.__name__ == "<lambda>"
    # indirizzo con un apice: mai nella condizione SQL
    monkeypatch.undo()
    monkeypatch.setattr(C, "LISTMONK_API_UTENTE", "u")
    monkeypatch.setattr(C, "LISTMONK_API_TOKEN", "t")
    monkeypatch.setattr(L, "_get", lambda *a, **k: pytest.fail("non deve chiamare listmonk"))
    assert L.iscritto("x'or 1=1@b.it") is None


# ---------------------------------------------------------------------------------------------- rotte
@pytest.fixture
def api(comuni, monkeypatch):
    from servizio import app as A
    monkeypatch.setattr(C, "LISTMONK_API_UTENTE", "u")
    monkeypatch.setattr(C, "LISTMONK_API_TOKEN", "t")
    monkeypatch.setattr(C, "TURNSTILE_SITEKEY", "")
    monkeypatch.setattr(P, "limiti", P.Limitatore())
    return TestClient(A.app)


def test_rotte(api, monkeypatch):
    o = api.get("/api/email/opzioni").json()
    assert o["attivo"] and o["max_comuni"] == 5 and o["max_regioni"] == 3
    assert [a["id"] for a in o["avvisi"]] == ["pioggia", "neve", "vento"]
    assert "non sostituisce le allerte" in o["avvertenza"] and "75 km/h" in o["avvisi"][2]["soglia"]
    assert len(api.get("/api/email/comuni").json()) == 6
    # collegamento: spedito, risposta uguale per tutti, al massimo EMAIL_LINK_GIORNO al giorno allo stesso indirizzo
    email = []
    monkeypatch.setattr(L, "iscritto", lambda e: {"id": 41})
    monkeypatch.setattr(PE.avvisi, "invia_a", lambda dest, ogg, testo, html, **k: email.append((dest, testo, k)) or True)
    for _ in range(4):
        assert api.post("/api/email/link", json={"email": "Mario@Esempio.it"}).json() == {"inviato": True}
    assert len(email) == 3 and email[0][0] == "mario@esempio.it"
    # (20/11/2026) nostra intestazione «Annulla iscrizione» (via-tutto con il numero dell'iscritto, mai l'indirizzo)
    k = email[0][2]
    assert k["solleva_bloccato"] is True and "/api/email/via-tutto?t=v1.tutto." in k["cancella"]
    assert PE.leggi_gettone(k["cancella"].split("t=")[1], "tutto")["id"] == 41 and "esempio" not in k["cancella"]
    assert api.post("/api/email/link", json={"email": "non-valido"}).status_code == 422
    t = email[0][1].split("#t=")[1].split()[0]
    # lettura: nuovo iscritto, niente scelto
    monkeypatch.setattr(L, "iscritto", lambda e: None)
    monkeypatch.setattr(L, "liste_servizi", lambda crea=True: {"mensile": 3, "settimanale": 7, "avvisi": 8})
    r = api.post("/api/email/leggi", json={"t": t}).json()
    assert r == {"email": "mario@esempio.it", "mensile": False, "settimanale": False, "avvisi": [], "regioni": [],
                 "comuni": []}
    # salvataggio
    salvati = []
    monkeypatch.setattr(L, "salva", lambda *a: salvati.append(a) or {})
    r = api.post("/api/email/salva", json={"t": t, "mensile": True, "regioni": ["08"], "settimanale": False,
                                           "comuni": ["040007"], "avvisi": ["vento"]})
    assert r.status_code == 200, r.text
    assert r.json()["avvisi"] == ["vento"] and r.json()["comuni"][0]["nome"] == "Cesena"
    email_s, nome, attive, spente, attr = salvati[0]
    assert email_s == "mario@esempio.it" and attive == {3, 8} and spente == {7}
    assert attr["regioni"] == ["08"] and attr["comuni"] == ["040007"] and attr["avvisi"] == ["vento"]
    assert api.post("/api/email/salva", json={"t": "v1.pref.9999999999.i1.x"}).status_code == 401
    # cancellazione con un clic (programma di posta: corpo «List-Unsubscribe=One-Click») e dalla pagina (JSON)
    tolti = []
    monkeypatch.setattr(L, "cancella", lambda sid, liste: tolti.append((sid, liste)))
    v = PE.gettone("via", 12, 400, 8)
    r = api.post(f"/api/email/via?t={v}", content="List-Unsubscribe=One-Click",
                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert r.status_code == 200 and r.json()["cancellato"] == "avvisi"
    assert api.post("/api/email/via", json={"t": v}).json()["preferenze"].startswith("t=v1.pref.")
    assert tolti == [(12, {8}), (12, {8})]
    assert api.post("/api/email/via", json={"t": PE.gettone("via", 12, 400, 99)}).status_code == 404


def test_rotte_spente_senza_configurazione(api, monkeypatch):
    monkeypatch.setattr(C, "LISTMONK_API_TOKEN", "")
    assert api.get("/api/email/opzioni").json()["attivo"] is False
    assert api.post("/api/email/link", json={"email": "a@b.it"}).status_code == 503


def test_intestazione_annulla_iscrizione_e_indirizzo_bloccato(monkeypatch):
    """20/11/2026: ogni email diretta porta la nostra List-Unsubscribe HTTPS (OCI non mette la sua, che sopprime
    l'indirizzo); un destinatario nella lista di soppressione di OCI viene riconosciuto."""
    import smtplib
    from servizio import avvisi as Av
    spedite, rifiuta = [], {"no": False}

    class SMTPFinto:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self): pass
        def login(self, u, p): pass
        def send_message(self, m):
            if rifiuta["no"]:
                raise smtplib.SMTPRecipientsRefused({m["To"]: (254, b"4.7.1 -  x@y.it is suppressed for sender ocid1.x")})
            spedite.append(m)

    monkeypatch.setattr(Av.smtplib, "SMTP", SMTPFinto)
    monkeypatch.setattr(C, "SMTP_SERVER", "smtp.prova")
    monkeypatch.setattr(C, "SMTP_MITTENTE", "eugenio@prova.it")
    monkeypatch.setattr(C, "EMAIL_AMMINISTRATORE", "admin@prova.it")
    monkeypatch.setattr(C, "SITO_URL", "https://eugenio.prova")
    assert Av.invia("errore", "testo")
    m = spedite[-1]
    assert m["List-Unsubscribe"] == "<https://eugenio.prova/api/email/servizio>"
    assert m["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert "Non usare «Annulla iscrizione»" in m.get_content()
    assert Av.invia_a("x@y.it", "o", "t", cancella="https://eugenio.prova/api/email/via-tutto?t=g")
    assert spedite[-1]["List-Unsubscribe"] == "<https://eugenio.prova/api/email/via-tutto?t=g>"
    rifiuta["no"] = True
    assert Av.invia_a("x@y.it", "o", "t") is False
    with pytest.raises(Av.IndirizzoBloccato):
        Av.invia_a("x@y.it", "o", "t", solleva_bloccato=True)


def test_rotte_indirizzo_bloccato_via_tutto_e_servizio(api, monkeypatch):
    from servizio import avvisi as Av
    amministratore = []
    monkeypatch.setattr(L, "iscritto", lambda e: None)

    def bloccato(*a, **k):
        raise Av.IndirizzoBloccato()
    monkeypatch.setattr(PE.avvisi, "invia_a", bloccato)
    monkeypatch.setattr(PE.avvisi, "invia", lambda o, t, *a: amministratore.append((o, t)) or True)
    r = api.post("/api/email/link", json={"email": "Bloccato@Esempio.it"})
    assert r.status_code == 409 and "bloccato dal servizio di posta" in r.json()["detail"]
    assert "contatti.html" in r.json()["detail"]
    assert amministratore and "bloccato@esempio.it" in amministratore[0][1] and "Suppression List" in amministratore[0][1]
    # «Annulla iscrizione» del programma di posta sul collegamento personale: fuori da tutti i servizi
    tolti = []
    monkeypatch.setattr(L, "liste_servizi", lambda crea=True: {"mensile": 3, "settimanale": 7, "avvisi": None})
    monkeypatch.setattr(L, "cancella", lambda sid, liste: tolti.append((sid, liste)))
    g = PE.gettone("tutto", 41, 400)
    r = api.post(f"/api/email/via-tutto?t={g}", content="List-Unsubscribe=One-Click",
                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert r.status_code == 200 and tolti == [(41, {3, 7})]
    assert api.post(f"/api/email/via-tutto?t={PE.gettone('via', 41, 400, 3)}").status_code == 401
    # email del servizio: risponde e non fa niente
    assert api.post("/api/email/servizio", content="List-Unsubscribe=One-Click").json() == {"cancellato": None}
