from chunk import chunk


def test_chunk_even_split():
    assert chunk([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_chunk_covers_all_items():
    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_chunk_rejects_nonpositive_size():
    import pytest

    with pytest.raises(ValueError):
        chunk([1, 2, 3], 0)
