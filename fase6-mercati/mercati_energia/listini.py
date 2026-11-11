"""Listini mensili pubblicati dalle centrali di committenza (11/11/2026, decisione di Paolo: si pubblicano i valori che
le centrali pubblicano).

Intercent-ER mette sulla pagina di ogni convenzione dell'energia elettrica uno zip `listini.zip` con un Excel per lotto
(`Listino_EE_19_L_1_<data>.xlsx`): per ogni fascia (F1, F2, F3) e per ogni mese il PUN medio mensile e il **prezzo**
(PUN + spread fisso, garanzie d'origine comprese), in €/kWh, IVA esclusa. Si legge **solo il prezzo**: le colonne del
PUN si scartano (dati GME, non si pubblicano finché non c'è la licenza).

Fonti, nell'ordine:
- la sezione `[listino]` del TOML di una convenzione: `url` dello zip (o di un .xlsx), scaricato ogni notte;
- la cartella `<archivio>/listini_manuali/<id della convenzione>/` con gli .xlsx o gli .zip copiati a mano (per esempio
  i listini 2025 della convenzione EE18, tolti dalla pagina quando la convenzione è scaduta); un file `listino.toml`
  nella stessa cartella può dire `centrale`, `titolo` e `serie` (l'id della convenzione di cui continua la serie).
- le convenzioni precedenti con gli stessi lotti: `precedenti = [{ id, titolo, url }]` nella sezione `[listino]`
  (per esempio EE18 per il 2025 accanto a EE19 per il 2026): stessa `serie`, così la pagina confronta i due anni.

Uscita: dataset `listini` dell'archivio (un file per anno), chiave convenzione + lotto + fascia + mese, `prezzo` con
la sua `unita` (€/MWh per l'energia elettrica, €/Smc per il gas; nei listini gas la «fascia» è l'uso).
I file scaricati sono trattati come non fidati: solo .xlsx dentro lo zip, letti con openpyxl in sola lettura e senza
formule, dimensioni limitate.
"""
from __future__ import annotations

import datetime as dt
import io
import logging
import re
import tomllib
import zipfile
from pathlib import Path

import httpx
import pandas as pd

from . import archivio

log = logging.getLogger(__name__)
DATASET = "listini"
CHIAVI = ["convenzione", "lotto", "fascia", "mese"]
MAX_BYTE = 20 * 1024 * 1024          # zip o Excel più grandi non si leggono
MAX_FILE_ZIP = 50
MESI = {m: i for i, m in enumerate(["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
                                    "settembre", "ottobre", "novembre", "dicembre"], 1)}
_RE_MESE = re.compile(r"(" + "|".join(MESI) + r")\s+(\d{4})", re.I)
FASCE = {"F0", "F1", "F2", "F3", "F23"}


def _testo(v) -> str:
    return "" if v is None else str(v).strip()


def _valore(v) -> float | None:
    """Numero da una cella: numero vero o testo con il punto o la virgola decimale («0.3706», «0,3706»)."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    t = _testo(v).replace(" ", "")
    if re.fullmatch(r"\d+(?:[.,]\d+)?", t):
        return float(t.replace(",", "."))
    return None


def _uso(testo: str) -> str:
    """Nome della variante dei listini gas, dalla denominazione dell'articolo («… NON TERMICHE», «… COGENERATORI …»)."""
    t = testo.upper()
    if "NON TERMIC" in t:
        return "Usi non termici"
    if "TERMIC" in t:
        return "Usi termici"
    if "COGEN" in t:
        return "Cogenerazione"
    return re.sub(r"\s+", " ", testo).strip() or "Prezzo"


