"""Scaricatore (scarica.py) con httpx.MockTransport: niente rete, niente indirizzi fissi dei file."""
from __future__ import annotations

import json

import httpx
import pytest

from suolo import scarica as S

CARTELLA = """<a href="https://g.invalid/library/consumo-di-suolo/indicatori/consumo_suolo_2025_com_prov_reg_naz_v2.0/download/en/1/consumo_suolo_2025_Com_Prov_Reg_Naz_v2.0.xlsx">a</a>
<a href="https://g.invalid/library/consumo-di-suolo/indicatori/consumo_suolo_2026_com_prov_reg_naz_v1.0/download/en/1/consumo_suolo_2026_Com_Prov_Reg_Naz_v1.0.xlsx">b</a>
<a href="https://g.invalid/library/consumo-di-suolo/indicatori/consumo_suolo_2026_com_prov_reg_naz_v1.10/download/en/1/consumo_suolo_2026_Com_Prov_Reg_Naz_v1.10.xlsx">c</a>
<a href="https://g.invalid/library/consumo-di-suolo/indicatori/consumo_suolo_2026_com_prov_reg_naz_v1.9/download/en/1/consumo_suolo_2026_Com_Prov_Reg_Naz_v1.9.xlsx">d</a>
<a href="https://g.invalid/library/consumo-di-suolo/indicatori/stato_del_territorio_2026_v1.0/download/en/1/stato_del_territorio_2026_v1.0.xlsx">e</a>"""


def test_file_con_anno_e_versione_piu_alti():
    f = S.file_indicatori(CARTELLA)
    assert f["nome"] == "consumo_suolo_2026_Com_Prov_Reg_Naz_v1.10.xlsx" and f["anno"] == 2026 and f["versione"] == "1.10"
    assert S.file_indicatori("<html>niente</html>") is None


def _client(contatori, csv_coltivazioni="DATAFLOW,X\n1,2\n", cartella=CARTELLA):
    def risposta(req: httpx.Request) -> httpx.Response:
        u = str(req.url)
        contatori.append(u)
        if u.endswith("/indicatori"):
            return httpx.Response(200, text=cartella)
        if u.endswith(".xlsx"):
            return httpx.Response(200, content=b"PK-finto-excel")
        if "COLTIVAZIONI" in u:
            assert req.headers["Accept"].startswith("application/vnd.sdmx.data+csv") and "startPeriod=2006" in u
            return httpx.Response(200, text=csv_coltivazioni)
        if "CENSAGRIC2020" in u:
            return httpx.Response(200, text="DATAFLOW,Y\n3,4\n")
        return httpx.Response(404)
    return httpx.Client(transport=httpx.MockTransport(risposta))


def test_scarica_e_cambiamenti(tmp_path):
    chiamate = []
    e = S.scarica(tmp_path, client=_client(chiamate), pausa=0)
    assert e["cambiati"] == ["ispra", "coltivazioni", "censimento2020"]
    assert (tmp_path / "ispra_indicatori.xlsx").read_bytes() == b"PK-finto-excel"
    stato = json.loads((tmp_path / "stato_scarico.json").read_text())
    assert stato["ispra"]["nome"].endswith("v1.10.xlsx") and stato["ispra"]["versione"] == "1.10"
    # di nuovo: niente di cambiato, l'Excel non si riscarica
    chiamate.clear()
    e = S.scarica(tmp_path, client=_client(chiamate), pausa=0)
    assert e["cambiati"] == [] and not any(u.endswith(".xlsx") for u in chiamate)
    # ISTAT cambia: solo le coltivazioni
    e = S.scarica(tmp_path, client=_client([], csv_coltivazioni="DATAFLOW,X\n1,3\n"), pausa=0)
    assert e["cambiati"] == ["coltivazioni"]


def test_risposte_sbagliate(tmp_path):
    with pytest.raises(RuntimeError, match="nessun file"):
        S.scarica(tmp_path, client=_client([], cartella="<html></html>"), pausa=0)
    with pytest.raises(RuntimeError, match="ISTAT"):
        S.scarica(tmp_path, client=_client([], csv_coltivazioni="<html>errore</html>"), pausa=0)


def test_carte_piu_recenti():
    pagine = {
        S.CARTELLA_CONSUMO: '<a href="https://g.invalid/library/consumo-di-suolo/carta-nazionale-consumo-suolo-2024">x</a>'
                            '<a href="https://g.invalid/library/consumo-di-suolo/carta-nazionale-consumo-suolo-2025/">y</a>',
        "https://g.invalid/library/consumo-di-suolo/carta-nazionale-consumo-suolo-2025":
            '<a href="https://g.invalid/c25/cambiamenti-2024-2025">c</a>',
        "https://g.invalid/c25/cambiamenti-2024-2025":
            '<a href="https://g.invalid/c25/cambiamenti-2024-2025/consumo_suolo_2024-2025_2p5/download/en/1/consumo_suolo_2024-2025_2p5.tif">a</a>'
            '<a href="https://g.invalid/c25/cambiamenti-2024-2025/consumo_suolo_2024-2025/download/en/1/consumo_suolo_2024-2025.tif">b</a>',
        S.CARTELLA_USO: '<a href="https://g.invalid/uso/uso-del-suolo-2022">u</a><a href="https://g.invalid/uso/uso-del-suolo-2023">v</a>',
        "https://g.invalid/uso/uso-del-suolo-2023": '<a href="https://g.invalid/uso/x/download/en/1/Uso_del_suolo_2023.tif">t</a>',
    }
    c = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, text=pagine.get(str(r.url), "")) ))
    k = S.carte_recenti(c)
    assert k["cambiamenti"]["nome"] == "consumo_suolo_2024-2025.tif" and k["cambiamenti"]["periodo"] == "2024-2025"
    assert k["uso"]["nome"] == "Uso_del_suolo_2023.tif" and k["uso"]["anno"] == 2023
