"""
.. module:: tree
"""
import attr
import numpy as np
import util

from util import SAVE_META


@attr.s
class Point():
    """Node in the tree, a point in 3D space."""

    id = attr.ib(metadata=SAVE_META)
    """Identifier of point, can be shared across stacks."""

    location = attr.ib(metadata=SAVE_META)
    """Node position as an (x, y, z) tuple."""

    parentBranch = attr.ib(default=None, repr=False, cmp=False)
    """Branch this point belongs to."""

    annotation = attr.ib(default="", cmp=False, metadata=SAVE_META)
    """Text annotation for node."""

    children = attr.ib(default=attr.Factory(list))
    """Branches coming off the node."""

    hilighted = attr.ib(default=None, cmp=False)
    """Indicates which points could not be registered."""

    def isRoot(self):
        """Whether this point represents the root of the whole tree."""
        return self.parentBranch is None

    def indexInParent(self):
        """How far along the branch this point sits, 0 = first point after branch point."""
        if self.parentBranch is None:
            return 0 # Root is first
        return self.parentBranch.indexForPoint(self)

    def isLastInBranch(self):
        """Return whether this point is the terminal point in the branch."""
        return self.nextPointInBranch(noWrap=True) is None

    def nextPointInBranch(self, delta=1, noWrap=False):
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
            # Underflow, so walk up parent.
            return self.parentBranch.parentPoint.nextPointInBranch(nextIdx + 1)
        else:
            assert nextIdx >= len(self.parentBranch.points)
            at = self.parentBranch.points[-1]
            # Overflow, so go down first branch.
            if at is not None and len(at.children) > 0 and len(at.children[0].points) > 0:
                childBranchFirstPoint = at.children[0].points[0]
                return childBranchFirstPoint.nextPointInBranch(nextIdx - len(self.parentBranch.points))

    def flattenSubtreePoints(self):
        """Return all points downstream from this point."""
        if self.parentBranch is not None:
            return self.parentBranch.flattenSubtreePoints(startIdx=self.indexInParent())
        # Root point, needs special logic
        points = [self]
        for child in self.children:
            points.extend(child.flattenSubtreePoints())
        return points

    def subtreeContainsID(self, pointID):
        """Whether the given point ID exists anywhere further down the tree."""
        return pointID in [p.id for p in self.flattenSubtreePoints()]

    def pathFromRoot(self):
        """Points in order to get from the root to this point."""
        points = []
        pointAt = self
        while pointAt is not None:
            points.append(pointAt)
            pointAt = pointAt.nextPointInBranch(delta=-1)
        return list(reversed(points))

    def longestDistanceToLeaf(self):
        tree = self.parentBranch._parentTree

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
