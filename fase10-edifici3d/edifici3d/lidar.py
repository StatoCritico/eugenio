"""LiDAR: DSM ridotto e falde dei tetti per corpo di fabbrica (Fase C; § 5 «Tetti dal DSM», § 7 e § 11 della proposta).

Ingressi, per tessera (1×1 km nella zona vera, più piccola nel campione sintetico), nel sistema della zona (EPSG:7791):
- DSM raster (GeoTIFF: primo impulso, o ultimo impulso dove c'è) oppure nuvola di punti LAS/LAZ classificata;
- DTM raster (RER 0,5 m dal WCS, DTM 5 m della Fase A) oppure i punti di terreno (classe 2) dello stesso LAS.

Uscite:
- **DSM ridotto**: griglia a 1 m, int16 in decimetri (quota s.l.m. × 10), vuoti = −32768, solo attorno agli edifici
  (fascia `maschera_m`), COG compresso. Lo stesso formato per il DTM usato, così i corpi a cavallo di due tessere si
  rielaborano quando arriva la tessera vicina senza riscaricare nulla.
- **Falde per corpo**: punti del DSM dentro la sagoma meno ~1 m di bordo; altezza = mediana (DSM − DTM); si provano
  piano orizzontale, una falda, capanna (due falde, colmo lungo uno dei due assi del rettangolo minimo) e padiglione
  (quattro falde) e si sceglie il più semplice che riduce davvero l'errore; errore alto (RMSE > `RMSE_MAX`) o pendenza
  < `PENDENZA_MIN` → tetto piano. Per ogni falda: pendenza (°), orientamento (azimut della discesa, gradi da nord in
  senso orario: 180 = sud), area in pianta, superficie inclinata, quota alta e bassa, errore. Un edificio presente nella
  sagoma ma non nel rilievo (copertura scarsa o DSM ≈ DTM) resta con la fonte successiva («non presente nel rilievo»).

Solo geometria e statistica di base (minimi quadrati): nessun coefficiente di norme.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from shapely.geometry import Polygon, MultiPolygon, box, mapping, Point
from shapely.geometry.base import BaseGeometry
from shapely import affinity
from shapely.prepared import prep

PASSO = 1.0                 # m: griglia del DSM ridotto
SCALA_DM = 10               # int16 in decimetri
VUOTO_I16 = -32768
BORDO = 1.0                 # m di bordo tolti dalla sagoma prima di campionare
RMSE_MAX = 0.5              # m: oltre, tetto irregolare → piano (§ 5, da tarare tra 0,3 e 0,5)
PENDENZA_MIN = 5.0          # °: sotto, tetto piano
MIGLIORA_REL = 0.30         # un modello più complesso deve ridurre l'RMSE di almeno il 30 % …
MIGLIORA_ASS = 0.05         # … e di almeno 5 cm
MIN_PUNTI = 12              # punti minimi per corpo
MIN_PUNTI_FALDA = 6
ALTEZZA_MIN = 1.5           # m: sotto, il corpo non c'è nel rilievo
COPERTURA_MIN = 0.3         # frazione minima di celle valide dentro la sagoma ridotta
SALTO_MIN = 2.5             # m: due gruppi di altezze separati da più di così → salto da segnalare (§ 7)
SETTORI = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]


def settore(az: float) -> str:
    return SETTORI[int(((az + 22.5) % 360) // 45)]


# ============================================================================================== griglie
@dataclass
class Griglia:
    """Raster in memoria: valori in metri (float32, NaN = vuoto), origine in alto a sinistra, passo in metri."""
    z: np.ndarray
    x0: float
    y1: float
    passo: float

    @property
    def forma(self):
        return self.z.shape

    @property
    def limiti(self):
        h, w = self.z.shape
        return self.x0, self.y1 - h * self.passo, self.x0 + w * self.passo, self.y1

    def centri(self):
        h, w = self.z.shape
        xs = self.x0 + self.passo * (np.arange(w) + 0.5)
        ys = self.y1 - self.passo * (np.arange(h) + 0.5)
        return xs, ys

    def valore(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Valore della cella che contiene (x, y) (NaN fuori)."""
        h, w = self.z.shape
        c = np.floor((np.asarray(x) - self.x0) / self.passo).astype(int)
        r = np.floor((self.y1 - np.asarray(y)) / self.passo).astype(int)
        ok = (c >= 0) & (c < w) & (r >= 0) & (r < h)
        out = np.full(np.shape(x), np.nan, dtype="float64")
        out[ok] = self.z[r[ok], c[ok]]
        return out


