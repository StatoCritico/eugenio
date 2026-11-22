"""«Dati pluviometrici» (Clima e meteo, 22/11/2026): pioggia misurata del Dipartimento della Protezione Civile.

Solo i prodotti «Merging» (radar corretto con i pluviometri), aggiornati dal DPC ogni 30 minuti: decisione di Paolo del
22/11/2026 (il radar da solo è poco affidabile; EuGEnio ha fini statistici, non di allerta: niente intensità istantanea,
niente bollettini di allerta, niente avvisi per email).
Fonte: API aperta radar-api.protezionecivile.it (senza account; chiamate del visualizzatore del DPC, non documentate) letta
con la libreria dpc-radar (Apache-2.0, https://github.com/agent-engineering-studio/dpc-radar). Dati CC BY-SA 4.0
(«Dipartimento della Protezione Civile»): tutto ciò che ne deriva (immagini, valori per comune, file, email) si pubblica
con la stessa licenza, segnata accanto ai dati (decisione di Paolo del 22/11/2026).

Prodotti: CUMh = pioggia delle h ore precedenti (3, 6, 12, 24), mm, griglia 0,01° in EPSG:4326, un frame ogni 30 minuti.

Il worker (thread a parte, ogni C.RADAR_MIN minuti, predefinito 30, `giro`):
  * ultimo frame di ogni prodotto in C.RADAR_DATI/ultimi (letture puntuali delle rotte), controllato contro il frame di
    30 minuti prima (dpc_radar RainGrid.quality: salti impossibili, valori oltre il record italiano, pixel isolati;
    tra il 9/10 e il 3/11/2026 il DPC ha pubblicato CUM24 alle :30 con valori fino a 20.584 mm): se il frame è scartato
    resta il precedente;
  * immagini PNG per la mappa in C.RADAR_SITO/<prodotto>/<AAAAMMGGTHHMMZ>.png alle ore locali multiple di h (CUM3 ogni 3
    ore, CUM24 a mezzanotte), riproiettate su una griglia fissa in Web Mercator (EPSG:3857, 1 km), per
    C.RADAR_GIORNI_MAPPA giorni (animazione della pagina fino a 7 giorni indietro);
  * archivio delle mappe CUM3 (ogni 3 ore locali) e CUM24 (mezzanotte locale) in C.RADAR_DATI/archivio, GeoTIFF compressi
    in decimi di mm, per C.RADAR_ARCHIVIO_ANNI anni (decisione di Paolo: 5 anni); si ferma sotto C.RADAR_SPAZIO_MIN_GB;
  * valori per comune degli stessi frame (mediana 3×3 al punto del comune di comuni.parquet) in
    C.RADAR_DATI/valori/<prodotto>/<AAAA-MM>.parquet, tenuti per sempre; NaN = nessuna misura (mai zero);
  * recupero all'indietro fino a C.RADAR_RECUPERO_GIORNI giorni (il DPC tiene i frame ~5 mesi), al più C.RADAR_SCARICHI
    frame per giro, i più recenti prima; i frame che il DPC non ha più si segnano e non si richiedono di nuovo;
  * C.RADAR_SITO/indice.json (copia in C.RADAR_DATI per l'api) con i frame disponibili, la griglia, la scala dei colori,
    le fonti e le licenze;
  * pioggia prevista dal sito (previsioni/ultima.parquet, ICON-2I → IFS) per il giorno appena iniziato, una volta al giorno,
    in C.RADAR_DATI/previsto/<AAAA>.parquet, per il confronto «previsto e misurato».
Rotte: /api/radar/stato, /api/radar/punto, /api/radar/comune/{istat} (in fondo al file).

  python -m servizio.worker radar        un giro
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import math
import re
import shutil
import threading
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from . import config as C, protezione as P

log = logging.getLogger("radar")
ROMA = ZoneInfo("Europe/Rome")
UTC = dt.timezone.utc

# ---------------------------------------------------------------------------------------------- prodotti e regole
PRODOTTI = ("CUM3", "CUM6", "CUM12", "CUM24")
ORE = {"CUM3": 3, "CUM6": 6, "CUM12": 12, "CUM24": 24}   # passo delle immagini (ore locali piene)
ARCHIVIO = ("CUM3", "CUM24")                             # mappe archiviate e valori per comune
PERIODO = dt.timedelta(minutes=30)                       # un frame «Merging» ogni 30 minuti
UNITA = {p: "mm" for p in PRODOTTI}
DESCRIZIONE = {
    "CUM3": "pioggia delle 3 ore precedenti (radar corretto con i pluviometri)",
    "CUM6": "pioggia delle 6 ore precedenti (radar corretto con i pluviometri)",
    "CUM12": "pioggia delle 12 ore precedenti (radar corretto con i pluviometri)",
    "CUM24": "pioggia delle 24 ore precedenti (radar corretto con i pluviometri)",
}
FONTE = ("Dati © Dipartimento della Protezione Civile («Merging» radar-pluviometri), CC BY-SA 4.0 – elaborazione "
         "EuGEnio")
URL_DPC = "https://radar.protezionecivile.gov.it/"
LICENZE = {
    "radar": {"attribuzione": "Dipartimento della Protezione Civile",
              "licenza": "CC BY-SA 4.0 – https://creativecommons.org/licenses/by-sa/4.0/",
              "nota": "le elaborazioni di EuGEnio su questi dati (immagini, valori per comune, file) sono pubblicate con la "
                      "stessa licenza CC BY-SA 4.0", "url": URL_DPC},
    "libreria": {"attribuzione": "dpc-radar (Agent Engineering Studio, G. Zileni)", "licenza": "Apache-2.0",
                 "url": "https://github.com/agent-engineering-studio/dpc-radar"},
}
AVVERTENZE = [
    "Dati a fini statistici, non di allerta: per le allerte valgono la Protezione Civile e la protezione civile regionale.",
    "Dove non c'è misura la mappa è tratteggiata in grigio: «nessuna misura» non vuol dire «niente pioggia».",
    "«Merging» del DPC: il radar dice dove è piovuto, i pluviometri quanto. Lontano dai radar e dai pluviometri, e dietro "
    "le montagne, il dato è meno sicuro.",
]
# scala dei colori (soglie inferiori delle classi); sotto la prima soglia: trasparente
SOGLIE = {"mm": [0.5, 1, 2, 5, 10, 15, 20, 30, 50, 75, 100, 150, 200, 300]}
COLORI = ["#c6e8ff", "#8cc8f5", "#4ea3e6", "#1f6fd1", "#16a35a", "#6cc63a", "#d8e22b", "#ffd21f", "#ffa31a",
          "#ff6a13", "#e8231c", "#b8124f", "#8a1fa8", "#5b1680"]
GRIGIO_MANCANTE = (128, 128, 128)
# griglia delle immagini: Web Mercator, 1 km, Italia con un po' di margine (lon 5,5–19,5; lat 35–48)
LON0, LAT0, LON1, LAT1 = 5.5, 35.0, 19.5, 48.0
RISOLUZIONE_M = 1000.0


def _merc(lon: float, lat: float) -> tuple[float, float]:
    r = 6378137.0
    return r * math.radians(lon), r * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


X0, Y0 = _merc(LON0, LAT0)
X1, Y1 = _merc(LON1, LAT1)
LARGHEZZA = int(math.ceil((X1 - X0) / RISOLUZIONE_M))
ALTEZZA = int(math.ceil((Y1 - Y0) / RISOLUZIONE_M))


def _lonlat(x: float, y: float) -> tuple[float, float]:
    r = 6378137.0
    return math.degrees(x / r), math.degrees(2 * math.atan(math.exp(y / r)) - math.pi / 2)


# angoli dell'immagine per MapLibre (alto-sinistra, alto-destra, basso-destra, basso-sinistra)
_XD, _YB = X0 + LARGHEZZA * RISOLUZIONE_M, Y1 - ALTEZZA * RISOLUZIONE_M
ANGOLI = [list(_lonlat(X0, Y1)), list(_lonlat(_XD, Y1)), list(_lonlat(_XD, _YB)), list(_lonlat(X0, _YB))]


# ---------------------------------------------------------------------------------------------- tempi e nomi
def nome(t: dt.datetime) -> str:
    return t.astimezone(UTC).strftime("%Y%m%dT%H%MZ")


def da_nome(s: str) -> dt.datetime:
    return dt.datetime.strptime(s, "%Y%m%dT%H%MZ").replace(tzinfo=UTC)


def iso(t: dt.datetime) -> str:
    return t.astimezone(UTC).isoformat().replace("+00:00", "Z")


def momenti(prodotto: str, da: dt.datetime, a: dt.datetime) -> list[dt.datetime]:
    """Frame delle immagini e dell'archivio tra `da` e `a` compresi (UTC): ore piene locali multiple di h (CUM24 a
    mezzanotte, ora italiana: d'estate le 22 UTC, d'inverno le 23)."""
    da, a = da.astimezone(UTC), a.astimezone(UTC)
    h = ORE[prodotto]
    t = da.replace(minute=0, second=0, microsecond=0)
    if t < da:
        t += dt.timedelta(hours=1)
    out = []
    while t <= a:
        if t.astimezone(ROMA).hour % h == 0:
            out.append(t)
        t += dt.timedelta(hours=1)
    return out


def ora_piena(t: dt.datetime) -> dt.datetime:
    return t.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


# ---------------------------------------------------------------------------------------------- percorsi
def percorso_png(p: str, t: dt.datetime, base: Path | None = None) -> Path:
    return Path(base or C.RADAR_SITO) / p / f"{nome(t)}.png"


def percorso_archivio(p: str, t: dt.datetime, base: Path | None = None) -> Path:
    return Path(base or C.RADAR_DATI) / "archivio" / p / f"{t.astimezone(UTC).year}" / f"{nome(t)}.tif"


def percorso_valori(p: str, t: dt.datetime, base: Path | None = None) -> Path:
    return Path(base or C.RADAR_DATI) / "valori" / p / f"{t.astimezone(ROMA):%Y-%m}.parquet"


def _leggi_json(p: Path, vuoto):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return vuoto


def _scrivi_json(p: Path, dati) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(dati, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(p)


def _stato(base: Path | None = None) -> dict:
    return _leggi_json(Path(base or C.RADAR_DATI) / "stato.json", {})


def _salva_stato(s: dict, base: Path | None = None) -> None:
    _scrivi_json(Path(base or C.RADAR_DATI) / "stato.json", s)


# ---------------------------------------------------------------------------------------------- immagini
def _palette() -> tuple[list[int], bytes]:
    """Palette dell'immagine: 0 trasparente, 1–2 tratteggio grigio dei punti senza misura, poi le classi."""
    pal = [0, 0, 0] + list(GRIGIO_MANCANTE) * 2
    alfa = [0, 150, 40]
    for c in COLORI:
        pal += [int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)]
        alfa.append(215)
    return pal + [0] * (768 - len(pal)), bytes(alfa)


