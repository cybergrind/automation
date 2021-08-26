from contextlib import suppress

import cv2
import numpy as np

from fan_tools.python import rel_path

from capture.common import crop, detect_text, Handler
from capture.cv import imread, match, put_text
from capture.ocr import CONF_THRESHOLD, OCRArea, read_text
from capture.utils import ctx, dtime, spell, throttle


T_DIR = rel_path('../../templates/poe')


@throttle(3.0)
def convocation():
    return ctx.gui.hotkey('w')  # convoc
    return 11


@throttle(4.0)
def reaper():
    ctx.gui.hotkey('r')  # reaper
    return 58


@throttle(0.2)
def instant_life_tap():
    ctx.gui.hotkey('g')  # life
    convocation()
    reaper()
    return True


@throttle(0.8)
def long_life_tap():
    ctx.gui.hotkey('a')  # life long
    convocation()
    reaper()
    return True


@spell(0.08, 0.35)
def summon():
    ctx.gui.click(button='right')
    return True


@spell(0.08, 0.40)
def dessecrate():
    ctx.gui.hotkey('t')
    return True


@spell(0.08, 0.66)
def offering():
    ctx.gui.hotkey('e')
    return True


class GameHandler(Handler):
    def __init__(self):
        self.life = LifeFragment()
        self.mana = ManaFragment()
        ctx.reset()
        self.d_or_s = True

    def frame(self, full):
        ctx.frame(full)
        ctx.d(f'Frame: {ctx.f_count}')

        if not can_spell(full):
            ctx.d('Cannot use spell')
            return

        last = self.life.frame(full)
        if last is not None:
            cv2.imshow('LIFE', last)

        p_count = phantasms_count(full)
        if p_count < 10:
            if self.d_or_s:
                if dessecrate():
                    self.d_or_s = False
            else:
                if offering():
                    self.d_or_s = True

    def handle_key(self, char):
        pass


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
        new_pos = detect_text(img, 'life')
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
            ctx.d('wait init')
            put_text(img, 'wait init')
            return

        data = 'ERR'
        try:
            curr, total = self.get_life(img)
            perc = curr / total
            self.prev = (curr, total)
            if not curr:
                data = 'DEAD'
            elif perc < 0.49:
                instant_life_tap()
                data = f'TAP: {curr} / {perc=}'
            elif perc < 0.73:
                long_life_tap()
                reaper()
                data = f'LTAP: {perc=}'
            elif perc < 0.99:
                convocation()
                summon()
                data = f'NP: {curr} / {perc=}'
            else:
                data = f'NP: {curr} / {perc=}'
            ctx.d(f'Life: {data}')
        except Exception as e:
            err = f'{e=} {self.ls=}'
            ctx.d(err)
            if err != self.prev_err:
                print(err, flush=True)
                self.prev_err = err
        put_text(img, data)
        return img

    @dtime('life with ocr =>')
    def get_life(self, img: np.ndarray):
        life_string, conf = self.ocr_one(img)
        self.conf = (self.conf * self.frames + conf) / (self.frames + 1)
        # print(f'{self.conf=} {self.frames=} {conf=}')
        self.frames += 1
        if conf < CONF_THRESHOLD:
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
        new_pos = detect_text(img, 'mana')
        if new_pos:
            self.set_pos(new_pos)

    def frame(self, full):
        if not self.pos:
            return
        with suppress(Exception):
            self.process_mana(crop(full, self.pos))

    def process_mana(self, img):
        mana_str, conf = self.ocr_one(img)
        if conf < CONF_THRESHOLD:
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


PHANT = imread(T_DIR / 'phant.png')


def get_phantasms(f):
    cropped = crop(f, (0, 0, 700, 125), copy=False)
    if coord := match(cropped, PHANT):
        x0, y0 = coord
        dy, dx = PHANT.shape[:2]
        return crop(cropped, (x0, y0, x0 + dx, y0 + dy + 23), copy=False)


def phantasms_count(f):
    return find_num((get_phantasms(f)))


SKELS = imread(T_DIR / 'skels.png')


def get_skels(f):
    cropped = crop(f, (0, 0, 700, 125), copy=False)
    if coord := match(cropped, SKELS):
        x0, y0 = coord
        dy, dx = SKELS.shape[:2]
        return crop(cropped, (x0, y0, x0 + dx + 19, y0 + dy + 21), copy=False)


CWALK = imread(T_DIR / 'cwalk.png')


def is_cwalk(f):
    cropped = crop(f, (0, 0, 700, 125), copy=False)
    _, conf, _, coord = cv2.minMaxLoc(cv2.matchTemplate(cropped, CWALK, cv2.TM_CCOEFF_NORMED))

    if conf > 0.7:
        return True


CHAT = imread(T_DIR / 'chat.png')


def is_chat(f):
    cropped = crop(f, [140, 1035, 180, 1075], copy=False)
    if match(cropped, CHAT):
        return True
    return False


CHAT_UP_BTN = imread(T_DIR / 'chat_up_btn.png')


def is_right_ok(f):
    cropped = crop(f, [0, 970, 25, 990], copy=False)
    if match(cropped, CHAT_UP_BTN):
        return True


@dtime('battle_loc => ')
def battle_loc(f):
    """
    1. not hideout
    2. has monster level
    """
    cropped = crop(f, [2200, 50, 2550, 130], copy=False)
    line = ' '.join(read_text(cropped)).lower()
    if 'hideout' in line:
        return False
    if 'monster level' in line:
        return True
    return False


@dtime('can_spell => ')
def can_spell(f):
    """
    1. have chat button: no wp or right side menus
    2. no chat active
    3. no hideout and have monster level (turn off when minimap too) + no right side menus
    """
    if not is_right_ok(f):
        return False
    if is_chat(f):
        return False
    if not battle_loc(f):
        return False
    return True


def skels_count(f):
    return find_num((get_skels(f)))


BUFF_NUMS = {}
for i in range(2, 21):
    BUFF_NUMS[i] = imread(T_DIR / f'buffs/{i}.png')


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
    if max_conf > 0.5:
        return candidate
    return 0
