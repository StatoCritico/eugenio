"""Dove mettere la mappa dopo la ricerca di un indirizzo (17/11/2026, segnalazione di Paolo).

Prima la ricerca delle pagine di mappa (Ortofoto, Modelli 3D, pagine dell'edificio: `fase5-sito/sito/cerca_luogo.js`)
andava sul punto della riga di `patrimonio.geolocalizza` a zoom fisso 17:
  * con il civico, sull'**accesso** ANNCSU (il portone sulla strada): per gli edifici grandi l'edificio resta fuori dalla
    vista (Rimini, viale Settembrini 2, ospedale Infermi: l'accesso «2» è all'angolo sud, l'ospedale 300–500 m più a nord);
  * senza civico, sul **civico di numero mediano** della via (ANNCSU) o sul punto della via dato da Zornade: per le vie
    lunghe è un punto qualsiasi (Rimini, via Coriano, ~6 km), e se la via non c'è con quel nome Zornade può portare
    lontano senza avviso (Perugia, «via Sant'Andrea delle Fratte»: è una frazione, non una via).

Qui, per la **sola ricerca di un luogo** (una riga), si aggiunge alla riga:
  * civico (o foglio e particella) → la **particella catastale** che contiene il punto, dalla cartografia catastale
    dell'Agenzia delle Entrate (servizio WFS INSPIRE, CC BY 4.0, nessuna chiave; la stessa fonte dello strato «Particelle»
    delle ortofoto, che usa il WMS): punto **interno garantito** (baricentro se cade dentro, altrimenti il centro del tratto
    interno più largo: particelle a L o a C) e riquadro; se il punto cade sulla strada (le strade non sono particelle, o sono
    particelle «STRADA…»), la particella edificata più vicina entro RAGGIO_M metri, preferendo quella scelta da Zornade.
    Civico ANNCSU con più accessi (2, 2/B … 2/O entro COMPLESSO_M metri) e cercato senza esponente: fra le particelle che
    contengono gli accessi si prende **la più grande** (decisione di Paolo del 17/11/2026, «scelta B»: un civico con molti
    esponenti è un complesso, l'ospedale Infermi è la particella n. 1, non quella dell'accesso «2» all'angolo sud); con un
    solo accesso, o con l'esponente scritto («2/B»), la particella di quell'accesso. La regola applicata è in `luogo_regola`;
  * via senza civico → il **punto a metà della lunghezza** della via (non il baricentro dei vertici) e il riquadro della via,
    dalle strade di OpenStreetMap (ODbL) con quel nome nel comune (`highway`, unite in catene; se non formano una linea sola,
    il punto che lascia metà della lunghezza da ciascuna parte lungo l'asse principale), altrimenti dai civici ANNCSU della
    via; tratti lontani più di GRUPPO_M metri sono vie diverse (frazioni);
  * più vie compatibili (nomi simili, stessa via in frazioni diverse, via non riconosciuta) → l'**elenco** da far scegliere
    alla pagina invece di andare lontano, con le località (frazioni) di OpenStreetMap con quel nome.

Le funzioni non fanno rete: ricevono il testo XML del WFS e il JSON di Overpass (le chiamate, con limiti e tetti, sono in
`fase4-server/servizio/luogo.py`). Geometria in Python puro (niente shapely: la fase 7 resta leggera), in metri su un piano
locale (errore trascurabile alla scala di una via).
"""
from __future__ import annotations

import math
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from .anncsu import Indirizzario, Via, _punteggio, normalizza, scomponi_via
from .zornade import da_riferimento

URL_WFS = "https://wfs.cartografia.agenziaentrate.gov.it/inspire/wfs/owfs01.php"
ATTRIBUZIONE_CATASTO = "Agenzia delle Entrate – Cartografia catastale (CC BY 4.0)"
ATTRIBUZIONE_OSM = "© OpenStreetMap contributors (ODbL 1.0)"
ATTRIBUZIONE_ANNCSU = "ANNCSU – Agenzia delle Entrate e ISTAT (CC BY 4.0)"
RAGGIO_M = 15          # punto sulla strada: particella edificata più vicina entro questa distanza
COMPLESSO_M = 600      # altri accessi dello stesso civico considerati (particella più grande del civico)
MAX_ACCESSI = 16       # accessi dello stesso civico considerati al più
MARGINE_ACCESSI_M = 20 # margine del riquadro unico attorno agli accessi
LATO_MAX_M = 640       # riquadro unico al più così (600 m + margini); oltre, una richiesta per accesso
PARALLELE = 4          # richieste per accesso insieme, al più
COUNT_RIQUADRO = 500   # particelle chieste al WFS nel riquadro unico
GRUPPO_M = 1000        # tratti con lo stesso nome più lontani di così: vie diverse (frazioni)
GRUPPO_CIVICI_M = 1500 # come sopra, per i soli civici ANNCSU (più radi delle linee)
MAX_SCELTE = 6
# strade vere (non sentieri, piste ciclabili, marciapiedi: «Percorso ciclopedonale Sant'Andrea delle Fratte» non è una via)
STRADE = ("motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|pedestrian|service|track|road")
LUOGHI = "suburb|quarter|neighbourhood|hamlet|village|locality|isolated_dwelling|town"


# ---------------------------------------------------------------------------------------------- geometria piana
def _scala(lat0: float) -> tuple[float, float]:
    """Metri per grado di longitudine e di latitudine intorno a lat0."""
    return 111_320.0 * math.cos(math.radians(lat0)), 110_574.0


