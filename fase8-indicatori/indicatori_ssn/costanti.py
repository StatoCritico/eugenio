"""Costanti della fase 8: dataset, voci del modello CE, codici delle regioni, aziende di ReportER.

Tutto ciò che può cambiare da un anno all'altro (un nuovo dataset CE, un'azienda rinominata in ReportER)
si aggiorna qui.
"""
from __future__ import annotations

# ------------------------------------------------------------------------------------------- OpenBDAP (RGS)
CKAN = "https://bdap-opendata.rgs.mef.gov.it/SpodCkanApi/api/3"
# Modello CE per ente: ID della risorsa CKAN (lo stesso usato da datastore/dump/<ID>.csv)
DATASET_CE = {
    2025: "27575c1c-655f-4c54-b9f7-54ea438143c6",   # IV trimestre, provvisorio (progressivo annuo)
    2024: "94083af2-a542-482d-8ad6-5877d04cd1ca",
    2023: "57bb2cce-4fdd-4de1-88b5-8e7551408481",
    2022: "5afc4cf8-a13e-4fb6-a81b-61896de5f9ea",
    2021: "7ed66089-fc41-4643-a110-d82dd2622f5b",
    2020: "41838a8d-33a1-4f4c-a4e8-1cba74b81e03",
    2019: "481179f0-2574-4e33-8479-8f1f5729090c",
    2018: "df1a970c-e570-403d-8f9a-1b736ee7e88f",
    2017: "e8e7721f-4871-49b7-afc6-1e5b97049891",
    2016: "1911b316-cb99-4561-a065-6033f0345c26",
    2015: "0aa5fab4-d4fe-40ec-a679-0c88309b0042",
}
ANNI = sorted(DATASET_CE)
PROVVISORI = {2025}          # anni con il solo CE del IV trimestre

# voci del modello CE (codici identici 2015–2025)
VOCI = {
    "BA1610": "Riscaldamento",
    "BA1660": "Utenze elettricità",
    "BA1670": "Altre utenze (gas, acqua)",
    "BA0340": "Combustibili, carburanti e lubrificanti",   # riportata a parte, esclusa dal totale
    "BA1650": "Utenze telefoniche",                        # esclusa
    "AZ9999": "Totale valore della produzione (A)",
    "BZ9999": "Totale costi della produzione (B)",
}
COMPONENTI = ["BA1610", "BA1660", "BA1670"]                # il totale energia e utenze è la loro somma
# voci pubblicate nei JSON (BA1650, telefonia, non serve a nulla e non si pubblica)
VOCI_USCITA = ["BA1610", "BA1660", "BA1670", "BA0340", "AZ9999", "BZ9999"]

CONSOLIDATO = "999"          # conto economico consolidato regionale
GSA = "000"                  # gestione sanitaria accentrata (esclusa dagli enti, spiegata in pagina)

# regioni e province autonome nel CE (codice a 3 cifre) → codice ISTAT a 2 cifre della mappa del sito,
# codice del servizio SDMX ISTAT (REF_AREA) e nome
REGIONI_CE = {
    "010": ("01", "ITC1", "Piemonte"),
    "020": ("02", "ITC2", "Valle d'Aosta"),
    "030": ("03", "ITC4", "Lombardia"),
    "041": ("04", "ITD1", "Provincia autonoma di Bolzano"),
    "042": ("04", "ITD2", "Provincia autonoma di Trento"),
    "050": ("05", "ITD3", "Veneto"),
    "060": ("06", "ITD4", "Friuli-Venezia Giulia"),
    "070": ("07", "ITC3", "Liguria"),
    "080": ("08", "ITD5", "Emilia-Romagna"),
    "090": ("09", "ITE1", "Toscana"),
    "100": ("10", "ITE2", "Umbria"),
    "110": ("11", "ITE3", "Marche"),
    "120": ("12", "ITE4", "Lazio"),
    "130": ("13", "ITF1", "Abruzzo"),
    "140": ("14", "ITF2", "Molise"),
    "150": ("15", "ITF3", "Campania"),
    "160": ("16", "ITF4", "Puglia"),
    "170": ("17", "ITF5", "Basilicata"),
    "180": ("18", "ITF6", "Calabria"),
    "190": ("19", "ITG1", "Sicilia"),
    "200": ("20", "ITG2", "Sardegna"),
}
NOMI_REGIONI_MAPPA = {
    "01": "Piemonte", "02": "Valle d'Aosta", "03": "Lombardia", "04": "Trentino-Alto Adige", "05": "Veneto",
    "06": "Friuli-Venezia Giulia", "07": "Liguria", "08": "Emilia-Romagna", "09": "Toscana", "10": "Umbria",
    "11": "Marche", "12": "Lazio", "13": "Abruzzo", "14": "Molise", "15": "Campania", "16": "Puglia",
    "17": "Basilicata", "18": "Calabria", "19": "Sicilia", "20": "Sardegna",
}

