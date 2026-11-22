"""Serie di Terna per «Carichi elettrici» e le analisi future (20/11/2026; lavoro `terna-api` del worker).

Due fonti, le stesse serie:
  - **Download Center** di dati.terna.it (POST JSON su /api/sitecore/dati/downloadcenter/recordsv2, nessuna chiave, non
    consuma la quota dell'API): lo **storico** dal TERNA_STORICO_INIZIO (2021-01), un mese per richiesta, qualche mese
    per giorno, ripreso da dove era rimasto (stato in TERNA_DATI/stato.json). Un mese entra appena è finito.
  - **API ufficiale** (https://developer.terna.it, OAuth2 client_credentials, chiavi solo nel .env): ogni giorno il
    **giorno prima** (e quelli rimasti indietro, al più TERNA_API_GIORNI_MAX) e una volta al mese l'**IMCEI**, che il
    Download Center non ha. Limiti di Terna: 1 richiesta al secondo, 300 al giorno; il contatore persistente
    (TERNA_DATI/quota_api.json, giorno italiano) si ferma a TERNA_API_TETTO (250) e conta anche le richieste del token.
Riserva reciproca: se un mese dello storico non arriva dal Download Center si prova l'API (se c'è quota); se l'API non
è configurata o non risponde, il mese in corso si legge dal Download Center.

Archivio (formato documentato nel README della fase 4, § «Dati di Terna»): un file Parquet per serie e mese (mese
italiano dell'istante) in TERNA_DATI/serie/<serie>/<AAAA-MM>.parquet, colonne normalizzate, deduplicato sulla chiave
(istante + zona o fonte; per l'IMCEI mese + regione + settore + tensione), vince l'ultima riga scritta.

Mai nel repository, mai scaricabile dal sito (decisione di Paolo del 20/11/2026). Niente dati di prezzo o di mercato di
Terna: i cataloghi Market e Fees non si toccano. Le chiavi e il token non vanno mai nel registro.
"""
from __future__ import annotations

import calendar
import datetime as dt
import json
import logging
import re
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

from . import config as C

log = logging.getLogger("terna")
ROMA = ZoneInfo("Europe/Rome")

URL_TOKEN = "https://api.terna.it/public-api/access-token"
URL_API = "https://api.terna.it/"
URL_DC = "https://dati.terna.it/api/sitecore/dati/downloadcenter/recordsv2"
AGENTE = "EuGEnio (https://eugenio.statocritico.it) - serie di Terna"
EPOCA_DC_MS = 62135596800000          # millisecondi tra 0001-01-01 e 1970-01-01: le date del Download Center


def _norm(nome: str) -> str:
    """Nome di colonna confrontabile: «Total Load [MW]» (Download Center) e «total_load_MW» (API) → «totalloadmw»."""
    return re.sub(r"[^a-z0-9]", "", str(nome).lower())


# serie → endpoint dell'API, chiavi possibili dell'elenco nella risposta, dataset del Download Center, colonne
# (nome normalizzato di Terna → nostro nome), colonne di testo della chiave
SERIE: dict[str, dict] = {
    "carico_totale": {
        "api": "load/v2.0/total-load", "json": ("total_load", "totalLoad"), "dc": "TotalLoad",
        "valori": {"totalloadmw": "carico_mw", "forecasttotalloadmw": "previsione_mw"},
        "testi": {"biddingzone": "zona"}, "chiave": ("zona",)},
    "carico_mercato": {
        "api": "load/v2.0/market-load", "json": ("marketLoad", "market_load"), "dc": "MarketLoad",
        "valori": {"marketloadmw": "carico_mw", "forecastmarketloadmw": "previsione_mw"},
        "testi": {"biddingzone": "zona"}, "chiave": ("zona",)},
    "picco_valle": {
        # nel Download Center «Peak Load [MW]» e «Valley Load [MW]» sono in realtà GW (42,3 il 31/10/2025), come
        # nell'API; una riga per fonte («Type», «Primary Source [GW]») più quella del totale (fonte vuota)
        "api": "load/v2.0/peak-valley-load", "json": ("peak_valley_load", "peakValleyLoad"), "dc": "PeakValleyLoad",
        "valori": {"peakloadgw": "picco_gw", "peakloadmw": "picco_gw", "valleyloadgw": "valle_gw",
                   "valleyloadmw": "valle_gw", "primarysourcegw": "fonte_gw"},
        "testi": {"type": "fonte"}, "chiave": ("fonte",)},
    "produzione": {
        "api": "generation/v2.0/actual-generation", "json": ("actual_generation", "actualGeneration"),
        "dc": "ActualGeneration", "valori": {"actualgenerationgwh": "energia_gwh", "actualgeneration": "energia_gwh"},
        "testi": {"primarysource": "fonte"}, "chiave": ("fonte",)},
    "rinnovabili": {
        "api": "generation/v2.0/renewable-generation", "json": ("renewable_generation", "renewableGeneration"),
        "dc": "RenewableGeneration",
        "valori": {"renewablegenerationgwh": "energia_gwh", "renewablegeneration": "energia_gwh"},
        "testi": {"energysource": "fonte"}, "chiave": ("fonte",)},
    "bilancio": {
        "api": "generation/v2.0/energy-balance", "json": ("energy_balance", "energyBalance"), "dc": "EnergyBalance",
        "valori": {"energybalancegwh": "energia_gwh", "energybalance": "energia_gwh"},
        "testi": {"energysource": "fonte"}, "chiave": ("fonte",)},
}
IMCEI = {"api": "load/v2.0/monthly-index-industrial-electrical-consumption",
         "json": ("monthly_index_industrial_electrical_consumption",),
         "valori": {"monthlyimcei": "indice", "consumptiongwh": "consumo_gwh"},
         "testi": {"region": "regione", "sector": "settore", "tensiontype": "tensione"},
         "chiave": ("mese", "regione", "settore", "tensione")}


