"""Prove di aggiorna_da_github.sh (21/11/2026, dopo l'aggiornamento fallito a v2026.11.21 che ha cancellato ~/energia).

Tutto in una cartella temporanea: un repository «origin» locale con le release, ~/energia finta con il .env, le cartelle del
sito e delle convenzioni, e un docker finto nel PATH che scrive i comandi ricevuti in un registro. Nessuna rete, nessun
container vero. Le prove girano solo dove ci sono bash, git, rsync e flock."""
import datetime
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "aggiorna_da_github.sh"
CARTELLE = ["fase3-storico", "fase4-server", "fase6-mercati", "fase7-territorio", "fase8-indicatori",
            "fase9-clima-storico", "fase10-edifici3d", "fase15-elettricita"]
ENV_SEGRETO = "CHIAVE_FINTA=solo-per-le-prove\n"

pytestmark = pytest.mark.skipif(any(shutil.which(c) is None for c in ("bash", "git", "rsync", "flock")),
                                reason="servono bash, git, rsync e flock")

DOCKER_FINTO = """#!/usr/bin/env bash
echo "$*" >> "$DOCKER_LOG"
if [ "$1 $2" = "compose build" ]; then
  [ -n "${FINTO_RM:-}" ] && rm -rf "$FINTO_RM"
  [ -n "${FINTO_BUILD_FALLISCE:-}" ] && exit 1
fi
exit 0
"""

DOCKERFILE = """FROM python:3.12-slim
COPY fase4-server/api/requirements.txt /tmp/requirements.txt
COPY fase9-clima-storico/*.py /app/clima_storico/
COPY fase15-elettricita/elettricita /app/elettricita
COPY fase10-edifici3d/edifici3d/a.py \\
     fase10-edifici3d/edifici3d/b.py /app/edifici3d/
COPY fase4-server/servizio /app/servizio
"""


