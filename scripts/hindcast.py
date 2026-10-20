"""Criteria 15 and 16: hindcast skill by lead band, and heatwave activations per season.

Part A (activations): ERA5 at RMMCH 1991 to latest, SOP thresholds, count heatwave events and days per
warm season (Sept to April).

Part B (skill): past ECMWF IFS 0.25 forecasts (Open-Meteo Previous Runs, leads 0 to 7), bias-corrected with
a mapping trained on the other warm season (no leakage). For every issue day, does the forecast show a
heatwave day (SOP definition, run of 2) within the lead band, and does ERA5? Bands: days 1-3, 4-7, 8.
No open archive of ECMWF forecasts beyond 8 days exists, so days 8 to 14 cannot be scored here.

Writes outputs/activations_per_season.csv and outputs/hindcast_skill.csv
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from heatews import alert as A, bias, config, era5_ncar as E, thresholds as T  # noqa: E402

cfg = config.load()
lat, lon = cfg["site"]["latitude"], cfg["site"]["longitude"]
a = cfg["alert"]
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

obs = E.daily_tmax(lat, lon, "SAST").sort_values("date").reset_index(drop=True)
obs["thr"] = T.for_dates(obs.date, cfg)
obs["hw"] = A.heatwave_days(A.hot_days(obs.tmax, obs.thr, a["comparison"]), a["run_length_days"])
obs["season"] = np.where(obs.date.dt.month >= 9, obs.date.dt.year, obs.date.dt.year - 1)
warm = obs[obs.date.dt.month.isin(bias.WARM)].copy()


def events(hw):
    hw = np.asarray(hw, dtype=int)
    return int(((hw[1:] == 1) & (hw[:-1] == 0)).sum() + hw[0])


act = warm.groupby("season").apply(lambda g: pd.Series({
    "events": events(g.hw.values), "heatwave_days": int(g.hw.sum()), "days": len(g)}), include_groups=False)
act = act[act.days >= 240].reset_index()
act["season"] = act.season.astype(str) + "/" + (act.season + 1).astype(str).str[-2:]
act.to_csv(OUT / "activations_per_season.csv", index=False)
print("Activations per warm season (ERA5, SOP P95 thresholds, RMMCH cell)")
print(act.tail(12).to_string(index=False))
for y0, y1 in ((1991, 2020), (2016, 2019), (2020, 2025)):
    s = act[act.season.str[:4].astype(int).between(y0, y1)]
    print(f"  {y0}-{y1}: mean {s.events.mean():.1f} events and {s.heatwave_days.mean():.1f} heatwave days per season")

fc_path = sorted((ROOT / "data" / "previous_runs").glob("*.csv"))
if not fc_path:
    print("No forecast archive yet: run scripts/fit_bias.py first.")
    sys.exit(0)
fc = pd.read_csv(fc_path[-1], parse_dates=["date"])
seasons = {"2024/25": ("2024-09-01", "2025-04-30"), "2025/26": ("2025-09-01", "2026-04-30")}
lookup = obs.set_index("date")
rows = []
for test_s, (t0, t1) in seasons.items():
    train_s = [s for s in seasons if s != test_s][0]
    tr0, tr1 = seasons[train_s]
    m = bias.Mapping.fit(fc[(fc.date >= tr0) & (fc.date <= tr1)], obs[["date", "tmax"]])
    fci = fc.set_index("date")
    for issue in pd.date_range(t0, t1, freq="D"):
        # Forecast series from the run issued on `issue`: day j (1..8) is target issue+j-1 at lead j-1
        tgt = [issue + pd.Timedelta(days=j) for j in range(8)]
        if not all(t in fci.index and t in lookup.index for t in tgt):
            continue
        raw = np.array([fci.loc[t, f"lead{j}"] for j, t in enumerate(tgt)], dtype=float)
        if np.isnan(raw).any():
            continue
        cor = np.array([m.correct([raw[j]], j)[0] for j in range(8)])
        thr = np.array([lookup.loc[t, "thr"] for t in tgt])
        # Pad one day either side from ERA5 so runs that cross the window edge are judged the same way
        fhw = A.heatwave_days(A.hot_days(cor, thr, a["comparison"]), a["run_length_days"])
        ohw = np.array([lookup.loc[t, "hw"] for t in tgt])
        for band, (s, e) in {"days 1-3": (1, 3), "days 4-7": (4, 7), "day 8": (8, 8)}.items():
            rows.append({"test_season": test_s, "issue": issue.date(), "band": band,
                         "forecast": bool(fhw[s - 1:e].any()), "observed": bool(ohw[s - 1:e].any())})
h = pd.DataFrame(rows)


def score(g):
    hits = int((g.forecast & g.observed).sum())
    miss = int((~g.forecast & g.observed).sum())
    fa = int((g.forecast & ~g.observed).sum())
    cn = int((~g.forecast & ~g.observed).sum())
    return pd.Series({"issue_days": len(g), "hits": hits, "misses": miss, "false_alarms": fa, "correct_negatives": cn,
                      "hit_rate": round(hits / (hits + miss), 2) if hits + miss else np.nan,
                      "false_alarm_ratio": round(fa / (hits + fa), 2) if hits + fa else np.nan})


sk = h.groupby("band").apply(score, include_groups=False).reindex(["days 1-3", "days 4-7", "day 8"]).reset_index()
sk.to_csv(OUT / "hindcast_skill.csv", index=False)
print("\nHindcast skill, warm seasons 2024/25 and 2025/26 (cross-validated bias correction)")
print(sk.to_string(index=False))
