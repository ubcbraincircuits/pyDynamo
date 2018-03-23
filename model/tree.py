"""
.. module:: tree
"""
import attr
import numpy as np
import util

from util import SAVE_META

@attr.s
class Transform:
    """Affine transform from pixel to world space."""

    rotation = attr.ib(default=attr.Factory(lambda: np.eye(3)), cmp=False, metadata=SAVE_META)
    """Rotation to apply to (x, y, z)."""

    translation = attr.ib(default=attr.Factory(lambda: np.array([0.0, 0.0, 0.0])), cmp=False, metadata=SAVE_META)
    """ (x, y, z) Translation to move all the points by."""

    scale = attr.ib(default=attr.Factory(lambda: np.array([1.0, 1.0, 1.0])), cmp=False, metadata=SAVE_META)
    """ (sX, sY, sZ) Scaling factors to multiply each axis by."""

@attr.s
class Point():
    """Node in the tree, a point in 3D space."""

    id = attr.ib(metadata=SAVE_META)
    """Identifier of point, can be shared across stacks."""

    location = attr.ib(metadata=SAVE_META)
    """Node position as an (x, y, z) tuple."""

    parentBranch = attr.ib(default=None, repr=False, cmp=False)
    """Branch this point belongs to"""

    annotation = attr.ib(default="", cmp=False, metadata=SAVE_META)
    """Text annotation for node."""

    children = attr.ib(default=attr.Factory(list))
    """Branches coming off the node."""

    hilighted = attr.ib(default=None, cmp=False)
    """Not sure...? Isn't used... """

    def isRoot(self):
        """Whether this point represents the root of the whole tree."""
        return self.parentBranch is None

    def indexInParent(self):
        # """How far along the branch this point sits, 0 = first point after branch point."""
        return self.parentBranch.indexForPoint(self)

