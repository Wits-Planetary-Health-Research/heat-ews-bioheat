# Goal: Heat early warning for BioHEAT, RMMCH site

Version 2, 20 Oct 2026. Updated against SOP-BH-13 and SOP-BH-07 (see Sources). Changes from version 1 are listed at the end.

## Objective

Give the BioHEAT study coordinator and Ijeoma Solarin a daily, dependable signal of whether a heatwave, as SOP-BH-13 defines it, is forecast at Rahima Moosa Mother and Child Hospital over the next 14 days, so heatwave visits can be activated in time. It must be simple enough to run without the build team and transparent enough to defend in a methods section.

## Heatwave definition (from SOP-BH-13)

Daily maximum ambient temperature above the 95th percentile for that month on at least 2 consecutive days. "Above" means strictly greater than: the SOP's worked example marks a day exactly at the threshold as not hot. The visit window is the heatwave days plus up to 2 days after. Monitoring runs daily in the warm season (Sept to April), using the 15-day forecast.

## Deliverables

- **D1 Interim threshold table:** monthly 90th and 95th percentiles of daily Tmax, September to April, for the RMMCH location. Includes a side-by-side with the values in SOP-BH-13 Appendix 1 and the method in one paragraph. Due Fri 23 Oct 2026.
- **D2 Thresholds file:** a config-driven thresholds CSV (monthly, matching the SOP, plus an optional calendar-day version), with the code that produces it.
- **D3 Forecast pipeline:** a daily job that pulls the latest ECMWF ensemble forecast for the site, bias-corrects it to the threshold's climate, and writes a 14-day forecast table.
- **D4 Alert logic:** a function that turns the forecast into a status for the coming fortnight: Warning (days 1 to 7), Watch (days 8 to 14) or No alert.
- **D5 Outputs:** a simple web page showing today's status, a 14-day chart against the threshold and a last-updated time, plus an email to the named recipients when status changes.
- **D6 Validation report:** hindcast performance by lead time, comparison with the on-site Davis station, and a short note on limits.
- **D7 Handover:** a README covering how to run it, how to change recipients and thresholds, what each status means, and what to do if it stops. Written so it can be cited from SOP-BH-13 as the "automated" monitoring option.

## Acceptance criteria

**Threshold (D1, D2)**
1. ERA5 daily Tmax (maximum of hourly 2 m temperature, local day SAST) is extracted at the site grid cell. Coordinates are recorded in the config.
2. Replication check: run on Soweto, 2016 to 2019, the code reproduces SOP-BH-13 Appendix 1 for all 12 months, within 0.3 °C. If it does not, the difference is explained in writing before going further.
3. D1 reports monthly P90 and P95 on both the SOP reference period (2016 to 2019) and the WMO 1991 to 2020 normal. Values match an independent recompute (separate script) to within 0.1 °C.
4. The percentile, reference period and monthly or calendar-day threshold are all config values. A unit test confirms the percentile and window maths on a synthetic series with a known answer.
5. ERA5 Tmax is compared with the on-site Davis Vantage Pro2 (via Vital Weather) over every overlapping day available, and with the nearest SAWS station if data can be had. The report gives bias, RMSE and correlation, and says plainly if the bias is over 1 °C.

**Forecast (D3)**
6. The pipeline pulls the ECMWF ensemble (all members, at least 14 days lead) from an open source with no paid licence. The source and access date are logged on every run.
7. The forecast is bias-corrected to ERA5 climate by lead time (quantile mapping or mean shift, using reforecasts or a past forecast archive). The method is documented and tested on held-out data.
8. If the forecast fetch fails or is incomplete, the run reports "System not updated" with the time of the last good run. It never shows "No alert" in that case. A test simulates a failed fetch.

**Alert logic (D4)**
9. A heatwave day is Tmax strictly above the threshold for that day's month. A heatwave is 2 or more consecutive heatwave days. The run length and the comparison (strict or inclusive) are config values.
10. Warning: ensemble median meets the definition within days 1 to 7. Watch: at least 50% of members meet the definition within days 8 to 14. Both cut-offs are config values.
11. Unit tests reproduce both worked examples in SOP-BH-13 (January, threshold 32.6 °C) and cover: a day exactly at the threshold, a single hot day, exactly 2 days, a run that crosses a month boundary with different thresholds, a run that straddles day 7 and day 8, and missing members.

**Outputs (D5)**
12. The page shows status, a 14-day chart with the threshold line and ensemble spread, the issue time and the data source. It works on a phone.
13. The email goes only when status changes (or as a daily digest if chosen). It is tested end to end with a test address before real recipients are added.
14. The job runs daily on a schedule with no manual step, and seven consecutive scheduled runs succeed.

