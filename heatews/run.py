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
    today_str = now.date().isoformat()
    if os.environ.get("HEATEWS_SCHEDULED") == "1" and prev.get("last_good_date") == today_str:
        print(f"Already ran successfully today ({prev.get('last_good')}); backup slot skipped.")
        return {"status": prev.get("status"), "skipped": True}
    site, fc, a = cfg["site"], cfg["forecast"], cfg["alert"]
    horizon = a["watch_days"][1]
    dates = members = th = th90 = current = expected = None
    pct, also = cfg["thresholds"]["percentile"], cfg["thresholds"].get("also_show")
    src = cfg["thresholds"].get("source", "table")
    th_label = (f"P{pct} by month, SOP-BH-13 Appendix 1" if src == "sop"
                else f"P{pct} by month, ERA5 1991-2020 at RMMCH")
    source = f"ECMWF IFS ensemble ({fc['model']}) via Open-Meteo; thresholds {th_label}"
    try:
        dates_all, raw_all, meta = fetcher(site["latitude"], site["longitude"], model=fc["model"],
                                           days=horizon + 1, past_days=2)
        today = pd.Timestamp(now.date())
        past = dates_all < today
        keep = ~past
        dates, raw = dates_all[keep][:horizon], raw_all[:, keep][:, :horizon]
        raw_past, dates_past = raw_all[:, past], dates_all[past]
        method = cfg.get("bias", {}).get("method", "mean_shift")
        if MAPPING.exists():
            mapping = bias.Mapping.load(MAPPING, method)
            members = mapping.correct_ensemble(raw)
            past_c = np.column_stack([mapping.correct(raw_past[:, j], 0) for j in range(raw_past.shape[1])]) \
                if raw_past.shape[1] else raw_past
            source += f"; bias-corrected to ERA5 by lead ({method.replace('_', ' ')})"
        else:
            members, past_c = raw, raw_past
            source += "; NOT bias-corrected (mapping file missing)"
        th = T.for_dates(dates, cfg)
        th90 = T.for_dates(dates, cfg, pct=also) if also else None
        result = A.status(members, th, cfg)
        if result["status"] != A.NOT_UPDATED:
            seq_dates = list(dates_past) + list(dates)
            seq_med = np.concatenate([np.nanmedian(past_c, axis=0) if past_c.shape[1] else np.array([]),
                                      result["median"]])
            current = A.current_heatwave(seq_dates, seq_med, T.for_dates(seq_dates, cfg), len(dates_past), cfg)
            expected = A.expected_heatwave(dates, result, cfg, current)
        source += f"; fetched {meta['fetched_utc']} UTC, {meta['members']} members"
    except forecast.FetchError as e:
        result = {"status": A.NOT_UPDATED, "reason": str(e)}

    last_good = prev.get("last_good")
    if result["status"] != A.NOT_UPDATED:
        last_good = issued
    html = render.page(result, issued, source, site["name"], dates, members, th, last_good,
                       threshold_label=th_label, thresh90=th90, current=current, also_pct=also, cfg=cfg,
                       expected=expected, pct=pct)
    (DOCS / "index.html").write_text(html)

    test = os.environ.get("HEATEWS_TEST") == "1"
    recipients = notify.recipients(cfg, test)
    email = "not needed"
    du = cfg["notify"].get("daily_until")
    du = pd.Timestamp(du).date() if du else None
    if notify.should_send(prev.get("status"), result["status"], cfg["notify"]["mode"], now.date(), du) or test:
        email = notify.send(notify.compose(result, issued, PAGE_URL, site["name"], current, expected, cfg), recipients)

    last_good_date = prev.get("last_good_date")
    if result["status"] != A.NOT_UPDATED:
        last_good_date = today_str
    state = {"status": result["status"], "issued": issued, "last_good": last_good, "last_good_date": last_good_date,
             "reason": result.get("reason", ""), "frac_watch_window": result.get("frac_watch_window"),
             "frac_warning_window": result.get("frac_warning_window"),
             "heatwave_now": bool(current),
             "heatwave_start": expected["start"].date().isoformat() if expected else None,
             "heatwave_end": expected["end"].date().isoformat() if expected else None,
             "visit_end": expected["visit_end"].date().isoformat() if expected else None}
    STATE.write_text(json.dumps(state, indent=1))
    row = pd.DataFrame([{**state, "email": email, "test_run": test, "recipient_count": len(recipients)}])
    # Rewrite the whole log so new columns never misalign older rows
    if LOG.exists():
        try:
            old_log = pd.read_csv(LOG, on_bad_lines="skip")
        except Exception:
            old_log = pd.DataFrame()
        row = pd.concat([old_log, row], ignore_index=True)
    row.to_csv(LOG, index=False)
    print(f"{issued}: {result['status']} ({email})")
    return result


if __name__ == "__main__":
    main()
