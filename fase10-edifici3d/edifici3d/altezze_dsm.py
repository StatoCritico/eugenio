"""Altezze degli edifici da DSM − DTM, per sagoma (08/11/2026, lettori regionali, gruppo C).

Modulo comune agli adattatori dei DB topografici **senza altezze** (Bolzano, Sardegna, Campania) o con altezze mancanti
(Trento: 21 % a 0) e al **controllo** delle altezze dei DB che le hanno (Genova, Trento, Lombardia, FVG…).

Misura di una sagoma (`misura`): dentro la sagoma **ridotta di 1 m** (niente bordi: pareti, gronde sporgenti, alberi
accanto) si prendono i pixel del DSM e la differenza pixel per pixel con il DTM (o, se le griglie sono diverse, con la
mediana del DTM dentro la sagoma intera). I pixel sotto 1,5 m (cortili, terreno visibile, sagoma più grande del tetto)
si scartano; la **gronda** è la mediana dei pixel restanti, il **colmo** il 90° percentile, la quota del terreno la
mediana (e il minimo) del DTM dentro la sagoma. Esiti: `ok`; `non_presente` (meno del 30 % dei pixel sopra 1,5 m:
edificio costruito dopo il rilievo, tettoia, demolito); `pochi_pixel` (sagoma troppo piccola per la risoluzione);
`fuori` (nessun pixel valido). La scelta della mediana viene dalle prove dell'08/11/2026 (`documenti/
CITTA_RIFERIMENTO_NORD.md`): a Trento DSM First mediana − DTM contro `MED_ALT` +0,20 m, 96 % entro 2 m su 555 edifici;
a Genova DSM − quota di gronda della CTR −0,11 m, 88 % entro 2 m.

Uso negli archivi (senza toccare `regionali.py` né `__main__.py`): `annota` scrive accanto alle proprietà di ogni sagoma
`dsm_gronda`, `dsm_colmo`, `dsm_quota`, `dsm_quota_min`, `dsm_pixel`, `dsm_alti`, `dsm_esito`, `dsm_fonte` e, per chi
resta senza altezza, `stima_gronda` (mediana dei vicini entro 100 m, almeno 3) in un GeoJSON nuovo; gli adattatori
(`edifici3d/adattatori/trento.py`, `bolzano.py`, `sardegna.py`, `campania.py`) leggono quei campi e `prepara-regione` fa il resto. I rilievi si danno come file
(GeoTIFF, ASCII Grid, zip con un ASCII) o come **fonte a tessere** del TOML della zona (`[fonti.lidar]`: indice WFS
delle tessere con gli URL, o griglia con un URL WCS a riquadro): `annota_da_fonte` scarica una tessera alla volta, misura
le sagome che la toccano, cancella la tessera e tiene per ogni sagoma la misura con più pixel (sagome a cavallo).

Controllo (`confronta`, comando proposto `confronta-dsm`): mediana, MAE e quota entro 2 m (e oltre 5 m) della
differenza (DSM − DTM) − altezza del DB su un file (campo dell'altezza o adattatore della zona) o su un archivio
preparato (celle di contesto, campo `gronda`).

Comando autonomo (finché `confronta-dsm` non entra in `__main__.py`):
  python -m edifici3d.altezze_dsm annota --file sagome.geojson --dsm dsm.tif --dtm dtm.tif --crs-raster EPSG:25832 --uscita s.geojson
  python -m edifici3d.altezze_dsm annota --zona bolzano --file sagome.geojson --uscita s.geojson     # tessere dal TOML
  python -m edifici3d.altezze_dsm confronta --archivio …/cc-by/lig/genova/prodotti --dsm DSM3931.asc --dtm DTM3931.asc --crs-raster EPSG:7791
  python -m edifici3d.altezze_dsm mosaico --file DTM3931.asc DTM3831.asc --crs EPSG:7791 --uscita dtm_genova.tif
"""
from __future__ import annotations

import json
import math
import tempfile
import time
from collections import Counter
from pathlib import Path

import numpy as np

RESTRINGI = 1.0          # m: la sagoma si riduce di tanto prima di leggere il DSM (bordi, pareti, alberi accanto)
SOGLIA_ALTO = 1.5        # m sopra il terreno: sotto, il pixel è terreno o cortile
QUOTA_ALTI_MIN = 0.30    # quota minima di pixel «alti» perché l'edificio risulti presente nel rilievo
PIXEL_MIN = 4            # pixel minimi dentro la sagoma ridotta
PERCENTILE_COLMO = 90
ALTEZZA_MAX = 250.0      # oltre: pixel spurio (gru, antenne, errori) – si scarta
RAGGIO_STIMA = 100.0     # m: vicini per la stima delle sagome senza altezza
MINIMO_STIMA = 3
SOGLIA_ENTRO = 2.0       # m: differenza «buona» nel confronto
SOGLIA_FUORI = 5.0
UA = {"User-Agent": "EuGEnio-edifici3d (eugenio.statocritico.it)"}


# ------------------------------------------------------------------------------------------------ raster


