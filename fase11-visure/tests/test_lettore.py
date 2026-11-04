"""Lettore delle visure: PDF sintetici (formato «attuale» e «a tabella», per immobile e per soggetto, fabbricati e
terreni), piani, numeri, dati personali tenuti fuori, regole sostituibili."""
import csv
import json

import pytest

from visure import lettore, piani
from visure.regole import carica
from visure.sintetici import ATTESI, ESITI_ATTESI, PERSONALI


@pytest.mark.parametrize("nome", sorted(ATTESI))
def test_unita_attese(sintetici, nome):
    v = lettore.leggi_pdf(sintetici / nome)
    assert v.esito == "letta"
    assert len(v.unita) == len(ATTESI[nome])
    for u, att in zip(v.unita, ATTESI[nome]):
        for k, x in att.items():
            assert u.get(k) == x, (nome, k, u.get(k), x)


@pytest.mark.parametrize("nome,esito", sorted(ESITI_ATTESI.items()))
def test_documenti_scartati(sintetici, nome, esito):
    v = lettore.leggi_pdf(sintetici / nome)
    assert v.esito == esito and not v.unita and v.nota


def test_pdf_rovinato(tmp_path):
    p = tmp_path / "rotto.pdf"
    p.write_bytes(b"%PDF-1.4 non un vero pdf")
    v = lettore.leggi_pdf(p)
    assert v.esito == "errore" and "non leggibile" in v.nota


def test_tipo_e_data(sintetici):
    v = lettore.leggi_pdf(sintetici / "visura_soggetto_tabella.pdf")
    assert v.tipo_visura == "per soggetto" and v.data_visura == "04/11/2026"
    assert {u["formato"] for u in v.unita} == {"tabella"}
    v = lettore.leggi_pdf(sintetici / "visura_immobile_B2_attuale.pdf")
    assert v.tipo_visura == "per immobile" and v.unita[0]["formato"] == "etichette"


def test_d4_senza_consistenza_e_ok(sintetici):
    v = lettore.leggi_pdf(sintetici / "visura_soggetto_tabella.pdf")
    d4 = [u for u in v.unita if u.get("categoria") == "D/4"][0]
    assert d4["esito"] == "ok" and d4.get("consistenza") is None


def test_nessun_dato_personale_nelle_unita(sintetici):
    for nome in ATTESI:
        v = lettore.leggi_pdf(sintetici / nome)
        assert v.righe_personali > 0
        assert not v.intestatari
        testo = json.dumps(v.unita, ensure_ascii=False)
        for s in PERSONALI:
            assert s not in testo, (nome, s)


def test_intestatari_solo_su_richiesta(sintetici):
    v = lettore.leggi_pdf(sintetici / "visura_immobile_A2_attuale.pdf", includi_intestatari=True)
    cf = {i["codici_fiscali"] for i in v.intestatari}
    assert {"PRVLCU75B41H294K", "TSTGNN62C12D704W"} <= cf
    # anche con l'opzione, i campi dell'unità restano senza dati personali
    assert "PRVLCU75B41H294K" not in json.dumps(v.unita)


def test_regole_utente_sostituiscono(tmp_path, sintetici):
    # una variante ipotetica: la consistenza scritta «Cons.» invece di «Consistenza»
    pagine = ["Visura per immobile\nCatasto Fabbricati\nImmobile n. 1\nComune di RAVENNA (H199)\n"
              "Foglio 3 Particella 44 Subalterno 1\nCategoria C/1, Classe 4, Cons. 55 m²\nRendita: Euro 1.200,00\n"
              "Indirizzo: VIA NUOVA n. 1 Piano T\nTotale: 60 m²"]
    u = lettore.leggi_testo(pagine).unita[0]
    assert u.get("consistenza") is None
    f = tmp_path / "mie.toml"
    f.write_text("[campi]\nconsistenza = ['cons(?:istenza|\\.)?:?\\s*([0-9][0-9.,]*)\\s*(vani|m²|m³)']\n", encoding="utf-8")
    R = carica(f)
    u = lettore.leggi_testo(pagine, R).unita[0]
    assert u["consistenza"] == 55 and u["unita_consistenza"] == "m²" and u["esito"] == "ok"
    # le altre voci restano quelle del pacchetto
    assert R.lista("campi", "foglio")


