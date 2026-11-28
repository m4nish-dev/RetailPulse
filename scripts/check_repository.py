"""
RetailPulse - repository, documentation and security checks (read-only).

  STRUCTURE   the retired Power BI folder is gone; the Tableau folder and data
              folders exist; every script the validation runner calls exists
  REFERENCES  no ACTIVE file mentions the retired BI tool or its paths; the few
              historical records that do are marked "HISTORICAL RECORD"
  LINKS       every relative Markdown link resolves; every script / SQL /
              notebook / Markdown path named in active documentation exists
  SECURITY    .env untracked and ignored; no credentials, private keys or home
              paths in files Git would commit; no data files, caches or large
              files would be committed; workbooks, extracts and data are ignored

"Files Git would commit" = tracked files plus untracked files that are not
ignored. Nothing is modified.

Usage:  ./venv/bin/python scripts/check_repository.py
Exit code 1 on any failure.
"""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
R: list[tuple[str, str, bool, str]] = []

# Files allowed to mention the retired tool, because they record project history.
HISTORICAL = {"reports/final_project_audit.md", "reports/phase6_documentation_audit.md",
              "reports/metric_audit_history.md", "TASK_TRACKER.md", "PROJECT_PLAN.md"}
HIST_MARK = "HISTORICAL RECORD"
RETIRED = re.compile(r"power\s*bi|powerbi|\bDAX\b|\.pbix|windows_implementation", re.I)
# an assignment (key = value, or key: "value") of a credential-like name to a literal of 6+ characters
SECRET = re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key)\b\s*(?:=|:\s*['\"])\s*['\"]?([A-Za-z0-9_\-+/=]{6,})")
SECRET_OK = {"change-me", "REPLACE_WITH_PASSWORD", "cfg.password", "os.environ", "getenv"}
TEXT = {".md", ".py", ".sql", ".ipynb", ".txt", ".json", ".csv", ".cfg", ".toml", ".yml", ".yaml", ""}
ALLOWED_CSV = {"tableau/tableau_calc_validation_results.csv", "tableau/data/_manifest.csv",
               "tableau/data/analytical/_manifest.csv"}


def ck(area, name, ok, detail=""):
    R.append((area, name, bool(ok), detail))


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout


def committable():
    files = set(git("ls-files", "-z").split("\0")) | set(git("ls-files", "-z", "--others", "--exclude-standard").split("\0"))
    return sorted(f for f in files if f and (ROOT / f).is_file())


def main():
    files = committable()
    me = "scripts/check_repository.py"

    # ---- structure -----------------------------------------------------------------
    ck("structure", "retired BI folder removed", not (ROOT / "powerbi").exists())
    for d in ["tableau", "tableau/data", "tableau/data/analytical", "reports/dashboard_screenshots"]:
        ck("structure", f"{d}/ exists", (ROOT / d).is_dir())
    runner = (ROOT / "scripts" / "run_all_validations.py").read_text(encoding="utf-8")
    called = sorted(set(re.findall(r'"((?:\.\./tableau/scripts/)?(?:validate|check|verify)_[a-z_]+\.py)"', runner)))
    missing = [c for c in called if not (ROOT / "scripts" / c).resolve().exists()]
    ck("structure", f"every script called by the validation runner exists ({len(called)})", not missing,
       f"missing: {missing or 'none'}")
    sqls = re.findall(r'"(\d\d_[a-z_]+\.sql)"', runner)
    ck("structure", "every SQL file named in the runner exists", all((ROOT / "sql" / s).exists() for s in sqls))

    # ---- retired-tool references -------------------------------------------------------
    active_hits, unmarked = [], []
    for f in files:
        if Path(f).suffix not in TEXT or f == me:
            continue
        text = (ROOT / f).read_text(encoding="utf-8", errors="replace")
        hits = [i + 1 for i, line in enumerate(text.splitlines()) if RETIRED.search(line)]
        if not hits:
            continue
        if f in HISTORICAL:
            if HIST_MARK not in text:
                unmarked.append(f)
            if re.search(r"\]\((?:\.\./)?powerbi/", text):
                active_hits.append(f"{f}: link into the removed folder")
        else:
            active_hits.append(f"{f}:{hits[:5]}")
    ck("references", "no active file mentions the retired BI tool or its paths", not active_hits,
       "; ".join(active_hits[:12]) or "none")
    ck("references", f"historical records that mention it carry '{HIST_MARK}'", not unmarked, f"{unmarked or 'none'}")

    # ---- links and paths in Markdown ---------------------------------------------------------
    broken, missing_paths = [], []
    path_re = re.compile(r"`((?:scripts|sql|notebooks|tableau|documentation|reports)/[A-Za-z0-9_./-]+\.(?:py|sql|ipynb|md))`")
    for f in files:
        if not f.endswith(".md"):
            continue
        text = (ROOT / f).read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)\s]+)\)", text):
            if re.match(r"(https?:|mailto:|#)", target):
                continue
            p = (ROOT / f).parent / target.split("#")[0]
            if not p.exists():
                broken.append(f"{f} -> {target}")
        if f not in HISTORICAL:
            for path in path_re.findall(text):
                if not (ROOT / path).exists():
                    missing_paths.append(f"{f}: {path}")
    ck("links", "every relative Markdown link resolves", not broken, "; ".join(broken[:10]) or "none")
    ck("links", "every script/SQL/notebook/doc path named in active docs exists", not missing_paths,
       "; ".join(sorted(set(missing_paths))[:10]) or "none")

    # ---- security and hygiene --------------------------------------------------------------
    ck("security", ".env is not tracked", ".env" not in git("ls-files").split())
    ignored = git("check-ignore", ".env", "tableau/RetailPulse.twbx", "tableau/RetailPulse.twb", "tableau/extracts/x.hyper", "tableau/data/x.csv",
                  "tableau/data/analytical/x.csv", "dataset/raw/x.csv", "dataset/cleaned/x.csv",
                  "scripts/__pycache__/x.pyc", "notebooks/.ipynb_checkpoints/x.ipynb").split()
    ck("security", "secrets, workbooks, extracts, data and caches are git-ignored", len(ignored) == 10,
       f"{len(ignored)}/10 ignored")
    leaks = []
    for f in files:
        if Path(f).suffix not in TEXT or f in (me, ".env.example"):
            continue
        text = (ROOT / f).read_text(encoding="utf-8", errors="replace")
        for m in SECRET.finditer(text):
            if not any(ok in m.group(0) for ok in SECRET_OK):
                leaks.append(f"{f}: {m.group(1)}=…")
        if "PRIVATE KEY-----" in text:
            leaks.append(f"{f}: private key")
        if re.search(r"/Users/[A-Za-z0-9_.-]+/", text):
            leaks.append(f"{f}: home-directory path")
    ck("security", "no credentials, private keys or home paths in committable files", not leaks,
       "; ".join(leaks[:8]) or "none")
    data = [f for f in files if f.endswith((".csv", ".hyper", ".twbx", ".twb", ".tde", ".pbix")) and f not in ALLOWED_CSV]
    ck("security", "no data files, extracts or workbooks would be committed", not data, f"{data[:8] or 'none'}")
    junk = [f for f in files if "__pycache__" in f or ".ipynb_checkpoints" in f or f.endswith((".pyc", ".DS_Store", ".tmp"))]
    ck("security", "no caches or temporary files would be committed", not junk, f"{junk[:8] or 'none'}")
    tracked = set(git("ls-files", "-z").split("\0"))
    size = lambda f: (ROOT / f).stat().st_size
    big = [f"{f} ({size(f) / 1e6:.1f} MB)" for f in files if size(f) > 50e6 or (f not in tracked and size(f) > 10e6)]
    ck("security", "no new file over 10 MB and no file near GitHub's 50 MB warning", not big, f"{big or 'none'}")
    data_dirs = [p for p in (ROOT / "tableau" / "data").rglob("*") if p.is_file()
                 and not p.name.endswith(".csv") and p.name not in (".gitkeep", ".DS_Store")]
    ck("security", "tableau/data holds only CSV files", not data_dirs, f"{[p.name for p in data_dirs] or 'none'}")

    for area, name, ok, detail in R:
        print(f"  {'PASS' if ok else 'FAIL'}  [{area}] {name}" + (f"  — {detail}" if detail else ""))
    n = sum(r[2] for r in R)
    print(f"checks: {len(R)}   PASS: {n}   FAIL: {len(R) - n}")
    sys.exit(0 if n == len(R) else 1)


if __name__ == "__main__":
    main()
