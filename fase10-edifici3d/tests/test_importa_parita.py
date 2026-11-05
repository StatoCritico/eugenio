"""Import DXF/IFC: correzioni del 04/11/2026 al comando Python e parità con la lettura nel browser.

- posa scritta nelle unità del disegno (DXF in millimetri), IfcMapConversion con il progetto in millimetri, orientamento
  delle falde riferito al nord vero (rotazione della posa, nord di IfcSite, convergenza del reticolo UTM);
- limiti per i file grandi (--grande) e processo figlio anche con «spawn» (come su Windows e nell'.exe);
- parità Python ↔ JavaScript sui DXF con node e le stesse librerie del sito (sito/lib); la parità sugli IFC (web-ifc è
  WebAssembly per il browser) è in test_importa_browser.py, con Chromium.
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent)); sys.path.insert(0, str(QUI))
pytest.importorskip("ezdxf"); pytest.importorskip("ifcopenshell")

import modelli_sintetici as MS  # noqa: E402
from edifici3d import importa as I  # noqa: E402

SITO = QUI.parents[1] / "fase5-sito" / "sito"


@pytest.fixture(scope="module")
def modelli(tmp_path_factory):
    d = tmp_path_factory.mktemp("modelli")
    return MS.genera(d)


@pytest.fixture(scope="module")
def risultati_py(modelli):
    return {n: I.importa_sicuro(p, posa=posa) for n, (p, posa) in modelli.items()}


def _props(r):
    return [f["properties"] for f in r["features"]]


def test_tutti_i_tipi_di_entita_dxf(risultati_py):
    p = _props(risultati_py["casa_metri.dxf"])
    tetti = sorted(x["tetto"] for x in p)
    assert tetti == ["capanna", "monofalda", "padiglione", "piano", "piano", "piano"]     # 3DFACE, blocco, POLYFACE, MESH, 2 prismi
    pad = next(x for x in p if x["tetto"] == "padiglione")
    assert sorted(round(f["orientamento"]) for f in pad["falde"]) == [60, 150, 240, 330]  # blocco ruotato di 30°
    assert any("3DSOLID" in a for a in risultati_py["casa_metri.dxf"]["avvisi"])


def test_posa_nelle_unita_del_disegno(risultati_py):
    r = risultati_py["casa_mm.dxf"]
    assert not any("scala" in a for a in r["avvisi"])      # 12000 mm = 12 m tra i due punti: scala 1
    (c,) = _props(r)
    assert c["gronda"] == pytest.approx(6.5) and c["colmo"] == pytest.approx(9.5) and c["area"] == pytest.approx(108, rel=0.01)
    lon, lat = r["features"][0]["geometry"]["coordinates"][0][0]
    assert abs(lat - 44.061) < 0.0002 and abs(lon - 12.57) < 0.0003


def test_ifc_millimetri_e_nord_vero(risultati_py):
    r = risultati_py["casa_mappa_mm.ifc"]
    assert r["posa"]["origine"] == "IfcMapConversion" and r["posa"]["scala"] == pytest.approx(1.0)
    casa = next(x for x in _props(r) if x["tetto"] == "capanna")
    assert casa["area"] == pytest.approx(120, rel=0.01) and casa["gronda"] == pytest.approx(7)
    # asse x del progetto ruotato di 20° in senso antiorario sul reticolo, convergenza ~2,5° a Rimini
    assert sorted(round(f["orientamento"]) for f in casa["falde"]) == [162, 342] or sorted(round(f["orientamento"]) for f in casa["falde"]) == [163, 343]
    s = next(x for x in _props(risultati_py["casa_sito.ifc"]) if x["tetto"] == "capanna")
    assert sorted(round(f["orientamento"]) for f in s["falde"]) == [15, 195]          # TrueNorth a 15°
    u = next(x for x in _props(risultati_py["casa_utm.dxf"]) if x["tetto"] == "capanna")
    assert sorted(round(f["orientamento"], 1) for f in u["falde"]) == [2.5, 182.5]     # reticolo UTM 32 a Rimini


def test_ifc_esclude_arredi_e_spazi(risultati_py):
    for n in ("casa_sito.ifc", "casa_mappa_mm.ifc"):
        assert sorted(x["tetto"] for x in _props(risultati_py[n])) == ["capanna", "piano"]   # né l'arredo né lo spazio


def test_limiti_grandi_e_spawn(modelli, monkeypatch):
    assert I.limiti(True)["MAX_MB"] == 500 and I.limiti(False)["MAX_MB"] == 50
    monkeypatch.setattr(I, "MAX_MB", 0.0001)
    p, posa = modelli["casa_utm.dxf"]
    with pytest.raises(I.ModelloNonValido, match="--grande"):
        I.importa_sicuro(p, posa=posa)
    assert I.importa_sicuro(p, posa=posa, grande=True)["features"]
    monkeypatch.setattr(I, "MAX_MB", 50)
    monkeypatch.setenv("EUGENIO_MP", "spawn")
    assert I.contesto_processi().get_start_method() == "spawn"
    assert len(I.importa_sicuro(p, posa=posa)["features"]) == 2


@pytest.mark.skipif(not shutil.which("node"), reason="node non disponibile")
def test_parita_dxf_con_node(modelli, risultati_py, tmp_path):
    """Stessi DXF letti da modelli_import.js con dxf-parser, Clipper e proj4js del sito: stesso GeoJSON."""
    script = tmp_path / "parita.js"
    script.write_text(r"""
