"""Client dell'API del GME (Gestore dei Mercati Energetici).

Credenziali personali e gratuite, da richiedere con il modulo su https://api.mercatoelettrico.org
(per un ente servono i documenti sui poteri di firma). Condizioni d'uso: licenza personale, non
commerciale, citando "Fonte: Gestore dei Mercati Energetici S.p.A."; la pubblicazione o
ridistribuzione dei dati richiede il permesso scritto del GME. La password scade ogni 6 mesi.

Documentazione: "Servizio API del GME – Guida tecnica" (15/10/2025).
  POST /api/v1/Auth          {"Login","Password"} → {"Success","token","Reason"}
  POST /api/v1/RequestData   {"Platform","Segment","DataName","IntervalStart","IntervalEnd","Attributes"}
                             → {"ContentResponse": base64(zip(json))}
  GET  /api/v1/GetMyQuotas
"""
from __future__ import annotations

import base64
import datetime as dt
import io
import json
import logging
import time
import zipfile
from zoneinfo import ZoneInfo

import httpx
import pandas as pd

log = logging.getLogger(__name__)
URL = "https://api.mercatoelettrico.org/request/api/v1"
ROMA = ZoneInfo("Europe/Rome")
FONTE = "Fonte: Gestore dei Mercati Energetici S.p.A."


class ErroreGME(RuntimeError):
    pass


class ClientGME:
    def __init__(self, utente: str, password: str, timeout: float = 120):
        if not utente or not password:
            raise ErroreGME("Credenziali GME mancanti (GME_UTENTE / GME_PASSWORD o password_file)")
        self.utente, self._pw = utente, password
        self.http = httpx.Client(timeout=timeout, headers={"User-Agent": "progetto-energia/1.0"})
        self.token: str | None = None

    # ------------------------------------------------------------------ base
    def _auth(self) -> None:
        r = self.http.post(f"{URL}/Auth", json={"Login": self.utente, "Password": self._pw})
        d = _json_ci(r)
        if r.status_code != 200 or not d.get("success"):
            motivo = d.get("reason") or r.text[:200]
            raise ErroreGME(f"Autenticazione GME fallita: {motivo}. La password scade ogni 6 mesi: "
                            "va rinnovata su https://api.mercatoelettrico.org/users/")
        self.token = d.get("token")

    def _intestazioni(self) -> dict:
        if not self.token:
            self._auth()
        return {"Authorization": f"Bearer {self.token}"}

    def quote(self) -> dict:
        r = self.http.get(f"{URL}/GetMyQuotas", headers=self._intestazioni())
        if r.status_code == 401:
            self.token = None
            r = self.http.get(f"{URL}/GetMyQuotas", headers=self._intestazioni())
        return _json_ci(r)

    def _attendi_quote(self, dati_stimati: int) -> None:
        """Se la richiesta farebbe superare la quota oraria di dati, aspetta l'ora successiva."""
        try:
            q = self.quote()
        except Exception:  # la verifica delle quote non deve bloccare il download
            return
        lim = {k.lower(): v for k, v in (q.get("limits") or {}).items()}
        usati_h = q.get("dataperhour") or 0
        max_h = lim.get("maxdataperhour")
        if max_h and usati_h + dati_stimati > max_h:
            ora = dt.datetime.now()
            attesa = 3600 - (ora.minute * 60 + ora.second) + 5
            log.info("Quota oraria GME quasi esaurita (%s/%s): attendo %d s", usati_h, max_h, attesa)
            time.sleep(attesa)

    def richiesta(self, segmento: str, nome: str, dal: dt.date, al: dt.date, attributi: dict | None = None,
                  piattaforma: str = "PublicMarketResults", dati_stimati: int = 0) -> list[dict]:
        corpo = {"Platform": piattaforma, "Segment": segmento, "DataName": nome,
                 "IntervalStart": int(dal.strftime("%Y%m%d")), "IntervalEnd": int(al.strftime("%Y%m%d")),
                 "Attributes": attributi or {}}
        for tentativo in range(6):
            if dati_stimati:
                self._attendi_quote(dati_stimati)
            try:
                r = self.http.post(f"{URL}/RequestData", json=corpo, headers=self._intestazioni())
            except httpx.HTTPError as e:
                log.warning("GME: errore di rete (%s), riprovo", e)
                time.sleep(30 * (tentativo + 1))
                continue
            if r.status_code == 401:
                self.token = None
                continue
            if r.status_code == 429:
                log.warning("GME: limite di richieste, attendo 65 s")
                time.sleep(65)
                continue
            if r.status_code >= 500:
                time.sleep(30 * (tentativo + 1))
                continue
            d = _json_ci(r)
            contenuto = d.get("contentresponse")
            if not contenuto:
                motivo = d.get("resultrequest") or r.text[:300]
                if "quot" in str(motivo).lower() or "limit" in str(motivo).lower():
                    log.warning("GME: %s – attendo l'ora successiva", motivo)
                    time.sleep(3600 - dt.datetime.now().minute * 60 + 5)
                    continue
                if "nessun" in str(motivo).lower() or "no data" in str(motivo).lower():
                    return []
                raise ErroreGME(f"GME {nome} {segmento} {dal}–{al}: {motivo}")
            return _decodifica(contenuto)
        raise ErroreGME(f"GME {nome}: troppi tentativi falliti")