def _area_anello(a: list[tuple[float, float]]) -> float:
    return 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(a, a[1:] + a[:1]))


def _dentro_anello(a: list[tuple[float, float]], x: float, y: float) -> bool:
    d = False
    for (x0, y0), (x1, y1) in zip(a, a[1:] + a[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            d = not d
    return d


def _dist_segmento(px, py, x0, y0, x1, y1) -> float:
    dx, dy = x1 - x0, y1 - y0
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / l2))
    return math.hypot(px - x0 - t * dx, py - y0 - t * dy)


@dataclass
class Particella:
    riferimento: str                     # A944_019000.170 (riferimento catastale nazionale)
    poligoni: list = field(default_factory=list)   # [(esterno, [buchi])], anelli di (lon, lat)

    @property
    def parti(self) -> dict:
        return da_riferimento(self.riferimento)

    @property
    def mappale(self) -> str:
        return self.riferimento.rsplit(".", 1)[-1]

    @property
    def strada(self) -> bool:
        """Particelle che non sono immobili: strade e acque (STRADA002, ACQUA001…)."""
        return bool(re.match(r"^(STRADA|ACQU)", self.mappale, re.IGNORECASE))

    def riquadro(self) -> list[float]:
        xs = [x for e, _ in self.poligoni for x, _ in e]
        ys = [y for e, _ in self.poligoni for _, y in e]
        return [min(xs), min(ys), max(xs), max(ys)]

    def contiene(self, lon: float, lat: float) -> bool:
        return any(_dentro_anello(e, lon, lat) and not any(_dentro_anello(b, lon, lat) for b in buchi)
                   for e, buchi in self.poligoni)

    def distanza_m(self, lon: float, lat: float) -> float:
        if self.contiene(lon, lat):
            return 0.0
        kx, ky = _scala(lat)
        d = math.inf
        for e, buchi in self.poligoni:
            for a in [e, *buchi]:
                for (x0, y0), (x1, y1) in zip(a, a[1:] + a[:1]):
                    d = min(d, _dist_segmento(lon * kx, lat * ky, x0 * kx, y0 * ky, x1 * kx, y1 * ky))
        return d

    def area_m2(self) -> float:
        if not self.poligoni:
            return 0.0
        kx, ky = _scala(self.poligoni[0][0][0][1])
        return sum(abs(_area_anello(e)) - sum(abs(_area_anello(b)) for b in buchi)
                   for e, buchi in self.poligoni) * kx * ky

    def punto_interno(self) -> tuple[float, float]:
        """Baricentro del poligono più grande se cade dentro la particella; altrimenti (particelle a L, a C, ad anello) il
        centro del tratto interno più largo su alcune orizzontali vicine al baricentro: sempre un punto della particella."""
        e, buchi = max(self.poligoni, key=lambda p: abs(_area_anello(p[0])))
        a = _area_anello(e)
        if abs(a) < 1e-18:
            return e[0]
        cx = sum((x0 + x1) * (x0 * y1 - x1 * y0) for (x0, y0), (x1, y1) in zip(e, e[1:] + e[:1])) / (6 * a)
        cy = sum((y0 + y1) * (x0 * y1 - x1 * y0) for (x0, y0), (x1, y1) in zip(e, e[1:] + e[:1])) / (6 * a)
        if self.contiene(cx, cy):
            return cx, cy
        y0, y1 = min(y for _, y in e), max(y for _, y in e)
        migliore, largo = None, -1.0
        for f in (0.5, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8, 0.1, 0.9):
            y = y0 + (y1 - y0) * f + 1e-12
            xs = sorted(xa + (y - ya) * (xb - xa) / (yb - ya)
                        for anello in [e, *buchi] for (xa, ya), (xb, yb) in zip(anello, anello[1:] + anello[:1])
                        if (ya > y) != (yb > y))
            for xa, xb in zip(xs[::2], xs[1::2]):
                peso = (xb - xa) * (1 - abs(f - 0.5))          # a parità di larghezza, più vicino al centro
                if peso > largo:
                    largo, migliore = peso, ((xa + xb) / 2, y)
        return migliore or (cx, cy)


def leggi_wfs(xml: str | bytes) -> list[Particella]:
    """Particelle di una risposta GetFeature del WFS catastale (GML 3.2, EPSG:6706: coppie «lat lon»)."""
    t = xml.decode("utf-8", "replace") if isinstance(xml, bytes) else xml
    out = []
    for m in re.finditer(r"<CP:CadastralParcel\b[^>]*>(.*?)</CP:CadastralParcel>", t, re.S):
        b = m.group(1)
        rif = re.search(r"<CP:NATIONALCADASTRALREFERENCE>([^<]*)<", b)
        if not rif:
            continue
        poligoni = []
        for pol in re.findall(r"<gml:Polygon\b.*?</gml:Polygon>", b, re.S):
            anelli = []
            for parte, lista in re.findall(r"<gml:(exterior|interior)>.*?<gml:posList[^>]*>([^<]*)</gml:posList>", pol, re.S):
                v = [float(x) for x in lista.split()]
                anello = [(v[i + 1], v[i]) for i in range(0, len(v) - 1, 2)]
                if len(anello) > 1 and anello[0] == anello[-1]:
                    anello = anello[:-1]
                if len(anello) >= 3:
                    anelli.append((parte, anello))
            esterni = [a for p, a in anelli if p == "exterior"]
            if esterni:
                poligoni.append((esterni[0], [a for p, a in anelli if p == "interior"]))
        if poligoni:
            out.append(Particella(rif.group(1).strip(), poligoni))
    return out


