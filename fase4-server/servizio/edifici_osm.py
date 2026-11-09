"""Ripiego OpenStreetMap per Modelli 3D (decisione di Paolo del 07/11/2026).

Dove il punto cade fuori da ogni archivio di qualità (DBTR: fuori dall'Emilia-Romagna e nei comuni ER non ancora
preparati) la pagina chiede qui gli edifici OSM intorno al punto e li usa come corpi: scelta dell'edificio, «Genera il
3D», ombre e report funzionano come con l'archivio. Dove c'è il DBTR vale il DBTR e OSM non si mescola (lo decide la
pagina, che conosce gli archivi e i confini ISTAT dei comuni preparati).

Rotta:
  GET /api/edifici/osm?lon=…&lat=…
      → FeatureCollection WGS84 dei corpi (stesse proprietà delle celle di contesto degli archivi: id, edificio, gronda,
        altezza, fonte della sagoma e dell'altezza, licenza «ODbL 1.0», qualità), con licenza, attribuzione, centro e
        raggio della richiesta, quanti corpi hanno l'altezza stimata.

Regole:
  * lettore e regole di `fase10-edifici3d/edifici3d/osm_campione.py` (way chiuse, multipoligoni con i cortili e way
    aperte, altezza `height` → `building:levels` × 3 m → **stima** dichiarata di 9 m), copiato nell'immagine dell'api;
  * client Overpass di `strati.py` (istanza principale e di riserva dello strato «osm_edifici», User-Agent del servizio);
  * il punto si arrotonda a una **cella di 0,002°** (~200 m): una sola query piccola (raggio 400 m attorno al centro della
    cella) serve tutti i punti della cella, copiata su disco (DATI/edifici_osm/) per EDIFICI_OSM_GIORNI giorni; a Overpass
    va il centro della cella, non il punto esatto dell'utente;
  * **una chiamata alla volta** per tutto il sito, almeno un secondo tra due chiamate (niente raffiche), attesa del turno
    al massimo EDIFICI_OSM_ATTESA_S secondi, poi 503; tetto EDIFICI_OSM_TETTO_ORA chiamate all'ora per tutto il sito;
  * limite per indirizzo «edifici_osm» (EDIFICI_OSM_ORA all'ora, solo le richieste che chiamano davvero Overpass o il
    WFS regionale: dal 09/11/2026 le celle già in copia contano in «edifici_osm_copia», EDIFICI_OSM_COPIA_ORA) e **verifica
    anti-robot** (Turnstile, gettone di sessione) come patrimonio e geocodifica: la rotta consuma le quote di Overpass;
  * EDIFICI_OSM=false nel .env la spegne (404 con il motivo, la pagina lo dice);
  * **altezze** (decisione di Paolo del 07/11/2026): ai corpi senza `height` né `building:levels` si dà la **mediana dei
    corpi DBTR vicini** (entro 200 m, almeno 3, letti dalle celle di contesto degli archivi del server elencati in
    `archivi.json`, CARTELLA_EDIFICI_INTERNA), altrove la stima fissa di 9 m; sempre «stima», con l'origine per corpo
    (`origine_altezza`: osm_height, osm_piani, dbtr_vicini, fissa) e i conteggi in `altezze`. Calcolata a ogni risposta
    (non nella copia su disco): un comune preparato dopo vale subito anche per le celle già copiate.
Licenza dei dati: © OpenStreetMap contributors, ODbL 1.0; la copia su disco è un database derivato ODbL, separato dagli
archivi CC BY.

**Sagome regionali al volo** (08/11/2026, decisione di Paolo): dove la Regione pubblica le sagome degli edifici aperte e
senza altezze con un WFS (`fase10-edifici3d/fonti/sagome_regionali.toml` e
`sagome_regionali.d/`: oggi Veneto (IODL 2.0), Sardegna (CC BY 4.0, WFS) e Campania (CC BY 4.0, ArcGIS REST)) la stessa rotta
risponde con le **sagome della Regione** e l'**altezza dell'edificio OSM che si sovrappone di più** (height, poi piani × 3
m), altrimenti la mediana dei corpi DBTR vicini o dei vicini con l'altezza OSM, altrimenti 9 m, sempre dichiarata per
corpo (`edifici3d/sagome_regionali.py`); gli edifici OSM senza sagoma regionale restano come corpi OSM. Il WFS riceve il
riquadro di 800 m attorno al centro della cella (non il punto dell'utente), nel sistema nativo della Regione (EPSG:6876
per il Veneto: in EPSG:4326 il filtro non trova nulla). Stessa verifica anti-robot e stessi limiti per IP; una chiamata
alla volta ai WFS, almeno un secondo tra due, tetto EDIFICI_REGIONALI_TETTO_ORA all'ora; copia su disco delle sagome
(DATI/edifici_regionali/<regione>/, EDIFICI_OSM_GIORNI giorni). Le quote dei corpi si leggono dal DTM del server
(`terreno.quote_punti`: in Veneto il DTM 5 m da voli LiDAR, se è sul server; dal 09/11/2026 b, dove non c'è un DTM
regionale, il Copernicus DEM 90 m delle tessere del terreno, anche per gli edifici OSM), così la vista 3D ha il terreno. Se il WFS
non risponde o non trova sagome resta il ripiego OSM, con l'avviso. EDIFICI_REGIONALI=false le spegne.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import threading
import time
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from . import config as C, protezione as P, strati as S

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/edifici")

try:                                    # lettore della fase 10 (nell'immagine: /app/edifici3d/osm_campione.py)
    from edifici3d import osm_campione as OC
except ImportError as e:                # pragma: no cover - immagine senza shapely/pyproj
    OC = None
    log.warning("edifici3d.osm_campione non disponibile: %s", e)
try:                                    # sagome regionali al volo (08/11/2026)
    from edifici3d import sagome_regionali as SR
except ImportError as e:                # pragma: no cover
    SR = None
    log.warning("edifici3d.sagome_regionali non disponibile: %s", e)

CELLA = 0.002
ITALIA = (6.6, 35.4, 18.6, 47.1)
SCHEDA = "https://www.openstreetmap.org/copyright"
NOTA = ("Ripiego: qui non c'è ancora un archivio di qualità (DBTR). Sagome da OpenStreetMap, completezza variabile; "
        "altezze dal tag height o dai piani (building:levels × 3 m), altrove stimate (mediana dei corpi DBTR entro 200 m "
        "dove ci sono, altrimenti 9 m) e dichiarate come stima.")
MAX_MB = 500                            # tetto della copia su disco

_turno = threading.Lock()
_ultima = [0.0]                         # monotonic dell'ultima chiamata a Overpass
_scritte = [0]


def cella(lon: float, lat: float) -> tuple[float, float, str]:
    """Centro della cella di 0,002° che contiene il punto e nome del file della copia."""
    i, j = round(lon / CELLA), round(lat / CELLA)
    return round(i * CELLA, 6), round(j * CELLA, 6), f"{j}_{i}"


def _copia(nome: str) -> Path:
    return C.DATI / "edifici_osm" / f"{nome}.json"


def leggi_copia(nome: str) -> dict | None:
    f = _copia(nome)
    try:
        if f.exists() and time.time() - f.stat().st_mtime < C.EDIFICI_OSM_GIORNI * 86400:
            return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    return None


def scrivi_copia(nome: str, d: dict) -> None:
    f = _copia(nome)
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        tmp.replace(f)
        _scritte[0] += 1
        if _scritte[0] % 20 == 1:
            pulisci()
    except OSError as e:
        log.warning("Edifici OSM: copia non scritta (%s)", e)


def pulisci() -> int:
    """Toglie le copie scadute e, oltre MAX_MB, le più vecchie. Restituisce quante ne ha tolte."""
    cartella = C.DATI / "edifici_osm"
    if not cartella.exists():
        return 0
    tolti, file = 0, []
    limite = time.time() - C.EDIFICI_OSM_GIORNI * 86400
    for f in cartella.glob("*.json"):
        try:
            st = f.stat()
        except OSError:
            continue
        if st.st_mtime < limite:
            f.unlink(missing_ok=True); tolti += 1
        else:
            file.append((st.st_mtime, st.st_size, f))
    totale = sum(x[1] for x in file)
    for _, peso, f in sorted(file):
        if totale <= MAX_MB * 1e6:
            break
        f.unlink(missing_ok=True); tolti += 1; totale -= peso
    return tolti


def chiedi(lon: float, lat: float) -> dict:
    """Una query a Overpass per la cella (lon, lat già arrotondati), letta con le regole di osm_campione."""
    urls = C.EDIFICI_OSM_URL or S.istanze_overpass()
    try:
        r = S.chiedi_overpass(urls, OC.query_punto(lon, lat), "xml", timeout=C.EDIFICI_OSM_TIMEOUT_S, nome="Edifici OSM")
    except httpx.HTTPError as e:
        log.warning("Edifici OSM: Overpass non raggiungibile (%s)", e)
        raise HTTPException(502, "OpenStreetMap (API Overpass) non risponde: riprova tra qualche minuto.")
    if r.status_code in (429, 504):
        raise HTTPException(503, "OpenStreetMap (API Overpass) è molto richiesto in questo momento: riprova tra qualche minuto.",
                            headers={"Retry-After": "60"})
    if r.status_code != 200 or "xml" not in r.headers.get("content-type", ""):
        log.warning("Edifici OSM: risposta %s %s", r.status_code, r.headers.get("content-type", ""))
        raise HTTPException(502, "OpenStreetMap (API Overpass) ha risposto con un errore: riprova tra qualche minuto.")
    errore = OC.errore_overpass(r.content)
    if errore:
        log.warning("Edifici OSM: %s", errore)
        raise HTTPException(502, "OpenStreetMap (API Overpass) non ha completato la richiesta: riprova tra qualche minuto.")
    try:
        return OC.corpi_al_volo(r.content, lon, lat)
    except Exception as e:   # noqa: BLE001 - XML illeggibile
        log.warning("Edifici OSM: risposta non leggibile (%s)", e)
        raise HTTPException(502, "OpenStreetMap (API Overpass) ha risposto con dati non leggibili.")


# ---------------------------------------------------------------------------------------------- altezze dai vicini DBTR
_archivi_cache: dict = {"mtime": None, "archivi": []}
_celle_cache: dict[str, list] = {}
MAX_CELLE = 64


def archivi_dbtr() -> list[tuple[Path, list, float]]:
    """(cartella dei prodotti, riquadro, cella) degli archivi elencati in archivi.json (riletti quando cambia il file)."""
    radice = C.CARTELLA_EDIFICI_INTERNA
    f = radice / "archivi.json"
    try:
        mt = f.stat().st_mtime
    except OSError:
        return []
    if _archivi_cache["mtime"] == mt:
        return _archivi_cache["archivi"]
    out = []
    try:
        voci = json.loads(f.read_text(encoding="utf-8")).get("archivi", [])
    except (OSError, ValueError):
        voci = []
    for v in voci[:200]:
        base = str((v or {}).get("base", ""))
        if not base.startswith("/edifici3d/") or ".." in base:
            continue
        cartella = radice / base[len("/edifici3d/"):].strip("/")
        try:
            ind = json.loads((cartella / "indice.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        r = ind.get("riquadro")
        if ind.get("sintetico") or not (isinstance(r, list) and len(r) == 4):
            continue
        out.append((cartella, [float(x) for x in r], float(ind.get("cella") or 0.01)))
    _archivi_cache.update(mtime=mt, archivi=out)
    return out


def _cella_dbtr(cartella: Path, nome: str) -> list:
    k = f"{cartella}|{nome}"
    if k not in _celle_cache:
        punti = []
        try:
            d = json.loads((cartella / "contesto" / f"{nome}.json").read_text(encoding="utf-8"))
            for f in d.get("features", []):
                g = OC.altezza_dbtr_valida(f.get("properties") or {})
                c = OC._centro(f.get("geometry")) if g is not None else None
                if c is not None:
                    punti.append((c[0], c[1], g))
        except (OSError, ValueError):
            pass
        while len(_celle_cache) >= MAX_CELLE:
            _celle_cache.pop(next(iter(_celle_cache)))
        _celle_cache[k] = punti
    return _celle_cache[k]


def vicini_dbtr(lon: float, lat: float, raggio_m: float) -> list[tuple[float, float, float]]:
    """Corpi DBTR (lon, lat, gronda) degli archivi del server entro ~raggio_m dal punto (celle di contesto)."""
    import math
    dlon, dlat = raggio_m / (111320 * math.cos(math.radians(lat))), raggio_m / 110574
    out = []
    for cartella, r, c in archivi_dbtr():
        if lon + dlon < r[0] or lon - dlon > r[2] or lat + dlat < r[1] or lat - dlat > r[3]:
            continue
        for i in range(math.floor((lon - dlon) / c), math.floor((lon + dlon) / c) + 1):
            for j in range(math.floor((lat - dlat) / c), math.floor((lat + dlat) / c) + 1):
                out.extend(_cella_dbtr(cartella, f"{i}_{j}"))
    return out


def con_altezze_vicine(d: dict) -> dict:
    """Copia della risposta con le altezze fisse portate alla mediana dei corpi DBTR vicini, dove ci sono."""
    d = json.loads(json.dumps(d))
    for f in d.get("features", []):                    # copie scritte prima del 07/11/2026 sera: senza l'origine
        f.setdefault("properties", {})["origine_altezza"] = OC.origine_altezza(f["properties"])
    try:
        lo, la = d.get("centro") or (None, None)
        if lo is not None and d.get("features"):
            OC.altezze_da_vicini(d["features"], vicini_dbtr(lo, la, OC.RAGGIO_VOLO + OC.RAGGIO_VICINI + 50))
    except Exception as e:   # noqa: BLE001 - archivi illeggibili: restano i 9 m
        log.warning("Edifici OSM: altezze dai vicini DBTR non calcolate (%s)", e)
    OC.conta_altezze(d)
    return d


# ---------------------------------------------------------------------------------------------- sagome regionali al volo
_turno_reg = threading.Lock()
_ultima_reg = [0.0]
NOTA_REGIONALI = ("Sagome dalla {regione} ({licenza}), altezze da OpenStreetMap dove ci sono (edificio OSM sovrapposto: "
                  "height o piani × 3 m), altrimenti stimate (mediana dei corpi DBTR vicini o dei vicini con l'altezza OSM, "
                  "altrimenti 9 m); gli edifici OSM senza sagoma regionale restano da OpenStreetMap.")


def _copia_reg(regione: str, nome: str) -> Path:
    return C.DATI / "edifici_regionali" / regione / f"{nome}.json"


def _copia_reg_valida(fonte_id: str, nome: str) -> bool:
    f = _copia_reg(fonte_id, nome)
    try:
        return f.exists() and time.time() - f.stat().st_mtime < C.EDIFICI_OSM_GIORNI * 86400
    except OSError:
        return False


def regionali_in_copia(lo: float, la: float, nome: str) -> bool:
    """La cella non chiede nulla al WFS regionale (fuori dalle regioni con le sagome al volo, o sagome già in copia)?"""
    if not C.EDIFICI_REGIONALI or SR is None:
        return True
    try:
        fonte = SR.fonte_nel_punto(lo, la)
    except Exception:   # noqa: BLE001
        return True
    return not fonte or _copia_reg_valida(fonte["id"], nome)


def sagome_wfs(fonte: dict, lo: float, la: float, nome: str) -> dict | None:
    """Sagome del WFS regionale per la cella (copia su disco o una chiamata, una alla volta); None se non risponde."""
    f = _copia_reg(fonte["id"], nome)
    try:
        if f.exists() and time.time() - f.stat().st_mtime < C.EDIFICI_OSM_GIORNI * 86400:
            return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    if not _turno_reg.acquire(timeout=C.EDIFICI_OSM_ATTESA_S):
        return None
    try:
        if not P.tetto_globale("wfs_regionali", C.EDIFICI_REGIONALI_TETTO_ORA):
            log.warning("Sagome regionali: tetto orario raggiunto")
            return None
        attesa = 1.0 - (time.monotonic() - _ultima_reg[0])
        if attesa > 0:
            time.sleep(attesa)
        try:
            r = httpx.get(SR.url_wfs(fonte, lo, la, OC.RAGGIO_VOLO), timeout=C.EDIFICI_REGIONALI_TIMEOUT_S,
                          headers={"User-Agent": "EuGEnio (https://eugenio.statocritico.it)"})
        finally:
            _ultima_reg[0] = time.monotonic()
        if r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
            log.warning("Sagome regionali %s: risposta %s %s", fonte["id"], r.status_code, r.headers.get("content-type", ""))
            return None
        dati = r.json()
        tenuti = SR.campi_tenuti(fonte)          # campi del catalogo nazionale più il campo dell'uso della fonte (08/11/2026)
        w = {"features": [{"id": x.get("id"), "geometry": x.get("geometry"),
                           "properties": {k: v for k, v in (x.get("properties") or {}).items() if k in tenuti}}
                          for x in dati.get("features", []) if x.get("geometry")],
             "data": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        try:
            f.parent.mkdir(parents=True, exist_ok=True)
            tmp = f.with_suffix(".tmp")
            tmp.write_text(json.dumps(w, separators=(",", ":")), encoding="utf-8")
            tmp.replace(f)
        except OSError as e:
            log.warning("Sagome regionali: copia non scritta (%s)", e)
        return w
    except (httpx.HTTPError, ValueError) as e:
        log.warning("Sagome regionali %s: WFS non raggiungibile (%s)", fonte["id"], e)
        return None
    finally:
        _turno_reg.release()


def con_quote(d: dict) -> dict:
    """quota_terreno dei corpi dal DTM del server (centro del corpo), dove c'è; (09/11/2026 b) altrimenti dal Copernicus DEM
    90 m, lo stesso delle tessere del terreno: senza quote la pagina spegneva il terreno (Susegana «piatta» senza il DTM
    del Veneto). Vale per le sagome regionali e per gli edifici OSM. In `quote_fonte` le fonti usate."""
    if not C.TERRENO_ATTIVO:
        return d
    try:
        from . import terreno as TR
        fs = d.get("features", [])
        centri = [OC._centro(f.get("geometry")) for f in fs]
        fonti: list[str] = []
        q = TR.quote_punti([c for c in centri if c is not None], ripiego=True, fonti=fonti)
        d["quote_fonte"] = "+".join(fonti) or None
        it = iter(q)
        n = 0
        for f, c in zip(fs, centri):
            v = next(it) if c is not None else None
            if v is not None:
                f["properties"]["quota_terreno"] = v
                n += 1
        d["quote_dtm"] = n
    except Exception as e:   # noqa: BLE001 - senza DTM: corpi senza quota (vista piatta)
        log.warning("Sagome regionali: quote non lette (%s)", e)
    return d


def con_sagome_regionali(d: dict, nome: str) -> dict:
    """Risposta OSM (già con le altezze dai vicini DBTR) → sagome regionali con le altezze OSM, se la cella è in una
    regione con le sagome al volo e il WFS risponde; altrimenti la risposta OSM com'è (con l'avviso se il WFS tace)."""
    if not C.EDIFICI_REGIONALI or SR is None:
        return d
    lo, la = d.get("centro") or (None, None)
    fonte = SR.fonte_nel_punto(lo, la) if lo is not None else None
    if not fonte:
        return d
    w = sagome_wfs(fonte, lo, la, nome)
    if w is None:
        d["avviso_sagome"] = f"Il servizio delle sagome della {fonte.get('ente', fonte['regione'])} non ha risposto: edifici da OpenStreetMap."
        return d
    if not w.get("features"):
        return d                                       # fuori dalla regione (riquadro largo) o zona senza edifici
    r = SR.unisci(w, fonte, d, lo, la)
    try:
        OC.altezze_da_vicini(r["features"], vicini_dbtr(lo, la, OC.RAGGIO_VOLO + OC.RAGGIO_VICINI + 50))
    except Exception as e:   # noqa: BLE001
        log.warning("Sagome regionali: vicini DBTR non letti (%s)", e)
    SR.altezze_da_vicini_osm(r["features"])
    OC.conta_altezze(r)
    for k in ("centro", "raggio", "cella"):
        r[k] = d.get(k)
    r.update({"scheda": fonte["scheda"], "fonte": f"{fonte['nome']} ({'servizio ArcGIS' if fonte.get('servizio_tipo') == 'arcgis' else 'WFS'} della Regione) e OpenStreetMap (API Overpass)",
              "nota": NOTA_REGIONALI.format(regione=fonte.get("ente", fonte["regione"]), licenza=fonte["licenza"]),
              "data": w.get("data"), "data_osm": d.get("data")})
    return con_quote(r)


@router.get("/osm")
def edifici_osm(request: Request, lon: float = Query(...), lat: float = Query(...)):
    if not C.EDIFICI_OSM:
        raise HTTPException(404, "Il ripiego OpenStreetMap degli edifici è spento su questo server.")
    if OC is None:
        raise HTTPException(503, "Il lettore degli edifici OpenStreetMap non è installato su questo server.")
    if not (ITALIA[0] <= lon <= ITALIA[2] and ITALIA[1] <= lat <= ITALIA[3]):
        raise HTTPException(400, "Punto fuori dall'Italia.")
    P.richiedi_sessione(request)
    lo, la, nome = cella(lon, lat)
    d = leggi_copia(nome)
    # (09/11/2026) la copia non consuma il limite di Overpass: conta solo nel tetto alto «edifici_osm_copia»
    P.limita(request, "edifici_osm_copia" if d is not None and regionali_in_copia(lo, la, nome) else "edifici_osm")
    if d is None:
        if not _turno.acquire(timeout=C.EDIFICI_OSM_ATTESA_S):
            raise HTTPException(503, "OpenStreetMap è molto richiesto in questo momento: riprova tra poco.",
                                headers={"Retry-After": "10"})
        try:
            d = leggi_copia(nome)                       # un'altra richiesta della stessa cella può averla appena scritta
            if d is None:
                if not P.tetto_globale("overpass", C.EDIFICI_OSM_TETTO_ORA):
                    raise HTTPException(503, "Gli edifici OpenStreetMap hanno esaurito la quota di quest'ora per tutti gli "
                                             "utenti del sito: riprova più tardi.", headers={"Retry-After": "600"})
                attesa = 1.0 - (time.monotonic() - _ultima[0])
                if attesa > 0:
                    time.sleep(attesa)
                try:
                    d = chiedi(lo, la)
                finally:
                    _ultima[0] = time.monotonic()
                d.update({"centro": [lo, la], "raggio": OC.RAGGIO_VOLO, "cella": CELLA, "scheda": SCHEDA, "nota": NOTA,
                          "fonte": "OpenStreetMap, tramite l'API Overpass",
                          "data": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
                scrivi_copia(nome, d)
        finally:
            _turno.release()
    risposta = con_sagome_regionali(con_altezze_vicine(d), nome)
    if "quote_dtm" not in risposta:
        risposta = con_quote(risposta)                  # 09/11/2026 b: anche gli edifici OSM alla quota del terreno
    lic = "IODL 2.0; ODbL 1.0" if risposta.get("sagome") else "ODbL 1.0"
    return JSONResponse(risposta, headers={"Cache-Control": "private, max-age=3600", "X-Licenza": lic})
