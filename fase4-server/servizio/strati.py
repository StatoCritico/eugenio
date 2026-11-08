"""Strati sopra le ortofoto: confini delle particelle catastali e contorni degli edifici (05/11/2026, seconda
pubblicazione, richiesta di Paolo per la pagina Modelli 3D).

Stessa logica del proxy delle ortofoto (`ortofoto.py`: copia su disco, ritmo verso la fonte per tutti gli utenti, limite
per indirizzo «ortofoto», 404 fuori zona o fuori zoom), ma per immagini **trasparenti** da mettere sopra la foto. Le rotte
stanno sotto `/api/ortofoto/strati/…`, così Caddy (nessuna compressione, timeout di 30 s) e la regola di rate limiting di
Cloudflare (che esclude `/api/ortofoto/`) valgono anche qui senza cambiarli.

Fonti nei TOML di `fase10-edifici3d/ortofoto/strati/` (copiati nell'immagine con le ortofoto):
  * **wms**: GetMap PNG trasparente. Se il servizio non offre EPSG:3857 (cartografia catastale dell'Agenzia delle
    Entrate: solo EPSG:6706, 4258, 25832–25834, 3044–3046) si chiede il riquadro in coordinate geografiche (`crs =
    "EPSG:4258"`, assi lat,lon del WMS 1.3.0) e si **riproietta** riga per riga in web mercator (le due proiezioni hanno
    la stessa longitudine lineare: basta spostare le righe secondo la latitudine; esatto al pixel). Con `metatessera = 2`
    si chiede un blocco di 2×2 tessere e si tiene quella in alto a destra (la scritta del servizio in basso a sinistra
    cade fuori; l'attribuzione completa resta sotto la mappa e nelle immagini scaricate).
  * `contorni = true`: il riempimento del servizio (particelle beige, edifici rosa) diventa trasparente e restano solo
    le linee e le scritte, ricolorate con `colore` (si vedono sulla foto). Modifica dichiarata nella citazione.
  * **overpass**: sagome degli edifici di OpenStreetMap (ODbL) in GeoJSON, a tessere dello zoom 16, dall'API Overpass;
    per le regioni senza DB topografico regionale servito qui. Archivio ODbL separato: `strati/osm/…` nella copia.

Rotte:
  GET /api/ortofoto/strati                         elenco degli strati accesi (tema, regioni, licenza, colore, …)
  GET /api/ortofoto/strati/{id}/{z}/{x}/{y}.png    tessera trasparente 256×256 in EPSG:3857
  GET /api/ortofoto/strati/{id}/16/{x}/{y}.json    sagome OSM della tessera (solo per le fonti «overpass»)
Spegnimento: `attiva = false` o `stato = "spenta"` nel TOML, oppure STRATI_SPENTI=id1,id2 nel .env.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import math
import re
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

from . import config as C, ortofoto as O, protezione as P

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ortofoto/strati")

TEMI = ("particelle", "edifici")
ZOOM_OSM = 16


@dataclass
class Strato:
    id: str
    tema: str
    nome: str
    tipo: str
    url: str
    licenza: str
    citazione: str
    scheda: str
    stato: str
    livello: str = ""
    crs: str = "EPSG:3857"
    formato: str = "image/png"
    regioni: tuple[str, ...] = ()          # codici ISTAT delle regioni servite; vuoto = tutte quelle non servite da altri
    attiva: bool = True
    zoom: tuple[int, int] = (16, 20)
    riquadro: tuple[float, float, float, float] = (6.6, 35.4, 18.6, 47.1)
    contorni: bool = False
    colore: str = "#ffd400"
    metatessera: int = 1
    legenda: str = ""
    al_secondo: float = 2.0
    all_ora: int = 2000
    url_riserva: tuple[str, ...] = ()       # altre istanze della stessa fonte (Overpass), provate in ordine se la prima fallisce
    nota: str = ""
    _x: list = field(default_factory=list, repr=False)

    def accesa(self) -> bool:
        return self.attiva and self.stato != "spenta" and self.id not in C.STRATI_SPENTI

    @property
    def estensione(self) -> str:
        return "json" if self.tipo == "overpass" else "png"

    def pubblica(self) -> dict:
        return {"id": self.id, "tema": self.tema, "nome": self.nome, "licenza": self.licenza,
                "citazione": self.citazione, "scheda": self.scheda, "stato": self.stato, "regioni": list(self.regioni),
                "zoom": list(self.zoom), "riquadro": list(self.riquadro), "colore": self.colore,
                "legenda": self.legenda, "tipo": "vettori" if self.tipo == "overpass" else "immagine", "nota": self.nota,
                "tessere": f"/api/ortofoto/strati/{self.id}/{{z}}/{{x}}/{{y}}.{self.estensione}"}


def leggi_toml(file: Path) -> list[Strato]:
    d = tomllib.loads(file.read_text(encoding="utf-8"))
    out = []
    for s in d.get("strato", []):
        sid = str(s.get("id", ""))
        if not re.fullmatch(r"[a-z0-9_]{2,40}", sid):
            raise ValueError(f"{file.name}: id «{sid}» non valido")
        if s.get("tema") not in TEMI:
            raise ValueError(f"{file.name}: tema «{s.get('tema')}» non valido per {sid} ({', '.join(TEMI)})")
        if s.get("tipo") not in ("wms", "overpass"):
            raise ValueError(f"{file.name}: tipo «{s.get('tipo')}» non valido per {sid} (wms o overpass)")
        stato = str(s.get("stato", "da confermare")).lower()
        if stato not in O.STATI:
            raise ValueError(f"{file.name}: stato «{stato}» non valido per {sid}")
        if O.ESCLUSI.search(str(s.get("url", ""))):
            raise ValueError(f"{file.name}: lo strato {sid} usa un servizio escluso")
        crs = str(s.get("crs", "EPSG:3857"))
        if crs not in ("EPSG:3857", "EPSG:4258", "EPSG:6706", "EPSG:4326"):
            raise ValueError(f"{file.name}: crs «{crs}» non gestito per {sid}")
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(s.get("colore", "#ffd400"))):
            raise ValueError(f"{file.name}: colore non valido per {sid}")
        ritmo = s.get("ritmo", {})
        out.append(Strato(id=sid, tema=s["tema"], nome=s.get("nome", sid), tipo=s["tipo"], url=s["url"],
                          licenza=s.get("licenza", ""), citazione=s.get("citazione", ""), scheda=s.get("scheda", ""),
                          stato=stato, livello=s.get("livello", ""), crs=crs, formato=s.get("formato", "image/png"),
                          regioni=tuple(str(r) for r in s.get("regioni", [])), attiva=bool(s.get("attiva", True)),
                          zoom=tuple(s.get("zoom", (16, 20))), riquadro=tuple(s.get("riquadro", (6.6, 35.4, 18.6, 47.1))),
                          contorni=bool(s.get("contorni", False)), colore=str(s.get("colore", "#ffd400")),
                          metatessera=max(1, min(3, int(s.get("metatessera", 1)))), legenda=s.get("legenda", ""),
                          url_riserva=tuple(str(u) for u in s.get("url_riserva", []) if not O.ESCLUSI.search(str(u))),
                          al_secondo=float(ritmo.get("al_secondo", 2)), all_ora=int(ritmo.get("all_ora", 2000)),
                          nota=s.get("nota", "")))
    return out


_strati: dict[str, Strato] | None = None


def strati(ricarica: bool = False) -> dict[str, Strato]:
    global _strati
    if _strati is None or ricarica:
        tutti: dict[str, Strato] = {}
        cartella = C.ORTOFOTO_FONTI / "strati"
        for file in sorted(cartella.glob("*.toml")) if cartella.exists() else []:
            try:
                for s in leggi_toml(file):
                    tutti[s.id] = s
            except (ValueError, KeyError, tomllib.TOMLDecodeError) as e:
                log.warning("Strati: %s scartato: %s", file.name, e)
        _strati = tutti
    return _strati


# ---------------------------------------------------------------------------------------------- geometria
def _dentro(s: Strato, z: int, x: int, y: int) -> bool:
    f = O.Fonte(id=s.id, nome="", tipo="wms", url="", formato="", licenza="", citazione="", scheda="", stato="",
                regione="", zoom=s.zoom, riquadro=s.riquadro)
    return O.dentro(f, z, x, y)


def blocco(s: Strato, z: int, x: int, y: int) -> tuple[int, int, int]:
    """(x0, y0, m) del blocco di m×m tessere chiesto alla fonte: la tessera voluta è quella in alto a destra."""
    m = s.metatessera
    return max(0, x - (m - 1)), y, m


def url_wms(s: Strato, z: int, x: int, y: int) -> tuple[str, int]:
    """URL del GetMap per la tessera (o il blocco) e lato in pixel dell'immagine chiesta."""
    x0, y0, m = blocco(s, z, x, y)
    lato = 256 * m
    sep = "&" if "?" in s.url else "?"
    if s.crs == "EPSG:3857":
        w, _, _, n = O.limiti_tessera(z, x0, y0)
        _, sud, est, _ = O.limiti_tessera(z, x0 + m - 1, y0 + m - 1)
        bbox = f"{w:.3f},{sud:.3f},{est:.3f},{n:.3f}"
    else:   # geografiche: nel WMS 1.3.0 EPSG:4258/4326/6706 vogliono lat,lon
        lo0, _, _, la1 = O.lonlat_tessera(z, x0, y0)
        _, la0, lo1, _ = O.lonlat_tessera(z, x0 + m - 1, y0 + m - 1)
        bbox = f"{la0:.9f},{lo0:.9f},{la1:.9f},{lo1:.9f}"
    return (f"{s.url}{sep}SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS={s.livello}&STYLES=&CRS={s.crs}"
            f"&BBOX={bbox}&WIDTH={lato}&HEIGHT={lato}&FORMAT={s.formato}&TRANSPARENT=TRUE"), lato


