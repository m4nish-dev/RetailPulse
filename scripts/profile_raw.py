"""
RetailPulse - Phase 1 raw-data profiler.

Reads every CSV in dataset/raw/ and reports structure, missing values,
duplicates and candidate keys. Read-only: it never writes to dataset/raw/.

Usage (from project root):
    ./venv/bin/python -I scripts/profile_raw.py
"""
from pathlib import Path
import pandas as pd

RAW = Path(__file__).resolve().parent.parent / "dataset" / "raw"

# Eight files are fully quoted UTF-8. The translation file carries a UTF-8 BOM,
# so it needs utf-8-sig, which strips the BOM from the first column name.
# Without this the first column name keeps an invisible character and joins
# fail silently.
ENCODINGS = {"product_category_name_translation.csv": "utf-8-sig"}

# Everything is loaded as string first. Reason: pandas guesses types on load,
# and a guess can silently corrupt data (zip codes losing leading zeros, IDs
# becoming floats). We look at the real values first, then convert
# deliberately in Phase 3.
def load(name: str) -> pd.DataFrame:
    return pd.read_csv(RAW / name, dtype=str, encoding=ENCODINGS.get(name, "utf-8"))


def main() -> None:
    files = sorted(p.name for p in RAW.glob("*.csv"))
    print(f"Found {len(files)} CSV files in {RAW}\n")

    for name in files:
        df = load(name)
        print("=" * 78)
        print(f"{name}")
        print(f"  shape: {df.shape[0]:,} rows x {df.shape[1]} columns")
        print(f"  exact duplicate rows: {df.duplicated().sum():,}")
        print("-" * 78)
        print(f"  {'column':<34} {'nulls':>8} {'null%':>7} {'unique':>9}  {'sample'}")
        for col in df.columns:
            nulls = df[col].isna().sum()
            pct = nulls / len(df) * 100
            nun = df[col].nunique(dropna=True)
            sample = df[col].dropna().iloc[0] if nun else ""
            sample = (str(sample)[:26] + "...") if len(str(sample)) > 26 else str(sample)
            flag = "  <-- UNIQUE+COMPLETE (PK candidate)" if (nun == len(df) and nulls == 0) else ""
            print(f"  {col:<34} {nulls:>8,} {pct:>6.2f}% {nun:>9,}  {sample}{flag}")
        print()


if __name__ == "__main__":
    main()
