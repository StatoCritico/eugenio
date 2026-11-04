# Immagine unica per API e worker. Contesto di build: la cartella principale del progetto.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    HF_HOME=/dati/hf PYTHONPATH=/app

# font DejaVu per i report PDF (accenti, °C, €, ≥): presi dai pacchetti Debian durante la build, mai a runtime;
# il servizio li cerca in /usr/share/fonts/truetype/dejavu (variabile REPORT_FONT_DIR)
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core \
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
COPY fase4-server/servizio /app/servizio

RUN useradd --uid 1000 --create-home energia
USER energia
EXPOSE 8000
# --no-access-log: gli IP dei visitatori stanno solo nel registro di Caddy, che si cancella dopo 14 giorni
CMD ["uvicorn", "servizio.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-access-log"]
