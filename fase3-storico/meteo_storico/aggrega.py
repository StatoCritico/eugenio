"""Aggregazione giornaliera (giorno civile Europe/Rome) ed esportazione per il server."""
from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

log = logging.getLogger(__name__)

# Giornaliero nazionale (04/11/2026, 7.896 comuni × ~4.300 giorni ≈ 34 milioni di righe): un solo giornaliero.parquet
# ordinato per comune e data, con UN ROW GROUP OGNI COMUNI_PER_BLOCCO COMUNI (un comune non è mai diviso tra due
# row group). Scrittura, lettura per comune e aggiornamento passano un blocco alla volta: la memoria resta quella di
# un blocco (100 comuni ≈ 430.000 righe ≈ 30 MB), mai quella del file intero.
COMUNI_PER_BLOCCO = 100
FORMATO = "giornaliero_a_blocchi_v1"          # nei metadati del file (chiave eugenio_formato)
CHIAVI = ["istat", "data"]
RIGHE_PER_LETTURA = 500_000                   # righe lette insieme dai file da aggiornare o convertire


def giornaliero(df: pd.DataFrame) -> pd.DataFrame:
    x = df.set_index(pd.DatetimeIndex(df["time"]).tz_convert("Europe/Rome")).drop(columns="time")
    g = x.resample("D")
    out = pd.DataFrame({
        "t_media": g.temperature_2m.mean(),
        "t_min": g.temperature_2m.min(),
        "t_max": g.temperature_2m.max(),
        "ur_media": g.relative_humidity_2m.mean(),
        "rad_globale_kwh_m2": g.shortwave_radiation.sum() / 1000.0,   # W/m² medi orari → kWh/m²
        "rad_diffusa_kwh_m2": g.diffuse_radiation.sum() / 1000.0,
        "vento_medio_kmh": g.wind_speed_10m.mean(),
        "nuvolosita_media": g.cloud_cover.mean(),
        "pioggia_mm": g.precipitation.sum(),
        "neve_cm": g.snowfall.sum(),
        "ore": g.temperature_2m.count(),
    })
    out = out[out.ore >= 20].drop(columns="ore")
    out["gg20"] = (20 - out.t_media).clip(lower=0)       # gradi giorno riscaldamento (base 20 °C)
    out["gc24"] = (out.t_media - 24).clip(lower=0)       # gradi giorno raffrescamento (base 24 °C)
    out.index = out.index.date
    out.index.name = "data"
    return out.astype("float32").reset_index()


def esporta(archivio: Path, comuni: pd.DataFrame, dest: Path) -> None:
    """Prepara la cartella da copiare sul server (fase 4):
      comuni.json, giornaliero.parquet (ERA5 corretto, tutti i comuni, a blocchi di comuni: vedi sotto),
      orario/<istat>.parquet (ICON storico, modalità di breve periodo),
      parametri_correzione.parquet, metriche.json

    Il giornaliero nazionale (~34 milioni di righe) non passa mai tutto in memoria: i comuni, in ordine di codice ISTAT,
    sono elaborati a blocchi di COMUNI_PER_BLOCCO; ogni blocco va in `giornaliero.parziale/` (riprendibile: un blocco
    già scritto non si rifà) e alla fine i blocchi diventano i row group di un solo `giornaliero.parquet`.
    """
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "orario").mkdir(exist_ok=True)
    par, n = [], 0
    codici = sorted(str(i) for i in comuni.istat)
    parziale = _Parziale(dest / "giornaliero.parziale", {"origine": "esporta", "comuni": codici,
                                                         "comuni_per_blocco": COMUNI_PER_BLOCCO})
    for k, blocco in enumerate(_blocchi_di(codici)):
        if not parziale.fatto(k):
            parti = []
            for istat in blocco:
                p = archivio / "orario" / "era5_corretto" / f"{istat}.parquet"
                if p.exists():
                    g = giornaliero(pd.read_parquet(p))
                    g.insert(0, "istat", istat)
                    parti.append(g)
            parziale.scrivi(k, pd.concat(parti, ignore_index=True) if parti else None)
            log.info("giornaliero: blocco %d (%d comuni con dati)", k + 1, len(parti))
        for istat in blocco:
            q = archivio / "orario" / "icon" / f"{istat}.parquet"
            if q.exists():
                shutil.copyfile(q, dest / "orario" / f"{istat}.parquet")
            for sorgente in ("era5", "icon2i", "ifs"):
                c = archivio / "correzione" / "parametri" / sorgente / f"{istat}.parquet"
                if c.exists():
                    par.append(pd.read_parquet(c))
    n = parziale.unisci(dest / "giornaliero.parquet")
    if par:
        pd.concat(par, ignore_index=True).to_parquet(dest / "parametri_correzione.parquet", index=False)
    for nome in ("comuni.json", "comuni.parquet"):
        if (archivio / nome).exists():
            shutil.copyfile(archivio / nome, dest / nome)
    for nome in ("metriche.json", "metriche_icon2i.json", "metriche_ifs.json"):
        m = archivio / "correzione" / nome
        if m.exists():
            shutil.copyfile(m, dest / nome)
    (dest / "LEGGIMI.txt").write_text(
        "Dati meteo: Open-Meteo.com (ERA5/ERA5-Land Copernicus, ICON DWD), CC BY 4.0.\n"
        "Comuni e sezioni di censimento: ISTAT, CC BY 4.0 (via Gramscii).\n"
        "giornaliero.parquet: ERA5-Seamless corretto verso ICON (vedi metriche.json), ordinato per comune,\n"
        f"un row group ogni {COMUNI_PER_BLOCCO} comuni.\n"
        "orario/: previsioni storiche ICON seamless, UTC.\n", encoding="utf-8")
    log.info("Esportati %d comuni (%d righe giornaliere) in %s", len(codici), n, dest)


