"""Corpi dal solo LiDAR e alberi dal DSM (Fase C/E, § 7 della proposta; 05/11/2026).

**Corpi dal solo LiDAR**, per le zone senza unità volumetriche (Bolzano, regioni senza DB topografico con le sagome):
1. altezza sul terreno h = DSM − DTM sulla griglia a 1 m; celle «alte» con h ≥ `SOGLIA` (2,5 m);
2. vegetazione tolta con la **ruvidezza**: deviazione standard di h nelle celle alte di un intorno 3×3 (solo le celle
   alte contano, così il bordo di un tetto non sembra ruvido); oltre `RUVIDEZZA` (0,8 m) la cella è chioma d'albero;
3. **raggruppamento per altezza simile** (§ 7: 1–1,5 m): due celle vicine (4-connessione) stanno nello stesso corpo se
   le loro altezze differiscono meno di `SALTO` (1,25 m); le falde inclinate restano unite (a 1 m un tetto a 31° sale di
   0,6 m), i corpi di altezza diversa si separano al gradino;
4. le celle ruvide ai bordi (gradini tra due corpi) si riassegnano al corpo vicino di altezza compatibile (due giri);
5. corpi sotto `AREA_MIN` (20 m²) scartati (camini, auto, siepi); buchi sotto 25 m² chiusi; sagome semplificate a 0,5 m;
6. i corpi che si toccano formano un **edificio** (un'unità per selezione, totali e report, come nella Fase A).
Altezza = mediana di h nel corpo (le falde si stimano dopo con `lidar.falde_corpo`, come per le UVL); terreno = mediana
del DTM. La licenza della sagoma è quella del DSM (CC0/CC BY): archivio aperto.

**Alberi dal DSM**: le celle alte che non sono edifici (chiome, ma anche tettoie leggere e mezzi alti) diventano ostacoli
per le ombre: quadrati di 2 m con l'altezza massima della chioma, solo entro `fascia` dagli edifici. La pagina 3D li
aggiunge agli ostacoli dell'orizzonte (FV e facciate) e li disegna in verde.

Solo geometria e statistica di base: nessun coefficiente di norme.
"""
from __future__ import annotations

import math

import numpy as np

from .lidar import Griglia

SOGLIA = 2.5            # m sopra il terreno
RUVIDEZZA = 0.8         # m: deviazione standard 3×3 oltre la quale la cella è vegetazione
SALTO = 1.25            # m: differenza massima tra celle vicine dello stesso corpo (§ 7: 1–1,5 m)
AREA_MIN = 20.0         # m²: corpi più piccoli scartati (§ 7: 20–25 m²)
BUCO_MIN = 25.0         # m²: buchi più piccoli chiusi
PASSO_ALBERI = 2.0      # m: lato dei quadrati degli alberi


def altezza_sul_terreno(dsm: Griglia, dtm: Griglia) -> np.ndarray:
    if dsm.z.shape != dtm.z.shape:
        raise ValueError("DSM e DTM devono stare sulla stessa griglia")
    return (dsm.z.astype("float64") - dtm.z.astype("float64"))


def ruvidezza(h: np.ndarray, alta: np.ndarray) -> np.ndarray:
    """Deviazione standard di h nell'intorno 3×3, contando solo le celle alte."""
    from scipy.ndimage import uniform_filter
    m = alta.astype("float64")
    hz = np.where(alta, h, 0.0)
    n = uniform_filter(m, 3, mode="constant")
    s1 = uniform_filter(hz, 3, mode="constant")
    s2 = uniform_filter(hz * hz, 3, mode="constant")
    with np.errstate(invalid="ignore", divide="ignore"):
        media = s1 / n
        var = s2 / n - media * media
    return np.sqrt(np.clip(np.nan_to_num(var, nan=0.0), 0, None))


