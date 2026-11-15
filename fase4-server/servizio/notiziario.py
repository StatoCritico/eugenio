"""Newsletter automatica dei dati di EuGEnio (listmonk, notizie.statocritico.it).

Distinta dalla newsletter degli articoli di Stato Critico (Substack, scritta a mano). Una sola
lista, mensile, a cui ci si iscrive dal modulo pubblico con doppia conferma: il giorno
NOTIZIARIO_GIORNO arriva il riepilogo del mese appena concluso e la sezione «Novità di EuGEnio».

Contenuto (11/11/2026, decisioni di Paolo per il primo numero):
- in cima gli **indici dei prezzi** del mese (file del sito /sito/dati/prezzi/indici.json): listini Intercent-ER
  (energia elettrica lotti 1 e 2, gas) e Consip (lotto dell'Emilia-Romagna), PSV day-ahead ARERA, PFOR,t ricostruito, con
  la variazione sullo stesso mese dell'anno prima e il collegamento alla pagina Statistiche › Indici dei prezzi; mai
  PUN né TTF;
- capoluoghi di provincia serviti dal sito, con i secondi capoluoghi (Cesena accanto a Forlì e gli altri di
  CO_CAPOLUOGHI): frase di sintesi, temperatura media, scarto in °C dalla media dello stesso mese negli anni precedenti
  dell'archivio (periodo dichiarato), scarto dalla normale 1991–2020 (dal clima dal 1940, fase 9), gradi giorno base 20
  °C di tutti i giorni del mese con la loro media e lo scarto;
- «Novità di EuGEnio»: le voci di fase5-sito/novita.toml dal numero precedente (escluso) al giorno dell'invio (compreso);
  nel primo numero (NOTIZIARIO_PRIMO_NUMERO) tutte, con due righe di benvenuto;
- niente prezzi Eurostat (tolti l'11/11/2026: dato semestrale, per ora non dice niente).
Con NOTIZIARIO_INVIO_AUTOMATICO=true (predefinito) le campagne partono da sole; altrimenti restano in
bozza in listmonk. I dati GME e TTF restano interni: non compaiono.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import time
import tomllib
from pathlib import Path

import httpx
import pandas as pd

from . import avvisi, config as C, listmonk as L, meteo

log = logging.getLogger(__name__)
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre",
        "ottobre", "novembre", "dicembre"]
FONTE_METEO = "Fonte: elaborazione EuGEnio su dati Open-Meteo.com (ERA5/Copernicus corretto, DWD ICON), CC BY 4.0."
# secondi capoluoghi delle province con due o tre capoluoghi (comuni.parquet segna solo il primo)
CO_CAPOLUOGHI = {"040007": "Cesena", "041067": "Urbino", "045003": "Carrara", "110001": "Andria", "110009": "Trani"}
NORMALE = "1991-2020"


def _num(x, dec=0):
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _segno(x: float, dec: int = 0) -> str:
    """Numero con il segno davanti, + o − (segno meno tipografico); zero senza segno."""
    t = _num(abs(x), dec)
    if t.strip("0,") == "":
        return t
    return ("+" if x > 0 else "−") + t


def _periodo(a: int, b: int) -> str:
    return str(a) if a == b else f"{a}–{b}"


def _capoluoghi() -> pd.DataFrame:
    cm = meteo.comuni()
    if "capoluogo" not in cm:
        return cm.head(0)
    return cm[cm.capoluogo.fillna(False).astype(bool) | cm.istat.astype(str).isin(CO_CAPOLUOGHI)].sort_values("nome")


def _piede() -> list[str]:
    return ["", f"Previsioni dei consumi per il tuo edificio: {C.SITO_URL}", "",
            "EuGEnio è un servizio di Stato Critico (statocritico.it)."]


def _primo_numero(invio: dt.date) -> bool:
    return f"{invio.year}-{invio.month:02d}" == C.NOTIZIARIO_PRIMO_NUMERO


def _numero_precedente(invio: dt.date) -> dt.date | None:
    """Giorno d'invio del numero precedente (None per il primo numero: le novità partono dall'inizio)."""
    if _primo_numero(invio):
        return None
    prima = invio.replace(day=1) - dt.timedelta(days=1)
    return prima.replace(day=min(C.NOTIZIARIO_GIORNO, prima.day))


def _benvenuto() -> list[str]:
    return ["**Benvenuto!** Questo è il primo numero della newsletter dei dati di EuGEnio, il servizio di Stato Critico "
            "che mette a disposizione di tutti, gratis e con codice aperto, dati e strumenti per l'energia degli "
            "edifici: clima e gradi giorno per comune, previsioni dei consumi, patrimonio edilizio ed edifici in 3D.", "",
            f"Ogni mese, il {C.NOTIZIARIO_GIORNO}, ti porta gli indici dei prezzi dell'energia, il freddo del mese "
            "appena concluso nei capoluoghi e le novità del servizio. Puoi cancellarti in ogni momento con il collegamento in fondo all'email.", ""]


# ---------------------------------------------------------------------------------------------- novità
def novita_tra(dal: dt.date | None, al: dt.date, file: Path | None = None) -> list[str]:
    """Righe Markdown della sezione «Novità di EuGEnio»: le voci di novita.toml con data dopo `dal` (escluso; None =
    dall'inizio) e fino ad `al` (compreso). Vuoto se nessuna voce."""
    f = Path(file or C.NOVITA_TOML)
    try:
        voci = tomllib.loads(f.read_text(encoding="utf-8")).get("voce", [])
    except (OSError, ValueError) as e:
        log.info("Newsletter: novità non lette (%s)", e)
        return []
    scelte = []
    for v in voci:
        try:
            g = dt.date.fromisoformat(str(v.get("data", "")))
        except ValueError:
            continue
        if (dal is None or g > dal) and g <= al:
            scelte.append((g, v))
    if not scelte:
        return []
    righe = ["## Novità di EuGEnio", ""]
    for g, v in sorted(scelte, key=lambda x: (x[0], x[1].get("versione", ""))):
        righe += [f"**{g.day} {MESI[g.month - 1]}: {v['titolo']}**", ""]
        if str(v.get("testo", "")).strip():      # voce senza elenchi (08/11/2026: «Meet EuGEnio», 26/10)
            righe += [str(v["testo"]).strip(), ""]
        # (08/11/2026) gruppi della pagina Novità: Nuovo, Migliorato, Verificato (righe vuote: elenchi Markdown giusti)
        for k, nome in (("nuovo", "Nuovo"), ("migliorato", "Migliorato"), ("verificato", "Verificato")):
            if v.get(k):
                righe += [f"*{nome}*", ""] + [f"- {x}" for x in v[k]] + [""]
    righe += [f"Tutte le novità: {C.SITO_URL}/novita.html", ""]
    return righe


# ---------------------------------------------------------------------------------------------- clima
def _clima_1940(istat: str, regione: str | None) -> tuple[dict, dict] | None:
    """Sintesi e mensili anno per anno del clima dal 1940 (fase 9, file del sito), o None se mancano."""
    base = Path(C.SITO_DATI) / "clima"
    try:
        if not regione:
            regione = json.loads((base / "regioni.json").read_text(encoding="utf-8")).get(istat)
        if not regione:
            return None
        sintesi = json.loads((base / regione / f"{istat}.json").read_text(encoding="utf-8"))
        mensili = json.loads((base / regione / f"{istat}_mensili.json").read_text(encoding="utf-8"))
        return sintesi, mensili
    except (OSError, ValueError):
        return None


def _scarto_storico(istat: str, regione: str | None, mese: int, da: int, a: int) -> float | None:
    """Di quanto il mese, in media negli anni da–a, era più caldo della normale 1991–2020 nella serie del clima dal 1940
    (ERA5-Land, stessa serie per i due termini). Sommato allo scarto dalla media da–a dell'archivio dà lo scarto dalla
    normale senza confrontare fonti diverse. None se mancano i file o qualche anno."""
    c = _clima_1940(istat, regione)
    if c is None:
        return None
    sintesi, mens = c
    try:
        normale = sintesi["periodi"][NORMALE]["mensili"]["t_media"][mese - 1]
        scala = mens.get("scala", {}).get("t_media", 10)
        valori = []
        for anno in range(da, a + 1):
            i = (anno - mens["da"]) * 12 + mese - 1
            if anno < mens["da"] or anno > mens["a"] or mens["t_media"][i] is None:
                return None
            valori.append(mens["t_media"][i] / scala)
    except (KeyError, IndexError, TypeError):
        return None
    if normale is None or not valori:
        return None
    return sum(valori) / len(valori) - normale


def _voci_freddo(cap: pd.DataFrame, anno: int, mese: int) -> list[dict]:
    """Temperatura e gradi giorno del mese per ogni comune di `cap` (istat, nome, facoltativi regione_cod), confrontati
    con lo stesso mese degli anni precedenti dell'archivio (con almeno 25 giorni) e con la normale 1991–2020. Si legge
    il giornaliero dei soli comuni di `cap` (filtro sul parquet: il file nazionale non si carica mai tutto)."""
    if cap.empty:
        return []
    g = pd.read_parquet(C.DATI / "giornaliero.parquet", columns=["istat", "data", "gg20", "t_media"],
                        filters=[("istat", "in", [str(i) for i in cap.istat])])
    g["data"] = pd.to_datetime(g.data)
    g = g[g.istat.isin(cap.istat) & (g.data.dt.month == mese)]
    if g.empty:
        return []
    voci = []
    for r in cap.itertuples():
        x = g[g.istat == r.istat]
        ora = x[x.data.dt.year == anno]
        a = x[x.data.dt.year < anno].groupby(x.data.dt.year).agg(gg=("gg20", "sum"), t=("t_media", "mean"),
                                                                 n=("gg20", "size"))
        a = a[a.n >= 25]                                    # anni con il mese (quasi) completo
        if len(ora) < 25 or a.empty:
            continue
        gg, t = ora.gg20.sum(), ora.t_media.mean()
        media_gg, media_t = a.gg.mean(), a.t.mean()
        da, fino = int(a.index.min()), int(a.index.max())
        reg = getattr(r, "regione_cod", None)
        storico = _scarto_storico(str(r.istat), reg, mese, da, fino)
        voci.append({"nome": r.nome, "regione_cod": reg, "gg": gg, "media_gg": media_gg, "t": t, "dt": t - media_t,
                     "dn": None if storico is None else t - media_t + storico,
                     "dgg": 100 * (gg / media_gg - 1) if media_gg > 1 else None, "da": da, "a": fino})
    return voci


def _righe_freddo(voci: list[dict], anno: int, mese: int, note: bool = True) -> list[str]:
    """Frase di sintesi e tabella dei capoluoghi; con `note` anche «Il tuo comune non c'è?», la fonte e il metodo."""
    if not voci:
        return []
    per = _periodo(min(v["da"] for v in voci), max(v["a"] for v in voci))
    mese_anno = f"{MESI[mese - 1].capitalize()} {anno}"
    n = len(voci)
    caldi = sum(1 for v in voci if round(v["dt"], 1) > 0)
    freddi = sum(1 for v in voci if round(v["dt"], 1) < 0)
    if caldi and not freddi:
        frase = f"{mese_anno} è stato più caldo della media {per} in {caldi} capoluoghi su {n}"
    elif freddi and not caldi:
        frase = f"{mese_anno} è stato più freddo della media {per} in {freddi} capoluoghi su {n}"
    elif caldi or freddi:
        frase = (f"{mese_anno} è stato più caldo della media {per} in {caldi} capoluoghi su {n} "
                 f"e più freddo in {freddi}")
    else:
        frase = f"{mese_anno} è stato in linea con la media {per} in tutti i {n} capoluoghi"
    dettagli = [f"in media {_segno(sum(v['dt'] for v in voci) / n, 1)} °C"]
    dgg = [v["dgg"] for v in voci if v["dgg"] is not None]
    if dgg and round(sum(dgg) / len(dgg)) != 0:
        d = sum(dgg) / len(dgg)
        dettagli.append(f"con il {_num(abs(d))} % di gradi giorno {'in meno' if d < 0 else 'in più'}")
    frase += ": " + " ".join(dettagli) + "."
    dn = [v["dn"] for v in voci if v["dn"] is not None]
    if dn:
        frase += f" Rispetto al clima del 1991–2020 lo scarto medio è di {_segno(sum(dn) / len(dn), 1)} °C."
    con_normale = bool(dn)
    righe = [frase, "",
             f"Temperatura media e gradi giorno (base 20 °C, tutti i giorni del mese, anche fuori dal periodo di "
             f"accensione di legge) di {mese_anno.lower()}, confrontati con lo stesso mese del {per} nell'archivio di "
             "EuGEnio. Meno gradi giorno vuol dire un mese più caldo.", ""]
    if con_normale:
        righe += [f"| Capoluogo | Temperatura media | Scarto dal {per} | Scarto dal 1991–2020 | GG del mese | "
                  f"Media GG {per} | Scarto GG |", "|---|---:|---:|---:|---:|---:|---:|"]
    else:
        righe += [f"| Capoluogo | Temperatura media | Scarto dal {per} | GG del mese | Media GG {per} | Scarto GG |",
                  "|---|---:|---:|---:|---:|---:|"]
    for v in voci:
        s_gg = f"{_segno(v['dgg'])} %" if v["dgg"] is not None else "—"
        s_n = (f" {_segno(v['dn'], 1)} °C |" if v["dn"] is not None else " — |") if con_normale else ""
        righe.append(f"| {v['nome']} | {_num(v['t'], 1)} °C | {_segno(v['dt'], 1)} °C |{s_n} {_num(v['gg'])} | "
                     f"{_num(v['media_gg'])} | {s_gg} |")
    if note:
        righe += _note_freddo(per, con_normale)
    return righe + [""]


def _note_freddo(per: str, con_normale: bool) -> list[str]:
    # (11/11/2026, Paolo) sotto la tabella: dove cercare gli altri comuni
    righe = ["", f"**Il tuo comune non c'è?** Cercalo in Clima e meteo › Dati climatici e scarica temperatura e gradi "
                 f"giorno giorno per giorno: {C.SITO_URL}/dati.html", "", FONTE_METEO]
    if con_normale:
        righe += ["", f"Lo scarto dal 1991–2020 somma lo scarto dalla media {per} e quanto lo stesso mese del {per} era "
                      "già diverso dal 1991–2020 nella serie del clima dal 1940 di EuGEnio (ERA5-Land), così non si "
                      f"confrontano fonti diverse. Il clima dal 1940 per ogni comune: {C.SITO_URL}/legge10.html"]
    return righe


def _tabella_freddo(anno: int, mese: int) -> list[str]:
    """Sezione dei gradi giorno e della temperatura del mese nei capoluoghi (11/11/2026): frase di sintesi, scarti in °C
    dalla media dell'archivio (periodo dichiarato: anni precedenti con almeno 25 giorni del mese) e dalla normale
    1991–2020. Senza capoluoghi nessuna lettura del giornaliero (con l'archivio nazionale sarebbero milioni di righe)."""
    cap = _capoluoghi()
    if cap.empty:
        log.warning("Newsletter: nessun capoluogo in comuni.parquet (colonna «capoluogo» mancante o vuota): "
                    "sezione dei gradi giorno saltata")
        return []
    return _righe_freddo(_voci_freddo(cap, anno, mese), anno, mese)


# ---------------------------------------------------------------------------------------------- prezzi
def _valore(ind: dict, lotto: str, variante: str, anno: int, mese: int):
    try:
        return ind["lotti"][lotto]["varianti"][variante][str(anno)][mese - 1]
    except (KeyError, IndexError, TypeError):
        return None


def _cella(ind: dict, lotto: str, variante: str, anno: int, mese: int, dec: int) -> str:
    """Valore del mese con la variazione sullo stesso mese dell'anno prima, «236,89 (+95 %)», o «—»."""
    ora, prima = _valore(ind, lotto, variante, anno, mese), _valore(ind, lotto, variante, anno - 1, mese)
    if ora is None:
        return "—"
    testo = _num(ora, dec)
    if prima:
        testo += f" ({_segno(100 * (ora / prima - 1))} %)"
    return testo


def _normale(s: str) -> str:
    return "".join(ch for ch in s.split("/")[0].lower() if ch.isalpha())


def _lotti_regioni(ind: dict, regioni_nomi: list[str] | None) -> list[str]:
    """(14/11/2026) Lotti Consip delle regioni scelte dall'iscritto, riconosciuti dal nome del lotto («Lotto 6: Emilia
    Romagna»); il lotto predefinito se nessuna regione corrisponde."""
    scelti = []
    for nome in regioni_nomi or []:
        n = _normale(nome)
        for k, lo in ind.get("lotti", {}).items():
            if n and n in _normale(lo.get("nome", "").replace("/", " ")) and k not in scelti:
                scelti.append(k)
    return scelti or [ind.get("lotto_predefinito", "")]


def _tabella_prezzi(anno: int, mese: int, file: Path | None = None,
                    regioni_nomi: list[str] | None = None) -> list[str]:
    """Sezione «Indici dei prezzi» (11/11/2026, Paolo): dal file del sito scritto ogni notte dal worker
    (/sito/dati/prezzi/indici.json: listini Intercent-ER e Consip, PSV ARERA, PFOR; mai PUN né TTF). Energia elettrica:
    Intercent-ER lotti 1 e 2 e Consip con il lotto predefinito (Emilia-Romagna), una riga per offerta e le fasce F1, F2,
    F3 in colonna; gas: listini Intercent-ER (lotto predefinito, primo uso), PSV e PFOR. Vuota se il file manca."""
    f = Path(file or Path(C.SITO_DATI) / "prezzi" / "indici.json")
    try:
        dati = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        log.info("Newsletter: indici dei prezzi non trovati (%s)", f)
        return []
    sezioni = {s["id"]: s["indici"] for s in dati.get("sezioni", [])}
    mese_anno = f"{MESI[mese - 1]} {anno}"
    righe = [f"## Indici dei prezzi di {mese_anno}", "",
             f"Prezzi pubblicati dalle centrali di committenza e indici del gas, IVA esclusa; tra parentesi la variazione su "
             f"{MESI[mese - 1]} {anno - 1}.", ""]
    el = []
    for ind in sezioni.get("elettricita", []):
        lotti = ["1", "2"] if ind.get("centrale") == "Intercent-ER" else _lotti_regioni(ind, regioni_nomi)
        for lo in lotti:
            if lo not in ind.get("lotti", {}):
                continue
            nome = f"{ind.get('centrale', '')} – {ind['lotti'][lo]['nome']}"
            el.append(f"| {nome} | " + " | ".join(_cella(ind, lo, fa, anno, mese, 2) for fa in ("F1", "F2", "F3")) + " |")
    if el:
        righe += ["| Energia elettrica (€/MWh) | F1 | F2 | F3 |", "|---|---:|---:|---:|"] + el + [""]
    gas = []
    for ind in sezioni.get("gas", []):
        # il lotto predefinito, o il primo che ha il valore del mese (il lotto 1 del gas segue l'anno termico: da
        # ottobre vale la convenzione nuova, che può non avere ancora il listino)
        lotti = [ind.get("lotto_predefinito", "")] + [k for k in ind.get("lotti", {}) if k != ind.get("lotto_predefinito")]
        scelta = [(lo, v) for lo in lotti if lo in ind.get("lotti", {}) for v in ind["lotti"][lo]["varianti"]]
        if not scelta:
            continue
        lo, v = next(((lo, v) for lo, v in scelta if _valore(ind, lo, v, anno, mese) is not None), scelta[0])
        dec = ind.get("decimali") if isinstance(ind.get("decimali"), int) else 4 if ind.get("unita") == "€/Smc" else 2
        nome = ind["titolo"] if not ind.get("centrale") else f"{ind['centrale']} – {ind['lotti'][lo]['nome']}, {v.lower()}"
        gas.append(f"| {nome} | {ind['unita']} | {_cella(ind, lo, v, anno, mese, dec)} |")
    if gas:
        righe += ["| Gas naturale | Unità | Valore |", "|---|---|---:|"] + gas + [""]
    if not el and not gas:
        return []
    righe += ["Fonti: Intercent-ER e Consip (listini e corrispettivi delle convenzioni), ARERA (PSV day-ahead, CC BY-SA 4.0); "
              "PFOR,t ricostruito da EuGEnio con il metodo ARERA.", "",
              f"Tutti i mesi, tutti i lotti e il **confronto delle convenzioni sui tuoi consumi**: {C.SITO_URL}/indici-prezzi.html",
              ""]
    return righe


# ---------------------------------------------------------------------------------------------- mensile
def testo_mensile(anno: int, mese: int, invio: dt.date | None = None) -> tuple[str, str]:
    """Oggetto e testo Markdown del numero sui dati del mese `mese`/`anno`, inviato il giorno `invio` (oggi)."""
    invio = invio or dt.date.today()
    nome_mese = f"{MESI[mese - 1]} {anno}"
    righe = [f"# EuGEnio, {nome_mese}", ""]
    if _primo_numero(invio):
        righe += _benvenuto()
    righe += _tabella_prezzi(anno, mese)          # (11/11/2026) gli indici dei prezzi in cima
    freddo = _tabella_freddo(anno, mese)
    if freddo:
        righe += [f"## Il freddo di {nome_mese}, comune per comune", ""] + freddo
    righe += novita_tra(_numero_precedente(invio), invio)
    righe += _piede()
    return f"EuGEnio – prezzi e freddo di {nome_mese}", "\n".join(righe)


# ---------------------------------------------------------------------------------------------- invio
def _campagna(lista: int, nome: str, oggetto: str, corpo: str) -> int | None:
    if not (C.LISTMONK_API_UTENTE and C.LISTMONK_API_TOKEN and lista):
        log.info("Newsletter: listmonk non configurato (%s)", nome)
        return None
    h = {"Authorization": f"token {C.LISTMONK_API_UTENTE}:{C.LISTMONK_API_TOKEN}"}
    r = httpx.post(f"{C.LISTMONK_URL}/api/campaigns", headers=h, timeout=30, json={
        "name": nome, "subject": oggetto, "lists": [lista], "type": "regular",
        "content_type": "markdown", "body": corpo})
    r.raise_for_status()
    cid = r.json()["data"]["id"]
    if C.NOTIZIARIO_INVIO_AUTOMATICO:
        httpx.put(f"{C.LISTMONK_URL}/api/campaigns/{cid}/status", headers=h, json={"status": "running"},
                  timeout=30).raise_for_status()
    else:
        avvisi.invia(f"newsletter in bozza: {oggetto}", f"Campagna {cid}: rileggerla e avviarla da {C.NOTIZIE_URL}/admin")
    log.info("Newsletter %s: campagna %s %s", nome, cid, "avviata" if C.NOTIZIARIO_INVIO_AUTOMATICO else "in bozza")
    return cid


def _mese_scorso(invio: dt.date) -> tuple[int, int]:
    ieri = invio.replace(day=1) - dt.timedelta(days=1)
    return ieri.year, ieri.month


def mensile(anno: int | None = None, mese: int | None = None, invio: dt.date | None = None):
    """Numero mensile. Con i messaggi personali (NOTIZIE_PERSONALI, predefinito) uno per iscritto con le sue regioni;
    altrimenti la campagna unica di prima."""
    invio = invio or dt.date.today()
    if anno is None:
        anno, mese = _mese_scorso(invio)
    if C.NOTIZIE_PERSONALI and L.attivo():
        return mensile_personale(anno, mese, invio)
    return _campagna(C.LISTA_MENSILE, f"Mensile {anno}-{mese:02d}", *testo_mensile(anno, mese, invio))


# ============================================================================================== servizi personali
# (14/11/2026, decisione di Paolo) tre servizi separati: mensile per regione, settimanale con le previsioni di fino a 5
# comuni, avvisi meteo del giorno dopo. Un messaggio per iscritto (API transazionale di listmonk), con i collegamenti per
# cambiare le scelte e per cancellarsi da quel servizio (anche con un clic dal programma di posta).
GIORNI = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
GIORNI_BREVI = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]
NOMI_SERVIZIO = {"mensile": "la newsletter mensile", "settimanale": "le previsioni settimanali",
                 "avvisi": "gli avvisi meteo"}
