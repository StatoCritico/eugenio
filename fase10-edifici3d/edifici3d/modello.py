"""Corpi ed edifici (§ 7 della proposta), piani e superfici (§ 8), indicatori geometrici (§ 9, analisi 1).

Un **corpo** è un prisma: sagoma (poligono in metri, sistema proiettato), quota del terreno, altezza di gronda e di colmo
sopra il terreno, tetto (piano o a falde), piani, fonte e qualità di ogni dato, edificio di appartenenza e licenza della
sagoma. Un **edificio** è l'insieme dei suoi corpi: si seleziona, si somma e va nei report come un'unità.

Piani: valore dichiarato nel CSV → visura catastale → stima dall'altezza (interpiano per uso). Superficie lorda =
Σ area × piani; netta ≈ 0,80–0,85 × lorda (0,82 se non c'è altro). La fonte di ogni numero resta accanto al numero.

Indicatori geometrici: volume lordo, superficie disperdente (pareti esposte + tetto + pavimento a terra), S/V, pareti
per orientamento (8 settori), pareti in comune con altri corpi (dello stesso edificio o confinanti): non disperdono,
tranne la parte che sporge sopra il corpo vicino più basso. Sono grandezze geometriche, non metodiche UNI.

Le stesse regole sono nel sito (`fase5-sito/sito/edifici_calcoli.js`); i test controllano che le tabelle coincidano.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict

from shapely.geometry import LineString, Polygon, MultiPolygon
from shapely.geometry.base import BaseGeometry

# interpiano tipico per uso (m), § 8: residenziale ~3,0; uffici e scuole 3,3–3,6; ospedali 3,8–4,5; capannoni un piano
INTERPIANI: dict[str, float] = {
    "residenziale": 3.0, "uffici": 3.4, "scuola": 3.5, "ospedale": 4.0, "commerciale": 4.0, "altro": 3.2,
}
UN_PIANO = {"capannone", "palestra", "industriale"}       # un solo piano, qualunque sia l'altezza
SOVRALZO = 0.3            # sovralzo del piano terra sul terreno (m)
NETTA_SU_LORDA = 0.82     # rapporto tipico 0,80–0,85
CAT_CATASTALI = {         # categoria catastale → uso, per la stima dei piani
    "A": "residenziale", "A/10": "uffici", "B/1": "altro", "B/4": "uffici", "B/5": "scuola", "B/2": "ospedale",
    "C/1": "commerciale", "D/1": "capannone", "D/4": "ospedale", "D/7": "capannone", "D/8": "commerciale",
    "C/2": "capannone", "C/3": "capannone",
}
SETTORI = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
TOLLERANZA_COMUNE = 0.25  # m: due lati più vicini di così sono una parete in comune


@dataclass
class Valore:
    """Un numero con la sua fonte: «csv», «visura», «stima», «DBTR UVL», «utente», … e la qualità (testo libero)."""
    valore: float | int | None
    fonte: str
    qualita: str | None = None


@dataclass
class Corpo:
    id: str
    edificio: str
    sagoma: Polygon                    # metri, sistema proiettato
    quota_terreno: float | None        # m s.l.m. (minimo o mediana del DTM, o base del DBTR)
    gronda: float                      # m sopra il terreno
    colmo: float | None = None         # m sopra il terreno; None o = gronda per il tetto piano
    tetto: str = "piano"               # piano | capanna | padiglione
    falde: int = 0
    piani: int | None = None
    fonte_sagoma: str = ""
    licenza: str = ""                  # licenza della sagoma: «CC BY 4.0» o «ODbL 1.0»
    fonte_altezza: str = ""
    qualita: str = ""
    uso: str | None = None
    extra: dict = field(default_factory=dict)

    @property
    def area(self) -> float:
        return float(self.sagoma.area)

    @property
    def altezza_media(self) -> float:
        """Altezza media del volume: tetto piano = gronda; falde = gronda + metà del dislivello."""
        if self.colmo is None or self.colmo <= self.gronda or self.tetto == "piano":
            return self.gronda
        return self.gronda + (self.colmo - self.gronda) / (2 if self.tetto == "capanna" else 3)

    def proprieta(self) -> dict:
        d = {k: v for k, v in asdict(self).items() if k not in ("sagoma", "extra")}
        d["area"] = round(self.area, 1)
        return d


# --------------------------------------------------------------------------------------------- piani e superfici
def uso_da(categoria: str | None = None, osm_building: str | None = None, dichiarato: str | None = None) -> str:
    """Uso del corpo: dichiarazione dell'utente → categoria catastale → tag OSM `building` → «altro»."""
    if dichiarato:
        return dichiarato.strip().lower()
    if categoria:
        c = categoria.strip().upper().replace(" ", "")
        if c in CAT_CATASTALI:
            return CAT_CATASTALI[c]
        if c[:1] in CAT_CATASTALI:
            return CAT_CATASTALI[c[:1]]
    osm = {"house": "residenziale", "apartments": "residenziale", "residential": "residenziale", "detached": "residenziale",
           "office": "uffici", "school": "scuola", "university": "scuola", "hospital": "ospedale",
           "retail": "commerciale", "commercial": "commerciale", "industrial": "capannone", "warehouse": "capannone",
           "sports_hall": "palestra"}
    return osm.get((osm_building or "").strip().lower(), "altro")


