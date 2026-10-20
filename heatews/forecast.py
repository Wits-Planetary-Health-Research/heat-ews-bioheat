"""ECMWF IFS ensemble forecast of daily Tmax, from the Open-Meteo ensemble API (ECMWF open data).

Daily Tmax for each member is the maximum of the hourly series over the SAST calendar day, the same
definition used for ERA5. Day 1 is today (SAST). Lead day k is today + k - 1.
"""
from datetime import datetime, timezone
import time

import numpy as np
import pandas as pd
import requests

URL = "https://ensemble-api.open-meteo.com/v1/ensemble"


class FetchError(RuntimeError):
    pass


def fetch(lat, lon, model="ecmwf_ifs025", days=15, tz="Africa/Johannesburg", tries=6, session=None):
    """Return (dates, members[n_members, n_days], meta). Raises FetchError on any failure."""
    get = (session or requests).get
    params = dict(latitude=lat, longitude=lon, hourly="temperature_2m", models=model,
                  forecast_days=days, timezone=tz)
    last = None
    for attempt in range(tries):
        try:
            r = get(URL, params=params, timeout=120)
            if r.status_code == 429:
                last = "HTTP 429"
                time.sleep(20 * (attempt + 1))
                continue
            if r.status_code != 200:
                raise FetchError(f"HTTP {r.status_code}")
            js = r.json()
            break
        except (requests.RequestException, ValueError) as e:
            last = str(e)
            time.sleep(5)
    else:
        raise FetchError(f"forecast fetch failed: {last}")
    return parse(js, model)


def parse(js, model="ecmwf_ifs025"):
    h = js.get("hourly")
    if not h or "time" not in h:
        raise FetchError("no hourly data in response")
    t = pd.to_datetime(h["time"])
    cols = [k for k in h if k.startswith("temperature_2m")]
    if not cols:
        raise FetchError("no temperature members in response")
    hourly = pd.DataFrame({c: pd.to_numeric(pd.Series(h[c]), errors="coerce").values for c in cols}, index=t)
    # Drop days with fewer than 20 valid hourly values in a member (partial last day)
    daily = hourly.groupby(hourly.index.date).max()
    counts = hourly.groupby(hourly.index.date).count()
    daily = daily.where(counts >= 20)
    daily = daily.dropna(how="all")
    meta = {"source": URL, "model": model, "grid_lat": js.get("latitude"), "grid_lon": js.get("longitude"),
            "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "members": len(cols)}
    dates = pd.to_datetime(daily.index)
    return dates, daily.T.values, meta
