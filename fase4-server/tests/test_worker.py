"""Lavori periodici del worker sui file del sito: indicatori (fase 8) e clima dal 1940 (fase 9).
Niente rete: la fase 8 è sostituita da un modulo finto, gli script della fase 9 da due script finti."""
from __future__ import annotations

import json
import sys
import textwrap
import types

import pytest

from servizio import config as C

# il worker importa servizio.meteo, che usa la fase 3: se non è installata bastano dei moduli segnaposto
try:
    from servizio import meteo  # noqa: F401
except ImportError:
    finti = {"meteo_storico": {"VARIABILI": []}, "meteo_storico.aggrega": {"giornaliero": None},
             "meteo_storico.correzione": {"applica": None}, "meteo_storico.limiti": {"Limitatore": object},
             "meteo_storico.scarica": {"FONTI": {}, "client": None, "richiesta": None}}
    for nome, attr in finti.items():
        m = sys.modules.get(nome) or types.ModuleType(nome)
        m.__dict__.update({k: v for k, v in attr.items() if k not in m.__dict__})
        sys.modules[nome] = m
    sys.modules.pop("servizio.meteo", None)
from servizio import worker as W  # noqa: E402


@pytest.fixture
def sito(tmp_path, monkeypatch):
    dati = tmp_path / "sito_dati"
    dati.mkdir()
    monkeypatch.setattr(C, "SITO_DATI", dati)
    monkeypatch.setattr(C, "DATI", tmp_path / "dati")
    return dati


def scrivi(cartella, nomi, testo="{}"):
    cartella.mkdir(parents=True, exist_ok=True)
    for n in nomi:
        (cartella / n).parent.mkdir(parents=True, exist_ok=True)
        (cartella / n).write_text(testo)


def test_pubblica_sostituisce_la_cartella(tmp_path):
    finale, nuova = tmp_path / "x", tmp_path / ".x_nuova"
    scrivi(finale, ["a.json", "vecchio.json"])
    scrivi(nuova, ["a.json"], '{"n": 2}')
    W._pubblica(nuova, finale)
    assert json.loads((finale / "a.json").read_text()) == {"n": 2}
    assert not (finale / "vecchio.json").exists() and not nuova.exists()
    assert not (tmp_path / ".x_vecchia").exists()


def finta_fase8(monkeypatch, file):
    cli = types.ModuleType("indicatori_ssn.cli")
    def aggiorna(out, cache, **kw):
        scrivi(out, file, '{"nuovo": true}')
        return {"dimensioni": {f: 15 for f in file}, "mancanti": []}
    cli.aggiorna = aggiorna
    pacchetto = types.ModuleType("indicatori_ssn")
    pacchetto.cli = cli
    monkeypatch.setitem(sys.modules, "indicatori_ssn", pacchetto)
    monkeypatch.setitem(sys.modules, "indicatori_ssn.cli", cli)


def test_indicatori_pubblica(sito, monkeypatch):
    scrivi(sito / "indicatori", ["indice.json", "08.json"])
    finta_fase8(monkeypatch, ["indice.json", "08.json", "09.json"])
    W.indicatori()
    assert json.loads((sito / "indicatori" / "09.json").read_text()) == {"nuovo": True}
    assert not (sito / ".indicatori_nuova").exists()


def test_indicatori_incompleti_lasciano_i_vecchi(sito, monkeypatch):
    scrivi(sito / "indicatori", ["indice.json"] + [f"{i:02d}.json" for i in range(1, 21)])
    finta_fase8(monkeypatch, ["indice.json", "08.json"])
    with pytest.raises(RuntimeError):
        W.indicatori()
    assert (sito / "indicatori" / "20.json").read_text() == "{}"


