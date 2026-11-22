"""File del sito per la pagina «Carichi elettrici» (Statistiche, sperimentale, 20/11/2026, richiesta di Paolo).

  costruisci_carichi(archivio: Path, uscita: Path) -> dict
      legge l'archivio mensile (formato sotto) e scrive in `uscita` i file statici della pagina carichi.html:
        indice.json            zone, voci e colori, fonti, elenco dei mesi con l'istante iniziale (UTC), il numero di
                               quarti d'ora e i cambi d'ora legale; la pagina lo legge per primo
        carico_AAAA-MM.json    potenza richiesta [MW, interi] per quarto d'ora, una serie per zona di mercato + Italia
                               (dal 22/11/2026 Italia = somma degli interi delle zone, dove ci sono tutte)
        fonti_AAAA-MM.json     potenza per fonte [MW, interi] per quarto d'ora, solo Italia (Terna non la divide per zona)
      La pagina scarica solo i mesi del periodo scelto. Il worker del server lo chiama in una cartella nuova e la
      pubblica in sito/dati/carichi/ (vedi README della fase 15).

  scarica(archivio: Path, mesi: list[tuple[int, int]], dataset=DATASET, rifai=False) -> dict
      scarica dal Download Center di Terna (dati.terna.it, nessuna chiave) i mesi che mancano nell'archivio;
      `rifai` riscarica anche quelli presenti (il mese in corso cresce ogni giorno).

Decisione di Paolo (20/11/2026): i dati di Terna si caricano sul sito per le elaborazioni ma **non si scaricano**
(nessun CSV, Excel o JSON da scaricare; al più le immagini dei grafici); i file costruiti non vanno nel repository.

Fonte della potenza richiesta: Terna «Fabbisogno Italia» (Download Center, dataset TotalLoad): carico effettivo per
zona di mercato e per l'Italia, ogni 15 minuti. Paolo aveva chiesto la potenza ricalcolata dall'energia scambiata in
borsa, ma i dati del GME sono solo per uso interno e non si mostrano sul sito: se arrivasse la licenza basta cambiare
FONTE_CARICO (punto unico) e scrivere nell'archivio un dataset con le stesse colonne.

Formato dell'archivio (una cartella, un file per dataset e mese):
  <archivio>/<Dataset>_<AAAA>-<MM>.json = {"Columns": {nome: tipo, …}, "Data": [[…], …]}
  cioè la risposta del Download Center così com'è («Count» e gli altri campi sono ignorati). Le colonne si riconoscono
  per nome:
    TotalLoad            Date, «Total Load [MW]», «Bidding Zone» (Italy, North, Centre-North, Centre-South, South,
                         Calabria, Sicily, Sardinia)
    ActualGeneration     Date, «Actual Generation» [GW medi nel quarto d'ora o nell'ora], «Primary Source» (Thermal,
                         Hydro, Wind, Geothermal, Photovoltaic, Self-consumption)
    RenewableGeneration  Date, «Renewable Generation» [GW], «Energy Source» (Biomass, Hydro, Wind, Geothermal,
                         Photovoltaic)
  Oppure (20/11/2026, unione con il worker) l'archivio Parquet del server, TERNA_DATI/serie (servizio/terna.py della
  fase 4, formato nel README della fase 4, § «Dati di Terna»): <archivio>/<serie>/<AAAA-MM>.parquet con `istante` già in
  UTC (ora ripetuta di ottobre già risolta), `zona`/`fonte` con i nomi inglesi di Terna e i valori `carico_mw` (serie
  carico_totale = TotalLoad) ed `energia_gwh` (produzione = ActualGeneration, rinnovabili = RenewableGeneration; al
  passo di 15 minuti GW medi). Si riconosce dalla cartella `carico_totale/`; il resto della costruzione è lo stesso.
  Date: millisecondi dal 1/1/0001 in ora locale italiana (come il Download Center), oppure testo ISO
  «AAAA-MM-GGTHH:MM[:SS]» in ora locale, oppure ISO con il fuso («…Z», «…+01:00»). Nel giorno del ritorno all'ora
  solare le ore 02:00–02:45 compaiono due volte con la stessa data locale: la prima volta valgono come ora legale
  (UTC+2), la seconda come ora solare (UTC+1). I dati orari (la generazione fino al 2024) valgono per i quattro quarti
  d'ora dell'ora.

Fonti nel grafico delle barre al 100 % (solo Italia; colori della pagina «Produzione e consumi di elettricità»):
  fv, eol, geo, idro, bio   dalla produzione rinnovabile (RenewableGeneration, comprende l'energia autoconsumata;
                            l'idroelettrico comprende i pompaggi, che Terna qui non separa)
  termo                     per differenza: produzione totale (ActualGeneration, autoconsumi compresi) meno le
                            rinnovabili; se manca la produzione rinnovabile, quella di ActualGeneration e niente
                            bioenergie (restano nel termoelettrico)
  saldo                     per differenza: potenza richiesta dell'Italia meno la produzione = saldo con l'estero meno
                            i consumi dei pompaggi e degli accumuli (può essere negativo)

  python -m elettricita.carichi scarica <archivio> --da 2025-11 [--a 2026-11] [--rifai-ultimo]
  python -m elettricita.carichi costruisci <archivio> <uscita>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import re
import time
import urllib.request
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

log = logging.getLogger("elettricita.carichi")

ROMA = ZoneInfo("Europe/Rome")
UTC = dt.timezone.utc
QUARTO = dt.timedelta(minutes=15)
EPOCA_NET = dt.datetime(1, 1, 1)          # le date del Download Center: millisecondi da qui, ora locale

URL = "https://dati.terna.it/api/sitecore/dati/downloadcenter/recordsv2"
AGENTE = "EuGEnio (https://eugenio.statocritico.it) - carichi elettrici"
DATASET = ["TotalLoad", "ActualGeneration", "RenewableGeneration"]

# ----------------------------------------------------------------------------------------------- punto unico della fonte
# Potenza richiesta per zona. Per passare ad altra fonte (per esempio il GME, se arrivasse la licenza) basta cambiare
# qui il dataset dell'archivio, le colonne e il testo della fonte mostrato nella pagina.
FONTE_CARICO = {
    "dataset": "TotalLoad",
    "valore": "Total Load [MW]",
    "zona": "Bidding Zone",
    "scala": 1.0,                          # → MW
    "testo": "Terna S.p.A. – Fabbisogno Italia (carico effettivo «Total Load» per zona di mercato, ogni 15 minuti), "
             "Download Center di dati.terna.it; elaborazione EuGEnio",
}
FONTE_GENERAZIONE = ("Terna S.p.A. – Produzione effettiva per fonte («Actual Generation») e produzione rinnovabile "
                     "(«Renewable Generation»), solo Italia, Download Center di dati.terna.it; elaborazione EuGEnio")
SCALA_GENERAZIONE = 1000.0                 # GW medi → MW

# zone di mercato (configurazione in vigore dal 1° gennaio 2021, confermata nel 2026: vedi README); "ITA" = Italia
ZONE = [
    ("ITA", "Italia", "Italy"),
    ("NORD", "Nord", "North"),
    ("CNOR", "Centro-Nord", "Centre-North"),
    ("CSUD", "Centro-Sud", "Centre-South"),
    ("SUD", "Sud", "South"),
    ("CALA", "Calabria", "Calabria"),
    ("SICI", "Sicilia", "Sicily"),
    ("SARD", "Sardegna", "Sardinia"),
]
ZONA_DA_TERNA = {t.lower(): z for z, _, t in ZONE} | {n.lower(): z for z, n, _ in ZONE} | {z.lower(): z for z, _, _ in ZONE}

# voci del grafico delle fonti: stessi id e colori di VOCI in costruisci.py (pagina «Produzione e consumi»)
VOCI = [
    ("termo", "Termoelettrico tradizionale", "#8a8f99"),
    ("bio", "Bioenergie", "#f0912a"),
    ("idro", "Idroelettrico (con i pompaggi)", "#7cc7e0"),
    ("geo", "Geotermico", "#d4561c"),
    ("eol", "Eolico", "#a9c641"),
    ("fv", "Fotovoltaico", "#f7cb15"),
    ("saldo", "Saldo con l'estero, pompaggi e accumuli (per differenza)", "#c7a0c0"),
]
ATTUALE = {"thermal": "termo", "hydro": "idro", "wind": "eol", "geothermal": "geo", "photovoltaic": "fv",
           "self-consumption": "auto"}
RINNOVABILE = {"biomass": "bio", "hydro": "idro", "wind": "eol", "geothermal": "geo", "photovoltaic": "fv"}


# ----------------------------------------------------------------------------------------------- scaricamento
def _post(corpo: dict, tentativi: int = 3) -> dict:
    dati = json.dumps(corpo).encode()
    for i in range(tentativi):
        try:
            req = urllib.request.Request(URL, data=dati, headers={"Content-Type": "application/json", "User-Agent": AGENTE})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)
        except Exception:
            if i == tentativi - 1:
                raise
            time.sleep(5 * (i + 1))
    raise RuntimeError("irraggiungibile")


def scarica_mese(dataset: str, anno: int, mese: int, pausa: float = 1.0) -> dict:
    """Un mese di un dataset, pagina dopo pagina (50.000 righe per pagina; un mese di TotalLoad ≈ 23.000 righe)."""
    righe: list = []
    colonne: dict = {}
    pagina = 0
    while True:
        d = _post({"filterDataset": dataset, "filterYear": str(anno), "filterMonth": str(mese), "orderByColumn": "Date",
                   "orderByDir": "asc", "pageSize": "50000", "pageIndex": str(pagina), "db": "dati"})
        colonne = d.get("Columns") or colonne
        nuove = d.get("Data") or []
        righe += nuove
        if not nuove or len(righe) >= int(d.get("Count") or 0):
            break
        pagina += 1
        time.sleep(pausa)
    return {"Columns": colonne, "Count": len(righe), "Data": righe}


def scarica(archivio: Path, mesi: list[tuple[int, int]], dataset: list[str] | None = None, rifai: bool = False,
            pausa: float = 1.0) -> dict:
    """Scarica nell'archivio i mesi che mancano (con `rifai` anche quelli presenti). Una richiesta al secondo."""
    archivio.mkdir(parents=True, exist_ok=True)
    fatti: dict[str, list[str]] = {}
    for ds in dataset or DATASET:
        for a, m in mesi:
            f = archivio / f"{ds}_{a:04d}-{m:02d}.json"
            if f.exists() and not rifai:
                continue
            d = scarica_mese(ds, a, m, pausa)
            if d["Data"]:
                tmp = f.with_suffix(".tmp")
                tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
                tmp.replace(f)
                fatti.setdefault(ds, []).append(f"{a:04d}-{m:02d}")
            log.info("Terna %s %04d-%02d: %d righe", ds, a, m, len(d["Data"]))
            time.sleep(pausa)
    return fatti