def riquadro_intorno(lat: float, lon: float, metri: float) -> tuple[float, float, float, float]:
    """(sud, ovest, nord, est) di un quadrato di lato 2×metri: l'ordine del parametro BBOX del WFS in EPSG:6706."""
    kx, ky = _scala(lat)
    return lat - metri / ky, lon - metri / kx, lat + metri / ky, lon + metri / kx


def parametri_wfs(lat: float, lon: float, metri: float = RAGGIO_M) -> dict:
    s, o, n, e = riquadro_intorno(lat, lon, metri)
    return {"SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature", "TYPENAMES": "CP:CadastralParcel",
            "BBOX": f"{s:.6f},{o:.6f},{n:.6f},{e:.6f}", "COUNT": "60"}


def parametri_wfs_riquadro(s: float, o: float, n: float, e: float, count: int = COUNT_RIQUADRO) -> dict:
    return {"SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature", "TYPENAMES": "CP:CadastralParcel",
            "BBOX": f"{s:.6f},{o:.6f},{n:.6f},{e:.6f}", "COUNT": str(count)}


def completo(xml: str | bytes | None) -> bool:
    """Risposta GetFeature valida e con tutte le particelle (numberMatched ≤ numberReturned): il WFS dell'Agenzia risponde a
    volte «Richiesta non valida» (ServiceExceptionReport), e con COUNT tronca."""
    if not xml:
        return False
    t = xml.decode("utf-8", "replace") if isinstance(xml, bytes) else xml
    if "FeatureCollection" not in t[:2000]:
        return False
    m = re.search(r'numberMatched="(\d+)"\s+numberReturned="(\d+)"', t[:3000])
    return not m or int(m.group(1)) <= int(m.group(2))


def particelle_degli_accessi(punti: list[tuple[float, float]], wfs, preferita: dict | None = None,
                             margine_m: float = MARGINE_ACCESSI_M, lato_max_m: float = LATO_MAX_M,
                             parallele: int = PARALLELE) -> tuple[dict, str, int]:
    """Particella di ogni accesso (lon, lat): {(lon, lat): (Particella, distanza) o None}, il modo usato («riquadro» o
    «per_accesso») e quante richieste sono fallite. Una sola richiesta
    al WFS con il riquadro degli accessi più margine_m (assegnazione in locale); se il riquadro supera lato_max_m o la
    risposta non è valida o completa, una richiesta per accesso, al più `parallele` insieme. Il primo punto è l'accesso
    cercato: per lui vale anche la particella preferita (Zornade)."""
    punti = list(dict.fromkeys(punti))
    lat0 = sum(y for _, y in punti) / len(punti)
    kx, ky = _scala(lat0)
    o, s = min(x for x, _ in punti) - margine_m / kx, min(y for _, y in punti) - margine_m / ky
    e, n = max(x for x, _ in punti) + margine_m / kx, max(y for _, y in punti) + margine_m / ky

    def assegna(particelle, x, y, i):
        q, d = scegli_particella(particelle, y, x, preferita if i == 0 else None)
        return (q, d) if q is not None else None
    if (e - o) * kx <= lato_max_m and (n - s) * ky <= lato_max_m:
        for _ in range(2):          # il WFS dell'Agenzia rifiuta a volte («Richiesta non valida») e poi risponde: un secondo tentativo
            try:
                xml = wfs(parametri_wfs_riquadro(s, o, n, e))
            except Exception:   # noqa: BLE001
                xml = None
            if completo(xml):
                particelle = leggi_wfs(xml)
                return {pt: assegna(particelle, *pt, i) for i, pt in enumerate(punti)}, "riquadro", 0

    def uno(ip):
        i, (x, y) = ip
        try:
            xml = wfs(parametri_wfs(y, x))
        except Exception:   # noqa: BLE001
            xml = None
        if not completo(xml):
            return "errore"
        return assegna(leggi_wfs(xml), x, y, i)
    with ThreadPoolExecutor(max_workers=max(1, parallele)) as ex:
        esiti = list(ex.map(uno, enumerate(punti)))
    errori = sum(v == "errore" for v in esiti)
    return {pt: (None if v == "errore" else v) for pt, v in zip(punti, esiti)}, "per_accesso", errori


def _stessa(p: Particella, belfiore, foglio, mappale) -> bool:
    if not mappale:
        return False
    r = p.parti
    return (str(r.get("mappale", p.mappale)) == str(mappale).strip()
            and (not foglio or str(r.get("foglio", "")) == str(foglio).strip().lstrip("0"))
            and (not belfiore or r.get("belfiore", "") == str(belfiore).strip()))


def scegli_particella(particelle: list[Particella], lat: float, lon: float, preferita: dict | None = None,
                      raggio_m: float = RAGGIO_M) -> tuple[Particella | None, float]:
    """La particella (non strada) che contiene il punto; altrimenti quella scelta da Zornade (`preferita`: belfiore, foglio,
    mappale) se è entro il raggio; altrimenti la più vicina entro il raggio. Restituisce anche la distanza in metri."""
    edificate = [p for p in particelle if not p.strada]
    for p in edificate:
        if p.contiene(lon, lat):
            return p, 0.0
    vicine = sorted(((p.distanza_m(lon, lat), i, p) for i, p in enumerate(edificate)))
    vicine = [(d, p) for d, _, p in vicine if d <= raggio_m]
    if preferita:
        for d, p in vicine:
            if _stessa(p, preferita.get("belfiore"), preferita.get("foglio"), preferita.get("mappale")):
                return p, d
    return (vicine[0][1], vicine[0][0]) if vicine else (None, 0.0)


