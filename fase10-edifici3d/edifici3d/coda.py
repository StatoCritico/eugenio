"""Coda «Aggiungi DBTR» (07/11/2026, decisione di Paolo): DB topografici caricati dagli utenti, preparati sul server e
messi nell'archivio comune solo dopo l'approvazione nella pagina interna.

Percorso di un file (cartella della coda `/dati/edifici_coda`, una sottocartella per richiesta, id di 32 cifre esadecimali):

  caricamento  l'api riceve il file a pezzi (servizio/dbtr_coda.py, Turnstile, limiti per IP e dimensione)
  ricevuto     file completo e controllo leggero superato (zip senza percorsi strani, link, bombe; o GeoPackage)
  in preparazione   questo modulo (container `edifici-coda`, una richiesta alla volta, bassa priorità): estrazione sicura,
               controlli (strati e colonne, EPSG, regione e riquadro, metadati della Regione, dati personali,
               `controlla-uvl`), `prepara --comune` (o `prepara-regione --comune`), `controlla-archivio`, anteprima
  in attesa di approvazione   (o «controlli non superati»): la pagina interna mostra esito e anteprima
  approvato    Paolo ha premuto Approva (api): questo modulo installa l'archivio in `<archivio>/cc-by/<zona>/<comune>/`,
               sposta l'archivio precedente dello stesso comune in `<archivio>/_precedenti/` e rigenera archivi.json
  installato / rifiutato   restano solo `esiti/<id>.json` (stato e data, nessun dato personale) per 30 giorni e una riga in
               `storico.jsonl` (comune, regione, formato, data, esito)

Rifiuta (api): la cartella della richiesta si cancella subito.

Nessun dato personale è chiesto all'utente (solo comune e regione); l'IP non si scrive nella richiesta (i limiti per IP
sono quelli in memoria di servizio/protezione.py). Le funzioni in testa (costanti, nomi, richiesta, controllo dello zip)
usano solo la libreria standard: l'api le importa senza GDAL.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import unicodedata
import zipfile
from pathlib import Path

log = logging.getLogger("edifici3d.coda")

# ------------------------------------------------------------------------------------------------ costanti comuni
# regioni della prima versione: chiave del sito → TOML della zona (fonti/), codice ISTAT della regione, formato
REGIONI = {
    "er": {"nome": "Emilia-Romagna", "toml": "emilia_romagna", "istat": "08", "sperimentale": False,
           "fonte": "DBTR – Unità volumetrica (UVL)"},
    "lom": {"nome": "Lombardia", "toml": "lombardia", "istat": "03", "sperimentale": True,
            "fonte": "DBGT – Unità volumetrica (classe 020101)"},
    "fvg": {"nome": "Friuli Venezia Giulia", "toml": "friuli_venezia_giulia", "istat": "06", "sperimentale": True,
            "fonte": "CTRN – Edificato"},
    "lig": {"nome": "Liguria", "toml": "liguria", "istat": "07", "sperimentale": True,
            "fonte": "CTR 1:5000 3D – Edificato"},
}
STATI = ("caricamento", "ricevuto", "in preparazione", "in attesa di approvazione", "controlli non superati",
         "approvato", "installato", "rifiutato")
FORMATI = ("zip", "gpkg")
ID = re.compile(r"[0-9a-f]{32}")
# estrazione sicura dello zip
ESTENSIONI_DATI = {".gpkg", ".shp", ".shx", ".dbf", ".prj", ".cpg", ".geojson", ".json"}
ESTENSIONI_META = {".xml", ".txt"}
MAX_VOCI = 2000
MAX_ESTRATTO = 3 * 1024 ** 3          # 3 GB estratti al massimo (un GeoPackage di Bologna ~200 MB)
MAX_RAPPORTO = 200                    # compressione oltre 200:1 su una voce grande = bomba
MAX_ANNIDATI = 1                      # uno zip dentro lo zip (pacchetti del portale), non di più
GPKG_TESTA = b"SQLite format 3\x00"
ZIP_TESTA = (b"PK\x03\x04", b"PK\x05\x06")
GIORNI_ESITI = 30
ORE_CARICAMENTO = 6                   # caricamenti lasciati a metà: cancellati dopo 6 ore


class FileNonValido(ValueError):
    """File rifiutato: il messaggio si può mostrare all'utente."""


def slug(nome: str) -> str:
    """«Montescudo-Monte Colombo» → «montescudo-monte-colombo» (nome della cartella dell'archivio)."""
    s = unicodedata.normalize("NFKD", str(nome or "")).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40].strip("-")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,40}", s or "") or s in ("prodotti", "grezzi", "lidar"):
        raise FileNonValido("nome del comune non valido")
    return s


def nome_comune(nome: str) -> str:
    n = re.sub(r"\s+", " ", str(nome or "")).strip()
    if not (2 <= len(n) <= 60) or not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿčšžČŠŽ' .\-/]*", n) or ".." in n:
        raise FileNonValido("nome del comune non valido (solo lettere, spazi, apostrofi e trattini; 2–60 caratteri)")
    return n


