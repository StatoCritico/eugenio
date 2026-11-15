"""Archivio psicrometrico orario leggero dal 1940 (14/11/2026): solo temperatura e umidità relativa, ora per ora, per
tutti i comuni. Serve al menu «Trattamento aria» del sito (diagramma psicrometrico, ore di funzionamento, carichi
latenti, free cooling) tramite le rotte /api/psicro/… della fase 4.

File: <cartella>/<istat>.parquet, una riga per ora con dati (le ore mancanti non ci sono: nell'API diventano null):
  ora    int32   ore dal 1970-01-01T00:00Z (UTC)
  t      int16   temperatura a 2 m in decimi di °C, riportata alla quota del comune
  ur     uint8   umidità relativa in % (vuota se manca il punto di rugiada)
  fonte  uint8   1 = ERA5 / ERA5-Land grezzo riportato alla quota del comune (come s3.py)
                 2 = serie oraria ERA5 corretta verso ICON (fase 3, `correggi`: dal 2015)
                 3 = ICON storico (riferimento della correzione; dal 24/05/2023 su S3, dal 14/11/2022 con l'API)
Metadati del file: eugenio_formato, istat, quota_m (quota del punto meteo, Copernicus DEM 90 m), dal, al.
Ordine di preferenza ora per ora: 2, poi 3, poi 1 (la serie corretta, dove c'è, vince).

Da dove arrivano i dati (come `scarica-s3`, s3.py): file .om di Open-Meteo sul bucket pubblico AWS, solo
temperature_2m e dew_point_2m. ERA5-Land (0,1°) dal 1950 dove ha la cella di terra; ERA5 (0,25°) per il 1940–1949 e,
ora per ora, dove ERA5-Land manca (mare, isole piccole); temperatura e punto di rugiada riportati alla quota del comune
con 6,5 °C/km; umidità da temperatura e punto di rugiada (s3.umidita). Verificato il 14/11/2026 sul bucket:
copernicus_era5/*/year_1940.om c'è (year_1939 no), copernicus_era5_land/*/year_1950.om c'è (year_1949 no).

Lavoro a gruppi di comuni vicini (come scarica-s3) e, dentro il gruppo, anno per anno: ogni anno del gruppo va in
<cartella>/.lavoro/<gruppo>/<anno>.parquet (un row group per comune), così si riprende da dove si era fermato; finiti gli
anni di un gruppo, ogni comune diventa un file solo (unito alla serie corretta e a ICON dell'archivio) e il lavoro del
gruppo si cancella. Memoria: un gruppo × un anno (800 comuni ≈ 0,3 GB) più un comune alla volta nell'unione.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import os
import shutil
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

log = logging.getLogger(__name__)

FORMATO = "psicro_v1"
FONTE_ERA5, FONTE_CORRETTA, FONTE_ICON = 1, 2, 3
NOMI_FONTE = {FONTE_ERA5: "ERA5/ERA5-Land (Copernicus) riportato alla quota del comune",
              FONTE_CORRETTA: "ERA5 corretto verso ICON (EuGEnio)",
              FONTE_ICON: "ICON storico (DWD)"}
_RANGO = np.array([9, 2, 0, 1], dtype=np.int8)        # indice = codice fonte; più basso = preferito
INIZIO = dt.date(1940, 1, 1)                          # primo anno di ERA5 sul bucket
INIZIO_LAND = dt.date(1950, 1, 1)                     # primo anno di ERA5-Land sul bucket
VAR = ["temperature_2m", "dew_point_2m"]
RIGHE_PER_ROW_GROUP = 24 * 3653                       # ~10 anni: le finestre brevi leggono solo l'ultimo pezzo
BLOCCO = ".scarica_in_corso"                          # c'è mentre scarica-psicro lavora: l'aggiornamento notturno aspetta
BLOCCO_FRESCO_S = 6 * 3600
SCHEMA = pa.schema([("ora", pa.int32()), ("t", pa.int16()), ("ur", pa.uint8()), ("fonte", pa.uint8())])
EPOCA = pd.Timestamp("1970-01-01", tz="UTC")
# codifica delta su tutte le colonne numeriche (le ore vicine si somigliano): 1,5 byte per ora contro 2,1 con la
# codifica normale (prova del 14/11/2026 su Bologna 1949–1950); zstd 6 scrive in fretta quanto 1 e comprime come 9
SCRITTURA = dict(compression="zstd", compression_level=6, use_dictionary=False,
                 column_encoding={"ora": "DELTA_BINARY_PACKED", "t": "DELTA_BINARY_PACKED", "ur": "DELTA_BINARY_PACKED",
                                  "fonte": "PLAIN"})


# ------------------------------------------------------------------------------------------- conversioni
def ora_da_tempi(tempi) -> np.ndarray:
    """Tempi (anche con fuso) → ore dal 1970 UTC (int64)."""
    t = pd.DatetimeIndex(pd.to_datetime(tempi, utc=True))
    return (t.as_unit("s").asi8 // 3600).astype(np.int64)


def tempo_da_ora(h: int) -> pd.Timestamp:
    return EPOCA + pd.Timedelta(hours=int(h))


def iso(h: int) -> str:
    return tempo_da_ora(h).strftime("%Y-%m-%dT%H:00Z")


def da_t_td(t: np.ndarray, td: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Temperatura e punto di rugiada (°C, float) → (t in decimi, ur in %) come float con NaN dove manca."""
    from .s3 import umidita
    t = np.asarray(t, dtype=np.float64)
    td = np.asarray(td, dtype=np.float64)
    with np.errstate(invalid="ignore", over="ignore"):
        ur = umidita(t, td)
    ur = np.where(np.isfinite(t) & np.isfinite(td), np.round(ur), np.nan)
    return np.round(t * 10), ur


