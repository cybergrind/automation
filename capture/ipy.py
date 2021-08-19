import json
from abc import ABC, abstractmethod
from contextlib import suppress
from functools import lru_cache

import cv2
import easyocr
import mss
import numpy as np
from IPython import get_ipython

from fan_tools.python import py_rel_path

from capture import ipy  # autoreload self
from capture.utils import ctx, throttle


i = get_ipython()
iem = i.extension_manager
iem.load_extension('autoreload')
i.magic('%autoreload 2')

sct = mss.mss()
LIFE_POS = False
POS_FILE = py_rel_path('../.old_pos')
FILE_BASE = py_rel_path('../.data')
FILE_BASE.mkdir(exist_ok=True)
CONF_TRESHOLD = 0.7
BUFF_NUMS = {}

for i in range(2, 21):
    BUFF_NUMS[i] = cv2.imread(f'buffs/{i}.png')

DEFAULT_POS = [0, 0, 300, 50]
POSITION = None

CHECK_MON = sct.monitors[0]
F_MON = sct.monitors[1]
STEP = 20
reader = easyocr.Reader(['en'], gpu=True)
IMG = None
DATA = 'default'


def s(img):
    """debug show"""
    cv2.imshow('debug', img)
    cv2.waitKey(60)


def dd():
    """destroy debug"""
    cv2.destroyWindow('debug')


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


# @lru_cache(3)
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
    ctx.gui.hotkey('w')  # convoc
    return 11


@throttle(4.0)
def reaper():
    ctx.gui.hotkey('r')  # reaper
    return 58


@throttle(0.6)
def instant_life_tap():
    ctx.gui.hotkey('g')  # life
    convocation()
    reaper()


@throttle(7.0)
def long_life_tap():
    ctx.gui.hotkey('a')  # life long
    convocation()
    reaper()


@throttle(0.5)
def summon():
    ctx.gui.click(button='right')


def put_text(img, txt, pos=(5, 20)):
    cv2.putText(img, txt, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)


def crop(full, pos, copy=True):
    x0, x1 = pos[0], pos[2]
    y0, y1 = pos[1], pos[3]
    img = full[y0:y1, x0:x1, :]
    if copy:
        return img.copy()
    return img


PHANT = cv2.imread('phant.png')


def get_phantasms(f):
    cropped = crop(f, (0, 0, 700, 125), copy=False)
    # can be: np.where(cv2.matchTemplate(cropped, PHANT, cv2.TM_CCOEFF_NORMED) > 0.77)
    _, conf, _, coord = cv2.minMaxLoc(cv2.matchTemplate(cropped, PHANT, cv2.TM_CCOEFF_NORMED))

    if conf > 0.7:
        x0, y0 = coord
        dy, dx = PHANT.shape[:2]
        return crop(cropped, (x0, y0, x0 + dx, y0 + dy), copy=False)


def phantasms_count(f):
    return find_num((get_phantasms(f)))


SKELS = cv2.imread('skels.png')


def get_skels(f):
    cropped = crop(f, (0, 0, 700, 125), copy=False)
    _, conf, _, coord = cv2.minMaxLoc(cv2.matchTemplate(cropped, SKELS, cv2.TM_CCOEFF_NORMED))

    if conf > 0.7:
        x0, y0 = coord
        dy, dx = SKELS.shape[:2]
        return crop(cropped, (x0, y0, x0 + dx + 19, y0 + dy + 21), copy=False)


def skels_count(f):
    return find_num((get_skels(f)))


