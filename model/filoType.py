from enum import Enum

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
class FiloType(Enum):
    ABSENT = 0
    INTERSTITIAL = 1
    TERMINAL = 2
    BRANCH_WITH_INTERSTITIAL = 3
    BRANCH_WITH_TERMINAL = 4
    BRANCH_ONLY = 5
