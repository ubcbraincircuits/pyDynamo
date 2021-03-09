import pandas as pd

from typing import Any, Callable, List, Union

import pydynamo_brain.files as files
import pydynamo_brain.util as util

from pydynamo_brain.model import FullState

# Run analysis for all branches, by running each desired function and combining into one dataframe.
def allBranches(
    stateOrPath: Union[FullState, str], funcs: List[Callable[..., pd.DataFrame]], **kwargs: Any
) -> pd.DataFrame:
    # Load state first if provided as a string.
    fullState = None
    if isinstance(stateOrPath, FullState):
        fullState = stateOrPath
    else:
        assert isinstance(stateOrPath, str)
        fullState = files.loadState(stateOrPath)
    assert fullState is not None
    
    # Merge all results into one dataframe.
    sortedBranchIDs = util.sortedBranchIDList(fullState.trees)
    result = pd.DataFrame(index=sortedBranchIDs)
    for func in funcs:
        result = result.join(func(fullState, sortedBranchIDs, **kwargs))
    return result
