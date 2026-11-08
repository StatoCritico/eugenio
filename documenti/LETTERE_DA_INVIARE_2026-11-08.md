# Lettere da inviare – 08/11/2026

Fase 10 (edifici 3D). Lettere pronte da copiare e spedire da **eugenio@statocritico.it**. Il quadro completo (stato delle
fonti, motivazioni, Regioni senza lettera) è in `documenti/LETTERE_REGIONI_DB_TOPOGRAFICI.md`; qui ci sono solo le **14
lettere di questo invio**, brevi, con l'indirizzo controllato l'08/11/2026 su fonti ufficiali.

Come si usa:
1. Copiare **A**, **Oggetto** e **Testo** di ogni sezione nella posta.
2. Le **PEC** accettano di solito solo messaggi da un'altra PEC: per la Calabria (solo PEC) spedire da una casella PEC;
   per le altre usare l'indirizzo email ordinario.
3. Annotare la data di invio in `DA_FARE.md` (sezione «Dall'08/11/2026 notte») e, quando arriva una risposta, aggiornare
   `fase10-edifici3d/fonti/regioni.toml` (stato, licenza, motivo).

Tolte rispetto al 07/11: **Basilicata** (dati e servizi provati, IODL 2.0) e **Comune di Venezia** (licenza IODL 2.0
scritta nello scarico). Nessuna lettera al Comune di Genova. Valle d'Aosta e Molise restano in
`LETTERE_REGIONI_DB_TOPOGRAFICI.md` ma non sono in questo invio.

## Riepilogo

| # | Destinatario | Cosa si chiede | Priorità |
|---|---|---|---|
| 1 | Regione Piemonte – Settore Sistema informativo territoriale e ambientale | conferma scritta della CC BY 2.5 di UN_VOL (Torino è già online con quella); WCS del DTM ICE 2009-2011; licenza «Edifici 3D 2017» Arpa | **alta** |
| 2 | Regione Siciliana – SITR (Area 2 Interdipartimentale) | licenza del servizio `mdt_2013` (CC BY 4.0?); in alternativa cessione gratuita di DTM e DSM a 2 m | **alta** |
| 3 | Regione Calabria – Centro cartografico regionale (via PEC del Dipartimento) | licenza aperta o permesso per il DTM 5 m (Catanzaro); edifici della CTR/DBT con altezze | **alta** |
| 4 | Regione Emilia-Romagna – Archivio Cartografico | estrazione completa di UVL ed EDI per provincia o regione; DSM/LAS RER 2023-24; deroga per caricare le altezze in OpenStreetMap | **alta** |
| 5 | Regione Lazio – Area SITR | licenza scritta del DBGT 2020 (per Roma intera) | media |
| 6 | Regione Toscana – Settore Sistema Informativo e Pianificazione del Territorio | scarico e licenza dell'Edificato – unità volumetriche al 2023 | media |
| 7 | Regione FVG – IRDAT | scarico in blocco (o WCS) del LiDAR 2017-2020 e licenza; DBTsped; licenza degli strati CTRN | media |
| 8 | Regione Campania – UOS SIT | quote di gronda o UN_VOL della restituzione 2020; DSM; file regionale del DBT | media |
| 9 | Regione Puglia – titolare del dato e SIT Puglia | CTR più recente del 2006; DSM/LiDAR; licenza del DBT Multiscala | media |
| 10 | Regione Umbria – SIAT | edifici con altezze (CTR 1:2.000 di Perugia, DBGT 10k) e licenza | media |
| 11 | Regione Marche – Direzione Ambiente e Risorse idriche | unità volumetriche per corpo; DSM; DTM 2019 scaricabile | bassa |
| 12 | Regione Sardegna – Assessorato Enti Locali, Pianificazione urbanistica | altezze più complete (DBGT comunali o LiDAR dopo il 2008); dicitura di attribuzione | bassa |
| 13 | Regione Abruzzo – Servizio per l'Informazione Territoriale | DBTI 2007 1:5.000 (edifici con quote) e DTM 10 m con licenza aperta | bassa |
| 14 | Provincia autonoma di Bolzano – Ufficio Pianificazione territoriale e cartografia | edifici con altezze o 3D; aggiornamento del DSM 0,5 m | bassa |

Verifica degli indirizzi (08/11/2026): pagina ufficiale della Regione per Sicilia, Calabria, Emilia-Romagna, Lazio,
Campania, Marche, Abruzzo, FVG; scheda di metadati ufficiale (catalogo nazionale RNDT geodati.gov.it, Geoportale
INSPIRE o catalogo regionale) per Piemonte, Toscana, Puglia, Umbria, Sardegna, Bolzano. Le fonti sono indicate in ogni
sezione.

---

## 1. Regione Piemonte

**A:** Settore A1613B – Sistema informativo territoriale e ambientale – **cartografico@regione.piemonte.it**
(fonte: scheda RNDT di BDTRE UN_VOL, https://geodati.gov.it/resource/id/r_piemon:6dacd512-8862-491a-a37b-c032cd54d081,
e scheda INSPIRE della BDTRE, entrambe con questo indirizzo come punto di contatto)

**Oggetto:** BDTRE – conferma della licenza delle unità volumetriche e servizio del DTM – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco e curo EuGEnio (https://eugenio.statocritico.it), un servizio gratuito, senza scopo di lucro e open
> source (https://github.com/statocritico/eugenio) che costruisce modelli 3D degli edifici per analisi energetiche.
>
> Per Torino usiamo le unità volumetriche (UN_VOL) della BDTRE, scaricate dal servizio WFS `bdtre_imm`, con la licenza
> CC BY 2.5 indicata nel vostro comunicato del novembre 2017 per tutti i dati della BDTRE, citando sempre la Regione.
> La scheda di metadati di UN_VOL riporta però «condizioni sconosciute»: vi chiedo di confermare per iscritto che la
> CC BY 2.5 (o una licenza successiva, come la CC BY 4.0) vale anche per le unità volumetriche.
>
> Vi chiedo inoltre l'indirizzo del servizio WCS del DTM della ripresa ICE 2009-2011 (`wcs_ice_2009_2011_dtm`) o un
> collegamento per scaricarlo, con la sua licenza, e con quale licenza è distribuito il servizio Arpa Piemonte «Edifici
> 3D 2017», da cui vengono molte altezze di UN_VOL.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – Stato Critico / EuGEnio
> eugenio@statocritico.it – https://eugenio.statocritico.it – https://github.com/statocritico/eugenio

---

## 2. Regione Siciliana – SITR

**A:** Dipartimento dell'Urbanistica – Area 2 Interdipartimentale (SITR) – **area2.sitr@regione.sicilia.it**
(PEC del Dipartimento: dipartimento.urbanistica@certmail.regione.sicilia.it, solo se necessario; fonte:
https://www.sitr.regione.sicilia.it/contatti/)

**Oggetto:** Licenza del servizio DTM 2013 (mdt_2013) – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco e curo EuGEnio (https://eugenio.statocritico.it), un servizio gratuito, senza scopo di lucro e open
> source (https://github.com/statocritico/eugenio) che costruisce modelli 3D degli edifici per analisi energetiche.
>
> Dal SITR usiamo la CTR 2012-2013 in CC BY 4.0, che ha la quota di gronda degli edifici nella z dei vertici. Per
> ricavarne l'altezza ci serve la quota del terreno: vi chiedo con quale licenza è distribuito il servizio ImageServer
> del DTM 2013 (`mdt_2013`), che non ne riporta una, e se possiamo usarlo in CC BY 4.0, citando la Regione.
>
> Se il servizio non può essere usato con una licenza aperta, vi chiedo in alternativa se, trattandosi di un progetto
> senza scopo di lucro, è possibile la cessione gratuita del DTM e del DSM a 2 m (ATA 2012-2013), con una licenza che
> permetta di pubblicare le altezze degli edifici derivate.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – Stato Critico / EuGEnio
> eugenio@statocritico.it – https://eugenio.statocritico.it – https://github.com/statocritico/eugenio

---

## 3. Regione Calabria

**A:** Dipartimento Ambiente, Paesaggio e Qualità Urbana – Settore 8 – QTRP, Osservatorio delle Trasformazioni e del
Paesaggio, Politiche Territoriali e **Centro Cartografico Regionale** – **PEC dipartimento.lavoripubblici@pec.regione.calabria.it**
(solo PEC: spedire da una casella PEC; la vecchia PEC cartografico.urbanistica@pec.regione.calabria.it è dismessa dal
10/02/2026; fonte: avviso dell'11/02/2026,
https://www.regione.calabria.it/dismissione-indirizzo-pec-cartografico-urbanisticapec-regione-calabria-it/)

**Oggetto:** DTM 5×5 m e edifici della CTR – richiesta di licenza aperta o autorizzazione – c.a. Centro Cartografico
Regionale – EuGEnio

**Testo:**

> Gentili,
>
> vi chiedo cortesemente di inoltrare questa richiesta al Centro Cartografico Regionale. Sono Paolo Bianco e curo EuGEnio
> (https://eugenio.statocritico.it), un servizio gratuito, senza scopo di lucro e open source
> (https://github.com/statocritico/eugenio) che costruisce modelli 3D degli edifici per analisi energetiche.
>
> Per Catanzaro abbiamo scaricato alcuni riquadri del DTM 5×5 m regionale. La scheda dice che «la cessione diretta ad
> Enti terzi dei dati non è consentita salvo concessioni/autorizzazioni specifiche»: per ora lo useremmo solo per la
> quota a terra degli edifici, citando la Regione, senza ridistribuirlo né mostrarlo come terreno. Vi chiedo se il DTM
> 5×5 m può essere rilasciato con una licenza aperta (CC BY 4.0 o IODL 2.0) o, in alternativa, un'autorizzazione scritta
> per EuGEnio a usarlo per le quote degli edifici e per il terreno delle viste 3D.
>
> Vi chiedo anche se è possibile ricevere lo strato degli edifici della CTR / DB topografico regionale, con le altezze se
> disponibili, e con quale licenza.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – Stato Critico / EuGEnio
> eugenio@statocritico.it – https://eugenio.statocritico.it – https://github.com/statocritico/eugenio

---

## 4. Regione Emilia-Romagna – Archivio Cartografico

**A:** Archivio Cartografico – **archiviocart@regione.emilia-romagna.it**
(fonte: https://geoportale.regione.emilia-romagna.it/archivio-cartografico/dove-siamo)

**Oggetto:** DBTR (UVL ed EDI) per provincia o regione, DSM/LAS RER 2023-24 e altezze in OpenStreetMap – EuGEnio

**Testo:**

> Gentili,
>
> vi scrivo di nuovo dopo la mia email del 3 novembre. Sono Paolo Bianco e curo EuGEnio
> (https://eugenio.statocritico.it), un servizio gratuito, senza scopo di lucro e open source
> (https://github.com/statocritico/eugenio) che costruisce modelli 3D degli edifici per analisi energetiche, in
> particolare del patrimonio sanitario. Il DBTR è la nostra fonte principale: oggi lo usiamo per 28 comuni, tra cui
> Bologna, Rimini, Ravenna, Cesena, Forlì e Faenza.
>
> Il Geoportale permette di estrarre Unità volumetrica (UVL) ed Edificio (EDI) un comune alla volta, con un limite
> giornaliero. Vi chiedo:
>
> - l'estrazione completa di UVL ed EDI (con ingombro al suolo e destinazione d'uso) per provincia o per tutta la regione,
>   in GeoPackage EPSG:7791, con un collegamento unico;
> - il DSM e le nuvole LAS del rilievo RER 2023-24, anche solo per i comuni romagnoli, con le modalità che preferite;
> - un'autorizzazione (deroga) a caricare in OpenStreetMap le altezze degli edifici ricavate dal DBTR: la CC BY 4.0 chiede
>   l'attribuzione in un modo che OpenStreetMap accetta solo con un permesso esplicito del titolare (la Fondazione
>   OpenStreetMap ha un modulo apposito, «CC BY 4.0 waiver»).
>
> Vi chiedo anche di confermare la licenza del DBTR (la scheda RNDT indica CC BY 4.0, i metadati nell'estrazione CC BY
> 3.0). Citeremo sempre la Regione come fonte, senza presentare i dati come ufficiali.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – Stato Critico / EuGEnio
> eugenio@statocritico.it – https://eugenio.statocritico.it – https://github.com/statocritico/eugenio

---

## 5. Regione Lazio

**A:** Area Sistema Informativo Territoriale Regionale – **segreteriasitr@regione.lazio.it**
(PEC: sistema_inform_territoriale@pec.regione.lazio.it; fonte:
https://regione.lazio.it/cittadini/urbanistica/sistema-informativo-territoriale-regionale/consultazione-archivi)

**Oggetto:** DBGT 2020: licenza scritta – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco e curo EuGEnio (https://eugenio.statocritico.it), un servizio gratuito, senza scopo di lucro e open
> source (https://github.com/statocritico/eugenio) che costruisce modelli 3D degli edifici per analisi energetiche.
>
> Per Roma usiamo le unità volumetriche del DBGT 2014 (foglio 374), scaricate da dati.lazio.it in CC BY 4.0. Sul
> geoportale abbiamo trovato anche il DBGT 2020 per comune, ma non la sua licenza: vi chiedo di confermare per iscritto
> con quale licenza è distribuita l'edizione 2020 (per noi andrebbero bene CC BY 4.0 o IODL 2.0), così da usarla per
> tutto il comune al posto dell'edizione 2014.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – Stato Critico / EuGEnio
> eugenio@statocritico.it – https://eugenio.statocritico.it – https://github.com/statocritico/eugenio

---

## 6. Regione Toscana

**A:** Settore Sistema Informativo e Pianificazione del Territorio – **contatto.cartografia@regione.toscana.it**
(fonte: scheda del catalogo regionale «Edificato – unità volumetriche al 2023»,
https://www502.regione.toscana.it/geonetwork/srv/api/records/r_toscan:294be9db-ba10-4e2d-a890-89f87d00f30a)

**Oggetto:** Edificato – unità volumetriche al 2023: scarico e licenza – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco e curo EuGEnio (https://eugenio.statocritico.it), un servizio gratuito, senza scopo di lucro e open
> source (https://github.com/statocritico/eugenio) che costruisce modelli 3D degli edifici per analisi energetiche.
>
> Per Firenze usiamo l'Edificato multiscala con le unità volumetriche (WFS `owsedificato`, CC BY 4.0): confrontate con
> il LiDAR 2023 del Comune, le altezze sono molto buone. Nel catalogo c'è anche il nuovo strato «Edificato – unità
> volumetriche al 2023», ma è solo consultabile (WMS) e non abbiamo trovato come scaricarlo.
>
> Vi chiedo di poter ricevere la versione al 2023 per la Toscana o per provincia, con un collegamento o un servizio di
> download, di confermare che anche questa è in CC BY 4.0 e di dirmi se il campo dell'altezza indica la gronda, il colmo
> o la media.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – Stato Critico / EuGEnio
> eugenio@statocritico.it – https://eugenio.statocritico.it – https://github.com/statocritico/eugenio

---

## 7. Regione Friuli Venezia Giulia – IRDAT

**A:** IRDAT – Infrastruttura regionale di dati ambientali e territoriali – **irdat@regione.fvg.it**
(fonte: pagina IRDAT della Regione, «Per informazioni scrivi a irdat@regione.fvg.it»,
https://www.regione.fvg.it/rafvg/cms/RAFVG/ambiente-territorio/conoscere-ambiente-territorio/FOGLIA2/FOGLIA1/)

**Oggetto:** LiDAR 2017-2020: scarico in blocco e licenza; DBTsped e licenza degli strati CTRN – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco e curo EuGEnio (https://eugenio.statocritico.it), un servizio gratuito, senza scopo di lucro e open
> source (https://github.com/statocritico/eugenio) che costruisce modelli 3D degli edifici per analisi energetiche.
>
> Per Trieste usiamo l'Edificato CTRN (edizione 2) dal WFS IRDAT, con la CC BY 4.0 della scheda del servizio di
> download. Lo abbiamo confrontato con il LiDAR 2017-2020 su 7.327 edifici: scarto mediano +0,05 m, 82 % entro 2 m.
>
> Vi chiedo:
>
> - uno scarico in blocco (o un servizio WCS) dei DTM e DSM 0,5 m del LiDAR 2017-2020, oggi disponibili per elemento,
>   e la loro licenza scritta (le schede riportano «Use constraints: -»);
> - la conferma della licenza degli strati dell'Edificato CTRN (le schede dei singoli strati dicono «Non indicato»);
> - la copertura del DBTsped e l'origine del campo `ALTEZZA_M`.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – Stato Critico / EuGEnio
> eugenio@statocritico.it – https://eugenio.statocritico.it – https://github.com/statocritico/eugenio

---

## 8. Regione Campania

**A:** UOS SIT/Iter – Sistema Informativo Territoriale – **sit@regione.campania.it**
(PEC: sit@pec.regione.campania.it; fonte: https://sit.regione.campania.it/ufficio-sit/contatti)

**Oggetto:** DBT 2020: quote degli edifici, DSM e file regionale – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco e curo EuGEnio (https://eugenio.statocritico.it), un servizio gratuito, senza scopo di lucro e open
> source (https://github.com/statocritico/eugenio) che costruisce modelli 3D degli edifici per analisi energetiche.
>
> Per Napoli usiamo le sagome del DBT 2020 e il DTM 5 m in CC BY 4.0. Il DBT non ha quote di gronda né unità
> volumetriche, per cui oggi le altezze vengono dalle classi del Copernicus Urban Atlas 2012 o sono stimate. Vi chiedo:
>
> - se esistono, anche non pubblicate, le quote di gronda o le unità volumetriche della restituzione 2020, e se possiamo
>   riceverle con la stessa licenza;
> - se esiste un DSM (fotogrammetrico 2020 o LiDAR) per Napoli o per la regione;
> - se esiste un file regionale o provinciale del DBT.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – Stato Critico / EuGEnio
> eugenio@statocritico.it – https://eugenio.statocritico.it – https://github.com/statocritico/eugenio

---

## 9. Regione Puglia

**A:** **servizio.territorio@regione.puglia.it** (Regione Puglia, titolare dei dati), in copia **info@sit.puglia.it**
(InnovaPuglia – SIT Puglia, punto di contatto e distributore) (fonte: schede di metadati della Regione Puglia sul
Geoportale INSPIRE, per esempio
https://inspire-geoportal.ec.europa.eu/srv/api/records/r_puglia:9845c1ad-880f-4a47-94ba-a9ae893c880f/formatters/xml)

**Oggetto:** CTR 1:5.000: aggiornamenti dopo il 2006, DSM e licenza del DBT Multiscala – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco e curo EuGEnio (https://eugenio.statocritico.it), un servizio gratuito, senza scopo di lucro e open
> source (https://github.com/statocritico/eugenio) che costruisce modelli 3D degli edifici per analisi energetiche.
>
> Per Bari usiamo la CTR 1:5.000 (volo 2006) con i punti di gronda e al piede e il DTM 8 m, scaricati dal SIT in IODL
> 2.0, con buoni risultati. Vi chiedo se esiste una CTR o un DB topografico più recente, un DSM o un rilievo LiDAR
> regionale, e se possiamo riceverli con una licenza aperta. Vi chiedo anche con quale licenza è distribuito il «DBT
> Multiscala 2006», oggi indicato come «Dato pubblico».
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – Stato Critico / EuGEnio
> eugenio@statocritico.it – https://eugenio.statocritico.it – https://github.com/statocritico/eugenio

---

## 10. Regione Umbria

**A:** SIAT – Sistema informativo ambientale e territoriale – **umbriageo@regione.umbria.it**
(fonte: scheda RNDT «Fabbricati», https://geodati.gov.it/resource/id/r_umbria:00000:20160905:112000; il portale
UmbriaGeo non risponde dal nostro ambiente: se possibile ricontrollare l'indirizzo dal browser)

**Oggetto:** Edifici con altezze (CTR 1:2.000 di Perugia, DBGT 10k) e licenza – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco e curo EuGEnio (https://eugenio.statocritico.it), un servizio gratuito, senza scopo di lucro e open
> source (https://github.com/statocritico/eugenio) che costruisce modelli 3D degli edifici per analisi energetiche.
>
> Per Perugia non abbiamo trovato edifici con le altezze scaricabili. Nel catalogo ci sono la CTR vettoriale 1:2.000 del
> centro (volo 2000), i Fabbricati 2005-2010 (senza altezze) e il DB GeoTopografico 10k Tevere-Trasimeno. Vi chiedo se la
> CTR 1:2.000 contiene le quote di gronda e di poterla ricevere, insieme a uno strato degli edifici con le altezze per la
> regione, e con quale licenza (le schede indicano CC BY 3.0, dati.gov.it la CC BY 4.0).
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – Stato Critico / EuGEnio
> eugenio@statocritico.it – https://eugenio.statocritico.it – https://github.com/statocritico/eugenio

---

## 11. Regione Marche

**A:** Direzione Ambiente e Risorse idriche – Sistema cartografico regionale – **direzione.ambiente@regione.marche.it**
(PEC: regione.marche.acquasuolocosta@emarche.it; fonte:
https://www.regione.marche.it/Regione-Utile/Paesaggio-Territorio-Urbanistica/Cartografia)

**Oggetto:** DBGT 2019: unità volumetriche per corpo, DSM e DTM – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco e curo EuGEnio (https://eugenio.statocritico.it), un servizio gratuito, senza scopo di lucro e open
> source (https://github.com/statocritico/eugenio) che costruisce modelli 3D degli edifici per analisi energetiche.
>
> Per Ancona usiamo il DBGT 2019 (edificio e punto quotato, CC BY 4.0), che dà una sola quota di gronda per edificio.
> Vi chiedo se esistono unità volumetriche con l'altezza per corpo (per esempio dalla restituzione 1:2.000 dei centri
> urbani) e un DSM regionale, con la stessa licenza.
>
> Vi segnalo anche che lo scaricamento del DTM regionale (Orografia 2019) si interrompe dopo 100–240 MB e non riprende:
> un file compresso o diviso in parti ci aiuterebbe.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – Stato Critico / EuGEnio
> eugenio@statocritico.it – https://eugenio.statocritico.it – https://github.com/statocritico/eugenio

---

## 12. Regione Sardegna

**A:** Assessorato degli Enti Locali – Pianificazione urbanistica – **eell.urb.pianificazione@regione.sardegna.it**
(fonte: scheda RNDT del DBGT 10k, https://geodati.gov.it/resource/id/R_SARDEG:2c842f2a-d268-45e4-a68c-6cff2070bd28)

**Oggetto:** DBGT 10k: altezze degli edifici e attribuzione – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco e curo EuGEnio (https://eugenio.statocritico.it), un servizio gratuito, senza scopo di lucro e open
> source (https://github.com/statocritico/eugenio) che costruisce modelli 3D degli edifici per analisi energetiche.
>
> Usiamo in CC BY 4.0 gli edifici del DBGT 10k 2022 (WFS) e il LiDAR 2008 della fascia costiera, da cui ricaviamo le
> altezze di una parte di Cagliari. Vi chiedo se esistono altezze degli edifici più complete (DBGT comunali con le quote
> o un LiDAR più recente del 2008) e quale dicitura di attribuzione preferite per il DBGT e per il LiDAR.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – Stato Critico / EuGEnio
> eugenio@statocritico.it – https://eugenio.statocritico.it – https://github.com/statocritico/eugenio

---

## 13. Regione Abruzzo

**A:** Servizio per l'Informazione Territoriale e la Telematica – **infocartografia@regione.abruzzo.it**
(fonte: geoportale Cartanet, http://geoportale.regione.abruzzo.it/Cartanet)

**Oggetto:** DBTI 2007 1:5.000 (edifici con quote) e DTM 10 m – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco e curo EuGEnio (https://eugenio.statocritico.it), un servizio gratuito, senza scopo di lucro e open
> source (https://github.com/statocritico/eugenio) che costruisce modelli 3D degli edifici per analisi energetiche.
>
> Su Cartanet abbiamo visto che il DBTI 2007 alla scala 1:5.000 e il DTM 10 m sono «disponibili presso la Regione». Vi
> chiedo di poter ricevere lo strato degli edifici con le quote e il DTM per la regione o per provincia, e con quale
> licenza (per noi andrebbero bene CC BY 4.0 o IODL 2.0: «dato pubblico» non è una licenza).
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – Stato Critico / EuGEnio
> eugenio@statocritico.it – https://eugenio.statocritico.it – https://github.com/statocritico/eugenio

---

## 14. Provincia autonoma di Bolzano

**A:** Ufficio Pianificazione territoriale e cartografia – **cartografia@provincia.bz.it**
(fonte: scheda del DTM 0,5 m nel catalogo RNDT, https://geodati.gov.it/resource/id/p_bz:Elevation:DigitalTerrainModel-0.5m,
e geocatalogo provinciale)

**Oggetto:** Edifici INSPIRE con altezze e aggiornamento del DSM 0,5 m – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco e curo EuGEnio (https://eugenio.statocritico.it), un servizio gratuito, senza scopo di lucro e open
> source (https://github.com/statocritico/eugenio) che costruisce modelli 3D degli edifici per analisi energetiche.
>
> Usiamo con soddisfazione i vostri dati in CC0: gli edifici INSPIRE dal WFS e il DTM e il DSM a 0,5 m, da cui ricaviamo
> le altezze degli edifici di Bolzano. Vi chiedo se esiste una versione degli edifici con le altezze (gronda, colmo) o in
> 3D, e se e quando è previsto un aggiornamento del DSM 0,5 m: alcuni edifici recenti, come il nuovo corpo dell'ospedale
> di Bolzano, non vi compaiono ancora.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – Stato Critico / EuGEnio
> eugenio@statocritico.it – https://eugenio.statocritico.it – https://github.com/statocritico/eugenio
