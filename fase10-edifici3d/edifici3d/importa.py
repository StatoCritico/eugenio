"""Modelli dell'utente: DXF (ezdxf, MIT) e IFC (IfcOpenShell, LGPL-3.0) → corpi con altezze e falde (Fase C, § 5).

Il risultato è un GeoJSON in WGS84 nel formato «eugenio-modello-1» che la pagina 3D apre **nel browser** (il file non
va sul server: § 5 della proposta, «elaborati solo nel browser, senza salvarli sul server»). Il comando gira sul PC
dell'utente o sul server dell'ente:

  pip install ezdxf ifcopenshell        # solo per questo comando
  python -m edifici3d importa-modello edificio.ifc --uscita modello.geojson
  python -m edifici3d importa-modello pianta.dxf --uscita modello.geojson --posa 0,0=12.5665,44.0600 10,0=12.5667,44.0600
  python -m edifici3d importa-modello grande.ifc --uscita modello.geojson --grande     # fino a 500 MB, 8 GB, 30 min

La stessa logica gira anche nel browser, nella pagina «Importa DXF/IFC» del sito (fase5-sito/sito/modelli_import.js,
con dxf-parser e web-ifc): i test di parità (tests/test_importa_parita.py) confrontano i due risultati sugli stessi file.
I punti di --posa si scrivono nelle unità del disegno; gli orientamenti delle falde sono riferiti al nord vero.

**Dati non fidati.** Il file si apre in un processo figlio con tetti di memoria (2 GB) e di CPU (120 s); prima si
controllano dimensione (50 MB), estensione e firma del formato (niente IFC compressi né XML); poi tetti sul numero di
entità, di blocchi annidati, di triangoli e di corpi; coordinate e altezze non finite o fuori scala si scartano; i nomi
presi dal file si ripuliscono. Nessun codice del file viene eseguito (DXF e IFC sono dati, ma i lettori sono librerie C/
C++ e Python: per questo il processo separato).

Cosa si legge
- **DXF**: polilinee chiuse con spessore (`thickness`: base = elevazione, altezza = spessore) o con l'altezza nel nome
  del layer («H=12,5»); facce 3D (3DFACE, MESH, POLYFACE, anche dentro i blocchi). Le facce rivolte in alto che sono la
  superficie più alta nel loro punto sono i tetti: si raggruppano per piano (normale entro 5°, distanza entro 0,3 m) →
  falde; falde vicine con la stessa gronda formano un corpo, i tetti piani a quote diverse corpi diversi (§ 7).
- **IFC**: geometria di tutti gli elementi costruttivi (IfcOpenShell, coordinate del mondo in metri), stessa regola dei
  tetti; posa automatica da IfcMapConversion (IFC4) o da latitudine, longitudine e nord di IfcSite.
"""
from __future__ import annotations

import hashlib
import json
import math
import multiprocessing as mp
import re
from pathlib import Path

import numpy as np

MAX_MB = 50
MAX_ENTITA = 200_000
MAX_PROFONDITA = 8
MAX_TRIANGOLI = 2_000_000
MAX_CORPI = 500
ALTEZZA_MAX = 300.0
COORD_MAX = 1e7                     # m: coordinate oltre (in valore assoluto) si scartano
MEMORIA = 2 * 1024 ** 3
CPU_S = 120
TEMPO_S = 180
LICENZA = "dati dell'utente"
FORMATO = "eugenio-modello-1"
UNITA_DXF = {1: 0.0254, 2: 0.3048, 4: 0.001, 5: 0.01, 6: 1.0, 7: 1000.0, 14: 0.1}   # $INSUNITS → metri


class ModelloNonValido(ValueError):
    pass


def pulisci(t, n: int = 80) -> str:
    """Testo preso dal file: solo caratteri stampabili, al più n."""
    t = re.sub(r"[\x00-\x1f\x7f<>]", " ", str(t or ""))
    return re.sub(r"\s+", " ", t).strip()[:n]


# ============================================================================================== controlli e processo
def controlla_file(p: Path, max_mb: float | None = None) -> str:
    p = Path(p)
    max_mb = MAX_MB if max_mb is None else max_mb
    if not p.is_file() or p.is_symlink():
        raise ModelloNonValido("il file non c'è o non è un file normale")
    mb = p.stat().st_size / 1024 ** 2
    if mb > max_mb:
        raise ModelloNonValido(f"file di {mb:.0f} MB: massimo {max_mb:g} MB" + ("" if max_mb >= LIMITI_GRANDE["MAX_MB"] else " (sul PC: opzione --grande)"))
    est = p.suffix.lower()
    testa = p.read_bytes()[:256] if p.stat().st_size else b""
    if est == ".ifc":
        if not testa.lstrip(b"\xef\xbb\xbf \r\n\t").startswith(b"ISO-10303-21"):
            raise ModelloNonValido("non è un IFC in formato STEP (ISO-10303-21); IFC compressi (.ifczip) e ifcXML non sono accettati")
        return "ifc"
    if est == ".dxf":
        if testa.startswith(b"AutoCAD Binary DXF"):
            return "dxf"
        t = testa.lstrip(b"\xef\xbb\xbf \r\n\t")
        if not re.match(rb"0\s*\r?\n\s*SECTION", t) and not re.match(rb"999\s*\r?\n", t):
            raise ModelloNonValido("non sembra un DXF (manca la sezione iniziale)")
        return "dxf"
    raise ModelloNonValido("formato non gestito: servono .dxf o .ifc (per il DWG: convertirlo prima in DXF)")


