"""Corpi dal solo LiDAR (raggruppamento per altezza, § 7) e alberi dal DSM sul campione sintetico (05/11/2026)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent))

from edifici3d import campione as K, lidar as L, lidar_corpi as LC, pipeline as PL, sintetico as S  # noqa: E402
from edifici3d.__main__ import _campione, main  # noqa: E402


@pytest.fixture(scope="module")
def radice(tmp_path_factory):
    r = tmp_path_factory.mktemp("campione")
    _campione(r)
    return r


@pytest.fixture(scope="module")
def griglie(radice):
    riq = (S.X0 - 50, S.Y0 - 50, S.X0 + 150, S.Y0 + 100)
    gs, ts = [], []
    for nome, x0, y0, x1, y1, ij in K.tessere():
        p = radice / "dsm" / f"{nome}.tif"
        if p.exists():
            gs.append(L.ricampiona(L.leggi_raster(p), (x0, y0, x1, y1)))
            ts.append(L.ricampiona(L.leggi_raster(radice / "dtm" / f"{nome}.tif"), (x0, y0, x1, y1)))
        else:
            a, b = L.griglie_da_las(L.leggi_las(radice / "las" / f"{nome}.las"), (x0, y0, x1, y1))
            gs.append(a); ts.append(b)
    return L.unisci(gs, riq), L.unisci(ts, riq)


def _iou(a, b):
    return a.intersection(b).area / a.union(b).area


def test_corpi_dal_solo_lidar(griglie):
    dsm, dtm = griglie
    corpi = LC.corpi_da_lidar(dsm, dtm, "T", "CC BY 4.0", "LiDAR di prova")
    uvl = {p["Id_e"]: (g, p) for p, g in S.uvl()}
    trovati = {}
    for c in corpi:
        k, (g, p) = max(uvl.items(), key=lambda kv: kv[1][0].intersection(c.sagoma).area)
        trovati.setdefault(k, []).append((c, _iou(g, c.sagoma)))
    # corpi isolati o di altezza diversa dai vicini: ritrovati con la loro sagoma e l'altezza giusta (±1,5 m)
    for k in ("C3", "C6", "C7", "C9"):
        c, iou = trovati[k][0]
        assert iou > 0.9, (k, iou)
        assert abs(c.gronda - float(str(uvl[k][1]["H_uvl"]).replace(",", "."))) < 3.5, k       # mediana del tetto: tra gronda e colmo
    assert "C10" not in trovati                                     # demolito: non c'è nel rilievo
    assert all(c.area >= LC.AREA_MIN for c in corpi) and all(c.licenza == "CC BY 4.0" for c in corpi)
    # la torre C3 (22 m) è un corpo separato da C1 e C2 (10 m) ma nello stesso edificio
    c3 = trovati["C3"][0][0]
    c1 = trovati["C1"][0][0]
    assert c3.id != c1.id and c3.edificio == c1.edificio
    # nessun corpo sugli alberi del campione
    from shapely.geometry import Point
    for ax, ay, r, h in K.ALBERI:
        assert not any(c.sagoma.contains(Point(S.X0 + ax, S.Y0 + ay)) for c in corpi)


def test_alberi_dal_dsm(griglie):
    dsm, dtm = griglie
    corpi = LC.corpi_da_lidar(dsm, dtm, "T", "CC BY 4.0", "LiDAR di prova")
    al = LC.alberi(dsm, dtm, [c.sagoma for c in corpi])
    assert al
    for ax, ay, r, h in K.ALBERI:
        vicini = [a for a in al if np.hypot(a[0] - (S.X0 + ax), a[1] - (S.Y0 + ay)) < r]
        assert vicini, (ax, ay)
        assert max(a[2] for a in vicini) == pytest.approx(h, abs=1.0)
    # nessun albero sopra le sagome
    from shapely.geometry import Point
    assert not any(c.sagoma.contains(Point(a[0], a[1])) for c in corpi for a in al)
    w = LC.alberi_in_wgs84(al[:3], S.CRS)
    assert 12.5 < w[0][0] < 12.7 and 44.0 < w[0][1] < 44.1 and w[0][4] == LC.PASSO_ALBERI


def test_pipeline_scrive_gli_alberi(radice, tmp_path):
    z = PL.carica_zona("campione")
    e = PL.Pipeline(z, tmp_path / "a", tmp_path / "s", radice=radice).esegui(subito=True)
    assert e["tessere_fatte"] > 0
    celle = list((tmp_path / "a" / "sintetico" / "campione" / "prodotti" / "lidar" / "alberi").glob("*.json"))
    assert celle
    d = json.loads(celle[0].read_text(encoding="utf-8"))
    assert d["campi"] == ["lon", "lat", "h", "quota", "lato"] and sum(len(v) for v in d["tessere"].values()) > 0


def test_lidar_corpi_per_una_zona_senza_sagome(radice, tmp_path, capsys):
    """Zona senza UVL: i corpi vengono dal LiDAR, poi la pipeline normale stima le falde su quei corpi."""
    z = PL.carica_zona("campione")
    z["edifici"] = {"licenza": "dati sintetici"}                    # nessuna cella di contesto già pronta
    pl = PL.Pipeline(z, tmp_path / "a", tmp_path / "s", radice=radice)
    r = pl.corpi_lidar(riquadro=(S.X0 - 50, S.Y0 - 50, S.X0 + 150, S.Y0 + 100))
    assert r["corpi"] >= 6 and r["edifici"] >= 4 and r["tessere"]
    prod = Path(r["prodotti"])
    assert (prod / "corpi.pmtiles").exists() and list((prod / "contesto").glob("*.json"))
    ind = json.loads((prod / "indice.json").read_text(encoding="utf-8"))
    assert ind["fonte_edifici"]["metodo"].startswith("corpi dal solo LiDAR")
    e = PL.Pipeline(z, tmp_path / "a", tmp_path / "s2", radice=radice).esegui(subito=True)
    assert e["tessere_fatte"] > 0 and e["corpi"] >= 6
    with pytest.raises(ValueError, match="nessuna tessera"):
        pl.corpi_lidar(tessere=["inesistente"])
