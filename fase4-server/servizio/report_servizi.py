"""Report dei servizi di EuGEnio: dalle risposte JSON delle API a un `report.Documento`.

Ogni funzione riceve la risposta già ottenuta dal sito (o calcolata dal server) e costruisce il
documento; il formato (pdf, xlsx, ods; docx e odt spenti dal 28/10/2026) lo sceglie `report.genera`. Le funzioni sono difensive:
un campo mancante o di tipo inatteso viene saltato, non fa fallire il report.

Nuovo tipo di report: scrivere `def report_xxx(d: dict, **kw) -> Documento` e aggiungerlo a `TIPI`;
la rotta `POST /api/report/xxx?formato=…` è subito disponibile.

Regola fissa: nessun dato di mercato GME/EEX (PUN, prezzi zonali, PSV, IGI, TTF, PFOR) nei report.
Le funzioni leggono solo campi noti e `_ammessa` scarta comunque le colonne con quei nomi.
"""
from __future__ import annotations

import math
import re
from collections.abc import Callable

from pydantic import ValidationError

from . import config as C
from .report import Avvertenza, ChiaveValore, Documento, Elenco, Fonte, Immagine, Paragrafo, Sezione, Tabella, Voce

# ---------------------------------------------------------------------------------------------- attribuzioni
OPEN_METEO = Fonte(testo="Weather data by Open-Meteo.com (CC BY 4.0)", url="https://open-meteo.com/")
MODELLI_METEO = Fonte(testo="Modelli meteo: Arpae ICON-2I, DWD ICON, ECMWF IFS; rianalisi ERA5 (Copernicus)")
ISTAT = Fonte(testo="Codici e confini comunali: ISTAT (CC BY 4.0)", url="https://www.istat.it/")
TIREX = Fonte(testo="Modello di previsione TiRex-2 (NX-AI, Apache 2.0)", url="https://huggingface.co/NX-AI")
ZORNADE = Fonte(testo="Dati elaborati da Zornade", url="https://zornade.com")
ANNCSU = Fonte(testo="ANNCSU – Agenzia delle Entrate e ISTAT (CC BY 4.0)")
AVVERTENZA_LEGGE10 = ("I dati derivano dal clima reale osservato nel comune e servono come confronto: non "
                      "sostituiscono i valori normativi della UNI 10349 e del DPR 412/93 (gradi giorno e zona "
                      "climatica), che restano quelli da usare nella relazione tecnica della Legge 10/91.")

_VIETATE = re.compile(r"(?i)(^|[^a-z])(pun|psv|ttf|igi|pfor|gme|eex)([^a-z]|$)")


def _ammessa(chiave: str) -> bool:
    """False per le colonne con dati di mercato riservati (solo uso interno)."""
    return not _VIETATE.search(str(chiave))


def _num(x) -> float | None:
    if isinstance(x, bool) or x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _lista(x) -> list:
    return x if isinstance(x, list) else []


def _diz(x) -> dict:
    return x if isinstance(x, dict) else {}


def _fonti(*fonti: Fonte, extra: list | None = None) -> list[Fonte]:
    """Fonti senza doppioni; `extra` sono testi (o {testo, url}) arrivati con la risposta dell'API."""
    out, visti = [], set()
    tutte = list(fonti)
    for x in _lista(extra):
        if isinstance(x, str) and x.strip():
            tutte.append(Fonte(testo=x.strip()[:1000]))
        elif isinstance(x, dict) and x.get("testo"):
            url = x.get("url") if isinstance(x.get("url"), str) and re.match(r"^https?://\S+$", x["url"]) else None
            tutte.append(Fonte(testo=str(x["testo"])[:1000], url=url))
    for f in tutte:
        k = f.testo.strip().lower()
        if k not in visti and _ammessa(f.testo):
            visti.add(k)
            out.append(f)
    return out


def _codice(s) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", str(s or ""))[:12]


# ---------------------------------------------------------------------------------------------- previsione
NOMI_MODALITA = {"breve": "breve termine (passo orario)", "lungo": "lungo termine (passo giornaliero)"}


