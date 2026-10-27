"""Lettura dei file .om di Open-Meteo dal bucket pubblico AWS (s3://openmeteo), senza credenziali.

I file .om sono divisi in blocchi (chunk) di 1 riga di latitudine × 6 longitudini × N ore, salvati in
ordine (lat, lon, tempo): i blocchi di una stessa riga sono contigui. OmFileReader chiede un intervallo di
byte per ogni blocco; questo adattatore raggruppa le richieste in blocchi da `blocco` byte allineati e li
tiene in memoria (LRU), così una riga dell'Italia costa una o due richieste HTTP invece di centinaia.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict

import fsspec

BUCKET = "openmeteo"


class FSBlocchi:
    def __init__(self, blocco: int = 256 << 10, blocco_chunk: int = 64 << 10, max_blocchi: int = 4096,
                 tentativi: int = 6):
        self.fs = fsspec.filesystem("s3", anon=True)
        self.B_anno = blocco          # file year_AAAA.om: una riga d'Italia occupa ~200 kB contigui
        self.B_chunk = blocco_chunk   # file chunk_N.om (504 ore): ~10 kB per riga d'Italia
        self.max = max_blocchi
        self.tentativi = tentativi
        self.cache: OrderedDict = OrderedDict()
        self.dim: dict = {}
        self.lock = threading.Lock()
        self.byte_scaricati = 0
        self.richieste = 0

    def size(self, path):
        if path not in self.dim:
            self.dim[path] = self.fs.size(path)
        return self.dim[path]

    def _B(self, path):
        return self.B_chunk if "/chunk_" in path else self.B_anno

    def _blocco(self, path, n):
        B = self._B(path)
        k = (path, n)
        with self.lock:
            if k in self.cache:
                self.cache.move_to_end(k)
                return self.cache[k]
        a = n * B
        b = min(a + B, self.size(path))
        for t in range(self.tentativi):
            try:
                dati = self.fs.cat_file(path, start=a, end=b)
                break
            except Exception:  # rete instabile: riprova con attesa crescente
                if t == self.tentativi - 1:
                    raise
                time.sleep(2 ** t)
        with self.lock:
            self.byte_scaricati += len(dati)
            self.richieste += 1
            self.cache[k] = dati
            while len(self.cache) > self.max:
                self.cache.popitem(last=False)
        return dati

    def cat_file(self, path, start=None, end=None, **kw):
        tot = self.size(path)
        start = 0 if start is None else (start if start >= 0 else tot + start)
        end = tot if end is None else (end if end >= 0 else tot + end)
        parti = []
        B = self._B(path)
        for n in range(start // B, (end - 1) // B + 1):
            d = self._blocco(path, n)
            a = max(start - n * B, 0)
            b = min(end - n * B, len(d))
            parti.append(d[a:b])
        return b"".join(parti)

    def svuota(self, path=None):
        with self.lock:
            for k in [k for k in self.cache if path is None or k[0] == path]:
                del self.cache[k]
