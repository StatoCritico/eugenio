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
  consumi     consumi [GWh] per settore, per regione e provincia (dal 2000), da «Total» (consumi per attività)
              sommato per settore; «ElectricalEnergy» solo per gli anni senza Total. Le differenze tra i due sopra il
              5 % per provincia e anno vanno nel log e nel campo «note» di italia.json.
  emissioni   (21/11/2026) solo per regione, dal 2000, da «GrossVsCO2Emissions»: per combustibile (EMISSIONI_VOCI)
              produzione termoelettrica lorda [GWh], emissioni di CO2 [kt] ed energia primaria stimata [tep] (metodo e
              riferimenti MEF/ISPRA in riferimenti_emissioni.json, copiati in italia.json; vedi energia_primaria()).
              Con le zone di mercato (ZONE, come fase5-sito/costruisci_zone.py) la pagina fa i subtotali per zona.
Anni copiati (22/11/2026): trova_copie() riconosce gli anni di un dataset uguali a un altro anno; non si usano.
Produzione e capacità di quegli anni si ricostruiscono dalle altre tabelle di Terna dello stesso anno
(ricostruisci_produzione, ricostruisci_capacita) o restano vuote; controlla_salti() segnala i totali nazionali che si
scostano di più del 15 % dalla media dell'anno prima e dopo. Tutto nel campo «note» di italia.json, su stderr e in
esito["controlli"].
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

# (21/11/2026) emissioni: combustibili di GrossVsCO2Emissions (nomi di Terna in minuscolo → voce)
EMISSIONI_VOCI = [
    ("gas", "Gas naturale", "gas naturale"),
    ("solidi", "Solidi", "solidi"),
    ("petroliferi", "Petroliferi", "petroliferi"),
    ("altri", "Altri (gas siderurgici e recuperi)", "altri"),
    ("bio", "Bioenergie e altri combustibili", "bioenergie"),
]
RIFERIMENTI = Path(__file__).resolve().parent / "riferimenti_emissioni.json"
# zone di mercato in vigore dal 1/1/2021 (ARERA 103/2019), come fase5-sito/costruisci_zone.py e sito/dati/mappa/zone.json
ZONE = [
    ("NORD", "Nord", ["01", "02", "03", "04", "05", "06", "07", "08"]),
    ("CNOR", "Centro-Nord", ["09", "11"]),
    ("CSUD", "Centro-Sud", ["10", "12", "13", "15"]),
    ("SUD", "Sud", ["14", "16", "17"]),
    ("CALA", "Calabria", ["18"]),
    ("SICI", "Sicilia", ["19"]),
    ("SARD", "Sardegna", ["20"]),
]

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


# ---- anni copiati da un altro anno nel Download Center (22/11/2026) ----
# Nei file di Terna alcuni anni sono la copia di un altro anno con l'anno cambiato: ElectricityBySource 2017 = 2008
# (Italia 319 130 GWh invece di ~295 800), 2006 = 2004, 2007 = valori del 2005 su altre province; GenerationPlants
# 2005 = 2002, 2006 = 2004, 2017 = tutte le righe del 2012 più 113 righe; CapacityRenewableSources 2005 = 2004.
# Tre casi: «identico» (stesse righe tolto l'anno), «contiene» (ha tutte le righe dell'altro anno, che sono almeno l'80 %
# delle sue), «valori» (almeno il 95 % dei valori diversi da zero sono quelli dell'altro anno, su chiavi diverse).
# Negli identici e nei «valori» la copia è l'anno più recente: in tutti i casi trovati l'anno più vecchio coincide con le
# altre tabelle di Terna del suo anno (p. es. ElectricityBySource 2008 = 319 130 GWh, il dato 2008 di Terna).
MIN_RIGHE_COPIA = 20          # sotto questo numero di righe con un valore non si confronta (file di prova, anni vuoti)
QUOTA_CONTIENE = 0.8
QUOTA_VALORI = 0.95


def _file_anni(raw: Path, ds: str) -> dict:
    out = {}
    for f in sorted(raw.glob(f"{ds}_*.json")):
        m = re.fullmatch(re.escape(ds) + r"_(\d{4})\.json", f.name)
        if m:
            out[int(m.group(1))] = f
    return out


