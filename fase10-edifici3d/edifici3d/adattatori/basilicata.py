"""Basilicata – DBGT 1:5.000 della Regione Basilicata, classe 020101 «Unità volumetrica», gruppo A, 08/11/2026.

Tre forme dello stesso dato (URL in `fonti/basilicata.toml`), verificate dal vivo l'08/11/2026, tutte in EPSG:25833 e
con licenza **IODL 2.0** (schede RNDT e PDF nello zip comunale):

- **WFS** `dbgt_0201:un_vol` (GeoJSON): campi minuscoli `un_vol_por`, `un_vol_av`, `cediuv`, `scril`; geometria
  PolygonZ con la **z costante = quota della base**; nessun identificativo tra le proprietà: si usa l'`id` della feature
  GeoJSON («un_vol.<n>»), che GDAL legge come campo `id`. Manca `un_vol_qe`: quota di gronda = z + `un_vol_av`;
- **zip regionale** `unita_volumetrica.zip` (Shapefile PolygonZ): `altezza_vo`, `porzione`;
- **zip comunale** `<17 + ISTAT>.zip`, file `unita_volumetrica_<codice>.shp` (Shapefile **2D**): `ALTEZZA_VO`,
  `PORZIONE`, `TIPO_PORZ`, `CEDIUV`: senza z la quota del terreno viene solo dal DTM (`--dtm`, WCS `rsdi_wcs__dtm_5m`).

Porzione «08» (sotterranea) scartata; 01 al suolo (99 %), 03/04 portici e sottopassaggi tenuti. Con il DTM la quota del
terreno è il minimo del DTM 5 m nella sagoma; la z della base (quota più bassa del piede) resta in `extra.quota_base_db`.
"""
from __future__ import annotations

from .a_dbgt import Nomi, adattatore

BASILICATA = adattatore(
    "basilicata_dbgt", fonte="DBGT Basilicata – Unità volumetrica (020101)", licenza="IODL 2.0",
    attribuzione="Regione Basilicata – RSDI, DBGT 1:5.000, Unità volumetrica (IODL 2.0)",
    crs_file="EPSG:25833", campi_attesi=("un_vol_av", "un_vol_por", "cediuv"),
    nomi=Nomi(id=("id", "CLASSID", "gml_id", "fid", "ogr_fid", "OBJECTID"), edificio=("cediuv",),
              altezza=("un_vol_av", "altezza_vo", "altezza_vol", "altezza"), estrusione=("un_vol_qe",),
              porzione=("un_vol_por", "porzione"), altri=("scril", "tipo_porz")),
    regione="Basilicata", nome_breve="DBGT Basilicata", etichetta_altezza="un_vol_av",
    qualita="DBGT 1:5.000 (volo 2013), altezza ±1–2 m; terreno dal DTM 5 m LiDAR 2013 o dalla z della base")

ADATTATORI = (BASILICATA,)
