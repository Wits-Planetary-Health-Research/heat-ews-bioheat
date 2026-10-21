import numpy as np
import pytest

from heatews import alert as A
from heatews.config import load

CFG = load()
JAN = 32.6  # SOP-BH-13 January P95


def hw(temps, thresh=JAN, comparison="strict", run=2):
    return list(A.heatwave_days(A.hot_days(temps, [thresh] * len(temps), comparison), run))


def test_sop_example_1_is_heatwave():
    # SOP-BH-13 example: 6-11 Jan 31.9, 32.2, 33.1, 32.7, 32.6, 31.5 -> heatwave (8th and 9th)
    assert hw([31.9, 32.2, 33.1, 32.7, 32.6, 31.5]) == [False, False, True, True, False, False]


def test_sop_example_2_not_heatwave():
    # SOP-BH-13 example: only 8 Jan above. The SOP marks 6 Jan (32.9) as not above, which is a typo
    # in the SOP; at 32.9 it is above 32.6 but it is isolated, so the conclusion still holds.
    assert not any(hw([32.9, 32.1, 33.1, 32.2, 32.6, 31.5]))


def test_exactly_at_threshold_is_not_hot_when_strict():
    assert not A.hot_days([32.6], [32.6], "strict")[0]
    assert A.hot_days([32.6], [32.6], "inclusive")[0]


def test_single_hot_day_not_heatwave():
    assert not any(hw([30, 33, 30]))


def test_exactly_two_days_is_heatwave():
    assert hw([30, 33, 33, 30]) == [False, True, True, False]


def test_run_length_configurable():
    assert not any(hw([30, 33, 33, 30], run=3))
    assert all(hw([33, 33, 33], run=3))


def test_month_boundary_uses_each_days_threshold():
    # 31 Jan (P95 32.6) then 1 Feb (P95 29.8): 32.0 and 30.0 -> Jan day not hot, Feb day hot -> no heatwave
    t = A.hot_days([32.0, 30.0], [32.6, 29.8])
    assert list(t) == [False, True]
    assert not A.heatwave_days(t, 2).any()
    # 33.0 on 31 Jan and 30.0 on 1 Feb are both above their own month's threshold -> heatwave
    t = A.hot_days([33.0, 30.0], [32.6, 29.8])
    assert A.heatwave_days(t, 2).all()


def _ens(day_values, n=50, noise=0.0, seed=0):
    rng = np.random.default_rng(seed)
    base = np.array(day_values, dtype=float)
    return base + rng.normal(0, noise, size=(n, len(base))) if noise else np.tile(base, (n, 1))


def test_straddle_day7_day8_counts_as_warning():
    temps = [25] * 14
    temps[6], temps[7] = 34, 34  # lead days 7 and 8
    r = A.status(_ens(temps), [JAN] * 14, CFG)
    assert r["status"] == A.WARNING


def test_watch_from_members_in_days_8_14():
    temps = [25] * 14
    temps[9], temps[10] = 34, 34
    r = A.status(_ens(temps), [JAN] * 14, CFG)
    assert r["status"] == A.WARNING or r["status"] == A.WATCH
    # median is hot on days 10-11 which is outside the warning window -> Watch
    assert r["status"] == A.WATCH


def test_watch_needs_member_fraction():
    temps = np.full((50, 14), 25.0)
    temps[:20, 9:11] = 34  # 40% of members
    assert A.status(temps, [JAN] * 14, CFG)["status"] == A.NO_ALERT
    temps[:26, 9:11] = 34  # 52%
    assert A.status(temps, [JAN] * 14, CFG)["status"] == A.WATCH


def test_no_alert_when_cool():
    assert A.status(_ens([25] * 14), [JAN] * 14, CFG)["status"] == A.NO_ALERT


def test_missing_members_reports_not_updated():
    e = _ens([25] * 14)
    e[15:] = np.nan  # only 15 valid members
    r = A.status(e, [JAN] * 14, CFG)
    assert r["status"] == A.NOT_UPDATED


def test_some_missing_members_still_runs():
    e = _ens([25] * 14, n=51)
    e[:5] = np.nan
    assert A.status(e, [JAN] * 14, CFG)["status"] == A.NO_ALERT


def test_short_horizon_reports_not_updated():
    assert A.status(_ens([25] * 10), [JAN] * 10, CFG)["status"] == A.NOT_UPDATED


def test_bias_methods():
    from heatews import bias
    t = {k: {"fq": [20.0, 30.0], "oq": [21.0, 29.0], "mean_shift": 1.2, "n": 10} for k in range(8)}
    ms = bias.Mapping(t)
    assert ms.correct([33.0], 0)[0] == pytest.approx(34.2)
    assert ms.correct([33.0], 12)[0] == pytest.approx(34.2)  # beyond lead 7 reuses lead 7
    qm = bias.Mapping(t, "quantile_mapping")
    assert qm.correct([25.0], 0)[0] == pytest.approx(25.0)
    assert qm.correct([32.0], 0)[0] == pytest.approx(31.0)  # above training range: constant top shift


def test_current_heatwave_day_and_end():
    d = list(range(10))
    med = [25, 34, 34, 34, 34, 25, 25, 25, 25, 25]
    c = A.current_heatwave(d, med, [JAN] * 10, 2, CFG)
    assert c["day_number"] == 2 and c["end"] == 4 and c["length_days"] == 4
    assert A.current_heatwave(d, med, [JAN] * 10, 6, CFG) is None
    assert A.current_heatwave(d, [25] + [34] * 9, [JAN] * 10, 3, CFG)["runs_past_forecast"]
