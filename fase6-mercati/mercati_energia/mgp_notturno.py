"""Lavoro notturno `mercato-mgp` (20/11/2026): mercato del giorno prima del GME. SOLO USO INTERNO (vedi mgp.py).

Sul server: `python -m servizio.worker mercato-mgp` (fase 4, ogni notte alle ORA_MERCATO_MGP, 04:15), oppure
`python -m mercati_energia -c /dati/mercati/config.toml mgp`. Gira dopo il lavoro `mercati` (02:30, prezzi e volumi),
con lo stesso limitatore delle chiamate dell'API (ClientGME rilegge all'avvio le connessioni già usate nell'ora).

Ogni notte, per al massimo `[mgp].max_minuti` minuti:
  1. serie piccole (liquidità, transiti, fabbisogno; archivio annuale, aggiornato per chiave): dall'ultimo giorno in
     archivio meno `giorni_riverifica` fino a domani; poi lo storico all'indietro a blocchi (7 giorni a 15 minuti, 31
     orari) fino a `inizio_serie` (o a quando il GME smette di rispondere per sei blocchi di fila);
  2. curve aggregate di domanda e offerta (un file al giorno): i giorni mancanti fino a oggi, poi
     `domanda_offerta_giorni_per_notte` giorni all'indietro fino a `domanda_offerta_inizio`; ne derivano offerta e
     domanda totali per zona e periodo (archivio annuale);
  3. offerte pubbliche (un file al giorno, il GME le pubblica dopo 7 giorni): i giorni mancanti fino a oggi −
     `offerte_ritardo_giorni`, poi `offerte_giorni_per_notte` giorni all'indietro fino a `offerte_inizio`, con
     `pausa_s` secondi fra una richiesta e l'altra. Lo storico si ferma se l'archivio delle offerte supera
     `offerte_max_gb` o se sul disco restano meno di `spazio_minimo_gb`.
Un giorno che fallisce (rete, quote) si ritenta le notti dopo, al massimo 3 volte; poi resta in `mgp_stato.json`
fra i `non_scaricati`. Tutto quello che il lavoro scrive sta nella cartella dell'archivio (cfg.cartella):
dataset, mgp_stato.json, mgp_ultima_esecuzione.json.

Email (il worker le manda solo se `da_segnalare` non è vuoto), una volta per episodio:
  - credenziali GME rifiutate (la password scade ogni 6 mesi);
  - una fonte senza dati nuovi da più di `giorni_ferma` giorni (oltre il ritardo normale di pubblicazione);
  - spazio su disco sotto `spazio_minimo_gb`;
  - il lavoro intero fallito per 3 notti di fila.
Credenziali non configurate: il lavoro non fa nulla e non scrive email (è una configurazione, non un guasto).
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import shutil
import time
import traceback
import zipfile
from pathlib import Path
from xml.etree.ElementTree import ParseError

import pandas as pd

from . import archivio, gme, mgp
from .config import Config

log = logging.getLogger(__name__)
SOGLIA_15MIN = mgp.SOGLIA_15MIN
MAX_TENTATIVI = 3
VUOTI_FINE_SERIE = 6

# sostituibili nei test
_adesso = time.time
_dormi = time.sleep


def _oggi() -> dt.date:
    return dt.datetime.fromtimestamp(_adesso(), gme.ROMA).date()


# ---------------------------------------------------------------------------------------------- stato
def _leggi_stato(cartella: Path) -> dict:
    p = cartella / "mgp_stato.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _scrivi_json(p: Path, d: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    tmp.replace(p)


def _avviso(stato: dict, esito: dict, chiave: str, attivo: bool, testo: str) -> None:
    """Un'email per episodio: si segnala quando la condizione compare, si azzera quando sparisce."""
    avvisi = stato.setdefault("avvisi", {})
    if attivo and not avvisi.get(chiave):
        esito["da_segnalare"].append(testo)
        avvisi[chiave] = _oggi().isoformat()
    elif not attivo and chiave in avvisi:
        del avvisi[chiave]


