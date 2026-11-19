# -*- coding: utf-8 -*-
"""
Costruzione della cartella di lavoro psicro_UTA.xlsx (diagramma psicrometrico e
progetto delle trasformazioni di una UTA).  Rieseguibile: python3 build_psicro.py [uscita.xlsx]

Tutte le grandezze sono calcolate con FORMULE (nessun valore precalcolato), senza
macro, LET/LAMBDA o matrici dinamiche: funziona in Excel 2010+, LibreOffice, Google Sheets.
Le iterazioni (T di rugiada, bulbo umido, ADP, saturazione adiabatica) sono
"srotolate" in colonne di appoggio del foglio Calcoli (Newton, 3-6 passi).
"""
import os
import sys
from openpyxl import Workbook
from openpyxl.utils import get_column_letter as L
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.comments import Comment
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule
from openpyxl.chart import ScatterChart, Reference, Series
from openpyxl.chart.series import SeriesLabel, StrRef
from openpyxl.chart.marker import Marker
from openpyxl.chart.label import DataLabelList, DataLabel
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.chart.axis import ChartLines
from openpyxl.chart.text import RichText
from openpyxl.drawing.line import LineProperties
from openpyxl.drawing.text import Paragraph, ParagraphProperties, CharacterProperties, Font as DFont

QUI = os.path.dirname(os.path.abspath(__file__))
# (14/11/2026) percorsi relativi: di predefinito il file scaricabile del sito; un altro percorso come primo argomento
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(QUI, "..", "..", "fase5-sito", "sito", "strumenti", "psicro_UTA.xlsx")
VERSIONE = "2.3"
DATA = "16/11/2026"
UTA_SCALE = 55   # scala di stampa del foglio UTA (A4 orizzontale, 2 pagine)

# ----------------------------------------------------------------------------- stili
ARIAL = "Arial"
F_IN = Font(name=ARIAL, size=10, color="0000FF", bold=True)
F_N = Font(name=ARIAL, size=10)
F_B = Font(name=ARIAL, size=10, bold=True)
F_SM = Font(name=ARIAL, size=9, color="404040")
F_H = Font(name=ARIAL, size=11, bold=True, color="FFFFFF")
F_T = Font(name=ARIAL, size=16, bold=True, color="1F3864")
F_WARN = Font(name=ARIAL, size=9, color="9C0006")
FILL_IN = PatternFill("solid", fgColor="FFF2CC")
FILL_CALC = PatternFill("solid", fgColor="F2F2F2")
FILL_GEN = PatternFill("solid", fgColor="3A5A80")
FILL_EST = PatternFill("solid", fgColor="8FC9EE")   # ESTATE = azzurro
FILL_INV = PatternFill("solid", fgColor="C00000")   # INVERNO = rosso
F_H_DARK = Font(name="Arial", size=11, bold=True, color="0B2545")
FILL_SUB = PatternFill("solid", fgColor="D9E1F2")
FILL_SUB_E = PatternFill("solid", fgColor="DCEEFA")
FILL_SUB_I = PatternFill("solid", fgColor="F8D7D7")
FILL_GREY = PatternFill("solid", fgColor="D9D9D9")
thin = Side(style="thin", color="A6A6A6")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)

# ------------------------------------------------------------ formule psicrometriche
P = "Calcoli!$D$4"     # pressione di calcolo [Pa] (riferimento da altri fogli)
PL = "$D$4"            # idem, dentro il foglio Calcoli
PK = "$D$5"            # pressione in kPa (dentro Calcoli)


def PS(t):
    """Pressione di saturazione ASHRAE Hyland-Wexler [Pa]; ghiaccio per t <= 0,01 °C."""
    T = f"({t}+273.15)"
    ice = (f"EXP(-5674.5359/{T}+6.3925247-0.009677843*{T}+0.00000062215701*{T}^2"
           f"+0.0000000020747825*{T}^3-9.484024E-13*{T}^4+4.1635019*LN({T}))")
    wat = (f"EXP(-5800.2206/{T}+1.3914993-0.048640239*{T}+0.000041764768*{T}^2"
           f"-0.000000014452093*{T}^3+6.5459673*LN({T}))")
    return f"IF({t}<=0.01,{ice},{wat})"


def LNPS(t):
    T = f"({t}+273.15)"
    ice = (f"(-5674.5359/{T}+6.3925247-0.009677843*{T}+0.00000062215701*{T}^2"
           f"+0.0000000020747825*{T}^3-9.484024E-13*{T}^4+4.1635019*LN({T}))")
    wat = (f"(-5800.2206/{T}+1.3914993-0.048640239*{T}+0.000041764768*{T}^2"
           f"-0.000000014452093*{T}^3+6.5459673*LN({T}))")
    return f"IF({t}<=0.01,{ice},{wat})"


def DLNPS(t):
    T = f"({t}+273.15)"
    ice = (f"(5674.5359/{T}^2-0.009677843+2*0.00000062215701*{T}+3*0.0000000020747825*{T}^2"
           f"-4*9.484024E-13*{T}^3+4.1635019/{T})")
    wat = (f"(5800.2206/{T}^2-0.048640239+2*0.000041764768*{T}-3*0.000000014452093*{T}^2"
           f"+6.5459673/{T})")
    return f"IF({t}<=0.01,{ice},{wat})"


def MAGNUS0(pw):
    """Stima iniziale della T di rugiada (Magnus su acqua/ghiaccio) per il metodo di Newton."""
    g = f"LN({pw}/611.2)"
    return f"IF({pw}>=611.2,243.12*{g}/(17.62-{g}),272.62*{g}/(22.46-{g}))"


def NEWTON_TD(T, pw):
    return f"{T}-(({LNPS(T)})-LN({pw}))/({DLNPS(T)})"


def WWB(t, tw, ps, p):
    """Umidità specifica dall'equazione del bulbo umido ASHRAE (ps = psat(tw) già calcolata)."""
    ws = f"(0.621945*{ps}/({p}-{ps}))"
    return (f"IF({tw}>=0,((2501-2.326*{tw})*{ws}-1.006*({t}-{tw}))/(2501+1.86*{t}-4.186*{tw}),"
            f"((2830-0.24*{tw})*{ws}-1.006*({t}-{tw}))/(2830+1.86*{t}-2.1*{tw}))")


# ----------------------------------------------------------------------- tabelle
TIPI = [
    ("Nessuna", "—", "—", "—",
     "Riga inattiva: lo stato dell'aria passa invariato alla riga successiva."),
    ("Miscela con ricircolo",
     "frazione di ricircolo in massa [0–1] oppure AUTO (= 1 − quota aria esterna)", "—", "—",
     "Miscela adiabatica dell'aria in arrivo con aria di ricircolo alle condizioni AMBIENTE (bilancio di massa e di entalpia)."),
    ("Recuperatore di calore",
     "efficienza sensibile εs [0–1] (tip. 0,5–0,75)",
     "efficienza latente εl [0–1] (vuoto/0 = solo sensibile; entalpico 0,5–0,7)", "—",
     "Recupero tra aria esterna e aria di ripresa (= ambiente), portate bilanciate: T = Tin + εs·(Tamb − Tin); x = xin + εl·(xamb − xin)."),
    ("Riscaldamento sensibile",
     "T uscita [°C]", "in alternativa (P1 vuoto): potenza ceduta all'aria [kW]", "—",
     "Batteria calda: x costante, T aumenta."),
    ("Raffreddamento sensibile",
     "T uscita [°C]", "in alternativa (P1 vuoto): potenza frigorifera [kW, positiva]", "—",
     "Batteria fredda secca: x costante. Avviso se T uscita < T di rugiada (si avrebbe condensa)."),
    ("Raffreddamento con deumidificazione",
     "x uscita [g/kg] oppure AUTO (= x del punto di immissione)",
     "fattore di bypass BF [-] (vuoto = 0,10; tip. 0,05–0,20)",
     "T ADP/superficie batteria [°C] (se compilato prevale su P1)",
     "Batteria fredda con condensa: retta ingresso → ADP (punto di rugiada dell'apparato, sulla saturazione); uscita = ADP + BF·(ingresso − ADP)."),
    ("Umidificazione adiabatica",
     "x uscita [g/kg] oppure AUTO (= x immissione)",
     "se P1 vuoto: UR uscita [%]",
     "se P1 e P2 vuoti: efficienza di saturazione [0–1]",
     "Umidificatore a pacco/ugelli: trasformazione a ENTALPIA COSTANTE, la T diminuisce. Limitata alla saturazione."),
    ("Umidificazione a vapore",
     "x uscita [g/kg] oppure AUTO (= x immissione)",
     "se P1 vuoto: UR uscita [%]",
     "entalpia del vapore [kJ/kg] (vuoto = 2676, vapore saturo ~100 °C)",
     "Iniezione di vapore: Δh = Δx·h_vapore, trasformazione quasi isoterma (lieve aumento di T)."),
    ("Preriscaldamento",
     "T uscita [°C] oppure AUTO (= fino all'isoentalpica che porta a x immissione con UR = P3)",
     "potenza [kW] se P1 vuoto",
     "UR uscita umidificatore per AUTO [%] (vuoto = 90)",
     "Batteria di preriscaldamento a monte dell'umidificatore adiabatico: x costante."),
    ("Post-riscaldamento",
     "T uscita [°C] oppure AUTO (= T immissione − ΔT dei ventilatori a valle)",
     "potenza [kW] se P1 vuoto", "—",
     "Batteria di post-riscaldamento: porta l'aria alla temperatura di immissione, x costante."),
    ("Ventilatore",
     "ΔT di riscaldamento dell'aria [K] (tip. 0,5–1)",
     "in alternativa (P1 vuoto): potenza termica ceduta all'aria [kW]", "—",
     "Riscaldamento dovuto al motore/ventilatore: x costante."),
]
NT = len(TIPI)
SHORT = [
    "Riga inattiva: lo stato passa invariato.",
    "P1 = frazione di ricircolo [0–1] o AUTO (= 1 − quota aria esterna)",
    "P1 = εs sensibile [0–1] | P2 = εl latente [0–1] (vuoto = solo sensibile)",
    "P1 = T uscita [°C] | oppure P2 = potenza [kW]",
    "P1 = T uscita [°C] | oppure P2 = potenza frigorifera [kW]",
    "P1 = x uscita [g/kg] o AUTO (= x imm.) | P2 = BF (vuoto = 0,10) | P3 = T ADP [°C] (prevale su P1)",
    "h costante. P1 = x uscita [g/kg] o AUTO | oppure P2 = UR uscita [%] | oppure P3 = efficienza [0–1]",
    "P1 = x uscita [g/kg] o AUTO | oppure P2 = UR uscita [%] | P3 = h vapore [kJ/kg] (vuoto = 2676)",
    "P1 = T uscita [°C] o AUTO (isoentalpica per x imm. a UR = P3) | P2 = potenza [kW] | P3 = UR [%] (vuoto = 90)",
    "P1 = T uscita [°C] o AUTO (= T imm. − ΔT ventilatori a valle) | oppure P2 = potenza [kW]",
    "P1 = ΔT [K] (tip. 0,5–1) | oppure P2 = potenza ceduta all'aria [kW]",
]
RIF_PORTATA = [
    "Aria esterna (condizioni di progetto)",
    "Aria ambiente",
    "Aria standard 20 °C, 101325 Pa (ρ = 1,204 kg/m³)",
    "Densità fissa ρ = 1,2 kg/m³",
]

# ----------------------------------------------------------- posizioni nel foglio UTA
R_Z, R_PCALC, R_POVR, R_P, R_V, R_OA, R_VRIN, R_VRIC, R_RIF = 6, 7, 8, 9, 10, 11, 12, 13, 14
SEAS = {"E": 16, "I": 46}     # riga di intestazione di ciascuna stagione
NROWS = 6
R_STIMA = 77


def srow(s, off):
    return SEAS[s] + off


# offset dentro la sezione stagionale
O_TEST, O_UREST, O_TAMB, O_URAMB, O_QS, O_QL = 2, 3, 4, 5, 6, 7
O_PE, O_PA, O_PI = 2, 3, 4            # righe della tabella punti (colonne G..O)
O_DT, O_R, O_AVV = 5, 6, 7
O_SEQH, O_COLH, O_R0 = 9, 10, 11       # riga 0 = ingresso, righe 1..6 = O_R0+1..
O_SUMH = 19

# ---------------------------------------------------------- posizioni nel foglio Calcoli
SE_ROWS = {"E": 17, "I": 28}  # E, A, I, R0, R1..R6 (10 righe)
SC_COL = {"E": "D", "I": "E"}  # grandezze di stagione
SC = {"vref": 41, "mtot": 42, "rho": 43, "cpA": 44, "Timm": 45, "ximm": 46, "fgen": 47,
      "mixidx": 48, "fmix": 49, "R": 50, "dT": 51, "xref": 52, "mOA": 53}
TR_ROWS = {"E": 57, "I": 67}  # prime righe del blocco trasformazioni


def se_row(s, k):
    """k: 'E','A','I' oppure 0..6 (uscita riga k)."""
    base = SE_ROWS[s]
    if k == "E":
        return base
    if k == "A":
        return base + 1
    if k == "I":
        return base + 2
    return base + 3 + k


def sc(s, key, sheet=True):
    a = f"${SC_COL[s]}${SC[key]}"
    return f"Calcoli!{a}" if sheet else a


wb = Workbook()
ws = wb.active
ws.title = "UTA"
wd = wb.create_sheet("psicro")
wm = wb.create_sheet("Mollier")
wg = wb.create_sheet("Guida")
wc = wb.create_sheet("Calcoli")
wl = wb.create_sheet("Liste")


# (16/11/2026) obbligo di licenza (CC BY 4.0, regola dei file Excel di EuGEnio): la citazione sta in cima a ogni foglio,
# sotto ogni grafico e nel piè di pagina di ogni pagina stampata
FONTE = "Fonte: EuGEnio – eugenio.statocritico.it"
FONTE_LUNGA = FONTE + " (foglio psicro_UTA.xlsx, licenza CC BY 4.0: chi lo usa o ne riporta grafici e valori deve citarlo)"
F_FONTE = Font(name=ARIAL, size=9, italic=True, color="404040")


def fonte_in_cima(w, rng):
    """Citazione nella riga 1, a destra del titolo (non sposta nessuna cella del foglio)."""
    a = rng.split(":")[0]
    w[a] = FONTE + " (CC BY 4.0)"
    w[a].font = F_FONTE
    w[a].alignment = Alignment(horizontal="right", vertical="top", wrap_text=False)
    if ":" in rng:
        w.merge_cells(rng)


def fonte_sotto(w, col, r0, h_cm):
    """Citazione nella prima riga libera sotto un grafico ancorato alla riga r0 e alto h_cm."""
    pt, r = 0.0, r0
    while pt < h_cm / 2.54 * 72:
        pt += w.row_dimensions[r].height or 15
        r += 1
    w[f"{col}{r}"] = FONTE + " – diagramma calcolato con il foglio psicro_UTA.xlsx (CC BY 4.0)"
    w[f"{col}{r}"].font = F_FONTE
    return r


def put(w, ref, val, font=F_N, fill=None, fmt=None, align=None, border=True):
    c = w[ref]
    c.value = val
    c.font = font
    if fill:
        c.fill = fill
    if fmt:
        c.number_format = fmt
    c.alignment = align if align else Alignment(vertical="center")
    if border:
        c.border = BOX
    return c


def note(w, ref, text, h=140):
    cm = Comment(text, "UTA")
    cm.width = 320
    cm.height = h
    w[ref].comment = cm


def inp(w, ref, val, fmt=None, txt=None, h=140):
    put(w, ref, val, F_IN, FILL_IN, fmt, Alignment(horizontal="center", vertical="center"))
    if txt:
        note(w, ref, txt, h)


def calc(w, ref, val, fmt=None, bold=False, align=None):
    put(w, ref, val, F_B if bold else F_N, FILL_CALC, fmt, align or Alignment(horizontal="center", vertical="center"))


def header(w, row, c1, c2, text, fill, font=F_H, height=20):
    w.merge_cells(f"{c1}{row}:{c2}{row}")
    c = w[f"{c1}{row}"]
    c.value = text
    c.font = F_H_DARK if fill is FILL_EST else font
    c.fill = fill
    c.alignment = Alignment(vertical="center")
    w.row_dimensions[row].height = height


def label(w, row, text, c1="B", c2="C", font=F_N, fill=None):
    w.merge_cells(f"{c1}{row}:{c2}{row}")
    c = w[f"{c1}{row}"]
    c.value = text
    c.font = font
    c.alignment = Alignment(vertical="center", wrap_text=True)
    c.border = BOX
    w[f"{c2}{row}"].border = BOX
    if fill:
        c.fill = fill


# =============================================================================== LISTE
wl["A1"] = "Liste per i menu a tendina (foglio di servizio, può restare nascosto)"
wl["A1"].font = F_B
fonte_in_cima(wl, "F1:I1")
for j, h in enumerate(["N", "Tipo trasformazione", "P1", "P2", "P3", "Descrizione", "Significato parametri (testo mostrato in UTA)"]):
    put(wl, f"{L(1 + j)}2", h, F_B, FILL_SUB)
for i, (n, p1, p2, p3, d) in enumerate(TIPI):
    r = 3 + i
    wl[f"A{r}"] = i + 1
    wl[f"B{r}"] = n
    wl[f"C{r}"] = p1
    wl[f"D{r}"] = p2
    wl[f"E{r}"] = p3
    wl[f"F{r}"] = d
    if True:
        wl[f"G{r}"] = SHORT[i]
    elif n == "Nessuna":
        wl[f"G{r}"] = "Nessun parametro. " + d
    else:
        s = f"P1 = {p1}"
        if p2 != "—":
            s += f" | P2 = {p2}"
        if p3 != "—":
            s += f" | P3 = {p3}"
        wl[f"G{r}"] = s
put(wl, "I2", "Riferimento della portata in volume", F_B, FILL_SUB)
for i, t in enumerate(RIF_PORTATA):
    wl[f"I{3 + i}"] = t
for col, wdt in zip("ABCDEFGHI", [5, 34, 50, 50, 45, 70, 90, 3, 48]):
    wl.column_dimensions[col].width = wdt
TIPI_RNG = f"Liste!$B$3:$B${2 + NT}"
RIF_RNG = "Liste!$I$3:$I$6"

# ================================================================================ UTA
ws.sheet_properties.tabColor = "3A5A80"
widths = {"A": 2, "B": 5, "C": 30, "D": 10, "E": 10, "F": 10, "G": 36, "H": 8.5, "I": 8.5, "J": 8.5,
          "K": 8.5, "L": 8.5, "M": 8.5, "N": 8.5, "O": 8.5, "P": 8.5, "Q": 8.5, "R": 8.5, "S": 9, "T": 38}