# ------------------------------------------------------------------------------------------------------- errori
class ErroreTerna(Exception):
    """Errore definitivo di una richiesta (4xx diverso da 401/429, risposta illeggibile)."""


class Rimanda(Exception):
    """429 o 5xx: si smette per ora e si riprova più tardi (TERNA_RIPROVA_MIN), senza consumare altra quota."""


class QuotaEsaurita(Exception):
    """Il contatore di oggi ha raggiunto TERNA_API_TETTO."""


# ------------------------------------------------------------------------------------------------------- utilità
def _numero(v) -> float | None:
    """Numeri in formati misti: 12.5, "12.5", " 13", "1.234,5", "1,234.5", "", None."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(" ", "").replace(" ", "")
    if not s or s.lower() in ("null", "nan", "-", "n.d."):
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _mese(s: str) -> tuple[int, int]:
    a, m = s.split("-")
    return int(a), int(m)


def _mese_str(a: int, m: int) -> str:
    return f"{a:04d}-{m:02d}"


def _mese_dopo(s: str) -> str:
    a, m = _mese(s)
    return _mese_str(a + (m == 12), 1 if m == 12 else m + 1)


def _leggi_json(p: Path, predefinito):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return predefinito


def _scrivi_json(p: Path, dati) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(dati, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    tmp.replace(p)


def stato_leggi() -> dict:
    return _leggi_json(C.TERNA_DATI / "stato.json", {})


def stato_scrivi(s: dict) -> None:
    _scrivi_json(C.TERNA_DATI / "stato.json", s)


def chiavi_presenti() -> bool:
    return bool(C.TERNA_CLIENT_ID and C.TERNA_CLIENT_SECRET)


# ------------------------------------------------------------------------------------------------------- quota
class Quota:
    """Contatore persistente delle richieste all'API di oggi (giorno italiano): {"giorno": "AAAA-MM-GG", "richieste": n}.
    Si scrive PRIMA di ogni richiesta, così un errore o un riavvio non la fanno dimenticare."""

    def __init__(self, file: Path, tetto: int, oggi=None):
        self.file, self.tetto = file, tetto
        self._oggi = oggi or (lambda: dt.datetime.now(ROMA).date())

    def _letto(self) -> dict:
        d = _leggi_json(self.file, {})
        g = str(self._oggi())
        return d if d.get("giorno") == g else {"giorno": g, "richieste": 0}

    def usate(self) -> int:
        return int(self._letto().get("richieste", 0))

    def rimaste(self) -> int:
        return max(0, self.tetto - self.usate())

    def consuma(self) -> None:
        d = self._letto()
        if d["richieste"] >= self.tetto:
            raise QuotaEsaurita(f"tetto di {self.tetto} richieste all'API di Terna raggiunto per il {d['giorno']}")
        d["richieste"] += 1
        _scrivi_json(self.file, d)


# ------------------------------------------------------------------------------------------------------- API ufficiale
class ClienteAPI:
    """Client dell'API ufficiale: token OAuth2 (valido 300 s, rinnovato prima della scadenza o dopo un 401), una
    richiesta al secondo, quota consumata prima di ogni chiamata (anche del token)."""

    def __init__(self, client_id: str, client_secret: str, quota: Quota, http: httpx.Client | None = None,
                 pausa: float | None = None, dormi=time.sleep, orologio=time.monotonic):
        self._id, self._segreto = client_id, client_secret
        self.quota = quota
        self.http = http or httpx.Client(timeout=90, headers={"User-Agent": AGENTE})
        self.pausa = C.TERNA_PAUSA_S if pausa is None else pausa
        self._dormi, self._orologio = dormi, orologio
        self._ultima = None
        self._token, self._scade = None, 0.0

    def __repr__(self) -> str:                 # niente chiavi né token nelle tracce degli errori
        return f"ClienteAPI(quota={self.quota.usate()}/{self.quota.tetto})"

    def _attendi(self) -> None:
        if self._ultima is not None:
            resta = self.pausa - (self._orologio() - self._ultima)
            if resta > 0:
                self._dormi(resta)
        self._ultima = self._orologio()

    def _nuovo_token(self) -> str:
        self.quota.consuma()
        self._attendi()
        r = self.http.post(URL_TOKEN, data={"grant_type": "client_credentials", "client_id": self._id,
                                            "client_secret": self._segreto},
                           headers={"Content-Type": "application/x-www-form-urlencoded"})
        if r.status_code == 429 or r.status_code >= 500:
            raise Rimanda(f"token: HTTP {r.status_code}")
        if r.status_code != 200:
            # il corpo non si registra: potrebbe ripetere i parametri
            raise ErroreTerna(f"token non ottenuto: HTTP {r.status_code} (chiavi sbagliate o applicazione non attiva?)")
        try:
            d = r.json()
            self._token = d["access_token"]
        except Exception:
            raise ErroreTerna("token: risposta illeggibile") from None
        self._scade = self._orologio() + float(d.get("expires_in") or 300) - 30
        return self._token

    def get(self, percorso: str, params: dict) -> dict | None:
        """GET con il token; None se il corpo è vuoto (parametri non riconosciuti da Terna: niente errore, corpo vuoto)."""
        for tentativo in (1, 2):
            if not self._token or self._orologio() >= self._scade:
                self._nuovo_token()
            self.quota.consuma()
            self._attendi()
            r = self.http.get(URL_API + percorso, params=params, headers={"Authorization": f"Bearer {self._token}"})
            if r.status_code == 401 and tentativo == 1:
                log.info("Terna API: 401 su %s, chiedo un token nuovo", percorso)
                self._token = None
                continue
            if r.status_code == 429 or r.status_code >= 500:
                raise Rimanda(f"{percorso}: HTTP {r.status_code}")
            if r.status_code != 200:
                raise ErroreTerna(f"{percorso} {params}: HTTP {r.status_code}")
            if not r.content.strip():
                log.warning("Terna API: corpo vuoto per %s %s (parametri non riconosciuti?)", percorso, params)
                return None
            try:
                return r.json()
            except Exception:
                raise ErroreTerna(f"{percorso}: risposta non JSON") from None
        raise ErroreTerna(f"{percorso}: 401 anche con un token nuovo")


def _elenco(risposta: dict | None, chiavi: tuple) -> list[dict]:
    if not risposta:
        return []
    for k in chiavi:
        if isinstance(risposta.get(k), list):
            return risposta[k]
    for k, v in risposta.items():                 # nome diverso da quello documentato: il primo elenco di oggetti
        if k != "result" and isinstance(v, list):
            return v
    return []


# ------------------------------------------------------------------------------------------------------- Download Center
class ClienteDC:
    """Download Center di dati.terna.it: un mese di un dataset, a pagine se le righe superano pageSize."""

    def __init__(self, http: httpx.Client | None = None, pausa: float | None = None, dormi=time.sleep,
                 orologio=time.monotonic, righe_pagina: int = 50000):
        self.http = http or httpx.Client(timeout=180, headers={"User-Agent": AGENTE})
        self.pausa = C.TERNA_PAUSA_S if pausa is None else pausa
        self._dormi, self._orologio = dormi, orologio
        self._ultima = None
        self.righe_pagina = righe_pagina

    def _attendi(self) -> None:
        if self._ultima is not None:
            resta = self.pausa - (self._orologio() - self._ultima)
            if resta > 0:
                self._dormi(resta)
        self._ultima = self._orologio()

    def mese(self, dataset: str, anno: int, mese: int) -> list[dict]:
        righe: list[dict] = []
        pagina = 0
        while True:
            self._attendi()
            r = self.http.post(URL_DC, json={
                "filterDataset": dataset, "filterYear": str(anno), "filterMonth": str(mese), "orderByColumn": "Date",
                "orderByDir": "desc", "pageSize": str(self.righe_pagina), "pageIndex": str(pagina), "db": "dati"})
            if r.status_code == 429 or r.status_code >= 500:
                raise Rimanda(f"Download Center {dataset} {anno}-{mese:02d}: HTTP {r.status_code}")
            if r.status_code != 200:
                raise ErroreTerna(f"Download Center {dataset} {anno}-{mese:02d}: HTTP {r.status_code}")
            try:
                d = r.json()
            except Exception:
                raise ErroreTerna(f"Download Center {dataset}: risposta non JSON") from None
            colonne = list((d.get("Columns") or {}).keys())
            dati = d.get("Data") or []
            righe += [dict(zip(colonne, x)) for x in dati]
            if not dati or len(righe) >= int(d.get("Count") or 0):
                return righe
            pagina += 1


# ------------------------------------------------------------------------------------------------------- normalizzazione
def _data_dc(v) -> dt.datetime | None:
    """Data del Download Center: millisecondi dall'1/1/0001 in ora locale «ingenua» (63897551100000 = 31/10/2025 23:45),
    oppure "/Date(ms+0100)/" (istante vero), oppure testo."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return dt.datetime(1970, 1, 1) + dt.timedelta(milliseconds=float(v) - EPOCA_DC_MS)
    s = str(v)
    m = re.match(r"/Date\((-?\d+)([+-]\d{4})?\)/", s.replace("\\", ""))
    if m:
        return dt.datetime.fromtimestamp(int(m.group(1)) / 1000, dt.timezone.utc).astimezone(ROMA).replace(tzinfo=None)
    try:
        return dt.datetime.fromisoformat(s.replace("T", " ").replace("Z", "")[:19])
    except ValueError:
        return None


