# Foglio psicro_UTA.xlsx

Cartella di lavoro senza macro (Excel 2010+, LibreOffice, Google Sheets): proprietà dell'aria umida, punto di immissione
dai carichi, sequenze UTA estate e inverno (fino a 6 righe), diagramma psicrometrico (foglio «psicro») e di Mollier, guida.
Riferimento per i numeri del sito: `psicro.js` e `aria/psicro.py` danno gli stessi risultati.

| File | Cosa fa |
|---|---|
| `build_psicro.py` | costruisce il foglio con openpyxl (tutte formule) e scrive `layout.json` |
| `guida_testo.py` | testo del foglio «Guida» (letto da build_psicro.py) |
| `make_cellmap.py` | da `layout.json` scrive `cellmap.json` e `MAPPA_CELLE.md` (indirizzi delle celle) |
| `check_workbook.py` | verifica: scrive gli ingressi dei casi in una copia, ricalcola con LibreOffice e confronta con `../tests/dati/reference_cases.json` |

Rigenerare (dalla cartella `foglio/`):

```
python3 build_psicro.py                  # scrive ../../fase5-sito/sito/strumenti/psicro_UTA.xlsx (il file scaricabile)
python3 build_psicro.py /tmp/prova.xlsx  # oppure altrove
python3 make_cellmap.py                  # cellmap.json e MAPPA_CELLE.md
python3 check_workbook.py ../../fase5-sito/sito/strumenti/psicro_UTA.xlsx cellmap.json --ref ../tests/dati/reference_cases.json
```

La verifica vuole LibreOffice (`soffice`) e dura qualche minuto; il 14/11/2026: **414/414 controlli superati**; il
15/11/2026, dopo il cambio dell'ambiente invernale predefinito, di nuovo **414/414** (i casi scrivono i loro ingressi) e
**0 errori** di formula su 6.011 formule.

**v2.2 (16/11/2026)** – regola dei file Excel di EuGEnio (obbligo di licenza CC BY 4.0): «Fonte: EuGEnio –
eugenio.statocritico.it» in cima a ogni foglio (riga 1 a destra del titolo, celle unite; nella Guida in B1, il testo parte
da B2), sotto ogni grafico (prima riga libera sotto il grafico, calcolata con `fonte_sotto`) e a sinistra nel piè di
pagina di ogni pagina stampata. Nessun indirizzo di UTA, Calcoli o Liste cambia. Verifica: **414/414** controlli; PDF di
LibreOffice di 12 pagine con la citazione in ogni piè.

Valori di partenza delle celle gialle (`DEF_IN`): estate esterno 32 °C/50 %, ambiente 26 °C/50 %; inverno esterno
−5 °C/80 %, **ambiente 20 °C/40 %** (decisione di Paolo del 15/11/2026, come le pagine «Trattamento aria»; prima 50 %).
Sono anche `DATI_PREDEFINITI` di `psicro.js` e di `aria/psicro.py`: se cambiano qui, cambiano là.

Il file del sito porta anche i **risultati salvati** delle formule (Excel e LibreOffice li ricalcolano comunque
all'apertura, `fullCalcOnLoad`): `tests/test_trasformazioni.py::test_come_il_foglio` li confronta con il calcolo in
Python e si salta se mancano. Dopo `build_psicro.py` si ricalcola il file con LibreOffice scrivendo nel file solo i
valori calcolati (il 15/11/2026 con lo script `recalc.py` della skill xlsx di Claude), poi si rifà la verifica.
Se cambia il foglio, cambiano anche `psicro.js` e `aria/psicro.py` (e i test di parità), e la versione del sito.
