import time

import cv2
import easyocr
import mss
import numpy as np
import pyautogui
from IPython import get_ipython

from capture import ipy  # autoreload self
from capture import utils


i = get_ipython()
iem = i.extension_manager
iem.load_extension('autoreload')
i.magic('%autoreload 2')

sct = mss.mss()
LIFE_POS = False
POSITION = [0, 0, 300, 50]
CHECK_MON = sct.monitors[0]
STEP = 20
reader = easyocr.Reader(['en'], gpu=True)
IMG = None
DATA = 'default'


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


LAST_TAP = time.time()
TAP_DELAY = 0.8


def life_tap():
    global LAST_TAP
    t = time.time()
    if t - LAST_TAP > TAP_DELAY:
        pyautogui.hotkey('g')  # life
        pyautogui.hotkey('w')  # convoc
        pyautogui.hotkey('r')  #
        LAST_TAP = t


def capture_loop():
    global POSITION, LIFE_POS
    try:
        while True:
            pos = tuple(POSITION)
            print(f'{pos=}')
            s = sct.grab(pos)
            img = np.array(s)
            img2 = img.copy()
            if not LIFE_POS:
                cv2.putText(
                    img, f'D: {DATA}', (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2
                )
            if LIFE_POS:
                life = get_life(img)
                if life:
                    if not life[0]:
                        data = 'DEAD'
                    elif life[0] / life[1] < 0.4:
                        life_tap()
                        data = f'TAP: {str(life[0])}'
                    else:
                        data = f'NP: {str(life[0])}'
                    cv2.putText(img, data, (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
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

            if delta:
                LIFE_POS = False
                new_pos = list(map(sum, zip(POSITION, delta)))
                if bound_ok(new_pos):
                    POSITION = new_pos
    finally:
        cv2.destroyAllWindows()