def _firma(f: Path, anno: int) -> tuple[frozenset, frozenset, int]:
    """(righe senza la colonna dell'anno, valori diversi da zero arrotondati, righe con un valore diverso da zero)."""
    d = json.loads(f.read_text(encoding="utf-8"))
    cols = list(d["Columns"])
    righe = d["Data"]
    ia = next((i for i, c in enumerate(cols) if c.lower() == "anno"), None)
    if ia is None or any(str(r[ia]) != str(anno) for r in righe if len(r) > ia):
        ia = next((i for i in range(len(cols)) if righe and all(len(r) > i and str(r[i]) == str(anno) for r in righe)), None)
    tuple_ = frozenset(json.dumps([x for j, x in enumerate(r) if j != ia], ensure_ascii=False) for r in righe)
    numeri = [r[-1] for r in righe if r and isinstance(r[-1], (int, float)) and r[-1] != 0]
    return tuple_, frozenset(round(float(x), 3) for x in numeri), len(numeri)


def trova_copie(raw: Path, dataset: list[str] | None = None) -> dict:
    """{dataset: {anno copiato: {"di": anno di origine, "tipo": identico|contiene|valori}}} per i file di `raw`."""
    if dataset is None:
        dataset = sorted({re.sub(r"_\d{4}\.json$", "", f.name) for f in raw.glob("*_*.json")})
    out: dict = {}
    for ds in dataset:
        firme = {a: _firma(f, a) for a, f in _file_anni(raw, ds).items()}
        firme = {a: v for a, v in firme.items() if v[2] >= MIN_RIGHE_COPIA}
        trovate: dict = {}
        for a, (ra, va, _n) in sorted(firme.items()):
            scelta = None
            for b, (rb, vb, _m) in sorted(firme.items()):
                if b == a:
                    continue
                if ra == rb:
                    if a > b:
                        scelta = (b, "identico")
                        break
                    continue
                if rb < ra and len(rb) >= QUOTA_CONTIENE * len(ra):
                    scelta = scelta or (b, "contiene")
                    continue
                if ra < rb:                       # le sue righe sono tutte nell'altro anno: la copia è l'altro
                    continue
                qa, qb = len(va & vb) / len(va), len(va & vb) / len(vb)
                if qa >= QUOTA_VALORI and (a > b or qb < QUOTA_VALORI) and not scelta:
                    scelta = (b, "valori")
            if scelta:
                trovate[a] = {"di": scelta[0], "tipo": scelta[1]}
        if trovate:
            out[ds] = trovate
    return out


def descrivi_copia(ds: str, anno: int, c: dict) -> str:
    come = {"identico": "stesse righe", "contiene": "contiene tutte le righe",
            "valori": "stessi valori su province e fonti diverse"}[c["tipo"]]
    return f"Terna, {ds} {anno}: copia del {c['di']} ({come}); i valori del {anno} non si usano"