def report_previsione(d: dict, nome_comune: Callable[[str], str | None] | None = None) -> Documento:
    """Risposta di POST /api/previsione (modello.prevedi) più il campo facoltativo `richiesta`.

    Forma attesa (da servizio/modello.py): modalita, passo, istat, covariate,
    storico {t, v}, previsione {t, "0.1"…"0.9", fonte_meteo}, avvisi, verifica {reale, mae, wape, bias,
    copertura_80} (solo con verifica).
    `richiesta` (aggiunto dal sito, facoltativo): comune, istat, modalita, orizzonte, covariate, tipo, unita.
    Ipotesi: `richiesta.comune` è il nome del comune (se è un codice numerico si tratta come ISTAT);
    `unita` (es. "kWh") non arriva dall'API e, se manca, i valori restano senza unità.
    """
    d = _diz(d)
    rq = _diz(d.get("richiesta"))
    istat = _codice(d.get("istat") or rq.get("istat") or (rq.get("comune") if str(rq.get("comune", "")).isdigit() else ""))
    comune = rq.get("comune") if isinstance(rq.get("comune"), str) and not str(rq.get("comune")).isdigit() else None
    comune = comune or rq.get("nome_comune") or d.get("comune")
    if not comune and istat and nome_comune:
        try:
            comune = nome_comune(istat)
        except Exception:
            comune = None
    modalita = str(d.get("modalita") or rq.get("modalita") or rq.get("modalità") or "")
    passo = str(d.get("passo") or ("ora" if modalita == "breve" else "giorno" if modalita == "lungo" else "passo"))
    unita = str(rq.get("unita") or rq.get("unità") or "")[:20] or None
    tipo = str(rq.get("tipo") or "")
    pr = _diz(d.get("previsione"))
    t = [str(x) for x in _lista(pr.get("t"))]
    q10, q50, q90 = (_lista(pr.get(k)) for k in ("0.1", "0.5", "0.9"))
    meteo = _lista(pr.get("fonte_meteo"))
    ver = _diz(d.get("verifica"))
    reale = _lista(ver.get("reale"))
    n = len(t)

    def val(lst, i):
        return _num(lst[i]) if i < len(lst) else None

    # parametri
    voci = [("Comune", comune), ("Codice ISTAT", istat or None),
            ("Modalità", NOMI_MODALITA.get(modalita, modalita or None)),
            ("Orizzonte", f"{n} {passo if n == 1 else {'ora': 'ore', 'giorno': 'giorni'}.get(passo, passo)}" if n else None),
            ("Primo passo previsto", t[0] if t else None), ("Ultimo passo previsto", t[-1] if t else None),
            ("Tipo di serie", {"energia": "energia (somma nel passo)", "potenza": "potenza (media nel passo)"}.get(tipo, tipo or None)),
            ("Unità di misura", unita)]
    cov = rq.get("covariate", d.get("covariate"))
    if isinstance(cov, str):
        cov = [c for c in cov.split(",") if c]
    if isinstance(cov, list):
        voci.append(("Covariate", ", ".join(str(c) for c in cov) or "solo calendario"))
    parametri = ChiaveValore(titolo=None, voci=[{"chiave": k, "valore": v} for k, v in voci if v not in (None, "")])

    # sintesi sulla mediana
    med = [x for x in (val(q50, i) for i in range(n)) if x is not None]
    sintesi = []
    if med:
        sintesi = [{"chiave": "Media della mediana", "valore": sum(med) / len(med), "unita": unita},
                   {"chiave": "Minimo della mediana", "valore": min(med), "unita": unita},
                   {"chiave": "Massimo della mediana", "valore": max(med), "unita": unita}]
        if tipo != "potenza":
            sintesi.append({"chiave": "Totale della mediana sull'orizzonte", "valore": sum(med), "unita": unita})
    sezioni = [Sezione(titolo="Parametri", blocchi=[parametri])]
    if sintesi:
        sezioni.append(Sezione(titolo="Sintesi", blocchi=[ChiaveValore(voci=sintesi)]))
    if ver:
        v = []
        if _num(ver.get("wape")) is not None:
            v.append({"chiave": "Errore relativo complessivo (WAPE)", "valore": 100 * _num(ver["wape"]), "unita": "%", "decimali": 1})
        if _num(ver.get("mae")) is not None:
            v.append({"chiave": f"Errore medio assoluto per {passo}", "valore": _num(ver["mae"]), "unita": unita})
        if _num(ver.get("bias")) is not None:
            v.append({"chiave": "Errore sistematico (bias)", "valore": _num(ver["bias"]), "unita": unita})
        if _num(ver.get("copertura_80")) is not None:
            v.append({"chiave": "Valori reali dentro la banda 10–90 %", "valore": 100 * _num(ver["copertura_80"]),
                      "unita": "%", "decimali": 0})
        sezioni.append(Sezione(titolo="Verifica sull'ultimo tratto dei dati", blocchi=[
            Paragrafo(testo="L'ultimo tratto dei dati caricati è stato nascosto al modello e previsto con il meteo "
                            "osservato; il confronto con i valori reali misura l'affidabilità attesa."),
            ChiaveValore(voci=v)]))

    avvisi = [Avvertenza(testo=str(a)[:2000]) for a in _lista(d.get("avvisi")) if isinstance(a, str) and a.strip()]
    avvisi.append(Avvertenza(livello="info", testo=(
        "La previsione è probabilistica: la mediana (P50) è il valore centrale, la banda P10–P90 contiene il valore "
        "reale in circa 8 casi su 10 se il modello è ben calibrato. Le ore sono in ora italiana.")))
    sezioni.append(Sezione(titolo="Avvertenze", blocchi=avvisi))

    intest = ["Data e ora" if passo == "ora" else "Giorno", "P10", "P50 (mediana)", "P90"]
    if reale:
        intest.append("Valore reale")
    intest.append("Meteo usato")
    righe = []
    for i in range(n):
        r = [t[i], val(q10, i), val(q50, i), val(q90, i)]
        if reale:
            r.append(val(reale, i))
        r.append(str(meteo[i]) if i < len(meteo) and meteo[i] is not None else None)
        righe.append(r)
    titolo_tab = "Previsione" + (f" ({unita})" if unita else "")
    blocchi = [Tabella(titolo=titolo_tab, intestazioni=intest, righe=righe,
                       decimali=[None, 2, 2, 2] + ([2] if reale else []) + [None])]
    st = _diz(d.get("storico"))
    ts, vs = _lista(st.get("t")), _lista(st.get("v"))
    if ts:
        blocchi.append(Tabella(titolo="Ultimi dati caricati", intestazioni=[intest[0], "Valore"],
                               righe=[[str(ts[i]), val(vs, i)] for i in range(len(ts))], decimali=[None, 2]))
    sezioni.append(Sezione(titolo="Dati", blocchi=blocchi))

    return Documento(
        titolo="Previsione dei consumi energetici",
        sottotitolo=" – ".join(x for x in (comune or (f"Comune ISTAT {istat}" if istat else None),
                                            NOMI_MODALITA.get(modalita)) if x) or None,
        nome_file="_".join(x for x in ("previsione", istat, modalita) if x),
        sezioni=sezioni,
        fonti=_fonti(TIREX, OPEN_METEO, MODELLI_METEO, ISTAT))


