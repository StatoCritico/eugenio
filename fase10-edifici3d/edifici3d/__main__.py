"""Riga di comando della fase 10 (Fase A).

  python -m edifici3d scarica --fonte dbtr_uvl --archivio /srv/energia/dati/edifici
  python -m edifici3d controlla-uvl --gpkg UVL.gpkg [--riquadro x0 y0 x1 y1]     # rapporto sugli attributi
  python -m edifici3d controlla-uvl --wms-punto 44.06 12.566                        # pochi corpi dal WMS pubblico
  python -m edifici3d prepara --gpkg UVL.gpkg --dtm dtm5.tif --archivio … [--riquadro …]
  python -m edifici3d demo --uscita ../fase5-sito/sito/dati/edifici3d               # dati sintetici per la pagina 3D
  python -m edifici3d ortofoto-sito --sito ospedale-rimini --anno 2023 --archivio … t1.tif t2.tif   # AGEA a mano (Fase B)

Fase C (LiDAR e pipeline notturna; zone in zone/*.toml):
  python -m edifici3d lidar --zona rimini --archivio /srv/energia/dati/edifici --stato /srv/energia/dati/edifici_stato
  python -m edifici3d lidar --zona auto …            # la prima zona della coda con tessere da fare (cron delle 3:30)
  python -m edifici3d lidar … --subito --max-minuti 20 --tessere 32_78504884   # prova fuori finestra su una tessera
  python -m edifici3d lidar … --aggiorna             # aggiornamento annuale: solo le tessere con fonte cambiata
  python -m edifici3d lidar-stato --stato …          # riepilogo delle zone (lo stesso della pagina di stato)
  python -m edifici3d lidar-fonti --zona rimini [--prova]   # fonti, stato e motivo; --prova controlla dal vivo
  python -m edifici3d campione --uscita /tmp/campione       # campione LiDAR sintetico (prove)
  python -m edifici3d importa-modello edificio.ifc --uscita modello.geojson [--posa …]   # DXF/IFC dell'utente

Fase E (altezze di Zornade, solo nell'archivio ODbL; estratto consegnato da Zornade, mai l'API):
  python -m edifici3d zornade-altezze --file estratto.gpkg --archivio … [--confronta-con …/cc-by/er/prodotti/contesto]
  python -m edifici3d zornade-campione --uscita /tmp/zornade_campione.geojson   # estratto sintetico per le prove
  python -m edifici3d regioni [--prova] [--markdown]     # fonti per regione (fonti/regioni.toml)

`prepara` scrive, nell'archivio della licenza CC BY: corpi.pmtiles, contesto/<cella>.json, dtm_cog.tif e
terreno.pmtiles (Terrarium); `prepara-osm` fa lo stesso per l'archivio ODbL. Caddy li serve da /edifici3d/ (vedi
fase4-server/Caddyfile).
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import dtm as D, fonti as F, ortofoto_sito as O, sintetico as S, tessere as T, uvl as U

log = logging.getLogger("edifici3d")


def _corpi_uvl(righe, dtm_file: Path | None):
    corpi = []
    for prop, g in righe:
        q = D.quota(dtm_file, g) if dtm_file else None
        c = U.corpo_da(prop, g, q["minimo"] if q else None)
        if c:
            if q:
                c.extra["quota_mediana"] = round(q["mediana"], 2)
            corpi.append(c)
    return corpi


def prepara(righe, dtm_file: Path | None, uscita: Path, licenza: str, attribuzione: str, sintetico: bool = False) -> dict:
    corpi = _corpi_uvl(righe, dtm_file)
    feat = T.feature_da_corpi(corpi, S.CRS)
    if sintetico:
        for f in feat:
            f["properties"]["sintetico"] = True
    n_t = T.corpi_pmtiles(feat, uscita / "corpi.pmtiles", licenza, attribuzione)
    n_c = T.celle_contesto(feat, uscita / "contesto", licenza, attribuzione)
    import math
    xs = [x for f in feat for x, _ in f["geometry"]["coordinates"][0]]
    ys = [y for f in feat for _, y in f["geometry"]["coordinates"][0]]
    esito = {"corpi": len(corpi), "tessere_corpi": n_t, "celle": n_c, "licenza": licenza, "attribuzione": attribuzione,
             "centro": [round((min(xs) + max(xs)) / 2, 6), round((min(ys) + max(ys)) / 2, 6)],
             "riquadro": [round(min(xs), 6), round(min(ys), 6), round(max(xs), 6), round(max(ys), 6)],
             "cella": T.CELLA, "nomi_celle": sorted(p.stem for p in (uscita / "contesto").glob("*.json"))[:5000]}
    if dtm_file:
        D.a_cog(dtm_file, uscita / "dtm_cog.tif")
        esito["tessere_terreno"] = D.terrarium_pmtiles(dtm_file, uscita / "terreno.pmtiles", attribuzione=attribuzione)
    if sintetico:
        esito["sintetico"] = True
        esito["avviso"] = S.AVVISO
    (uscita / "indice.json").write_text(json.dumps(esito, ensure_ascii=False, indent=1), encoding="utf-8")
    return esito


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(prog="edifici3d", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--zona", default="emilia_romagna")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scarica"); s.add_argument("--fonte", required=True); s.add_argument("--archivio", type=Path, required=True)
    c = sub.add_parser("controlla-uvl")
    c.add_argument("--gpkg", type=Path); c.add_argument("--geojson", type=Path)
    c.add_argument("--wms-punto", nargs=2, type=float, metavar=("LAT", "LON"))
    c.add_argument("--riquadro", nargs=4, type=float)
    c.add_argument("--json", action="store_true", help="stampa anche il controllo in JSON")
    r = sub.add_parser("prepara")
    r.add_argument("--gpkg", type=Path, required=True); r.add_argument("--dtm", type=Path)
    r.add_argument("--archivio", type=Path, required=True); r.add_argument("--riquadro", nargs=4, type=float)
    d = sub.add_parser("demo"); d.add_argument("--uscita", type=Path, required=True)
    o = sub.add_parser("ortofoto-sito", help="ortofoto AGEA scaricate a mano → 50 cm, COG e PMTiles del sito")
    o.add_argument("--sito", required=True); o.add_argument("--anno", type=int, required=True)
    o.add_argument("--archivio", type=Path, required=True); o.add_argument("tessere", nargs="+", type=Path)
    li = sub.add_parser("lidar", help="pipeline notturna a tessere (Fase C)")
    li.add_argument("--zona", required=True, help="nome del TOML in zone/, percorso di un TOML o «auto»")
    li.add_argument("--archivio", type=Path, required=True); li.add_argument("--stato", type=Path, required=True)
    li.add_argument("--prodotti", type=Path, help="cartella dei prodotti (predefinita: archivio della licenza)")
    li.add_argument("--radice", type=Path, help="cartella che sostituisce {radice} negli URL (campione)")
    li.add_argument("--subito", action="store_true", help="ignora la finestra oraria")
    li.add_argument("--max-minuti", type=float); li.add_argument("--tessere", nargs="+")
    li.add_argument("--aggiorna", action="store_true", help="ricontrolla le tessere fatte (aggiornamento annuale)")
    ls = sub.add_parser("lidar-stato"); ls.add_argument("--stato", type=Path, required=True)
    lf = sub.add_parser("lidar-fonti"); lf.add_argument("--zona", default="rimini"); lf.add_argument("--prova", action="store_true")
    ca = sub.add_parser("campione", help="campione LiDAR sintetico con i prodotti della Fase A")
    ca.add_argument("--uscita", type=Path, required=True)
    im = sub.add_parser("importa-modello", help="DXF o IFC dell'utente → GeoJSON dei corpi con le falde")
    im.add_argument("file", type=Path); im.add_argument("--uscita", type=Path, required=True)
    im.add_argument("--crs", help="sistema delle coordinate del disegno se è già georeferenziato (es. EPSG:7791)")
    im.add_argument("--posa", nargs="+", metavar="X,Y=LON,LAT",
                    help="due punti noti (coordinate del disegno = lon,lat) oppure uno solo più --rotazione")
    im.add_argument("--rotazione", type=float, default=0.0, help="azimut dell'asse +Y del disegno (gradi da nord vero in senso orario), con un solo punto di posa")
    im.add_argument("--unita", type=float, help="metri per unità del disegno (predefinito: dal file, altrimenti 1)")
    im.add_argument("--edificio", default="MODELLO")
    im.add_argument("--grande", action="store_true", help="file molto grandi: fino a 500 MB, 8 GB di memoria, 30 minuti (solo sul PC)")
    za = sub.add_parser("zornade-altezze", help="estratto di Zornade → corpi e confronto nell'archivio ODbL (Fase E)")
    za.add_argument("--file", type=Path, required=True); za.add_argument("--strato")
    za.add_argument("--archivio", type=Path, required=True)
    za.add_argument("--confronta-con", type=Path, help="cartella contesto/ dei corpi CC BY della Fase A")
    za.add_argument("--mappa", nargs="+", metavar="CHIAVE=COLONNA", help="colonne con nomi diversi (es. altezza=h_lidar)")
    za.add_argument("--soglia-iou", type=float, default=0.5)
    za.add_argument("--sintetico", action="store_true", help="segna i prodotti come sintetici (campione)")
    rg = sub.add_parser("regioni", help="fonti per regione (fonti/regioni.toml): riepilogo, controllo, prova dal vivo")
    rg.add_argument("--prova", action="store_true", help="ricontrolla dal vivo gli url_prova")
    rg.add_argument("--markdown", action="store_true", help="tabella per il README")
    zc = sub.add_parser("zornade-campione", help="estratto Zornade sintetico sull'isolato di prova")
    zc.add_argument("--uscita", type=Path, required=True)
    a = p.parse_args(argv)
    if a.cmd == "regioni":
        from . import regioni as RG
        d = RG.carica()
        err = RG.controlla(d)
        if a.markdown:
            print(RG.markdown(d))
        else:
            for r in RG.riepilogo(d):
                print(f"{r['nome']:<32} edifici: {r['edifici']:<16} dtm: {r['dtm']:<16} dsm: {r['dsm']:<16} ortofoto: {r['ortofoto']}")
            print("conteggi:", RG.conteggi(d), "– verificato il", d.get("verificato"))
        if a.prova:
            for x in RG.prova(d):
                print(f"{x['regione']:<32} {x['tema']:<9} {x['stato']:<16} {x['esito']:<40} {x['nome']}")
        for e in err:
            print("ERRORE:", e)
        return 1 if err else 0
    if a.cmd in ("zornade-altezze", "zornade-campione"):
        return _zornade(a)
    if a.cmd == "lidar":
        return _lidar(a)
    if a.cmd == "lidar-stato":
        from . import pipeline as PL
        r = PL.riepilogo(a.stato)
        for z in r["zone"]:
            print(f"{z.get('nome')} ({z.get('zona')}): {z.get('conteggi')} su {z.get('totale_tessere')} tessere; "
                  f"ultima esecuzione: {(z.get('esecuzioni') or [{}])[-1].get('esito', '—')}")
        print(json.dumps(r, ensure_ascii=False, indent=1)[:4000])
        return 0
    if a.cmd == "lidar-fonti":
        return _fonti(a)
    if a.cmd == "campione":
        return _campione(a.uscita)
    if a.cmd == "importa-modello":
        from . import importa as I
        posa = I.posa_da_argomenti(a.posa, a.rotazione, a.crs)
        r = I.importa_sicuro(a.file, posa=posa, unita=a.unita, edificio=a.edificio, grande=a.grande)
        a.uscita.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({k: v for k, v in r.items() if k != "features"} | {"corpi": len(r["features"])}, ensure_ascii=False, indent=1))
        return 0
    zona = F.carica_zona(a.zona)

    if a.cmd == "scarica":
        for f in F.scarica_fonte(a.archivio, zona, a.fonte):
            print(f)
        return 0
    if a.cmd == "controlla-uvl":
        if a.gpkg:
            prop = [x for x, _ in U.leggi_gpkg(a.gpkg, riquadro=a.riquadro)]
        elif a.geojson:
            prop = U.leggi_geojson_wms(a.geojson)
        elif a.wms_punto:
            import httpx
            wms = zona["fonti"]["dbtr_uvl"]["wms"]
            prop = [f.get("properties", {}) for f in httpx.get(U.url_getfeatureinfo(wms, *a.wms_punto), timeout=60).json().get("features", [])]
        else:
            p.error("serve --gpkg, --geojson o --wms-punto")
        ctl = U.controlla(prop)
        print(U.rapporto(ctl))
        if a.json:
            print(json.dumps(ctl, ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "prepara":
        f = F.fonti(zona)["dbtr_uvl"]
        out = F.cartella(a.archivio, zona, f.licenza, "prodotti")
        esito = prepara(U.leggi_gpkg(a.gpkg, riquadro=a.riquadro), a.dtm, out, f.licenza, f.attribuzione)
        print(json.dumps(esito, ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "demo":
        esito = demo(a.uscita)
        print(json.dumps(esito, ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "ortofoto-sito":
        print(json.dumps(O.prepara(a.tessere, a.sito, a.anno, a.archivio), ensure_ascii=False, indent=1))
        return 0
    return 1


def _zornade(a) -> int:
    from . import zornade as Z
    if a.cmd == "zornade-campione":
        print(Z.campione(a.uscita))
        return 0
    zona = F.carica_zona(a.zona)
    crs = zona["zona"].get("crs", "EPSG:7791")
    mappa = dict(x.split("=", 1) for x in (a.mappa or []))
    corpi, res = Z.leggi(a.file, a.strato, crs=crs, mappa=mappa)
    confronto = None
    cambiati = []
    if a.confronta_con:
        base = Z.corpi_da_contesto(a.confronta_con, crs)
        confronto = Z.confronta(base, corpi, a.soglia_iou)
        cambiati = Z.applica_altezze(base, corpi, a.soglia_iou)
        res["corpi_base_con_altezza_zornade"] = len(cambiati)
    uscita = F.cartella(a.archivio, zona, Z.LICENZA, "prodotti") / "zornade"
    esito = Z.prepara(corpi + cambiati, uscita, res, confronto, sintetico=a.sintetico, crs=crs)
    print(json.dumps({k: v for k, v in esito.items() if k != "attribuzione_html"}, ensure_ascii=False, indent=1))
    return 0


def demo(uscita: Path, stato: Path | None = None) -> dict:
    """Demo sintetica del sito: prodotti della Fase A e, dal campione LiDAR sintetico, le falde (lidar/)."""
    import shutil
    import tempfile
    uscita = Path(uscita).resolve()
    uscita.mkdir(parents=True, exist_ok=True)
    tif = Path(uscita) / "_dtm_sintetico.tif"
    S.dtm(tif)
    esito = prepara(S.uvl(), tif, uscita, U.LICENZA, "Dati sintetici di esempio (EuGEnio)", sintetico=True)
    tif.unlink()
    (uscita / "consumi_esempio.json").write_text(json.dumps(
        {"sintetico": True, "avviso": S.AVVISO, "edificio": "E-DEMO", "unita": "Smc", "mesi": S.consumi_mensili()},
        ensure_ascii=False, indent=1), encoding="utf-8")
    from . import campione as K, pipeline as PL
    shutil.rmtree(uscita / "lidar", ignore_errors=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        K.genera(tmp)
        z = PL.carica_zona("campione")
        pl = PL.Pipeline(z, tmp / "archivio", stato or (tmp / "stato"), prodotti=uscita, radice=tmp)
        pl.z["edifici"] = {"contesto": str(uscita / "contesto")}
        esito["lidar"] = pl.esegui(subito=True)
    return esito


def _campione(uscita: Path) -> int:
    """Campione LiDAR sintetico più i prodotti della Fase A dell'isolato sintetico (uscita/prodotti)."""
    from . import campione as K
    uscita.mkdir(parents=True, exist_ok=True)
    K.genera(uscita)
    tif = uscita / "_dtm_sintetico.tif"
    S.dtm(tif)
    prepara(S.uvl(), tif, uscita / "prodotti", U.LICENZA, "Dati sintetici di esempio (EuGEnio)", sintetico=True)
    tif.unlink()
    print(f"campione scritto in {uscita}: dsm/, dtm/, las/, prodotti/ (zona di prova: zone/campione.toml, --radice {uscita})")
    return 0


