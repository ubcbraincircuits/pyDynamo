from __future__ import annotations
"""
.. module:: tree
"""
import attr
import math
import numpy as np

from typing import List, Optional, TYPE_CHECKING

import pydynamo_brain.util as util
from pydynamo_brain.util import SAVE_META, Point3D

if TYPE_CHECKING:
    from .branch import Branch


@attr.s
class Point():
    """Node in the tree, a point in 3D space."""

    id: str = attr.ib(metadata=SAVE_META)
    """Identifier of point, can be shared across stacks."""

    location: Point3D = attr.ib(metadata=SAVE_META)
    """Node position as an (x, y, z) tuple, in pixels."""

    radius: Optional[float] = attr.ib(default=None, metadata=SAVE_META)
    """(optional) radius of the point, in pixels."""

    parentBranch: Optional[Branch] = attr.ib(default=None, repr=False, eq=False, order=False)
    """Branch this point belongs to."""

    annotation: str = attr.ib(default="", eq=False, order=False, metadata=SAVE_META)
    """Text annotation for node."""

    children: List[Branch] = attr.ib(default=attr.Factory(list))
    """Branches coming off the node."""

    manuallyMarked: Optional[bool] = attr.ib(default=None, eq=False, order=False, metadata=SAVE_META)
    """Indicates which points have been marked to be revisited."""

    hilighted: Optional[bool] = attr.ib(default=None, eq=False, order=False, metadata=SAVE_META)
    """ NOTE: Hilighting has been removed, keep here for backwards compatibility."""

    def isRoot(self) -> bool:
        """Whether this point represents the root of the whole tree."""
        return self.parentBranch is None

    def indexInParent(self) -> int:
        """How far along the branch this point sits, 0 = first point after branch point."""
        if self.parentBranch is None:
            return 0 # Root is first
        return self.parentBranch.indexForPoint(self)

    def isLastInBranch(self) -> bool:
        """Return whether this point is the terminal point in the branch."""
        return self.nextPointInBranch(noWrap=True) is None

    def removeChildrenByID(self, branchID: str) -> None:
        """Removes a branch from the list of branches coming off this point."""
        self.children = [b for b in self.children if b.id != branchID]

    def nextPointInBranch(self, delta: int=1, noWrap: bool=False) -> Optional[Point]:
        """Walks a distance along the branch and returns the sibling."""
        if delta == 0:
            return self

        if self.parentBranch is None:
            if delta < 0:
                # Root point has none before
                return None
            else:
                if noWrap:
                    return None
                # Walk down to first branch.
                if len(self.children) > 0 and len(self.children[0].points) > 0:
                    return self.children[0].points[0].nextPointInBranch(delta - 1)
            return None # Not hit - for type hints only

        idx = self.indexInParent()
        nextIdx = idx + delta
        if nextIdx == -1:
            return self.parentBranch.parentPoint
        elif nextIdx >= 0 and nextIdx < len(self.parentBranch.points):
            return self.parentBranch.points[nextIdx]
        if noWrap:
            return None
        # Wrapping allowed, so walk before/after brach.
        if nextIdx < 0:
            if self.parentBranch.parentPoint is not None:
                return self.parentBranch.parentPoint.nextPointInBranch(nextIdx + 1)
            return None
        else:
            assert nextIdx >= len(self.parentBranch.points)
            at = self.parentBranch.points[-1]
            # Overflow, so go down first branch.
            if at is not None and len(at.children) > 0 and len(at.children[0].points) > 0:
                childBranchFirstPoint = at.children[0].points[0]
                return childBranchFirstPoint.nextPointInBranch(nextIdx - len(self.parentBranch.points))
        return None # Not hit - for type hints only

    def flattenSubtreePoints(self) -> List[Point]:
        """Return all points downstream from this point."""
        if self.parentBranch is not None:
            return self.parentBranch.flattenSubtreePoints(startIdx=self.indexInParent())
        # Root point, needs special logic
        points = [self]
        for child in self.children:
            points.extend(child.flattenSubtreePoints())
        return points

    def subtreeContainsID(self, pointID:str) -> bool:
        """Whether the given point ID exists anywhere further down the tree."""
        return pointID in [p.id for p in self.flattenSubtreePoints()]

    def pathFromRoot(self) -> List[Point]:
        """Points in order to get from the root to this point."""
        points = []
        pointAt: Optional[Point] = self
        while pointAt is not None:
            points.append(pointAt)
            pointAt = pointAt.nextPointInBranch(delta=-1)
        return list(reversed(points))

    def radiusFromAncestors(self) -> float:
        """Walks backwards from current point until a radius is found.
            Returns default value (5) if no Radius is found """
        ancestorRadius: Optional[float] = None
        upTreePoint: Optional[Point] = self
        while ancestorRadius == None and upTreePoint is not None:
            upTreePoint = upTreePoint.nextPointInBranch(delta=-1)
            if upTreePoint == None:
                ancestorRadius == 5.0
            if upTreePoint is not None:
                if upTreePoint.radius is not None:
                    ancestorRadius = upTreePoint.radius
            else:
                ancestorRadius = 5.0

        if ancestorRadius is None:
            ancestorRadius = 5.0 # Not hit - for type hints only
        return ancestorRadius

    def longestDistanceToLeaf(self) -> float:
        branchForTree = self.parentBranch
        if branchForTree is None and len(self.children) > 0:
            branchForTree = self.children[0]
        if branchForTree is None:
            # No branches in tree:
            return 0.0

        tree = branchForTree._parentTree

        longestDist = 0.0
        sibling = self.nextPointInBranch(noWrap=True)
        if sibling is not None:
            siblingDist = tree.spatialDist(self, sibling) + sibling.longestDistanceToLeaf()
            longestDist = max(longestDist, siblingDist)
        for child in self.children:
            if len(child.points) > 0:
                cPoint = child.points[0]
                childDist = tree.spatialDist(self, cPoint) + cPoint.longestDistanceToLeaf()
                longestDist = max(longestDist, childDist)
        return longestDist

    def returnWorldRadius(self, fullState) -> float:
        """Returns world radius value of point or Zero if there is no radius.
        :returns: (worldRadius)
        """
        if self.radius is not None:
            xScale, yScale, _ = fullState.projectOptions.pixelSizes
            scaleFactor = math.sqrt(xScale*yScale)
            worldRadius = self.radius * scaleFactor
        else:
            worldRadius = 0

        return worldRadius
