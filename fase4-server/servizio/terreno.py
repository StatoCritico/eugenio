"""Tessere del terreno su richiesta per la pagina 3D (decisione di Paolo del 07/11/2026).

Il DTM **non va più negli archivi dei comuni** (prima: `terreno.pmtiles` e `dtm_cog.tif` in ogni archivio, fino a 170 MB
per i comuni montani). Il server tiene il DTM 5 m come COG unico per quadrante in `CARTELLA_TERRENO` (/dati/terreno,
cioè /srv/energia/dati/terreno), convertito **una volta** dallo zip della Regione con il comando della fase 10
`dtm-server` (scrive `<nome>.tif` e `<nome>.json` con sistema, riquadro, licenza e attribuzione), e genera le tessere
Terrarium **solo dove qualcuno apre il 3D**.

Rotte:
  GET /api/terreno/{z}/{x}/{y}.png   tessera 256×256 Terrarium (web mercator, numerazione XYZ), zoom TERRENO_ZOOM_MIN–15
  GET /api/terreno/fonti             DTM disponibili (riquadro, licenza, attribuzione) e ripiego

Regole:
  * **letture a finestra** dal COG (rasterio): per gli zoom bassi si apre la panoramica giusta (5 m · 2^k ≤ pixel della
    tessera), quindi una tessera costa al più ~1 MB di lettura;
  * fuori dai DTM regionali (o dove hanno vuoti, mare compreso) **ripiego sul Copernicus DEM GLO-90** già usato per
    l'orizzonte lontano (orizzonte.py); se anche quello non risponde, **tessera piatta** a 0 m dichiarata
    (`X-Terreno-Fonte: piatta`, nessuna copia, Cache-Control breve); fuori dall'Italia 404 (MapLibre la ignora);
  * **copia su disco** (CARTELLA_TERRENO_TESSERE/<versione>/<z>/<x>/<y>.png, versione = impronta dei DTM presenti: un
    DTM nuovo non mescola tessere vecchie) con tetto TERRENO_MAX_GB e pulizia delle più vecchie (come le ortofoto);
  * **limiti**: le tessere già in copia contano solo nel tetto anti-abuso «tessere_copia» (TESSERE_COPIA_ORA, 09/11/2026);
    quelle da generare TERRENO_ORA all'ora per IP (tipo «terreno» di protezione.py) e al più TERRENO_PARALLELE generate
    insieme (CPU del server);
  * **intestazioni**: Cache-Control public TERRENO_CACHE_S (30 giorni, anche Cloudflare), ETag, X-Terreno-Fonte
    («dtm», «dtm+copernicus», «copernicus», «piatta»), X-Terreno-Licenza;
  * TERRENO_ATTIVO=false spegne la rotta (404): la pagina mostra la mappa piatta, quote dei corpi e ombre non cambiano
    (le quote sono scritte nei corpi da `prepara`).
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import math
import os
import threading
import time
from pathlib import Path

import numpy as np
from fastapi import APIRouter, HTTPException, Request, Response

from . import config as C, protezione as P

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/terreno")

ZOOM_MAX = 15
R_TERRA = 20037508.342789244
ITALIA = (6.0, 35.0, 19.0, 47.5)
COPERNICUS = ("Copernicus DEM GLO-90 (© DLR e Airbus, licenza Copernicus DEM), dai file di Open-Meteo.com (CC BY 4.0)")
LICENZA_COPERNICUS = "licenza Copernicus DEM"


# ---------------------------------------------------------------------------------------------- geometria
def limiti_tessera(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    t = 2 * R_TERRA / 2 ** z
    return -R_TERRA + x * t, R_TERRA - (y + 1) * t, -R_TERRA + (x + 1) * t, R_TERRA - y * t


def lonlat_tessera(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    n = 2 ** z
    lon = lambda i: i / n * 360 - 180
    lat = lambda j: math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * j / n))))
    return lon(x), lat(y + 1), lon(x + 1), lat(y)


def centri_pixel(z: int, x: int, y: int, n: int = 256) -> tuple[np.ndarray, np.ndarray]:
    """lon, lat (gradi) dei centri dei pixel della tessera (n×n), righe dall'alto."""
    w, s, e, nn = limiti_tessera(z, x, y)
    passo = (e - w) / n
    mx = w + (np.arange(n) + 0.5) * passo
    my = nn - (np.arange(n) + 0.5) * passo
    lon = np.degrees(mx / 6378137.0)
    lat = np.degrees(2 * np.arctan(np.exp(my / 6378137.0)) - math.pi / 2)
    return np.broadcast_to(lon, (n, n)), np.broadcast_to(lat[:, None], (n, n))


