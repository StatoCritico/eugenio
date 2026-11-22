"""Costruzione dei file della pagina «Carichi elettrici» con dati di Terna inventati (niente rete).

_archivio(tmp) scrive un archivio di prova (settembre e ottobre 2026, con il ritorno all'ora solare e la generazione
oraria in ottobre); lo usa anche la prova nel browser della fase 5.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from elettricita import carichi as K

ROMA = ZoneInfo("Europe/Rome")
ZONE = {"North": 0.58, "Centre-North": 0.08, "Centre-South": 0.15, "South": 0.07, "Calabria": 0.02, "Sicily": 0.06, "Sardinia": 0.04}


def _ms(t_loc: dt.datetime) -> int:
    return int((t_loc - dt.datetime(1, 1, 1)).total_seconds() * 1000)


def _italia(i: int, t: dt.datetime) -> float:
    ora = t.astimezone(ROMA).hour + t.minute / 60
    return 30000 + 8000 * math.sin((ora - 6) / 24 * 2 * math.pi) + (i % 7) * 10


def _scrivi(f: Path, colonne: list[str], righe: list):
    f.write_text(json.dumps({"Columns": {c: "x" for c in colonne}, "Count": len(righe), "Data": righe}), encoding="utf-8")


def _archivio(tmp: Path) -> Path:
    arch = tmp / "archivio"
    arch.mkdir()
    for a, m in ((2026, 9), (2026, 10)):
        t0, n = K._griglia(a, m)
        carico, att, rin = [], [], []
        doppie = []
        for i in range(n):
            t = t0 + i * K.QUARTO
            loc = t.astimezone(ROMA).replace(tzinfo=None)
            data = _ms(loc) if m == 10 else loc.strftime("%Y-%m-%dT%H:%M:%S")   # ottobre in ms, settembre in ISO
            it = _italia(i, t)
            parti = {z: round(it * q + (i % 5) * (j + 1), 3) for j, (z, q) in enumerate(ZONE.items())}
            parti_tot = sum(parti.values())
            righe = [[data, round(parti_tot, 3), 0.0, "Italy"]] + [[data, v, 0.0, z] for z, v in parti.items()]
            if m == 10 and loc.date() == dt.date(2026, 10, 25) and loc.hour == 2:
                doppie.append(righe)
            else:
                carico += righe
            # generazione [GW]: oraria in ottobre (solo all'ora piena), quartoraria in settembre
            if m == 10 and loc.minute:
                continue
            fv = max(0.0, 10 * math.sin((loc.hour - 6) / 12 * math.pi))
            gw = {"Thermal": it / 1000 * 0.5, "Hydro": 3.0, "Wind": 2.0, "Geothermal": 0.6, "Photovoltaic": fv, "Self-consumption": 2.0}
            att += [[data, round(v, 3), k] for k, v in gw.items()]
            rin += [[data, round(v, 3), k] for k, v in {"Biomass": 1.5, "Hydro": 3.0, "Wind": 2.0, "Geothermal": 0.6, "Photovoltaic": fv * 1.3}.items()]
        # ora doppia: le righe di «South» con l'ordine scambiato (Terna non dice quale valore è dell'ora legale)
        prima, dopo = doppie[:4], doppie[4:]
        for p, d in zip(prima, dopo):
            ps = next(r for r in p if r[3] == "South"); ds = next(r for r in d if r[3] == "South")
            ps[1], ds[1] = ds[1], ps[1]
        for r in prima + dopo:
            carico += r
        _scrivi(arch / f"TotalLoad_{a}-{m:02d}.json", ["Date", "Total Load [MW]", "Forecast Total Load [MW]", "Bidding Zone"], carico)
        _scrivi(arch / f"ActualGeneration_{a}-{m:02d}.json", ["Date", "Actual Generation", "Primary Source"], att)
        if m == 9:
            _scrivi(arch / f"RenewableGeneration_{a}-{m:02d}.json", ["Date", "Renewable Generation", "Energy Source"], rin)
    return arch


@pytest.fixture()
def uscita(tmp_path):
    out = tmp_path / "out"
    esito = K.costruisci_carichi(_archivio(tmp_path), out)
    assert esito["mesi"] == ["2026-09", "2026-10"]
    return out


def test_indice(uscita):
    ix = json.loads((uscita / "indice.json").read_text(encoding="utf-8"))
    assert [z["id"] for z in ix["zone"]] == ["ITA", "NORD", "CNOR", "CSUD", "SUD", "CALA", "SICI", "SARD"]
    assert [v["id"] for v in ix["voci"]] == ["termo", "bio", "idro", "geo", "eol", "fv", "saldo"]
    assert {v["id"]: v["colore"] for v in ix["voci"]}["fv"] == "#f7cb15"          # colori della pagina «Produzione e consumi»
    set_, ott = ix["mesi"]
    assert set_["inizio"] == "2026-08-31T22:00:00Z" and set_["n"] == 30 * 96 and set_["ora_legale"] == [[0, 120]]
    assert ott["n"] == 31 * 96 + 4 and ott["ora_legale"] == [[0, 120], [24 * 96 + 12, 60]]   # 25 ottobre, 01:00 UTC
    assert set_["passo_fonti"] == 15 and ott["passo_fonti"] == 60 and set_["rinnovabili"] and not ott["rinnovabili"]
    assert "Terna" in ix["fonte"] and "GME" not in json.dumps(ix)


def test_carico_e_ora_doppia(uscita):
    c = json.loads((uscita / "carico_2026-10.json").read_text(encoding="utf-8"))["zone"]
    assert set(c) == {"ITA", "NORD", "CNOR", "CSUD", "SUD", "CALA", "SICI", "SARD"}
    n = len(c["ITA"])
    assert all(isinstance(v, int) for s in c.values() for v in s)
    # la somma delle zone torna con l'Italia anche nell'ora doppia (South rimesso nell'ordine giusto)
    assert max(abs(c["ITA"][i] - sum(c[z][i] for z in c if z != "ITA")) for i in range(n)) <= 4


def test_italia_somma_delle_zone(uscita, tmp_path):
    """(22/11/2026, Paolo) Italia = somma delle zone quarto d'ora per quarto d'ora, esatta anche dopo l'arrotondamento;
    lo scarto tra «Italy» di Terna e la somma va nell'indice. Dove manca una zona resta «Italy» di Terna."""
    ix = json.loads((uscita / "indice.json").read_text(encoding="utf-8"))
    assert all(m["scarto_italia_mw"] < 0.01 for m in ix["mesi"])
    for am in ("2026-09", "2026-10"):
        c = json.loads((uscita / f"carico_{am}.json").read_text(encoding="utf-8"))["zone"]
        assert list(c)[0] == "ITA"
        assert all(c["ITA"][i] == sum(c[z][i] for z in c if z != "ITA") for i in range(len(c["ITA"])))
    # Italia di Terna diversa dalla somma (+500 MW) e una zona mancante in un quarto d'ora
    arch = tmp_path / "b"; arch.mkdir()
    righe = []
    for h in range(2):
        d = f"2026-09-01T0{h}:00:00"
        righe.append([d, 1500.0 + 500, "Italy"])
        righe += [[d, v, z] for z, v in {"North": 1000.4, "Centre-North": 499.6}.items() if not (h == 1 and z == "North")]
        righe += [[d, 0.0, z] for z in ("Centre-South", "South", "Calabria", "Sicily", "Sardinia")]
    _scrivi(arch / "TotalLoad_2026-09.json", ["Date", "Total Load [MW]", "Bidding Zone"], righe)
    K.costruisci_carichi(arch, tmp_path / "o")
    c = json.loads((tmp_path / "o" / "carico_2026-09.json").read_text(encoding="utf-8"))["zone"]
    assert c["ITA"][0] == 1500 and c["ITA"][4] == 2000                  # somma delle zone; senza North: Italy di Terna
    assert json.loads((tmp_path / "o" / "indice.json").read_text(encoding="utf-8"))["mesi"][0]["scarto_italia_mw"] == 500


