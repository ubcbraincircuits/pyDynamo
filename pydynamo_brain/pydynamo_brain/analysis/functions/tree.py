import numpy as np
import pandas as pd

from typing import Any, List

import pydynamo_brain.analysis as pdAnalysis
import pydynamo_brain.util as util

from pydynamo_brain.model import FiloType, FullState


MIN_MOTILITY = 0.1

# Provide the number of points in each tree.
def pointCount(fullState: FullState, **kwargs: Any) -> pd.DataFrame:
    counts = []
    for tree in fullState.trees:
        counts.append(len(tree.flattenPoints()))
    return pd.DataFrame({'pointCount': counts})

# Provide the number of branches in each tree.
def branchCount(fullState: FullState, **kwargs: Any) -> pd.DataFrame:
    counts = []
    for tree in fullState.trees:
        counts.append(len(tree.branches))
    return pd.DataFrame({'branchCount': counts})

# Provide the number of filo in each tree:
def filoCount(fullState: FullState, **kwargs: Any) -> pd.DataFrame:
    filoTypes = pdAnalysis.addedSubtractedTransitioned(fullState.trees, **kwargs)[0]
    countInterstitial = np.sum(
        (filoTypes == FiloType.INTERSTITIAL) |
        (filoTypes == FiloType.BRANCH_WITH_INTERSTITIAL)
    , axis=1)
    countTerminal = np.sum(
        (filoTypes == FiloType.TERMINAL) |
        (filoTypes == FiloType.BRANCH_WITH_TERMINAL)
    , axis=1)
    return pd.DataFrame({
        'filoCount': countInterstitial + countTerminal,
        'interstitialFiloCount': countInterstitial,
        'terminalFiloCount': countTerminal,
    })

# Calculate filopodia density (#/mm):
def filoDensity(fullState: FullState, **kwargs: Any) -> pd.DataFrame:
    counts = filoCount(fullState, **kwargs)
    # Scale up to per-mm, rather than per-micron
    lengths = tdbl(fullState, **kwargs)['tdbl'] / 1000.0
    return pd.DataFrame({
        'filoDensity': counts['filoCount'] / lengths,
        'interstitialFiloDensity': counts['interstitialFiloCount'] / lengths,
        'terminalFiloDensity': counts['terminalFiloCount'] / lengths,
    })

# Provide the total dendritic branch length in each tree.
def tdbl(fullState: FullState, **kwargs: Any) -> pd.DataFrame:
    tdbls = []
    for tree in fullState.trees:
        tdbls.append(pdAnalysis.TDBL(tree, **kwargs))
    return pd.DataFrame({'tdbl': tdbls})

# X and Y point for the maximal Sholl crossings, fitted using a polynomial
def shollStats(fullState: FullState, **kwargs: Any) -> pd.DataFrame:
    if 'shollBinSize' not in kwargs:
        raise Exception("Sholl requires shollBinSize to be set")
    binSizeUm = kwargs['shollBinSize']

    maxRadius = 0.0
    for tree in fullState.trees:
        maxRadius = max(maxRadius, tree.spatialRadius())

    criticalValues, dendriteMaxes = [], []
    for tree in fullState.trees:
        crossCounts, radii = pdAnalysis.sholl.shollCrossings(tree, binSizeUm, maxRadius)
        pCoeff, maxX, maxY = pdAnalysis.sholl.shollMetrics(crossCounts, radii)
        criticalValues.append(maxX)
        dendriteMaxes.append(maxY)

    return pd.DataFrame({
        'shollCriticalValue': criticalValues, # Radius for maximal crossings
        'shollDendriteMax': dendriteMaxes     # Number of crossings there
    })

# Provide motility added/subtracted/transitioned/extended/retracted counts
def motility(fullState: FullState, **kwargs: Any) -> pd.DataFrame:
    trees = fullState.trees
    nA: List[int] = []
    nS: List[int] = []
    nT: List[int] = []
    nE: List[int] = []
    nR: List[int] = []

    branchIDList = util.sortedBranchIDList(trees)
    _, added, subtracted, transitioned, _, _ = \
        pdAnalysis.addedSubtractedTransitioned(trees, **kwargs)
    motilityValues, _ = pdAnalysis.motility(trees, **kwargs)
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