# ---------------------------------------------------------------------------------------------- blocchi
def _passo(giorno: dt.date) -> int:
    return 7 if giorno >= SOGLIA_15MIN else 31


def _blocchi_avanti(dal: dt.date, al: dt.date):
    a = dal
    while a <= al:
        b = min(al, a + dt.timedelta(days=_passo(a) - 1))
        if a < SOGLIA_15MIN <= b:            # i blocchi non attraversano il passaggio ai 15 minuti
            b = SOGLIA_15MIN - dt.timedelta(days=1)
        yield a, b
        a = b + dt.timedelta(days=1)


def _blocchi_indietro(dal: dt.date, al: dt.date):
    b = al
    while b >= dal:
        a = max(dal, b - dt.timedelta(days=_passo(b) - 1))
        if a < SOGLIA_15MIN <= b:
            a = SOGLIA_15MIN
        yield a, b
        b = a - dt.timedelta(days=1)


class _Tempo:
    def __init__(self, minuti: float):
        self.fine = _adesso() + minuti * 60

    def finito(self) -> bool:
        return _adesso() >= self.fine


# ---------------------------------------------------------------------------------------------- serie piccole
def _serie_piccola(cfg: Config, cl, nome: str, stato: dict, tempo: _Tempo, oggi: dt.date) -> int:
    cart, m = cfg.cartella, cfg.mgp
    s = stato.setdefault(nome, {})
    inizio = m.inizio_serie or cfg.gme.inizio_orario or cfg.gme.inizio_quartorario
    domani = oggi + dt.timedelta(days=1)
    k = mgp.chiavi(nome)
    n = 0
    ultimo = archivio.ultima_data(cart, nome, "data")
    dal = (ultimo - dt.timedelta(days=m.giorni_riverifica)) if ultimo else domani - dt.timedelta(days=30)
    for a, b in _blocchi_avanti(max(dal, inizio), domani):
        n += archivio.aggiorna(cart, nome, mgp.scarica_serie(cl, nome, a, b), k, "data")
    if s.get("completo"):
        return n
    primo = archivio.prima_data(cart, nome, "data") or domani
    limite = dt.date.fromisoformat(s["inizia_il"]) if s.get("inizia_il") else inizio
    vuoti, fine_vuoto = 0, None
    if primo <= limite:
        s["completo"] = True
        return n
    for a, b in _blocchi_indietro(limite, primo - dt.timedelta(days=1)):
        if tempo.finito():
            return n
        df = mgp.scarica_serie(cl, nome, a, b)
        if df.empty:
            vuoti += 1
            fine_vuoto = fine_vuoto or b
            if vuoti >= VUOTI_FINE_SERIE:          # la serie comincia dopo il primo blocco vuoto
                s["inizia_il"], s["completo"] = str(fine_vuoto + dt.timedelta(days=1)), True
                return n
        else:
            vuoti, fine_vuoto = 0, None
            n += archivio.aggiorna(cart, nome, df, k, "data")
        s["raggiunto"] = str(a)
    s["completo"] = True
    return n


# ---------------------------------------------------------------------------------------------- dataset giornalieri
def _spazio_ok(cfg: Config, esito: dict, stato: dict) -> bool:
    libero = shutil.disk_usage(cfg.cartella).free
    basso = libero < cfg.mgp.spazio_minimo_gb * 1e9
    _avviso(stato, esito, "spazio", basso,
            f"Spazio su disco quasi finito: {libero / 1e9:.1f} GB liberi nella cartella dei mercati (soglia "
            f"{cfg.mgp.spazio_minimo_gb:g} GB). Il recupero dello storico MGP è fermo; i giorni nuovi continuano.")
    return not basso


