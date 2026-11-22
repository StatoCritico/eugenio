"""Disegno della pagina iniziale (22/11/2026; rifatto alle 13:41–13:45 su richiesta di Paolo).

Un edificio a piastra (bassa) e torre (alta) in assonometria, con la piastra aperta in spaccato per mostrare l'unità di
trattamento aria con il recupero di calore e i canali; fotovoltaico sulla piastra; solare termico e pompa di calore sul
tetto della torre; centrale termica con caldaia, sopra il gruppo frigo e la torre evaporativa; cogeneratore; ombre (corte
d'estate, lunghe d'inverno); reti: cabina primaria, traliccio con la linea fino alla cabina MT/BT, cabina del gas con il
tubo; territorio con campi, particelle, case, alberi e strada; radar e stazione meteo; cielo con sole, nuvole, pioggia e
neve.

Scrive parti/scena_home.svg, che costruisci_pagine.py mette in index.html (blocco <!-- scena-home -->). Si rilancia solo
quando si cambia il disegno:

    python parti/scena_home.py

Ogni parte che si può indicare è un <g class="parte" data-parte="…" data-gruppo="…">: le chiavi sono quelle di
[parti.…] in parti/home.toml (titolo, descrizione, pagine; senza pagine attive la parte è «prossimamente»). Ogni parte ha
un punto di richiamo (+) per far capire che si può indicare. Colori e animazioni: stile.css (classi sc-…, varianti per
inverno, meteo e tema chiaro)."""
from __future__ import annotations

import math
from pathlib import Path

W, H = 960, 700
CX, CY, S = 470, 172, 22.0
C30, S30 = math.cos(math.radians(30)), math.sin(math.radians(30))
OMBRA = {"estate": (0.5, -0.2), "inverno": (1.2, -0.48)}       # spostamento dell'ombra a terra per unità d'altezza


def iso(x: float, y: float, z: float = 0.0) -> tuple[float, float]:
    return CX + (x - y) * C30 * S, CY + (x + y) * S30 * S - z * S


def pts(*p3) -> str:
    return " ".join(f"{a:.1f},{b:.1f}" for a, b in (iso(*p) for p in p3))


def poli(cls: str, *p3) -> str:
    return f'<polygon class="{cls}" points="{pts(*p3)}"/>'


def linea(cls: str, p, q) -> str:
    a, b = iso(*p), iso(*q)
    return f'<line class="{cls}" x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}"/>'


def scatola(x0, y0, x1, y1, h, cls, z0=0.0) -> list[str]:
    """Parallelepipedo: facce visibili (y=y1 a sinistra, x=x1 a destra, sopra)."""
    return [
        poli(f"sc-{cls}-sx", (x0, y1, z0), (x1, y1, z0), (x1, y1, z0 + h), (x0, y1, z0 + h)),
        poli(f"sc-{cls}-dx", (x1, y0, z0), (x1, y1, z0), (x1, y1, z0 + h), (x1, y0, z0 + h)),
        poli(f"sc-{cls}-su", (x0, y0, z0 + h), (x1, y0, z0 + h), (x1, y1, z0 + h), (x0, y1, z0 + h)),
    ]


def cilindro(x, y, r, z0, z1, cls) -> list[str]:
    a, b = iso(x, y, z0), iso(x, y, z1)
    rx, ry = r * S * 1.22, r * S * 0.7
    return [f'<path class="sc-{cls}-corpo" d="M{a[0] - rx:.1f},{b[1]:.1f} L{a[0] - rx:.1f},{a[1]:.1f} '
            f'A{rx:.1f},{ry:.1f} 0 0 0 {a[0] + rx:.1f},{a[1]:.1f} L{a[0] + rx:.1f},{b[1]:.1f} Z"/>',
            f'<ellipse class="sc-{cls}-su" cx="{b[0]:.1f}" cy="{b[1]:.1f}" rx="{rx:.1f}" ry="{ry:.1f}"/>']


def inviluppo(punti):
    p = sorted(set(punti))
    if len(p) <= 2:
        return p

    def giro(seq):
        out = []
        for q in seq:
            while len(out) >= 2 and ((out[-1][0] - out[-2][0]) * (q[1] - out[-2][1])
                                     - (out[-1][1] - out[-2][1]) * (q[0] - out[-2][0])) <= 0:
                out.pop()
            out.append(q)
        return out
    basso, alto = giro(p), giro(list(reversed(p)))
    return basso[:-1] + alto[:-1]


def ombra(x0, y0, x1, y1, zt, stagione, zb=0.0) -> str:
    vx, vy = OMBRA[stagione]
    ang = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    tutti = [(x + vx * zb, y + vy * zb) for x, y in ang] + [(x + vx * zt, y + vy * zt) for x, y in ang]
    return f'<polygon class="sc-ombra sc-ombra-{stagione}" points="{pts(*[(x, y, 0) for x, y in inviluppo(tutti)])}"/>'


