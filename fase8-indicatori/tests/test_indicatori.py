"""Prove della fase 8 su dati piccoli in tests/dati (nessuna richiesta in rete)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from indicatori_ssn import bdap, calcolo, cli, costanti as K, istat, reporter
from indicatori_ssn.rete import FonteNonDisponibile

DATI = Path(__file__).parent / "dati"
ANNI = [2023, 2024]


def ce():
    return {a: bdap.leggi_testo(DATI / f"ce_{a}.csv", a) for a in ANNI}


# ------------------------------------------------------------------------------------------------ OpenBDAP
def test_importi_e_codici():
    assert bdap.importo("1234567.89") == pytest.approx(1234567.89)
    assert bdap.importo("1.234.567,89") == pytest.approx(1234567.89)
    assert bdap.importo("100,5") == pytest.approx(100.5)
    assert bdap.importo("") is None and bdap.importo(None) is None
    assert bdap.codice(80) == "080" and bdap.codice("41") == "041" and bdap.codice("999.0") == "999"


def test_ce_solo_voci_utili():
    righe = ce()[2024]
    assert {r["voce"] for r in righe} == set(K.VOCI)            # BA0010 scartata
    r = next(r for r in righe if r["cod_ente"] == "114" and r["voce"] == "BA1660")
    assert r["cod_regione"] == "080" and float(r["importo"]) == 25455736


def test_ce_variante_punto_e_virgola():
    righe = bdap.da_testo((DATI / "ce_variante.csv").read_text(encoding="utf-8"), 2025)
    assert [(r["voce"], float(r["importo"])) for r in righe] == [("BA1660", 1234567.89), ("BA1610", 100.5)]
    assert righe[0]["tipo_rilevazione"] == "IV trimestre"


def test_ce_colonne_mancanti():
    with pytest.raises(FonteNonDisponibile):
        bdap.da_testo("a;b\n1;2\n", 2024)


# ------------------------------------------------------------------------------------------------ ReportER
def test_numeri_reporter():
    assert reporter.numero("1.124.403") == 1124403
    assert reporter.numero("0,33") == pytest.approx(0.33)
    assert reporter.numero(".") is None


def test_tabella_giornate():
    d = json.loads((DATI / "reporter_giornate_2024.json").read_text(encoding="utf-8"))
    valori, meta = reporter.leggi_tabella(d)
    per, ignote = reporter.per_ente(valori)
    assert per["114"] == 861172 and per["999"] == 3602183 and per["908"] == 370158
    assert not ignote and meta["aggiornato"] == "20/10/2025"


def test_tabella_popolazione_e_posti_letto():
    pop, _ = reporter.leggi_tabella(json.loads((DATI / "reporter_popolazione_2024.json").read_text()), "Residenti")
    assert reporter.per_ente(pop)[0]["114"] == 1124403
    pl, _ = reporter.leggi_tabella(json.loads((DATI / "reporter_posti_letto_2024.json").read_text()))
    p = reporter.per_ente(pl)[0]
    assert p["114"] == 2936 and p["999"] == 13127


def test_corpo_reporter():
    c = reporter.corpo(K.REPORT_POSTI_LETTO, 2024)
    assert (c["flowId"], c["macroScopeId"], c["scopeId"], c["tabId"]) == (13, 1, 1, 1)
    assert {"id": "DII_95FA321823A416C50C315", "values": [{"value": "1 "}]} in c["activeFilterList"]


# ---------------------------------------------------------------------------------------------------- ISTAT
def test_posas():
    reg = istat.leggi_posas((DATI / "posas_regioni.csv").read_text(encoding="utf-8"), "regioni")
    prov = istat.leggi_posas((DATI / "posas_province.csv").read_text(encoding="utf-8"), "province")
    assert reg["08"] == 4461998
    aree = istat._aree(reg, prov)
    assert aree["ITD5"] == 4461998 and aree["ITD1"] + aree["ITD2"] == reg["04"]
    assert "04" not in aree


def test_ricostruzione():
    r = istat.leggi_ricostruzione((DATI / "ricostruzione_regioni.csv").read_text(encoding="utf-8"))
    assert set(r) == {2018, 2019}
    assert r[2019]["08"] == 4459453              # popolazione al 1/1/2019, vale per il 31/12/2018
    assert r[2018]["08"] < r[2019]["08"]


def test_csv_sdmx():
    t = "DATAFLOW,FREQ,REF_AREA,DATA_TYPE,SEX,AGE,MARITAL_STATUS,TIME_PERIOD,OBS_VALUE\n" \
        "IT1:22_289(1.0),A,IT,JAN,9,TOTAL,99,2025,58943464\nIT1:22_289(1.0),A,ITD5,JAN,9,TOTAL,99,2025,4461998\n"
    assert istat.leggi_csv_sdmx(t) == {"IT": {2025: 58943464.0}, "ITD5": {2025: 4461998.0}}


# ------------------------------------------------------------------------------------------------- calcolo
def costruito():
    rep = {"dati": {"giornate": {2024: {"114": 861172, "908": 370158, "999": 3602183}},
                    "posti_letto": {2024: {"114": 2936, "999": 13127}},
                    "popolazione": {2024: {"114": 1124403, "999": 4482977}}, "accessi_dh": {}},
           "aggiornato": {}}
    pop = {"dati": {"IT": {2023: 58971230, 2024: 58943464}, "ITD5": {2024: 4461998}, "ITE1": {2024: 3657716},
                    "ITD1": {2024: 539679}}, "serie": {2023: "censimento", 2024: "censimento"}}
    return calcolo.costruisci(calcolo.raccogli_ce(ce()), rep, pop, ANNI)


def test_unita_e_gsa():
    r = costruito()
    er = r["regioni"]["08"]["ambiti"][0]
    assert [e["cod"] for e in er["enti"]] == ["114", "908"]                 # GSA e consolidato fuori
    assert er["enti"][0]["nome"] == "Azienda USL della Romagna"
    assert set(r["indice"]["consolidati"]) == {"080", "090", "041"}
    tn = r["regioni"]["04"]["ambiti"]
    assert [a["ce"] for a in tn] == ["041", "042"] and tn[1]["enti"] == []
    # il nome è cambiato tra 2023 e 2024: resta la storia
    assert er["enti"][1]["nomi"][0][:2] == [2023, 2023]


def test_indicatori_2024():
    r = costruito()
    i = ANNI.index(2024)
    romagna = r["regioni"]["08"]["ambiti"][0]["enti"][0]
    d = calcolo.indicatori(romagna, i)
    assert d["spesa"] == 39455736
    assert round(d["leva"], 1) == 75.8 and round(d["incidenza"] * 100, 2) == 1.32 and round(d["peso"] * 100, 2) == 1.33
    assert round(d["per_giornata"], 2) == 45.82 and round(d["per_posto"]) == 13439 and round(d["per_cittadino"], 2) == 35.09
    er = r["indice"]["consolidati"]["080"]
    e = calcolo.indicatori(er, i)
    assert e["spesa"] == 187362060 and round(e["per_giornata"], 2) == 52.01 and round(e["per_posto"]) == 14273
    assert round(e["per_cittadino"], 2) == 41.79                            # residenti SISEPS
    assert er["fonte_pop"] == "siseps" and er["pop_istat"][i] == 4461998
    # componenti
    assert calcolo.indicatori(romagna, i, "elettricita")["spesa"] == 25455736


def test_italia_somma_dei_consolidati():
    r = costruito()
    it, i = r["indice"]["italia"], ANNI.index(2024)
    attesa = sum(calcolo.spesa(c, i) for c in r["indice"]["consolidati"].values())
    assert calcolo.spesa(it, i) == attesa
    assert it["n_regioni"] == [3, 3]
    assert r["indice"]["anni_incompleti_italia"] == ANNI                    # mancano 18 consolidati nella prova
    assert len(it["regioni_mancanti"][i]) == 18 and "Calabria" in it["regioni_mancanti"][i]
    # senza la popolazione delle regioni mancanti non si può togliere: il pro capite dell'Italia resta n.d.
    assert "pop" not in it
    toscana = r["indice"]["consolidati"]["090"]
    assert toscana["pop"][i] == 3657716 and "gg" not in toscana


def test_popolazione_italia_senza_le_regioni_mancanti():
    pop = {"dati": {"IT": {2024: 1000}}, "serie": {}}
    for reg, (_, nuts, _) in K.REGIONI_CE.items():
        if reg not in ("080", "090", "041"):
            pop["dati"].setdefault(nuts, {})[2024] = 40
    r = calcolo.costruisci(calcolo.raccogli_ce(ce()), None, pop, ANNI)
    assert r["indice"]["italia"]["pop"] == [None, 1000 - 18 * 40]
    assert r["indice"]["italia"]["fonte_pop"] == "istat"


def test_nd_senza_denominatori():
    r = costruito()
    toscana_asl = r["regioni"]["09"]["ambiti"][0]["enti"][0]
    d = calcolo.indicatori(toscana_asl, 1)
    assert d["per_cittadino"] is None and d["per_giornata"] is None and d["leva"] is not None


def test_nomi_leggibili():
    n = calcolo.nome_leggibile
    assert n("AZIENDA USL DELLA ROMAGNA") == "Azienda USL della Romagna"
    assert n("A.S.L. TO3") == "A.S.L. TO3"
    assert n("AZIENDA ULSS N. 6 EUGANEA") == "Azienda ULSS n. 6 Euganea"
    assert n("Già scritto") == "Già scritto"


# ----------------------------------------------------------------------------------------------- comando
def test_aggiorna_scrive_i_file(tmp_path, monkeypatch):
    monkeypatch.setattr(K, "ANNI", ANNI)
    cache = tmp_path / "cache"
    (cache / "bdap").mkdir(parents=True)
    for a in ANNI:
        bdap.scrivi_cache(bdap.leggi_testo(DATI / f"ce_{a}.csv", a), cache / "bdap" / f"ce_{a}.csv")
    rep = {"dati": {"giornate": {a: {"114": 861172} for a in ANNI}, "accessi_dh": {a: {} for a in ANNI},
                    "posti_letto": {a: {"114": 2936} for a in ANNI}, "popolazione": {a: {"114": 1124403} for a in ANNI}},
           "aggiornato": {}}
    monkeypatch.setattr(reporter, "scarica", lambda rete, anni: rep)
    monkeypatch.setattr(istat, "scarica", lambda rete, anni, c: {"dati": {"IT": {a: 58943464 for a in ANNI}}, "serie": {}})
    out = tmp_path / "out"
    esito = cli.aggiorna(out, cache, anni=ANNI)
    assert esito["mancanti"] == []
    assert {f.name for f in out.iterdir()} == {"indice.json"} | {f"{m}.json" for m in K.NOMI_REGIONI_MAPPA}
    assert all(n < 200_000 for n in esito["dimensioni"].values())
    indice = json.loads((out / "indice.json").read_text())
    assert indice["anni"] == ANNI and indice["fonti"][0]["licenza"] == "CC BY 4.0"
    assert not any(v in json.dumps(indice) for v in ("BA1650",))           # la telefonia non si pubblica
    for f in out.glob("*.json"):                                           # licenza e citazione in ogni file
        d = json.loads(f.read_text())
        assert "CC BY 4.0" in d["licenza"] and "citando EuGEnio come fonte" in d["licenza"]
        assert d["citazione"].startswith("Fonte: EuGEnio – eugenio.statocritico.it (dati aggiornati il ")


def test_aggiorna_non_scrive_se_manca_una_fonte(tmp_path, monkeypatch):
    monkeypatch.setattr(K, "ANNI", ANNI)

    def guasto(rete, anno, cartella):
        raise FonteNonDisponibile("manutenzione")
    monkeypatch.setattr(bdap, "scarica_anno", guasto)
    monkeypatch.setattr(reporter, "scarica", lambda rete, anni: {"dati": {}, "aggiornato": {}})
    monkeypatch.setattr(istat, "scarica", lambda rete, anni, c: {"dati": {}, "serie": {}})
    with pytest.raises(FonteNonDisponibile):
        cli.aggiorna(tmp_path / "out", tmp_path / "cache", anni=ANNI)
    assert not (tmp_path / "out").exists()
