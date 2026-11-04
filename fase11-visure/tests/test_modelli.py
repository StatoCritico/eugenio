"""Conversione dei modelli DXF/IFC in EuGEnio Visure (04/11/2026): comando `modello`, controllo di avvio `prova
--modelli`, scheda «Modelli DXF/IFC» della pagina locale, pacchetto approvato che contiene edifici3d/importa.py.
Stesso codice di `python -m edifici3d importa-modello` (fase 10): qui si controlla che arrivi intero all'avviatore."""
import json
import sys
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("ezdxf"); pytest.importorskip("ifcopenshell"); pytest.importorskip("shapely")

import costruisci_pacchetto as CP  # noqa: E402
from visure.__main__ import principale  # noqa: E402
from visure import modelli as MO  # noqa: E402
from test_web import chiedi, multipart, server  # noqa: E402,F401

FASE10 = Path(__file__).resolve().parents[2] / "fase10-edifici3d"


@pytest.fixture(scope="module")
def file_prova(tmp_path_factory):
    sys.path.insert(0, str(FASE10 / "tests"))
    import modelli_sintetici as MS
    return MS.genera(tmp_path_factory.mktemp("modelli"))


def test_prova_dei_modelli():
    ok, msg = MO.prova()
    assert ok, msg
    assert principale(["prova", "--modelli"]) == 0


def test_comando_modello(file_prova, tmp_path, capsys):
    p, _ = file_prova["casa_sito.ifc"]
    out = tmp_path / "m.geojson"
    assert principale(["modello", str(p), "--uscita", str(out)]) == 0
    g = json.loads(out.read_text(encoding="utf-8"))
    assert g["formato"] == "eugenio-modello-1" and len(g["features"]) == 2
    p, _ = file_prova["casa_mm.dxf"]
    assert principale(["modello", str(p), "--uscita", str(out), "--posa", "0,0=12.57,44.061", "12000,0=12.57015,44.061"]) == 0
    assert not json.loads(out.read_text(encoding="utf-8"))["avvisi"]
    p, _ = file_prova["casa_metri.dxf"]
    assert principale(["modello", str(p), "--uscita", str(out)]) == 1          # manca la posa: messaggio, non eccezione
    assert "posa" in capsys.readouterr().err


def test_pagina_locale_dei_modelli(server, file_prova):  # noqa: F811
    porta, st = server
    s, _, pag = chiedi(porta, "GET", "/modelli")
    assert s == 200 and b"Converti un modello DXF o IFC" in pag and st.gettone.encode() in pag
    p, _ = file_prova["casa_utm.dxf"]
    corpo, tipo = multipart([("gettone", None, st.gettone.encode()), ("file", "casa_utm.dxf", p.read_bytes()),
                             ("crs", None, b"EPSG:7791")])
    s, h, g = chiedi(porta, "POST", "/modello", corpo, {"Content-Type": tipo})
    assert s == 200 and h["Content-Type"] == "application/geo+json" and "casa_utm.geojson" in h["Content-Disposition"]
    assert len(json.loads(g)["features"]) == 2
    corpo, tipo = multipart([("gettone", None, st.gettone.encode()), ("file", "casa_utm.dxf", p.read_bytes())])
    s, _, pag = chiedi(porta, "POST", "/modello", corpo, {"Content-Type": tipo})
    assert s == 422 and "posa".encode() in pag                                  # senza posa: pagina con il motivo
    corpo, tipo = multipart([("gettone", None, b"sbagliato"), ("file", "casa_utm.dxf", p.read_bytes())])
    assert chiedi(porta, "POST", "/modello", corpo, {"Content-Type": tipo})[0] == 403


def test_pacchetto_contiene_il_convertitore(tmp_path):
    z, _ = CP.costruisci(tmp_path)
    nomi = zipfile.ZipFile(z).namelist()
    assert "edifici3d/importa.py" in nomi and "edifici3d/__init__.py" in nomi and "visure/modelli.py" in nomi
    assert not any("tests" in n or "uni_privato" in n for n in nomi)
    assert zipfile.ZipFile(z).read("edifici3d/importa.py") == (FASE10 / "edifici3d" / "importa.py").read_bytes().replace(b"\r\n", b"\n")
