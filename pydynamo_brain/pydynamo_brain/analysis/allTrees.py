import pandas as pd

from typing import Any, Callable, List, Union

import pydynamo_brain.files as files

from pydynamo_brain.model import FullState

# Run analysis for all trees, by running each desired function and combining into one dataframe.
def allTrees(
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
    result = pd.DataFrame(index=list(range(len(fullState.trees))))
    for func in funcs:
        result = result.join(func(fullState, **kwargs))
    return result