def find_num(img):
    candidate = 0
    max_conf = 0
    if img is None:
        return 0
    for i, mask in BUFF_NUMS.items():
        _, conf, _, coord = cv2.minMaxLoc(cv2.matchTemplate(img, mask, cv2.TM_CCOEFF_NORMED))
        if conf > max_conf:
            candidate = i
            max_conf = conf
    if max_conf > 0.7:
        return candidate


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
        s, confidence = data[0][1], data[0][2]
        return s, confidence

    @property
    def rect(self):
        return (self.pos[0], self.pos[1]), (self.pos[2], self.pos[3])


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
    """
    pos: [130, 1083, 264, 1119]
    """

    def __init__(self):
        super().__init__('life')
        self.prev = None
        self.ls = None
        self.prev_err = None
        self.frames = 0
        self.conf = 1.0

    def detect(self, img):
        new_pos = detect_next(img, 'life')
        if new_pos:
            print(f'POS: {new_pos}')
            self.set_pos(new_pos)

    def keep_bw(self, img):
        # return img # 0.891
        hl, hh = 175, 255  # hl 180=.910, 175=.915, 165
        lh = 70  # 70=.896 80=.896
        if img.shape[2] == 3:
            self.mask1 = cv2.inRange(img, (hl, hl, hl), (hh, hh, hh))
            self.mask2 = cv2.inRange(img, (0, 0, 0), (lh, lh, lh))
        else:
            self.mask1 = cv2.inRange(img, (hl, hl, hl, 0), (hh, hh, hh, 255))
            self.mask2 = cv2.inRange(img, (0, 0, 0, 0), (lh, lh, lh, 255))
        self.mask = self.mask1.copy()
        self.mask[self.mask2 > 1] = 255
        out = cv2.GaussianBlur(
            img, (3, 3), cv2.BORDER_DEFAULT
        )  # 1x=.890 3x=0899 5x.883 7x=.90 9x.85
        out[self.mask > 1] = img[self.mask > 1]  # 0.899
        # out = cv2.bitwise_and(img, img, mask=self.mask)  # 0.899
        # out = cv2.GaussianBlur(out, (3, 3), cv2.BORDER_DEFAULT)
        return out

    def frame(self, full):
        self.prev = None

        img = crop(full, self.pos or [0, 0, 150, 150])
        img = self.keep_bw(img)

        self.last_img = img.copy()

        if not self.pos:
            put_text(img, 'wait init')
            return
        data = 'ERR'
        try:
            curr, total = self.get_life(img)
            perc = curr / total
            self.prev = (curr, total)
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
                summon()
                data = f'NP: {curr}/ {perc}'
            else:
                data = f'NP: {curr}'
        except Exception as e:
            err = f'{e=} {self.ls=}'
            if err != self.prev_err:
                print(err, flush=True)
                self.prev_err = err
        put_text(img, data)
        return img

    def get_life(self, img: np.ndarray):
        life_string, conf = self.ocr_one(img)
        self.conf = (self.conf * self.frames + conf) / (self.frames + 1)
        # print(f'{self.conf=} {self.frames=} {conf=}')
        self.frames += 1
        if conf < CONF_TRESHOLD:
            print(f'{life_string=} => {conf=}')
            return
        life_string = life_string.replace(',', '').replace('.', '')

        self.ls = life_string
        if '/' not in life_string:
            return
        curr, total = life_string.split('/')

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
        t = ctx.time()
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
        mana_str, conf = self.ocr_one(img)
        if conf < CONF_TRESHOLD:
            return
        curr, total = mana_str.split('/')
        curr = int(curr.replace(',', ''))
        total = int(total.replace(',', ''))
        t = ctx.time()
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


def video_frames(cap):
    positioned = False
    life = LifeFragment()
    c = 0
    while cap.isOpened():
        c += 1
        ok, frame = cap.read()
        if c < 30:
            continue

        orig = frame.copy()
        if not ok:
            break
        if cv2.waitKey(10) & 0xFF == ord('q'):
            break
        elif cv2.waitKey(10) & 0xFF == ord('d'):
            life.detect(frame)

        life.frame(frame)
        cv2.rectangle(frame, *life.rect, (255, 0, 255), 1)
        put_text(frame, str(life.prev), life.rect[1])

        print(f'L: {life.prev} / {life.frames} / {life.conf}', flush=True)

        if life.prev and (life.prev[1] != 4246):
            cv2.imwrite('bad.png', orig)
            cv2.waitKey(10000)

        cv2.imshow('video', frame)
        if not positioned:
            positioned = True
            m2 = sct.monitors[2]
            cv2.moveWindow('video', m2['left'], m2['top'])
    print(f'Finished: {cap=}')


def play_video(video=py_rel_path('../20210818_13-14-52.mp4').resolve().as_uri()):
    with ctx.mock_gui():
        try:
            cap = cv2.VideoCapture(video)
            video_frames(cap)
        except Exception as e:
            print(f'Exc: {e}')
            raise
        finally:
            cv2.destroyWindow('video')


def capture_loop():
    if not POSITION:
        get_pos()

    life = LifeFragment()
    mana = ManaFragment()

    global LIFE_POS

    try:
        while True:
            pos = tuple(POSITION)
            s = sct.grab(F_MON)
            full = np.array(s)
            img = crop(full, pos)

            img2 = img.copy()

            last = life.frame(full)
            # mana.frame(full)

            if last is not None:
                cv2.imshow('LIFE', last)

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
