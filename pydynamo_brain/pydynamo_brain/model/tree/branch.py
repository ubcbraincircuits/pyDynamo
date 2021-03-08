from __future__ import annotations
"""
.. module:: tree
"""

import attr
import numpy as np

from typing import Any, List, Optional, Tuple, TYPE_CHECKING

import pydynamo_brain.util as util
from pydynamo_brain.util import SAVE_META

from .point import Point

if TYPE_CHECKING:
    from .tree import Tree

@attr.s
class Branch():
    """Single connected branch on a Tree"""

    id: str = attr.ib(metadata=SAVE_META)
    """Identifier of a branch, can be shared across stacks."""

    _parentTree: Tree = attr.ib(default=None, repr=False, eq=False, order=False)
    """Tree the branch belongs to"""

    parentPoint: Optional[Point] = attr.ib(default=None, repr=False, eq=False, order=False, metadata=SAVE_META)
    """Node this branched off, or None for root branch"""

    points: List[Point] = attr.ib(default=attr.Factory(list), metadata=SAVE_META)
    """Points along this dendrite branch, in order."""

    isEnded: bool = attr.ib(default=False, eq=False, order=False)
    """Not sure...? Isn't used... """

    colorData: Any = attr.ib(default=None, eq=False, order=False) # Not used yet
    """Not sure...? Isn't used... """

    reparentTo: Optional[Point] = attr.ib(default=None, metadata=SAVE_META)
    """HACK - document"""

    def indexInParent(self) -> int:
        """Ordinal number of branch within the tree it is owned by."""
        return self._parentTree.branches.index(self)

    def indexForPointID(self, pointID: str) -> int:
        """Given a point ID, return how far along the branch it sits."""
        for idx, point in enumerate(self.points):
            if point.id == pointID:
                return idx
        return -1

    def indexForPoint(self, pointTarget: Point) -> int:
        """Given a point, return how far along the branch it sits."""
        return self.indexForPointID(pointTarget.id)

    def isEmpty(self) -> bool:
        """Whether the branch has no points other than the branch point."""
        return len(self.points) == 0

    def hasPointWithAnnotation(self, annotation: str, recurseUp:bool=False) -> bool:
        """Whether any point directly on this branch has a given annotation."""
        pointsWithParent = self.pointsWithParentIfExists()
        if util.lastPointWithLabelIdx(pointsWithParent, annotation) >= 0:
            return True

        # Optionally go upwards, e.g. you're an axon branch if you come off the main axon.
        if recurseUp and self.parentPoint is not None and self.parentPoint.parentBranch is not None:
            if self.parentPoint.parentBranch == self:
                # Hmm... not sure how this happened?
                return False
            # NOTE: this will also apply even if the parent's point is after
            # the point I have branched off at. This could be edited if needed,
            # to only match if I'm after the annotation.
            return self.parentPoint.parentBranch.hasPointWithAnnotation(annotation, recurseUp)
        else:
            return False

    def isAxon(self, axonLabel: str='axon', recurseUp: bool=True) -> bool:
        """Whether the branch is labelled as the axon."""
        return self.hasPointWithAnnotation(axonLabel, recurseUp)

    def isBasal(self, basalLabel: str='basal', recurseUp: bool=True) -> bool:
        return self.hasPointWithAnnotation(basalLabel, recurseUp)

    def hasChildren(self) -> bool:
        """True if any point on the branch has child branches coming off it."""
        return _lastPointWithChildren(self.points) > -1

    def isFilo(self, maxLength: float) -> Tuple[bool, float]:
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

    def getOrder(self, centrifugal: bool=False) -> int:
        """Order of the branch - number of branches away from the soma.
        Shaft order by default, centrifugal = split branch at each branching spot."""
        assert self.parentPoint is not None
        if self.parentPoint.isRoot():
            return 1

        assert self.parentPoint.parentBranch is not None

        parentOrder = self.parentPoint.parentBranch.getOrder()

        if centrifugal:
            # Centrifugal order: When walking along a branch,
            # increment order each time subbranches come off it.
            pointAt: Optional[Point] = self.parentPoint.parentBranch.points[0]
            while pointAt is not None and pointAt.id != self.parentPoint.id:
                if len(pointAt.children) > 0:
                    parentOrder += 1
                pointAt = pointAt.nextPointInBranch(noWrap=True)
        else:
            # Shaft order: no adjustment needed,
            # just count branches upwards until we get to the root
            pass

        return parentOrder + 1

    def addPoint(self, point: Point) -> int:
        """Appends a point at the end of the branch.

        :returns: the index of the new point."""
        self.points.append(point)
        point.parentBranch = self
        return len(self.points) - 1

    def insertPointBefore(self, point: Point, index: int) -> int:
        """Appends a point within a branch.

        :returns: the index of the new point."""
        self.points.insert(index, point)
        point.parentBranch = self
        return index

    def removePointLocally(self, point: Point) -> Optional[Point]:
        """Remove a single point from the branch, leaving points before and after.

        :returns: The point before this one"""
        if point not in self.points:
            print ("Deleting point not in the branch? Whoops")
            return None
        index = self.points.index(point)
        self.points.remove(point)
        return self.parentPoint if index == 0 else self.points[index - 1]

    def setParentPoint(self, parentPoint: Point) -> None:
        """Sets the parent point for this branch, and adds the branch to its parent's children."""
        if self.parentPoint is not None and self in self.parentPoint.children:
            self.parentPoint.children.remove(self) # Remove from previous parent first, if needed
        self.parentPoint = parentPoint
        self.parentPoint.children.append(self)

    def flattenSubtreePoints(self, startIdx: int=0) -> List[Point]:
        """Return all points on this branch and subbranches."""
        points = []
        for p in self.points[startIdx:]:
            points.append(p)
            for child in p.children:
                points.extend(child.flattenSubtreePoints())
        return points

    def subtreeContainsID(self, pointID: str) -> bool:
        """Whether the given point ID exists on this branch or subbranches down the tree."""
        return pointID in [p.id for p in self.flattenSubtreePoints()]

    def worldLengths(self, fromIdx: int=0) -> Tuple[float, float]:
        """Returns world length of the branch, plus the length to the last branch point.

        :returns: (totalLength, totalLength to last branch)
        """
        pointsWithRoot = self.pointsWithParentIfExists()[fromIdx:]

        x, y, z = self._parentTree.worldCoordPoints(pointsWithRoot)
        lastBranchPoint = _lastPointWithChildren(pointsWithRoot)
        totalLength, totalLengthToLastBranch = 0.0, 0.0
        for i in range(len(x) - 1):
            edgeDistance = util.deltaSz((x[i], y[i], z[i]), (x[i+1], y[i+1], z[i+1]))
            totalLength += edgeDistance
            if i < lastBranchPoint:
                totalLengthToLastBranch += edgeDistance
        return totalLength, totalLengthToLastBranch

    def cumulativeWorldLengths(self) -> List[float]:
        """Calculate the length to all points along the branch.

        :returns: List of cumulative lengths, how far along the branch to get to each point."""
        pointsWithRoot = self.pointsWithParentIfExists()
        x, y, z = self._parentTree.worldCoordPoints(pointsWithRoot)
        cumulativeLength, lengths = 0.0, []
        for i in range(len(x) - 1):
            edgeDistance = util.deltaSz((x[i], y[i], z[i]), (x[i+1], y[i+1], z[i+1]))
            cumulativeLength += edgeDistance
            lengths.append(cumulativeLength)
        return lengths

    def pointsWithParentIfExists(self) -> List[Point]:
        if self.parentPoint is not None:
            return [self.parentPoint] + self.points
        return self.points

### Utilities

# Return the index of the last point with child branches, or -1 if not found.
def _lastPointWithChildren(points: List[Point]) -> int:
    lastPointIdx = -1
    for i, point in enumerate(points):
        if len(point.children) > 0:
            lastPointIdx = i
    return lastPointIdx

# Return the index of the last point whose label contains given text, or -1 if not found.
# TODO - move somewhere common.
def _lastPointWithLabel(points: List[Point], label: str) -> int:
    lastPointIdx = -1
    for i, point in enumerate(points):
        if point.annotation.find(label) != -1:
            lastPointIdx = i
    return lastPointIdx
