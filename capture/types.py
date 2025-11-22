from typing import NamedTuple

import numpy as np
import numpy.typing as npt


class Rect(NamedTuple):
    x: int
    y: int
    w: int
    h: int

    def overlap(self, r: 'Rect') -> float:
        """
        returns overlap percentage
        """
        x_overlap = max(0, min(self.x + self.w, r.x + r.w) - max(self.x, r.x))
        y_overlap = max(0, min(self.y + self.h, r.y + r.h) - max(self.y, r.y))
        overlap_area = x_overlap * y_overlap
        if overlap_area == 0:
            return 0.0
        self_area = self.w * self.h
        r_area = r.w * r.h
        union_area = self_area + r_area - overlap_area
        return overlap_area / union_area


Img = npt.NDArray[np.uint8]