def unisci_riquadri(*r) -> list[float] | None:
    r = [x for x in r if x]
    if not r:
        return None
    return [min(x[0] for x in r), min(x[1] for x in r), max(x[2] for x in r), max(x[3] for x in r)]


def vicini_entro(punti: list[tuple[float, float]], lat: float, lon: float,
                 massimo_m: float = COMPLESSO_M) -> list[tuple[float, float]]:
    """Accessi (lon, lat) dello stesso civico entro massimo_m dal punto, il più vicino prima, senza doppioni."""
    kx, ky = _scala(lat)
    d = sorted({(math.hypot((x - lon) * kx, (y - lat) * ky), x, y) for x, y in punti})
    return [(x, y) for m, x, y in d if m <= massimo_m]


def esito_particella(p: Particella, distanza_m: float) -> dict:
    lon, lat = p.punto_interno()
    r = p.parti
    return {"luogo_tipo": "particella", "luogo_lat": round(lat, 7), "luogo_lon": round(lon, 7),
            "luogo_riquadro": [round(v, 7) for v in p.riquadro()],
            "luogo_fonte": ATTRIBUZIONE_CATASTO,
            "particella_ade": {"riferimento": p.riferimento, "foglio": r.get("foglio"), "mappale": p.mappale,
                               "belfiore": r.get("belfiore"), "area_m2": round(p.area_m2()),
                               "riquadro": [round(v, 7) for v in p.riquadro()], "distanza_m": round(distanza_m, 1)}}


# ---------------------------------------------------------------------------------------------- linee e metà via
def _lunghezza(linea: list[tuple[float, float]], kx: float, ky: float) -> float:
    return sum(math.hypot((x1 - x0) * kx, (y1 - y0) * ky) for (x0, y0), (x1, y1) in zip(linea, linea[1:]))


def _punto_a(linea, s, kx, ky) -> tuple[float, float]:
    """Punto a distanza s (metri) dall'inizio della linea."""
    for (x0, y0), (x1, y1) in zip(linea, linea[1:]):
        l = math.hypot((x1 - x0) * kx, (y1 - y0) * ky)
        if s <= l and l > 0:
            t = s / l
            return x0 + t * (x1 - x0), y0 + t * (y1 - y0)
        s -= l
    return linea[-1]


def catene(linee: list[list[tuple[float, float]]]) -> list[list[tuple[float, float]]]:
    """Unisce le linee che si toccano in un estremo condiviso da due sole linee (i tratti in cui OSM spezza una via)."""
    linee = [list(l) for l in linee if len(l) >= 2]
    k = lambda p: (round(p[0], 7), round(p[1], 7))   # noqa: E731
    cambiato = True
    while cambiato:
        cambiato = False
        conta: dict = {}
        for l in linee:
            for p in (l[0], l[-1]):
                conta[k(p)] = conta.get(k(p), 0) + 1
        for i, a in enumerate(linee):
            for j in range(i + 1, len(linee)):
                b = linee[j]
                if a is b or a[0] == a[-1] or b[0] == b[-1]:
                    continue
                for pa, pb in ((a[-1], b[0]), (a[-1], b[-1]), (a[0], b[0]), (a[0], b[-1])):
                    if k(pa) == k(pb) and conta.get(k(pa)) == 2:
                        if pa is a[0]:
                            a.reverse()
                        nuova = a + (b[1:] if k(a[-1]) == k(b[0]) else b[::-1][1:])
                        linee[i] = nuova
                        del linee[j]
                        cambiato = True
                        break
                if cambiato:
                    break
            if cambiato:
                break
    return linee


