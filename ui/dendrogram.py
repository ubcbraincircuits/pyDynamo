import math
import numpy as np

from analysis import addedSubtractedTransitioned
from model import FiloType
import util

FILO_DIST = 10

def _fillWithOffset(toMap, fromMap, offset):
    for id, value in fromMap.items():
        toMap[id] = value + offset

# Return a mapping of point ID -> X position, for all points downstream from a branch.
def _pointXFromBranch(branch, branchIsFiloMap):
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
        childPointX = _pointXFromBranch(leftBranch, branchIsFiloMap)
        _fillWithOffset(localPointX, childPointX, atX)
        atX += math.floor(max(childPointX.values())) + 1

    # ... then place filopodia points sideways based off length...
    nextOffset = -1
    for filo in childFilo:
        lengths = filo.cumulativeWorldLengths()
        for point, dist in zip(filo.points, lengths):
            localPointX[point.id] = atX + (dist/FILO_DIST) * nextOffset * 0.9
        nextOffset *= -1 # alternate on left vs right.

    # ... then place all the points on this branch in the center...
    for point in branch.points:
        localPointX[point.id] = atX
    atX += 1

    # ... and finally place points in branches coming off to the right.
    for rightBranch in childBranchesRight:
        childPointX = _pointXFromBranch(rightBranch, branchIsFiloMap)
        _fillWithOffset(localPointX, childPointX, atX)
        atX += math.floor(max(childPointX.values())) + 1

    return localPointX


# Return a mapping of point ID -> X position, for all points in a tree.
def _calculatePointX(tree, branchIsFiloMap):
    assert tree.rootPoint is not None
    pointX = {}

    # Where we're up to having placed children
    atX = 0

    for branch in tree.rootPoint.children:
        # Get X for our child...
        childBranchX = _pointXFromBranch(branch, branchIsFiloMap)
        # ...and offset by how far we are:
        _fillWithOffset(pointX, childBranchX, atX)
        # _fillWithOffset(  filoX,   childFiloX, atX)
        atX += max(childBranchX.values())

    # Set X position for root to the average of child branches.
    meanChildX = np.mean([pointX[b.points[0].id] for b in tree.rootPoint.children])
    pointX[tree.rootPoint.id] = meanChildX
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
def calculatePositions(tree, branchIDToFiloTypeMap=None):
    # First calculate branch types if it hasn't been done yet:
    if branchIDToFiloTypeMap is None:
        ftArray, _, _ , _, _, _ = addedSubtractedTransitioned([tree], filoDist=FILO_DIST)
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
    pointX = _calculatePointX(tree, branchIsFiloMap)
    pointY = _calculatePointY(tree, branchIsFiloMap)
    return pointX, pointY