for k, v in widths.items():
    ws.column_dimensions[k].width = v

ws["B1"] = "UTA – Trasformazioni psicrometriche e diagramma dell'aria umida"
ws["B1"].font = F_T
fonte_in_cima(ws, "N1:T1")
ws["B2"] = (f"Versione {VERSIONE} del {DATA} – proprietà dell'aria umida secondo ASHRAE Fundamentals 2017 "
            "(Hyland–Wexler). Istruzioni complete nel foglio «Guida».")
ws["B2"].font = F_SM
ws.merge_cells("C3:E3")
put(ws, "C3", "Celle gialle = dati da inserire/modificare", F_IN, FILL_IN)
put(ws, "G3", "Celle grigie = calcolate (non modificare)", F_N, FILL_CALC)
ws.merge_cells("H3:L3")
put(ws, "H3", "Il triangolo rosso nelle celle gialle = nota con istruzioni", F_SM, None, border=False)
ws["T3"] = "Segno potenze: + calore ceduto all'aria, − calore sottratto"
ws["T3"].font = F_SM

# ---------------------------------------------------------------- dati generali
header(ws, 5, "B", "T", "DATI GENERALI", FILL_GEN)
label(ws, R_Z, "Altitudine del sito s.l.m.")
inp(ws, f"D{R_Z}", 120, "0", "Altitudine del sito sul livello del mare [m].\nServe a calcolare la pressione atmosferica "
    "(p = 101325·(1 − 2,25577e-5·z)^5,2559).\nEsempi: Milano 120 m, Roma 20 m, Torino 240 m, L'Aquila 714 m.\nCampo: −400 … 4000 m.")
put(ws, f"E{R_Z}", "m", F_SM)
label(ws, R_PCALC, "Pressione atmosferica calcolata")
calc(ws, f"D{R_PCALC}", f"=101325*(1-0.0000225577*MAX(-500,MIN(8000,D{R_Z})))^5.2559", "0")
put(ws, f"E{R_PCALC}", "Pa", F_SM)
label(ws, R_POVR, "Pressione imposta (facoltativa)")
inp(ws, f"D{R_POVR}", None, "0", "Lasciare VUOTO per usare la pressione calcolata dall'altitudine.\n"
    "Inserire un valore [Pa] solo per imporre una pressione diversa (es. 101325 per il livello del mare standard).\nCampo tipico: 60000 … 105000 Pa.")
put(ws, f"E{R_POVR}", "Pa", F_SM)
label(ws, R_P, "Pressione di calcolo p", font=F_B)
calc(ws, f"D{R_P}", f"=IF(ISNUMBER(D{R_POVR}),MAX(30000,MIN(120000,D{R_POVR})),D{R_PCALC})", "0", bold=True)
put(ws, f"E{R_P}", "Pa", F_SM)
label(ws, R_V, "Portata d'aria di mandata (totale)")
inp(ws, f"D{R_V}", 5000, "#,##0", "Portata volumetrica TOTALE immessa in ambiente [m³/h] (aria esterna + ricircolo).\n"
    "Lo stato a cui si riferisce il volume si sceglie nella cella «Riferimento della portata».\n"
    "Valori tipici: 1000 … 50000 m³/h. Per uffici aria esterna 30–40 m³/h per persona (UNI 10339).")
put(ws, f"E{R_V}", "m³/h", F_SM)
label(ws, R_OA, "Quota di aria esterna (rinnovo)")
inp(ws, f"D{R_OA}", 100, "0", "Percentuale di aria esterna sulla portata totale [%].\n100 = UTA a tutta aria esterna (nessun ricircolo).\n"
    "Valori tipici: 20 … 100 %. Il resto è ricircolo alle condizioni ambiente.\nLa miscela avviene nella riga di tipo «Miscela con ricircolo» (parametro AUTO).")
put(ws, f"E{R_OA}", "%", F_SM)
label(ws, R_VRIN, "Portata di aria esterna (rinnovo)")
calc(ws, f"D{R_VRIN}", f"=D{R_V}*D{R_OA}/100", "#,##0")
put(ws, f"E{R_VRIN}", "m³/h", F_SM)
label(ws, R_VRIC, "Portata di ricircolo")
calc(ws, f"D{R_VRIC}", f"=D{R_V}-D{R_VRIN}", "#,##0")
put(ws, f"E{R_VRIC}", "m³/h", F_SM)
label(ws, R_RIF, "Riferimento della portata")
ws.merge_cells(f"D{R_RIF}:G{R_RIF}")
inp(ws, f"D{R_RIF}", RIF_PORTATA[0], None,
    "Stato dell'aria a cui si riferisce la portata in m³/h (scegliere dal menu):\n"
    "• Aria esterna (default): ṁ = V/(3600·v_esterna)\n• Aria ambiente: ṁ = V/(3600·v_ambiente)\n"
    "• Aria standard 20 °C / 101325 Pa: ρ = 1,204 kg/m³\n• Densità fissa 1,2 kg/m³ (metodo tradizionale)\n"
    "v = volume specifico per kg di aria secca, calcolato con la pressione di calcolo.", 170)
ws[f"D{R_RIF}"].alignment = Alignment(horizontal="left")
for c in "EFG":
    ws[f"{c}{R_RIF}"].fill = FILL_IN
    ws[f"{c}{R_RIF}"].border = BOX
dv_rif = DataValidation(type="list", formula1=RIF_RNG, allow_blank=False)
dv_rif.error = "Scegliere un'opzione dal menu"
dv_rif.errorTitle = "Valore non valido"
ws.add_data_validation(dv_rif)
dv_rif.add(f"D{R_RIF}")

# tabella di conversione della portata
put(ws, "G6", "Conversione portata volume → massa", F_B, FILL_SUB)
put(ws, "H6", "Estate", F_B, FILL_SUB_E, align=CENTER)
put(ws, "I6", "Inverno", F_B, FILL_SUB_I, align=CENTER)
put(ws, "J6", "u.m.", F_B, FILL_SUB, align=CENTER)
conv = [
    ("v di riferimento", "vref", "0.0000", "m³/kg_as"),
    ("ρ aria umida di rif. = (1+x)/v", "rho", "0.0000", "kg/m³"),
    ("ṁ aria secca = V/(3600·v)", "mtot", "0.0000", "kg/s"),
    ("ṁ aria secca", None, "#,##0", "kg/h"),
    ("ṁ aria esterna", "mOA", "0.0000", "kg/s"),
    ("Frazione di ricircolo (AUTO)", "fgen", "0.00", "-"),
]
for i, (lab, key, fmt, um) in enumerate(conv):
    r = 7 + i
    put(ws, f"G{r}", lab, F_N)
    for s, col in (("E", "H"), ("I", "I")):
        if key:
            calc(ws, f"{col}{r}", f"={sc(s, key)}", fmt)
        else:
            calc(ws, f"{col}{r}", f"={col}{r - 1}*3600", fmt)
    put(ws, f"J{r}", um, F_SM, align=CENTER)
ws["G13"] = "ṁ = portata di aria SECCA: tutte le potenze sono Q = ṁ·Δh (h per kg di aria secca)."
ws["G13"].font = F_SM

# ------------------------------------------------------------------ sezioni stagionali
SEQ_COLS = ["N", "Tipo di trasformazione", "P1", "P2", "P3", "Significato dei parametri (dipende dal tipo)",
            "T [°C]", "UR [%]", "x [g/kg]", "h [kJ/kg]", "T rugiada [°C]", "T b.u. [°C]", "v [m³/kg]",
            "ṁ [kg/s]", "Q sens. [kW]", "Q lat. [kW]", "Q tot. [kW]", "Acqua [kg/h]", "Note / avvisi"]
PRESET = {
    "E": [("Miscela con ricircolo", "AUTO", None, None),
          ("Raffreddamento con deumidificazione", "AUTO", 0.1, None),
          ("Post-riscaldamento", "AUTO", None, None),
          ("Ventilatore", 0.7, None, None),
          ("Nessuna", None, None, None),
          ("Nessuna", None, None, None)],
    "I": [("Recuperatore di calore", 0.6, None, None),
          ("Miscela con ricircolo", "AUTO", None, None),
          ("Preriscaldamento", "AUTO", None, 90),
          ("Umidificazione adiabatica", "AUTO", None, None),
          ("Post-riscaldamento", "AUTO", None, None),
          ("Ventilatore", 0.7, None, None)],
}
DEF_IN = {"E": (32, 50, 26, 50, 5000, 1500), "I": (-5, 80, 20, 40, 8000, 500)}   # (15/11/2026, Paolo) ambiente invernale 20 °C / 40 %, come le pagine del sito

dv_tipo = DataValidation(type="list", formula1=TIPI_RNG, allow_blank=True)
dv_tipo.error = "Scegliere un tipo di trasformazione dal menu"
dv_tipo.errorTitle = "Tipo non valido"
ws.add_data_validation(dv_tipo)

TR = {}  # mappa colonne del blocco trasformazioni di Calcoli (riempita più sotto)

for s in ("E", "I"):
    b = SEAS[s]
    est = s == "E"
    nome = "ESTATE" if est else "INVERNO"
    fillH = FILL_EST if est else FILL_INV
    fillS = FILL_SUB_E if est else FILL_SUB_I
    header(ws, b, "B", "T", f"{nome} – condizioni di progetto, carichi e punto di immissione", fillH)
    # sottotitoli
    for c, t in (("B", "Dato di progetto"), ("D", "Valore"), ("E", "u.m.")):
        put(ws, f"{c}{b + 1}", t, F_B, fillS, align=CENTER)
    ws.merge_cells(f"B{b + 1}:C{b + 1}")
    for j, t in enumerate(["Punto", "T [°C]", "UR [%]", "x [g/kg]", "h [kJ/kg]", "T rugiada [°C]",
                           "T b.u. [°C]", "v [m³/kg]", "ρ [kg/m³]"]):
        put(ws, f"{L(7 + j)}{b + 1}", t, F_B, fillS, align=CENTER)
    ws.row_dimensions[b + 1].height = 28
    d = DEF_IN[s]
    if est:
        labs = [("Temperatura esterna di progetto", "°C",
                 "Temperatura a bulbo secco esterna di progetto estiva [°C].\nRiferimento: UNI 10349 / dati climatici locali. "
                 "Esempi: Milano 32 °C, Roma 33 °C, Palermo 34 °C.\nCampo: 25 … 45 °C."),
                ("Umidità relativa esterna", "%",
                 "Umidità relativa esterna estiva di progetto [%].\nEsempio Milano 50 % (x ≈ 15 g/kg). Campo: 20 … 90 %."),
                ("Temperatura ambiente (interna)", "°C",
                 "Temperatura interna di progetto estiva [°C]. Tipico 24 … 27 °C (UNI EN 16798-1)."),
                ("Umidità relativa ambiente", "%",
                 "Umidità relativa interna estiva [%]. Tipico 45 … 60 %."),
                ("Carico sensibile ambiente", "W",
                 "Carico termico SENSIBILE dell'ambiente in estate [W] (positivo = calore entrante: irraggiamento, persone, luci, apparecchi).\n"
                 "Determina la T di immissione: T_imm = T_amb − Qs/(ṁ·cp). Campo tipico: 20 … 120 W/m²."),
                ("Carico latente ambiente", "W",
                 "Carico LATENTE dell'ambiente in estate [W] (vapore prodotto da persone, processi; positivo).\n"
                 "Determina x di immissione: x_imm = x_amb − Ql/(ṁ·r0), r0 = 2501 kJ/kg. Tipico 40–70 W per persona.")]
    else:
        labs = [("Temperatura esterna di progetto", "°C",
                 "Temperatura esterna invernale di progetto [°C] (UNI EN 12831 / UNI 10349).\n"
                 "Esempi: Milano −5 °C, Torino −8 °C, Roma 0 °C, Bologna −5 °C. Campo: −20 … 10 °C."),
                ("Umidità relativa esterna", "%",
                 "Umidità relativa esterna invernale [%]. Tipico 70 … 90 %. Esempio Milano 80 %."),
                ("Temperatura ambiente (interna)", "°C",
                 "Temperatura interna invernale di progetto [°C]. Tipico 20 °C (DPR 412/93)."),
                ("Umidità relativa ambiente", "%",
                 "Umidità relativa interna invernale [%]. Tipico 40 … 50 %; il foglio parte da 40 %, come le pagine del sito."),
                ("Dispersioni termiche ambiente", "W",
                 "Potenza dispersa dall'ambiente in inverno da coprire CON L'ARIA [W] (positivo = perdita).\n"
                 "T_imm = T_amb + Qd/(ṁ·cp). Inserire 0 se l'aria è immessa a temperatura neutra (riscaldamento con altri terminali)."),
                ("Carico latente ambiente", "W",
                 "Apporti LATENTI interni in inverno [W] (persone, processi; positivo). x_imm = x_amb − Ql/(ṁ·r0).")]
    for i, (lab, um, txt) in enumerate(labs):
        r = b + 2 + i
        label(ws, r, lab)
        fmt = "0.0" if um in ("°C", "%") else "#,##0"
        inp(ws, f"D{r}", d[i], fmt, txt)
        put(ws, f"E{r}", um, F_SM)
    # tabella punti E, A, I
    for j, (k, lab) in enumerate((("E", "E – Aria esterna"), ("A", "A – Ambiente"),
                                  ("I", "I – Immissione (dai carichi)"))):
        r = b + 2 + j
        rr = se_row(s, k)
        put(ws, f"G{r}", lab, F_B)
        for col, src, fmt in (("H", "C", "0.0"), ("J", "K", "0.00"), ("K", "H", "0.00"),
                              ("N", "I", "0.0000"), ("O", "J", "0.000")):
            calc(ws, f"{col}{r}", f"=Calcoli!{src}{rr}", fmt)
        calc(ws, f"I{r}", f"=Calcoli!G{rr}*100", "0.0")
    # (le colonne L e M vengono completate dopo aver definito il motore degli stati)
    r = b + O_DT
    put(ws, f"G{r}", "ΔT di immissione |T_amb − T_imm|", F_N)
    calc(ws, f"H{r}", f"={sc(s, 'dT')}", "0.0")
    put(ws, f"I{r}", "K", F_SM)
    r = b + O_R
    put(ws, f"G{r}", "Fattore termico R = Qs/(Qs+Ql)" if est else "R = Qs/(Qs+Ql), Qs = −dispersioni", F_N)
    calc(ws, f"H{r}", f"={sc(s, 'R')}", "0.00")
    put(ws, f"I{r}", "-", F_SM)
    r = b + O_AVV
    put(ws, f"G{r}", "Verifiche del punto di immissione", F_B)
    ws.merge_cells(f"H{r}:T{r}")
    lim = 10 if est else 15
    ximm_ok = (f"IF(Calcoli!G{se_row(s, 'I')}>1,\"UR immissione > 100 %: punto impossibile, aumentare la portata. \",\"\")")
    dtw = (f"IF({sc(s, 'dT')}>{lim},\"ΔT di immissione > {lim} K: rischio discomfort/stratificazione, aumentare la portata. \",\"\")")
    neg = (f"IF({sc(s, 'mtot')}<=0,\"Portata nulla. \",\"\")")
    mixw = (f"IF(AND({sc(s, 'fgen')}>0,{sc(s, 'mixidx')}>{NROWS}),\"Ricircolo previsto nei dati generali ma nessuna riga «Miscela» nella sequenza (calcolo a tutta aria esterna). \",\"\")")
    xw = (f"IF(Calcoli!D{se_row(s, 'I')}<=0,\"x immissione ≤ 0: carico latente troppo alto. \",\"\")")
    calc(ws, f"H{r}", f"=IF(LEN({ximm_ok}&{dtw}&{neg}&{mixw}&{xw})=0,\"OK\",{ximm_ok}&{dtw}&{neg}&{mixw}&{xw})",
         None, align=Alignment(horizontal="left", wrap_text=True, vertical="center"))
    ws.row_dimensions[r].height = 30

    # tabella sequenza
    header(ws, b + O_SEQH, "B", "T", f"Sequenza di trattamento – {nome} (l'ingresso di ogni riga è l'uscita della riga precedente)", fillH)
    hr = b + O_COLH
    for j, t in enumerate(SEQ_COLS):
        put(ws, f"{L(2 + j)}{hr}", t, F_B, fillS, align=CENTER)
    ws.row_dimensions[hr].height = 30
    # riga 0
    r0 = b + O_R0
    put(ws, f"B{r0}", 0, F_B, FILL_CALC, align=CENTER)
    put(ws, f"C{r0}", "Ingresso: aria esterna (punto E)", F_B, FILL_CALC)
    for c in "DEF":
        put(ws, f"{c}{r0}", None, F_N, FILL_CALC)
    put(ws, f"G{r0}", "Stato di partenza della sequenza", F_SM, FILL_CALC)
    for k in range(1, NROWS + 1):
        r = r0 + k
        put(ws, f"B{r}", k, F_B, FILL_CALC, align=CENTER)
        tp, p1, p2, p3 = PRESET[s][k - 1]
        inp(ws, f"C{r}", tp, None,
            "Tipo di trasformazione: scegliere dal menu a tendina.\n«Nessuna» = riga inattiva.\n"
            "Il significato dei parametri P1, P2, P3 compare nella colonna G; i dettagli sono nel foglio «Guida».", 120)
        ws[f"C{r}"].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        dv_tipo.add(f"C{r}")
        for c, v in (("D", p1), ("E", p2), ("F", p3)):
            inp(ws, f"{c}{r}", v, "General",
                {"D": "Parametro P1 (vedi colonna G per il tipo scelto).\nNumero oppure il testo AUTO dove previsto "
                      "(AUTO = valore ricavato dal punto di immissione o dai dati generali).\n"
                      "Esempi: T uscita [°C], x uscita [g/kg], efficienza [0–1], ΔT ventilatore [K]. Lasciare vuoto se non serve.",
                 "E": "Parametro P2 (vedi colonna G).\nEsempi: fattore di bypass BF (0,05–0,20), efficienza latente, "
                      "UR uscita [%], potenza [kW] in alternativa a P1. Vuoto = valore predefinito o non usato.",
                 "F": "Parametro P3 (vedi colonna G).\nEsempi: T ADP batteria fredda [°C], efficienza di saturazione [0–1], "
                      "entalpia del vapore [kJ/kg], UR obiettivo per il preriscaldamento AUTO [%]. Vuoto = predefinito."}[c], 150)
        calc(ws, f"G{r}", f"=IFERROR(INDEX(Liste!$G$3:$G${2 + NT},MATCH(C{r},{TIPI_RNG},0)),\"Tipo non riconosciuto: scegliere dal menu\")",
             None, align=Alignment(wrap_text=True, vertical="top", horizontal="left"))
        ws[f"G{r}"].font = F_SM
        ws.row_dimensions[r].height = 44