def percorso_raster(p: str | Path) -> str:
    """Percorso leggibile da GDAL: uno zip con dentro un solo raster (.asc/.tif) si apre con /vsizip/."""
    p = str(p)
    if p.lower().endswith(".zip"):
        import zipfile
        with zipfile.ZipFile(p) as z:
            dentro = [n for n in z.namelist() if n.lower().endswith((".asc", ".tif", ".tiff"))]
        if not dentro:
            raise ValueError(f"{p}: nessun raster nello zip")
        return f"/vsizip/{Path(p).resolve()}/{dentro[0]}"
    return p


class Raster:
    """Raster aperto con il sistema dichiarato (gli ASCII Grid di solito non ne hanno uno)."""

    def __init__(self, percorso: str | Path, crs: str | None = None):
        import rasterio
        self.percorso = str(percorso)
        self.ds = rasterio.open(percorso_raster(percorso))
        self.crs = crs or (self.ds.crs.to_string() if self.ds.crs else None)
        if self.crs is None:
            raise ValueError(f"{percorso}: sistema delle coordinate non dichiarato (usa --crs-raster)")
        from shapely.geometry import box
        self.riquadro = box(*self.ds.bounds)

    def leggi(self, geom, all_touched: bool = False):
        """Valori (array con NaN fuori) e trasformazione del ritaglio sulla geometria; (None, None) se fuori."""
        from rasterio.mask import mask
        if not geom.intersects(self.riquadro):
            return None, None
        try:
            a, t = mask(self.ds, [geom.__geo_interface__], crop=True, all_touched=all_touched, filled=False)
        except ValueError:
            return None, None
        v = a[0].astype("float64").filled(np.nan) if hasattr(a[0], "filled") else a[0].astype("float64")
        nd = self.ds.nodata
        if nd is not None:
            v[v == nd] = np.nan
        v[(v < -1000) | (v > 9000)] = np.nan                  # nodata non dichiarati (-9999, 0 ai bordi di certi ASCII)
        return v, t

    def chiudi(self):
        self.ds.close()


def _primo_non_zero(old_data, new_data, old_nodata, new_nodata, **kw):
    """Metodo di `rasterio.merge`: il primo valore valido e diverso da 0 (i DTM 5k della Campania hanno il bordo a 0)."""
    import numpy as _np
    m = _np.logical_and(old_nodata, ~new_nodata) & (new_data != 0)
    old_data[m] = new_data[m]


def mosaico(file: list, dest: Path, crs: str | None = None, passo: float | None = None, zero_vuoto: bool = False) -> Path:
    """Più tessere (GeoTIFF, ASCII, zip) → un GeoTIFF float32 compresso, a tessere, con nodata −9999 (DTM per
    `prepara-regione --dtm`). Le tessere vuote fra aree lontane restano nodata (la compressione le rende leggere).
    `zero_vuoto`: lo 0 esatto è un vuoto (bordo delle tessere ASCII della Campania)."""
    import rasterio
    from rasterio.merge import merge
    srcs = [rasterio.open(percorso_raster(f)) for f in file]
    try:
        kw = {"res": passo} if passo else {}
        if zero_vuoto:
            kw["method"] = _primo_non_zero
        a, t = merge(srcs, nodata=-9999.0, dtype="float32", **kw)
        c = crs or (srcs[0].crs.to_string() if srcs[0].crs else None)
        if c is None:
            raise ValueError("sistema delle coordinate non dichiarato: usa --crs")
        a = a[0].astype("float32")
        a[(a < -1000) | (a > 9000)] = -9999.0
        if zero_vuoto:
            a[a == 0] = -9999.0
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(dest, "w", driver="GTiff", width=a.shape[1], height=a.shape[0], count=1, dtype="float32",
                           crs=c, transform=t, nodata=-9999.0, compress="DEFLATE", predictor=3, tiled=True,
                           blockxsize=512, blockysize=512) as d:
            d.write(a, 1)
    finally:
        for s in srcs:
            s.close()
    return Path(dest)


# ------------------------------------------------------------------------------------------------ misura