def _istante_api(data: str, offset: str | None) -> dt.datetime | None:
    """date "2022-06-10 23:45:00" + date_offset "+02:00" → istante UTC; senza offset None (si decide dopo)."""
    try:
        locale = dt.datetime.fromisoformat(str(data).strip().replace("T", " ")[:19])
    except ValueError:
        return None
    m = re.match(r"^([+-])(\d{1,2}):?(\d{2})?$", str(offset or "").strip())
    if not m:
        return None
    segno = 1 if m.group(1) == "+" else -1
    delta = dt.timedelta(hours=int(m.group(2)), minutes=int(m.group(3) or 0))
    return (locale - segno * delta).replace(tzinfo=dt.timezone.utc)


def _risolvi_ora_locale(righe: list[dict], chiave: tuple, valore: str) -> None:
    """Istanti delle righe che hanno solo l'ora locale (`_locale`, senza offset). Nell'ora ripetuta di fine ottobre
    (02:00–02:59 due volte) Terna ripete la stessa ora locale senza dire quale sia l'ora legale e l'ordine delle righe non
    aiuta: per ogni zona o fonte la riga più vicina al valore del quarto d'ora precedente è l'ora legale (continuità),
    l'altra l'ora solare. Le ore inesistenti di marzo (non dovrebbero esserci) si spostano avanti di un'ora."""
    gruppi: dict[tuple, list[dict]] = {}
    for r in righe:
        if r.get("istante") is not None or r.get("_locale") is None:
            continue
        loc = r["_locale"]
        a = loc.replace(tzinfo=ROMA, fold=0)
        b = loc.replace(tzinfo=ROMA, fold=1)
        if a.utcoffset() == b.utcoffset():
            ist = a.astimezone(dt.timezone.utc)
            if ist.astimezone(ROMA).replace(tzinfo=None) != loc:          # ora inesistente
                ist = (loc + dt.timedelta(hours=1)).replace(tzinfo=ROMA).astimezone(dt.timezone.utc)
            r["istante"] = ist
        else:
            gruppi.setdefault(tuple(r.get(k) for k in chiave), []).append(r)
    if not gruppi:
        return
    precedenti: dict[tuple, list[dict]] = {}
    for r in righe:
        if r.get("istante") is not None:
            precedenti.setdefault(tuple(r.get(k) for k in chiave), []).append(r)
    for k, amb in gruppi.items():
        primo = min(x["_locale"] for x in amb)
        prima = [x for x in precedenti.get(k, []) if x["istante"] < primo.replace(tzinfo=ROMA, fold=0)]
        rif = max(prima, key=lambda x: x["istante"]).get(valore) if prima else None
        per_ora: dict[dt.datetime, list[dict]] = {}
        for x in amb:
            per_ora.setdefault(x["_locale"], []).append(x)
        for loc in sorted(per_ora):
            coppia = per_ora[loc]
            if len(coppia) >= 2 and rif is not None and all(c.get(valore) is not None for c in coppia[:2]):
                coppia = sorted(coppia[:2], key=lambda c: abs(c[valore] - rif)) + coppia[2:]
            for i, c in enumerate(coppia):
                c["istante"] = loc.replace(tzinfo=ROMA, fold=0 if i == 0 else 1).astimezone(dt.timezone.utc)
            if coppia[0].get(valore) is not None:
                rif = coppia[0][valore]