**Validation (D6)**
15. A hindcast over at least 2015 to 2025 (Sept to April) reports hit rate, false alarm ratio and missed events at lead days 1 to 3, 4 to 7 and 8 to 14, against heatwaves defined from ERA5 with the SOP thresholds.
16. The report states plainly how far ahead the alert can be trusted, based on criterion 15, and how many heatwave activations per season the SOP thresholds would have produced.

**Reliability and handover (D7)**
17. The whole pipeline rebuilds from a clean checkout with one command. Package versions are pinned.
18. The code sits in the Wits Planetary Health Research GitHub org. No credentials are stored in the repo.
19. Someone outside the build team follows the README and changes a recipient and the run length without help.
20. An independent review against this file passes before handover.

## Constraints

- Open data only: ERA5 (Copernicus CDS or the Open-Meteo archive), ECMWF open data or the Open-Meteo ensemble API, SAWS where available, and the study's own Davis station data.
- Python for the pipeline, with GitHub Actions for scheduling and GitHub Pages for the page. SOP-BH-07 plans R for the station API, so the station reader may be R. [CHECK]
- No patient or study participant data goes into this system. Weather station data are not identifiable but follow SOP-BH-07 handling rules.
- Nothing is sent to real recipients until Craig approves.
- 24-hour build target for D1 to D5. D6 and D7 can follow.

## Out of scope (for now)

- WhatsApp delivery (phase 2, needs a Meta Business number or Twilio).
- Health-based thresholds from DLNM work.
- Other sites or cities.
- Changing the SOP itself. The system reports what the SOP says; any proposed change goes to Ijeoma as a recommendation.

## Open decisions

| # | Question | Who | Default used until answered |
|---|----------|-----|-----------------------------|
| Q1 | Variable | Answered by SOP-BH-13 | Daily Tmax |
| Q2 | Run length | Answered by SOP-BH-13 | 2 consecutive days |
| Q3 | Threshold percentile. The SOP says P95; Nic and Ijeoma's emails say P90. Which drives the alert? | Ijeoma | P95 (SOP), with P90 shown on the page |
| Q4 | Reference period. The SOP uses 2016 to 2019 only, leaving out 2020 to 2024 as unusually hot. Four years gives unstable percentiles. Keep it, or move to 1991 to 2020? | Ijeoma, with Craig's advice | Alert on SOP values; report 1991 to 2020 alongside in D1 |
| Q5 | Location. The SOP thresholds are for Soweto; the site is RMMCH. Which grid cell? | Ijeoma / Sam | RMMCH, -26.17, 27.98 [CHECK], Soweto kept for the replication check |
| Q6 | Does Vital Weather have API access, who holds the login, and does it publish the 15-day forecast SOP-BH-13 refers to? | Ijeoma / data manager | Treat station as observations only |
| Q7 | Who receives alerts, and how: on change or a daily digest? SOP-BH-13 has "person X or automated" as a placeholder. | Ijeoma | Ijeoma and study coordinator, on change |
| Q8 | What is Sibu's role: threshold, review or sign-off? | Craig | Reviewer of D1 and D6 |
| Q9 | Watch cut-off: is 50% of members right? | Craig / Ijeoma | 50% |

## Roles

- Build lead: Sam Zermatten-Jack
- Scope and methods sign-off: Craig Parker
- User and SOP owner: Ijeoma Solarin
- Named collaborator: Sibusiso Hlatjwako (Sibu)

## Stop conditions

- Iteration cap: 25 per session.
- Hard deadline: D1 to Ijeoma by Fri 23 Oct 2026.

## Sources

- SOP-BH-13 Heatwave visit, draft 0.1 (effective 2 Dec 2025, Ijeoma Solarin). Wits PHR SharePoint, SOPs under review.
- SOP-BH-07 Data collection from on-site weather station and indoor temperature loggers, V0.1. Same folder.
- Email thread "Heat-EWS for BioHEAT", Nic Brink and Ijeoma Solarin, 20 Oct 2026.

## Changes from version 1

- Threshold moved from P90 to P95 per month, as the SOP states; P90 kept in D1 and on the page (Q3).
- Monthly thresholds are now the default, matching the SOP; calendar-day becomes optional.
- Added the replication check (criterion 2) and the SOP worked-example tests (criterion 11).
- "Above" set to strictly greater than, per the SOP example.
- Station comparison now targets the on-site Davis Vantage Pro2 first.
- Q1 and Q2 answered; Q3 to Q6 added.