def misura(sagoma, dsm: Raster, dtm: Raster, restringi: float = RESTRINGI) -> dict | None:
    """Altezza di gronda e di colmo e quota del terreno di una sagoma (nel sistema dei raster). None se fuori."""
    interna = sagoma.buffer(-restringi) if restringi else sagoma
    if interna.is_empty or interna.area < 1.0:
        interna = sagoma.buffer(-restringi / 2) if restringi else sagoma
        if interna.is_empty or interna.area < 0.5:
            interna = sagoma
    s, ts = dsm.leggi(interna)
    if s is None:
        return None
    t_int, tt = dtm.leggi(interna)
    t_tutta, _ = dtm.leggi(sagoma, all_touched=True)
    tv = t_tutta[np.isfinite(t_tutta)] if t_tutta is not None else np.array([])
    if not tv.size:
        return None
    q_med, q_min = float(np.median(tv)), float(np.min(tv))
    if t_int is not None and t_int.shape == s.shape and tt == ts:
        h = s - t_int                                       # stessa griglia: differenza pixel per pixel (pendii)
        h = np.where(np.isfinite(h), h, s - q_med)
    else:
        h = s - q_med
    h = h[np.isfinite(h)]
    out = {"quota": round(q_med, 2), "quota_min": round(q_min, 2), "pixel": int(h.size)}
    if h.size == 0:
        return {**out, "esito": "fuori"}
    alti = h[(h >= SOGLIA_ALTO) & (h <= ALTEZZA_MAX)]
    out["alti"] = round(float(alti.size) / h.size, 3)
    if h.size < PIXEL_MIN:
        if alti.size:
            out.update(gronda=round(float(np.median(alti)), 2), colmo=round(float(np.max(alti)), 2))
        return {**out, "esito": "pochi_pixel"}
    if alti.size < QUOTA_ALTI_MIN * h.size:
        return {**out, "esito": "non_presente", "massimo": round(float(np.max(h)), 2)}
    out.update(gronda=round(float(np.median(alti)), 2), colmo=round(float(np.percentile(alti, PERCENTILE_COLMO)), 2),
               p10=round(float(np.percentile(alti, 10)), 2), esito="ok")
    return out


def _migliore(a: dict | None, b: dict | None) -> dict | None:
    if a is None:
        return b
    if b is None:
        return a
    return b if b.get("pixel", 0) > a.get("pixel", 0) else a


def _trasformatore(da: str | None, a: str):
    from pyproj import CRS, Transformer
    if not da:
        return None
    try:
        if CRS.from_user_input(da) == CRS.from_user_input(a):
            return None
    except Exception:   # noqa: BLE001
        return None
    tr = Transformer.from_crs(da, a, always_xy=True)
    return lambda x, y, z=None: tr.transform(x, y)


def misura_coppie(sagome: list, coppie: list, crs_sagome: str | None = None, misure: dict | None = None) -> dict:
    """`sagome`: lista di (chiave, poligono 2D nel sistema `crs_sagome`); `coppie`: lista di (Raster DSM, Raster DTM)
    nello stesso sistema. Per ogni chiave la misura con più pixel tra le coppie che la toccano."""
    from shapely.ops import transform
    from shapely.strtree import STRtree
    misure = {} if misure is None else misure
    if not sagome or not coppie:
        return misure
    crs_r = coppie[0][0].crs
    f = _trasformatore(crs_sagome, crs_r)
    geoms = [transform(f, g) if f else g for _, g in sagome]
    albero = STRtree(geoms)
    for dsm, dtm in coppie:
        for i in albero.query(dsm.riquadro):
            k = sagome[int(i)][0]
            misure[k] = _migliore(misure.get(k), misura(geoms[int(i)], dsm, dtm))
    return misure


def accoppia(dsm_file: list, dtm_file: list, crs: str | None = None) -> list:
    """Apre DSM e DTM e li accoppia per sovrapposizione dei riquadri (stessa tessera; un DTM unico va con tutti)."""
    dsm = [Raster(p, crs) for p in dsm_file]
    dtm = [Raster(p, crs) for p in dtm_file]
    coppie = []
    for s in dsm:
        cand = [(t.riquadro.intersection(s.riquadro).area, t) for t in dtm if t.riquadro.intersects(s.riquadro)]
        if cand:
            coppie.append((s, max(cand, key=lambda x: x[0])[1]))
    return coppie


# ------------------------------------------------------------------------------------------------ fonti a tessere


def tessere_da_fonte(fonte: dict, riquadro, crs_riquadro: str, client=None) -> list[dict]:
    """Tessere di una fonte LiDAR del TOML che toccano il riquadro: [{nome, dsm, dtm, riquadro}] con gli URL.

    Due modi: `indice_wfs` + `indice_strato` (+ `indice_crs`, `campo_nome`): quadro d'unione WFS con i campi usati nei
    modelli `url_dsm`/`url_dtm` (es. «…/{n_tavola}_DTM.asc», «{dsm_buildi}»); `griglia` (lato in m) + `url_dsm`/
    `url_dtm` con {x0},{y0},{x1},{y1}: un servizio WCS chiesto a riquadri (es. Bolzano)."""
    import httpx
    from pyproj import Transformer
    x0, y0, x1, y1 = riquadro
    if fonte.get("griglia"):
        lato = float(fonte["griglia"])
        tr = Transformer.from_crs(crs_riquadro, fonte["crs"], always_xy=True) if crs_riquadro != fonte["crs"] else None
        if tr:
            xs, ys = tr.transform([x0, x1, x0, x1], [y0, y0, y1, y1])
            x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        out = []
        for e in range(int(math.floor(x0 / lato)), int(math.floor(x1 / lato)) + 1):
            for n in range(int(math.floor(y0 / lato)), int(math.floor(y1 / lato)) + 1):
                q = dict(x0=e * lato, y0=n * lato, x1=(e + 1) * lato, y1=(n + 1) * lato)
                q = {k: (int(v) if float(v).is_integer() else v) for k, v in q.items()}
                from shapely.geometry import box
                out.append({"nome": f"{q['x0']}_{q['y0']}", "dsm": fonte["url_dsm"].format(**q),
                            "dtm": fonte["url_dtm"].format(**q), "riquadro": [q["x0"], q["y0"], q["x1"], q["y1"]],
                            "geom": box(q["x0"], q["y0"], q["x1"], q["y1"]), "crs": fonte["crs"]})
        return out
    crs_i = fonte.get("indice_crs", crs_riquadro)
    if crs_i != crs_riquadro:
        tr = Transformer.from_crs(crs_riquadro, crs_i, always_xy=True)
        xs, ys = tr.transform([x0, x1, x0, x1], [y0, y0, y1, y1])
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    from urllib.parse import urlencode
    q = {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": fonte["indice_strato"],
         "outputFormat": "application/json", "count": 5000, "bbox": f"{x0},{y0},{x1},{y1},{crs_i}"}
    cl = client or httpx.Client(timeout=httpx.Timeout(30, read=120), follow_redirects=True, headers=UA)
    r = cl.get(f"{fonte['indice_wfs']}?{urlencode(q)}")
    r.raise_for_status()
    out = []
    for f in r.json().get("features", []):
        p = f.get("properties") or {}
        from shapely.geometry import shape
        out.append({"nome": str(p.get(fonte.get("campo_nome", "nome"))), "dsm": fonte["url_dsm"].format(**p),
                    "dtm": fonte["url_dtm"].format(**p), "crs": crs_i,
                    "geom": shape(f["geometry"]) if f.get("geometry") else None})
    return out


