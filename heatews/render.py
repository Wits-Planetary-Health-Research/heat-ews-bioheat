"""Static status page: today's status, 14-day chart against the threshold, issue time, data source."""
from html import escape
import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import alert as A

COLOURS = {A.WARNING: "#b42318", A.WATCH: "#b54708", A.NO_ALERT: "#3f6212", A.NOT_UPDATED: "#475467"}
HEADLINE = {
    A.WARNING: "Heatwave expected in the next 7 days",
    A.WATCH: "Possible heatwave in 8 to 14 days",
    A.NO_ALERT: "No heatwave expected in the next 14 days",
    A.NOT_UPDATED: "Forecast not updated today",
}
MEANING = {
    A.WARNING: "Start preparing for heatwave visits. Check tomorrow's update before the PI or designee decides on activation.",
    A.WATCH: "No action yet. Keep an eye on the daily update.",
    A.NO_ALERT: "Nothing to do.",
    A.NOT_UPDATED: "Today's forecast could not be loaded. Do not read this as 'no heatwave'. Check the SAWS forecast manually.",
}


def chart_svg(dates, members, thresh, comparison_label="P95", thresh90=None, label90="P90"):
    m = np.asarray(members, dtype=float)
    days = np.arange(1, m.shape[1] + 1)
    fig, ax = plt.subplots(figsize=(5.2, 3.6), dpi=100)
    lo, hi = np.nanpercentile(m, 10, axis=0), np.nanpercentile(m, 90, axis=0)
    ax.fill_between(days, lo, hi, color="#98a2b3", alpha=0.45, lw=0, label="Range of 80% of ensemble members")
    ax.plot(days, np.nanmedian(m, axis=0), color="#101828", lw=2, marker="o", ms=3.5, label="Ensemble median")
    ax.step(days, thresh, where="mid", color="#b42318", lw=1.5, ls="--", label=f"Threshold ({comparison_label})")
    if thresh90 is not None:
        ax.step(days, thresh90, where="mid", color="#b42318", lw=1, ls=":", alpha=0.7, label=f"{label90} (for reference)")
    ax.axvspan(7.5, days[-1] + 0.5, color="#f2f4f7", zorder=0)
    ax.set_xlim(0.5, days[-1] + 0.5)
    ax.set_xticks(days[::2])
    ax.set_xticklabels([pd.Timestamp(d).strftime("%d\n%b") for d in dates][::2], fontsize=10)
    ax.set_ylabel("Max temperature (°C)", fontsize=10)
    ax.tick_params(axis="y", labelsize=10)
    ax.text(4, ax.get_ylim()[1], "Days 1 to 7", ha="center", va="bottom", fontsize=10, color="#475467")
    ax.text((7.5 + days[-1] + 0.5) / 2, ax.get_ylim()[1], "Days 8 to 14", ha="center", va="bottom", fontsize=10,
            color="#475467")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(fontsize=9, frameon=False, loc="upper left", ncol=1, bbox_to_anchor=(0, -0.22))
    fig.tight_layout()
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    svg = buf.getvalue()
    return svg[svg.index("<svg"):]


def _d(x):
    return pd.Timestamp(x).strftime("%a %d %b")


