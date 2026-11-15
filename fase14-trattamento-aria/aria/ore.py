"""Ore di funzionamento (14/11/2026): gemello Python della parte di calcolo di fase5-sito/sito/aria_ore.js.

Per un gruppo di ore (indici di psicro.filtra_gruppo / gruppi_ore.filtra) di una serie oraria T (°C) e UR (%):
- statistiche(): ore, anni della finestra, ore l'anno, quota dell'anno, T min/media/max, UR media, percentili 1/50/99 % di
  x (g/kg) e h (kJ/kg), bulbo umido massimo;
- classi_t() / classi_x() / matrice_tx(): «metodo dei bin», ore per classe di T (2 K) e di x (1 g/kg) con i valori medi
  coincidenti;
- zona(): ore dentro/fuori da una zona di comfort (rettangolo T–UR) e ore che chiedono riscaldamento, raffreddamento,
  umidificazione, deumidificazione (regole nel docstring).
Come nel browser, T, UR e i vettori x, h, twb sono in float32 (psicro.vettori arrotondato), i quantili sono quelli
lineari di psicro.quantile; l'anno medio vale 8.766 ore. Statistiche della serie, non valori di norma.
"""
from __future__ import annotations

import math

import numpy as np

from . import psicro as P

ANNO = 8766
PASSO_T = 2.0
PASSO_X = 1.0


def _vettori32(t, ur, p):
    t = np.asarray(t, dtype=np.float32)
    ur = np.asarray(ur, dtype=np.float32)
    V = P.vettori(t.astype(float), ur.astype(float), p)
    return t.astype(float), ur.astype(float), {k: np.asarray(V[k], dtype=np.float32).astype(float) for k in ("x", "h", "twb")}


def _valide(V, indici):
    sel = np.asarray(indici, dtype=np.int64)
    return sel[np.isfinite(V["x"][sel])]


def statistiche(t, ur, p, indici, i0=0, n=None) -> dict:
    t, ur, V = _vettori32(t, ur, p)
    n = len(t) if n is None else n
    sel = _valide(V, indici)
    k = len(sel)
    periodo = max(0, n - i0)
    anni = periodo / ANNO
    nan = math.nan

    def q(v, f):
        return P.quantile(np.sort(V[v][sel].astype(np.float32)), f) if k else nan
    return {
        "ore": k, "anni": anni, "oreAnno": k / anni if anni > 0 else nan, "quota": k / periodo * 100 if periodo else nan,
        "tMin": float(t[sel].min()) if k else nan, "tMedia": float(t[sel].mean()) if k else nan,
        "tMax": float(t[sel].max()) if k else nan, "urMedia": float(ur[sel].mean()) if k else nan,
        "x01": q("x", 0.01) * 1000, "x50": q("x", 0.5) * 1000, "x99": q("x", 0.99) * 1000,
        "h01": q("h", 0.01), "h50": q("h", 0.5), "h99": q("h", 0.99),
        "twbMax": float(V["twb"][sel].max()) if k else nan,
    }


def _classi(chiave, valori_medi, passo):
    """chiave: classe intera per ora; valori_medi: {nome: array}; → righe da/a/ore/medie (classi vuote comprese)."""
    if not len(chiave):
        return []
    k0, k1 = int(chiave.min()), int(chiave.max())
    L = k1 - k0 + 1
    c = chiave - k0
    ore = np.bincount(c, minlength=L).astype(float)
    somme = {nome: np.bincount(c, weights=v, minlength=L) for nome, v in valori_medi.items()}
    out = []
    for j in range(L):
        o = ore[j]
        r = {"da": (j + k0) * passo, "a": (j + k0 + 1) * passo, "ore": o}
        for nome, s in somme.items():
            r[nome] = s[j] / o if o else math.nan
        out.append(r)
    return out


def classi_t(t, ur, p, indici, passo=PASSO_T) -> list[dict]:
    t, ur, V = _vettori32(t, ur, p)
    sel = _valide(V, indici)
    chiave = np.floor(t[sel] / passo).astype(np.int64)
    return _classi(chiave, {"ur": ur[sel], "x": V["x"][sel] * 1000, "h": V["h"][sel], "twb": V["twb"][sel]}, passo)


def classi_x(t, ur, p, indici, passo=PASSO_X) -> list[dict]:
    t, ur, V = _vettori32(t, ur, p)
    sel = _valide(V, indici)
    chiave = np.floor(V["x"][sel] * 1000 / passo).astype(np.int64)
    return _classi(chiave, {"t": t[sel], "ur": ur[sel], "h": V["h"][sel]}, passo)


def matrice_tx(t, ur, p, indici, passo_t=PASSO_T, passo_x=PASSO_X) -> dict:
    t, ur, V = _vettori32(t, ur, p)
    sel = _valide(V, indici)
    if not len(sel):
        return {"t": [], "x": [], "ore": []}
    kt = np.floor(t[sel] / passo_t).astype(np.int64)
    kx = np.floor(V["x"][sel] * 1000 / passo_x).astype(np.int64)
    a, c = int(kt.min()), int(kx.min())
    M = np.zeros((int(kt.max()) - a + 1, int(kx.max()) - c + 1), dtype=int)
    np.add.at(M, (kt - a, kx - c), 1)
    return {"t": [(a + i) * passo_t for i in range(M.shape[0])], "x": [(c + i) * passo_x for i in range(M.shape[1])], "ore": M.tolist()}


def zona(t, ur, p, indici, t_min, t_max, ur_min, ur_max) -> dict:
    """Zona di comfort T–UR (limiti compresi). Ora per ora: T < t_min → riscaldamento, T > t_max → raffreddamento
    (sensibile, a x costante, fino al limite più vicino Tc); UR a Tc = UR·psat(T)/psat(Tc) (UR al massimo 100):
    < ur_min → umidificazione, > ur_max → deumidificazione; «nella zona» = nessuno dei quattro."""
    t, ur, V = _vettori32(t, ur, p)
    sel = _valide(V, indici)
    T, U = t[sel], np.minimum(ur[sel], 100.0)
    risc, raff = T < t_min, T > t_max
    tc = np.where(risc, float(t_min), np.where(raff, float(t_max), T))
    uc = np.where(risc | raff, U * np.exp(P._ln_psat_v(T) - P._ln_psat_v(tc)), U)
    umid, deum = uc < ur_min, uc > ur_max
    dentro = ~(risc | raff | umid | deum)
    return {"ore": int(len(sel)), "dentro": int(dentro.sum()), "fuori": int(len(sel) - dentro.sum()), "riscaldare": int(risc.sum()),
            "raffreddare": int(raff.sum()), "umidificare": int(umid.sum()), "deumidificare": int(deum.sum())}
