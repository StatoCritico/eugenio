"""Report scaricabili: un modello di documento generico e tre renderer (docx, pdf, xlsx).

Il documento è indipendente dal formato: titolo, sottotitolo, data, sezioni fatte di blocchi
(paragrafo, elenco, tabella, coppie chiave/valore, immagine PNG o SVG, avvertenza) e, in fondo,
le fonti e attribuzioni. Ogni file porta l'intestazione "Prodotto da EuGEnio – eugenio.statocritico.it", nel piè
di pagina un'avvertenza breve (gratuità e assenza di garanzia, uso dell'intelligenza artificiale, dove segnalare
gli errori) con il numero di pagina e, in fondo al documento, il testo completo delle avvertenze.

Tutto avviene in memoria: `genera()` restituisce i byte del file e non scrive nulla su disco.

Convenzioni:
  * nei documenti (docx, pdf) numeri e date sono in formato italiano: 1.234,56 e 27/10/2026;
  * in xlsx i numeri restano numeri (con formato di cella) e le date ISO diventano date di Excel;
  * le stringhe di una tabella che sono date o date/ore ISO (2026-10-27, 2026-10-27T13:00+01:00)
    sono riconosciute e formattate; le date/ore con fuso sono riportate all'ora italiana.

Per un nuovo tipo di report non serve toccare questo file: basta costruire un `Documento`
(vedi `report_servizi.py`).
"""
from __future__ import annotations

import base64
from pathlib import Path
import datetime as dt
import io
import logging
import math
import re
import unicodedata
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Literal, Union
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from . import config as C

log = logging.getLogger(__name__)

SITO = "https://eugenio.statocritico.it"
CONTATTI = f"{SITO}/contatti.html"
INTESTAZIONE = "Prodotto da EuGEnio – eugenio.statocritico.it"
PIE_DI_PAGINA = INTESTAZIONE          # nome storico: metadati dei file (commenti, creatore)
# Avvertenza breve del piè di pagina (Word e PDF: due righe in carattere piccolo; coerente con la FAQ
# "I dati sono garantiti?", faq.html#garanzia). In Excel l'intestazione e il piè di stampa hanno un limite
# di 255 caratteri: per questo c'è una versione più corta.
# Licenza dei dati elaborati e dei report (il codice resta AGPL-3.0): CC BY 4.0, cioè riuso libero, anche con
# modifiche, a condizione di citare EuGEnio come fonte. Gli stessi testi sono in licenza.html (#dati) e in faq.html#riuso.
LICENZA_DATI = ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/deed.it")
CITAZIONE = "Fonte: EuGEnio – eugenio.statocritico.it"
LICENZA_PAGINA = f"{SITO}/licenza.html#dati"
PIE_AVVERTENZA = ("Servizio gratuito e senza garanzia: dati calcolati o reperiti con sistemi automatici e verificati "
                  "a campione; nessuna responsabilità per errori nei dati, nelle previsioni o nell'uso del report. "
                  "Sviluppato anche con l'intelligenza artificiale; le previsioni usano il modello TiRex-2. "
                  f"Riuso libero con licenza CC BY 4.0 citando «{CITAZIONE}». "
                  "Segnala gli errori: eugenio.statocritico.it/contatti.html")
# Excel: intestazione e piè di stampa, codici di formato compresi, non possono superare 255 caratteri
PIE_AVVERTENZA_XLSX = ("Prodotto da EuGEnio. Servizio gratuito e senza garanzia: dati automatici verificati a campione. "
                       f"Riuso CC BY 4.0 citando «{CITAZIONE}». "
                       "Vedi foglio Info. Errori: eugenio.statocritico.it/contatti.html")
TITOLO_AVVERTENZE = "Avvertenze e limiti di responsabilità"
TESTO_LICENZA = (
    "Licenza: questo report e i dati elaborati che contiene sono distribuiti con licenza Creative Commons "
    f"Attribuzione 4.0 Internazionale (CC BY 4.0, {LICENZA_DATI[1]}). Si possono riutilizzare, anche modificati, "
    "a condizione di citare EuGEnio come fonte nei documenti che li usano, per esempio: "
    f"«{CITAZIONE}, report del giorno/mese/anno», e di mantenere le attribuzioni delle fonti originali elencate "
    "in «Fonti e attribuzioni». I dati di origine restano soggetti alle loro licenze: per esempio le particelle "
    "e gli indirizzi trovati con Zornade richiedono il collegamento «Dati elaborati da Zornade» (zornade.com) e "
    "non si possono ridistribuire in blocco come dati grezzi; gli eventuali valori ricavati dagli anni tipo del CTI "
    "non hanno la licenza CC BY: si possono citare, ma per ridistribuirli serve il permesso del CTI. "
    "Chi usa il report non deve presentarlo come documento ufficiale né come approvato da EuGEnio. I testi normativi, come il DPR 412/93, sono atti "
    "pubblici: la citazione riguarda le nostre elaborazioni e raccolte. Il codice di EuGEnio ha licenza AGPL-3.0. "
    f"Dettagli: {LICENZA_PAGINA}")