def _scarica(url: str, dest: Path, client) -> Path:
    with client.stream("GET", url) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for b in r.iter_bytes(1 << 20):
                f.write(b)
    return dest


def _estensione(url: str, predefinita: str = ".tif") -> str:
    u = url.split("?")[0].lower()
    for e in (".zip", ".asc", ".tif", ".tiff"):
        if u.endswith(e):
            return e
    return predefinita


def annota_da_fonte(sagome: list, fonte: dict, crs_sagome: str, client=None, cartella: Path | None = None,
                    pausa: float = 0.5, tieni: bool = False, avanzamento=None) -> tuple[dict, dict]:
    """Scarica le tessere della fonte che toccano le sagome (una alla volta, con una pausa; un errore HTTP la salta e
    si annota), misura e cancella. Restituisce (misure per chiave, resoconto)."""
    import httpx
    from shapely.ops import unary_union, transform
    cl = client or httpx.Client(timeout=httpx.Timeout(30, read=300), follow_redirects=True, headers=UA)
    if not sagome:
        return {}, {"tessere": 0}
    tutte = unary_union([g.envelope for _, g in sagome])
    tessere = tessere_da_fonte(fonte, tutte.bounds, crs_sagome, cl)
    if tessere and all(t.get("geom") is not None for t in tessere):   # solo le tessere che toccano una sagoma
        from shapely.strtree import STRtree
        f_t = _trasformatore(crs_sagome, tessere[0]["crs"])
        al = STRtree([transform(f_t, g) if f_t else g for _, g in sagome])
        tessere = [t for t in tessere if len(al.query(t["geom"], predicate="intersects"))]
    misure, errori, mb = {}, [], 0.0
    tmp = Path(cartella or tempfile.mkdtemp(prefix="dsm_"))
    tmp.mkdir(parents=True, exist_ok=True)
    for i, t in enumerate(tessere):
        fs = tmp / f"{t['nome']}_dsm{_estensione(t['dsm'])}"
        ft = tmp / f"{t['nome']}_dtm{_estensione(t['dtm'])}"
        try:
            for u, d in ((t["dsm"], fs), (t["dtm"], ft)):
                if not d.exists():
                    _scarica(u, d, cl)
                    time.sleep(pausa)
            mb += (fs.stat().st_size + ft.stat().st_size) / 1e6
            coppia = (Raster(fs, fonte["crs"]), Raster(ft, fonte["crs"]))
            misura_coppie(sagome, [coppia], crs_sagome, misure)
            coppia[0].chiudi(), coppia[1].chiudi()
        except Exception as e:   # noqa: BLE001 - una tessera che manca non ferma le altre
            errori.append(f"{t['nome']}: {e}")
        finally:
            if not tieni:
                fs.unlink(missing_ok=True), ft.unlink(missing_ok=True)
        if avanzamento:
            avanzamento(i + 1, len(tessere), t["nome"])
    return misure, {"tessere": len(tessere), "mb_scaricati": round(mb, 1), "errori": errori}


# ------------------------------------------------------------------------------------------------ annota