# ================================================================= CALCOLI: motore degli stati
wc.sheet_properties.tabColor = "808080"
wc["A1"] = "CALCOLI – foglio di servizio (non modificare). Proprietà dell'aria umida e iterazioni."
wc["A1"].font = Font(name=ARIAL, size=12, bold=True)
fonte_in_cima(wc, "K1:P1")
wc["A2"] = ("Le iterazioni sono srotolate in colonne: T rugiada = Newton su ln psat (3 passi da Magnus); "
            "bulbo umido = Newton con derivata numerica (6 passi) sull'equazione ASHRAE del bulbo umido.")
wc["A2"].font = F_SM
put(wc, "B4", "Pressione di calcolo p", F_B, FILL_SUB)
put(wc, "D4", "=UTA!D9", F_N, FILL_CALC, "0")
put(wc, "E4", "Pa", F_SM)
put(wc, "B5", "Pressione in kPa", F_B, FILL_SUB)
put(wc, "D5", "=D4/1000", F_N, FILL_CALC, "0.000")
put(wc, "E5", "kPa", F_SM)
consts = [("Costanti usate (scritte nelle formule)", ""),
          ("Rapporto masse molari vapore/aria", "0,621945"),
          ("cp aria secca [kJ/kg K]", "1,006"), ("cp vapore [kJ/kg K]", "1,86"),
          ("Calore latente a 0 °C r0 [kJ/kg]", "2501"),
          ("Costante aria secca Ra [kJ/kg K]", "0,287042"), ("Fattore volume 1+1,607858·x", "1,607858"),
          ("Entalpia vapore umidificatore (default) [kJ/kg]", "2676"),
          ("BF default batteria fredda", "0,10"), ("UR uscita umidificatore per preriscaldamento AUTO", "90 %")]
for i, (a, v) in enumerate(consts):
    wc[f"G{4 + i}"] = a
    wc[f"J{4 + i}"] = v
    wc[f"G{4 + i}"].font = F_B if i == 0 else F_SM
    wc[f"J{4 + i}"].font = F_SM

# colonne del motore degli stati
SEC = {}
cols_se = ["lab", "t", "x", "pw", "ps", "phi", "h", "v", "rho", "xg", "xs", "td0", "td1", "td2", "td3"]
for k in range(1, 7):
    cols_se += [f"wa{k}", f"wb{k}", f"tw{k}"]
for i, k in enumerate(cols_se):
    SEC[k] = L(2 + i)
SE_TD = SEC["td3"]
SE_TW = SEC["tw6"]
put(wc, "B15", "MOTORE DEGLI STATI (una riga per ogni stato dell'aria)", F_B, FILL_SUB)
hdrs = {"lab": "Stato", "t": "T [°C]", "x": "x [kg/kg]", "pw": "pv [Pa]", "ps": "psat [Pa]", "phi": "φ [-]",
        "h": "h [kJ/kg]", "v": "v [m³/kg]", "rho": "ρ [kg/m³]", "xg": "x [g/kg]", "xs": "x sat(T) [kg/kg]",
        "td0": "Td0 Magnus", "td1": "Td1", "td2": "Td2", "td3": "T rugiada"}
for k in cols_se:
    t = hdrs.get(k, k)
    if k.startswith("wa"):
        t = f"psat(Tw{k[2]}-1)"
    elif k.startswith("wb"):
        t = f"psat(+δ) {k[2]}"
    elif k.startswith("tw"):
        t = "T bulbo umido" if k == "tw6" else f"Tw{k[2]}"
    put(wc, f"{SEC[k]}16", t, F_B, FILL_GREY, align=CENTER)

UTA_IN = {}  # celle di ingresso UTA per stagione
for s in ("E", "I"):
    b = SEAS[s]
    UTA_IN[s] = {"Te": f"UTA!$D${b + 2}", "URe": f"UTA!$D${b + 3}", "Ta": f"UTA!$D${b + 4}",
                 "URa": f"UTA!$D${b + 5}", "Qs": f"UTA!$D${b + 6}", "Ql": f"UTA!$D${b + 7}"}


def write_state(s, key, labtxt, tf, xf=None, phif=None):
    r = se_row(s, key)
    c = SEC
    wc[f"{c['lab']}{r}"] = labtxt
    wc[f"{c['t']}{r}"] = "=MAX(-100,MIN(200," + tf[1:] + "))"   # protezione da dati assurdi
    t = f"{c['t']}{r}"
    if xf is None:   # da UR
        wc[f"{c['x']}{r}"] = f"=0.621945*{phif}*{c['ps']}{r}/({PL}-{phif}*{c['ps']}{r})"
    else:
        wc[f"{c['x']}{r}"] = xf
    x = f"{c['x']}{r}"
    wc[f"{c['pw']}{r}"] = f"=MAX({PL}*{x}/(0.621945+{x}),0.001)"
    wc[f"{c['ps']}{r}"] = "=" + PS(t)
    wc[f"{c['phi']}{r}"] = f"={c['pw']}{r}/{c['ps']}{r}"
    wc[f"{c['h']}{r}"] = f"=1.006*{t}+{x}*(2501+1.86*{t})"
    wc[f"{c['v']}{r}"] = f"=0.287042*({t}+273.15)*(1+1.607858*{x})/{PK}"
    wc[f"{c['rho']}{r}"] = f"=(1+{x})/{c['v']}{r}"
    wc[f"{c['xg']}{r}"] = f"={x}*1000"
    wc[f"{c['xs']}{r}"] = f"=0.621945*{c['ps']}{r}/({PL}-{c['ps']}{r})"
    pw = f"{c['pw']}{r}"
    wc[f"{c['td0']}{r}"] = "=" + MAGNUS0(pw)
    for a, bb in (("td0", "td1"), ("td1", "td2"), ("td2", "td3")):
        wc[f"{c[bb]}{r}"] = f"=IFERROR({NEWTON_TD(f'{c[a]}{r}', pw)},{c[a]}{r})"
    prev = t
    for k in range(1, 7):
        wa, wbk, tw = f"{c[f'wa{k}']}{r}", f"{c[f'wb{k}']}{r}", f"{c[f'tw{k}']}{r}"
        wc[wa] = f"=IFERROR({PS(prev)},1)"
        wc[wbk] = f"=IFERROR({PS(f'({prev}+0.001)')},1)"
        gA = f"(({WWB(t, prev, wa, PL)})-{x})"
        gB = f"(({WWB(t, f'({prev}+0.001)', wbk, PL)})-{x})"
        wc[tw] = f"=IFERROR({prev}-{gA}*0.001/({gB}-{gA}),{prev})"
        prev = tw
    for k in cols_se:
        cell = wc[f"{SEC[k]}{r}"]
        cell.font = F_N
        cell.fill = FILL_CALC
        cell.border = BOX


# ============================================================ CALCOLI: blocco trasformazioni
TRC = []


def addc(*names):
    for n in names:
        TRC.append(n)


addc("n", "code", "has1", "has2", "has3", "p1", "p2", "p3", "auto1",
     "tin", "xin", "hin", "tdin", "mdot", "cpin",
     "f2", "x2", "h2", "t2", "t3", "x3", "t4", "t5",
     "bf", "xt6", "psadp", "xadp", "pwadp", "a0", "a1", "a2", "a3", "tadp", "ok6", "dry6", "need6", "t6", "x6",
     "mode7", "phit7")
for k in range(1, 7):
    addc(f"s7a{k}", f"s7b{k}", f"s7t{k}")
addc("xs7", "xt7", "t7e", "x7", "t7",
     "hv8", "mode8", "xt8", "phit8")
for k in range(1, 5):
    addc(f"s8p{k}", f"s8t{k}")
addc("s8p5", "x8u", "x8", "t8",
     "phi9", "pw9", "b0", "b1", "b2", "b3", "h9", "t9a", "t9",
     "fandn", "t10a", "t10", "inf10", "fan", "t11",
     "tout", "xout", "hout", "phiout", "Qt", "Ql", "Qs", "water",
     "wmiss", "wtype", "wgen", "nota")
TRL = {n: L(2 + i) for i, n in enumerate(TRC)}
TR.update(TRL)

TR_DESC = {"n": "N", "code": "codice tipo", "has1": "P1 numerico?", "has2": "P2 numerico?", "has3": "P3 numerico?",
           "p1": "P1", "p2": "P2", "p3": "P3", "auto1": "P1=AUTO?", "tin": "T ingresso", "xin": "x ingresso",
           "hin": "h ingresso", "tdin": "Tdew ingresso", "mdot": "ṁ riga [kg/s]", "cpin": "cp umido",
           "f2": "Mix: frazione ric.", "x2": "Mix: x", "h2": "Mix: h", "t2": "Mix: T", "t3": "Recup: T", "x3": "Recup: x",
           "t4": "Risc: T", "t5": "Raffr: T", "bf": "Batt: BF", "xt6": "Batt: x obiettivo", "psadp": "psat(P3)",
           "xadp": "x ADP", "pwadp": "pv ADP", "a0": "ADP0", "a1": "ADP1", "a2": "ADP2", "a3": "ADP3", "tadp": "T ADP",
           "ok6": "Batt: dati ok", "dry6": "Batt secca", "need6": "Nessuna deum.", "t6": "Batt: T out", "x6": "Batt: x out",
           "mode7": "Adiab: modo", "phit7": "Adiab: φ obiettivo", "xs7": "Adiab: x(T*)", "xt7": "Adiab: x obiettivo",
           "t7e": "Adiab: T efficienza", "x7": "Adiab: x out", "t7": "Adiab: T out", "hv8": "Vap: h vapore",
           "mode8": "Vap: modo", "xt8": "Vap: x obiettivo", "phit8": "Vap: φ obiettivo", "s8p5": "Vap: psat fin.",
           "x8u": "Vap: x da UR", "x8": "Vap: x out", "t8": "Vap: T out", "phi9": "Pre: UR obiettivo",
           "pw9": "Pre: pv", "b0": "Pre T0", "b1": "Pre T1", "b2": "Pre T2", "b3": "Pre: T(x_imm,UR)", "h9": "Pre: h obiettivo",
           "t9a": "Pre: T AUTO", "t9": "Pre: T out", "fandn": "ΔT ventil. a valle", "t10a": "Post: T AUTO", "t10": "Post: T out",
           "inf10": "Post: non raggiungibile", "fan": "Ventil: ΔT", "t11": "Ventil: T out", "tout": "T uscita",
           "xout": "x uscita", "hout": "h uscita", "phiout": "φ uscita", "Qt": "Q tot [kW]", "Ql": "Q lat [kW]",
           "Qs": "Q sens [kW]", "water": "acqua [kg/h]", "wmiss": "avviso param.", "wtype": "avviso tipo",
           "wgen": "avviso saturaz.", "nota": "NOTE"}

for s in ("E", "I"):
    b = SEAS[s]
    r0 = TR_ROWS[s]
    nome = "ESTATE" if s == "E" else "INVERNO"
    put(wc, f"B{r0 - 2}", f"TRASFORMAZIONI {nome} (righe 1–6 della sequenza)", F_B, FILL_SUB)
    for n in TRC:
        put(wc, f"{TRL[n]}{r0 - 1}", TR_DESC.get(n, n), F_B, FILL_GREY, align=CENTER)
    wc.row_dimensions[r0 - 1].height = 30
    codes_rng = f"${TRL['code']}${r0}:${TRL['code']}${r0 + NROWS - 1}"
    G = {"p": PL, "Timm": sc(s, "Timm", False), "ximm": sc(s, "ximm", False), "mtot": sc(s, "mtot", False),
         "fgen": sc(s, "fgen", False), "mixidx": sc(s, "mixidx", False), "fmix": sc(s, "fmix", False),
         "tA": f"${SEC['t']}${se_row(s, 'A')}", "xA": f"${SEC['x']}${se_row(s, 'A')}", "hA": f"${SEC['h']}${se_row(s, 'A')}"}
    for k in range(1, NROWS + 1):
        r = r0 + k - 1
        ur = b + O_R0 + k
        prev = se_row(s, k - 1)
        R = {n: f"{TRL[n]}{r}" for n in TRC}
        R.update(G)

        def S(n, f):
            wc[f"{TRL[n]}{r}"] = "=" + f.format(**R) if isinstance(f, str) else f
        S("n", k)
        S("code", f"IFERROR(MATCH(UTA!$C{ur},{TIPI_RNG},0),1)")
        for i, c in enumerate("DEF"):
            S(f"has{i + 1}", f"ISNUMBER(UTA!${c}{ur})")
            S(f"p{i + 1}", f"IF(ISNUMBER(UTA!${c}{ur}),UTA!${c}{ur},0)")
        S("auto1", f"IF(ISTEXT(UTA!$D{ur}),UPPER(TRIM(UTA!$D{ur}))=\"AUTO\",FALSE)")
        S("tin", f"{SEC['t']}{prev}")
        S("xin", f"{SEC['x']}{prev}")
        S("hin", f"{SEC['h']}{prev}")
        S("tdin", f"{SEC['td3']}{prev}")
        S("mdot", "IF({n}<{mixidx},{mtot}*(1-{fmix}),{mtot})")
        S("cpin", "1.006+1.86*{xin}")
        # 2 miscela
        S("f2", "MAX(0,MIN(1,IF({has1},{p1},{fgen})))")
        S("x2", "(1-{f2})*{xin}+{f2}*{xA}")
        S("h2", "(1-{f2})*{hin}+{f2}*{hA}")
        S("t2", "({h2}-2501*{x2})/(1.006+1.86*{x2})")
        # 3 recuperatore
        S("t3", "IF({has1},{tin}+{p1}*({tA}-{tin}),{tin})")
        S("x3", "IF({has1},{xin}+IF({has2},{p2},0)*({xA}-{xin}),{xin})")
        # 4/5 sensibile
        S("t4", "IF({has1},{p1},IF({has2},{tin}+{p2}/({mdot}*{cpin}),{tin}))")
        S("t5", "IF({has1},{p1},IF({has2},{tin}-{p2}/({mdot}*{cpin}),{tin}))")
        # 6 batteria fredda
        S("bf", "IF({has2},{p2},0.1)")
        S("xt6", "IF({has1},{p1}/1000,IF({auto1},{ximm},-1))")
        S("psadp", "IFERROR(IF({has3}," + PS(R["p3"]) + ",0),0)")
        S("xadp", "IF({has3},0.621945*{psadp}/({p}-{psadp}),IF(AND({xt6}>0,{bf}<1),({xt6}-{bf}*{xin})/(1-{bf}),-1))")
        S("pwadp", "IF({xadp}>0,{p}*{xadp}/(0.621945+{xadp}),611.2)")
        wc[f"{TRL['a0']}{r}"] = "=" + MAGNUS0(R["pwadp"])
        for a, bb in (("a0", "a1"), ("a1", "a2"), ("a2", "a3")):
            wc[f"{TRL[bb]}{r}"] = f"=IFERROR({NEWTON_TD(R[a], R['pwadp'])},{R[a]})"
        S("tadp", "IF({has3},{p3},{a3})")
        S("ok6", "AND({xadp}>0,{bf}>=0,{bf}<1)")
        S("dry6", "AND({has3},{xadp}>={xin})")
        S("need6", "AND(NOT({has3}),{xt6}>={xin})")
        S("t6", "IF(OR(NOT({ok6}),{need6}),{tin},{tadp}+{bf}*({tin}-{tadp}))")
        S("x6", "IF(OR(NOT({ok6}),{need6},{dry6}),{xin},{xadp}+{bf}*({xin}-{xadp}))")
        # 7 adiabatica: Newton sulla isoentalpica h = hin fino a φ = phit7
        S("mode7", "IF(OR({has1},{auto1}),1,IF({has2},2,IF({has3},3,0)))")
        S("phit7", "IF({mode7}=2,MIN(1,MAX(0.01,{p2}/100)),1)")
        prevT = R["tin"]
        for it in range(1, 7):
            ca, cb, ct = R[f"s7a{it}"], R[f"s7b{it}"], R[f"s7t{it}"]
            wc[ca] = f"=IFERROR({PS(prevT)},1)"
            wc[cb] = f"=IFERROR({PS(f'({prevT}+0.001)')},1)"
            ph = R["phit7"]
            gA = f"(({R['hin']}-1.006*{prevT})/(2501+1.86*{prevT})-0.621945*{ph}*{ca}/({PL}-{ph}*{ca}))"
            gB = (f"(({R['hin']}-1.006*({prevT}+0.001))/(2501+1.86*({prevT}+0.001))"
                  f"-0.621945*{ph}*{cb}/({PL}-{ph}*{cb}))")
            wc[ct] = f"=IFERROR({prevT}-{gA}*0.001/({gB}-{gA}),{prevT})"
            prevT = ct
        S("xs7", "({hin}-1.006*{s7t6})/(2501+1.86*{s7t6})")
        S("xt7", "IF({has1},{p1}/1000,IF({auto1},{ximm},0))")
        S("t7e", "IF({mode7}=3,{tin}-MAX(0,MIN(1,{p3}))*({tin}-{s7t6}),{tin})")
        S("x7", "CHOOSE({mode7}+1,{xin},MAX({xin},MIN({xt7},{xs7})),MAX({xin},{xs7}),MAX({xin},({hin}-1.006*{t7e})/(2501+1.86*{t7e})))")
        S("t7", "IF({x7}<={xin}+0.000000001,{tin},({hin}-2501*{x7})/(1.006+1.86*{x7}))")
        # 8 vapore
        S("hv8", "IF({has3},{p3},2676)")
        S("mode8", "IF(OR({has1},{auto1}),1,IF({has2},2,0))")
        S("xt8", "IF({has1},{p1}/1000,IF({auto1},{ximm},0))")
        S("phit8", "MIN(1,MAX(0.01,{p2}/100))")
        prevT = R["tin"]
        for it in range(1, 5):
            cp_, ct = R[f"s8p{it}"], R[f"s8t{it}"]
            wc[cp_] = f"=IFERROR({PS(prevT)},1)"
            xk = f"(0.621945*{R['phit8']}*{cp_}/({PL}-{R['phit8']}*{cp_}))"
            wc[ct] = f"=IFERROR(({R['hin']}+({xk}-{R['xin']})*{R['hv8']}-2501*{xk})/(1.006+1.86*{xk}),{R['tin']})"
            prevT = ct
        wc[R["s8p5"]] = f"=IFERROR({PS(prevT)},1)"
        S("x8u", "0.621945*{phit8}*{s8p5}/({p}-{phit8}*{s8p5})")
        S("x8", "IF({mode8}=1,MAX({xin},{xt8}),IF({mode8}=2,MAX({xin},{x8u}),{xin}))")
        S("t8", "({hin}+({x8}-{xin})*{hv8}-2501*{x8})/(1.006+1.86*{x8})")
        # 9 preriscaldamento
        S("phi9", "IF({has3},MIN(1,MAX(0.05,{p3}/100)),0.9)")
        S("pw9", "MAX(1,{p}*{ximm}/(0.621945+{ximm})/{phi9})")
        wc[f"{TRL['b0']}{r}"] = "=" + MAGNUS0(R["pw9"])
        for a, bb in (("b0", "b1"), ("b1", "b2"), ("b2", "b3")):
            wc[f"{TRL[bb]}{r}"] = f"=IFERROR({NEWTON_TD(R[a], R['pw9'])},{R[a]})"
        S("h9", "1.006*{b3}+{ximm}*(2501+1.86*{b3})")
        S("t9a", "({h9}-2501*{xin})/(1.006+1.86*{xin})")
        S("t9", "IF({has1},{p1},IF({auto1},MAX({tin},{t9a}),IF({has2},{tin}+{p2}/({mdot}*{cpin}),{tin})))")
        # 10 post-riscaldamento
        last = r0 + NROWS - 1
        if r < last:
            S("fandn", f"SUM({TRL['fan']}{r + 1}:{TRL['fan']}{last})")
        else:
            S("fandn", "0")
        S("t10a", "{Timm}-{fandn}")
        S("t10", "IF({has1},{p1},IF({auto1},MAX({tin},{t10a}),IF({has2},{tin}+{p2}/({mdot}*{cpin}),{tin})))")
        S("inf10", "AND({code}=10,{auto1},{tin}>{t10a}+0.05)")
        # 11 ventilatore
        S("fan", "IF({code}=11,IF({has1},{p1},IF({has2},{p2}/({mdot}*{cpin}),0)),0)")
        S("t11", "{tin}+{fan}")
        # uscita
        S("tout", "IFERROR(CHOOSE({code},{tin},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11}),{tin})")
        S("xout", "IFERROR(CHOOSE({code},{xin},{x2},{x3},{xin},{xin},{x6},{x7},{x8},{xin},{xin},{xin}),{xin})")
        sr = se_row(s, k)
        S("hout", f"{SEC['h']}{sr}")
        S("phiout", f"{SEC['phi']}{sr}")
        S("Qt", "IF({code}=2,0,{mdot}*({hout}-{hin}))")
        S("Ql", "IF({code}=2,0,{mdot}*({xout}-{xin})*2501)")
        S("Qs", "{Qt}-{Ql}")
        S("water", "IF({code}=2,0,{mdot}*({xout}-{xin})*3600)")
        S("wmiss", "IF(AND(ISERROR(MATCH(UTA!$C" + str(ur) + "," + TIPI_RNG + ",0)),LEN(UTA!$C" + str(ur) +
          ")>0),\"Tipo non riconosciuto. \",\"\")&IF(OR(AND({code}=3,NOT({has1})),AND(OR({code}=4,{code}=5,{code}=11),"
          "NOT(OR({has1},{has2}))),AND(OR({code}=9,{code}=10),NOT(OR({has1},{auto1},{has2}))),"
          "AND({code}=6,NOT(OR({has1},{auto1},{has3}))),AND({code}=7,{mode7}=0),AND({code}=8,{mode8}=0)),"
          "\"Parametro mancante: la riga non modifica lo stato. \",\"\")")
        w2 = ("IF({f2}=0,\"Frazione di ricircolo 0: nessuna miscela (100 % aria esterna). \","
              "\"Ricircolo \"&FIXED({f2}*100,0,TRUE)&\" % in massa; portata a monte \"&FIXED({mtot}*(1-{f2}),3,TRUE)&\" kg/s. \")")
        w3 = ("IF({has1},\"Potenza recuperata \"&FIXED(ABS({Qt}),2,TRUE)&\" kW. \",\"\")")
        w4 = "IF({tout}<{tin}-0.001,\"Attenzione: T uscita < T ingresso (non è un riscaldamento). \",\"\")"
        w5 = ("IF({tout}>{tin}+0.001,\"Attenzione: T uscita > T ingresso. \",\"\")&IF({tout}<{tdin}-0.01,"
              "\"T uscita sotto la T di rugiada dell'aria in ingresso: si forma condensa, usare «Raffreddamento con deumidificazione». \",\"\")")
        w6 = ("IF(NOT({ok6}),\"Dati batteria non validi (x ADP ≤ 0 oppure BF ≥ 1). \","
              "IF({need6},\"x obiettivo ≥ x ingresso: nessuna deumidificazione necessaria (riga senza effetto). \","
              "\"ADP = \"&FIXED({tadp},1,TRUE)&\" °C; SHR = \"&FIXED(IF({Qt}<>0,{Qs}/{Qt},0),2,TRUE)&\"; BF = \"&FIXED({bf},2,TRUE)&\". \""
              "&IF({tadp}<0,\"ADP < 0 °C: rischio di brina. \",\"\")&IF({dry6},\"Batteria secca (ADP sopra la rugiada). \",\"\")))")
        w7 = ("IF(AND({mode7}=1,{xt7}>{xs7}+0.0000001),\"x obiettivo oltre la saturazione: limitato a UR 100 %. \",\"\")"
              "&IF(AND({mode7}>0,{x7}<={xin}+0.000000001),\"Nessuna umidificazione (obiettivo ≤ ingresso). \",\"\")"
              "&IF({mode7}>0,\"h costante = \"&FIXED({hin},2,TRUE)&\" kJ/kg. \",\"\")")
        w8 = ("IF(AND({mode8}>0,{x8}<={xin}+0.000000001),\"Nessuna umidificazione (obiettivo ≤ ingresso). \",\"\")"
              "&IF({mode8}>0,\"Vapore \"&FIXED({water},2,TRUE)&\" kg/h. \",\"\")")
        w9 = ("IF(AND({auto1},{t9a}<={tin}),\"Preriscaldamento non necessario (entalpia già sufficiente). \","
              "IF({auto1},\"AUTO: fino a h = \"&FIXED({h9},2,TRUE)&\" kJ/kg (isoentalpica per x_imm a UR \"&FIXED({phi9}*100,0,TRUE)&\" %). \",\"\"))")
        w10 = ("IF({inf10},\"PUNTO DI IMMISSIONE NON RAGGIUNGIBILE: T ingresso (\"&FIXED({tin},1,TRUE)&\" °C) > T richiesta (\"&FIXED({t10a},1,TRUE)&"
               "\" °C). Aumentare la portata o ridurre BF. \",IF({auto1},\"AUTO: T = T_imm − ΔT ventilatori a valle = \"&FIXED({t10a},1,TRUE)&\" °C. \",\"\"))")
        w11 = "\"\""
        S("wtype", "IFERROR(CHOOSE({code},\"\"," + ",".join([w2, w3, w4, w5, w6, w7, w8, w9, w10, w11]) + "),\"\")")
        S("wgen", "IF({phiout}>1.0001,\"OLTRE SATURAZIONE (UR > 100 %): stato non fisico, nebbia/condensa. \",\"\")")
        S("nota", "IF({code}=1,IF(LEN({wmiss})>0,{wmiss},\"\"),IF(LEN({wmiss}&{wtype}&{wgen})=0,\"OK\",{wmiss}&{wgen}&{wtype}))")
        for n in TRC:
            cell = wc[f"{TRL[n]}{r}"]
            cell.font = F_N
            cell.fill = FILL_CALC
            cell.border = BOX

