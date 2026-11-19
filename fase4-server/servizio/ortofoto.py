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
  * **limite per indirizzo** (09/11/2026): solo le tessere chieste davvero alla fonte contano nel tipo «ortofoto» di
    protezione.py (ORTOFOTO_ORA all'ora per IP); quelle servite dalla copia su disco contano nel tetto anti-abuso
    «tessere_copia» (TESSERE_COPIA_ORA, comune con strati e terreno). Il 429 porta Retry-After e X-EuGEnio-Limite: la
    pagina ferma le richieste di quella fonte e lo dice sotto la mappa (protezione.js);
  * **intestazioni**: Cache-Control public (ORTOFOTO_CACHE_S, così anche Cloudflare tiene la copia; per le fonti senza copia
    «private, max-age=86400», solo il browser, dal 09/11/2026), ETag, X-Ortofoto-Fonte,
    X-Ortofoto-Licenza; fuori dal riquadro o dagli zoom della fonte 404 senza chiamare la fonte;
  * nessuna immagine Google, Esri, Bing, EOX 2018+, AGEA infrarosso o WMS regionali AGEA: il proxy serve **solo** le
    fonti dei TOML e rifiuta all'avvio quelle con URL di quei servizi (elenco ESCLUSI);
  * **errori della fonte** (09/11/2026 c, prove P9 di Paolo: decine di «502 Bad Gateway» di AGEA 2012 in Console e
    l'ortofoto che arrivava «a pezzi»): la rotta è asincrona (l'attesa del turno e la chiamata alla fonte non tengono
    occupato un thread: prima con 40 thread tutti fermi ad aspettare, le richieste in coda superavano i 30 s di Caddy, che
    rispondeva 502), la chiamata alla fonte dura al più ORTOFOTO_TIMEOUT_S, al più `2 × ritmo.al_secondo` chiamate in
    volo per fonte. Un errore della fonte (timeout, rete, 5xx, XML di errore), o il turno non arrivato in tempo, dà una
    **tessera vuota pulita**: 200, PNG trasparente, `Cache-Control: no-store` (mai in copia: né server, né Cloudflare, né
    browser), `X-Ortofoto-Errore: fonte|occupata|ferma` e `Retry-After`. Nessuna riga rossa in Console; la pagina conta
    questi errori e, se si ripetono, ferma la fonte e lo scrive sotto la mappa (protezione.js). Dopo GUASTI_SOGLIA errori
    di fila in GUASTI_FINESTRA_S secondi senza una risposta buona la fonte è **ferma** per GUASTI_PAUSA_S secondi: in quel
    tempo le tessere nuove rispondono subito vuote con `X-Ortofoto-Errore: ferma`, senza chiamare la fonte.
  * **fonti con più anni** (17/11/2026, ortofoto AGEA 2022-2024 del Geoportale AGEA, `tipo = "arcgis"` e `anni`): ogni
    anno AGEA vola circa un terzo d'Italia e il servizio di quell'anno dà una tessera trasparente (PNG di 876 byte) dove
    non ha volato. Per ogni tessera il proxy chiede prima l'anno più recente; se non riempie la tessera chiede **insieme**
    gli altri e compone: sopra l'anno più recente, nei buchi (confini tra regioni volate in anni diversi) l'anno
    precedente, e così via (un errore di un anno che non serve non conta). La tessera
    composta va in copia con accanto un file `.anno` con gli anni usati, ed esce con `X-Ortofoto-Anno: 2023` (o
    `2023,2022` sui confini): la pagina li raccoglie (protezione.js) e la citazione dice l'anno vero della vista. Per non
    chiedere a vuoto, gli anni che hanno dato una tessera tutta trasparente a uno zoom ≥ 10 non si chiedono più per le
    tessere figlie fino a 4 livelli sotto (memoria `_vuote_anno`). Fino allo zoom `zoom_tessere` (18) si usano le
    tessere già pronte del servizio (`/tile/{z}/{y}/{x}`, ~0,5 s); oltre, `exportImage` sul riquadro della tessera.
  * **scacchiere** (19/11/2026, segnalazione di Paolo): l'`exportImage` del Geoportale AGEA risponde 200 con una
    scacchiera bianca e nera al posto della foto (tutti gli anni, tutta Italia). La fonte `agea` ora arriva solo allo zoom
    18 (tessere già pronte) e una tessera a scacchiera (`scacchiera`) di qualunque fonte vale come errore della fonte: non
    si copia e la pagina vede una tessera vuota.
"""
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import inspect
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
TIPI = ("wms", "xyz", "arcgis")
ESPONI = "X-Ortofoto-Fonte, X-Ortofoto-Licenza, X-Ortofoto-Vuota, X-Ortofoto-Errore, X-Ortofoto-Anno, Retry-After"
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
    # (09/11/2026 b) fuori dalla sua regione la WMS della Toscana risponde 200 con un JPEG bianco di ~1,7 kB e la scritta
    # «Fonte dei dati: Regione Toscana – Base informativa territoriale…» (a Bagno di Romagna, Cesena, Bologna, La Spezia,
    # Perugia: dentro il riquadro della fonte). Con `segnaposto = true` queste tessere diventano vuote (PNG trasparente
    # con X-Ortofoto-Vuota: 1), come quelle della RER senza immagini: la pagina passa da sola alla fonte successiva
    segnaposto: bool = False
    # (17/11/2026) fonti con più anni (AGEA 2022-2024): `{anno}` nell'URL, anni dal più recente; la citazione può
    # contenere `{anni}` (sostituito con gli anni usati nella vista; nell'elenco «2022-2024»)
    anni: tuple[int, ...] = ()
    zoom_tessere: int = 18             # tipo «arcgis»: tessere già pronte fino a questo zoom, oltre exportImage
    _istanti: list = field(default_factory=list, repr=False)

    @property
    def estensione(self) -> str:
        return ESTENSIONI.get(self.formato, "jpg")

    def accesa(self) -> bool:
        if not self.attiva or self.stato == "spenta" or self.id in C.ORTOFOTO_SPENTE:
            return False
        return not (C.ORTOFOTO_SOLO_CONFERMATE and self.stato != "confermata")

    @property
    def citazione_generica(self) -> str:
        """Citazione senza segnaposto: con più anni «2022-2024» (la pagina mette gli anni veri della vista)."""
        if "{anni}" not in self.citazione:
            return self.citazione
        return self.citazione.replace("{anni}", testo_anni(self.anni, intervallo=True))

    def pubblica(self) -> dict:
        d = self._pubblica()
        if self.anni:
            d["anni"] = list(self.anni)
            d["citazione_anni"] = self.citazione    # con «{anni}»: la pagina lo sostituisce con gli anni della vista
        return d

    def _pubblica(self) -> dict:
        return {"id": self.id, "nome": self.nome, "licenza": self.licenza, "citazione": self.citazione_generica,
                "scheda": self.scheda, "stato": self.stato, "regione": self.regione, "copia": self.cache,
                "nei_report": self.nei_report, "zoom": list(self.zoom), "riquadro": list(self.riquadro),
                "priorita": self.priorita, "formato": self.formato,
                # (08/11/2026) le frecce sotto la mappa spostano l'ortofoto di 1 m: solo le fonti WMS (BBOX spostato)
                "spostabile": self.tipo == "wms", "spostamento_max": SPOSTAMENTO_MAX_M if self.tipo == "wms" else 0,
                # «?t=1» (trasparente) e «?s=1» (segnaposto, 09/11/2026 b): indirizzi nuovi, così browser e Cloudflare non
                # usano le tessere copiate prima (nere, o bianche con la scritta)
                "tessere": f"/api/ortofoto/{self.id}/{{z}}/{{x}}/{{y}}.{self.estensione}"
                           + ("?t=1" if self.trasparente else "?s=1" if self.segnaposto else "")}


def testo_anni(anni, intervallo: bool = False) -> str:
    """[2023] → «2023»; [2023, 2022] → «2022 e 2023»; con `intervallo` e più di due anni «2022-2024»."""
    a = sorted({int(x) for x in anni})
    if not a:
        return ""
    if intervallo and len(a) > 2 and a == list(range(a[0], a[-1] + 1)):
        return f"{a[0]}-{a[-1]}"
    if len(a) == 1:
        return str(a[0])
    return ", ".join(map(str, a[:-1])) + " e " + str(a[-1])


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
        if f.get("tipo") not in TIPI:
            raise ValueError(f"{file.name}: tipo «{f.get('tipo')}» non valido per {f.get('id')} (wms, xyz o arcgis)")
        anni = tuple(sorted({int(a) for a in f.get("anni", [])}, reverse=True))
        if ("{anno}" in str(f.get("url", ""))) != bool(anni):
            raise ValueError(f"{file.name}: la fonte {f.get('id')} deve avere sia «{{anno}}» nell'URL sia l'elenco anni")
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
                         priorita=int(f.get("priorita", 5)), trasparente=bool(f.get("trasparente", False)),
                         segnaposto=bool(f.get("segnaposto", False)), anni=anni,
                         zoom_tessere=int(f.get("zoom_tessere", 18))))
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


def url_tessera(f: Fonte, z: int, x: int, y: int, de: int = 0, dn: int = 0, anno: int | None = None) -> str:
    if f.tipo == "xyz":
        return f.url.replace("{z}", str(z)).replace("{x}", str(x)).replace("{y}", str(y))
    if f.tipo == "arcgis":
        # ImageServer di ArcGIS (Geoportale AGEA): tessere già pronte fino a zoom_tessere, oltre exportImage sul riquadro
        base = f.url.replace("{anno}", str(anno if anno is not None else (f.anni[0] if f.anni else ""))).rstrip("/")
        if z <= f.zoom_tessere:
            return f"{base}/tile/{z}/{y}/{x}"
        w, s, e, n = limiti_tessera(z, x, y)
        return (f"{base}/exportImage?bbox={w:.3f},{s:.3f},{e:.3f},{n:.3f}&bboxSR=3857&imageSR=3857&size=256,256"
                f"&format=jpgpng&compressionQuality=85&f=image")
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


def scacchiera(dati: bytes) -> bool:
    """Immagine segnaposto a scacchiera bianca e nera (19/11/2026: exportImage del Geoportale AGEA): quasi tutti i pixel
    grigi neutri, molto chiari o molto scuri, con tutti e due i colori ben presenti. Una foto vera non è mai così."""
    try:
        import io
        import numpy as np
        from PIL import Image
        a = np.asarray(Image.open(io.BytesIO(dati)).convert("RGB")).astype(np.int16)
    except (OSError, ValueError):
        return False
    if a.size == 0:
        return False
    neutri = (np.abs(a[..., 0] - a[..., 1]) + np.abs(a[..., 1] - a[..., 2])) < 12
    luce = a.mean(axis=2)
    bianchi, neri = (neutri & (luce > 225)).mean(), (neutri & (luce < 30)).mean()
    return bianchi + neri > 0.8 and min(bianchi, neri) > 0.2


def vuota(dati: bytes) -> bool:
    """Tessera PNG tutta trasparente (zona senza dati della fonte, 09/11/2026: la RER 2023-24 non ha immagini a Bologna,
    Modena, Parma, Imola, Ferrara, Faenza, Bagno di Romagna, Comacchio). Le tessere vuote sono PNG di poche centinaia di
    byte: le altre non si decodificano."""
    if dati[:8] != b"\x89PNG\r\n\x1a\n" or len(dati) > 4000:
        return False
    try:
        import io
        import numpy as np
        from PIL import Image
        a = np.asarray(Image.open(io.BytesIO(dati)).convert("RGBA"))
        return int(a[..., 3].max()) == 0
    except (OSError, ValueError):
        return False


_VUOTA_PNG: bytes | None = None


def vuota_png() -> bytes:
    """Tessera PNG 256×256 tutta trasparente (al posto dei segnaposto: sotto si vede il contesto)."""
    global _VUOTA_PNG
    if _VUOTA_PNG is None:
        import io
        from PIL import Image
        b = io.BytesIO()
        Image.new("RGBA", (256, 256), (0, 0, 0, 0)).save(b, "PNG", optimize=True)
        _VUOTA_PNG = b.getvalue()
    return _VUOTA_PNG


def segnaposto_bianco(dati: bytes) -> bool:
    """Tessera «segnaposto» di una WMS fuori dalla sua zona: immagine piccola (≤ 4000 byte: una foto vera di 256×256 pesa
    10–30 kB) quasi tutta bianca (≥ 95 % dei pixel sopra 235 in tutti e tre i canali), anche con una scritta."""
    if len(dati) > 4000 or not (dati[:3] == b"\xff\xd8\xff" or dati[:8] == b"\x89PNG\r\n\x1a\n"):
        return False
    try:
        import io
        import numpy as np
        from PIL import Image
        im = Image.open(io.BytesIO(dati))
        if im.mode in ("RGBA", "LA", "P") and dati[:4] == b"\x89PNG":
            a = np.asarray(im.convert("RGBA"))
            if int(a[..., 3].max()) == 0:
                return False                         # già trasparente: la gestisce vuota()
        a = np.asarray(im.convert("RGB"))
        return float((a > 235).all(axis=2).mean()) >= 0.95
    except (OSError, ValueError):
        return False


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


def file_anno(p: Path) -> Path:
    """Accanto alla tessera in copia di una fonte con più anni: gli anni usati («2023» o «2023,2022»)."""
    return p.with_name(p.name + ".anno")


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


_client: httpx.AsyncClient | None = None


async def _scarica(url: str) -> httpx.Response:
    """Chiamata alla fonte, asincrona (09/11/2026 c): mentre aspetta la fonte non occupa un thread dell'api."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=C.ORTOFOTO_TIMEOUT_S, follow_redirects=True,
                                    headers={"User-Agent": "EuGEnio/1.0 (+https://eugenio.statocritico.it)"},
                                    limits=httpx.Limits(max_connections=64, max_keepalive_connections=16))
    return await _client.get(url)


