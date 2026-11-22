"""Anni copiati da un altro anno nel Download Center di Terna (22/11/2026): riconoscimento, ricostruzione, note.

Nei dati veri ElectricityBySource 2017 è la copia esatta del 2008 (Italia 319 130 GWh invece di ~295 800): qui lo
stesso caso con dati inventati sulle 9 province dell'Emilia-Romagna (servono almeno MIN_RIGHE_COPIA righe con valore)."""
from __future__ import annotations

import json
from pathlib import Path

from elettricita import costruisci as K

MAPPA = Path(__file__).resolve().parents[2] / "fase5-sito" / "sito" / "dati" / "mappa"
PROVINCE = ["Bologna", "Ferrara", "Forlì-Cesena", "Modena", "Parma", "Piacenza", "Ravenna", "Reggio Nell'Emilia", "Rimini"]
ER = "Emilia-Romagna"


def _scrivi(raw: Path, ds: str, anno: int, colonne: list[str], righe: list[list]):
    (raw / f"{ds}_{anno}.json").write_text(json.dumps({"Columns": {c: "String" for c in colonne}, "Count": len(righe),
                                                       "Data": righe}, ensure_ascii=False), encoding="utf-8")


IDRO = {2005: 0.83, 2008: 0.91, 2012: 0.88, 2016: 1.0, 2017: 1.07, 2018: 0.97}     # idraulicità dell'anno (valori diversi da un anno all'altro)


def _ebs(a: int, k: float) -> list[list]:
    """Produzione lorda per provincia: termo 1000·k·(i+1), idrico 100·h·(i+1) + 10 di pompaggi, fotovoltaico 50·k·(i+1)."""
    out = []
    for i, p in enumerate(PROVINCE):
        out += [[a, "Lorda", ER, p, "Termoelettrico", 1000.0 * k * (i + 1)],
                [a, "Lorda", ER, p, "Idrico", 100.0 * IDRO[a] * (i + 1) + 10.0],
                [a, "Lorda", ER, p, "Fotovoltaico", 50.0 * k * (i + 1)]]
    return out


def _prs(a: int, k: float) -> list[list]:
    out = []
    for i, p in enumerate(PROVINCE):
        out += [[a, "Lorda", ER, p, "Idrico", 100.0 * IDRO[a] * (i + 1)],
                [a, "Lorda", ER, p, "Fotovoltaico", 50.0 * k * (i + 1)],
                [a, "Lorda", ER, p, "Bioenergie", 20.0 * k * (i + 1) + 0.37]]
    return out


def _pt(a: int, k: float) -> list[list]:
    """ProductionThermal: due righe per chiave (lorda = maggiore, netta), due sottocategorie per provincia."""
    out = []
    for i, p in enumerate(PROVINCE):
        for sott, quota in (("Ciclo combinato", 0.6), ("Turbine a gas", 0.4)):
            lordo = 1000.0 * k * (i + 1) * quota
            out += [[a, ER, p, "Non cogenerative", sott, lordo], [a, ER, p, "Non cogenerative", sott, lordo * 0.95]]
    return out


COL_EBS = ["Anno", "Tipo produzione", "Regione", "Provincia", "Fonte", "Produzione (GWh)"]
COL_PRS = ["Anno", "Tipo produzione", "Regione", "Provincia", "Fonte rinnovabile", "Produzione (GWh)"]
COL_PT = ["Anno", "Regione", "Provincia", "Categoria", "Sottocategoria", "Produzione (GWh)"]
COL_CBS = ["Anno", "Regione", "Fonte", "Copertura (GWh)"]