@pytest.mark.parametrize("testo,livelli,riass", [
    ("T-1-2", [0, 1, 2], {"piani_fuori_terra": 3, "piani_interrati": 0, "piano_piu_alto": "2"}),
    ("S1-T", [-1, 0], {"piani_fuori_terra": 1, "piani_interrati": 1, "piano_piu_alto": "T"}),
    ("PT", [0], {"piani_fuori_terra": 1}),
    ("piano terra", [0], {"piani_fuori_terra": 1}),
    ("S2-S1-T-1", [-2, -1, 0, 1], {"piani_interrati": 2, "piani_fuori_terra": 2}),
    ("1°-2°", [1, 2], {"piani_fuori_terra": 3}),
    ("da 1 a 3", [1, 2, 3], {"piano_piu_alto": "3"}),
    ("-1", [-1], {"piani_interrati": 1, "piani_fuori_terra": 0}),
    ("R", [0], {"piani": "T"}),
    ("T-1-sottotetto", [0, 1], {"piani": "T;1;sottotetto", "piani_fuori_terra": 2}),
    ("2-ammezzato", [2], {"piani": "2;ammezzato"}),
    ("", [], {"piani_fuori_terra": None}),
])
def test_piani(testo, livelli, riass):
    liv, altri = piani.livelli(testo)
    assert liv == livelli
    r = piani.riassumi(liv, altri)
    for k, v in riass.items():
        assert r[k] == v


@pytest.mark.parametrize("s,n", [("1.880,00", 1880.0), ("6,5", 6.5), ("1.250", 1250.0), ("98", 98.0),
                                 ("Euro 568,10", 568.1), ("", None), ("vani", None)])
def test_numero(s, n):
    assert lettore.numero(s) == n


def test_indice_csv_senza_personali(sintetici, tmp_path):
    from visure.uscite import scrivi
    vv = [lettore.leggi_pdf(p) for p in sorted(sintetici.glob("*.pdf"))]
    scrivi(tmp_path, vv)
    testo = "".join(p.read_text(encoding="utf-8") for p in tmp_path.iterdir() if p.is_file())
    for s in PERSONALI:
        assert s not in testo
    assert not (tmp_path / "intestatari_DATI_PERSONALI.csv").exists()
    righe = list(csv.DictReader((tmp_path / "indice.csv").read_text(encoding="utf-8-sig").splitlines(), delimiter=";"))
    assert len(righe) == sum(len(x) for x in ATTESI.values())
    assert righe[0]["consistenza"] in ("42300", "5,5")   # virgola decimale per Excel in italiano


VARIANTI = {
    # etichette con i due punti, «Mappale», «Sub.», «mq», «€», piano dopo il punto e virgola
    "Visura per immobile\nCatasto Fabbricati\nComune di CESENATICO ( Codice: C574)\nUnità immobiliare n. 1\n"
    "Foglio: 12 Mappale: 345 Sub.: 7\nZona Cens.: 2 Micro Zona: 1 Categoria: C/1 Classe: 5 Consistenza: 48 mq\n"
    "Superficie catastale: 55 mq\nRendita: € 1.234,56\nIndirizzo: VIALE DEI MILLE n. 3 piano: T;":
        {"codice_comune": "C574", "particella": "345", "subalterno": "7", "categoria": "C/1", "consistenza": 48,
         "unita_consistenza": "m²", "superficie_catastale": 55, "rendita_euro": 1234.56, "piani": "T", "microzona": "1"},
    # sezione urbana, zeri iniziali, «Interno» dopo il piano, visura storica
    "Visura storica per immobile\nCatasto dei Fabbricati\nImmobile n. 1\nDati identificativi: Comune di SAN MAURO "
    "PASCOLI (I027) (FC)\nSezione urbana A Foglio 4 Particella 0098 Subalterno 12\nZona censuaria 1, Categoria A/3, "
    "Classe 2, Consistenza 4 vani\nRendita: Euro 280,02\nIndirizzo: VIA ROMA n. 1 Piano 1-2 Interno 4\n"
    "Dati di superficie: Totale: 75 m² Totale escluse aree scoperte: 72 m²":
        {"comune": "SAN MAURO PASCOLI", "sezione": "A", "particella": "98", "piani": "1;2", "indirizzo": "VIA ROMA n. 1",
         "superficie_escluse_aree_scoperte": 72},
    # unità collabente (F/2) senza consistenza né rendita; «VIA DEL PIANO» nell'indirizzo
    "Visura per immobile\nCatasto Fabbricati\nImmobile n. 1\nComune di RICCIONE (H274)\nFoglio 9 Particella 100 "
    "Subalterno 1\nCategoria F/2\nIndirizzo: VIA DEL PIANO n. 3 Piano T":
        {"categoria": "F/2", "esito": "ok", "indirizzo": "VIA DEL PIANO n. 3", "piani": "T"},
}


@pytest.mark.parametrize("testo,atteso", list(VARIANTI.items()))
def test_varianti_di_scrittura(testo, atteso):
    v = lettore.leggi_testo([testo])
    assert len(v.unita) == 1
    for k, x in atteso.items():
        assert v.unita[0].get(k) == x, (k, v.unita[0].get(k))