def righe_mercatore(z: int, y0: int, m: int):
    """Per ogni riga dell'immagine in web mercator (blocco di m tessere a partire da y0), la riga corrispondente
    dell'immagine chiesta con la latitudine lineare (stesso riquadro). Restituisce un array di indici."""
    import numpy as np
    n = 2 ** z
    lato = 256 * m
    lat = lambda j: math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * j / n))))
    la_n, la_s = lat(y0), lat(y0 + m)
    j = y0 + (np.arange(lato) + 0.5) / 256.0                     # centro di ogni riga in unità di tessera
    la = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * j / n))))
    src = (la_n - la) / (la_n - la_s) * lato - 0.5
    return np.clip(np.rint(src), 0, lato - 1).astype(int)


def elabora(s: Strato, dati: bytes, z: int, x: int, y: int) -> bytes:
    """Riproiezione (se serve), contorni ricolorati (se chiesti) e ritaglio della tessera dal blocco. PNG RGBA."""
    import numpy as np
    from PIL import Image
    x0, y0, m = blocco(s, z, x, y)
    im = Image.open(io.BytesIO(dati)).convert("RGBA")
    lato = 256 * m
    if im.size != (lato, lato):
        im = im.resize((lato, lato), Image.NEAREST)
    a = np.asarray(im).copy()
    if s.crs != "EPSG:3857":
        a = a[righe_mercatore(z, y0, m)]
    c0, r0 = (x - x0) * 256, 0
    a = a[r0:r0 + 256, c0:c0 + 256]
    if s.contorni:
        a = solo_contorni(a, s.colore)
    out = io.BytesIO()
    Image.fromarray(a, "RGBA").save(out, "PNG", optimize=True)
    return out.getvalue()


