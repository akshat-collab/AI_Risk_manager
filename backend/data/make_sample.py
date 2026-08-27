import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.synthetic_data import generate_synthetic_transactions

if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "sample_transactions.csv"
    df = generate_synthetic_transactions(n=500, seed=42, inject_spike=False)
    df.drop(columns=["is_demo"], errors="ignore").to_csv(out, index=False)
    print(f"Wrote {out} ({len(df)} rows)")
