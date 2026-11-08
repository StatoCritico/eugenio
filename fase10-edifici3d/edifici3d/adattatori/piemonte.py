"""Piemonte – BDTRE della Regione Piemonte, classe 020101 «Unità volumetrica» (`un_vol`), gruppo A, 08/11/2026.

Fonte: WFS regionale `bdtre_imm` (typeName `un_vol`; URL in `fonti/piemonte.toml`), che **non risponde dal container**
di sviluppo ma risponde dal PC di Paolo: l'08/11/2026 tutto lo strato su Torino e dintorni (riquadro EPSG:32632
387000–404000 E, 4980000–4999000 N, 139.244 volumi, deduplicati per `uuid`) è stato scaricato da lì in GeoJSON e
letto qui. Campi veri:

- `uuid` (identificativo), `data_acq`, `data_agg`, `data_fin`, `ente_for`, `ente_prod`, `modo_prod`, `sc_acq`;
- `un_vol_av` **testo** con l'altezza in metri interi («6»), vuoto in 33.899 volumi (scartati); mediana 5 m, massimo
  166 m (grattacielo Intesa Sanpaolo);
- `un_vol_por` **testo del dominio** («al suolo» in tutti i volumi di Torino; «sotterranea»/«interrata» si scartano);
- `un_vol_qe` sempre vuoto; `un_vol_ex` «altezza» o vuoto; geometria **2D** (Polygon), EPSG:32632;
- `modo_prod`: 105.202 volumi «banche dati esterne – geometrie da catasto, altezza volumi da ARPA PIEMONTE
  (DSM-DTM, LAS)» con data 2017: l'altezza è un DSM − DTM dell'Arpa sulla sagoma catastale (in `extra`).

Nessun identificativo d'edificio (`cediuv` assente): ogni volume è un edificio. Nessuna quota: senza `--dtm` la quota
del terreno resta vuota e la pagina 3D usa l'altitudine del comune («quota non nota»). Il DTM 5 m ICE 2009-2011
(CC BY 4.0, WCS `wcs_ice_2009_2011_dtm`) non è raggiungibile dal container: da provare dal server.
Licenza: **CC BY 2.5** dal comunicato della Regione (novembre 2017: «Tutti i dati e i servizi della BDTRE pubblicati
sono resi disponibili con licenza Creative Commons – BY 2.5»); la scheda RNDT di UN_VOL dice «Condizioni sconosciute»:
da confermare con la lettera alla Regione.
"""
from __future__ import annotations

from .a_dbgt import Nomi, adattatore

PIEMONTE = adattatore(
    "piemonte_bdtre", fonte="BDTRE Piemonte – Unità volumetrica (020101)", licenza="CC BY 2.5",
    attribuzione="Regione Piemonte – BDTRE, Unità volumetriche (altezze ARPA Piemonte), CC BY 2.5",
    crs_file="EPSG:32632", campi_attesi=("uuid", "un_vol_av", "un_vol_por", "modo_prod", "data_agg"),
    nomi=Nomi(id=("uuid", "UN_VOL_UUID", "CLASSID", "id", "ogr_fid"), edificio=("cediuv", "edifc_uuid"),
              altezza=("un_vol_av", "ELEV", "altezza"), estrusione=("un_vol_qe",), porzione=("un_vol_por",),
              anno=("data_agg",), altri=("modo_prod", "ente_prod", "sc_acq")),
    regione="Piemonte", nome_breve="BDTRE Piemonte", etichetta_altezza="un_vol_av",
    qualita="BDTRE 1:10.000 (in città sagome catastali), altezza intera da DSM − DTM Arpa 2017, ±1–2 m")

ADATTATORI = (PIEMONTE,)
