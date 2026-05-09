from collections import deque
from threading import Lock
from time import time
from helpers.environment import RATE_LIMIT_PER_MINUTE

# NOTE: state is per-worker process. With multiple Gunicorn workers the effective
# limit is RATE_LIMIT_PER_MINUTE × workers. Either set --workers 1 (sufficient
# for a single MikroTik device) or divide RATE_LIMIT_PER_MINUTE accordingly.
_lock = Lock()
_timestamps: deque = deque()


def check_rate_limit() -> bool:
    """Return True if the request is within the allowed rate, False if exceeded."""
    now = time()
    with _lock:
        while _timestamps and now - _timestamps[0] > 60:
            _timestamps.popleft()
        if len(_timestamps) >= RATE_LIMIT_PER_MINUTE:
            return False
        _timestamps.append(now)
        return True
