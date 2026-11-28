"""
RetailPulse - generate the Tableau workbook (.twb) from the validated registry.

WHAT IT WRITES
  tableau/RetailPulse.twb             6 data sources + 2 parameters + 100 calculated fields
                                      + 8 KPI check sheets (sheet names from the dashboard spec)
  tableau/RetailPulse_model_only.twb  the same model with one empty sheet: a fallback if
                                      the KPI sheets ever stop the workbook from opening

  For every data source: the text-file connections (tableau/data and
  tableau/data/analytical), the tables in the order of the registry, the
  relationships (root table to each related table, on the documented key),
  every column with its data type, role and FINAL caption (CSV name, or the
  documented rename such as rev_order_id), and the calculated fields with
  their number formats. Field and calculation names are exactly those in
  tableau/calculated_fields.md, so nothing has to be renamed or retyped.

HOW THE FORMAT WAS DETERMINED (no guessing)
  The XML mirrors what Tableau Desktop Public Edition 2026.3.2 itself writes:
  element order, attributes, internal names for duplicate columns
  ("[order_id (vw_review_summary.csv)]"), metadata-record type codes and the
  relationship ("object-graph") syntax were copied from a workbook saved by
  that build, and calculated-field / parameter / worksheet markup from the
  Superstore sample shipped with it. scripts/validate_tableau_workbook.py
  checks the result against Tableau's official 2026.3 XSD and against the
  registry.

DASHBOARD WORKBOOK (build(..., with_dashboards=True), used for tableau/RetailPulse_Final.*)
  adds the 41 chart worksheets, 8 dashboards, shared filter controls, dashboard actions and
  formatting defined in scripts/tableau_charts.py (from tableau/dashboard_specification.md), on
  10 Tableau data sources: two-table views (root + one related table) of the 6 registry data
  sources, because Tableau 2026.3.2 cannot query a data source in which several related tables
  share the root key (error 1B885FB3).

PATHS
  Tableau stores the absolute folder of each CSV. The default is this
  repository's tableau/data; pass --data-dir to point elsewhere. The generated
  .twb files are git-ignored (they contain this machine's path); re-run the
  script on any machine to regenerate them.

Usage:
  ./venv/bin/python scripts/build_tableau_workbook.py
  ./venv/bin/python scripts/build_tableau_workbook.py --data-dir /path/to/tableau/data
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys
import uuid
import xml.etree.ElementTree as ET

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tableau_registry import (BRL, CALCS, DATA_SOURCES, DAYS, DEC2, FIELDS, HEADERS, INT,  # noqa: E402
                              PARAMETERS, PCT, TAB)
import tableau_charts as C  # noqa: E402

SOURCE_BUILD = "2026.3.2 (20263.26.1120.1648)"     # the installed Tableau Desktop Public Edition
VERSION = "18.1"                                   # the document version that build writes
MANIFEST = ["AnimationOnByDefault", "MarkAnimation", "ObjectModelEncapsulateLegacy", "ObjectModelTableType",
            "SchemaViewerObjectModel", "SheetIdentifierTracking", "WindowsPersistSimpleIdentifiers"]
# Declared only when the workbook contains <manual-sort>/<computed-sort>: without it Tableau
# 2026.3.2 reads sorts in the older format and rejects <manual-sort> (error D2E8DA72). The
# Superstore sample shipped with that build declares it alongside its 14 <manual-sort> elements.
SORT_FLAG = "SortTagCleanup"
REMOTE_TYPE = {"string": "129", "integer": "20", "real": "5", "date": "133", "datetime": "135"}
AGGREGATION = {"string": "Count", "integer": "Sum", "real": "Sum", "date": "Year", "datetime": "Year"}
# numeric columns used as discrete axes (dimension), as the dashboard specification requires
NUMERIC_DIMENSIONS = {"months_since_acquisition", "review_score", "total_orders", "stage_order", "order_year",
                      "r_score", "f_score", "m_score", "is_repeat_customer"}
# display names for 0/1 members (shown on the One-time vs Repeat chart)
ALIASES = {"is_repeat_customer": {0: "One-time", 1: "Repeat"}}
FORMATS = {BRL: 'c"R$ "#,##0.00;-"R$ "#,##0.00', PCT: "p0.00%", INT: "n#,##0", DEC2: "n#,##0.0000",
           DAYS: "n#,##0.00"}

# KPI check sheets: (sheet name from the specification, data source, measure IDs in display order)
KPI_SHEETS = [
    ("1.0 KPIs", "RP Orders", ["M01", "M02", "M03", "M06", "M07"]),
    ("1.5 YoY Jan–Aug", "RP Orders", ["M15", "M13", "M14"]),
    ("2.0 KPIs", "RP Customers", ["M16", "M19", "M18", "M20", "M21"]),
    ("3.0 KPIs", "RP Categories", ["M24", "M26", "M25", "N07"]),
    ("4.0 KPIs", "RP Sellers", ["M30", "M29", "M34", "M32", "M33"]),
    ("5.0 KPIs", "RP Orders", ["M36", "M40", "M41", "M38", "M44", "M08"]),
    ("5.6 Stage Shares", "RP Orders", ["N24", "N23", "N22", "N21", "N17"]),
    ("6.0 KPIs", "RP Orders", ["M46", "M47", "M48", "M45", "N25"]),
]


# ---- deterministic identifiers (same input -> same file) -----------------------------
def _h(text: str, n: int, alphabet: str) -> str:
    digest = int(hashlib.sha256(text.encode()).hexdigest(), 16)
    out = []
    for _ in range(n):
        digest, r = divmod(digest, len(alphabet))
        out.append(alphabet[r])
    return "".join(out)


LOWER = "0123456789abcdefghijklmnopqrstuvwxyz"
federated_name = lambda ds: "federated." + _h("ds:" + ds, 28, LOWER)
textscan_name = lambda ds, folder: "textscan." + _h(f"conn:{ds}:{folder}", 28, LOWER)
object_id = lambda ds, t: f"{t}.csv_" + hashlib.md5(f"obj:{ds}:{t}".encode()).hexdigest().upper()
hyper_name = lambda ds: "hyper." + _h("hyper:" + ds, 28, LOWER)
HYPER_SCHEMA = "Extract"          # schema Tableau's own .hyper files use (World Indicators sample)
det_uuid = lambda key: "{" + str(uuid.UUID(hashlib.md5(key.encode()).hexdigest())).upper() + "}"


# ---- column types from the actual CSVs ----------------------------------------------------
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def infer_types(folder: Path, table: str) -> dict[str, str]:
    df = pd.read_csv(folder / f"{table}.csv", low_memory=False)
    types = {}
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_integer_dtype(s):
            types[col] = "integer"
        elif pd.api.types.is_float_dtype(s):
            types[col] = "real"
        else:
            v = s.dropna().astype(str)
            if len(v) and v.str.match(DATE_RE).all():
                types[col] = "date"
            elif len(v) and v.str.match(DATETIME_RE).all():
                types[col] = "datetime"
            else:
                types[col] = "string"
    return types


def role_type(col: str, dtype: str) -> tuple[str, str]:
    if dtype == "string":
        return "dimension", "nominal"
    if dtype in ("date", "datetime"):
        return "dimension", "ordinal"
    if col in NUMERIC_DIMENSIONS:
        return "dimension", "ordinal"
    return "measure", "quantitative"


# ---- model of one data source ---------------------------------------------------------------
class SourceModel:
    """Tables, internal names, captions and types for one data source (Tableau's naming rules)."""

    def __init__(self, ds: str, data_dir: Path, mode: str = "text", hyper_db: str | None = None,
                 tables: list[str] | None = None, caption: str | None = None):
        """mode 'text': text-file connections to the CSVs (live).
        mode 'hyper': one connection to a .hyper file holding every table of the data source in schema
        "Extract" (the pattern of the World Indicators sample shipped with Tableau Public); hyper_db is the
        dbname Tableau stores (absolute path for a .twb, package-relative for a .twbx).
        tables/caption: a Tableau data source over a subset of the registry data source's tables (the root
        and one related table), with the registry's field names, internal names and calculations."""
        assert mode in ("text", "hyper") and (mode == "text" or hyper_db)
        self.mode, self.hyper_db = mode, hyper_db
        self.ds = ds
        self.caption = caption or ds
        self.name = federated_name(self.caption)
        all_tables = DATA_SOURCES[ds]
        self.tables = [x for x in all_tables if tables is None or x[0] in tables]
        self.folder_of = {t: (data_dir if d.name == "data" else data_dir / "analytical") for t, d, _, _ in self.tables}
        self.folders = []
        for t, *_ in self.tables:
            f = self.folder_of[t]
            if f not in self.folders:
                self.folders.append(f)
        self.conn_of_folder = {f: textscan_name(ds, f.name) for f in self.folders}
        self.types = {t: infer_types(self.folder_of[t], t) for t, *_ in self.tables}
        caption_of = {(tbl, col): cap for cap, (tbl, col) in FIELDS[ds].items()}
        self.columns = []           # (table, col, internal, caption, dtype, ordinal)
        seen, ordinal = set(), 0
        keep = {t for t, *_ in self.tables}
        for t, *_ in all_tables:                 # internal names follow the full model, so formulas match
            for col in HEADERS[t]:
                internal = f"[{col}]" if col not in seen else f"[{col} ({self.rel(t)})]"
                seen.add(col)
                if t in keep:
                    self.columns.append((t, col, internal, caption_of[(t, col)], self.types[t][col], ordinal))
                    ordinal += 1
        self.internal_of_caption = {c[3]: c[2] for c in self.columns}
        self.col_by_internal = {c[2]: c for c in self.columns}
        self.calcs = [c for c in CALCS if c["ds"] == ds]
        if tables is not None:                   # keep the calculations whose every reference is available
            names, ok = set(self.internal_of_caption) | set(PARAMETERS), []
            changed = True
            while changed:
                changed = False
                for c in self.calcs:
                    if c not in ok and all(r in names for r in re.findall(r"\[([^\]]+)\]", c["formula"])):
                        ok.append(c)
                        names.add(c["name"])
                        changed = True
            self.calcs = [c for c in self.calcs if c in ok]
        self.calc_internal = {c["name"]: f"[RP_{c['id']}]" for c in self.calcs}

    def rel(self, t: str) -> str:
        """Logical table name Tableau uses: 'vw_order_summary.csv' for a text file, 'vw_order_summary' in a .hyper."""
        return f"{t}.csv" if self.mode == "text" else t

    def objid(self, t: str) -> str:
        return object_id(self.ds, t) if self.mode == "text" else \
            f"{t}_" + hashlib.md5(f"obj:{self.ds}:{t}".encode()).hexdigest().upper()

    def conn_name(self, t: str) -> str:
        return self.conn_of_folder[self.folder_of[t]] if self.mode == "text" else hyper_name(self.caption)

    def translate(self, formula: str) -> str:
        """Display names in the registry formula -> Tableau internal names."""
        def sub(m):
            tok = m.group(1)
            if tok in self.calc_internal:
                return self.calc_internal[tok]
            if tok in PARAMETERS:
                return f"[Parameters].[{tok}]"
            if tok in self.internal_of_caption:
                return self.internal_of_caption[tok]
            raise KeyError(f"{self.ds}: unknown reference [{tok}] in formula")
        return re.sub(r"\[([^\]]+)\]", sub, formula)

    def calc_datatype(self, c) -> tuple[str, str, str]:
        f = c["formula"]
        if c["kind"] == "row-level":
            if f.startswith("DATETRUNC"):
                return "date", "dimension", "ordinal"
            if f.startswith("CASE"):
                return "integer", "dimension", "ordinal"
            if "=" in f and " THEN " not in f:
                return "boolean", "dimension", "nominal"
            return "real", "measure", "quantitative"
        if c["id"] in ("H05", "H07", "H09"):
            return "boolean", "dimension", "nominal"
        if c["fmt"] == INT:
            if re.search(r"\b(COUNTD?|RANK_DENSE)\(", f):
                return "integer", "measure", "quantitative"
            refs = [self.col_by_internal.get(self.internal_of_caption.get(r)) for r in re.findall(r"\[([^\]]+)\]", f)]
            if refs and all(r is not None and r[4] == "integer" for r in refs):
                return "integer", "measure", "quantitative"
        return "real", "measure", "quantitative"

    def calc_deps(self, ids: list[str]) -> tuple[list, list]:
        """Transitive closure: calculations and base columns the given calculations use."""
        by_name = {c["name"]: c for c in self.calcs}
        calcs, cols, todo = {}, {}, [c for c in self.calcs if c["id"] in ids]
        while todo:
            c = todo.pop()
            if c["id"] in calcs:
                continue
            calcs[c["id"]] = c
            for tok in re.findall(r"\[([^\]]+)\]", c["formula"]):
                if tok in by_name:
                    todo.append(by_name[tok])
                elif tok in self.internal_of_caption:
                    cols[self.internal_of_caption[tok]] = self.col_by_internal[self.internal_of_caption[tok]]
        return list(calcs.values()), list(cols.values())


# ---- XML helpers ---------------------------------------------------------------------------
def sub(parent, tag, **attrs):
    return ET.SubElement(parent, tag, {k.replace("_", "-"): str(v) for k, v in attrs.items()})


def relation_el(parent, m: SourceModel, table: str):
    if m.mode == "hyper":         # a .hyper table carries its own schema: no <columns> (as in World Indicators)
        return sub(parent, "relation", connection=m.conn_name(table), name=table,
                   table=f"[{HYPER_SCHEMA}].[{table}]", type="table")
    rel = sub(parent, "relation", connection=m.conn_of_folder[m.folder_of[table]], name=f"{table}.csv",
              table=f"[{table}#csv]", type="table")
    cols = sub(rel, "columns", character_set="UTF-8", header="yes", locale="en_US", separator=",")
    for i, col in enumerate(HEADERS[table]):
        sub(cols, "column", datatype=m.types[table][col], name=col, ordinal=i)
    return rel


def column_el(parent, internal, caption, dtype, role, typ, fmt=None):
    attrs = {"caption": caption, "datatype": dtype} if caption is not None else {"datatype": dtype}
    if fmt:
        attrs["default-format"] = fmt
    attrs.update({"name": internal, "role": role, "type": typ})
    return ET.SubElement(parent, "column", attrs)


def calc_column_el(parent, m: SourceModel, c):
    dtype, role, typ = m.calc_datatype(c)
    el = column_el(parent, m.calc_internal[c["name"]], c["name"], dtype, role, typ, FORMATS.get(c["fmt"]))
    calc = sub(el, "calculation", **{"class": "tableau", "formula": m.translate(c["formula"])})
    if c["kind"] == "table calculation":
        sub(calc, "table-calc", ordering_type="Rows")
    return el


def datasource_el(parent, m: SourceModel, measure_names: bool = False, extra_bins: list | None = None):
    """measure_names: declare the built-in [:Measure Names] field, as Tableau does for every data source
    whose sheets use Measure Names (Superstore sample). Without it Tableau 2026.3.2 logs "Namespace
    unexpectedly missing field '[...].[:Measure Names]'" when a KPI sheet is drawn."""
    ds = sub(parent, "datasource", caption=m.caption, inline="true", name=m.name, version=VERSION)
    conn = sub(ds, "connection", **{"class": "federated"})
    named = sub(conn, "named-connections")
    if m.mode == "hyper":
        nc = sub(named, "named-connection", caption=m.caption, name=hyper_name(m.caption))
        sub(nc, "connection", **{"authentication": "auth-none", "author-locale": "en_US", "class": "hyper",
                                 "dbname": m.hyper_db, "default-settings": "yes", "port": "", "sslmode": "",
                                 "username": "tableau_internal_user"})
    for f in (m.folders if m.mode == "text" else []):
        nc = sub(named, "named-connection", caption=f.name, name=m.conn_of_folder[f])
        first = next(t for t, *_ in m.tables if m.folder_of[t] == f)
        sub(nc, "connection", **{"class": "textscan", "directory": str(f), "filename": f"{first}.csv",
                                 "password": "", "server": ""})
    if len(m.tables) == 1:
        relation_el(conn, m, m.tables[0][0])
    else:
        coll = sub(conn, "relation", type="collection")
        for t, *_ in m.tables:
            relation_el(coll, m, t)
        cols = sub(conn, "cols")
        for t, col, internal, *_ in sorted(m.columns, key=lambda c: c[2]):
            sub(cols, "map", key=internal, value=f"[{m.rel(t)}].[{col}]")
    recs = sub(conn, "metadata-records")
    for t, *_ in (m.tables if m.mode == "text" else []):      # hyper connections carry no capability records
        r = sub(recs, "metadata-record", **{"class": "capability"})
        for tag, val in [("remote-name", None), ("remote-type", "0"), ("parent-name", f"[{t}.csv]"),
                         ("remote-alias", None), ("aggregation", "Count"), ("contains-null", "true")]:
            e = sub(r, tag)
            if val is not None:
                e.text = val
        attrs = sub(r, "attributes")
        for k, v in [("character-set", '"UTF-8"'), ("collation", '"en_US"'), ("field-delimiter", '","'),
                     ("header-row", '"true"'), ("locale", '"en_US"'), ("single-char", '""')]:
            a = sub(attrs, "attribute", datatype="string", name=k)
            a.text = v
    for t, col, internal, caption, dtype, ordinal in m.columns:
        r = sub(recs, "metadata-record", **{"class": "column"})
        fields = [("remote-name", col), ("remote-type", REMOTE_TYPE[dtype]), ("local-name", internal),
                  ("parent-name", f"[{m.rel(t)}]"), ("remote-alias", col), ("ordinal", str(ordinal)),
                  ("local-type", dtype), ("aggregation", AGGREGATION[dtype])]
        if dtype == "string":
            fields += [("scale", "1"), ("width", "1073741823")]
        fields += [("contains-null", "true")]
        for tag, val in fields:
            sub(r, tag).text = val
        if dtype == "string":
            sub(r, "collation", flag="0", name="LEN_RGB" if m.mode == "text" else "LEN_RUS")
        sub(r, "object-id").text = f"[{m.objid(t)}]"
    sub(ds, "aliases", enabled="yes")
    if measure_names:
        column_el(ds, "[:Measure Names]", None, "string", "dimension", "nominal")
    if len(m.tables) > 1:
        for t, *_ in sorted(m.tables):
            column_el(ds, f"[__tableau_internal_object_id__].[{m.objid(t)}]", m.rel(t), "table",
                      "measure", "quantitative")
    entries = [(c[2], ("col", c)) for c in m.columns] + [(m.calc_internal[c["name"]], ("calc", c)) for c in m.calcs]
    entries += [(b[0], ("bin", b)) for b in (extra_bins or [])]
    for _, (kind, item) in sorted(entries, key=lambda e: e[0].lower()):
        if kind == "col":
            t, col, internal, caption, dtype, _ = item
            role, typ = role_type(col, dtype)
            el = column_el(ds, internal, caption, dtype, role, typ)
            if extra_bins is not None and col in ALIASES:
                al = sub(el, "aliases")
                for k, v in ALIASES[col].items():
                    sub(al, "alias", key=str(k), value=v)
        elif kind == "calc":
            calc_column_el(ds, m, item)
        else:
            bin_column_el(ds, *item)
    sub(ds, "layout", dim_ordering="alphabetic", measure_ordering="alphabetic", show_structure="true")
    if len(m.tables) > 1:
        og = sub(ds, "object-graph")
        objs = sub(og, "objects")
        for t, *_ in m.tables:
            o = sub(objs, "object", caption=m.rel(t), id=m.objid(t))
            relation_el(sub(o, "properties", context=""), m, t)
        rels = sub(og, "relationships")
        root = m.tables[0][0]
        for t, _, key, _ in m.tables[1:]:
            rel = sub(rels, "relationship")
            e = sub(rel, "expression", op="=")
            sub(e, "expression", op=f"[{key}]")
            sub(e, "expression", op=f"[{key} ({m.rel(t)})]")
            sub(rel, "first-end-point", object_id=m.objid(root))
            sub(rel, "second-end-point", object_id=m.objid(t))
    return ds


def parameters_el(parent, lists: dict[str, list[str]] | None = None):
    """lists: allowed values for a parameter (shown as a dropdown), e.g. the 74 categories for p_category."""
    lists = lists or {}
    ds = sub(parent, "datasource", hasconnection="false", inline="true", name="Parameters", version=VERSION)
    sub(ds, "aliases", enabled="yes")
    for name, (dtype, value, _) in PARAMETERS.items():
        col = ET.SubElement(ds, "column", {"caption": name, "datatype": dtype.lower(), "name": f"[{name}]",
                                           "param-domain-type": "list" if name in lists else "any", "role": "measure",
                                           "type": "nominal", "value": f'"{value}"'})
        sub(col, "calculation", **{"class": "tableau", "formula": f'"{value}"'})
        if name in lists:
            mem = sub(col, "members")
            for v in lists[name]:
                sub(mem, "member", value=f'"{v}"')


def empty_table(ws):
    table = sub(ws, "table")
    view = sub(table, "view")
    sub(view, "datasources")
    sub(view, "aggregation", value="true")
    sub(table, "style")
    pane = sub(sub(table, "panes"), "pane", selection_relaxation_option="selection-relaxation-allow")
    sub(sub(pane, "view"), "breakdown", value="auto")
    sub(pane, "mark", **{"class": "Automatic"})
    sub(table, "rows")
    sub(table, "cols")


def kpi_worksheet(parent, sheet: str, m: SourceModel, ids: list[str]):
    ws = sub(parent, "worksheet", name=sheet)
    table = sub(ws, "table")
    view = sub(table, "view")
    dss = sub(view, "datasources")
    sub(dss, "datasource", caption=m.ds, name=m.name)
    deps = sub(view, "datasource-dependencies", datasource=m.name)
    calcs, cols = m.calc_deps(ids)
    entries = [(c[2], ("col", c)) for c in cols] + [(m.calc_internal[c["name"]], ("calc", c)) for c in calcs]
    for _, (kind, item) in sorted(entries, key=lambda e: e[0].lower()):
        if kind == "col":
            t, col, internal, caption, dtype, _ = item
            role, typ = role_type(col, dtype)
            column_el(deps, internal, caption, dtype, role, typ)
        else:
            calc_column_el(deps, m, item)
    inst = {cid: f"[usr:RP_{cid}:qk]" for cid in ids}
    for cid in sorted(ids):
        sub(deps, "column-instance", column=f"[RP_{cid}]", derivation="User", name=inst[cid], pivot="key",
            type="quantitative")
    flt = sub(view, "filter", **{"class": "categorical", "column": f"[{m.name}].[:Measure Names]"})
    union = ET.SubElement(flt, "groupfilter", {"function": "union", "user:op": "manual"})
    for cid in ids:
        sub(union, "groupfilter", function="member", level="[:Measure Names]", member=f'"[{m.name}].{inst[cid]}"')
    ms = sub(view, "manual-sort", column=f"[{m.name}].[:Measure Names]", direction="ASC")
    dic = sub(ms, "dictionary")
    for cid in ids:
        sub(dic, "bucket").text = f'"[{m.name}].{inst[cid]}"'
    sub(view, "aggregation", value="true")
    sub(table, "style")
    pane = sub(sub(table, "panes"), "pane", selection_relaxation_option="selection-relaxation-allow")
    sub(sub(pane, "view"), "breakdown", value="auto")
    sub(pane, "mark", **{"class": "Text"})
    enc = sub(pane, "encodings")
    sub(enc, "text", column=f"[{m.name}].[Multiple Values]")
    sub(table, "rows")
    sub(table, "cols").text = f"[{m.name}].[:Measure Names]"
    sub(ws, "simple-id", uuid=det_uuid("ws:" + sheet))
    return ws


def window_el(parent, sheet: str, maximized: bool, hidden: bool = False):
    attrs = {"class": "worksheet"}
    if hidden:
        attrs["hidden"] = "true"
    if maximized:
        attrs["maximized"] = "true"
    attrs["name"] = sheet
    w = ET.SubElement(parent, "window", attrs)
    cards = sub(w, "cards")
    left = sub(sub(cards, "edge", name="left"), "strip", size="160")
    for t in ("pages", "filters", "marks"):
        sub(left, "card", type=t)
    top = sub(cards, "edge", name="top")
    for size, t in (("2147483647", "columns"), ("2147483647", "rows"), ("31", "title")):
        sub(sub(top, "strip", size=size), "card", type=t)
    sub(w, "simple-id", uuid=det_uuid("win:" + sheet))


# =====================================================================================================
# Chart worksheets, dashboards and actions (definitions in scripts/tableau_charts.py)
# =====================================================================================================
SUFFIX = {"nominal": "nk", "ordinal": "ok", "quantitative": "qk"}


def q(v) -> str:
    """Member literal as Tableau writes it: strings quoted, numbers and booleans bare."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return f'"{v}"'


class SheetCtx:
    """Collects the columns and column instances one worksheet uses, and resolves pills to instance names."""

    def __init__(self, m: SourceModel, tc: dict | None = None):
        self.m, self.tc = m, tc or {}
        self.calc_ids: set[str] = set()
        self.cols: dict[str, tuple] = {}
        self.bins: dict[str, tuple] = {}
        self.inst: dict[str, dict] = {}

    def ds(self) -> str:
        return f"[{self.m.name}]"

    def full(self, inst: str) -> str:
        return f"{self.ds()}.{inst}"

    def _base(self, caption: str):
        internal = self.m.internal_of_caption[caption]
        self.cols[internal] = self.m.col_by_internal[internal]
        return internal, self.m.col_by_internal[internal]

    def _calc(self, name: str):
        c = next(c for c in self.m.calcs if c["name"] == name)
        self.calc_ids.add(c["id"])
        return self.m.calc_internal[name], c

    def _add(self, name, column, derivation, typ, tc=None):
        if name not in self.inst:
            self.inst[name] = {"column": column, "derivation": derivation, "name": name, "pivot": "key", "type": typ,
                               "tc": tc}
        return name

    def _tc_spec(self, pill):
        spec = self.tc.get(pill)
        if spec is None:
            return None
        if isinstance(spec, str):
            return {"ordering-type": spec}
        kind, field = spec
        return {"ordering-field": self.full(self.resolve(field)), "ordering-type": "Field"}

    def resolve(self, pill: str) -> str:
        """Pill -> column-instance name (without the data source prefix)."""
        k, f = pill.split(":", 1) if ":" in pill else (pill, "")
        if k == "D":
            if f in self.m.internal_of_caption:
                internal, col = self._base(f)
                role, typ = role_type(col[1], col[4])
                typ = "nominal" if col[4] == "string" else "ordinal"
            else:                                   # a row-level calculation used as a dimension
                internal, c = self._calc(f)
                typ = "ordinal"
            bare = internal[1:-1]
            return self._add(f"[none:{bare}:{SUFFIX[typ]}]", internal, "None", typ)
        if k == "Q":
            internal = self._base(f)[0] if f in self.m.internal_of_caption else self._calc(f)[0]
            return self._add(f"[none:{internal[1:-1]}:qk]", internal, "None", "quantitative")
        if k == "S":
            internal, _ = self._base(f)
            return self._add(f"[sum:{internal[1:-1]}:qk]", internal, "Sum", "quantitative")
        if k in ("C", "A"):
            internal, c = self._calc(f)
            dtype, role, typ = self.m.calc_datatype(c)
            if c["kind"] == "row-level":
                return self._add(f"[none:{internal[1:-1]}:{SUFFIX[typ]}]", internal, "None", typ)
            typ = "nominal" if dtype == "boolean" else "quantitative"
            return self._add(f"[usr:{internal[1:-1]}:{SUFFIX[typ]}]", internal, "User", typ, self._tc_spec(pill))
        if k == "B":
            internal, _ = self._calc(f)
            return self._add(f"[none:{internal[1:-1]}:nk]", internal, "None", "nominal")
        if k in ("M", "MD"):
            internal, _ = self._calc(f)
            typ = "quantitative" if k == "M" else "ordinal"
            return self._add(f"[tmn:{internal[1:-1]}:{SUFFIX[typ]}]", internal, "Month-Trunc", typ)
        if k == "RANK":
            internal, _ = self._base(f)
            spec = self._tc_spec(pill) or {"ordering-type": "Columns"}
            spec = {**spec, "rank-options": "Competition,Descending", "type": "Rank"}
            return self._add(f"[rank:sum:{internal[1:-1]}:qk]", internal, "Sum", "quantitative", spec)
        if k == "BIN":
            size = C.BINS[(self.m.caption, f)]
            src = self._base(f)[0] if f in self.m.internal_of_caption else self._calc(f)[0]
            name = f"[{src[1:-1]} (bin)]"
            self.bins[name] = (f"{f} (bin)", src, size)
            return self._add(f"[none:{name[1:-1]}:ok]", name, "None", "ordinal")
        raise ValueError(pill)

    def shelf(self, pills: list[str], mv_inst: bool = True) -> str:
        parts = []
        for p in pills:
            if p == "MV":
                parts.append(f"{self.ds()}.[Multiple Values]")
            elif p == "MN":
                parts.append(f"{self.ds()}.[:Measure Names]")
            else:
                parts.append(self.full(self.resolve(p)))
        if not parts:
            return ""
        if len(parts) == 1:
            return parts[0]
        dims = all(not self._is_measure(p) for p in pills)
        return "(" + (" / " if dims else " + ").join(parts) + ")"

    def _is_measure(self, p):
        return p == "MV" or p.split(":")[0] in ("C", "S", "RANK", "A") and not p.startswith("B:")

    def write_deps(self, view):
        """<datasources> and <datasource-dependencies> (Parameters first, as Tableau writes them)."""
        calcs, cols = self.m.calc_deps(sorted(self.calc_ids))
        for internal, col in self.cols.items():
            if col not in cols:
                cols.append(col)
        params = sorted({p for c in calcs for p in PARAMETERS if f"[{p}]" in c["formula"]})
        dss = sub(view, "datasources")
        sub(dss, "datasource", caption=self.m.caption, name=self.m.name)
        if params:
            sub(dss, "datasource", name="Parameters")
            pdeps = sub(view, "datasource-dependencies", datasource="Parameters")
            for p in params:
                param_column_el(pdeps, p)
        deps = sub(view, "datasource-dependencies", datasource=self.m.name)
        entries = [(c[2], ("col", c)) for c in cols] + [(self.m.calc_internal[c["name"]], ("calc", c)) for c in calcs]
        entries += [(name, ("bin", (name, *b))) for name, b in self.bins.items()]
        for _, (kind, item) in sorted(entries, key=lambda e: e[0].lower()):
            if kind == "col":
                t, col, internal, caption, dtype, _ = item
                role, typ = role_type(col, dtype)
                column_el(deps, internal, caption, dtype, role, typ)
            elif kind == "calc":
                calc_column_el(deps, self.m, item)
            else:
                bin_column_el(deps, *item)
        for name in sorted(self.inst, key=lambda n: n.lower()):
            a = self.inst[name]
            ci = sub(deps, "column-instance", column=a["column"], derivation=a["derivation"], name=name, pivot="key",
                     type=a["type"])
            if a["tc"]:
                sub(ci, "table-calc", **{k.replace("-", "_"): v for k, v in a["tc"].items()})


def bin_column_el(parent, name, caption, src, size):
    dtype = "integer" if float(size).is_integer() else "real"
    el = column_el(parent, name, caption, dtype, "dimension", "ordinal")
    sub(el, "calculation", **{"class": "bin", "decimals": "-1" if dtype == "real" else "0", "formula": src,
                               "peg": "0", "size": str(size)})
    return el


def param_column_el(parent, name):
    dtype, value, _ = PARAMETERS[name]
    col = ET.SubElement(parent, "column", {"caption": name, "datatype": dtype.lower(), "name": f"[{name}]",
                                           "param-domain-type": "any", "role": "measure", "type": "nominal",
                                           "value": f'"{value}"'})
    sub(col, "calculation", **{"class": "tableau", "formula": f'"{value}"'})


def filter_el(view, ctx: SheetCtx, kind: str, pill: str, value, group: int | None = None):
    """Filters in the forms Tableau writes (categorical member/except/top-N, quantitative range/non-null)."""
    inst = ctx.resolve(pill)
    col = ctx.full(inst)
    attrs = {"class": "categorical", "column": col}
    if kind in ("ctxtrue",):
        attrs["context"] = "true"
    if group is not None:
        attrs["filter-group"] = str(group)
    if kind in ("range", "min", "nonnull"):
        attrs = {"class": "quantitative", "column": col}
        if group is not None:
            attrs["filter-group"] = str(group)
        attrs["included-values"] = "non-null" if kind == "nonnull" else "in-range"
        f = ET.SubElement(view, "filter", attrs)
        lo, hi = (value, None) if kind == "min" else (value if kind == "range" else (None, None))
        if lo is not None:
            sub(f, "min").text = str(lo)
        if hi is not None:
            sub(f, "max").text = str(hi)
        return f
    f = ET.SubElement(view, "filter", attrs)
    lvl = inst
    if kind in ("true", "ctxtrue", "tctrue"):
        ET.SubElement(f, "groupfilter", {"function": "member", "level": lvl, "member": "true",
                                         "user:ui-domain": "database", "user:ui-enumeration": "inclusive",
                                         "user:ui-marker": "enumerate"})
    elif kind == "member":
        ET.SubElement(f, "groupfilter", {"function": "member", "level": lvl, "member": q(value),
                                         "user:ui-domain": "database", "user:ui-enumeration": "inclusive",
                                         "user:ui-marker": "enumerate"})
    elif kind == "exclude":
        ex = ET.SubElement(f, "groupfilter", {"function": "except", "user:ui-domain": "database",
                                              "user:ui-enumeration": "exclusive", "user:ui-marker": "enumerate"})
        sub(ex, "groupfilter", function="level-members", level=lvl)
        for v in value:
            sub(ex, "groupfilter", function="member", level=lvl, member=q(v))
    elif kind == "all":
        ET.SubElement(f, "groupfilter", {"function": "level-members", "level": lvl, "user:ui-domain": "database",
                                         "user:ui-enumeration": "all", "user:ui-marker": "enumerate"})
    elif kind == "top":
        n, by = value
        by_inst = ctx.resolve(by)
        by_expr = ctx.inst[by_inst]["column"]
        end = ET.SubElement(f, "groupfilter", {"count": str(n), "end": "top", "function": "end", "units": "records",
                                               "user:ui-marker": "end", "user:ui-top-by-field": "true"})
        order = ET.SubElement(end, "groupfilter", {"direction": "DESC", "expression": by_expr, "function": "order",
                                                   "user:ui-marker": "order"})
        ET.SubElement(order, "groupfilter", {"function": "level-members", "level": lvl, "user:ui-enumeration": "all",
                                             "user:ui-marker": "enumerate"})
    else:
        raise ValueError(kind)
    return f


def palette_rules(style, ctx: SheetCtx, spec: dict):
    rules = []
    for pill, mapping in (spec.get("palette") or {}).items():
        field = f"{ctx.ds()}.[:Measure Names]" if pill == "MN" else ctx.full(ctx.resolve(pill))
        enc = ET.Element("encoding", {"attr": "color", "field": field, "type": "palette"})
        for key, colour in mapping.items():
            bucket = q(ctx.full(ctx.resolve(key))) if pill == "MN" else q(key)
            sub(sub(enc, "map", to=colour), "bucket").text = bucket
        rules.append(enc)
    for key, colours in (("diverge", None), ("sequential", ["#FBE3D6", C.ORANGE]), ("sequential_red", ["#FBE0E0", "#B83A3A"])):
        if spec.get(key):
            field = ctx.full(ctx.resolve(spec[key]))
            if colours is None:
                rules.append(ET.Element("encoding", {"attr": "color", "field": field, "palette": "tableau-orange-blue",
                                                     "type": "interpolated"}))
            else:
                enc = ET.Element("encoding", {"attr": "color", "field": field, "type": "custom-interpolated"})
                pal = sub(enc, "color-palette", custom="true", name="", type="ordered-sequential")
                for c in colours:
                    sub(pal, "color").text = c
                rules.append(enc)
    if rules:
        sr = sub(style, "style-rule", element="mark")
        for r in rules:
            sr.append(r)


def chart_worksheet(parent, spec: dict, m: SourceModel, groups: dict[str, list[tuple]]):
    """One chart (or KPI) worksheet. groups: shared dashboard filters [(pill, group id, title)] for this sheet."""
    name = spec["name"]
    kpi = spec.get("kpi")
    if kpi:
        names = {c["id"]: c["name"] for c in m.calcs}
        spec = {**spec, "mark": "Text", "rows": [], "cols": ["MN"], "enc": {"text": ["MV"]},
                "mv": [f"C:{names[i]}" for i in kpi]}
    tc = dict(spec.get("tc") or {})
    for f in spec.get("filters", []):
        if f[0] == "tctrue":
            tc[f[1]] = f[2]
    ctx = SheetCtx(m, tc)
    ws = sub(parent, "worksheet", name=name)
    if spec.get("title"):
        lo = sub(ws, "layout-options")
        C.text_runs(sub(lo, "title"), [(spec["title"], {"fontcolor": C.INK, "fontname": C.FONT_BOLD, "fontsize": "11"})])
    table = sub(ws, "table")
    view = sub(table, "view")
    # resolve everything first so the dependency block is complete
    rows = ctx.shelf(spec.get("rows", []))
    cols = ctx.shelf(spec.get("cols", []))
    enc = spec.get("enc") or {}
    mv = [ctx.resolve(p) for p in spec.get("mv", [])]
    enc_cols = []
    for key in ("color", "size", "wedge"):
        if enc.get(key):
            enc_cols.append((key, enc[key]))
    for key in ("lod", "tooltip", "text"):
        for p in enc.get(key, []):
            enc_cols.append((key, p))
    enc_inst = [(k, None if p in ("MN", "MV") else ctx.resolve(p), p) for k, p in enc_cols]
    flts = list(spec.get("filters", []))
    for pill, gid, _ in groups.get(name, []):
        flts.append(("all", pill, None, gid))
    flt_inst = [ctx.resolve(f[1]) for f in flts]
    sort = spec.get("sort")
    if sort and sort[0] != "manual":
        ctx.resolve(sort[0]), ctx.resolve(sort[2])
    elif sort:
        ctx.resolve(sort[1])
    if spec.get("refline"):
        [ctx.resolve(p) for p in spec["refline"]]
    for key in ("diverge", "sequential", "sequential_red"):
        if spec.get(key):
            ctx.resolve(spec[key])
    for pill, mapping in (spec.get("palette") or {}).items():
        if pill != "MN":
            ctx.resolve(pill)
    ctx.write_deps(view)
    # filters (Measure Names first, as on the KPI sheets), then the sheet's own and the shared ones
    if mv:
        flt = sub(view, "filter", **{"class": "categorical", "column": f"{ctx.ds()}.[:Measure Names]"})
        union = ET.SubElement(flt, "groupfilter", {"function": "union", "user:op": "manual"})
        for i in mv:
            sub(union, "groupfilter", function="member", level="[:Measure Names]", member=q(ctx.full(i)))
    for f in flts:
        filter_el(view, ctx, f[0], f[1], f[2], f[3] if len(f) > 3 else None)
    if mv:
        ms = sub(view, "manual-sort", column=f"{ctx.ds()}.[:Measure Names]", direction="ASC")
        dic = sub(ms, "dictionary")
        for i in mv:
            sub(dic, "bucket").text = q(ctx.full(i))
    if sort and sort[0] == "manual":
        ms = sub(view, "manual-sort", column=ctx.full(ctx.resolve(sort[1])), direction="ASC")
        dic = sub(ms, "dictionary")
        for v in sort[2]:
            sub(dic, "bucket").text = q(v)
    elif sort:
        sub(view, "computed-sort", column=ctx.full(ctx.resolve(sort[0])), direction=sort[1],
            using=ctx.full(ctx.resolve(sort[2])))
    on_shelf = set(re.findall(r"\[[^\]]+\]\.(\[[^\]]+\])", rows + cols)) | {i for _, i, _ in enc_inst if i}
    slices = [ctx.full(i) for i in dict.fromkeys(flt_inst) if i not in on_shelf]
    if slices:
        sl = sub(view, "slices")
        for s in slices:
            sub(sl, "column").text = s
    sub(view, "aggregation", value="true")
    style = sub(table, "style")
    palette_rules(style, ctx, spec)
    if spec.get("mark") == "Text":
        sr = sub(style, "style-rule", element="cell")
        big = bool(kpi)
        sub(sr, "format", attr="font-size", value="15" if big else "9")
        if big:
            sub(sr, "format", attr="font-weight", value="bold")
        sub(sr, "format", attr="color", value=C.INK)
    for pill, gid, title in groups.get(name, []):
        sr = sub(style, "style-rule", element="quick-filter")
        sub(sr, "format", attr="title", field=ctx.full(ctx.resolve(pill)), value=title)
    sr = sub(style, "style-rule", element="worksheet")
    sub(sr, "format", attr="font-family", value=C.FONT)
    pane = sub(sub(table, "panes"), "pane", selection_relaxation_option="selection-relaxation-allow")
    sub(sub(pane, "view"), "breakdown", value="auto")
    sub(pane, "mark", **{"class": spec.get("mark", "Automatic")})
    if enc_inst:
        encs = sub(pane, "encodings")
        tag = {"color": "color", "size": "size", "wedge": "wedge-size", "lod": "lod", "tooltip": "tooltip", "text": "text"}
        for k, i, p in enc_inst:
            col = (f"{ctx.ds()}.[:Measure Names]" if p == "MN" else f"{ctx.ds()}.[Multiple Values]" if p == "MV"
                   else ctx.full(i))
            sub(encs, tag[k], column=col)
    for n, p in enumerate(spec.get("refline") or []):
        i = ctx.full(ctx.resolve(p))
        sub(pane, "reference-line", axis_column=i, enable_instant_analytics="false", formula="median",
            id=f"refline{n}", label_type="none", probability="95", scope="per-table", value_column=i, z_order=str(n + 1))
    pst = []
    if spec.get("labels"):
        pst.append(("mark-labels-show", "true"))
        pst.append(("mark-labels-cull", "true"))
    if spec.get("color"):
        pst.append(("mark-color", spec["color"]))
    if pst:
        sr = sub(sub(pane, "style"), "style-rule", element="mark")
        for a, v in pst:
            sub(sr, "format", attr=a, value=v)
    sub(table, "rows").text = rows or None
    sub(table, "cols").text = cols or None
    sub(ws, "simple-id", uuid=det_uuid("ws:" + name))
    return ws


# ---- dashboards ---------------------------------------------------------------------------------------
class Zones:
    def __init__(self, width: int, height: int):
        self.W, self.H, self.next = width, height, 3

    def id(self):
        self.next += 1
        return self.next

    def box(self, parent, x, y, w, h, **attrs):
        a = {"h": str(round(h / self.H * 100000)), "id": str(self.id())}
        a.update({k.replace("_", "-"): str(v) for k, v in attrs.items()})
        a.update({"w": str(round(w / self.W * 100000)), "x": str(round(x / self.W * 100000)),
                  "y": str(round(y / self.H * 100000))})
        return ET.SubElement(parent, "zone", a)


def zone_style(z, background=None, margin="4", padding=None, border=None):
    st = sub(z, "zone-style")
    sub(st, "format", attr="border-color", value=border or "#000000")
    sub(st, "format", attr="border-style", value="solid" if border else "none")
    sub(st, "format", attr="border-width", value="1" if border else "0")
    sub(st, "format", attr="margin", value=margin)
    if padding:
        sub(st, "format", attr="padding", value=padding)
    if background:
        sub(st, "format", attr="background-color", value=background)
    return st


def text_zone(Z, parent, x, y, w, h, runs, background=None, margin="4", padding="4"):
    z = Z.box(parent, x, y, w, h, type_v2="text")
    C.text_runs(z, runs)
    zone_style(z, background, margin, padding)
    return z


def nav_button(Z, parent, x, y, w, h, label, target_uuid, active):
    z = Z.box(parent, x, y, w, h, type_v2="dashboard-object")
    b = sub(z, "button", action=f'tabdoc:goto-sheet window-id="{target_uuid}"', button_type="text")
    vs = sub(b, "button-visual-state")
    sub(vs, "caption").text = label
    sub(vs, "button-caption-font-style", fontcolor=C.WHITE, fontname=C.FONT_BOLD, fontsize="10")
    sub(vs, "format", attr="background-color", value=C.ORANGE if active else C.INK)
    zone_style(z, margin="3")
    return z


def dashboard_el(parent, d: dict, models: dict, filters: dict, inst_of: dict):
    W, H = 1400, d.get("height", 1150)
    Z = Zones(W, H)
    db = sub(parent, "dashboard", name=d["name"])
    st = sub(db, "style")
    sr = sub(st, "style-rule", element="table")
    sub(sr, "format", attr="background-color", value=C.BG)
    sub(db, "size", maxheight=str(H), maxwidth=str(W), minheight=str(H), minwidth=str(W), sizing_mode="fixed")
    # data sources used by filter and parameter controls
    used = filters.get(d["name"], [])
    dsn = sorted({inst_of[(fl[3][0], fl[0])][0] for fl in used})
    if used or d.get("detail"):
        dss = sub(db, "datasources")
        for ds in dsn:
            sub(dss, "datasource", caption=ds, name=models[ds].name)
        if d.get("detail"):
            sub(dss, "datasource", name="Parameters")
            pdeps = sub(db, "datasource-dependencies", datasource="Parameters")
            param_column_el(pdeps, d["detail"])
        for ds in dsn:
            deps = sub(db, "datasource-dependencies", datasource=models[ds].name)
            items = [inst_of[(fl[3][0], fl[0])] for fl in used if inst_of[(fl[3][0], fl[0])][0] == ds]
            seen = set()
            for _, col, inst in items:
                if col[2] not in seen:
                    seen.add(col[2])
                    role, typ = role_type(col[1], col[4])
                    column_el(deps, col[2], col[3], col[4], role, typ)
            for _, col, inst in items:
                if inst not in seen:
                    seen.add(inst)
                    typ = "nominal" if col[4] == "string" else "ordinal"
                    sub(deps, "column-instance", column=col[2], derivation="None", name=inst, pivot="key", type=typ)
    zones = sub(db, "zones")
    root = Z.box(zones, 0, 0, W, H, type_v2="layout-basic")
    col = Z.box(root, 0, 0, W, H, param="vert", type_v2="layout-flow")
    y = 0
    # header
    hdr_h = 62
    hdr = Z.box(col, 0, y, W, hdr_h, param="horz", type_v2="layout-flow")
    title = d["title"] if not d.get("detail") else (
        "Category: <[Parameters].[p_category]>" if d["detail"] == "p_category" else "Seller: <[Parameters].[p_seller]>")
    text_zone(Z, hdr, 0, y, 1000, hdr_h, [
        ("RetailPulse  ·  ", {"fontcolor": C.ORANGE, "fontname": C.FONT_BOLD, "fontsize": "18"}),
        (title, {"fontcolor": C.INK, "fontname": C.FONT_BOLD, "fontsize": "18"}),
        ("\n", {}),
        ((d["question"] + "   " if d["question"] else "") + C.PERIOD, {"fontcolor": C.GREY, "fontname": C.FONT,
                                                                       "fontsize": "10"})], background=C.WHITE,
              margin="0", padding="10")
    if d.get("detail"):
        pz = Z.box(hdr, 1000, y, 400, hdr_h, mode="compact" if d["detail"] == "p_category" else "type_in",
                   param=f"[Parameters].[{d['detail']}]", type_v2="paramctrl")
        zone_style(pz, C.WHITE, margin="0", padding="8")
    else:
        text_zone(Z, hdr, 1000, y, 400, hdr_h, [("Pages: use the dashboard tabs above", {"fontcolor": C.GREY,
                                                 "fontname": C.FONT, "fontsize": "10"})], background=C.WHITE,
                  margin="0", padding="10")
    y += hdr_h
    # filters + KPI strip
    kpi_h = 104
    band = Z.box(col, 0, y, W, kpi_h, param="horz", type_v2="layout-flow")
    fw = 230 if used else 0
    if used:
        fcol = Z.box(band, 0, y, fw, kpi_h, param="vert", type_v2="layout-flow")
        fh = kpi_h / len(used)
        for i, (pill, mode, title, sheets) in enumerate(used):
            ds, coldef, inst = inst_of[(sheets[0], pill)]
            fz = Z.box(fcol, 0, round(y + i * fh), fw, round(fh), mode=mode, name=sheets[0],
                       param=f"[{models[ds].name}].{inst}", type_v2="filter")
            zone_style(fz, C.WHITE, margin="2", padding="2")
    ks = C.kpis(d)
    kx, kw = fw, (W - fw) / len(ks)
    for n, k in enumerate(ks):
        w = W - round(kx) if n == len(ks) - 1 else round(kw)
        kz = Z.box(band, round(kx), y, w, kpi_h, name=k)
        zone_style(kz, C.WHITE, margin="4", padding="4")
        kx += kw
    y += kpi_h
    cap_h, foot_h = 66, 26
    total = sum(h for h, _ in d["rows"])
    avail = H - y - cap_h - foot_h
    for h, items in d["rows"]:
        h = round(h * avail / total)
        row = Z.box(col, 0, y, W, h, param="horz", type_v2="layout-flow")
        x = 0
        for n, (sheet, frac) in enumerate(items):
            w = W - x if n == len(items) - 1 else round(W * frac)
            z = Z.box(row, x, y, w, h, name=sheet)
            zone_style(z, C.WHITE, margin="4", padding="6")
            x += w
        y += h
    rest = H - y - foot_h
    text_zone(Z, col, 0, y, W, rest, [(" ".join(d["captions"]), {"fontcolor": C.INK, "fontname": C.FONT,
                                                                   "fontsize": "9"})], background=C.WHITE)
    y += rest
    text_zone(Z, col, 0, y, W, foot_h, [(C.FOOTER, {"fontcolor": C.GREY, "fontname": C.FONT, "fontsize": "8"})])
    sub(db, "simple-id", uuid=det_uuid("db:" + d["name"]))
    return db


def actions_el(wb, models):
    acts = sub(wb, "actions")
    legacy, params = [], []
    sheets_on = {d["name"]: [z for _, items in d["rows"] for z, _ in items] + C.kpis(d) for d in C.DASHBOARDS}
    for i, a in enumerate(C.ACTIONS, 1):
        name = f"[Action{i}_{hashlib.md5(a['caption'].encode() + a['dashboard'].encode()).hexdigest().upper()}]"
        if a["kind"] in ("filter", "goto"):
            act = sub(acts, "action", caption=a["caption"], name=name)
            sub(act, "activation", auto_clear="true", type="on-select" if a["kind"] == "filter" else "explicit")
            if a["kind"] == "filter":
                sub(act, "source", dashboard=a["dashboard"], type="sheet", worksheet=a["source"])
                exclude, target = a["exclude"], a["dashboard"]
            else:
                src = sub(act, "source", dashboard=a["dashboard"], type="sheet")
                for s in sheets_on[a["dashboard"]]:
                    if s not in a["sources"]:
                        sub(src, "exclude-sheet", name=s)
                exclude = [s for s in sheets_on[a["target"]] if s not in a["keep"]]
                target = a["target"]
            cmd = sub(act, "command", command="tsc:tsl-filter")
            sub(cmd, "param", name="exclude", value=",".join(exclude))
            sub(cmd, "param", name="special-fields", value="all")
            sub(cmd, "param", name="target", value=target)
        else:
            params.append((name, a))
    for name, a in params:
        m = models[a["ds"]]
        act = sub(acts, "edit-parameter-action", caption=a["caption"], name=name)
        sub(act, "activation", auto_clear="true", type="on-select")
        src = sub(act, "source", dashboard=a["dashboard"], type="sheet")
        for s in sheets_on[a["dashboard"]]:
            if s not in a["sources"]:
                sub(src, "exclude-sheet", name=s)
        sub(act, "agg-type", type="attr")
        sub(act, "clear-option", type="do-nothing", value="")
        ps = sub(act, "params")
        field = a["field"].split(":", 1)[1]
        sub(ps, "param", name="source-field", value=f"[{m.name}].{m.internal_of_caption[field]}")
        sub(ps, "param", name="target-parameter", value=f"[Parameters].[{a['param']}]")
    return acts


def build(data_dir: Path, with_kpi_sheets: bool, hyper_dbs: dict[str, str] | None = None,
          with_dashboards: bool = False) -> ET.ElementTree:
    """hyper_dbs: {data source: dbname} switches every data source to its .hyper file (extract).
    with_dashboards: add the 39 chart sheets, 8 dashboards and their actions (scripts/tableau_charts.py)."""
    if with_dashboards:
        return build_full(data_dir, hyper_dbs)
    return build_kpi(data_dir, with_kpi_sheets, hyper_dbs)


def build_full(data_dir: Path, hyper_dbs: dict[str, str] | None) -> ET.ElementTree:
    wb = ET.Element("workbook", {"original-version": VERSION, "source-build": SOURCE_BUILD, "source-platform": "mac",
                                 "version": VERSION, "xmlns:user": "http://www.tableausoftware.com/xml/user"})
    man = sub(wb, "document-format-change-manifest")
    for f in sorted(MANIFEST + [SORT_FLAG]):
        sub(man, f)
    prefs = sub(wb, "preferences")
    sub(prefs, "preference", name="ui.encoding.shelf.height", value="24")
    sub(prefs, "preference", name="ui.shelf.height", value="26")
    dss = sub(wb, "datasources")
    cats = sorted(pd.read_csv(data_dir / "analytical" / "dim_category.csv").category.dropna().unique())
    parameters_el(dss, {"p_category": cats})
    models = {}
    for cap, (reg, tables) in C.SOURCES.items():
        models[cap] = (SourceModel(reg, data_dir, "hyper", hyper_dbs[reg], tables, cap) if hyper_dbs
                       else SourceModel(reg, data_dir, tables=tables, caption=cap))
    # every sheet in display order: KPI sheets in their dashboard position, then the charts
    specs = [{"name": s, "ds": C.KPI_SOURCE.get(s, ds), "kpi": ids} for s, ds, ids in KPI_SHEETS] + C.CHARTS
    order = {d["name"]: i for i, d in enumerate(C.DASHBOARDS)}
    specs.sort(key=lambda s: tuple(int(x) for x in s["name"].split(" ")[0].split(".")))
    mn_sources = {s["ds"] for s in specs if s.get("kpi") or s.get("mv") or "MN" in s.get("rows", []) + s.get("cols", [])}
    extra = {ds: [] for ds in models}
    for (ds, field), size in C.BINS.items():
        m = models[ds]
        src = m.internal_of_caption.get(field) or m.calc_internal[field]
        extra[ds].append((f"[{src[1:-1]} (bin)]", f"{field} (bin)", src, size))
    for m in models.values():
        datasource_el(dss, m, measure_names=m.ds in mn_sources, extra_bins=extra[m.ds])
    # shared dashboard filters: one filter group per control, on every sheet it applies to
    groups: dict[str, list] = {}
    inst_of: dict = {}
    gid = 100
    for dname, ctrls in C.DASH_FILTERS.items():
        for pill, mode, title, sheets in ctrls:
            gid += 1
            for s in sheets:
                groups.setdefault(s, []).append((pill, gid, title))
                ds = next(x["ds"] for x in specs if x["name"] == s)
                m = models[ds]
                ctx = SheetCtx(m)
                inst = ctx.resolve(pill)
                internal = ctx.inst[inst]["column"]
                inst_of[(s, pill)] = (ds, m.col_by_internal[internal], inst)
    wss = sub(wb, "worksheets")
    for s in specs:
        chart_worksheet(wss, s, models[s["ds"]], groups)
    dbs = sub(wb, "dashboards")
    for d in C.DASHBOARDS:
        dashboard_el(dbs, d, models, C.DASH_FILTERS, inst_of)
    wins = sub(wb, "windows", source_height="30")
    on_dash = {z for d in C.DASHBOARDS for _, items in d["rows"] for z, _ in items} | \
        {k for d in C.DASHBOARDS for k in C.kpis(d)}
    for s in specs:
        window_el(wins, s["name"], maximized=False, hidden=s["name"] in on_dash)
    for i, d in enumerate(C.DASHBOARDS):
        attrs = {"class": "dashboard"}
        if i == 0:
            attrs["maximized"] = "true"
        attrs["name"] = d["name"]
        w = ET.SubElement(wins, "window", attrs)
        vps = sub(w, "viewpoints")
        for z in sorted({z for _, items in d["rows"] for z, _ in items} | set(C.kpis(d))):
            sub(sub(vps, "viewpoint", name=z), "zoom", type="entire-view")
        sub(w, "active", id="-1")
        sub(w, "simple-id", uuid=det_uuid("win:" + d["name"]))
    # actions go before <worksheets> in Tableau's element order
    acts = actions_el(ET.Element("tmp"), models)
    wb.insert(list(wb).index(wss), acts)
    return ET.ElementTree(wb)


def build_kpi(data_dir: Path, with_kpi_sheets: bool, hyper_dbs: dict[str, str] | None = None) -> ET.ElementTree:
    """The KPI-only workbook (RetailPulse.twb / RetailPulse_model_only.twb), unchanged."""
    wb = ET.Element("workbook", {"original-version": VERSION, "source-build": SOURCE_BUILD, "source-platform": "mac",
                                 "version": VERSION, "xmlns:user": "http://www.tableausoftware.com/xml/user"})
    man = sub(wb, "document-format-change-manifest")
    for f in sorted(MANIFEST + ([SORT_FLAG] if with_kpi_sheets else [])):
        sub(man, f)
    prefs = sub(wb, "preferences")
    sub(prefs, "preference", name="ui.encoding.shelf.height", value="24")
    sub(prefs, "preference", name="ui.shelf.height", value="26")
    dss = sub(wb, "datasources")
    parameters_el(dss)
    models = {ds: (SourceModel(ds, data_dir, "hyper", hyper_dbs[ds]) if hyper_dbs else SourceModel(ds, data_dir))
              for ds in DATA_SOURCES}
    kpi_sources = {ds for _, ds, _ in KPI_SHEETS} if with_kpi_sheets else set()
    for m in models.values():
        datasource_el(dss, m, measure_names=m.ds in kpi_sources)
    wss = sub(wb, "worksheets")
    sheets = []
    if with_kpi_sheets:
        for sheet, ds, ids in KPI_SHEETS:
            kpi_worksheet(wss, sheet, models[ds], ids)
            sheets.append(sheet)
    else:
        ws = sub(wss, "worksheet", name="Sheet 1")
        empty_table(ws)
        sub(ws, "simple-id", uuid=det_uuid("ws:Sheet 1"))
        sheets.append("Sheet 1")
    wins = sub(wb, "windows", source_height="30")
    for i, sheet in enumerate(sheets):
        window_el(wins, sheet, maximized=(i == 0))
    return ET.ElementTree(wb)


def write(tree: ET.ElementTree, path: Path):
    ET.indent(tree, space="  ")
    body = ET.tostring(tree.getroot(), encoding="unicode")
    body = body.replace(" />", " />")
    path.write_text("<?xml version='1.0' encoding='utf-8' ?>\n\n<!-- build 20263.26.1120.1648 "
                    "(generated by scripts/build_tableau_workbook.py) -->\n" + body + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Generate the RetailPulse Tableau workbook")
    ap.add_argument("--data-dir", type=Path, default=TAB / "data", help="folder holding the CSVs and analytical/")
    ap.add_argument("--out-dir", type=Path, default=TAB, help="where to write the .twb files")
    args = ap.parse_args()
    data_dir = args.data_dir.resolve()
    missing = [f"{t}.csv" for ds in DATA_SOURCES for t, d, _, _ in DATA_SOURCES[ds]
               if not ((data_dir if d.name == "data" else data_dir / "analytical") / f"{t}.csv").exists()]
    if missing:
        sys.exit(f"ABORT: missing CSV files under {data_dir}: {missing}. Run scripts/export_tableau_*.py first.")
    for name, kpi in (("RetailPulse.twb", True), ("RetailPulse_model_only.twb", False)):
        path = args.out_dir / name
        write(build(data_dir, kpi), path)
        print(f"wrote {path.relative_to(TAB.parent) if path.is_relative_to(TAB.parent) else path}  "
              f"({path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
