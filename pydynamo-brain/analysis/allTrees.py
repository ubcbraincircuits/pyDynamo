import pandas as pd

import files
from model import FullState

# Run analysis for all trees, by running each desired function and combining into one dataframe.
def allTrees(stateOrPath, funcs, **kwargs):
    # Load state first if provided as a string.
    fullState = None
    if isinstance(stateOrPath, FullState):
        fullState = stateOrPath
    else:
        assert isinstance(stateOrPath, str)
        fullState = files.loadState(stateOrPath)

    # Merge all results into one dataframe.
    result = pd.DataFrame(index=list(range(len(fullState.trees))))
    for func in funcs:
        result = result.join(func(fullState, **kwargs))
    return result