# grandezze di stagione
put(wc, "B39", "GRANDEZZE DI STAGIONE", F_B, FILL_SUB)
put(wc, "D40", "Estate", F_B, FILL_SUB_E, align=CENTER)
put(wc, "E40", "Inverno", F_B, FILL_SUB_I, align=CENTER)
SC_DESC = {"vref": "v di riferimento per la portata [m³/kg_as]", "mtot": "ṁ aria secca di mandata [kg/s]",
           "rho": "ρ aria umida di riferimento [kg/m³]", "cpA": "cp umido ambiente 1,006+1,86·x_amb [kJ/kg K]",
           "Timm": "T immissione [°C]", "ximm": "x immissione [kg/kg]", "fgen": "frazione di ricircolo dai dati generali [-]",
           "mixidx": "riga della prima «Miscela» (99 = nessuna)", "fmix": "frazione di ricircolo della miscela [-]",
           "R": "fattore termico R [-]", "dT": "|T_amb − T_imm| [K]", "xref": "x dello stato di riferimento [kg/kg]",
           "mOA": "ṁ aria esterna [kg/s]"}
for s in ("E", "I"):
    c = SC_COL[s]
    IN = UTA_IN[s]
    eE, eA = se_row(s, "E"), se_row(s, "A")
    idx = f"IFERROR(MATCH(UTA!$D${R_RIF},{RIF_RNG},0),1)"
    f = {
        "xref": f"=CHOOSE({idx},{SEC['x']}{eE},{SEC['x']}{eA},0,{SEC['x']}{eE})",
        "vref": f"=CHOOSE({idx},{SEC['v']}{eE},{SEC['v']}{eA},0.287042*293.15/101.325,(1+{SEC['x']}{eE})/1.2)",
        "mtot": f"=UTA!$D${R_V}/3600/{c}{SC['vref']}",
        "rho": f"=(1+{c}{SC['xref']})/{c}{SC['vref']}",
        "cpA": f"=1.006+1.86*{SEC['x']}{eA}",
        "Timm": (f"={SEC['t']}{eA}-{IN['Qs']}/1000/({c}{SC['mtot']}*{c}{SC['cpA']})" if s == "E" else
                 f"={SEC['t']}{eA}+{IN['Qs']}/1000/({c}{SC['mtot']}*{c}{SC['cpA']})"),
        "ximm": f"={SEC['x']}{eA}-{IN['Ql']}/1000/({c}{SC['mtot']}*2501)",
        "fgen": f"=MAX(0,MIN(1,1-UTA!$D${R_OA}/100))",
        "mixidx": f"=IFERROR(MATCH(2,${TRL['code']}${TR_ROWS[s]}:${TRL['code']}${TR_ROWS[s] + NROWS - 1},0),99)",
        "fmix": f"=IF({c}{SC['mixidx']}<99,INDEX(${TRL['f2']}${TR_ROWS[s]}:${TRL['f2']}${TR_ROWS[s] + NROWS - 1},{c}{SC['mixidx']}),0)",
        "R": (f"=IF(({IN['Qs']}+{IN['Ql']})<>0,{IN['Qs']}/({IN['Qs']}+{IN['Ql']}),1)" if s == "E" else
              f"=IF((-{IN['Qs']}+{IN['Ql']})<>0,-{IN['Qs']}/(-{IN['Qs']}+{IN['Ql']}),1)"),
        "dT": f"=ABS({SEC['t']}{eA}-{c}{SC['Timm']})",
        "mOA": f"={c}{SC['mtot']}*(1-{c}{SC['fmix']})",
    }
    for key, row in SC.items():
        put(wc, f"{c}{row}", f[key], F_N, FILL_CALC, "0.0000")
for key, row in SC.items():
    put(wc, f"B{row}", SC_DESC[key], F_N)
    wc.merge_cells(f"B{row}:C{row}")

# stati
for s in ("E", "I"):
    IN = UTA_IN[s]
    write_state(s, "E", "E – esterno", f"={IN['Te']}", phif=f"({IN['URe']}/100)")
    write_state(s, "A", "A – ambiente", f"={IN['Ta']}", phif=f"({IN['URa']}/100)")
    write_state(s, "I", "I – immissione", f"={sc(s, 'Timm', False)}", xf=f"={sc(s, 'ximm', False)}")
    e = se_row(s, "E")
    write_state(s, 0, "R0 – ingresso (= E)", f"={SEC['t']}{e}", xf=f"={SEC['x']}{e}")
    for k in range(1, NROWS + 1):
        tr = TR_ROWS[s] + k - 1
        write_state(s, k, f"R{k} – uscita riga {k}", f"={TRL['tout']}{tr}", xf=f"={TRL['xout']}{tr}")
wc["A17"] = "ESTATE"
wc["A28"] = "INVERNO"
for a in ("A17", "A28"):
    wc[a].font = F_B

# completamento tabella punti UTA (T rugiada / bulbo umido)
for s in ("E", "I"):
    b = SEAS[s]
    for j, k in enumerate(("E", "A", "I")):
        r = b + 2 + j
        rr = se_row(s, k)
        calc(ws, f"L{r}", f"=Calcoli!{SE_TD}{rr}", "0.0")
        calc(ws, f"M{r}", f"=IF(Calcoli!{SEC['phi']}{rr}>1,\"—\",Calcoli!{SE_TW}{rr})", "0.0")

# ============================================================ UTA: righe della sequenza (risultati)
for s in ("E", "I"):
    b = SEAS[s]
    for k in range(0, NROWS + 1):
        r = b + O_R0 + k
        rr = se_row(s, k)
        tr = TR_ROWS[s] + k - 1
        vals = [("H", f"=Calcoli!{SEC['t']}{rr}", "0.0"), ("I", f"=Calcoli!{SEC['phi']}{rr}*100", "0.0"),
                ("J", f"=Calcoli!{SEC['xg']}{rr}", "0.00"), ("K", f"=Calcoli!{SEC['h']}{rr}", "0.00"),
                ("L", f"=Calcoli!{SE_TD}{rr}", "0.0"), ("M", f"=Calcoli!{SE_TW}{rr}", "0.0"),
                ("N", f"=Calcoli!{SEC['v']}{rr}", "0.0000")]
        if k == 0:
            vals += [("O", f"={sc(s, 'mOA')}", "0.000"),
                     ("P", None, None), ("Q", None, None), ("R", None, None), ("S", None, None), ("T", "Aria esterna di progetto", None)]
        else:
            vals += [("O", f"=Calcoli!{TRL['mdot']}{tr}", "0.000"), ("P", f"=Calcoli!{TRL['Qs']}{tr}", "0.00"),
                     ("Q", f"=Calcoli!{TRL['Ql']}{tr}", "0.00"), ("R", f"=Calcoli!{TRL['Qt']}{tr}", "0.00"),
                     ("S", f"=Calcoli!{TRL['water']}{tr}", "0.00"), ("T", f"=Calcoli!{TRL['nota']}{tr}", None)]
        for col, f, fmt in vals:
            calc(ws, f"{col}{r}", f, fmt, bold=(col == "R" and k > 0))
        ws[f"T{r}"].alignment = Alignment(wrap_text=True, vertical="top", horizontal="left")
        ws[f"T{r}"].font = F_SM

    # riepilogo
    nome = "ESTATE" if s == "E" else "INVERNO"
    fillH = FILL_EST if s == "E" else FILL_INV
    fillS = FILL_SUB_E if s == "E" else FILL_SUB_I
    hs = b + O_SUMH
    header(ws, hs, "B", "T", f"Riepilogo {nome}", fillH)
    tr0, tr1 = TR_ROWS[s], TR_ROWS[s] + NROWS - 1
    codeR = f"Calcoli!${TRL['code']}${tr0}:${TRL['code']}${tr1}"

    def sumif(code, key):
        return f"SUMIF({codeR},{code},Calcoli!${TRL[key]}${tr0}:${TRL[key]}${tr1})"
    summ = [
        ("Potenza frigorifera totale batterie", f"=-({sumif(5, 'Qt')}+{sumif(6, 'Qt')})", "kW"),
        ("   di cui sensibile", f"=-({sumif(5, 'Qs')}+{sumif(6, 'Qs')})", "kW"),
        ("   di cui latente", f"=-({sumif(5, 'Ql')}+{sumif(6, 'Ql')})", "kW"),
        ("Preriscaldamento", f"={sumif(9, 'Qt')}", "kW"),
        ("Post-riscaldamento / riscaldamento", f"={sumif(10, 'Qt')}+{sumif(4, 'Qt')}", "kW"),
        ("Acqua condensata", f"=-{sumif(6, 'water')}", "kg/h"),
        ("Acqua di umidificazione", f"={sumif(7, 'water')}+{sumif(8, 'water')}", "kg/h"),
        ("Potenza recuperata", f"=ABS({sumif(3, 'Qt')})", "kW"),
        ("Calore dei ventilatori", f"={sumif(11, 'Qt')}", "kW"),
    ]
    for i, (lab, f, um) in enumerate(summ):
        r = hs + 1 + i
        label(ws, r, lab, font=F_B if i in (0, 3, 4) else F_N)
        calc(ws, f"D{r}", f, "0.00", bold=True)
        put(ws, f"E{r}", um, F_SM)
    # verifica uscita UTA vs immissione
    rl = se_row(s, NROWS)
    ri = se_row(s, "I")
    r = hs + 1
    put(ws, f"G{r}", "Confronto", F_B, fillS)
    for j, t in enumerate(["T [°C]", "UR [%]", "x [g/kg]", "h [kJ/kg]"]):
        put(ws, f"{L(8 + j)}{r}", t, F_B, fillS, align=CENTER)
    for j, (lab, rowx) in enumerate((("Uscita UTA (ultima riga)", rl), ("Immissione richiesta (I)", ri))):
        rr = r + 1 + j
        put(ws, f"G{rr}", lab, F_N)
        calc(ws, f"H{rr}", f"=Calcoli!{SEC['t']}{rowx}", "0.0")
        calc(ws, f"I{rr}", f"=Calcoli!{SEC['phi']}{rowx}*100", "0.0")
        calc(ws, f"J{rr}", f"=Calcoli!{SEC['xg']}{rowx}", "0.00")
        calc(ws, f"K{rr}", f"=Calcoli!{SEC['h']}{rowx}", "0.00")
    rr = r + 3
    put(ws, f"G{rr}", "Scostamento (uscita − immissione)", F_N)
    for col in "HIJK":
        calc(ws, f"{col}{rr}", f"={col}{rr - 2}-{col}{rr - 1}", "0.00")
    rr = r + 4
    put(ws, f"G{rr}", "Punto di immissione raggiungibile?", F_B)
    inf = f"SUMPRODUCT(--(Calcoli!${TRL['inf10']}${tr0}:${TRL['inf10']}${tr1}))"
    calc(ws, f"H{rr}", f"=IF(OR({inf}>0,ABS(H{rr - 1})>0.3,ABS(J{rr - 1})>0.1),\"NO\",\"SÌ\")", None, bold=True)
    rr = r + 5
    put(ws, f"G{rr}", "Esito", F_B)
    ws.merge_cells(f"H{rr}:T{rr}")
    calc(ws, f"H{rr}", f"=IF({inf}>0,\"PUNTO DI IMMISSIONE NON RAGGIUNGIBILE: l'aria a monte del post-riscaldamento è già più calda della T di immissione richiesta "
                       f"(post-riscaldamento = 0). Aumentare la portata o ridurre il fattore di bypass BF.\","
                       f"IF(H{rr - 1}=\"SÌ\",\"Lo stato in uscita dall'UTA coincide con il punto di immissione richiesto.\","
                       f"\"L'uscita dell'UTA NON coincide con il punto di immissione: verificare tipi e parametri della sequenza (scostamenti sopra).\"))",
         None, align=Alignment(horizontal="left", vertical="center", wrap_text=True))
    ws.row_dimensions[rr].height = 30

