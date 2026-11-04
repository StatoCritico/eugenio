"""Visure sintetiche in PDF per i test e le prove (dati inventati).

Imitano la struttura delle visure catastali (formato «attuale» a campi con etichetta e formato «a tabella», per
immobile e per soggetto, fabbricati e terreni), con persone, codici fiscali, fogli e particelle **inventati**. Ogni
pagina porta la scritta «ESEMPIO SINTETICO – non è un documento dell'Agenzia delle Entrate». Servono finché non
arrivano le visure vere anonimizzate; le regole di regole.toml si provano su questi file.

Richiede reportlab (solo per sviluppo e test: requirements-dev.txt).

  python -m visure esempi --uscita cartella
"""
from __future__ import annotations

from pathlib import Path

AVVISO = "ESEMPIO SINTETICO - non è un documento dell'Agenzia delle Entrate: dati inventati"

# risultati attesi (usati dai test): file → elenco di unità con i campi principali
ATTESI: dict[str, list[dict]] = {
    "visura_immobile_B2_attuale.pdf": [
        {"catasto": "F", "comune": "RAVENNA", "codice_comune": "H199", "foglio": "120", "particella": "1450",
         "subalterno": "2", "categoria": "B/2", "classe": "2", "consistenza": 42300, "unita_consistenza": "m³",
         "superficie_catastale": 9870, "rendita_euro": 98450, "piani": "S1;T;1;2;3;4", "piani_fuori_terra": 5,
         "piani_interrati": 1, "piano_piu_alto": "4", "indirizzo": "VIALE DELL'ESEMPIO n. 5"},
    ],
    "visura_immobile_A2_attuale.pdf": [
        {"catasto": "F", "comune": "RIMINI", "codice_comune": "H294", "foglio": "77", "particella": "210",
         "subalterno": "9", "categoria": "A/2", "classe": "3", "consistenza": 5.5, "unita_consistenza": "vani",
         "superficie_catastale": 98, "superficie_escluse_aree_scoperte": 95, "rendita_euro": 568.1, "piani": "2",
         "piani_fuori_terra": 3, "piano_piu_alto": "2", "indirizzo": "VIA DI PROVA n. 10"},
    ],
    "visura_soggetto_tabella.pdf": [
        {"catasto": "F", "comune": "FORLI'", "codice_comune": "D704", "foglio": "50", "particella": "300", "subalterno": "1",
         "categoria": "A/10", "classe": "2", "consistenza": 6.5, "superficie_catastale": 140, "rendita_euro": 1880,
         "piani": "T;1"},
        {"catasto": "F", "comune": "FORLI'", "codice_comune": "D704", "foglio": "50", "particella": "300", "subalterno": "2",
         "categoria": "A/10", "classe": "2", "consistenza": 9, "superficie_catastale": 205, "rendita_euro": 2603.08,
         "piani": "2;3"},
        {"catasto": "F", "comune": "FORLI'", "codice_comune": "D704", "foglio": "50", "particella": "300", "subalterno": "4",
         "categoria": "C/6", "classe": "3", "consistenza": 18, "unita_consistenza": "m²", "superficie_catastale": 20,
         "rendita_euro": 70, "piani": "S1"},
        {"catasto": "F", "comune": "FORLI'", "codice_comune": "D704", "foglio": "51", "particella": "12", "subalterno": None,
         "categoria": "D/4", "rendita_euro": 154000, "piani": "S1;T;1;2;3;4;5;6"},
        {"catasto": "F", "comune": "CESENA", "codice_comune": "C573", "foglio": "90", "particella": "455", "subalterno": "1",
         "categoria": "B/5", "classe": "1", "consistenza": 12500, "unita_consistenza": "m³", "superficie_catastale": 3180,
         "rendita_euro": 16137.5, "piani": "T;1;2"},
        {"catasto": "T", "comune": "CESENA", "codice_comune": "C573", "foglio": "90", "particella": "456",
         "qualita": "SEMINATIVO", "classe": "2", "superficie_m2": 12345, "reddito_dominicale_euro": 45.2,
         "reddito_agrario_euro": 38.1},
    ],
    "visura_terreni_attuale.pdf": [
        {"catasto": "T", "comune": "RAVENNA", "codice_comune": "H199", "foglio": "200", "particella": "12",
         "qualita": "SEMINATIVO IRRIGUO", "classe": "1", "superficie_m2": 8520, "reddito_dominicale_euro": 98.7,
         "reddito_agrario_euro": 61.4},
    ],
}
# nessuna unità: documenti che il lettore deve scartare con il motivo giusto
ESITI_ATTESI = {"documento_non_visura.pdf": "non_riconosciuta", "visura_scansione.pdf": "senza_testo"}
# dati personali inventati presenti nei PDF (i test controllano che non escano mai nei CSV)
PERSONALI = ["SMPPRS80A01H199Z", "PRVLCU75B41H294K", "TSTGNN62C12D704W", "00000000000", "ESEMPIO PERSONA",
             "PROVA LUCIA", "TEST GIOVANNI", "ENTE SANITARIO DI ESEMPIO"]