def solo_contorni(a, colore: str):
    """Toglie il riempimento: restano i pixel più scuri del colore di fondo dei poligoni (linee, scritte) e il bordo delle
    zone piene; tutto ricolorato con `colore`, opaco; il resto trasparente."""
    import numpy as np
    op = a[..., 3] > 40
    out = np.zeros_like(a)
    if not op.any():
        return out
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    fondo = float(np.median(lum[op]))
    scuro = op & (lum < fondo - 35)
    p = np.pad(op, 1, mode="edge")          # il bordo della tessera non è un contorno (niente griglia tra le tessere)
    tutti_vicini = p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    linea = scuro | (op & ~tutti_vicini)
    r, g, b = (int(colore[i:i + 2], 16) for i in (1, 3, 5))
    out[linea] = (r, g, b, 255)
    return out


# ---------------------------------------------------------------------------------------------- OSM (Overpass)
def query_overpass(z: int, x: int, y: int) -> str:
    lo0, la0, lo1, la1 = O.lonlat_tessera(z, x, y)
    bb = f"{la0:.6f},{lo0:.6f},{la1:.6f},{lo1:.6f}"
    return f'[out:json][timeout:25];(way["building"]({bb});relation["building"]["type"="multipolygon"]({bb}););out geom;'


def geojson_da_overpass(d: dict) -> dict:
    """Ways chiuse → Polygon; relazioni multipoligono → un Polygon per ogni anello esterno. Solo geometria e id OSM."""
    feats = []
    for el in d.get("elements", []):
        anelli = []
        if el.get("type") == "way" and el.get("geometry"):
            anelli = [el["geometry"]]
        elif el.get("type") == "relation":
            anelli = [m["geometry"] for m in el.get("members", []) if m.get("role") == "outer" and m.get("geometry")]
        for g in anelli:
            c = [[round(p["lon"], 7), round(p["lat"], 7)] for p in g]
            if len(c) < 4 or c[0] != c[-1]:
                continue
            feats.append({"type": "Feature", "properties": {"osm": f"{el['type'][0]}{el['id']}"},
                          "geometry": {"type": "Polygon", "coordinates": [c]}})
    return {"type": "FeatureCollection", "features": feats,
            "attribution": "© contributori OpenStreetMap (ODbL 1.0)"}


