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
import tomllib
from pathlib import Path

import httpx
import pandas as pd

from . import avvisi, config as C, meteo

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


def _tabella_freddo(anno: int, mese: int) -> list[str]:
    """Sezione dei gradi giorno e della temperatura del mese nei capoluoghi (11/11/2026): frase di sintesi, scarti in °C
    dalla media dell'archivio (periodo dichiarato: anni precedenti con almeno 25 giorni del mese) e dalla normale
    1991–2020. Senza capoluoghi nessuna lettura del giornaliero (con l'archivio nazionale sarebbero milioni di righe)."""
    cap = _capoluoghi()
    if cap.empty:
        log.warning("Newsletter: nessun capoluogo in comuni.parquet (colonna «capoluogo» mancante o vuota): "
                    "sezione dei gradi giorno saltata")
        return []
    # solo i capoluoghi (filtro sul parquet): il giornaliero nazionale non si carica mai tutto
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
        storico = _scarto_storico(str(r.istat), getattr(r, "regione_cod", None), mese, da, fino)
        voci.append({"nome": r.nome, "gg": gg, "media_gg": media_gg, "t": t, "dt": t - media_t,
                     "dn": None if storico is None else t - media_t + storico,
                     "dgg": 100 * (gg / media_gg - 1) if media_gg > 1 else None, "da": da, "a": fino})
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
    # (11/11/2026, Paolo) sotto la tabella: dove cercare gli altri comuni
    righe += ["", f"**Il tuo comune non c'è?** Cercalo in Clima e meteo › Dati climatici e scarica temperatura e gradi "
                  f"giorno giorno per giorno: {C.SITO_URL}/dati.html", "", FONTE_METEO]
    if con_normale:
        righe += ["", f"Lo scarto dal 1991–2020 somma lo scarto dalla media {per} e quanto lo stesso mese del {per} era "
                      "già diverso dal 1991–2020 nella serie del clima dal 1940 di EuGEnio (ERA5-Land), così non si "
                      f"confrontano fonti diverse. Il clima dal 1940 per ogni comune: {C.SITO_URL}/legge10.html"]
    return righe + [""]


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


def _tabella_prezzi(anno: int, mese: int, file: Path | None = None) -> list[str]:
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
        lotti = ["1", "2"] if ind.get("centrale") == "Intercent-ER" else [ind.get("lotto_predefinito", "")]
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


def mensile(anno: int | None = None, mese: int | None = None, invio: dt.date | None = None) -> int | None:
    invio = invio or dt.date.today()
    if anno is None:
        ieri = invio.replace(day=1) - dt.timedelta(days=1)
        anno, mese = ieri.year, ieri.month
    return _campagna(C.LISTA_MENSILE, f"Mensile {anno}-{mese:02d}", *testo_mensile(anno, mese, invio))