def _canvas(percorso: Path, orizzontale: bool = False):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(percorso), pagesize=landscape(A4) if orizzontale else A4)
    c.setTitle("Visura sintetica di esempio")
    c.setAuthor("EuGEnio Visure - test")
    return c


def _testata(c, pagina: int, tipo: str, alto: float, n_visura: str = "T000001"):
    c.setFont("Helvetica-Bold", 8)
    c.drawString(40, alto, AVVISO)
    c.setFont("Helvetica", 8)
    c.drawString(40, alto - 14, "Direzione Provinciale di ESEMPIO - Ufficio Provinciale - Territorio - Servizi Catastali")
    c.drawString(40, alto - 26, f"{tipo}")
    c.drawRightString(c._pagesize[0] - 40, alto - 26, "Data: 04/11/2026 - Ora: 10:15:32")
    c.drawRightString(c._pagesize[0] - 40, alto - 38, f"Visura n.: {n_visura} Pag: {pagina}")


def _righe(c, x, y, righe, passo=12, font=("Helvetica", 8)):
    c.setFont(*font)
    for r in righe:
        c.drawString(x, y, r)
        y -= passo
    return y


def visura_b2(cartella: Path) -> Path:
    p = cartella / "visura_immobile_B2_attuale.pdf"
    c = _canvas(p)
    _testata(c, 1, "Visura attuale per immobile", 800)
    y = _righe(c, 40, 740, [
        "Situazione degli atti informatizzati al 04/11/2026",
        "Dati della richiesta  Comune di RAVENNA (Codice: H199)",
        "                      Catasto Fabbricati  Foglio: 120 Particella: 1450 Sub.: 2",
        "",
        "Immobile n. 1",
        "Catasto Fabbricati",
        "Dati identificativi: Comune di RAVENNA (H199) (RA)",
        "Sezione urbana - Foglio 120 Particella 1450 Subalterno 2",
        "Classamento:",
        "Rendita: Euro 98.450,00",
        "Zona censuaria 1, Categoria B/2 a), Classe 2, Consistenza 42.300 m³",
        "Indirizzo: VIALE DELL'ESEMPIO n. 5 Piano S1-T-1-2-3-4",
        "Dati di superficie: Totale: 9.870 m²",
        "Ultimo atto di aggiornamento: VARIAZIONE del 01/02/2019 Pratica n. RA0000001 in atti dal 01/02/2019",
    ])
    c.drawString(c._pagesize[0] - 80, 60, "Segue")
    c.showPage()
    _testata(c, 2, "Visura attuale per immobile", 800)
    _righe(c, 40, 740, [
        "Intestazione attuale dell'immobile n. 1 - totale righe intestati: 1",
        "> 1. ENTE SANITARIO DI ESEMPIO (CF 00000000000) sede in RAVENNA (RA)",
        "     Diritto di: Proprieta' per 1/1 (deriva dall'atto 1)",
        "1. Atto del 01/01/2000 Pubblico ufficiale NOTAIO DI ESEMPIO Sede RAVENNA (RA) Repertorio n. 1",
        "",
        "a) B/2: Case di cura ed ospedali (senza fine di lucro)",
        "Visura telematica esente per fini istituzionali",
        "Rilasciata da: Servizio Telematico",
    ])
    c.save()
    return p