# ---- lettura dei file di Terna ----
def _righe(raw: Path, ds: str, salta: dict | None = None):
    """Righe dei file <ds>_<anno>.json; `salta` = {dataset: anni da non leggere} (anni copiati)."""
    via = set((salta or {}).get(ds, ()))
    for a, f in _file_anni(raw, ds).items():
        if a in via:
            continue
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

    # Anni copiati da un altro anno (trova_copie): non si leggono; produzione e capacità si ricostruiscono dalle altre
    # tabelle di Terna dello stesso anno (ricostruisci_produzione, ricostruisci_capacita) o restano vuote.
    copie = trova_copie(raw)
    salta = {ds: set(v) for ds, v in copie.items()}
    note: list[str] = []
    for ds, v in copie.items():
        for anno, c in sorted(v.items()):
            note.append(descrivi_copia(ds, anno, c))

    # Righe doppie: in alcuni anni Terna ripete la stessa chiave (regione, provincia, fonte) con un valore e un vuoto, o
    # con due valori vicini (CapacityRenewableSources 2017–2018). Per ogni chiave si tiene il valore più alto non vuoto;
    # per il termoelettrico si prende il minore tra «Impianti di generazione» e la somma della «Termoelettrica» per
    # categoria (che fino al 2022 conta anche il geotermico toscano). I «+16 GW di termoelettrico» di GenerationPlants
    # 2017 non erano doppioni: il file del 2017 contiene tutte le righe del 2012 (vedi trova_copie).
    def unico(ds, filtro, chiave, campo):
        out: dict = {}
        for r in _righe(raw, ds, salta):
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
    gp, n, vuoti = ricostruisci_capacita(gp, crs, termo_ct, copie.get("GenerationPlants", {}),
                                         copie.get("CapacityRenewableSources", {}), set(copie.get("CapacityThermal", {})))
    note += n
    _fonti(T, "capacita", gp, _togli_anni(crs, vuoti), add)
    ebs = unico("ElectricityBySource", lorda_p, lambda r: (r["Regione"], r["Provincia"], r["Anno"], r["Fonte"].lower()), "_v")
    prs = unico("ProductionRenewableSources", lorda_p, lambda r: (r["Regione"], r["Provincia"], r["Anno"], r["Fonte rinnovabile"].lower()), "_v")
    # ProductionThermal: niente colonna Lorda/Netta, ogni chiave due volte: il valore maggiore è il lordo
    pt_k = unico("ProductionThermal", lambda r: True, lambda r: (r["Regione"], r["Provincia"], r["Anno"], r["Categoria"], r["Sottocategoria"]), "_v")
    pt: dict = defaultdict(float)
    for (reg, prov, anno, _c, _s), v in pt_k.items():
        pt[(reg, prov, int(anno))] += v
    pomp_reg: dict = {}
    for r in _righe(raw, "ConsumptionBySource", salta):
        if (r.get("Fonte") or "").lower() == "idrico tradizionale" and isinstance(r.get("_v"), (int, float)):
            pomp_reg[(norm(r["Regione"]), int(r["Anno"]))] = float(r["_v"])
    ebs, n, vuoti = ricostruisci_produzione(ebs, prs, pt, pomp_reg, copie.get("ElectricityBySource", {}),
                                            copie.get("ProductionRenewableSources", {}), set(copie.get("ProductionThermal", {})))
    note += n
    _fonti(T, "produzione", ebs, _togli_anni(prs, vuoti), add)
    # richiesta per regione: copertura della domanda per fonte
    mappa_cop = {"termoelettrico tradizionale": "termo", "bioenergie": "bio", "idrico rinnovabile": "idro",
                 "pompaggi": "pomp", "idrico tradizionale": "pomp", "geotermoelettrico": "geo", "eolico": "eol", "fotovoltaico": "fv",
                 "accumulo stand alone": "acc", "saldo import/export": "saldo"}
    for r in _righe(raw, "ConsumptionBySource", salta):
        voce = mappa_cop.get(r["Fonte"].lower())
        if voce:
            add("richiesta", r["Regione"], None, r["Anno"], voce, _val(r, "_v"))
    # consumi per settore da «Total» (consumi per attività; negli anni fino al 2023 anche ElectricalEnergy ha più righe
    # per provincia e settore): si somma per anno, provincia e settore. «ElectricalEnergy» (Energia elettrica per
    # settore) solo per gli anni in cui Total manca: nel 2019 e nel 2020 ha ~7 e ~5,5 TWh di industria in meno (Brescia,
    # Taranto) rispetto a Total, Market e IndustrialSector.
    mappa_set = {"industria": "ind", "servizi": "ser", "domestico": "dom", "agricoltura": "agr"}
    tot = _consumi(raw, "Total", mappa_set, salta)
    ee = _consumi(raw, "ElectricalEnergy", mappa_set, salta)
    anni_tot = {k[2] for k in tot}
    for (reg, prov, anno, voce), v in tot.items():
        add("consumi", reg, prov, anno, voce, v)
    for (reg, prov, anno, voce), v in ee.items():
        if anno not in anni_tot:
            add("consumi", reg, prov, anno, voce, v)
    T["_note"] = note + confronta_consumi(tot, ee)
    T["_copie"] = copie
    for n in note:
        print(n, file=sys.stderr)
    return T


def leggi_emissioni(raw: Path, salta: dict | None = None) -> dict:
    """{regione Terna: {anno: {voce: [GWh, Mt CO2]}}} da GrossVsCO2Emissions (solo regione; valori vuoti = 0).
    Attenzione: in questi file l'ordine delle colonne in «Columns» è quello dei dati (Anno, Combustibile, Produzione,
    Regione, Emissioni); si leggono per nome. Righe ripetute per chiave: si tiene il valore più alto, come per le altre."""
    voce_di = {t: k for k, _, t in EMISSIONI_VOCI}
    out: dict = defaultdict(lambda: defaultdict(dict))
    for r in _righe(raw, "GrossVsCO2Emissions", salta):
        voce = voce_di.get((r.get("Combustibile") or "").strip().lower())
        if not voce:
            continue
        em = next((r[k] for k in r if k.lower().startswith("emissioni")), None)
        p = float(r["Produzione"]) if isinstance(r.get("Produzione"), (int, float)) else 0.0
        e = float(em) if isinstance(em, (int, float)) else 0.0
        prima = out[ripara(r["Regione"])][int(r["Anno"])].get(voce, [0.0, 0.0])
        out[ripara(r["Regione"])][int(r["Anno"])][voce] = [max(prima[0], p), max(prima[1], e)]
    return out