def griglia_da_punti(x, y, z, riquadro, passo: float = PASSO, modo: str = "max") -> Griglia:
    """Punti → griglia (massimo per il DSM, minimo per il terreno). Celle vuote = NaN."""
    x0, y0, x1, y1 = riquadro
    w = max(1, int(round((x1 - x0) / passo)))
    h = max(1, int(round((y1 - y0) / passo)))
    x = np.asarray(x, dtype="float64"); y = np.asarray(y, dtype="float64"); z = np.asarray(z, dtype="float64")
    c = np.floor((x - x0) / passo).astype(np.int64)
    r = np.floor((y1 - y) / passo).astype(np.int64)
    ok = (c >= 0) & (c < w) & (r >= 0) & (r < h) & np.isfinite(z)
    idx = r[ok] * w + c[ok]
    zz = z[ok]
    piena = np.full(h * w, -np.inf if modo == "max" else np.inf)
    if modo == "max":
        np.maximum.at(piena, idx, zz)
    else:
        np.minimum.at(piena, idx, zz)
    piena[~np.isfinite(piena)] = np.nan
    return Griglia(piena.reshape(h, w).astype("float32"), x0, y1, passo)


def riempi_buchi(g: Griglia, passi: int = 2) -> Griglia:
    """Buchi piccoli (celle senza punti) riempiti con la media delle vicine valide, al più `passi` volte."""
    z = g.z.astype("float64").copy()
    for _ in range(passi):
        vuoti = np.isnan(z)
        if not vuoti.any():
            break
        somma = np.zeros_like(z); conta = np.zeros_like(z)
        piena = np.where(vuoti, 0.0, z)
        valida = (~vuoti).astype("float64")
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                somma += np.roll(np.roll(piena, dy, 0), dx, 1)
                conta += np.roll(np.roll(valida, dy, 0), dx, 1)
        riempibili = vuoti & (conta >= 3)
        z[riempibili] = somma[riempibili] / conta[riempibili]
    return Griglia(z.astype("float32"), g.x0, g.y1, g.passo)


def terreno_interpolato(g: Griglia) -> Griglia:
    """DTM dai punti di terreno: i vuoti (sotto gli edifici) presi dal punto valido più vicino (scipy, se c'è)."""
    z = g.z
    vuoti = np.isnan(z)
    if not vuoti.any() or vuoti.all():
        return g
    try:
        from scipy.ndimage import distance_transform_edt
        _, (ri, ci) = distance_transform_edt(vuoti, return_indices=True)
        piena = z[ri, ci]
    except ImportError:                                   # senza scipy: media globale dei validi
        piena = np.where(vuoti, np.nanmedian(z), z)
    return Griglia(piena.astype("float32"), g.x0, g.y1, g.passo)


def ricampiona(g: Griglia, riquadro, passo: float = PASSO) -> Griglia:
    """Griglia qualsiasi → griglia di passo `passo` sul riquadro (cella più vicina; per il DTM 5 m va bene)."""
    x0, y0, x1, y1 = riquadro
    w = max(1, int(round((x1 - x0) / passo))); h = max(1, int(round((y1 - y0) / passo)))
    xs = x0 + passo * (np.arange(w) + 0.5); ys = y1 - passo * (np.arange(h) + 0.5)
    gx, gy = np.meshgrid(xs, ys)
    if passo >= g.passo:   # da fine a grosso: massimo per il DSM sarebbe meglio, ma qui serve la quota tipica: media
        k = int(round(passo / g.passo))
        if k > 1 and abs(k * g.passo - passo) < 1e-6:
            sub = g.passo * (np.arange(k) + 0.5) - passo / 2
            acc = np.zeros_like(gx); n = np.zeros_like(gx)
            for dx in sub:
                for dy in sub:
                    v = g.valore(gx + dx, gy + dy)
                    ok = np.isfinite(v)
                    acc[ok] += v[ok]; n[ok] += 1
            z = np.where(n > 0, acc / np.maximum(n, 1), np.nan)
            return Griglia(z.astype("float32"), x0, y1, passo)
    return Griglia(g.valore(gx, gy).astype("float32"), x0, y1, passo)


