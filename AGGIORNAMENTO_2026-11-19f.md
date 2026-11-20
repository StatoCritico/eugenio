# Aggiornamento del 19/11/2026 f – psicro_UTA.xlsx con la grafica originale dei diagrammi

Pubblicazione sopra la `v2026.11.19e`. Sito **`?v=20261119f`**, release **`v2026.11.19f`**, voce nelle Novità. Cambiano il
foglio scaricabile `strumenti/psicro_UTA.xlsx` (v2.3), il suo generatore e la sua guida (fase 14), la versione di tutte le
pagine e i testi per gli agenti: niente da fare a mano sul server oltre all'aggiornamento.

## Richiesta di Paolo (19/11/2026)

«Perché hai modificato il layout del diagramma psicrometrico del mio file excel psicro originale? Ti avevo detto di
mantenerlo uguale. Ok per il grafico che hai aggiunto nel foglio delle trasformazioni, ma nel foglio psicro e nel foglio
Mollier lo stile, il layout e la grafica vanno ripristinati quelli originali.» – «Sì, usa lo stesso stile del mio per il
diagramma di Mollier.» Dopo il primo confronto: «1 ok dritte, 2 rifallo identico, 3 va bene così, 4 sì aggiungile».

## Cosa cambia

- Fogli «psicro» e «Mollier» con la grafica di `psicro_finale.xls`: fondo bianco con bordo nero, griglia nera (continua
  ogni 5, tratteggiata ogni 1), curve nere (saturazione 3 pt, le altre 1 pt), niente titoli degli assi, numeri dell'asse
  verticale a destra, Arial 10, estate rossa e inverno blu spessi 3 pt; A3 orizzontale con il diagramma grande
  (35,2 × 23,2 cm) in pagina 1, legenda e tabella dei punti in pagina 2.
- Nel T–x tornano le famiglie di curve dell'originale (asse obliquo delle entalpie, isoentalpiche in kcal/kg e in kJ/kg,
  isocore 0,78…0,95 m³/kg) e il goniometro identico: due semicerchi centrati in (0; 30), rombi del fattore termico R,
  quadrati di Δh/Δx, ⊗ al centro, ∞; i due raggi spessi sono le direzioni A → I di progetto.
- **Scritte dell'originale nelle stesse posizioni** (20/11, Paolo con lo screenshot di Excel: «rimettile in tutte le
  posizioni, sia in psicro che in mollier»): valori delle isoentalpiche in kcal e kJ, «h[kcal]», «h[kJ]», volumi, UR 10…90 %,
  scale del goniometro, «∆hs/∆htot», «∆h/∆x», «x(g/Kg)», «T (C°)». Volumi e UR si spostano con la pressione del comune.
  Unità della scala Δh/Δx scritta «kJ/g» (nell'originale «kcal/kgh2o», ma i valori sono kJ/g).
- **Mollier** con le stesse famiglie di curve e le stesse scritte del T–x, portate nelle sue coordinate, più isoterme ogni
  5 °C, scala di bordo Δh/Δx e polo.
- Trasformazioni rettilinee (decisione di Paolo: l'originale le smussava e la curva passava oltre la saturazione).
- La copia ridotta nel foglio UTA resta com'era (a colori, estate
  blu e inverno rosso come le tabelle).
- Nessuna cella di ingresso o di risultato cambia (`cellmap.json` invariato): il blocco delle nuove curve è in fondo al
  foglio «Calcoli». Verifica: 414/414 controlli, 0 errori di formula dopo il ricalcolo, prove della fase 14 passate.

## Procedura AM1–AM3

### AM1. [Browser] Merge e release
1. Apri la pull request del ramo `claude/psicro-stile-originale` (collegamento di Claude), scheda **Files changed**, poi
   **Merge pull request** → **Confirm merge**.
2. Apri il collegamento `https://github.com/StatoCritico/eugenio/releases/new?…` già compilato da Claude (tag
   `v2026.11.19f`) e premi **Publish release**.

### AM2. [Server] Aggiornamento
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa aspettarsi: `Aggiornamento da v2026.11.19e a v2026.11.19f`, `Release v2026.11.19f installata` e il Purge di Cloudflare
fatto.

### AM3. [Browser] Prova
1. Apri https://eugenio.statocritico.it/aria-trasformazioni.html con **Ctrl+F5** e scarica il foglio Excel (vuoto e compilato).
2. Foglio «psicro»: diagramma grande con fondo bianco, griglia e curve nere, semicerchi del goniometro in alto a sinistra con
   ⊗ e ∞, estate rossa e inverno blu. Anteprima di stampa: A3 orizzontale, diagramma in pagina 1, legenda in pagina 2.
3. Foglio «Mollier»: stesso stile, con le etichette. Foglio «UTA»: risultati uguali a prima, copia ridotta a colori.