def leggi_excel(dati: bytes, convenzione: str, centrale: str = "Intercent-ER", file: str = "") -> pd.DataFrame:
    """Righe (convenzione, centrale, lotto, fascia, mese, data, prezzo, unita, file) da un listino Intercent-ER in Excel.

    Colonne riconosciute dall'intestazione: «Numero Lotto»; la fascia («multiorari» o valori F0…F3) per l'energia
    elettrica, oppure, nei listini gas, l'uso dalla «DENOMINAZIONE ARTICOLO» (usi termici, non termici, cogenerazione:
    va nella stessa colonna `fascia`); le colonne del **prezzo** con mese e anno nel titolo («… Prezzo €/KWh gennaio
    2026 …», «… Prezzo €/Smc ottobre 2025 …»). Le colonne del solo PUN o del solo PSV (titolo con il mese ma senza
    «prezzo») e la colonna «PREZZO OFFERTO PER UM» (senza mese) non si leggono. €/kWh → €/MWh (2 decimali); €/Smc
    resta in €/Smc (4 decimali, come nel listino)."""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(dati), read_only=True, data_only=True)
    righe = []
    for ws in wb.worksheets:
        tabella = [list(r) for r in ws.iter_rows(values_only=True)]
        for i, intest in enumerate(tabella):
            testi = [_testo(c) for c in intest]
            c_lotto = next((j for j, t in enumerate(testi) if t.lower().startswith("numero lotto")), None)
            prezzi = {}
            for j, t in enumerate(testi):
                m = _RE_MESE.search(t.replace("\n", " "))
                if m and "prezzo" in t.lower():
                    if re.search(r"/\s*kwh", t, re.I):
                        unita, scala, dec = "€/MWh", 1000.0, 2
                    elif re.search(r"/\s*smc", t, re.I):
                        unita, scala, dec = "€/Smc", 1.0, 4
                    else:
                        unita, scala, dec = "€/MWh", 1.0, 2
                    prezzi[j] = (f"{int(m.group(2))}-{MESI[m.group(1).lower()]:02d}", unita, scala, dec)
            if c_lotto is None or not prezzi:
                continue
            c_fascia = next((j for j, t in enumerate(testi) if "multiorari" in t.lower() or t.lower() == "fascia"), None)
            c_desc = next((j for j, t in enumerate(testi) if t.upper().startswith("DENOMINAZIONE ARTICOLO")), None)
            gas = any(u == "€/Smc" for _, u, _, _ in prezzi.values())
            lotto = None
            for r in tabella[i + 1:]:
                if c_lotto < len(r) and _testo(r[c_lotto]):
                    lotto = _testo(r[c_lotto])
                if gas:
                    fascia = _uso(_testo(r[c_desc])) if c_desc is not None and c_desc < len(r) and _testo(r[c_desc]) else ""
                    if not _testo(r[c_lotto] if c_lotto < len(r) else None):
                        continue        # righe di nota sotto la tabella
                else:
                    fascia = _testo(r[c_fascia]).upper() if c_fascia is not None and c_fascia < len(r) else ""
                    if not fascia:   # fascia non trovata dal titolo: la prima cella F0…F3 della riga
                        fascia = next((_testo(c).upper() for c in r if _testo(c).upper() in FASCE), "")
                    if fascia not in FASCE:
                        continue
                if not fascia or lotto is None:
                    continue
                for j, (mese, unita, scala, dec) in prezzi.items():
                    v = _valore(r[j] if j < len(r) else None)
                    if v is not None and v > 0:
                        righe.append({"convenzione": convenzione, "centrale": centrale, "lotto": lotto, "fascia": fascia,
                                      "mese": mese, "data": dt.date.fromisoformat(f"{mese}-01"),
                                      "prezzo": round(v * scala, dec), "unita": unita, "file": file})
            break   # una sola tabella per foglio
    wb.close()
    return pd.DataFrame(righe)


_RE_LOTTO = re.compile(r"^\s*Lotto\s+(\d+)\s*:\s*(.+?)\s*$", re.I)


