# Progress: Heat-EWS for BioHEAT

Goal file: GOAL.md (version 2). Session 1 started 20 Oct 2026, 19:45 SAST.

## Criteria status

| # | Criterion (short) | Status | Evidence |
|---|---|---|---|
| 1 | ERA5 Tmax at site, coords in config | **pass** | iter 6. Coords [CHECK] Q5 |
| 2 | Reproduce SOP Appendix 1 within 0.3 °C | **pass** | iter 6, `scripts/check_replication.py` |
| 3 | D1 table, both periods, independent recompute 0.1 °C | **pass** | iter 7, `scripts/compare_recompute.py` |
| 4 | Config-driven thresholds, percentile/window unit test | **pass** | `tests/test_thresholds.py` |
| 5 | Station comparison | partial | SAWS done (iter 8). On-site Davis blocked on Q6 |
| 6 | ECMWF ensemble from open source, logged | **pass** | iter 13: 51 members, source and fetch time on page and in docs/runs.csv |
| 7 | Bias correction by lead, tested held-out | **pass** | iter 14, `outputs/bias_holdout.csv` |
| 8 | "System not updated" on failed fetch, tested | **pass** | `tests/test_run.py::test_failed_fetch_never_shows_no_alert` |
| 9 | Strict-above, run length config | **pass** | `tests/test_alert.py` |
| 10 | Warning/Watch cut-offs config | **pass** | `tests/test_alert.py::test_watch_needs_member_fraction` |
| 11 | SOP worked-example and edge-case tests | **pass** | 14 tests in `tests/test_alert.py` |
| 12 | Page | built | sample render checked (iter 9); needs a live run |
| 13 | Email on change, test address | built | logic tested with a stub; needs SMTP account and test address |
| 14 | Daily schedule, 7 runs | built | `.github/workflows/daily.yml`; needs the repo |
| 15 | Hindcast scores by lead band | built, not yet run | needs forecast archive; days 8 to 14 cannot be scored with open data |
| 16 | Trust horizon and activations per season | half done | activations done (iter 8); trust horizon needs C15 |
| 17 | One-command rebuild, pinned | partial | clean checkout rebuilds all finished steps (iter 10); bias and run steps pending |
| 18 | Repo in Wits PHR org, no secrets | blocked | needs Craig to approve creating the repo |
| 19 | README test by outsider | open | README written |
| 20 | Independent review | open | |

## Iteration log

**Iter 1 (19:45).** Set up config.yaml, heatews package, tests. Open-Meteo archive reachable; ensemble API returned 429 once.

**Iter 2 (19:50).** C2 first try via Open-Meteo ERA5 at Soweto: P90 max |diff| 0.27, P95 max |diff| 0.36 °C. Just fails.

**Iter 3 (19:55).** Unit tests: 19 pass after fixing a leap-day bug (29 Feb not pooled with 28 Feb).

**Iter 4 (19:58).** Open-Meteo returned "Daily API request limit exceeded" for every API. Long multi-year requests count as many calls. Switched ERA5 to the public NSF NCAR copy on AWS (ranged reads of hourly 2 m temperature, 5 x 4 cell block around Soweto and RMMCH). Threads were serialised by h5py, so moved to processes. Google ARCO ERA5 ruled out (whole-globe chunks); AWS era5-pds retired (access denied).

**Iter 5 (20:00).** Built forecast fetch/parse, lead-dependent quantile mapping, page renderer, notifier, daily run, workflow, Makefile, README. Run tests: 24 pass, including the failed-fetch path.

**Iter 6 (20:05).** ERA5 1991-01 to 2026-07 complete (NCAR has nothing after July 2026 yet). C2 rerun on raw ERA5: Soweto cell (-26.25, 27.75), SAST day, 2016-2019.
P90 max |diff| 0.27 °C, mean +0.03. P95 max |diff| 0.22 °C, mean +0.05. **PASS.** UTC day gives the same result. The Iter 2 gap came from Open-Meteo's elevation adjustment, so the SOP was built from raw ERA5.

**Iter 7 (20:06).** C3: `build_d1.py` then `recompute_independent.py` (plain numpy, hand-written type 7 percentile, no shared code) then `compare_recompute.py`: 96 values compared, max |diff| 0.0000 °C. **PASS.**

**Iter 8 (20:08).** C5 SAWS part: Johannesburg Intl (68368, GHCN-Daily), 1991-01 to 2020-05, 9253 days. ERA5 cell (-26.25, 28.25). All months: bias -0.20 °C, RMSE 1.79, r 0.915. Sept to April: bias -0.45 °C, RMSE 1.84, r 0.863, station P95 30.1 vs ERA5 30.0. Bias under 1 °C.
C16 activations (ERA5 RMMCH cell, SOP P95): 1.2 events per season over 1991-2020, 14 of 29 seasons with none; 2.3 per season over 2020-2025. Alternatives in `outputs/activation_scenarios.csv`.

