"""Rispetto dei limiti dell'API gratuita di Open-Meteo (uso non commerciale).

Limiti pubblicati: 600 chiamate/minuto, 5.000/ora, 10.000/giorno, 300.000/mese.
Una richiesta "pesa" più di una chiamata se chiede più di 10 variabili, più di 2 settimane o più
punti: peso = punti × max(1, giorni/14) × max(1, variabili/10).

Il consumo è salvato su file, così il conteggio sopravvive a interruzioni e riavvii.
Con un'istanza Open-Meteo locale (docker) i limiti non servono: usare `illimitato=True`.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

log = logging.getLogger(__name__)

LIMITI = {60: 600, 3600: 5000, 86400: 10000, 30 * 86400: 300000}
MARGINE = 0.9


def peso(punti: int, giorni: int, variabili: int) -> float:
    return punti * max(1.0, giorni / 14) * max(1.0, variabili / 10)


class Limitatore:
    def __init__(self, file_stato: Path, illimitato: bool = False):
        self.file = file_stato
        self.illimitato = illimitato
        self.eventi: list[tuple[float, float]] = []
        if file_stato.exists():
            try:
                self.eventi = [tuple(e) for e in json.loads(file_stato.read_text())]
            except Exception:
                self.eventi = []

    def _pulisci(self, ora: float) -> None:
        self.eventi = [e for e in self.eventi if ora - e[0] < max(LIMITI)]

    def _usato(self, ora: float, finestra: int) -> float:
        return sum(w for t, w in self.eventi if ora - t < finestra)

    def attendi(self, w: float) -> None:
        if self.illimitato:
            return
        while True:
            ora = time.time()
            self._pulisci(ora)
            attesa = 0.0
            for finestra, lim in LIMITI.items():
                if self._usato(ora, finestra) + w > lim * MARGINE:
                    # aspetta che escano dalla finestra abbastanza eventi
                    cum = self._usato(ora, finestra) + w - lim * MARGINE
                    for t, ww in sorted(self.eventi):
                        if ora - t < finestra:
                            cum -= ww
                            if cum <= 0:
                                attesa = max(attesa, t + finestra - ora + 1)
                                break
                    else:
                        attesa = max(attesa, finestra)
            if attesa <= 0:
                return
            if finestra >= 30 * 86400 and attesa > 86400:
                raise RuntimeError("Raggiunto il limite mensile dell'API gratuita: riprendere il mese prossimo "
                                   "o usare un'istanza Open-Meteo locale (vedi README).")
            log.info("Limite API: attendo %.0f s", attesa)
            time.sleep(min(attesa, 900))

    def registra(self, w: float) -> None:
        if self.illimitato:
            return
        self.eventi.append((time.time(), w))
        self.file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.eventi))
        tmp.replace(self.file)

    def riepilogo(self) -> str:
        ora = time.time()
        self._pulisci(ora)
        nomi = {60: "minuto", 3600: "ora", 86400: "giorno", 30 * 86400: "30 giorni"}
        return ", ".join(f"{nomi[f]} {self._usato(ora, f):.0f}/{l}" for f, l in LIMITI.items())
