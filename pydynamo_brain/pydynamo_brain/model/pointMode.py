from enum import IntEnum
from functools import total_ordering

from typing import Any

@total_ordering
class PointMode(IntEnum):
    """Which click 'mode' the selected point is currently in."""

    DEFAULT: int = 0
    """Selected point is part of a normal drawing."""

    MOVE: int = 1
    """Selected point is being moved."""

    REPARENT: int = 2
    """Selected point is being reparented"""

    def __lt__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return self.value < other.value
        raise NotImplemented

    def __int__(self) -> int:
        return self.value
