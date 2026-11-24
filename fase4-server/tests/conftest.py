"""Impostazioni comuni delle prove della fase 4 (19/11/2026): nessuna prova deve leggere il DTM nazionale vero da Zenodo
(servizio/terreno.py): la fonte remota è spenta, le prove che la usano la accendono con un file o un servizio simulato."""
import os

os.environ.setdefault("TERRENO_NAZIONALE_URL", "")

# (24/11/2026 sera) come nel container (api/Dockerfile copia i pacchetti delle altre fasi in /app): le prove trovano da
# sole `territorio` (fase 7), `meteo_storico` (fase 3), `mercati_energia` (fase 6) e gli altri, senza PYTHONPATH a mano.
# La fase 10 va prima (il suo `edifici3d` è quello vero), le altre dopo, in coda, per non coprire `servizio`.
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

_RADICE = Path(__file__).resolve().parents[2]
_f10 = str(_RADICE / "fase10-edifici3d")
if (_RADICE / "fase10-edifici3d").exists() and _f10 not in sys.path:
    sys.path.insert(0, _f10)
for _fase in ("fase3-storico", "fase6-mercati", "fase7-territorio", "fase8-indicatori", "fase15-elettricita", "fase16-suolo", "fase17-cer-fv"):
    _p = str(_RADICE / _fase)
    if (_RADICE / _fase).exists() and _p not in sys.path:
        sys.path.append(_p)
