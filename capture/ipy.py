import cv2
import mss
import numpy as np
from IPython import get_ipython

from fan_tools.python import py_rel_path

from capture import ipy  # noqa autoreload self
from capture.cv import put_text
from capture.games.poe import GameHandler
from capture.ocr import run_ocr
from capture.utils import ctx


i = get_ipython()
iem = i.extension_manager
iem.load_extension('autoreload')
i.magic('%autoreload 2')

sct = mss.mss()

CHECK_MON = sct.monitors[0]
F_MON = sct.monitors[1]
STEP = 20
IMG = None
DATA = 'default'


_SHOW = None  # Debug Image


def s(img):
    """debug show"""
    global _SHOW
    cv2.imshow('debug', img)
    cv2.waitKey(60)
    _SHOW = img


def save(name):
    """save debug image"""
    if _SHOW is None:
        return
    return cv2.imwrite(name, _SHOW)


def dd():
    """destroy debug"""
    cv2.destroyWindow('debug')


def ik(key, char):
    return key == ord(char)


def bound_ok(rect):
    x, x1, y, y1 = CHECK_MON['left'], CHECK_MON['width'], CHECK_MON['top'], CHECK_MON['height']
    if x > rect[0] or rect[0] > x1:
        return False
    if x > rect[2] or rect[2] > x1:
        return False
    if y > rect[1] or rect[1] > y1:
        return False
    if y > rect[3] or rect[3] > y1:
        return False
    return True


def video_frames(cap):
    positioned = False
    game = GameHandler()
    life = game.life
    c = 0
    while cap.isOpened():
        c += 1
        ok, frame = cap.read()
        if c < 30:
            continue
        orig = frame.copy()
        k = cv2.waitKey(10)
        if not ok:
            break
        if k & 0xFF == ord('q'):
            break
        elif k & 0xFF == ord('d'):
            life.detect(frame)

        game.frame(frame)
        dbg(ctx.dbg)

        while ctx.c.get('pause_processing'):
            dbg(['Paused...'] + ctx.dbg)
            cv2.waitKey(10)

        if ctx.c.get('kill_processing'):
            ctx.c.pop('kill_processing')
            return

        # if ctx.f_count > 10:
        #     print(ctx.gui_calls, flush=True)
        #     print(f'GUI CALLS^')
        #     return

        # life.frame(frame)
        cv2.rectangle(frame, *life.rect, (255, 0, 255), 1)
        put_text(frame, str(life.prev), life.rect[1])

        # print(f'L: {life.prev} / {life.frames} / {life.conf}', flush=True)

        # if life.prev and (life.prev[1] != 4246):
        #     cv2.imwrite('bad.png', orig)
        #     cv2.waitKey(10000)

        to_show = frame.copy()
        if ctx.gui_calls:
            put_text(to_show, [str(c) for c in ctx.gui_calls], (10, 340))
        cv2.imshow('video', to_show)
        if not positioned:
            positioned = True
            m2 = sct.monitors[2]
            cv2.moveWindow('video', m2['left'], m2['top'])
    print(f'Finished: {cap=}')


def play_video(video=py_rel_path('../20210818_13-14-52.mp4').resolve().as_uri()):
    with ctx.mock_all():
        try:
            cap = cv2.VideoCapture(video)
            video_frames(cap)
        except Exception as e:
            print(f'Exc: {e}')
            raise
        finally:
            cv2.destroyWindow('video')


def pause_processing():
    if ctx.c.get('pause_processing'):
        ctx.c.pop('pause_processing')
        return
    ctx.c['pause_processing'] = True


def kill_processing():
    ctx.c['kill_processing'] = True


def dbg(strings):
    name = 'dbg'
    dbg_img = np.zeros((500, 700, 3), np.uint8)
    put_text(dbg_img, strings, color=(0, 128, 0), size=0.65)
    cv2.imshow(name, dbg_img)
    cv2.waitKey(1)

    x0, y0, _, _ = cv2.getWindowImageRect(name)
    m2 = sct.monitors[2]
    if x0 != -1 and x0 < m2['left']:
        if x0 < m2['left']:
            cv2.moveWindow(name, m2['left'], m2['top'])


def capture_loop():
    game = GameHandler()
    dbg(['Init capture'])

    try:
        while True:
            s = sct.grab(F_MON)
            full = np.array(s)[:, :, :3]
            game.frame(full)
            dbg(ctx.dbg)

            while ctx.c.get('pause_processing'):
                dbg(['Paused...'] + ctx.dbg)
                cv2.waitKey(30)

            if ctx.c.get('kill_processing'):
                ctx.c.pop('kill_processing')
                dbg(['killed...'])
                return

            k = cv2.waitKey(8) & 0xFF

            if k == ord('q'):
                break

            if ik(k, 'o'):
                run_ocr(full)
            else:
                game.handle_key(k)

    finally:
        cv2.destroyWindow('Life')


from system_hotkey import SystemHotkey


hk = SystemHotkey()

kb = ('super', 'shift', 'u')
kb2 = ('super', 'shift', 'y')

hk.register(kb, callback=lambda x: pause_processing(), overwrite=True)
hk.register(kb2, callback=lambda x: kill_processing(), overwrite=True)
