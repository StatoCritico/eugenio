# syntax=docker/dockerfile:1
# EuGEnio Visure – versione Docker del lettore (per enti e per chi preferisce non installare Python).
# Contesto: la cartella fase11-visure, più il contesto «fase10» (convertitore dei modelli DXF/IFC, dal 04/11/2026).
#   docker build --build-context fase10=../fase10-edifici3d -f docker/Dockerfile -t eugenio-visure:0.1.0 .
# Uso a riga di comando, senza rete:
#   docker run --rm --network none -v "$PWD/lavoro:/lavoro" eugenio-visure:0.1.0 leggi /lavoro/visure --uscita /lavoro/risultati
#   docker run --rm --network none -v "$PWD/lavoro:/lavoro" eugenio-visure:0.1.0 modello /lavoro/edificio.ifc --uscita /lavoro/modello.geojson
# Pagina locale (porta pubblicata solo sul 127.0.0.1 del PC): docker compose -f docker/docker-compose.yml up
FROM python:3.13-slim

LABEL org.opencontainers.image.title="EuGEnio Visure" \
      org.opencontainers.image.description="Lettore locale delle visure catastali in PDF (nessuna credenziale, nessun accesso a SISTER)" \
      org.opencontainers.image.source="https://github.com/statocritico/eugenio" \
      org.opencontainers.image.licenses="AGPL-3.0-only"

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
COPY requirements.txt requirements-modelli.txt /app/
# dietro un proxy aziendale che ispeziona HTTPS: --secret id=ca_proxy,src=certificato.crt (non resta nell'immagine)
RUN --mount=type=secret,id=ca_proxy,required=false \
    if [ -f /run/secrets/ca_proxy ]; then export PIP_CERT=/run/secrets/ca_proxy; fi; \
    pip install -r /app/requirements.txt -r /app/requirements-modelli.txt \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin visure
COPY visure /app/visure
# lo stesso convertitore di `importa-modello` (fase 10): solo questi due file, niente dati né modulo privato
COPY --from=fase10 edifici3d/__init__.py edifici3d/importa.py /app/edifici3d/
WORKDIR /lavoro
ENV PYTHONPATH=/app
USER visure
# il controllo di avvio deve passare già nella costruzione dell'immagine
RUN python -m visure prova --modelli
HEALTHCHECK --interval=60s --timeout=5s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8770/salute', timeout=3).status == 200 else 1)" || exit 1
EXPOSE 8770
ENTRYPOINT ["python", "-m", "visure"]
CMD ["web", "--host", "0.0.0.0", "--porta", "8770", "--non-aprire"]
