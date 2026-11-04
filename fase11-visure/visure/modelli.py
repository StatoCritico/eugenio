"""Conversione dei modelli DXF e IFC sul PC (EuGEnio Visure, decisione del 04/11/2026).

Per i file troppo pesanti per la pagina «Importa DXF/IFC» del sito (oltre 30–50 MB o molto complessi) l'avviatore
`EuGEnioVisure.exe` e l'immagine Docker convertono il file in locale, con lo stesso codice del comando
`python -m edifici3d importa-modello` (fase10-edifici3d/edifici3d/importa.py, ezdxf + IfcOpenShell, file trattati come
non fidati, lettura in un processo separato con limiti di memoria e di tempo). Il risultato è il GeoJSON
«eugenio-modello-1» che la pagina Modelli 3D apre nel browser. Nessuna connessione di rete.

Dove si trova `edifici3d.importa`:
  - nel pacchetto approvato del lettore (visure-<v>.zip), accanto a visure/ (costruisci_pacchetto.py lo copia dalla
    fase 10, così l'impronta SHA-256 dell'elenco copre anche lui);
  - nell'immagine Docker, in /app/edifici3d;
  - nel repository, nella cartella fase10-edifici3d accanto a fase11-visure.
Le librerie compilate (numpy, shapely, pyproj, ezdxf, IfcOpenShell) stanno nell'.exe (PyInstaller) o nell'ambiente.
"""
from __future__ import annotations

import importlib
import sys
import tempfile
from pathlib import Path

LIBRERIE = ("numpy", "shapely", "pyproj", "ezdxf", "ifcopenshell", "ifcopenshell.geom")


def _importa():
    try:
        return importlib.import_module("edifici3d.importa")
    except ImportError:
        repo = Path(__file__).resolve().parents[2] / "fase10-edifici3d"
        if (repo / "edifici3d" / "importa.py").is_file() and str(repo) not in sys.path:
            sys.path.append(str(repo))
        return importlib.import_module("edifici3d.importa")


def disponibile() -> tuple[bool, str]:
    """(True, versioni) se la conversione dei modelli c'è in questa installazione."""
    mancanti, versioni = [], []
    for n in LIBRERIE:
        try:
            m = importlib.import_module(n)
            v = getattr(m, "__version__", None) or getattr(m, "version", None)
            if v and "." not in n:
                versioni.append(f"{n} {v}")
        except Exception:  # noqa: BLE001
            mancanti.append(n)
    if mancanti:
        return False, "librerie mancanti: " + ", ".join(mancanti)
    try:
        _importa()
    except Exception as e:  # noqa: BLE001
        return False, f"modulo di conversione non trovato ({e})"
    return True, ", ".join(versioni)


def converti(percorso: Path, posa: list[str] | None = None, crs: str | None = None, rotazione: float = 0.0,
             unita: float | None = None, grande: bool = False, edificio: str = "MODELLO") -> dict:
    """File DXF o IFC → GeoJSON «eugenio-modello-1» (solleva edifici3d.importa.ModelloNonValido con il motivo)."""
    I = _importa()
    p = I.posa_da_argomenti(posa, rotazione, crs)
    return I.importa_sicuro(Path(percorso), posa=p, unita=unita, edificio=edificio, grande=grande)


def errore_modello(e: Exception) -> str | None:
    """Il messaggio per l'utente se e è un errore del modello, altrimenti None."""
    try:
        I = _importa()
    except Exception:  # noqa: BLE001
        return None
    return str(e) if isinstance(e, I.ModelloNonValido) else None


def prova() -> tuple[bool, str]:
    """Controllo di avvio della conversione: un DXF e un IFC minimi, creati al momento, letti nel processo separato."""
    ok, msg = disponibile()
    if not ok:
        return False, msg
    try:
        import ezdxf
        import ifcopenshell
        import ifcopenshell.api as api
        with tempfile.TemporaryDirectory(prefix="eugenio_modelli_") as d:
            d = Path(d)
            doc = ezdxf.new("R2010"); doc.header["$INSUNITS"] = 6
            m = doc.modelspace()
            for f in _capanna():
                m.add_3dface(f)
            doc.saveas(d / "prova.dxf")
            r = converti(d / "prova.dxf", posa=["0,0=12.5665,44.06"])
            (c,) = [x["properties"] for x in r["features"]]
            if c["tetto"] != "capanna" or abs(c["gronda"] - 6) > 0.01 or abs(c["colmo"] - 9) > 0.01:
                return False, f"DXF di prova letto male: {c['tetto']} {c['gronda']} {c['colmo']}"
            f = ifcopenshell.file(schema="IFC4")
            api.run("root.create_entity", f, ifc_class="IfcProject", name="Prova")
            api.run("unit.assign_unit", f)
            ctx = api.run("context.add_context", f, context_type="Model")
            body = api.run("context.add_context", f, context_type="Model", context_identifier="Body",
                           target_view="MODEL_VIEW", parent=ctx)
            site = api.run("root.create_entity", f, ifc_class="IfcSite", name="Sito")
            site.RefLatitude = [44, 3, 36, 0]; site.RefLongitude = [12, 33, 59, 0]
            vs, fs = [], []
            for fc in _capanna():
                for v in fc:
                    if v not in vs:
                        vs.append(v)
                fs.append([vs.index(v) for v in fc])
            el = api.run("root.create_entity", f, ifc_class="IfcRoof")
            rep = api.run("geometry.add_mesh_representation", f, context=body, vertices=[vs], faces=[fs])
            api.run("geometry.assign_representation", f, product=el, representation=rep)
            f.write(str(d / "prova.ifc"))
            r = converti(d / "prova.ifc")
            (c,) = [x["properties"] for x in r["features"]]
            if c["tetto"] != "capanna" or r["posa"].get("origine") != "IfcSite":
                return False, f"IFC di prova letto male: {c['tetto']} {r['posa']}"
        return True, f"conversione dei modelli a posto ({msg})"
    except Exception as e:  # noqa: BLE001
        return False, f"conversione dei modelli: errore {type(e).__name__}: {e}"


def _capanna():
    A, B, C, D = (0, 0, 0), (10, 0, 0), (10, 8, 0), (0, 8, 0)
    a, b, c, d = (0, 0, 6), (10, 0, 6), (10, 8, 6), (0, 8, 6)
    r1, r2 = (0, 4, 9), (10, 4, 9)
    return [[A, B, b, a], [B, C, c, b], [C, D, d, c], [D, A, a, d], [a, b, r2, r1], [d, c, r2, r1]]