# ============================================================================================== lettura e scrittura
def leggi_raster(percorso, riquadro=None, max_celle: int = 30_000_000) -> Griglia:
    """GeoTIFF (float o int16 in decimetri con l'etichetta SCALA_DM) → Griglia in metri, ritagliata sul riquadro."""
    import rasterio
    from rasterio.windows import from_bounds
    with rasterio.open(percorso) as src:
        if src.width * src.height > max_celle:
            raise ValueError(f"raster troppo grande ({src.width}×{src.height})")
        if abs(src.transform.b) > 1e-9 or abs(src.transform.d) > 1e-9:
            raise ValueError("raster ruotato non gestito")
        passo = abs(src.transform.a)
        if riquadro:
            win = from_bounds(*riquadro, transform=src.transform).round_offsets().round_lengths()
            a = src.read(1, window=win, boundless=True, masked=True)
            t = src.window_transform(win)
        else:
            a = src.read(1, masked=True); t = src.transform
        scala = float(src.tags().get("SCALA_DM", 0) or 0)
        z = a.astype("float64").filled(np.nan)
        if src.nodata is not None and not np.isnan(src.nodata):
            z[z == src.nodata] = np.nan
        z[z < -1000] = np.nan                     # vuoti scritti come −9999 o −32768 senza nodata dichiarato
        if scala:
            z = z / scala
    return Griglia(z.astype("float32"), t.c, t.f, passo)


def scrivi_ridotto(g: Griglia, dest, crs: str = "EPSG:7791", maschera: np.ndarray | None = None, etichette: dict | None = None):
    """Griglia (m) → GeoTIFF int16 in decimetri, compresso a blocchi (COG se il driver c'è), vuoti = −32768."""
    import rasterio
    from rasterio.transform import from_origin
    from pathlib import Path
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    z = g.z.astype("float64")
    if maschera is not None:
        z = np.where(maschera, z, np.nan)
    q = np.where(np.isfinite(z), np.clip(np.round(z * SCALA_DM), -32767, 32767), VUOTO_I16).astype("int16")
    h, w = q.shape
    tmp = dest.with_name(dest.name + ".tmp.tif")
    prof = dict(driver="GTiff", width=w, height=h, count=1, dtype="int16", crs=crs, nodata=VUOTO_I16,
                transform=from_origin(g.x0, g.y1, g.passo, g.passo), compress="DEFLATE", predictor=2)
    if w >= 256 and h >= 256:
        prof.update(tiled=True, blockxsize=256, blockysize=256)
    with rasterio.open(tmp, "w", **prof) as f:
        f.write(q, 1)
        f.update_tags(SCALA_DM=str(SCALA_DM), UNITA="decimetri sul livello del mare", **(etichette or {}))
    try:
        from rasterio.shutil import copy as rcopy
        with rasterio.open(tmp) as src:
            fin = dest.with_name(dest.name + ".cog.tif")
            rcopy(src, fin, driver="COG", COMPRESS="DEFLATE", PREDICTOR="2", BLOCKSIZE="256", OVERVIEWS="NONE")
        fin.replace(dest)
        tmp.unlink(missing_ok=True)
    except Exception:                              # senza driver COG resta il GeoTIFF a blocchi
        tmp.replace(dest)
    return dest


