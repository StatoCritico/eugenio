"""Archivio psicrometrico (14/11/2026): fase 3 (meteo_storico/psicro.py: formato, unione delle fonti, scarico riprendibile
con S3 finto, aggiornamento notturno) e rotte /api/psicro/… (servizio/psicro.py) su una cartella sintetica.

  cd fase4-server && PYTHONPATH=../fase3-storico python -m pytest tests/test_psicro.py -q
Niente rete: le letture da S3 sono sostituite da funzioni finte."""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RADICE = Path(__file__).resolve().parents[2]
for p in (RADICE / "fase4-server", RADICE / "fase3-storico"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

pytest.importorskip("pyarrow")
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from meteo_storico import psicro as A, s3  # noqa: E402
from servizio import config as C, meteo, protezione as P, psicro as R, worker as W  # noqa: E402

H = lambda s: int(A.ora_da_tempi([s])[0])     # noqa: E731


def serie(dal: str, al: str, fonte: int, t0: float = 10.0, buchi=()) -> A.Serie:
    ore = np.arange(H(dal), H(al) + 1)
    t = (t0 + 5 * np.sin(ore / 24 * 2 * np.pi)) * 10
    ur = np.full(len(ore), 70.0)
    m = ~np.isin(ore, [H(b) for b in buchi])
    return A.Serie(ore[m], np.round(t[m]), ur[m], fonte)


# ------------------------------------------------------------------------------------------- fase 3
def test_conversioni_e_umidita():
    t, ur = A.da_t_td(np.array([20.0, 20.0, np.nan, 5.0]), np.array([20.0, 10.0, 1.0, np.nan]))
    assert t[0] == 200 and ur[0] == 100 and 50 <= ur[1] <= 54          # Td 10 a 20 °C ≈ 52 %
    assert np.isnan(t[2]) and np.isnan(ur[2]) and t[3] == 50 and np.isnan(ur[3])
    assert A.ora_da_tempi(["1970-01-01T01:00Z"])[0] == 1 and A.iso(H("1940-01-01T00:00Z")) == "1940-01-01T00:00Z"
    assert H("1940-01-01T00:00Z") < 0       # prima del 1970: ore negative, int32 basta (−262.968)


def test_unisci_preferisce_corretta_poi_icon_poi_grezzo():
    grezzo = serie("2014-12-31T00:00Z", "2015-01-02T23:00Z", A.FONTE_ERA5, t0=0)
    corretta = serie("2015-01-01T00:00Z", "2015-01-01T23:00Z", A.FONTE_CORRETTA, t0=30)
    icon = serie("2015-01-01T12:00Z", "2015-01-02T05:00Z", A.FONTE_ICON, t0=20)
    s = A.unisci(icon, grezzo, corretta)
    assert len(s) == 72 and (np.diff(s.ora) == 1).all()
    f = dict(zip(s.ora.tolist(), s.fonte.tolist()))
    assert f[H("2014-12-31T23:00Z")] == 1 and f[H("2015-01-01T13:00Z")] == 2
    assert f[H("2015-01-02T03:00Z")] == 3 and f[H("2015-01-02T06:00Z")] == 1


def test_scrivi_e_leggi_con_buchi(tmp_path):
    s = serie("1949-12-31T00:00Z", "1950-01-01T23:00Z", A.FONTE_ERA5, buchi=["1950-01-01T03:00Z"])
    s.ur[5] = np.nan
    p = tmp_path / "037006.parquet"
    A.scrivi(p, s, "037006", 71.4)
    import pyarrow.parquet as pq
    sch = pq.read_schema(p)
    assert [str(sch.field(c).type) for c in ("ora", "t", "ur", "fonte")] == ["int32", "int16", "uint8", "uint8"]
    i = A.info(p)
    assert i["quota_m"] == 71 and i["prima"] == H("1949-12-31T00:00Z") and i["ultima"] == H("1950-01-01T23:00Z")
    assert i["righe"] == 47 and i["formato"] == A.FORMATO
    r = A.leggi(p)
    assert len(r) == 47 and np.isnan(r.ur[5]) and np.allclose(r.t, s.t)
    assert len(A.leggi(p, H("1950-01-01T20:00Z"))) == 4
    assert A.completo(p, H("1949-12-31T00:00Z"), H("1950-01-01T23:00Z") + 1)
    assert not A.completo(p, H("1949-12-31T00:00Z"), H("1950-01-02T23:00Z") + 1)


def celle_finte(comuni: pd.DataFrame) -> pd.DataFrame:
    c = comuni[["istat", "lat", "lon"]].copy().reset_index(drop=True)
    c["quota"] = [50.0 + 100 * k for k in range(len(c))]
    for d in ("era5_land", "era5"):
        c[f"{d}_i"], c[f"{d}_j"], c[f"{d}_h"] = 1, np.arange(len(c)), c.quota + 65    # cella 65 m più in alto: comune +0,42 °C
    for d in ("icon_d2", "icon_eu"):
        c[f"{d}_i"], c[f"{d}_j"], c[f"{d}_h"] = -1, -1, np.nan
    return c


class FS:
    letti = 0


@pytest.fixture
def s3_finto(monkeypatch):
    """S3 senza rete: celle fisse, fine dei dati il 3/1/1950 alle 23, ERA5-Land dal 1950 (valori diversi da ERA5)."""
    chiamate = []

    def leggi_dom(fs, c, dom, variabili, h0, h1):
        chiamate.append((dom, len(c), h0, h1))
        ore = np.arange(h0, h1)[None, :].repeat(len(c), 0)
        base = 12.0 if dom == "era5_land" else 2.0
        out = {"temperature_2m": (base + 0 * ore).astype(np.float32), "dew_point_2m": (base - 4 + 0 * ore).astype(np.float32)}
        if dom == "era5_land":             # Rimini ha la cella di mare: niente ERA5-Land
            mare = (c.istat == "099014").to_numpy()
            for v in out.values():
                v[mare] = np.nan
        return out
    monkeypatch.setattr(s3, "FSBlocchi", FS)
    monkeypatch.setattr(s3, "celle", lambda fs, comuni, archivio: celle_finte(comuni))
    monkeypatch.setattr(s3, "fine_dati", lambda fs, dom: H("1950-01-03T23:00Z"))
    monkeypatch.setattr(s3, "_leggi_dom", leggi_dom)
    return chiamate


COMUNI = pd.DataFrame({"istat": ["037006", "039014", "099014"], "nome": ["Bologna", "Ravenna", "Rimini"],
                       "regione_cod": "08", "lat": [44.49, 44.41, 44.06], "lon": [11.34, 12.2, 12.57]})


def test_scarica_riprendibile_e_unione(tmp_path, s3_finto):
    arch = tmp_path / "archivio"
    (arch / "orario" / "era5_corretto").mkdir(parents=True)
    t = pd.date_range("1950-01-02", periods=24, freq="h", tz="UTC")
    pd.DataFrame({"time": t, "temperature_2m": np.float32(30.04), "relative_humidity_2m": np.float32(55)}).to_parquet(
        arch / "orario" / "era5_corretto" / "037006.parquet")
    ris = A.scarica(arch, COMUNI, dal=dt.date(1949, 12, 31), per_gruppo=2)
    assert ris["scritti"] == 3 and ris["al"] == "1950-01-03T23:00Z"
    cart = arch / "psicro"
    assert not (cart / ".lavoro").exists() and not (cart / A.BLOCCO).exists()
    c = pd.read_parquet(cart / "celle.parquet")
    assert sorted(c.istat) == sorted(COMUNI.istat) and "quota" in c
    bo = A.leggi(cart / "037006.parquet")
    assert len(bo) == 96 and bo.ora[0] == H("1949-12-31T00:00Z")
    f = dict(zip(bo.ora.tolist(), zip(bo.fonte.tolist(), bo.t.tolist())))
    assert f[H("1949-12-31T05:00Z")] == (1, 24.0)               # ERA5 (2 °C) + 0,42 °C di quota
    assert f[H("1950-01-01T05:00Z")] == (1, 124.0)              # ERA5-Land (12 °C) + 0,42
    assert f[H("1950-01-02T05:00Z")] == (2, 300.0)              # serie corretta
    ri = A.leggi(cart / "099014.parquet")                       # cella di mare: ERA5 anche dal 1950
    assert set(ri.t.tolist()) == {24.0}
    assert A.info(cart / "039014.parquet")["quota_m"] == 150
    # di nuovo: tutto completo, nessuna lettura
    n = len(s3_finto)
    assert A.scarica(arch, COMUNI, dal=dt.date(1949, 12, 31), per_gruppo=2)["scritti"] == 0
    assert len(s3_finto) == n


def test_scarica_riprende_dagli_anni_fatti(tmp_path, s3_finto, monkeypatch):
    arch = tmp_path / "archivio"
    vero = A._unisci_gruppo

    def si_ferma(*a, **k):
        raise KeyboardInterrupt
    monkeypatch.setattr(A, "_unisci_gruppo", si_ferma)
    with pytest.raises(KeyboardInterrupt):
        A.scarica(arch, COMUNI, dal=dt.date(1949, 12, 31), per_gruppo=3)
    pezzi = list((arch / "psicro" / ".lavoro").glob("*/*.parquet"))
    assert sorted(p.stem for p in pezzi) == ["1949", "1950"]
    assert not (arch / "psicro" / A.BLOCCO).exists()           # il blocco si toglie anche dopo un errore
    monkeypatch.setattr(A, "_unisci_gruppo", vero)
    n = len(s3_finto)
    A.scarica(arch, COMUNI, dal=dt.date(1949, 12, 31), per_gruppo=3)
    assert len(s3_finto) == n                                   # anni già scritti: niente S3
    assert len(A.leggi(arch / "psicro" / "099014.parquet")) == 96


def test_aggiorna_notte_icon_poi_s3(tmp_path, s3_finto, monkeypatch):
    cart = tmp_path / "psicro"
    for k, istat in enumerate(COMUNI.istat):
        A.scrivi(cart / f"{istat}.parquet", serie("1950-01-01T00:00Z", "1950-01-02T11:00Z", 1), istat, 50.0 + k)
    celle_finte(COMUNI).to_parquet(cart / "celle.parquet")
    orario = tmp_path / "orario"
    orario.mkdir()
    t = pd.date_range("1950-01-02T00:00Z", "1950-01-05T23:00Z", freq="h")
    pd.DataFrame({"time": t, "temperature_2m": 7.0, "relative_humidity_2m": 60.0}).to_parquet(orario / "037006.parquet")
    e = A.aggiorna(cart, orario, usa_s3=True, giorni_max=10)
    assert e["icon"] == 1 and e["s3"] == 2 and e["aggiornati"] == 3
    bo = A.leggi(cart / "037006.parquet")
    assert bo.ora[-1] == H("1950-01-05T23:00Z") and bo.fonte[-1] == 3
    assert (bo.fonte[bo.ora <= H("1950-01-02T11:00Z")] == 1).all()          # le ore vecchie non cambiano
    ra = A.leggi(cart / "039014.parquet")
    assert ra.ora[-1] == H("1950-01-03T23:00Z") and ra.fonte[-1] == 1 and len(ra) == 72
    assert A.info(cart / "039014.parquet")["quota_m"] == 51
    # con scarica-psicro al lavoro non si tocca nulla
    (cart / A.BLOCCO).write_text("{}")
    assert A.aggiorna(cart, orario)["saltato"] == "scarica-psicro in corso"
    assert A.aggiorna(tmp_path / "manca", orario)["saltato"] == "cartella assente"


def test_stima_spazio():
    s = A.stima(7896, dt.date(1940, 1, 1), dt.date(2026, 11, 14))
    assert 760_000 < s["ore_per_comune"] < 763_000 and 7 < s["gb_totali"] < 12


# ------------------------------------------------------------------------------------------- worker
def test_worker_senza_cartella_non_fa_nulla(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "CARTELLA_PSICRO", tmp_path / "psicro")
    assert W.psicro() == {"saltato": "cartella assente"}


def test_worker_aggiorna_con_icon(tmp_path, monkeypatch):
    cart, dati = tmp_path / "psicro", tmp_path / "dati"
    A.scrivi(cart / "037006.parquet", serie("2026-11-01T00:00Z", "2026-11-10T23:00Z", 2), "037006", 54.0)
    (dati / "orario").mkdir(parents=True)
    t = pd.date_range("2026-11-09T00:00Z", "2026-11-12T23:00Z", freq="h")
    pd.DataFrame({"time": t, "temperature_2m": 9.0, "relative_humidity_2m": 88.0}).to_parquet(dati / "orario" / "037006.parquet")
    monkeypatch.setattr(C, "CARTELLA_PSICRO", cart)
    monkeypatch.setattr(C, "DATI", dati)
    monkeypatch.setattr(C, "PSICRO_S3", False)
    e = W.psicro()
    assert e["icon"] == 1 and A.info(cart / "037006.parquet")["ultima"] == H("2026-11-12T23:00Z")


# ------------------------------------------------------------------------------------------- API
@pytest.fixture
def api(tmp_path, monkeypatch):
    dati = tmp_path / "dati"
    cart = dati / "psicro"
    (dati / "orario").mkdir(parents=True)
    pd.DataFrame({"istat": ["037006", "039014", "099014", "040012"], "nome": ["Bologna", "Ravenna", "Rimini", "Forlì"],
                  "regione_cod": "08"}).to_parquet(dati / "comuni.parquet")
    # Bologna: 1940 → 10/11/2026 con un buco di 3 ore nel 2026; fonti 1 fino al 2014, 2 dopo
    grezzo = serie("1940-01-01T00:00Z", "2014-12-31T23:00Z", 1)
    corretta = serie("2015-01-01T00:00Z", "2026-11-10T23:00Z", 2,
                     buchi=["2026-03-01T00:00Z", "2026-03-01T01:00Z", "2026-03-01T02:00Z"])
    corretta.ur[-1] = np.nan
    A.scrivi(cart / "037006.parquet", A.unisci(grezzo, corretta), "037006", 54.0)
    # Ravenna: solo la serie oraria ICON del server (archivio dal 1940 non ancora copiato)
    t = pd.date_range("2022-11-14T00:00Z", "2026-11-10T23:00Z", freq="h")
    pd.DataFrame({"time": t, "temperature_2m": 12.34, "relative_humidity_2m": 77.4}).to_parquet(dati / "orario" / "039014.parquet")
    pd.DataFrame({"istat": ["040012"], "quota": [34.0]}).to_parquet(cart / "celle.parquet")
    monkeypatch.setattr(C, "DATI", dati)
    monkeypatch.setattr(C, "CARTELLA_PSICRO", cart)
    monkeypatch.setattr(C, "REGIONI", ["08"])
    monkeypatch.setattr(C, "SOLO_COMUNI", [])
    R._serie.cache_clear()
    R._risposta.cache_clear()
    R._celle.cache_clear()
    P.limiti.clear()
    app = FastAPI()
    app.include_router(R.router)
    return TestClient(app), cart


def test_disponibilita(api):
    cl, _ = api
    d = cl.get("/api/psicro/disponibilita/037006").json()
    assert d["comune"] == "Bologna" and d["quota_m"] == 54 and d["pressione_pa"] == R.pressione(54) == 100678
    assert d["dal"] == "1940-01-01T00:00Z" and d["al"] == "2026-11-10T23:00Z" and d["anni_completi"] == 86
    assert d["archivio"] == "psicro" and "ERA5" in d["fonte"] and "CC BY 4.0" in d["licenza"]
    assert d["anni_scelte"] == [1, 2, 5, 10, 20, 0]
    r = cl.get("/api/psicro/disponibilita/039014").json()
    assert r["archivio"] == "orario_icon" and r["anni_completi"] == 3 and r["anni_scelte"] == [1, 2, 0]
    assert r["dal"] == "2022-11-14T00:00Z" and "ICON" in r["fonte"] and "non è ancora sul server" in r["note"][0]
    assert r["quota_m"] is None and r["pressione_pa"] == 101325 and "livello del mare" in r["note"][-1]


def test_serie_finestre_e_buchi(api):
    cl, _ = api
    d = cl.get("/api/psicro/serie/037006?anni=1").json()
    assert d["inizio"] == "2025-11-11T00:00Z" == d["dal"] and d["al"] == "2026-11-10T23:00Z" and d["passo_h"] == 1
    assert d["n"] == len(d["t"]) == len(d["ur"]) == 8760 and d["anni_richiesti"] == 1 and d["anni_dati"] == 1.0
    i = H("2026-03-01T00:00Z") - H("2025-11-11T00:00Z")
    assert d["t"][i:i + 3] == [None, None, None] and d["t"][i + 3] is not None and d["ur"][-1] is None
    assert all(isinstance(x, int) for x in d["t"][:100]) and "3 ore senza dati (null)." in d["note"]
    assert d["fonte"] == A.NOMI_FONTE[2] and d["pressione_pa"] == 100678
    for anni, inizio in ((2, "2024-11-11"), (5, "2021-11-11"), (10, "2016-11-11"), (20, "2006-11-11"), (0, "1940-01-01")):
        x = cl.get(f"/api/psicro/serie/037006?anni={anni}").json()
        assert x["inizio"].startswith(inizio) and x["n"] == H(x["al"]) - H(x["inizio"]) + 1, anni
    tutta = cl.get("/api/psicro/serie/037006?anni=0").json()
    assert tutta["n"] == H("2026-11-10T23:00Z") - H("1940-01-01T00:00Z") + 1 and tutta["anni_dati"] == 86.9
    assert any("Prima del 1950" in n for n in tutta["note"]) and any("ore dal 01/01/1940" in n for n in tutta["note"])
    venti = cl.get("/api/psicro/serie/037006?anni=20").json()
    assert ";" in venti["fonte"] and not any("Prima del 1950" in n for n in venti["note"])


def test_serie_ripiego_icon(api):
    cl, _ = api
    d = cl.get("/api/psicro/serie/039014?anni=10").json()
    assert d["inizio"] == "2022-11-14T00:00Z" and d["anni_richiesti"] == 10 and d["anni_dati"] == 4.0
    assert d["t"][0] == 123 and d["ur"][0] == 77
    assert any("non è ancora sul server" in n for n in d["note"]) and any("Chiesti 10 anni" in n for n in d["note"])
    assert cl.get("/api/psicro/serie/039014?anni=1").json()["n"] == 8760


def test_quota_dalle_celle_e_503(api):
    cl, cart = api
    r = cl.get("/api/psicro/serie/040012?anni=1")
    assert r.status_code == 503 and "non è ancora sul server" in r.json()["detail"]
    assert cl.get("/api/psicro/disponibilita/099014").status_code == 503
    assert R.quota("040012") == (34.0, None)
    import shutil
    shutil.rmtree(cart)                      # archivio assente del tutto: Bologna senza file, nessun ripiego
    R._serie.cache_clear()
    assert cl.get("/api/psicro/serie/037006?anni=1").status_code == 503


def test_errori_e_limiti(api, monkeypatch):
    cl, _ = api
    assert cl.get("/api/psicro/serie/037006?anni=3").status_code == 422
    assert cl.get("/api/psicro/serie/037006?anni=-1").status_code == 422
    assert cl.get("/api/psicro/serie/000000?anni=1").status_code == 404
    assert cl.get("/api/psicro/disponibilita/000000").status_code == 404
    P.limiti.clear()
    monkeypatch.setattr(C, "PSICRO_ORA", 2)
    assert cl.get("/api/psicro/serie/037006?anni=1").status_code == 200
    assert cl.get("/api/psicro/serie/037006?anni=2").status_code == 200
    r = cl.get("/api/psicro/serie/037006?anni=1")
    assert r.status_code == 429 and r.headers["X-EuGEnio-Limite"] == "psicro" and "temperatura e umidità" in r.json()["detail"]
    assert cl.get("/api/psicro/disponibilita/037006").status_code == 200       # la disponibilità conta solo nei «dati»


def test_copia_in_memoria_si_rinnova_col_file(api):
    cl, cart = api
    a = cl.get("/api/psicro/serie/037006?anni=1").json()
    s = A.leggi(cart / "037006.parquet")
    A.scrivi(cart / "037006.parquet", A.unisci(s, serie("2026-11-11T00:00Z", "2026-11-11T23:00Z", 3)), "037006", 54.0)
    import os
    os.utime(cart / "037006.parquet", (1e9 + 5e8, 2e9))
    b = cl.get("/api/psicro/serie/037006?anni=1").json()
    assert b["al"] == "2026-11-11T23:00Z" != a["al"] and "ICON" in b["fonte"]


def test_rotte_nell_app():
    pytest.importorskip("fastapi")
    from servizio.app import app
    percorsi = set(app.openapi()["paths"])
    assert {"/api/psicro/disponibilita/{istat}", "/api/psicro/serie/{istat}"} <= percorsi
