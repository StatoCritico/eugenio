"""Avviatore: pacchetto riproducibile, impronte SHA-256 delle versioni approvate, revoche, ritorno alla versione
precedente quando la nuova fallisce il controllo di avvio, indirizzi ammessi."""
import hashlib
import json
import sys
import zipfile

import pytest

import avviatore as AV
import costruisci_pacchetto as CP


@pytest.fixture()
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setenv("EUGENIO_VISURE_DATI", str(tmp_path / "dati"))
    res = tmp_path / "risorse"
    (res / "pacchetti").mkdir(parents=True)
    monkeypatch.setattr(AV, "risorse", lambda: res)
    zip_, sha = CP.costruisci(tmp_path / "dist")
    yield tmp_path, res, zip_, sha
    AV._dimentica_visure()
    sys.path[:] = [p for p in sys.path if not p.endswith(".zip")]


def elenco(*voci, revocate=()):
    return {"formato": 1, "programma": "eugenio-visure", "versioni": list(voci), "revocate": list(revocate)}


def voce(v, file, sha, **k):
    return {"versione": v, "file": file, "sha256": sha, "url": f"https://github.com/x/{file}", "stato": "approvata", **k}


def guasta(zip_buono, dest, versione):
    """Una versione «nuova» che fallisce il controllo di avvio (autotest che restituisce False)."""
    with zipfile.ZipFile(zip_buono) as a, zipfile.ZipFile(dest, "w") as b:
        for n in a.namelist():
            dati = a.read(n)
            if n == "visure/__init__.py":
                dati = dati.replace(b'VERSIONE = "0.1.0"', f'VERSIONE = "{versione}"'.encode())
            if n == "visure/autotest.py":
                dati += b"\n\ndef prova():\n    return False, 'guasto di prova'\n"
            b.writestr(n, dati)
    return hashlib.sha256(dest.read_bytes()).hexdigest()


def test_pacchetto_riproducibile(tmp_path):
    _, a = CP.costruisci(tmp_path / "a")
    _, b = CP.costruisci(tmp_path / "b")
    assert a == b


def test_elenco_del_repository_aggiornato(tmp_path):
    """L'impronta della versione attuale nell'elenco è quella del pacchetto costruito dalle sorgenti di adesso
    (dopo ogni modifica al lettore: python avviatore/costruisci_pacchetto.py --aggiorna-elenco)."""
    e = AV.valida_elenco(json.loads((CP.QUI / "versioni_approvate.json").read_text(encoding="utf-8")))
    v = CP.versione()
    voci = [x for x in e["versioni"] if x["versione"] == v]
    assert voci, f"versione {v} non nell'elenco"
    _, sha = CP.costruisci(tmp_path)
    assert voci[0]["sha256"] == sha
    assert e["visura_api"]["stato"] == "non attivo"


def test_usa_il_pacchetto_incorporato(ambiente):
    tmp, res, zip_, sha = ambiente
    (res / "pacchetti" / zip_.name).write_bytes(zip_.read_bytes())
    f = tmp / "elenco.json"
    f.write_text(json.dumps(elenco(voce("0.1.0", zip_.name, sha))))
    cli, note = AV.prepara(aggiorna=False, file_elenco=str(f))
    assert cli is not None and "in uso la versione 0.1.0" in note[-1]
    assert (tmp / "dati" / "versioni" / zip_.name).exists()


def test_impronta_diversa_rifiutata(ambiente):
    tmp, res, zip_, sha = ambiente
    (res / "pacchetti" / zip_.name).write_bytes(zip_.read_bytes() + b"x")      # manomesso
    f = tmp / "elenco.json"
    f.write_text(json.dumps(elenco(voce("0.1.0", zip_.name, sha))))
    cli, note = AV.prepara(aggiorna=False, file_elenco=str(f))
    assert cli is None and "non disponibile" in " ".join(note)
    # una copia locale manomessa si cancella
    d = tmp / "dati" / "versioni" / zip_.name
    d.write_bytes(b"manomesso")
    assert AV.procura(voce("0.1.0", zip_.name, sha), tmp / "dati", aggiorna=False) is None
    assert not d.exists()


def test_revocata_non_si_usa(ambiente):
    tmp, res, zip_, sha = ambiente
    (res / "pacchetti" / zip_.name).write_bytes(zip_.read_bytes())
    f = tmp / "elenco.json"
    f.write_text(json.dumps(elenco(voce("0.1.0", zip_.name, sha), revocate=[sha])))
    cli, _ = AV.prepara(aggiorna=False, file_elenco=str(f))
    assert cli is None


def test_ritorno_alla_precedente(ambiente):
    tmp, res, zip_, sha = ambiente
    (res / "pacchetti" / zip_.name).write_bytes(zip_.read_bytes())
    sha2 = guasta(zip_, res / "pacchetti" / "visure-0.2.0.zip", "0.2.0")
    f = tmp / "elenco.json"
    f.write_text(json.dumps(elenco(voce("0.1.0", zip_.name, sha), voce("0.2.0", "visure-0.2.0.zip", sha2))))
    cli, note = AV.prepara(aggiorna=False, file_elenco=str(f))
    assert cli is not None
    testo = " ".join(note)
    assert "0.2.0" in testo and "guasto di prova" in testo and "in uso la versione 0.1.0" in testo
    stato = json.loads((tmp / "dati" / "stato.json").read_text())
    assert sha2 in stato["fallite"] and stato["ultima"] == sha
    # al giro dopo la 0.2.0 non si riprova
    cli, note = AV.prepara(aggiorna=False, file_elenco=str(f))
    assert not any("0.2.0" in n for n in note)


def test_scaricamento_con_impronta(ambiente, monkeypatch):
    tmp, res, zip_, sha = ambiente
    dati = zip_.read_bytes()
    monkeypatch.setattr(AV, "scarica", lambda url, massimo, timeout=15: dati)
    p = AV.procura(voce("0.1.0", zip_.name, sha), tmp / "dati", aggiorna=True)
    assert p and AV.sha256(p) == sha
    p.unlink()
    monkeypatch.setattr(AV, "scarica", lambda url, massimo, timeout=15: dati + b"!")
    assert AV.procura(voce("0.1.0", zip_.name, sha), tmp / "dati", aggiorna=True) is None


def test_versione_minima_dell_avviatore(ambiente):
    tmp, res, zip_, sha = ambiente
    e = elenco(voce("0.1.0", zip_.name, sha, minimo_avviatore="9.0.0"))
    assert AV.candidate(e, set()) == []


@pytest.mark.parametrize("url,ok", [
    ("https://raw.githubusercontent.com/statocritico/eugenio/main/x.json", True),
    ("https://github.com/statocritico/eugenio/releases/download/visure-v0.1.0/visure-0.1.0.zip", True),
    ("http://github.com/x", False), ("https://github.com.attaccante.example/x", False), ("file:///etc/passwd", False),
])
def test_host_ammessi(url, ok):
    assert AV.host_ammesso(url) is ok


def test_elenchi_non_validi():
    for e in ({}, {"formato": 2, "programma": "eugenio-visure"},
              elenco({"versione": "1", "file": "../x.zip", "sha256": "0" * 64})):
        with pytest.raises(ValueError):
            AV.valida_elenco(e)
