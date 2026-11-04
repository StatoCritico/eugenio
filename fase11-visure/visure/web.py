"""Pagina locale di EuGEnio Visure: si apre nel browser del PC, su http://127.0.0.1:8770 (solo libreria standard).

Si scelgono i PDF delle visure (e, se si vuole, il CSV di Patrimonio), il programma li legge sul PC e propone i file
da scaricare. Dal 04/11/2026 la scheda «Modelli DXF/IFC» converte i modelli pesanti in GeoJSON per la pagina Modelli 3D
(visure/modelli.py). Niente esce dal PC: la pagina non carica nulla da Internet (Content-Security-Policy «self») e il
programma non apre connessioni. Protezioni per un servizio locale: ascolto su 127.0.0.1 (Docker: 0.0.0.0 dentro il
container, porta pubblicata solo su 127.0.0.1), controllo dell'intestazione Host (contro il DNS rebinding), gettone
casuale nel modulo (contro le richieste da altri siti), limite di dimensione, risultati cancellati alla chiusura.
"""
from __future__ import annotations

import html
import io
import secrets
import shutil
import tempfile
import threading
import time
import webbrowser
import zipfile
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

from . import VERSIONE
from .lettore import leggi_pdf
from .regole import carica
from .uscite import AVVERTENZA, leggi_csv, scrivi

MAX_CORPO = 400 * 1024 * 1024
DURATA = 4 * 3600          # i risultati restano al massimo 4 ore
STILE = """body{font:15px/1.5 system-ui,sans-serif;margin:0;background:#16181d;color:#e8e6e3}
main{max-width:980px;margin:0 auto;padding:24px 16px}h1{font-size:1.5rem;margin:.2rem 0}
a{color:#ff9478}.riquadro{border:1px solid #3a3f4a;border-radius:8px;padding:16px;margin:16px 0}
label{display:block;margin:.6rem 0}.avviso{border-left:4px solid #ffb547;padding:8px 12px;background:#2a2620}
.errore{border-left-color:#ff6b6b}button{font:inherit;padding:.5rem 1.1rem;border-radius:6px;border:0;
background:#ff7a59;color:#16181d;font-weight:600;cursor:pointer}table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border-bottom:1px solid #3a3f4a;padding:4px 6px;text-align:left;vertical-align:top}.scorre{overflow-x:auto}
code{background:#262a33;padding:0 4px;border-radius:4px}.schede{margin:.4rem 0 1rem;font-weight:600}
input:not([type]){font:inherit;padding:.3rem .5rem;border-radius:6px;border:1px solid #3a3f4a;background:transparent;color:inherit}@media (prefers-color-scheme:light){body{background:#fff;color:#1d1d1f}
.riquadro{border-color:#ccc}.avviso{background:#fff6e5}th,td{border-color:#ddd}code{background:#eee}a{color:#1A3F8F}}"""


MAX_MODELLO = 520 * 1024 * 1024    # con «file molto grande» il convertitore accetta fino a 500 MB


def _pagina(titolo: str, corpo: str) -> bytes:
    schede = "<nav class='schede'><a href='/'>Visure catastali</a> · <a href='/modelli'>Modelli DXF/IFC</a></nav>"
    return (f"<!doctype html><html lang='it'><head><meta charset='utf-8'><meta name='viewport' "
            f"content='width=device-width,initial-scale=1'><title>{html.escape(titolo)}</title><style>{STILE}</style>"
            f"</head><body><main><p>EuGEnio Visure {VERSIONE} · tutto resta su questo computer</p>{schede}{corpo}</main></body></html>"
            ).encode("utf-8")


class Stato:
    def __init__(self, regole=None):
        self.gettone = secrets.token_urlsafe(24)
        self.radice = Path(tempfile.mkdtemp(prefix="eugenio_visure_"))
        self.lavori: dict[str, dict] = {}
        self.regole = carica(regole)
        self.blocco = threading.Lock()

    def pulisci(self):
        ora = time.time()
        with self.blocco:
            for k in [k for k, v in self.lavori.items() if ora - v["ora"] > DURATA]:
                shutil.rmtree(self.lavori.pop(k)["cartella"], ignore_errors=True)


