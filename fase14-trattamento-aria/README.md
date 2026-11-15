# Fase 14 – Trattamento aria (psicrometria)

Base di calcolo del menu **«Trattamento aria › Psicrometria»** del sito (14/11/2026, quattro pagine sperimentali:
Trasformazioni (UTA), Ore di funzionamento, Carichi latenti, Free cooling e recupero). Il calcolo nelle pagine lo fa il
browser con `fase5-sito/sito/psicro.js`; qui ci sono il **gemello Python** con le stesse funzioni, i test contro un
riferimento indipendente e i test di parità con il sito, e il generatore del **foglio Excel** `psicro_UTA.xlsx` che il sito
offre da scaricare.

```
aria/psicro.py        gemello di psicro.js: stati, inverse, trasformazioni, sequenza UTA, serie orarie (NumPy),
                      condizioni di progetto, ora locale e gruppi di ore
foglio/               generatore del foglio psicro_UTA.xlsx (build_psicro.py, guida_testo.py), mappa delle celle e verifica
tests/test_psicro.py  aria/psicro.py contro psychrolib 2.5 SI (tests/dati/) e casi UTA
tests/test_parita_js.py + parita_node.js   stesso calcolo in node (psicro.js, gruppi_ore.js) e in Python
tests/dati/           riferimento psychrolib (vedi LEGGIMI.md)

Gemelli delle pagine (stessi numeri del browser, verificati con prove di parità in node):
aria/trasformazioni.py  Trasformazioni (UTA): stima stagionale del foglio, celle del foglio compilato, configurazione
aria/ore.py             Ore di funzionamento: statistiche del gruppo, classi di T e x («bin»), zona di comfort
aria/latenti.py         Carichi latenti: deumidificazione d'estate e umidificazione a vapore d'inverno dell'aria esterna
aria/freecooling.py     Free cooling e recupero: regimi ora per ora, economizzatore, recuperatore, brina
tests/test_trasformazioni.py                 trasformazioni.py e parità con aria_trasformazioni.js
tests/test_ore.py + parita_ore_node.js       ore.py e parità con aria_ore.js
tests/test_freecooling.py + freecooling_node.js   freecooling.py, casi a mano e parità con aria_freecooling.js
(fase5-sito/tests/test_aria_latenti.py)      latenti.py e parità con aria_latenti.js (sta nella fase 5)
```

Prove, dalla cartella principale del repository:
```bash
python -m pytest fase14-trattamento-aria/tests          # servono numpy, pyarrow non serve; node per la parità
python -m pytest fase5-sito/tests/test_aria_latenti.py  # carichi latenti (Python e node)
python fase14-trattamento-aria/foglio/build_psicro.py   # rifà strumenti/psicro_UTA.xlsx (vedi foglio/README.md)
```
Senza node le prove di parità si saltano. psychrolib serve solo a rigenerare `tests/dati/reference_cases.json`
(`make_reference.py`): le prove normali leggono il file già pronto.

## Formule

Le stesse del foglio e di psychrolib SI (ASHRAE Handbook – Fundamentals 2017, cap. 1):

| Grandezza | Formula |
|---|---|
| pressione dalla quota | p = 101325·(1 − 2,25577·10⁻⁵·z)^5,2559 Pa (quota limitata a −500…8000 m) |
| pressione di saturazione | Hyland–Wexler, **sul ghiaccio per t ≤ 0,01 °C**, sull'acqua sopra |
| umidità specifica | x = 0,621945·pw/(p − pw) [kg/kg aria secca] |
| entalpia | h = 1,006·t + x·(2501 + 1,86·t) [kJ/kg aria secca] |
| volume specifico | v = 0,287042·(t + 273,15)·(1 + 1,607858·x)/(p/1000) [m³/kg aria secca]; ρ = (1 + x)/v |
| T di rugiada | Newton su ln psat partendo da Magnus, fino a convergenza |
| T di bulbo umido | equazione ASHRAE (35/37 sotto 0 °C); Newton partendo da T dove la radice è unica, e **entro 3 K da 0 °C (o se Newton non converge) la bisezione di psychrolib** (`GetTWetBulbFromHumRatio`: tra T di rugiada e T, tolleranza 0,001 K, ramo «acqua» o «ghiaccio» secondo il punto medio), così vicino a 0 °C si sceglie la stessa radice di psychrolib (14/11/2026; prima fino a 0,68 K di scarto in qualche stato) |
| coordinata di Mollier | Y = (h − 2501·x)/1,006 = T·(1 + 1,86·x/1,006): a x = 0 coincide con T |

Il foglio fa 3–6 passi di Newton «srotolati» nelle celle; qui si va fino a convergenza: le differenze sono sotto i
millesimi di grado (414/414 controlli del foglio contro psychrolib entro le tolleranze; qui griglia entro 2·10⁻³ K).

## Convenzioni (le stesse del foglio)

- **Portata**: ṁ (aria secca) = V/(3600·v_rif); riferimento a scelta tra aria esterna (predefinito), ambiente, aria
  standard 20 °C/101325 Pa (v = 0,287042·293,15/101,325) e densità fissa 1,2 kg/m³ (v = (1 + x_est)/1,2).
- **Punto di immissione dai carichi**: T_imm = T_amb − Qs/(ṁ·cp), cp = 1,006 + 1,86·x_amb; x_imm = x_amb − Ql/(ṁ·2501).
  In inverno Qs è la dispersione (positiva) e T_imm = T_amb + Qs/(ṁ·cp). R = Qs/(Qs + Ql) (in inverno con Qs negativo).