# ---------------------------------------------------------------------------------------------- rotte
USER_AGENT = "EuGEnio/1.0 (+https://eugenio.statocritico.it)"


def _scarica(url: str, dati: str | None = None, timeout: float | None = None) -> httpx.Response:
    h = {"User-Agent": USER_AGENT}
    t = timeout or (45 if dati is not None else 30)
    with httpx.Client(timeout=t, follow_redirects=True, headers=h) as c:
        return c.post(url, data={"data": dati}) if dati is not None else c.get(url)


def chiedi_overpass(urls, query: str, formato: str = "json", timeout: float | None = None, nome: str = "Overpass") -> httpx.Response:
    """Prova le istanze di Overpass in ordine (le pubbliche sono spesso sovraccariche: 502/504/429, o lente) e
    restituisce la prima risposta 200 del formato chiesto («json» o «xml»), altrimenti l'ultima ottenuta; se nessuna
    risponde, l'ultimo errore di rete. Usata dallo strato «Contorni degli edifici» e dal ripiego OSM di Modelli 3D
    (servizio/edifici_osm.py, 07/11/2026)."""
    ultima, errore = None, None
    for url in urls:
        try:
            r = _scarica(url, query, timeout) if timeout else _scarica(url, query)
        except httpx.HTTPError as e:
            log.info("%s: %s non risponde (%s)", nome, url, e)
            errore = e
            continue
        if r.status_code == 200 and formato in r.headers.get("content-type", ""):
            return r
        log.info("%s: %s risponde %s", nome, url, r.status_code)
        ultima = r
    if ultima is not None:
        return ultima
    raise errore or httpx.HTTPError("nessuna istanza Overpass")


# Istanze di Overpass (07/11/2026, decisione di Paolo): principale overpass-api.de (FOSSGIS e.V., Germania); riserva
# comune allo strato «Contorni degli edifici» e al ripiego OSM di Modelli 3D: «Overpass API Europa» di Christian Dresel
# (ovp.dresel.systems, Fürth, Germania; dati Europa da Geofabrik, libera, senza chiave, 4 richieste in parallelo per IP),
# al posto di maps.mail.ru (VK). Scelta e alternative nel TOML dello strato e nel README della fase 4.
OVERPASS_PRINCIPALE = "https://overpass-api.de/api/interpreter"
OVERPASS_RISERVA = "https://ovp.dresel.systems/api/interpreter"


def riserva_overpass(s: "Strato | None" = None) -> list[str]:
    """Istanze di riserva: OVERPASS_RISERVA del .env se c'è (anche vuota = nessuna riserva, per esempio se dal server la
    riserva non risponde: il ripiego dirà che OpenStreetMap non risponde), altrimenti url_riserva del TOML dello strato,
    altrimenti la riserva predefinita."""
    if C.OVERPASS_RISERVA is not None:
        return [u for u in C.OVERPASS_RISERVA if not O.ESCLUSI.search(u)]
    if s is not None:
        return list(s.url_riserva)
    return [OVERPASS_RISERVA]