def classi(valori: np.ndarray, unita: str) -> np.ndarray:
    """Indice della palette per ogni pixel: 0 sotto la prima soglia, 3.. le classi; NaN → tratteggio (1 sulle righe
    oblique, 2 tra le righe), così «nessuna misura» non sembra mai «niente pioggia»."""
    s = SOGLIE[unita]
    v = np.nan_to_num(valori, nan=-1.0)
    idx = np.digitize(v, s).astype(np.uint8)                 # 0 sotto la prima soglia, 1..len(s)
    out = np.where(idx > 0, idx + 2, 0).astype(np.uint8)
    nan = ~np.isfinite(valori)
    if nan.any():
        r, c = np.indices(valori.shape)
        out[nan] = np.where(((r + c) % 7 == 0)[nan], 1, 2)
    return out


def su_griglia(griglia) -> np.ndarray:
    """Il frame (RainGrid) riproiettato sulla griglia fissa delle immagini (EPSG:3857, 1 km); NaN fuori dal frame."""
    from affine import Affine
    from rasterio.warp import Resampling, reproject
    dst = np.full((ALTEZZA, LARGHEZZA), np.nan, dtype="float32")
    reproject(griglia.data.astype("float32"), dst, src_transform=griglia.transform, src_crs=griglia.crs, src_nodata=np.nan,
              dst_transform=Affine(RISOLUZIONE_M, 0, X0, 0, -RISOLUZIONE_M, Y1), dst_crs="EPSG:3857", dst_nodata=np.nan,
              resampling=Resampling.nearest)
    return dst


