"""ERA5 daily maximum temperature from the Open-Meteo historical archive.

Daily Tmax is the maximum of hourly ERA5 2 m temperature over the local (SAST) calendar day,
as computed by Open-Meteo when a timezone is given.
"""
from datetime import date
from pathlib import Path
import time

import pandas as pd
import requests

from .config import ROOT

URL = "https://archive-api.open-meteo.com/v1/archive"
CACHE = ROOT / "data" / "era5"


def _get(params, tries=8):
    for attempt in range(tries):
        r = requests.get(URL, params=params, timeout=300)
        if r.status_code == 429:
            time.sleep(min(30 * (attempt + 1), 180))
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()


def fetch_cells(cells, start, end, model="era5", tz="Africa/Johannesburg", variable="temperature_2m_max"):
    """Fetch several grid cells in one request and cache each one. cells: list of (lat, lon)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    files = [CACHE / f"{model}_{la:.3f}_{lo:.3f}_{start}_{end}.csv" for la, lo in cells]
    if all(f.exists() for f in files):
        return [pd.read_csv(f, parse_dates=["date"]) for f in files]
    params = dict(latitude=",".join(str(c[0]) for c in cells), longitude=",".join(str(c[1]) for c in cells),
                  start_date=str(start), end_date=str(end), daily=variable, timezone=tz, models=model)
    js = _get(params)
    js = js if isinstance(js, list) else [js]
    out = []
    for f, j in zip(files, js):
        df = pd.DataFrame({"date": pd.to_datetime(j["daily"]["time"]), "tmax": j["daily"][variable]})
        df.to_csv(f, index=False)
        f.with_suffix(".meta.txt").write_text(
            f"grid_lat: {j.get('latitude')}\ngrid_lon: {j.get('longitude')}\nelevation: {j.get('elevation')}\n"
            f"accessed: {date.today().isoformat()}\nsource: {URL}\nmodel: {model}\n")
        out.append(df)
    return out


def fetch(lat, lon, start, end, model="era5", tz="Africa/Johannesburg", variable="temperature_2m_max",
          use_cache=True):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{model}_{lat:.3f}_{lon:.3f}_{start}_{end}.csv"
    if use_cache and f.exists():
        return pd.read_csv(f, parse_dates=["date"])
    params = dict(latitude=lat, longitude=lon, start_date=str(start), end_date=str(end),
                  daily=variable, timezone=tz, models=model)
    for attempt in range(5):
        r = requests.get(URL, params=params, timeout=120)
        if r.status_code == 429:
            time.sleep(10 * (attempt + 1))
            continue
        r.raise_for_status()
        break
    else:
        r.raise_for_status()
    js = r.json()
    df = pd.DataFrame({"date": pd.to_datetime(js["daily"]["time"]), "tmax": js["daily"][variable]})
    meta = {"grid_lat": js.get("latitude"), "grid_lon": js.get("longitude"), "elevation": js.get("elevation"),
            "accessed": date.today().isoformat(), "source": URL, "model": model}
    df.to_csv(f, index=False)
    (f.with_suffix(".meta.txt")).write_text("\n".join(f"{k}: {v}" for k, v in meta.items()))
    return df
