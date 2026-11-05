"""Metadati dell'.exe (avviatore/versione_windows.txt) coerenti con la versione (05/11/2026): SignPath vincola la firma a
ProductName e ProductVersion, quindi devono restare stabili e uguali a VERSIONE del lettore e dell'avviatore."""
import re

from conftest import QUI

AVV = QUI.parent / "avviatore"


def _versione(file, nome):
    return re.search(rf'{nome}\s*=\s*"([^"]+)"', file.read_text(encoding="utf-8")).group(1)


def test_metadati_coerenti():
    t = (AVV / "versione_windows.txt").read_text(encoding="utf-8")
    v = _versione(QUI.parent / "visure" / "__init__.py", "VERSIONE")
    assert _versione(AVV / "avviatore.py", "VERSIONE_AVVIATORE") == v
    campi = dict(re.findall(r"StringStruct\('(\w+)', '([^']*)'\)", t))
    assert campi["ProductName"] == "EuGEnio Visure"
    assert campi["ProductVersion"] == campi["FileVersion"] == v
    assert campi["OriginalFilename"] == "EuGEnioVisure.exe" and campi["InternalName"] == "EuGEnioVisure"
    numeri = tuple(int(x) for x in (v.split(".") + ["0", "0", "0"])[:4])
    assert f"filevers={numeri}".replace(" ", "") in t.replace(" ", "")
    assert f"prodvers={numeri}".replace(" ", "") in t.replace(" ", "")


def test_code_signing_policy_documentata():
    frase = "Free code signing provided by"
    readme = (QUI.parent / "README.md").read_text(encoding="utf-8")
    assert "### Code signing policy" in readme and frase in readme and "certificate by" in readme
    for ruolo in ("Authors", "Reviewers", "Approvers"):
        assert ruolo in readme
    pagina = (QUI.parents[1] / "fase5-sito" / "sito" / "visure.html").read_text(encoding="utf-8")
    assert 'id="code-signing-policy">Code signing policy<' in pagina and "SignPath Foundation" in pagina
    assert "%LOCALAPPDATA%\\EuGEnio\\Visure" in pagina and "--non-aggiornare" in pagina
    wf = (QUI.parents[1] / ".github" / "workflows" / "visure-windows.yml").read_text(encoding="utf-8")
    assert "#code-signing-policy" in wf
