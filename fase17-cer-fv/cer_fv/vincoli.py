"""Vincoli paesaggistici della Regione Emilia-Romagna per «CER – Sviluppo impianti FV» (24/11/2026, sera).

Richiesta di Paolo (24/11, 20:54–20:56): escludere dai terreni pubblici i vincoli del gruppo «Vincoli paesaggistici»
del catalogo dei dati della Regione (https://datacatalog.regione.emilia-romagna.it/catalogCTA/dataset?groups=vincoli-paesaggistici),
licenza CC BY 4.0, con questa divisione:

- **esclusi** (`classe = "escluso"`): boschi (art. 142 c. 1 g), corsi d'acqua con le fasce di 150 m (c), territori
  costieri (a), territori contermini ai laghi (b), zone di interesse archeologico (m), beni archeologici tutelati,
  beni dell'art. 136; in più le zone umide (i), che il catalogo non mette nel gruppo ma il servizio della Regione sì;
- **segnalati** (`classe = "segnalato"`): usi civici e università agrarie (h).

Le zone escluse dai vincoli dell'art. 142 c. 2 non hanno file nel catalogo (24/11/2026): non si possono ancora usare.
Le montagne sopra i 1.200 m (d) e i circhi glaciali (e) non toccano i terreni agricoli della pianura e della collina:
non si scaricano.

Tutto in `DATI/vincoli/` (con `DATI=/srv/energia/dati`), niente copie altrove:
- `scarica()` → gli zip degli shapefile (indirizzi letti dall'API del catalogo, che li può cambiare) e i GML dei beni
  archeologici e delle zone umide dal WFS del Patrimonio culturale dell'Emilia-Romagna;
- `costruisci()` → `vincoli_er.sqlite` con i perimetri semplificati (2 m) in gradi e un indice spaziale, per la rotta
  `/api/cer-fv/vincoli` (livello «Aree non idonee» della pagina);
- `Vincoli` → poligoni in UTM 32N per misurare, nella costruzione dei terreni, quanta parte di ogni particella pubblica
  è vincolata.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("cer_fv.vincoli")

DATI = Path(os.environ.get("DATI", "/srv/energia/dati"))
CARTELLA = DATI / "vincoli"
CATALOGO = "https://datacatalog.regione.emilia-romagna.it/catalogCTA/api/3/action/package_show?id="
WFS_PC = "https://www.patrimonioculturale-er.it/wfs/?SERVICE=WFS&VERSION=1.0.0&REQUEST=GetFeature&TYPENAME="
EPSG_RER = 7791          # RDN2008 / UTM zone 32N, come nei .prj dei file della Regione
ATTRIBUZIONE = ("Vincoli paesaggistici: Regione Emilia-Romagna – adeguamento cartografico del PTPR (CC BY 4.0); beni "
                "archeologici e zone umide: Patrimonio culturale dell'Emilia-Romagna (CC BY 4.0)")


@dataclass(frozen=True)
class Fonte:
    codice: str            # anche nome del file in DATI/vincoli
    nome: str              # come lo legge l'utente
    classe: str            # «escluso» o «segnalato»
    pacchetto: str = ""    # nome del dataset nel catalogo (shapefile in zip)
    shp: tuple = ()        # nomi dei .shp da leggere nello zip
    wfs: str = ""          # strato del WFS del Patrimonio culturale (GML 2, EPSG:4326)


FONTI = (
    Fonte("boschi", "foreste e boschi (art. 142 c. 1 g)", "escluso",
          "aree-tutelate-per-legge-dlgs42-04-art-142-comma-1496228620142-6746", ("AS_FBO_PL",)),
    Fonte("fiumi", "corsi d'acqua e fasce di 150 m (art. 142 c. 1 c)", "escluso",
          "aree-tutelate-per-legge-dlgs42-04-art-142-comma-1496228620137-6746", ("AS_P_FRF_pl", "AS_P_CAC_pl")),
    Fonte("costa", "territori costieri (art. 142 c. 1 a)", "escluso",
          "aree-tutelate-per-legge-dlgs42-04-art-142-comma-1496228620144-6772", ("AS_COS_PL",)),
    Fonte("laghi", "territori contermini ai laghi (art. 142 c. 1 b)", "escluso",
          "aree-tutelate-per-legge-dlgs42-04-art-142-comma-1496228620141-6746", ("AS_TCL_PL",)),
    Fonte("archeologia", "zone di interesse archeologico (art. 142 c. 1 m)", "escluso",
          "aree-tutelate-per-legge-dlgs42-04-art-142-comma-1496228620145-6772", ("AS_ZIA_PL",)),
    Fonte("art136", "beni paesaggistici dichiarati (art. 136)", "escluso",
          "copertura-vettoriale-dei-vincoli-articolo-136-del-dlgs-42-2004-1496228620081-664", ("AS_P_IMM_PL",)),
    Fonte("beni_archeologici", "beni archeologici tutelati", "escluso", wfs="ba_v_vincoli_pl"),
    Fonte("zone_umide", "zone umide (art. 142 c. 1 i)", "escluso", wfs="rer_bp_zoneumide_pl"),
    Fonte("usi_civici", "usi civici e università agrarie (art. 142 c. 1 h)", "segnalato",
          "aree-tutelate-per-legge-dlgs42-04-art-142-comma-1496228620148-6772", ("AS_P_USC_PL",)),
)
PER_CODICE = {f.codice: f for f in FONTI}


def _get(url: str, timeout: int = 600):
    req = urllib.request.Request(url, headers={"User-Agent": "EuGEnio (eugenio.statocritico.it) cer_fv"})
    return urllib.request.urlopen(req, timeout=timeout)   # noqa: S310 - indirizzi fissi della Regione


def _scrivi(url: str, f: Path) -> int:
    tmp = f.with_name(f.name + ".part")
    with _get(url) as r, open(tmp, "wb") as out:
        while blocco := r.read(1 << 20):
            out.write(blocco)
    tmp.replace(f)
    return f.stat().st_size


def url_zip(pacchetto: str) -> str:
    """Indirizzo dello zip dello shapefile dal catalogo (la risorsa SHP/ZIP sul datacatalog)."""
    with _get(CATALOGO + pacchetto, 60) as r:
        d = json.load(r)["result"]
    rr = [x for x in d["resources"] if (x.get("format") or "").upper() in ("SHP", "ZIP")]
    rr.sort(key=lambda x: "datacatalog" not in (x.get("url") or ""))    # prima le copie del catalogo
    if not rr:
        raise IOError(f"{pacchetto}: nessuno shapefile nel catalogo")
    return rr[0]["url"]


def scarica(dest: Path = CARTELLA) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    out = {"cartella": str(dest), "file": {}}
    for f in FONTI:
        if f.wfs:
            n = _scrivi(WFS_PC + f.wfs, dest / f"{f.codice}.gml")
            out["file"][f.codice] = n
        else:
            n = _scrivi(url_zip(f.pacchetto), dest / f"{f.codice}.zip")
            out["file"][f.codice] = n
        log.info("%s: %.1f MB", f.codice, n / 1e6)
    return out


# ------------------------------------------------------------------ lettura
def _anelli_gml(testo: str) -> list:
    return [[tuple(map(float, p.split(","))) for p in t.split()] for t in testo]


def poligoni_gml(f: Path):
    """(proprietà, shapely in EPSG:4326) dal GML 2 di MapServer."""
    import shapely
    ns = {"gml": "http://www.opengis.net/gml"}
    for _, el in ET.iterparse(f, events=("end",)):
        if not el.tag.endswith("featureMember"):
            continue
        feat = list(el)[0]
        props = {c.tag.split("}")[-1]: (c.text or "").strip() for c in feat if c.tag.split("}")[-1] not in ("geom", "boundedBy")}
        poli = []
        for p in feat.iter("{http://www.opengis.net/gml}Polygon"):
            est = p.find("gml:outerBoundaryIs/gml:LinearRing/gml:coordinates", ns)
            buchi = p.findall("gml:innerBoundaryIs/gml:LinearRing/gml:coordinates", ns)
            if est is None:
                continue
            a = _anelli_gml([est.text] + [b.text for b in buchi])
            poli.append(shapely.Polygon(a[0], a[1:]))
        el.clear()
        if poli:
            yield props, shapely.MultiPolygon(poli) if len(poli) > 1 else poli[0]


def poligoni_shp(z: zipfile.ZipFile, nome: str):
    """(proprietà, shapely in UTM 32N) da uno shapefile dentro lo zip (letto in memoria: il più grande, i boschi, è
    ~260 MB)."""
    import io
    import shapefile
    import shapely
    nomi = {n.rsplit("/", 1)[-1].rsplit(".", 1)[0].upper() + "." + n.rsplit(".", 1)[-1].lower(): n for n in z.namelist()}
    if f"{nome.upper()}.shp" not in nomi:
        log.warning("%s: nello zip manca %s.shp (la Regione ha cambiato i nomi?)", z.filename, nome)
        return
    leggi = lambda est: io.BytesIO(z.read(nomi[f"{nome.upper()}.{est}"]))  # noqa: E731
    r = shapefile.Reader(shp=leggi("shp"), shx=leggi("shx") if f"{nome.upper()}.shx" in nomi else None, dbf=leggi("dbf"),
                         encoding="utf-8", encodingErrors="replace")
    campi = [x[0] for x in r.fields[1:]]
    for sr in r.iterShapeRecords():
        geo = _poligono(sr.shape)
        if geo is not None:
            yield dict(zip(campi, sr.record)), geo


def _poligono(sh):
    """Shapely da una forma poligonale dello shapefile: anelli orari = esterni, antiorari = buchi dell'ultimo esterno
    (la conversione di pyshp si ferma sugli anelli degeneri, che qui si saltano)."""
    import shapely
    if sh.shapeType not in (5, 15, 25) or not sh.points:
        return None
    parti = list(sh.parts) + [len(sh.points)]
    poli = []
    for a, b in zip(parti[:-1], parti[1:]):
        anello = [p[:2] for p in sh.points[a:b]]
        if len(anello) < 4:
            continue
        area2 = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(anello, anello[1:] + anello[:1]))
        if area2 == 0:
            continue
        if area2 < 0 or not poli:                   # orario (area negativa): esterno
            poli.append([anello, []])
        else:
            poli[-1][1].append(anello)
    try:
        geo = shapely.MultiPolygon([shapely.Polygon(e, h) for e, h in poli]) if len(poli) > 1 else shapely.Polygon(*poli[0]) if poli else None
        if geo is not None and not geo.is_valid:
            geo = shapely.make_valid(geo)
        return geo if geo is not None and not geo.is_empty else None
    except Exception:   # noqa: BLE001 - geometria rovinata: si salta
        return None


def _nome(f: Fonte, p: dict) -> str:
    for k in ("TITOLO", "titolo", "nome", "nm_sda", "denom", "NOME_USU", "NOME_USC"):
        if p.get(k):
            return f"{f.nome}: {str(p[k]).strip()}"[:200]
    return f.nome


def elementi(cartella: Path = CARTELLA):
    """(fonte, nome, shapely in UTM 32N) di tutte le fonti presenti nella cartella."""
    from pyproj import Transformer
    import shapely.ops
    da4326 = Transformer.from_crs(4326, EPSG_RER, always_xy=True)
    for f in FONTI:
        if f.wfs:
            p = cartella / f"{f.codice}.gml"
            if not p.exists():
                log.warning("manca %s", p)
                continue
            for props, g in poligoni_gml(p):
                yield f, _nome(f, props), shapely.ops.transform(da4326.transform, g)
        else:
            p = cartella / f"{f.codice}.zip"
            if not p.exists():
                log.warning("manca %s", p)
                continue
            with zipfile.ZipFile(p) as z:
                for nome in f.shp:
                    for props, g in poligoni_shp(z, nome):
                        if str(props.get("escluso") or "").strip().upper() == "E":     # tratti di fiume esclusi
                            continue
                        yield f, _nome(f, props), g


# ------------------------------------------------------------------ per i terreni: quota vincolata della particella
class Vincoli:
    def __init__(self, cartella: Path = CARTELLA):
        import shapely
        self.fonti, self.nomi, geo = [], [], []
        for f, nome, g in elementi(cartella):
            self.fonti.append(f); self.nomi.append(nome); geo.append(g)
        self.geo = geo
        self.albero = shapely.STRtree(geo) if geo else None
        log.info("vincoli: %d poligoni (%s)", len(geo), ", ".join(sorted({f.codice for f in self.fonti})))

    def misura(self, particella_utm) -> dict:
        """quota_vincolata (0-1, dei vincoli che escludono, sovrapposizioni contate una volta), testo dei vincoli con
        la quota di ognuno, testo dei vincoli solo segnalati."""
        import shapely
        if self.albero is None or particella_utm is None or particella_utm.is_empty or particella_utm.area <= 0:
            return {"quota_vincolata": None, "vincoli": None, "vincoli_segnalati": None}
        area = particella_utm.area
        escl, per_fonte, segn = [], {}, {}
        for i in self.albero.query(particella_utm, predicate="intersects"):
            try:
                x = self.geo[i].intersection(particella_utm)
            except Exception:   # noqa: BLE001
                continue
            if x.is_empty or x.area / area < 0.01:
                continue
            f = self.fonti[i]
            if f.classe == "escluso":
                escl.append(x)
                per_fonte[f.nome] = per_fonte.get(f.nome, 0) + x.area
            else:
                segn[self.nomi[i]] = segn.get(self.nomi[i], 0) + x.area
        quota = min(1.0, shapely.union_all(escl).area / area) if escl else 0.0
        testo = "; ".join(f"{n} {round(100 * min(1, a / area))} %" for n, a in sorted(per_fonte.items(), key=lambda kv: -kv[1]))
        stesto = "; ".join(f"{n} {round(100 * min(1, a / area))} %" for n, a in sorted(segn.items(), key=lambda kv: -kv[1]))
        return {"quota_vincolata": round(quota, 3), "vincoli": testo or None, "vincoli_segnalati": stesto or None}


# ------------------------------------------------------------------ per la mappa: perimetri semplificati
def costruisci(cartella: Path = CARTELLA, tolleranza_m: float = 2.0) -> dict:
    from pyproj import Transformer
    import shapely
    import shapely.ops
    t0 = time.time()
    a4326 = Transformer.from_crs(EPSG_RER, 4326, always_xy=True)
    f = cartella / "vincoli_er.sqlite"
    tmp = f.with_name(f.name + ".tmp")
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(tmp)
    db.execute("CREATE TABLE v (id INTEGER PRIMARY KEY, codice, classe, nome, geojson)")
    db.execute("CREATE VIRTUAL TABLE v_rt USING rtree(id, ovest, est, sud, nord)")
    n, per = 0, {}
    for fonte, nome, g in elementi(cartella):
        s = shapely.ops.transform(a4326.transform, g.simplify(tolleranza_m, preserve_topology=True))
        if s.is_empty:
            continue
        s = shapely.set_precision(s, 1e-5)          # ~1 m: basta per la mappa e alleggerisce le risposte
        n += 1
        per[fonte.codice] = per.get(fonte.codice, 0) + 1
        x0, y0, x1, y1 = s.bounds
        db.execute("INSERT INTO v VALUES (?,?,?,?,?)", (n, fonte.codice, fonte.classe, nome, json.dumps(shapely.geometry.mapping(s), separators=(",", ":"))))
        db.execute("INSERT INTO v_rt VALUES (?,?,?,?,?)", (n, x0, x1, y0, y1))
    info = {"costruito": time.strftime("%Y-%m-%d %H:%M"), "poligoni": n, "per_fonte": per, "attribuzione": ATTRIBUZIONE}
    db.execute("CREATE TABLE info (chiave PRIMARY KEY, valore)")
    db.executemany("INSERT INTO info VALUES (?, ?)", [(k, json.dumps(v)) for k, v in info.items()])
    db.commit(); db.close()
    tmp.replace(f)
    info.update(file=str(f), mb=round(f.stat().st_size / 1e6, 1), secondi=round(time.time() - t0, 1))
    log.info("scritto %s: %d poligoni, %.1f MB", f, n, info["mb"])
    return info
