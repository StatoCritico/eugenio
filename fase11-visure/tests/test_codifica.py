"""Uscita rediretta con una codepage Windows (05/11/2026). Su GitHub Actions (windows-2022) l'.exe con l'uscita
rediretta usava cp1252 e falliva con «UnicodeEncodeError: 'charmap' codec can't encode character '→'» durante
`EuGEnioVisure.exe modello …`; lo stesso succederebbe a chi lancia i comandi da cmd/PowerShell con `> file.txt` o
dentro un altro programma. Qui i comandi girano in un processo separato con PYTHONIOENCODING=cp1252 (come la codepage
ANSI di Windows) e l'uscita in una pipe: non devono fallire né stampare tracce di eccezioni."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

FASE = Path(__file__).resolve().parents[1]
FASE10 = FASE.parent / "fase10-edifici3d"


def esegui(args, tmp_path, **env):
    e = {**os.environ, "PYTHONIOENCODING": "cp1252", "EUGENIO_VISURE_DATI": str(tmp_path / "dati"), **env}
    e.pop("PYTHONUTF8", None)
    e["PYTHONPATH"] = os.pathsep.join([str(FASE), str(FASE / "avviatore"), e.get("PYTHONPATH", "")])
    return subprocess.run([sys.executable, *args], cwd=tmp_path, env=e, capture_output=True, timeout=300)


def test_la_prova_riproduce_il_guasto(tmp_path):
    """Controllo della prova stessa: senza correzione, un «→» con cp1252 in una pipe fa fallire Python."""
    r = esegui(["-c", "print('→')"], tmp_path)
    assert r.returncode != 0 and b"UnicodeEncodeError" in r.stderr


def test_avviatore_uscita_robusta(tmp_path):
    r = esegui(["-c", "import avviatore as AV; AV.uscita_robusta(); print('· in uso → – né'); "
                      "import sys; print('errore → ·', file=sys.stderr)"], tmp_path)
    assert r.returncode == 0, r.stderr
    assert "→ – né".encode() in r.stdout and "errore →".encode() in r.stderr


def test_avviatore_avvio_con_cp1252(tmp_path):
    """L'avviatore come lo lancia l'.exe (__main__), con il pacchetto costruito dalle sorgenti e `--stato`."""
    sys.path.insert(0, str(FASE / "avviatore"))
    import costruisci_pacchetto as CP
    zip_, sha = CP.costruisci(tmp_path / "pacchetti")
    import json
    elenco = tmp_path / "elenco.json"
    elenco.write_text(json.dumps({"formato": 1, "programma": "eugenio-visure", "revocate": [], "versioni": [
        {"versione": CP.versione(), "file": zip_.name, "sha256": sha, "url": f"https://github.com/x/{zip_.name}",
         "stato": "approvata"}]}), encoding="utf-8")
    codice = ("import runpy, sys, avviatore as AV; from pathlib import Path; "
              f"AV.risorse = lambda: Path({str(tmp_path)!r}); "
              f"sys.argv = ['avviatore', '--non-aggiornare', '--elenco', {str(elenco)!r}, '--stato']; "
              "g = runpy.run_path(AV.__file__, init_globals={'risorse': AV.risorse}, run_name='__main__')")
    r = esegui(["-c", codice], tmp_path)
    assert b"Traceback" not in r.stderr, r.stderr.decode("utf-8", "replace")
    # qui conta la codifica, non la scelta della versione (che nel test non trova il pacchetto in risorse()):
    # l'intestazione con «–» deve arrivare in UTF-8 anche con PYTHONIOENCODING=cp1252, senza Traceback
    assert "EuGEnio Visure – avviatore".encode() in r.stdout


def test_lettore_comandi_con_cp1252(tmp_path):
    r = esegui(["-m", "visure", "versione"], tmp_path)
    assert r.returncode == 0 and b"Traceback" not in r.stderr, r.stderr
    r = esegui(["-m", "visure", "--help"], tmp_path)
    assert r.returncode == 0 and "→".encode() in r.stdout, r.stderr


def test_modello_con_cp1252_e_spawn(tmp_path):
    pytest.importorskip("ifcopenshell"); pytest.importorskip("ezdxf"); pytest.importorskip("shapely")
    sys.path.insert(0, str(FASE10 / "tests"))
    import modelli_sintetici as MS
    MS.genera(tmp_path / "modelli")
    out = tmp_path / "m.geojson"
    r = esegui(["-m", "visure", "modello", str(tmp_path / "modelli" / "casa_sito.ifc"), "--uscita", str(out)],
               tmp_path, EUGENIO_MP="spawn")
    assert r.returncode == 0 and b"Traceback" not in r.stderr, r.stderr.decode("utf-8", "replace")
    assert out.exists()
    r = esegui(["-m", "visure", "prova", "--modelli"], tmp_path, EUGENIO_MP="spawn")
    assert r.returncode == 0 and b"Traceback" not in r.stderr, r.stderr.decode("utf-8", "replace")
