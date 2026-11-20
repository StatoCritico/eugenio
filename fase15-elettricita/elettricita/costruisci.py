"""File del sito per la pagina «Produzione e consumi di elettricità» (Statistiche, 20/11/2026).

  costruisci(raw: Path, uscita: Path, mappa: Path | None = None) -> dict
      legge <raw>/<dataset>_<anno>.json scritti da terna_dc.scarica e scrive in `uscita`:
        italia.json   regioni (valori per anno e voce), voci e colori, anni, obiettivi del burden sharing
        RR.json       province della regione RR (stesse grandezze; per il Trentino-Alto Adige anche gli obiettivi di
                      Bolzano e Trento)
      `mappa` è la cartella dati/mappa del sito (posizioni di regioni e province, ISTAT 2026); se manca, la
      cartella «mappa» accanto a `uscita`.
      Il worker lo chiama in una cartella nuova e la pubblica con _pubblica (fase 4) solo se il controllo passa.

Decisione di Paolo (20/11/2026): i dati di Terna si caricano sul sito per le elaborazioni ma **non sono scaricabili**;
si possono scaricare al più le immagini delle elaborazioni (mappa, grafici).

Grandezze (tutte lorde, come le pubblica Terna; valori per provincia sommati per la regione):
  capacita    potenza efficiente lorda [MW] per fonte (dal 2000)
  produzione  produzione lorda [GWh] per fonte (dal 2000)
  richiesta   richiesta di energia elettrica per regione [GWh] per fonte di copertura (dal 2005; solo regioni)
  consumi     consumi [GWh] per settore, per regione e provincia (dal 2000)
Le fonti separano il termoelettrico tradizionale dalle bioenergie (termoelettrico − bioenergie) e i pompaggi
dall'idrico rinnovabile (idrico − idrico rinnovabile), come fa Terna nella copertura della domanda.

Burden sharing: DM MASE 21 giugno 2024 (aree idonee, GU n. 153 del 2/7/2024), art. 2, Tabella A: potenza aggiuntiva
minima da fonti rinnovabili rispetto al 31/12/2020, per regione e provincia autonoma, anno per anno dal 2021 al 2030
(80 GW in tutto). La sentenza del TAR Lazio n. 9155 del 13/5/2025 ha annullato l'art. 7, commi 2 e 3 (criteri delle
aree idonee), non la Tabella A. Il confronto di EuGEnio usa la variazione della potenza efficiente lorda rinnovabile di
Terna rispetto al 2020: è una stima (il decreto conta la potenza nominale dei nuovi impianti e dei potenziamenti).

  python -m elettricita.costruisci <raw> <uscita> <cartella dati/mappa>
"""
from __future__ import annotations

import json
import math
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

FONTE = ("Terna S.p.A. – Dati statistici sull'energia elettrica in Italia (dati.terna.it, Download Center); "
         "elaborazione EuGEnio")

# voci e colori (fonti: i colori delle pagine della generazione di Terna; gli altri scelti da EuGEnio)
VOCI = {
    "capacita": [
        ("termo", "Termoelettrico tradizionale", "#8a8f99"),
        ("bio", "Bioenergie", "#f0912a"),
        ("idro", "Idrico rinnovabile", "#7cc7e0"),
        ("pomp", "Pompaggio puro", "#2e7fb8"),
        ("geo", "Geotermico", "#d4561c"),
        ("eol", "Eolico", "#a9c641"),
        ("fv", "Fotovoltaico", "#f7cb15"),
        ("acc", "Accumuli stand alone", "#8e6bbf"),
    ],
    "produzione": [
        ("termo", "Termoelettrico tradizionale", "#8a8f99"),
        ("bio", "Bioenergie", "#f0912a"),
        ("idro", "Idrico rinnovabile", "#7cc7e0"),
        ("pomp", "Pompaggi", "#2e7fb8"),
        ("geo", "Geotermico", "#d4561c"),
        ("eol", "Eolico", "#a9c641"),
        ("fv", "Fotovoltaico", "#f7cb15"),
        ("acc", "Accumuli stand alone", "#8e6bbf"),
    ],
    "richiesta": [
        ("termo", "Termoelettrico tradizionale", "#8a8f99"),
        ("bio", "Bioenergie", "#f0912a"),
        ("idro", "Idrico rinnovabile", "#7cc7e0"),
        ("pomp", "Pompaggi", "#2e7fb8"),
        ("geo", "Geotermico", "#d4561c"),
        ("eol", "Eolico", "#a9c641"),
        ("fv", "Fotovoltaico", "#f7cb15"),
        ("acc", "Accumuli stand alone", "#8e6bbf"),
        ("saldo", "Saldo con le altre regioni e l'estero", "#c7a0c0"),
    ],
    "consumi": [
        ("ind", "Industria", "#5b6c8f"),
        ("ser", "Servizi", "#4fa3a5"),
        ("dom", "Domestico", "#e07a5f"),
        ("agr", "Agricoltura", "#81b29a"),
    ],
}
UNITA = {"capacita": "MW", "produzione": "GWh", "richiesta": "GWh", "consumi": "GWh"}
FER = ["bio", "idro", "geo", "eol", "fv"]          # fonti rinnovabili per il burden sharing