def _json_ci(r: httpx.Response) -> dict:
    """JSON con chiavi in minuscolo (la documentazione alterna 'Success' e 'success')."""
    try:
        d = r.json()
    except ValueError:
        return {}
    return {k.lower(): v for k, v in d.items()} if isinstance(d, dict) else {"_lista": d}


def _decodifica(b64: str) -> list[dict]:
    z = zipfile.ZipFile(io.BytesIO(base64.b64decode(b64)))
    nome = next(n for n in z.namelist() if n.lower().endswith(".json"))
    d = json.loads(z.read(nome).decode("utf-8-sig"))
    if isinstance(d, dict):  # alcune risposte incapsulano la lista
        d = next((v for v in d.values() if isinstance(v, list)), [d])
    return d


# ---------------------------------------------------------------------------------------------- tempo
def inizio_intervallo(giorno: pd.Series, ora: pd.Series | None, periodo: pd.Series | None, minuti: int) -> pd.Series:
    """Istante UTC di inizio di ogni intervallo, contando gli intervalli dalla mezzanotte locale
    (gestisce le giornate di 23 e 25 ore del cambio d'ora)."""
    mezzanotte = pd.to_datetime(giorno.astype(str), format="%Y%m%d").dt.tz_localize(ROMA).dt.tz_convert("UTC")
    if periodo is not None and periodo.notna().any() and minuti < 60:
        n = pd.to_numeric(periodo, errors="coerce").fillna(1).astype(int) - 1
        return mezzanotte + pd.to_timedelta(n * minuti, unit="m")
    n = pd.to_numeric(ora, errors="coerce").fillna(1).astype(int) - 1
    return mezzanotte + pd.to_timedelta(n * 60, unit="m")


