"""Costruzione dei file della pagina «Produzione e consumi di elettricità» con dati di Terna inventati (niente rete)."""
from __future__ import annotations

import json
from pathlib import Path

from elettricita import costruisci as K

MAPPA = Path(__file__).resolve().parents[2] / "fase5-sito" / "sito" / "dati" / "mappa"


def _scrivi(raw: Path, ds: str, anno: int, colonne: list[str], righe: list[list]):
    (raw / f"{ds}_{anno}.json").write_text(json.dumps({"Columns": {c: "String" for c in colonne}, "Count": len(righe),
                                                       "Data": righe}), encoding="utf-8")


def _raw(tmp: Path) -> Path:
    raw = tmp / "raw"; raw.mkdir()
    for a, fv in ((2020, 100.0), (2021, 130.0)):
        _scrivi(raw, "GenerationPlants", a, ["Anno", "Tipo capacità", "Regione", "Provincia", "Fonte", "MW"], [
            [a, "Lorda", "Emilia-Romagna", "Bologna", "Termoelettrico", 500.0],
            [a, "Lorda", "Emilia-Romagna", "Bologna", "Termoelettrico", 900.0],        # doppione di Terna: vale il minore con CT
            [a, "Lorda", "Emilia-Romagna", "Bologna", "Idrico", 60.0],
            [a, "Lorda", "Emilia-Romagna", "Bologna", "Fotovoltaico", fv],
            [a, "Netta", "Emilia-Romagna", "Bologna", "Fotovoltaico", 1.0],
            [a, "Lorda", "Emilia-Romagna", "ForlÃ¬-Cesena", "Fotovoltaico", 10.0],
            [a, "Lorda", "Sardegna", "Sud Sardegna", "Eolico", 5.0]])
        _scrivi(raw, "CapacityRenewableSources", a, ["Anno", "Tipo capacità", "Regione", "Provincia", "Fonti", "MW"], [
            [a, "Lorda", "Emilia-Romagna", "Bologna", "Bioenergie", 40.0],
            [a, "Lorda", "Emilia-Romagna", "Bologna", "Idrico", 50.0],
            [a, "Lorda", "Emilia-Romagna", "Bologna", "Fotovoltaico", fv],
            [a, "Lorda", "Emilia-Romagna", "Bologna", "Idrico", None]])
        _scrivi(raw, "CapacityThermal", a, ["Anno", "Tipo capacità", "Regione", "Provincia", "Categoria", "Sottocategoria", "MW"], [
            [a, "Lorda", "Emilia-Romagna", "Bologna", "Cogenerative", "Ciclo combinato", 300.0],
            [a, "Lorda", "Emilia-Romagna", "Bologna", "Non cogenerative", "Turbine a gas", 300.0]])
        # Total: consumi per attività e classe (si sommano per settore). ElectricalEnergy: nel 2021 manca una riga di
        # industria (come Brescia e Taranto 2019–2020 nei dati veri) e non deve contare
        _scrivi(raw, "Total", a, ["Anno", "Regione", "Provincia", "Settore", "Attività", "Classe", "GWh"], [
            [a, "Emilia-Romagna", "Bologna", "Industria", "Attività manifatturiere", "Metallurgia", 10.0],
            [a, "Emilia-Romagna", "Bologna", "Industria", "Attività manifatturiere", "Alimentari", 5.0],
            [a, "Emilia-Romagna", "Bologna", "Domestico", None, None, 3.0],
            [a, "Emilia-Romagna", "Bologna", "Servizi", "Commercio", None, 2.0],
            [a, "Emilia-Romagna", "Bologna", "Agricoltura", None, None, 1.0]])
        _scrivi(raw, "ElectricalEnergy", a, ["Anno", "Regione", "Provincia", "Settore", "GWh"], [
            [a, "Emilia-Romagna", "Bologna", "Industria", 5.0]] + ([] if a == 2021 else [[a, "Emilia-Romagna", "Bologna", "Industria", 10.0]]) + [
            [a, "Emilia-Romagna", "Bologna", "Domestico", 3.0], [a, "Emilia-Romagna", "Bologna", "Servizi", 2.0],
            [a, "Emilia-Romagna", "Bologna", "Agricoltura", 1.0]])
        # (21/11/2026) produzione ed emissioni per la grandezza «Emissioni»
        _scrivi(raw, "ElectricityBySource", a, ["Anno", "Tipo produzione", "Regione", "Provincia", "Fonte", "GWh"], [
            [a, "Lorda", "Emilia-Romagna", "Bologna", "Termoelettrico", 1000.0],
            [a, "Lorda", "Emilia-Romagna", "Bologna", "Idrico", 300.0],
            [a, "Lorda", "Emilia-Romagna", "Bologna", "Fotovoltaico", 500.0],
            [a, "Netta", "Emilia-Romagna", "Bologna", "Termoelettrico", 950.0],
            [a, "Lorda", "Sardegna", "Sud Sardegna", "Termoelettrico", 400.0],
            [a, "Lorda", "Sardegna", "Sud Sardegna", "Eolico", 100.0]])
        _scrivi(raw, "ProductionRenewableSources", a, ["Anno", "Tipo produzione", "Regione", "Provincia", "Fonte rinnovabile", "GWh"], [
            [a, "Lorda", "Emilia-Romagna", "Bologna", "Bioenergie", 200.0],
            [a, "Lorda", "Emilia-Romagna", "Bologna", "Idrico", 250.0],
            [a, "Lorda", "Emilia-Romagna", "Bologna", "Fotovoltaico", 500.0]])
        # come nei file veri: colonne Anno, Combustibile, Produzione, Regione, Emissioni; «Gas Naturale» dal 2021
        gas = "Gas naturale" if a == 2020 else "Gas Naturale"
        _scrivi(raw, "GrossVsCO2Emissions", a, ["Anno", "Combustibile", "Produzione", "Regione", "Emissioni (milioni di tonnellate)"], [
            [a, gas, 800.0, "Emilia-Romagna", 0.3],
            [a, "Bioenergie", 200.0, "Emilia-Romagna", 0.02],
            [a, "Solidi", None, "Emilia-Romagna", None],
            [a, "Solidi", 300.0, "Sardegna", 0.27],
            [a, gas, 100.0, "Sardegna", 0.04]])
        _scrivi(raw, "ConsumptionBySource", a, ["Anno", "Regione", "Fonte", "GWh"], [
            [a, "Emilia-Romagna", "Termoelettrico tradizionale", 20.0], [a, "Emilia-Romagna", "Saldo import/export", -4.0],
            [a, "Trentino-Alto Adige", "Idrico rinnovabile", 7.0]])
    return raw


