"""Criterion 3: D1 values must match the independent recompute within 0.1 degrees C."""
from pathlib import Path
import sys

import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "outputs"
a = pd.read_csv(OUT / "D1_full_year.csv")
b = pd.read_csv(OUT / "D1_independent.csv")
a = a.replace({"cell": {"rmmch": "rmmch", "soweto": "soweto"}})
m = a.merge(b, on=["cell", "period", "month"], suffixes=("", "_ind"))
assert len(m) == 48, f"expected 48 rows, got {len(m)}"
d = pd.concat([(m.p90 - m.p90_ind).abs(), (m.p95 - m.p95_ind).abs()])
print(f"Rows compared: {len(m) * 2}. Max |diff| {d.max():.4f} C  ->  {'PASS' if d.max() <= 0.1 else 'FAIL'}")
sys.exit(0 if d.max() <= 0.1 else 1)