def scrivi_png(griglia, p: Path) -> int:
    from PIL import Image
    idx = classi(su_griglia(griglia), UNITA[griglia.product.name])
    img = Image.fromarray(idx, mode="P")
    pal, alfa = _palette()
    img.putpalette(pal)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp.png")
    img.save(tmp, format="PNG", optimize=True, transparency=alfa)
    tmp.replace(p)
    return p.stat().st_size


def scrivi_archivio(griglia, p: Path) -> int:
    """GeoTIFF compresso (deflate, a tessere) in decimi di mm, nodata −1: ~10 volte più piccolo del file del DPC."""
    import rasterio
    d = griglia.data
    v = np.where(np.isfinite(d), np.clip(np.round(d * 10), 0, 32767), -1).astype("int16")
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp.tif")
    prof = dict(driver="GTiff", width=v.shape[1], height=v.shape[0], count=1, dtype="int16", nodata=-1,
                crs=griglia.crs, transform=griglia.transform, compress="deflate", predictor=2, tiled=True,
                blockxsize=256, blockysize=256)
    with rasterio.open(tmp, "w", **prof) as ds:
        ds.write(v, 1)
        ds.update_tags(prodotto=griglia.product.name, fine=iso(griglia.time), unita="0.1 mm", fonte=FONTE)
    tmp.replace(p)
    return p.stat().st_size


def leggi_archivio(p: Path, prodotto: str, quando: dt.datetime | None = None):
    """Un frame dell'archivio come RainGrid (mm, NaN dove manca); `quando` di predefinito dal nome del file."""
    import rasterio
    from dpc_radar import RainGrid
    from dpc_radar.products import product
    with rasterio.open(p) as ds:
        v = ds.read(1).astype("float32")
        tr, crs = ds.transform, ds.crs
    v[v < 0] = np.nan
    return RainGrid(product(prodotto), quando or da_nome(p.stem), v / 10, tr, crs)


# ---------------------------------------------------------------------------------------------- valori per comune
@lru_cache(maxsize=2)
def _comuni_file(percorso: str, mtime: float):
    import pandas as pd
    df = pd.read_parquet(percorso, columns=["istat", "nome", "lat", "lon"])
    df["istat"] = df.istat.astype(str).str.zfill(6)
    return df.dropna(subset=["lat", "lon"]).reset_index(drop=True)


def comuni():
    p = C.DATI / "comuni.parquet"
    if not p.exists():
        return None
    return _comuni_file(str(p), p.stat().st_mtime)


def campiona_comuni(griglia) -> "object":
    import pandas as pd
    cm = comuni()
    if cm is None or cm.empty:
        return pd.DataFrame(columns=["istat", "fine", "mm"])
    v = griglia.sample(list(zip(cm.lon.astype(float), cm.lat.astype(float))))
    mm = np.array([np.nan if x is None else round(float(x), 1) for x in v], dtype="float32")
    return pd.DataFrame({"istat": cm.istat.values, "fine": pd.Timestamp(griglia.time.astimezone(UTC)), "mm": mm})


def valori_fatti(p: Path) -> set[str]:
    if not p.exists():
        return set()
    return {nome(x.to_pydatetime()) for x in _fine_file(str(p), p.stat().st_mtime)}


@lru_cache(maxsize=64)
def _fine_file(percorso: str, mtime: float):
    import pandas as pd
    return pd.read_parquet(percorso, columns=["fine"]).fine.drop_duplicates().tolist()


def aggiungi_valori(df, p: Path) -> int:
    import pandas as pd
    if df is None or len(df) == 0:
        return 0
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        df = pd.concat([pd.read_parquet(p), df], ignore_index=True)
    df = df.drop_duplicates(["istat", "fine"], keep="last").sort_values(["fine", "istat"])
    tmp = p.with_suffix(".tmp")
    df.to_parquet(tmp, index=False, compression="zstd")
    tmp.replace(p)
    return len(df)


