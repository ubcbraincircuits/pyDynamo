import numpy as np

from model import FiloType

def addedSubtractedTransitioned(
    trees,
    excludeAxon=True,
    excludeBasal=True,
    terminalDist=10,
    filoDist=10
):
    # All outputs will be [# trees][# branches]
    nTrees = len(trees)
    nBranches = len(trees[-1].branches)
    resultShape = (nTrees, nBranches)

    # Outputs:
    filoTypes = np.full(resultShape, FiloType.ABSENT)
    addedResult = np.full(resultShape, False)
    subtracted = np.full(resultShape, False)
    transitioned = np.full(resultShape, False)
    masterChanged = np.full(resultShape, False)
    masterNodes = np.full(resultShape, np.nan)

    for treeAt, tree in enumerate(trees):
        _recursiveFiloTypes(filoTypes, masterNodes, masterChanged, trees, treeAt, 0, excludeAxon, excludeBasal, terminalDist, filoDist)

    filos = (filoTypes > FiloType.ABSENT) & (filoTypes < FiloType.BRANCH_ONLY) # NOTE: brackets needed for numpy precendence
    branches = (filoTypes > FiloType.TERMINAL)
    added = (filos[1:, :] & ~filos[:-1, :])
    subtracted = (~filos[1:, :] & filos[:-1, :])
    transitioned = filos[:-1, :] & ~branches[:-1, :] & branches[1:, :]
    masterChanged = masterChanged[1:, :] # No changes in first tree

    added[masterChanged] = False
    subtracted[masterChanged] = False


    return filoTypes, added, subtracted, transitioned, masterChanged, masterNodes

# HACK : TODO: Migrate to ID-based results rather than index-based
def _recursiveFiloTypes(filoTypes, masterNodes, masterChanged, trees, treeIdx, branchIdx, excludeAxon, excludeBasal, terminalDist, filoDist):
    branch = trees[treeIdx].branches[branchIdx]
    pointsWithRoot = [branch.parentPoint] + branch.points

    # 1) If the branch has not been created yet, or is empty, abort
    if len(pointsWithRoot) < 2:
        filoTypes[treeIdx][branchIdx] = FiloType.ABSENT
        return
    # 2) If the branch contains an 'axon' label, abort
    if excludeAxon and _lastPointWithLabel(pointsWithRoot, 'axon') >= 0:
        filoTypes[treeIdx][branchIdx] = FiloType.ABSENT
        return
    # 3) If the branch is a basal dendrite, abort
    if excludeBasal and _lastPointWithLabel(pointsWithRoot, 'basal') >= 0:
        filoTypes[treeIdx][branchIdx] = FiloType.ABSENT
        return
    # 4) If the branch has a lamella and no children, abort
    if (not branch.hasChildren()) and _lastPointWithLabel(pointsWithRoot, 'lam') >= 0:
        filoTypes[treeIdx][branchIdx] = FiloType.BRANCH_ONLY
        return

    # Walk down each child in turn:
    totalLength, totalLengthToLastBranch = branch.worldLengths()
    cumulativeLengths = branch.cumulativeWorldLengths()
    for pointIdx, point in enumerate(branch.points):
        if len(point.children) == 0:
            continue # Skip childless points

        forceInterstitial = False
        for childBranch in point.children:
            childBranchIdx = childBranch.indexInParent()
            if len(childBranch.points) < 1:
                continue # Skip empty branches

            if childBranch.isFilo(filoDist):
                distPointToEnd = totalLength - cumulativeLengths[pointIdx]
                isTerminal = (distPointToEnd < terminalDist)
                filoTypes[treeIdx][childBranchIdx] = \
                    FiloType.TERMINAL if isTerminal else FiloType.INTERSTITIAL

                # HACK TODO - figure out what this is doing?
                # mark branchtip filopodia as branch:
                # current node has 1 children and is the endpoint
                if len(childBranch.points) == 1 and point == branch.points[-1]:
                    filoTypes[treeIdx][childBranchIdx] = FiloType.BRANCH_ONLY
                    masterNodes[treeIdx][childBranchIdx] = branchIdx # we use convention that long branches are their own masternode
                    masterChanged[treeIdx][childBranchIdx] = _didMasterChange(masterNodes, treeIdx, branchIdx)

            else: # Not filo
                # all terminal filopodia identified so far are actually interstitial
                forceInterstitial = True
                _recursiveFiloTypes(filoTypes, masterNodes, masterChanged, trees, treeIdx, childBranchIdx, excludeAxon, excludeBasal, terminalDist, filoDist)

        # Turn all previous terminal filos into interstitial filos
        if forceInterstitial:
            for prevPoint in branch.points:
                if prevPoint == point:
                    break
                for childBranch in prevPoint.children:
                    childBranchIdx = childBranch.indexInParent()
                    if filoTypes[treeIdx][childBranchIdx] == FiloType.TERMINAL:
                        filoTypes[treeIdx][childBranchIdx] = FiloType.INTERSTITIAL


        # deal with potential terminal filopodium that's part of the branch
        # {note that forceinterstitial was set for the last child in above section}
        totalDist = totalLength - totalLengthToLastBranch

        # part of this branch is a filopodium
        if totalDist > 0 and totalDist < filoDist:
            #the last child is a branch, so this terminal filo is interstitial
            filoTypes[treeIdx][branchIdx] = \
                FiloType.BRANCH_WITH_INTERSTITIAL if forceInterstitial else FiloType.BRANCH_WITH_TERMINAL

            # branches are also defined by a 'master node' that marks the start of any potential temrinal filopodium
            lastPointWithChildren = None
            for point in reversed(branch.points):
                if len(point.children) > 0:
                    lastPointWithChildren = point
                    break
            if lastPointWithChildren is not None:
                masterNodes[treeIdx][branchIdx] = lastPointWithChildren.indexInParent()
                masterChanged[treeIdx][branchIdx] = _didMasterChange(masterNodes, treeIdx, branchIdx)
        elif totalDist == 0: # a trunk branch
            filoTypes[treeIdx][branchIdx] = FiloType.BRANCH_ONLY
            masterNodes[treeIdx][branchIdx] = branch.children[-1] # the last node is the masternode
            masterChanged[treeIdx][branchIdx] = _didMasterChange(masterNodes, treeIdx, branchIdx)
        else: # a long branch
            filoTypes[treeIdx][branchIdx] = FiloType.BRANCH_ONLY
            masterNodes[treeIdx][branchIdx] = branchIdx # we use convention that long branches are their own masternode
            masterChanged[treeIdx][branchIdx] = _didMasterChange(masterNodes, treeIdx, branchIdx)

# TODO: Get rid of this and parallelize calculation
def _didMasterChange(masterNodes, treeIdx, branchIdx):
    if treeIdx == 1:
        return False
    return masterNodes[treeIdx, branchIdx] != masterNodes[treeIdx - 1, branchIdx]

# Return the index of the last point whose label contains given text, or -1 if not found.
# TODO - move somewhere common.
def _lastPointWithLabel(points, label):
    lastPointIdx = -1
    for i, point in enumerate(points):
        if point.annotation.find(label) != -1:
            lastPointIdx = i
    return lastPointIdx
