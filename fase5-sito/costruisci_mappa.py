"""Genera i file di mappa del sito per TUTTA ITALIA, dai confini Gramscii (versione bloccata nella fase 3).

  python costruisci_mappa.py --comuni <archivio fase 3>/comuni.parquet

Uscita in sito/dati/mappa/:
  italia.json   le 20 regioni (≈130 kB): vista d'insieme e scelta della regione
  <RR>.json     i comuni e i confini delle province di una regione (codice ISTAT a due cifre, 8–200 kB compressi), caricati
                solo quando servono: il visitatore non scarica mai l'Italia intera (1,7 MB)
L'elenco comuni deve essere nazionale (`python -m meteo_storico comuni --regioni tutte`).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent / "fase3-storico"))
from meteo_storico import gramscii  # noqa: E402


def _bbox(ds: list[str], margine: float = 3.0) -> list[float]:
    xs, ys = [], []
    for d in ds:
        for x, y in re.findall(r"(-?\d+\.?\d*),(-?\d+\.?\d*)", d):
            xs.append(float(x))
            ys.append(float(y))
    return [round(min(xs) - margine, 1), round(min(ys) - margine, 1),
            round(max(xs) - min(xs) + 2 * margine, 1), round(max(ys) - min(ys) + 2 * margine, 1)]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--comuni", required=True, help="comuni.parquet (o .json) nazionale della fase 3")
    p.add_argument("--cache", default=str(QUI / ".cache"), help="cartella di cache dei file Gramscii")
    p.add_argument("--uscita", default=str(QUI / "sito" / "dati" / "mappa"))
    a = p.parse_args()
    cache = Path(a.cache)
    geo_c = json.loads(gramscii.scarica("italy-municipalities.geo.json", cache).read_text(encoding="utf-8"))
    geo_r = json.loads(gramscii.scarica("italy-regions.geo.json", cache).read_text(encoding="utf-8"))
    geo_p = json.loads(gramscii.scarica("italy-provinces.geo.json", cache).read_text(encoding="utf-8"))
    province = {s["aliases"][0]: s for s in geo_p["shapes"]}
    # codice ISTAT più recente di ogni comune (l'ultimo alias): l'elenco dei comuni può avere ancora i codici
    # precedenti alle riforme provinciali (Sardegna 2026), i confini delle province no
    attuale = {a: s["aliases"][-1] for s in geo_c["shapes"] for a in s["aliases"]}
    if a.comuni.endswith(".json"):
        righe = json.loads(Path(a.comuni).read_text(encoding="utf-8"))
    else:
        import pandas as pd
        righe = pd.read_parquet(a.comuni).to_dict(orient="records")
    info = {r["istat"]: r for r in righe}
    dest = Path(a.uscita)
    dest.mkdir(parents=True, exist_ok=True)

    regioni = []
    for s in geo_r["shapes"]:
        cod = next((x for x in s["aliases"] if re.fullmatch(r"\d{2}", x)), None)
        regioni.append({"cod": cod, "nome": s["name"], "d": s["d"]})
    (dest / "italia.json").write_text(json.dumps(
        {"viewBox": [float(v) for v in geo_r["viewBox"].split()], "fonte": geo_r.get("source"),
         "versione": gramscii.revisione(), "regioni": regioni}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")

    per_regione: dict[str, list] = {}
    for s in geo_c["shapes"]:
        istat = next((x for x in reversed(s["aliases"]) if x in info), None)
        if not istat:
            continue
        r = info[istat]
        per_regione.setdefault(r["regione_cod"], []).append(
            {"istat": istat, "nome": r["nome"], "prov": r["provincia"], "d": s["d"], "x": r["svg_x"], "y": r["svg_y"]})
    for cod, comuni in sorted(per_regione.items()):
        nome = next((x["nome"] for x in regioni if x["cod"] == cod), cod)
        f = dest / f"{cod}.json"
        cod_prov = sorted({attuale.get(c["istat"], c["istat"])[:3] for c in comuni})
        prov = [{"cod": p, "sigla": (province[p]["aliases"] + [""])[1], "nome": province[p]["name"], "d": province[p]["d"]}
                for p in cod_prov if p in province]
        f.write_text(json.dumps({"viewBox": _bbox([c["d"] for c in comuni]), "regione": cod, "nome": nome,
                                 "fonte": geo_c.get("source"), "versione": gramscii.revisione(), "comuni": comuni,
                                 "province": prov, "fonte_province": geo_p.get("source")},
                                ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"{cod} {nome:32s} {len(comuni):5d} comuni {len(prov):3d} province  {f.stat().st_size // 1024:5d} kB")
    print(f"italia.json: {(dest / 'italia.json').stat().st_size // 1024} kB")


if __name__ == "__main__":
    main()