def normalizza(serie: str, righe: list[dict], origine: str) -> list[dict]:
    """Righe di Terna (Download Center o API) → righe dell'archivio: istante (UTC), zona o fonte, valori, origine."""
    S = SERIE[serie]
    fuori: list[dict] = []
    for r in righe:
        n = {_norm(k): v for k, v in r.items()}
        x: dict = {"origine": origine}
        for k in S["chiave"]:
            x[k] = ""
        for nome_t, nostro in S["testi"].items():
            if nome_t in n and n[nome_t] is not None:
                x[nostro] = str(n[nome_t]).strip()
        for nome_t, nostro in S["valori"].items():
            if nome_t in n and x.get(nostro) is None:
                x[nostro] = _numero(n[nome_t])
        for nostro in set(S["valori"].values()):
            x.setdefault(nostro, None)
        ist = _istante_api(n["date"], n.get("dateoffset")) if origine == "api" and "date" in n else None
        x["istante"] = ist
        x["_locale"] = None if ist else _data_dc(n.get("date"))
        if x["istante"] is None and x["_locale"] is None:
            continue
        fuori.append(x)
    principale = next(iter(S["valori"].values()))
    _risolvi_ora_locale(fuori, S["chiave"], principale)
    fuori = [x for x in fuori if x.get("istante") is not None]
    for x in fuori:
        x.pop("_locale", None)
    if serie == "picco_valle":
        fuori = _picco_valle_totali(fuori)
    return fuori