def _altezza_db(p: dict, campo: str | None):
    if not campo:
        return None
    try:
        v = float(p.get(campo))
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def stima_vicini(centri: list, altezze: list, raggio: float = RAGGIO_STIMA, minimo: int = MINIMO_STIMA) -> list:
    """Per ogni centro senza altezza (None) la mediana delle altezze note entro `raggio`, al mezzo metro, o None."""
    from shapely.strtree import STRtree
    from shapely.geometry import Point
    note = [(c, h) for c, h in zip(centri, altezze) if h is not None]
    if not note:
        return [None] * len(centri)
    al = STRtree([Point(c) for c, _ in note])
    out = []
    for c, h in zip(centri, altezze):
        if h is not None:
            out.append(None)
            continue
        vic = [note[int(j)][1] for j in al.query(Point(c).buffer(raggio))]
        out.append(round(float(np.median(vic)) * 2) / 2 if len(vic) >= minimo else None)
    return out


def annota(righe: list, misure_fn, crs_file: str, campo_altezza: str | None = None, solo_senza: bool = False,
           etichetta: str = "DSM − DTM", confine=None) -> tuple[list, dict]:
    """Righe (proprietà, geometria) → righe con i campi `dsm_*` e `stima_gronda`. `misure_fn(sagome)` → misure (es.
    `lambda s: misura_coppie(s, coppie, crs_file)` o `annota_da_fonte`). `solo_senza`: si misurano solo le sagome
    senza altezza nel DB (`campo_altezza` ≤ 0 o vuoto: Trento). `confine`: poligono nel sistema del file: si tengono le
    sagome con il punto interno dentro."""
    from .regionali import _poligono, nomi_completi
    tenute, sagome = [], []
    for p, g in righe:
        p = nomi_completi(dict(p))
        if g is None:
            continue
        p2, _ = _poligono(g)
        if p2 is None or p2.is_empty:
            continue
        if confine is not None and not confine.contains(p2.representative_point()):
            continue
        k = len(tenute)
        tenute.append((p, g, p2))
        if not solo_senza or _altezza_db(p, campo_altezza) is None:
            sagome.append((k, p2))
    ris = misure_fn(sagome)
    misure, resoconto = ris if isinstance(ris, tuple) else (ris, {})
    esiti = Counter()
    for k, (p, g, p2) in enumerate(tenute):
        m = misure.get(k)
        if m is None:
            esiti["non misurata" if not solo_senza or _altezza_db(p, campo_altezza) is None else "altezza dal DB"] += 1
            continue
        esiti[m["esito"]] += 1
        p.update({"dsm_esito": m["esito"], "dsm_pixel": m["pixel"], "dsm_quota": m["quota"],
                  "dsm_quota_min": m["quota_min"], "dsm_alti": m.get("alti"), "dsm_fonte": etichetta})
        if m.get("gronda") is not None and m["esito"] in ("ok", "pochi_pixel"):
            p.update(dsm_gronda=m["gronda"], dsm_colmo=m.get("colmo"))
    # stima per chi resta senza altezza (né dal DB né dal DSM): mediana dei vicini
    centri = [(p2.centroid.x, p2.centroid.y) for _, _, p2 in tenute]
    alt = [(_altezza_db(p, campo_altezza) or p.get("dsm_gronda")) for p, _, _ in tenute]
    stime = stima_vicini(centri, alt)
    n_stime = 0
    for (p, _, _), s in zip(tenute, stime):
        if s is not None:
            p["stima_gronda"] = s
            n_stime += 1
    out = [(p, g) for p, g, _ in tenute]
    return out, {"sagome": len(tenute), "misurate": len(sagome), "esiti": dict(esiti), "stime_vicini": n_stime,
                 "crs_file": crs_file, **resoconto}


def leggi_righe(percorso: Path, riquadro=None) -> list:
    """(proprietà, geometria shapely) di un file; GeoJSON letto direttamente (i GeoJSON dei WFS hanno proprietà a lista,
    come `bbox`, che il lettore comune non converte: si tolgono), gli altri formati con pyogrio e il solo `riquadro`
    (lo Shapefile della provincia di Trento ha 147.481 edifici)."""
    from shapely.geometry import shape, box
    percorso = Path(percorso)
    if percorso.suffix.lower() in (".json", ".geojson"):
        d = json.loads(percorso.read_text(encoding="utf-8"))
        rq = box(*riquadro) if riquadro else None
        out = []
        for f in d.get("features", []):
            if not f.get("geometry"):
                continue
            g = shape(f["geometry"])
            if rq is not None and not g.intersects(rq):
                continue
            p = {k: v for k, v in (f.get("properties") or {}).items() if not isinstance(v, (list, dict))}
            if f.get("id") is not None and "id" not in p:
                p["id"] = f["id"]
            out.append((p, g))
        return out
    from .uvl import _leggi
    rr, gg, _ = _leggi(str(percorso), None, riquadro)
    return list(zip(rr, gg))


def scrivi_geojson(righe: list, dest: Path, crs: str | None = None) -> Path:
    from shapely.geometry import mapping

    def pulito(v):
        if hasattr(v, "item"):
            v = v.item()
        if isinstance(v, float) and not math.isfinite(v):
            return None
        return v
    fs = [{"type": "Feature", "geometry": mapping(g),
           "properties": {k: pulito(v) for k, v in p.items() if not isinstance(v, (list, dict))}} for p, g in righe]
    d = {"type": "FeatureCollection", "features": fs}
    if crs:
        d["crs"] = {"type": "name", "properties": {"name": crs}}
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return dest


