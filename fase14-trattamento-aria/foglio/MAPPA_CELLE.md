# Mappa delle celle – psicro_UTA.xlsx

Generata da `build/make_cellmap.py` (indirizzi stabili: cambiano solo se si modifica `build_psicro.py`).
Tutte le celle sono nel foglio **UTA** salvo diversa indicazione. x in **g/kg** nel foglio UTA (kg/kg nel foglio Calcoli), UR in **%**, potenze in **kW**, carichi in ingresso in **W**.

## Dati generali (input in giallo)

| Grandezza | Cella | Note |
|---|---|---|
| Altitudine z [m] | D6 | input |
| Pressione calcolata [Pa] | D7 | formula |
| Pressione imposta [Pa] | D8 | input facoltativo, vuoto = calcolata |
| Pressione di calcolo p [Pa] | D9 | formula |
| Portata di mandata V [m³/h] | D10 | input |
| Quota aria esterna [%] | D11 | input (100 = tutta aria esterna) |
| Portata rinnovo / ricircolo [m³/h] | D12 / D13 | formula |
| Riferimento della portata | D14 | input, menu: «Aria esterna (condizioni di progetto)» / «Aria ambiente» / «Aria standard 20 °C, 101325 Pa (ρ = 1,204 kg/m³)» / «Densità fissa ρ = 1,2 kg/m³» |
| v rif. [m³/kg] estate / inverno | H7 / I7 |  |
| ρ rif. [kg/m³] | H8 / I8 |  |
| ṁ aria secca [kg/s] | H9 / I9 | estate / inverno |
| ṁ [kg/h] | H10 / I10 |  |
| ṁ aria esterna [kg/s] | H11 / I11 |  |
| frazione ricircolo AUTO | H12 / I12 |  |

## ESTATE (intestazione riga 16)

| Input | Cella |
|---|---|
| T esterna [°C] | D18 |
| UR esterna [%] | D19 |
| T ambiente [°C] | D20 |
| UR ambiente [%] | D21 |
| Carico sensibile [W] | D22 |
| Carico latente [W] | D23 |

Punti (colonne: H = T °C, I = UR %, J = x g/kg, K = h kJ/kg, L = T rugiada °C, M = T bulbo umido °C, N = v m³/kg, O = ρ kg/m³):

| Punto | Riga |
|---|---|
| E esterno | 18 |
| A ambiente | 19 |
| I immissione | 20 |

ΔT immissione H21; fattore termico R H22; verifiche (testo) H23.

Sequenza: riga 0 (ingresso = esterno) riga 27; righe 1–6 = righe 28–33.
Colonne: B N, **C tipo** (input, menu), **D P1, E P2, F P3** (input), G significato parametri, H T, I UR %, J x g/kg, K h, L T rugiada, M T bulbo umido, N v, O ṁ kg/s, P Q sensibile kW, Q Q latente kW, R Q totale kW, S acqua kg/h (+ aggiunta, − condensata), T note.

| Riepilogo | Cella |
|---|---|
| Potenza frigorifera totale [kW] | D36 |
|   di cui sensibile [kW] | D37 |
|   di cui latente [kW] | D38 |
| Preriscaldamento [kW] | D39 |
| Post-riscaldamento + riscaldamento [kW] | D40 |
| Acqua condensata [kg/h] | D41 |
| Acqua di umidificazione [kg/h] | D42 |
| Potenza recuperata [kW] | D43 |
| Calore ventilatori [kW] | D44 |
| Uscita UTA (T, UR, x, h) | H37:K37 |
| Immissione richiesta | H38:K38 |
| Scostamento | H39:K39 |
| Raggiungibile? («SÌ»/«NO») | H40 |
| Esito (testo) | H41 |

## INVERNO (intestazione riga 46)

| Input | Cella |
|---|---|
| T esterna [°C] | D48 |
| UR esterna [%] | D49 |
| T ambiente [°C] | D50 |
| UR ambiente [%] | D51 |
| Dispersioni [W] | D52 |
| Carico latente [W] | D53 |

Punti (colonne: H = T °C, I = UR %, J = x g/kg, K = h kJ/kg, L = T rugiada °C, M = T bulbo umido °C, N = v m³/kg, O = ρ kg/m³):