def _picco_valle_totali(righe: list[dict]) -> list[dict]:
    """Download Center: per ogni istante una riga per fonte con picco o valle ripetuti; si aggiunge la riga del totale
    (fonte vuota), la stessa che dà l'API."""
    tot: dict = {}
    for r in righe:
        if r["fonte"]:
            t = tot.setdefault(r["istante"], {"istante": r["istante"], "fonte": "", "picco_gw": None, "valle_gw": None,
                                              "fonte_gw": None, "origine": r["origine"]})
            for k in ("picco_gw", "valle_gw"):
                if t[k] is None and r.get(k) is not None:
                    t[k] = r[k]
    gia = {r["istante"] for r in righe if not r["fonte"]}
    return righe + [t for i, t in tot.items() if i not in gia]


def normalizza_imcei(righe: list[dict], anno: int, mese: int) -> list[dict]:
    fuori = []
    for r in righe:
        n = {_norm(k): v for k, v in r.items()}
        a, m = n.get("year"), n.get("month")
        x = {"mese": _mese_str(int(a), int(m)) if a and m else _mese_str(anno, mese), "origine": "api"}
        for nome_t, nostro in IMCEI["testi"].items():
            x[nostro] = str(n.get(nome_t) or "").strip()
        for nome_t, nostro in IMCEI["valori"].items():
            x[nostro] = _numero(n.get(nome_t))
        fuori.append(x)
    return fuori


# ------------------------------------------------------------------------------------------------------- archivio
def cartella_serie() -> Path:
    return C.TERNA_DATI / "serie"


def archivia(serie: str, righe: list[dict], cartella: Path | None = None) -> int:
    """Aggiunge le righe ai file mensili della serie, deduplicando sulla chiave (vince l'ultima scritta). Restituisce le
    righe ricevute e scritte."""
    import pandas as pd
    if not righe:
        return 0
    cartella = (cartella or cartella_serie()) / serie
    cartella.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(righe)
    if serie == "imcei":
        chiave = list(IMCEI["chiave"])
        df["_mese"] = df["mese"]
        colonne = ["mese", "regione", "settore", "tensione", "indice", "consumo_gwh", "origine"]
    else:
        S = SERIE[serie]
        chiave = ["istante", *S["chiave"]]
        df["istante"] = pd.to_datetime(df["istante"], utc=True)
        df["_mese"] = df["istante"].dt.tz_convert("Europe/Rome").dt.strftime("%Y-%m")
        valori = list(dict.fromkeys(S["valori"].values()))
        colonne = ["istante", *S["chiave"], *valori, "origine"]
    for c in colonne:
        if c not in df:
            df[c] = None
    testi = [c for c in chiave if c != "istante"]
    n = 0
    for mese, parte in df.groupby("_mese"):
        f = cartella / f"{mese}.parquet"
        parte = parte[colonne]
        n += len(parte)
        if f.exists():
            parte = pd.concat([pd.read_parquet(f), parte], ignore_index=True)
        for c in testi:
            parte[c] = parte[c].fillna("").astype(str)
        for c in colonne:
            if c not in chiave and c != "origine":
                parte[c] = pd.to_numeric(parte[c], errors="coerce").astype("float64")
        parte = parte.drop_duplicates(subset=chiave, keep="last").sort_values(chiave).reset_index(drop=True)
        tmp = f.with_suffix(".tmp")
        parte.to_parquet(tmp, index=False)
        tmp.replace(f)
    return n


# ------------------------------------------------------------------------------------------------------- lavori
def _giorno_it(g: dt.date) -> str:
    return g.strftime("%d/%m/%Y")


