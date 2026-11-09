"""Configurazione da variabili d'ambiente (file .env letto da docker compose)."""
from __future__ import annotations

import os
from pathlib import Path

DATI = Path(os.environ.get("DATI", "/dati"))
# regioni SERVITE dal sito (comuni, meteo, Legge 10, Dati climatici): codici ISTAT separati da virgola, vuoto = tutta Italia
REGIONI = [r.strip().zfill(2) for r in os.environ.get("REGIONI", "08").split(",") if r.strip()]
# regioni di cui il worker AGGIORNA ogni giorno previsioni (Open-Meteo) e storico (04/11/2026): vuoto = tutte quelle
# servite (comportamento di prima). Con l'archivio nazionale si può servire tutta Italia (REGIONI vuoto) e aggiornare
# ogni giorno solo una parte (es. REGIONI_AGGIORNATE=08), per stare nei limiti dell'API gratuita di Open-Meteo; le
# regioni aggiornate valgono solo tra quelle servite.
REGIONI_AGGIORNATE = [r.strip().zfill(2) for r in os.environ.get("REGIONI_AGGIORNATE", "").split(",") if r.strip()]
SOLO_COMUNI = [c.strip() for c in os.environ.get("SOLO_COMUNI", "").split(",") if c.strip()]  # per prove
ORE_PREVISIONI = int(os.environ.get("ORE_PREVISIONI", "6"))          # ogni quante ore aggiornare le previsioni
ORA_STORICO_UTC = int(os.environ.get("ORA_STORICO_UTC", "5"))        # aggiornamento giornaliero dello storico
ZORNADE_API_KEY = os.environ.get("ZORNADE_API_KEY", "")
ZORNADE_URL = os.environ.get("ZORNADE_URL", "https://api.zornade.com/api/v2")
OPEN_METEO_LOCALE = os.environ.get("OPEN_METEO_LOCALE") or None     # es. http://open-meteo:8080
MAX_UPLOAD_MB = float(os.environ.get("MAX_UPLOAD_MB", "5"))
MAX_RIGHE = int(os.environ.get("MAX_RIGHE", "200000"))
DISPOSITIVO = os.environ.get("TIREX_DEVICE", "cpu")
MODELLO = os.environ.get("TIREX_MODELLO", "NX-AI/TiRex-2")
ORIGINI_CORS = [o for o in os.environ.get("ORIGINI_CORS", "").split(",") if o]

# previsioni meteo
MODELLO_BREVE = "italia_meteo_arpae_icon_2i"   # Arpae ICON-2I, 2,2 km, fino a 72 h
MODELLO_LUNGO = "ecmwf_ifs025"                 # ECMWF IFS 0,25°, fino a 15 giorni
MISCELA_DA_H, MISCELA_A_H = 48, 72             # transizione lineare ICON-2I → IFS
GIORNI_PREVISIONE = 15

# limiti di contesto per TiRex-2
CONTESTO_ORARIO = 24 * 90       # 90 giorni di storia oraria
CONTESTO_GIORNALIERO = 365 * 3  # 3 anni di storia giornaliera
MAX_ORIZZONTE_ORE = 24 * 15
MAX_ORIZZONTE_GIORNI = 365

# dati di mercato (fase 6)
MERCATI_CONFIG = os.environ.get("MERCATI_CONFIG", "/dati/mercati/config.toml")
ORA_MERCATI_LOCALE = os.environ.get("ORA_MERCATI", "02:30")          # aggiornamento notturno, ora italiana
# I dati GME e TTF/EEX sono solo per uso interno (simulazioni e analisi): nessuna rotta li espone.

# patrimonio edilizio (fase 7)
MAX_EDIFICI = int(os.environ.get("MAX_EDIFICI", "500"))               # righe per singolo caricamento
ANNCSU_FILE = DATI / "anncsu" / "anncsu_civici.parquet"               # indirizzario ANNCSU (civici georeferenziati)
ANNCSU_GIORNO = int(os.environ.get("ANNCSU_GIORNO", "12"))            # giorno del mese in cui riscaricarlo

