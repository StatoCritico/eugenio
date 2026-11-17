"""Immobili delle Pubbliche Amministrazioni (censimento MEF) con i confini della particella catastale (AdE).

Due fonti aperte, entrambe CC BY 4.0, unite per identificativo catastale:

1. **MEF – Dipartimento dell'Economia, progetto «Patrimonio della PA»** (art. 2, c. 222, L. 191/2009): elenco dei
   beni immobili (fabbricati e terreni) dichiarati dalle Amministrazioni. Ultimo anno pubblicato (verifica del
   17/11/2026): **dati al 31/12/2023**, rilevazione aprile-dicembre 2024, 3,26 milioni di righe in 31 ZIP (per
   tipologia di amministrazione e, per i Comuni, per regione). Pagina:
   https://www.de.mef.gov.it/it/attivita_istituzionali/patrimonio_pubblico/censimento_immobili_pubblici/open_data_immobili/dati_immobili_2023.html
   CSV con `;`, virgolette, codifica Windows-1252, virgola decimale, a capo dentro i campi. Il MEF dà un **punto**
   (centroide della particella fornito dall'Agenzia delle Entrate, oppure indirizzo, oppure posizione scelta
   dall'utente) e l'**identificativo catastale** `comune:sezione:[sez. urbana:]foglio:particella:denominatore:
   [tipo:]subalterno` (più identificativi separati da `;` per le unità graffate). **Non dà poligoni.**
2. **Agenzia delle Entrate – download massivo della cartografia catastale** (particelle, INSPIRE CadastralParcel):
   https://wfs-download.cartografia.agenziaentrate.eu/wfsdownload/<REGIONE>.zip (19 regioni, 14,7 GB in tutto;
   versione del 22-23/09/2026). ZIP regione → ZIP provincia → ZIP comune → `<COD>_<NOME>_ple.gml` (particelle) e
   `_map.gml` (fogli). EPSG:6706 con ordine **lat lon**. Riferimento: `NATIONALCADASTRALREFERENCE` =
   `<comune 4><sezione 1 o «_»><foglio 4><allegato><sviluppo>.<particella>` (es. `A045_000100.1`,
   `F363A001300.100`). Il Trentino-Alto Adige non c'è (catasto tavolare delle Province autonome).

L'aggancio usa (comune, sezione, foglio, particella): il poligono è quello della **particella**, quindi per un
fabbricato è il lotto dell'edificio (ente urbano), non la sagoma; più unità immobiliari della stessa particella
condividono lo stesso poligono. Nei comuni con sezioni urbane diverse da quelle censuarie l'aggancio può mancare.

La lettura dei GML è fatta «a flusso» (ricerca dei tag sui byte): si costruisce il poligono solo per le particelle
del censimento, ~20 volte più veloce di GDAL. Nessuna dipendenza oltre a pandas, pyarrow e shapely.
"""
from __future__ import annotations

import io
import json
import logging
import math
import re
import shutil
import zipfile
from collections import defaultdict
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

log = logging.getLogger(__name__)

MEF_BASE = "https://www.de.mef.gov.it"
MEF_PAGINA = (MEF_BASE + "/it/attivita_istituzionali/patrimonio_pubblico/censimento_immobili_pubblici/"
              "open_data_immobili/dati_immobili_{anno}.html")
ADE_URL = "https://wfs-download.cartografia.agenziaentrate.eu/wfsdownload/{}.zip"
REGIONI_ADE = ["ABRUZZO", "BASILICATA", "CALABRIA", "CAMPANIA", "EMILIA-ROMAGNA", "FRIULI-VENEZIA-GIULIA", "LAZIO",
               "LIGURIA", "LOMBARDIA", "MARCHE", "MOLISE", "PIEMONTE", "PUGLIA", "SARDEGNA", "SICILIA", "TOSCANA",
               "UMBRIA", "VALLE-AOSTA", "VENETO"]
ATTRIBUZIONE = ("Fonti: MEF – Dipartimento dell'Economia, «Patrimonio della PA», dati beni immobili al 31/12/{anno} "
                "(CC BY 4.0); Agenzia delle Entrate, cartografia catastale (CC BY 4.0). "
                "Elaborazione: EuGEnio – eugenio.statocritico.it")

