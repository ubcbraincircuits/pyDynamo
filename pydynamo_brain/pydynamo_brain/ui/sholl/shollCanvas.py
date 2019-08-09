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
        self.maxRadius += 1e-9 # exclusive -> inclusive(ish)
        # TODO - load from config
        self.binSizeUm = 5

        self.shollResults = []
        for tree in treeModels:
            self.shollResults.append(shollCrossings(tree, self.binSizeUm, self.maxRadius))

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
        counts, xs = self.shollResults[treeIdx]
        ax.bar(xs, counts, width=(self.binSizeUm * 0.8))

    def needToUpdate(self):
        for ax in self.axes:
            ax.cla()
        self.compute_initial_figure()
        self.draw()

    def canPrev(self):
        return self.firstTree > 0

    def canNext(self):
        return self.firstTree < len(self.treeModels) - self.TREE_COUNT

    def previous(self, toEnd):
        endIdx = 0
        nextIdx = endIdx if toEnd else max(self.firstTree - 1, endIdx)
        if nextIdx != self.firstTree:
            self.firstTree = nextIdx
            self.needToUpdate()

    def next(self, toEnd):
        endIdx = len(self.treeModels) - self.TREE_COUNT
        nextIdx = endIdx if toEnd else min(self.firstTree + 1, endIdx)
        if nextIdx != self.firstTree:
            self.firstTree = nextIdx
            self.needToUpdate()
