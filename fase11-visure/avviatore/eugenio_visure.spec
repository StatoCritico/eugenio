# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: EuGEnioVisure.exe (un solo file) = avviatore + Python + pypdf + numpy, shapely, pyproj, ezdxf e
# IfcOpenShell (conversione dei modelli DXF/IFC, dal 04/11/2026) + elenco delle versioni approvate + pacchetto del lettore
# della versione attuale (dist/visure-<v>.zip, da costruire prima con costruisci_pacchetto.py).
# Il lettore NON è compilato dentro l'.exe: l'avviatore lo carica dallo zip dopo averne controllato l'impronta.
#
#   pyinstaller --clean --noconfirm avviatore/eugenio_visure.spec      (dalla cartella fase11-visure)
import json
import re
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

FASE = Path(SPECPATH).resolve().parent
versione = re.search(r'VERSIONE\s*=\s*"([^"]+)"', (FASE / "visure" / "__init__.py").read_text(encoding="utf-8")).group(1)
pacchetto = FASE / "dist" / f"visure-{versione}.zip"
if not pacchetto.exists():
    raise SystemExit(f"manca {pacchetto}: esegui prima python avviatore/costruisci_pacchetto.py")
elenco = json.loads((FASE / "avviatore" / "versioni_approvate.json").read_text(encoding="utf-8"))
if not any(v["versione"] == versione for v in elenco["versioni"]):
    raise SystemExit(f"la versione {versione} non è nell'elenco delle versioni approvate")

# conversione dei modelli DXF/IFC (04/11/2026): il codice (edifici3d/importa.py) sta nel pacchetto approvato, le
# librerie compilate qui. IfcOpenShell ha un modulo C++ (_ifcopenshell_wrapper) e gli schemi; pyproj il database proj.db.
dati, binari, nascosti = [], [], collect_submodules("pypdf")
for lib in ("ifcopenshell", "pyproj", "shapely", "ezdxf"):
    d, b, h = collect_all(lib)
    dati += d; binari += b; nascosti += h
nascosti += collect_submodules("numpy") + ["multiprocessing.spawn", "ctypes.wintypes"]
# plugin di IfcOpenShell che la conversione non usa (esportazioni in DAE/GLB/OBJ/STEP/SVG…, documenti JSON/XML/RDB,
# OpenCOLLADA): restano fuori per alleggerire l'.exe. I plugin della geometria (mapping_*, kernel_*, tree_*) restano.
INUTILI = ("ifcopenshell_geometry_dae", "ifcopenshell_geometry_glb", "ifcopenshell_geometry_igs", "ifcopenshell_geometry_obj",
           "ifcopenshell_geometry_stp", "ifcopenshell_geometry_svg", "ifcopenshell_geometry_ttl", "ifcopenshell_geometry_writer",
           "ifcopenshell_document_", "OpenCOLLADA", "GeneratedSaxParser", "MathMLSolver")
binari = [x for x in binari if not any(k in Path(x[0]).name for k in INUTILI)]

a = Analysis(
    [str(FASE / "avviatore" / "avviatore.py")],
    pathex=[],
    binaries=binari,
    datas=[(str(FASE / "avviatore" / "versioni_approvate.json"), "."), (str(pacchetto), "pacchetti")] + dati,
    hiddenimports=nascosti,
    # visure ed edifici3d NON si compilano nell'.exe: si caricano dal pacchetto approvato dopo il controllo dell'impronta
    excludes=["visure", "edifici3d", "tkinter", "reportlab", "PIL", "pandas", "pytest", "matplotlib", "IPython", "scipy"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="EuGEnioVisure",
    debug=False,
    strip=False,
    upx=False,                 # UPX fa scattare più spesso gli antivirus: niente compressione
    console=True,              # finestra di testo: si vede cosa fa e si chiude con Ctrl+C
    disable_windowed_traceback=False,
    version=str(FASE / "avviatore" / "versione_windows.txt") if (FASE / "avviatore" / "versione_windows.txt").exists() else None,
)
