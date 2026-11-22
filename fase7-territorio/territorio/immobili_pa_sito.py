"""Prodotti per il sito degli immobili delle PA (pagina Territorio › Edifici pubblici e retino in Modelli 3D).

Dai due GeoParquet di `immobili_pa.componi` si preparano:

1. **`immobili_pa_<anno>_<AAAAMMGGhhmm>.pmtiles`** (tessere vettoriali, tippecanoe; nome con la versione dal 22/11/2026,
   vedi `nome_pmtiles`), da mettere nella cartella degli archivi edifici (servita da Caddy in `/edifici3d/immobili_pa/`). Due strati:
   - `particelle`: poligoni delle particelle con beni pubblici, dallo zoom 13 al 16 (oltre si ingrandisce il 16);
   - `punti`: un punto per particella fino allo zoom 12 (vista d'insieme) e, a tutti gli zoom, i beni con un punto
     affidabile ma senza particella agganciata.
   Proprietà corte, per tenere leggere le tessere: `r` riferimento AdE (o `b<id bene>` per i punti senza particella),
   `t` tipo (`E` solo fabbricati, `T` solo terreni, `M` entrambi), `n` numero di beni, `g` gruppo di enti (codice di
   GRUPPI_ENTI), `a` primo ente (accorciato), `tp` prime tipologie (accorciate), `e` enti della particella (dal
   22/11/2026, ricerca per ente): testo delimitato da virgole con un elemento `<id ente><ruolo>` per ente e ruolo, ruolo
   `p` in proprietà e `u` in uso (detenzione), per esempio `",12p,4031u,"`; la pagina filtra con
   `["in", ",12p,", ["get", "e"]]`.
2. **`immobili_pa_<anno>.sqlite`** per l'API (ricerca, scheda, ricerca per ente): tabella `beni` con le colonne utili,
   l'id dell'ente (`ente`) e il ruolo (`ruolo`: P proprietà, U uso), e una tabella FTS5 per la ricerca a parole su ente,
   comune, indirizzo, tipologia e identificativo catastale; tabella `particelle` con centro e riquadro; dal 22/11/2026
   tabelle `enti` (una riga per ente con i totali), `ente_particelle` (ente, particella, ruolo, natura: una riga per
   gruppo, con centro, numero di beni e superfici) e `comuni` (codice catastale → nome, provincia, regione).
   **Senza** il soggetto cedente e il suo codice fiscale (per gli immobili in affitto possono essere persone fisiche) e
   senza il codice fiscale dell'ente, che serve solo qui dentro per raggruppare: fuori va la **chiave** derivata
   (`chiave_ente`, 10 caratteri esadecimali di SHA-256, stabile da un anno all'altro) e l'id progressivo.
3. **`enti_<anno>_<versione>.json`** accanto al PMTiles (dal 22/11/2026): elenco di tutti gli enti per l'autocompletamento
   nel browser (id, chiave, nome, gruppo, sede, regioni con beni, conteggi). Nome con la versione come il PMTiles, perché
   gli id cambiano con i dati.
4. **`indice.json`** accanto al PMTiles: anno, nome del PMTiles e di `enti_….json`, conteggi, attribuzione, zoom, gruppi
   (letto dalle pagine).

Tutte le uscite si scrivono in file provvisori nella stessa cartella e si sostituiscono con `os.replace` (22/11/2026):
si può rifare tutto con il sito e l'API accesi.

Servono il programma `tippecanoe` (2.17 o successivo, scrive i PMTiles; su Ubuntu/Debian `apt install tippecanoe`),
pandas, pyarrow e shapely.
"""
from __future__ import annotations

import hashlib
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


# --------------------------------------------------------------------------------------------- enti (22/11/2026)
def chiave_ente(cf: str | None, nome: str | None = None) -> str:
    """Chiave pubblica e stabile di un ente: primi 10 caratteri esadecimali di SHA-256 del codice fiscale (maiuscolo, senza
    spazi). Senza codice fiscale (file di prova, righe anomale) si usa il nome normalizzato, con un prefisso diverso. Il
    codice fiscale non esce mai da questo modulo: nelle tessere va l'id progressivo, nei collegamenti la chiave."""
    cf = "".join((cf or "").split()).upper()
    base = f"CF:{cf}" if cf else f"NOME:{_norma(nome or '')}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:10]


def _sigla_provincia(p: str) -> str:
    p = (p or "").strip()
    return p if len(p) <= 3 else ""


SI = ("sì", "si", "s")


