"""Sorveglianza notturna delle fonti delle convenzioni (Intercent-ER, Consip, CET, ...) e del PSV ARERA.

Ogni notte, dopo i dati di mercato:
  1. legge le pagine da sorvegliare: quelle elencate in `convenzioni/fonti/centrali.toml` (elenchi delle
     convenzioni e delle gare, pagine di gare in corso) e quelle nella sezione `[sorveglianza]` di ogni
     convenzione. Una richiesta per pagina, condizionata (ETag / Last-Modified);
  2. se il testo di una pagina cambia, ne salva una copia e scarica i documenti collegati nuovi che
     interessano (listini, guide, esiti, capitolati, ...), con il testo estratto dai PDF;
  3. sulle pagine elenco segnala i collegamenti nuovi che parlano di energia elettrica o gas: nuove
     convenzioni o gare da aggiungere;
  4. cerca nei testi i valori indicati in `[[sorveglianza.valore]]` (spread, corrispettivi) e li confronta
     con quelli del file TOML. Se un valore è diverso e la regola dice `applica = true`, aggiorna il file
     (con una copia di sicurezza e un commento con data e fonte); altrimenti lo propone;
  5. controlla che il PSV day-ahead ARERA del mese scorso sia arrivato (dopo il giorno 7 del mese).

Si segnala solo ciò che è cambiato rispetto alla notte prima: una pagina che non risponde viene segnalata
alla terza notte di fila, poi una volta a settimana. Tutto sta in `<archivio>/sorveglianza/`.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import io
import json
import logging
import re
import shutil
import tomllib
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import httpx

log = logging.getLogger(__name__)

AGENTE = "Mozilla/5.0 (compatible; EuGEnio/1.0; +https://eugenio.statocritico.it)"
MAX_BYTE = 40_000_000
ESTENSIONI_DOC = (".pdf", ".xlsx", ".xls", ".csv", ".zip", ".docx", ".odt", ".ods")
DOCUMENTI_DEFAULT = r"listin|prezz|guida|esit|aggiudic|capitolat|convenzion|accordo|condizion|spread|dettaglio.econom"
PAROLE_DEFAULT = ["energia elettrica", "gas naturale", "fornitura di gas", "fornitura di energia"]
NUMERO = r"[0-9]+(?:[.,][0-9]+)?"


@dataclass
class Fonte:
    id: str
    url: str
    tipo: str = "pagina"                  # pagina | elenco
    centrale: str = ""
    convenzione: str | None = None        # id della convenzione a cui appartiene (se viene dal suo TOML)
    documenti: str = DOCUMENTI_DEFAULT    # regex (senza maiuscole) su indirizzo o testo del collegamento
    parole: list[str] = field(default_factory=lambda: list(PAROLE_DEFAULT))
    ignora: str = ""                      # regex di testo variabile da togliere prima dell'impronta


@dataclass
class Regola:
    convenzione: str
    file: Path
    lotto: str
    campo: str                            # spread | perdite | corrispettivi.fisso_pod_anno | ...
    cerca: str                            # regex con un gruppo numerico
    applica: bool = False
    fonti: str = ""                       # regex sul nome dei documenti in cui cercare (vuoto: tutti)
    scala: float = 1.0                    # es. 0,01 se il documento è in c€/Smc e il TOML in €/Smc


# ------------------------------------------------------------------------------------------ configurazione
def carica_fonti(cartella_convenzioni: Path) -> tuple[list[Fonte], list[Regola]]:
    """Fonti da `fonti/centrali.toml` e dalle sezioni [sorveglianza] dei file delle convenzioni."""
    fonti, regole = [], []
    centrali = Path(cartella_convenzioni) / "fonti" / "centrali.toml"
    if centrali.exists():
        for f in tomllib.loads(centrali.read_text(encoding="utf-8")).get("fonte", []):
            fonti.append(Fonte(**{k: v for k, v in f.items() if k in Fonte.__dataclass_fields__}))
    for file in sorted(Path(cartella_convenzioni).glob("*.toml")):
        raw = tomllib.loads(file.read_text(encoding="utf-8"))
        s, idc = raw.get("sorveglianza", {}), raw["convenzione"]["id"]
        for i, url in enumerate(s.get("pagine", [])):
            fonti.append(Fonte(id=f"{idc}-{i + 1}", url=url, convenzione=idc, centrale=raw["convenzione"]["ente"],
                               documenti=s.get("documenti", DOCUMENTI_DEFAULT), ignora=s.get("ignora", "")))
        for v in s.get("valore", []):
            regole.append(Regola(convenzione=idc, file=file, lotto=str(v["lotto"]), campo=v["campo"],
                                 cerca=v["cerca"], applica=bool(v.get("applica", False)), fonti=v.get("fonti", ""),
                                 scala=float(v.get("scala", 1.0))))
    return fonti, regole


# ------------------------------------------------------------------------------------------ pagine e testo
def testo_html(pagina: str) -> str:
    """Testo leggibile di una pagina, senza script, stili, menu e piè di pagina."""
    t = re.sub(r"(?is)<(script|style|noscript|svg|nav|header|footer)\b.*?</\1>", " ", pagina)
    m = re.search(r"(?is)<main\b.*?</main>", t)
    t = m.group(0) if m else t
    t = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h[1-6])>", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return "\n".join(r for r in (re.sub(r"[ \t\xa0]+", " ", x).strip() for x in t.splitlines()) if r)


def collegamenti(pagina: str, base: str) -> list[dict]:
    out, visti = [], set()
    for href, testo in re.findall(r'(?is)<a\b[^>]*?href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', pagina):
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        url = urljoin(base, html.unescape(href.strip()))
        if url not in visti:
            visti.add(url)
            out.append({"url": url, "testo": re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", testo))).strip()})
    return out


def _impronta(testo: str, ignora: str = "") -> str:
    if ignora:
        testo = re.sub(ignora, "", testo, flags=re.I)
    return hashlib.sha256(re.sub(r"\s+", " ", testo).strip().encode()).hexdigest()


def _e_documento(url: str) -> bool:
    p = unquote(urlparse(url).path).lower()
    return p.endswith(ESTENSIONI_DOC) or "@@download" in p or "displayattach" in p or "downloadallegato" in url.lower()


def _nome_file(url: str, risposta: httpx.Response | None = None) -> str:
    cd = (risposta.headers.get("content-disposition", "") if risposta is not None else "")
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', cd)
    nome = unquote(m.group(1)) if m else ""
    tv = re.search(r"(?i)TECHVALUE=([^*&]+)", unquote(url))     # allegati SATER (Intercent-ER)
    if not nome and tv:
        nome = tv.group(1)
    if not nome:
        parti = [x for x in unquote(urlparse(url).path).split("/") if x and not x.startswith("@@")]
        nome = parti[-1] if parti else "documento"
        if nome in ("file", "download") and len(parti) > 1:
            nome = parti[-2]
    nome = re.sub(r"[^\w.\-]+", "_", nome)[-120:]
    return nome or "documento"


def estrai_testo(nome: str, dati: bytes) -> str:
    """Testo di PDF, fogli di calcolo, CSV e ZIP (i file dentro lo ZIP, uno dopo l'altro)."""
    n = nome.lower()
    try:
        if n.endswith(".pdf") or dati[:5] == b"%PDF-":
            from pypdf import PdfReader
            return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(dati)).pages)
        if n.endswith((".xlsx", ".xls", ".ods")):
            import pandas as pd
            fogli = pd.read_excel(io.BytesIO(dati), sheet_name=None, header=None, dtype=str)
            return "\n".join(f"[{k}]\n" + v.fillna("").to_csv(sep=";", index=False, header=False) for k, v in fogli.items())
        if n.endswith(".csv"):
            return dati.decode("utf-8", errors="replace")
        if n.endswith(".zip") or dati[:2] == b"PK" and not n.endswith((".docx", ".odt")):
            with zipfile.ZipFile(io.BytesIO(dati)) as z:
                return "\n".join(f"[{i.filename}]\n" + estrai_testo(i.filename, z.read(i)) for i in z.infolist()
                                 if not i.is_dir() and i.file_size < MAX_BYTE)
        if n.endswith((".html", ".htm")):
            return testo_html(dati.decode("utf-8", errors="replace"))
    except Exception as e:  # un documento illeggibile non ferma la sorveglianza
        log.warning("Testo non estratto da %s: %s", nome, e)
    return ""


