"""Build D1: monthly P90 and P95 of daily Tmax, Sept to April, for RMMCH and Soweto, on the SOP period
(2016 to 2019) and the WMO normal (1991 to 2020), next to SOP-BH-13 Appendix 1.

Writes outputs/D1_thresholds.csv and outputs/D1_full_year.csv
"""
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from heatews import config, era5_ncar as E, thresholds as T  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "outputs"
MONTHS = [9, 10, 11, 12, 1, 2, 3, 4]
NAMES = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct",
         11: "Nov", 12: "Dec"}


def build():
    cfg = config.load()
    cells = {"soweto": (-26.25, 27.75), "rmmch": (cfg["site"]["latitude"], cfg["site"]["longitude"])}
    periods = {"sop_2016_2019": (2016, 2019), "wmo_1991_2020": (1991, 2020)}
    rows = []
    for cname, (la, lo) in cells.items():
        df = E.daily_tmax(la, lo, "SAST")
        grid = df.attrs["grid"]
        for pname, yrs in periods.items():
            have = sorted(df[(df.date.dt.year >= yrs[0]) & (df.date.dt.year <= yrs[1])].date.dt.year.unique())
            assert have[0] == yrs[0] and have[-1] == yrs[1], f"missing years for {pname}: {have[:2]}..{have[-2:]}"
            for p in (90, 95):
                for m, v in T.monthly(df, yrs, p).items():
                    rows.append({"cell": cname, "grid_lat": grid[0], "grid_lon": grid[1], "period": pname,
                                 "month": m, f"pct": p, "value": round(v, 3)})
    r = pd.DataFrame(rows).pivot_table(index=["cell", "grid_lat", "grid_lon", "period", "month"], columns="pct",
                                       values="value").reset_index()
    r.columns = [c if isinstance(c, str) else f"p{c}" for c in r.columns]
    sop = pd.DataFrame({"month": range(1, 13), "sop_p90": [cfg["sop_appendix1"]["p90"][m] for m in range(1, 13)],
                        "sop_p95": [cfg["sop_appendix1"]["p95"][m] for m in range(1, 13)]})
    r = r.merge(sop, on="month")
    OUT.mkdir(exist_ok=True)
    r.to_csv(OUT / "D1_full_year.csv", index=False)

    # Compact Sept to April table
    w = r.pivot_table(index="month", columns=["cell", "period"], values=["p90", "p95"])
    tab = pd.DataFrame({"Month": [NAMES[m] for m in MONTHS]})
    for p in ("p90", "p95"):
        tab[f"SOP App.1 {p.upper()}"] = [cfg["sop_appendix1"][p][m] for m in MONTHS]
        tab[f"RMMCH 2016-19 {p.upper()}"] = [round(w[(p, "rmmch", "sop_2016_2019")][m], 1) for m in MONTHS]
        tab[f"RMMCH 1991-2020 {p.upper()}"] = [round(w[(p, "rmmch", "wmo_1991_2020")][m], 1) for m in MONTHS]
        tab[f"Soweto 1991-2020 {p.upper()}"] = [round(w[(p, "soweto", "wmo_1991_2020")][m], 1) for m in MONTHS]
    tab.to_csv(OUT / "D1_thresholds.csv", index=False)
    return r, tab


if __name__ == "__main__":
    r, tab = build()
    print(tab.to_string(index=False))