AVVERTENZE = (
    "EuGEnio è un servizio gratuito e senza scopo di lucro. I dati di questo report sono calcolati o reperiti con "
    "sistemi automatici e verificati a campione da esseri umani: abbiamo fatto quanto materialmente possibile per "
    "renderli affidabili, ma non sono garantiti. EuGEnio non è responsabile di eventuali errori: né di quelli "
    "contenuti nei dati, né di quelli derivanti dai risultati delle previsioni o dalla lettura, diffusione o riuso "
    "di questo report, che non sostituisce le verifiche di un tecnico né i dati ufficiali richiesti dalle norme.",
    "Il servizio, il suo codice e i suoi testi sono stati sviluppati anche con strumenti di intelligenza "
    "artificiale. Le previsioni dei consumi usano TiRex-2, un modello di apprendimento automatico eseguito sul "
    "nostro server; gli altri numeri del report sono prodotti da calcoli fissi, documentati nella pagina Come funziona.",
    TESTO_LICENZA,
    f"Sito: {SITO}. Se trovi degli errori, segnalali: {CONTATTI}",
)
# Logo nell'intestazione: il PNG accanto a questo file (logo orizzontale Corallo chiaro, sfondo trasparente).
# Word e PDF lo mettono a sinistra dell'intestazione di pagina, Excel in cima al foglio Info (se c'è Pillow).
# Senza il file i report escono senza logo.
_LOGO = Path(__file__).with_name("logo_eugenio.png")   # logo orizzontale (simbolo + scritta)
LOGO_PNG: bytes | None = _LOGO.read_bytes() if _LOGO.exists() else None
LOGO_ALTEZZA_CM = 1.2      # altezza del logo nel foglio Info di Excel (12 mm, note sullo stile § 5)
# Nel logo dell'intestazione (logo_eugenio.png, simbolo + scritta) la base del simbolo è allineata alla linea di base
# della scritta e il tetto sporge un po' sopra la E: sul PNG (alto 273 px, tagliato
# sulla linea di base, così in Word poggia sulla stessa riga del titolo) la E va dal pixel 39 al 269.
LOGO_MAIUSCOLA = 230 / 273   # altezza della E sul PNG del logo (il tetto del simbolo sporge sopra)
LOGO_CIMA_MAIUSCOLA = 39 / 273
ALTEZZA_E_MM = 4.0         # altezza della E di EuGEnio nell'intestazione di pagina (Word e PDF)
# Colori della stampa, uguali per tutti i vestiti del sito: testo nero, nessun fondo colorato, collegamenti in blu
# scuro sottolineati. A colori restano solo il logo e i grafici.
COLORE_LINK = "1A3F8F"                                               # esadecimale per Word ed Excel
COLORE_LINK_RGB = tuple(int(COLORE_LINK[i:i + 2], 16) for i in (0, 2, 4))   # (26, 63, 143) per il PDF
# Serie per i grafici dei report (futuri): pensata per chi confonde rosso e verde e per la stampa in bianco e nero,
# quindi ogni serie ha anche un tratto e un retino suoi. "tratto": lunghezze di tratto e vuoto in punti (None =
# linea continua); "retino": riempimento delle barre (nomi pensati per i motivi di matplotlib/openpyxl).
SERIE_STAMPA = (
    {"nome": "S1", "colore": "#1F3A6E", "linea": "continua", "tratto": None, "barre": "piene", "retino": None},
    {"nome": "S2", "colore": "#C4532F", "linea": "tratteggio 8-4", "tratto": (8, 4), "barre": "righe oblique /", "retino": "/"},
    {"nome": "S3", "colore": "#4F86C6", "linea": "punti 2-3", "tratto": (2, 3), "barre": "puntini", "retino": "."},
    {"nome": "S4", "colore": "#B57D00", "linea": "tratto-punto 10-3-2-3", "tratto": (10, 3, 2, 3), "barre": "righe oblique \\", "retino": "\\"},
    {"nome": "S5", "colore": "#7A2E6A", "linea": "tratto lungo 14-6", "tratto": (14, 6), "barre": "quadretti", "retino": "+"},
    {"nome": "S6", "colore": "#7F7F7F", "linea": "puntini radi 1-5", "tratto": (1, 5), "barre": "vuote, bordo a puntini", "retino": None},
)
FUSO = ZoneInfo("Europe/Rome")
FORMATI = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre",
        "ottobre", "novembre", "dicembre"]

# ============================================================================================ modello
Testo = Annotated[str, StringConstraints(max_length=C.REPORT_MAX_TESTO)]
Breve = Annotated[str, StringConstraints(max_length=300)]
Cella = Union[bool, int, float, str, None]   # bool prima di int: True non deve diventare 1


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Paragrafo(_Base):
    tipo: Literal["paragrafo"] = "paragrafo"
    testo: Testo


class Elenco(_Base):
    tipo: Literal["elenco"] = "elenco"
    voci: list[Testo] = Field(max_length=1000)
    numerato: bool = False


class Tabella(_Base):
    """`decimali`, se presente, ha un valore per colonna (None = automatico: 0 per gli interi, 2 per i decimali)."""
    tipo: Literal["tabella"] = "tabella"
    titolo: Breve | None = None
    intestazioni: list[Breve] = Field(min_length=1, max_length=C.REPORT_MAX_COLONNE)
    righe: list[list[Cella]] = Field(max_length=C.REPORT_MAX_RIGHE)
    decimali: list[Annotated[int, Field(ge=0, le=8)] | None] | None = None
    nota: Testo | None = None

    @model_validator(mode="after")
    def _forma(self):
        n = len(self.intestazioni)
        for i, r in enumerate(self.righe):
            if len(r) > n:
                raise ValueError(f"la riga {i + 1} ha {len(r)} celle ma le intestazioni sono {n}")
            for c in r:
                if isinstance(c, str) and len(c) > C.REPORT_MAX_TESTO:
                    raise ValueError("cella troppo lunga")
        if self.decimali is not None and len(self.decimali) != n:
            raise ValueError("decimali deve avere un valore per colonna")
        return self


class Voce(_Base):
    chiave: Breve
    valore: Cella | Testo = None
    unita: Breve | None = None
    decimali: Annotated[int, Field(ge=0, le=8)] | None = None


class ChiaveValore(_Base):
    tipo: Literal["chiave_valore"] = "chiave_valore"
    titolo: Breve | None = None
    voci: list[Voce] = Field(max_length=500)