# ---------------------------------------------------------------------------------------------- Legge 10
COLONNE_MENSILI = [("t_media", "T media (°C)", 1), ("t_min_media", "T min (°C)", 1), ("t_max_media", "T max (°C)", 1),
                   ("h_globale_mj", "Irradiazione globale (MJ/m² giorno)", 1),
                   ("h_diffusa_mj", "di cui diffusa (MJ/m² giorno)", 1), ("pv_pa", "Pressione del vapore (Pa)", 0),
                   ("ur_media", "Umidità relativa (%)", 0), ("vento_ms", "Vento (m/s)", 1)]
MESI_BREVI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]


def report_legge10(d: dict, **_) -> Documento:
    """Risposta di GET /api/clima-legge10/{istat} (meteo_storico.legge10.calcola + istat, comune, fonte).

    Campi usati (come in fase5-sito/sito/legge10.js): comune, istat, stagioni, giorni, avvertenza, fonte,
    gradi_giorno {gg_periodo_zona, zona_di_riferimento, zona_risultante, gg_anno_intero, minimo, massimo,
    tendenza_gg_per_decennio, per_stagione {stagione: gg}, gg_per_periodo_di_ogni_zona {zona: gg}},
    temperatura_progetto {invernale, estiva, metodo}, mensili [{mese, t_media, …}].
    Facoltativo, aggiunto dal sito da dati/dpr412.json: dpr412 {gg, zona, alt, nome, nota,
    origini [{nome, gg, zona, alt}]} con i valori di legge dell'Allegato A del DPR 412/93; la differenza
    percentuale e il confronto delle zone si ricalcolano qui.
    """
    d = _diz(d)
    istat = _codice(d.get("istat"))
    comune = str(d.get("comune") or "")[:200] or None
    gg = _diz(d.get("gradi_giorno"))
    tp = _diz(d.get("temperatura_progetto"))
    stagioni = [str(s) for s in _lista(d.get("stagioni"))]

    sezioni = [Sezione(titolo="Avvertenza", blocchi=[Avvertenza(testo=AVVERTENZA_LEGGE10)] + (
        [Avvertenza(livello="info", testo=str(d["avvertenza"])[:5000])]
        if isinstance(d.get("avvertenza"), str) and d["avvertenza"].strip() else []))]
    if stagioni:
        giorni = _num(d.get("giorni"))
        sezioni.append(Sezione(titolo="Periodo esaminato", blocchi=[Paragrafo(testo=(
            f"{len(stagioni)} stagioni di riscaldamento, dalla {stagioni[0]} alla {stagioni[-1]}"
            + (f" ({int(giorni):,} giorni).".replace(",", ".") if giorni is not None else ".")))]))

    if gg:
        tend = _num(gg.get("tendenza_gg_per_decennio"))
        voci = [
            {"chiave": "Gradi giorno (base 20 °C) nel periodo di accensione della zona "
                       f"{gg.get('zona_di_riferimento') or ''}".strip(), "valore": _num(gg.get("gg_periodo_zona")), "decimali": 0},
            {"chiave": "Zona climatica che ne risulta (DPR 412/93, art. 2)", "valore": gg.get("zona_risultante")},
            {"chiave": "Gradi giorno sull'anno intero", "valore": _num(gg.get("gg_anno_intero")), "decimali": 0},
            {"chiave": "Minimo nel periodo della zona", "valore": _num(gg.get("minimo")), "decimali": 0},
            {"chiave": "Massimo nel periodo della zona", "valore": _num(gg.get("massimo")), "decimali": 0},
            {"chiave": "Tendenza (gradi giorno per decennio)",
             "valore": tend if tend is not None else "— (servono almeno 5 stagioni)", "decimali": 0},
        ]
        blocchi = [ChiaveValore(voci=[v for v in voci if v["valore"] is not None and not isinstance(v["valore"], dict)])]
        per = _diz(gg.get("per_stagione"))
        if per:
            blocchi.append(Tabella(titolo="Gradi giorno per stagione", intestazioni=["Stagione", "Gradi giorno"],
                                   righe=[[str(k), _num(v)] for k, v in per.items()], decimali=[None, 0]))
        zone = _diz(gg.get("gg_per_periodo_di_ogni_zona"))
        if zone:
            zr = gg.get("zona_risultante")
            blocchi.append(Tabella(titolo="Gradi giorno nel periodo di accensione di ogni zona",
                                   intestazioni=["Zona", "Gradi giorno", "Zona risultante"],
                                   righe=[[str(z), _num(v), "sì" if z == zr else ""] for z, v in zone.items()],
                                   decimali=[None, 0, None]))
        sezioni.append(Sezione(titolo="Gradi giorno e zona climatica", blocchi=blocchi))

    dpr = _sezione_dpr412(_diz(d.get("dpr412")), gg)
    if dpr:
        sezioni.append(dpr)

    if tp:
        voci = [{"chiave": "Temperatura di progetto invernale", "valore": _num(tp.get("invernale")), "unita": "°C", "decimali": 1},
                {"chiave": "Temperatura di progetto estiva", "valore": _num(tp.get("estiva")), "unita": "°C", "decimali": 1},
                {"chiave": "Metodo", "valore": str(tp["metodo"])[:2000] if tp.get("metodo") else None}]
        sezioni.append(Sezione(titolo="Temperature di progetto",
                               blocchi=[ChiaveValore(voci=[v for v in voci if v["valore"] is not None])]))

    mensili = [m for m in _lista(d.get("mensili")) if isinstance(m, dict)]
    if mensili:
        presenti = [c for c in COLONNE_MENSILI if any(c[0] in m for m in mensili)]
        righe = []
        for m in mensili:
            k = m.get("mese")
            mese = MESI_BREVI[k - 1] if isinstance(k, int) and 1 <= k <= 12 else str(k)
            righe.append([mese] + [_num(m.get(c[0])) for c in presenti])
        sezioni.append(Sezione(titolo="Valori medi mensili", blocchi=[Tabella(
            intestazioni=["Mese"] + [c[1] for c in presenti], righe=righe, decimali=[None] + [c[2] for c in presenti])]))

    extra = [d["fonte"]] if isinstance(d.get("fonte"), str) else []
    if dpr:
        extra.append({"testo": "DPR 26 agosto 1993, n. 412, Allegato A (testo vigente, Normattiva)", "url": DPR412_URL})
    return Documento(
        titolo="Dati climatici per la Legge 10",
        sottotitolo=(f"{comune} (ISTAT {istat})" if comune and istat else comune or (f"ISTAT {istat}" if istat else None)),
        nome_file="_".join(x for x in ("clima_legge10", istat) if x),
        sezioni=sezioni,
        fonti=_fonti(OPEN_METEO, MODELLI_METEO, ISTAT, extra=extra + [
            "Riferimenti normativi: UNI 10349, DPR 412/93, Legge 10/91 (valori normativi da usare nella relazione tecnica)"]))