def da_t_ur(t: np.ndarray, ur: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Temperatura (°C) e umidità (%) delle serie orarie dell'archivio → (decimi, %) float con NaN."""
    t = np.asarray(t, dtype=np.float64)
    ur = np.asarray(ur, dtype=np.float64)
    ur = np.where(np.isfinite(t), np.round(np.clip(ur, 0, 100)), np.nan)
    return np.round(t * 10), ur


# ------------------------------------------------------------------------------------------- file
class Serie:
    """Serie oraria in memoria: ora (int64), t (decimi, float con NaN), ur (%, float con NaN), fonte (uint8)."""
    __slots__ = ("ora", "t", "ur", "fonte")

    def __init__(self, ora, t, ur, fonte):
        self.ora = np.asarray(ora, dtype=np.int64)
        self.t = np.asarray(t, dtype=np.float32)
        self.ur = np.asarray(ur, dtype=np.float32)
        self.fonte = np.broadcast_to(np.asarray(fonte, dtype=np.uint8), self.ora.shape).copy()

    def __len__(self):
        return len(self.ora)

    @classmethod
    def vuota(cls) -> "Serie":
        return cls(np.zeros(0, np.int64), np.zeros(0), np.zeros(0), np.zeros(0, np.uint8))

    def da(self, h: int) -> "Serie":
        m = self.ora >= h
        return Serie(self.ora[m], self.t[m], self.ur[m], self.fonte[m])


def unisci(*parti: Serie) -> Serie:
    """Una serie sola, ordinata per ora; per la stessa ora vince la fonte preferita (2, poi 3, poi 1).
    Le righe senza temperatura si scartano."""
    parti = [p for p in parti if p is not None and len(p)]
    if not parti:
        return Serie.vuota()
    ora = np.concatenate([p.ora for p in parti])
    t = np.concatenate([p.t for p in parti])
    ur = np.concatenate([p.ur for p in parti])
    fonte = np.concatenate([p.fonte for p in parti])
    ok = np.isfinite(t)
    ora, t, ur, fonte = ora[ok], t[ok], ur[ok], fonte[ok]
    ordine = np.lexsort((_RANGO[np.minimum(fonte, 3)], ora))
    ora, t, ur, fonte = ora[ordine], t[ordine], ur[ordine], fonte[ordine]
    primo = np.ones(len(ora), dtype=bool)
    primo[1:] = ora[1:] != ora[:-1]
    return Serie(ora[primo], t[primo], ur[primo], fonte[primo])


def _tabella(s: Serie) -> pa.Table:
    t_ok = np.isfinite(s.t)
    ur_ok = np.isfinite(s.ur)
    return pa.table({
        "ora": pa.array(s.ora.astype(np.int32), type=pa.int32()),
        "t": pa.array(np.where(t_ok, s.t, 0).astype(np.int16), type=pa.int16(), mask=~t_ok),
        "ur": pa.array(np.where(ur_ok, s.ur, 0).astype(np.uint8), type=pa.uint8(), mask=~ur_ok),
        "fonte": pa.array(s.fonte.astype(np.uint8), type=pa.uint8()),
    }, schema=SCHEMA)


def scrivi(p: Path, s: Serie, istat: str, quota: float | None) -> None:
    """Scrittura atomica (file temporaneo + rename): l'api legge il file vecchio finché il nuovo non è pronto."""
    tab = _tabella(s)
    meta = {"eugenio_formato": FORMATO, "istat": istat,
            "quota_m": "" if quota is None or not np.isfinite(quota) else f"{float(quota):.0f}",
            "dal": iso(int(s.ora[0])) if len(s) else "", "al": iso(int(s.ora[-1])) if len(s) else ""}
    tab = tab.replace_schema_metadata({k: str(v) for k, v in meta.items()})
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.tmp")
    pq.write_table(tab, tmp, row_group_size=RIGHE_PER_ROW_GROUP, write_statistics=["ora"], **SCRITTURA)
    tmp.replace(p)


def leggi(p: Path, dal_ora: int | None = None) -> Serie:
    """Legge un file dell'archivio (con dal_ora solo i row group che servono)."""
    f = pq.ParquetFile(p)
    gruppi = list(range(f.metadata.num_row_groups))
    if dal_ora is not None:
        tenuti = []
        for k in gruppi:
            st = f.metadata.row_group(k).column(0).statistics
            if st is None or not st.has_min_max or st.max >= dal_ora:
                tenuti.append(k)
        gruppi = tenuti
    if not gruppi:
        return Serie.vuota()
    tab = f.read_row_groups(gruppi)
    s = Serie(tab["ora"].to_numpy(), tab["t"].cast(pa.float32()).to_numpy(zero_copy_only=False),
              tab["ur"].cast(pa.float32()).to_numpy(zero_copy_only=False), tab["fonte"].to_numpy())
    return s.da(dal_ora) if dal_ora is not None else s


def info(p: Path) -> dict:
    """Metadati senza leggere i dati: istat, quota_m, prima e ultima ora (dalle statistiche dei row group), righe."""
    md = pq.read_metadata(p)
    meta = {k.decode(): v.decode() for k, v in (md.metadata or {}).items() if not k.startswith(b"ARROW")}
    lo = hi = None
    for k in range(md.num_row_groups):
        st = md.row_group(k).column(0).statistics
        if st is not None and st.has_min_max:
            lo = st.min if lo is None else min(lo, st.min)
            hi = st.max if hi is None else max(hi, st.max)
    q = meta.get("quota_m", "")
    return {"istat": meta.get("istat", p.stem), "formato": meta.get("eugenio_formato"),
            "quota_m": float(q) if q not in ("", None) else None,
            "prima": None if lo is None else int(lo), "ultima": None if hi is None else int(hi), "righe": md.num_rows}


def da_orario(p: Path, fonte: int, dal_ora: int | None = None) -> Serie:
    """Serie oraria dell'archivio (orario/era5_corretto, orario/icon, orario/ del server) → Serie."""
    if not p.exists():
        return Serie.vuota()
    try:
        d = pd.read_parquet(p, columns=["time", "temperature_2m", "relative_humidity_2m"])
    except Exception as e:                       # file rotto: si va avanti senza
        log.warning("psicro: %s illeggibile (%s)", p, e)
        return Serie.vuota()
    if d.empty:
        return Serie.vuota()
    ora = ora_da_tempi(d["time"])
    t, ur = da_t_ur(d["temperature_2m"].to_numpy(dtype="float64"), d["relative_humidity_2m"].to_numpy(dtype="float64"))
    s = unisci(Serie(ora, t, ur, fonte))
    return s.da(dal_ora) if dal_ora is not None else s


# ------------------------------------------------------------------------------------------- lettura S3
def t_td(fs, c: pd.DataFrame, h0: int, h1: int) -> tuple[np.ndarray, np.ndarray]:
    """Temperatura e punto di rugiada (comuni × ore, °C) alla quota del comune, come s3.era5: ERA5-Land dal 1950 dove
    c'è, altrimenti ERA5, ora per ora (con entrambe le grandezze dalla stessa fonte). ERA5 si legge solo per i comuni
    che ne hanno bisogno (anni prima del 1950, celle di mare)."""
    from . import s3
    n, h_land = h1 - h0, s3._ora(dt.datetime.combine(INIZIO_LAND, dt.time()))
    z = c.quota.to_numpy(dtype="float64")[:, None]
    t = np.full((len(c), n), np.nan, dtype=np.float32)
    td = np.full((len(c), n), np.nan, dtype=np.float32)
    a = max(h0, h_land)
    if a < h1:
        land = s3._leggi_dom(fs, c, "era5_land", VAR, a, h1)
        dl = (c.era5_land_h.to_numpy(dtype="float64")[:, None] - z) * s3.GRADIENTE
        t[:, a - h0:] = land["temperature_2m"] + dl
        td[:, a - h0:] = land["dew_point_2m"] + dl
    manca = ~(np.isfinite(t) & np.isfinite(td))
    righe = np.flatnonzero(manca.any(axis=1))
    if len(righe):
        sub = c.iloc[righe].reset_index(drop=True)
        e = s3._leggi_dom(fs, sub, "era5", VAR, h0, h1)
        de = (sub.era5_h.to_numpy(dtype="float64")[:, None] - z[righe]) * s3.GRADIENTE
        m = manca[righe]
        t[righe] = np.where(m, e["temperature_2m"] + de, t[righe])
        td[righe] = np.where(m, e["dew_point_2m"] + de, td[righe])
    return t, td


# ------------------------------------------------------------------------------------------- scarico
def _id_gruppo(codici: list[str]) -> str:
    return hashlib.sha1(",".join(codici).encode()).hexdigest()[:12]


def _pezzo_fatto(p: Path, h1: int) -> bool:
    if not p.exists():
        return False
    try:
        m = pq.read_metadata(p).metadata or {}
        return int(m.get(b"eugenio_h1", b"0")) >= h1
    except Exception:
        return False


def _scrivi_pezzo(p: Path, gr: pd.DataFrame, h0: int, h1: int, t: np.ndarray, td: np.ndarray) -> None:
    """Un anno di un gruppo: un row group per comune (solo le ore con temperatura)."""
    ore = np.arange(h0, h1, dtype=np.int64)
    tmp = p.with_name(f".{p.name}.tmp")
    p.parent.mkdir(parents=True, exist_ok=True)
    schema = pa.schema([("istat", pa.string()), *SCHEMA]).with_metadata({"eugenio_h0": str(h0), "eugenio_h1": str(h1)})
    with pq.ParquetWriter(tmp, schema, compression="zstd", compression_level=3) as w:
        for k, istat in enumerate(gr.istat):
            tt, uu = da_t_td(t[k], td[k])
            s = unisci(Serie(ore, tt, uu, FONTE_ERA5))
            if not len(s):
                continue
            tab = _tabella(s)
            w.write_table(pa.table({"istat": pa.array([istat] * len(s), pa.string()), **{c: tab[c] for c in tab.column_names}},
                                   schema=schema))
    tmp.replace(p)


def _da_pezzi(pezzi: list[pq.ParquetFile], indici: list[dict], istat: str) -> Serie:
    parti = []
    for f, ind in zip(pezzi, indici):
        for k in ind.get(istat, ()):
            tab = f.read_row_group(k, columns=["ora", "t", "ur", "fonte"])
            parti.append(Serie(tab["ora"].to_numpy(), tab["t"].cast(pa.float32()).to_numpy(zero_copy_only=False),
                               tab["ur"].cast(pa.float32()).to_numpy(zero_copy_only=False), tab["fonte"].to_numpy()))
    return unisci(*parti)


def _indice_pezzo(f: pq.ParquetFile) -> dict:
    """istat → row group (dalle statistiche della colonna istat: un comune per row group)."""
    out: dict[str, list[int]] = {}
    for k in range(f.metadata.num_row_groups):
        st = f.metadata.row_group(k).column(0).statistics
        if st is not None and st.has_min_max and st.min == st.max:
            v = st.min.decode() if isinstance(st.min, bytes) else str(st.min)
            out.setdefault(v, []).append(k)
        else:                                               # non dovrebbe succedere: si legge la colonna
            for v in set(f.read_row_group(k, columns=["istat"])["istat"].to_pylist()):
                out.setdefault(v, []).append(k)
    return out


def completo(p: Path, h0: int, h1: int) -> bool:
    """Il file finale copre già [h0, h1)?"""
    if not p.exists():
        return False
    try:
        i = info(p)
    except Exception:
        return False
    return i["formato"] == FORMATO and i["prima"] is not None and i["prima"] <= h0 + 24 * 7 and i["ultima"] >= h1 - 1


def _celle_psicro(cartella: Path, c: pd.DataFrame) -> None:
    """Quota e celle ERA5/ERA5-Land dei comuni (per l'api: quota e pressione; per l'aggiornamento notturno da S3)."""
    col = ["istat", "lat", "lon", "quota", "era5_land_i", "era5_land_j", "era5_land_h", "era5_i", "era5_j", "era5_h"]
    nuove = c[col].copy()
    f = cartella / "celle.parquet"
    if f.exists():
        vecchie = pd.read_parquet(f)
        nuove = pd.concat([vecchie[~vecchie.istat.isin(nuove.istat)], nuove], ignore_index=True)
    cartella.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(".celle.parquet.tmp")
    nuove.sort_values("istat").to_parquet(tmp, index=False)
    tmp.replace(f)


def scarica(archivio: Path, comuni: pd.DataFrame, cartella: Path | None = None, dal: dt.date = INIZIO,
            al: dt.date | None = None, per_gruppo: int = 400, tieni_lavoro: bool = False, fs=None) -> dict:
    """Scarica T e Td da S3 e scrive <cartella>/<istat>.parquet per i comuni (cartella predefinita: archivio/psicro).
    Riprendibile: i comuni con il file già completo si saltano, gli anni già scritti di un gruppo non si rifanno."""
    from . import s3
    cartella = Path(cartella or archivio / "psicro")
    cartella.mkdir(parents=True, exist_ok=True)
    blocco = cartella / BLOCCO
    blocco.write_text(json.dumps({"pid": os.getpid(), "inizio": dt.datetime.now().isoformat(timespec="seconds")}))
    fs = fs or s3.FSBlocchi()
    try:
        c = s3.celle(fs, comuni, archivio)
        _celle_psicro(cartella, c)
        fine = s3.fine_dati(fs, "era5")
        if al:
            fine = min(fine, s3._ora(dt.datetime.combine(al, dt.time(23))))
        dal = max(dal, INIZIO)
        h_ini = s3._ora(dt.datetime.combine(dal, dt.time()))
        h_fin = fine + 1
        if h_ini >= h_fin:
            raise ValueError("periodo vuoto: --dal dopo l'ultima ora disponibile")
        da_fare = c[[not completo(cartella / f"{r.istat}.parquet", h_ini, h_fin) for r in c.itertuples()]]
        log.info("psicro: %d comuni, %d già completi; periodo %s → %s", len(c), len(c) - len(da_fare), iso(h_ini),
                 iso(h_fin - 1))
        da_fare = da_fare.sort_values(["lat", "lon"]).reset_index(drop=True)
        gruppi = [da_fare.iloc[k:k + per_gruppo].reset_index(drop=True) for k in range(0, len(da_fare), per_gruppo)]
        anni = range(tempo_da_ora(h_ini).year, tempo_da_ora(h_fin - 1).year + 1)
        t0, b0, fatti = time.time(), fs.letti, 0
        for ng, gr in enumerate(gruppi, 1):
            gid = _id_gruppo(list(gr.istat))
            lavoro = cartella / ".lavoro" / gid
            lavoro.mkdir(parents=True, exist_ok=True)
            (lavoro / "comuni.json").write_text(json.dumps(list(gr.istat)))
            for anno in anni:
                h0 = max(h_ini, s3._ora(dt.datetime(anno, 1, 1)))
                h1 = min(h_fin, s3._ora(dt.datetime(anno + 1, 1, 1)))
                p = lavoro / f"{anno}.parquet"
                if h0 >= h1 or _pezzo_fatto(p, h1):
                    continue
                t1 = time.time()
                t, td = t_td(fs, gr, h0, h1)
                _scrivi_pezzo(p, gr, h0, h1, t, td)
                blocco.touch()
                log.info("psicro gruppo %d/%d (%d comuni) anno %d: %.0f s (totale %.1f GB letti, %.0f min)", ng,
                         len(gruppi), len(gr), anno, time.time() - t1, (fs.letti - b0) / 1e9, (time.time() - t0) / 60)
            fatti += _unisci_gruppo(archivio, cartella, gr, lavoro, h_ini)
            if not tieni_lavoro:
                shutil.rmtree(lavoro, ignore_errors=True)
        if not tieni_lavoro:
            try:
                (cartella / ".lavoro").rmdir()
            except OSError:
                pass
        return {"comuni": len(c), "scritti": fatti, "dal": iso(h_ini), "al": iso(h_fin - 1),
                "gb_letti": round((fs.letti - b0) / 1e9, 2), "minuti": round((time.time() - t0) / 60, 1)}
    finally:
        blocco.unlink(missing_ok=True)


def _unisci_gruppo(archivio: Path, cartella: Path, gr: pd.DataFrame, lavoro: Path, h_ini: int) -> int:
    """Per ogni comune del gruppo: anni da S3 + file già presente + serie corretta (2) + ICON (3) → un file."""
    pezzi = [pq.ParquetFile(p) for p in sorted(lavoro.glob("[0-9]*.parquet"))]
    indici = [_indice_pezzo(f) for f in pezzi]
    n = 0
    for r in gr.itertuples():
        p = cartella / f"{r.istat}.parquet"
        grezzo = _da_pezzi(pezzi, indici, r.istat)
        vecchio = leggi(p) if p.exists() else None
        corretta = da_orario(archivio / "orario" / "era5_corretto" / f"{r.istat}.parquet", FONTE_CORRETTA, h_ini)
        icon = da_orario(archivio / "orario" / "icon" / f"{r.istat}.parquet", FONTE_ICON, h_ini)
        s = unisci(corretta, icon, grezzo, vecchio)
        if len(s):
            scrivi(p, s, r.istat, float(r.quota) if pd.notna(r.quota) else None)
            n += 1
    log.info("psicro: unione di %d comuni (%s…)", n, ", ".join(list(gr.istat)[:3]))
    return n


# ------------------------------------------------------------------------------------------- aggiornamento notturno
def in_corso(cartella: Path) -> bool:
    b = cartella / BLOCCO
    try:
        return time.time() - b.stat().st_mtime < BLOCCO_FRESCO_S
    except OSError:
        return False


def aggiorna(cartella: Path, orario: Path | None = None, usa_s3: bool = True, giorni_max: int = 45,
             per_gruppo: int = 800, fs=None, comuni: list[str] | None = None) -> dict:
    """Aggiunge le ore nuove ai file esistenti (mai le vecchie): prima dalla serie oraria ICON del server (`orario`,
    fonte 3; c'è per i comuni aggiornati ogni giorno dal worker), poi, per chi resta indietro, da ERA5/ERA5-Land su S3
    (fonte 1, ~5 giorni di ritardo, al più gli ultimi `giorni_max` giorni). Un comune alla volta, scrittura atomica."""
    cartella = Path(cartella)
    esito = {"comuni": 0, "icon": 0, "s3": 0, "saltato": None}
    if not cartella.is_dir():
        esito["saltato"] = "cartella assente"
        return esito
    if in_corso(cartella):
        esito["saltato"] = "scarica-psicro in corso"
        return esito
    file = {p.stem: p for p in cartella.glob("[0-9]*.parquet")}
    if comuni is not None:
        file = {k: v for k, v in file.items() if k in set(comuni)}
    esito["comuni"] = len(file)
    ultima, quota, nuove = {}, {}, {}
    for istat, p in file.items():
        try:
            i = info(p)
        except Exception as e:
            log.warning("psicro: %s illeggibile (%s)", p, e)
            continue
        if i["ultima"] is not None:
            ultima[istat], quota[istat] = i["ultima"], i["quota_m"]
    if orario is not None and Path(orario).is_dir():
        for istat, h in ultima.items():
            s = da_orario(Path(orario) / f"{istat}.parquet", FONTE_ICON, h + 1)
            if len(s):
                nuove[istat] = [s]
                ultima[istat] = int(s.ora[-1])
                esito["icon"] += 1
    if usa_s3 and ultima and (cartella / "celle.parquet").exists():
        from . import s3
        fs = fs or s3.FSBlocchi()
        fine = s3.fine_dati(fs, "era5")
        c = pd.read_parquet(cartella / "celle.parquet")
        c = c[c.istat.isin([k for k, h in ultima.items() if h < fine])].copy()
        if len(c):
            c["dopo"] = c.istat.map(ultima)
            h0 = max(int(c.dopo.min()) + 1, fine + 1 - giorni_max * 24)
            c = c.sort_values(["lat", "lon"]).reset_index(drop=True)
            ore = np.arange(h0, fine + 1, dtype=np.int64)
            for k in range(0, len(c), per_gruppo):
                gr = c.iloc[k:k + per_gruppo].reset_index(drop=True)
                t, td = t_td(fs, gr, h0, fine + 1)
                for j, r in enumerate(gr.itertuples()):
                    tt, uu = da_t_td(t[j], td[j])
                    s = unisci(Serie(ore, tt, uu, FONTE_ERA5)).da(int(r.dopo) + 1)
                    if len(s):
                        nuove.setdefault(r.istat, []).append(s)
                        esito["s3"] += 1
    for istat, parti in nuove.items():
        p = file[istat]
        scrivi(p, unisci(leggi(p), *parti), istat, quota.get(istat))
    log.info("psicro: aggiornati %d comuni (ICON %d, S3 %d) su %d", len(nuove), esito["icon"], esito["s3"], len(file))
    esito["aggiornati"] = len(nuove)
    return esito


# ------------------------------------------------------------------------------------------- stime
def stima(comuni: int, dal: dt.date = INIZIO, al: dt.date | None = None, byte_per_ora: float = 1.25) -> dict:
    """Stima dello spazio su disco (byte_per_ora misurato sui file veri, README della fase 3)."""
    al = al or dt.date.today()
    ore = (al - dal).days * 24
    return {"ore_per_comune": ore, "mb_per_comune": round(ore * byte_per_ora / 1e6, 2),
            "gb_totali": round(comuni * ore * byte_per_ora / 1e9, 1)}
