"""Fonti per regione (fase 10, Fase E): lettura e controllo di `fonti/regioni.toml`, riepilogo, prova dal vivo.

Il file registra, per ogni regione e provincia autonoma, DB topografici con altezze, DTM, DSM/LiDAR e ortofoto con
licenza, stato («attiva», «in attesa», «non disponibile»), data della verifica e collegamenti. Regola: una fonte è
«attiva» solo con una licenza compatibile con la CC BY 4.0 di EuGEnio scritta in una scheda ufficiale e un servizio o
download provato dal vivo; solo le fonti attive si possono accendere nei TOML di EuGEnio (ortofoto/, fonti/, zone/).

  python -m edifici3d regioni                 # riepilogo per regione
  python -m edifici3d regioni --prova         # ricontrolla dal vivo gli url_prova (dal server: alcuni portali
                                              # chiudono le connessioni che arrivano da fuori Italia)
  python -m edifici3d regioni --markdown      # tabella per il README
"""
from __future__ import annotations

import tomllib
from pathlib import Path

QUI = Path(__file__).resolve().parent.parent
FILE = QUI / "fonti" / "regioni.toml"
STATI = ("attiva", "in attesa", "non disponibile")
TEMI = ("edifici", "dtm", "dsm", "ortofoto")
INCOMPATIBILI = ("nc", "non commerciale", "by-sa", "diritti riservati", "copyright", "agea")


def carica(percorso: Path = FILE) -> dict:
    return tomllib.loads(Path(percorso).read_text(encoding="utf-8"))


def controlla(d: dict) -> list[str]:
    """Errori di forma e di regola (vuoto = tutto bene)."""
    err = []
    compatibili = set(d.get("licenze_compatibili") or [])
    regioni = d.get("regione") or []
    if len(regioni) != 21:
        err.append(f"attese 21 voci (19 regioni + 2 province autonome), trovate {len(regioni)}")
    for r in regioni:
        temi = [f.get("tema") for f in r.get("fonte", [])]
        for t in TEMI:
            if t not in temi:
                err.append(f"{r.get('nome')}: manca il tema {t}")
        for f in r.get("fonte", []):
            err += _controlla_fonte(f, r.get("nome", "?"), compatibili)
    for f in d.get("nazionale") or []:
        err += _controlla_fonte(f, "nazionale", compatibili | {"ODbL 1.0"})
    return err


def _controlla_fonte(f: dict, dove: str, compatibili: set[str]) -> list[str]:
    err = []
    n = f"{dove} / {f.get('tema')} / {f.get('nome')}"
    if f.get("stato") not in STATI:
        err.append(f"{n}: stato {f.get('stato')!r} non valido")
    if not f.get("verifica"):
        err.append(f"{n}: manca la data della verifica")
    if f.get("stato") == "attiva":
        lic = str(f.get("licenza", ""))
        if not any(lic.startswith(c) for c in compatibili):
            err.append(f"{n}: attiva con licenza {lic!r} non compatibile")
        if any(x in lic.lower() for x in INCOMPATIBILI):
            err.append(f"{n}: attiva con licenza {lic!r} che contiene una clausola incompatibile")
        if not (f.get("scheda") or f.get("usata_in")):
            err.append(f"{n}: attiva senza scheda")
        if not (f.get("prova") or f.get("usata_in")):
            err.append(f"{n}: attiva senza prova dal vivo")
    if f.get("stato") in ("in attesa", "non disponibile") and not f.get("motivo"):
        err.append(f"{n}: manca il motivo")
    return err


def riepilogo(d: dict) -> list[dict]:
    out = []
    for r in d.get("regione") or []:
        riga = {"codice": r["codice"], "nome": r["nome"]}
        for t in TEMI:
            fs = [f for f in r.get("fonte", []) if f.get("tema") == t]
            riga[t] = fs[0]["stato"] if fs else "—"
        out.append(riga)
    return out


def conteggi(d: dict) -> dict[str, int]:
    c = {s: 0 for s in STATI}
    for r in d.get("regione") or []:
        for f in r.get("fonte", []):
            c[f["stato"]] += 1
    return c


def markdown(d: dict) -> str:
    sigla = {"attiva": "**attiva**", "in attesa": "in attesa", "non disponibile": "—"}
    righe = ["| Regione | Edifici (altezze) | DTM | DSM / LiDAR | Ortofoto |", "|---|---|---|---|---|"]
    for r in riepilogo(d):
        righe.append(f"| {r['nome']} | " + " | ".join(sigla.get(r[t], r[t]) for t in TEMI) + " |")
    return "\n".join(righe)


def prova(d: dict, client=None) -> list[dict]:
    """Ricontrolla gli url_prova (al più il primo kB): codice HTTP e tipo. Non tocca il file."""
    import httpx
    proprio = client is None
    client = client or httpx.Client(timeout=30, follow_redirects=True,
                                    headers={"User-Agent": "EuGEnio-verifica/1.0 (eugenio.statocritico.it)",
                                             "Range": "bytes=0-1023"})
    out = []
    try:
        for r in list(d.get("regione") or []) + [{"nome": "nazionale", "fonte": d.get("nazionale") or []}]:
            for f in r.get("fonte", []):
                u = f.get("url_prova")
                if not u:
                    continue
                try:
                    x = client.get(u)
                    esito = f"{x.status_code} {x.headers.get('content-type', '')}".strip()
                except Exception as e:
                    esito = f"errore: {type(e).__name__}"
                out.append({"regione": r["nome"], "tema": f["tema"], "nome": f["nome"], "stato": f["stato"], "esito": esito})
    finally:
        if proprio:
            client.close()
    return out
