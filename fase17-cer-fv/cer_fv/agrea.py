"""Piani colturali grafici di AGREA: scaricamento sul server e lettura a pezzi (24/11/2026).

**I dati AGREA non si cedono** (decisione di Paolo del 24/11/2026): stanno solo nella cartella dei dati di EuGEnio sul
server (`DATI/agrea/<campagna>/`, con `DATI=/srv/energia/dati`), mai nel repository, mai serviti né nelle risposte
dell'API. Tutto in quella cartella, niente copie altrove (Paolo, 24/11 alle 10:29: «non sparpagliarli dappertutto»).

Fonte: https://agreagestione.regione.emilia-romagna.it/agrea-file/UtilizziGrafici/<anno>/Uti_Part_PCG_<anno>_<PR>.zip
(dal 2021): gli appezzamenti dichiarati **ritagliati sulle particelle catastali**, divisi per provincia della particella,
con comune ISTAT, sezione, foglio, particella e superficie (`SUP_UTI`, ettari). Codice dell'azienda già cifrato da AGREA.
Il file `_XX` (particelle fuori regione) non si scarica. Un anno pesa ~1,3 GB di zip; il `.dbf` di una provincia, aperto,
fino a qualche GB: per questo si legge a pezzi dallo zip (`righe_dbf`), senza estrarlo e senza tenerlo in memoria.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
import re
import struct
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterator

log = logging.getLogger("cer_fv.agrea")

BASE = "https://agreagestione.regione.emilia-romagna.it/agrea-file/UtilizziGrafici/"
DATI = Path(os.environ.get("DATI", "/srv/energia/dati"))
CARTELLA = DATI / "agrea"
PROVINCE = ("BO", "FC", "FE", "MO", "PC", "PR", "RA", "RE", "RN")
_VOCE = re.compile(r'(\d+/\d+/\d{4})\s+(\d+:\d+\s+[AP]M)\s+(?:&lt;dir&gt;|(\d+))\s+<A HREF="([^"]+)"', re.I)


def _get(url: str, timeout: int = 120):
    req = urllib.request.Request(url, headers={"User-Agent": "EuGEnio (eugenio.statocritico.it) cer_fv"})
    return urllib.request.urlopen(req, timeout=timeout)   # noqa: S310 - indirizzo fisso di AGREA


def elenco(url: str) -> list[dict]:
    """Voci dell'elenco della cartella (IIS): nome, dimensione (None per le cartelle), data."""
    with _get(url, 60) as r:
        testo = r.read().decode("utf-8", "replace")
    out = []
    for data, ora, dim, href in _VOCE.findall(testo):
        nome = href.rstrip("/").rsplit("/", 1)[-1]
        out.append({"nome": nome, "url": url.split("/agrea-file/")[0] + href if href.startswith("/") else url + href,
                    "dimensione": int(dim) if dim else None, "data": f"{data} {ora}"})
    return out


def campagne_chiuse(anni: list[int], quante: int = 3, oggi: dt.date | None = None) -> list[int]:
    """Le ultime `quante` campagne concluse: quella dell'anno in corso è ancora aperta (AGREA la aggiorna)."""
    oggi = oggi or dt.date.today()
    return sorted(a for a in anni if a < oggi.year)[-quante:]


def scarica(dest: Path = CARTELLA, quante: int = 3, anni: list[int] | None = None, togli_vecchie: bool = False,
            oggi: dt.date | None = None) -> dict:
    """Scarica in `dest/<anno>/` gli zip delle 9 province delle campagne scelte; salta quelli già presenti con la stessa
    dimensione; scrive prima in `.part` e poi rinomina. Con `togli_vecchie` cancella le cartelle `dest/<anno>/` delle
    campagne non più usate (solo cartelle con il nome di un anno, solo dentro `dest`)."""
    voci = elenco(BASE)
    disponibili = sorted(int(v["nome"]) for v in voci if v["dimensione"] is None and re.fullmatch(r"\d{4}", v["nome"]))
    scelti = sorted(anni) if anni else campagne_chiuse(disponibili, quante, oggi)
    dest.mkdir(parents=True, exist_ok=True)
    esito = {"cartella": str(dest), "campagne": scelti, "scaricati": [], "gia_presenti": [], "tolte": []}
    for anno in scelti:
        cart = dest / str(anno)
        cart.mkdir(exist_ok=True)
        for v in elenco(f"{BASE}{anno}/"):
            m = re.fullmatch(rf"Uti_Part_PCG_{anno}_([A-Z]{{2}})\.zip", v["nome"], re.I)
            if not m or m.group(1).upper() not in PROVINCE:
                continue
            f = cart / v["nome"]
            if f.exists() and f.stat().st_size == v["dimensione"]:
                esito["gia_presenti"].append(f"{anno}/{v['nome']}")
                continue
            tmp = f.with_suffix(".zip.part")
            log.info("scarico %s (%.0f MB)", v["url"], (v["dimensione"] or 0) / 1e6)
            with _get(v["url"], 600) as r, open(tmp, "wb") as out:
                while blocco := r.read(1 << 20):
                    out.write(blocco)
            preso = tmp.stat().st_size
            if v["dimensione"] and preso != v["dimensione"]:
                tmp.unlink(missing_ok=True)
                raise IOError(f"{v['nome']}: scaricati {preso} byte su {v['dimensione']}")
            with zipfile.ZipFile(tmp) as z:
                if z.testzip() is not None:
                    tmp.unlink(missing_ok=True)
                    raise IOError(f"{v['nome']}: zip rovinato")
            tmp.replace(f)
            esito["scaricati"].append(f"{anno}/{v['nome']}")
    if togli_vecchie:
        import shutil
        for p in dest.iterdir():
            if p.is_dir() and re.fullmatch(r"\d{4}", p.name) and int(p.name) not in scelti:
                shutil.rmtree(p)
                esito["tolte"].append(p.name)
    return esito


