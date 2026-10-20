"""Criterion 7: fit the lead-dependent quantile mapping and test it on held-out data.

Training: warm season Sept 2024 to Apr 2025. Test: warm season Sept 2025 to Apr 2026 (to the last ERA5 day).
Then refit on everything and save data/bias_mapping.json for the daily run.
Writes outputs/bias_holdout.csv
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from heatews import bias, config, era5_ncar as E  # noqa: E402

cfg = config.load()
lat, lon = cfg["site"]["latitude"], cfg["site"]["longitude"]
obs = E.daily_tmax(lat, lon, "SAST")
end = obs.date.max().date()
fc = bias.fetch_previous_runs(lat, lon, "2024-03-01", str(end))

train = fc[(fc.date >= "2024-09-01") & (fc.date <= "2025-04-30")]
test = fc[(fc.date >= "2025-09-01") & (fc.date <= "2026-04-30")]
m = bias.Mapping.fit(train, obs)
t = test.merge(obs.rename(columns={"tmax": "obs"}), on="date")
t = t[t.date.dt.month.isin(bias.WARM)]
rows = []
for k in range(0, 8):
    d = t[[f"lead{k}", "obs"]].dropna()
    raw = d[f"lead{k}"].values
    cor = m.correct(raw, k)
    shift = raw + m.table[k]["mean_shift"]
    o = d.obs.values
    rows.append({"forecast_day": k + 1, "lead": k, "n_test": len(d),
                 "raw_bias": round(float((raw - o).mean()), 2), "raw_mae": round(float(np.abs(raw - o).mean()), 2),
                 "qm_bias": round(float((cor - o).mean()), 2), "qm_mae": round(float(np.abs(cor - o).mean()), 2),
                 "shift_bias": round(float((shift - o).mean()), 2), "shift_mae": round(float(np.abs(shift - o).mean()), 2),
                 "raw_p95": round(float(np.quantile(raw, .95)), 1), "qm_p95": round(float(np.quantile(cor, .95)), 1),
                 "obs_p95": round(float(np.quantile(o, .95)), 1)})
r = pd.DataFrame(rows)
(ROOT / "outputs").mkdir(exist_ok=True)
r.to_csv(ROOT / "outputs" / "bias_holdout.csv", index=False)
print(r.to_string(index=False))
improved = (r.qm_mae <= r.raw_mae).all() and (r.qm_bias.abs() <= r.raw_bias.abs() + 0.05).all()
print("Held-out test:", "PASS (quantile mapping no worse than raw at every lead)" if improved else "CHECK")

full = fc[fc.date.dt.month.isin(bias.WARM)]
bias.Mapping.fit(full, obs).save(ROOT / "data" / "bias_mapping.json")
print("Saved data/bias_mapping.json, trained on", full.date.min().date(), "to", full.date.max().date())