def _centri(particelle_parquet: Path):
    """Centro (punto sulla superficie), riquadro, area e numero di beni di ogni particella, in un DataFrame."""
    import pandas as pd
    import shapely
    parti = []
    for lotto in pq.ParquetFile(particelle_parquet).iter_batches(batch_size=100_000,
                                                                 columns=["ref_ade", "area_m2", "n_beni", "geometry"]):
        d = lotto.to_pydict()
        g = shapely.from_wkb(d["geometry"]); c = shapely.point_on_surface(g); b = shapely.bounds(g)
        parti.append(pd.DataFrame({"ref_ade": d["ref_ade"], "lon": shapely.get_x(c).round(6), "lat": shapely.get_y(c).round(6),
                                   "ovest": b[:, 0].round(6), "sud": b[:, 1].round(6), "est": b[:, 2].round(6),
                                   "nord": b[:, 3].round(6), "area_m2": d["area_m2"], "n_beni": d["n_beni"]}))
    if not parti:
        return pd.DataFrame(columns=["ref_ade", "lon", "lat", "ovest", "sud", "est", "nord", "area_m2", "n_beni"])
    return pd.concat(parti, ignore_index=True)


def _testo(serie) -> "pd.Series":
    return serie.astype("string").fillna("").str.strip()


def enti(beni_parquet: Path, particelle_parquet: Path, centri=None) -> dict:
    """Enti dichiaranti, coppie ente–particella e gruppi per le tessere, calcolati dal parquet dei beni.

    Restituisce un dizionario con:
    - `enti`: DataFrame, una riga per ente (id progressivo ordinato per nome, chiave, nome, classificazione, sede, totali);
    - `ente_righe`: id dell'ente per ogni riga del parquet dei beni, nello stesso ordine (per la colonna `ente` dell'indice);
    - `ruolo_righe`: «P» (proprietà) o «U» (in uso: titolo di detenzione senza titolo di proprietà) per ogni riga;
    - `coppie`: DataFrame (ente, ref, ruolo, natura) con centro, beni, superfici e testi per l'elenco della pagina;
      `ref` è il riferimento AdE della particella o `b<id bene>` per i beni senza particella (centro solo se il punto del
      censimento è affidabile, come nelle tessere);
    - `comuni`: DataFrame (comune_cod, comune, provincia, regione);
    - `e_di`: riferimento → testo `",<id><p|u>,…,"` per la proprietà `e` delle tessere.

    Le unità graffate (più particelle nello stesso identificativo) contano in ogni particella che toccano, come in
    `immobili_pa.componi`; superficie e cubatura vanno solo sulla particella principale (`ref_ade` del bene), così la
    somma delle righe non conta due volte la stessa unità. I totali degli enti si calcolano sulle righe dei beni."""
    import numpy as np
    import pandas as pd
    from .immobili_pa import FONTI_PUNTO_AFFIDABILI, chiavi_mef, testo_chiave

    voluti = ["id_bene", "amm_cf", "amministrazione", "tipologia_amm", "settore", "macrocategoria", "amm_regione",
              "amm_provincia", "amm_comune", "titolo_proprieta", "titolo_detenzione", "natura", "regione", "provincia",
              "comune", "comune_cod", "indirizzo", "civico", "id_catastale", "ref_ade", "lat", "lon", "georeferenziato",
              "geo_fonte", "tipologia", "superficie_mq", "sup_riferimento_mq", "cubatura_mc", "epoca", "vincolo", "utilizzo",
              "a_terzi_intera", "a_terzi_parziale"]
    disp = set(pq.read_schema(beni_parquet).names)
    col = [c for c in voluti if c in disp]
    ripetitive = [c for c in col if c not in ("id_bene", "id_catastale", "indirizzo", "civico", "ref_ade", "lat", "lon",
                                              "superficie_mq", "sup_riferimento_mq", "cubatura_mc")]
    t = pq.read_table(beni_parquet, columns=col, read_dictionary=ripetitive).to_pandas()
    for c in voluti:
        if c not in t:
            t[c] = None
    n = len(t)
    nome = _testo(t["amministrazione"])
    cf = _testo(t["amm_cf"]).str.replace(r"\s+", "", regex=True).str.upper()
    # chiave interna di raggruppamento: il codice fiscale (mai scritto in uscita); senza, il nome normalizzato
    t["_k"] = np.where(cf != "", "CF:" + cf, "NOME:" + nome.map(_norma))
    del cf

    def prevalente(campo):
        v = _testo(t[campo])
        x = pd.DataFrame({"_k": t["_k"], "v": v})
        x = x[x["v"] != ""].groupby(["_k", "v"], observed=True).size().reset_index(name="c")
        x = x.sort_values(["_k", "c", "v"], ascending=[True, False, True]).drop_duplicates("_k")
        return dict(zip(x["_k"], x["v"]))

    chiavi = sorted(set(t["_k"]))
    nomi = prevalente("amministrazione")
    ordine = sorted(chiavi, key=lambda k: (_norma(nomi.get(k, "")), nomi.get(k, ""), k))
    id_di = {k: i + 1 for i, k in enumerate(ordine)}
    t["ente"] = t["_k"].map(id_di).astype("int64")
    tipologie = prevalente("tipologia_amm")
    e = pd.DataFrame({"_k": ordine, "id": [id_di[k] for k in ordine]})
    e["chiave"] = [chiave_ente(k[3:]) if k.startswith("CF:") else chiave_ente(None, k[5:]) for k in ordine]
    e["nome"] = [nomi.get(k, "") for k in ordine]
    e["tipologia_amm"] = [tipologie.get(k, "") for k in ordine]
    e["gruppo"] = [gruppo_ente(x) for x in e["tipologia_amm"]]
    for campo, dest in [("settore", "settore"), ("macrocategoria", "macrocategoria"), ("amm_regione", "sede_regione"),
                        ("amm_provincia", "sede_provincia"), ("amm_comune", "sede_comune")]:
        p = prevalente(campo)
        e[dest] = [p.get(k, "") for k in ordine]

    # indicatori per riga
    natura = _testo(t["natura"]).str.upper()
    fab = (natura == "FABBRICATO").to_numpy()
    ter = (natura == "TERRENO").to_numpy()
    prop = _testo(t["titolo_proprieta"]) != ""
    det = _testo(t["titolo_detenzione"]) != ""
    ruolo = np.where(det & ~prop, "U", "P")
    sup = pd.to_numeric(t["superficie_mq"], errors="coerce").fillna(0).to_numpy()
    rif = pd.to_numeric(t["sup_riferimento_mq"], errors="coerce").fillna(0).to_numpy()
    sup = np.where(sup > 0, sup, np.where(rif > 0, rif, 0.0))
    cub = pd.to_numeric(t["cubatura_mc"], errors="coerce").fillna(0).to_numpy()
    util = _testo(t["utilizzo"])
    vinc = _testo(t["vincolo"])
    terzi = _testo(t["a_terzi_intera"]).str.lower().isin(SI) | _testo(t["a_terzi_parziale"]).str.lower().isin(SI)
    ref = _testo(t["ref_ade"])
    epoca = _testo(t["epoca"])
    r = pd.DataFrame({"ente": t["ente"].to_numpy(), "fab": fab.astype(int), "ter": ter.astype(int),
                      "sup_fab": np.where(fab, sup, 0.0), "sup_ter": np.where(ter, sup, 0.0), "cub": cub,
                      "prop": (ruolo == "P").astype(int), "det": (ruolo == "U").astype(int),
                      "nonut": (util == "Non utilizzato").astype(int).to_numpy(),
                      "inut": (util == "Inutilizzabile").astype(int).to_numpy(),
                      "vinc": (~vinc.isin(["", "Nessuno", "ND"])).astype(int).to_numpy(),
                      "terzi": terzi.astype(int).to_numpy(), "senza": (ref == "").astype(int).to_numpy(),
                      "regione": _testo(t["regione"]).to_numpy(), "comune_cod": _testo(t["comune_cod"]).str.upper().to_numpy()})
    g = r.groupby("ente").agg(n_beni=("fab", "size"), n_fabbricati=("fab", "sum"), n_terreni=("ter", "sum"),
                              sup_fabbricati_mq=("sup_fab", "sum"), sup_terreni_mq=("sup_ter", "sum"), cubatura_mc=("cub", "sum"),
                              n_proprieta=("prop", "sum"), n_detenzione=("det", "sum"), n_non_utilizzati=("nonut", "sum"),
                              n_inutilizzabili=("inut", "sum"), n_vincolati=("vinc", "sum"), n_a_terzi=("terzi", "sum"),
                              n_senza_particella=("senza", "sum"))
    g["n_regioni"] = r[r["regione"] != ""].groupby("ente")["regione"].nunique()
    g["n_comuni"] = r[r["comune_cod"] != ""].groupby("ente")["comune_cod"].nunique()
    ep = pd.DataFrame({"ente": r["ente"], "epoca": epoca})[fab & ~epoca.isin(["", "ND"]).to_numpy()]
    ep = ep.groupby(["ente", "epoca"]).size().reset_index(name="c").sort_values(["ente", "c", "epoca"], ascending=[True, False, True])
    g["epoca_prevalente"] = ep.drop_duplicates("ente").set_index("ente")["epoca"]
    # regioni (dei beni) per il filtro dell'elenco: nome → indice nell'elenco ordinato
    regioni = sorted(x for x in set(r["regione"]) if x)
    reg_di = {x: i for i, x in enumerate(regioni)}
    rr = r.loc[r["regione"] != "", ["ente", "regione"]].drop_duplicates()
    reg_enti = rr.assign(i=rr["regione"].map(reg_di)).sort_values("i").groupby("ente")["i"].agg(list)
    del r

    # coppie ente–particella: particella principale più le altre parti delle unità graffate
    if centri is None:
        centri = _centri(particelle_parquet)
    k_part = {}
    if len(centri):
        from .immobili_pa import chiave_ade
        for rf in centri["ref_ade"]:
            try:
                k_part[testo_chiave(chiave_ade(rf))] = rf
            except ValueError:
                pass
    idc = t["id_catastale"].astype("string").fillna("")
    graff = idc.str.contains(";", regex=False).to_numpy()
    refs = [[x] if x else [] for x in ref]
    for i in np.flatnonzero(graff):
        altri = [k_part.get(testo_chiave(k)) for k in chiavi_mef(idc.iat[i], natura.iat[i], t["comune_cod"].iat[i])]
        for x in altri:
            if x and x not in refs[i]:
                refs[i].append(x)
    del k_part
    id_bene = _testo(t["id_bene"])
    principale = []
    lista = []
    for i, rs in enumerate(refs):
        if rs:
            lista.append(rs); principale.append([True] + [False] * (len(rs) - 1))
        else:
            lista.append([f"b{id_bene.iat[i]}"]); principale.append([True])
    del refs
    affidabile = (_testo(t["georeferenziato"]).str.lower().isin(SI) | _testo(t["geo_fonte"]).isin(FONTI_PUNTO_AFFIDABILI)).to_numpy()
    lat = pd.to_numeric(t["lat"], errors="coerce").to_numpy(); lon = pd.to_numeric(t["lon"], errors="coerce").to_numpy()
    ind = (_testo(t["indirizzo"]) + " " + _testo(t["civico"])).str.strip()
    ind = ind.where(~ind.str.upper().isin(["SNC", "S.N.C.", "0"]), "")
    c = pd.DataFrame({"ente": t["ente"].to_numpy(), "ref": lista, "princ": principale, "ruolo": ruolo,
                      "natura": np.where(fab, "E", "T"), "id_bene": id_bene.to_numpy(), "sup": sup, "cub": cub,
                      "comune_cod": _testo(t["comune_cod"]).str.upper().to_numpy(), "indirizzo": ind.to_numpy(),
                      "tipologia": _testo(t["tipologia"]).to_numpy(), "epoca": epoca.to_numpy(), "utilizzo": util.to_numpy(),
                      "titolo": np.where(prop, _testo(t["titolo_proprieta"]), _testo(t["titolo_detenzione"])),
                      "plon": np.where(affidabile, lon, np.nan), "plat": np.where(affidabile, lat, np.nan)})
    comuni = pd.DataFrame({"comune_cod": c["comune_cod"], "comune": _testo(t["comune"]).to_numpy(),
                           "provincia": _testo(t["provincia"]).to_numpy(), "regione": _testo(t["regione"]).to_numpy()})
    comuni = comuni[comuni["comune_cod"] != ""].drop_duplicates("comune_cod").sort_values("comune_cod").reset_index(drop=True)
    ente_righe = t["ente"].to_numpy(); del t
    c = c.explode(["ref", "princ"], ignore_index=True)
    c["princ"] = c["princ"].astype(bool)
    c.loc[~c["princ"], ["sup", "cub"]] = 0.0
    # «first» dei gruppi salta i valori mancanti: i testi vuoti (e l'epoca «ND») diventano mancanti, così resta il primo
    # valore compilato senza funzioni Python per gruppo (sul file nazionale i gruppi sono ~2 milioni)
    for campo in ("comune_cod", "indirizzo", "epoca", "utilizzo", "titolo"):
        c[campo] = c[campo].replace({"": None, **({"ND": None} if campo == "epoca" else {})})
    chiave = ["ente", "ref", "ruolo", "natura"]
    agg = c.groupby(chiave, sort=True).agg(n_beni=("id_bene", "nunique"), sup_mq=("sup", "sum"), cubatura_mc=("cub", "sum"),
                                           comune_cod=("comune_cod", "first"), indirizzo=("indirizzo", "first"),
                                           epoca=("epoca", "first"), utilizzo=("utilizzo", "first"), titolo=("titolo", "first"),
                                           plon=("plon", "first"), plat=("plat", "first"))
    tip = c.loc[c["tipologia"] != "", chiave + ["tipologia"]].drop_duplicates().sort_values(chiave + ["tipologia"])
    agg["tipologie"] = tip.groupby(chiave)["tipologia"].agg(" · ".join).str.slice(0, 200)
    agg = agg.reset_index()
    agg[["comune_cod", "indirizzo", "epoca", "utilizzo", "titolo", "tipologie"]] = \
        agg[["comune_cod", "indirizzo", "epoca", "utilizzo", "titolo", "tipologie"]].fillna("")
    del c, tip
    cen = centri[["ref_ade", "lon", "lat", "area_m2"]].rename(columns={"ref_ade": "ref"})
    agg = agg.merge(cen, on="ref", how="left")
    senza = agg["lon"].isna()
    agg.loc[senza, "lon"] = agg.loc[senza, "plon"].round(6); agg.loc[senza, "lat"] = agg.loc[senza, "plat"].round(6)
    agg = agg.drop(columns=["plon", "plat"])
    agg["sup_mq"] = agg["sup_mq"].round(1); agg["cubatura_mc"] = agg["cubatura_mc"].round(1)

    # totali che vengono dalle coppie: particelle, area dei lotti, riquadro
    part = agg[~agg["ref"].str.startswith("b")].drop_duplicates(["ente", "ref"])
    g["n_particelle"] = part.groupby("ente").size()
    g["area_particelle_m2"] = part.groupby("ente")["area_m2"].sum().round(0)
    conpunto = agg.dropna(subset=["lon", "lat"])
    q = conpunto.groupby("ente").agg(ovest=("lon", "min"), sud=("lat", "min"), est=("lon", "max"), nord=("lat", "max"))
    g = g.join(q)
    e = e.merge(g.reset_index(), left_on="id", right_on="ente", how="left").drop(columns=["ente", "_k"])
    for col_int in ["n_beni", "n_fabbricati", "n_terreni", "n_proprieta", "n_detenzione", "n_non_utilizzati",
                    "n_inutilizzabili", "n_vincolati", "n_a_terzi", "n_senza_particella", "n_regioni", "n_comuni",
                    "n_particelle"]:
        e[col_int] = e[col_int].fillna(0).astype("int64")
    e["sup_fabbricati_mq"] = e["sup_fabbricati_mq"].round(0); e["sup_terreni_mq"] = e["sup_terreni_mq"].round(0)
    e["cubatura_mc"] = e["cubatura_mc"].round(0)
    e["epoca_prevalente"] = e["epoca_prevalente"].fillna("")
    e["regioni_beni"] = [reg_enti.get(i, []) for i in e["id"]]

    # proprietà «e» delle tessere: enti e ruoli di ogni riferimento
    er = agg[["ref", "ente", "ruolo"]].drop_duplicates().sort_values(["ref", "ente", "ruolo"])
    er["tok"] = er["ente"].astype(str) + er["ruolo"].str.lower()
    e_di = ("," + er.groupby("ref")["tok"].agg(",".join) + ",").to_dict()
    return {"enti": e, "ente_righe": ente_righe, "ruolo_righe": ruolo, "coppie": agg, "comuni": comuni, "e_di": e_di,
            "regioni": regioni}