# ---------------------------------------------------------------------------------------------- Terrarium
def codifica(zq: np.ndarray) -> np.ndarray:
    v = np.nan_to_num(zq.astype("float64"), nan=0.0) + 32768.0
    r = np.floor(v / 256.0)
    g = np.floor(v - r * 256.0)
    b = np.floor((v - r * 256.0 - g) * 256.0)
    return np.clip(np.stack([r, g, b], axis=-1), 0, 255).astype("uint8")


def decodifica(rgb: np.ndarray) -> np.ndarray:
    rgb = rgb.astype("float64")
    return rgb[..., 0] * 256.0 + rgb[..., 1] + rgb[..., 2] / 256.0 - 32768.0


def png(rgb: np.ndarray) -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.fromarray(rgb, "RGB").save(b, format="PNG", optimize=True)
    return b.getvalue()


# ---------------------------------------------------------------------------------------------- DTM del server
_dtm_cache: tuple[float, list[dict]] | None = None
_blocco = threading.Lock()


def dtm_disponibili(ricarica: bool = False) -> list[dict]:
    """Schede dei DTM in CARTELLA_TERRENO (<nome>.tif con <nome>.json di `dtm-server`); rilette ogni 5 minuti."""
    global _dtm_cache
    with _blocco:
        if not ricarica and _dtm_cache and time.time() - _dtm_cache[0] < 300:
            return _dtm_cache[1]
        out = []
        cartella = C.CARTELLA_TERRENO
        for j in sorted(cartella.glob("*.json")) if cartella.exists() else []:
            tif = j.with_suffix(".tif")
            if not tif.is_file():
                continue
            try:
                d = json.loads(j.read_text(encoding="utf-8"))
                d["percorso"] = str(tif)
                d["impronta"] = f"{tif.name}:{tif.stat().st_size}:{int(tif.stat().st_mtime)}"
                if len(d.get("riquadro_wgs84", [])) == 4:
                    out.append(d)
            except (OSError, ValueError) as e:
                log.warning("Terreno: scheda %s scartata (%s)", j.name, e)
        # più DTM insieme (08/11/2026: Emilia-Romagna, Veneto, …): per ogni tessera prima il più dettagliato
        out.sort(key=lambda d: (min((abs(float(v)) for v in d.get("passo_m") or [999]), default=999), d.get("file", "")))
        _dtm_cache = (time.time(), out)
        return out


