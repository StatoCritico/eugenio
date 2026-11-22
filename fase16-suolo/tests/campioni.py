"""Piccoli campioni inventati per le prove della fase 16 (niente rete): Excel ISPRA, CSV ISTAT, stato dello scarico.

Territorio: Bologna (037006) e Imola (037032), provincia di Bologna (037), Emilia-Romagna (08); Aggius in Sardegna, con
il codice nuovo ISPRA 113001 (provincia 113, Gallura Nord-Est Sardegna) e il vecchio 090001 nelle mappe del sito (si
abbina per nome). Anni ISPRA 2006, 2012, 2015 e il foglio 2012_rev; edizione 2016.
"""
from __future__ import annotations

import json
from pathlib import Path

CAMPI = (["csuolo1", "csuolo4", "csuolo8", "csuolo10", "csuolo13", "pidrau4", "pfrane3", "pfrane4", "ccoste4", "careep2",
          "clammi3", "clammi4"] + [f"csuolox{c}" for c in (111, 112, 113, 114, 115, 116, 117, 118, 121, 122, 123, 124, 125, 126)])

# comune: (nome, prov, reg, superficie) e per anno: suolo consumato; incrementi per classe (111, 122, 125)
COMUNI = {
    37006: ("Bologna", 37, 8, 14073.0),
    37032: ("Imola", 37, 8, 20494.0),
    113001: ("Aggius", 113, 20, 8624.0),
}
SUOLO = {   # anno → comune → suolo consumato
    2006: {37006: 5000.0, 37032: 2000.0, 113001: 100.0},
    2012: {37006: 5060.0, 37032: 2030.0, 113001: 101.0},
    2015: {37006: 5080.0, 37032: 2040.5, 113001: 101.5},
}
REV = {2012: {37006: 5055.0, 37032: 2030.0, 113001: 101.0}}
CLASSI = {  # anno → comune → {classe: incremento}; il 2012 ha una parte non attribuita (lordo > somma delle classi)
    2012: {37006: {111: 30.0, 122: 20.0}, 37032: {125: 30.0}, 113001: {122: 1.0}},
    2015: {37006: {111: 10.0, 122: 12.0}, 37032: {125: 10.5}, 113001: {111: 0.5}},
}
LORDO = {2012: {37006: 65.0, 37032: 30.0, 113001: 1.0}, 2015: {37006: 22.0, 37032: 10.5, 113001: 0.5}}
RIPRISTINI = {2012: {37006: 5.0, 37032: 0.0, 113001: 0.0}, 2015: {37006: 2.0, 37032: 0.0, 113001: 0.0}}


def _riga_comune(pc: int, anno: int, rev: bool = False) -> dict:
    nome, prov, reg, sup = COMUNI[pc]
    cons = (REV if rev else SUOLO)[anno][pc]
    r = {"pro_com": pc, "nome_comune": nome, "cod_prov": prov, "nome_provincia": "x", "cod_reg": reg, "nome_regione": "x",
         "csuolo1": cons, "csuolo4": 100 * cons / sup, "clammi3": sup, "clammi4": 1000 * (pc % 7 + 1),
         "pidrau4": cons * 0.1, "pfrane3": cons * 0.01, "pfrane4": cons * 0.02, "ccoste4": 0.0, "careep2": cons * 0.05}
    if anno in CLASSI and not rev:
        lordo, rip = LORDO[anno][pc], RIPRISTINI[anno][pc]
        r.update({"csuolo10": lordo, "csuolo13": rip, "csuolo8": lordo - rip})
        for c, v in CLASSI[anno][pc].items():
            r[f"csuolox{c}"] = v
    return r


def _somma(righe: list[dict], chiave_cod: str, cod) -> dict:
    out = {chiave_cod: cod}
    for k in CAMPI:
        vals = [r.get(k) for r in righe if r.get(k) not in (None, "")]
        out[k] = sum(vals) if vals else ""
    if out["clammi3"]:
        out["csuolo4"] = 100 * out["csuolo1"] / out["clammi3"]
    return out