BOLLETTINO_PC = "https://mappe.protezionecivile.gov.it/it/mappe-rischi/bollettino-di-criticita/"
CSS = ("body{margin:0;padding:0;background:#ffffff;color:#111111;font-family:Helvetica,Arial,sans-serif;font-size:15px;"
       "line-height:1.5}.eugenio{max-width:680px;margin:0 auto;padding:16px}h1{font-size:22px;margin:0 0 12px}"
       "h2{font-size:18px;margin:24px 0 8px}a{color:#1A3F8F}table{border-collapse:collapse;margin:8px 0 12px;"
       "font-size:13px}th,td{border:1px solid #111111;padding:4px 6px}th{font-weight:bold;text-align:left}"
       "td{text-align:right}td:first-child{text-align:left}.piede{font-size:12px;color:#444444;margin-top:24px}")


def html(md_testo: str, titolo: str) -> str:
    """Markdown → HTML dell'email (tabelle comprese), sobrio e leggibile anche in stampa."""
    import markdown
    corpo = markdown.markdown(md_testo, extensions=["tables", "sane_lists"])
    t = titolo.replace("&", "&amp;").replace("<", "&lt;")
    return (f"<!doctype html><html lang=\"it\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" "
            f"content=\"width=device-width\"><title>{t}</title><style>{CSS}</style></head><body><div class=\"eugenio\">"
            f"{corpo}</div></body></html>")