def serie_comune(istat: str, prodotto: str, da: dt.datetime, a: dt.datetime, base: Path | None = None) -> list[dict]:
    """Valori di un comune tra `da` e `a` (UTC, fine del periodo) dai file mensili; mm None = nessuna misura."""
    import pandas as pd
    cartella = Path(base or C.RADAR_DATI) / "valori" / prodotto
    if not cartella.is_dir():
        return []
    mesi = set()
    t = da.astimezone(ROMA).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    while t <= a.astimezone(ROMA):
        mesi.add(f"{t:%Y-%m}")
        t = (t + dt.timedelta(days=32)).replace(day=1)
    out = []
    for m in sorted(mesi):
        f = cartella / f"{m}.parquet"
        if not f.exists():
            continue
        d = pd.read_parquet(f, filters=[("istat", "==", istat)])
        for r in d.itertuples():
            fine = r.fine.to_pydatetime().replace(tzinfo=UTC) if r.fine.tzinfo is None else r.fine.to_pydatetime()
            if da <= fine <= a:
                out.append({"fine": iso(fine), "mm": None if not np.isfinite(r.mm) else round(float(r.mm), 1)})
    return sorted(out, key=lambda x: x["fine"])


def giornalieri(istat: str, giorni: int, oggi: dt.date | None = None, base: Path | None = None) -> list[dict]:
    """Pioggia di ogni giorno (ora italiana) degli ultimi `giorni` giorni, dal CUM24 di mezzanotte del giorno dopo."""
    oggi = oggi or dt.datetime.now(ROMA).date()
    da = dt.datetime.combine(oggi - dt.timedelta(days=giorni - 2), dt.time(0), ROMA)     # fine del primo giorno
    a = dt.datetime.combine(oggi + dt.timedelta(days=1), dt.time(0), ROMA)
    out = []
    for r in serie_comune(istat, "CUM24", da.astimezone(UTC), a.astimezone(UTC), base):
        giorno = (dt.datetime.fromisoformat(r["fine"].replace("Z", "+00:00")).astimezone(ROMA) - dt.timedelta(hours=1)).date()
        out.append({"data": giorno.isoformat(), "mm": r["mm"]})
    return out


def previsti(istat: str, da: dt.date, a: dt.date, base: Path | None = None) -> dict[str, float]:
    """Pioggia prevista dal sito per i giorni tra `da` e `a` (registrata a inizio giornata), {data: mm}."""
    import pandas as pd
    out = {}
    for anno in range(da.year, a.year + 1):
        f = Path(base or C.RADAR_DATI) / "previsto" / f"{anno}.parquet"
        if f.exists():
            d = pd.read_parquet(f, filters=[("istat", "==", istat)])
            for r in d.itertuples():
                g = r.data if isinstance(r.data, dt.date) else pd.Timestamp(r.data).date()
                if da <= g <= a and np.isfinite(r.mm):
                    out[g.isoformat()] = round(float(r.mm), 1)
    return out


def registra_previsto(oggi: dt.date | None = None, base: Path | None = None) -> int:
    """Pioggia prevista dal sito (previsioni/ultima.parquet, ICON-2I → IFS corretti) per il giorno italiano `oggi`, per
    ogni comune con almeno 20 ore di previsione: serve al confronto «previsto e misurato»."""
    import pandas as pd
    oggi = oggi or dt.datetime.now(ROMA).date()
    f = C.DATI / "previsioni" / "ultima.parquet"
    if not f.exists():
        return 0
    d = pd.read_parquet(f, columns=["istat", "time", "precipitation"])
    d["data"] = pd.to_datetime(d.time, utc=True).dt.tz_convert(ROMA).dt.date
    d = d[d.data == oggi]
    if d.empty:
        return 0
    g = d.groupby("istat").agg(mm=("precipitation", "sum"), ore=("precipitation", "count")).reset_index()
    g = g[g.ore >= 20].drop(columns="ore")
    g["istat"] = g.istat.astype(str).str.zfill(6)
    g["data"] = oggi
    g["mm"] = g.mm.round(1).astype("float32")
    p = Path(base or C.RADAR_DATI) / "previsto" / f"{oggi.year}.parquet"
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        g = pd.concat([pd.read_parquet(p), g], ignore_index=True).drop_duplicates(["istat", "data"], keep="last")
    tmp = p.with_suffix(".tmp")
    g[["data", "istat", "mm"]].to_parquet(tmp, index=False, compression="zstd")
    tmp.replace(p)
    return int((g.data == oggi).sum())


def registra_previsto_email(prev: dict, base: Path | None = None) -> int:
    """Previsioni delle email settimanali ({istat: DataFrame giornaliero con data e pioggia}) tenute per confrontarle, la
    settimana dopo, con la pioggia misurata (le previsioni del sito coprono solo le regioni aggiornate)."""
    import pandas as pd
    righe = [{"data": r.data, "istat": str(i).zfill(6), "mm": float(r.pioggia)}
             for i, df in (prev or {}).items() if df is not None for r in df.itertuples()
             if r.pioggia is not None and np.isfinite(r.pioggia)]
    if not righe:
        return 0
    g = pd.DataFrame(righe)
    p = Path(base or C.RADAR_DATI) / "previsto_email.parquet"
    if p.exists():
        g = pd.concat([pd.read_parquet(p), g], ignore_index=True)
    g = g.drop_duplicates(["istat", "data"], keep="first")             # la prima previsione (una settimana prima)
    lim = dt.date.today() - dt.timedelta(days=60)
    g = g[pd.to_datetime(g.data).dt.date >= lim]
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    g.to_parquet(tmp, index=False, compression="zstd")
    tmp.replace(p)
    return len(righe)


