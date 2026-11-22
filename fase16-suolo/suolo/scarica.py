"""Scaricamento dei dati per la pagina «Suolo e aree agricole» (fase 16, 22/11/2026). Niente indirizzi fissi dei file:
si legge l'elenco delle cartelle e si sceglie il file con l'anno e la versione più alti (il nome cambia a ogni edizione
e versione: v1.0 → v1.1 in pochi giorni).

  scarica(raw: Path, carte: bool = False, client=None) -> dict
      raw/ispra_indicatori.xlsx      indicatori del consumo di suolo per comune, provincia, regione e Italia
                                     (groupware SINAnet, cartella «indicatori», consumo_suolo_<AAAA>_Com_Prov_Reg_Naz_v<x>.xlsx)
      raw/istat_coltivazioni.csv     stime congiunturali delle superfici coltivate (ha, DATA_TYPE=ART) per provincia,
                                     2006 → ultimo anno (SDMX 101_1015_DF_DCSP_COLTIVAZIONI_2)
      raw/istat_censimento2020.csv   7° Censimento dell'agricoltura: SAU (ARU) e superficie agricola non utilizzata
                                     (AA_UNUT) per comune (SDMX DF_DCAT_CENSAGRIC2020_SURF_ALL)
      raw/stato_scarico.json         nome, versione, dimensione e data dei file; impronta SHA-256 dei CSV ISTAT
      con carte=True anche le due carte raster per l'incrocio agricolo (agricolo.py, ~800 MB, una volta l'anno):
      raw/carte/consumo_suolo_<AAAA>-<AAAA>.tif (carta dei cambiamenti dell'ultima edizione, 10 m) e
      raw/carte/Uso_del_suolo_<AAAA>.tif (carta di uso del suolo più recente).
  L'esito dice che cosa è cambiato ("cambiati": [...]); il worker ricostruisce solo se qualcosa è cambiato.

Licenze: ISPRA/SNPA e ISTAT CC BY 4.0 (citazione e indicazione delle modifiche).

  python -m suolo.scarica <raw> [--carte]
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path

GROUPWARE = "https://groupware.sinanet.isprambiente.it/uso-copertura-e-consumo-di-suolo/library"
CARTELLA_INDICATORI = f"{GROUPWARE}/consumo-di-suolo/indicatori"
CARTELLA_CONSUMO = f"{GROUPWARE}/consumo-di-suolo"
CARTELLA_USO = f"{GROUPWARE}/copertura-del-suolo/carta-di-copertura-del-suolo"
SDMX = "https://esploradati.istat.it/SDMXWS/rest/data"
COLTIVAZIONI = "IT1,101_1015_DF_DCSP_COLTIVAZIONI_2,1.0"
CENSIMENTO = "IT1,DF_DCAT_CENSAGRIC2020_SURF_ALL,1.0"
CSV = {"Accept": "application/vnd.sdmx.data+csv;version=1.0.0"}
AGENTE = {"User-Agent": "EuGEnio (statistiche del suolo; https://eugenio.statocritico.it)"}

RE_INDICATORI = re.compile(r'href="([^"]*/download/[^"]*/(consumo_suolo_(\d{4})_Com_Prov_Reg_Naz_v(\d+(?:\.\d+)*)\.xlsx))"', re.I)
RE_CARTA_ANNO = re.compile(r'href="([^"]*/consumo-di-suolo/carta-nazionale-consumo-suolo-(\d{4}))/?"', re.I)
RE_CARTELLA_CAMBI = re.compile(r'href="([^"]*/cambiamenti-(\d{4})-(\d{4}))/?"', re.I)
RE_CAMBI = re.compile(r'href="([^"]*/download/[^"]*/(consumo_suolo_(\d{4})-(\d{4})\.tif))"', re.I)
RE_CARTELLA_USO = re.compile(r'href="([^"]*/uso-del-suolo-(\d{4}))/?"', re.I)
RE_USO = re.compile(r'href="([^"]*/download/[^"]*/(Uso_del_suolo_(\d{4})\.tif))"', re.I)


def _versione(v: str) -> tuple:
    return tuple(int(x) for x in v.split("."))


def file_indicatori(html: str) -> dict | None:
    """Dall'HTML della cartella «indicatori»: il file con l'anno e poi la versione più alti (None se non c'è)."""
    trovati = [{"url": m.group(1), "nome": m.group(2), "anno": int(m.group(3)), "versione": m.group(4)}
               for m in RE_INDICATORI.finditer(html)]
    return max(trovati, key=lambda f: (f["anno"], _versione(f["versione"])), default=None)


def _piu_recente(regex, html: str, gruppo_anno: int = 2) -> dict | None:
    trovati = [{"url": m.group(1), "anno": int(m.group(gruppo_anno)), "m": m} for m in regex.finditer(html)]
    return max(trovati, key=lambda f: f["anno"], default=None)


def _client(client=None):
    if client is not None:
        return client
    import httpx
    return httpx.Client(timeout=httpx.Timeout(60, read=600), follow_redirects=True, headers=AGENTE)


def _testo(c, url: str) -> str:
    r = c.get(url)
    r.raise_for_status()
    return r.text


def _scarica_file(c, url: str, dest: Path) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".parziale")
    with c.stream("GET", url) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for blocco in r.iter_bytes(1 << 20):
                f.write(blocco)
    tmp.replace(dest)
    return dest.stat().st_size


