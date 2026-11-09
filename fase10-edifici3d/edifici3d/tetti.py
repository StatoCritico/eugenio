"""Forma dei tetti dei corpi: stima dal colmo del DB topografico e ipotesi automatica (08/11/2026, decisione di Paolo).

**SOSPESO NELLA VISTA dal 09/11/2026 c** (decisione di Paolo: l'ipotesi automatica «si fa ingannare da tetti complessi con
UTA e simili»: l'Ospedale Infermi di Rimini, piano, usciva a falde; le case di via Ovidio, a falde, uscivano piane). Le
pagine 3D partono con **tutti i tetti piani** e l'utente sceglie i tetti a falde con la tegola della sezione «Coperture»
(`edifici_calcoli.js`, `tettoScelto`: stessa forma, inclinazione scelta, 22° all'inizio). Questo modulo resta per i
conteggi negli archivi e come riferimento (gemello di `faldeStimate` e `tettoIpotizzato`, test di parità invariato), ma
la vista, il PNG, il report e la pagina Fotovoltaico non lo usano più.

Stesse regole e stessi numeri di `fase5-sito/sito/edifici_calcoli.js` (`faldeStimate`, `tettoIpotizzato`): un test di
parità (`tests/test_tetti.py`) li confronta in node. Serve per contare i corpi per fonte del tetto negli archivi (numeri
nei documenti) e come riferimento della regola fuori dal browser.

Tre fonti per la forma del tetto, in ordine di affidabilità:
  1. **falde misurate dal LiDAR** (pipeline notturna, `lidar/indice.json` dell'archivio: `lidar.py`, `lidar_corpi.py`);
  2. **tetto stimato dal colmo DBTR** (`colmo` > gronda + 0,3 m): capanna sul lato lungo del rettangolo minimo, padiglione
     se lato lungo / lato corto < 1,3; niente stima per i corpi con cortile o poco rettangolari (< 70 % del rettangolo);
  3. **tetto ipotizzato**: stessa forma con inclinazione **22° in pianura** (e collina) e **32° in montagna**, colmo =
     gronda + semiluce × tan(inclinazione) (semiluce = metà del lato corto del rettangolo minimo).

Pianura o montagna: **quota del terreno sotto il corpo** (DTM, `quota_terreno` dei corpi) ≥ 600 m nei comuni del Nord e
≥ 700 m al Centro, al Sud e nelle isole (soglie della definizione ISTAT della zona altimetrica di montagna). La
classificazione ISTAT dei comuni per zona altimetrica non è tra i dati del sito né tra i file aperti che ISTAT pubblica
oggi (altimetria e fasce altimetriche dei comuni, senza la zona); la quota sotto l'edificio è più vicina al tetto vero
(il paese di fondovalle di un comune montano resta in pianura/collina). Senza la quota del corpo (edifici OpenStreetMap)
vale l'altitudine del comune del DPR 412/93, Allegato A (`fase5-sito/sito/dati/dpr412.json`).

Restano **piani** i corpi plausibilmente piani: uso produttivo, commerciale o sportivo (`capannone`, `commerciale`,
`palestra`, `industriale`, dal DBTR o da OSM), tipi DBTR industriali, tettoie, hangar, serre, cabine, tribune e palazzi
dello sport, corpi con cortile, corpi oltre 1.500 m² in pianta, gronda sotto 3 m (accessori), forma poco rettangolare
(< 70 % del rettangolo minimo: più robusto del numero di lati, che nel DBTR conta anche i vertici allineati), lato corto
oltre 25 m o sotto 2 m.
"""
from __future__ import annotations

import math
import re

RAPPORTO_PADIGLIONE = 1.3
RIEMPIMENTO_MIN = 0.7
SALTO_MIN = 0.3
IPOTESI_TETTO = {"pianura": 22, "montagna": 32, "soglia_nord": 600, "soglia_centro_sud": 700,
                 "area_piano": 1500, "lato_piano": 25, "gronda_piano": 3}
USI_TETTO_PIANO = ("capannone", "commerciale", "palestra", "industriale")
TIPI_TETTO_PIANO = re.compile(r"industrial|capannone|hangar|tettoia|palazzo dello sport|tribuna|serra|impiant|cabina", re.I)
PROVINCE_NORD_NUOVE = (93, 96, 97, 98, 99, 103, 108)
GRAD = math.pi / 180


def _arr(x: float, d: int) -> float:
    """Math.round(x · 10^d) / 10^d di JavaScript (metà verso +∞, non all'intero pari)."""
    f = 10 ** d
    return math.floor(x * f + 0.5) / f


def chiudi(r):
    r = [list(p) for p in r]
    return r + [r[0]] if r and (r[0][0] != r[-1][0] or r[0][1] != r[-1][1]) else r