def previsti_email(istat: str, base: Path | None = None) -> dict[str, float]:
    import pandas as pd
    p = Path(base or C.RADAR_DATI) / "previsto_email.parquet"
    if not p.exists():
        return {}
    d = pd.read_parquet(p, filters=[("istat", "==", str(istat).zfill(6))])
    return {pd.Timestamp(r.data).date().isoformat(): round(float(r.mm), 1) for r in d.itertuples()}


def totali_mese(anno: int, mese: int, base: Path | None = None):
    """Pioggia del mese per comune (somma dei CUM24 di mezzanotte del mese, ora italiana) con il numero di giorni
    misurati; DataFrame istat, mm, giorni. Vuoto se l'archivio non copre il mese."""
    import pandas as pd
    da = dt.datetime(anno, mese, 1, tzinfo=ROMA) + dt.timedelta(days=1)
    fine = (dt.datetime(anno, mese, 1) + dt.timedelta(days=32)).replace(day=1)
    a = dt.datetime(fine.year, fine.month, 1, tzinfo=ROMA)
    cartella = Path(base or C.RADAR_DATI) / "valori" / "CUM24"
    parti = [pd.read_parquet(f) for f in (cartella / f"{anno}-{mese:02d}.parquet", cartella / f"{a:%Y-%m}.parquet") if f.exists()]
    if not parti:
        return pd.DataFrame(columns=["istat", "mm", "giorni"])
    d = pd.concat(parti, ignore_index=True)
    fine_loc = pd.to_datetime(d.fine, utc=True).dt.tz_convert(ROMA)
    d = d[(fine_loc >= pd.Timestamp(da)) & (fine_loc <= pd.Timestamp(a)) & (fine_loc.dt.hour == 0)]
    if d.empty:
        return pd.DataFrame(columns=["istat", "mm", "giorni"])
    return d.groupby("istat").mm.agg(mm="sum", giorni="count").reset_index()


# ---------------------------------------------------------------------------------------------- giro del worker
def _assenti(base: Path | None = None) -> dict:
    return _leggi_json(Path(base or C.RADAR_DATI) / "assenti.json", {})


def _segna_assente(assenti: dict, p: str, t: dt.datetime) -> None:
    lista = assenti.setdefault(p, [])
    if nome(t) not in lista:
        lista.append(nome(t))
        del lista[:-5000]


def spazio_libero_gb(cartella: Path) -> float:
    cartella.mkdir(parents=True, exist_ok=True)
    return shutil.disk_usage(cartella).free / 1e9


def lavori(disponibili: dict[str, dt.datetime], adesso: dt.datetime, *, base_dati: Path | None = None,
           base_sito: Path | None = None, assenti: dict | None = None, archivio_ok: bool = True,
           ultimi: dict | None = None) -> list[tuple[str, dt.datetime, set[str]]]:
    """Frame da scaricare in questo giro, i più importanti prima: l'ultimo di ogni prodotto (ogni 30 minuti), poi le
    immagini mancanti e l'archivio, dal più recente al più vecchio. Ogni lavoro: (prodotto, istante, {cose da fare})."""
    assenti, ultimi = assenti or {}, ultimi or {}
    voci: dict[tuple[str, str], set[str]] = {}

    def aggiungi(p, t, cosa):
        if nome(t) in assenti.get(p, ()):
            return
        voci.setdefault((p, nome(t)), set()).add(cosa)
    for p, ultimo in disponibili.items():
        if ultimo is None:
            continue
        if (ultimi.get(p) or {}).get("fine") != nome(ultimo):
            aggiungi(p, ultimo, "ultimo")
        for t in momenti(p, adesso - dt.timedelta(days=C.RADAR_GIORNI_MAPPA), ultimo):
            if not percorso_png(p, t, base_sito).exists():
                aggiungi(p, t, "png")
        if p in ARCHIVIO:
            limite = adesso - dt.timedelta(days=C.RADAR_RECUPERO_GIORNI)
            fatti_mese: dict[Path, set[str]] = {}
            for t in momenti(p, limite, ultimo):
                pv = percorso_valori(p, t, base_dati)
                if pv not in fatti_mese:
                    fatti_mese[pv] = valori_fatti(pv)
                if nome(t) not in fatti_mese[pv]:
                    aggiungi(p, t, "valori")
                if archivio_ok and t >= adesso - dt.timedelta(days=365 * C.RADAR_ARCHIVIO_ANNI) and \
                        not percorso_archivio(p, t, base_dati).exists():
                    aggiungi(p, t, "archivio")
    prima = [(p, n) for (p, n), c in voci.items() if "ultimo" in c]
    resto = sorted((k for k in voci if k not in prima), key=lambda k: k[1], reverse=True)
    return [(p, da_nome(n), voci[(p, n)]) for p, n in prima + resto]


async def _frame(client, p: str, t: dt.datetime, assenti: dict, esito: dict):
    """Un frame dal DPC come RainGrid, o None (assente o errore, già contato in `esito`)."""
    from dpc_radar import RainGrid
    from dpc_radar.client import Absent
    try:
        raw = await client.download(p, t)
    except Exception as e:                           # un frame che non arriva non ferma gli altri
        esito["errori"].append(f"{p} {nome(t)}: {type(e).__name__}: {e}")
        return None
    if isinstance(raw, Absent):
        _segna_assente(assenti, p, t)
        esito["assenti"] += 1
        return None
    esito["scaricati"] += 1
    esito["byte"] += len(raw)
    return RainGrid.from_geotiff(raw, p, t)


