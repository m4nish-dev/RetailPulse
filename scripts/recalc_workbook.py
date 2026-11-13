"""
RetailPulse - recalculate the Phase 2 workbook and verify its KPIs.

Why this is needed: openpyxl writes formula TEXT but cannot evaluate it. Until
a real spreadsheet engine opens the file, every summary cell is just a string,
so "the spreadsheet agrees with Python" cannot be claimed.

This drives LibreOffice headlessly via its command line to open the workbook,
evaluate every formula, and write the results back. The recalculated file is
then read with openpyxl(data_only=True) to extract the computed values,
scanned for formula errors, and installed over the original.

NOTE: an earlier version of this script used the UNO Python bridge
(/Applications/LibreOffice.app/Contents/Resources/python). On this machine that
interpreter hangs on launch, so the CLI route below is used instead - it is
also simpler and has fewer moving parts.

Usage (from project root):
    ./venv/bin/python scripts/recalc_workbook.py [--install]

    --install   overwrite excel/<workbook>.xlsx with the recalculated copy
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
XLSX = ROOT / "excel" / "RetailPulse_Phase2_Exploration.xlsx"
SOFFICE = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
ERROR_PREFIXES = ("#REF!", "#VALUE!", "#DIV/0!", "#N/A", "#NAME?",
                  "#NULL!", "#NUM!", "Err:")


def recalculate(src: Path, outdir: Path) -> Path:
    """Open in LibreOffice, evaluate all formulas, write back as .xlsx."""
    if not SOFFICE.exists():
        sys.exit(f"LibreOffice not found at {SOFFICE}\n"
                 "Install with:  brew install --cask libreoffice")
    subprocess.run(
        [str(SOFFICE), "--headless", "--invisible", "--nologo", "--norestore",
         "--convert-to", "xlsx", "--outdir", str(outdir), str(src)],
        check=True, capture_output=True, timeout=1800)
    out = outdir / src.name
    if not out.exists():
        sys.exit("LibreOffice produced no output file")
    return out


def scan_errors(wb) -> list[str]:
    """Any cell whose evaluated result is a spreadsheet error."""
    bad = []
    for name in wb.sheetnames:
        if name.startswith("DATA_"):      # data sheets hold no formulas
            continue
        for row in wb[name].iter_rows():
            for cell in row:
                v = cell.value
                if isinstance(v, str) and v.startswith(ERROR_PREFIXES):
                    bad.append(f"{name}!{cell.coordinate} = {v}")
    return bad


def compare_kpis(wb) -> tuple[int, int, list]:
    """Read sheet 04 and compare the spreadsheet column against Python."""
    ws = wb["04_KPI_Validation"]
    header = next(r for r in range(1, 25)
                  if ws.cell(row=r, column=1).value == "#")
    ok, skipped, mismatches = 0, [], []
    print(f"{'KPI':<46}{'SPREADSHEET':>17}{'PYTHON':>17}{'DIFF':>12}")
    print("-" * 92)
    r = header + 1
    while (label := ws.cell(row=r, column=2).value):
        sheet_v = ws.cell(row=r, column=3).value
        py_v = ws.cell(row=r, column=4).value
        if isinstance(sheet_v, str) or sheet_v is None:
            skipped.append(label)
            print(f"{label[:45]:<46}{'not computable':>17}{py_v:>17,.4f}{'-':>12}")
        else:
            diff = sheet_v - py_v
            flag = "" if abs(diff) < 0.011 else "   <<< MISMATCH"
            (mismatches.append((label, sheet_v, py_v)) if flag else None)
            ok += 0 if flag else 1
            print(f"{label[:45]:<46}{sheet_v:>17,.4f}{py_v:>17,.4f}{diff:>12,.4f}{flag}")
        r += 1
    print("-" * 92)
    return ok, len(skipped), mismatches


def main() -> None:
    install = "--install" in sys.argv
    with tempfile.TemporaryDirectory() as tmp:
        print(f"Recalculating {XLSX.name} ({XLSX.stat().st_size/1024**2:.1f} MB)...")
        out = recalculate(XLSX, Path(tmp))

        wb_vals = load_workbook(out, data_only=True)
        errors = scan_errors(wb_vals)
        ok, skipped, mismatches = compare_kpis(wb_vals)

        print(f"\nComputable KPIs reconciling : {ok}")
        print(f"Not computable in a sheet   : {skipped}")
        print(f"Mismatches                  : {len(mismatches)}")
        print(f"Formula errors              : {len(errors)}")
        for e in errors:
            print(f"    {e}")

        if install and not errors and not mismatches:
            shutil.copy2(out, XLSX)
            print(f"\nInstalled recalculated workbook -> {XLSX}")
        elif install:
            print("\nNOT installed: fix the errors/mismatches above first.")

    sys.exit(1 if (errors or mismatches) else 0)


if __name__ == "__main__":
    main()