def area_con_segno(r) -> float:
    r = chiudi(r)
    return sum(r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1] for i in range(len(r) - 1)) / 2


def area(r) -> float:
    return abs(area_con_segno(r))


def area_corpo(ring, buchi=()) -> float:
    return max(0.0, area(ring) - sum(area(b) for b in buchi if len(b) >= 3))


def inviluppo(p):
    q = sorted((list(x) for x in p), key=lambda a: (a[0], a[1]))
    if len(q) < 3:
        return q

    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for x in q:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], x) <= 0:
            lo.pop()
        lo.append(x)
    for x in reversed(q):
        while len(hi) >= 2 and cr(hi[-2], hi[-1], x) <= 0:
            hi.pop()
        hi.append(x)
    return lo[:-1] + hi[:-1]


def rettangolo_tetto(ring):
    """Rettangolo minimo orientato (u lungo il lato lungo): dict A, u, v, s0, s1, t0, t1, La, Lb, anello; None se < 3 punti."""
    anello = chiudi(ring)[:-1]
    if len(anello) < 3:
        return None
    h = inviluppo(anello)
    m = None
    for i in range(len(h)):
        a, b = h[i], h[(i + 1) % len(h)]
        ll = math.hypot(b[0] - a[0], b[1] - a[1])
        if ll < 1e-9:
            continue
        u = [(b[0] - a[0]) / ll, (b[1] - a[1]) / ll]
        v = [-u[1], u[0]]
        s = [p[0] * u[0] + p[1] * u[1] for p in h]
        t = [p[0] * v[0] + p[1] * v[1] for p in h]
        A = (max(s) - min(s)) * (max(t) - min(t))
        if m is None or A < m["A"]:
            m = {"A": A, "u": u, "v": v, "s0": min(s), "s1": max(s), "t0": min(t), "t1": max(t)}
    if m is None:
        return None
    u, v, s0, s1, t0, t1 = m["u"], m["v"], m["s0"], m["s1"], m["t0"], m["t1"]
    if s1 - s0 < t1 - t0:
        ou = u
        u, v = v, [-ou[0], -ou[1]]
        s0, s1, t0, t1 = t0, t1, -s1, -s0
    return {"A": m["A"], "u": u, "v": v, "s0": s0, "s1": s1, "t0": t0, "t1": t1, "La": s1 - s0, "Lb": t1 - t0, "anello": anello}


def clip_convesso(poli, taglio):
    """Sutherland–Hodgman: poligono qualsiasi tagliato da un poligono convesso (come clipConvesso in JS)."""
    ccw = area_con_segno(taglio) > 0
    out = [list(p) for p in poli]
    for i in range(len(taglio)):
        if not out:
            break
        a, b = taglio[i], taglio[(i + 1) % len(taglio)]
        inp, out = out, []

        def d(p):
            return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])

        def lato(p):
            x = d(p)
            return x >= -1e-9 if ccw else x <= 1e-9
        for k in range(len(inp)):
            p, q = inp[k], inp[(k + 1) % len(inp)]
            ip, iq = lato(p), lato(q)
            if ip:
                out.append(p)
            if ip != iq:
                d1, d2 = d(p), d(q)
                t = d1 / (d1 - d2)
                out.append([p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])])
    return out if len(out) >= 3 and area(out) > 0.05 else None


# cortili veri per i tetti (09/11/2026, come cortiliDi in JS): buchi di almeno 25 m² o del 10 % della pianta; cavedi e buchi
# occupati da un corpo interno (Bagno di Romagna, foglio 54 particella 216: 8 m² in 178 m²) non rendono piano il tetto
CORTILE_MIN_M2 = 25.0
CORTILE_MIN_QUOTA = 0.10


def cortili(ring, buchi=()) -> list:
    A = area(ring)
    return [b for b in buchi if len(b) >= 3 and (area(b) >= CORTILE_MIN_M2 or area(b) >= CORTILE_MIN_QUOTA * A)]