def richiamo(x, y, z, prossimamente=False, schermo=None) -> str:
    """Punto di richiamo (+) sulla parte: fa capire che si può indicare; tratteggiato se la parte è «prossimamente»."""
    a = schermo or iso(x, y, z)
    cls = "sc-richiamo" + (" sc-richiamo-poi" if prossimamente else "")
    return (f'<g class="{cls}" transform="translate({a[0]:.1f} {a[1]:.1f})"><circle class="sc-alone" r="12"/>'
            f'<circle class="sc-punto" r="8.5"/><path d="M-4,0 H4 M0,-4 V4"/></g>')


def parte(chiave: str, gruppo: str, corpo: list[str]) -> str:
    return (f'<g class="parte" data-parte="{chiave}" data-gruppo="{gruppo}" tabindex="0" role="button">\n  '
            + "\n  ".join(corpo) + "\n</g>")


# ------------------------------------------------------------------------------------------------- elementi
def vetrata(piano, a0, a1, fisso, z0, z1, lato, interpiano=0.95, passo=0.55) -> list[str]:
    """Facciata a vetri con marcapiani e montanti: lato 'sx' (piano y=fisso, a = x) o 'dx' (piano x=fisso, a = y)."""
    P = (lambda a, z: (a, fisso, z)) if lato == "sx" else (lambda a, z: (fisso, a, z))
    out = [poli(f"sc-vetro-{lato}", P(a0, z0), P(a1, z0), P(a1, z1), P(a0, z1))]
    z = z0 + interpiano
    while z < z1 - 0.1:
        out.append(poli(f"sc-marcapiano-{lato}", P(a0, z - .13), P(a1, z - .13), P(a1, z + .05), P(a0, z + .05)))
        z += interpiano
    a = a0 + passo
    while a < a1 - 0.05:
        out.append(linea("sc-montante", P(a, z0), P(a, z1)))
        a += passo
    return out


def pannelli(x0, y0, x1, y1, z, file, inclin, cls, righe_x=0.62, tubi=False) -> list[str]:
    out, passo = [], (y1 - y0) / file
    for i in range(file):
        ya, yb = y0 + i * passo + .08, y0 + i * passo + passo * .72
        q = [(x0, ya, z + .05), (x1, ya, z + .05), (x1, yb, z + .05 + inclin), (x0, yb, z + .05 + inclin)]
        out.append(poli(cls, *q))
        x = x0 + (0.18 if tubi else righe_x)
        while x < x1 - .08:
            out.append(linea(f"{cls}-riga", (x, ya, z + .05), (x, yb, z + .05 + inclin)))
            x += 0.2 if tubi else righe_x
        if not tubi:
            out.append(linea(f"{cls}-riga", (x0, (ya + yb) / 2, z + .05 + inclin / 2), (x1, (ya + yb) / 2, z + .05 + inclin / 2)))
        out.append(poli("sc-neve sc-neve-pannello", *[(a, b, c + .01) for a, b, c in q]))
    return out


def ventola(x, y, z, r=0.36) -> list[str]:
    c = iso(x, y, z)
    rx, ry = r * S * 1.22, r * S * 0.7
    return [f'<ellipse class="sc-ventola-fondo" cx="{c[0]:.1f}" cy="{c[1]:.1f}" rx="{rx:.1f}" ry="{ry:.1f}"/>',
            f'<g class="sc-ventola" style="transform-origin:{c[0]:.1f}px {c[1]:.1f}px">'
            f'<line x1="{c[0] - rx * .8:.1f}" y1="{c[1]:.1f}" x2="{c[0] + rx * .8:.1f}" y2="{c[1]:.1f}"/>'
            f'<line x1="{c[0]:.1f}" y1="{c[1] - ry * .8:.1f}" x2="{c[0]:.1f}" y2="{c[1] + ry * .8:.1f}"/></g>']


def sbuffi(c, cls, n=3, passo=(3, 9), r0=4) -> str:
    return (f'<g class="{cls}">' + "".join(
        f'<circle cx="{c[0] + passo[0] * i:.1f}" cy="{c[1] - 6 - passo[1] * i:.1f}" r="{r0 + 2 * i}" '
        f'style="animation-delay:{i * .85:.2f}s"/>' for i in range(n)) + '</g>')