def quote_copernicus(punti: list[tuple[float, float]]) -> list[float | None]:
    """(09/11/2026 b) Quote del Copernicus DEM 90 m nei punti WGS84 (le stesse delle tessere del terreno fuori dai DTM
    regionali): una finestra sola attorno ai punti, bilineare; None se il DEM non risponde."""
    if not punti:
        return []
    from . import orizzonte as O
    lon0, lon1 = min(p[0] for p in punti), max(p[0] for p in punti)
    lat0, lat1 = min(p[1] for p in punti), max(p[1] for p in punti)
    clat, clon = (lat0 + lat1) / 2, (lon0 + lon1) / 2
    raggio = max((lat1 - lat0) / 2 * 111000.0, (lon1 - lon0) / 2 * 111320.0 * math.cos(math.radians(clat))) + 200
    if raggio > 5000 and len(punti) > 1:                # punti lontani tra loro: una finestra piccola per ognuno
        return [q for p in punti for q in quote_copernicus([p])]
    try:
        g, la0, lo0 = O.finestra_dem(clat, clon, raggio)
    except Exception as e:                              # noqa: BLE001 - S3 non raggiungibile: punti senza quota
        log.warning("Terreno: Copernicus non disponibile per le quote (%s)", e)
        return [None] * len(punti)
    g = np.asarray(g, dtype="float64")
    g[g < -900] = 0.0
    rg = O.RIGHE_GRADO
    out: list[float | None] = []
    for lon, lat in punti:
        i, j = (lat - la0) * rg - 0.5, (lon - lo0) * rg - 0.5
        i0 = min(max(int(math.floor(i)), 0), g.shape[0] - 2)
        j0 = min(max(int(math.floor(j)), 0), g.shape[1] - 2)
        di, dj = min(max(i - i0, 0.0), 1.0), min(max(j - j0, 0.0), 1.0)
        v = (g[i0, j0] * (1 - di) * (1 - dj) + g[i0 + 1, j0] * di * (1 - dj)
             + g[i0, j0 + 1] * (1 - di) * dj + g[i0 + 1, j0 + 1] * di * dj)
        out.append(round(float(v), 2) if math.isfinite(v) else None)
    return out


def quote_punti(punti: list[tuple[float, float]], ripiego: bool = False, fonti: list | None = None) -> list[float | None]:
    """Quote del terreno (m) nei punti WGS84 dal DTM regionale più dettagliato che li copre (None dove nessuno li copre).
    Serve alle sagome regionali al volo (08/11/2026): corpi alla quota vera, terreno 3D acceso anche fuori dal DBTR.
    (09/11/2026 b) Con `ripiego` i punti fuori dai DTM regionali prendono la quota del Copernicus DEM 90 m, come le
    tessere del terreno: a Susegana senza il DTM del Veneto (J5 bis non fatto) i corpi restavano senza quota e la pagina
    spegneva il terreno («c'è ma è piatta»). In `fonti` (se data) «dtm» e/o «copernicus»."""
    out: list[float | None] = [None] * len(punti)
    if not punti:
        return out
    try:
        _quote_dtm(punti, out)
    except Exception as e:                              # noqa: BLE001 - senza rasterio o DTM illeggibili: resta il ripiego
        log.warning("Terreno: quote dai DTM non lette (%s)", e)
    if any(q is not None for q in out) and fonti is not None:
        fonti.append("dtm")
    mancano = [i for i, q in enumerate(out) if q is None]
    if ripiego and mancano:
        cop = quote_copernicus([punti[i] for i in mancano])
        for i, v in zip(mancano, cop):
            out[i] = v
        if fonti is not None and any(v is not None for v in cop):
            fonti.append("copernicus")
    return out


def _quote_dtm(punti: list[tuple[float, float]], out: list[float | None]) -> None:
    import rasterio
    from pyproj import Transformer
    for d in dtm_disponibili():
        mancano = [i for i, q in enumerate(out) if q is None]
        if not mancano:
            break
        r = d["riquadro_wgs84"]
        dentro = [i for i in mancano if r[0] <= punti[i][0] <= r[2] and r[1] <= punti[i][1] <= r[3]]
        if not dentro:
            continue
        try:
            t = Transformer.from_crs("EPSG:4326", d.get("crs") or "EPSG:7791", always_xy=True)
            xy = [t.transform(*punti[i]) for i in dentro]
            with rasterio.open(d["percorso"]) as src:
                for i, v in zip(dentro, src.sample(xy)):
                    q = float(v[0])
                    if math.isfinite(q) and q > -900 and (src.nodata is None or q != src.nodata):
                        out[i] = round(q, 2)
        except Exception as e:                       # noqa: BLE001 - file illeggibile: restano senza quota
            log.warning("Terreno: quote non lette da %s (%s)", d.get("file"), e)


