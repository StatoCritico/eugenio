"""Abbinamento delle unità agli edifici di Patrimonio, colonne visura_…, file d'uscita, riga di comando e parità con
il modulo JavaScript del sito (visure_abbina.js, con node)."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from visure import arricchisci as A
from visure import lettore
from visure.uscite import leggi_csv, scrivi

SITO = Path(__file__).resolve().parents[2] / "fase5-sito" / "sito"


def unita(sintetici):
    return [u for p in sorted(sintetici.glob("*.pdf")) for u in lettore.leggi_pdf(p).unita]


def test_abbina_per_nome_e_per_codice(sintetici):
    uu = unita(sintetici)
    patr = leggi_csv(sintetici / "patrimonio_esempio_visure.csv")
    out, sciolte = A.abbina(patr, uu)
    per = {r["id"]: r for r in out}
    # per nome del comune (file dell'utente): da verificare; Forlì = FORLI'
    assert per["E3"]["visura_esito"] == "verificare"
    assert per["E3"]["visura_subalterni"] == 3 and per["E3"]["visura_categorie"] == "A/10 ×2; C/6"
    assert per["E3"]["visura_uso"] == "uffici" and per["E3"]["visura_superficie_catastale"] == 365
    assert per["E3"]["visura_piani"] == "S1;T;1;2;3" and per["E3"]["visura_piani_fuori_terra"] == 4
    assert per["E1"]["visura_consistenza_m3"] == 42300 and per["E1"]["visura_uso"] == "ospedale"
    assert per["E6"]["visura_esito"] == "nessuna_visura"
    assert {(u["foglio"], u["particella"]) for u in sciolte} == {("90", "456"), ("200", "12")}
    # con il risultato della geolocalizzazione (belfiore, foglio_catasto, mappale): ok
    geo = [{"id": "G1", "belfiore": "H199", "foglio_catasto": "0120", "mappale": "01450", "comune_catasto": "RAVENNA"}]
    out, _ = A.abbina(geo, uu)
    assert out[0]["visura_esito"] == "ok" and out[0]["visura_unita"] == 1


def test_codice_comune_nel_file_e_sezione(sintetici):
    uu = unita(sintetici)
    out, _ = A.abbina([{"id": 1, "comune": "H294", "foglio": "77", "particella": "210"}], uu)
    assert out[0]["visura_esito"] == "ok"
    out, _ = A.abbina([{"id": 1, "comune": "H294", "sezione": "B", "foglio": "77", "particella": "210"}], uu)
    assert out[0]["visura_esito"] == "verificare"    # sezione solo da una parte
    uu2 = [dict(u, sezione="A") if u.get("particella") == "210" else u for u in uu]
    out, _ = A.abbina([{"id": 1, "comune": "H294", "sezione": "B", "foglio": "77", "particella": "210"}], uu2)
    assert out[0]["visura_esito"] == "nessuna_visura"  # sezioni diverse
    out, _ = A.abbina([{"id": 1, "comune": "Ravenna", "foglio": "77", "particella": "210"}], uu)
    assert out[0]["visura_esito"] == "nessuna_visura"  # comune diverso


def test_stessa_particella_in_piu_righe(sintetici):
    uu = unita(sintetici)
    out, _ = A.abbina([{"id": 1, "comune": "Rimini", "foglio": "77", "particella": "210"},
                       {"id": 2, "comune": "RIMINI", "foglio": "77", "particella": "0210"}], uu)
    assert all("stessa particella" in r["visura_nota"] for r in out)


def test_uscite_con_patrimonio(sintetici, tmp_path):
    vv = [lettore.leggi_pdf(p) for p in sorted(sintetici.glob("*.pdf"))]
    patr = leggi_csv(sintetici / "patrimonio_esempio_visure.csv")
    ris = scrivi(tmp_path, vv, patr, list(patr[0]), sorgenti={p.name: p for p in sintetici.glob("*.pdf")}, ordina=True)
    assert (tmp_path / "patrimonio_con_visure.csv").exists() and (tmp_path / "visure.json").exists()
    assert (tmp_path / "pdf" / "RAVENNA_H199" / "F120_P1450" / "sub_2.pdf").exists()
    assert (tmp_path / "pdf" / "per_soggetto" / "visura_soggetto_tabella.pdf").exists()
    reg = (tmp_path / "registro.txt").read_text(encoding="utf-8")
    assert "non abbinate" in reg and "senza_testo" in reg
    righe = leggi_csv(tmp_path / "patrimonio_con_visure.csv")
    assert list(righe[0])[:5] == ["id", "denominazione", "comune", "foglio", "particella"]
    assert righe[0]["visura_piani"] == "S1;T;1;2;3;4"
    assert ris["pdf_ordinati"] == 4
    d = json.loads((tmp_path / "visure.json").read_text(encoding="utf-8"))
    assert d["formato"] == "eugenio-visure" and len(d["unita"]) == 9


def test_patrimonio_con_visure_leggibile_da_fase7(sintetici, tmp_path):
    """Il CSV arricchito resta un file valido per Patrimonio (fase 7): stesse colonne di partenza riconosciute."""
    pytest.importorskip("pandas")
    pytest.importorskip("httpx")        # la fase 7 lo importa (client di Zornade)
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "fase7-territorio"))
    from territorio.patrimonio import leggi as leggi7
    vv = [lettore.leggi_pdf(p) for p in sorted(sintetici.glob("*.pdf"))]
    patr = leggi_csv(sintetici / "patrimonio_esempio_visure.csv")
    scrivi(tmp_path, vv, patr, list(patr[0]))
    df = leggi7(tmp_path / "patrimonio_con_visure.csv")
    assert {"id", "comune", "foglio", "particella", "visura_piani"} <= set(df.columns)
    assert len(df) == 6


def test_edifici_senza_patrimonio(sintetici):
    ed = A.edifici_da_unita(unita(sintetici))
    assert len(ed) == 7     # 5 particelle di fabbricati + 2 terreni
    forli = [e for e in ed if e["particella"] == "300"][0]
    assert forli["codice_comune"] == "D704" and forli["visura_unita"] == 3


def test_riga_di_comando(sintetici, tmp_path):
    from visure.__main__ import principale
    assert principale(["leggi", str(sintetici), "--uscita", str(tmp_path / "u"), "--includi-intestatari"]) == 0
    assert (tmp_path / "u" / "edifici_visure.csv").exists()
    pers = (tmp_path / "u" / "intestatari_DATI_PERSONALI.csv").read_text(encoding="utf-8")
    assert "SMPPRS80A01H199Z" in pers
    assert "SMPPRS80A01H199Z" not in (tmp_path / "u" / "indice.csv").read_text(encoding="utf-8")
    assert principale(["controlla", str(sintetici / "visura_immobile_A2_attuale.pdf")]) == 1
    assert principale(["controlla", str(sintetici / "documento_non_visura.pdf")]) == 0
    assert principale(["prova"]) == 0


@pytest.mark.skipif(not shutil.which("node"), reason="node non disponibile")
def test_parita_con_javascript(sintetici, tmp_path):
    """visure_abbina.js (sito) e arricchisci.py danno le stesse colonne sugli stessi dati."""
    uu = unita(sintetici)
    patr = leggi_csv(sintetici / "patrimonio_esempio_visure.csv") + [
        {"id": "G1", "belfiore": "H199", "foglio_catasto": "120", "mappale": "1450", "comune_catasto": "RAVENNA"},
        {"id": "G2", "comune": "D704", "foglio": "050", "particella": "300", "sezione": ""},
        {"id": "G3", "comune": "Rimini", "foglio": "77", "particella": "210"}]
    py, _ = A.abbina(patr, uu)
    ed_py = A.edifici_da_unita(uu)
    dati = tmp_path / "dati.json"
    dati.write_text(json.dumps({"unita": uu, "patrimonio": patr}, ensure_ascii=False), encoding="utf-8")
    script = (f"const V=require({json.dumps(str(SITO / 'visure_abbina.js'))});"
              f"const d=JSON.parse(require('fs').readFileSync({json.dumps(str(dati))},'utf8'));"
              "const a=V.abbina(d.patrimonio,d.unita);"
              "process.stdout.write(JSON.stringify({edifici:a.edifici,sciolte:a.nonAbbinate.length,da_unita:V.edificiDaUnita(d.unita)}));")
    js = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, encoding="utf-8", check=True).stdout)
    assert len(js["edifici"]) == len(py)
    for a, b in zip(py, js["edifici"]):
        for c in A.COLONNE_EDIFICIO:
            assert (a.get(c) if a.get(c) is not None else "") == (b.get(c) if b.get(c) is not None else ""), (a["id"], c, a.get(c), b.get(c))
    assert js["sciolte"] == 2
    for a, b in zip(ed_py, js["da_unita"]):
        for c in ["comune", "codice_comune", "foglio", "particella"] + A.COLONNE_EDIFICIO:
            assert (a.get(c) if a.get(c) is not None else "") == (b.get(c) if b.get(c) is not None else ""), (c, a.get(c), b.get(c))


@pytest.mark.skipif(not shutil.which("node"), reason="node non disponibile")
def test_js_scarta_colonne_personali(sintetici, tmp_path):
    from visure.__main__ import principale
    principale(["leggi", str(sintetici), "--uscita", str(tmp_path / "u")])
    indice = (tmp_path / "u" / "indice.csv").read_text(encoding="utf-8-sig")
    # un file modificato a mano con una colonna di intestatari: la pagina la scarta
    righe = indice.splitlines()
    righe[0] += ";intestatari;codice_fiscale"
    righe[1:] = [r + ";ESEMPIO PERSONA;SMPPRS80A01H199Z" for r in righe[1:]]
    f = tmp_path / "con_personali.csv"
    f.write_text("\n".join(righe), encoding="utf-8")
    script = (f"const V=require({json.dumps(str(SITO / 'visure_abbina.js'))});"
              "const righe=(t,s)=>t.split(/\\r?\\n/).filter(Boolean).map(r=>r.split(s));"
              f"const r=V.leggi(require('fs').readFileSync({json.dumps(str(f))},'utf8'),'x.csv',righe);"
              "process.stdout.write(JSON.stringify(r));")
    r = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, encoding="utf-8", check=True).stdout)
    assert r["tipo"] == "unita" and len(r["unita"]) == 9
    assert set(r["scartate"]) == {"intestatari", "codice_fiscale"}
    assert "SMPPRS80A01H199Z" not in json.dumps(r["unita"])