async def _chiama(url: str) -> httpx.Response:
    """`_scarica` con il tempo massimo; accetta anche una funzione sincrona (i test la sostituiscono)."""
    async def uno():
        r = _scarica(url)
        return await r if inspect.isawaitable(r) else r
    return await asyncio.wait_for(uno(), timeout=C.ORTOFOTO_TIMEOUT_S + 1)


# ---------------------------------------------------------------------------------------------- fonti che non rispondono
GUASTI_SOGLIA = 6          # errori di fila (senza una risposta buona in mezzo)…
GUASTI_FINESTRA_S = 60.0   # …in questi secondi
GUASTI_PAUSA_S = 60.0      # → fonte ferma per questo tempo (raddoppia a ogni nuovo fermo, fino a 5 minuti)
GUASTI_PAUSA_MAX_S = 300.0


class Guasti:
    """Errori recenti per fonte e fermo dopo errori ripetuti (09/11/2026 c), per tutti gli utenti insieme."""

    def __init__(self):
        self._b = threading.Lock()
        self._errori: dict[str, list[float]] = {}
        self._ferma: dict[str, float] = {}
        self._pausa: dict[str, float] = {}

    def ferma_per(self, fid: str, ora: float | None = None) -> float:
        """Secondi di fermo che restano alla fonte (0 se non è ferma)."""
        t = time.monotonic() if ora is None else ora
        with self._b:
            return max(0.0, self._ferma.get(fid, 0.0) - t)

    def errore(self, fid: str, ora: float | None = None) -> float:
        """Conta un errore; restituisce i secondi di fermo se la fonte si ferma ora, altrimenti 0."""
        t = time.monotonic() if ora is None else ora
        with self._b:
            e = [x for x in self._errori.get(fid, []) if t - x < GUASTI_FINESTRA_S] + [t]
            self._errori[fid] = e
            if len(e) < GUASTI_SOGLIA:
                return 0.0
            p = min(GUASTI_PAUSA_MAX_S, self._pausa.get(fid, GUASTI_PAUSA_S / 2) * 2)
            self._pausa[fid], self._ferma[fid], self._errori[fid] = p, t + p, []
            log.warning("Ortofoto %s: %d errori in %d s, fonte ferma per %d s", fid, GUASTI_SOGLIA, GUASTI_FINESTRA_S, p)
            return p

    def buona(self, fid: str) -> None:
        with self._b:
            self._errori.pop(fid, None)
            self._pausa.pop(fid, None)

    def svuota(self):
        with self._b:
            self._errori.clear()
            self._ferma.clear()
            self._pausa.clear()


