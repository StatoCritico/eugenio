"""Scarica una volta i caratteri (licenza SIL OFL) e li salva in sito/font, con font.css.
Così il sito non fa richieste a Google Fonts dai browser dei visitatori (privacy/GDPR)."""
import re
import urllib.request
from pathlib import Path

CSS = ("https://fonts.googleapis.com/css2?family=Hanken+Grotesk:ital,wght@0,400;0,700;1,400"
       "&family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&display=swap")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"  # per avere woff2
dest = Path("sito/font")
dest.mkdir(parents=True, exist_ok=True)
css = urllib.request.urlopen(urllib.request.Request(CSS, headers={"User-Agent": UA})).read().decode()
for i, url in enumerate(sorted(set(re.findall(r"url\((https://[^)]+\.woff2)\)", css)))):
    nome = f"f{i}.woff2"
    (dest / nome).write_bytes(urllib.request.urlopen(url).read())
    css = css.replace(url, nome)
(dest / "font.css").write_text(css, encoding="utf-8")
print("Caratteri salvati in", dest)