def _piede_personale(sid: int, lista: int, servizio: str) -> list[str]:
    from . import preferenze_email as PE
    return ["", "---", "",
            f"Cambia servizi, regioni e comuni: {PE.url_preferenze(sid)}", "",
            f"Non vuoi più ricevere {NOMI_SERVIZIO[servizio]}? Cancellati con un clic: {PE.url_cancella(sid, lista)}", "",
            "EuGEnio è un servizio gratuito di Stato Critico (statocritico.it), con codice aperto."]


# ---------------------------------------------------------------------------------------------- registro degli invii
def _registro(chiave: str) -> Path:
    d = C.DATI / "invii_email"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{chiave}.txt"


def _gia_inviati(chiave: str) -> set[int]:
    p = _registro(chiave)
    return {int(x) for x in p.read_text().split()} if p.exists() else set()


def _segna(chiave: str, sid: int) -> None:
    with _registro(chiave).open("a") as f:
        f.write(f"{sid}\n")


def _pulisci_registro(giorni: int = 120) -> None:
    d = C.DATI / "invii_email"
    if not d.exists():
        return
    limite = dt.datetime.now().timestamp() - giorni * 86400
    for f in d.glob("*.txt"):
        if f.stat().st_mtime < limite:
            f.unlink(missing_ok=True)


