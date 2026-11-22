"""Suolo agricolo consumato: incrocio fatto da EuGEnio (decisione di Paolo del 22/11/2026, «facciamo noi i dati incrociando»).

  agricolo(cambiamenti, uso, mappa, uscita, regioni=None) -> dict

Ingressi (ISPRA, CC BY 4.0, groupware SINAnet, vedi scarica.py):
  cambiamenti  carta dei cambiamenti del consumo di suolo (es. consumo_suolo_2024-2025.tif, 10 m, EPSG:7794, uint32):
               codici 2111…2126 = nuovo consumo (da suolo non consumato alla classe 111…126), vedi classi.py
  uso          Carta nazionale di uso del suolo ISPRA (Uso_del_suolo_2023.tif, 10 m, EPSG:3035, int16): usi agricoli
               11 seminativi, 12 foraggere, 13 colture permanenti, 14 aree agroforestali, 16 altri usi agricoli. La carta
               integra Copernicus 2018 e la carta del consumo di suolo 2023: per i cambiamenti successivi al 2023 dice
               com'era usato il suolo prima di essere consumato.
  mappa        cartella dati/mappa del sito (comuni ISTAT 2026 generalizzati, ~100 m): ogni pixel va al comune che lo
               contiene (o al più vicino entro 500 m, per le coste semplificate).

Procedimento (pixel per pixel, nessuna ricampionatura dei raster):
  1. la carta dei cambiamenti si legge a strisce; si tengono i pixel con un codice di nuovo consumo (sono pochi:
     circa 10.000 ha = 1 milione di pixel all'anno su 12,5 miliardi);
  2. il centro di ogni pixel si porta da EPSG:7794 a EPSG:3035 (pyproj) e si legge l'uso del suolo 2023 in quel punto;
  3. il centro si porta in UTM 32N (coordinate dei file di mappa) e si assegna al comune;
  4. si somma per comune: nuovo consumo per gruppo di classi (classi.GRUPPI) e la parte su suolo agricolo, per gruppo e
     per uso agricolo; poi province, regioni, Italia. Un pixel vale 0,01 ha.
Il risultato è una stima di EuGEnio: dichiararlo come «elaborazione EuGEnio su dati ISPRA/SNPA» (vedi README).

Uscita: un JSON {"anno", "periodo", "file", "gruppi", "usi", "italia", "regioni", "province", "comuni"} dove ogni unità è
{"lordo": [ha per gruppo], "agricolo": [ha per gruppo], "usi": [ha per uso agricolo]} (lordo = nuovo consumo, come
csuolo10 dell'Excel ISPRA salvo i bordi dei comuni).

  python -m suolo.agricolo <cambiamenti.tif> <uso.tif> <cartella dati/mappa> <uscita.json> [--regioni 08,03] [--anno 2025]
Servono numpy, rasterio, pyproj e shapely (solo qui: il resto della fase 16 non li usa).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

from .classi import GRUPPI, USI_AGRICOLI, USI_ALTRI
from . import mappa as M

RIGHE_STRISCIA = 512
PIXEL_HA = 0.01


def _pixel_nuovo_consumo(cambiamenti: Path, avanzamento=None):
    """(righe, colonne, codici, trasformazione, crs) dei pixel con un codice di nuovo consumo."""
    import numpy as np
    import rasterio
    with rasterio.open(cambiamenti) as d:
        codici_validi = np.array([2000 + c for _, _, _, cl in GRUPPI for c in cl], dtype=np.uint32)
        R, Cc, V = [], [], []
        for r0 in range(0, d.height, RIGHE_STRISCIA):
            h = min(RIGHE_STRISCIA, d.height - r0)
            a = d.read(1, window=((r0, r0 + h), (0, d.width)))
            m = (a >= 2111) & (a <= 2126)
            if m.any():
                rr, cc = np.nonzero(m)
                vv = a[rr, cc]
                ok = np.isin(vv, codici_validi)
                R.append(rr[ok] + r0); Cc.append(cc[ok]); V.append(vv[ok])
            if avanzamento and (r0 // RIGHE_STRISCIA) % 25 == 0:
                avanzamento(f"cambiamenti: riga {r0}/{d.height}")
        return (np.concatenate(R) if R else np.zeros(0, int), np.concatenate(Cc) if Cc else np.zeros(0, int),
                np.concatenate(V) if V else np.zeros(0, np.uint32), d.transform, d.crs)


def _campiona(uso: Path, xs, ys, crs_da):
    """Valori della carta d'uso nei punti (xs, ys) espressi in crs_da: una lettura per striscia di righe con punti."""
    import numpy as np
    import rasterio
    from pyproj import Transformer
    with rasterio.open(uso) as d:
        t = Transformer.from_crs(crs_da, d.crs, always_xy=True)
        X, Y = t.transform(xs, ys)
        inv = ~d.transform
        col, riga = inv * (np.asarray(X), np.asarray(Y))
        col = np.floor(col).astype(np.int64); riga = np.floor(riga).astype(np.int64)
        out = np.full(len(xs), -1, dtype=np.int32)
        dentro = (col >= 0) & (col < d.width) & (riga >= 0) & (riga < d.height)
        idx = np.nonzero(dentro)[0]
        if not len(idx):
            return out
        passo = 1024
        strisce = riga[idx] // passo
        ordine = np.argsort(strisce, kind="stable")
        idx, strisce = idx[ordine], strisce[ordine]
        confini = np.nonzero(np.diff(strisce))[0] + 1
        for gruppo in np.split(np.arange(len(idx)), confini):
            ii = idx[gruppo]
            r0 = int(strisce[gruppo[0]]) * passo
            c0, c1 = int(col[ii].min()), int(col[ii].max()) + 1
            h = min(passo, d.height - r0)
            a = d.read(1, window=((r0, r0 + h), (c0, c1)))
            out[ii] = a[riga[ii] - r0, col[ii] - c0]
        return out