# ------------------------------------------------------------------------------------- ReportER (SISEPS)
REPORTER = "https://reporter.regione.emilia-romagna.it/ReportERHomeService/methods/stats"
# (flusso, ambito, sottoambito, scheda), filtro dell'anno e filtri fissi {id: valore}
REPORT_GIORNATE = {
    "coordinate": (10, 2, 1, 2), "nome": "SDO – Giornate (STATS-10-2-1-2)",
    "anno": "DII_4F31BE1D2905CD43C8FC0",
    "fissi": {"DII_39596": "PUB"},                     # tipo presidio: ospedali pubblici
    "regime": "DII_CC997921392AD99330B9F",             # 001 degenza ordinaria, 002 day hospital
}
REPORT_POSTI_LETTO = {
    "coordinate": (13, 1, 1, 1), "nome": "Posti letto per bilancio annuale (STATS-13-1-1-1)",
    "anno": "DII_D52F00EF9C934F033813A",               # data di rilevazione: 31/12 dell'anno
    "fissi": {"DII_95FA321823A416C50C315": "1 "},      # tipo presidio: strutture pubbliche (con lo spazio)
}
REPORT_POPOLAZIONE = {
    "coordinate": (23, 1, 1, 1), "nome": "Popolazione (STATS-23-1-1-1)",
    "anno": "DII_14F50D3A78F8C6AB3A6A4",               # residenti al 31/12 dell'anno
    "fissi": {},
}
# aziende di ReportER → codice ente del CE (regione 080)
AZIENDE_REPORTER = {
    "PIACENZA": "101", "PARMA": "102", "REGGIO EMILIA": "103", "MODENA": "104", "BOLOGNA": "105",
    "IMOLA": "106", "FERRARA": "109", "ROMAGNA": "114",
    "AOSPU PARMA": "902", "AOSP REGGIO EMILIA": "903", "AOSPU MODENA": "904",
    "AOSPU BOLOGNA": "908", "IRCCS S. ORSOLA": "908", "AOSPU FERRARA": "909", "I.O.R.": "960",
}
REGIONE_REPORTER = "080"

# ------------------------------------------------------------------------------------------------- ISTAT
SDMX = "https://esploradati.istat.it/SDMXWS/rest"
# popolazione residente al 1° gennaio: censimento permanente (dal 1/1/2019) e ricostruzione intercensuaria
FLUSSO_POP = "22_289"
FLUSSO_POP_RICOSTRUITA = "164_164_DF_DCIS_RICPOPRES2011_1"
PRIMO_ANNO_CENSIMENTO = 2019   # anno di riferimento (31/12) dal quale si usa 22_289 (popolazione al 1/1/2020)

# ------------------------------------------------------------------------------------------- attribuzioni
FONTI = [
    {"id": "openbdap", "testo": "Ragioneria Generale dello Stato – OpenBDAP, Modello di rilevazione del Conto "
     "Economico degli enti del SSN (anni 2015–2025)", "url": "https://bdap-opendata.rgs.mef.gov.it/tema/sanit%C3%A0",
     "licenza": "CC BY 4.0", "licenza_url": "https://creativecommons.org/licenses/by/4.0/deed.it"},
    {"id": "reporter", "testo": "Regione Emilia-Romagna – ReportER (SISEPS): giornate di degenza (Banca dati SDO), "
     "posti letto (Anagrafe strutture), popolazione residente per Azienda USL",
     "url": "https://salute.regione.emilia-romagna.it/siseps/reporter",
     "licenza": "CC BY 4.0", "licenza_url": "https://www.regione.emilia-romagna.it/note-legali"},
    {"id": "istat", "testo": "ISTAT – Popolazione residente al 1° gennaio di Italia, regioni e province autonome "
     "(ricostruzione intercensuaria 2002–2019 e censimento permanente; 1/1/2026 stima)", "url": "https://demo.istat.it/",
     "licenza": "CC BY 4.0", "licenza_url": "https://www.istat.it/note-legali/"},
]
ELABORAZIONE = "Elaborazione di EuGEnio (Stato Critico) sui dati originali: somme, rapporti e abbinamento dei codici."
# Licenza delle elaborazioni (eugenio.statocritico.it/licenza.html#dati): CC BY 4.0, riuso citando EuGEnio come fonte
CITAZIONE = "Fonte: EuGEnio – eugenio.statocritico.it"
LICENZA = ("Elaborazioni di EuGEnio con licenza CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/deed.it): "
           "si possono riutilizzare, anche modificate, citando EuGEnio come fonte nei documenti che le usano e "
           "mantenendo le fonti originali indicate in «fonti», che restano soggette alle loro licenze. "
           "Dettagli: https://eugenio.statocritico.it/licenza.html#dati")


def citazione(aggiornato) -> str:
    """Formula di citazione con la data dei dati (date o testo ISO)."""
    import datetime as _dt
    d = _dt.date.fromisoformat(aggiornato) if isinstance(aggiornato, str) else aggiornato
    return f"{CITAZIONE} (dati aggiornati il {d:%d/%m/%Y})"
