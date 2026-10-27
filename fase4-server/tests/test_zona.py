"""Regola della zona risultante (decisione del 27/10/2026), uguale in fase 3, fase 9 e cti_try."""
from meteo_storico import legge10


def gg(a, b, c, d, e, f):
    return dict(zip("ABCDEF", (a, b, c, d, e, f)))


def test_zona_dpr_tra_le_coerenti():
    g = gg(1500, 1600, 1800, 2050, 2250, 2400)       # D ed E entrambe coerenti
    assert legge10.zona_risultante(g, "D") == "D"
    assert legge10.zona_risultante(g, "E") == "E"


def test_senza_dpr_la_piu_centrale():
    g = gg(1500, 1600, 1800, 2050, 2250, 2400)       # margini: D 50 GG, E 150 GG
    assert legge10.zona_risultante(g) == "E"
    assert legge10.zona_risultante(g, "C") == "E"    # zona DPR non coerente: come senza DPR
    assert legge10.zona_risultante(gg(1500, 1600, 1800, 2080, 2120, 2400)) == "D"


def test_nessuna_coerente():
    # caso artificiale: nessuna zona coerente → zona dei GG sull'anno intero
    assert legge10.zona_risultante(gg(700, 1000, 1500, 2200, 3100, 2900)) == "E"