SCARICA = """
import sys, pathlib
a = sys.argv
pathlib.Path(a[a.index("--cache") + 1]).mkdir(parents=True, exist_ok=True)
open(a[a.index("--log") + 1], "a").write("scaricato\\n")
"""
CALCOLA = """
import sys, pathlib
a = sys.argv
u = pathlib.Path(a[a.index("--uscita") + 1])
n = int(pathlib.Path(a[a.index("--cache") + 1]).joinpath("..", "n").resolve().read_text())
(u / "clima" / "08").mkdir(parents=True)
(u / "clima" / "indice.json").write_text("{}")
for i in range(n):
    (u / "clima" / "08" / f"0370{i:02d}.json").write_text('{"nuovo": 1}')
for f in ("clima_stagioni.csv", "clima_sintesi.csv", "clima_mensili.parquet"):
    (u / f).write_text("nuovo")
"""


@pytest.fixture
def fase9(sito, tmp_path, monkeypatch):
    codice = tmp_path / "codice"
    codice.mkdir()
    (codice / "scarica.py").write_text(textwrap.dedent(SCARICA))
    (codice / "calcola.py").write_text(textwrap.dedent(CALCOLA))
    lavoro = tmp_path / "lavoro"
    lavoro.mkdir()
    (lavoro / "comuni.parquet").write_text("finto")
    monkeypatch.setattr(C, "CLIMA_CODICE", codice)
    monkeypatch.setattr(C, "CLIMA_LAVORO", lavoro)
    scrivi(sito / "clima", ["indice.json", "08/037006.json", "08/037007.json"])
    for f in ("clima_stagioni.csv", "clima_sintesi.csv"):
        (sito / f).write_text("vecchio")
    return lavoro


def test_clima_pubblica(sito, fase9):
    (fase9 / "n").write_text("5")
    W.clima()
    assert len(list((sito / "clima" / "08").glob("*.json"))) == 5
    assert (sito / "clima_sintesi.csv").read_text() == "nuovo"
    assert (fase9 / "clima_mensili.parquet").exists() and not (sito / "clima_mensili.parquet").exists()
    assert "scaricato" in (fase9 / "scarica.log").read_text()
    assert not (sito / ".clima_nuova").exists()


def test_clima_incompleto_lascia_i_vecchi(sito, fase9):
    (fase9 / "n").write_text("1")          # 2 file JSON contro i 3 pubblicati
    with pytest.raises(RuntimeError):
        W.clima()
    assert (sito / "clima" / "08" / "037007.json").exists()
    assert (sito / "clima_sintesi.csv").read_text() == "vecchio"


def test_clima_senza_comuni(sito, tmp_path, monkeypatch):
    monkeypatch.setattr(C, "CLIMA_LAVORO", tmp_path / "vuota")
    with pytest.raises(FileNotFoundError):
        W.clima()


def test_date_del_clima():
    assert (10, 7) in C.CLIMA_DATE and (10, 1) in C.CLIMA_DATE


def test_mercati_senza_credenziali_gme_non_manda_email(monkeypatch):
    """Credenziali GME mancanti: nessun avviso; un errore vero invece sì."""
    import sys, types
    from servizio import worker as W
    inviati = []
    monkeypatch.setattr(W.avvisi, "invia", lambda o, t, *a, **k: inviati.append(o) or True)
    esiti = [{"errori": ["Credenziali GME mancanti (GME_UTENTE / GME_PASSWORD o password_file)"], "sorveglianza": {}},
             {"errori": ["Credenziali GME mancanti (x)", "EEX: timeout"], "sorveglianza": {}}]
    notturno = types.SimpleNamespace(esegui=lambda cfg: esiti.pop(0))
    pacchetto = types.ModuleType("mercati_energia"); pacchetto.notturno = notturno
    config = types.ModuleType("mercati_energia.config"); config.carica = lambda p: {}
    monkeypatch.setitem(sys.modules, "mercati_energia", pacchetto)
    monkeypatch.setitem(sys.modules, "mercati_energia.notturno", notturno)
    monkeypatch.setitem(sys.modules, "mercati_energia.config", config)
    W.mercati()
    assert inviati == []
    W.mercati()
    assert inviati == ["dati di mercato: aggiornamento incompleto"]


