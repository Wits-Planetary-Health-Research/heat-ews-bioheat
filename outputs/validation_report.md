# Validation report (D6)

Heat-EWS for BioHEAT, RMMCH. 20 Oct 2026. Numbers come from `outputs/` and can be rebuilt with `make thresholds bias validate`.

## 1. Thresholds

- SOP-BH-13 Appendix 1 is reproduced from raw ERA5 (Soweto cell -26.25, 27.75, 2016 to 2019, SAST day, linear percentile) in every month. Max difference 0.27 °C (P90) and 0.22 °C (P95).
- A separate script with no shared code gives the same D1 values (96 compared, max difference 0.0000 °C).

## 2. ERA5 against a station

SAWS Johannesburg International (68368, GHCN-Daily), 1991 to May 2020, ERA5 cell -26.25, 28.25:

| Months | Days | Bias (ERA5 minus station) | RMSE | Correlation | P95 station / ERA5 |
|---|---|---|---|---|---|
| All | 9253 | -0.20 °C | 1.79 °C | 0.915 | 29.5 / 29.5 |
| Sept to April | 6165 | -0.45 °C | 1.84 °C | 0.863 | 30.1 / 30.0 |

The bias is under 1 °C. The on-site Davis station at RMMCH isn't compared yet (needs a Vital Weather export).

## 3. Bias correction

Past ECMWF IFS 0.25° forecasts (Open-Meteo Previous Runs), trained on the 2024/25 warm season and tested on 2025/26 (242 days per lead). The raw forecast runs 0.7 to 1.4 °C cold at every lead. Both corrections remove the mean bias and lower the MAE at every lead (`bias_holdout.csv`).

The two differ on hot days. On days ERA5 was above the threshold, quantile mapping left the forecast 2.1 °C too cold on average, compared with 0.3 °C for a mean shift by lead (`correction_comparison.csv`). Quantile mapping matches the overall spread but cools the tail. Because the forecast already underestimates hot days, that makes the misses worse. The system uses the mean shift.

## 4. Can it see heatwaves coming?

Hindcast, warm seasons 2024/25 and 2025/26, 484 issue days. The correction is trained on the other season each time. A heatwave is 2 or more consecutive days above the monthly P95 from ERA5 at RMMCH, 1991 to 2020 (switched from the SOP's Soweto 2016 to 2019 values on 21 Oct 2026), judged on the same 8-day window for forecast and ERA5.

| Warning window | Heatwaves caught | Missed | False alarms | Hit rate | False-alarm ratio |
|---|---|---|---|---|---|
| Days 1 to 3 | 24 | 2 | 25 | 0.92 | 0.51 |
| Days 4 to 7 | 32 | 2 | 36 | 0.94 | 0.53 |
| Day 8 | 14 | 2 | 21 | 0.88 | 0.60 |

With these thresholds a warm season has about 3 heatwave events on average over 1991 to 2020, and about 4 since 2020 (`activations_per_season.csv`). On the old SOP values it was about 1, with half of seasons having none.

## 5. How far ahead can it be trusted

A Warning for the coming week catches 9 in 10 heatwaves. About half of Warnings will not turn into a full heatwave, though the forecast heat is usually close. Day 8 is still useful. Days 9 to 14 cannot be scored with open data, so read Watch as a heads-up.

In practice: use a Warning to start getting ready and confirm with the next day's run before activating.

## 6. Limits

- The skill numbers rest on about 30 heatwave windows over two seasons. Treat them as rough.
- The hindcast uses the deterministic IFS run. The live system uses the median of the 51-member ensemble, which is smoother and may sit a little lower on hot days.
- ERA5 smooths over a 25 km box. The hospital itself may run hotter, and the on-site station will show by how much.
- The SOP-BH-13 Appendix 1 values (four years, neighbouring Soweto cell) are no longer used for the alert. They can be switched back with `thresholds.source: sop`. See `D1_note.md`.
