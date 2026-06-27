from threshold_band import band_for, TierMap


def test_below_lowest_edge():
    assert band_for([10, 20, 30], 5) == -1


def test_exact_edge_lands_on_that_band():
    assert band_for([10, 20, 30], 20) == 1


def test_between_edges_takes_lower():
    assert band_for([10, 20, 30], 27) == 1


def test_value_at_first_edge():
    assert band_for([10, 20, 30], 10) == 0


def test_value_above_last_edge():
    assert band_for([10, 20, 30], 99) == 2


def test_single_edge():
    assert band_for([10], 10) == 0
    assert band_for([10], 9) == -1
    assert band_for([10], 11) == 0


def test_tier_names():
    tm = TierMap([0, 100, 1000], ["bronze", "silver", "gold"])
    assert tm.tier(-5) is None
    assert tm.tier(0) == "bronze"
    assert tm.tier(100) == "silver"
    assert tm.tier(500) == "silver"
    assert tm.tier(1000) == "gold"