def albero(x, y, h=1.5, r=0.72, tipo="tondo") -> list[str]:
    b, t = iso(x, y, 0), iso(x, y, h)
    rr = r * S
    out = [f'<line class="sc-tronco" x1="{b[0]:.1f}" y1="{b[1]:.1f}" x2="{t[0]:.1f}" y2="{t[1]:.1f}"/>']
    if tipo == "conifera":
        out.append(f'<path class="sc-conifera" d="M{t[0]:.1f},{t[1] - rr * 2.2:.1f} L{t[0] + rr * .72:.1f},{t[1] + rr * .2:.1f} '
                   f'L{t[0] - rr * .72:.1f},{t[1] + rr * .2:.1f} Z"/>')
        out.append(f'<path class="sc-conifera-luce" d="M{t[0]:.1f},{t[1] - rr * 2.2:.1f} L{t[0] - rr * .72:.1f},{t[1] + rr * .2:.1f} '
                   f'L{t[0] - rr * .1:.1f},{t[1] + rr * .2:.1f} Z"/>')
        out.append(f'<path class="sc-neve" d="M{t[0]:.1f},{t[1] - rr * 2.2:.1f} L{t[0] + rr * .3:.1f},{t[1] - rr * 1.25:.1f} '
                   f'L{t[0] - rr * .3:.1f},{t[1] - rr * 1.25:.1f} Z"/>')
    else:
        cy = t[1] - rr * .6
        out.append(f'<circle class="sc-chioma" cx="{t[0]:.1f}" cy="{cy:.1f}" r="{rr:.1f}"/>')
        out.append(f'<path class="sc-chioma-luce" d="M{t[0] - rr:.1f},{cy:.1f} A{rr:.1f},{rr:.1f} 0 0 1 {t[0]:.1f},{cy - rr:.1f} '
                   f'A{rr * .9:.1f},{rr:.1f} 0 0 0 {t[0] - rr:.1f},{cy:.1f} Z"/>')
        out.append(f'<ellipse class="sc-neve" cx="{t[0]:.1f}" cy="{cy - rr * .62:.1f}" rx="{rr * .72:.1f}" ry="{rr * .36:.1f}"/>')
    return out


def casa(x0, y0, x1, y1, h, r=0.9) -> list[str]:
    ym = (y0 + y1) / 2
    out = scatola(x0, y0, x1, y1, h, "casa")
    out += [poli("sc-tetto-sx", (x0, y1, h), (x1, y1, h), (x1, ym, h + r), (x0, ym, h + r)),
            poli("sc-tetto-dx", (x1, y0, h), (x1, y1, h), (x1, ym, h + r)),
            poli("sc-neve", (x0, y1, h), (x1, y1, h), (x1, ym, h + r), (x0, ym, h + r))]
    for k in (0.4, 1.15):
        if y0 + k + .42 < y1:
            out.append(poli("sc-finestra", (x1, y0 + k, .5), (x1, y0 + k + .42, .5), (x1, y0 + k + .42, 1.05), (x1, y0 + k, 1.05)))
    return out