def modulo(st: Stato) -> bytes:
    return _pagina("EuGEnio Visure", f"""
<h1>Leggi le visure catastali</h1>
<p>Scegli i PDF delle visure (per immobile o per soggetto, fabbricati e terreni). Il programma ne legge foglio,
particella, subalterno, categoria, classe, consistenza, superficie, rendita, indirizzo e piani e prepara un CSV per la
pagina Patrimonio di EuGEnio. Non si collega a SISTER né ad altri servizi: lavora solo sui file che scegli.</p>
<p class="avviso">{html.escape(AVVERTENZA)}</p>
<form class="riquadro" method="post" action="/leggi" enctype="multipart/form-data">
<input type="hidden" name="gettone" value="{st.gettone}">
<label>PDF delle visure (anche molti insieme)<br><input type="file" name="pdf" accept=".pdf,application/pdf" multiple required></label>
<label>Facoltativo: il CSV di Patrimonio (quello caricato nella pagina o il risultato scaricato) da arricchire<br>
<input type="file" name="patrimonio" accept=".csv,.txt"></label>
<label><input type="checkbox" name="intestatari" value="1"> Salva a parte anche intestatari e codici fiscali
(<b>dati personali</b>: il file <code>intestatari_DATI_PERSONALI.csv</code> è solo per uso tuo, non caricarlo su
EuGEnio né altrove)</label>
<button type="submit">Leggi le visure</button>
</form>
<p>Poi, nella pagina <b>Patrimonio</b> di EuGEnio, carica <code>indice.csv</code>, <code>patrimonio_con_visure.csv</code> o
<code>visure.json</code> nel passo «Visure catastali»: l'abbinamento agli edifici si fa nel tuo browser e le colonne
delle visure non vanno al server.</p>""")


def pagina_modelli(st: Stato) -> bytes:
    from .modelli import disponibile
    ok, msg = disponibile()
    if not ok:
        return _pagina("EuGEnio Visure – modelli", f"""<h1>Modelli DXF/IFC</h1>
<p class="avviso errore">La conversione dei modelli non c'è in questa installazione ({html.escape(msg)}). Usa
l'.exe di EuGEnio Visure, l'immagine Docker o <code>pip install ezdxf ifcopenshell shapely pyproj numpy</code>.</p>""")
    return _pagina("EuGEnio Visure – modelli", f"""
<h1>Converti un modello DXF o IFC</h1>
<p>Per i file troppo pesanti per la pagina «Importa DXF/IFC» del sito (oltre 30–50 MB o molto complessi). Il programma
ricava corpi, altezze e falde dei tetti <b>su questo computer</b>, con lo stesso codice della pagina e del comando
<code>importa-modello</code>, e ti fa scaricare <code>modello.geojson</code> da aprire nella pagina «Importa DXF/IFC» o
«Modelli 3D» di EuGEnio (lo legge solo il browser).</p>
<form class="riquadro" method="post" action="/modello" enctype="multipart/form-data">
<input type="hidden" name="gettone" value="{st.gettone}">
<label>Disegno o modello (.dxf, .ifc)<br><input type="file" name="file" accept=".dxf,.ifc" required></label>
<p><b>Posizione</b> (solo se il file non è georeferenziato; gli IFC con IfcMapConversion o IfcSite si posizionano da soli):</p>
<label>Sistema di riferimento delle coordinate del disegno (es. <code>EPSG:7791</code>, <code>EPSG:3003</code>)<br>
<input name="crs" placeholder="EPSG:7791"></label>
<label>oppure due punti noti, nella forma <code>X,Y=LON,LAT</code> (X e Y nelle unità del disegno)<br>
<input name="posa1" placeholder="0,0=12.5665,44.0600" size="32"> <input name="posa2" placeholder="10,0=12.56663,44.0600" size="32"></label>
<label>Unità del disegno (solo DXF senza $INSUNITS): metri per unità<br><input name="unita" placeholder="1 (metri), 0.001 (mm)"></label>
<label><input type="checkbox" name="grande" value="1"> File molto grande (fino a 500 MB, 8 GB di memoria, 30 minuti)</label>
<button type="submit">Converti</button>
</form>
<p>Da riga di comando: <code>EuGEnioVisure.exe modello edificio.ifc --uscita modello.geojson</code> (con
<code>--crs</code>, <code>--posa</code>, <code>--unita</code>, <code>--grande</code>).</p>""")


