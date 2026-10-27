"""Test dell'indirizzario ANNCSU (nessuna chiamata di rete: lo ZIP è costruito nel test)."""
import zipfile
from pathlib import Path

import pandas as pd

from territorio import anncsu, patrimonio
from territorio.anncsu import Indirizzario, normalizza, scomponi_civico, scomponi_via, separa_civico

from test_patrimonio import COMUNI, Finto

# stesse colonne e stesse particolarità del file reale: `;`, virgola decimale, virgolette dentro
# l'odonimo, civici senza coordinate o con 0,0, odonimi per esteso
INTESTAZIONE = ("CODICE_COMUNE;CODICE_ISTAT;PROGRESSIVO_NAZIONALE;CODICE_COMUNALE;ODONIMO;LOCALITA';"
                "DIZIONE_LINGUA1;DIZIONE_LINGUA2;PROGRESSIVO_ACCESSO;CODICE_COMUNALE_ACCESSO;CIVICO;ESPONENTE;"
                "SPECIFICITA;METRICO;PROGRESSIVO_SNC;COORD_X_COMUNE;COORD_Y_COMUNE;QUOTA;METODO")
RIGHE = [
    ("A944", "037006", "VIA LUIGI ZAMBONI", "31", "", "11,352000", "44,496800", "4"),
    ("A944", "037006", "VIA LUIGI ZAMBONI", "33", "", "11,352300", "44,496892", "4"),
    ("A944", "037006", "VIA LUIGI ZAMBONI", "33", "A", "11,352350", "44,496900", "4"),
    ("A944", "037006", "VIA LUIGI ZAMBONI", "35", "", "11,352600", "44,496950", "4"),
    ("A944", "037006", "VIA LUIGI ZAMBONI", "38", "", "11,352700", "44,497100", "4"),
    ("A944", "037006", "MURA ANTEO ZAMBONI", "33", "", "11,356000", "44,497400", "4"),
    ("A944", "037006", "VIA DELL'INDIPENDENZA", "10", "", "11,343000", "44,498000", "3"),
    ("A944", "037006", "VIA DELL'INDIPENDENZA", "12", "", "", "", ""),             # senza coordinate
    ("A944", "037006", 'VIA SILVIO MARCUZZI "MONTES"', "1", "", "0", "0", "5"),     # 0,0: scartato
    ("A944", "037006", "VIA SANTO STEFANO", "1", "", "11,348000", "44,492000", "4"),
    ("A944", "037006", "PIAZZA DI PORTA SANTO STEFANO", "2", "", "11,356300", "44,485100", "4"),
    ("H199", "039014", "PIAZZA DEL POPOLO", "1", "", "12,199000", "44,417000", "1"),
]


def _zip(tmp: Path) -> Path:
    righe = [INTESTAZIONE] + [
        f"{b};{i};1;1;{o};;;;1;1;{c};{e};;;;{x};{y};;{m}" for b, i, o, c, e, x, y, m in RIGHE]
    z = tmp / "INDIR_ITA.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("INDIR_ITA_20261001.csv", "\n".join(righe) + "\n")
    return z


def test_testi():
    assert normalizza("Via dell'Indipendenza, ") == "VIA DELL INDIPENDENZA"
    assert scomponi_via("V.le Carducci").dug == "VIALE"
    assert scomponi_via("P.zza S. Stefano").parole == ("STEFANO",)
    assert scomponi_via("Via dell'Indipendenza").parole == ("INDIPENDENZA",)
    assert scomponi_via("Via F.lli Bandiera").parole == ("FRATELLI", "BANDIERA")
    # numeri romani, in lettere e in cifre; anni dopo il mese; "Umberto I" = "Umberto Primo"
    assert scomponi_via("Via XXIV Maggio").parole == scomponi_via("VIA VENTIQUATTRO MAGGIO").parole == ("24", "MAGGIO")
    assert scomponi_via("Via XXI Aprile").parole == scomponi_via("VIA VENTUNO APRILE").parole
    assert scomponi_via("Via XXIII Settembre").parole == scomponi_via("VIALE 23 SETTEMBRE 1845").parole
    assert scomponi_via("Via Umberto I").parole == scomponi_via("VIALE UMBERTO PRIMO").parole == ("UMBERTO", "1")
    assert scomponi_via("Via I Maggio").parole == ("1", "MAGGIO")
    assert scomponi_via("Via V. Veneto").parole == ("VENETO",) and scomponi_via("Via V. Veneto").iniziali == ("V",)
    # abbreviazioni e vie di frazione
    assert scomponi_via("Via Circonvall.ne Occ.le").parole == ("CIRCONVALLAZIONE", "OCCIDENTALE")
    assert scomponi_via("Via Prov.le Bagnara").parole == ("PROVINCIALE", "BAGNARA")
    assert scomponi_via("LOCALITA' ALFERO VIA GIACOMO LEOPARDI").parole == ("GIACOMO", "LEOPARDI")
    assert scomponi_via("Via Sant’Agà").parole == scomponi_via("VIA SANT' AGA'").parole
    assert scomponi_civico("33") == (33, "") and scomponi_civico("33/a") == (33, "A")
    assert scomponi_civico("12 bis") == (12, "BIS") and scomponi_civico("snc") == (None, "")
    assert separa_civico("Via Zamboni, 33/A") == ("Via Zamboni", "33/A")
    assert separa_civico("Via Zamboni n. 33") == ("Via Zamboni", "33")
    assert separa_civico("Piazza Maggiore") == ("Piazza Maggiore", "")
    assert separa_civico("Via XX Settembre") == ("Via XX Settembre", "")


