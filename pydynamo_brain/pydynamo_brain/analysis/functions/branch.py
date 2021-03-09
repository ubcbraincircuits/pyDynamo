import math
import numpy as np
import pandas as pd

from typing import Any, Callable, Dict, List

import pydynamo_brain.analysis as pdAnalysis
from pydynamo_brain.model import FullState

# Provide the length of the branch, and the length to the last branch.
def branchLengths(fullState: FullState, branchIDList: List[str], **kwargs: Any) -> pd.DataFrame:
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
def branchType(fullState: FullState, branchIDList: List[str], **kwargs: Any) -> pd.DataFrame:
    nTrees = len(fullState.trees)
    filoTypes, added, subtracted, transitioned, masterChanged, masterNodes = \
        pdAnalysis.addedSubtractedTransitioned(fullState.trees, **kwargs)
    intFiloTypes = filoTypes.astype(int)

    colNames = [('branchType_%02d' % (i + 1)) for i in range(nTrees)]
    return pd.DataFrame(data=intFiloTypes.T, index=branchIDList, columns=colNames)

# For each branch, return whether any point on the branch contains a given annotation
def branchHasAnnotation(
    fullState: FullState, branchIDList: List[str], annotation: str, recurseUp: bool=False, **kwargs: Any
) -> pd.DataFrame:
    result = {}
    for treeIdx, tree in enumerate(fullState.trees):
        haveAnnotations = []
        for branchID in branchIDList:
            branch = tree.getBranchByID(branchID)
            if branch is None:
                haveAnnotations.append(False)
            else:
                haveAnnotations.append(branch.hasPointWithAnnotation(annotation, recurseUp))
        result['annotated_%s_%02d' % (annotation, treeIdx + 1)] = haveAnnotations
    return pd.DataFrame(data=result, index=branchIDList).sort_index(axis=1)

# Given an annotation, wrap it up into an analysis function run over branches.
def branchHasAnnotationFunc(
    annotation: str, recurseUp: bool=False
) -> Callable[..., pd.DataFrame]: # Note: mypy doesn't deal well with kwargs in a Callable type.
    def funcWrapper(fullState: FullState, branchIDList: List[str], **kwargs: Any) -> pd.DataFrame:
        return branchHasAnnotation(fullState, branchIDList, annotation, recurseUp, **kwargs)
    return funcWrapper

# For each branch, find the ID of the parent branch
def branchParentIDs(fullState: FullState, branchIDList: List[str], **kwargs: Any) -> pd.DataFrame:
    result = {}
    for treeIdx, tree in enumerate(fullState.trees):
        parentPointIDs = []
        parentBranchIDs = []
        for branchID in branchIDList:
            branch = tree.getBranchByID(branchID)
            if branch is None or branch.parentPoint is None:
                parentPointIDs.append('')
                parentBranchIDs.append('')
            else:
                parentPointIDs.append(branch.parentPoint.id)
                if branch.parentPoint.parentBranch is None:
                    parentBranchIDs.append('')
                else:
                    parentBranchIDs.append(branch.parentPoint.parentBranch.id)
        result['parentPointID_%02d' % (treeIdx + 1)] = parentPointIDs
        result['parentBranchID_%02d' % (treeIdx + 1)] = parentBranchIDs
    return pd.DataFrame(data=result, index=branchIDList).sort_index(axis=1)

# For each branch, find the branch order (shaft or centrifugal)
# https://www.mbfbioscience.com/help/nl11/Default.htm#Editing/branchOrder.htm
def branchOrder(fullState: FullState, branchIDList: List[str], **kwargs: Any) -> pd.DataFrame:
    centrifugalOrder = True
    if 'shaftOrder' in kwargs:
        centrifugalOrder = not kwargs['shaftOrder']

    result = {}
    for treeIdx, tree in enumerate(fullState.trees):
        branchOrders = []
        for branchID in branchIDList:
            branch = tree.getBranchByID(branchID)
            if branch is None:
                branchOrders.append(-1)
            else:
                branchOrders.append(branch.getOrder(centrifugalOrder))
        result['order_%02d' % (treeIdx + 1)] = branchOrders

    return pd.DataFrame(data=result, index=branchIDList).sort_index(axis=1)