# limiti per i file molto grandi, solo sul PC dell'utente (opzione --grande): il browser resta a 50 MB
LIMITI_GRANDE = {"MAX_MB": 500, "MAX_ENTITA": 2_000_000, "MAX_TRIANGOLI": 20_000_000, "MEMORIA": 8 * 1024 ** 3,
                 "CPU_S": 1800, "TEMPO_S": 1900}


def limiti(grande: bool = False) -> dict:
    base = {k: globals()[k] for k in ("MAX_MB", "MAX_ENTITA", "MAX_TRIANGOLI", "MEMORIA", "CPU_S", "TEMPO_S")}
    return base | (LIMITI_GRANDE if grande else {})


def _limita_memoria_windows(byte: int) -> None:
    """Su Windows non c'è RLIMIT_AS: il processo figlio si chiude da solo in un Job Object con un tetto di memoria."""
    import ctypes
    from ctypes import wintypes as w

    class BASIC(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", w.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", w.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", w.DWORD), ("SchedulingClass", w.DWORD)]

    class IO(ctypes.Structure):
        _fields_ = [(n, ctypes.c_uint64) for n in ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                                                    "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class ESTESO(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", BASIC), ("IoInfo", IO), ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateJobObjectW.restype = w.HANDLE
    k32.GetCurrentProcess.restype = w.HANDLE
    job = k32.CreateJobObjectW(None, None)
    info = ESTESO()
    info.BasicLimitInformation.LimitFlags = 0x100          # JOB_OBJECT_LIMIT_PROCESS_MEMORY
    info.ProcessMemoryLimit = byte
    if not k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):   # ExtendedLimitInformation
        raise OSError(ctypes.get_last_error())
    if not k32.AssignProcessToJobObject(job, k32.GetCurrentProcess()):
        raise OSError(ctypes.get_last_error())


def _figlio(conn, percorso, tipo, unita, lim=None):
    g = globals()
    for k, v in (lim or {}).items():        # con «spawn» (Windows) il figlio riparte dai valori del modulo
        g[k] = v
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (MEMORIA, MEMORIA))
        resource.setrlimit(resource.RLIMIT_CPU, (CPU_S, CPU_S + 5))
    except Exception:
        try:
            import os
            if os.name == "nt":
                _limita_memoria_windows(MEMORIA)
        except Exception:
            pass
    try:
        r = leggi_dxf(percorso, unita) if tipo == "dxf" else leggi_ifc(percorso)
        conn.send(("ok", r))
    except ModelloNonValido as e:
        conn.send(("errore", str(e)))
    except MemoryError:
        conn.send(("errore", "modello troppo grande per la memoria consentita (sul PC prova --grande)"))
    except Exception as e:
        conn.send(("errore", f"file non leggibile ({type(e).__name__})"))
    finally:
        conn.close()


def contesto_processi():
    """«fork» dove c'è (Linux, macOS da riga di comando), altrimenti «spawn» (Windows, anche nell'.exe dell'avviatore,
    che chiama multiprocessing.freeze_support()); EUGENIO_MP=spawn per provarlo anche su Linux."""
    import os
    metodo = os.environ.get("EUGENIO_MP") or ("fork" if "fork" in mp.get_all_start_methods() else "spawn")
    return mp.get_context(metodo)


