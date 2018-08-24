import math
import numpy as np

from analysis import addedSubtractedTransitioned
from model import FiloType
import util

def _fillWithOffset(toMap, fromMap, offset):
    for id, value in fromMap.items():
        toMap[id] = value + offset

# Return a mapping of point ID -> X position, for all points downstream from a branch.
def _pointXFromBranch(branch, branchIsFiloMap, filoDist):
    localPointX = {}

    # Child branches, in eventual order of being drawn left to right:
    childBranchesLeft, childFilo, childBranchesRight = [], [], []

    for point in branch.points:
        for childBranch in point.children:
            if (len(childBranch.points) == 0):
                continue

            if branchIsFiloMap[childBranch.id]:
                childFilo.append(childBranch)
            else:
                # Alternate whether child branches are shown on the left or right:
                if len(childBranchesLeft) == len(childBranchesRight):
                    childBranchesLeft = childBranchesLeft + [childBranch]
                else:
                    childBranchesRight = [childBranch] + childBranchesRight

    # Place all pointsin branches coming out the left in order...
    atX = 0
    for leftBranch in childBranchesLeft:
        childPointX = _pointXFromBranch(leftBranch, branchIsFiloMap, filoDist)
        if len(childPointX) > 0:
            _fillWithOffset(localPointX, childPointX, atX)
            atX += math.floor(max(childPointX.values())) + 1

    # ... then place filopodia points sideways based off length...
    nextOffset = -1
    for filo in childFilo:
        lengths = filo.cumulativeWorldLengths()
        for point, dist in zip(filo.points, lengths):
            localPointX[point.id] = atX + (dist/filoDist) * nextOffset * 0.9
        nextOffset *= -1 # alternate on left vs right.

    # ... then place all the points on this branch in the center...
    for point in branch.points:
        localPointX[point.id] = atX
    atX += 1

    # ... and finally place points in branches coming off to the right.
    for rightBranch in childBranchesRight:
        childPointX = _pointXFromBranch(rightBranch, branchIsFiloMap, filoDist)
        if len(childPointX) > 0:
            _fillWithOffset(localPointX, childPointX, atX)
            atX += math.floor(max(childPointX.values())) + 1

    return localPointX


# Return a mapping of point ID -> X position, for all points in a tree.
def _calculatePointX(tree, branchIsFiloMap, filoDist):
    assert tree.rootPoint is not None
    pointX = {}

    # Where we're up to having placed children
    atX = 0

    for branch in tree.rootPoint.children:
        # Get X for our child...
        childPointX = _pointXFromBranch(branch, branchIsFiloMap, filoDist)
        if len(childPointX) > 0:
            # ...and offset by how far we are:
            _fillWithOffset(pointX, childPointX, atX)
            atX += max(childPointX.values())

    # Set X position for root to the average of child branches.
    childX = []
    for b in tree.rootPoint.children:
        if len(b.points) > 0:
            childX.append(pointX[b.points[0].id])
    pointX[tree.rootPoint.id] = np.mean(childX)
    return pointX


# Return a mapping of point ID -> Y position, for all points downstream from a branch.
def _pointYFromBranch(collector, branchIsFiloMap, branch, yAt):
    # Filopodia drawn horizontally, not vertically.
    if branchIsFiloMap[branch.id]:
        for point in branch.points:
            collector[point.id] = yAt
        return

    # Otherwise, draw points upwards based of world length.
    lengths = branch.cumulativeWorldLengths()
    for point, dist in zip(branch.points, lengths):
        collector[point.id] = yAt + dist
        for childBranch in point.children:
            _pointYFromBranch(collector, branchIsFiloMap, childBranch, yAt + dist)


# Return a mapping of point ID -> Y position, for all points in a tree.
def _calculatePointY(tree, branchIsFiloMap):
    assert tree.rootPoint is not None
    pointY = {}
    pointY[tree.rootPoint.id] = 0
    for branch in tree.rootPoint.children:
        _pointYFromBranch(pointY, branchIsFiloMap, branch, 0)
    return pointY


# Calculate X and Y positions for all points within a tree.
def calculatePositions(tree, branchIDToFiloTypeMap=None, filoDist=10):
    # First calculate branch types if it hasn't been done yet:
    if branchIDToFiloTypeMap is None:
        ftArray, _, _ , _, _, _ = addedSubtractedTransitioned([tree], filoDist=filoDist)
        filoTypes = ftArray[0]
        branchIDList = util.sortedBranchIDList([tree])
        branchIDToFiloTypeMap = {}
        for i in range(len(branchIDList)):
            branchIDToFiloTypeMap[branchIDList[i]] = filoTypes[i]

    # Next, simplify into a mapping of whether each branch is a filo (horizontal) or not (vertical)
    branchIsFiloMap = {}
    for id, filoType in branchIDToFiloTypeMap.items():
        branchIsFiloMap[id] = (filoType == FiloType.INTERSTITIAL or filoType == FiloType.TERMINAL)

    # Finally, calculate both X and Y positions
    pointX = _calculatePointX(tree, branchIsFiloMap, filoDist)
    pointY = _calculatePointY(tree, branchIsFiloMap)
    return pointX, pointY

def calculateAllPositions(trees, filoTypes, branchIDList, filoDist=10):
    allX, allY = [], []
    for tree, treeFiloTypes in zip(trees, filoTypes):
        branchIDToFiloTypeMap = {}
        for i, id in enumerate(branchIDList):
            branchIDToFiloTypeMap[id] = treeFiloTypes[i]
        treeX, treeY = calculatePositions(tree, branchIDToFiloTypeMap, filoDist)
        allX.append(treeX)
        allY.append(treeY)
    return allX, allY
