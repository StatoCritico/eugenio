# Dati di riferimento

`reference_cases.json` (e la versione leggibile `reference_cases.md`) sono valori calcolati con
**PsychroLib 2.5.0, unità SI** (https://github.com/psychrometrics/psychrolib), dallo script `make_reference.py`:

- griglia di stati a 0, 500 e 1000 m (T da −10 a 35 °C, UR 30–100 %): psat, x, h, v, T di rugiada, bulbo umido;
- casi UTA a–e (estate con e senza ricircolo, inverno con umidificazione adiabatica o a vapore, riscaldamento e
  umidificazione singoli), con le ipotesi scritte in `meta.assumptions` e le varianti di convenzione.

**Licenza di PsychroLib: MIT** («Copyright (c) 2018-2020 The PsychroLib Contributors… Licensed under the MIT License»,
intestazione di `psychrolib.py` 2.5.0; equazioni e coefficienti dall'ASHRAE Handbook – Fundamentals 2017). I numeri qui
sono un prodotto di calcolo usato solo per le prove; la libreria non è inclusa nel repository né usata dal sito.

Rigenerare: `pip install psychrolib==2.5.0` e `python3 make_reference.py` (scrive i due file accanto allo script).
