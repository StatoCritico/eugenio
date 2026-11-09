"""Estrazioni DBTR raggruppate divise per comune (09/11/2026).

Il Geoportale dell'Emilia-Romagna, scaricando più fogli o un'area, mette in un solo `estraz_procons.gpkg` gli edifici di
più comuni (estrazioni 354184 e 354185 della Romagna, 354168 e 354187 di Bologna). `prepara` non filtra per comune: qui
si scrive, per ogni estrazione, un GeoPackage ridotto con i quattro strati filtrati in modo coerente:

- `V_EDI_GPG` (edifici): quelli del comune;
- `V_UVL_GPG` (corpi): quelli con `EDI_ID_E` di un edificio tenuto;
- `V_EDI_GPGSA` (ingombri) e `V_EDI_CT_USO_AVM` (destinazioni): quelli con `ID_E` di un edificio tenuto.

Un edificio è del comune se il suo codice catastale `COD_COM` è uno di quelli dati, oppure se `COD_COM` è vuoto (circa il
10 % degli edifici: per lo più edifici senza particella) e il suo **punto interno** cade nel confine ISTAT del comune
(`b_regioni.confine_comune`, senza margine). Per riconoscere i codici catastali, `elenco` conta per ogni `COD_COM` in
quale confine ISTAT cadono i punti interni dei suoi edifici (comune e quota).

Comandi (dalla cartella fase10-edifici3d):
  python -m edifici3d dividi --gpkg 354184/estraz_procons.gpkg 354185/estraz_procons.gpkg --elenco
  python -m edifici3d dividi --gpkg 354168/estraz_procons.gpkg 354187/estraz_procons.gpkg --codici B880 --istat 037011 \\
         --uscita divisi/casalecchio-di-reno
Scrive `<uscita>/<nome dell'estrazione>/estraz_procons.gpkg` (il nome è la cartella del file, o la cartella degli
Shapefile) per ogni estrazione che ha corpi del comune; `prepara --gpkg` li legge tutti insieme (doppioni tolti per `ID_E`).
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

STRATI = ("V_UVL_GPG", "V_EDI_GPG", "V_EDI_GPGSA", "V_EDI_CT_USO_AVM")
CRS = "EPSG:7791"


def nome_estrazione(src: Path) -> str:
    src = Path(src)
    return src.name if src.is_dir() else src.parent.name


def _leggi(src: Path, strato: str, geometria: bool = True, colonne=None):
    import pyogrio
    import pyogrio.raw as R
    src = Path(src)
    if src.is_dir():
        f = next((src / f"{strato}{e}" for e in (".shp", ".dbf") if (src / f"{strato}{e}").exists()), None)
        return None if f is None else R.read(str(f), read_geometry=geometria, columns=colonne)
    if strato not in [str(n) for n, _ in pyogrio.list_layers(str(src))]:
        return None
    return R.read(str(src), layer=strato, read_geometry=geometria, columns=colonne)


def confini(regione: str = "08", cartella: Path | None = None) -> list[tuple[str, str, object]]:
    """(istat, nome, confine shapely in EPSG:7791) dei comuni della regione, dai file di mappa del sito."""
    from . import b_regioni as B
    cartella = Path(cartella or B.MAPPE)
    m = json.loads((cartella / f"{regione}.json").read_text(encoding="utf-8"))
    return [(c["istat"], c["nome"], B.confine_comune(c["istat"], CRS, margine=0, cartella=cartella))
            for c in m.get("comuni", [])]


def edifici(sorgenti, comuni=None) -> tuple[dict, dict]:
    """{estrazione: {ID_E: (COD_COM o None, istat del confine che contiene il punto interno o None)}} e
    {COD_COM: (istat, nome, quota, edifici contati)} per riconoscere i codici catastali."""
    from shapely import STRtree, from_wkb, point_on_surface
    comuni = comuni if comuni is not None else confini()
    albero = STRtree([g for _, _, g in comuni])
    esito, voti = {}, defaultdict(Counter)
    for src in sorgenti:
        r = _leggi(src, "V_EDI_GPG", colonne=["ID_E", "COD_COM"])
        if r is None:
            raise ValueError(f"{src}: strato V_EDI_GPG assente")
        meta, _, g, campi = r
        d = dict(zip(meta["fields"], campi))
        punti = point_on_surface(from_wkb(g))
        ist = [None] * len(punti)
        for ip, ic in zip(*albero.query(punti, predicate="within")):
            ist[ip] = comuni[ic][0]
        cod = [str(c) if c not in (None, "") else None for c in d["COD_COM"]]
        for c, i in zip(cod, ist):
            if c and i:
                voti[c][i] += 1
        esito[str(src)] = {str(e): (c, i) for e, c, i in zip(d["ID_E"], cod, ist)}
    nomi = {i: n for i, n, _ in comuni}
    codici = {}
    for c, v in sorted(voti.items()):
        i, n = v.most_common(1)[0]
        codici[c] = (i, nomi.get(i), round(n / sum(v.values()), 3), sum(v.values()))
    return esito, codici


def scrivi(src: Path, tenuti: set[str], uscita: Path) -> dict | None:
    """GeoPackage ridotto con i quattro strati; None (niente file) se nessun corpo è del comune."""
    import numpy as np
    import pyogrio.raw as R
    uscita = Path(uscita)
    conti, dati_strati = {}, []
    for strato in STRATI:
        r = _leggi(src, strato, geometria=(strato != "V_EDI_CT_USO_AVM"))
        if r is None:
            continue
        meta, _, g, campi = r
        nomi = list(meta["fields"])
        chiave = "EDI_ID_E" if strato == "V_UVL_GPG" else "ID_E"
        m = np.array([str(v) in tenuti for v in campi[nomi.index(chiave)]], dtype=bool)
        if strato == "V_UVL_GPG" and not m.any():
            return None
        dati_strati.append((strato, meta, None if g is None else np.asarray(g, dtype=object)[m],
                            [np.asarray(c)[m] for c in campi], nomi))
        conti[strato] = int(m.sum())
    uscita.parent.mkdir(parents=True, exist_ok=True)
    if uscita.exists():
        uscita.unlink()
    for strato, meta, geo, dati, nomi in dati_strati:
        kw = {"layer": strato, "driver": "GPKG", "append": uscita.exists()}
        if geo is not None:
            kw.update(geometry_type=meta["geometry_type"], crs=meta["crs"])
        R.write(str(uscita), geo, dati, nomi, **kw)
    return conti


def dividi(sorgenti, codici, istat, uscita: Path, comuni=None) -> dict:
    """Un GeoPackage ridotto per estrazione in <uscita>/<estrazione>/estraz_procons.gpkg; {estrazione: conti}."""
    codici, istat = {str(c) for c in codici}, {str(i) for i in istat}
    tabella, _ = edifici(sorgenti, comuni)
    esito = {}
    for src in sorgenti:
        tenuti = {e for e, (c, i) in tabella[str(src)].items() if c in codici or (c is None and i in istat)}
        conti = scrivi(src, tenuti, Path(uscita) / nome_estrazione(src) / "estraz_procons.gpkg")
        if conti:
            esito[nome_estrazione(src)] = conti
    return esito
