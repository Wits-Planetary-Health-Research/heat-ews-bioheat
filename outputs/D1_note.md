# BioHEAT heat thresholds: Sept to April (D1)

Prepared 20 Oct 2026 for Ijeoma Solarin. Daily maximum temperature (Tmax), °C.

## Monthly thresholds

| Month | SOP-BH-13 P95 | RMMCH, 1991-2020 P95 | SOP-BH-13 P90 | RMMCH, 1991-2020 P90 |
|---|---|---|---|---|
| Sep | 30.5 | 29.8 | 30.1 | 29.0 |
| Oct | 32.1 | 31.4 | 31.7 | 30.3 |
| Nov | 32.3 | 30.6 | 31.0 | 29.5 |
| Dec | 31.8 | 30.4 | 31.0 | 29.5 |
| Jan | 32.6 | 30.0 | 30.7 | 29.2 |
| Feb | 29.8 | 29.7 | 28.9 | 28.9 |
| Mar | 28.9 | 28.7 | 28.7 | 27.9 |
| Apr | 27.5 | 26.5 | 27.0 | 25.8 |

The full set, including RMMCH on 2016-2019 and Soweto on 1991-2020, is in `D1_thresholds.csv`.

## How these were made

Daily Tmax is the highest hourly ERA5 2 m temperature (0.25° grid, public NSF NCAR copy) over each SAST calendar day. Percentiles pool every day in the calendar month across the reference years, using linear interpolation (R quantile type 7). The SOP column is SOP-BH-13 Appendix 1 as published. The same code reproduces that table from ERA5 for the Soweto grid cell (-26.25, 27.75) over 2016-2019 to within 0.27 °C in every month, so the method matches. The RMMCH grid cell is -26.25, 28.0. A separate script with no shared code gives identical values. ERA5 agrees well with SAWS Johannesburg International over 1991-2020 (warm-season bias -0.45 °C, RMSE 1.8 °C, correlation 0.86, 95th percentiles within 0.1 °C).

## What the choice of threshold means in practice

Heatwave events per warm season, SOP definition (2+ consecutive days above the threshold), ERA5 at RMMCH:

| Threshold | Events per season, 1991-2020 | Seasons with none, 1991-2020 (of 29) | Events per season, 2020-2025 |
|---|---|---|---|
| SOP P95 (current) | 1.2 | 14 | 2.3 |
| SOP P90 | 2.5 | 9 | 3.8 |
| 1991-2020 P95 | 3.0 | 8 | 3.8 |
| 1991-2020 P90 | 5.8 | 2 | 7.2 |

On the current SOP thresholds, about half of past warm seasons had no qualifying heatwave. The 2016-2019 base runs warmer than the 1991-2020 normal from October to January, by up to 2.6 °C in January, which is why it triggers less often. The alert system uses the SOP P95 values by default and can switch to any of the others with one setting.