guasti = Guasti()
_in_volo: dict[tuple[int, str], asyncio.Semaphore] = {}


def _semaforo(f: Fonte) -> asyncio.Semaphore:
    """Chiamate in volo verso la fonte: al più 2 × ritmo.al_secondo (un semaforo per ciclo degli eventi)."""
    k = (id(asyncio.get_running_loop()), f.id)
    s = _in_volo.get(k)
    if s is None:
        s = _in_volo[k] = asyncio.Semaphore(max(2, int(2 * f.al_secondo)))
    return s


def tessera_errore(f: Fonte, motivo: str, riprova: float) -> Response:
    """Tessera vuota «pulita» al posto di un errore della fonte: 200, PNG trasparente, mai in copia. La pagina la
    riconosce da X-Ortofoto-Errore (fonte: la fonte ha risposto male o non ha risposto; occupata: turno non arrivato in
    tempo; ferma: fonte ferma dopo errori ripetuti) e la richiede dopo Retry-After secondi."""
    return Response(vuota_png(), media_type="image/png", headers={
        "Cache-Control": "no-store", "X-Ortofoto-Fonte": f.id, "X-Ortofoto-Errore": motivo,
        "Retry-After": str(max(1, int(math.ceil(riprova)))),
        "Access-Control-Expose-Headers": ESPONI})


