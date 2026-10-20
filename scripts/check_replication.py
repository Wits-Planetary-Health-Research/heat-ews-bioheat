"""Criterion 2: reproduce SOP-BH-13 Appendix 1 (ERA5 Soweto 2016 to 2019) within 0.3 degrees C."""
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from heatews import config, era5_ncar as E, thresholds as T  # noqa: E402

TOL = 0.3
cfg = config.load()
s = cfg["replication_site"]
df = E.daily_tmax(-26.25, 27.75, "SAST")
ok = True
for p in (90, 95):
    ours = T.monthly(df, (2016, 2019), p)
    sop = pd.Series(cfg["sop_appendix1"][f"p{p}"])
    d = (ours - sop)
    print(f"P{p}: max |diff| {d.abs().max():.2f} C, mean {d.mean():+.2f} C  ->  {'PASS' if d.abs().max() <= TOL else 'FAIL'}")
    ok &= bool(d.abs().max() <= TOL)
print("Replication:", "PASS" if ok else "FAIL", f"(grid cell {df.attrs['grid']})")
sys.exit(0 if ok else 1)
