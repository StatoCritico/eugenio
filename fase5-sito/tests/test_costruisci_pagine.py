"""Prove di costruisci_pagine.py su una copia del sito."""
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

QUI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(QUI))
import costruisci_pagine as C  # noqa: E402

VOCI = {"index.html": "./", "patrimonio.html": "patrimonio.html", "legge10.html": "legge10.html",
        "dati.html": "dati.html", "indicatori.html": "indicatori.html", "metodo.html": "metodo.html",
        "faq.html": "faq.html", "sitografia.html": "sitografia.html", "mirror.html": "mirror.html",
        "contatti.html": "contatti.html", "licenza.html": None, "privacy.html": None}


@pytest.fixture()
def sito(tmp_path):
    d = tmp_path / "sito"
    d.mkdir()
    for f in (QUI / "sito").glob("*.html"):
        shutil.copy(f, d)
    for f in (QUI / "sito").glob("*.js"):
        shutil.copy(f, d)
    return d


def test_idempotente(sito):
    assert C.main(["--sito", str(sito)]) == 0
    prima = {f.name: f.read_text(encoding="utf-8") for f in sito.iterdir()}
    assert C.main(["--sito", str(sito), "--controlla"]) == 0
    assert C.main(["--sito", str(sito)]) == 0
    assert prima == {f.name: f.read_text(encoding="utf-8") for f in sito.iterdir()}


def test_voce_attiva_e_marcatori(sito):
    C.main(["--sito", str(sito)])
    for nome, href in VOCI.items():
        s = (sito / nome).read_text(encoding="utf-8")
        for parte in ("testa", "testata", "piede"):
            assert s.count(f"<!-- {parte} -->") == 1 and s.count(f"<!-- /{parte} -->") == 1, (nome, parte)
        attivi = re.findall(r'<a [^>]*aria-current="page"[^>]*>', s)
        if href is None:
            assert not attivi, nome
        else:
            assert len(attivi) == 2 and all(f'href="{href}"' in a for a in attivi), (nome, attivi)
            assert not any('class="marchio"' in a for a in attivi)


def test_versione(sito):
    C.main(["--sito", str(sito), "--versione", "20991231z"])
    for f in sito.iterdir():
        t = f.read_text(encoding="utf-8")
        assert not re.search(r"\?v=(?!20991231z)\d{8}", t), f.name
    assert 'const V = "20991231z"' in (sito / "cti_legge10.js").read_text(encoding="utf-8")
    assert C.main(["--sito", str(sito), "--versione", "20991231z", "--controlla"]) == 0


def test_modifica_del_modello_arriva_in_tutte_le_pagine(sito, monkeypatch, tmp_path):
    parti = tmp_path / "parti"
    shutil.copytree(C.PARTI, parti)
    p = parti / "piede.html"
    p.write_text(p.read_text(encoding="utf-8").replace("Contattaci", "Scrivici"), encoding="utf-8")
    monkeypatch.setattr(C, "PARTI", parti)
    C.main(["--sito", str(sito)])
    for nome in VOCI:
        assert "Scrivici</a>" in (sito / nome).read_text(encoding="utf-8")


# ---------------------------------------------------------------- menu a gruppi e pagine segnaposto (03/11/2026)
GRUPPI = {"clima": ["dati.html", "legge10.html", "./", "edificio-clima.html"],   # (08/11/2026) Cambiamento climatico, ultima
          "patrimonio": ["patrimonio.html", "ortofoto.html", "lidar.html", "modelli3d.html", "importa-dxf-ifc.html", "aggiungi-dbtr.html",
                         "dbtr-istruzioni.html", "visure.html"],
          "statistiche": ["indicatori.html"]}
VIETATI = ("PUN Index GME =", "€/MWh", "Prezzo medio")   # nessun valore nelle pagine in attesa della licenza GME


def test_menu_sei_gruppi_e_voci_raggiungibili(sito):
    C.main(["--sito", str(sito)])
    t = (C.PARTI / "testata.html").read_text(encoding="utf-8")
    titoli = re.findall(r'<details class="voce-gruppo"[^>]*><summary>([^<]+)</summary>', t)
    # dal 05/11/2026 (seconda pubblicazione) il sesto gruppo Statistiche, con «Costi energetici Sanità» (indicatori.html)
    # (08/11/2026) «Edificio» → «Edifici» (data-gruppo resta «edificio»: la scelta fissata nei browser non si perde)
    assert titoli == ["Clima e meteo", "Patrimonio", "Edifici", "Cogenerazione", "Fotovoltaico", "Statistiche"]
    for gruppo, voci in GRUPPI.items():
        blocco = re.search(rf'data-gruppo="{gruppo}"><summary>.*?</details>', t, re.S).group(0)
        assert re.findall(r'href="([^"]+)"', blocco) == voci
    # ogni voce del menu porta a una pagina che esiste; le vecchie voci restano raggiungibili
    for href in set(re.findall(r'href="([^"#:]+\.html|\./)"', t)):
        assert (sito / ("index.html" if href == "./" else href)).exists(), href
    for vecchia in ("indicatori.html", "metodo.html", "faq.html", "sitografia.html", "mirror.html", "contatti.html"):
        assert f'href="{vecchia}"' in t


def test_gruppo_attivo(sito):
    C.main(["--sito", str(sito)])
    s = (sito / "lidar.html").read_text(encoding="utf-8")
    assert re.search(r'<details class="voce-gruppo" data-gruppo="patrimonio" data-attivo>', s)
    assert re.search(r'<details class="pannello-gruppo" data-gruppo="patrimonio" data-attivo open>', s)
    assert s.count("data-attivo") == 2
    s = (sito / "indicatori.html").read_text(encoding="utf-8")
    # dal 05/11/2026 «Costi energetici Sanità» è nel gruppo Statistiche (non più «Indicatori» tra le altre pagine)
    assert re.search(r'<details class="voce-gruppo" data-gruppo="statistiche" data-attivo>', s) and s.count("data-attivo") == 2
    altre = re.search(r'<nav class="menu-info"[^>]*>.*?</nav>', s, re.S).group(0)
    assert "indicatori.html" not in altre and ">Indicatori<" not in s
    assert "<h1>Costi energetici Sanità</h1>" in s and "Costi energetici Sanità</title>" in s
    assert "Servizio sperimentale non ancora verificato" not in s     # validata: niente avviso né «S» nel menu
    # dal 07/11/2026 sera anche Dati climatici e Legge 10 sono validate: niente avviso né «S» nel menu; dal 09/11/2026
    # anche Previsioni (index.html)
    for nome in ("dati.html", "legge10.html", "index.html"):
        s = (sito / nome).read_text(encoding="utf-8")
        assert "Servizio sperimentale non ancora verificato" not in s, nome
        assert not re.search(r'href="%s">[^<]*<span class="cantiere' % re.escape(nome), s), nome


def test_segnaposto_senza_dati_gme(sito):
    C.main(["--sito", str(sito)])
    pagine = [f for f in sito.glob("*.html") if 'class="articolo segnaposto"' in f.read_text(encoding="utf-8")]
    # 20 al 03/11/2026; dal 04/11/2026 (Fase B) Ortofoto, Irradiazione, PVGIS, D.Lgs. 199 e Obblighi sono strumenti; dal
    # 05/11/2026 anche Emissioni (blocco 3) e le pagine delle analisi senza UNI
    assert len(pagine) >= 8
    for f in pagine:
        s = f.read_text(encoding="utf-8")
        assert 'class="stato-pagina"' in s and 'id="fonti"' in s, f.name
        if "In attesa della licenza GME" in s:
            assert not any(v in s for v in VIETATI), f.name


# ---------------------------------------------------------------- edifici 3D (fase 10, Fase A, 04/11/2026)
PAGINE_3D = ["modelli3d.html", "edificio-geometria.html", "edificio-consumi.html", "fv-ombre.html", "fv-producibilita.html",
             "fv-irradiazione.html", "fv-pvgis.html", "fv-dlgs199.html", "edificio-obblighi.html"]   # ultime 4: Fase B


