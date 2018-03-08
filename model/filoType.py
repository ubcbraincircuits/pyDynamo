from enum import Enum
from functools import total_ordering


"""
From Matlab:
%filo types key:
% 0 - absent
% 1 - interstitial filo
% 2 - terminal filo
% 3 - branch w int filo
% 4 - branch w term filo
% 5 - branch only

TODO: Document
"""
@total_ordering
class FiloType(Enum):
    ABSENT = 0
    INTERSTITIAL = 1
    TERMINAL = 2
    BRANCH_WITH_INTERSTITIAL = 3
    BRANCH_WITH_TERMINAL = 4
    BRANCH_ONLY = 5

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

# Note: order matters. All those with value 1 -> 4 are counted as filo
