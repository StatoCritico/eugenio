"""Altezze del DBTR non plausibili → stima (decisione di Paolo del 07/11/2026).

Alcune UVL hanno un'altezza impossibile per la loro sagoma (Bagno di Romagna, foglio 54 numero 216: 8,3 m² con H_UVL 114 m).
Il corpo **resta**; l'altezza del DBTR si sostituisce con una stima e si conserva in `h_dbtr_scartata`:

  * stima = mediana delle gronde dei corpi vicini (centro del riquadro entro RAGGIO_M) con altezza plausibile
    (≤ VICINI_MAX_M), arrotondata al mezzo metro; senza vicini, dall'uso: due piani (modello.INTERPIANI) più il sovralzo,
    tra 6 e 9 m;
  * `fonte_altezza` = «stima: altezza DBTR non plausibile (X m)», `qualita` = «altezza stimata (dato DBTR non plausibile)»;
    il colmo del DBTR si toglie (tetto piano).

Regola (provata sui 19 comuni del 07/11/2026, 502 corpi oltre 25 m; tabella nel README della fase 10). Un corpo è
**candidato** se non è un tipo verticale (luogo di culto, campanile, torre, ciminiera, edificio industriale o impianto
tecnologico, serbatoio, antenna, faro, inceneritore: lì un corpo stretto e alto è normale) e:
  * gronda oltre MASSIMO_M (150 m: nessun edificio dell'ER è così alto), oppure
  * gronda oltre SOGLIA_M (30 m) **e** snellezza (gronda / larghezza minima dell'inviluppo convesso) oltre SNELLEZZA (8):
    gli edifici alti veri stanno sotto 6 (Grattacielo di Rimini 83 m su 17 m: 4,8), i campanili intorno a 5.
Un candidato è **non plausibile** se supera MASSIMO_M, oppure se non tocca un corpo alto (riquadro entro CONTATTO_M,
almeno CONTATTO_AREA_M2 e gronda ≥ la sua − CONTATTO_SCARTO_M: torrini di scale e ascensori sopra un palazzo alto) e
inoltre ha area sotto AREA_M2 (30 m², la regola dei «sospetti» di `controlla-uvl`) o gronda oltre RELATIVA × la
mediana dei vicini (o nessun vicino).

Tutto con aritmetica semplice sulle coordinate del sistema della zona (EPSG:7791), **identica** nel lettore del sito
(`fase5-sito/sito/dbtr_lettore.js`, funzione `plausibilita`), così Python e browser cambiano gli stessi corpi.
"""
from __future__ import annotations

import math

from .modello import INTERPIANI, SOVRALZO

SOGLIA_M = 30.0
MASSIMO_M = 150.0
SNELLEZZA = 8.0
AREA_M2 = 30.0
RELATIVA = 3.0
RAGGIO_M = 100.0
VICINI_MAX_M = 40.0
CONTATTO_M = 3.0
CONTATTO_AREA_M2 = 60.0
CONTATTO_SCARTO_M = 8.0
STIMA_MIN, STIMA_MAX = 6.0, 9.0
VERTICALI = ("culto", "campanile", "torre", "ciminiera", "industr", "impianto", "capannone", "serbatoio", "antenna",
             "faro", "inceneritore", "silo")
QUALITA = "altezza stimata (dato DBTR non plausibile)"


def verticale(destinazione, tipo) -> bool:
    t = f"{destinazione or ''} {tipo or ''}".lower()
    return any(v in t for v in VERTICALI)