# file statici del sito aggiornati dal worker (montati in scrittura solo nel worker: /srv/energia/sito/dati)
SITO_DATI = Path(os.environ.get("SITO_DATI", "/sito/dati"))
# indicatori della sanità (fase 8): una volta al mese
INDICATORI_GIORNO = int(os.environ.get("INDICATORI_GIORNO", "5"))       # giorno del mese, dalle 6
# clima dal 1940 (fase 9): due volte l'anno, giorno/mese separati da virgola. Il 10 luglio la stagione di
# riscaldamento 1/7–30/6 è finita da 10 giorni (ERA5T arriva con ~5 giorni di ritardo): entrano i suoi gradi
# giorno. Il 10 gennaio è finito l'anno solare: entrano i mensili, le temperature di progetto e la tendenza annua.
CLIMA_DATE = [tuple(int(x) for x in d.split("/")) for d in os.environ.get("CLIMA_DATE", "10/01,10/07").split(",") if d.strip()]
CLIMA_LAVORO = Path(os.environ.get("CLIMA_LAVORO", str(DATI / "clima_lavoro")))   # comuni.parquet, cache, registri
CLIMA_CODICE = Path(os.environ.get("CLIMA_CODICE", "/app/clima_storico"))           # script della fase 9

# report scaricabili (pdf, xlsx, ods; docx e odt spenti dal 28/10/2026): limiti del documento ricevuto e font per il PDF
REPORT_MAX_MB = float(os.environ.get("REPORT_MAX_MB", "5"))                    # corpo JSON della richiesta
REPORT_MAX_SEZIONI = int(os.environ.get("REPORT_MAX_SEZIONI", "50"))
REPORT_MAX_BLOCCHI = int(os.environ.get("REPORT_MAX_BLOCCHI", "100"))          # blocchi per sezione
REPORT_MAX_RIGHE = int(os.environ.get("REPORT_MAX_RIGHE", "5000"))             # righe per tabella
REPORT_MAX_RIGHE_TOTALI = int(os.environ.get("REPORT_MAX_RIGHE_TOTALI", "10000"))
REPORT_MAX_COLONNE = int(os.environ.get("REPORT_MAX_COLONNE", "30"))
REPORT_MAX_TESTO = int(os.environ.get("REPORT_MAX_TESTO", "20000"))            # caratteri per testo
REPORT_MAX_IMMAGINI = int(os.environ.get("REPORT_MAX_IMMAGINI", "10"))
REPORT_MAX_IMMAGINE_KB = int(os.environ.get("REPORT_MAX_IMMAGINE_KB", "1500"))
REPORT_FONT_DIR = Path(os.environ.get("REPORT_FONT_DIR", "/usr/share/fonts/truetype/dejavu"))  # fonts-dejavu-core
# Formati dei report offerti dalle rotte /api/report (decisione del 28/10/2026): il servizio gratuito produce solo il
# PDF e i dati grezzi (Excel .xlsx e OpenDocument .ods). Word (docx) e ODT restano nel codice ma sono spenti: le rotte
# rispondono 410. Per riaccenderli basta, nel .env, REPORT_FORMATI=pdf,xlsx,ods,docx,odt (poi riavviare l'api).
REPORT_FORMATI = tuple(f.strip().lower() for f in os.environ.get("REPORT_FORMATI", "pdf,xlsx,ods").split(",")
                       if f.strip())

