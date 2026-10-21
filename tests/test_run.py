"""End-to-end run with a fake forecast, including the failed-fetch path (criterion 8)."""
from datetime import datetime, timedelta, timezone
import json

import numpy as np
import pandas as pd
import pytest

from heatews import alert as A, config, forecast, run


@pytest.fixture
def tmp_docs(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "DOCS", tmp_path)
    monkeypatch.setattr(run, "STATE", tmp_path / "status.json")
    monkeypatch.setattr(run, "LOG", tmp_path / "runs.csv")
    monkeypatch.setattr(run, "MAPPING", tmp_path / "none.json")
    return tmp_path


NOW = datetime(2027, 1, 10, 6, 0, tzinfo=timezone(timedelta(hours=2)))


def fake(values, n=51):
    def f(lat, lon, model, days):
        dates = pd.date_range("2027-01-10", periods=days, freq="D")
        v = np.tile(np.asarray(values[:days], dtype=float), (n, 1))
        return dates, v, {"fetched_utc": "2027-01-10T04:00:00+00:00", "members": n}
    return f


def failing(*a, **k):
    raise forecast.FetchError("HTTP 503")


def test_normal_run_writes_page_and_state(tmp_docs):
    r = run.main(fetcher=fake([25] * 15), now=NOW)
    assert r["status"] == A.NO_ALERT
    assert "No alert" in (tmp_docs / "index.html").read_text()
    assert json.loads((tmp_docs / "status.json").read_text())["last_good"].startswith("Sun 10 Jan 2027")


def test_warning_run(tmp_docs):
    v = [25] * 15
    v[2] = v[3] = 34
    assert run.main(fetcher=fake(v), now=NOW)["status"] == A.WARNING


def test_failed_fetch_never_shows_no_alert(tmp_docs):
    run.main(fetcher=fake([25] * 15), now=NOW)
    later = NOW + timedelta(days=1)
    r = run.main(fetcher=failing, now=later)
    assert r["status"] == A.NOT_UPDATED
    html = (tmp_docs / "index.html").read_text()
    assert "System not updated" in html
    assert "<b>No alert</b>" not in html
    assert "Last good run: Sun 10 Jan 2027" in html


def test_incomplete_fetch_reports_not_updated(tmp_docs):
    assert run.main(fetcher=fake([25] * 15, n=10), now=NOW)["status"] == A.NOT_UPDATED


def test_email_only_on_change(tmp_docs, monkeypatch):
    sent = []
    monkeypatch.setattr(run.notify, "send", lambda msg, rec: sent.append(msg["Subject"]) or "sent")
    run.main(fetcher=fake([25] * 15), now=NOW)          # first run: change from nothing
    run.main(fetcher=fake([25] * 15), now=NOW)          # same status: no email
    v = [25] * 15
    v[2] = v[3] = 34
    run.main(fetcher=fake(v), now=NOW)                  # change to Warning
    assert len(sent) == 2 and sent[-1].endswith("Warning")


def test_email_failure_does_not_crash():
    from heatews import notify
    from email.message import EmailMessage
    assert notify.send(EmailMessage(), ["a@b.c"], env={"SMTP_HOST": "smtp.gmail.com"}) == "SMTP credentials not set"
    r = notify.send(EmailMessage(), ["a@b.c"], env={"SMTP_HOST": "127.0.0.1", "SMTP_PORT": "1", "SMTP_USER": "x", "SMTP_PASSWORD": "y"})
    assert r.startswith("email failed")


def test_recipients_from_secret_env():
    from heatews import notify
    cfg = config.load()
    env = {"HEATEWS_RECIPIENTS": "a@x.org, b@x.org;c@x.org", "HEATEWS_TEST_RECIPIENTS": "t@x.org"}
    assert notify.recipients(cfg, False, env) == ["a@x.org", "b@x.org", "c@x.org"]
    assert notify.recipients(cfg, True, env) == ["t@x.org"]
    assert notify.recipients(cfg, False, {}) == []
    lines = {"HEATEWS_RECIPIENTS": "a@x.org\nb@x.org\n c@x.org \n"}
    assert notify.recipients(cfg, False, lines) == ["a@x.org", "b@x.org", "c@x.org"]


def test_email_modes():
    from datetime import date
    from heatews import notify
    d = date(2026, 10, 25)
    assert notify.should_send("Watch", "Watch", "alerts", d, date(2026, 10, 27))      # first week: daily
    assert notify.should_send("No alert", "No alert", "alerts", d, date(2026, 10, 27))
    later = date(2026, 11, 1)
    assert not notify.should_send("No alert", "No alert", "alerts", later, date(2026, 10, 27))
    assert notify.should_send("Watch", "Watch", "alerts", later, date(2026, 10, 27))   # alert day
    assert notify.should_send("Watch", "No alert", "alerts", later, None)              # change
    assert not notify.should_send("Watch", "Watch", "on_change", later, None)


def test_backup_slot_skips_after_good_run(tmp_docs, monkeypatch):
    monkeypatch.setenv("HEATEWS_SCHEDULED", "1")
    sent = []
    monkeypatch.setattr(run.notify, "send", lambda msg, rec: sent.append(1) or "sent")
    run.main(fetcher=fake([25] * 15), now=NOW)                       # first slot runs
    r = run.main(fetcher=fake([25] * 15), now=NOW + timedelta(hours=1))  # backup slot same day
    assert r.get("skipped") and len(sent) == 1


def test_backup_slot_retries_after_failed_fetch(tmp_docs, monkeypatch):
    monkeypatch.setenv("HEATEWS_SCHEDULED", "1")
    run.main(fetcher=failing, now=NOW)
    r = run.main(fetcher=fake([25] * 15), now=NOW + timedelta(hours=1))
    assert not r.get("skipped") and r["status"] == A.NO_ALERT
