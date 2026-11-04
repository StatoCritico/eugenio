"""File prodotti dal lettore.

  Visure_AAAA-MM-GG/
    indice.csv                      una riga per unità immobiliare (fabbricati e terreni), senza dati personali
    edifici_visure.csv              una riga per particella, con le colonne visura_… (senza file di Patrimonio)
    patrimonio_con_visure.csv       il file di Patrimonio con le colonne visura_… (solo con --patrimonio)
    visure.json                     unità ed edifici insieme: la pagina Patrimonio lo legge direttamente
    registro.txt                    esito di ogni PDF e motivi
    pdf/<Comune>_<Belfiore>/F<foglio>_P<particella>/sub_<n>.pdf   copie ordinate (solo con --ordina)
    intestatari_DATI_PERSONALI.csv  solo con --includi-intestatari: dati personali, da non condividere

CSV con «;» e virgola decimale (Excel in italiano), UTF-8 con BOM.
"""
from __future__ import annotations

import csv
import io
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from . import VERSIONE
from .arricchisci import COLONNE_EDIFICIO, abbina, edifici_da_unita
from .lettore import CAMPI_UNITA, Visura

AVVERTENZA = ("Dati letti automaticamente dalle visure catastali: non sostituiscono le visure ufficiali dell'Agenzia "
              "delle Entrate e vanno controllati. Vietato usarli per re-identificare persone.")


