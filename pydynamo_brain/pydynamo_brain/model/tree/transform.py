"""
.. module:: tree
"""
import attr
import numpy as np

from typing import List

import pydynamo_brain.util as util
from pydynamo_brain.util import SAVE_META


@attr.s
class Transform:
    """Affine transform from pixel to world space."""

    rotation: List[List[float]] = attr.ib(default=attr.Factory(lambda: np.eye(3).tolist()), eq=False, order=False, metadata=SAVE_META)
    """Rotation to apply to (x, y, z)."""

    translation: List[float] = attr.ib(default=attr.Factory(lambda: [0.0, 0.0, 0.0]), eq=False, order=False, metadata=SAVE_META)
    """ (x, y, z) Translation to move all the points by."""

    scale: List[float] = attr.ib(default=attr.Factory(lambda: [1.0, 1.0, 1.0]), eq=False, order=False, metadata=SAVE_META)
    """ (sX, sY, sZ) Scaling factors to multiply each axis by."""
