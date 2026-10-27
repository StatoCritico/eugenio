"""Richieste HTTP con cache su disco, pause tra le richieste e qualche nuovo tentativo.

Tutte le fonti sono pubbliche e senza chiavi: qui non c'è nessun segreto.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path

import httpx

log = logging.getLogger("indicatori_ssn")
AGENTE = "EuGEnio-indicatori/1.0 (+https://eugenio.statocritico.it; dati aperti, senza scopo di lucro)"


class FonteNonDisponibile(RuntimeError):
    """La fonte risponde, ma non con i dati (manutenzione, errore del server, formato inatteso)."""


class Rete:
    def __init__(self, cache: Path, pausa: float = 2.0, tentativi: int = 3, timeout: float = 180.0,
                 rinnova: bool = False):
        self.cache = Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.pausa = pausa
        self.tentativi = tentativi
        self.rinnova = rinnova           # True: ignora i file in cache e riscarica
        self._ultima = 0.0
        self.client = httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": AGENTE})

    def _aspetta(self):
        attesa = self.pausa - (time.monotonic() - self._ultima)
        if attesa > 0:
            time.sleep(attesa)
        self._ultima = time.monotonic()

    def nome_cache(self, *parti) -> Path:
        h = hashlib.sha1(json.dumps(parti, sort_keys=True, default=str).encode()).hexdigest()[:16]
        return self.cache / f"{h}"

    def richiesta(self, metodo: str, url: str, *, json_corpo=None, accetta: str | None = None,
                  atteso: str | None = None, flusso_in: Path | None = None) -> httpx.Response | Path:
        """Una richiesta con nuovi tentativi. `atteso`: parte del Content-Type richiesta (es. "json"):
        se il server risponde con altro (la pagina di manutenzione di OpenBDAP è HTML) è un errore.
        `flusso_in`: scrive il corpo in quel file (risposte grandi) e restituisce il percorso."""
        intest = {"Accept": accetta} if accetta else {}
        ultimo = None
        for n in range(1, self.tentativi + 1):
            self._aspetta()
            try:
                if flusso_in is not None:
                    tmp = flusso_in.with_suffix(flusso_in.suffix + ".parziale")
                    with self.client.stream(metodo, url, json=json_corpo, headers=intest) as r:
                        self._controlla(r, atteso, url)
                        with open(tmp, "wb") as f:
                            for blocco in r.iter_bytes(1 << 16):
                                f.write(blocco)
                    tmp.replace(flusso_in)
                    return flusso_in
                r = self.client.request(metodo, url, json=json_corpo, headers=intest)
                self._controlla(r, atteso, url)
                return r
            except FonteNonDisponibile as e:
                ultimo = e
                if "manutenzione" in str(e):
                    break                     # inutile insistere
            except httpx.HTTPError as e:
                ultimo = e
            log.warning("tentativo %d di %d non riuscito per %s: %s", n, self.tentativi, url, ultimo)
            time.sleep(self.pausa * 2 * n)
        raise FonteNonDisponibile(f"{url}: {ultimo}")

    @staticmethod
    def _controlla(r: httpx.Response, atteso: str | None, url: str):
        if r.status_code >= 400:
            raise FonteNonDisponibile(f"errore HTTP {r.status_code}")
        tipo = r.headers.get("Content-Type", "")
        if atteso and atteso not in tipo:
            if "html" in tipo:
                raise FonteNonDisponibile("la fonte risponde con una pagina HTML (manutenzione o servizio sospeso)")
            raise FonteNonDisponibile(f"tipo di risposta inatteso: {tipo or 'nessuno'}")

    def json(self, metodo: str, url: str, corpo=None, *, chiave=None) -> dict:
        """JSON con cache: la stessa richiesta non si ripete se il file c'è già."""
        f = self.nome_cache(metodo, url, corpo, chiave).with_suffix(".json")
        if f.exists() and not self.rinnova:
            return json.loads(f.read_text(encoding="utf-8"))
        r = self.richiesta(metodo, url, json_corpo=corpo, atteso="json")
        d = r.json()
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        return d

    def chiudi(self):
        self.client.close()
