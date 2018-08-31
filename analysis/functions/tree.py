import pandas as pd

from ..TDBL import TDBL

# Provide the number of points in each tree.
def pointCount(fullState, **kwargs):
    counts = []
    for tree in fullState.trees:
        counts.append(len(tree.flattenPoints()))
    return pd.DataFrame({'pointCount': counts})

# Provide the number of brances in each tree.
def branchCount(fullState, **kwargs):
    counts = []
    for tree in fullState.trees:
        counts.append(len(tree.branches))
    return pd.DataFrame({'branchCount': counts})

# Provide the total dendritic branch length in each tree.
def tdbl(fullState, **kwargs):
    tdbls = []
    for tree in fullState.trees:
        tdbls.append(TDBL(tree, **kwargs))
    return pd.DataFrame({'tdbl': tdbls})
