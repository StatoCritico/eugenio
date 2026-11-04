"""Ortofoto AGEA scaricate a mano per un sito puntuale (fase 10, Fase B, § 6 della proposta, fonte n. 3).

Procedura (a mano, fuori dalla pipeline notturna):
  1. Dal GeoPortale AGEA (https://geoportale.agea.gov.it) si scaricano le tessere dell'ortofoto **RGB** 2022, 2023 o
     2024 che coprono il sito (al massimo 20 tessere per richiesta, codice via email, limite giornaliero). Licenza
     CC BY 4.0 (note legali del GeoPortale, Reg. UE 2023/138). **Mai** l'infrarosso né le foto originali (convenzione
     per le PA: solo fini istituzionali).
  2. `python -m edifici3d ortofoto-sito --sito ospedale-rimini --anno 2023 --archivio /srv/energia/dati/edifici \\
        tessera1.tif tessera2.tif …`
     unisce le tessere, tiene solo le bande rosso, verde e blu (una quarta banda, l'infrarosso, si scarta e si
     segnala), riporta tutto in web mercator a **50 cm** a terra, scrive un COG JPEG e un PMTiles di tessere JPEG
     (zoom 14–18) e la scheda `indice.json` con licenza, citazione, data e impronta SHA256 delle tessere di partenza.
  3. I file vanno in `<archivio>/cc-by/ortofoto_siti/<sito>/`; l'elenco di tutti i siti in
     `<archivio>/cc-by/ortofoto_siti/indice.json`. Caddy li serve da `/edifici3d/cc-by/ortofoto_siti/` e la pagina
     Ortofoto li offre come fonti in più, con la citazione «AGEA – Ortofoto <anno> RGB (CC BY 4.0)».
  4. Le tessere scaricate (grezzi) si cancellano dopo il controllo: resta solo la versione a 50 cm.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import math
import re
from pathlib import Path

import numpy as np

from . import tessere

RISOLUZIONE_M = 0.5
ZOOM = (14, 18)
LICENZA = "CC BY 4.0"
SCHEDA = "https://geoportale.agea.gov.it/legal-notes"


def citazione(anno: int) -> str:
    return f"AGEA – Ortofoto {anno} RGB, ridotta a 50 cm da EuGEnio (CC BY 4.0)"


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _jpeg(rgb: np.ndarray, qualita: int = 85) -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.fromarray(rgb, "RGB").save(b, format="JPEG", quality=qualita, optimize=True)
    return b.getvalue()


def prepara(tessere_tif: list[Path], sito: str, anno: int, archivio: Path) -> dict:
    """Mosaico → web mercator a 50 cm → COG + PMTiles JPEG + indice. Restituisce la scheda del sito."""
    import rasterio
    from rasterio.merge import merge
    from rasterio.warp import Resampling, calculate_default_transform, reproject, transform_bounds
    from rasterio.transform import from_bounds

    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,60}", sito):
        raise ValueError("nome del sito: minuscole, cifre e trattini")
    if not (2022 <= anno <= 2030):
        raise ValueError("anno: solo ortofoto AGEA dal 2022 (RGB, CC BY 4.0)")
    if not tessere_tif:
        raise ValueError("nessuna tessera")
    avvisi = []
    sorgenti = [rasterio.open(p) for p in tessere_tif]
    try:
        bande = {s.count for s in sorgenti}
        if min(bande) < 3:
            raise ValueError("le tessere devono avere almeno le tre bande RGB")
        if max(bande) > 3:
            avvisi.append("quarta banda (infrarosso) scartata: si tengono solo rosso, verde e blu")
        crs = sorgenti[0].crs
        if any(s.crs != crs for s in sorgenti):
            raise ValueError("le tessere hanno sistemi di riferimento diversi")
        mosaico, trasf = merge(sorgenti, indexes=[1, 2, 3])
        nodata = sorgenti[0].nodata
    finally:
        for s in sorgenti:
            s.close()
    h, w = mosaico.shape[1:]
    lim = rasterio.transform.array_bounds(h, w, trasf)          # (ovest, sud, est, nord)
    lon0, lat0, lon1, lat1 = transform_bounds(crs, "EPSG:4326", *lim)
    # 50 cm a terra in web mercator: il metro di mercatore vale 1/cos(lat) metri a terra
    scala = 1 / math.cos(math.radians((lat0 + lat1) / 2))
    t3857, W, H = calculate_default_transform(crs, "EPSG:3857", w, h, *lim,
                                              resolution=RISOLUZIONE_M * scala)
    out = np.zeros((3, H, W), dtype="uint8")
    for b in range(3):
        reproject(mosaico[b], out[b], src_transform=trasf, src_crs=crs, src_nodata=nodata,
                  dst_transform=t3857, dst_crs="EPSG:3857", dst_nodata=0, resampling=Resampling.average)
    cartella = archivio / "cc-by" / "ortofoto_siti" / sito
    cartella.mkdir(parents=True, exist_ok=True)
    cog = cartella / "ortofoto_cog.tif"
    with rasterio.open(cog, "w", driver="COG", width=W, height=H, count=3, dtype="uint8", crs="EPSG:3857",
                       transform=t3857, compress="JPEG", quality=85, blocksize=512, overviews="AUTO") as d:
        d.write(out)
    # tessere JPEG per MapLibre
    tiles: dict[tuple[int, int, int], bytes] = {}
    for z in range(ZOOM[0], ZOOM[1] + 1):
        x0, y1 = tessere.lonlat_a_tessera(lon0, lat0, z)
        x1, y0 = tessere.lonlat_a_tessera(lon1, lat1, z)
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                a, s_, e, n = tessere.limiti_mercatore(z, x, y)
                t = np.zeros((3, 256, 256), dtype="uint8")
                for b in range(3):
                    reproject(out[b], t[b], src_transform=t3857, src_crs="EPSG:3857", src_nodata=0,
                              dst_transform=from_bounds(a, s_, e, n, 256, 256), dst_crs="EPSG:3857", dst_nodata=0,
                              resampling=Resampling.bilinear)
                if not t.any():
                    continue
                tiles[(z, x, y)] = _jpeg(np.moveaxis(t, 0, -1))
    pm = cartella / "ortofoto.pmtiles"
    tessere.scrivi_pmtiles(pm, tiles, tipo="jpg", limiti=(lon0, lat0, lon1, lat1), zoom=ZOOM,
                           metadati={"name": f"ortofoto {sito}", "attribution": citazione(anno),
                                     "description": "Ortofoto AGEA RGB ridotta a 50 cm"})
    scheda = {"sito": sito, "anno": anno, "fonte": "AGEA", "licenza": LICENZA, "citazione": citazione(anno), "scheda": SCHEDA,
              "risoluzione_m": RISOLUZIONE_M, "riquadro": [round(v, 6) for v in (lon0, lat0, lon1, lat1)],
              "zoom": list(ZOOM), "tessere": len(tiles), "preparata": dt.date.today().isoformat(),
              "originali": [{"file": Path(p).name, "sha256": _sha(Path(p))} for p in tessere_tif], "avvisi": avvisi,
              "pmtiles": f"/edifici3d/cc-by/ortofoto_siti/{sito}/ortofoto.pmtiles"}
    (cartella / "indice.json").write_text(json.dumps(scheda, ensure_ascii=False, indent=1), encoding="utf-8")
    aggiorna_elenco(archivio)
    return scheda


def aggiorna_elenco(archivio: Path) -> list[dict]:
    radice = archivio / "cc-by" / "ortofoto_siti"
    siti = []
    for p in sorted(radice.glob("*/indice.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        siti.append({k: d[k] for k in ("sito", "anno", "licenza", "citazione", "scheda", "riquadro", "zoom", "pmtiles")})
    (radice / "indice.json").write_text(json.dumps({"siti": siti}, ensure_ascii=False, indent=1), encoding="utf-8")
    return siti
