#!/usr/bin/env python3
"""Check an Excel psychrometric/AHU workbook against reference_cases.json.

Usage:
  python3 check_workbook.py WORKBOOK.xlsx CELLMAP.json [--ref reference_cases.json]
                            [--keep DIR] [--json-out results.json] [--only CASE ...]

For each case in the cell map: copy the workbook, write the input cells (openpyxl),
recalculate with LibreOffice headless (soffice --convert-to xlsx, private profile),
read the output cells with data_only=True and compare with the reference values.
See README.md for the cell-map format. Exit code 0 = all pass, 1 = failures.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))

# default tolerances by leaf-name pattern: (regex, abs_tol, rel_tol); pass if
# |diff| <= max(abs_tol, rel_tol*|ref|)
TOLS = [
    (r"(^|_)(T|Tdew|Twb)(_|$)|_T_C$|^T_|_C$", 0.2, 0.0),   # temperatures, K
    (r"gkg$", 0.1, 0.0),                                   # humidity ratio g/kg
    (r"h_kJkg$|kJkg$", 0.3, 0.0),                          # enthalpy
    (r"RH_pct$|_pct$", 1.0, 0.0),                          # relative humidity %
    (r"v_m3kg$|m3kg$", 0.003, 0.0),                        # specific volume
    (r"_kW", 0.05, 0.02),                                  # powers: 2 % (floor 0.05 kW)
    (r"kgh$", 0.05, 0.02),                                 # water flows: 2 %
    (r"kgs$", 0.0, 0.01),                                  # mass flows: 1 %
    (r"^p_Pa$", 1.0, 0.001),                               # total pressure: 0.1 %
    (r"psat|pv_Pa|_Pa$", 1.0, 0.005),                      # pressures: 0.5 %
    (r"cp", 0.002, 0.0),
    (r"_K$", 0.2, 0.0),
]
DEFAULT_TOL = (0.0, 0.01)


def default_tol(path):
    leaf = path.split(".")[-1]
    for pat, a, r in TOLS:
        if re.search(pat, leaf):
            return a, r
    return DEFAULT_TOL


def get_path(d, path):
    cur = d
    for k in path.split("."):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            raise KeyError(f"reference path not found: {path}")
    return cur


def resolve_ref(ref, case_prefix, path):
    """'/ahu.a_1000.m_da_kgs' = absolute path; otherwise relative to the case's ref_case."""
    if path.startswith("/"):
        return path[1:], get_path(ref, path[1:])
    full = f"{case_prefix}.{path}" if case_prefix else path
    return full, get_path(ref, full)


def split_addr(addr, default_sheet):
    m = re.match(r"^(?:'([^']+)'|([^!]+))!([A-Za-z]+[0-9]+)$", addr)
    if m:
        return (m.group(1) or m.group(2)), m.group(3).upper()
    if re.match(r"^[A-Za-z]+[0-9]+$", addr):
        if not default_sheet:
            raise ValueError(f"cell {addr} has no sheet and no default_sheet given")
        return default_sheet, addr.upper()
    raise ValueError(f"bad cell address: {addr}")


def recalc(src, outdir):
    """Recalculate src with LibreOffice headless; returns path of recalculated copy."""
    profile = tempfile.mkdtemp(prefix="lo_profile_")
    os.makedirs(outdir, exist_ok=True)
    cmd = ["soffice", f"-env:UserInstallation=file://{profile}", "--headless", "--norestore",
           "--calc", "--convert-to", "xlsx:Calc MS Excel 2007 XML", "--outdir", outdir, src]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    shutil.rmtree(profile, ignore_errors=True)
    out = os.path.join(outdir, os.path.splitext(os.path.basename(src))[0] + ".xlsx")
    if r.returncode != 0 or not os.path.exists(out):
        raise RuntimeError(f"LibreOffice conversion failed: {r.stdout}\n{r.stderr}")
    return out