def riferimenti() -> dict:
    return json.loads(RIFERIMENTI.read_text(encoding="utf-8"))


def _fattore_anno(anni: dict, anno: int) -> float:
    """Fattore dell'anno; prima del primo anno pubblicato il primo, dopo l'ultimo l'ultimo."""
    ks = sorted(int(a) for a in anni)
    a = min(max(anno, ks[0]), ks[-1])
    return float(anni[str(a)])


def energia_primaria(voce: str, anno: int, gwh: float, mt: float, rif: dict) -> float:
    """Energia primaria [tep] del combustibile: gas, solidi e petroliferi = emissioni / fattore per contenuto di energia
    primaria (ISPRA 430/2026, Tabella 1.4, tCO2/tep); altri e bioenergie (e i combustibili senza emissioni dichiarate) =
    produzione × 0,086 tep/MWh / rendimento convenzionale (Reg. delegato UE 2023/2104)."""
    ep = rif["energia_primaria"]
    fatt = ep["fattori_tco2_tep"].get(voce)
    if fatt and mt > 0:
        return mt * 1e6 / _fattore_anno(fatt["anni"], anno)
    eta = ep["rendimenti"].get(voce, ep["rendimenti"]["altri"])["valore"]
    return gwh * 1000 * ep["tep_mwh"] / eta


INDICATORI = ["termo_gwh", "fer_gwh", "totale_gwh", "co2_kt", "tep", "fattore_medio", "fattore_termo", "tep_mwh"]


def indicatori(prod: list | None, em: list | None) -> list | None:
    """Indicatori di un'unità (regione, zona, Italia) in un anno, con le somme già fatte:
    prod = produzione per voce (VOCI["produzione"]) o None; em = [[GWh], [kt CO2], [tep]] per combustibile.
    → [termoelettrico GWh, rinnovabili GWh, totale GWh (senza pompaggi e accumuli), CO2 kt, tep,
       fattore medio tCO2/MWh (CO2 / totale), fattore del termoelettrico tCO2/MWh (CO2 / termoelettrico),
       contenuto di energia primaria del termoelettrico tep/MWh]  (None dove manca il denominatore)."""
    if not em:
        return None
    ids = [k for k, _, _ in VOCI["produzione"]]
    termo, co2, tep = sum(em[0]), sum(em[1]), sum(em[2])
    fer = tot = None
    if prod:
        fer = sum(v for k, v in zip(ids, prod) if k in FER)
        tot = sum(v for k, v in zip(ids, prod) if k not in ("pomp", "acc"))
    medio = co2 / tot if tot else None                 # kt / GWh = t / MWh
    f_termo = co2 / termo if termo else None
    tep_mwh = tep / (termo * 1000) if termo else None
    r = lambda x, d: None if x is None else round(x, d)
    return [r(termo, 1), r(fer, 1), r(tot, 1), r(co2, 1), r(tep, 0), r(medio, 4), r(f_termo, 4), r(tep_mwh, 4)]


def _somma(liste: list) -> list | None:
    liste = [x for x in liste if x]
    if not liste:
        return None
    if isinstance(liste[0][0], list):
        return [[sum(v) for v in zip(*[x[i] for x in liste])] for i in range(len(liste[0]))]
    return [sum(v) for v in zip(*liste)]


def _consumi(raw: Path, ds: str, mappa_set: dict, salta: dict | None = None) -> dict:
    """{(regione, provincia, anno, voce): GWh} sommando le righe di dettaglio (attività, classe)."""
    out: dict = defaultdict(float)
    for r in _righe(raw, ds, salta):
        voce = mappa_set.get((r.get("Settore") or "").lower())
        if voce:
            out[(r["Regione"], r["Provincia"], int(r["Anno"]), voce)] += _val(r, "_v")
    return out


SOGLIA_CONFRONTO = 0.05