def importa_sicuro(percorso: Path, posa: dict | None = None, unita: float | None = None, edificio: str = "MODELLO",
                   in_processo: bool = True, grande: bool = False) -> dict:
    """Controlli, lettura in un processo figlio con tetti, posa e GeoJSON «eugenio-modello-1». Con grande=True (opzione
    --grande, solo sul PC) valgono i limiti di LIMITI_GRANDE: fino a 500 MB, 8 GB di memoria, 30 minuti."""
    percorso = Path(percorso)
    lim = limiti(grande)
    tipo = controlla_file(percorso, lim["MAX_MB"])
    if in_processo:
        ctx = contesto_processi()
        a, b = ctx.Pipe(duplex=False)
        pr = ctx.Process(target=_figlio, args=(b, str(percorso), tipo, unita, lim), daemon=True)
        pr.start()
        b.close()
        if not a.poll(lim["TEMPO_S"]):
            pr.kill(); pr.join(5)
            raise ModelloNonValido(f"lettura oltre {lim['TEMPO_S']} s: modello troppo complesso (sul PC prova --grande)")
        try:
            esito, r = a.recv()
        except EOFError:
            pr.join(5)
            raise ModelloNonValido("la lettura si è interrotta (memoria o tempo esauriti, o file danneggiato)")
        pr.join(5)
        if esito != "ok":
            raise ModelloNonValido(r)
    else:
        r = leggi_dxf(percorso, unita) if tipo == "dxf" else leggi_ifc(percorso)
    h = hashlib.sha256(percorso.read_bytes()).hexdigest()
    return geojson(r, in_metri(posa, r.get("unita_m", 1.0)) or r.get("georef"), tipo, pulisci(percorso.name, 120), h, edificio)


def in_metri(posa: dict | None, k: float) -> dict | None:
    """I punti della posa si scrivono nelle unità del disegno (quelle che si leggono nel CAD, es. millimetri): i corpi
    sono già in metri, quindi le coordinate del disegno dei punti si moltiplicano per le stesse unità."""
    if not posa or k == 1.0:
        return posa
    q = dict(posa)
    if q.get("tipo") == "punto":
        q["x"], q["y"] = q["x"] * k, q["y"] * k
    elif q.get("tipo") == "due_punti":
        q["punti"] = [(x * k, y * k, lon, lat) for x, y, lon, lat in q["punti"]]
    return q


# ============================================================================================== DXF
def leggi_dxf(percorso, unita: float | None = None) -> dict:
    import ezdxf
    from ezdxf import recover
    doc, auditor = recover.readfile(str(percorso))
    avvisi = []
    if auditor.has_errors:
        avvisi.append(f"DXF con {len(auditor.errors)} errori corretti in lettura")
    ins = int(doc.header.get("$INSUNITS", 0) or 0)
    k = unita or UNITA_DXF.get(ins) or 1.0
    if not unita and ins not in UNITA_DXF:
        avvisi.append("unità del disegno non indicate: si assumono metri (opzione --unita per cambiarle)")
    tri: list = []
    prismi: list = []
    conta = {"n": 0, "solidi": 0}

    def visita(entita, prof=0):
        for e in entita:
            conta["n"] += 1
            if conta["n"] > MAX_ENTITA:
                raise ModelloNonValido(f"troppe entità (oltre {MAX_ENTITA})")
            t = e.dxftype()
            try:
                if t == "INSERT":
                    if prof >= MAX_PROFONDITA:
                        raise ModelloNonValido("blocchi annidati troppo in profondità")
                    visita(e.virtual_entities(), prof + 1)
                elif t == "3DFACE":
                    v = [tuple(e.dxf.get(f"vtx{i}")) for i in range(4)]
                    _aggiungi_poligono(tri, v, k)
                elif t == "MESH":
                    vs = [tuple(p) for p in e.vertices]
                    for f in e.faces:
                        _aggiungi_poligono(tri, [vs[i] for i in f if 0 <= i < len(vs)], k)
                elif t == "POLYLINE" and e.is_poly_face_mesh:
                    from ezdxf.render import MeshBuilder
                    m = MeshBuilder.from_polyface(e)
                    for f in m.faces:
                        _aggiungi_poligono(tri, [tuple(m.vertices[i]) for i in f], k)
                elif t in ("LWPOLYLINE", "POLYLINE") and e.is_closed:
                    _prisma(e, t, k, prismi)
                elif t in ("3DSOLID", "BODY", "REGION", "SURFACE"):
                    conta["solidi"] += 1
            except ModelloNonValido:
                raise
            except Exception:
                continue
            if len(tri) > MAX_TRIANGOLI:
                raise ModelloNonValido(f"troppi triangoli (oltre {MAX_TRIANGOLI})")

    visita(doc.modelspace())
    if conta["solidi"]:
        avvisi.append(f"{conta['solidi']} solidi ACIS (3DSOLID) non letti: esportarli come MESH o 3DFACE")
    corpi = corpi_da_triangoli(np.array(tri, dtype="float64").reshape(-1, 3, 3)) if tri else []
    corpi += [c for c in prismi if not any(_sovrapposto(c, d) for d in corpi)]
    if not corpi:
        raise ModelloNonValido("nessun corpo trovato: servono polilinee chiuse con spessore o facce 3D")
    return {"corpi": corpi[:MAX_CORPI], "avvisi": avvisi, "georef": None, "unita_m": k}


