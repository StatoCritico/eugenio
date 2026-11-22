"""Lavoro «suolo» del worker (22/11/2026, pagina «Suolo e aree agricole», fase 16). Nessuna rete: lo scaricatore è finto;
il costruttore è quello vero della fase 16 con i campioni inventati di fase16-suolo/tests/campioni.py (se la fase 16 è
nel PYTHONPATH) oppure un modulo finto."""
from __future__ import annotations

import datetime as dt
import inspect
import json
import shutil
import sys
import types
from pathlib import Path

import pytest

from servizio import config as C
from test_worker import W, scrivi  # noqa: E402  (moduli segnaposto della fase 3 già sistemati lì)

FASE16 = Path(__file__).resolve().parents[2] / "fase16-suolo"
MAPPA = Path(__file__).resolve().parents[2] / "fase5-sito" / "sito" / "dati" / "mappa"


@pytest.fixture
def cartelle(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "DATI", tmp_path / "dati")
    monkeypatch.setattr(C, "SUOLO_DATI", tmp_path / "dati" / "suolo")
    monkeypatch.setattr(C, "SITO_DATI", tmp_path / "sito_dati")
    monkeypatch.setattr(C, "SUOLO_CARTE", False)
    (tmp_path / "sito_dati").mkdir()
    shutil.copytree(MAPPA, tmp_path / "sito_dati" / "mappa")
    return tmp_path


@pytest.fixture
def email(monkeypatch):
    from servizio import avvisi
    inviati = []
    monkeypatch.setattr(avvisi, "invia", lambda oggetto, testo, *a, **k: inviati.append((oggetto, testo)) or True)
    return inviati


def fase16(monkeypatch, scarica, costruisci=None, agricolo=None):
    """Moduli finti suolo.scarica (e, se dati, suolo.costruisci e suolo.agricolo); altrimenti il costruttore vero."""
    pacchetto = types.ModuleType("suolo")
    sm = types.ModuleType("suolo.scarica")
    sm.scarica = scarica
    moduli = {"suolo": pacchetto, "suolo.scarica": sm}
    pacchetto.__path__ = [str(FASE16 / "suolo")]          # il costruttore vero si importa da qui
    if costruisci is None:
        if str(FASE16) not in sys.path:
            sys.path.insert(0, str(FASE16))
        import importlib
        monkeypatch.setitem(sys.modules, "suolo", pacchetto)
        moduli["suolo.costruisci"] = importlib.import_module("suolo.costruisci")
    else:
        cm = types.ModuleType("suolo.costruisci")
        cm.costruisci = costruisci
        moduli["suolo.costruisci"] = cm
    if agricolo is not None:
        am = types.ModuleType("suolo.agricolo")
        am.agricolo = agricolo
        moduli["suolo.agricolo"] = am
    for nome, m in moduli.items():
        monkeypatch.setitem(sys.modules, nome, m)
    pacchetto.scarica, pacchetto.costruisci = sm, moduli["suolo.costruisci"]


def _scarica_campioni(cambiati=("ispra", "coltivazioni", "censimento2020"), carte=None):
    def scarica(raw, carte_=False, **k):
        sys.path.insert(0, str(FASE16 / "tests"))
        import campioni
        if not (Path(raw) / "ispra_indicatori.xlsx").exists():
            campioni.raw(Path(raw), agricolo=False)
        stato = {"ispra": {"nome": "consumo_suolo_2016_Com_Prov_Reg_Naz_v1.0.xlsx"}, **(carte or {})}
        return {"cambiati": list(cambiati), "stato": stato}
    return scarica


def test_suolo_pubblica_con_il_costruttore_vero(cartelle, email, monkeypatch):
    pytest.importorskip("openpyxl")
    fase16(monkeypatch, _scarica_campioni())
    e = W.suolo()
    assert e["pubblicati"] == 21 and email == []                   # italia.json + 20 regioni
    it = json.loads((C.SITO_DATI / "suolo" / "italia.json").read_text(encoding="utf-8"))
    assert it["anni"]["suolo"] == [2006, 2012, 2015] and not (C.SITO_DATI / ".suolo_nuova").exists()
    # di nuovo, niente di cambiato: non si ricostruisce
    fase16(monkeypatch, _scarica_campioni(cambiati=()))
    assert W.suolo()["invariato"] is True
    # un controllo non superato (somme che non tornano) lascia i file di prima e manda un'email
    import campioni
    campioni.scrivi_excel(C.SUOLO_DATI / "ispra_indicatori.xlsx", alterato={("Comuni", "2015"): {"csuolo1": 1.0}})
    fase16(monkeypatch, _scarica_campioni(cambiati=("ispra",)))
    e = W.suolo()
    assert "errore" in e and "somma" in e["errore"] and len(email) == 1 and "controlli" in email[0][0]
    assert json.loads((C.SITO_DATI / "suolo" / "italia.json").read_text(encoding="utf-8")) == it