def mesi_tra(da: str, a: str) -> list[tuple[int, int]]:
    y, m = map(int, da.split("-"))
    y2, m2 = map(int, a.split("-"))
    out = []
    while (y, m) <= (y2, m2):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


# ----------------------------------------------------------------------------------------------- lettura
def _data_locale(v) -> tuple[dt.datetime, bool]:
    """(istante, già_utc): istante naive in ora locale se già_utc è False, aware in UTC altrimenti."""
    if isinstance(v, (int, float)):
        return EPOCA_NET + dt.timedelta(milliseconds=v), False
    s = str(v).strip()
    m = re.match(r"/Date\((-?\d+)([+-]\d{4})?\)/", s)
    if m:                                  # /Date(ms dal 1970)/: istante assoluto
        return dt.datetime.fromtimestamp(int(m.group(1)) / 1000, UTC), True
    t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo:
        return t.astimezone(UTC), True
    return t, False


def _colonna(colonne: list[str], *nomi: str) -> int:
    basse = [c.lower() for c in colonne]
    for n in nomi:
        if n.lower() in basse:
            return basse.index(n.lower())
    for n in nomi:                         # nome parziale (per esempio «Total Load» senza l'unità)
        for i, c in enumerate(basse):
            if c.startswith(n.lower().split(" [")[0]):
                return i
    raise KeyError(f"colonna {nomi[0]!r} assente fra {colonne}")


