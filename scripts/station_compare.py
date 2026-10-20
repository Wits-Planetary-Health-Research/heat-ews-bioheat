"""Criterion 5: ERA5 daily Tmax against station observations.

SAWS Johannesburg International (OR Tambo, WMO 68368) from NOAA GHCN-Daily, 1991 to 2020 overlap.
The on-site Davis Vantage Pro2 at RMMCH is added when a Vital Weather export is placed at
data/stations/rmmch_davis_daily.csv (columns: date, tmax).

Writes outputs/station_comparison.csv
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from heatews import era5_ncar as E  # noqa: E402

ST = ROOT / "data" / "stations"
WARM = [9, 10, 11, 12, 1, 2, 3, 4]


def stats(name, obs, era, note=""):
    m = obs.merge(era, on="date", suffixes=("_obs", "_era5")).dropna()
    rows = []
    for label, sub in (("all months", m), ("Sept to April", m[m.date.dt.month.isin(WARM)])):
        d = sub.tmax_era5 - sub.tmax_obs
        rows.append({"station": name, "months": label, "n_days": len(sub),
                     "first": sub.date.min().date(), "last": sub.date.max().date(),
                     "bias_era5_minus_obs": round(d.mean(), 2), "rmse": round(float(np.sqrt((d ** 2).mean())), 2),
                     "correlation": round(sub.tmax_era5.corr(sub.tmax_obs), 3),
                     "obs_p95": round(sub.tmax_obs.quantile(0.95), 1), "era5_p95": round(sub.tmax_era5.quantile(0.95), 1),
                     "bias_over_1C": abs(d.mean()) > 1, "note": note})
    return rows


def main():
    rows = []
    g = pd.read_csv(ST / "SFM00068368.csv", usecols=["DATE", "TMAX"], low_memory=False).dropna()
    g = pd.DataFrame({"date": pd.to_datetime(g.DATE), "tmax": g.TMAX / 10.0})  # GHCN TMAX is tenths of a degree
    g = g[(g.date.dt.year >= 1991) & (g.tmax > -10) & (g.tmax < 45)]
    era = E.daily_tmax(-26.139, 28.246, "SAST")
    rows += stats("SAWS Johannesburg Intl (68368), GHCN-Daily", g, era,
                  f"ERA5 cell {era.attrs['grid']}; station day is the SAWS observing day")
    davis = ST / "rmmch_davis_daily.csv"
    if davis.exists():
        d = pd.read_csv(davis, parse_dates=["date"])
        era = E.daily_tmax(-26.176, 27.985, "SAST")
        rows += stats("RMMCH on-site Davis Vantage Pro2", d, era, f"ERA5 cell {era.attrs['grid']}")
    else:
        rows.append({"station": "RMMCH on-site Davis Vantage Pro2", "note": "no data yet: needs Vital Weather export (Q6)"})
    out = pd.DataFrame(rows)
    (ROOT / "outputs").mkdir(exist_ok=True)
    out.to_csv(ROOT / "outputs" / "station_comparison.csv", index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