CAMPI_ENTI_JSON = ["id", "chiave", "nome", "gruppo", "sede", "beni", "fabbricati", "terreni", "particelle", "regioni"]


def enti_json(en: dict, anno: int) -> dict:
    """Elenco degli enti per l'autocompletamento nel browser (`enti_<anno>_<versione>.json`): righe compatte, in ordine di
    nome. «sede» è il comune della sede con la sigla della provincia; «regioni» gli indici (in `regioni`) delle regioni dove
    l'ente ha beni. Nessun codice fiscale."""
    righe = []
    for x in en["enti"].itertuples(index=False):
        prov = _sigla_provincia(x.sede_provincia)
        sede = (x.sede_comune or "").strip().title()
        sede = f"{sede} ({prov})" if sede and prov else sede
        righe.append([int(x.id), x.chiave, x.nome, x.gruppo, sede, int(x.n_beni), int(x.n_fabbricati), int(x.n_terreni),
                      int(x.n_particelle), list(x.regioni_beni)])
    return {"anno": anno, "campi": CAMPI_ENTI_JSON, "regioni": en["regioni"], "gruppi": {k: v[0] for k, v in GRUPPI_ENTI.items()},
            "enti": righe}


# --------------------------------------------------------------------------------------------- GeoJSON per tippecanoe
def scrivi_geojsonseq(particelle_parquet: Path, beni_parquet: Path, dest: Path, e_di: dict | None = None) -> dict:
    """Scrive `particelle.geojsonl` e `punti.geojsonl` (una feature per riga) in `dest`. Restituisce i conteggi.
    `e_di` (riferimento → enti, da `enti()`) aggiunge la proprietà `e` in tutti e due gli strati."""
    e_di = e_di or {}
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
                if d["ref_ade"][i] in e_di:
                    p["e"] = e_di[d["ref_ade"][i]]
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
                if p["r"] in e_di:
                    p["e"] = e_di[p["r"]]
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


