"""Disegno della pagina iniziale (22/11/2026): un edificio in assonometria con le reti che lo alimentano, il territorio
intorno e il meteo sopra. Scrive parti/scena_home.svg, che costruisci_pagine.py mette in index.html (blocco
<!-- scena-home -->). Si rilancia solo quando si cambia il disegno:

    python parti/scena_home.py

Ogni parte che si può indicare è un <g class="parte" data-gruppo="…"> (gruppi del menu: clima, patrimonio, edificio,
aria, cogenerazione, fotovoltaico, statistiche). I colori sono classi (sc-…) definite in stile.css, con le varianti per
l'inverno (.inverno sulla scena) e per il tema chiaro; le animazioni (pioggia, neve, fumo, nuvole) sono in CSS e si
fermano con prefers-reduced-motion."""
from __future__ import annotations

import math
from pathlib import Path

W, H = 960, 720
CX, CY, S = 480, 175, 24.0         # origine e scala dell'assonometria
C30, S30 = math.cos(math.radians(30)), math.sin(math.radians(30))


def iso(x: float, y: float, z: float = 0.0) -> tuple[float, float]:
    return CX + (x - y) * C30 * S, CY + (x + y) * S30 * S - z * S


def pts(*p3) -> str:
    return " ".join(f"{a:.1f},{b:.1f}" for a, b in (iso(*p) for p in p3))


def poli(cls: str, *p3, extra: str = "") -> str:
    return f'<polygon class="{cls}" points="{pts(*p3)}"{extra}/>'


def scatola(x0, y0, x1, y1, h, cls="muro", z0=0.0) -> list[str]:
    """Parallelepipedo: facce visibili (y=y1 a sinistra, x=x1 a destra, sopra)."""
    return [
        poli(f"sc-{cls}-sx", (x0, y1, z0), (x1, y1, z0), (x1, y1, z0 + h), (x0, y1, z0 + h)),
        poli(f"sc-{cls}-dx", (x1, y0, z0), (x1, y1, z0), (x1, y1, z0 + h), (x1, y0, z0 + h)),
        poli(f"sc-{cls}-su", (x0, y0, z0 + h), (x1, y0, z0 + h), (x1, y1, z0 + h), (x0, y1, z0 + h)),
    ]


def finestre(x0, y0, x1, y1, piani, h_piano, z0=0.0, passo=1.0) -> list[str]:
    out = []
    for p in range(piani):
        z = z0 + p * h_piano + 0.9
        y = y0 + 0.35
        while y + 0.55 <= y1 - 0.2:          # facciata destra (x = x1)
            out.append(poli("sc-vetro", (x1, y, z), (x1, y + 0.55, z), (x1, y + 0.55, z + 1.0), (x1, y, z + 1.0)))
            y += passo
        x = x0 + 0.35
        while x + 0.55 <= x1 - 0.2:          # facciata sinistra (y = y1)
            out.append(poli("sc-vetro", (x, y1, z), (x + 0.55, y1, z), (x + 0.55, y1, z + 1.0), (x, y1, z + 1.0)))
            x += passo
    return out


def casa(x0, y0, x1, y1, h, r=1.2) -> list[str]:
    ym = (y0 + y1) / 2
    out = scatola(x0, y0, x1, y1, h, "casa")
    out += [
        poli("sc-tetto-sx", (x0, y1, h), (x1, y1, h), (x1, ym, h + r), (x0, ym, h + r)),
        poli("sc-tetto-dx", (x1, y0, h), (x1, y1, h), (x1, ym, h + r)),
        poli("sc-neve", (x0, y1, h), (x1, y1, h), (x1, ym, h + r), (x0, ym, h + r)),
    ]
    out.append(poli("sc-vetro", (x1, y0 + 0.5, 0.6), (x1, y0 + 1.0, 0.6), (x1, y0 + 1.0, 1.4), (x1, y0 + 0.5, 1.4)))
    return out


