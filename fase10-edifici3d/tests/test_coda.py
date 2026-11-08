"""Coda «Aggiungi DBTR» (07/11/2026): estrazione sicura, controlli, preparazione, installazione dopo l'approvazione con la
copia precedente, archivi.json, ritorno all'archivio precedente, pulizia. Dati sintetici (dbtr_sintetici.py), niente rete."""
from __future__ import annotations

import json
import os
import stat
import sys
import time
import zipfile
from pathlib import Path

import pytest

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent)); sys.path.insert(0, str(QUI))
pytest.importorskip("pyogrio")
import dbtr_sintetici as DS  # noqa: E402
from edifici3d import archivi as A, coda as K  # noqa: E402


def _richiesta(coda: Path, rid: str, regione: str, comune: str, sorgente: Path, istat=None, intero=True, extra=None):
    d = coda / rid
    d.mkdir(parents=True)
    with zipfile.ZipFile(d / "caricato.bin", "w") as z:
        if sorgente.is_dir():
            for f in sorted(sorgente.iterdir()):
                z.write(f, f"estrazione/{f.name}")
        else:
            z.write(sorgente, "estrazione/estraz_procons.gpkg")
        z.writestr("estrazione/metadati.xml", "<md>Regione Emilia-Romagna – Creative Commons CC BY 4.0</md>")
        for n, b in (extra or {}).items():
            z.writestr(n, b)
    K.scrivi_richiesta(coda, {"id": rid, "stato": "ricevuto", "creata": K.adesso(), "t": time.time(), "regione": regione,
                              "comune": comune, "comune_slug": K.slug(comune), "istat": istat, "intero": intero, "formato": "zip",
                              "dimensione": (d / "caricato.bin").stat().st_size})
    return d


def test_nomi_e_zip_malevoli(tmp_path):
    assert K.slug("Montescudo-Monte Colombo") == "montescudo-monte-colombo" and K.slug("Forlì") == "forli"
    assert K.nome_comune("Duino Aurisina/Devin Nabrežina")
    for cattivo in ("../../etc", "a", "Rimini<script>", "/etc"):
        with pytest.raises(K.FileNonValido):
            K.nome_comune(cattivo)
    def z(nome, voci):
        p = tmp_path / nome
        with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as f:
            for n, b, *attr in voci:
                i = zipfile.ZipInfo(n); i.compress_type = zipfile.ZIP_DEFLATED
                if attr:
                    i.external_attr = attr[0]
                f.writestr(i, b)
        return p
    with pytest.raises(K.FileNonValido, match="percorso"):
        K.controlla_file(z("a.zip", [("../x.shp", b"1")]))
    with pytest.raises(K.FileNonValido, match="simbolico"):
        K.controlla_file(z("b.zip", [("x.shp", b"/etc/passwd", (stat.S_IFLNK | 0o777) << 16)]))
    with pytest.raises(K.FileNonValido, match="compressione"):
        K.controlla_file(z("c.zip", [("x.gpkg", bytes(60 * 1024 * 1024))]))
    with pytest.raises(K.FileNonValido, match="GeoPackage"):
        K.controlla_file(z("d.zip", [("x.exe", b"MZ")]))
    # estrazione: solo i file attesi, niente fuori dalla cartella
    ok = z("e.zip", [("dati/V_UVL_GPG.shp", b"x"), ("dati/leggimi.exe", b"MZ"), ("dati/m.xml", b"<x/>")])
    e = K.estrai_sicuro(ok, tmp_path / "estratto")
    assert sorted(e["file"]) == ["dati/V_UVL_GPG.shp", "dati/m.xml"] and "dati/leggimi.exe" in e["ignorati"]
    assert not (tmp_path / "estratto" / "dati" / "leggimi.exe").exists()