# ------------------------------------------------------------- stima stagionale
rs = R_STIMA
header(ws, rs, "B", "T", "STIMA STAGIONALE (indicativa, metodo dei gradi giorno – solo aria esterna di rinnovo)", FILL_GEN)
stima_in = [
    ("Gradi giorno GG", 2404, "K·g", "0",
     "Gradi giorno della località (DPR 412/93, base 20 °C) [K·giorno].\nEsempi: Milano 2404, Torino 2617, Bologna 2259, Roma 1415, Napoli 1034, Palermo 751."),
    ("Ore di funzionamento giornaliere", 12, "h/g", "0",
     "Ore al giorno in cui l'UTA funziona durante la stagione di riscaldamento [h/giorno], 1 … 24."),
    ("Rendimento medio generazione", 0.9, "-", "0.00",
     "Rendimento medio stagionale del generatore di calore [-]. Caldaia a condensazione 0,90–1,00; pompa di calore: usare il COP medio (es. 3)."),
    ("PCI combustibile (gas naturale)", 9.59, "kWh/Sm³", "0.00",
     "Potere calorifico inferiore del combustibile [kWh/Sm³]. Gas naturale ≈ 9,59 kWh/Sm³ (34,5 MJ/Sm³)."),
    ("Ore equivalenti pieno carico estate", 500, "h", "0",
     "Ore equivalenti di funzionamento a piena potenza della batteria fredda nella stagione estiva [h]. Tipico 300 … 900 h."),
    ("EER medio gruppo frigo", 3.0, "-", "0.00",
     "Efficienza media stagionale del gruppo frigorifero (EER/SEER) [-]. Tipico 2,5 … 5."),
]
for i, (lab, v, um, fmt, txt) in enumerate(stima_in):
    r = rs + 1 + i
    label(ws, r, lab)
    inp(ws, f"D{r}", v, fmt, txt)
    put(ws, f"E{r}", um, F_SM)
GG, HG, ETA, PCI, HEQ, EER = [f"D{rs + 1 + i}" for i in range(6)]
trI0, trI1 = TR_ROWS["I"], TR_ROWS["I"] + NROWS - 1
eps = (f"IFERROR(INDEX(Calcoli!${TRL['p1']}${trI0}:${TRL['p1']}${trI1},MATCH(3,Calcoli!${TRL['code']}${trI0}:${TRL['code']}${trI1},0)),0)")
stima_out = [
    ("ṁ aria esterna (inverno)", f"={sc('I', 'mOA')}", "kg/s", "0.000"),
    ("εs recuperatore (prima riga invernale)", f"={eps}", "-", "0.00"),
    ("Fabbisogno senza recupero ṁ·cp·GG·ore", f"=H{rs + 1}*{sc('I', 'cpA')}*{GG}*{HG}", "kWh", "#,##0"),
    ("Energia recuperata = fabbisogno·ε", f"=H{rs + 3}*H{rs + 2}", "kWh", "#,##0"),
    ("Fabbisogno netto ventilazione", f"=H{rs + 3}-H{rs + 4}", "kWh", "#,##0"),
    ("Combustibile = netto/(η·PCI)", f"=IF({ETA}*{PCI}>0,H{rs + 5}/({ETA}*{PCI}),0)", "Sm³", "#,##0"),
    ("Energia frigorifera = P frigo·ore eq.", f"=D{SEAS['E'] + O_SUMH + 1}*{HEQ}", "kWh", "#,##0"),
    ("Energia elettrica frigo = E frigo/EER", f"=IF({EER}>0,H{rs + 7}/{EER},0)", "kWh", "#,##0"),
]
for i, (lab, f, um, fmt) in enumerate(stima_out):
    r = rs + 1 + i
    put(ws, f"G{r}", lab, F_N)
    calc(ws, f"H{r}", f, fmt, bold=i in (4, 5, 7))
    put(ws, f"I{r}", um, F_SM)
ws.merge_cells(f"B{rs + 10}:T{rs + 10}")
ws[f"B{rs + 10}"] = ("STIMA: considera solo il calore SENSIBILE per portare l'aria esterna di rinnovo da T esterna a 20 °C "
                     "(gradi giorno base 20 °C), con UTA in funzione «ore/24» del tempo; non include umidificazione, "
                     "post-riscaldamento per i carichi, perdite di distribuzione né l'effetto della temperatura minima del recuperatore.")
ws[f"B{rs + 10}"].font = F_SM
ws[f"B{rs + 10}"].alignment = WRAP
ws.row_dimensions[rs + 10].height = 30

# formattazioni condizionali (avvisi)
red_fill = PatternFill("solid", fgColor="FFC7CE")
for s in ("E", "I"):
    b = SEAS[s]
    rng = f"T{b + O_R0 + 1}:T{b + O_R0 + NROWS}"
    ws.conditional_formatting.add(rng, FormulaRule(formula=["OR(" + ",".join(f'ISNUMBER(SEARCH("{w}",T{b + O_R0 + 1}))' for w in ("RAGGIUNGIBILE", "SATURAZIONE", "mancante", "Attenzione", "brina", "riconosciuto", "non validi", "rugiada dell")) + ")"], fill=red_fill))
    ra = b + O_AVV
    ws.conditional_formatting.add(f"H{ra}", FormulaRule(formula=[f'H{ra}<>"OK"'], fill=red_fill))
    rr = b + O_SUMH + 5
    ws.conditional_formatting.add(f"H{rr}", FormulaRule(formula=[f'H{rr}="NO"'], fill=red_fill))

ws.freeze_panes = "D4"


# ============================================================ CALCOLI: dati del diagramma
CH0 = 100
put(wc, f"B{CH0}", "DATI DEL DIAGRAMMA PSICROMETRICO (curve ritagliate all'area T −10…50 °C, x 0…30 g/kg)", F_B, FILL_SUB)
XMAX = 0.030
# tabella di saturazione (passo 0,5 K)
for j, t in enumerate(["T [°C]", "psat [Pa]", "x sat [g/kg]", "h sat [kJ/kg]", "v sat [m³/kg]"]):
    put(wc, f"{L(2 + j)}{CH0 + 2}", t, F_B, FILL_GREY, align=CENTER)
SAT0 = CH0 + 3
NSAT = 121
for i in range(NSAT):
    r = SAT0 + i
    wc[f"B{r}"] = -10 + 0.5 * i
    wc[f"C{r}"] = "=" + PS(f"B{r}")
    wc[f"D{r}"] = f"=1000*0.621945*C{r}/({PL}-C{r})"
    wc[f"E{r}"] = f"=1.006*B{r}+D{r}/1000*(2501+1.86*B{r})"
    wc[f"F{r}"] = f"=0.287042*(B{r}+273.15)*(1+1.607858*D{r}/1000)/{PK}"
SAT1 = SAT0 + NSAT - 1
TS_RNG = f"$B${SAT0}:$B${SAT1}"
HS_RNG = f"$E${SAT0}:$E${SAT1}"
VS_RNG = f"$F${SAT0}:$F${SAT1}"

# curve di umidità relativa (10 curve x 41 punti)
PHIS = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]
RH_HDR = CH0 + 2       # nome
RH_PTS0 = CH0 + 11     # primo punto
NPT = 41
RH_SER = []
for j, phi in enumerate(PHIS):
    ct, cx = L(8 + 2 * j), L(9 + 2 * j)
    r = RH_HDR
    wc[f"{ct}{r}"] = f"UR {int(phi * 100)}%"
    wc[f"{ct}{r}"].font = F_B
    wc[f"{ct}{r + 1}"] = phi                                   # φ
    wc[f"{ct}{r + 2}"] = f"={PL}*{XMAX}/(0.621945+{XMAX})/{ct}{r + 1}"   # psat richiesta per x = 30 g/kg
    wc[f"{ct}{r + 3}"] = "=" + MAGNUS0(f"{ct}{r + 2}")
    for a in range(3):
        wc[f"{ct}{r + 4 + a}"] = "=" + NEWTON_TD(f"{ct}{r + 3 + a}", f"{ct}{r + 2}")
    wc[f"{ct}{r + 7}"] = f"=MIN(50,{ct}{r + 6})"                  # T finale
    wc[f"{cx}{r + 1}"] = "φ"
    wc[f"{cx}{r + 7}"] = "T fine"
    for i in range(NPT):
        rr = RH_PTS0 + i
        wc[f"{ct}{rr}"] = f"=-10+({ct}${r + 7}+10)*{i}/{NPT - 1}"
        ps = PS(f"{ct}{rr}")
        wc[f"{cx}{rr}"] = f"=1000*0.621945*{ct}${r + 1}*{ps}/({PL}-{ct}${r + 1}*{ps})"
    RH_SER.append((ct, cx, f"{ct}{r}"))
RH_PTS1 = RH_PTS0 + NPT - 1

# linee isoentalpiche
H0 = 160
HVALS = list(range(0, 121, 10))
for j, t in enumerate(["nome", "h [kJ/kg]", "indice", "T sat(h)", "T a x=30", "T inizio", "T fine",
                       "T1", "T2", "T3", "T4", "T5", "x1", "x2", "x3", "x4", "x5"]):
    put(wc, f"{L(8 + j)}{H0 - 1}", t, F_B, FILL_GREY, align=CENTER)
H_SER = []
for i, h in enumerate(HVALS):
    r = H0 + i
    wc[f"H{r}"] = f"h {h}"
    wc[f"I{r}"] = h
    wc[f"J{r}"] = f"=IFERROR(MATCH(I{r},{HS_RNG},1),0)"
    wc[f"K{r}"] = (f"=IF(J{r}<1,-10,IF(J{r}>={NSAT},50,INDEX({TS_RNG},J{r})+(I{r}-INDEX({HS_RNG},J{r}))/"
                   f"(INDEX({HS_RNG},J{r}+1)-INDEX({HS_RNG},J{r}))*0.5))")
    wc[f"L{r}"] = f"=(I{r}-2501*{XMAX})/(1.006+1.86*{XMAX})"
    wc[f"M{r}"] = f"=MAX(-10,K{r},L{r})"
    wc[f"N{r}"] = f"=MAX(M{r},MIN(50,I{r}/1.006))"
    for k in range(5):
        cT, cX = L(15 + k), L(20 + k)
        wc[f"{cT}{r}"] = f"=M{r}+(N{r}-M{r})*{k}/4"
        wc[f"{cX}{r}"] = f"=MAX(0,1000*(I{r}-1.006*{cT}{r})/(2501+1.86*{cT}{r}))"
    H_SER.append(r)

# linee a volume specifico costante
V0 = 180
for j, t in enumerate(["nome", "v [m³/kg]", "indice", "T sat(v)", "T a x=30", "T inizio", "T a x=0", "T fine",
                       "T1", "T2", "T3", "T4", "x1", "x2", "x3", "x4"]):
    put(wc, f"{L(8 + j)}{V0 - 1}", t, F_B, FILL_GREY, align=CENTER)
V_SER = []
for i in range(10):
    r = V0 + i
    if i == 0:
        wc[f"I{r}"] = f"=ROUNDUP(0.287042*263.15/{PK}/0.02,0)*0.02"
    else:
        wc[f"I{r}"] = f"=I{r - 1}+0.02"
    wc[f"H{r}"] = f"=\"v \"&FIXED(I{r},2,TRUE)"
    wc[f"J{r}"] = f"=IFERROR(MATCH(I{r},{VS_RNG},1),0)"
    wc[f"K{r}"] = (f"=IF(J{r}<1,-10,IF(J{r}>={NSAT},50,INDEX({TS_RNG},J{r})+(I{r}-INDEX({VS_RNG},J{r}))/"
                   f"(INDEX({VS_RNG},J{r}+1)-INDEX({VS_RNG},J{r}))*0.5))")
    wc[f"L{r}"] = f"=I{r}*{PK}/(0.287042*(1+1.607858*{XMAX}))-273.15"
    wc[f"M{r}"] = f"=MAX(-10,K{r},L{r})"
    wc[f"N{r}"] = f"=I{r}*{PK}/0.287042-273.15"
    wc[f"O{r}"] = f"=MAX(M{r},MIN(50,N{r}))"
    for k in range(4):
        cT, cX = L(16 + k), L(20 + k)
        wc[f"{cT}{r}"] = f"=M{r}+(O{r}-M{r})*{k}/3"
        wc[f"{cX}{r}"] = f"=MAX(0,1000*(I{r}*{PK}/(0.287042*({cT}{r}+273.15))-1)/1.607858)"
    V_SER.append(r)

# rette ambiente e goniometro
RA0 = 200
put(wc, f"H{RA0 - 1}", "Retta ambiente (da A verso I, prolungata ×2)", F_B, FILL_GREY)
for j, s in enumerate(("E", "I")):
    ct, cx = L(8 + 2 * j), L(9 + 2 * j)
    a, i_ = se_row(s, "A"), se_row(s, "I")
    wc[f"{ct}{RA0}"] = "T " + ("estate" if s == "E" else "inverno")
    wc[f"{cx}{RA0}"] = "x [g/kg]"
    wc[f"{ct}{RA0 + 1}"] = f"={SEC['t']}{a}"
    wc[f"{cx}{RA0 + 1}"] = f"={SEC['xg']}{a}"
    wc[f"{ct}{RA0 + 2}"] = f"=MAX(-10,MIN(50,{SEC['t']}{a}+2*({SEC['t']}{i_}-{SEC['t']}{a})))"
    wc[f"{cx}{RA0 + 2}"] = (f"=MAX(0,{SEC['xg']}{a}+IF({SEC['t']}{i_}<>{SEC['t']}{a},({ct}{RA0 + 2}-{SEC['t']}{a})/"
                            f"({SEC['t']}{i_}-{SEC['t']}{a}),2)*({SEC['xg']}{i_}-{SEC['xg']}{a}))")

GO = 206
put(wc, f"H{GO}", "Goniometro del fattore termico R (centro, raggi)", F_B, FILL_GREY)
wc[f"H{GO + 1}"] = "cx"
wc[f"I{GO + 1}"] = 0
wc[f"H{GO + 2}"] = "cy"
wc[f"I{GO + 2}"] = 30
wc[f"H{GO + 3}"] = "raggio x [K]"
wc[f"I{GO + 3}"] = 8
wc[f"H{GO + 4}"] = "raggio y [g/kg]"
wc[f"I{GO + 4}"] = 6.4
CX, CY, RX, RY = f"$I${GO + 1}", f"$I${GO + 2}", f"$I${GO + 3}", f"$I${GO + 4}"
ARC0 = GO + 7
wc[f"H{ARC0 - 1}"] = "arco T"
wc[f"I{ARC0 - 1}"] = "arco x"
for i in range(19):
    th = 180 + 5 * i
    wc[f"H{ARC0 + i}"] = f"={CX}+{RX}*COS(RADIANS({th}))"
    wc[f"I{ARC0 + i}"] = f"={CY}+{RY}*SIN(RADIANS({th}))"
RTICKS = [1.0, 0.8, 0.6, 0.4, 0.2, 0.0]
TICK_SER = []
for j, R_ in enumerate(RTICKS):
    ct, cx = L(11 + 2 * j), L(12 + 2 * j)
    wc[f"{ct}{ARC0 - 2}"] = f"R={str(R_).replace('.', ',')}" if R_ not in (1.0, 0.0) else f"R={int(R_)}"
    wc[f"{ct}{ARC0 - 1}"] = R_
    # direzione (−R, −(1−R)·cp/r0·1000) normalizzata nello spazio "visivo"
    dT = f"(-{ct}${ARC0 - 1}/{RX})"
    dX = f"(-(1-{ct}${ARC0 - 1})*{sc('E', 'cpA', False)}/2501*1000/{RY})"
    nrm = f"SQRT({dT}^2+{dX}^2)"
    for q, frac in enumerate((0.86, 1.0)):
        wc[f"{ct}{ARC0 + q}"] = f"={CX}+{frac}*{RX}*{dT}/{nrm}"
        wc[f"{cx}{ARC0 + q}"] = f"={CY}+{frac}*{RY}*{dX}/{nrm}"
    TICK_SER.append((ct, cx, f"{ct}{ARC0 - 2}"))
RL = []
for j, s in enumerate(("E", "I")):
    ct, cx = L(24 + 2 * j), L(25 + 2 * j)
    a, i_ = se_row(s, "A"), se_row(s, "I")
    wc[f"{ct}{ARC0 - 2}"] = "R estate" if s == "E" else "R inverno"
    dT = f"(({SEC['t']}{i_}-{SEC['t']}{a})/{RX})"
    dX = f"(({SEC['xg']}{i_}-{SEC['xg']}{a})/{RY})"
    nrm = f"MAX(0.000001,SQRT({dT}^2+{dX}^2))"
    wc[f"{ct}{ARC0}"] = f"={CX}"
    wc[f"{cx}{ARC0}"] = f"={CY}"
    wc[f"{ct}{ARC0 + 1}"] = f"={CX}+{RX}*{dT}/{nrm}"
    wc[f"{cx}{ARC0 + 1}"] = f"=MIN(30,{CY}+{RY}*{dX}/{nrm})"
    RL.append((ct, cx))

for col in range(1, 60):
    wc.column_dimensions[L(col)].width = 11
wc.column_dimensions["A"].width = 9
wc.column_dimensions["B"].width = 14
wc.freeze_panes = "C17"
wc.print_area = "A1:AH72"
wc.page_setup.orientation = "landscape"
wc.page_setup.fitToWidth = 1
wc.page_setup.fitToHeight = 0
wc.sheet_properties.pageSetUpPr.fitToPage = True

# ===================================================================== GRAFICO


def rich(sz=700, color="404040", b=False):
    cp = CharacterProperties(sz=sz, b=b, solidFill=color, latin=DFont(typeface="Arial"))
    return RichText(p=[Paragraph(pPr=ParagraphProperties(defRPr=cp), endParaRPr=cp)])


