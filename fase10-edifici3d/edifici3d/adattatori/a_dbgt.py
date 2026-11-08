"""Base comune degli adattatori «DBGT nazionale» del gruppo A (08/11/2026): Lazio, Basilicata, Piemonte.

I DB topografici regionali fatti sul Catalogo dei dati territoriali nazionale (DM 10/11/2011) hanno la classe 020101
«Unità volumetrica» (`UN_VOL`) con gli stessi attributi del DBGT lombardo: `UN_VOL_AV` altezza del volume (m),
`UN_VOL_QE` quota di estrusione (m s.l.m., sommità), `UN_VOL_POR` porzione, `CEDIUV` edificio di appartenenza,
`CLASSID` identificativo; spesso la z dei vertici è la quota della base. Le Regioni cambiano però le maiuscole
(Basilicata: `un_vol_av`), i nomi negli Shapefile per comune (`ALTEZZA_VO`, `PORZIONE`) e i campi accessori. Qui una
sola funzione legge tutti i casi da un elenco di nomi possibili, senza distinguere maiuscole e minuscole; ogni regione
dichiara i suoi nomi nel proprio modulo (`lazio.py`, `basilicata.py`, `piemonte.py`).

Regole (uguali per tutte le regioni, come `lombardia_dbgt` di `regionali.py`):
- altezza = campo d'altezza; se manca: quota di estrusione − z della base;
- quota del terreno = DTM (se c'è) → quota di estrusione − altezza → z della base → quota della base dichiarata →
  nessuna (la pagina 3D usa allora l'altitudine del comune, «quota non nota»);
- porzione «08» (sotterranea) scartata: nel DBGT del Lazio (foglio 374) i 2.950 volumi «08» appartengono per il 99 %
  a edifici con `EDIFC_SOT` = 02 (sotterraneo) e hanno la base 2–4 m sotto quella dei volumi vicini; nel DBGT della
  Basilicata «08» è la porzione sotterranea; le porzioni 03/04 (portici, sottopassaggi) hanno la base al livello dei
  volumi vicini e si tengono;
- l'altezza è alla sommità del volume: si usa come gronda («gronda o colmo da verificare», come le UVL dell'ER).

`AdattatoreDBGT` aggiunge a `regionali.Adattatore` il metodo `coerenza(righe)`, usato da `regionali.controlla` quando
la modifica condivisa proposta in `lettori/a/MODIFICHE_CONDIVISE.md` sarà applicata (oggi `controlla` scrive per questi
adattatori il testo della Liguria).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from shapely.geometry import MultiPolygon, Polygon, shape

from ..regionali import Adattatore, Corpo, numero

PORZIONI_SOTTERRANEE = ("08",)


def minuscole(p: dict) -> dict:
    """Proprietà con le chiavi in minuscolo (la prima vince se due chiavi differiscono solo per le maiuscole)."""
    out: dict = {}
    for k, v in p.items():
        out.setdefault(str(k).lower(), v)
    return out


def _vuoto(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v)) or str(v).strip() in ("", "Null", "NULL", "null")


def primo(pm: dict, nomi) -> object | None:
    """Primo valore non vuoto tra i nomi (in minuscolo) dati."""
    for n in nomi:
        v = pm.get(n.lower())
        if not _vuoto(v):
            return v
    return None


def codice(v) -> str | None:
    """Codice di dominio come testo a due cifre («1» → «01», 8.0 → «08»)."""
    if _vuoto(v):
        return None
    s = str(v).strip()
    try:
        f = float(s)
        if f.is_integer() and len(s) <= 4:
            return f"{int(f):02d}"
    except ValueError:
        pass
    return s


def z_base(g) -> float | None:
    """Quota più bassa dei vertici del contorno esterno (z = base del volume nei DBGT con PolygonZ)."""
    if g is None:
        return None
    g = shape(g) if isinstance(g, dict) else g
    if isinstance(g, MultiPolygon):
        g = max(g.geoms, key=lambda x: x.area)
    if not isinstance(g, Polygon):
        return None
    zs = [c[2] for c in g.exterior.coords if len(c) > 2 and c[2] is not None and math.isfinite(c[2])]
    return min(zs) if zs and any(abs(z) > 1e-9 for z in zs) else None


def sotterranea(por: str | None, ad) -> bool:
    """Porzione da scartare: codice «08» o testo del dominio («sotterranea», «interrata»; BDTRE Piemonte usa i testi)."""
    if por is None:
        return False
    return por in ad.porzioni_scartate or any(t in por.lower() for t in ("sotterr", "interrat"))


@dataclass
class Nomi:
    """Nomi possibili dei campi (si prova il primo, poi gli altri; maiuscole indifferenti)."""
    id: tuple = ("CLASSID", "UUID", "UN_VOL_UUID", "id", "ID", "OBJECTID", "ogr_fid", "fid")
    edificio: tuple = ("CEDIUV",)
    altezza: tuple = ("UN_VOL_AV",)
    estrusione: tuple = ("UN_VOL_QE",)
    base: tuple = ()                       # quota della base dichiarata (m s.l.m.), se il DB la dà come campo
    porzione: tuple = ("UN_VOL_POR",)
    anno: tuple = ()                       # data o anno di aggiornamento del dato
    comune: tuple = ()                     # codice ISTAT del comune
    altri: tuple = ()                      # campi copiati così come sono in `extra`


def corpo_dbgt(p: dict, g: Polygon, z: float | None, quota_dtm: float | None, *, ad: "AdattatoreDBGT") -> Corpo | None:
    """Una riga di UN_VOL → corpo (vedi le regole in testa al modulo). `z` è la z media del contorno passata da
    `regionali.corpi` (nei DBGT di Lazio e Basilicata la z è costante sul poligono: media = base)."""
    pm = minuscole(p)
    n = ad.nomi
    por = codice(primo(pm, n.porzione))
    if sotterranea(por, ad):
        return None
    h = numero(primo(pm, n.altezza))
    qe = numero(primo(pm, n.estrusione))
    qb_campo = numero(primo(pm, n.base)) if n.base else None
    zb = z if (z is not None and math.isfinite(z) and abs(z) > 1e-9) else None
    if (h is None or h <= 0) and qe is not None:
        b = qb_campo if qb_campo is not None else zb
        if b is not None:
            h = qe - b                                  # altezza = sommità − base
    if h is None or not math.isfinite(h) or h <= 0 or h > ad.altezza_massima or g.area < 1:
        return None
    if qe is not None:
        base, da = qe - h, "quota di estrusione − altezza"
    elif zb is not None:
        base, da = zb, "z della base"
    elif qb_campo is not None:
        base, da = qb_campo, "quota della base"
    else:
        base, da = None, None
    q = quota_dtm if quota_dtm is not None else base
    fonte_h = f"{ad.nome_breve} {ad.etichetta_altezza} (gronda o colmo da verificare)"
    if quota_dtm is not None and base is not None:
        fonte_h += f"; base DB {base:.1f} m ({da}), DTM {quota_dtm:.1f} m"
    elif base is not None:
        fonte_h += f"; terreno = {da}"
    id_ = primo(pm, n.id)
    ed = primo(pm, n.edificio)
    extra = {"porzione": por, "regione": ad.regione}
    if qe is not None:
        extra["quota_estrusione"] = qe
    if base is not None:
        extra["quota_base_db"] = round(base, 2)
    a = primo(pm, n.anno) if n.anno else None
    if a is not None:
        extra["anno_dato"] = str(a)[:4]
    c = primo(pm, n.comune) if n.comune else None
    if c is not None:
        extra["istat"] = str(c)
    for k in n.altri:
        v = primo(pm, (k,))
        if v is not None:
            extra[k.lower()] = v if isinstance(v, (int, float, str)) else str(v)
    id_ = str(id_) if id_ is not None else f"{ad.chiave}_{round(g.centroid.x, 1)}_{round(g.centroid.y, 1)}"
    return Corpo(id=id_, edificio=str(ed) if ed is not None else id_, sagoma=g, quota_terreno=q, gronda=round(float(h), 3),
                 tetto="piano", fonte_sagoma=ad.fonte, licenza=ad.licenza, fonte_altezza=fonte_h, qualita=ad.qualita,
                 extra=extra)


@dataclass
class AdattatoreDBGT(Adattatore):
    """`regionali.Adattatore` con i nomi dei campi della regione e il controllo di coerenza delle quote."""
    nomi: Nomi = field(default_factory=Nomi)
    regione: str = ""
    nome_breve: str = "DBGT"
    etichetta_altezza: str = "UN_VOL_AV"
    qualita: str = "DBGT, altezza ±1–2 m"
    porzioni_scartate: tuple = PORZIONI_SOTTERRANEE
    altezza_massima: float = 400.0

    def coerenza(self, righe) -> str:
        """Testo per `controlla`: quota di estrusione − z della base = altezza (se ci sono entrambe), oppure quanti
        volumi hanno la z della base, l'altezza, la porzione sotterranea."""
        tot, coer, con_qe, con_z, con_h, sotto = 0, 0, 0, 0, 0, 0
        for p, g in righe:
            tot += 1
            pm = minuscole(p)
            h, qe = numero(primo(pm, self.nomi.altezza)), numero(primo(pm, self.nomi.estrusione))
            zb = z_base(g) if g is not None else None
            con_h += h is not None and h > 0
            con_qe += qe is not None
            con_z += zb is not None
            sotto += sotterranea(codice(primo(pm, self.nomi.porzione)), self)
            if None not in (h, qe, zb):
                zm = _z_media(g)
                if zm is not None and abs(qe - zm - h) < 0.05:
                    coer += 1
        parti = [f"altezza > 0 in {con_h} su {tot}"]
        if con_qe and con_z:
            parti.append(f"quota di estrusione − z della base = altezza in {coer} su {tot}")
        elif con_z:
            parti.append(f"z della base (geometria 3D) in {con_z} su {tot}: quota di gronda = z + altezza")
        elif con_qe:
            parti.append(f"quota di estrusione in {con_qe} su {tot}: terreno = estrusione − altezza")
        else:
            parti.append("nessuna quota assoluta nel file: serve --dtm per la quota del terreno")
        if sotto:
            parti.append(f"{sotto} volumi in porzione sotterranea (scartati)")
        return "; ".join(parti)


def _z_media(g) -> float | None:
    g = shape(g) if isinstance(g, dict) else g
    if isinstance(g, MultiPolygon):
        g = max(g.geoms, key=lambda x: x.area)
    if not isinstance(g, Polygon):
        return None
    zs = [c[2] for c in g.exterior.coords if len(c) > 2]
    return sum(zs) / len(zs) if zs else None


def adattatore(chiave: str, *, fonte: str, licenza: str, attribuzione: str, crs_file: str, campi_attesi: tuple,
               nomi: Nomi, regione: str, nome_breve: str, etichetta_altezza: str, qualita: str,
               serve_dtm: bool = False, **kw) -> AdattatoreDBGT:
    """Costruisce l'adattatore: la funzione `corpo` richiama `corpo_dbgt` con l'adattatore stesso."""
    ad = AdattatoreDBGT(chiave, fonte, licenza, attribuzione, crs_file, campi_attesi, serve_dtm, None, nomi=nomi,
                        regione=regione, nome_breve=nome_breve, etichetta_altezza=etichetta_altezza, qualita=qualita, **kw)
    ad.corpo = lambda p, g, z, q, _ad=ad: corpo_dbgt(p, g, z, q, ad=_ad)
    return ad
