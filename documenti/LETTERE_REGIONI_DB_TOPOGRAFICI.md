# Lettere alle Regioni: database topografici degli edifici con le altezze

Data: 07/11/2026, aggiornato l'08/11/2026 (sera) dopo le città di riferimento, i lettori regionali e la verifica degli indirizzi · **Testi brevi pronti da spedire: `documenti/LETTERE_DA_INVIARE_2026-11-08.md`** (14 lettere con priorità) · Fase 10 (edifici 3D) · Fonte dell'elenco: `fase10-edifici3d/fonti/regioni.toml` (verifica dell'08/11/2026) e `documenti/CITTA_RIFERIMENTO_*.md`

## A cosa serve

Questo documento raccoglie le email da mandare agli uffici cartografici delle Regioni e delle Province autonome per chiedere **l'estrazione completa (regionale o per provincia) del database topografico degli edifici con le altezze** (unità volumetriche o equivalenti). Sono le Regioni che in `regioni.toml` hanno il tema «edifici» in stato «in attesa» o «non disponibile», più l'Emilia-Romagna, dove il dato è aperto ma si scarica solo un comune alla volta. **Aggiornamento dell'08/11/2026**: dove le città di riferimento hanno trovato dati scaricabili con licenza aperta (Lazio, Piemonte, Toscana, Marche, Puglia, Campania, Sardegna, Bolzano, Basilicata, FVG) le lettere sono state ridotte alle sole domande rimaste (licenza scritta, versione più recente, DSM, scarico in blocco); la **Basilicata** non ha più una lettera (dati e servizi provati, IODL 2.0). Per il **Comune di Venezia** non serve una lettera: il DBGT comunale con le unità volumetriche si scarica dalla Carta Tecnica di dati.venezia.it con la licenza IODL 2.0 scritta nello scarico. Per il **Comune di Genova** nessuna lettera.

Come si usa:

1. Per ogni Regione copiare **Oggetto** e **Testo** e spedirli da eugenio@statocritico.it all'indirizzo della tabella.
2. Gli indirizzi **PEC** di solito accettano solo messaggi da un'altra PEC: se non si spedisce da una casella PEC, usare l'indirizzo email ordinario quando c'è (per Calabria e Molise c'è solo la PEC o nessun indirizzo verificato).
3. Prima di spedire alle Regioni segnate «da verificare» o «solo scheda di metadati», controllare l'indirizzo dal browser (diversi portali del Centro-Sud non rispondono dal nostro ambiente di sviluppo, che è fuori Italia).
4. Annotare in `DA_FARE.md` la data di invio. Quando arriva una risposta, aggiornare stato, licenza e motivo in `regioni.toml`.

Le lettere non riportano dati personali oltre al nome e all'email di progetto, e non contengono segreti.

## Riepilogo

Legenda della colonna «Stato dell'indirizzo»:
- **verificato**: indirizzo letto su una pagina della Regione o del suo geoportale il 07/11/2026;
- **scheda di metadati**: indirizzo letto in una scheda di metadati ufficiale pubblicata dalla Regione (RNDT o catalogo regionale), perché il portale non risponde dal nostro ambiente; va ricontrollato prima dell'invio;
- **da verificare**: nessun indirizzo d'ufficio trovato; c'è il link della pagina più vicina.

