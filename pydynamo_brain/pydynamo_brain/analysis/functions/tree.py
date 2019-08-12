import numpy as np
import pandas as pd

import pydynamo_brain.util as util

from pydynamo_brain.analysis import addedSubtractedTransitioned, TDBL
from pydynamo_brain.analysis import motility as motilityFunc
from pydynamo_brain.analysis import sholl


MIN_MOTILITY  = 0.1

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

# X and Y point for the maximal Sholl crossings, fitted using a polynomial
def shollStats(fullState, **kwargs):
    if 'shollBinSize' not in kwargs:
        raise Exception("Sholl requires shollBinSize to be set")
    binSizeUm = kwargs['shollBinSize']

    maxRadius = 0
    for tree in fullState.trees:
        maxRadius = max(maxRadius, tree.spatialRadius())

    criticalValues, dendriteMaxes = [], []
    for tree in fullState.trees:
        crossCounts, radii = sholl.shollCrossings(tree, binSizeUm, maxRadius)
        pCoeff, maxX, maxY = sholl.shollMetrics(crossCounts, radii)
        criticalValues.append(maxX)
        dendriteMaxes.append(maxY)

    return pd.DataFrame({
        'shollCriticalValue': criticalValues, # Radius for maximal crossings
        'shollDendriteMax': dendriteMaxes     # Number of crossings there
    })

# Provide motility added/subtracted/transitioned/extended/retracted counts
def motility(fullState, **kwargs):
    trees = fullState.trees
    nA, nS, nT, nE, nR = [], [], [], [], []

    branchIDList = util.sortedBranchIDList(trees)
    _, added, subtracted, transitioned, _, _ = \
        addedSubtractedTransitioned(trees, **kwargs)
    motilityValues, _ = motilityFunc(trees, **kwargs)
    rawMotility = motilityValues['raw'] # Use raw motility

    for treeIdx, treeModel in enumerate(trees):
        if treeIdx == 0:
            # First tree has no changes by definition:
            for arr in [nA, nS, nT, nE, nR]:
                arr.append(-1)
        else:
            # Otherwise, look up A/S/T and calculate E/R
            oldTreeModel = trees[treeIdx - 1]

            growCount, shrinkCount = 0, 0
            for branch in treeModel.branches:
                branchIdx = branchIDList.index(branch.id)
                if not added[treeIdx-1][branchIdx] and not transitioned[treeIdx-1][branchIdx]:
                    motValue = rawMotility[treeIdx-1][branchIdx]
                    if abs(motValue) > MIN_MOTILITY and len(branch.points) > 0:
                        if motValue > 0:
                            growCount += 1
                        else:
                            shrinkCount += 1
            nA.append(np.sum(added[treeIdx-1]))
            nS.append(np.sum(subtracted[treeIdx-1]))
            nT.append(np.sum(transitioned[treeIdx-1]))
            nE.append(growCount)
            nR.append(shrinkCount)

    return pd.DataFrame({
        'branchesAdded': nA,
        'branchesSubtracted': nS,
        'branchesTransitioned': nT,
        'branchesExtended': nE,
        'branchesRetracted': nR,
    })
