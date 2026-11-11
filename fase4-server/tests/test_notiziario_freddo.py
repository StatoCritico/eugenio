"""Sezione dei gradi giorno della newsletter mensile (11/11/2026): frase di sintesi, scarto in °C, periodo dichiarato,
scarto dalla normale 1991–2020 dal clima dal 1940, Cesena tra i capoluoghi, nessuna lettura del giornaliero senza
capoluoghi, benvenuto e niente Eurostat."""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from servizio import config as C, notiziario as N   # noqa: E402


def _giornaliero(cartella: Path, t_per_anno: dict[str, dict[int, float]]) -> None:
    righe = []
    for istat, anni in t_per_anno.items():
        for anno, t in anni.items():
            for d in pd.date_range(f"{anno}-10-01", f"{anno}-10-31"):
                righe.append({"istat": istat, "data": d, "gg20": max(0.0, 20 - t), "t_media": t})
    pd.DataFrame(righe).to_parquet(cartella / "giornaliero.parquet", index=False)


def _capoluoghi(monkeypatch, nomi: dict[str, str]):
    df = pd.DataFrame({"istat": list(nomi), "nome": list(nomi.values()), "capoluogo": True})
    monkeypatch.setattr(N, "_capoluoghi", lambda: df.sort_values("nome"))


def test_frase_scarto_e_periodo(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "DATI", tmp_path)
    monkeypatch.setattr(C, "SITO_DATI", tmp_path / "sito")      # niente clima dal 1940: tabella senza la normale
    _capoluoghi(monkeypatch, {"037006": "Bologna", "099014": "Rimini"})
    # Bologna: 14 °C negli anni prima, 16 °C nel 2026 → +2,0 °C, GG 186 → 124 (−33 %)
    # Rimini: 15 °C prima, 15,6 °C nel 2026 → +0,6 °C, GG 155 → 136 (−12 %); medie +1,3 °C e −23 %
    _giornaliero(tmp_path, {"037006": {2015: 14, 2020: 14, 2025: 14, 2026: 16},
                            "099014": {2015: 15, 2020: 15, 2025: 15, 2026: 15.6}})
    r = N._tabella_freddo(2026, 10)
    testo = "\n".join(r)
    assert r[0] == ("Ottobre 2026 è stato più caldo della media 2015–2025 in 2 capoluoghi su 2: in media +1,3 °C "
                    "con il 23 % di gradi giorno in meno.")
    assert "| Capoluogo | Temperatura media | Scarto dal 2015–2025 | GG del mese | Media GG 2015–2025 | Scarto GG |" in r
    assert "| Bologna | 16,0 °C | +2,0 °C | 124 | 186 | −33 % |" in r
    assert "1991" not in testo
    assert "| Rimini | 15,6 °C | +0,6 °C | 136 | 155 | −12 % |" in r
    assert "Meno gradi giorno vuol dire un mese più caldo." in testo and N.FONTE_METEO in r
    # (11/11/2026) subito sotto la tabella il collegamento per cercare gli altri comuni
    i = r.index("| Rimini | 15,6 °C | +0,6 °C | 136 | 155 | −12 % |")
    assert r[i + 2].startswith("**Il tuo comune non c'è?**") and r[i + 2].endswith("/dati.html")


def test_caldo_e_freddo_insieme_e_mese_incompleto(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "DATI", tmp_path)
    monkeypatch.setattr(C, "SITO_DATI", tmp_path / "sito")
    _capoluoghi(monkeypatch, {"037006": "Bologna", "034027": "Parma", "033032": "Piacenza"})
    _giornaliero(tmp_path, {"037006": {2024: 14, 2025: 14, 2026: 15}, "034027": {2024: 14, 2025: 14, 2026: 13}})
    # Piacenza solo con pochi giorni del 2026: esclusa
    extra = pd.DataFrame({"istat": "033032", "data": pd.date_range("2026-10-01", "2026-10-10"), "gg20": 6.0,
                          "t_media": 14.0})
    g = pd.concat([pd.read_parquet(tmp_path / "giornaliero.parquet"), extra])
    g.to_parquet(tmp_path / "giornaliero.parquet", index=False)
    r = N._tabella_freddo(2026, 10)
    assert r[0].startswith("Ottobre 2026 è stato più caldo della media 2024–2025 in 1 capoluoghi su 2 e più freddo in 1:")
    assert not any("Piacenza" in x for x in r)
    assert "| Parma | 13,0 °C | −1,0 °C |" in "\n".join(r)


def test_senza_capoluoghi_non_legge_il_giornaliero(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "DATI", tmp_path)          # nessun giornaliero.parquet: una lettura darebbe errore
    monkeypatch.setattr(N, "_capoluoghi", lambda: pd.DataFrame(columns=["istat", "nome"]))
    assert N._tabella_freddo(2026, 10) == []


