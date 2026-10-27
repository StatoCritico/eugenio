"""Geolocalizzazione di un patrimonio immobiliare diffuso (centinaia o migliaia di edifici).

Ingresso: CSV con una riga per edificio e almeno una di queste informazioni, in ordine di affidabilità:
  1. coordinate:        lat, lon
  2. dati catastali:    comune, foglio, particella (o mappale) [, sezione]
  3. indirizzo:         indirizzo [, civico], comune (il civico può anche stare in fondo all'indirizzo)
Colonne facoltative: id, denominazione (e qualsiasi altra, riportata in uscita).

Gli indirizzi si cercano prima nell'ANNCSU (archivio ufficiale dei civici, file locale, se fornito) e
poi con la geocodifica di Zornade; il punto trovato si porta sulla particella con Zornade. Il punto di
un civico è l'accesso sulla strada: se cade su una particella stradale si prova qualche punto vicino
per trovare la particella edificata.

Uscita: stesse righe con particella catastale (FID Zornade, foglio, mappale, superficie), punto, fonte
del punto, comune ISTAT/catastale e un esito:
  ok           trovato in modo univoco e coerente con il comune dichiarato
  verificare   trovato ma da controllare: più particelle, comune diverso da quello dichiarato, particella
               che non è un immobile (strada, acque), civico non trovato tal quale, via interpretata
  non_trovato  nessun risultato (la colonna nota dice cosa è stato cercato)
Più un GeoJSON di punti per la mappa. Le ricerche sono in cache: rieseguire costa solo le righe nuove.
"""
from __future__ import annotations

import io
import json
import logging
import math
import re
from pathlib import Path

import pandas as pd

from .anncsu import ATTRIBUZIONE as ATTRIBUZIONE_ANNCSU, INFORMATIVE, Indirizzario, separa_civico
from .zornade import ATTRIBUZIONE, ATTRIBUZIONE_HTML, ATTRIBUZIONE_URL, Zornade, coordinate, da_riferimento

log = logging.getLogger(__name__)
NON_EDIFICI = {"strada": "una strada", "acqua": "acque", "acque": "acque"}
# punti di prova attorno a un accesso che cade sulla strada: (metri verso nord, metri verso est)
INTORNO = [(d * dy, d * dx) for d in (8, 16) for dy, dx in ((1, 0), (0, 1), (-1, 0), (0, -1))]
SINONIMI = {
    "lat": ["lat", "latitudine", "latitude", "y"], "lon": ["lon", "lng", "longitudine", "longitude", "x"],
    "comune": ["comune", "citta", "città", "municipio", "localita", "località"],
    "foglio": ["foglio", "fg"], "particella": ["particella", "mappale", "map", "part", "numero"],
    "sezione": ["sezione", "sez"], "indirizzo": ["indirizzo", "via", "address", "ubicazione"],
    "civico": ["civico", "n_civico", "numero_civico"], "id": ["id", "codice", "cod", "codice_edificio"],
    "denominazione": ["denominazione", "nome", "descrizione", "edificio"],
}


def _norm(c: str) -> str:
    return re.sub(r"[^a-z0-9àèéìòù_]", "_", c.strip().lower()).strip("_")


def leggi(file: Path | str | bytes) -> pd.DataFrame:
    grezzo = file if isinstance(file, bytes) else Path(file).read_bytes()
    try:
        testo = grezzo.decode("utf-8-sig")
    except UnicodeDecodeError:          # CSV salvato da Excel con la codifica di Windows
        testo = grezzo.decode("cp1252")
    sep = ";" if testo.splitlines()[0].count(";") >= testo.splitlines()[0].count(",") else ","
    df = pd.read_csv(io.StringIO(testo), sep=sep, dtype=str).fillna("")
    mappa = {}
    for c in df.columns:
        n = _norm(c)
        for std, alias in SINONIMI.items():
            if n in alias and std not in mappa.values():
                mappa[c] = std
                break
    df = df.rename(columns=mappa)
    if "id" not in df:
        df.insert(0, "id", [str(i + 1) for i in range(len(df))])
    return df


def _num(v) -> float | None:
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _aggiungi(ris: dict, testo: str) -> None:
    ris["nota"] = (ris["nota"] + "; " if ris["nota"] else "") + testo


def _via_civico(r: dict) -> tuple[str, str]:
    via, civ = str(r.get("indirizzo", "")).strip(), str(r.get("civico", "")).strip()
    if not civ:
        via, civ = separa_civico(via)
    return via, civ