def versione() -> str:
    imp = "|".join(d["impronta"] for d in dtm_disponibili()) or "nessun-dtm"
    return hashlib.sha1(imp.encode()).hexdigest()[:10]


def _tocca(r, b) -> bool:
    return not (b[2] < r[0] or b[0] > r[2] or b[3] < r[1] or b[1] > r[3])


def _livello(src, z: int, lat: float) -> int | None:
    """Panoramica da aprire: la più grossolana con passo ≤ pixel della tessera (None = piena risoluzione)."""
    pixel = 2 * R_TERRA / 2 ** z / 256 * math.cos(math.radians(lat))
    passo = abs(src.res[0])
    ov = src.overviews(1)
    scelta = None
    for k, f in enumerate(ov):
        if passo * f <= pixel:
            scelta = k
    return scelta


def leggi_dtm(d: dict, z: int, x: int, y: int) -> np.ndarray | None:
    """Quote della tessera dal COG (NaN dove manca), con lettura a finestra e panoramica adatta allo zoom."""
    import rasterio
    from rasterio.transform import from_bounds
    from rasterio.warp import Resampling, reproject
    w, s, e, n = limiti_tessera(z, x, y)
    b = lonlat_tessera(z, x, y)
    with rasterio.Env(GDAL_CACHEMAX=64):
        with rasterio.open(d["percorso"]) as src0:
            liv = _livello(src0, z, (b[1] + b[3]) / 2)
        apri = {"overview_level": liv} if liv is not None else {}
        with rasterio.open(d["percorso"], **apri) as src:
            out = np.full((256, 256), np.nan, dtype="float32")
            reproject(rasterio.band(src, 1), out, src_nodata=src.nodata, dst_transform=from_bounds(w, s, e, n, 256, 256),
                      dst_crs="EPSG:3857", dst_nodata=np.nan, resampling=Resampling.bilinear)
    out[out < -900] = np.nan
    return None if np.isnan(out).all() else out


def leggi_copernicus(z: int, x: int, y: int) -> np.ndarray:
    """Quote della tessera dal Copernicus DEM 90 m (stessi file dell'orizzonte lontano), bilineare; mare = 0."""
    from . import orizzonte as O
    lon, lat = centri_pixel(z, x, y)
    rg = O.RIGHE_GRADO
    fi = lat * rg                                   # righe assolute (da sud), colonne da −180°
    fj = (lon + 180.0) * rg
    r0, r1 = int(math.floor(fi.min())) - 1, int(math.ceil(fi.max())) + 2
    c0, c1 = int(math.floor(fj.min())) - 1, int(math.ceil(fj.max())) + 2
    parti = []
    for grado in range(math.floor(r0 / rg), math.floor((r1 - 1) / rg) + 1):
        a = max(r0, grado * rg) - grado * rg
        bb = min(r1, (grado + 1) * rg) - grado * rg
        parti.append(np.asarray(O._lettore(grado)[a:bb, c0:c1], dtype="float32"))
    g = np.vstack(parti)
    g[g < -900] = 0.0
    i = fi - r0 - 0.5
    j = fj - c0 - 0.5
    i0 = np.clip(np.floor(i).astype(int), 0, g.shape[0] - 2)
    j0 = np.clip(np.floor(j).astype(int), 0, g.shape[1] - 2)
    di = np.clip(i - i0, 0, 1)
    dj = np.clip(j - j0, 0, 1)
    v = (g[i0, j0] * (1 - di) * (1 - dj) + g[i0 + 1, j0] * di * (1 - dj)
         + g[i0, j0 + 1] * (1 - di) * dj + g[i0 + 1, j0 + 1] * di * dj)
    return v.astype("float32")


