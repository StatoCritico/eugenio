"""Campione LiDAR **sintetico** per prove e dimostrazioni (Fase C): non sono dati reali.

Costruisce, sull'isolato sintetico di `sintetico.py` (vicino a Rimini), un rilievo inventato a tessere di 50 m:
- `dsm/<tessera>.tif` e `dtm/<tessera>.tif` (GeoTIFF float32 a 0,5 m, EPSG:7791) come quelli che la Regione consegna;
- `las/<tessera>.las` (LAS 1.4, classi 2 terreno, 5 vegetazione alta, 6 edifici, 2 punti/m²) per una tessera che non ha
  il DSM raster, così la pipeline prova anche la strada dei LAS.
Tetti di forma nota (per i test): C1 a capanna con il colmo lungo x (falde a sud e a nord, 23,2°), C2, C3, C5, C8 e C10
piani, C4 a una falda verso sud (6°), C6 a capanna con il colmo lungo y (falde a est e a ovest, 31°), C7 a padiglione
(20,6°), C9 a capanna (26,6°); C10 **non c'è** nel rilievo (demolito: la pipeline lo deve dire). Qualche albero, un
camino sulla torre C3 e rumore di 3 cm. Ogni file porta l'etichetta SINTETICO.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from . import sintetico as S

LATO = 50.0                       # m: tessere del campione (la zona vera usa 1.000 m)
PASSO = 0.5
NOME = "C_{x0:.0f}_{y0:.0f}"      # nome delle tessere del campione
# tessere del campione: x locale da −50 a 150, y da −50 a 100 (attorno a X0, Y0 di sintetico.py)
COLONNE = range(-1, 3)
RIGHE = range(-1, 2)
SOLO_LAS = (1, 0)                 # (colonna, riga) della tessera con il solo LAS

# tetti: id → (forma, parametri). Coordinate locali (m) come in sintetico._p; gronda = H_uvl del DBTR sintetico
TETTI = {
    "C1": ("capanna_x", 10.0, 13.0), "C2": ("piano", 10.0), "C3": ("piano", 22.0), "C4": ("monofalda_sud", 8.0, 6.0),
    "C5": ("piano", 7.0), "C6": ("capanna_y", 6.0, 9.0), "C7": ("padiglione", 18.0, 21.0), "C8": ("piano", 13.0),
    "C9": ("capanna_x", 9.0, 11.5),
}
ASSENTI = {"C10"}
ALBERI = [(-5.0, 60.0, 4.0, 9.0), (110.0, -30.0, 5.0, 11.0), (20.0, 70.0, 3.5, 7.0)]   # x, y, raggio, altezza


def _sagome():
    from shapely.geometry import Polygon
    return {p["Id_e"]: g for p, g in S.uvl()}


def altezza_tetto(cid: str, g, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Altezza del tetto sopra il terreno nei punti (x, y) assoluti dentro la sagoma g."""
    forma, *p = TETTI[cid]
    x0, y0, x1, y1 = g.bounds
    if forma == "piano":
        return np.full_like(x, p[0])
    if forma == "capanna_x":            # colmo parallelo a x, a metà della y
        g0, c0 = p; semi = (y1 - y0) / 2
        return g0 + (c0 - g0) * (1 - np.abs(y - (y0 + semi)) / semi)
    if forma == "capanna_y":
        g0, c0 = p; semi = (x1 - x0) / 2
        return g0 + (c0 - g0) * (1 - np.abs(x - (x0 + semi)) / semi)
    if forma == "monofalda_sud":        # bassa a sud, sale verso nord
        g0, inc = p
        return g0 + (y - y0) * math.tan(math.radians(inc))
    if forma == "padiglione":
        g0, c0 = p
        semi_c = min(x1 - x0, y1 - y0) / 2
        d = np.minimum.reduce([x - x0, x1 - x, y - y0, y1 - y])
        return g0 + (c0 - g0) * np.clip(d / semi_c, 0, 1)
    raise ValueError(forma)