def test_pagine_3d_librerie_locali():
    for nome in PAGINE_3D:
        s = (QUI / "sito" / nome).read_text(encoding="utf-8")
        assert 'class="strumento pagina-edificio3d"' in s and 'id="mappa3d"' in s, nome
        assert 'src="lib/maplibre-gl/maplibre-gl.js' in s and 'src="lib/pmtiles/pmtiles.js' in s, nome
        assert not re.search(r'(src|href)="https?://(cdn|unpkg|cdnjs)', s), nome          # niente CDN
        assert "segnaposto" not in re.search(r"<main[^>]*>", s).group(0), nome
        assert "ODbL" in s and "CC BY 4.0" in s, nome                                      # licenze delle sagome
    for lib, lic in (("maplibre-gl", "LICENSE.txt"), ("pmtiles", "LICENSE")):
        assert (QUI / "sito" / "lib" / lib / lic).exists(), lib
    # demo sintetica dichiarata come tale
    import json
    ind = json.loads((QUI / "sito" / "dati" / "edifici3d" / "indice.json").read_text(encoding="utf-8"))
    assert ind["sintetico"] is True and "sintetici" in ind["avviso"]


def test_calcoli_js_con_node():
    import shutil, subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node non installato")
    prova = r'''
const E = require(process.argv[1]);
const sq = (x0, y0, w, h) => [[x0, y0], [x0 + w, y0], [x0 + w, y0 + h], [x0, y0 + h], [x0, y0]];
const i = E.indicatori([{ id: "b", edificio: "E", ring: sq(0, 0, 10, 10), gronda: 6 }, { id: "t", edificio: "E", ring: sq(10, 0, 10, 10), gronda: 15 }]);
const s = E.sole(new Date(Date.UTC(2026, 5, 21, 11, 0)), 44.06, 12.57);
const f = E.firma([{ consumo: 300, gg: 0 }, { consumo: 1200, gg: 100 }, { consumo: 2100, gg: 200 }]);
console.log(JSON.stringify({ comune: i.pareti_in_comune_tra_corpi, o: i.pareti_per_orientamento.O, alt: s.altezza, base: f.base,
  pend: f.pendenza, div: E.dividi(sq(0, 0, 10, 10), [5, -1], [5, 11]).map(E.area), fac: E.mappaFacoltative(["id", "Piani", "SLP (m²)", "gas"]) }));
'''
    out = subprocess.run([node, "-e", prova, str(QUI / "sito" / "edifici_calcoli.js")], capture_output=True, text=True, encoding="utf-8", check=True).stdout
    import json
    d = json.loads(out)
    assert d["comune"] == pytest.approx(60) and d["o"] == pytest.approx(150)
    assert 68 < d["alt"] < 70                         # sole al solstizio d'estate a mezzogiorno a Rimini
    assert d["base"] == pytest.approx(300) and d["pend"] == pytest.approx(9)
    assert d["div"] == [50, 50]
    assert d["fac"] == {"1": "piani_fuori_terra", "2": "superficie_lorda"}


# ---------------------------------------------------------------- Fase B (04/11/2026)
def test_pagine_fase_b():
    for nome in PAGINE_3D:
        s = (QUI / "sito" / nome).read_text(encoding="utf-8")
        for id_ in ("passo-obblighi", "passo-facciate", "passo-pvgis", "passo-priorita", "sfondo-ortofoto", "attribuzione-ortofoto"):
            assert f'id="{id_}"' in s, (nome, id_)
        assert "Allegato III" in s and "PVGIS" in s and "Copernicus" in s, nome
    o = (QUI / "sito" / "ortofoto.html").read_text(encoding="utf-8")
    assert 'id="mappa-ortofoto"' in o and 'id="attribuzione"' in o and "segnaposto" not in re.search(r"<main[^>]*>", o).group(0)
    assert 'src="ortofoto.js' in o and 'src="lib/maplibre-gl/maplibre-gl.js' in o
    assert not re.search(r'(src|href)="https?://(cdn|unpkg|cdnjs)', o)
    js = (QUI / "sito" / "ortofoto.js").read_text(encoding="utf-8")
    for vietato in ("google.com", "googleapis", "arcgisonline", "virtualearth", "s2cloudless-20"):   # nessun indirizzo dei servizi esclusi
        assert vietato not in o.lower() and vietato not in js.lower()
    t = (QUI / "parti" / "testata.html").read_text(encoding="utf-8")
    assert re.search(r'href="ortofoto.html">[^<]*<span class="cantiere prova">sperimentale', t)
    for href in ("fv-irradiazione.html", "fv-pvgis.html", "fv-dlgs199.html", "edificio-obblighi.html"):     # (08/11/2026) in lavorazione
        assert f'href="{href}"' not in t and f'data-pagina="{href}"' in t, href


def test_calcoli_fase_b_con_node():
    import json
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node non installato")
    prova = r'''
const E = require(process.argv[1]);
const sq = (x0, y0, w, h) => [[x0, y0], [x0 + w, y0], [x0 + w, y0 + h], [x0, y0 + h], [x0, y0]];
const corpi = [{ id: "b", edificio: "E", ring: sq(0, 0, 10, 10), gronda: 6 }, { id: "t", edificio: "E", ring: sq(10, 0, 10, 10), gronda: 15 }];
const parti = E.partiFacciate(corpi, []);
const esposta = parti.reduce((s, p) => s + p.area, 0);
const cl = E.climaSintetico(2025, 44.06, 12.57);
const uno = [{ id: "a", edificio: "E", ring: sq(0, 0, 10, 10), gronda: 9 }], vic = [{ id: "v", edificio: "V", ring: sq(0, -22, 10, 10), gronda: 20 }];
const sud = (v) => { const p = E.partiFacciate(uno, v), ost = [...uno, ...v].map((c) => ({ ring: c.ring, cima: c.gronda }));
  const oz = p.map((x) => E.orizzonte(x.centro, ost, 72, 250)); return E.riepilogoFacciate(p, E.irraggiamentoFacciate(cl, 44.06, 12.57, p, oz)).S; };
const libero = sud([]), ombreggiato = sud(vic);
const unito = Array.from(E.uniscio(new Float32Array(72).fill(1), Array.from({ length: 36 }, (_, k) => (k === 9 ? 10 : 0))));
console.log(JSON.stringify({ esposta, comune: E.indicatori(corpi).pareti_esposte, libero: libero.kwh_m2, ombra: ombreggiato.kwh_m2,
  perdita: ombreggiato.perdita, unito18: unito[18], unito0: unito[0],
  p1: E.obbligoFer(400, { intervento: "primo" }), p2: E.obbligoFer(400, { intervento: "nuovo", pubblico: true }),
  ht: E.htMassimo("E", 0.55), ht2: E.htMassimo("A", 0.8), htx: E.htMassimo("Z", 0.5),
  cl: E.priorita([{ id: 1, kwh_m2: 200, costo_m2: 30 }, { id: 2, kwh_m2: 100, costo_m2: 10 }, { id: 3, kwh_m2: 150 }]).map((x) => [x.id, x.posto]) }));
'''
    d = json.loads(subprocess.run([node, "-e", prova, str(QUI / "sito" / "edifici_calcoli.js")], capture_output=True, text=True, encoding="utf-8",
                                  check=True).stdout)
    assert d["esposta"] == pytest.approx(d["comune"])            # stesse pareti esposte degli indicatori (§ 7)
    assert d["ombra"] < d["libero"] and d["perdita"] > 5          # l'edificio alto a sud fa ombra sulla facciata sud
    assert d["unito18"] == pytest.approx(10) and d["unito0"] == pytest.approx(1)
    # D.Lgs. 199/2021, Allegato III, sez. B, punti 3 e 5
    assert d["p1"]["kw"] == pytest.approx(10) and d["p1"]["k"] == 0.025 and d["p1"]["quota_totale"] == 40
    assert d["p2"]["kw"] == pytest.approx(22) and d["p2"]["quota_acs"] == 65 and d["p2"]["quota_totale"] == 65
    # DM 26/6/2015 come modificato dal DM 28/10/2025, Tabella 10
    assert d["ht"] == {"valore": 0.55, "fascia": "0,4 ≤ S/V < 0,7"} and d["ht2"]["valore"] == 0.58 and d["htx"] is None
    assert d["cl"] == [[1, 1], [3, 2], [2, 3]]


