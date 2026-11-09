"""Riga di comando della fase 10 (Fase A).

  python -m edifici3d scarica --fonte dbtr_uvl --archivio /srv/energia/dati/edifici
  python -m edifici3d controlla-uvl --gpkg UVL.gpkg [--riquadro x0 y0 x1 y1]     # rapporto sugli attributi
  python -m edifici3d controlla-uvl --wms-punto 44.06 12.566                        # pochi corpi dal WMS pubblico
  python -m edifici3d prepara --gpkg rimini/estraz_procons.gpkg [cesena/estraz_procons.gpkg faenza/ …] --dtm DTM5x5_ed2025_SE_7791.zip \
         --archivio … [--riquadro …] [--archivi-json]        # GeoPackage o cartella Shapefile; più comuni insieme
  python -m edifici3d dtm-ritaglia --file DTM5x5_ed2025_SE_7791.zip --riquadro x0 y0 x1 y1 --uscita dtm5_rimini.tif
  python -m edifici3d dtm-server --file DTM5x5_ed2025_SE_7791.zip --uscita /dati/terreno/dtm5_er_se.tif   # COG per /api/terreno
  python -m edifici3d dtm-server --regione veneto --crs EPSG:6876 --file tavole_veneto/ --uscita /dati/terreno/dtm5_veneto_tv.tif
  python -m edifici3d archivi-json --archivio /srv/energia/dati/edifici      # solo DBTR e archivi veri (--con-prova: anche le prove OSM)
  python -m edifici3d dividi --gpkg 354184/estraz_procons.gpkg --elenco      # estrazione raggruppata: COD_COM → comune ISTAT
  python -m edifici3d dividi --gpkg 354184/estraz_procons.gpkg --codici D899 --istat 040015 --uscita divisi/gambettola
  python -m edifici3d demo --uscita ../fase5-sito/sito/dati/edifici3d               # dati sintetici per la pagina 3D
  python -m edifici3d ortofoto-sito --sito ospedale-rimini --anno 2023 --archivio … t1.tif t2.tif   # AGEA a mano (Fase B)

Fase C (LiDAR e pipeline notturna; zone in zone/*.toml):
  python -m edifici3d lidar --zona rimini --archivio /srv/energia/dati/edifici --stato /srv/energia/dati/edifici_stato
  python -m edifici3d lidar --zona auto …            # la prima zona della coda con tessere da fare (cron delle 3:30)
  python -m edifici3d lidar … --subito --max-minuti 20 --tessere 32_78504884   # prova fuori finestra su una tessera
  python -m edifici3d lidar … --aggiorna             # aggiornamento annuale: solo le tessere con fonte cambiata
  python -m edifici3d lidar-stato --stato …          # riepilogo delle zone (lo stesso della pagina di stato)
  python -m edifici3d lidar-celle --archivio …       # elenco delle celle di falde e alberi in lidar/indice.json (09/11 b)
  python -m edifici3d lidar-fonti --zona rimini [--prova]   # fonti, stato e motivo; --prova controlla dal vivo
  python -m edifici3d campione --uscita /tmp/campione       # campione LiDAR sintetico (prove)
  python -m edifici3d importa-modello edificio.ifc --uscita modello.geojson [--posa …]   # DXF/IFC dell'utente
  python -m edifici3d dtm-wcs --riquadro 770000 4860000 800000 4890000 --uscita dtm5_rimini.tif   # DTM 5 m dal WCS
  python -m edifici3d osm-campione --riquadro 12.5600 44.0555 12.5735 44.0640 --nome rimini-prova --archivio …   # prova ODbL
  python -m edifici3d lidar-copertura --zona rimini --fonte rer_dsm_costa_2019   # maschera della copertura (05/11/2026)
  python -m edifici3d lidar-indice --zona trento --fonte pat_dsm_2009            # indice dei file di una fonte a più file
  python -m edifici3d lidar-corpi --zona bolzano --archivio … --riquadro x0 y0 x1 y1   # corpi dal solo LiDAR (§ 7)

Coda «Aggiungi DBTR» (07/11/2026; servizio edifici-coda, una richiesta alla volta, installazione dopo l'approvazione):
  python -m edifici3d coda --cartella /dati/edifici_coda --archivio /dati/edifici [--ciclo]
  python -m edifici3d coda-ripristina --archivio /dati/edifici --zona er --comune rimini   # torna all'archivio precedente

Fase E (altezze di Zornade, solo nell'archivio ODbL; estratto consegnato da Zornade, mai l'API):
  python -m edifici3d zornade-altezze --file estratto.gpkg --archivio … [--confronta-con …/cc-by/er/prodotti/contesto]
  python -m edifici3d zornade-campione --uscita /tmp/zornade_campione.geojson   # estratto sintetico per le prove
  python -m edifici3d regioni [--prova] [--markdown]     # fonti per regione (fonti/regioni.toml)
  python -m edifici3d --zona lombardia regionale-campione --riquadro x0 y0 x1 y1 --max 500 --uscita c.geojson
  python -m edifici3d --zona lombardia controlla-regione --file c.geojson        # attributi e coerenza delle quote
  python -m edifici3d --zona liguria prepara-regione --file c.geojson --dtm dtm.tif --archivio …   # corpi → prodotti
  python -m edifici3d confronta-dsm --archivio-comune …/cc-by/lig/genova/prodotti --dsm DSM3931.asc --dtm DTM3931.asc --crs-raster EPSG:7791
  python -m edifici3d --zona trento confronta-dsm --file edifici.shp --campo MED_ALT --dsm *_DSMFirst.asc --dtm *_DTM.asc --crs-raster EPSG:25832

`prepara` scrive, nell'archivio della licenza CC BY: corpi.pmtiles, contesto/<cella>.json e indice.json; il DTM dà solo la
quota di ogni corpo (dal 07/11/2026 il terreno 3D viene dalla rotta /api/terreno del server; dtm_cog.tif e terreno.pmtiles
solo con --terreno-archivio); `prepara-osm` fa lo stesso per l'archivio ODbL. Caddy li serve da /edifici3d/ (vedi
fase4-server/Caddyfile).
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

from . import dtm as D, fonti as F, ortofoto_sito as O, plausibilita as PLA, sintetico as S, tessere as T, uvl as U

log = logging.getLogger("edifici3d")


def _corpi_uvl(righe, dtm_file: Path | None, edifici: dict | None = None):
    corpi = []
    edifici = edifici or {}
    righe = list(righe)
    conv = U.convenzione(prop for prop, _ in righe)
    log.info("Convenzione di H_UVL: %s", conv)
    for prop, g in righe:
        if g is None:
            continue
        q = D.quota(dtm_file, g) if dtm_file else None
        e = edifici.get(str(prop.get("EDI_ID_E") or prop.get("Edi_id_e") or ""))
        c = U.corpo_da(prop, g, q["minimo"] if q else None, edificio=e, conv=conv)
        if c:
            if q:
                c.extra["quota_mediana"] = round(q["mediana"], 2)
            corpi.append(c)
    # altezze non plausibili → stima (decisione del 07/11/2026, plausibilita.py; stessa regola nel lettore del sito)
    cambi = PLA.applica(corpi)
    if cambi:
        log.info("Altezze DBTR non plausibili portate alla stima: %d corpi", len(cambi))
    return corpi


def prepara(righe, dtm_file: Path | None, uscita: Path, licenza: str, attribuzione: str, sintetico: bool = False,
            edifici: dict | None = None, extra: dict | None = None, terreno: bool | None = None) -> dict:
    """UVL → prodotti. `dtm_file` può essere anche un quadrante del DTM (zip o TIFF grande): si ritaglia sul riquadro
    dei corpi (dtm_locale.per_corpi) e il ritaglio si cancella alla fine."""
    from . import dtm_locale as DL
    uscita.mkdir(parents=True, exist_ok=True)
    ritaglio = None
    file_dtm = [Path(x) for x in dtm_file] if isinstance(dtm_file, (list, tuple)) else ([Path(dtm_file)] if dtm_file else [])
    if file_dtm and (len(file_dtm) > 1 or DL.grande(file_dtm[0])):
        geoms = [g for _, g in righe if g is not None]
        if not geoms:
            raise ValueError("nessun corpo da preparare")
        b = [g.bounds for g in geoms]
        ritaglio = DL.per_corpi(file_dtm, (min(x[0] for x in b), min(x[1] for x in b), max(x[2] for x in b), max(x[3] for x in b)), uscita)
        dtm_file = ritaglio
    elif file_dtm:
        dtm_file = file_dtm[0]
    try:
        corpi = _corpi_uvl(righe, dtm_file, edifici)
        return prepara_corpi(corpi, dtm_file, uscita, licenza, attribuzione, sintetico, S.CRS, extra=extra, terreno=terreno)
    finally:
        if ritaglio and Path(ritaglio).exists():
            Path(ritaglio).unlink()


# terreno della pagina 3D (07/11/2026): dalla rotta del server, non dall'archivio del comune
TERRENO_ARCHIVIO = False
TERRENO_SERVER = "/api/terreno/{z}/{x}/{y}.png"


def prepara_corpi(corpi, dtm_file: Path | None, uscita: Path, licenza: str, attribuzione: str, sintetico: bool = False,
                  crs: str = "EPSG:7791", extra: dict | None = None, terreno: bool | None = None) -> dict:
    """Corpi già costruiti (UVL, adattatori regionali, …) nel sistema `crs` → PMTiles, celle di contesto e indice.

    Terreno (decisione del 07/11/2026): il DTM serve per la **quota di ogni corpo** (già scritta nei corpi da chi li
    costruisce); `terreno.pmtiles` e `dtm_cog.tif` **non vanno più negli archivi dei comuni**: la pagina 3D prende il
    terreno dalla rotta del server `/api/terreno/{z}/{x}/{y}.png` (fase4-server/servizio/terreno.py). Con `terreno=True`
    (opzione `--terreno-archivio`) si scrivono ancora, per le prove sul PC senza server; predefinito: TERRENO_ARCHIVIO."""
    if terreno is None:
        terreno = TERRENO_ARCHIVIO or sintetico           # la demo sintetica tiene il suo DTM sintetico
    if not corpi:
        raise ValueError("nessun corpo da preparare")
    feat = T.feature_da_corpi(corpi, crs)
    if sintetico:
        for f in feat:
            f["properties"]["sintetico"] = True
    n_t = T.corpi_pmtiles(feat, uscita / "corpi.pmtiles", licenza, attribuzione)
    n_c = T.celle_contesto(feat, uscita / "contesto", licenza, attribuzione)
    import math
    xs = [x for f in feat for x, _ in f["geometry"]["coordinates"][0]]
    ys = [y for f in feat for _, y in f["geometry"]["coordinates"][0]]
    esito = {"corpi": len(corpi), "tessere_corpi": n_t, "celle": n_c, "licenza": licenza, "attribuzione": attribuzione,
             "centro": [round((min(xs) + max(xs)) / 2, 6), round((min(ys) + max(ys)) / 2, 6)],
             "riquadro": [round(min(xs), 6), round(min(ys), 6), round(max(xs), 6), round(max(ys), 6)],
             "cella": T.CELLA, "nomi_celle": sorted(p.stem for p in (uscita / "contesto").glob("*.json"))[:5000]}
    if dtm_file and terreno:
        D.a_cog(dtm_file, uscita / "dtm_cog.tif")
        esito["tessere_terreno"] = D.terrarium_pmtiles(dtm_file, uscita / "terreno.pmtiles", attribuzione=attribuzione)
    else:
        for f in ("dtm_cog.tif", "terreno.pmtiles"):        # un archivio rifatto non tiene i file vecchi
            (uscita / f).unlink(missing_ok=True)
        esito["terreno"] = TERRENO_SERVER
    if dtm_file:
        esito["quote_da_dtm"] = True
    stimate = [c for c in corpi if (c.extra or {}).get("h_dbtr_scartata") is not None]
    if stimate:
        esito["altezze_stimate"] = len(stimate)
        esito["altezze_stimate_elenco"] = [{"id": c.id, "foglio": c.extra.get("foglio"), "numero": c.extra.get("numero"),
                                            "h_dbtr": c.extra["h_dbtr_scartata"], "stima": c.gronda} for c in stimate[:200]]
    if sintetico:
        esito["sintetico"] = True
        esito["avviso"] = S.AVVISO
    esito["crs"] = crs
    if extra:
        esito.update(extra)
    (uscita / "indice.json").write_text(json.dumps(esito, ensure_ascii=False, indent=1), encoding="utf-8")
    return esito


# licenze aperte degli archivi dei DB topografici (08/11/2026): testo di LICENZE.txt e licenze ammesse da controlla-archivio.
# Cartelle: cc-by/ per CC BY 4.0, CC BY 2.5 e CC0 1.0; iodl/ per IODL 2.0; odbl/ per ODbL (mappa [archivi] dei TOML).
TESTI_LICENZA = {
    "CC BY 4.0": "Creative Commons Attribuzione 4.0 (https://creativecommons.org/licenses/by/4.0/deed.it)",
    "CC BY 2.5": "Creative Commons Attribuzione 2.5 Italia (https://creativecommons.org/licenses/by/2.5/it/)",
    "IODL 2.0": "Italian Open Data License 2.0 (https://www.dati.gov.it/content/italian-open-data-license-v20)",
    "CC0 1.0": ("Creative Commons CC0 1.0 Universale (https://creativecommons.org/publicdomain/zero/1.0/deed.it): "
                "nessun obbligo, attribuzione di cortesia"),
}


def controlla_archivio(prodotti: Path, punti=()) -> dict:
    """Controlli di qualità di un archivio preparato (per gli agenti che preparano i comuni, 07/11/2026): file presenti,
    licenza e attribuzione, corpi nelle celle = corpi dell'indice, altezze (quantili, fuori scala), cortili, campi
    dell'edificio (foglio, numero, destinazione), edifici dei punti dati. «problemi» vuoto = archivio pronto."""
    from shapely.geometry import Point, shape
    prodotti = Path(prodotti)
    problemi, avvisi = [], []
    for f in ("indice.json", "corpi.pmtiles"):
        if not (prodotti / f).is_file():
            problemi.append(f"manca {f}")
    if not (prodotti / "indice.json").is_file():
        return {"problemi": problemi, "avvisi": avvisi}
    ind = json.loads((prodotti / "indice.json").read_text(encoding="utf-8"))
    lic = ind.get("licenza") or ""
    if lic not in TESTI_LICENZA or lic not in ind.get("attribuzione", ""):
        problemi.append(f"licenza/attribuzione inattese: {ind.get('licenza')} / {ind.get('attribuzione')}")
    if ind.get("sintetico"):
        problemi.append("archivio sintetico")
    corpi = {}
    for c in sorted((prodotti / "contesto").glob("*.json")):
        for f in json.loads(c.read_text(encoding="utf-8"))["features"]:
            corpi.setdefault(f["properties"]["id"], f)
    n = len(corpi)
    if n != ind.get("corpi"):
        problemi.append(f"corpi nelle celle {n} ≠ indice {ind.get('corpi')}")
    g = sorted(float(f["properties"].get("gronda", 0)) for f in corpi.values())
    q = (lambda p: round(g[min(len(g) - 1, int(len(g) * p))], 1)) if g else (lambda p: None)
    alti = sum(1 for x in g if x > 60)
    bassi = sum(1 for x in g if x < 2)
    # comuni interi: 4–15 m; estrazioni parziali (centri storici, grattacieli: Genova 21,4 m confermata dal DSM): 4–25 m
    if g and not (4 <= q(0.5) <= (25 if ind.get("parziale") else 15)):
        problemi.append(f"mediana della gronda fuori scala: {q(0.5)} m")
    if alti > max(5, n * 0.001):
        avvisi.append(f"{alti} corpi oltre 60 m: controllare (quote assolute non riconosciute?)")
    edifici = {f["properties"].get("edificio") for f in corpi.values()}
    con = lambda k: sum(1 for f in corpi.values() if f["properties"].get(k))
    esito_punti = []
    for lon, lat, nome in punti:
        p = Point(lon, lat)
        dentro = [f for f in corpi.values() if shape(f["geometry"]).contains(p)]
        if not dentro:
            vicini = sorted(((shape(f["geometry"]).distance(p) * 80000, f) for f in corpi.values()
                             if shape(f["geometry"]).distance(p) < 0.0004), key=lambda x: x[0])
            if vicini:
                dentro = [vicini[0][1]]
        if not dentro:
            problemi.append(f"punto «{nome}»: nessun edificio entro 30 m")
            continue
        e = dentro[0]["properties"]["edificio"]
        cc = [f for f in corpi.values() if f["properties"].get("edificio") == e]
        esito_punti.append({"punto": nome, "edificio": e, "nome": dentro[0]["properties"].get("nome"),
                            "foglio": dentro[0]["properties"].get("foglio"), "numero": dentro[0]["properties"].get("numero"),
                            "destinazione": dentro[0]["properties"].get("destinazione"), "corpi": len(cc),
                            "gronde": sorted(f["properties"]["gronda"] for f in cc),
                            "cortili": sum(len(f["geometry"]["coordinates"]) - 1 for f in cc)})
    return {"nome": ind.get("nome"), "corpi": n, "edifici": len(edifici), "riquadro": ind.get("riquadro"),
            "gronda_m": {"p05": q(0.05), "mediana": q(0.5), "p95": q(0.95), "max": g[-1] if g else None,
                         "sotto_2m": bassi, "oltre_60m": alti},
            "a_capanna": con("colmo"), "con_cortile": sum(1 for f in corpi.values() if len(f["geometry"]["coordinates"]) > 1),
            "con_foglio_numero": sum(1 for f in corpi.values() if f["properties"].get("foglio") and f["properties"].get("numero")),
            "con_destinazione": con("destinazione"), "fonti_altezza": dict(sorted(
                {k: sum(1 for f in corpi.values() if f["properties"].get("altezza_dbtr") == k) for k in ("relativa", "assoluta")}.items())),
            "punti": esito_punti, "secondi_preparazione": ind.get("secondi"), "fonte_edifici": ind.get("fonte_edifici"),
            "mb": round(sum(p.stat().st_size for p in prodotti.rglob("*") if p.is_file()) / 1e6, 1),
            "altezze_stimate": sum(1 for f in corpi.values() if f["properties"].get("h_dbtr_scartata") is not None),
            "terreno": "archivio (terreno.pmtiles)" if (prodotti / "terreno.pmtiles").is_file() else "rotta del server",
            "problemi": problemi, "avvisi": avvisi}


