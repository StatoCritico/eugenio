"""OpenBDAP in disservizio (28/10/2026: «Cannot convert data to csv» su tutti gli anni): niente 33 tentativi a vuoto,
copia in cache quando c'è, messaggio chiaro."""
import httpx
import pytest

from indicatori_ssn import bdap, cli
from indicatori_ssn.rete import FonteNonDisponibile, Rete

ANNI = [2015, 2016, 2017, 2018, 2019, 2020]


def test_openbdap_giu_si_ferma_e_usa_la_cache(tmp_path, monkeypatch):
    cartella = tmp_path / "bdap"
    cartella.mkdir()
    bdap.scrivi_cache([{"anno": "2018", "voce": "BA1660", "importo": "1.0"}], cartella / "ce_2018.csv")
    chiamate = []

    def guasto(rete, anno, cartella):
        chiamate.append(anno)
        raise FonteNonDisponibile("servizio non disponibile: Cannot convert data to csv")
    monkeypatch.setattr(bdap, "scarica_anno", guasto)
    righe, mancanti, giu = cli.scarica_ce(None, ANNI, cartella)
    assert chiamate == [2015, 2016]                      # dopo due anni di fila non si insiste
    assert giu and list(righe) == [2018] and righe[2018][0]["voce"] == "BA1660"
    assert mancanti == ["CE 2015", "CE 2016", "CE 2017", "CE 2019", "CE 2020"]


def test_un_anno_guasto_non_ferma_gli_altri(tmp_path, monkeypatch):
    chiamate = []

    def a_volte(rete, anno, cartella):
        chiamate.append(anno)
        if anno == 2016:
            raise FonteNonDisponibile("errore HTTP 500")
        f = cartella / f"ce_{anno}.csv"
        cartella.mkdir(exist_ok=True)
        bdap.scrivi_cache([], f)
        return f
    monkeypatch.setattr(bdap, "scarica_anno", a_volte)
    righe, mancanti, giu = cli.scarica_ce(None, ANNI, tmp_path / "bdap")
    assert chiamate == ANNI and not giu and mancanti == ["CE 2016"]


def test_messaggio_finale(tmp_path, monkeypatch):
    monkeypatch.setattr(bdap, "scarica_anno", lambda r, a, c: (_ for _ in ()).throw(FonteNonDisponibile("x")))
    monkeypatch.setattr(cli.reporter, "scarica", lambda rete, anni: {"dati": {}, "aggiornato": {}})
    monkeypatch.setattr(cli.istat, "scarica", lambda rete, anni, c: {"dati": {"IT": {a: 1 for a in ANNI}}, "serie": {}})
    with pytest.raises(FonteNonDisponibile, match="^OpenBDAP non disponibile; dati mancanti"):
        cli.aggiorna(tmp_path / "out", tmp_path / "cache", anni=ANNI)
    assert not (tmp_path / "out").exists()


def test_errore_json_del_portale_senza_nuovi_tentativi(tmp_path, monkeypatch):
    richieste = []

    def portale(req):
        richieste.append(req.url)
        return httpx.Response(200, json={"error": {"message": "Cannot convert data to csv", "__type": "Dataset Error"},
                                         "help": "", "success": False})
    monkeypatch.setattr("time.sleep", lambda s: None)
    rete = Rete(tmp_path / "http", pausa=0)
    rete.client = httpx.Client(transport=httpx.MockTransport(portale))
    with pytest.raises(FonteNonDisponibile, match="Cannot convert data to csv"):
        rete.richiesta("GET", "https://esempio/datastore/dump/x.csv", atteso="csv", flusso_in=tmp_path / "x.csv")
    assert len(richieste) == 1
