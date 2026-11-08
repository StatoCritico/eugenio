"""Proxy delle ortofoto con copia su disco (fase 10, Fase B, § 6 della proposta).

Le fonti stanno nei TOML di `fase10-edifici3d/ortofoto/` (uno per regione, cartella ORTOFOTO_FONTI): per ognuna URL,
strato, licenza, citazione, stato («confermata», «da confermare», «spenta»), copia sì/no, zoom, riquadro e ritmo.

Rotte:
  GET /api/ortofoto/fonti                      elenco delle fonti accese, con licenza, citazione e stato (per la pagina)
  GET /api/ortofoto/{fonte}/{z}/{x}/{y}.jpg    tessera 256×256 in web mercator (EPSG:3857), numerazione XYZ
      ?de=<m>&dn=<m>                           (08/11/2026) ortofoto spostata di de metri verso est e dn verso nord
                                               rispetto alla cartografia (interi, da -20 a 20; solo fonti WMS): si chiede
                                               alla fonte il BBOX spostato, nessuna copia su disco (vedi `bbox_spostato`)

Regole:
  * **disattivabile per fonte**: `attiva = false` o `stato = "spenta"` nel TOML, oppure ORTOFOTO_SPENTE=id1,id2 nel .env
    (vale subito dopo il riavvio dell'api, senza toccare i TOML); con ORTOFOTO_SOLO_CONFERMATE=true si servono solo
    le fonti «confermata» (per esempio per spegnere la RER finché la Regione non risponde);
  * **copia su disco** (CARTELLA_ORTOFOTO/<fonte>/<z>/<x>/<y>.<ext>) solo per le fonti con `cache = true`; le altre
    (WMS del Geoportale Nazionale) passano dal vivo senza copia. La copia vale ORTOFOTO_GIORNI giorni, poi si richiede;
    se la cartella supera ORTOFOTO_MAX_GB si cancellano le tessere più vecchie (pulizia ogni ora al più);
  * **ritmo verso la fonte** per tutti gli utenti insieme: al massimo `ritmo.al_secondo` chiamate al secondo e
    `ritmo.all_ora` all'ora (dal TOML); una richiesta aspetta il suo turno al più ORTOFOTO_ATTESA_S secondi, poi 503 con
    Retry-After; le tessere già in copia non contano;
  * **limite per indirizzo**: tipo «ortofoto» di protezione.py (ORTOFOTO_ORA tessere all'ora per IP);
  * **intestazioni**: Cache-Control public (ORTOFOTO_CACHE_S, così anche Cloudflare tiene la copia), ETag, X-Ortofoto-Fonte,
    X-Ortofoto-Licenza; fuori dal riquadro o dagli zoom della fonte 404 senza chiamare la fonte;
  * nessuna immagine Google, Esri, Bing, EOX 2018+, AGEA infrarosso o WMS regionali AGEA: il proxy serve **solo** le
    fonti dei TOML e rifiuta all'avvio quelle con URL di quei servizi (elenco ESCLUSI).
"""
from __future__ import annotations

import hashlib
import logging
import math
import os
import re
import threading
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, Response

from . import config as C, protezione as P

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ortofoto")

STATI = ("confermata", "da confermare", "spenta")
# servizi esclusi dalla decisione del § 6: un TOML che li usa viene scartato all'avvio
ESCLUSI = re.compile(r"(?i)(google|gstatic|arcgisonline|esri|virtualearth|bing\.|"
                     r"s2cloudless-20(1[89]|2\d)|agea.*(irg|nir|infra)|wms/agea)")
ESTENSIONI = {"image/jpeg": "jpg", "image/png": "png"}
R_TERRA = 20037508.342789244
E2_WGS84 = 0.00669437999014          # eccentricità al quadrato dell'ellissoide WGS84 (= GRS80 al decimo di mm)
SPOSTAMENTO_MAX_M = 20               # spostamento manuale massimo dell'ortofoto per asse (08/11/2026)