def _ultimo_salvato(p: str):
    f = C.RADAR_DATI / "ultimi" / f"{p}.tif"
    u = _leggi_json(C.RADAR_DATI / "ultimi" / "ultimi.json", {}).get(p) or {}
    if not f.exists() or not u.get("fine"):
        return None
    try:
        return leggi_archivio_come(f, p, da_nome(u["fine"]))
    except Exception:
        return None


def leggi_archivio_come(f: Path, p: str, t: dt.datetime):
    return leggi_archivio(f, p, t)


async def _scarica(lista: list[tuple[str, dt.datetime, set[str]]], esito: dict, assenti: dict, ultimi: dict,
                   client=None) -> None:
    from dpc_radar import RadarClient
    proprio = client is None
    client = client or RadarClient(timeout_s=90)
    try:
        for p, t, cosa in lista:
            g = await _frame(client, p, t, assenti, esito)
            if g is None:
                continue
            try:
                # controllo contro il frame di 30 minuti prima (salti impossibili) e regole sul frame da solo
                prima = None
                if "ultimo" in cosa:
                    prima = _ultimo_salvato(p)
                    if prima is None or prima.time != t - PERIODO:
                        prima = await _frame(client, p, t - PERIODO, assenti, esito)
                q = g.quality(prima)
                if q.grid is None:                        # frame scartato: resta il precedente
                    esito["scartati"].append(f"{p} {nome(t)} ({q.verdict}, {q.reasons.get('jump', 0)} pixel)")
                    continue
                if q.mask.any():
                    esito["pixel_scartati"] += int(q.mask.sum())
                g = q.grid
                if "png" in cosa:
                    scrivi_png(g, percorso_png(p, t))
                    esito["png"] += 1
                if "archivio" in cosa:
                    scrivi_archivio(g, percorso_archivio(p, t))
                    esito["archivio"] += 1
                if "valori" in cosa:
                    aggiungi_valori(campiona_comuni(g), percorso_valori(p, t))
                    esito["valori"] += 1
                if "ultimo" in cosa:
                    scrivi_archivio(g, C.RADAR_DATI / "ultimi" / f"{p}.tif")
                    ultimi[p] = {"fine": nome(t), "verdetto": q.verdict, "pixel_scartati": int(q.mask.sum())}
            except Exception as e:
                esito["errori"].append(f"{p} {nome(t)}: {type(e).__name__}: {e}")
    finally:
        if proprio:
            await client.aclose()


async def disponibili_ora(client=None) -> dict[str, dt.datetime | None]:
    from dpc_radar import RadarClient
    proprio = client is None
    client = client or RadarClient(timeout_s=60)
    out = {}
    try:
        for p in PRODOTTI:
            try:
                lp = await client.last_product(p)
                out[p] = lp.time if lp else None
            except Exception as e:
                log.warning("Radar: ultimo frame di %s non letto: %s: %s", p, type(e).__name__, e)
                out[p] = None
    finally:
        if proprio:
            await client.aclose()
    return out


def pulizia(adesso: dt.datetime, base_dati: Path | None = None, base_sito: Path | None = None) -> dict:
    """Immagini fuori dalla finestra dell'animazione e mappe dell'archivio più vecchie di RADAR_ARCHIVIO_ANNI anni."""
    tolte = {"png": 0, "archivio": 0}
    sito, dati = Path(base_sito or C.RADAR_SITO), Path(base_dati or C.RADAR_DATI)
    limite = adesso - dt.timedelta(days=C.RADAR_GIORNI_MAPPA, hours=1)
    for p in PRODOTTI:
        for f in (sito / p).glob("*.png") if (sito / p).is_dir() else []:
            try:
                if da_nome(f.stem) < limite:
                    f.unlink()
                    tolte["png"] += 1
            except ValueError:
                continue
    limite = adesso - dt.timedelta(days=365 * C.RADAR_ARCHIVIO_ANNI + 3)
    for f in (dati / "archivio").rglob("*.tif") if (dati / "archivio").is_dir() else []:
        try:
            if da_nome(f.stem) < limite:
                f.unlink()
                tolte["archivio"] += 1
        except ValueError:
            continue
    return tolte


def frame_disponibili(base_sito: Path | None = None) -> dict[str, list[str]]:
    sito = Path(base_sito or C.RADAR_SITO)
    return {p: sorted(f.stem for f in (sito / p).glob("*.png")) if (sito / p).is_dir() else [] for p in PRODOTTI}


def scrivi_indice(base_sito: Path | None = None, base_dati: Path | None = None) -> dict:
    sito = Path(base_sito or C.RADAR_SITO)
    st = _stato(base_dati)
    fr = frame_disponibili(sito)
    ultimi = _leggi_json(Path(base_dati or C.RADAR_DATI) / "ultimi" / "ultimi.json", {})
    dati = {
        "aggiornato": iso(dt.datetime.now(UTC)),
        "raccolta_dal": st.get("raccolta_dal"),
        "griglia": {"crs": "EPSG:3857", "risoluzione_m": RISOLUZIONE_M, "larghezza": LARGHEZZA, "altezza": ALTEZZA,
                    "angoli": ANGOLI},
        "prodotti": {p: {"frame": fr[p], "unita": UNITA[p], "descrizione": DESCRIZIONE[p], "passo_ore": ORE[p],
                         "ultimo": (ultimi.get(p) or {}).get("fine")} for p in PRODOTTI},
        "scala": {u: {"soglie": s, "colori": COLORI[:len(s)]} for u, s in SOGLIE.items()},
        "mancante": {"colore": "#808080", "testo": "nessuna misura (tratteggio grigio)"},
        "fonte": FONTE, "licenze": LICENZE, "avvertenze": AVVERTENZE,
        "giorni_mappa": C.RADAR_GIORNI_MAPPA, "archivio_anni": C.RADAR_ARCHIVIO_ANNI,
    }
    _scrivi_json(sito / "indice.json", dati)
    _scrivi_json(Path(base_dati or C.RADAR_DATI) / "indice.json", dati)      # copia per l'api (non vede /sito/dati)
    return dati