@attr.s
class Branch():
    """Single connected branch on a Tree"""

    id = attr.ib(metadata=SAVE_META)
    """Identifier of a branch, can be shared across stacks."""

    _parentTree = attr.ib(default=None, repr=False, cmp=False)
    """Tree the branch belongs to"""

    parentPoint = attr.ib(default=None, repr=False, cmp=False, metadata=SAVE_META)
    """Node this branched off, or None for root branch"""

    points = attr.ib(default=attr.Factory(list), metadata=SAVE_META)
    """Points along this dendrite branch, in order."""

    isEnded = attr.ib(default=False, cmp=False)
    """Not sure...? Isn't used... """

    colorData = attr.ib(default=None, cmp=False) # Not used yet
    """Not sure...? Isn't used... """

    reparentTo = attr.ib(default=None, metadata=SAVE_META)
    """HACK - document"""

    def indexInParent(self):
        """Ordinal number of branch within the tree it is owned by."""
        return self._parentTree.branches.index(self)

    def indexForPoint(self, pointTarget):
        """Given a point, return how far along the branch it sits."""
        for idx, point in enumerate(self.points):
            if point.id == pointTarget.id:
                return idx
        return -1

    def isEmpty(self):
        """Whether the branch has no points other than the branch point."""
        return len(self.points) == 0

    def isAxon(self, axonLabel='axon'):
        """Whether the branch is labelled as the axon."""
        return util.lastPointWithLabelIdx([self.parentPoint] + self.points, axonLabel) >= 0

    def isBasal(self, basalLabel='basal'):
        return util.lastPointWithLabelIdx([self.parentPoint] + self.points, basalLabel) >= 0

    def hasChildren(self):
        """True if any point on the branch has child branches coming off it."""
        return _lastPointWithChildren(self.points) > -1

    def isFilo(self, maxLength):
        """A branch is considered a Filo if it has no children, not a lamella, and not too long.

        :returns: Tuple pair (whether it is a Filo, total length of the branch)"""
        # If it has children, it's not a filo
        if self.hasChildren():
            return False, 0
        # If it has a lamella, it's not a filo
        if _lastPointWithLabel(self.points, 'lam') > -1:
            return False, 0
        totalLength, _ = self.worldLengths()
        return totalLength < maxLength, totalLength

    def addPoint(self, point):
        """Appends a point at the end of the branch.

        :returns: the index of the new point."""
        self.points.append(point)
        point.parentBranch = self
        return len(self.points) - 1

    def insertPointBefore(self, point, index):
        """Appends a point within a branch.

        :returns: the index of the new point."""
        self.points.insert(index, point)
        point.parentBranch = self
        return index

    def removePointLocally(self, point):
        """Remove a single point from the branch, leaving points before and after.

        :returns: The point before this one"""
        if point not in self.points:
            print ("Deleting point not in the branch? Whoops")
            return1
        index = self.points.index(point)
        self.points.remove(point)
        return self.parentPoint if index == 0 else self.points[index - 1]

    def setParentPoint(self, parentPoint):
        """Sets the parent point for this branch, and adds the branch to its parent's children."""
        self.parentPoint = parentPoint
        self.parentPoint.children.append(self)

    def worldLengths(self, fromIdx=0):
        """Returns world length of the branch, plus the length to the last branch point.

        :returns: (totalLength, totalLength to last branch)
        """
        pointsWithRoot = [self.parentPoint] + self.points
        pointsWithRoot = pointsWithRoot[fromIdx:]
        x, y, z = self._parentTree.worldCoordPoints(pointsWithRoot)
        lastBranchPoint = _lastPointWithChildren(pointsWithRoot)
        totalLength, totalLengthToLastBranch = 0, 0
        for i in range(len(x) - 1):
            edgeDistance = util.deltaSz((x[i], y[i], z[i]), (x[i+1], y[i+1], z[i+1]))
            totalLength += edgeDistance
            if i < lastBranchPoint:
                totalLengthToLastBranch += edgeDistance
        return totalLength, totalLengthToLastBranch

    def cumulativeWorldLengths(self):
        """Calculate the length to all points along the branch.

        :returns: List of cumulative lengths, how far along the branch to get to each point."""
        pointsWithRoot = [self.parentPoint] + self.points
        x, y, z = self._parentTree.worldCoordPoints(pointsWithRoot)
        cumulativeLength, lengths = 0, []
        for i in range(len(x) - 1):
            edgeDistance = util.deltaSz((x[i], y[i], z[i]), (x[i+1], y[i+1], z[i+1]))
            cumulativeLength += edgeDistance
            lengths.append(cumulativeLength)
        return lengths