def test_scarica_e_cerca(tmp_path):
    f = anncsu.scarica(tmp_path, zip_locale=_zip(tmp_path))
    df = pd.read_parquet(f)
    assert len(df) == 10                                 # tolte la riga senza coordinate e quella a 0,0
    assert "data=20261001" in (tmp_path / "anncsu_civici.info").read_text()
    idx = Indirizzario(f)
    r = idx.cerca("037006", "A944", "Via Zamboni", "33")
    assert r.odonimo == "VIA LUIGI ZAMBONI" and r.esatto and r.nota == "" and r.civico == "33"
    assert abs(r.lat - 44.496892) < 1e-6
    assert idx.cerca("037006", "A944", "Via Zamboni", "33/A").civico == "33/A"
    # civico mancante: il più vicino sullo stesso lato (dispari), non il 38
    # il civico accanto (±2) è un'informazione, uno lontano è un dubbio
    r = idx.cerca("037006", "A944", "Via Zamboni", "37")
    assert r.civico == "35" and not r.esatto and r.nota.startswith("usato il civico vicino 35")
    assert r.nota.startswith(anncsu.INFORMATIVE)
    r = idx.cerca("037006", "A944", "Via Zamboni", "45")
    assert r.civico == "35" and "45 non georeferenziato" in r.nota and not r.nota.startswith(anncsu.INFORMATIVE)
    # forma breve e articoli
    assert idx.cerca("037006", "A944", "Via Indipendenza", "10").odonimo == "VIA DELL'INDIPENDENZA"
    # errore di battitura: trovata ma segnalata
    # errore di battitura confermato dal civico esistente: informazione; senza conferma: dubbio
    r = idx.cerca("037006", "A944", "Via Zamboi", "33")
    assert r.odonimo == "VIA LUIGI ZAMBONI" and r.nota.startswith("via riconosciuta come VIA LUIGI ZAMBONI")
    assert "interpretata" in idx.cerca("037006", "A944", "Via Zamboi", "37").nota
    # la DUG distingue Via Zamboni da Mura Anteo Zamboni
    assert idx.cerca("037006", "A944", "Mura Zamboni", "33").odonimo == "MURA ANTEO ZAMBONI"
    assert idx.cerca("037006", "A944", "Via Garibaldi", "1") is None
    # nome più lungo scelto per la DUG, ma esiste una via con lo stesso nome esatto: segnalato
    r = idx.cerca("037006", "A944", "P.zza Santo Stefano", "2")
    assert r.odonimo == "PIAZZA DI PORTA SANTO STEFANO" and "esiste anche VIA SANTO STEFANO" in r.nota
    assert idx.cerca("039014", "H199", "P.zza del Popolo", "1").odonimo == "PIAZZA DEL POPOLO"
    # edificio d'angolo: si prova una via alla volta
    r = idx.cerca("037006", "A944", "Via Garibaldi e Via Indipendenza", "10")
    assert r.odonimo == "VIA DELL'INDIPENDENZA" and "angolo" in r.nota
    # perché una via non si trova: assente, oppure presente ma senza civici georeferenziati
    assert idx.motivo("037006", "Via Garibaldi") == "via non presente in ANNCSU"
    assert "non ne ha ancora georeferenziato nessuno" in idx.motivo("037006", "Via Marcuzzi")
    vie = pd.read_parquet(tmp_path / "anncsu_vie.parquet").set_index("odonimo")
    assert vie.loc["VIA DELL'INDIPENDENZA", "civici"] == 2 and vie.loc["VIA DELL'INDIPENDENZA", "georeferenziati"] == 1


