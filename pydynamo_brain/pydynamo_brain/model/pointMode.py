from enum import IntEnum
from functools import total_ordering

@total_ordering
class PointMode(IntEnum):
    """Which click 'mode' the selected point is currently in."""

    DEFAULT = 0
    """Selected point is part of a normal drawing."""

    MOVE = 1
    """Selected point is being moved."""

    REPARENT = 2
    """Selected point is being reparented"""

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

    def __int__(self):
        return self.value