def tessere(particelle_parquet: Path, beni_parquet: Path, out: Path, attribuzione: str, e_di: dict | None = None) -> dict:
    """GeoJSON di lavoro (cartella temporanea accanto all'uscita) → PMTiles con tippecanoe e tile-join."""
    for prog in ("tippecanoe", "tile-join"):
        if not shutil.which(prog):
            raise RuntimeError(f"serve {prog} (su Ubuntu/Debian: sudo apt install tippecanoe)")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        cont = scrivi_geojsonseq(particelle_parquet, beni_parquet, Path(tmp), e_di)
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
               "geo_fonte", "superficie_mq", "cubatura_mc", "sup_pertinenze_mq", "sup_riferimento_mq", "epoca", "vincolo",
               "natura_giuridica", "titolo_proprieta", "quota_proprieta", "titolo_detenzione", "detenzione_intera",
               "canone_annuo", "utilizzo", "finalita", "altra_finalita", "compendio", "tipologia_compendio",
               "a_terzi_intera", "a_terzi_parziale", "sistema_catastale"]
# mai nell'indice pubblico: soggetto cedente e suo codice fiscale (possono essere persone fisiche), CF dell'ente
ESCLUSE = ("cedente", "cedente_cf", "amm_cf")
# colonne delle tabelle nuove (22/11/2026): l'ordine è quello delle tabelle; i test controllano che non ci sia ESCLUSE
COLONNE_ENTI = ["id", "chiave", "nome", "tipologia_amm", "gruppo", "settore", "macrocategoria", "sede_regione",
                "sede_provincia", "sede_comune", "n_beni", "n_fabbricati", "n_terreni", "n_particelle", "n_senza_particella",
                "sup_fabbricati_mq", "sup_terreni_mq", "cubatura_mc", "area_particelle_m2", "n_proprieta", "n_detenzione",
                "n_non_utilizzati", "n_inutilizzabili", "n_vincolati", "n_a_terzi", "epoca_prevalente", "n_regioni",
                "n_comuni", "ovest", "sud", "est", "nord"]