DPR412_URL = ("https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.del.presidente.della.repubblica:"
              "1993-08-26;412!vig=")
ZONE = ("A", "B", "C", "D", "E", "F")


def _zona(x) -> str | None:
    z = str(x or "").strip().upper()
    return z if z in ZONE else None


def _sezione_dpr412(dpr: dict, gg: dict) -> Sezione | None:
    """Valori di legge del DPR 412/93 accanto a quelli calcolati; None se il corpo non li porta."""
    if not dpr:
        return None
    calc, z_calc = _num(gg.get("gg_periodo_zona")), _zona(gg.get("zona_risultante"))
    g_dpr, z_dpr, alt = _num(dpr.get("gg")), _zona(dpr.get("zona")), _num(dpr.get("alt"))
    origini = [o for o in _lista(dpr.get("origini")) if isinstance(o, dict)]
    nota = str(dpr["nota"])[:1000] if isinstance(dpr.get("nota"), str) and dpr["nota"].strip() else None
    if g_dpr is None and not origini and not nota:
        return None
    blocchi = [Paragrafo(testo=(
        "I gradi giorno e la zona del DPR 412/93 sono i valori di legge, fissati nel 1993 sul clima dei decenni "
        "precedenti: sono quelli da usare nella relazione tecnica. Il calcolo di EuGEnio descrive il clima reale "
        "delle ultime stagioni e serve a confrontare i consumi."))]
    voci = []
    if g_dpr is not None:
        voci.append({"chiave": "Gradi giorno del DPR 412/93", "valore": g_dpr, "decimali": 0})
    if z_dpr:
        voci.append({"chiave": "Zona climatica del DPR 412/93", "valore": z_dpr})
    if alt is not None:
        voci.append({"chiave": "Altitudine della casa comunale (DPR)", "valore": alt, "unita": "m", "decimali": 0})
    if isinstance(dpr.get("nome"), str) and dpr["nome"].strip():
        voci.append({"chiave": "Nome nel DPR", "valore": dpr["nome"].strip()[:200]})
    if g_dpr and calc is not None:
        voci.append({"chiave": "Differenza dei gradi giorno calcolati rispetto al DPR",
                     "valore": round(100 * (calc - g_dpr) / g_dpr, 1), "unita": "%", "decimali": 1})
    if z_dpr and z_calc:
        voci.append({"chiave": "La zona calcolata coincide con quella del DPR",
                     "valore": "sì" if z_dpr == z_calc else f"no (calcolata {z_calc}, DPR {z_dpr})"})
    if nota:
        voci.append({"chiave": "Nota", "valore": nota})
    if voci:
        blocchi.append(ChiaveValore(voci=voci))
    if origini:
        blocchi.append(Tabella(
            titolo="Comuni d'origine nel DPR 412/93",
            intestazioni=["Comune nel DPR", "Gradi giorno", "Zona", "Altitudine (m)"],
            righe=[[str(o.get("nome") or "")[:200], _num(o.get("gg")), _zona(o.get("zona")) or "", _num(o.get("alt"))]
                   for o in origini[:50]],
            decimali=[None, 0, None, 0]))
    return Sezione(titolo="Confronto con il DPR 412/93", blocchi=blocchi)


