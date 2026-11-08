"""Pipeline notturna degli edifici a tessere (Fase C, § 11 della proposta).

Una zona per file TOML (`zone/<zona>.toml`): tessere, fonti LiDAR con licenza e stato, limiti. Per ogni tessera con
edifici: scarica → elabora (DSM ridotto, falde per corpo) → salva i prodotti → cancella i grezzi → riscrive lo stato.

- **Riprendibile**: lo stato (`<stato>/<zona>.json`) si riscrive a ogni tessera, in modo atomico; una tessera
  interrotta riparte da capo alla notte dopo (lo scaricamento riprende dal pezzo già arrivato) e conta come tentativo.
- **Idempotente**: una tessera fatta si salta finché la versione della sua fonte non cambia; i prodotti sono indicizzati
  per tessera e per corpo, quindi rifare una tessera sovrascrive gli stessi file.
- **Limiti**: finestra oraria (3:30–7:00) e minuti massimi, spazio libero minimo (20 GB), quota di download per notte,
  dimensione massima di una tessera, tentativi massimi (poi la tessera è saltata e segnalata), pausa finché il server
  sta calcolando una previsione (`pausa_url` → `previsioni_in_corso` di /api/salute).
- **Fonti in attesa**: una fonte si usa solo con `attiva = true`, un `url` e `licenza_confermata = true`; le altre
  compaiono nella pagina di stato con il motivo.
- Un corpo a cavallo di due tessere si rielabora quando arriva la tessera vicina, dai DSM ridotti già salvati.
- **Copertura** (05/11/2026): una fonte può dichiarare l'area che copre (`[fonti.<id>.copertura]`: riquadri nel sistema
  della zona e/o una maschera GeoJSON in `zone/coperture/`); una tessera è coperta solo se dentro l'area cade almeno la
  quota `minima` (0,95) dell'area dei suoi edifici (o della tessera, se non ne ha). Fuori, la fonte «non copre» e vince
  la successiva per priorità, come per le tavole che mancano nel quadro di unione.
- **Alberi** (05/11/2026): le chiome del DSM attorno agli edifici diventano quadrati di 2 m in `lidar/alberi/` (ombre
  della pagina 3D). **Corpi dal solo LiDAR** (`corpi_lidar`, comando `lidar-corpi`) per le zone senza sagome.
- **Fonti a più file** (05/11/2026): con `indice` (JSON in `zone/coperture/` con nome e riquadro di ogni file, comando
  `lidar-indice`) l'URL usa `{file}`; per ogni tessera si scaricano i file che la toccano (al più `max_file_tessera`) e
  si uniscono in un mosaico. L'indice dà anche la copertura.

Prodotti (archivio della licenza della fonte, come la Fase A): `<prodotti>/lidar/dsm/<t>.tif`, `dtm/<t>.tif` (int16 in
decimetri), `corpi/<t>.json` (risultati per corpo, sistema della zona), `falde/<i>_<j>.json` (celle di 0,01° in WGS84
lette dalla pagina 3D) e `indice.json` (fonti, licenze, attribuzioni, tessere).
"""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import logging
import math
import os
import re
import shutil
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx
import numpy as np

from . import fonti as F, lidar as L, lidar_corpi as LC, tessere as T

log = logging.getLogger(__name__)
QUI = Path(__file__).resolve().parent.parent
ZONE = QUI / "zone"
TIPI = {"dsm", "las", "dtm"}
NOTTI = 30
GB = 1024 ** 3


# ============================================================================================== zona
def carica_zona(nome: str | Path) -> dict:
    """Legge e controlla il TOML della zona. Gli URL stanno solo nel TOML, mai nel codice."""
    p = Path(nome)
    if not p.suffix:
        p = ZONE / f"{nome}.toml"
    z = tomllib.loads(p.read_text(encoding="utf-8"))
    z["_file"] = str(p)
    zona = z.get("zona") or {}
    for k in ("nome", "codice", "archivio", "crs", "riquadro", "lato_tessera", "nome_tessera"):
        if k not in zona:
            raise ValueError(f"{p.name}: manca zona.{k}")
    if not re.fullmatch(r"[a-z0-9_-]{1,32}", zona["codice"]):
        raise ValueError(f"{p.name}: codice della zona non valido")
    arch = z.get("archivi") or {}
    for k, f in (z.get("fonti") or {}).items():
        if f.get("tipo") not in TIPI:
            raise ValueError(f"{p.name}: fonte {k}: tipo {f.get('tipo')!r} (dsm, las o dtm)")
        if f.get("attiva") and f.get("licenza") not in arch:
            raise ValueError(f"{p.name}: fonte {k} attiva con licenza {f.get('licenza')!r} senza archivio in [archivi]")
    z.setdefault("limiti", {})
    return z


def usabile(f: dict) -> tuple[bool, str]:
    """Una fonte si usa solo se è attiva, ha un URL e la licenza è confermata."""
    if not f.get("attiva"):
        return False, f.get("motivo") or "disattivata"
    if not (f.get("url") or "").strip():
        return False, "manca l'URL"
    if not f.get("licenza_confermata"):
        return False, "licenza da confermare"
    return True, "attiva"


def elenco_fonti(z: dict) -> list[dict]:
    out = []
    for k, f in (z.get("fonti") or {}).items():
        ok, motivo = usabile(f)
        out.append({"id": k, "tipo": f["tipo"], "descrizione": f.get("descrizione", k), "licenza": f.get("licenza", ""),
                    "licenza_confermata": bool(f.get("licenza_confermata")), "attribuzione": f.get("attribuzione", ""),
                    "scheda": f.get("scheda", ""), "stato": "attiva" if ok else (f.get("stato") or "in attesa"),
                    "motivo": motivo, "priorita": int(f.get("priorita", 99)), "verifica": f.get("verifica", "")})
    return sorted(out, key=lambda x: (x["tipo"] == "dtm", x["priorita"]))