def _intestazioni(f: Fonte, dati: bytes, copia: str, anni: str = "") -> dict[str, str]:
    # fonti senza copia (consultazione dal vivo, AGEA 2012 del Geoportale): nessuna copia sul server né su Cloudflare, ma
    # (09/11/2026) la copia privata del browser per un giorno, come qualsiasi visualizzatore WMS: prima «no-store» faceva
    # richiedere alla fonte ogni tessera a ogni ritorno sulla stessa zona
    h = {"Cache-Control": f"public, max-age={C.ORTOFOTO_CACHE_S}" if f.cache else "private, max-age=86400",
         "ETag": '"' + hashlib.sha1(dati).hexdigest()[:20] + '"',
         "X-Ortofoto-Fonte": f.id, "X-Ortofoto-Licenza": f.licenza.encode("ascii", "replace").decode(),
         "X-Ortofoto-Copia": copia,
         "Access-Control-Expose-Headers": ESPONI}
    if (f.trasparente or f.segnaposto or f.anni) and vuota(dati):
        h["X-Ortofoto-Vuota"] = "1"          # la pagina passa da sola a un'altra fonte (09/11/2026)
    if anni:
        h["X-Ortofoto-Anno"] = anni          # (17/11/2026) anni di volo usati nella tessera, dal più recente
    return h


