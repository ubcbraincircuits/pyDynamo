import attr
import math

from .tree import *

@attr.s
class UIState():
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

    # UI Option for dendrite line width
    lineWidth = attr.ib(default=3)

    def currentBranch(self):
        if self.currentBranchIndex == -1:
            return None
        return self._tree.branches[self.currentBranchIndex]

    def currentPoint(self):
        if self.currentPointIndex == -1:
            return self._tree.rootPoint
        return self.currentBranch().points[self.currentPointIndex]

    # HACK - move these to dendrite canvas actions
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
            beforeDelta = self.normDelta(beforePoint.location, currentPointAt)
            afterDelta = self.normDelta(afterPoint.location, currentPointAt)
            currDelta = self.normDelta(location, currentPointAt)
            if (self.dotDelta(beforeDelta, currDelta) > self.dotDelta(afterDelta, currDelta)):
                newPointIndex = self.currentPointIndex
            else:
                newPointIndex = self.currentPointIndex + 1

        self.currentPointIndex = branch.insertPointBefore(newPoint, newPointIndex)

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

    def deleteBranch(self, branch):
        # Need to remove backwards, as we're removing while we're iterating
        reverseIndex = list(reversed(range(len(branch.points))))
        for i in reverseIndex:
            self.deletePoint(branch.points[i])
        self._tree.removeBranch(branch)

    def deletePoint(self, point):
        for branch in self._tree.branches:
            if branch.parentPoint == point:
                self.deleteBranch(branch)
        oldBranch = point.parentBranch
        newPoint = oldBranch.removePointLocally(point)
        point.parentBranch = None
        self.selectPoint(newPoint)

    # TODO - move elsewhere?
    def closestPointInZPlane(self, location):
        closestPoint = None
        closestDist = None
        for point in self._tree.flattenPoints():
            if point.location[2] != location[2]:
                continue
            dist = self.deltaSz(location, point.location)
            if closestDist is None or dist < closestDist:
                closestPoint = point
                closestDist = dist
        return closestPoint, closestDist

    def toggleLineWidth(self):
        if self.lineWidth == 4:
            self.lineWidth = 1
        else:
            self.lineWidth += 1

    # HACK - move to common location
    def normDelta(self, p1, p2):
        x, y, z = p1[0] - p2[0], p1[1] - p2[1], p1[2] - p2[2]
        sz = math.sqrt(x*x + y*y + z*z)
        return (x/sz, y/sz, z/sz)

    def dotDelta(self, p1, p2):
        return p1[0] * p2[0] + p1[1] * p2[1] + p1[2] * p2[2]

    def deltaSz(self, p1, p2):
        x, y, z = p1[0] - p2[0], p1[1] - p2[1], p1[2] - p2[2]
        return math.sqrt(x*x + y*y + z*z)