def _aggiungi_poligono(tri: list, v, k: float):
    pts = []
    for p in v:
        if p is None or len(p) < 3:
            continue
        q = (float(p[0]) * k, float(p[1]) * k, float(p[2]) * k)
        if all(math.isfinite(c) and abs(c) < COORD_MAX for c in q) and (not pts or q != pts[-1]):
            pts.append(q)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    for i in range(1, len(pts) - 1):
        tri.append((pts[0], pts[i], pts[i + 1]))


def _prisma(e, t, k: float, out: list):
    from shapely.geometry import Polygon
    if t == "LWPOLYLINE":
        pts = [(float(x) * k, float(y) * k) for x, y, *_ in e.get_points("xy")]
        base = float(e.dxf.get("elevation", 0) or 0) * k
    else:
        vs = [v.dxf.location for v in e.vertices]
        pts = [(float(p[0]) * k, float(p[1]) * k) for p in vs]
        base = float(vs[0][2]) * k if vs else 0.0
    spessore = float(e.dxf.get("thickness", 0) or 0) * k
    h = abs(spessore) if spessore else _altezza_layer(e.dxf.get("layer", ""))
    if len(pts) < 3 or not all(math.isfinite(c) and abs(c) < COORD_MAX for p in pts for c in p):
        return
    g = Polygon(pts)
    if not g.is_valid:
        g = g.buffer(0)
    if g.is_empty or g.area < 1 or g.geom_type != "Polygon":
        return
    if spessore < 0:
        base -= abs(spessore)
    gr = h if h and 0 < h <= ALTEZZA_MAX else None
    out.append({"sagoma": list(g.exterior.coords), "base": base, "gronda": gr, "colmo": gr, "tetto": "piano",
                "falde": [_falda_piana(g, gr or 0.0)],
                "nota": None if gr else "altezza non indicata nel DXF: da completare nella pagina",
                "nome": pulisci(e.dxf.get("layer", ""))})


def _altezza_layer(nome: str) -> float | None:
    m = re.search(r"(?:^|[^A-Za-z])(?:H|ALT|ALTEZZA)\s*[=_:]?\s*(\d+(?:[.,]\d+)?)", str(nome), flags=re.I)
    return float(m.group(1).replace(",", ".")) if m else None


def _falda_piana(g, h: float) -> dict:
    return {"pendenza": 0.0, "orientamento": 180.0, "area_pianta": g.area, "superficie": g.area, "alto": h, "basso": h,
            "anello": list(g.exterior.coords)}


def _sovrapposto(a: dict, b: dict) -> bool:
    from shapely.geometry import Polygon
    pa, pb = Polygon(a["sagoma"]), Polygon(b["sagoma"])
    return pa.intersection(pb).area > 0.5 * min(pa.area, pb.area)


# ============================================================================================== IFC
TIPI_IFC_ESCLUSI = ("IfcSpace", "IfcOpeningElement", "IfcSite", "IfcAnnotation", "IfcGrid", "IfcVirtualElement",
                    "IfcGeographicElement", "IfcFurnishingElement", "IfcDistributionElement")


def leggi_ifc(percorso) -> dict:
    import ifcopenshell
    import ifcopenshell.geom
    _cartella_plugin(ifcopenshell)
    f = ifcopenshell.open(str(percorso))
    avvisi = []
    prodotti = [p for p in f.by_type("IfcProduct") if getattr(p, "Representation", None)
                and not any(p.is_a(t) for t in TIPI_IFC_ESCLUSI)]
    if len(prodotti) > MAX_ENTITA:
        raise ModelloNonValido(f"troppi elementi (oltre {MAX_ENTITA})")
    s = ifcopenshell.geom.settings()
    for chiave in ("use-world-coords", "USE_WORLD_COORDS"):
        try:
            s.set(chiave, True)
            break
        except Exception:
            try:
                s.set(getattr(s, chiave), True)
                break
            except Exception:
                continue
    tri = []
    primo_errore = None
    for p in prodotti:
        try:
            sh = ifcopenshell.geom.create_shape(s, p)
        except Exception as e:
            primo_errore = primo_errore or pulisci(f"{type(e).__name__}: {e}", 120)
            continue
        g = sh.geometry
        v = np.asarray(g.verts, dtype="float64").reshape(-1, 3)
        fc = np.asarray(g.faces, dtype=np.int64).reshape(-1, 3)
        if not len(fc):
            continue
        if not np.isfinite(v).all() or np.abs(v).max() > COORD_MAX:
            continue
        tri.append(v[fc])
        if sum(len(x) for x in tri) > MAX_TRIANGOLI:
            raise ModelloNonValido(f"troppi triangoli (oltre {MAX_TRIANGOLI})")
    if not tri:
        raise ModelloNonValido("nessuna geometria leggibile negli elementi dell'IFC"
                               + (f" (primo errore: {primo_errore})" if primo_errore else ""))
    corpi = corpi_da_triangoli(np.concatenate(tri))
    if not corpi:
        raise ModelloNonValido("nessun tetto riconosciuto nel modello")
    return {"corpi": corpi[:MAX_CORPI], "avvisi": avvisi, "georef": georef_ifc(f), "unita_m": 1.0,
            "schema": pulisci(f.schema, 20)}