def converti_modello(campi: dict) -> tuple[int, bytes, str, dict]:
    """(codice, corpo, tipo, intestazioni) della conversione: GeoJSON da scaricare o pagina con l'errore."""
    import json
    from .modelli import converti, errore_modello
    testo = lambda k: (campi.get(k) or [(None, b"")])[0][1].decode("utf-8", errors="ignore").strip()  # noqa: E731
    fn, dati = (campi.get("file") or [(None, b"")])[0]
    nome = Path(fn or "modello").name
    if not dati or Path(nome).suffix.lower() not in (".dxf", ".ifc"):
        return 400, _pagina("Modello", "<p class='avviso errore'>Scegli un file .dxf o .ifc. <a href='/modelli'>Indietro</a></p>"), \
            "text/html; charset=utf-8", {}
    posa = [x for x in (testo("posa1"), testo("posa2")) if x] or None
    try:
        unita = float(testo("unita").replace(",", ".")) if testo("unita") else None
    except ValueError:
        unita = None
    with tempfile.TemporaryDirectory(prefix="eugenio_modello_") as d:
        p = Path(d) / nome
        p.write_bytes(dati)
        try:
            r = converti(p, posa=posa, crs=testo("crs") or None, unita=unita, grande=bool(testo("grande")))
        except Exception as e:  # noqa: BLE001
            m = errore_modello(e)
            if m is None:
                m = f"errore inatteso ({type(e).__name__})"
            return 422, _pagina("Modello non convertito", f"<p class='avviso errore'>Modello non convertito: "
                                f"{html.escape(m)}.</p><p><a href='/modelli'>Indietro</a></p>"), "text/html; charset=utf-8", {}
    uscita = Path(nome).stem.replace('"', "") + ".geojson"
    return 200, json.dumps(r, ensure_ascii=False).encode("utf-8"), "application/geo+json", \
        {"Content-Disposition": f'attachment; filename="{uscita}"'}


def risultato_html(st: Stato, lid: str) -> bytes:
    lav = st.lavori[lid]
    ris, cart = lav["ris"], lav["cartella"]
    files = sorted(p.name for p in cart.iterdir() if p.is_file())
    link = "".join(f"<li><a href='/scarica/{lid}/{quote(n)}'>{html.escape(n)}</a>"
                   + (" – <b>dati personali</b>" if "PERSONALI" in n else "") + "</li>" for n in files)
    righe = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(u.get(k) if u.get(k) is not None else ''))}</td>" for k in
                         ("file", "comune", "foglio", "particella", "subalterno", "categoria", "consistenza",
                          "unita_consistenza", "superficie_catastale", "rendita_euro", "piani", "esito", "nota")) + "</tr>"
        for u in ris["unita"])
    reg = html.escape((cart / "registro.txt").read_text(encoding="utf-8"))
    return _pagina("EuGEnio Visure – risultato", f"""
<h1>Risultato</h1>
<p>{len(ris['unita'])} unità da {len(lav['nomi'])} PDF; {len(ris['edifici'])} edifici.</p>
<div class="riquadro"><b>Scarica</b><ul><li><a href='/scarica/{lid}/visure.zip'>tutto in uno zip</a></li>{link}</ul></div>
<div class="scorre"><table><tr><th>File</th><th>Comune</th><th>Foglio</th><th>Particella</th><th>Sub</th><th>Cat.</th>
<th>Consistenza</th><th></th><th>Sup. (m²)</th><th>Rendita (€)</th><th>Piani</th><th>Esito</th><th>Nota</th></tr>{righe}</table></div>
<h2>Registro</h2><pre style="white-space:pre-wrap">{reg}</pre>
<p><a href="/">Leggi altre visure</a></p>""")


