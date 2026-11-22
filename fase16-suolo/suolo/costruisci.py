"""File del sito per la pagina «Suolo e aree agricole» (Statistiche, 22/11/2026, richiesta di Paolo).

  costruisci(raw: Path, uscita: Path, mappa: Path | None = None, precedente: Path | None = None, forza: bool = False) -> dict
      legge in `raw` i file di scarica.py (ispra_indicatori.xlsx, istat_coltivazioni.csv, istat_censimento2020.csv,
      stato_scarico.json) e, se c'è, agricolo_<anno>.json di agricolo.py; scrive in `uscita`:
        italia.json   voci, anni, riferimenti, totale Italia e regioni (valori per anno e voce)
        RR.json       province della regione RR (stesse grandezze) e comuni (suolo consumato e incremento netto per anno)
      `mappa` è la cartella dati/mappa del sito (posizioni e codici, ISTAT 2026); se manca, «mappa» accanto a `uscita`.
      `precedente` è l'italia.json pubblicato: se il suolo consumato di una regione cambia di più del 2 % in un anno già
      pubblicato si ferma (ValueError), salvo forza=True (nuova edizione ISPRA con revisioni grandi: controllare a mano).
      Il worker lo chiama in una cartella nuova e la pubblica con _pubblica (fase 4) solo se i controlli passano.

Le tre scelte della pagina (decisione di Paolo del 22/11/2026):
  suolo    grandezze di stato [ha] per anno (2006, 2012, 2015…): SAU e superficie agricola non utilizzata (censimento ISTAT
           2020, uguali in tutti gli anni), suolo consumato (csuolo1), suolo consumato in aree a pericolosità idraulica media
           P2 (pidrau4; le classi P1 ⊃ P2 ⊃ P3 sono annidate), da frana elevata e molto elevata P3+P4 (pfrane3 + pfrane4),
           entro 300 m dalla costa (ccoste4), in aree protette EUAP (careep2). Le voci si sovrappongono: niente totale.
  consumi  flussi [ha] per periodo, per gruppo di classi (classi.GRUPPI, csuolox111…126) più «non attribuito a una classe»
           (consumo lordo csuolo10 meno la somma delle classi: c'è solo nel 2006–2012); in più il bilancio
           [lordo csuolo10, ripristini csuolo13, netto csuolo8] e, dove c'è l'incrocio di agricolo.py, la parte su suolo
           agricolo per gruppo (stima EuGEnio). Il flusso dell'anno t è il periodo che finisce in t (2012 = 2006–2012,
           2015 = 2012–2015, poi annuali): «periodi» in italia.json.
  colture  superfici [ha] per famiglia di colture (colture.py, ISTAT stime congiunturali), per anno dal 2006.

Serie ISPRA come le pubblica ISPRA (decisione di Paolo): superfici dei fogli «Comuni_AAAA» ecc.; i fogli «_rev» (anno
precedente rivisto nell'edizione successiva) vanno in «rev» e la pagina li segnala, senza sostituire il valore pubblicato.

Controlli prima di scrivere (ValueError): somme comuni = province = regioni = Italia per ogni anno (suolo consumato e
consumo lordo, tolleranza 1 ha o 1 milionesimo); tutti i comuni abbinati alla mappa (i sardi per nome); tutte le province
e le regioni nella mappa; ultimo anno = anno dell'edizione − 1; scarto con l'edizione pubblicata (vedi `precedente`).

  python -m suolo.costruisci <raw> <uscita> <cartella dati/mappa> [--precedente italia.json] [--forza]
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from . import censimento, colture
from . import mappa as M
from .classi import GRUPPI

TOLLERANZA_HA = 1.0
SOGLIA_EDIZIONE = 0.02
LICENZA = "CC BY 4.0"
LICENZA_URL = "https://creativecommons.org/licenses/by/4.0/legalcode.it"
CITAZIONE = ("Elaborazione EuGEnio su dati ISPRA/SNPA, ISTAT e Copernicus (licenze CC BY 4.0 e dati Copernicus con "
             "attribuzione); dati modificati: aggregati e ricalcolati")

VOCI = {
    "suolo": [
        ("sau", "Superficie agricola utilizzata (SAU, censimento 2020)", "#6aa84f"),
        ("nonut", "Superficie agricola non utilizzata (censimento 2020)", "#c5a572"),
        ("cons", "Suolo consumato", "#8e2c2c"),
        ("idr", "Suolo consumato in aree a pericolosità idraulica media (P2)", "#3d85c6"),
        ("frane", "Suolo consumato in aree a pericolosità da frana elevata e molto elevata (P3+P4)", "#a0612b"),
        ("coste", "Suolo consumato entro 300 m dalla costa", "#45b5c4"),
        ("protette", "Suolo consumato in aree protette (EUAP)", "#2e7d32"),
    ],
    "consumi": [(g, n, c) for g, n, c, _ in GRUPPI] + [("nc", "Non attribuito a una classe", "#b8b8b8")],
}
CENSIMENTO_VOCI = 2          # le prime due voci di «suolo» vengono dal censimento 2020
BILANCIO = ["consumo lordo [ha]", "ripristini [ha]", "consumo netto [ha]"]

RE_FOGLIO = re.compile(r"^(Comuni|Province|Regioni|Nazionale)_(\d{4})(_rev)?$")


# ---------------------------------------------------------------- lettura dell'Excel
class Libro:
    """Fogli dell'Excel ISPRA come liste di dizionari. python-calamine se c'è (1 s), altrimenti openpyxl in sola lettura
    (qualche minuto per 87 MB: va bene per un lavoro annuale del worker)."""

    def __init__(self, percorso: Path):
        self.percorso = Path(percorso)
        try:
            from python_calamine import CalamineWorkbook
            self._wb = CalamineWorkbook.from_path(str(self.percorso))
            self.nomi = list(self._wb.sheet_names)
            self._cal = True
        except ImportError:
            import openpyxl
            self._wb = openpyxl.load_workbook(self.percorso, read_only=True, data_only=True)
            self.nomi = list(self._wb.sheetnames)
            self._cal = False

    def righe(self, nome: str) -> list[list]:
        if self._cal:
            return self._wb.get_sheet_by_name(nome).to_python()
        return [list(r) for r in self._wb[nome].iter_rows(values_only=True)]

    def tabella(self, nome: str) -> list[dict]:
        r = self.righe(nome)
        if not r:
            return []
        testa = [str(x).strip() if x is not None else "" for x in r[0]]
        return [dict(zip(testa, x)) for x in r[1:] if any(v not in (None, "") for v in x)]


def _n(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _z(v) -> float:
    x = _n(v)
    return 0.0 if x is None else x


def _info(libro: Libro) -> dict:
    """Titolo, edizione, versione e data dal foglio «Info»."""
    out = {"titolo": None, "edizione": None, "versione": None, "data": None}
    if "Info" not in libro.nomi:
        return out
    for r in libro.righe("Info"):
        t = " ".join(str(x) for x in r if x not in (None, "")).strip()
        m = re.search(r"Edizione\s+(\d{4})", t)
        if m and not out["titolo"]:
            out["titolo"], out["edizione"] = t, int(m.group(1))
        m = re.search(r"\(v\.?\s*([\d.]+)\)\s*[–-]\s*(\d{1,2}/\d{1,2}/\d{4})", t)
        if m:
            out["versione"], out["data"] = m.group(1), m.group(2)
    return out


def _stato(r: dict) -> list:
    return [round(_z(r.get("csuolo1")), 2), round(_z(r.get("pidrau4")), 2),
            round(_z(r.get("pfrane3")) + _z(r.get("pfrane4")), 2), round(_z(r.get("ccoste4")), 2), round(_z(r.get("careep2")), 2)]


def _flussi(r: dict) -> tuple[list, list] | None:
    lordo = _n(r.get("csuolo10"))
    if lordo is None:
        return None
    gruppi = [round(sum(_z(r.get(f"csuolox{c}")) for c in cl), 2) for _, _, _, cl in GRUPPI]
    nc = round(max(0.0, lordo - sum(gruppi)), 2)
    if nc < 0.05:
        nc = 0.0
    return gruppi + [nc], [round(lordo, 2), round(_z(r.get("csuolo13")), 2), round(_z(r.get("csuolo8")), 2)]


def leggi_ispra(xlsx: Path) -> dict:
    """{"info", "anni", "rev": [anni], "livelli": {livello: {anno|"AAAA_rev": [righe]}}}"""
    libro = Libro(xlsx)
    livelli: dict = defaultdict(dict)
    for nome in libro.nomi:
        m = RE_FOGLIO.match(nome)
        if m:
            livelli[m.group(1)][m.group(2) + (m.group(3) or "")] = libro.tabella(nome)
    anni = sorted({int(k) for k in livelli["Nazionale"] if k.isdigit()})
    rev = sorted({int(k[:4]) for k in livelli["Nazionale"] if k.endswith("_rev")})
    if not anni:
        raise ValueError("ISPRA: nessun foglio Nazionale_AAAA nell'Excel degli indicatori")
    return {"info": _info(libro), "anni": anni, "rev": rev, "livelli": livelli}


# ---------------------------------------------------------------- controlli
def _vicini(a: float, b: float) -> bool:
    return abs(a - b) <= max(TOLLERANZA_HA, 1e-6 * max(abs(a), abs(b)))


def controlla_somme(isp: dict) -> list[str]:
    """Somme comuni = province = regioni = Italia per ogni foglio (csuolo1 e csuolo10). Errori come testi."""
    err = []
    L = isp["livelli"]
    for chiave in sorted(L["Nazionale"]):
        for campo in ("csuolo1", "csuolo10"):
            tot = {liv: sum(_z(r.get(campo)) for r in L[liv].get(chiave, [])) for liv in ("Comuni", "Province", "Regioni", "Nazionale")}
            if tot["Nazionale"] == 0 and campo == "csuolo10":
                continue
            for liv in ("Comuni", "Province", "Regioni"):
                if not _vicini(tot[liv], tot["Nazionale"]):
                    err.append(f"{chiave}, {campo}: somma {liv} {tot[liv]:.2f} ha contro Italia {tot['Nazionale']:.2f} ha")
        # per provincia: somma dei comuni
        per_prov: dict = defaultdict(float)
        for r in L["Comuni"].get(chiave, []):
            per_prov[int(_z(r.get("cod_prov")))] += _z(r.get("csuolo1"))
        for r in L["Province"].get(chiave, []):
            p = int(_z(r.get("cod_prov")))
            if not _vicini(per_prov.get(p, 0.0), _z(r.get("csuolo1"))):
                err.append(f"{chiave}: provincia {p}, somma dei comuni {per_prov.get(p, 0.0):.2f} contro {_z(r.get('csuolo1')):.2f} ha")
    return err


def confronta_precedente(nuova: dict, vecchia: dict, soglia: float = SOGLIA_EDIZIONE) -> list[str]:
    """Regioni e anni in cui il suolo consumato cambia di più della soglia rispetto ai file pubblicati."""
    out = []
    vecchie = {r["cod"]: r for r in vecchia.get("regioni", [])}
    for r in nuova["regioni"]:
        v = vecchie.get(r["cod"])
        if not v:
            continue
        for a, x in r.get("suolo", {}).items():
            y = (v.get("suolo") or {}).get(a)
            if not y or not y[2]:
                continue
            d = (x[2] - y[2]) / y[2]
            if abs(d) > soglia:
                out.append(f"{r['nome']} {a}: suolo consumato {y[2]:.0f} → {x[2]:.0f} ha ({d * 100:+.1f} %)")
    return out


# ---------------------------------------------------------------- costruzione
def _per_unita(righe: list[dict], chiave_cod: str, larghezza: int) -> dict:
    return {f"{int(_z(r.get(chiave_cod))):0{larghezza}d}": r for r in righe if _n(r.get(chiave_cod)) is not None}


def _serie(isp: dict, livello: str, chiave_cod: str, larghezza: int) -> dict:
    """{cod: {"sup", "pop": {anno}, "suolo": {anno: [5]}, "consumi": {anno: [..]}, "bilancio": {anno: [3]}, "rev": {anno}, "nome"}}"""
    L = isp["livelli"][livello]
    out: dict = defaultdict(lambda: {"pop": {}, "suolo": {}, "consumi": {}, "bilancio": {}, "rev": {}})
    ultimo = str(isp["anni"][-1])
    for anno in isp["anni"]:
        for cod, r in _per_unita(L.get(str(anno), []), chiave_cod, larghezza).items():
            u = out[cod]
            u["nome"] = r.get("nome_comune") or r.get("nome_provincia") or r.get("nome_regione") or r.get("nome_nazione")
            a = str(anno)
            u["suolo"][a] = _stato(r)
            if _n(r.get("clammi4")) is not None:
                u["pop"][a] = int(_z(r.get("clammi4")))
            f = _flussi(r)
            if f and anno != isp["anni"][0]:
                u["consumi"][a], u["bilancio"][a] = f
            if a == ultimo:
                u["sup"] = round(_z(r.get("clammi3")), 2)
    for anno in isp["rev"]:
        for cod, r in _per_unita(L.get(f"{anno}_rev", []), chiave_cod, larghezza).items():
            out[cod]["rev"][str(anno)] = round(_z(r.get("csuolo1")), 2)
    return out


def _somma_vettori(dest: dict, chiave: str, v: list):
    prima = dest.get(chiave)
    dest[chiave] = [round(a + b, 2) for a, b in zip(prima, v)] if prima else list(v)


def costruisci(raw: Path, uscita: Path, mappa: Path | None = None, precedente: Path | None = None, forza: bool = False) -> dict:
    raw, uscita = Path(raw), Path(uscita)
    mappa = Path(mappa) if mappa else uscita.parent / "mappa"
    m = M.carica(mappa)
    stato_scarico = {}
    if (raw / "stato_scarico.json").exists():
        stato_scarico = json.loads((raw / "stato_scarico.json").read_text(encoding="utf-8"))
    isp = leggi_ispra(raw / "ispra_indicatori.xlsx")
    note: list[str] = []

    # --- controlli ISPRA
    errori = controlla_somme(isp)
    edizione = isp["info"].get("edizione") or (stato_scarico.get("ispra") or {}).get("anno")
    if edizione and isp["anni"][-1] != edizione - 1:
        errori.append(f"ultimo anno {isp['anni'][-1]} diverso da edizione {edizione} − 1")
    regioni_i = _serie(isp, "Regioni", "cod_reg", 2)
    province_i = _serie(isp, "Province", "cod_prov", 3)
    comuni_i = _serie(isp, "Comuni", "pro_com", 6)
    italia_i = next(iter(_serie(isp, "Nazionale", "cod_naz", 1).values()))
    mancano_r = sorted(set(regioni_i) - set(m["regioni"]))
    mancano_p = sorted(set(province_i) - set(m["province"]))
    if mancano_r or mancano_p:
        errori.append(f"regioni o province ISPRA non nella mappa: {mancano_r} {mancano_p}")
    righe_c = isp["livelli"]["Comuni"][str(isp["anni"][-1])]
    nomi_c = {f"{int(_z(r['pro_com'])):06d}": (r.get("nome_comune"), f"{int(_z(r['cod_reg'])):02d}") for r in righe_c}
    abbinati, non = M.abbina_comuni(nomi_c, m["comuni"])
    if non:
        errori.append(f"{len(non)} comuni ISPRA non abbinati alla mappa: {non[:15]}")
    if errori:
        raise ValueError("controlli non superati:\n  " + "\n  ".join(errori))
    prov_di_ispra = {f"{int(_z(r['pro_com'])):06d}": f"{int(_z(r['cod_prov'])):03d}" for r in righe_c}
    provincia_di = {abbinati[pc]: prov_di_ispra[pc] for pc in abbinati}          # codice della mappa → provincia 2026

    # --- censimento 2020 (SAU, non utilizzata)
    cens = censimento.sau(raw / "istat_censimento2020.csv", m, provincia_di) if (raw / "istat_censimento2020.csv").exists() else None
    if cens:
        note += cens["note"]
    # --- colture
    col = colture.famiglie(raw / "istat_coltivazioni.csv") if (raw / "istat_coltivazioni.csv").exists() else None
    if col:
        note += col["note"]
    # --- incrocio agricolo (facoltativo)
    agr = None
    file_agr = sorted(raw.glob("agricolo_*.json"))
    if file_agr:
        agr = json.loads(file_agr[-1].read_text(encoding="utf-8"))
        if str(agr["anno"]) not in italia_i["consumi"]:
            note.append(f"Incrocio agricolo {agr['anno']}: anno non presente nei dati ISPRA, ignorato")
            agr = None
    agr_reg: dict = {}
    agr_prov: dict = {}
    agr_it = None
    if agr:
        a = str(agr["anno"])
        for ist, v in agr["comuni"].items():
            p = provincia_di.get(ist)
            if not p:
                continue
            _somma_vettori(agr_prov, p, v["agricolo"])
            _somma_vettori(agr_reg, m["province"][p]["regione"], v["agricolo"])
        agr_it = [round(x, 2) for x in agr["italia"]["agricolo"]]
        lordo_px = sum(agr["italia"]["lordo"])
        lordo_isp = italia_i["bilancio"][a][0]
        scarto = (lordo_px - lordo_isp) / lordo_isp if lordo_isp else 0
        if abs(scarto) > 0.02:
            note.append(f"Incrocio agricolo {a}: nuovo consumo dai pixel {lordo_px:.0f} ha contro {lordo_isp:.0f} ha dell'Excel "
                        f"({scarto * 100:+.1f} %)")

    def suolo_con_sau(u: dict, sau_v: list | None) -> dict:
        s = sau_v or [None, None]
        return {a: [s[0], s[1], *v] for a, v in u["suolo"].items()}

    def unita(cod: str, u: dict, pos: dict, sau_v, agr_v, col_v) -> dict:
        out = {"cod": cod, "nome": pos["nome"], "lon": pos["lon"], "lat": pos["lat"], "sup": u.get("sup"),
               "pop": u["pop"], "suolo": suolo_con_sau(u, sau_v), "consumi": u["consumi"], "bilancio": u["bilancio"]}
        if u["rev"]:
            out["rev"] = u["rev"]
        if agr_v is not None and agr:
            out["agricolo"] = {str(agr["anno"]): [round(x, 2) for x in agr_v]}
        if col_v:
            out["colture"] = {str(a): v for a, v in sorted(col_v.items())}
        return out

    regioni_out = []
    for cod in sorted(m["regioni"]):
        pos = m["regioni"][cod]
        regioni_out.append(unita(cod, regioni_i[cod], pos, cens["regioni"].get(cod) if cens else None,
                                 agr_reg.get(cod, [0.0] * len(GRUPPI)) if agr else None, (col or {}).get("regioni", {}).get(cod)))
    italia_out = unita("IT", italia_i, {"nome": "Italia", "lon": None, "lat": None}, cens["italia"] if cens else None,
                       agr_it, (col or {}).get("italia"))

    anni_suolo = isp["anni"]
    anni_flussi = [a for a in isp["anni"][1:] if str(a) in italia_i["consumi"]]
    periodi = {str(a): [isp["anni"][i - 1], a] for i, a in enumerate(isp["anni"]) if i and a in anni_flussi}
    voci = {g: [{"id": i, "nome": n, "colore": c} for i, n, c in VOCI[g]] for g in VOCI}
    voci["colture"] = [{"id": i, "nome": n, "colore": c} for i, n, c in (col["voci"] if col else [])]
    isp_file = stato_scarico.get("ispra") or {}
    riferimenti = {
        "ispra": {"titolo": isp["info"].get("titolo"), "edizione": edizione, "versione": isp["info"].get("versione") or isp_file.get("versione"),
                  "data": isp["info"].get("data"), "file": isp_file.get("nome"), "url": isp_file.get("url"),
                  "licenza": LICENZA, "licenza_url": LICENZA_URL,
                  "citazione": f"Munafò M. (a cura di), {edizione}, Consumo di suolo, ecosistemi urbani e stato del territorio. "
                               f"Edizione {edizione}, Report ambientali SNPA" if edizione else None},
        "istat_colture": {"titolo": "ISTAT, Coltivazioni: superfici e produzione (stime congiunturali), superficie totale",
                          "flusso": "101_1015_DF_DCSP_COLTIVAZIONI_2", "licenza": LICENZA,
                          "scaricato": (stato_scarico.get("coltivazioni") or {}).get("scaricato")},
        "istat_censimento": {"titolo": "ISTAT, 7° Censimento generale dell'agricoltura (2020): SAU e superficie agricola non utilizzata",
                             "flusso": "DF_DCAT_CENSAGRIC2020_SURF_ALL", "licenza": LICENZA,
                             "nazionale": cens["nazionale"] if cens else None},
        "agricolo": ({"anno": agr["anno"], "periodo": agr.get("periodo"), "file": agr.get("file"),
                      "metodo": "carta dei cambiamenti del consumo di suolo ISPRA × Carta nazionale di uso del suolo ISPRA "
                                "(usi agricoli 11–16), pixel di 10 m assegnati ai comuni; stima EuGEnio",
                      "usi": agr.get("usi"), "usi_italia": agr["italia"].get("usi"),
                      "usi_non_agricoli_italia": (agr.get("usi_non_agricoli") or {}).get("IT"),
                      "confronto": {"fonte": "ISMEA nel Rapporto SNPA 2026, consumo di suolo agricolo 2024–2025", "ha": 8208}}
                     if agr else None),
        "citazione": CITAZIONE,
    }
    comune = {"fonte": CITAZIONE, "unita": "ha"}
    italia_json = {**comune, "riferimenti": riferimenti, "voci": voci, "bilancio": BILANCIO, "censimento_voci": CENSIMENTO_VOCI,
                   "anni": {"suolo": anni_suolo, "consumi": anni_flussi, "colture": (col or {}).get("anni", []),
                            "agricolo": [agr["anno"]] if agr else []},
                   "periodi": periodi, "rev": [str(a) for a in isp["rev"]], "note": note,
                   "italia": italia_out, "regioni": regioni_out}
    if precedente and Path(precedente).exists():
        diff = confronta_precedente(italia_json, json.loads(Path(precedente).read_text(encoding="utf-8")))
        if diff and not forza:
            raise ValueError("suolo consumato cambiato di più del 2 % rispetto ai file pubblicati (usa forza dopo un "
                             "controllo):\n  " + "\n  ".join(diff[:30]))
        note += diff
    uscita.mkdir(parents=True, exist_ok=True)
    (uscita / "italia.json").write_text(json.dumps(italia_json, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # --- province e comuni per regione
    anni_c = [str(a) for a in isp["anni"]]
    dimensioni = {"italia.json": (uscita / "italia.json").stat().st_size}
    pc_di = {v: k for k, v in abbinati.items()}                     # codice della mappa → pro_com ISPRA
    for rcod, rpos in sorted(m["regioni"].items()):
        prov_out = []
        for pcod, ppos in sorted(m["province"].items(), key=lambda x: x[1]["nome"]):
            if ppos["regione"] != rcod or pcod not in province_i:
                continue
            p = unita(pcod, province_i[pcod], ppos, cens["province"].get(pcod) if cens else None,
                      agr_prov.get(pcod, [0.0] * len(GRUPPI)) if agr else None, (col or {}).get("province", {}).get(pcod))
            p["sigla"] = ppos["sigla"]
            prov_out.append(p)
        comuni_out = []
        for ist, c in sorted(m["comuni"].items()):
            if c["regione"] != rcod:
                continue
            u = comuni_i.get(pc_di.get(ist))
            if not u:
                continue
            comuni_out.append([ist, c["nome"], provincia_di.get(ist), u.get("sup"),
                               [round(u["suolo"][a][0], 2) if a in u["suolo"] else None for a in anni_c],
                               [round(u["bilancio"][a][2], 2) if a in u["bilancio"] else None for a in anni_c]])
        f = uscita / f"{rcod}.json"
        f.write_text(json.dumps({**comune, "regione": rcod, "nome": rpos["nome"], "province": prov_out,
                                 "comuni": {"anni": [int(a) for a in anni_c],
                                            "campi": ["istat", "nome", "provincia", "superficie [ha]", "suolo consumato [ha]",
                                                      "incremento netto [ha]"], "dati": comuni_out}},
                                ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        dimensioni[f.name] = f.stat().st_size
    it25 = italia_out["suolo"][str(isp["anni"][-1])]
    return {"edizione": edizione, "versione": riferimenti["ispra"]["versione"], "anni": italia_json["anni"],
            "italia_ultimo_anno": {"anno": isp["anni"][-1], "suolo_consumato_ha": it25[CENSIMENTO_VOCI],
                                   "percentuale": round(100 * it25[CENSIMENTO_VOCI] / italia_out["sup"], 2) if italia_out["sup"] else None},
            "comuni": len(abbinati), "note": note, "dimensioni": dimensioni}


def main() -> None:
    prec = sys.argv[sys.argv.index("--precedente") + 1] if "--precedente" in sys.argv else None
    a = [x for x in sys.argv[1:] if not x.startswith("--") and x != prec]
    if len(a) != 3:
        sys.exit(__doc__)
    esito = costruisci(Path(a[0]), Path(a[1]), Path(a[2]), Path(prec) if prec else None, "--forza" in sys.argv)
    print(json.dumps(esito, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