def _leggi(f: Path, valore: str, chiave: str):
    """Righe (istante UTC, chiave, valore) di un file dell'archivio, con le ore doppie dell'ora solare risolte."""
    d = json.loads(f.read_text(encoding="utf-8"))
    colonne = list((d.get("Columns") or {}).keys())
    i_t, i_v, i_k = _colonna(colonne, "Date"), _colonna(colonne, valore), _colonna(colonne, chiave)
    visti: dict = defaultdict(int)
    for r in d.get("Data") or []:
        v = r[i_v]
        if v is None or r[i_t] is None:
            continue
        t, assoluto = _data_locale(r[i_t])
        k = str(r[i_k]).strip()
        if not assoluto:
            n = visti[(t, k)]
            visti[(t, k)] += 1
            loc = t.replace(tzinfo=ROMA, fold=min(n, 1))
            # ore che non esistono (passaggio all'ora legale): scartate
            if loc.astimezone(UTC).astimezone(ROMA).replace(tzinfo=None) != t:
                continue
            t = loc.astimezone(UTC)
        yield t, k, float(v)


# archivio Parquet del worker (fase 4, servizio/terna.py): dataset del Download Center → (serie, colonna chiave, valore)
PARQUET = {
    "TotalLoad": ("carico_totale", "zona", "carico_mw"),
    "ActualGeneration": ("produzione", "fonte", "energia_gwh"),
    "RenewableGeneration": ("rinnovabili", "fonte", "energia_gwh"),
}


