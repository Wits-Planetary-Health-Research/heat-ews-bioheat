"""Daily run: fetch forecast, bias-correct, compute status, write the page, email on change.

python -m heatews.run            normal run
HEATEWS_TEST=1 python -m heatews.run   send email to test recipients only
"""
from datetime import datetime, timedelta, timezone
import json
import os

import numpy as np
import pandas as pd

from . import alert as A, bias, config, forecast, notify, render, thresholds as T
from .config import ROOT

DOCS = ROOT / "docs"
STATE = DOCS / "status.json"
LOG = DOCS / "runs.csv"
MAPPING = ROOT / "data" / "bias_mapping.json"
PAGE_URL = os.environ.get("HEATEWS_PAGE_URL") or "https://wits-planetary-health-research.github.io/heat-ews-bioheat/"


def sast_now():
    return datetime.now(timezone(timedelta(hours=2)))


def main(cfg=None, fetcher=forecast.fetch, now=None):
    cfg = cfg or config.load()
    now = now or sast_now()
    issued = now.strftime("%a %d %b %Y, %H:%M SAST")
    DOCS.mkdir(exist_ok=True)
    prev = json.loads(STATE.read_text()) if STATE.exists() else {}
    site, fc, a = cfg["site"], cfg["forecast"], cfg["alert"]
    horizon = a["watch_days"][1]
    dates = members = th = None
    source = f"ECMWF IFS ensemble ({fc['model']}) via Open-Meteo; thresholds SOP-BH-13 Appendix 1"
    try:
        dates, raw, meta = fetcher(site["latitude"], site["longitude"], model=fc["model"], days=horizon + 1)
        today = pd.Timestamp(now.date())
        keep = (dates >= today)
        dates, raw = dates[keep][:horizon], raw[:, keep][:, :horizon]
        if MAPPING.exists():
            method = cfg.get("bias", {}).get("method", "mean_shift")
            members = bias.Mapping.load(MAPPING, method).correct_ensemble(raw)
            source += f"; bias-corrected to ERA5 by lead ({method.replace('_', ' ')})"
        else:
            members = raw
            source += "; NOT bias-corrected (mapping file missing)"
        th = T.for_dates(dates, cfg)
        result = A.status(members, th, cfg)
        source += f"; fetched {meta['fetched_utc']} UTC, {meta['members']} members"
    except forecast.FetchError as e:
        result = {"status": A.NOT_UPDATED, "reason": str(e)}

    last_good = prev.get("last_good")
    if result["status"] != A.NOT_UPDATED:
        last_good = issued
    html = render.page(result, issued, source, site["name"], dates, members, th, last_good)
    (DOCS / "index.html").write_text(html)

    test = os.environ.get("HEATEWS_TEST") == "1"
    recipients = notify.recipients(cfg, test)
    email = "not needed"
    if notify.should_send(prev.get("status"), result["status"], cfg["notify"]["mode"]) or test:
        email = notify.send(notify.compose(result, issued, PAGE_URL, site["name"]), recipients)

    state = {"status": result["status"], "issued": issued, "last_good": last_good,
             "reason": result.get("reason", ""), "frac_watch_window": result.get("frac_watch_window"),
             "frac_warning_window": result.get("frac_warning_window")}
    STATE.write_text(json.dumps(state, indent=1))
    row = pd.DataFrame([{**state, "email": email}])
    row.to_csv(LOG, mode="a", header=not LOG.exists(), index=False)
    print(f"{issued}: {result['status']} ({email})")
    return result


if __name__ == "__main__":
    main()
