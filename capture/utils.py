import time
from functools import wraps


def throttle(delay):
    """
    call decorated function not more often than a delay
    """
    LAST_ACTION = 0

    def _inner(func):
        @wraps(func)
        def rets(*args, **kwargs):
            nonlocal LAST_ACTION
            t = time.time()
            if t - LAST_ACTION >= delay:
                func(*args, **kwargs)
                LAST_ACTION = t

        return rets

    return _inner