- **Tipi di trasformazione** (codici 1–11 del foglio): Nessuna · Miscela con ricircolo (P1 frazione in massa o AUTO =
  1 − quota esterna; miscela di h e x con l'aria ambiente; le righe prima della miscela hanno la portata di aria esterna) ·
  Recuperatore di calore (P1 εs, P2 εl: sensibile o entalpico, ripresa = ambiente) · Riscaldamento / Raffreddamento
  sensibile (P1 T uscita o P2 potenza) · Raffreddamento con deumidificazione (P1 x uscita o AUTO = x_imm, P2 BF, vuoto 0,10,
  P3 T ADP che prevale; x_ADP = (x_out − BF·x_in)/(1 − BF), T_ADP = rugiada di x_ADP, T_out = T_ADP + BF·(T_in − T_ADP)) ·
  Umidificazione adiabatica (h costante; P1 x o AUTO, P2 UR, P3 efficienza di saturazione sull'isoentalpica; limitata alla
  saturazione) · Umidificazione a vapore (P1 x o AUTO, P2 UR; Δh = Δx·h_vapore, 2676 kJ/kg se P3 è vuoto) ·
  Preriscaldamento (AUTO = fino all'isoentalpica che porta a x_imm con UR P3, predefinita 90 %) · Post-riscaldamento (AUTO =
  T_imm − ΔT dei ventilatori a valle) · Ventilatore (P1 ΔT o P2 potenza).
- **Potenze**: Q_tot = ṁ·Δh, Q_lat = ṁ·Δx·2501, Q_sens = Q_tot − Q_lat (kW, + calore ceduto all'aria); acqua = ṁ·Δx·3600
  kg/h (+ aggiunta, − condensata); la miscela non ha potenza.
- **Avvisi**: stesse frasi della colonna «Note / avvisi» del foglio (FIXED con la virgola decimale), uguali in JS e Python.
- **Raggiungibile**: NO se il post-riscaldamento AUTO non basta o se l'uscita dista più di 0,3 K o 0,1 g/kg dall'immissione.

## Condizioni di progetto da una serie oraria

Statistiche della **serie scelta** (non valori di norma: per la Legge 10 restano UNI 10349 e UNI EN 12831). Livelli
modificabili dall'utente (decisione del 14/11/2026), **predefiniti 99 % / 1 %**; scelte rapide 99,6 · 99 · 95 % per
l'inverno e 0,4 · 1 · 5 % per l'estate, più un valore libero.

- ore valide = ore con T e UR; quantile con interpolazione lineare sui valori ordinati (float32 come nel browser);
- **inverno L %**: T superata nel L % delle ore (quantile 1 − L/100), con l'**UR media coincidente**;
- **estate l %**: T superata solo nell'l % delle ore (quantile 1 − l/100), con il **bulbo umido medio coincidente**;
- allo stesso livello estivo: **entalpia** e **umidità specifica** con la **T media coincidente**, e il **bulbo umido** con
  la T media coincidente;
- «coincidente» = media della grandezza abbinata sulle ore il cui valore cade nella classe centrata sul percentile
  (1 K per T e bulbo umido, 2 kJ/kg per h, 0,5 g/kg per x), allargata (raddoppio) finché ci sono almeno 10 ore. Metodo
  come le tabelle ASHRAE (cap. 14, MCWB/MCDB), applicato alla serie oraria del comune.

## Gruppi di ore e ora locale

`campi_orari()` (e `campiOrari()` in `gruppi_ore.js`) danno anno, mese, giorno, ora locale, giorno della settimana per ogni
ora della serie (in UTC), con l'ora legale italiana: dal 1996 la regola europea (dall'ultima domenica di marzo alle 01 UTC
all'ultima di ottobre alle 01 UTC), prima le date storiche di tzdata (`LEGALE_STORICA`, Europe/Rome: 1940–1948, nessuna
1949–1965, 1966–1979 fine maggio–fine settembre, 1980–1995 fine marzo–fine settembre). Giorno della settimana giusto anche
prima del 1970 (in JS `((g + 3) % 7 + 7) % 7`). Prova: `test_regressione_1940_…` in `tests/test_parita_js.py` (JS =
Python = zoneinfo ora per ora dal 1940 al 2029). «Ultimi N anni» come il server: ultima ora + 1 h − N anni, 29/02 → 28/02.
Un gruppo è: date da/a (gg/mm, anche a cavallo d'anno), ore da/a (l'ora h è compresa se da ≤ h < a,
anche a cavallo della mezzanotte), giorni tutti o feriali, ultimi N anni (N×12 mesi fino all'ultima ora). Preset: Estate
01/06–30/09; Inverno 01/11–31/03 (o il periodo di accensione della zona climatica DPR 412 del comune); Ore d'ufficio 8–18
feriali (dalle 8 alle 18, cioè ore 8:00–17:59: 10 ore al giorno; la pagina lo scrive sotto i campi); Tutto il giorno.

## Come le usa il sito

`fase5-sito/sito/psicro.js` (formule), `diagramma_aria.js` (diagramma psicrometrico e di Mollier), `scelta_aria.js`
(passo 1: comune e serie, livello di progetto), `gruppi_ore.js` (gruppi di ore): API nel README della fase 5, sezione
«Trattamento aria». La serie oraria arriva da `GET /api/psicro/serie/{istat}?anni=` (fase 4); con `?prova=1` le pagine usano
una serie sintetica generata nel browser.

## Foglio Excel

Vedi `foglio/README.md`. Il file scaricabile è `fase5-sito/sito/strumenti/psicro_UTA.xlsx` (eccezione in `.gitignore`).