# ------------------------------------------------------------------------------------------ valori nel TOML
def _numero(s: str) -> float:
    s = s.strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return float(s)


def valore_attuale(file: Path, lotto: str, campo: str):
    raw = tomllib.loads(Path(file).read_text(encoding="utf-8"))
    for l in raw.get("lotto", []):
        if str(l.get("id")) == lotto:
            v = l
            for parte in campo.split("."):
                v = v.get(parte) if isinstance(v, dict) else None
            return v
    raise KeyError(f"{Path(file).name}: lotto {lotto} non trovato")


def imposta_valore(file: Path, lotto: str, campo: str, nuovo: float, nota: str, copie: Path | None = None) -> None:
    """Cambia un valore numerico di un lotto nel file TOML, lasciando intatto il resto (commenti compresi)."""
    file = Path(file)
    righe = file.read_text(encoding="utf-8").splitlines(keepends=True)
    *tabella, chiave = campo.split(".")
    sezione_voluta = ".".join(["lotto", *tabella])
    in_lotto, lotto_giusto, sezione, trovata = False, False, None, None
    for i, r in enumerate(righe):
        s = r.strip()
        if s.startswith("[[lotto]]"):
            in_lotto, lotto_giusto, sezione = True, False, "lotto"
            continue
        if s.startswith("["):
            if s.startswith("[lotto.") and in_lotto:
                sezione = s.strip("[]").strip()
            else:
                in_lotto = False
            continue
        if in_lotto and sezione == "lotto" and re.match(r'id\s*=\s*"?([^"\s#]+)"?', s):
            lotto_giusto = re.match(r'id\s*=\s*"?([^"\s#]+)"?', s).group(1) == lotto
        if in_lotto and lotto_giusto and sezione == sezione_voluta and re.match(rf"{re.escape(chiave)}\s*=", s):
            trovata = i
    if trovata is None:
        raise KeyError(f"{file.name}: campo {campo} del lotto {lotto} non trovato (le tabelle in linea non si aggiornano)")
    m = re.match(r"^(\s*" + re.escape(chiave) + r"\s*=\s*)(\"[^\"]*\"|[^#\s]+)(\s*)(#.*)?$", righe[trovata].rstrip("\n"))
    vecchio = m.group(2)
    righe[trovata] = f"{m.group(1)}{nuovo:g}{m.group(3) or '  '}# {nota}; prima: {vecchio}\n"
    if copie is not None:
        copie.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, copie / f"{file.stem}.{dt.datetime.now():%Y%m%d-%H%M%S}.toml")
    testo = "".join(righe)
    tomllib.loads(testo)    # se il risultato non è un TOML valido non si scrive nulla
    file.write_text(testo, encoding="utf-8")


