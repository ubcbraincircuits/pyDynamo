from enum import IntEnum
from functools import total_ordering

@total_ordering
class DrawMode(IntEnum):
    """Which global 'mode' the drawer is currently in."""

    DEFAULT = 0
    """Normal draw POI points."""

    PUNCTA = 1
    """POI drawn indicate puncta, rather than tree points"""

    REGISTRATION = 2
    """Selected points are being registered, don't have to match IDs."""

    RADII = 3
    """Editing point radii."""

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

    def __int__(self):
        return self.value