def confronta_consumi(tot: dict, ee: dict, soglia: float = SOGLIA_CONFRONTO) -> list[str]:
    """Province e anni in cui Total ed ElectricalEnergy differiscono di più della soglia (sul maggiore dei due)."""
    somma = {"Total": defaultdict(float), "ElectricalEnergy": defaultdict(float)}
    nomi: dict = {}
    for ds, d in (("Total", tot), ("ElectricalEnergy", ee)):
        for (reg, prov, anno, _v), x in d.items():
            k = (norm(reg), norm(prov or ""), anno)
            somma[ds][k] += x
            nomi.setdefault(k, ripara(prov or reg))
    anni_comuni = {k[2] for k in somma["Total"]} & {k[2] for k in somma["ElectricalEnergy"]}
    note = []
    for k in sorted(set(somma["Total"]) | set(somma["ElectricalEnergy"]), key=lambda k: (k[2], k[0], k[1])):
        if k[2] not in anni_comuni:
            continue
        a, b = somma["Total"].get(k, 0.0), somma["ElectricalEnergy"].get(k, 0.0)
        m = max(abs(a), abs(b))
        if m > 0 and abs(a - b) / m > soglia:
            note.append(f"Consumi {k[2]}, {nomi[k]}: Total {a:.1f} GWh, ElectricalEnergy {b:.1f} GWh "
                        f"({(b - a) / m * 100:+.0f} %); si usa Total")
    for n in note:
        print(n, file=sys.stderr)
    return note


# ---- ricostruzione degli anni copiati (22/11/2026) ----
def _per_anno(d: dict, fonte: str | None = None) -> dict:
    """{(reg, prov, anno, fonte): v} → {anno: {(norm reg, norm prov): v}} (solo `fonte`, o già senza fonte)."""
    out: dict = defaultdict(dict)
    for k, v in d.items():
        if fonte is not None and k[3] != fonte:
            continue
        out[int(k[2])][(norm(k[0]), norm(k[1] or ""))] = v
    return out


def _interpola(serie: dict, anno: int) -> tuple[dict, list[int]]:
    """Media per provincia dell'anno valido prima e dopo `anno` (o di quello che c'è): ({chiave: v}, anni usati)."""
    prima = [a for a in serie if a < anno]
    dopo = [a for a in serie if a > anno]
    usati = ([max(prima)] if prima else []) + ([min(dopo)] if dopo else [])
    somma: dict = defaultdict(float)
    conta: dict = defaultdict(int)
    for a in usati:
        for k, v in serie[a].items():
            somma[k] += v
            conta[k] += 1
    return {k: somma[k] / conta[k] for k in somma}, usati


def _n(x: float) -> str:
    """Numero intero con il punto delle migliaia (319.130)."""
    return f"{x:,.0f}".replace(",", ".")


def _anni_testo(usati: list[int]) -> str:
    return " e del ".join(map(str, usati)) if usati else "nessun anno"


def _togli_anni(d: dict, anni: set) -> dict:
    return defaultdict(float, {k: v for k, v in d.items() if int(k[2]) not in anni})