def _lidar(a) -> int:
    from . import pipeline as PL
    aggiorna = a.aggiorna
    if a.zona == "auto":
        z, annuale = PL.scegli_zona(a.stato)
        if z is None:
            print("nessuna zona con fonti LiDAR attive: niente da fare (vedi `lidar-fonti`)")
            return 0
        aggiorna = aggiorna or annuale
    else:
        z = PL.carica_zona(a.zona)
    pl = PL.Pipeline(z, a.archivio, a.stato, prodotti=a.prodotti, radice=a.radice)
    esito = pl.esegui(subito=a.subito, max_minuti=a.max_minuti, solo=a.tessere, aggiorna=aggiorna)
    print(json.dumps({"zona": z["zona"]["codice"], **esito}, ensure_ascii=False, indent=1))
    return 0


def _fonti(a) -> int:
    from . import pipeline as PL
    z = PL.carica_zona(a.zona)
    for f in PL.elenco_fonti(z):
        print(f"{f['id']:<22} {f['tipo']:<4} {f['stato']:<10} {f['licenza']:<14} {f['motivo']}")
    if a.prova:   # prova dal vivo sulla tessera al centro del riquadro: copertura (quadro di unione) e risposta del server
        import httpx
        pl = PL.Pipeline(z, Path("/tmp"), Path("/tmp"))
        x0, y0, x1, y1 = z["zona"]["riquadro"]
        lato = z["zona"]["lato_tessera"]
        t = pl.griglia[(int(((x0 + x1) / 2) // lato), int(((y0 + y1) / 2) // lato))]
        print(f"prova sulla tessera {t.nome}")
        for k, f in (z.get("fonti") or {}).items():
            esito = []
            if f.get("quadro_unione"):
                try:
                    pr = pl._quadro(f["quadro_unione"], t)
                    esito.append(f"quadro di unione: {'coperta ' + str(pr.get('TAVOLA', '')) if pr else 'non coperta'}")
                except Exception as e:
                    esito.append(f"quadro di unione: errore {type(e).__name__}")
            u = (f.get("url") or "").strip()
            if u and not u.startswith("file:"):
                try:
                    r = httpx.get(pl.url(f, t).replace("size=1000,1000", "size=10,10").replace("bbox=%s,%s,%s,%s" % (t.x0, t.y0, t.x1, t.y1),
                                  "bbox=%s,%s,%s,%s" % (t.x0, t.y0, t.x0 + 20, t.y0 + 20)), timeout=40)
                    esito.append(f"HTTP {r.status_code} {r.headers.get('content-type', '')}")
                except Exception as e:
                    esito.append(f"non raggiungibile ({type(e).__name__})")
            print(f"  {k:<22} " + ("; ".join(esito) or "nessun indirizzo da provare"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
