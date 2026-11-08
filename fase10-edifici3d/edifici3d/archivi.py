"""archivi.json: elenco degli archivi degli edifici letto da Modelli 3D (07/11/2026).

Modulo leggero (solo json, re, pathlib e la tabella dei comuni di `uvl`): lo usano il comando `archivi-json`, `prepara
--archivi-json` e l'installazione degli archivi approvati dalla coda «Aggiungi DBTR» (`coda.py`).

Si elencano gli indici di `<archivio>/*/*/prodotti/` (archivi regionali, es. `cc-by/er/prodotti/`) e di
`<archivio>/*/*/*/prodotti/` (un archivio per comune, es. `cc-by/er/rimini/prodotti/`, `cc-by/lom/bergamo/prodotti/`).
Le cartelle che cominciano con «_» (per esempio `_precedenti/`, le copie tenute per tornare indietro) non si elencano mai.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# codici ISTAT dei comuni ER con l'estrazione DBTR scaricata il 06/11/2026 (copia di uvl.COMUNI_ISTAT, che resta la
# tabella di riferimento: qui per non importare shapely nell'immagine dell'api)
try:
    from .uvl import COMUNI_ISTAT
except Exception:  # pragma: no cover - senza shapely (non succede nelle immagini del progetto)
    COMUNI_ISTAT = {}


def _nascosta(rel: str) -> bool:
    return any(p.startswith("_") for p in rel.split("/"))


def scrivi_archivi_json(archivio: Path, prova: bool = False) -> dict:
    """<archivio>/archivi.json dagli indici presenti (cc-by/er/prodotti/, cc-by/<regione>/<comune>/prodotti/,
    iodl/<regione>/<comune>/prodotti/, odbl/<nome>/prodotti/): prima gli archivi dei DB topografici (CC BY 4.0 e 2.5,
    IODL 2.0, CC0 1.0: dei comuni e regionali, più affidabili; cartelle per licenza nel README, 08/11/2026), poi gli
    archivi ODbL veri, per ultimi gli archivi di prova OSM (solo se prova=True: dal 07/11/2026, decisione di Paolo,
    **non** si elencano più – fuori dal DBTR la pagina usa il ripiego OSM al volo, GET /api/edifici/osm – e i file restano
    sul server come riserva). Il file precedente si copia in archivi.json.prima. Ogni voce: base, nome, licenza,
    attribuzione, riquadro (la pagina interroga solo gli archivi il cui riquadro tocca il punto) e, per gli archivi di un
    comune intero, `istat`: la pagina considera coperto dal DB topografico il confine ISTAT del comune (non il riquadro,
    che sborda sui comuni vicini)."""
    archivio = Path(archivio)
    voci = []
    for ind in sorted(list(archivio.glob("*/*/prodotti/indice.json")) + list(archivio.glob("*/*/*/prodotti/indice.json"))):
        rel = ind.parent.relative_to(archivio).as_posix()
        if _nascosta(rel):
            continue
        try:
            d = json.loads(ind.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if d.get("sintetico"):
            continue
        lic = d.get("licenza", "")
        # DB topografici con licenza di sola attribuzione (CC BY x.y, IODL 2.0) o CC0 prima di ODbL (08/11/2026)
        ordine = (0 if lic.startswith(("CC BY", "IODL", "CC0")) else 1) + (2 if d.get("prova") else 0)
        if d.get("prova") and not prova:
            continue
        voce = {"base": f"/edifici3d/{rel}/", "nome": d.get("nome") or rel, "licenza": lic,
                "attribuzione": d.get("attribuzione", ""), "riquadro": d.get("riquadro"), "corpi": d.get("corpi")}
        istat = d.get("istat") or (None if d.get("parziale") else COMUNI_ISTAT.get(str(d.get("comune") or "")))
        if istat and re.fullmatch(r"\d{6}", str(istat)):
            voce["istat"] = str(istat)
        voci.append((ordine, rel, voce))
    voci.sort(key=lambda x: (x[0], x[1]))
    esito = {"archivi": [v for _, _, v in voci]}
    # falde e alberi dal LiDAR: archivio regionale dell'ER (pipeline notturna), anche quando i corpi sono per comune
    # (07/11/2026 sera) solo se la pipeline ha già scritto lidar/indice.json: prima la pagina non lo chiede (niente 404);
    # la pipeline rigenera archivi.json quando scrive il primo indice delle falde
    if any(v["base"].startswith("/edifici3d/cc-by/er/") for _, _, v in voci) and \
            (archivio / "cc-by" / "er" / "prodotti" / "lidar" / "indice.json").is_file():
        esito["lidar"] = "/edifici3d/cc-by/er/prodotti/"
    dest = archivio / "archivi.json"
    if dest.exists():
        (archivio / "archivi.json.prima").write_bytes(dest.read_bytes())
    tmp = dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(esito, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(dest)                        # mai un archivi.json a metà per la pagina
    return esito