# ---------------------------------------------------------------------------------------------- patrimonio
ESITI = {"ok": "trovato", "verificare": "da verificare", "non_trovato": "non trovato", "errore": "errore"}
# colonne note delle righe di /api/patrimonio (territorio.patrimonio.geolocalizza, come usate da patrimonio.js)
COLONNE_PATRIMONIO = [("id", "Codice", None), ("denominazione", "Denominazione", None),
                      ("cercato", "Indirizzo cercato", None), ("esito", "Esito", None),
                      ("indirizzo_trovato", "Indirizzo trovato", None), ("fonte_punto", "Fonte del punto", None),
                      ("comune_catasto", "Comune catastale", None), ("foglio_catasto", "Foglio", None),
                      ("mappale", "Mappale", None), ("area_m2", "Superficie particella (m²)", 0),
                      ("tipo_particella", "Tipo particella", None), ("lat", "Latitudine", 5), ("lon", "Longitudine", 5),
                      ("nota", "Nota", None)]


def report_patrimonio(d: dict, **_) -> Documento:
    """Oggetto {righe, fonti} con le righe unite di tutti i blocchi inviati a POST /api/patrimonio.

    Ipotesi: ogni riga ha `esito` (ok, verificare, non_trovato, errore) e i campi usati da patrimonio.js
    (id, denominazione, indirizzo, civico, comune, indirizzo_trovato, fonte_punto, comune_catasto,
    foglio_catasto, mappale, area_m2, tipo_particella, lat, lon, nota). Il `riepilogo` del server non si usa:
    i conteggi si rifanno dalle righe, perché il sito unisce più blocchi. Se nessuna colonna nota è
    presente, si riportano tutte le colonne trovate (tranne quelle con dati di mercato).
    """
    d = _diz(d)
    righe = [r for r in _lista(d.get("righe")) if isinstance(r, dict)]
    conta: dict[str, int] = {}
    for r in righe:
        conta[str(r.get("esito"))] = conta.get(str(r.get("esito")), 0) + 1
    voci = [{"chiave": "Edifici esaminati", "valore": len(righe)}]
    voci += [{"chiave": f"Esito: {nome}", "valore": conta.get(k, 0)} for k, nome in ESITI.items()
             if k != "errore" or conta.get(k)]
    altri = sum(v for k, v in conta.items() if k not in ESITI)
    if altri:
        voci.append({"chiave": "Esito non indicato", "valore": altri})

    def cercato(r):
        return " ".join(str(r[k]) for k in ("indirizzo", "civico", "comune") if r.get(k) not in (None, "")) or None

    def valore(r, k):
        if k == "cercato":
            return cercato(r)
        if k == "esito":
            return ESITI.get(r.get("esito"), r.get("esito"))
        v = r.get(k)
        if isinstance(v, (dict, list)):
            return None
        return _num(v) if k in ("area_m2", "lat", "lon") else v

    note = [c for c in COLONNE_PATRIMONIO if any(r.get(c[0]) not in (None, "") or
                                                  (c[0] == "cercato" and cercato(r)) for r in righe)]
    if righe and not note:
        chiavi = []
        for r in righe:
            chiavi += [k for k in r if k not in chiavi and _ammessa(k) and not isinstance(r[k], (dict, list))]
        note = [(k, k, None) for k in chiavi]
    note = [c for c in note if _ammessa(c[0])][:30]
    sezioni = [Sezione(titolo="Riepilogo", blocchi=[ChiaveValore(voci=voci), Avvertenza(testo=(
        "La geolocalizzazione è automatica: controllare gli edifici «da verificare» e «non trovati» prima di "
        "usare i dati. Le particelle catastali sono indicative e non hanno valore legale."))])]
    if righe:
        sezioni.append(Sezione(titolo="Edifici", blocchi=[Tabella(
            intestazioni=[c[1] for c in note],
            righe=[[valore(r, c[0]) for c in note] for r in righe],
            decimali=[c[2] for c in note])]))
    # attribuzione Zornade obbligatoria (piano gratuito), sempre con il link a https://zornade.com
    f = d.get("fonte")
    zornade = (Fonte(testo=f[:1000], url=ZORNADE.url) if isinstance(f, str) and f.startswith(ZORNADE.testo)
               else ZORNADE)
    return Documento(
        titolo="Patrimonio edilizio geolocalizzato",
        sottotitolo=f"{len(righe):,} edifici".replace(",", "."),
        nome_file="patrimonio_geolocalizzato",
        sezioni=sezioni,
        fonti=_fonti(zornade, ANNCSU, ISTAT, extra=d.get("fonti")))


# ---------------------------------------------------------------------------------------------- indicatori SSN
OPENBDAP = Fonte(testo="Ragioneria Generale dello Stato – OpenBDAP, modello CE degli enti del SSN (CC BY 4.0)",
                 url="https://bdap-opendata.rgs.mef.gov.it/tema/sanit%C3%A0")