def giro(adesso: dt.datetime | None = None, client=None) -> dict:
    """Un giro del lavoro dei dati pluviometrici (worker, ogni RADAR_MIN minuti)."""
    adesso = adesso or dt.datetime.now(UTC)
    st = _stato()
    st.setdefault("raccolta_dal", iso(adesso))
    esito = {"scaricati": 0, "assenti": 0, "byte": 0, "png": 0, "archivio": 0, "valori": 0, "pixel_scartati": 0,
             "scartati": [], "errori": []}
    libero = spazio_libero_gb(C.RADAR_DATI)
    archivio_ok = libero >= C.RADAR_SPAZIO_MIN_GB
    if not archivio_ok and not st.get("avviso_spazio"):
        from . import avvisi
        avvisi.invia("dati pluviometrici: archivio delle mappe fermo",
                     f"Restano {libero:.1f} GB liberi (soglia RADAR_SPAZIO_MIN_GB={C.RADAR_SPAZIO_MIN_GB:g}): il worker "
                     "smette di archiviare le mappe CUM3 e CUM24 finché non si libera spazio. Immagini della pagina e "
                     "valori per comune continuano.")
        st["avviso_spazio"] = iso(adesso)
    elif archivio_ok:
        st.pop("avviso_spazio", None)
    assenti = _assenti()
    ultimi = _leggi_json(C.RADAR_DATI / "ultimi" / "ultimi.json", {})

    async def tutto():
        disp = await disponibili_ora(client)
        lista = lavori(disp, adesso, assenti=assenti, archivio_ok=archivio_ok, ultimi=ultimi)
        esito["in_coda"] = len(lista)
        await _scarica(lista[:C.RADAR_SCARICHI], esito, assenti, ultimi, client)
        return disp
    disp = asyncio.run(tutto())
    _scrivi_json(C.RADAR_DATI / "assenti.json", assenti)
    _scrivi_json(C.RADAR_DATI / "ultimi" / "ultimi.json", ultimi)
    esito["pulizia"] = pulizia(adesso)
    # previsione del sito per il giorno appena iniziato (una volta al giorno, dopo le 00:20 italiane)
    loc = adesso.astimezone(ROMA)
    if (loc.hour, loc.minute) >= (0, 20) and st.get("previsto") != loc.date().isoformat():
        try:
            esito["previsto"] = registra_previsto(loc.date())
            st["previsto"] = loc.date().isoformat()
        except Exception as e:
            esito["errori"].append(f"previsto: {type(e).__name__}: {e}")
    ok = esito["scaricati"] > 0 or (bool(disp) and any(disp.values()) and esito["in_coda"] == 0)
    if ok:
        st["ultimo_ok"] = iso(adesso)
    st["ultimo_giro"] = iso(adesso)
    st["ultimo_esito"] = {k: v for k, v in esito.items() if k not in ("errori", "scartati")} | {
        "errori": esito["errori"][:5], "scartati": esito["scartati"][:5]}
    _salva_stato(st)
    scrivi_indice()
    if esito["errori"]:
        log.warning("Radar: %d errori (primo: %s)", len(esito["errori"]), esito["errori"][0])
    if esito["scartati"]:
        log.warning("Radar: frame scartati dal controllo di qualità: %s", esito["scartati"])
    log.info("Radar: %s", {k: v for k, v in esito.items() if k not in ("errori", "scartati")})
    if not ok and esito["errori"]:
        raise RuntimeError(esito["errori"][0])
    return esito


# ---------------------------------------------------------------------------------------------- letture (rotte)
@lru_cache(maxsize=8)
def _ultimo_file(percorso: str, mtime: float, prodotto: str, quando: str):
    return leggi_archivio_come(Path(percorso), prodotto, da_nome(quando))


def ultimi_frame() -> dict:
    u = _leggi_json(C.RADAR_DATI / "ultimi" / "ultimi.json", {})
    out = {}
    for p in PRODOTTI:
        f = C.RADAR_DATI / "ultimi" / f"{p}.tif"
        if (u.get(p) or {}).get("fine") and f.exists():
            out[p] = (f, u[p]["fine"])
    return out


def comune_vicino(lon: float, lat: float) -> dict | None:
    cm = comuni()
    if cm is None or cm.empty:
        return None
    d = (cm.lat.values - lat) ** 2 + ((cm.lon.values - lon) * math.cos(math.radians(lat))) ** 2
    i = int(np.argmin(d))
    km = math.sqrt(float(d[i])) * 111.2
    return {"istat": str(cm.istat.iloc[i]), "nome": str(cm.nome.iloc[i]), "distanza_km": round(km, 1)} if km < 25 else None


def punto(lon: float, lat: float) -> dict:
    valori = {}
    for p, (f, quando) in ultimi_frame().items():
        try:
            g = _ultimo_file(str(f), f.stat().st_mtime, p, quando)
            v = g.sample([(lon, lat)])[0]
        except Exception as e:
            log.warning("Radar: lettura di %s non riuscita: %s", p, e)
            v = None
        valori[p] = {"valore": None if v is None else round(v, 1), "unita": UNITA[p], "fine": iso(da_nome(quando)),
                     "descrizione": DESCRIZIONE[p]}
    return {"lon": lon, "lat": lat, "valori": valori, "comune": comune_vicino(lon, lat), "fonte": FONTE,
            "licenze": LICENZE, "avvertenze": AVVERTENZE}