const fs = require('fs');
const S = process.argv[2], casi = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const M = require(S + '/modelli_import.js');
const lib = { DxfParser: require(S + '/lib/dxf-parser/dxf-parser.js'), ClipperLib: require(S + '/lib/clipper-lib/clipper.js'),
  proj4: require(S + '/lib/proj4/proj4.js') };
const out = {};
console.log = () => {};                     // dxf-parser scrive avvisi sui codici di gruppo sconosciuti
for (const [nome, [p, posa]] of Object.entries(casi)) {
  const buf = fs.readFileSync(p);
  const tipo = M.controllaFile(nome, buf.length, new Uint8Array(buf.subarray(0, 256)));
  const r = M.leggiDxf(buf.toString('utf8'), lib);
  out[nome] = M.geojson(r, M.inMetri(posa, r.unita_m) || r.georef, tipo, nome, 'x', lib.proj4);
}
process.stdout.write(JSON.stringify(out));
""", encoding="utf-8")
    casi = {n: [str(p), posa] for n, (p, posa) in modelli.items() if n.endswith(".dxf")}
    (tmp_path / "casi.json").write_text(json.dumps(casi), encoding="utf-8")
    js = json.loads(subprocess.run(["node", str(script), str(SITO), str(tmp_path / "casi.json")], capture_output=True,
                                   text=True, encoding="utf-8", check=True).stdout)
    for n in casi:
        assert MS.confronta(risultati_py[n], js[n]) == [], n


@pytest.mark.skipif(not shutil.which("node"), reason="node non disponibile")
def test_controlli_js_come_python(tmp_path):
    """Gli stessi file non fidati vengono rifiutati anche dal modulo del browser, con lo stesso motivo."""
    casi = {"x.ifc": b"<?xml version='1.0'?><ifcXML/>", "x.ifczip": b"PK\x03\x04", "x.dxf": b"ciao",
            "b.dxf": b"AutoCAD Binary DXF\r\n\x1a\x00"}
    js = subprocess.run(["node", "-e", f"""
const M = require({json.dumps(str(SITO / 'modelli_import.js'))});
const casi = {json.dumps({k: list(v) for k, v in casi.items()})};
const out = {{}};
for (const [n, b] of Object.entries(casi)) {{ try {{ M.controllaFile(n, b.length, new Uint8Array(b)); out[n] = 'ok'; }} catch (e) {{ out[n] = e.message; }} }}
try {{ M.controllaFile('g.ifc', 51 * 1024 * 1024, new TextEncoder().encode('ISO-10303-21;')); out.g = 'ok'; }} catch (e) {{ out.g = e.message; }}
out.pulisci = M.pulisci('Sito <script>\\x00alert(1)');
process.stdout.write(JSON.stringify(out));"""], capture_output=True, text=True, encoding="utf-8", check=True).stdout
    r = json.loads(js)
    assert "STEP" in r["x.ifc"] and "formato" in r["x.ifczip"] and "DXF" in r["x.dxf"] and "binario" in r["b.dxf"]
    assert "50 MB" in r["g"] and "PC" in r["g"]
    assert r["pulisci"] == I.pulisci("Sito <script>\x00alert(1)")