| Punto | Riga |
|---|---|
| E esterno | 48 |
| A ambiente | 49 |
| I immissione | 50 |

ΔT immissione H51; fattore termico R H52; verifiche (testo) H53.

Sequenza: riga 0 (ingresso = esterno) riga 57; righe 1–6 = righe 58–63.
Colonne: B N, **C tipo** (input, menu), **D P1, E P2, F P3** (input), G significato parametri, H T, I UR %, J x g/kg, K h, L T rugiada, M T bulbo umido, N v, O ṁ kg/s, P Q sensibile kW, Q Q latente kW, R Q totale kW, S acqua kg/h (+ aggiunta, − condensata), T note.

| Riepilogo | Cella |
|---|---|
| Potenza frigorifera totale [kW] | D66 |
|   di cui sensibile [kW] | D67 |
|   di cui latente [kW] | D68 |
| Preriscaldamento [kW] | D69 |
| Post-riscaldamento + riscaldamento [kW] | D70 |
| Acqua condensata [kg/h] | D71 |
| Acqua di umidificazione [kg/h] | D72 |
| Potenza recuperata [kW] | D73 |
| Calore ventilatori [kW] | D74 |
| Uscita UTA (T, UR, x, h) | H67:K67 |
| Immissione richiesta | H68:K68 |
| Scostamento | H69:K69 |
| Raggiungibile? («SÌ»/«NO») | H70 |
| Esito (testo) | H71 |

## Stima stagionale
Input D78:D83 (GG, ore/giorno, rendimento, PCI, ore eq. estive, EER); risultati H78:H85.

## Foglio Calcoli

- Pressione D4 (Pa), D5 (kPa).
- Motore degli stati: estate righe 17–26 (E, A, I, R0, R1…R6), inverno righe 28–37. Colonne: C T, D x [kg/kg], E pv, F psat [Pa], G φ [-], H h, I v, J ρ, K x [g/kg], P T rugiada, AH T bulbo umido.
- Grandezze di stagione: colonna D (estate) / E (inverno), righe vref 41, mtot 42, rho 43, cpA 44, Timm 45, ximm 46, fgen 47, mixidx 48, fmix 49, R 50, dT 51, xref 52, mOA 53.
- Trasformazioni: estate righe 57–62, inverno righe 67–72; colonne principali: codice C, ṁ O, T ADP AH, T uscita CR, x uscita CS, Q tot CV, Q lat CW, Q sens CX, acqua CY, note DC.
- Dati del diagramma T–x (foglio «psicro»): dalla riga 100 (tabella di saturazione, curve UR, isoentalpiche, isocore, rette ambiente, goniometro).
- Dati del diagramma di Mollier (foglio «Mollier»): dalla riga 240 (curve UR, isoterme 300–483 e 486–495, isoentalpiche 500–512, isocore 520–529, trasformazioni e punti 540–563 = x da UTA e Y = T·(1+1,86·x/1006), scala di bordo Δh/Δx 580–598).

Ordine dei fogli: UTA, psicro (ex «Diagramma»), Mollier, Guida, Calcoli, Liste (nascosto). Nessun indirizzo di UTA o Calcoli è cambiato rispetto alla v2.0.

## Codici dei tipi di trasformazione

| Codice | Tipo |
|---|---|
| 1 | Nessuna |
| 2 | Miscela con ricircolo |
| 3 | Recuperatore di calore |
| 4 | Riscaldamento sensibile |
| 5 | Raffreddamento sensibile |
| 6 | Raffreddamento con deumidificazione |
| 7 | Umidificazione adiabatica |
| 8 | Umidificazione a vapore |
| 9 | Preriscaldamento |
| 10 | Post-riscaldamento |
| 11 | Ventilatore |

## Verifica automatica
`cellmap.json` (stessa cartella) è nel formato di `check_workbook.py`:
```
python3 check_workbook.py ../../fase5-sito/sito/strumenti/psicro_UTA.xlsx cellmap.json --ref ../tests/dati/reference_cases.json
```
Convenzioni: per i casi estivi il post-riscaldamento AUTO porta a T_imm − ΔT ventilatore (variante `variant_postheat_to_Timm_minus_fan` del riferimento); nel caso d il riscaldatore AUTO porta a T_imm e il vapore viene dopo (variante `variant_heat_to_Timm_then_steam`).
