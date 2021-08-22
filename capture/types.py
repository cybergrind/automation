from typing import NamedTuple

import numpy as np
import numpy.typing as npt


class Rect(NamedTuple):
    x: int
    y: int
    w: int
    h: int


Img = npt.NDArray[np.uint8]
