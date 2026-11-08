"""DB topografici regionali fuori dall'Emilia-Romagna → corpi di fabbrica (Fase E, 05/11/2026).

Stesso modello per corpo della Fase A (`modello.Corpo`): sagoma nel sistema della zona, quota del terreno, gronda (m
sopra il terreno), tetto piano (le falde arrivano dal LiDAR nella Fase C), fonte e qualità di ogni dato, edificio di
appartenenza e licenza della sagoma. Un adattatore per formato; le fonti (URL, strati, licenze) stanno nei TOML in
`fonti/<regione>.toml`, mai nel codice.

Formati verificati dal vivo il 04–05/11/2026 dal container di sviluppo, su piccoli campioni (nessun blocco aggirato):

- **Lombardia, DBGT classe 020101 «Unità volumetrica»** (ArcGIS REST `DBGT_Tema0201_Edificato/MapServer/0`, CC BY 4.0):
  `UN_VOL_AV` altezza del volume (m), `UN_VOL_QE` quota di estrusione (m s.l.m., sommità), z dei vertici = quota della
  base (con `returnZ`), `CEDIUV` edificio di appartenenza, `UN_VOL_POR` tipo di porzione (codici 01–04, tenuti in `extra`),
  `CLASSID` identificativo. Campione di Milano (60 volumi): `UN_VOL_QE − z = UN_VOL_AV` al centimetro in 51; nei 9 con
  porzione «03» la z della base sta 3,5 m più in basso (parte sotto terra), quindi la quota del terreno si prende come
  `UN_VOL_QE − UN_VOL_AV` (o dal DTM, se c'è). L'altezza è alla sommità del volume: si usa come gronda («gronda o colmo
  da verificare» come per le UVL dell'ER).
- **Friuli Venezia Giulia, IRDAT «Edificato CTRN»** (WFS `EDIFICI`, uno strato per foglio della CTRN, EPSG:6708 =
  RDN2008/UTM 33N, CC BY 4.0 nella scheda del servizio): `ALTEZZA` (m), `QUOTA_PIEDE` e `QUOTA_GRONDA` (m s.l.m.),
  `VOLUME`, `CODICE`, `NOME` («EDIFICIO CIVILE», …), `ID`. Campione: `QUOTA_GRONDA − QUOTA_PIEDE = ALTEZZA`. Ogni elemento
  è un corpo; manca un identificativo d'edificio (ogni corpo è un edificio, unibile dall'utente).
- **Liguria, CTR 1:5000 3D / DB topografico, strato «Edificato»** (WFS `M2237:L8178`, EPSG:3003 Gauss-Boaga Ovest,
  CC BY 4.0): nessun campo di altezza; la z dei vertici è **costante per poligono** (399 su 400 nel campione) ed è la quota
  della gronda: nel punto del primo edificio del campione la z vale 141,0 m e il DTM regionale 2023 (WMS `M2056`, strato
  `L6952`) 137 m, cioè 4 m di edificio. Quindi altezza = z − quota del DTM dentro la sagoma: **serve il DTM** (senza,
  il corpo si scarta). Campi `def_tipo_edil`, `def_cat_uso`, `def_sotterr`, `def_stato`, `def_porz_est`: si scartano i
  sotterranei, gli aggetti e gli stati diversi da «In esercizio»/«In costruzione».

Lo scaricamento di un campione (`campione_*`) chiede **una zona piccola** e un numero massimo di oggetti, una pagina alla
volta: serve alle prove e alla prima zona; l'archivio regionale completo si scarica una volta, dal server, con lo stesso
comando a pezzi o dal download ufficiale della Regione.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.ops import transform as sh_transform

from .modello import Corpo, numero

# ------------------------------------------------------------------------------------------------ utilità


def _vuoto(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v)) or str(v).strip() in ("", "Null", "NULL", "null")


def _poligono(g):
    """Geometria (dict GeoJSON o shapely) → poligono 2D più grande, con la z media del contorno esterno (o None)."""
    g = shape(g) if isinstance(g, dict) else g
    if g is None or g.is_empty:
        return None, None
    if isinstance(g, MultiPolygon):
        g = max(g.geoms, key=lambda x: x.area)
    if not isinstance(g, Polygon):
        return None, None
    zs = [c[2] for c in g.exterior.coords if len(c) > 2]
    z = sum(zs) / len(zs) if zs else None
    p2 = Polygon([(c[0], c[1]) for c in g.exterior.coords], [[(c[0], c[1]) for c in r.coords] for r in g.interiors])
    if not p2.is_valid:
        p2 = p2.buffer(0)
        if isinstance(p2, MultiPolygon):
            p2 = max(p2.geoms, key=lambda x: x.area)
    return p2, z


# nomi completi delle colonne lette dagli adattatori: negli Shapefile (DBF) i nomi si troncano a 10 caratteri
# (QUOTA_GRONDA → QUOTA_GRON, def_tipo_edil → def_tipo_e): si riportano al nome completo (07/11/2026, «Aggiungi DBTR»)
NOMI_COMPLETI = ("CLASSID", "CEDIUV", "UN_VOL_AV", "UN_VOL_QE", "UN_VOL_POR", "ID", "ALTEZZA", "QUOTA_PIEDE",
                 "QUOTA_GRONDA", "VOLUME", "CODICE", "NOME", "id", "def_tipo_edil", "def_cat_uso", "def_sotterr", "def_stato",
                 "def_porz_est", "ogr_fid")
_TRONCATI = {n[:10]: n for n in NOMI_COMPLETI if len(n) > 10}


def nomi_completi(p: dict) -> dict:
    """Proprietà con i nomi completi (gli altri restano come sono)."""
    if not any(k in _TRONCATI for k in p):
        return p
    return {_TRONCATI.get(k, k) if _TRONCATI.get(k, k) not in p else k: v for k, v in p.items()}


def _z_variabile(g) -> float:
    g = shape(g) if isinstance(g, dict) else g
    if isinstance(g, MultiPolygon):
        g = max(g.geoms, key=lambda x: x.area)
    zs = [c[2] for c in getattr(g, "exterior", g).coords if len(c) > 2] if g is not None else []
    return (max(zs) - min(zs)) if zs else 0.0


# ------------------------------------------------------------------------------------------------ adattatori


@dataclass
class Adattatore:
    chiave: str
    fonte: str                 # nome della fonte che va in fonte_sagoma
    licenza: str
    attribuzione: str
    crs_file: str              # sistema delle coordinate dei file/servizi della fonte
    campi_attesi: tuple
    serve_dtm: bool
    corpo: Callable            # (proprieta, poligono 2D nel sistema della zona, z media, quota DTM) → Corpo | None

    def descrizione(self) -> dict:
        return {"chiave": self.chiave, "fonte": self.fonte, "licenza": self.licenza, "crs_file": self.crs_file,
                "serve_dtm": self.serve_dtm, "campi_attesi": list(self.campi_attesi)}


def _corpo_lombardia(p: dict, g: Polygon, z: float | None, quota_dtm: float | None) -> Corpo | None:
    h = numero(p.get("UN_VOL_AV"))
    qe = numero(p.get("UN_VOL_QE"))
    if (h is None or h <= 0) and qe is not None and z is not None:
        h = qe - z                              # se manca l'altezza: quota di estrusione − quota della base
    if not h or h <= 0 or g.area < 1:
        return None
    # quota del terreno: sommità − altezza (nelle porzioni «03» la z della base sta ~3,5 m più in basso, sotto terra)
    base = qe - h if qe is not None else z
    q = quota_dtm if quota_dtm is not None else base
    sotto = round(base - z, 2) if (z is not None and base is not None and base - z > 0.5) else None
    fonte_h = "DBGT Lombardia UN_VOL_AV (gronda o colmo da verificare)"
    if quota_dtm is not None and base is not None:
        fonte_h += f"; base DBGT {base:.1f} m, DTM {quota_dtm:.1f} m"
    return Corpo(id=str(p.get("CLASSID") or p.get("OBJECTID")), edificio=str(p.get("CEDIUV") or p.get("CLASSID") or p.get("OBJECTID")),
                 sagoma=g, quota_terreno=q, gronda=float(h), tetto="piano", fonte_sagoma=LOMBARDIA.fonte,
                 licenza=LOMBARDIA.licenza, fonte_altezza=fonte_h, qualita="DBGT, altezza ±1–2 m (scala 1:2000)",
                 extra={"porzione": p.get("UN_VOL_POR"), "quota_estrusione": qe, "regione": "Lombardia",
                        **({"base_sotto_terra_m": sotto} if sotto else {})})


def _corpo_fvg(p: dict, g: Polygon, z: float | None, quota_dtm: float | None) -> Corpo | None:
    h = numero(p.get("ALTEZZA"))
    piede, gronda = numero(p.get("QUOTA_PIEDE")), numero(p.get("QUOTA_GRONDA"))
    if (h is None or h <= 0) and piede is not None and gronda is not None:
        h = gronda - piede
    if not h or h <= 0 or g.area < 1:
        return None
    q = quota_dtm if quota_dtm is not None else piede
    nome = str(p.get("NOME") or "").strip()
    uso = None
    if "CIVIL" in nome.upper():
        uso = "residenziale"
    elif any(k in nome.upper() for k in ("INDUSTR", "CAPANN")):
        uso = "capannone"
    return Corpo(id=str(p.get("ID")), edificio=str(p.get("ID")), sagoma=g, quota_terreno=q, gronda=float(h),
                 tetto="piano", fonte_sagoma=FVG.fonte, licenza=FVG.licenza,
                 fonte_altezza="CTRN FVG ALTEZZA (QUOTA_GRONDA − QUOTA_PIEDE)", qualita="CTRN 1:5000, altezza ±1–2 m",
                 uso=uso, extra={"codice": p.get("CODICE"), "nome": nome, "quota_piede": piede, "quota_gronda": gronda,
                                 "regione": "Friuli Venezia Giulia"})


_LIG_SCARTA_STATO = ("diruto", "rudere", "demolit", "distrutt")


def _corpo_liguria(p: dict, g: Polygon, z: float | None, quota_dtm: float | None) -> Corpo | None:
    if "sotterraneo" in str(p.get("def_sotterr") or "").lower() and "non" not in str(p.get("def_sotterr")).lower():
        return None
    if str(p.get("def_porz_est") or "").lower().startswith("aggett"):
        return None
    stato = str(p.get("def_stato") or "").lower()
    if any(s in stato for s in _LIG_SCARTA_STATO):
        return None
    if z is None or quota_dtm is None or g.area < 1:
        return None
    h = z - quota_dtm
    if h < 1.5 or h > 300:
        return None
    uso_testo = str(p.get("def_cat_uso") or "")
    uso = "residenziale" if uso_testo.lower().startswith("residenz") else None
    return Corpo(id=str(p.get("id") or p.get("ogr_fid")), edificio=str(p.get("id") or p.get("ogr_fid")), sagoma=g,
                 quota_terreno=quota_dtm, gronda=round(float(h), 2), tetto="piano", fonte_sagoma=LIGURIA.fonte,
                 licenza=LIGURIA.licenza, fonte_altezza=f"CTR 3D Liguria: quota di gronda {z:.1f} m − DTM {quota_dtm:.1f} m",
                 qualita="CTR 1:5000 3D, altezza ±2–3 m (gronda dalla CTR, terreno dal DTM)", uso=uso,
                 extra={"tipo": p.get("def_tipo_edil"), "uso_ctr": uso_testo, "quota_gronda": round(z, 2),
                        "regione": "Liguria"})


LOMBARDIA = Adattatore("lombardia_dbgt", "DBGT Lombardia – Unità volumetrica (020101)", "CC BY 4.0",
                       "Regione Lombardia – DBGT, Unità volumetrica (CC BY 4.0)", "EPSG:4326",
                       ("CLASSID", "CEDIUV", "UN_VOL_AV", "UN_VOL_QE", "UN_VOL_POR"), False, _corpo_lombardia)
FVG = Adattatore("fvg_ctrn", "IRDAT FVG – Edificato CTRN", "CC BY 4.0",
                 "Regione Autonoma Friuli Venezia Giulia – IRDAT, Edificato CTRN (CC BY 4.0)", "EPSG:6708",
                 ("ID", "ALTEZZA", "QUOTA_PIEDE", "QUOTA_GRONDA", "NOME"), False, _corpo_fvg)
LIGURIA = Adattatore("liguria_ctr3d", "Regione Liguria – CTR 3D, Edificato", "CC BY 4.0",
                     "Regione Liguria – Carta Tecnica Regionale 1:5000 3D / DB topografico (CC BY 4.0)", "EPSG:3003",
                     ("id", "def_tipo_edil", "def_cat_uso", "def_sotterr", "def_stato", "def_porz_est"), True, _corpo_liguria)

ADATTATORI: dict[str, Adattatore] = {a.chiave: a for a in (LOMBARDIA, FVG, LIGURIA)}


def _carica_adattatori_esterni() -> None:
    """Adattatori delle altre regioni (08/11/2026): un modulo per regione o gruppo in `edifici3d/adattatori/`, ognuno con
    una tupla `ADATTATORI`; si aggiungono qui senza toccare questo file."""
    import importlib
    import pkgutil
    from . import adattatori as pacchetto
    for m in sorted(pkgutil.iter_modules(pacchetto.__path__), key=lambda x: x.name):
        modulo = importlib.import_module(f"{pacchetto.__name__}.{m.name}")
        for ad in getattr(modulo, "ADATTATORI", ()):
            ADATTATORI[ad.chiave] = ad


_carica_adattatori_esterni()


# ------------------------------------------------------------------------------------------------ lettura


def leggi_file(percorso: Path, strato: str | None = None) -> tuple[list[tuple[dict, object]], str | None]:
    """(proprietà, geometria shapely con z) e sistema delle coordinate dichiarato dal file (GeoJSON, GPKG, SHP, FGB)."""
    from .uvl import _leggi
    righe, geoms, meta = _leggi(percorso, strato) if strato else _leggi(percorso, None)
    return list(zip(righe, geoms)), meta.get("crs")


def corpi(righe, adattatore: Adattatore | str, crs_uscita: str, crs_file: str | None = None,
          dtm: Path | None = None, riquadro=None) -> tuple[list[Corpo], dict]:
    """Righe del file → corpi nel sistema della zona. `dtm`: GeoTIFF nel sistema della zona (obbligatorio per la
    Liguria, facoltativo per le altre: se c'è, la quota del terreno viene dal DTM). `riquadro` (x0, y0, x1, y1) nel
    sistema della zona: si tengono i corpi che lo toccano."""
    from pyproj import Transformer
    from shapely.geometry import box
    from . import dtm as D
    a = ADATTATORI[adattatore] if isinstance(adattatore, str) else adattatore
    src = crs_file or a.crs_file
    tr = None if _stesso_crs(src, crs_uscita) else Transformer.from_crs(src, crs_uscita, always_xy=True)
    rq = box(*riquadro) if riquadro else None
    out, scarti = [], Counter()
    for p, g in righe:
        p = nomi_completi(p)
        if g is None:
            scarti["senza geometria"] += 1
            continue
        p2, z = _poligono(g)
        if p2 is None or p2.is_empty:
            scarti["geometria non poligonale"] += 1
            continue
        if tr is not None:
            p2 = sh_transform(lambda x, y, zz=None: tr.transform(x, y), p2)
        if rq is not None and not p2.intersects(rq):
            scarti["fuori dal riquadro"] += 1
            continue
        q = None
        if dtm is not None:
            r = D.quota(dtm, p2)
            q = r["minimo"] if r else None
            if r is None:
                scarti["fuori dal DTM"] += 1
        if a.serve_dtm and q is None:
            scarti["manca la quota del terreno (DTM)"] += 1
            continue
        c = a.corpo(p, p2, z, q)
        if c is None:
            scarti["altezza assente o non valida, o elemento escluso"] += 1
            continue
        if dtm is not None and r:
            c.extra["quota_mediana"] = round(r["mediana"], 2)
        out.append(c)
    alt = sorted(c.gronda for c in out)
    res = {"adattatore": a.chiave, "fonte": a.fonte, "licenza": a.licenza, "letti": len(righe), "corpi": len(out),
           "scarti": dict(scarti), "crs_file": src, "crs_uscita": crs_uscita, "dtm": bool(dtm),
           "altezza": {"min": alt[0] if alt else None, "mediana": alt[len(alt) // 2] if alt else None,
                       "max": alt[-1] if alt else None},
           "edifici": len({c.edificio for c in out})}
    return out, res


def _stesso_crs(a: str, b: str) -> bool:
    try:
        from pyproj import CRS
        return CRS.from_user_input(a) == CRS.from_user_input(b)
    except Exception:
        return a == b


def scegli_adattatore(fonte: dict, righe) -> Adattatore:
    """Adattatore della fonte (`adattatore` del TOML) o, se al file mancano i suoi campi, il primo di `alternativi` che li
    trova tutti (08/11/2026: FVG, `fvg_ctrn_ed2` per gli strati ED2 e `fvg_ctrn` per gli ED1 caricati nella coda)."""
    candidati = [fonte["adattatore"], *fonte.get("alternativi", [])]
    campi = {k for p, _ in righe[:2000] for k in nomi_completi(p)}
    for c in candidati:
        a = ADATTATORI[c]
        if all(k in campi for k in a.campi_attesi):
            return a
    return ADATTATORI[candidati[0]]


def controlla(righe, adattatore: Adattatore | str) -> dict:
    """Controllo degli attributi come per le UVL: campi presenti, riempimento, altezze, coerenza delle quote."""
    a = ADATTATORI[adattatore] if isinstance(adattatore, str) else adattatore
    righe = [(nomi_completi(p), g) for p, g in righe]
    prop = [p for p, _ in righe]
    campi = sorted({k for p in prop for k in p})
    pieni = {c: sum(1 for p in prop if not _vuoto(p.get(c))) for c in campi}
    coerenti, z_var = 0, 0
    for p, g in righe:
        if a is LOMBARDIA:
            _, z = _poligono(g) if g is not None else (None, None)
            h, qe = numero(p.get("UN_VOL_AV")), numero(p.get("UN_VOL_QE"))
            if None not in (h, qe, z) and abs(qe - z - h) < 0.05:
                coerenti += 1
        elif a is FVG:
            h, pi, gr = numero(p.get("ALTEZZA")), numero(p.get("QUOTA_PIEDE")), numero(p.get("QUOTA_GRONDA"))
            if None not in (h, pi, gr) and abs(gr - pi - h) < 0.05:
                coerenti += 1
        elif a is LIGURIA and g is not None and _z_variabile(g) > 0.01:
            z_var += 1
    esito = {"adattatore": a.chiave, "oggetti": len(prop), "campi": campi, "pieni": pieni,
             "mancanti": [c for c in a.campi_attesi if c not in campi]}
    if hasattr(a, "coerenza"):                       # adattatori esterni (edifici3d/adattatori/, 08/11/2026)
        esito["coerenza"] = a.coerenza(righe)
    elif a is LOMBARDIA:
        esito["coerenza"] = (f"UN_VOL_QE − z della base = UN_VOL_AV in {coerenti} su {len(prop)} (gli altri: base sotto "
                             "terra, porzione 03; terreno = UN_VOL_QE − UN_VOL_AV)")
    elif a is FVG:
        esito["coerenza"] = f"QUOTA_GRONDA − QUOTA_PIEDE = ALTEZZA in {coerenti} su {len(prop)}"
    elif a is LIGURIA:
        esito["coerenza"] = f"z costante per poligono in {len(prop) - z_var} su {len(prop)} (z = quota di gronda)"
    else:
        esito["coerenza"] = "nessun controllo delle quote per questo adattatore (vedi la sua documentazione)"
    return esito


# ------------------------------------------------------------------------------------------------ campioni dal vivo


def url_campione(fonte: dict, riquadro, crs_riquadro: str, max_oggetti: int, inizio: int = 0) -> str:
    """URL di una pagina del campione: ArcGIS REST (Lombardia) o WFS 2.0.0 (FVG, Liguria). Il riquadro va nel sistema
    del servizio (`crs_servizio` del TOML)."""
    from urllib.parse import urlencode
    x0, y0, x1, y1 = riquadro
    if fonte.get("servizio_tipo") == "arcgis":
        q = {"geometry": f"{x0},{y0},{x1},{y1}", "geometryType": "esriGeometryEnvelope", "inSR": crs_riquadro.split(":")[-1],
             "spatialRel": "esriSpatialRelIntersects", "outFields": "*", "returnZ": "true", "f": "geojson",
             "resultOffset": inizio, "resultRecordCount": max_oggetti, "orderByFields": "OBJECTID"}
        return f"{fonte['servizio'].rstrip('/')}/query?{urlencode(q)}"
    q = {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": fonte["strato"],
         "count": max_oggetti, "startIndex": inizio, "outputFormat": "application/json",
         "bbox": f"{x0},{y0},{x1},{y1},{crs_riquadro}", "srsName": fonte.get("crs_servizio", crs_riquadro)}
    return f"{fonte['servizio']}?{urlencode(q)}"


def scarica_campione(fonte: dict, riquadro, dest: Path, max_oggetti: int = 500, pagina: int = 200,
                     client=None, pausa: float = 1.0) -> dict:
    """Scarica a pagine (al più `max_oggetti`) gli oggetti che toccano il riquadro e scrive un GeoJSON unico. Una
    richiesta alla volta con una pausa tra le pagine; nessun tentativo di aggirare limiti o blocchi: un errore HTTP
    ferma lo scaricamento."""
    import time
    import httpx
    crs = fonte.get("crs_servizio", "EPSG:4326")
    cl = client or httpx.Client(timeout=httpx.Timeout(30, read=120), follow_redirects=True,
                                headers={"User-Agent": "EuGEnio-edifici3d (eugenio.statocritico.it)"})
    feat, crs_file, inizio = [], None, 0
    while len(feat) < max_oggetti:
        n = min(pagina, max_oggetti - len(feat))
        r = cl.get(url_campione(fonte, riquadro, crs, n, inizio))
        r.raise_for_status()
        d = r.json()
        if "error" in d:
            raise RuntimeError(f"servizio: {d['error']}")
        fs = d.get("features") or []
        if crs_file is None and d.get("crs"):
            crs_file = d["crs"].get("properties", {}).get("name")
        feat += fs
        if len(fs) < n:
            break
        inizio += len(fs)
        time.sleep(pausa)
    out = {"type": "FeatureCollection", "features": feat}
    if crs_file:
        out["crs"] = {"type": "name", "properties": {"name": crs_file}}
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return {"oggetti": len(feat), "file": str(dest), "crs_file": crs_file or ("EPSG:4326" if fonte.get("servizio_tipo") == "arcgis" else crs)}


def riproietta_dtm(sorgente: Path, dest: Path, crs: str, passo: float | None = None) -> Path:
    """DTM scaricato nel sistema della Regione (es. Liguria in EPSG:3003) → GeoTIFF float32 nel sistema della zona."""
    import numpy as np
    import rasterio
    from rasterio.warp import calculate_default_transform, reproject, Resampling
    with rasterio.open(sorgente) as src:
        kw = {"resolution": passo} if passo else {}
        t, w, h = calculate_default_transform(src.crs, crs, src.width, src.height, *src.bounds, **kw)
        prof = dict(driver="GTiff", width=w, height=h, count=1, dtype="float32", crs=crs, transform=t, nodata=-9999.0,
                    compress="DEFLATE")
        a = src.read(1).astype("float32")
        if src.nodata is not None:
            a[a == src.nodata] = np.nan
        out = np.full((h, w), np.nan, dtype="float32")
        reproject(a, out, src_transform=src.transform, src_crs=src.crs, dst_transform=t, dst_crs=crs,
                  resampling=Resampling.bilinear, src_nodata=np.nan, dst_nodata=np.nan)
    out[~np.isfinite(out)] = -9999.0
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(dest, "w", **prof) as d:
        d.write(out, 1)
    return Path(dest)