def _cella(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return (str(int(v)) if v.is_integer() else f"{v:.2f}".rstrip("0").rstrip(".")).replace(".", ",")
    return str(v)


def scrivi_csv(percorso: Path, righe: list[dict], colonne: list[str]) -> None:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    w.writerow(colonne)
    for r in righe:
        w.writerow([_cella(r.get(c)) for c in colonne])
    percorso.write_text("﻿" + buf.getvalue(), encoding="utf-8")


def leggi_csv(dati: bytes | str | Path) -> list[dict]:
    """CSV di Patrimonio (separatore ; o , ; UTF-8 o Windows-1252); le righe di nota che iniziano con # si saltano."""
    if isinstance(dati, Path) or (isinstance(dati, str) and not ("\n" in dati or ";" in dati)):
        dati = Path(dati).read_bytes()
    if isinstance(dati, bytes):
        try:
            dati = dati.decode("utf-8-sig")
        except UnicodeDecodeError:
            dati = dati.decode("cp1252")
    righe = [r for r in dati.splitlines() if r.strip()]
    while righe and righe[0].lstrip().startswith("#"):
        righe.pop(0)
    if not righe:
        return []
    sep = ";" if righe[0].count(";") >= righe[0].count(",") else ","
    lett = csv.reader(righe, delimiter=sep)
    titoli = [t.strip() for t in next(lett)]
    return [dict(zip(titoli, [c.strip() for c in r] + [""] * (len(titoli) - len(r)))) for r in lett if any(c.strip() for c in r)]


def _nome_cartella(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", s or "").strip("_") or "senza_nome"


def ordina_pdf(visure: list[Visura], sorgenti: dict[str, Path], cartella: Path) -> int:
    """Copia ogni visura per immobile in pdf/<Comune>_<Belfiore>/F<foglio>_P<particella>/sub_<n>.pdf; le visure per
    soggetto (molte particelle) vanno in pdf/per_soggetto/."""
    n = 0
    for v in visure:
        src = sorgenti.get(v.file)
        if not src or not v.unita:
            continue
        if v.tipo_visura and v.tipo_visura.startswith("per soggetto") or len({(u["foglio"], u["particella"]) for u in v.unita}) > 1:
            dest = cartella / "pdf" / "per_soggetto" / v.file
        else:
            u = v.unita[0]
            sub = f"sub_{u['subalterno']}" if u.get("subalterno") else ("terreno" if u.get("catasto") == "T" else "sub_0")
            dest = (cartella / "pdf" / f"{_nome_cartella(u.get('comune'))}_{u.get('codice_comune') or 'X000'}"
                    / f"F{u['foglio']}_P{_nome_cartella(u['particella'])}" / f"{sub}.pdf")
            k = 2
            while dest.exists():
                dest = dest.with_name(f"{sub}_{k}.pdf")
                k += 1
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        n += 1
    return n


def risultato(visure: list[Visura], patrimonio: list[dict] | None = None) -> dict:
    """Tutto in memoria: unità, edifici (dal patrimonio o per particella), unità non abbinate, registro."""
    unita = [u for v in visure for u in v.unita]
    if patrimonio is not None:
        edifici, sciolte = abbina(patrimonio, unita)
    else:
        edifici, sciolte = edifici_da_unita(unita), []
    return {"unita": unita, "edifici": edifici, "non_abbinate": sciolte, "con_patrimonio": patrimonio is not None}


def registro(visure: list[Visura], ris: dict, includi_intestatari: bool) -> str:
    righe = [f"EuGEnio Visure {VERSIONE} – {datetime.now():%d/%m/%Y %H:%M}", AVVERTENZA, ""]
    for v in visure:
        righe.append(f"{v.file}: {v.esito}" + (f" – {v.tipo_visura}" if v.tipo_visura else "")
                     + (f", visura del {v.data_visura}" if v.data_visura else "")
                     + f", {len(v.unita)} unità" + (f" ({v.nota})" if v.nota else ""))
        for u in v.unita:
            if u.get("esito") != "ok":
                righe.append(f"   foglio {u.get('foglio')} particella {u.get('particella')} sub {u.get('subalterno') or '-'}: "
                             f"{u.get('nota')}")
        if v.righe_personali:
            righe.append(f"   {v.righe_personali} righe con dati personali tolte prima della lettura"
                         + (" (intestatari salvati a parte, su richiesta)" if includi_intestatari else ""))
    if ris["con_patrimonio"]:
        c = {}
        for e in ris["edifici"]:
            c[e["visura_esito"]] = c.get(e["visura_esito"], 0) + 1
        righe += ["", f"Patrimonio: {len(ris['edifici'])} edifici – " + ", ".join(f"{k} {n}" for k, n in sorted(c.items())),
                  f"Unità non abbinate a nessun edificio: {len(ris['non_abbinate'])}"]
        for u in ris["non_abbinate"]:
            righe.append(f"   {u.get('comune')} foglio {u.get('foglio')} particella {u.get('particella')} sub "
                         f"{u.get('subalterno') or '-'} ({u.get('file')})")
    return "\n".join(righe) + "\n"


def json_risultato(ris: dict) -> dict:
    return {"formato": "eugenio-visure", "versione_formato": 1, "programma": f"EuGEnio Visure {VERSIONE}",
            "generato": datetime.now().isoformat(timespec="seconds"), "avvertenza": AVVERTENZA,
            "unita": [{k: u.get(k) for k in CAMPI_UNITA} for u in ris["unita"]],
            "edifici": ris["edifici"]}


def scrivi(cartella: Path, visure: list[Visura], patrimonio: list[dict] | None = None,
           colonne_patrimonio: list[str] | None = None, includi_intestatari: bool = False,
           sorgenti: dict[str, Path] | None = None, ordina: bool = False) -> dict:
    cartella.mkdir(parents=True, exist_ok=True)
    ris = risultato(visure, patrimonio)
    scrivi_csv(cartella / "indice.csv", ris["unita"], CAMPI_UNITA)
    if patrimonio is not None:
        col = list(colonne_patrimonio or (list(patrimonio[0]) if patrimonio else []))
        scrivi_csv(cartella / "patrimonio_con_visure.csv", ris["edifici"], col + [c for c in COLONNE_EDIFICIO if c not in col])
    else:
        base = ["id", "comune", "codice_comune", "sezione", "foglio", "particella", "indirizzo"]
        scrivi_csv(cartella / "edifici_visure.csv", ris["edifici"], base + COLONNE_EDIFICIO)
    (cartella / "visure.json").write_text(json.dumps(json_risultato(ris), ensure_ascii=False, indent=1), encoding="utf-8")
    (cartella / "registro.txt").write_text(registro(visure, ris, includi_intestatari), encoding="utf-8")
    if includi_intestatari:
        righe = [{"file": v.file, **i} for v in visure for i in v.intestatari]
        scrivi_csv(cartella / "intestatari_DATI_PERSONALI.csv", righe, ["file", "riga", "codici_fiscali", "diritto"])
    if ordina and sorgenti:
        ris["pdf_ordinati"] = ordina_pdf(visure, sorgenti, cartella)
    return ris