def _comuni(xs, ys, crs_da, mappa: Path):
    """Codice ISTAT (mappa del sito) del comune di ogni punto ("" se fuori da tutti, oltre 500 m)."""
    import numpy as np
    import shapely
    from pyproj import Transformer
    poli = M.poligoni_comuni(mappa)
    t = Transformer.from_crs(crs_da, "EPSG:32632", always_xy=True)
    E, N = t.transform(xs, ys)
    sx = M.S * np.asarray(E) + M.AX
    sy = -M.S * np.asarray(N) + M.AY
    punti = shapely.points(sx, sy)
    albero = shapely.STRtree([g for _, _, g in poli])
    out = np.full(len(xs), "", dtype=object)
    i_p, i_g = albero.query(punti, predicate="intersects")
    out[i_p] = [poli[j][0] for j in i_g]
    fuori = np.nonzero(out == "")[0]
    if len(fuori):
        j_p, j_g = albero.query_nearest(punti[fuori], max_distance=0.5)
        out[fuori[j_p]] = [poli[j][0] for j in j_g]
    return out


def agricolo(cambiamenti: Path, uso: Path, mappa: Path, uscita: Path | None = None, regioni: list[str] | None = None,
             anno: int | None = None, avanzamento=None) -> dict:
    import numpy as np
    t0 = time.time()
    log = avanzamento or (lambda s: None)
    righe, col, cod, tr, crs = _pixel_nuovo_consumo(Path(cambiamenti), log)
    log(f"pixel di nuovo consumo: {len(cod)} ({time.time() - t0:.0f} s)")
    xs, ys = tr * (col + 0.5, righe + 0.5)
    xs, ys = np.asarray(xs), np.asarray(ys)
    istat = _comuni(xs, ys, crs, Path(mappa))
    log(f"comuni assegnati ({time.time() - t0:.0f} s)")
    m = M.carica(Path(mappa))
    reg_di = np.array([m["comuni"][i]["regione"] if i else "" for i in istat], dtype=object)
    if regioni:
        tieni = np.isin(reg_di, regioni)
        xs, ys, cod, istat, reg_di = xs[tieni], ys[tieni], cod[tieni], istat[tieni], reg_di[tieni]
    u = _campiona(Path(uso), xs, ys, crs)
    log(f"uso del suolo letto ({time.time() - t0:.0f} s)")

    ids = [g for g, _, _, _ in GRUPPI]
    usi = list(USI_AGRICOLI)
    gi = {2000 + c: ids.index(g) for g, _, _, cl in GRUPPI for c in cl}
    vuoto = lambda: {"lordo": [0.0] * len(ids), "agricolo": [0.0] * len(ids), "usi": [0.0] * len(usi)}
    comuni: dict = defaultdict(vuoto)
    altri: dict = defaultdict(lambda: defaultdict(float))      # regione → uso non agricolo (o «nd») → ha
    fuori = 0
    for c, ist, uu, rg in zip(cod.tolist(), istat.tolist(), u.tolist(), reg_di.tolist()):
        if not ist:
            fuori += 1
            continue
        if uu not in USI_AGRICOLI:
            nome_uso = USI_ALTRI.get(uu, "senza dato")
            altri[rg][nome_uso] += PIXEL_HA
            altri["IT"][nome_uso] += PIXEL_HA
        v = comuni[ist]
        k = gi[c]
        v["lordo"][k] += PIXEL_HA
        if uu in USI_AGRICOLI:
            v["agricolo"][k] += PIXEL_HA
            v["usi"][usi.index(uu)] += PIXEL_HA

    def somma(dove: dict, chiave: str, v: dict):
        acc = dove.setdefault(chiave, vuoto())
        for k in acc:
            acc[k] = [a + b for a, b in zip(acc[k], v[k])]

    sig2cod = {p["sigla"]: c for c, p in m["province"].items()}
    province, reg, italia = {}, {}, {}
    for ist, v in comuni.items():
        c = m["comuni"][ist]
        somma(province, sig2cod.get(c["prov"], c["prov"]), v)
        somma(reg, c["regione"], v)
        somma(italia, "IT", v)
    tondo = lambda d: {k: {kk: [round(x, 2) for x in vv] for kk, vv in v.items()} for k, v in sorted(d.items())}
    nome = Path(cambiamenti).name
    mt = re.search(r"(\d{4})\D+(\d{4})", nome)
    anno = anno or (int(mt.group(2)) if mt else None)
    esito = {
        "anno": anno, "periodo": f"{mt.group(1)}–{mt.group(2)}" if mt else None,
        "file": {"cambiamenti": nome, "uso": Path(uso).name},
        "regioni_calcolate": regioni or "tutte",
        "gruppi": [{"id": g, "nome": n} for g, n, _, _ in GRUPPI],
        "usi": [{"id": k, "nome": v} for k, v in USI_AGRICOLI.items()],
        "pixel_ha": PIXEL_HA, "pixel_fuori_dai_comuni": fuori,
        "usi_non_agricoli": {k: {u: round(x, 2) for u, x in sorted(v.items(), key=lambda q: -q[1])} for k, v in sorted(altri.items())},
        "italia": tondo(italia).get("IT", vuoto()), "regioni": tondo(reg), "province": tondo(province), "comuni": tondo(comuni),
        "secondi": round(time.time() - t0),
    }
    if uscita:
        Path(uscita).parent.mkdir(parents=True, exist_ok=True)
        Path(uscita).write_text(json.dumps(esito, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return esito


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cambiamenti"); p.add_argument("uso"); p.add_argument("mappa"); p.add_argument("uscita")
    p.add_argument("--regioni", default="", help="codici a 2 cifre separati da virgole (prototipo): solo queste regioni")
    p.add_argument("--anno", type=int, default=None)
    a = p.parse_args(argv)
    esito = agricolo(Path(a.cambiamenti), Path(a.uso), Path(a.mappa), Path(a.uscita),
                     [r for r in a.regioni.split(",") if r] or None, a.anno, lambda s: print(s, file=sys.stderr, flush=True))
    it = esito["italia"]
    print(json.dumps({"anno": esito["anno"], "lordo_ha": round(sum(it["lordo"]), 1), "agricolo_ha": round(sum(it["agricolo"]), 1),
                      "regioni": {k: [round(sum(v["lordo"]), 1), round(sum(v["agricolo"]), 1)] for k, v in esito["regioni"].items()},
                      "secondi": esito["secondi"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
