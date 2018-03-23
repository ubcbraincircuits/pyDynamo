import numpy as np

from .addedSubtractedTransitioned import addedSubtractedTransitioned
from .TDBL import TDBL

from model import FiloType

def motility(trees,
    excludeAxon=True,
    excludeBasal=True,
    includeAS=False,
    terminalDist=10,
    filoDist=10
):
    """TODO - document."""

    print ("\n\nCalculating motility...")
    filoTypes, added, subtracted, _, masterChangedOut, _ = \
        addedSubtractedTransitioned(trees, excludeAxon, excludeBasal, terminalDist, filoDist)

    # Outputs:
    nTrees, nBranches = len(trees), len(trees[-1].branches)
    resultShape = (nTrees, nBranches)
    filoLengths = np.full(resultShape, np.nan)
    allTDBL = np.zeros(nTrees)

    # Calculate Filo lengths for all trees:
    for treeIdx, tree in enumerate(trees):
        allTDBL[treeIdx] = TDBL(tree, excludeAxon, excludeBasal, includeFilo=True, filoDist=filoDist)
        for branch in tree.rootPoint.children:
            _calcFiloLengths(filoLengths[treeIdx], treeIdx, branch, excludeAxon, excludeBasal, filoDist)

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


def _calcFiloLengths(filoLengths, treeIdx, branch, excludeAxon, excludeBasal, filoDist):
    branchIdx = branch.indexInParent()
    pointsWithRoot = [branch.parentPoint] + branch.points

    # 1) If the branch has not been created yet, or is empty, abort
    if branch.isEmpty():
        filoLengths[branchIdx] = 0
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
            _calcFiloLengths(filoLengths, treeIdx, childBranch, excludeAxon, excludeBasal, filoDist)

    # 6) Add the final filo for this branch if it's short enough.
    filoLengths[branchIdx] = 0
    totalLength, totalLengthToLastBranch = branch.worldLengths()
    if totalLengthToLastBranch > 0:
        lengthPastLastBranch = totalLength - totalLengthToLastBranch
        if lengthPastLastBranch < filoDist:
            filoLengths[branchIdx] = lengthPastLastBranch
