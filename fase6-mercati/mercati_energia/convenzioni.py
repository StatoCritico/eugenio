"""Convenzioni di fornitura di energia elettrica e gas delle centrali di committenza regionali
(Intercent-ER, Consorzio Energia Toscana, Consip, Aria, SCR Piemonte, ...).

Ogni convenzione è un file TOML (vedi convenzioni/modelli). Una convenzione ha uno o più lotti;
ogni lotto ha una regola di prezzo dell'energia e, se previsti, corrispettivi fissi e di potenza.

Regole di prezzo dell'energia (per fascia F0/F1/F2/F3/F23):
  indice_piu_spread       P = coefficiente × I(mese) + spread
  base_piu_delta_indice   P = P0 + k × (I(mese) − I_riferimento)       (indicizzazioni "vecchio stile")
  fisso                   P = P0
  prezzi_pubblicati       P letto da un CSV pubblicato dalla centrale (mese;fascia;prezzo)
Per il gas l'indice in €/MWh è convertito in €/Smc con il PCS (GJ/Smc, standard 0,03852).

Il calcolo riguarda la componente energia (più perdite e corrispettivi della convenzione): non
include trasporto, oneri di sistema, accise e IVA, che dipendono da ARERA e dal punto di fornitura.
Valori segnaposto "DA_COMPILARE" bloccano il calcolo con un elenco dei campi mancanti.
"""
from __future__ import annotations

import datetime as dt
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

SEGNAPOSTO = "DA_COMPILARE"
FASCE_VALIDE = {"F0", "F1", "F2", "F3", "F23"}
INDICE_PER_FASCIA_PUN = {"F0": "PUN_MENSILE", "F1": "PUN_F1", "F2": "PUN_F2", "F3": "PUN_F3", "F23": "PUN_F23"}


@dataclass
class Lotto:
    id: str
    descrizione: str
    regola: str
    fasce: list[str]
    indice: dict[str, str] = field(default_factory=dict)          # fascia → nome indice
    indice_alternativo: dict[str, str] = field(default_factory=dict)
    spread: dict[str, float] = field(default_factory=dict)
    p0: dict[str, float] = field(default_factory=dict)
    coefficiente: float = 1.0
    k: float = 1.0
    indice_riferimento: float | None = None
    perdite: float = 0.0
    pcs_gj_smc: float | None = None
    file_prezzi: Path | None = None
    corrispettivi: dict = field(default_factory=dict)
    ambito: dict = field(default_factory=dict)


@dataclass
class Convenzione:
    id: str
    ente: str
    titolo: str
    regione: str
    commodity: str
    dal: dt.date
    al: dt.date
    unita_prezzo: str
    fonte: str
    lotti: list[Lotto]
    file: Path | None = None

    def lotto(self, id_lotto: str) -> Lotto:
        for l in self.lotti:
            if l.id == id_lotto:
                return l
        raise KeyError(f"Lotto {id_lotto} non presente in {self.id}")


def _per_fascia(v, fasce) -> dict:
    if v is None:
        return {}
    if isinstance(v, dict):
        return {k.upper(): x for k, x in v.items()}
    return {f: v for f in fasce}


def carica(file: Path) -> Convenzione:
    file = Path(file)
    raw = tomllib.loads(file.read_text(encoding="utf-8"))
    c = raw["convenzione"]
    lotti = []
    for l in raw.get("lotto", []):
        fasce = [f.upper() for f in l.get("fasce", ["F0"])]
        if not set(fasce) <= FASCE_VALIDE:
            raise ValueError(f"{file.name} lotto {l.get('id')}: fasce non valide {fasce}")
        indice = l.get("indice")
        if indice == "PUN_FASCE":
            indice = {f: INDICE_PER_FASCIA_PUN[f] for f in fasce}
        lotti.append(Lotto(
            id=str(l["id"]), descrizione=l.get("descrizione", ""), regola=l["regola_prezzo"], fasce=fasce,
            indice=_per_fascia(indice, fasce), indice_alternativo=_per_fascia(l.get("indice_alternativo"), fasce),
            spread=_per_fascia(l.get("spread"), fasce), p0=_per_fascia(l.get("p0"), fasce),
            coefficiente=l.get("coefficiente", 1.0), k=l.get("k", 1.0),
            indice_riferimento=l.get("indice_riferimento"), perdite=l.get("perdite", 0.0),
            pcs_gj_smc=l.get("pcs_gj_smc", 0.03852 if c.get("commodity") == "gas" else None),
            file_prezzi=(file.parent / l["file_prezzi"]) if l.get("file_prezzi") else None,
            corrispettivi=l.get("corrispettivi", {}), ambito=l.get("ambito", {})))
    conv = Convenzione(id=c["id"], ente=c["ente"], titolo=c.get("titolo", ""), regione=str(c.get("regione", "")),
                       commodity=c["commodity"], dal=c["dal"], al=c["al"],
                       unita_prezzo=c.get("unita_prezzo", "EUR/MWh" if c["commodity"] != "gas" else "EUR/Smc"),
                       fonte=c.get("fonte", ""), lotti=lotti, file=file)
    return conv


def da_compilare(conv: Convenzione) -> list[str]:
    """Campi ancora segnaposto (il calcolo li rifiuta)."""
    out = []
    for l in conv.lotti:
        for nome in ("spread", "p0", "corrispettivi"):
            for k, v in getattr(l, nome).items():
                if v == SEGNAPOSTO:
                    out.append(f"lotto {l.id}: {nome}.{k}")
        if l.indice_riferimento == SEGNAPOSTO:
            out.append(f"lotto {l.id}: indice_riferimento")
    return out


def carica_tutte(cartella: Path) -> list[Convenzione]:
    return [carica(f) for f in sorted(Path(cartella).glob("*.toml"))]


