from __future__ import annotations

"""
.. module:: tree
"""
import attr
import numpy as np

from typing import List

import pydynamo_brain.util as util
from pydynamo_brain.util import SAVE_META, Point3D

from typing import Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

from .branch import Branch
from .point import Point
from .transform import Transform

if TYPE_CHECKING:
    from pydynamo_brain.model import FullState, UIState

@attr.s
class Tree():
    """3D Tree structure."""

    rootPoint: Optional[Point] = attr.ib(default=None, metadata=SAVE_META)
    """Soma, initial start of the main branch."""

    branches: List[Branch] = attr.ib(default=attr.Factory(list), metadata=SAVE_META)
    """All branches making up this dendrite tree."""

    transform: Transform = attr.ib(default=attr.Factory(Transform), metadata=SAVE_META)
    """Conversion for this tree from pixel to world coordinates."""

    _parentState: Optional[UIState] = attr.ib(default=None, repr=False, eq=False, order=False)
    """UI State this belongs to."""

    # HACK - make faster, index points by ID
    def getPointByID(self, pointID: str, includeDisconnected: bool=False) -> Optional[Point]:
        """Given the ID of a point, find the point object that matches."""
        for point in self.flattenPoints(includeDisconnected):
            if point.id == pointID:
                return point
        return None

    def getBranchByID(self, branchID: str) -> Optional[Branch]:
        """Given the ID of a branch, find the branch object that matches."""
        for branch in self.branches:
            if branch.id == branchID:
                return branch
        return None

    def addBranch(self, branch: Branch) -> int:
        """Adds a branch to the tree.

        :returns: Index of branch within the tree."""
        self.branches.append(branch)
        branch._parentTree = self
        return len(self.branches) - 1

    def removeBranch(self, branch: Branch) -> None:
        """Removes a branch from the tree - assumes all points already removed."""
        if branch not in self.branches:
            print ("Deleting branch not in the tree? Whoops")
            return
        if len(branch.points) > 0:
            print ("Removing a branch that still has stuff on it? use uiState.removeBranch.")
            return
        if branch.parentPoint is not None:
            branch.parentPoint.removeChildrenByID(branch.id)
        self.branches.remove(branch)

    def removePointByID(self, pointID: str) -> Optional[Point]:
        """Removes a single point from the tree, identified by ID."""
        pointToRemove = self.getPointByID(pointID)
        if pointToRemove is not None:
            if pointToRemove.parentBranch is None:
                assert self.rootPoint is not None and pointToRemove.id == self.rootPoint.id
                if len(self.branches) == 0:
                    self.rootPoint = None
                else:
                    print ("You can't remove the soma if other points exist - please remove those first!")
                return None
            else:
                result = pointToRemove.parentBranch.removePointLocally(pointToRemove)
                # Clean up branch if its only point was removed
                if pointToRemove.parentBranch.isEmpty():
                    self.removeBranch(pointToRemove.parentBranch)
                return result
        else:
            return None

    def reparentPoint(self, childPoint: Point, newParent: Point, newBranchID: Optional[str]=None) -> Optional[str]:
        """Changes a point (and its later siblings) to a new branch off the given parent."""
        if childPoint.parentBranch is None:
            # should not be allowed, skip
            print ("Can't reparent the root! Ignoring...")
            return None

        oldBranch, newBranch = childPoint.parentBranch, newParent.parentBranch

        if newParent.isLastInBranch() and not newParent.isRoot():
            assert newBranch is not None

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
            newID: Optional[str] = None
            atIdx = childPoint.indexInParent()

            if atIdx > 0: # need to split the old branch
                newID = newBranchID if newBranchID is not None else self._fullState().nextBranchID()
                newBranch = Branch(id=newID)
                while len(oldBranch.points) > atIdx:
                    toMove = oldBranch.points[atIdx]
                    oldBranch.removePointLocally(toMove)
                    newBranch.addPoint(toMove)
                self.addBranch(newBranch)
            newBranch.setParentPoint(newParent)
            return newID

    def movePoint(self, pointID: str, newLocation: Point3D, downstream: bool=False) -> None:
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

    def flattenPoints(self, includeDisconnected: bool=False) -> List[Point]:
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

    def nextPointFilteredWithCount(self,
            sourcePoint: Point, filterFunc: Callable[[Point], bool], delta:int
    ) -> Tuple[Optional[Point], int]:
        """Starting at a point, walk the tree to find all points that match a
        filter, and step a certain amount to the next one.
        Also return the count, for convenience."""
        points = self.flattenPoints()
        filteredPoints = [p for p in points if p == sourcePoint or filterFunc(p)]
        countPass = len(filteredPoints)
        if not filterFunc(sourcePoint):
            countPass -= 1

        if len(filteredPoints) == 0 or sourcePoint not in filteredPoints:
            return None, countPass

        idx = filteredPoints.index(sourcePoint) + delta
        nextIdx = idx % len(filteredPoints) # wrap

        found = filteredPoints[nextIdx]
        result = found if filterFunc(found) else None
        return result, countPass

    def continueParentBranchIfFirst(self, point: Optional[Point]) -> None:
        """If point is first in its branch, change it to extend its parent."""
        if point is None or point.indexInParent() > 0 or point.isRoot():
            return # Moving right along, nothing to see here...
        assert point.parentBranch is not None # Root

        branch = point.parentBranch
        parent = branch.parentPoint
        assert parent is not None
        if parent.isRoot():
            return # All branches are children of the root...
        assert parent.parentBranch is not None

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
            self.removeBranch(branch) # Also removes branch from parent point

    def updateAllPrimaryBranches(self, point: Optional[Point]=None) -> None:
        """For all branching points, make the longest branch continue the parent branch."""
        if point is None:
            point = self.rootPoint
        if point is None:
            return

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
        def _branchDistRemaining(branch: Branch) -> float:
            if len(branch.points) > 0:
                return -branch.points[0].longestDistanceToLeaf()
            return 0.0
        point.children.sort(key=_branchDistRemaining)

        # Step 3: Recurse down tree:
        nextPoint = point.nextPointInBranch(noWrap=True)
        if nextPoint is not None:
            self.updateAllPrimaryBranches(nextPoint)
        for childBranch in point.children:
            if len(childBranch.points) > 0:
                self.updateAllPrimaryBranches(childBranch.points[0])

    def updateAllBranchesMinimalAngle(self, point: Optional[Point]=None) -> None:
        """For all branching points, continue the parent branch with small angle at bifurications"""

        def _lreturnTriple(point, nextPoint=None):
            if nextPoint==None:
                nextPoint = point.nextPointInBranch(noWrap=True)
            pointBefore = point.nextPointInBranch(delta=-1, noWrap=True)
            if pointBefore is not None:
                triple=(pointBefore, point, nextPoint)
            return triple

        def _lreturnBranchAngle(tree, point,  nextPoint=None):
            triple = _lreturnTriple(point,  nextPoint)
            if not all(triple):
                return 0
            else:
                xs, ys, zs = tree.worldCoordPoints(list(triple))
                worldAt = [np.array([x, y, z]) for x, y, z in zip(xs, ys, zs)]
                AB, BC = worldAt[1] - worldAt[0], worldAt[2] - worldAt[1]

                cosAngle = np.dot(AB, BC) / (np.linalg.norm(AB) * np.linalg.norm(BC))
                angle = np.abs(np.arccos(cosAngle))
                return angle

        # List of all points which are branch parents
        parent_points = []
        for branch in self.branches:
            if branch.parentPoint.isRoot() == False:
                if len(branch.parentPoint.children) > 0:
                    parent_points.append(branch.parentPoint.id)

        # Check the branch angles at bifurications and reparent
        for point_id in parent_points:
            point = self.getPointByID(point_id)
            if _lreturnBranchAngle(self, point) > _lreturnBranchAngle(self, point, point.children[0].points[0]):
                self.continueParentBranchIfFirst(point.children[0].points[0])


    def cleanBranchIDs(self) -> None:
        """For all branches, set the ID of the branch to its first point's ID.

        Note: Branch IDs should be removed overall and this be the default behaviour.
        """
        for branch in self.branches:
            if len(branch.points) > 0:
                branch.id = branch.points[0].id
            else:

                branch.id = self._fullState().nextBranchID()

    def cleanEmptyBranches(self) -> int:
        """For all branches, if it has no points just remove it completely.

        :returns: Number of branches removed.
        """
        emptyBranches = [b for b in self.branches if len(b.points) == 0]
        for emptyBranch in emptyBranches:
            self.removeBranch(emptyBranch)
        return len(emptyBranches)

    def spatialRadius(self) -> float:
        """External longest distance to points from soma."""
        return self.spatialAndTreeRadius()[0]

    def spatialAndTreeRadius(self) -> Tuple[float, float]:
        """External and internal longest distance to points from soma."""
        maxS, maxT = 0.0, 0.0
        if self.rootPoint is not None:
            for point in self.flattenPoints():
                pS, pT = self.spatialAndTreeDist(self.rootPoint, point)
                maxS, maxT = max(maxS, pS), max(maxT, pT)
        return maxS, maxT

    def closestPointTo(self, targetLocation: Point3D, zFilter: bool=False) -> Optional[Point]:
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

    def closestPointToWorldLocation(self, targetWorldLocation: Point3D) -> Optional[Point]:
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

    def worldCoordPoints(self, points: List[Point]) -> Tuple[List[float], List[float], List[float]]:
        """Convert image pixel (x, y, z) to a real-world (x, y, z) position."""
        x: List[float] = []
        y: List[float] = []
        z: List[float] = []

        globalScale = self._fullState().projectOptions.pixelSizes
        for p in points:
            # POIUY: support calling with list of locations?
            #pAt = p
            #if hasattr(p, 'location'):
            pAt = p.location

            # Note: For now, tree-specific transforms are unsupported!
            #pAt = np.matmul(np.array(self.transform.rotation), np.array(pAt).T).T
            #pAt = (pAt + np.array(self.transform.translation)) * np.array(self.transform.scale)
            pAt = np.array(pAt) * globalScale
            x.append(pAt[0])
            y.append(pAt[1])
            z.append(pAt[2])
        return x, y, z

    def spatialDist(self, p1: Point, p2: Point) -> float:
        """Given two points in the tree, return the 3D spatial distance"""
        x, y, z = self.worldCoordPoints([p1, p2])
        p1Location = (x[0], y[0], z[0])
        p2Location = (x[1], y[1], z[1])
        return util.deltaSz(p1Location, p2Location)

    def spatialAndTreeDist(self, p1: Point, p2: Point) -> Tuple[float, float]:
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
            pA = (path1X[ i ], path1Y[ i ], path1Z[ i ])
            pB = (path1X[i+1], path1Y[i+1], path1Z[i+1])
            treeDist += util.deltaSz(pA, pB)
        for i in range(len(path2X) - 1):
            pA = (path2X[ i ], path2Y[ i ], path2Z[ i ])
            pB = (path2X[i+1], path2Y[i+1], path2Z[i+1])
            treeDist += util.deltaSz(pA, pB)
        return self.spatialDist(p1, p2), treeDist

    def _recursiveMovePointDelta(self, point: Point, delta: Point3D) -> None:
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

    def clearAndCopyFrom(self, otherTree: Tree, idMaker: FullState) -> None:
        pointMap: Dict[str, Point] = {}
        assert otherTree.rootPoint is not None, "Can't clone empty tree."

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

    def _fullState(self) -> FullState:
        """
        Utility to return the non-none fullstate object.
        """
        assert self._parentState is not None, "Accessing uninitialized tree"
        assert self._parentState._parent is not None, "Accessing uninitialized tree"
        return self._parentState._parent

    #Cleaning Methods for autotraced trees
    def cleanUpTree(self):
        print('Clean-up')
        self.updateAllPrimaryBranches()
        def removeOverBranch(localTree, branch):
            if branch.hasChildren() == False:
                print("Let's prune it!")
                print(len(branch.points))
                branch.points = []
                
                localTree.removeBranch(branch.id)
            else:
                for _point in branch.points[::-1]:
                    if len(_point.children) > 0:
                        for child in _point.children:
                            removeOverBranch(localTree, child)


        ids = set()
        ids = set([b.id for b in self.branches])
        branchIDs =  sorted(list(ids))

        for branch in branchIDs:
            if self.getBranchByID(branch) is not None:
                print(branch)
                _tempBranch = self.getBranchByID(branch)
                if _tempBranch.hasChildren():
                    for _point in _tempBranch.points:
                        if len(_point.children) > 0:
                            try:
                                A = _point.location
                                B = _point.children[0].points[0].location
                                C = _tempBranch.points[_point.indexInParent()+1].location
                                if  75 > angle_between_vectors(A,B,C):
                                    removeOverBranch(self, _point.children[0])
                                    _point.children.pop()
                                if  130 < angle_between_vectors(A,B,C):
                                    removeOverBranch(self, _point.children[0])
                                    _point.children.pop()
                            except:
                                pass
        # Remove empties 
        self.cleanEmptyBranches()
        self.updateAllPrimaryBranches()



