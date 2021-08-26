import sys
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

import pyautogui

from fan_tools.unix import succ


def throttle(delay):
    """
    call decorated function not more often than a delay
    """

    def _inner(func):
        f_name = f'tt_{func.__name__}'

        @wraps(func)
        def rets(*args, t=None, **kwargs):
            last_action = ctx.floats(f_name)
            if t is None:
                t = ctx.time()
            # print(f'Got time: {t} / {t-LAST_ACTION}')
            if t - last_action >= delay:
                ret = func(*args, **kwargs)
                if ret:
                    ctx.set_float(f_name, t)
                return ret

        return rets

    return _inner


def spell(cooldown=0.1, cast_time=0):
    f_name = 'next_cast'

    def _inner(func):
        wfunc = throttle(cooldown)(func)

        @wraps(func)
        def cast(*args, **kwargs):
            next_cast = ctx.floats(f_name)
            t = ctx.time()

            if t < next_cast:
                return False

            ret = wfunc(*args, t=t, **kwargs)
            if ret:
                ctx.set_float(f_name, t + cast_time)
            return ret

        return cast

    return _inner


class GuiWrapper:
    def __init__(self):
        self.mocked = False
        self.reset()

    def hotkey(self, *args, **kwargs):
        if self.mocked:
            self.gui_calls.append(['hotkey', args, kwargs, ctx.time()])
            return True
        if not self.can_click:
            ctx.d('cannot click')
            return False
        self.gui_calls.append(['hotkey', args, kwargs, ctx.time()])
        pyautogui.hotkey(*args, **kwargs)
        return True

    def click(self, *args, **kwargs):
        if self.mocked:
            self.gui_calls.append(['click', args, kwargs, ctx.time()])
            return True
        if not self.can_click:
            return False
        self.gui_calls.append(['click', args, kwargs, ctx.time()])
        pyautogui.click(*args, **kwargs)
        return True

    def reset(self):
        self.gui_calls = deque(maxlen=15)
        self.win_delay = 0.4
        self.last_win = ''
        self.last_win_call = 0

    @throttle(0.4)
    def get_wname(self):
        return succ('xdotool getwindowfocus getwindowname')[1][0]

    @property
    def can_click(self):
        if self.mocked:
            # print('CC: true / mocked')
            return True
        self.last_win = self.get_wname() or self.last_win
        ck = self.last_win in ['Path of Exile', 'WOW - Wine desktop']
        print(f'Can click: {ck} => {self.last_win}')
        return ck

    @contextmanager
    def mock(self):
        self.mocked = True
        yield
        self.reset()
        self.mocked = False


class Context(dict):
    def __init__(self):
        if not hasattr(sys, '_ctx_inner'):  # survive ipython's autoreload
            sys._ctx_inner = ContextVar('ctx', default={'gui': GuiWrapper(), 'frame_time': None})
        self.inner = sys._ctx_inner
        self.reset()

    def __getitem__(self, name):
        return self.c.__getitem__(name)

    def __setitem__(self, name, value):
        return self.c.__setitem__(name, value)

    def reset(self):
        global _NEXT_CAST
        _NEXT_CAST = 0
        self.c.update(
            {'f_count': 0, 'f_img': None, 'f_debug': None, 'f': defaultdict(float), 'debug': []}
        )

    def frame(self, img, delta=1):
        self.c['f_count'] += 1
        self.c['f_img'] = img
        self.c['f_debug'] = img.copy()  # debug frame, draw here
        self.c['debug'] = []

    def d(self, msg):
        self.c['debug'].append(msg)

    @property
    def df(self):
        return self.c['f_debug']

    @property
    def dbg(self):
        return self.c['debug']

    @property
    def f_count(self):
        return self.c['f_count']

    def floats(self, name):
        return self.c['f'][name]

    def set_float(self, name, value):
        self.c['f'][name] = value

    @property
    def c(self):
        return self.inner.get()

    @property
    def can_click(self):
        return self.gui.can_click

    @property
    def gui(self):
        return self.c['gui']

    def add_hotkey(self, *args):
        self.c.get('gui_calls', {}).append(f'hotkey: {args} <= {ctx.time()}')

    @property
    def gui_calls(self):
        return self.gui.gui_calls

    @contextmanager
    def mock_gui(self):
        with self.gui.mock():
            yield

    @property
    def c_dbg(self):
        c_copy = self.c.copy()
        c_copy.pop('f_img')
        c_copy.pop('f_debug')
        return c_copy

    @contextmanager
    def mock_time(self, fps=60):
        self.c['frame_time'] = fps
        c = self.c_dbg

        print(f'Mock time: {fps} / {c} => {id(self.c)}')
        yield
        print('Unmock time')
        self.c['frame_time'] = False

    @contextmanager
    def mock_all(self, fps=60):
        with self.mock_gui(), self.mock_time(fps):
            yield

    def time(self):
        ft = self.c.get('frame_time')
        c = self.c_dbg

        # print(f'T: {ft} / {c}  => {id(self.c)}')

        if ft:
            return 1 / ft * self.c['f_count']

        if 'time' in self.c:
            return self.c['time']
        return time.time()


ctx = Context()


def dtime(debug_msg=''):
    """decorator that measures function time and put into context"""

    def _inner(func):
        @wraps(func)
        def ret(*args, **kwargs):
            t = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                ctx.d(f'{debug_msg} time: {time.time() - t:.3f}')

        return ret

    return _inner