AVVERTENZE_INDICATORI = [
    "Sono euro, non kilowattora: la spesa segue i prezzi oltre ai consumi (il 2022 mostra i rincari).",
    "Le voci contabili non sono uguali ovunque (contratti servizio energia, global service): il totale è più solido "
    "delle singole componenti.",
    "Il valore della produzione è in gran parte finanziamento regionale: la leva dipende anche dal riparto.",
    "La spesa di un'AUSL comprende le sedi territoriali, giornate e posti letto solo gli ospedali.",
    "Il 2025 è provvisorio (conto economico del IV trimestre).",
]
# (campo, intestazione, decimali, moltiplicatore)
COLONNE_INDICATORI = [
    ("spesa", "Spesa (€)", 0, 1), ("AZ9999", "Valore della produzione (€)", 0, 1),
    ("BZ9999", "Costi della produzione (€)", 0, 1), ("leva", "Leva (volte)", 1, 1),
    ("incidenza", "Incidenza (%)", 2, 100), ("peso", "Peso (%)", 2, 100),
    ("per_giornata", "€ per giornata di degenza", 2, 1), ("per_posto", "€ per posto letto", 0, 1),
    ("per_cittadino", "€ per cittadino", 2, 1),
]
RIGHE_CONFRONTO = [
    ("spesa", "Spesa per energia e utenze (€)", 0, 1), ("leva", "Leva (€ di produzione per 1 € di energia)", 1, 1),
    ("incidenza", "Incidenza sul valore della produzione (%)", 2, 100),
    ("peso", "Peso sui costi della produzione (%)", 2, 100), ("per_cittadino", "€ per cittadino", 2, 1),
    ("per_giornata", "€ per giornata di degenza ordinaria", 2, 1), ("per_posto", "€ per posto letto", 0, 1),
]


def _per(x, k: float):
    v = _num(x)
    return None if v is None else v * k


def report_indicatori(d: dict, **_) -> Documento:
    """Corpo mandato da fase5-sito/sito/indicatori.js (valori già calcolati dal sito con le formule di
    fase8-indicatori/indicatori_ssn/calcolo.py): ente, regione, italia {nome, codice, regione_ce,
    fonte_residenti, anni [{anno, provvisorio, spesa, leva, incidenza, peso, per_giornata, per_posto,
    per_cittadino, AZ9999, BZ9999, …}]}, consolidato, componente, anno_confronto, avvertenze, fonti, elaborazione.
    Qui si impagina soltanto: nessun ricalcolo, nessun dato oltre a quelli ricevuti."""
    d = _diz(d)
    unita = {k: _diz(d.get(k)) for k in ("ente", "regione", "italia")}
    unita = {k: u for k, u in unita.items() if _lista(u.get("anni"))}
    ente = unita.get("ente", {})
    nome = str(ente.get("nome") or "Ente")[:200]
    comp = str(d.get("componente") or "totale energia e utenze")[:200]
    avv = [str(x)[:1000] for x in _lista(d.get("avvertenze")) if isinstance(x, str) and x.strip()][:12] or AVVERTENZE_INDICATORI
    sezioni = [Sezione(titolo="Avvertenze", blocchi=[Elenco(voci=avv)]),
               Sezione(titolo="Che cosa si confronta", blocchi=[Paragrafo(testo=(
                   f"Spesa considerata: {comp}. Ogni ente si confronta con il conto consolidato della sua regione "
                   "(codice 999) e con l'Italia (somma dei consolidati di regioni e province autonome). "
                   "Leva = valore della produzione / spesa; incidenza = spesa / valore della produzione; "
                   "peso = spesa / costi della produzione."))])]

    def riga_anno(u, anno):
        return next((r for r in _lista(u.get("anni")) if isinstance(r, dict) and r.get("anno") == anno), {})

    anno = d.get("anno_confronto")
    if isinstance(anno, int) and unita:
        nomi = [str(unita[k].get("nome") or k)[:80] for k in unita]
        righe = []
        for campo, etichetta, _, k in RIGHE_CONFRONTO:
            valori = [_per(riga_anno(unita[u], anno).get(campo), k) for u in unita]
            if any(v is not None for v in valori):
                righe.append([etichetta] + valori)
        prov = any(riga_anno(u, anno).get("provvisorio") is True for u in unita.values())
        sezioni.append(Sezione(titolo=f"Confronto nel {anno}" + (" (provvisorio)" if prov else ""), blocchi=[Tabella(
            intestazioni=["Indicatore"] + nomi, righe=righe, decimali=None,
            nota="n.d. = dato non disponibile (manca il denominatore).")]))
    for k, u in unita.items():
        presenti = [c for c in COLONNE_INDICATORI if any(_num(_diz(r).get(c[0])) is not None for r in _lista(u.get("anni")))]
        righe = []
        for r in _lista(u.get("anni"))[:50]:
            r = _diz(r)
            a = r.get("anno")
            righe.append([f"{a} (provvisorio)" if r.get("provvisorio") is True else str(a)]
                         + [_per(r.get(c[0]), c[3]) for c in presenti])
        if righe:
            fp = u.get("fonte_residenti")
            nota = {"siseps": "Residenti: SISEPS (ReportER).", "istat": "Residenti: ISTAT."}.get(fp)
            sezioni.append(Sezione(titolo=str(u.get("nome") or k)[:200], blocchi=[Tabella(
                intestazioni=["Anno"] + [c[1] for c in presenti], righe=righe,
                decimali=[None] + [c[2] for c in presenti], nota=nota)]))
    extra = list(_lista(d.get("fonti")))
    if isinstance(d.get("elaborazione"), str):
        extra.append(d["elaborazione"][:1000])
    cod = "_".join(x for x in (_codice(ente.get("regione_ce")), _codice(ente.get("codice"))) if x)
    return Documento(
        titolo="Indicatori della spesa energetica",
        sottotitolo=f"{nome} – {comp}",
        nome_file="_".join(x for x in ("indicatori_energia", cod) if x),
        sezioni=sezioni,
        fonti=_fonti(OPENBDAP, extra=extra))