def gestore(st: Stato, host_ammessi: set[str]):
    class G(BaseHTTPRequestHandler):
        server_version = "EuGEnioVisure"

        def log_message(self, *a):        # nessun registro con i nomi dei file sulla console
            pass

        def _host_ok(self) -> bool:
            h = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]").lower()
            return h in host_ammessi

        def _manda(self, codice: int, corpo: bytes, tipo="text/html; charset=utf-8", extra: dict | None = None):
            self.send_response(codice)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; form-action 'self'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(corpo)

        def do_GET(self):  # noqa: N802
            if not self._host_ok():
                return self._manda(403, b"host non ammesso", "text/plain")
            st.pulisci()
            if self.path in ("/", "/index.html"):
                return self._manda(200, modulo(st))
            if self.path == "/modelli":
                return self._manda(200, pagina_modelli(st))
            if self.path == "/salute":
                return self._manda(200, b'{"stato":"ok"}', "application/json")
            parti = self.path.split("/")
            if len(parti) == 3 and parti[1] == "risultato" and parti[2] in st.lavori:
                return self._manda(200, risultato_html(st, parti[2]))
            if len(parti) == 4 and parti[1] == "scarica" and parti[2] in st.lavori:
                cart = st.lavori[parti[2]]["cartella"]
                nome = Path(parti[3]).name
                if nome == "visure.zip":
                    buf = io.BytesIO()
                    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                        for p in sorted(cart.rglob("*")):
                            if p.is_file():
                                z.write(p, p.relative_to(cart).as_posix())
                    corpo, tipo = buf.getvalue(), "application/zip"
                else:
                    p = cart / nome
                    if not p.is_file():
                        return self._manda(404, b"non trovato", "text/plain")
                    corpo = p.read_bytes()
                    tipo = {"csv": "text/csv; charset=utf-8", "json": "application/json",
                            "txt": "text/plain; charset=utf-8"}.get(nome.rsplit(".", 1)[-1], "application/octet-stream")
                return self._manda(200, corpo, tipo, {"Content-Disposition": f'attachment; filename="{nome}"'})
            return self._manda(404, b"non trovato", "text/plain")

        def do_POST(self):  # noqa: N802
            if not self._host_ok() or self.path not in ("/leggi", "/modello"):
                return self._manda(403, b"non ammesso", "text/plain")
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0 or n > (MAX_MODELLO if self.path == "/modello" else MAX_CORPO):
                return self._manda(413, _pagina("Troppo grande", "<p class='avviso errore'>File troppo grandi: "
                                                "dividi le visure in più gruppi.</p>"))
            corpo = self.rfile.read(n)
            msg = BytesParser(policy=policy.HTTP).parsebytes(
                b"Content-Type: " + (self.headers.get("Content-Type") or "").encode() + b"\r\n\r\n" + corpo)
            campi: dict[str, list] = {}
            for parte in msg.iter_parts():
                nome = parte.get_param("name", header="content-disposition")
                campi.setdefault(nome, []).append((parte.get_filename(), parte.get_payload(decode=True) or b""))
            if not campi.get("gettone") or campi["gettone"][0][1].decode(errors="ignore") != st.gettone:
                return self._manda(403, _pagina("Non ammesso", "<p class='avviso errore'>Modulo scaduto: "
                                                "<a href='/'>ricarica la pagina</a>.</p>"))
            if self.path == "/modello":
                return self._manda(*converti_modello(campi))
            lid = secrets.token_urlsafe(12)
            cart = st.radice / lid
            ingresso = cart / "_ingresso"
            ingresso.mkdir(parents=True)
            includi = bool(campi.get("intestatari"))
            visure, sorgenti, nomi = [], {}, []
            for i, (fn, dati) in enumerate(campi.get("pdf", [])):
                if not dati:
                    continue
                nome = Path(fn or f"visura_{i + 1}.pdf").name
                if nome in sorgenti:
                    nome = f"{i + 1}_{nome}"
                p = ingresso / nome
                p.write_bytes(dati)
                sorgenti[nome] = p
                nomi.append(nome)
                visure.append(leggi_pdf(p, st.regole, includi_intestatari=includi))
            if not visure:
                shutil.rmtree(cart, ignore_errors=True)
                return self._manda(400, _pagina("Nessun PDF", "<p class='avviso errore'>Nessun PDF ricevuto. "
                                                "<a href='/'>Indietro</a></p>"))
            patrimonio = colonne = None
            if campi.get("patrimonio") and campi["patrimonio"][0][1]:
                patrimonio = leggi_csv(campi["patrimonio"][0][1])
                colonne = list(patrimonio[0]) if patrimonio else []
            ris = scrivi(cart / "risultati", visure, patrimonio, colonne, includi, sorgenti, ordina=True)
            shutil.rmtree(ingresso, ignore_errors=True)
            with st.blocco:
                st.lavori[lid] = {"ris": ris, "cartella": cart / "risultati", "nomi": nomi, "ora": time.time()}
            self.send_response(303)
            self.send_header("Location", f"/risultato/{lid}")
            self.send_header("Content-Length", "0")
            self.end_headers()
    return G


def crea_server(host: str = "127.0.0.1", porta: int = 8770, regole=None) -> tuple[ThreadingHTTPServer, Stato]:
    st = Stato(regole)
    ammessi = {"127.0.0.1", "localhost", "::1"}
    if host not in ("127.0.0.1", "localhost", "::1"):
        ammessi.add(host)     # in Docker si arriva comunque da 127.0.0.1 del PC (porta pubblicata solo lì)
    srv = ThreadingHTTPServer((host, porta), gestore(st, ammessi))
    return srv, st


def avvia(host: str = "127.0.0.1", porta: int = 8770, apri: bool = True, regole=None) -> None:
    srv, st = crea_server(host, porta, regole)
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    print(f"EuGEnio Visure {VERSIONE}: apri {url} (Ctrl+C per chiudere)")
    if apri:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        shutil.rmtree(st.radice, ignore_errors=True)