# ------------------------------------------------------------------------------------------------ per gli adattatori

ALTEZZA_PICCOLI = 3.0    # m: baracche, tettoie, serre, cabine senza altezza


def gronda_da_campi(p: dict, uso: str | None = None, piccolo: bool = False, rilievo: str = "") -> dict:
    """Gronda di una sagoma dai campi scritti da `annota`: DSM − DTM («ok» o «pochi_pixel»), poi la mediana dei vicini
    (`stima_gronda`), poi una stima dall'uso (`plausibilita.stima_uso`: 6–9 m; 3 m per i manufatti piccoli). Sempre
    con la fonte dichiarata: {gronda, fonte, qualita, origine, extra}."""
    from .plausibilita import stima_uso
    g = p.get("dsm_gronda")
    es = p.get("dsm_esito")
    extra = {k: p[k] for k in ("dsm_esito", "dsm_pixel", "dsm_colmo", "dsm_quota") if p.get(k) is not None}
    if g is not None and es == "ok" and p.get("ua_classe"):      # Copernicus UA Building Height (altezze_ua.py, 08/11/2026)
        extra["altezza_classe_ua"] = p["ua_classe"]
        return {"gronda": round(float(g), 2), "fonte": f"{p.get('dsm_fonte')}, {int(float(p.get('dsm_pixel') or 0))} pixel)", "origine": "ua",
                "extra": extra, "qualita": f"classe di altezza Copernicus UA 2012 ({p['ua_classe']}), rielaborata"}
    if g is not None and es in ("ok", "pochi_pixel") and float(g) >= SOGLIA_ALTO:
        fonte = (f"{p.get('dsm_fonte') or 'DSM − DTM'}: mediana dei pixel dentro la sagoma ridotta di 1 m "
                 f"({p.get('dsm_pixel')} pixel{', pochi' if es == 'pochi_pixel' else ''})")
        return {"gronda": round(float(g), 2), "fonte": fonte, "origine": "dsm", "extra": extra,
                "qualita": "altezza da DSM − DTM, ±1 m" + (" (sagoma piccola)" if es == "pochi_pixel" else "")}
    perche = {"non_presente": f"non presente nel rilievo{(' ' + rilievo) if rilievo else ''} (costruito dopo o tettoia)",
              "fuori": "fuori dal rilievo", "pochi_pixel": "sagoma troppo piccola per il rilievo"}.get(es, "fuori dal rilievo")
    if p.get("stima_gronda") is not None and not piccolo:
        h = float(p["stima_gronda"])
        return {"gronda": h, "fonte": f"stima: mediana dei vicini entro {RAGGIO_STIMA:g} m ({h:g} m); {perche}",
                "origine": "vicini", "qualita": "altezza stimata", "extra": {**extra, "stima_altezza": "vicini"}}
    h = ALTEZZA_PICCOLI if piccolo else stima_uso(uso)
    return {"gronda": h, "fonte": f"stima: {'manufatto piccolo' if piccolo else 'uso'} ({h:g} m); {perche}",
            "origine": "uso", "qualita": "altezza stimata", "extra": {**extra, "stima_altezza": "uso"}}


def quota_corpo(p: dict, quota_dtm: float | None, quota_db: float | None = None) -> float | None:
    """Quota del terreno: DTM passato a prepara-regione, poi quella del DB, poi la mediana del DTM del rilievo."""
    for q in (quota_dtm, quota_db, p.get("dsm_quota")):
        try:
            if q is not None and math.isfinite(float(q)) and float(q) > -100:
                return float(q)
        except (TypeError, ValueError):
            continue
    return None


# ------------------------------------------------------------------------------------------------ confronto


def statistiche(differenze, soglia: float = SOGLIA_ENTRO) -> dict:
    d = np.asarray([x for x in differenze if x is not None and math.isfinite(x)], dtype="float64")
    if not d.size:
        return {"n": 0}
    return {"n": int(d.size), "mediana": round(float(np.median(d)), 2), "mae": round(float(np.mean(np.abs(d))), 2),
            "entro_2m": round(float(np.mean(np.abs(d) < soglia)), 3),
            "oltre_5m": round(float(np.mean(np.abs(d) > SOGLIA_FUORI)), 3),
            "p10": round(float(np.percentile(d, 10)), 2), "p90": round(float(np.percentile(d, 90)), 2)}