def _parquet(archivio: Path) -> bool:
    """True se `archivio` è l'archivio Parquet del worker (cartella carico_totale/ con dentro dei .parquet)."""
    return any((archivio / PARQUET[FONTE_CARICO["dataset"]][0]).glob("*.parquet")) if FONTE_CARICO["dataset"] in PARQUET else False


def _file_mese(archivio: Path, dataset: str, am: str) -> Path:
    if _parquet(archivio) and dataset in PARQUET:
        return archivio / PARQUET[dataset][0] / f"{am}.parquet"
    return archivio / f"{dataset}_{am}.json"


def _mesi(archivio: Path, dataset: str) -> list[str]:
    if _parquet(archivio) and dataset in PARQUET:
        cartella, modello = archivio / PARQUET[dataset][0], r"(\d{4}-\d\d)\.parquet$"
    else:
        cartella, modello = archivio, rf"{dataset}_(\d{{4}}-\d\d)\.json$"
    return sorted({m.group(1) for f in cartella.glob("*") if (m := re.match(modello, f.name))})


def _leggi_parquet(f: Path, dataset: str):
    """Righe (istante UTC, chiave, valore) di un file Parquet dell'archivio del worker."""
    import pandas as pd
    _, chiave, valore = PARQUET[dataset]
    df = pd.read_parquet(f, columns=["istante", chiave, valore])
    df = df[df[valore].notna() & df["istante"].notna()]
    ist = pd.to_datetime(df["istante"], utc=True)
    for t, k, v in zip(ist, df[chiave], df[valore]):
        yield t.to_pydatetime().astimezone(UTC), str(k).strip(), float(v)


def _righe(archivio: Path, dataset: str, am: str, valore: str, chiave: str):
    f = _file_mese(archivio, dataset, am)
    return _leggi_parquet(f, dataset) if f.suffix == ".parquet" else _leggi(f, valore, chiave)


