"""OpenBDAP (Ragioneria Generale dello Stato): modello CE per ente, voci energetiche e totali.

Per ogni anno si scarica il CSV completo (datastore/dump/<ID>.csv) e lo si filtra; il catalogo non offre la
ricerca filtrata del datastore (datastore_search risponde 404).
In cache resta un CSV piccolo per anno con le sole voci di `costanti.VOCI`.
"""
from __future__ import annotations

import csv
import io
import logging
import re
from pathlib import Path

from . import costanti as K
from .rete import FonteNonDisponibile, Rete

log = logging.getLogger("indicatori_ssn")

CAMPI = ["anno", "cod_regione", "regione", "tipo_rilevazione", "cod_ente", "cod_ente_bdap", "ente", "voce",
         "data_aggiornamento", "importo"]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z]", "", s.lower())


# riconoscimento delle colonne dal nome (il CSV usa nomi lunghi con spazi e accenti)
_COLONNE = {
    "anno": ("annodiriferimento", "anno"),
    "cod_regione": ("codiceregione",),
    "regione": ("descrizioneregione",),
    "tipo_rilevazione": ("tiporilevazione",),
    "cod_ente": ("codiceentessn",),
    "cod_ente_bdap": ("codiceentebdap",),
    "ente": ("descrizioneente",),
    "voce": ("codicevocecontabile",),
    "data_aggiornamento": ("dataaggiornamento",),
    "importo": ("importototaleeuro", "importototale", "importo"),
}


def mappa_colonne(intestazione: list[str]) -> dict[str, str]:
    n = {_norm(c): c for c in intestazione}
    out = {}
    for campo, candidati in _COLONNE.items():
        for c in candidati:
            if c in n:
                out[campo] = n[c]
                break
    mancano = {"cod_regione", "cod_ente", "voce", "importo"} - set(out)
    if mancano:
        raise FonteNonDisponibile(f"CSV del CE senza le colonne {sorted(mancano)}: {intestazione}")
    return out


def importo(testo) -> float | None:
    """Importi del CE: '1234567.89', '1234567,89', '1.234.567,89' o numero."""
    if testo is None:
        return None
    if isinstance(testo, (int, float)):
        return float(testo)
    s = str(testo).strip().replace(" ", "").replace(" ", "")
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def codice(x, cifre=3) -> str:
    s = str(x or "").strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s.zfill(cifre) if s.isdigit() else s


def normalizza(riga: dict, colonne: dict[str, str], anno: int) -> dict | None:
    voce = str(riga.get(colonne["voce"], "")).strip().upper()
    if voce not in K.VOCI:
        return None
    out = {c: str(riga.get(colonne[c], "") if c in colonne else "").strip() for c in CAMPI}
    out["voce"] = voce
    out["cod_regione"] = codice(out["cod_regione"])
    out["cod_ente"] = codice(out["cod_ente"])
    out["anno"] = out["anno"][:4] if out["anno"][:4].isdigit() else str(anno)
    v = importo(riga.get(colonne["importo"]))
    out["importo"] = "" if v is None else repr(round(v, 2))
    return out


def filtra_csv(sorgente, anno: int):
    """Righe normalizzate delle sole voci utili da un CSV (file aperto in testo)."""
    campione = sorgente.read(8192)
    sorgente.seek(0)
    try:
        sep = csv.Sniffer().sniff(campione.split("\n", 1)[0], delimiters=",;|\t").delimiter
    except csv.Error:
        sep = ","
    r = csv.DictReader(sorgente, delimiter=sep)
    colonne = mappa_colonne(r.fieldnames or [])
    for riga in r:
        n = normalizza(riga, colonne, anno)
        if n:
            yield n


def scrivi_cache(righe, f: Path) -> int:
    tmp = f.with_suffix(".parziale")
    n = 0
    with open(tmp, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=CAMPI)
        w.writeheader()
        for riga in righe:
            w.writerow(riga)
            n += 1
    tmp.replace(f)
    return n


def scarica_anno(rete: Rete, anno: int, cartella: Path) -> Path:
    """CSV completo del CE dell'anno (datastore/dump; l'API del catalogo non offre datastore_search), filtrato
    sulle voci utili; il file completo si cancella e in cache resta solo ce_<anno>.csv."""
    cartella.mkdir(parents=True, exist_ok=True)
    f = cartella / f"ce_{anno}.csv"
    if f.exists() and not rete.rinnova:
        return f
    grezzo = cartella / f"ce_{anno}_completo.csv"
    rete.richiesta("GET", f"{K.CKAN}/datastore/dump/{K.DATASET_CE[anno]}.csv", atteso="csv", flusso_in=grezzo)
    with open(grezzo, encoding="utf-8-sig", newline="") as s:
        n = scrivi_cache(filtra_csv(s, anno), f)
    grezzo.unlink()
    if not n:
        raise FonteNonDisponibile(f"CE {anno}: nessuna riga con le voci cercate")
    log.info("CE %d: %d righe utili", anno, n)
    return f


def leggi(f: Path) -> list[dict]:
    with open(f, encoding="utf-8", newline="") as s:
        return list(csv.DictReader(s))


def metadati(rete: Rete, anno: int) -> dict:
    """Titolo, licenza e data di modifica del dataset (package_show)."""
    try:
        p = rete.json("GET", f"{K.CKAN}/action/package_show?id={K.DATASET_CE[anno]}").get("result") or {}
        return {"titolo": p.get("title"), "licenza": p.get("license_title") or p.get("license_id"),
                "modificato": p.get("metadata_modified")}
    except FonteNonDisponibile as e:
        return {"errore": str(e)}


def da_testo(testo: str, anno: int) -> list[dict]:
    """Per le prove: righe normalizzate da un CSV in memoria."""
    return list(filtra_csv(io.StringIO(testo), anno))


def leggi_testo(f: Path, anno: int) -> list[dict]:
    """Righe normalizzate da un CSV del CE così come lo pubblica OpenBDAP (anche completo)."""
    with open(f, encoding="utf-8-sig", newline="") as s:
        return list(filtra_csv(s, anno))