# ---------------------------------------------------------------- Fase C (04/11/2026)
def test_pagine_fase_c():
    import json
    for nome in PAGINE_3D:
        s = (QUI / "sito" / nome).read_text(encoding="utf-8")
        for id_ in ("falde-tetti", "tabella-falde", "messaggio-falde", "modello-file"):
            assert f'id="{id_}"' in s, (nome, id_)
        assert "interno/" not in s
    js = (QUI / "sito" / "edificio3d.js").read_text(encoding="utf-8")
    assert "lidar/indice.json" in js and "lidar/falde/" in js and "eugenio-modello-1" in js
    assert "fetch(\"/api/edifici/importa" not in js            # il modello dell'utente non va al server
    ind = json.loads((QUI / "sito" / "dati" / "edifici3d" / "lidar" / "indice.json").read_text(encoding="utf-8"))
    assert ind["sintetico"] is True and "inventate" in ind["avviso"]
    # pagina interna fuori dal menu e dalla costruzione delle pagine
    t = (QUI / "parti" / "testata.html").read_text(encoding="utf-8")
    assert "interno" not in t
    p = (QUI / "sito" / "interno" / "edifici.html").read_text(encoding="utf-8")
    assert 'content="noindex, nofollow"' in p and "/api/interno/edifici/stato" in (QUI / "sito" / "interno" / "edifici.js").read_text()


# dal 05/11/2026 le analisi 7, 9 e 13 (senza norme UNI) sono nel codice pubblico: le loro pagine non chiedono più lo stato
ANALISI_PAGINE = {"edificio-fabbisogno.html": {"5"}, "edificio-involucro.html": {"8", "12"}, "edificio-impianti.html": {"10", "11"}}


def test_pagine_fase_e_aggancio_analisi():
    """Analisi 5 e 7–13: ogni pagina parte da «non disponibile in questa installazione» (anche senza JavaScript) e
    chiede lo stato al server; nessun contenuto di norme UNI nelle pagine né nello script."""
    trovati = set()
    for nome, attese in ANALISI_PAGINE.items():
        s = (QUI / "sito" / nome).read_text(encoding="utf-8")
        ids = set(re.findall(r'data-analisi="(\d+)"', s))
        assert ids == attese, nome
        assert s.count("analisi non disponibile in questa installazione") >= len(attese)
        assert re.search(r'<script src="analisi_uni\.js\?v=\d{8}[a-z]?"></script>', s), nome
        trovati |= ids
    assert trovati == {"5", "8", "10", "11", "12"}
    js = (QUI / "sito" / "analisi_uni.js").read_text(encoding="utf-8")
    assert "/api/analisi/stato" in js and "analisi non disponibile in questa installazione" in js
    assert "uni_privato" not in js


# ---------------------------------------------------------------- Importa DXF/IFC (04/11/2026)
LIB_MODELLI = {"dxf-parser": ("dxf-parser.js", "LICENSE"), "web-ifc": ("web-ifc-api-iife.js", "LICENSE.md"),
               "clipper-lib": ("clipper.js", "LICENSE"), "proj4": ("proj4.js", "LICENSE.md")}


def test_pagina_importa_dxf_ifc_e_librerie_solo_li():
    sito = QUI / "sito"
    s = (sito / "importa-dxf-ifc.html").read_text(encoding="utf-8")
    t = (QUI / "parti" / "testata.html").read_text(encoding="utf-8")
    assert t.count('href="importa-dxf-ifc.html"') == 2                         # menu del computer e del telefono
    assert 'aria-current="page"' in s and 'id="file-modello"' in s and 'id="passo-pc"' in s
    assert "30 MB" in s and "EuGEnioVisure.exe" in s and "importa-modello" in s and "docker run" in s
    assert re.search(r'<script src="modelli_import\.js\?v=\d{8}[a-z]"></script>', s)
    assert "web-ifc-api" not in s and "dxf-parser.js" not in s                 # si caricano nel worker, web-ifc solo per gli IFC
    for lib, (js, lic) in LIB_MODELLI.items():
        assert (sito / "lib" / lib / js).is_file() and (sito / "lib" / lib / lic).is_file(), lib
    assert (sito / "lib" / "web-ifc" / "web-ifc.wasm").is_file()
    assert all(f"`{x}`" in (sito / "lib" / "README.md").read_text(encoding="utf-8") for x in LIB_MODELLI)
    # nessun'altra pagina scarica i lettori dei modelli
    for f in sito.glob("*.html"):
        if f.name == "importa-dxf-ifc.html":
            continue
        h = f.read_text(encoding="utf-8")
        assert not any(x in h for x in ("modelli_worker", "modelli_import", "importa_modello.js", "lib/web-ifc", "lib/dxf-parser",
                                        "lib/clipper-lib", "lib/proj4")), f.name
    w = (sito / "modelli_worker.js").read_text(encoding="utf-8")
    assert "fetch(" not in w and "XMLHttpRequest" not in w                      # il worker non parla con il server
    p = (sito / "importa_modello.js").read_text(encoding="utf-8")
    # solo /api/ortofoto/fonti e, dal 05/11/2026, i file statici dell'archivio degli edifici (posa «sagoma»), sempre in GET
    assert "method: \"POST\"" not in p and "/api/" in p and p.count("fetch(") == 2 and "/edifici3d/cc-by/er/prodotti/" in p
    e = (sito / "edificio3d.js").read_text(encoding="utf-8")
    assert "modello=locale" in (sito / "importa_modello.js").read_text(encoding="utf-8") and '"modello") === "locale"' in e


# ---------------------------------------------------------------- menu fissato e voci GME non cliccabili (04/11/2026)
PAGINE_GME = ["cog-spark-spread.html", "cog-simulazione.html", "cog-confronto.html", "cog-rischio.html", "cog-car.html",
              "fv-mercato.html"]


def test_voci_gme_non_cliccabili_nel_menu(sito):
    t = (C.PARTI / "testata.html").read_text(encoding="utf-8")
    for p in PAGINE_GME:
        assert f'href="{p}"' not in t, p                                      # né nella tendina né nel menu del telefono
        voci = re.findall(rf'<span class="voce-gme" data-pagina="{re.escape(p)}"[^>]*>', t)
        assert len(voci) == 2, p
        assert all('aria-disabled="true"' in v and 'title="In attesa di autorizzazione dal GME"' in v for v in voci), p
        assert (sito / p).exists(), p                                         # la pagina resta, solo non è collegata
    assert "licenza GME</span></a>" not in t
    # sulla pagina GME il gruppo resta segnato e la voce ha aria-current
    C.main(["--sito", str(sito)])
    s = (sito / "cog-car.html").read_text(encoding="utf-8")
    assert re.search(r'<details class="voce-gruppo" data-gruppo="cogenerazione" data-attivo>', s)
    assert len(re.findall(r'<span class="voce-gme" data-pagina="cog-car.html"[^>]*aria-current="page"', s)) == 2


def test_nessun_collegamento_interno_alle_pagine_gme(sito):
    """Le pagine in attesa della licenza GME non sono raggiungibili da collegamenti del sito (resta solo il
    collegamento della pagina a sé stessa, con aria-current, nell'elenco «Nello stesso gruppo»)."""
    C.main(["--sito", str(sito)])
    for f in sorted(sito.glob("*.html")):
        s = f.read_text(encoding="utf-8")
        for m in re.finditer(r'<a [^>]*href="([^"#?]+)[^"]*"[^>]*>', s):
            if m.group(1) in PAGINE_GME:
                assert m.group(1) == f.name and 'aria-current="page"' in m.group(0), (f.name, m.group(0))


def test_riga_fissata_nella_testata_e_nel_head():
    t = (C.PARTI / "testata.html").read_text(encoding="utf-8")
    assert t.count('<nav class="riga-fissata" id="riga-fissata"') == 1
    assert t.index('class="testata-menu"') < t.index('class="riga-fissata"') < t.index("</header>")
    h = (C.PARTI / "testa.html").read_text(encoding="utf-8")
    assert 'localStorage.getItem("menu-fissato")' in h and "d.dataset.menuFissato" in h
    assert "clima|patrimonio|edificio|cogenerazione|fotovoltaico|statistiche" in h
    js = (QUI / "sito" / "aspetto.js").read_text(encoding="utf-8")
    for testo in ("Clicca qui per fissare il menu ${nome} sotto la barra",
                  "Clicca qui per richiudere la barra di ${nome} e tornare al menu a tendina", "aria-pressed", '"menu-fissato"'):
        assert testo in js, testo
    css = (QUI / "sito" / "stile.css").read_text(encoding="utf-8")
    assert "--nero-riga: #000" in css and ":root[data-menu-fissato] .riga-fissata" in css


# ---------------------------------------------------------------- blocco 2 del 05/11/2026 (affinamenti Edificio)
def _node(prova, *argomenti):
    import json
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node non installato")
    return json.loads(subprocess.run([node, "-e", prova, str(QUI / "sito" / "edifici_calcoli.js"), *argomenti],
                                     capture_output=True, text=True, encoding="utf-8", check=True).stdout)