def _overpass(s: "Strato", query: str) -> httpx.Response:
    """Istanza principale dello strato e poi quelle di riserva (riserva_overpass)."""
    return chiedi_overpass((s.url, *riserva_overpass(s)), query, "json", nome=f"Strato {s.id}")


def istanze_overpass() -> list[str]:
    """Istanze di Overpass dello strato OSM dei TOML (anche se lo strato è spento: la fonte è la stessa), con la riserva
    comune."""
    for s in strati().values():
        if s.tipo == "overpass":
            return [s.url, *riserva_overpass(s)]
    return [OVERPASS_PRINCIPALE, *riserva_overpass()]


@router.get("")
def elenco(request: Request):
    P.limita(request, "dati")
    accesi = sorted((s for s in strati().values() if s.accesa()), key=lambda s: (s.tema, 0 if s.regioni else 1, s.id))
    return {"strati": [s.pubblica() for s in accesi],
            "nota": "Strati trasparenti sopra le ortofoto, serviti dal server di EuGEnio con la licenza e la citazione "
                    "di ciascuna fonte. Per gli edifici vale lo strato della regione, se c'è; altrove OpenStreetMap."}


@router.get("/{sid}/{z}/{x}/{y}.{ext}")
def tessera(request: Request, sid: str, z: int, x: int, y: int, ext: str):
    s = strati().get(sid)
    if s is None or not s.accesa():
        raise HTTPException(404, "Strato non disponibile")
    if ext != s.estensione or (s.tipo == "overpass" and z != ZOOM_OSM) or not _dentro(s, z, x, y):
        raise HTTPException(404, "Tessera fuori dalla zona o dagli zoom dello strato")
    P.limita(request, "ortofoto")
    p = C.CARTELLA_ORTOFOTO / "strati" / s.id / str(z) / str(x) / f"{y}.{s.estensione}"
    tipo = "application/json" if s.tipo == "overpass" else "image/png"
    dati = O.leggi_copia(p)
    if dati is None:
        fine = time.monotonic() + C.ORTOFOTO_ATTESA_S
        while (attesa := O.ritmo.prova(s)) and time.monotonic() + attesa <= fine:
            time.sleep(attesa)
        if attesa:
            raise HTTPException(503, "Fonte dello strato molto richiesta: riprova tra poco",
                                headers={"Retry-After": str(int(math.ceil(attesa)))})
        try:
            if s.tipo == "overpass":
                r = _overpass(s, query_overpass(z, x, y))
            else:
                r = _scarica(url_wms(s, z, x, y)[0])
        except httpx.HTTPError as e:
            log.warning("Strato %s: fonte non raggiungibile (%s)", s.id, e)
            raise HTTPException(502, "La fonte dello strato non risponde")
        ct = r.headers.get("content-type", "").split(";")[0].strip()
        if r.status_code != 200 or not (ct.startswith("image/") or (s.tipo == "overpass" and "json" in ct)):
            log.warning("Strato %s: risposta %s %s", s.id, r.status_code, ct)
            raise HTTPException(502, "La fonte dello strato ha risposto con un errore")
        try:
            if s.tipo == "overpass":
                dati = json.dumps(geojson_da_overpass(r.json()), separators=(",", ":")).encode()
            else:
                dati = elabora(s, r.content, z, x, y)
        except Exception as e:   # noqa: BLE001 - immagine o JSON illeggibile
            log.warning("Strato %s: risposta non leggibile (%s)", s.id, e)
            raise HTTPException(502, "La fonte dello strato ha risposto con dati non leggibili")
        try:
            O.scrivi_copia(p, dati)
            O.pulisci()
        except OSError as e:
            log.warning("Strato %s: copia non scritta (%s)", s.id, e)
    h = {"Cache-Control": f"public, max-age={C.ORTOFOTO_CACHE_S}",
         "ETag": '"' + hashlib.sha1(dati).hexdigest()[:20] + '"',
         "X-Strato": s.id, "X-Strato-Licenza": s.licenza.encode("ascii", "replace").decode()}
    if request.headers.get("if-none-match") == h["ETag"]:
        return Response(status_code=304, headers=h)
    return Response(dati, media_type=tipo, headers=h)
