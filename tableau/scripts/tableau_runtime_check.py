"""
RetailPulse - check the final workbook INSIDE Tableau Desktop Public Edition (macOS only).

This is the runtime test that XML and Python checks cannot replace. Two passes:

  DASHBOARDS  each of the 8 dashboards is opened (as the active window) in a fresh Tableau instance.
              Pass = the workbook loads with no error dialog (load errors, the Tableau Public extract
              check 3C242D89, query errors 1B885FB3 ...), every extract connects, no query error is
              logged, and every worksheet on the dashboard issues its queries.
  SHEETS      each worksheet is opened on its own. The SQL Tableau generated for it is taken from
              Hyper's log and re-executed on the extract; the results must contain the figures of
              tableau/dashboard_specification.md (CHECKS below) and, for the KPI sheets, every KPI
              value of the validated calculated-field reference (tableau_calc_validation_results.csv).
              Table calculations (moving average, MoM %, rank, cumulative share) are computed by
              Tableau after the query: for those sheets their inputs are checked, and the formulas
              themselves are covered by scripts/validate_tableau_calcs.py.

It writes copies of tableau/RetailPulse_Final.twbx to a scratch folder (the active window changed)
and never modifies anything in tableau/. Each check runs in its own Tableau instance, started and closed
by this script; a Tableau window you have open is not touched (its activity may add log lines, so
avoid working in Tableau while the check runs). Nothing is clicked or typed: clicks on filters and
actions are NOT tested here (see reports/tableau_final_validation.md for what was tested).

Usage:  ./venv/bin/python tableau/scripts/tableau_runtime_check.py [--only dashboards|sheets]
                                                               [--sheets NAME ...] [--wait 40]
        (the scratch copies appear in Tableau's "recent workbooks" list; remove them there if unwanted)
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
sys.path.insert(0, str(ROOT / "scripts"))
from tableau_registry import DATA_SOURCES  # noqa: E402

TAB = ROOT / "tableau"
APP = "Tableau Public (Apple silicon)"
LOGS = Path.home() / "Documents" / "My Tableau Repository" / "Logs"
FINAL = TAB / "RetailPulse_Final.twbx"
ET.register_namespace("user", "http://www.tableausoftware.com/xml/user")
HYPER_OF_TABLE = {t: ds.replace(" ", "_") + ".hyper" for ds, tables in DATA_SOURCES.items() for t, *_ in tables}

# Expected figures per sheet, from tableau/dashboard_specification.md (unfiltered).
#   number          must appear in a result cell (|diff| <= tol, default 0.005)
#   ("str", s)      string must appear in a result cell
#   ("rows", n)     a result set with exactly n rows
#   ("sum", n)      a numeric column of one result set sums to n
CHECKS: dict[str, list] = {
    "1.0 KPIs": [13494400.74, 99441, 96096, 98199, 86.90],
    "1.1 Revenue and Orders by Month": [1003862.14, ("rows", 20)],
    "1.2 Revenue MoM %": [1003862.14, ("rows", 20)],
    "1.3 Revenue by State (Top 12)": [5163867.22, 1811623.42, 1573508.20],
    "1.4 Top 10 Categories": [1255695.13, ("str", "health_beauty")],
    "1.5 YoY Jan–Aug": [3080850.81, 7341037.41],
    "2.0 KPIs": [96096, 93099, 2997, 13494400.74],
    "2.1 One-time vs Repeat": [93099, 2997],
    "2.2 RFM Segments": [21427, 14792, 33498, 23420, 951, 895],
    "2.3 Customer Value Distribution": [("sum", 94983)],
    "2.4 Cohort Retention Matrix": [("str", "2017-01"), ("str", "2018-07")],
    "2.5 Purchase Frequency": [93099, 2745, 203, 30, 8, 6, 3, 1],
    "3.0 KPIs": [13494400.74, 74, 112101, 1255695.13],
    "3.1 Revenue by Category (Top 15)": [1255695.13, ("str", "watches_gifts")],
    "3.2 Pareto": [1255695.13, ("rows", 74)],
    "3.3 Monthly Trend (Top 5)": [("str", "health_beauty"), ("str", "watches_gifts"), ("str", "bed_bath_table"),
                                 ("str", "sports_leisure"), ("str", "computers_accessories")],
    "3.4 Growth vs Decline": [(5.3222, 0.0001), (4.4427, 0.0001), (-0.0312, 0.0001), (-0.4579, 0.0001)],
    "3.5 Category Table": [1255695.13, 9634, ("rows", 74)],
    "4.0 KPIs": [3053, 13494400.74],
    "4.1 Top 20 Sellers": [229237.63],
    "4.2 Seller Concentration Curve": [229237.63, ("rows", 3053)],
    "4.3 Scorecard Scatter": [("rows", 428)],
    "4.4 Intervention Table": [187923.89, ("rows", 21)],
    "5.0 KPIs": [96478, 7827, 2241126.29, 96476],
    "5.1 Order Status": [96478, 1107, 625, 609, 314, 301, 5, 2],
    "5.2 Promised vs Actual": [39.51, 12.65, 15.19, 7.73],
    "5.3 Delivery by State": [8.76, ("rows", 27)],
    "5.4 Delivery Time Distribution": [("sum", 96170)],
    "5.5 Delivery Stage Breakdown": [0.40, 2.85, 9.36],
    "5.6 Stage Shares": [95088],
    "6.0 KPIs": [99224, 4795, (4.0864, 0.00005)],
    "6.1 Score Distribution": [11424, 3151, 8179, 19142, 57328],
    "6.2 Delay vs Score": [(4.201, 0.0005), (4.202, 0.0005), (3.184, 0.0005), (3.860, 0.0005), (1.733, 0.0005),
                           (3.660, 0.0005), (1.726, 0.0005), (2.895, 0.0005)],
    "6.3 Satisfaction Trend": [("rows", 20)],
    "6.4 Category Satisfaction": [(3.6175, 0.00005), (4.4626, 0.00005), ("rows", 35)],
    "7.0 KPIs": [1255695.13, (4.4427, 0.0001)],
    "7.0 Product KPIs": [9634],
    "7.0 Review KPIs": [(4.1822, 0.00005), (0.1019, 0.00005), (0.0537, 0.00005)],
    "7.1 Rank and Cumulative Share": [1255695.13],
    "7.2 Monthly Trend": [("rows", 20)],
    "7.3 Top 10 Products": [("rows", 10)],
    "7.4 Top 10 Sellers in Category": [("rows", 10)],
    "7.5 Seller Delivery in Category": [1255695.13, (2.69, 0.005)],
    "7.6 Satisfaction": [(4.1822, 0.00005), (4.3728, 0.00005), 8826],
    "8.0 KPIs": [229237.63, 1131, (15.06, 0.005), (4.136, 0.0005)],
    "8.1 Cumulative Share": [229237.63],
    "8.2 Profile": [("str", "SP")],
    "8.3 Categories Sold": [("rows", 10), ("sum", 229237.63)],
    "8.4 Category Breakdown": [("rows", 10)],
}


# FILTERS pass: a filter or parameter value is saved into a copy of the workbook (what a viewer's click
# would set), the window is opened, and the figures Tableau then computes must equal the specification's
# filtered test values. (window, sheet whose queries are checked, change, expected figures)
#   ("group", field, value)  every sheet of the dashboard's shared filter on `field` keeps only `value`
#   ("param", name, value)   parameter value
FILTER_TESTS = [
    ("1 Executive", "1.0 KPIs", ("group", "customer_state", "SP"), [5163867.22]),
    ("2 Customers", "2.0 KPIs", ("group", "customer_state", "SP"), [5162518.20]),
    ("4 Sellers", "4.0 KPIs", ("group", "seller_state", "SP"), [8687740.35, 1822]),
    ("5 Operations", "5.0 KPIs", ("group", "customer_state", "SP"), [(8.76, 0.005)]),
    ("6 Satisfaction", "6.0 KPIs", ("group", "customer_state", "SP"), [41690]),
    ("7 Category Detail", "7.0 KPIs", ("param", "p_category", "watches_gifts"), ["csv:watches_gifts"]),
]


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
    return sorted(out, key=lambda d: d.get("ts", ""))


def running() -> bool:
    return subprocess.run(["pgrep", "-f", "MacOS/Tableau Public"], capture_output=True).returncode == 0


APPBIN = f"/Applications/{APP}.app/Contents/MacOS/Tableau Public"


def close_instance(proc: subprocess.Popen):
    """Close ONLY the Tableau instance this script started (it holds a scratch copy, so nothing can be lost);
    any other Tableau window the user has open is left alone."""
    proc.kill()
    proc.wait(timeout=30)
    time.sleep(2)


def variant(src_twb: bytes, window: str, change=None) -> bytes:
    """The workbook with `window` (sheet or dashboard) as the active, visible window, optionally with a
    saved filter or parameter value (FILTER_TESTS)."""
    root = ET.fromstring(src_twb)
    if change and change[0] == "group":
        _, field, value = change
        dash = next(d for d in root.find("dashboards") if d.get("name") == window)
        groups = set()
        for z in dash.iter("zone"):
            if z.get("type-v2") == "filter" and f":{field}:" in z.get("param", ""):
                ws = next(w for w in root.find("worksheets") if w.get("name") == z.get("name"))
                groups |= {f.get("filter-group") for f in ws.iter("filter") if f.get("column") == z.get("param")}
        for f in root.iter("filter"):
            if f.get("filter-group") in groups:
                g = f.find("groupfilter")
                level = g.get("level")
                f.remove(g)
                ET.SubElement(f, "groupfilter", {"function": "member", "level": level, "member": f'"{value}"',
                                                 "{http://www.tableausoftware.com/xml/user}ui-domain": "database",
                                                 "{http://www.tableausoftware.com/xml/user}ui-enumeration": "inclusive",
                                                 "{http://www.tableausoftware.com/xml/user}ui-marker": "enumerate"})
    if change and change[0] == "param":
        _, name, value = change
        for c in root.iter("column"):
            if c.get("name") == f"[{name}]" and c.get("param-domain-type"):
                c.set("value", f'"{value}"')
                c.find("calculation").set("formula", f'"{value}"')
    for w in root.find("windows"):
        w.attrib.pop("maximized", None)
        if w.get("name") == window:
            w.set("maximized", "true")
            w.attrib.pop("hidden", None)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def open_copy(inner_name, inner, members, window, path, wait, change=None) -> tuple[list[dict], list[str], str]:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(inner_name, variant(inner, window, change))
        for n, data in members.items():
            z.writestr(n, data)
    start = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    # a dedicated instance per check (the executable started directly, not through `open`, which would hand the
    # file to an instance the user may have open)
    proc = subprocess.Popen([APPBIN, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    last, quiet = None, 0
    for _ in range(wait):                                 # wait until the logs stop growing (or `wait` s)
        time.sleep(1)
        n = sum(p.stat().st_size for p in LOGS.glob("*.txt")) + sum(p.stat().st_size for p in LOGS.glob("hyperd*.log"))
        quiet = quiet + 1 if n == last else 0
        last = n
        if quiet >= 6:
            break
    time.sleep(2)
    tab = [e for e in log_events("log*.txt", start)
           if not isinstance(e.get("ctx"), dict) or e["ctx"].get("wb") in (None, path.stem)]
    queries = [e["v"]["query"] for e in log_events("hyperd*.log", start)
               if e.get("k") == "query-begin" and isinstance(e.get("v"), dict)
               and '"Extract".' in e["v"].get("query", "")]
    close_instance(proc)
    return tab, queries, start


def summarize(tab: list[dict]) -> dict:
    dialogs = []
    for e in tab:
        v = str(e.get("v"))
        if "show-detailed-error-dialog" in v:
            m = re.search(r"errorcode=([0-9a-f]+)", v)
            dialogs.append(m.group(1) if m else v[:120])
    errors = [str(e["v"].get("error-messages", ""))[:220] for e in tab if e.get("k") == "qp-process-query-error"]
    sheets = {j.get("owner-worksheet") for e in tab if e.get("k") == "qp-batch-summary"
              for j in e["v"].get("jobs", []) if j.get("owner-worksheet")}
    hyper = {e["v"]["attributes"].get("dbname", "").split("/")[-1] for e in tab
             if e.get("k") == "hyper-protocol-connection-success"}
    missing = sum("unexpectedly missing field" in str(e.get("v")) for e in tab)
    return {"dialogs": dialogs, "errors": errors, "sheets": sheets, "hyper": hyper, "missing": missing}


def run_queries(hp, queries: list[str], ext_dir: Path) -> list[pd.DataFrame]:
    frames = []
    for q in dict.fromkeys(queries):
        tables = re.findall(r'"Extract"\."([^"]+)"', q)
        dbs = {HYPER_OF_TABLE.get(t) for t in tables} - {None}
        if len(dbs) != 1:
            continue
        try:
            with Connection(hp.endpoint, str(ext_dir / dbs.pop())) as c:
                with c.execute_query(q) as res:
                    names = [col.name.unescaped for col in res.schema.columns]
                    frames.append(pd.DataFrame([list(r) for r in res], columns=names))
        except Exception:                                  # e.g. queries on Tableau's session temp tables
            continue
    return frames


def evaluate(sheet: str, frames: list[pd.DataFrame], kpi_expected: dict) -> list[tuple[str, bool]]:
    nums, strs = [], set()
    for f in frames:
        for col in f.columns:
            for v in f[col]:
                if isinstance(v, bool) or v is None:
                    continue
                if isinstance(v, (int, float)):
                    nums.append(float(v))
                elif hasattr(v, "__float__") and not isinstance(v, str):
                    try:
                        nums.append(float(v))
                    except (TypeError, ValueError):
                        strs.add(str(v))
                else:
                    strs.add(str(v))
    # averages and ratios: Tableau's SQL returns the parts (e.g. SUM and COUNT of an AVG, or the numerator and
    # denominator of a ratio KPI) and Tableau divides after the query, so ratios of returned columns count too
    derived = []
    for f in frames:
        num = f.apply(pd.to_numeric, errors="coerce")
        cols = [c for c in num.columns if num[c].notna().any()]
        for a_ in cols:
            for b_ in cols:
                if a_ != b_:
                    with pd.option_context("mode.use_inf_as_na", True) if False else _nullctx():
                        r = (num[a_] / num[b_]).replace([float("inf"), float("-inf")], float("nan")).dropna()
                    derived += [float(x) for x in r] + [float(x) - 1 for x in r]   # ratio; growth = ratio - 1
        for c in cols:                                         # percent-unit columns divided by 100 in Tableau
            derived += [float(x) / 100 for x in num[c].dropna()]
    out = []
    checks = list(CHECKS.get(sheet, [])) + [(v, max(0.005, 1e-9 * abs(v))) for v in kpi_expected.get(sheet, [])]
    for c in checks:
        if isinstance(c, tuple) and c[0] == "str":
            out.append((f"'{c[1]}' present", c[1] in strs))
        elif isinstance(c, tuple) and c[0] == "rows":
            out.append((f"{c[1]} rows", any(len(f) == c[1] for f in frames)))
        elif isinstance(c, tuple) and c[0] == "sum":
            ok = any(abs(pd.to_numeric(f[col], errors="coerce").sum() - c[1]) <= 0.01
                     for f in frames for col in f.columns if pd.api.types.is_numeric_dtype(f[col]) or
                     pd.to_numeric(f[col], errors="coerce").notna().all())
            out.append((f"a column sums to {c[1]:,}", ok))
        else:
            v, tol = c if isinstance(c, tuple) else (c, 0.005)
            if any(abs(n - v) <= tol for n in nums):
                out.append((f"{v:,}", True))
            else:
                out.append((f"{v:,} (Tableau ratio of returned parts)", any(abs(n - v) <= tol for n in derived)))
    return out


class _nullctx:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def kpi_reference(root: ET.Element) -> dict[str, list[float]]:
    """KPI sheets: the validated unfiltered value of every calculated field they show (ratios computed by
    Tableau after the query are excluded: the query returns their inputs, which are checked)."""
    res = pd.read_csv(TAB / "tableau_calc_validation_results.csv")
    res = res[(res.kind == "reference check") & res.context.str.startswith("unfiltered")]
    ref = res.groupby("id").expected.first().to_dict()
    out = {}
    for ws in root.find("worksheets"):
        members = [g.get("member") for g in ws.iter("groupfilter") if g.get("level") == "[:Measure Names]"]
        ids = [m.group(1) for x in members if (m := re.search(r"RP_([MN]\d\d)", x or ""))]
        name = ws.get("name", "")
        if name[:2] not in ("7.", "8.") and name.split(" ")[1:2] in (["KPIs"], ["Stage"], ["YoY"]):
            out[ws.get("name")] = [ref[i] for i in ids if i in ref and i not in RATIOS]
    return out


# ratio KPIs that Tableau finishes after the query (their inputs are checked instead)
RATIOS = {"M06", "M19", "M15", "M39", "M40", "M44", "M47", "M48", "N22", "N23", "N24", "N21", "N18", "N19", "N20",
          "M34", "M27", "M33", "M32", "M35", "N11", "N15", "N16", "N26", "N28", "N31", "N33", "N30", "N39", "M20",
          "M46", "N32", "N29"}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--scratch", type=Path, default=Path(tempfile.gettempdir()) / "retailpulse_tableau_check")
    ap.add_argument("--wait", type=int, default=40, help="maximum seconds per window")
    ap.add_argument("--only", choices=["dashboards", "sheets", "filters"])
    ap.add_argument("--sheets", nargs="*", help="only these worksheet / dashboard names")
    args = ap.parse_args()
    if not FINAL.exists():
        sys.exit("ABORT: build the workbook first: tableau/scripts/build_tableau_extracts.py")
    args.scratch.mkdir(parents=True, exist_ok=True)
    ext_dir = TAB / "extracts"
    with zipfile.ZipFile(FINAL) as z:
        inner_name = next(n for n in z.namelist() if n.endswith(".twb"))
        inner = z.read(inner_name)
        members = {n: z.read(n) for n in z.namelist() if n != inner_name}
    root = ET.fromstring(inner)
    sheets = [w.get("name") for w in root.find("worksheets")]
    dashboards = {d.get("name"): sorted({z.get("name") for z in d.iter("zone")
                                         if z.get("name") and not z.get("type-v2")})
                  for d in (root.find("dashboards") if root.find("dashboards") is not None else [])}
    report = {"dashboards": {}, "sheets": {}}
    fails = 0
    if args.only in (None, "dashboards"):
        print(f"DASHBOARDS ({len(dashboards)})")
        for i, (name, zone_sheets) in enumerate(dashboards.items(), 1):
            if args.sheets and name not in args.sheets:
                continue
            tab, _, _ = open_copy(inner_name, inner, members, name, args.scratch / f"RP_dash_{i}.twbx", args.wait)
            s = summarize(tab)
            missing_sheets = [z for z in zone_sheets if z not in s["sheets"]]
            ok = not s["dialogs"] and not s["errors"] and not s["missing"] and not missing_sheets
            fails += not ok
            report["dashboards"][name] = {**s, "sheets": sorted(s["sheets"]), "hyper": sorted(s["hyper"]),
                                          "not_queried": missing_sheets, "ok": ok}
            print(f"  {'PASS' if ok else 'FAIL'}  {name:<20} dialogs {len(s['dialogs'])} {s['dialogs']} · query errors "
                  f"{len(s['errors'])} · sheets queried {len(zone_sheets) - len(missing_sheets)}/{len(zone_sheets)}"
                  + (f" (not queried: {missing_sheets})" if missing_sheets else "") + f" · extracts {len(s['hyper'])}")
            for e in s["errors"][:3]:
                print("        ", e)
    if args.only in (None, "sheets"):
        kpi_expected = kpi_reference(root)
        print(f"\nWORKSHEETS ({len(sheets)})")
        with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU, parameters={"log_config": ""}) as hp:
            for i, name in enumerate(sheets, 1):
                if args.sheets and name not in args.sheets:
                    continue
                tab, queries, _ = open_copy(inner_name, inner, members, name, args.scratch / f"RP_sheet_{i}.twbx",
                                            args.wait)
                s = summarize(tab)
                frames = run_queries(hp, queries, ext_dir)
                res = evaluate(name, frames, kpi_expected)
                ok = not s["dialogs"] and not s["errors"] and not s["missing"] and bool(queries) and all(r for _, r in res)
                fails += not ok
                report["sheets"][name] = {"dialogs": s["dialogs"], "errors": s["errors"], "queries": len(queries),
                                          "result_rows": [len(f) for f in frames],
                                          "checks": [(c, bool(r)) for c, r in res], "ok": ok}
                bad = [c for c, r in res if not r]
                print(f"  {'PASS' if ok else 'FAIL'}  {name:<34} queries {len(queries):>2} · checks "
                      f"{sum(r for _, r in res)}/{len(res)}" + (f" · failed: {bad}" if bad else "")
                      + (f" · dialogs {s['dialogs']}" if s["dialogs"] else "") + (f" · errors {s['errors'][:1]}" if s["errors"] else ""))
    if args.only in (None, "filters"):
        print(f"\nFILTERS AND PARAMETERS ({len(FILTER_TESTS)}: values saved into a copy, not clicked)")
        cat = pd.read_csv(TAB / "data" / "vw_category_performance.csv")
        report["filters"] = {}
        with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU, parameters={"log_config": ""}) as hp:
            for i, (window, sheet, change, expected) in enumerate(FILTER_TESTS, 1):
                if args.sheets and window not in args.sheets:
                    continue
                tab, queries, _ = open_copy(inner_name, inner, members, window, args.scratch / f"RP_filter_{i}.twbx",
                                            args.wait, change)
                s = summarize(tab)
                frames = run_queries(hp, queries, ext_dir)
                exp = [round(cat.loc[cat.category == e[4:], "revenue"].sum(), 2) if isinstance(e, str) else e
                       for e in expected]
                CHECKS[f"__filter{i}"] = exp
                res = evaluate(f"__filter{i}", frames, {})
                ok = not s["dialogs"] and not s["errors"] and all(r for _, r in res)
                fails += not ok
                label = f"{window} · {change[1]} = {change[2]}"
                report["filters"][label] = {"checks": [(c, bool(r)) for c, r in res], "ok": ok, "dialogs": s["dialogs"]}
                print(f"  {'PASS' if ok else 'FAIL'}  {label:<42} {sheet}: " + ", ".join(f"{c} {'ok' if r else 'MISSING'}"
                                                                                  for c, r in res))
    out = args.scratch / "tableau_runtime_check.json"
    out.write_text(json.dumps(report, indent=1, default=str))
    print(f"\nresult: {'ALL PASS' if not fails else f'{fails} FAILED'}   (details: {out})")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
