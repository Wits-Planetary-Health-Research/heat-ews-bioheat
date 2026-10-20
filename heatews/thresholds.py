"""Percentile thresholds of daily Tmax.

Percentiles use numpy's default linear interpolation, which matches R's quantile type 7.
"""
import numpy as np
import pandas as pd


def monthly(df, years, pct):
    """Percentile of daily Tmax for each calendar month over the reference years (inclusive)."""
    d = df[(df.date.dt.year >= years[0]) & (df.date.dt.year <= years[1])].dropna(subset=["tmax"])
    return d.groupby(d.date.dt.month)["tmax"].apply(lambda s: float(np.percentile(s, pct)))


def calendar_day(df, years, pct, window=15):
    """Percentile for each day of year, pooling a centred window of `window` days across reference years.

    Day of year uses a 365-day calendar; 29 Feb is pooled with 28 Feb.
    """
    half = window // 2
    d = df[(df.date.dt.year >= years[0]) & (df.date.dt.year <= years[1])].dropna(subset=["tmax"]).copy()
    d["doy"] = doy365(d.date)
    out = {}
    for k in range(1, 366):
        near = [((k - 1 + o) % 365) + 1 for o in range(-half, half + 1)]
        out[k] = float(np.percentile(d.loc[d.doy.isin(near), "tmax"], pct))
    return pd.Series(out, name=f"p{pct}")


def doy365(dates):
    dates = pd.to_datetime(pd.Series(dates))
    doy = dates.dt.dayofyear
    leap_after_feb = dates.dt.is_leap_year & ((dates.dt.month > 2) | ((dates.dt.month == 2) & (dates.dt.day == 29)))
    doy = doy - leap_after_feb.astype(int)
    return doy.values


def for_dates(dates, cfg, table=None):
    """Threshold that applies to each date, under the configured kind."""
    dates = pd.to_datetime(pd.Series(dates))
    th = cfg["thresholds"]
    if table is None:
        table = operational_table(cfg)
    if th["kind"] == "monthly":
        return dates.dt.month.map(table).values
    return pd.Series(doy365(dates)).map(table).values


def operational_table(cfg, df=None):
    """Thresholds the alert uses. By default the published SOP-BH-13 Appendix 1 values."""
    th = cfg["thresholds"]
    if th.get("use_sop_table", False) and th["kind"] == "monthly":
        return cfg["sop_appendix1"][f"p{th['percentile']}"]
    if df is None:
        raise ValueError("ERA5 data needed to compute thresholds")
    if th["kind"] == "monthly":
        return monthly(df, th["reference_period"], th["percentile"]).to_dict()
    return calendar_day(df, th["reference_period"], th["percentile"], th["calendar_window_days"]).to_dict()
