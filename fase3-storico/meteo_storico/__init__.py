"""Archivio meteo storico per comune da Open-Meteo, con correzione ERA5 sul periodo di sovrapposizione.

Fonti:
  * ERA5-Seamless (ECMWF/Copernicus via Open-Meteo, archive API): serie lunga e omogenea;
  * Historical Forecast ICON seamless (DWD ICON-D2/EU/global via Open-Meteo): stessi modelli
    usati per le previsioni, disponibile da novembre 2022.

Tutti i dati sono in UTC; le aggregazioni giornaliere sono per giorno civile Europe/Rome.
Dati: Open-Meteo.com, CC BY 4.0. Confini e codici: ISTAT, CC BY 4.0 (via Gramscii).
"""
__version__ = "1.0.0"

VARIABILI = [
    "temperature_2m",        # °C
    "relative_humidity_2m",  # %
    "shortwave_radiation",   # W/m² (media dell'ora precedente)
    "diffuse_radiation",     # W/m²
    "wind_speed_10m",        # km/h
    "cloud_cover",           # %
    "precipitation",         # mm
    "snowfall",              # cm
]
