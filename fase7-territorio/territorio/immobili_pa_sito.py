"""Prodotti per il sito degli immobili delle PA (pagina Territorio › Edifici pubblici e retino in Modelli 3D).

Dai due GeoParquet di `immobili_pa.componi` si preparano:

1. **`immobili_pa_<anno>_<AAAAMMGGhhmm>.pmtiles`** (tessere vettoriali, tippecanoe; nome con la versione dal 22/11/2026,
   vedi `nome_pmtiles`), da mettere nella cartella degli archivi edifici (servita da Caddy in `/edifici3d/immobili_pa/`). Due strati:
   - `particelle`: poligoni delle particelle con beni pubblici, dallo zoom 13 al 16 (oltre si ingrandisce il 16);
   - `punti`: un punto per particella fino allo zoom 12 (vista d'insieme) e, a tutti gli zoom, i beni con un punto
     affidabile ma senza particella agganciata.
   Proprietà corte, per tenere leggere le tessere: `r` riferimento AdE (o `b<id bene>` per i punti senza particella),
   `t` tipo (`E` solo fabbricati, `T` solo terreni, `M` entrambi), `n` numero di beni, `g` gruppo di enti (codice di
   GRUPPI_ENTI), `a` primo ente (accorciato), `tp` prime tipologie (accorciate).
2. **`immobili_pa_<anno>.sqlite`** per l'API (ricerca e scheda): tabella `beni` con le colonne utili e una tabella FTS5
   per la ricerca a parole su ente, comune, indirizzo, tipologia e identificativo catastale; tabella `particelle` con
   centro e riquadro. **Senza** il soggetto cedente e il suo codice fiscale (per gli immobili in affitto possono essere
   persone fisiche) e senza il codice fiscale dell'ente.
3. **`indice.json`** accanto al PMTiles: anno, nome del PMTiles, conteggi, attribuzione, zoom, gruppi (letto dalle pagine).

Tutte le uscite si scrivono in file provvisori nella stessa cartella e si sostituiscono con `os.replace` (22/11/2026):
si può rifare tutto con il sito e l'API accesi.

Servono il programma `tippecanoe` (2.17 o successivo, scrive i PMTiles; su Ubuntu/Debian `apt install tippecanoe`),
pandas, pyarrow e shapely.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
import unicodedata
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

log = logging.getLogger(__name__)
ZOOM_POLIGONI = 13      # da qui i confini delle particelle; sotto, un punto per particella

# gruppi di enti per i filtri della pagina (codice nelle tessere → etichetta); l'ordine è quello del menu.
# Le tipologie si confrontano normalizzate (_norma): nei CSV MEF gli accenti sono apostrofi («Universita'», «Citta'
# Metropolitane e Province», «Unioni di Comuni e Comunita' Montane»), nel dizionario sono lettere accentate. Fino al
# 22/11/2026 il confronto era letterale e Province, Università e Unioni finivano in «Altri enti».
# Unioni di Comuni e Comunità montane: gruppo proprio «I» (decisione del 22/11/2026), non dentro i Comuni.
GRUPPI_ENTI = {
    "C": ("Comuni", ("Comuni",)),
    "I": ("Unioni di Comuni e Comunità montane", ("Unioni di Comuni e Comunità Montane",)),
    "P": ("Province e Città metropolitane", ("Città Metropolitane e Province",)),
    "R": ("Regioni", ("Regioni",)),
    "S": ("Sanità (ASL e ospedali)", ("Enti Locali del Servizio Sanitario",)),
    "U": ("Università", ("Università",)),
    "E": ("Edilizia residenziale pubblica", ("Aziende, Enti e Istituti Territoriali per l'Edilizia Residenziale",)),
    "M": ("Stato: ministeri e organi costituzionali", ("Ministeri e Presidenza del Consiglio dei Ministri",
                                                       "Organi Costituzionali E Di Rilievo Costituzionale",
                                                       "Agenzie Fiscali")),
    "N": ("Previdenza (INPS, INAIL…)", ("Enti Nazionali Pubblici Di Previdenza e Assistenza",)),
    "A": ("Altri enti", ()),
}


def _norma(s: str) -> str:
    """Tipologia confrontabile: senza accenti né apostrofi, minuscola, spazi singoli («Universita'» = «Università»)."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"['’‘`´]", "", s)
    return " ".join(s.lower().split())


_DA_TIPOLOGIA = {_norma(t): k for k, (_, ts) in GRUPPI_ENTI.items() for t in ts}


def gruppo_ente(tipologia_amm: str) -> str:
    """Codice del gruppo di enti per una «Tipologia Amministrazione» del MEF (A = altri)."""
    return _DA_TIPOLOGIA.get(_norma(tipologia_amm), "A")


def _tipo(n_fab: int, n_ter: int) -> str:
    return "M" if n_fab and n_ter else ("E" if n_fab else "T")


def _corto(s: str, n: int = 80) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


# --------------------------------------------------------------------------------------------- GeoJSON per tippecanoe
def scrivi_geojsonseq(particelle_parquet: Path, beni_parquet: Path, dest: Path) -> dict:
    """Scrive `particelle.geojsonl` e `punti.geojsonl` (una feature per riga) in `dest`. Restituisce i conteggi."""
    import shapely
    import shapely.geometry
    dest.mkdir(parents=True, exist_ok=True)
    n_pol = n_pun = 0
    pf = pq.ParquetFile(particelle_parquet)
    with open(dest / "particelle.geojsonl", "w", encoding="utf-8") as fp, \
            open(dest / "punti.geojsonl", "w", encoding="utf-8") as fu:
        for lotto in pf.iter_batches(batch_size=50_000, columns=["ref_ade", "n_beni", "n_fabbricati", "n_terreni",
                                                                  "amministrazioni", "tipologie_amm", "tipologie",
                                                                  "geometry"]):
            d = lotto.to_pydict()
            geoms = shapely.from_wkb(d["geometry"])
            centri = shapely.point_on_surface(geoms)
            for i, g in enumerate(geoms):
                prima_tip = (d["tipologie_amm"][i] or "").split(" · ")[0]
                p = {"r": d["ref_ade"][i], "t": _tipo(d["n_fabbricati"][i], d["n_terreni"][i]), "n": int(d["n_beni"][i]),
                     "g": gruppo_ente(prima_tip), "a": _corto((d["amministrazioni"][i] or "").split(" · ")[0]),
                     "tp": _corto(d["tipologie"][i] or "", 90)}
                fp.write(json.dumps({"type": "Feature", "properties": p, "geometry": shapely.geometry.mapping(g)},
                                    ensure_ascii=False, separators=(",", ":")) + "\n")
                c = centri[i]
                fu.write(json.dumps({"type": "Feature", "tippecanoe": {"maxzoom": ZOOM_POLIGONI - 1}, "properties": p,
                                     "geometry": {"type": "Point", "coordinates": [round(c.x, 6), round(c.y, 6)]}},
                                    ensure_ascii=False, separators=(",", ":")) + "\n")
                n_pol += 1
        # beni senza particella ma con un punto affidabile (centroide AdE, utente o indirizzo al civico)
        bf = pq.ParquetFile(beni_parquet)
        voluti = ["id_bene", "ref_ade", "natura", "tipologia_amm", "amministrazione", "tipologia", "lat", "lon",
                  "georeferenziato", "geo_fonte"]
        for lotto in bf.iter_batches(batch_size=100_000, columns=[c for c in voluti if c in bf.schema_arrow.names]):
            d = lotto.to_pydict()
            for i in range(len(d["id_bene"])):
                if d["ref_ade"][i] or d["lat"][i] is None or d["lon"][i] is None:
                    continue
                # punto affidabile: «Immobile Geo-Ref.» = Sì (centroide AdE, utente o indirizzo al civico)
                geo = d.get("georeferenziato", [None] * (i + 1))[i]
                if (geo or "").lower() not in ("sì", "si") and (d.get("geo_fonte") or [""] * (i + 1))[i] \
                        not in ("IDENTIFICATIVI_CATASTALI", "UTENTE"):
                    continue
                fab = d["natura"][i] == "FABBRICATO"
                p = {"r": f"b{d['id_bene'][i]}", "t": "E" if fab else "T", "n": 1, "g": gruppo_ente(d["tipologia_amm"][i]),
                     "a": _corto(d["amministrazione"][i]), "tp": _corto(d["tipologia"][i] or "", 90), "s": 1}
                fu.write(json.dumps({"type": "Feature", "properties": p, "geometry": {"type": "Point",
                                     "coordinates": [round(d["lon"][i], 6), round(d["lat"][i], 6)]}},
                                    ensure_ascii=False, separators=(",", ":")) + "\n")
                n_pun += 1
    return {"particelle": n_pol, "punti_senza_particella": n_pun}


def comandi_tippecanoe(cartella: Path, out: Path, attribuzione: str) -> list[list[str]]:
    """Righe di comando (separate per i test): due passate e l'unione con tile-join.

    Prova del 17/11/2026 (tippecanoe 2.49): con lo zoom minimo per feature («tippecanoe»: {"minzoom": 13}) sui poligoni
    ogni tessera teneva **una sola** particella; senza `-r1` ne scartava ~2 milioni «per frequenza» a ogni zoom, anche al
    16. Quindi: particelle in una passata propria dallo zoom 13 (`-Z13`), punti in un'altra dallo zoom 4 (lo zoom massimo
    per feature dei punti delle particelle funziona), `-r1` in tutte e due, sfoltimento dei punti solo se una tessera supera
    il limite, poi `tile-join` nel PMTiles finale."""
    a, b = cartella / "particelle.pmtiles", cartella / "punti.pmtiles"
    comuni = ["--force", "--quiet", "-r1", "-z16", "--maximum-tile-bytes=1000000"]
    return [
        ["tippecanoe", "-o", str(a), *comuni, f"-Z{ZOOM_POLIGONI}", "--no-tiny-polygon-reduction-at-maximum-zoom",
         "-L", f"particelle:{cartella / 'particelle.geojsonl'}"],
        ["tippecanoe", "-o", str(b), *comuni, "-Z4", "--drop-densest-as-needed", "-L", f"punti:{cartella / 'punti.geojsonl'}"],
        ["tile-join", "-o", str(out), "--force", "--quiet", "-n", "Immobili delle PA", "-A", attribuzione,
         "--no-tile-size-limit", str(a), str(b)],
    ]


def tessere(particelle_parquet: Path, beni_parquet: Path, out: Path, attribuzione: str) -> dict:
    """GeoJSON di lavoro (cartella temporanea accanto all'uscita) → PMTiles con tippecanoe e tile-join."""
    for prog in ("tippecanoe", "tile-join"):
        if not shutil.which(prog):
            raise RuntimeError(f"serve {prog} (su Ubuntu/Debian: sudo apt install tippecanoe)")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        cont = scrivi_geojsonseq(particelle_parquet, beni_parquet, Path(tmp))
        # tile-join scrive nella cartella di lavoro (stesso disco dell'uscita); il file finale compare solo intero
        provvisorio = Path(tmp) / "finale.pmtiles"
        for cmd in comandi_tippecanoe(Path(tmp), provvisorio, attribuzione):
            log.info("%s", " ".join(cmd[:3]))
            subprocess.run(cmd, check=True)
        os.replace(provvisorio, out)
    return cont


# --------------------------------------------------------------------------------------------- SQLite per l'API
COLONNE_SQL = ["id_bene", "ref_ade", "aggancio", "natura", "tipologia", "amministrazione", "tipologia_amm",
               "regione", "provincia", "comune", "comune_cod", "indirizzo", "civico", "id_catastale", "lat", "lon",
               "geo_fonte", "superficie_mq", "cubatura_mc", "sup_pertinenze_mq", "epoca", "vincolo", "natura_giuridica",
               "titolo_proprieta", "quota_proprieta", "titolo_detenzione", "canone_annuo", "utilizzo", "finalita",
               "altra_finalita", "compendio", "tipologia_compendio", "a_terzi_intera", "a_terzi_parziale"]
# mai nell'indice pubblico: soggetto cedente e suo codice fiscale (possono essere persone fisiche), CF dell'ente
ESCLUSE = ("cedente", "cedente_cf", "amm_cf")


def _provvisorio(out: Path) -> Path:
    """File di lavoro accanto all'uscita (stesso disco, così os.replace è atomico). Nome con il punto davanti e senza
    l'estensione finale: l'API cerca `immobili_pa_*.sqlite` e non lo vede mai."""
    return out.with_name(f".{out.name}.nuovo")


def indice_sqlite(beni_parquet: Path, particelle_parquet: Path, out: Path, info: dict | None = None) -> dict:
    """Indice per l'API. Scritto in un file provvisorio nella stessa cartella e poi sostituito con os.replace (22/11/2026):
    l'API lo apre con `immutable=1`, una connessione per richiesta, e non deve mai leggere un file a metà. Le richieste
    già aperte finiscono sul file vecchio (su Linux resta leggibile finché è aperto), le nuove aprono quello nuovo.
    `info` (chiave → valore) va nella tabella `info` prima della sostituzione."""
    import shapely
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = _provvisorio(out)
    if tmp.exists():
        tmp.unlink()                                    # resto di un rifacimento interrotto
    try:
        n = _scrivi_indice(beni_parquet, particelle_parquet, tmp, info or {}, shapely)
        os.replace(tmp, out)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return {"beni": n}


def _scrivi_indice(beni_parquet: Path, particelle_parquet: Path, out: Path, info: dict, shapely) -> int:
    db = sqlite3.connect(out)
    db.execute("PRAGMA journal_mode=OFF"); db.execute("PRAGMA synchronous=OFF")
    disp = set(pq.read_schema(beni_parquet).names)
    col = [c for c in COLONNE_SQL if c in disp]
    db.execute(f"CREATE TABLE beni ({', '.join(col)}, gruppo)")
    db.execute("CREATE VIRTUAL TABLE cerca USING fts5(testo, tokenize='unicode61 remove_diacritics 2')")
    n = 0
    for lotto in pq.ParquetFile(beni_parquet).iter_batches(batch_size=100_000, columns=col):
        d = lotto.to_pydict()
        righe = [tuple(d[c][i] for c in col) + (gruppo_ente(d["tipologia_amm"][i] or ""),) for i in range(len(d["id_bene"]))]
        db.executemany(f"INSERT INTO beni VALUES ({','.join('?' * (len(col) + 1))})", righe)
        campi = [c for c in ("amministrazione", "comune", "provincia", "indirizzo", "civico", "tipologia", "compendio",
                             "id_catastale", "ref_ade") if c in d]
        testi = [(n + i + 1, " ".join(str(d[c][i] or "") for c in campi)) for i in range(len(d["id_bene"]))]
        db.executemany("INSERT INTO cerca(rowid, testo) VALUES (?, ?)", testi)
        n += len(righe)
    db.execute("CREATE INDEX beni_ref ON beni(ref_ade)")
    db.execute("CREATE INDEX beni_id ON beni(id_bene)")
    db.execute("CREATE TABLE particelle (ref_ade PRIMARY KEY, lon, lat, ovest, sud, est, nord, area_m2, n_beni)")
    for lotto in pq.ParquetFile(particelle_parquet).iter_batches(batch_size=100_000,
                                                                 columns=["ref_ade", "area_m2", "n_beni", "geometry"]):
        d = lotto.to_pydict()
        g = shapely.from_wkb(d["geometry"]); c = shapely.point_on_surface(g); b = shapely.bounds(g)
        db.executemany("INSERT INTO particelle VALUES (?,?,?,?,?,?,?,?,?)",
                       [(d["ref_ade"][i], round(c[i].x, 6), round(c[i].y, 6), *[round(float(v), 6) for v in b[i]],
                         d["area_m2"][i], d["n_beni"][i]) for i in range(len(d["ref_ade"]))])
    db.execute("CREATE TABLE info (chiave PRIMARY KEY, valore)")
    db.executemany("INSERT INTO info VALUES (?, ?)", [(k, json.dumps(v, ensure_ascii=False)) for k, v in info.items()])
    db.commit(); db.execute("VACUUM"); db.close()
    return n


def nome_pmtiles(anno: int, versione: str | None = None) -> str:
    """Nome del PMTiles con la versione (data e ora del rifacimento, 22/11/2026): `indice.json` (sempre riconvalidato,
    Cache-Control no-cache) dice alle pagine quale file leggere, così Cloudflare e i browser non mescolano tessere
    vecchie (in copia per un giorno) e nuove con lo stesso nome, e non serve la Purge."""
    return f"immobili_pa_{anno}_{versione or time.strftime('%Y%m%d%H%M')}.pmtiles"


def _scrivi_json(f: Path, dati: dict) -> None:
    tmp = _provvisorio(f)
    tmp.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, f)


def _pulisci_pmtiles(cartella: Path, anno: int, tieni: set[str]) -> list[str]:
    """Toglie i PMTiles dello stesso anno non più in uso (si tiene anche il precedente, per le pagine già aperte)."""
    via = []
    for f in cartella.glob(f"immobili_pa_{anno}*.pmtiles"):
        if f.name not in tieni:
            f.unlink(); via.append(f.name)
    return via


def prepara(cartella: Path, anno: int, uscita_tessere: Path, uscita_indice: Path, attribuzione: str,
            versione: str | None = None) -> dict:
    """Tutti i prodotti del sito da `cartella` (dove `immobili-pa` ha scritto i GeoParquet).

    Ordine (22/11/2026), pensato per rifare tutto con il sito acceso: (1) PMTiles nuovo con un nome nuovo, accanto al
    vecchio; (2) indice SQLite in un file provvisorio poi sostituito; (3) `indice.json` sostituito per ultimo, così le
    pagine passano al file nuovo solo quando c'è tutto; (4) si cancellano i PMTiles più vecchi del precedente."""
    beni = cartella / f"immobili_pa_{anno}_beni.parquet"
    part = cartella / f"immobili_pa_{anno}_particelle.parquet"
    f_indice = uscita_tessere / "indice.json"
    try:
        precedente = Path(json.loads(f_indice.read_text(encoding="utf-8")).get("pmtiles", "")).name
    except (OSError, ValueError):
        precedente = ""
    pm = uscita_tessere / nome_pmtiles(anno, versione)
    cont = tessere(part, beni, pm, attribuzione)
    sq = uscita_indice / f"immobili_pa_{anno}.sqlite"
    n_ben = pq.read_metadata(beni).num_rows
    indice = {"anno": anno, "pmtiles": f"/edifici3d/immobili_pa/{pm.name}", "attribuzione": attribuzione,
              "licenza": "CC BY 4.0", "zoom_particelle": ZOOM_POLIGONI, "beni": n_ben, **cont,
              "gruppi": {k: v[0] for k, v in GRUPPI_ENTI.items()}}
    indice_sqlite(beni, part, sq, info=indice)
    _scrivi_json(f_indice, indice)
    tolti = _pulisci_pmtiles(uscita_tessere, anno, {pm.name, precedente})
    if tolti:
        log.info("PMTiles vecchi tolti: %s", ", ".join(tolti))
    return indice
