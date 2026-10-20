"""Independent recompute of monthly Tmax percentiles (criterion 3).

Deliberately shares no code with the heatews package: reads the raw hourly .npz files with plain
numpy, builds SAST daily maxima by hand, and uses a hand-written type 7 percentile.
Prints a CSV: cell,period,month,p90,p95
"""
from datetime import datetime, timedelta
from pathlib import Path
import sys

import numpy as np

DIR = Path(__file__).resolve().parent.parent / "data" / "era5_ncar"


def pct7(x, p):
    x = sorted(x)
    h = (len(x) - 1) * p / 100.0
    lo = int(h)
    hi = min(lo + 1, len(x) - 1)
    return x[lo] + (h - lo) * (x[hi] - x[lo])


def daily_max(lat, lon):
    days = {}
    for f in sorted(DIR.glob("2t_*.npz")):
        z = np.load(f, allow_pickle=True)
        i = int(np.argmin(np.abs(z["lat"] - lat)))
        j = int(np.argmin(np.abs(z["lon"] - lon)))
        units = str(z["tunits"])
        origin = datetime.fromisoformat(units.split(" since ")[1].strip().replace(" ", "T")[:19])
        for t, v in zip(z["t"], z["v"][:, i, j]):
            local = origin + timedelta(hours=float(t)) + timedelta(hours=2)
            k = local.date()
            days.setdefault(k, []).append(float(v))
    return {k: max(v) for k, v in days.items() if len(v) >= 20}


if __name__ == "__main__":
    cells = {"soweto": (-26.25, 27.75), "rmmch": (-26.25, 28.0)}
    periods = {"sop_2016_2019": (2016, 2019), "wmo_1991_2020": (1991, 2020)}
    print("cell,period,month,p90,p95")
    for cname, (la, lo) in cells.items():
        dm = daily_max(la, lo)
        for pname, (y0, y1) in periods.items():
            for m in range(1, 13):
                vals = [v for k, v in dm.items() if y0 <= k.year <= y1 and k.month == m]
                print(f"{cname},{pname},{m},{pct7(vals, 90):.3f},{pct7(vals, 95):.3f}")
    sys.stdout.flush()