def test_suolo_scarto_oltre_il_2_per_cento_e_forza(cartelle, email, monkeypatch):
    pytest.importorskip("openpyxl")
    fase16(monkeypatch, _scarica_campioni())
    W.suolo()
    f = C.SITO_DATI / "suolo" / "italia.json"
    it = json.loads(f.read_text(encoding="utf-8"))
    it["regioni"][7]["suolo"]["2015"][2] *= 1.1                     # i file pubblicati avevano il 10 % in più
    f.write_text(json.dumps(it))
    e = W.suolo()
    assert "2 %" in e["errore"] and len(email) == 1
    e = W.suolo(forza=True)
    assert e["pubblicati"] == 21 and len(email) == 1


def test_suolo_incrocio_agricolo_una_volta_per_carta(cartelle, email, monkeypatch):
    monkeypatch.setattr(C, "SUOLO_CARTE", True)
    carte = {"cambiamenti": {"nome": "consumo_suolo_2024-2025.tif", "periodo": "2024-2025"}, "uso": {"nome": "Uso_del_suolo_2023.tif"}}
    chiamate = []

    def agricolo(camb, uso, mappa, uscita, anno=None):
        chiamate.append((Path(camb).name, Path(uso).name, anno))
        Path(uscita).write_text("{}")
        return {"italia": {"lordo": [1.0], "agricolo": [0.5]}, "secondi": 1}

    def costruisci(raw, uscita, mappa=None, precedente=None, forza=False):
        scrivi(uscita, ["italia.json", "08.json"])
        return {"ok": 1}
    fase16(monkeypatch, _scarica_campioni(cambiati=("cambiamenti", "uso"), carte=carte), costruisci, agricolo)
    e = W.suolo()
    assert chiamate == [("consumo_suolo_2024-2025.tif", "Uso_del_suolo_2023.tif", 2025)]
    assert e["agricolo"]["agricolo_ha"] == 0.5 and (C.SUOLO_DATI / "agricolo_2025.json").exists() and e["pubblicati"] == 2
    # stessa carta il mese dopo: niente incrocio, niente costruzione
    fase16(monkeypatch, _scarica_campioni(cambiati=(), carte=carte), costruisci, agricolo)
    assert W.suolo()["invariato"] is True and len(chiamate) == 1
    # incrocio che fallisce: email, ma la pagina si costruisce lo stesso
    def guasto(*a, **k):
        raise MemoryError("troppo grande")
    (C.SUOLO_DATI / "agricolo_2025.json").unlink()
    fase16(monkeypatch, _scarica_campioni(cambiati=("ispra",), carte=carte), costruisci, guasto)
    e = W.suolo()
    assert "errore" in e["agricolo"] and e["pubblicati"] == 2 and len(email) == 1


def test_suolo_email_solo_dopo_due_mesi_senza_risposta(cartelle, email, monkeypatch):
    def guasto(raw, carte=False, **k):
        raise OSError("connessione rifiutata")
    fase16(monkeypatch, guasto, costruisci=lambda *a, **k: {})
    mese = {"m": dt.datetime(2026, 12, 6, 6, tzinfo=W.ROMA)}

    class Ora(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return mese["m"]
    monkeypatch.setattr(W.dt, "datetime", Ora)
    W.suolo()
    W.suolo()
    assert email == []
    mese["m"] = dt.datetime(2027, 1, 6, 6, tzinfo=W.ROMA)
    W.suolo()
    W.suolo()
    assert len(email) == 1 and "due mesi" in email[0][0]


def test_suolo_nel_ciclo_nei_comandi_e_nella_configurazione():
    s = inspect.getsource(W.ciclo)
    assert 'fatti.get("suolo") != oggi' in s and "C.SUOLO_GIORNO" in s and "_suolo_mancante()" in s
    assert "|carichi|suolo|suolo-forza" in W.__doc__
    sorgente = inspect.getsource(W)
    assert '"suolo": suolo' in sorgente and '"suolo-forza"' in sorgente
    assert C.SUOLO_GIORNO == 6 and C.SUOLO_ORA == "05:30" and isinstance(C.SUOLO_CARTE, bool)
    assert str(C.SUOLO_DATI).endswith("suolo")


def test_immagine_aggiornamento_e_repository():
    """fase16-suolo nell'immagine e fra le cartelle copiate dall'aggiornamento; i dati costruiti (dati/suolo) non si
    sovrascrivono con l'rsync del sito e non vanno nel repository."""
    radice = Path(__file__).resolve().parents[2]
    df = (radice / "fase4-server" / "api" / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY fase16-suolo/suolo /app/suolo" in df
    sh = (radice / "fase4-server" / "aggiorna_da_github.sh").read_text(encoding="utf-8")
    assert "fase15-elettricita fase16-suolo)" in sh and "--exclude=dati/suolo/" in sh
    gi = (radice / ".gitignore").read_text(encoding="utf-8")
    assert "fase5-sito/sito/dati/suolo/" in gi and "fase16-suolo/raw/" in gi
