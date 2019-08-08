import numpy as np

import pydynamo_brain.util as util

from pydynamo_brain.analysis import shollCrossings
from pydynamo_brain.ui.baseMatplotlibCanvas import BaseMatplotlibCanvas

GREY_COLOUR   = (0.75, 0.75, 0.75, 0.75)

BINS = 30

# Draws a dendritic tree in 3D space that can be rotated by the user.
class ShollCanvas(BaseMatplotlibCanvas):
    TREE_COUNT = 3

    def __init__(self, parent, firstTreeIdx, treeModels, filePaths, *args, **kwargs):
        self.treeModels = treeModels
        self.filePaths = filePaths
        self.vizTreeCount = min(len(treeModels), self.TREE_COUNT)
        self.firstTree = max(0, min(len(treeModels) - self.vizTreeCount, firstTreeIdx))

        self.maxRadius = 0
        for tree in treeModels:
            for p in tree.flattenPoints():
                x, y, z = tree.worldCoordPoints([tree.rootPoint, p])
                d = util.deltaSz((x[0], y[0], z[0]), (x[1], y[1], z[1]))
                self.maxRadius = max(self.maxRadius, d)

        super(ShollCanvas, self).__init__(*args, subplots=self.vizTreeCount, **kwargs)
        self.fig.subplots_adjust(top=0.95, bottom=0.05, right=0.95, left=0.05, wspace=0.05, hspace=0.05)

    def compute_initial_figure(self):
        for offset, ax in enumerate(self.axes):
            treeIdx = self.firstTree + offset
            ax.set_title(util.createTitle(treeIdx, self.filePaths[treeIdx]))
            ax.set_facecolor("white")
            self.drawSingleTreeSholl(ax, treeIdx)

    # Given one tree, draw sholl data for that tree
    def drawSingleTreeSholl(self, ax, treeIdx):
        # TODO - precalc
        treeModel = self.treeModels[treeIdx]
        barWidth = self.maxRadius / BINS * 0.8
        counts, xs = shollCrossings(treeModel, self.maxRadius, BINS)
        ax.bar(xs, counts, width=barWidth)

    def needToUpdate(self):
        for ax in self.axes:
            ax.cla()
        self.compute_initial_figure()
        self.draw()

    def canPrev(self):
        return self.firstTree > 0

    def canNext(self):
        return self.firstTree < len(self.treeModels) - 1

    def previous(self, toEnd):
        endIdx = 0
        nextIdx = endIdx if toEnd else max(self.firstTree - 1, endIdx)
        if nextIdx != self.firstTree:
            self.firstTree = nextIdx
            self.needToUpdate()

    def next(self, toEnd):
        endIdx = len(self.treeModels) - 2
        nextIdx = endIdx if toEnd else min(self.firstTree + 1, endIdx)
        if nextIdx != self.firstTree:
            self.firstTree = nextIdx
            self.needToUpdate()
