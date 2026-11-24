"""Probabilità di coltura DOP o certificata per particella, dai piani colturali grafici di AGREA (24/11/2026).

**I dati AGREA non si cedono** (decisione di Paolo del 24/11/2026): i file stanno sul server in `DATI/agrea/<campagna>/`
(zip o shapefile come scaricati da https://agrea.regione.emilia-romagna.it/servizi/documentazione/open-data-sullutilizzo-del-suolo-1),
non entrano nel repository né nelle risposte dell'API; da qui esce solo un numero 0-100 per particella e la sua classe.

Regole in `regole_colture.toml` (accanto a questo file). Campi usati del tracciato AGREA (descrizione della fornitura dei
piani colturali grafici): DESC_COLT, DESC_USO, DESC_QUAL, FLAG_BIO, FLAG_INTE e la geometria dell'appezzamento; i nomi si
cercano senza distinguere maiuscole e con qualche variante (COD_/DESC_ troncati dai DBF a 10 caratteri).
"""
from __future__ import annotations

import logging
import re
import tomllib
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

log = logging.getLogger("cer_fv.colture")
QUI = Path(__file__).resolve().parent
SI = {"S", "SI", "Y", "YES", "1", "T", "TRUE", "X"}

# province dell'Emilia-Romagna: nome (come nel censimento MEF) → codice ISTAT a 3 cifre, per i fattori delle regole
PROVINCE_ER = {"PIACENZA": "033", "PARMA": "034", "REGGIO EMILIA": "035", "REGGIO NELL'EMILIA": "035", "MODENA": "036",
               "BOLOGNA": "037", "FERRARA": "038", "RAVENNA": "039", "FORLI'-CESENA": "040", "FORLÌ-CESENA": "040",
               "FORLI-CESENA": "040", "RIMINI": "099"}


def codice_provincia(nome: str | None) -> str:
    n = re.sub(r"\s+", " ", str(nome or "").strip().upper())
    return PROVINCE_ER.get(n, "")


@dataclass
class Categoria:
    nome: str
    cerca: re.Pattern
    peso: float
    province: dict[str, float]

    def fattore(self, provincia: str) -> float:
        return self.province.get(provincia, self.province.get("*", 0.0))


@dataclass
class Regole:
    campagne: int = 3
    alta: int = 60
    media: int = 30
    qualita: re.Pattern = field(default_factory=lambda: re.compile(r"\b(DOP|IGP|DOC|DOCG|IGT)\b"))
    categorie: list[Categoria] = field(default_factory=list)

    def classe(self, p: int | None) -> str:
        if p is None:
            return "non dichiarata"
        return "alta" if p >= self.alta else "media" if p >= self.media else "bassa"


def regole(percorso: Path | None = None) -> Regole:
    d = tomllib.loads((percorso or QUI / "regole_colture.toml").read_text(encoding="utf-8"))
    cat = [Categoria(c["nome"], re.compile(c["cerca"], re.I), float(c["peso"]), {str(k): float(v) for k, v in c.get("province", {}).items()})
           for c in d.get("categoria", [])]
    return Regole(int(d.get("campagne", 3)), int(d["classi"]["alta"]), int(d["classi"]["media"]),
                  re.compile(d.get("qualita_certificata", r"\b(DOP|IGP)\b"), re.I), cat)


def peso_appezzamento(r: dict, provincia: str, R: Regole) -> float:
    """Peso 0-1 di un appezzamento: 1 se biologico, integrato o di qualità DOP/IGP; altrimenti categoria × provincia."""
    if str(r.get("flag_bio") or "").strip().upper() in SI or str(r.get("flag_inte") or "").strip().upper() in SI:
        return 1.0
    if R.qualita.search(str(r.get("desc_qual") or "")):
        return 1.0
    testo = f"{r.get('desc_colt') or ''} {r.get('desc_uso') or ''}".upper()
    for c in R.categorie:
        if c.cerca.search(testo):
            return max(0.0, min(1.0, c.peso * c.fattore(provincia)))
    return 0.0


# ------------------------------------------------------------------ lettura dei file AGREA
ALIAS = {"desc_colt": ["DESC_COLT", "DESC_COLTU", "DS_COLT", "COLTURA"], "desc_uso": ["DESC_USO", "DS_USO", "USO"],
         "desc_qual": ["DESC_QUAL", "DS_QUAL", "QUALITA"], "flag_bio": ["FLAG_BIO", "FL_BIO", "BIO"],
         "flag_inte": ["FLAG_INTE", "FLAG_INTEG", "FL_INTE", "INTEGRATO"]}


def _campi(nomi: list[str]) -> dict[str, int]:
    up = [n.upper() for n in nomi]
    out = {}
    for k, alias in ALIAS.items():
        for a in alias:
            if a in up:
                out[k] = up.index(a)
                break
    return out


def _crs_da(prj: str | None, x: float, y: float):
    from pyproj import CRS
    if prj:
        try:
            return CRS.from_wkt(prj)
        except Exception:   # noqa: BLE001 - .prj illeggibile: si va per tentativi sotto
            log.warning("file .prj non leggibile, sistema di riferimento dedotto dalle coordinate")
    if 1_000_000 < x < 2_000_000 and 4_000_000 < y < 5_500_000:
        return CRS.from_epsg(3003)                      # Monte Mario / Gauss-Boaga fuso Ovest
    if 200_000 < x < 1_000_000 and 4_000_000 < y < 5_500_000:
        return CRS.from_epsg(32632)                     # UTM 32N (WGS84/ETRS89)
    if -180 <= x <= 180 and -90 <= y <= 90:
        return CRS.from_epsg(4326)
    raise ValueError(f"sistema di riferimento AGREA non riconosciuto (x={x}, y={y}): aggiungere il file .prj")