def leggi_las(percorso, riquadro=None, max_punti: int = 60_000_000) -> dict:
    """LAS/LAZ (laspy) → array x, y, z, classe, numero di ritorno. Il file è un dato non fidato: si controlla il numero di
    punti dichiarato prima di leggere e si scartano coordinate non finite."""
    import laspy
    with laspy.open(str(percorso)) as f:
        n = int(f.header.point_count)
        if n > max_punti:
            raise ValueError(f"LAS con troppi punti ({n})")
        p = f.read()
    x = np.asarray(p.x, dtype="float64"); y = np.asarray(p.y, dtype="float64"); z = np.asarray(p.z, dtype="float64")
    cl = np.asarray(p.classification, dtype="int16")
    rit = np.asarray(p.return_number, dtype="int16")
    ok = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    if riquadro:
        x0, y0, x1, y1 = riquadro
        ok &= (x >= x0) & (x < x1) & (y >= y0) & (y < y1)
    return {"x": x[ok], "y": y[ok], "z": z[ok], "classe": cl[ok], "ritorno": rit[ok]}


def griglie_da_las(punti: dict, riquadro, passo: float = PASSO, classi_dsm=(6,), classe_terreno: int = 2) -> tuple[Griglia, Griglia]:
    """DSM (massimo dei primi ritorni; se il LAS ha la classe Edifici si tiene il massimo di tutto, ma il tetto è quello
    della classe 6) e DTM (minimo della classe terreno, vuoti interpolati)."""
    x, y, z, cl, rit = punti["x"], punti["y"], punti["z"], punti["classe"], punti["ritorno"]
    primi = rit <= 1
    dsm = griglia_da_punti(x[primi], y[primi], z[primi], riquadro, passo, "max")
    edif = np.isin(cl, list(classi_dsm))
    if edif.any():   # dove ci sono punti della classe Edifici il DSM prende quelli (niente rami sopra i tetti)
        de = griglia_da_punti(x[edif], y[edif], z[edif], riquadro, passo, "max")
        dsm = Griglia(np.where(np.isfinite(de.z), de.z, dsm.z), dsm.x0, dsm.y1, passo)
    t = cl == classe_terreno
    dtm = griglia_da_punti(x[t], y[t], z[t], riquadro, passo, "min") if t.any() else Griglia(np.full_like(dsm.z, np.nan), dsm.x0, dsm.y1, passo)
    return riempi_buchi(dsm, 2), terreno_interpolato(dtm)


def maschera_edifici(g: Griglia, sagome: list[BaseGeometry], fascia: float) -> np.ndarray:
    """Celle entro `fascia` metri da una sagoma (il DSM ridotto tiene solo le aree costruite)."""
    import rasterio.features
    from rasterio.transform import from_origin
    if not sagome:
        return np.zeros(g.z.shape, dtype=bool)
    geoms = [s.buffer(fascia) for s in sagome]
    return rasterio.features.geometry_mask(geoms, out_shape=g.z.shape, transform=from_origin(g.x0, g.y1, g.passo, g.passo),
                                           invert=True, all_touched=True)


def unisci(griglie: list[Griglia], riquadro, passo: float = PASSO) -> Griglia:
    """Mosaico di griglie dello stesso passo sul riquadro (le celle valide successive non sovrascrivono le prime)."""
    x0, y0, x1, y1 = riquadro
    w = max(1, int(round((x1 - x0) / passo))); h = max(1, int(round((y1 - y0) / passo)))
    out = Griglia(np.full((h, w), np.nan, dtype="float32"), x0, y1, passo)
    xs, ys = out.centri()
    gx, gy = np.meshgrid(xs, ys)
    for g in griglie:
        v = g.valore(gx, gy)
        vuoti = np.isnan(out.z)
        out.z[vuoti] = v[vuoti]
    return out


# ============================================================================================== modelli di tetto
def _piano_ls(x, y, z):
    """z = a·x + b·y + c ai minimi quadrati; restituisce (a, b, c, residui)."""
    A = np.column_stack([x, y, np.ones_like(x)])
    coef, *_ = np.linalg.lstsq(A, z, rcond=None)
    return coef[0], coef[1], coef[2], z - A @ coef