def test_segno():
    assert N._segno(1.26, 1) == "+1,3" and N._segno(-0.04, 1) == "0,0" and N._segno(-12.4) == "−12"


def _clima(cartella: Path, istat: str, normale_ott: float, ott_per_anno: dict[int, float]) -> None:
    """File finti del clima dal 1940 (formato della fase 9): normale 1991–2020 e mensili anno per anno (×10)."""
    d = cartella / "clima" / "08"
    d.mkdir(parents=True, exist_ok=True)
    t = [None] * 12
    t[9] = normale_ott
    (d / f"{istat}.json").write_text(json.dumps({"periodi": {"1991-2020": {"mensili": {"t_media": t}}}}))
    da, a = min(ott_per_anno), max(ott_per_anno)
    serie = [None] * ((a - da + 1) * 12)
    for anno, v in ott_per_anno.items():
        serie[(anno - da) * 12 + 9] = round(v * 10)
    (d / f"{istat}_mensili.json").write_text(json.dumps({"da": da, "a": a, "scala": {"t_media": 10}, "t_media": serie}))
    (cartella / "clima" / "regioni.json").write_text(json.dumps({istat: "08"}))


def test_scarto_dalla_normale(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "DATI", tmp_path)
    monkeypatch.setattr(C, "SITO_DATI", tmp_path / "sito")
    _capoluoghi(monkeypatch, {"037006": "Bologna"})
    _giornaliero(tmp_path, {"037006": {2024: 14, 2025: 14, 2026: 16}})
    # clima dal 1940: normale di ottobre 13,0 °C, ottobre 2024–2025 a 13,8 °C → già +0,8; più +2,0 dall'archivio = +2,8
    _clima(tmp_path / "sito", "037006", 13.0, {2023: 13.0, 2024: 13.6, 2025: 14.0})
    r = N._tabella_freddo(2026, 10)
    assert r[0].endswith("Rispetto al clima del 1991–2020 lo scarto medio è di +2,8 °C.")
    assert "| Capoluogo | Temperatura media | Scarto dal 2024–2025 | Scarto dal 1991–2020 | GG del mese | " \
           "Media GG 2024–2025 | Scarto GG |" in r
    assert "| Bologna | 16,0 °C | +2,0 °C | +2,8 °C | 124 | 186 | −33 % |" in r
    # un anno mancante nel clima dal 1940: niente normale per quel comune
    _clima(tmp_path / "sito", "037006", 13.0, {2025: 14.0})
    assert "1991" not in "\n".join(N._tabella_freddo(2026, 10))


def test_cesena_tra_i_capoluoghi(monkeypatch):
    cm = pd.DataFrame({"istat": ["040012", "040007", "040005"], "nome": ["Forlì", "Cesena", "Cesenatico"],
                       "capoluogo": [True, False, False]})
    monkeypatch.setattr(N.meteo, "comuni", lambda: cm)
    assert list(N._capoluoghi().nome) == ["Cesena", "Forlì"]


def test_primo_numero_con_benvenuto_e_senza_eurostat(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "DATI", tmp_path)
    monkeypatch.setattr(C, "SITO_DATI", tmp_path / "sito")
    monkeypatch.setattr(C, "NOTIZIARIO_PRIMO_NUMERO", "2026-11")
    _capoluoghi(monkeypatch, {"037006": "Bologna"})
    _giornaliero(tmp_path, {"037006": {2025: 14, 2026: 16}})
    (tmp_path / "mercati" / "eurostat").mkdir(parents=True)   # anche con il file Eurostat presente: sezione tolta
    pd.DataFrame({"tax": ["X_VAT"], "nrg_cons": ["MWH20-499"], "time": ["2025-S2"], "valore": [0.2]}).to_parquet(
        tmp_path / "mercati" / "eurostat" / "elettricita_pmi.parquet")
    oggetto, testo = N.testo_mensile(2026, 10, dt.date(2026, 11, 12))
    assert oggetto == "EuGEnio – prezzi e freddo di ottobre 2026"
    assert testo.startswith("# EuGEnio, ottobre 2026") and "## Il freddo di ottobre 2026, comune per comune" in testo
    assert "**Benvenuto!**" in testo and "Eurostat" not in testo and "PMI" not in testo
    assert "Meet EuGEnio" in testo and "19 comuni" in testo                     # tutte le novità fino all'invio
    _, dopo = N.testo_mensile(2026, 11, dt.date(2026, 12, 12))
    assert "Benvenuto" not in dopo and "Meet EuGEnio" not in dopo