def test_fonti(uscita):
    f9 = json.loads((uscita / "fonti_2026-09.json").read_text(encoding="utf-8"))["voci"]
    c9 = json.loads((uscita / "carico_2026-09.json").read_text(encoding="utf-8"))["zone"]["ITA"]
    i = 12 * 4                                   # 1 settembre, 12:00 (il mese parte dalla mezzanotte italiana)
    assert f9["fv"][i] == round(10 * math.sin(6 / 12 * math.pi) * 1.3 * 1000) and f9["bio"][i] == 1500
    # termoelettrico = produzione totale (con gli autoconsumi) − rinnovabili; saldo = richiesta − produzione
    assert abs(sum(f9[k][i] for k in ("termo", "bio", "idro", "geo", "eol", "fv")) - (c9[i] / 2 + 3000 + 2000 + 600 + 10000 + 2000)) < 80   # (il carico ha in più le piccole variazioni per zona)
    assert abs(f9["saldo"][i] - (c9[i] - sum(f9[k][i] for k in f9 if k != "saldo"))) <= 6
    # ottobre: generazione oraria → quattro quarti d'ora uguali; senza produzione rinnovabile niente bioenergie
    f10 = json.loads((uscita / "fonti_2026-10.json").read_text(encoding="utf-8"))["voci"]
    assert f10["termo"][40:44] == [f10["termo"][40]] * 4 and set(f10["bio"]) == {0}