def campo(x0, y0, x1, y1, righe=6, cls="sc-campo") -> list[str]:
    out = [poli(cls, (x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    for i in range(1, righe):
        y = y0 + (y1 - y0) * i / righe
        out.append(linea("sc-solco", (x0 + .1, y), (x1 - .1, y)))
    out.append(poli("sc-neve sc-neve-campo", (x0, y0), (x1, y0), (x1, y1), (x0, y1)))
    out.append(poli("sc-particella", (x0, y0), (x1, y0), (x1, y1), (x0, y1)))
    return out


# ------------------------------------------------------------------------------------------------- scena
def disegno() -> str:
    g: list[str] = ['<defs>'
                    '<linearGradient id="sc-g-cielo" x1="0" y1="0" x2="0" y2="1"><stop class="sc-cielo-alto" offset="0"/>'
                    '<stop class="sc-cielo-basso" offset="1"/></linearGradient>'
                    '<radialGradient id="sc-g-sole"><stop class="sc-sole-centro" offset=".35"/>'
                    '<stop class="sc-sole-alone" offset="1"/></radialGradient>'
                    '</defs>']

    # ---------------------------------------------------------------------------------- cielo
    def nuvola(x, y, k=1.0, cls="sc-nuvola"):
        return (f'<g class="{cls}" transform="translate({x} {y}) scale({k})">'
                '<path class="sc-nuvola-corpo" d="M-70,10 Q-72,-12 -46,-14 Q-40,-38 -12,-34 Q4,-56 32,-40 Q62,-44 64,-14 '
                'Q84,-10 80,10 Z"/><path class="sc-nuvola-ombra" d="M-70,10 L80,10 Q78,3 66,1 L-58,1 Q-68,3 -70,10 Z"/></g>')
    pioggia = '<g class="sc-pioggia">' + "".join(
        f'<line x1="{x}" y1="{y}" x2="{x - 5}" y2="{y + 15}" style="animation-delay:{(i * .13) % 1:.2f}s"/>'
        for i, (x, y) in enumerate((530 + 19 * (i % 11) + (i // 11) * 8, 104 + 30 * (i // 11)) for i in range(44))) + '</g>'
    neve = '<g class="sc-fiocchi">' + "".join(
        f'<circle cx="{x}" cy="{y}" r="{1.8 + (i % 3) * .7:.1f}" style="animation-delay:{(i * .37) % 3:.2f}s"/>'
        for i, (x, y) in enumerate((30 + (i * 67) % 900, 18 + (i * 47) % 200) for i in range(60))) + '</g>'
    g.append(parte("meteo", "clima", [
        f'<rect class="sc-cielo" x="0" y="0" width="{W}" height="{H}"/>',
        '<g class="sc-sole"><circle class="sc-sole-alone" cx="140" cy="92" r="72"/><circle class="sc-sole-disco" cx="140" cy="92" r="28"/></g>',
        nuvola(330, 66, .62, "sc-nuvola sc-nuvola-lenta"), nuvola(640, 90, 1.05), pioggia, neve,
        nuvola(860, 50, .72, "sc-nuvola sc-nuvola-lenta"), richiamo(0, 0, 0, schermo=(640, 60))]))

    # ---------------------------------------------------------------------------------- territorio
    terr = [poli("sc-terreno", (0, 0), (22, 0), (22, 22), (0, 22)),
            poli("sc-neve sc-neve-terreno", (0, 0), (22, 0), (22, 22), (0, 22)),
            poli("sc-terreno-bordo-sx", (0, 22, 0), (22, 22, 0), (22, 22, -0.7), (0, 22, -0.7)),
            poli("sc-terreno-bordo-dx", (22, 0, 0), (22, 22, 0), (22, 22, -0.7), (22, 0, -0.7)),
            poli("sc-marciapiede", (0, 14.6), (22, 14.6), (22, 17.2), (0, 17.2)),
            poli("sc-strada", (0, 15.0), (22, 15.0), (22, 16.8), (0, 16.8))]
    x = 0.4
    while x < 21.6:
        terr.append(linea("sc-mezzeria", (x, 15.9), (x + .6, 15.9)))
        x += 1.3
    terr.append(poli("sc-piazzale", (5.4, 5.4), (14.4, 5.4), (14.4, 14.0), (5.4, 14.0)))
    terr += campo(0.6, 0.6, 4.8, 5.8, 7) + campo(0.6, 10.4, 4.4, 13.8, 5) + campo(0.8, 17.8, 6.8, 21.4, 5, "sc-campo sc-campo-2")
    terr += casa(7.2, 1.0, 9.2, 3.0, 1.5) + casa(10.0, 1.2, 11.8, 3.0, 1.3) + casa(8.6, 18.2, 10.8, 20.2, 1.5) + casa(12.0, 18.4, 13.8, 20.2, 1.3)
    for (x, y, t) in ((5.6, 1.6, "conifera"), (6.0, 3.6, "tondo"), (4.9, 14.0, "tondo"), (5.0, 9.6, "conifera"),
                      (15.4, 18.6, "tondo"), (17.4, 19.6, "conifera"), (19.8, 18.4, "tondo"), (7.4, 20.6, "tondo"),
                      (21.2, 14.0, "conifera"), (12.9, 1.6, "tondo"), (5.2, 6.8, "tondo")):
        terr += albero(x, y, tipo=t)
    terr.append(richiamo(2.5, 12.1, .2))
    g.append(parte("territorio", "patrimonio", terr))

    # ---------------------------------------------------------------------------------- radar e stazione meteo
    RX, RY = 1.9, 7.9
    st = [poli("sc-recinto", (0.6, 6.4), (4.4, 6.4), (4.4, 9.6), (0.6, 9.6))]
    st += scatola(RX - .7, RY - .7, RX + .7, RY + .7, .5, "base")
    a, b = iso(RX, RY, .5), iso(RX, RY, 4.2)
    st.append(f'<path class="sc-traliccio-radar" d="M{a[0] - 9:.1f},{a[1]:.1f} L{b[0] - 4:.1f},{b[1]:.1f} L{b[0] + 4:.1f},{b[1]:.1f} L{a[0] + 9:.1f},{a[1]:.1f} Z"/>')
    for k in range(1, 6):
        z = .5 + k * .62
        p, q = iso(RX, RY, z)
        w = 9 - k * .9
        st.append(f'<line class="sc-ferro-fine" x1="{p - w:.1f}" y1="{q:.1f}" x2="{p + w:.1f}" y2="{q:.1f}"/>')
    st.append(f'<circle class="sc-radome" cx="{b[0]:.1f}" cy="{b[1] - 15:.1f}" r="19"/>')
    st.append(f'<path class="sc-radome-luce" d="M{b[0] - 19:.1f},{b[1] - 15:.1f} A19,19 0 0 1 {b[0]:.1f},{b[1] - 34:.1f} A16,19 0 0 0 {b[0] - 19:.1f},{b[1] - 15:.1f} Z"/>')
    st.append(f'<path class="sc-neve" d="M{b[0] - 15:.1f},{b[1] - 26:.1f} A19,19 0 0 1 {b[0] + 15:.1f},{b[1] - 26:.1f} Q{b[0]:.1f},{b[1] - 20:.1f} {b[0] - 15:.1f},{b[1] - 26:.1f} Z"/>')
    # stazione meteo: palo, anemometro, banderuola, schermo solare
    a, b = iso(3.6, 8.4, 0), iso(3.6, 8.4, 2.6)
    st.append(f'<line class="sc-palo" x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}"/>')
    st.append(f'<line class="sc-palo" x1="{b[0] - 12:.1f}" y1="{b[1] + 3:.1f}" x2="{b[0] + 12:.1f}" y2="{b[1] - 3:.1f}"/>')
    st.append(f'<g class="sc-anemometro" style="transform-origin:{b[0] - 12:.1f}px {b[1] - 3:.1f}px">'
              f'<circle cx="{b[0] - 17:.1f}" cy="{b[1] - 3:.1f}" r="2.6"/><circle cx="{b[0] - 7:.1f}" cy="{b[1] - 3:.1f}" r="2.6"/>'
              f'<line x1="{b[0] - 17:.1f}" y1="{b[1] - 3:.1f}" x2="{b[0] - 7:.1f}" y2="{b[1] - 3:.1f}"/></g>')
    st.append(f'<path class="sc-banderuola" d="M{b[0] + 8:.1f},{b[1] - 4:.1f} L{b[0] + 20:.1f},{b[1] - 8:.1f} L{b[0] + 18:.1f},{b[1] - 2:.1f} Z"/>')
    st += scatola(3.3, 8.7, 3.9, 9.3, .55, "schermo", z0=1.1)
    st.append(richiamo(RX, RY, 6.6))
    g.append(parte("stazione-meteo", "clima", st))

    # ---------------------------------------------------------------------------------- misure dell'edificio
    x0, y0, x1, y1, hp = 6.0, 6.0, 13.6, 13.2, 2.3            # piastra
    cx0, cy0 = 10.2, 9.8                                        # angolo aperto in spaccato
    tx0, ty0, tx1, ty1, ht = 6.6, 6.6, 9.8, 9.6, 8.0            # torre
    CT = (15.2, 6.0, 18.0, 8.6, 1.6)                            # centrale termica
    CG = (15.2, 9.8, 17.6, 11.2, 1.3)                           # cogeneratore

    # ombre a terra (estate corte, inverno lunghe)
    om = []
    for s in ("estate", "inverno"):
        om += [ombra(tx0, ty0, tx1, ty1, ht, s), ombra(x0, y0, x1, y1, hp, s),
               ombra(*CT[:4], CT[4] + 1.2, s), ombra(*CG[:4], CG[4], s)]
    om.append(richiamo(0, 0, 0, schermo=iso(13.6 + 3.2, 6.4, 0)))
    g.append(parte("ombre", "edificio", om))

    # ---------------------------------------------------------------------------------- reti: cabina primaria e traliccio
    cp = [poli("sc-recinto", (16.4, 0.6), (21.4, 0.6), (21.4, 4.6), (16.4, 4.6))]
    cp += scatola(16.8, 1.0, 18.6, 2.4, 1.5, "cabina")
    for xa in (17.0, 19.2):
        cp += scatola(xa, 3.0, xa + 1.3, 4.1, 1.1, "trafo")
        for k in range(4):
            cp.append(linea("sc-alette", (xa + .2 + k * .3, 4.1, .12), (xa + .2 + k * .3, 4.1, 1.0)))
    cp += [linea("sc-ferro", (19.6, 1.2, 0), (19.6, 1.2, 2.6)), linea("sc-ferro", (21.0, 1.2, 0), (21.0, 1.2, 2.6)),
           linea("sc-ferro", (19.6, 1.2, 2.6), (21.0, 1.2, 2.6))]
    cp.append(richiamo(17.7, 1.7, 2.6))
    g.append(parte("cabina-primaria", "statistiche", cp))

    tr = []
    px, py, ph = 15.0, 3.2, 6.4
    b1, b2, cima = (px - .4, py + .4, 0), (px + .4, py - .4, 0), (px, py, ph)
    m1, m2 = (px - .22, py + .22, ph * .5), (px + .22, py - .22, ph * .5)
    tr += [linea("sc-ferro", b1, cima), linea("sc-ferro", b2, cima), linea("sc-ferro", b1, m2), linea("sc-ferro", b2, m1),
           linea("sc-ferro", m1, m2), linea("sc-ferro", (px - .32, py + .32, ph * .25), (px + .32, py - .32, ph * .25))]
    br1, br2 = (px - 1.1, py + 1.1, ph * .86), (px + 1.1, py - 1.1, ph * .86)
    tr.append(linea("sc-ferro", br1, br2))
    tr.append(linea("sc-ferro", (px - .7, py + .7, ph * .7), (px + .7, py - .7, ph * .7)))
    tr += scatola(13.9, 4.3, 14.8, 5.2, 1.1, "cabina")                       # cabina MT/BT dell'edificio
    for p, q in ((iso(20.3, 1.2, 2.6), iso(*br2)), (iso(*br1), iso(14.35, 4.75, 1.1))):
        mx, my = (p[0] + q[0]) / 2, max(p[1], q[1]) + 12
        tr.append(f'<path class="sc-filo" d="M{p[0]:.1f},{p[1]:.1f} Q{mx:.1f},{my:.1f} {q[0]:.1f},{q[1]:.1f}"/>')
    tr.append(richiamo(px, py, ph + .9))
    g.append(parte("traliccio", "statistiche", tr))

    # ---------------------------------------------------------------------------------- edificio: piastra aperta e torre
    ed = []
    # interno dello spaccato: pavimento e pareti di fondo (le facce interne si vedono dall'angolo aperto)
    ed.append(poli("sc-pavimento", (cx0, cy0, 0), (x1, cy0, 0), (x1, y1, 0), (cx0, y1, 0)))
    ed.append(poli("sc-interno-sx", (cx0, cy0, 0), (x1, cy0, 0), (x1, cy0, hp), (cx0, cy0, hp)))
    ed.append(poli("sc-interno-dx", (cx0, cy0, 0), (cx0, y1, 0), (cx0, y1, hp), (cx0, cy0, hp)))
    # sezione del solaio di copertura (poché) sopra le pareti interne
    ed.append(poli("sc-sezione", (cx0, cy0, hp - .28), (x1, cy0, hp - .28), (x1, cy0, hp), (cx0, cy0, hp)))
    ed.append(poli("sc-sezione", (cx0, cy0, hp - .28), (cx0, y1, hp - .28), (cx0, y1, hp), (cx0, cy0, hp)))
    # facce esterne della piastra fuori dallo spaccato
    ed.append(poli("sc-muro-sx", (x0, y1, 0), (cx0, y1, 0), (cx0, y1, hp), (x0, y1, hp)))
    ed.append(poli("sc-muro-dx", (x1, y0, 0), (x1, cy0, 0), (x1, cy0, hp), (x1, y0, hp)))
    ed.append(poli("sc-nastro-sx", (x0 + .3, y1, .7), (cx0 - .3, y1, .7), (cx0 - .3, y1, 1.7), (x0 + .3, y1, 1.7)))
    ed.append(poli("sc-nastro-dx", (x1, y0 + .3, .7), (x1, cy0 - .3, .7), (x1, cy0 - .3, 1.7), (x1, y0 + .3, 1.7)))
    a = x0 + .85
    while a < cx0 - .35:
        ed.append(linea("sc-montante", (a, y1, .7), (a, y1, 1.7)))
        a += .85
    a = y0 + .85
    while a < cy0 - .35:
        ed.append(linea("sc-montante", (x1, a, .7), (x1, a, 1.7)))
        a += .85
    # sezioni dei muri tagliati
    ed.append(poli("sc-sezione", (cx0, y1 - .25, 0), (cx0, y1, 0), (cx0, y1, hp), (cx0, y1 - .25, hp)))
    ed.append(poli("sc-sezione", (x1 - .25, cy0, 0), (x1, cy0, 0), (x1, cy0, hp), (x1 - .25, cy0, hp)))
    # copertura a L e parapetto
    L = [(x0, y0, hp), (x1, y0, hp), (x1, cy0, hp), (cx0, cy0, hp), (cx0, y1, hp), (x0, y1, hp)]
    ed.append(poli("sc-muro-su", *L))
    i = .16
    ed.append(poli("sc-copertura", (x0 + i, y0 + i, hp), (x1 - i, y0 + i, hp), (x1 - i, cy0, hp), (cx0, cy0, hp), (cx0, y1 - i, hp), (x0 + i, y1 - i, hp)))
    ed.append(poli("sc-neve", (x0 + i, y0 + i, hp), (x1 - i, y0 + i, hp), (x1 - i, cy0, hp), (cx0, cy0, hp), (cx0, y1 - i, hp), (x0 + i, y1 - i, hp)))
    # ingresso sul fronte sinistro
    ed.append(poli("sc-pensilina", (7.0, y1, 1.15), (8.6, y1, 1.15), (8.6, y1 + .8, 1.15), (7.0, y1 + .8, 1.15)))
    ed.append(poli("sc-ingresso", (7.2, y1, 0), (8.4, y1, 0), (8.4, y1, 1.1), (7.2, y1, 1.1)))
    # torre
    ed += vetrata("y", tx0, tx1, ty1, hp, ht - .4, "sx")
    ed += vetrata("x", ty0, ty1, tx1, hp, ht - .4, "dx")
    ed += scatola(tx0, ty0, tx1, ty1, .4, "corona", z0=ht - .4)
    ed.append(poli("sc-copertura", (tx0 + i, ty0 + i, ht), (tx1 - i, ty0 + i, ht), (tx1 - i, ty1 - i, ht), (tx0 + i, ty1 - i, ht)))
    ed.append(poli("sc-neve", (tx0 + i, ty0 + i, ht), (tx1 - i, ty0 + i, ht), (tx1 - i, ty1 - i, ht), (tx0 + i, ty1 - i, ht)))
    ed.append(richiamo(tx1, ty1 - .2, 5.4))
    g.append(parte("edificio", "edificio", ed))

    # contatore accanto all'ingresso (prezzi e costi)
    ct_ = scatola(9.2, y1, 9.8, y1 + .25, .9, "contatore", z0=.25)
    ct_.append(poli("sc-display", (9.3, y1 + .25, .75), (9.7, y1 + .25, .75), (9.7, y1 + .25, 1.0), (9.3, y1 + .25, 1.0)))
    ct_.append(richiamo(9.5, y1 + .2, 1.7))
    g.append(parte("contatore", "statistiche", ct_))

    # ---------------------------------------------------------------------------------- spaccato: UTA con recupero e canali
    za = 0.0
    uta = []
    # canali: mandata (in alto, verso la torre) e ripresa
    uta += scatola(10.6, 10.5, 11.1, 11.0, hp - .5 - 1.15, "canale-mandata", z0=1.15)
    uta += scatola(10.25, 10.5, 10.6, 11.0, .45, "canale-mandata", z0=hp - .85)
    uta += scatola(12.5, 10.5, 13.0, 11.0, hp - .5 - 1.15, "canale-ripresa", z0=1.15)
    uta += scatola(12.5, 9.85, 13.0, 10.5, .45, "canale-ripresa", z0=hp - .85)
    # corpo dell'UTA: presa d'aria, filtri, batterie, ventilatore
    uta += scatola(10.5, 11.3, 11.4, 12.6, 1.15, "uta", z0=za)
    uta += scatola(12.2, 11.3, 13.2, 12.6, 1.15, "uta", z0=za)
    for k in (10.8, 11.1):
        uta.append(linea("sc-uta-giunto", (k, 12.6, .08), (k, 12.6, 1.07)))
    uta.append(poli("sc-batteria", (12.35, 12.6, .2), (12.65, 12.6, .2), (12.65, 12.6, .95), (12.35, 12.6, .95)))
    c = iso(12.95, 12.6, .58)
    uta.append(f'<circle class="sc-ventola-fondo" cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="6.5"/>')
    uta.append(f'<g class="sc-ventola" style="transform-origin:{c[0]:.1f}px {c[1]:.1f}px"><line x1="{c[0] - 5:.1f}" y1="{c[1]:.1f}" '
               f'x2="{c[0] + 5:.1f}" y2="{c[1]:.1f}"/><line x1="{c[0]:.1f}" y1="{c[1] - 5:.1f}" x2="{c[0]:.1f}" y2="{c[1] + 5:.1f}"/></g>')
    # frecce dell'aria (mandata blu, ripresa rossa)
    a1, a2 = iso(10.85, 10.75, hp - .62), iso(10.3, 10.75, hp - .62)
    uta.append(f'<path class="sc-freccia-mandata" d="M{a1[0]:.1f},{a1[1]:.1f} L{a2[0]:.1f},{a2[1]:.1f}"/>')
    uta.append(richiamo(11.0, 11.9, 1.9))
    g.append(parte("uta", "aria", uta))
    rec = scatola(11.4, 11.3, 12.2, 12.6, 1.15, "recupero", z0=za)
    rec += [linea("sc-recupero-x", (11.45, 12.6, .1), (12.15, 12.6, 1.05)), linea("sc-recupero-x", (12.15, 12.6, .1), (11.45, 12.6, 1.05))]
    rec.append(richiamo(11.8, 11.9, 1.9 + .0, schermo=None).replace("translate(", "translate(", 1))
    g.append(parte("recupero", "aria", rec))

    # ---------------------------------------------------------------------------------- tetti: fotovoltaico, solare termico, pompa di calore
    g.append(parte("fotovoltaico", "fotovoltaico",
                   pannelli(6.4, 9.95, 9.9, 13.0, hp, 3, .32, "sc-fv") + pannelli(10.1, 6.3, 13.3, 9.6, hp, 3, .32, "sc-fv")
                   + [richiamo(11.7, 7.9, hp + 1.0)]))
    g.append(parte("solare-termico", "edificio",
                   pannelli(tx0 + .3, ty0 + .25, tx1 - .3, ty0 + 1.65, ht, 1, .45, "sc-st", tubi=True)
                   + cilindro(tx1 - .55, ty0 + .55, .26, ht + .5, ht + 1.25, "serbatoio")
                   + [richiamo(tx0 + 1.2, ty0 + .9, ht + 1.5, True)]))
    pdc = scatola(tx0 + .35, ty0 + 2.0, tx1 - .35, ty1 - .3, .75, "pdc", z0=ht)
    pdc.append(poli("sc-pdc-fascia", (tx1 - .35, ty0 + 2.0, ht + .48), (tx1 - .35, ty1 - .3, ht + .48),
                    (tx1 - .35, ty1 - .3, ht + .6), (tx1 - .35, ty0 + 2.0, ht + .6)))
    for k in (tx0 + 1.0, tx0 + 2.2):
        pdc += ventola(k, (ty0 + 2.0 + ty1 - .3) / 2, ht + .75, .32)
    pdc.append(richiamo(tx0 + 1.6, ty1 - .5, ht + 1.6, True))
    g.append(parte("pdc", "edificio", pdc))

    # ---------------------------------------------------------------------------------- centrale termica, frigo e torre evaporativa
    a0, b0, a1_, b1_, h = CT
    cald = scatola(a0, b0, a1_, b1_, h, "centrale")
    for k in range(4):
        z = .3 + k * .26
        cald.append(linea("sc-feritoia", (a1_, b0 + .3, z), (a1_, b0 + 1.4, z)))
    cald.append(poli("sc-porta", (a0 + .4, b1_, 0), (a0 + 1.1, b1_, 0), (a0 + 1.1, b1_, 1.05), (a0 + .4, b1_, 1.05)))
    cald += cilindro(a0 + .35, b1_ - .45, .15, h, 4.6, "camino")
    cald.append(sbuffi(iso(a0 + .35, b1_ - .45, 4.6), "sc-vapore"))
    cald.append(richiamo(a1_, b0 + 1.9, 1.0, True))
    g.append(parte("caldaia", "edificio", cald))
    fr = scatola(a0 + .25, b0 + .2, a0 + 1.55, b0 + 1.4, .7, "frigo", z0=h)
    for k in range(3):
        fr.append(linea("sc-feritoia", (a0 + 1.55, b0 + .35, h + .15 + k * .18), (a0 + 1.55, b0 + 1.25, h + .15 + k * .18)))
    fr += scatola(a0 + 1.75, b0 + .15, a1_ - .15, b0 + 1.95, 1.05, "torre", z0=h)
    for k in range(4):
        fr.append(linea("sc-torre-lamella", (a1_ - .15, b0 + .3, h + .15 + k * .2), (a1_ - .15, b0 + 1.8, h + .15 + k * .2)))
    fr += ventola((a0 + 1.75 + a1_ - .15) / 2, b0 + 1.05, h + 1.05, .4)
    fr.append(sbuffi(iso((a0 + 1.75 + a1_ - .15) / 2, b0 + 1.05, h + 1.05), "sc-pennacchio", 3, (2, 10), 6))
    fr.append(richiamo(a0 + .9, b0 + .8, h + 1.4, True))
    g.append(parte("frigo", "edificio", fr))

    # ---------------------------------------------------------------------------------- cogeneratore
    a0, b0, a1_, b1_, h = CG
    cog = scatola(a0, b0, a1_, b1_, h, "cog")
    for k in (a0 + .6, a0 + 1.2, a0 + 1.8):
        cog.append(linea("sc-cog-giunto", (k, b1_, .08), (k, b1_, h - .08)))
    cog += cilindro(a1_ - .4, b0 + .35, .17, h, 3.3, "scarico")
    cog.append(sbuffi(iso(a1_ - .4, b0 + .35, 3.3), "sc-fumo"))
    cog.append(richiamo(a0 + 1.0, b0 + .7, h + .9, True))
    g.append(parte("cogenerazione", "cogenerazione", cog))

    # ---------------------------------------------------------------------------------- cabina del gas e tubo
    gas = [poli("sc-recinto", (18.8, 11.4), (21.4, 11.4), (21.4, 13.6), (18.8, 13.6))]
    p0, p1, p2, p3, p4 = iso(22, 12.4), iso(19.6, 12.4), iso(18.6, 10.5), iso(17.6, 10.5), iso(18.6, 8.0)
    gas.append(f'<polyline class="sc-gas" points="{p0[0]:.1f},{p0[1]:.1f} {p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},{p2[1]:.1f} {p3[0]:.1f},{p3[1]:.1f}"/>')
    p5 = iso(18.0, 8.0)
    gas.append(f'<polyline class="sc-gas" points="{p2[0]:.1f},{p2[1]:.1f} {p4[0]:.1f},{p4[1]:.1f} {p5[0]:.1f},{p5[1]:.1f}"/>')
    gas += scatola(19.4, 11.8, 20.8, 13.0, 1.1, "gas")
    gas.append(poli("sc-gas-fascia", (19.4, 13.0, .7), (20.8, 13.0, .7), (20.8, 13.0, .85), (19.4, 13.0, .85)))
    gas += cilindro(20.4, 12.1, .1, 1.1, 1.7, "sfiato")
    gas.append(richiamo(20.1, 12.4, 2.3, True))
    g.append(parte("cabina-gas", "statistiche", gas))
    return "\n".join(g)


def main() -> None:
    svg = (f'<svg class="scena-svg" viewBox="0 0 {W} {H}" role="group" aria-labelledby="scena-titolo" '
           f'xmlns="http://www.w3.org/2000/svg">\n<title id="scena-titolo">Un edificio a piastra e torre, aperto in spaccato, con '
           f'i suoi impianti, le reti che lo alimentano, il territorio intorno, il radar e la stazione meteo e il cielo sopra: '
           f'ogni parte porta a un gruppo di pagine</title>\n{disegno()}\n</svg>\n')
    Path(__file__).with_name("scena_home.svg").write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
