import numpy as np

from model import FiloType
from util import emptyArrayMatrix

# Set these to tree / branch indexes to print TDBL information for that specific target.
DEBUG_TREE = -1
DEBUG_BRANCH = -1

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
    masterNodes = emptyArrayMatrix(nTrees, nBranches)

    for treeAt, tree in enumerate(trees):
        _recursiveFiloTypes(filoTypes, masterNodes, masterChanged, trees, treeAt, 0, excludeAxon, excludeBasal, terminalDist, filoDist)

    filoExists = (filoTypes > FiloType.ABSENT)
    filos = filoExists & (filoTypes < FiloType.BRANCH_ONLY) # NOTE: brackets needed for numpy precendence
    branches = (filoTypes > FiloType.TERMINAL)
    filoBefore, filoAfter = filos[:-1, :], filos[1:, :]
    added = (~filoBefore & filoAfter)
    subtracted = (filoBefore & ~filoExists[1:, :])
    transitioned = filoBefore & ~branches[:-1, :] & branches[1:, :]
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
        if treeIdx == DEBUG_TREE:
            print("branch %d is empty" % (branchIdx + 1))
        filoTypes[treeIdx][branchIdx] = FiloType.ABSENT
        return
    # 2) If the branch contains an 'axon' label, abort
    if excludeAxon and _lastPointWithLabel(pointsWithRoot, 'axon') >= 0:
        if treeIdx == DEBUG_TREE:
            print("branch %d is axon" % (branchIdx + 1))
        filoTypes[treeIdx][branchIdx] = FiloType.ABSENT
        return
    # 3) If the branch is a basal dendrite, abort
    if excludeBasal and _lastPointWithLabel(pointsWithRoot, 'basal') >= 0:
        if treeIdx == DEBUG_TREE:
            print("branch %d is basal" % (branchIdx + 1))
        filoTypes[treeIdx][branchIdx] = FiloType.ABSENT
        return
    # 4) If the branch has a lamella and no children, abort
    if (not branch.hasChildren()) and _lastPointWithLabel(pointsWithRoot, 'lam') >= 0:
        if treeIdx == DEBUG_TREE:
            print("branch %d is childless lamella" % (branchIdx + 1))
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

            childIsFilo, childLength = childBranch.isFilo(filoDist)
            if childIsFilo:
                if treeIdx == DEBUG_TREE:
                    print ("Child %d is filo, length %f < %f" % (childBranchIdx + 1, childLength, filoDist))
                distPointToEnd = totalLength - cumulativeLengths[pointIdx]
                if treeIdx == DEBUG_TREE and childBranchIdx == DEBUG_BRANCH:
                    hasChildren = []
                    for pIdx, p in enumerate(branch.points):
                        if len(p.children) > 0:
                            hasChildren.append(pIdx)
                isTerminal = (distPointToEnd < terminalDist)
                filoTypes[treeIdx][childBranchIdx] = \
                    FiloType.TERMINAL if isTerminal else FiloType.INTERSTITIAL

                # HACK TODO - figure out what this is doing?
                # mark branchtip filopodia as branch:
                # current node has 1 children and is the endpoint
                if len(point.children) == 1 and pointIdx == len(branch.points) - 1:
                    if treeIdx == DEBUG_TREE:
                        print ("child %d is branchtip filo" % (childBranchIdx + 1))
                    filoTypes[treeIdx][childBranchIdx] = FiloType.BRANCH_ONLY
                    masterNodes[treeIdx][childBranchIdx] = [branchIdx] # we use convention that long branches are their own masternode
                    if treeIdx == DEBUG_TREE and childBranchIdx == DEBUG_BRANCH:
                        print ("setting master to %s" % (str(masterNodes[treeIdx][childBranchIdx])))
                        print ("Compared to %s" % (str(masterNodes[treeIdx - 1][childBranchIdx])))
                    masterChanged[treeIdx][childBranchIdx] = _didMasterChange(masterNodes, treeIdx, childBranchIdx)
                    if treeIdx == DEBUG_TREE and childBranchIdx == DEBUG_BRANCH:
                        print ("master changed [%d][%d] = %s" % (treeIdx, childBranchIdx, str(masterChanged[treeIdx][childBranchIdx])))

            else: # Not filo
                # all terminal filopodia identified so far are actually interstitial
                forceInterstitial = True
                if treeIdx == DEBUG_TREE:
                    print ("Going down child branch, id = %d" % (childBranchIdx + 1))
                _recursiveFiloTypes(filoTypes, masterNodes, masterChanged, trees, treeIdx, childBranchIdx, excludeAxon, excludeBasal, terminalDist, filoDist)

        # Turn all previous terminal filos into interstitial filos
        if forceInterstitial:
            if treeIdx == DEBUG_TREE:
                print ("Force inter for point %d of branch %d" % (pointIdx + 2, branchIdx + 1))
            for prevPointIdx, prevPoint in enumerate(branch.points):
                for childBranch in prevPoint.children:
                    childBranchIdx = childBranch.indexInParent()
                    if treeIdx == DEBUG_TREE:
                        print ("Forcing %d to be int" % (childBranchIdx))
                    if filoTypes[treeIdx][childBranchIdx] == FiloType.TERMINAL:
                        filoTypes[treeIdx][childBranchIdx] = FiloType.INTERSTITIAL
                if prevPointIdx == pointIdx:
                    break


    # deal with potential terminal filopodium that's part of the branch
    # {note that forceinterstitial was set for the last child in above section}
    totalDist = totalLength - totalLengthToLastBranch
    if treeIdx == DEBUG_TREE:
        print ("Branch %d has distance %f - %f" % (branchIdx + 1, totalLength, totalLengthToLastBranch))

    # part of this branch is a filopodium
    if totalDist > 0 and totalDist < filoDist:
        #the last child is a branch, so this terminal filo is interstitial
        filoTypes[treeIdx][branchIdx] = \
            FiloType.BRANCH_WITH_INTERSTITIAL if forceInterstitial else FiloType.BRANCH_WITH_TERMINAL

        if treeIdx == DEBUG_TREE:
            print('branch %d has terminal filo. Force? %d' % (branchIdx+1, forceInterstitial))

        # branches are also defined by a 'master node' that marks the start of any potential temrinal filopodium
        lastPointWithChildren = None
        for point in reversed(branch.points):
            if len(point.children) > 0:
                lastPointWithChildren = point
                break
        if lastPointWithChildren is not None:
            masterNodes[treeIdx][branchIdx] = [b.indexInParent() for b in lastPointWithChildren.children]
            masterChanged[treeIdx][branchIdx] = _didMasterChange(masterNodes, treeIdx, branchIdx)

    elif totalDist == 0: # a trunk branch
        if treeIdx == DEBUG_TREE:
            print('branch %d is a trunk branch' % (branchIdx+1))
        filoTypes[treeIdx][branchIdx] = FiloType.BRANCH_ONLY
        masterNodes[treeIdx][branchIdx] = [b.indexInParent() for b in branch.points[-1].children] # the last node is the masternode
        masterChanged[treeIdx][branchIdx] = _didMasterChange(masterNodes, treeIdx, branchIdx)
    else: # a long branch
        if treeIdx == DEBUG_TREE:
            print('branch %d is a long branch' % (branchIdx+1))
        filoTypes[treeIdx][branchIdx] = FiloType.BRANCH_ONLY
        masterNodes[treeIdx][branchIdx] = [branchIdx] # we use convention that long branches are their own masternode
        if treeIdx == DEBUG_TREE and branchIdx == DEBUG_BRANCH:
            print ("Master node for target is %s" % (str(masterNodes[treeIdx][branchIdx])))
        masterChanged[treeIdx][branchIdx] = _didMasterChange(masterNodes, treeIdx, branchIdx)

    if treeIdx == DEBUG_TREE and branchIdx <= DEBUG_BRANCH:
        print ("After point %d, master is %s" % (branchIdx, str(masterNodes[0][DEBUG_BRANCH])))

# TODO: Get rid of this and parallelize calculation
def _didMasterChange(masterNodes, treeIdx, branchIdx):
    if treeIdx == 0:
        return False

    if treeIdx == DEBUG_TREE and branchIdx == DEBUG_BRANCH:
        print("old: master[%d][%d] = %s" % (treeIdx - 1, branchIdx, str(masterNodes[treeIdx - 1][branchIdx])))
        print("new: master[%d][%d] = %s" % (treeIdx, branchIdx, str(masterNodes[treeIdx][branchIdx])))

    for v in masterNodes[treeIdx - 1][branchIdx]:
        if v in masterNodes[treeIdx][branchIdx]:
            return False
    return True

# Return the index of the last point whose label contains given text, or -1 if not found.
# TODO - move somewhere common.
def _lastPointWithLabel(points, label):
    lastPointIdx = -1
    for i, point in enumerate(points):
        if point.annotation.find(label) != -1:
            lastPointIdx = i
    return lastPointIdx