def _api_giorni(cli: ClienteAPI, stato: dict, ieri: dt.date, esito: dict) -> None:
    """Il giorno prima e quelli rimasti indietro (al più TERNA_API_GIORNI_MAX); lo stato avanza solo a giorno completo."""
    fatto = stato.get("api_giorno")
    primo = ieri - dt.timedelta(days=C.TERNA_API_GIORNI_MAX - 1)
    if fatto:
        primo = max(primo, dt.date.fromisoformat(fatto) + dt.timedelta(days=1))
    g = primo
    while g <= ieri:
        if cli.quota.rimaste() < len(SERIE) + 1:
            esito["avvisi"].append(f"quota di oggi quasi finita: {g} rimandato a domani")
            break
        for serie, S in SERIE.items():
            risposta = cli.get(S["api"], {"dateFrom": _giorno_it(g), "dateTo": _giorno_it(g)})
            esito["righe"][serie] = esito["righe"].get(serie, 0) + archivia(
                serie, normalizza(serie, _elenco(risposta, S["json"]), "api"))
        stato["api_giorno"] = str(g)
        stato["ultimo_ok_api"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        stato_scrivi(stato)
        esito["giorni_api"].append(str(g))
        g += dt.timedelta(days=1)


def _api_imcei(cli: ClienteAPI, stato: dict, oggi: dt.date, esito: dict, massimo: int = 12) -> None:
    """IMCEI (solo nell'API): dal TERNA_STORICO_INIZIO un mese per richiesta fino al primo mese non ancora pubblicato.
    Recupero: fino a `massimo` mesi al giorno; a regime una sola prova al giorno dal TERNA_IMCEI_GIORNO del mese."""
    corrente = _mese_str(oggi.year, oggi.month)
    m = stato.get("imcei") or C.TERNA_STORICO_INIZIO
    if m >= corrente or stato.get("imcei_provato") == str(oggi):
        return
    a, mm = _mese(m)
    indietro = (oggi.year - a) * 12 + oggi.month - mm
    if indietro <= 2 and oggi.day < C.TERNA_IMCEI_GIORNO:
        return
    stato["imcei_provato"] = str(oggi)
    for _ in range(massimo):
        if m >= corrente or cli.quota.rimaste() < 2:
            break
        a, mm = _mese(m)
        righe = normalizza_imcei(_elenco(cli.get(IMCEI["api"], {"year": a, "month": mm}), IMCEI["json"]), a, mm)
        if not righe:
            if (oggi.year - a) * 12 + oggi.month - mm <= 3:
                log.info("Terna IMCEI: %s non ancora pubblicato", m)
                break
            log.warning("Terna IMCEI: %s senza dati (mese vecchio: lo salto)", m)   # lo storico non si blocca
        esito["righe"]["imcei"] = esito["righe"].get("imcei", 0) + archivia("imcei", righe)
        m = _mese_dopo(m)
        stato["imcei"] = m
    stato_scrivi(stato)


def _api_mese(cli: ClienteAPI, serie: str, anno: int, mese: int) -> int:
    """Riserva dello storico: un mese intero di una serie dall'API (una richiesta)."""
    S = SERIE[serie]
    ultimo = calendar.monthrange(anno, mese)[1]
    risposta = cli.get(S["api"], {"dateFrom": f"01/{mese:02d}/{anno}", "dateTo": f"{ultimo:02d}/{mese:02d}/{anno}"})
    righe = normalizza(serie, _elenco(risposta, S["json"]), "api")
    if not righe:
        raise ErroreTerna(f"API {serie} {anno}-{mese:02d}: nessuna riga")
    return archivia(serie, righe)


def _dc_storico(dc: ClienteDC, cli: ClienteAPI | None, stato: dict, oggi: dt.date, esito: dict) -> None:
    """Storico dal Download Center: TERNA_STORICO_MESI mesi per serie e per giorno, dai mesi già finiti."""
    corrente = _mese_str(oggi.year, oggi.month)
    puntatori = stato.setdefault("dc", {})
    errori_di_fila = 0
    for serie, S in SERIE.items():
        for _ in range(C.TERNA_STORICO_MESI):
            m = puntatori.get(serie) or C.TERNA_STORICO_INIZIO
            if m >= corrente:
                break
            a, mm = _mese(m)
            try:
                righe = normalizza(serie, dc.mese(S["dc"], a, mm), "dc")
                if not righe:
                    raise ErroreTerna(f"Download Center {S['dc']} {m}: nessuna riga")
                esito["righe"][serie] = esito["righe"].get(serie, 0) + archivia(serie, righe)
                errori_di_fila = 0
                stato["ultimo_ok_dc"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            except (ErroreTerna, Rimanda, httpx.HTTPError) as e:
                log.warning("Terna storico %s %s dal Download Center: %s", serie, m, e)
                errori_di_fila += 1
                riuscito = False
                if cli is not None:
                    try:
                        esito["righe"][serie] = esito["righe"].get(serie, 0) + _api_mese(cli, serie, a, mm)
                        riuscito = True
                        esito["avvisi"].append(f"{serie} {m}: dall'API (Download Center non disponibile)")
                    except (ErroreTerna, QuotaEsaurita) as e2:
                        log.warning("Terna storico %s %s dall'API: %s", serie, m, e2)
                if not riuscito:
                    esito["avvisi"].append(f"{serie} {m}: non scaricato ({e})")
                    if errori_di_fila >= 2:
                        log.warning("Terna: Download Center non disponibile, storico rimandato a domani")
                        stato_scrivi(stato)
                        return
                    break
            puntatori[serie] = _mese_dopo(m)
            esito["mesi_dc"].append(f"{serie} {m}")
            stato_scrivi(stato)


# ------------------------------------------------------------------------------------------------------- giorni mancanti
# (22/11/2026, Paolo) nello storico del Download Center mancavano il 14 e il 15 gennaio 2026 (carico e produzione): un
# mese con dei giorni vuoti entrava lo stesso e non si riprovava più. Ora i mesi archiviati si controllano una volta
# (quelli completi vanno in stato["buchi_controllati"]), quelli con giorni mancanti vanno in stato["buchi"] e si riprovano
# una volta al giorno, al più TERNA_BUCHI_MESI mesi per giro e TERNA_BUCHI_PROVE volte.
SERIE_BUCHI = ("carico_totale", "produzione", "rinnovabili")


def giorni_mancanti(serie: str, mese: str, cartella: Path | None = None) -> list[str]:
    """Giorni (AAAA-MM-GG, ora italiana) del mese archiviato con meno della metà degli istanti di un giorno tipico del
    mese (mediana: vale per i dati orari e per quelli a 15 minuti). [] se il file non c'è."""
    import pandas as pd
    f = (cartella or cartella_serie()) / serie / f"{mese}.parquet"
    if not f.exists():
        return []
    df = pd.read_parquet(f, columns=["istante"])
    giorni = pd.to_datetime(df["istante"], utc=True).dt.tz_convert("Europe/Rome").dt.strftime("%Y-%m-%d")
    conta = df["istante"].groupby(giorni.values).nunique()
    if conta.empty:
        return []
    soglia = 0.5 * float(conta.median())
    a, m = _mese(mese)
    tutti = [f"{mese}-{g:02d}" for g in range(1, calendar.monthrange(a, m)[1] + 1)]
    return [g for g in tutti if conta.get(g, 0) < soglia]


def _ripara_buchi(dc: ClienteDC, cli: ClienteAPI | None, stato: dict, oggi: dt.date, esito: dict) -> None:
    corrente = _mese_str(oggi.year, oggi.month)
    buchi, controllati = stato.setdefault("buchi", {}), stato.setdefault("buchi_controllati", {})
    puntatori = stato.get("dc") or {}
    da_fare = []
    for serie in SERIE_BUCHI:
        cartella = cartella_serie() / serie
        fine = puntatori.get(serie) or C.TERNA_STORICO_INIZIO      # i mesi prima di questo sono già nello storico
        for f in sorted(cartella.glob("*.parquet")) if cartella.exists() else []:
            m = f.stem
            if m >= corrente or m >= fine or m in controllati.get(serie, []):
                continue
            info = buchi.get(serie, {}).get(m)
            if info is None:
                g = giorni_mancanti(serie, m)
                if not g:
                    controllati.setdefault(serie, []).append(m)
                    continue
                info = buchi.setdefault(serie, {})[m] = {"giorni": g, "prove": 0}
                log.warning("Terna %s %s: mancano %d giorni (%s): li riprovo nei prossimi giri", serie, m, len(g),
                            ", ".join(g[:5]) + ("…" if len(g) > 5 else ""))
            if info.get("definitivo") or info.get("ultima") == str(oggi):
                continue
            da_fare.append((serie, m, info))
    for serie, m, info in da_fare[:C.TERNA_BUCHI_MESI]:
        a, mm = _mese(m)
        info["prove"] += 1
        info["ultima"] = str(oggi)
        S = SERIE[serie]
        try:
            if cli is not None and cli.quota.rimaste() >= len(info["giorni"]) + 1:
                for g in info["giorni"]:
                    d = dt.date.fromisoformat(g)
                    risposta = cli.get(S["api"], {"dateFrom": _giorno_it(d), "dateTo": _giorno_it(d)})
                    archivia(serie, normalizza(serie, _elenco(risposta, S["json"]), "api"))
            else:
                archivia(serie, normalizza(serie, dc.mese(S["dc"], a, mm), "dc"))
        except (ErroreTerna, Rimanda, QuotaEsaurita, httpx.HTTPError) as e:
            log.warning("Terna %s %s, giorni mancanti: %s", serie, m, e)
            esito["avvisi"].append(f"{serie} {m}, giorni mancanti: {e}")
        resto = giorni_mancanti(serie, m)
        if not resto:
            del buchi[serie][m]
            controllati.setdefault(serie, []).append(m)
            esito.setdefault("buchi_riparati", []).append(f"{serie} {m}")
            log.info("Terna %s %s: giorni mancanti recuperati", serie, m)
        else:
            info["giorni"] = resto
            if info["prove"] >= C.TERNA_BUCHI_PROVE:
                info["definitivo"] = True
                log.warning("Terna %s %s: %s ancora mancanti dopo %d prove, non riprovo più", serie, m, ", ".join(resto), info["prove"])
            esito.setdefault("buchi", []).append(f"{serie} {m}: {', '.join(resto)}")
    stato_scrivi(stato)


def _dc_mese_corrente(dc: ClienteDC, stato: dict, oggi: dt.date, esito: dict) -> None:
    """Riserva dell'aggiornamento giornaliero: il mese in corso dal Download Center (solo per le serie col storico
    completo), quando l'API non è configurata o non ha risposto."""
    corrente = _mese_str(oggi.year, oggi.month)
    for serie, S in SERIE.items():
        if (stato.get("dc") or {}).get(serie, C.TERNA_STORICO_INIZIO) < corrente:
            continue
        try:
            righe = normalizza(serie, dc.mese(S["dc"], oggi.year, oggi.month), "dc")
            esito["righe"][serie] = esito["righe"].get(serie, 0) + archivia(serie, righe)
            stato["ultimo_ok_dc"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        except (ErroreTerna, Rimanda, httpx.HTTPError) as e:
            log.warning("Terna mese in corso %s dal Download Center: %s", serie, e)
            esito["avvisi"].append(f"{serie} {corrente} (Download Center): {e}")
            break
    stato_scrivi(stato)


def aggiorna(oggi: dt.date | None = None, api: ClienteAPI | None = None, dc: ClienteDC | None = None) -> dict:
    """Lavoro `terna-api`: API (giorno prima, IMCEI), storico dal Download Center, riserva. Restituisce l'esito;
    "rimandato": True dopo un 429 o un 5xx (il worker riprova dopo TERNA_RIPROVA_MIN minuti). Un solo aggiornamento alla
    volta (lucchetto TERNA_DATI/.aggiorna.lock): il ciclo del worker e un `docker compose run` a mano non si sovrappongono."""
    import fcntl
    C.TERNA_DATI.mkdir(parents=True, exist_ok=True)
    with open(C.TERNA_DATI / ".aggiorna.lock", "w") as lucchetto:
        try:
            fcntl.flock(lucchetto, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            log.info("Terna: un altro aggiornamento è in corso, niente da fare")
            return {"giorni_api": [], "mesi_dc": [], "righe": {}, "avvisi": [], "rimandato": False, "api": "",
                    "saltato": "aggiornamento già in corso"}
        return _aggiorna(oggi, api, dc)


def _aggiorna(oggi: dt.date | None, api: ClienteAPI | None, dc: ClienteDC | None) -> dict:
    oggi = oggi or dt.datetime.now(ROMA).date()
    ieri = oggi - dt.timedelta(days=1)
    C.TERNA_DATI.mkdir(parents=True, exist_ok=True)
    stato = stato_leggi()
    esito: dict = {"giorni_api": [], "mesi_dc": [], "righe": {}, "avvisi": [], "rimandato": False, "api": "spenta"}
    if api is None and chiavi_presenti():
        api = ClienteAPI(C.TERNA_CLIENT_ID, C.TERNA_CLIENT_SECRET, Quota(C.TERNA_DATI / "quota_api.json", C.TERNA_API_TETTO))
    api_ok = False
    if api is None:
        log.info("Terna API: TERNA_CLIENT_ID o TERNA_CLIENT_SECRET mancanti nel .env, aggiornamento dall'API saltato "
                 "(storico dal Download Center sì)")
    else:
        esito["api"] = "configurata"
        try:
            _api_giorni(api, stato, ieri, esito)
            _api_imcei(api, stato, oggi, esito)
            api_ok = True
        except Rimanda as e:
            log.warning("Terna API: %s, riprovo più tardi", e)
            esito["rimandato"] = True
            esito["avvisi"].append(f"API: {e}")
        except QuotaEsaurita as e:
            log.warning("Terna API: %s", e)
            esito["avvisi"].append(str(e))
        except (ErroreTerna, httpx.HTTPError) as e:
            log.warning("Terna API: %s: %s", type(e).__name__, e)
            esito["avvisi"].append(f"API: {type(e).__name__}: {e}")
    dc = dc or ClienteDC()
    _dc_storico(dc, api if (api is not None and not esito["rimandato"]) else None, stato, oggi, esito)
    if C.TERNA_BUCHI_MESI:
        _ripara_buchi(dc, api if (api is not None and not esito["rimandato"]) else None, stato, oggi, esito)
    if not api_ok:
        _dc_mese_corrente(dc, stato, oggi, esito)
    if api is not None:
        esito["quota_usata"] = api.quota.usate()
    _controlla_avviso(stato, esito)
    stato_scrivi(stato)
    log.info("Terna: %s", {k: v for k, v in esito.items() if v})
    return esito


def _controlla_avviso(stato: dict, esito: dict, adesso: dt.datetime | None = None) -> None:
    """Email una volta per episodio se l'archivio non si aggiorna da più di TERNA_AVVISO_GIORNI giorni: con le chiavi
    conta l'API (chiavi scadute o revocate si scoprono così, anche se il Download Center fa da riserva), senza conta il
    Download Center. Si riarma quando torna ad aggiornarsi. Le chiavi mancanti non sono un guasto: nessuna email."""
    from . import avvisi
    adesso = adesso or dt.datetime.now(dt.timezone.utc)
    tipo = "api" if esito.get("api") == "configurata" else "dc"
    ultimo = stato.get(f"ultimo_ok_{tipo}") or stato.setdefault(f"inizio_{tipo}", adesso.isoformat(timespec="seconds"))
    fermo = (adesso - dt.datetime.fromisoformat(ultimo)).total_seconds() / 86400
    chiave = f"avvisato_{tipo}"
    if fermo > C.TERNA_AVVISO_GIORNI:
        if not stato.get(chiave):
            stato[chiave] = True
            fonte = "L'API ufficiale" if tipo == "api" else "Il Download Center"
            avvisi.invia(f"dati di Terna non aggiornati da più di {C.TERNA_AVVISO_GIORNI:g} giorni",
                         f"{fonte} di Terna non aggiorna l'archivio {C.TERNA_DATI / 'serie'} da {fermo:.1f} giorni.\n"
                         "Controllare il registro del worker (docker compose logs worker | grep -i terna) e, per l'API, "
                         "l'applicazione su https://developer.terna.it.\nUltimi avvisi: " + "; ".join(esito["avvisi"][-10:]))
    else:
        stato[chiave] = False
