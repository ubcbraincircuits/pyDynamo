import pandas as pd

import pydynamo_brain.files as files
import pydynamo_brain.util as util

from pydynamo_brain.model import FullState

# Run analysis for all puncta, by running each desired function and combining into one dataframe.
def allPuncta(stateOrPath, funcs, **kwargs):
    # Load state first if provided as a string.
    fullState = None
    if isinstance(stateOrPath, FullState):
        fullState = stateOrPath
    else:
        assert isinstance(stateOrPath, str)
        fullState = files.loadState(stateOrPath)

    # Merge all results into one dataframe.
    sortedPunctaIDs = util.sortedPunctaIDList(fullState.puncta)
    result = pd.DataFrame(index=sortedPunctaIDs)
    for func in funcs:
        result = result.join(func(fullState, sortedPunctaIDs, **kwargs))
    return result