def falde_stimate(ring, gronda: float, colmo: float | None, buchi=(), tipo_voluto: str | None = None):
    """Falde del tetto stimato da gronda e colmo (anelli in metri): {tipo, falde} o None (come faldeStimate in JS)."""
    if colmo is None or not (colmo > gronda + SALTO_MIN) or cortili(ring, buchi):
        return None
    m = rettangolo_tetto(ring)
    if not m or m["A"] < 1 or area_corpo(ring, buchi) / m["A"] < RIEMPIMENTO_MIN:
        return None
    u, v, s0, s1, t0, t1, anello = m["u"], m["v"], m["s0"], m["s1"], m["t0"], m["t1"], m["anello"]
    La, Lb = s1 - s0, t1 - t0
    semi, salto = Lb / 2, colmo - gronda
    if Lb < 2:
        return None

    def pt(s, t):
        return [s * u[0] + t * v[0], s * u[1] + t * v[1]]

    def az(d):
        return ((math.atan2(d[0], d[1]) / GRAD) + 360) % 360

    def S(p):
        return p[0] * u[0] + p[1] * u[1]

    def T(p):
        return p[0] * v[0] + p[1] * v[1]
    if tipo_voluto in ("capanna", "padiglione", "monofalda"):
        tipo = tipo_voluto
    else:
        tipo = "padiglione" if La / Lb < RAPPORTO_PADIGLIONE else "capanna"
    tm = (t0 + t1) / 2
    reg = []
    if tipo == "monofalda":
        verso = v if v[1] <= 0 else [-v[0], -v[1]]
        basso = t1 if verso is v else t0
        reg.append(([pt(s0, t0), pt(s1, t0), pt(s1, t1), pt(s0, t1)], verso, lambda p: abs(basso - T(p)), Lb))
    elif tipo == "capanna":
        reg.append(([pt(s0, t0), pt(s1, t0), pt(s1, tm), pt(s0, tm)], [-v[0], -v[1]], lambda p: T(p) - t0, semi))
        reg.append(([pt(s0, tm), pt(s1, tm), pt(s1, t1), pt(s0, t1)], v, lambda p: t1 - T(p), semi))
    else:
        a0, a1 = s0 + semi, s1 - semi
        reg.append(([pt(s0, t0), pt(s1, t0), pt(a1, tm), pt(a0, tm)], [-v[0], -v[1]], lambda p: T(p) - t0, semi))
        reg.append(([pt(a0, tm), pt(a1, tm), pt(s1, t1), pt(s0, t1)], v, lambda p: t1 - T(p), semi))
        reg.append(([pt(s0, t0), pt(a0, tm), pt(s0, t1)], [-u[0], -u[1]], lambda p: S(p) - s0, semi))
        reg.append(([pt(s1, t0), pt(s1, t1), pt(a1, tm)], u, lambda p: s1 - S(p), semi))
    falde = []
    for k, (poli, d, dg, largo) in enumerate(reg):
        pezzo = clip_convesso(anello, poli)
        if not pezzo:
            continue
        tanp = salto / largo
        dist = [dg(p) for p in pezzo]
        ap = area(pezzo)
        pend = math.atan(tanp) / GRAD
        falde.append({"id": f"S{k + 1}", "ring": chiudi(pezzo), "pendenza": _arr(pend, 1), "orientamento": _arr(az(d), 0),
                      "superficie": _arr(ap / math.cos(pend * GRAD), 1), "area_pianta": _arr(ap, 1),
                      "alto": _arr(gronda + min(salto, max(dist) * tanp), 2),
                      "basso": _arr(gronda + max(0, min(dist)) * tanp, 2)})
    return {"tipo": tipo, "falde": falde} if falde else None


def comune_del_nord(istat) -> bool | None:
    """True per i comuni delle regioni del Nord (codice ISTAT del comune: provincia a 3 cifre), None se il codice manca."""
    try:
        p = int(str(istat or "").zfill(6)[:3])
    except ValueError:
        return None
    if p <= 0:
        return None
    return p <= 40 or p in PROVINCE_NORD_NUOVE


def zona_altimetrica(quota, istat=None) -> dict:
    nord = comune_del_nord(istat)
    soglia = IPOTESI_TETTO["soglia_centro_sud"] if nord is False else IPOTESI_TETTO["soglia_nord"]
    try:
        q = float(quota) if quota is not None and quota != "" else math.nan
    except (TypeError, ValueError):
        q = math.nan
    montagna = math.isfinite(q) and q >= soglia
    return {"montagna": montagna, "soglia": soglia, "quota": q if math.isfinite(q) else None,
            "inclinazione": IPOTESI_TETTO["montagna" if montagna else "pianura"]}


def motivo_tetto_piano(ring, gronda, uso=None, tipo_edificio=None, buchi=(), m=False) -> str | None:
    """Perché il corpo resta piano nell'ipotesi automatica (None = si ipotizza a falde). Stesse frasi del sito."""
    u = str(uso or "").lower()
    tipo = str(tipo_edificio or "")
    if u in USI_TETTO_PIANO:
        return f"uso {'sportivo' if u == 'palestra' else 'commerciale' if u == 'commerciale' else 'produttivo'} ({u})"
    if TIPI_TETTO_PIANO.search(tipo):
        return f"tipo di edificio «{tipo}»"
    if cortili(ring, buchi):
        return "corpo con cortile"
    A = area_corpo(ring, buchi)
    if A > IPOTESI_TETTO["area_piano"]:
        return f"corpo molto grande ({_arr(A, 0):.0f} m²)"
    if gronda is None or not (gronda >= IPOTESI_TETTO["gronda_piano"]):
        return "corpo basso, accessorio (gronda sotto 3 m)"
    if m is False:
        m = rettangolo_tetto(ring)
    if not m or m["A"] < 1 or A / m["A"] < RIEMPIMENTO_MIN:
        return "forma poco rettangolare"
    if m["Lb"] > IPOTESI_TETTO["lato_piano"]:
        return f"lato corto oltre 25 m ({_arr(m['Lb'], 0):.0f} m)"
    if m["Lb"] < 2:
        return "corpo più stretto di 2 m"
    return None


