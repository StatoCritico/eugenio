import sys
from pathlib import Path

import pytest

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent))
sys.path.insert(0, str(QUI.parent / "avviatore"))


@pytest.fixture(scope="session")
def sintetici(tmp_path_factory) -> Path:
    from visure.sintetici import PATRIMONIO_ESEMPIO, genera
    d = tmp_path_factory.mktemp("visure_sintetiche")
    genera(d)
    (d / "patrimonio_esempio_visure.csv").write_text(PATRIMONIO_ESEMPIO, encoding="utf-8")
    return d