def _anncsu(idx: Indirizzario, dich, via: str, civ: str, ris: dict) -> str:
    """Restituisce "" se ha trovato il punto, altrimenti il motivo (usato nella nota solo se
    neanche Zornade trova l'indirizzo)."""
    if dich is None:
        return "comune non riconosciuto: ANNCSU non consultato"
    t = idx.cerca(dich.istat, getattr(dich, "belfiore", None), via, civ)
    if t is None:
        return f"{idx.motivo(dich.istat, via)} a {dich.nome}"
    ris["lat"], ris["lon"] = float(t.lat), float(t.lon)
    ris["fonte_punto"] = "ANNCSU"
    ris["indirizzo_trovato"] = f"{t.odonimo} {t.civico}"
    if t.nota:
        _aggiungi(ris, t.nota)
    return ""


def _geocodifica(z: Zornade, via: str, civ: str, com: str, ris: dict):
    """Prima "via civico comune"; se non trova nulla, "via comune" (punto della via, da verificare)."""
    tentativi = [" ".join(x for x in (via, civ, com) if x)]
    if civ:
        tentativi.append(" ".join(x for x in (via, com) if x))
    for i, q in enumerate(tentativi):
        geo = z.geocodifica(q, limite=3)
        if geo:
            if i > 0:
                _aggiungi(ris, f"civico {civ} non trovato: usato un punto di {via}")
            elif len(geo) > 1:
                _aggiungi(ris, "più indirizzi possibili: usato il primo")
            ris["fonte_punto"] = "Zornade"
            ris["indirizzo_trovato"] = (geo[0].get("formatted_address") or geo[0].get("label") or q)
            return geo[0]
    _aggiungi(ris, f"indirizzo non trovato da Zornade ({tentativi[0]})")
    return None


def _sposta(lat: float, lon: float, nord_m: float, est_m: float) -> tuple[float, float]:
    return lat + nord_m / 111_320, lon + est_m / (111_320 * math.cos(math.radians(lat)))


def _particella_edificata(z: Zornade, lat: float, lon: float) -> tuple[dict | None, int]:
    """Particella nel punto; se è una strada, la prima particella non stradale nei punti vicini."""
    part = z.particella_in_punto(lat, lon)
    if not part or str(part.get("kind") or "").lower() not in NON_EDIFICI:
        return part, 0
    for dn, de in INTORNO:
        p = z.particella_in_punto(*_sposta(lat, lon, dn, de))
        if p and str(p.get("kind") or "").lower() not in NON_EDIFICI:
            return p, int(round(math.hypot(dn, de)))
    return part, 0


