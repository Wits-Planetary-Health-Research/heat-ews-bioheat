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