def _indici(cartella: Path) -> None:
    """File del sito con gli indici dei prezzi (forma di mercati_energia/prezzi_pubblici.py)."""
    def serie(ott25, ott26):
        a, b = [None] * 12, [None] * 12
        a[9], b[9] = ott25, ott26
        return {"2025": a, "2026": b}
    dati = {"aggiornato": "2026-11-12", "anni": [2025, 2026], "sezioni": [
        {"id": "elettricita", "titolo": "Energia elettrica", "indici": [
            {"id": "intercenter-ee19-2026", "centrale": "Intercent-ER", "titolo": "Intercent-ER", "unita": "€/MWh",
             "lotto_predefinito": "1", "lotti": {
                 "1": {"nome": "Lotto 1 – sanità MT", "varianti": {f: serie(121.32, 235.26) for f in ("F1", "F2", "F3")}},
                 "2": {"nome": "Lotto 2 – BT", "varianti": {f: serie(122.75, 236.64) for f in ("F1", "F2", "F3")}}}},
            {"id": "consip-ee22", "centrale": "Consip", "titolo": "Consip", "unita": "€/MWh", "lotto_predefinito": "6",
             "lotti": {"6": {"nome": "Lotto 6: Emilia Romagna", "varianti": {f: serie(121.33, 236.89) for f in ("F1", "F2", "F3", "F0")}},
                       "17": {"nome": "Lotto 17: Italia", "varianti": {"F1": serie(1.0, 2.0)}}}}]},
        {"id": "gas", "titolo": "Gas naturale", "indici": [
            {"id": "intercenter-gn22", "centrale": "Intercent-ER", "titolo": "Intercent-ER gas", "unita": "€/Smc",
             "lotto_predefinito": "1", "lotti": {
                 "1": {"nome": "Lotto 1 – PA", "varianti": {"Usi termici": {"2025": [None] * 12, "2026": [None] * 12}}},
                 "2": {"nome": "Lotto 2 – cogeneratori", "varianti": {"Cogenerazione": serie(None, 0.9429)}}}},
            {"id": "psv-da-arera", "titolo": "PSV day-ahead, media mensile (ARERA)", "unita": "€/MWh",
             "lotto_predefinito": "", "lotti": {"": {"nome": "", "varianti": {"": serie(33.05, 88.36)}}}},
            {"id": "pfor", "titolo": "PFOR,t ricostruito da EuGEnio", "unita": "€/MWh",
             "lotto_predefinito": "", "lotti": {"": {"nome": "", "varianti": {"": serie(35.0, 70.0)}}}}]}], "in_attesa": []}
    d = cartella / "prezzi"
    d.mkdir(parents=True, exist_ok=True)
    (d / "indici.json").write_text(json.dumps(dati), encoding="utf-8")


def test_indici_dei_prezzi_in_cima(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "DATI", tmp_path)
    monkeypatch.setattr(C, "SITO_DATI", tmp_path / "sito")
    _indici(tmp_path / "sito")
    r = N._tabella_prezzi(2026, 10)
    assert r[0] == "## Indici dei prezzi di ottobre 2026"
    assert "| Intercent-ER – Lotto 1 – sanità MT | 235,26 (+94 %) | 235,26 (+94 %) | 235,26 (+94 %) |" in r
    assert any(x.startswith("| Intercent-ER – Lotto 2 – BT |") for x in r)
    assert any(x.startswith("| Consip – Lotto 6: Emilia Romagna | 236,89 (+95 %)") for x in r)
    assert not any("Lotto 17" in x for x in r)                       # di Consip solo il lotto dell'Emilia-Romagna
    # gas: il lotto 1 non ha ottobre (anno termico nuovo): si mostra il lotto 2; PSV e PFOR con la variazione
    assert "| Intercent-ER – Lotto 2 – cogeneratori, cogenerazione | €/Smc | 0,9429 |" in r
    assert "| PSV day-ahead, media mensile (ARERA) | €/MWh | 88,36 (+167 %) |" in r
    assert "| PFOR,t ricostruito da EuGEnio | €/MWh | 70,00 (+100 %) |" in r
    assert r[-2].endswith("/indici-prezzi.html") and "PUN" not in "\n".join(r) and "TTF" not in "\n".join(r)
    # nel numero: prima i prezzi, poi il freddo
    _capoluoghi(monkeypatch, {"037006": "Bologna"})
    _giornaliero(tmp_path, {"037006": {2025: 14, 2026: 16}})
    _, testo = N.testo_mensile(2026, 10, dt.date(2026, 12, 12))
    assert testo.index("## Indici dei prezzi") < testo.index("## Il freddo")


def test_senza_file_dei_prezzi(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "SITO_DATI", tmp_path / "manca")
    assert N._tabella_prezzi(2026, 10) == []
