"""Email on status change. SMTP settings come from environment variables (GitHub Actions secrets):
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM. Nothing is stored in the repo.

Recipients: the HEATEWS_RECIPIENTS secret (comma-separated), or HEATEWS_TEST_RECIPIENTS when HEATEWS_TEST=1.
Addresses are kept out of config.yaml because the repo is public. Config lists are a fallback.
"""
from email.message import EmailMessage
import os
import re
import smtplib

from . import alert as A


def recipients(cfg, test=False, env=os.environ):
    key = "HEATEWS_TEST_RECIPIENTS" if test else "HEATEWS_RECIPIENTS"
    raw = env.get(key, "")
    # Accept commas, semicolons, spaces or new lines between addresses
    lst = [a.strip() for a in re.split(r"[,;\s]+", raw) if "@" in a]
    return lst or list(cfg["notify"]["test_recipients" if test else "recipients"] or [])


def should_send(prev, now, mode="on_change", today=None, daily_until=None):
    """mode: on_change (only when the status changes), alerts (on change, and every day while there is a
    Watch or Warning), daily_digest (every day). daily_until (a date) forces a daily email up to and
    including that day, whatever the mode."""
    if daily_until is not None and today is not None and today <= daily_until:
        return True
    if mode == "daily_digest":
        return True
    if mode == "alerts" and now in (A.WARNING, A.WATCH):
        return True
    return prev != now


def compose(result, issued, page_url, site, current=None):
    from .render import HEADLINE, MEANING
    import pandas as pd
    s = result["status"]
    msg = EmailMessage()
    msg["Subject"] = f"BioHEAT heat alert ({site}): {HEADLINE[s]}"
    lines = [HEADLINE[s] + ".", MEANING[s], ""]
    if s != A.NOT_UPDATED:
        if current:
            more = " or longer" if current.get("runs_past_forecast") else ""
            lines.append(f"Heatwave now: yes, day {current['day_number']}, likely to last until "
                         f"{pd.Timestamp(current['end']).strftime('%a %d %b')}{more}.")
        else:
            lines.append("Heatwave now: no.")
        lines.append(f"Chance of a heatwave in the next 7 days: {round(result['frac_warning_window'] * 100)}%.")
        lines.append(f"Chance of a heatwave in days 8 to 14: {round(result['frac_watch_window'] * 100)}%.")
        lines.append("")
    lines += [f"Issued {issued}.", f"Full forecast: {page_url}"]
    msg.set_content("\n".join(lines))
    return msg


def send(msg, recipients, env=os.environ):
    if not recipients:
        return "no recipients configured"
    host = env.get("SMTP_HOST")
    if not host:
        return "SMTP not configured"
    if not env.get("SMTP_USER") or not env.get("SMTP_PASSWORD"):
        return "SMTP credentials not set"
    msg["From"] = env.get("SMTP_FROM") or env["SMTP_USER"]
    msg["To"] = ", ".join(recipients)
    try:
        with smtplib.SMTP(host, int(env.get("SMTP_PORT") or 587), timeout=60) as s:
            s.starttls()
            s.login(env["SMTP_USER"], env["SMTP_PASSWORD"])
            s.send_message(msg)
    except (smtplib.SMTPException, OSError) as e:
        # A mail failure must never stop the page from updating
        return f"email failed: {type(e).__name__}: {e}"
    return f"sent to {len(recipients)}"