def test_costruisci(tmp_path):
    esito = K.costruisci(_raw(tmp_path), tmp_path / "out", MAPPA)
    it = json.loads((tmp_path / "out" / "italia.json").read_text(encoding="utf-8"))
    assert esito["anni"]["capacita"] == [2020, 2021] and "italia.json" in esito["dimensioni"]
    er = next(r for r in it["regioni"] if r["cod"] == "08")
    ids = [v["id"] for v in it["voci"]["capacita"]]
    c21 = dict(zip(ids, er["capacita"]["2021"]))
    # termoelettrico = min(doppione più alto 900, somma per categoria 600) − bioenergie 40
    assert c21["termo"] == 560 and c21["bio"] == 40 and c21["idro"] == 50 and c21["pomp"] == 10
    assert c21["fv"] == 140                                     # Bologna 130 + Forlì-Cesena 10 (nome riparato)
    cons = dict(zip([v["id"] for v in it["voci"]["consumi"]], er["consumi"]["2021"]))
    assert cons == {"ind": 15, "ser": 2, "dom": 3, "agr": 1}    # da Total, righe di dettaglio sommate
    # confronto con ElectricalEnergy: solo Bologna 2021 supera il 5 % (6 contro 21 GWh); nel log e in «note»
    assert len(it["note"]) == 1 and "2021, Bologna" in it["note"][0] and esito["note"] == it["note"]
    rich = dict(zip([v["id"] for v in it["voci"]["richiesta"]], er["richiesta"]["2021"]))
    assert rich["saldo"] == -4 and rich["termo"] == 20
    # obiettivi: Tabella A; Trentino-Alto Adige = Bolzano + Trento
    assert er["obiettivi"][-1] == 6330 and next(r for r in it["regioni"] if r["cod"] == "04")["obiettivi"][-1] == 515 + 631
    # la somma delle righe della Tabella A fa 80.002 MW (il decreto scrive 80.001: arrotondamenti)
    assert sum(r["obiettivi"][-1] for r in it["regioni"]) == 80002
    sard = json.loads((tmp_path / "out" / "20.json").read_text(encoding="utf-8"))
    sud = next(p for p in sard["province"] if p["nome"] == "Sud Sardegna")
    assert sud["storica"] is True and sud["cod"] is None
    fc = next(p for p in json.loads((tmp_path / "out" / "08.json").read_text(encoding="utf-8"))["province"] if p["sigla"] == "FC")
    assert fc["nome"] == "Forlì-Cesena"


