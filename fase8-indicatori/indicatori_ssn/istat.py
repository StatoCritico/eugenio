"""ISTAT: popolazione residente al 1° gennaio per Italia, regioni e province autonome.

La popolazione al 1° gennaio dell'anno T vale come popolazione al 31/12 dell'anno T-1 (anno di riferimento
del conto economico). Due serie, con un salto tra l'una e l'altra che la pagina segnala:
  fino al 31/12/2018  ricostruzione intercensuaria 2002–2019 (popolazione al 1/1/2016–2019)
  dal 31/12/2019      censimento permanente, popolazione residente al 1° gennaio (POSAS, dal 1/1/2020)

Si leggono i file pubblicati da ISTAT su demo.istat.it (ZIP con CSV, aggiornati una volta l'anno); se non
rispondono si prova il servizio SDMX di esploradati.istat.it (dataflow 22_289 e
164_164_DF_DCIS_RICPOPRES2011_1, chiave A.<area>.JAN.9.TOTAL.99), che il 27/10/2026 rispondeva con errori.
Le province autonome di Bolzano (021) e Trento (022) si prendono dai file per provincia.
"""
from __future__ import annotations

import csv
import io
import logging
import zipfile
from pathlib import Path

from . import costanti as K
from .rete import FonteNonDisponibile, Rete

log = logging.getLogger("indicatori_ssn")
DEMO = "https://demo.istat.it/data"
CSV_SDMX = "application/vnd.sdmx.data+csv;version=1.0.0"
# codice ISTAT della regione (2 cifre) → codice SDMX usato nei file JSON; 04 è il Trentino-Alto Adige intero
AREA_DA_REGIONE = {m: nuts for (m, nuts, _) in K.REGIONI_CE.values() if m != "04"}
AREA_DA_PROVINCIA = {"021": "ITD1", "022": "ITD2"}         # province autonome


def _intero(x) -> int | None:
    try:
        return int(str(x).strip().replace(".", ""))
    except ValueError:
        return None


def _csv_da_zip(dati: bytes) -> str:
    z = zipfile.ZipFile(io.BytesIO(dati))
    nome = next(n for n in z.namelist() if n.lower().endswith(".csv"))
    return z.read(nome).decode("utf-8-sig", errors="replace")


# ------------------------------------------------------------------------- censimento permanente (POSAS)
def leggi_posas(testo: str, livello: str) -> dict[str, int]:
    """POSAS per regioni o province: {codice: totale} dalla riga Età = 999 (o sommando le età)."""
    righe = testo.splitlines()
    inizio = next(i for i, r in enumerate(righe) if r.lstrip('"').lower().startswith("codice"))
    r = csv.reader(righe[inizio:], delimiter=";")
    testa = next(r)
    i_tot = len(testa) - 1
    tot999, somma = {}, {}
    for x in r:
        if len(x) < len(testa):
            continue
        cod, eta, v = x[0].strip().zfill(2 if livello == "regioni" else 3), x[2].strip(), _intero(x[i_tot])
        if v is None:
            continue
        if eta == "999":
            tot999[cod] = v
        elif eta.isdigit():
            somma[cod] = somma.get(cod, 0) + v
    return tot999 or somma


# ------------------------------------------------------------------------- ricostruzione intercensuaria
def leggi_ricostruzione(testo: str) -> dict[int, dict[str, int]]:
    """File "PopolazioneEta-Territorio-*": blocchi per anno ("Tutte le cittadinanze - Anno: AAAA"), dentro
    ognuno il primo sotto-blocco è quello dei due sessi insieme. {anno del 1° gennaio: {codice: totale}}."""
    out: dict[int, dict[str, int]] = {}
    anno, sotto, blocco = None, 0, None
    for riga in testo.splitlines():
        s = riga.strip().strip('"')
        if "Anno:" in s:
            tutte = s.lower().startswith("tutte le cittadinanze")
            try:
                a = int(s.split("Anno:")[1].strip()[:4])
            except ValueError:
                a = None
            anno = a if tutte else None
            sotto = 0
            continue
        if anno is None:
            continue
        campi = riga.split(";")
        if campi[0].lower().startswith("codice"):
            sotto += 1
            blocco = out.setdefault(anno, {}) if sotto == 1 else None
            continue
        if blocco is None or not campi[0].strip().isdigit():
            continue
        valori = [_intero(c) for c in campi[2:]]
        blocco[campi[0].strip()] = sum(v for v in valori if v is not None)
    return out


# ------------------------------------------------------------------------------------------ SDMX (riserva)
def leggi_csv_sdmx(testo: str) -> dict[str, dict[int, float]]:
    """CSV SDMX → {REF_AREA: {anno del 1° gennaio: valore}}."""
    out: dict[str, dict[int, float]] = {}
    for riga in csv.DictReader(io.StringIO(testo.lstrip("﻿"))):
        area = (riga.get("REF_AREA") or "").strip()
        periodo = (riga.get("TIME_PERIOD") or "").strip()[:4]
        valore = (riga.get("OBS_VALUE") or "").strip()
        if area and periodo.isdigit() and valore:
            try:
                out.setdefault(area, {})[int(periodo)] = float(valore)
            except ValueError:
                pass
    return out


