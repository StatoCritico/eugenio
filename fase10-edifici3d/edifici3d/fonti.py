"""Fonti della zona (TOML) e scaricamento negli archivi separati per licenza.

Struttura dell'archivio (fuori dal repository, per esempio /srv/energia/dati/edifici):
  <archivio>/cc-by/<zona>/grezzi/...      DBTR UVL, DTM, aggregati (CC BY 4.0)
  <archivio>/odbl/<zona>/grezzi/...       OpenStreetMap (ODbL 1.0)
  <archivio>/<licenza>/<zona>/fonti.json  registro: URL, data, dimensione, SHA256 e attribuzione di ogni file
I prodotti (PMTiles, COG) vanno in <archivio>/<licenza>/<zona>/prodotti/ e restano separati allo stesso modo.

Scaricamento a pezzi con ripresa (Range), file temporaneo `.parziale` e nome definitivo solo a fine download.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

log = logging.getLogger(__name__)
QUI = Path(__file__).resolve().parent.parent
FONTI = QUI / "fonti"


@dataclass
class Fonte:
    chiave: str
    descrizione: str
    licenza: str
    attribuzione: str
    dati: dict

    @property
    def url(self) -> str:
        return self.dati.get("url", "") or ""


def carica_zona(nome: str | Path = "emilia_romagna") -> dict:
    p = Path(nome)
    if not p.suffix:
        p = FONTI / f"{nome}.toml"
    z = tomllib.loads(p.read_text(encoding="utf-8"))
    licenze = z.get("archivi", {})
    for k, f in z.get("fonti", {}).items():
        if f.get("licenza") not in licenze:
            raise ValueError(f"fonte {k}: licenza {f.get('licenza')!r} senza archivio in [archivi]")
    return z


def fonti(zona: dict) -> dict[str, Fonte]:
    return {k: Fonte(k, f.get("descrizione", k), f["licenza"], f.get("attribuzione", ""), f)
            for k, f in zona.get("fonti", {}).items()}


def cartella(archivio: Path, zona: dict, licenza: str, parte: str = "grezzi") -> Path:
    """Cartella dell'archivio per licenza: CC BY e ODbL non finiscono mai nella stessa cartella."""
    sotto = zona["archivi"][licenza]
    return Path(archivio) / sotto / zona["zona"]["codice"] / parte


def registra(archivio: Path, zona: dict, fonte: Fonte, file: Path, url: str) -> None:
    reg = cartella(archivio, zona, fonte.licenza, "fonti.json")
    dati = json.loads(reg.read_text(encoding="utf-8")) if reg.exists() else {"file": []}
    h = hashlib.sha256()
    with open(file, "rb") as f:
        for blocco in iter(lambda: f.read(1 << 20), b""):
            h.update(blocco)
    dati["file"] = [x for x in dati["file"] if x["nome"] != file.name] + [{
        "nome": file.name, "fonte": fonte.chiave, "url": url, "licenza": fonte.licenza,
        "attribuzione": fonte.attribuzione, "byte": file.stat().st_size, "sha256": h.hexdigest(),
        "scaricato": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}]
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")


def scarica(url: str, dest: Path, client: httpx.Client | None = None, blocco: int = 1 << 20) -> Path:
    """Scarica url in dest con ripresa: se esiste dest.parziale chiede il resto con Range."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".parziale")
    inizio = tmp.stat().st_size if tmp.exists() else 0
    proprio = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(60, read=300), follow_redirects=True)
    try:
        intest = {"Range": f"bytes={inizio}-"} if inizio else {}
        with client.stream("GET", url, headers=intest) as r:
            if r.status_code == 416:            # già tutto scaricato
                pass
            elif r.status_code not in (200, 206):
                raise RuntimeError(f"{url}: HTTP {r.status_code}")
            else:
                modo = "ab" if r.status_code == 206 else "wb"
                with open(tmp, modo) as f:
                    for pezzo in r.iter_bytes(blocco):
                        f.write(pezzo)
    finally:
        if proprio:
            client.close()
    tmp.replace(dest)
    return dest


def nome_da_url(url: str, predefinito: str) -> str:
    n = Path(urlparse(url).path).name
    return n or predefinito


def scarica_fonte(archivio: Path, zona: dict, chiave: str, client: httpx.Client | None = None,
                  quadranti: list[str] | None = None) -> list[Path]:
    """Scarica una fonte del TOML nell'archivio della sua licenza. Restituisce i file scaricati.
    Una fonte senza URL (da completare a mano nel TOML) solleva un errore chiaro, senza tentativi.
    `quadranti`: solo questi (per nome, es. ["SE"]) tra i quadranti della fonte; con `byte` nel TOML la dimensione si
    controlla alla fine (07/11/2026: DTM 5 m in grezzi/dtm5/)."""
    f = fonti(zona)[chiave]
    q = [x if isinstance(x, dict) else {"url": x} for x in f.dati.get("quadranti", [])]
    if quadranti:
        q = [x for x in q if str(x.get("nome", "")).upper() in {n.upper() for n in quadranti}]
        if not q:
            raise RuntimeError(f"fonte {chiave}: nessun quadrante tra {quadranti}")
    attesi = {x["url"]: x.get("byte") for x in q if x.get("url")}
    urls = [u for u in (([] if quadranti else [f.url]) + [x.get("url") for x in q]) if u]
    if not urls:
        raise RuntimeError(f"fonte {chiave}: URL vuoto in {zona['zona']['nome']}.toml – "
                           f"vedi {f.dati.get('pagina_download') or f.dati.get('scheda')}")
    out = []
    dest = cartella(archivio, zona, f.licenza)
    if q:
        dest = dest / chiave
    for u in urls:
        p = scarica(u, dest / nome_da_url(u, f"{chiave}.{f.dati.get('formato', 'bin')}"), client)
        if attesi.get(u) and p.stat().st_size != attesi[u]:
            raise RuntimeError(f"{p.name}: {p.stat().st_size} byte invece di {attesi[u]} (rilancia: riprende da dove è rimasto)")
        registra(archivio, zona, f, p, u)
        log.info("%s: %s (%d byte)", chiave, p.name, p.stat().st_size)
        out.append(p)
    return out


def url_wcs(fonte: Fonte, riquadro: tuple[float, float, float, float], crs: str = "EPSG:7791") -> str:
    """GetCoverage WCS 1.0.0 di un riquadro (x_min, y_min, x_max, y_max nel sistema crs) in GeoTIFF. L'1.0.0 perché il
    WCS 2.0.1 dei servizi ArcGIS della Regione risponde in multipart (prova del 04/11/2026)."""
    x0, y0, x1, y1 = riquadro
    cov = fonte.dati.get("wcs_coverage") or "1"
    passo = fonte.dati.get("wcs_passo", 5)
    return (f"{fonte.dati['wcs']}?service=WCS&version=1.0.0&request=GetCoverage&coverage={cov}&crs={crs}"
            f"&bbox={x0},{y0},{x1},{y1}&resx={passo}&resy={passo}&format=GeoTIFF")
