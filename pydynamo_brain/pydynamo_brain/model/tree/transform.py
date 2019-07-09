"""
.. module:: tree
"""
import attr
import numpy as np

import pydynamo_brain.util as util
from pydynamo_brain.util import SAVE_META


@attr.s
class Transform:
    """Affine transform from pixel to world space."""

    rotation = attr.ib(default=attr.Factory(lambda: np.eye(3).tolist()), cmp=False, metadata=SAVE_META)
    """Rotation to apply to (x, y, z)."""

    translation = attr.ib(default=attr.Factory(lambda: [0.0, 0.0, 0.0]), cmp=False, metadata=SAVE_META)
    """ (x, y, z) Translation to move all the points by."""

    scale = attr.ib(default=attr.Factory(lambda: [1.0, 1.0, 1.0]), cmp=False, metadata=SAVE_META)
    """ (sX, sY, sZ) Scaling factors to multiply each axis by."""