### Cloning utilities

def _clonePoint(point: Point, idMaker: FullState, pointMap: Dict[str, Point]) -> Point:
    assert point.id not in pointMap
    newID = point.id if idMaker is None else idMaker.nextPointID()
    # NOTE: SWC point ID can be stored here too if needed.
    newPoint = Point(id=newID, location=point.location, radius=point.radius)
    pointMap[point.id] = newPoint
    return newPoint

def _cloneBranch(branch: Branch, idMaker: FullState, pointMap: Dict[str, Point]) -> Branch:
    newID = branch.id if idMaker is None else idMaker.nextBranchID()
    b = Branch(id=newID)
    for point in branch.points:
        b.addPoint(_clonePoint(point, idMaker, pointMap))
    return b



#
# Debug formatting for converting trees to string representation
#
def printPoint(tree: Tree, point: Optional[Point], pad: str="", isFirst: bool=False) -> None:
    if point is None:
        return
    print (pad + ("-> " if isFirst else "   ") + str(point))
    pad = pad + "   "
    for branch in point.children:
        if branch.parentPoint == point:
            printBranch(tree, branch, pad)

def printBranch(tree: Tree, branch: Optional[Branch], pad:str="") -> None:
    if branch is None:
        return
    if len(branch.points) > 0 and branch.points[0] == branch.parentPoint:
        print ("BRANCH IS OWN PARENT? :(")
        return
    print (pad + "-> Branch " + branch.id + " = ")
    for point in branch.points:
        printPoint(tree, point, pad)