def _raw(tmp: Path, con_pt: bool = True) -> Path:
    raw = tmp / "raw"
    raw.mkdir()
    fattori = {2008: 2.013, 2016: 1.0, 2017: 1.1, 2018: 1.2}
    for a, k in fattori.items():
        righe = _ebs(a, k) if a != 2017 else [[2017] + r[1:] for r in _ebs(2008, fattori[2008])]   # 2017 = 2008
        _scrivi(raw, "ElectricityBySource", a, COL_EBS, righe)
        _scrivi(raw, "ProductionRenewableSources", a, COL_PRS, _prs(a, k))
        if con_pt or a != 2017:
            _scrivi(raw, "ProductionThermal", a, COL_PT, _pt(a, k))
    # pompaggi 2017 per regione (produzione degli impianti di pompaggio): 135 GWh (negli altri anni 9 × 10 = 90)
    _scrivi(raw, "ConsumptionBySource", 2017, COL_CBS, [[2017, ER, "Idrico tradizionale", 135.0]])
    return raw


def test_trova_copie(tmp_path):
    raw = _raw(tmp_path)
    copie = K.trova_copie(raw)
    assert copie == {"ElectricityBySource": {2017: {"di": 2008, "tipo": "identico"}}}
    assert "copia del 2008" in K.descrivi_copia("ElectricityBySource", 2017, copie["ElectricityBySource"][2017])