@dataclass
class Fonte:
    id: str
    nome: str
    tipo: str
    url: str
    formato: str
    licenza: str
    citazione: str
    scheda: str
    stato: str
    regione: str
    livello: str = ""
    attiva: bool = True
    cache: bool = True
    nei_report: bool = True
    zoom: tuple[int, int] = (0, 20)
    riquadro: tuple[float, float, float, float] = (-180.0, -85.0, 180.0, 85.0)
    al_secondo: float = 4.0
    all_ora: int = 6000
    priorita: int = 5
    # (07/11/2026 sera, Brisighella) zone senza dati: la RER 2023-24 in JPEG le dà nere e opache (88 % della tessera
    # allo zoom 13 sulle colline di Brisighella); con `trasparente = true` si chiede PNG con TRANSPARENT=TRUE, il proxy
    # rende JPEG le tessere piene e PNG con la trasparenza quelle con buchi (sotto si vede il contesto)
    trasparente: bool = False
    _istanti: list = field(default_factory=list, repr=False)

    @property
    def estensione(self) -> str:
        return ESTENSIONI.get(self.formato, "jpg")

    def accesa(self) -> bool:
        if not self.attiva or self.stato == "spenta" or self.id in C.ORTOFOTO_SPENTE:
            return False
        return not (C.ORTOFOTO_SOLO_CONFERMATE and self.stato != "confermata")

    def pubblica(self) -> dict:
        return {"id": self.id, "nome": self.nome, "licenza": self.licenza, "citazione": self.citazione,
                "scheda": self.scheda, "stato": self.stato, "regione": self.regione, "copia": self.cache,
                "nei_report": self.nei_report, "zoom": list(self.zoom), "riquadro": list(self.riquadro),
                "priorita": self.priorita, "formato": self.formato,
                # (08/11/2026) le frecce sotto la mappa spostano l'ortofoto di 1 m: solo le fonti WMS (BBOX spostato)
                "spostabile": self.tipo == "wms", "spostamento_max": SPOSTAMENTO_MAX_M if self.tipo == "wms" else 0,
                "tessere": f"/api/ortofoto/{self.id}/{{z}}/{{x}}/{{y}}.{self.estensione}" + ("?t=1" if self.trasparente else "")}


def leggi_toml(file: Path) -> list[Fonte]:
    d = tomllib.loads(file.read_text(encoding="utf-8"))
    out = []
    for f in d.get("fonte", []):
        ritmo = f.get("ritmo", {})
        stato = str(f.get("stato", "da confermare")).strip().lower()
        if stato not in STATI:
            raise ValueError(f"{file.name}: stato «{stato}» non valido per {f.get('id')} (ammessi: {', '.join(STATI)})")
        if ESCLUSI.search(str(f.get("url", ""))):
            raise ValueError(f"{file.name}: la fonte {f.get('id')} usa un servizio escluso (§ 6 della proposta)")
        if f.get("tipo") not in ("wms", "xyz"):
            raise ValueError(f"{file.name}: tipo «{f.get('tipo')}» non valido per {f.get('id')} (wms o xyz)")
        if not re.fullmatch(r"[a-z0-9_]{2,40}", str(f.get("id", ""))):
            raise ValueError(f"{file.name}: id «{f.get('id')}» non valido (minuscole, cifre e _)")
        out.append(Fonte(id=f["id"], nome=f.get("nome", f["id"]), tipo=f["tipo"], url=f["url"],
                         formato=f.get("formato", "image/jpeg"), licenza=f.get("licenza", ""),
                         citazione=f.get("citazione", ""), scheda=f.get("scheda", ""), stato=stato,
                         regione=str(d.get("regione", "")), livello=f.get("livello", ""),
                         attiva=bool(f.get("attiva", True)), cache=bool(f.get("cache", True)),
                         nei_report=bool(f.get("nei_report", True)), zoom=tuple(f.get("zoom", (0, 20))),
                         riquadro=tuple(f.get("riquadro", (-180, -85, 180, 85))),
                         al_secondo=float(ritmo.get("al_secondo", 4)), all_ora=int(ritmo.get("all_ora", 6000)),
                         priorita=int(f.get("priorita", 5)), trasparente=bool(f.get("trasparente", False))))
    return out


_fonti: dict[str, Fonte] | None = None
_blocco = threading.Lock()


def fonti(ricarica: bool = False) -> dict[str, Fonte]:
    """Tutte le fonti dei TOML (anche spente), per id. Un TOML sbagliato si salta con un avviso nel registro."""
    global _fonti
    with _blocco:
        if _fonti is None or ricarica:
            tutte: dict[str, Fonte] = {}
            cartella = C.ORTOFOTO_FONTI
            for file in sorted(cartella.glob("*.toml")) if cartella.exists() else []:
                try:
                    for f in leggi_toml(file):
                        tutte[f.id] = f
                except (ValueError, KeyError, tomllib.TOMLDecodeError) as e:
                    log.warning("Ortofoto: %s scartato: %s", file.name, e)
            _fonti = tutte
        return _fonti


