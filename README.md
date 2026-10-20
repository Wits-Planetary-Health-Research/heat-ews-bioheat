# Heat-EWS for BioHEAT (RMMCH)

A daily heat alert for the BioHEAT study at Rahima Moosa Mother and Child Hospital. It checks the ECMWF ensemble forecast against the SOP-BH-13 heatwave definition and tells the study team whether a heatwave is coming in the next 14 days.

It does the forecast check in SOP-BH-13 ("person X or automated"). It does not decide on activation. The PI or designee still does that.

## What the statuses mean

| Status | Meaning | What to do |
|---|---|---|
| Warning | A heatwave is forecast within days 1 to 7 | Start SOP-BH-13 preparations. Check the next day's run, then ask the PI or designee to decide on activation |
| Watch | At least half the ensemble shows a heatwave in days 8 to 14 | No action yet. Check the page each day |
| No alert | No heatwave forecast in the next 14 days | Nothing |
| System not updated | Today's forecast didn't load | Don't read this as "no heatwave". Check the SAWS forecast by hand and tell Craig or Sam |

A heatwave is daily maximum temperature **above** the monthly 95th percentile (SOP-BH-13 Appendix 1) on at least 2 consecutive days. A day exactly at the threshold doesn't count, as in the SOP's worked example.

## Where to see it

- The page: GitHub Pages for this repo (link in the repo's About box). It shows today's status, a 14-day chart against the threshold and a day-by-day table.
- Email: sent when the status changes, to the people in `config.yaml`.

## Change something

Everything you'd want to change is in `config.yaml`. Edit it on GitHub (pencil icon), then commit. The next run picks it up.

- Add or remove an email recipient: edit `notify.recipients`. One address per line, like `- name@witsphr.org`.
- Change the run length: `alert.run_length_days` (SOP says 2).
- Switch from P95 to P90: set `thresholds.percentile: 90`. With `use_sop_table: true` it uses the Appendix 1 P90 column.
- Use thresholds computed from a different period: set `use_sop_table: false` and set `reference_period`, for example `[1991, 2020]`. You'll need to rerun `make era5` first.
- Count a day exactly at the threshold as hot: `alert.comparison: inclusive`.
- Change the Watch cut-off: `alert.watch_member_fraction` (0.5 is half the members).

To run it straight away, go to Actions, pick "Daily heat alert" and press "Run workflow". Tick "test email" to send only to `notify.test_recipients`.

## If it stops

- The page says "System not updated": the forecast service didn't answer. It normally sorts itself out by the next day. If it lasts more than 2 days, check the Actions tab for the error.
- No new page for a day or more: GitHub may have paused the schedule. This happens after 60 days with no commits on the repo. Open Actions and re-enable the workflow.
- Emails stopped: check the `SMTP_*` secrets under Settings, Secrets and variables, Actions.

## How it works

1. Each day at 07:13 SAST, GitHub Actions fetches the latest ECMWF IFS ensemble (51 members, 0.25°) for the site from Open-Meteo, which serves ECMWF open data.
2. Each member's hourly temperature becomes a daily maximum over the SAST day.
3. Each forecast day is bias-corrected to ERA5 with a mean shift by lead time, fitted on past IFS forecasts (`data/bias_mapping.json`). The raw forecast runs about 1 °C cold. Days 9 to 14 use the lead 7 correction because there's no open archive past that.
4. The thresholds are the SOP-BH-13 Appendix 1 values for each month.
5. Warning if the ensemble median shows a heatwave in days 1 to 7. Watch if at least half the members show one in days 8 to 14.

## Rebuild from scratch

```
make all
```

This installs pinned packages, pulls the ERA5 block (about 15 minutes), builds the threshold tables and checks, fits the bias correction, runs the tests and does one alert run. Each step also runs on its own: `make era5`, `make thresholds`, `make bias`, `make test`, `make run`.

## Data

- ERA5 hourly 2 m temperature, 0.25°, from the public NSF NCAR copy on AWS (`s3://nsf-ncar-era5`). No account needed.
- ECMWF IFS ensemble and past IFS forecasts through Open-Meteo (CC BY 4.0, free for non-commercial use).
- SAWS Johannesburg International (68368) daily Tmax from NOAA GHCN-Daily, used only for the station check.
- The on-site Davis Vantage Pro2 (SOP-BH-07) isn't connected yet.

No participant data goes into this system.

## Checks and what they showed

The full log is in `PROGRESS.md`. Short version:

- SOP replication: the code reproduces SOP-BH-13 Appendix 1 from raw ERA5 for the Soweto grid cell (-26.25, 27.75), 2016 to 2019, for all 12 months. Max difference 0.27 °C (P90) and 0.22 °C (P95).
- Independent recompute: see `outputs/D1_independent.csv` and `scripts/compare_recompute.py`.
- Station check: ERA5 against SAWS Johannesburg International, Sept to April 1991 to 2020: bias -0.45 °C, RMSE 1.8 °C, same 95th percentile within 0.1 °C.
- Bias correction: mean shift brings the cold bias to near zero and keeps hot days within 0.3 °C. Quantile mapping was tried and dropped because it made hot days 2 °C colder.
- Hindcast, 2024/25 and 2025/26: a Warning in days 1 to 3 caught 10 of 15 heatwaves, days 4 to 7 caught 15 of 20. More than half of Warnings didn't meet the SOP definition. Full write-up in `outputs/validation_report.md`.

## Known limits

- The SOP thresholds come from four years (2016 to 2019) for Soweto. Four years is a thin base for a 95th percentile, and the site is in a neighbouring grid cell. `outputs/D1_thresholds.csv` sets them beside 1991 to 2020 and RMMCH values so the team can decide.
- Forecasts past about a week have little skill for a 2-day event. Treat Watch as a heads-up, not a forecast.
- Days 8 to 14 can't be scored against past forecasts with open data. See `PROGRESS.md`.
- ERA5 smooths over a 25 km box. The on-site station will show how far the hospital itself differs.

## Contacts

Craig Parker (methods), Sam Zermatten-Jack (build), Ijeoma Solarin (SOP owner).