def geolocalizza(df: pd.DataFrame, z: Zornade, comuni: pd.DataFrame, dettagli: bool = False,
                 anncsu: Indirizzario | None = None) -> pd.DataFrame:
    """comuni: elenco con istat, nome, belfiore, provincia (meteo_storico comuni.parquet o simile).
    anncsu: indirizzario ANNCSU locale (facoltativo, consigliato per gli indirizzi)."""
    per_nome = {str(n).strip().lower(): r for n, r in zip(comuni.nome, comuni.itertuples())}
    per_belf = {r.belfiore: r for r in comuni.itertuples()}
    out = []
    for i, r in enumerate(df.to_dict(orient="records"), 1):
        ris = {"metodo": None, "fonte_punto": None, "indirizzo_trovato": None, "esito": "non_trovato", "nota": "",
               "lat": None, "lon": None, "fid": None, "foglio_catasto": None, "mappale": None, "area_m2": None,
               "belfiore": None, "istat": None, "comune_catasto": None, "tipo_particella": None}
        dich = per_nome.get(str(r.get("comune", "")).strip().lower())
        try:
            part = None
            lat, lon = _num(r.get("lat")), _num(r.get("lon"))
            if lat is not None and lon is not None:
                ris["metodo"] = ris["fonte_punto"] = "coordinate"
                part = z.particella_in_punto(lat, lon)
                ris["lat"], ris["lon"] = lat, lon
            elif r.get("particella") and r.get("comune"):
                ris["metodo"] = ris["fonte_punto"] = "catasto"
                nome = dich.nome if dich is not None else r["comune"]   # Zornade vuole il nome, non il codice
                trovate = z.cerca_particella(nome, r.get("foglio") or None, r["particella"], r.get("sezione") or None)
                if len(trovate) > 1:
                    _aggiungi(ris, f"{len(trovate)} particelle corrispondenti: indicare foglio e sezione")
                if not trovate:
                    _aggiungi(ris, f"particella non trovata a {nome}, foglio {r.get('foglio') or '?'}, "
                                   f"mappale {r['particella']}")
                part = trovate[0] if trovate else None
            elif r.get("indirizzo"):
                ris["metodo"] = "indirizzo"
                via, civ = _via_civico(r)
                motivo = _anncsu(anncsu, dich, via, civ, ris) if anncsu is not None else "ANNCSU non fornito"
                if motivo:
                    geo = _geocodifica(z, via, civ, str(r.get("comune", "")).strip(), ris)
                    if geo:
                        ris["lat"], ris["lon"] = coordinate(geo)
                    elif anncsu is not None:
                        _aggiungi(ris, motivo)
                if ris["lat"] is not None:
                    part, spost = _particella_edificata(z, ris["lat"], ris["lon"])
                    if spost:
                        _aggiungi(ris, f"accesso sulla strada: usata la particella edificata a ~{spost} m")
            else:
                ris["nota"] = "riga senza coordinate, dati catastali o indirizzo"
            if part:
                mun = part.get("municipality") or {}
                plat, plon = coordinate(part)
                rif = da_riferimento(part.get("cadastral_reference"))
                ris.update({"fid": part.get("fid"), "foglio_catasto": part.get("foglio") or rif.get("foglio"),
                            "mappale": part.get("label"), "area_m2": part.get("area_m2"),
                            "belfiore": mun.get("code") or rif.get("belfiore"), "comune_catasto": mun.get("name"),
                            "tipo_particella": part.get("kind")})
                if rif.get("allegato", "0") != "0" or rif.get("sviluppo", "0") != "0":
                    _aggiungi(ris, f"foglio con allegato {rif['allegato']} / sviluppo {rif['sviluppo']}")
                tipo = str(part.get("kind") or "").lower()
                if tipo in NON_EDIFICI:
                    _aggiungi(ris, f"la particella è {NON_EDIFICI[tipo]}, non un immobile: controllare il punto")
                if ris["lat"] is None:
                    ris["lat"], ris["lon"] = plat, plon
                c = per_belf.get(ris["belfiore"])
                ris["istat"] = c.istat if c is not None else None
                # spostamento sulla particella edificata e fogli con allegato sono informazioni, non dubbi
                dubbi = [n for n in ris["nota"].split("; ")
                         if n and not n.startswith(("accesso sulla strada", "foglio con allegato") + INFORMATIVE)]
                ris["esito"] = "verificare" if dubbi else "ok"
                if dich is not None and ris["belfiore"] and dich.belfiore != ris["belfiore"]:
                    ris["esito"] = "verificare"
                    _aggiungi(ris, f"comune catastale {mun.get('name')} diverso da quello indicato")
                if dettagli and ris["fid"]:
                    ris["dettaglio"] = json.dumps(z.dettaglio(ris["fid"]), ensure_ascii=False)
            elif ris["lat"] is not None:
                ris["esito"] = "verificare"
                _aggiungi(ris, "punto trovato ma nessuna particella")
                if dich is not None:
                    ris["istat"], ris["belfiore"] = dich.istat, dich.belfiore
        except Exception as e:  # una riga in errore non ferma il lotto
            log.warning("Riga %s: %s", r.get("id"), e)
            ris["esito"], ris["nota"] = "errore", str(e)[:200]
        out.append({**r, **ris})
        if i % 50 == 0:
            log.info("Geolocalizzati %d/%d edifici (%d chiamate Zornade)", i, len(df), z.chiamate)
    return pd.DataFrame(out)


def fonti(df: pd.DataFrame) -> list[str]:
    """Fonti da citare per i risultati (oltre al link a Zornade, obbligatorio col piano gratuito)."""
    f = ["Catasto: Agenzia delle Entrate (CC BY 4.0), via Zornade", "ISTAT (CC BY 4.0)",
         "© OpenStreetMap contributors (ODbL)"]
    if "fonte_punto" in df and (df.fonte_punto == "ANNCSU").any():
        f.insert(1, ATTRIBUZIONE_ANNCSU)
    return f


def geojson(df: pd.DataFrame) -> dict:
    feats = []
    for r in df.to_dict(orient="records"):
        if r.get("lat") is None or pd.isna(r.get("lat")):
            continue
        prop = {k: (None if isinstance(v, float) and pd.isna(v) else v) for k, v in r.items()
                if k not in ("lat", "lon", "dettaglio")}
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
                      "properties": prop})
    # piano gratuito Zornade: l'attribuzione va mostrata come link cliccabile (attribution_html)
    return {"type": "FeatureCollection", "features": feats, "attribution": ATTRIBUZIONE,
            "attribution_url": ATTRIBUZIONE_URL, "attribution_html": ATTRIBUZIONE_HTML, "sources": fonti(df)}


def riepilogo(df: pd.DataFrame) -> str:
    c = df.esito.value_counts().to_dict()
    testo = (f"{len(df)} edifici: {c.get('ok', 0)} ok, {c.get('verificare', 0)} da verificare, "
             f"{c.get('non_trovato', 0)} non trovati, {c.get('errore', 0)} errori")
    if "fonte_punto" in df:
        f = df.fonte_punto.value_counts().to_dict()
        if f.get("ANNCSU") or f.get("Zornade"):
            testo += f" (indirizzi: {f.get('ANNCSU', 0)} da ANNCSU, {f.get('Zornade', 0)} da Zornade)"
    return testo
