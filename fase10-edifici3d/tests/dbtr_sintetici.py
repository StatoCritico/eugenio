"""DB topografici sintetici per i test di «Aggiungi DBTR» (07/11/2026): stessi strati e colonne delle estrazioni vere
(DBTR ER in GeoPackage e Shapefile, DBGT Lombardia con le z, CTRN FVG), pochi corpi inventati vicino a Rimini, Milano e
Udine che toccano tutte le regole delle altezze (intero, quota del tetto, colmo, H ≤ 0, quota senza altezza, cortile,
corpo troppo piccolo, corpo senza edificio). Nessun dato vero: si possono pubblicare."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from shapely import to_wkb
from shapely.geometry import Polygon, box

X0, Y0 = 780500.0, 4880600.0          # EPSG:7791, centro di Rimini


def _rett(x, y, w, h, buco=None):
    p = box(x, y, x + w, y + h)
    if buco:
        bx, by, bw, bh = buco
        p = Polygon(p.exterior.coords, [box(x + bx, y + by, x + bx + bw, y + by + bh).exterior.coords])
    return p


def righe_er(convenzione: str = "quote"):
    """(uvl, edifici, usi): liste di dict con «geom» (shapely, EPSG:7791) per le UVL e gli edifici."""
    X, Y = X0, Y0
    uvl = [
        dict(ID_E="U1", EDI_ID_E="E1", H_UVL=7.0, B_UVL=5.0, H_COLMO=None, H_GRONDA=None, geom=_rett(X, Y, 20, 10)),
        dict(ID_E="U2", EDI_ID_E="E2", H_UVL=12.0, B_UVL=5.0, H_COLMO=19.5, H_GRONDA=13.1, geom=_rett(X + 40, Y, 30, 30, (10, 10, 10, 10))),
        dict(ID_E="U3", EDI_ID_E="E2", H_UVL=17.35, B_UVL=5.2, H_COLMO=None, H_GRONDA=None, geom=_rett(X + 70, Y, 12, 30)),
        dict(ID_E="U4", EDI_ID_E="E3", H_UVL=0.0, B_UVL=5.0, H_COLMO=None, H_GRONDA=None, geom=_rett(X + 100, Y, 8, 8)),
        dict(ID_E="U5", EDI_ID_E="E3", H_UVL=5.6, B_UVL=5.3, H_COLMO=None, H_GRONDA=None, geom=_rett(X + 120, Y, 8, 8)),
        dict(ID_E="U6", EDI_ID_E="E4", H_UVL=6.0, B_UVL=5.0, H_COLMO=None, H_GRONDA=None, geom=_rett(X + 140, Y, 0.5, 0.5)),
        dict(ID_E="U7", EDI_ID_E=None, H_UVL=9.0, B_UVL=5.1, H_COLMO=None, H_GRONDA=None, geom=_rett(X, Y + 50, 15, 15)),
        dict(ID_E="U8", EDI_ID_E="E5", H_UVL=24.0, B_UVL=4.9, H_COLMO=None, H_GRONDA=None,
             geom=Polygon([(X + 30, Y + 50), (X + 60, Y + 52), (X + 58, Y + 80), (X + 33, Y + 76)])),
    ]
    if convenzione == "altezze":     # come Faenza: decimali sotto la base (base ~33 m) → altezze
        for k in range(6):
            uvl.append(dict(ID_E=f"A{k}", EDI_ID_E="E6", H_UVL=10.5 + k, B_UVL=33.0, H_COLMO=None, H_GRONDA=None,
                            geom=_rett(X + 200 + 20 * k, Y, 12, 12)))
        uvl.append(dict(ID_E="A9", EDI_ID_E="E6", H_UVL=44.5, B_UVL=33.2, H_COLMO=None, H_GRONDA=None,
                        geom=_rett(X + 330, Y, 6, 6)))       # campanile: con la convenzione «altezze» resta 44,5 m
    for r in uvl:
        r.update(TIPO_FONTE="DTM DSM 2008", QUALITA=2, D_TETTO="piano", D_TY_PORZ="edificio", DATA_AGG=20250101)
    edifici = [
        dict(ID_E="E1", FOGLIO=74, NUMERO="1100", NOME="Palazzo di prova", D_TY_EDI="edificio civile",
             D_STAT_E="esistente", COD_COM="H294", geom=_rett(X, Y, 20, 10)),
        dict(ID_E="E2", FOGLIO=0, NUMERO=None, NOME="Non assegnato", D_TY_EDI="edificio civile", D_STAT_E="esistente",
             COD_COM="H294", geom=_rett(X + 40, Y, 42, 30)),
        dict(ID_E="E5", FOGLIO=99, NUMERO="1", NOME="Ospedale di prova", D_TY_EDI="edificio pubblico",
             D_STAT_E="esistente", COD_COM="H294", geom=_rett(X + 30, Y + 50, 30, 30)),
    ]
    usi = [dict(ID_E="E1", CT_USO=101, D_CT_USO="residenziale"), dict(ID_E="E5", CT_USO=302, D_CT_USO="sede di ospedale"),
           dict(ID_E="E2", CT_USO=705, D_CT_USO="commerciale")]
    return uvl, edifici, usi


def _scrivi(path, layer, righe, campi, driver, crs, con_geom=True, tipo="Polygon"):
    import pyogrio.raw as R
    geom = np.array([to_wkb(r["geom"]) for r in righe], dtype=object) if con_geom else None
    dati = []
    for c in campi:
        v = [r.get(c) for r in righe]
        if all(isinstance(x, (int, np.integer)) or x is None for x in v) and any(x is not None for x in v):
            dati.append(np.array([x if x is not None else 0 for x in v], dtype="int64"))
        elif all(isinstance(x, (int, float)) or x is None for x in v) and any(x is not None for x in v):
            dati.append(np.array([np.nan if x is None else float(x) for x in v], dtype="float64"))
        else:
            dati.append(np.array([None if x is None else str(x) for x in v], dtype=object))
    R.write(str(path), geom, dati, campi, layer=layer, driver=driver, crs=crs,
            geometry_type=tipo if con_geom else None, append=Path(path).exists() and driver == "GPKG")


CAMPI_UVL = ["ID_E", "EDI_ID_E", "H_UVL", "B_UVL", "H_COLMO", "H_GRONDA", "TIPO_FONTE", "QUALITA", "D_TETTO", "D_TY_PORZ", "DATA_AGG"]
CAMPI_EDI = ["ID_E", "FOGLIO", "NUMERO", "NOME", "D_TY_EDI", "D_STAT_E", "COD_COM"]
CAMPI_USO = ["ID_E", "CT_USO", "D_CT_USO"]


def gpkg_er(path: Path, convenzione: str = "quote") -> Path:
    uvl, edi, usi = righe_er(convenzione)
    path = Path(path)
    path.unlink(missing_ok=True)
    _scrivi(path, "V_EDI_GPG", edi, CAMPI_EDI, "GPKG", "EPSG:7791")
    _scrivi(path, "V_UVL_GPG", uvl, CAMPI_UVL, "GPKG", "EPSG:7791")
    _scrivi(path, "V_EDI_CT_USO_AVM", usi, CAMPI_USO, "GPKG", "EPSG:7791", con_geom=False)
    return path


def shp_er(cartella: Path, convenzione: str = "quote") -> Path:
    uvl, edi, usi = righe_er(convenzione)
    cartella = Path(cartella)
    cartella.mkdir(parents=True, exist_ok=True)
    _scrivi(cartella / "V_UVL_GPG.shp", "V_UVL_GPG", uvl, CAMPI_UVL, "ESRI Shapefile", "EPSG:7791")
    _scrivi(cartella / "V_EDI_GPG.shp", "V_EDI_GPG", edi, CAMPI_EDI, "ESRI Shapefile", "EPSG:7791")
    _scrivi(cartella / "V_EDI_CT_USO_AVM.dbf", "V_EDI_CT_USO_AVM", usi, CAMPI_USO, "ESRI Shapefile", None, con_geom=False)
    return cartella


def shp_lombardia(cartella: Path) -> Path:
    """DBGT 020101 con le z della base (PolygonZ), EPSG:7791, vicino a Milano."""
    from shapely.geometry import Polygon as P
    x, y = 514700.0, 5034500.0
    def pz(x0, y0, w, h, z):
        return P([(x0, y0, z), (x0 + w, y0, z), (x0 + w, y0 + h, z), (x0, y0 + h, z), (x0, y0, z)])
    righe = [dict(CLASSID="L1", CEDIUV="C1", UN_VOL_AV=15.2, UN_VOL_QE=135.2, UN_VOL_POR="01", geom=pz(x, y, 20, 15, 120.0)),
             dict(CLASSID="L2", CEDIUV="C1", UN_VOL_AV=6.0, UN_VOL_QE=126.0, UN_VOL_POR="03", geom=pz(x + 20, y, 10, 15, 116.5)),
             dict(CLASSID="L3", CEDIUV="C2", UN_VOL_AV=0.0, UN_VOL_QE=120.0, UN_VOL_POR="04", geom=pz(x + 50, y, 10, 10, 120.0))]
    cartella = Path(cartella)
    cartella.mkdir(parents=True, exist_ok=True)
    _scrivi(cartella / "UN_VOL.shp", "UN_VOL", righe, ["CLASSID", "CEDIUV", "UN_VOL_AV", "UN_VOL_QE", "UN_VOL_POR"],
            "ESRI Shapefile", "EPSG:7791", tipo="Polygon Z")
    return cartella


def shp_fvg(cartella: Path) -> Path:
    """CTRN Edificato con ALTEZZA e quote, EPSG:6708 (RDN2008 / UTM 33N), vicino a Udine."""
    x, y = 365000.0, 5104000.0
    righe = [dict(ID=1, ALTEZZA=9.5, QUOTA_PIEDE=110.0, QUOTA_GRONDA=119.5, NOME="EDIFICIO CIVILE", CODICE="0201", geom=_rett(x, y, 15, 12)),
             dict(ID=2, ALTEZZA=None, QUOTA_PIEDE=110.0, QUOTA_GRONDA=118.0, NOME="CAPANNONE INDUSTRIALE", CODICE="0203", geom=_rett(x + 30, y, 40, 20)),
             dict(ID=3, ALTEZZA=0.0, QUOTA_PIEDE=None, QUOTA_GRONDA=None, NOME="BARACCA", CODICE="0209", geom=_rett(x + 80, y, 4, 4))]
    cartella = Path(cartella)
    cartella.mkdir(parents=True, exist_ok=True)
    _scrivi(cartella / "EDIFICATO.shp", "EDIFICATO", righe, ["ID", "ALTEZZA", "QUOTA_PIEDE", "QUOTA_GRONDA", "NOME", "CODICE"],
            "ESRI Shapefile", "EPSG:6708")
    return cartella