# nomi brevi delle colonne MEF (stesso ordine del dizionario 2023)
COLONNE = {
    "Settore Istituzionale": "settore", "Macrocategoria Amministrazione": "macrocategoria",
    "Tipologia Amministrazione": "tipologia_amm", "Amministrazione Denominazione": "amministrazione",
    "Amministrazione Codice Fiscale": "amm_cf", "Regione (Amministrazione)": "amm_regione",
    "Provincia (Amministrazione)": "amm_provincia", "Comune (Amministrazione)": "amm_comune",
    "Cod. Comune (Amministrazione)": "amm_comune_cod", "Titolo proprietà": "titolo_proprieta",
    "Quota proprietà": "quota_proprieta", "Titolo detenzione": "titolo_detenzione",
    "Detenzione Intera UI": "detenzione_intera", "Superficie in detenzione": "sup_detenzione",
    "Canone annuale": "canone_annuo", "Sogg. cedente (denominazione)": "cedente", "Soggetto cedente (CF)": "cedente_cf",
    "ID bene": "id_bene", "Natura del bene": "natura", "Stato Accatastamento": "accatastamento",
    "Sistema Catastale": "sistema_catastale", "Regione del bene": "regione", "Provincia del bene": "provincia",
    "Comune del bene": "comune", "Codice Comune del bene": "comune_cod", "Indirizzo": "indirizzo",
    "Numero Civico": "civico", "Fonte Georeferenziazione": "geo_fonte", "Precisione Georeferenziazione": "geo_precisione",
    "Immobile Geo-Ref.": "georeferenziato", "Latitudine": "lat", "Longitudine": "lon",
    "Identificativo catastale": "id_catastale", "Codice Bene non accatastato": "cod_non_accatastato",
    "Tipologia Bene Immobile": "tipologia", "Superficie (mq)": "superficie_mq", "Cubatura (mc)": "cubatura_mc",
    "Sup. aree pertinenziali (mq)": "sup_pertinenze_mq", "Superficie di Riferimento (mq)": "sup_riferimento_mq",
    "Epoca Costruzione": "epoca", "Vinc. culturale/paesaggistico": "vincolo", "Natura Giuridica del Bene": "natura_giuridica",
    "Diritto gravante sul terreno": "diritto_terreno", "ID Compendio": "id_compendio",
    "Descrizione Compendio": "compendio", "Tipologia Compendio": "tipologia_compendio", "Utilizzo del bene": "utilizzo",
    "Finalità": "finalita", "Altra finalità": "altra_finalita", "ui data interamente a terzi": "a_terzi_intera",
    "ui data parzialmente a terzi": "a_terzi_parziale",
}
NUMERICHE = ["quota_proprieta", "sup_detenzione", "canone_annuo", "lat", "lon", "superficie_mq", "cubatura_mc",
             "sup_pertinenze_mq", "sup_riferimento_mq"]


# --------------------------------------------------------------------------------------------- chiavi di aggancio
def norm_foglio(f: str) -> str:
    f = (f or "").strip().upper()
    return f.zfill(4) if f.isdigit() else f.rjust(4, "0")


def norm_particella(p: str) -> str:
    p = (p or "").strip().upper()
    return (p.lstrip("0") or "0") if p.isdigit() else p


def chiave_ade(ref: str) -> tuple[str, str, str, str]:
    """Riferimento AdE posizionale: comune (4) + sezione (1, «_» se assente) + foglio (4) + allegato (1) + sviluppo (1)
    + «.» + particella. 'A045_000100.1' → ('A045', '', '0001', '1'); 'F363A001300.100' → ('F363', 'A', '0013', '100').
    ValueError se il riferimento non ha la forma attesa."""
    testa, par = ref.split(".", 1)
    if len(testa) != 11 or not par:
        raise ValueError(ref)
    sez = testa[4].upper()
    return testa[:4].upper(), "" if sez == "_" else sez, testa[5:9].upper(), norm_particella(par)