def test_coda_preparazione_installazione_e_ritorno(tmp_path):
    coda, arch = tmp_path / "coda", tmp_path / "archivio"
    s = tmp_path / "s"
    _richiesta(coda, "a" * 32, "er", "Rimini", DS.gpkg_er(s / "er.gpkg") if s.mkdir() is None else None, istat="099014")
    _richiesta(coda, "b" * 32, "fvg", "Udine", DS.shp_fvg(s / "fvg"), istat="030129")
    _richiesta(coda, "c" * 32, "lom", "Milano", DS.shp_er(s / "er_shp"))            # regione sbagliata: niente colonne DBGT
    _richiesta(coda, "d" * 32, "er", "Rimini", DS.gpkg_er(s / "er2.gpkg"), extra={"dati/persone.json": b"{}"})
    giri = [K.un_giro(coda, arch, None, None)["preparato"] for _ in range(5)]
    assert giri[:4] == ["in attesa di approvazione", "in attesa di approvazione", "controlli non superati", "in attesa di approvazione"]
    assert giri[4] is None                                                          # una alla volta, poi niente
    r = K.leggi_richiesta(coda, "a" * 32)
    e = r["esito"]
    assert e["corpi"] == 5 and e["scartati"] == 3 and e["convenzione"] == "quote" and e["percorso"] == "cc-by/er/rimini/"
    assert e["gronda_m"]["max"] == 24.0 and e["con_cortile"] == 1 and e["sostituisce"] is False
    assert r["controlli"]["metadati"]["regione_citata"] and r["controlli"]["dentro_regione"] and not r["controlli"]["dati_personali"]
    ant = json.loads((coda / ("a" * 32) / "anteprima.geojson").read_text())
    assert len(ant["features"]) == 5 and {"g", "c", "e"} <= set(ant["features"][0]["properties"])
    assert not (coda / ("a" * 32) / "lavoro").exists()                              # file estratti cancellati
    assert any("colonne attese mancanti" in p for p in K.leggi_richiesta(coda, "c" * 32)["controlli"]["problemi"])
    assert K.leggi_richiesta(coda, "b" * 32)["esito"]["percorso"] == "cc-by/fvg/udine/"
    # approvazione (la scrive l'api): installazione al giro successivo, archivi.json con l'ISTAT del comune
    for rid in ("a" * 32, "b" * 32):
        r = K.leggi_richiesta(coda, rid); r["stato"] = "approvato"; K.scrivi_richiesta(coda, r)
    g = K.un_giro(coda, arch, None, None)
    assert g["installati"] == ["installato", "installato"]
    aj = json.loads((arch / "archivi.json").read_text())
    basi = {a["base"]: a for a in aj["archivi"]}
    assert basi["/edifici3d/cc-by/er/rimini/prodotti/"]["istat"] == "099014"
    assert basi["/edifici3d/cc-by/fvg/udine/prodotti/"]["istat"] == "030129"
    assert "IRDAT" in basi["/edifici3d/cc-by/fvg/udine/prodotti/"]["attribuzione"]
    assert (arch / "cc-by/er/rimini/LICENZE.txt").exists() and (arch / "cc-by/fvg/udine/LICENZE.txt").exists()
    assert not (coda / ("a" * 32)).exists() and K.leggi_esito(coda, "a" * 32)["stato"] == "installato"
    storico = [json.loads(x) for x in (coda / "storico.jsonl").read_text().splitlines()]
    assert {x["comune"] for x in storico} == {"Rimini", "Udine"} and all("ip" not in x for x in storico)
    # seconda proposta dello stesso comune: sostituisce, la precedente va in _precedenti/ e non entra in archivi.json
    r = K.leggi_richiesta(coda, "d" * 32)
    assert r["esito"]["sostituisce"] is False                                        # preparata prima dell'installazione
    r["stato"] = "approvato"; K.scrivi_richiesta(coda, r)
    K.un_giro(coda, arch, None, None)
    prec = list((arch / "_precedenti").iterdir())
    assert len(prec) == 1 and prec[0].name.startswith("cc-by-er-rimini-")
    aj = json.loads((arch / "archivi.json").read_text())
    assert not any("_precedenti" in a["base"] for a in aj["archivi"]) and len(aj["archivi"]) == 2
    assert (arch / "archivi.json.prima").exists()
    # ritorno all'archivio precedente
    out = K.ripristina(arch, "er", "rimini")
    assert out["ripristinato"] == "cc-by/er/rimini" and out["archivi"] == 2
    assert (arch / "cc-by/er/rimini/prodotti/indice.json").exists()


def test_prepara_regione_per_comune(tmp_path):
    from edifici3d.__main__ import main
    lom = DS.shp_lombardia(tmp_path / "lom")
    assert main(["--zona", "lombardia", "prepara-regione", "--file", str(lom / "UN_VOL.shp"), "--archivio", str(tmp_path / "a"),
                 "--comune", "milano", "--istat", "015146"]) == 0
    ind = json.loads((tmp_path / "a/cc-by/lom/milano/prodotti/indice.json").read_text())
    assert ind["istat"] == "015146" and ind["comune"] == "milano" and ind["corpi"] == 2 and ind["nome"] == "Lombardia – Milano"
    aj = A.scrivi_archivi_json(tmp_path / "a")
    assert aj["archivi"][0]["istat"] == "015146" and "lidar" not in aj


def test_pulizia_finestra_e_coda_ordinata(tmp_path):
    coda = tmp_path / "coda"
    K.scrivi_richiesta(coda, {"id": "e" * 32, "stato": "caricamento", "creata": K.adesso()})
    vecchio = time.time() - 7 * 3600
    os.utime(coda / ("e" * 32), (vecchio, vecchio))
    assert K.pulizia(coda) == 1 and not (coda / ("e" * 32)).exists()
    assert K._fuori_finestra("03:15-07:00", time.struct_time((2026, 11, 7, 4, 0, 0, 5, 311, 0)))
    assert not K._fuori_finestra("03:15-07:00", time.struct_time((2026, 11, 7, 12, 0, 0, 5, 311, 0)))
    assert K._fuori_finestra("23:00-01:00", time.struct_time((2026, 11, 7, 0, 30, 0, 5, 311, 0)))
    s = tmp_path / "s"; s.mkdir()
    _richiesta(coda, "f" * 32, "er", "Lugo", DS.gpkg_er(s / "x.gpkg"))
    assert K.un_giro(coda, tmp_path / "a", None, "00:00-23:59")["attesa"].startswith("finestra")   # nessuna preparazione
    assert K.leggi_richiesta(coda, "f" * 32)["stato"] == "ricevuto"