# ------------------------------------------------------------------ lettura a pezzi del .dbf dentro lo zip
def righe_dbf(flusso, campi: list[str] | None = None) -> Iterator[dict]:
    """Righe di un file dBASE III letto in sequenza (anche da `ZipFile.open`), solo i `campi` chiesti (tutti se None).
    Testo in latin-1, spazi tolti; numeri come testo (li converte chi li usa)."""
    testa = flusso.read(32)
    n, lunga_testa, lunga_riga = struct.unpack("<IHH", testa[4:12])
    descr = flusso.read(lunga_testa - 32)
    defs, pos = [], 1                                   # il primo byte di ogni riga è il segno di cancellazione
    for i in range(0, len(descr) - 1, 32):
        d = descr[i:i + 32]
        if d[0] == 0x0D:
            break
        nome = d[:11].split(b"\x00")[0].decode("latin-1").strip()
        lung = d[16]
        defs.append((nome, pos, lung))
        pos += lung
    voluti = [(k, a, a + l) for k, a, l in defs if campi is None or k.upper() in {c.upper() for c in campi}]
    for _ in range(n):
        riga = flusso.read(lunga_riga)
        if len(riga) < lunga_riga:
            break
        if riga[:1] == b"*":
            continue
        yield {k: riga[a:b].decode("latin-1", "replace").strip() for k, a, b in voluti}


def campi_dbf(flusso) -> list[str]:
    testa = flusso.read(32)
    lunga_testa = struct.unpack("<H", testa[8:10])[0]
    descr = flusso.read(lunga_testa - 32)
    out = []
    for i in range(0, len(descr) - 1, 32):
        if descr[i] == 0x0D:
            break
        out.append(descr[i:i + 11].split(b"\x00")[0].decode("latin-1").strip())
    return out


def dbf_negli_zip(cartella: Path) -> Iterator[tuple[str, zipfile.ZipFile, str]]:
    """(nome, zip aperto, nome del .dbf) per ogni .dbf degli zip della cartella di una campagna."""
    for p in sorted(cartella.glob("*.zip")):
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if n.lower().endswith(".dbf"):
                    yield f"{p.name}:{n}", z, n


# ------------------------------------------------------------------ codici ISTAT → codici catastali (Belfiore)
ISTAT_ELENCO = "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv"


def istat_belfiore(comuni: Path | None = None, cartella: Path = CARTELLA) -> dict[str, str]:
    """Dal `comuni.parquet` della fase 3 (colonne istat, belfiore: sul server `DATI/clima_lavoro/comuni.parquet`) o,
    se manca, dall'elenco dei comuni dell'ISTAT, salvato una volta in `cartella/comuni_istat.csv`."""
    comuni = comuni or DATI / "clima_lavoro" / "comuni.parquet"
    if comuni.exists() and comuni.suffix == ".parquet":
        import pyarrow.parquet as pq
        t = pq.read_table(comuni).to_pydict()
        ist = t.get("istat") or t.get("__index_level_0__")
        return {str(i).zfill(6): str(b).upper() for i, b in zip(ist, t["belfiore"]) if i and b}
    import csv
    import io
    f = comuni if comuni.exists() and comuni.suffix == ".csv" else cartella / "comuni_istat.csv"
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        with _get(ISTAT_ELENCO) as r:
            f.write_bytes(r.read())
    testo = f.read_bytes().decode("latin-1")
    out = {}
    for i, riga in enumerate(csv.reader(io.StringIO(testo), delimiter=";")):
        if i == 0 or len(riga) < 20:
            continue
        ist, belf = riga[4].strip().zfill(6), riga[19].strip().upper()
        if ist.isdigit() and len(belf) == 4:
            out[ist] = belf
    return out