def test_mercato_mgp_email_solo_se_da_segnalare(monkeypatch, tmp_path):
    """(20/11/2026) Lavoro mercato-mgp: email solo per i motivi decisi da mgp_notturno; senza configurazione nulla."""
    import sys, types
    from servizio import worker as W
    inviati = []
    monkeypatch.setattr(W.avvisi, "invia", lambda o, t, *a, **k: inviati.append((o, t)) or True)
    monkeypatch.setattr(W.C, "MERCATI_CONFIG", str(tmp_path / "manca.toml"))
    assert W.mercato_mgp() == {}
    (tmp_path / "config.toml").write_text("")
    monkeypatch.setattr(W.C, "MERCATI_CONFIG", str(tmp_path / "config.toml"))
    esiti = [{"errori": ["mgp_offerte 2025-11-01: rete"], "da_segnalare": []},
             {"errori": [], "da_segnalare": ["Autenticazione GME fallita: password scaduta"]}]
    mgp_notturno = types.SimpleNamespace(esegui=lambda cfg: esiti.pop(0))
    pacchetto = types.ModuleType("mercati_energia"); pacchetto.mgp_notturno = mgp_notturno
    config = types.ModuleType("mercati_energia.config"); config.carica = lambda p: {}
    monkeypatch.setitem(sys.modules, "mercati_energia", pacchetto)
    monkeypatch.setitem(sys.modules, "mercati_energia.mgp_notturno", mgp_notturno)
    monkeypatch.setitem(sys.modules, "mercati_energia.config", config)
    W.mercato_mgp()
    assert inviati == []
    W.mercato_mgp()
    assert len(inviati) == 1 and "password scaduta" in inviati[0][1]
    assert ":" in W.C.ORA_MERCATO_MGP and "mercato-mgp" in W.__doc__


# ---------------------------------------------------------------------------------------------- rete elettrica (17/11/2026)
def test_rete_prossima_lettura_ogni_15_minuti():
    base = 1_700_000_000 // 900 * 900          # un quarto d'ora esatto
    assert W.prossima_lettura(base, 15) == base + 180                 # minuto 3 del quarto d'ora
    assert W.prossima_lettura(base + 180, 15) == base + 900 + 180
    assert W.prossima_lettura(base + 500, 15) == base + 900 + 180
    assert W.prossima_lettura(base + 100, 15) == base + 180


def test_rete_interruzioni_email_solo_dopo_72_ore(monkeypatch):
    inviati = []
    monkeypatch.setattr(W.avvisi, "invia", lambda oggetto, testo: inviati.append(oggetto))
    t0 = 1_700_000_000.0
    e = W._Errori(ultimo_ok=t0, ore=72)

    def guasto():
        raise RuntimeError("HTTP 500")
    for k in range(1, 72 * 4 + 1):                        # 72 ore di letture fallite ogni 15 minuti: nessuna email
        assert not e.esegui(guasto, t0 + k * 900)
    assert inviati == []
    for k in range(72 * 4 + 1, 80 * 4):                   # oltre le 72 ore: una sola email
        e.esegui(guasto, t0 + k * 900)
    assert inviati == ["rete elettrica: interruzioni non lette da più di 72 ore"]
    assert e.esegui(lambda: None, t0 + 81 * 3600) and e.n == 0
    assert len(inviati) == 1                              # nessuna email quando ripartono
    for k in range(1, 10):
        e.esegui(guasto, t0 + 81 * 3600 + k * 900)
    assert len(inviati) == 1