def albero(x, y, h=1.6, r=0.9) -> list[str]:
    bx, by = iso(x, y, 0)
    tx, ty = iso(x, y, h)
    rr = r * S
    return [
        f'<line class="sc-tronco" x1="{bx:.1f}" y1="{by:.1f}" x2="{tx:.1f}" y2="{ty:.1f}"/>',
        f'<ellipse class="sc-chioma" cx="{tx:.1f}" cy="{ty - rr * .55:.1f}" rx="{rr:.1f}" ry="{rr * 1.05:.1f}"/>',
        f'<ellipse class="sc-neve" cx="{tx:.1f}" cy="{ty - rr * 1.05:.1f}" rx="{rr * .8:.1f}" ry="{rr * .45:.1f}"/>',
    ]


def traliccio(x, y, h=6.2) -> tuple[list[str], tuple[float, float]]:
    b1, b2 = iso(x - 0.35, y + 0.35, 0), iso(x + 0.35, y - 0.35, 0)
    t = iso(x, y, h)
    m1, m2 = iso(x - 0.2, y + 0.2, h * .55), iso(x + 0.2, y - 0.2, h * .55)
    a1, a2 = iso(x - 0.9, y + 0.9, h * .85), iso(x + 0.9, y - 0.9, h * .85)
    seg = lambda p, q: f'<line class="sc-ferro" x1="{p[0]:.1f}" y1="{p[1]:.1f}" x2="{q[0]:.1f}" y2="{q[1]:.1f}"/>'
    out = [seg(b1, t), seg(b2, t), seg(b1, m2), seg(b2, m1), seg(m1, m2), seg(a1, a2)]
    return out, a2