def _scrivi(p: Path, testo: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(testo, encoding="utf-8")


def _git(cartella, *arg):
    subprocess.run(["git", "-C", str(cartella), *arg], check=True, capture_output=True,
                   env={**os.environ, "GIT_AUTHOR_NAME": "prova", "GIT_AUTHOR_EMAIL": "p@example.invalid",
                        "GIT_COMMITTER_NAME": "prova", "GIT_COMMITTER_EMAIL": "p@example.invalid"})


def _release(origin: Path, tag: str, script_testo: str | None = None, dockerfile: str = DOCKERFILE):
    """Scrive nel repository «origin» il contenuto minimo di una release e crea il tag."""
    for d in CARTELLE:
        _scrivi(origin / d / "LEGGIMI.txt", d)
    _scrivi(origin / "fase4-server/aggiorna_da_github.sh", script_testo or SCRIPT.read_text(encoding="utf-8"))
    _scrivi(origin / "fase4-server/docker-compose.yml", "services: {}\n")
    _scrivi(origin / "fase4-server/api/Dockerfile", dockerfile)
    _scrivi(origin / "fase4-server/api/requirements.txt", "")
    _scrivi(origin / "fase4-server/servizio/app.py", "")
    _scrivi(origin / "fase9-clima-storico/clima.py", "")
    _scrivi(origin / "fase15-elettricita/elettricita/__init__.py", "")
    _scrivi(origin / "fase10-edifici3d/edifici3d/a.py", "")
    _scrivi(origin / "fase10-edifici3d/edifici3d/b.py", "")
    _scrivi(origin / ".dockerignore", "")
    _scrivi(origin / "fase5-sito/novita.toml", "")
    _scrivi(origin / "fase5-sito/sito/index.html", '<script src="app.js?v=20261121a"></script>\n')
    _scrivi(origin / "fase6-mercati/convenzioni/a.toml", "a = 1\n")
    _scrivi(origin / "fase6-mercati/convenzioni/fonti/b.toml", "b = 1\n")
    _git(origin, "add", "-A")
    _git(origin, "commit", "-q", "-m", tag, "--allow-empty")
    _git(origin, "tag", tag)


@pytest.fixture
def banco(tmp_path):
    home = tmp_path / "home"
    energia = home / "energia"
    # ~/energia della versione installata (v2026.11.16): senza fase15-elettricita, con il .env
    for d in CARTELLE[:-1]:
        _scrivi(energia / d / "LEGGIMI.txt", d + " vecchia")
    _scrivi(energia / "fase4-server/docker-compose.yml", "services: {}\n")
    _scrivi(energia / "fase4-server/.env", ENV_SEGRETO)
    _scrivi(energia / "VERSIONE_VECCHIA", "v2026.11.16")
    shutil.copy(SCRIPT, energia / "fase4-server/aggiorna_da_github.sh")
    _scrivi(home / ".eugenio_versione", "v2026.11.16\n")
    conv = tmp_path / "convenzioni"
    _scrivi(conv / "fonti/b.toml", "b = 0\n")
    (tmp_path / "sito").mkdir()
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-q")
    binf = tmp_path / "bin"
    _scrivi(binf / "docker", DOCKER_FINTO)
    (binf / "docker").chmod(0o755)
    env = {**os.environ, "HOME": str(home), "PATH": f"{binf}:{os.environ['PATH']}",
           "EUGENIO_REPO": str(origin), "EUGENIO_CLONE": str(home / "eugenio-git"),
           "EUGENIO_ENERGIA": str(energia), "EUGENIO_SITO": str(tmp_path / "sito"),
           "EUGENIO_CONVENZIONI": str(conv), "EUGENIO_ATTESA": "0", "DOCKER_LOG": str(tmp_path / "docker.log"),
           "TMPDIR": str(tmp_path)}
    for k in ("EUGENIO_AGG_COPIA", "EUGENIO_RILANCIATO", "EUGENIO_ENV_BACKUP", "EUGENIO_STATO", "EUGENIO_REGISTRO"):
        env.pop(k, None)

    class Banco:
        pass
    b = Banco()
    b.tmp, b.home, b.energia, b.origin, b.env = tmp_path, home, energia, origin, env

    def lancia(*arg, script=None, **extra):
        r = subprocess.run(["bash", str(script or energia / "fase4-server/aggiorna_da_github.sh"), *arg],
                           env={**env, **extra}, capture_output=True, text=True, timeout=120)
        r.registro = (home / "aggiorna_da_github.log").read_text(encoding="utf-8") \
            if (home / "aggiorna_da_github.log").exists() else ""
        r.docker = (tmp_path / "docker.log").read_text(encoding="utf-8") \
            if (tmp_path / "docker.log").exists() else ""
        return r
    b.lancia = lancia
    return b


def _copie(energia: Path):
    return sorted(p.name for p in energia.parent.glob(energia.name + "_prima_*"))


def test_aggiornamento_riuscito_copia_nuova_non_cancellata_anche_con_data_vecchia(banco):
    _release(banco.origin, "v2026.11.21")
    # copie del 14–16/11 senza file .eugenio_copia, con data recente; ~/energia con una data vecchia (cp -a la conserva)
    for t in ("v2026.11.14", "v2026.11.16", "v2026.11.16b"):
        _scrivi(banco.home / f"energia_prima_{t}/fase4-server/docker-compose.yml", "")
    os.utime(banco.energia, (946684800, 946684800))     # 2000-01-01
    r = banco.lancia("v2026.11.21")
    assert r.returncode == 0, r.stdout + r.stderr
    copie = _copie(banco.energia)
    assert "energia_prima_v2026.11.21" in copie, copie
    assert copie == ["energia_prima_v2026.11.16", "energia_prima_v2026.11.16b", "energia_prima_v2026.11.21"]
    nuova = banco.home / "energia_prima_v2026.11.21"
    assert (nuova / "fase4-server/.env").read_text() == ENV_SEGRETO
    assert (nuova / ".eugenio_copia").read_text().split()[1:] == ["v2026.11.16", "v2026.11.21"]
    assert (banco.energia / "fase15-elettricita/elettricita/__init__.py").exists()
    assert (banco.energia / "fase4-server/.env").read_text() == ENV_SEGRETO
    assert "compose build api" in r.docker
    assert (banco.home / ".eugenio_versione").read_text().strip() == "v2026.11.21"
    assert "rilancio" not in r.registro                 # script del tag uguale: nessun rilancio


def test_forza_non_sovrascrive_la_copia_esistente(banco):
    _release(banco.origin, "v2026.11.21")
    vecchia = banco.home / "energia_prima_v2026.11.21"
    _scrivi(vecchia / "fase4-server/docker-compose.yml", "")
    _scrivi(vecchia / "fase4-server/.env", "QUELLA_BUONA=1\n")
    r = banco.lancia("--forza", "v2026.11.21")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (vecchia / "fase4-server/.env").read_text() == "QUELLA_BUONA=1\n"
    assert not (vecchia / "energia").exists()
    assert len(_copie(banco.energia)) == 2


def test_copia_del_env(banco):
    _release(banco.origin, "v2026.11.21")
    backup = banco.home / ".eugenio_env_backup"
    backup.mkdir()
    for i in range(12):                                  # copie vecchie: se ne tengono 10
        _scrivi(backup / f"env_2026-10-{i + 10:02d}", f"VECCHIO={i}\n")
    oggi = datetime.date.today().isoformat()
    _scrivi(backup / f"env_{oggi}", "SALVATO_A_MANO=1\n")   # come quello di Paolo del 21/11, ma diverso
    r = banco.lancia("v2026.11.21")
    assert r.returncode == 0, r.stdout + r.stderr
    nomi = sorted(p.name for p in backup.iterdir())
    assert len(nomi) == 10, nomi
    assert f"env_{oggi}" in nomi                         # quello salvato a mano non si sovrascrive
    nuovi = [n for n in nomi if n.startswith(f"env_{oggi}_")]
    assert len(nuovi) == 1
    f = backup / nuovi[0]
    assert f.read_text() == ENV_SEGRETO
    assert stat.S_IMODE(f.stat().st_mode) == 0o600
    assert stat.S_IMODE(backup.stat().st_mode) == 0o700
    assert "solo-per-le-prove" not in r.stdout + r.registro   # il segreto non si stampa


def test_copia_del_env_uguale_all_ultima_non_si_ripete(banco):
    _release(banco.origin, "v2026.11.21")
    backup = banco.home / ".eugenio_env_backup"
    _scrivi(backup / "env_2026-11-21", ENV_SEGRETO)
    r = banco.lancia("v2026.11.21")
    assert r.returncode == 0, r.stdout + r.stderr
    assert sorted(p.name for p in backup.iterdir()) == ["env_2026-11-21"]


def test_senza_env_non_si_tocca_niente(banco):
    _release(banco.origin, "v2026.11.21")
    (banco.energia / "fase4-server/.env").unlink()
    r = banco.lancia("v2026.11.21")
    assert r.returncode == 1
    assert _copie(banco.energia) == []
    assert not (banco.energia / "fase15-elettricita").exists()
    assert "compose build" not in r.docker
    assert ".eugenio_env_backup" in r.registro


def test_torna_indietro_senza_copia_non_cancella_energia(banco):
    _release(banco.origin, "v2026.11.21")
    copia = banco.home / "energia_prima_v2026.11.21"
    r = banco.lancia("v2026.11.21", FINTO_BUILD_FALLISCE="1", FINTO_RM=str(copia))
    assert r.returncode == 1
    assert not copia.exists()
    assert (banco.energia / "fase4-server/.env").read_text() == ENV_SEGRETO
    assert (banco.energia / "fase4-server/docker-compose.yml").exists()
    assert "ERRORE GRAVE" in r.registro
    assert "avvisi.invia" in r.docker                    # l'avviso all'amministratore parte
    assert r.docker.count("compose build") == 1          # niente ricostruzione da una copia che non c'è
    assert "up -d" not in r.docker
    assert (banco.home / ".eugenio_versione").read_text().strip() == "v2026.11.16"


def test_torna_indietro_con_copia_sposta_e_rimette(banco):
    _release(banco.origin, "v2026.11.21")
    r = banco.lancia("v2026.11.21", FINTO_BUILD_FALLISCE="1")
    assert r.returncode == 1
    assert (banco.energia / "VERSIONE_VECCHIA").exists()
    assert not (banco.energia / "fase15-elettricita").exists()
    assert not (banco.energia / ".eugenio_copia").exists()
    assert (banco.energia / "fase4-server/.env").read_text() == ENV_SEGRETO
    fallite = list(banco.home.glob("energia.fallita_*"))
    assert len(fallite) == 1 and (fallite[0] / "fase15-elettricita").exists()
    assert not list(banco.home.glob("energia.ripristino_*"))
    assert (banco.home / "energia_prima_v2026.11.21").exists()
    assert (banco.home / ".eugenio_versione").read_text().strip() == "v2026.11.16"


def test_controllo_dei_copy_ferma_prima_dei_container(banco):
    _release(banco.origin, "v2026.11.21", dockerfile=DOCKERFILE + "COPY fase16-nuova/modulo /app/modulo\n")
    r = banco.lancia("v2026.11.21")
    assert r.returncode == 1
    assert "fase16-nuova/modulo" in r.registro
    assert "compose build" not in r.docker and "up -d" not in r.docker
    assert (banco.energia / "VERSIONE_VECCHIA").exists()          # codice di prima rimesso
    assert not (banco.energia / "fase15-elettricita").exists()
    assert (banco.energia / "fase4-server/.env").read_text() == ENV_SEGRETO


def test_controllo_dei_copy_in_prova(banco):
    _release(banco.origin, "v2026.11.21", dockerfile=DOCKERFILE + "COPY fase16-nuova/modulo /app/modulo\n")
    r = banco.lancia("--prova", "v2026.11.21")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "fase16-nuova/modulo" in r.stdout
    assert "fase15" not in r.stdout.split("ATTENZIONE")[-1]       # fase15 la copierebbe la release: non manca
    assert _copie(banco.energia) == [] and r.docker == ""


def test_rilancio_dello_script_del_tag(banco):
    testo = SCRIPT.read_text(encoding="utf-8")
    segno = "trap 'rm -f \"$EUGENIO_AGG_COPIA\"' EXIT\n"
    assert segno in testo
    del_tag = testo.replace(segno, segno + 'echo "SCRIPT_DEL_TAG rilanciato=${EUGENIO_RILANCIATO:-}"\n', 1)
    _release(banco.origin, "v2026.11.21", script_testo=del_tag)
    r = banco.lancia("--forza")                          # senza release: la sceglie il primo script e la passa
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count("SCRIPT_DEL_TAG rilanciato=1") == 1
    assert "rilancio quello della release" in r.registro
    assert "a v2026.11.21, script della release" in r.registro
    assert (banco.home / ".eugenio_versione").read_text().strip() == "v2026.11.21"
    assert not list(banco.tmp.glob("aggiorna_da_github.*.sh"))    # copie temporanee cancellate


def test_rilancio_conserva_la_prova(banco):
    testo = SCRIPT.read_text(encoding="utf-8")
    _release(banco.origin, "v2026.11.21", script_testo=testo + "\n# diverso\n")
    r = banco.lancia("--prova", "v2026.11.21")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "rilancio quello della release" in r.registro
    assert "Prova finita" in r.stdout
    assert _copie(banco.energia) == [] and r.docker == ""