def unita_ifc(f) -> float:
    """Metri per unità di lunghezza del progetto (IfcUnitAssignment): 0,001 per i millimetri."""
    pref = {"EXA": 1e18, "PETA": 1e15, "TERA": 1e12, "GIGA": 1e9, "MEGA": 1e6, "KILO": 1e3, "HECTO": 1e2, "DECA": 10.0,
            "DECI": 0.1, "CENTI": 0.01, "MILLI": 1e-3, "MICRO": 1e-6, "NANO": 1e-9}
    try:
        for ua in f.by_type("IfcUnitAssignment"):
            for u in ua.Units:
                if getattr(u, "UnitType", None) != "LENGTHUNIT":
                    continue
                if u.is_a("IfcSIUnit"):
                    return pref.get(u.Prefix or "", 1.0) if u.Prefix else 1.0
                if u.is_a("IfcConversionBasedUnit"):
                    mf = u.ConversionFactor
                    return float(mf.ValueComponent.wrappedValue) * unita_ifc_si(mf.UnitComponent, pref)
    except Exception:
        pass
    return 1.0


def unita_ifc_si(u, pref) -> float:
    try:
        return pref.get(u.Prefix or "", 1.0) if u.Prefix else 1.0
    except Exception:
        return 1.0


def _cartella_plugin(ifcopenshell) -> None:
    """IfcOpenShell 0.8+ carica la geometria di ogni schema da plugin (.so/.dll) accanto al modulo; nell'.exe di
    PyInstaller la cartella non è tra quelle cercate («No geometry mapping registered for ifc4»): la si aggiunge."""
    try:
        d = str(Path(ifcopenshell.__file__).resolve().parent)
        ora = list(ifcopenshell.get_plugin_search_paths())
        if d not in ora:
            ifcopenshell.set_plugin_search_paths(ora + [d])
    except Exception:
        pass


def georef_ifc(f) -> dict | None:
    """Posa dal file: IfcMapConversion (IFC4) se c'è, altrimenti latitudine/longitudine e nord vero di IfcSite."""
    try:
        for mc in f.by_type("IfcMapConversion"):
            crs = mc.TargetCRS
            nome = str(getattr(crs, "Name", "") or "")
            m = re.search(r"(\d{4,5})", nome)
            if not m:
                continue
            # Scale porta le unità del progetto in quelle della mappa; la geometria di IfcOpenShell è già in metri
            # (geometria in mm con Scale = 0,001 → si divide per 0,001 dopo averla moltiplicata per 1000)
            a = float(mc.XAxisAbscissa if mc.XAxisAbscissa is not None else 1.0)
            b = float(mc.XAxisOrdinate if mc.XAxisOrdinate is not None else 0.0)
            return {"tipo": "conversione", "crs": f"EPSG:{m.group(1)}", "e0": float(mc.Eastings), "n0": float(mc.Northings),
                    "quota": float(mc.OrthogonalHeight or 0.0), "a": a, "b": b,
                    "scala": float(mc.Scale or 1.0) / unita_ifc(f),
                    "origine": "IfcMapConversion"}
    except Exception:
        pass
    try:
        for site in f.by_type("IfcSite"):
            if site.RefLatitude and site.RefLongitude:
                g = lambda c: (abs(c[0]) + c[1] / 60 + c[2] / 3600 + (c[3] if len(c) > 3 else 0) / 3.6e9) * (-1 if c[0] < 0 or any(x < 0 for x in c) else 1)
                rot = 0.0
                for ctx in f.by_type("IfcGeometricRepresentationContext"):
                    tn = getattr(ctx, "TrueNorth", None)
                    if tn is not None:
                        x, y = tn.DirectionRatios[:2]
                        rot = math.degrees(math.atan2(x, y))     # nord vero rispetto all'asse y del modello
                        break
                ox = oy = 0.0
                try:   # l'origine di IfcSite nelle coordinate del mondo (la latitudine e longitudine sono lì)
                    import ifcopenshell.util.placement as up
                    m = up.get_local_placement(site.ObjectPlacement)     # unità del progetto → metri
                    ox, oy = float(m[0][3]) * unita_ifc(f), float(m[1][3]) * unita_ifc(f)
                except Exception:
                    pass
                return {"tipo": "punto", "lon": g(site.RefLongitude), "lat": g(site.RefLatitude), "x": ox, "y": oy,
                        "rotazione": -rot, "quota": float(site.RefElevation or 0.0), "origine": "IfcSite"}
    except Exception:
        pass
    return None


