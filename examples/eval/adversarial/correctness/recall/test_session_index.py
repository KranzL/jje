import pytest

from session_index import SessionIndex


def build(horizon, items):
    idx = SessionIndex(horizon)
    for sid, ts in items:
        idx.record(sid, ts)
    return idx


def test_records_keep_issue_order():
    idx = build(50, [("a", 100), ("c", 140), ("b", 110)])
    assert idx.active(120) == ["a", "b", "c"]


def test_active_excludes_well_aged_sessions():
    idx = build(30, [("a", 100), ("b", 110), ("c", 145)])
    assert idx.active(132) == ["b", "c"]


def test_active_keeps_everything_when_fresh():
    idx = build(30, [("a", 100), ("b", 110), ("c", 120)])
    assert idx.active(125) == ["a", "b", "c"]


def test_evict_returns_and_drops_expired():
    idx = build(30, [("a", 100), ("b", 118), ("c", 142)])
    assert idx.evict(135) == ["a"]
    assert idx.active(135) == ["b", "c"]
    assert len(idx) == 2


def test_evict_on_empty_is_noop():
    idx = build(30, [])
    assert idx.evict(1000) == []
    assert idx.active(1000) == []


def test_horizon_must_be_positive():
    with pytest.raises(ValueError):
        SessionIndex(0)


def test_all_expired_when_far_in_future():
    idx = build(30, [("a", 100), ("b", 118), ("c", 142)])
    assert idx.evict(10_000) == ["a", "b", "c"]
    assert len(idx) == 0