# ---------------------------------------------------------------------------------------------- giornaliero a blocchi
def _blocchi_di(codici: list[str]):
    n = max(1, int(COMUNI_PER_BLOCCO))
    for i in range(0, len(codici), n):
        yield codici[i:i + n]


class _Parziale:
    """Cartella di lavoro `giornaliero.parziale/`: un file per blocco, scritti in modo atomico, e `lavoro.json` con
    la descrizione del lavoro. Se il lavoro cambia (altri comuni, altro file d'origine, altra dimensione dei blocchi) la
    cartella si svuota e si riparte; altrimenti i blocchi già scritti si tengono (ripresa dopo un'interruzione)."""

    def __init__(self, cartella: Path, lavoro: dict):
        self.d = cartella
        self.d.mkdir(parents=True, exist_ok=True)
        f = self.d / "lavoro.json"
        try:
            vecchio = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            vecchio = None
        if vecchio != lavoro:
            for x in self.d.iterdir():
                if x.is_file():
                    x.unlink()
            f.write_text(json.dumps(lavoro), encoding="utf-8")
        elif any(self.d.glob("blocco_*.parquet")):
            log.info("giornaliero: riprendo il lavoro in %s", self.d)

    def _p(self, k: int) -> Path:
        return self.d / f"blocco_{k:05d}.parquet"

    def fatto(self, k: int) -> bool:
        return self._p(k).exists() or (self.d / f"blocco_{k:05d}.vuoto").exists()

    def scrivi(self, k: int, df: pd.DataFrame | None) -> None:
        if df is None or df.empty:
            (self.d / f"blocco_{k:05d}.vuoto").touch()
            return
        df = df.sort_values(CHIAVI, kind="stable").reset_index(drop=True)
        tmp = self.d / f"blocco_{k:05d}.tmp"
        df.to_parquet(tmp, index=False, compression="zstd")
        os.replace(tmp, self._p(k))

    def unisci(self, finale: Path) -> int:
        """Blocchi → `finale` (un row group per blocco, scrittura atomica), poi cancella la cartella. Righe scritte."""
        scr = ScrittoreBlocchi(finale)
        for p in sorted(self.d.glob("blocco_*.parquet")):
            scr.aggiungi(pd.read_parquet(p))
        n = scr.chiudi()
        shutil.rmtree(self.d, ignore_errors=True)
        return n