# ---------------------------------------------------------------------------------------------- geometria delle tessere
def limiti_tessera(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """(ovest, sud, est, nord) in EPSG:3857 della tessera XYZ."""
    t = 2 * R_TERRA / 2 ** z
    return -R_TERRA + x * t, R_TERRA - (y + 1) * t, -R_TERRA + (x + 1) * t, R_TERRA - y * t


def lonlat_tessera(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """(lon_min, lat_min, lon_max, lat_max) della tessera."""
    n = 2 ** z
    lon = lambda i: i / n * 360 - 180
    lat = lambda j: math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * j / n))))
    return lon(x), lat(y + 1), lon(x + 1), lat(y)


def dentro(f: Fonte, z: int, x: int, y: int) -> bool:
    if not (f.zoom[0] <= z <= f.zoom[1]) or not (0 <= x < 2 ** z and 0 <= y < 2 ** z):
        return False
    a, b, c, d = lonlat_tessera(z, x, y)
    r = f.riquadro
    return not (c < r[0] or a > r[2] or d < r[1] or b > r[3])


def scala_mercatore(lat: float) -> tuple[float, float]:
    """Unità di EPSG:3857 per metro di terreno verso est e verso nord alla latitudine `lat` (gradi, ellissoide WGS84).
    Web mercator usa le coordinate geodetiche su una sfera di raggio a: x = a·λ, y = a·ln tan(π/4 + φ/2); un metro sul
    terreno vale a/(N·cos φ) unità verso est e a/(M·cos φ) verso nord (N, M raggi di curvatura del primo verticale e
    del meridiano). A 44° N circa 1,388 e 1,393."""
    p = math.radians(lat)
    w = 1 - E2_WGS84 * math.sin(p) ** 2
    return math.sqrt(w) / math.cos(p), w ** 1.5 / ((1 - E2_WGS84) * math.cos(p))


def bbox_spostato(z: int, x: int, y: int, de: int = 0, dn: int = 0) -> tuple[float, float, float, float]:
    """BBOX in EPSG:3857 da chiedere alla fonte perché la foto appaia spostata di `de` m verso est e `dn` m verso nord
    rispetto alla cartografia (08/11/2026, frecce sotto la mappa). Il contenuto che deve comparire nella tessera è quello
    che sta `de` m a ovest e `dn` m a sud: si chiede alla fonte il riquadro della tessera spostato di (−de, −dn) metri.
    Le richieste WMS sono già in EPSG:3857 (la proiezione delle tessere): lo spostamento è esatto in metri (scala locale
    dell'ellissoide al centro della tessera; scarto < 1 cm sui 20 m anche allo zoom 12) e l'immagine non si riproietta."""
    w, s, e, n = limiti_tessera(z, x, y)
    if not (de or dn):
        return w, s, e, n
    lat = math.degrees(math.atan(math.sinh(((s + n) / 2) / 6378137.0)))
    ke, kn = scala_mercatore(lat)
    dx, dy = -de * ke, -dn * kn
    return w + dx, s + dy, e + dx, n + dy


def url_tessera(f: Fonte, z: int, x: int, y: int, de: int = 0, dn: int = 0) -> str:
    if f.tipo == "xyz":
        return f.url.replace("{z}", str(z)).replace("{x}", str(x)).replace("{y}", str(y))
    w, s, e, n = bbox_spostato(z, x, y, de, dn)
    sep = "&" if "?" in f.url else "?"
    return (f"{f.url}{sep}SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS={f.livello}&STYLES=&CRS=EPSG:3857"
            f"&BBOX={w:.3f},{s:.3f},{e:.3f},{n:.3f}&WIDTH=256&HEIGHT=256&FORMAT="
            + ("image/png&TRANSPARENT=TRUE" if f.trasparente else f.formato))


def senza_buchi(dati: bytes) -> tuple[bytes, str]:
    """Tessera PNG con trasparenza (fonte `trasparente`) → JPEG se è tutta piena (più leggera), altrimenti PNG RGBA con le
    zone senza dati trasparenti. Restituisce (dati, tipo)."""
    import io
    import numpy as np
    from PIL import Image
    im = Image.open(io.BytesIO(dati))
    im = im.convert("RGBA")
    a = np.asarray(im)
    out = io.BytesIO()
    if int(a[..., 3].min()) == 255:
        im.convert("RGB").save(out, "JPEG", quality=88)
        return out.getvalue(), "image/jpeg"
    im.save(out, "PNG", optimize=True)
    return out.getvalue(), "image/png"