COLONNE_COPPIE = ["ente", "ref", "ruolo", "natura", "lon", "lat", "n_beni", "sup_mq", "cubatura_mc", "area_m2",
                  "comune_cod", "indirizzo", "tipologie", "epoca", "utilizzo", "titolo"]


def _provvisorio(out: Path) -> Path:
    """File di lavoro accanto all'uscita (stesso disco, così os.replace è atomico). Nome con il punto davanti e senza
    l'estensione finale: l'API cerca `immobili_pa_*.sqlite` e non lo vede mai."""
    return out.with_name(f".{out.name}.nuovo")


def indice_sqlite(beni_parquet: Path, particelle_parquet: Path, out: Path, info: dict | None = None,
                  en: dict | None = None, centri=None) -> dict:
    """Indice per l'API. Scritto in un file provvisorio nella stessa cartella e poi sostituito con os.replace (22/11/2026):
    l'API lo apre con `immutable=1`, una connessione per richiesta, e non deve mai leggere un file a metà. Le richieste
    già aperte finiscono sul file vecchio (su Linux resta leggibile finché è aperto), le nuove aprono quello nuovo.
    `info` (chiave → valore) va nella tabella `info` prima della sostituzione. `en` (risultato di `enti()`) e `centri`
    (di `_centri()`) si calcolano qui se non vengono passati."""
    import shapely
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = _provvisorio(out)
    if tmp.exists():
        tmp.unlink()                                    # resto di un rifacimento interrotto
    try:
        n = _scrivi_indice(beni_parquet, particelle_parquet, tmp, info or {}, shapely, en=en, centri=centri)
        os.replace(tmp, out)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return {"beni": n}