def printTree(tree: Tree) -> None:
    printPoint(tree, tree.rootPoint)


# Functions for cleaning autotrace tree; Move else where?
def angle_between_vectors(A, B, C):
    # Calculate vectors AB and AC
    vector_AB = np.array(B) - np.array(A)
    vector_AC = np.array(C) - np.array(A)
    
    # Calculate the dot product of vectors AB and AC
    dot_product = np.dot(vector_AB, vector_AC)
    
    # Calculate the magnitude (norm) of vectors AB and AC
    magnitude_AB = np.linalg.norm(vector_AB)
    magnitude_AC = np.linalg.norm(vector_AC)
    
    # Calculate the cosine of the angle between vectors AB and AC
    cosine_theta = dot_product / (magnitude_AB * magnitude_AC)
    
    # Calculate the angle in radians using arccosine
    angle_rad = np.arccos(cosine_theta)
    
    # Convert the angle to degrees
    angle_deg = np.degrees(angle_rad)

    return angle_deg 

def scanBranchFlow(branchPoints):
    newPoints = []
    if len(branchPoints)<4:
        return branchPoints
    else:
        if 40 < angle_between_vectors(branchPoints[0].location,
                                    branchPoints[1].location,
                                    branchPoints[2].location):
                if angle_between_vectors(branchPoints[0].location,
                                    branchPoints[1].location,
                                    branchPoints[2].location) < angle_between_vectors(branchPoints[0].location,
                    branchPoints[2].location,
                    branchPoints[3].location):
                    if len(branchPoints[1].children) == 0:
                        branchPoints.pop(1)
        
        return branchPoints[:3] + scanBranchFlow(branchPoints[2:][3:])
                                            