def _df(righe: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(righe)
    df.columns = [c[0].lower() + c[1:] if c else c for c in df.columns]
    return df


# ---------------------------------------------------------------------------------------------- dataset
def prezzi_mgp(cl: ClientGME, dal: dt.date, al: dt.date) -> pd.DataFrame:
    """Prezzi zonali MGP e PUN Index GME. Quartorari dal 1/10/2025 (PT15), orari prima (PT60)."""
    parti = []
    soglia = dt.date(2025, 10, 1)
    for a, b, gran, minuti in ((dal, min(al, soglia - dt.timedelta(days=1)), "PT60", 60),
                               (max(dal, soglia), al, "PT15", 15)):
        if a > b:
            continue
        attr = {"GranularityType": gran} if b >= soglia else {}
        righe = cl.richiesta("MGP", "ME_ZonalPrices", a, b, attr, dati_stimati=(b - a).days * 96 * 20 * 7)
        if not righe:
            continue
        df = _df(righe)
        df["inizio_utc"] = inizio_intervallo(df["flowDate"], df.get("hour"), df.get("period"), minuti)
        df["minuti"] = minuti
        parti.append(pd.DataFrame({
            "inizio_utc": df.inizio_utc, "data": pd.to_datetime(df.flowDate.astype(str), format="%Y%m%d").dt.date,
            "ora": pd.to_numeric(df.get("hour"), errors="coerce").astype("Int16"),
            "periodo": pd.to_numeric(df.get("period"), errors="coerce").astype("Int16"),
            "minuti": df.minuti.astype("int16"), "zona": df.zone.astype(str),
            "prezzo": pd.to_numeric(df.price, errors="coerce").astype("float32"),
            "note": df.get("notes", pd.Series([None] * len(df))).astype("string")}))
    return pd.concat(parti, ignore_index=True) if parti else pd.DataFrame()


def volumi_mgp(cl: ClientGME, dal: dt.date, al: dt.date) -> pd.DataFrame:
    righe = cl.richiesta("MGP", "ME_ZonalVolumes", dal, al, dati_stimati=(al - dal).days * 96 * 20 * 8)
    if not righe:
        return pd.DataFrame()
    df = _df(righe)
    minuti = 15 if dal >= dt.date(2025, 10, 1) else 60
    return pd.DataFrame({
        "inizio_utc": inizio_intervallo(df.flowDate, df.get("hour"), df.get("period"), minuti),
        "data": pd.to_datetime(df.flowDate.astype(str), format="%Y%m%d").dt.date,
        "zona": df.zone.astype(str), "minuti": minuti,
        "acquisti_mwh": pd.to_numeric(df.purchased, errors="coerce").astype("float32"),
        "vendite_mwh": pd.to_numeric(df.sold, errors="coerce").astype("float32")})


def mgp_gas(cl: ClientGME, dal: dt.date, al: dt.date, segmento: str = "MGP-GAS") -> pd.DataFrame:
    """Esiti dell'asta del mercato del giorno prima del gas (prezzo del gas al PSV, €/MWh)."""
    righe = cl.richiesta(segmento, "GAS_MGASAuctionResults", dal, al, dati_stimati=(al - dal).days * 8 + 8)
    if not righe:
        return pd.DataFrame()
    df = _df(righe)
    return pd.DataFrame({
        "data": pd.to_datetime(df.flowDate.astype(str), format="%Y%m%d").dt.date,
        "mercato": df.market.astype(str), "prodotto": df["product"].astype(str),
        "prezzo": pd.to_numeric(df.price, errors="coerce").astype("float32"),
        "volumi_mwh": pd.to_numeric(df.get("totalVolumesMWh"), errors="coerce").astype("float32")})


def igi(cl: ClientGME, dal: dt.date, al: dt.date) -> pd.DataFrame:
    """IGI – Italian Gas Index del GME (€/MWh)."""
    righe = cl.richiesta("IGI", "GAS_IGIndex", dal, al, dati_stimati=(al - dal).days * 3 + 3)
    if not righe:
        return pd.DataFrame()
    df = _df(righe)
    return pd.DataFrame({
        "data": pd.to_datetime(df.flowDate.astype(str), format="%Y%m%d").dt.date,
        "prodotto": df["product"].astype(str),
        "prezzo": pd.to_numeric(df.price, errors="coerce").astype("float32")})


def mgp_gas_continua(cl: ClientGME, dal: dt.date, al: dt.date) -> pd.DataFrame:
    """MGP-GAS in negoziazione continua: prezzo medio ponderato per prodotto e giorno gas (€/MWh, PSV)."""
    righe = cl.richiesta("MGP-GAS", "GAS_ContinuousTrading", dal, al, dati_stimati=(al - dal).days * 3 * 16 + 16)
    if not righe:
        return pd.DataFrame()
    df = _df(righe)
    num = lambda c: pd.to_numeric(df.get(c), errors="coerce").astype("float32")  # noqa: E731
    return pd.DataFrame({
        "data": pd.to_datetime(df.flowDate.astype(str), format="%Y%m%d").dt.date,
        "mercato": df.market.astype(str), "prodotto": df["product"].astype(str),
        "prezzo_medio": num("averagePrice"), "prezzo_min": num("minPrice"), "prezzo_max": num("maxPrice"),
        "volumi_mwh": num("mWhVolumes") if "mWhVolumes" in df else num("mwhVolumes")})
