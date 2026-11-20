# Aggiornamento del 20/11/2026 – «Annulla iscrizione» senza blocchi

Pubblicazione sopra la `v2026.11.19f`. Sito **`?v=20261120a`**, release **`v2026.11.20`**, voce nelle Novità. Cambiano il
servizio (`fase4-server/servizio/avvisi.py`, `preferenze_email.py`), le prove, i testi per gli agenti e la versione delle
pagine. Sul server l'aggiornamento basta; in più va **sbloccato a mano** l'indirizzo di Paolo nella console di Oracle.

## Segnalazione di Paolo (20/11/2026, 07:26)

«Il collegamento per la modifica dell'iscrizione alla newsletter non parte più: verifica di Cloudflare, poi "Email non
spedita". Nei giorni scorsi funzionava.» Poi: «Sì, l'ho annullato io intenzionalmente per vedere se annullava. Non sapevo
fosse irreversibile. Bisogna aggiungere un collegamento annulla iscrizione in tutte le newsletter, altrimenti se l'utente le
annulla forzosamente con Gmail non potrà più reiscriversi.»

## Causa (dal registro dell'api)

`SMTPRecipientsRefused … (254, '4.7.1 - ing.paolo.bianco@gmail.com is suppressed for sender ocid1.emailsender…')`; il
login SMTP funziona. OCI Email Delivery aggiunge una sua intestazione `List-Unsubscribe` a ogni email che **non ne ha già
una HTTPS**; «Annulla iscrizione» di Gmail su quella mette l'indirizzo nella **lista di soppressione** di OCI e da lì OCI
rifiuta tutte le email per lui. I messaggi dei tre servizi avevano già la nostra intestazione e il collegamento «Cancellati
con un clic»; ne erano senza le email spedite direttamente dal server: il **collegamento personale** e le **email del
servizio** per l'amministratore.

## Cosa cambia

- Ogni email spedita direttamente ha la nostra intestazione HTTPS con `List-Unsubscribe-Post` (un clic, RFC 8058), così OCI
  non mette la sua:
  - collegamento personale → `POST /api/email/via-tutto?t=…`: toglie l'iscritto da tutti i servizi (gettone con il numero
    dell'iscritto, mai l'indirizzo); per chi non è ancora iscritto → `/api/email/servizio`;
  - email del servizio → `POST /api/email/servizio`, che non fa niente; in fondo all'email: «Non usare "Annulla
    iscrizione": si spengono togliendo EMAIL_AMMINISTRATORE».
- Indirizzo già nella lista di soppressione: la pagina dice che è bloccato dal servizio di posta e rimanda ai Contatti
  (invece di «Email non spedita»); all'amministratore arriva un'email con l'indirizzo e il percorso per sbloccarlo.
- I messaggi dei tre servizi restano come sono: «Cancellati con un clic» nel piè e «Annulla iscrizione» di Gmail che toglie
  solo da quel servizio, senza blocchi.
- Prove: fase 4 349 passate (2 nuove in `test_email_personali.py`); fase 5 pagine, agenti e Newsletter e avvisi nel
  browser 47 passate.

## Procedura AN1–AN4

### AN1. [Browser] Sblocca il tuo indirizzo in Oracle Cloud (se non l'hai già fatto)
1. Apri https://cloud.oracle.com e accedi; in alto a destra la regione deve essere **Italy Northwest (Milan)**.
2. Menu ☰ › **Developer Services** › **Email Delivery** › nel menu a sinistra **Suppression List**.
3. In «Compartment» scegli quello **radice** (col nome del tenancy).
4. Sulla riga di `ing.paolo.bianco@gmail.com` (motivo «Unsubscribe»): ⋮ › **Delete** › conferma.

### AN2. [Browser] Merge e release
1. Apri la pull request del ramo `claude/annulla-iscrizione` (collegamento di Claude), scheda **Files changed**, poi
   **Merge pull request** → **Confirm merge**.
2. Apri il collegamento `https://github.com/StatoCritico/eugenio/releases/new?…` già compilato da Claude (tag
   `v2026.11.20`) e premi **Publish release**.

### AN3. [Server] Aggiornamento
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa aspettarsi: `Aggiornamento da v2026.11.19f a v2026.11.20`, `Release v2026.11.20 installata` e il Purge di Cloudflare
fatto.

### AN4. [Browser] Prova
1. Apri https://eugenio.statocritico.it/dati-per-email.html con **Ctrl+F5**, scrivi il tuo indirizzo e premi «Mandami il
   collegamento»: deve comparire la conferma e l'email deve arrivare (la prima volta guarda anche in Spam).
2. In Gmail apri l'email › ⋮ › **Mostra originale**: la riga `List-Unsubscribe:` deve contenere
   `https://eugenio.statocritico.it/api/email/…` (non un indirizzo di Oracle).
3. Facoltativo, per provare il giro intero: «Annulla iscrizione» di Gmail su quell'email, poi di nuovo «Mandami il
   collegamento»: l'email deve arrivare ancora.