def _componenti(h: np.ndarray, maschera: np.ndarray, salto: float) -> np.ndarray:
    """Etichette (0 = nessuna) dei gruppi di celle della maschera unite se vicine e con |Δh| < salto."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    H, W = h.shape
    idx = np.arange(H * W).reshape(H, W)
    righe, colonne = [], []
    for a, b, ha, hb, ma, mb in ((idx[:, :-1], idx[:, 1:], h[:, :-1], h[:, 1:], maschera[:, :-1], maschera[:, 1:]),
                                 (idx[:-1, :], idx[1:, :], h[:-1, :], h[1:, :], maschera[:-1, :], maschera[1:, :])):
        ok = ma & mb & (np.abs(ha - hb) < salto)
        righe.append(a[ok]); colonne.append(b[ok])
    r = np.concatenate(righe) if righe else np.array([], dtype=int)
    c = np.concatenate(colonne) if colonne else np.array([], dtype=int)
    g = coo_matrix((np.ones(len(r), dtype=np.int8), (r, c)), shape=(H * W, H * W))
    _, lab = connected_components(g, directed=False)
    lab = lab.reshape(H, W) + 1
    lab[~maschera] = 0
    # rinumera 1..n
    uniche, inv = np.unique(lab, return_inverse=True)
    lab = inv.reshape(H, W)
    if uniche[0] != 0:
        lab = lab + 1
    return lab


def segmenta(dsm: Griglia, dtm: Griglia, soglia: float = SOGLIA, ruvido: float = RUVIDEZZA, salto: float = SALTO,
             area_min: float = AREA_MIN) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(etichette dei corpi, altezze h, maschera delle chiome) sulla griglia del DSM."""
    h = altezza_sul_terreno(dsm, dtm)
    valida = np.isfinite(h)
    alta = valida & (h >= soglia)
    r = ruvidezza(np.nan_to_num(h), alta)
    liscia = alta & (r <= ruvido)
    lab = _componenti(np.nan_to_num(h), liscia, salto)
    cella = dsm.passo ** 2
    conteggi = np.bincount(lab.ravel())
    piccoli = np.where(conteggi * cella < area_min)[0]
    piccoli = piccoli[piccoli > 0]
    if len(piccoli):
        lab[np.isin(lab, piccoli)] = 0
    # celle ruvide ai bordi: al corpo vicino con altezza compatibile (mediana del corpo ± salto), due giri
    if lab.max() > 0:
        from scipy.ndimage import median as med_lab
        etich = np.arange(1, lab.max() + 1)
        mediane = np.zeros(lab.max() + 1)
        presenti = np.unique(lab[lab > 0])
        mediane[presenti] = med_lab(np.nan_to_num(h), lab, presenti)
        for _ in range(2):
            libere = alta & (lab == 0)
            if not libere.any():
                break
            nuovo = lab.copy()
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                vic = np.roll(np.roll(lab, dy, 0), dx, 1)
                if dy == 1: vic[0, :] = 0
                if dy == -1: vic[-1, :] = 0
                if dx == 1: vic[:, 0] = 0
                if dx == -1: vic[:, -1] = 0
                ok = libere & (nuovo == 0) & (vic > 0) & (np.abs(np.nan_to_num(h) - mediane[vic]) < salto)
                nuovo[ok] = vic[ok]
            lab = nuovo
        del etich
    chiome = alta & (lab == 0)
    return lab, h, chiome


def corpi_da_lidar(dsm: Griglia, dtm: Griglia, prefisso: str, licenza: str, fonte: str, crs: str = "EPSG:7791",
                   **kw) -> list:
    """Corpi (`modello.Corpo`) dal DSM e dal DTM di una tessera; id «<prefisso>_<n>», edifici «<prefisso>_E<m>»."""
    import rasterio.features
    from rasterio.transform import from_origin
    from shapely.geometry import shape, Polygon, MultiPolygon
    from shapely.ops import unary_union
    from .modello import Corpo
    lab, h, _ = segmenta(dsm, dtm, **kw)
    if lab.max() == 0:
        return []
    tr = from_origin(dsm.x0, dsm.y1, dsm.passo, dsm.passo)
    pezzi: dict[int, list] = {}
    for g, v in rasterio.features.shapes(lab.astype("int32"), mask=lab > 0, transform=tr, connectivity=4):
        pezzi.setdefault(int(v), []).append(shape(g))
    sagome = {}
    for k, gs in pezzi.items():
        p = unary_union(gs)
        if isinstance(p, MultiPolygon):
            p = max(p.geoms, key=lambda x: x.area)
        p = Polygon(p.exterior, [r for r in p.interiors if Polygon(r).area >= BUCO_MIN]).simplify(0.5, preserve_topology=True)
        if p.is_valid and p.area >= kw.get("area_min", AREA_MIN):
            sagome[k] = p
    # edifici: corpi che si toccano (celle adiacenti con etichette diverse)
    padre = {k: k for k in sagome}

    def trova(x):
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x
    for a, b in ((lab[:, :-1], lab[:, 1:]), (lab[:-1, :], lab[1:, :])):
        ok = (a > 0) & (b > 0) & (a != b)
        for x, y in set(zip(a[ok].tolist(), b[ok].tolist())):
            if x in padre and y in padre:
                padre[trova(x)] = trova(y)
    gruppi = {}
    for k in sorted(sagome):
        gruppi.setdefault(trova(k), len(gruppi) + 1)
    dtm_z = dtm.z.astype("float64")
    out = []
    for n, k in enumerate(sorted(sagome), 1):
        sel = lab == k
        hk = h[sel]
        q = float(np.nanmedian(dtm_z[sel]))
        alt = float(np.nanmedian(hk))
        c = Corpo(id=f"{prefisso}_{n}", edificio=f"{prefisso}_E{gruppi[trova(k)]}", sagoma=sagome[k],
                  quota_terreno=round(q, 2), gronda=round(alt, 2), tetto="piano", fonte_sagoma=f"{fonte} – raggruppamento per altezza (§ 7)",
                  licenza=licenza, fonte_altezza=f"{fonte}: mediana di DSM − DTM",
                  qualita="sagoma dal DSM a 1 m (±1 m), da controllare sull'ortofoto",
                  extra={"celle": int(sel.sum()), "h_min": round(float(np.nanpercentile(hk, 5)), 2),
                         "h_max": round(float(np.nanpercentile(hk, 95)), 2), "dal_lidar": True})
        out.append(c)
    return out


