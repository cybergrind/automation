import math
import logging
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

from capture.types import Img, Rect


CONF_THRESHOLD_TM = 0.7  # cv2 template matching
log = logging.getLogger(__name__)


def match_image(img: Img, template: Img, threshold: float = CONF_THRESHOLD_TM) -> Optional[Rect]:
    # can be: np.where(cv2.matchTemplate(cropped, PHANT, cv2.TM_CCOEFF_NORMED) > 0.77)
    _, conf, _, coord = cv2.minMaxLoc(cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED))
    if conf > threshold:
        if len(coord) == 2:
            return Rect(*coord, *template.shape[:2])
        return coord


def match_many(img: Img, template: Img, threshold: float = CONF_THRESHOLD_TM) -> List[Rect]:
    matches = []
    res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
    loc = np.where(res >= threshold)
    w, h = template.shape[1], template.shape[0]
    for pt in zip(*loc[::-1]):
        matches.append(Rect(pt[0], pt[1], w, h))
    return matches


def merge_multi(*images: List[Img]) -> Img:
    """merge multiple images into one. for one-pass ocr"""
    width = max(x.shape[1] for x in images)
    height = sum(x.shape[0] for x in images)
    to_ocr = np.zeros((height, width, 3), np.uint8)
    curr_y = 0
    for i in images:
        y, x = i.shape[:2]
        to_ocr[curr_y : curr_y + y, 0:x, :] = i
        curr_y += y
    return to_ocr


def put_text(img, txt, pos=(5, 20), color=(255, 0, 255), size=0.5):
    step = math.ceil(32 * size)

    if isinstance(txt, str):
        cv2.putText(img, txt, pos, cv2.FONT_HERSHEY_SIMPLEX, size, color, 2)
    elif isinstance(txt, list):
        x, y = pos
        for idx, s in enumerate(txt):
            text_pos = (x, y + idx * step)
            cv2.putText(img, s, text_pos, cv2.FONT_HERSHEY_SIMPLEX, size, color, 2)


def imread(path: Path) -> Img:
    return cv2.imread(str(path))[:, :, :3]
