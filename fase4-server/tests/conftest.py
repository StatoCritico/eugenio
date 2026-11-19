"""Impostazioni comuni delle prove della fase 4 (19/11/2026): nessuna prova deve leggere il DTM nazionale vero da Zenodo
(servizio/terreno.py): la fonte remota è spenta, le prove che la usano la accendono con un file o un servizio simulato."""
import os

os.environ.setdefault("TERRENO_NAZIONALE_URL", "")