def scrivi_excel(percorso: Path, alterato: dict | None = None, edizione: int = 2016) -> None:
    """Excel nello stesso formato di consumo_suolo_AAAA_Com_Prov_Reg_Naz (fogli Info, Comuni_AAAA, Province_…, Regioni_…,
    Nazionale_…, anche _rev). `alterato` = {(livello, foglio): {campo: valore}} cambia la prima riga di un foglio."""
    import openpyxl
    wb = openpyxl.Workbook()
    info = wb.active
    info.title = "Info"
    for riga in (["ISPRA"], [f"Consumo di suolo, ecosistemi urbani e stato del territorio. Edizione {edizione}"],
                 [f"Elaborazioni del consumo di suolo (v. 1.0) – 27/10/{edizione}"], ["CC BY 4.0"]):
        info.append(riga)
    fogli = [(str(a), a, False) for a in sorted(SUOLO)] + [(f"{a}_rev", a, True) for a in sorted(REV)]
    testa_c = ["pro_com", "nome_comune", "cod_prov", "nome_provincia", "cod_reg", "nome_regione"] + CAMPI
    for nome, anno, rev in fogli:
        com = [_riga_comune(pc, anno, rev) for pc in COMUNI]
        prov = [_somma([r for r in com if r["cod_prov"] == p], "cod_prov", p) for p in sorted({r["cod_prov"] for r in com})]
        for p in prov:
            p.update({"nome_provincia": "x", "cod_reg": 8 if p["cod_prov"] == 37 else 20, "nome_regione": "x"})
        reg = [_somma([r for r in com if r["cod_reg"] == g], "cod_reg", g) for g in sorted({r["cod_reg"] for r in com})]
        for g in reg:
            g["nome_regione"] = "x"
        naz = [_somma(com, "cod_naz", 0)]
        naz[0]["nome_nazione"] = "Italia"
        for livello, righe, testa in (("Comuni", com, testa_c), ("Province", prov, ["cod_prov", "nome_provincia", "cod_reg", "nome_regione"] + CAMPI),
                                      ("Regioni", reg, ["cod_reg", "nome_regione"] + CAMPI), ("Nazionale", naz, ["cod_naz", "nome_nazione"] + CAMPI)):
            ws = wb.create_sheet(f"{livello}_{nome}")
            ws.append(testa)
            for i, r in enumerate(righe):
                if alterato and i == 0 and (livello, nome) in alterato:
                    r = {**r, **alterato[(livello, nome)]}
                ws.append([r.get(k, "") for k in testa])
    wb.save(percorso)


TESTA_SDMX = ("DATAFLOW,FREQ,REF_AREA,DATA_TYPE,TYPE_OF_CROP,DESTINATION_WINEGRAPES,TIME_PERIOD,OBS_VALUE,OBS_STATUS,NOTE_DS,"
              "NOTE_REF_AREA,NOTE_DATA_TYPE,NOTE_TYPE_OF_CROP_EUCODE,NOTE_TYPE_OF_CROP,NOTE_DESTINATION_WINEGRAPES,"
              "NOTE_TIME_PERIOD,BASE_PER,UNIT_MEAS,UNIT_MULT")