# DM 21/6/2024, Tabella A: obiettivi di potenza aggiuntiva [MW] 2021…2030 (cumulati rispetto al 31/12/2020)
TABELLA_A = {
    "Abruzzo": [4, 65, 196, 454, 640, 850, 1086, 1350, 1648, 2092],
    "Basilicata": [145, 204, 329, 543, 748, 973, 1218, 1486, 1779, 2105],
    "Calabria": [45, 95, 210, 549, 857, 1206, 1603, 2055, 2568, 3173],
    "Campania": [74, 237, 569, 909, 1297, 1728, 2206, 2736, 3325, 3976],
    "Emilia-Romagna": [100, 343, 860, 1288, 1851, 2504, 3263, 4143, 5164, 6330],
    "Friuli-Venezia Giulia": [30, 96, 321, 404, 573, 772, 1006, 1280, 1603, 1960],
    "Lazio": [82, 305, 544, 933, 1346, 1829, 2396, 3059, 3835, 4757],
    "Liguria": [29, 80, 122, 198, 281, 382, 504, 653, 834, 1059],
    "Lombardia": [184, 622, 1521, 1963, 2714, 3592, 4616, 5812, 7208, 8766],
    "Marche": [32, 110, 241, 457, 679, 930, 1217, 1544, 1916, 2346],
    "Molise": [2, 38, 59, 175, 273, 383, 509, 651, 812, 1003],
    "Piemonte": [78, 285, 851, 1098, 1541, 2053, 2645, 3330, 4121, 4991],
    "Puglia": [163, 507, 876, 1672, 2405, 3213, 4104, 5084, 6165, 7387],
    "Sardegna": [34, 175, 468, 998, 1553, 2207, 2980, 3892, 4969, 6264],
    "Sicilia": [144, 473, 952, 1842, 2764, 3847, 5120, 6616, 8375, 10485],
    "Toscana": [42, 150, 359, 667, 1019, 1444, 1958, 2580, 3332, 4250],
    "Bolzano/Bozen": [11, 41, 120, 139, 186, 239, 298, 364, 438, 515],
    "Trento": [11, 41, 108, 140, 195, 258, 333, 419, 520, 631],
    "Umbria": [15, 60, 135, 279, 429, 609, 823, 1079, 1384, 1756],
    "Valle d'Aosta": [1, 4, 10, 27, 47, 75, 112, 162, 231, 328],
    "Veneto": [125, 413, 1088, 1373, 1889, 2483, 3164, 3947, 4847, 5828],
}
ANNI_OBIETTIVI = list(range(2021, 2031))

# province storiche di Terna che non sono nei confini ISTAT 2026: posizione indicativa (lon, lat) per le barre
STORICHE = {
    "carbonia iglesias": ("Carbonia-Iglesias", 8.62, 39.20),
    "olbia tempio": ("Olbia-Tempio", 9.35, 40.85),
    "sud sardegna": ("Sud Sardegna", 8.85, 39.40),
}
ALIAS = {"aosta": "valle d aosta vallee d aoste", "reggio di calabria": "reggio calabria", "forli cesena": "forli cesena"}


def norm(s: str) -> str:
    s = s or ""
    try:                                     # «ForlÃ¬» (UTF-8 letto come Latin-1 nei dati di Terna) → «Forlì»
        s2 = s.encode("latin-1").decode("utf-8")
        s = s2
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z]+", " ", s).strip()
    return ALIAS.get(s, s)


def ripara(s: str) -> str:
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


# ---- posizioni dai file della mappa del sito (percorsi SVG in UTM 32N scalato, come confini_gl.js) ----
S, AX, AY = 0.0010012596459353985, -313.67365575107954, 5226.851664605516


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


