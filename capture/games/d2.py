import enum
from contextlib import suppress
from unittest import mock

import cv2
import numpy as np

from fan_tools.python import rel_path

from capture.common import crop, detect_text, Handler
from capture.cv import imread, match, put_text
from capture.ocr import CONF_THRESHOLD, OCRArea, read_text
from capture.utils import ctx, dtime, spell, throttle


T_DIR = rel_path('../../templates/d2')


def split_coords(source, x_num, y_num=1):
    if y_num != 1:
        raise NotImplementedError(f'{y_num=}')

    if isinstance(source, tuple):
        x0, y0, x1, y1 = source
    else:
        x0, y0 = 0, 0
        y1, x1 = source.shape[:2]
    dx = int((x1 - x0) / x_num)
    for i in range(x_num):
        cx0 = x0 + dx * i
        start = cx0, y0
        end = cx0 + dx, y1
        yield start, end


def points_to_rect(p0, p1):
    x0, y0 = p0
    x1, y1 = p1
    return [x0, y0, int(x1 - x0), int(y1 - y0)]


def hist(img):
    out = []
    mask = cv2.inRange(img, (170, 220, 250), (180, 230, 255))
    print(f'M: {mask.shape=} / {img.shape=} / {mask.size=}')
    mask = None
    for i in range(3):
        h = cv2.calcHist(img[:, :, i], [0], mask, [16], [0, 255])
        print(f'{h=}')
        out.append(int(np.argmax(h)))
    return out


class POT(enum.IntEnum):
    HP = enum.auto()
    MP = enum.auto()
    RV = enum.auto()


class Potions:
    p_dir = T_DIR / 'potions'
    p_dir.mkdir(parents=True, exist_ok=True)

    coord = (1332, 1350, 1620, 1415)
    data = []
    pos = [None, None, None, None]
    have_read = []

    def reread(self):
        for f in self.p_dir.iterdir():
            if f in self.have_read:
                continue

            h = imread(f)
            self.have_read.append(f)

            n = f.name
            if n.startswith('mana'):
                _t = POT.MP
            elif n.startswith('hp'):
                _t = POT.HP
            elif n.startswith('rev'):
                _t = POT.RV
            else:
                continue
            self.data.append((h, _t))

    def detect(self, img, cropped):
        cv2.imshow('I', img)
        cv2.imshow('C', cropped)

        for template, _type in self.data:
            if match(img, template, 0.93):
                print(f'Ret type: {_type}')
                return _type

        cv2.imwrite(str(self.p_dir / 'a_unk.png'), cropped)

    def frame(self, full):
        cropped = crop(ctx.df, self.coord, copy=False)
        h, w = cropped.shape[:2]
        # cv2.rectangle(cropped, (0, 0), (w, h), (255, 255, 0), 2)
        self.rects(cropped)

    def hash(self, img):
        return hash(str(img))

    def rects(self, cropped):
        h, w = cropped.shape[:2]
        for idx, ((x0, y0), (x1, y1)) in enumerate(split_coords(cropped, 4)):
            dx = int(x1 - x0)
            start = x0 + int(dx / 3) + 9, y0 + 23
            end = x1 - int(dx / 3), y1 - 9

            cell = crop(cropped, (x0, y0, x1, y1), copy=False)
            img = crop(cropped, (*start, *end))
            self.reread()
            what = self.detect(cell, cropped=img)

            self.pos[idx] = what
            ctx.d(f'{idx=} => {what}')

            # h = hist(img)
            # ctx.d(f'Hist: {idx=} => {h}')
            # cv2.rectangle(cropped, start, end, h, 3)


class D2Handler(Handler):
    def __init__(self):
        self.potions = Potions()
        self.life = mock.MagicMock()
        ctx.reset()

    g_pos = (2150, 1300, 2200, 1400)
    g_tmpl = imread(T_DIR / 'game.png')

    def is_game(self, full):
        return match(crop(full, self.g_pos, copy=True), self.g_tmpl)

    def frame(self, full):
        ctx.frame(full)
        if not self.is_game(full):
            ctx.d('No game')
            return
        self.potions.frame(full)
        ctx.d(f'Frame: {ctx.f_count}')

    def handle_key(self, char):
        pass