def _rmse(res) -> float:
    return float(np.sqrt(np.mean(np.square(res)))) if len(res) else float("inf")


@dataclass
class Falda:
    a: float
    b: float
    c: float
    regione: BaseGeometry
    punti: int
    rmse: float

    @property
    def pendenza(self) -> float:
        return math.degrees(math.atan(math.hypot(self.a, self.b)))

    @property
    def orientamento(self) -> float:
        """Azimut della discesa (gradi da nord in senso orario): la direzione verso cui la falda guarda."""
        if math.hypot(self.a, self.b) < 1e-9:
            return 180.0
        return (math.degrees(math.atan2(-self.a, -self.b)) + 360) % 360


@dataclass
class Modello:
    nome: str                # piano | monofalda | capanna | padiglione
    parametri: int
    falde: list[Falda]
    rmse: float
    residui: np.ndarray = field(repr=False, default=None)


def _rettangolo(sagoma: BaseGeometry):
    """Rettangolo minimo: centro, versore del lato lungo, semilati (lungo, corto)."""
    r = sagoma.minimum_rotated_rectangle
    cs = list(r.exterior.coords)[:4]
    l1 = math.dist(cs[0], cs[1]); l2 = math.dist(cs[1], cs[2])
    if l1 >= l2:
        u = ((cs[1][0] - cs[0][0]) / max(l1, 1e-9), (cs[1][1] - cs[0][1]) / max(l1, 1e-9)); L, W = l1, l2
    else:
        u = ((cs[2][0] - cs[1][0]) / max(l2, 1e-9), (cs[2][1] - cs[1][1]) / max(l2, 1e-9)); L, W = l2, l1
    c = r.centroid
    return (c.x, c.y), u, L / 2, W / 2


def _semipiano(centro, n, offset, grande):
    """Poligono grande della parte con (p − centro)·n ≥ offset."""
    cx, cy = centro
    nx, ny = n
    ux, uy = -ny, nx
    px, py = cx + nx * offset, cy + ny * offset
    return Polygon([(px + ux * grande, py + uy * grande), (px - ux * grande, py - uy * grande),
                    (px - ux * grande + nx * grande, py - uy * grande + ny * grande),
                    (px + ux * grande + nx * grande, py + uy * grande + ny * grande)])


def _fit_regioni(x, y, z, etichette, regioni, nome, parametri) -> Modello | None:
    falde, residui = [], np.zeros_like(z)
    for k, reg in enumerate(regioni):
        sel = etichette == k
        if sel.sum() < MIN_PUNTI_FALDA:
            return None
        a, b, c, res = _piano_ls(x[sel], y[sel], z[sel])
        residui[sel] = res
        falde.append(Falda(a, b, c, reg, int(sel.sum()), _rmse(res)))
    return Modello(nome, parametri, falde, _rmse(residui), residui)


def modelli(x, y, z, sagoma: BaseGeometry) -> list[Modello]:
    """I quattro modelli provati sullo stesso insieme di punti (coordinate già centrate)."""
    out = []
    c0 = float(np.mean(z))
    res0 = z - c0
    out.append(Modello("piano", 1, [Falda(0.0, 0.0, c0, sagoma, len(z), _rmse(res0))], _rmse(res0), res0))
    a, b, c, res = _piano_ls(x, y, z)
    out.append(Modello("monofalda", 3, [Falda(a, b, c, sagoma, len(z), _rmse(res))], _rmse(res), res))
    centro, u, sl, sc = _rettangolo(sagoma)
    grande = 4 * (sl + sc) + 10
    migliore = None
    for asse in (u, (-u[1], u[0])):                       # colmo lungo il lato lungo o lungo il corto
        n = (-asse[1], asse[0])                            # normale al colmo
        v = (x - centro[0]) * n[0] + (y - centro[1]) * n[1]
        semi = sc if asse == u else sl
        for off in (0.0, -0.15 * semi, 0.15 * semi, -0.3 * semi, 0.3 * semi):
            et = (v < off).astype(int)
            regioni = [sagoma.intersection(_semipiano(centro, n, off, grande)),
                       sagoma.intersection(_semipiano(centro, (-n[0], -n[1]), -off, grande))]
            m = _fit_regioni(x, y, z, et, regioni, "capanna", 6)
            if m and (migliore is None or m.rmse < migliore.rmse):
                migliore = m
    if migliore:
        out.append(migliore)
    # padiglione: ogni punto va alla falda del lato più vicino del rettangolo (scheletro del rettangolo)
    n = (-u[1], u[0])
    s = (x - centro[0]) * u[0] + (y - centro[1]) * u[1]
    t = (x - centro[0]) * n[0] + (y - centro[1]) * n[1]
    dist = np.stack([sl - s, sl + s, sc - t, sc + t])           # verso +u, −u, +n, −n
    et = np.argmin(dist, axis=0)
    regioni = _regioni_padiglione(centro, u, sl, sc)
    regioni = [sagoma.intersection(r) for r in regioni]
    m = _fit_regioni(x, y, z, et, regioni, "padiglione", 12)
    if m:
        out.append(m)
    return out


