import numpy as np
import numpy.polynomial.polynomial as npPoly

import pydynamo_brain.util as util

from pydynamo_brain.analysis import shollCrossings, shollMetrics
from pydynamo_brain.ui.baseMatplotlibCanvas import BaseMatplotlibCanvas

GREY_COLOUR   = (0.75, 0.75, 0.75, 0.75)

# Draws a dendritic tree in 3D space that can be rotated by the user.
class ShollCanvas(BaseMatplotlibCanvas):
    TREE_COUNT = 3
    FIT_DEGREE = 7

    def __init__(self, parent, fullState, firstTreeIdx, treeModels, filePaths, *args, **kwargs):
        self.treeModels = treeModels
        self.filePaths = filePaths
        self.vizTreeCount = min(len(treeModels), self.TREE_COUNT)
        self.firstTree = max(0, min(len(treeModels) - self.vizTreeCount, firstTreeIdx))

        maxRadius = 0
        for tree in treeModels:
            maxRadius = max(maxRadius, tree.spatialRadius())
        maxRadius += 1e-9 # exclusive -> inclusive(ish)

        analysisOpt = fullState.projectOptions.analysisOptions
        self.binSizeUm = analysisOpt['shollBinSize'] if 'shollBinSize' in analysisOpt else 5.0

        self.maxCount = 0
        self.shollResults = []
        for tree in treeModels:
            crossCounts, radii = shollCrossings(tree, self.binSizeUm, maxRadius)
            pCoeff, maxX, maxY = shollMetrics(crossCounts, radii)
            self.shollResults.append((crossCounts, radii, pCoeff, maxX, maxY))
            self.maxCount = max(self.maxCount, np.max(crossCounts))

        super(ShollCanvas, self).__init__(*args, subplots=self.vizTreeCount, **kwargs)
        self.fig.subplots_adjust(top=0.95, bottom=0.05, right=0.95, left=0.05, wspace=0.05, hspace=0.05)


    def compute_initial_figure(self):
        for offset, ax in enumerate(self.axes):
            treeIdx = self.firstTree + offset
            ax.set_title(util.createTitle(treeIdx, self.filePaths[treeIdx]))
            ax.set_facecolor("white")
            ax.set_ylim(0, 1.1 * self.maxCount)
            ax.set_xlabel("Radius (uM)")
            if offset == 0:
                ax.set_ylabel("Intersection count")
            else:
                ax.get_yaxis().set_visible(False)
            self.drawSingleTreeSholl(ax, treeIdx)

    # Given one tree, draw sholl data for that tree
    def drawSingleTreeSholl(self, ax, treeIdx):
        counts, xs, pCoeff, maxX, maxY = self.shollResults[treeIdx]
        bounds = [np.min(xs), np.max(xs)]
        hdPolyX = np.arange(bounds[0], bounds[1], (bounds[1]-bounds[0]) / 1000)

        ax.bar(xs, counts, width=(self.binSizeUm * 0.8), color='b', alpha=0.5, zorder=1)
        ax.plot(hdPolyX, npPoly.polyval(hdPolyX, pCoeff).clip(min=0), color='b', zorder=2)
        ax.scatter(maxX, maxY, c='r', zorder=3)

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
