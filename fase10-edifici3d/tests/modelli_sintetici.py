"""Modelli DXF e IFC **sintetici** (inventati) per le prove di `importa-modello` e della lettura nel browser.

Gli stessi file vanno al comando Python (ezdxf, IfcOpenShell) e alla pagina «Importa DXF/IFC» (dxf-parser, web-ifc):
i test di parità confrontano i due risultati. `genera(cartella)` restituisce {nome: (percorso, posa)}, dove la posa è
quella da passare a `importa_sicuro` (None se il file è già georeferenziato).

  python tests/modelli_sintetici.py CARTELLA      # scrive i file (anche per provarli a mano nella pagina)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path


def casa(x0, y0, L_, W, g, c):
    """Casa a capanna: 4 pareti, 2 falde (colmo lungo x), 2 timpani, pavimento."""
    A, B, C, D = (x0, y0, 0), (x0 + L_, y0, 0), (x0 + L_, y0 + W, 0), (x0, y0 + W, 0)
    a, b, cc, d = (x0, y0, g), (x0 + L_, y0, g), (x0 + L_, y0 + W, g), (x0, y0 + W, g)
    r1, r2 = (x0, y0 + W / 2, c), (x0 + L_, y0 + W / 2, c)
    return [[A, B, b, a], [B, C, cc, b], [C, D, d, cc], [D, A, a, d], [a, b, r2, r1], [d, cc, r2, r1],
            [a, r1, d, d], [b, r2, cc, cc], [A, B, C, D]]


def padiglione(x0, y0, L_, W, g, c, rientro):
    """Tetto a padiglione (4 falde) con le pareti."""
    A, B, C, D = (x0, y0, 0), (x0 + L_, y0, 0), (x0 + L_, y0 + W, 0), (x0, y0 + W, 0)
    a, b, cc, d = (x0, y0, g), (x0 + L_, y0, g), (x0 + L_, y0 + W, g), (x0, y0 + W, g)
    r1, r2 = (x0 + rientro, y0 + W / 2, c), (x0 + L_ - rientro, y0 + W / 2, c)
    return [[A, B, b, a], [B, C, cc, b], [C, D, d, cc], [D, A, a, d],
            [a, b, r2, r1], [cc, d, r1, r2], [b, cc, r2, r2], [d, a, r1, r1]]


def _dxf_a(p: Path):
    """Metri, non georeferenziato: 3DFACE (capanna), polilinea con spessore, altezza nel layer, blocco ruotato e
    scalato (padiglione), POLYFACE (monofalda), MESH (tetto piano), un 3DSOLID (non leggibile: avviso)."""
    import ezdxf
    doc = ezdxf.new("R2010"); doc.header["$INSUNITS"] = 6
    m = doc.modelspace()
    for f in casa(0, 0, 10, 8, 6, 9):
        m.add_3dface(f)
    m.add_lwpolyline([(20, 0), (32, 0), (32, 12), (20, 12)], close=True, dxfattribs={"thickness": 12.0, "layer": "TORRE"})
    m.add_lwpolyline([(40, 0), (46, 0), (46, 6), (40, 6)], close=True, dxfattribs={"layer": "BOX_H_4.5"})
    blk = doc.blocks.new("PADIGLIONE", base_point=(1, 1, 0))
    for f in padiglione(1, 1, 12, 8, 5, 8, 4):
        blk.add_3dface(f)
    m.add_blockref("PADIGLIONE", (0, 40, 0), dxfattribs={"rotation": 30, "xscale": 1.0, "yscale": 1.0, "zscale": 1.0})
    # monofalda come POLYFACE: falda da 4 m (sud) a 7 m (nord)
    pf = m.add_polyface()
    v = [(60, 0, 0), (70, 0, 0), (70, 9, 0), (60, 9, 0), (60, 0, 4), (70, 0, 4), (70, 9, 7), (60, 9, 7)]
    for q in ([0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7], [4, 5, 6, 7]):
        pf.append_face([v[i] for i in q])
    # tetto piano a 15 m come MESH
    me = m.add_mesh()
    with me.edit_data() as md:
        md.vertices = [(60, 30, 0), (72, 30, 0), (72, 42, 0), (60, 42, 0), (60, 30, 15), (72, 30, 15), (72, 42, 15), (60, 42, 15)]
        md.faces = [[0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7], [4, 5, 6, 7]]
    so = m.add_3dsolid()               # dati ACIS minimi (SAT di testo, si scrive solo fino a R2010)
    so.sat = ["700 0 1 0", "@8 ezdxf 9 ACIS 7.0 @24 Thu Jan 01 00:00:00 2026", "1 9.9999999999999995e-07 1e-10", "End-of-ACIS-data"]
    doc.saveas(p)


def _dxf_b(p: Path):
    """Metri, già in EPSG:7791 (RDN2008 / UTM 32N) vicino a Rimini: una casa a capanna e una polilinea con spessore."""
    import ezdxf
    doc = ezdxf.new("R2010"); doc.header["$INSUNITS"] = 6
    m = doc.modelspace()
    E0, N0 = 786210.0, 4883050.0
    for f in casa(E0, N0, 14, 10, 7, 10.5):
        m.add_3dface(f)
    m.add_lwpolyline([(E0 + 30, N0), (E0 + 42, N0), (E0 + 42, N0 + 9), (E0 + 30, N0 + 9)], close=True,
                     dxfattribs={"thickness": 9.0, "layer": "UFFICI", "elevation": 0.0})
    doc.saveas(p)


def _dxf_c(p: Path):
    """Millimetri ($INSUNITS = 4), non georeferenziato: si posa con due punti noti."""
    import ezdxf
    doc = ezdxf.new("R2010"); doc.header["$INSUNITS"] = 4
    m = doc.modelspace()
    for f in casa(0, 0, 12000, 9000, 6500, 9500):
        m.add_3dface(f)
    doc.saveas(p)


def _ifc(p: Path, mappa: bool, mm: bool = False, nord: float = 0.0):
    import ifcopenshell
    import ifcopenshell.api as api
    f = ifcopenshell.file(schema="IFC4")
    pr = api.run("root.create_entity", f, ifc_class="IfcProject", name="Prova sintetica")
    if mm:
        lun = api.run("unit.add_si_unit", f, unit_type="LENGTHUNIT", prefix="MILLI")
        api.run("unit.assign_unit", f, units=[lun])
    else:
        api.run("unit.assign_unit", f)
    ctx = api.run("context.add_context", f, context_type="Model")
    body = api.run("context.add_context", f, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=ctx)
    site = api.run("root.create_entity", f, ifc_class="IfcSite", name="Sito <script>")
    bld = api.run("root.create_entity", f, ifc_class="IfcBuilding", name="Edificio")
    api.run("aggregate.assign_object", f, relating_object=pr, products=[site])
    api.run("aggregate.assign_object", f, relating_object=site, products=[bld])
    if nord:
        r = math.radians(nord)
        ctx.TrueNorth = f.createIfcDirection((-math.sin(r), math.cos(r)))
    if mappa:
        crs = f.createIfcProjectedCRS(Name="EPSG:7791", Description="RDN2008 / UTM zone 32N")
        a = math.cos(math.radians(20)); b = math.sin(math.radians(20))
        f.createIfcMapConversion(SourceCRS=ctx, TargetCRS=crs, Eastings=786400.0, Northings=4883200.0,
                                 OrthogonalHeight=5.0, XAxisAbscissa=a, XAxisOrdinate=b, Scale=(0.001 if mm else 1.0))
    else:
        site.RefLatitude = [44, 3, 36, 0]; site.RefLongitude = [12, 33, 59, 0]

    def mesh(cls, facce):
        # vertici in metri: add_mesh_representation li converte da solo nelle unità del progetto (mm compresi)
        el = api.run("root.create_entity", f, ifc_class=cls)
        vs, fs = [], []
        for fc in facce:
            idx = []
            for v in fc:
                if v not in vs:
                    vs.append(v)
                idx.append(vs.index(v))
            fs.append(idx)
        rep = api.run("geometry.add_mesh_representation", f, context=body, vertices=[vs], faces=[fs])
        api.run("geometry.assign_representation", f, product=el, representation=rep)
        if cls == "IfcSpace":
            api.run("aggregate.assign_object", f, relating_object=bld, products=[el])
        else:
            api.run("spatial.assign_container", f, relating_structure=bld, products=[el])
    fc = casa(0, 0, 12, 10, 7, 10)
    mesh("IfcWall", fc[:4])
    mesh("IfcRoof", [fc[4], fc[5]])
    mesh("IfcSlab", [fc[8], [(0, 0, 3), (12, 0, 3), (12, 10, 3), (0, 10, 3)]])    # solaio intermedio: non è un tetto
    # secondo corpo: tetto piano a 4 m
    mesh("IfcWall", [[(20, 0, 0), (28, 0, 0), (28, 0, 4), (20, 0, 4)], [(28, 0, 0), (28, 6, 0), (28, 6, 4), (28, 0, 4)],
                     [(28, 6, 0), (20, 6, 0), (20, 6, 4), (28, 6, 4)], [(20, 6, 0), (20, 0, 0), (20, 0, 4), (20, 6, 4)]])
    mesh("IfcSlab", [[(20, 0, 4), (28, 0, 4), (28, 6, 4), (20, 6, 4)]])
    # un arredo alto (escluso) e uno spazio (escluso): non devono diventare tetti
    mesh("IfcFurnishingElement", [[(40, 0, 0), (41, 0, 0), (41, 1, 0), (40, 1, 0)], [(40, 0, 6), (41, 0, 6), (41, 1, 6), (40, 1, 6)]])
    mesh("IfcSpace", [[(50, 0, 9), (55, 0, 9), (55, 5, 9), (50, 5, 9)]])
    f.write(str(p))


# punti noti per i file non georeferenziati (inventati, vicino a Rimini)
POSE = {
    "casa_metri.dxf": {"tipo": "due_punti", "punti": [(0.0, 0.0, 12.5665, 44.0600), (10.0, 0.0, 12.566625, 44.0600)]},
    "casa_mm.dxf": {"tipo": "due_punti", "punti": [(0.0, 0.0, 12.5700, 44.0610), (12000.0, 0.0, 12.570150, 44.0610)]},
}


def genera(cartella: Path) -> dict:
    cartella = Path(cartella); cartella.mkdir(parents=True, exist_ok=True)
    out = {}
    _dxf_a(cartella / "casa_metri.dxf"); out["casa_metri.dxf"] = (cartella / "casa_metri.dxf", POSE["casa_metri.dxf"])
    _dxf_b(cartella / "casa_utm.dxf"); out["casa_utm.dxf"] = (cartella / "casa_utm.dxf", {"tipo": "crs", "crs": "EPSG:7791"})
    _dxf_c(cartella / "casa_mm.dxf"); out["casa_mm.dxf"] = (cartella / "casa_mm.dxf", POSE["casa_mm.dxf"])
    _ifc(cartella / "casa_sito.ifc", mappa=False, nord=15.0); out["casa_sito.ifc"] = (cartella / "casa_sito.ifc", None)
    _ifc(cartella / "casa_mappa_mm.ifc", mappa=True, mm=True); out["casa_mappa_mm.ifc"] = (cartella / "casa_mappa_mm.ifc", None)
    return out


if __name__ == "__main__":
    for nome, (p, posa) in genera(Path(sys.argv[1] if len(sys.argv) > 1 else "modelli_sintetici")).items():
        print(p, posa or "(georeferenziato)")


# ---------------------------------------------------------------------------------------------- confronto Python ↔ JS
def _centroide(f):
    cs = f["geometry"]["coordinates"][0][:-1]
    return sum(q[0] for q in cs) / len(cs), sum(q[1] for q in cs) / len(cs)


def confronta(py: dict, js: dict) -> list[str]:
    """Differenze tra il GeoJSON del comando Python e quello della pagina (stesso file, stessa posa). I corpi si
    abbinano per posizione (l'ordine può cambiare: i due lettori elencano gli elementi IFC in ordine diverso);
    tolleranze: 5 cm di posizione, 2 cm di altezza, 1 % di area, 0,3° di pendenza, 0,5° di orientamento."""
    d = []
    for k in ("type", "formato", "licenza", "fonte"):
        if py.get(k) != js.get(k):
            d.append(f"{k}: {py.get(k)!r} ≠ {js.get(k)!r}")
    if {k: v for k, v in py["posa"].items()} .keys() != js["posa"].keys():
        d.append(f"posa: {sorted(py['posa'])} ≠ {sorted(js['posa'])}")
    if len(py["avvisi"]) != len(js["avvisi"]):
        d.append(f"avvisi: {py['avvisi']} ≠ {js['avvisi']}")
    if len(py["features"]) != len(js["features"]):
        return d + [f"corpi: {len(py['features'])} ≠ {len(js['features'])}"]
    m = 111_320.0
    restanti = list(js["features"])
    for f in py["features"]:
        cx, cy = _centroide(f)
        g = min(restanti, key=lambda x: math.hypot(_centroide(x)[0] - cx, _centroide(x)[1] - cy))
        restanti.remove(g)
        gx, gy = _centroide(g)
        dist = math.hypot((gx - cx) * m * math.cos(math.radians(cy)), (gy - cy) * m)
        p, q = f["properties"], g["properties"]
        nome = p["id"]
        if dist > 0.05:
            d.append(f"{nome}: centro spostato di {dist:.3f} m")
        if p["tetto"] != q["tetto"]:
            d.append(f"{nome}: tetto {p['tetto']} ≠ {q['tetto']}")
        for k in ("gronda", "colmo", "quota_base_modello"):
            a, b = p.get(k), q.get(k)
            if (a is None) != (b is None) or (a is not None and abs(a - b) > 0.02):
                d.append(f"{nome}: {k} {a} ≠ {b}")
        if abs(p["area"] - q["area"]) > max(0.5, 0.01 * p["area"]):
            d.append(f"{nome}: area {p['area']} ≠ {q['area']}")
        if p.get("nota") != q.get("nota") or p["fonte_altezza"] != q["fonte_altezza"] or p["licenza"] != q["licenza"]:
            d.append(f"{nome}: nota, fonte o licenza diverse")
        fa = sorted(p["falde"], key=lambda x: (x["orientamento"], x["pendenza"]))
        fb = sorted(q["falde"], key=lambda x: (x["orientamento"], x["pendenza"]))
        if len(fa) != len(fb):
            d.append(f"{nome}: falde {len(fa)} ≠ {len(fb)}")
            continue
        for x, y in zip(fa, fb):
            do = abs((x["orientamento"] - y["orientamento"] + 180) % 360 - 180)
            if abs(x["pendenza"] - y["pendenza"]) > 0.3 or do > 0.5 or x["settore"] != y["settore"]:
                d.append(f"{nome}: falda {x['pendenza']}°/{x['orientamento']}° ≠ {y['pendenza']}°/{y['orientamento']}°")
            for k in ("superficie", "area_pianta"):
                if abs(x[k] - y[k]) > max(0.5, 0.01 * x[k]):
                    d.append(f"{nome}: falda {k} {x[k]} ≠ {y[k]}")
            for k in ("alto", "basso"):
                if abs(x[k] - y[k]) > 0.02:
                    d.append(f"{nome}: falda {k} {x[k]} ≠ {y[k]}")
    return d
