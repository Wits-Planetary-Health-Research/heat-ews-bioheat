"""Daily Tmax from the hourly ERA5 block pulled by scripts/pull_ncar_era5.py."""
import numpy as np
import pandas as pd

from .config import ROOT

DIR = ROOT / "data" / "era5_ncar"


def _times(t, units):
    units = str(units)
    if "since" in units:
        step, origin = units.split(" since ")
        mult = {"hours": "h", "days": "D", "minutes": "min", "seconds": "s"}[step.strip()]
        return pd.Timestamp(origin.strip()) + pd.to_timedelta(t, unit=mult)
    return pd.to_datetime(t)


def hourly(lat, lon):
    """Hourly 2 m temperature (deg C, UTC index) for the grid cell nearest lat, lon."""
    parts = []
    for f in sorted(DIR.glob("2t_*.npz")):
        z = np.load(f, allow_pickle=True)
        i = int(np.argmin(abs(z["lat"] - lat)))
        j = int(np.argmin(abs(z["lon"] - lon)))
        parts.append(pd.Series(z["v"][:, i, j], index=_times(z["t"], z["tunits"])))
    s = pd.concat(parts).sort_index()
    s = s[~s.index.duplicated()]
    s.attrs["grid"] = (float(z["lat"][i]), float(z["lon"][j]))
    return s


def daily_tmax(lat, lon, day="SAST"):
    """Daily maximum of hourly values. day='SAST' uses the local calendar day (UTC+2), 'UTC' the UTC day."""
    s = hourly(lat, lon)
    idx = s.index + pd.Timedelta(hours=2) if day == "SAST" else s.index
    g = pd.Series(s.values, index=idx).groupby(idx.floor("D"))
    d = g.max().where(g.count() >= 20)
    out = pd.DataFrame({"date": d.index, "tmax": d.values}).dropna()
    out.attrs["grid"] = s.attrs["grid"]
    return out