def _regioni_padiglione(centro, u, sl, sc):
    """Le quattro falde del rettangolo (lati +u, −u, +n, −n), dai vertici e dai due estremi del colmo."""
    cx, cy = centro
    n = (-u[1], u[0])
    P = lambda s, t: (cx + u[0] * s + n[0] * t, cy + u[1] * s + n[1] * t)
    r = max(sl - sc, 0.0)
    g = 1.05                                          # un po' più grandi del rettangolo: si tagliano con la sagoma
    A, B, C, D = P(sl * g, sc * g), P(-sl * g, sc * g), P(-sl * g, -sc * g), P(sl * g, -sc * g)
    E1, E2 = P(r, 0), P(-r, 0)
    return [Polygon([D, A, E1]), Polygon([B, C, E2]), Polygon([A, B, E2, E1]), Polygon([C, D, E1, E2])]


def scegli_modello(ms: list[Modello]) -> Modello:
    """Il più semplice che riduce davvero l'errore (MIGLIORA_REL e MIGLIORA_ASS rispetto al migliore finora)."""
    ms = sorted(ms, key=lambda m: m.parametri)
    best = ms[0]
    for m in ms[1:]:
        if m.rmse < best.rmse * (1 - MIGLIORA_REL) and best.rmse - m.rmse > MIGLIORA_ASS:
            best = m
    return best


def _salto(h: np.ndarray) -> float | None:
    """Due gruppi netti di altezze (salto dentro il corpo, § 7): differenza tra i due gruppi, o None."""
    if len(h) < 2 * MIN_PUNTI:
        return None
    s = np.sort(h)
    gaps = np.diff(s)
    k = int(np.argmax(gaps))
    basso, alto = s[:k + 1], s[k + 1:]
    if min(len(basso), len(alto)) < 0.2 * len(s):
        return None
    d = float(np.median(alto) - np.median(basso))
    if d > SALTO_MIN and np.std(basso) < 0.6 and np.std(alto) < 0.6:
        return d
    return None