def superficie(x: np.ndarray, y: np.ndarray, rng=None, rumore: float = 0.03) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Quote assolute di DSM e DTM nei punti (x, y) e classe del punto (2 terreno, 5 alberi, 6 edifici)."""
    import shapely
    t = S.quota(x, y).astype("float64")
    dsm = t.copy()
    cl = np.full(x.shape, 2, dtype="int16")
    for cid, g in _sagome().items():
        if cid in ASSENTI or cid not in TETTI:
            continue
        dentro = shapely.contains_xy(g, x, y)
        if dentro.any():
            base = np.min(S.quota(np.array([c[0] for c in g.exterior.coords]), np.array([c[1] for c in g.exterior.coords])))
            dsm[dentro] = base + altezza_tetto(cid, g, x[dentro], y[dentro])
            cl[dentro] = 6
    # camino sulla torre C3 (2 m sopra il tetto, 1 m²)
    cam = (np.abs(x - (S.X0 + 23.0)) < 0.5) & (np.abs(y - (S.Y0 + 23.0)) < 0.5)
    dsm[cam] += 2.0
    for ax, ay, r, h in ALBERI:
        d = np.hypot(x - (S.X0 + ax), y - (S.Y0 + ay))
        a = d < r
        dsm[a] = np.maximum(dsm[a], t[a] + h * (1 - (d[a] / r) ** 2))
        cl[a & (cl == 2)] = 5
    if rng is not None and rumore:
        dsm = dsm + rng.normal(0, rumore, dsm.shape)
    return dsm, t, cl


def tessere():
    """(nome, x0, y0, x1, y1) delle tessere del campione in EPSG:7791."""
    out = []
    for j in RIGHE:
        for i in COLONNE:
            x0, y0 = S.X0 + i * LATO, S.Y0 + j * LATO
            out.append((NOME.format(x0=x0, y0=y0), x0, y0, x0 + LATO, y0 + LATO, (i, j)))
    return out


def genera(cartella: Path, seme: int = 11) -> dict:
    """Scrive il campione in `cartella` (dsm/, dtm/, las/, indice.json). Restituisce l'indice."""
    import rasterio
    from rasterio.transform import from_origin
    cartella = Path(cartella)
    rng = np.random.default_rng(seme)
    indice = {"sintetico": True, "avviso": "Rilievo LiDAR sintetico di esempio: non rappresenta edifici reali.",
              "crs": S.CRS, "lato": LATO, "passo": PASSO, "tessere": []}
    for nome, x0, y0, x1, y1, ij in tessere():
        n = int(LATO / PASSO)
        xs = x0 + PASSO * (np.arange(n) + 0.5); ys = y1 - PASSO * (np.arange(n) + 0.5)
        gx, gy = np.meshgrid(xs, ys)
        dsm, dtm, _ = superficie(gx.ravel(), gy.ravel(), rng)
        voce = {"nome": nome, "riquadro": [x0, y0, x1, y1]}
        if ij != SOLO_LAS:
            for cosa, z in (("dsm", dsm), ("dtm", dtm)):
                p = cartella / cosa / f"{nome}.tif"
                p.parent.mkdir(parents=True, exist_ok=True)
                with rasterio.open(p, "w", driver="GTiff", width=n, height=n, count=1, dtype="float32", crs=S.CRS,
                                   transform=from_origin(x0, y1, PASSO, PASSO), nodata=-9999.0) as f:
                    f.write(z.reshape(n, n).astype("float32"), 1)
                    f.update_tags(SINTETICO="1", AVVISO=indice["avviso"])
            voce["dsm"] = True
        else:
            _las(cartella / "las" / f"{nome}.las", x0, y0, rng)
            voce["las"] = True
        indice["tessere"].append(voce)
    (cartella / "indice.json").write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8")
    return indice


def _las(dest: Path, x0: float, y0: float, rng, densita: float = 2.0):
    import laspy
    n = int(LATO * LATO * densita)
    x = x0 + rng.uniform(0, LATO, n); y = y0 + rng.uniform(0, LATO, n)
    dsm, dtm, cl = superficie(x, y, rng)
    # sotto gli alberi una parte dei punti arriva al terreno (secondo ritorno)
    alberi = np.where(cl == 5)[0]
    terra = rng.choice(alberi, size=len(alberi) // 3, replace=False) if len(alberi) else np.array([], dtype=int)
    ritorno = np.ones(n, dtype=np.uint8)
    z = dsm.copy()
    z[terra] = dtm[terra]; cl[terra] = 2; ritorno[terra] = 2
    h = laspy.LasHeader(point_format=6, version="1.4")
    h.offsets = [x0, y0, 0.0]; h.scales = [0.01, 0.01, 0.01]
    las = laspy.LasData(h)
    las.x, las.y, las.z = x, y, z
    las.classification = cl.astype(np.uint8)
    las.return_number = ritorno
    las.number_of_returns = np.where(np.isin(np.arange(n), terra), 2, 1).astype(np.uint8)
    dest.parent.mkdir(parents=True, exist_ok=True)
    las.write(str(dest))