def _sdmx(c, flusso: str, chiave: str, dest: Path, inizio: str | None = None) -> str:
    url = f"{SDMX}/{flusso}/{chiave}/" + (f"?startPeriod={inizio}" if inizio else "")
    r = c.get(url, headers=CSV)
    r.raise_for_status()
    if not r.text.startswith("DATAFLOW"):
        raise RuntimeError(f"ISTAT: risposta inattesa da {url}: {r.text[:120]!r}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(r.text, encoding="utf-8")
    return hashlib.sha256(r.content).hexdigest()


def carte_recenti(c) -> dict:
    """{"cambiamenti": {url, nome, periodo}, "uso": {url, nome, anno}} delle carte più recenti (None dove manca)."""
    out = {"cambiamenti": None, "uso": None}
    anno = _piu_recente(RE_CARTA_ANNO, _testo(c, CARTELLA_CONSUMO))
    if anno:
        cart = _piu_recente(RE_CARTELLA_CAMBI, _testo(c, anno["url"]), 3)
        if cart:
            f = [m for m in RE_CAMBI.finditer(_testo(c, cart["url"]))]
            if f:
                m = max(f, key=lambda m: int(m.group(4)))
                out["cambiamenti"] = {"url": m.group(1), "nome": m.group(2), "periodo": f"{m.group(3)}-{m.group(4)}"}
    uso = _piu_recente(RE_CARTELLA_USO, _testo(c, CARTELLA_USO))
    if uso:
        f = [m for m in RE_USO.finditer(_testo(c, uso["url"]))]
        if f:
            m = max(f, key=lambda m: int(m.group(3)))
            out["uso"] = {"url": m.group(1), "nome": m.group(2), "anno": int(m.group(3))}
    return out


def scarica(raw: Path, carte: bool = False, client=None, pausa: float = 1.0) -> dict:
    raw = Path(raw)
    raw.mkdir(parents=True, exist_ok=True)
    fstato = raw / "stato_scarico.json"
    try:
        prima = json.loads(fstato.read_text(encoding="utf-8"))
    except Exception:
        prima = {}
    stato = dict(prima)
    cambiati = []
    c = _client(client)
    # ISPRA: indicatori (nome con anno e versione; si riscarica se nome o dimensione cambiano)
    f = file_indicatori(_testo(c, CARTELLA_INDICATORI))
    if not f:
        raise RuntimeError("ISPRA: nessun file consumo_suolo_<AAAA>_Com_Prov_Reg_Naz_v<x>.xlsx nella cartella degli indicatori")
    dest = raw / "ispra_indicatori.xlsx"
    if (prima.get("ispra") or {}).get("nome") != f["nome"] or not dest.exists():
        n = _scarica_file(c, f["url"], dest)
        stato["ispra"] = {"nome": f["nome"], "anno": f["anno"], "versione": f["versione"], "url": f["url"], "byte": n,
                          "scaricato": time.strftime("%Y-%m-%d")}
        cambiati.append("ispra")
    time.sleep(pausa)
    # ISTAT: si scarica ogni volta (pochi MB) e si confronta l'impronta
    for chiave, flusso, sel, inizio, nome in (("coltivazioni", COLTIVAZIONI, "A..ART..", "2006", "istat_coltivazioni.csv"),
                                              ("censimento2020", CENSIMENTO, "A..ARU+AA_UNUT", None, "istat_censimento2020.csv")):
        impronta = _sdmx(c, flusso, sel, raw / nome, inizio)
        if (prima.get(chiave) or {}).get("sha256") != impronta:
            stato[chiave] = {"flusso": flusso, "sha256": impronta, "scaricato": time.strftime("%Y-%m-%d")}
            cambiati.append(chiave)
        time.sleep(pausa)
    if carte:
        k = carte_recenti(c)
        for chiave in ("cambiamenti", "uso"):
            x = k[chiave]
            if not x:
                continue
            dest = raw / "carte" / x["nome"]
            if (prima.get(chiave) or {}).get("nome") != x["nome"] or not dest.exists():
                for vecchio in (raw / "carte").glob("consumo_suolo_*.tif" if chiave == "cambiamenti" else "Uso_del_suolo_*.tif"):
                    if vecchio.name != x["nome"]:
                        vecchio.unlink()
                stato[chiave] = {**x, "byte": _scarica_file(c, x["url"], dest), "scaricato": time.strftime("%Y-%m-%d")}
                cambiati.append(chiave)
            time.sleep(pausa)
    fstato.write_text(json.dumps(stato, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"cambiati": cambiati, "stato": stato}


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    print(json.dumps(scarica(Path(sys.argv[1]), carte="--carte" in sys.argv), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
