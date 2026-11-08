"""Altezze del DBTR non plausibili portate alla stima (plausibilita.py, decisione del 07/11/2026) e parità con il lettore
del sito (dbtr_lettore.js, funzione `plausibilita`, in node). Casi presi dai 19 comuni veri: Bagno di Romagna 114 m su
8,3 m² (cade), Grattacielo di Rimini 83 m su 17 × 47 m (resta), campanile di Faenza 44,5 m (resta), ciminiera di Forlì
60 m su 14 m² (resta), torrino di scala sopra un palazzo di 35 m (resta)."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from shapely.geometry import box

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent))
from edifici3d import plausibilita as PL  # noqa: E402
from edifici3d.modello import Corpo  # noqa: E402

SITO = QUI.parents[1] / "fase5-sito" / "sito"


def _corpo(i, x, y, lx, ly, h, dest=None, tipo=None, uso="residenziale", colmo=None):
    extra = {k: v for k, v in (("destinazione", dest), ("tipo_edificio", tipo), ("foglio", "1"), ("numero", str(i))) if v}
    return Corpo(id=f"c{i}", edificio=f"e{i}", sagoma=box(x, y, x + lx, y + ly), quota_terreno=10.0, gronda=float(h),
                 colmo=colmo, tetto="capanna" if colmo else "piano", falde=2 if colmo else 0, fonte_sagoma="DBTR",
                 licenza="CC BY 4.0", fonte_altezza="DBTR H_UVL", uso=uso, extra=extra)


def quartiere():
    """Case di 7–9 m ogni 25 m su 300 × 300 m, più i casi speciali; un corpo isolato a 2 km."""
    c, i = [], 0
    for gx in range(12):
        for gy in range(12):
            c.append(_corpo(i, gx * 25.0, gy * 25.0, 12, 10, 7 + (gx + gy) % 3)); i += 1
    speciali = [
        ("bagno", _corpo(900, 101.0, 113.0, 2.9, 2.9, 114.0, "abitativa", "generica")),              # 8,4 m²
        ("sottile", _corpo(901, 151.0, 163.0, 2.5, 2.0, 41.0, "abitativa", "generica")),
        ("grattacielo", _corpo(902, 51.0, 213.0, 17.0, 47.0, 83.0, "abitativa", "generica", colmo=85.0)),
        ("campanile", _corpo(903, 201.0, 63.0, 9.0, 9.5, 44.5, "luogo di culto", "campanile")),
        ("ciminiera", _corpo(904, 251.0, 263.0, 3.7, 3.7, 60.2, "stabilimento industriale", "capannone")),
        ("palazzo", _corpo(905, 1000.0, 1000.0, 20.0, 20.0, 35.0, "abitativa", "generica")),
        ("torrino", _corpo(906, 1021.0, 1005.0, 3.0, 3.0, 33.0, "abitativa", "generica")),         # tocca il palazzo
        ("isolato", _corpo(907, 2000.0, 2000.0, 3.0, 3.0, 50.0, "abitativa", "generica", uso="residenziale")),
        ("capannone_isolato", _corpo(908, 3000.0, 3000.0, 3.0, 3.0, 50.0, None, "generica", uso="capannone")),
    ]
    return c + [x for _, x in speciali], {k: x.id for k, x in speciali}


def test_regola_sui_casi_veri():
    corpi, ids = quartiere()
    cambi = {x["id"]: x for x in PL.applica(corpi)}
    assert set(cambi) == {ids["bagno"], ids["sottile"], ids["isolato"], ids["capannone_isolato"]}
    per_id = {c.id: c for c in corpi}
    b = per_id[ids["bagno"]]
    assert b.extra["h_dbtr_scartata"] == 114.0 and 7 <= b.gronda <= 9 and b.extra["stima_altezza"] == "vicini"
    assert b.fonte_altezza == "stima: altezza DBTR non plausibile (114 m)" and b.qualita == PL.QUALITA
    assert b.colmo is None and b.tetto == "piano"
    assert per_id[ids["isolato"]].gronda == 6.3 and per_id[ids["isolato"]].extra["stima_altezza"] == "uso"
    assert per_id[ids["capannone_isolato"]].gronda == 8.0
    for k in ("grattacielo", "campanile", "ciminiera", "palazzo", "torrino"):
        assert "h_dbtr_scartata" not in per_id[ids[k]].extra, k
    assert per_id[ids["grattacielo"]].colmo == 85.0


def test_funzioni_di_base():
    assert PL.larghezza_minima([(0, 0), (10, 0), (10, 4), (0, 4)]) == pytest.approx(4.0)
    assert PL.larghezza_minima([(0, 0), (10, 10), (12, 8), (2, -2)]) == pytest.approx(2 * 2 ** 0.5)
    assert PL.testo_metri(47.94) == "47,9" and PL.testo_metri(114.0) == "114" and PL.testo_metri(30.25) == "30,3"
    assert PL.mediana([3, 1, 2]) == 2 and PL.mediana([1, 2, 3, 4]) == 2.5 and PL.mediana([]) is None
    assert PL.mezzo_metro(7.25) == 7.5 and PL.mezzo_metro(7.2) == 7.0
    assert PL.verticale("luogo di culto", None) and PL.verticale(None, "capannone") and not PL.verticale("abitativa", "generica")


@pytest.mark.skipif(not shutil.which("node"), reason="node non disponibile")
def test_parita_con_il_lettore_del_sito(tmp_path):
    corpi, _ = quartiere()
    ingresso = [{"id": c.id, "sagoma": [[list(p) for p in c.sagoma.exterior.coords]], "gronda": c.gronda, "colmo": c.colmo,
                 "tetto": c.tetto, "falde": c.falde, "uso": c.uso, "extra": c.extra, "fonte_altezza": c.fonte_altezza,
                 "qualita": c.qualita} for c in corpi]
    (tmp_path / "in.json").write_text(json.dumps(ingresso), encoding="utf-8")
    script = ("const D=require(process.argv[1]);const fs=require('fs');const c=JSON.parse(fs.readFileSync(process.argv[2]));"
              "D.plausibilita(c);fs.writeFileSync(process.argv[3],JSON.stringify(c));")
    subprocess.run(["node", "-e", script, str(SITO / "dbtr_lettore.js"), str(tmp_path / "in.json"), str(tmp_path / "out.json")],
                   check=True, timeout=60)
    js = {c["id"]: c for c in json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))}
    PL.applica(corpi)
    for c in corpi:
        j = js[c.id]
        assert (j["gronda"], j["colmo"], j["tetto"], j["fonte_altezza"], j["qualita"]) == \
               (c.gronda, c.colmo, c.tetto, c.fonte_altezza, c.qualita), c.id
        assert j["extra"].get("h_dbtr_scartata") == c.extra.get("h_dbtr_scartata"), c.id
        assert j["extra"].get("stima_altezza") == c.extra.get("stima_altezza"), c.id