def visura_a2(cartella: Path) -> Path:
    p = cartella / "visura_immobile_A2_attuale.pdf"
    c = _canvas(p)
    _testata(c, 1, "Visura attuale per immobile", 800, "T000002")
    _righe(c, 40, 740, [
        "Situazione degli atti informatizzati al 04/11/2026",
        "Dati della richiesta  Comune di RIMINI ( Codice: H294)",
        "Catasto Fabbricati   Foglio: 77 Particella: 210 Sub.: 9",
        "",
        "INTESTATI",
        "1  PROVA LUCIA nata a RIMINI (RN) il 01/02/1975  PRVLCU75B41H294K*  (1) Proprieta' per 1/2",
        "2  TEST GIOVANNI nato a FORLI' (FC) il 12/03/1962  TSTGNN62C12D704W*  (1) Proprieta' per 1/2",
        "",
        "Unità immobiliare n. 1",
        "Dati identificativi: Comune di RIMINI (H294) (RN)",
        "Foglio 77 Particella 210 Subalterno 9",
        "Classamento: Rendita: Euro 568,10",
        "Zona censuaria 1, Categoria A/2, Classe 3, Consistenza 5,5 vani",
        "Indirizzo: VIA DI PROVA n. 10 Piano 2",
        "Dati di superficie: Totale: 98 m² Totale escluse aree scoperte b): 95 m²",
        "Notifica  Partita  Mod.58",
    ])
    c.save()
    return p


def visura_soggetto(cartella: Path) -> Path:
    p = cartella / "visura_soggetto_tabella.pdf"
    c = _canvas(p, orizzontale=True)
    W = c._pagesize[0]
    X = [40, 62, 100, 135, 180, 210, 240, 268, 315, 350, 410, 490, 560]
    T = ["N.", "Sezione", "Foglio", "Particella", "Sub", "Zona", "Micro", "Categoria", "Classe", "Consistenza",
         "Superficie", "Rendita", "Indirizzo"]

    def titoli(y):
        c.setFont("Helvetica-Bold", 7)
        c.drawString(40, y + 12, "N.   DATI IDENTIFICATIVI")
        c.drawString(268, y + 12, "DATI DI CLASSAMENTO")
        c.drawString(560, y + 12, "ALTRE INFORMAZIONI")
        for x, t in zip(X, T):
            c.drawString(x, y, t)
        c.setFont("Helvetica", 6)
        c.drawString(62, y - 8, "Urbana")
        c.drawString(210, y - 8, "Cens.")
        c.drawString(240, y - 8, "Zona")
        c.drawString(410, y - 8, "Catastale")
        return y - 22

    def riga(y, valori, extra=()):
        c.setFont("Helvetica", 7)
        for x, v in zip(X, valori):
            if v:
                c.drawString(x, y, v)
        for i, e in enumerate(extra):
            c.drawString(e[0], y - 9 * (i + 1), e[1])
        return y - 12 - 9 * len(extra)

    _testata(c, 1, "Visura per soggetto", 560, "T000003")
    y = _righe(c, 40, 505, [
        "Situazione degli atti informatizzati al 04/11/2026",
        "Dati della richiesta   Soggetto: ESEMPIO PERSONA (CF SMPPRS80A01H199Z)",
        "                       Terreni e Fabbricati siti in tutta la provincia",
        "Soggetto individuato   ESEMPIO PERSONA nato a RAVENNA (RA) il 01/01/1980  SMPPRS80A01H199Z",
        "",
        "1. Unità immobiliari site nel Comune di FORLI'(Codice D704) - Catasto dei Fabbricati",
    ], passo=11)
    y = titoli(y - 18)
    y = riga(y, ["1", "", "50", "300", "1", "1", "", "A/10", "2", "6,5 vani", "Totale: 140 m²", "Euro 1.880,00",
                 "VIA DEI TEST n. 3 piano: T-1;"])
    y = riga(y, ["2", "", "50", "300", "2", "1", "", "A/10", "2", "9 vani", "Totale: 205 m²", "Euro 2.603,08",
                 "VIA DEI TEST n. 3 piano: 2-3;"])
    y = riga(y, ["3", "", "50", "300", "4", "1", "", "C/6", "3", "18 m²", "Totale: 20 m²", "Euro 70,00",
                 "VIA DEI TEST n. 3 piano: S1;"], extra=[(410, "Totale escluse aree scoperte: 20 m²")])
    y = riga(y, ["4", "", "51", "12", "", "", "", "D/4", "", "", "", "Euro 154.000,00",
                 "VIALE DELLE PROVE n. 1 piano: S1-T-1-2-3-4-5-6;"])
    _righe(c, 40, y - 4, ["Totale: vani 15,5  m² 18  Rendita: Euro 158.553,08",
                          "Intestazione degli immobili indicati al n. 1",
                          "1  ESEMPIO PERSONA nato a RAVENNA (RA) il 01/01/1980  SMPPRS80A01H199Z*  (1) Proprieta' per 1/1"])
    c.drawString(W - 80, 40, "Segue")
    c.showPage()

    _testata(c, 2, "Visura per soggetto", 560, "T000003")
    y = _righe(c, 40, 505, ["2. Unità immobiliari site nel Comune di CESENA(Codice C573) - Catasto dei Fabbricati"])
    y = titoli(y - 18)
    y = riga(y, ["1", "", "90", "455", "1", "2", "", "B/5", "1", "12.500 m³", "Totale: 3.180 m²", "Euro 16.137,50",
                 "VIA DELLA SCUOLA DI PROVA n. 8 piano: T-1-2;"])
    y = _righe(c, 40, y - 4, ["Immobile 1: Annotazione: classamento proposto e validato (D.M. 701/94)",
                              "Intestazione degli immobili indicati al n. 2",
                              "1  ESEMPIO PERSONA nato a RAVENNA (RA) il 01/01/1980  SMPPRS80A01H199Z*  (1) Proprieta' per 1/1",
                              "",
                              "3. Immobili siti nel Comune di CESENA(Codice C573) - Catasto dei Terreni"], passo=11)
    XT = [40, 70, 100, 140, 170, 200, 290, 330, 400, 460, 540]
    TT = ["N.", "Foglio", "Particella", "Sub", "Porz", "Qualità", "Classe", "ha are ca", "Deduz", "Dominicale", "Agrario"]
    y -= 18
    c.setFont("Helvetica-Bold", 7)
    for x, t in zip(XT, TT):
        c.drawString(x, y, t)
    y -= 14
    c.setFont("Helvetica", 7)
    for x, v in zip(XT, ["1", "90", "456", "", "", "SEMINATIVO", "2", "1 23 45", "", "Euro 45,20", "Euro 38,10"]):
        if v:
            c.drawString(x, y, v)
    _righe(c, 40, y - 16, ["Intestazione degli immobili indicati al n. 3",
                           "1  ESEMPIO PERSONA nato a RAVENNA (RA) il 01/01/1980  SMPPRS80A01H199Z*  (1) Proprieta' per 1/1",
                           "Rilasciata da: Servizio Telematico"])
    c.save()
    return p


