import attr
import math

from .tree import *

from util import snapToRange, normDelta, dotDelta, deltaSz

@attr.s
class UIState():
    # Full state this belongs within
    _parent = attr.ib(default=None)

    # Tree being shown in the UI.
    _tree = attr.ib(default=None)

    # Currently active branch, indexed by position in list of branches.
    currentBranchIndex = attr.ib(default=-1)

    # Currently active point, indexed by position in list of nodes.
    currentPointIndex = attr.ib(default=-1)

    # UI Option for whether or not to show annotations.
    showAnnotations = attr.ib(default=True)

    # UI Option for whether or not to show all branches, or just the nearby ones.
    drawAllBranches = attr.ib(default=False)

    # (lower-, upper-) bounds for intensities to show
    colorLimits = attr.ib(default=(0, 1))

    def parent(self):
        return self._parent

    def currentBranch(self):
        if self.currentBranchIndex == -1:
            return None
        return self._tree.branches[self.currentBranchIndex]

    def currentPoint(self):
        if self.currentPointIndex == -1:
            return self._tree.rootPoint
        return self.currentBranch().points[self.currentPointIndex]

    def deleteBranch(self, branch):
        # Need to remove backwards, as we're removing while we're iterating
        reverseIndex = list(reversed(range(len(branch.points))))
        for i in reverseIndex:
            self.deletePoint(branch.points[i])
        self._tree.removeBranch(branch)

    def changeBrightness(self, lowerDelta, upperDelta):
        self.colorLimits = (
            snapToRange(self.colorLimits[0] + lowerDelta, 0, self.colorLimits[1] - 0.001),
            snapToRange(self.colorLimits[1] + upperDelta, self.colorLimits[0] + 0.001, 1),
        )

    # TODO - move elsewhere?
    def closestPointInZPlane(self, location):
        closestPoint = None
        closestDist = None
        for point in self._tree.flattenPoints():
            if point.location[2] != location[2]:
                continue
            dist = deltaSz(location, point.location)
            if closestDist is None or dist < closestDist:
                closestPoint = point
                closestDist = dist
        return closestPoint, closestDist

    ##
    ## IN THE PROCESS OF BEING MOVED TO FULL_STATE_ACTIONS:
    ##
    def selectPoint(self, newPoint):
        if newPoint is None or newPoint == self._tree.rootPoint:
            self.currentBranchIndex = -1
            self.currentPointIndex = -1
        else:
            branch = newPoint.parentBranch
            if branch in self._tree.branches and newPoint in branch.points:
                self.currentBranchIndex = self._tree.branches.index(branch)
                self.currentPointIndex = branch.points.index(newPoint)
            else:
                print ("Can't find point... %s" % newPoint)

    def addPointToCurrentBranchAndSelect(self, location):
        if self._tree.rootPoint is None:
            self._tree.rootPoint = Point(location)
            return
        if self.currentBranchIndex == -1:
            self.currentBranchIndex = self._tree.addBranch(Branch(parentPoint=self._tree.rootPoint))
        self.currentPointIndex = self.currentBranch().addPoint(Point(location))

    def addPointToNewBranchAndSelect(self, location):
        newBranch = Branch(parentPoint=self.currentPoint())
        self.currentBranchIndex = self._tree.addBranch(newBranch)
        self.currentPointIndex = self.currentBranch().addPoint(Point(location))

    def addPointMidBranchAndSelect(self, location):
        branch = self.currentBranch()
        if branch is None:
            return

        currentPointAt = self.currentPoint().location
        newPoint = Point(location)
        newPointIndex = None

        if len(branch.points) < 2:
            # Branch is either empty or has only one point, so add new point at start:
            newPointIndex = 0
        elif self.currentPointIndex == len(branch.points) - 1:
            # Current = last point in branch, so add new point before it:
            newPointIndex = self.currentPointIndex
        else:
            beforePoint = branch.parentPoint if self.currentPointIndex == 0 else branch.points[self.currentPointIndex - 1]
            afterPoint = branch.points[self.currentPointIndex + 1]
            if beforePoint is None:
                return # Whoops, ignore.
            beforeDelta = normDelta(beforePoint.location, currentPointAt)
            afterDelta = normDelta(afterPoint.location, currentPointAt)
            currDelta = normDelta(location, currentPointAt)
            if (dotDelta(beforeDelta, currDelta) > dotDelta(afterDelta, currDelta)):
                newPointIndex = self.currentPointIndex
            else:
                newPointIndex = self.currentPointIndex + 1

        self.currentPointIndex = branch.insertPointBefore(newPoint, newPointIndex)
        # Returns old branch, and next point after
        return branch, None if newPointIndex == len(branch.points) else branch.points[newPointIndex]

    def deletePoint(self, point):
        for branch in self._tree.branches:
            if branch.parentPoint == point:
                self.deleteBranch(branch)
        oldBranch = point.parentBranch
        newPoint = oldBranch.removePointLocally(point)
        point.parentBranch = None
        self.selectPoint(newPoint)
