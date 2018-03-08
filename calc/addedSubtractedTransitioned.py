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
    filoTypes = np.full(resultShape, np.nan)
    addedResult = np.full(resultShape, False)
    subtractedResult = np.full(resultShape, False)
    transitionedResult = np.full(resultShape, False)
    masterNodesResult = np.full(resultShape, np.nan)
    masterChangedResult = np.full(resultShape, False)

    for treeAt, tree in enumerate(trees):
        _recursiveFiloTypes(filoTypes, trees, treeAt, 1, terminalDist, filoDist)

    filos = (filoTypes > 0) & (filoTypes < 5) # NOTE: brackets needed for numpy precendence
    branches = (filoTypes > 2)
    added = (filos[:, 1:] & ~filos[:, :-1])
    subtracted = (~filos[:, 1:] & filos[:, :-1])
    transitioned = filos[:, :-1] & ~branches[:, :-1] & branches[:, 1:]

    added[masterChanged] = False
    subtracted[masterChanged] = False


    return filoTypeResult, added, subtracted, transitioned, masterNodes, masterChanged

def _recursiveFiloTypes(filoTypeResult, trees, treeIdx, branchIdx, terminalDist, filoDist):
    branch = trees[treeIdx].branches[branchIdx]
    pointsWithRoot = [branch.parentPoint] + branch.points

    # 1) If the branch has not been created yet, or is empty, abort
    if len(pointsWithRoot) < 2:
        filoTypeResult[treeIdx][branchIdx] = FiloType.ABSENT
        return
    # 2) If the branch contains an 'axon' label, abort
    if excludeAxon and _lastPointWithLabel(pointsWithRoot, 'axon') >= 0:
        filoTypeResult[treeIdx][branchIdx] = FiloType.ABSENT
        return
    # 3) If the branch is a basal dendrite, abort
    if excludeBasal and _lastPointWithLabel(pointsWithRoot, 'basal') >= 0:
        filoTypeResult[treeIdx][branchIdx] = FiloType.ABSENT
        return
    # 4) If the branch has a lamella and no children, abort
    hasChildren = OAISDASD
    if (not hasChildren) and _lastPointWithLabel(pointsWithRoot, 'lam') >= 0:
        filoTypeResult[treeIdx][branchIdx] = FiloType.BRANCH_ONLY
        return

    # Walk down each child in turn:
    totalLength, totalLengthToLastBranch = branch.worldLengths()
    for point in branch.points:
        if len(point.children) == 0:
            continue # Skip childless points

        forceInterstitial = False
        for childBranch in point.children:
            childBranchIdx = AKJSDAS
            if len(childBranch.points) < 1:
                continue # Skip empty branches

            if childBranch.isFilo(filoDist):
                isTerminal = (distPointToEnd < terminalDist)
                filoTypeResult[treeIdx][childBranchIdx] = \
                    FiloType.TERMINAL if isTerminal else FiloType.INTERSTITIAL

                # HACK TODO - figure out what this is doing?
                # mark branchtip filopodia as branch:
                # current node has 1 children and is the endpoint
                if len(childBranch.points) == 1 and point == branch.points[-1]:
                    filoTypeResult[treeIdx][childBranchIdx] = FiloType.BRANCH_ONLY
                    masterNodes[treeIdx][childBranchIdx] = branchIdx # we use convention that long branches are their own masternode
                    masterChanged[treeIdx][branchIdx] = _didMasterChange(treeIdx, branchIdx)

            else: # Not filo
                # all terminal filopodia identified so far are actually interstitial
                forceInterstitial = True
                _recursiveFiloTypes(filoTypeResult, trees, treeIdx, childBranchIdx, terminalDist, filoDist)

        # Turn all previous terminal filos into interstitial filos
        if forceInterstitial:
            for prevPoint in branch.points:
                if prevPoint == point:
                    break
                for childBranch in prevPoint.children:
                    childBranchIdx = ASDJASD
                    if filoTypeResult[treeIdx][childBranchIdx] == FiloType.TERMINAL:
                        filoTypeResult[treeIdx][childBranchIdx] = FiloType.INTERSTITIAL


        # deal with potential terminal filopodium that's part of the branch
        # {note that forceinterstitial was set for the last child in above section}
        totalDist = totalLength - totalLengthToLastBranch

        # part of this branch is a filopodium
        if totalDist > 0 and totalDist < filoDist:
            #the last child is a branch, so this terminal filo is interstitial
            filoTypeResult[treeIdx][branchIdx] = \
                FiloType.BRANCH_WITH_INTERSTITIAL if forceInterstitial else FiloType.BRANCH_WITH_TERMINAL

            # branches are also defined by a 'master node' that marks the start of any potential temrinal filopodium
            if ~isempty(haschildren)
                masterNodes[treeIdx][branchIdx] =  branch{2}(haschildren(end));
                masterChanged[treeIdx][branchIdx] = _didMasterChange(treeIdx, branchIdx)
            end
        elif totalDist == 0: # a trunk branch
            filoTypeResult[treeIdx][branchIdx] = FiloType.BRANCH_ONLY
            masterNodes[treeIdx][branchIdx] = branch{2}(end); %the last node is the masternode
            masterChanged[treeIdx][branchIdx] = _didMasterChange(treeIdx, branchIdx)
        else: # a long branch
            filoTypeResult[treeIdx][branchIdx] = FiloType.BRANCH_ONLY
            masterNodes[treeIdx][branchIdx] = branchIdx # we use convention that long branches are their own masternode
            masterChanged[treeIdx][branchIdx] = _didMasterChange(treeIdx, branchIdx)

# TODO: Get rid of this and parallelize calculation
def _didMasterChange(treeIdx, branchIdx):
    if treeIdx == 1:
        return False
    return masterNodes[treeIdx, branchIdx] != masterNodes[treeIdx - 1, branchIdx]