def confronta(voci: list, coppie: list, crs_voci: str, area_min: float = 30.0, peggiori: int = 10) -> dict:
    """`voci`: lista di (id, poligono, altezza del DB) nel sistema `crs_voci`. Confronto con DSM − DTM (mediana dei
    pixel alti dentro la sagoma ridotta di 1 m), solo sagome di almeno `area_min` m² con misura «ok»."""
    sag = [(i, g) for i, (k, g, h) in enumerate(voci) if h is not None and g.area >= area_min]
    mis = misura_coppie(sag, coppie, crs_voci)
    righe = []
    esiti = Counter()
    for i, (k, g, h) in enumerate(voci):
        m = mis.get(i)
        if m is None:
            continue
        esiti[m["esito"]] += 1
        if m["esito"] == "ok":
            righe.append({"id": k, "area": round(g.area, 1), "h_db": round(h, 2), "h_dsm": m["gronda"],
                          "colmo_dsm": m["colmo"], "differenza": round(m["gronda"] - h, 2)})
    st = statistiche([r["differenza"] for r in righe])
    righe.sort(key=lambda r: -abs(r["differenza"]))
    return {"voci": len(voci), "misurate": sum(esiti.values()), "esiti": dict(esiti),
            "dsm_meno_db": st, "peggiori": righe[:peggiori], "_righe": righe}


def voci_da_archivio(prodotti: Path, crs: str) -> list:
    """Corpi delle celle di contesto di un archivio preparato (WGS84) → (id, poligono nel sistema `crs`, gronda)."""
    from shapely.geometry import shape
    from shapely.ops import transform
    f = _trasformatore("EPSG:4326", crs)
    visti, out = set(), []
    for c in sorted((Path(prodotti) / "contesto").glob("*.json")):
        for x in json.loads(c.read_text(encoding="utf-8"))["features"]:
            p = x.get("properties") or {}
            if p.get("id") in visti:
                continue
            visti.add(p.get("id"))
            g = shape(x["geometry"])
            out.append((p.get("id"), transform(f, g) if f else g, float(p["gronda"]) if p.get("gronda") is not None else None))
    return out


def voci_da_file(righe: list, crs_file: str, campo: str | None = None, adattatore=None, crs_uscita: str | None = None,
                 dtm: Path | None = None) -> tuple[list, str]:
    """Righe di un file → voci per il confronto: con `campo` l'altezza è quel campo (> 0); con un adattatore si
    costruiscono i corpi (con `dtm` se serve, es. Liguria) e l'altezza è la gronda del corpo."""
    from .regionali import _poligono, corpi as R_corpi
    if adattatore is not None:
        cs, _ = R_corpi(righe, adattatore, crs_uscita or crs_file, crs_file, dtm)
        return [(c.id, c.sagoma, c.gronda) for c in cs], crs_uscita or crs_file
    out = []
    for i, (p, g) in enumerate(righe):
        p2, _ = _poligono(g) if g is not None else (None, None)
        if p2 is None:
            continue
        out.append((p.get("id") or p.get("ID") or i, p2, _altezza_db(p, campo)))
    return out, crs_file


def confronta_dsm(dsm: list, dtm: list, crs_raster: str | None = None, archivio: Path | None = None,
                  file: Path | None = None, campo: str | None = None, adattatore=None, crs_file: str | None = None,
                  crs_zona: str | None = None, dtm_quota: Path | None = None, area_min: float = 30.0) -> dict:
    """Funzione del comando `confronta-dsm`: archivio preparato (`archivio` = cartella `prodotti`) o file (con `campo`
    o con l'adattatore della zona). Restituisce il resoconto senza l'elenco completo."""
    coppie = accoppia(dsm, dtm, crs_raster)
    if not coppie:
        raise ValueError("nessuna coppia DSM/DTM sovrapposta")
    crs_r = coppie[0][0].crs
    if archivio is not None:
        voci, crs_v = voci_da_archivio(archivio, crs_r), crs_r
    else:
        import pyogrio
        crs_letto = pyogrio.read_info(str(file)).get("crs")
        righe = leggi_righe(Path(file))
        voci, crs_v = voci_da_file(righe, crs_file or crs_letto or crs_r, campo, adattatore, crs_zona, dtm_quota)
    from shapely.ops import unary_union
    tutte = unary_union([c[0].riquadro for c in coppie])
    f = _trasformatore(crs_v, crs_r)
    from shapely.ops import transform
    voci = [v for v in voci if (transform(f, v[1]) if f else v[1]).within(tutte)]
    r = confronta(voci, coppie, crs_v, area_min)
    r.pop("_righe", None)
    r["dsm"] = [c[0].percorso for c in coppie]
    for s, t in coppie:
        s.chiudi(), t.chiudi()
    return r


# ------------------------------------------------------------------------------------------------ comando autonomo