def invia_personali(chiave: str, servizio: str, lista: int, costruisci) -> dict:
    """Un messaggio per ogni iscritto attivo della lista. `costruisci(iscritto)` → (oggetto, testo Markdown) o None
    (niente da mandare). Il registro `chiave` evita i doppioni se il worker riparte a metà."""
    from . import preferenze_email as PE
    modello = L.modello_tx()
    fatti = _gia_inviati(chiave)
    esito = {"inviati": 0, "saltati": 0, "errori": []}
    for s in L.destinatari(lista):
        sid = int(s["id"])
        if sid in fatti:
            continue
        try:
            r = costruisci(s)
            if r is None:
                esito["saltati"] += 1
                continue
            oggetto, md_testo = r
            md_testo += "\n" + "\n".join(_piede_personale(sid, lista, servizio))
            L.messaggio(sid, modello, oggetto, html(md_testo, oggetto), via=PE.url_cancella_un_clic(sid, lista))
            _segna(chiave, sid)
            esito["inviati"] += 1
        except Exception as e:      # un iscritto che non va non ferma gli altri
            log.exception("Email %s: iscritto %s non servito", chiave, sid)
            esito["errori"].append(f"{sid}: {type(e).__name__}: {e}")
        time.sleep(C.NOTIZIE_PAUSA_S)
    log.info("Email %s: %s", chiave, {k: (len(v) if isinstance(v, list) else v) for k, v in esito.items()})
    if esito["errori"]:
        avvisi.invia(f"email {chiave}: {len(esito['errori'])} non spedite",
                     "\n".join(esito["errori"][:50]))
    _pulisci_registro()
    return esito