# newsletter automatica dei dati (listmonk) e avvisi all'amministratore
LISTMONK_URL = os.environ.get("LISTMONK_URL", "http://listmonk:9000")
LISTMONK_API_UTENTE = os.environ.get("LISTMONK_API_UTENTE", "")
LISTMONK_API_TOKEN = os.environ.get("LISTMONK_API_TOKEN", "")
LISTA_MENSILE = int(os.environ.get("LISTA_MENSILE", "0") or 0)
NOTIZIARIO_INVIO_AUTOMATICO = os.environ.get("NOTIZIARIO_INVIO_AUTOMATICO", "true").lower() == "true"
NOTIZIARIO_GIORNO = int(os.environ.get("NOTIZIARIO_GIORNO", "12"))     # giorno del mese del numero mensile
SMTP_SERVER = os.environ.get("SMTP_SERVER", "")
SMTP_PORTA = int(os.environ.get("SMTP_PORTA", "587"))
SMTP_UTENTE = os.environ.get("SMTP_UTENTE", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_MITTENTE = os.environ.get("SMTP_MITTENTE", "")
EMAIL_AMMINISTRATORE = os.environ.get("EMAIL_AMMINISTRATORE", "")
SITO_URL = os.environ.get("SITO_URL", "https://eugenio.statocritico.it")
# registro delle versioni del sito (07/11/2026; fase5-sito/novita.toml, copiato nell'immagine): voci del mese nella newsletter
NOVITA_TOML = Path(os.environ.get("NOVITA_TOML", "/app/novita.toml" if Path("/app/novita.toml").exists()
                                   else str(Path(__file__).resolve().parents[2] / "fase5-sito" / "novita.toml")))
NOTIZIE_URL = os.environ.get("NOTIZIE_URL", "https://notizie.statocritico.it")

# dati storici scaricabili (pagina "Dati storici", servizio/storici.py): solo dati ridistribuibili con attribuzione
STORICI_MAX_RIGHE_CSV = int(os.environ.get("STORICI_MAX_RIGHE_CSV", "500000"))     # righe per file CSV
STORICI_MAX_RIGHE_XLSX = int(os.environ.get("STORICI_MAX_RIGHE_XLSX", "300000"))   # righe per file Excel
STORICI_MAX_CELLE_XLSX = int(os.environ.get("STORICI_MAX_CELLE_XLSX", "3000000"))  # righe × colonne in Excel (~40 s di scrittura)
# OpenDocument (ods): scritto a flusso, ~9 s per 3 milioni di celle sul PC di prova (più lento sul server ARM);
# lo stesso tetto dell'Excel tiene il file apribile senza fatica in LibreOffice
STORICI_MAX_RIGHE_ODS = int(os.environ.get("STORICI_MAX_RIGHE_ODS", "300000"))     # righe per file ods
STORICI_MAX_CELLE_ODS = int(os.environ.get("STORICI_MAX_CELLE_ODS", "3000000"))    # righe × colonne in ods
STORICI_MAX_COMUNI = int(os.environ.get("STORICI_MAX_COMUNI", "2000"))             # comuni elencati uno per uno
STORICI_MAX_COMUNI_LEGGE10 = int(os.environ.get("STORICI_MAX_COMUNI_LEGGE10", "400"))
STORICI_COPERTURA = int(os.environ.get("STORICI_COPERTURA", "90"))      # % minima di dati per un periodo valido
STORICI_ESTRAZIONI_ORA = int(os.environ.get("STORICI_ESTRAZIONI_ORA", "30"))   # download per IP all'ora
STORICI_STIME_ORA = int(os.environ.get("STORICI_STIME_ORA", "600"))            # stime per IP all'ora
STORICI_PARALLELE = int(os.environ.get("STORICI_PARALLELE", "2"))              # estrazioni contemporanee

# protezione dell'API (servizio/protezione.py): limiti per IP (gli IPv6 contano per rete /64), tetti per tutti gli
# utenti insieme, verifica anti-robot Cloudflare Turnstile sulle rotte che costano, avvisi all'amministratore
LIMITE_DATI_ORA = int(os.environ.get("LIMITE_DATI_ORA", "600"))          # meteo, Legge 10, mappa, comuni per IP all'ora
ZORNADE_TETTO_ORA = int(os.environ.get("ZORNADE_TETTO_ORA", "6000"))     # chiamate Zornade all'ora per tutto il sito
ZORNADE_AVVISO_QUOTA = float(os.environ.get("ZORNADE_AVVISO_QUOTA", "0.7"))   # email quando l'ora supera il 70 %
PREVISIONI_PARALLELE = int(os.environ.get("PREVISIONI_PARALLELE", "2"))  # ammesse insieme: modello.py ne calcola una, l'altra in fila
PREVISIONI_ATTESA_S = float(os.environ.get("PREVISIONI_ATTESA_S", "30"))  # attesa massima in coda, poi 503
# Turnstile: chiave del sito (pubblica) e chiave segreta (solo nel .env). Senza le due chiavi la verifica è spenta
# (prove, mirror). TURNSTILE_HOSTNAME: nomi accettati nella risposta di Cloudflare (vuoto = nessun controllo).
TURNSTILE_SITEKEY = os.environ.get("TURNSTILE_SITEKEY", "")
TURNSTILE_SECRET = os.environ.get("TURNSTILE_SECRET", "")
TURNSTILE_HOSTNAME = [h.strip() for h in os.environ.get("TURNSTILE_HOSTNAME", "eugenio.statocritico.it").split(",")
                      if h.strip()]
TURNSTILE_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
# gettone di sessione rilasciato dopo la verifica: firmato con SESSIONE_CHIAVE (vuota = chiave casuale a ogni avvio,
# le sessioni aperte si rinnovano da sole), valido SESSIONE_MINUTI e legato alla rete di chi l'ha chiesto
SESSIONE_CHIAVE = os.environ.get("SESSIONE_CHIAVE", "")
SESSIONE_MINUTI = int(os.environ.get("SESSIONE_MINUTI", "30"))
SESSIONI_ORA = int(os.environ.get("SESSIONI_ORA", "60"))                 # verifiche per IP all'ora
# avviso email solo quando la stessa rete supera i limiti almeno AVVISO_429_SOGLIA volte al giorno per
# AVVISO_429_GIORNI giorni consecutivi; i conteggi (con gli IP) restano AVVISO_429_CONSERVA_GIORNI giorni
AVVISO_429_SOGLIA = int(os.environ.get("AVVISO_429_SOGLIA", "20"))
AVVISO_429_GIORNI = int(os.environ.get("AVVISO_429_GIORNI", "3"))
AVVISO_429_CONSERVA_GIORNI = int(os.environ.get("AVVISO_429_CONSERVA_GIORNI", "7"))
PROTEZIONE_DIR = Path(os.environ.get("PROTEZIONE_DIR", str(DATI / "protezione")))

# ortofoto (fase 10, Fase B; servizio/ortofoto.py): TOML delle fonti (copiati nell'immagine da fase10-edifici3d/ortofoto),
# copia su disco delle tessere, fonti spente senza toccare i TOML, limite per IP
_FONTI_REPO = Path(__file__).resolve().parents[2] / "fase10-edifici3d" / "ortofoto"
ORTOFOTO_FONTI = Path(os.environ.get("ORTOFOTO_FONTI") or ("/app/ortofoto_fonti" if Path("/app/ortofoto_fonti").exists()
                                                           else str(_FONTI_REPO)))
CARTELLA_ORTOFOTO = Path(os.environ.get("CARTELLA_ORTOFOTO_INTERNA", str(DATI / "ortofoto")))
ORTOFOTO_SPENTE = {s.strip() for s in os.environ.get("ORTOFOTO_SPENTE", "").split(",") if s.strip()}
ORTOFOTO_SOLO_CONFERMATE = os.environ.get("ORTOFOTO_SOLO_CONFERMATE", "false").lower() == "true"
ORTOFOTO_GIORNI = int(os.environ.get("ORTOFOTO_GIORNI", "180"))          # validità della copia di una tessera
ORTOFOTO_MAX_GB = float(os.environ.get("ORTOFOTO_MAX_GB", "15"))          # tetto della copia su disco
ORTOFOTO_CACHE_S = int(os.environ.get("ORTOFOTO_CACHE_S", "2592000"))     # Cache-Control verso browser e Cloudflare (30 giorni)
# (09/11/2026, prove J10: migliaia di 429 in Modelli 3D) contano solo le tessere chieste davvero alla fonte (non in copia);
# una sessione intensa in 3D (viste inclinate, più fonti, più zoom) ne chiede facilmente qualche migliaio all'ora
ORTOFOTO_ORA = int(os.environ.get("ORTOFOTO_ORA", "12000"))               # tessere scaricate dalla fonte per IP all'ora
STRATI_ORA = int(os.environ.get("STRATI_ORA", "12000"))                   # tessere di particelle e contorni dalla fonte per IP all'ora
# tessere servite dalla copia su disco (ortofoto, strati, terreno insieme): non toccano le fonti esterne, tetto anti-abuso
TESSERE_COPIA_ORA = int(os.environ.get("TESSERE_COPIA_ORA", "60000"))
ORTOFOTO_ATTESA_S = float(os.environ.get("ORTOFOTO_ATTESA_S", "8"))       # attesa massima del turno verso la fonte (09/11/2026: 6 → 8)
# strati sopra le ortofoto (particelle catastali, contorni degli edifici; servizio/strati.py, 05/11/2026): spenti dal .env
STRATI_SPENTI = {s.strip() for s in os.environ.get("STRATI_SPENTI", "").split(",") if s.strip()}

# ripiego OpenStreetMap per Modelli 3D (servizio/edifici_osm.py, decisione di Paolo del 07/11/2026): edifici OSM intorno
# al punto dall'API Overpass dove non c'è un archivio DBTR. EDIFICI_OSM=false lo spegne (la rotta risponde 404).
EDIFICI_OSM = os.environ.get("EDIFICI_OSM", "true").lower() not in ("false", "0", "no", "spento")
# (09/11/2026) EDIFICI_OSM_ORA conta solo le richieste che vanno davvero a Overpass o al WFS regionale (cella non in copia),
# comprese le tessere OSM dei «Contorni degli edifici»; le celle in copia contano in EDIFICI_OSM_COPIA_ORA
EDIFICI_OSM_ORA = int(os.environ.get("EDIFICI_OSM_ORA", "300"))            # richieste a Overpass per IP all'ora
EDIFICI_OSM_COPIA_ORA = int(os.environ.get("EDIFICI_OSM_COPIA_ORA", "3000"))  # richieste servite dalla copia per IP all'ora
EDIFICI_OSM_TETTO_ORA = int(os.environ.get("EDIFICI_OSM_TETTO_ORA", "300"))  # chiamate a Overpass all'ora per tutto il sito
EDIFICI_OSM_GIORNI = int(os.environ.get("EDIFICI_OSM_GIORNI", "30"))       # validità della copia su disco di una cella
EDIFICI_OSM_ATTESA_S = float(os.environ.get("EDIFICI_OSM_ATTESA_S", "15"))  # attesa massima del turno (una chiamata alla volta)
EDIFICI_OSM_TIMEOUT_S = float(os.environ.get("EDIFICI_OSM_TIMEOUT_S", "30"))  # per istanza di Overpass (due istanze + attesa < 100 s di Cloudflare)
# istanze di Overpass (separate da virgola, in ordine); vuoto = quelle dello strato «osm_edifici» (ortofoto/strati/edifici.toml)
EDIFICI_OSM_URL = [u.strip() for u in os.environ.get("EDIFICI_OSM_URL", "").split(",") if u.strip()]
# sagome regionali al volo con le altezze OSM (08/11/2026, servizio/edifici_osm.py, edifici3d/sagome_regionali.py): dove la
# Regione pubblica le sagome aperte senza altezze (Veneto, IODL 2.0) la rotta /api/edifici/osm dà quelle sagome con le
# altezze di OpenStreetMap. EDIFICI_REGIONALI=false le spegne (resta il ripiego OSM di prima).
EDIFICI_REGIONALI = os.environ.get("EDIFICI_REGIONALI", "true").lower() not in ("false", "0", "no", "spento")
EDIFICI_REGIONALI_TETTO_ORA = int(os.environ.get("EDIFICI_REGIONALI_TETTO_ORA", "300"))   # chiamate ai WFS regionali all'ora
EDIFICI_REGIONALI_TIMEOUT_S = float(os.environ.get("EDIFICI_REGIONALI_TIMEOUT_S", "30"))
# istanza di riserva di Overpass comune allo strato OSM e al ripiego (07/11/2026: Overpass API Europa, ovp.dresel.systems,
# al posto di maps.mail.ru): assente = quella del TOML; presente ma vuota = nessuna riserva (se dal server non risponde)
OVERPASS_RISERVA = ([u.strip() for u in os.environ["OVERPASS_RISERVA"].split(",") if u.strip()]
                    if "OVERPASS_RISERVA" in os.environ else None)

# confronto PVGIS (fase 10, Fase B; servizio/pvgis.py): chiamato dal server (PVGIS non ha CORS), con copia delle risposte
PVGIS_URL = os.environ.get("PVGIS_URL", "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc")
PVGIS_AL_SECONDO = float(os.environ.get("PVGIS_AL_SECONDO", "20"))       # il JRC ammette 30 chiamate/s per IP: margine
PVGIS_ORA = int(os.environ.get("PVGIS_ORA", "60"))                        # confronti per IP all'ora
PVGIS_CACHE_GIORNI = int(os.environ.get("PVGIS_CACHE_GIORNI", "90"))
# orizzonte lontano dal Copernicus DEM 90 m (servizio/orizzonte.py, stessi file .om su S3 della fase 3)
# terreno della pagina 3D su richiesta (07/11/2026, servizio/terreno.py): DTM come COG in CARTELLA_TERRENO (comando
# dtm-server della fase 10), tessere Terrarium copiate in CARTELLA_TERRENO_TESSERE
TERRENO_ATTIVO = os.environ.get("TERRENO_ATTIVO", "true").lower() != "false"
CARTELLA_TERRENO = Path(os.environ.get("CARTELLA_TERRENO", str(DATI / "terreno")))
CARTELLA_TERRENO_TESSERE = Path(os.environ.get("CARTELLA_TERRENO_TESSERE", str(DATI / "terreno_tessere")))
TERRENO_ZOOM_MIN = int(os.environ.get("TERRENO_ZOOM_MIN", "8"))
TERRENO_MAX_GB = float(os.environ.get("TERRENO_MAX_GB", "5"))
TERRENO_CACHE_S = int(os.environ.get("TERRENO_CACHE_S", "2592000"))      # 30 giorni
TERRENO_ORA = int(os.environ.get("TERRENO_ORA", "6000"))                 # tessere da generare per IP all'ora (09/11/2026: 3000 → 6000)
TERRENO_PARALLELE = int(os.environ.get("TERRENO_PARALLELE", "2"))        # tessere generate insieme
TERRENO_ATTESA_S = float(os.environ.get("TERRENO_ATTESA_S", "10"))
ORIZZONTE_RAGGIO_KM = float(os.environ.get("ORIZZONTE_RAGGIO_KM", "25"))
ORIZZONTE_ORA = int(os.environ.get("ORIZZONTE_ORA", "120"))               # profili per IP all'ora

# pagina di stato interna degli edifici (fase 10, Fase C; servizio/interno.py): Cloudflare Access verificato sul server.
# Team domain (es. <team>.cloudflareaccess.com) e audience (AUD tag dell'applicazione Access) solo nel .env; senza i due
# valori le rotte /api/interno/* rispondono 503. CF_ACCESS_EMAIL: email ammesse (facoltativo, separate da virgola).
CF_ACCESS_TEAM_DOMAIN = os.environ.get("CF_ACCESS_TEAM_DOMAIN", "")
CF_ACCESS_AUD = os.environ.get("CF_ACCESS_AUD", "")
CF_ACCESS_EMAIL = os.environ.get("CF_ACCESS_EMAIL", "")
EDIFICI_STATO = Path(os.environ.get("EDIFICI_STATO", str(DATI / "edifici_stato")))          # stato.json della pipeline
CARTELLA_EDIFICI_INTERNA = Path(os.environ.get("CARTELLA_EDIFICI_INTERNA", str(DATI / "edifici")))
INTERNO_ORA = int(os.environ.get("INTERNO_ORA", "300"))                   # richieste per IP all'ora alle rotte interne

# «Aggiungi DBTR» (07/11/2026, decisione di Paolo; servizio/dbtr_coda.py): DB topografici caricati dagli utenti (solo con
# il loro consenso) in una coda sul server, preparati dal servizio edifici-coda e messi nell'archivio comune solo dopo
# l'approvazione nella pagina interna. File a pezzi (Cloudflare accetta al più 100 MB per richiesta; Caddy 40 MB su
# /api/dbtr/*). DBTR_CODA=false spegne il caricamento (404); la lettura nel browser resta.
DBTR_CODA = os.environ.get("DBTR_CODA", "true").lower() not in ("false", "0", "no", "spento")
CARTELLA_CODA_DBTR = Path(os.environ.get("CARTELLA_CODA_DBTR", str(DATI / "edifici_coda")))
DBTR_MAX_MB = float(os.environ.get("DBTR_MAX_MB", "300"))                 # dimensione massima di un file (zip o GeoPackage)
DBTR_PEZZO_MB = float(os.environ.get("DBTR_PEZZO_MB", "32"))              # pezzo di ogni richiesta (sotto i 40 MB di Caddy)
DBTR_CARICAMENTI_GIORNO = int(os.environ.get("DBTR_CARICAMENTI_GIORNO", "3"))  # file proposti per IP ogni 24 ore
DBTR_PEZZI_ORA = int(os.environ.get("DBTR_PEZZI_ORA", "60"))              # pezzi per IP all'ora (60 × 32 MB)
DBTR_CODA_MAX = int(os.environ.get("DBTR_CODA_MAX", "20"))                # richieste aperte (non ancora approvate o rifiutate)
DBTR_CODA_MAX_GB = float(os.environ.get("DBTR_CODA_MAX_GB", "4"))         # spazio occupato dalla coda
DBTR_LIBERO_MIN_GB = float(os.environ.get("DBTR_LIBERO_MIN_GB", "10"))    # spazio libero che deve restare sul disco
