"""Toscana – Edificato multiscala, unità volumetriche (gruppo B dei lettori regionali, 08/11/2026).

Fonte: Regione Toscana, WFS MapServer `owsedificato`, strato `ms:rt_edif.unitavolumetriche` (GML 3.1.1, EPSG:3003,
CC BY 4.0), o lo zip regionale SpatiaLite con gli stessi campi. Scaricamento del comune: `python -m edifici3d.b_regioni
toscana-wfs --istat <codice>`.

Campi (verificati dal vivo l'08/11/2026 su Firenze):
- `uv_av` altezza del volume (m), `uv_qe` quota di estrusione (m s.l.m., sommità), `uv_qs` quota al suolo (m s.l.m.):
  `uv_qe − uv_av = uv_qs` al centimetro nelle porzioni «01 Al Suolo»; nelle altre (es. «05 Soffitto di loggia») la base
  sta sopra il terreno (soffitto del vuoto sotto il volume);
- `uv_id` identificativo del volume, `edifc_id` (o `edi_min_id` per gli edifici minori) edificio di appartenenza;
- `edifc_dty` tipologia, `edifc_duso` uso, `edifc_dstat` stato, `edifc_dsot` sotterraneo, `edi_min_dty` tipo di edificio
  minore, `dtvolo` data del volo, `scala` (02 = 1:2.000, 10 = 1:10.000).

Regole: si scartano i volumi sotterranei, i ruderi e i demoliti (gli «In Disuso/diruto» restano: sono in piedi;
le porzioni «Seminterrata» contano come al suolo). Gronda = `uv_av` (alla sommità del volume: «gronda o
colmo da verificare» come per le UVL dell'ER e il DBGT lombardo). Quota del terreno = DTM se c'è, altrimenti `uv_qs`.
Nelle porzioni sopraelevate, col DTM la gronda va dal terreno alla sommità (`uv_qe − DTM`: il vuoto sotto il volume si
riempie, come in un prisma), senza DTM resta `uv_av` dalla quota `uv_qs` (segnato in `extra`).
"""
from __future__ import annotations

from ..regionali import Adattatore, Corpo, numero

_SCARTA_STATO = ("rudere", "demolit", "distrutt")    # «In Disuso/diruto» resta: edifici in piedi non usati
_USI = (("resid", "residenziale"), ("sanit", "ospedale"), ("ospedal", "ospedale"), ("istruz", "scuola"), ("scuol", "scuola"),
        ("scolast", "scuola"), ("univers", "scuola"), ("industr", "capannone"), ("artigian", "capannone"),
        ("commerc", "commerciale"), ("amministr", "uffici"), ("uffic", "uffici"), ("sport", "palestra"))
RESIDENZIALE_MAX = 80.0          # m: oltre, un volume «Residenziale» è un errore di quota (verifica 08/11/2026)
_SCALE = {"02": "CTR 1:2.000", "05": "CTR 1:5.000", "10": "CTR 1:10.000"}


def _testo(v) -> str:
    return "" if v is None else str(v).strip()


def uso_toscana(testo: str) -> str | None:
    t = testo.lower()
    for k, u in _USI:
        if k in t:
            return u
    return None


def _corpo_toscana(p: dict, g, z: float | None, quota_dtm: float | None) -> Corpo | None:
    sot = _testo(p.get("edifc_dsot")).lower()
    if "sotterran" in sot and "non" not in sot:
        return None
    stato = (_testo(p.get("edifc_dstat")) + " " + _testo(p.get("edi_min_dst"))).lower()
    if any(s in stato for s in _SCARTA_STATO):
        return None
    por = _testo(p.get("uv_por"))
    dpor = _testo(p.get("uv_dpor"))
    if "sotterran" in dpor.lower():
        return None
    h, qe, qs = numero(p.get("uv_av")), numero(p.get("uv_qe")), numero(p.get("uv_qs"))
    if (h is None or h <= 0) and qe is not None and qs is not None:
        h = qe - qs
    if h is None or h <= 0 or g.area < 1:
        return None
    al_suolo = por in ("", "01", "-") or dpor.lower().startswith(("al suolo", "seminterr"))
    terreno = quota_dtm if quota_dtm is not None else qs
    gronda = h
    fonte_h = "Edificato multiscala Toscana uv_av (gronda o colmo da verificare)"
    extra = {"porzione": dpor or por, "quota_estrusione": qe, "quota_suolo": qs, "regione": "Toscana"}
    if not al_suolo:
        if quota_dtm is not None and qe is not None and qe - quota_dtm > h:
            gronda = round(qe - quota_dtm, 2)
            fonte_h = f"Edificato multiscala Toscana: uv_qe {qe:.1f} m − DTM {quota_dtm:.1f} m (porzione sopraelevata)"
        else:
            extra["base_sopraelevata"] = True
    elif quota_dtm is not None and qs is not None:
        fonte_h += f"; suolo DB {qs:.1f} m, DTM {quota_dtm:.1f} m"
    uso_testo = _testo(p.get("edifc_duso"))
    if gronda > 400 or (gronda > RESIDENZIALE_MAX and uso_toscana(uso_testo) == "residenziale"):
        return None                  # errori del dato: a Firenze 6 volumi residenziali con uv_qe 321,2 m (h 183–198 m)
    tipo = _testo(p.get("edifc_dty"))
    minore = _testo(p.get("edi_min_dty"))
    edificio = _testo(p.get("edifc_id")) or _testo(p.get("edi_min_id")) or _testo(p.get("uv_id")) or _testo(p.get("uv_pk"))
    for k, v in (("tipo", tipo), ("uso_ctr", uso_testo), ("edificio_minore", minore), ("volo", _testo(p.get("dtvolo"))),
                 ("scala", _testo(p.get("scala")))):
        if v and v != "-":
            extra[k] = v
    scala = _SCALE.get(_testo(p.get("scala")), "CTR")
    return Corpo(id=_testo(p.get("uv_id")) or _testo(p.get("uv_pk")), edificio=edificio, sagoma=g, quota_terreno=terreno,
                 gronda=float(gronda), tetto="piano", fonte_sagoma=TOSCANA.fonte, licenza=TOSCANA.licenza,
                 fonte_altezza=fonte_h, qualita=f"{scala}, altezza ±1–2 m", uso=uso_toscana(uso_testo), extra=extra)


TOSCANA = Adattatore("toscana_uv", "Regione Toscana – Edificato multiscala, unità volumetriche", "CC BY 4.0",
                     "Regione Toscana – Edificato multiscala, unità volumetriche (CC BY 4.0)", "EPSG:3003",
                     ("uv_id", "edifc_id", "uv_av", "uv_qe", "uv_qs", "uv_por", "edifc_duso"), False, _corpo_toscana)


def coerenza(righe) -> str:
    """`uv_qe − uv_av = uv_qs` nelle porzioni al suolo (per il controllo degli attributi)."""
    n = ok = 0
    for p, _ in righe:
        h, qe, qs = numero(p.get("uv_av")), numero(p.get("uv_qe")), numero(p.get("uv_qs"))
        if None in (h, qe, qs):
            continue
        n += 1
        ok += abs(qe - h - qs) < 0.05
    return f"uv_qe − uv_av = uv_qs in {ok} su {n} (le altre: porzioni con la base sopraelevata)"


TOSCANA.coerenza = coerenza          # usata da regionali.controlla (proposta comune dei gruppi A e B)

ADATTATORI = (TOSCANA,)
