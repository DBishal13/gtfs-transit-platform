"""In-memory sliding-window rate limiter, keyed by org_id.

Adequate for a single-instance portfolio deployment — not for horizontal scaling, since
each process instance would track its own independent counters. A Redis-backed
implementation (`INCR` + `EXPIRE`, or a sliding-window sorted set) is the documented
upgrade path if this ever needs to run behind a multi-instance load balancer; not built
here, per service/README.md's explicitly-deferred list.

Note: api_keys.rate_limit_per_min (service/migrations/0002_tenancy.sql) exists in the
schema for future per-key limits but isn't read here yet — every request is currently
limited uniformly per org_id via Settings.rate_limit_default_per_min, regardless of
whether it authenticated via JWT or a specific API key.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from threading import Lock

_WINDOW_SECONDS = 60.0
_lock = Lock()
_request_times: dict[uuid.UUID, deque[float]] = defaultdict(deque)


def check_rate_limit(org_id: uuid.UUID, *, limit_per_min: int, now: float | None = None) -> bool:
    """Returns True if this request is allowed, False if `org_id` has already made
    `limit_per_min` requests in the trailing 60-second window. `now` is injectable for
    tests; defaults to time.monotonic()."""
    current = now if now is not None else time.monotonic()
    cutoff = current - _WINDOW_SECONDS
    with _lock:
        window = _request_times[org_id]
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= limit_per_min:
            return False
        window.append(current)
        return True


def reset_for_tests(org_id: uuid.UUID) -> None:
    """Test-only helper: clears one org's window so tests don't leak state into each other."""
    with _lock:
        _request_times.pop(org_id, None)