def _griglia(anno: int, mese: int) -> tuple[dt.datetime, int]:
    """Primo quarto d'ora del mese (UTC) e numero di quarti d'ora del mese locale."""
    t0 = dt.datetime(anno, mese, 1, tzinfo=ROMA).astimezone(UTC)
    a2, m2 = (anno + 1, 1) if mese == 12 else (anno, mese + 1)
    t1 = dt.datetime(a2, m2, 1, tzinfo=ROMA).astimezone(UTC)
    return t0, int((t1 - t0) / QUARTO)


def _serie(righe, t0: dt.datetime, n: int, mappa) -> tuple[dict, int]:
    """{chiave: [valore o None] * n} sulla griglia dei quarti d'ora e passo dei dati (15 o 60 minuti).
    I dati orari valgono per i quattro quarti d'ora dell'ora."""
    righe = [(t, mappa(k), v) for t, k, v in righe]
    righe = [r for r in righe if r[1] is not None]
    orari = bool(righe) and all(t.minute == 0 for t, _, _ in righe) and len({t for t, _, _ in righe}) * 3 < n
    out: dict = {}
    for t, k, v in righe:
        i = int((t - t0) / QUARTO)
        s = out.setdefault(k, [None] * n)
        for j in range(i, min(n, i + 4) if orari else i + 1):
            if 0 <= j < n:
                s[j] = v
    return out, 60 if orari else 15


def _zona(k: str) -> str | None:
    z = ZONA_DA_TERNA.get(k.lower())
    if z is None:
        raise ValueError(f"zona di mercato sconosciuta nei dati: {k!r} (configurazione cambiata? aggiorna ZONE)")
    return z


