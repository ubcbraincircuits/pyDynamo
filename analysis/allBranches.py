import pandas as pd

import files
import util

from model import FullState

# Run analysis for all trees, by running each desired function and combining into one dataframe.
def allBranches(stateOrPath, funcs, **kwargs):
    # Load state first if provided as a string.
    fullState = None
    if isinstance(stateOrPath, FullState):
        fullState = stateOrPath
    else:
        assert isinstance(stateOrPath, str)
        fullState = files.loadState(stateOrPath)

    # Merge all results into one dataframe.
    sortedBranchIDs = util.sortedBranchIDList(fullState.trees)
    result = pd.DataFrame(index=sortedBranchIDs)
    for func in funcs:
        result = result.join(func(fullState, sortedBranchIDs, **kwargs))
    return result