# archivi.json: modulo leggero (07/11/2026), usato anche dall'installazione degli archivi approvati dalla coda
from .archivi import scrivi_archivi_json  # noqa: E402,F401


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(prog="edifici3d", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--zona", default="emilia_romagna")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scarica"); s.add_argument("--fonte", required=True); s.add_argument("--archivio", type=Path, required=True)
    s.add_argument("--quadrante", nargs="+", help="solo questi quadranti della fonte (es. SE per il DTM 5 m della Romagna)")
    c = sub.add_parser("controlla-uvl")
    c.add_argument("--gpkg", type=Path, help="GeoPackage dell'estrazione o cartella degli Shapefile"); c.add_argument("--geojson", type=Path)
    c.add_argument("--wms-punto", nargs=2, type=float, metavar=("LAT", "LON"))
    c.add_argument("--riquadro", nargs=4, type=float); c.add_argument("--strato")
    c.add_argument("--json", action="store_true", help="stampa anche il controllo in JSON")
    r = sub.add_parser("prepara", help="GeoPackage DBTR (V_UVL_GPG + V_EDI_GPG) → archivio CC BY cc-by/er/prodotti/")
    r.add_argument("--gpkg", type=Path, required=True, nargs="+",
                   help="uno o più comuni: GeoPackage dell'estrazione o cartella degli Shapefile (V_UVL_GPG.shp…); "
                        "tutti insieme nell'unico archivio cc-by/er/ (si rifà da capo con tutti i comuni ogni volta)")
    r.add_argument("--dtm", type=Path, nargs="+", help="DTM: GeoTIFF piccolo, o i quadranti (zip o TIFF) da ritagliare")
    r.add_argument("--archivio", type=Path, required=True); r.add_argument("--riquadro", nargs=4, type=float)
    r.add_argument("--strato", help="strato delle UVL (predefinito: V_UVL_GPG o UVL_Unita_volumetrica)")
    r.add_argument("--comune", help="nome dell'archivio del comune (minuscole e trattini, es. rimini): scrive in "
                   "cc-by/er/<comune>/prodotti/, autonomo dagli altri comuni (più comuni in parallelo, cartelle diverse)")
    r.add_argument("--nome", help="nome dell'archivio in archivi.json (predefinito: «DBTR Emilia-Romagna – <Comune>»)")
    r.add_argument("--istat", help="codice ISTAT del comune (6 cifre), se il nome non è nella tabella uvl.COMUNI_ISTAT: la pagina "
                   "usa il confine del comune come zona coperta dal DBTR")
    r.add_argument("--parziale", action="store_true", help="estrazione di una parte del comune (es. Ravenna, solo l'ospedale): "
                   "zona coperta = riquadro dei corpi, mai il confine del comune")
    r.add_argument("--archivi-json", action="store_true", help="scrive o aggiorna <archivio>/archivi.json con il DBTR per primo")
    r.add_argument("--terreno-archivio", action="store_true", help="scrive anche terreno.pmtiles e dtm_cog.tif nell'archivio "
                   "(prove sul PC senza server; predefinito: il terreno viene dalla rotta /api/terreno del server)")
    ds = sub.add_parser("dtm-server", help="DTM (uno o più zip, TIFF o ASCII Grid, o una cartella) → COG unico per zona per la "
                        "rotta /api/terreno del server")
    ds.add_argument("--file", type=Path, nargs="+", required=True, help="file o cartelle (le tavole si mosaicano)")
    ds.add_argument("--uscita", type=Path, required=True)
    ds.add_argument("--regione", default="er", choices=("er", "veneto"), help="scheda: licenza, attribuzione e nome in legenda")
    ds.add_argument("--crs", help="sistema dei file che non lo dicono (es. EPSG:6876 per le tavole ASCII Grid del Veneto)")
    ds.add_argument("--attribuzione"); ds.add_argument("--licenza"); ds.add_argument("--nome")
    rt = sub.add_parser("dtm-ritaglia", help="finestra di un quadrante del DTM 5 m (zip o TIFF) in un GeoTIFF piccolo")
    rt.add_argument("--file", type=Path, required=True)
    rt.add_argument("--riquadro", nargs=4, type=float, required=True, metavar=("X0", "Y0", "X1", "Y1"), help="EPSG:7791")
    rt.add_argument("--uscita", type=Path, required=True); rt.add_argument("--margine", type=float, default=0.0)
    qa = sub.add_parser("controlla-archivio", help="controlli di qualità di un archivio preparato (indice, celle, altezze, cortili)")
    qa.add_argument("cartella", type=Path, help="…/cc-by/er/<comune>/prodotti")
    qa.add_argument("--punto", nargs=3, action="append", metavar=("LON", "LAT", "NOME"), help="punto che deve cadere in un edificio")
    dv = sub.add_parser("dividi", help="estrazione DBTR raggruppata → un GeoPackage ridotto per comune (COD_COM, o confine "
                        "ISTAT per gli edifici senza codice), da passare a prepara --gpkg")
    dv.add_argument("--gpkg", type=Path, nargs="+", required=True, help="estrazioni (GeoPackage o cartelle Shapefile)")
    dv.add_argument("--codici", nargs="+", default=[], help="codici catastali COD_COM del comune (es. A944)")
    dv.add_argument("--istat", nargs="+", default=[], help="codici ISTAT del comune per gli edifici senza COD_COM (es. 037006)")
    dv.add_argument("--uscita", type=Path, help="cartella: <uscita>/<estrazione>/estraz_procons.gpkg")
    dv.add_argument("--elenco", action="store_true", help="solo l'elenco dei COD_COM con il comune ISTAT che li contiene")
    aj = sub.add_parser("archivi-json", help="scrive <archivio>/archivi.json dagli archivi presenti (DBTR dei comuni prima; "
                        "le prove OSM solo con --con-prova)")
    aj.add_argument("--archivio", type=Path, required=True)
    aj.add_argument("--con-prova", action="store_true", help="elenca anche gli archivi di prova OSM, per ultimi (prima del 07/11/2026 "
                    "era il comportamento predefinito)")
    aj.add_argument("--senza-prova", action="store_true", help="(predefinito dal 07/11/2026; resta per i comandi già scritti)")
    d = sub.add_parser("demo"); d.add_argument("--uscita", type=Path, required=True)
    o = sub.add_parser("ortofoto-sito", help="ortofoto AGEA scaricate a mano → 50 cm, COG e PMTiles del sito")
    o.add_argument("--sito", required=True); o.add_argument("--anno", type=int, required=True)
    o.add_argument("--archivio", type=Path, required=True); o.add_argument("tessere", nargs="+", type=Path)
    li = sub.add_parser("lidar", help="pipeline notturna a tessere (Fase C)")
    li.add_argument("--zona", required=True, help="nome del TOML in zone/, percorso di un TOML o «auto»")
    li.add_argument("--archivio", type=Path, required=True); li.add_argument("--stato", type=Path, required=True)
    li.add_argument("--prodotti", type=Path, help="cartella dei prodotti (predefinita: archivio della licenza)")
    li.add_argument("--radice", type=Path, help="cartella che sostituisce {radice} negli URL (campione)")
    li.add_argument("--subito", action="store_true", help="ignora la finestra oraria")
    li.add_argument("--max-minuti", type=float); li.add_argument("--tessere", nargs="+")
    li.add_argument("--aggiorna", action="store_true", help="ricontrolla le tessere fatte (aggiornamento annuale)")
    ls = sub.add_parser("lidar-stato"); ls.add_argument("--stato", type=Path, required=True)
    lce = sub.add_parser("lidar-celle", help="elenco delle celle di falde e alberi in ogni lidar/indice.json dell'archivio "
                                             "(la pagina 3D chiede solo quelle; 09/11/2026 b)")
    lce.add_argument("--archivio", type=Path, required=True)
    lf = sub.add_parser("lidar-fonti"); lf.add_argument("--zona", default="rimini"); lf.add_argument("--prova", action="store_true")
    lc = sub.add_parser("lidar-copertura", help="maschera della copertura di una fonte (zone/coperture/), una richiesta")
    lc.add_argument("--zona", required=True); lc.add_argument("--fonte", required=True); lc.add_argument("--passo", type=float, default=100.0)
    lk = sub.add_parser("lidar-corpi", help="corpi dal solo LiDAR (raggruppamento per altezza) per una zona senza sagome")
    lk.add_argument("--zona", required=True); lk.add_argument("--archivio", type=Path, required=True)
    lk.add_argument("--stato", type=Path, default=Path("/tmp/edifici_stato")); lk.add_argument("--radice", type=Path)
    lk.add_argument("--prodotti", type=Path); lk.add_argument("--tessere", nargs="+")
    lk.add_argument("--riquadro", nargs=4, type=float, help="x0 y0 x1 y1 nel sistema della zona")
    lx = sub.add_parser("lidar-indice", help="indice dei file di una fonte a più file (solo le intestazioni)")
    lx.add_argument("--zona", required=True); lx.add_argument("--fonte", required=True)
    lx.add_argument("--max", type=int, help="al più tanti file nuovi per volta"); lx.add_argument("--pausa", type=float, default=0.3)
    ca = sub.add_parser("campione", help="campione LiDAR sintetico con i prodotti della Fase A")
    ca.add_argument("--uscita", type=Path, required=True)
    oc = sub.add_parser("osm-campione", help="archivio di prova ODbL di un quartiere: OSM (una chiamata all'API) + DTM 5 m dal WCS")
    oc.add_argument("--riquadro", nargs=4, type=float, required=True, metavar=("LON0", "LAT0", "LON1", "LAT1"))
    oc.add_argument("--nome", required=True); oc.add_argument("--archivio", type=Path, required=True)
    oc.add_argument("--altezza-stima", type=float, default=9.0, help="altezza dei corpi senza height né building:levels (0 = nessuna)")
    oc.add_argument("--senza-dtm", action="store_true"); oc.add_argument("--osm", type=Path, help="file .osm già scaricato")
    oc.add_argument("--dtm", type=Path, help="DTM già scaricato (es. grezzi/dtm5.tif) o quadrante: nessuna richiesta al WCS")
    dw = sub.add_parser("dtm-wcs", help="DTM 5 m dell'Emilia-Romagna dal WCS pubblico, a blocchi di 10 km, in un GeoTIFF")
    dw.add_argument("--riquadro", nargs=4, type=float, required=True, metavar=("X0", "Y0", "X1", "Y1"), help="EPSG:7791")
    dw.add_argument("--uscita", type=Path, required=True)
    im = sub.add_parser("importa-modello", help="DXF o IFC dell'utente → GeoJSON dei corpi con le falde")
    im.add_argument("file", type=Path); im.add_argument("--uscita", type=Path, required=True)
    im.add_argument("--crs", help="sistema delle coordinate del disegno se è già georeferenziato (es. EPSG:7791)")
    im.add_argument("--posa", nargs="+", metavar="X,Y=LON,LAT",
                    help="due punti noti (coordinate del disegno = lon,lat) oppure uno solo più --rotazione")
    im.add_argument("--rotazione", type=float, default=0.0, help="azimut dell'asse +Y del disegno (gradi da nord vero in senso orario), con un solo punto di posa")
    im.add_argument("--unita", type=float, help="metri per unità del disegno (predefinito: dal file, altrimenti 1)")
    im.add_argument("--edificio", default="MODELLO")
    im.add_argument("--grande", action="store_true", help="file molto grandi: fino a 500 MB, 8 GB di memoria, 30 minuti (solo sul PC)")
    za = sub.add_parser("zornade-altezze", help="estratto di Zornade → corpi e confronto nell'archivio ODbL (Fase E)")
    za.add_argument("--file", type=Path, required=True); za.add_argument("--strato")
    za.add_argument("--archivio", type=Path, required=True)
    za.add_argument("--confronta-con", type=Path, help="cartella contesto/ dei corpi CC BY della Fase A")
    za.add_argument("--mappa", nargs="+", metavar="CHIAVE=COLONNA", help="colonne con nomi diversi (es. altezza=h_lidar)")
    za.add_argument("--soglia-iou", type=float, default=0.5)
    za.add_argument("--sintetico", action="store_true", help="segna i prodotti come sintetici (campione)")
    rg = sub.add_parser("regioni", help="fonti per regione (fonti/regioni.toml): riepilogo, controllo, prova dal vivo")
    rg.add_argument("--prova", action="store_true", help="ricontrolla dal vivo gli url_prova")
    rg.add_argument("--markdown", action="store_true", help="tabella per il README")
    zc = sub.add_parser("zornade-campione", help="estratto Zornade sintetico sull'isolato di prova")
    zc.add_argument("--uscita", type=Path, required=True)
    rc = sub.add_parser("regionale-campione", help="piccolo campione dal servizio di una regione (fonti/<regione>.toml)")
    rc.add_argument("--riquadro", nargs=4, type=float, required=True, help="x0 y0 x1 y1 nel sistema del servizio (crs_servizio)")
    rc.add_argument("--max", type=int, default=500); rc.add_argument("--strato"); rc.add_argument("--uscita", type=Path, required=True)
    for nome in ("controlla-regione", "prepara-regione"):
        pr = sub.add_parser(nome, help="DB topografico regionale → corpi (adattatori di regionali.py)")
        pr.add_argument("--file", type=Path, required=True); pr.add_argument("--strato")
        pr.add_argument("--crs-file", help="sistema del file se non lo dichiara")
        if nome == "prepara-regione":
            pr.add_argument("--dtm", type=Path, help="DTM nel sistema della zona (obbligatorio per la Liguria)")
            pr.add_argument("--archivio", type=Path, required=True); pr.add_argument("--riquadro", nargs=4, type=float)
            # un archivio per comune anche fuori dall'ER (07/11/2026, coda «Aggiungi DBTR»): cc-by/<zona>/<comune>/prodotti/
            pr.add_argument("--comune", help="nome dell'archivio del comune (minuscole e trattini): cc-by/<zona>/<comune>/prodotti/")
            pr.add_argument("--nome", help="nome dell'archivio in archivi.json")
            pr.add_argument("--istat", help="codice ISTAT del comune intero (6 cifre): zona coperta = confine del comune")
            pr.add_argument("--parziale", action="store_true", help="estrazione di una parte del comune: zona coperta = riquadro")
            pr.add_argument("--terreno-archivio", action="store_true", help="scrive anche terreno.pmtiles e dtm_cog.tif nell'archivio")
            pr.add_argument("--attribuzione-dtm", help="attribuzione del DTM passato con --dtm in LICENZE.txt "
                            "(predefinita: fonti.dtm5 o fonti.dtm del TOML della zona)")
    # altezze contro DSM − DTM (08/11/2026, gruppo C): la funzione è altezze_dsm.confronta_dsm
    cd = sub.add_parser("confronta-dsm", help="altezze di un archivio o di un file contro DSM − DTM (mediana, quota entro 2 m)")
    cd.add_argument("--dsm", nargs="+", required=True, help="DSM: GeoTIFF, ASCII Grid o zip con un ASCII (più tessere)")
    cd.add_argument("--dtm", nargs="+", required=True, help="DTM delle stesse tessere")
    cd.add_argument("--crs-raster", help="sistema dei raster se non lo dichiarano (gli ASCII di solito no)")
    cd.add_argument("--archivio-comune", type=Path, help="cartella prodotti di un archivio preparato (campo gronda)")
    cd.add_argument("--file", type=Path, help="file del DB topografico (con --campo, o con l'adattatore della zona)")
    cd.add_argument("--campo", help="campo dell'altezza nel file (es. MED_ALT); senza: adattatore di fonti/<zona>.toml")
    cd.add_argument("--crs-file"); cd.add_argument("--dtm-quota", type=Path, help="DTM per l'adattatore (Liguria)")
    cd.add_argument("--area-min", type=float, default=30.0)
    # coda «Aggiungi DBTR» (07/11/2026): file caricati dagli utenti, preparati qui, installati dopo l'approvazione
    co = sub.add_parser("coda", help="coda «Aggiungi DBTR»: prepara i file ricevuti e installa quelli approvati")
    co.add_argument("--cartella", type=Path, default=Path("/dati/edifici_coda"), help="cartella della coda")
    co.add_argument("--archivio", type=Path, default=Path("/dati/edifici"))
    co.add_argument("--ciclo", action="store_true", help="resta acceso: un giro al minuto (servizio edifici-coda)")
    co.add_argument("--pausa-url", default="http://api:8000/api/salute",
                    help="aspetta finché il server calcola previsioni (vuoto: non controllare)")
    co.add_argument("--finestra", default="03:15-07:00", help="ore in cui non si prepara (pipeline LiDAR); vuoto: sempre")
    cr = sub.add_parser("coda-ripristina", help="torna all'archivio precedente di un comune (copie in _precedenti/)")
    cr.add_argument("--archivio", type=Path, default=Path("/dati/edifici")); cr.add_argument("--zona", required=True)
    cr.add_argument("--comune", required=True)
    a = p.parse_args(argv)
    if a.cmd in ("coda", "coda-ripristina"):
        from . import coda as CO
        if a.cmd == "coda-ripristina":
            print(json.dumps(CO.ripristina(a.archivio, a.zona, a.comune), ensure_ascii=False, indent=1))
            return 0
        if a.ciclo:
            CO.ciclo(a.cartella, a.archivio, a.pausa_url or None, a.finestra or None)
            return 0
        print(json.dumps(CO.un_giro(a.cartella, a.archivio, a.pausa_url or None, None), ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "dtm-wcs":
        from . import dtm_wcs as DW
        print(json.dumps(DW.scarica(tuple(a.riquadro), a.uscita), ensure_ascii=False))
        return 0
    if a.cmd == "osm-campione":
        from . import osm_campione as OC
        esito = OC.prepara(tuple(a.riquadro), a.archivio, a.nome, a.altezza_stima or None, not a.senza_dtm, a.osm, dtm_file=a.dtm)
        print(json.dumps({k: esito[k] for k in ("corpi", "tessere_corpi", "celle", "centro", "riquadro") if k in esito}, ensure_ascii=False))
        print("riga per /edifici3d/archivi.json:", json.dumps(OC.voce_archivi(a.nome), ensure_ascii=False))
        return 0
    if a.cmd == "dtm-server":
        from . import dtm_locale as DL
        print(json.dumps(DL.cog_server(a.file, a.uscita, attribuzione=a.attribuzione, crs=a.crs, regione=a.regione,
                                       licenza=a.licenza, nome=a.nome), ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "dtm-ritaglia":
        from . import dtm_locale as DL
        print(json.dumps(DL.ritaglia(a.file, a.riquadro, a.uscita, a.margine), ensure_ascii=False))
        return 0
    if a.cmd == "controlla-archivio":
        r = controlla_archivio(a.cartella, [(float(x), float(y), n) for x, y, n in (a.punto or [])])
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0 if not r["problemi"] else 1
    if a.cmd == "dividi":
        from . import dividi as DV
        if a.elenco:
            _, codici = DV.edifici(a.gpkg)
            print(json.dumps(codici, ensure_ascii=False, indent=1))
            return 0
        if not a.uscita or not a.codici:
            p.error("dividi: servono --codici e --uscita (o --elenco)")
        print(json.dumps(DV.dividi(a.gpkg, a.codici, a.istat, a.uscita), ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "archivi-json":
        print(json.dumps(scrivi_archivi_json(a.archivio, prova=a.con_prova and not a.senza_prova), ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "regioni":
        from . import regioni as RG
        d = RG.carica()
        err = RG.controlla(d)
        if a.markdown:
            print(RG.markdown(d))
        else:
            for r in RG.riepilogo(d):
                print(f"{r['nome']:<32} edifici: {r['edifici']:<16} dtm: {r['dtm']:<16} dsm: {r['dsm']:<16} ortofoto: {r['ortofoto']}")
            print("conteggi:", RG.conteggi(d), "– verificato il", d.get("verificato"))
        if a.prova:
            for x in RG.prova(d):
                print(f"{x['regione']:<32} {x['tema']:<9} {x['stato']:<16} {x['esito']:<40} {x['nome']}")
        for e in err:
            print("ERRORE:", e)
        return 1 if err else 0
    if a.cmd in ("zornade-altezze", "zornade-campione"):
        return _zornade(a)
    if a.cmd in ("regionale-campione", "controlla-regione", "prepara-regione"):
        return _regionale(a)
    if a.cmd == "confronta-dsm":
        from . import altezze_dsm as AD, regionali as R
        ad = crs_zona = None
        if a.file and not a.campo:
            z = F.carica_zona(a.zona)
            ad, crs_zona = R.ADATTATORI[z["fonti"]["edifici"]["adattatore"]], z["zona"]["crs"]
        r = AD.confronta_dsm(a.dsm, a.dtm, a.crs_raster, a.archivio_comune, a.file, a.campo, ad, a.crs_file, crs_zona,
                             a.dtm_quota, a.area_min)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "lidar":
        return _lidar(a)
    if a.cmd == "lidar-stato":
        from . import pipeline as PL
        r = PL.riepilogo(a.stato)
        for z in r["zone"]:
            print(f"{z.get('nome')} ({z.get('zona')}): {z.get('conteggi')} su {z.get('totale_tessere')} tessere; "
                  f"ultima esecuzione: {(z.get('esecuzioni') or [{}])[-1].get('esito', '—')}")
        print(json.dumps(r, ensure_ascii=False, indent=1)[:4000])
        return 0
    if a.cmd == "lidar-celle":
        from . import pipeline as PL
        print(json.dumps(PL.aggiorna_celle_archivio(a.archivio), ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "lidar-fonti":
        return _fonti(a)
    if a.cmd == "lidar-corpi":
        from . import pipeline as PL
        pl = PL.Pipeline(PL.carica_zona(a.zona), a.archivio, a.stato, prodotti=a.prodotti, radice=a.radice)
        print(json.dumps(pl.corpi_lidar(a.tessere, a.riquadro), ensure_ascii=False, indent=1))
        return 0
    if a.cmd in ("lidar-copertura", "lidar-indice"):
        from . import coperture as CO, pipeline as PL
        z = PL.carica_zona(a.zona)
        r = CO.maschera_fonte(z, a.fonte, passo=a.passo) if a.cmd == "lidar-copertura" else \
            CO.indice_fonte(z, a.fonte, massimo=a.max, pausa=a.pausa)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "campione":
        return _campione(a.uscita)
    if a.cmd == "importa-modello":
        from . import importa as I
        posa = I.posa_da_argomenti(a.posa, a.rotazione, a.crs)
        r = I.importa_sicuro(a.file, posa=posa, unita=a.unita, edificio=a.edificio, grande=a.grande)
        a.uscita.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({k: v for k, v in r.items() if k != "features"} | {"corpi": len(r["features"])}, ensure_ascii=False, indent=1))
        return 0
    zona = F.carica_zona(a.zona)

    if a.cmd == "scarica":
        for f in F.scarica_fonte(a.archivio, zona, a.fonte, quadranti=a.quadrante):
            print(f)
        return 0
    if a.cmd == "controlla-uvl":
        if a.gpkg:
            prop = [x for x, _ in U.leggi_gpkg(a.gpkg, a.strato, riquadro=a.riquadro)]
            edi = U.leggi_edifici(a.gpkg, riquadro=a.riquadro)
            if edi:
                print(f"Edifici (V_EDI_GPG) nel riquadro: {len(edi)}; con foglio e numero: "
                      f"{sum(1 for e in edi.values() if e.get('FOGLIO') and e.get('NUMERO'))}; con destinazione d'uso: "
                      f"{sum(1 for e in edi.values() if e.get('D_CT_USO'))}")
        elif a.geojson:
            prop = U.leggi_geojson_wms(a.geojson)
        elif a.wms_punto:
            import httpx
            wms = zona["fonti"]["dbtr_uvl"]["wms"]
            prop = [f.get("properties", {}) for f in httpx.get(U.url_getfeatureinfo(wms, *a.wms_punto), timeout=60).json().get("features", [])]
        else:
            p.error("serve --gpkg, --geojson o --wms-punto")
        ctl = U.controlla(prop)
        print(U.rapporto(ctl))
        if a.json:
            print(json.dumps(ctl, ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "prepara":
        import time
        t0 = time.time()
        import re
        f = F.fonti(zona)["dbtr_uvl"]
        if a.comune:
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,40}", a.comune) or a.comune in ("prodotti", "grezzi", "lidar"):
                p.error("--comune: minuscole, cifre e trattini (es. rimini, montescudo-montecolombo)")
            out = F.cartella(a.archivio, zona, f.licenza, "") / a.comune / "prodotti"
        else:
            out = F.cartella(a.archivio, zona, f.licenza, "prodotti")
        if not a.nome:
            a.nome = "DBTR Emilia-Romagna" + (f" – {a.comune.replace('-', ' ').title()}" if a.comune else "")
        righe, edi, sorgenti, visti = [], {}, [], set()
        for g in a.gpkg:
            r_g = U.leggi_gpkg(g, a.strato, riquadro=a.riquadro)
            e_g = U.leggi_edifici(g, riquadro=a.riquadro)
            nuove = [x for x in r_g if str(x[0].get("ID_E")) not in visti]    # due estrazioni vicine: corpi una volta sola
            visti.update(str(x[0].get("ID_E")) for x in nuove)
            righe += nuove; edi.update(e_g)
            comuni = sorted({str(e.get("COD_COM")) for e in e_g.values() if e.get("COD_COM")})
            sorgenti.append({"file": f"{g.parent.name}/{g.name}" if g.is_file() else g.name, "uvl_lette": len(r_g),
                             "uvl_nuove": len(nuove), "edifici_letti": len(e_g), "comuni_catastali": comuni[:12]})
        if a.istat and not re.fullmatch(r"\d{6}", a.istat):
            p.error("--istat: sei cifre (es. 099014)")
        istat = None if a.parziale else (a.istat or U.COMUNI_ISTAT.get(a.comune or ""))
        extra = {"nome": a.nome, "comune": a.comune or None, "istat": istat, "parziale": True if a.parziale else None,
                 "fonte_edifici": sorgenti,
                 "fonti_file": {"corpi.pmtiles": f.attribuzione, "contesto/": f.attribuzione}}
        if a.dtm:
            dt = F.fonti(zona)["dtm5"]
            if a.terreno_archivio:
                extra["fonti_file"].update({"terreno.pmtiles": dt.attribuzione, "dtm_cog.tif": dt.attribuzione})
            extra["attribuzione_terreno"] = dt.attribuzione      # quote dei corpi (e terreno della rotta del server)
        extra = {k: v for k, v in extra.items() if v is not None}
        esito = prepara(righe, a.dtm if not a.dtm or len(a.dtm) > 1 else a.dtm[0], out, f.licenza, f.attribuzione,
                        edifici=edi, extra=extra, terreno=a.terreno_archivio)
        esito["secondi"] = round(time.time() - t0, 1)
        (out / "indice.json").write_text(json.dumps(esito, ensure_ascii=False, indent=1), encoding="utf-8")
        (out.parent / "LICENZE.txt").write_text(
            f"Sagome e altezze degli edifici: {f.attribuzione} – {f.dati.get('scheda', '')}\n"
            "Licenza: Creative Commons Attribuzione 4.0 (https://creativecommons.org/licenses/by/4.0/deed.it).\n"
            + (f"Quote del terreno dei corpi{' e terreno (terreno.pmtiles, dtm_cog.tif)' if a.terreno_archivio else ''}: "
               f"{F.fonti(zona)['dtm5'].attribuzione}\n" if a.dtm else "")
            + "Elaborazione: EuGEnio (Stato Critico), regole delle altezze nel README della fase 10.\n", encoding="utf-8")
        if a.archivi_json:
            esito["archivi_json"] = scrivi_archivi_json(a.archivio)
        print(json.dumps({k: v for k, v in esito.items() if k != "nomi_celle"}, ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "demo":
        esito = demo(a.uscita)
        print(json.dumps(esito, ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "ortofoto-sito":
        print(json.dumps(O.prepara(a.tessere, a.sito, a.anno, a.archivio), ensure_ascii=False, indent=1))
        return 0
    return 1


def _regionale(a) -> int:
    """Adattatori dei DB topografici di Lombardia, FVG e Liguria (Fase E, 05/11/2026)."""
    from . import regionali as R
    zona = F.carica_zona(a.zona)
    f = zona["fonti"]["edifici"]
    if a.cmd == "regionale-campione":
        fonte = dict(f, strato=a.strato or f.get("strato"))
        print(json.dumps(R.scarica_campione(fonte, a.riquadro, a.uscita, a.max), ensure_ascii=False, indent=1))
        return 0
    righe, crs_file = R.leggi_file(a.file, a.strato)
    ad = R.scegli_adattatore(f, righe)               # `alternativi` del TOML se al file mancano i campi (08/11/2026)
    if a.cmd == "controlla-regione":
        print(json.dumps(R.controlla(righe, ad), ensure_ascii=False, indent=1))
        return 0
    crs = zona["zona"]["crs"]
    corpi, res = R.corpi(righe, ad, crs, a.crs_file or crs_file, a.dtm, a.riquadro)
    extra = {"fonte_edifici": res}
    if a.comune:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,40}", a.comune) or a.comune in ("prodotti", "grezzi", "lidar"):
            raise SystemExit("--comune: minuscole, cifre e trattini (es. bergamo)")
        if a.istat and not re.fullmatch(r"\d{6}", a.istat):
            raise SystemExit("--istat: sei cifre")
        out = F.cartella(a.archivio, zona, f["licenza"], "") / a.comune / "prodotti"
        extra.update({"nome": a.nome or f"{zona['zona']['nome']} – {a.comune.replace('-', ' ').title()}", "comune": a.comune})
        if a.istat and not a.parziale:
            extra["istat"] = a.istat
        if a.parziale:
            extra["parziale"] = True
    else:
        out = F.cartella(a.archivio, zona, f["licenza"], "prodotti")
        if a.nome:
            extra["nome"] = a.nome
    esito = prepara_corpi(corpi, a.dtm, out, f["licenza"], f.get("attribuzione") or ad.attribuzione, crs=crs, extra=extra,
                          terreno=getattr(a, "terreno_archivio", False))
    if a.comune:
        # testo secondo la licenza (CC BY 4.0/2.5, IODL 2.0, CC0 1.0: 08/11/2026) e attribuzione del DTM delle quote
        fd = zona["fonti"].get("dtm5") or zona["fonti"].get("dtm") or {}
        att_dtm = getattr(a, "attribuzione_dtm", None) or fd.get("attribuzione")
        (out.parent / "LICENZE.txt").write_text(
            f"Sagome e altezze degli edifici: {f.get('attribuzione') or ad.attribuzione} – {f.get('scheda', '')}\n"
            f"Licenza: {TESTI_LICENZA.get(f['licenza'], f['licenza'])}.\n"
            + (f"Quote del terreno dei corpi: {att_dtm}\n" if a.dtm and att_dtm else "")
            + "Elaborazione: EuGEnio (Stato Critico), adattatori di edifici3d/regionali.py e edifici3d/adattatori/.\n",
            encoding="utf-8")
    print(json.dumps({k: v for k, v in esito.items() if k != "nomi_celle"}, ensure_ascii=False, indent=1))
    return 0


def _zornade(a) -> int:
    from . import zornade as Z
    if a.cmd == "zornade-campione":
        print(Z.campione(a.uscita))
        return 0
    zona = F.carica_zona(a.zona)
    crs = zona["zona"].get("crs", "EPSG:7791")
    mappa = dict(x.split("=", 1) for x in (a.mappa or []))
    corpi, res = Z.leggi(a.file, a.strato, crs=crs, mappa=mappa)
    confronto = None
    cambiati = []
    if a.confronta_con:
        base = Z.corpi_da_contesto(a.confronta_con, crs)
        confronto = Z.confronta(base, corpi, a.soglia_iou)
        cambiati = Z.applica_altezze(base, corpi, a.soglia_iou)
        res["corpi_base_con_altezza_zornade"] = len(cambiati)
    uscita = F.cartella(a.archivio, zona, Z.LICENZA, "prodotti") / "zornade"
    esito = Z.prepara(corpi + cambiati, uscita, res, confronto, sintetico=a.sintetico, crs=crs)
    print(json.dumps({k: v for k, v in esito.items() if k != "attribuzione_html"}, ensure_ascii=False, indent=1))
    return 0


def demo(uscita: Path, stato: Path | None = None) -> dict:
    """Demo sintetica del sito: prodotti della Fase A e, dal campione LiDAR sintetico, le falde (lidar/)."""
    import shutil
    import tempfile
    uscita = Path(uscita).resolve()
    uscita.mkdir(parents=True, exist_ok=True)
    tif = Path(uscita) / "_dtm_sintetico.tif"
    S.dtm(tif)
    esito = prepara(S.uvl(), tif, uscita, U.LICENZA, "Dati sintetici di esempio (EuGEnio)", sintetico=True)
    tif.unlink()
    (uscita / "consumi_esempio.json").write_text(json.dumps(
        {"sintetico": True, "avviso": S.AVVISO, "edificio": "E-DEMO", "unita": "Smc", "mesi": S.consumi_mensili()},
        ensure_ascii=False, indent=1), encoding="utf-8")
    from . import campione as K, pipeline as PL
    shutil.rmtree(uscita / "lidar", ignore_errors=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        K.genera(tmp)
        z = PL.carica_zona("campione")
        pl = PL.Pipeline(z, tmp / "archivio", stato or (tmp / "stato"), prodotti=uscita, radice=tmp)
        pl.z["edifici"] = {"contesto": str(uscita / "contesto")}
        esito["lidar"] = pl.esegui(subito=True)
    return esito


def _campione(uscita: Path) -> int:
    """Campione LiDAR sintetico più i prodotti della Fase A dell'isolato sintetico (uscita/prodotti)."""
    from . import campione as K
    uscita.mkdir(parents=True, exist_ok=True)
    K.genera(uscita)
    tif = uscita / "_dtm_sintetico.tif"
    S.dtm(tif)
    prepara(S.uvl(), tif, uscita / "prodotti", U.LICENZA, "Dati sintetici di esempio (EuGEnio)", sintetico=True)
    tif.unlink()
    print(f"campione scritto in {uscita}: dsm/, dtm/, las/, prodotti/ (zona di prova: zone/campione.toml, --radice {uscita})")
    return 0


def _lidar(a) -> int:
    from . import pipeline as PL
    aggiorna = a.aggiorna
    if a.zona == "auto":
        z, annuale = PL.scegli_zona(a.stato, archivio=a.archivio)
        if z is None:
            print("nessuna zona con fonti LiDAR attive: niente da fare (vedi `lidar-fonti`)")
            return 0
        aggiorna = aggiorna or annuale
    else:
        z = PL.carica_zona(a.zona)
    pl = PL.Pipeline(z, a.archivio, a.stato, prodotti=a.prodotti, radice=a.radice)
    esito = pl.esegui(subito=a.subito, max_minuti=a.max_minuti, solo=a.tessere, aggiorna=aggiorna)
    print(json.dumps({"zona": z["zona"]["codice"], **esito}, ensure_ascii=False, indent=1))
    return 0


def _fonti(a) -> int:
    from . import pipeline as PL
    z = PL.carica_zona(a.zona)
    for f in PL.elenco_fonti(z):
        print(f"{f['id']:<22} {f['tipo']:<4} {f['stato']:<10} {f['licenza']:<14} {f['motivo']}")
    if a.prova:   # prova dal vivo sulla tessera al centro del riquadro: copertura (quadro di unione) e risposta del server
        import httpx
        pl = PL.Pipeline(z, Path("/tmp"), Path("/tmp"))
        x0, y0, x1, y1 = z["zona"]["riquadro"]
        lato = z["zona"]["lato_tessera"]
        t = pl.griglia[(int(((x0 + x1) / 2) // lato), int(((y0 + y1) / 2) // lato))]
        print(f"prova sulla tessera {t.nome}")
        for k, f in (z.get("fonti") or {}).items():
            esito = []
            if f.get("quadro_unione"):
                try:
                    pr = pl._quadro(f["quadro_unione"], t)
                    esito.append(f"quadro di unione: {'coperta ' + str(pr.get('TAVOLA', '')) if pr else 'non coperta'}")
                except Exception as e:
                    esito.append(f"quadro di unione: errore {type(e).__name__}")
            u = (f.get("url") or "").strip()
            if u and not u.startswith("file:"):
                try:
                    r = httpx.get(pl.url(f, t).replace("size=1000,1000", "size=10,10").replace("bbox=%s,%s,%s,%s" % (t.x0, t.y0, t.x1, t.y1),
                                  "bbox=%s,%s,%s,%s" % (t.x0, t.y0, t.x0 + 20, t.y0 + 20)), timeout=40)
                    esito.append(f"HTTP {r.status_code} {r.headers.get('content-type', '')}")
                except Exception as e:
                    esito.append(f"non raggiungibile ({type(e).__name__})")
            print(f"  {k:<22} " + ("; ".join(esito) or "nessun indirizzo da provare"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