class ScrittoreBlocchi:
    """Scrive un giornaliero a blocchi da DataFrame che arrivano già in ordine di comune, ognuno con comuni completi.
    Tiene in memoria al più un blocco più l'ultimo pezzo ricevuto. Scrive in `<finale>.nuovo` e sostituisce `finale`
    solo a `chiudi()` (chi legge vede il file vecchio o quello nuovo, mai uno a metà)."""

    def __init__(self, finale: Path, schema: pa.Schema | None = None):
        self.finale = Path(finale)
        self.tmp = self.finale.with_name(self.finale.name + ".nuovo")
        self.schema = _schema_pulito(schema) if schema is not None else None
        self.w: pq.ParquetWriter | None = None
        self.attesa: list[pd.DataFrame] = []
        self.n_attesa = 0          # comuni in attesa
        self.righe = 0
        self.ultimo: str | None = None

    def aggiungi(self, df: pd.DataFrame) -> None:
        if df is None or df.empty:
            return
        df = df.sort_values(CHIAVI, kind="stable").reset_index(drop=True)
        primo = str(df.istat.iloc[0])
        if self.ultimo is not None and primo <= self.ultimo:
            raise ValueError(f"giornaliero: comuni non in ordine ({primo} dopo {self.ultimo})")
        self.ultimo = str(df.istat.iloc[-1])
        self.attesa.append(df)
        self.n_attesa += df.istat.nunique()
        while self.n_attesa >= COMUNI_PER_BLOCCO:
            self._scarica(COMUNI_PER_BLOCCO)

    def _scarica(self, quanti: int) -> None:
        tutto = pd.concat(self.attesa, ignore_index=True) if len(self.attesa) > 1 else self.attesa[0]
        codici = tutto.istat.drop_duplicates()
        if quanti >= len(codici):
            blocco, resto = tutto, tutto.iloc[:0]
        else:
            taglio = codici.iloc[quanti]
            blocco, resto = tutto[tutto.istat < taglio], tutto[tutto.istat >= taglio]
        self._scrivi(blocco)
        self.attesa = [resto.reset_index(drop=True)] if len(resto) else []
        self.n_attesa = resto.istat.nunique() if len(resto) else 0

    def _scrivi(self, df: pd.DataFrame) -> None:
        if df.empty:
            return
        if self.schema is None:
            self.schema = _schema_pulito(pa.Schema.from_pandas(df, preserve_index=False))
        t = _a_tabella(df, self.schema)
        if self.w is None:
            self.tmp.parent.mkdir(parents=True, exist_ok=True)
            meta = {b"eugenio_formato": FORMATO.encode(), b"comuni_per_blocco": str(COMUNI_PER_BLOCCO).encode()}
            self.w = pq.ParquetWriter(self.tmp, self.schema.with_metadata(meta), compression="zstd")
        self.w.write_table(t, row_group_size=max(1, t.num_rows))
        self.righe += t.num_rows

    def chiudi(self) -> int:
        if self.attesa:
            self._scarica(10 ** 9)
        if self.w is None:                 # nessuna riga: file vuoto con lo schema, se noto
            if self.schema is None:
                return 0
            pq.write_table(self.schema.empty_table(), self.tmp)
        else:
            self.w.close()
        os.replace(self.tmp, self.finale)
        return self.righe

    def annulla(self) -> None:
        if self.w is not None:
            self.w.close()
        self.tmp.unlink(missing_ok=True)


def _schema_pulito(s: pa.Schema) -> pa.Schema:
    s = s.remove_metadata()
    return pa.schema([pa.field(f.name, pa.string() if f.name == "istat" else f.type) for f in s])


def _a_tabella(df: pd.DataFrame, schema: pa.Schema) -> pa.Table:
    df = df.copy()
    for f in schema:
        if f.name not in df:
            df[f.name] = np.nan
    df["istat"] = df.istat.astype(str)
    if pa.types.is_date32(schema.field("data").type):
        df["data"] = pd.to_datetime(df["data"]).dt.date
    t = pa.Table.from_pandas(df[schema.names], preserve_index=False)
    return t.cast(schema)


def _da_tabella(t: pa.Table) -> pd.DataFrame:
    df = t.to_pandas()
    if "istat" in df:
        df["istat"] = df.istat.astype(str)
    return df


