"""Regioni, province e comuni dei file di mappa del sito (fase5-sito/sito/dati/mappa, ISTAT 1/1/2026, generalizzati).

I percorsi SVG sono in UTM 32N scalato (come fase 3, meteo_storico/comuni.py e confini_gl.js): x = S·E + AX, y = −S·N + AY.
Qui servono:
  - le posizioni (baricentro dell'anello più grande, in lon/lat) per gli istogrammi della pagina;
  - i codici e i nomi per abbinare i dati ISPRA e ISTAT (i comuni sardi delle mappe hanno ancora i codici vecchi
    090/091/092/095/111, ISPRA e ISTAT quelli delle province 112–119: si abbinano per nome normalizzato);
  - i poligoni dei comuni (shapely, facoltativo) per l'incrocio con le carte raster (agricolo.py).
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path

S, AX, AY = 0.0010012596459353985, -313.67365575107954, 5226.851664605516

# nomi che ISPRA o ISTAT scrivono diversamente dalle mappe del sito (chiave e valore già normalizzati)
ALIAS = {
    "valle d aosta": "valle d aosta vallee d aoste",
    "trentino alto adige": "trentino alto adige sudtirol",
    "bolzano": "bolzano bozen",
    "bolzano bozen": "bolzano bozen",
    "aosta": "valle d aosta vallee d aoste",
    "massa carrara": "massa carrara",
    "reggio di calabria": "reggio calabria",
    "forli cesena": "forli cesena",
}


def norm(s: str) -> str:
    """Nome normalizzato: minuscolo, senza accenti né segni (Forlì-Cesena → «forli cesena»), con gli alias."""
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z]+", " ", s).strip()
    return ALIAS.get(s, s)


def norm_comune(s: str) -> str:
    """Per i comuni: niente alias, solo la parte prima della barra («Bolzano/Bozen» → «bolzano»)."""
    s = str(s or "").split("/")[0]
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]+", " ", s).strip()


def _utm_lonlat(E: float, N: float) -> tuple[float, float]:
    a, f, k0, l0 = 6378137.0, 1 / 298.257223563, 0.9996, math.radians(9)
    e2 = f * (2 - f); ep2 = e2 / (1 - e2)
    x = E - 500000; M = N / k0
    mu = M / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    f1 = (mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu) + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
          + (151 * e1 ** 3 / 96) * math.sin(6 * mu) + (1097 * e1 ** 4 / 512) * math.sin(8 * mu))
    s, c, t = math.sin(f1), math.cos(f1), math.tan(f1)
    C1, T1 = ep2 * c * c, t * t
    N1 = a / math.sqrt(1 - e2 * s * s); R1 = a * (1 - e2) / (1 - e2 * s * s) ** 1.5; D = x / (N1 * k0)
    lat = f1 - (N1 * t / R1) * (D * D / 2 - (5 + 3 * T1 + 10 * C1 - 4 * C1 * C1 - 9 * ep2) * D ** 4 / 24
                                + (61 + 90 * T1 + 298 * C1 + 45 * T1 * T1 - 252 * ep2 - 3 * C1 * C1) * D ** 6 / 720)
    lon = l0 + (D - (1 + 2 * T1 + C1) * D ** 3 / 6 + (5 - 2 * C1 + 28 * T1 - 3 * C1 * C1 + 8 * ep2 + 24 * T1 * T1) * D ** 5 / 120) / c
    return math.degrees(lon), math.degrees(lat)


def anelli(d: str) -> list[list[tuple[float, float]]]:
    out = []
    for parte in d.split("M"):
        p = parte.replace("Z", "").strip()
        if not p:
            continue
        pts = [tuple(map(float, q.split(","))) for q in p.split("L") if "," in q]
        if len(pts) >= 3:
            out.append(pts)
    return out


def centro(d: str) -> tuple[float, float]:
    """Baricentro dell'anello più grande del percorso SVG, in lon/lat (4 decimali)."""
    meglio, area_max = None, -1.0
    for pts in anelli(d):
        A = cx = cy = 0.0
        for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
            cr = x0 * y1 - x1 * y0
            A += cr; cx += (x0 + x1) * cr; cy += (y0 + y1) * cr
        if abs(A) > area_max and A != 0:
            area_max, meglio = abs(A), (cx / (3 * A), cy / (3 * A))
    x, y = meglio
    lon, lat = _utm_lonlat((x - AX) / S, (AY - y) / S)
    return round(lon, 4), round(lat, 4)