def _valore(v):
    """Valore per SQLite: NaN e NA → NULL, interi e decimali numpy → Python."""
    if v is None:
        return None
    try:
        if v != v:                                       # NaN
            return None
    except (TypeError, ValueError):
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


def _scrivi_indice(beni_parquet: Path, particelle_parquet: Path, out: Path, info: dict, shapely, en: dict | None = None,
                   centri=None) -> int:
    if centri is None:
        centri = _centri(particelle_parquet)
    if en is None:
        en = enti(beni_parquet, particelle_parquet, centri)
    db = sqlite3.connect(out)
    db.execute("PRAGMA journal_mode=OFF"); db.execute("PRAGMA synchronous=OFF")
    disp = set(pq.read_schema(beni_parquet).names)
    col = [c for c in COLONNE_SQL if c in disp]
    assert not set(col) & set(ESCLUSE)
    con_enti = True
    extra = ["gruppo"] + (["ente", "ruolo"] if con_enti else [])
    db.execute(f"CREATE TABLE beni ({', '.join(col + extra)})")
    db.execute("CREATE VIRTUAL TABLE cerca USING fts5(testo, tokenize='unicode61 remove_diacritics 2')")
    n = 0
    for lotto in pq.ParquetFile(beni_parquet).iter_batches(batch_size=100_000, columns=col):
        d = lotto.to_pydict()
        m = len(d["id_bene"])
        if con_enti:
            ent = en["ente_righe"][n:n + m].tolist(); ruo = en["ruolo_righe"][n:n + m].tolist()
            righe = [tuple(d[c][i] for c in col) + (gruppo_ente(d["tipologia_amm"][i] or ""), ent[i], ruo[i]) for i in range(m)]
        else:
            righe = [tuple(d[c][i] for c in col) + (gruppo_ente(d["tipologia_amm"][i] or ""),) for i in range(m)]
        db.executemany(f"INSERT INTO beni VALUES ({','.join('?' * (len(col) + len(extra)))})", righe)
        campi = [c for c in ("amministrazione", "comune", "provincia", "indirizzo", "civico", "tipologia", "compendio",
                             "id_catastale", "ref_ade") if c in d]
        testi = [(n + i + 1, " ".join(str(d[c][i] or "") for c in campi)) for i in range(m)]
        db.executemany("INSERT INTO cerca(rowid, testo) VALUES (?, ?)", testi)
        n += m
    db.execute("CREATE INDEX beni_ref ON beni(ref_ade)")
    db.execute("CREATE INDEX beni_id ON beni(id_bene)")
    db.execute("CREATE TABLE particelle (ref_ade PRIMARY KEY, lon, lat, ovest, sud, est, nord, area_m2, n_beni)")
    db.executemany("INSERT INTO particelle VALUES (?,?,?,?,?,?,?,?,?)",
                   [tuple(_valore(v) for v in r) for r in centri[["ref_ade", "lon", "lat", "ovest", "sud", "est", "nord",
                                                                  "area_m2", "n_beni"]].itertuples(index=False)])
    if con_enti:
        _scrivi_enti(db, en)
    db.execute("CREATE TABLE info (chiave PRIMARY KEY, valore)")
    db.executemany("INSERT INTO info VALUES (?, ?)", [(k, json.dumps(v, ensure_ascii=False)) for k, v in info.items()])
    db.commit(); db.execute("VACUUM"); db.close()
    return n