def info_giornaliero(p: Path) -> dict:
    """Come è fatto il file, dalle sole statistiche dei row group: righe, row group, formato, ordinato per comune."""
    f = pq.ParquetFile(p)
    md = f.metadata
    meta = f.schema_arrow.metadata or {}
    i = f.schema_arrow.get_field_index("istat")
    estremi, ordinato, a_blocchi = [], True, True
    for rg in range(md.num_row_groups):
        st = md.row_group(rg).column(i).statistics
        if st is None or not st.has_min_max:
            ordinato = a_blocchi = False
            break
        lo, hi = str(st.min), str(st.max)
        if estremi:
            if lo < estremi[-1][1]:
                ordinato = False
            if lo <= estremi[-1][1]:
                a_blocchi = False            # un comune diviso tra due row group (o fuori ordine)
        estremi.append((lo, hi))
    return {"righe": md.num_rows, "row_group": md.num_row_groups,
            "formato": meta.get(b"eugenio_formato", b"").decode() or None,
            "comuni_per_blocco": int(meta[b"comuni_per_blocco"]) if b"comuni_per_blocco" in meta else None,
            "ordinato": ordinato, "a_blocchi": a_blocchi and ordinato, "estremi": estremi}


def leggi_comune(p: Path, istat: str, estremi: list[tuple[str, str]] | None = None,
                 colonne: list[str] | None = None) -> pd.DataFrame:
    """Le righe di un comune, leggendo solo i row group che possono contenerlo (statistiche min/max di `istat`)."""
    f = pq.ParquetFile(p)
    if estremi is None:
        estremi = info_giornaliero(p)["estremi"] or []
    gruppi = ([k for k, (lo, hi) in enumerate(estremi) if lo <= istat <= hi]
              if len(estremi) == f.metadata.num_row_groups else list(range(f.metadata.num_row_groups)))
    cols = None if colonne is None else list(dict.fromkeys(["istat", *colonne]))
    if not gruppi:
        return _da_tabella(f.schema_arrow.empty_table().select(cols) if cols else f.schema_arrow.empty_table())
    t = f.read_row_groups(gruppi, columns=cols)
    t = t.filter(pc.equal(t["istat"].cast(pa.string()), istat))
    return _da_tabella(t)


def _unisci_righe(vecchie: pd.DataFrame | None, nuove: pd.DataFrame | None) -> pd.DataFrame:
    parti = [x for x in (vecchie, nuove) if x is not None and len(x)]
    if not parti:
        return pd.DataFrame()
    if len(parti) == 1:
        return parti[0]
    d = pd.concat(parti, ignore_index=True)
    return d.drop_duplicates(CHIAVI, keep="last").sort_values(CHIAVI, kind="stable").reset_index(drop=True)


def aggiorna_a_blocchi(p: Path, nuovi: pd.DataFrame | None = None) -> int:
    """Aggiunge (o corregge) righe istat+data nel giornaliero e lo riscrive a blocchi di COMUNI_PER_BLOCCO comuni,
    senza mai caricarlo tutto. Le righe nuove vincono su quelle esistenti con la stessa chiave; i comuni nuovi entrano
    al loro posto in ordine. Senza `nuovi` converte soltanto il file al formato a blocchi.

    File ordinato per comune (anche con row group di altre dimensioni, come quelli scritti prima del 07/11/2026):
    una sola passata, un row group alla volta. File non ordinato: `converti_a_blocchi` (una lettura filtrata per
    blocco, riprendibile). Restituisce le righe scritte."""
    p = Path(p)
    nuovi = _prepara_nuovi(nuovi)
    if not p.exists():
        scr = ScrittoreBlocchi(p)
        if nuovi is not None:
            scr.aggiungi(nuovi)
        return scr.chiudi()
    inf = info_giornaliero(p)
    if not inf["ordinato"]:
        log.info("giornaliero: %s non è ordinato per comune, conversione a blocchi", p)
        return converti_a_blocchi(p, nuovi)
    f = _apri(p)
    scr = ScrittoreBlocchi(p, f.schema_arrow)
    resto = nuovi                                           # righe nuove non ancora scritte (in ordine)
    sospese: pd.DataFrame | None = None                     # righe dell'ultimo comune letto (può continuare)
    try:
        # a pezzi di RIGHE_PER_LETTURA righe, qualunque sia la dimensione dei row group del file
        for b in f.iter_batches(batch_size=RIGHE_PER_LETTURA):
            df = _da_tabella(pa.Table.from_batches([b]))
            if df.empty:
                continue
            if not df.istat.is_monotonic_increasing or (sospese is not None and df.istat.iloc[0] < sospese.istat.iloc[0]):
                raise _NonOrdinato
            if sospese is not None:
                df = pd.concat([sospese, df], ignore_index=True)
            ultimo = df.istat.iloc[-1]
            completi, sospese = df[df.istat < ultimo], df[df.istat == ultimo]
            if resto is not None and len(resto):
                entra, resto = resto[resto.istat < ultimo], resto[resto.istat >= ultimo]
            else:
                entra = None
            scr.aggiungi(_unisci_righe(completi, entra))
        scr.aggiungi(_unisci_righe(sospese, resto))
        return scr.chiudi()
    except _NonOrdinato:
        scr.annulla()
        log.info("giornaliero: %s non è ordinato per comune dentro i row group, conversione a blocchi", p)
        return converti_a_blocchi(p, nuovi)
    except BaseException:
        scr.annulla()
        raise