# ============================================================================================== tetti e corpi dai triangoli
def corpi_da_triangoli(t: np.ndarray, toll_angolo: float = 5.0, toll_distanza: float = 0.3) -> list[dict]:
    """Triangoli (n×3×3, metri) → corpi con falde. Tetti = facce rivolte in alto che sono la superficie più alta nel
    loro punto; raggruppate per piano → falde; falde a contatto con la stessa gronda → un corpo."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    from shapely.strtree import STRtree
    if not len(t):
        return []
    a, b, c = t[:, 0], t[:, 1], t[:, 2]
    n = np.cross(b - a, c - a)
    area3 = np.linalg.norm(n, axis=1) / 2
    ok = area3 > 1e-4
    t, n, area3 = t[ok], n[ok], area3[ok]
    n = n / np.linalg.norm(n, axis=1)[:, None]
    zmin = float(t[:, :, 2].min())
    # le normali vanno orientate verso l'alto per i tetti (i modelli non sempre le hanno coerenti)
    su = n[:, 2] > 0.15
    giu = n[:, 2] < -0.15
    n[giu] *= -1
    cand = np.where((su | giu) & (t[:, :, 2].max(axis=1) > zmin + 1.0))[0]
    if not len(cand):
        return []
    proj = [Polygon(t[i, :, :2]) for i in cand]
    validi = [k for k, p in enumerate(proj) if p.is_valid and p.area > 1e-3]
    cand = cand[validi]; proj = [proj[k] for k in validi]
    if not len(cand):
        return []
    albero = STRtree(proj)
    cen = t[cand].mean(axis=1)

    def z_in(i, x, y):
        nn = n[i]; p0 = t[i, 0]
        return p0[2] - (nn[0] * (x - p0[0]) + nn[1] * (y - p0[1])) / nn[2]

    from shapely.geometry import Point
    tetti = []
    for k, i in enumerate(cand):
        x, y, z = cen[k]
        sopra = False
        for j in albero.query(Point(x, y)):
            ii = cand[j]
            if ii == i or not proj[j].covers(Point(x, y)):
                continue
            if z_in(ii, x, y) > z + 0.2:
                sopra = True
                break
        if not sopra:
            tetti.append(k)
    # raggruppamento per piano
    gruppi: list[dict] = []
    cos_t = math.cos(math.radians(toll_angolo))
    for k in tetti:
        i = cand[k]
        nn = n[i]; d = float(nn @ t[i, 0])
        for g in gruppi:
            if float(g["n"] @ nn) >= cos_t and abs(float(g["n"] @ t[i, 0]) - g["d"]) <= toll_distanza:
                g["idx"].append(k); g["area3"] += area3[i]
                break
        else:
            gruppi.append({"n": nn.copy(), "d": d, "idx": [k], "area3": float(area3[i])})
    falde = []
    for g in gruppi:
        poli = unary_union([proj[k] for k in g["idx"]]).buffer(0.01).buffer(-0.01).simplify(0.02)
        if poli.is_empty or poli.area < 1.0:
            continue
        zs = t[cand[g["idx"]]][:, :, 2]
        nn = g["n"]
        pend = math.degrees(math.acos(min(1.0, abs(float(nn[2])))))
        orient = (math.degrees(math.atan2(nn[0], nn[1])) + 360) % 360 if pend >= 0.5 else 180.0
        falde.append({"poligono": poli, "pendenza": pend, "orientamento": orient, "superficie": g["area3"],
                      "alto": float(zs.max()), "basso": float(zs.min())})
    if not falde:
        return []
    # corpi: falde inclinate a contatto con gronde simili insieme; ogni tetto piano a sé
    corpi_idx: list[list[int]] = []
    for k, f in enumerate(falde):
        messo = False
        if f["pendenza"] >= 5:
            for grp in corpi_idx:
                g0 = falde[grp[0]]
                if g0["pendenza"] >= 5 and abs(g0["basso"] - f["basso"]) < 1.0 and any(
                        falde[q]["poligono"].buffer(0.3).intersects(f["poligono"]) for q in grp):
                    grp.append(k); messo = True
                    break
        if not messo:
            corpi_idx.append([k])
    corpi = []
    for grp in corpi_idx:
        poli = unary_union([falde[k]["poligono"] for k in grp]).buffer(0.05).buffer(-0.05).simplify(0.02)
        if poli.geom_type == "MultiPolygon":
            poli = max(poli.geoms, key=lambda p: p.area)
        if poli.is_empty or poli.area < 4:
            continue
        # base: punto più basso dei triangoli sotto la sagoma (pareti comprese)
        sotto = poli.buffer(0.5)
        bb = sotto.bounds
        dentro = (t[:, :, 0].min(axis=1) <= bb[2]) & (t[:, :, 0].max(axis=1) >= bb[0]) & \
                 (t[:, :, 1].min(axis=1) <= bb[3]) & (t[:, :, 1].max(axis=1) >= bb[1])
        base = float(t[dentro][:, :, 2].min()) if dentro.any() else zmin
        fs = [falde[k] for k in grp]
        alto = max(f["alto"] for f in fs) - base
        basso = min(f["basso"] for f in fs) - base
        if not (0 < alto <= ALTEZZA_MAX):
            continue
        incl = [f for f in fs if f["pendenza"] >= 5]
        tetto = "piano" if not incl else {1: "monofalda", 2: "capanna", 4: "padiglione"}.get(len(incl), "a falde")
        corpi.append({"sagoma": list(poli.exterior.coords), "base": base, "gronda": round(basso if incl else alto, 2),
                      "colmo": round(alto, 2), "tetto": tetto,
                      "falde": [{"pendenza": f["pendenza"], "orientamento": f["orientamento"],
                                 "area_pianta": f["poligono"].area, "superficie": f["superficie"],
                                 "alto": f["alto"] - base, "basso": f["basso"] - base,
                                 "anello": list((f["poligono"] if f["poligono"].geom_type == "Polygon"
                                                 else max(f["poligono"].geoms, key=lambda p: p.area)).exterior.coords)}
                                for f in fs]})
        if len(corpi) >= MAX_CORPI:
            break
    return corpi


# ============================================================================================== posa e GeoJSON
def posa_da_argomenti(posa: list[str] | None, rotazione: float = 0.0, crs: str | None = None) -> dict | None:
    if crs:
        if not re.fullmatch(r"EPSG:\d{4,5}", crs):
            raise ModelloNonValido("--crs: scrivere EPSG:<numero>")
        return {"tipo": "crs", "crs": crs}
    if not posa:
        return None
    punti = []
    for p in posa:
        m = re.fullmatch(r"\s*(-?[\d.]+),(-?[\d.]+)=(-?[\d.]+),(-?[\d.]+)\s*", p)
        if not m:
            raise ModelloNonValido(f"--posa {p!r}: formato X,Y=LON,LAT")
        punti.append(tuple(float(x) for x in m.groups()))
    if len(punti) == 1:
        x, y, lon, lat = punti[0]
        return {"tipo": "punto", "x": x, "y": y, "lon": lon, "lat": lat, "rotazione": rotazione}
    if len(punti) == 2:
        return {"tipo": "due_punti", "punti": punti}
    raise ModelloNonValido("--posa: uno o due punti")


def trasformazione(posa: dict | None):
    """Funzione (x, y) del disegno → (lon, lat), e avvisi."""
    from pyproj import Transformer
    avvisi = []
    if not posa:
        raise ModelloNonValido("manca la posa: il modello non è georeferenziato. Indicare --crs, oppure --posa con due "
                               "punti noti (coordinate del disegno = lon,lat), o un punto e --rotazione")
    a_wgs = Transformer.from_crs("EPSG:7791", "EPSG:4326", always_xy=True)
    da_wgs = Transformer.from_crs("EPSG:4326", "EPSG:7791", always_xy=True)
    if posa["tipo"] == "crs":
        t = Transformer.from_crs(posa["crs"], "EPSG:4326", always_xy=True)
        return (lambda x, y: t.transform(x, y)), avvisi
    if posa["tipo"] == "conversione":
        t = Transformer.from_crs(posa["crs"], "EPSG:4326", always_xy=True)
        h = math.hypot(posa["a"], posa["b"]) or 1.0
        ca, sa, s = posa["a"] / h, posa["b"] / h, posa["scala"]
        return (lambda x, y: t.transform(posa["e0"] + s * (ca * x - sa * y), posa["n0"] + s * (sa * x + ca * y))), avvisi
    if posa["tipo"] == "punto":
        # rotazione = azimut (gradi da nord vero, in senso orario) dell'asse +Y del disegno; nel reticolo UTM si
        # aggiunge l'angolo tra nord vero e nord del reticolo (convergenza del meridiano, ~2,5° a Rimini)
        e0, n0 = da_wgs.transform(posa["lon"], posa["lat"])
        e1, n1 = da_wgs.transform(posa["lon"], posa["lat"] + 0.001)
        convergenza = math.degrees(math.atan2(e1 - e0, n1 - n0))
        r = math.radians(posa.get("rotazione", 0.0) + convergenza)
        cr, sr = math.cos(r), math.sin(r)

        def f(x, y):
            dx, dy = x - posa["x"], y - posa["y"]
            return a_wgs.transform(e0 + cr * dx + sr * dy, n0 - sr * dx + cr * dy)
        return f, avvisi
    if posa["tipo"] == "due_punti":
        (x1, y1, lo1, la1), (x2, y2, lo2, la2) = posa["punti"]
        e1, n1 = da_wgs.transform(lo1, la1); e2, n2 = da_wgs.transform(lo2, la2)
        zd = complex(x2 - x1, y2 - y1); zm = complex(e2 - e1, n2 - n1)
        if abs(zd) < 1e-6:
            raise ModelloNonValido("--posa: i due punti del disegno coincidono")
        k = zm / zd
        if not 0.9 < abs(k) < 1.1:
            avvisi.append(f"scala della posa {abs(k):.3f} (attesa 1): controllare le unità del disegno e i due punti")
        return (lambda x, y: a_wgs.transform(*((lambda w: (w.real, w.imag))(complex(e1, n1) + k * complex(x - x1, y - y1))))), avvisi
    raise ModelloNonValido("posa non riconosciuta")


def geojson(r: dict, posa: dict | None, tipo: str, nome_file: str, sha256: str, edificio: str = "MODELLO") -> dict:
    """Corpi in coordinate del disegno → FeatureCollection WGS84 «eugenio-modello-1»."""
    from shapely.geometry import Polygon
    f, avvisi = trasformazione(posa)
    avvisi = list(r.get("avvisi", [])) + avvisi
    edificio = pulisci(edificio, 40) or "MODELLO"
    fonte = f"modello dell'utente ({tipo.upper()})"

    def anello(cs):
        out = []
        for x, y, *_ in cs:
            lon, lat = f(x, y)
            if not (math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
                raise ModelloNonValido("coordinate fuori scala dopo la posa")
            out.append([round(lon, 8), round(lat, 8)])
        return out

    feats = []
    for k, c in enumerate(r["corpi"], 1):
        cid = f"{edificio}-{k}"
        falde = []
        # gli orientamenti delle falde sono misurati sugli assi del disegno: si portano al nord vero con l'azimut
        # dell'asse +Y del disegno nel punto del corpo (rotazione della posa, nord di IfcSite, convergenza del reticolo)
        dy = azimut_y(f, *_centro(c["sagoma"]))
        for j, fa in enumerate(c.get("falde", []), 1):
            p = float(fa["pendenza"])
            orient = (float(fa["orientamento"]) + dy) % 360 if p >= 0.5 else float(fa["orientamento"])
            falde.append({"id": f"F{j}", "pendenza": round(p, 1), "orientamento": round(orient, 1) % 360,
                          "settore": "—" if p < 5 else _settore(orient),
                          "area_pianta": round(float(fa["area_pianta"]), 1), "superficie": round(float(fa["superficie"]), 1),
                          "alto": round(float(fa["alto"]), 2), "basso": round(float(fa["basso"]), 2),
                          "geometria": {"type": "Polygon", "coordinates": [anello(fa["anello"])]}})
        props = {"id": cid, "edificio": edificio, "gronda": c.get("gronda"), "colmo": c.get("colmo"), "tetto": c.get("tetto", "piano"),
                 "falde": falde, "fonte_sagoma": fonte, "fonte_altezza": fonte, "licenza": LICENZA,
                 "area": round(Polygon(c["sagoma"]).area, 1), "quota_base_modello": round(float(c.get("base", 0.0)), 2)}
        if c.get("nota"):
            props["nota"] = c["nota"]
        feats.append({"type": "Feature", "id": cid, "geometry": {"type": "Polygon", "coordinates": [anello(c["sagoma"])]},
                      "properties": props})
    return {"type": "FeatureCollection", "formato": FORMATO, "fonte": fonte, "file": nome_file, "sha256": sha256,
            "licenza": LICENZA, "avvisi": avvisi[:20], "posa": {k: v for k, v in (posa or {}).items() if k != "punti"}
            | ({"punti": len(posa["punti"])} if posa and "punti" in posa else {}),
            "features": feats}


def _centro(cs) -> tuple[float, float]:
    pts = [(float(q[0]), float(q[1])) for q in cs[:-1]] or [(0.0, 0.0)]
    return sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts)


def azimut_y(f, x: float, y: float) -> float:
    """Azimut (gradi dal nord vero, senso orario) dell'asse +Y del disegno nel punto (x, y), dalla trasformazione."""
    lo0, la0 = f(x, y)
    lo1, la1 = f(x, y + 1.0)
    return math.degrees(math.atan2((lo1 - lo0) * math.cos(math.radians(la0)), la1 - la0))


def _settore(az: float) -> str:
    return ["N", "NE", "E", "SE", "S", "SO", "O", "NO"][int(((az + 22.5) % 360) // 45)]
