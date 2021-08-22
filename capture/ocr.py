import json
from abc import ABC, abstractmethod
from contextlib import suppress
from typing import List

import easyocr

from fan_tools.python import py_rel_path

from capture.types import Img, Rect


CONF_THRESHOLD = 0.56  # OCR
FILE_BASE = py_rel_path('../.data')
FILE_BASE.mkdir(exist_ok=True)

reader = easyocr.Reader(['en'], gpu=True)


def run_ocr(img: Img):
    data = reader.readtext(img)
    return data


def read_text(img: Img) -> List[str]:
    data = reader.readtext(img)
    return [d[1] for d in data]


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
    def rect(self) -> Rect:
        return (self.pos[0], self.pos[1]), (self.pos[2], self.pos[3])