def test_tabella_11_e_quota_vetrata():
    d = _node(r'''
const E = require(process.argv[1]);
console.log(JSON.stringify({ e30: E.htMassimoPrimoLivello("E", 30), c9: E.htMassimoPrimoLivello("C", 9), a5: E.htMassimoPrimoLivello("A", 5),
  f100: E.htMassimoPrimoLivello("F", 100), b52: E.htMassimoPrimoLivello("B", 52), x: E.htMassimoPrimoLivello("E", 120), z: E.htMassimoPrimoLivello("Z", 20),
  n: [E.HT_TAB11_QUOTE.length, ...Object.values(E.HT_TAB11).map((r) => r.length)],
  st: E.quotaVetrataStimata({ superficie_disperdente: 1000, pareti_esposte: 600 }, "uffici"), st0: E.quotaVetrataStimata(null) }));''')
    # DM 26/6/2015 come modificato dal DM 28/10/2025, All. 1, App. A, § 2.1, Tabella 11 (GU n. 283 del 5/12/2025)
    assert d["e30"]["valore"] == pytest.approx(0.58 + 0.4 * (0.62 - 0.58), abs=1e-3) and d["e30"]["interpolato"]
    assert d["e30"]["colonne"] == [[28, 0.58], [33, 0.62]]
    assert d["c9"] == {"valore": 0.6, "colonne": [[9, 0.6]], "interpolato": False, "nota": ""}
    assert d["a5"]["valore"] == 0.72 and "prima colonna" in d["a5"]["nota"]
    assert d["f100"]["valore"] == 0.96 and d["b52"]["valore"] == 1.47 and d["x"] is None and d["z"] is None
    assert d["n"] == [20] * 7
    assert d["st"]["quota"] == pytest.approx(18) and d["st0"] is None    # 30 % di 600 m² su 1000 m²


def test_colonne_visura_e_precedenza():
    d = _node(r'''
const E = require(process.argv[1]);
const v = E.daVisura({ visura_esito: "ok", visura_piani: "3", visura_superficie_catastale: "812,5", visura_uso: "uffici" });
const nessuna = E.daVisura({ visura_esito: "nessuna_visura", visura_piani: "3" });
const titoli = ["id", "Gas (Smc)", "visura_piani_fuori_terra", "visura_superficie_catastale", "visura_rendita_euro", "Superficie lorda"];
const m = E.mappaVisura(titoli), l = E.leggiVisura(m, ["S1", "100", "4", "900", "1234", ""]);
const sq = (x0, y0, w, h) => [[x0, y0], [x0 + w, y0], [x0 + w, y0 + h], [x0, y0 + h], [x0, y0]];
const s = E.superfici([{ id: "a", ring: sq(0, 0, 20, 10), gronda: 9 }], { superficie_lorda: 700 }, l);
console.log(JSON.stringify({ v, nessuna, m, l, piani: s.piani_fuori_terra, lorda: s.superficie_lorda, cat: s.superficie_catastale }));''')
    assert d["v"] == {"superficie_catastale": 812.5, "piani_fuori_terra": 3, "uso": "uffici"} and d["nessuna"] == {}
    assert d["m"] == {"2": "visura_piani_fuori_terra", "3": "visura_superficie_catastale", "4": "visura_rendita_euro"}
    assert d["l"] == {"piani_fuori_terra": 4, "superficie_catastale": 900}
    assert d["piani"] == {"valore": 4, "fonte": "visura"} and d["lorda"] == {"valore": 700, "fonte": "csv"}
    assert d["cat"] == {"valore": 900, "fonte": "visura"}


def test_perez_contro_pvgis():
    """Trasposizione di Perez (1990) contro PVGIS 5.3 (SARAH3, 2020, Rimini; giorno 15 di ogni mese): sul piano a 30° e
    sulla facciata sud la Perez sta entro il 3 % di PVGIS e più vicina dell'isotropa."""
    d = _node(r'''
const E = require(process.argv[1]); const P = JSON.parse(require("fs").readFileSync(process.argv[2]));
const r = { iso30: 0, per30: 0, pv30: 0, iso90: 0, per90: 0, pv90: 0 };
for (const [t, ghi, dhi, p30, p90] of P.righe) {
  const d = new Date(Date.UTC(+t.slice(0, 4), +t.slice(4, 6) - 1, +t.slice(6, 8), +t.slice(9, 11), +t.slice(11, 13))), s = E.sole(d, 44.06, 12.57);
  r.iso30 += E.trasponi(ghi, dhi, s, 30, 180, { modello: "isotropo" }).poa; r.per30 += E.trasponi(ghi, dhi, s, 30, 180).poa; r.pv30 += p30;
  r.iso90 += E.trasponi(ghi, dhi, s, 90, 180, { modello: "isotropo" }).poa; r.per90 += E.trasponi(ghi, dhi, s, 90, 180).poa; r.pv90 += p90;
}
console.log(JSON.stringify(r));''', str(QUI / "tests" / "pvgis_rimini_2020_giorno15.json"))
    for a in ("30", "90"):
        per, iso, pv = d["per" + a], d["iso" + a], d["pv" + a]
        assert abs(per / pv - 1) < 0.03, (a, per / pv)
        assert abs(per / pv - 1) < abs(iso / pv - 1), a


def test_perez_uguale_a_pvlib():
    pvlib = pytest.importorskip("pvlib")
    import json
    import numpy as np
    rng = np.random.default_rng(7)
    casi = [dict(zen=float(rng.uniform(5, 85)), az=float(rng.uniform(60, 300)), dhi=float(rng.uniform(20, 400)), dni=float(rng.uniform(0, 900)),
                 tilt=float(rng.uniform(0, 90)), saz=float(rng.uniform(90, 270)), extra=float(rng.uniform(1322, 1412))) for _ in range(100)]
    out = _node(r'''
const E = require(process.argv[1]); const c = JSON.parse(process.argv[2]); const G = Math.PI / 180;
console.log(JSON.stringify(c.map((x) => { const a = 90 - x.zen;
  const ca = Math.cos(a * G) * Math.sin(x.tilt * G) * Math.cos((x.az - x.saz) * G) + Math.sin(a * G) * Math.cos(x.tilt * G);
  const p = E.perez(x.dhi, x.dni, x.zen, x.extra, ca, x.tilt); return p.isotropa + p.circumsolare + p.orizzonte; })));''', json.dumps(casi))
    for x, v in zip(casi, out):
        am = pvlib.atmosphere.get_relative_airmass(x["zen"], "kastenyoung1989")
        ref = float(pvlib.irradiance.perez(x["tilt"], x["saz"], x["dhi"], x["dni"], x["extra"], x["zen"], x["az"], am))
        assert v == pytest.approx(ref, abs=1e-6)


def test_posa_sulla_sagoma():
    d = _node(r'''
const E = require(process.argv[1]); const G = Math.PI / 180;
const L = [[0, 0], [30, 0], [30, 10], [10, 10], [10, 25], [0, 25], [0, 0]];
const pr = E.proiezione(12.57, 44.06), rot = 37;
const f = ([x, y]) => { const c = Math.cos(rot * G), s = Math.sin(rot * G); return [x * c + y * s + 15, -x * s + y * c - 4]; };
const r = E.posaDaSagoma([L], [L.map((q) => pr.indietro(f(q)))]);
const err = r.punti.map(([x, y, lon, lat]) => { const [X, Y] = pr.avanti([lon, lat]), [ex, ey] = f([x, y]); return Math.hypot(X - ex, Y - ey); });
console.log(JSON.stringify({ rot: r.rotazione, iou: r.iou, aree: r.rapporto_aree, err, nulla: E.posaDaSagoma([], []) }));''')
    assert d["rot"] == pytest.approx(37, abs=0.01) and d["iou"] > 0.98 and d["aree"] == pytest.approx(1, abs=1e-6)
    assert max(d["err"]) < 0.01 and d["nulla"] is None


def test_pagine_blocco_2():
    for nome in PAGINE_3D:
        s = (QUI / "sito" / nome).read_text(encoding="utf-8")
        for id_ in ("quota-vetrata", "nota-sede"):
            assert f'id="{id_}"' in s, (nome, id_)
        assert "Tabella 11" in s and "alberi" in s, nome
    js = (QUI / "sito" / "edificio3d.js").read_text(encoding="utf-8")
    assert "eugenio-sede" in js and "lidar/alberi/" in js and "htMassimoPrimoLivello" in js and 'modello_cielo: "Perez (1990)"' in js
    p = (QUI / "sito" / "patrimonio.js").read_text(encoding="utf-8")
    assert "modelli3d.html?sede=locale" in p and "sessionStorage" in p
    i = (QUI / "sito" / "importa-dxf-ifc.html").read_text(encoding="utf-8")
    assert 'value="sagoma"' in i and 'id="campi-sagoma"' in i and "edifici_calcoli.js" in i
    assert "posaDaSagoma" in (QUI / "sito" / "importa_modello.js").read_text(encoding="utf-8")
    v = (QUI / "sito" / "valori_sedi.js").read_text(encoding="utf-8")
    assert "mappaVisura" in v and "superficie_catastale" in v


