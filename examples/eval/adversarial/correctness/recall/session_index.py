from bisect import insort


class SessionIndex:
    """In-memory index of issued sessions, ordered by issue time.

    Retention contract: a session is considered expired once its age has
    reached the configured horizon. Age is measured as ``now - issued_at``.
    A session is active while its age is strictly less than ``horizon`` and
    expired once its age is at least ``horizon``.

    The index keeps issue times sorted so that eviction and active-set
    queries can locate the live/expired split in logarithmic time rather
    than scanning the whole table on every tick.
    """

    def __init__(self, horizon):
        if horizon <= 0:
            raise ValueError("horizon must be positive")
        self._horizon = horizon
        self._stamps = []
        self._ids = []

    def record(self, session_id, issued_at):
        pos = self._locate(issued_at)
        self._stamps.insert(pos, issued_at)
        self._ids.insert(pos, session_id)

    def _locate(self, issued_at):
        lo, hi = 0, len(self._stamps)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._stamps[mid] <= issued_at:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def _split(self, now):
        cutoff = now - self._horizon
        lo, hi = 0, len(self._stamps)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._stamps[mid] < cutoff:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def evict(self, now):
        idx = self._split(now)
        expired = self._ids[:idx]
        self._stamps = self._stamps[idx:]
        self._ids = self._ids[idx:]
        return expired

    def active(self, now):
        return list(self._ids[self._split(now):])

    def __len__(self):
        return len(self._ids)