def stima_piani(gronda: float, uso: str = "altro") -> int:
    """piani ≈ (gronda − sovralzo) ÷ interpiano, arrotondato, almeno 1 (un solo piano per capannoni e palestre)."""
    if uso in UN_PIANO:
        return 1
    if gronda is None or not math.isfinite(gronda) or gronda <= 0:
        return 1
    return max(1, round((gronda - SOVRALZO) / INTERPIANI.get(uso, INTERPIANI["altro"])))


def scegli(csv=None, visura=None, stima=None, nomi=("csv", "visura", "stima")) -> Valore:
    """Precedenza del § 8: valore del CSV → visura catastale → stima. Vuoti, testi non numerici e ≤ 0 si saltano."""
    for v, nome in zip((csv, visura, stima), nomi):
        n = numero(v)
        if n is not None and n > 0:
            return Valore(n, nome)
    return Valore(None, "mancante")


def numero(v) -> float | None:
    """Numero anche all'italiana («1.234,5»); None per vuoti e testi."""
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v) if math.isfinite(v) else None
    s = str(v).strip().replace(" ", "")
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        x = float(s)
    except ValueError:
        return None
    return x if math.isfinite(x) else None


@dataclass
class Edificio:
    id: str
    corpi: list[Corpo]

    def superfici(self, csv: dict | None = None, visura: dict | None = None) -> dict:
        """Piani e superfici con fonte. csv / visura: dict con le colonne facoltative di Patrimonio (piani_fuori_terra,
        piani_interrati, superficie_lorda, superficie_netta, superficie_catastale, anno_costruzione)."""
        csv, visura = csv or {}, visura or {}
        per_corpo = []
        lorda_stimata = 0.0
        for c in self.corpi:
            p = c.piani if c.piani else stima_piani(c.gronda, c.uso or "altro")
            per_corpo.append({"corpo": c.id, "piani": p, "fonte": "dato del corpo" if c.piani else "stima"})
            lorda_stimata += c.area * p
        piani_max = max((x["piani"] for x in per_corpo), default=None)
        piani = scegli(csv.get("piani_fuori_terra"), visura.get("piani_fuori_terra"), piani_max)
        interrati = scegli(csv.get("piani_interrati"), visura.get("piani_interrati"), None)
        lorda = scegli(csv.get("superficie_lorda"), visura.get("superficie_lorda"), lorda_stimata or None)
        netta_st = lorda.valore * NETTA_SU_LORDA if lorda.valore else None
        netta = scegli(csv.get("superficie_netta"), visura.get("superficie_netta"), netta_st)
        catastale = scegli(csv.get("superficie_catastale"), visura.get("superficie_catastale"), None)
        anno = scegli(csv.get("anno_costruzione"), visura.get("anno_costruzione"), None)
        return {"piani_fuori_terra": piani, "piani_interrati": interrati, "superficie_lorda": lorda,
                "superficie_netta": netta, "superficie_catastale": catastale, "anno_costruzione": anno,
                "per_corpo": per_corpo}


# --------------------------------------------------------------------------------------------- indicatori geometrici
def _lati(p: Polygon):
    xs = list(p.exterior.coords)
    for a, b in zip(xs, xs[1:]):
        if a != b:
            yield a, b
    for anello in p.interiors:
        cs = list(anello.coords)
        for a, b in zip(cs, cs[1:]):
            if a != b:
                yield a, b