def _centro(d: str) -> tuple[float, float]:
    """Baricentro dell'anello più grande del percorso SVG, in lon/lat (4 decimali)."""
    meglio, area_max = None, -1.0
    for parte in d.split("M"):
        p = parte.replace("Z", "").strip()
        if not p:
            continue
        pts = [tuple(map(float, q.split(","))) for q in p.split("L") if "," in q]
        if len(pts) < 3:
            continue
        A = cx = cy = 0.0
        for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
            cr = x0 * y1 - x1 * y0
            A += cr; cx += (x0 + x1) * cr; cy += (y0 + y1) * cr
        if abs(A) > area_max and A != 0:
            area_max, meglio = abs(A), (cx / (3 * A), cy / (3 * A))
    x, y = meglio
    lon, lat = _utm_lonlat((x - AX) / S, (AY - y) / S)
    return round(lon, 4), round(lat, 4)


def posizioni(mappa: Path) -> tuple[dict, dict]:
    """regioni: nome normalizzato → {cod, nome, lon, lat}; province: nome normalizzato → {cod, sigla, nome, regione, …}."""
    italia = json.loads((mappa / "italia.json").read_text(encoding="utf-8"))
    regioni = {}
    for r in italia["regioni"]:
        if not re.fullmatch(r"\d\d", r["cod"]) or not 1 <= int(r["cod"]) <= 20:
            continue
        lon, lat = _centro(r["d"])
        regioni[norm(r["nome"])] = {"cod": r["cod"], "nome": r["nome"], "lon": lon, "lat": lat}
    province = {}
    for r in regioni.values():
        m = json.loads((mappa / f"{r['cod']}.json").read_text(encoding="utf-8"))
        for p in m.get("province", []):
            lon, lat = _centro(p["d"])
            province[norm(p["nome"])] = {"cod": p["cod"], "sigla": p["sigla"], "nome": p["nome"], "regione": r["cod"],
                                         "lon": lon, "lat": lat}
    # nomi di Terna diversi da quelli ISTAT 2026
    for k, v in list(regioni.items()):
        if k.startswith("valle d aosta"):
            regioni["valle d aosta"] = v
        if k.startswith("trentino"):
            regioni["trentino alto adige"] = v
    return regioni, province


