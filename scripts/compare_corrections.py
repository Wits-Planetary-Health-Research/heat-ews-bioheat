"""Compare bias-correction methods on the hindcast (warm seasons 2024/25 and 2025/26, cross-validated).

For each method: mean error on days ERA5 was above the threshold, MAE on all days, and event scores
(SOP heatwave within days 1-3 and 4-7, judged on the same window).
Writes outputs/correction_comparison.csv
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from heatews import alert as A, bias, config, era5_ncar as E, thresholds as T  # noqa: E402

cfg = config.load()
a = cfg["alert"]
obs = E.daily_tmax(cfg["site"]["latitude"], cfg["site"]["longitude"], "SAST")
obs["thr"] = T.for_dates(obs.date, cfg)
lk = obs.set_index("date")
fc = pd.read_csv(sorted((ROOT / "data" / "previous_runs").glob("*.csv"))[-1], parse_dates=["date"])
fci = fc.set_index("date")
seasons = {"2024/25": ("2024-09-01", "2025-04-30"), "2025/26": ("2025-09-01", "2026-04-30")}


def linear_fit(train):
    """Per-lead regression obs = a + b * fc (fixes conditional bias as well as mean bias)."""
    d = train.merge(obs[["date", "tmax"]], on="date")
    d = d[d.date.dt.month.isin(bias.WARM)]
    out = {}
    for k in range(8):
        x = d[[f"lead{k}", "tmax"]].dropna()
        b, a0 = np.polyfit(x[f"lead{k}"], x.tmax, 1)
        out[k] = (a0, b)
    return out


rows = []
for method in ("raw", "quantile mapping", "mean shift", "linear"):
    days, ev = [], []
    for test_s, (t0, t1) in seasons.items():
        tr = [s for s in seasons if s != test_s][0]
        train = fc[(fc.date >= seasons[tr][0]) & (fc.date <= seasons[tr][1])]
        qm = bias.Mapping.fit(train, obs[["date", "tmax"]])
        lin = linear_fit(train)
        for issue in pd.date_range(t0, t1, freq="D"):
            tgt = [issue + pd.Timedelta(days=j) for j in range(8)]
            if not all(t in fci.index and t in lk.index for t in tgt):
                continue
            raw = np.array([fci.loc[t, f"lead{j}"] for j, t in enumerate(tgt)], float)
            if np.isnan(raw).any():
                continue
            if method == "raw":
                c = raw
            elif method == "quantile mapping":
                c = np.array([qm.correct([raw[j]], j)[0] for j in range(8)])
            elif method == "mean shift":
                c = np.array([raw[j] + qm.table[j]["mean_shift"] for j in range(8)])
            else:
                c = np.array([lin[j][0] + lin[j][1] * raw[j] for j in range(8)])
            thr = np.array([lk.loc[t, "thr"] for t in tgt])
            ob = np.array([lk.loc[t, "tmax"] for t in tgt])
            fhw = A.heatwave_days(A.hot_days(c, thr), a["run_length_days"])
            ohw = A.heatwave_days(A.hot_days(ob, thr), a["run_length_days"])
            for j in range(8):
                days.append((j + 1, ob[j], c[j], thr[j]))
            for band, (s, e) in {"days 1-3": (1, 3), "days 4-7": (4, 7)}.items():
                ev.append((band, bool(fhw[s - 1:e].any()), bool(ohw[s - 1:e].any())))
    dd = pd.DataFrame(days, columns=["lead", "obs", "cor", "thr"])
    hot = dd[dd.obs > dd.thr]
    e = pd.DataFrame(ev, columns=["band", "f", "o"])
    r = {"method": method, "hot_day_error": round((hot.cor - hot.obs).mean(), 2),
         "mae_all": round((dd.cor - dd.obs).abs().mean(), 2)}
    for band in ("days 1-3", "days 4-7"):
        g = e[e.band == band]
        h, m, f = int((g.f & g.o).sum()), int((~g.f & g.o).sum()), int((g.f & ~g.o).sum())
        r[f"{band} hits/misses/false"] = f"{h}/{m}/{f}"
        r[f"{band} hit rate"] = round(h / (h + m), 2) if h + m else np.nan
        r[f"{band} FAR"] = round(f / (h + f), 2) if h + f else np.nan
    rows.append(r)
out = pd.DataFrame(rows)
out.to_csv(ROOT / "outputs" / "correction_comparison.csv", index=False)
pd.set_option("display.width", 250)
print(out.to_string(index=False))