# ---------------------------------------------------------------- blocco 3 del 05/11/2026 (analisi senza GME e senza UNI)
def test_pagine_blocco_3_senza_gme_ne_uni():
    import json
    for nome, script in (("cog-emissioni.html", "emissioni_cog.js"), ("edificio-clima.html", "analisi_pubbliche.js"),
                         ("edificio-cer.html", "analisi_pubbliche.js"), ("fv-leed.html", None)):
        s = (QUI / "sito" / nome).read_text(encoding="utf-8")
        main = re.search(r"<main[^>]*>", s).group(0)
        assert "segnaposto" not in main and "data-analisi" not in s and "sperimentale" in s, nome
        if script:
            assert f'src="{script}?v=' in s, nome
        assert not any(v in s for v in VIETATI), nome          # nessun dato di mercato
    js = (QUI / "sito" / "emissioni_cog.js").read_text(encoding="utf-8") + (QUI / "sito" / "analisi_pubbliche.js").read_text(encoding="utf-8")
    assert not re.search(r"(?i)\b(pun|psv|igi|ttf|mgp)\b", js) and "gse.it" not in js.lower()
    d = json.loads((QUI / "sito" / "dati" / "ispra_fattori_emissione.json").read_text(encoding="utf-8"))
    terzi = json.loads((QUI.parent / "fase13-cogenerazione" / "dati_terzi" / "ispra_fattori_emissione.json").read_text(encoding="utf-8"))
    assert d == terzi and "CC BY 4.0" in d["licenza"] and "430/26" in d["fonte"]
    # Rapporto ISPRA 430/2026, Tabella 1.7 (2024: consumi 192,6; produzione lorda 209,4) e Tabella 1.4 (gas 2024)
    assert d["elettrico_g_kwh"]["anni"]["2024"] == [418.1, 370.7, 209.4, 192.6]
    assert d["gas_naturale"]["anni"]["2024"] == {"t_co2_tj": 59.089, "t_co2_1000_sm3": 2.026}
    t = (QUI / "parti" / "testata.html").read_text(encoding="utf-8")
    # (08/11/2026) Cambiamento climatico resta sperimentale e accessibile; le altre tre sono in lavorazione
    assert re.search(r'href="edificio-clima.html">Cambiamento climatico <span class="cantiere prova">sperimentale', t)
    for href in ("cog-emissioni.html", "edificio-cer.html", "fv-leed.html"):
        assert f'href="{href}"' not in t and t.count(f'<span class="voce-gme voce-corso" data-pagina="{href}"') == 2, href
    l = (QUI / "sito" / "fv-leed.html").read_text(encoding="utf-8")
    assert "non sono riprodotti" in l and "usgbc.org" in l


def test_calcoli_blocco_3_con_node():
    d = _node(r'''
const E = require(process.argv[1].replace("edifici_calcoli.js", "emissioni_cog.js"));
const A = require(process.argv[1].replace("edifici_calcoli.js", "analisi_pubbliche.js"));
const fs = require("fs");
const r = E.calcola({ elettrica_mwh: 1000, calore_mwh: 1150, gas_mwh_pci: 2650 }, { fattore_rete_g_kwh: 199.6, fattore_gas_t_tj: 59.089, rendimento_caldaia: 0.9 });
const tg = E.daTaglia({ potenza_kwe: 200, ore: 5000, rendimento_elettrico: 0.38, rendimento_termico: 0.44 });
const x = [...Array(60).keys()].map((i) => 1960 + i), y = x.map((v) => 2800 - 5 * (v - 1960));
const t = A.tendenza(x, y), p = A.proietta(t, 2050);
const cer = A.condivisa(A.leggiCer(fs.readFileSync(process.argv[2], "utf8")));
const semplice = A.condivisa([{ ora: "1", sede: "a", cabina: "C", prelievo: 5, immissione: 0 }, { ora: "1", sede: "b", cabina: "C", prelievo: 0, immissione: 3 },
  { ora: "2", sede: "a", cabina: "C", prelievo: 1, immissione: 0 }, { ora: "2", sede: "b", cabina: "C", prelievo: 0, immissione: 4 },
  { ora: "1", sede: "z", cabina: "D", prelievo: 0, immissione: 9 }]);
console.log(JSON.stringify({ r, tg, t: [t.pendenza, t.sen, t.mk.p], p, cer: cer.map((c) => [c.cabina, c.condivisa]), semplice: semplice.map((c) => [c.cabina, c.condivisa]),
  annuo: A.consumoAnnuo({ base: 300, pendenza: 9 }, 2000) }));''', str(QUI / "sito" / "esempi" / "cer_esempio_sintetico.csv"))
    kg = 59.089 * 1000 / 277.7778                                   # kg CO2 per MWh di gas
    assert d["r"]["co2_chp_t"] == pytest.approx(2650 * kg / 1000, rel=1e-6)
    assert d["r"]["co2_separata_t"] == pytest.approx(1000 * 0.1996 + 1150 / 0.9 * kg / 1000, rel=1e-6)
    assert d["r"]["evitata_t"] == pytest.approx(d["r"]["co2_separata_t"] - d["r"]["co2_chp_t"])
    # pareggio: con quel fattore della rete il cogeneratore emette quanto l'alternativa
    s = d["r"]["soglia_rete_g_kwh"]
    assert 1000 * s / 1000 + 1150 / 0.9 * kg / 1000 == pytest.approx(d["r"]["co2_chp_t"], rel=1e-6)
    assert d["tg"]["elettrica_mwh"] == 1000 and d["tg"]["gas_mwh_pci"] == pytest.approx(1000 / 0.38)
    assert d["t"][0] == pytest.approx(-5) and d["t"][1] == pytest.approx(-5) and d["t"][2] < 1e-6
    assert d["p"]["valore"] == pytest.approx(2800 - 5 * 90)
    assert d["semplice"] == [["C", 4], ["D", 0]]                     # ora 1: min(5, 3); ora 2: min(1, 4); D senza prelievi
    assert [c for c, _ in d["cer"]] == ["CP-ESEMPIO-1", "CP-ESEMPIO-2"] and all(v > 0 for _, v in d["cer"])
    assert d["annuo"] == 12 * 300 + 9 * 2000


# ---------------------------------------------------------------- Ortofoto e Modelli 3D dopo le prove del 05/11/2026
def test_ortofoto_e_modelli3d_05_11():
    o = (QUI / "sito" / "ortofoto.html").read_text(encoding="utf-8")
    for js in ("minimappa.js", "confini_gl.js", "esporta_mappa.js"):
        assert f'src="{js}?v=' in o, js
    assert o.index('src="minimappa.js') < o.index('src="ortofoto.js')         # window.EUGENIO prima della pagina
    assert 'id="scarica-ortofoto"' in o and 'id="messaggio-immagine"' in o and "ISTAT" in o
    m = (QUI / "sito" / "modelli3d.html").read_text(encoding="utf-8")
    # i moduli di ricerca li crea cerca_luogo.js nel contenitore (seconda pubblicazione del 05/11/2026)
    for id_ in ("cerca-edificio", "genera-3d", "torna-2d", "apri-demo", "scarica-3d", "fonti-corpi", "aiuto-3d"):
        assert f'id="{id_}"' in m, id_
    assert 'href="modelli3d.html?archivio=demo"' in m
    for js in ("minimappa.js", "confini_gl.js", "esporta_mappa.js"):
        assert f'src="{js}?v=' in m, js
    # 07/11/2026 sera: tutte le pagine 3D hanno la mappa di Modelli 3D (stessi elementi e moduli), la demo è quella della pagina
    for nome in PAGINE_3D[1:]:
        s = (QUI / "sito" / nome).read_text(encoding="utf-8")
        for id_ in ("cerca-edificio", "genera-3d", "torna-2d", "apri-demo", "esci-demo", "scarica-3d", "fonti-corpi", "livelli-mappa", "caselle-strati"):
            assert f'id="{id_}"' in s, (nome, id_)
        for js in ("minimappa.js", "confini_gl.js", "esporta_mappa.js", "cerca_luogo.js", "strati_gl.js", "dbtr_locale.js"):
            assert f'src="{js}?v=' in s, (nome, js)
        assert f'href="{nome}?archivio=demo"' in s and f'id="esci-demo" href="{nome}"' in s, nome
        assert s.index('src="dbtr_locale.js') < s.index('src="edificio3d.js'), nome
    # confini dai file già ospitati, nessun servizio esterno; PDF scritto nel browser, senza librerie
    for js in ("confini_gl.js", "esporta_mappa.js"):
        t = (QUI / "sito" / js).read_text(encoding="utf-8")
        assert not re.search(r"https?://(?!eugenio\.statocritico\.it)[a-z0-9.-]+\.[a-z]{2,}/", t.replace("eugenio.statocritico.it", "")), js
    assert "dati/mappa/italia.json" in (QUI / "sito" / "confini_gl.js").read_text(encoding="utf-8")
    e = (QUI / "sito" / "edificio3d.js").read_text(encoding="utf-8")
    assert "la demo sintetica non va sopra le foto vere" in e and "/api/patrimonio" in e