def chiavi_mef(ident: str, natura: str, comune_cod: str | None = None) -> list[tuple[str, str, str, str]]:
    """Chiavi (comune, sezione, foglio, particella) di un identificativo MEF, anche graffato.
    Terreni: comune:sezione:foglio:particella:denominatore:tipo:sub.
    Fabbricati: comune:sezione:sez.urbana:foglio:particella:denominatore:[tipo:]sub (la sezione urbana non serve).
    Se il codice comune è troncato (es. «205» per F205) e si conosce il comune del bene, si usa quello."""
    out = []
    for pezzo in (ident or "").split(";"):
        c = pezzo.split(":")
        if len(c) < 4 or not c[0].strip():
            continue
        if (natura or "").upper() == "TERRENO":
            com, sez, fog, par = c[0], c[1], c[2], c[3]
        else:
            if len(c) < 5:
                continue
            com, sez, fog, par = c[0], c[1], c[3], c[4]
        com = com.strip().upper()
        if len(com) != 4 and comune_cod and str(comune_cod).upper().endswith(com):
            com = str(comune_cod).upper()
        if fog.strip() and par.strip():
            k = (com, sez.strip().upper(), norm_foglio(fog), norm_particella(par))
            if k not in out:
                out.append(k)
    return out


def testo_chiave(k: tuple[str, str, str, str]) -> str:
    return "|".join(k)


# --------------------------------------------------------------------------------------------- MEF
def link_mef(html: str, anno: int) -> list[str]:
    """Indirizzi degli ZIP, del CSV degli adempimenti e del dizionario nella pagina dell'anno."""
    trovati = re.findall(rf'href="(/[^"]*immobili_{anno}/[^"]+\.(?:zip|csv|pdf))"', html)
    return sorted({MEF_BASE + u for u in trovati})


def leggi_csv_mef(dati: bytes) -> pd.DataFrame:
    """Un CSV MEF (Windows-1252, `;`, virgolette, a capo dentro i campi) → DataFrame con i nomi brevi."""
    df = pd.read_csv(io.BytesIO(dati), sep=";", quotechar='"', encoding="cp1252", dtype=str, keep_default_na=False,
                     engine="c")
    df.columns = [COLONNE.get(c.strip(), c.strip()) for c in df.columns]
    for c in df.columns:
        if df[c].str.contains("\n|\r", regex=True).any():
            df[c] = df[c].str.replace(r"[\r\n]+", " ", regex=True)
    for c in NUMERICHE:
        if c in df:
            v = df[c].str.strip()
            if c not in ("lat", "lon"):
                v = v.str.replace(".", "", regex=False)
            df[c] = pd.to_numeric(v.str.replace(",", ".", regex=False), errors="coerce")
    return df


def scarica_mef(dest: Path, anno: int = 2023, client=None) -> Path:
    """Scarica gli ZIP dell'anno, li unisce e scrive `mef_immobili_pa_<anno>.parquet` (più il dizionario PDF)."""
    import httpx
    dest = Path(dest); grezzi = dest / f"mef_{anno}"; grezzi.mkdir(parents=True, exist_ok=True)
    cl = client or httpx.Client(timeout=120, follow_redirects=True)
    pagina = cl.get(MEF_PAGINA.format(anno=anno)); pagina.raise_for_status()
    parti = []
    for u in link_mef(pagina.text, anno):
        f = grezzi / u.rsplit("/", 1)[1]
        if not f.exists():
            r = cl.get(u); r.raise_for_status(); f.write_bytes(r.content)
        if f.suffix == ".zip":
            with zipfile.ZipFile(f) as z:
                for n in z.namelist():
                    if n.lower().endswith(".csv"):
                        d = leggi_csv_mef(z.read(n)); d["file"] = Path(n).name; parti.append(d)
                        log.info("MEF %s: %d righe", n, len(d))
    df = pd.concat(parti, ignore_index=True)
    out = dest / f"mef_immobili_pa_{anno}.parquet"
    df.to_parquet(out, index=False, compression="zstd")
    return out


FONTI_PUNTO_AFFIDABILI = ("IDENTIFICATIVI_CATASTALI", "UTENTE")   # centroide AdE della particella o punto messo a mano