def meta_via(linee: list[list[tuple[float, float]]]) -> tuple[float, float, float]:
    """(lon, lat, lunghezza in metri) del punto a metà della via. Se i tratti formano (quasi) una catena sola, metà della
    catena; altrimenti (diramazioni, carreggiate separate) il punto delle linee che lascia metà della lunghezza da ciascuna
    parte lungo l'asse principale della via."""
    linee = [l for l in linee if len(l) >= 2]
    lat0 = sum(y for l in linee for _, y in l) / sum(len(l) for l in linee)
    kx, ky = _scala(lat0)
    tot = sum(_lunghezza(l, kx, ky) for l in linee)
    cat = sorted(catene(linee), key=lambda l: _lunghezza(l, kx, ky), reverse=True)
    lc = _lunghezza(cat[0], kx, ky)
    if lc >= 0.8 * tot:
        x, y = _punto_a(cat[0], lc / 2, kx, ky)
        return x, y, tot
    # campioni ogni ~10 m con il loro peso (lunghezza), proiettati sull'asse principale
    campioni = []
    for l in linee:
        for (x0, y0), (x1, y1) in zip(l, l[1:]):
            s = math.hypot((x1 - x0) * kx, (y1 - y0) * ky)
            n = max(1, int(s // 10))
            for i in range(n):
                t = (i + 0.5) / n
                campioni.append((x0 + t * (x1 - x0), y0 + t * (y1 - y0), s / n))
    mx = sum(x * w for x, _, w in campioni) / tot
    my = sum(y * w for _, y, w in campioni) / tot
    sxx = sum(w * ((x - mx) * kx) ** 2 for x, _, w in campioni)
    syy = sum(w * ((y - my) * ky) ** 2 for _, y, w in campioni)
    sxy = sum(w * (x - mx) * kx * (y - my) * ky for x, y, w in campioni)
    ang = 0.5 * math.atan2(2 * sxy, sxx - syy)
    ux, uy = math.cos(ang), math.sin(ang)
    proiettati = sorted(campioni, key=lambda c: ((c[0] - mx) * kx) * ux + ((c[1] - my) * ky) * uy)
    s = 0.0
    for x, y, w in proiettati:
        s += w
        if s >= tot / 2:
            return x, y, tot
    x, y, _ = proiettati[-1]
    return x, y, tot


def meta_civici(punti: list[tuple[float, float]]) -> tuple[float, float, float]:
    """Senza linee: i civici ordinati lungo l'asse principale, il punto a metà della spezzata che li unisce; la lunghezza
    è l'estensione dei civici lungo l'asse."""
    if len(punti) == 1:
        return punti[0][0], punti[0][1], 0.0
    lat0 = sum(y for _, y in punti) / len(punti)
    kx, ky = _scala(lat0)
    mx, my = sum(x for x, _ in punti) / len(punti), lat0
    sxx = sum(((x - mx) * kx) ** 2 for x, _ in punti)
    syy = sum(((y - my) * ky) ** 2 for _, y in punti)
    sxy = sum((x - mx) * kx * (y - my) * ky for x, y in punti)
    ang = 0.5 * math.atan2(2 * sxy, sxx - syy)
    ux, uy = math.cos(ang), math.sin(ang)
    proiezione = lambda p: ((p[0] - mx) * kx) * ux + ((p[1] - my) * ky) * uy   # noqa: E731
    linea = sorted(punti, key=proiezione)
    x, y = _punto_a(linea, _lunghezza(linea, kx, ky) / 2, kx, ky)
    # lunghezza: estensione lungo l'asse (la spezzata dei civici va a zig-zag tra i due lati della via)
    return x, y, proiezione(linea[-1]) - proiezione(linea[0])


def gruppi(oggetti: list[list[tuple[float, float]]], distanza_m: float) -> list[list[int]]:
    """Indici delle linee (o dei punti, come linee di un punto) raggruppati per vicinanza (collegamento singolo)."""
    if not oggetti:
        return []
    lat0 = sum(y for o in oggetti for _, y in o) / sum(len(o) for o in oggetti)
    kx, ky = _scala(lat0)
    pts = [[(x * kx, y * ky) for x, y in o] for o in oggetti]
    box = [(min(x for x, _ in p), min(y for _, y in p), max(x for x, _ in p), max(y for _, y in p)) for p in pts]

    def vicini(i, j):
        a, b = box[i], box[j]
        if a[0] - b[2] > distanza_m or b[0] - a[2] > distanza_m or a[1] - b[3] > distanza_m or b[1] - a[3] > distanza_m:
            return False
        # vertici a meno della soglia, oppure un vertice vicino a un segmento dell'altra linea
        for p, q in ((pts[i], pts[j]), (pts[j], pts[i])):
            for x, y in p:
                if len(q) == 1:
                    if math.hypot(x - q[0][0], y - q[0][1]) <= distanza_m:
                        return True
                    continue
                for (x0, y0), (x1, y1) in zip(q, q[1:]):
                    if _dist_segmento(x, y, x0, y0, x1, y1) <= distanza_m:
                        return True
        return False

    padre = list(range(len(oggetti)))

    def radice(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i
    if all(len(p) == 1 for p in pts):
        # (19/11/2026, Venezia «piazza San Marco»: il sestiere ha migliaia di civici con un solo odonimo) solo punti: griglia
        # di lato distanza/√2, i punti di una cella sono tutti entro la distanza (uniti senza confronti), poi si confrontano
        # solo le celle entro due passi; prima tutte le coppie, n² (6.000 civici: 4 s per via, più sul server)
        lato = max(float(distanza_m), 1.0) / math.sqrt(2)
        celle: dict = {}
        for i, p in enumerate(pts):
            celle.setdefault((int(math.floor(p[0][0] / lato)), int(math.floor(p[0][1] / lato))), []).append(i)
        for dentro in celle.values():
            for i in dentro[1:]:
                padre[radice(i)] = radice(dentro[0])
        chiavi = list(celle)
        for (cx, cy) in chiavi:
            a = celle[(cx, cy)]
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if (dx, dy) <= (0, 0):
                        continue
                    b = celle.get((cx + dx, cy + dy))
                    if not b or radice(a[0]) == radice(b[0]):
                        continue
                    if any(math.hypot(pts[i][0][0] - pts[j][0][0], pts[i][0][1] - pts[j][0][1]) <= distanza_m for i in a for j in b):
                        padre[radice(a[0])] = radice(b[0])
    else:
        for i in range(len(oggetti)):
            for j in range(i + 1, len(oggetti)):
                if radice(i) != radice(j) and vicini(i, j):
                    padre[radice(i)] = radice(j)
    out: dict = {}
    for i in range(len(oggetti)):
        out.setdefault(radice(i), []).append(i)
    return sorted(out.values(), key=lambda g: g[0])


def _riquadro_punti(pts) -> list[float]:
    return [min(x for x, _ in pts), min(y for _, y in pts), max(x for x, _ in pts), max(y for _, y in pts)]


# ---------------------------------------------------------------------------------------------- OpenStreetMap
def parole_chiave(via: str, massimo: int = 3) -> list[str]:
    """Le parole più lunghe del nome (senza tipo di strada, articoli e numeri): filtrano le strade chieste a Overpass."""
    v = scomponi_via(via)
    parole = sorted({p for p in v.parole if p.isalpha() and len(p) >= 3}, key=lambda p: (-len(p), p))
    return parole[:massimo]


def _regex_parola(parola: str) -> str:
    """Espressione per Overpass che trova la parola anche con accenti e apostrofi tipografici nel nome OSM."""
    varianti = {"A": "[aàáâ]", "E": "[eèéê]", "I": "[iìíî]", "O": "[oòóô]", "U": "[uùúû]"}
    return "".join(varianti.get(c, c.lower()) for c in parola.upper() if c.isalnum())


def query_overpass(istat: str, via: str) -> str | None:
    """Strade (e località) del comune con una delle parole chiave nel nome; None se il nome non ha parole utili."""
    parole = parole_chiave(via)
    if not parole or not re.fullmatch(r"\d{6}", str(istat or "")):
        return None
    rx = "|".join(_regex_parola(p) for p in parole)
    return (f'[out:json][timeout:25];area["ref:ISTAT"="{istat}"]["boundary"="administrative"]->.a;'
            f'(way(area.a)["highway"~"^({STRADE})(_link)?$"]["name"~"{rx}",i];'
            f'node(area.a)["place"~"^({LUOGHI})$"]["name"~"{rx}",i];);out geom;')


def _punteggio_largo(cercata: Via, nome: str) -> float:
    """Punteggio ANNCSU (≥ 0,8 via riconosciuta, ≥ 0,72 da verificare); se è 0 ma il nome ha in comune almeno una parola
    significativa, un punteggio basso (≤ 0,6) che serve solo all'elenco delle vie simili."""
    k = scomponi_via(nome)
    s = _punteggio(cercata, k)
    if s or not cercata.parole:
        return s
    comuni = set(cercata.parole) & set(k.parole)
    comuni = {p for p in comuni if p.isalpha() and len(p) >= 3}
    return 0.6 * len(comuni) / max(len(set(cercata.parole)), len(set(k.parole))) if comuni else 0.0


def candidate_osm(dati: dict, via: str) -> list[dict]:
    """Vie di OSM (per nome e per gruppo di tratti vicini) e località compatibili con il testo cercato."""
    cercata = scomponi_via(via)
    per_nome: dict = {}          # nome normalizzato → (nome come in OSM, linee): «D'Agliano» e «d'Agliano» sono la stessa via
    luoghi = []
    for e in (dati or {}).get("elements", []):
        nome = (e.get("tags") or {}).get("name", "")
        if not nome:
            continue
        if e.get("type") == "way" and len(e.get("geometry") or []) >= 2:
            per_nome.setdefault(normalizza(nome), (nome, []))[1].append(
                [(float(g["lon"]), float(g["lat"])) for g in e["geometry"]])
        elif e.get("type") == "node" and "lat" in e:
            luoghi.append((nome, float(e["lon"]), float(e["lat"]), (e.get("tags") or {}).get("place", "")))
    out = []
    for nome, linee in per_nome.values():
        s = _punteggio_largo(cercata, nome)
        if s <= 0:
            continue
        gr = gruppi(linee, GRUPPO_M)
        for n, g in enumerate(gr, 1):
            tratti = [linee[i] for i in g]
            x, y, l = meta_via(tratti)
            out.append({"nome": nome, "tipo": "via", "lat": round(y, 7), "lon": round(x, 7),
                        "riquadro": [round(v, 7) for v in _riquadro_punti([p for t in tratti for p in t])],
                        "lunghezza_m": round(l), "fonte": ATTRIBUZIONE_OSM, "punteggio": round(s, 3),
                        "tratto": n if len(gr) > 1 else None, "civici": None})
    # località (frazioni): solo se il nome corrisponde bene a tutto il testo cercato senza il tipo di strada
    senza_dug = Via("", cercata.parole, " ".join(cercata.parole), cercata.iniziali)
    for nome, x, y, tipo in luoghi:
        k = scomponi_via(nome)
        s = _punteggio(senza_dug, Via("", k.parole, k.testo, k.iniziali))
        if s >= 0.8:
            out.append({"nome": nome, "tipo": "località", "lat": round(y, 7), "lon": round(x, 7), "riquadro": None,
                        "lunghezza_m": None, "fonte": ATTRIBUZIONE_OSM, "punteggio": round(min(s, 0.79), 3),
                        "tratto": None, "civici": None, "luogo": tipo})
    return out


def candidate_anncsu(idx: Indirizzario, istat: str, belfiore: str | None, via: str) -> list[dict]:
    """Vie ANNCSU compatibili (anche solo in parte) con il testo: punto a metà della spezzata dei civici, per gruppo."""
    out = []
    for s, odonimo, punti in idx.vie_simili(istat, belfiore, via, _punteggio_largo):
        gr = gruppi([[p] for p in punti], GRUPPO_CIVICI_M)
        for n, g in enumerate(gr, 1):
            pts = [punti[i] for i in g]
            x, y, l = meta_civici(pts)
            out.append({"nome": odonimo, "tipo": "via", "lat": round(y, 7), "lon": round(x, 7),
                        "riquadro": [round(v, 7) for v in _riquadro_punti(pts)], "lunghezza_m": round(l),
                        "fonte": ATTRIBUZIONE_ANNCSU, "punteggio": round(s, 3), "tratto": n if len(gr) > 1 else None,
                        "civici": len(pts)})
    return out


def _stessa_via(a: str, b: str) -> bool:
    va, vb = scomponi_via(a), scomponi_via(b)
    return _punteggio(va, vb) >= 0.8 and _punteggio(vb, va) >= 0.8


def _dentro(r: list[float] | None, lon: float, lat: float, margine: float = 0.002) -> bool:
    return bool(r) and r[0] - margine <= lon <= r[2] + margine and r[1] - margine <= lat <= r[3] + margine


def unisci_candidate(osm: list[dict], anncsu: list[dict]) -> list[dict]:
    """Le vie OSM hanno la geometria vera: a una via ANNCSU con lo stesso nome nello stesso posto si aggiunge solo il numero
    dei civici. Le vie ANNCSU senza corrispondente in OSM restano (punto dai civici). Ordine: punteggio, poi lunghezza."""
    out = [dict(c) for c in osm]
    for a in anncsu:
        gemella = next((o for o in out if o["tipo"] == "via" and _stessa_via(a["nome"], o["nome"])
                        and _dentro(o["riquadro"], a["lon"], a["lat"])), None)
        if gemella is not None:
            gemella["civici"] = (gemella["civici"] or 0) + a["civici"]
            gemella["punteggio"] = max(gemella["punteggio"], a["punteggio"])
            gemella["nome_anncsu"] = a["nome"]
        else:
            out.append(dict(a))
    out.sort(key=lambda c: (-c["punteggio"], -(c["lunghezza_m"] or 0)))
    return out


def decidi(candidate: list[dict], riconosciuta: float = 0.8) -> tuple[dict | None, list[dict], bool]:
    """(via scelta o None, elenco da mostrare, si deve far scegliere?). Una sola via riconosciuta (o una nettamente
    migliore): si va lì e le altre sono «altre vie simili». Più vie riconosciute alla pari (stesso nome in frazioni diverse)
    o nessuna riconosciuta ma qualcuna simile: si fa scegliere."""
    elenco = candidate[:MAX_SCELTE]
    buone = [c for c in candidate if c["punteggio"] >= riconosciuta]
    if len(buone) == 1:
        return buone[0], [c for c in elenco if c is not buone[0]], False
    if len(buone) > 1:
        if buone[0]["punteggio"] - buone[1]["punteggio"] >= 0.1:
            return buone[0], [c for c in elenco if c is not buone[0]], False
        return None, elenco, True
    return None, elenco, bool(elenco)


def etichetta(c: dict) -> str:
    """Testo di una scelta: «Via Coriano (6,1 km, 342 civici)», «Sant'Andrea delle Fratte (località)»."""
    if c.get("tipo") == "località":
        return f"{c['nome']} (località)"
    dett = []
    if c.get("tratto"):
        dett.append(f"tratto {c['tratto']}")
    if c.get("lunghezza_m"):
        l = c["lunghezza_m"]
        dett.append(f"{l / 1000:.1f} km".replace(".", ",") if l >= 1000 else f"{l} m")
    if c.get("civici"):
        dett.append(f"{c['civici']} civici")
    return f"{c['nome']}" + (f" ({', '.join(dett)})" if dett else "")


def esito_via(scelta: dict | None, elenco: list[dict], scegli: bool) -> dict:
    for c in elenco + ([scelta] if scelta else []):
        c["etichetta"] = etichetta(c)
    out = {"vie_candidate": elenco, "scegli_via": scegli}
    if scelta:
        out.update({"luogo_tipo": scelta["tipo"], "luogo_lat": scelta["lat"], "luogo_lon": scelta["lon"],
                    "luogo_riquadro": scelta["riquadro"], "luogo_fonte": scelta["fonte"], "via_scelta": scelta})
    return out


# ---------------------------------------------------------------------------------------------- una ricerca
def _via_non_riconosciuta(riga: dict) -> bool:
    """Il punto con il civico viene da una via che ANNCSU non conosce con quel nome (Zornade), o che ha solo interpretato."""
    nota = str(riga.get("nota") or "")
    return riga.get("fonte_punto") != "ANNCSU" or "interpretata come" in nota or "più vie possibili" in nota


def arricchisci(riga: dict, istat: str | None = None, belfiore: str | None = None, idx: Indirizzario | None = None,
                wfs=None, overpass=None) -> dict:
    """Campi da aggiungere alla riga di `patrimonio.geolocalizza` per la ricerca di un luogo (una riga, pagine di mappa).

    istat, belfiore: del comune scritto (se riconosciuto). wfs(parametri) → testo XML della cartografia catastale;
    overpass(query) → JSON di Overpass. Tutte e due possono mancare, restituire None o sollevare un'eccezione: la riga resta
    com'era, con un avviso. Campi aggiunti (nessuno tolto): luogo_tipo («particella», «via», «località» o None), luogo_lat,
    luogo_lon (dove mettere il segnaposto), luogo_riquadro [ovest, sud, est, nord] (da inquadrare), luogo_fonte, luogo_avviso,
    luogo_regola («particella_piu_grande_del_civico», «particella_del_civico», «particella_dell_accesso» con l'esponente,
    «particella_del_punto» per foglio e particella, coordinate o punto di Zornade, «meta_della_via», «località»),
    particella_ade, vie_candidate, scegli_via, via_scelta."""
    from .patrimonio import _via_civico          # qui: patrimonio non importa luogo
    out: dict = {"luogo_regola": None, "luogo_tipo": None, "luogo_lat": None, "luogo_lon": None, "luogo_riquadro": None, "luogo_fonte": None,
                 "luogo_avviso": "", "particella_ade": None, "vie_candidate": [], "scegli_via": False, "via_scelta": None}
    avvisi = []
    istat = istat or riga.get("istat")
    belfiore = belfiore or riga.get("belfiore")
    metodo = riga.get("metodo")
    via, civ = _via_civico(riga) if metodo == "indirizzo" else ("", "")

    def vie() -> tuple[dict | None, list[dict], bool]:
        osm = []
        q = query_overpass(istat, via) if overpass else None
        if q:
            try:
                d = overpass(q)
                osm = candidate_osm(d, via) if d else []
                if d is None:
                    avvisi.append("strade di OpenStreetMap non disponibili ora")
            except Exception:   # noqa: BLE001 - la ricerca resta com'era
                avvisi.append("strade di OpenStreetMap non disponibili ora")
        ann = candidate_anncsu(idx, istat, belfiore, via) if idx is not None and istat else []
        return decidi(unisci_candidate(osm, ann))

    # via senza civico: metà della via (o l'elenco da cui scegliere)
    if metodo == "indirizzo" and not civ:
        scelta, elenco, scegli = vie()
        out.update(esito_via(scelta, elenco, scegli))
        if scelta:
            out["luogo_regola"] = "meta_della_via" if scelta["tipo"] == "via" else "località"
        if not scelta and not scegli:
            avvisi.append("via non trovata nelle strade di OpenStreetMap né nei civici ANNCSU: punto dell'indirizzo")
        out["luogo_avviso"] = "; ".join(avvisi)
        return out

    lat, lon = riga.get("lat"), riga.get("lon")
    try:
        lat, lon = float(lat), float(lon)
        if not (35 < lat < 48 and 6 < lon < 19.5):
            raise ValueError
    except (TypeError, ValueError):
        lat = lon = None
    # civico su una via non riconosciuta: si fa scegliere se ci sono vie simili ma nessuna riconosciuta
    if metodo == "indirizzo" and _via_non_riconosciuta(riga):
        scelta, elenco, scegli = vie()
        if scelta is not None:          # la via esiste con quel nome: il punto trovato vale, le altre sono «simili»
            elenco = [c for c in elenco if c is not scelta]
            scegli = False
        out.update(esito_via(None, elenco, scegli))
        if scegli:
            out["luogo_avviso"] = "; ".join(avvisi)
            return out
    if lat is None:
        out["luogo_avviso"] = "; ".join(avvisi)
        return out
    # civico, foglio e particella o coordinate: la particella catastale nel punto
    if wfs is None:
        out["luogo_avviso"] = "; ".join(avvisi)
        return out
    guasto = []
    preferita = {"belfiore": riga.get("belfiore"), "foglio": riga.get("foglio_catasto"), "mappale": riga.get("mappale")}
    regola, accessi = "particella_del_punto", []
    # (17/11/2026, decisione di Paolo, scelta B) civico ANNCSU senza esponente con più accessi (2, 2/B … 2/O entro
    # COMPLESSO_M): la particella più grande fra quelle che li contengono (l'ospedale Infermi, non l'angolo sud)
    trovato = str(riga.get("indirizzo_trovato") or "")
    if metodo == "indirizzo" and riga.get("fonte_punto") == "ANNCSU" and " " in trovato:
        if re.search(r"[A-Za-z]", civ):
            regola = "particella_dell_accesso"
        else:
            regola = "particella_del_civico"
            if idx is not None and istat:
                odonimo, civico_trovato = trovato.rsplit(" ", 1)
                try:
                    accessi = vicini_entro(idx.accessi(istat, belfiore, odonimo, civico_trovato.split("/")[0]), lat, lon)
                except Exception:   # noqa: BLE001
                    accessi = []
    p, d, modo = None, 0.0, None
    if len(accessi) >= 2:
        punti = [(lon, lat)] + [a for a in accessi if a != (lon, lat)][:MAX_ACCESSI - 1]
        esiti, modo, errori = particelle_degli_accessi(punti, wfs, preferita)
        trovate = {v[0].riferimento: v for v in esiti.values() if v}
        if trovate:
            p, d = max(trovate.values(), key=lambda v: v[0].area_m2())
            regola = "particella_piu_grande_del_civico"
        elif errori == len(punti):
            guasto.append(1)
    else:
        try:
            xml = wfs(parametri_wfs(lat, lon))
        except Exception:   # noqa: BLE001
            xml = None
        if xml is None:
            guasto.append(1)
        else:
            p, d = scegli_particella(leggi_wfs(xml), lat, lon, preferita)
    if guasto and p is None:
        avvisi.append("cartografia catastale non disponibile ora: mappa sul punto dell'indirizzo")
    if p is None:
        if not guasto:
            avvisi.append(f"nessuna particella catastale entro {RAGGIO_M} m dal punto: mappa sul punto dell'indirizzo")
        out["luogo_avviso"] = "; ".join(avvisi)
        return out
    out.update(esito_particella(p, d))
    out["luogo_regola"] = regola
    if modo:
        out["particella_ade"].update({"accessi": len(punti), "richiesta_wfs": modo})
    out["luogo_avviso"] = "; ".join(avvisi)
    return out