# ============================================================================================== corpo
def falde_corpo(sagoma: BaseGeometry, dsm: Griglia, dtm: Griglia | None, quota_terreno: float | None = None,
                bordo: float = BORDO) -> dict:
    """Falde e altezze di un corpo dalla sagoma (stesso sistema del DSM). Restituisce un dizionario serializzabile:
    stato («ok», «non presente nel rilievo», «poco coperto»), tetto, falde [...], gronda, colmo, altezza_mediana,
    quota_terreno, rmse, punti, copertura, qualita, note."""
    if not isinstance(sagoma, (Polygon, MultiPolygon)) or sagoma.is_empty:
        return {"stato": "sagoma non valida"}
    s = sagoma if sagoma.is_valid else sagoma.buffer(0)
    interno = s.buffer(-bordo)
    if interno.is_empty or interno.area < 4 * dsm.passo ** 2:
        interno = s.buffer(-min(bordo, 0.25))
    if interno.is_empty:
        interno = s
    x0, y0, x1, y1 = interno.bounds
    xs = np.arange(math.floor(x0 / dsm.passo) * dsm.passo + dsm.passo / 2, x1, dsm.passo)
    ys = np.arange(math.floor(y0 / dsm.passo) * dsm.passo + dsm.passo / 2, y1, dsm.passo)
    if not len(xs) or not len(ys):
        return {"stato": "poco coperto", "punti": 0, "copertura": 0.0}
    gx, gy = np.meshgrid(xs, ys)
    gx = gx.ravel(); gy = gy.ravel()
    import shapely
    dentro = shapely.contains_xy(interno, gx, gy)
    gx, gy = gx[dentro], gy[dentro]
    attesi = max(len(gx), 1)
    z = dsm.valore(gx, gy)
    ok = np.isfinite(z)
    gx, gy, z = gx[ok], gy[ok], z[ok]
    copertura = len(z) / attesi
    if dtm is not None:
        t = dtm.valore(gx, gy)
        if np.isfinite(t).any():
            t = np.where(np.isfinite(t), t, np.nanmedian(t))
        else:
            t = np.full_like(z, quota_terreno if quota_terreno is not None else np.nan)
    else:
        t = np.full_like(z, quota_terreno if quota_terreno is not None else np.nan)
    qt = float(np.nanmin(t)) if np.isfinite(t).any() else quota_terreno
    base = {"punti": int(len(z)), "copertura": round(copertura, 3),
            "quota_terreno": None if qt is None or not math.isfinite(qt) else round(qt, 2)}
    if len(z) < MIN_PUNTI or copertura < COPERTURA_MIN:
        return {**base, "stato": "poco coperto" if len(z) else "non presente nel rilievo"}
    h = z - t
    hm = float(np.nanmedian(h)) if np.isfinite(h).any() else float("nan")
    if not math.isfinite(hm) or hm < ALTEZZA_MIN:
        return {**base, "stato": "non presente nel rilievo", "altezza_mediana": None if not math.isfinite(hm) else round(hm, 2)}
    # tolti gli spigoli anomali (camini, antenne, rami): fuori da mediana ± 4·MAD
    mad = float(np.median(np.abs(h - hm))) or 0.1
    tieni = np.abs(h - hm) <= max(4 * 1.4826 * mad, 1.0)
    if tieni.sum() >= MIN_PUNTI:
        gx, gy, z, t, h = gx[tieni], gy[tieni], z[tieni], t[tieni], h[tieni]
    cx, cy = s.centroid.x, s.centroid.y
    xl, yl = gx - cx, gy - cy
    sag_l = affinity.translate(s, -cx, -cy)
    # le falde si adattano alle quote assolute del DSM (la pendenza del terreno non entra nel tetto); le altezze si
    # riferiscono alla quota del terreno del corpo (minimo del DTM nella sagoma, come la Fase A)
    rif = qt if qt is not None and math.isfinite(qt) else float(np.nanmin(t))
    ms = modelli(xl, yl, z, sag_l)
    m = scegli_modello(ms)
    note = []
    salto = _salto(h)
    if salto:
        note.append(f"salto di altezza di circa {salto:.1f} m dentro il corpo: da dividere")
    tetto = m.nome
    irregolare = m.rmse > RMSE_MAX
    if m.nome != "piano" and max(f.pendenza for f in m.falde) < PENDENZA_MIN:
        tetto = "piano"
    if irregolare:
        tetto = "piano"
        note.append(f"altezze irregolari (RMSE {m.rmse:.2f} m): tetto trattato come piano")
    if tetto == "piano":
        q50 = float(np.median(z)) - rif
        falde = [{"id": "F1", "pendenza": 0.0, "orientamento": 180.0, "settore": "—",
                  "area_pianta": round(s.area, 1), "superficie": round(s.area, 1),
                  "alto": round(q50, 2), "basso": round(q50, 2), "rmse": round(_rmse(z - rif - q50), 3),
                  "punti": int(len(h)), "geometria": _coord(s, cx, cy, 0)}]
        gronda = colmo = q50
    else:
        falde = []
        for k, f in enumerate(m.falde):
            reg = f.regione
            if reg.is_empty or reg.area < 1:
                continue
            vx = np.array([p[0] for p in _vertici(reg)]); vy = np.array([p[1] for p in _vertici(reg)])
            zv = f.a * vx + f.b * vy + f.c - rif
            falde.append({"id": f"F{k + 1}", "pendenza": round(f.pendenza, 1), "orientamento": round(f.orientamento, 1) % 360,
                          "settore": settore(f.orientamento), "area_pianta": round(reg.area, 1),
                          "superficie": round(reg.area / math.cos(math.radians(f.pendenza)), 1),
                          "alto": round(float(zv.max()), 2), "basso": round(float(zv.min()), 2), "rmse": round(f.rmse, 3),
                          "punti": f.punti, "geometria": _coord(reg, cx, cy, 0)})
        # gronda e colmo: estremi delle falde estrapolati fino al bordo della sagoma (i punti stanno ~1 m dentro)
        pred = z - m.residui - rif
        gronda = max(min(f["basso"] for f in falde), float(np.percentile(pred, 1)) - 1.5) if falde else float(np.percentile(pred, 5))
        colmo = max(f["alto"] for f in falde) if falde else float(np.percentile(pred, 98))
    if not falde:
        return {**base, "stato": "poco coperto"}
    qualita = "buona" if (m.rmse <= 0.2 and copertura >= 0.8) else "media" if (m.rmse <= 0.35 and copertura >= 0.6) else "bassa"
    return {**base, "stato": "ok", "tetto": tetto, "modello": m.nome, "falde": falde,
            "gronda": round(gronda, 2), "colmo": round(colmo, 2), "altezza_mediana": round(hm, 2),
            "rmse": round(m.rmse, 3), "qualita": qualita, "note": note,
            "prove": {x.nome: round(x.rmse, 3) for x in ms}}