def _giornaliero(cfg: Config, nome: str, scarica, ultimo_disponibile: dt.date, inizio: dt.date, per_notte: int,
                 stato: dict, esito: dict, tempo: _Tempo, dopo=None, limite_byte: float | None = None) -> int:
    """Dataset con un file per giorno: giorni mancanti fino a `ultimo_disponibile`, giorni falliti da ritentare, poi
    `per_notte` giorni all'indietro fino a `inizio`. `dopo(giorno, df)` riceve ogni giorno scaricato."""
    cart, m = cfg.cartella, cfg.mgp
    s = stato.setdefault(nome, {})
    falliti: dict = s.setdefault("falliti", {})
    presenti = set(archivio.giorni(cart, nome))
    tentati: set[dt.date] = set()
    n_righe = 0
    richieste = 0

    def prova(g: dt.date) -> str:
        """'ok', 'vuoto' o 'errore'."""
        nonlocal n_righe, richieste
        tentati.add(g)
        if richieste:
            _dormi(m.pausa_s)
        richieste += 1
        try:
            df = scarica(g)
        except gme.CredenzialiGME:
            raise
        except (gme.ErroreGME, OSError, ValueError, ParseError, zipfile.BadZipFile) as e:
            falliti[str(g)] = falliti.get(str(g), 0) + 1
            log.warning("MGP %s %s: %s", nome, g, e)
            esito["errori"].append(f"{nome} {g}: {type(e).__name__}: {e}")
            return "errore"
        falliti.pop(str(g), None)
        if df is None or df.empty:
            return "vuoto"
        n_righe += archivio.scrivi_giorno(cart, nome, g, df)
        presenti.add(g)
        if dopo:
            dopo(g, df)
        return "ok"

    # 1. giorni recenti mancanti (al massimo 14 a notte: dopo una lunga pausa si recupera in più notti)
    ultimo = max(presenti) if presenti else None
    dal = (ultimo + dt.timedelta(days=1)) if ultimo else ultimo_disponibile
    recenti = [dal + dt.timedelta(days=i) for i in range((ultimo_disponibile - dal).days + 1)][:14]
    for g in recenti:
        if tempo.finito():
            break
        prova(g)
    # 2. giorni falliti nelle notti precedenti
    for g_txt, volte in sorted(falliti.items()):
        if volte >= MAX_TENTATIVI or tempo.finito():
            continue
        g = dt.date.fromisoformat(g_txt)
        if g not in presenti and g not in tentati:
            prova(g)
    s["non_scaricati"] = sorted(g for g, v in falliti.items() if v >= MAX_TENTATIVI)
    # 3. storico all'indietro, dal giorno più vecchio raggiunto (scaricato o trovato vuoto)
    if not s.get("completo"):
        limite = dt.date.fromisoformat(s["inizia_il"]) if s.get("inizia_il") else inizio
        partenza = [min(presenti)] if presenti else [ultimo_disponibile + dt.timedelta(days=1)]
        if s.get("raggiunto"):
            partenza.append(dt.date.fromisoformat(s["raggiunto"]))
        g = min(partenza) - dt.timedelta(days=1)
        fatti, vuoti = 0, s.get("vuoti_di_fila", 0)
        while g >= limite and fatti < per_notte and not tempo.finito():
            if not _spazio_ok(cfg, esito, stato):
                break
            if limite_byte and archivio.dimensione(cart, nome) > limite_byte:
                s["fermo_per_spazio"] = True
                log.info("MGP %s: archivio oltre %.0f GB, storico fermo", nome, limite_byte / 1e9)
                break
            if g in tentati or falliti.get(str(g), 0) >= MAX_TENTATIVI:
                g -= dt.timedelta(days=1)
                continue
            r = prova(g)
            fatti += 1
            if r == "vuoto":
                vuoti += 1
                if vuoti >= VUOTI_FINE_SERIE:
                    s["inizia_il"], s["completo"] = str(g + dt.timedelta(days=vuoti)), True
                    break
            elif r == "ok":
                vuoti = 0
            if r != "errore":
                s["raggiunto"] = str(g)
            g -= dt.timedelta(days=1)
        else:
            if g < limite:
                s["completo"] = True
        s["vuoti_di_fila"] = vuoti
    s["primo_giorno"] = str(min(presenti)) if presenti else None
    s["ultimo_giorno"] = str(max(presenti)) if presenti else None
    s["byte"] = archivio.dimensione(cart, nome)
    return n_righe