# ---------------------------------------------------------------------------------------------- mensile per regione
def _capoluoghi_italia() -> pd.DataFrame:
    """Capoluoghi di tutte le regioni (comuni.parquet intero, non solo le REGIONI servite), con i secondi capoluoghi."""
    cm = pd.read_parquet(C.DATI / "comuni.parquet")
    cm["istat"] = cm.istat.astype(str)
    if "capoluogo" not in cm:
        return cm.head(0)
    return cm[cm.capoluogo.fillna(False).astype(bool) | cm.istat.isin(CO_CAPOLUOGHI)].sort_values("nome")


def _nomi_regioni(cap: pd.DataFrame) -> dict[str, str]:
    if "regione_cod" not in cap or "regione" not in cap:
        return {}
    return {str(k): str(v).split("/")[0] for k, v in cap.groupby("regione_cod").regione.first().items()}


def _tabella_regioni(voci: list[dict], nomi: dict[str, str], anno: int, mese: int) -> list[str]:
    """Indicatori del mese regione per regione: media dei capoluoghi di provincia di ogni regione."""
    per_reg: dict[str, list[dict]] = {}
    for v in voci:
        if v.get("regione_cod"):
            per_reg.setdefault(str(v["regione_cod"]), []).append(v)
    if not per_reg:
        return []
    per = _periodo(min(v["da"] for v in voci), max(v["a"] for v in voci))
    con_normale = any(v["dn"] is not None for v in voci)
    righe = [f"Media dei capoluoghi di provincia di ogni regione, {MESI[mese - 1]} {anno} confrontato con lo stesso "
             f"mese del {per}{' e con il 1991–2020' if con_normale else ''}. Gradi giorno base 20 °C di tutti i giorni "
             "del mese.", ""]
    if con_normale:
        righe += [f"| Regione | Temperatura media | Scarto dal {per} | Scarto dal 1991–2020 | GG del mese | Scarto GG |",
                  "|---|---:|---:|---:|---:|---:|"]
    else:
        righe += [f"| Regione | Temperatura media | Scarto dal {per} | GG del mese | Scarto GG |",
                  "|---|---:|---:|---:|---:|"]
    for cod in sorted(per_reg, key=lambda c: nomi.get(c, c)):
        vv = per_reg[cod]
        n = len(vv)
        t, d = sum(v["t"] for v in vv) / n, sum(v["dt"] for v in vv) / n
        gg = sum(v["gg"] for v in vv) / n
        dgg = [v["dgg"] for v in vv if v["dgg"] is not None]
        s_gg = f"{_segno(sum(dgg) / len(dgg))} %" if dgg else "—"
        s_n = ""
        if con_normale:
            dn = [v["dn"] for v in vv if v["dn"] is not None]
            s_n = f" {_segno(sum(dn) / len(dn), 1)} °C |" if len(dn) == n else " — |"
        righe.append(f"| {nomi.get(cod, cod)} | {_num(t, 1)} °C | {_segno(d, 1)} °C |{s_n} {_num(gg)} | {s_gg} |")
    return righe + [""]