# ============================================================================================== tessere e corpi
@dataclass
class Tessera:
    nome: str
    x0: float
    y0: float
    x1: float
    y1: float
    i: int
    j: int

    @property
    def riquadro(self):
        return (self.x0, self.y0, self.x1, self.y1)

    def valori(self) -> dict:
        return {"tavola": self.nome, "x0": self.x0, "y0": self.y0, "x1": self.x1, "y1": self.y1,
                "e_km": int(self.x0 // 1000), "n_km": int(self.y0 // 1000), "e_hm": int(self.x0 // 100),
                "n_hm": int(self.y0 // 100)}


def griglia_tessere(z: dict):
    zona = z["zona"]
    lato = float(zona["lato_tessera"])
    x0, y0, x1, y1 = zona["riquadro"]
    out = {}
    for j in range(math.floor(y0 / lato), math.ceil(y1 / lato)):
        for i in range(math.floor(x0 / lato), math.ceil(x1 / lato)):
            t = Tessera("", i * lato, j * lato, (i + 1) * lato, (j + 1) * lato, i, j)
            t.nome = zona["nome_tessera"].format(**t.valori())
            out[(i, j)] = t
    return out, lato


@dataclass
class CorpoZ:
    id: str
    edificio: str
    sagoma: object            # poligono nel sistema della zona
    proprieta: dict
    tessera: tuple[int, int]
    toccate: set
    lonlat: tuple[float, float]


def leggi_corpi(cartella_contesto, z: dict, griglia, lato: float) -> dict[str, CorpoZ]:
    """Corpi della Fase A (celle GeoJSON in WGS84 di `prodotti/contesto/`) dentro il riquadro della zona, nel sistema
    della zona, ognuno assegnato alla tessera del suo centroide."""
    from pyproj import Transformer
    import shapely
    from shapely.geometry import shape
    tr = Transformer.from_crs("EPSG:4326", z["zona"]["crs"], always_xy=True)
    x0, y0, x1, y1 = z["zona"]["riquadro"]
    corpi: dict[str, CorpoZ] = {}
    cartelle = cartella_contesto if isinstance(cartella_contesto, (list, tuple)) else [cartella_contesto]
    for p in [q for c in cartelle for q in sorted(Path(c).glob("*.json"))]:
        try:
            fc = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for f in fc.get("features", []):
            cid = str(f.get("properties", {}).get("id") or f.get("id") or "")
            if not cid or cid in corpi:
                continue
            try:
                g = shape(f["geometry"])
            except Exception:
                continue
            lon, lat = g.centroid.x, g.centroid.y
            gz = shapely.transform(g, lambda x, y: tr.transform(x, y), interleaved=False)
            c = gz.centroid
            if not (x0 <= c.x < x1 and y0 <= c.y < y1):
                continue
            bx0, by0, bx1, by1 = gz.bounds
            toccate = {(i, j) for i in range(math.floor(bx0 / lato), math.floor(bx1 / lato) + 1)
                       for j in range(math.floor(by0 / lato), math.floor(by1 / lato) + 1)}
            corpi[cid] = CorpoZ(cid, str(f["properties"].get("edificio", "")), gz, f["properties"],
                                (math.floor(c.x / lato), math.floor(c.y / lato)), toccate, (lon, lat))
    return corpi


# ============================================================================================== stato
def _adesso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def scrivi_json(p: Path, dati) -> None:
    """Scrittura atomica: file temporaneo nella stessa cartella e poi rename."""
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)


def leggi_json(p: Path, predefinito=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return predefinito


def pulisci_errore(e: BaseException) -> str:
    """Messaggio d'errore per la pagina di stato: niente parametri delle query (possono contenere chiavi) né percorsi
    lunghi, al più 300 caratteri."""
    t = f"{type(e).__name__}: {e}"
    t = re.sub(r"(https?://[^\s?'\"]+)\?[^\s'\"]*", r"\1?…", t)
    return t[:300]


@contextlib.contextmanager
def blocco(percorso: Path):
    """Una sola esecuzione per zona (flock non bloccante)."""
    import fcntl
    percorso.parent.mkdir(parents=True, exist_ok=True)
    f = open(percorso, "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        raise RuntimeError("un'altra esecuzione della pipeline è già in corso su questa zona")
    try:
        f.write(str(os.getpid()))
        f.flush()
        yield
    finally:
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()


class Fermati(Exception):
    """Un limite della notte è stato raggiunto (non è un errore della tessera)."""


# ============================================================================================== copertura delle fonti
MINIMA_COPERTURA = 0.95


def leggi_indice(f: dict, cartella_zone: Path) -> dict | None:
    """Indice dei file di una fonte a più file: {"crs", "file": [{"nome", "riquadro": [x0, y0, x1, y1]}]}."""
    if not f.get("indice"):
        return None
    p = Path(f["indice"])
    if not p.is_absolute():
        p = Path(cartella_zone) / p
    return json.loads(p.read_text(encoding="utf-8"))


def area_coperta(f: dict, crs_zona: str, cartella_zone: Path):
    """Area coperta dalla fonte nel sistema della zona (shapely) o None se la fonte non dichiara limiti."""
    from shapely.geometry import box, shape
    from shapely.ops import unary_union, transform as sh_transform
    c = f.get("copertura") or {}
    pezzi = [box(*r) for r in c.get("riquadri", [])]
    if c.get("maschera"):
        p = Path(c["maschera"])
        if not p.is_absolute():
            p = Path(cartella_zone) / p
        d = json.loads(p.read_text(encoding="utf-8"))
        crs = (d.get("crs") or {}).get("properties", {}).get("name") or c.get("maschera_crs") or crs_zona
        geoms = [shape(x["geometry"]) for x in d.get("features", [])]
        if crs and crs.replace("urn:ogc:def:crs:", "").replace("::", ":") != crs_zona:
            from pyproj import Transformer
            tr = Transformer.from_crs(crs.replace("urn:ogc:def:crs:", "").replace("::", ":"), crs_zona, always_xy=True)
            geoms = [sh_transform(tr.transform, g) for g in geoms]
        pezzi += geoms
    ind = leggi_indice(f, cartella_zone)
    if ind:
        pezzi += [box(*x["riquadro"]) for x in ind.get("file", [])]
    if not pezzi:
        return None
    return unary_union(pezzi)


def copre(area, t: "Tessera", sagome=(), minima: float = MINIMA_COPERTURA) -> bool:
    """La fonte copre la tessera se dentro l'area cade almeno `minima` dell'area dei suoi edifici (o della tessera)."""
    if area is None:
        return True
    from shapely.geometry import box
    from shapely.ops import unary_union
    tb = box(*t.riquadro)
    if not area.intersects(tb):
        return False
    base = unary_union([g.intersection(tb) for g in sagome]) if sagome else tb
    if base.is_empty or base.area <= 0:
        base = tb
    return base.intersection(area).area >= minima * base.area - 1e-9


def file_della_tessera(ind: dict, t: "Tessera", massimo: int = 6) -> list[str]:
    """Nomi dei file dell'indice che toccano la tessera (al più `massimo`, i più sovrapposti prima)."""
    from shapely.geometry import box
    tb = box(*t.riquadro)
    sov = []
    for x in ind.get("file", []):
        a = box(*x["riquadro"]).intersection(tb).area
        if a > 0:
            sov.append((-a, x["nome"]))
    return [n for _, n in sorted(sov)[:massimo]]


# ============================================================================================== pipeline
def dtm_server(crs: str) -> list[Path]:
    """COG del DTM sul server (comando dtm-server: <nome>.tif con <nome>.json) nel sistema `crs`, da DTM_SERVER
    (predefinita /dati/terreno, la stessa cartella della rotta /api/terreno)."""
    cartella = Path(os.environ.get("DTM_SERVER", "/dati/terreno"))
    out = []
    for j in sorted(cartella.glob("*.json")) if cartella.is_dir() else []:
        try:
            d = json.loads(j.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if j.with_suffix(".tif").is_file() and str(d.get("crs", "")).upper() == str(crs).upper():
            out.append(j.with_suffix(".tif"))
    return out


class Pipeline:
    def __init__(self, zona: dict, archivio: Path, stato: Path, prodotti: Path | None = None, radice: Path | None = None,
                 client: httpx.Client | None = None, orologio=time.monotonic, dorme=time.sleep, adesso=None):
        self.z = zona
        self.zona = zona["zona"]
        self.lim = zona.get("limiti", {})
        self.archivio = Path(archivio)
        self.cartella_stato = Path(stato)
        self.radice = Path(radice) if radice else Path(zona["_file"]).parent
        self.client = client
        self.orologio, self.dorme = orologio, dorme
        self.adesso = adesso or (lambda: dt.datetime.now().astimezone())
        self.griglia, self.lato = griglia_tessere(zona)
        self.file_stato = self.cartella_stato / f"{self.zona['codice']}.json"
        self.stato = leggi_json(self.file_stato, None) or {}
        # licenza dei prodotti: quella della fonte DSM/LAS attiva (le fonti di licenze diverse vanno in archivi diversi)
        self._prodotti_forzati = Path(prodotti) if prodotti else None
        self.cartella_zone = Path(zona["_file"]).parent
        self._aree: dict[str, object] = {}
        self._indici: dict[str, dict | None] = {}

    # ------------------------------------------------------------------ percorsi
    def _zona_archivio(self):
        return {"archivi": self.z.get("archivi", {}), "zona": {"codice": self.zona["archivio"]}}

    def prodotti(self, licenza: str) -> Path:
        if self._prodotti_forzati:
            return self._prodotti_forzati
        return F.cartella(self.archivio, self._zona_archivio(), licenza, "prodotti")

    def contesto(self) -> Path:
        e = self.z.get("edifici", {})
        if e.get("contesto"):
            return self._percorso(e["contesto"])
        if self._prodotti_forzati:
            return self._prodotti_forzati / "contesto"
        return F.cartella(self.archivio, self._zona_archivio(), e.get("licenza", "CC BY 4.0"), "prodotti") / "contesto"

    def contesti(self) -> list[Path]:
        """Celle dei corpi della Fase A: l'archivio regionale (cc-by/er/prodotti/contesto) e, dal 07/11/2026, gli archivi
        dei comuni (cc-by/er/<comune>/prodotti/contesto, `prepara --comune`). I prodotti LiDAR restano nell'archivio
        regionale (cc-by/er/prodotti/lidar/), che la pagina trova con la chiave «lidar» di archivi.json."""
        base = self.contesto()
        out = [base]
        e = self.z.get("edifici", {})
        if not e.get("contesto") and not self._prodotti_forzati:
            reg = F.cartella(self.archivio, self._zona_archivio(), e.get("licenza", "CC BY 4.0"), "")
            out += sorted(p for p in reg.glob("*/prodotti/contesto") if p.is_dir())
        return [p for p in out if p.is_dir()] or [base]

    def _percorso(self, t: str) -> Path:
        t = t.replace("{radice}", str(self.radice))
        p = Path(t)
        return p if p.is_absolute() else (self.radice / p)

    def grezzi(self, licenza: str, tavola: str) -> Path:
        return F.cartella(self.archivio, self._zona_archivio(), licenza, "grezzi") / "lidar" / tavola

    # ------------------------------------------------------------------ fonti
    def fonti_attive(self, tipo: set[str]) -> list[tuple[str, dict]]:
        fs = [(k, f) for k, f in (self.z.get("fonti") or {}).items() if f["tipo"] in tipo and usabile(f)[0]]
        return sorted(fs, key=lambda kf: int(kf[1].get("priorita", 99)))

    def url(self, f: dict, t: Tessera, file: str = "") -> str:
        if file and f.get("sostituisci"):          # indice condiviso: es. ["dsm", "dtm"] per i file del DTM
            file = file.replace(f["sostituisci"][0], f["sostituisci"][1], 1)
        return f["url"].format(radice=str(self.radice), file=file, **t.valori())

    def area(self, chiave: str, f: dict):
        if chiave not in self._aree:
            self._aree[chiave] = area_coperta(f, self.zona["crs"], self.cartella_zone)
        return self._aree[chiave]

    def indice(self, chiave: str, f: dict) -> dict | None:
        if chiave not in self._indici:
            self._indici[chiave] = leggi_indice(f, self.cartella_zone)
        return self._indici[chiave]

    def file_tessera(self, chiave: str, f: dict, t: Tessera) -> list[str]:
        ind = self.indice(chiave, f)
        return file_della_tessera(ind, t, int(f.get("max_file_tessera", 6))) if ind else []

    def _http(self) -> httpx.Client:
        if self.client is None:
            self.client = httpx.Client(timeout=httpx.Timeout(30, read=300), follow_redirects=True,
                                       headers={"User-Agent": "EuGEnio-edifici3d (eugenio.statocritico.it)"})
        return self.client

    def versione(self, chiave: str, f: dict, t: Tessera, sagome=()) -> str | None:
        """Versione della fonte per la tessera; None = la fonte non copre la tessera."""
        minima = float((f.get("copertura") or {}).get("minima", MINIMA_COPERTURA))
        if not copre(self.area(chiave, f), t, sagome, minima):
            return None
        if f.get("indice"):
            nomi = self.file_tessera(chiave, f, t)
            if not nomi:
                return None
            return f"{chiave}:{f.get('versione_fissa', '')}:" + "|".join(nomi)
        u = self.url(f, t)
        modo = f.get("versione", "intestazioni")
        if u.startswith("file:"):
            p = Path(u[5:])
            if not p.exists():
                return None
            st = p.stat()
            return f"{chiave}:{st.st_size}:{int(st.st_mtime)}"
        qu = f.get("quadro_unione")
        if qu:                                 # WMS del quadro di unione: la tessera c'è? con quali date?
            props = self._quadro(qu, t)
            if props is None:
                return None
            campi = qu.get("campi_versione", [])
            return f"{chiave}:" + "|".join(str(props.get(c, "")).strip() for c in campi)
        if modo == "fissa":
            return f"{chiave}:{f.get('versione_fissa', '')}"
        r = self._http().head(u)
        if r.status_code == 404:
            return None
        if r.status_code >= 400:
            raise RuntimeError(f"{chiave}: HTTP {r.status_code}")
        return f"{chiave}:" + (r.headers.get("etag") or r.headers.get("last-modified") or r.headers.get("content-length") or "?")

    def _quadro(self, qu: dict, t: Tessera) -> dict | None:
        from pyproj import Transformer
        tr = Transformer.from_crs(self.zona["crs"], "EPSG:4326", always_xy=True)
        lon, lat = tr.transform((t.x0 + t.x1) / 2, (t.y0 + t.y1) / 2)
        d = 0.0005
        u = (f"{qu['wms']}?service=WMS&version=1.3.0&request=GetFeatureInfo&layers={qu['strato']}&query_layers={qu['strato']}"
             f"&crs=CRS:84&bbox={lon - d},{lat - d},{lon + d},{lat + d}&width=11&height=11&i=5&j=5"
             f"&info_format=application/geojson&feature_count=1")
        r = self._http().get(u)
        r.raise_for_status()
        fs = r.json().get("features", [])
        return fs[0].get("properties", {}) if fs else None

    def scarica(self, u: str, dest: Path, conto: dict) -> Path:
        """Scaricamento con ripresa e tetti: dimensione massima della tessera e quota della notte."""
        max_b = float(self.lim.get("max_mb_tessera", 2000)) * 1024 ** 2
        if u.startswith("file:"):
            src = Path(u[5:])
            if src.stat().st_size > max_b:
                raise ValueError(f"file oltre {self.lim.get('max_mb_tessera', 2000)} MB")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
            conto["byte"] += dest.stat().st_size
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".parziale")
        inizio = tmp.stat().st_size if tmp.exists() else 0
        intest = {"Range": f"bytes={inizio}-"} if inizio else {}
        quota = float(self.lim.get("max_gb_notte", 25)) * GB
        with self._http().stream("GET", u, headers=intest) as r:
            if r.status_code == 416:
                pass
            elif r.status_code not in (200, 206):
                raise RuntimeError(f"HTTP {r.status_code}")
            else:
                lung = int(r.headers.get("content-length") or 0)
                if lung and lung + (inizio if r.status_code == 206 else 0) > max_b:
                    raise ValueError("tessera oltre la dimensione massima")
                modo = "ab" if r.status_code == 206 else "wb"
                scritti = inizio if r.status_code == 206 else 0
                with open(tmp, modo) as fo:
                    for pezzo in r.iter_bytes(1 << 20):
                        fo.write(pezzo)
                        scritti += len(pezzo)
                        conto["byte"] += len(pezzo)
                        if scritti > max_b:
                            raise ValueError("tessera oltre la dimensione massima")
                        if conto["byte"] > quota:
                            raise Fermati("quota di download della notte raggiunta")
        tmp.replace(dest)
        return dest

    # ------------------------------------------------------------------ limiti
    def _scadenza(self, max_minuti: float | None, subito: bool) -> float:
        inizio = self.orologio()
        m = float(max_minuti if max_minuti is not None else self.lim.get("max_minuti", 210))
        scad = inizio + m * 60
        fin = self.lim.get("finestra")
        if fin and not subito:
            a, b = (dt.time.fromisoformat(x) for x in fin)
            ora = self.adesso()
            t = ora.time()
            dentro = (a <= t < b) if a < b else (t >= a or t < b)
            if not dentro:
                raise Fermati(f"fuori dalla finestra {fin[0]}–{fin[1]}")
            fine = ora.replace(hour=b.hour, minute=b.minute, second=0, microsecond=0)
            if fine <= ora:
                fine += dt.timedelta(days=1)
            scad = min(scad, inizio + (fine - ora).total_seconds())
        return scad

    def disco_libero_gb(self) -> float:
        p = self.archivio
        while not p.exists() and p != p.parent:
            p = p.parent
        return shutil.disk_usage(p).free / GB

    def controlla(self, scadenza: float, conto: dict) -> None:
        if self.orologio() >= scadenza:
            raise Fermati("tempo della notte finito")
        if self.disco_libero_gb() < float(self.lim.get("min_gb_liberi", 20)):
            raise Fermati(f"spazio libero sotto {self.lim.get('min_gb_liberi', 20)} GB")
        if conto["byte"] >= float(self.lim.get("max_gb_notte", 25)) * GB:
            raise Fermati("quota di download della notte raggiunta")
        self._pausa(scadenza)

    def _pausa(self, scadenza: float) -> None:
        u = self.lim.get("pausa_url")
        if not u:
            return
        fine = min(scadenza, self.orologio() + float(self.lim.get("pausa_max_minuti", 20)) * 60)
        while True:
            try:
                n = int(httpx.get(u, timeout=3).json().get("previsioni_in_corso") or 0)
            except Exception:
                return                               # api non raggiungibile: si va avanti
            if n <= 0:
                return
            if self.orologio() >= fine:
                raise Fermati("il server sta calcolando previsioni da troppo tempo")
            log.info("previsione in corso sul server: pausa di 20 s")
            self.dorme(20)

    # ------------------------------------------------------------------ esecuzione
    def esegui(self, subito: bool = False, max_minuti: float | None = None, solo: list[str] | None = None,
               aggiorna: bool = False) -> dict:
        with blocco(self.cartella_stato / f"{self.zona['codice']}.lock"):
            return self._esegui(subito, max_minuti, solo, aggiorna)

    def _nuovo_stato(self):
        s = self.stato or {}
        s.setdefault("zona", self.zona["codice"]); s["nome"] = self.zona["nome"]
        s.setdefault("tessere", {}); s.setdefault("esecuzioni", [])
        s["ordine"] = self.zona.get("ordine", 99)
        s["prova"] = bool(self.zona.get("prova"))
        s["fonti"] = elenco_fonti(self.z)
        s["limiti"] = {k: self.lim.get(k) for k in ("finestra", "max_minuti", "min_gb_liberi", "max_gb_notte",
                                                     "max_tentativi", "max_mb_tessera") if k in self.lim}
        self.stato = s
        return s

    def salva(self):
        s = self.stato
        conta: dict[str, int] = {}
        qual: dict[str, int] = {}
        for t in s["tessere"].values():
            conta[t["stato"]] = conta.get(t["stato"], 0) + 1
            for k, v in (t.get("qualita") or {}).items():
                qual[k] = qual.get(k, 0) + v
        s["conteggi"] = conta
        s["qualita"] = qual
        s["aggiornato"] = _adesso()
        try:
            s["disco"] = {"libero_gb": round(self.disco_libero_gb(), 2)}
        except OSError:
            pass
        scrivi_json(self.file_stato, s)

    def _esegui(self, subito, max_minuti, solo, aggiorna) -> dict:
        s = self._nuovo_stato()
        corpi = leggi_corpi(self.contesti(), self.z, self.griglia, self.lato)
        # tessere con edifici: tutte quelle toccate da almeno un corpo (anche solo da un pezzo di sagoma)
        con_edifici = set().union(*(c.toccate for c in corpi.values())) if corpi else set()
        tessere = [self.griglia[k] for k in sorted(con_edifici, key=lambda ij: (-ij[1], ij[0])) if k in self.griglia]
        s["totale_tessere"] = len(tessere)
        s["corpi"] = len(corpi)
        for t in tessere:
            s["tessere"].setdefault(t.nome, {"stato": "da fare", "tentativi": 0})
        # una tessera rimasta «in corso» è un'esecuzione interrotta: conta come tentativo
        for v in s["tessere"].values():
            if v["stato"] == "in corso":
                v["stato"] = "errore"; v["tentativi"] = v.get("tentativi", 0) + 1
                v["errore"] = "esecuzione interrotta"
        esec = {"inizio": _adesso(), "tessere_fatte": 0, "tessere_errore": 0, "corpi": 0, "byte": 0, "esito": "in corso"}
        s["esecuzioni"].append(esec)
        s["esecuzioni"] = s["esecuzioni"][-NOTTI:]
        conto = {"byte": 0}
        dsm_fonti = self.fonti_attive({"dsm", "las"})
        if not tessere:                                 # nessun corpo della Fase A: la zona aspetta le sagome
            esec.update(esito="in attesa", motivo="nessun corpo della Fase A per la zona (prodotti/contesto vuoto)",
                        fine=_adesso())
            self.salva()
            return esec
        if not dsm_fonti:
            esec.update(esito="in attesa", motivo="nessuna fonte DSM o LAS attiva (vedi le fonti)", fine=_adesso())
            self.salva()
            return esec
        try:
            scadenza = self._scadenza(max_minuti, subito)
        except Fermati as e:
            esec.update(esito="non avviata", motivo=str(e), fine=_adesso())
            self.salva()
            return esec
        max_t = int(self.lim.get("max_tentativi", 3))
        oggi = dt.datetime.now(dt.timezone.utc)
        giorni = float(self.lim.get("aggiorna_giorni", 365))
        try:
            for t in tessere:
                if solo and t.nome not in solo:
                    continue
                v = s["tessere"][t.nome]
                if v["stato"] == "saltata":
                    continue
                if v["stato"] in ("fatta", "senza rilievo"):
                    if not aggiorna:
                        continue
                    ultima = v.get("controllata") or v.get("fatta")
                    if ultima and (oggi - dt.datetime.fromisoformat(ultima)).days < giorni:
                        continue
                self.controlla(scadenza, conto)
                try:
                    self._tessera(t, v, corpi, dsm_fonti, conto, aggiorna)
                    if v["stato"] == "fatta":
                        esec["tessere_fatte"] += 1
                        esec["corpi"] += v.get("corpi", 0)
                except Fermati:
                    v["stato"] = "da fare"
                    raise
                except Exception as e:                          # errore della tessera: si passa alla prossima
                    log.warning("tessera %s: %s", t.nome, e)
                    v["tentativi"] = v.get("tentativi", 0) + 1
                    v["errore"] = pulisci_errore(e)
                    v["ultimo_errore"] = _adesso()
                    v["stato"] = "saltata" if v["tentativi"] >= max_t else "errore"
                    esec["tessere_errore"] += 1
                    s.setdefault("errori", []).append({"tessera": t.nome, "quando": v["ultimo_errore"], "errore": v["errore"],
                                                       "tentativo": v["tentativi"]})
                    s["errori"] = s["errori"][-50:]
                finally:
                    esec["byte"] = conto["byte"]
                    self.salva()
            esec["esito"] = "completata" if all(x["stato"] in ("fatta", "senza rilievo", "saltata")
                                                for x in s["tessere"].values()) else "parziale"
            if esec["esito"] == "completata" and not s.get("completata"):
                s["completata"] = _adesso()
        except Fermati as e:
            esec["esito"] = "fermata"; esec["motivo"] = str(e)
        esec["fine"] = _adesso()
        esec["byte"] = conto["byte"]
        self.salva()
        return esec

    # ------------------------------------------------------------------ una tessera
    def _tessera(self, t: Tessera, v: dict, corpi: dict[str, CorpoZ], dsm_fonti, conto: dict, aggiorna: bool) -> None:
        t0 = self.orologio()
        scelta = None
        sagome_t = [c.sagoma for c in corpi.values() if (t.i, t.j) in c.toccate]
        for k, f in dsm_fonti:
            ver = self.versione(k, f, t, sagome_t)
            if ver is not None:
                scelta = (k, f, ver)
                break
        if scelta is None:
            v.update(stato="senza rilievo", controllata=_adesso(), fonte=None, versione=None)
            v.pop("errore", None)
            return
        k, f, ver = scelta
        if aggiorna and v.get("stato") == "fatta" and v.get("versione") == ver:
            v["controllata"] = _adesso()
            return
        v["stato"] = "in corso"
        self.salva()
        licenza = f["licenza"]
        grezzi = self.grezzi(licenza, t.nome)
        prodotti = self.prodotti(licenza) / "lidar"
        byte0 = conto["byte"]
        passo = float(self.lim.get("passo_dsm", L.PASSO))
        raw = None
        if f.get("indice"):                            # fonte a più file: mosaico dei file che toccano la tessera
            dsm = self._mosaico(k, f, t, grezzi, conto, passo)
        else:
            nome_file = Path(urlparse(self.url(f, t).replace("file:", "file://", 1)).path).name or f"{t.nome}.bin"
            raw = self.scarica(self.url(f, t), grezzi / f"{k}_{nome_file}"[-120:], conto)
        if f.get("indice"):
            dtm, fonte_dtm = self._dtm(t, grezzi, conto, passo, licenza, sagome_t)
        elif f["tipo"] == "las":
            pts = L.leggi_las(raw, riquadro=t.riquadro, max_punti=int(self.lim.get("max_punti_las", 60_000_000)))
            dsm, dtm = L.griglie_da_las(pts, t.riquadro, passo)
            fonte_dtm = f"{k} (classe terreno)"
        else:
            dsm = L.ricampiona(L.leggi_raster(raw, t.riquadro), t.riquadro, passo)
            dtm, fonte_dtm = self._dtm(t, grezzi, conto, passo, licenza, sagome_t)
        # DSM e DTM ridotti, solo attorno agli edifici
        sagome = sagome_t
        masc = L.maschera_edifici(dsm, sagome, float(self.lim.get("maschera_m", 30)))
        et = {"FONTE": k, "VERSIONE": ver, "TESSERA": t.nome}
        L.scrivi_ridotto(dsm, prodotti / "dsm" / f"{t.nome}.tif", self.zona["crs"], masc, et)
        if dtm is not None:
            L.scrivi_ridotto(dtm, prodotti / "dtm" / f"{t.nome}.tif", self.zona["crs"], masc, {**et, "FONTE_DTM": fonte_dtm or ""})
        # alberi (05/11/2026): chiome dal DSM attorno agli edifici, ostacoli per le ombre della pagina 3D
        if dtm is not None:
            self._alberi(t, dsm, dtm, sagome, prodotti)
        # corpi da (ri)elaborare: quelli della tessera e quelli delle vicine che la toccano
        da_fare = [c for c in corpi.values() if c.tessera == (t.i, t.j) or ((t.i, t.j) in c.toccate)]
        n_falde, qual = self._corpi(da_fare, prodotti, k, f, ver, fonte_dtm)
        mie = [c for c in da_fare if c.tessera == (t.i, t.j)]
        q_mie = self._conta_qualita(prodotti, t.nome)
        # i corpi delle tessere vicine rielaborati qui cambiano anche i loro conteggi
        for nome in {self.griglia[c.tessera].nome for c in da_fare} - {t.nome}:
            vv = self.stato["tessere"].get(nome)
            if vv and vv.get("stato") == "fatta":
                vv["qualita"] = self._conta_qualita(prodotti, nome)
        if not self.lim.get("tieni_grezzi"):
            shutil.rmtree(grezzi, ignore_errors=True)
        kb = sum(p.stat().st_size for p in (prodotti / "dsm" / f"{t.nome}.tif", prodotti / "dtm" / f"{t.nome}.tif") if p.exists())
        v.update(stato="fatta", fonte=k, versione=ver, fonte_dtm=fonte_dtm, fatta=_adesso(), controllata=_adesso(),
                 corpi=len(mie), falde=n_falde, qualita=q_mie, byte_scaricati=conto["byte"] - byte0,
                 byte_prodotti=kb, secondi=round(self.orologio() - t0, 1))
        v.pop("errore", None)
        self._indice(prodotti, k, f)

    def _mosaico(self, k: str, f: dict, t: Tessera, grezzi: Path, conto: dict, passo: float) -> L.Griglia:
        griglie = []
        for nome in self.file_tessera(k, f, t):
            r = self.scarica(self.url(f, t, nome), grezzi / f"{k}_{nome}"[-120:], conto)
            griglie.append(L.ricampiona(L.leggi_raster(r, t.riquadro), t.riquadro, passo))
        if not griglie:
            raise RuntimeError(f"{k}: nessun file dell'indice per {t.nome}")
        return L.unisci(griglie, t.riquadro, passo)

    def _dtm(self, t: Tessera, grezzi: Path, conto: dict, passo: float, licenza: str, sagome=()):
        """DTM della tessera: fonti `dtm` attive che la coprono, per priorità; se la prima lascia dei vuoti (es. DTM 0,5 m
        di Bolzano solo nelle aree insediative) si riempiono con le successive; infine il DTM della Fase A."""
        griglie, usate = [], []
        for kd, fd in self.fonti_attive({"dtm"}):
            try:
                if self.versione(kd, fd, t, sagome) is None:
                    continue
                if fd.get("indice"):
                    g = self._mosaico(kd, fd, t, grezzi, conto, passo)
                else:
                    rd = self.scarica(self.url(fd, t), grezzi / f"{kd}_{t.nome}.tif", conto)
                    g = L.ricampiona(L.leggi_raster(rd, t.riquadro), t.riquadro, passo)
                griglie.append(g); usate.append(kd)
                if not np.isnan(L.unisci(griglie, t.riquadro, passo).z).any():
                    break
            except Fermati:
                raise
            except Exception as e:
                log.warning("DTM %s per %s: %s", kd, t.nome, e)
        cog = self.prodotti(licenza) / "dtm_cog.tif"            # ripiego: DTM della Fase A, se l'archivio lo ha ancora
        if (not griglie or np.isnan(L.unisci(griglie, t.riquadro, passo).z).any()) and cog.exists():
            griglie.append(L.ricampiona(L.leggi_raster(cog, t.riquadro), t.riquadro, passo)); usate.append("DTM della Fase A")
        # ripiego dal 07/11/2026: il DTM 5 m del server (COG di `dtm-server` in DTM_SERVER, /dati/terreno), lo stesso della
        # rotta /api/terreno; letto a finestra, solo se è nel sistema della zona
        for tif in dtm_server(self.zona["crs"]):
            if griglie and not np.isnan(L.unisci(griglie, t.riquadro, passo).z).any():
                break
            try:
                griglie.append(L.ricampiona(L.leggi_raster(tif, t.riquadro, max_celle=10 ** 11), t.riquadro, passo))
                usate.append(f"DTM del server ({tif.name})")
            except Exception as e:
                log.warning("DTM del server %s per %s: %s", tif.name, t.nome, e)
        if not griglie:
            return None, None
        return (griglie[0] if len(griglie) == 1 else L.unisci(griglie, t.riquadro, passo)), " + ".join(usate)

    def _alberi(self, t: Tessera, dsm, dtm, sagome, prodotti: Path) -> int:
        """Chiome della tessera → celle di 0,01° in WGS84 (`lidar/alberi/<i>_<j>.json`, per tessera: rifare sovrascrive)."""
        try:
            pts = LC.alberi(dsm, dtm, sagome, fascia=float(self.lim.get("fascia_alberi_m", 50)))
        except Exception as e:                            # gli alberi sono un di più: un errore non ferma la tessera
            log.warning("alberi di %s: %s", t.nome, e)
            return 0
        celle: dict[str, list] = {}
        for a in LC.alberi_in_wgs84(pts, self.zona["crs"]):
            celle.setdefault(f"{math.floor(a[0] / T.CELLA)}_{math.floor(a[1] / T.CELLA)}", []).append(a)
        for nome, aa in celle.items():
            pth = prodotti / "alberi" / f"{nome}.json"
            d = leggi_json(pth, {"cella": nome, "crs": "EPSG:4326", "campi": ["lon", "lat", "h", "quota", "lato"], "tessere": {}})
            d["tessere"][t.nome] = aa
            scrivi_json(pth, d)
        return len(pts)

    def corpi_lidar(self, tessere: list[str] | None = None, riquadro=None, conto: dict | None = None) -> dict:
        """Corpi dal solo LiDAR (§ 7) per una zona senza sagome: per ogni tessera scelta (nomi o riquadro) scarica DSM e
        DTM dalle fonti attive, raggruppa le celle per altezza e scrive i prodotti della Fase A (contesto/, corpi.pmtiles,
        indice.json) nell'archivio della licenza del DSM. Poi la pipeline normale stima le falde su questi corpi."""
        from shapely.geometry import box
        from .__main__ import prepara_corpi
        conto = conto if conto is not None else {"byte": 0}
        scelte = [t for t in self.griglia.values() if (tessere and t.nome in tessere)
                  or (riquadro is not None and box(*t.riquadro).intersects(box(*riquadro)))]
        if not scelte:
            raise ValueError("nessuna tessera scelta (--tessere o --riquadro nel sistema della zona)")
        passo = float(self.lim.get("passo_dsm", L.PASSO))
        corpi, usate, licenze, attrib = [], [], set(), {}
        for t in scelte:
            for k, f in self.fonti_attive({"dsm", "las"}):
                if self.versione(k, f, t) is None:
                    continue
                grezzi = self.grezzi(f["licenza"], t.nome)
                if f.get("indice"):
                    dsm = self._mosaico(k, f, t, grezzi, conto, passo)
                    dtm, _ = self._dtm(t, grezzi, conto, passo, f["licenza"])
                elif f["tipo"] == "las":
                    raw = self.scarica(self.url(f, t), grezzi / f"{k}_{t.nome}.las", conto)
                    dsm, dtm = L.griglie_da_las(L.leggi_las(raw, riquadro=t.riquadro), t.riquadro, passo)
                else:
                    raw = self.scarica(self.url(f, t), grezzi / f"{k}_{t.nome}.tif", conto)
                    dsm = L.ricampiona(L.leggi_raster(raw, t.riquadro), t.riquadro, passo)
                    dtm, _ = self._dtm(t, grezzi, conto, passo, f["licenza"])
                if dtm is not None:
                    nuovi = LC.corpi_da_lidar(dsm, dtm, f"L{t.nome}", f["licenza"], f.get("descrizione", k), self.zona["crs"])
                    # un corpo a cavallo del bordo compare in due tessere: si tiene quello con il baricentro dentro la tessera
                    tb = box(*t.riquadro)
                    corpi += [c for c in nuovi if tb.contains(c.sagoma.centroid)]
                    usate.append(t.nome); licenze.add(f["licenza"]); attrib[k] = f.get("attribuzione", k)
                if not self.lim.get("tieni_grezzi"):
                    shutil.rmtree(grezzi, ignore_errors=True)
                break
        if not corpi:
            return {"tessere": usate, "corpi": 0}
        if len(licenze) > 1:
            raise ValueError(f"fonti con licenze diverse nelle tessere scelte: {sorted(licenze)}")
        lic = licenze.pop()
        out = self.prodotti(lic)
        esito = prepara_corpi(corpi, None, out, lic, "; ".join(attrib.values()), crs=self.zona["crs"],
                              extra={"fonte_edifici": {"metodo": "corpi dal solo LiDAR (§ 7)", "tessere": usate}})
        return {"tessere": usate, "corpi": len(corpi), "edifici": len({c.edificio for c in corpi}), "prodotti": str(out),
                "celle": esito.get("celle"), "byte": conto["byte"]}

    @staticmethod
    def _conta_qualita(prodotti: Path, nome: str) -> dict[str, int]:
        d = leggi_json(prodotti / "corpi" / f"{nome}.json", {}) or {}
        q: dict[str, int] = {}
        for r in (d.get("corpi") or {}).values():
            k = r.get("qualita") or r.get("stato", "—")
            q[k] = q.get(k, 0) + 1
        return q

    def _corpi(self, corpi: list[CorpoZ], prodotti: Path, k: str, f: dict, ver: str, fonte_dtm) -> tuple[int, dict]:
        """Falde dei corpi dai DSM ridotti delle tessere che toccano; aggiorna i file per tessera e le celle."""
        per_tessera: dict[str, dict] = {}
        celle: dict[str, dict] = {}
        n_falde = 0
        qual = {}
        for c in corpi:
            bx0, by0, bx1, by1 = c.sagoma.bounds
            riq = (math.floor(bx0) - 2, math.floor(by0) - 2, math.ceil(bx1) + 2, math.ceil(by1) + 2)
            gd, gt = [], []
            for ij in sorted(c.toccate):
                tt = self.griglia.get(ij)
                if not tt:
                    continue
                pd, pt = prodotti / "dsm" / f"{tt.nome}.tif", prodotti / "dtm" / f"{tt.nome}.tif"
                if pd.exists():
                    gd.append(L.leggi_raster(pd, riq))
                if pt.exists():
                    gt.append(L.leggi_raster(pt, riq))
            if not gd:
                continue
            passo = gd[0].passo
            dsm = L.unisci(gd, riq, passo)
            dtm = L.unisci(gt, riq, passo) if gt else None
            r = L.falde_corpo(c.sagoma, dsm, dtm, quota_terreno=c.proprieta.get("quota_terreno"))
            r.update({"id": c.id, "edificio": c.edificio, "fonte": k, "descrizione_fonte": f.get("descrizione", k),
                      "versione": ver, "fonte_dtm": fonte_dtm, "licenza": f["licenza"],
                      "attribuzione": f.get("attribuzione", ""), "elaborato": _adesso(),
                      "altezza_dbtr": c.proprieta.get("gronda")})
            if f.get("sintetico"):
                r["sintetico"] = True
            qual[c.id] = r.get("qualita") or r.get("stato", "—")
            n_falde += len(r.get("falde", []))
            tt = self.griglia[c.tessera]
            per_tessera.setdefault(tt.nome, {})[c.id] = r
            w = L.in_wgs84(r, self.zona["crs"])
            cella = f"{math.floor(c.lonlat[0] / T.CELLA)}_{math.floor(c.lonlat[1] / T.CELLA)}"
            celle.setdefault(cella, {})[c.id] = w
        for nome, rs in per_tessera.items():
            p = prodotti / "corpi" / f"{nome}.json"
            d = leggi_json(p, {"tessera": nome, "crs": self.zona["crs"], "corpi": {}})
            d["corpi"].update(rs)
            scrivi_json(p, d)
        for nome, rs in celle.items():
            p = prodotti / "falde" / f"{nome}.json"
            d = leggi_json(p, {"cella": nome, "crs": "EPSG:4326", "corpi": {}})
            d["corpi"].update(rs)
            scrivi_json(p, d)
        return n_falde, qual

    def _indice(self, prodotti: Path, k: str, f: dict) -> None:
        """Registro delle fonti e delle attribuzioni della zona, letto dalla pagina 3D (`lidar/indice.json`)."""
        p = prodotti / "indice.json"
        d = leggi_json(p, {"cella": T.CELLA, "attribuzioni": {}, "zone": {}})
        a = d["attribuzioni"].setdefault(k, {"descrizione": f.get("descrizione", k), "licenza": f["licenza"],
                                            "attribuzione": f.get("attribuzione", ""), "scheda": f.get("scheda", ""),
                                            "tessere": 0})
        a["tessere"] = sum(1 for v in self.stato["tessere"].values() if v.get("fonte") == k and v["stato"] == "fatta")
        d["zone"][self.zona["codice"]] = {"nome": self.zona["nome"], "aggiornato": _adesso()}
        d["aggiornato"] = _adesso()
        if f.get("sintetico"):
            d["sintetico"] = True
            d["avviso"] = "Rilievo LiDAR sintetico di esempio: falde e altezze sono inventate e non rappresentano edifici reali."
        scrivi_json(p, d)
        # (07/11/2026 sera) archivi.json dice alla pagina dove sono le falde solo quando ci sono: si aggiorna qui
        try:
            from .archivi import scrivi_archivi_json
            aj = self.archivio / "archivi.json"
            if aj.is_file() and "lidar" not in json.loads(aj.read_text(encoding="utf-8")):
                scrivi_archivi_json(self.archivio)
        except (OSError, ValueError) as e:     # noqa: PERF203 – mai fermare la pipeline per l'elenco
            log.warning("archivi.json non aggiornato: %s", e)


# ============================================================================================== scelta della zona e stato
def zone_disponibili(cartella: Path = ZONE) -> list[dict]:
    out = []
    for p in sorted(Path(cartella).glob("*.toml")):
        try:
            out.append(carica_zona(p))
        except (ValueError, OSError, tomllib.TOMLDecodeError) as e:
            log.warning("%s: %s", p.name, e)
    return sorted(out, key=lambda z: z["zona"].get("ordine", 99))


def scegli_zona(cartella_stato: Path, cartella_zone: Path = ZONE, archivio: Path | None = None) -> tuple[dict | None, bool]:
    """La prima zona della coda (campo `ordine`) con fonti attive e tessere da fare; se sono tutte complete, la zona
    controllata da più tempo (aggiornamento annuale). Le zone di prova (`prova = true`) non entrano; con `archivio`, non
    entrano nemmeno le zone senza i corpi della Fase A (celle di contesto)."""
    candidate = []
    for z in zone_disponibili(cartella_zone):
        if z["zona"].get("prova"):
            continue
        if not [1 for f in (z.get("fonti") or {}).values() if f["tipo"] in ("dsm", "las") and usabile(f)[0]]:
            continue
        if archivio is not None:
            ctx = Pipeline(z, archivio, cartella_stato).contesti()
            if not any(c.is_dir() and any(c.glob("*.json")) for c in ctx):
                continue
        st = leggi_json(Path(cartella_stato) / f"{z['zona']['codice']}.json", {}) or {}
        if not st.get("completata"):
            return z, False
        candidate.append((st.get("aggiornato", ""), z))
    if candidate:
        return sorted(candidate, key=lambda x: x[0])[0][1], True
    return None, False


def riepilogo(cartella_stato: Path) -> dict:
    """Tutte le zone (per la pagina di stato e per `lidar-stato`)."""
    zone = []
    for p in sorted(Path(cartella_stato).glob("*.json")):
        s = leggi_json(p, None)
        if isinstance(s, dict) and "tessere" in s:
            zone.append(s)
    return {"zone": sorted(zone, key=lambda s: s.get("ordine", 99))}
