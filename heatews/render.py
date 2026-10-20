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
MEANING = {
    A.WARNING: "A heatwave (SOP-BH-13 definition) is forecast in the next 7 days. Prepare to activate heatwave visits.",
    A.WATCH: "A heatwave is possible in days 8 to 14. Check again daily; no activation yet.",
    A.NO_ALERT: "No heatwave forecast in the next 14 days.",
    A.NOT_UPDATED: "Today's forecast could not be loaded. Do not read this as 'no heatwave'. Check the SAWS forecast manually.",
}


def chart_svg(dates, members, thresh, comparison_label="P95"):
    m = np.asarray(members, dtype=float)
    days = np.arange(1, m.shape[1] + 1)
    fig, ax = plt.subplots(figsize=(5.2, 3.6), dpi=100)
    lo, hi = np.nanpercentile(m, 10, axis=0), np.nanpercentile(m, 90, axis=0)
    ax.fill_between(days, lo, hi, color="#98a2b3", alpha=0.45, lw=0, label="Range of 80% of ensemble members")
    ax.plot(days, np.nanmedian(m, axis=0), color="#101828", lw=2, marker="o", ms=3.5, label="Ensemble median")
    ax.step(days, thresh, where="mid", color="#b42318", lw=1.5, ls="--", label=f"Threshold ({comparison_label})")
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


def page(result, issued, source, site_name, dates=None, members=None, thresh=None, last_good=None,
         threshold_label="P95 by month (SOP-BH-13 Appendix 1)"):
    s = result["status"]
    colour = COLOURS[s]
    chart = ""
    rows = ""
    if s != A.NOT_UPDATED and members is not None:
        chart = chart_svg(dates, members, thresh)
        med = result["median"]
        prob = result["member_prob_days"]
        for k, d in enumerate(dates):
            flag = "Heatwave day" if result["hw_median"][k] else ""
            rows += (f"<tr><td>{k + 1}</td><td>{pd.Timestamp(d).strftime('%a %d %b')}</td><td>{med[k]:.1f}</td>"
                     f"<td>{thresh[k]:.1f}</td><td>{prob[k] * 100:.0f}%</td><td>{flag}</td></tr>")
    extra = ""
    if s == A.NOT_UPDATED:
        extra = f"<p class='note'>Reason: {escape(result.get('reason', 'unknown'))}. Last good run: {escape(last_good or 'none')}.</p>"
    table = ""
    if rows:
        table = ("<h2>Day by day</h2><div class='scroll'><table><thead><tr><th>Day</th><th>Date</th>"
                 "<th>Median Tmax °C</th><th>Threshold °C</th><th>Members in a heatwave</th><th></th></tr></thead>"
                 f"<tbody>{rows}</tbody></table></div>")
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
.status b {{ color:{colour}; font-size:1.4rem; display:block; }}
svg {{ width:100%; height:auto; }}
.scroll {{ overflow-x:auto; }}
table {{ border-collapse:collapse; font-size:.85rem; width:100%; }}
th, td {{ border-bottom:1px solid var(--line); padding:6px 8px; text-align:left; white-space:nowrap; }}
</style></head><body>
<h1>BioHEAT heat alert: {escape(site_name)}</h1>
<div class="meta">Issued {escape(issued)}</div>
<div class="status"><b>{escape(s)}</b>{escape(MEANING[s])}</div>
{extra}
{chart}
{table}
<h2>How this works</h2>
<p class="note">A heatwave is daily maximum temperature above the monthly threshold ({escape(threshold_label)}) on at least 2
consecutive days, as defined in SOP-BH-13. Warning: the ensemble median meets this within days 1 to 7.
Watch: at least half of the ensemble members meet it within days 8 to 14. The forecast is the ECMWF ensemble,
bias-corrected to ERA5. Forecasts beyond about a week are uncertain; the PI or designee decides on activation.</p>
<p class="note">Data: {escape(source)}</p>
</body></html>"""