# ---- lettura dei file di Terna ----
def _righe(raw: Path, ds: str):
    for f in sorted(raw.glob(f"{ds}_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        cols = list(d["Columns"])
        for r in d["Data"]:
            riga = dict(zip(cols, r))
            riga["_v"] = r[-1] if r else None          # il valore è sempre l'ultima colonna (MW o GWh)
            yield riga


def _val(r: dict, chiave: str) -> float:
    v = r.get(chiave)
    return float(v) if isinstance(v, (int, float)) else 0.0


def leggi(raw: Path) -> dict:
    """{grandezza: {(regione, provincia|None): {anno: {voce: valore}}}} con i nomi di Terna (riparati)."""
    T: dict = {g: defaultdict(lambda: defaultdict(lambda: defaultdict(float))) for g in VOCI}

    def add(g, reg, prov, anno, voce, v):
        T[g][(ripara(reg), ripara(prov) if prov else None)][int(anno)][voce] += v

    # Righe doppie: in alcuni anni Terna ripete la stessa chiave (regione, provincia, fonte) con due valori diversi (2017:
    # +16 GW di termoelettrico rispetto al 2016 e al 2018) o con un valore e un vuoto. Per ogni chiave si tiene il valore
    # più alto non vuoto; per il termoelettrico si prende il minore tra «Impianti di generazione» e la somma della
    # «Termoelettrica» per categoria (che fino al 2024 conta anche il geotermico toscano e nel 2017 non ha i doppioni).
    def unico(ds, filtro, chiave, campo):
        out: dict = {}
        for r in _righe(raw, ds):
            if not filtro(r):
                continue
            k = chiave(r)
            v = r.get(campo)
            if isinstance(v, (int, float)):
                out[k] = max(out.get(k, float("-inf")), float(v))
        return defaultdict(float, out)

    lorda_c = lambda r: r["Tipo capacità"] == "Lorda"
    lorda_p = lambda r: r["Tipo produzione"] == "Lorda"
    gp = unico("GenerationPlants", lorda_c, lambda r: (r["Regione"], r["Provincia"], r["Anno"], r["Fonte"].lower()), "_v")
    crs = unico("CapacityRenewableSources", lorda_c, lambda r: (r["Regione"], r["Provincia"], r["Anno"], r["Fonti"].lower()), "_v")
    ct = unico("CapacityThermal", lorda_c, lambda r: (r["Regione"], r["Provincia"], r["Anno"], r["Categoria"], r["Sottocategoria"]), "_v")
    termo_ct: dict = defaultdict(float)
    for (reg, prov, anno, _c, _s), v in ct.items():
        termo_ct[(reg, prov, anno)] += v
    for (reg, prov, anno), v in termo_ct.items():
        k = (reg, prov, anno, "termoelettrico")
        if k in gp:
            gp[k] = min(gp[k], v)
    _fonti(T, "capacita", gp, crs, add)
    ebs = unico("ElectricityBySource", lorda_p, lambda r: (r["Regione"], r["Provincia"], r["Anno"], r["Fonte"].lower()), "_v")
    prs = unico("ProductionRenewableSources", lorda_p, lambda r: (r["Regione"], r["Provincia"], r["Anno"], r["Fonte rinnovabile"].lower()), "_v")
    _fonti(T, "produzione", ebs, prs, add)
    # richiesta per regione: copertura della domanda per fonte
    mappa_cop = {"termoelettrico tradizionale": "termo", "bioenergie": "bio", "idrico rinnovabile": "idro",
                 "pompaggi": "pomp", "idrico tradizionale": "pomp", "geotermoelettrico": "geo", "eolico": "eol", "fotovoltaico": "fv",
                 "accumulo stand alone": "acc", "saldo import/export": "saldo"}
    for r in _righe(raw, "ConsumptionBySource"):
        voce = mappa_cop.get(r["Fonte"].lower())
        if voce:
            add("richiesta", r["Regione"], None, r["Anno"], voce, _val(r, "_v"))
    # consumi per settore (negli anni fino al 2023 Terna dà più righe per provincia e settore, una per attività: si sommano)
    mappa_set = {"industria": "ind", "servizi": "ser", "domestico": "dom", "agricoltura": "agr"}
    for r in _righe(raw, "ElectricalEnergy"):
        voce = mappa_set.get(r["Settore"].lower())
        if voce:
            add("consumi", r["Regione"], r["Provincia"], r["Anno"], voce, _val(r, "_v"))
    return T


def _fonti(T, g, tutte, rinn, add):
    chiavi = {k[:3] for k in tutte} | {k[:3] for k in rinn}
    for reg, prov, anno in chiavi:
        t = lambda f: tutte.get((reg, prov, anno, f), 0.0)
        r = lambda f: rinn.get((reg, prov, anno, f), 0.0)
        bio = r("bioenergie")
        add(g, reg, prov, anno, "termo", max(0.0, t("termoelettrico") - bio))
        add(g, reg, prov, anno, "bio", bio)
        idro_r = r("idrico")
        add(g, reg, prov, anno, "idro", idro_r)
        add(g, reg, prov, anno, "pomp", max(0.0, t("idrico") - idro_r))
        add(g, reg, prov, anno, "geo", max(t("geotermoelettrico"), r("geotermoelettrico")))
        add(g, reg, prov, anno, "eol", max(t("eolico"), r("eolico")))
        add(g, reg, prov, anno, "fv", max(t("fotovoltaico"), r("fotovoltaico")))
        add(g, reg, prov, anno, "acc", t("accumulo stand alone"))


# ---- scrittura ----
def _arr(valori: dict, g: str) -> list:
    return [round(valori.get(k, 0.0), 1) for k, _, _ in VOCI[g]]


def costruisci(raw: Path, uscita: Path, mappa: Path | None = None) -> dict:
    mappa = mappa or uscita.parent / "mappa"     # nel worker: SITO_DATI/.elettricita_nuova → SITO_DATI/mappa
    regioni_pos, province_pos = posizioni(mappa)
    T = leggi(raw)
    uscita.mkdir(parents=True, exist_ok=True)
    anni = {g: sorted({a for serie in T[g].values() for a in serie}) for g in VOCI}

    # regioni: somma delle province (richiesta: già per regione)
    per_regione: dict = {g: defaultdict(lambda: defaultdict(lambda: defaultdict(float))) for g in VOCI}
    per_provincia: dict = defaultdict(lambda: {g: {} for g in VOCI})   # (cod_regione, nome provincia) → …
    sconosciute = set()
    for g in VOCI:
        for (reg, prov), serie in T[g].items():
            rp = regioni_pos.get(norm(reg))
            if not rp:
                sconosciute.add(reg)
                continue
            for anno, v in serie.items():
                for voce, x in v.items():
                    per_regione[g][rp["cod"]][anno][voce] += x
            if prov:
                per_provincia[(rp["cod"], prov)][g] = serie
    if sconosciute:
        raise ValueError(f"regioni di Terna non riconosciute: {sorted(sconosciute)}")

    obiettivi = {}
    for nome, valori in TABELLA_A.items():
        cod = "04" if nome in ("Bolzano/Bozen", "Trento") else regioni_pos[norm(nome)]["cod"]
        obiettivi.setdefault(cod, [0] * 10)
        obiettivi[cod] = [a + b for a, b in zip(obiettivi[cod], valori)]

    regioni_out = []
    for rp in sorted({v["cod"]: v for v in regioni_pos.values()}.values(), key=lambda x: x["cod"]):
        cod = rp["cod"]
        voce = {"cod": cod, "nome": rp["nome"], "lon": rp["lon"], "lat": rp["lat"]}
        for g in VOCI:
            voce[g] = {str(a): _arr(per_regione[g][cod].get(a, {}), g) for a in anni[g] if a in per_regione[g][cod]}
        voce["obiettivi"] = obiettivi.get(cod)
        regioni_out.append(voce)

    voci_out = {g: [{"id": k, "nome": n, "colore": c} for k, n, c in VOCI[g]] for g in VOCI}
    comune = {"fonte": FONTE, "unita": UNITA, "voci": voci_out, "fer": FER, "anni": anni,
              "obiettivi_anni": ANNI_OBIETTIVI, "obiettivi_base": 2020,
              "obiettivi_fonte": "DM MASE 21 giugno 2024 (aree idonee), art. 2, Tabella A (GU n. 153 del 2/7/2024)"}
    (uscita / "italia.json").write_text(json.dumps({**comune, "regioni": regioni_out}, ensure_ascii=False,
                                                   separators=(",", ":")), encoding="utf-8")

    # province per regione
    dimensioni = {}
    non_trovate = set()
    for rp in {v["cod"]: v for v in regioni_pos.values()}.values():
        cod = rp["cod"]
        prov_out = []
        for (c, nome), dati in sorted(per_provincia.items()):
            if c != cod:
                continue
            pp = province_pos.get(norm(nome))
            storica = None
            if not pp:
                s = STORICHE.get(norm(nome))
                if not s:
                    non_trovate.add(nome)
                    continue
                storica = {"cod": None, "sigla": None, "nome": s[0], "lon": s[1], "lat": s[2]}
            pos = pp or storica
            voce = {"cod": pos["cod"], "sigla": pos["sigla"], "nome": pos["nome"] if pp else storica["nome"],
                    "nome_terna": nome, "lon": pos["lon"], "lat": pos["lat"], "storica": bool(storica)}
            for g in VOCI:
                serie = dati.get(g) or {}
                voce[g] = {str(a): _arr(v, g) for a, v in sorted(serie.items())}
            if cod == "04" and pp:
                tab = TABELLA_A.get("Bolzano/Bozen" if pp["sigla"] == "BZ" else "Trento")
                voce["obiettivi"] = tab
            prov_out.append(voce)
        # stessa provincia con nomi diversi negli anni (es. «Pesaro E Urbino» e «Pesaro e Urbino»): si uniscono
        unite: dict = {}
        for p in prov_out:
            k = (p["cod"], p["nome"])
            if k not in unite:
                unite[k] = p
                continue
            for g in VOCI:
                for a, v in p[g].items():
                    prima = unite[k][g].get(a)
                    unite[k][g][a] = [round(x + y, 1) for x, y in zip(prima, v)] if prima else v
        prov_out = sorted(unite.values(), key=lambda p: p["nome"])
        f = uscita / f"{cod}.json"
        f.write_text(json.dumps({**comune, "regione": cod, "nome": rp["nome"], "province": prov_out}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        dimensioni[f.name] = f.stat().st_size
    if non_trovate:
        raise ValueError(f"province di Terna senza posizione: {sorted(non_trovate)}")
    dimensioni["italia.json"] = (uscita / "italia.json").stat().st_size
    return {"anni": anni, "dimensioni": dimensioni}


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    esito = costruisci(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
    print(json.dumps(esito, indent=1))


if __name__ == "__main__":
    main()
