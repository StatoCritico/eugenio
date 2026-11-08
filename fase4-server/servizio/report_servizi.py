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



def _modello_cielo(d) -> str:
    """Modello del cielo diffuso dichiarato dalla pagina 3D (dal 05/11/2026 Perez; le pagine più vecchie: isotropo)."""
    m = str((d or {}).get("modello_cielo") or "").strip().lower() if isinstance(d, dict) else ""
    return "di Perez (1990)" if m.startswith("perez") else "isotropa"


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


# variabili meteo delle schede della pagina (fase5-sito/sito/app.js, COV), nello stesso ordine delle opzioni
NOMI_CLIMA = {"temperatura": "Temperatura", "gradi_giorno": "Gradi giorno", "gradi_raffrescamento": "Gradi giorno estivi",
              "radiazione": "Radiazione solare", "diffusa": "Radiazione diffusa", "umidita": "Umidità", "vento": "Vento",
              "nuvolosita": "Nuvolosità", "pioggia": "Pioggia", "neve": "Neve"}
ORDINE_CLIMA = {"breve": ["temperatura", "radiazione", "umidita", "diffusa", "vento", "nuvolosita", "pioggia", "neve"],
                "lungo": ["temperatura", "gradi_giorno", "gradi_raffrescamento", "radiazione", "umidita", "vento", "pioggia"]}
# colori fissi dei grafici del PDF (tema chiaro, vestito corallo): niente trasparenze, che fpdf2 non rende sempre
_COL = {"inchiostro": "#2b2730", "serie1": "#c43c12", "serie2": "#2f6db5", "banda1": "#f6d9cc", "banda2": "#eeb39b",
        "linea": "#dddae0", "tenue": "#6b6670", "debole": "#f1eff3"}


def _nome_clima(k: str, modalita: str) -> str:
    return "Temperatura media" if (k == "temperatura" and modalita == "lungo") else NOMI_CLIMA.get(k, k)


def _ordine_clima(clima: dict, richieste, modalita: str) -> list[str]:
    """Variabili meteo della risposta nell'ordine delle opzioni della pagina (quello delle covariate richieste,
    poi quello predefinito della modalità, poi le altre)."""
    rich = richieste.split(",") if isinstance(richieste, str) else richieste if isinstance(richieste, list) else []
    ordine = [str(k) for k in rich] + ORDINE_CLIMA.get(modalita, []) + list(clima)
    out = []
    for k in ordine:
        if k in clima and k not in out and _ammessa(k):
            out.append(k)
    return out[:C.REPORT_MAX_COLONNE - 6]


def _etichetta_t(x: str, passo: str) -> str:
    x = str(x)
    if len(x) >= 10 and x[4] == "-" and x[7] == "-":
        g = f"{x[8:10]}/{x[5:7]}"
        return f"{g} {x[11:13]}h" if passo == "ora" and len(x) >= 13 else f"{g}/{x[2:4]}"
    return x[:16]