def _inviluppo(punti):
    """Inviluppo convesso (catena monotona di Andrew), punti (x, y)."""
    p = sorted(set((float(x), float(y)) for x, y in punti))
    if len(p) < 3:
        return p

    def giro(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    sotto, sopra = [], []
    for q in p:
        while len(sotto) >= 2 and giro(sotto[-2], sotto[-1], q) <= 0:
            sotto.pop()
        sotto.append(q)
    for q in reversed(p):
        while len(sopra) >= 2 and giro(sopra[-2], sopra[-1], q) <= 0:
            sopra.pop()
        sopra.append(q)
    return sotto[:-1] + sopra[:-1]


def larghezza_minima(anello) -> float:
    """Larghezza minima dell'inviluppo convesso dell'anello (m): il lato corto di un rettangolo."""
    h = _inviluppo(anello)
    if len(h) < 3:
        return 0.0
    migliore = math.inf
    for i in range(len(h)):
        ax, ay = h[i]
        bx, by = h[(i + 1) % len(h)]
        lx, ly = bx - ax, by - ay
        lung = math.hypot(lx, ly)
        if lung == 0:
            continue
        nx, ny = -ly / lung, lx / lung
        pr = [(x - ax) * nx + (y - ay) * ny for x, y in h]
        migliore = min(migliore, max(pr) - min(pr))
    return 0.0 if migliore == math.inf else migliore


def mediana(v):
    s = sorted(v)
    n = len(s)
    if not n:
        return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def mezzo_metro(x: float) -> float:
    return math.floor(x * 2 + 0.5) / 2


def testo_metri(x: float) -> str:
    """114 → «114», 47.94 → «47,9» (uguale in JS)."""
    v = math.floor(x * 10 + 0.5) / 10
    return (str(int(v)) if v == int(v) else f"{v:.1f}").replace(".", ",")


def stima_uso(uso) -> float:
    if uso in ("capannone", "palestra", "industriale"):
        return 8.0
    v = 2 * INTERPIANI.get(uso or "altro", INTERPIANI["altro"]) + SOVRALZO
    return min(STIMA_MAX, max(STIMA_MIN, math.floor(v * 10 + 0.5) / 10))


def giudica(elementi) -> dict[int, dict]:
    """elementi: dict con «anello» (esterno, coordinate metriche), «area», «gronda», «destinazione», «tipo», «uso».
    Restituisce {indice: {"gronda": stima, "scartata": gronda originale, "stima": "vicini"|"uso"}} dei non plausibili."""
    n = len(elementi)
    riq, cen = [], []
    for e in elementi:
        xs = [p[0] for p in e["anello"]]
        ys = [p[1] for p in e["anello"]]
        r = (min(xs), min(ys), max(xs), max(ys))
        riq.append(r)
        cen.append(((r[0] + r[2]) / 2, (r[1] + r[3]) / 2))
    candidati = []
    for i, e in enumerate(elementi):
        h = e["gronda"]
        if h is None or h <= SOGLIA_M or verticale(e.get("destinazione"), e.get("tipo")):
            continue
        if h > MASSIMO_M or h / max(larghezza_minima(e["anello"]), 0.5) > SNELLEZZA:
            candidati.append(i)
    if not candidati:
        return {}
    # griglia di RAGGIO_M per cercare i vicini
    griglia: dict[tuple[int, int], list[int]] = {}
    for j, (x, y) in enumerate(cen):
        griglia.setdefault((math.floor(x / RAGGIO_M), math.floor(y / RAGGIO_M)), []).append(j)

    def vicini(i):
        x, y = cen[i]
        gx, gy = math.floor(x / RAGGIO_M), math.floor(y / RAGGIO_M)
        out = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in griglia.get((gx + dx, gy + dy), ()):
                    if j != i and (cen[j][0] - x) ** 2 + (cen[j][1] - y) ** 2 <= RAGGIO_M ** 2:
                        out.append(j)
        return sorted(out)

    scarti: dict[int, list[int]] = {}
    for i in candidati:
        h = elementi[i]["gronda"]
        vv = vicini(i)
        if h > MASSIMO_M:
            scarti[i] = vv
            continue
        r = riq[i]
        tocca = any(elementi[j]["area"] >= CONTATTO_AREA_M2 and (elementi[j]["gronda"] or 0) >= h - CONTATTO_SCARTO_M
                    and riq[j][0] <= r[2] + CONTATTO_M and riq[j][2] >= r[0] - CONTATTO_M
                    and riq[j][1] <= r[3] + CONTATTO_M and riq[j][3] >= r[1] - CONTATTO_M for j in vv)
        if tocca:
            continue
        m = mediana([elementi[j]["gronda"] for j in vv if 0 < (elementi[j]["gronda"] or 0) <= VICINI_MAX_M])
        if elementi[i]["area"] < AREA_M2 or m is None or h > RELATIVA * m:
            scarti[i] = vv
    out = {}
    for i, vv in scarti.items():
        m = mediana([elementi[j]["gronda"] for j in vv
                     if j not in scarti and 0 < (elementi[j]["gronda"] or 0) <= VICINI_MAX_M])
        if m is not None:
            out[i] = {"gronda": max(2.0, mezzo_metro(m)), "scartata": elementi[i]["gronda"], "stima": "vicini"}
        else:
            out[i] = {"gronda": stima_uso(elementi[i].get("uso")), "scartata": elementi[i]["gronda"], "stima": "uso"}
    return out


def applica(corpi) -> list[dict]:
    """Corpi (modello.Corpo, sistema metrico) del DBTR: porta alla stima quelli non plausibili. Restituisce l'elenco dei
    cambiati (id, foglio, numero, gronda scartata, stima) per l'indice e il controllo."""
    el = []
    for c in corpi:
        g = c.sagoma
        el.append({"anello": list(g.exterior.coords)[:-1], "area": g.area, "gronda": c.gronda,
                   "destinazione": (c.extra or {}).get("destinazione"), "tipo": (c.extra or {}).get("tipo_edificio"),
                   "uso": c.uso})
    cambi = []
    for i, s in sorted(giudica(el).items()):
        c = corpi[i]
        c.extra = dict(c.extra or {})
        c.extra["h_dbtr_scartata"] = round(float(s["scartata"]), 2)
        c.extra["stima_altezza"] = s["stima"]
        c.gronda = s["gronda"]
        c.colmo, c.tetto, c.falde = None, "piano", 0
        c.fonte_altezza = f"stima: altezza DBTR non plausibile ({testo_metri(s['scartata'])} m)"
        c.qualita = QUALITA
        cambi.append({"id": c.id, "foglio": c.extra.get("foglio"), "numero": c.extra.get("numero"),
                      "h_dbtr": c.extra["h_dbtr_scartata"], "stima": c.gronda, "da": s["stima"],
                      "area": round(c.sagoma.area, 1)})
    return cambi
