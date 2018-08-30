import attr
import math
import numpy as np

from .tree.branch import Branch
from .tree.point import Point
from .tree.tree import Tree

from util import snapToRange, normDelta, dotDelta, deltaSz, SAVE_META

@attr.s
class UIState():
    # Full state this belongs within
    _parent = attr.ib(default=None)

    # Tree being shown in the UI.
    _tree = attr.ib(default=None)

    # Path of image, use ImageCache to obtain actual volume
    imagePath = attr.ib(default=None)

    # Whether the stack is shown or hidden
    isHidden = attr.ib(default=False, metadata=SAVE_META)

    # ID of currently active point
    currentPointID = attr.ib(default=None)

    # Cache of the current point
    _currentPointCache = attr.ib(default=None)

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

    # UI Option for whether to flatten all z planes into one image.
    zProject = attr.ib(default=False)

    # UI Option for whether or not to show higlighted points in a different color
    showHilighted = attr.ib(default=False)

    # UI Option for whether or not to show *all* the points and dendrites
    hideAll = attr.ib(default=False)

    # (lower-, upper-) bounds for intensities to show
    colorLimits = attr.ib(default=(0, 1), metadata=SAVE_META)

    def parent(self):
        return self._parent

    def currentBranch(self):
        # No branches, or no current point:
        if len(self._tree.branches) == 0 or self._currentPointCache is None:
            return None
        if self._currentPointCache.parentBranch is not None:
            return self._currentPointCache.parentBranch
        else:
            # Root point, to place on first branch.
            return self._tree.branches

    def currentPoint(self):
        return self._currentPointCache

    def deleteBranch(self, branch):
        # Need to remove backwards, as we're removing while we're iterating
        reverseIndex = list(reversed(range(len(branch.points))))
        for i in reverseIndex:
            self.deletePointByID(branch.points[i].id)
        self._tree.removeBranch(branch)
        self._currentPointCache = None

    def changeBrightness(self, lowerDelta, upperDelta):
        self.colorLimits = (
            snapToRange(self.colorLimits[0] + lowerDelta, 0, self.colorLimits[1] - 0.001),
            snapToRange(self.colorLimits[1] + upperDelta, self.colorLimits[0] + 0.001, 1),
        )

    ## Local actions to apply only to this stack.

    def selectPointByID(self, selectedID, isMove=False):
        self._currentPointCache = self._tree.getPointByID(selectedID)
        if self._currentPointCache is not None:
            self.currentPointID = self._currentPointCache.id
            self.isMoving = isMove
        else:
            if not isMove:
                self.currentPointID = None
                self.isMoving = False
        self.isReparenting = False

    def addPointToCurrentBranchAndSelect(self, location, newPointID=None, newBranchID=None):
        newPoint = Point(self.maybeCreateNewID(newPointID), location)
        if self._tree.rootPoint is None:
            self._tree.rootPoint = newPoint
        else:
            branch = self.currentBranch()
            if branch is None:
                if len(self._tree.branches) == 0:
                    # First branch, so create it
                    newBranchID = self.maybeCreateBranchID(newBranchID)
                    branch = Branch(newBranchID, self._tree)
                    branch.setParentPoint(self._tree.rootPoint)
                    self._tree.addBranch(branch)
                else:
                    # We have branches, but none selected, so skip this stack.
                    return None
            branch.addPoint(newPoint)
            self._currentPointCache = newPoint
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
        self.currentPointID = newPoint.id
        self._currentPointCache = newPoint
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
        self._currentPointCache = newPoint
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
        self.currentPointID = newPoint.id
        self._currentPointCache = newPoint

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