def nome_dtm(d: dict) -> str:
    """Nome per la legenda della pagina 3D (scheda di `dtm-server`; le schede di prima del 08/11 non l'hanno)."""
    return str(d.get("nome") or "DTM 5 m Regione Emilia-Romagna (CC BY 4.0)")


def genera(z: int, x: int, y: int, nomi: list | None = None) -> tuple[np.ndarray, str, str]:
    """(quote 256×256, fonte, licenza) della tessera: DTM regionali (il più dettagliato prima), poi Copernicus, poi piatta.
    In `nomi` (se dato) i nomi dei DTM usati, per l'intestazione X-Terreno-Nome."""
    b = lonlat_tessera(z, x, y)
    quote, fonti, licenze = None, [], []
    nomi = nomi if nomi is not None else []
    for d in dtm_disponibili():
        if not _tocca(d["riquadro_wgs84"], b):
            continue
        try:
            q = leggi_dtm(d, z, x, y)
        except Exception as e:                       # file illeggibile: si passa al ripiego
            log.warning("Terreno %s/%s/%s da %s: %s", z, x, y, d.get("file"), e)
            continue
        if q is None:
            continue
        quote = q if quote is None else np.where(np.isnan(quote), q, quote)
        fonti.append("dtm")
        licenze.append(d.get("licenza", ""))
        nomi.append(nome_dtm(d))
        if not np.isnan(quote).any():
            break
    if quote is None or np.isnan(quote).any():
        try:
            cop = leggi_copernicus(z, x, y)
            quote = cop if quote is None else np.where(np.isnan(quote), cop, quote)
            fonti.append("copernicus")
            licenze.append(LICENZA_COPERNICUS)
        except Exception as e:                       # S3 non raggiungibile o omfiles assente
            log.warning("Terreno %s/%s/%s: Copernicus non disponibile (%s)", z, x, y, e)
            if quote is None:
                return np.zeros((256, 256), dtype="float32"), "piatta", ""
            quote = np.where(np.isnan(quote), 0.0, quote)
    fonte = "+".join(dict.fromkeys(fonti))
    return quote, fonte, ", ".join(dict.fromkeys(x for x in licenze if x))


# ---------------------------------------------------------------------------------------------- copia su disco
def file_copia(z: int, x: int, y: int) -> Path:
    return C.CARTELLA_TERRENO_TESSERE / versione() / str(z) / str(x) / f"{y}.png"


_ultima_pulizia = 0.0


def pulisci(forza: bool = False) -> int:
    """Oltre TERRENO_MAX_GB toglie le tessere più vecchie fino all'80 %."""
    global _ultima_pulizia
    if not forza and time.time() - _ultima_pulizia < 3600:
        return 0
    _ultima_pulizia = time.time()
    radice = C.CARTELLA_TERRENO_TESSERE
    if not radice.exists():
        return 0
    tutti = [(p.stat().st_mtime, p.stat().st_size, p) for p in radice.rglob("*.png") if p.is_file()]
    totale, tetto = sum(s for _, s, _ in tutti), C.TERRENO_MAX_GB * 1e9
    if totale <= tetto:
        return 0
    tolti = 0
    for _, s, p in sorted(tutti):
        if totale <= 0.8 * tetto:
            break
        p.unlink(missing_ok=True)
        p.with_suffix(".txt").unlink(missing_ok=True)
        totale -= s
        tolti += 1
    if tolti:
        log.info("Terreno: tolte %d tessere vecchie dalla copia", tolti)
    return tolti


def _scrivi(p: Path, dati: bytes, fonte: str, licenza: str, nome: str = "") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_bytes(dati)
    tmp.replace(p)
    p.with_suffix(".txt").write_text(f"{fonte}\n{licenza}\n{nome}\n", encoding="utf-8")


def _ascii(t: str) -> str:
    """Intestazioni HTTP in latin-1: lettere accentate e simboli sostituiti (la pagina usa il nome solo in legenda)."""
    import unicodedata
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return t.replace("\n", " ")[:200]