def test_trova_copie_contiene_e_valori(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    base = _ebs(2012, 1.0)
    _scrivi(raw, "GenerationPlants", 2012, COL_EBS, base)
    # 2017: tutte le righe del 2012 più qualche riga in più (come GenerationPlants 2017 nei dati veri)
    _scrivi(raw, "GenerationPlants", 2017, COL_EBS, [[2017] + r[1:] for r in base] + [[2017, "Lorda", ER, "Bologna", "Eolico", 3.0]])
    # 2007: i valori del 2005 su province diverse (come ElectricityBySource 2007)
    r05 = _ebs(2005, 1.3)
    valori = [r[-1] for r in r05]
    _scrivi(raw, "ElectricityBySource", 2005, COL_EBS, r05)
    _scrivi(raw, "ElectricityBySource", 2007, COL_EBS, [[2007] + r[1:-1] + [v] for r, v in zip(r05, valori[1:] + valori[:1])])
    _scrivi(raw, "ElectricityBySource", 2006, COL_EBS, [[2006] + r[1:-1] + [r[-1] * 1.7] for r in _ebs(2005, 1.0)])
    # file piccoli (prove, anni quasi vuoti): non si confrontano
    for a in (2020, 2021):
        _scrivi(raw, "Total", a, ["Anno", "Regione", "Provincia", "Settore", "GWh"], [[a, ER, "Bologna", "Domestico", 3.0]])
    assert K.trova_copie(raw) == {"ElectricityBySource": {2007: {"di": 2005, "tipo": "valori"}},
                                  "GenerationPlants": {2017: {"di": 2012, "tipo": "contiene"}}}


def _italia(out: Path) -> dict:
    return json.loads((out / "italia.json").read_text(encoding="utf-8"))


def test_ricostruzione_produzione(tmp_path, capsys):
    esito = K.costruisci(_raw(tmp_path), tmp_path / "out", MAPPA)
    it = _italia(tmp_path / "out")
    er = next(r for r in it["regioni"] if r["cod"] == "08")
    ids = [v["id"] for v in it["voci"]["produzione"]]
    p17 = dict(zip(ids, er["produzione"]["2017"]))
    s = sum(range(1, 10))                                     # 45
    # termo (lordo di ProductionThermal 1100·45) − bioenergie; idrico rinnovabile 107·45; pompaggi 135 (regione)
    bio = 22 * s + 9 * 0.37
    assert p17["termo"] == round(1100 * s - bio, 1) and p17["bio"] == round(bio, 1)
    assert p17["idro"] == round(107 * s, 1) and p17["pomp"] == 135.0 and p17["fv"] == round(55 * s, 1)
    # non i valori del 2008 copiati (termo 2000·45)
    assert sum(er["produzione"]["2017"]) < sum(er["produzione"]["2018"])
    # province: pompaggi divisi come la media del 2016 e del 2018 (10 per provincia → 15 ciascuna)
    prov = json.loads((tmp_path / "out" / "08.json").read_text(encoding="utf-8"))["province"]
    bo = next(p for p in prov if p["nome"] == "Bologna")
    assert dict(zip(ids, bo["produzione"]["2017"]))["pomp"] == 15.0
    note = it["note"]
    assert any("ElectricityBySource 2017: copia del 2008" in n for n in note)
    assert any(n.startswith("Produzione 2017 ricostruita") and "ProductionThermal" in n and "media del 2016 e del 2018" in n
               for n in note)
    assert esito["controlli"]["copie"] == ["Terna, ElectricityBySource 2017: copia del 2008 (stesse righe); "
                                           "i valori del 2017 non si usano"]
    assert "copia del 2008" in capsys.readouterr().err


def test_anno_copiato_senza_fonti(tmp_path):
    """Senza ProductionThermal del 2017 la produzione 2017 resta vuota (niente numeri sbagliati) con la nota."""
    K.costruisci(_raw(tmp_path, con_pt=False), tmp_path / "out", MAPPA)
    it = _italia(tmp_path / "out")
    assert 2017 not in it["anni"]["produzione"] and 2016 in it["anni"]["produzione"]
    assert any(n.startswith("Produzione 2017: dato di Terna non disponibile") for n in it["note"])


def test_ricostruzione_capacita(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    col_gp = ["Anno", "Tipo capacità", "Regione", "Provincia", "Fonte", "MW"]
    col_crs = ["Anno", "Tipo capacità", "Regione", "Provincia", "Fonti", "MW"]
    col_ct = ["Anno", "Tipo capacità", "Regione", "Provincia", "Categoria", "Sottocategoria", "MW"]

    def gp(a, k):
        return [r for i, p in enumerate(PROVINCE) for r in (
            [a, "Lorda", ER, p, "Termoelettrico", 300.0 * k * (i + 1)], [a, "Lorda", ER, p, "Idrico", 40.0 * (i + 1) + 8.0],
            [a, "Lorda", ER, p, "Fotovoltaico", 30.0 * k * (i + 1)])]
    for a, k in ((2012, 3.0), (2016, 1.0), (2017, 1.1), (2018, 1.2)):
        _scrivi(raw, "GenerationPlants", a, col_gp, gp(a, k) if a != 2017 else [[2017] + r[1:] for r in gp(2012, 3.0)])
        _scrivi(raw, "CapacityRenewableSources", a, col_crs, [r for i, p in enumerate(PROVINCE) for r in (
            [a, "Lorda", ER, p, "Idrico", 40.0 * (i + 1)], [a, "Lorda", ER, p, "Fotovoltaico", 30.0 * k * (i + 1)])])
        _scrivi(raw, "CapacityThermal", a, col_ct, [[a, "Lorda", ER, p, "Non cogenerative", "Ciclo combinato", 300.0 * k * (i + 1)]
                                                   for i, p in enumerate(PROVINCE)])
    esito = K.costruisci(raw, tmp_path / "out", MAPPA)
    it = _italia(tmp_path / "out")
    er = next(r for r in it["regioni"] if r["cod"] == "08")
    ids = [v["id"] for v in it["voci"]["capacita"]]
    c17 = dict(zip(ids, er["capacita"]["2017"]))
    s = 45
    assert c17["termo"] == 330 * s and c17["idro"] == 40 * s and c17["pomp"] == 8 * 9 and c17["fv"] == 33 * s
    assert any(n.startswith("Capacità 2017 ricostruita") for n in esito["note"])


def test_controlla_salti():
    serie = {2016: 289_768, 2017: 360_854, 2018: 289_708, 2019: 293_853}
    note = K.controlla_salti(serie, "produzione", "GWh")
    assert len(note) == 1 and "produzione 2017" in note[0] and "+25 %" in note[0] and "360.854" in note[0]
    assert K.controlla_salti({2016: 100, 2017: 114, 2018: 100}, "x", "GWh") == []
