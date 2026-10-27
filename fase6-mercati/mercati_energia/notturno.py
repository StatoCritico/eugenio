"""Aggiornamento notturno dei dati di mercato, con recupero progressivo dello storico.

Orario consigliato: 02:30 ora italiana. A quell'ora sono già pubblicati l'MGP e l'MGP-GAS del giorno
dopo, l'IGI del giorno e il TTF fino a ieri. Si aggiornano anche il PSV day-ahead mensile ufficiale
(ARERA CMEM,m, nuovo valore nei primi due giorni lavorativi del mese; i mesi 10/2022-12/2023 dal file
`dati/psv_da_arera_2022_2023.csv`) e le quotazioni dei future
trimestrali TTF lette dal sito EEX, che servono solo al calcolo del PFOR (più un'eventuale fonte CSV).
Poi la sorveglianza delle fonti delle convenzioni (sorveglianza.py): pagine delle centrali, documenti nuovi,
confronto dei valori con i file TOML.

Ogni notte, per ogni serie:
  1. dati recenti: dall'ultimo giorno in archivio (meno `giorni_riverifica`, per le rettifiche) a domani;
     se l'archivio è vuoto, gli ultimi 30 giorni;
  2. storico: all'indietro, dal giorno più vecchio in archivio fino all'inizio della serie
     (PUN e prezzi zonali dal 1/4/2004, gas dal dicembre 2010, IGI dalla sua prima pubblicazione),
     per al massimo `max_minuti_storico` minuti a notte. Se per sei blocchi di fila il GME non
     restituisce nulla, la serie si considera iniziata lì. Il punto raggiunto è in storico.json:
     in pochi giorni lo storico è completo, poi resta solo l'aggiornamento recente.
"""
from __future__ import annotations

import datetime as dt
import logging
import time

from . import archivio, arera, eex, gme, indici, pfor
from .config import Config

log = logging.getLogger(__name__)
SOGLIA_15MIN = dt.date(2025, 10, 1)


def _passo(nome: str, giorno: dt.date) -> int:
    if nome in ("mgp_prezzi", "mgp_volumi"):
        return 7 if giorno >= SOGLIA_15MIN else 31
    return 90


def _blocchi_avanti(nome, dal, al):
    a = dal
    while a <= al:
        b = min(al, a + dt.timedelta(days=_passo(nome, a) - 1))
        if a < SOGLIA_15MIN <= b:            # i blocchi non attraversano il passaggio ai 15 minuti
            b = SOGLIA_15MIN - dt.timedelta(days=1)
        yield a, b
        a = b + dt.timedelta(days=1)


def _blocchi_indietro(nome, dal, al):
    b = al
    while b >= dal:
        a = max(dal, b - dt.timedelta(days=_passo(nome, b) - 1))
        if a < SOGLIA_15MIN <= b:
            a = SOGLIA_15MIN
        yield a, b
        b = a - dt.timedelta(days=1)


def serie(cfg: Config) -> list[tuple]:
    g = cfg.gme
    inizio_el = g.inizio_orario or g.inizio_quartorario
    out = [("mgp_prezzi", gme.prezzi_mgp, inizio_el, ["inizio_utc", "zona"])]
    if g.volumi:
        out.append(("mgp_volumi", gme.volumi_mgp, inizio_el, ["inizio_utc", "zona"]))
    out += [("mgp_gas", gme.mgp_gas, g.inizio_gas, ["data", "mercato", "prodotto"]),
            ("mgp_gas_continua", gme.mgp_gas_continua, g.inizio_gas, ["data", "mercato", "prodotto"]),
            ("igi", gme.igi, g.inizio_igi, ["data", "prodotto"])]
    return out