def leggi_consip(dati: bytes, convenzione: str, centrale: str = "Consip", file: str = "") -> pd.DataFrame:
    """Corrispettivi mensili Consip (11/11/2026, «EE22 - Corrispettivi - MMAA.xlsx» da acquistinretepa.it): un foglio
    per lotto («Lotto 6»), con il nome del lotto («Lotto 6: Emilia Romagna»), e la tabella «Forniture a Prezzo variabile»:
    riga d'intestazione con «Fascia oraria» e i mesi come date, poi una riga per fascia (F0, F1, F2, F3) con il prezzo
    variabile in €/MWh (PUN + spread del lotto, al netto delle perdite di rete). Si legge solo la prima tabella di
    ogni foglio; il foglio «PUN Index GME e PUN per fascia» non si legge."""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(dati), read_only=True, data_only=True)
    righe = []
    for ws in wb.worksheets:
        if not re.fullmatch(r"\s*Lotto\s+\d+\s*", ws.title):
            continue
        lotto, nome = None, ""
        mesi, c_fascia = {}, None
        for n, r in enumerate(ws.iter_rows(max_row=80, values_only=True)):
            celle = list(r)
            if lotto is None:
                for c in celle:
                    m = _RE_LOTTO.match(_testo(c))
                    if m:
                        lotto, nome = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip(" -")
                        break
            if not mesi:
                testi = [_testo(c).lower() for c in celle]
                if "fascia oraria" in testi:
                    c_fascia = testi.index("fascia oraria")
                    mesi = {j: f"{c.year}-{c.month:02d}" for j, c in enumerate(celle) if isinstance(c, dt.datetime)}
                continue
            fascia = _testo(celle[c_fascia]).upper() if c_fascia is not None and c_fascia < len(celle) else ""
            if fascia not in FASCE:
                break        # fine della prima tabella
            for j, mese in mesi.items():
                v = celle[j] if j < len(celle) else None
                if isinstance(v, (int, float)) and v > 0:
                    righe.append({"convenzione": convenzione, "centrale": centrale, "lotto": lotto or ws.title.split()[-1],
                                  "lotto_nome": nome, "fascia": fascia, "mese": mese,
                                  "data": dt.date.fromisoformat(f"{mese}-01"), "prezzo": round(float(v), 2),
                                  "unita": "€/MWh", "file": file})
    wb.close()
    return pd.DataFrame(righe)


def leggi_file(dati: bytes, nome: str, convenzione: str, centrale: str = "Intercent-ER",
               formato: str = "intercenter") -> pd.DataFrame:
    """Un .xlsx o uno .zip di .xlsx (solo i .xlsx dentro lo zip, nessun percorso seguito). `formato`: «intercenter»
    (listini per lotto) o «consip» (corrispettivi con un foglio per lotto)."""
    lettore = leggi_consip if formato == "consip" else leggi_excel
    if len(dati) > MAX_BYTE:
        raise ValueError(f"{nome}: oltre {MAX_BYTE // 1048576} MB")
    parti = []
    # anche un .xlsx è uno zip: si guarda dentro solo se non è un .xlsx (nome) e non contiene [Content_Types].xml
    zip_vero = False
    if not nome.lower().endswith(".xlsx") and zipfile.is_zipfile(io.BytesIO(dati)):
        with zipfile.ZipFile(io.BytesIO(dati)) as z:
            zip_vero = "[Content_Types].xml" not in z.namelist()
    if zip_vero:
        with zipfile.ZipFile(io.BytesIO(dati)) as z:
            voci = [v for v in z.infolist() if v.filename.lower().endswith(".xlsx") and not v.is_dir()][:MAX_FILE_ZIP]
            for v in voci:
                if v.file_size > MAX_BYTE:
                    continue
                parti.append(lettore(z.read(v), convenzione, centrale, Path(v.filename).name))
    else:
        parti.append(lettore(dati, convenzione, centrale, Path(nome).name))
    parti = [p for p in parti if not p.empty]
    return pd.concat(parti, ignore_index=True) if parti else pd.DataFrame()


def scarica(url: str) -> bytes:
    # il client tiene i cookie tra un rinvio e l'altro: acquistinretepa.it (Consip) passa per un accesso SSO anonimo
    with httpx.Client(timeout=90, follow_redirects=True, max_redirects=40,
                      headers={"User-Agent": "Mozilla/5.0 (compatible; EuGEnio; eugenio.statocritico.it)"}) as c:
        r = c.get(url)
        r.raise_for_status()
        if len(r.content) > MAX_BYTE:
            raise ValueError(f"{url}: oltre {MAX_BYTE // 1048576} MB")
        return r.content