def _apri(p: Path) -> pq.ParquetFile:
    # senza pre_buffer: lettura a flusso (pre_buffer porta in memoria interi row group in anticipo, ~2× la memoria)
    return pq.ParquetFile(p, pre_buffer=False, buffer_size=1 << 20)


class _NonOrdinato(Exception):
    pass


def converti_a_blocchi(p: Path, nuovi: pd.DataFrame | None = None) -> int:
    """Per un giornaliero NON ordinato per comune (o senza statistiche): elenco dei comuni row group per row group,
    poi una lettura filtrata del file per ogni blocco di comuni, ognuno salvato in `giornaliero.parziale/` accanto al
    file (riprendibile: se si interrompe, rilanciando si rifanno solo i blocchi mancanti), infine l'unione."""
    p = Path(p)
    nuovi = _prepara_nuovi(nuovi)
    f = _apri(p)
    codici: set[str] = set()
    for b in f.iter_batches(batch_size=RIGHE_PER_LETTURA * 4, columns=["istat"]):
        codici |= set(pc.unique(b.column(0).cast(pa.string())).to_pylist())
    if nuovi is not None:
        codici |= set(nuovi.istat)
    codici = sorted(codici)
    st = p.stat()
    lavoro = {"origine": str(p.name), "dimensione": st.st_size, "mtime": int(st.st_mtime), "comuni": len(codici),
              "comuni_per_blocco": COMUNI_PER_BLOCCO, "nuovi": 0 if nuovi is None else int(len(nuovi))}
    parziale = _Parziale(p.with_name(p.stem + ".parziale"), lavoro)
    schema = _schema_pulito(f.schema_arrow)
    for k, blocco in enumerate(_blocchi_di(codici)):
        if parziale.fatto(k):
            continue
        t = pq.read_table(p, filters=[("istat", "in", blocco)], pre_buffer=False, buffer_size=1 << 20)
        vecchie = _da_tabella(t)
        entra = nuovi[nuovi.istat.isin(blocco)] if nuovi is not None else None
        parziale.scrivi(k, _unisci_righe(vecchie, entra))
        log.info("giornaliero: blocco %d di %d convertito", k + 1, -(-len(codici) // max(1, COMUNI_PER_BLOCCO)))
    scr = ScrittoreBlocchi(p, schema)
    for q in sorted(parziale.d.glob("blocco_*.parquet")):
        scr.aggiungi(pd.read_parquet(q))
    n = scr.chiudi()
    shutil.rmtree(parziale.d, ignore_errors=True)
    return n


def _prepara_nuovi(nuovi: pd.DataFrame | None) -> pd.DataFrame | None:
    if nuovi is None or len(nuovi) == 0:
        return None
    d = nuovi.copy()
    d["istat"] = d.istat.astype(str)
    d["data"] = pd.to_datetime(d["data"]).dt.date
    return d.drop_duplicates(CHIAVI, keep="last").sort_values(CHIAVI, kind="stable").reset_index(drop=True)