def carica(mappa: Path, comuni: bool = False) -> dict:
    """{"regioni": {cod: {cod, nome, lon, lat}}, "province": {cod3: {cod, sigla, nome, regione, lon, lat}},
        "comuni": {istat: {istat, nome, prov (sigla), regione, d?}}} dai file della mappa del sito.
    I comuni (senza percorso, salvo comuni=True) servono all'abbinamento dei codici."""
    italia = json.loads((Path(mappa) / "italia.json").read_text(encoding="utf-8"))
    regioni, province, com = {}, {}, {}
    for r in italia["regioni"]:
        if not re.fullmatch(r"\d\d", r["cod"]) or not 1 <= int(r["cod"]) <= 20:
            continue
        lon, lat = centro(r["d"])
        regioni[r["cod"]] = {"cod": r["cod"], "nome": r["nome"], "lon": lon, "lat": lat}
    for cod in regioni:
        m = json.loads((Path(mappa) / f"{cod}.json").read_text(encoding="utf-8"))
        for p in m.get("province", []):
            lon, lat = centro(p["d"])
            province[p["cod"]] = {"cod": p["cod"], "sigla": p["sigla"], "nome": p["nome"], "regione": cod, "lon": lon, "lat": lat}
        for c in m.get("comuni", []):
            v = {"istat": c["istat"], "nome": c["nome"], "prov": c["prov"], "regione": cod}
            if comuni:
                v["d"] = c["d"]
            com[c["istat"]] = v
    return {"regioni": regioni, "province": province, "comuni": com}


def abbina_comuni(codici_nomi: dict[str, tuple[str, str]], mappa_comuni: dict) -> tuple[dict, list]:
    """codici_nomi: {pro_com della fonte: (nome, cod_regione a 2 cifre)} → ({pro_com: istat della mappa}, non abbinati).
    Prima per codice; poi, solo nella stessa regione, per nome normalizzato (i 377 comuni sardi)."""
    per_nome: dict = {}
    for istat, c in mappa_comuni.items():
        per_nome.setdefault((c["regione"], norm_comune(c["nome"])), []).append(istat)
    usati = set()
    out, mancano = {}, []
    for pc, (nome, reg) in codici_nomi.items():
        if pc in mappa_comuni and norm_comune(mappa_comuni[pc]["nome"]) == norm_comune(nome):
            out[pc] = pc; usati.add(pc)
    for pc, (nome, reg) in codici_nomi.items():
        if pc in out:
            continue
        cand = [i for i in per_nome.get((reg, norm_comune(nome)), []) if i not in usati]
        if len(cand) == 1:
            out[pc] = cand[0]; usati.add(cand[0])
        elif pc in mappa_comuni and pc not in usati:          # stesso codice, nome scritto diversamente
            out[pc] = pc; usati.add(pc)
        else:
            mancano.append(pc)
    return out, mancano


def poligoni_comuni(mappa: Path):
    """[(istat, regione, poligono shapely in coordinate SVG)] per l'incrocio con i raster (serve shapely)."""
    from shapely.geometry import Polygon
    out = []
    m = carica(mappa, comuni=True)
    for istat, c in m["comuni"].items():
        g = None
        for pts in anelli(c["d"]):
            p = Polygon(pts)
            if not p.is_valid:
                p = p.buffer(0)
            g = p if g is None else g.symmetric_difference(p)      # pari e dispari: gli anelli interni sono buchi
        if g is not None and not g.is_empty:
            out.append((istat, c["regione"], g))
    return out