def test_emissioni(tmp_path):
    """Fattori di emissione, energia primaria, subtotali per zona di mercato e Italia (dati inventati)."""
    K.costruisci(_raw(tmp_path), tmp_path / "out", MAPPA)
    it = json.loads((tmp_path / "out" / "italia.json").read_text(encoding="utf-8"))
    assert it["anni"]["emissioni"] == [2020, 2021]
    assert [v["id"] for v in it["emissioni"]["voci"]] == ["gas", "solidi", "petroliferi", "altri", "bio"]
    er = next(r for r in it["regioni"] if r["cod"] == "08")
    p, e, t = er["emissioni"]["2021"]
    assert p == [800, 0, 0, 0, 200] and e == [300, 0, 0, 0, 20]          # GWh e kt
    # gas: 0,3 Mt / 2,467 tCO2/tep (fattore 2022, il primo pubblicato, per gli anni prima); bioenergie: 200 GWh × 0,086 / 0,35
    assert t[0] == round(0.3e6 / 2.467) and t[4] == round(200_000 * 0.086 / 0.35)
    ind = dict(zip(it["emissioni"]["indicatori"], er["indicatori"]["2021"]))
    # produzione: termo 800 + bio 200 + idro 250 + pompaggi 50 + fv 500; totale senza pompaggi 1750, rinnovabili 950
    assert ind["termo_gwh"] == 1000 and ind["fer_gwh"] == 950 and ind["totale_gwh"] == 1750 and ind["co2_kt"] == 320
    assert ind["fattore_medio"] == round(320 / 1750, 4) and ind["fattore_termo"] == 0.32
    assert ind["tep_mwh"] == round((0.3e6 / 2.467 + 200_000 * 0.086 / 0.35) / 1_000_000, 4)
    sa = dict(zip(it["emissioni"]["indicatori"], next(r for r in it["regioni"] if r["cod"] == "20")["indicatori"]["2021"]))
    assert sa["fattore_medio"] == 0.62 and sa["fattore_termo"] == 0.775        # 310 kt / 500 GWh e / 400 GWh
    assert sa["tep"] == round(0.27e6 / 3.903 + 0.04e6 / 2.467)
    # zone di mercato come zone.json del sito; subtotali = somme prima dei rapporti
    zone = {z["id"]: z for z in it["zone"]}
    sito = json.loads((MAPPA / "zone.json").read_text(encoding="utf-8"))["zone"]
    assert [(z["id"], z["regioni"]) for z in it["zone"]] == [(z["id"], z["regioni"]) for z in sito]
    assert zone["NORD"]["indicatori"]["2021"] == er["indicatori"]["2021"]
    assert zone["CNOR"]["indicatori"]["2021"] is None                          # nessun dato nelle sue regioni
    tot = dict(zip(it["emissioni"]["indicatori"], it["emissioni"]["italia"]["2021"]))
    assert tot["co2_kt"] == 630 and tot["fattore_medio"] == 0.28 and tot["fattore_termo"] == 0.45
    # riferimenti: MEF 0,187 tep/MWh e ISPRA 430/2026 con fonte e data di lettura (niente numeri nel JavaScript)
    rif = it["emissioni"]["riferimenti"]
    assert rif["mef"]["valore"] == 0.187 and "EEN 3/08" in rif["mef"]["fonte"]
    assert "430/2026" in rif["ispra"]["fonte"] and rif["ispra"]["serie"]["produzione"]["anni"]["2024"] == 0.2094
    assert rif["letto"] and set(rif["ispra"]["serie"]) >= {"termoelettrica", "produzione", "consumi"}