def orientamento(a, b, ccw: bool) -> float:
    """Azimut (gradi da nord, in senso orario) della normale esterna del lato a→b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    nx, ny = (dy, -dx) if ccw else (-dy, dx)     # anello antiorario: la normale esterna è a destra
    return (math.degrees(math.atan2(nx, ny)) + 360) % 360


def settore(az: float) -> str:
    return SETTORI[int(((az + 22.5) % 360) // 45)]


def _poligoni(g: BaseGeometry) -> list[Polygon]:
    if isinstance(g, Polygon):
        return [g]
    if isinstance(g, MultiPolygon):
        return list(g.geoms)
    return []


def in_comune(a, b, altro: Polygon) -> float:
    """Lunghezza del lato a→b affacciata a un lato di `altro` parallelo (entro 5°) e a meno di TOLLERANZA_COMUNE."""
    seg = LineString([a, b])
    lung = seg.length
    ux, uy = (b[0] - a[0]) / lung, (b[1] - a[1]) / lung
    tot = 0.0
    for p in _poligoni(altro):
        for c, d in _lati(p):
            l2 = math.dist(c, d)
            if l2 < 1e-6:
                continue
            vx, vy = (d[0] - c[0]) / l2, (d[1] - c[1]) / l2
            if abs(ux * vy - uy * vx) > 0.087:          # non paralleli (più di ~5°)
                continue
            if abs((c[0] - a[0]) * uy - (c[1] - a[1]) * ux) > TOLLERANZA_COMUNE:   # troppo lontani
                continue
            t1 = (c[0] - a[0]) * ux + (c[1] - a[1]) * uy
            t2 = (d[0] - a[0]) * ux + (d[1] - a[1]) * uy
            tot += max(0.0, min(lung, max(t1, t2)) - max(0.0, min(t1, t2)))
    return min(tot, lung)


def indicatori(edificio: Edificio, vicini: list[Corpo] = ()) -> dict:
    """Volume lordo, superfici disperdenti, S/V, pareti per orientamento e in comune (analisi 1 del § 9).

    Ogni lato di ogni corpo è una parete alta quanto la gronda del corpo; per i tratti che toccano un altro corpo
    (dello stesso edificio o dei vicini) la parte fino alla gronda del vicino è «in comune» e non disperde; la parte
    che sporge sopra disperde. I tetti a falde contano con la superficie inclinata."""
    altri = [c for c in vicini if c.edificio != edificio.id]
    volume = tetti = pavimenti = 0.0
    pareti = {s: 0.0 for s in SETTORI}
    comuni_stesso = comuni_vicini = 0.0
    corpi = edificio.corpi
    from shapely.geometry.polygon import orient
    for c in corpi:
        p = c.sagoma.buffer(0) if not c.sagoma.is_valid else c.sagoma
        if isinstance(p, Polygon):
            p = orient(p, 1.0)          # esterno antiorario, fori orari: la normale dei lati dei cortili guarda il cortile
        volume += c.area * c.altezza_media
        pavimenti += c.area
        if c.colmo and c.colmo > c.gronda and c.tetto != "piano":
            # larghezza minore del rettangolo minimo come campata: falde inclinate di atan(dislivello / semi-campata)
            r = p.minimum_rotated_rectangle
            xs = list(r.exterior.coords)
            l1 = math.dist(xs[0], xs[1]); l2 = math.dist(xs[1], xs[2])
            semi = max(min(l1, l2) / 2, 0.5)
            tetti += c.area / math.cos(math.atan((c.colmo - c.gronda) / semi))
        else:
            tetti += c.area
        ccw = p.exterior.is_ccw
        for a, b in _lati(p):
            seg = LineString([a, b])
            lung = seg.length
            if lung <= 1e-6:
                continue
            az = orientamento(a, b, ccw)
            esposta = lung * c.gronda
            for o in corpi + altri:
                if o is c:
                    continue
                comune = in_comune(a, b, o.sagoma)
                if comune <= 0.01:
                    continue
                coperta = comune * min(c.gronda, o.gronda)
                esposta -= coperta
                if o.edificio == c.edificio:
                    comuni_stesso += coperta / 2       # vista dai due corpi: metà per lato
                else:
                    comuni_vicini += coperta
            pareti[settore(az)] += max(esposta, 0.0)
    pareti_esposte = sum(pareti.values())
    disperdente = pareti_esposte + tetti + pavimenti
    return {
        "volume_lordo": volume, "superficie_pavimento_terra": pavimenti, "superficie_tetti": tetti,
        "pareti_esposte": pareti_esposte, "pareti_per_orientamento": pareti,
        "pareti_in_comune_tra_corpi": comuni_stesso, "pareti_in_comune_con_vicini": comuni_vicini,
        "superficie_disperdente": disperdente, "s_su_v": disperdente / volume if volume > 0 else None,
    }
