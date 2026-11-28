"""
RetailPulse - check the final workbook INSIDE Tableau Desktop Public Edition (macOS only).

This is the runtime test that XML and Python checks cannot replace. For each KPI check sheet it:
  1. writes a copy of tableau/RetailPulse_Final.twbx (to a scratch folder) in which that sheet is
     the active window, so Tableau draws it as soon as the workbook opens;
  2. opens the copy with Tableau (macOS `open -a`; nothing is clicked or typed);
  3. reads Tableau's own logs: the workbook loaded, all six extracts connected, no error dialog
     (including the Tableau Public extract check, error 3C242D89, which runs when a workbook opens);
  4. takes the SQL Tableau generated for the sheet from Hyper's log, re-executes that exact SQL on
     the extract, and compares every KPI value with the validated SQL reference values.

It never modifies anything in tableau/. Each check runs in a fresh Tableau instance, which is asked to quit
afterwards (an unmodified workbook closes without a prompt). Close Tableau before running it.

Usage:  ./venv/bin/python tableau/scripts/tableau_runtime_check.py [--scratch DIR] [--wait 90]
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
import zipfile

import pandas as pd
from tableauhyperapi import Connection, HyperProcess, Telemetry

ROOT = Path(__file__).resolve().parents[2]
TAB = ROOT / "tableau"
APP = "Tableau Public (Apple silicon)"
LOGS = Path.home() / "Documents" / "My Tableau Repository" / "Logs"
FINAL = TAB / "RetailPulse_Final.twbx"
DB_OF_TABLE = {"vw_order_summary": "RP_Orders", "vw_customer_summary": "RP_Customers",
               "vw_category_performance": "RP_Categories", "vw_seller_performance": "RP_Sellers",
               "delivery_stage_orders": "RP_Orders", "vw_review_summary": "RP_Orders"}


def log_events(pattern: str, since: str) -> list[dict]:
    """Events since `since` from every matching log: Tableau rotates its logs and each instance writes its own."""
    out = []
    for path in sorted(LOGS.glob(pattern)):
        for line in path.read_text(errors="replace").splitlines():
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if isinstance(d, dict) and d.get("ts", "") >= since:
                out.append(d)
    return out


def quit_tableau():
    """Ask Tableau to quit (unmodified workbooks close without a prompt) and wait for it to exit."""
    subprocess.run(["osascript", "-e", 'tell application id "com.tableausoftware.tableaupublic" to quit'],
                   capture_output=True)
    for _ in range(60):
        if subprocess.run(["pgrep", "-f", "Tableau Public"], capture_output=True).returncode:
            return True
        time.sleep(1)
    return False


def variant(src_twb: bytes, sheet: str) -> bytes:
    root = ET.fromstring(src_twb)
    for w in root.find("windows"):
        w.attrib.pop("maximized", None)
        if w.get("name") == sheet:
            w.set("maximized", "true")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def expected_values() -> dict[str, float]:
    res = pd.read_csv(TAB / "tableau_calc_validation_results.csv")
    res = res[(res.kind == "reference check") & res.context.str.startswith("unfiltered")]
    return res.groupby("id").expected.first().to_dict()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--scratch", type=Path, default=Path(tempfile.gettempdir()) / "retailpulse_tableau_check")
    ap.add_argument("--wait", type=int, default=90, help="seconds to wait for each sheet's query")
    ap.add_argument("--sheets", nargs="*", help="only these sheet names (default: all KPI sheets)")
    args = ap.parse_args()
    if not FINAL.exists():
        sys.exit("ABORT: build the workbook first: tableau/scripts/build_tableau_extracts.py")
    args.scratch.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(FINAL) as z:
        inner_name = next(n for n in z.namelist() if n.endswith(".twb"))
        inner = z.read(inner_name)
        members = {n: z.read(n) for n in z.namelist() if n != inner_name}
    sheets = [w.get("name") for w in ET.fromstring(inner).find("worksheets")]
    expected = expected_values()
    results, opened = [], []
    if subprocess.run(["pgrep", "-f", "Tableau Public"], capture_output=True).returncode == 0:
        sys.exit("ABORT: Tableau is already running; close it first so each check starts in a fresh instance")
    for i, sheet in enumerate(sheets, 1):
        if args.sheets and sheet not in args.sheets:
            continue
        path = args.scratch / f"RP_check_{i}.twbx"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(inner_name, variant(inner, sheet))
            for n, data in members.items():
                z.writestr(n, data)
        start = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        subprocess.run(["open", "-a", APP, str(path)], check=True)
        query = None
        for _ in range(args.wait):
            time.sleep(1)
            qs = [e["v"]["query"] for e in log_events("hyperd*.log", start)
                  if e.get("k") == "query-begin" and re.search(r"RP_[MN]\d\d", (e.get("v") or {}).get("query", ""))]
            if qs:
                query = qs[-1]
                time.sleep(3)
                break
        time.sleep(5)                                       # let any error dialog reach the log
        tab = [e for e in log_events("log*.txt", start)
               if not isinstance(e.get("ctx"), dict) or e["ctx"].get("wb") in (None, path.stem)]
        dialogs = [str(e.get("v"))[:200] for e in tab if "show-detailed-error-dialog" in str(e.get("v"))]
        hyper_ok = sorted({e["v"]["attributes"].get("dbname", "").split("/")[-1]
                           for e in tab if e.get("k") == "hyper-protocol-connection-success"})
        mn_warn = sum("unexpectedly missing field" in str(e.get("v")) for e in tab)
        opened.append((sheet, dialogs, hyper_ok, mn_warn))
        results.append((sheet, query))
        quit_tableau()
        print(f"[{sheet}] opened; error dialogs: {len(dialogs)}; extracts connected: {len(hyper_ok)}; "
              f"missing-field warnings: {mn_warn}; KPI query captured: {'yes' if query else 'NO'}")

    print("\nRe-executing Tableau's generated SQL on the extracts:")
    fails = 0
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU, parameters={"log_config": ""}) as hp:
        for sheet, q in results:
            if not q:
                print(f"  FAIL  {sheet}: no query captured")
                fails += 1
                continue
            table = next(t for t in DB_OF_TABLE if f'"Extract"."{t}"' in q)
            with Connection(hp.endpoint, str(TAB / "extracts" / f"{DB_OF_TABLE[table]}.hyper")) as c:
                res = c.execute_query(q)
                names = [col.name.unescaped for col in res.schema.columns]
                row = next(iter(res))
                res.close()
            for n, v in zip(names, row):
                if n.startswith("TEMP("):                      # Tableau's intermediate columns (e.g. sum and count of an AVG)
                    continue
                m = re.search(r"RP_([MN]\d\d)", n)
                if not m or m.group(1) not in expected or v is None:
                    continue
                exp = expected[m.group(1)]
                ok = abs(float(v) - exp) <= max(0.005, 1e-9 * abs(exp))
                fails += not ok
                print(f"  {'PASS' if ok else 'FAIL'}  {sheet:<18} {m.group(1)} = {float(v):,.4f}   expected {exp:,.4f}")
    bad_open = [s for s, d, h, w in opened if d or len(h) < 6 or w]
    print(f"\nsheets opened without error dialog or missing-field warning: {len(opened) - len(bad_open)}/{len(opened)}")
    print(f"KPI values matching the validated reference: {'all' if not fails else f'{fails} mismatches'}")
    sys.exit(1 if fails or bad_open else 0)


if __name__ == "__main__":
    main()
