"""
.. module:: tree
"""
import attr
import numpy as np
import util

from util import SAVE_META

from .branch import Branch
from .point import Point
from .transform import Transform


@attr.s
class Tree():
    """3D Tree structure."""

    rootPoint = attr.ib(default=None, metadata=SAVE_META)
    """Soma, initial start of the main branch."""

    branches = attr.ib(default=attr.Factory(list), metadata=SAVE_META)
    """All branches making up this dendrite tree."""

    transform = attr.ib(default=attr.Factory(Transform), metadata=SAVE_META)
    """Conversion for this tree from pixel to world coordinates."""

    _parentState = attr.ib(default=None, repr=False, cmp=False)
    """UI State this belongs to."""

    # HACK - make faster, index points by ID
    def getPointByID(self, pointID, includeDisconnected=False):
        """Given the ID of a point, find the point object that matches."""
        for point in self.flattenPoints(includeDisconnected):
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
            if pointToRemove.parentBranch is None:
                assert pointToRemove.id == self.rootPoint.id
                if len(self.branches) == 0:
                    self.rootPoint = None
                else:
                    print ("You can't remove the soma if other points exist - please remove those first!")
                    return None
            else:
                return pointToRemove.parentBranch.removePointLocally(pointToRemove)
        else:
            return None

    def reparentPoint(self, childPoint, newParent, newBranchID=None):
        """Changes a point (and its later siblings) to a new branch off the given parent."""
        if childPoint.parentBranch is None:
            # should not be allowed, skip
            print ("Can't reparent the root! Ignoring...")
            return None
        oldBranch, newBranch = childPoint.parentBranch, newParent.parentBranch

        if newParent.isLastInBranch() and not newParent.isRoot():
            # Append the child point to the new parent's branch
            atIdx = childPoint.indexInParent()
            while len(oldBranch.points) > atIdx:
                toMove = oldBranch.points[atIdx]
                oldBranch.removePointLocally(toMove)
                newBranch.addPoint(toMove)
            return None
        else:
            # Otherwise, move a whole branch - creating a new one if needed
            newBranch = childPoint.parentBranch
            newID = None
            atIdx = childPoint.indexInParent()

            if atIdx > 0: # need to split the old branch
                newID = newBranchID if newBranchID is not None else self._parentState._parent.nextBranchID()
                newBranch = Branch(id=newID)
                while len(oldBranch.points) > atIdx:
                    toMove = oldBranch.points[atIdx]
                    oldBranch.removePointLocally(toMove)
                    newBranch.addPoint(toMove)
                self.addBranch(newBranch)
            newBranch.setParentPoint(newParent)
            return newID

    def movePoint(self, pointID, newLocation, downstream=False):
        """Moves a point to a new loction, optionally also moving all downstream points by the same.

        :param pointID: ID of point to move.
        :param newLocation: (x, y, z) tuple to move it to.
        :param moveDownstream: Boolean flag of whether to move all child points and points later in the branch.
        """
        pointToMove = self.getPointByID(pointID)
        assert pointToMove is not None, "Trying to move an unknown point ID"
        delta = util.locationMinus(newLocation, pointToMove.location)
        if downstream:
            self._recursiveMovePointDelta(pointToMove, delta)
        else:
            # Non-recursive, so just move this one point:
            pointToMove.location = newLocation

    def flattenPoints(self, includeDisconnected=False):
        """Returns all points in the tree, as a single list."""
        if self.rootPoint is None:
            return []
        if not includeDisconnected:
            return self.rootPoint.flattenSubtreePoints()
        # Use this version when the parent/child tree structure hasn't been set up:
        points = [self.rootPoint]
        for b in self.branches:
            points.extend(b.points)
        return points

    def continueParentBranchIfFirst(self, point):
        """If point is first in its branch, change it to extend its parent."""
        if point is None or point.indexInParent() > 0 or point.isRoot():
            return # Moving right along, nothing to see here...

        branch = point.parentBranch
        parent = branch.parentPoint
        assert parent is not None
        if parent.isRoot():
            return # All branches are children of the root...

        parentIdx = parent.indexInParent()
        parentsBranch = parent.parentBranch
        afterParentPoints = parentsBranch.points[parentIdx+1:]
        parentsBranch.points = parentsBranch.points[:parentIdx+1]
        for sibling in branch.points:
            parentsBranch.addPoint(sibling)

        branch.points = []
        if len(afterParentPoints) > 0:
            # Move after parent to new branch:
            for afterParentPoint in afterParentPoints:
                branch.addPoint(afterParentPoint)
        else:
            # Otherwise, remove from tree completely
            self.removeBranch(branch)
            parent.children.remove(branch)

    def updateAllPrimaryBranches(self, point=None):
        """For all branching points, make the longest branch continue the parent branch."""
        if point is None:
            point = self.rootPoint

        # Step 1: find the longest child, see if it's longer than the continuation
        nextPoint = point.nextPointInBranch(noWrap=True)
        nextDist = None if nextPoint is None else nextPoint.longestDistanceToLeaf()
        longestContinuation = (None, nextDist)
        for i, childBranch in enumerate(point.children):
            if len(childBranch.points) > 0:
                childPoint = childBranch.points[0]
                childDist = childPoint.longestDistanceToLeaf()
                if nextDist is None or nextDist < childDist:
                    nextPoint, nextDist = childPoint, childDist
        if nextDist is not None:
            self.continueParentBranchIfFirst(nextPoint)

        # Step 2: Normalize by sorting branches by remaining length:
        def _branchDistRemaining(branch):
            if len(branch.points) > 0:
                return -branch.points[0].longestDistanceToLeaf()
            return 0
        point.children.sort(key=_branchDistRemaining)

        # Step 3: Recurse down tree:
        nextPoint = point.nextPointInBranch(noWrap=True)
        if nextPoint is not None:
            self.updateAllPrimaryBranches(nextPoint)
        for childBranch in point.children:
            if len(childBranch.points) > 0:
                self.updateAllPrimaryBranches(childBranch.points[0])


    def closestPointTo(self, targetLocation, zFilter=False):
        """Given a position in the volume, find the point closest to it in image space.

        :param targetLocation: (x, y, z) location tuple.
        :param zFilter: If true, only items on the same zStack are considered.
        :returns: Point object of point closest to the target location."""
        closestDist, closestPoint = None, None
        for point in self.flattenPoints():
            if zFilter and round(point.location[2]) != round(targetLocation[2]):
                continue
            dist = util.deltaSz(targetLocation, point.location)
            if closestDist is None or dist < closestDist:
                closestDist, closestPoint = dist, point
        return closestPoint

    def closestPointToWorldLocation(self, targetWorldLocation):
        """Given a position in world space, find the point closest to it in world space.

        :param targetWorldLocation: (x, y, z) location tuple.
        :returns: Point object of point closest to the target location."""
        closestDist, closestPoint = None, None
        allPoints = self.flattenPoints()
        allX, allY, allZ = self.worldCoordPoints(allPoints)
        for point, loc in zip(allPoints, zip(allX, allY, allZ)):
            dist = util.deltaSz(targetWorldLocation, loc)
            if closestDist is None or dist < closestDist:
                closestDist, closestPoint = dist, point
        return closestPoint

    def worldCoordPoints(self, points):
        """Convert image pixel (x, y, z) to a real-world (x, y, z) position."""
        x, y, z = [], [], []
        globalScale = self._parentState._parent.projectOptions.pixelSizes
        for p in points:
            pAt = p
            if hasattr(p, 'location'):
                pAt = p.location
            pAt = np.array(pAt)
            pAt = np.matmul(self.transform.rotation, pAt.T).T
            pAt = (pAt + self.transform.translation) * self.transform.scale
            pAt = pAt * globalScale
            x.append(pAt[0]), y.append(pAt[1]), z.append(pAt[2])
        return x, y, z

    def spatialDist(self, p1, p2):
        """Given two points in the tree, return the 3D spatial distance"""
        x, y, z = self.worldCoordPoints([p1, p2])
        p1Location = (x[0], y[0], z[0])
        p2Location = (x[1], y[1], z[1])
        return util.deltaSz(p1Location, p2Location)

    def spatialAndTreeDist(self, p1, p2):
        """Given two points in the tree, return both the 3D spatial distance,
        as well as how far to travel along the tree."""
        path1, path2 = p1.pathFromRoot(), p2.pathFromRoot()
        lastMatch = 0
        while lastMatch < len(path1) and lastMatch < len(path2) and path1[lastMatch].id == path2[lastMatch].id:
            lastMatch += 1
        lastMatch -= 1
        path1X, path1Y, path1Z = self.worldCoordPoints(path1[lastMatch:])
        path2X, path2Y, path2Z = self.worldCoordPoints(path2[lastMatch:])
        treeDist = 0.0
        for i in range(len(path1X) - 1):
            p1 = (path1X[ i ], path1Y[ i ], path1Z[ i ])
            p2 = (path1X[i+1], path1Y[i+1], path1Z[i+1])
            treeDist += util.deltaSz(p1, p2)
        for i in range(len(path2X) - 1):
            p1 = (path2X[ i ], path2Y[ i ], path2Z[ i ])
            p2 = (path2X[i+1], path2Y[i+1], path2Z[i+1])
            treeDist += util.deltaSz(p1, p2)
        return self.spatialDist(p1, p2), treeDist

    def _recursiveMovePointDelta(self, point, delta):
        """Recursively move a point, plus all its children and later neighbours."""
        point.location = util.locationPlus(point.location, delta)
        # First, move any branches coming off this point, by moving their first point
        for branch in self.branches:
            if branch.parentPoint is not None and branch.parentPoint.id == point.id and len(branch.points) > 0:
                self._recursiveMovePointDelta(branch.points[0], delta)
        # Next, move the next point on this branch (which will recursively do likewise...)
        if point.parentBranch is not None:
            nextIdx = point.parentBranch.indexForPoint(point) + 1
            assert nextIdx > 0, "Moving a point on a branch that doesn't know the point is there?"
            if nextIdx < len(point.parentBranch.points):
                self._recursiveMovePointDelta(point.parentBranch.points[nextIdx], delta)

    def clearAndCopyFrom(self, otherTree, idMaker):
        pointMap = {}
        self.rootPoint = _clonePoint(otherTree.rootPoint, idMaker, pointMap)

        nonEmptyBranches = [branch for branch in otherTree.branches if len(branch.points) > 0]
        for branch in nonEmptyBranches:
            self.addBranch(_cloneBranch(branch, idMaker, pointMap))

        for newBranch, oldBranch in zip(self.branches, nonEmptyBranches):
            if oldBranch.parentPoint is not None:
                if oldBranch.parentPoint.id not in pointMap:
                    print ("Disconnected branch exists? Skipping")
                else:
                    newBranch.setParentPoint(pointMap[oldBranch.parentPoint.id])
            if oldBranch.reparentTo is not None:
                if oldBranch.reparentTo.id not in pointMap:
                    print ("Disconnected reparented branch exists? Skipping")
                else:
                    newBranch.reparentTo = pointMap[oldBranch.reparentTo.id]


