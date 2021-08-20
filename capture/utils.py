import time
from collections import deque
from contextlib import contextmanager
from functools import wraps
from unittest import mock

import pyautogui

from fan_tools.unix import succ

from capture.context import _ctx_inner


def throttle(delay, gui=True):
    """
    call decorated function not more often than a delay
    """
    LAST_ACTION = 0

    def _inner(func):
        @wraps(func)
        def rets(*args, t=None, **kwargs):
            nonlocal LAST_ACTION
            if t is None:
                t = ctx.time()
            # print(f'Got time: {t} / {t-LAST_ACTION}')
            if gui and not ctx.can_click:
                return False

            if t - LAST_ACTION >= delay:
                ret = func(*args, **kwargs)
                if ret:
                    LAST_ACTION = t
                return ret

        return rets

    return _inner


_NEXT_CAST = 0


def spell(cooldown=0.1, cast_time=0, gui=True):
    def _inner(func):
        wfunc = throttle(cooldown)(func)

        @wraps(func)
        def cast(*args, **kwargs):
            global _NEXT_CAST
            t = ctx.time()
            # print(f'{_NEXT_CAST=} vs {t=} / {func}')

            if t < _NEXT_CAST:
                return False

            if gui and not ctx.can_click:
                return False

            ret = wfunc(*args, t=t, **kwargs)
            if ret:
                _NEXT_CAST = t + cast_time
            return ret

        return cast

    return _inner


class Context(dict):
    def __init__(self):
        self.inner = _ctx_inner
        self.frame_time = False
        self.reset()

    def __getitem__(self, name):
        return self.c.__getitem__(name)

    def __setitem__(self, name, value):
        return self.c.__setitem__(name, value)

    def reset(self):
        global _NEXT_CAST
        _NEXT_CAST = 0
        self.c.update({'gui_calls': deque(maxlen=15), 'f_count': 0, 'f_img': None})
        self.win_delay = 0.4
        self.last_win = ''
        self.last_win_call = 0

    def frame(self, img, delta=1):
        self.c['f_count'] += 1
        self.c['f_img'] = img

    @property
    def c(self):
        return self.inner.get()

    @property
    def can_click(self):
        if isinstance(self.gui, mock.MagicMock):
            return True
        t = ctx.time()
        if t - self.last_win_call >= self.win_delay or not self.last_win:
            wname = succ('xdotool getwindowfocus getwindowname')[1][0]
            self.last_win = wname
        ck = self.last_win in ['Path of Exile']
        # print(f'Can click: {ck} => {self.last_win}')
        return ck

    @property
    def gui(self):
        return self.c.get('gui', pyautogui)

    def add_hotkey(self, *args):
        self.c.get('gui_calls', {}).append(f'hotkey: {args} <= {ctx.time()}')

    @property
    def gui_calls(self):
        return self.c.get('gui_calls')

    @contextmanager
    def mock_gui(self):
        gui_mock = mock.MagicMock()
        hk_mock = mock.MagicMock(side_effect=self.add_hotkey)
        gui_mock.attach_mock(hk_mock, 'hotkey')
        self.c['gui'] = gui_mock
        yield
        del self.c['gui']

    @contextmanager
    def mock_time(self, fps=60):
        self.c['frame_time'] = fps
        print(f'Mock time: {fps} / {self.c}')
        yield
        print('Unmock time')
        self.c['frame_time'] = False

    @contextmanager
    def mock_all(self, fps=60):
        with self.mock_gui(), self.mock_time(fps):
            yield

    def time(self):
        ft = self.c.get('frame_time')
        c = self.c.copy()
        c.pop('f_img')

        # print(f'T: {ft} / {c}')

        if ft:
            return 1 / ft * self.c['f_count']

        if 'time' in self.c:
            return self.c['time']
        return time.time()


ctx = Context()