**Iter 9 (20:10).** Rendered a sample page with a synthetic ensemble; chart checked visually (`outputs/sample_chart.png`). Wrote D1 note (`outputs/D1_note.md`).

**Iter 10 (20:15).** C17: fresh `git clone` into scratch, then `make install era5 stations thresholds test validate`. ERA5 pulled from scratch, replication PASS (same numbers), recompute 0.0000 °C, 24 tests pass, station and activation outputs identical. The bias and run steps are still to do (Open-Meteo).

**Iter 11 (20:20).** Drafted reply-all to Ijeoma and Nic in Outlook (cc Sam, Matthew), left unsent for Craig. It gives the D1 table and asks Q3, Q4, Q6, Q7. The Friday line is highlighted for Craig to check. Scheduled this session to resume at 02:20 SAST for C6, C7, C15.

**Iter 12 (20:45 to 21:00).** With Craig's OK: created Wits-Planetary-Health-Research/heat-ews-bioheat, made it public (Pages needs public on the free plan), installed the Claude GitHub app on the org for this repo only, pushed. Added SMTP_USER secret; SMTP_PASSWORD form left open for Craig. Pages source set to GitHub Actions. Made mail failures non-fatal (new test, 25 pass).

**Iter 13 (20:59).** First live run on GitHub Actions: ECMWF IFS ensemble, 51 members, fetched 18:59 UTC. Status No alert; 27% of members show a heatwave in days 8 to 14; not yet bias-corrected. Page live at https://wits-planetary-health-research.github.io/heat-ews-bioheat/ and checked by eye: status, chart, threshold step at 1 Nov (32.1 to 32.3), day table. C6 source and access logged on the page and in docs/runs.csv. Started the rebuild workflow on GitHub (own Open-Meteo quota) to fit the bias correction and run the hindcast.

**Iter 14 (21:25).** Rebuild workflow on GitHub (clean machine): make install era5 stations thresholds bias validate test all passed and committed data/bias_mapping.json. C7 held-out (train 2024/25, test 2025/26 warm season, 242 days per lead): raw IFS runs about 1 °C cold at every lead (bias -0.7 to -1.4). Quantile mapping: bias within ±0.35 °C and lower MAE at every lead (day 1 1.35 to 0.82, day 4 1.76 to 1.47, day 8 2.45 to 2.05). **PASS.**
C15 first pass looked weak (days 1-3 hit rate 0.22, FAR 0.60). The scoring took observed heatwaves from the full record but forecast ones from the 8-day window, which penalises runs already under way on the issue day. Rescoring on the same window, plus a tolerant score and a hot-day error check; the forecast archive is now committed so this can run locally. Rerunning on GitHub.

## Findings Craig should see

- The SOP's 2016-2019 thresholds are 1 to 2.6 °C above the 1991-2020 normal from October to January (Jan P95 32.6 vs 30.0). On them, about half of past warm seasons had no qualifying heatwave.
- SOP-BH-13's second worked example marks 32.9 °C as not above 32.6 °C. Typo; the conclusion (not a heatwave) still holds.
- The SOP table is for the Soweto cell; RMMCH is the next cell east. On 2016-2019 they differ by up to 0.3 °C.

## Decisions made without Craig

| Date | Decision | Reason | How to reverse |
|---|---|---|---|
| 20 Oct | Operational thresholds = published SOP Appendix 1 P95 (use_sop_table: true) | SOP is the approved study document | config.yaml thresholds block |
| 20 Oct | Daily Tmax = max of hourly ERA5 over the SAST day | Matches local reading; makes no difference to the replication | era5_ncar.daily_tmax(day=...) |
| 20 Oct | Percentile = linear interpolation (type 7) | Reproduces the SOP table | thresholds.monthly |
| 20 Oct | RMMCH coordinates -26.176, 27.985 | Approximate, flagged [CHECK] | config.yaml site |
| 20 Oct | ERA5 source = NSF NCAR copy on AWS, raw grid values | Open-Meteo quota; raw grid matches the SOP | scripts/pull_ncar_era5.py |
| 20 Oct | Bias correction trained on IFS deterministic past forecasts (leads 0 to 7), applied to ensemble members; days 9 to 15 reuse lead 7 | No open archive of ensemble forecasts; same model at the same resolution | heatews/bias.py |
| 20 Oct | Daily run at 07:13 SAST | Latest overnight ECMWF run is on Open-Meteo by then; page fresh for the working day | .github/workflows/daily.yml |
| 20 Oct | Email on status change only | GOAL default Q7 | config.yaml notify.mode |

## Blockers

- C6, C7, C15: Open-Meteo quota for this connection resets around 02:00 SAST. A scheduled resume is set.
- C5 (Davis part): Vital Weather export or API login (Q6).
- C13: an SMTP sending account and a test address. Nothing goes to real recipients without Craig.
- C14, C18: a repo in the Wits PHR GitHub org. Craig to approve creating it.
- C19: a person outside the build team to follow the README.