def richieste_per_comune(beni: pd.DataFrame) -> dict[str, dict]:
    """comune → {chiave: [(lon, lat), …]}: le chiavi da cercare nel GML del comune e i punti MEF affidabili che servono
    a scegliere fra più sezioni o a trovare la particella quando l'identificativo non c'è più nella mappa."""
    rich: dict[str, dict] = defaultdict(dict)
    col = lambda c: beni[c] if c in beni else [None] * len(beni)
    for ident, nat, cc, la, lo, fonte in zip(beni["id_catastale"], beni["natura"], col("comune_cod"), col("lat"),
                                             col("lon"), col("geo_fonte")):
        punto = (float(lo), float(la)) if fonte in FONTI_PUNTO_AFFIDABILI and la and lo and la == la and lo == lo \
            else None
        for k in chiavi_mef(ident, nat, cc):
            for com in {k[0], str(cc).upper() if cc else k[0]}:
                lista = rich[com].setdefault(k, [])
                if punto and punto not in lista:
                    lista.append(punto)
    return rich


# --------------------------------------------------------------------------------------------- AdE
_RE_REF = re.compile(rb"<CP:NATIONALCADASTRALREFERENCE>([^<]+)</CP:NATIONALCADASTRALREFERENCE>")
_RE_POS = re.compile(rb"<gml:posList[^>]*>([^<]+)</gml:posList>")


def _anello(txt: bytes):
    v = txt.split()
    return list(zip(map(float, v[1::2]), map(float, v[0::2])))  # EPSG:6706 è lat lon: si scambia in lon lat


def _geometria(blocco: bytes):
    from shapely.geometry import MultiPolygon, Polygon
    poligoni = []
    for pz in blocco.split(b"<gml:Polygon")[1:]:
        ext = _RE_POS.search(pz, max(pz.find(b"<gml:exterior"), 0))
        if not ext:
            continue
        buchi = [_anello(m.group(1)) for i in pz.split(b"<gml:interior")[1:] if (m := _RE_POS.search(i))]
        poligoni.append(Polygon(_anello(ext.group(1)), buchi))
    if not poligoni:
        return None
    return poligoni[0] if len(poligoni) == 1 else MultiPolygon(poligoni)


_RE_BBOX = re.compile(rb"<gml:lowerCorner>([^<]+)</gml:lowerCorner>\s*<gml:upperCorner>([^<]+)</gml:upperCorner>")
CELLA = 0.002   # griglia dei punti per il secondo passaggio (~200 m)


def _membri(dati: bytes):
    pos = 0
    while (i := dati.find(b"<wfs:member>", pos)) >= 0:
        j = dati.find(b"</wfs:member>", i)
        yield dati[i:j]
        pos = j + 13


def _contiene(g, punti) -> bool:
    from shapely.geometry import Point
    return any(g.covers(Point(p)) for p in punti)


