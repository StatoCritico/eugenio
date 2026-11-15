# -*- coding: utf-8 -*-
"""Genera cellmap.json (per check_workbook.py) e MAPPA_CELLE.md accanto a questo file (layout.json lo scrive build_psicro.py)."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
LY = json.load(open(os.path.join(HERE, "layout.json"), encoding="utf-8"))
OUT = HERE
SE, SI = LY["SEAS"]["E"], LY["SEAS"]["I"]
O = LY["O"]
TRL, SEC = LY["TRL"], LY["SEC"]
RIF0 = LY["RIF"][0]


def u(c):
    return f"UTA!{c}"


def seq_inputs(base, rows):
    """rows: lista di 6 tuple (tipo, p1, p2, p3)"""
    d = {}
    for k, (t, p1, p2, p3) in enumerate(rows, start=1):
        r = base + O["R0"] + k
        d[u(f"C{r}")] = {"value": t}
        for c, v in (("D", p1), ("E", p2), ("F", p3)):
            d[u(f"{c}{r}")] = {"value": v} if v is not None else {"value": None}
    return d


def gen_inputs(z=0, V="ref:inputs.V_m3h", oa=100):
    return {u("D6"): z, u("D8"): {"value": None}, u("D10"): V, u("D11"): oa, u("D14"): {"value": RIF0}}


def state_out(row, prefix, keys=("T_C", "x_gkg", "h_kJkg", "RH_pct", "v_m3kg", "Tdew_C", "Twb_C")):
    col = {"T_C": "H", "RH_pct": "I", "x_gkg": "J", "h_kJkg": "K", "Tdew_C": "L", "Twb_C": "M", "v_m3kg": "N"}
    return {u(f"{col[k]}{row}"): f"{prefix}.{k}" for k in keys}


NONE6 = [("Nessuna", None, None, None)] * 6
SUMMER = [("Miscela con ricircolo", "AUTO", None, None), ("Raffreddamento con deumidificazione", "AUTO", 0.1, None),
          ("Post-riscaldamento", "AUTO", None, None), ("Ventilatore", 0.7, None, None),
          ("Nessuna", None, None, None), ("Nessuna", None, None, None)]


def summer_case(name, oa, feasible=True):
    inp = gen_inputs(oa=oa)
    inp.update({u(f"D{SE + 2}"): "ref:inputs.T_oa_C", u(f"D{SE + 3}"): "ref:inputs.RH_oa_pct",
                u(f"D{SE + 4}"): "ref:inputs.T_room_C", u(f"D{SE + 5}"): "ref:inputs.RH_room_pct",
                u(f"D{SE + 6}"): {"ref": "inputs.Qs_kW", "scale": 1000}, u(f"D{SE + 7}"): {"ref": "inputs.Ql_kW", "scale": 1000}})
    inp.update(seq_inputs(SE, SUMMER))
    r0 = SE + O["R0"]
    out = {u("H9"): "m_da_kgs", u(f"H{SE + 4}"): "supply_T_imm_C", u(f"J{SE + 4}"): "supply_x_imm_gkg"}
    out.update(state_out(SE + 2, "states.OA"))
    out.update(state_out(SE + 3, "states.ROOM"))
    if oa < 100:
        out.update(state_out(r0 + 1, "states.MIX"))
    out.update(state_out(r0 + 2, "states.COIL_OUT"))
    out[f"Calcoli!{TRL['tadp']}{LY['TR_ROWS']['E'] + 1}"] = "states.ADP.T_C"
    out[u(f"H{r0 + 3}")] = "variant_postheat_to_Timm_minus_fan.postheat_out_T_C"
    out[u(f"H{r0 + 4}")] = "variant_postheat_to_Timm_minus_fan.supply_T_C"
    s0 = SE + O["SUMH"]
    out[u(f"D{s0 + 1}")] = "powers.cooling_total_kW"
    out[u(f"D{s0 + 2}")] = "powers.cooling_sensible_kW"
    out[u(f"D{s0 + 3}")] = "powers.cooling_latent_kW"
    out[u(f"D{s0 + 5}")] = "variant_postheat_to_Timm_minus_fan.postheat_kW"
    out[u(f"D{s0 + 6}")] = "powers.condensate_kgh"
    out[u(f"D{s0 + 9}")] = "powers.fan_heat_kW"
    out[u(f"H{s0 + 5}")] = {"expect": "SÌ" if feasible else "NO", "label": "punto di immissione raggiungibile"}
    return {"name": name, "inputs": inp, "outputs": out}


def winter_inputs(seq):
    inp = gen_inputs(oa=100)
    inp.update({u(f"D{SI + 2}"): "ref:inputs.T_oa_C", u(f"D{SI + 3}"): "ref:inputs.RH_oa_pct",
                u(f"D{SI + 4}"): "ref:inputs.T_room_C", u(f"D{SI + 5}"): "ref:inputs.RH_room_pct",
                u(f"D{SI + 6}"): {"ref": "inputs.Q_heat_loss_kW", "scale": 1000},
                u(f"D{SI + 7}"): {"ref": "inputs.Ql_gain_kW", "scale": 1000}})
    inp.update(seq_inputs(SI, seq))
    return inp


def winter_c(name):
    seq = [("Recuperatore di calore", "ref:inputs.eps_HR", None, None), ("Miscela con ricircolo", "AUTO", None, None),
           ("Preriscaldamento", "AUTO", None, 90), ("Umidificazione adiabatica", "AUTO", None, None),
           ("Post-riscaldamento", "AUTO", None, None), ("Nessuna", None, None, None)]
    inp = winter_inputs(seq)
    inp[u(f"D{SI + O['R0'] + 1}")] = "ref:inputs.eps_HR"
    r0 = SI + O["R0"]
    out = {u("I9"): "m_da_kgs", u(f"H{SI + 4}"): "supply_T_imm_C", u(f"J{SI + 4}"): "supply_x_imm_gkg"}
    out.update(state_out(SI + 2, "states.OA"))
    out.update(state_out(SI + 3, "states.ROOM"))
    out.update(state_out(r0 + 1, "states.HR_OUT"))
    out.update(state_out(r0 + 3, "states.PREHEAT_OUT"))
    out.update(state_out(r0 + 4, "states.HUM_OUT"))
    out.update(state_out(r0 + 5, "states.SUPPLY"))
    s0 = SI + O["SUMH"]
    out[u(f"D{s0 + 8}")] = "powers.heat_recovery_kW"
    out[u(f"D{s0 + 4}")] = "powers.preheat_kW"
    out[u(f"D{s0 + 5}")] = "powers.postheat_kW"
    out[u(f"D{s0 + 7}")] = "powers.humidifier_water_kgh"
    out[u(f"H{s0 + 5}")] = {"expect": "SÌ", "label": "punto di immissione raggiungibile"}
    return {"name": name, "inputs": inp, "outputs": out}


def winter_d(name):
    seq = [("Recuperatore di calore", 0.6, None, None), ("Nessuna", None, None, None),
           ("Post-riscaldamento", "AUTO", None, None), ("Umidificazione a vapore", "AUTO", None, None),
           ("Nessuna", None, None, None), ("Nessuna", None, None, None)]
    inp = winter_inputs(seq)
    r0 = SI + O["R0"]
    out = {u("I9"): "m_da_kgs"}
    out.update(state_out(r0 + 1, "states.HR_OUT"))
    out[u(f"H{r0 + 4}")] = "variant_heat_to_Timm_then_steam.supply_T_C"
    out[u(f"J{r0 + 4}")] = "states.SUPPLY.x_gkg"
    s0 = SI + O["SUMH"]
    out[u(f"D{s0 + 5}")] = "variant_heat_to_Timm_then_steam.heater_kW"
    out[u(f"D{s0 + 7}")] = "powers.steam_kgh"
    out[u(f"D{s0 + 8}")] = "powers.heat_recovery_kW"
    return {"name": name, "inputs": inp, "outputs": out}


cases = [summer_case("a_5000", 100), summer_case("b_5000", 70), summer_case("a_1000", 100, feasible=False),
         winter_c("c_5000"), winter_c("c_1000"), winter_d("d_5000")]
# e1: riscaldamento 20 -> 22 °C, 1000 m3/h riferiti all'ingresso
inp = gen_inputs(V="ref:inputs.V_m3h")
inp.update({u(f"D{SI + 2}"): "ref:inputs.T_in_C", u(f"D{SI + 3}"): "ref:inputs.RH_in_pct", u(f"D{SI + 4}"): 20,
            u(f"D{SI + 5}"): 50, u(f"D{SI + 6}"): 0, u(f"D{SI + 7}"): 0})
inp.update(seq_inputs(SI, [("Riscaldamento sensibile", 22, None, None)] + NONE6[:5]))
out = {u("I9"): "m_da_kgs", u(f"R{SI + O['R0'] + 1}"): "powers.heating_kW"}
out.update(state_out(SI + O["R0"], "states.IN"))
out.update(state_out(SI + O["R0"] + 1, "states.OUT"))
cases.append({"name": "e1_1000", "inputs": inp, "outputs": out})
# e2: umidificazione adiabatica fino a saturazione
inp = gen_inputs(V="ref:inputs.V_m3h")
inp.update({u(f"D{SE + 2}"): "ref:inputs.T_in_C", u(f"D{SE + 3}"): "ref:states.IN.RH_pct", u(f"D{SE + 4}"): 26,
            u(f"D{SE + 5}"): 50, u(f"D{SE + 6}"): 0, u(f"D{SE + 7}"): 0})
inp.update(seq_inputs(SE, [("Umidificazione adiabatica", None, 100, None)] + NONE6[:5]))
out = {u("H9"): "m_da_kgs", u(f"S{SE + O['R0'] + 1}"): "powers.water_kgh"}
out.update(state_out(SE + O["R0"], "states.IN", ("T_C", "x_gkg", "h_kJkg", "Tdew_C", "Twb_C")))
out.update(state_out(SE + O["R0"] + 1, "states.OUT", ("T_C", "x_gkg", "h_kJkg", "RH_pct")))
cases.append({"name": "e2_1000", "inputs": inp, "outputs": out})

# griglia di stati: 4 stati per ricalcolo (E e A di estate e inverno)
GRID = {0: [["t-10_rh30", "t-5_rh80", "t0_rh50", "t5_rh30"], ["t10_rh50", "t20_rh50", "t26_rh50", "t32_rh50"],
            ["t40_rh80", "t35_rh30", "t15_rh100", "t-5_rh30"]],
        500: [["t20_rh50", "t-10_rh80", "t32_rh50", "t5_rh50"]],
        1000: [["t-5_rh50", "t35_rh50", "t26_rh30", "t10_rh80"]]}
slots = [(SE, 2), (SE, 4), (SI, 2), (SI, 4)]   # (base, offset riga input T); UR = +1; punti E/A riga base+2/+3
pt_rows = [SE + 2, SE + 3, SI + 2, SI + 3]
ps_rows = [LY["SE_ROWS"]["E"], LY["SE_ROWS"]["E"] + 1, LY["SE_ROWS"]["I"], LY["SE_ROWS"]["I"] + 1]
for z, groups in GRID.items():
    for gi, g in enumerate(groups):
        inp = gen_inputs(z=z, V=5000)
        out = {}
        for j, sid in enumerate(g):
            full = f"/states.z{z}_{sid}"
            base, off = slots[j]
            inp[u(f"D{base + off}")] = f"ref:{full}.T_C"
            inp[u(f"D{base + off + 1}")] = f"ref:{full}.RH_pct"
            out.update({k: "/" + v[0:].replace(f"{full[1:]}", f"{full[1:]}") for k, v in
                        state_out(pt_rows[j], full[1:]).items()})
            out[f"Calcoli!{SEC['ps']}{ps_rows[j]}"] = f"{full}.psat_Pa"
        out[u("D9")] = f"/states.z{z}_{g[0]}.p_Pa"
        cases.append({"name": f"griglia_z{z}_{gi + 1}", "ref_case": "", "inputs": inp, "outputs": out})

json.dump({"default_sheet": "UTA", "cases": cases}, open(os.path.join(OUT, "cellmap.json"), "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)
print("cellmap.json:", len(cases), "casi")

# ------------------------------------------------------------------ MAPPA_CELLE.md
TR = LY["TR_ROWS"]
md = []
A = md.append
A("# Mappa delle celle – psicro_UTA.xlsx\n")
A("Generata da `build/make_cellmap.py` (indirizzi stabili: cambiano solo se si modifica `build_psicro.py`).")
A("Tutte le celle sono nel foglio **UTA** salvo diversa indicazione. x in **g/kg** nel foglio UTA (kg/kg nel foglio Calcoli), UR in **%**, potenze in **kW**, carichi in ingresso in **W**.\n")
A("## Dati generali (input in giallo)\n")
A("| Grandezza | Cella | Note |\n|---|---|---|")
for a, b, c in [("Altitudine z [m]", "D6", "input"), ("Pressione calcolata [Pa]", "D7", "formula"),
                ("Pressione imposta [Pa]", "D8", "input facoltativo, vuoto = calcolata"),
                ("Pressione di calcolo p [Pa]", "D9", "formula"), ("Portata di mandata V [m³/h]", "D10", "input"),
                ("Quota aria esterna [%]", "D11", "input (100 = tutta aria esterna)"),
                ("Portata rinnovo / ricircolo [m³/h]", "D12 / D13", "formula"),
                ("Riferimento della portata", "D14", "input, menu: " + " / ".join(f"«{t}»" for t in LY["RIF"])),
                ("v rif. [m³/kg] estate / inverno", "H7 / I7", ""), ("ρ rif. [kg/m³]", "H8 / I8", ""),
                ("ṁ aria secca [kg/s]", "H9 / I9", "estate / inverno"), ("ṁ [kg/h]", "H10 / I10", ""),
                ("ṁ aria esterna [kg/s]", "H11 / I11", ""), ("frazione ricircolo AUTO", "H12 / I12", "")]:
    A(f"| {a} | {b} | {c} |")
for s, b in (("ESTATE", SE), ("INVERNO", SI)):
    A(f"\n## {s} (intestazione riga {b})\n")
    A("| Input | Cella |\n|---|---|")
    labs = ["T esterna [°C]", "UR esterna [%]", "T ambiente [°C]", "UR ambiente [%]",
            "Carico sensibile [W]" if s == "ESTATE" else "Dispersioni [W]", "Carico latente [W]"]
    for i, l in enumerate(labs):
        A(f"| {l} | D{b + 2 + i} |")
    A("\nPunti (colonne: H = T °C, I = UR %, J = x g/kg, K = h kJ/kg, L = T rugiada °C, M = T bulbo umido °C, N = v m³/kg, O = ρ kg/m³):\n")
    A("| Punto | Riga |\n|---|---|")
    A(f"| E esterno | {b + 2} |\n| A ambiente | {b + 3} |\n| I immissione | {b + 4} |")
    A(f"\nΔT immissione H{b + 5}; fattore termico R H{b + 6}; verifiche (testo) H{b + 7}.\n")
    A(f"Sequenza: riga 0 (ingresso = esterno) riga {b + O['R0']}; righe 1–6 = righe {b + O['R0'] + 1}–{b + O['R0'] + 6}.")
    A("Colonne: B N, **C tipo** (input, menu), **D P1, E P2, F P3** (input), G significato parametri, H T, I UR %, J x g/kg, K h, "
      "L T rugiada, M T bulbo umido, N v, O ṁ kg/s, P Q sensibile kW, Q Q latente kW, R Q totale kW, S acqua kg/h (+ aggiunta, − condensata), T note.\n")
    s0 = b + O["SUMH"]
    A("| Riepilogo | Cella |\n|---|---|")
    for i, l in enumerate(["Potenza frigorifera totale [kW]", "  di cui sensibile [kW]", "  di cui latente [kW]",
                           "Preriscaldamento [kW]", "Post-riscaldamento + riscaldamento [kW]", "Acqua condensata [kg/h]",
                           "Acqua di umidificazione [kg/h]", "Potenza recuperata [kW]", "Calore ventilatori [kW]"]):
        A(f"| {l} | D{s0 + 1 + i} |")
    A(f"| Uscita UTA (T, UR, x, h) | H{s0 + 2}:K{s0 + 2} |\n| Immissione richiesta | H{s0 + 3}:K{s0 + 3} |\n"
      f"| Scostamento | H{s0 + 4}:K{s0 + 4} |\n| Raggiungibile? («SÌ»/«NO») | H{s0 + 5} |\n| Esito (testo) | H{s0 + 6} |")
A(f"\n## Stima stagionale\nInput D{LY['STIMA'] + 1}:D{LY['STIMA'] + 6} (GG, ore/giorno, rendimento, PCI, ore eq. estive, EER); risultati H{LY['STIMA'] + 1}:H{LY['STIMA'] + 8}.\n")
A("## Foglio Calcoli\n")
A(f"- Pressione D4 (Pa), D5 (kPa).")
A(f"- Motore degli stati: estate righe {LY['SE_ROWS']['E']}–{LY['SE_ROWS']['E'] + 9} (E, A, I, R0, R1…R6), inverno righe {LY['SE_ROWS']['I']}–{LY['SE_ROWS']['I'] + 9}. "
  f"Colonne: {SEC['t']} T, {SEC['x']} x [kg/kg], {SEC['pw']} pv, {SEC['ps']} psat [Pa], {SEC['phi']} φ [-], {SEC['h']} h, {SEC['v']} v, {SEC['rho']} ρ, "
  f"{SEC['xg']} x [g/kg], {SEC['td3']} T rugiada, {SEC['tw6']} T bulbo umido.")
A(f"- Grandezze di stagione: colonna D (estate) / E (inverno), righe " + ", ".join(f"{k} {v}" for k, v in LY["SC"].items()) + ".")
A(f"- Trasformazioni: estate righe {TR['E']}–{TR['E'] + 5}, inverno righe {TR['I']}–{TR['I'] + 5}; colonne principali: "
  f"codice {TRL['code']}, ṁ {TRL['mdot']}, T ADP {TRL['tadp']}, T uscita {TRL['tout']}, x uscita {TRL['xout']}, Q tot {TRL['Qt']}, Q lat {TRL['Ql']}, "
  f"Q sens {TRL['Qs']}, acqua {TRL['water']}, note {TRL['nota']}.")
A("- Dati del diagramma T–x (foglio «psicro»): dalla riga 100 (tabella di saturazione, curve UR, isoentalpiche, isocore, rette ambiente, goniometro).")
A("- Dati del diagramma di Mollier (foglio «Mollier»): dalla riga 240 (curve UR, isoterme 300–483 e 486–495, isoentalpiche 500–512, isocore 520–529, "
  "trasformazioni e punti 540–563 = x da UTA e Y = T·(1+1,86·x/1006), scala di bordo Δh/Δx 580–598).\n")
A("Ordine dei fogli: UTA, psicro (ex «Diagramma»), Mollier, Guida, Calcoli, Liste (nascosto). Nessun indirizzo di UTA o Calcoli è cambiato rispetto alla v2.0.\n")
A("## Codici dei tipi di trasformazione\n")
A("| Codice | Tipo |\n|---|---|")
for i, t in enumerate(LY["TIPI"], start=1):
    A(f"| {i} | {t} |")
A("\n## Verifica automatica\n`cellmap.json` (stessa cartella) è nel formato di `check_workbook.py`:\n"
  "```\npython3 check_workbook.py ../../fase5-sito/sito/strumenti/psicro_UTA.xlsx cellmap.json --ref ../tests/dati/reference_cases.json\n```\n"
  "Convenzioni: per i casi estivi il post-riscaldamento AUTO porta a T_imm − ΔT ventilatore (variante `variant_postheat_to_Timm_minus_fan` del riferimento); "
  "nel caso d il riscaldatore AUTO porta a T_imm e il vapore viene dopo (variante `variant_heat_to_Timm_then_steam`).")
open(os.path.join(OUT, "MAPPA_CELLE.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
print("MAPPA_CELLE.md scritto")
