"""Heatwave detection and alert status, following SOP-BH-13.

A heatwave day is Tmax above the threshold for that day (strictly above by default).
A heatwave is `run_length_days` or more consecutive heatwave days.
"""
import numpy as np
import pandas as pd

WARNING, WATCH, NO_ALERT, NOT_UPDATED = "Warning", "Watch", "No alert", "System not updated"


def hot_days(tmax, thresh, comparison="strict"):
    tmax = np.asarray(tmax, dtype=float)
    thresh = np.asarray(thresh, dtype=float)
    hot = tmax > thresh if comparison == "strict" else tmax >= thresh
    return hot & ~np.isnan(tmax)


def heatwave_days(hot, run_length=2):
    """Boolean mask of days that belong to a run of at least `run_length` hot days."""
    hot = np.asarray(hot, dtype=bool)
    out = np.zeros_like(hot)
    i, n = 0, len(hot)
    while i < n:
        if hot[i]:
            j = i
            while j < n and hot[j]:
                j += 1
            if j - i >= run_length:
                out[i:j] = True
            i = j
        else:
            i += 1
    return out


def window_has_heatwave(hw, start, end):
    """True if any heatwave day falls in lead days start..end (1-based, inclusive).

    Detection runs over the full horizon first, so a run that straddles two windows counts in each
    window it touches. A run that is only half inside the forecast horizon cannot be confirmed.
    """
    return bool(np.asarray(hw)[start - 1:end].any())


def status(members, thresh, cfg):
    """Alert status from an ensemble.

    members: 2-D array (n_members, n_days), lead day 1 first, bias-corrected Tmax.
    thresh: 1-D array (n_days) of thresholds for those dates.
    Returns dict with status and supporting numbers.
    """
    a = cfg["alert"]
    members = np.asarray(members, dtype=float)
    valid = ~np.all(np.isnan(members), axis=1)
    members = members[valid]
    n = len(members)
    if n < a["min_members"]:
        return {"status": NOT_UPDATED, "reason": f"only {n} ensemble members"}
    ws, we = a["warning_days"]
    vs, ve = a["watch_days"]
    if members.shape[1] < ve:
        return {"status": NOT_UPDATED, "reason": f"forecast covers {members.shape[1]} days, need {ve}"}

    median = np.nanmedian(members, axis=0)
    hw_median = heatwave_days(hot_days(median, thresh, a["comparison"]), a["run_length_days"])
    hw_members = np.array([heatwave_days(hot_days(m, thresh, a["comparison"]), a["run_length_days"])
                           for m in members])
    frac_watch = float(np.mean([window_has_heatwave(h, vs, ve) for h in hw_members]))
    frac_warn = float(np.mean([window_has_heatwave(h, ws, we) for h in hw_members]))

    if window_has_heatwave(hw_median, ws, we):
        s = WARNING
    elif frac_watch >= a["watch_member_fraction"]:
        s = WATCH
    else:
        s = NO_ALERT
    return {"status": s, "members": n, "median": median, "hw_median": hw_median,
            "member_prob_days": hw_members.mean(axis=0), "frac_warning_window": frac_warn,
            "frac_watch_window": frac_watch}


def current_heatwave(dates, median, thresh, today_idx, cfg):
    """Is a heatwave under way today? Uses recent past days plus the forecast median.

    Returns None, or dict with start, end (last forecast heatwave day), day_number, length_days.
    """
    a = cfg["alert"]
    hw = heatwave_days(hot_days(median, thresh, a["comparison"]), a["run_length_days"])
    if today_idx >= len(hw) or not hw[today_idx]:
        return None
    i = today_idx
    while i > 0 and hw[i - 1]:
        i -= 1
    j = today_idx
    while j + 1 < len(hw) and hw[j + 1]:
        j += 1
    return {"start": dates[i], "end": dates[j], "day_number": today_idx - i + 1, "length_days": j - i + 1,
            "runs_past_forecast": j == len(hw) - 1}
