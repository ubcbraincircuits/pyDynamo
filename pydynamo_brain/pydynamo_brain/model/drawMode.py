from enum import IntEnum
from functools import total_ordering

from typing import Any

@total_ordering
class DrawMode(IntEnum):
    """Which global 'mode' the drawer is currently in."""

    DEFAULT: int = 0
    """Normal draw POI points."""

    PUNCTA: int = 1
    """POI drawn indicate puncta, rather than tree points"""

    REGISTRATION: int = 2
    """Selected points are being registered, don't have to match IDs."""

    RADII: int = 3
    """Editing point radii."""

    def __lt__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return self.value < other.value
        raise NotImplemented

    def __int__(self) -> int:
        return self.value
