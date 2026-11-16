# -*- coding: utf-8 -*-
# Testo del foglio «Guida» (letto da build_psicro.py). Tipi: T titolo, H sezione, S sottosezione, P paragrafo, F formula.
GUIDA = [
("T", "GUIDA – UTA: trasformazioni psicrometriche e diagramma dell'aria umida"),
("P", f"Versione {VERSIONE} del {DATA}. Cartella di lavoro senza macro, compatibile con Excel 2010 e successivi, LibreOffice Calc e Google Sheets."),

("H", "1. A cosa serve"),
("P", "Il file serve a dimensionare in modo rapido un'unità di trattamento aria (UTA) per un ambiente, in estate e in inverno:\n"
      "• calcola le proprietà dell'aria umida (T, UR, x, h, T di rugiada, T di bulbo umido, volume specifico, densità) alla pressione del sito;\n"
      "• ricava dai carichi dell'ambiente il punto di immissione (I) e il fattore termico R;\n"
      "• calcola una sequenza di fino a 6 trasformazioni per stagione (miscela, recuperatore, batterie, umidificatori, ventilatore) con potenze, acqua condensata o aggiunta e avvisi;\n"
      "• disegna le trasformazioni sul diagramma psicrometrico T–x (foglio «psicro») e sul diagramma di Mollier h–x (foglio «Mollier»);\n"
      "• fornisce una stima stagionale indicativa dell'energia per la ventilazione."),

("H", "2. Legenda dei colori e dei fogli"),
("P", "• Celle GIALLE con testo blu: dati da inserire o modificare. Ogni cella gialla ha una nota (triangolino rosso) con cosa inserire, unità di misura e valori tipici.\n"
      "• Celle GRIGIE: risultati calcolati con formule. Non vanno modificate.\n"
      "• Intestazioni AZZURRE = ESTATE, ROSSE = INVERNO, blu-grigio = dati generali. Nei diagrammi: spezzata BLU = ESTATE, spezzata ROSSA = INVERNO.\n"
      "• Celle rosate nella colonna «Note / avvisi» o nelle verifiche: c'è un problema da controllare.\n"
      "Fogli: «UTA» (dati e risultati, è il foglio principale), «psicro» (diagramma T–x), «Mollier» (diagramma h–x), «Guida» (questo testo), «Calcoli» (formule di servizio e dati delle curve, da non modificare), «Liste» (nascosto: elenchi dei menu a tendina)."),
("P", "Convenzione dei segni delle potenze: positivo = calore ceduto all'aria (riscaldamento, umidificazione), negativo = calore sottratto all'aria (raffreddamento, deumidificazione). "
      "Nel riepilogo la potenza frigorifera e l'acqua condensata sono riportate come valori positivi."),

("H", "3. Procedura passo per passo"),
("P", "1) DATI GENERALI: inserire l'altitudine (la pressione si calcola da sola; se serve si può imporre una pressione), la portata totale di mandata in m³/h, la quota di aria esterna in % e lo stato a cui si riferisce la portata (di norma «Aria esterna»).\n"
      "2) ESTATE e INVERNO: inserire T e UR esterne di progetto, T e UR ambiente, i carichi sensibile e latente (in inverno: dispersioni da coprire con l'aria e apporti latenti). "
      "Il foglio calcola il punto di immissione I, il ΔT di immissione e il fattore termico R, con le verifiche (ΔT eccessivo, UR > 100 %, ecc.).\n"
      "3) SEQUENZA: per ogni riga scegliere il tipo di trasformazione dal menu e compilare i parametri P1, P2, P3. La colonna «Significato dei parametri» spiega cosa inserire per il tipo scelto. "
      "L'ingresso di ogni riga è l'uscita della riga precedente; la riga 0 è l'aria esterna.\n"
      "4) Leggere i risultati di ogni riga (stato in uscita, ṁ, potenze sensibile/latente/totale in kW, acqua in kg/h, note) e il RIEPILOGO della stagione.\n"
      "5) Controllare il confronto «Uscita UTA – Immissione richiesta»: se l'esito è «SÌ» la sequenza realizza il punto di immissione calcolato dai carichi.\n"
      "6) Guardare i fogli «psicro» e «Mollier» per verificare visivamente le trasformazioni (blu = estate, rosso = inverno).\n"
      "I modelli già compilati (preset) funzionano subito: modificare solo i dati gialli che interessano."),

("H", "4. Dati generali e portata in massa"),
("P", "Tutte le potenze si calcolano con la portata di ARIA SECCA ṁ [kg/s], perché entalpia e umidità specifica sono riferite al kg di aria secca. "
      "La portata in volume V [m³/h] viene convertita così:"),
("F", "ṁ = V / (3600 · v_rif)    v_rif = volume specifico [m³/kg a.s.] dello stato di riferimento\n"
      "ρ_rif = (1 + x_rif) / v_rif    densità dell'aria umida [kg/m³]"),
("P", "Opzioni di riferimento: «Aria esterna (condizioni di progetto)» (predefinita: la portata è quella aspirata all'esterno, ṁ diversa in estate e inverno), «Aria ambiente», "
      "«Aria standard 20 °C, 101325 Pa» (v = 0,8305 m³/kg, ρ = 1,204 kg/m³), «Densità fissa ρ = 1,2 kg/m³» (metodo tradizionale; ṁ = V·1,2/3600/(1+x_esterna)). "
      "La tabella «Conversione portata» mostra v, ρ e ṁ per le due stagioni.\n"
      "Quota di aria esterna: 100 % = UTA a tutta aria esterna. Con valori minori il resto è ricircolo alle condizioni ambiente: la miscela avviene nella riga «Miscela con ricircolo» (parametro AUTO). "
      "Le righe a monte della miscela lavorano con la sola portata di aria esterna ṁ·(1−f), quelle a valle con la portata totale ṁ."),

("H", "5. Punto di immissione e fattore termico"),
("F", "cp = 1,006 + 1,86·x_amb  [kJ/(kg K)]          r0 = 2501 kJ/kg\n"
      "ESTATE:  T_imm = T_amb − Qs/(ṁ·cp)          x_imm = x_amb − Ql/(ṁ·r0)\n"
      "INVERNO: T_imm = T_amb + Qd/(ṁ·cp)          x_imm = x_amb − Ql/(ṁ·r0)\n"
      "R = Qs/(Qs + Ql)  (in inverno Qs = −Qd)"),
("P", "Qs, Ql, Qd in kW (il foglio converte i W inseriti). La retta ambiente sul diagramma passa per A e I. Verifiche automatiche: ΔT di immissione > 10 K in estate o > 15 K in inverno (rischio di discomfort o stratificazione), UR di immissione > 100 % (punto impossibile: aumentare la portata), x di immissione ≤ 0, ricircolo previsto ma nessuna riga «Miscela»."),

("H", "6. Tipi di trasformazione e parametri"),
("P", "Ogni parametro può essere un numero; dove indicato si può scrivere il testo AUTO. Una cella vuota significa «non usato» oppure «valore predefinito». Se manca un parametro obbligatorio la riga non modifica lo stato e la nota segnala «Parametro mancante»."),
("S", "Nessuna"),
("P", "Riga inattiva: lo stato passa invariato."),
("S", "Miscela con ricircolo  – P1 = frazione di ricircolo [0–1] oppure AUTO"),
("P", "Miscela adiabatica dell'aria in arrivo con aria di ricircolo alle condizioni ambiente, pesata sulle portate di aria secca: x = (1−f)·x_in + f·x_amb, h = (1−f)·h_in + f·h_amb, T da (h, x). AUTO = 1 − quota di aria esterna. Nessuna potenza scambiata."),
("S", "Recuperatore di calore  – P1 = εs, P2 = εl (facoltativa)"),
("P", "Scambio tra aria esterna e aria di ripresa (= ambiente) a portate bilanciate: T = T_in + εs·(T_amb − T_in); x = x_in + εl·(x_amb − x_in). Con P2 vuoto o 0 il recuperatore è solo sensibile (piastre, batterie accoppiate); con εl > 0 è entalpico (ruota igroscopica). "
      "Valori tipici εs 0,5–0,75 (piastre controcorrente fino a 0,85). Non si considerano la condensazione/brinamento lato espulsione né lo sbrinamento."),
("S", "Riscaldamento sensibile  – P1 = T uscita [°C] oppure P2 = potenza [kW]"),
("P", "Batteria calda generica, x costante: Q = ṁ·(h_out − h_in). Con P2: T_out = T_in + Q/(ṁ·cp)."),
("S", "Raffreddamento sensibile  – P1 = T uscita [°C] oppure P2 = potenza frigorifera [kW]"),
("P", "Batteria fredda secca, x costante. Se la T di uscita scende sotto la T di rugiada dell'aria in ingresso compare un avviso: in realtà si avrebbe condensa, usare il tipo «Raffreddamento con deumidificazione»."),
("S", "Raffreddamento con deumidificazione  – P1 = x uscita [g/kg] o AUTO, P2 = BF, P3 = T ADP [°C]"),
("P", "Modello della batteria fredda con fattore di bypass: l'uscita giace sul segmento rettilineo (nel piano T–x) che unisce l'ingresso al punto ADP (apparatus dew point) sulla curva di saturazione:"),
("F", "x_ADP = (x_out − BF·x_in)/(1 − BF)          T_ADP = T di rugiada di x_ADP\n"
      "T_out = T_ADP + BF·(T_in − T_ADP)\n(modo con P3: x_ADP = x_sat(T_ADP), x_out = x_ADP + BF·(x_in − x_ADP))\n"
      "Q_tot = ṁ·(h_out − h_in)   Q_lat = ṁ·(x_out − x_in)·2501\nQ_sens = Q_tot − Q_lat     SHR = Q_sens/Q_tot\n"
      "Condensa [kg/h] = ṁ·(x_in − x_out)·3600"),
("P", "AUTO = x del punto di immissione (la batteria deumidifica quanto basta a coprire il carico latente). BF predefinito 0,10 (tipico 0,05–0,20: più ranghi = BF minore). "
      "Avvisi: ADP < 0 °C (rischio di brina), x obiettivo ≥ x ingresso (nessuna deumidificazione), batteria secca nel modo con ADP. La potenza è quella lato aria; l'entalpia della condensa (≈ 0,1–0,3 % del totale) è trascurata."),
("S", "Umidificazione adiabatica  – P1 = x uscita o AUTO; altrimenti P2 = UR uscita [%]; altrimenti P3 = efficienza di saturazione"),
("P", "Umidificatore a pacco evaporante o a ugelli con acqua ricircolata: trasformazione a ENTALPIA COSTANTE (h_out = h_in), la temperatura scende. "
      "Con l'efficienza: T_out = T_in − ε·(T_in − T*), dove T* è la temperatura di saturazione sulla stessa isoentalpica. Se la x richiesta supera la saturazione il risultato è limitato a UR 100 % con avviso. "
      "Acqua evaporata [kg/h] = ṁ·(x_out − x_in)·3600."),
("S", "Umidificazione a vapore  – P1 = x uscita o AUTO; altrimenti P2 = UR uscita [%]; P3 = entalpia del vapore [kJ/kg]"),
("F", "h_out = h_in + (x_out − x_in)·h_vap\nh_vap predefinita = 2676 kJ/kg (vapore saturo a ~100 °C)"),
("P", "La trasformazione è quasi isoterma (la T aumenta di qualche decimo di grado). Con UR obiettivo il foglio risolve per punto fisso (4 iterazioni)."),
("S", "Preriscaldamento  – P1 = T uscita o AUTO, P2 = potenza [kW], P3 = UR obiettivo dell'umidificatore per AUTO [%]"),
("P", "Batteria a monte dell'umidificatore adiabatico. AUTO = riscalda fino all'isoentalpica che passa per il punto (x_imm, UR = P3, predefinito 90 %): così l'umidificatore adiabatico a valle porta l'aria esattamente a x_imm con UR 90 %. "
      "Se l'aria è già abbastanza calda la batteria resta spenta (nota «non necessario»)."),
("S", "Post-riscaldamento  – P1 = T uscita o AUTO, P2 = potenza [kW]"),
("P", "AUTO = T_imm − ΔT dei ventilatori che si trovano più a valle nella sequenza, così che l'aria arrivi in ambiente esattamente a T_imm. "
      "Se l'aria in ingresso è già più calda (per esempio una batteria fredda che con portata piccola non riesce ad arrivare a T_imm) la batteria resta spenta e compare «PUNTO DI IMMISSIONE NON RAGGIUNGIBILE»: aumentare la portata o ridurre BF."),
("S", "Ventilatore  – P1 = ΔT [K] oppure P2 = potenza [kW]"),
("P", "Riscaldamento dell'aria dovuto al ventilatore e al motore (motore nel flusso): ΔT tipico 0,5–1 K. In alternativa si inserisce la potenza ceduta (≈ potenza elettrica assorbita)."),

("H", "7. Logica AUTO e modelli precompilati"),
("P", "Il testo AUTO collega le trasformazioni al punto di immissione, così i modelli funzionano senza toccare i parametri:\n"
      "• Miscela: frazione = 1 − quota aria esterna.\n• Batteria fredda: x uscita = x_imm.\n• Umidificatori: x uscita = x_imm.\n"
      "• Preriscaldamento: fino all'isoentalpica per (x_imm, UR 90 %).\n• Post-riscaldamento: T_imm − ΔT ventilatori a valle.\n"
      "ESTATE (preset): Miscela (AUTO) → Raffreddamento con deumidificazione (AUTO, BF 0,10) → Post-riscaldamento (AUTO) → Ventilatore (0,7 K).\n"
      "INVERNO (preset): Recuperatore (εs 0,6) → Miscela (AUTO) → Preriscaldamento (AUTO, UR 90 %) → Umidificazione adiabatica (AUTO) → Post-riscaldamento (AUTO) → Ventilatore (0,7 K).\n"
      "Con quota di aria esterna 100 % la riga «Miscela» non ha effetto (nota «Frazione di ricircolo 0»). "
      "Per una variante con umidificatore a vapore: sostituire «Umidificazione adiabatica» con «Umidificazione a vapore» (AUTO) e mettere «Nessuna» al posto del preriscaldamento."),

("H", "8. Formule delle proprietà dell'aria umida (ASHRAE Fundamentals 2017, cap. 1)"),
("F", "Pressione:      p = 101325·(1 − 2,25577·10⁻⁵·z)^5,2559  [Pa], z in m\n"
      "Saturazione:    acqua (t > 0,01 °C):\n"
      "                ln psat = C8/T + C9 + C10·T + C11·T² + C12·T³ + C13·ln T\n"
      "                ghiaccio (t ≤ 0,01 °C):\n"
      "                ln psat = C1/T + C2 + C3·T + C4·T² + C5·T³ + C6·T⁴ + C7·ln T\n"
      "                T = t + 273,15 K; coefficienti Hyland–Wexler (ASHRAE eq. 5–6)\n"
      "Umidità spec.:  x = 0,621945·pv/(p − pv)  [kg/kg a.s.];  pv = φ·psat\n"
      "Entalpia:       h = 1,006·t + x·(2501 + 1,86·t)  [kJ/kg a.s.]\n"
      "Vol. specifico: v = 0,287042·(t + 273,15)·(1 + 1,607858·x)/(p/1000)  [m³/kg]\n"
      "Densità:        ρ = (1 + x)/v  [kg/m³ aria umida]\n"
      "T di rugiada:   psat(Td) = pv  (Newton su ln psat, 3 passi da Magnus)\n"
      "T bulbo umido:  Tw ≥ 0: x = [(2501 − 2,326·Tw)·xs(Tw) − 1,006·(t − Tw)]\n"
      "                          / (2501 + 1,86·t − 4,186·Tw)\n"
      "                Tw < 0: 2830 − 0,24·Tw … / (2830 + 1,86·t − 2,1·Tw)\n"
      "                (Newton, 6 passi)\n"
      "Potenze:        Q = ṁ·Δh [kW];  Q_lat = ṁ·Δx·2501;  Q_sens = Q − Q_lat\n"
      "                acqua = ṁ·Δx·3600 [kg/h]"),
("P", "Le iterazioni sono scritte come colonne successive nel foglio «Calcoli» (nessuna macro, nessun calcolo iterativo, nessun riferimento circolare). "
      "Le formule sono le stesse della libreria psychrolib (ASHRAE 2017, unità SI)."),

("H", "9. Il diagramma di Mollier (foglio «Mollier»)"),
("P", "Il foglio «Mollier» mostra le STESSE trasformazioni del foglio «psicro» nel diagramma h–x di Mollier (forma usata nei testi europei e italiani). "
      "Gli stati sono gli stessi del foglio UTA: si cambia solo il sistema di coordinate, nessun calcolo è duplicato."),
("F", "Ascissa:   x [g/kg aria secca], 0…30 (come l'asse verticale del diagramma T–x)\n"
      "Ordinata:  Y = (h − 2501·x)/1,006 = T·(1 + 1,86·x/1,006) [°C], −10…50\n"
      "           a x = 0 la coordinata Y coincide con T: l'asse si legge in °C\n"
      "Isoterme:  Y = T·(1 + 1,849·x)  → rette quasi orizzontali, poco crescenti\n"
      "Isoentalpiche: Y = (h − 2,501·x[g/kg])/1,006 → rette oblique, −2,486 °C per g/kg\n"
      "Scala di bordo: q = Δh/Δx [kJ/kg]; direzione ΔY/Δx = (q − 2501)/1006 °C per g/kg\n"
      "Fattore termico: R ≈ 1 − 2501/q"),
("P", "Come si legge: un riscaldamento o raffreddamento sensibile è una retta VERTICALE (x costante); l'umidificazione adiabatica segue le rette blu di entalpia costante; "
      "l'umidificazione a vapore è quasi parallela alle isoterme; la miscela di due arie sta esattamente sul segmento che le congiunge (in h–x la regola della leva è esatta); "
      "la batteria fredda porta l'aria vicino alla curva di saturazione."),
("P", "Scala di bordo Δh/Δx: al posto del goniometro, sul bordo del grafico ci sono tacche con i valori del rapporto q = Δh/Δx [kJ/kg]. "
      "La direzione di una trasformazione con rapporto q è parallela alla retta che congiunge il POLO (punto x = 0, Y = 20 sull'asse sinistro) con la tacca q. "
      "q = 2501 è orizzontale, q = 0 è parallela alle isoentalpiche, q → ±∞ è verticale. "
      "I due raggi tratteggiati (blu = estate, rosso = inverno) partono dal polo con il rapporto Δh/Δx della retta ambiente A → I; la loro etichetta riporta anche il fattore termico R "
      "(R ≈ 1 − 2501/q). Si mostra q sulla scala e R nell'etichetta dei raggi perché un secondo goniometro in R, nel sistema obliquo, sarebbe meno leggibile."),
("H", "10. Valori tipici di progetto"),
("P", "• Esterno estate: Milano 32 °C / 50 %, Roma 33 °C / 45 %, Napoli 33 °C / 50 %, Palermo 34 °C / 50 %.\n"
      "• Esterno inverno: Milano −5 °C / 80 %, Torino −8 °C, Bologna −5 °C, Firenze 0 °C, Roma 0 °C, Napoli 2 °C (UNI EN 12831 / UNI 10349).\n"
      "• Ambiente: estate 24–27 °C, 45–60 %; inverno 20 °C, 40–50 % (il foglio parte da 20 °C / 40 %, come le pagine «Trattamento aria» del sito).\n"
      "• ΔT di immissione: estate 6–10 K; inverno 5–15 K (aria calda tende a stratificare).\n"
      "• Fattore di bypass batteria fredda: 4 ranghi ≈ 0,10–0,15; 6 ranghi ≈ 0,05; 8 ranghi ≈ 0,02.\n"
      "• Efficienza recuperatori: piastre a flussi incrociati 0,5–0,65, controcorrente 0,75–0,9, ruota entalpica 0,7–0,8 (εl 0,6–0,7), batterie accoppiate 0,4–0,6.\n"
      "• Ventilatori: ΔT 0,5–1 K.\n"
      "• Gradi giorno (DPR 412/93): Milano 2404, Torino 2617, Bologna 2259, Firenze 1821, Roma 1415, Napoli 1034, Palermo 751."),

("H", "11. Limiti e ipotesi"),
("P", "• Diagramma e calcoli validi nel campo −10…50 °C e 0…30 g/kg (le formule funzionano anche fuori, ma il grafico è ritagliato a quest'area).\n"
      "• Ricircolo sempre alle condizioni ambiente (nessun guadagno di calore nei canali di ripresa); una sola miscela per stagione (la prima riga «Miscela» decide la portata a monte).\n"
      "• Il recuperatore lavora a portate bilanciate con ripresa = ambiente; non si considerano brinamento e by-pass antigelo.\n"
      "• Batteria fredda con retta ingresso–ADP nel piano T–x (modello del fattore di bypass); l'entalpia della condensa è trascurata.\n"
      "• Umidificazione adiabatica a entalpia costante (differisce di meno di 0,1 K dalla trasformazione a bulbo umido costante).\n"
      "• Vicino a 0 °C l'equazione ASHRAE del bulbo umido ha una piccola discontinuità: la T di bulbo umido può differire di qualche decimo di grado da altri programmi in quella zona.\n"
      "• Il goniometro (foglio «psicro») presuppone un rapporto larghezza/altezza dell'area del grafico ≈ 1,6; ridimensionando il grafico le direzioni restano parallele ma il semicerchio si deforma.\n"
      "• La stima stagionale è solo indicativa (vedi nota sotto la tabella)."),

("H", "12. Correzioni rispetto al file originale (psicro.xls)"),
("P", "1. Potenza sensibile: la formula usava ΔT·cp·V/ρ con V in m³/h (unità errate; es. 1000 m³/h e ΔT = −2 K davano −1659 «W» invece di circa −675 W). Ora ṁ = V/(3600·v) [kg/s] e Q = ṁ·Δh [kW].\n"
      "2. La potenza latente non veniva mai calcolata e la formula inversa (T da potenza) era sbagliata: ora Q_lat = ṁ·Δx·2501 e le trasformazioni accettano la potenza come parametro alternativo.\n"
      "3. L'umidificazione adiabatica teneva costante la T (28 °C) con x fisso a 24 g/kg: ora avviene a entalpia costante (da 28 °C / 14,1 g/kg si arriva a ≈ 21,9 °C a saturazione).\n"
      "4. Serie del grafico «ser a» con intervalli X (5 celle) e Y (4 celle) disallineati e linee smussate: ora ogni serie ha X e Y della stessa lunghezza, linee rettilinee e marcatori.\n"
      "5. SCEGLI con 5 opzioni per 7 tipi di trasformazione (errori per «umid isot» e «miscela»); la miscela non era implementata e la portata di ricircolo non era usata: ora 11 tipi, tutti implementati, miscela con portate.\n"
      "6. La sezione estiva conteneva solo numeri scritti a mano: ora è interamente calcolata.\n"
      "7. Pressione fissa 101300 Pa indipendente dall'altitudine: ora p dipende dall'altitudine (con possibilità di imporla).\n"
      "8. Formula delle curve di UR con un termine spurio φ/Ps al denominatore: corretta (x = 0,621945·φ·psat/(p − φ·psat)).\n"
      "9. INDIRETTO(\"r[-1]c\";0) (volatile, notazione R1C1): sostituito da riferimenti normali.\n"
      "10. ρ = 1,21 e cp = 1,004 fissi: ora ρ = (1+x)/v e ṁ = V/v dallo stato reale, cp = 1,006 + 1,86·x.\n"
      "11. Colonne BF / EffU / Dispersioni termiche presenti ma inutilizzate: ora il fattore di bypass, le efficienze e le dispersioni entrano nei calcoli.\n"
      "Inoltre: pressione di saturazione Magnus sostituita con Hyland–Wexler (ASHRAE), aggiunte T di rugiada e di bulbo umido, punto di immissione dai carichi, verifiche e avvisi, note sulle celle, stima stagionale."),

("H", "13. Stampa"),
("P", "Tutti i fogli sono impostati per carta A4, con intestazione (nome del file e del foglio) e piè di pagina «Pagina n di N».\n"
      "• «UTA»: A4 orizzontale, 2 pagine (pagina 1 = dati generali + ESTATE con riepilogo; pagina 2 = INVERNO + stima stagionale), scala fissa 55 %. "
      "Si usa una scala fissa invece di «Adatta a 1 pagina di larghezza» perché con «Adatta a» Excel ignora le interruzioni di pagina manuali. "
      "La copia ridotta del diagramma (a destra delle tabelle) NON si stampa: per la stampa usare i fogli «psicro» e «Mollier». Per testi più grandi si può scegliere A3 (scala circa 75 %).\n"
      "• «psicro» e «Mollier»: una pagina A4 orizzontale ciascuno (grafico, legenda e tabella dei punti).\n"
      "• «Guida»: A4 verticale, larghezza adattata alla pagina.\n"
      "• «Calcoli»: una pagina A4 orizzontale con costanti, prime colonne del motore degli stati e grandezze di stagione (le colonne di iterazione non si stampano). «Liste» è nascosto."),
("H", "14. Registro delle modifiche"),
("P", "v2.2 (16/11/2026) – Citazione obbligatoria della licenza CC BY 4.0 «Fonte: EuGEnio – eugenio.statocritico.it» in cima a ogni foglio, sotto ogni grafico e nel piè di pagina di ogni pagina stampata: chi usa il foglio o ne riporta grafici e valori deve mantenerla."),
("P", "v2.1 (14/11/2026) – Nuovo foglio «Mollier» (diagramma h–x con isoterme, UR, entalpia, volume specifico, scala di bordo Δh/Δx con R, stesse trasformazioni del diagramma T–x); "
      "foglio «Diagramma» rinominato «psicro»; colori delle stagioni invertiti (ESTATE azzurro/blu, INVERNO rosso) in tabelle e grafici, spezzate più spesse; "
      "impostazioni di stampa A4 per tutti i fogli; testi dei parametri abbreviati; guida aggiornata (§9 Mollier, §13 Stampa)."),
("P", "v2.0 (13/11/2026) – Ricostruzione completa: foglio «UTA» con dati generali, sezioni estate/inverno, sequenze di 6 trasformazioni con preset e logica AUTO, riepiloghi e stima stagionale; "
      "nuovo diagramma psicrometrico (saturazione, UR 10–90 %, entalpia in kJ/kg, volume specifico, rette ambiente, goniometro del fattore termico, trasformazioni estate/inverno); "
      "proprietà ASHRAE 2017 con iterazioni senza macro; correzione dei punti elencati al §11; guida.\n"
      "v1.x – File originale psicro.xls (diagramma in kcal e kJ, tabella «trasf» con 4 trasformazioni per stagione)."),
]