# ---------------------------------------------------------------------------------------------- calcolo
def _valore_indice(indici: pd.DataFrame, nome: str, mese: str):
    s = indici[(indici.indice == nome) & (indici.mese == mese)]
    return None if s.empty else float(s.valore.iloc[0])


def prezzi(conv: Convenzione, id_lotto: str, mesi: list[str], indici: pd.DataFrame) -> pd.DataFrame:
    """Prezzo unitario dell'energia per mese e fascia, nell'unità della convenzione."""
    mancanti = da_compilare(conv)
    if mancanti:
        raise ValueError(f"Convenzione {conv.id}: valori da compilare – {'; '.join(mancanti)}")
    l = conv.lotto(id_lotto)
    pub = None
    if l.regola == "prezzi_pubblicati":
        pub = pd.read_csv(l.file_prezzi, sep=None, engine="python", dtype=str)
        pub.columns = [c.strip().lower() for c in pub.columns]
        pub["prezzo"] = pd.to_numeric(pub.prezzo.str.replace(",", ".", regex=False), errors="coerce")
        pub["mese"] = pd.to_datetime(pub.mese).dt.to_period("M").astype(str)
        pub["fascia"] = pub.fascia.str.upper()
    righe = []
    for mese in mesi:
        primo = pd.Timestamp(mese + "-01").date()
        fuori = not (conv.dal.replace(day=1) <= primo <= conv.al)
        for f in l.fasce:
            note, iv = [], None
            if l.regola == "prezzi_pubblicati":
                s = pub[(pub.mese == mese) & (pub.fascia == f)]
                p = float(s.prezzo.iloc[0]) if len(s) else None
                if p is None:
                    note.append("prezzo non pubblicato")
            elif l.regola == "fisso":
                p = float(l.p0[f])
            else:
                nome = l.indice.get(f)
                iv = _valore_indice(indici, nome, mese) if nome else None
                if iv is None and l.indice_alternativo.get(f):
                    iv = _valore_indice(indici, l.indice_alternativo[f], mese)
                    if iv is not None:
                        note.append(f"stima con {l.indice_alternativo[f]} al posto di {nome}")
                if iv is None:
                    p = None
                    note.append(f"indice {nome} non disponibile")
                else:
                    if conv.commodity == "gas" and l.pcs_gj_smc:
                        iv_u = iv * l.pcs_gj_smc / 3.6           # €/MWh → €/Smc
                    elif conv.unita_prezzo.lower().startswith("c"):
                        iv_u = iv / 10.0                          # €/MWh → c€/kWh
                    else:
                        iv_u = iv
                    if l.regola == "indice_piu_spread":
                        p = l.coefficiente * iv_u + float(l.spread[f])
                    elif l.regola == "base_piu_delta_indice":
                        p = float(l.p0[f]) + l.k * (iv_u - float(l.indice_riferimento))
                    else:
                        raise ValueError(f"Regola di prezzo sconosciuta: {l.regola}")
            if fuori:
                note.append("mese fuori dal periodo della convenzione")
            righe.append({"convenzione": conv.id, "lotto": l.id, "mese": mese, "fascia": f, "indice": iv,
                          "prezzo": None if p is None else round(p, 6),
                          "prezzo_con_perdite": None if p is None else round(p * (1 + l.perdite), 6),
                          "unita": conv.unita_prezzo, "note": "; ".join(note)})
    return pd.DataFrame(righe)


def costo(conv: Convenzione, id_lotto: str, consumi: pd.DataFrame, indici: pd.DataFrame,
          n_pod: int = 1, potenza_kw: float | None = None) -> pd.DataFrame:
    """consumi: colonne mese (AAAA-MM), fascia, quantita (MWh per l'elettricità – o kWh/1000 –, Smc per il gas).
    Restituisce per mese: energia, corrispettivo fisso, potenza e totale (senza rete, oneri e imposte)."""
    l = conv.lotto(id_lotto)
    c = consumi.copy()
    c["fascia"] = c.fascia.str.upper()
    if set(c.fascia) - set(l.fasce):
        if l.fasce == ["F0"]:
            c = c.groupby("mese", as_index=False).quantita.sum().assign(fascia="F0")
        elif "F23" in l.fasce:
            c["fascia"] = c.fascia.replace({"F2": "F23", "F3": "F23"})
            c = c.groupby(["mese", "fascia"], as_index=False).quantita.sum()
        else:
            raise ValueError(f"I consumi hanno fasce {sorted(set(c.fascia))}, il lotto prevede {l.fasce}")
    pr = prezzi(conv, id_lotto, sorted(c.mese.unique()), indici)
    m = c.merge(pr, on=["mese", "fascia"], how="left")
    fattore = 10.0 if conv.unita_prezzo.lower().startswith("c") else 1.0   # c€/kWh × MWh → €
    m["euro_energia"] = m.prezzo_con_perdite * m.quantita * fattore
    out = m.groupby("mese", as_index=False).agg(quantita=("quantita", "sum"), euro_energia=("euro_energia", "sum"),
                                                note=("note", lambda x: "; ".join(sorted({n for n in x if n}))))
    fisso = l.corrispettivi.get("fisso_pod_anno") or 0.0
    pot = l.corrispettivi.get("potenza_kw_mese") or 0.0
    out["euro_fisso"] = float(fisso) * n_pod / 12.0
    out["euro_potenza"] = float(pot) * (potenza_kw or 0.0)
    out["euro_totale"] = out[["euro_energia", "euro_fisso", "euro_potenza"]].sum(axis=1, min_count=1)
    out.insert(0, "lotto", l.id)
    out.insert(0, "convenzione", conv.id)
    return out