def fonte_lidar(zona: str) -> tuple[dict, dict]:
    """[fonti.lidar] del TOML della zona (fonti/<zona>.toml) e la zona."""
    from . import fonti as F
    z = F.carica_zona(zona)
    f = (z.get("fonti") or {}).get("lidar")
    if not f:
        raise SystemExit(f"fonti/{zona}.toml: manca [fonti.lidar]")
    return dict(f), z


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m edifici3d.altezze_dsm", description=__doc__.split("\n")[0])
    ap.add_argument("--zona", help="fonti/<zona>.toml: [fonti.lidar] per le tessere, adattatore per il confronto")
    sub = ap.add_subparsers(dest="cmd", required=True)
    an = sub.add_parser("annota", help="sagome → GeoJSON con dsm_gronda, dsm_quota, … e stima_gronda")
    an.add_argument("--file", type=Path, required=True); an.add_argument("--uscita", type=Path, required=True)
    an.add_argument("--dsm", nargs="*", default=[]); an.add_argument("--dtm", nargs="*", default=[])
    an.add_argument("--crs-raster"); an.add_argument("--crs-file")
    an.add_argument("--campo-altezza", help="campo dell'altezza del DB (per --solo-senza e per la stima dei vicini)")
    an.add_argument("--solo-senza", action="store_true", help="misura solo le sagome senza altezza nel DB")
    an.add_argument("--confine", type=Path, help="GeoJSON del confine (nel sistema del file o in WGS84 se dichiarato)")
    an.add_argument("--riquadro", nargs=4, type=float, help="x0 y0 x1 y1 nel sistema del file")
    an.add_argument("--tieni", action="store_true", help="non cancellare le tessere scaricate")
    an.add_argument("--cartella", type=Path, help="cartella delle tessere scaricate")
    mo = sub.add_parser("mosaico", help="tessere (ASCII, GeoTIFF, zip) → un GeoTIFF (DTM per prepara-regione)")
    mo.add_argument("--file", nargs="+", required=True); mo.add_argument("--uscita", type=Path, required=True)
    mo.add_argument("--crs"); mo.add_argument("--passo", type=float)
    mo.add_argument("--zero-vuoto", action="store_true", help="lo 0 esatto è un vuoto (bordi dei DTM 5k della Campania)")
    co = sub.add_parser("confronta", help="altezze del DB o di un archivio contro DSM − DTM")
    co.add_argument("--dsm", nargs="+", required=True); co.add_argument("--dtm", nargs="+", required=True)
    co.add_argument("--crs-raster"); co.add_argument("--archivio", type=Path, help="cartella prodotti di un archivio")
    co.add_argument("--file", type=Path); co.add_argument("--campo"); co.add_argument("--crs-file")
    co.add_argument("--dtm-quota", type=Path, help="DTM nel sistema della zona per l'adattatore (Liguria)")
    co.add_argument("--area-min", type=float, default=30.0)
    a = ap.parse_args(argv)
    if a.cmd == "mosaico":
        fs = []
        for f in a.file:                                   # uno zip con più ASCII: tutte le tessere dentro
            if str(f).lower().endswith(".zip"):
                import zipfile
                with zipfile.ZipFile(f) as z:
                    fs += [f"/vsizip/{Path(f).resolve()}/{n}" for n in z.namelist() if n.lower().endswith((".asc", ".tif"))]
            else:
                fs.append(f)
        print(mosaico(fs, a.uscita, a.crs, a.passo, a.zero_vuoto))
        return 0
    if a.cmd == "confronta":
        ad, crs_zona = None, None
        if a.file and not a.campo and a.zona:
            from . import regionali as R
            from . import fonti as F
            z = F.carica_zona(a.zona)
            ad, crs_zona = R.ADATTATORI[z["fonti"]["edifici"]["adattatore"]], z["zona"]["crs"]
        r = confronta_dsm(a.dsm, a.dtm, a.crs_raster, a.archivio, a.file, a.campo, ad, a.crs_file, crs_zona,
                          a.dtm_quota, a.area_min)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    from shapely.geometry import box, shape
    import pyogrio
    crs_file = a.crs_file or pyogrio.read_info(str(a.file)).get("crs")
    if not crs_file:
        raise SystemExit("--crs-file: il file non dichiara il sistema")
    confine = None
    if a.confine:
        d = json.loads(a.confine.read_text(encoding="utf-8"))
        from shapely.ops import unary_union, transform
        confine = unary_union([shape(f["geometry"]) for f in d.get("features", [d])])
        crs_c = (d.get("crs") or {}).get("properties", {}).get("name", "EPSG:4326")
        fc = _trasformatore(crs_c, crs_file)
        confine = transform(fc, confine) if fc else confine
    if a.riquadro:
        confine = box(*a.riquadro) if confine is None else confine.intersection(box(*a.riquadro))
    righe = leggi_righe(a.file, confine.bounds if confine is not None else None)
    if a.dsm:
        coppie = accoppia(a.dsm, a.dtm, a.crs_raster)
        fn = lambda s: misura_coppie(s, coppie, crs_file)                       # noqa: E731
        etichetta = "DSM − DTM (" + ", ".join(Path(c[0].percorso).name for c in coppie[:4]) + ")"
    else:
        fonte, _ = fonte_lidar(a.zona)
        etichetta = fonte.get("attribuzione") or fonte.get("descrizione") or "DSM − DTM"

        def fn(s):
            return annota_da_fonte(s, fonte, crs_file, cartella=a.cartella, tieni=a.tieni,
                                   avanzamento=lambda i, n, t: print(f"  tessera {i}/{n} {t}", flush=True) if i % 10 == 0 or i == n else None)
    out, res = annota(righe, fn, crs_file, a.campo_altezza, a.solo_senza, etichetta, confine)
    scrivi_geojson(out, a.uscita, crs_file)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