def fonti(cartella_convenzioni: Path | None) -> list[dict]:
    """Le sezioni [listino] dei TOML delle convenzioni: id, centrale, titolo, url, lotti (etichette)."""
    out = []
    if not cartella_convenzioni or not Path(cartella_convenzioni).exists():
        return out
    for f in sorted(Path(cartella_convenzioni).glob("*.toml")):
        raw = tomllib.loads(f.read_text(encoding="utf-8"))
        li, conv = raw.get("listino"), raw.get("convenzione", {})
        if li and li.get("url"):
            serie = conv.get("id", f.stem)       # le precedenti stanno nella stessa serie (stessi lotti)
            base = {"serie": serie, "centrale": conv.get("ente", "Intercent-ER"), "lotti": li.get("lotti", {}),
                    "formato": li.get("formato", "intercenter"), "lotto_predefinito": str(li.get("lotto_predefinito", "")),
                    "nome": li.get("nome", conv.get("ente", ""))}
            out.append({**base, "id": serie, "titolo": conv.get("titolo", ""), "url": li["url"]})
            for pr in li.get("precedenti", []):
                if pr.get("url") and pr.get("id"):
                    out.append({**base, "id": pr["id"], "titolo": pr.get("titolo", pr["id"]), "url": pr["url"]})
    # listini di convenzioni che EuGEnio non calcola (solo i prezzi pubblicati): convenzioni/fonti/listini.toml
    extra = Path(cartella_convenzioni) / "fonti" / "listini.toml"
    if extra.exists():
        for li in tomllib.loads(extra.read_text(encoding="utf-8")).get("listino", []):
            if li.get("url") and li.get("id"):
                base = {"serie": li.get("serie", li["id"]), "centrale": li.get("centrale", ""), "lotti": li.get("lotti", {}),
                        "formato": li.get("formato", "intercenter"),
                        "lotto_predefinito": str(li.get("lotto_predefinito", "")), "nome": li.get("nome", "")}
                out.append({**base, "id": li["id"], "titolo": li.get("titolo", li["id"]), "url": li["url"]})
                for pr in li.get("precedenti", []):        # convenzioni precedenti con gli stessi lotti (11/11/2026)
                    if pr.get("url") and pr.get("id"):
                        out.append({**base, "id": pr["id"], "titolo": pr.get("titolo", pr["id"]), "url": pr["url"]})
    return out


def aggiorna(cartella: Path, cartella_convenzioni: Path | None) -> dict:
    """Scarica i listini delle convenzioni con [listino] e legge quelli copiati a mano. Righe scritte per fonte."""
    esito = {}
    for f in fonti(cartella_convenzioni):
        try:
            df = leggi_file(scarica(f["url"]), f["url"].split("?")[0].rstrip("/").split("/")[-1] or "listini.zip",
                            f["id"], f["centrale"], f.get("formato", "intercenter"))
            if not df.empty:
                df["serie"], df["titolo"] = f["serie"], f["titolo"]
            esito[f["id"]] = archivio.aggiorna(cartella, DATASET, df, CHIAVI, "data")
        except Exception as e:  # noqa: BLE001 - una fonte giù non ferma le altre
            log.warning("Listino %s: %s", f["id"], e)
            esito[f["id"]] = f"errore: {e}"
    manuali = Path(cartella) / "listini_manuali"
    for d in sorted(p for p in manuali.iterdir() if p.is_dir()) if manuali.exists() else []:
        meta = {}
        if (d / "listino.toml").exists():
            meta = tomllib.loads((d / "listino.toml").read_text(encoding="utf-8"))
        parti = []
        for p in sorted(d.iterdir()):
            if p.suffix.lower() in (".xlsx", ".zip"):
                try:
                    parti.append(leggi_file(p.read_bytes(), p.name, d.name, meta.get("centrale", "Intercent-ER"),
                                            meta.get("formato", "intercenter")))
                except Exception as e:  # noqa: BLE001
                    log.warning("Listino a mano %s: %s", p, e)
        parti = [x.assign(serie=meta.get("serie", d.name), titolo=meta.get("titolo", d.name)) for x in parti
                 if not x.empty]
        esito[d.name] = archivio.aggiorna(cartella, DATASET, pd.concat(parti, ignore_index=True), CHIAVI, "data") \
            if parti else 0
    return esito


def leggi(cartella: Path) -> pd.DataFrame:
    return archivio.leggi(Path(cartella), DATASET)