class Immagine(_Base):
    """Immagine in base64. PNG in tutti i documenti; SVG solo nel PDF (in docx resta la didascalia,
    in xlsx le immagini non sono incluse)."""
    tipo: Literal["immagine"] = "immagine"
    formato: Literal["png", "svg"]
    dati: str = Field(max_length=C.REPORT_MAX_IMMAGINE_KB * 1024 * 4 // 3 + 4)
    didascalia: Breve | None = None
    larghezza_cm: float = Field(16, gt=1, le=18)

    @field_validator("dati")
    @classmethod
    def _base64(cls, v: str) -> str:
        v = v.split(",", 1)[1] if v.startswith("data:") else v      # accetta anche un data URL
        try:
            base64.b64decode(v, validate=True)
        except Exception:
            raise ValueError("immagine non in base64")
        return v

    @model_validator(mode="after")
    def _contenuto(self):
        b = self.byte()
        if len(b) > C.REPORT_MAX_IMMAGINE_KB * 1024:
            raise ValueError(f"immagine troppo grande (massimo {C.REPORT_MAX_IMMAGINE_KB} kB)")
        if self.formato == "png" and not b.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("i dati non sono un PNG")
        if self.formato == "svg":
            t = b[:4096].decode("utf-8", "replace").lower()
            tutto = b.decode("utf-8", "replace").lower()
            if "<svg" not in t:
                raise ValueError("i dati non sono un SVG")
            # niente risorse esterne, script o entità: l'SVG deve essere autonomo
            if any(x in tutto for x in ("<image", "<script", "<!entity", "<foreignobject", "href=\"http",
                                        "href='http", "href=\"file", "href='file")):
                raise ValueError("SVG con contenuti non ammessi (immagini, script o riferimenti esterni)")
        return self

    def byte(self) -> bytes:
        return base64.b64decode(self.dati)


class Avvertenza(_Base):
    tipo: Literal["avvertenza"] = "avvertenza"
    testo: Testo
    livello: Literal["attenzione", "info"] = "attenzione"


Blocco = Annotated[Union[Paragrafo, Elenco, Tabella, ChiaveValore, Immagine, Avvertenza], Field(discriminator="tipo")]


class Sezione(_Base):
    titolo: Breve | None = None
    blocchi: list[Blocco] = Field(default_factory=list, max_length=C.REPORT_MAX_BLOCCHI)


class Fonte(_Base):
    testo: Annotated[str, StringConstraints(min_length=1, max_length=1000)]
    url: Annotated[str, StringConstraints(max_length=500, pattern=r"^https?://\S+$")] | None = None


class Documento(_Base):
    titolo: Annotated[str, StringConstraints(min_length=1, max_length=300)]
    sottotitolo: Breve | None = None
    data: dt.date | dt.datetime | None = None          # vuota = oggi
    nome_file: Annotated[str, StringConstraints(max_length=120)] | None = None   # senza estensione
    sezioni: list[Sezione] = Field(default_factory=list, max_length=C.REPORT_MAX_SEZIONI)
    fonti: list[Fonte] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def _totali(self):
        blocchi = [b for s in self.sezioni for b in s.blocchi]
        righe = sum(len(b.righe) for b in blocchi if isinstance(b, Tabella))
        if righe > C.REPORT_MAX_RIGHE_TOTALI:
            raise ValueError(f"troppe righe nelle tabelle ({righe}): massimo {C.REPORT_MAX_RIGHE_TOTALI}")
        if sum(isinstance(b, Immagine) for b in blocchi) > C.REPORT_MAX_IMMAGINI:
            raise ValueError(f"troppe immagini: massimo {C.REPORT_MAX_IMMAGINI}")
        return self

    def giorno(self) -> dt.date:
        if self.data is None:
            return dt.datetime.now(FUSO).date()
        return self.data.date() if isinstance(self.data, dt.datetime) else self.data


# ============================================================================================ formati
_RE_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RE_DATA_ORA = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?$")


def come_data(v) -> dt.date | dt.datetime | None:
    """Data o data/ora (senza fuso, in ora italiana) se `v` è una stringa ISO, altrimenti None."""
    if not isinstance(v, str):
        return None
    try:
        if _RE_DATA.match(v):
            return dt.date.fromisoformat(v)
        if _RE_DATA_ORA.match(v):
            t = dt.datetime.fromisoformat(v)
            return t.astimezone(FUSO).replace(tzinfo=None) if t.tzinfo else t
    except ValueError:
        return None
    return None


def numero(x: float | int, decimali: int | None = None) -> str:
    """1234.5 → '1.234,50' (separatore delle migliaia: punto; decimali: virgola)."""
    if isinstance(x, float) and not math.isfinite(x):
        return "—"
    if decimali is None:
        decimali = 0 if isinstance(x, int) else 2
    # arrotondamento "commerciale" (5,25 → 5,3), non quello del binario/pari di Python
    q = Decimal(str(x)).quantize(Decimal(1).scaleb(-decimali), rounding=ROUND_HALF_UP)
    if q == 0:
        q = abs(q)      # niente "-0,0"
    s =f"{q:,.{decimali}f}"
    return s.replace(",", "\u0001").replace(".", ",").replace("\u0001", ".")


def data_it(d: dt.date | dt.datetime, estesa: bool = False) -> str:
    if estesa:
        return f"{d.day} {MESI[d.month - 1]} {d.year}"
    if isinstance(d, dt.datetime):
        return d.strftime("%d/%m/%Y %H:%M")
    return d.strftime("%d/%m/%Y")


def testo_cella(v, decimali: int | None = None) -> str:
    """Valore di una cella come testo per docx e pdf."""
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "sì" if v else "no"
    if isinstance(v, (int, float)):
        return numero(v, decimali)
    d = come_data(v)
    return data_it(d) if d is not None else str(v)


def _numerica(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _colonne_numeriche(t: Tabella) -> list[bool]:
    """Colonna numerica se la maggior parte delle celle non vuote è un numero: si allinea a destra."""
    out = []
    for j in range(len(t.intestazioni)):
        vals = [r[j] for r in t.righe if j < len(r) and r[j] is not None]
        out.append(bool(vals) and sum(map(_numerica, vals)) * 2 > len(vals))
    return out


def _dec(t: Tabella, j: int) -> int | None:
    return t.decimali[j] if t.decimali else None


def nome_file(doc: Documento, formato: str) -> str:
    """Nome di file pulito (lettere ASCII, cifre, trattini bassi): `nome_file` se indicato
    (es. clima_legge10_037006), altrimenti il titolo seguito dalla data."""
    base = doc.nome_file or f"{doc.titolo}_{doc.giorno():%Y%m%d}"
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    base = re.sub(r"[^A-Za-z0-9]+", "_", base).strip("_").lower()[:80] or "report"
    return f"{base}.{formato}"


_ERRORI = {"missing": "campo obbligatorio", "extra_forbidden": "campo non previsto", "too_long": "troppi elementi",
           "string_too_long": "testo troppo lungo", "string_too_short": "testo vuoto", "too_short": "troppo pochi elementi",
           "string_pattern_mismatch": "formato non valido", "literal_error": "valore non ammesso",
           "union_tag_invalid": "tipo di blocco non ammesso", "union_tag_not_found": "manca il tipo del blocco",
           "json_invalid": "JSON non valido", "date_from_datetime_parsing": "data non valida",
           "less_than_equal": "valore troppo grande", "greater_than": "valore troppo piccolo",
           "greater_than_equal": "valore troppo piccolo", "int_parsing": "serve un numero intero",
           "model_type": "serve un oggetto", "list_type": "serve un elenco", "string_type": "serve un testo"}


def errori_in_italiano(e) -> str:
    """Riassunto in italiano di una pydantic.ValidationError (senza riportare i dati ricevuti)."""
    parti = []
    for x in e.errors(include_url=False, include_input=False, include_context=True)[:5]:
        dove = ".".join(str(p) for p in x.get("loc", ()) if p not in ("function-after",)) or "documento"
        if x.get("type") == "value_error":
            msg = str(x.get("msg", "")).removeprefix("Value error, ")
        else:
            msg = _ERRORI.get(x.get("type"), x.get("msg", "non valido"))
        parti.append(f"{dove}: {msg}")
    n = e.error_count()
    return "Documento non valido – " + "; ".join(parti) + (f" (e altri {n - 5} errori)" if n > 5 else "")


# ============================================================================================ docx
def _docx(doc: Documento) -> bytes:
    from docx import Document as Docx
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor, Mm

    d = Docx()
    d.core_properties.title = doc.titolo
    d.core_properties.author = "EuGEnio"
    d.core_properties.comments = PIE_DI_PAGINA
    st = d.styles["Normal"]
    st.font.size = Pt(10)
    sez = d.sections[0]
    sez.page_width, sez.page_height = Mm(210), Mm(297)         # A4 verticale (il modello di python-docx è Letter)
    sez.left_margin = sez.right_margin = Cm(2)
    sez.top_margin = sez.bottom_margin = Cm(2)

    # stile sobrio: testo solo nero, nessun fondo colorato; i riquadri sono bordi sottili neri
    def riquadro(par):
        pr = par.get_or_add_pPr()
        bordi = OxmlElement("w:pBdr")
        for lato in ("top", "left", "bottom", "right"):
            e = OxmlElement(f"w:{lato}")
            for k, v in (("w:val", "single"), ("w:sz", "6"), ("w:space", "4"), ("w:color", "000000")):
                e.set(qn(k), v)
            bordi.append(e)
        pr.append(bordi)

    def bordo_sotto(cella):
        pr = cella.get_or_add_tcPr()
        b = OxmlElement("w:tcBorders")
        e = OxmlElement("w:bottom")
        for k, v in (("w:val", "single"), ("w:sz", "12"), ("w:space", "0"), ("w:color", "000000")):
            e.set(qn(k), v)
        b.append(e)
        pr.append(b)

    for nome in ("Title", "Subtitle", "Heading 1", "Heading 2", "Heading 3"):
        try:
            d.styles[nome].font.color.rgb = RGBColor(0, 0, 0)
        except KeyError:
            pass

    def collegamento(par, testo: str, url: str, dim: float | None = None):
        rid = par.part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
                                 is_external=True)
        h = OxmlElement("w:hyperlink")
        h.set(qn("r:id"), rid)
        r = OxmlElement("w:r")
        rpr = OxmlElement("w:rPr")
        for tag, val in (("w:color", COLORE_LINK), ("w:u", "single")):
            e = OxmlElement(tag)
            e.set(qn("w:val"), val)
            rpr.append(e)
        if dim:                                                  # mezzi punti, come vuole Word
            e = OxmlElement("w:sz")
            e.set(qn("w:val"), str(round(dim * 2)))
            rpr.append(e)
        r.append(rpr)
        t = OxmlElement("w:t")
        t.text = testo
        t.set(qn("xml:space"), "preserve")
        r.append(t)
        h.append(r)
        par._p.append(h)

    def campo(par, istruzione: str):
        """Campo di Word (PAGE, NUMPAGES), un elemento per run: così il formato del run vale anche per il
        risultato (LibreOffice altrimenti lo mostra con il carattere predefinito)."""
        for tipo, testo in (("begin", None), (None, istruzione), ("separate", None), (None, "1"), ("end", None)):
            r = par.add_run()
            if tipo:
                e = OxmlElement("w:fldChar")
                e.set(qn("w:fldCharType"), tipo)
            elif testo == istruzione:
                e = OxmlElement("w:instrText")
                e.set(qn("xml:space"), "preserve")
                e.text = f" {istruzione} "
            else:
                e = OxmlElement("w:t")
                e.text = testo
            r._r.append(e)

    def tabella_docx(intest: list[str], righe: list[list[str]], destra: list[bool], ripeti: bool = True,
                     testata: bool = True):
        t = d.add_table(rows=0, cols=len(intest))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        piccolo = Pt(8 if len(intest) > 6 else 9)

        def riga(valori, grassetto=False):
            celle = t.add_row().cells
            for j, (c, v) in enumerate(zip(celle, valori)):
                p = c.paragraphs[0]
                run = p.add_run(v)
                run.font.size = piccolo
                run.bold = grassetto
                if destra[j]:
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            return celle

        if testata:
            celle = riga(intest, True)
            for c in celle:
                bordo_sotto(c._tc)
            if ripeti:
                trpr = t.rows[0]._tr.get_or_add_trPr()
                e = OxmlElement("w:tblHeader")
                e.set(qn("w:val"), "true")
                trpr.append(e)
        for r in righe:
            riga(r)
        return t

    # intestazione del documento
    d.add_heading(doc.titolo, 0)
    if doc.sottotitolo:
        d.add_paragraph(doc.sottotitolo, style="Subtitle")
    p = d.add_paragraph(data_it(doc.giorno(), estesa=True))
    p.runs[0].font.color.rgb = RGBColor(0, 0, 0)

    for s in doc.sezioni:
        if s.titolo:
            d.add_heading(s.titolo, 1)
        for b in s.blocchi:
            if isinstance(b, Paragrafo):
                d.add_paragraph(b.testo)
            elif isinstance(b, Elenco):
                for v in b.voci:
                    d.add_paragraph(v, style="List Number" if b.numerato else "List Bullet")
            elif isinstance(b, Tabella):
                if b.titolo:
                    d.add_heading(b.titolo, 2)
                num = _colonne_numeriche(b)
                righe = [[testo_cella(r[j] if j < len(r) else None, _dec(b, j)) for j in range(len(b.intestazioni))]
                         for r in b.righe]
                tabella_docx(b.intestazioni, righe, num)
                if b.nota:
                    n = d.add_paragraph(b.nota)
                    n.runs[0].font.size = Pt(8)
                    n.runs[0].italic = True
                else:
                    d.add_paragraph()
            elif isinstance(b, ChiaveValore):
                if b.titolo:
                    d.add_heading(b.titolo, 2)
                righe = [[v.chiave, _valore_voce(v)] for v in b.voci]
                t = tabella_docx(["", ""], righe, [False, False], testata=False)
                for r in t.rows:
                    r.cells[0].paragraphs[0].runs[0].bold = True
                    r.cells[0].width, r.cells[1].width = Cm(7), Cm(10)
                d.add_paragraph()
            elif isinstance(b, Immagine):
                if b.formato == "png":
                    d.add_picture(io.BytesIO(b.byte()), width=Cm(b.larghezza_cm))
                    d.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                else:
                    n = d.add_paragraph("[Grafico vettoriale (SVG): incluso nella versione PDF del report]")
                    n.runs[0].italic = True
                if b.didascalia:
                    n = d.add_paragraph(b.didascalia)
                    n.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    n.runs[0].font.size = Pt(8)
            elif isinstance(b, Avvertenza):
                p = d.add_paragraph()
                r = p.add_run("Attenzione: " if b.livello == "attenzione" else "Nota: ")
                r.bold = True
                p.add_run(b.testo)
                riquadro(p._p)

    if doc.fonti:
        d.add_heading("Fonti e attribuzioni", 1)
        for f in doc.fonti:
            p = d.add_paragraph(style="List Bullet")
            if f.url:
                p.add_run(f.testo + " – ")
                collegamento(p, f.url, f.url)
            else:
                p.add_run(f.testo)

    # avvertenze complete, una volta in fondo al documento
    d.add_heading(TITOLO_AVVERTENZE, 1)
    for testo in AVVERTENZE:
        p = d.add_paragraph()
        r = p.add_run(testo)
        r.font.size = Pt(8.5)

    # intestazione di pagina (pagine verticali): logo, simbolo alto come la E, a sinistra e titolo al centro, sulla
    # stessa riga; sotto, la linea che separa l'intestazione. "Prodotto da EuGEnio" va nel piè di pagina.
    ph = sez.header.paragraphs[0]
    ph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    larghezza = sez.page_width - sez.left_margin - sez.right_margin
    ph.paragraph_format.tab_stops.add_tab_stop(larghezza // 2, WD_TAB_ALIGNMENT.CENTER)
    if LOGO_PNG:
        ph.add_run().add_picture(io.BytesIO(LOGO_PNG), height=Mm(ALTEZZA_E_MM / LOGO_MAIUSCOLA))
    r = ph.add_run("\t" + doc.titolo)
    r.bold, r.font.size, r.font.color.rgb = True, Pt(10), RGBColor(0, 0, 0)
    pr = ph._p.get_or_add_pPr()
    bordi = OxmlElement("w:pBdr")
    e = OxmlElement("w:bottom")
    for k, v in (("w:val", "single"), ("w:sz", "6"), ("w:space", "4"), ("w:color", "000000")):
        e.set(qn(k), v)
    bordi.append(e)
    pr.append(bordi)

    # piè di pagina: avvertenza breve (carattere piccolo) e numero di pagina
    pp = sez.footer.paragraphs[0]
    pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pp.add_run("Prodotto da EuGEnio – ")
    collegamento(pp, "eugenio.statocritico.it", SITO, dim=6.5)
    pp.add_run(". " + PIE_AVVERTENZA)
    pn = sez.footer.add_paragraph()
    pn.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pn.add_run("Pagina ")
    campo(pn, "PAGE")
    pn.add_run(" di ")
    campo(pn, "NUMPAGES")
    for par, dim in ((pp, 6.5), (pn, 7)):
        for r in par.runs:
            r.font.size = Pt(dim)
            r.font.color.rgb = RGBColor(0, 0, 0)
    out = io.BytesIO()
    d.save(out)
    return out.getvalue()


def _valore_voce(v: Voce) -> str:
    t = testo_cella(v.valore, v.decimali)
    return f"{t} {v.unita}" if v.unita and v.valore is not None else t


# ============================================================================================ pdf
_SOSTITUZIONI = {"≥": ">=", "≤": "<=", "–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"', "•": "-",
                 "…": "...", "€": "EUR", " ": " ", " ": " ", "\u0001": ""}


def _font_pdf() -> dict[str, str] | None:
    """Percorsi dei TTF DejaVu (pacchetto Debian fonts-dejavu-core), o None se mancano."""
    cartella = C.REPORT_FONT_DIR
    file = {"": "DejaVuSans.ttf", "B": "DejaVuSans-Bold.ttf", "I": "DejaVuSans-Oblique.ttf",
            "BI": "DejaVuSans-BoldOblique.ttf"}
    trovati = {s: str(cartella / f) for s, f in file.items() if (cartella / f).exists()}
    return trovati if "" in trovati else None


def _pdf(doc: Documento) -> bytes:
    from fpdf import FPDF
    from fpdf.enums import ResourceAccessPolicy
    from fpdf.fonts import FontFace

    font = _font_pdf()
    if font is None:
        log.warning("Font DejaVu non trovati in %s: PDF con Helvetica (simboli sostituiti)", C.REPORT_FONT_DIR)

    def t(s: str) -> str:
        """Con Helvetica (latin-1) i simboli fuori dalla codifica si sostituiscono."""
        if font:
            return s
        for a, b in _SOSTITUZIONI.items():
            s = s.replace(a, b)
        return s.encode("latin-1", "replace").decode("latin-1")

    class PDF(FPDF):
        def header(self):
            # una riga: logo (simbolo alto come la E + scritta) a sinistra, titolo al centro e, solo sulle pagine
            # orizzontali, "Prodotto da EuGEnio" a destra; sotto, la linea che separa l'intestazione
            orizzontale = self.w > self.h
            cima, base = 8.0, 8.0 + ALTEZZA_E_MM            # cima e linea di base delle maiuscole
            x_testo = self.l_margin
            if LOGO_PNG:
                h = ALTEZZA_E_MM / LOGO_MAIUSCOLA
                y = cima - LOGO_CIMA_MAIUSCOLA * h
                info = self.image(io.BytesIO(LOGO_PNG), x=self.l_margin, y=y, h=h)
                x_testo = self.l_margin + float(info.rendered_width) + 6
            destra = self.w - self.r_margin
            if orizzontale:
                self.set_font(famiglia, "", 7.5)
                largh = self.get_string_width("Prodotto da EuGEnio – eugenio.statocritico.it")
                self.set_xy(destra - largh, base - 3.2)
                self.set_text_color(0, 0, 0)
                self.cell(self.get_string_width("Prodotto da EuGEnio – "), 4, t("Prodotto da EuGEnio – "))
                self.set_text_color(*COLORE_LINK_RGB)
                self.cell(self.get_string_width("eugenio.statocritico.it"), 4, "eugenio.statocritico.it", link=SITO)
                destra -= largh + 6
            # titolo centrato sulla pagina, senza invadere logo e testo a destra
            self.set_text_color(0, 0, 0)
            dim = 10.0
            self.set_font(famiglia, grassetto, dim)
            titolo_t = t(doc.titolo)
            spazio = 2 * min(self.w / 2 - x_testo, destra - self.w / 2)
            while self.get_string_width(titolo_t) > spazio and dim > 7:
                dim -= 0.5
                self.set_font(famiglia, grassetto, dim)
            while self.get_string_width(titolo_t) > spazio and len(titolo_t) > 4:
                titolo_t = titolo_t[:-2].rstrip() + "…" if font else titolo_t[:-4].rstrip() + "..."
            larg_t = self.get_string_width(titolo_t)
            self.set_xy(self.w / 2 - larg_t / 2, base - 3.4)
            self.cell(larg_t, 4, titolo_t)
            self.set_draw_color(0, 0, 0)
            self.set_line_width(0.25)
            self.line(self.l_margin, base + 2.6, self.w - self.r_margin, base + 2.6)
            self.set_xy(self.l_margin, self.t_margin)

        def footer(self):
            # sulle pagine verticali "Prodotto da EuGEnio" apre il piè, di seguito all'avvertenza (senza andare a capo)
            testo = PIE_AVVERTENZA if self.w > self.h else f"{INTESTAZIONE}. {PIE_AVVERTENZA}"
            self.set_y(-17)
            self.set_font(famiglia, "", 6)
            self.set_text_color(0, 0, 0)
            self.multi_cell(0, 2.8, t(testo), align="C", new_x="LMARGIN", new_y="NEXT", link=CONTATTI)
            self.cell(0, 3, t(f"Pagina {self.page_no()} di {{nb}}"), align="C")
            self.set_text_color(0, 0, 0)

    # tabelle larghe (più di 8 colonne): pagina orizzontale, per non spezzare le parole a metà
    colonne = max((len(b.intestazioni) for s in doc.sezioni for b in s.blocchi if isinstance(b, Tabella)), default=0)
    pdf = PDF(orientation="L" if colonne > 8 else "P", format="A4")
    pdf.set_margins(18, 21, 18)                 # in alto: sotto la linea dell'intestazione
    pdf.set_auto_page_break(True, margin=21)
    pdf.set_title(doc.titolo)
    pdf.set_author("EuGEnio")
    pdf.set_creator(PIE_DI_PAGINA)
    if font:
        famiglia = "DejaVu"
        for stile, percorso in font.items():
            pdf.add_font("DejaVu", stile, percorso)
        stili = set(font)
    else:
        famiglia, stili = "helvetica", {"", "B", "I", "BI"}
    corsivo = "I" if "I" in stili else ""
    grassetto = "B" if "B" in stili else ""
    pdf.add_page()
    epw = pdf.epw

    def titolo(testo: str, dim: float, spazio_prima: float = 3):
        if pdf.get_y() > pdf.h - 60:          # niente titoli orfani in fondo alla pagina
            pdf.add_page()
        pdf.ln(spazio_prima)
        pdf.set_font(famiglia, grassetto, dim)
        pdf.multi_cell(0, dim * 0.5, t(testo), align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1.5)
        pdf.set_font(famiglia, "", 10)

    def tabella_pdf(intest: list[str] | None, righe: list[list[str]], destra: list[bool], larghezze=None):
        n = len(righe[0]) if righe else len(intest or [])
        dim = 9 if n <= 5 else 8 if n <= 8 else 7 if n <= 12 else 6
        pdf.set_font(famiglia, "", dim)
        if larghezze is None:
            # larghezza in mm: almeno la parola più lunga (le parole non si spezzano), al più 60 mm per i testi
            # lunghi; fpdf2 riporta poi le larghezze alla pagina in proporzione
            larghezze = []
            for j in range(n):
                celle = [t(r[j]) for r in righe[:200]]
                parole = [p for c in celle for p in c.split()]
                w = max([pdf.get_string_width(p) for p in parole] + [3.0])
                w = max(w, min(max([pdf.get_string_width(c) for c in celle] + [0.0]), 60))
                if intest:
                    pdf.set_font(famiglia, grassetto, dim)
                    w = max(w, max(pdf.get_string_width(p) for p in (t(intest[j]).split() or [""])))
                    pdf.set_font(famiglia, "", dim)
                larghezze.append(w + 2.5)
            totale = sum(larghezze)     # tabelle strette: non a tutta pagina
            larghezza = epw if totale > epw * 0.6 else max(totale * 1.4, epw * 0.5)
        else:
            larghezza = epw
        allinea = tuple("RIGHT" if x else "LEFT" for x in destra)
        with pdf.table(col_widths=larghezze, text_align=allinea, line_height=dim * 0.5, align="LEFT",
                       first_row_as_headings=intest is not None, repeat_headings=1, width=larghezza,
                       headings_style=FontFace(emphasis="BOLD" if grassetto else None),
                       padding=1) as tab:
            for r in ([intest] if intest else []) + righe:
                riga = tab.row()
                for c in r:
                    riga.cell(t(c))
        pdf.set_font(famiglia, "", 10)
        pdf.ln(2)

    # intestazione
    pdf.set_font(famiglia, grassetto, 18)
    pdf.multi_cell(0, 9, t(doc.titolo), align="L", new_x="LMARGIN", new_y="NEXT")
    if doc.sottotitolo:
        pdf.set_font(famiglia, "", 12)
        pdf.multi_cell(0, 6, t(doc.sottotitolo), align="L", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(famiglia, "", 9)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, t(data_it(doc.giorno(), estesa=True)), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)
    pdf.set_font(famiglia, "", 10)

    for s in doc.sezioni:
        if s.titolo:
            titolo(s.titolo, 13)
        for b in s.blocchi:
            if isinstance(b, Paragrafo):
                pdf.multi_cell(0, 5, t(b.testo), align="L", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(1.5)
            elif isinstance(b, Elenco):
                for i, v in enumerate(b.voci, 1):
                    segno = f"{i}." if b.numerato else ("•" if font else "-")
                    pdf.set_x(pdf.l_margin + 2)
                    pdf.cell(6, 5, segno)
                    pdf.multi_cell(epw - 8, 5, t(v), align="L", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(1.5)
            elif isinstance(b, Tabella):
                if b.titolo:
                    titolo(b.titolo, 11, 1)
                num = _colonne_numeriche(b)
                righe = [[testo_cella(r[j] if j < len(r) else None, _dec(b, j)) for j in range(len(b.intestazioni))]
                         for r in b.righe]
                tabella_pdf(list(b.intestazioni), righe, num)
                if b.nota:
                    pdf.set_font(famiglia, corsivo, 8)
                    pdf.multi_cell(0, 4, t(b.nota), align="L", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font(famiglia, "", 10)
                    pdf.ln(1)
            elif isinstance(b, ChiaveValore):
                if b.titolo:
                    titolo(b.titolo, 11, 1)
                if b.voci:
                    tabella_pdf(None, [[v.chiave, _valore_voce(v)] for v in b.voci], [False, False], (40, 60))
            elif isinstance(b, Immagine):
                larg = min(b.larghezza_cm * 10, epw)
                pdf.image(io.BytesIO(b.byte()), x=pdf.l_margin + (epw - larg) / 2, w=larg,
                          resource_access_policy=ResourceAccessPolicy(0))
                if b.didascalia:
                    pdf.set_font(famiglia, corsivo, 8)
                    pdf.multi_cell(0, 4, t(b.didascalia), align="C", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font(famiglia, "", 10)
                pdf.ln(2)
            elif isinstance(b, Avvertenza):
                pdf.set_draw_color(0, 0, 0)
                if pdf.get_y() > pdf.h - 40:
                    pdf.add_page()
                pdf.set_font(famiglia, grassetto, 9)
                pdf.multi_cell(0, 5, t("Attenzione" if b.livello == "attenzione" else "Nota"), align="L", border="LTR",
                               padding=(2, 2, 0, 2), new_x="LMARGIN", new_y="NEXT")
                pdf.set_font(famiglia, "", 9)
                pdf.multi_cell(0, 4.6, t(b.testo), align="L", border="LBR", padding=(0, 2, 2, 2),
                               new_x="LMARGIN", new_y="NEXT")
                pdf.set_font(famiglia, "", 10)
                pdf.set_fill_color(255, 255, 255)   # le tabelle riempiono le celle col colore corrente
                pdf.ln(2)

    if doc.fonti:
        titolo("Fonti e attribuzioni", 13)
        pdf.set_font(famiglia, "", 9)
        for f in doc.fonti:
            pdf.set_x(pdf.l_margin + 2)
            pdf.cell(5, 5, "•" if font else "-")
            pdf.set_left_margin(pdf.l_margin + 7)
            pdf.write(5, t(f.testo))
            if f.url:
                pdf.write(5, t(" – "))
                pdf.set_text_color(*COLORE_LINK_RGB)
                pdf.write(5, f.url, link=f.url)
                pdf.set_text_color(0, 0, 0)
            pdf.set_left_margin(pdf.l_margin - 7)
            pdf.ln(6)

    # avvertenze complete, una volta in fondo al documento
    titolo(TITOLO_AVVERTENZE, 11)
    pdf.set_font(famiglia, "", 8)
    for testo in AVVERTENZE:
        pdf.multi_cell(0, 4, t(testo), align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
    return bytes(pdf.output())


# ============================================================================================ xlsx
def _xlsx(doc: Documento) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    info = wb.active
    info.title = "Info"
    wb.properties.title = doc.titolo
    wb.properties.creator = "EuGEnio"
    grass = Font(bold=True)
    from openpyxl.styles import Border, Side
    sotto = Border(bottom=Side(style="medium", color="000000"))     # niente fondi colorati: solo bordi neri
    riquadro = Border(*(Side(style="thin", color="000000"),) * 4)
    nomi_usati = {"info"}

    def nome_foglio(t: str | None, n: int) -> str:
        base = re.sub(r"[\[\]:*?/\\']", " ", t or f"Tabella {n}").strip()[:28] or f"Tabella {n}"
        nome, k = base, 2
        while nome.lower() in nomi_usati:
            nome = f"{base[:25]} ({k})"
            k += 1
        nomi_usati.add(nome.lower())
        return nome

    def scrivi(ws, r: int, c: int, v, decimali: int | None = None):
        cella = ws.cell(row=r, column=c)
        if isinstance(v, bool):
            cella.value = "sì" if v else "no"
        elif isinstance(v, (int, float)):
            if isinstance(v, float) and not math.isfinite(v):
                cella.value = None
            else:
                cella.value = v
                d = decimali if decimali is not None else (0 if isinstance(v, int) else 2)
                cella.number_format = "#,##0" if d == 0 else "#,##0." + "0" * d
        elif isinstance(v, str):
            d = come_data(v)
            if d is not None:
                cella.value = d
                cella.number_format = "dd/mm/yyyy hh:mm" if isinstance(d, dt.datetime) else "dd/mm/yyyy"
            else:
                cella.value = v
                if v.startswith("="):       # mai formule dai dati dell'utente
                    cella.data_type = "s"
        return cella

    r = 1
    if LOGO_PNG:
        try:
            from openpyxl.drawing.image import Image as XImg     # richiede Pillow
            img = XImg(io.BytesIO(LOGO_PNG))
            alto = round(LOGO_ALTEZZA_CM / 2.54 * 96)            # pixel a 96 punti per pollice
            img.height, img.width = alto, round(alto * img.width / img.height)
            info.add_image(img, "A1")
            info.row_dimensions[1].height = alto * 0.75 + 4      # punti
            r += 1
        except Exception:                      # senza Pillow il logo si omette
            log.info("Logo non inserito nel foglio Excel (manca Pillow?)")
    c = info.cell(row=r, column=1, value=INTESTAZIONE)
    c.hyperlink = SITO
    c.font = Font(italic=True, color=COLORE_LINK, size=9)
    r += 1
    info.cell(row=r, column=1, value=doc.titolo).font = Font(bold=True, size=14)
    r += 1
    if doc.sottotitolo:
        info.cell(row=r, column=1, value=doc.sottotitolo).font = Font(size=12)
        r += 1
    info.cell(row=r, column=1, value="Data").font = grass
    c = info.cell(row=r, column=2, value=doc.giorno())
    c.number_format = "dd/mm/yyyy"
    c.alignment = Alignment(horizontal="left")
    r += 2

    n_tab = 0
    for s in doc.sezioni:
        if s.titolo:
            info.cell(row=r, column=1, value=s.titolo).font = Font(bold=True, size=12)
            r += 1
        for b in s.blocchi:
            if isinstance(b, Paragrafo):
                info.cell(row=r, column=1, value=b.testo).alignment = Alignment(wrap_text=True, vertical="top")
                info.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
                r += 1
            elif isinstance(b, Elenco):
                for i, v in enumerate(b.voci, 1):
                    info.cell(row=r, column=1, value=f"{i}. {v}" if b.numerato else f"• {v}")
                    r += 1
            elif isinstance(b, ChiaveValore):
                if b.titolo:
                    info.cell(row=r, column=1, value=b.titolo).font = Font(bold=True, italic=True)
                    r += 1
                for v in b.voci:
                    info.cell(row=r, column=1, value=v.chiave).font = grass
                    scrivi(info, r, 2, v.valore, v.decimali).alignment = Alignment(horizontal="left")
                    if v.unita:
                        info.cell(row=r, column=3, value=v.unita)
                    r += 1
            elif isinstance(b, Avvertenza):
                c = info.cell(row=r, column=1, value=("Attenzione: " if b.livello == "attenzione" else "Nota: ") + b.testo)
                c.alignment = Alignment(wrap_text=True, vertical="top")
                c.border = riquadro
                info.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
                info.row_dimensions[r].height = 15 * max(1, math.ceil(len(c.value) / 95))
                r += 1
            elif isinstance(b, Immagine):
                testo = "[Immagine non inclusa nel foglio di calcolo"
                info.cell(row=r, column=1, value=f"{testo}{': ' + b.didascalia if b.didascalia else ''}]")
                r += 1
            elif isinstance(b, Tabella):
                n_tab += 1
                nome = nome_foglio(b.titolo, n_tab)
                ws = wb.create_sheet(nome)
                for j, h in enumerate(b.intestazioni, 1):
                    c = ws.cell(row=1, column=j, value=h)
                    c.font, c.border = grass, sotto
                    c.alignment = Alignment(wrap_text=True, vertical="top")
                larg = [len(h) for h in b.intestazioni]
                for i, riga in enumerate(b.righe, 2):
                    for j, v in enumerate(riga):
                        scrivi(ws, i, j + 1, v, _dec(b, j))
                        if i < 300:
                            larg[j] = max(larg[j], len(testo_cella(v, _dec(b, j))))
                for j, w in enumerate(larg, 1):
                    ws.column_dimensions[get_column_letter(j)].width = min(max(w + 2, 8), 50)
                ws.freeze_panes = "A2"
                if b.righe:
                    ws.auto_filter.ref = f"A1:{get_column_letter(len(b.intestazioni))}{len(b.righe) + 1}"
                c = info.cell(row=r, column=1, value=f"Tabella «{b.titolo or nome}»: foglio «{nome}»")
                c.hyperlink = f"#'{nome}'!A1"
                c.font = Font(color=COLORE_LINK, underline="single")
                r += 1
                if b.nota:
                    info.cell(row=r, column=1, value=b.nota).font = Font(italic=True, size=9)
                    r += 1
        r += 1

    if doc.fonti:
        info.cell(row=r, column=1, value="Fonti e attribuzioni").font = Font(bold=True, size=12)
        r += 1
        for f in doc.fonti:
            info.cell(row=r, column=1, value=f.testo)
            if f.url:
                c = info.cell(row=r, column=2, value=f.url)
                c.hyperlink = f.url
                c.font = Font(color=COLORE_LINK, underline="single")
            r += 1
        r += 1
    info.cell(row=r, column=1, value=TITOLO_AVVERTENZE).font = Font(bold=True, size=12)
    r += 1
    for testo in AVVERTENZE:
        c = info.cell(row=r, column=1, value=testo)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        c.font = Font(size=9, color="000000")
        info.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
        info.row_dimensions[r].height = 12.5 * max(1, math.ceil(len(testo) / 150))
        r += 1
    c = info.cell(row=r, column=1, value=CONTATTI)
    c.hyperlink = CONTATTI
    c.font = Font(color=COLORE_LINK, underline="single", size=9)
    info.column_dimensions["A"].width = 60
    info.column_dimensions["B"].width = 28
    info.column_dimensions["C"].width = 14
    info.column_dimensions["D"].width = 14
    info.sheet_properties.pageSetUpPr.fitToPage = True      # in stampa il foglio Info sta nella larghezza
    info.page_setup.fitToWidth, info.page_setup.fitToHeight = 1, 0
    for ws in wb.worksheets:                   # intestazione e piè di pagina di stampa di ogni foglio
        ws.oddHeader.left.text = "EuGEnio"
        ws.oddHeader.left.size = 9
        ws.oddHeader.center.text = doc.titolo[:120]
        ws.oddHeader.center.size = 9
        ws.oddFooter.left.text = PIE_AVVERTENZA_XLSX
        ws.oddFooter.left.size = 6
        ws.oddFooter.right.text = "Pagina &P di &N"
        ws.oddFooter.right.size = 7
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


# ============================================================================================ ingresso
RENDERER = {"docx": _docx, "pdf": _pdf, "xlsx": _xlsx}


def genera(doc: Documento, formato: str) -> bytes:
    """Byte del file nel formato richiesto ('docx', 'pdf', 'xlsx'). Nulla viene scritto su disco."""
    if formato not in RENDERER:
        raise ValueError(f"formato non supportato: {formato} (ammessi: {', '.join(RENDERER)})")
    return RENDERER[formato](doc)