def testo_mensile_regioni(anno: int, mese: int, invio: dt.date, regioni: list[str], voci: list[dict],
                          nomi: dict[str, str], file_prezzi: Path | None = None) -> tuple[str, str]:
    """Numero mensile personale: prezzi nazionali (Consip con i lotti delle regioni scelte), indicatori regione per
    regione, i capoluoghi delle regioni scelte, novità."""
    nome_mese = f"{MESI[mese - 1]} {anno}"
    scelte = [r for r in regioni if r in nomi]
    righe = [f"# EuGEnio, {nome_mese}", ""]
    if _primo_numero(invio):
        righe += _benvenuto()
    righe += _tabella_prezzi(anno, mese, file_prezzi, [nomi[r] for r in scelte])
    reg = _tabella_regioni(voci, nomi, anno, mese)
    if reg:
        righe += [f"## Il freddo di {nome_mese}, regione per regione", ""] + reg
    for r in scelte:
        vv = [v for v in voci if str(v.get("regione_cod")) == r]
        if vv:
            righe += [f"## {nomi[r]}: i capoluoghi", ""] + _righe_freddo(vv, anno, mese, note=False)
    if not scelte:
        righe += [f"Scegli fino a {C.EMAIL_MAX_REGIONI} regioni per avere anche i loro capoluoghi uno per uno: trovi il "
                  "collegamento in fondo all'email.", ""]
    if voci:
        per = _periodo(min(v["da"] for v in voci), max(v["a"] for v in voci))
        righe += _note_freddo(per, any(v["dn"] is not None for v in voci)) + [""]
    righe += novita_tra(_numero_precedente(invio), invio)
    titolo = " e ".join(nomi[r] for r in scelte[:2]) + (" e altre" if len(scelte) > 2 else "")
    oggetto = f"EuGEnio – prezzi e freddo di {nome_mese}" + (f" ({titolo})" if titolo else "")
    return oggetto, "\n".join(righe)


