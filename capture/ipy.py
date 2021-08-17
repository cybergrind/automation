import json
import time
from abc import ABC, abstractmethod
from contextlib import suppress
from functools import lru_cache

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
FILE_BASE = py_rel_path('../.data')
FILE_BASE.mkdir(exist_ok=True)

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


#@lru_cache(3)
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


@throttle(3.0)
def convocation():
    pyautogui.hotkey('w')  # convoc
    return 11


@throttle(4.0)
def reaper():
    pyautogui.hotkey('r')  # reaper
    return 58


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


@throttle(8.0)
def summon():
    pass


def put_text(img, txt):
    cv2.putText(img, txt, (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)


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


def crop(full, pos):
    x0, x1 = pos[0], pos[2]
    y0, y1 = pos[1], pos[3]
    img = full[y0:y1, x0:x1, :]
    return img


class OCRArea(ABC):
    def __init__(self, name):
        self.f = FILE_BASE / name
        self.pos = None
        self.last_img = None
        with suppress(Exception):
            if self.f.exists():
                self.pos = json.loads(self.f.read_text())

    @abstractmethod
    def detect(self, img):
        raise NotImplementedError

    @abstractmethod
    def frame(self, data):
        raise NotImplementedError

    def set_pos(self, new_pos):
        self.pos = new_pos
        self.f.write_text(json.dumps(new_pos))

    def ocr_one(self, img):
        data = reader.readtext(img)
        str = data[0][1]
        return str


def detect_next(img, txt):
    texts = run_ocr(img)
    for idx, i in enumerate(texts):
        if txt in i[1].lower():
            if len(i[1]) == len(txt):
                life_coord = texts[idx + 1][0]
                x0 = int(life_coord[0][0])
                y0 = int(life_coord[0][1])
                x1 = int(life_coord[2][0])
                y1 = int(life_coord[2][1])
                pos = [x0, y0, x1, y1]
                return pos


class LifeFragment(OCRArea):
    def __init__(self):
        super().__init__('life')
        self.prev = 0
        self.ls = None

    def detect(self, img):
        new_pos = detect_next(img, 'life')
        if new_pos:
            print(f'POS: {new_pos}')
            self.set_pos(new_pos)

    def frame(self, full):
        img = crop(full, self.pos or [0, 0, 150, 150])
        self.last_img = img
        if not self.pos:
            put_text(img, 'wait init')
            return
        data = 'ERR'
        try:
            curr, total = self.get_life(img)
            perc = curr / total
            if not curr:
                data = 'DEAD'
            elif perc < 0.4:
                instant_life_tap()
                data = f'TAP: {curr}'
            elif perc < 0.73:
                long_life_tap()
                reaper()
                data = f'LTAP: {perc}'
            elif perc < 0.99:
                convocation()
                data = f'NP: {curr}/ {perc}'
            else:
                data = f'NP: {curr}'
        except Exception as e:
            print(f'{e=}', flush=True)
            print(f'{e=} {self.ls=}', flush=True)
            pass
        put_text(img, data)

    def get_life(self, img: np.ndarray):
        life_string = self.ocr_one(img).replace(',', '').replace('.', '')
        self.ls = life_string
        if '/' in life_string:
            curr, total = life_string.split('/')
        else:
            curr, total = life_string[:-5], life_string[-4:]
            if len(curr) > 4:
                curr = curr[:4]

        curr = int(curr)
        total = int(total)
        return curr, total


class ManaFragment(OCRArea):
    active_delay = 1.3

    def __init__(self):
        super().__init__('mana')
        self.prev = 0
        self.last_change = 0
        self.active = False

        self.regen = 40  # MANUAL
        self.threshold = 353 - 32  # MANUAL

        self.to_regen = 0
        self.to_regen_t = 0

    def calc_threshold(self):
        threshold = self.threshold
        t = time.time()
        print(f'{self.to_regen=}')
        if self.to_regen:
            d = t - self.to_regen_t
            self.to_regen -= max(0, self.to_regen - self.regen * d)
            threshold -= self.to_regen
        self.to_regen_t = t
        return threshold

    def add_regen(self, val):
        if val:
            self.to_regen += val

    def detect(self, img):
        new_pos = detect_next(img, 'mana')
        if new_pos:
            self.set_pos(new_pos)

    def frame(self, full):
        if not self.pos:
            return
        with suppress(Exception):
            self.process_mana(crop(full, self.pos))

    def process_mana(self, img):
        mana_str = self.ocr_one(img)
        curr, total = mana_str.split('/')
        curr = int(curr.replace(',', ''))
        total = int(total.replace(',', ''))
        t = time.time()
        # print(f'MANA: {curr=} {self.prev=} / {self.last_change=}')

        # if curr != self.prev:
        threshold = self.calc_threshold()

        if curr <= threshold:
            print(f'{curr=} vs {threshold=}')
            self.last_change = t
            self.prev = curr
            self.on_change()
        elif t - self.last_change <= self.active_delay:
            self.on_change()

    def on_change(self):
        self.add_regen(convocation())
        self.add_regen(reaper())


def capture_loop():
    if not POSITION:
        get_pos()

    life = LifeFragment()
    mana = ManaFragment()

    global LIFE_POS

    try:
        while True:
            pos = tuple(POSITION)
            s = sct.grab(CHECK_MON)
            full = np.array(s)
            img = crop(full, pos)

            img2 = img.copy()

            life.frame(full)
            # mana.frame(full)

            if life.last_img is not None:
                cv2.imshow('LIFE', life.last_img)

            k = cv2.waitKey(30) & 0xFF

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
                life.detect(full)
                mana.detect(full)
            elif ik(k, 'a'):
                LIFE_POS = True

            if delta:
                LIFE_POS = False
                new_pos = list(map(sum, zip(POSITION, delta)))
                if bound_ok(new_pos):
                    set_pos(new_pos)
    finally:
        cv2.destroyAllWindows()
