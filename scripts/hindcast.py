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
rows, days = [], []
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
        ob = np.array([lookup.loc[t, "tmax"] for t in tgt])
        fhw = A.heatwave_days(A.hot_days(cor, thr, a["comparison"]), a["run_length_days"])
        # Observed heatwave days judged on the same 8-day window the forecast sees, so a run already in
        # progress before the issue day is treated the same way on both sides
        ohw = A.heatwave_days(A.hot_days(ob, thr, a["comparison"]), a["run_length_days"])
        ohw_full = np.array([lookup.loc[t, "hw"] for t in tgt])
        for j in range(8):
            days.append({"lead_day": j + 1, "obs": ob[j], "raw": raw[j], "cor": cor[j], "thr": thr[j]})
        for band, (s, e) in {"days 1-3": (1, 3), "days 4-7": (4, 7), "day 8": (8, 8)}.items():
            rows.append({"test_season": test_s, "issue": issue.date(), "band": band,
                         "forecast": bool(fhw[s - 1:e].any()), "observed": bool(ohw[s - 1:e].any()),
                         "observed_full": bool(ohw_full[s - 1:e].any()),
                         # tolerant: forecast heatwave within one day either side of the band
                         "forecast_pm1": bool(fhw[max(s - 2, 0):min(e + 1, 8)].any())})
h = pd.DataFrame(rows)
dd = pd.DataFrame(days)


def score(g, f="forecast", o="observed"):
    F, O = g[f], g[o]
    hits = int((F & O).sum())
    miss = int((~F & O).sum())
    fa = int((F & ~O).sum())
    cn = int((~F & ~O).sum())
    return pd.Series({"issue_days": len(g), "hits": hits, "misses": miss, "false_alarms": fa, "correct_negatives": cn,
                      "hit_rate": round(hits / (hits + miss), 2) if hits + miss else np.nan,
                      "false_alarm_ratio": round(fa / (hits + fa), 2) if hits + fa else np.nan})


order = ["days 1-3", "days 4-7", "day 8"]
out = []
for label, f, o in (("same window (primary)", "forecast", "observed"),
                    ("observed from full record", "forecast", "observed_full"),
                    ("within 1 day (tolerant)", "forecast_pm1", "observed")):
    s = h.groupby("band").apply(score, f=f, o=o, include_groups=False).reindex(order).reset_index()
    s.insert(0, "scoring", label)
    out.append(s)
sk = pd.concat(out)
sk.to_csv(OUT / "hindcast_skill.csv", index=False)
print("\nHindcast skill, warm seasons 2024/25 and 2025/26 (cross-validated bias correction)")
print(sk.to_string(index=False))

# Day-level check: on days ERA5 is above the threshold, how close is the forecast?
hot = dd[dd.obs > dd.thr]
diag = hot.groupby("lead_day").apply(lambda g: pd.Series({
    "n_hot_days": len(g), "obs_minus_thr": round((g.obs - g.thr).mean(), 2),
    "raw_error": round((g.raw - g.obs).mean(), 2), "corrected_error": round((g.cor - g.obs).mean(), 2),
    "corrected_above_thr": round(float((g.cor > g.thr).mean()), 2)}), include_groups=False).reset_index()
allday = dd.groupby("lead_day").apply(lambda g: pd.Series({
    "corrected_mae_all": round(float((g.cor - g.obs).abs().mean()), 2),
    "corr_all": round(float(np.corrcoef(g.cor, g.obs)[0, 1]), 3)}), include_groups=False).reset_index()
diag = diag.merge(allday, on="lead_day")
diag.to_csv(OUT / "hindcast_hot_days.csv", index=False)
print("\nOn days ERA5 was above the threshold")
print(diag.to_string(index=False))