def test_energia_primaria():
    rif = K.riferimenti()
    assert K.energia_primaria("gas", 2024, 100.0, 0.0371, rif) == 0.0371e6 / 2.474
    assert K.energia_primaria("solidi", 2030, 10.0, 0.01, rif) == 0.01e6 / 3.861      # dopo il 2024: fattore 2024
    assert abs(K.energia_primaria("altri", 2024, 35.0, 0.05, rif) - 35_000 * 0.086 / 0.35) < 1e-6
    assert abs(K.energia_primaria("gas", 2024, 35.0, 0.0, rif) - 35_000 * 0.086 / 0.35) < 1e-6   # senza emissioni: rendimento
    assert K.indicatori(None, None) is None


def test_riserva_electricalenergy(tmp_path):
    """Anni senza Total: consumi da ElectricalEnergy, nessuna nota."""
    raw = _raw(tmp_path)
    _scrivi(raw, "ElectricalEnergy", 2022, ["Anno", "Regione", "Provincia", "Settore", "GWh"], [
        [2022, "Emilia-Romagna", "Bologna", "Industria", 7.0], [2022, "Emilia-Romagna", "Bologna", "Industria", 4.0]])
    K.costruisci(raw, tmp_path / "out", MAPPA)
    it = json.loads((tmp_path / "out" / "italia.json").read_text(encoding="utf-8"))
    er = next(r for r in it["regioni"] if r["cod"] == "08")
    assert er["consumi"]["2022"][0] == 11 and er["consumi"]["2021"][0] == 15
    # (22/11/2026) più l'avviso del controllo anti-salto (consumi 2021 +31 % sulla media del 2020 e del 2022)
    assert it["anni"]["consumi"] == [2020, 2021, 2022] and len([n for n in it["note"] if n.startswith("Consumi")]) == 1
    assert [n for n in it["note"] if n.startswith("Controllo salti: consumi 2021")]


def test_confronta_consumi():
    tot = {("Puglia", "Taranto", 2019, "ind"): 100.0, ("Puglia", "Bari", 2019, "ind"): 100.0}
    ee = {("Puglia", "Taranto", 2019, "ind"): 94.0, ("Puglia", "Bari", 2019, "ind"): 96.0}
    note = K.confronta_consumi(tot, ee)
    assert len(note) == 1 and "Taranto" in note[0] and "-6 %" in note[0]


def test_regione_sconosciuta(tmp_path):
    raw = _raw(tmp_path)
    _scrivi(raw, "ConsumptionBySource", 2022, ["Anno", "Regione", "Fonte", "GWh"], [[2022, "Atlantide", "Eolico", 1.0]])
    try:
        K.costruisci(raw, tmp_path / "out", MAPPA)
    except ValueError as e:
        assert "Atlantide" in str(e)
    else:
        raise AssertionError("regione sconosciuta non segnalata")