def mensile_personale(anno: int, mese: int, invio: dt.date | None = None) -> dict:
    invio = invio or dt.date.today()
    cap = _capoluoghi_italia()
    voci = _voci_freddo(cap, anno, mese) if not cap.empty else []
    nomi = _nomi_regioni(cap)

    def costruisci(s):
        return testo_mensile_regioni(anno, mese, invio, L.scelte(s)["regioni"], voci, nomi)
    return invia_personali(f"mensile-{anno}-{mese:02d}", "mensile", C.LISTA_MENSILE, costruisci)


# ---------------------------------------------------------------------------------------------- settimanale
def _fmt(x, dec=0, unita=""):
    if x is None or (isinstance(x, float) and x != x):
        return "—"
    return f"{_num(x, dec)}{(' ' + unita) if unita else ''}"


def _gg_stessi_giorni(istat: str, giorni: list[dt.date]) -> tuple[float, int, int] | None:
    """Media dei gradi giorno degli stessi giorni dell'anno negli anni dell'archivio (anni completi), o None."""
    try:
        g = meteo.storico_giornaliero(istat)
    except (FileNotFoundError, OSError, ValueError, KeyError):
        return None
    if g.empty or "gg20" not in g:
        return None
    d = pd.to_datetime(g.data)
    md = {(x.month, x.day) for x in giorni}
    sel = g[[(m, dd) in md for m, dd in zip(d.dt.month, d.dt.day)]].assign(anno=d.dt.year)
    sel = sel[sel.anno < giorni[0].year]
    per = sel.groupby("anno").gg20.agg(["sum", "size"])
    per = per[per["size"] == len(md)]
    if per.empty:
        return None
    return float(per["sum"].mean()), int(per.index.min()), int(per.index.max())


def testo_settimanale(lunedi: dt.date, comuni: list[dict], prev: dict[str, pd.DataFrame]) -> tuple[str, str] | None:
    """Previsioni da lunedì a domenica per i comuni dell'iscritto: [{"istat", "nome", "provincia"}]."""
    from . import meteo_email as ME
    giorni = [lunedi + dt.timedelta(days=i) for i in range(7)]
    domenica = giorni[-1]
    righe = [f"# EuGEnio, previsioni dal {lunedi.day} {MESI[lunedi.month - 1]} al {domenica.day} "
             f"{MESI[domenica.month - 1]}", "",
             "Temperature minime e massime, pioggia (neve fusa compresa), neve fresca, raffica più forte e gradi giorno "
             "(base 20 °C) previsti giorno per giorno. Sono previsioni: più i giorni sono lontani, più possono cambiare.",
             ""]
    trovati = 0
    for c in comuni:
        p = prev.get(c["istat"])
        if p is None or p.empty:
            continue
        sett = p[p.data.isin(giorni)]
        if sett.empty:
            continue
        trovati += 1
        nome = f"{c['nome']} ({c['provincia']})" if c.get("provincia") else c["nome"]
        righe += [f"## {nome}", "", "| Giorno | Min | Max | Pioggia | Neve | Raffica | GG | Attenzione |",
                  "|---|---:|---:|---:|---:|---:|---:|---|"]
        for r in sett.itertuples():
            nota = ", ".join({"pioggia": "pioggia forte", "neve": "neve", "vento": "vento molto forte"}[x]
                             for x in ME.superamenti(r._asdict()))
            righe.append(f"| {GIORNI_BREVI[r.data.weekday()]} {r.data.day} | {_fmt(r.tmin, 0, '°C')} | "
                         f"{_fmt(r.tmax, 0, '°C')} | {_fmt(r.pioggia, 0, 'mm')} | {_fmt(r.neve, 0, 'cm')} | "
                         f"{_fmt(r.raffica, 0, 'km/h')} | {_fmt(r.gg20, 1)} | {nota} |")
        gg = float(sett.gg20.sum())
        frase = f"Gradi giorno previsti nella settimana: **{_num(gg)}**"
        if len(sett) == 7:
            n = _gg_stessi_giorni(c["istat"], giorni)
            if n and n[0] > 1:
                frase += (f"; negli stessi giorni del {_periodo(n[1], n[2])} in media {_num(n[0])} "
                          f"({_segno(100 * (gg / n[0] - 1))} %)")
        righe += ["", frase + ".", ""]
    if not trovati:
        return None
    righe += ["La colonna «Attenzione» segna i giorni che superano le soglie degli avvisi meteo di EuGEnio (pioggia "
              f"forte, neve, vento molto forte); per riceverli il giorno prima iscriviti agli avvisi meteo.",
              "", f"Le previsioni non sostituiscono le allerte della Protezione Civile e degli enti pubblici.",
              "", ME.FONTE, ""]
    oggetto = (f"EuGEnio – previsioni dal {lunedi.day} al {domenica.day} {MESI[domenica.month - 1]}: "
               + ", ".join(c["nome"] for c in comuni[:3]) + (" e altri" if len(comuni) > 3 else ""))
    return oggetto, "\n".join(righe)


