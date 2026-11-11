"""Listini delle convenzioni e indici dei prezzi pubblicabili (11/11/2026): solo prezzi dei listini, PSV ARERA e PFOR;
mai PUN né TTF nel file pubblico."""
from __future__ import annotations

import datetime as dt
import io
import json
import zipfile
from pathlib import Path

import openpyxl
import pandas as pd

from mercati_energia import archivio, indici, listini, prezzi_pubblici as P

MESI = ["gennaio", "febbraio", "marzo"]


def _listino(lotto: str, anno: int, pun: dict, spread: float) -> bytes:
    """Excel con la forma dei listini Intercent-ER: titolo, intestazioni con PUN e prezzo per mese, una riga per fascia."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([f'Energia Elettrica 19 - Listino Lotto {lotto} "prova"'])
    intest = ["Numero Lotto", "CODICE CIG", "\n€/KWh PUN medio mensile per fascia", "Spread €/KWh",
              "(*) (**)\nPREZZO OFFERTO PER UM \n€/KWh\n(IVA esclusa)\n"]
    for m in MESI:
        intest += [f"PUNMM\n €/KWh \n{m} {anno}\n(IVA esclusa)",
                   f"PUNMM\n+ spread (comprensivo del valore GO)\n=\nPrezzo €/KWh \n{m} {anno}\n(IVA esclusa)"]
    intest += ["Punti di prelievo multiorari", "IVA (%)"]
    ws.append(intest)
    for i, f in enumerate(["F1", "F2", "F3"]):
        r = [lotto if i == 0 else None, "CIG" if i == 0 else None, 0.105, spread, 0.105 + spread]
        for k in range(len(MESI)):
            r += [pun[f][k], round(pun[f][k] + spread, 5)]
        r += [f, 22 if i == 0 else None]
        ws.append(r)
    ws.append(["(*) nota a piè di tabella"])
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


PUN = {"F1": [0.15126, 0.12228, 0.14302], "F2": [0.1374, 0.11984, 0.15391], "F3": [0.11829, 0.1053, 0.13809]}


def test_legge_solo_il_prezzo_dal_listino():
    df = listini.leggi_excel(_listino("1", 2026, PUN, 0.00187), "intercenter-ee19-2026")
    assert len(df) == 9 and set(df.fascia) == {"F1", "F2", "F3"} and set(df.lotto) == {"1"}
    g = df.set_index(["fascia", "mese"]).prezzo
    assert g[("F1", "2026-01")] == 153.13 and g[("F3", "2026-03")] == 139.96
    # nessun valore del solo PUN (151,26) e nessun prezzo «di gara» senza mese (106,87)
    assert 151.26 not in set(df.prezzo) and 106.87 not in set(df.prezzo)


def test_zip_e_cartella_a_mano(tmp_path):
    z = io.BytesIO()
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("Listini/Listino_L_1.xlsx", _listino("1", 2026, PUN, 0.00187))
        f.writestr("Listini/Listino_L_2.xlsx", _listino("2", 2026, PUN, 0.00325))
        f.writestr("leggimi.txt", "non un listino")
    df = listini.leggi_file(z.getvalue(), "listini.zip", "intercenter-ee19-2026")
    assert len(df) == 18 and set(df.lotto) == {"1", "2"}
    d = tmp_path / "listini_manuali" / "intercenter-ee18-2025"
    d.mkdir(parents=True)
    (d / "Listino_EE_18_L_1.xlsx").write_bytes(_listino("1", 2025, PUN, 0.002))
    (d / "listino.toml").write_text('serie = "intercenter-ee19-2026"\ntitolo = "Energia elettrica 18 – fornitura 2025"\n')
    esito = listini.aggiorna(tmp_path, None)
    assert esito == {"intercenter-ee18-2025": 9}
    letto = listini.leggi(tmp_path)
    assert set(letto.serie) == {"intercenter-ee19-2026"} and set(letto.titolo) == {"Energia elettrica 18 – fornitura 2025"}


def _archivio(tmp_path: Path) -> None:
    """Archivio con listini 2025 e 2026, PSV ARERA, PUN, TTF e future: nel file pubblico solo i primi due e il PFOR."""
    righe = []
    for anno, conv, tit, spread in ((2025, "intercenter-ee18-2025", "Energia elettrica 18 – fornitura 2025", 2.0),
                                    (2026, "intercenter-ee19-2026", "Energia elettrica 19 – fornitura 2026", 1.87)):
        for m in range(1, 13 if anno == 2025 else 11):
            for f, base in (("F1", 150.0), ("F2", 140.0), ("F3", 120.0)):
                righe.append({"convenzione": conv, "centrale": "Intercent-ER", "lotto": "1", "fascia": f,
                              "mese": f"{anno}-{m:02d}", "data": dt.date(anno, m, 1),
                              "prezzo": base + m + spread, "unita": "€/MWh", "file": "x.xlsx",
                              "serie": "intercenter-ee19-2026", "titolo": tit})
    archivio.aggiorna(tmp_path, "listini", pd.DataFrame(righe), listini.CHIAVI, "data")
    imp = [{"indice": "PSV_DA", "mese": f"{a}-{m:02d}", "data": dt.date(a, m, 1), "valore": 35.0 + m + (a - 2025)}
           for a in (2025, 2026) for m in range(1, 13) if not (a == 2026 and m > 10)]
    archivio.aggiorna(tmp_path, "indici_importati", pd.DataFrame(imp), ["indice", "mese"], "data")
    # PUN orario con un valore riconoscibile (777,77) e TTF giornaliero (66,66): non devono uscire
    archivio.aggiorna(tmp_path, "mgp_prezzi", pd.DataFrame(
        {"inizio_utc": pd.date_range("2026-01-01", periods=48, freq="h", tz="UTC"), "zona": "PUN", "prezzo": 777.77,
         "minuti": 60}), ["inizio_utc", "zona"], "inizio_utc")
    archivio.aggiorna(tmp_path, "ttf_eex", pd.DataFrame(
        {"data": pd.date_range("2025-08-01", "2026-09-30", freq="D").date, "prezzo": 66.66}), ["data"], "data")
    indici.calcola(tmp_path)


def test_file_pubblico_senza_pun_ne_ttf(tmp_path):
    _archivio(tmp_path)
    conv = tmp_path / "conv"
    conv.mkdir()
    (conv / "ee19.toml").write_text('[convenzione]\nid = "intercenter-ee19-2026"\nente = "Intercent-ER"\n'
                                    'titolo = "Energia elettrica 19 – fornitura 2026"\n[listino]\nurl = "https://x"\n'
                                    'lotti = { "1" = "Lotto 1 – aziende sanitarie, media tensione" }\n')
    d = P.scrivi(tmp_path, conv, tmp_path / "sito" / "prezzi" / "indici.json", dt.date(2026, 11, 12))
    assert d["anni"] == [2025, 2026]
    el, gas = d["sezioni"]
    assert [i["titolo"] for i in el["indici"]] == ["Intercent-ER"]
    ip = el["indici"][0]
    assert ip["lotto_predefinito"] == "1" and ip["lotti"]["1"]["nome"] == "Lotto 1 – aziende sanitarie, media tensione"
    v = ip["lotti"]["1"]["varianti"]
    assert list(v) == ["F1", "F2", "F3"] and v["F1"]["2025"][0] == 153.0 and v["F1"]["2026"][9] == 161.87
    assert v["F1"]["2026"][10:] == [None, None]                       # novembre e dicembre non ancora pubblicati
    assert "Energia elettrica 18 – fornitura 2025 (2025)" in ip["fonte"]
    ids = [i["id"] for i in gas["indici"]]
    assert ids == ["psv-da-arera", "pfor"]
    assert [i["decimali"] for i in gas["indici"]] == [4, 4] and el["indici"][0]["decimali"] == 2   # (11/11) PSV e PFOR: 4
    psv = gas["indici"][0]["lotti"][""]["varianti"][""]
    assert psv["2025"][0] == 36.0 and psv["2026"][9] == 46.0 and gas["indici"][0]["licenza"] == "CC BY-SA 4.0"
    pf = gas["indici"][1]
    pv = pf["lotti"][""]["varianti"][""]
    assert pv["2026"][9] == pv["2026"][10] == pv["2026"][11]                                  # IV trimestre
    assert pf["dettagli"]["2026-10"]["trimestre"] == "2026 T4"
    testo = (tmp_path / "sito" / "prezzi" / "indici.json").read_text(encoding="utf-8")
    numeri = json.loads(testo)
    # nessun valore del PUN né del TTF giornaliero: il PFOR (66,66 €/MWh di media) è l'unico numero dal TTF
    assert "777.77" not in testo and "PUN_F1" not in testo and "TTF_MENSILE" not in testo
    tutti = [x for s in numeri["sezioni"] for i in s["indici"] for lo in i["lotti"].values()
             for vv in lo["varianti"].values() for a in vv.values() for x in a if x is not None]
    assert 777.77 not in tutti


def test_indici_ammessi():
    assert P.INDICI_AMMESSI == {"PSV_DA", "PFOR"}


def _consip() -> bytes:
    """Excel con la forma dei corrispettivi Consip: foglio del PUN (da non leggere) e un foglio per lotto."""
    wb = openpyxl.Workbook()
    pun = wb.active
    pun.title = "PUN Index GME e PUN per fascia"
    pun.append(["Mese", "F0", "F1", "F2", "F3"])
    pun.append([dt.datetime(2026, 10, 1), 230.82, 233.39, 252.14, 215.88])
    for n, nome, spread in ((6, "Emilia Romagna ", 3.5), (17, "Italia", 2.0)):
        ws = wb.create_sheet(f"Lotto {n}")
        ws.append(["torna al SOMMARIO"])
        ws.append([f"Lotto {n}: {nome}"])
        ws.append(["Opzione Verde", None, "2,00 Euro/MWh"])
        ws.append(["Forniture a Prezzo variabile a 12 e 24 mesi"])
        ws.append([None, "Fascia oraria", "ΨVAR", None, dt.datetime(2025, 10, 1), dt.datetime(2026, 10, 1)])
        for f, base in (("F0", 111.04), ("F1", 117.83), ("F2", 121.66), ("F3", 99.48)):
            ws.append([None, f, spread, None, round(base + spread, 2), round(base + 115 + spread, 2)])
        ws.append([f"Lotto {n}: {nome} - Prezzi variabili al netto delle perdite di rete (Euro/MWh)"])
        ws.append([None, "F1", spread, None, 999.0, 999.0])          # seconda tabella: non si legge
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def test_corrispettivi_consip(tmp_path):
    df = listini.leggi_file(_consip(), "EE22 - Corrispettivi - 1026.xlsx", "consip-ee22", "Consip", "consip")
    assert sorted(df.lotto.unique()) == ["17", "6"] and len(df) == 16
    x = df[df.lotto == "6"].set_index(["fascia", "mese"])
    assert x.loc[("F1", "2026-10"), "prezzo"] == 236.33 and x.lotto_nome.iloc[0] == "Emilia Romagna"
    assert 233.39 not in set(df.prezzo) and 999.0 not in set(df.prezzo)   # niente PUN, niente 2ª tabella
    archivio.aggiorna(tmp_path, "listini", df.assign(serie="consip-ee22", titolo="Energia Elettrica 22"),
                      listini.CHIAVI, "data")
    conv = tmp_path / "conv"
    (conv / "fonti").mkdir(parents=True)
    (conv / "fonti" / "listini.toml").write_text('[[listino]]\nid = "consip-ee22"\ncentrale = "Consip"\n'
                                                 'titolo = "Energia Elettrica 22"\nnome = "Consip – Energia Elettrica 22"\n'
                                                 'formato = "consip"\nlotto_predefinito = "6"\nurl = "https://x"\n')
    d = P.costruisci(tmp_path, conv, dt.date(2026, 11, 12))
    ind = d["sezioni"][0]["indici"][0]
    assert ind["titolo"] == "Consip – Energia Elettrica 22" and ind["lotto_predefinito"] == "6"
    assert list(ind["lotti"]) == ["6", "17"] and ind["lotti"]["6"]["nome"] == "Lotto 6: Emilia Romagna"
    assert list(ind["lotti"]["6"]["varianti"]) == ["F1", "F2", "F3", "F0"]
    assert ind["lotti"]["6"]["varianti"]["F1"]["2025"][9] == 121.33 and "perdite di rete" in ind["nota"]


def _listino_gas() -> bytes:
    """Excel con la forma dei listini gas Intercent-ER: valori scritti come testo, uso dalla denominazione."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['Listino Gas Naturale 22, Lotto 1 "prova"'])
    ws.append(["Numero Lotto", "CODICE CIG", "DENOMINAZIONE ARTICOLO OPERATORE ECONOMICO", "Spread offerto\n€/Smc",
               " (*)\nPREZZO OFFERTO PER UM", "PSV\nottobre 2025\n(IVA esclusa)",
               "PSV\n+ spread\n=\nPrezzo €/Smc \nottobre 2025\n(IVA esclusa)", "PSV\ngennaio 2026\n(IVA esclusa)",
               "PSV\n+ spread\n=\nPrezzo €/Smc \ngennaio 2026\n(IVA esclusa)"])
    ws.append(["1", "CIG", "GAS 22_AASS E ALTRI ENTI  TERMICHE", "0.0208", "0.4208", "0.3498", "0.3706", "0.3995", "0.4203"])
    ws.append(["1", "CIG", "GAS 22_AASS E ALTRI ENTI NON TERMICHE", "0.0146", "0.4146", "0.3498", "0.3644", "0.3995",
               "0.41409999999999997"])
    ws.append(["(*) Prezzo per UM offerto dal Fornitore in sede di gara"])
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def test_listino_gas_in_smc(tmp_path):
    df = listini.leggi_excel(_listino_gas(), "intercenter-gn22")
    assert set(df.unita) == {"€/Smc"} and set(df.fascia) == {"Usi termici", "Usi non termici"} and len(df) == 4
    g = df.set_index(["fascia", "mese"]).prezzo
    assert g[("Usi termici", "2025-10")] == 0.3706 and g[("Usi non termici", "2026-01")] == 0.4141
    assert 0.3498 not in set(df.prezzo) and 0.4208 not in set(df.prezzo)      # niente PSV da solo, niente prezzo di gara
    archivio.aggiorna(tmp_path, "listini", df.assign(serie="intercenter-gn22", titolo="Gas naturale 22"),
                      listini.CHIAVI, "data")
    d = P.costruisci(tmp_path, None, dt.date(2026, 11, 12))
    el, gas = d["sezioni"]
    assert el["indici"] == [] and gas["indici"][0]["unita"] == "€/Smc"
    assert gas["indici"][0]["lotti"]["1"]["varianti"]["Usi termici"]["2026"][0] == 0.4203     # 4 decimali