def ricostruisci_produzione(ebs: dict, prs: dict, pt: dict, pomp_reg: dict, copie_ebs: dict, copie_prs: dict,
                            copie_pt: set) -> tuple[dict, list[str], set]:
    """Righe di ElectricityBySource per gli anni copiati, dalle altre tabelle di Terna dello stesso anno:
    termoelettrico lordo = ProductionThermal (somma dei valori lordi per categoria); idrico rinnovabile, geotermico,
    eolico, fotovoltaico = ProductionRenewableSources; pompaggi = ConsumptionBySource «Idrico tradizionale» per regione
    (produzione degli impianti di pompaggio), divisa tra le province come la media dell'anno valido prima e dopo
    (se manca il dato regionale, la media stessa). Se manca una delle due tabelle, l'anno resta vuoto.
    → (ebs con gli anni ricostruiti, note, anni rimasti vuoti)."""
    note: list[str] = []
    vuoti: set = set()
    ebs = _togli_anni(ebs, set(copie_prs))            # senza le rinnovabili dell'anno la produzione non si separa
    for a in sorted(copie_prs):
        if a not in copie_ebs:
            note.append(f"Produzione {a}: dato di Terna non disponibile (ProductionRenewableSources {a} è una copia)")
    anni_pt = {k[2] for k in pt}
    anni_prs = {int(k[2]) for k in prs}
    pomp_prov: dict = defaultdict(dict)               # pompaggi lordi per provincia negli anni validi
    idro_e, idro_r = _per_anno(ebs, "idrico"), _per_anno(prs, "idrico")
    for anno, d in idro_e.items():
        for k, v in d.items():
            pomp_prov[anno][k] = max(0.0, v - idro_r.get(anno, {}).get(k, 0.0))
    for a in sorted(copie_ebs):
        if a in copie_prs or a in copie_pt or a not in anni_pt or a not in anni_prs:
            note.append(f"Produzione {a}: dato di Terna non disponibile (ElectricityBySource {a} è una copia e mancano "
                        "ProductionThermal o ProductionRenewableSources dello stesso anno)")
            vuoti.add(a)
            continue
        nomi: dict = {}                               # (norm reg, norm prov) → nomi di Terna dell'anno
        for k in prs:
            if int(k[2]) == a:
                nomi.setdefault((norm(k[0]), norm(k[1] or "")), (k[0], k[1]))
        for (reg, prov, anno), _v in pt.items():
            if anno == a:
                nomi.setdefault((norm(reg), norm(prov or "")), (reg, prov))
        quote, usati = _interpola({y: v for y, v in pomp_prov.items() if y != a}, a)
        righe: dict = {}
        for (nr, np_), (reg, prov) in nomi.items():
            r = lambda f: prs.get((reg, prov, a, f), 0.0)
            righe[(reg, prov, a, "termoelettrico")] = sum(v for (rg, pv, an), v in pt.items()
                                                         if an == a and (norm(rg), norm(pv or "")) == (nr, np_))
            righe[(reg, prov, a, "idrico")] = r("idrico")
            for f in ("geotermoelettrico", "eolico", "fotovoltaico"):
                righe[(reg, prov, a, f)] = r(f)
        regioni = {nr for nr, _ in nomi}
        da_regione = 0
        for nr in sorted(regioni):
            pesi = {k: quote.get(k, 0.0) for k in nomi if k[0] == nr}
            totale = pomp_reg.get((nr, a))
            if totale is None:
                totale = sum(pesi.values())
            else:
                da_regione += 1
            totale = max(0.0, totale)
            sp = sum(pesi.values())
            if totale and not sp:
                note.append(f"Produzione {a}: pompaggi di {nr} ({totale:.0f} GWh) non attribuibili alle province, esclusi")
                continue
            for k, w in pesi.items():
                if w:
                    reg, prov = nomi[k]
                    righe[(reg, prov, a, "idrico")] += totale * w / sp
        ebs.update(righe)
        tot = sum(righe.values())
        note.append(f"Produzione {a} ricostruita (ElectricityBySource {a} è una copia di {copie_ebs[a]['di']}): "
                    f"termoelettrico lordo da ProductionThermal (per ogni chiave il valore maggiore, cioè il lordo), "
                    f"idrico rinnovabile, geotermico, eolico e fotovoltaico da ProductionRenewableSources, pompaggi da "
                    f"ConsumptionBySource «Idrico tradizionale» per regione ({da_regione} regioni) divisi tra le province "
                    f"come la media del {_anni_testo(usati)}; Italia {_n(tot)} GWh")
    return ebs, note, vuoti