def _ora_legale(t0: dt.datetime, n: int) -> list[list[int]]:
    """[[indice, minuti dall'UTC], …] a ogni cambio di fuso nel mese (il primo all'indice 0)."""
    out: list[list[int]] = []
    for i in range(0, n, 4):               # i cambi avvengono all'ora piena
        off = int((t0 + i * QUARTO).astimezone(ROMA).utcoffset().total_seconds() // 60)
        if not out or out[-1][1] != off:
            out.append([i, off])
    return out


def _ora_doppia(car: dict, ora_legale: list[list[int]]) -> None:
    """Nel giorno del ritorno all'ora solare Terna ripete 02:00–02:45 senza dire quale valore è dell'ora legale: per ogni
    zona si sceglie l'ordine dei due valori che fa tornare meglio la somma delle zone con l'Italia."""
    zone = [z for z in car if z != "ITA"]
    if "ITA" not in car or not zone or len(zone) > 10:
        return
    for (k, off), (k0, off0) in zip(ora_legale[1:], ora_legale):
        if not (off < off0 and k >= 4):
            continue
        for j in range(4):
            a, b = k - 4 + j, k + j
            if b >= len(car["ITA"]) or any(car[z][a] is None or car[z][b] is None for z in car):
                continue
            def scarto(bits: int) -> float:
                sa = sum(car[z][b] if bits >> i & 1 else car[z][a] for i, z in enumerate(zone))
                sb = sum(car[z][a] if bits >> i & 1 else car[z][b] for i, z in enumerate(zone))
                return abs(car["ITA"][a] - sa) + abs(car["ITA"][b] - sb)
            migliore = min(range(1 << len(zone)), key=scarto)
            for i, z in enumerate(zone):
                if migliore >> i & 1:
                    car[z][a], car[z][b] = car[z][b], car[z][a]


def _interi(s: list) -> list:
    return [None if v is None else int(round(v)) for v in s]


def _taglia(serie: dict, n: int) -> int:
    """Numero di quarti d'ora fino all'ultimo con un valore (mese in corso)."""
    ultimo = 0
    for s in serie.values():
        for i in range(n - 1, -1, -1):
            if s[i] is not None:
                ultimo = max(ultimo, i + 1)
                break
    return ultimo


def fonti_quarto(att: dict, rin: dict, carico: float | None) -> dict | None:
    """Potenza per fonte [MW] in un quarto d'ora dalla produzione effettiva (att, autoconsumi compresi) e da quella
    rinnovabile (rin); None se manca la produzione effettiva."""
    if not att or any(att.get(k) is None for k in ("termo", "idro", "eol", "geo", "fv")):
        return None
    totale = sum(v for v in att.values() if v is not None)
    if rin and all(rin.get(k) is not None for k in ("bio", "idro", "eol", "geo", "fv")):
        p = {k: rin[k] for k in ("bio", "idro", "eol", "geo", "fv")}
    else:
        p = {"bio": 0.0, **{k: att[k] for k in ("idro", "eol", "geo", "fv")}}
    p["termo"] = max(0.0, totale - sum(p.values()))
    p["saldo"] = None if carico is None else carico - sum(p.values())
    return p


# ----------------------------------------------------------------------------------------------- costruzione
def costruisci_carichi(archivio: Path, uscita: Path) -> dict:
    archivio, uscita = Path(archivio), Path(uscita)
    uscita.mkdir(parents=True, exist_ok=True)
    ds_c = FONTE_CARICO["dataset"]
    mesi = _mesi(archivio, ds_c)
    if not mesi:
        raise FileNotFoundError(f"nessun file {ds_c}_AAAA-MM.json (né {PARQUET.get(ds_c, ('?',))[0]}/AAAA-MM.parquet) in {archivio}")
    elenco, dimensioni = [], {}
    for am in mesi:
        a, m = map(int, am.split("-"))
        t0, n = _griglia(a, m)
        car, passo_c = _serie(_righe(archivio, ds_c, am, FONTE_CARICO["valore"], FONTE_CARICO["zona"]), t0, n, _zona)
        car = {z: [None if v is None else v * FONTE_CARICO["scala"] for v in s] for z, s in car.items()}
        if "ITA" not in car and car:        # Italia = somma delle zone, se la fonte non la dà
            car["ITA"] = [None if any(car[z][i] is None for z in car) else sum(car[z][i] for z in car) for i in range(n)]
        n_dati = _taglia(car, n)
        if not n_dati:
            continue
        voce = {"mese": am, "inizio": t0.strftime("%Y-%m-%dT%H:%M:%SZ"), "n": n_dati, "completo": n_dati == n,
                "ora_legale": _ora_legale(t0, n_dati), "passo_carico": passo_c, "fonti": False}
        _ora_doppia(car, voce["ora_legale"])
        # (22/11/2026, Paolo) Italia = somma delle sette zone, quarto d'ora per quarto d'ora. Nei dati di Terna la serie
        # «Italy» coincide già con la somma (scarto massimo 7e-12 MW su nov 2025 – nov 2026, dopo l'ora doppia di
        # ottobre); arrotondando ogni zona all'intero, però, la somma degli interi poteva differire di 1–3 MW: ora l'Italia
        # scritta è la somma degli interi delle zone. Dove manca una zona resta la serie «Italy» di Terna (se c'è).
        # Lo scarto massimo tra «Italy» e la somma (prima dell'arrotondamento) va nell'indice: scarto_italia_mw.
        zone = [z for z in car if z != "ITA"]
        interi = {z: _interi(s[:n_dati]) for z, s in car.items()}
        scarto = 0.0
        if zone:
            ita = car.setdefault("ITA", [None] * n)
            for i in range(n_dati):
                if any(car[z][i] is None for z in zone):
                    continue
                somma = sum(car[z][i] for z in zone)
                if ita[i] is not None:
                    scarto = max(scarto, abs(ita[i] - somma))
                ita[i] = somma
                interi.setdefault("ITA", [None] * n_dati)[i] = sum(interi[z][i] for z in zone)
            interi["ITA"] = interi.get("ITA") or _interi(ita[:n_dati])
        voce["scarto_italia_mw"] = round(scarto, 3)
        if scarto > 1:
            log.warning("carichi %s: «Italy» di Terna diversa dalla somma delle zone fino a %.1f MW (si usa la somma)", am, scarto)
        f = uscita / f"carico_{am}.json"
        f.write_text(json.dumps({"mese": am, "zone": {z: interi[z] for z in [*(["ITA"] if "ITA" in interi else []), *zone]}},
                                separators=(",", ":")), encoding="utf-8")
        dimensioni[f.name] = f.stat().st_size
        fa, fr = _file_mese(archivio, "ActualGeneration", am), _file_mese(archivio, "RenewableGeneration", am)
        if fa.exists():
            att, passo_g = _serie(_righe(archivio, "ActualGeneration", am, "Actual Generation", "Primary Source"), t0, n,
                                  lambda k: ATTUALE.get(k.lower()))
            rin, _ = (_serie(_righe(archivio, "RenewableGeneration", am, "Renewable Generation", "Energy Source"), t0, n,
                             lambda k: RINNOVABILE.get(k.lower())) if fr.exists() else ({}, 15))
            out = {k: [None] * n_dati for k, _, _ in VOCI}
            presenti = 0
            for i in range(n_dati):
                p = fonti_quarto({k: (s[i] * SCALA_GENERAZIONE if s[i] is not None else None) for k, s in att.items()},
                                 {k: (s[i] * SCALA_GENERAZIONE if s[i] is not None else None) for k, s in rin.items()},
                                 car.get("ITA", [None] * n)[i])
                if p:
                    presenti += 1
                    for k in out:
                        out[k][i] = p[k]
            if presenti:
                f = uscita / f"fonti_{am}.json"
                f.write_text(json.dumps({"mese": am, "voci": {k: _interi(s) for k, s in out.items()}}, separators=(",", ":")),
                             encoding="utf-8")
                dimensioni[f.name] = f.stat().st_size
                voce.update(fonti=True, passo_fonti=passo_g, rinnovabili=bool(rin))
        elenco.append(voce)
    if not elenco:
        raise ValueError("archivio senza valori di potenza richiesta")
    indice = {
        "fonte": FONTE_CARICO["testo"], "fonte_generazione": FONTE_GENERAZIONE,
        "aggiornato": dt.datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "passo": 15,
        "zone": [{"id": z, "nome": n, "terna": t} for z, n, t in ZONE],
        "voci": [{"id": k, "nome": n, "colore": c} for k, n, c in VOCI],
        "mesi": elenco,
    }
    (uscita / "indice.json").write_text(json.dumps(indice, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    dimensioni["indice.json"] = (uscita / "indice.json").stat().st_size
    return {"mesi": [v["mese"] for v in elenco], "dimensioni": dimensioni}


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="comando", required=True)
    s = sub.add_parser("scarica")
    s.add_argument("archivio", type=Path)
    s.add_argument("--da", required=True, help="primo mese, AAAA-MM")
    s.add_argument("--a", default=dt.date.today().strftime("%Y-%m"), help="ultimo mese, AAAA-MM (predefinito: questo)")
    s.add_argument("--dataset", default=",".join(DATASET))
    s.add_argument("--rifai-ultimo", action="store_true", help="riscarica l'ultimo mese anche se c'è (mese in corso)")
    c = sub.add_parser("costruisci")
    c.add_argument("archivio", type=Path)
    c.add_argument("uscita", type=Path)
    a = p.parse_args(argv)
    if a.comando == "scarica":
        mesi = mesi_tra(a.da, a.a)
        ds = a.dataset.split(",")
        scarica(a.archivio, mesi[:-1], ds)
        scarica(a.archivio, mesi[-1:], ds, rifai=a.rifai_ultimo)
    else:
        print(json.dumps(costruisci_carichi(a.archivio, a.uscita), indent=1))


if __name__ == "__main__":
    main()
