"""
RetailPulse - repair the generated Tableau workbook for Tableau Desktop Public Edition 2026.3.2.

PROBLEM (Tableau error D2E8DA72)
  "No declaration found for element 'manual-sort'" and "element 'manual-sort' is
  not allowed for content model '(datasources?,mapsources?,datasource-dependencies*,
  filter,sort,perspectives,slices?,aggregation)'".

ROOT CAUSE
  Tableau reads a workbook's sort elements in one of two formats, chosen by the
  <document-format-change-manifest>. The current format (<manual-sort>,
  <computed-sort>, <natural-sort>; the one in Tableau's published 2026.3 XSD) is
  used only when the manifest declares <SortTagCleanup />. Without it, Tableau
  applies the older content model quoted in the error, in which <manual-sort>
  does not exist. scripts/build_tableau_workbook.py copied its manifest from a
  workbook Tableau 2026.3.2 had saved with no sorting, so that declaration was
  never needed there and was missing here.

  Evidence: the Superstore sample shipped with Tableau 2026.3.2 contains 14
  <manual-sort> and 7 <computed-sort> elements, no legacy <sort> element, and
  declares <SortTagCleanup /> in its manifest.

REPAIR
  Insert <SortTagCleanup /> into the manifest (alphabetical position, as in the
  Superstore sample). The <manual-sort> elements are kept unchanged, so every
  sort column, direction and bucket order is preserved exactly. Nothing else
  changes.

CHECKS PERFORMED HERE
  * inventory of every sort element (sheet, column, direction, buckets)
  * every element and attribute name in the workbook also appears in
    Tableau-written reference files (the Superstore sample inside the installed
    Tableau app, and any workbook given with --reference)
  * text diff: exactly one line added, all other lines byte-identical
  * regression: original vs repaired element counts, worksheets, data sources,
    calculated fields, parameters, filters, relationships, sorts; the only
    difference must be the one manifest element
  * CSV dependencies: every connection folder and table file exists
  * Tableau's official 2026.3 XSD (tableau/schema/), via scripts/validate_tableau_workbook.py

OUTPUTS
  tableau/RetailPulse.twb.backup              byte copy of the input (never overwritten if it differs)
  tableau/RetailPulse_repaired.twb            repaired workbook
  reports/tableau_workbook_repair_report.md   what was found, changed and checked

Usage:
  ./venv/bin/python scripts/repair_tableau_workbook.py
  ./venv/bin/python scripts/repair_tableau_workbook.py --input tableau/RetailPulse.twb --reference /path/to/saved.twb
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import hashlib
from pathlib import Path
import shutil
import sys
import zipfile

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
TAB = ROOT / "tableau"
sys.path.insert(0, str(ROOT / "scripts"))
SUPERSTORE = Path("/Applications/Tableau Public (Apple silicon).app/Contents/help/Workbooks/en_US/Superstore.twbx")

SORT_TAGS = ("manual-sort", "computed-sort", "natural-sort", "alphabetic-sort")
FLAG = "SortTagCleanup"


def local(tag: str) -> str:
    """Feature-conditional names such as '_.fcp.MarkAnimation.true...style-rule' -> 'style-rule'."""
    return tag.split("...")[-1] if tag.startswith("_.fcp") else tag


def parse(path_or_bytes) -> etree._ElementTree:
    parser = etree.XMLParser(remove_blank_text=False, remove_comments=False, resolve_entities=False, no_network=True)
    if isinstance(path_or_bytes, bytes):
        return etree.ElementTree(etree.fromstring(path_or_bytes, parser))
    return etree.parse(str(path_or_bytes), parser)


def references(extra: list[Path]) -> list[tuple[str, etree._ElementTree]]:
    refs = []
    if SUPERSTORE.exists():
        with zipfile.ZipFile(SUPERSTORE) as z:
            name = next(n for n in z.namelist() if n.endswith(".twb"))
            refs.append(("Superstore sample (Tableau 2026.3.2 app bundle)", parse(z.read(name))))
    for p in extra:
        if p.exists():
            refs.append((p.name, parse(p)))
    return refs


def vocabulary(tree) -> tuple[set, set]:
    tags, attrs = set(), set()
    for e in tree.iter():
        if not isinstance(e.tag, str):
            continue
        t = local(e.tag)
        tags.add(t)
        attrs.update((t, a) for a in e.attrib)
    return tags, attrs


def sorts_by_sheet(tree) -> list[dict]:
    out = []
    for ws in tree.getroot().iter("worksheet"):
        for s in ws.iter(*SORT_TAGS):
            out.append({"sheet": ws.get("name"), "element": s.tag, "column": s.get("column"),
                        "direction": s.get("direction"), "using": s.get("using"),
                        "buckets": [b.text for b in s.iter("bucket")]})
    return out


def manifest_flags(tree) -> list[str]:
    m = tree.getroot().find("document-format-change-manifest")
    return [local(c.tag) for c in m] if m is not None else []


def summary(tree) -> dict:
    r = tree.getroot()
    calcs = [c for c in r.iter("column") if c.find("calculation") is not None]
    return {
        "elements": Counter(local(e.tag) for e in r.iter() if isinstance(e.tag, str)),
        "worksheets": [w.get("name") for w in r.iter("worksheet")],
        "dashboards": [d.get("name") for d in r.iter("dashboard")],
        "datasources": [d.get("caption") or d.get("name") for d in r.find("datasources")],
        "calculations (incl. sheet copies)": len(calcs),
        "datasource calculations": len([c for d in r.find("datasources") for c in d.findall("column")
                                        if c.find("calculation") is not None and d.get("name") != "Parameters"]),
        "parameters": [c.get("caption") for d in r.find("datasources") if d.get("name") == "Parameters"
                       for c in d.findall("column")],
        "filters": len(list(r.iter("filter"))),
        "relationships": len(list(r.iter("relationship"))),
        "sorts": sorts_by_sheet(tree),
    }


def csv_dependencies(tree) -> list[tuple[str, bool]]:
    out = []
    for ds in tree.getroot().find("datasources"):
        conn = ds.find("connection")
        if conn is None:
            continue
        folders = {nc.get("name"): Path(nc.find("connection").get("directory"))
                   for nc in conn.iter("named-connection")}
        for rel in conn.iter("relation"):
            if rel.get("type") == "table":
                p = folders[rel.get("connection")] / rel.get("name")
                out.append((f"{ds.get('caption')}: {rel.get('name')}", p.exists()))
    return out


def repair(tree, text: str) -> tuple[list[str], str]:
    """Declare SortTagCleanup when the workbook uses the current sort elements.

    The parsed tree decides WHERE the declaration belongs (alphabetical position in the
    manifest, the order Tableau itself writes); the change is then applied as one inserted
    line at that element's source line, so the rest of the file stays byte-identical.
    Returns (change log, new text)."""
    root = tree.getroot()
    if not any(True for _ in root.iter(*SORT_TAGS)):
        return ["no sort elements: nothing to declare"], text
    man = root.find("document-format-change-manifest")
    if man is None or len(man) == 0:
        raise SystemExit("ABORT: workbook has no document-format-change-manifest entries")
    if FLAG in manifest_flags(tree):
        return [f"<{FLAG} /> already declared: no change"], text
    children = list(man)
    pos = next((i for i, c in enumerate(children) if local(c.tag) > FLAG), len(children))
    anchor = children[pos] if pos < len(children) else children[-1]
    lines = text.split("\n")
    line_no = anchor.sourceline - 1                       # 0-based index of the anchor's line
    indent = lines[line_no][:len(lines[line_no]) - len(lines[line_no].lstrip())]
    insert_at = line_no if pos < len(children) else line_no + 1
    lines.insert(insert_at, f"{indent}<{FLAG} />")
    log = [f"inserted <{FLAG} /> into <document-format-change-manifest> as entry {pos + 1} of {len(children) + 1} "
           f"(alphabetical, between <{local(children[pos - 1].tag) if pos else '-'} /> and "
           f"<{local(children[pos].tag) if pos < len(children) else '-'} />), file line {insert_at + 1}"]
    return log, "\n".join(lines)


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--input", type=Path, default=TAB / "RetailPulse.twb")
    ap.add_argument("--output", type=Path, default=TAB / "RetailPulse_repaired.twb")
    ap.add_argument("--report", type=Path, default=ROOT / "reports" / "tableau_workbook_repair_report.md")
    ap.add_argument("--reference", type=Path, action="append", default=[],
                    help="a workbook saved by Tableau 2026.3.2 (may be given more than once)")
    args = ap.parse_args()
    src = args.input
    if not src.exists():
        raise SystemExit(f"ABORT: {src} not found")

    # 1. backup (recoverable, never silently overwritten)
    backup = src.with_name(src.name + ".backup")
    if backup.exists() and md5(backup) != md5(src):
        raise SystemExit(f"ABORT: {backup.name} exists and differs from {src.name}; move it away first")
    if not backup.exists():
        shutil.copy2(src, backup)
    assert md5(backup) == md5(src)

    # 2. inspect
    original = parse(src)
    before = summary(original)
    refs = references(args.reference)
    ref_tags, ref_attrs = set(), set()
    for _, t in refs:
        tg, at = vocabulary(t)
        ref_tags |= tg
        ref_attrs |= at
    tags, attrs = vocabulary(original)
    unknown_tags, unknown_attrs = sorted(tags - ref_tags), sorted(attrs - ref_attrs)
    ref_flags = {name: manifest_flags(t) for name, t in refs}

    # 3. repair (on a fresh parse; the original tree stays untouched for comparison)
    changes, new_text = repair(parse(src), src.read_text(encoding="utf-8"))
    args.output.write_text(new_text, encoding="utf-8")

    # 4. validate
    after_tree = parse(args.output)
    after = summary(after_tree)
    checks = []
    ck = lambda name, ok, detail="": checks.append((name, bool(ok), detail))
    ck("repaired file parses as XML", True)
    o_lines, a_lines = src.read_text(encoding="utf-8").split("\n"), args.output.read_text(encoding="utf-8").split("\n")
    extra = [ln for ln in a_lines if ln not in o_lines] if len(a_lines) == len(o_lines) + 1 else a_lines
    ck("text diff: exactly one line added, every other line byte-identical",
       len(a_lines) == len(o_lines) + 1 and [ln for ln in a_lines if ln.strip() != f"<{FLAG} />"] == o_lines,
       f"added: {[x.strip() for x in extra][:3]}")
    remaining = [s for s in after["sorts"]]
    ck(f"manifest declares <{FLAG} /> (required for {len(remaining)} sort elements)",
       FLAG in manifest_flags(after_tree) or not remaining)
    diff_elems = {k: after["elements"].get(k, 0) - before["elements"].get(k, 0)
                  for k in set(before["elements"]) | set(after["elements"])
                  if after["elements"].get(k, 0) != before["elements"].get(k, 0)}
    ck("only change: one manifest element added", diff_elems == {FLAG: 1} or (not changes[0].startswith("inserted")
                                                                             and not diff_elems), f"{diff_elems}")
    for key in ("worksheets", "dashboards", "datasources", "calculations (incl. sheet copies)", "datasource calculations",
                "parameters", "filters", "relationships"):
        ck(f"{key} unchanged ({before[key] if isinstance(before[key], int) else len(before[key])})",
           before[key] == after[key])
    ck("every sort element preserved (sheet, column, direction, bucket order)", before["sorts"] == after["sorts"],
       f"{len(after['sorts'])} sorts")
    # everything outside the manifest is identical
    o_root, a_root = original.getroot(), after_tree.getroot()
    same = all(etree.tostring(o) == etree.tostring(a) for o, a in zip(o_root, a_root)
               if o.tag != "document-format-change-manifest") and len(o_root) == len(a_root)
    ck("all workbook sections other than the manifest are byte-identical", same)
    ck("every element name also appears in Tableau-written reference files", not unknown_tags,
       f"{unknown_tags or 'none unknown'} ({len(refs)} reference file(s))")
    ck("every element/attribute pair also appears in Tableau-written reference files", not unknown_attrs,
       f"{unknown_attrs[:5] or 'none unknown'}")
    deps = csv_dependencies(after_tree)
    ck(f"all {len(deps)} CSV dependencies exist", all(ok for _, ok in deps),
       ", ".join(n for n, ok in deps if not ok) or "all present")
    import validate_tableau_workbook as V
    bad, waived = V.xsd_errors(args.output)
    ck("valid against Tableau's official 2026.3 XSD", not bad,
       (bad[0] if bad else "no errors") + (f" (waived: missing <explain-data>, also absent from files Tableau writes)"
                                           if waived else ""))

    # 5. report
    rel = lambda p: p.relative_to(ROOT) if p.is_relative_to(ROOT) else p.name
    L = []
    w = L.append
    w("# Tableau Workbook Repair Report")
    w("")
    w(f"**Date:** {date.today().isoformat()} · **Script:** `scripts/repair_tableau_workbook.py` · "
      f"**Input:** `{rel(src)}` · **Output:** `{rel(args.output)}` · **Backup:** `{rel(backup)}`")
    w("")
    w("## Error reported by Tableau Desktop Public Edition 2026.3.2")
    w("")
    w("Error code D2E8DA72: *No declaration found for element 'manual-sort'*; *attributes 'column' and "
      "'direction' are not declared*; *element 'manual-sort' is not allowed for content model "
      "'(datasources?,mapsources?,datasource-dependencies\\*,filter,sort,perspectives,slices?,aggregation)'*. "
      "Reported twice per KPI sheet: at the `<manual-sort>` line and at the closing `</view>`.")
    w("")
    w("## Root cause")
    w("")
    w("Tableau reads sort elements in one of two formats, selected by the workbook's "
      "`<document-format-change-manifest>`. The current format (`<manual-sort>`, `<computed-sort>`, "
      "`<natural-sort>`, as in Tableau's published 2026.3 XSD) applies only when the manifest declares "
      f"`<{FLAG} />`. Otherwise Tableau uses the older content model quoted in the error, which has no "
      "`<manual-sort>`. The workbook generator copied its manifest from a workbook Tableau 2026.3.2 had saved "
      "**without** any sorting, so the declaration was missing.")
    w("")
    w("**Evidence:**")
    for name, flags in ref_flags.items():
        n_sorts = len(sorts_by_sheet(next(t for nm, t in refs if nm == name)))
        w(f"- **{name}**: {n_sorts} current-format sort elements; manifest declares `{FLAG}`: "
          f"**{'yes' if FLAG in flags else 'no'}**")
    w(f"- **Generated workbook (before repair)**: {len(before['sorts'])} `<manual-sort>` elements; "
      f"manifest declares `{FLAG}`: **{'yes' if FLAG in manifest_flags(original) else 'no'}**")
    w("- Every other element and attribute name in the workbook also occurs in the Tableau-written reference "
      "files (check below), so no other unsupported markup was found.")
    w("")
    w("## Invalid elements found")
    w("")
    w(f"**{len(before['sorts'])}** `<manual-sort>` elements, one per KPI check sheet. Each sets the left-to-right "
      "order of the KPI values (Measure Names) to the order listed in the dashboard specification:")
    w("")
    w("| Sheet | Element | Column | Direction | Intended order (buckets) |")
    w("|---|---|---|---|---|")
    for s in before["sorts"]:
        order = ", ".join(b.split(":")[1] for b in s["buckets"])
        w(f"| {s['sheet']} | `{s['element']}` | Measure Names | {s['direction']} | {order} |")
    w("")
    w("(`RP_M01` = Total Revenue etc.; IDs as in `tableau/calculated_fields.md`.)")
    w("")
    w("## Repair applied")
    w("")
    for c in changes:
        w(f"- {c}")
    w("- The `<manual-sort>` elements were **kept unchanged**: sorting behaviour is preserved exactly. "
      "Nothing was deleted or converted.")
    w("- The generator (`scripts/build_tableau_workbook.py`) now declares the same flag, so regenerated "
      "workbooks do not repeat the problem.")
    w("")
    w("## Validation")
    w("")
    w("| Check | Result | Detail |")
    w("|---|---|---|")
    for name, ok, detail in checks:
        w(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
    w("")
    w("## Structure before and after")
    w("")
    w("| Item | Before | After |")
    w("|---|---|---|")
    for key in ("worksheets", "dashboards", "datasources", "parameters"):
        w(f"| {key} | {len(before[key])} | {len(after[key])} |")
    for key in ("datasource calculations", "calculations (incl. sheet copies)", "filters", "relationships"):
        w(f"| {key} | {before[key]} | {after[key]} |")
    w(f"| sort elements | {len(before['sorts'])} | {len(after['sorts'])} |")
    w(f"| manifest flags | {len(manifest_flags(original))} | {len(manifest_flags(after_tree))} |")
    w("")
    w("## Not verified here")
    w("")
    w("Opening the workbook in Tableau Desktop Public Edition was **not** done by this script: there is no "
      "supported way to drive Tableau's window from a script. XSD validation is syntactic only (Tableau's own "
      "note). The manual test is to open `tableau/RetailPulse_repaired.twb` in Tableau.")
    args.report.write_text("\n".join(L) + "\n", encoding="utf-8")

    for c in changes:
        print("CHANGE ", c)
    for name, ok, detail in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    n = sum(ok for _, ok, _ in checks)
    print(f"checks: {len(checks)}   PASS: {n}   FAIL: {len(checks) - n}")
    print(f"backup: {rel(backup)}   repaired: {rel(args.output)}   report: {rel(args.report)}")
    sys.exit(0 if n == len(checks) else 1)


if __name__ == "__main__":
    main()
