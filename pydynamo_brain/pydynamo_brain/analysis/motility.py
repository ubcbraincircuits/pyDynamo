import numpy as np

from typing import Any, Dict, List, Tuple

from .addedSubtractedTransitioned import addedSubtractedTransitioned
from .TDBL import TDBL

from pydynamo_brain.model import Tree, Branch, FiloType
import pydynamo_brain.util as util

def motility(trees: List[Tree],
    excludeAxon: bool=True,
    excludeBasal: bool=True,
    includeAS: bool=False,
    terminalDist: float=10.0,
    filoDist: float=10.0,
    **kwargs: Any,
) -> Tuple[Dict[str, np.ndarray], np.ndarray]:
    """Calculate motility of all branches across time.

    Args:
        trees (list): The structure of the tree across time.
        excludeAxon (bool): Flag indicating whether the motility of the axon should be skipped.
        excludeBasal (bool): Flag indicating whether the motility of basal dendrites should be skipped.
        includeAS (bool): Flag indicating whether changes of branches that were added/subtracted should be included.
        terminalDist (float): Maximum distance between last branch and end of dendrite for that to be considered a filo.
        filoDist (float): Maximum distance a branch can be for it to be considered a filo.

    Returns:
        (tuple): tuple containing:

            motility(dict): the raw changes, plus those normalized by tdbl/filo lengths/counts

            filoLengths(np.array): the length of filopodia on each each branch.
    """

    # print ("\n\nCalculating motility...")
    filoTypes, added, subtracted, _, masterChangedOut, _ = \
        addedSubtractedTransitioned(trees, excludeAxon, excludeBasal, terminalDist, filoDist)

    # Outputs:
    nTrees = len(trees)
    branchIDList = util.sortedBranchIDList(trees)
    nBranches = len(branchIDList)

    resultShape = (nTrees, nBranches)
    filoLengths = np.full(resultShape, np.nan)
    allTDBL = np.zeros(nTrees)

    # Calculate Filo lengths for all trees:
    for treeIdx, tree in enumerate(trees):
        allTDBL[treeIdx] = TDBL(tree, excludeAxon, excludeBasal, includeFilo=True, filoDist=filoDist)
        if tree.rootPoint is not None:
            for branch in tree.rootPoint.children:
                _calcFiloLengths(branchIDList, filoLengths[treeIdx], treeIdx, branch, excludeAxon, excludeBasal, filoDist)

    # Raw motility:
    lengthBefore, lengthAfter = filoLengths[:-1, :], filoLengths[1:, :]
    rawMotility = lengthAfter - lengthBefore
    rawMotility[masterChangedOut] = np.nan

    # including motility due to additions/subtractions
    if includeAS:
        rawMotility[added] = lengthAfter[added]
        rawMotility[subtracted] = -lengthBefore[subtracted]

    filoLengthWithNan = np.array(filoLengths[:rawMotility.shape[0], :])
    filoLengthWithNan[np.isnan(rawMotility)] = np.nan
    filoLengthSum = np.nansum(filoLengthWithNan, axis=1)
    nFilo = np.sum((filoTypes > FiloType.ABSENT) & (filoTypes < FiloType.BRANCH_ONLY), axis=1)

    # Normalize by pre stats, not post:
    motilities = {
        'raw': rawMotility,
        'rawTDBL': np.nansum(rawMotility, axis=1) / allTDBL[:-1],
        'rawFilo': np.nansum(rawMotility, axis=1) / filoLengthSum,
        'rawNFilo': np.nansum(rawMotility, axis=1) / nFilo[:-1]
    }
    return motilities, filoLengths


def _calcFiloLengths(
    branchIDList: List[str], filoLengths: np.ndarray,
    treeIdx: int, branch: Branch,
    excludeAxon: bool, excludeBasal: bool, filoDist: float
) -> None:
    if branch.id not in branchIDList:
        return

    branchIdx = branchIDList.index(branch.id)
    pointsWithRoot = branch.points
    if branch.parentPoint is not None:
        pointsWithRoot = [branch.parentPoint] + pointsWithRoot

    # 1) If the branch has not been created yet, or is empty, abort
    if branch.isEmpty():
        filoLengths[branchIdx] = 0.0
        return
    # 2) If the branch contains an 'axon' label, abort. 3) Same with basal dendrite.
    if (excludeAxon and branch.isAxon()) or (excludeBasal and branch.isBasal()):
        filoLengths[branchIdx] = np.nan
        return
    # 4) If we're a filo, set and stop:
    isFilo, branchLength = branch.isFilo(filoDist)
    if isFilo:
        filoLengths[branchIdx] = branchLength
        return

    # 5) Recurse to fill filolengths cache for all child branches:
    for point in branch.points:
        for childBranch in point.children:
            _calcFiloLengths(branchIDList, filoLengths, treeIdx, childBranch, excludeAxon, excludeBasal, filoDist)

    # 6) Add the final filo for this branch if it is there, otherwise use entire length
    filoLengths[branchIdx] = 0
    totalLength, totalLengthToLastBranch = branch.worldLengths()
    lengthPastLastBranch = totalLength - totalLengthToLastBranch
    filoLengths[branchIdx] = lengthPastLastBranch
