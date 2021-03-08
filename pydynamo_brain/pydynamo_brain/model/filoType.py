from enum import IntEnum
from functools import total_ordering

from typing import Any

@total_ordering
class FiloType(IntEnum):
    """Categorization for a point/branch based of Filo present.
    Note that order matters, 1->4 are counted as Filo."""

    ABSENT: int = 0
    """Filo is not there."""

    INTERSTITIAL: int = 1
    """Filo in the middle of a branch."""

    TERMINAL: int = 2
    """Filo at the end of a branch"""

    BRANCH_WITH_INTERSTITIAL: int = 3
    """Branch with downstream interstitial Filo."""

    BRANCH_WITH_TERMINAL: int = 4
    """Branch with downstream terminal Filo."""

    BRANCH_ONLY: int = 5
    """Branch with no Filo."""

    def __lt__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

    def __int__(self) -> int:
        return self.value