def ricostruisci_capacita(gp: dict, crs: dict, ct: dict, copie_gp: dict, copie_crs: dict,
                          copie_ct: set) -> tuple[dict, list[str], set]:
    """Righe di GenerationPlants per gli anni copiati: termoelettrico = CapacityThermal (meno il geotermico, se
    nell'anno valido più vicino CapacityThermal lo comprende), rinnovabili = CapacityRenewableSources, pompaggio puro =
    media per provincia dell'anno valido prima e dopo (GenerationPlants idrico − CapacityRenewableSources idrico).
    Se manca una delle due tabelle dello stesso anno, l'anno resta vuoto.
    → (gp con gli anni ricostruiti, note, anni rimasti vuoti)."""
    note: list[str] = []
    vuoti: set = set()
    gp = _togli_anni(gp, set(copie_crs))
    for a in sorted(copie_crs):
        if a not in copie_gp:
            note.append(f"Capacità {a}: dato di Terna non disponibile (CapacityRenewableSources {a} è una copia)")
    anni_ct = {int(k[2]) for k in ct}
    anni_crs = {int(k[2]) for k in crs}
    anni_gp = sorted({int(k[2]) for k in gp})
    termo_gp, geo_crs = _per_anno(gp, "termoelettrico"), _per_anno(crs, "geotermoelettrico")
    ct_anno = _per_anno({(k[0], k[1], k[2], None): v for k, v in ct.items()})
    pomp: dict = defaultdict(dict)
    idro_g, idro_r = _per_anno(gp, "idrico"), _per_anno(crs, "idrico")
    for anno, d in idro_g.items():
        if anno in anni_crs:
            for k, v in d.items():
                pomp[anno][k] = max(0.0, v - idro_r.get(anno, {}).get(k, 0.0))
    for a in sorted(copie_gp):
        if a in copie_crs or a in copie_ct or a not in anni_ct or a not in anni_crs:
            perche = [f"GenerationPlants {a} è una copia del {copie_gp[a]['di']}"]
            if a in copie_crs:
                perche.append(f"CapacityRenewableSources {a} del {copie_crs[a]['di']}")
            note.append(f"Capacità {a}: dato di Terna non disponibile ({', '.join(perche)})")
            vuoti.add(a)
            continue
        vicini = sorted((y for y in anni_gp if y in anni_ct and y in anni_crs), key=lambda y: (abs(y - a), y))
        con_geo = False
        if vicini:
            y = vicini[0]
            diff = sum(ct_anno[y].values()) - sum(termo_gp[y].values())
            geo = sum(geo_crs.get(y, {}).values())
            con_geo = geo > 0 and diff > 0.5 * geo
        quote, usati = _interpola({y: v for y, v in pomp.items() if y != a}, a)
        nomi: dict = {}
        for k in crs:
            if int(k[2]) == a:
                nomi.setdefault((norm(k[0]), norm(k[1] or "")), (k[0], k[1]))
        for (reg, prov, anno) in ct:
            if int(anno) == a:
                nomi.setdefault((norm(reg), norm(prov or "")), (reg, prov))
        righe: dict = {}
        for chiave, (reg, prov) in nomi.items():
            r = lambda f: crs.get((reg, prov, a, f), 0.0)
            termo = ct_anno[a].get(chiave, 0.0) - (geo_crs.get(a, {}).get(chiave, 0.0) if con_geo else 0.0)
            righe[(reg, prov, a, "termoelettrico")] = max(0.0, termo)
            righe[(reg, prov, a, "idrico")] = r("idrico") + quote.get(chiave, 0.0)
            for f in ("geotermoelettrico", "eolico", "fotovoltaico"):
                righe[(reg, prov, a, f)] = r(f)
        persi = sum(v for k, v in quote.items() if k not in nomi)
        if persi > 0.5:
            note.append(f"Capacità {a}: {persi:.0f} MW di pompaggio puro in province senza dati nell'anno, esclusi")
        gp.update(righe)
        tot = sum(righe.values())
        note.append(f"Capacità {a} ricostruita (GenerationPlants {a} è una copia del {copie_gp[a]['di']}): termoelettrico "
                    f"da CapacityThermal{' meno il geotermico (compreso in CapacityThermal)' if con_geo else ''}, "
                    f"rinnovabili da CapacityRenewableSources, pompaggio puro come media per provincia del "
                    f"{_anni_testo(usati)}; Italia {_n(tot)} MW")
    return gp, note, vuoti


SOGLIA_SALTO = 0.15