def _scrivi_enti(db: sqlite3.Connection, en: dict) -> None:
    """Tabelle della ricerca per ente (22/11/2026): `enti`, `ente_particelle`, `comuni` e l'indice su beni(ente)."""
    e = en["enti"]
    assert not set(COLONNE_ENTI) & set(ESCLUSE) and not set(COLONNE_COPPIE) & set(ESCLUSE)
    db.execute(f"CREATE TABLE enti ({', '.join(c + (' INTEGER PRIMARY KEY' if c == 'id' else '') for c in COLONNE_ENTI)})")
    db.executemany(f"INSERT INTO enti VALUES ({','.join('?' * len(COLONNE_ENTI))})",
                   [tuple(_valore(v) for v in r) for r in e[COLONNE_ENTI].itertuples(index=False)])
    db.execute("CREATE UNIQUE INDEX enti_chiave ON enti(chiave)")
    db.execute(f"CREATE TABLE ente_particelle ({', '.join(COLONNE_COPPIE)}, PRIMARY KEY (ente, ref, ruolo, natura)) WITHOUT ROWID")
    c = en["coppie"]
    for i in range(0, len(c), 200_000):
        db.executemany(f"INSERT INTO ente_particelle VALUES ({','.join('?' * len(COLONNE_COPPIE))})",
                       [tuple(_valore(v) for v in r) for r in c.iloc[i:i + 200_000][COLONNE_COPPIE].itertuples(index=False)])
    db.execute("CREATE INDEX ente_particelle_comune ON ente_particelle(ente, comune_cod)")
    db.execute("CREATE TABLE comuni (comune_cod PRIMARY KEY, comune, provincia, regione)")
    db.executemany("INSERT INTO comuni VALUES (?,?,?,?)", list(en["comuni"].itertuples(index=False, name=None)))
    db.execute("CREATE INDEX beni_ente ON beni(ente, ruolo, natura)")


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
    """Toglie i PMTiles e gli elenchi degli enti dello stesso anno non più in uso (si tengono anche i precedenti, per le
    pagine già aperte)."""
    via = []
    for f in [*cartella.glob(f"immobili_pa_{anno}*.pmtiles"), *cartella.glob(f"enti_{anno}_*.json")]:
        if f.name not in tieni:
            f.unlink(); via.append(f.name)
    return via