def campo(x0, y0, x1, y1, righe=5) -> list[str]:
    out = [poli("sc-campo", (x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    for i in range(1, righe):
        y = y0 + (y1 - y0) * i / righe
        a, b = iso(x0, y), iso(x1, y)
        out.append(f'<line class="sc-solco" x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}"/>')
    out.append(poli("sc-particella", (x0, y0), (x1, y0), (x1, y1), (x0, y1)))
    out.append(poli("sc-neve sc-neve-campo", (x0, y0), (x1, y0), (x1, y1), (x0, y1)))
    return out


def parte(gruppo: str, titolo: str, corpo: list[str]) -> str:
    return (f'<g class="parte" data-gruppo="{gruppo}" tabindex="0" role="button" aria-label="{titolo}">\n  '
            + "\n  ".join(corpo) + "\n</g>")


def disegno() -> str:
    g = []
    # ---------------------------------------------------------------- cielo e meteo (clima)
    cielo = [f'<rect class="sc-cielo" x="0" y="0" width="{W}" height="{H}"/>']
    sole = ['<g class="sc-sole">',
            '<g class="sc-raggi">' + "".join(
                f'<line x1="{170 + 52 * math.cos(a):.1f}" y1="{100 + 52 * math.sin(a):.1f}" '
                f'x2="{170 + 70 * math.cos(a):.1f}" y2="{100 + 70 * math.sin(a):.1f}"/>'
                for a in (i * math.pi / 6 for i in range(12))) + '</g>',
            '<circle cx="170" cy="100" r="38"/>', '</g>']
    def nuvola(x, y, k=1.0, cls="sc-nuvola"):
        return (f'<g class="{cls}" transform="translate({x} {y}) scale({k})">'
                '<ellipse cx="0" cy="0" rx="62" ry="24"/><ellipse cx="-30" cy="-14" rx="30" ry="24"/>'
                '<ellipse cx="18" cy="-24" rx="36" ry="30"/><ellipse cx="50" cy="-6" rx="26" ry="20"/></g>')
    pioggia = '<g class="sc-pioggia">' + "".join(
        f'<line x1="{x}" y1="{y}" x2="{x - 6}" y2="{y + 18}" style="animation-delay:{(i * .17) % 1:.2f}s"/>'
        for i, (x, y) in enumerate((545 + 22 * (i % 9) + (i // 9) * 9, 115 + 34 * (i // 9)) for i in range(36))) + '</g>'
    neve = '<g class="sc-fiocchi">' + "".join(
        f'<circle cx="{x}" cy="{y}" r="{2.2 + (i % 3) * .8:.1f}" style="animation-delay:{(i * .37) % 3:.2f}s"/>'
        for i, (x, y) in enumerate((40 + (i * 71) % 880, 20 + (i * 53) % 220) for i in range(52))) + '</g>'
    clima = cielo + sole + [nuvola(380, 70, .8, "sc-nuvola sc-nuvola-lenta"), nuvola(610, 95, 1.25), pioggia, neve,
                            nuvola(830, 55, .9, "sc-nuvola sc-nuvola-lenta")]
    g.append(parte("clima", "Clima e meteo", clima))

    # ---------------------------------------------------------------- territorio (patrimonio)
    terr = [poli("sc-terreno", (0, 0), (21, 0), (21, 21), (0, 21)),
            poli("sc-neve sc-neve-terreno", (0, 0), (21, 0), (21, 21), (0, 21)),
            poli("sc-terreno-bordo-sx", (0, 21, 0), (21, 21, 0), (21, 21, -0.8), (0, 21, -0.8)),
            poli("sc-terreno-bordo-dx", (21, 0, 0), (21, 21, 0), (21, 21, -0.8), (21, 0, -0.8)),
            poli("sc-strada", (0, 14.2), (21, 14.2), (21, 15.4), (0, 15.4))]
    terr += campo(0.8, 0.8, 5.6, 5.4) + campo(0.8, 7.0, 5.2, 12.8, 6) + campo(1.0, 16.4, 6.2, 20.4, 4)
    for (x, y) in ((7.2, 1.2), (6.6, 3.4), (6.4, 9.4), (6.6, 12.2), (17.2, 10.2), (19.4, 12.6), (12.4, 18.6), (9.6, 19.4), (15.2, 17.8), (19.6, 17.0), (13.4, 1.6)):
        terr += albero(x, y)
    terr += casa(8.4, 1.4, 10.6, 3.6, 1.8) + casa(16.4, 16.6, 18.6, 18.8, 1.6) + casa(7.6, 16.6, 9.8, 18.6, 1.6)
    g.append(parte("patrimonio", "Territorio", terr))

    # ---------------------------------------------------------------- edificio
    x0, y0, x1, y1, piani, hp = 8.2, 8.0, 12.2, 12.4, 4, 1.7
    h = piani * hp
    edif = scatola(x0, y0, x1, y1, h, "edificio") + finestre(x0, y0, x1, y1, piani, hp)
    ingresso = poli("sc-porta", (x1, 10.0, 0), (x1, 10.9, 0), (x1, 10.9, 1.3), (x1, 10.0, 1.3))
    edif.append(ingresso)
    edif.append(poli("sc-neve", (x0, y0, h), (x1, y0, h), (x1, y1, h), (x0, y1, h)))
    g.append(parte("edificio", "Edifici", edif))

    # pannelli fotovoltaici sul tetto
    fv = []
    for i in range(3):
        xa = x0 + 0.35 + i * 1.05
        fv.append(poli("sc-pannello", (xa, y0 + 2.2, h + .05), (xa + .9, y0 + 2.2, h + .05),
                       (xa + .9, y1 - 0.35, h + .55), (xa, y1 - 0.35, h + .55)))
        fv.append(poli("sc-neve sc-neve-pannello", (xa, y0 + 2.2, h + .05), (xa + .9, y0 + 2.2, h + .05),
                       (xa + .9, y1 - 0.35, h + .55), (xa, y1 - 0.35, h + .55)))
    g.append(parte("fotovoltaico", "Fotovoltaico", fv))

    # unità di trattamento aria sul tetto, con il ventilatore
    uta = scatola(x0 + 0.4, y0 + 0.35, x1 - 0.5, y0 + 1.55, 1.0, "uta", z0=h)
    cx_, cy_ = iso(x1 - 1.4, y0 + 0.95, h + 1.0)
    uta.append(f'<ellipse class="sc-ventola-fondo" cx="{cx_:.1f}" cy="{cy_:.1f}" rx="11" ry="6"/>')
    uta.append(f'<g class="sc-ventola" style="transform-origin:{cx_:.1f}px {cy_:.1f}px">'
               f'<line x1="{cx_ - 9:.1f}" y1="{cy_:.1f}" x2="{cx_ + 9:.1f}" y2="{cy_:.1f}"/>'
               f'<line x1="{cx_:.1f}" y1="{cy_ - 5:.1f}" x2="{cx_:.1f}" y2="{cy_ + 5:.1f}"/></g>')
    for i in range(3):
        yy = y0 + 0.6 + i * 0.3
        a, b = iso(x1 - 0.5, yy, h + .25), iso(x1 - 0.5, yy, h + .8)
        uta.append(f'<line class="sc-griglia" x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}"/>')
    g.append(parte("aria", "Trattamento aria", uta))

    # cogeneratore accanto all'edificio, con il camino e il fumo
    cog = scatola(13.0, 10.2, 14.8, 12.0, 1.4, "cog")
    ca, cb = iso(14.2, 10.7, 1.4), iso(14.2, 10.7, 4.2)
    cog.append(f'<line class="sc-camino" x1="{ca[0]:.1f}" y1="{ca[1]:.1f}" x2="{cb[0]:.1f}" y2="{cb[1]:.1f}"/>')
    cog.append('<g class="sc-fumo">' + "".join(
        f'<circle cx="{cb[0] + 4 * i:.1f}" cy="{cb[1] - 8 - 10 * i:.1f}" r="{5 + 2 * i}" style="animation-delay:{i * .9:.1f}s"/>'
        for i in range(3)) + '</g>')
    g.append(parte("cogenerazione", "Cogenerazione", cog))
    # ---------------------------------------------------------------- reti (statistiche): linea elettrica e gas
    reti = [poli("sc-recinto", (15.6, 2.2), (20.4, 2.2), (20.4, 7.4), (15.6, 7.4))]
    reti += scatola(16.2, 2.8, 18.2, 4.4, 1.6, "cabina")
    reti += scatola(16.4, 5.4, 17.6, 6.6, 1.2, "trafo") + scatola(18.4, 5.4, 19.6, 6.6, 1.2, "trafo")
    # tubo del gas interrato, dal bordo al cogeneratore e all'edificio, con la cabina di riduzione
    a, b, c = iso(21, 12.8), iso(14.8, 12.8), iso(12.3, 12.8)
    reti.append(f'<polyline class="sc-gas" points="{a[0]:.1f},{a[1]:.1f} {b[0]:.1f},{b[1]:.1f} {c[0]:.1f},{c[1]:.1f}"/>')
    reti += scatola(19.4, 12.2, 20.4, 13.4, 0.9, "gas")
    # linea elettrica dalla cabina primaria alla cabina MT/BT dell'edificio
    punte = []
    for (x, y) in ((15.8, 8.8),):
        corpo, punta = traliccio(x, y)
        reti += corpo
        punte.append(punta)
    reti += scatola(12.8, 7.2, 13.7, 8.1, 1.1, "cabina")
    arrivo = iso(13.25, 7.65, 1.1)
    partenza = iso(17.2, 3.6, 1.6)
    catena = [partenza] + punte + [arrivo]
    for p, q in zip(catena, catena[1:]):
        mx, my = (p[0] + q[0]) / 2, max(p[1], q[1]) + 14
        reti.append(f'<path class="sc-filo" d="M{p[0]:.1f},{p[1]:.1f} Q{mx:.1f},{my:.1f} {q[0]:.1f},{q[1]:.1f}"/>')
    g.append(parte("statistiche", "Statistiche: reti e mercati dell'energia", reti))

    return "\n".join(g)


def main() -> None:
    corpo = disegno()
    svg = (f'<svg class="scena-svg" viewBox="0 0 {W} {H}" role="group" aria-labelledby="scena-titolo" '
           f'xmlns="http://www.w3.org/2000/svg">\n<title id="scena-titolo">Un edificio con il territorio intorno, le reti '
           f'che lo alimentano e il meteo sopra: ogni parte porta a un gruppo di pagine</title>\n{corpo}\n</svg>\n')
    (Path(__file__).with_name("scena_home.svg")).write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
