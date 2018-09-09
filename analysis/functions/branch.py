import numpy as np
import pandas as pd

import math

from ..addedSubtractedTransitioned import addedSubtractedTransitioned

# Provide the length of the branch, and the length to the last branch.
def branchLengths(fullState, branchIDList, **kwargs):
    result = {}
    for treeIdx, tree in enumerate(fullState.trees):
        fullLengths, lastBranchLengths = [], []
        for branchID in branchIDList:
            branch = tree.getBranchByID(branchID)
            if branch is None:
                fullLengths.append(math.nan)
                lastBranchLengths.append(math.nan)
            else:
                full, last = branch.worldLengths()
                fullLengths.append(full)
                lastBranchLengths.append(last)
        result['length_%02d' % (treeIdx + 1)] = fullLengths
        result['lengthToLastBranch_%02d' % (treeIdx + 1)] = lastBranchLengths
    return pd.DataFrame(data=result, index=branchIDList).sort_index(axis=1)

# For each branch, calculate filo type, and add as an int.
# @see FiloTypes.py for mapping from that to meaning of the values.
def branchType(fullState, branchIDList, **kwargs):
    nTrees = len(fullState.trees)
    filoTypes, added, subtracted, transitioned, masterChanged, masterNodes = \
        addedSubtractedTransitioned(fullState.trees, **kwargs)
    intFiloTypes = filoTypes.astype(int)

    colNames = [('branchType_%02d' % (i + 1)) for i in range(nTrees)]
    return pd.DataFrame(data=intFiloTypes.T, index=branchIDList, columns=colNames)