def alberi(dsm: Griglia, dtm: Griglia, sagome=(), fascia: float = 50.0, passo: float = PASSO_ALBERI, **kw) -> list[list[float]]:
    """Chiome (celle alte che non sono edifici) → quadrati di `passo` m: [x, y, h sopra il terreno, quota del terreno],
    centro del quadrato nel sistema della zona; solo entro `fascia` dalle sagome (se date)."""
    _, h, chiome = segmenta(dsm, dtm, **kw)
    if sagome:
        from shapely.ops import unary_union
        import rasterio.features
        from rasterio.transform import from_origin
        vicino = rasterio.features.geometry_mask([unary_union(list(sagome)).buffer(fascia)], out_shape=h.shape,
                                                 transform=from_origin(dsm.x0, dsm.y1, dsm.passo, dsm.passo), invert=True)
        # le chiome che cadono dentro una sagoma (rami sopra il tetto) non contano: lì vince il tetto
        dentro = rasterio.features.geometry_mask(list(sagome), out_shape=h.shape,
                                                 transform=from_origin(dsm.x0, dsm.y1, dsm.passo, dsm.passo), invert=True)
        chiome = chiome & vicino & ~dentro
    if not chiome.any():
        return []
    k = max(1, int(round(passo / dsm.passo)))
    H, W = h.shape
    Hk, Wk = math.ceil(H / k), math.ceil(W / k)
    hp = np.full((Hk * k, Wk * k), np.nan)
    hp[:H, :W] = np.where(chiome, h, np.nan)
    tp = np.full((Hk * k, Wk * k), np.nan)
    tp[:H, :W] = np.where(chiome, dtm.z, np.nan)
    blocchi = hp.reshape(Hk, k, Wk, k)
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            hmax = np.nanmax(blocchi, axis=(1, 3))
            tmed = np.nanmedian(tp.reshape(Hk, k, Wk, k), axis=(1, 3))
    out = []
    lato = k * dsm.passo
    for r, c in zip(*np.where(np.isfinite(hmax))):
        x = dsm.x0 + (c + 0.5) * lato
        y = dsm.y1 - (r + 0.5) * lato
        out.append([round(float(x), 2), round(float(y), 2), round(float(hmax[r, c]), 1), round(float(tmed[r, c]), 1)])
    return out


def alberi_in_wgs84(punti: list[list[float]], crs: str, lato: float = PASSO_ALBERI) -> list[list[float]]:
    """[x, y, h, q] nel sistema della zona → [lon, lat, h, q, lato] per le celle della pagina 3D."""
    if not punti:
        return []
    from pyproj import Transformer
    t = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    xs, ys = zip(*[(p[0], p[1]) for p in punti])
    lon, lat = t.transform(xs, ys)
    return [[round(a, 7), round(b, 7), p[2], p[3], lato] for a, b, p in zip(lon, lat, punti)]