# ---------------------------------------------------------------------------------------------- valori per sede
CONVENZIONE_ABBINAMENTI = (
    "Abbinamento dei consumi ai costi per posizione: la prima colonna di consumo da sinistra va con la prima colonna "
    "di costo da sinistra, la seconda con la seconda e così via. Il costo unitario medio è la somma dei costi divisa "
    "per la somma dei consumi, sulle sole sedi che hanno entrambi i valori.")


def _testo(x, n: int = 300) -> str:
    return str(x if x is not None else "")[:n]


def _immagine_svg(x, titolo_predefinito: str) -> Immagine | None:
    """{titolo, svg (base64)} → Immagine SVG; None se manca o non è valida (un'immagine sbagliata non ferma il report)."""
    x = _diz(x)
    dati = x.get("svg")
    if not isinstance(dati, str) or not dati:
        return None
    try:
        return Immagine(formato="svg", dati=dati, didascalia=_testo(x.get("titolo") or titolo_predefinito) or None,
                        larghezza_cm=17)
    except ValidationError:
        return None


def _tabella_valori(t) -> Tabella | None:
    """{titolo, intestazioni, righe, decimali} dal sito → Tabella, senza colonne con nomi di dati di mercato."""
    t = _diz(t)
    intest = [_testo(h, 300) for h in _lista(t.get("intestazioni"))][:C.REPORT_MAX_COLONNE]
    tenere = [j for j, h in enumerate(intest) if _ammessa(h)]
    if not tenere:
        return None
    dec = _lista(t.get("decimali"))

    def cella(v):
        if isinstance(v, bool) or v is None:
            return v
        if isinstance(v, (int, float)):
            return _num(v)
        return _testo(v, 1000)

    righe = []
    for r in _lista(t.get("righe"))[:C.REPORT_MAX_RIGHE]:
        r = _lista(r)
        righe.append([cella(r[j]) if j < len(r) else None for j in tenere])
    decimali = [dec[j] if j < len(dec) and isinstance(dec[j], int) and 0 <= dec[j] <= 8 else None for j in tenere]
    return Tabella(titolo=_testo(t.get("titolo")) or None, intestazioni=[intest[j] for j in tenere], righe=righe,
                   decimali=decimali, nota=_testo(t.get("nota"), 2000) or None)