# ---------------------------------------------------------------------------------------------- fonti con più anni
VUOTE_ZOOM_MIN = 10        # tessere tutte trasparenti ricordate da questo zoom in su…
VUOTE_LIVELLI = 4          # …e usate per saltare quell'anno nelle tessere figlie fino a 4 livelli sotto
VUOTE_MAX = 200_000        # tessere ricordate per fonte e anno (oltre si ricomincia)
_vuote_anno: dict[tuple[str, int], set[tuple[int, int, int]]] = {}
_vuote_blocco = threading.Lock()


def anno_vuoto(fid: str, anno: int, z: int, x: int, y: int) -> bool:
    """True se l'anno ha dato una tessera tutta trasparente per un antenato vicino (stesso posto, zoom più basso): lì
    quell'anno non ha volato e non si chiede. Solo antenati entro VUOTE_LIVELLI livelli e da VUOTE_ZOOM_MIN in su: a
    zoom più bassi una striscia stretta di volo può sparire nel ricampionamento."""
    with _vuote_blocco:
        v = _vuote_anno.get((fid, anno))
        if not v:
            return False
        for k in range(1, VUOTE_LIVELLI + 1):
            if z - k < VUOTE_ZOOM_MIN:
                break
            if (z - k, x >> k, y >> k) in v:
                return True
    return False