def make_series(sh, ct, cx, r0, r1, name=None, name_ref=None, color="000000", width=0.75, dash=None,
                marker=None, msize=5, label_idx=None, label_pos="r", label_color=None, label_sz=700, rows=False,
                nolines=False):
    if rows:
        xs = Reference(sh, min_col=ct[0], max_col=ct[1], min_row=r0, max_row=r0)
        ys = Reference(sh, min_col=cx[0], max_col=cx[1], min_row=r0, max_row=r0)
    else:
        xs = Reference(sh, min_col=ct, max_col=ct, min_row=r0, max_row=r1)
        ys = Reference(sh, min_col=cx, max_col=cx, min_row=r0, max_row=r1)
    se = Series(ys, xs)
    if name_ref:
        se.tx = SeriesLabel(strRef=StrRef(f=name_ref))
    elif name:
        se.tx = SeriesLabel(v=name)
    se.smooth = False
    gp = GraphicalProperties()
    if nolines:
        gp.line = LineProperties(noFill=True)
    else:
        gp.line = LineProperties(solidFill=color, w=int(width * 12700))
        if dash:
            gp.line.prstDash = dash
    se.spPr = gp
    if marker:
        se.marker = Marker(symbol=marker, size=msize)
        se.marker.graphicalProperties = GraphicalProperties(solidFill=color)
        se.marker.graphicalProperties.line = LineProperties(solidFill=color)
    else:
        se.marker = Marker(symbol="none")
    if label_idx is not None:
        dl = DataLabel(idx=label_idx, showSerName=True, showVal=False, showCatName=False, showLegendKey=False,
                       showPercent=False, showBubbleSize=False, dLblPos=label_pos, txPr=rich(label_sz, label_color or color))
        se.dLbls = DataLabelList(dLbl=[dl], showSerName=False, showVal=False, showCatName=False, showLegendKey=False,
                                 showPercent=False, showBubbleSize=False)
    return se

# ===================================================================== DATI DI MOLLIER (Calcoli, righe 240+)
# Coordinata di Mollier: Y = (h - 2501·x)/1,006 = T·(1 + 1,86·x/1,006)   (x in kg/kg; con x in g/kg: T·(1+x·1,86/1006))
# A x = 0 Y coincide con T; le isoentalpiche sono rette con pendenza -2,501/1,006 °C per g/kg.


def YM(t, xg):
    return f"{t}*(1+{xg}*1.86/1006)"


M0 = 240
put(wc, f"B{M0}", "DATI DEL DIAGRAMMA DI MOLLIER – coordinata Y = (h − 2501·x)/1,006 = T·(1 + 1,86·x/1,006); ascissa x [g/kg]. "
    "Le curve sono ritagliate all'area x 0…30 g/kg, Y −10…50.", F_B, FILL_SUB)
# --- curve di umidità relativa (stessi φ e nomi del diagramma T–x)
MRH_HDR = M0 + 2
MRH_P0 = M0 + 11
MRH = []
for j, phi in enumerate(PHIS):
    cT, cX, cY = L(8 + 3 * j), L(9 + 3 * j), L(10 + 3 * j)
    old = RH_SER[j][0]
    h0 = MRH_HDR
    wc[f"{cT}{h0}"] = f"={old}{RH_HDR}"                     # nome
    wc[f"{cT}{h0 + 1}"] = f"={old}{RH_HDR + 1}"             # φ
    ph = f"{cT}${h0 + 1}"

    def xg_of(t, ph=ph):
        ps = PS(t)
        return f"(1000*0.621945*{ph}*{ps}/({PL}-{ph}*{ps}))"
    wc[f"{cX}{h0 + 1}"] = "φ"
    wc[f"{cT}{h0 + 2}"] = f"=-10/(1+{xg_of('(-10)')}*1.86/1006)"      # T iniziale (Y = -10)
    wc[f"{cX}{h0 + 2}"] = "T inizio"
    wc[f"{cT}{h0 + 3}"] = 50
    for it in range(3):                                                # punto fisso per Y = 50
        prev = f"{cT}{h0 + 3 + it}"
        wc[f"{cT}{h0 + 4 + it}"] = f"=IFERROR(50/(1+{xg_of(prev)}*1.86/1006),{prev})"
    wc[f"{cT}{h0 + 7}"] = f"=MIN({old}{RH_HDR + 7},{cT}{h0 + 6})"     # T finale
    wc[f"{cX}{h0 + 7}"] = "T fine"
    wc[f"{cT}{MRH_P0 - 1}"] = "T"
    wc[f"{cX}{MRH_P0 - 1}"] = "x [g/kg]"
    wc[f"{cY}{MRH_P0 - 1}"] = "Y Mollier"
    for i in range(NPT):
        rr = MRH_P0 + i
        wc[f"{cT}{rr}"] = f"={cT}${h0 + 2}+({cT}${h0 + 7}-{cT}${h0 + 2})*{i}/{NPT - 1}"
        wc[f"{cX}{rr}"] = "=" + xg_of(f"{cT}{rr}")
        wc[f"{cY}{rr}"] = "=" + YM(f"{cT}{rr}", f"{cX}{rr}")
    MRH.append((9 + 3 * j, 10 + 3 * j, f"'Calcoli'!${cT}${h0}", phi))
MRH_P1 = MRH_P0 + NPT - 1

# --- isoterme ogni 1 °C (una serie con interruzioni: righe vuote fra le rette)
ISO0 = 300
put(wc, f"B{ISO0 - 1}", "Isoterme ogni 1 °C (t, x, Y; riga vuota = interruzione)", F_B, FILL_GREY)


def XEND(t, tn):
    """x [g/kg] di fine isoterma: saturazione, bordo destro (30) o bordo superiore/inferiore."""
    ps = PS(t)
    lim = "30"
    if tn > 0:
        lim = f"(50/{t}-1)*1006/1.86"
    elif tn < 0:
        lim = f"(-10/{t}-1)*1006/1.86"
    return f"MAX(0,MIN(1000*0.621945*{ps}/({PL}-{ps}),30,{lim}))"


ISO_T = list(range(-9, 51))
for k, t in enumerate(ISO_T):
    r = ISO0 + 3 * k
    wc[f"B{r}"] = t
    wc[f"C{r}"] = 0
    wc[f"D{r}"] = f"={t}"
    wc[f"B{r + 1}"] = t
    wc[f"C{r + 1}"] = "=" + XEND(f"({t})", t)
    wc[f"D{r + 1}"] = "=" + YM(f"({t})", f"C{r + 1}")
ISO1 = ISO0 + 3 * len(ISO_T) - 2
# --- isoterme ogni 5 °C con etichetta
I5_0 = 486
put(wc, f"B{I5_0 - 1}", "Isoterme ogni 5 °C (nome, t, x1, x2, Y1, Y2)", F_B, FILL_GREY)
I5 = []
for k, t in enumerate(range(-5, 46, 5)):
    r = I5_0 + k
    wc[f"B{r}"] = f"{t} °C"
    wc[f"C{r}"] = t
    wc[f"D{r}"] = 0
    wc[f"E{r}"] = "=" + XEND(f"C{r}", t)
    wc[f"F{r}"] = f"=C{r}"
    wc[f"G{r}"] = "=" + YM(f"C{r}", f"E{r}")
    I5.append((r, t))
# --- isoentalpiche (stessi valori del diagramma T–x): rette
HM0 = 500
put(wc, f"B{HM0 - 1}", "Isoentalpiche (nome, h, x inizio, x fine, Y inizio, Y fine)", F_B, FILL_GREY)
HM = []
for i, hr in enumerate(H_SER):
    r = HM0 + i
    wc[f"B{r}"] = f"=H{hr}"
    wc[f"C{r}"] = f"=I{hr}"
    wc[f"D{r}"] = f"=MAX(0,(C{r}-50*1.006)/2.501)"
    xs_h = f"1000*(C{r}-1.006*K{hr})/(2501+1.86*K{hr})"
    wc[f"E{r}"] = f"=MAX(D{r},MIN(30,{xs_h},(C{r}+10*1.006)/2.501))"
    wc[f"F{r}"] = f"=(C{r}-2.501*D{r})/1.006"
    wc[f"G{r}"] = f"=(C{r}-2.501*E{r})/1.006"
    HM.append(r)
# --- volume specifico costante
VM0 = 520
put(wc, f"B{VM0 - 1}", "Isocore (nome, v, x lato saturazione, Y cand., x1..x3 punto fisso Y=50, x inizio, X1..X4, Y1..Y4)", F_B, FILL_GREY)
VM = []
for i, vr in enumerate(V_SER):
    r = VM0 + i
    wc[f"B{r}"] = f"=H{vr}"
    wc[f"C{r}"] = f"=I{vr}"
    wc[f"D{r}"] = f"=MIN(30,T{vr})"                           # x lato saturazione/alto (dal blocco T–x)
    wc[f"E{r}"] = f"=O{vr}*(1+W{vr}*1.86/1006)"              # Y dell'estremo lato x piccolo
    prev = f"W{vr}"
    for it, cc in enumerate("FGH"):
        wc[f"{cc}{r}"] = (f"=IFERROR(MAX(0,1000*(C{r}*{PK}/(0.287042*(50/(1+{prev}*1.86/1006)+273.15))-1)/1.607858),{prev})")
        prev = f"{cc}{r}"
    wc[f"I{r}"] = f"=MIN(D{r},IF(E{r}<=50,W{vr},H{r}))"
    for k in range(4):
        cX, cY = L(10 + k), L(14 + k)
        wc[f"{cX}{r}"] = f"=I{r}+(D{r}-I{r})*{k}/3"
        tt = f"(C{r}*{PK}/(0.287042*(1+1.607858*{cX}{r}/1000))-273.15)"
        wc[f"{cY}{r}"] = f"=MAX(-10,MIN(50,{tt}*(1+{cX}{r}*1.86/1006)))"
    VM.append(r)
# --- trasformazioni e punti (riuso delle celle di stato del foglio UTA: solo la coordinata Y è nuova)
PM0 = 540
put(wc, f"B{PM0 - 1}", "Trasformazioni e punti in coordinate di Mollier (x da UTA, Y = T·(1+1,86·x/1006))", F_B, FILL_GREY)
PROC = {}
for j, s in enumerate(("E", "I")):
    b = SEAS[s]
    c1, c2 = L(2 + 2 * j), L(3 + 2 * j)
    wc[f"{c1}{PM0}"] = "x " + ("estate" if s == "E" else "inverno")
    wc[f"{c2}{PM0}"] = "Y"
    for k in range(NROWS + 1):
        r = PM0 + 1 + k
        ur = b + O_R0 + k
        wc[f"{c1}{r}"] = f"=UTA!J{ur}"
        wc[f"{c2}{r}"] = "=" + YM(f"UTA!H{ur}", f"UTA!J{ur}")
    PROC[s] = (2 + 2 * j, 3 + 2 * j, PM0 + 1, PM0 + 1 + NROWS)
PTS0 = PM0 + 10
PTS = {}
for j, s in enumerate(("E", "I")):
    b = SEAS[s]
    for q in range(3):
        r = PTS0 + 3 * j + q
        wc[f"A{r}"] = ("E", "A", "I")[q] + (" est" if s == "E" else " inv")
        wc[f"B{r}"] = f"=UTA!J{b + 2 + q}"
        wc[f"C{r}"] = "=" + YM(f"UTA!H{b + 2 + q}", f"UTA!J{b + 2 + q}")
        PTS[(s, q)] = r
# retta ambiente: da A verso I, prolungata ×2 (lineare in coordinate di Mollier) e ritagliata
RAM = PTS0 + 8
wc[f"A{RAM - 1}"] = "Retta ambiente Mollier (x, Y) – riga 1 = A, riga 2 = estremo; riga 3 = fattore k"
RAMC = {}
for j, s in enumerate(("E", "I")):
    cX, cY = L(2 + 2 * j), L(3 + 2 * j)
    ra, ri = PTS[(s, 1)], PTS[(s, 2)]
    XA, YA, XI, YI = f"B{ra}", f"C{ra}", f"B{ri}", f"C{ri}"
    dX, dY = f"({XI}-{XA})", f"({YI}-{YA})"
    kx = f"IF({dX}>0,(30-{XA})/{dX},IF({dX}<0,-{XA}/{dX},2))"
    ky = f"IF({dY}>0,(50-{YA})/{dY},IF({dY}<0,(-10-{YA})/{dY},2))"
    wc[f"{cX}{RAM + 2}"] = f"=MAX(0,MIN(2,{kx},{ky}))"
    wc[f"{cX}{RAM}"] = f"={XA}"
    wc[f"{cY}{RAM}"] = f"={YA}"
    wc[f"{cX}{RAM + 1}"] = f"={XA}+{cX}{RAM + 2}*{dX}"
    wc[f"{cY}{RAM + 1}"] = f"={YA}+{cX}{RAM + 2}*{dY}"
    RAMC[s] = (2 + 2 * j, 3 + 2 * j)
# --- scala di bordo Δh/Δx (polo sull'asse x = 0, Y = YP)
ES0 = 580
YP = 20
put(wc, f"B{ES0 - 1}", "Scala di bordo Δh/Δx [kJ/kg] – polo (x = 0; Y = cella C580); per ogni valore: s = (q − 2501)/1,006/1000 °C per g/kg",
    F_B, FILL_GREY)
wc[f"B{ES0}"] = "Y del polo"
wc[f"C{ES0}"] = YP
POLE = f"$C${ES0}"
for j, t in enumerate(["nome", "q [kJ/kg]", "pendenza s", "x bordo", "Y bordo", "lungh. vis.", "δ", "X1", "X2", "Y1", "Y2"]):
    put(wc, f"{L(2 + j)}{ES0 + 1}", t, F_B, FILL_GREY, align=CENTER)
QT = [-20000, -5000, -2000, 0, 1000, 2000, 2501, 3000, 4000, 5000, 10000, 20000]
TK = []


def edge_cells(r, s_formula):
    wc[f"D{r}"] = s_formula
    wc[f"E{r}"] = (f"=IF(AND({POLE}+30*D{r}<=50,{POLE}+30*D{r}>=-10),30,IF(D{r}>0,(50-{POLE})/D{r},(-10-{POLE})/D{r}))")
    wc[f"F{r}"] = f"={POLE}+D{r}*E{r}"
    wc[f"G{r}"] = f"=MAX(0.000001,E{r}*SQRT((1.7/30)^2+(D{r}/60)^2))"


for i, q in enumerate(QT):
    r = ES0 + 2 + i
    wc[f"B{r}"] = f"{q}".replace("-", "−")
    wc[f"C{r}"] = q
    edge_cells(r, f"=(C{r}-2501)/1006")
    wc[f"H{r}"] = f"=MIN(1,0.035/G{r})"
    wc[f"I{r}"] = f"=E{r}*(1-H{r})"
    wc[f"J{r}"] = f"=E{r}"
    wc[f"K{r}"] = f"={POLE}+D{r}*I{r}"
    wc[f"L{r}"] = f"=F{r}"
    sv = (q - 2501) / 1006
    yr = YP + 30 * sv
    pos = "l" if -10 <= yr <= 50 else ("b" if sv > 0 else "t")
    TK.append((r, pos))
RAY0 = ES0 + 2 + len(QT) + 1
RAYS = {}
for j, s in enumerate(("E", "I")):
    r = RAY0 + j
    a, i_ = se_row(s, "A"), se_row(s, "I")
    dh = f"({SEC['h']}{i_}-{SEC['h']}{a})"
    dx = f"({SEC['xg']}{i_}-{SEC['xg']}{a})"
    wc[f"C{r}"] = f"=IF(ABS({dx})<0.000001,0,1000*{dh}/{dx})"
    wc[f"B{r}"] = (f"=\"Δh/Δx {'estate' if s == 'E' else 'inverno'} = \"&IF(ABS({dx})<0.000001,\"∞\",FIXED(C{r},0,TRUE))"
                   f"&\" kJ/kg (R = \"&FIXED({sc(s, 'R', False)},2,TRUE)&\")\"")
    edge_cells(r, f"=IF(ABS({dx})<0.000001,IF({dh}>=0,1000000,-1000000),(C{r}-2501)/1006)")
    wc[f"I{r}"] = 0
    wc[f"J{r}"] = f"=E{r}"
    wc[f"K{r}"] = f"={POLE}"
    wc[f"L{r}"] = f"=F{r}"
    RAYS[s] = r
POLE_R = RAY0 + 3
wc[f"B{POLE_R}"] = "polo Δh/Δx [kJ/kg]"
wc[f"C{POLE_R}"] = 0
wc[f"D{POLE_R}"] = f"={POLE}"

# ===================================================================== GRAFICI
COL_E = "0070C0"     # ESTATE = blu (spezzata), INVERNO = rosso
COL_I = "C00000"
W_PROC = 2.75


def rich(sz=700, color="404040", b=False):
    cp = CharacterProperties(sz=sz, b=b, solidFill=color, latin=DFont(typeface="Arial"))
    return RichText(p=[Paragraph(pPr=ParagraphProperties(defRPr=cp), endParaRPr=cp)])


def make_series(sh, ct, cx, r0, r1, name=None, name_ref=None, color="000000", width=0.75, dash=None,
                marker=None, msize=5, label_idx=None, label_pos="r", label_color=None, label_sz=700, rows=False,
                nolines=False):
    if rows:
        xs = Reference(sh, min_col=ct[0], max_col=ct[1], min_row=r0, max_row=r0)
        ys = Reference(sh, min_col=cx[0], max_col=cx[1], min_row=r0, max_row=r0)
    else:
        xs = Reference(sh, min_col=ct, max_col=ct, min_row=r0, max_row=r1)
        ys = Reference(sh, min_col=cx, max_col=cx, min_row=r0, max_row=r1)
    se = Series(ys, xs)
    if name_ref:
        se.tx = SeriesLabel(strRef=StrRef(f=name_ref))
    elif name:
        se.tx = SeriesLabel(v=name)
    se.smooth = False
    gp = GraphicalProperties()
    if nolines:
        gp.line = LineProperties(noFill=True)
    else:
        gp.line = LineProperties(solidFill=color, w=int(width * 12700))
        if dash:
            gp.line.prstDash = dash
    se.spPr = gp
    if marker:
        se.marker = Marker(symbol=marker, size=msize)
        se.marker.graphicalProperties = GraphicalProperties(solidFill=color)
        se.marker.graphicalProperties.line = LineProperties(solidFill=color)
    else:
        se.marker = Marker(symbol="none")
    if label_idx is not None:
        dl = DataLabel(idx=label_idx, showSerName=True, showVal=False, showCatName=False, showLegendKey=False,
                       showPercent=False, showBubbleSize=False, dLblPos=label_pos, txPr=rich(label_sz, label_color or color))
        se.dLbls = DataLabelList(dLbl=[dl], showSerName=False, showVal=False, showCatName=False, showLegendKey=False,
                                 showPercent=False, showBubbleSize=False)
    return se


def grid(ax, major=True, minor=True):
    if major:
        ax.majorGridlines = ChartLines(spPr=GraphicalProperties(ln=LineProperties(solidFill="BFBFBF", w=6350)))
    else:
        ax.majorGridlines = None
    if minor:
        ax.minorGridlines = ChartLines(spPr=GraphicalProperties(ln=LineProperties(solidFill="E7E6E6", w=3175)))


def add_process_series(S, xy_proc, xy_pts, labels=True):
    """Spezzate delle sequenze e punti E/A/I (stessi colori e simboli nei due diagrammi)."""
    for s in ("E", "I"):
        col = COL_E if s == "E" else COL_I
        S.append(xy_proc(s, col))
    for s in ("E", "I"):
        col = COL_E if s == "E" else COL_I
        for j, (nm, mk) in enumerate((("E", "diamond"), ("A", "square"), ("I", "triangle"))):
            S.append(xy_pts(s, j, nm + (" est" if s == "E" else " inv"), col, mk,
                            {0: "r", 1: "t", 2: "b"}[j]))