def _shapefile_in(percorso: Path) -> Iterator[tuple[str, object]]:
    """(nome, shapefile.Reader) per ogni .shp della cartella o degli zip (anche zip dentro zip, un livello)."""
    import io
    import shapefile
    if percorso.is_dir():
        for p in sorted(percorso.rglob("*")):
            if p.suffix.lower() in {".shp", ".zip"}:
                yield from _shapefile_in(p)
        return
    if percorso.suffix.lower() == ".shp":
        prj = percorso.with_suffix(".prj")
        r = shapefile.Reader(str(percorso), encoding="latin-1")
        r._prj = prj.read_text(encoding="latin-1", errors="replace") if prj.exists() else None
        yield percorso.name, r
        return
    if percorso.suffix.lower() == ".zip":
        with zipfile.ZipFile(percorso) as z:
            nomi = z.namelist()
            for n in nomi:
                if n.lower().endswith(".zip"):
                    tmp = percorso.parent / f".{percorso.stem}__{Path(n).name}"
                    tmp.write_bytes(z.read(n))
                    try:
                        yield from _shapefile_in(tmp)
                    finally:
                        tmp.unlink(missing_ok=True)
            for n in nomi:
                if not n.lower().endswith(".shp"):
                    continue
                base = n[:-4]
                leggi = lambda e: io.BytesIO(z.read(base + e)) if (base + e) in nomi else None   # noqa: E731
                ext = {e.lower(): e for e in (".dbf", ".DBF", ".shx", ".SHX", ".prj", ".PRJ") if (base + e) in nomi}
                r = shapefile.Reader(shp=io.BytesIO(z.read(n)), dbf=leggi(ext.get(".dbf", ".dbf")),
                                     shx=leggi(ext.get(".shx", ".shx")), encoding="latin-1")
                p = ext.get(".prj")
                r._prj = z.read(base + p).decode("latin-1", "replace") if p else None
                yield f"{percorso.name}:{n}", r


def appezzamenti(cartella: Path) -> Iterator[tuple[object, dict]]:
    """(poligono shapely in EPSG:3003, attributi) degli appezzamenti di una campagna."""
    import shapely
    import shapely.geometry
    import shapely.ops
    from pyproj import CRS, Transformer
    dest = CRS.from_epsg(3003)
    for nome, r in _shapefile_in(cartella):
        campi = _campi([f[0] for f in r.fields[1:]])
        if "desc_colt" not in campi and "desc_uso" not in campi:
            log.warning("%s: nessun campo della coltura (DESC_COLT/DESC_USO), saltato", nome)
            continue
        tr = None
        n = 0
        for sr in r.iterShapeRecords():
            g = sr.shape.__geo_interface__
            if not g or not g.get("coordinates"):
                continue
            if tr is None:
                x, y = sr.shape.points[0]
                crs = _crs_da(r._prj, x, y)
                tr = None if crs == dest else Transformer.from_crs(crs, dest, always_xy=True)
            geom = shapely.geometry.shape(g)
            if tr is not None:
                geom = shapely.ops.transform(tr.transform, geom)
            if not geom.is_valid:
                geom = shapely.make_valid(geom)
            rec = sr.record
            yield geom, {k: rec[i] for k, i in campi.items()}
            n += 1
        log.info("%s: %d appezzamenti", nome, n)


def campagne_disponibili(radice: Path, quante: int) -> list[tuple[int, Path]]:
    """Ultime `quante` campagne in `radice/<anno>/`."""
    if not radice or not radice.exists():
        return []
    anni = sorted((int(p.name), p) for p in radice.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}", p.name))
    return anni[-quante:]


class Indice:
    """Appezzamenti di una campagna con il loro peso, in un STRtree; il peso dipende dalla provincia della particella."""

    def __init__(self, anno: int, elementi: list[tuple[object, dict]]):
        import shapely
        self.anno = anno
        self.geom = [g for g, _ in elementi]
        self.att = [a for _, a in elementi]
        self.albero = shapely.STRtree(self.geom) if self.geom else None
        self.limiti = shapely.total_bounds(self.geom) if self.geom else None

    def quota(self, particella, provincia: str, R: Regole) -> tuple[float, float]:
        """(quota pesata, quota dichiarata) della particella coperta dagli appezzamenti della campagna."""
        if self.albero is None or particella.area <= 0:
            return 0.0, 0.0
        pesata = coperta = 0.0
        for i in self.albero.query(particella, predicate="intersects"):
            a = particella.intersection(self.geom[i]).area / particella.area
            if a <= 0:
                continue
            coperta += a
            pesata += a * peso_appezzamento(self.att[i], provincia, R)
        return min(1.0, pesata), min(1.0, coperta)


def carica(radice: Path, R: Regole) -> list[Indice]:
    out = []
    for anno, cartella in campagne_disponibili(radice, R.campagne):
        el = list(appezzamenti(cartella))
        log.info("campagna %d: %d appezzamenti", anno, len(el))
        out.append(Indice(anno, el))
    return out


def indicatore(particella_3003, provincia: str, indici: Iterable[Indice], R: Regole) -> dict:
    """Probabilità 0-100 (massimo delle campagne), classe, campagne usate e quota dichiarata ad AGREA."""
    migliore, dich, anni = None, 0.0, []
    for ix in indici:
        q, c = ix.quota(particella_3003, provincia, R)
        anni.append(ix.anno)
        dich = max(dich, c)
        if c > 0:
            migliore = q if migliore is None else max(migliore, q)
    p = None if migliore is None else int(round(100 * migliore))
    return {"prob_coltura": p, "classe_coltura": R.classe(p), "campagne": ",".join(map(str, anni)),
            "quota_dichiarata": round(dich, 3)}