def _sdmx(rete: Rete, flusso: str, ini: int, fin: int, f: Path) -> dict[str, dict[int, float]]:
    aree = "+".join(["IT"] + sorted({v[1] for v in K.REGIONI_CE.values()}))
    url = f"{K.SDMX}/data/IT1,{flusso},1.0/A.{aree}.JAN.9.TOTAL.99/ALL/?startPeriod={ini}&endPeriod={fin}"
    if not f.exists() or rete.rinnova:
        rete.richiesta("GET", url, accetta=CSV_SDMX, atteso="csv", flusso_in=f)
    return leggi_csv_sdmx(f.read_text(encoding="utf-8"))


# ------------------------------------------------------------------------------------------------ insieme
def _scarica_zip(rete: Rete, url: str, f: Path) -> str:
    if not f.exists() or rete.rinnova:
        rete.richiesta("GET", url, atteso="zip", flusso_in=f)
    return _csv_da_zip(f.read_bytes())


def da_censimento(rete: Rete, anno_gen: int, cartella: Path) -> tuple[dict[str, int], bool]:
    """Popolazione al 1/1/anno_gen e True se ISTAT la indica come stima (l'ultimo anno, di solito)."""
    testo = _scarica_zip(rete, f"{DEMO}/posas/POSAS_{anno_gen}_it_Regioni.zip", cartella / f"POSAS_{anno_gen}_Regioni.zip")
    reg = leggi_posas(testo, "regioni")
    prov = leggi_posas(_scarica_zip(rete, f"{DEMO}/posas/POSAS_{anno_gen}_it_Province.zip",
                                    cartella / f"POSAS_{anno_gen}_Province.zip"), "province")
    return _aree(reg, prov), "stima" in testo.split("\n", 1)[0].lower()


def _aree(reg: dict[str, int], prov: dict[str, int], italia: int | None = None) -> dict[str, int]:
    out = {AREA_DA_REGIONE[c]: v for c, v in reg.items() if c in AREA_DA_REGIONE}
    out.update({AREA_DA_PROVINCIA[c]: v for c, v in prov.items() if c in AREA_DA_PROVINCIA})
    out["IT"] = italia if italia is not None else sum(reg.values())
    return out


def da_ricostruzione(rete: Rete, cartella: Path) -> dict[int, dict[str, int]]:
    base = f"{DEMO}/ricostruzione/PopolazioneEta-Territorio-"
    reg = leggi_ricostruzione(_scarica_zip(rete, base + "Regioni.zip", cartella / "Ricostruzione_Regioni.zip"))
    prov = leggi_ricostruzione(_scarica_zip(rete, base + "Province.zip", cartella / "Ricostruzione_Province.zip"))
    return {a: _aree(reg[a], prov.get(a, {})) for a in reg}


def scarica(rete: Rete, anni: list[int], cartella: Path) -> dict:
    """{"dati": {area: {anno di riferimento: residenti al 31/12}}, "serie": {anno: ricostruzione | censimento | stima}}."""
    cartella.mkdir(parents=True, exist_ok=True)
    pop: dict[str, dict[int, float]] = {}
    serie: dict[int, str] = {}

    def metti(rif, valori, nome):
        for area, v in valori.items():
            pop.setdefault(area, {})[rif] = v
        serie[rif] = nome

    ricostruiti = [a for a in anni if a < K.PRIMO_ANNO_CENSIMENTO]
    if ricostruiti:
        try:
            ric = da_ricostruzione(rete, cartella)
            for a in ricostruiti:
                if a + 1 in ric:
                    metti(a, ric[a + 1], "ricostruzione")
        except (FonteNonDisponibile, StopIteration, KeyError, zipfile.BadZipFile) as e:
            log.warning("ISTAT, ricostruzione da demo.istat.it non disponibile (%s): provo SDMX", e)
            try:
                d = _sdmx(rete, K.FLUSSO_POP_RICOSTRUITA, min(ricostruiti) + 1, max(ricostruiti) + 1,
                          cartella / "sdmx_ricostruzione.csv")
                for a in ricostruiti:
                    metti(a, {ar: s[a + 1] for ar, s in d.items() if a + 1 in s}, "ricostruzione")
            except FonteNonDisponibile as e2:
                log.warning("ISTAT SDMX non disponibile: %s", e2)
    for a in (x for x in anni if x >= K.PRIMO_ANNO_CENSIMENTO):
        try:
            valori, stima = da_censimento(rete, a + 1, cartella)
            metti(a, valori, "stima" if stima else "censimento")
        except (FonteNonDisponibile, StopIteration, KeyError, zipfile.BadZipFile) as e:
            log.warning("ISTAT, popolazione al 1/1/%d da demo.istat.it non disponibile (%s): provo SDMX", a + 1, e)
            try:
                d = _sdmx(rete, K.FLUSSO_POP, a + 1, a + 1, cartella / f"sdmx_{a + 1}.csv")
                if d:
                    metti(a, {ar: s[a + 1] for ar, s in d.items() if a + 1 in s}, "censimento")
            except FonteNonDisponibile as e2:
                log.warning("ISTAT SDMX non disponibile: %s", e2)
    return {"dati": pop, "serie": serie}