def base_chart(width_cm, height_cm):
    ch = ScatterChart()
    ch.scatterStyle = "lineMarker"
    ch.roundedCorners = False
    ch.legend = None
    ch.width = width_cm
    ch.height = height_cm
    ch.display_blanks = "gap"
    return ch


def build_chart(width_cm, height_cm, labels=True):
    ch = base_chart(width_cm, height_cm)
    S = ch.series
    lab = (lambda i: i) if labels else (lambda i: None)
    for j, (ct, cx, nref) in enumerate(RH_SER):
        ci, xi = 8 + 2 * j, 9 + 2 * j
        sat = j == 0
        S.append(make_series(wc, ci, xi, RH_PTS0, RH_PTS1, name_ref=f"'Calcoli'!${ct}${RH_HDR}",
                             color="000000" if sat else "7F7F7F", width=2.25 if sat else 0.75,
                             label_idx=lab(NPT - 1), label_pos="t" if j < 7 else "l", label_color="404040"))
    for r in H_SER:
        S.append(make_series(wc, (15, 19), (20, 24), r, r, name_ref=f"'Calcoli'!$H${r}", color="2E75B6", width=0.6,
                             label_idx=lab(0), label_pos="l", label_color="2E75B6", label_sz=650, rows=True))
    for r in V_SER:
        S.append(make_series(wc, (16, 19), (20, 23), r, r, name_ref=f"'Calcoli'!$H${r}", color="548235", width=0.6,
                             dash="dash", label_idx=lab(1), label_pos="r", label_color="548235", label_sz=650, rows=True))
    S.append(make_series(wc, 8, 9, ARC0, ARC0 + 18, name="goniometro", color="404040", width=0.75))
    for j, (ct, cx, nref) in enumerate(TICK_SER):
        S.append(make_series(wc, 11 + 2 * j, 12 + 2 * j, ARC0, ARC0 + 1, name_ref=f"'Calcoli'!${ct}${ARC0 - 2}",
                             color="404040", width=1.0, label_idx=lab(1), label_pos="l" if j < 3 else "b", label_color="404040",
                             label_sz=650))
    for j, (ct, cx) in enumerate(RL):
        S.append(make_series(wc, 24 + 2 * j, 25 + 2 * j, ARC0, ARC0 + 1, name="R " + ("estate" if j == 0 else "inverno"),
                             color=COL_E if j == 0 else COL_I, width=2.0))
    for j, s in enumerate(("E", "I")):
        S.append(make_series(wc, 8 + 2 * j, 9 + 2 * j, RA0 + 1, RA0 + 2, name="retta ambiente",
                             color=COL_E if s == "E" else COL_I, width=1.25, dash="sysDash"))
    add_process_series(
        S,
        lambda s, col: make_series(ws, 8, 10, SEAS[s] + O_R0, SEAS[s] + O_R0 + NROWS, name="Estate" if s == "E" else "Inverno",
                                   color=col, width=W_PROC, marker="circle", msize=6),
        lambda s, j, nm, col, mk, pos: make_series(ws, 8, 10, SEAS[s] + 2 + j, SEAS[s] + 2 + j, name=nm, color=col, marker=mk,
                                                   msize=8, label_idx=0, label_pos=pos, label_color=col, label_sz=800,
                                                   nolines=True))
    ch.x_axis.scaling.min = -10
    ch.x_axis.scaling.max = 50
    ch.x_axis.majorUnit = 5
    ch.x_axis.minorUnit = 1
    ch.y_axis.scaling.min = 0
    ch.y_axis.scaling.max = 30
    ch.y_axis.majorUnit = 2
    ch.y_axis.minorUnit = 1
    ch.x_axis.title = "Temperatura a bulbo secco T [°C]"
    ch.y_axis.title = "Umidità specifica x [g/kg aria secca]"
    ch.x_axis.number_format = "0"
    ch.y_axis.number_format = "0"
    ch.x_axis.delete = False
    ch.y_axis.delete = False
    ch.y_axis.crosses = "max"
    grid(ch.x_axis)
    grid(ch.y_axis)
    ch.x_axis.txPr = rich(800, "000000")
    ch.y_axis.txPr = rich(800, "000000")
    for ax in (ch.x_axis, ch.y_axis):
        ax.title.overlay = False
    return ch


def build_mollier(width_cm, height_cm):
    ch = base_chart(width_cm, height_cm)
    S = ch.series
    # isoterme 1 °C (serie unica con interruzioni) e 5 °C etichettate
    S.append(make_series(wc, 3, 4, ISO0, ISO1, name="isoterme 1 °C", color="C9C9C9", width=0.4))
    for r, t in I5:
        S.append(make_series(wc, (4, 5), (6, 7), r, r, name_ref=f"'Calcoli'!$B${r}", color="7F7F7F", width=0.75,
                             label_idx=1, label_pos="r" if t <= 30 else "l", label_color="595959", label_sz=650, rows=True))
    # UR
    for j, (cx, cy, nref, phi) in enumerate(MRH):
        sat = j == 0
        S.append(make_series(wc, cx, cy, MRH_P0, MRH_P1, name_ref=nref, color="000000" if sat else "7F7F7F",
                             width=2.25 if sat else 0.75, label_idx=NPT - 1 if phi < 0.5 else 30 + int(phi * 10) - 5,
                             label_pos="b" if phi < 0.5 else "r",
                             label_color="404040"))
    # entalpia
    for r in HM:
        S.append(make_series(wc, (4, 5), (6, 7), r, r, name_ref=f"'Calcoli'!$B${r}", color="2E75B6", width=0.6,
                             label_idx=1, label_pos="b", label_color="2E75B6", label_sz=650, rows=True))
    # volume specifico
    for r in VM:
        S.append(make_series(wc, (10, 13), (14, 17), r, r, name_ref=f"'Calcoli'!$B${r}", color="548235", width=0.6,
                             dash="dash", label_idx=1, label_pos="r", label_color="548235", label_sz=650, rows=True))
    # scala di bordo Δh/Δx
    for r, pos in TK:
        S.append(make_series(wc, (9, 10), (11, 12), r, r, name_ref=f"'Calcoli'!$B${r}", color="404040", width=1.25,
                             label_idx=1, label_pos=pos, label_color="404040", label_sz=650, rows=True))
    for s in ("E", "I"):
        r = RAYS[s]
        S.append(make_series(wc, (9, 10), (11, 12), r, r, name_ref=f"'Calcoli'!$B${r}", color=COL_E if s == "E" else COL_I,
                             width=1.5, dash="dash", label_idx=1, label_pos="r" if s == "E" else "t",
                             label_color=COL_E if s == "E" else COL_I, label_sz=700, rows=True))
    S.append(make_series(wc, 3, 4, POLE_R, POLE_R, name_ref=f"'Calcoli'!$B${POLE_R}", color="404040", marker="circle",
                         msize=6, label_idx=0, label_pos="t", label_color="404040", label_sz=650, nolines=True))
    # rette ambiente
    for s in ("E", "I"):
        cx, cy = RAMC[s]
        S.append(make_series(wc, cx, cy, RAM, RAM + 1, name="retta ambiente", color=COL_E if s == "E" else COL_I,
                             width=1.25, dash="sysDash"))
    add_process_series(
        S,
        lambda s, col: make_series(wc, PROC[s][0], PROC[s][1], PROC[s][2], PROC[s][3],
                                   name="Estate" if s == "E" else "Inverno", color=col, width=W_PROC, marker="circle", msize=6),
        lambda s, j, nm, col, mk, pos: make_series(wc, 2, 3, PTS[(s, j)], PTS[(s, j)], name=nm, color=col, marker=mk,
                                                   msize=8, label_idx=0, label_pos=pos, label_color=col, label_sz=800,
                                                   nolines=True))
    ch.x_axis.scaling.min = 0
    ch.x_axis.scaling.max = 30
    ch.x_axis.majorUnit = 2
    ch.x_axis.minorUnit = 1
    ch.y_axis.scaling.min = -10
    ch.y_axis.scaling.max = 50
    ch.y_axis.majorUnit = 5
    ch.y_axis.minorUnit = 1
    ch.x_axis.title = "Umidità specifica x [g/kg aria secca]"
    ch.y_axis.title = "Temperatura [°C] (coordinata di Mollier)"
    ch.x_axis.number_format = "0"
    ch.y_axis.number_format = "0"
    ch.x_axis.delete = False
    ch.y_axis.delete = False
    ch.x_axis.crosses = "min"
    grid(ch.x_axis, major=True, minor=False)
    ch.y_axis.majorGridlines = None
    ch.x_axis.txPr = rich(800, "000000")
    ch.y_axis.txPr = rich(800, "000000")
    for ax in (ch.x_axis, ch.y_axis):
        ax.title.overlay = False
    return ch


# --------------------------------------------------------------- famiglie di curve e goniometro dell'originale
# Ricostruzione, con le costanti e la pressione di questo foglio, del foglio «calc» di psicro_finale.xls:
# asse delle entalpie (retta x = 20/30·T + 10 e parallela +4), isoentalpiche in kcal/kg (continue, fino
# all'asse + 2), isoentalpiche in kJ/kg (tratteggiate, nella fascia tra le due rette d'asse), isocore
# 0,78…0,95 m³/kg (fino a saturazione + 2), goniometro a due semicerchi centrati in (0; 30):
# raggio 7 = fattore termico R (rombi), raggio 9 = rapporto Δh/Δx in kJ/g (quadrati).
OG = wc.max_row + 3
put(wc, f"B{OG}", "Diagramma T–x nello stile dell'originale (psicro_finale.xls): famiglie di curve", F_B, FILL_GREY)
OG_T0 = OG + 3                     # prima riga dei dati (T = −10 °C)
OG_NT = 61                         # T = −10…50 °C
OG_T1 = OG_T0 + OG_NT - 1
KCAL = list(range(0, 31))
VOLS = [round(0.95 - 0.01 * i, 2) for i in range(18)]
KJ = list(range(10, 100, 5))
wc[f"C{OG + 1}"] = "T [°C]"
wc[f"D{OG + 1}"] = "x sat"
wc[f"E{OG + 1}"] = "asse h"
wc[f"F{OG + 1}"] = "asse h2"
OG_KC = {h: L(7 + i) for i, h in enumerate(KCAL)}
OG_VO = {v: L(7 + len(KCAL) + i) for i, v in enumerate(VOLS)}
OG_KJ = {h: L(7 + len(KCAL) + len(VOLS) + i) for i, h in enumerate(KJ)}
for h, c in OG_KC.items():
    wc[f"{c}{OG + 1}"] = f"h {h} kcal"
    wc[f"{c}{OG + 2}"] = h
for v, c in OG_VO.items():
    wc[f"{c}{OG + 1}"] = f"v {str(v).replace('.', ',')}"
    wc[f"{c}{OG + 2}"] = v
for h, c in OG_KJ.items():
    wc[f"{c}{OG + 1}"] = f"h {h} kJ"
    wc[f"{c}{OG + 2}"] = h
for i in range(OG_NT):
    r = OG_T0 + i
    t = f"$C{r}"
    wc[f"C{r}"] = -10 + i
    ps = PS(t)
    wc[f"D{r}"] = f"=1000*0.621945*{ps}/({PL}-{ps})"
    wc[f"E{r}"] = f"=20/30*{t}+10"
    wc[f"F{r}"] = f"=E{r}+4"
    for h, c in OG_KC.items():
        xv = f"({c}${OG + 2}*4.1868-1.006*{t})/(2501+1.86*{t})*1000"
        wc[f"{c}{r}"] = f"=MIN({xv},2+$E{r})"
    for v, c in OG_VO.items():
        xv = f"1000*0.621945*({c}${OG + 2}*{PL}/(287.055*(273.15+{t}))-1)"
        wc[f"{c}{r}"] = f"=MIN({xv},2+$D{r})"
    for h, c in OG_KJ.items():
        xv = f"({c}${OG + 2}-1.006*{t})/(2501+1.86*{t})*1000"
        wc[f"{c}{r}"] = f"=MIN(MAX({xv},$E{r}),2+$F{r})"

# goniometro
OGG = OG_T1 + 3
put(wc, f"B{OGG}", "Goniometro dell'originale: centro (0; 30), raggio 7 = R, raggio 9 = Δh/Δx [kJ/g]", F_B, FILL_GREY)
wc[f"C{OGG + 1}"] = "R"
wc[f"D{OGG + 1}"] = "dx/dT"
wc[f"E{OGG + 1}"] = "T"
wc[f"F{OGG + 1}"] = "x"
wc[f"H{OGG + 1}"] = "Δh/Δx [kJ/g]"
wc[f"I{OGG + 1}"] = "dx/dT"
wc[f"J{OGG + 1}"] = "T"
wc[f"K{OGG + 1}"] = "x"
wc[f"M{OGG + 1}"] = "arco 7: T"
wc[f"N{OGG + 1}"] = "arco 7: x"
wc[f"O{OGG + 1}"] = "arco 9: T"
wc[f"P{OGG + 1}"] = "arco 9: x"
GR = [1, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0, -0.1, -0.2, -0.5, -0.8, -1, -2, -5, -1000,
      1000, 5, 4, 3, 2, 1.8, 1.5, 1.2]
GP = [100, 20, 10, 9, 8, 7, 6, 5, 4.5, 4, 3.8, 3.6, 3.4, 3.2, 3, 2.9, 2.8, 2.7, "=0.624*4.1868", 2.5, 2.4, 2.3,
      2.2, 2.1, 2, 1.8, 1.6, 1.4, 1.2, 1, 0.8, 0.6, 0.4, 0.2, 0.0001, -1, -2, -5, -10]
G0 = OGG + 2
for i, R_ in enumerate(GR):
    r = G0 + i
    wc[f"C{r}"] = R_
    if R_ == 0:
        wc[f"E{r}"] = 0
        wc[f"F{r}"] = 23
        continue
    wc[f"D{r}"] = f"=1.006*(1/C{r}-1)/2501*1000"
    wc[f"F{r}"] = f"=-ABS(D{r})*7/SQRT(1+D{r}^2)+30"
    wc[f"E{r}"] = f"=IF(D{r}=0,-7,(F{r}-30)/D{r})"
for i, E_ in enumerate(GP):
    r = G0 + i
    wc[f"H{r}"] = E_
    wc[f"I{r}"] = f"=1.006/(H{r}-2.501)"
    wc[f"K{r}"] = f"=-ABS(I{r})*9/SQRT(1+I{r}^2)+30"
    wc[f"J{r}"] = f"=(K{r}-30)/I{r}"
r = G0 + len(GP)                   # chiusura a destra (Δh/Δx → ∞)
wc[f"H{r}"] = "∞"
wc[f"J{r}"] = 9
wc[f"K{r}"] = 30
G_P1 = r
for i in range(37):                # semicerchi disegnati a passi di 5°
    r = G0 + i
    wc[f"M{r}"] = f"=7*COS(RADIANS({180 + 5 * i}))"
    wc[f"N{r}"] = f"=30+7*SIN(RADIANS({180 + 5 * i}))"
    wc[f"O{r}"] = f"=9*COS(RADIANS({180 + 5 * i}))"
    wc[f"P{r}"] = f"=30+9*SIN(RADIANS({180 + 5 * i}))"
GC = G0 + 40                       # centro ⊗ e rette ambiente di progetto (raggio 7)
wc[f"C{GC}"] = "⊗"
wc[f"E{GC}"] = 0
wc[f"F{GC}"] = 30
wc[f"C{GC + 1}"] = "∞"
wc[f"E{GC + 1}"] = 9
wc[f"F{GC + 1}"] = 30
OG_RL = {}
for j, s_ in enumerate(("E", "I")):
    rr = GC + 3 + 3 * j
    a, i_ = se_row(s_, "A"), se_row(s_, "I")
    wc[f"C{rr}"] = "R estate (raggio 7)" if s_ == "E" else "R inverno (raggio 7)"
    wc[f"E{rr}"] = 0
    wc[f"F{rr}"] = 30
    dT = f"({SEC['t']}{i_}-{SEC['t']}{a})"
    dX = f"({SEC['xg']}{i_}-{SEC['xg']}{a})"
    wc[f"D{rr + 1}"] = f"=IF(ABS({dT})<0.000001,1E+9*IF({dX}<0,1,-1),{dX}/{dT})"
    wc[f"F{rr + 1}"] = f"=-ABS(D{rr + 1})*7/SQRT(1+D{rr + 1}^2)+30"
    wc[f"E{rr + 1}"] = f"=IF(D{rr + 1}=0,-7,(F{rr + 1}-30)/D{rr + 1})"
    OG_RL[s_] = rr