def scrivi_colture(percorso: Path, extra: list[tuple] = ()) -> None:
    """Superfici (ART) per IT, Emilia-Romagna (ITD5), Bologna (ITD55), Sardegna (ITG2) e Sassari (ITG25).
    2015: prati permanenti come figli (PERMGRASSE, POORINGS); 2016: come totale PGRAPM e anche i figli (non si sommano);
    OHROIE duplica OLIVO e si esclude; 2017 ha una sola voce (anno incompleto, escluso)."""
    righe = []
    for area, f in (("IT", 3.0), ("ITD5", 2.0), ("ITD55", 1.0), ("ITG2", 1.0), ("ITG25", 1.0)):
        for anno, voci in ((2015, {"WHEATD": 100, "COMMEAT": 50, "PERMGRASSE": 30, "POORINGS": 20, "OLIVTAB_OIL": 10, "WINEES": 5}),
                           (2016, {"WHEATD": 110, "PIGWETWINT": 40, "PGRAPM": 60, "PERMGRASSE": 35, "POORINGS": 25,
                                   "OLIVTAB_OIL": 12, "OLIVO": 11, "OHROIE": 11, "WINEES": 6}),
                           (2017, {"WHEATD": 120})):
            for c, v in voci.items():
                righe.append(f"IT1:X(1.0),A,{area},ART,{c},ALL,{anno},{v * f},,,,,,,,,,,")
            righe.append(f"IT1:X(1.0),A,{area},PA_EXT,WHEATD,ALL,{anno},1,,,,,,,,,,,")      # altro tipo di dato: ignorato
    for area, c, anno, v in extra:
        righe.append(f"IT1:X(1.0),A,{area},ART,{c},ALL,{anno},{v},,,,,,,,,,,")
    Path(percorso).write_text(TESTA_SDMX + "\n" + "\n".join(righe) + "\n", encoding="utf-8")


def scrivi_censimento(percorso: Path) -> None:
    righe = ["IT1:DF(1.0),A,037006,ARU,2020,3000.5,,,037006,,,,,,", "IT1:DF(1.0),A,037006,AA_UNUT,2020,20,,,037006,,,,,,",
             "IT1:DF(1.0),A,037032,ARU,2020,15000,,,037032,,,,,,", "IT1:DF(1.0),A,090001,ARU,2020,4000,,,090001,,,,,,",
             "IT1:DF(1.0),A,090001,AA_UNUT,2020,100,,,090001,,,,,,", "IT1:DF(1.0),A,IT,ARU,2020,22000.5,,,IT,,,,,,"]
    Path(percorso).write_text("DATAFLOW,FREQ,REF_AREA,DATA_TYPE,TIME_PERIOD,OBS_VALUE,OBS_STATUS,NOTE_DS,"
                              "NOTE_ISTAT_TERR_OFFICIAL_CODE,NOTE_REF_AREA,NOTE_DATA_TYPE,NOTE_TIME_PERIOD,BASE_PER,UNIT_MEAS,UNIT_MULT\n"
                              + "\n".join(righe) + "\n", encoding="utf-8")


def raw(cartella: Path, alterato: dict | None = None, edizione: int = 2016, agricolo: bool = True) -> Path:
    cartella.mkdir(parents=True, exist_ok=True)
    scrivi_excel(cartella / "ispra_indicatori.xlsx", alterato, edizione)
    scrivi_colture(cartella / "istat_coltivazioni.csv")
    scrivi_censimento(cartella / "istat_censimento2020.csv")
    (cartella / "stato_scarico.json").write_text(json.dumps({"ispra": {"nome": "consumo_suolo_2016_Com_Prov_Reg_Naz_v1.0.xlsx",
                                                                        "anno": 2016, "versione": "1.0", "url": "https://esempio.invalid/x.xlsx"}}))
    if agricolo:
        # incrocio di agricolo.py per il periodo 2012–2015 (anno 2015): codici delle mappe del sito
        g = 7
        vuoto = [0.0] * g
        com = {"037006": {"lordo": [10, 0, 0, 12, 0, 0, 0], "agricolo": [4, 0, 0, 6, 0, 0, 0], "usi": [10, 0, 0, 0, 0]},
               "090001": {"lordo": [0.5] + vuoto[1:], "agricolo": [0.5] + vuoto[1:], "usi": [0.5, 0, 0, 0, 0]}}
        (cartella / "agricolo_2015.json").write_text(json.dumps({"anno": 2015, "periodo": "2012–2015", "file": {},
            "italia": {"lordo": [10.5, 0, 0, 12, 0, 0, 0], "agricolo": [4.5, 0, 0, 6, 0, 0, 0], "usi": [10.5, 0, 0, 0, 0]},
            "regioni": {}, "comuni": com, "usi_non_agricoli": {"IT": {"Urbano e aree assimilate": 12.0}}}))
    return cartella
