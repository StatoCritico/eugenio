"""Configurazione da variabili d'ambiente (file .env letto da docker compose)."""
from __future__ import annotations

import os
from pathlib import Path

DATI = Path(os.environ.get("DATI", "/dati"))
REGIONI = [r.strip().zfill(2) for r in os.environ.get("REGIONI", "08").split(",") if r.strip()]
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
