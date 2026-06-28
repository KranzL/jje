import math

import pytest

from windowstats import (
    BucketGrid,
    RetentionPolicy,
    Sample,
    SlidingWindow,
    bucket_index,
    summarize,
)


def make_window():
    w = SlidingWindow()
    for i in range(10):
        w.append(Sample(ts=float(i), value=float(i * i)))
    return w


def test_append_rejects_out_of_order():
    w = SlidingWindow()
    w.append(Sample(ts=5.0, value=1.0))
    with pytest.raises(ValueError):
        w.append(Sample(ts=4.0, value=1.0))


def test_query_half_open_interior():
    w = make_window()
    got = [s.ts for s in w.query(2.5, 6.5)]
    assert got == [3.0, 4.0, 5.0, 6.0]


def test_query_empty_when_reversed():
    w = make_window()
    with pytest.raises(ValueError):
        w.query(6.0, 2.0)


def test_query_inclusive_contains_both_ends():
    w = make_window()
    got = [s.ts for s in w.query_inclusive(3.0, 6.0)]
    assert got == [3.0, 4.0, 5.0, 6.0]


def test_first_at_or_after():
    w = make_window()
    assert w.first_at_or_after(3.0) == 3
    assert w.first_at_or_after(3.5) == 4
    assert w.first_at_or_after(-1.0) == 0


def test_drop_before():
    w = make_window()
    dropped = w.drop_before(4.0)
    assert dropped == 4
    assert len(w) == 6
    assert w.query(0.0, 100.0)[0].ts == 4.0


def test_bucket_index_boundary_goes_to_later_bucket():
    assert bucket_index(0.0, 0.0, 10.0) == 0
    assert bucket_index(9.999, 0.0, 10.0) == 0
    assert bucket_index(10.0, 0.0, 10.0) == 1


def test_bucket_counts():
    w = SlidingWindow()
    for ts in [0.0, 1.0, 2.0, 10.0, 11.0, 25.0]:
        w.append(Sample(ts=ts, value=1.0))
    grid = BucketGrid(origin=0.0, width=10.0)
    counts = grid.counts(w, 0.0, 30.0)
    assert counts == [3, 2, 1]


def test_summarize_basic():
    samples = [Sample(ts=float(i), value=float(i)) for i in range(101)]
    summ = summarize(samples)
    assert summ.count == 101
    assert summ.minimum == 0.0
    assert summ.maximum == 100.0
    assert summ.median == 50.0
    assert summ.p95 == 95.0


def test_retention_evicts_old():
    w = make_window()
    policy = RetentionPolicy(horizon=5.0)
    dropped = policy.apply(w, now=9.0)
    assert dropped == 4
    assert w.query(0.0, 100.0)[0].ts == 4.0


def test_retention_rejects_nonpositive_horizon():
    with pytest.raises(ValueError):
        RetentionPolicy(horizon=0.0)
