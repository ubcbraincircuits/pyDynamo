from PyQt5.QtGui import QPen, QPainter, QBrush, QFont, QColor
from PyQt5.QtCore import Qt, QPointF, QRectF

import matplotlib.pyplot as plt
import numpy as np

LINE_COLOR_COUNT = 7
COLOR_STEP = 3 # needs to be co-prime with color count
ROOT_COLOR_ID = COLOR_STEP # Color of first branch to use.
LINE_COLORS = plt.get_cmap('hsv')(np.arange(0.0, 1.0, 1.0/LINE_COLOR_COUNT))[:, :3]

class BranchToColorMap():
    """Singleton cache mapping branch IDs to rbg colours."""

    # Singleton instance - create BranchToColorMap() and get back the same cache each time.
    _instance = None
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = object.__new__(BranchToColorMap)
        return cls._instance

    # Maps branch ID to color ID in [0, LINE_COLOR_COUNT)
    _branchToColorID = dict()

    # @return ID of the color for a given branch
    def _colorIDForBranch(self, branch):
        if branch is None:
            # Default to root, if no branch provided
            return ROOT_COLOR_ID
        if branch.id not in self._branchToColorID:
            print ("Branch %s doesn't have a color?!" % branch.id)
            return ROOT_COLOR_ID
        return self._branchToColorID[branch.id]

    # @return Number of the given branches that have a given colour
    def _childColorCounts(self, branches):
        counts = [0 for _ in range(LINE_COLOR_COUNT)]
        for branch in branches:
            if branch.id in self._branchToColorID:
                counts[self._branchToColorID[branch.id]] += 1
        return counts

    def _initFromPointOrBranches(self, parentColorID, point=None, branches=None):
        if branches is None:
            # If point is provided, find branches by all off this point's branch:
            if point is None or ((point.parentBranch is not None) and (len(point.parentBranch.points) == 0)):
                return
            # Either root, or first point in a branch
            assert point.parentBranch is None or point.parentBranch.points[0].id == point.id

            # Find all branches off this one:
            allPoints = [point] if point.isRoot() else point.parentBranch.points
            branches = []
            for branchPoint in allPoints:
                branches.extend(branchPoint.children)

        # And assign them color IDs in order:
        childColorCounts = self._childColorCounts(branches)
        for branch in branches:
            nextColorID, bestNextColor = parentColorID, None

            while True:
                nextColorID = (nextColorID + COLOR_STEP) % LINE_COLOR_COUNT
                if nextColorID == parentColorID:
                    break
                if bestNextColor is None or childColorCounts[nextColorID] < childColorCounts[bestNextColor]:
                    bestNextColor = nextColorID

            self._branchToColorID[branch.id] = bestNextColor
            childColorCounts[bestNextColor] += 1
            if len(branch.points) > 0:
                # Walk down and do the same for this branch:
                self._initFromPointOrBranches(bestNextColor, point=branch.points[0])

    # Start the mapping from a fresh slate.
    def initFromFullState(self, fullState):
        self._branchToColorID = dict()
        for tree in fullState.trees:
            self.addNewTree(tree)

    # Add a new tree to the mapping:
    def addNewTree(self, tree):
        self._initFromPointOrBranches(0, point=tree.rootPoint)

    # Add a single branch to the mapping:
    def updateBranch(self, branch):
        if branch.id in self._branchToColorID:
            del self._branchToColorID[branch.id]
        parentColorID = self._colorIDForBranch(branch.parentPoint.parentBranch)
        self._initFromPointOrBranches(parentColorID, branches=[branch])

    # @return RGB tuple for a branch, or root point if branch == None
    def rgbForBranch(self, branch):
        return LINE_COLORS[self._colorIDForBranch(branch)]

    # @return QColor for a branch, or root point if branch == None
    def colorForBranch(self, branch):
        rgb = self.rgbForBranch(branch)
        return QColor.fromRgbF(rgb[0], rgb[1], rgb[2])