def test_nomi_come_negli_elenchi_degli_enti():
    righe = [("037006", "A944", o, c, "", 44.49 + i / 1000, 11.34, 4) for i, (o, c) in enumerate([
        ("VIALE PIEMONTE", 20), ("PIAZZA MAZZINI", 20), ("VIALE GIUSEPPE MAZZINI", 20), ("VIA ETTORE BENINI", 27),
        ("VIA CORRADO BENINI", 27), ("VIA TONO ZANCANARO", 167), ("VIA PUBLIO OVIDIO NASONE", 99),
        ("VIALE 23 SETTEMBRE 1845", 120), ("VIA CONSOLARE RIMINI-SAN MARINO", 76), ("MURA ANTEO ZAMBONI", 1)])]
    idx = Indirizzario(pd.DataFrame(righe, columns=["istat", "belfiore", "odonimo", "civico", "esponente", "lat",
                                                    "lon", "metodo"]))
    r = idx.cerca("037006", "A944", "Via Piemonte", "20")      # Via per Viale: stessa famiglia, nessun dubbio
    assert r.odonimo == "VIALE PIEMONTE" and r.nota == ""
    assert idx.cerca("037006", "A944", "Via Mazzini", "20").odonimo == "VIALE GIUSEPPE MAZZINI"
    r = idx.cerca("037006", "A944", "Via E. Benini", "27")     # l'iniziale sceglie ETTORE
    assert r.odonimo == "VIA ETTORE BENINI" and "più vie" not in r.nota
    assert idx.cerca("037006", "A944", "Via Zancanaro Tono", "167").odonimo == "VIA TONO ZANCANARO"
    r = idx.cerca("037006", "A944", "Via Ovidio", "99")
    assert r.odonimo == "VIA PUBLIO OVIDIO NASONE" and "riconosciuta" in r.nota   # il 99 la conferma
    assert idx.cerca("037006", "A944", "Via XXIII Settembre", "120").nota == ""
    assert idx.cerca("037006", "A944", "S.S. Consolare per San Marino", "76").odonimo == "VIA CONSOLARE RIMINI-SAN MARINO"
    assert idx.cerca("037006", "A944", "Via Zamboni", "1").nota != ""   # Via contro Mura: tipo diverso, segnalato


def test_scarica_regione(tmp_path):
    f = anncsu.scarica(tmp_path, zip_locale=_zip(tmp_path), istat={"039014"})
    assert set(pd.read_parquet(f).istat) == {"039014"}


class FintoStrada(Finto):
    """Il punto esatto dell'accesso cade sulla strada; 8 m più a nord c'è l'edificio."""

    def particella_in_punto(self, lat, lon):
        if abs(lat - 44.496892) < 1e-7:
            return {"fid": 1, "label": "STRADA1", "kind": "strada", "cadastral_reference": "A944_019000.STRADA1",
                    "municipality": {"code": "A944", "name": "Bologna"}, "centroid": {"lat": lat, "lng": lon}}
        return super().particella_in_punto(lat, lon)


def test_patrimonio_con_anncsu(tmp_path):
    idx = Indirizzario(anncsu.scarica(tmp_path, zip_locale=_zip(tmp_path)))
    df = patrimonio.leggi(Path(__file__).parent.parent / "esempi" / "patrimonio_esempio.csv").head(1)
    z = Finto(civico_noto=False)
    r = patrimonio.geolocalizza(df, z, COMUNI, anncsu=idx).iloc[0]
    assert z.query == []                                  # Zornade geocodifica non serve
    assert r.fonte_punto == "ANNCSU" and r.indirizzo_trovato == "VIA LUIGI ZAMBONI 33"
    assert r.esito == "ok" and r.foglio_catasto == "190" and r.istat == "037006"
    g = patrimonio.geojson(patrimonio.geolocalizza(df, z, COMUNI, anncsu=idx))
    assert any("ANNCSU" in s for s in g["sources"])
    # accesso sulla strada → particella edificata vicina, esito comunque ok
    r = patrimonio.geolocalizza(df, FintoStrada(), COMUNI, anncsu=idx).iloc[0]
    assert r.tipo_particella == "immobile" and r.esito == "ok" and "~8 m" in r.nota


def test_anncsu_assente_ripiega_su_zornade(tmp_path):
    idx = Indirizzario(anncsu.scarica(tmp_path, zip_locale=_zip(tmp_path)))
    df = pd.DataFrame([{"id": "X", "indirizzo": "Via Garibaldi 5", "comune": "Bologna"}])
    z = Finto()
    r = patrimonio.geolocalizza(df, z, COMUNI, anncsu=idx).iloc[0]
    assert z.query == ["Via Garibaldi 5 Bologna"] and r.fonte_punto == "Zornade" and r.esito == "ok"