def test_rete_saturazione_email_solo_province_ferme_da_72_ore(tmp_path, monkeypatch):
    import datetime as dt
    from servizio import rete as R
    inviati = []
    monkeypatch.setattr(W.avvisi, "invia", lambda oggetto, testo: inviati.append(oggetto))
    monkeypatch.setattr(C, "RETE_DB", tmp_path / "rete" / "rete.sqlite")
    t0 = dt.datetime(2026, 11, 18, 1, 15, tzinfo=R.ROMA)
    db = R.connetti()
    with R.transazione(db):
        db.executemany("INSERT INTO province (cod) VALUES (?)", [(f"{k:03d}",) for k in range(1, 11)])
    db.close()
    giro = {"ora": t0, "ok": True}

    def finto():
        if not giro["ok"]:
            raise RuntimeError("elenco delle province non letto")
        db = R.connetti()
        with R.transazione(db):
            for k in range(1, 8):                           # 7 province falliscono ogni notte
                R._segna_errore(db, f"{k:03d}", R.iso(giro["ora"]), "HTTP 500")
        db.close()
        return {"ok": 3, "falliti": {}}
    monkeypatch.setattr(R, "aggiorna_saturazione", finto)
    monkeypatch.setattr(R, "adesso", lambda: giro["ora"])
    for notte in range(3):                                  # 0, 24, 48 ore: niente
        giro["ora"] = t0 + dt.timedelta(days=notte)
        W.rete_saturazione()
    giro["ora"] = t0 + dt.timedelta(days=3)                 # 72 ore esatte: non ancora «più di 72»
    assert W.rete_saturazione()["ferme_72h"] == [] and inviati == []
    giro["ora"] = t0 + dt.timedelta(days=3, hours=1)
    assert len(W.rete_saturazione()["ferme_72h"]) == 7
    assert inviati == ["rete elettrica: 7 province non aggiornate da più di 72 ore"]
    giro["ora"], giro["ok"] = t0 + dt.timedelta(days=4), False    # giro fallito: nessuna email in più, nessuna eccezione
    W.rete_saturazione()
    assert len(inviati) == 1
    assert len(R.province_ferme(ora=t0 + dt.timedelta(days=7, hours=2))) == 10   # anche 8-10, ferme dal giorno 4


def test_rete_saturazione_cinque_province_ferme_nessuna_email(tmp_path, monkeypatch):
    import datetime as dt
    from servizio import rete as R
    inviati = []
    monkeypatch.setattr(W.avvisi, "invia", lambda oggetto, testo: inviati.append(oggetto))
    monkeypatch.setattr(C, "RETE_DB", tmp_path / "rete" / "rete.sqlite")
    t0 = dt.datetime(2026, 11, 18, 1, 15, tzinfo=R.ROMA)
    db = R.connetti()
    with R.transazione(db):
        for k in range(1, 6):
            R._segna_errore(db, f"{k:03d}", R.iso(t0), "HTTP 500")
    db.close()
    monkeypatch.setattr(R, "aggiorna_saturazione", lambda: {"ok": 100, "falliti": {}})
    monkeypatch.setattr(R, "adesso", lambda: t0 + dt.timedelta(days=10))
    assert len(W.rete_saturazione()["ferme_72h"]) == 5 and inviati == []


# ---------------------------------------------------------------------------------------------- servizio GSE (20/11/2026)
def test_gse_aree_email_solo_se_non_risponde(monkeypatch):
    from servizio import rete as R
    inviati = []
    monkeypatch.setattr(W.avvisi, "invia", lambda oggetto, testo: inviati.append((oggetto, testo)))
    monkeypatch.setattr(R, "controlla_servizio_gse", lambda: {"ok": True, "strato_0": "AC_2025"})
    assert W.gse_aree()["ok"] and inviati == []
    def guasto():
        raise RuntimeError("servizio del GSE: HTTP 404")
    monkeypatch.setattr(R, "controlla_servizio_gse", guasto)
    e = W.gse_aree()
    assert e == {"ok": False, "errore": "RuntimeError: servizio del GSE: HTTP 404"}
    assert len(inviati) == 1 and inviati[0][0] == "servizio del GSE delle aree convenzionali non risponde"
    assert R.URL_GSE_AREE in inviati[0][1] and "rete.js" in inviati[0][1]


def test_gse_aree_nel_ciclo_una_volta_al_mese():
    import inspect
    s = inspect.getsource(W.ciclo)
    assert "C.GSE_CONTROLLO_GIORNO" in s and 'fatti.get("gse_aree") != oggi' in s
    assert 1 <= C.GSE_CONTROLLO_GIORNO <= 28 and 0 <= C.GSE_CONTROLLO_ORA <= 23
