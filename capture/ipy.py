import json
import time
from contextlib import suppress

import cv2
import easyocr
import mss
import numpy as np
import pyautogui
from IPython import get_ipython

from fan_tools.python import py_rel_path

from capture import ipy  # autoreload self
from capture import utils
from capture.utils import throttle


i = get_ipython()
iem = i.extension_manager
iem.load_extension('autoreload')
i.magic('%autoreload 2')

sct = mss.mss()
LIFE_POS = False
POS_FILE = py_rel_path('../.old_pos')
DEFAULT_POS = [0, 0, 300, 50]
POSITION = None

CHECK_MON = sct.monitors[0]
STEP = 20
reader = easyocr.Reader(['en'], gpu=True)
IMG = None
DATA = 'default'


def get_pos():
    global POSITION

    if POS_FILE.exists():
        with suppress(Exception):
            POSITION = json.loads(POS_FILE.read_text())
            print(f'READ: {POSITION=}')
            if not POSITION:
                set_pos(POSITION)
    if not POSITION:
        set_pos(DEFAULT_POS)
    print(f'{POSITION=}')


def set_pos(new_pos):
    global POSITION
    POSITION = new_pos
    POS_FILE.write_text(json.dumps(new_pos))


get_pos()


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


def run_ocr(img: np.ndarray):
    global IMG, DATA
    IMG = img
    data = reader.readtext(img)
    print(f'{data}')
    strings = []
    for d in data:
        strings.append(d[1])
    DATA = '|'.join(strings)
    return data


def get_life(img: np.ndarray):
    try:
        data = reader.readtext(img)
        life_string = data[0][1]
        curr, total = life_string.split('/')
        curr = int(curr.replace(',', ''))
        total = int(total.replace(',', ''))
        return curr, total
    except:
        pass


def run_detect():
    global LIFE_POS
    m1 = sct.monitors[1]
    s = np.array(sct.grab(m1))
    texts = run_ocr(s)
    for idx, i in enumerate(texts):
        if 'life' in i[1].lower():
            if len(i[1]) == len('life'):
                LIFE_POS = True
                life_coord = texts[idx + 1][0]
                POSITION[0] = life_coord[0][0]
                POSITION[1] = life_coord[0][1]
                POSITION[2] = life_coord[2][0]
                POSITION[3] = life_coord[2][1]
            print(f'HAVE: {i=}')

            # coord = i[0]
            # x0 = coord[0][0]
            # x1 = coord[]


@throttle(3.0)
def convocation():
    pyautogui.hotkey('w')  # convoc


@throttle(4.0)
def reaper():
    pyautogui.hotkey('r')  # reaper


@throttle(0.6)
def instant_life_tap():
    pyautogui.hotkey('g')  # life
    convocation()
    reaper()


@throttle(7.0)
def long_life_tap():
    pyautogui.hotkey('a')  # life long
    convocation()
    reaper()


def life_processing(img):
    if not LIFE_POS:
        cv2.putText(img, f'D: {DATA}', (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
    else:
        life = get_life(img)

        if life:
            perc = life[0] / life[1]
            if not life[0]:
                data = 'DEAD'
            elif perc < 0.4:
                instant_life_tap()
                data = f'TAP: {str(life[0])}'
            elif perc < 0.7:
                long_life_tap()
                data = f'LTAP: {perc=}'
            else:
                data = f'NP: {str(life[0])}'
            cv2.putText(img, data, (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)


def capture_loop():
    if not POSITION:
        get_pos()

    global LIFE_POS

    try:
        while True:
            pos = tuple(POSITION)
            print(f'{pos=}')
            s = sct.grab(pos)
            img = np.array(s)
            img2 = img.copy()
            life_processing(img)
            cv2.imshow('example', img)

            k = cv2.waitKey(50) & 0xFF

            if k == ord('q'):
                cv2.destroyAllWindows()
                break

            delta = 0

            if ik(k, 'j'):
                delta = (0, STEP, 0, STEP)
            elif ik(k, 'k'):
                delta = (0, -STEP, 0, -STEP)
            elif ik(k, 'h'):
                delta = (-STEP, 0, -STEP, 0)
            elif ik(k, 'l'):
                delta = (STEP, 0, STEP, 0)
            elif ik(k, 'o'):
                run_ocr(img2)
            elif ik(k, 'd'):
                run_detect()
            elif ik(k, 'a'):
                LIFE_POS = True

            if delta:
                LIFE_POS = False
                new_pos = list(map(sum, zip(POSITION, delta)))
                if bound_ok(new_pos):
                    set_pos(new_pos)
    finally:
        cv2.destroyAllWindows()