def visura_terreni(cartella: Path) -> Path:
    p = cartella / "visura_terreni_attuale.pdf"
    c = _canvas(p)
    _testata(c, 1, "Visura attuale per immobile", 800, "T000004")
    _righe(c, 40, 740, [
        "Situazione degli atti informatizzati al 04/11/2026",
        "Dati della richiesta  Comune di RAVENNA (Codice: H199)",
        "Catasto Terreni  Foglio: 200 Particella: 12",
        "",
        "Immobile n. 1",
        "Catasto Terreni",
        "Dati identificativi: Comune di RAVENNA (H199) (RA)",
        "Foglio 200 Particella 12",
        "Classamento:",
        "Redditi: dominicale Euro 98,70 agrario Euro 61,40",
        "Particella con qualità: SEMINATIVO IRRIGUO di classe 1",
        "Superficie: 8.520 m²",
        "",
        "Intestazione attuale dell'immobile n. 1 - totale righe intestati: 1",
        "> 1. ESEMPIO PERSONA (CF SMPPRS80A01H199Z) nato a RAVENNA (RA) il 01/01/1980",
        "     Diritto di: Proprieta' per 1/1",
    ])
    c.save()
    return p


def non_visura(cartella: Path) -> Path:
    p = cartella / "documento_non_visura.pdf"
    c = _canvas(p)
    _righe(c, 40, 780, ["Verbale della riunione di condominio", "Ordine del giorno: manutenzione del tetto",
                        "Presenti: tutti i condomini"])
    c.save()
    return p


def scansione(cartella: Path) -> Path:
    p = cartella / "visura_scansione.pdf"
    c = _canvas(p)
    c.rect(40, 400, 500, 300)     # come una scansione: nessun testo
    c.save()
    return p


def genera(cartella: str | Path) -> list[Path]:
    d = Path(cartella)
    d.mkdir(parents=True, exist_ok=True)
    return [f(d) for f in (visura_b2, visura_a2, visura_soggetto, visura_terreni, non_visura, scansione)]


# patrimonio d'esempio che si abbina alle visure sintetiche (stesse particelle; una riga senza visura)
PATRIMONIO_ESEMPIO = """id;denominazione;comune;foglio;particella
E1;Ospedale di esempio;Ravenna;120;1450
E2;Appartamento di prova;Rimini;77;210
E3;Uffici di prova;Forlì;50;300
E4;Clinica di prova;Forlì;51;12
E5;Scuola di prova;Cesena;90;455
E6;Magazzino senza visura;Cesena;90;999
"""
