"""File caricati dagli utenti in Excel (.xlsx) od OpenDocument (.ods): conversione nel CSV che le pagine già capiscono.

Così chi ha i dati in un foglio di calcolo non deve convertirli a mano. Si usa il **primo foglio**; date e ore
diventano AAAA-MM-GG [hh:mm:ss], i numeri hanno il punto decimale, il separatore è il punto e virgola.
Tutto in memoria: il file non viene salvato. Il vecchio formato .xls (Excel 97–2003) non è letto: va salvato in .xlsx.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import math
import zipfile

import pandas as pd

ESTENSIONI = (".csv", ".txt", ".xlsx", ".ods")


def tipo(dati: bytes) -> str:
    """'xlsx', 'ods', 'xls' oppure 'csv' (tutto il resto: testo), riconosciuto dal contenuto e non dal nome."""
    if dati[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "xls"
    if dati[:4] == b"PK\x03\x04":
        try:
            with zipfile.ZipFile(io.BytesIO(dati)) as z:
                nomi = z.namelist()
                if "mimetype" in nomi and b"opendocument.spreadsheet" in z.read("mimetype"):
                    return "ods"
                if any(n.startswith("xl/") for n in nomi):
                    return "xlsx"
        except zipfile.BadZipFile:
            pass
        raise ValueError("Il file è un archivio compresso ma non è un foglio Excel (.xlsx) né OpenDocument (.ods)")
    return "csv"


def _cella(v) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)) or v is pd.NaT:
        return ""
    if isinstance(v, (pd.Timestamp, dt.datetime)):
        return v.strftime("%Y-%m-%d") if (v.hour, v.minute, v.second, v.microsecond) == (0, 0, 0, 0) \
            else v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, dt.date):
        return v.isoformat()
    if isinstance(v, dt.time):
        return v.strftime("%H:%M:%S")
    if isinstance(v, bool):
        return "vero" if v else "falso"
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() and abs(v) < 1e15 else repr(v)
    return str(v).strip()


def fogli(dati: bytes) -> list[str]:
    t = tipo(dati)
    if t not in ("xlsx", "ods"):
        return []
    return list(pd.ExcelFile(io.BytesIO(dati), engine="openpyxl" if t == "xlsx" else "odf").sheet_names)


def in_csv(dati: bytes, max_righe: int | None = None) -> bytes:
    """Restituisce i byte di un CSV: invariati se il file è già testo, convertiti se è .xlsx o .ods."""
    t = tipo(dati)
    if t == "csv":
        return dati
    if t == "xls":
        raise ValueError("Il formato .xls (Excel 97–2003) non è supportato: salva il file come .xlsx, .ods o .csv")
    df = pd.read_excel(io.BytesIO(dati), sheet_name=0, header=None, dtype=object,
                       engine="openpyxl" if t == "xlsx" else "odf")
    righe = [[_cella(v) for v in r] for r in df.itertuples(index=False, name=None)]
    # via righe e colonne vuote in fondo (i fogli spesso hanno celle formattate ma vuote)
    while righe and not any(righe[-1]):
        righe.pop()
    larghezza = max((max((k + 1 for k, v in enumerate(r) if v), default=0) for r in righe), default=0)
    if not righe or not larghezza:
        raise ValueError("Il primo foglio del file è vuoto")
    if max_righe and len(righe) > max_righe + 1:
        raise ValueError(f"Troppe righe ({len(righe) - 1}): massimo {max_righe}")
    out = io.StringIO()
    w = csv.writer(out, delimiter=";", lineterminator="\r\n")
    for r in righe:
        w.writerow(r[:larghezza])
    return out.getvalue().encode("utf-8")
