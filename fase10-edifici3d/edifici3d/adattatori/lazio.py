"""Lazio – DBGT 2014 della Regione Lazio, classe 020101 «Unità volumetrica» (`UN_VOL`), gruppo A, 08/11/2026.

Fonte: «2014 Carta Tecnica Regionale Numerica scala 1:5.000 – Provincia di Roma», risorsa «DBGT 5K formato SHP», un
zip per foglio 1:50.000 (`DBT_Lazio_RM374.zip` = foglio 374 «Roma»), licenza cc-by4 su dati.lazio.it (URL nel TOML
`fonti/lazio.toml`). Verificato dal vivo l'08/11/2026 su `UN_VOL.*` del foglio 374 (letti con richieste Range dal File
Browser pubblico della Regione, in modalità anonima come nel browser):

- Shapefile **PolygonZ**, `.prj` «ETRS_1989_UTM_Zone_33N» (EPSG:25833; la Regione dichiara RDN2008/UTM 33N, EPSG:7792:
  differenza di centimetri); 280.897 volumi;
- campi `CLASSID, COD_ISTAT, DATA_AGG, FONTE, LIVELLO, UN_VOL_AV, UN_VOL_POR, UN_VOL_QE, CEDIUV, SCALA` (gli stessi del
  DBGT lombardo più `COD_ISTAT` e `DATA_AGG`); `UN_VOL_QE − z = UN_VOL_AV` in tutti i volumi provati (z costante per
  poligono = quota della base); `UN_VOL_AV` da 3,0 a 111,3 m, mediana 7,95 m;
- `UN_VOL_POR`: 01 (277.727), 08 (2.950: sotterranei, scartati), 04 (213), 03 (7); `DATA_AGG` 2003 (223.903) o 2014
  (56.994): va in `extra.anno_dato`.

Nessun DTM recente in formato comodo (solo DXF di punti 2002-03): la quota del terreno è `UN_VOL_QE − UN_VOL_AV`.
"""
from __future__ import annotations

from .a_dbgt import Nomi, adattatore

LAZIO = adattatore(
    "lazio_dbgt", fonte="DBGT Lazio 2014 – Unità volumetrica (020101)", licenza="CC BY 4.0",
    attribuzione="Regione Lazio – DBGT 2014, Carta Tecnica Regionale Numerica 1:5.000, Unità volumetrica (CC BY 4.0)",
    crs_file="EPSG:25833", campi_attesi=("CLASSID", "CEDIUV", "UN_VOL_AV", "UN_VOL_QE", "UN_VOL_POR", "COD_ISTAT", "DATA_AGG"),
    nomi=Nomi(anno=("DATA_AGG",), comune=("COD_ISTAT",)), regione="Lazio", nome_breve="DBGT Lazio",
    etichetta_altezza="UN_VOL_AV", qualita="DBGT 1:5.000 (volo 2002-03, aggiornato al 2014), altezza ±1–2 m")

ADATTATORI = (LAZIO,)