def _vertici(g: BaseGeometry):
    if isinstance(g, Polygon):
        return list(g.exterior.coords)
    if isinstance(g, MultiPolygon):
        return [p for q in g.geoms for p in q.exterior.coords]
    return [p for q in getattr(g, "geoms", []) if isinstance(q, Polygon) for p in q.exterior.coords]


def _coord(g: BaseGeometry, dx: float, dy: float, cifre: int = 2):
    """Geometria (coordinate locali) riportata nel sistema della zona, come GeoJSON."""
    g = affinity.translate(g, dx, dy) if (dx or dy) else g
    polys = [g] if isinstance(g, Polygon) else [p for p in getattr(g, "geoms", []) if isinstance(p, Polygon)]
    polys = [p for p in polys if p.area >= 0.5]
    if not polys:
        return None
    if len(polys) == 1:
        return {"type": "Polygon", "coordinates": [[[round(x, 2), round(y, 2)] for x, y in polys[0].exterior.coords]]}
    return {"type": "MultiPolygon", "coordinates": [[[[round(x, 2), round(y, 2)] for x, y in p.exterior.coords]] for p in polys]}


def in_wgs84(risultato: dict, crs: str = "EPSG:7791", cifre: int = 7) -> dict:
    """Le geometrie delle falde passano da EPSG:7791 a WGS84 (per le celle della pagina 3D)."""
    from pyproj import Transformer
    t = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    r = dict(risultato)
    falde = []
    for f in risultato.get("falde", []):
        f = dict(f)
        g = f.get("geometria")
        if g:
            def conv(anello):
                xs, ys = t.transform([p[0] for p in anello], [p[1] for p in anello])
                return [[round(a, cifre), round(b, cifre)] for a, b in zip(xs, ys)]
            if g["type"] == "Polygon":
                f["geometria"] = {"type": "Polygon", "coordinates": [conv(a) for a in g["coordinates"]]}
            else:
                f["geometria"] = {"type": "MultiPolygon", "coordinates": [[conv(a) for a in p] for p in g["coordinates"]]}
        falde.append(f)
    r["falde"] = falde
    return r
