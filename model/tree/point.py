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
        return self.nextPointInBranch() is None

    def nextPointInBranch(self, delta=1):
        """Walks a distance along the branch and returns the sibling."""
        if self.parentBranch is None:
            return None # Root point alone in branch.
        idx = self.indexInParent()
        nextIdx = idx + delta
        if nextIdx == -1:
            return self.parentBranch.parentPoint
        elif nextIdx >= 0 and nextIdx < len(self.parentBranch.points):
            return self.parentBranch.points[nextIdx]
        else:
            return None

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