# ---------------------------------------------------------------------------------------------- fonti ferme
def _controlla_ferme(cfg: Config, stato: dict, esito: dict, oggi: dt.date) -> None:
    m = cfg.mgp
    attese = {}
    for nome in mgp.SERIE:
        attese[nome] = (archivio.ultima_data(cfg.cartella, nome, "data"), oggi)
    if m.domanda_offerta:
        g = archivio.giorni(cfg.cartella, "mgp_domanda_offerta")
        attese["mgp_domanda_offerta"] = (g[-1] if g else None, oggi)
    if m.offerte:
        g = archivio.giorni(cfg.cartella, "mgp_offerte")
        attese["mgp_offerte"] = (g[-1] if g else None, oggi - dt.timedelta(days=m.offerte_ritardo_giorni))
    prima = dt.date.fromisoformat(stato.setdefault("prima_esecuzione", oggi.isoformat()))
    for nome, (ultimo, atteso) in attese.items():
        if ultimo is None:
            ferma = (oggi - prima).days > m.giorni_ferma
            ritardo = f"nessun dato in archivio dopo {(oggi - prima).days} giorni"
        else:
            ferma = (atteso - ultimo).days > m.giorni_ferma
            ritardo = f"ultimo giorno in archivio {ultimo}, atteso {atteso}"
        _avviso(stato, esito, f"ferma_{nome}", ferma,
                f"GME, mercato del giorno prima: la serie {nome} non riceve dati nuovi ({ritardo}).")


