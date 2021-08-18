import time
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from unittest import mock

import pyautogui


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
                ret = func(*args, **kwargs)
                LAST_ACTION = t
                return ret

        return rets

    return _inner


class Context(dict):
    def __init__(self):
        self.inner = ContextVar('ctx', default={})

    def __getitem__(self, name):
        return self.c.__getitem__(name)

    def __setitem__(self, name, value):
        return self.c.__setitem__(name, value)

    @property
    def c(self):
        return self.inner.get()

    @property
    def gui(self):
        return self.c.get('gui', pyautogui)

    @contextmanager
    def mock_gui(self):
        self.c['gui'] = mock.MagicMock()
        yield
        del self.c['gui']

    def time(self):
        if 'time' in self.c:
            return self.c['time']
        return time.time()


ctx = Context()
