# Pipeline notturna degli edifici (fase 10, Fase C): container separato dall'api, 1 CPU e 4 GB (docker-compose.yml
# della fase 4, profilo «edifici»). Contesto di build: la cartella principale del progetto. Lanciato dal cron dell'host
# alle 3:30 (AGGIORNAMENTO_2026-11-04.md, § Fase C): la pipeline si ferma da sola alle 7:00.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*
COPY fase10-edifici3d/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
WORKDIR /app
COPY fase10-edifici3d /app
RUN useradd --uid 1000 --create-home energia
USER energia
ENTRYPOINT ["python", "-m", "edifici3d"]
CMD ["lidar", "--zona", "auto", "--archivio", "/dati/edifici", "--stato", "/dati/edifici_stato"]