def test_inversa_utm_dei_confini_con_node():
    import shutil, subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node non installato")
    prova = r'''
global.window = {}; global.document = { currentScript: null, addEventListener() {} };
require(process.argv[1]);
const C = window.EUGENIO_CONFINI;
// trasformazione diretta di comuni.py (fase 3): lon, lat → svg; qui si torna indietro
const S = 0.0010012596459353985, AX = -313.67365575107954, AY = 5226.851664605516;
const [lo, la] = C.utmLonlat(500000 + 3.5683 * 80180, 4879000);
console.log(JSON.stringify({ lo, la, rimini: C.svgLonlat(S * 788000 + AX, -S * 4884000 + AY) }));
'''
    out = subprocess.run([node, "-e", prova, str(QUI / "sito" / "confini_gl.js")], capture_output=True, text=True, encoding="utf-8", check=True).stdout
    import json
    d = json.loads(out)
    from pyproj import Transformer
    t = Transformer.from_crs(32632, 4326, always_xy=True)
    lon, lat = t.transform(788000, 4884000)
    assert d["rimini"][0] == pytest.approx(lon, abs=2e-6) and d["rimini"][1] == pytest.approx(lat, abs=2e-6)
    lon, lat = t.transform(500000 + 3.5683 * 80180, 4879000)
    assert d["lo"] == pytest.approx(lon, abs=2e-6) and d["la"] == pytest.approx(lat, abs=2e-6)


# ---------------------------------------------------------------- seconda pubblicazione del 05/11/2026 (menu e mappe)
def test_etichette_brevi_nelle_tendine():
    """Nelle tendine (e quindi nella riga fissata, che le copia) «S», «GME» e il triangolo giallo; testo intero nel title e
    per i lettori di schermo; nel menu del telefono le parole intere."""
    t = (C.PARTI / "testata.html").read_text(encoding="utf-8")
    tendine = "".join(re.findall(r'<ul class="tendina">.*?</ul>', t, re.S))
    pannello = re.search(r'<nav class="menu-pannello".*?</nav>', t, re.S).group(0)
    assert ">sperimentale<" not in tendine and ">in sviluppo<" not in tendine and ">licenza GME<" not in tendine
    s = re.findall(r'<span class="cantiere prova breve" title="sperimentale"><span aria-hidden="true">S</span><span class="solo-lettori"> \(sperimentale\)</span></span>', tendine)
    v = re.findall(r'<span class="cantiere sviluppo breve" title="in sviluppo"><svg class="segnale"[^>]*aria-hidden="true"', tendine)
    g = re.findall(r'<span class="cantiere breve" title="licenza GME[^"]*" aria-hidden="true">GME</span>', tendine)
    # (08/11/2026) 5 «S» (Cambiamento climatico; Ortofoto, Modelli 3D, Importa DXF/IFC, Aggiungi edifici), 2 triangoli
    # «in sviluppo» cliccabili (LiDAR, Visure), 16 voci in lavorazione con il triangolo e non cliccabili, 6 GME
    assert len(s) == pannello.count(">sperimentale<") == 5 and len(v) == pannello.count(">in sviluppo<") == 2 and len(g) == 6
    assert tendine.count('class="voce-gme voce-corso"') == pannello.count('class="voce-gme voce-corso"') == 16
    assert tendine.count('fill="#f5c400"') == 18 and tendine.count('stroke="#1a1a1a"') >= 18      # giallo con il bordo scuro
    css = (QUI / "sito" / "stile.css").read_text(encoding="utf-8")
    assert ".cantiere.breve" in css and ".cantiere .segnale" in css
    # «Costi energetici Sanità» senza etichetta (pagina validata)
    assert re.search(r'<a href="indicatori.html">Costi energetici Sanità</a>', tendine)


def test_ortofoto_e_modelli3d_seconda_pubblicazione():
    o = (QUI / "sito" / "ortofoto.html").read_text(encoding="utf-8")
    m = (QUI / "sito" / "modelli3d.html").read_text(encoding="utf-8")
    for s in (o, m):
        assert 'src="cerca_luogo.js?v=' in s and 'src="strati_gl.js?v=' in s and 'id="caselle-strati"' in s and 'id="legenda-strati"' in s
        assert "Agenzia" in s and "OpenStreetMap" in s and "ODbL" in s
    assert 'id="cerca-luogo"' in o
    assert 'id="esci-demo" href="modelli3d.html"' in m and 'id="strato-ortofoto"' in m and 'id="cerca-edificio"' in m
    e = (QUI / "sito" / "esporta_mappa.js").read_text(encoding="utf-8")
    assert "showSaveFilePicker" in e and "AbortError" in e and "Download avviato" in e and "controllaCopia" in e
    assert "Immagine scaricata" not in e          # niente più «scaricata» detto prima di sapere se il file è partito
    j = (QUI / "sito" / "edificio3d.js").read_text(encoding="utf-8")
    assert "trascinaPunto" in j and "puntoCambiato" in j and "EUGENIO_CERCA" in j and "EUGENIO_STRATI" in j
    st = (QUI / "sito" / "strati_gl.js").read_text(encoding="utf-8")
    assert "/api/ortofoto/strati" in st and "zornade" not in st.lower()     # nessuna dipendenza nuova da Zornade


def test_aggiungi_dbtr_e_istruzioni():
    """«Aggiungi DBTR» (07/11/2026): pagina dello strumento e pagina delle istruzioni nel gruppo Patrimonio; le librerie
    dei GeoPackage e degli zip (sql.js, fflate) solo nel Web Worker di quella pagina; consenso non spuntato; privacy,
    F.A.Q., Modelli 3D e protezione.js aggiornati."""
    sito = QUI / "sito"
    a = (sito / "aggiungi-dbtr.html").read_text(encoding="utf-8")
    assert 'id="consenso"' in a and 'id="consenso" checked' not in a and 'id="proponi" type="button" disabled' in a
    assert 'src="dbtr_locale.js?v=' in a and 'src="aggiungi_dbtr.js?v=' in a and 'href="dbtr-istruzioni.html"' in a
    assert "sql-wasm" not in a and "fflate" not in a.split("<main")[1].split("piede-fonti")[0]
    w = (sito / "dbtr_worker.js").read_text(encoding="utf-8")
    assert "lib/sql.js/sql-wasm.js" in w and "lib/fflate/fflate.js" in w and "dbtr_lettore.js" in w and "fetch(" not in w
    for f in sito.glob("*.html"):
        if f.name != "aggiungi-dbtr.html":
            t = f.read_text(encoding="utf-8")
            assert "sql-wasm" not in t and "lib/fflate" not in t and "dbtr_worker" not in t, f.name
    for f in ("sql.js/sql-wasm.js", "sql.js/sql-wasm.wasm", "sql.js/LICENSE", "fflate/fflate.js", "fflate/LICENSE"):
        assert (sito / "lib" / f).is_file(), f
    i = (sito / "dbtr-istruzioni.html").read_text(encoding="utf-8")
    for regione in ("emilia-romagna", "lombardia", "friuli-venezia-giulia", "liguria", "trento", "veneto", "altre-regioni"):
        assert f'id="{regione}"' in i
    assert "EPSG:7791" in i and "un comune alla volta" in i and "in attesa di chiarimento dalla Regione" in i
    assert "verifica sul portale" in i
    p = (sito / "privacy.html").read_text(encoding="utf-8")
    assert 'id="dbtr"' in p and "consenso" in p.split('id="dbtr"')[1][:2500]
    assert 'id="aggiungi-dbtr"' in (sito / "faq.html").read_text(encoding="utf-8")
    m = (sito / "modelli3d.html").read_text(encoding="utf-8")
    assert m.index('src="dbtr_locale.js?v=') < m.index('src="edificio3d.js?v=') and 'href="aggiungi-dbtr.html"' in m
    assert "dbtr\\/inizia" in (sito / "protezione.js").read_text(encoding="utf-8")



