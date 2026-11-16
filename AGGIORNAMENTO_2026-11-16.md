# Aggiornamento del 16/11/2026 – Trattamento aria: barra di scorrimento e scarico psicrometrico più robusto

Piccola pubblicazione sopra la `v2026.11.14b`. Sito **`?v=20261116a`**, release **`v2026.11.16`**.

## Cosa cambia

**Segnalazioni di Paolo del 16/11 mattina**
1. Le quattro pagine di **Trattamento aria** non avevano la barra di scorrimento della colonna sinistra come le altre
   pagine: la colonna (titolo, mappa, diagramma) scorreva con la pagina. Ora è ferma sotto la testata, alta quanto la
   finestra, e scorre da sola con la sua barra, come Legge 10 e le altre pagine a due colonne (`stile.css`: tolta la regola
   `.pagina-aria .mappa-area { position: static; height: auto; }`, mappa e diagramma non si schiacciano).
2. Il sottotitolo **«Psicrometria»** non cliccabile in cima al gruppo **resta** (decisione di Paolo del 16/11): raccoglie
   le quattro pagine e prepara i futuri sottotitoli «Unità di trattamento aria» e «Recuperatori».
2b. **Sitografia › Energia**: aggiunta **ASviS** (Alleanza Italiana per lo Sviluppo Sostenibile, `https://asvis.it`), tra le
   associazioni come FIRE (richiesta di Paolo del 16/11).

**Scarico dell'archivio psicrometrico (`scarica-psicro`), dopo la prima prova sul server del 15–16/11**
3. Lo scarico si era fermato alle 00:10 con `RuntimeError: Not an OM file` (anno 2026 del gruppo 9: Open-Meteo stava
   riscrivendo il file sul bucket). Ora `s3.leggi` dimentica dimensione e blocchi in cache di quel file e riprova fino a 3
   volte (dopo 30, 60 e 90 s); `FSBlocchi.dimentica(path)` è nuovo.
4. Il rilancio del mattino rifaceva tutti i comuni (`51 già completi` invece di ~3.200) perché la fine di ERA5 era
   avanzata di un giorno. Ora un comune conta come fatto anche se gli mancano al più **30 giorni** in fondo
   (`psicro.MARGINE_FINE`); le ore mancanti le aggiunge il lavoro notturno del worker (fino a 45 giorni).
