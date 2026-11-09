"""Estrazioni DBTR raggruppate divise per comune (09/11/2026): COD_COM, o confine ISTAT per gli edifici senza codice."""
import numpy as np
import pytest

pyogrio = pytest.importorskip("pyogrio")
from pyproj import Transformer
from shapely import box, to_wkb

from edifici3d import dividi as DV
from edifici3d import uvl as U

CRS = "EPSG:7791"


def _gpkg(percorso, edifici):
    """edifici: [(ID_E, COD_COM, lon, lat)] → GeoPackage con i quattro strati del DBTR (un corpo per edificio)."""
    import pyogrio.raw as R
    tr = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
    sag = []
    for _, _, lon, lat in edifici:
        x, y = tr.transform(lon, lat)
        sag.append(to_wkb(box(x - 5, y - 5, x + 5, y + 5)))
    geo = np.array(sag, dtype=object)
    ide = np.array([e[0] for e in edifici], dtype=object)
    cod = np.array([e[1] for e in edifici], dtype=object)
    kw = {"driver": "GPKG", "geometry_type": "Polygon", "crs": CRS}
    R.write(str(percorso), geo, [ide, cod, np.array(["1"] * len(edifici), dtype=object)], ["ID_E", "COD_COM", "FOGLIO"],
            layer="V_EDI_GPG", **kw)
    R.write(str(percorso), geo, [np.array([f"u{e[0]}" for e in edifici], dtype=object), ide,
                                 np.array([9.0] * len(edifici)), np.array([40.0] * len(edifici))],
            ["ID_E", "EDI_ID_E", "H_UVL", "B_UVL"], layer="V_UVL_GPG", append=True, **kw)
    R.write(str(percorso), geo, [ide], ["ID_E"], layer="V_EDI_GPGSA", append=True, **kw)
    R.write(str(percorso), None, [ide, np.array([101] * len(edifici), dtype=np.int32)], ["ID_E", "CT_USO"],
            layer="V_EDI_CT_USO_AVM", driver="GPKG", append=True)


def test_dividi_per_codice_e_confine(tmp_path):
    src = tmp_path / "354187" / "estraz_procons.gpkg"
    src.parent.mkdir()
    _gpkg(src, [("e1", "A944", 11.3426, 44.4949),     # Bologna, codice di Bologna
                ("e2", None, 11.3440, 44.4955),       # Bologna, senza codice: confine ISTAT
                ("e3", None, 11.3600, 44.5800),       # Castel Maggiore, senza codice
                ("e4", "C204", 11.3430, 44.4952)])    # codice di Castel Maggiore: vale il codice, non il punto
    _, codici = DV.edifici([src])
    assert codici["A944"][:2] == ("037006", "Bologna")
    esito = DV.dividi([src], ["A944"], ["037006"], tmp_path / "divisi")
    assert esito == {"354187": {"V_UVL_GPG": 2, "V_EDI_GPG": 2, "V_EDI_GPGSA": 2, "V_EDI_CT_USO_AVM": 2}}
    out = tmp_path / "divisi" / "354187" / "estraz_procons.gpkg"
    assert sorted(str(r[0]["EDI_ID_E"]) for r in U.leggi_gpkg(out)) == ["e1", "e2"]
    assert sorted(U.leggi_edifici(out)) == ["e1", "e2"]
    assert U.leggi_edifici(out)["e1"]["CT_USO"] == 101
    # nessun corpo del comune: nessun file
    assert DV.dividi([src], ["G570"], ["037047"], tmp_path / "pianoro") == {}
    assert not (tmp_path / "pianoro" / "354187").exists()