def _intestazioni(dati: bytes, fonte: str, licenza: str, copia: str, nome: str = "") -> dict[str, str]:
    breve = fonte == "piatta"
    h = {"Cache-Control": "public, max-age=300" if breve else f"public, max-age={C.TERRENO_CACHE_S}",
         "ETag": '"' + hashlib.sha1(dati).hexdigest()[:20] + '"', "X-Terreno-Fonte": fonte,
         "X-Terreno-Licenza": licenza.encode("ascii", "replace").decode(), "X-Terreno-Copia": copia,
         "Access-Control-Expose-Headers": "X-Terreno-Fonte, X-Terreno-Licenza, X-Terreno-Nome"}
    if nome:
        h["X-Terreno-Nome"] = _ascii(nome)               # 08/11/2026: quale DTM regionale (più DTM sul server)
    return h


_parallele = threading.BoundedSemaphore(max(1, C.TERRENO_PARALLELE))


# ---------------------------------------------------------------------------------------------- rotte
@router.get("/fonti")
def fonti(request: Request):
    P.limita(request, "dati")
    return {"attivo": C.TERRENO_ATTIVO, "zoom": [C.TERRENO_ZOOM_MIN, ZOOM_MAX], "codifica": "terrarium",
            "tessere": "/api/terreno/{z}/{x}/{y}.png",
            "dtm": [{k: d.get(k) for k in ("file", "crs", "passo_m", "riquadro_wgs84", "licenza", "attribuzione", "nome", "scheda", "data")}
                    for d in dtm_disponibili()],
            "ripiego": COPERNICUS,
            "nota": "Terreno per la vista 3D: DTM regionali dove ci sono, altrimenti Copernicus DEM 90 m. Le quote dei "
                    "corpi degli edifici sono calcolate dal DTM regionale quando si prepara l'archivio, non da queste tessere."}


@router.get("/{z}/{x}/{y}.png")
def tessera(request: Request, z: int, x: int, y: int):
    if not C.TERRENO_ATTIVO:
        raise HTTPException(404, "Terreno spento")
    if not (C.TERRENO_ZOOM_MIN <= z <= ZOOM_MAX) or not (0 <= x < 2 ** z and 0 <= y < 2 ** z):
        raise HTTPException(404, "Zoom o tessera fuori dai limiti")
    if not _tocca(ITALIA, lonlat_tessera(z, x, y)):
        raise HTTPException(404, "Tessera fuori dall'Italia")
    p = file_copia(z, x, y)
    try:
        dati = p.read_bytes()
        meta = p.with_suffix(".txt").read_text(encoding="utf-8").split("\n")
        h = _intestazioni(dati, meta[0], meta[1] if len(meta) > 1 else "", "si", meta[2] if len(meta) > 2 else "")
        P.limita(request, "tessere_copia")             # dalla copia: tetto anti-abuso comune con le ortofoto (09/11/2026)
        if request.headers.get("if-none-match") == h["ETag"]:
            return Response(status_code=304, headers=h)
        return Response(dati, media_type="image/png", headers=h)
    except (FileNotFoundError, IndexError):
        pass
    P.limita(request, "terreno")
    if not _parallele.acquire(timeout=C.TERRENO_ATTESA_S):
        raise HTTPException(503, "Server molto occupato: riprova tra poco", headers={"Retry-After": "2"})
    try:
        nomi: list[str] = []
        quote, fonte, licenza = genera(z, x, y, nomi)
    finally:
        _parallele.release()
    nome = " e ".join(dict.fromkeys(nomi))
    dati = png(codifica(quote))
    if fonte != "piatta":
        try:
            _scrivi(p, dati, fonte, licenza, nome)
            pulisci()
        except OSError as e:
            log.warning("Terreno: copia non scritta (%s)", e)
    return Response(dati, media_type="image/png", headers=_intestazioni(dati, fonte, licenza, "nuova" if fonte != "piatta" else "no", nome))
