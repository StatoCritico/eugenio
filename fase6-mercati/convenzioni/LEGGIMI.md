# Convenzioni

Qui vanno i file TOML delle convenzioni in uso (uno per convenzione). I modelli in `modelli/`
contengono la struttura e i campi `DA_COMPILARE`: copiarli qui e completarli.

Regole di prezzo disponibili: `indice_piu_spread`, `base_piu_delta_indice`, `fisso`, `prezzi_pubblicati`
(CSV `mese;fascia;prezzo` pubblicato dalla centrale). Indici utilizzabili: quelli di
`python -m mercati_energia indici` (PUN_MENSILE, PUN_F1/F2/F3/F23, PZ_<zona>, PSV_MGPGAS_MENSILE,
IGI_MENSILE, TTF_MENSILE) più quelli importati da CSV (es. PSV_DA).

Per aggiungere un'altra centrale (Consip, Aria Lombardia, SCR Piemonte, Soresa, ...) basta un nuovo file:
nessuna modifica al codice.

## Sorveglianza notturna

Ogni notte il server controlla le pagine elencate in `fonti/centrali.toml` (elenchi di convenzioni e gare) e quelle
nella sezione `[sorveglianza]` di ogni file, scarica i documenti nuovi e confronta i valori trovati con le regole
`[[sorveglianza.valore]]`. Email solo quando cambia qualcosa. Dettagli nel README della fase 6. `fonti/` sta in
una sottocartella perché i `*.toml` di questa cartella sono letti come convenzioni.

## File compilati (26/10/2026)

| File | Periodo | Stato |
|---|---|---|
| `intercenter_ee19_2026.toml` | 2026 | verificata su capitolato, convenzione e determina 401/2025; sorveglianza con regole sugli spread |
| `intercenter_ee20_2027.toml` | 2027 | da pagina, capitolato e listini EE20 |
| `intercenter_gn23_2026_27.toml` | 10/2026 – 9/2027 | lotto 1, da capitolato e listini GN23; indice PSV_DA = CMEM ARERA verificato |
| `intercenter_gn23_cogen_2027.toml` | 2027 | lotto 2 cogenerazione; indice giornaliero ponderato approssimato con la media mensile |
| `cet_ee_2026.toml` | 2026 | spread 2026 dalla comunicazione CET ai soci del 29/10/2025 (corretti il 26/10/2026: prima c'erano quelli del 2025); nessun corrispettivo fisso o di potenza del fornitore |
| `cet_gas_2025_26.toml` | 10/2025 – 9/2026 | spread dalla presentazione CET; PCS standard perché quello del capitolato non è pubblico |

Ogni valore ha la fonte nel commento accanto. Prima di usare un risultato per una decisione, ricontrollare
spread e periodo sulla guida alla convenzione o sul listino in vigore: le centrali li aggiornano.
