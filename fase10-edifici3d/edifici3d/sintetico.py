"""Quartiere e DTM **sintetici** per prove e dimostrazioni: non sono dati reali.

Un isolato di prova vicino a Rimini (solo la posizione è reale, per avere sole e latitudine plausibili): un edificio
«E-DEMO» a tre corpi (L con una torre), un capannone a due corpi, una casa con tetto a capanna e qualche edificio
attorno, più un DTM a pendenza leggera. Proprietà e attributi imitano quelli delle UVL (H_uvl, B_uvl, Id_e, Edi_id_e)
con Tipo_fonte = «SINTETICO». Ogni file prodotto porta `"sintetico": true` e l'avviso «Dati sintetici di esempio».
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon, box, mapping
from shapely import affinity

from .modello import Corpo

AVVISO = ("Dati sintetici di esempio: sagome, altezze e terreno sono inventati per mostrare come funziona la pagina; "
          "non rappresentano edifici reali.")
CRS = "EPSG:7791"
# punto di partenza in EPSG:7791 (RDN2008 / UTM 32N), zona di Rimini
X0, Y0 = 788_000.0, 4_884_000.0
QUOTA0 = 8.0


def _p(x, y, w, h, rot=0.0):
    g = box(X0 + x, Y0 + y, X0 + x + w, Y0 + y + h)
    return affinity.rotate(g, rot, origin=(X0, Y0)) if rot else g


def uvl() -> list[tuple[dict, Polygon]]:
    """UVL sintetiche (proprietà come il DBTR, geometria in EPSG:7791)."""
    righe = [
        # edificio dimostrativo: corpo basso a L (due UVL) e torre
        ("C1", "E-DEMO", _p(0, 0, 40, 14), 10.0), ("C2", "E-DEMO", _p(0, 14, 14, 26), 10.0),
        ("C3", "E-DEMO", _p(14, 14, 12, 12), 22.0),
        # capannone e uffici attaccati
        ("C4", "E-CAP", _p(60, -10, 36, 24), 8.0), ("C5", "E-CAP", _p(60, 14, 12, 10), 7.0),
        # casa a capanna
        ("C6", "E-CASA", _p(-30, 30, 10, 12), 6.0),
        # vicini: un condominio a sud-est, uno a ovest attaccato al corpo C1
        ("C7", "E-VIC1", _p(30, -45, 20, 16), 18.0), ("C8", "E-VIC2", _p(-16, -2, 16, 16), 13.0),
        ("C9", "E-VIC3", _p(-40, 60, 18, 10), 9.0), ("C10", "E-VIC4", _p(70, 50, 14, 14), 15.0),
    ]
    out = []
    for cid, eid, g, h in righe:
        cx, cy = g.centroid.x, g.centroid.y
        # H_COLMO del DBTR è una quota assoluta (07/11/2026): colmo a 9 m sopra la base
        colmo = f"{quota(cx, cy) + 9:.2f}".replace(".", ",") if cid == "C6" else "Null"
        out.append(({"Id_e": cid, "Edi_id_e": eid, "H_uvl": f"{h:g}".replace(".", ","),
                     "B_uvl": f"{quota(cx, cy):.2f}".replace(".", ","), "H_GRONDA": "Null", "H_COLMO": colmo,
                     "Tipo_fonte": "SINTETICO", "Qualita": "20", "D_tetto": "Non assegnato", "D_ty_porz": "generica",
                     "Data_da": "Null", "Data_a": "Null"}, g))
    return out


def quota(x: float, y: float) -> float:
    """Terreno sintetico: piano inclinato di 1 m ogni 100 m verso nord-ovest più una leggera ondulazione."""
    return QUOTA0 + 0.01 * (-(x - X0) + (y - Y0)) / 1.4142 + 0.4 * np.sin((x - X0) / 60.0)


def dtm(dest: Path, lato: float = 800.0, passo: float = 5.0) -> Path:
    """GeoTIFF sintetico 5 m in EPSG:7791 centrato sull'isolato."""
    import rasterio
    from rasterio.transform import from_origin
    n = int(lato / passo)
    xs = X0 - lato / 2 + passo * (np.arange(n) + 0.5)
    ys = Y0 + lato / 2 - passo * (np.arange(n) + 0.5)
    gx, gy = np.meshgrid(xs, ys)
    z = quota(gx, gy).astype("float32")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(dest, "w", driver="GTiff", width=n, height=n, count=1, dtype="float32", crs=CRS,
                       transform=from_origin(X0 - lato / 2, Y0 + lato / 2, passo, passo), nodata=np.nan) as f:
        f.write(z, 1)
        f.update_tags(SINTETICO="1", AVVISO=AVVISO)
    return dest


def consumi_mensili() -> list[dict]:
    """Consumi mensili di gas sintetici per l'edificio dimostrativo (Smc), costruiti da una firma inventata:
    300 Smc al mese di base + 9 Smc per grado giorno, con gradi giorno mensili tipici della costa romagnola."""
    gg = [430, 330, 260, 110, 0, 0, 0, 0, 0, 90, 260, 400]
    mesi = ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06", "2025-07", "2025-08", "2025-09",
            "2025-10", "2025-11", "2025-12"]
    rng = np.random.default_rng(7)
    return [{"mese": m, "gas_smc": round((300 + 9 * g) * (1 + rng.normal(0, 0.04)), 0), "gg_esempio": g}
            for m, g in zip(mesi, gg)]
