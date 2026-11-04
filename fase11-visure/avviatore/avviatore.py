"""Avviatore di EuGEnio Visure per Windows (diventa EuGEnioVisure.exe con PyInstaller; gira anche con Python).

Cosa fa, a ogni avvio:
  1. legge l'elenco delle **versioni approvate** (versioni_approvate.json): quello incorporato nell'.exe e, se c'è
     rete, quello pubblicato nel repository (github.com/statocritico/eugenio, solo HTTPS, solo host di GitHub);
  2. sceglie la versione approvata più recente compatibile con questo avviatore, che non sia revocata e che non
     abbia già fallito i controlli su questo PC;
  3. se il pacchetto di quella versione non c'è, lo prende da quello incorporato o lo scarica dall'indirizzo
     dell'elenco; in ogni caso ne controlla l'impronta SHA-256, che deve essere **identica** a quella dell'elenco
     (un pacchetto diverso, anche di un solo byte, si cancella e non si usa);
  4. carica il pacchetto ed esegue il controllo di avvio (visure.autotest): se fallisce, segna la versione come
     fallita e torna alla precedente approvata;
  5. avvia il lettore (pagina locale nel browser, o i comandi passati: `EuGEnioVisure.exe leggi cartella`); dal
     04/11/2026 anche la conversione dei modelli DXF/IFC (`EuGEnioVisure.exe modello edificio.ifc`, scheda «Modelli
     DXF/IFC» della pagina locale), con lo stesso codice di `importa-modello` della fase 10 dentro il pacchetto approvato.

Il lettore non usa credenziali e non si collega a SISTER o ad altri servizi dell'Agenzia delle Entrate; l'unica
connessione dell'avviatore è la lettura dell'elenco e dei pacchetti da GitHub (spegnibile con --non-aggiornare).

Opzioni dell'avviatore (prima dei comandi del lettore): --non-aggiornare, --stato (dice quale versione userebbe e
perché, poi esce), --elenco FILE (elenco locale, per le prove).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

VERSIONE_AVVIATORE = "0.1.0"
URL_ELENCO = "https://raw.githubusercontent.com/statocritico/eugenio/main/fase11-visure/avviatore/versioni_approvate.json"
HOST_AMMESSI = {"raw.githubusercontent.com", "github.com", "objects.githubusercontent.com",
                "release-assets.githubusercontent.com"}
MAX_ELENCO = 256 * 1024
MAX_PACCHETTO = 25 * 1024 * 1024
AVVISO = ("EuGEnio Visure legge solo i PDF delle visure che scegli, sul tuo computer: non chiede credenziali, non si "
          "collega a SISTER né ad altri servizi dell'Agenzia delle Entrate e non invia le visure a nessuno. I dati "
          "letti non sostituiscono le visure ufficiali; vietato usarli per re-identificare persone.")


def _moduli_del_lettore():   # pragma: no cover - mai chiamata: dice a PyInstaller cosa serve al pacchetto caricato
    import argparse, base64, collections, csv, dataclasses, email.parser, email.policy, html, http.server  # noqa: F401,E401
    import importlib.resources, io, logging, re, secrets, tempfile, threading, time, tomllib  # noqa: F401,E401
    import unicodedata, urllib.parse, uuid, webbrowser, zipfile, zlib  # noqa: F401,E401
    import pypdf  # noqa: F401
    # conversione dei modelli DXF/IFC (edifici3d/importa.py nel pacchetto): librerie compilate nell'.exe
    import ctypes, ctypes.wintypes, math, multiprocessing, multiprocessing.spawn  # noqa: F401,E401
    import numpy, shapely, shapely.geometry, shapely.ops, shapely.strtree, pyproj  # noqa: F401,E401
    import ezdxf, ezdxf.recover, ezdxf.render  # noqa: F401,E401
    import ifcopenshell, ifcopenshell.geom, ifcopenshell.api, ifcopenshell.util.placement  # noqa: F401,E401


# ------------------------------------------------------------------ cartelle e file
def cartella_dati() -> Path:
    if os.environ.get("EUGENIO_VISURE_DATI"):
        d = Path(os.environ["EUGENIO_VISURE_DATI"])
    elif os.name == "nt":
        d = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "EuGEnio" / "Visure"
    else:
        d = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "eugenio-visure"
    (d / "versioni").mkdir(parents=True, exist_ok=True)
    return d


def risorse() -> Path:
    """Cartella dei file incorporati: quella di PyInstaller nell'.exe, accanto a questo file con Python."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def registra(d: Path, testo: str) -> None:
    try:
        with open(d / "avviatore.log", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {testo}\n")
    except OSError:
        pass


def leggi_stato(d: Path) -> dict:
    try:
        return json.loads((d / "stato.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"fallite": []}


def scrivi_stato(d: Path, st: dict) -> None:
    (d / "stato.json").write_text(json.dumps(st, indent=1), encoding="utf-8")


# ------------------------------------------------------------------ elenco delle versioni approvate
def _num(v: str) -> tuple:
    return tuple(int(x) for x in str(v).split(".") if x.isdigit())


def valida_elenco(e) -> dict:
    if not isinstance(e, dict) or e.get("formato") != 1 or e.get("programma") != "eugenio-visure":
        raise ValueError("elenco non valido")
    for v in e.get("versioni", []):
        if not (isinstance(v, dict) and v.get("versione") and v.get("file") and len(str(v.get("sha256", ""))) == 64):
            raise ValueError("voce dell'elenco non valida")
        if "/" in v["file"] or "\\" in v["file"] or v["file"].startswith("."):
            raise ValueError("nome di file non ammesso")
    return e


def host_ammesso(url: str) -> bool:
    u = urllib.parse.urlparse(url)
    return u.scheme == "https" and (u.hostname or "") in HOST_AMMESSI


def scarica(url: str, massimo: int, timeout: float = 15) -> bytes:
    """Solo HTTPS verso GitHub; i reindirizzamenti di GitHub verso i suoi host dei file sono ammessi."""
    if not host_ammesso(url):
        raise ValueError(f"indirizzo non ammesso: {url}")

    class SoloGitHub(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            if not host_ammesso(newurl):
                raise ValueError(f"reindirizzamento non ammesso: {newurl}")
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    op = urllib.request.build_opener(SoloGitHub)
    req = urllib.request.Request(url, headers={"User-Agent": f"EuGEnioVisure/{VERSIONE_AVVIATORE}"})
    with op.open(req, timeout=timeout) as r:
        dati = r.read(massimo + 1)
    if len(dati) > massimo:
        raise ValueError("file troppo grande")
    return dati


def elenco(d: Path, aggiorna: bool, file_elenco: str | None = None) -> tuple[dict, str]:
    """(elenco, provenienza). Ordine: file indicato → remoto (salvato in cache) → cache → incorporato."""
    if file_elenco:
        return valida_elenco(json.loads(Path(file_elenco).read_text(encoding="utf-8"))), "file indicato"
    incorporato = valida_elenco(json.loads((risorse() / "versioni_approvate.json").read_text(encoding="utf-8")))
    if aggiorna:
        try:
            remoto = valida_elenco(json.loads(scarica(URL_ELENCO, MAX_ELENCO, timeout=6)))
            (d / "versioni_approvate.json").write_text(json.dumps(remoto, indent=1), encoding="utf-8")
            return _con_revoche(remoto, incorporato), "repository"
        except Exception as e:  # noqa: BLE001 - senza rete si usa quello che c'è
            registra(d, f"elenco remoto non letto: {e}")
    try:
        cache = valida_elenco(json.loads((d / "versioni_approvate.json").read_text(encoding="utf-8")))
        return _con_revoche(cache, incorporato), "copia locale"
    except (OSError, ValueError):
        return incorporato, "incorporato"


def _con_revoche(a: dict, b: dict) -> dict:
    """Le revoche si sommano: un'impronta revocata in uno qualsiasi degli elenchi non si usa."""
    out = dict(a)
    out["revocate"] = sorted(set(a.get("revocate", [])) | set(b.get("revocate", [])))
    return out


def candidate(e: dict, fallite: set[str]) -> list[dict]:
    rev = set(e.get("revocate", []))
    ok = [v for v in e.get("versioni", []) if v.get("stato", "approvata") == "approvata" and v["sha256"] not in rev
          and v["sha256"] not in fallite and _num(v.get("minimo_avviatore", "0")) <= _num(VERSIONE_AVVIATORE)]
    return sorted(ok, key=lambda v: _num(v["versione"]), reverse=True)


# ------------------------------------------------------------------ pacchetti
def procura(v: dict, d: Path, aggiorna: bool) -> Path | None:
    """Il pacchetto della versione, con l'impronta giusta, nella cartella delle versioni (o None)."""
    dest = d / "versioni" / v["file"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        if sha256(dest) == v["sha256"]:
            return dest
        registra(d, f"{dest.name}: impronta diversa dall'elenco, cancellato")
        dest.unlink()
    inc = risorse() / "pacchetti" / v["file"]
    if inc.exists() and sha256(inc) == v["sha256"]:
        shutil.copyfile(inc, dest)
        return dest
    if aggiorna and v.get("url"):
        try:
            dati = scarica(v["url"], MAX_PACCHETTO)
        except Exception as e:  # noqa: BLE001
            registra(d, f"{v['file']}: non scaricato ({e})")
            return None
        if hashlib.sha256(dati).hexdigest() != v["sha256"]:
            registra(d, f"{v['file']}: scaricato ma con impronta diversa dall'elenco, scartato")
            return None
        fd, tmp = tempfile.mkstemp(dir=d / "versioni", suffix=".part")
        with os.fdopen(fd, "wb") as f:
            f.write(dati)
        os.replace(tmp, dest)
        return dest
    return None


def _dimentica_visure() -> None:
    for k in [k for k in sys.modules if k in ("visure", "edifici3d") or k.startswith(("visure.", "edifici3d."))]:
        del sys.modules[k]


def carica(zip_: Path, versione: str):
    """Importa il pacchetto dallo zip ed esegue il controllo di avvio. Restituisce il modulo `visure.__main__` o
    solleva un'eccezione con il motivo."""
    _dimentica_visure()
    sys.path.insert(0, str(zip_))
    try:
        import importlib
        mod = importlib.import_module("visure")
        if getattr(mod, "VERSIONE", None) != versione:
            raise RuntimeError(f"il pacchetto dice di essere la versione {getattr(mod, 'VERSIONE', '?')}")
        ok, msg = importlib.import_module("visure.autotest").prova()
        if not ok:
            raise RuntimeError(f"controllo di avvio non superato: {msg}")
        return importlib.import_module("visure.__main__")
    except Exception:
        sys.path.remove(str(zip_))
        _dimentica_visure()
        raise


def prepara(aggiorna: bool = True, file_elenco: str | None = None) -> tuple[object | None, list[str]]:
    """(modulo della riga di comando del lettore, righe di resoconto)."""
    d = cartella_dati()
    st = leggi_stato(d)
    fallite = set(st.get("fallite", []))
    e, prov = elenco(d, aggiorna, file_elenco)
    note = [f"elenco delle versioni approvate: {prov}"]
    for v in candidate(e, fallite):
        z = procura(v, d, aggiorna)
        if not z:
            note.append(f"versione {v['versione']}: pacchetto non disponibile")
            continue
        try:
            cli = carica(z, v["versione"])
        except Exception as ex:  # noqa: BLE001
            note.append(f"versione {v['versione']}: {ex}; si torna alla precedente")
            registra(d, f"versione {v['versione']} fallita: {ex}")
            st.setdefault("fallite", []).append(v["sha256"])
            scrivi_stato(d, st)
            continue
        note.append(f"in uso la versione {v['versione']} (SHA-256 {v['sha256'][:16]}…)")
        st["ultima"] = v["sha256"]
        scrivi_stato(d, st)
        registra(d, note[-1])
        return cli, note
    note.append("nessuna versione approvata utilizzabile")
    return None, note


def principale(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    aggiorna = "--non-aggiornare" not in argv
    solo_stato = "--stato" in argv
    file_elenco = None
    if "--elenco" in argv:
        i = argv.index("--elenco")
        file_elenco = argv[i + 1]
        del argv[i:i + 2]
    argv = [a for a in argv if a not in ("--non-aggiornare", "--stato")]
    print(f"EuGEnio Visure – avviatore {VERSIONE_AVVIATORE}\n{AVVISO}\n")
    cli, note = prepara(aggiorna, file_elenco)
    for n in note:
        print("· " + n)
    if cli is None:
        print("\nImpossibile avviare: nessuna versione approvata disponibile. Riprova con la rete accesa o scarica di "
              "nuovo l'avviatore da github.com/statocritico/eugenio/releases.")
        return 3
    if solo_stato:
        return 0
    return cli.principale(argv or ["web"])


if __name__ == "__main__":
    # la conversione dei modelli legge il file in un processo separato: nell'.exe (e su Windows) è «spawn», che
    # rilancia questo eseguibile; freeze_support() lo riconosce e fa partire solo il processo figlio
    import multiprocessing
    multiprocessing.freeze_support()
    sys.exit(principale())
