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

Hindcast, warm seasons 2024/25 and 2025/26, 484 issue days. The correction is trained on the other season each time. A heatwave is the SOP definition (2 or more consecutive days above the monthly P95), judged on the same 8-day window for forecast and ERA5.

| Warning window | Heatwaves caught | Missed | False alarms | Hit rate | False-alarm ratio |
|---|---|---|---|---|---|
| Days 1 to 3 | 10 | 5 | 14 | 0.67 | 0.58 |
| Days 4 to 7 | 15 | 5 | 29 | 0.75 | 0.66 |
| Day 8 | 4 | 3 | 18 | 0.57 | 0.82 |

Activations per warm season over 1991 to 2025 are in `activations_per_season.csv` and `activation_scenarios.csv`.

## 5. How far ahead can it be trusted

A Warning for the coming week catches about 2 in 3 heatwaves. More than half of Warnings will not turn into a heatwave that meets the SOP definition. The forecast heat is usually there, just slightly short of the threshold or one day short of a 2-day run. By day 8 most alerts are false. Days 9 to 14 cannot be scored with open data, so Watch should be read as a heads-up to keep checking, and never as grounds to activate.

In practice: use Warning to start getting ready (kits, sonographer bookings) and confirm with the next day's run before activating.

## 6. Limits

- The skill numbers rest on 15 to 20 heatwave windows over two seasons. Treat them as rough.
- The hindcast uses the deterministic IFS run. The live system uses the median of the 51-member ensemble, which is smoother and may sit a little lower on hot days.
- ERA5 smooths over a 25 km box. The hospital itself may run hotter, and the on-site station will show by how much.
- The SOP thresholds come from four years for the neighbouring Soweto cell. See `D1_note.md`.