def build_chart_orig(width_cm, height_cm):
    """Diagramma T–x del foglio «psicro» con le famiglie di curve e il goniometro di psicro_finale.xls."""
    from openpyxl.utils import column_index_from_string as CI
    ch = base_chart(width_cm, height_cm)
    S = ch.series
    for j, (ct, cx, nref) in enumerate(RH_SER):
        S.append(make_series(wc, 8 + 2 * j, 9 + 2 * j, RH_PTS0, RH_PTS1, name_ref=f"'Calcoli'!${ct}${RH_HDR}",
                             color="000000", width=2.25 if j == 0 else 0.75))
    for c, nm in (("E", "asse h"), ("F", "asse h2")):
        S.append(make_series(wc, 3, CI(c), OG_T0, OG_T1, name=nm, color="000000", width=1))
    for h, c in OG_KC.items():
        S.append(make_series(wc, 3, CI(c), OG_T0, OG_T1, name_ref=f"'Calcoli'!${c}${OG + 1}", color="000000", width=1))
    for k, (v, c) in enumerate(OG_VO.items()):
        S.append(make_series(wc, 3, CI(c), OG_T0, OG_T1, name_ref=f"'Calcoli'!${c}${OG + 1}", color="000000", width=1,
                             dash=None if k == 0 else "dash"))
    for h, c in OG_KJ.items():
        S.append(make_series(wc, 3, CI(c), OG_T0, OG_T1, name_ref=f"'Calcoli'!${c}${OG + 1}", color="000000", width=1,
                             dash="dash"))
    # goniometro
    S.append(make_series(wc, 13, 14, G0, G0 + 36, name="goniometro R", color="000000", width=1))
    S.append(make_series(wc, 15, 16, G0, G0 + 36, name="goniometro Δh/Δx", color="000000", width=1))
    S.append(make_series(wc, 5, 6, G0, G0 + len(GR) - 1, name="R", color="000000", marker="diamond", msize=5,
                         nolines=True))
    S.append(make_series(wc, 10, 11, G0, G_P1, name="Δh/Δx", color="000000", marker="square", msize=4,
                         nolines=True))
    S.append(make_series(wc, 5, 6, GC + 1, GC + 1, name_ref=f"'Calcoli'!$C${GC + 1}", color="404040", nolines=True,
                         marker="none", label_idx=0, label_pos="r", label_sz=1400))
    inf_se, inf_dl = S[-1], S[-1].dLbls
    for s_ in ("E", "I"):
        rr = OG_RL[s_]
        S.append(make_series(wc, 5, 6, rr, rr + 1, name="R " + ("estate" if s_ == "E" else "inverno"),
                             color=COL_E if s_ == "E" else COL_I, width=3, marker="diamond", msize=7))
    for j, s_ in enumerate(("E", "I")):
        S.append(make_series(wc, 8 + 2 * j, 9 + 2 * j, RA0 + 1, RA0 + 2, name="retta ambiente",
                             color=COL_E if s_ == "E" else COL_I, width=1.25, dash="sysDash"))
    add_process_series(
        S,
        lambda s_, col: make_series(ws, 8, 10, SEAS[s_] + O_R0, SEAS[s_] + O_R0 + NROWS,
                                    name="Estate" if s_ == "E" else "Inverno", color=col, width=W_PROC,
                                    marker="circle", msize=6),
        lambda s_, j, nm, col, mk, pos: make_series(ws, 8, 10, SEAS[s_] + 2 + j, SEAS[s_] + 2 + j, name=nm, color=col,
                                                    marker=mk, msize=8, label_idx=0, label_pos=pos, label_color=col,
                                                    label_sz=800, nolines=True))
    # centro ⊗ (simbolo come etichetta, uguale in Excel e LibreOffice)
    S.append(make_series(wc, 5, 6, GC, GC, name_ref=f"'Calcoli'!$C${GC}", color="404040", nolines=True,
                         marker="none", label_idx=0, label_pos="ctr", label_sz=2000))
    cen_se, cen_dl = S[-1], S[-1].dLbls
    ch.x_axis.scaling.min, ch.x_axis.scaling.max = -10, 50
    ch.y_axis.scaling.min, ch.y_axis.scaling.max = 0, 30
    ch.x_axis.delete = ch.y_axis.delete = False
    stile_originale(ch)
    inf_se.dLbls = inf_dl
    for d in inf_dl.dLbl:
        d.txPr = rich(1400, "000000")
    cen_se.dLbls = cen_dl
    for d in cen_dl.dLbl:
        d.txPr = rich(2000, "000000")
    return ch


# --------------------------------------------------------------- stile originale (psicro_finale.xls)
# I fogli «psicro» e «Mollier» riprendono la grafica del diagramma originale dell'autore:
# fondo bianco con bordo nero, griglia nera (principale continua, secondaria tratteggiata, passo 1),
# curve di riferimento nere (saturazione 3 pt, le altre 1 pt; volume specifico tratteggiato),
# nessun titolo degli assi, etichette dell'asse verticale a destra, Arial 10, ESTATE rossa e INVERNO blu
# spessi 3 pt. La copia ridotta nel foglio UTA mantiene lo stile a colori.
from openpyxl.chart.layout import Layout, ManualLayout

OR_E, OR_I = "FF0000", "0000FF"      # colori dell'originale: estate rossa (ser a), inverno blu (ser b)
_MAP_PROC = {COL_E: OR_E, COL_I: OR_I}


def _rgb(fill):
    c = getattr(fill, "srgbClr", None) if fill is not None else None
    c = getattr(c, "val", c)
    return str(c).upper()[-6:] if c is not None else None


def _col(se):
    ln = se.spPr.line if se.spPr is not None else None
    return _rgb(ln.solidFill) if ln is not None else None


def _mk_col(se):
    gp = se.marker.graphicalProperties if se.marker is not None else None
    return _rgb(gp.solidFill) if gp is not None else None


def stile_originale(ch, etichette_curve=False):
    """Ristila un grafico costruito da build_chart/build_mollier nello stile di psicro_finale.xls."""
    for se in ch.series:
        col = _col(se) or _mk_col(se)
        ln = se.spPr.line
        proc = col in _MAP_PROC
        if proc:
            nc = _MAP_PROC[col]
            if ln is not None and not ln.noFill:
                ln.solidFill = nc
                if ln.prstDash is None:
                    ln.w = 38100                  # 3 pt come «ser a» / «ser b»
            if se.marker is not None and se.marker.symbol != "none":
                se.marker.graphicalProperties = GraphicalProperties(solidFill=nc)
                se.marker.graphicalProperties.line = LineProperties(solidFill=nc)
                se.marker.size = 7 if se.marker.size and se.marker.size > 6 else 5
            if se.dLbls is not None:
                for d in se.dLbls.dLbl:
                    d.txPr = rich(1000, nc)
            se.smooth = False                     # trasformazioni rettilinee (punti calcolati)
            continue
        # curve di riferimento: nere
        w0 = ln.w or 9525
        if not ln.noFill:
            ln.solidFill = "000000"
            if col == "000000" and w0 >= 25000:
                ln.w = 38100                      # saturazione 3 pt
            elif col == "C9C9C9":
                ln.noFill = True                  # isoterme ogni 1 °C (Mollier): la griglia secondaria basta
                ln.solidFill = None
            else:
                ln.w = 12700                      # 1 pt
                if ln.prstDash not in (None, "solid"):
                    ln.prstDash = "lgDash"
        if se.marker is not None and se.marker.symbol not in (None, "none"):
            se.marker.graphicalProperties = GraphicalProperties(solidFill="000000")
            se.marker.graphicalProperties.line = LineProperties(solidFill="000000")
        # niente smussatura: le curve hanno già abbastanza punti, e LibreOffice smussa tutto il grafico
        # se anche una sola serie è smussata (le trasformazioni devono restare rettilinee)
        se.smooth = False
        if se.dLbls is not None:
            if etichette_curve or col == "404040":
                for d in se.dLbls.dLbl:
                    d.txPr = rich(800, "000000")
            else:
                se.dLbls = None
    # assi: niente titoli, griglia nera, Arial 10, etichette verticali a destra
    for ax in (ch.x_axis, ch.y_axis):
        ax.title = None
        ax.number_format = "General"
        ax.majorGridlines = ChartLines(spPr=GraphicalProperties(ln=LineProperties(solidFill="000000", w=3175)))
        ax.minorGridlines = ChartLines(spPr=GraphicalProperties(ln=LineProperties(solidFill="000000", w=3175,
                                                                                    prstDash="dash")))
        ax.minorUnit = 1
        ax.majorUnit = 5
        ax.txPr = rich(1000, "000000")
        ax.spPr = GraphicalProperties(ln=LineProperties(solidFill="000000", w=3175))
    ch.x_axis.majorTickMark = ch.x_axis.minorTickMark = "out"
    ch.y_axis.majorTickMark = ch.y_axis.minorTickMark = "in"
    ch.x_axis.crosses = "min"
    ch.y_axis.crosses = "max"
    ch.y_axis.tickLblPos = "high"
    ch.x_axis.tickLblPos = "nextTo"
    ch.plot_area.layout = Layout(manualLayout=ManualLayout(xMode="edge", yMode="edge",
                                                           x=0.0071, y=0.0272, w=0.9902, h=0.9723))
    ch.plot_area.spPr = GraphicalProperties(solidFill="FFFFFF", ln=LineProperties(solidFill="000000", w=12700))
    ch.graphical_properties = GraphicalProperties(noFill=True, ln=LineProperties(noFill=True))
    return ch


# --------------------------------------------------------------- impostazioni di stampa
from openpyxl.worksheet.page import PageMargins
from openpyxl.worksheet.pagebreak import Break, RowBreak


def print_setup(w, area, orientation, fit=None, scale=None, row_breaks=(), title_rows=None, paper=9):
    w.print_area = area
    w.page_setup.orientation = orientation
    w.page_setup.paperSize = paper                  # 9 = A4, 8 = A3
    w.page_margins = PageMargins(left=0.5, right=0.5, top=0.75, bottom=0.75, header=0.3, footer=0.3)
    if fit:
        w.sheet_properties.pageSetUpPr.fitToPage = True
        w.page_setup.fitToWidth, w.page_setup.fitToHeight = fit
    else:
        w.sheet_properties.pageSetUpPr.fitToPage = False
        w.page_setup.scale = scale
    if row_breaks:
        w.row_breaks = RowBreak()
        for rb in row_breaks:
            w.row_breaks.append(Break(id=rb))
    if title_rows:
        w.print_title_rows = title_rows
    w.print_options.horizontalCentered = True
    for hf in (w.oddHeader,):
        hf.left.text = "&F"
        hf.left.size = 8
        hf.right.text = "&A"
        hf.right.size = 8
    w.oddFooter.left.text = FONTE
    w.oddFooter.left.size = 8
    w.oddFooter.center.text = "Pagina &P di &N"
    w.oddFooter.center.size = 8
    w.oddFooter.right.text = f"v{VERSIONE}"
    w.oddFooter.right.size = 8


# --------------------------------------------------------------- fogli dei diagrammi
# Impaginazione dell'originale: diagramma grande (35,2 × 23,2 cm) su A3 orizzontale, una pagina;
# legenda e tabella dei punti sulla pagina seguente.
CH_W, CH_H = 35.2, 23.2


def chart_sheet(w, title, subtitle, chart, legend, tab):
    w.sheet_properties.tabColor = tab
    w.column_dimensions["A"].width = 2
    for c in range(2, 22):
        w.column_dimensions[L(c)].width = 9.5
    w["B1"] = title
    w["B1"].font = F_T
    w["B2"] = subtitle
    w["B2"].font = F_N
    w.add_chart(chart, "B4")
    rf = fonte_sotto(w, "B", 4, CH_H)
    fonte_in_cima(w, "N1:U1")
    LG = rf + 2
    for i, (a, bb) in enumerate(legend):
        put(w, f"B{LG + i}", a, F_B if i == 0 else Font(name=ARIAL, size=9), FILL_SUB if i == 0 else None)
        w.merge_cells(f"B{LG + i}:E{LG + i}")
        put(w, f"F{LG + i}", bb, Font(name=ARIAL, size=9), FILL_SUB if i == 0 else None)
        w.merge_cells(f"F{LG + i}:M{LG + i}")
    put(w, f"O{LG}", "Punto", F_B, FILL_SUB)
    w.merge_cells(f"O{LG}:Q{LG}")
    for j, t in enumerate(["T [°C]", "UR [%]", "x [g/kg]", "h [kJ/kg]"]):
        put(w, f"{L(18 + j)}{LG}", t, F_B, FILL_SUB, align=CENTER)
    rr = LG + 1
    for s in ("E", "I"):
        b = SEAS[s]
        for j, nm in enumerate(("Esterno", "Ambiente", "Immissione")):
            put(w, f"O{rr}", f"{nm} – {'estate' if s == 'E' else 'inverno'}",
                Font(name=ARIAL, size=9, bold=True, color=OR_E if s == "E" else OR_I),
                FILL_SUB_I if s == "E" else FILL_SUB_E)
            w.merge_cells(f"O{rr}:Q{rr}")
            for q, col in enumerate("HIJK"):
                calc(w, f"{L(18 + q)}{rr}", f"=UTA!{col}{b + 2 + j}", "0.0" if col != "J" else "0.00")
            rr += 1
    last = LG + max(len(legend), 7) - 1
    print_setup(w, f"A1:U{last}", "landscape", fit=(1, 2), row_breaks=(rf,), paper=8)


SUBT = (f"=\"Pressione di calcolo p = \"&FIXED({P},0,TRUE)&\" Pa (altitudine \"&FIXED(UTA!D{R_Z},0,TRUE)&\" m). "
        f"Rosso = ESTATE, blu = INVERNO; E = esterno, A = ambiente, I = immissione.\"")
leg_common = [("Curva nera spessa", "saturazione (UR 100 %)"),
              ("Curve nere sottili", "umidità relativa 10…90 %"),
              ("Rette nere continue discendenti", "entalpia costante [kJ/kg aria secca]"),
              ("Rette nere tratteggiate", "volume specifico costante [m³/kg aria secca]"),
              ("Spezzata ROSSA spessa", "sequenza ESTATE (punto 0 = esterno, poi uscita di ogni riga)"),
              ("Spezzata BLU spessa", "sequenza INVERNO"),
              ("Rombo / quadrato / triangolo", "E esterno / A ambiente / I immissione"),
              ("Tratteggio rosso / blu", "retta ambiente (da A verso I) estate / inverno")]
leg_psicro = ([("Legenda – diagramma T–x", "")] +
              [("Assi", "ascissa T a bulbo secco [°C]; ordinata (a destra) x [g/kg aria secca]")] + leg_common +
              [("Goniometro in alto a sinistra", "direzioni per R = Qs/(Qs+Ql); segmenti colorati = R di progetto"),
               ("Nota", "le righe «Nessuna» ripetono il punto precedente; trasformazioni rettilinee (non smussate)")])
leg_moll = ([("Legenda – diagramma di Mollier", "")] +
            [("Assi", "ascissa x [g/kg]; ordinata (a destra) Y = (h − 2501·x)/1,006 = T·(1 + 1,849·x): a x = 0 coincide con T"),
             ("Rette nere quasi orizzontali", "isoterme ogni 5 °C (etichettate)")] + leg_common +
            [("Scala di bordo Δh/Δx [kJ/kg]", "direzione = retta dal polo (x = 0; Y = 20) alla tacca; R ≈ 1 − 2501/(Δh/Δx)"),
             ("Raggi tratteggiati colorati", "rapporto Δh/Δx del punto A → I di progetto (con R) estate / inverno")])
chart_sheet(wd, "Diagramma psicrometrico (T – x) con le trasformazioni dell'UTA", SUBT,
            build_chart_orig(CH_W, CH_H), leg_psicro, "0070C0")
chart_sheet(wm, "Diagramma di Mollier (h – x) con le trasformazioni dell'UTA", SUBT,
            stile_originale(build_mollier(CH_W, CH_H), etichette_curve=True), leg_moll, "C00000")

# copia ridotta del diagramma nel foglio UTA (fuori dall'area di stampa)
ws.add_chart(build_chart(26, 16, labels=False), "V5")
fonte_sotto(ws, "V", 5, 16)
ws["V4"] = "Diagramma T–x (copia ridotta, non stampata – versione completa nei fogli «psicro» e «Mollier»)"
ws["V4"].font = F_B

# ===================================================================== GUIDA
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "guida_testo.py"), encoding="utf-8").read())
wg.sheet_properties.tabColor = "548235"
wg.column_dimensions["A"].width = 2
GW = 95
wg.column_dimensions["B"].width = GW
wg["B1"] = FONTE_LUNGA
wg["B1"].font = F_FONTE
wg["B1"].alignment = Alignment(horizontal="right")
r = 2
G_ROWS = []          # (riga, tipo, altezza)
for kind, text in GUIDA:
    parts = [text] if kind in ("F", "T", "H", "S") else [t for t in str(text).split("\n") if t.strip()]
    for part in parts:
        c = wg[f"B{r}"]
        c.value = part
        if kind == "T":
            c.font = Font(name=ARIAL, size=14, bold=True, color="1F3864")
        elif kind == "H":
            c.font = Font(name=ARIAL, size=11, bold=True, color="FFFFFF")
            c.fill = FILL_GEN
        elif kind == "S":
            c.font = Font(name=ARIAL, size=10, bold=True, color="1F3864")
        elif kind == "F":
            c.font = Font(name="Courier New", size=8.5)
            c.fill = FILL_CALC
        else:
            c.font = F_N
        c.alignment = Alignment(wrap_text=True, vertical="top")
        cpl = {"F": 100, "T": 70, "H": 85}.get(kind, 98)      # caratteri per riga (stima prudente)
        lh = {"F": 11.5, "T": 20, "H": 16}.get(kind, 13.5)
        nlines = sum(max(1, -(-len(line) // cpl)) for line in str(part).split("\n"))
        hgt = min(409, lh * nlines + 5)
        wg.row_dimensions[r].height = hgt
        G_ROWS.append((r, kind, hgt))
        r += 1
# impaginazione: interruzioni manuali calcolate (nessun titolo di sezione a fine pagina)
G_SCALE = 93
G_LIMIT = 0.97 * 734 / (G_SCALE / 100)     # pt di righe per pagina (86 % dell'area utile)
G_BREAKS = []
cur = 0
for i, (rr_, kind, hgt) in enumerate(G_ROWS):
    nxt = G_ROWS[i + 1][2] if i + 1 < len(G_ROWS) else 0
    need = hgt + (nxt + 40 if kind in ("H", "S") else 0)
    if cur > 0 and cur + need > G_LIMIT:
        G_BREAKS.append(rr_ - 1)
        cur = 0
    cur += hgt
GUIDA_LAST = r - 1
print_setup(wg, f"A1:B{GUIDA_LAST}", "portrait", scale=G_SCALE, row_breaks=G_BREAKS)

# Calcoli: si stampano costanti, motore degli stati (colonne principali) e grandezze di stagione
print_setup(wc, "A1:P53", "landscape", fit=(1, 1))
print_setup(wl, f"A1:I{2 + NT}", "landscape", fit=(1, 1))
# UTA: scala fissa (con «Adatta a» Excel ignora le interruzioni manuali); 2 pagine A4 orizzontali
print_setup(ws, f"A1:T{R_STIMA + 10}", "landscape", scale=UTA_SCALE, row_breaks=(SEAS["I"] - 1,))

wl.sheet_state = "hidden"
wb.calculation.fullCalcOnLoad = True
wb.active = 0
os.makedirs(os.path.dirname(OUT), exist_ok=True)
wb.save(OUT)
print("salvato", OUT)


# ------------------------------------------------- mappa delle celle (per MAPPA_CELLE.md / cellmap.json)
import json
LAYOUT = {"SEAS": SEAS, "O": {"TEST": O_TEST, "UREST": O_UREST, "TAMB": O_TAMB, "URAMB": O_URAMB, "QS": O_QS, "QL": O_QL,
                              "PE": O_PE, "PA": O_PA, "PI": O_PI, "DT": O_DT, "R": O_R, "AVV": O_AVV,
                              "R0": O_R0, "SUMH": O_SUMH},
          "GEN": {"z": R_Z, "pcalc": R_PCALC, "pover": R_POVR, "p": R_P, "V": R_V, "OA": R_OA, "rif": R_RIF},
          "TR_ROWS": TR_ROWS, "TRL": TRL, "SEC": SEC, "SE_ROWS": SE_ROWS, "SC": SC, "SC_COL": SC_COL,
          "STIMA": R_STIMA, "TIPI": [t[0] for t in TIPI], "RIF": RIF_PORTATA}
json.dump(LAYOUT, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "layout.json"), "w"), indent=1, ensure_ascii=False)
