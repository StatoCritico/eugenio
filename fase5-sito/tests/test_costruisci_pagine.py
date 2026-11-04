"""Prove di costruisci_pagine.py su una copia del sito."""
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
GRUPPI = {"clima": ["dati.html", "legge10.html", "./"],
          "patrimonio": ["patrimonio.html", "ortofoto.html", "lidar.html", "modelli3d.html", "importa-dxf-ifc.html", "visure.html"]}
VIETATI = ("PUN Index GME =", "€/MWh", "Prezzo medio")   # nessun valore nelle pagine in attesa della licenza GME


def test_menu_cinque_gruppi_e_voci_raggiungibili(sito):
    C.main(["--sito", str(sito)])
    t = (C.PARTI / "testata.html").read_text(encoding="utf-8")
    titoli = re.findall(r'<details class="voce-gruppo"[^>]*><summary>([^<]+)</summary>', t)
    assert titoli == ["Clima e meteo", "Patrimonio", "Edificio", "Cogenerazione", "Fotovoltaico"]
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
    assert "data-attivo" not in s                 # Indicatori sta tra le altre pagine, fuori dai gruppi


def test_segnaposto_senza_dati_gme(sito):
    C.main(["--sito", str(sito)])
    pagine = [f for f in sito.glob("*.html") if 'class="articolo segnaposto"' in f.read_text(encoding="utf-8")]
    assert len(pagine) >= 15        # 20 al 03/11/2026; dal 04/11/2026 (Fase B) Ortofoto, Irradiazione, PVGIS, D.Lgs. 199 e Obblighi sono strumenti
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
    out = subprocess.run([node, "-e", prova, str(QUI / "sito" / "edifici_calcoli.js")], capture_output=True, text=True, check=True).stdout
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
    for href in ("ortofoto.html", "fv-irradiazione.html", "fv-pvgis.html", "fv-dlgs199.html", "edificio-obblighi.html"):
        assert re.search(rf'href="{re.escape(href)}">[^<]*<span class="cantiere prova">sperimentale', t), href


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
    d = json.loads(subprocess.run([node, "-e", prova, str(QUI / "sito" / "edifici_calcoli.js")], capture_output=True, text=True,
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


ANALISI_PAGINE = {"edificio-fabbisogno.html": {"5"}, "edificio-cer.html": {"7"}, "edificio-involucro.html": {"8", "12"},
                  "fv-leed.html": {"9"}, "edificio-impianti.html": {"10", "11"}, "edificio-clima.html": {"13"}}


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
    assert trovati == {"5", "7", "8", "9", "10", "11", "12", "13"}
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
    assert "method: \"POST\"" not in p and "/api/" in p and p.count("fetch(") == 1   # solo /api/ortofoto/fonti
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
    assert "clima|patrimonio|edificio|cogenerazione|fotovoltaico" in h
    js = (QUI / "sito" / "aspetto.js").read_text(encoding="utf-8")
    for testo in ("Clicca qui per fissare il menu ${nome} sotto la barra",
                  "Clicca qui per richiudere la barra di ${nome} e tornare al menu a tendina", "aria-pressed", '"menu-fissato"'):
        assert testo in js, testo
    css = (QUI / "sito" / "stile.css").read_text(encoding="utf-8")
    assert "--nero-riga: #000" in css and ":root[data-menu-fissato] .riga-fissata" in css