def tetto_ipotizzato(ring, gronda, uso=None, tipo_edificio=None, buchi=(), quota=None, istat=None, tipo=None) -> dict:
    """{piano: True, motivo} oppure {tipo, falde, colmo, inclinazione, montagna, quota, soglia} (come tettoIpotizzato)."""
    try:
        g = float(gronda)
    except (TypeError, ValueError):
        return {"piano": True, "motivo": "corpo senza gronda"}
    if not math.isfinite(g):
        return {"piano": True, "motivo": "corpo senza gronda"}
    m = rettangolo_tetto(ring)
    motivo = motivo_tetto_piano(ring, g, uso, tipo_edificio, buchi, m)
    if motivo:
        return {"piano": True, "motivo": motivo}
    z = zona_altimetrica(quota, istat)
    colmo = _arr(g + m["Lb"] / 2 * math.tan(z["inclinazione"] * GRAD), 2)
    r = falde_stimate(ring, g, colmo, buchi, tipo)
    if not r:
        return {"piano": True, "motivo": "forma poco rettangolare"}
    return {"tipo": r["tipo"], "falde": r["falde"], "colmo": colmo, "inclinazione": z["inclinazione"],
            "montagna": z["montagna"], "quota": z["quota"], "soglia": z["soglia"]}


# ---------------------------------------------------------------------------------------------- conteggi per archivio
def _metri(geom: dict):
    """Anelli del primo poligono in metri con la proiezione locale del sito (edifici_calcoli.js, proiezione)."""
    g = geom.get("coordinates") if geom else None
    if geom and geom.get("type") == "MultiPolygon":
        g = g[0] if g else None
    anelli = [r for r in (g or []) if len(r) >= 4]
    if not anelli:
        return None, []
    lon0, lat0 = anelli[0][0][0], anelli[0][0][1]
    kx, ky = 111320 * math.cos(lat0 * GRAD), 110574
    conv = [[[(p[0] - lon0) * kx, (p[1] - lat0) * ky] for p in r] for r in anelli]
    return conv[0], conv[1:201]


def fonte_tetto(props: dict, geom: dict, lidar: dict | None = None, istat=None, quota_comune=None) -> tuple[str, dict]:
    """Fonte del tetto di un corpo dell'archivio in cascata (LiDAR → colmo DBTR → ipotesi → piano): (fonte, dettaglio)."""
    if lidar and lidar.get("stato") == "ok":
        return "lidar", {}
    ring, buchi = _metri(geom)
    if ring is None:
        return "piano", {"motivo": "sagoma non valida"}
    try:
        g = float(props.get("gronda"))
    except (TypeError, ValueError):
        g = math.nan
    colmo = props.get("colmo")
    try:
        colmo = float(colmo) if colmo not in (None, "") else None
    except (TypeError, ValueError):
        colmo = None
    if colmo and falde_stimate(ring, g, colmo, buchi):
        return "colmo", {}
    q = props.get("quota_terreno")
    quota = q if q is not None and q != "" else quota_comune
    r = tetto_ipotizzato(ring, g, props.get("uso"), props.get("tipo_edificio") or props.get("destinazione"), buchi, quota, istat)
    if r.get("piano"):
        return "piano", {"motivo": r["motivo"]}
    return "ipotesi", {"montagna": r["montagna"], "inclinazione": r["inclinazione"], "tipo": r["tipo"]}


def conta_tetti(features, istat=None, lidar: dict | None = None, quota_comune=None) -> dict:
    """Corpi per fonte del tetto: {lidar, colmo, ipotesi, pianura, montagna, piano, motivi_piano {motivo breve: n}}."""
    n = {"lidar": 0, "colmo": 0, "ipotesi": 0, "pianura": 0, "montagna": 0, "piano": 0, "motivi_piano": {}}
    for f in features:
        p = f.get("properties") or {}
        fonte, d = fonte_tetto(p, f.get("geometry"), (lidar or {}).get(str(p.get("id"))), istat, quota_comune)
        n[fonte] += 1
        if fonte == "ipotesi":
            n["montagna" if d["montagna"] else "pianura"] += 1
        elif fonte == "piano":
            k = re.sub(r" \(.*$|«.*$", "", d["motivo"]).strip()
            n["motivi_piano"][k] = n["motivi_piano"].get(k, 0) + 1
    return n
