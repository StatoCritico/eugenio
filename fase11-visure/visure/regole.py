"""Caricamento delle regole di riconoscimento (regole.toml nel pacchetto, più un file dell'utente facoltativo)."""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

FLAG = re.IGNORECASE | re.MULTILINE


@dataclass
class Regole:
    grezze: dict
    compilate: dict = field(default_factory=dict)

    def lista(self, sezione: str, voce: str) -> list[re.Pattern]:
        chiave = (sezione, voce)
        if chiave not in self.compilate:
            v = self.grezze.get(sezione, {}).get(voce, [])
            self.compilate[chiave] = [re.compile(x, FLAG) for x in ([v] if isinstance(v, str) else v)]
        return self.compilate[chiave]

    def cerca(self, sezione: str, voce: str, testo: str) -> re.Match | None:
        for p in self.lista(sezione, voce):
            m = p.search(testo)
            if m:
                return m
        return None

    def valore(self, sezione: str, voce: str, testo: str) -> str | None:
        m = self.cerca(sezione, voce, testo)
        if not m:
            return None
        return (m.group(1) if m.groups() else m.group(0)).strip()

    def c_e(self, sezione: str, voce: str, testo: str) -> bool:
        return self.cerca(sezione, voce, testo) is not None

    @property
    def colonne(self) -> dict[str, list[str]]:
        return self.grezze.get("tabella", {}).get("colonne", {})


def _unisci(base: dict, altro: dict) -> dict:
    out = dict(base)
    for k, v in altro.items():
        out[k] = _unisci(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def carica(file_utente: str | Path | None = None) -> Regole:
    """Regole del pacchetto (lette anche da uno zip, per l'avviatore) con le voci del file dell'utente al posto delle
    corrispondenti."""
    base = tomllib.loads(resources.files("visure").joinpath("regole.toml").read_text(encoding="utf-8"))
    if file_utente:
        base = _unisci(base, tomllib.loads(Path(file_utente).read_text(encoding="utf-8")))
    return Regole(base)
