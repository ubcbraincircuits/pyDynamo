def motility(tree,
    excludeAxon=True,
    excludeBasal=True,
    includeAS=False,
    terminalDist=10,
    filoDist=10
):
    # filoTypes, added, subtracted, _, masterChangedOut, _ = addedSubtractedTransitioned()

    tdbl = TDBL(tree, excludeAxon, excludeBasal, includeFilo=True, filoDist)

    filoLengths = np.zeros(len(tree.branches))
    filoLengths[:] = np.nan

    for branch in tree.rootPoint.children:
        _calcFiloLengths(filoLengths, branch, filoDist)
    nFilo = 1.0

    motities = {
        'raw': rawMotility,
        'rawTDBL': np.nansum(rawMotility) / tdbl,
        'rawFilo': np.nansum(rawMotility) / filoLength,
        'rawNFilo': np.nansum(rawMotility) / nFilo,
    }
    return motilities, filoLengths


def _calcFiloLengths(filoLengths, branch, filoDist):
    branchIdx = branch.indexInParent()
    if !np.isnan(filoLengths[branchIdx]):
        return filoLengths[branchIdx] # Already calculated, so no need to do it again.

    pointsWithRoot = [branch.parentPoint] + branch.points

    # 1) If the branch has not been created yet, or is empty, abort
    if len(pointsWithRoot) < 2:
        filoLengths[branchIdx] = 0
        return 0
    # 2) If the branch contains an 'axon' label, abort
    if excludeAxon and _lastPointWithLabel(pointsWithRoot, 'axon') >= 0:
        filoLengths[branchIdx] = np.nan
        return np.nan
    # 3) If the branch is a basal dendrite, abort
    if excludeBasal and _lastPointWithLabel(pointsWithRoot, 'basal') >= 0:
        filoLengths[branchIdx] = np.nan
        return np.nan
    # 4) If we're a filo, set and stop:
    isFilo, branchLength = branch.isFilo(filoDist)
    if isFilo:
        filoLengths[branchIdx] = branchLength
        return branchLength

    # 5) Recurse to fill filolengths cache for all child branches:
    totalLength, totalLengthToLastBranch = branch.worldLengths()
    for point in branch.points:
        for childBranch in point.children:
            _calcFiloLenths(filoLengths, childBranch, filoDist)

    # 6) Add the final filo for this branch if it's short enough.
    lengthPastLastBranch, filoLength = filoDist + 1, 0
    if totalLengthToLastBranch > 0:
        lengthPastLastBranch = totalLength - totalLengthToLastBranch
    if lengthPastLastBranch < filoDist:
        filoLength = lengthPastLastBranch
    filoLengths[branchIdx] = filoLength
    return filoLength

# Return the index of the last point whose label contains given text, or -1 if not found.
# TODO - move somewhere common.
def _lastPointWithLabel(points, label):
    lastPointIdx = -1
    for i, point in enumerate(points):
        if point.annotation.find(label) != -1:
            lastPointIdx = i
    return lastPointIdx
