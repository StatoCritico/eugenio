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

Limiti (GetMyQuotas, 28/10/2026): 5 connessioni contemporanee, 10 al minuto, 100 all'ora, 2,25 MB di dati al minuto,
350 MB all'ora. Ogni chiamata è una connessione (anche Auth, GetMyQuotas e le risposte 429): il client le conta
in locale e aspetta prima di superare i limiti (vedi ClientGME).
"""
from __future__ import annotations

import base64
import datetime as dt
import io
import json
import logging
import time
import zipfile
from collections import deque
from zoneinfo import ZoneInfo

import httpx
import pandas as pd

log = logging.getLogger(__name__)
URL = "https://api.mercatoelettrico.org/request/api/v1"
ROMA = ZoneInfo("Europe/Rome")
FONTE = "Fonte: Gestore dei Mercati Energetici S.p.A."


class ErroreGME(RuntimeError):
    pass


# Limiti letti dal vivo con GetMyQuotas il 28/10/2026 (la guida tecnica non li pubblica). Il client li rilegge
# all'avvio e usa questi solo se la lettura fallisce. Ogni chiamata conta come connessione: Auth, GetMyQuotas e
# RequestData, comprese quelle respinte con 429.
LIMITI_PREDEFINITI = {"minuto": 10, "ora": 100, "dati_minuto": 2_250_000, "dati_ora": 350_000_000}
MARGINE_CONNESSIONI = (2, 10)      # connessioni lasciate libere: al minuto, all'ora (8/min e 90/ora con i limiti di oggi)
MARGINE_DATI = 0.9                 # frazione della quota di dati usata

# sostituibili nei test
_adesso = time.time
_dormi = time.sleep


class ClientGME:
    """Client dell'API GME con un limitatore delle chiamate.

    Il GME conta una finestra oraria che parte dalla prima connessione (`lastModifiedHour` di GetMyQuotas): oltre le
    100 connessioni risponde 429 finché la finestra non scade, e ogni nuovo tentativo conta anch'esso. Per questo il
    client tiene in locale l'istante di ogni chiamata e aspetta *prima* di superare il limite, invece di riprovare dopo
    il 429. Le quote si leggono una sola volta, all'avvio, e servono anche a sapere quante connessioni sono già state
    usate nella finestra in corso (per esempio da un'esecuzione precedente).
    """

    def __init__(self, utente: str, password: str, timeout: float = 120, transport: httpx.BaseTransport | None = None):
        if not utente or not password:
            raise ErroreGME("Credenziali GME mancanti (GME_UTENTE / GME_PASSWORD o password_file)")
        self.utente, self._pw = utente, password
        self.http = httpx.Client(timeout=timeout, headers={"User-Agent": "progetto-energia/1.0"}, transport=transport)
        self.token: str | None = None
        self.limiti = dict(LIMITI_PREDEFINITI)
        self._conn: deque[float] = deque()              # istanti delle connessioni dell'ultima ora
        self._dati: deque[tuple[float, int]] = deque()  # (istante, byte ricevuti) dell'ultima ora
        self._quote_lette = False

    # ------------------------------------------------------------------ limitatore
    def _max_minuto(self) -> int:
        return max(1, int(self.limiti["minuto"]) - MARGINE_CONNESSIONI[0])

    def _max_ora(self) -> int:
        return max(1, int(self.limiti["ora"]) - MARGINE_CONNESSIONI[1])

    def _pulisci(self, ora: float) -> None:
        while self._conn and self._conn[0] <= ora - 3600:
            self._conn.popleft()
        while self._dati and self._dati[0][0] <= ora - 3600:
            self._dati.popleft()

    def _attesa_necessaria(self, ora: float) -> tuple[float, str]:
        """Secondi da aspettare prima della prossima connessione (0 = si può chiamare subito)."""
        self._pulisci(ora)
        if len(self._conn) >= self._max_ora():
            return self._conn[len(self._conn) - self._max_ora()] + 3600 - ora + 1, "connessioni all'ora"
        ultimo_minuto = [t for t in self._conn if t > ora - 60]
        if len(ultimo_minuto) >= self._max_minuto():
            return ultimo_minuto[len(ultimo_minuto) - self._max_minuto()] + 60 - ora + 1, "connessioni al minuto"
        dati_ora = sum(n for _, n in self._dati)
        if dati_ora >= MARGINE_DATI * self.limiti["dati_ora"]:
            return self._dati[0][0] + 3600 - ora + 1, "dati all'ora"
        dati_min = [(t, n) for t, n in self._dati if t > ora - 60]
        if sum(n for _, n in dati_min) >= MARGINE_DATI * self.limiti["dati_minuto"]:
            return dati_min[0][0] + 60 - ora + 1, "dati al minuto"
        return 0.0, ""

    def _turno(self) -> None:
        """Aspetta finché una nuova connessione resta nei limiti, poi la registra."""
        while True:
            ora = _adesso()
            attesa, motivo = self._attesa_necessaria(ora)
            if attesa <= 0:
                self._conn.append(ora)
                return
            livello = logging.INFO if attesa > 120 else logging.DEBUG
            log.log(livello, "GME: limite di %s raggiunto in locale, attendo %d s", motivo, attesa)
            _dormi(attesa)

    def _chiama(self, metodo: str, url: str, **kw) -> httpx.Response:
        self._turno()
        r = self.http.request(metodo, url, **kw)
        self._dati.append((_adesso(), len(r.content)))
        return r

    # ------------------------------------------------------------------ base
    def _auth(self) -> None:
        r = self._chiama("POST", f"{URL}/Auth", json={"Login": self.utente, "Password": self._pw})
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
        """Quote dell'API (una connessione). Aggiorna i limiti e il conto delle connessioni già usate."""
        r = self._chiama("GET", f"{URL}/GetMyQuotas", headers=self._intestazioni())
        if r.status_code == 401:
            self.token = None
            r = self._chiama("GET", f"{URL}/GetMyQuotas", headers=self._intestazioni())
        if r.status_code != 200:
            raise ErroreGME(f"GME GetMyQuotas: risposta {r.status_code} {r.text[:200]}")
        d = _json_ci(r)
        self._quote_lette = True
        self._usa_quote(d)
        return d

    def _usa_quote(self, d: dict) -> None:
        lim = {k.lower(): v for k, v in (d.get("limits") or {}).items()}
        for chiave, nome in (("minuto", "maxconnectionsperminute"), ("ora", "maxconnectionsperhour"),
                             ("dati_minuto", "maxdataperminute"), ("dati_ora", "maxdataperhour")):
            if lim.get(nome):
                self.limiti[chiave] = int(lim[nome])
        # connessioni già usate nella finestra oraria del GME, oltre a quelle contate qui
        usate = int(d.get("connectionsperhour") or 0) - len(self._conn)
        if usate <= 0:
            return
        ora = _adesso()
        inizio = _istante_roma(d.get("lastmodifiedhour"))
        if inizio is None or inizio > ora:
            inizio = ora                        # non si sa quando scade la finestra: la si considera appena iniziata
        if inizio <= ora - 3600:
            return                              # finestra già scaduta: il contatore del GME si azzera alla prossima chiamata
        self._conn.extendleft([inizio] * usate)
        self._conn = deque(sorted(self._conn))
        log.info("GME: %d connessioni già usate nella finestra oraria iniziata alle %s",
                 int(d.get("connectionsperhour") or 0), dt.datetime.fromtimestamp(inizio, ROMA).strftime("%H:%M"))

    def _assicura_quote(self) -> None:
        if self._quote_lette:
            return
        self._quote_lette = True
        self._intestazioni()                # credenziali sbagliate o scadute: errore subito, con il suo messaggio
        try:
            self.quote()
        except Exception as e:  # senza quote si usano i limiti predefiniti
            log.warning("GME: quote non lette (%s), uso i limiti predefiniti %s", e, self.limiti)

    @staticmethod
    def _attesa_dopo_429(r: httpx.Response, volte: int) -> float:
        """Il primo 429 può essere il limite al minuto (65 s); se si ripete è quello orario: si riprova ogni 15 minuti,
        perché ogni tentativo conta come connessione e non ha senso consumarne altre a vuoto."""
        try:
            return float(r.headers["Retry-After"]) + 1
        except (KeyError, ValueError):
            return 65 if volte == 1 else 900

    def richiesta(self, segmento: str, nome: str, dal: dt.date, al: dt.date, attributi: dict | None = None,
                  piattaforma: str = "PublicMarketResults", dati_stimati: int = 0) -> list[dict]:
        """`dati_stimati` non serve più (il limitatore conta i byte ricevuti): resta per compatibilità."""
        corpo = {"Platform": piattaforma, "Segment": segmento, "DataName": nome,
                 "IntervalStart": int(dal.strftime("%Y%m%d")), "IntervalEnd": int(al.strftime("%Y%m%d")),
                 "Attributes": attributi or {}}
        self._assicura_quote()
        respinte = 0
        for tentativo in range(6):
            try:
                r = self._chiama("POST", f"{URL}/RequestData", json=corpo, headers=self._intestazioni())
            except httpx.HTTPError as e:
                log.warning("GME: errore di rete (%s), riprovo", e)
                _dormi(30 * (tentativo + 1))
                continue
            if r.status_code == 401:
                self.token = None
                continue
            if r.status_code == 429:
                respinte += 1
                attesa = self._attesa_dopo_429(r, respinte)
                log.warning("GME: limite di richieste superato (429, %d° volta), attendo %d s", respinte, attesa)
                _dormi(attesa)
                continue
            if r.status_code >= 500:
                _dormi(30 * (tentativo + 1))
                continue
            d = _json_ci(r)
            contenuto = d.get("contentresponse")
            if not contenuto:
                motivo = d.get("resultrequest") or r.text[:300]
                if "quot" in str(motivo).lower() or "limit" in str(motivo).lower():
                    log.warning("GME: %s – attendo 15 minuti", motivo)
                    _dormi(900)
                    continue
                if "nessun" in str(motivo).lower() or "no data" in str(motivo).lower():
                    return []
                raise ErroreGME(f"GME {nome} {segmento} {dal}–{al}: {motivo}")
            return _decodifica(contenuto)
        raise ErroreGME(f"GME {nome}: troppi tentativi falliti")


def _istante_roma(testo) -> float | None:
    """'2026-10-28T19:44:13.08' (ora italiana, senza fuso) → istante Unix."""
    if not testo:
        return None
    try:
        t = dt.datetime.fromisoformat(str(testo))
    except ValueError:
        return None
    return (t if t.tzinfo else t.replace(tzinfo=ROMA)).timestamp()


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
