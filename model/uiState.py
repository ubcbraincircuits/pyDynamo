import attr
import math
import numpy as np

from .tree.branch import Branch
from .tree.point import Point
from .tree.tree import Tree

from util import snapToRange, normDelta, dotDelta, deltaSz, SAVE_META


# TODO: Move elsewhere
def normalizeImage(imageData):
    imageData = imageData.astype(np.float64) ** 0.8 # Gamma correction
    for c in range(imageData.shape[0]):
        for i in range(imageData.shape[1]):
            d = imageData[c, i]
            mn = np.percentile(d, 10)
            mx = np.max(d)
            imageData[c, i] = 255 * (d - mn) / (mx - mn)
    return np.round(imageData.clip(min=0)).astype(np.uint8)

@attr.s
class UIState():
    # Full state this belongs within
    _parent = attr.ib(default=None)

    # Tree being shown in the UI.
    _tree = attr.ib(default=None)

    # Path of image, use ImageCache to obtain actual volume
    imagePath = attr.ib(default=None)

    # ID of currently active branch
    currentBranchID = attr.ib(default=None)

    # ID of currently active point
    currentPointID = attr.ib(default=None)

    # Whether the current point is being moved (True) or just selected (False)
    isMoving = attr.ib(default=False)

    # Whether the current point is being reparented (True) or just selected (False)
    isReparenting = attr.ib(default=False)

    # UI Option for whether or not to show annotations.
    showAnnotations = attr.ib(default=False, metadata=SAVE_META)

    # UI Option for whether or not to show IDs (drawn like annotations).
    showIDs = attr.ib(default=False, metadata=SAVE_META)

    # UI Option for whether or not to show all branches, or just the nearby ones.
    drawAllBranches = attr.ib(default=False, metadata=SAVE_META)

    # UI Option for whether or not to show higlighted points in a different color
    showHilighted = attr.ib(default=False)

    # UI Option for whether or not to show *all* the points and dendrites
    hideAll = attr.ib(default=False)

    # (lower-, upper-) bounds for intensities to show
    colorLimits = attr.ib(default=(0, 1), metadata=SAVE_META)

    def parent(self):
        return self._parent

    def currentBranch(self):
        return self._tree.getBranchByID(self.currentBranchID)

    def currentImage(self):
        return self.imageVolume[self._parent.channel][self._parent.zAxisAt]

    def currentPoint(self):
        if self.currentPointID is None:
            return None
        return self._tree.getPointByID(self.currentPointID)

    def deleteBranch(self, branch):
        # Need to remove backwards, as we're removing while we're iterating
        reverseIndex = list(reversed(range(len(branch.points))))
        for i in reverseIndex:
            self.deletePointByID(branch.points[i].id)
        self._tree.removeBranch(branch)

    def changeBrightness(self, lowerDelta, upperDelta):
        self.colorLimits = (
            snapToRange(self.colorLimits[0] + lowerDelta, 0, self.colorLimits[1] - 0.001),
            snapToRange(self.colorLimits[1] + upperDelta, self.colorLimits[0] + 0.001, 1),
        )

    ## Local actions to apply only to this stack.

    def selectPointByID(self, selectedID, isMove=False):
        selectedPoint = self._tree.getPointByID(selectedID)
        if selectedPoint is not None:
            self.currentPointID = selectedID
            if selectedPoint.isRoot():
                if len(self._tree.branches) > 0:
                    self.currentBranchID = self._tree.branches[0].id
                else:
                    self.currentBranchID = None
            else:
                self.currentBranchID = selectedPoint.parentBranch.id
            self.isMoving = isMove
        else:
            if not isMove:
                self.currentPointID = None
                self.currentBranchID = None
                self.isMoving = False
        self.isReparenting = False


    def addPointToCurrentBranchAndSelect(self, location, newPointID=None, newBranchID=None):
        newPoint = Point(self.maybeCreateNewID(newPointID), location)
        if self._tree.rootPoint is None:
            self._tree.rootPoint = newPoint
        else:
            if self.currentBranch() is None:
                if len(self._tree.branches) == 0:
                    # First branch, so create it
                    newBranchID = self.maybeCreateBranchID(newBranchID)
                    newBranch = Branch(newBranchID, self._tree)
                    newBranch.setParentPoint(self._tree.rootPoint)
                    self._tree.addBranch(newBranch)
                    self.currentBranchID = newBranch.id
                else:
                    # We have branches, but none selected, so skip this stack.
                    return None
            self.currentBranch().addPoint(newPoint)
            self.currentPointID = newPoint.id
        return newPoint

    def addPointToNewBranchAndSelect(self, location, newPointID=None, newBranchID=None):
        if self.currentPoint() is None:
            return None, None

        # Make new branch from current point.
        newBranchID = self.maybeCreateBranchID(newBranchID)
        newBranch = Branch(newBranchID, self._tree)
        newBranch.setParentPoint(self.currentPoint())
        # Add new point to it.
        newPoint = Point(self.maybeCreateNewID(newPointID), location)
        newBranch.addPoint(newPoint)
        # And update the tree.
        self._tree.addBranch(newBranch)
        self.currentBranchID = newBranch.id
        self.currentPointID = newPoint.id
        return newPoint, newBranch

    def addPointMidBranchAndSelect(self, location):
        branch = self.currentBranch()
        if branch is None:
            return None, False
        currentPoint = self.currentPoint()
        if currentPoint is None:
            return None, False
        currentPointIndex = branch.indexForPoint(self.currentPoint())
        newPoint = Point(self.maybeCreateNewID(None), location)
        newPointIndex = None
        isAfter = False

        if currentPointIndex == -1:
            # Selected the root point in the first branch, so add before the first point
            newPointIndex = 0
            isAfter = True
        elif len(branch.points) < 2:
            # Branch is either empty or has only one point, so add new point at start:
            newPointIndex = 0
            isAfter = (len(branch.points) == 0)
        elif currentPointIndex == len(branch.points) - 1:
            # Current = last point in branch, so add new point before it:
            newPointIndex = currentPointIndex
            isAfter = False
        else:
            beforePoint = branch.parentPoint if currentPointIndex == 0 else branch.points[currentPointIndex - 1]
            afterPoint = branch.points[currentPointIndex + 1]
            if beforePoint is None:
                return None, False # Something's gone wrong, ignore

            beforeDelta = normDelta(beforePoint.location, currentPoint.location)
            afterDelta = normDelta(afterPoint.location, currentPoint.location)
            currDelta = normDelta(location, currentPoint.location)
            isAfter = (dotDelta(beforeDelta, currDelta) < dotDelta(afterDelta, currDelta))
            newPointIndex = currentPointIndex + (1 if isAfter else 0)

        branch.insertPointBefore(newPoint, newPointIndex)
        self.currentPointID = newPoint.id
        # Returns added point, and whether it was before or after the source
        return newPoint, isAfter

    def addKnownPointMidBranchAndSelect(self, location, branch, source, isAfter, newPointID):
        newPoint = Point(newPointID, location)
        newIndex = branch.indexForPoint(source)
        if newIndex == -1:
            assert source.isRoot()
            newIndex = 0
        elif isAfter:
            newIndex += 1
        branch.insertPointBefore(newPoint, newIndex)
        self.currentBranchID = branch.id
        self.currentPointID = newPoint.id

    def deletePointByID(self, pointID):
        if pointID != self._tree.rootPoint.id:
            for branch in self._tree.branches:
                if branch.parentPoint is not None and branch.parentPoint.id == pointID:
                    self.deleteBranch(branch)
        return self._tree.removePointByID(pointID)

    def endMove(self, newLocation, downstream):
        # assert self.isMoving and self.currentPointID is not None, "Can only end a move if actually moving a point"
        if self.isMoving and self.currentPointID is not None:
            self._tree.movePoint(self.currentPointID, newLocation, downstream)


    def maybeCreateNewID(self, newPointID):
        return newPointID if newPointID is not None else self._parent.nextPointID()

    def maybeCreateBranchID(self, newBranchID):
        return newBranchID if newBranchID is not None else self._parent.nextBranchID()
