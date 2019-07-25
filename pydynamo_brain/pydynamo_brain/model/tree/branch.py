"""
.. module:: tree
"""
import attr
import numpy as np

import pydynamo_brain.util as util
from pydynamo_brain.util import SAVE_META

from .point import Point


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

    def indexForPointID(self, pointID):
        """Given a point ID, return how far along the branch it sits."""
        for idx, point in enumerate(self.points):
            if point.id == pointID:
                return idx
        return -1

    def indexForPoint(self, pointTarget):
        """Given a point, return how far along the branch it sits."""
        return self.indexForPointID(pointTarget.id)

    def isEmpty(self):
        """Whether the branch has no points other than the branch point."""
        return len(self.points) == 0

    def hasPointWithAnnotation(self, annotation, recurseUp=False):
        """Whether any point directly on this branch has a given annotation."""
        if util.lastPointWithLabelIdx([self.parentPoint] + self.points, annotation) >= 0:
            return True
        # Optionally go upwards, e.g. you're an axon branch if you come off the main axon.
        if recurseUp and self.parentPoint.parentBranch is not None:
            # NOTE: this will also apply even if the parent's point is after
            # the point I have branched off at. This could be edited if needed,
            # to only match if I'm after the annotation.
            return self.parentPoint.parentBranch.hasPointWithAnnotation(annotation, recurseUp)
        else:
            return False

    def isAxon(self, axonLabel='axon', recurseUp=True):
        """Whether the branch is labelled as the axon."""
        return self.hasPointWithAnnotation(axonLabel, recurseUp)

    def isBasal(self, basalLabel='basal', recurseUp=True):
        return self.hasPointWithAnnotation(basalLabel, recurseUp)

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
            return
        index = self.points.index(point)
        self.points.remove(point)
        return self.parentPoint if index == 0 else self.points[index - 1]

    def setParentPoint(self, parentPoint):
        """Sets the parent point for this branch, and adds the branch to its parent's children."""
        if self.parentPoint is not None and self in self.parentPoint.children:
            self.parentPoint.children.remove(self) # Remove from previous parent first, if needed
        self.parentPoint = parentPoint
        self.parentPoint.children.append(self)

    def flattenSubtreePoints(self, startIdx=0):
        """Return all points on this branch and subbranches."""
        points = []
        for p in self.points[startIdx:]:
            points.append(p)
            for child in p.children:
                points.extend(child.flattenSubtreePoints())
        return points

    def subtreeContainsID(self, pointID):
        """Whether the given point ID exists on this branch or subbranches down the tree."""
        return pointID in [p.id for p in self.flattenSubtreePoints()]

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


### Utilities

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
