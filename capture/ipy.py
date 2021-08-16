import cv2
import mss
import numpy as np
from IPython import get_ipython

from capture import ipy  # autoreload self
from capture import utils


i = get_ipython()
iem = i.extension_manager
iem.load_extension('autoreload')
i.magic('%autoreload 2')

sct = mss.mss()
POSITION = [0, 0, 1500, 900]
CHECK_MON = sct.monitors[0]


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


def capture_loop():
    global POSITION
    try:
        while True:
            pos = tuple(POSITION)
            print(f'{pos=}')
            s = sct.grab(pos)
            img = np.array(s)
            cv2.imshow('example', img)

            k = cv2.waitKey(100) & 0xFF

            if k == ord('q'):
                cv2.destroyAllWindows()
                break

            delta = 0

            if ik(k, 'j'):
                delta = (0, 50, 0, 50)
            elif ik(k, 'k'):
                delta = (0, -50, 0, -50)
            elif ik(k, 'h'):
                delta = (-50, 0, -50, 0)
            elif ik(k, 'l'):
                delta = (50, 0, 50, 0)

            if delta:
                new_pos = list(map(sum, zip(POSITION, delta)))
                if bound_ok(new_pos):
                    POSITION = new_pos
    finally:
        cv2.destroyAllWindows()