def page(result, issued, source, site_name, dates=None, members=None, thresh=None, last_good=None,
         threshold_label="P95 by month", thresh90=None, current=None, also_pct=90):
    s = result["status"]
    colour = COLOURS[s]
    chart = ""
    rows = ""
    tiles = ""
    if s != A.NOT_UPDATED and members is not None:
        chart = chart_svg(dates, members, thresh, "P95", thresh90, f"P{also_pct}")
        med = result["median"]
        prob = result["member_prob_days"]
        for k, d in enumerate(dates):
            flag = "Heatwave day" if result["hw_median"][k] else ""
            t90 = f"<td>{thresh90[k]:.1f}</td>" if thresh90 is not None else ""
            rows += (f"<tr><td>{k + 1}</td><td>{_d(d)}</td><td>{med[k]:.1f}</td>"
                     f"<td>{thresh[k]:.1f}</td>{t90}<td>{prob[k] * 100:.0f}%</td><td>{flag}</td></tr>")
        if current:
            more = " or longer" if current["runs_past_forecast"] else ""
            now_txt = (f"<b class='yes'>Yes</b>Day {current['day_number']}, likely to last until "
                       f"{_d(current['end'])}{more}")
        else:
            now_txt = "<b>No</b>Not today"
        p7 = round(result["frac_warning_window"] * 100)
        p14 = round(result["frac_watch_window"] * 100)
        tiles = (f"<div class='tiles'><div class='tile'><span>Heatwave now?</span>{now_txt}</div>"
                 f"<div class='tile'><span>Chance of a heatwave, next 7 days</span><b>{p7}%</b></div>"
                 f"<div class='tile'><span>Chance of a heatwave, days 8 to 14</span><b>{p14}%</b></div></div>"
                 "<p class='note'>Chance is the share of the 51 ECMWF forecast versions that show at least "
                 "2 days in a row above the threshold.</p>")
    extra = ""
    if s == A.NOT_UPDATED:
        extra = f"<p class='note'>Reason: {escape(result.get('reason', 'unknown'))}. Last good run: {escape(last_good or 'none')}.</p>"
    table = ""
    if rows:
        h90 = f"<th>P{also_pct} °C</th>" if thresh90 is not None else ""
        table = ("<h2>Day by day</h2><div class='scroll'><table><thead><tr><th>Day</th><th>Date</th>"
                 f"<th>Median Tmax °C</th><th>Threshold (P95) °C</th>{h90}<th>Chance this day is in a heatwave</th>"
                 f"<th></th></tr></thead><tbody>{rows}</tbody></table></div>")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>BioHEAT heat alert</title>
<style>
:root {{ --fg:#101828; --muted:#475467; --line:#d0d5dd; --bg:#ffffff; }}
body {{ font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; color:var(--fg); background:var(--bg);
       margin:0; padding:16px; max-width:760px; margin-inline:auto; line-height:1.45; }}
h1 {{ font-size:1.15rem; margin:0 0 4px; }} h2 {{ font-size:1rem; margin:24px 0 8px; }}
.meta, .note {{ color:var(--muted); font-size:.85rem; }}
.status {{ border-left:6px solid {colour}; padding:12px 14px; background:#f9fafb; margin:16px 0; }}
.status b {{ color:{colour}; font-size:1.35rem; display:block; line-height:1.25; }}
.status small {{ color:{colour}; font-weight:600; text-transform:uppercase; letter-spacing:.04em; font-size:.75rem; }}
.tiles {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); gap:8px; margin:12px 0 4px; }}
.tile {{ border:1px solid var(--line); padding:10px 12px; }}
.tile span {{ display:block; color:var(--muted); font-size:.8rem; }}
.tile b {{ display:block; font-size:1.5rem; }}
.tile b.yes {{ color:#b42318; }}
svg {{ width:100%; height:auto; }}
.scroll {{ overflow-x:auto; }}
table {{ border-collapse:collapse; font-size:.85rem; width:100%; }}
th, td {{ border-bottom:1px solid var(--line); padding:6px 8px; text-align:left; white-space:nowrap; }}
</style></head><body>
<h1>BioHEAT heat alert: {escape(site_name)}</h1>
<div class="meta">Issued {escape(issued)}</div>
<div class="status"><small>{escape(s)}</small><b>{escape(HEADLINE[s])}</b>{escape(MEANING[s])}</div>
{extra}
{tiles}
{chart}
{table}
<h2>How this works</h2>
<p class="note">A heatwave is daily maximum temperature above the monthly threshold ({escape(threshold_label)}) on at least 2
consecutive days. Warning: the ensemble median meets this within days 1 to 7.
Watch: at least half of the ensemble members meet it within days 8 to 14. The forecast is the ECMWF ensemble,
bias-corrected to ERA5. Forecasts beyond about a week are uncertain; the PI or designee decides on activation.</p>
<p class="note">Data: {escape(source)}</p>
</body></html>"""
