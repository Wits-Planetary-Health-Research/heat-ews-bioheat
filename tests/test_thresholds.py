import numpy as np
import pandas as pd

from heatews import thresholds as T
from heatews.config import load


def synthetic(years=(2001, 2004)):
    dates = pd.date_range(f"{years[0]}-01-01", f"{years[1]}-12-31", freq="D")
    # Tmax equals day-of-month: every month has values 1..28/29/30/31 repeated each year
    return pd.DataFrame({"date": dates, "tmax": dates.day.astype(float)})


def test_monthly_percentile_known_answer():
    df = synthetic()
    m = T.monthly(df, (2001, 2004), 95)
    # January: values 1..31, four times each. numpy linear percentile of that set:
    expected = np.percentile(np.tile(np.arange(1, 32), 4), 95)
    assert abs(m[1] - expected) < 1e-9
    # Linear interpolation (R type 7) on 124 values: rank 0.95*123 = 116.85 -> between 30 and 30 -> 30.0
    assert abs(m[1] - 30.0) < 1e-9


def test_monthly_respects_reference_years():
    df = synthetic((2000, 2005))
    df.loc[df.date.dt.year == 2005, "tmax"] = 100.0
    assert T.monthly(df, (2000, 2004), 95)[1] < 40


def test_calendar_day_window_size_and_wrap():
    dates = pd.date_range("2001-01-01", "2003-12-31", freq="D")
    doy = T.doy365(dates)
    df = pd.DataFrame({"date": dates, "tmax": doy.astype(float)})
    c = T.calendar_day(df, (2001, 2003), 100, window=15)
    # Max over a centred 15-day window of day-of-year values: day 100 sees 93..107
    assert c[100] == 107
    # Window wraps over the year end: day 1 sees 358..365 and 1..8, max is 365
    assert c[1] == 365
    c50 = T.calendar_day(df, (2001, 2003), 0, window=15)
    assert c50[100] == 93


def test_leap_day_pooled_with_28_feb():
    assert list(T.doy365(["2004-02-28", "2004-02-29", "2004-03-01", "2005-03-01"])) == [59, 59, 60, 60]


def test_operational_table_defaults_to_sop():
    cfg = load()
    t = T.operational_table(cfg)
    assert t[1] == 32.6 and t[9] == 30.5
    assert list(T.for_dates(["2026-01-31", "2026-02-01"], cfg)) == [32.6, 29.8]