# ---------------------------------------------------------------------------------------------- lavoro
def esegui(cfg: Config, client=None) -> dict:
    """Un giro del lavoro `mercato-mgp`. Restituisce l'esito; `da_segnalare` elenca i soli motivi per un'email."""
    t0 = _adesso()
    cart, m = cfg.cartella, cfg.mgp
    oggi = _oggi()
    esito = {"inizio": dt.datetime.fromtimestamp(t0, gme.ROMA).isoformat(timespec="seconds"), "righe": {},
             "errori": [], "da_segnalare": []}
    if not (cfg.gme.abilitato and m.abilitato):
        esito["saltato"] = "disattivato in configurazione"
        return esito
    try:
        cl = client or gme.ClientGME(cfg.gme.utente, cfg.gme.password())
    except gme.ErroreGME as e:                  # credenziali non inserite: nessun file, nessuna email
        log.info("MGP: %s", e)
        esito["saltato"] = str(e)
        return esito
    cart.mkdir(parents=True, exist_ok=True)
    stato = _leggi_stato(cart)
    tempo = _Tempo(m.max_minuti)
    try:
        try:
            for nome in mgp.SERIE:
                try:
                    esito["righe"][nome] = _serie_piccola(cfg, cl, nome, stato, tempo, oggi)
                except gme.CredenzialiGME:
                    raise
                except Exception as e:
                    log.exception("MGP %s", nome)
                    esito["errori"].append(f"{nome}: {type(e).__name__}: {e}")
            if m.domanda_offerta:
                def totali(g, df):
                    esito["righe"]["mgp_offerta_domanda_totali"] = esito["righe"].get(
                        "mgp_offerta_domanda_totali", 0) + archivio.aggiorna(
                        cart, "mgp_offerta_domanda_totali", mgp.totali_offerta_domanda(df),
                        ["inizio_utc", "minuti", "zona", "lato"], "data")
                esito["righe"]["mgp_domanda_offerta"] = _giornaliero(
                    cfg, "mgp_domanda_offerta", lambda g: mgp.domanda_offerta(cl, g), oggi, m.domanda_offerta_inizio,
                    m.domanda_offerta_giorni_per_notte, stato, esito, tempo, dopo=totali)
            if m.offerte:
                esito["righe"]["mgp_offerte"] = _giornaliero(
                    cfg, "mgp_offerte", lambda g: mgp.offerte_pubbliche(cl, g),
                    oggi - dt.timedelta(days=m.offerte_ritardo_giorni), m.offerte_inizio, m.offerte_giorni_per_notte,
                    stato, esito, tempo, limite_byte=m.offerte_max_gb * 1e9)
            _avviso(stato, esito, "credenziali", False, "")
        except gme.CredenzialiGME as e:
            esito["errori"].append(str(e))
            _avviso(stato, esito, "credenziali", True,
                    f"{e}\nIl lavoro mercato-mgp (e il lavoro mercati) non scaricano nulla finché la password non è "
                    "rinnovata e aggiornata nel file .env del server (GME_PASSWORD).")
        _controlla_ferme(cfg, stato, esito, oggi)
        stato["notti_fallite"] = 0
    except Exception as e:                       # guasto inatteso: email solo alla terza notte di fila
        log.exception("MGP: lavoro non riuscito")
        esito["errori"].append(f"{type(e).__name__}: {e}")
        stato["notti_fallite"] = stato.get("notti_fallite", 0) + 1
        if stato["notti_fallite"] == MAX_TENTATIVI:
            esito["da_segnalare"].append(f"Lavoro mercato-mgp non riuscito per {MAX_TENTATIVI} notti di fila. Ultimo "
                                         f"errore:\n{traceback.format_exc(limit=5)}")
    finally:
        esito["durata_s"] = round(_adesso() - t0, 1)
        esito["stato"] = {k: v for k, v in stato.items() if k.startswith("mgp_")}
        _scrivi_json(cart / "mgp_stato.json", stato)
        _scrivi_json(cart / "mgp_ultima_esecuzione.json", esito)
    log.info("MGP: righe %s, errori %d, da segnalare %d, %.0f s", esito["righe"], len(esito["errori"]),
             len(esito["da_segnalare"]), esito["durata_s"])
    return esito


def riepilogo(cfg: Config) -> str:
    """Stato dell'archivio MGP per il comando `mgp-stato`: giorni e spazio, nessun valore dei dati."""
    st = _leggi_stato(cfg.cartella)
    righe = []
    for nome in list(mgp.SERIE) + ["mgp_offerta_domanda_totali"]:
        righe.append(f"{nome:28s} dal {archivio.prima_data(cfg.cartella, nome, 'data')} al "
                     f"{archivio.ultima_data(cfg.cartella, nome, 'data')}  "
                     f"{archivio.dimensione(cfg.cartella, nome) / 1e6:8.1f} MB"
                     + ("  storico completo" if st.get(nome, {}).get("completo") else ""))
    for nome in ("mgp_domanda_offerta", "mgp_offerte"):
        g = archivio.giorni(cfg.cartella, nome)
        s = st.get(nome, {})
        righe.append(f"{nome:28s} dal {g[0] if g else None} al {g[-1] if g else None}  {len(g)} giorni  "
                     f"{archivio.dimensione(cfg.cartella, nome) / 1e6:8.1f} MB"
                     + ("  storico completo" if s.get("completo") else "")
                     + (f"  non scaricati: {', '.join(s['non_scaricati'])}" if s.get("non_scaricati") else ""))
    libero = shutil.disk_usage(cfg.cartella).free if cfg.cartella.exists() else 0
    righe.append(f"Spazio libero sul disco dell'archivio: {libero / 1e9:.1f} GB")
    if st.get("avvisi"):
        righe.append(f"Avvisi aperti: {', '.join(st['avvisi'])}")
    return "\n".join(righe)