def _comuni_di(s: dict, cm: pd.DataFrame) -> list[dict]:
    out = []
    for i in L.scelte(s)["comuni"]:
        if i in cm.index:
            out.append({"istat": i, "nome": str(cm.nome[i]), "provincia": str(cm.provincia[i] or "")})
    return out


def _comuni_nomi() -> pd.DataFrame:
    cm = pd.read_parquet(C.DATI / "comuni.parquet", columns=["istat", "nome", "provincia"])
    cm["istat"] = cm.istat.astype(str)
    return cm.set_index("istat")


def settimanale(oggi: dt.date | None = None) -> dict | None:
    from . import meteo_email as ME
    oggi = oggi or dt.date.today()
    lunedi = oggi + dt.timedelta(days=(7 - oggi.weekday()) % 7 or 7)
    lista = L.lista(C.NOME_LISTA_SETTIMANALE, C.LISTA_SETTIMANALE)
    iscritti = L.destinatari(lista)
    if not iscritti:
        log.info("Previsioni settimanali: nessun iscritto")
        return None
    cm = _comuni_nomi()
    tutti = sorted({c for s in iscritti for c in L.scelte(s)["comuni"]})
    prev = ME.previsioni(tutti, (lunedi - oggi).days + 8)
    return invia_personali(f"settimanale-{lunedi}", "settimanale", lista,
                           lambda s: testo_settimanale(lunedi, _comuni_di(s, cm), prev))


# ---------------------------------------------------------------------------------------------- avvisi meteo
def _descrivi_avviso(tipo: str, g: dict) -> str:
    if tipo == "pioggia":
        return (f"pioggia forte, {_num(g['pioggia'])} mm nelle 24 ore (al massimo {_num(g['pioggia_1h'])} mm in "
                "un'ora)")
    if tipo == "neve":
        return f"neve, {_num(g['neve'])} cm di neve fresca"
    return f"vento molto forte, raffiche fino a {_num(g['raffica'])} km/h"


def testo_avviso(domani: dt.date, voci: list[tuple[dict, list[str], dict]]) -> tuple[str, str] | None:
    """Avviso per domani: voci = [(comune, tipi superati tra quelli scelti, giorno di previsione)]."""
    from . import meteo_email as ME
    from . import preferenze_email as PE
    voci = [v for v in voci if v[1]]
    if not voci:
        return None
    quando = f"{GIORNI[domani.weekday()]} {domani.day} {MESI[domani.month - 1]}"
    righe = [f"# Avviso meteo EuGEnio per domani, {quando}", "",
             f"**Non è un'allerta.** {PE.AVVERTENZA_AVVISI}", "",
             f"Le previsioni di oggi per domani superano le soglie che hai scelto:", ""]
    for c, tipi, g in voci:
        nome = f"{c['nome']} ({c['provincia']})" if c.get("provincia") else c["nome"]
        righe.append(f"- **{nome}**: " + "; ".join(_descrivi_avviso(t, g) for t in tipi) + ".")
    s = PE.soglie()
    righe += ["", "Soglie degli avvisi: pioggia forte, " + s["pioggia"] + "; neve, " + s["neve"] + "; vento molto forte, "
              + s["vento"] + ". Sono previsioni del modello per il punto del comune: in altre zone dello stesso comune "
              "e nelle ore successive i valori possono essere diversi.", "",
              f"Le allerte ufficiali le emettono la Protezione Civile e le Regioni: bollettino nazionale di criticità "
              f"{BOLLETTINO_PC}; segui anche il sito di allerta della tua Regione, il tuo Comune e IT-alert.", "",
              ME.FONTE, ""]
    tipi_tutti = []
    for _, tipi, _ in voci:
        tipi_tutti += [t for t in tipi if t not in tipi_tutti]
    nomi_t = {"pioggia": "pioggia forte", "neve": "neve", "vento": "vento molto forte"}
    oggetto = (f"EuGEnio – avviso meteo per domani: {', '.join(nomi_t[t] for t in tipi_tutti)} a "
               + ", ".join(c["nome"] for c, _, _ in voci[:3]) + (" e altri" if len(voci) > 3 else ""))
    return oggetto, "\n".join(righe)


def avvisi_meteo(oggi: dt.date | None = None) -> dict | None:
    from . import meteo_email as ME
    oggi = oggi or dt.date.today()
    domani = oggi + dt.timedelta(days=1)
    lista = L.lista(C.NOME_LISTA_AVVISI, C.LISTA_AVVISI)
    iscritti = [s for s in L.destinatari(lista) if L.scelte(s)["avvisi"] and L.scelte(s)["comuni"]]
    if not iscritti:
        log.info("Avvisi meteo: nessun iscritto")
        return None
    cm = _comuni_nomi()
    tutti = sorted({c for s in iscritti for c in L.scelte(s)["comuni"]})
    prev = ME.previsioni(tutti, 3)
    giorni = {i: ME.giorno(p, domani) for i, p in prev.items()}

    def costruisci(s):
        scelti = set(L.scelte(s)["avvisi"])
        voci = []
        for c in _comuni_di(s, cm):
            g = giorni.get(c["istat"])
            if g:
                voci.append((c, [t for t in ME.superamenti(g) if t in scelti], g))
        return testo_avviso(domani, voci)
    # gli iscritti senza superamenti non vengono segnati nel registro: se il worker riparte, si ricontrollano
    return invia_personali(f"avvisi-{domani}", "avvisi", lista, costruisci)