def leggi_ple(dati: bytes, richieste) -> tuple[int, list, list]:
    """Legge un `_ple.gml` e restituisce (particelle lette, [(chiave, riferimento, geometria, aggancio)], riferimenti
    fuori formato). `richieste`: {chiave: [punti MEF (lon, lat)]} (va bene anche un insieme di chiavi).

    Regole, in ordine, tutte automatiche:
    1. «esatto»: comune, sezione, foglio e particella coincidono;
    2. «senza_sezione»: il MEF non scrive la sezione che l'AdE indica e la particella esiste in una sola sezione;
    3. «sezione_dal_punto»: esiste in più sezioni e si sceglie quella che contiene il punto MEF;
    4. «punto»: l'identificativo non c'è nella mappa (rinumerato, sezione urbana diversa, scritto male): si prende la
       particella che contiene il punto MEF, solo se il punto è il centroide AdE o è stato messo dall'utente."""
    if not isinstance(richieste, dict):
        richieste = {k: [] for k in richieste}
    tot, trovate, riserva, strani = 0, [], {}, []
    for blocco in _membri(dati):
        tot += 1
        m = _RE_REF.search(blocco)
        if not m:
            continue
        ref = m.group(1).decode()
        try:
            k = chiave_ade(ref)
        except ValueError:
            strani.append(ref); continue
        if k in richieste:
            if (g := _geometria(blocco)) is not None:
                trovate.append((k, ref, g, "esatto"))
        elif k[1] and (k2 := (k[0], "", k[2], k[3])) in richieste:
            riserva.setdefault(k2, []).append((ref, blocco))
    gia = {t[0] for t in trovate}
    for k2, cand in riserva.items():
        if k2 in gia:
            continue
        if len({r.split(".")[0][4] for r, _ in cand}) == 1:
            if (g := _geometria(cand[0][1])) is not None:
                trovate.append((k2, cand[0][0], g, "senza_sezione")); gia.add(k2)
        elif richieste[k2]:
            for r, bl in cand:
                if (g := _geometria(bl)) is not None and _contiene(g, richieste[k2]):
                    trovate.append((k2, r, g, "sezione_dal_punto")); gia.add(k2); break

    # 4) secondo passaggio, solo se resta qualcosa con un punto affidabile
    griglia: dict[tuple, list] = defaultdict(list)
    for k, punti in richieste.items():
        if k not in gia:
            for p in punti:
                griglia[(int(p[0] // CELLA), int(p[1] // CELLA))].append((k, p))
    if griglia:
        for blocco in _membri(dati):
            g = None
            if bb := _RE_BBOX.search(blocco):
                la0, lo0 = map(float, bb.group(1).split()); la1, lo1 = map(float, bb.group(2).split())
            elif (g := _geometria(blocco)) is not None:
                lo0, la0, lo1, la1 = g.bounds
            else:
                continue
            cand = [(k, p) for cx in range(int(lo0 // CELLA), int(lo1 // CELLA) + 1)
                    for cy in range(int(la0 // CELLA), int(la1 // CELLA) + 1) for k, p in griglia.get((cx, cy), ())
                    if k not in gia and lo0 <= p[0] <= lo1 and la0 <= p[1] <= la1]
            if not cand:
                continue
            g = g if g is not None else _geometria(blocco)
            if g is None:
                continue
            ref = _RE_REF.search(blocco).group(1).decode() if _RE_REF.search(blocco) else ""
            for k, p in cand:
                if k not in gia and _contiene(g, [p]):
                    trovate.append((k, ref, g, "punto")); gia.add(k)
    return tot, trovate, strani


def poligoni_regione(zip_regione: Path, richieste: dict[str, dict], lavoro: Path) -> tuple[pa.Table, dict]:
    """Tutti i comuni di uno ZIP regionale AdE → tabella (chiave, riferimento, geometria WKB)."""
    import shapely
    col = {"chiave": [], "ref_ade": [], "aggancio": [], "geometry": []}
    stat = {"comuni": 0, "particelle_lette": 0, "strani": 0}
    with zipfile.ZipFile(zip_regione) as zr:
        for prov in zr.namelist():
            tmp = lavoro / f"_{zip_regione.stem}_{Path(prov).stem}.zip"
            with zr.open(prov) as s, open(tmp, "wb") as d:
                shutil.copyfileobj(s, d, 1 << 24)
            try:
                with zipfile.ZipFile(tmp) as zp:
                    for cz in zp.namelist():
                        req = richieste.get(Path(cz).name[:4].upper())
                        if not req:
                            continue
                        with zipfile.ZipFile(io.BytesIO(zp.read(cz))) as zc:
                            for g in zc.namelist():
                                if g.endswith("_ple.gml"):
                                    tot, trovate, strani = leggi_ple(zc.read(g), req)
                                    stat["comuni"] += 1; stat["particelle_lette"] += tot; stat["strani"] += len(strani)
                                    for k, ref, geom, agg in trovate:
                                        col["chiave"].append(testo_chiave(k)); col["ref_ade"].append(ref)
                                        col["aggancio"].append(agg)
                                        col["geometry"].append(shapely.to_wkb(geom))
            finally:
                tmp.unlink(missing_ok=True)
    stat["agganciate"] = len(col["chiave"])
    return pa.table(col), stat


def scarica_poligoni(dest: Path, beni: pd.DataFrame, regioni=None) -> list[Path]:
    """Per ogni regione: scarica lo ZIP AdE (poi lo cancella) e salva `poligoni/<REGIONE>.parquet`."""
    import httpx
    dest = Path(dest); (dest / "poligoni").mkdir(parents=True, exist_ok=True)
    rich = richieste_per_comune(beni)
    fatti = []
    for reg in regioni or REGIONI_ADE:
        out = dest / "poligoni" / f"{reg}.parquet"
        if not out.exists():
            z = dest / f"_{reg}.zip"
            with httpx.stream("GET", ADE_URL.format(reg), timeout=600, follow_redirects=True) as r, open(z, "wb") as f:
                r.raise_for_status()
                for b in r.iter_bytes(1 << 24):
                    f.write(b)
            try:
                tab, stat = poligoni_regione(z, rich, dest)
            finally:
                z.unlink(missing_ok=True)
            pq.write_table(tab, out, compression="zstd")
            log.info("AdE %s: %s", reg, stat)
        fatti.append(out)
    return fatti


# --------------------------------------------------------------------------------------------- composizione
def _area_m2(g) -> float:
    """Area in m² con la proiezione equirettangolare locale (errore < 0,5 % su una particella)."""
    c = g.centroid
    return g.area * (111_320.0 ** 2) * math.cos(math.radians(c.y))


def _scrivi_tabella(tab: pa.Table, tipo: list[str], out: Path, anno: int):
    """GeoParquet 1.0 (WKB, CRS84) con l'attribuzione nei metadati."""
    meta = {"version": "1.0.0", "primary_column": "geometry",
            "columns": {"geometry": {"encoding": "WKB", "geometry_types": tipo, "crs": "OGC:CRS84"}}}
    tab = tab.replace_schema_metadata({**(tab.schema.metadata or {}), b"geo": json.dumps(meta).encode(),
                                       b"attribuzione": ATTRIBUZIONE.format(anno=anno).encode()})
    pq.write_table(tab, out, compression="zstd")


def componi(beni_parquet: Path, poligoni: list[Path], dest: Path, anno: int = 2023) -> dict:
    """Scrive `immobili_pa_<anno>_beni.parquet` (punti, tutte le colonne MEF + `ref_ade` e `aggancio`) e
    `immobili_pa_<anno>_particelle.parquet` (un poligono per particella AdE con i dati riassunti dei beni).
    Lavora in due passate con le sole colonne necessarie: sul file nazionale resta sotto i 4 GB di memoria."""
    import pyarrow.compute as pc
    import shapely

    # chiave MEF → (riferimento AdE, aggancio): la prima trovata (stessa particella in più allegati/sviluppi)
    idx = pa.concat_tables([pq.read_table(p, columns=[c for c in ("chiave", "ref_ade", "aggancio")
                                                      if c in pq.read_schema(p).names]) for p in poligoni],
                           promote_options="default").to_pandas() if poligoni else \
        pd.DataFrame(columns=["chiave", "ref_ade", "aggancio"])
    if "aggancio" not in idx:
        idx["aggancio"] = None
    idx["aggancio"] = idx["aggancio"].fillna("esatto")
    idx = idx.drop_duplicates("chiave")
    ref_di = dict(zip(idx.chiave, idx.ref_ade)); agg_di = dict(zip(idx.chiave, idx.aggancio))
    del idx

    # 1) beni: riferimento della particella, aggancio e punto, a livello Arrow (senza pandas)
    # le colonne di testo ripetitive restano a dizionario: la tabella nazionale passa da ~3,6 GB a qualche centinaio di MB
    testo = [f.name for f in pq.read_schema(beni_parquet) if pa.types.is_string(f.type) or pa.types.is_large_string(f.type)]
    ripetitive = [c for c in testo if c not in ("id_bene", "id_catastale", "indirizzo", "cod_non_accatastato")]
    t = pq.read_table(beni_parquet, read_dictionary=ripetitive)
    chiavi = [[testo_chiave(k) for k in chiavi_mef(i, n, c)] for i, n, c in
              zip(t["id_catastale"].to_pylist(), t["natura"].to_pylist(), t["comune_cod"].to_pylist())]
    scelta = [next((k for k in ks if k in ref_di), None) for ks in chiavi]
    del chiavi
    punti = [shapely.to_wkb(shapely.Point(lo, la)) if la and lo else None
             for la, lo in zip(t["lat"].to_pylist(), t["lon"].to_pylist())]
    t = (t.append_column("ref_ade", pa.array([ref_di.get(k) for k in scelta], pa.string()))
          .append_column("aggancio", pa.array([agg_di.get(k) for k in scelta], pa.string()))
          .append_column("geometry", pa.array(punti, pa.binary())))
    del scelta, punti
    con_id = int(pc.sum(pc.greater(pc.utf8_length(pc.fill_null(t["id_catastale"], "")), 0)).as_py())
    n_beni, n_pol = t.num_rows, int(pc.sum(pc.is_valid(t["ref_ade"])).as_py() or 0)
    log.info("componi: beni pronti")
    _scrivi_tabella(t, ["Point"], Path(dest) / f"immobili_pa_{anno}_beni.parquet", anno)
    del t

    # 2) particelle: una riga per particella AdE (contando anche le parti delle unità graffate)
    e = pq.read_table(beni_parquet, columns=["id_bene", "natura", "amministrazione", "tipologia_amm", "tipologia",
                                             "regione", "comune", "id_catastale", "comune_cod"],
                      read_dictionary=["natura", "amministrazione", "tipologia_amm", "tipologia", "regione",
                                       "comune"]).to_pandas()
    e["chiave"] = [[testo_chiave(k) for k in chiavi_mef(i, str(n), c)]
                   for i, n, c in zip(e.pop("id_catastale"), e["natura"], e.pop("comune_cod"))]
    log.info("componi: chiavi delle particelle")
    e = e.explode("chiave").dropna(subset=["chiave"])
    e["ref_ade"] = e["chiave"].map(ref_di)
    e = e.dropna(subset=["ref_ade"]).drop(columns="chiave")
    for c in ["natura", "amministrazione", "tipologia_amm", "tipologia", "regione", "comune"]:
        e[c] = e[c].astype(str).replace({"nan": "", "<NA>": ""})
    e["fab"] = (e["natura"] == "FABBRICATO").astype(int); e["ter"] = (e["natura"] == "TERRENO").astype(int)
    g = e.groupby("ref_ade").agg(regione=("regione", "first"), comune=("comune", "first"),
                                 n_beni=("id_bene", "nunique"), n_fabbricati=("fab", "sum"), n_terreni=("ter", "sum"))
    for c, nome in [("amministrazione", "amministrazioni"), ("tipologia_amm", "tipologie_amm"), ("tipologia", "tipologie")]:
        u = e.loc[e[c] != "", ["ref_ade", c]].drop_duplicates().sort_values(["ref_ade", c])
        g[nome] = u.groupby("ref_ade")[c].agg(" · ".join).str.slice(0, 500)
    g = g.fillna({"amministrazioni": "", "tipologie_amm": "", "tipologie": ""}).reset_index()
    del e
    log.info("componi: particelle raggruppate")
    pol = pa.concat_tables([pq.read_table(p) for p in poligoni], promote_options="default").to_pandas()
    pol["aggancio"] = pol.get("aggancio", pd.Series(index=pol.index, dtype=object)).fillna("esatto")
    pol = pol.sort_values("aggancio", key=lambda s: s.map({"esatto": 0}).fillna(1)).drop_duplicates("ref_ade")
    g = g.merge(pol.drop(columns=["chiave"]), on="ref_ade", how="inner")
    del pol
    k = [chiave_ade(r) for r in g["ref_ade"]]
    for i, c in enumerate(["comune_cod", "sezione", "foglio", "particella"]):
        g.insert(1 + i, c, [x[i] for x in k])
    log.info("componi: poligoni uniti")
    wkb = g.pop("geometry").tolist()
    g["area_m2"] = [round(_area_m2(x), 1) for x in shapely.from_wkb(wkb)]
    tab = pa.Table.from_pandas(g, preserve_index=False).append_column("geometry", pa.array(wkb, pa.binary()))
    _scrivi_tabella(tab, ["Polygon", "MultiPolygon"], Path(dest) / f"immobili_pa_{anno}_particelle.parquet", anno)
    return {"beni": n_beni, "beni_con_identificativo": con_id, "beni_con_poligono": n_pol, "particelle": len(g)}
