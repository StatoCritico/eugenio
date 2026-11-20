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

**v2.3 (19/11/2026)** – richiesta di Paolo: i fogli «psicro» e «Mollier» riprendono stile, impaginazione e grafica del
diagramma originale `psicro_finale.xls` (analizzato dal suo XML: 195 serie, griglia, assi, misure del disegno).
`stile_originale()` ristila un grafico già costruito: fondo bianco con bordo nero, griglia nera (continua ogni 5, tratteggiata
ogni 1), curve nere (saturazione 3 pt, le altre 1 pt, tratteggi lunghi), niente titoli degli assi, numeri dell'asse
verticale a destra, Arial 10, estate rossa `FF0000` e inverno blu `0000FF` spessi 3 pt, trasformazioni rettilinee
(nessuna serie smussata: LibreOffice smussa tutto il grafico se una sola serie lo è). `build_chart_orig()` costruisce il T–x
del foglio «psicro» con le famiglie dell'originale ricalcolate nel foglio «Calcoli» (blocco in fondo, dopo tutte le altre
celle: nessun indirizzo esistente cambia): asse delle entalpie x = 20/30·T + 10 e parallela +4, isoentalpiche in kcal/kg
0…30 fino all'asse + 2, in kJ/kg 10…95 tratteggiate nella fascia tra le rette d'asse, isocore 0,78…0,95 fino a
saturazione + 2, goniometro a due semicerchi centrati in (0; 30) – raggio 7 con i rombi del fattore termico R, raggio 9
con i quadrati di Δh/Δx in kJ/g, ⊗ al centro e ∞ come etichette – e i due raggi di progetto A → I. **Scritte dell'originale** (20/11, richiesta di Paolo con lo screenshot di Excel): tabella
`ETI` copiata dalle colonne CE…CO del foglio «calc» (posizione e testo), una serie invisibile di un punto per scritta
(`serie_etichetta`), Arial 8 grassetto; volumi e UR spostati quanto la curva rispetto a 101325 Pa; unità della scala
Δh/Δx scritta «kJ/g» (nell'originale «kcal/kgh2o», sbagliata). `build_mollier_orig()`: nel Mollier le stesse famiglie e
le stesse scritte portate in X = x, Y = T·(1 + 1,849·x/1000) (colonne `OG_MY`), più isoterme, scala di bordo Δh/Δx e polo. Disegno 35,2 × 23,2 cm su A3 orizzontale; legenda e tabella dei punti in pagina 2. La
copia ridotta nel foglio UTA non cambia. Verifica: **414/414** controlli, 0 errori di formula dopo il ricalcolo,
prove della fase 14 passate.

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
