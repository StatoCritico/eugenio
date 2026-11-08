"""Regione Campania – DBT 2020 e CTR 2020, edifici senza altezze (08/11/2026, lettori regionali, gruppo C).

Due forme dello stesso dato (volo AGEA 2020, 1:5.000, CC BY 4.0, «Geoportale Regione Campania»):

- **DBT 2020 per comune** (`DBT_5K.zip`, SharePoint della Regione, scaricato da Paolo l'08/11/2026): DBGT nazionale (GeoUML)
  esportato in Shapefile, con le geometrie in file separati: `EDIFC_CR_EDF_IS` (ingombro al suolo, **PolygonZ con
  z = quota al piede**: contro il DTM 5 m mediana +0,32 m), legato a `EDIFC` (attributi `EDIFC_TY`, `EDIFC_STAT`,
  `EDIFC_SOT`) e alle tabelle `EDIFC_EDIFC_USO` (`EDIFC_USO`, codici del catalogo nazionale: 0302 ospedale…) e
  `EDIFC_EDIFC_NOME`. `leggi_dbt_zip` ricompone le sagome con gli attributi: la colonna di legame (`CLASSREF` →
  `CLASSID`) si riconosce dai valori in comune. Verificato sullo zip di Napoli (08/11/2026): `EDIFC.dbf` 31.112 righe
  (CLASSID, EDIFC_SOT 01/02, EDIFC_STAT 01 in costruzione / 02 diruto / 03 costruito, EDIFC_TY, COD_ISTAT 63049),
  `EDIFC_CR_EDF_IS.shp` 31.112 PolygonZ (solo CLASSREF), `EDIFC_EDIFC_USO.dbf` 31.271 righe (CLASSREF, EDIFC_USO a 2,
  4 o 6 cifre: 01, 0801, 030301, 030102…), `EDIFC_EDIFC_NOME.dbf` 761 (CLASSREF, NOME, testo UTF-8 letto come Latin-1).
- **CTR 2020, MapServer `Amministrativo/CTR2020`, strato 4 «Poligoni»** (ArcGIS REST, interrogabile per riquadro,
  GeoJSON in WGS84): campi `tipo` (codice CTR: 31110000 «Edificio civile», 3111000O «edificio ospedale», 31210000
  «Capannone»…) e `descr`. Provato dal vivo l'08/11/2026 sul Cardarelli (790 poligoni, 160 edifici). Serve anche alle
  sagome al volo (`fonti/sagome_regionali.d/campania.toml`).

Altezze: nessuna nel dato. Da **DSM − DTM** (`altezze_dsm.annota`) se un DSM aperto arriverà (oggi nessuno: PST da
verificare dopo il 10/11/2026), altrimenti stima dai vicini o dall'uso, sempre dichiarata. Napoli (decisione di Paolo
dell'08/11/2026 ore 15:22, archivio pubblicato): altezze dal Copernicus Urban Atlas Building Height 2012
(`edifici3d/altezze_ua.py`, zona `campania_napoli` con l'attribuzione Copernicus), poi vicini, poi uso.

Comando sullo zip di Paolo:
  python -m edifici3d.adattatori.campania dbt-zip --zip …/citta_rif/napoli/DBT_5K.zip --uscita napoli_dbt.geojson
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

from ..regionali import Adattatore, Corpo, numero
from .. import altezze_dsm as AD

# codici della CTR 2020 (campo `tipo`, prime cifre) → uso; i codici con la lettera finale precisano l'uso
CTR_USI = {"3111000O": "ospedale", "3111000S": "scuola", "3111000C": "commerciale", "3111000R": "commerciale",
           "3111000H": "commerciale", "3111000I": "capannone", "3111000M": "uffici", "311100SP": "uffici",
           "3121": "capannone", "3122": "capannone", "3123": "capannone", "3141": "palestra", "31110000": "residenziale"}
CTR_EDIFICI = ("311", "312", "313", "314", "3153", "3154", "3160", "3162", "3165", "3166")
CTR_SCARTA = ("31110100", "31114000", "31214000", "3162000A", "31630000", "31640000", "31670000")
CTR_PICCOLI = ("3162", "3165", "3166", "3161")
# usi del catalogo nazionale (EDIFC_USO): come sagome_regionali.USI
# (dominio H_EDIFC_CATEGORIA_USO dello zip di Napoli, 08/11/2026: 0301 sanità, 030102 sede di ospedale, 030104 clinica,
# 0303 istruzione, 030301 scuola, 030302 università, 07 commerciale, 08 industriale)
DBT_USI = {"01": "residenziale", "02": "uffici", "0301": "ospedale", "030101": "uffici", "030103": "uffici",
           "0303": "scuola", "03": "uffici", "07": "commerciale", "08": "capannone", "09": "capannone", "1002": "palestra"}
DBT_DESTINAZIONI = {"01": "residenziale", "0101": "residenziale - abitativa", "02": "amministrativo", "0201": "municipio",
                    "03": "servizio pubblico", "0301": "sanità", "030101": "sede di servizio socio assistenziale",
                    "030102": "sede di ospedale", "030103": "sede servizi sanitari asl", "030104": "sede clinica",
                    "0303": "istruzione", "030301": "sede di scuola", "030302": "università", "0305": "sede di tribunale",
                    "0306": "sede di forze dell'ordine", "04": "militare", "05": "luogo di culto", "06": "servizi di trasporto",
                    "07": "commerciale", "0701": "sede di banca", "08": "industriale", "95": "altro"}
DBT_STATO = {"01": "in costruzione", "02": "diruto, rudere", "03": "costruito"}
DBT_TIPO = {"01": "generica", "02": "palazzo a torre, grattacielo", "04": "villa", "05": "villetta a schiera",
            "07": "campanile", "08": "capannone", "09": "edificio rurale", "10": "castello", "11": "chiesa",
            "13": "faro", "14": "hangar", "19": "palazzetto dello sport", "21": "stadio", "22": "cattedrale", "95": "altro"}


def ctr_edificio(tipo: str) -> bool:
    t = str(tipo or "")
    return t.startswith(CTR_EDIFICI) and t not in CTR_SCARTA


def _uso_ctr(tipo: str) -> str | None:
    t = str(tipo or "")
    return CTR_USI.get(t) or CTR_USI.get(t[:4])


def _uso_dbt(cod, ty=None) -> str | None:
    c = str(cod or "").strip()
    u = (DBT_USI.get(c[:6]) or DBT_USI.get(c[:4]) or DBT_USI.get(c[:2])) if c else None
    return u or ("capannone" if str(ty or "") in ("08", "14") else None)


def _testo(v) -> str:
    """I DBF dello zip hanno testi UTF-8 letti come Latin-1 («UniversitÃ\xa0»): si ricompongono."""
    t = str(v or "").strip()
    try:
        return t.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return t


def _corpo_campania(p: dict, g, z: float | None, quota_dtm: float | None) -> Corpo | None:
    if g.area < 2:
        return None
    if "tipo" in p and "EDIFC_TY" not in p:                     # CTR 2020 dal MapServer
        tipo = str(p.get("tipo") or "")
        if not ctr_edificio(tipo):
            return None
        uso, piccolo, descr = _uso_ctr(tipo), tipo.startswith(CTR_PICCOLI), str(p.get("descr") or "").strip()
        ident, forma = str(p.get("objectid") or p.get("OBJECTID") or p.get("id")), "CTR 2020"
        extra = {"tipo_edificio": descr or tipo, "codice_ctr": tipo}
    else:                                                       # DBT 2020 ricomposto da leggi_dbt_zip
        stato = str(p.get("EDIFC_STAT") or "").strip()
        if stato == "02" or str(p.get("EDIFC_SOT") or "").strip() == "02":   # diruto/rudere, sotterraneo
            return None
        ty = str(p.get("EDIFC_TY") or "").strip()
        uso, piccolo = _uso_dbt(p.get("EDIFC_USO"), ty), False
        ident, forma = str(p.get("CLASSID") or p.get("id")), "DBT 2020"
        cu = str(p.get("EDIFC_USO") or "").strip()
        extra = {"tipo_edificio": DBT_TIPO.get(ty, ty or None), "codice_uso": cu or None,
                 "destinazione": DBT_DESTINAZIONI.get(cu) or DBT_DESTINAZIONI.get(cu[:4]) or DBT_DESTINAZIONI.get(cu[:2]),
                 "stato": DBT_STATO.get(stato, stato or None)}
        if p.get("EDIFC_NOME"):
            extra["nome"] = _testo(p["EDIFC_NOME"])
    r = AD.gronda_da_campi(p, uso, piccolo=piccolo or g.area < 15, rilievo="")
    q = AD.quota_corpo(p, quota_dtm, z if (z is not None and z > -50 and forma == "DBT 2020") else None)
    if q is None and z is not None and z > -50:
        q = z
    if q is None:
        return None
    return Corpo(id=f"cam_{ident}", edificio=f"cam_{ident}", sagoma=g, quota_terreno=q, gronda=r["gronda"], tetto="piano",
                 fonte_sagoma=f"{CAMPANIA.fonte} ({forma})", licenza=CAMPANIA.licenza, fonte_altezza=r["fonte"],
                 qualita=r["qualita"], uso=uso,
                 extra={"regione": "Campania", **{k: v for k, v in {**extra, **r["extra"]}.items() if v not in (None, "")}})


CAMPANIA = Adattatore("campania_dbt", "Regione Campania – DBT/CTR 2020, Edifici", "CC BY 4.0",
                      "Regione Campania – DBT e CTR 2020, Geoportale Regione Campania (CC BY 4.0)", "EPSG:25833",
                      ("EDIFC_TY", "EDIFC_USO"), False, _corpo_campania)

ADATTATORI = (CAMPANIA,)


# ------------------------------------------------------------------------------------------------ zip del DBT


def _nome(zf: zipfile.ZipFile, base: str, est: str) -> str | None:
    for n in zf.namelist():
        if n.split("/")[-1].upper() == f"{base}.{est}".upper():
            return n
    return None


def _tabella(percorso_zip: Path, zf: zipfile.ZipFile, base: str, geometria: bool) -> tuple[list[dict], list]:
    from ..uvl import _leggi
    n = _nome(zf, base, "shp" if geometria else "dbf")
    if n is None:
        return [], []
    righe, geoms, _ = _leggi(f"/vsizip/{Path(percorso_zip).resolve()}/{n}", None, geometria=geometria)
    return righe, geoms


def _legame(righe: list[dict], chiavi: set) -> str | None:
    """Colonna i cui valori coincidono di più con le chiavi date (CLASSID di EDIFC)."""
    if not righe:
        return None
    meglio, n_max = None, 0
    for c in righe[0]:
        n = sum(1 for r in righe[:2000] if str(r.get(c)) in chiavi)
        if n > n_max:
            meglio, n_max = c, n
    return meglio if n_max else None


def leggi_dbt_zip(percorso_zip: Path) -> dict:
    """`DBT_5K.zip` di un comune → GeoJSON (EPSG:25833) delle sagome `EDIFC_CR_EDF_IS` con gli attributi di `EDIFC`
    (EDIFC_TY, EDIFC_STAT, EDIFC_SOT…), l'uso (`EDIFC_USO`, il primo se più d'uno) e il nome."""
    from shapely.geometry import mapping
    with zipfile.ZipFile(percorso_zip) as zf:
        edifc, _ = _tabella(percorso_zip, zf, "EDIFC", False)
        sag, geoms = _tabella(percorso_zip, zf, "EDIFC_CR_EDF_IS", True)
        usi, _ = _tabella(percorso_zip, zf, "EDIFC_EDIFC_USO", False)
        nomi, _ = _tabella(percorso_zip, zf, "EDIFC_EDIFC_NOME", False)
    if not sag:
        raise ValueError(f"{percorso_zip}: manca EDIFC_CR_EDF_IS.shp")
    k_e = "CLASSID" if edifc and "CLASSID" in edifc[0] else (next(iter(edifc[0])) if edifc else None)
    per_id = {str(r[k_e]): r for r in edifc} if k_e else {}
    chiavi = set(per_id)
    k_s = _legame(sag, chiavi)
    k_u, k_n = _legame(usi, chiavi), _legame(nomi, chiavi)
    uso = {}
    for r in usi:
        c = next((r[k] for k in r if k.upper().startswith("EDIFC_USO")), None)
        uso.setdefault(str(r.get(k_u)), c)
    nome = {}
    for r in nomi:
        c = next((r[k] for k in r if "NOME" in k.upper() and k != k_n), None)
        c = _testo(c) if c else c
        nome.setdefault(str(r.get(k_n)), c)
    fs = []
    for r, g in zip(sag, geoms):
        if g is None:
            continue
        cid = str(r.get(k_s)) if k_s else None
        e = per_id.get(cid, {})
        p = {"CLASSID": cid or r.get("CLASSID"), **{k: v for k, v in e.items() if k.upper().startswith("EDIFC_")}}
        p["EDIFC_USO"] = uso.get(cid)
        if nome.get(cid):
            p["EDIFC_NOME"] = nome[cid]
        fs.append({"type": "Feature", "geometry": mapping(g), "properties": {k: v for k, v in p.items() if v is not None}})
    return {"type": "FeatureCollection", "features": fs, "crs": {"type": "name", "properties": {"name": "EPSG:25833"}},
            "legame": {"edifc": k_e, "sagome": k_s, "usi": k_u, "nomi": k_n, "sagome_legate": sum(1 for f in fs if f["properties"].get("EDIFC_TY") is not None)}}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m edifici3d.adattatori.campania")
    sub = ap.add_subparsers(dest="cmd", required=True)
    z = sub.add_parser("dbt-zip", help="DBT_5K.zip di un comune → GeoJSON delle sagome con gli attributi")
    z.add_argument("--zip", type=Path, required=True); z.add_argument("--uscita", type=Path, required=True)
    a = ap.parse_args(argv)
    d = leggi_dbt_zip(a.zip)
    leg = d.pop("legame")
    a.uscita.parent.mkdir(parents=True, exist_ok=True)
    a.uscita.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"sagome": len(d["features"]), "legame": leg, "file": str(a.uscita)}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