def _svg_serie(t: list[str], n0: int, linee: list[tuple], bande: list[tuple] = (), deboli: list[bool] | None = None,
               unita: str | None = None, passo: str = "ora", legenda: list[tuple] | None = None) -> str:
    """Grafico a linee piatto (SVG senza CSS né trasparenze) per il PDF: t = etichette di tutti i passi, n0 = passi
    osservati prima del futuro; linee = [(valori sui passi, colore, spessore, tratteggio|None)], bande = [(basso, alto,
    colore)] sui soli passi futuri, deboli = passi futuri con meteo meno affidabile (fondo grigio)."""
    from xml.sax.saxutils import escape
    W, H, sx, dx, su, gi = 760, 300, 56, 12, 14, 52
    n = max(len(t), 2)
    vals = [v for serie in linee for v in serie[0] if v is not None]
    vals += [v for b in bande for lst in b[:2] for v in lst if v is not None]
    if not vals:
        vals = [0.0, 1.0]
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.08 or 1
    lo, hi = lo - pad, hi + pad
    X = lambda i: sx + (W - sx - dx) * i / (n - 1)
    Y = lambda v: su + (H - su - gi) * (1 - (v - lo) / (hi - lo))
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>']
    if deboli:
        i = 0
        while i < len(deboli):
            if deboli[i]:
                j = i
                while j + 1 < len(deboli) and deboli[j + 1]:
                    j += 1
                o.append(f'<rect x="{X(n0 + i):.1f}" y="{su}" width="{max(X(n0 + j) - X(n0 + i), 1):.1f}" '
                         f'height="{H - su - gi}" fill="{_COL["debole"]}"/>')
                i = j + 1
            else:
                i += 1
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        y = Y(v)
        o.append(f'<line x1="{sx}" y1="{y:.1f}" x2="{W - dx}" y2="{y:.1f}" stroke="{_COL["linea"]}" stroke-width="0.8"/>')
        dec = 1 if abs(hi - lo) < 20 else 0
        o.append(f'<text x="{sx - 6}" y="{y + 4:.1f}" font-size="11" fill="{_COL["tenue"]}" font-family="DejaVu Sans" '
                 f'text-anchor="end">{escape(f"{v:,.{dec}f}".replace(",", " ").replace(".", ",").replace(" ", "."))}</text>')
    if unita:
        o.append(f'<text x="{sx}" y="{su - 3}" font-size="10" fill="{_COL["tenue"]}" font-family="DejaVu Sans">'
                 f'{escape(unita)}</text>')
    passi = 6
    for k in range(passi + 1):
        i = round((n - 1) * k / passi)
        anc = "start" if k == 0 else "end" if k == passi else "middle"
        o.append(f'<text x="{X(i):.1f}" y="{H - gi + 16}" font-size="11" fill="{_COL["tenue"]}" font-family="DejaVu Sans" '
                 f'text-anchor="{anc}">{escape(_etichetta_t(t[i], passo) if i < len(t) else "")}</text>')
    for basso, alto, col in bande:
        su_ = [(X(n0 + i), Y(v)) for i, v in enumerate(alto) if v is not None]
        giu = [(X(n0 + i), Y(v)) for i, v in enumerate(basso) if v is not None][::-1]
        if su_ and giu:
            o.append(f'<polygon points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in su_ + giu)}" fill="{col}"/>')
    if 0 < n0 < n:
        o.append(f'<line x1="{X(n0 - 0.5):.1f}" y1="{su}" x2="{X(n0 - 0.5):.1f}" y2="{H - gi}" stroke="{_COL["tenue"]}" '
                 f'stroke-width="0.8" stroke-dasharray="2 3"/>')
    for valori, col, w, tratt, inizio in linee:
        d, giu = "", False
        for i, v in enumerate(valori):
            if v is None:
                giu = False
                continue
            d += f'{"L" if giu else "M"}{X(inizio + i):.1f},{Y(v):.1f}'
            giu = True
        if d:
            o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}"'
                     + (f' stroke-dasharray="{tratt}"' if tratt else "") + ' stroke-linejoin="round"/>')
    x = sx
    for col, testo, tipo in legenda or []:
        if tipo == "banda":
            o.append(f'<rect x="{x}" y="{H - 16}" width="16" height="9" fill="{col}"/>')
        else:
            o.append(f'<line x1="{x}" y1="{H - 11}" x2="{x + 16}" y2="{H - 11}" stroke="{col}" stroke-width="2.5"'
                     + (' stroke-dasharray="5 3"' if tipo == "tratto" else "") + "/>")
        o.append(f'<text x="{x + 21}" y="{H - 7}" font-size="11" fill="{_COL["inchiostro"]}" font-family="DejaVu Sans">'
                 f'{escape(testo)}</text>')
        x += 30 + 6.3 * len(testo)
    o.append("</svg>")
    return "".join(o)


def _immagine_grafico(svg: str, didascalia: str) -> Immagine | None:
    import base64
    try:
        return Immagine(formato="svg", dati=base64.b64encode(svg.encode("utf-8")).decode("ascii"),
                        didascalia=didascalia[:300], larghezza_cm=17)
    except ValidationError:
        return None


DEBOLI = {"previsione IFS", "miscela ICON-2I/IFS", "climatologia"}