def segna_vuoto(fid: str, anno: int, z: int, x: int, y: int) -> None:
    if z < VUOTE_ZOOM_MIN:
        return
    with _vuote_blocco:
        v = _vuote_anno.setdefault((fid, anno), set())
        if len(v) >= VUOTE_MAX:
            v.clear()
        v.add((z, x, y))


def svuota_vuote() -> None:
    with _vuote_blocco:
        _vuote_anno.clear()


def componi(pezzi: list[tuple[int, bytes]]) -> tuple[bytes, str, list[int], bool]:
    """Pezzi (anno, immagine) dal più recente, già senza le tessere tutte trasparenti → (dati, tipo, anni usati, piena).
    Sopra l'anno più recente, nei suoi buchi i precedenti. Un JPEG (o un PNG tutto pieno) in testa esce com'è, senza
    ricomprimere. Una tessera composta piena diventa JPEG, con buchi PNG trasparente."""
    import io
    import numpy as np
    from PIL import Image
    if not pezzi:
        return vuota_png(), "image/png", [], False
    anno0, d0 = pezzi[0]
    if d0[:3] == b"\xff\xd8\xff":
        return d0, "image/jpeg", [anno0], True
    immagini, coperto, usati = [], None, []
    for anno, d in pezzi:
        im = Image.open(io.BytesIO(d)).convert("RGBA")
        if im.size != (256, 256):
            im = im.resize((256, 256))
        a = np.asarray(im)[..., 3]
        if coperto is None:
            coperto = np.zeros_like(a)
        if ((a > 0) & (coperto < 255)).any():
            usati.append(anno)
            immagini.append(im)
            coperto = np.maximum(coperto, a)
        if int(coperto.min()) == 255:
            break
    piena = coperto is not None and int(coperto.min()) == 255
    if usati == [anno0]:
        return d0, "image/png", usati, piena      # un solo anno (anche con il mare trasparente): com'è, senza ricomprimere
    out = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    for im in reversed(immagini):                  # dal più vecchio al più recente: il più recente sta sopra
        out = Image.alpha_composite(out, im)
    b = io.BytesIO()
    if piena:
        out.convert("RGB").save(b, "JPEG", quality=88)
        return b.getvalue(), "image/jpeg", usati, True
    out.save(b, "PNG", optimize=True)
    return b.getvalue(), "image/png", usati, False


async def _turno(f: Fonte, fine: float) -> float:
    """Aspetta il turno verso la fonte fino a `fine` (monotonic): 0 se è arrivato, altrimenti i secondi che mancavano."""
    while (attesa := ritmo.prova(f)) and time.monotonic() + attesa <= fine:
        await asyncio.sleep(attesa)
    return attesa


async def _anno(f: Fonte, anno: int, z: int, x: int, y: int, fine: float) -> tuple[int, str, object]:
    """Un anno di una fonte con più anni → (anno, esito, dati o attesa): esito «ok», «vuota», «occupata» o «fonte»."""
    if anno_vuoto(f.id, anno, z, x, y):
        return anno, "vuota", None
    if attesa := await _turno(f, fine):
        return anno, "occupata", attesa
    t0 = time.monotonic()
    try:
        async with _semaforo(f):
            r = await _chiama(url_tessera(f, z, x, y, anno=anno))
    except (httpx.HTTPError, asyncio.TimeoutError, OSError) as e:
        log.warning("Ortofoto %s %s: fonte non raggiungibile (%s dopo %.1f s)", f.id, anno, type(e).__name__,
                    time.monotonic() - t0)
        return anno, "fonte", None
    tipo = r.headers.get("content-type", "").split(";")[0].strip()
    if r.status_code == 404:                # fuori dalla cache dell'anno: lì non ha volato
        segna_vuoto(f.id, anno, z, x, y)
        return anno, "vuota", None
    if r.status_code != 200 or not tipo.startswith("image/"):
        log.warning("Ortofoto %s %s: risposta %s %s dopo %.1f s", f.id, anno, r.status_code, tipo, time.monotonic() - t0)
        return anno, "fonte", None
    if vuota(r.content):
        segna_vuoto(f.id, anno, z, x, y)
        return anno, "vuota", None
    if await asyncio.to_thread(scacchiera, r.content):    # (19/11/2026) segnaposto, non la foto: errore della fonte
        log.warning("Ortofoto %s %s: tessera a scacchiera %s/%s/%s, scartata", f.id, anno, z, x, y)
        return anno, "fonte", None
    return anno, "ok", r.content