def run_case(wb_path, case, ref, workdir, default_sheet):
    name = case["name"]
    prefix = case.get("ref_case", f"ahu.{name}" if name in ref.get("ahu", {}) else "")
    sheet0 = case.get("default_sheet", default_sheet)
    cdir = os.path.join(workdir, re.sub(r"[^A-Za-z0-9_.-]", "_", name))
    os.makedirs(cdir, exist_ok=True)
    inp_path = os.path.join(cdir, "input_" + os.path.basename(wb_path))
    wb = openpyxl.load_workbook(wb_path)
    for addr, val in case.get("inputs", {}).items():
        if isinstance(val, str) and val.startswith("ref:"):
            _, val = resolve_ref(ref, prefix, val[4:])
        elif isinstance(val, dict):
            v = val["ref"] if "ref" in val else val["value"]
            if isinstance(v, str) and "ref" in val:
                _, v = resolve_ref(ref, prefix, v)
            val = v * val.get("scale", 1.0) + val.get("offset", 0.0) if isinstance(v, (int, float)) else v
        sh, cell = split_addr(addr, sheet0)
        if sh not in wb.sheetnames:
            raise KeyError(f"[{name}] sheet '{sh}' not in workbook {wb.sheetnames}")
        wb[sh][cell].value = val
    wb.save(inp_path)
    out_path = recalc(inp_path, os.path.join(cdir, "recalc"))
    wbv = openpyxl.load_workbook(out_path, data_only=True)
    rows = []
    for addr, spec in case.get("outputs", {}).items():
        if isinstance(spec, str):
            spec = {"ref": spec}
        sh, cell = split_addr(addr, sheet0)
        raw = wbv[sh][cell].value if sh in wbv.sheetnames else "#NOSHEET"
        if "expect" in spec:
            rpath, rval = "(literal)", spec["expect"]
        else:
            rpath, rval = resolve_ref(ref, prefix, spec["ref"])
        label = spec.get("label", rpath)
        if isinstance(rval, bool) or isinstance(rval, str):
            ok = str(raw).strip().upper() in {str(rval).upper(), {True: "TRUE", False: "FALSE"}.get(rval, "?"),
                                               {True: "1", False: "0"}.get(rval, "?")}
            rows.append((name, addr, label, rval, raw, None, None, ok))
            continue
        try:
            got = float(raw) * spec.get("scale", 1.0) + spec.get("offset", 0.0)
        except (TypeError, ValueError):
            rows.append((name, addr, label, rval, raw, None, None, False))
            continue
        a, r = default_tol(rpath)
        a = spec.get("tol", a)
        r = spec.get("rel_tol", 0.0 if "tol" in spec else r)
        tol = max(a, r * abs(rval))
        diff = got - rval
        rows.append((name, addr, label, rval, got, diff, tol, abs(diff) <= tol + 1e-12))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workbook")
    ap.add_argument("cellmap")
    ap.add_argument("--ref", default=os.path.join(HERE, "reference_cases.json"))
    ap.add_argument("--keep", help="directory to keep intermediate/recalculated files")
    ap.add_argument("--json-out")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    ref = json.load(open(a.ref))
    cmap = json.load(open(a.cellmap))
    workdir = a.keep or tempfile.mkdtemp(prefix="wbcheck_")
    all_rows, errors = [], []
    for case in cmap["cases"]:
        if a.only and case["name"] not in a.only:
            continue
        try:
            all_rows += run_case(os.path.abspath(a.workbook), case, ref, workdir,
                                 cmap.get("default_sheet"))
        except Exception as e:  # report and continue
            errors.append((case["name"], repr(e)))
    w = [24, 10, 44, 12, 12, 10, 8]
    hdr = ["case", "cell", "quantity", "ref", "workbook", "diff", "tol"]
    print("  ".join(h.ljust(n) for h, n in zip(hdr, w)) + "  result")
    print("-" * (sum(w) + 2 * len(w) + 6))

    def f(v):
        if isinstance(v, float):
            return f"{v:.4g}" if abs(v) >= 1e4 or (v != 0 and abs(v) < 1e-3) else f"{v:.4f}"
        return str(v)
    for row in all_rows:
        vals = [row[0], row[1], row[2][-44:], f(row[3]), f(row[4]),
                "" if row[5] is None else f"{row[5]:+.4f}", "" if row[6] is None else f"{row[6]:.3g}"]
        print("  ".join(str(v).ljust(n) for v, n in zip(vals, w)) + ("  PASS" if row[7] else "  FAIL"))
    npass = sum(r[7] for r in all_rows)
    print(f"\n{npass}/{len(all_rows)} checks passed")
    for n, e in errors:
        print(f"ERROR in case {n}: {e}")
    if a.json_out:
        json.dump([dict(zip(hdr + ["pass"], r)) for r in all_rows] + [{"error": e, "case": n} for n, e in errors],
                  open(a.json_out, "w"), indent=1, default=str)
    if not a.keep:
        shutil.rmtree(workdir, ignore_errors=True)
    sys.exit(0 if npass == len(all_rows) and not errors and all_rows else 1)


if __name__ == "__main__":
    main()