def test_fonti_quarto_senza_dati():
    assert K.fonti_quarto({}, {}, 1000) is None
    p = K.fonti_quarto({"termo": 10, "idro": 1, "eol": 1, "geo": 1, "fv": 1, "auto": 2}, {}, 20)
    assert p["termo"] == 12 and p["saldo"] == 4


def test_zona_sconosciuta(tmp_path):
    arch = tmp_path / "a"; arch.mkdir()
    _scrivi(arch / "TotalLoad_2026-09.json", ["Date", "Total Load [MW]", "Bidding Zone"], [["2026-09-01T00:00:00", 1.0, "Atlantide"]])
    with pytest.raises(ValueError, match="Atlantide"):
        K.costruisci_carichi(arch, tmp_path / "o")


def test_mesi_tra():
    assert K.mesi_tra("2025-11", "2026-02") == [(2025, 11), (2025, 12), (2026, 1), (2026, 2)]


def test_archivio_parquet_del_worker(tmp_path):
    """(20/11/2026, unione con il worker) l'archivio Parquet del server (TERNA_DATI/serie, servizio/terna.py della fase 4:
    istante in UTC, zona/fonte, carico_mw/energia_gwh) dà gli stessi file dell'archivio JSON del Download Center."""
    pd = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    arch = _archivio(tmp_path)
    serie = tmp_path / "serie"
    for ds, (nome, chiave, valore) in K.PARQUET.items():
        (serie / nome).mkdir(parents=True)
        for f in sorted(arch.glob(f"{ds}_*.json")):
            am = f.stem.split("_")[1]
            col_v, col_k = {"TotalLoad": ("Total Load [MW]", "Bidding Zone"), "ActualGeneration": ("Actual Generation", "Primary Source"),
                            "RenewableGeneration": ("Renewable Generation", "Energy Source")}[ds]
            righe = list(K._leggi(f, col_v, col_k))
            df = pd.DataFrame({"istante": pd.to_datetime([t for t, _, _ in righe], utc=True), chiave: [k for _, k, _ in righe],
                               valore: [v for _, _, v in righe], "origine": "dc"})
            df.to_parquet(serie / nome / f"{am}.parquet", index=False)
    (serie / "picco_valle").mkdir()                    # le altre serie dell'archivio non disturbano
    a, b = tmp_path / "da_json", tmp_path / "da_parquet"
    assert K.costruisci_carichi(arch, a)["mesi"] == K.costruisci_carichi(serie, b)["mesi"] == ["2026-09", "2026-10"]
    nomi = sorted(f.name for f in a.glob("*.json"))
    assert nomi == sorted(f.name for f in b.glob("*.json")) and "fonti_2026-10.json" in nomi
    for nome in nomi:
        x, y = (json.loads((d / nome).read_text(encoding="utf-8")) for d in (a, b))
        if nome == "indice.json":
            x.pop("aggiornato"); y.pop("aggiornato")
        assert x == y, nome


def test_archivio_vuoto(tmp_path):
    (tmp_path / "serie" / "carico_totale").mkdir(parents=True)
    with pytest.raises(FileNotFoundError):
        K.costruisci_carichi(tmp_path / "serie", tmp_path / "out")