async def tessera_anni(f: Fonte, z: int, x: int, y: int) -> tuple[bytes, str, list[int]] | Response:
    """Tessera di una fonte con più anni: prima l'anno più recente da chiedere; se non riempie la tessera, gli altri
    insieme, e si compone. Un errore conta solo se serviva (un anno più recente pieno lo rende inutile)."""
    fine = time.monotonic() + C.ORTOFOTO_ATTESA_S
    da_chiedere = [a for a in f.anni if not anno_vuoto(f.id, a, z, x, y)]
    esiti: list[tuple[int, str, object]] = []
    if da_chiedere:
        primo = await _anno(f, da_chiedere[0], z, x, y, fine)
        esiti.append(primo)
        pieno = primo[1] == "ok" and await asyncio.to_thread(lambda: componi([(primo[0], primo[2])])[3])
        if not pieno and primo[1] in ("ok", "vuota") and len(da_chiedere) > 1:
            esiti += await asyncio.gather(*(_anno(f, a, z, x, y, fine) for a in da_chiedere[1:]))
    pezzi: list[tuple[int, bytes]] = []
    for anno, esito, val in esiti:             # dal più recente
        if esito == "ok":
            pezzi.append((anno, val))
            dati, tipo, usati, piena = await asyncio.to_thread(componi, pezzi)
            if piena:
                guasti.buona(f.id)
                return dati, tipo, usati
        elif esito == "occupata":
            return tessera_errore(f, "occupata", float(val))
        elif esito == "fonte":
            return tessera_errore(f, "fonte", guasti.errore(f.id) or 30)
    guasti.buona(f.id)
    dati, tipo, usati, _ = await asyncio.to_thread(componi, pezzi)
    return dati, tipo, usati


# ---------------------------------------------------------------------------------------------- rotte
@router.get("/fonti")
def elenco(request: Request):
    P.limita(request, "dati")
    accese = sorted((f for f in fonti().values() if f.accesa()), key=lambda f: (f.priorita, f.id))
    return {"fonti": [f.pubblica() for f in accese],
            "nota": "Ortofoto servite dal server di EuGEnio con la licenza e la citazione di ciascuna fonte. "
                    "Nei report ogni figura con ortofoto riporta la sua licenza e la sua citazione."}