# ---------------------------------------------------------------- Novità (07/11/2026)
def test_novita_versione_feed_e_menu():
    import tomllib
    import xml.etree.ElementTree as ET
    sys.path.insert(0, str(QUI))
    import costruisci_pagine as CP
    voci = tomllib.loads((QUI / "novita.toml").read_text(encoding="utf-8"))["voce"]
    indice = (QUI / "sito" / "index.html").read_text(encoding="utf-8")
    assert voci[0]["versione"] == CP.versione_attuale(QUI / "sito"), "la prima voce di novita.toml non è la versione di index.html"
    assert CP.leggi_novita() == voci                                    # controlli superati (ordine, campi)
    # nessun dato di mercato né cose private nelle voci
    testo = json.dumps(voci, ensure_ascii=False)
    assert not re.search(r"\b(PUN|PSV|IGI|TTF|EEX|fase 2|uni_privato|Arpae)\b", testo), testo
    # pagina generata e aggiornata, con una sezione per voce
    pag = (QUI / "sito" / "novita.html").read_text(encoding="utf-8")
    assert pag.count('<div class="novita-voce"') == len(voci) and f'id="d{voci[0]["data"].replace("-", "")}"' in pag
    assert CP._senza_parti(pag) == CP._senza_parti(CP.pagina_novita(voci).replace("{{versione}}", voci[0]["versione"]))
    # feed Atom valido: elementi obbligatori, una entry per voce, indirizzi assoluti
    A = "{http://www.w3.org/2005/Atom}"
    xml = (QUI / "sito" / "novita.xml").read_text(encoding="utf-8")
    assert xml == CP.feed_novita(voci)
    r = ET.fromstring(xml.encode("utf-8"))
    assert r.tag == f"{A}feed" and r.find(f"{A}id") is not None and r.find(f"{A}updated").text.startswith(voci[0]["data"])
    entries = r.findall(f"{A}entry")
    assert len(entries) == len(voci) and len({e.find(f"{A}id").text for e in entries}) == len(voci)
    for e in entries:
        for k in ("title", "id", "updated", "content"):
            assert e.find(f"{A}{k}") is not None and e.find(f"{A}{k}").text, k
        assert re.match(r"https://eugenio\.statocritico\.it/novita\.html#d\d{8}(-\d+)?$", e.find(f"{A}link").get("href"))
        assert 'href="https://' in e.find(f"{A}content").text or "href" not in e.find(f"{A}content").text
    # (08/11/2026) in fondo la messa online del 26/10/2026, senza versione: «Meet EuGEnio», «Siamo online»
    ultima = voci[-1]
    assert (ultima["data"], ultima["titolo"], ultima["testo"]) == ("2026-10-26", "Meet EuGEnio", "Siamo online") and "versione" not in ultima
    assert '<h2 id="d20261026">26 ottobre 2026 – Meet EuGEnio</h2>' in pag and '<p class="novita-testo">Siamo online</p>' in pag
    assert entries[-1].find(f"{A}id").text.endswith("novita/d20261026") and entries[-1].find(f"{A}summary").text == "Siamo online"
    with pytest.raises(SystemExit):              # senza versione solo una voce con il solo testo
        f = Path(__import__("tempfile").mkdtemp()) / "n.toml"
        f.write_text('[[voce]]\ndata = "2026-10-26"\ntitolo = "X"\nnuovo = ["a"]\n', encoding="utf-8")
        CP.leggi_novita(f)
    # (08/11/2026, Paolo) la versione del sito resta solo in novita.toml: né in pagina né nel feed (ancore per data)
    corpo_pag = pag[pag.index('<main class="articolo novita"'):pag.index("</main>")]
    corpo_pag = re.sub(r'^<main[^>]*>', "", corpo_pag)
    for v in voci:
        if v.get("versione"):
            assert v["versione"] not in corpo_pag and v["versione"] not in xml, v["versione"]
    assert "Versione del sito" not in pag and "Versione del sito" not in xml
    assert 'id="d20261107"' in pag and 'id="d20261107-2"' in pag             # due voci lo stesso giorno: ancore stabili
    # (08/11/2026, Paolo) solo funzioni per gli utenti: gruppi Nuovo / Migliorato / Verificato, niente modifiche interne
    assert set(re.findall(r'<p class="novita-tipo">([^<]+)</p>', pag)) <= {"Nuovo", "Migliorato", "Verificato"}
    assert "Cambiato" not in pag and "Corretto" not in pag and "Verificato" in pag
    for x in ("anti-robot", "Turnstile", "llms.txt", "assistente AI", "agenti", "proxy", "PMTiles", "WMS", "Caddy", "cache",
              "rotta", "menu"):
        assert x.lower() not in testo.lower(), x
    v07b = next(v for v in voci if v.get("versione") == "20261107b")          # (09/11/2026: non è più la prima voce)
    assert any("Dati climatici" in r and "Legge 10" in r for r in v07b["verificato"])
    assert any("Previsioni" in r for r in next(v for v in voci if v.get("versione") == "20261109a")["verificato"])
    with pytest.raises(SystemExit, match="campi sconosciuti"):
        f = Path(__import__("tempfile").mkdtemp()) / "c.toml"
        f.write_text('[[voce]]\ndata = "2026-11-01"\nversione = "20261101a"\ntitolo = "X"\ncorretto = ["a"]\n', encoding="utf-8")
        CP.leggi_novita(f)
    # testata: Novità tra Mirror e Contattaci, nel menu del computer e del telefono; feed nella testa comune
    for nome in ("index.html", "faq.html", "modelli3d.html", "novita.html"):
        s = (QUI / "sito" / nome).read_text(encoding="utf-8")
        info = re.search(r'<nav class="menu-info"[^>]*>(.*?)</nav>', s, re.S).group(1)
        assert re.findall(r">([^<]+)</a>", info) == ["Come funziona", "F.A.Q.", "Sitografia", "Mirror", "Novità", "Contattaci"], nome
        assert s.count(f'class="voce-novita" data-ultima="{voci[0]["versione"]}"') >= 2, nome
        assert '<link rel="alternate" type="application/atom+xml" title="Novità di EuGEnio" href="novita.xml">' in s, nome
    assert "application/atom+xml" in (QUI.parent / "fase4-server" / "Caddyfile").read_text(encoding="utf-8")


# ---------------------------------------------------------------- menu dell'08/11/2026 (decisioni di Paolo, ore 12:19)
# pagine «in lavorazione»: voce col triangolo giallo e non cliccabile, nessun collegamento nel sito, avviso in cima
PAGINE_IN_CORSO = ["edificio-obblighi.html", "edificio-geometria.html", "edificio-consumi.html", "edificio-fabbisogno.html",
                   "edificio-involucro.html", "edificio-impianti.html", "edificio-ecobonus.html", "edificio-conto-termico.html",
                   "cog-emissioni.html", "fv-ombre.html", "fv-irradiazione.html", "fv-producibilita.html", "fv-pvgis.html",
                   "fv-dlgs199.html", "fv-leed.html", "edificio-cer.html"]
ACCESSIBILI = {"clima": ["dati.html", "legge10.html", "./", "edificio-clima.html"],
               "patrimonio": ["patrimonio.html", "ortofoto.html", "lidar.html", "modelli3d.html", "importa-dxf-ifc.html",
                              "aggiungi-dbtr.html", "dbtr-istruzioni.html", "visure.html"],
               "statistiche": ["indicatori.html"]}


