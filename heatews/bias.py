"""Lead-dependent bias correction of forecast Tmax towards ERA5.

Training data: Open-Meteo Previous Runs API, ECMWF IFS 0.25 (the same model the open ensemble uses),
which keeps the forecast made 0 to 7 days before each target day. Lead 0 is the same-day run, which is
forecast day 1 in the ensemble; forecast day k is lead k-1. For each lead we fit an empirical quantile
mapping from forecast Tmax to ERA5 Tmax over the warm season (Sept to April). Forecast days 9 to 15
reuse the lead 7 mapping, since no open archive goes further.
"""
from datetime import date
import json
import time

import numpy as np
import pandas as pd
import requests

from .config import ROOT

URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
CACHE = ROOT / "data" / "previous_runs"
QS = np.linspace(0.01, 0.99, 49)
WARM = [9, 10, 11, 12, 1, 2, 3, 4]


def fetch_previous_runs(lat, lon, start, end, model="ecmwf_ifs025", leads=range(1, 8), tz="Africa/Johannesburg"):
    """Daily Tmax of the forecast issued `lead` days before each target day (SAST), one column per lead."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{model}_{lat:.3f}_{lon:.3f}_{start}_{end}.csv"
    if f.exists():
        return pd.read_csv(f, parse_dates=["date"])
    var = ["temperature_2m"] + [f"temperature_2m_previous_day{k}" for k in leads]
    params = dict(latitude=lat, longitude=lon, start_date=str(start), end_date=str(end),
                  hourly=",".join(var), models=model, timezone=tz)
    for attempt in range(8):
        r = requests.get(URL, params=params, timeout=300)
        if r.status_code == 429:
            time.sleep(min(30 * (attempt + 1), 180))
            continue
        r.raise_for_status()
        break
    js = r.json()
    h = pd.DataFrame(js["hourly"])
    h["time"] = pd.to_datetime(h["time"])
    g = h.set_index("time").groupby(lambda t: t.date())
    d = g.max().where(g.count() >= 20)
    out = pd.DataFrame({"date": pd.to_datetime(d.index)})
    out["lead0"] = d["temperature_2m"].values
    for k in leads:
        out[f"lead{k}"] = d[f"temperature_2m_previous_day{k}"].values
    out.to_csv(f, index=False)
    f.with_suffix(".meta.txt").write_text(f"source: {URL}\nmodel: {model}\naccessed: {date.today()}\n"
                                          f"grid_lat: {js.get('latitude')}\ngrid_lon: {js.get('longitude')}\n")
    return out


class Mapping:
    """Per-lead empirical quantile mapping. Outside the training range, a constant shift is applied."""

    def __init__(self, table=None, method="mean_shift"):
        self.table = table or {}
        # mean_shift is the default: quantile mapping fixed the overall distribution but made hot days
        # colder (it cannot fix the forecast's conditional bias), see outputs/correction_comparison.csv
        self.method = method

    @classmethod
    def fit(cls, fc, obs, leads=range(0, 8), months=WARM):
        df = fc.merge(obs.rename(columns={"tmax": "obs"}), on="date")
        df = df[df.date.dt.month.isin(months)]
        table = {}
        for k in leads:
            d = df[[f"lead{k}", "obs"]].dropna()
            table[k] = {"fq": np.quantile(d[f"lead{k}"], QS).tolist(), "oq": np.quantile(d["obs"], QS).tolist(),
                        "mean_shift": float((d["obs"] - d[f"lead{k}"]).mean()), "n": int(len(d))}
        return cls(table)

    def correct(self, values, lead):
        lead = min(max(self.table), max(min(self.table), lead))
        t = self.table[lead]
        v = np.asarray(values, dtype=float)
        if self.method == "mean_shift":
            return v + t["mean_shift"]
        fq, oq = np.array(t["fq"]), np.array(t["oq"])
        out = np.interp(v, fq, oq)
        lo, hi = v < fq[0], v > fq[-1]
        out[lo] = v[lo] + (oq[0] - fq[0])
        out[hi] = v[hi] + (oq[-1] - fq[-1])
        return out

    def correct_ensemble(self, members):
        m = np.asarray(members, dtype=float)
        # Forecast day 1 (today's run, valid today) is lead 0; day k is lead k-1; beyond lead 7 reuse lead 7
        return np.column_stack([self.correct(m[:, j], j) for j in range(m.shape[1])])

    def save(self, path):
        path.write_text(json.dumps({str(k): v for k, v in self.table.items()}, indent=1))

    @classmethod
    def load(cls, path, method="mean_shift"):
        return cls({int(k): v for k, v in json.loads(path.read_text()).items()}, method)