@router.get("/{fonte}/{z}/{x}/{y}.{ext}")
async def tessera(request: Request, fonte: str, z: int, x: int, y: int, ext: str,
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
    p = file_copia(f, z, x, y)
    # (08/11/2026) tessere spostate: mai copia su disco. Ogni passo da 1 m è un'altra serie di tessere, quasi uguali a
    # quelle normali e usate da una sola persona per pochi minuti: copiarle riempirebbe ORTOFOTO_MAX_GB e la pulizia
    # toglierebbe per prime le tessere normali più vecchie, che servono a tutti. Restano la copia del browser (un giorno)
    # e il ritmo verso la fonte, come per le altre.
    copia = f.cache and not spostata
    anni = ""
    if copia:
        dati = leggi_copia(p)
        if dati is not None and f.anni:
            try:                                # (17/11/2026) senza il file degli anni la copia non vale
                anni = file_anno(p).read_text(encoding="ascii").strip()
            except (OSError, UnicodeDecodeError):
                dati = None
        if dati is not None and f.anni and z > f.zoom_tessere and await asyncio.to_thread(scacchiera, dati):
            dati = None                         # (19/11/2026) scacchiere di exportImage copiate prima: si richiede
        if dati is not None and f.segnaposto and segnaposto_bianco(dati):
            dati = vuota_png()                  # segnaposto copiati prima del 09/11 b: vuoti anche dalla copia
            with contextlib.suppress(OSError):
                scrivi_copia(p, dati)
        if dati is not None:
            P.limita(request, "tessere_copia")
            h = _intestazioni(f, dati, "si", anni)
            if request.headers.get("if-none-match") == h["ETag"]:
                return Response(status_code=304, headers=h)
            return Response(dati, media_type=tipo_di(dati, f.formato), headers=h)
    # (09/11/2026 c) fonte ferma dopo errori ripetuti: tessera vuota subito, senza chiamarla né contarla nel limite
    if (resta := guasti.ferma_per(f.id)) > 0:
        return tessera_errore(f, "ferma", resta)
    P.limita(request, "ortofoto")                       # tessera da chiedere alla fonte (09/11/2026: solo queste contano)
    if f.anni:                                          # (17/11/2026) AGEA 2022-2024: anno più recente, composto
        esito = await tessera_anni(f, z, x, y)
        if isinstance(esito, Response):
            return esito
        dati, tipo, usati = esito
        anni = ",".join(map(str, usati))
        if copia:
            try:
                scrivi_copia(file_anno(p), anni.encode("ascii"))
                scrivi_copia(p, dati)
                pulisci()
            except OSError as e:
                log.warning("Ortofoto %s: copia non scritta (%s)", f.id, e)
        return Response(dati, media_type=tipo, headers=_intestazioni(f, dati, "nuova" if copia else "no", anni))
    # una mappa chiede 15–30 tessere insieme: si aspetta il proprio turno per qualche secondo (senza occupare un thread)
    if attesa := await _turno(f, time.monotonic() + C.ORTOFOTO_ATTESA_S):
        return tessera_errore(f, "occupata", attesa)
    t0 = time.monotonic()
    try:
        async with _semaforo(f):
            r = await _chiama(url_tessera(f, z, x, y, de, dn))
    except (httpx.HTTPError, asyncio.TimeoutError, OSError) as e:
        # (09/11/2026 d) nel registro anche il tempo: «TimeoutError dopo 18,0 s» = fonte lenta, pochi decimi = rete o rifiuto
        log.warning("Ortofoto %s: fonte non raggiungibile (%s dopo %.1f s)", f.id, type(e).__name__, time.monotonic() - t0)
        return tessera_errore(f, "fonte", guasti.errore(f.id) or 30)
    tipo = r.headers.get("content-type", "").split(";")[0].strip()
    if r.status_code == 404 and f.tipo == "xyz":
        guasti.buona(f.id)                              # la fonte risponde: la tessera non c'è
        raise HTTPException(404, "Tessera non disponibile nella fonte")
    if r.status_code != 200 or not tipo.startswith("image/"):
        # i WMS rispondono 200 con un XML di errore (ServiceException): non si copia
        log.warning("Ortofoto %s: risposta %s %s dopo %.1f s", f.id, r.status_code, tipo, time.monotonic() - t0)
        return tessera_errore(f, "fonte", guasti.errore(f.id) or 30)
    dati = r.content
    if await asyncio.to_thread(scacchiera, dati):      # (19/11/2026) segnaposto a scacchiera: errore, mai in copia
        log.warning("Ortofoto %s: tessera a scacchiera %s/%s/%s, scartata", f.id, z, x, y)
        return tessera_errore(f, "fonte", guasti.errore(f.id) or 30)
    if f.segnaposto and segnaposto_bianco(dati):
        dati, tipo = vuota_png(), "image/png"   # 09/11/2026 b: tessera segnaposto (fuori dalla regione) = vuota
    elif f.trasparente:
        try:
            dati, tipo = await asyncio.to_thread(senza_buchi, dati)
        except (OSError, ValueError) as e:      # immagine illeggibile: non si copia
            log.warning("Ortofoto %s: tessera illeggibile (%s)", f.id, e)
            return tessera_errore(f, "fonte", guasti.errore(f.id) or 30)
    guasti.buona(f.id)
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
