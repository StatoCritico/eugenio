"""Open-Meteo: una risposta troncata (JSON interrotto a metà, 4/11/2026) si riprova invece di fermare l'aggiornamento."""
import json

import httpx
import pandas as pd

from meteo_storico import scarica
from meteo_storico.limiti import Limitatore


def test_json_troncato_si_riprova(tmp_path, monkeypatch):
    monkeypatch.setattr(scarica.time, "sleep", lambda s: None)
    buono = {"hourly": {"time": [0, 3600], "temperature_2m": [1.0, 2.0]}}
    risposte = [httpx.Response(200, content=json.dumps(buono)[:30].encode(),
                               headers={"content-type": "application/json"}),
                httpx.Response(200, json=buono)]
    http = httpx.Client(transport=httpx.MockTransport(lambda req: risposte.pop(0)))
    lim = Limitatore(tmp_path / "stato_api.json", illimitato=True)
    out = scarica.richiesta(http, lim, "https://esempio/v1/archive", pd.DataFrame({"lat": [44.5], "lon": [11.3]}),
                            "icon_seamless", forecast_days=1, variabili=["temperature_2m"])
    assert not risposte and len(out) == 1 and list(out[0].temperature_2m) == [1.0, 2.0]