def test_menu_08_11_gruppi_e_voci_in_lavorazione(sito):
    t = (C.PARTI / "testata.html").read_text(encoding="utf-8")
    gruppi = {g["id"]: g for g in C.gruppi_menu(t)}
    assert [g["titolo"] for g in gruppi.values()] == ["Clima e meteo", "Patrimonio", "Edifici", "Cogenerazione", "Fotovoltaico", "Statistiche"]
    for gid, voci in ACCESSIBILI.items():
        assert [v["pagina"] for v in gruppi[gid]["voci"]] == voci and all(v["tipo"] == "" for v in gruppi[gid]["voci"]), gid
    assert gruppi["clima"]["voci"][-1]["nome"] == "Cambiamento climatico"
    # Edifici: «Obblighi di legge» prima voce, Ecobonus e Conto Termico in fondo, tutte in lavorazione
    ed = gruppi["edificio"]["voci"]
    assert ed[0]["nome"] == "Obblighi di legge" and [v["nome"] for v in ed[-2:]] == ["Ecobonus", "Conto Termico"]
    assert all(v["tipo"] == "corso" for v in ed)
    # Comunità energetiche nel Fotovoltaico, prima della voce GME
    fv = gruppi["fotovoltaico"]["voci"]
    assert [v["pagina"] for v in fv[-2:]] == ["edificio-cer.html", "fv-mercato.html"] and fv[-1]["tipo"] == "gme"
    assert [v["tipo"] for v in gruppi["cogenerazione"]["voci"]].count("corso") == 1
    assert sorted(C.pagine_in_corso(t)) == sorted(PAGINE_IN_CORSO)
    for p in PAGINE_IN_CORSO:
        assert f'href="{p}"' not in t, p                                       # né tendina né menu del telefono
        voci = re.findall(rf'<span class="voce-gme voce-corso" data-pagina="{re.escape(p)}"[^>]*>', t)
        assert len(voci) == 2 and all('aria-disabled="true"' in v and 'title="In lavorazione: disponibile prossimamente"' in v for v in voci), p
        assert (QUI / "sito" / p).exists(), p                                  # la pagina resta nel sito
    C.main(["--sito", str(sito)])
    for p in PAGINE_IN_CORSO:
        s = (sito / p).read_text(encoding="utf-8")
        # avviso in cima, subito dopo la testata, una volta sola; il gruppo del menu resta segnato
        assert s.count("Pagina in lavorazione, non ancora verificata.") == 1, p
        assert s.index("<!-- /testata -->") < s.index("<!-- in-lavorazione -->") < s.index("<main"), p
        assert len(re.findall(rf'<span class="voce-gme voce-corso" data-pagina="{re.escape(p)}"[^>]*aria-current="page"', s)) == 2, p
        assert s.count("data-attivo") == 2, p
    for p in ("modelli3d.html", "edificio-clima.html", "index.html", "cog-car.html"):
        assert "<!-- in-lavorazione -->" not in (sito / p).read_text(encoding="utf-8"), p


def test_nessun_collegamento_interno_alle_pagine_in_lavorazione(sito):
    """Come le pagine GME: nessun collegamento del sito porta a una pagina in lavorazione (né il menu, né «Nello stesso
    gruppo», né i testi, né le Novità); resta solo il collegamento della pagina a sé stessa."""
    C.main(["--sito", str(sito)])
    for f in sorted(sito.glob("*.html")):
        s = f.read_text(encoding="utf-8")
        for m in re.finditer(r'<a [^>]*href="([^"#?]+)[^"]*"[^>]*>', s):
            if m.group(1) in PAGINE_IN_CORSO:
                assert m.group(1) == f.name, (f.name, m.group(0))
    for js in sorted((QUI / "sito").glob("*.js")):
        t = js.read_text(encoding="utf-8")
        for p in PAGINE_IN_CORSO:
            assert not re.search(rf'["\'`]{re.escape(p)}', t), (js.name, p)   # nessun «Apri in…» verso le pagine in lavorazione
    voci = C.leggi_novita()
    assert not any(c["indirizzo"] in PAGINE_IN_CORSO for v in voci for c in v.get("collegamenti", []))
    testo = json.dumps(voci, ensure_ascii=False)
    for vecchio in ("Edificio ›", "Fotovoltaico:", "Cogenerazione ›", "Le pagine Edificio", "pagine 3D"):
        assert vecchio not in testo, vecchio
    assert any("Clima e meteo › Cambiamento climatico" in x for x in next(v for v in voci if v.get("versione") == "20261107b").get("migliorato", []))


def test_stesso_gruppo_ed_etichetta_dal_menu(sito):
    """«Nello stesso gruppo» e l'etichetta del gruppo sopra il titolo vengono dal menu della testata."""
    C.main(["--sito", str(sito)])
    s = (sito / "edificio-clima.html").read_text(encoding="utf-8")
    assert '<p class="gruppo-servizio">Clima e meteo</p>' in s and "<h1>Cambiamento climatico</h1>" in s
    assert "<title>EuGEnio – Cambiamento climatico</title>" in s and "Clima che cambia" not in s
    blocco = re.search(r'<ul class="stesso-gruppo">(.*?)</ul>', s, re.S).group(1)
    assert re.findall(r'href="([^"]+)"', blocco) == ["dati.html", "legge10.html", "./", "edificio-clima.html"]
    s = (sito / "edificio-cer.html").read_text(encoding="utf-8")
    assert '<p class="gruppo-servizio">Fotovoltaico</p>' in s
    blocco = re.search(r'<ul class="stesso-gruppo">(.*?)</ul>', s, re.S).group(1)
    assert blocco.count('class="voce-gme voce-corso"') == 6 and blocco.count('title="In attesa di autorizzazione dal GME"') == 1
    assert re.findall(r'href="([^"]+)"', blocco) == ["edificio-cer.html"]
    for p in ("edificio-geometria.html", "edificio-ecobonus.html", "edificio-conto-termico.html", "edificio-fabbisogno.html"):
        assert '<p class="gruppo-servizio">Edifici</p>' in (sito / p).read_text(encoding="utf-8"), p
    s = (sito / "lidar.html").read_text(encoding="utf-8")
    blocco = re.search(r'<ul class="stesso-gruppo">(.*?)</ul>', s, re.S).group(1)
    assert re.findall(r'href="([^"]+)"', blocco) == ACCESSIBILI["patrimonio"]
    for p in ("edificio-ecobonus.html", "edificio-conto-termico.html"):
        s = (sito / p).read_text(encoding="utf-8")
        assert 'class="articolo segnaposto"' in s and 'class="stato-pagina"' in s and 'id="fonti"' in s, p


def test_ricerca_esempio_cesena_e_partenza():
    js = (QUI / "sito" / "cerca_luogo.js").read_text(encoding="utf-8")
    assert 'placeholder: "viale Ghirotti 286"' in js and 'placeholder: "Cesena"' in js and "Gambalunga" not in js
    m = re.search(r"const PARTENZA = \{ lon: ([\d.]+), lat: ([\d.]+), zoom: ([\d.]+)", js)
    lon, lat, z = map(float, m.groups())
    # ospedale Bufalini (particella foglio 149 n. 387 dell'archivio DBTR di Cesena: 44,1319–44,1364 N, 12,2580–12,2625 E)
    assert 12.2580 < lon < 12.2625 and 44.1310 < lat < 44.1364 and 15 <= z <= 16.5
    assert "partenza()" in (QUI / "sito" / "edificio3d.js").read_text(encoding="utf-8")
    assert "P0.zoom" in (QUI / "sito" / "ortofoto.js").read_text(encoding="utf-8")
    assert 'placeholder="Es. viale Ghirotti 286, Cesena' in (QUI / "sito" / "index.html").read_text(encoding="utf-8")


def test_confini_json_validi_per_il_browser():
    """09/11/2026 (prove J10, «Comune "torino" non trovato»): 01.json aveva un NaN (comune «None» di Torino) e 15.json 92
    NaN (sigla «NA» di Napoli): JSON.parse del browser falliva e tutto il Piemonte e la Campania mancavano. Ogni file deve
    essere JSON stretto, con nome e sigla di provincia testuali per tutti i comuni."""
    import json
    cartella = Path(__file__).resolve().parents[1] / "sito" / "dati" / "mappa"
    def no_nan(x):
        raise ValueError(f"valore non JSON: {x}")
    n = 0
    for f in sorted(cartella.glob("[0-9][0-9].json")):
        d = json.loads(f.read_text(encoding="utf-8"), parse_constant=no_nan)
        for c in d["comuni"]:
            assert isinstance(c["nome"], str) and c["nome"] and isinstance(c["prov"], str) and c["prov"], (f.name, c["istat"])
            n += 1
    assert n > 7800
    d = {c["istat"]: c for c in json.loads((cartella / "01.json").read_text(encoding="utf-8"))["comuni"]}
    assert d["001272"]["nome"] == "Torino" and d["001168"]["nome"] == "None"
    assert all(c["prov"] == "NA" for c in json.loads((cartella / "15.json").read_text(encoding="utf-8"))["comuni"] if c["istat"].startswith("063"))