def _gme(cfg: Config, esito: dict) -> None:
    cl = gme.ClientGME(cfg.gme.utente, cfg.gme.password())
    domani = dt.date.today() + dt.timedelta(days=1)
    scadenza = time.time() + cfg.gme.max_minuti_storico * 60
    stato = archivio.stato_storico(cfg.cartella)
    for nome, funzione, inizio, chiavi in serie(cfg):
        n = 0
        try:
            # 1. recenti
            ultimo = archivio.ultima_data(cfg.cartella, nome, "data")
            dal = (ultimo - dt.timedelta(days=cfg.gme.giorni_riverifica)) if ultimo else domani - dt.timedelta(days=30)
            for a, b in _blocchi_avanti(nome, max(dal, inizio), domani):
                n += archivio.aggiorna(cfg.cartella, nome, funzione(cl, a, b), chiavi, "data")
            # 2. storico all'indietro
            s = stato.setdefault(nome, {})
            primo = archivio.prima_data(cfg.cartella, nome, "data") or domani
            limite = dt.date.fromisoformat(s["inizia_il"]) if s.get("inizia_il") else inizio
            vuoti = 0
            if primo > limite:
                for a, b in _blocchi_indietro(nome, limite, primo - dt.timedelta(days=1)):
                    if time.time() > scadenza:
                        break
                    righe = funzione(cl, a, b)
                    if righe is None or righe.empty:
                        vuoti += 1
                        if vuoti == 1:
                            fine_vuoto = b
                        if vuoti >= 6:   # nessun dato da sei blocchi: la serie comincia dopo il primo vuoto
                            s["inizia_il"] = str(fine_vuoto + dt.timedelta(days=1))
                            s["completo"] = True
                            break
                        s["raggiunto"] = str(a)
                        continue
                    vuoti = 0
                    n += archivio.aggiorna(cfg.cartella, nome, righe, chiavi, "data")
                    s["raggiunto"] = str(a)
                else:
                    s["completo"] = True
            else:
                s["completo"] = True
            s["primo_giorno"] = str(archivio.prima_data(cfg.cartella, nome, "data"))
            esito["dataset"][nome] = n
        except gme.ErroreGME:
            raise
        except Exception as e:  # un dataset in errore non ferma gli altri
            log.exception("GME %s", nome)
            esito["errori"].append(f"GME {nome}: {e}")
        finally:
            archivio.salva_stato_storico(cfg.cartella, stato)
    esito["storico"] = stato


def esegui(cfg: Config) -> dict:
    t0 = time.time()
    esito = {"inizio": dt.datetime.now().isoformat(timespec="seconds"), "dataset": {}, "errori": []}
    if cfg.gme.abilitato:
        try:
            _gme(cfg, esito)
        except gme.ErroreGME as e:
            esito["errori"].append(str(e))
    if cfg.ttf_eex:
        try:
            esito["dataset"]["ttf_eex"] = archivio.aggiorna(cfg.cartella, "ttf_eex", eex.ttf_ngp(), ["data"], "data")
        except Exception as e:
            log.exception("EEX TTF")
            esito["errori"].append(f"EEX TTF: {e}")
    if cfg.arera_cmem:
        # 10/2022-12/2023 dal file nel pacchetto (nessuna chiamata in rete), poi la pagina dal 2024
        esito["dataset"]["psv_da_arera"] = archivio.aggiorna(cfg.cartella, "indici_importati", arera.storico(),
                                                             ["indice", "mese"], "data")
        try:
            esito["dataset"]["psv_da_arera"] += archivio.aggiorna(cfg.cartella, "indici_importati", arera.cmem(),
                                                                  ["indice", "mese"], "data")
        except Exception as e:
            log.exception("ARERA CMEM")
            esito["errori"].append(f"ARERA CMEM: {e}")
    if cfg.ttf_forward_eex:
        try:
            esito["dataset"]["ttf_forward"] = archivio.aggiorna(cfg.cartella, "ttf_forward", eex.ttf_trimestrali(),
                                                                ["data", "trimestre"], "data")
        except Exception as e:
            log.exception("EEX future trimestrali TTF")
            esito["errori"].append(f"EEX future trimestrali TTF: {e}")
    if cfg.pfor_sorgente.get("url"):
        try:
            esito["dataset"]["ttf_forward"] = archivio.aggiorna(cfg.cartella, "ttf_forward",
                                                                pfor.scarica_forward(cfg.pfor_sorgente),
                                                                ["data", "trimestre"], "data")
        except Exception as e:
            log.exception("forward TTF")
            esito["errori"].append(f"forward TTF: {e}")
    if cfg.sorveglianza and cfg.convenzioni:
        # pagine delle centrali e documenti delle convenzioni: novità, valori cambiati, PSV ARERA in ritardo
        try:
            from . import sorveglianza
            esito["sorveglianza"] = sorveglianza.esegui(cfg.cartella, cfg.convenzioni)
        except Exception as e:
            log.exception("sorveglianza")
            esito["errori"].append(f"sorveglianza delle convenzioni: {e}")
    try:
        esito["indici_mensili"] = int(len(indici.calcola(cfg.cartella, tuple(cfg.festivi_extra))))
    except Exception as e:
        log.exception("indici")
        esito["errori"].append(f"indici mensili: {e}")
    esito["durata_s"] = round(time.time() - t0, 1)
    esito["dimensioni_byte"] = archivio.dimensioni(cfg.cartella)
    archivio.registra_esecuzione(cfg.cartella, esito)
    log.info("Aggiornamento mercati: %s", {k: v for k, v in esito.items() if k != "storico"})
    return esito
