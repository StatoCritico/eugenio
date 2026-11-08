"""«Aggiungi DBTR» (07/11/2026): parità tra il lettore del sito (fase5-sito/sito/dbtr_lettore.js, in node) e il Python
(uvl.py, regionali.py, tessere.feature_da_corpi) su DB topografici sintetici (tests/dbtr_sintetici.py): GeoPackage e
Shapefile del DBTR ER (convenzione «quote» e «altezze», cortile, colmo, corpi scartati), DBGT Lombardia con le z, CTRN FVG
con i nomi troncati del DBF. Stessi corpi, stesse proprietà, stesse coordinate WGS84 (entro 2·10⁻⁷ gradi, ~2 cm).

Con DBTR_VERI=<cartella> (predefinita /home/claude/dbtr2, mai nel repository) anche sulle estrazioni vere di Lugo
(GeoPackage) e Faenza (Shapefile): lì le geometrie non valide che il Python ripara con make_valid danno pochi corpi
diversi (prova del 07/11/2026: Lugo 1 su 19.906, Faenza 3 su 29.630, Rimini 6 su 40.518; tetto del test 0,1 %)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent)); sys.path.insert(0, str(QUI))
pytest.importorskip("pyogrio")
import dbtr_sintetici as DS  # noqa: E402
from edifici3d import regionali as RG, tessere as T, uvl as U  # noqa: E402
from edifici3d.__main__ import _corpi_uvl  # noqa: E402

SITO = QUI.parents[1] / "fase5-sito" / "sito"
VERI = Path(os.environ.get("DBTR_VERI", "/home/claude/dbtr2"))
pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="node non disponibile")


def js(regione, tmp_path, *ingressi):
    out = tmp_path / f"js_{regione}.json"
    subprocess.run(["node", str(QUI / "dbtr_node.js"), str(SITO), regione, str(out), *map(str, ingressi)], check=True, timeout=600)
    return json.loads(out.read_text(encoding="utf-8"))


def py_er(percorso):
    righe = U.leggi_gpkg(percorso)
    return T.feature_da_corpi(_corpi_uvl(righe, None, U.leggi_edifici(percorso)), "EPSG:7791")


def py_regione(percorso, chiave, crs_zona):
    righe, crs = RG.leggi_file(percorso)
    corpi, res = RG.corpi(righe, chiave, crs_zona, crs)
    return T.feature_da_corpi(corpi, crs_zona), res


def _anello(r):
    return sorted((round(x, 6), round(y, 6)) for x, y in r[:-1])


def confronta(fp, fj, tolleranza_corpi=0):
    """Confronto corpo per corpo; restituisce il numero di corpi diversi (sagoma o proprietà)."""
    a = {f["properties"]["id"]: f for f in fp}
    b = {f["properties"]["id"]: f for f in fj}
    diversi = len(set(a) ^ set(b))
    for k in set(a) & set(b):
        pa, pb = a[k]["properties"], b[k]["properties"]
        ok = set(pa) == set(pb)
        for c in pa:
            if not ok:
                break
            va, vb = pa[c], pb.get(c)
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                ok = abs(va - vb) <= (0.06 if c == "area" else 0.011)
            else:
                ok = va == vb
        ga, gb = a[k]["geometry"]["coordinates"], b[k]["geometry"]["coordinates"]
        if ok and len(ga) == len(gb):
            for ra, rb in zip(sorted(ga, key=len), sorted(gb, key=len)):
                sa, sb = _anello(ra), _anello(rb)
                if len(sa) != len(sb) or any(abs(p[0] - q[0]) > 2.1e-6 or abs(p[1] - q[1]) > 2.1e-6 for p, q in zip(sa, sb)):
                    ok = False
                    break
        else:
            ok = False
        if not ok:
            diversi += 1
            if tolleranza_corpi == 0:
                pytest.fail(f"corpo {k} diverso:\nPY {pa}\nJS {pb}\nPY {ga}\nJS {gb}")
    return diversi


@pytest.mark.parametrize("formato", ["gpkg", "shp"])
@pytest.mark.parametrize("conv", ["quote", "altezze"])
def test_parita_dbtr_er(tmp_path, formato, conv):
    p = DS.gpkg_er(tmp_path / "er.gpkg", conv) if formato == "gpkg" else DS.shp_er(tmp_path / "er_shp", conv)
    fp = py_er(p)
    r = js("er", tmp_path, p)
    assert "errore" not in r, r
    assert confronta(fp, r["features"]) == 0
    s = r["sintesi"]
    assert s["convenzione"] == conv == U.convenzione(x for x, _ in U.leggi_gpkg(p))
    ctl = U.controlla([x for x, _ in U.leggi_gpkg(p)])
    for k in ("corpi", "edifici", "tipi_altezza", "colmi"):
        assert s["controllo"][k] == ctl[k], k
    assert s["controllo"]["gronda"] == pytest.approx(ctl["gronda"])
    ids = {f["properties"]["id"] for f in r["features"]}
    assert "U4" not in ids and "U6" not in ids                                           # H ≤ 0, < 1 m²
    assert ("U5" in ids) == (conv == "altezze")               # H_UVL ≈ B_UVL: quota senza altezza solo con le «quote»
    u2 = next(f for f in r["features"] if f["properties"]["id"] == "U2")
    assert len(u2["geometry"]["coordinates"]) == 2 and u2["properties"]["colmo"] == 14.5  # cortile e colmo − base
    u1 = next(f for f in r["features"] if f["properties"]["id"] == "U1")["properties"]
    assert (u1["foglio"], u1["numero"], u1["nome"]) == ("74", "1100", "Palazzo di prova") and "destinazione" in u1
    if conv == "altezze":
        assert next(f for f in r["features"] if f["properties"]["id"] == "A9")["properties"]["gronda"] == 44.5   # campanile
    else:
        assert next(f for f in r["features"] if f["properties"]["id"] == "U3")["properties"]["gronda"] == 12.15  # quota del tetto
    assert s["terreno"].startswith("quote dei corpi dalla base") and "dal server" in s["terreno"] and s["licenza"] == "CC BY 4.0"


def test_parita_lombardia_e_fvg(tmp_path):
    lom = DS.shp_lombardia(tmp_path / "lom")
    fp, res = py_regione(lom / "UN_VOL.shp", "lombardia_dbgt", "EPSG:7791")
    r = js("lom", tmp_path, lom)
    assert "errore" not in r, r
    assert confronta(fp, r["features"]) == 0 and len(fp) == 2
    assert next(f for f in r["features"] if f["properties"]["id"] == "L2")["properties"]["quota_terreno"] == 120   # base 03
    fvg = DS.shp_fvg(tmp_path / "fvg")
    fp, res = py_regione(fvg / "EDIFICATO.shp", "fvg_ctrn", "EPSG:6708")
    r = js("fvg", tmp_path, fvg)
    assert "errore" not in r, r
    assert confronta(fp, r["features"]) == 0 and len(fp) == 2                # QUOTA_GRON/QUOTA_PIED riconosciute
    assert r["sintesi"]["controllo"]["scarti"] == {"altezza assente o non valida, o elemento escluso": 1} == res["scarti"]


def test_zip_annidato_e_rifiuti(tmp_path):
    import zipfile
    p = DS.gpkg_er(tmp_path / "estraz_procons.gpkg")
    interno = tmp_path / "interno.zip"
    with zipfile.ZipFile(interno, "w") as z:
        z.write(p, "dati/estraz_procons.gpkg")
        z.writestr("dati/leggimi.exe", b"MZ")
    esterno = tmp_path / "pacchetto.zip"
    with zipfile.ZipFile(esterno, "w") as z:
        z.write(interno, "interno.zip")
    r = js("er", tmp_path, esterno)
    assert "errore" not in r and len(r["features"]) == 5
    cattivo = tmp_path / "cattivo.zip"
    with zipfile.ZipFile(cattivo, "w") as z:
        z.writestr("../../fuori.gpkg", b"x")
    assert "percorso non ammesso" in js("er", tmp_path, cattivo)["errore"]
    assert "V_UVL_GPG" in js("er", tmp_path, DS.shp_fvg(tmp_path / "fvg"))["errore"]   # regione sbagliata: niente UVL
    sbagliato = DS.shp_er(tmp_path / "er_senza_prj")
    (sbagliato / "V_UVL_GPG.prj").unlink()
    assert ".prj" in js("er", tmp_path, sbagliato)["errore"]
    assert "DTM" in js("lig", tmp_path, DS.shp_fvg(tmp_path / "fvg2"))["errore"]       # Liguria: serve il DTM


@pytest.mark.skipif(not (VERI / "lugo_2026-11-06" / "estraz_procons.gpkg").exists(), reason="estrazione vera di Lugo assente")
def test_parita_estrazione_vera_lugo(tmp_path):
    p = VERI / "lugo_2026-11-06" / "estraz_procons.gpkg"
    fp = py_er(p)
    r = js("er", tmp_path, p)
    assert "errore" not in r, r
    d = confronta(fp, r["features"], tolleranza_corpi=1)
    assert d <= max(10, 0.001 * len(fp)), f"{d} corpi diversi su {len(fp)}"
    assert len(r["features"]) == pytest.approx(len(fp), rel=0.001)


@pytest.mark.skipif(not (VERI / "faenza_2026-11-06" / "V_UVL_GPG.shp").exists(), reason="estrazione vera di Faenza assente")
def test_parita_estrazione_vera_faenza_shapefile(tmp_path):
    p = VERI / "faenza_2026-11-06"
    fp = py_er(p)
    r = js("er", tmp_path, p)
    assert "errore" not in r, r
    assert r["sintesi"]["convenzione"] == "altezze"
    d = confronta(fp, r["features"], tolleranza_corpi=1)
    assert d <= max(10, 0.001 * len(fp)), f"{d} corpi diversi su {len(fp)}"
