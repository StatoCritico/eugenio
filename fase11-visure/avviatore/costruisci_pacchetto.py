"""Pacchetto riproducibile del lettore (visure-<versione>.zip) e voce dell'elenco delle versioni approvate.

Lo zip contiene la cartella visure/ (Python puro, regole.toml) e, dal 04/11/2026, edifici3d/__init__.py e
edifici3d/importa.py della fase 10 (conversione dei modelli DXF/IFC): stesse sorgenti → stesso file, byte per byte
(ordine fisso, date fisse, permessi fissi), quindi la stessa impronta SHA-256 su qualunque PC o in GitHub Actions.

  python avviatore/costruisci_pacchetto.py                    # crea dist/visure-<v>.zip e stampa la voce
  python avviatore/costruisci_pacchetto.py --aggiorna-elenco  # e la scrive in avviatore/versioni_approvate.json

Approvare una versione = provarla (test verdi, prova con visure vere anonimizzate), poi aggiornare l'elenco nel
repository con la sua impronta e pubblicare lo zip come allegato della release `visure-v<versione>`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import date
from pathlib import Path

QUI = Path(__file__).resolve().parent
FASE = QUI.parent
DATA_FISSA = (2026, 1, 1, 0, 0, 0)
URL_RELEASE = "https://github.com/statocritico/eugenio/releases/download/visure-v{v}/visure-{v}.zip"


def versione() -> str:
    m = re.search(r'VERSIONE\s*=\s*"([^"]+)"', (FASE / "visure" / "__init__.py").read_text(encoding="utf-8"))
    return m.group(1)


# convertitore dei modelli DXF/IFC (04/11/2026): lo stesso file della fase 10, copiato nel pacchetto accanto a visure/
FASE10 = FASE.parent / "fase10-edifici3d"
DALLA_FASE10 = ("edifici3d/__init__.py", "edifici3d/importa.py")


def file_del_pacchetto() -> list[tuple[str, Path]]:
    """(nome nello zip, file) in ordine fisso: visure/ e i due file di edifici3d/ della fase 10."""
    out = [(p.relative_to(FASE).as_posix(), p) for p in (FASE / "visure").rglob("*")
           if p.is_file() and "__pycache__" not in p.parts and p.suffix in (".py", ".toml")]
    for n in DALLA_FASE10:
        if not (FASE10 / n).is_file():
            raise SystemExit(f"manca {FASE10 / n}: il pacchetto si costruisce dal repository completo")
        out.append((n, FASE10 / n))
    return sorted(out)


def costruisci(uscita: Path | None = None) -> tuple[Path, str]:
    v = versione()
    uscita = uscita or (FASE / "dist")
    uscita.mkdir(parents=True, exist_ok=True)
    dest = uscita / f"visure-{v}.zip"
    with zipfile.ZipFile(dest, "w") as z:
        for nome, p in file_del_pacchetto():
            info = zipfile.ZipInfo(nome, DATA_FISSA)
            # senza compressione: zlib e zlib-ng (Windows/Linux, versioni di Python diverse) comprimono in modo
            # diverso e l'impronta cambierebbe secondo dove si costruisce il pacchetto
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o644 << 16
            info.create_system = 3
            # a capo sempre \n: lo stesso zip anche da un checkout Windows con autocrlf
            z.writestr(info, p.read_bytes().replace(b"\r\n", b"\n"))
    return dest, hashlib.sha256(dest.read_bytes()).hexdigest()


def voce(v: str, sha: str) -> dict:
    return {"versione": v, "data": date.today().isoformat(), "file": f"visure-{v}.zip", "sha256": sha,
            "url": URL_RELEASE.format(v=v), "minimo_avviatore": "0.1.0", "stato": "approvata"}


def aggiorna_elenco(v: str, sha: str, file: Path = QUI / "versioni_approvate.json", revoca: bool = False) -> dict:
    e = json.loads(file.read_text(encoding="utf-8"))
    vecchie = [x for x in e["versioni"] if x["versione"] != v]
    prima = next((x for x in e["versioni"] if x["versione"] == v), None)
    nuova = voce(v, sha)
    if revoca and prima and prima["sha256"] != sha:
        # versione già pubblicata e poi cambiata: la vecchia impronta si revoca (nessuno deve usare due 0.1.0 diverse).
        # Meglio comunque alzare il numero di versione a ogni cambiamento dopo la pubblicazione.
        e["revocate"] = sorted(set(e.get("revocate", [])) | {prima["sha256"]})
    e["versioni"] = sorted(vecchie + [nuova], key=lambda x: tuple(int(n) for n in x["versione"].split(".")))
    file.write_text(json.dumps(e, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return e


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--uscita", type=Path)
    ap.add_argument("--aggiorna-elenco", action="store_true")
    ap.add_argument("--revoca", action="store_true", help="revoca l'impronta precedente della stessa versione")
    a = ap.parse_args()
    dest, sha = costruisci(a.uscita)
    print(dest)
    print(f"SHA-256 {sha}")
    print(json.dumps(voce(versione(), sha), indent=1))
    if a.aggiorna_elenco:
        aggiorna_elenco(versione(), sha, revoca=a.revoca)
        print("elenco aggiornato:", QUI / "versioni_approvate.json")