### Cloning utilities

def _clonePoint(point, idMaker, pointMap):
    assert point.id not in pointMap
    newID = point.id if idMaker is None else idMaker.nextPointID()
    # NOTE: SWC point ID can be stored here too if needed.
    newPoint = Point(id=newID, location=point.location, radius=point.radius)
    pointMap[point.id] = newPoint
    return newPoint

def _cloneBranch(branch, idMaker, pointMap):
    newID = branch.id if idMaker is None else idMaker.nextBranchID()
    b = Branch(id=newID)
    for point in branch.points:
        b.addPoint(_clonePoint(point, idMaker, pointMap))
    return b



#
# Debug formatting for converting trees to string representation
#
def printPoint(tree, point, pad="", isFirst=False):
    print (pad + ("-> " if isFirst else "   ") + str(point))
    pad = pad + "   "
    for branch in point.children:
        if branch.parentPoint == point:
            printBranch(tree, branch, pad)

def printBranch(tree, branch, pad=""):
    if len(branch.points) > 0 and branch.points[0] == branch.parentPoint:
        print ("BRANCH IS OWN PARENT? :(")
        return
    print (pad + "-> Branch " + branch.id + " = ")
    for point in branch.points:
        printPoint(tree, point, pad)

def printTree(tree):
    printPoint(tree, tree.rootPoint)