5. `AGGIORNAMENTO_2026-11-14b.md`, Z8-A: i file di prova sono di ~170 KB (contengono già la serie corretta dal 2015 e
   ICON) e la pulizia vuole `sudo` (la cartella è dell'utente 1000).

## File toccati (rispetto alla `v2026.11.14b`)

- fase 3: `meteo_storico/s3.py` (letture riprovate, `dimentica`), `meteo_storico/psicro.py` (`MARGINE_FINE`), README;
- fase 4: `tests/test_psicro.py` (3 prove nuove);
- fase 5: `sito/stile.css`, `sito/sitografia.html` (ASviS), `novita.toml` (voce del 16/11) e `novita.html/xml`, tutte le pagine a `?v=20261116a`,
  `sito/EUGENIO_PER_AGENTI.md` e `sito/llms.txt`, README;
- `EUGENIO_PER_AGENTI.md` nella radice, `AGGIORNAMENTO_2026-11-14b.md` (Z8-A), questo file.

## Test (16/11/2026, container)

`fase4-server/tests/test_psicro.py` **19 passati**; fase 5 (costruzione delle pagine, menu, pagine di Trattamento aria,
file per gli agenti) passati; nel browser (Chromium, 1400×850) la colonna sinistra delle quattro pagine è `sticky`, alta
767 px, con contenuto di ~1.450–1.600 px che scorre da solo, come in Legge 10.

## Procedura AA1–AA5

**Quando**: il passo sul PC (AA1–AA2) subito; il passo sul server (AA3) **dopo la fine dello scarico** in corso
(`scarica-psicro` nella sessione tmux `psicro`): lo script ricostruisce l'immagine e riavvia api e worker, e non conviene
farlo mentre lo scarico gira.

### AA1. [PC] Applicare la patch
La patch `eugenio_2026-11-16.patch` è già **dentro il clone** (l'ha messa Claude; `git apply --check` pulito sopra il
commit `accce69` della `v2026.11.14b`); `git status` la mostra come `?? eugenio_2026-11-16.patch`.
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
git pull
```
```powershell
git status --short
```
```powershell
git apply --3way --whitespace=nowarn eugenio_2026-11-16.patch
```
```powershell
Move-Item eugenio_2026-11-16.patch ..\
```
```powershell
Select-String -Path fase5-sito\sito\index.html -Pattern "20261116a" -List | Measure-Object
```
Cosa aspettarsi: `Already up to date.`; da `git status` solo `?? eugenio_2026-11-16.patch`; righe `Applied patch …
cleanly` (e `Falling back to direct application...`, normale); `Count : 1`.

Cosa fare se va male: `with conflicts`, `error:` o `patch does not apply` → fermati e mandami l'uscita (per tornare
indietro: `git reset --hard` e `git clean -fd`).

### AA2. [PC] Commit, push e release `v2026.11.16`
```powershell
git add -A
```
```powershell
git status --short | Select-String -Pattern "fase2-gradi-giorno|uni_privato|(^|/)\.env$|\.patch$|psicro/.*\.parquet|__pycache__"
```
```powershell
git commit -m "16/11/2026: Trattamento aria con la barra di scorrimento della colonna sinistra; scarica-psicro riprova i file .om riscritti e non rifà i comuni quando la fine di ERA5 avanza; sito ?v=20261116a; procedura AGGIORNAMENTO_2026-11-16"
```
```powershell
git push
```
```powershell
python -c "import tomllib; v=tomllib.load(open('fase5-sito/novita.toml','rb'))['voce'][0]; g={'nuovo':'Nuovo','migliorato':'Migliorato','verificato':'Verificato'}; t=[v['titolo'],'','https://eugenio.statocritico.it/novita.html','']; [t.extend(['### '+g[k]]+['- '+x for x in v[k]]+['']) for k in g if v.get(k)]; open('../note_release_1116.md','w',encoding='utf-8').write(chr(10).join(t))"
```
```powershell
gh release create v2026.11.16 --target main --title "EuGEnio 16 novembre 2026 – Trattamento aria, barra di scorrimento" --notes-file ..\note_release_1116.md
```
Cosa aspettarsi: il secondo comando non stampa nulla; il push finisce con `… main -> main`; la release stampa
`…/releases/tag/v2026.11.16`.

### AA3. [Server] Aggiornamento da GitHub (a scarico finito)
```bash
ssh eugenio
```
```bash
tmux ls; ls /srv/energia/dati/psicro/.scarica_in_corso 2>/dev/null
```
Cosa aspettarsi: nessuna sessione `psicro` (o una sessione ferma con il JSON finale dello scarico) e nessun file
`.scarica_in_corso`. Se lo scarico gira ancora, aspetta.
```bash
~/energia/fase4-server/aggiorna_da_github.sh --prova
```
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa aspettarsi: `Aggiornamento da v2026.11.14b a v2026.11.16`, `Sito della release: ?v=20261116a`, codice: pochi file
(fase 3 e fase 4), sito: le pagine per la versione, `api e worker aggiornati e funzionanti`, `Purge di Cloudflare: fatto`
(o «fallo a mano»), `Release v2026.11.16 installata`.

Cosa fare se va male: `ERRORE: …` → mandami le ultime 30 righe di `~/aggiorna_da_github.log` (il server torna da solo
alla versione di prima).

### AA4. [Browser] La barra di scorrimento
`https://eugenio.statocritico.it/aria-ore.html` (Ctrl+F5), finestra larga (più di 861 px): la colonna sinistra resta
ferma sotto il menu e ha la sua barra sottile vicino al divisore; scorrendo la colonna sinistra si arriva al diagramma
senza che i passi di destra si muovano. Lo stesso nelle altre tre pagine di Trattamento aria. Sul telefono (una colonna)
nulla cambia. **Novità** → in cima la voce del 16/11. **Sitografia** → nel gruppo Energia c'è ASviS, il collegamento si apre.

### AA5. Da ricordare
Un nuovo `scarica-psicro` il giorno dopo non serve più `--al`: i comuni scaricati fino a 30 giorni prima della fine si
saltano. Un «Not an OM file» isolato ora lascia nel log una riga `s3: … illeggibile …, nuovo tentativo tra 30 s` e lo
scarico continua.

## Da riportare in RIEPILOGO.md e DA_FARE.md

- RIEPILOGO, riga di stato: «**16/11/2026** – sito `?v=20261116a`, release `v2026.11.16` (AA1–AA5): colonna sinistra di
  Trattamento aria con la sua barra di scorrimento; `scarica-psicro` riprova i file .om riscritti e salta i comuni con al
  più 30 giorni mancanti in fondo. Archivio psicrometrico dal 1940 sul server: primo scarico del 15–16/11 (ramo A, con la
  serie corretta dal 2015).»
- RIEPILOGO, decisioni di Paolo del 16/11: il sottotitolo «Psicrometria» non cliccabile resta; ASviS nella Sitografia, gruppo Energia.
- DA_FARE: [ ] **Paolo**: AA1–AA2 subito, AA3–AA4 a scarico finito; poi Z12, Z13 e Z15 di `AGGIORNAMENTO_2026-11-14b.md`.
