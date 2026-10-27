"""Download dei confini comunali e delle sezioni di censimento da Gramscii, a versione bloccata.

Scelta: non copiamo i dati grezzi nel nostro repository e non li leggiamo "dal vivo" dai browser
dei visitatori. Il repository registra solo QUALE versione usare (commit del dataset Hugging Face
in `territorio.lock.json`); i file si scaricano da quella versione, si verificano con le impronte
SHA-256 pubblicate da Gramscii (SHA256SUMS e census-sections-2021/manifest.json) e restano in
cache. Nel repository finiscono solo i derivati piccoli che servono al sito (es. mappa.json).

  python -m meteo_storico territorio verifica    # nuova versione Gramscii o ISTAT disponibile?
  python -m meteo_storico territorio blocca      # passa all'ultima versione (poi rigenerare i comuni)
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import httpx

log = logging.getLogger(__name__)
DATASET = "Gramscii-IT/european-territory-boundaries"
API = f"https://huggingface.co/api/datasets/{DATASET}"
LOCK = Path(__file__).resolve().parent / "territorio.lock.json"
REVISIONE_PREDEFINITA = "8aff37c269d8c9ff7fd4748f0f0599810302185b"   # 12/10/2026, comuni ISTAT 1/1/2026


def revisione() -> str:
    if LOCK.exists():
        return json.loads(LOCK.read_text(encoding="utf-8")).get("gramscii_revisione", REVISIONE_PREDEFINITA)
    return REVISIONE_PREDEFINITA


def url(percorso: str, rev: str | None = None) -> str:
    return f"https://huggingface.co/datasets/{DATASET}/resolve/{rev or revisione()}/{percorso}"


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _impronte(cache: Path, rev: str) -> dict[str, str]:
    p = cache / f"impronte_{rev[:12]}.json"
    if p.exists():
        return json.loads(p.read_text())
    imp = {}
    r = httpx.get(url("SHA256SUMS", rev), follow_redirects=True, timeout=60)
    if r.status_code == 200:
        for riga in r.text.splitlines():
            if riga.strip():
                h, nome = riga.split(maxsplit=1)
                imp[nome.strip()] = h
    r = httpx.get(url("census-sections-2021/manifest.json", rev), follow_redirects=True, timeout=60)
    if r.status_code == 200:
        for reg in r.json().get("regions", {}).values():
            imp[reg["file"]] = reg["sha256"]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(imp))
    return imp


def scarica(percorso: str, cache: Path, rev: str | None = None) -> Path:
    """Scarica (se manca) e verifica un file del dataset alla revisione bloccata."""
    rev = rev or revisione()
    dest = cache / "gramscii" / rev[:12] / percorso
    attesa = _impronte(cache, rev).get(percorso)
    if dest.exists() and (attesa is None or _sha256(dest) == attesa):
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    log.info("Scarico %s (revisione %s)", percorso, rev[:12])
    with httpx.stream("GET", url(percorso, rev), follow_redirects=True, timeout=300) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for b in r.iter_bytes(1 << 20):
                f.write(b)
    if attesa and _sha256(tmp) != attesa:
        tmp.unlink()
        raise RuntimeError(f"Impronta SHA-256 non corrispondente per {percorso}: file alterato o incompleto")
    tmp.replace(dest)
    return dest


def ultima_revisione() -> dict:
    d = httpx.get(API, timeout=30).json()
    return {"revisione": d.get("sha"), "modificato": d.get("lastModified")}


def blocca(rev: str, istat_sha256: str | None = None) -> None:
    dati = json.loads(LOCK.read_text(encoding="utf-8")) if LOCK.exists() else {}
    dati["gramscii_revisione"] = rev
    if istat_sha256:
        dati["istat_elenco_sha256"] = istat_sha256
    LOCK.write_text(json.dumps(dati, indent=1), encoding="utf-8")