@attr.s
class Tree():
    """3D Tree structure."""

    rootPoint = attr.ib(default=None, metadata=SAVE_META)
    """Soma, initial start of the main branch."""

    branches = attr.ib(default=attr.Factory(list), metadata=SAVE_META)
    """All branches making up this dendrite tree."""

    transform = attr.ib(default=attr.Factory(Transform))
    """Conversion for this tree from pixel to world coordinates."""

    # HACK - make faster, index points by ID
    def getPointByID(self, pointID):
        """Given the ID of a point, find the point object that matches."""
        for point in self.flattenPoints():
            if point.id == pointID:
                return point
        return None

    def getBranchByID(self, branchID):
        """Given the ID of a branch, find the branch object that matches."""
        for branch in self.branches:
            if branch.id == branchID:
                return branch
        return None

    def addBranch(self, branch):
        """Adds a branch to the tree.

        :returns: Index of branch within the tree."""
        self.branches.append(branch)
        branch._parentTree = self
        return len(self.branches) - 1

    def removeBranch(self, branch):
        """Removes a branch from the tree - assumes all points already removed."""
        if branch not in self.branches:
            print ("Deleting branch not in the tree? Whoops")
            return
        if len(branch.points) > 0:
            print ("Removing a branch that still has stuff on it? use uiState.removeBranch.")
            return
        self.branches.remove(branch)

    def removePointByID(self, pointID):
        """Removes a single point from the tree, identified by ID."""
        pointToRemove = self.getPointByID(pointID)
        if pointToRemove is not None:
            return pointToRemove.parentBranch.removePointLocally(pointToRemove)
        else:
            return None

    def movePoint(self, pointID, newLocation, moveDownstream=False):
        """Moves a point to a new loction, optionally also moving all downstream points by the same.

        :param pointID: ID of point to move.
        :param newLocation: (x, y, z) tuple to move it to.
        :param moveDownstream: Boolean flag of whether to move all child points and points later in the branch.
        """
        pointToMove = self.getPointByID(pointID)
        assert pointToMove is not None, "Trying to move an unknown point ID"
        delta = util.locationMinus(newLocation, pointToMove.location)
        if moveDownstream:
            self._recursiveMovePointDelta(pointToMove, delta)
        else:
            # Non-recursive, so just move this one point:
            pointToMove.location = newLocation

    def flattenPoints(self):
        """Returns all points in the tree, as a single list."""
        if self.rootPoint is None:
            return []
        result = [self.rootPoint]
        for branch in self.branches:
            result.extend(branch.points)
        return result

    def closestPointTo(self, targetLocation, zFilter=False):
        """Given a position, find the point closest to it.

        :param targetLocation: (x, y, z) location tuple.
        :param zFilter: If true, only items on the same zStack are considered.
        :returns: Point object of point closest to the target location."""
        # TODO - need to fix for world coordinates?
        closestDist, closestPoint = None, None
        for point in self.flattenPoints():
            if zFilter and point.location[2] != targetLocation[2]:
                continue
            dist = util.deltaSz(targetLocation, point.location)
            if closestDist is None or dist < closestDist:
                closestDist, closestPoint = dist, point
        return closestPoint

    def worldCoordPoints(self, points):
        """Convert image pixel (x, y, z) to a real-world (x, y, z) position."""
        x, y, z = [], [], []
        # HACK: Enter values on load?
        self.transform.scale = np.array([0.3070, 0.3070, 1.5])
        for p in points:
            pAt = np.array(p.location)
            pAt = np.matmul(self.transform.rotation, pAt.T).T
            pAt = (pAt + self.transform.translation) * self.transform.scale
            x.append(pAt[0]), y.append(pAt[1]), z.append(pAt[2])
        return x, y, z

    def _recursiveMovePointDelta(self, point, delta):
        """Recursively move a point, plus all its children and later neighbours."""
        point.location = util.locationPlus(point.location, delta)
        # First, move any branches coming off this point, by moving their first point
        for branch in self.branches:
            if branch.parentPoint.id == point.id and len(branch.points) > 0:
                self._recursiveMovePointDelta(branch.points[0], delta)
        # Next, move the next point on this branch (which will recursively do likewise...)
        if point.parentBranch is not None:
            nextIdx = point.parentBranch.indexForPoint(point) + 1
            assert nextIdx > 0, "Moving a point on a branch that doesn't know the point is there?"
            if nextIdx < len(point.parentBranch.points):
                self._recursiveMovePointDelta(point.parentBranch.points[nextIdx], delta)


### Branch utilities

# Return the index of the last point with child branches, or -1 if not found.
def _lastPointWithChildren(points):
    lastPointIdx = -1
    for i, point in enumerate(points):
        if len(point.children) > 0:
            lastPointIdx = i
    return lastPointIdx

# Return the index of the last point whose label contains given text, or -1 if not found.
# TODO - move somewhere common.
def _lastPointWithLabel(points, label):
    lastPointIdx = -1
    for i, point in enumerate(points):
        if point.annotation.find(label) != -1:
            lastPointIdx = i
    return lastPointIdx

#
# Debug formatting for converting trees to string representation
#
def printPoint(tree, point, pad="", isFirst=False):
    print (pad + ("-> " if isFirst else "   ") + str(point))
    pad = pad + "   "
    for branch in tree.branches:
        if branch.parentPoint == point:
            printBranch(tree, branch, pad)

def printBranch(tree, branch, pad=""):
    if branch.points[0] == branch.parentPoint:
        print ("BRANCH IS OWN PARENT? :(")
        return
    print (pad + "-> Branch " + branch.id + " = ")
    for point in branch.points:
        printPoint(tree, point, pad)

def printTree(tree):
    printPoint(tree, tree.rootPoint)
