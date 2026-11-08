# Immagine unica per API e worker. Contesto di build: la cartella principale del progetto.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    HF_HOME=/dati/hf PYTHONPATH=/app

# font DejaVu per i report PDF (accenti, °C, €, ≥): presi dai pacchetti Debian durante la build, mai a runtime;
# il servizio li cerca in /usr/share/fonts/truetype/dejavu (variabile REPORT_FONT_DIR)
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core libexpat1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.1
COPY fase4-server/api/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

WORKDIR /app
COPY fase3-storico/meteo_storico /app/meteo_storico
COPY fase6-mercati/mercati_energia /app/mercati_energia
COPY fase7-territorio/territorio /app/territorio
# lavori periodici del worker: indicatori della sanità (fase 8) e clima dal 1940 (fase 9, script lanciati a parte)
COPY fase8-indicatori/indicatori_ssn /app/indicatori_ssn
COPY fase9-clima-storico/*.py /app/clima_storico/
# fonti delle ortofoto (fase 10, Fase B): un TOML per regione, letti da servizio/ortofoto.py
COPY fase10-edifici3d/ortofoto /app/ortofoto_fonti
# analisi 5 e 7–13 (Fase E): solo l'aggancio pubblico; il modulo privato uni_privato NON entra nell'immagine (si monta
# da /srv/energia/dati/uni_privato, che il container vede come /dati/uni_privato)
COPY fase10-edifici3d/edifici3d/__init__.py fase10-edifici3d/edifici3d/analisi.py /app/edifici3d/
# ripiego OpenStreetMap di Modelli 3D (07/11/2026, servizio/edifici_osm.py): il lettore OSM della fase 10 e quello che gli
# serve (corpi, feature GeoJSON); shapely e pyproj sono in requirements.txt
COPY fase10-edifici3d/edifici3d/modello.py fase10-edifici3d/edifici3d/osm.py fase10-edifici3d/edifici3d/osm_campione.py \
     fase10-edifici3d/edifici3d/tessere.py fase10-edifici3d/edifici3d/sagome_regionali.py /app/edifici3d/
# sagome regionali al volo con le altezze OSM (08/11/2026): fonti accese (Veneto)
COPY fase10-edifici3d/fonti/sagome_regionali.toml /app/fonti/sagome_regionali.toml
# altre regioni, un file per regione (08/11/2026: Sardegna WFS e Campania ArcGIS REST); la cartella c'è sempre (almeno il
# LEGGIMI). sagome_regionali.py importa solo osm_campione (sopra), pyproj e shapely: gli adattatori dei DB topografici
# (edifici3d/adattatori/, altezze_dsm.py, a_comuni.py, b_regioni.py, fonti/<regione>.toml) servono solo all'immagine
# energia-edifici (fase10-edifici3d/Dockerfile, che copia tutta la fase 10)
COPY fase10-edifici3d/fonti/sagome_regionali.d /app/fonti/sagome_regionali.d
# «Aggiungi DBTR» (07/11/2026, servizio/dbtr_coda.py): stati, nomi e controllo leggero dello zip della coda (in testa solo
# libreria standard; la preparazione la fa il servizio edifici-coda con l'immagine energia-edifici)
COPY fase10-edifici3d/edifici3d/coda.py /app/edifici3d/
# registro delle versioni (07/11/2026): la newsletter mensile mette le voci del mese nella sezione «Novità di EuGEnio»
COPY fase5-sito/novita.toml /app/novita.toml
COPY fase4-server/servizio /app/servizio

RUN useradd --uid 1000 --create-home energia
USER energia
EXPOSE 8000
# --no-access-log: gli IP dei visitatori stanno solo nel registro di Caddy, che si cancella dopo 14 giorni
CMD ["uvicorn", "servizio.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-access-log"]