def controlla_salti(serie: dict, nome: str, unita: str, soglia: float = SOGLIA_SALTO) -> list[str]:
    """Avvisi per gli anni in cui il totale nazionale cambia di più della soglia rispetto alla media dell'anno prima e
    dell'anno dopo (serie = {anno: totale}; solo anni con entrambi i vicini)."""
    note = []
    for a in sorted(serie):
        if a - 1 in serie and a + 1 in serie:
            m = (serie[a - 1] + serie[a + 1]) / 2
            if m and abs(serie[a] - m) / abs(m) > soglia:
                note.append(f"Controllo salti: {nome} {a}, Italia {_n(serie[a])} {unita} contro {_n(m)} di media del "
                            f"{a - 1} e del {a + 1} ({(serie[a] - m) / abs(m) * 100:+.0f} %)")
    return note


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
    note = T.pop("_note", [])
    copie = T.pop("_copie", {})
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

    # emissioni per regione (solo regione: Terna non le pubblica per provincia)
    rif = riferimenti()
    em = leggi_emissioni(raw, {ds: set(v) for ds, v in copie.items()})
    em_reg: dict = defaultdict(dict)
    for reg, serie in em.items():
        rp = regioni_pos.get(norm(reg))
        if not rp:
            raise ValueError(f"regione di Terna non riconosciuta nelle emissioni: {reg}")
        for anno, v in serie.items():
            p = [v.get(k, [0.0, 0.0])[0] for k, _, _ in EMISSIONI_VOCI]
            e = [v.get(k, [0.0, 0.0])[1] for k, _, _ in EMISSIONI_VOCI]
            t = [energia_primaria(k, anno, p[i], e[i], rif) for i, (k, _, _) in enumerate(EMISSIONI_VOCI)]
            em_reg[rp["cod"]][str(anno)] = [[round(x, 1) for x in p], [round(x * 1000, 2) for x in e], [round(x) for x in t]]
    anni["emissioni"] = sorted({int(a) for s_ in em_reg.values() for a in s_})
    for voce in regioni_out:
        voce["emissioni"] = dict(sorted(em_reg.get(voce["cod"], {}).items()))
    zone = _zone(mappa, {r["cod"] for r in regioni_out})
    # indicatori per regione, zona di mercato e Italia (somme prima dei rapporti)
    per_cod = {r["cod"]: r for r in regioni_out}
    for voce in regioni_out:
        voce["indicatori"] = {a: indicatori(voce["produzione"].get(a), voce["emissioni"].get(a)) for a in voce["emissioni"]}
    def aggrega(codici):
        out = {}
        for a in map(str, anni["emissioni"]):
            em_ = _somma([per_cod[c]["emissioni"].get(a) for c in codici])
            pr_ = _somma([per_cod[c]["produzione"].get(a) for c in codici])
            out[a] = indicatori(pr_, em_)
        return out
    for z in zone:
        z["indicatori"] = aggrega(z["regioni"])
    italia_ind = aggrega(list(per_cod))

    # controllo anti-salto sui totali nazionali (somma delle regioni)
    nomi_g = {"capacita": "capacità", "produzione": "produzione", "richiesta": "richiesta", "consumi": "consumi"}
    salti = []
    for g in VOCI:
        serie = {a: sum(sum(_arr(per_regione[g][c].get(a, {}), g)) for c in per_regione[g]) for a in anni[g]}
        salti += controlla_salti(serie, nomi_g[g], UNITA[g])
    for i, (campo, unita_em) in enumerate((("produzione termoelettrica", "GWh"), ("emissioni di CO2", "kt"))):
        serie = {int(a): sum(sum(r["emissioni"][a][i]) for r in regioni_out if a in r["emissioni"])
                 for a in map(str, anni["emissioni"])}
        salti += controlla_salti(serie, campo, unita_em)
    for n in salti:
        print(n, file=sys.stderr)
    note = note + salti
    controlli = {"copie": [descrivi_copia(ds, a, c) for ds, v in sorted(copie.items()) for a, c in sorted(v.items())],
                 "salti": salti}

    voci_out = {g: [{"id": k, "nome": n, "colore": c} for k, n, c in VOCI[g]] for g in VOCI}
    comune = {"fonte": FONTE, "unita": UNITA, "voci": voci_out, "fer": FER, "anni": anni,
              "obiettivi_anni": ANNI_OBIETTIVI, "obiettivi_base": 2020,
              "obiettivi_fonte": "DM MASE 21 giugno 2024 (aree idonee), art. 2, Tabella A (GU n. 153 del 2/7/2024)"}
    em_out = {"voci": [{"id": k, "nome": n} for k, n, _ in EMISSIONI_VOCI],
              "campi": ["produzione termoelettrica lorda [GWh]", "emissioni di CO2 [kt]", "energia primaria stimata [tep]"],
              "indicatori": INDICATORI, "italia": italia_ind,
              "riferimenti": {"mef": rif["mef"], "ispra": rif["ispra"], "energia_primaria": rif["energia_primaria"],
                              "letto": rif["letto"]}}
    (uscita / "italia.json").write_text(json.dumps({**comune, "note": note, "emissioni": em_out, "zone": zone,
                                                    "regioni": regioni_out}, ensure_ascii=False,
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
    return {"anni": anni, "dimensioni": dimensioni, "note": note, "controlli": controlli}


def _zone(mappa: Path, codici: set) -> list:
    """Zone di mercato con le regioni; se c'è dati/mappa/zone.json deve dire lo stesso (altrimenti errore)."""
    zone = [{"id": i, "nome": n, "regioni": r} for i, n, r in ZONE]
    f = mappa / "zone.json"
    if f.exists():
        sito = [{"id": z["id"], "nome": z["nome"], "regioni": z["regioni"]} for z in json.loads(f.read_text(encoding="utf-8"))["zone"]]
        if sito != zone:
            raise ValueError("zone di mercato diverse da quelle di dati/mappa/zone.json")
    tutte = [c for z in zone for c in z["regioni"]]
    if sorted(tutte) != sorted(codici) or len(set(tutte)) != len(tutte):
        raise ValueError("le zone di mercato non coprono ogni regione una volta sola")
    return zone


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    esito = costruisci(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
    print(json.dumps(esito, indent=1))


if __name__ == "__main__":
    main()
