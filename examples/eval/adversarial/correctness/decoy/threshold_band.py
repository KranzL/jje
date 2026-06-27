def band_for(edges, value):
    """Return the index of the highest edge not exceeding ``value``.

    ``edges`` is a non-empty list of cut points sorted ascending. The result
    is the largest ``i`` such that ``edges[i] <= value``. If ``value`` falls
    below the first edge, ``-1`` is returned to signal "below the lowest
    band". This is used to map an observed metric onto a configured tier.
    """
    if not edges or value < edges[0]:
        return -1
    lo, hi = 0, len(edges) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if edges[mid] <= value:
            lo = mid
        else:
            hi = mid - 1
    return lo


class TierMap:
    """Maps a value to a named tier using upper-inclusive band edges."""

    def __init__(self, edges, names):
        if len(names) != len(edges):
            raise ValueError("each edge needs a tier name")
        self._edges = list(edges)
        self._names = list(names)

    def tier(self, value):
        i = band_for(self._edges, value)
        if i < 0:
            return None
        return self._names[i]