def report_valori_sedi(d: dict, formato: str = "pdf", **_) -> Documento:
    """Corpo mandato da fase5-sito/sito/valori_sedi.js (pagina Patrimonio, «Valori per sede»):
    titolo, sottotitolo, totali [{colonna, tipo: consumo|costo, totale, unita, sedi}],
    prezzi [{consumo, costo, valore, unita, sedi}], mappe [{titolo, svg}], pareto [{titolo, tipo, svg}]
    (SVG piatti in base64, colori risolti), tabelle [{titolo, tipo, intestazioni, righe, decimali, nota}], note, fonti,
    avviso {titolo, testo} facoltativo (file d'esempio: va in cima al report).
    Ordine (richiesta di Paolo): totali e costi unitari medi, mappe tridimensionali, Pareto dei consumi e poi dei
    costi, tabelle dei consumi e poi dei costi. Nel PDF le immagini SVG; in Excel e ODS solo totali e tabelle.
    I valori sono quelli del file dell'utente: qui si impagina soltanto."""
    d = _diz(d)
    pdf = formato == "pdf"
    sezioni: list[Sezione] = []
    note = [_testo(x, 2000) for x in _lista(d.get("note")) if isinstance(x, str) and x.strip()][:10]

    # 1. totali, prima i consumi e poi i costi
    blocchi = []
    for tipo, titolo in (("consumo", "Consumi"), ("costo", "Costi")):
        righe = [[_testo(x.get("colonna")), _num(x.get("totale")), _testo(x.get("unita"), 40) or None,
                  int(x["sedi"]) if isinstance(x.get("sedi"), int) else None]
                 for x in map(_diz, _lista(d.get("totali")))
                 if x.get("tipo") == tipo and _ammessa(x.get("colonna", ""))]
        if righe:
            # decimali: nessuno se tutti i totali superano 1.000 (MWh, Smc, €…), altrimenti due
            dec = 0 if all(r[1] is None or abs(r[1]) >= 1000 for r in righe) else 2
            blocchi.append(Tabella(titolo=f"Totali dei {titolo.lower()}", intestazioni=["Colonna", "Totale", "Unità", "Sedi"],
                                   righe=righe[:C.REPORT_MAX_COLONNE * 4], decimali=[None, dec, None, 0]))
    if blocchi:
        blocchi.append(Paragrafo(testo="I totali sono calcolati su tutte le sedi del file, anche quelle spente sulla mappa."))
        sezioni.append(Sezione(titolo="Totali", blocchi=blocchi))
    # costi unitari medi: una voce per abbinamento, ognuna coi suoi decimali (2 per l'energia in €/MWh, decisione di
    # Paolo del 29/10/2026; quelli indicati dalla pagina, altrimenti 3)
    voci = []
    for x in map(_diz, _lista(d.get("prezzi"))):
        if not (_ammessa(x.get("consumo", "")) and _ammessa(x.get("costo", ""))):
            continue
        dx = x.get("decimali")
        n = x.get("sedi") if isinstance(x.get("sedi"), int) else None
        chiave = f"{_testo(x.get('consumo'))} ← {_testo(x.get('costo'))}" + (f" ({n} {'sede' if n == 1 else 'sedi'})" if n else "")
        voci.append(Voce(chiave=chiave[:200], valore=_num(x.get("valore")), unita=_testo(x.get("unita"), 40) or None,
                         decimali=dx if isinstance(dx, int) and 0 <= dx <= 4 else 3))
    if voci:
        if formato in ("xlsx", "ods"):   # nei fogli una tabella vera (un foglio a sé, numeri come numeri)
            dd = {v.decimali for v in voci}
            blocco = Tabella(titolo="Costi unitari medi", intestazioni=["Abbinamento", "Costo unitario medio", "Unità"],
                             righe=[[v.chiave, v.valore, v.unita] for v in voci[:100]],
                             decimali=[None, dd.pop() if len(dd) == 1 else 3, None])
        else:                             # nel PDF ogni voce coi suoi decimali
            blocco = ChiaveValore(titolo="Costi unitari medi", voci=voci[:100])
        sezioni.append(Sezione(titolo="Costi unitari medi", blocchi=[
            blocco,
            Paragrafo(testo=CONVENZIONE_ABBINAMENTI)]))

    # 2-3. immagini (solo PDF): mappe, poi Pareto dei consumi e dei costi, entro il limite di immagini del documento
    if pdf:
        posti = C.REPORT_MAX_IMMAGINI
        saltate = 0
        gruppi = [("Mappe tridimensionali", [_immagine_svg(m, "Mappa") for m in _lista(d.get("mappe"))[:4]])]
        for tipo, titolo in (("consumo", "Diagrammi di Pareto dei consumi"), ("costo", "Diagrammi di Pareto dei costi")):
            gruppi.append((titolo, [_immagine_svg(p, "Diagramma di Pareto") for p in _lista(d.get("pareto"))
                                    if _diz(p).get("tipo") == tipo and _ammessa(_diz(p).get("titolo", ""))][:20]))
        for titolo, immagini in gruppi:
            immagini = [i for i in immagini if i is not None]
            tenute, saltate = immagini[:posti], saltate + max(0, len(immagini) - posti)
            posti -= len(tenute)
            if tenute:
                sezioni.append(Sezione(titolo=titolo, blocchi=tenute))
        if saltate:
            note.append(f"{saltate} grafici non sono entrati nel report (massimo {C.REPORT_MAX_IMMAGINI} immagini).")

    # 4. tabelle: prima i consumi, poi i costi
    tabelle = [t for t in map(_diz, _lista(d.get("tabelle")))]
    for tipo, titolo in (("consumo", "Valori per sede: consumi"), ("costo", "Valori per sede: costi")):
        for t in tabelle:
            if t.get("tipo") == tipo:
                tab = _tabella_valori(t)
                if tab is not None:
                    sezioni.append(Sezione(titolo=titolo, blocchi=[tab]))
    if note:
        sezioni.append(Sezione(titolo="Note", blocchi=[Elenco(voci=note)]))
    if not sezioni:
        sezioni.append(Sezione(titolo="Nessun dato", blocchi=[Paragrafo(testo="Il corpo non conteneva totali né tabelle.")]))
    avviso = _diz(d.get("avviso"))           # file d'esempio: avviso «Dati di esempio non reali» in cima
    primi = []
    if avviso.get("testo"):
        primi.append(Avvertenza(livello="attenzione", testo=f"{_testo(avviso.get('titolo'), 200) or 'Attenzione'}. {_testo(avviso.get('testo'), 2000)}"))
    sezioni.insert(0, Sezione(titolo=None, blocchi=primi + [Avvertenza(livello="info", testo=(
        "I valori sono quelli del file caricato, non verificati da EuGEnio. La posizione delle sedi è una stima "
        "automatica: le sedi senza coordinate sono poste al centro del loro comune."))]))
    return Documento(
        titolo=_testo(d.get("titolo")) or "Valori per sede",
        sottotitolo=_testo(d.get("sottotitolo")) or None,
        nome_file="valori_per_sede",
        sezioni=sezioni[:C.REPORT_MAX_SEZIONI],
        fonti=_fonti(*([ZORNADE] if any("anncsu" in str(x).lower() for x in _lista(d.get("fonti"))) else [ZORNADE, ANNCSU]),
                     ISTAT, extra=d.get("fonti")))


TIPI: dict[str, Callable[..., Documento]] = {
    "previsione": report_previsione,
    "legge10": report_legge10,
    "patrimonio": report_patrimonio,
    "indicatori": report_indicatori,
    "valori_sedi": report_valori_sedi,
}
# tipi che ricevono anche il formato (per esempio per lasciare le immagini fuori da Excel e ODS)
CON_FORMATO = {"valori_sedi"}
