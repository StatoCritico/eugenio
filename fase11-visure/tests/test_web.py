"""Pagina locale di EuGEnio Visure: modulo, gettone, controllo dell'Host, lettura, download."""
import http.client
import io
import re
import threading
import uuid
import zipfile

import pytest

from visure.web import crea_server


@pytest.fixture()
def server():
    srv, st = crea_server("127.0.0.1", 0)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield srv.server_address[1], st
    srv.shutdown()
    srv.server_close()


def chiedi(porta, metodo, percorso, corpo=None, intest=None):
    c = http.client.HTTPConnection("127.0.0.1", porta, timeout=20)
    c.request(metodo, percorso, body=corpo, headers=intest or {})
    r = c.getresponse()
    return r.status, dict(r.getheaders()), r.read()


def multipart(campi):
    b = uuid.uuid4().hex
    out = io.BytesIO()
    for nome, fn, dati in campi:
        out.write(f"--{b}\r\n".encode())
        disp = f'form-data; name="{nome}"' + (f'; filename="{fn}"' if fn else "")
        out.write(f"Content-Disposition: {disp}\r\n".encode())
        if fn:
            out.write(b"Content-Type: application/octet-stream\r\n")
        out.write(b"\r\n" + dati + b"\r\n")
    out.write(f"--{b}--\r\n".encode())
    return out.getvalue(), f"multipart/form-data; boundary={b}"


def test_modulo_e_intestazioni(server):
    porta, st = server
    s, h, corpo = chiedi(porta, "GET", "/")
    assert s == 200 and st.gettone.encode() in corpo
    assert "default-src 'self'" in h["Content-Security-Policy"]
    assert b"http" not in re.sub(rb"https?://[^\"' <]*(127\.0\.0\.1|localhost)", b"", corpo.split(b"<style>")[0])


def test_host_estraneo_rifiutato(server):
    porta, _ = server
    s, _, _ = chiedi(porta, "GET", "/", intest={"Host": "attaccante.example:8770"})
    assert s == 403


def test_lettura_e_download(server, sintetici):
    porta, st = server
    campi = [("gettone", None, st.gettone.encode())]
    for n in ("visura_immobile_A2_attuale.pdf", "visura_soggetto_tabella.pdf"):
        campi.append(("pdf", n, (sintetici / n).read_bytes()))
    campi.append(("patrimonio", "p.csv", (sintetici / "patrimonio_esempio_visure.csv").read_bytes()))
    corpo, tipo = multipart(campi)
    s, h, _ = chiedi(porta, "POST", "/leggi", corpo, {"Content-Type": tipo})
    assert s == 303
    s, _, pag = chiedi(porta, "GET", h["Location"])
    assert s == 200 and "7 unità".encode() in pag
    lid = h["Location"].rsplit("/", 1)[1]
    s, h2, z = chiedi(porta, "GET", f"/scarica/{lid}/visure.zip")
    assert s == 200 and h2["Content-Type"] == "application/zip"
    nomi = zipfile.ZipFile(io.BytesIO(z)).namelist()
    assert "patrimonio_con_visure.csv" in nomi and "indice.csv" in nomi
    assert not any("PERSONALI" in n for n in nomi)
    assert any(n.startswith("pdf/RIMINI_H294/") for n in nomi)
    s, _, csv = chiedi(porta, "GET", f"/scarica/{lid}/indice.csv")
    assert s == 200 and b"PRVLCU75B41H294K" not in csv
    s, _, _ = chiedi(porta, "GET", f"/scarica/{lid}/..%2F..%2Fetc%2Fpasswd")
    assert s == 404


def test_gettone_sbagliato(server, sintetici):
    porta, _ = server
    corpo, tipo = multipart([("gettone", None, b"sbagliato"),
                             ("pdf", "a.pdf", (sintetici / "visura_immobile_A2_attuale.pdf").read_bytes())])
    s, _, _ = chiedi(porta, "POST", "/leggi", corpo, {"Content-Type": tipo})
    assert s == 403