def scheda_comune(istat: str, giorni: int = 30) -> dict:
    cm = comuni()
    riga = cm[cm.istat == istat] if cm is not None else None
    if riga is None or riga.empty:
        raise HTTPException(404, "comune non trovato")
    oggi = dt.datetime.now(ROMA).date()
    gg = giornalieri(istat, giorni, oggi)
    adesso = dt.datetime.now(UTC)
    tre = serie_comune(istat, "CUM3", adesso - dt.timedelta(days=7), adesso)
    prev = previsti(istat, oggi - dt.timedelta(days=giorni), oggi)
    return {"istat": istat, "nome": str(riga.nome.iloc[0]), "lat": float(riga.lat.iloc[0]), "lon": float(riga.lon.iloc[0]),
            "giornalieri": [{**g, "previsto_mm": prev.get(g["data"])} for g in gg], "tre_ore": tre,
            "nota_giornalieri": "pioggia del giorno (ora italiana) dal Merging CUM24 della mezzanotte successiva; "
                                "previsto: previsione del sito registrata a inizio giornata (ICON-2I → IFS)",
            "fonte": FONTE, "licenze": LICENZE}


def stato() -> dict:
    st = _stato()
    ind = _leggi_json(C.RADAR_DATI / "indice.json", {})
    fr = {p: (ind.get("prodotti", {}).get(p) or {}).get("frame", []) for p in PRODOTTI}
    arch = C.RADAR_DATI / "archivio"
    peso = sum(f.stat().st_size for f in arch.rglob("*.tif")) if arch.is_dir() else 0
    return {"raccolta_dal": st.get("raccolta_dal"), "ultimo_giro": st.get("ultimo_giro"), "ultimo_ok": st.get("ultimo_ok"),
            "frame": {p: {"n": len(v), "primo": v[0] if v else None, "ultimo": v[-1] if v else None} for p, v in fr.items()},
            "ultimi": _leggi_json(C.RADAR_DATI / "ultimi" / "ultimi.json", {}), "archivio_gb": round(peso / 1e9, 3),
            "archivio_anni": C.RADAR_ARCHIVIO_ANNI, "fonte": FONTE, "licenze": LICENZE, "avvertenze": AVVERTENZE}


# ---------------------------------------------------------------------------------------------- rotte
router = APIRouter(prefix="/api/radar")


def _risposta(dati, max_age: int) -> JSONResponse:
    return JSONResponse(dati, headers={"Cache-Control": f"public, max-age={max_age}"})


@router.get("/stato")
def rotta_stato(request: Request):
    P.limita(request, "radar")
    return _risposta(stato(), 60)


@router.get("/punto")
def rotta_punto(request: Request, lat: float, lon: float):
    P.limita(request, "radar")
    if not (LAT0 <= lat <= LAT1 and LON0 <= lon <= LON1):
        raise HTTPException(422, "punto fuori dall'Italia")
    return _risposta(punto(lon, lat), 300)


@router.get("/comune/{istat}")
def rotta_comune(request: Request, istat: str, giorni: int = 30):
    P.limita(request, "radar")
    if not re.fullmatch(r"\d{6}", istat):
        raise HTTPException(422, "istat: 6 cifre")
    return _risposta(scheda_comune(istat, max(1, min(400, giorni))), 600)


# ---------------------------------------------------------------------------------------------- thread del worker
class Errori:
    """Giri falliti (come per le interruzioni): un'email solo quando non va a buon fine nessun giro da più di
    RADAR_AVVISO_ORE ore, una per episodio."""
    def __init__(self, ore: float = 12.0):
        self.ore, self.n, self.avvisato = ore, 0, False
        u = _stato().get("ultimo_ok")
        self.ultimo_ok = dt.datetime.fromisoformat(u.replace("Z", "+00:00")).timestamp() if u else None

    def esegui(self, f, adesso: float) -> bool:
        try:
            f()
        except Exception as e:
            self.n += 1
            log.warning("Radar: giro fallito (%d di fila): %s: %s", self.n, type(e).__name__, e)
            if self.ultimo_ok is None:
                self.ultimo_ok = adesso
            if not self.avvisato and adesso - self.ultimo_ok > self.ore * 3600:
                from . import avvisi
                self.avvisato = True
                avvisi.invia(f"dati pluviometrici: DPC non letto da più di {self.ore:g} ore",
                             f"{self.n} giri falliti di fila; ultimo errore: {type(e).__name__}: {e}\n\nLe chiamate "
                             "all'API radar del DPC non sono documentate: se il servizio è cambiato, controllare la "
                             "versione della libreria dpc-radar (fase4-server/api/requirements.txt).")
            return False
        self.n, self.avvisato, self.ultimo_ok = 0, False, adesso
        return True


def ciclo(fermo: threading.Event | None = None) -> None:
    import time
    fermo = fermo or threading.Event()
    errori = Errori(C.RADAR_AVVISO_ORE)
    while not fermo.is_set():
        errori.esegui(giro, time.time())
        passo = C.RADAR_MIN * 60
        # 4 minuti dopo il multiplo di 30 minuti: il DPC pubblica il frame qualche minuto dopo l'ora che porta
        fermo.wait(max(60.0, passo - (time.time() % passo) + 240))