def tipo_di(dati: bytes, predefinito: str) -> str:
    """Tipo di una tessera in copia dai primi byte (le fonti `trasparente` mettono JPEG e PNG nello stesso file .jpg)."""
    if dati[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if dati[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    return predefinito


# ---------------------------------------------------------------------------------------------- ritmo verso la fonte
class Ritmo:
    """Ritmo per fonte, per tutti gli utenti insieme: finestra di un secondo e finestra di un'ora."""

    def __init__(self):
        self._b = threading.Lock()
        self._sec: dict[str, list[float]] = {}
        self._ora: dict[str, list[float]] = {}

    def prova(self, f: Fonte, ora: float | None = None) -> float:
        """0 se si può chiamare (e conta la chiamata), altrimenti i secondi da aspettare."""
        t = time.monotonic() if ora is None else ora
        with self._b:
            s = [x for x in self._sec.get(f.id, []) if t - x < 1.0]
            h = [x for x in self._ora.get(f.id, []) if t - x < 3600.0]
            self._sec[f.id], self._ora[f.id] = s, h
            if len(h) >= f.all_ora:
                return max(1.0, 3600.0 - (t - h[0]))
            if len(s) >= max(1, int(f.al_secondo)):
                return max(0.05, 1.0 - (t - s[0]))
            s.append(t)
            h.append(t)
            return 0.0

    def svuota(self):
        with self._b:
            self._sec.clear()
            self._ora.clear()


ritmo = Ritmo()


# ---------------------------------------------------------------------------------------------- copia su disco
def file_copia(f: Fonte, z: int, x: int, y: int) -> Path:
    # fonti `trasparente`: cartella nuova `<id>_t`, così le tessere nere copiate prima del 07/11/2026 sera non si usano
    # più (la cartella vecchia si può cancellare: passo J dell'aggiornamento)
    return C.CARTELLA_ORTOFOTO / (f"{f.id}_t" if f.trasparente else f.id) / str(z) / str(x) / f"{y}.{f.estensione}"


def leggi_copia(p: Path) -> bytes | None:
    try:
        st = p.stat()
    except FileNotFoundError:
        return None
    if time.time() - st.st_mtime > C.ORTOFOTO_GIORNI * 86400:
        return None
    return p.read_bytes()


def scrivi_copia(p: Path, dati: bytes) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + f".{os.getpid()}.tmp")
    tmp.write_bytes(dati)
    tmp.replace(p)


_ultima_pulizia = 0.0


def pulisci(forza: bool = False) -> int:
    """Se la copia supera ORTOFOTO_MAX_GB toglie le tessere più vecchie fino all'80 %. Restituisce i file tolti."""
    global _ultima_pulizia
    if not forza and time.time() - _ultima_pulizia < 3600:
        return 0
    _ultima_pulizia = time.time()
    radice = C.CARTELLA_ORTOFOTO
    if not radice.exists():
        return 0
    tutti = [(p.stat().st_mtime, p.stat().st_size, p) for p in radice.rglob("*.*") if p.is_file()]
    totale, tetto = sum(s for _, s, _ in tutti), C.ORTOFOTO_MAX_GB * 1e9
    if totale <= tetto:
        return 0
    tolti = 0
    for _, s, p in sorted(tutti):
        if totale <= 0.8 * tetto:
            break
        p.unlink(missing_ok=True)
        totale -= s
        tolti += 1
    log.info("Ortofoto: tolte %d tessere vecchie dalla copia", tolti)
    return tolti


def _scarica(url: str) -> httpx.Response:
    with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": "EuGEnio/1.0 (+https://eugenio.statocritico.it)"}) as c:
        return c.get(url)


def _intestazioni(f: Fonte, dati: bytes, copia: str) -> dict[str, str]:
    h = {"Cache-Control": f"public, max-age={C.ORTOFOTO_CACHE_S}" if f.cache else "no-store",
         "ETag": '"' + hashlib.sha1(dati).hexdigest()[:20] + '"',
         "X-Ortofoto-Fonte": f.id, "X-Ortofoto-Licenza": f.licenza.encode("ascii", "replace").decode(),
         "X-Ortofoto-Copia": copia, "Access-Control-Expose-Headers": "X-Ortofoto-Fonte, X-Ortofoto-Licenza"}
    return h


# ---------------------------------------------------------------------------------------------- rotte
@router.get("/fonti")
def elenco(request: Request):
    P.limita(request, "dati")
    accese = sorted((f for f in fonti().values() if f.accesa()), key=lambda f: (f.priorita, f.id))
    return {"fonti": [f.pubblica() for f in accese],
            "nota": "Ortofoto servite dal server di EuGEnio con la licenza e la citazione di ciascuna fonte. "
                    "Nei report ogni figura con ortofoto riporta la sua licenza e la sua citazione."}


@router.get("/{fonte}/{z}/{x}/{y}.{ext}")
def tessera(request: Request, fonte: str, z: int, x: int, y: int, ext: str,
            de: int = Query(0, ge=-SPOSTAMENTO_MAX_M, le=SPOSTAMENTO_MAX_M, description="metri verso est (ortofoto spostata)"),
            dn: int = Query(0, ge=-SPOSTAMENTO_MAX_M, le=SPOSTAMENTO_MAX_M, description="metri verso nord (ortofoto spostata)")):
    f = fonti().get(fonte)
    if f is None or not f.accesa():
        raise HTTPException(404, "Fonte di ortofoto non disponibile")
    if ext != f.estensione or not dentro(f, z, x, y):
        raise HTTPException(404, "Tessera fuori dalla zona o dagli zoom della fonte")
    spostata = bool(de or dn)
    if spostata and f.tipo != "wms":
        raise HTTPException(400, "Spostamento dell'ortofoto possibile solo per le fonti WMS (non per le tessere già pronte)")
    P.limita(request, "ortofoto")
    p = file_copia(f, z, x, y)
    # (08/11/2026) tessere spostate: mai copia su disco. Ogni passo da 1 m è un'altra serie di tessere, quasi uguali a
    # quelle normali e usate da una sola persona per pochi minuti: copiarle riempirebbe ORTOFOTO_MAX_GB e la pulizia
    # toglierebbe per prime le tessere normali più vecchie, che servono a tutti. Restano la copia del browser (un giorno)
    # e il ritmo verso la fonte, come per le altre.
    copia = f.cache and not spostata
    if copia:
        dati = leggi_copia(p)
        if dati is not None:
            h = _intestazioni(f, dati, "si")
            if request.headers.get("if-none-match") == h["ETag"]:
                return Response(status_code=304, headers=h)
            return Response(dati, media_type=tipo_di(dati, f.formato), headers=h)
    # una mappa chiede 15–30 tessere insieme: si aspetta il proprio turno per qualche secondo, poi 503
    fine = time.monotonic() + C.ORTOFOTO_ATTESA_S
    while (attesa := ritmo.prova(f)) and time.monotonic() + attesa <= fine:
        time.sleep(attesa)
    if attesa:
        raise HTTPException(503, "Fonte delle ortofoto molto richiesta: riprova tra poco",
                            headers={"Retry-After": str(int(math.ceil(attesa)))})
    try:
        r = _scarica(url_tessera(f, z, x, y, de, dn))
    except httpx.HTTPError as e:
        log.warning("Ortofoto %s: fonte non raggiungibile (%s)", f.id, e)
        raise HTTPException(502, "La fonte delle ortofoto non risponde")
    tipo = r.headers.get("content-type", "").split(";")[0].strip()
    if r.status_code == 404 and f.tipo == "xyz":
        raise HTTPException(404, "Tessera non disponibile nella fonte")
    if r.status_code != 200 or not tipo.startswith("image/"):
        # i WMS rispondono 200 con un XML di errore (ServiceException): non si copia
        log.warning("Ortofoto %s: risposta %s %s", f.id, r.status_code, tipo)
        raise HTTPException(502, "La fonte delle ortofoto ha risposto con un errore")
    dati = r.content
    if f.trasparente:
        try:
            dati, tipo = senza_buchi(dati)
        except (OSError, ValueError) as e:      # immagine illeggibile: non si copia
            log.warning("Ortofoto %s: tessera illeggibile (%s)", f.id, e)
            raise HTTPException(502, "La fonte delle ortofoto ha risposto con un'immagine illeggibile")
    if copia:
        try:
            scrivi_copia(p, dati)
            pulisci()
        except OSError as e:
            log.warning("Ortofoto %s: copia non scritta (%s)", f.id, e)
    h = _intestazioni(f, dati, "nuova" if copia else "no")
    if spostata:
        h["X-Ortofoto-Spostamento"] = f"de={de}; dn={dn}"
        if f.cache:     # copia del browser e di Cloudflare più breve: tessere usate per poco
            h["Cache-Control"] = f"public, max-age={min(C.ORTOFOTO_CACHE_S, 86400)}"
    return Response(dati, media_type=tipo, headers=h)