def report_previsione(d: dict, nome_comune: Callable[[str], str | None] | None = None, formato: str = "pdf") -> Documento:
    """Risposta di POST /api/previsione (modello.prevedi) più il campo facoltativo `richiesta`.

    Forma attesa (da servizio/modello.py): modalita, passo, istat, covariate,
    storico {t, v}, previsione {t, "0.1"…"0.9", fonte_meteo}, avvisi, verifica {reale, mae, wape, bias,
    copertura_80} (solo con verifica).
    `richiesta` (aggiunto dal sito, facoltativo): comune, istat, modalita, orizzonte, covariate, tipo, unita.
    Ipotesi: `richiesta.comune` è il nome del comune (se è un codice numerico si tratta come ISTAT);
    `unita` (es. "kWh") non arriva dall'API e, se manca, i valori restano senza unità.
    Dal 04/11/2026: `clima` {variabile: {unita, storico, previsione}} con le variabili meteo negli stessi passi, e
    `solo_clima` true per la risposta di GET /api/clima-previsto/{istat} (nessun consumo, nessun quantile). Le tabelle
    mettono consumi e variabili meteo in colonne affiancate (CSV, Excel, ODS); nel PDF i grafici in sequenza, prima i
    consumi e poi le variabili nell'ordine delle opzioni della pagina.
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
    solo = bool(d.get("solo_clima"))
    clima = {k: _diz(v) for k, v in _diz(d.get("clima")).items() if isinstance(k, str)}
    chiavi = _ordine_clima(clima, rq.get("covariate", d.get("covariate")), modalita)
    cl_pr = {k: _lista(clima[k].get("previsione")) for k in chiavi}
    cl_st = {k: _lista(clima[k].get("storico")) for k in chiavi}
    un_cl = {k: str(clima[k].get("unita") or "")[:20] for k in chiavi}
    testa_cl = [_nome_clima(k, modalita) + (f" ({un_cl[k]})" if un_cl[k] else "") for k in chiavi]

    def val(lst, i):
        return _num(lst[i]) if i < len(lst) else None

    # parametri
    voci = [("Comune", comune), ("Codice ISTAT", istat or None),
            ("Modalità", NOMI_MODALITA.get(modalita, modalita or None)),
            ("Orizzonte", f"{n} {passo if n == 1 else {'ora': 'ore', 'giorno': 'giorni'}.get(passo, passo)}" if n else None),
            ("Primo passo previsto", t[0] if t else None), ("Ultimo passo previsto", t[-1] if t else None),
            ("Cosa si prevede", "solo il clima (variabili meteo, senza consumi)" if solo else None),
            ("Tipo di serie", None if solo else {"energia": "energia (somma nel passo)", "potenza": "potenza (media nel passo)"}.get(tipo, tipo or None)),
            ("Unità di misura", None if solo else unita)]
    cov = rq.get("covariate", d.get("covariate"))
    if isinstance(cov, str):
        cov = [c for c in cov.split(",") if c]
    if isinstance(cov, list):
        voci.append(("Variabili meteo" if solo else "Covariate", ", ".join(str(c) for c in cov) or "solo calendario"))
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
    if solo:
        for k, nome in zip(chiavi, testa_cl):
            v = [x for x in (val(cl_pr[k], i) for i in range(n)) if x is not None]
            if v:
                sintesi.append({"chiave": f"{_nome_clima(k, modalita)}: media prevista", "valore": sum(v) / len(v),
                                "unita": un_cl[k] or None, "decimali": 1})
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

    st = _diz(d.get("storico"))
    ts, vs = [str(x) for x in _lista(st.get("t"))], _lista(st.get("v"))

    # grafici in sequenza (solo PDF): prima i consumi, poi le variabili meteo nell'ordine delle opzioni della pagina
    if formato == "pdf" and n:
        tutti = ts + t
        deboli = [i < len(meteo) and str(meteo[i]) in DEBOLI for i in range(n)]
        imm = []
        if not solo and q50:
            linee = [([val(vs, i) for i in range(len(ts))], _COL["inchiostro"], 1.3, None, 0)]
            if reale:
                linee.append(([val(reale, i) for i in range(n)], _COL["serie2"], 1.6, "7 4", len(ts)))
            linee.append(([val(q50, i) for i in range(n)], _COL["serie1"], 2, None, len(ts)))
            bande = [([val(q10, i) for i in range(n)], [val(q90, i) for i in range(n)], _COL["banda1"]),
                     ([val(_lista(pr.get("0.3")), i) for i in range(n)], [val(_lista(pr.get("0.7")), i) for i in range(n)],
                      _COL["banda2"])]
            if not _lista(pr.get("0.3")):
                bande = bande[:1]
            leg = [(_COL["inchiostro"], "dati caricati", "linea"), (_COL["serie1"], "previsione (mediana)", "linea"),
                   (_COL["banda1"], "8 casi su 10", "banda")] + ([(_COL["serie2"], "valori reali", "tratto")] if reale else [])
            g = _immagine_grafico(_svg_serie(tutti, len(ts), linee, bande, deboli, unita, passo, leg),
                                  "Consumi" + (f" ({unita})" if unita else "") + ": dati caricati e previsione")
            if g:
                imm.append(g)
        for k, nome in zip(chiavi, testa_cl):
            linee = [([val(cl_st[k], i) for i in range(len(ts))], _COL["inchiostro"], 1.3, None, 0),
                     ([val(cl_pr[k], i) for i in range(n)], _COL["serie1"], 2, None, len(ts))]
            leg = [(_COL["inchiostro"], "osservato" if solo else "nel periodo dei dati", "linea"),
                   (_COL["serie1"], "previsto", "linea")]
            g = _immagine_grafico(_svg_serie(tutti, len(ts), linee, (), deboli, un_cl[k], passo, leg), nome)
            if g:
                imm.append(g)
        if imm:
            imm = imm[:C.REPORT_MAX_IMMAGINI]
            sezioni.append(Sezione(titolo="Grafici", blocchi=[
                Paragrafo(testo="Prima i consumi, poi le variabili meteo nell'ordine della pagina. La linea tratteggiata "
                                "verticale separa il passato dal futuro; il fondo grigio segna il meteo meno affidabile "
                                "(modello globale o climatologia).")] + imm))

    avvisi = [Avvertenza(testo=str(a)[:2000]) for a in _lista(d.get("avvisi")) if isinstance(a, str) and a.strip()]
    avvisi.append(Avvertenza(livello="info", testo=(
        "Variabili meteo previste per il comune, senza consumi: osservate fino all'ultimo dato disponibile, poi "
        "previste (ICON-2I, ECMWF IFS) e, nel lungo termine, climatologia. Le ore sono in ora italiana." if solo else
        "La previsione è probabilistica: la mediana (P50) è il valore centrale, la banda P10–P90 contiene il valore "
        "reale in circa 8 casi su 10 se il modello è ben calibrato. Le ore sono in ora italiana.")))
    sezioni.append(Sezione(titolo="Avvertenze", blocchi=avvisi))

    # tabelle: consumi e variabili meteo in colonne affiancate
    intest = ["Data e ora" if passo == "ora" else "Giorno"]
    if not solo:
        intest += ["P10", "P50 (mediana)", "P90"] + (["Valore reale"] if reale else [])
    intest += testa_cl + ["Meteo usato"]
    righe = []
    for i in range(n):
        r = [t[i]]
        if not solo:
            r += [val(q10, i), val(q50, i), val(q90, i)] + ([val(reale, i)] if reale else [])
        r += [val(cl_pr[k], i) for k in chiavi]
        r.append(str(meteo[i]) if i < len(meteo) and meteo[i] is not None else None)
        righe.append(r)
    titolo_tab = ("Clima previsto" if solo else "Previsione") + (f" ({unita})" if unita and not solo else "")
    dec_cons = [] if solo else [2, 2, 2] + ([2] if reale else [])
    blocchi = [Tabella(titolo=titolo_tab, intestazioni=intest, righe=righe,
                       decimali=[None] + dec_cons + [2] * len(chiavi) + [None])]
    if ts:
        fst = _lista(d.get("fonte_storico"))
        testa_st = [intest[0]] + ([] if solo else ["Valore"]) + testa_cl + (["Meteo"] if solo else [])
        righe_st = []
        for i in range(len(ts)):
            r = [ts[i]] + ([] if solo else [val(vs, i)]) + [val(cl_st[k], i) for k in chiavi]
            if solo:
                r.append(str(fst[i]) if i < len(fst) and fst[i] is not None else None)
            righe_st.append(r)
        blocchi.append(Tabella(titolo="Ultimi giorni osservati" if solo else "Ultimi dati caricati", intestazioni=testa_st,
                               righe=righe_st,
                               decimali=[None] + ([] if solo else [2]) + [2] * len(chiavi) + ([None] if solo else [])))
    sezioni.append(Sezione(titolo="Dati", blocchi=blocchi))

    if solo:
        return Documento(
            titolo="Previsione del clima",
            sottotitolo=" – ".join(x for x in (comune or (f"Comune ISTAT {istat}" if istat else None),
                                                NOMI_MODALITA.get(modalita)) if x) or None,
            nome_file="_".join(x for x in ("clima_previsto", istat, modalita) if x),
            sezioni=sezioni,
            fonti=_fonti(OPEN_METEO, MODELLI_METEO, ISTAT))
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


def _riga_valori(d: dict, chiavi: list[tuple[str, str, str | None, int]]) -> list[Voce]:
    out = []
    for k, etichetta, unita, dec in chiavi:
        x = _diz(d.get(k))
        v = _num(x.get("valore")) if x else _num(d.get(k))
        if v is None:
            continue
        fonte = _testo(x.get("fonte"), 60) if x else ""
        out.append(Voce(chiave=etichetta + (f" ({fonte})" if fonte else ""), valore=v, unita=unita, decimali=dec))
    return out


def report_edificio(d: dict, formato: str = "pdf", **_) -> Documento:
    """Corpo mandato da fase5-sito/sito/edificio3d.js (pagine Modelli 3D, Geometria, Consumi, Producibilità):
    titolo, edificio {id, nome, comune}, sintetico (bool), superfici {piani_fuori_terra: {valore, fonte}, …},
    geometria {volume_lordo, superficie_disperdente, s_su_v, pareti_per_orientamento {N: m², …}, …},
    corpi [{id, area, gronda, colmo, tetto, fonte_tetto, piani, fonte_sagoma, fonte_altezza, licenza, qualita}],
    tetti {scelta, testo, conteggi {lidar, colmo, ipotesi, piano, …}} (forma dei tetti, 08/11/2026),
    falde [{corpo, falda, pendenza, orientamento, superficie, area_pianta, fonte}] (Fase C),
    firma {base, pendenza, r2, unita, mesi [{mese, consumo, gg20}]}, consumi_normalizzati [{voce, valore, unita}],
    fv {aree [{nome, area, inclinazione, orientamento, moduli, kwp, kwh_anno, perdita_ombre}], totale_kwh, anno_clima},
    immagini [{titolo, svg}] (solo nel PDF), note, fonti. Nessun dato di mercato: le colonne con quei nomi si scartano."""
    d = _diz(d)
    pdf = formato == "pdf"
    sezioni: list[Sezione] = []
    e = _diz(d.get("edificio"))
    primi = []
    if d.get("sintetico"):
        primi.append(Avvertenza(livello="attenzione", testo=(
            "Dati sintetici di esempio: sagome, altezze, terreno e consumi sono inventati per mostrare come funziona la "
            "pagina e non rappresentano edifici reali.")))
    primi.append(Avvertenza(livello="info", testo=(
        "Geometria ricostruita da dati topografici con altezze approssimate (DBTR: circa ±3 m): piani e superfici sono "
        "stime se non sono stati indicati nel file o nelle visure. Non sostituisce un rilievo né una diagnosi energetica.")))
    sezioni.append(Sezione(titolo=None, blocchi=primi))
    voci = [Voce(chiave=k, valore=_testo(e.get(c), 200)) for k, c in (("Edificio", "nome"), ("Codice", "id"), ("Comune", "comune")) if e.get(c)]
    voci += _riga_valori(_diz(d.get("superfici")), [
        ("piani_fuori_terra", "Piani fuori terra", None, 0), ("piani_interrati", "Piani interrati", None, 0),
        ("superficie_lorda", "Superficie lorda", "m²", 0), ("superficie_netta", "Superficie netta", "m²", 0),
        ("superficie_catastale", "Superficie catastale", "m²", 0), ("anno_costruzione", "Anno di costruzione", None, 0)])
    if voci:
        sezioni.append(Sezione(titolo="Edificio, piani e superfici", blocchi=[ChiaveValore(voci=voci[:30])]))
    g = _diz(d.get("geometria"))
    gv = _riga_valori(g, [("volume_lordo", "Volume lordo", "m³", 0), ("superficie_disperdente", "Superficie disperdente", "m²", 0),
                          ("s_su_v", "Rapporto S/V", "m⁻¹", 2), ("superficie_tetti", "Tetti", "m²", 0),
                          ("superficie_pavimento_terra", "Pavimento a terra", "m²", 0), ("pareti_esposte", "Pareti esposte", "m²", 0),
                          ("pareti_in_comune_tra_corpi", "Pareti in comune tra corpi", "m²", 0),
                          ("pareti_in_comune_con_vicini", "Pareti in comune con edifici vicini", "m²", 0)])
    blocchi = [ChiaveValore(voci=gv)] if gv else []
    po = _diz(g.get("pareti_per_orientamento"))
    if po:
        blocchi.append(Tabella(titolo="Pareti esposte per orientamento", intestazioni=["Orientamento", "Superficie (m²)"],
                               righe=[[_testo(k, 4), _num(v)] for k, v in list(po.items())[:8]], decimali=[None, 0]))
    if blocchi:
        sezioni.append(Sezione(titolo="Indicatori geometrici", blocchi=blocchi))
    corpi = [_diz(c) for c in _lista(d.get("corpi"))][:C.REPORT_MAX_RIGHE]
    if corpi:
        sezioni.append(Sezione(titolo="Corpi", blocchi=[Tabella(
            intestazioni=["Corpo", "Area (m²)", "Gronda (m)", "Colmo (m)", "Tetto", "Piani", "Sagoma", "Altezza", "Licenza", "Qualità"],
            righe=[[_testo(c.get("id"), 60), _num(c.get("area")), _num(c.get("gronda")), _num(c.get("colmo")),
                    _testo(c.get("tetto"), 20), _num(c.get("piani")), _testo(c.get("fonte_sagoma"), 80),
                    _testo(c.get("fonte_altezza"), 120), _testo(c.get("licenza"), 20), _testo(c.get("qualita"), 120)] for c in corpi],
            decimali=[None, 0, 1, 1, None, 0, None, None, None, None])] + _blocchi_tetti(d)))
    falde = [_diz(f) for f in _lista(d.get("falde"))][:C.REPORT_MAX_RIGHE]
    if falde:   # fase 10, Fase C: falde misurate dal LiDAR o lette dal modello dell'utente
        sezioni.append(Sezione(titolo="Falde dei tetti", blocchi=[Tabella(
            intestazioni=["Corpo", "Falda", "Pendenza (°)", "Orientamento (°)", "Superficie (m²)", "In pianta (m²)", "Fonte"],
            righe=[[_testo(f.get("corpo"), 60), _testo(f.get("falda"), 12), _num(f.get("pendenza")), _num(f.get("orientamento")),
                    _num(f.get("superficie")), _num(f.get("area_pianta")), _testo(f.get("fonte"), 160)] for f in falde],
            decimali=[None, None, 1, 0, 0, 0, None]),
            Paragrafo(testo="Falde ricavate dal rilievo LiDAR (punti del DSM dentro il corpo, piano, capanna o padiglione ai minimi "
                            "quadrati), dal modello dell'utente, stimate dal colmo del DB topografico o ipotizzate (22° in pianura, "
                            "32° in montagna; a capanna sul lato lungo o a padiglione), come dice la colonna «Fonte»; orientamento "
                            "in gradi da nord in senso orario (180 = sud), vuoto per i tetti piani.")]))
    cn = [x for x in map(_diz, _lista(d.get("consumi_normalizzati"))) if _ammessa(x.get("voce", "")) and _ammessa(x.get("unita", ""))]
    if cn:
        sezioni.append(Sezione(titolo="Consumi normalizzati", blocchi=[Tabella(
            intestazioni=["Voce", "Valore", "Unità"], righe=[[_testo(x.get("voce")), _num(x.get("valore")), _testo(x.get("unita"), 40)] for x in cn[:50]],
            decimali=[None, 2, None])]))
    f = _diz(d.get("firma"))
    if f.get("mesi"):
        u = _testo(f.get("unita"), 20)
        bl = [ChiaveValore(voci=[v for v in (
            Voce(chiave="Carico di base (gradi giorno = 0)", valore=_num(f.get("base")), unita=f"{u}/mese", decimali=0),
            Voce(chiave="Sensibilità al clima", valore=_num(f.get("pendenza")), unita=f"{u}/(°C·giorno)", decimali=2),
            Voce(chiave="R²", valore=_num(f.get("r2")), decimali=2)) if v.valore is not None])]
        bl.append(Tabella(titolo="Consumi mensili e gradi giorno reali", intestazioni=["Mese", f"Consumo ({u})", "Gradi giorno (20 °C)", "Atteso dalla firma"],
                          righe=[[_testo(m.get("mese"), 10), _num(m.get("consumo")), _num(m.get("gg20")), _num(m.get("atteso"))]
                                 for m in map(_diz, _lista(f.get("mesi")))][:240], decimali=[None, 0, 0, 0]))
        bl.append(Paragrafo(testo="Firma energetica: retta dei minimi quadrati tra consumo mensile e gradi giorno reali del "
                                   "comune (base 20 °C, archivio meteo di EuGEnio)."))
        sezioni.append(Sezione(titolo="Firma energetica", blocchi=bl))
    fv = _diz(d.get("fv"))
    if fv.get("aree"):
        sezioni.append(Sezione(titolo="Fotovoltaico sui tetti", blocchi=[Tabella(
            intestazioni=["Area", "Superficie (m²)", "Inclinazione (°)", "Orientamento (°)", "Moduli", "Potenza (kWp)",
                          "Producibilità (kWh/anno)", "Perdita per ombre (%)"],
            righe=[[_testo(a.get("nome"), 60), _num(a.get("area")), _num(a.get("inclinazione")), _num(a.get("orientamento")),
                    _num(a.get("moduli")), _num(a.get("kwp")), _num(a.get("kwh_anno")), _num(a.get("perdita_ombre"))]
                   for a in map(_diz, _lista(fv.get("aree")))][:200], decimali=[None, 1, 0, 0, 0, 2, 0, 1]),
            Paragrafo(testo=f"Totale: {_num(fv.get('totale_kwh')) or 0:,.0f} kWh/anno".replace(",", ".")
                      + (f" con il clima orario del {_testo(fv.get('anno_clima'), 10)}." if fv.get("anno_clima") else ".")
                      + f" Modello semplificato (trasposizione {_modello_cielo(fv)}, perdite di sistema 14 %, temperatura delle celle)"
                        "; orientamento in gradi da nord in senso orario (180 = sud).")]))
    sezioni += _sezioni_fase_b(d)
    fonti_ortofoto: list[Fonte] = []
    if pdf:
        imm = [i for i in (_immagine_svg(x, "Figura") for x in _lista(d.get("immagini"))[:C.REPORT_MAX_IMMAGINI]) if i]
        for x in _lista(d.get("immagini_png"))[:max(0, C.REPORT_MAX_IMMAGINI - len(imm))]:
            i, f = _immagine_ortofoto(x)
            if i is not None:
                imm.append(i)
                fonti_ortofoto.append(f)
        if imm:
            sezioni.append(Sezione(titolo="Figure", blocchi=imm))
    note = [_testo(x, 2000) for x in _lista(d.get("note")) if isinstance(x, str) and x.strip()][:10]
    if note:
        sezioni.append(Sezione(titolo="Note", blocchi=[Elenco(voci=note)]))
    return Documento(titolo=_testo(d.get("titolo")) or "Edificio in 3D", sottotitolo=_testo(e.get("nome")) or None,
                     nome_file="edificio", sezioni=sezioni[:C.REPORT_MAX_SEZIONI],
                     fonti=_fonti(OPEN_METEO, *fonti_ortofoto, extra=d.get("fonti")))


NOMI_FONTE_TETTO = {"lidar": "misurato dal LiDAR", "colmo": "stimato dal colmo DBTR", "ipotesi": "ipotizzato (22°/32°)",
                    "piano": "piano", "modello": "dal modello dell'utente", "utente": "corretto a mano"}


def _blocchi_tetti(d: dict) -> list:
    """Forma dei tetti (08/11/2026): scelta (cascata in Modelli 3D, scelta dell'utente nelle pagine Edificio e Fotovoltaico)
    e corpi per fonte; testo ripulito, solo numeri interi nei conteggi."""
    t = _diz(d.get("tetti"))
    if not t:
        return []
    voci = [Voce(chiave="Forma dei tetti", valore=_testo(t.get("scelta"), 120))] if t.get("scelta") else []
    n = _diz(t.get("conteggi"))
    for k, nome in NOMI_FONTE_TETTO.items():
        v = _num(n.get(k))
        if v:
            voci.append(Voce(chiave=f"Corpi con il tetto {nome}", valore=v, decimali=0))
    out = [ChiaveValore(voci=voci[:10])] if voci else []
    if t.get("testo"):
        out.append(Paragrafo(testo=_testo(t.get("testo"), 600)))
    return out


def _immagine_ortofoto(x) -> tuple[Immagine | None, Fonte | None]:
    """{titolo, png (base64), ortofoto {id, licenza, citazione, scheda}} → immagine con licenza e citazione nella
    didascalia. Regola del § 6: ogni figura con ortofoto porta licenza e citazione; senza, la figura non entra. Le fonti
    «solo dal vivo» (Geoportale Nazionale) non entrano mai nei report."""
    x = _diz(x)
    o = _diz(x.get("ortofoto"))
    cit, lic = _testo(o.get("citazione"), 400).strip(), _testo(o.get("licenza"), 80).strip()
    if not (cit and lic) or _testo(o.get("id"), 40) in _ORTOFOTO_SOLO_DAL_VIVO or not isinstance(x.get("png"), str):
        return None, None
    titolo = _testo(x.get("titolo"), 200).split(". ")[0] or "Vista dell'edificio con l'ortofoto"
    sp = testo_spostamento(o.get("de"), o.get("dn"))
    sp = f" {sp}." if sp else ""
    try:
        i = Immagine(formato="png", dati=x["png"], didascalia=f"{titolo}. Ortofoto: {cit} – licenza {lic}."[:300 - len(sp)] + sp,
                     larghezza_cm=17)
    except ValidationError:
        return None, None
    url = o.get("scheda") if isinstance(o.get("scheda"), str) and re.match(r"^https?://\S+$", o["scheda"]) else None
    return i, Fonte(testo=f"Ortofoto: {cit}", url=url)


_ORTOFOTO_SOLO_DAL_VIVO = {"pcn2012"}


def testo_spostamento(de, dn) -> str:
    """(08/11/2026) «Ortofoto spostata manualmente di 2 m E, 1 m S rispetto alla cartografia» (frecce sotto la mappa);
    vuoto se lo spostamento è nullo o non valido (interi da -20 a 20, come il proxy)."""
    def m(v):
        try:
            v = int(v)
        except (TypeError, ValueError):
            return 0
        return v if -20 <= v <= 20 else 0
    de, dn = m(de), m(dn)
    parti = ([f"{abs(de)} m {'E' if de > 0 else 'O'}"] if de else []) + ([f"{abs(dn)} m {'N' if dn > 0 else 'S'}"] if dn else [])
    return f"Ortofoto spostata manualmente di {', '.join(parti)} rispetto alla cartografia" if parti else ""


def _sezioni_fase_b(d: dict) -> list[Sezione]:
    """Obblighi di legge, sole sulle facciate, orizzonte lontano, confronto PVGIS e classifica di priorità (Fase B)."""
    out: list[Sezione] = []
    o = _diz(d.get("obblighi"))
    righe = [x for x in map(_diz, _lista(o.get("righe")))][:30]
    if righe:
        out.append(Sezione(titolo="Obblighi di legge", blocchi=[
            Paragrafo(testo=f"Intervento: {_testo(o.get('intervento'), 80)}" + ("; edificio pubblico." if o.get("pubblico") else ".")),
            Tabella(intestazioni=["Voce", "Valore", "Riferimento"],
                    righe=[[_testo(r.get("voce"), 200), _testo(r.get("valore"), 200), _testo(r.get("riferimento"), 200)] for r in righe]),
            Paragrafo(testo="Potenza minima: D.Lgs. 199/2021, Allegato III, sezione B, punto 3 (P = k · S, k = 0,025 per gli "
                            "edifici esistenti e 0,05 per i nuovi; S = superficie in pianta dell'edificio al livello del terreno) "
                            "e punto 5 (edifici pubblici: +10 % e +5 punti). Le quote del punto 1 si verificano sui consumi del "
                            "progetto. H'T: DM 26/6/2015, Allegato 1, Appendice A, Tabella 10, nel testo del DM 28/10/2025. "
                            "Promemoria, non sostituisce la relazione tecnica del progettista (art. 26, comma 5).")]))
    f = _diz(d.get("facciate"))
    po = [x for x in map(_diz, _lista(f.get("per_orientamento")))][:8]
    if po:
        bl = [Tabella(intestazioni=["Orientamento", "Esposta (m²)", "kWh/m² anno", "kWh anno", "Estate giu–ago (kWh)",
                                    "Inverno dic–feb (kWh)", "Perdita per ombre (%)"],
                      righe=[[_testo(x.get("orientamento"), 4), _num(x.get("area")), _num(x.get("kwh_m2")), _num(x.get("kwh")),
                              _num(x.get("estate")), _num(x.get("inverno")), _num(x.get("perdita"))] for x in po],
                      decimali=[None, 0, 0, 0, 0, 0, 1])]
        bl.append(Paragrafo(testo=f"Sole sulle sole parti esposte delle facciate, in {int(_num(f.get('parti')) or 0)} pezzi di circa "
                                  "4 × 3 m (le parti in comune con altri corpi o con edifici confinanti non ricevono sole), con "
                                  "le ombre degli edifici entro 250 m" + (" e l'orizzonte del terreno" if f.get("orizzonte_lontano") else "")
                                  + (f"; clima orario del {_testo(f.get('anno_clima'), 10)}." if f.get("anno_clima") else ".")
                                  + f" Irradiazione sul piano verticale, trasposizione {_modello_cielo(f)}."))
        out.append(Sezione(titolo="Sole sulle facciate", blocchi=bl))
    z = _diz(d.get("orizzonte_lontano"))
    if _num(z.get("massimo")) is not None:
        it = lambda v, d=1: f"{v:.{d}f}".replace(".", ",")
        out.append(Sezione(titolo="Orizzonte lontano", blocchi=[Paragrafo(testo=(
            f"Orizzonte del terreno fino a {it(_num(z.get('raggio')) or 25, 0)} km dal Copernicus DEM 90 m: angolo massimo "
            f"{it(_num(z.get('massimo')))}°; quota del terreno nel punto {it(_num(z.get('quota')) or 0, 0)} m. Unito, direzione "
            "per direzione, all'orizzonte degli edifici vicini."))]))
    p = _diz(d.get("pvgis"))
    pa = [x for x in map(_diz, _lista(p.get("aree")))][:50]
    if pa:
        def diff(x):
            e, v = _num(x.get("eugenio_kwh")), _num(x.get("pvgis_kwh"))
            return 100 * (e - v) / v if e is not None and v else None
        out.append(Sezione(titolo="Confronto con PVGIS", blocchi=[
            Tabella(intestazioni=["Area", "EuGEnio (kWh/anno)", "PVGIS con orizzonte", "PVGIS senza", "Differenza (%)", "Dati PVGIS"],
                    righe=[[_testo(x.get("id"), 40), _num(x.get("eugenio_kwh")), _num(x.get("pvgis_kwh")), _num(x.get("pvgis_senza_kwh")),
                            diff(x), f"{_testo(x.get('banca_dati'), 30)} {'–'.join(str(int(a)) for a in _lista(x.get('anni')) if isinstance(a, (int, float)))}"]
                           for x in pa], decimali=[None, 0, 0, 0, 1, None]),
            Paragrafo(testo="PVGIS chiamato dal server di EuGEnio con l'orizzonte calcolato da EuGEnio (userhorizon) e senza; "
                            "PVGIS usa i suoi dati di radiazione, non il clima orario di EuGEnio.")]))
    pr = _diz(d.get("priorita"))
    sedi = [x for x in map(_diz, _lista(pr.get("sedi")))][:C.REPORT_MAX_RIGHE]
    if sedi:
        crit = ["intensita", "sensibilita", "base", "costo", "fv"]
        pesi = _diz(pr.get("pesi"))
        out.append(Sezione(titolo="Classifica di priorità del patrimonio", blocchi=[
            Tabella(intestazioni=["Posto", "Sede", "Punteggio", "Consumo/m²", "Sensibilità", "Carico di base", "Costo/m²", "FV/m²", "kWh/m²"],
                    righe=[[_num(x.get("posto")), _testo(x.get("nome"), 80), _num(x.get("punteggio"))]
                           + [_num(_diz(x.get("punteggi")).get(k)) for k in crit] + [_num(x.get("kwh_m2"))] for x in sedi],
                    decimali=[0, None, 0, 0, 0, 0, 0, 0, 0]),
            Paragrafo(testo="Punteggi da 0 a 100 per criterio (rango della sede tra quelle in classifica), poi media pesata dei "
                            "criteri disponibili; pesi: " + ", ".join(f"{k} {(_num(pesi.get(k)) or 0):.2f}".replace(".", ",") for k in crit)
                            + ". Più alto = intervenire prima. Costi inseriti dall'utente (bollette o convenzioni); nessun prezzo "
                              "di borsa.")]))
    return out


TIPI: dict[str, Callable[..., Documento]] = {
    "previsione": report_previsione,
    "legge10": report_legge10,
    "patrimonio": report_patrimonio,
    "indicatori": report_indicatori,
    "valori_sedi": report_valori_sedi,
    "edificio": report_edificio,
}
# tipi che ricevono anche il formato (per esempio per lasciare le immagini fuori da Excel e ODS)
CON_FORMATO = {"valori_sedi", "edificio", "previsione"}   # previsione: i grafici solo nel PDF (04/11/2026)
