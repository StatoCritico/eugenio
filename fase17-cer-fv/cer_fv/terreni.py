"""Terreni pubblici candidati per gli impianti delle CER (fase 17, 24/11/2026).

Dall'indice degli immobili delle PA (fase 7, `immobili_pa_<anno>.sqlite`, tabella `ente_particelle`) prende le particelle
dei **terreni in proprietà** di enti pubblici, con superficie, comune, ente (nome, settore, sede) e tipologie; dove ci sono
i piani colturali grafici di AGREA aggiunge la **probabilità di coltura DOP o certificata** (colture.py). Scrive
`terreni_pubblici_<anno>.sqlite` con un indice spaziale R*Tree, letto dalla rotta `/api/cer-fv/terreni` (fase 4).

Nel file: nessun codice fiscale, nessun soggetto cedente (come nell'indice pubblico degli immobili), nessun dato AGREA
oltre all'indicatore. Licenza delle parti: MEF «Patrimonio della PA» + AdE cartografia catastale (CC BY 4.0) elaborati da
EuGEnio; indicatore elaborato da EuGEnio sui dati AGREA, che non si cedono.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from collections import defaultdict
from pathlib import Path

from . import colture as K

log = logging.getLogger("cer_fv.terreni")

COLONNE = ["id", "ref", "lon", "lat", "area_m2", "comune_cod", "foglio", "particella", "comune", "provincia", "regione",
           "ente_chiave", "ente", "settore", "ente_sede", "n_enti", "enti", "tipologie", "utilizzo", "n_beni", "sup_mq",
           "prob_coltura", "classe_coltura", "campagne", "quota_dichiarata"]


def _ultimo(cartella: Path, schema: str) -> Path | None:
    f = sorted(cartella.glob(schema))
    return f[-1] if f else None


def terreni_dall_indice(indice: Path) -> list[dict]:
    """Una riga per particella catastale di terreni in proprietà di enti pubblici (il primo ente per superficie)."""
    db = sqlite3.connect(f"file:{indice}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    tab = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
    if "ente_particelle" not in tab:
        raise RuntimeError(f"{indice}: manca la tabella ente_particelle (indice della fase 7 dal 22/11/2026)")
    con_comuni = "comuni" in tab
    sql = ("SELECT ep.ref, ep.lon, ep.lat, ep.area_m2, ep.comune_cod, ep.tipologie, ep.utilizzo, ep.n_beni, ep.sup_mq,"
           " e.chiave, e.nome, e.settore, e.sede_comune, e.sede_provincia"
           + (", c.comune, c.provincia, c.regione" if con_comuni else ", NULL AS comune, NULL AS provincia, NULL AS regione")
           + " FROM ente_particelle ep JOIN enti e ON e.id = ep.ente"
           + (" LEFT JOIN comuni c ON c.comune_cod = ep.comune_cod" if con_comuni else "")
           + " WHERE ep.natura = 'T' AND ep.ruolo = 'P' AND ep.ref NOT LIKE 'b%' AND ep.lon IS NOT NULL")
    gruppi: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for r in db.execute(sql):
        gruppi[r["ref"]].append(r)
    db.close()
    out = []
    for ref, rr in gruppi.items():
        rr.sort(key=lambda r: -(r["sup_mq"] or 0))
        p = rr[0]
        nomi = list(dict.fromkeys(r["nome"] for r in rr if r["nome"]))
        tip = list(dict.fromkeys(t for r in rr for t in str(r["tipologie"] or "").split(" · ") if t))
        sede = " ".join(x for x in (p["sede_comune"], f"({p['sede_provincia']})" if p["sede_provincia"] else "") if x)
        out.append({"ref": ref, "lon": p["lon"], "lat": p["lat"], "area_m2": p["area_m2"], "comune_cod": p["comune_cod"],
                    "comune": p["comune"], "provincia": p["provincia"], "regione": p["regione"],
                    "ente_chiave": p["chiave"], "ente": p["nome"], "settore": p["settore"], "ente_sede": sede,
                    "n_enti": len(nomi), "enti": " · ".join(nomi)[:500], "tipologie": " · ".join(tip)[:300],
                    "utilizzo": p["utilizzo"], "n_beni": sum(r["n_beni"] or 0 for r in rr), "sup_mq": sum(r["sup_mq"] or 0 for r in rr)})
    return out


def geometrie(parquet: Path, refs: set[str], limiti_4326=None, con_geometria: bool = True) -> dict[str, tuple]:
    """ref → (poligono in EPSG:4326 o None, foglio, particella) dal parquet delle particelle della fase 7."""
    import pyarrow.parquet as pq
    import shapely
    out = {}
    f = pq.ParquetFile(parquet)
    cols = [c for c in ("ref_ade", "foglio", "particella") + (("geometry",) if con_geometria else ()) if c in f.schema_arrow.names]
    for b in f.iter_batches(columns=cols, batch_size=50_000):
        d = b.to_pydict()
        for i, ref in enumerate(d["ref_ade"]):
            if ref not in refs:
                continue
            if not con_geometria:
                out[ref] = (None, d.get("foglio", [None] * len(d["ref_ade"]))[i], d.get("particella", [None] * len(d["ref_ade"]))[i])
                continue
            g = shapely.from_wkb(d["geometry"][i])
            if limiti_4326 is not None:
                x0, y0, x1, y1 = g.bounds
                if x1 < limiti_4326[0] or x0 > limiti_4326[2] or y1 < limiti_4326[1] or y0 > limiti_4326[3]:
                    out[ref] = (None, d.get("foglio", [None] * len(d["ref_ade"]))[i], d.get("particella", [None] * len(d["ref_ade"]))[i])
                    continue
            out[ref] = (g, d.get("foglio", [None] * len(d["ref_ade"]))[i], d.get("particella", [None] * len(d["ref_ade"]))[i])
    return out


def costruisci(immobili: Path, dest: Path, agrea: Path | None = None, regole_file: Path | None = None,
               comuni: Path | None = None) -> dict:
    """Scrive `dest/terreni_pubblici_<anno>.sqlite`. `immobili`: cartella con l'indice SQLite e il parquet delle particelle.
    `comuni`: tabella ISTAT → codice catastale per l'abbinamento dei file AGREA con le particelle (vedi agrea.istat_belfiore)."""
    t0 = time.time()
    indice = _ultimo(immobili, "immobili_pa_*.sqlite")
    if not indice:
        raise FileNotFoundError(f"nessun immobili_pa_<anno>.sqlite in {immobili}")
    anno = int(indice.stem.split("_")[-1])
    righe = terreni_dall_indice(indice)
    log.info("terreni pubblici in proprietà: %d particelle", len(righe))
    R = K.regole(regole_file)
    parquet = immobili / f"immobili_pa_{anno}_particelle.parquet"
    refs = {r["ref"] for r in righe}
    # prima foglio e particella (senza geometrie): servono le chiavi catastali per leggere AGREA tenendo solo queste
    fp = geometrie(parquet, refs, con_geometria=False) if parquet.exists() else {}
    chiavi = {}
    for r in righe:
        _, foglio, part = fp.get(r["ref"], (None, None, None))
        r["foglio"], r["particella"] = foglio, part
        k = K.chiave_da_ref(r["ref"], foglio, part)
        if k:
            chiavi[r["ref"]] = k
    indici = []
    if agrea:
        from . import agrea as A
        tab = {}
        if any(K._catastale(c) for _, c in K.campagne_disponibili(agrea, R.campagne)):
            # (24/11/2026) niente ripiego geometrico per questi file: milioni di poligoni in memoria, non finisce più
            tab = A.istat_belfiore(comuni, agrea)
            if not tab:
                raise RuntimeError("tabella dei comuni (ISTAT → codice catastale) vuota: indicala con --comuni")
        indici = K.carica(agrea, R, set(chiavi.values()), tab)
    spaziali = [ix for ix in indici if isinstance(ix, K.Indice)]
    geo = {}
    if spaziali and parquet.exists():
        from pyproj import Transformer
        tr = Transformer.from_crs(3003, 4326, always_xy=True)
        b = [ix.limiti for ix in spaziali if ix.limiti is not None]
        limiti = None
        if b:
            x0, y0 = tr.transform(min(v[0] for v in b), min(v[1] for v in b))
            x1, y1 = tr.transform(max(v[2] for v in b), max(v[3] for v in b))
            limiti = (x0, y0, x1, y1)
        geo = geometrie(parquet, refs, limiti)
    if spaziali:
        import shapely.ops
        from pyproj import Transformer
        tr = Transformer.from_crs(4326, 3003, always_xy=True)
    con_ind = 0
    for r in righe:
        r.update({"prob_coltura": None, "classe_coltura": None, "campagne": None, "quota_dichiarata": None})
        if not indici:
            continue
        g = geo.get(r["ref"], (None,))[0]
        g3 = shapely.ops.transform(tr.transform, g) if (spaziali and g is not None) else None
        k = chiavi.get(r["ref"])
        if g3 is None and k is None:
            continue
        r.update(K.indicatore(g3, K.codice_provincia(r["provincia"]), indici, R, k, r.get("area_m2")))
        con_ind += 1
    dest.mkdir(parents=True, exist_ok=True)
    f = dest / f"terreni_pubblici_{anno}.sqlite"
    tmp = f.with_suffix(".sqlite.tmp")
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(tmp)
    db.execute(f"CREATE TABLE terreni ({', '.join(c + (' INTEGER PRIMARY KEY' if c == 'id' else '') for c in COLONNE)})")
    db.execute("CREATE VIRTUAL TABLE terreni_rt USING rtree(id, ovest, est, sud, nord)")
    for i, r in enumerate(righe, 1):
        db.execute(f"INSERT INTO terreni VALUES ({','.join('?' * len(COLONNE))})", [i] + [r.get(c) for c in COLONNE[1:]])
        db.execute("INSERT INTO terreni_rt VALUES (?,?,?,?,?)", (i, r["lon"], r["lon"], r["lat"], r["lat"]))
    info = {"anno": anno, "costruito": time.strftime("%Y-%m-%d %H:%M"), "particelle": len(righe), "con_indicatore": con_ind,
            "campagne_agrea": [ix.anno for ix in indici],
            "fonti": "MEF – Patrimonio della PA (CC BY 4.0); Agenzia delle Entrate – cartografia catastale (CC BY 4.0); "
                     "probabilità di coltura: elaborazione EuGEnio sui piani colturali grafici AGREA (dati non ceduti)"}
    db.execute("CREATE TABLE info (chiave PRIMARY KEY, valore)")
    db.executemany("INSERT INTO info VALUES (?, ?)", [(k, json.dumps(v)) for k, v in info.items()])
    db.commit(); db.close()
    tmp.replace(f)
    info["file"] = str(f)
    info["secondi"] = round(time.time() - t0, 1)
    log.info("scritto %s (%d particelle, %d con l'indicatore, %.0f s)", f, len(righe), con_ind, info["secondi"])
    return info
