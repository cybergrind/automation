from abc import ABC, abstractmethod
from typing import Optional

import numpy.typing as npt

#from capture.ocr import run_ocr
from capture.types import Img, Rect


def crop(full: Img, pos: Rect, copy: bool = True):
    x0, x1 = pos[0], pos[2]
    y0, y1 = pos[1], pos[3]
    img = full[y0:y1, x0:x1, :]
    if copy:
        return img.copy()[:, :, :3]
    return img[:, :, :3]


def detect_text(img: Img, txt: str) -> Optional[Rect]:
    texts = run_ocr(img)
    for idx, i in enumerate(texts):
        if txt in i[1].lower():
            if len(i[1]) == len(txt):
                coord = texts[idx + 1][0]
                x0 = int(coord[0][0])
                y0 = int(coord[0][1])
                x1 = int(coord[2][0])
                y1 = int(coord[2][1])
                pos = [x0, y0, x1, y1]
                return pos


class Handler(ABC):
    @abstractmethod
    def frame(self, frame: npt.NDArray):
        raise NotImplementedError