def prepara(cartella: Path, anno: int, uscita_tessere: Path, uscita_indice: Path, attribuzione: str,
            versione: str | None = None) -> dict:
    """Tutti i prodotti del sito da `cartella` (dove `immobili-pa` ha scritto i GeoParquet).

    Ordine (22/11/2026), pensato per rifare tutto con il sito acceso: (0) enti e coppie ente–particella, in memoria;
    (1) PMTiles nuovo con un nome nuovo, accanto al vecchio; (2) elenco degli enti `enti_<anno>_<versione>.json`, anche lui
    con un nome nuovo; (3) indice SQLite in un file provvisorio poi sostituito; (4) `indice.json` sostituito per ultimo,
    così le pagine passano ai file nuovi solo quando c'è tutto; (5) si cancellano i file più vecchi dei precedenti."""
    beni = cartella / f"immobili_pa_{anno}_beni.parquet"
    part = cartella / f"immobili_pa_{anno}_particelle.parquet"
    f_indice = uscita_tessere / "indice.json"
    try:
        vecchio = json.loads(f_indice.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        vecchio = {}
    precedenti = {Path(vecchio.get(k) or "").name for k in ("pmtiles", "enti")} - {""}
    versione = versione or time.strftime("%Y%m%d%H%M")
    centri = _centri(part)
    en = enti(beni, part, centri)
    log.info("enti: %d, coppie ente–particella: %d", len(en["enti"]), len(en["coppie"]))
    pm = uscita_tessere / nome_pmtiles(anno, versione)
    cont = tessere(part, beni, pm, attribuzione, e_di=en["e_di"])
    fe = uscita_tessere / f"enti_{anno}_{versione}.json"
    elenco = enti_json(en, anno)
    tmp = _provvisorio(fe)
    tmp.write_text(json.dumps(elenco, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, fe)
    sq = uscita_indice / f"immobili_pa_{anno}.sqlite"
    n_ben = pq.read_metadata(beni).num_rows
    indice = {"anno": anno, "pmtiles": f"/edifici3d/immobili_pa/{pm.name}", "enti": f"/edifici3d/immobili_pa/{fe.name}",
              "attribuzione": attribuzione, "licenza": "CC BY 4.0", "zoom_particelle": ZOOM_POLIGONI, "beni": n_ben, **cont,
              "n_enti": len(en["enti"]), "gruppi": {k: v[0] for k, v in GRUPPI_ENTI.items()}}
    indice_sqlite(beni, part, sq, info=indice, en=en, centri=centri)
    _scrivi_json(f_indice, indice)
    tolti = _pulisci_pmtiles(uscita_tessere, anno, {pm.name, fe.name} | precedenti)
    if tolti:
        log.info("file vecchi tolti: %s", ", ".join(tolti))
    return indice