def cerca_valori(regola: Regola, testi: dict[str, str]) -> list[float]:
    """Valori distinti trovati con la regex, nei testi il cui nome corrisponde a `regola.fonti`."""
    trovati = []
    for nome, testo in testi.items():
        if regola.fonti and not re.search(regola.fonti, nome, re.I):
            continue
        for m in re.finditer(regola.cerca, testo, re.I | re.S):
            try:
                v = round(_numero(m.group(1)) * regola.scala, 6)
            except (ValueError, IndexError):
                continue
            if v not in trovati:
                trovati.append(v)
    return trovati


# ------------------------------------------------------------------------------------------ esecuzione
class Sorveglianza:
    def __init__(self, cartella_archivio: Path, cartella_convenzioni: Path, client: httpx.Client | None = None,
                 oggi: dt.date | None = None):
        self.dir = Path(cartella_archivio) / "sorveglianza"
        self.convenzioni = Path(cartella_convenzioni)
        self.client = client or httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": AGENTE})
        self.oggi = oggi or dt.date.today()
        self.file_stato = self.dir / "stato.json"
        self.stato = json.loads(self.file_stato.read_text(encoding="utf-8")) if self.file_stato.exists() else {}
        self.stato.setdefault("pagine", {})
        self.stato.setdefault("documenti", {})
        self.stato.setdefault("valori", {})
        self.esito = {"controllate": 0, "cambiate": [], "documenti_nuovi": [], "nuove_gare": [], "valori_aggiornati": [],
                      "proposte": [], "avvisi": [], "pagine_in_errore": []}

    # -- pagine
    def _leggi_pagina(self, f: Fonte) -> None:
        st = self.stato["pagine"].setdefault(f.url, {})
        intest = {}
        if st.get("etag"):
            intest["If-None-Match"] = st["etag"]
        if st.get("last_modified"):
            intest["If-Modified-Since"] = st["last_modified"]
        try:
            r = self.client.get(f.url, headers=intest)
            if r.status_code == 304:
                st.update(controllata=str(self.oggi), errori=0)
                self.esito["controllate"] += 1
                return
            r.raise_for_status()
        except Exception as e:
            st["errori"] = st.get("errori", 0) + 1
            st["ultimo_errore"] = f"{type(e).__name__}: {e}"[:300]
            if st["errori"] == 3 or (st["errori"] > 3 and st["errori"] % 7 == 3):
                self.esito["pagine_in_errore"].append({"fonte": f.id, "url": f.url, "notti": st["errori"],
                                                       "errore": st["ultimo_errore"]})
            return
        self.esito["controllate"] += 1
        pagina = r.text
        testo, link = testo_html(pagina), collegamenti(pagina, str(r.url))
        impronta = _impronta(testo, f.ignora)
        prima_volta = "impronta" not in st
        cambiata = not prima_volta and impronta != st["impronta"]
        cartella = self.dir / "pagine" / re.sub(r"[^\w\-]+", "_", f.id)
        if prima_volta or cambiata:
            cartella.mkdir(parents=True, exist_ok=True)
            (cartella / f"{self.oggi}_{impronta[:8]}.txt").write_text(f"{f.url}\n\n{testo}", encoding="utf-8")
        link_prima = set(st.get("link", []))
        nuovi = [l for l in link if l["url"] not in link_prima]
        if cambiata:
            self.esito["cambiate"].append({"fonte": f.id, "centrale": f.centrale, "url": f.url})
        if f.tipo == "elenco" and not prima_volta:
            for l in nuovi:
                if any(p in l["testo"].lower() or p.replace(" ", "-") in l["url"].lower() for p in f.parole):
                    self.esito["nuove_gare"].append({"fonte": f.id, "centrale": f.centrale, "titolo": l["testo"],
                                                     "url": l["url"]})
        if f.tipo == "pagina" and (prima_volta or nuovi):
            for l in (link if prima_volta else nuovi):
                # nome del file e testo del collegamento, non l'indirizzo intero (che può contenere "convenzioni")
                if _e_documento(l["url"]) and re.search(f.documenti, f"{_nome_file(l['url'])} {l['testo']}", re.I):
                    self._scarica_documento(f, l, segnala=not prima_volta)
        st.update(impronta=impronta, link=[l["url"] for l in link], controllata=str(self.oggi), errori=0,
                  etag=r.headers.get("etag"), last_modified=r.headers.get("last-modified"))
        if cambiata or prima_volta:
            st["cambiata"] = str(self.oggi)
        st["testo"] = str(cartella / f"{self.oggi}_{impronta[:8]}.txt") if (prima_volta or cambiata) else st.get("testo")

    def _scarica_documento(self, f: Fonte, l: dict, segnala: bool) -> None:
        if l["url"] in self.stato["documenti"]:
            return
        try:
            r = self.client.get(l["url"])
            r.raise_for_status()
            dati = r.content
            if len(dati) > MAX_BYTE:
                raise ValueError(f"file troppo grande ({len(dati) / 1e6:.0f} MB)")
        except Exception as e:
            log.warning("Documento non scaricato %s: %s", l["url"], e)
            return
        sha = hashlib.sha256(dati).hexdigest()
        nome = _nome_file(l["url"], r)
        cartella = self.dir / "documenti" / re.sub(r"[^\w\-]+", "_", f.convenzione or f.id)
        cartella.mkdir(parents=True, exist_ok=True)
        dest = cartella / f"{sha[:8]}_{nome}"
        dest.write_bytes(dati)
        testo = estrai_testo(nome, dati)
        if testo:
            dest.with_name(dest.name + ".txt").write_text(testo, encoding="utf-8")
        self.stato["documenti"][l["url"]] = {"file": str(dest), "sha256": sha, "titolo": l["testo"], "fonte": f.id,
                                            "convenzione": f.convenzione, "scaricato": str(self.oggi)}
        if segnala:
            self.esito["documenti_nuovi"].append({"fonte": f.id, "convenzione": f.convenzione, "titolo": l["testo"],
                                                  "url": l["url"], "file": dest.name})

    # -- valori delle convenzioni
    def _testi_convenzione(self, fonti: list[Fonte], idc: str) -> dict[str, str]:
        testi = {}
        for f in fonti:
            if f.convenzione == idc:
                p = self.stato["pagine"].get(f.url, {}).get("testo")
                if p and Path(p).exists():
                    testi[f"pagina {f.id}"] = Path(p).read_text(encoding="utf-8")
        for url, d in self.stato["documenti"].items():
            t = Path(d["file"] + ".txt")
            if d.get("convenzione") == idc and t.exists():
                testi[f"{Path(d['file']).name} {d.get('titolo', '')}"] = t.read_text(encoding="utf-8")
        return testi

    def _verifica_valori(self, fonti: list[Fonte], regole: list[Regola]) -> None:
        for g in regole:
            chiave = f"{g.convenzione}|{g.lotto}|{g.campo}"
            testi = self._testi_convenzione(fonti, g.convenzione)
            if not testi:
                continue
            trovati = cerca_valori(g, testi)
            try:
                attuale = valore_attuale(g.file, g.lotto, g.campo)
            except KeyError as e:         # lotto rinominato nel file: la regola va corretta
                self.esito["avvisi"].append(f"regola di sorveglianza non applicabile: {e}")
                continue
            if len(trovati) == 1:
                esito = "uguale" if isinstance(attuale, (int, float)) and abs(trovati[0] - attuale) < 1e-9 else "diverso"
            else:
                esito = "non_trovato" if not trovati else "ambiguo"
            situazione, prima = f"{esito}:{trovati}", self.stato["valori"].get(chiave, "")
            if prima == situazione:
                continue          # già segnalato una notte precedente
            self.stato["valori"][chiave] = situazione
            if esito == "non_trovato" and not prima.startswith(("uguale", "diverso")):
                continue          # mai trovato finora (documento non ancora pubblicato): niente da dire
            voce = {"convenzione": g.convenzione, "lotto": g.lotto, "campo": g.campo, "nel_file": attuale,
                    "trovati": trovati, "esito": esito}
            if esito == "diverso" and g.applica:
                try:
                    imposta_valore(g.file, g.lotto, g.campo, trovati[0],
                                   f"aggiornato dalla sorveglianza il {self.oggi}", self.dir / "copie_toml")
                    self.stato["valori"][chiave] = f"uguale:{trovati}"
                    self.esito["valori_aggiornati"].append(voce)
                    continue
                except (KeyError, ValueError, AttributeError) as e:   # es. spread scritto per fascia { F1 = .. }
                    voce["nota"] = f"non aggiornato da solo: {e}"
            if esito != "uguale":
                self.esito["proposte"].append(voce)

    # -- PSV ARERA
    def _verifica_psv(self, cartella_archivio: Path) -> None:
        if self.oggi.day <= 7:
            return
        mese = (self.oggi.replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")
        if self.stato.get("psv_segnalato") == mese:
            return
        try:
            import pandas as pd
            d = Path(cartella_archivio) / "indici_importati"
            df = pd.concat([pd.read_parquet(p) for p in d.glob("*.parquet")]) if d.exists() else pd.DataFrame()
            presente = not df.empty and ((df.indice == "PSV_DA") & (df.mese == mese)).any()
        except Exception:
            presente = False
        if not presente:
            self.esito["avvisi"].append(f"PSV day-ahead ARERA di {mese} non ancora in archivio (CMEM,m attesa nei "
                                        "primi due giorni lavorativi del mese)")
            self.stato["psv_segnalato"] = mese

    def esegui(self, cartella_archivio: Path | None = None) -> dict:
        fonti, regole = carica_fonti(self.convenzioni)
        for f in fonti:
            self._leggi_pagina(f)
        self._verifica_valori(fonti, regole)
        if cartella_archivio is not None:
            self._verifica_psv(cartella_archivio)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.file_stato.write_text(json.dumps(self.stato, ensure_ascii=False, indent=1), encoding="utf-8")
        self.esito["da_segnalare"] = any(self.esito[k] for k in ("cambiate", "documenti_nuovi", "nuove_gare",
                                                                 "valori_aggiornati", "proposte", "avvisi",
                                                                 "pagine_in_errore"))
        return self.esito


def esegui(cartella_archivio: Path, cartella_convenzioni: Path) -> dict:
    return Sorveglianza(cartella_archivio, cartella_convenzioni).esegui(cartella_archivio)


def riepilogo(esito: dict) -> str:
    """Testo dell'email all'amministratore."""
    r = []
    if esito["valori_aggiornati"]:
        r.append("VALORI AGGIORNATI DA SOLI nei file delle convenzioni (ricopiarli anche nel repository):")
        r += [f"  - {v['convenzione']} lotto {v['lotto']} {v['campo']}: {v['nel_file']} → {v['trovati'][0]}"
              for v in esito["valori_aggiornati"]]
    if esito["proposte"]:
        r.append("DA CONTROLLARE A MANO:")
        for v in esito["proposte"]:
            spiega = {"diverso": f"nel file {v['nel_file']}, nei documenti {v['trovati'][0]}",
                      "ambiguo": f"nel file {v['nel_file']}, nei documenti più valori {v['trovati']}",
                      "non_trovato": "valore non più trovato nei documenti (formato cambiato?)"}[v["esito"]]
            r.append(f"  - {v['convenzione']} lotto {v['lotto']} {v['campo']}: {spiega}"
                     + (f" ({v['nota']})" if v.get("nota") else ""))
    if esito["nuove_gare"]:
        r.append("POSSIBILI NUOVE CONVENZIONI O GARE (aggiungere un file TOML):")
        r += [f"  - {g['centrale']}: {g['titolo']}\n    {g['url']}" for g in esito["nuove_gare"]]
    if esito["documenti_nuovi"]:
        r.append("DOCUMENTI NUOVI SCARICATI:")
        r += [f"  - {d['convenzione'] or d['fonte']}: {d['titolo'] or d['file']}\n    {d['url']}"
              for d in esito["documenti_nuovi"]]
    if esito["cambiate"]:
        r.append("PAGINE CAMBIATE:")
        r += [f"  - {c['centrale']} ({c['fonte']}): {c['url']}" for c in esito["cambiate"]]
    if esito["avvisi"]:
        r.append("AVVISI:")
        r += [f"  - {a}" for a in esito["avvisi"]]
    if esito["pagine_in_errore"]:
        r.append("PAGINE CHE NON RISPONDONO:")
        r += [f"  - {p['fonte']} da {p['notti']} notti: {p['errore']}\n    {p['url']}" for p in esito["pagine_in_errore"]]
    return "\n".join(r)