def test_precedenti_nel_file_dei_listini(tmp_path):
    """(11/11/2026) Anche convenzioni/fonti/listini.toml dichiara le convenzioni precedenti (GN21 accanto a GN22)."""
    (tmp_path / "fonti").mkdir()
    (tmp_path / "fonti" / "listini.toml").write_text(
        '[[listino]]\nid = "intercenter-gn22"\ncentrale = "Intercent-ER"\ntitolo = "Gas naturale 22"\nurl = "https://a"\n'
        'lotti = { "1" = "Lotto 1" }\nprecedenti = [ { id = "intercenter-gn21", titolo = "Gas naturale 21", url = "https://b" } ]\n')
    f = {x["id"]: x for x in listini.fonti(tmp_path)}
    assert set(f) == {"intercenter-gn22", "intercenter-gn21"}
    assert f["intercenter-gn21"]["serie"] == "intercenter-gn22" and f["intercenter-gn21"]["lotti"] == {"1": "Lotto 1"}


def test_pfor_storico_ha_la_precedenza(tmp_path):
    """(11/11/2026) Valori trimestrali del PFOR in €/Smc forniti da Paolo: convertiti in €/MWh (III/2020 = valore ARERA
    5,861184 €/MWh), stessi nei tre mesi, prima del calcolo dalle quotazioni."""
    f = tmp_path / "pfor_storico.csv"
    f.write_text("anno;trimestre;pfor_eur_smc\n2020;3;0,062715\n2025;1;0,480040\n2026;4;0,659500\n", encoding="utf-8")
    s = P.pfor_storico(f)
    assert round(s[(2020, 3)], 4) == 5.8612
    _archivio(tmp_path)                       # il TTF di prova (66,66) darebbe un PFOR calcolato diverso
    d = P.costruisci(tmp_path, None, dt.date(2026, 11, 12), file_pfor=f)
    pf = [i for i in d["sezioni"][1]["indici"] if i["id"] == "pfor"][0]
    v = pf["lotti"][""]["varianti"][""]
    assert v["2025"][:3] == [44.8636] * 3 and v["2026"][9:] == [61.6355] * 3
    assert pf["dettagli"]["2026-10"] == {"trimestre": "2026 T4", "metodo": "valore storico", "provvisorio": False}
    assert P.pfor_storico(tmp_path / "manca.csv") == {}