def adesso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def cartella_richiesta(coda: Path, rid: str) -> Path:
    if not ID.fullmatch(str(rid or "")):
        raise FileNonValido("richiesta inesistente")
    return Path(coda) / rid


def leggi_richiesta(coda: Path, rid: str) -> dict | None:
    p = cartella_richiesta(coda, rid) / "richiesta.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def scrivi_richiesta(coda: Path, r: dict) -> dict:
    d = cartella_richiesta(coda, r["id"])
    d.mkdir(parents=True, exist_ok=True)
    r["aggiornata"] = adesso()
    tmp = d / "richiesta.json.tmp"
    tmp.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(d / "richiesta.json")
    return r


def richieste(coda: Path) -> list[dict]:
    out = []
    for d in sorted(Path(coda).iterdir()) if Path(coda).is_dir() else []:
        if d.is_dir() and ID.fullmatch(d.name):
            r = leggi_richiesta(coda, d.name)
            if r:
                out.append(r)
    out.sort(key=lambda r: (r.get("creata", ""), r.get("t", 0)))
    return out


def scrivi_esito(coda: Path, rid: str, stato_finale: str, r: dict | None = None) -> None:
    """Esito finale (installato o rifiutato) per l'utente e riga dello storico; nessun dato personale."""
    e = Path(coda) / "esiti"
    e.mkdir(parents=True, exist_ok=True)
    riga = {"id": rid, "stato": stato_finale, "data": adesso()}
    if r:
        riga.update({k: r.get(k) for k in ("regione", "comune", "formato", "dimensione", "creata")})
        if r.get("esito"):
            riga["corpi"] = r["esito"].get("corpi")
    (e / f"{rid}.json").write_text(json.dumps({"id": rid, "stato": stato_finale, "data": riga["data"]}), encoding="utf-8")
    with open(Path(coda) / "storico.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(riga, ensure_ascii=False) + "\n")


def leggi_esito(coda: Path, rid: str) -> dict | None:
    if not ID.fullmatch(str(rid or "")):
        return None
    try:
        return json.loads((Path(coda) / "esiti" / f"{rid}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ------------------------------------------------------------------------------------------------ zip sicuro
def _nome_sicuro(nome: str) -> str:
    """Percorso relativo pulito dentro lo zip; FileNonValido per percorsi assoluti, «..», unità di Windows, NUL."""
    if "\x00" in nome:
        raise FileNonValido("nome di file non valido nello zip")
    n = nome.replace("\\", "/")
    if n.startswith("/") or re.match(r"^[A-Za-z]:", n) or any(p == ".." for p in n.split("/")):
        raise FileNonValido(f"percorso non ammesso nello zip: {nome[:80]}")
    parti = [p for p in n.split("/") if p not in ("", ".")]
    return "/".join(parti)


def _e_link(info: zipfile.ZipInfo) -> bool:
    modo = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(modo)


def controlla_zip(percorso: Path, livello: int = 0) -> dict:
    """Controllo leggero (api e coda) senza estrarre: voci, percorsi, link simbolici, bombe, estensioni.
    Restituisce {"voci", "dati", "meta", "ignorati", "estratto"}; FileNonValido se il file è da rifiutare."""
    try:
        z = zipfile.ZipFile(percorso)
    except (zipfile.BadZipFile, OSError) as e:
        raise FileNonValido(f"zip non leggibile ({type(e).__name__})")
    with z:
        voci = z.infolist()
        if len(voci) > MAX_VOCI:
            raise FileNonValido(f"troppe voci nello zip ({len(voci)}, massimo {MAX_VOCI})")
        tot, dati, meta, ignorati, annidati = 0, [], [], [], []
        for i in voci:
            n = _nome_sicuro(i.filename)
            if _e_link(i):
                raise FileNonValido(f"collegamento simbolico nello zip: {n[:80]}")
            if i.is_dir() or not n:
                continue
            if i.flag_bits & 0x1:
                raise FileNonValido("zip cifrato con password: non si può leggere")
            tot += i.file_size
            if tot > MAX_ESTRATTO:
                raise FileNonValido("contenuto dello zip troppo grande una volta estratto (oltre 3 GB)")
            if i.file_size > 50 * 1024 ** 2 and i.compress_size and i.file_size / i.compress_size > MAX_RAPPORTO:
                raise FileNonValido(f"compressione anomala nello zip ({n[:60]}): file rifiutato")
            ext = Path(n).suffix.lower()
            if ext in ESTENSIONI_DATI:
                dati.append(n)
            elif ext in ESTENSIONI_META:
                meta.append(n)
            elif ext == ".zip" and livello < MAX_ANNIDATI:
                annidati.append(n)
            else:
                ignorati.append(n)
        if not dati and not annidati:
            raise FileNonValido("nello zip non c'è né un GeoPackage (.gpkg) né uno Shapefile (.shp/.dbf/.shx)")
        return {"voci": len(voci), "dati": dati, "meta": meta, "ignorati": ignorati[:50], "annidati": annidati,
                "estratto": tot}


def controlla_file(percorso: Path) -> dict:
    """Tipo del file caricato dalle prime righe (mai dall'estensione): GeoPackage o zip; altrimenti FileNonValido."""
    with open(percorso, "rb") as f:
        testa = f.read(16)
    if testa.startswith(GPKG_TESTA):
        return {"formato": "gpkg"}
    if testa[:4] in ZIP_TESTA:
        return {"formato": "zip", **controlla_zip(percorso)}
    raise FileNonValido("il file non è né uno zip né un GeoPackage")


def estrai_sicuro(percorso: Path, dest: Path, livello: int = 0) -> dict:
    """Estrae solo i file attesi (dati e metadati) in `dest`, con i limiti di controlla_zip ricontrollati durante la
    scrittura (dimensione reale, non quella dichiarata). Un GeoPackage caricato da solo si copia come dati.gpkg."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    tipo = controlla_file(percorso) if livello == 0 else {"formato": "zip", **controlla_zip(percorso, livello)}
    if tipo["formato"] == "gpkg":
        shutil.copyfile(percorso, dest / "dati.gpkg")
        return {"formato": "gpkg", "file": ["dati.gpkg"], "ignorati": []}
    scritti, tot = [], 0
    radice = dest.resolve()
    with zipfile.ZipFile(percorso) as z:
        for i in z.infolist():
            n = _nome_sicuro(i.filename)
            if i.is_dir() or not n:
                continue
            ext = Path(n).suffix.lower()
            if ext not in ESTENSIONI_DATI | ESTENSIONI_META and not (ext == ".zip" and livello < MAX_ANNIDATI):
                continue
            uscita = (dest / n).resolve()
            if radice not in uscita.parents:
                raise FileNonValido(f"percorso non ammesso nello zip: {n[:80]}")
            uscita.parent.mkdir(parents=True, exist_ok=True)
            letti = 0
            with z.open(i) as src, open(uscita, "wb") as out:
                while True:
                    b = src.read(1 << 20)
                    if not b:
                        break
                    letti += len(b)
                    tot += len(b)
                    if letti > i.file_size + 1024 or tot > MAX_ESTRATTO:
                        raise FileNonValido("contenuto dello zip più grande di quanto dichiarato: file rifiutato")
                    out.write(b)
            if ext == ".zip":
                sotto = estrai_sicuro(uscita, uscita.with_suffix(""), livello + 1)
                scritti += [f"{Path(n).with_suffix('').as_posix()}/{x}" for x in sotto["file"]]
                uscita.unlink()
            else:
                scritti.append(n)
    return {"formato": "zip", "file": scritti, "ignorati": tipo.get("ignorati", [])}


# ------------------------------------------------------------------------------------------------ controlli
PERSONALI_COLONNE = re.compile(r"(?i)^(cognome|nominativ|intestat|propriet|cod(ice)?_?fisc|c_?f$|cf$|partita_?iva|p_?iva|"
                               r"e_?mail|telefon|cellulare|titolare|possessor|residen|nato_|data_?nascita)")
CF = re.compile(r"\b[A-Z]{6}\d{2}[A-EHLMPR-T]\d{2}[A-Z]\d{3}[A-Z]\b")
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
METADATI_LICENZE = re.compile(r"(?i)(CC[ -]?BY(?:[ -]SA)?[ -]?\d\.\d|Creative Commons[^<\n]{0,60}|IODL ?2\.0)")


def trova_sorgente(cartella: Path, regione: str) -> dict:
    """GeoPackage o Shapefile da leggere nella cartella estratta (fino a 3 livelli)."""
    cartella = Path(cartella)
    gpkg = sorted(p for p in cartella.rglob("*.gpkg") if len(p.relative_to(cartella).parts) <= 4)
    shp = sorted(p for p in cartella.rglob("*.shp") if len(p.relative_to(cartella).parts) <= 4)
    gj = sorted(p for p in cartella.rglob("*.geojson") if len(p.relative_to(cartella).parts) <= 4)
    if regione == "er":
        import pyogrio
        for g in gpkg:
            try:
                if any(str(n) in ("V_UVL_GPG", "UVL_Unita_volumetrica", "UVL_GPG") for n, _ in pyogrio.list_layers(str(g))):
                    return {"tipo": "gpkg", "percorso": g}
            except Exception:  # noqa: BLE001
                continue
        for s in shp:
            if s.stem.upper() == "V_UVL_GPG":
                return {"tipo": "shp", "percorso": s.parent}
        raise FileNonValido("manca lo strato delle unità volumetriche V_UVL_GPG (GeoPackage o Shapefile)")
    if gpkg:
        return {"tipo": "gpkg", "percorso": gpkg[0]}
    if shp:
        # il più grande: di solito lo strato degli edifici (i pacchetti hanno anche strati accessori)
        return {"tipo": "shp", "percorso": max(shp, key=lambda p: p.stat().st_size)}
    if gj:
        return {"tipo": "geojson", "percorso": gj[0]}
    raise FileNonValido("nessun GeoPackage, Shapefile o GeoJSON nel file")


def _riquadro_wgs84(geoms, crs) -> list | None:
    from pyproj import Transformer
    b = [g.bounds for g in geoms if g is not None and not g.is_empty]
    if not b:
        return None
    x0, y0 = min(x[0] for x in b), min(x[1] for x in b)
    x1, y1 = max(x[2] for x in b), max(x[3] for x in b)
    t = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    xs, ys = zip(*(t.transform(x, y) for x, y in ((x0, y0), (x0, y1), (x1, y0), (x1, y1))))
    return [round(min(xs), 5), round(min(ys), 5), round(max(xs), 5), round(max(ys), 5)]


def _dati_personali(percorso: Path) -> list[str]:
    """Colonne con nomi da dato personale e valori che sembrano codici fiscali o email (su un campione di ogni strato)."""
    import pyogrio
    import pyogrio.raw as R
    trovati = []
    try:
        strati = [str(n) for n, _ in pyogrio.list_layers(str(percorso))]
    except Exception:  # noqa: BLE001
        return trovati
    for s in strati[:20]:
        try:
            meta, _f, _g, campi = R.read(str(percorso), layer=s, read_geometry=False, max_features=3000)
        except Exception:  # noqa: BLE001
            continue
        for nome, valori in zip(meta["fields"], campi):
            if PERSONALI_COLONNE.search(str(nome)):
                trovati.append(f"{s}.{nome}: nome di colonna da dato personale")
            testi = [str(v) for v in list(valori)[:3000] if isinstance(v, str)]
            if any(CF.search(t) for t in testi):
                trovati.append(f"{s}.{nome}: valori che sembrano codici fiscali")
            elif any(EMAIL.search(t) for t in testi):
                trovati.append(f"{s}.{nome}: valori che sembrano indirizzi email")
    return trovati


def _metadati(cartella: Path, regione: str) -> dict:
    """Metadati della Regione (XML dell'estrazione), letti come testo (nessun parser XML: niente entità esterne)."""
    nome = REGIONI[regione]["nome"]
    out = {"file": 0, "regione_citata": False, "licenze": []}
    for p in sorted(Path(cartella).rglob("*.xml"))[:10]:
        try:
            t = p.read_bytes()[:2_000_000].decode("utf-8", errors="replace")
        except OSError:
            continue
        out["file"] += 1
        if nome.lower().split("-")[0] in t.lower():
            out["regione_citata"] = True
        out["licenze"] += [m.strip() for m in METADATI_LICENZE.findall(t)]
    out["licenze"] = sorted(set(out["licenze"]))[:6]
    return out


def _crs_er_ok(crs) -> bool:
    """EPSG:7791 (RDN2008 / UTM 32N), o un equivalente pratico (ETRS89 o WGS84 / UTM 32N)."""
    from pyproj import CRS
    try:
        c = CRS.from_user_input(crs)
    except Exception:  # noqa: BLE001
        return False
    if c.equals(CRS.from_epsg(7791), ignore_axis_order=True):
        return True
    e = c.to_epsg(min_confidence=60)
    if e in (7791, 6707, 25832, 32632):
        return True
    try:  # .prj ESRI «RDN2008_UTM_zone_32N»: stessa proiezione, nome diverso
        return c.is_projected and "utm" in c.name.lower() and "32n" in c.name.lower().replace(" ", "")
    except Exception:  # noqa: BLE001
        return False


def controlla(cartella: Path, regione: str) -> dict:
    """Controlli automatici sui file estratti. «problemi» vuoto = si può preparare."""
    from . import fonti as F, uvl as U
    if regione not in REGIONI:
        raise FileNonValido("regione non prevista")
    zona = F.carica_zona(REGIONI[regione]["toml"])
    problemi, avvisi = [], []
    src = trova_sorgente(cartella, regione)
    esito = {"sorgente": {"tipo": src["tipo"], "nome": Path(src["percorso"]).name}, "problemi": problemi, "avvisi": avvisi}
    import pyogrio
    esito["strati"] = [str(n) for n, _ in pyogrio.list_layers(str(src["percorso"]))][:30]
    if regione == "er":
        righe, geoms, meta = U._leggi(src["percorso"], U.strato_uvl(src["percorso"]))
        crs = meta.get("crs")
        esito["crs"] = crs
        if not crs or not _crs_er_ok(crs):
            problemi.append(f"sistema di riferimento inatteso ({str(crs)[:60]}): il DBTR è in EPSG:7791 (RDN2008 / UTM 32N)")
        mancanti = [c for c in ("ID_E", "EDI_ID_E", "H_UVL", "B_UVL") if c not in meta["fields"]]
        if mancanti:
            problemi.append("colonne mancanti in V_UVL_GPG: " + ", ".join(mancanti))
        if "V_EDI_GPG" not in esito["strati"]:
            avvisi.append("manca lo strato Edificio (V_EDI_GPG): niente foglio, numero, nome e destinazione")
        if "V_EDI_CT_USO_AVM" not in esito["strati"]:
            avvisi.append("manca la destinazione d'uso (V_EDI_CT_USO_AVM)")
        if not mancanti:
            ctl = U.controlla(righe)
            esito["controllo"] = {k: ctl[k] for k in ("corpi", "edifici", "altezza", "gronda", "tipi_altezza", "colmi", "domande", "mancanti")}
            esito["convenzione"] = U.convenzione(righe)
            edi = U.leggi_edifici(src["percorso"])
            comuni = sorted({str(e.get("COD_COM")) for e in edi.values() if e.get("COD_COM")})
            esito["comuni_catastali"] = comuni[:20]
            if len(comuni) > 3:
                avvisi.append(f"{len(comuni)} comuni catastali nel file: più comuni insieme o un'estrazione di confine")
        geoms_crs = (geoms, crs)
    else:
        from . import regionali as RG
        righe, crs = RG.leggi_file(src["percorso"])
        ad = RG.scegli_adattatore(zona["fonti"]["edifici"], righe)       # FVG: edizione 2 o 1 secondo i campi (08/11/2026)
        esito["crs"] = crs
        if not crs:
            problemi.append("il file non dichiara il sistema di riferimento (manca il .prj?)")
        ctl = RG.controlla(righe, ad)
        esito["controllo"] = ctl
        if ctl["mancanti"]:
            problemi.append(f"colonne attese mancanti per {REGIONI[regione]['fonte']}: " + ", ".join(ctl["mancanti"]))
        if ad.serve_dtm and not dtm_regione(regione):
            problemi.append("le altezze della CTR 3D ligure si ricavano dal DTM regionale, che non è ancora sul server")
        geoms_crs = ([g for _, g in righe], crs)
    try:
        riq = _riquadro_wgs84(*geoms_crs) if geoms_crs[1] else None
    except Exception:  # noqa: BLE001
        riq = None
    esito["riquadro"] = riq
    rz = zona["zona"].get("riquadro")
    if riq and rz:
        m = 0.05
        dentro = riq[0] >= rz[0] - m and riq[1] >= rz[1] - m and riq[2] <= rz[2] + m and riq[3] <= rz[3] + m
        esito["dentro_regione"] = dentro
        if not dentro:
            problemi.append(f"il riquadro dei dati {riq} esce dalla regione dichiarata ({REGIONI[regione]['nome']})")
        lato = max(riq[2] - riq[0], riq[3] - riq[1])
        if lato > 1.2:
            avvisi.append(f"riquadro molto grande ({lato:.1f}°): più di un comune?")
    elif not riq:
        problemi.append("riquadro dei dati non calcolabile (geometrie vuote o sistema di riferimento sconosciuto)")
    esito["metadati"] = _metadati(cartella, regione)
    if esito["metadati"]["file"] and not esito["metadati"]["regione_citata"]:
        avvisi.append("i metadati XML non citano la Regione dichiarata")
    per = _dati_personali(src["percorso"])
    esito["dati_personali"] = per
    if per:
        problemi.append("possibili dati personali: " + "; ".join(per[:5]))
    esito["_percorso"] = str(src["percorso"])
    return esito


def dtm_regione(regione: str, archivio: Path | None = None) -> list[Path]:
    """DTM sul server per la preparazione: ER = quadranti del DTM 5 m in cc-by/er/grezzi/dtm5/ (o CODA_DTM_ER);
    Liguria = GeoTIFF in cc-by/lig/grezzi/dtm/ (o CODA_DTM_LIG); le altre regioni non lo usano."""
    env = os.environ.get(f"CODA_DTM_{regione.upper()}", "").strip()
    if env:
        return [Path(x) for x in env.split(",") if Path(x).exists()]
    base = Path(archivio or os.environ.get("CODA_ARCHIVIO", "/dati/edifici"))
    if regione == "er":
        return sorted((base / "cc-by/er/grezzi/dtm5").glob("DTM5x5_*_7791.zip"))
    if regione == "lig":
        return sorted((base / "cc-by/lig/grezzi/dtm").glob("*.tif"))
    return []


# ------------------------------------------------------------------------------------------------ preparazione
def _limiti_figlio():  # pragma: no cover - eseguita nel processo figlio
    os.nice(15)
    try:
        import resource
        g = int(float(os.environ.get("CODA_MEMORIA_GB", "3.5")) * 1024 ** 3)
        resource.setrlimit(resource.RLIMIT_AS, (g, g))
    except (ImportError, ValueError, OSError):
        pass


def _esegui(argomenti: list[str], registro: Path, timeout: float) -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1]) + os.pathsep + env.get("PYTHONPATH", "")
    with open(registro, "a", encoding="utf-8") as reg:
        reg.write(f"$ edifici3d {' '.join(argomenti)}\n")
        reg.flush()
        p = subprocess.run([sys.executable, "-m", "edifici3d", *argomenti], stdout=reg, stderr=subprocess.STDOUT,
                           timeout=timeout, env=env, preexec_fn=_limiti_figlio if os.name == "posix" else None)
    return p.returncode


def anteprima(prodotti: Path, dest: Path, massimo: int = 15000) -> int:
    """GeoJSON leggero dei corpi preparati (gronda e colmo), per la mappa della pagina interna."""
    visti = {}
    for c in sorted((Path(prodotti) / "contesto").glob("*.json")):
        for f in json.loads(c.read_text(encoding="utf-8"))["features"]:
            visti.setdefault(f["properties"]["id"], f)
    fs = list(visti.values())
    passo = max(1, -(-len(fs) // massimo))
    r = lambda c: [r(x) for x in c] if isinstance(c[0], list) else [round(c[0], 6), round(c[1], 6)]
    out = [{"type": "Feature", "geometry": {"type": f["geometry"]["type"], "coordinates": r(f["geometry"]["coordinates"])},
            "properties": {"g": f["properties"].get("gronda"), "c": f["properties"].get("colmo"),
                           "e": f["properties"].get("edificio")}} for f in fs[::passo]]
    dest.write_text(json.dumps({"type": "FeatureCollection", "features": out, "totale": len(fs), "passo": passo},
                               separators=(",", ":")), encoding="utf-8")
    return len(out)


def _sospetti(prodotti: Path) -> list[dict]:
    """Corpi piccoli e altissimi (sotto 30 m², oltre 40 m) **rimasti** dopo la regola di plausibilità di `prepara`
    (plausibilita.py, 07/11/2026: le altezze non plausibili sono già portate alla stima; restano campanili, torri,
    ciminiere). Solo segnalati a chi approva."""
    out, visti = [], set()
    for c in sorted((Path(prodotti) / "contesto").glob("*.json")):
        for f in json.loads(c.read_text(encoding="utf-8"))["features"]:
            p = f["properties"]
            if p["id"] in visti:
                continue
            visti.add(p["id"])
            if (p.get("area") or 0) < 30 and (p.get("gronda") or 0) > 40 and p.get("h_dbtr_scartata") is None:
                out.append({k: p.get(k) for k in ("id", "area", "gronda", "foglio", "numero")})
    return out


def prepara(coda: Path, rid: str, archivio: Path) -> dict:
    """Prepara una richiesta «ricevuto»: estrazione, controlli, prepara, controllo dell'archivio, anteprima."""
    from .__main__ import controlla_archivio
    d = cartella_richiesta(coda, rid)
    r = leggi_richiesta(coda, rid)
    if not r or r.get("stato") != "ricevuto":
        return r or {}
    r["stato"] = "in preparazione"
    r["preparazione_inizio"] = adesso()
    scrivi_richiesta(coda, r)
    t0 = time.time()
    lavoro = d / "lavoro"
    shutil.rmtree(lavoro, ignore_errors=True)
    shutil.rmtree(d / "archivio", ignore_errors=True)
    registro = d / "registro.txt"
    regione = r["regione"]
    try:
        est = estrai_sicuro(d / "caricato.bin", lavoro)
        ctl = controlla(lavoro, regione)
        ctl["file_estratti"] = len(est["file"])
        ctl["file_ignorati"] = est.get("ignorati", [])[:20]
        percorso = ctl.pop("_percorso")
        r["controlli"] = ctl
        if ctl["problemi"]:
            r["stato"] = "controlli non superati"
            return r
        zc = REGIONI[regione]
        dtm = dtm_regione(regione, archivio)
        nome_arch = (f"DBTR Emilia-Romagna – {r['comune']}" if regione == "er" else f"{zc['nome']} – {r['comune']}")
        uscita = d / "archivio"
        if regione == "er":
            arg = ["prepara", "--comune", r["comune_slug"], "--nome", nome_arch, "--gpkg", percorso, "--archivio", str(uscita)]
        else:
            arg = ["--zona", zc["toml"], "prepara-regione", "--file", percorso, "--archivio", str(uscita),
                   "--comune", r["comune_slug"], "--nome", nome_arch]
        if r.get("istat") and r.get("intero"):
            arg += ["--istat", r["istat"]]
        else:
            arg += ["--parziale"]
        timeout = float(os.environ.get("CODA_MINUTI", "120")) * 60
        codice = _esegui(arg + (["--dtm", *map(str, dtm)] if dtm else []), registro, timeout)
        if codice != 0 and dtm and regione == "er":
            # DTM che non copre il comune o non leggibile: si rifà con la quota della base del DBTR (B_UVL), dichiarato
            ctl["avvisi"].append("DTM del server non utilizzabile per questo comune: terreno dalla base del DBTR (B_UVL)")
            codice = _esegui(arg, registro, timeout)
        if codice != 0:
            r["stato"] = "controlli non superati"
            ctl["problemi"].append(f"preparazione non riuscita (codice {codice}): vedi registro")
            return r
        zona_cod = {"er": "er", "lom": "lom", "fvg": "fvg", "lig": "lig"}[regione]
        prodotti = uscita / "cc-by" / zona_cod / r["comune_slug"] / "prodotti"
        qa = controlla_archivio(prodotti)
        n_ant = anteprima(prodotti, d / "anteprima.geojson")
        sospetti = _sospetti(prodotti)
        letti = (ctl.get("controllo") or {}).get("corpi") or (ctl.get("controllo") or {}).get("oggetti")
        r["esito"] = {k: qa.get(k) for k in ("nome", "corpi", "edifici", "riquadro", "gronda_m", "a_capanna", "con_cortile",
                                              "con_foglio_numero", "con_destinazione", "fonti_altezza", "altezze_stimate", "mb",
                                              "problemi", "avvisi")}
        r["esito"]["letti"] = letti
        r["esito"]["scartati"] = (letti - qa["corpi"]) if isinstance(letti, int) and isinstance(qa.get("corpi"), int) else None
        r["esito"]["convenzione"] = ctl.get("convenzione")
        r["esito"]["dtm"] = bool(dtm) and not any("DTM del server" in a for a in ctl["avvisi"])
        r["esito"]["anteprima_corpi"] = n_ant
        r["esito"]["percorso"] = f"cc-by/{zona_cod}/{r['comune_slug']}/"
        r["esito"]["sostituisce"] = (Path(archivio) / "cc-by" / zona_cod / r["comune_slug"] / "prodotti" / "indice.json").exists()
        # la mediana fuori da 4–15 m è un'anomalia da guardare (centri storici, zone industriali, file piccoli), non un blocco
        bloccanti = [x for x in qa.get("problemi") or [] if not x.startswith("mediana della gronda")]
        r["esito"]["anomalie"] = [x for x in qa.get("problemi") or [] if x not in bloccanti] + list(qa.get("avvisi") or [])
        if sospetti:
            r["esito"]["sospetti"] = sospetti[:20]
            r["esito"]["anomalie"].append(f"{len(sospetti)} corpi sotto 30 m² e oltre 40 m di tipo verticale (campanili, torri, "
                                          "ciminiere): da guardare (solo segnalati)")
        if qa.get("altezze_stimate"):
            r["esito"]["anomalie"].append(f"{qa['altezze_stimate']} corpi con altezza del DBTR non plausibile portati alla stima "
                                          "(h_dbtr_scartata nei corpi)")
        r["stato"] = "controlli non superati" if bloccanti else "in attesa di approvazione"
        return r
    except FileNonValido as e:
        r["stato"] = "controlli non superati"
        r.setdefault("controlli", {"problemi": [], "avvisi": []})["problemi"].append(str(e))
        return r
    except subprocess.TimeoutExpired:
        r["stato"] = "controlli non superati"
        r.setdefault("controlli", {"problemi": [], "avvisi": []})["problemi"].append("preparazione troppo lunga: interrotta")
        return r
    except Exception as e:  # noqa: BLE001
        log.exception("preparazione di %s non riuscita", rid)
        r["stato"] = "controlli non superati"
        r.setdefault("controlli", {"problemi": [], "avvisi": []})["problemi"].append(
            f"file non leggibile o preparazione non riuscita ({type(e).__name__}: {str(e)[:160]})")
        return r
    finally:
        shutil.rmtree(lavoro, ignore_errors=True)
        r["secondi"] = round(time.time() - t0, 1)
        r["preparazione_fine"] = adesso()
        scrivi_richiesta(coda, r)


# ------------------------------------------------------------------------------------------------ installazione
def installa(coda: Path, rid: str, archivio: Path, copie: int = 2) -> dict:
    """Richiesta «approvato» → archivio in <archivio>/cc-by/<zona>/<comune>/, precedente in _precedenti/, archivi.json."""
    from .archivi import scrivi_archivi_json
    d = cartella_richiesta(coda, rid)
    r = leggi_richiesta(coda, rid)
    if not r or r.get("stato") != "approvato":
        return r or {}
    rel = r["esito"]["percorso"].strip("/")
    sorg = d / "archivio" / rel
    if not (sorg / "prodotti" / "indice.json").is_file():
        r["stato"] = "controlli non superati"
        r.setdefault("controlli", {"problemi": [], "avvisi": []})["problemi"].append("archivio preparato non trovato")
        return scrivi_richiesta(coda, r)
    dest = Path(archivio) / rel
    if dest.exists():
        prec = Path(archivio) / "_precedenti"
        prec.mkdir(parents=True, exist_ok=True)
        chiave = rel.replace("/", "-")
        shutil.move(str(dest), str(prec / f"{chiave}-{time.strftime('%Y%m%d-%H%M%S')}"))
        vecchie = sorted(prec.glob(f"{chiave}-2*"))
        for v in vecchie[:-copie]:
            shutil.rmtree(v, ignore_errors=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(sorg), str(dest))
    scrivi_archivi_json(Path(archivio))
    scrivi_esito(coda, rid, "installato", r)
    shutil.rmtree(d, ignore_errors=True)
    log.info("archivio %s installato in %s", rid, rel)
    return {**r, "stato": "installato"}


def ripristina(archivio: Path, zona: str, comune: str) -> dict:
    """Torna all'archivio precedente di un comune (l'attuale va in _precedenti/), poi archivi.json."""
    from .archivi import scrivi_archivi_json
    rel = f"cc-by/{zona}/{slug(comune)}"
    prec = sorted((Path(archivio) / "_precedenti").glob(f"{rel.replace('/', '-')}-2*"))
    if not prec:
        raise FileNonValido(f"nessuna copia precedente di {rel}")
    dest = Path(archivio) / rel
    if dest.exists():
        shutil.move(str(dest), str(Path(archivio) / "_precedenti" / f"{rel.replace('/', '-')}-{time.strftime('%Y%m%d-%H%M%S')}-sostituita"))
    shutil.move(str(prec[-1]), str(dest))
    return {"ripristinato": rel, "da": prec[-1].name, "archivi": len(scrivi_archivi_json(Path(archivio))["archivi"])}


# ------------------------------------------------------------------------------------------------ ciclo
def pulizia(coda: Path, ora: float | None = None) -> int:
    """Caricamenti lasciati a metà oltre 6 ore ed esiti oltre 30 giorni."""
    ora = time.time() if ora is None else ora
    n = 0
    for d in Path(coda).iterdir() if Path(coda).is_dir() else []:
        if d.is_dir() and ID.fullmatch(d.name):
            r = leggi_richiesta(coda, d.name)
            if (r is None or r.get("stato") == "caricamento") and ora - d.stat().st_mtime > ORE_CARICAMENTO * 3600:
                shutil.rmtree(d, ignore_errors=True)
                n += 1
    for e in (Path(coda) / "esiti").glob("*.json") if (Path(coda) / "esiti").is_dir() else []:
        if ora - e.stat().st_mtime > GIORNI_ESITI * 86400:
            e.unlink(missing_ok=True)
    return n


def _fuori_finestra(finestra: str | None, ora: time.struct_time | None = None) -> bool:
    """Vero se adesso è nella finestra in cui non si prepara (es. «03:15-07:00», la pipeline LiDAR)."""
    if not finestra:
        return False
    ora = ora or time.localtime()
    a, b = finestra.split("-")
    m = ora.tm_hour * 60 + ora.tm_min
    ma = int(a[:2]) * 60 + int(a[3:5])
    mb = int(b[:2]) * 60 + int(b[3:5])
    return ma <= m < mb if ma <= mb else (m >= ma or m < mb)


def previsioni_in_corso(url: str | None) -> int:
    if not url:
        return 0
    try:
        import httpx
        return int(httpx.get(url, timeout=3).json().get("previsioni_in_corso") or 0)
    except Exception:  # noqa: BLE001
        return 0


def un_giro(coda: Path, archivio: Path, pausa_url: str | None = None, finestra: str | None = None) -> dict:
    """Un passo: pulizia, installazione delle approvate, poi al più UNA preparazione (la più vecchia)."""
    coda = Path(coda)
    coda.mkdir(parents=True, exist_ok=True)
    esito = {"puliti": pulizia(coda), "installati": [], "preparato": None}
    tutte = richieste(coda)
    for r in tutte:
        if r.get("stato") == "approvato":
            esito["installati"].append(installa(coda, r["id"], archivio).get("stato"))
    for r in tutte:
        if r.get("stato") == "in preparazione":       # interrotta (container riavviato): si riprova da capo
            r["stato"] = "ricevuto"
            scrivi_richiesta(coda, r)
    da_fare = [r for r in richieste(coda) if r.get("stato") == "ricevuto"]
    if not da_fare:
        return esito
    if _fuori_finestra(finestra):
        esito["attesa"] = f"finestra {finestra}"
        return esito
    if previsioni_in_corso(pausa_url) > 0:
        esito["attesa"] = "previsione in corso sul server"
        return esito
    esito["preparato"] = prepara(coda, da_fare[0]["id"], archivio).get("stato")
    return esito


def ciclo(coda: Path, archivio: Path, pausa_url: str | None, finestra: str | None, attesa: float = 60.0) -> None:  # pragma: no cover
    import fcntl
    Path(coda).mkdir(parents=True, exist_ok=True)
    with open(Path(coda) / ".coda.lock", "w") as blocco:
        fcntl.flock(blocco, fcntl.LOCK_EX)              # una sola coda per server
        log.info("coda «Aggiungi DBTR» avviata: %s → %s", coda, archivio)
        while True:
            try:
                e = un_giro(coda, archivio, pausa_url, finestra)
                if e["installati"] or e["preparato"] or e["puliti"]:
                    log.info("giro della coda: %s", e)
            except Exception:  # noqa: BLE001
                log.exception("giro della coda non riuscito")
            time.sleep(attesa)