| Regione | Prodotto richiesto | Destinatario | Indirizzo | Fonte dell'indirizzo | Stato dell'indirizzo |
|---|---|---|---|---|---|
| Emilia-Romagna | DBTR: EDI_GPG, UVL_GPG, EDI_GPGSA, EDI_CT_USO_AVM (provincia o regione); DSM/LAS RER 2023-24; deroga per le altezze in OpenStreetMap | Archivio Cartografico | archiviocart@regione.emilia-romagna.it | [Geoportale RER – Archivio, Dove siamo](https://geoportale.regione.emilia-romagna.it/archivio-cartografico/dove-siamo) | verificato |
| Piemonte | conferma della CC BY 2.5 di UN_VOL; URL del WCS del DTM ICE 2009-2011; licenza «Edifici 3D 2017» Arpa | Settore A1613B Sistema informativo territoriale e ambientale | cartografico@regione.piemonte.it | [Scheda RNDT BDTRE UN_VOL](https://geodati.gov.it/resource/id/r_piemon:6dacd512-8862-491a-a37b-c032cd54d081) e scheda INSPIRE della BDTRE (08/11) | scheda di metadati (ricontrollata l'08/11) |
| Valle d'Aosta | CTRN – Fabbricati; Edificato 2018 | Ufficio cartografico | u-cartografia@regione.vda.it (PEC: difesa_suolo@pec.regione.vda.it) | [Geoportale SCT – contatti](https://geoportale.regione.vda.it/?p=6633) | verificato |
| P.A. Bolzano | versione con altezze o 3D degli edifici INSPIRE; aggiornamento del DSM 0,5 m | Ufficio Pianificazione territoriale e cartografia | cartografia@provincia.bz.it | [Geocatalogo provinciale, scheda DTM 0,5 m](https://geonetwork1.civis.bz.it/geonetwork/srv/api/records/p_bz:Elevation:DigitalTerrainModel-0.5m) | verificato (catalogo provinciale) |
| Toscana | solo la versione «al 2023» dell'Edificato (scarico e licenza) | Settore Sistema Informativo e Pianificazione del Territorio | contatto.cartografia@regione.toscana.it | [Catalogo regionale, scheda Edificato 2023](https://www502.regione.toscana.it/geonetwork/srv/api/records/r_toscan:294be9db-ba10-4e2d-a890-89f87d00f30a) | verificato (catalogo regionale) |
| Umbria | CTR 1:2.000 di Perugia con quote; Fabbricati 2005-2010; DBGT 10k Tevere-Trasimeno; CC BY 3.0/4.0 | SIAT – Sistema informativo ambientale e territoriale | umbriageo@regione.umbria.it | [Scheda RNDT Fabbricati](https://geodati.gov.it/resource/id/r_umbria:00000:20160905:112000) | scheda di metadati |
| Marche | unità volumetriche per corpo (oltre la gronda per edificio del DBGT 2019); DSM | Direzione Ambiente e Risorse idriche – Sistema cartografico regionale | direzione.ambiente@regione.marche.it (PEC: regione.marche.acquasuolocosta@emarche.it) | [Regione Marche – Cartografia](https://www.regione.marche.it/Regione-Utile/Paesaggio-Territorio-Urbanistica/Cartografia) | verificato |
| Lazio | solo la licenza scritta del DBGT 2020 (e versione della CC BY del DTM 2002-03) | Area Sistema Informativo Territoriale Regionale | segreteriasitr@regione.lazio.it (PEC: sistema_inform_territoriale@pec.regione.lazio.it) | [Regione Lazio – SITR, consultazione archivi](https://regione.lazio.it/cittadini/urbanistica/sistema-informativo-territoriale-regionale/consultazione-archivi) | verificato |
| Abruzzo | DBTI 2007 1:5.000 in SHP (edifici con quote) e DTM 10 m 2007, licenza aperta | Servizio per l'Informazione Territoriale e la Telematica | infocartografia@regione.abruzzo.it | [Cartanet – Geoportale Abruzzo](http://geoportale.regione.abruzzo.it/Cartanet) | verificato |
| Molise | DBT / CTR regionale – edifici | da individuare (cartografia regionale) | indirizzo da verificare | pagina più vicina: [www.regione.molise.it](https://www.regione.molise.it/) | da verificare |
| Campania | quote di gronda o UN_VOL della restituzione 2020; DSM; file unico regionale | UOS SIT/Iter – Sistema Informativo Territoriale | sit@regione.campania.it (PEC: sit@pec.regione.campania.it) | [Geoportale Campania – Contatti](https://sit.regione.campania.it/ufficio-sit/contatti) | verificato |
| Puglia | aggiornamento della CTR dopo il 2006; DSM/LiDAR; licenza del DBT Multiscala | Servizio regionale competente (titolare) e SIT Puglia (InnovaPuglia) | servizio.territorio@regione.puglia.it; info@sit.puglia.it | [Scheda RNDT DTM Puglia](https://geodati.gov.it/resource/id/r_puglia:85898eba-d4b0-4c3b-a2c7-6ea666522591) | scheda di metadati |
| Friuli Venezia Giulia | scarico in blocco (o WCS) del LiDAR 2017-2020 e sua licenza; DBTsped; licenza degli strati CTRN | IRDAT | irdat@regione.fvg.it | [Regione FVG – IRDAT](https://www.regione.fvg.it/rafvg/cms/RAFVG/ambiente-territorio/conoscere-ambiente-territorio/FOGLIA2/FOGLIA1/) | verificato (08/11) |
| Calabria | licenza aperta o permesso per il DTM 5×5 m (Catanzaro); DBT / CTR regionale – edifici | Dip. Ambiente, Paesaggio e Qualità Urbana – Settore 8 – QTRP e Centro cartografico regionale | PEC: dipartimento.lavoripubblici@pec.regione.calabria.it | [Regione Calabria – avviso PEC del Centro cartografico](https://www.regione.calabria.it/dismissione-indirizzo-pec-cartografico-urbanisticapec-regione-calabria-it/) | verificato (solo PEC) |
| Sicilia | licenza del servizio `mdt_2013` (CC BY 4.0?); in alternativa cessione gratuita di DTM e DSM a 2 m | Dip. Urbanistica – Area 2 Interdipartimentale (SITR) | area2.sitr@regione.sicilia.it (PEC: dipartimento.urbanistica@certmail.regione.sicilia.it) | [SITR – Contatti](https://www.sitr.regione.sicilia.it/contatti/) | verificato |
| Sardegna | altezze (DBGT comunali con quote o LiDAR dopo il 2008); dicitura di attribuzione | Assessorato Enti Locali – Pianificazione urbanistica | eell.urb.pianificazione@regione.sardegna.it | [Scheda RNDT DBGT 10k](https://geodati.gov.it/resource/id/R_SARDEG:2c842f2a-d268-45e4-a68c-6cff2070bd28) | scheda di metadati |

Riassunto (08/11/2026 sera): 16 lettere, di cui **14 in questo invio** (`LETTERE_DA_INVIARE_2026-11-08.md`; Valle d'Aosta e Molise restano qui, non in questo invio). **9 verificati** su pagine della Regione (Emilia-Romagna, Valle d'Aosta, Marche, Lazio, Abruzzo, Campania, Calabria, Sicilia, Friuli Venezia Giulia: ricontrollati l'08/11), **2 verificati** sul catalogo di metadati della Regione o Provincia (Toscana, Bolzano), **4 da scheda RNDT o INSPIRE** (Piemonte, Umbria, Puglia, Sardegna: ricontrollati l'08/11), **1 da verificare** (Molise). Basilicata tolta (fonte attiva, nessuna lettera); Comune di Venezia e Comune di Genova: nessuna lettera.

---

## Emilia-Romagna

**Destinatario:** Archivio Cartografico – archiviocart@regione.emilia-romagna.it

**Oggetto:** DBTR (Edificio, Unità volumetrica, uso) per provincia o regione, DSM/LAS RER 2023-24 e altezze in OpenStreetMap – EuGEnio

**Testo:**

> Gentili,
>
> vi scrivo di nuovo dopo la mia email del 3 novembre su DSM, nuvole LAS e ortofoto. Sono Paolo Bianco, ingegnere, e curo EuGEnio, un servizio gratuito e open source (AGPL-3.0) del progetto personale Stato Critico, senza scopo di lucro. EuGEnio costruisce modelli 3D degli edifici per analisi energetiche: ombre, fotovoltaico, fabbisogno, priorità di intervento sul patrimonio pubblico, in particolare sanitario. Il Database Topografico Regionale è la nostra fonte principale; OpenStreetMap è solo un ripiego.
>
> Il Geoportale permette di estrarre i layer Edificio (EDI_GPG) e Unità volumetrica (UVL_GPG) un comune alla volta, con un limite giornaliero: per i 330 comuni servirebbero settimane. Vi chiedo quindi l'estrazione completa, per provincia o regionale, di EDI_GPG, UVL_GPG, EDI_GPGSA (ingombro al suolo) ed EDI_CT_USO_AVM (destinazione d'uso), in GeoPackage EPSG:7791, con un collegamento unico o su disco.
>
> Vi chiedo inoltre il DSM e le nuvole LAS del rilievo RER 2023-24 (anche solo per i comuni romagnoli) e un'autorizzazione (deroga) a caricare in OpenStreetMap le altezze degli edifici ricavate dal DBTR: OpenStreetMap accetta dati in CC BY 4.0 solo con un permesso esplicito del titolare (modulo «CC BY 4.0 waiver» della Fondazione OpenStreetMap).
>
> Vi chiedo anche di confermare per iscritto la licenza: la scheda RNDT indica CC BY 4.0, mentre i metadati XML dentro l'estrazione indicano CC BY 3.0. Mi farebbe piacere sapere anche ogni quanto viene aggiornato il DBTR e se esiste già un download regionale in blocco che non ho trovato.
>
> Citeremo sempre fonte e licenza della Regione, senza presentare i dati come ufficiali; l'archivio derivato sarà pubblicato con la stessa licenza, senza uso commerciale, e il codice è pubblico.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – EuGEnio, un servizio di Stato Critico – eugenio@statocritico.it – https://eugenio.statocritico.it

---

## Piemonte

**Destinatario:** Settore A1613B Sistema informativo territoriale e ambientale – cartografico@regione.piemonte.it (indirizzo della scheda RNDT: ricontrollarlo su geoportale.piemonte.it prima dell'invio, dal browser: dal nostro ambiente il geoportale non risponde)

**Oggetto:** BDTRE – conferma della licenza CC BY 2.5 delle unità volumetriche e servizio del DTM – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco, ingegnere, e curo EuGEnio, un servizio gratuito e open source (AGPL-3.0) del progetto personale Stato Critico, senza scopo di lucro. EuGEnio costruisce modelli 3D degli edifici per analisi energetiche: ombre, fotovoltaico, fabbisogno e priorità di intervento sul patrimonio pubblico, in particolare sanitario. Usiamo i database topografici regionali come fonte principale e OpenStreetMap solo come ripiego.
>
> Abbiamo scaricato dal servizio WFS `bdtre_imm` le unità volumetriche (UN_VOL) di Torino e le stiamo usando per il modello 3D della città, citando la Regione e la licenza CC BY 2.5 indicata nel vostro comunicato del novembre 2017 per tutti i dati della BDTRE. La scheda di metadati di UN_VOL riporta però «condizioni sconosciute»: vi chiedo di confermare per iscritto che la CC BY 2.5 (o una licenza successiva, come la CC BY 4.0 della scheda generale della BDTRE) vale anche per le unità volumetriche.
>
> Per le quote del terreno ci servirebbe il DTM della ripresa ICE 2009-2011: vi chiedo l'indirizzo del servizio WCS (`wcs_ice_2009_2011_dtm`) o di un download, con la licenza. Vi chiedo anche con quale licenza è distribuito il servizio Arpa Piemonte «Edifici 3D 2017», da cui vengono molte altezze di UN_VOL, e se esiste uno scarico in blocco della BDTRE (per provincia o regionale) che non ho trovato.
>
> Citeremo sempre fonte e licenza della Regione, senza presentare i dati come ufficiali; l'archivio derivato sarà pubblicato con la stessa licenza, senza uso commerciale, e il codice è pubblico.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – EuGEnio, un servizio di Stato Critico – eugenio@statocritico.it – https://eugenio.statocritico.it

---

## Valle d'Aosta

**Destinatario:** Ufficio cartografico – u-cartografia@regione.vda.it

**Oggetto:** Richiesta di dati sugli edifici con altezze (CTRN – Fabbricati, Edificato 2018) – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco, ingegnere, e curo EuGEnio, un servizio gratuito e open source (AGPL-3.0) del progetto personale Stato Critico, senza scopo di lucro. EuGEnio costruisce modelli 3D degli edifici per analisi energetiche: ombre, fotovoltaico, fabbisogno e priorità di intervento sul patrimonio pubblico, in particolare sanitario. Usiamo i database topografici regionali come fonte principale e OpenStreetMap solo come ripiego.
>
> Nel catalogo abbiamo trovato i Fabbricati della CTRN e l'Edificato 2018 da ortofoto, entrambi in CC BY, ma senza altezze. Vi chiedo se esiste una versione con le altezze degli edifici (quota di gronda, altezza o unità volumetriche) e, in ogni caso, di poter ricevere gli edifici per l'intera regione in un unico file, preferibilmente GeoPackage nel sistema di riferimento ufficiale regionale, tramite un collegamento o un FTP.
>
> Vi chiedo anche di confermare per iscritto la licenza (CC BY 4.0, come indicato nel repertorio SCT?), di dirmi ogni quanto vengono aggiornati questi dati e se esiste già un download regionale in blocco che non ho trovato.
>
> Citeremo sempre fonte e licenza della Regione, senza presentare i dati come ufficiali; l'archivio derivato sarà pubblicato con la stessa licenza, senza uso commerciale, e il codice è pubblico.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – EuGEnio, un servizio di Stato Critico – eugenio@statocritico.it – https://eugenio.statocritico.it

---

## Provincia autonoma di Bolzano

**Destinatario:** Ufficio Pianificazione territoriale e cartografia – cartografia@provincia.bz.it

**Oggetto:** Edifici INSPIRE: versione con altezze e aggiornamento del DSM 0,5 m – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco, ingegnere, e curo EuGEnio, un servizio gratuito e open source (AGPL-3.0) del progetto personale Stato Critico, senza scopo di lucro. EuGEnio costruisce modelli 3D degli edifici per analisi energetiche: ombre, fotovoltaico, fabbisogno e priorità di intervento sul patrimonio pubblico, in particolare sanitario. Usiamo i database topografici regionali come fonte principale e OpenStreetMap solo come ripiego.
>
> Usiamo già con soddisfazione i vostri dati in CC0: le sagome degli edifici INSPIRE (Building e BuildingPart, dal servizio WFS), il DTM e il DSM a 0,5 m, da cui ricaviamo le altezze degli edifici di Bolzano, e l'ortofoto 2023, citandone sempre la fonte. Il servizio WFS degli edifici è in 2D, mentre la descrizione del dato parla di un livello di dettaglio più alto: vi chiedo se esiste una versione degli edifici con le altezze (gronda, colmo) o in 3D e se è possibile riceverla.
>
> Vi chiedo anche se e quando è previsto un aggiornamento del DSM 0,5 m: alcuni edifici recenti, come il nuovo corpo dell'ospedale di Bolzano, non vi compaiono ancora.
>
> Citeremo sempre fonte e licenza della Provincia, senza presentare i dati come ufficiali; l'archivio derivato sarà pubblicato con la stessa licenza, senza uso commerciale, e il codice è pubblico.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – EuGEnio, un servizio di Stato Critico – eugenio@statocritico.it – https://eugenio.statocritico.it

---

## Toscana

**Destinatario:** Settore Sistema Informativo e Pianificazione del Territorio – contatto.cartografia@regione.toscana.it

**Oggetto:** Edificato – unità volumetriche al 2023: scarico e licenza – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco, ingegnere, e curo EuGEnio, un servizio gratuito e open source (AGPL-3.0) del progetto personale Stato Critico, senza scopo di lucro. EuGEnio costruisce modelli 3D degli edifici per analisi energetiche: ombre, fotovoltaico, fabbisogno e priorità di intervento sul patrimonio pubblico, in particolare sanitario. Usiamo i database topografici regionali come fonte principale e OpenStreetMap solo come ripiego.
>
> Per Firenze usiamo già l'«Edificato multiscala» con le unità volumetriche (servizio WFS `owsedificato`, licenza CC BY 4.0) e lo confrontiamo con il LiDAR 2023 del Comune: i risultati sono molto buoni. Nel catalogo regionale abbiamo trovato anche il nuovo strato «Edificato – unità volumetriche al 2023» (versione 1.0, ottobre 2026), ma è solo consultabile (WMS `rt_edificato`): il servizio WFS risponde con un errore e non abbiamo trovato un collegamento per scaricarlo.
>
> Vi chiedo di poter ricevere la versione al 2023 per tutta la Toscana, o per provincia, con un collegamento o un servizio di download, e di confermare per iscritto che anche questa versione è in CC BY 4.0. Mi sarebbe utile sapere il significato del campo dell'altezza (gronda, colmo o media) e ogni quanto è previsto l'aggiornamento.
>
> Citeremo sempre fonte e licenza della Regione, senza presentare i dati come ufficiali; l'archivio derivato sarà pubblicato con la stessa licenza, senza uso commerciale, e il codice è pubblico.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – EuGEnio, un servizio di Stato Critico – eugenio@statocritico.it – https://eugenio.statocritico.it

---

## Umbria

**Destinatario:** SIAT – umbriageo@regione.umbria.it (indirizzo della scheda RNDT: ricontrollarlo su umbriageo.regione.umbria.it prima dell'invio; il portale non risponde dal nostro ambiente, anche l'08/11/2026)

**Oggetto:** Richiesta dei dati sugli edifici con altezze (CTR 1:2.000 di Perugia, Fabbricati, DBGT) – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco, ingegnere, e curo EuGEnio, un servizio gratuito e open source (AGPL-3.0) del progetto personale Stato Critico, senza scopo di lucro. EuGEnio costruisce modelli 3D degli edifici per analisi energetiche: ombre, fotovoltaico, fabbisogno e priorità di intervento sul patrimonio pubblico, in particolare sanitario. Usiamo i database topografici regionali come fonte principale e OpenStreetMap solo come ripiego.
>
> Nel catalogo abbiamo trovato la CTR vettoriale 1:2.000 del centro di Perugia (volo 2000, edizione 2002), la CTR 10k dell'asta del Tevere e del Trasimeno (volo 2013), i «Fabbricati – Sistema ecografico catastale 2005-2010» (senza altezze) e il Data base GeoTopografico 10k Tevere-Trasimeno. Vi chiedo se la CTR 1:2.000 di Perugia contiene le quote di gronda degli edifici e di poterla ricevere, insieme a uno strato degli edifici con le altezze per la regione (unità volumetriche o quota di gronda), preferibilmente in GeoPackage nel sistema RDN2008 / UTM 33N, con un collegamento o un FTP: il portale UmbriaGeo non risulta raggiungibile dal nostro ambiente.
>
> Vi chiedo anche la licenza scritta: le schede RNDT indicano CC BY 3.0 (D.G.R. 1389/2014), dati.gov.it la CC BY 4.0; il DBGT Tevere-Trasimeno è pubblicato con un WMS a uso non commerciale: si può usare con una licenza aperta? Mi sarebbe utile sapere la frequenza di aggiornamento e se esiste un download regionale in blocco.
>
> Citeremo sempre fonte e licenza della Regione, senza presentare i dati come ufficiali; l'archivio derivato sarà pubblicato con la stessa licenza, senza uso commerciale, e il codice è pubblico.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – EuGEnio, un servizio di Stato Critico – eugenio@statocritico.it – https://eugenio.statocritico.it

---

## Marche

**Destinatario:** Direzione Ambiente e Risorse idriche – Sistema cartografico regionale – direzione.ambiente@regione.marche.it

**Oggetto:** DBGT 2019: unità volumetriche per corpo e DSM – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco, ingegnere, e curo EuGEnio, un servizio gratuito e open source (AGPL-3.0) del progetto personale Stato Critico, senza scopo di lucro. EuGEnio costruisce modelli 3D degli edifici per analisi energetiche: ombre, fotovoltaico, fabbisogno e priorità di intervento sul patrimonio pubblico, in particolare sanitario. Usiamo i database topografici regionali come fonte principale e OpenStreetMap solo come ripiego.
>
> Per Ancona usiamo già il DBGT 2019 (edificio e punto quotato, CC BY 4.0 come indica la pagina OpenData): l'altezza la ricaviamo dalla quota di gronda dell'edificio meno il punto quotato al piede. Il DBGT 2019 dà però una sola quota di gronda per edificio (scala 1:10.000): vi chiedo se esistono le unità volumetriche con l'altezza per corpo di fabbrica (per esempio dalla restituzione 1:2.000 dei centri urbani) e un DSM regionale, e di poterli ricevere con la stessa licenza.
>
> Vi segnalo anche che il file del DTM regionale (Orografia 2019) si interrompe dopo 100–240 MB e che il server non accetta la ripresa dello scaricamento, e che il certificato di `static.regione.marche.it` risulta non valido: se possibile, un file compresso o diviso in parti ci aiuterebbe.
>
> Citeremo sempre fonte e licenza della Regione, senza presentare i dati come ufficiali; l'archivio derivato sarà pubblicato con la stessa licenza, senza uso commerciale, e il codice è pubblico.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – EuGEnio, un servizio di Stato Critico – eugenio@statocritico.it – https://eugenio.statocritico.it

---

## Lazio

**Destinatario:** Area Sistema Informativo Territoriale Regionale – segreteriasitr@regione.lazio.it

**Oggetto:** DBGT 2020: licenza scritta – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco, ingegnere, e curo EuGEnio, un servizio gratuito e open source (AGPL-3.0) del progetto personale Stato Critico, senza scopo di lucro. EuGEnio costruisce modelli 3D degli edifici per analisi energetiche: ombre, fotovoltaico, fabbisogno e priorità di intervento sul patrimonio pubblico, in particolare sanitario. Usiamo i database topografici regionali come fonte principale e OpenStreetMap solo come ripiego.
>
> Per Roma usiamo già le unità volumetriche del DBGT 2014 (foglio 374), scaricate da dati.lazio.it in CC BY 4.0. Sul geoportale abbiamo trovato anche il DBGT 2020 per comune (per esempio Roma.zip), ma per l'edizione 2020 non abbiamo trovato la licenza scritta: vi chiedo di confermare per iscritto con quale licenza è distribuito (per noi andrebbero bene CC BY 4.0 o IODL 2.0), così da poterlo usare al posto dell'edizione 2014.
>
> Vi chiedo anche quale versione della licenza CC BY vale per il DTM 2002-2003 (su dati.lazio.it compare «cc-by» senza versione).
>
> Citeremo sempre fonte e licenza della Regione, senza presentare i dati come ufficiali; l'archivio derivato sarà pubblicato con la stessa licenza, senza uso commerciale, e il codice è pubblico.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – EuGEnio, un servizio di Stato Critico – eugenio@statocritico.it – https://eugenio.statocritico.it

---

## Abruzzo

**Destinatario:** Servizio per l'Informazione Territoriale e la Telematica – infocartografia@regione.abruzzo.it

**Oggetto:** Richiesta del DBTI 2007 1:5.000 (edifici con quote) e del DTM 10 m – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco, ingegnere, e curo EuGEnio, un servizio gratuito e open source (AGPL-3.0) del progetto personale Stato Critico, senza scopo di lucro. EuGEnio costruisce modelli 3D degli edifici per analisi energetiche: ombre, fotovoltaico, fabbisogno e priorità di intervento sul patrimonio pubblico, in particolare sanitario. Usiamo i database topografici regionali come fonte principale e OpenStreetMap solo come ripiego.
>
> Sul geoportale Cartanet abbiamo visto che la CTR/DBTI 2007 alla scala 1:5.000 in Shapefile e il DTM 10 m del 2007 sono «disponibili presso la Regione». Vi chiedo di poter ricevere lo strato degli edifici del DBTI 2007 con le quote (unità volumetriche, quota di gronda o altezza) e il DTM 10 m per tutta la regione o per provincia, con un collegamento, un FTP o un disco.
>
> Vi chiedo anche con quale licenza sono distribuiti questi dati (le schede che abbiamo visto indicano «dato pubblico», che non è una licenza: per noi andrebbero bene CC BY 4.0 o IODL 2.0), ogni quanto vengono aggiornati e se esiste un download in blocco che non ho trovato.
>
> Citeremo sempre fonte e licenza della Regione, senza presentare i dati come ufficiali; l'archivio derivato sarà pubblicato con la stessa licenza, senza uso commerciale, e il codice è pubblico.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – EuGEnio, un servizio di Stato Critico – eugenio@statocritico.it – https://eugenio.statocritico.it

---

## Molise

**Destinatario:** indirizzo da verificare. Le schede RNDT del Molise (2012) indicano come contatto la società in-house Molise Dati S.p.A., non un ufficio regionale; il geoportale e il sito della Regione non rispondono dal nostro ambiente. Pagina più vicina: https://www.regione.molise.it/ (cercare la struttura che cura la cartografia regionale e il geoportale).

**Oggetto:** Richiesta del DBT / CTR regionale – edifici con altezze – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco, ingegnere, e curo EuGEnio, un servizio gratuito e open source (AGPL-3.0) del progetto personale Stato Critico, senza scopo di lucro. EuGEnio costruisce modelli 3D degli edifici per analisi energetiche: ombre, fotovoltaico, fabbisogno e priorità di intervento sul patrimonio pubblico, in particolare sanitario. Usiamo i database topografici regionali come fonte principale e OpenStreetMap solo come ripiego.
>
> Nel catalogo nazionale RNDT abbiamo trovato per il Molise solo i servizi di consultazione del DTM e dell'ortofoto 2007, senza licenza indicata, e nessuna scheda sugli edifici. Vi chiedo se la Regione dispone di uno strato degli edifici (Carta Tecnica o DB topografico), meglio se con le altezze, e di poterlo ricevere per tutta la regione, preferibilmente in GeoPackage nel sistema RDN2008 / UTM 33N, con un collegamento, un FTP o un disco.
>
> Vi chiedo anche con quale licenza sono distribuiti questi dati (per noi andrebbero bene CC BY 4.0 o IODL 2.0), ogni quanto vengono aggiornati e se esiste già un download regionale in blocco che non ho trovato. Se l'ufficio competente è un altro, vi ringrazio se vorrete inoltrare la richiesta.
>
> Citeremo sempre fonte e licenza della Regione, senza presentare i dati come ufficiali; l'archivio derivato sarà pubblicato con la stessa licenza, senza uso commerciale, e il codice è pubblico.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – EuGEnio, un servizio di Stato Critico – eugenio@statocritico.it – https://eugenio.statocritico.it

---

## Campania

**Destinatario:** UOS SIT/Iter – Sistema Informativo Territoriale – sit@regione.campania.it

**Oggetto:** DBT 2020: quote degli edifici, DSM e file regionale – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco, ingegnere, e curo EuGEnio, un servizio gratuito e open source (AGPL-3.0) del progetto personale Stato Critico, senza scopo di lucro. EuGEnio costruisce modelli 3D degli edifici per analisi energetiche: ombre, fotovoltaico, fabbisogno e priorità di intervento sul patrimonio pubblico, in particolare sanitario. Usiamo i database topografici regionali come fonte principale e OpenStreetMap solo come ripiego.
>
> Usiamo con piacere la CTR, il DBT e il DTM 2020 che il geoportale distribuisce in CC BY 4.0: per Napoli abbiamo già preparato le sagome degli edifici dal DBT 2020 con le quote del terreno dal DTM 5 m. Il DBT 2020 però non contiene unità volumetriche né quote di gronda, per cui le altezze degli edifici oggi sono solo stimate. Vi chiedo:
>
> - se esistono, anche non pubblicate, le quote di gronda o di estradosso degli edifici (o le unità volumetriche) della restituzione 2020, e se possiamo riceverle con la stessa licenza;
> - se esiste un DSM (fotogrammetrico 2020 o LiDAR) per Napoli o per la regione;
> - se esiste un file unico regionale (o per provincia) del DBT, e se possiamo scaricare in automatico dalle cartelle condivise per comune.
>
> Citeremo sempre fonte e licenza della Regione, senza presentare i dati come ufficiali; l'archivio derivato sarà pubblicato con la stessa licenza, senza uso commerciale, e il codice è pubblico.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – EuGEnio, un servizio di Stato Critico – eugenio@statocritico.it – https://eugenio.statocritico.it

---

## Puglia

**Destinatario:** servizio.territorio@regione.puglia.it (titolare del dato nella scheda RNDT), in copia info@sit.puglia.it (SIT Puglia, InnovaPuglia); ricontrollarli prima dell'invio

**Oggetto:** CTR 1:5.000: aggiornamenti dopo il 2006, DSM e licenza del DBT Multiscala – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco, ingegnere, e curo EuGEnio, un servizio gratuito e open source (AGPL-3.0) del progetto personale Stato Critico, senza scopo di lucro. EuGEnio costruisce modelli 3D degli edifici per analisi energetiche: ombre, fotovoltaico, fabbisogno e priorità di intervento sul patrimonio pubblico, in particolare sanitario. Usiamo i database topografici regionali come fonte principale e OpenStreetMap solo come ripiego.
>
> Per Bari usiamo già la CTR 1:5.000 (volo 2006) con i punti di gronda e al piede degli edifici e il DTM 8 m, scaricati dal SIT in IODL 2.0: i risultati sono buoni. Vi chiedo se esiste un aggiornamento più recente della CTR o del DB topografico (per esempio da un volo del 2015 o successivo) e un DSM o un rilievo LiDAR regionale, e di poterli ricevere con una licenza aperta.
>
> Vi chiedo anche con quale licenza è distribuito il «DBT Multiscala 2006», oggi indicato come «Dato pubblico», che non è una licenza.
>
> Citeremo sempre fonte e licenza della Regione, senza presentare i dati come ufficiali; l'archivio derivato sarà pubblicato con la stessa licenza, senza uso commerciale, e il codice è pubblico.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – EuGEnio, un servizio di Stato Critico – eugenio@statocritico.it – https://eugenio.statocritico.it

---

## Friuli Venezia Giulia

**Destinatario:** IRDAT – irdat@regione.fvg.it (pagina IRDAT della Regione, verificata l'08/11/2026)

**Oggetto:** LiDAR 2017-2020: scarico in blocco e licenza; licenza degli strati CTRN – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco, ingegnere, e curo EuGEnio, un servizio gratuito e open source (AGPL-3.0) del progetto personale Stato Critico, senza scopo di lucro. EuGEnio costruisce modelli 3D degli edifici per analisi energetiche: ombre, fotovoltaico, fabbisogno e priorità di intervento sul patrimonio pubblico, in particolare sanitario. Usiamo i database topografici regionali come fonte principale e OpenStreetMap solo come ripiego.
>
> Usiamo già l'Edificato CTRN (edizione 2, con ALTEZZA e quote) del servizio WFS IRDAT per Trieste, con la CC BY 4.0 indicata nella scheda del servizio di download (le schede dei singoli strati dicono «Non indicato»: vi chiedo di confermare la licenza anche per questi). Abbiamo confrontato le altezze con il LiDAR 2017-2020 su 7.327 edifici di Trieste: scarto mediano +0,05 m, 82 % entro 2 m.
>
> Vi chiedo uno scarico in blocco (o un servizio WCS) dei DTM e DSM 0,5 m del rilievo LiDAR 2017-2020, oggi per elemento, e la loro licenza scritta (le schede riportano «Use constraints: -»; la pagina regionale cita la IODL 2.0). Mi sarebbe utile anche sapere la copertura del DBTsped e l'origine del campo `ALTEZZA_M`.
>
> Citeremo sempre fonte e licenza della Regione, senza presentare i dati come ufficiali; l'archivio derivato sarà pubblicato con la stessa licenza, senza uso commerciale, e il codice è pubblico.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – EuGEnio, un servizio di Stato Critico – eugenio@statocritico.it – https://eugenio.statocritico.it

---

## Calabria

**Destinatario:** Dipartimento Ambiente, Paesaggio e Qualità Urbana – Settore 8 – QTRP, Osservatorio delle Trasformazioni e del Paesaggio, Politiche Territoriali e Centro Cartografico Regionale – PEC dipartimento.lavoripubblici@pec.regione.calabria.it (avviso della Regione dell'11/02/2026, ricontrollato l'08/11/2026: dal 10/02/2026 la vecchia PEC del Centro cartografico è dismessa; spedire da una casella PEC)

**Oggetto:** Richiesta del DBT / CTR regionale – edifici con altezze – c.a. Centro cartografico regionale – EuGEnio

**Testo:**

> Gentili,
>
> chiedo cortesemente di inoltrare questa richiesta al Centro Cartografico Regionale. Sono Paolo Bianco, ingegnere, e curo EuGEnio, un servizio gratuito e open source (AGPL-3.0) del progetto personale Stato Critico, senza scopo di lucro. EuGEnio costruisce modelli 3D degli edifici per analisi energetiche: ombre, fotovoltaico, fabbisogno e priorità di intervento sul patrimonio pubblico, in particolare sanitario. Usiamo i database topografici regionali come fonte principale e OpenStreetMap solo come ripiego.
>
> Nel catalogo nazionale RNDT non abbiamo trovato schede sugli edifici della Calabria e il geoportale regionale non risulta raggiungibile dal nostro ambiente di sviluppo. Vi chiedo di poter ricevere lo strato degli edifici della Carta Tecnica / DB topografico regionale, con le altezze se disponibili (unità volumetriche o quota di gronda), per tutta la regione o per provincia, preferibilmente in GeoPackage nel sistema RDN2008 / UTM 33N, con un collegamento, un FTP o un disco.
>
> Vi chiedo anche con quale licenza sono distribuiti (per noi andrebbero bene CC BY 4.0 o IODL 2.0), ogni quanto vengono aggiornati e se esiste già un download regionale in blocco che non ho trovato.
>
> Per Catanzaro abbiamo scaricato alcuni riquadri del DTM 5×5 m regionale: la scheda dice che «la cessione diretta ad Enti terzi dei dati non è consentita salvo concessioni/autorizzazioni specifiche» e chiede la citazione della fonte. Per ora lo useremmo solo per calcolare la quota a terra degli edifici, citando la Regione, senza ridistribuirlo né mostrarlo come terreno. Vi chiedo se il DTM 5×5 m può essere rilasciato con una licenza aperta (CC BY 4.0 o IODL 2.0) o, in alternativa, un'autorizzazione scritta per EuGEnio a usarlo per le quote degli edifici e per il terreno delle viste 3D; vi chiedo anche se è possibile un accesso anonimo al download (oggi FTP con credenziali) e una scheda di metadati aggiornata della CTR 1:5.000 con la sua licenza.
>
> Citeremo sempre fonte e licenza della Regione, senza presentare i dati come ufficiali; l'archivio derivato sarà pubblicato con la stessa licenza, senza uso commerciale, e il codice è pubblico.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – EuGEnio, un servizio di Stato Critico – eugenio@statocritico.it – https://eugenio.statocritico.it

---

## Sicilia

**Destinatario:** Dipartimento dell'Urbanistica – Area 2 Interdipartimentale (SITR) – area2.sitr@regione.sicilia.it (il SITR chiede di usare la PEC solo se necessario)

**Oggetto:** Licenza del servizio DTM 2013 (mdt_2013) – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco, ingegnere, e curo EuGEnio, un servizio gratuito e open source (AGPL-3.0) del progetto personale Stato Critico, senza scopo di lucro. EuGEnio costruisce modelli 3D degli edifici per analisi energetiche: ombre, fotovoltaico, fabbisogno e priorità di intervento sul patrimonio pubblico, in particolare sanitario. Usiamo i database topografici regionali come fonte principale e OpenStreetMap solo come ripiego.
>
> Dal SITR usiamo la CTR 2012-2013, scaricabile in CC BY 4.0, che ha già la quota di gronda degli edifici nella z dei vertici. Per ricavare l'altezza serve però la quota del terreno: vi chiedo con quale licenza è distribuito il servizio ImageServer del DTM 2013 (`mdt_2013`), che non riporta una licenza, e se possiamo usarlo in CC BY 4.0.
>
> Se il servizio non può essere usato con una licenza aperta, vi chiedo in alternativa se, trattandosi di un progetto senza scopo di lucro, è possibile la cessione gratuita del DTM e del DSM a 2 m (ATA 2012-2013), con una licenza che permetta di pubblicare le altezze degli edifici derivate.
>
> Citeremo sempre fonte e licenza della Regione, senza presentare i dati come ufficiali; l'archivio derivato sarà pubblicato con la stessa licenza, senza uso commerciale, e il codice è pubblico.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – EuGEnio, un servizio di Stato Critico – eugenio@statocritico.it – https://eugenio.statocritico.it

---

## Sardegna

**Destinatario:** Assessorato degli Enti Locali – Pianificazione urbanistica – eell.urb.pianificazione@regione.sardegna.it (indirizzo della scheda RNDT del 2022: ricontrollarlo prima dell'invio)

**Oggetto:** DBGT 10k ed edifici: altezze e attribuzione – EuGEnio

**Testo:**

> Gentili,
>
> sono Paolo Bianco, ingegnere, e curo EuGEnio, un servizio gratuito e open source (AGPL-3.0) del progetto personale Stato Critico, senza scopo di lucro. EuGEnio costruisce modelli 3D degli edifici per analisi energetiche: ombre, fotovoltaico, fabbisogno e priorità di intervento sul patrimonio pubblico, in particolare sanitario. Usiamo i database topografici regionali come fonte principale e OpenStreetMap solo come ripiego.
>
> Usiamo già, in CC BY 4.0, gli edifici del DBGT 10k 2022 dal servizio WFS e il LiDAR 2008 della fascia costiera, da cui ricaviamo le altezze di una parte di Cagliari. Vi chiedo se esistono altezze degli edifici più complete: DBGT comunali vettoriali 1:1.000–1:2.000 con le quote, oppure un rilievo LiDAR di Cagliari e della costa più recente del 2008.
>
> Vi chiedo anche di confermare la dicitura di attribuzione che preferite per il DBGT e per il LiDAR.
>
> Citeremo sempre fonte e licenza della Regione, senza presentare i dati come ufficiali; l'archivio derivato sarà pubblicato con la stessa licenza, senza uso commerciale, e il codice è pubblico.
>
> Grazie per l'attenzione, cordiali saluti.
>
> Paolo Bianco – EuGEnio, un servizio di Stato Critico – eugenio@statocritico.it – https://eugenio.statocritico.it

---

## Regioni e Comuni con fonte «attiva» (nessuna lettera di richiesta dati)

- **Lombardia** (DBGT – Unità volumetrica, CC BY 4.0): nessuna lettera. A Milano il DBGT coincide con il DBT 2020 del Comune (archivio dell'08/11/2026); DTM 5 m dall'ImageServer regionale.
- **Provincia autonoma di Trento** (Edifici P.A.T. 3D, CC BY 4.0, `MED_ALT`; LiDAR PAT 2014/2018 per le altezze mancanti): nessuna lettera.
- **Veneto** (Edifici del Veneto feb. 2022, IODL 2.0, sagome senza altezze): nessuna lettera. **Comune di Venezia**: nessuna lettera, il DBGT comunale con le unità volumetriche (altezze, quote di base, gronda ed estrusione) si scarica dalla «Carta Tecnica» di dati.venezia.it, aggiornato al 10/09/2026, con la licenza IODL 2.0 scritta in `Informazioni_e_licenza.pdf` (archivio del comune intero dell'08/11/2026).
- **Liguria** (CTR 3D, CC BY 4.0): nessuna lettera. A Genova il DSM/DTM comunale 50 cm (LiDAR 2018, CC BY 4.0) dà le quote e il controllo delle altezze; **Comune di Genova**: nessuna lettera.
- **Basilicata** (DBGT – Unità volumetrica, IODL 2.0; DTM e DSM 5 m dal WCS): lettera tolta l'08/11/2026, servizi della RSDI provati dal vivo (Potenza intera). Eventualmente, più avanti, solo una richiesta di DTM/DSM più fini del LiDAR 2013.

## Scoperte che cambiano `regioni.toml` (riportate nel file l'08/11/2026)

- **Campania – edifici**: la pagina [Carta Tecnica Regionale](https://sit.regione.campania.it/carta-tecnica-regionale) del geoportale (sit.regione.campania.it, raggiungibile il 07/11/2026) dice che **CTR, DBT e DTM aggiornati al 2020 per l'intera regione si scaricano liberamente in CC BY 4.0**, da un repository web (cartella condivisa della Regione) e da una mappa interattiva; c'è anche un WMS della CTR 2020. Le note legali del geoportale confermano la CC BY 4.0. Restano da verificare la presenza delle unità volumetriche con le altezze e il formato. La fonte può passare da «in attesa / da verificare» a «in attesa» con licenza CC BY 4.0 e servizio indicato; anche il tema **dtm** della Campania (DTM 2020, CC BY 4.0) va aggiornato.
- **Calabria**: dal 10/02/2026 la PEC del Centro cartografico regionale è dismessa; le comunicazioni vanno alla PEC del Dipartimento Governo del territorio.
- **Puglia**: il portale SIT elenca «DBT Multiscala 2006» e una sezione «Download Cartografie»; da controllare dal browser se contiene gli edifici.
- **Umbria**: oltre ai Fabbricati 2005-2010 esiste un Data base GeoTopografico 10k dell'asta del Tevere e del Trasimeno (volo 2013), da aggiungere come fonte parziale se ha lo strato dell'edificato.
- **Abruzzo**: il geoportale Cartanet (geoportale.regione.abruzzo.it/Cartanet) risponde, a differenza di quanto annotato il 04/11 (503); il portale open data continua a non rispondere.

## Fonti consultate (07/11/2026)

Pagine delle Regioni e dei loro geoportali:
- Emilia-Romagna: https://geoportale.regione.emilia-romagna.it/archivio-cartografico/dove-siamo e https://geoportale.regione.emilia-romagna.it/archivio-cartografico/come-acquistare
- Valle d'Aosta: https://geoportale.regione.vda.it/?p=6633
- P.A. Bolzano: https://geonetwork1.civis.bz.it/geonetwork/srv/api/records/p_bz:Elevation:DigitalTerrainModel-0.5m (pagina natura-territorio.provincia.bz.it non leggibile senza JavaScript)
- Toscana: https://www502.regione.toscana.it/geonetwork/srv/api/records/r_toscan:294be9db-ba10-4e2d-a890-89f87d00f30a
- Marche: https://www.regione.marche.it/Regione-Utile/Paesaggio-Territorio-Urbanistica/Cartografia
- Lazio: https://regione.lazio.it/cittadini/urbanistica/sistema-informativo-territoriale-regionale/consultazione-archivi
- Abruzzo: http://geoportale.regione.abruzzo.it/Cartanet
- Campania: https://sit.regione.campania.it/ufficio-sit/contatti, https://sit.regione.campania.it/carta-tecnica-regionale, https://sit.regione.campania.it/ufficio-sit/news/cartografie-digitali-della-regione-campania, https://sit.regione.campania.it/note-legali
- Puglia: http://www.sit.puglia.it/portal/portale_sit e pagina «Cartografie Tecniche e Tematiche» (la pagina «Contatti» risponde 404)
- Calabria: https://www.regione.calabria.it/dismissione-indirizzo-pec-cartografico-urbanisticapec-regione-calabria-it/ e https://www.regione.calabria.it/dipartimento-governo-del-territorio-difesa-del-suolo-e-politiche-per-la-casa/
- Sicilia: https://www.sitr.regione.sicilia.it/contatti/

Schede di metadati RNDT (catalogo nazionale geodati.gov.it, schede pubblicate dalle Regioni):
- Piemonte: https://geodati.gov.it/resource/id/r_piemon:6dacd512-8862-491a-a37b-c032cd54d081
- Valle d'Aosta: https://geodati.gov.it/resource/id/r_vda:01533-META:20160908:170944
- Umbria: https://geodati.gov.it/resource/id/r_umbria:00000:20160905:112000 e https://geodati.gov.it/resource/id/r_umbria:00000:20200110:112000
- Emilia-Romagna: https://geodati.gov.it/resource/id/r_emiro:2024-01-31T143925
- Lazio: https://geodati.gov.it/resource/id/r_lazio:eb519f30-d2c9-430f-9e96-74d0
- Abruzzo: https://geodati.gov.it/resource/id/r_abruzz:00151:20120710:152430
- Molise: https://geodati.gov.it/resource/id/r_molise:00020:20120413:113457 e https://geodati.gov.it/resource/id/r_molise:00022:20120413:115401
- Puglia: https://geodati.gov.it/resource/id/r_puglia:85898eba-d4b0-4c3b-a2c7-6ea666522591
- Basilicata: https://geodati.gov.it/resource/id/r_basili:26e21af8:14ff44204d8:214c, https://geodati.gov.it/resource/id/r_basili:9EE9C09A-7091-D8A2-A41D-F28191B86C4F
- Sardegna: https://geodati.gov.it/resource/id/R_SARDEG:2c842f2a-d268-45e4-a68c-6cff2070bd28, https://geodati.gov.it/resource/id/R_SARDEG:e2327002-a91f-4e77-a0b8-6518c020d2c2
- Bolzano: https://geodati.gov.it/resource/id/p_bz:Elevation:DigitalTerrainModel-0.5m

Portali non raggiungibili dal nostro ambiente il 07/11/2026 (da riprovare dal browser o dal server): geoportale e sito della Regione Piemonte (il WFS `bdtre_imm` risponde dal PC di Paolo), umbriageo.regione.umbria.it e regione.umbria.it (anche l'08/11), geoportale e sito della Regione Molise, geoportale.regione.calabria.it, sardegnageoportale.it, opendata.regione.abruzzo.it (503), dati.venezia.it (controllo anti-robot: scaricato da Paolo dal browser). Dall'08/11/2026 la RSDI della Basilicata risponde.
